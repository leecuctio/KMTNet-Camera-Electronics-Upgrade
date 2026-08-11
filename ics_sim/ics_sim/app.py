#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Application wiring.

9개 노드(ICS + K/M/T/N.IC + K/M/T/N.CB)를 한 프로세스에서 대표한다.  수신은
9개 ID 전부로 받고(그래야 OBSAgent 의 kstatus/dmawait/datasource 가 도달한다),
발신 이름은 emit_node_mode 에 따라 노드별 또는 전부 ICS 로 낸다 (DevNote 3.1).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable

from .auxcontrol import AuxControlClient
from .commands import Dispatcher
from .config import SimConfig
from .emitter import Emitter
from .hardware import make_backend
from .impv2 import Message
from .nodes import NodeRouter, Role
from .sequencer import Sequencer
from .state import IcsState
from .telemetry import TelemetryRelay
from .transport import UdpEndpoint

log = logging.getLogger('ics_sim.app')


class IcsSim:
    """시뮬레이터 본체."""

    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg
        self.router = NodeRouter(cfg.node)
        self.state = IcsState(expnum_file=cfg.paths.expnum_file)
        # 마지막으로 쓴 EXPNUM 을 이어받는다 -- 재실행에도 번호가 되돌아가지
        # 않는 것이 요구사항이다 (state.load_expnum, DevNote 11.12)
        self.state.load_expnum()
        self.state.init_channels(cfg.node.ccds)
        self.state.guide_build = ''

        self.transport = UdpEndpoint(cfg, self._on_message)
        self.emit = Emitter(cfg, self.router, self.transport.send)
        self.telem = TelemetryRelay(cfg, self._send_query)
        self.backend = make_backend(cfg)
        self.aux = AuxControlClient(cfg.auxcontrol)
        self.seq = Sequencer(cfg, self.state, self.emit, self.router,
                             self.telem, self.backend, self.aux)
        self.dispatch = Dispatcher(self)

        self._tasks: set[asyncio.Task] = set()
        #: 마지막 브로드캐스트 (원문, 수신 시각) -- XIS 가 등록 슬롯마다 한 부씩
        #: 복사해 보내는 중복 사본을 걸러낸다 (DevNote 3.1.2)
        self._last_broadcast: tuple[str, float] = ('', 0.0)

    # -- 생명주기 ---------------------------------------------------------

    async def start(self) -> None:
        for note in self.cfg.validate():
            log.warning('config: %s', note)
        if self.cfg.transport.xis_addr is not None:
            # XIS 는 같은 노드 ID 로 메시지가 오면 (IP,port) 를 확인 없이
            # 덮어쓴다.  운영 허브에 레거시 ICS/IC 가 살아 있는 채로 붙으면
            # 등록하는 순간 그쪽 라우팅을 가로챈다 (xis/xis.md 7절).
            log.warning(
                'XIS 허브 %s:%d 에 연결합니다 -- 운영 허브라면 레거시 ICS/IC '
                '계통(및 isisrelay)을 먼저 정지하세요.  같은 노드 ID 등록이 '
                '레거시의 라우팅을 즉시 가로챕니다 (xis/xis.md 7절)',
                *self.cfg.transport.xis_addr)
        await self.transport.start()
        await self.aux.start()
        self.register()
        log.info('ICS simulator ready -- nodes: %s, backend=%s',
                 ', '.join(self.router.registered_ids), self.backend.name)

    def register(self) -> None:
        """XIS 에 노드를 등록한다 -- 수신하려는 **9개 ID 전부**로 PING 을 보낸다.

        IMPv2 에는 등록 API 가 없다.  노드가 자기 이름으로 아무 메시지나 보내면
        XIS 가 "노드ID -> (IP,port)" 를 기억하는 것이 전부다.  ICS 이름으로만
        보내면 K.IC 앞으로 오는 kstatus/dmawait/datasource 가 도달하지 않는다
        (DevNote 3.1.1).

        **9개 ID 가 같은 (IP,port) 를 가리켜도 안전하다** -- 2026-08-04 에 XIS
        서버 소스로 확인했다.  클라이언트 테이블은 노드 ID 로만 키잉되고
        (`strcmp` 로 ID 만 비교, 주소는 갱신만 한다) 주소 충돌 검사 자체가 없다.
        브로드캐스트 코드도 *"clients that share the same port as the sending
        host"* 를 명시적으로 다룬다.  한때 검토하던 "노드마다 소켓을 따로
        여는 방식(2안)"은 불필요하다 -- 논의 전 과정은 xis/xis.md 부록 A.
        """
        if not self.cfg.transport.register_all_nodes:
            self.emit.register_ping(self.cfg.node.ics_id)
            log.warning('register_all_nodes=false -- %s 만 등록합니다. '
                        'kstatus/dmawait/datasource 는 도달하지 않습니다',
                        self.cfg.node.ics_id)
            return
        for node_id in self.router.registered_ids:
            self.emit.register_ping(node_id)

    async def stop(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
        await self.aux.stop()
        await self.transport.stop()

    def spawn(self, coro: Awaitable) -> asyncio.Task:
        """부수 작업을 백그라운드로 돌린다 (참조를 유지해 GC 를 막는다)."""
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    # -- 수신 -------------------------------------------------------------

    def _send_query(self, dest: str, cmdword: str) -> None:
        """TelemetryRelay 가 TC 에 질의할 때 쓰는 콜백."""
        self.emit.emit_req(dest, cmdword)

    def _on_message(self, msg: Message, addr) -> None:  # noqa: ANN001
        # 자기 발신 에코부터 버린다.  XIS 경유 모드에서는 시퀀서가 K.IC 등
        # 자기 노드 앞으로 보낸 INITIALIZE/ERASE/SHOPEN/GO 가 허브를 돌아
        # 그대로 되돌아온다 -- 클라이언트 테이블의 K.IC 주소가 우리 자신이기
        # 때문이다.  걸러내지 않으면 명령이 이중 실행된다 (DevNote 3.1.2).
        # 내부 실행은 발신 전에 이미 끝났으므로 에코는 버리는 것이 맞다.
        if self.router.owns(msg.src):
            log.debug('self-echo dropped: %s', msg.raw)
            return

        # AL 브로드캐스트는 XIS 가 등록 슬롯마다 한 부씩 복사한다 -- 9개 ID 로
        # 등록한 우리에게는 같은 데이터그램이 최대 9부 도착한다 (v2.9.1 은
        # 송신 슬롯 하나만 제외한다, xis/xis.md 6.3).  첫 부만 처리한다.
        if msg.is_broadcast:
            now = time.monotonic()
            last_raw, last_seen = self._last_broadcast
            if (msg.raw == last_raw and
                    now - last_seen <= self.cfg.transport.broadcast_dedup_sec):
                log.debug('duplicate broadcast dropped: %s', msg.raw)
                return
            self._last_broadcast = (msg.raw, now)

        # TC 응답부터 걸러낸다 -- 우리가 먼저 질의한 것에 대한 답이다.
        if msg.mtype == 'DONE' and msg.src.upper() == 'TC':
            if self.telem.on_tc_reply(msg):
                return

        target = self.router.resolve(msg)

        if target.role is Role.GUIDE:
            # G.IC 는 범위 밖이다.  ICG 가 별도 프로그램으로 존재하므로 여기서
            # 답하면 오히려 충돌한다.
            return
        if not target.is_ours:
            return

        if msg.mtype in ('REQ', 'EXEC'):
            self.dispatch.handle(msg, target)
            return

        # DONE/STATUS/ERROR/WARNING 은 다른 노드의 보고다.  통합 구조에서는
        # 우리가 스스로에게 보낼 일이 없으므로 기록만 한다.
        log.debug('unhandled %s from %s: %s', msg.mtype, msg.src, msg.payload)

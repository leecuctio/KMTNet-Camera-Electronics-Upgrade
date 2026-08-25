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
import os
import time
from typing import Awaitable

from . import rawhdr, rawpair
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


def _disp_width(text: str) -> int:
    """터미널에서 차지하는 칸 수.  **한글·한자는 두 칸이다.**

    `f'{label:<14}'` 는 문자 수로 세므로 한글 라벨이 든 표가 어긋난다.
    stdlib 만으로 맞추려면 East Asian Width 를 보면 된다.
    """
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1
               for c in text)


class IcsSim:
    """시뮬레이터 본체."""

    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg
        self.router = NodeRouter(cfg.node)
        # `site_code` 는 파일명 `<YYYYMMDD>`(사이트별 관측일)와 헤더 정체성에
        # 함께 쓰인다.  `normalize_site()` 를 지나므로 `KMTC`/`KMTS`/`KMTA` 밖은
        # 모두 `KMTK` 로 떨어진다 (운영자 확정 2026-08-13, 코드는 D-017 개정).
        site, self.site_why = self._resolve_site()
        self.state = IcsState(expnum_file=cfg.paths.expnum_file,
                              site_code=site)
        # 마지막으로 쓴 EXPNUM 을 이어받는다 -- 재실행에도 번호가 되돌아가지
        # 않는 것이 요구사항이다 (state.load_expnum, DevNote 11.12)
        self.state.load_expnum()
        self.state.init_channels(cfg.node.ccds)
        self.state.guide_build = ''

        self.transport = UdpEndpoint(cfg, self._on_message)
        self.emit = Emitter(cfg, self.router, self.transport.send)
        self.telem = TelemetryRelay(cfg, self._send_query)
        # TC 의 TELID 를 실효 사이트와 대조하게 한다 (D-015).
        self.telem.site_code = site
        self.backend = make_backend(cfg)
        self.aux = AuxControlClient(cfg.auxcontrol)
        self.seq = Sequencer(cfg, self.state, self.emit, self.router,
                             self.telem, self.backend, self.aux)
        self.dispatch = Dispatcher(self)

        self._tasks: set[asyncio.Task] = set()
        #: 마지막 브로드캐스트 (원문, 수신 시각) -- XIS 가 등록 슬롯마다 한 부씩
        #: 복사해 보내는 중복 사본을 걸러낸다 (DevNote 3.1.2)
        self._last_broadcast: tuple[str, float] = ('', 0.0)

    def _resolve_site(self) -> tuple[str, str]:
        """실효 사이트 코드와 그 근거.

        **`[node] observatory` 한 값이 정한다** (운영자 지시 2026-08-24).
        `config.load()` 가 이미 그 값을 검증하고 `telid`/`site` 를 유도해
        두었으므로 여기서는 읽어 오기만 한다 -- 모르는 값이면 설정 읽기
        단계에서 이미 거부됐다.

        ⚠️ 종전에는 **호스트 IP 판정(D-015)이 ini 를 이겼다.**  그 경로는
        폐지했다: NIC 가 내려가거나 낯선 대역에 붙으면 실제 관측 자료가
        `KMTK.…` 이름으로 저장되는 위험이 있었고, 그것을 막는 대가로 "설정이
        맞는데도 판정이 이긴다" 는 반대 위험을 안고 있었다.  이제는 설정
        한 줄이 정본이고, 대신 그 값이 **틀리면 기동이 멈춘다.**
        """
        n = self.cfg.node
        return n.telid, f'[node] observatory={n.observatory}'


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
        self._warn_if_real_frames_would_be_labelled_bench()
        self.log_identity_banner()
        log.info('ICS simulator ready -- nodes: %s, backend=%s',
                 ', '.join(self.router.registered_ids), self.backend.name)

    def _warn_if_real_frames_would_be_labelled_bench(self) -> None:
        """실물 컨트롤러인데 사이트가 `KMTK`(KASI) 인 경우 (D-011 · D-017).

        **이 조합만 조용히 넘어갈 수 있어서 따로 잡는다.**  사이트가 `KMTK` 면
        보통은 정말 실험실이고 시뮬 프레임이라 문제가 없다.  그런데 백엔드가
        `archon` 이면 **실화소가 `KMTK.…` 이름으로 아카이브에 들어간다** --
        사이트 정체를 영구히 잃는 경로다.

        사이트는 이제 `[node] observatory` 한 줄이 정하므로(2026-08-24) 오배포는
        **그 줄 하나가 틀린 것**이다.  실물 백엔드로 KASI 이름을 달고 찍는
        상황이 그 증상이다.

        시뮬 백엔드에서는 아무 말도 하지 않는다 -- 실험실이 조용해야 사람이
        경고를 무시하는 것을 학습하지 않는다.
        """
        if self.state.site_code != rawpair.KASI_SITE:
            return
        if rawhdr.datasrc_of(self.backend.name) == rawhdr.DATASRC_SIM:
            return
        log.warning(
            '사이트가 %s(KASI/실험실)인데 백엔드가 실물 %r 이다 -- **실화소가 '
            '%s.… 이름으로 저장된다.**  관측소 장비라면 [node] observatory 가 '
            'KASI 로 남아 있는 것이니 CTIO/SSO/SAAO 중 맞는 값으로 고칠 것.  '
            '자료를 찍기 전에 확인할 것 (D-017)',
            rawpair.KASI_SITE, self.backend.name, rawpair.KASI_SITE)

    def log_identity_banner(self) -> None:
        """기동 시 **사이트 정체를 한 덩어리로** 남긴다.

        **오배포를 자료 한 장 찍기 전에 사람 눈에 띄게 하는 것이 목적이다.**
        `[node] observatory` 한 줄이 사이트 코드 -> 좌표 -> 관측일 경계 ->
        파일명 -> `INSTRUME` -> `TELESCOP`/`FPAID` 까지 전부 끌고 가므로
        (D-011·D-014·D-017), 그 한 줄이 틀리면 **아무 오류 없이** 전부 틀린다.  헤더에 `OBSERVAT`/좌표가 남으니 사후 탐지는 가능하지만,
        그때는 이미 아카이브에 들어가 있다 -- 그래서 **t=0 에 보여주는 쪽**이
        런타임 검사보다 값싸고 확실하다.

        파일명 예시를 함께 찍는 이유: 운영자가 실제로 확인해야 하는 것이
        "이 이름으로 아카이브에 들어가도 되나" 이기 때문이다.  설정값 나열보다
        완성된 이름 한 줄이 오배포를 더 빨리 드러낸다.

        `DATASRC` 를 넣은 이유: 시뮬 산출물이 실제 아카이브로 흘러드는 것을
        막는 유일한 카드이므로(규격 5.5절), 기동 때 그 값을 보고 넘어가게 한다.
        """
        cfg, st = self.cfg, self.state
        site = st.site_code
        geo = rawhdr.observatory_header(site, cfg.site_for(site))
        instr = rawhdr.instrument_header(rawpair.CONTROLLERS[0][0], site,
                                         cfg.camera.as_dict())
        suffix = f'{st.obs_date()}.{st.expnum:06d}'
        example = rawpair.physical_name(site, suffix, rawpair.CONTROLLERS[0][0])

        def known(card: str) -> bool:
            """sentinel 이 아닌 실제 값인가 (규격 5.0절: 문자열 `NC`, 정수 `-1`)."""
            v = geo[card]
            return str(v) != 'NC' and v != -1

        if known('LATITUDE'):
            where = (f'lat {geo["LATITUDE"]}   lon {geo["LONGITUD"]} (서경)'
                     f'   elev {geo["ELEVATIO"]} m')
        else:
            # 값이 없을 때 `elev -1 m` 처럼 sentinel 을 단위와 함께 보여주면
            # 실제 측정값처럼 읽힌다.  없다고 말하는 편이 낫다.
            where = '(설정 없음 -- 헤더에 sentinel 이 실린다)'

        boundary = rawpair.boundary_ut(site)
        obsday = (f'UT {boundary}   -- 파일명 <YYYYMMDD> 가 이 경계로 갈린다'
                  if boundary != '(없음)' else
                  'UT 날짜 그대로 (KASI 는 관측 야간 개념이 없다)')

        rows = [
            ('사이트', f'{site}   (OBSERVAT='
                       f'{rawpair.OBSERVAT.get(site, "?")})'),
            ('근거', getattr(self, 'site_why', '(없음)')),
            ('TELESCOP', str(geo['TELESCOP'])),
            # `FPAID` 도 사이트가 정한다 (raw spec 5.3.1절, D-017 항목 6) --
            # 사이트를 바꾸면 **조용히 따라오는** 값이라 배너에 세운다.
            # ⚠️ 망원경 번호와 FPA 번호는 관측소 셋 모두 어긋나는 것이 정상이다.
            ('FPAID', str(instr['FPAID']).strip()),
            ('위치', where),
            ('관측일 경계', obsday),
            ('파일명 예시', example),
            # **풀어낸 절대경로를 보여준다.**  상대경로(`../data`)는 **실행한
            # 디렉터리** 기준으로 풀리고 `~` 는 펼쳐지므로, 적어 둔 문자열만
            # 보여 주면 자료가 실제로 어디에 쌓이는지 알 수 없다 -- 배너의
            # 목적은 "자료 한 장 찍기 전에 사람 눈에 띄게" 다.
            ('data_dir', os.path.abspath(cfg.paths.data_dir)
                         + ('' if os.path.isabs(cfg.paths.data_dir)
                            else f'   (설정 {cfg.paths.data_dir!r} · cwd 기준)')),
            ('EXPNUM', f'다음 {st.expnum:06d}'
                       f'   (기록 {st.expnum_file or "지속 없음"})'),
            ('backend', f'{self.backend.name}'
                        f'   ->  DATASRC={rawhdr.datasrc_of(self.backend.name)}'),
        ]

        width = 74
        lines = ['=' * width,
                 ' 사이트 정체 -- 배포가 맞는지 여기서 확인하세요',
                 '-' * width]
        lines += [f' {label}{" " * max(1, 15 - _disp_width(label))}{value}'
                  for label, value in rows]
        lines.append('=' * width)
        # 여러 줄을 **한 번의 로그 호출**로 낸다 -- 줄마다 부르면 다른 태스크의
        # 로그가 사이에 끼어 덩어리가 깨진다.
        log.info('\n%s', '\n'.join(lines))

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

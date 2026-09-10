#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UDP transport for IMPv2 messages.

전송 계층은 UDP 다 (ics_legacy_report 7.3절).  연결 개념이 없으므로 노드 등록도
"자기 포트를 열고 PING 을 한 번 보내기"가 전부다.

두 가지 발신 경로를 지원한다:
  * xis_host 가 설정돼 있으면 모든 발신을 XIS 허브로 보낸다 (실제 배치 형태).
  * 비어 있으면 direct-reply 모드 -- recvfrom 으로 학습한 피어 주소로 직접
    보낸다.  허브 없이 시뮬 하나만 띄워 시험할 때 쓴다.

발신은 rate-limited 큐를 거친다.  레거시 MODS 클라이언트의 dispatcher.cpp 가
같은 패턴을 쓴다(ics_legacy_report 7.5절) -- 4개 IC 에 연달아 명령을 뿌릴 때
UDP 유실이나 수신측 처리 지연을 막기 위해서다.

참고 (DevNote 5.3): 실제 배치에서 ICS<->XIS 링크만 시리얼(/dev/ttyS0)이고, 그
구간에서만 바이트 손상/메시지 접합이 관측된다.  시뮬은 UDP 만 쓰므로 그 계열
손상은 구조적으로 발생하지 않는다.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable

from . import impv2
from .impv2 import Message

log = logging.getLogger('ics_sim.transport')

#: ⭐ **화면에서 뺄 자동 왕복**의 커맨드워드 (운영자 2026-09-11).  사람이 친
#: 것도, 사람에게 답한 것도 아니고 **프로그램이 스스로 주고받는** 줄들이다 --
#: 취득마다 나가는 텔레메트리 질의(`AUXSTATUS`/`TCSSTATUS`)와 기동 핸드셰이킹
#: (`PING`/`PONG`).
#:
#: ⛔ **자취가 지워지는 것이 아니다** -- 로그 파일에는 그대로 남는다.  화면에만
#: 안 낸다 (`[logging] verbose`).
#: ⚠️ 목록을 늘릴 때는 *"이것이 없으면 사람이 무엇을 못 아나"* 를 먼저 볼 것.
#: 명령과 그 응답은 **여기 들어오면 안 된다** -- ABC/OBSAgent 가 무엇을
#: 시켰는지가 화면에서 사라진다.
CHATTER_WORDS = frozenset({'AUXSTATUS', 'TCSSTATUS', 'PING', 'PONG'})


def wire_command(raw: str) -> str:
    """와이어 한 줄에서 **커맨드워드**를 뽑는다.  못 뽑으면 빈 문자열.

    형식은 `SRC>DST [종류:] CMDWORD 본문` 이다 (스펙 2장) -- 종류(`DONE:` ·
    `ERROR:` · `STATUS:` · `EXEC:`)는 있을 수도 없을 수도 있다.

        ICG>TC AUXSTATUS                     -> 'AUXSTATUS'
        TC>ICG DONE: AUXSTATUS AUXQDATE=...  -> 'AUXSTATUS'
        ICG>ICG STATUS: GO PCTREAD=5         -> 'GO'
    """
    addr, _, rest = raw.partition(' ')
    if '>' not in addr:
        return ''
    parts = rest.split()
    if not parts:
        return ''
    word = parts[0]
    if word.endswith(':'):                 # 종류 -- 그 다음이 커맨드워드다
        word = parts[1] if len(parts) > 1 else ''
    return word.rstrip(':').upper()


def essential_wire(raw: str) -> bool:
    """이 와이어 줄을 **화면에 낼까** (`verbose = off` 일 때).

    ⭐ 판정은 커맨드워드 하나다 -- `CHATTER_WORDS` 에 들면 잡음이다.
    """
    return wire_command(raw) not in CHATTER_WORDS

Addr = tuple[str, int]
MessageHandler = Callable[[Message, Addr], None]


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, endpoint: 'UdpEndpoint') -> None:
        self._ep = endpoint

    def connection_made(self, transport) -> None:  # noqa: ANN001
        self._ep._transport = transport

    def datagram_received(self, data: bytes, addr: Addr) -> None:
        self._ep._on_datagram(data, addr)

    def error_received(self, exc: Exception) -> None:
        log.warning('UDP error: %s', exc)


class UdpEndpoint:
    """단일 UDP 소켓으로 9개 노드분 트래픽을 주고받는다."""

    def __init__(self, cfg, on_message: MessageHandler) -> None:
        self.cfg = cfg
        self._on_message = on_message
        self._transport: asyncio.DatagramTransport | None = None
        self._queue: asyncio.Queue[tuple[bytes, Addr | None, str]] = asyncio.Queue()
        self._pump: asyncio.Task | None = None
        #: 노드 이름(대문자) -> (주소, 학습 시각)
        self._peers: dict[str, tuple[Addr, float]] = {}
        self._last_sender: Addr | None = None
        #: 테스트/골든 대조용 발신 기록 (와이어에 실린 그대로, 종료문자 제외)
        self.sent_log: list[str] = []
        self.recv_log: list[str] = []

    # -- 생명주기 ---------------------------------------------------------

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(
            lambda: _Protocol(self),
            local_addr=(self.cfg.transport.bind_host, self.cfg.transport.bind_port),
        )
        self._pump = asyncio.create_task(self._pump_loop(), name='ics_sim.send_pump')
        log.info('UDP bound on %s:%d (%s)',
                 self.cfg.transport.bind_host, self.cfg.transport.bind_port,
                 'via XIS %s:%d' % self.cfg.transport.xis_addr
                 if self.cfg.transport.xis_addr else 'direct-reply mode')

    async def stop(self) -> None:
        if self._pump is not None:
            self._pump.cancel()
            try:
                await self._pump
            except asyncio.CancelledError:
                pass
            self._pump = None
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    @property
    def port(self) -> int:
        """실제 바인딩된 포트 (bind_port=0 일 때 유용)."""
        if self._transport is None:
            return self.cfg.transport.bind_port
        return self._transport.get_extra_info('sockname')[1]

    # -- 수신 -------------------------------------------------------------

    def _on_datagram(self, data: bytes, addr: Addr) -> None:
        msg = impv2.parse(data)
        if msg is None:
            # 스펙 2.5절: malformed 에는 절대 ERROR 로 응답하지 않는다.
            log.debug('malformed datagram from %s: %r', addr, data[:120])
            return
        self._last_sender = addr
        self._peers[msg.src.upper()] = (addr, time.monotonic())
        self.recv_log.append(msg.raw)
        if self.cfg.logging.wire and not self._keyboard_line(msg.raw):
            # ⛔ **키보드 에코는 안 찍는다** (운영자 2026-09-08).  콘솔 명령의
            # 응답은 우리 자신에게 나갔다가 되돌아와 `_on_message` 가 버리는데
            # (self-echo), 그것까지 찍으면 **한 메시지가 두 줄로 보인다**.
            # ⭐ 방향 표시(`<<<`)도 뗐다 -- `SRC>DST` 가 이미 방향을 말한다
            # (목적지가 우리면 들어온 것).
            log.info('%s', msg.raw,
                     extra={'essential': essential_wire(msg.raw)})
        self._on_message(msg, addr)

    def _keyboard_line(self, raw: str) -> bool:
        """`ICG>ICG …` 처럼 **우리가 우리에게** 보낸 줄인가.

        콘솔(키보드) 입력이 그 꼴로 조립된다 (`Console.feed`) -- 스펙 2.2절의
        키보드 인터페이스 관례다.  ⚠️ 노드 이름이 같은 것만 본다: 남이 우리
        앞으로 보낸 줄은 `SRC` 가 다르므로 걸리지 않는다.
        """
        me = (self.cfg.node.ics_id or '').upper()
        if not me:
            return False
        src, _, rest = raw.partition('>')
        dst = rest.split(' ', 1)[0] if rest else ''
        return src.strip().upper() == me and dst.strip().upper() == me

    def _trim_keyboard(self, line: str) -> str:
        """키보드 줄이면 `SRC>DST ` 앞머리를 뗀다 -- 아니면 그대로."""
        if not self._keyboard_line(line):
            return line
        _head, _, rest = line.partition(' ')
        return rest or line

    def feed(self, line: str, addr: Addr = ('127.0.0.1', 0)) -> None:
        """테스트에서 소켓 없이 메시지를 주입한다."""
        self._on_datagram(impv2.format_raw(line), addr)

    # -- 발신 -------------------------------------------------------------

    def send(self, payload: bytes, dest_node: str) -> None:
        """rate-limited 큐에 넣는다.  실제 전송은 pump 태스크가 한다."""
        line = payload.rstrip(b'\r').decode('ascii', errors='replace')
        self.sent_log.append(line)
        if self.cfg.logging.wire:
            # ⭐ **방향 표시를 안 쓴다** (운영자 2026-09-08) -- `SRC>DST` 가
            # 이미 방향을 말하므로 `>>>`/`<<<` 는 넉 자를 더할 뿐이다.
            # ⭐ **키보드 줄은 노드 표기까지 뗀다** -- `ICG>ICG DONE: …` 의
            # 앞 여덟 자는 *"내가 나에게"* 라 아무것도 안 알린다.
            log.info('%s', self._trim_keyboard(line),
                     extra={'essential': essential_wire(line)})
        self._queue.put_nowait((payload, self.route_for(dest_node), dest_node))

    def route_for(self, dest_node: str) -> Addr | None:
        """dest_node 를 실제 UDP 주소로.  없으면 `None`(발신이 버려진다).

        ⭐ 공개 이름인 것은 **보내기 전에 물어볼 수 있어야** 하기 때문이다 --
        콘솔의 `>NODE 메시지` 가 그렇다 (버려지는 것을 사람에게 알린다).
        ⚠️ `xis_addr` 이 설정돼 있으면 **늘 주소가 나온다** — 허브가 살아 있는지는
        이 함수가 모른다.
        """
        xis = self.cfg.transport.xis_addr
        if xis is not None:
            return xis
        known = self._peers.get(dest_node.upper())
        if known is not None:
            addr, learned = known
            if time.monotonic() - learned <= self.cfg.transport.peer_ttl_sec:
                return self._usable(addr)
            del self._peers[dest_node.upper()]
        return self._usable(self._last_sender)

    @staticmethod
    def _usable(addr: Addr | None) -> Addr | None:
        """포트 0 은 실주소가 아니다 -- feed() 로 주입된 테스트 메시지의 흔적."""
        if addr is None or addr[1] == 0:
            return None
        return addr

    async def _pump_loop(self) -> None:
        gap = self.cfg.transport.send_gap_ms / 1000.0
        while True:
            payload, addr, dest = await self._queue.get()
            if self._transport is not None and addr is not None:
                try:
                    self._transport.sendto(payload, addr)
                except OSError as exc:
                    log.warning('sendto %s (%s) failed: %s', dest, addr, exc)
            elif addr is None:
                log.debug('no route for %s, message dropped', dest)
            if gap > 0:
                await asyncio.sleep(gap)

    async def drain(self) -> None:
        """발신 큐가 빌 때까지 기다린다 (테스트 편의)."""
        gap = max(self.cfg.transport.send_gap_ms / 1000.0, 0.001)
        while not self._queue.empty():
            await asyncio.sleep(gap)

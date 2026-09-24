#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기동에서 **XIS 허브가 살아 있는지 확인하고, 아니면 멈춘다** (운영자 지시
2026-09-04).

⭐ **왜 멈추나.**  운영자 확정: *"ICS 와 ICG 는 XIS 를 통해서만 통신한다 --
직접 통신은 없앤다."*  그러면 허브가 없을 때 `VACGAUGE`·`EXPENABLE`·`HKDATA`
가 **한 줄도 안 나간다.**  ⛔ 그런데 그 실패가 **조용하다**: 라우트가 없으면
전송 계층이 `log.debug('no route for %s, message dropped')` 한 줄로 버린다.
`sendto` 는 성공하고 `error_received` 도 안 뜨므로 **신호가 0**이다 -- 게이지가
안 꺼진 채로 밤새 science 를 찍는 것이 그 상태다.  그래서 **자료를 찍기 전에**
막는다.

**어떻게 확인하나.**  IMPv2 표준 핸드셰이크 하나면 된다:

    ICS>XIS PING
    XIS>ICS PONG

⭐ 이것은 **추측이 아니라 허브 소스로 확인한 것**이다 -- `ics_sim/xis/branches/
xisis-2.7.3/server/commands.c:114` 가 `PING` 에 `PONG` 으로 답한다.  레거시
운영 콘솔에서도 같은 왕복이 보인다 (운영자 실측 2026-09-04:
`OBS% >XIS ping` -> `PONG received from XIS`).

⚠️ **허브 자신에게 묻는 것이 요점이다.**  다른 노드(ICG 등)에 물으면 *"허브가
죽었나 / 상대가 죽었나"* 를 못 가른다 -- 둘 다 무응답으로 같아 보인다.

⛔ **자동 우회는 없다.**  허브가 없으면 알리고 멈출 뿐, 직결로 넘어가지
않는다 (DevNote 11.15 확정 -- 두 경로가 조용히 갈리면 어느 길로 온 값인지 못
가른다).
"""

from __future__ import annotations

import asyncio
import logging

log = logging.getLogger('ics_archon.xischeck')

#: 허브 노드 이름 -- 레거시부터 이 이름이다 (`isis.ini` `ServerID`).
XIS_ID = 'XIS'

#: `PONG` 으로 치는 메시지 타입 (`msg.mtype`).  허브의 답은 타입 토큰이 없어 암묵
#: `REQ` 로 풀린다 -- `ERROR`/`FATAL`/`EXEC` 은 답이 아니다 (`XisGate.note_message`).
_PONG_TYPES = ('REQ', 'DONE')


class XisUnreachable(RuntimeError):
    """허브에 닿지 않는다 -- 기동을 멈춘다."""


class XisGate:
    """`PING` 을 보내고 `PONG` 을 기다린다.  못 받으면 기동을 멈춘다.

    쓰는 쪽은 둘만 하면 된다:

    * `_on_message()` 에서 받은 메시지를 `note_message()` 에 흘려보낸다.
    * `start()` 에서 `await gate.check(emit_ping)` 을 부른다.
    """

    def __init__(self, node_id: str, *, timeout: float = 2.0,
                 tries: int = 3, required: bool = True,
                 xis_host: str = '') -> None:
        #: 우리 이름 (진단 문구용).
        self.node_id = node_id
        self.timeout = float(timeout)
        self.tries = max(1, int(tries))
        self.required = bool(required)
        #: 설정된 허브 주소 -- 비어 있으면 애초에 허브로 안 간다.
        self.xis_host = (xis_host or '').strip()
        self._pong = asyncio.Event()
        #: 진단용 -- 몇 번째 시도에 답이 왔나 (0 = 못 받음).
        self.answered_on = 0

    # -- 수신 -------------------------------------------------------------

    def note_message(self, msg) -> None:  # noqa: ANN001
        """받은 메시지 하나를 본다 -- 허브의 `PONG` 이면 기다림을 푼다.

        ⚠️ **보낸 이가 허브인지 함께 본다** -- 다른 노드도 `PONG` 을 낸다
        (`commands.cmd_ping` 이 브로드캐스트 `PING` 에 답한다).  그것을 세면
        *"허브는 죽었는데 옆 노드가 살아 있어서 통과"* 가 된다.

        ⭐ **커맨드워드 + 타입으로 가른다** (DevNote 11.96) -- 허브의 답 `XIS>ICS PONG`
        은 타입 토큰이 없는 암묵 REQ 라 파서가 `mtype='REQ'`·`cmdword='PONG'` 으로 푼다.
        받는 타입은 `REQ` 와 `DONE` 둘이다 (`DONE: PONG` 꼴로 답하는 허브도 통과).
        ⛔ 원문 부분 문자열로 보지 않는다 (2026-09-15 규약) -- 본문에만 `PONG` 이 든 줄
        (`XIS>ICS ERROR: FOO PONG`)을 답으로 세면 안 된다.  ⛔ 커맨드워드만 봐도 안 된다
        -- `XIS>ICS ERROR: PONG …` 은 허브의 **거절**이지 살아 있다는 답이 아니다.
        ⚠️ `app._is_reply_to` 는 `DONE`/`ERROR`/`FATAL` 전용이라 여기에 못 쓴다.
        """
        if self._pong.is_set():
            return
        src = (getattr(msg, 'src', '') or '').upper()
        word = (getattr(msg, 'cmdword', '') or '').upper()
        mtype = (getattr(msg, 'mtype', '') or '').upper()
        if src == XIS_ID and word == 'PONG' and mtype in _PONG_TYPES:
            self._pong.set()

    # -- 검사 -------------------------------------------------------------

    async def check(self, emit_ping) -> None:  # noqa: ANN001
        """`PING` 을 보내고 `PONG` 을 기다린다.  없으면 `XisUnreachable`.

        `emit_ping` 은 인자 없이 불러 `PING` 한 통을 내보내는 콜러블이다
        (`lambda: app.emit.ping('XIS')`).

        ⚠️ **`required=False` 면 경고만 하고 지나간다** -- 시험 하네스와
        `--backend sim` 처럼 허브 없이 도는 자리가 있다.  ⛔ 배포 설정에서는
        켜 두는 것이 정본이다 (`[archon] require_xis`).
        """
        if not self.required:
            return
        if not self.xis_host:
            raise XisUnreachable(
                '[transport] xis_host 가 비어 있다 -- ICS 와 ICG 는 XIS 허브를 '
                '통해서만 통신하기로 확정됐다(운영자 2026-09-04).  비워 두면 '
                'VACGAUGE·EXPENABLE·HKDATA 가 **한 줄도 안 나가고 그 실패가 '
                '조용하다**(라우트가 없으면 메시지가 debug 로그 한 줄로 '
                '버려진다).  허브 주소를 적거나, 허브 없이 돌릴 자리라면 '
                '[archon] require_xis = false 로 명시할 것')
        for attempt in range(1, self.tries + 1):
            emit_ping()
            try:
                await asyncio.wait_for(self._pong.wait(), self.timeout)
            except asyncio.TimeoutError:
                log.warning('XIS did not answer PING (%d/%d) -- %s',
                            attempt, self.tries, self.xis_host)
                continue
            self.answered_on = attempt
            log.info('XIS confirmed -- PONG (attempt %d, %s)',
                     attempt, self.xis_host)
            return
        raise XisUnreachable(
            'XIS 허브(%s)가 PING 에 %d번 답하지 않았다 -- 기동을 멈춘다.  '
            '⭐ 허브가 떠 있는지(`isis -f<경로>/isis.ini`), 주소·포트가 맞는지, '
            '방화벽이 UDP 를 막지 않는지 볼 것.  ⛔ 허브 없이 %s 를 띄우면 '
            'ICG 와 주고받는 명령이 조용히 사라진다 -- 그래서 자료를 찍기 전에 '
            '멈춘다' % (self.xis_host, self.tries, self.node_id))

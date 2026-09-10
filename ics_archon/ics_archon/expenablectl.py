#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ICS 가 science 독출 앞뒤로 guide 노출을 막고 푼다 -- `EXPENABLE` (2026-09-04).

⭐ **파일 이름이 `guideexp.py` 였다** (개명 2026-09-09, DevNote 11.57).  이 모듈이
다루는 것은 `EXPENABLE` 이고 `GUIEXP`(가이드 노출시간)는 **다른 명령**인데, 옛
이름이 그 명령을 가리키는 것처럼 읽혔다 -- `app.py` 가 `CMD as GUIEXP_CMD` 로
들여오기까지 해서 더 그랬다 (지금은 `EXPENABLE_CMD`).
⛔ **ini 키는 그대로 `GUIEXPCTRL`·`guiexp_lead` 다** -- 설치본이 쓰는 운영자 낱말이라
갈아 끼우면 벤치 ini 가 깨진다.  그 둘의 개명은 운영자 판단이다.

운영자 문면: *"`EXPENABLE` 은 ICS 노출 전/후에 보내는 게 아니고, ICS(science
CCD) **독출 2초 전**과 **독출완료 직후**에 보내는 거야.  독출 전에 0, 독출 후에
1.  `ics_archon.ini` 에 `GUIEXPCTRL = true/false` 옵션을 두어서 true 일 때 자동
으로 보내주도록."*

⚠️ **`EXPENABLE` 의 뜻이 바뀐 것이 아니다** -- ICG 쪽 플래그(`icg_archon/
expenable.py`)는 그대로 *"guide 노출을 막는 지속 플래그"* 이고, 여기는 **ICS 가
그것을 자동으로 여닫는 쪽**이다.  콘솔에서 사람이 치는 길은 그대로 남는다.

    ICS>ICG EXPENABLE 0      science 독출 시작 `lead` 초 전
    ICS>ICG EXPENABLE 1      science 독출이 끝난 직후

⭐ **왜 "2초 전" 인가** -- guide 가 이미 시작한 프레임을 마칠 시간을 준다.
독출이 시작되는 순간에 보내면 그 프레임이 독출 구간에 걸친다.

⭐ **왜 "독출 후" 이고 "저장 후" 가 아닌가** -- 막으려는 것은 독출이고, 저장은
호스트 쪽 일이라 guide 와 무관하다.  ⚠️ 다만 `FETCH` 가 독출 구간에 포함되므로
**국면이 `READOUT` 을 벗어난 뒤**(=`WRITING`/`IDLE`)에 푼다 -- 운영자 단서
*"혹시 Fetch 에 방해가 된다면 fetch 후에"* 가 그 자리다.

⚠️ **`GO n` 이면 프레임마다 여닫는다** -- 독출이 n 번이기 때문이다.  그것이
의도이고, guide 는 그 사이에 노출한다.

⛔ **모르는 상태에서는 보낸다** -- 재기동 직후처럼 우리가 ICG 의 플래그를 모를
때, 안 보내면 *"막았다고 믿는데 안 막힌"* 상태가 된다.  같은 값을 두 번 보내는
비용은 메시지 하나뿐이다 (게이지와 달리 `APPLY*` 왕복이 없다).
"""

from __future__ import annotations

import asyncio
import logging

log = logging.getLogger('ics_archon.expenablectl')

CMD = 'EXPENABLE'

#: 상태 셋.  `BLOCKED` = guide 노출 금지(`0`), `ALLOWED` = 허용(`1`).
BLOCKED, ALLOWED, UNKNOWN = 'BLOCKED', 'ALLOWED', 'UNKNOWN'

#: 독출이 끝났다고 보는 국면들 -- `FETCH` 는 `READOUT` 안이므로 그 다음이다.
_DONE_PHASES = ('WRITING', 'IDLE')


class ExpEnableControl:
    """science 독출 구간에 맞춰 `EXPENABLE` 을 여닫는다."""

    def __init__(self, node: str, lead: float, spawn,  # noqa: ANN001
                 emit_req, reply_timeout: float = 10.0,  # noqa: ANN001
                 enabled: bool = True) -> None:
        self.node = node
        #: 독출 시작 **몇 초 전**에 막을지.
        self.lead = float(lead)
        self.reply_timeout = float(reply_timeout)
        self.enabled = bool(enabled)
        self._spawn = spawn
        self._emit_req = emit_req
        self.state = UNKNOWN
        self._deadman: asyncio.Task | None = None
        self._replied = True
        self.sent_block = 0
        self.sent_allow = 0

    # -- 국면 관찰 --------------------------------------------------------

    def on_phase(self, phase: str, to_readout: float) -> None:
        """감시 태스크가 매 틱 부른다.

        `phase` 는 `state.expstatus`, `to_readout` 은 **독출 시작까지 남은 초**
        (모르면 `inf`, 이미 독출 중이면 `0`).
        """
        if not self.enabled:
            return
        phase = (phase or '').upper()
        if phase == 'READOUT' or to_readout <= self.lead:
            self._want(BLOCKED)
        elif phase in _DONE_PHASES:
            self._want(ALLOWED)

    def _want(self, state: str) -> None:
        if self.state == state:
            return                          # 이미 그 상태 -- 안 보낸다
        self._send(state)

    # -- 발신 -------------------------------------------------------------

    def _send(self, state: str) -> None:
        word = '0' if state == BLOCKED else '1'
        self.state = state
        self._replied = False
        if state == BLOCKED:
            self.sent_block += 1
        else:
            self.sent_allow += 1
        log.info('ICS>%s %s %s (%s)', self.node, CMD, word,
                 'guide exposures blocked' if state == BLOCKED
                 else 'guide exposures allowed')
        self._emit_req(self.node, CMD, word)
        self._cancel(self._deadman)
        self._deadman = self._spawn(self._watch_reply(word))

    async def _watch_reply(self, word: str) -> None:
        """답이 없으면 알린다.  ⚠️ 조용한 실패는 *"막았다고 믿는"* 상태다."""
        try:
            await asyncio.sleep(self.reply_timeout)
        except asyncio.CancelledError:
            return
        if not self._replied:
            log.warning('%s did not answer %s %s within %.0fs -- the guide '
                        'exposure lock state is UNKNOWN',
                        self.node, CMD, word, self.reply_timeout)
            self.state = UNKNOWN

    def note_reply(self, line: str) -> None:
        """ICG 의 `EXPENABLE` 응답을 봤다."""
        self._replied = True
        if 'ERROR' in line.upper():
            log.warning('the guide exposure-lock command was refused -- %s',
                        line.strip())
            self.state = UNKNOWN
        else:
            log.debug('guide exposure-lock reply -- %s', line.strip())

    async def close(self) -> None:
        """종료 -- 데드맨만 세운다.

        ⚠️ **잠금을 풀지 않는다.**  ICS 가 내려갈 때 자동으로 풀면, 독출 중에
        죽은 경우 guide 가 그 구간에 노출한다.  ⭐ 푸는 것은 사람의 판단이고
        콘솔에서 `EXPENABLE ON` 한 줄이다.
        """
        self._cancel(self._deadman)
        self._deadman = None

    @staticmethod
    def _cancel(task) -> None:  # noqa: ANN001
        if task is not None and not task.done():
            task.cancel()

    def summary(self) -> str:
        return ('guide exposure: state=%s node=%s lead=%.1fs '
                '(sent block=%d allow=%d)'
                % (self.state, self.node, self.lead,
                   self.sent_block, self.sent_allow))

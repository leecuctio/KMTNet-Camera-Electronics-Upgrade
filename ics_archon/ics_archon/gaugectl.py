#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ICS 가 노출 앞뒤로 진공 이온게이지를 끄고 켠다 (운영자 지시 2026-09-04).

**왜.**  ⭐ *"진공게이지의 필라멘트가 science 영상 자료에 영향을 끼쳐"* (운영자).
그래서 게이지 Off 는 예외가 아니라 **science 노출 중의 평상 상태**다.

**누가 끄나.**  게이지는 guide 듀어의 `MOD10` 에 달려 있어 **ICG 만 만질 수
있다**.  그래서 ICS 는 명령을 **보내는** 쪽이다:

    ICS>ICG VACGAUGE OFF        노출 앞
    ICS>ICG VACGAUGE ON         노출이 끝나고 `reenable_after` 뒤

**언제.**  ⭐ **스크립트 관측이든 콘솔에서 직접 친 `GO` 든 같은 자리**를 지난다
(`Dispatcher.cmd_go`) -- 그래서 거기 한 곳에서 끈다.

⭐ **상태 넷을 명시한다** (운영자 정정 2026-09-04):

    노출 앞      ->  OFF          (끔.  명령을 보낸다)
    취득 종료    ->  PENDING_ON   (**켜짐대기** -- 아직 꺼져 있다)
    10분 경과    ->  ON           (켠다)
    새 노출      ->  OFF          (타이머 해제.  이미 꺼져 있으면 명령은 안 보낸다)

⚠️ **`PENDING_ON` 이 따로 있어야 하는 이유**: 타이머가 만료됐을 때 *"지금도
켜짐대기인가"* 를 물어야 한다.  ⛔ 그 확인이 없으면 **다음 노출 도중에 켜진다**
-- 취소가 한 박자 늦거나 취소 예외를 놓친 경우가 그것이다.  ⭐ 그래서 안전장치가
둘이다: **꺼질 때 타이머를 해제**하고, **만료 시점에 상태를 다시 본다**.

⭐ **명령을 안 보내도 상태는 옮긴다** -- 켜짐대기에서 새 노출이 오면 게이지는
이미 꺼져 있으므로 `VACGAUGE OFF` 를 다시 보내지 않지만, **상태는 `OFF` 로
되돌린다** (운영자 지적).  안 그러면 만료 판정이 켜짐대기를 보고 켜 버린다.

⚠️ **켜는 기준은 "취득(독출) 종료"** 다 -- 운영자 문면이 처음 *"셔터 닫힌 후"*
였는데 `GO n` 은 셔터가 **n 번** 닫히므로 첫 닫힘에 걸면 **다음 프레임 도중에
켜진다** (운영자 확인: *"맞아 취득(독출) 종료시점이 기준"*).

⛔ **끄는 것은 공짜가 아니다** -- `VACGAUGE` 가 `APPLYDIO09` 를 부르고 그것이
MOD10 의 VCPU 를 재시작해 **`DEWPRES` 에 결측 창**을 만든다 (DevNote 11.18).
그래서 **이미 꺼져 있다고 아는 동안에는 다시 보내지 않는다** -- 되풀이하면 창만
늘어난다.  ⚠️ ICG 가 재기동해도 그 상태는 컨트롤러 설정에 남아 있고 ICG 가
`RCONFIG` 로 되읽으므로(gauge.load), 우리가 아는 값과 어긋나지 않는다.

⚠️ **답이 안 와도 우리는 모른다** -- `DONE: VACGAUGE …` 는 ICS 의 명령 처리부가
쓰지 않는 메시지라 조용히 버려진다.  그래서 보낸 뒤 `reply_timeout` 안에 답이
안 보이면 **경고한다**: 게이지가 안 꺼진 채 science 를 찍는 것이 이 기능이
막으려던 바로 그 상태다.
"""

from __future__ import annotations

import asyncio
import logging
import time

log = logging.getLogger('ics_archon.gaugectl')

CMD = 'VACGAUGE'

#: 상태 넷.  ⭐ `PENDING_ON` 은 **아직 꺼져 있다** -- 물리적으로는 `OFF` 와
#: 같고, 다른 것은 *"타이머가 돌고 있다"* 는 사실뿐이다.
OFF, PENDING_ON, ON, UNKNOWN = 'OFF', 'PENDING_ON', 'ON', 'UNKNOWN'

#: 게이지가 **실제로 꺼져 있다고 아는** 상태들.
_DARK = (OFF, PENDING_ON)


class GaugeControl:
    """노출 앞뒤의 게이지 On/Off 와 되켜기 타이머."""

    def __init__(self, node: str, reenable_after: float, spawn,  # noqa: ANN001
                 emit_req, reply_timeout: float = 10.0,          # noqa: ANN001
                 enabled: bool = True, settle_after: float = 5.0,
                 is_busy=None) -> None:  # noqa: ANN001
        #: 명령을 보낼 상대 (ICG 의 노드 이름).
        self.node = node
        #: 취득이 끝나고 다시 켜기까지 [s].
        self.reenable_after = float(reenable_after)
        self.reply_timeout = float(reply_timeout)
        self.enabled = bool(enabled)
        self._spawn = spawn
        self._emit_req = emit_req
        #: ⛔ **취득 중인가** -- 인자 없는 호출로 참/거짓.  운영자 지시
        #: 2026-09-04: *"노출이나 독출 진행 중에는 무조건 Gauge ON 을 하지
        #: 않는다."*
        #:
        #: ⚠️ `None` 이면 **검사를 건너뛴다**(단위시험·하네스처럼 시퀀서가 없는
        #: 자리).  "모르니 안 켠다" 로 하면 그 자리에서 게이지가 **영영 안
        #: 켜진다** -- 실기에서는 앱이 반드시 건네주므로(`app.py`) 그 갈래가
        #: 남지 않는다.  ⭐ 호출이 **터졌을 때**는 반대로 "취득 중" 으로 본다
        #: (`_busy_now`) -- 배선이 없는 것과 배선이 고장 난 것은 다르다.
        self._is_busy = is_busy
        #: ⭐ 상태 기계 -- `OFF`/`PENDING_ON`/`ON`/`UNKNOWN`.
        #: ⚠️ 게이지의 실제 상태가 아니라 *"우리가 아는 바"* 다.
        self.state = UNKNOWN
        #: 되켜기 타이머 · 응답 데드맨 태스크.
        self._timer: asyncio.Task | None = None
        self._deadman: asyncio.Task | None = None
        #: 마지막으로 보낸 뒤 답을 봤나 -- 데드맨이 본다.
        self._replied = True
        #: ⭐ **껐으면 안정화 시간을 준다** [s] (운영자 지시 2026-09-04).
        self.settle_after = float(settle_after)
        #: 그 대기가 끝나는 시각 (monotonic).  `None` 이면 기다릴 것이 없다.
        self._settle_until: float | None = None
        #: 진단용 셈.
        self.sent_off = 0
        self.sent_on = 0

    # -- 바깥에서 부르는 자리 ---------------------------------------------

    def before_exposure(self) -> bool:
        """`GO` 처리 **앞에서** 부른다.  명령을 실제로 보냈으면 `True`.

        ⭐ **어느 갈래든 상태는 `OFF` 로 간다** -- 켜짐대기에서 왔으면 게이지는
        이미 꺼져 있으므로 명령은 안 보내지만, **상태를 안 옮기면 만료 판정이
        켜짐대기를 보고 다음 노출 도중에 켜 버린다** (운영자 지적).

        ⚠️ 타이머는 **언제나** 해제한다 -- 상태 확인과 이중 안전장치다.
        """
        if not self.enabled:
            return False
        self._cancel_timer('노출이 시작된다')
        if self.state in _DARK:
            # 게이지는 이미 꺼져 있다 -- `APPLYDIO` 가 `DEWPRES` 결측 창을
            # 만드므로 되풀이하지 않는다.  ⭐ 상태만 `OFF` 로 굳힌다.
            if self.state != OFF:
                log.info('켜짐대기를 취소하고 꺼짐으로 되돌린다 (새 노출)')
            self.state = OFF
            return False
        self._send(False)
        # ⭐ **켜져 있어서 방금 껐다** -- 실제로 꺼질 때까지 기다려야 한다.
        if self.settle_after > 0:
            self._settle_until = time.monotonic() + self.settle_after
        return True

    async def settle(self) -> None:
        """방금 끈 게이지가 **실제로 꺼질 때까지** 기다린다 (운영자 2026-09-04).

        ⛔ **`VACGAUGE OFF` 는 즉시가 아니다** -- ICG 가 `APPLYDIO09` 를 내고
        그것이 MOD10 의 VCPU 를 재시작한다.  그 사이에 `ccdflush = true` 의
        `Prep`+`Flush` 가 돌면 **필라멘트가 켜진 채로 flush** 하고, 그 오염은
        science 자료에 그대로 남는다 (이 기능이 막으려던 바로 그 상태).
        ⚠️ 응답(`DONE: VACGAUGE …`)을 기다리는 것이 더 정확하지만, 그 답은
        **ICS 명령 처리부가 쓰지 않는 메시지**라 `_on_message` 엿듣기에 기대야
        하고 답이 없을 때 무한정 막힌다 -- 고정 대기가 더 단순하고 예측 가능하다.

        ⭐ **켜져 있어서 껐을 때만 기다린다.**  연속 촬영은 노출이 1~2분이라
        둘째 장부터는 게이지가 이미 꺼져 있고(`before_exposure()` 가 명령을 아예
        안 보낸다) 이 대기도 **0초**다 (운영자 2026-09-04).

        한 프레임에 여러 번 불려도 안전하다 -- 마감 시각을 한 번 쓰고 지운다.
        """
        until, self._settle_until = self._settle_until, None
        if until is None:
            return
        left = until - time.monotonic()
        if left <= 0:
            return
        log.info('진공게이지를 껐다 -- %.1f 초 안정화한 뒤 노출을 시작한다 '
                 '(APPLYDIO 가 MOD10 VCPU 를 재시작한다)', left)
        await asyncio.sleep(left)

    def after_acquisition(self) -> None:
        """**독출이 끝난 시점**에 부른다 -- 켜짐대기로 옮기고 10분 타이머를 건다.

        ⭐ **10분의 기준은 독출 완료다** (운영자 확정 2026-09-04) -- 셔터
        닫힘이 아니다.  `GO n` 은 셔터가 n 번 닫히므로 첫 닫힘에 걸면 **다음
        프레임 도중에 켜진다**.

        ⭐ **켜짐대기에서도 다시 건다** (운영자 지시 2026-09-04).  타이머가
        취득 중에 만료되면 `_reenable_later()` 가 **켜지 않고 켜짐대기로
        남겨 두는데**, 그 상태를 여기서 받아 **독출 완료 시점부터 10분을 다시**
        센다.  ⛔ 종전에는 `state != OFF` 로 곧바로 돌아가 그 자리가 비어
        있었다 -- 그러면 켜짐대기인 채로 아무도 타이머를 안 걸어 게이지가
        **영영 안 켜진다**.

        ⚠️ 이미 켜져 있거나(`ON`) 모르는 상태(`UNKNOWN`)면 켤 것이 없다.
        """
        if not self.enabled or self.state not in _DARK:
            return
        self._cancel_timer('새 타이머를 건다')
        self.state = PENDING_ON
        log.info('취득 종료 -- 켜짐대기.  %.0f 초 뒤에 진공게이지를 켠다',
                 self.reenable_after)
        self._timer = self._spawn(self._reenable_later())

    def note_reply(self, line: str) -> None:
        """ICG 가 보낸 `VACGAUGE` 응답을 봤다고 알린다 (데드맨 해제)."""
        self._replied = True
        if 'ERROR' in line.upper():
            # ⛔ 껐다고 믿는 채로 science 를 찍는 것이 막으려던 상태다.
            log.warning('⛔ 진공게이지 명령이 거절됐다 -- %s.  게이지가 안 '
                        '꺼진 채 노출이 돌 수 있다', line.strip())
            # ⚠️ 모르는 상태에서 켜짐대기 타이머를 남기면 **모르는 채로 켠다**.
            self._cancel_timer('상태를 모르게 됐다')
            self.state = UNKNOWN
        else:
            log.info('진공게이지 응답 -- %s', line.strip())

    async def close(self) -> None:
        """종료 -- 타이머를 세운다.  ⚠️ 게이지를 켜지는 않는다.

        ⭐ 프로그램이 내려간다고 필라멘트를 켤 이유가 없다.  다음 기동이
        상태를 `RCONFIG` 로 되읽으므로 잃는 것도 없다.
        """
        self._cancel_timer('프로그램이 내려간다')
        self._cancel(self._deadman)
        self._deadman = None

    # -- 안쪽 -------------------------------------------------------------

    def _send(self, on: bool) -> None:
        word = 'ON' if on else 'OFF'
        self.state = ON if on else OFF
        self._replied = False
        if on:
            self.sent_on += 1
        else:
            self.sent_off += 1
        log.info('ICS>%s %s %s', self.node, CMD, word)
        self._emit_req(self.node, CMD, word)
        self._cancel(self._deadman)
        self._deadman = self._spawn(self._watch_reply(word))

    async def _watch_reply(self, word: str) -> None:
        """답이 안 오면 알린다 -- 조용한 실패가 가장 나쁜 자리다."""
        try:
            await asyncio.sleep(self.reply_timeout)
        except asyncio.CancelledError:
            return
        if not self._replied:
            log.warning('⚠️ %s 가 %s %s 에 %.0f 초 안에 답하지 않았다 -- ICG 가 '
                        '떠 있는지, 허브가 이 이름을 아는지 볼 것.  게이지 '
                        '상태는 **모름**이다', self.node, CMD, word,
                        self.reply_timeout)
            self._cancel_timer('상태를 모르게 됐다')
            self.state = UNKNOWN

    async def _reenable_later(self) -> None:
        try:
            await asyncio.sleep(self.reenable_after)
        except asyncio.CancelledError:
            return
        self._timer = None
        if self.state != PENDING_ON:
            # ⛔⛔ **이중 안전장치**다.  취소가 한 박자 늦거나 취소 예외를
            # 놓쳤을 때, 여기서 상태를 다시 안 보면 **노출 도중에 켜진다**.
            log.info('타이머가 만료됐지만 상태가 %s 라 켜지 않는다', self.state)
            return
        # ⛔⛔ **세 번째 안전장치 -- 취득 중이면 무조건 안 켠다**
        # (운영자 지시 2026-09-04).  상태 확인만으로는 못 막는 길이 있다:
        # 취득 중에 들어온 `GO` 가 *"already in progress"* 로 거절되면 그것이
        # `ERROR` 라서 자가 치유가 **돌고 있는 취득 중에** 타이머를 걸었다 --
        # 남은 노출이 10분을 넘으면 **노출 도중에 켜진다**.
        # ⭐ 여기서는 **켜지 않고 켜짐대기로 남긴다**.  다시 세는 것은
        # `after_acquisition()` 몫이고, 그래야 10분이 **독출 완료 기준**으로
        # 유지된다.
        if self._busy_now():
            log.info('%.0f 초가 지났지만 **취득 중이라 켜지 않는다** -- '
                     '켜짐대기로 남긴다.  독출이 끝나면 거기서부터 다시 '
                     '%.0f 초를 센다', self.reenable_after, self.reenable_after)
            return
        log.info('%.0f 초가 지났다 -- 진공게이지를 켠다', self.reenable_after)
        self._send(True)

    def _busy_now(self) -> bool:
        """취득이 돌고 있나.

        ⚠️ **배선이 없는 것과 고장 난 것을 가른다.**  `is_busy` 를 아예 안
        받았으면(단위시험·하네스) 검사를 **건너뛴다** -- 거기서 "취득 중" 으로
        보면 게이지가 영영 안 켜진다.  반대로 배선이 있는데 호출이 **터지면**
        "취득 중" 으로 본다: 켜야 할 때 안 켜면 진공 읽기가 늦어질 뿐이지만,
        안 켜야 할 때 켜면 **science 노출이 필라멘트에 오염된다** -- 두 실수의
        무게가 다르다.
        """
        if self._is_busy is None:
            return False
        try:
            return bool(self._is_busy())
        except Exception:                       # noqa: BLE001
            log.warning('취득 여부를 못 읽었다 -- 안전한 쪽으로 "취득 중" 으로 '
                        '본다 (게이지를 안 켠다)')
            return True

    def _cancel_timer(self, why: str) -> None:
        if self._timer is not None:
            log.info('되켜기 타이머를 취소한다 (%s)', why)
            self._cancel(self._timer)
            self._timer = None

    @staticmethod
    def _cancel(task) -> None:  # noqa: ANN001
        if task is not None and not task.done():
            task.cancel()

    # -- 진단 -------------------------------------------------------------

    @property
    def pending_reenable(self) -> bool:
        return self._timer is not None and not self._timer.done()

    @property
    def wanted(self):  # noqa: ANN201
        """게이지가 **켜져 있다고 아는가** -- `True`/`False`/`None`(모름).

        ⭐ `PENDING_ON` 은 `False` 다: 켜짐대기는 *"타이머가 돈다"* 는 뜻이고
        게이지는 **아직 꺼져 있다**.
        """
        if self.state == ON:
            return True
        if self.state in _DARK:
            return False
        return None

    def summary(self) -> str:
        return ('vacuum gauge: state=%s node=%s reenable=%.0fs%s '
                '(sent off=%d on=%d)'
                % (self.state, self.node, self.reenable_after,
                   ' [timer pending]' if self.pending_reenable else '',
                   self.sent_off, self.sent_on))

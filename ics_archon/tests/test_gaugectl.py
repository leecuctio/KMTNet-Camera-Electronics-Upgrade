#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ICS 가 노출 앞뒤로 진공게이지를 끄고 켠다 (운영자 지시 2026-09-04).

운영자 문면: *"ICS에서는 스크립트 관측 전에 또는 go를 직접 입력할 때에는 노출
전에 끄고, 타이머를 두어서 노출 완료(셔터 닫힌) 후 10분 뒤에 켜도록."*

⛔ **왜.**  게이지 필라멘트가 science 영상을 오염시킨다.  게이지는 guide 듀어의
`MOD10` 에 있어 **ICG 만** 만질 수 있으므로 ICS 는 `VACGAUGE` 를 **보낸다**.

지키려는 것 다섯:

* ⭐ **노출 앞에 끈다** -- `GO` 처리 앞이다 (스크립트든 콘솔이든 같은 자리).
* ⛔ **이미 꺼져 있으면 다시 안 보낸다** -- `APPLYDIO` 가 `DEWPRES` 결측 창을
  만든다 (11.18).  되풀이하면 창만 늘어난다.
* ⭐ **새 노출이 오면 되켜기 타이머를 취소한다** -- 안 그러면 노출 중에 켜진다.
* ⭐ **`GO` 가 거절되면 자가 치유**한다 -- 취득이 시작 안 됐으니 "끝났다" 도
  안 온다.  그대로 두면 게이지가 영영 꺼진 채 남는다.
* ⚠️ **답이 없으면 알린다** -- `DONE: VACGAUGE …` 는 ICS 가 안 쓰는 메시지라
  조용히 버려진다.  "안 꺼진 채 찍는" 상태가 소리 없이 지나가면 안 된다.
"""

from __future__ import annotations

import asyncio
import logging

import pytest

import ics_archon  # noqa: F401

from ics_archon import gaugectl as gc  # noqa: E402
from ics_archon.gaugectl import GaugeControl  # noqa: E402


class Harness:
    """보낸 것을 모으고 태스크를 붙잡아 두는 최소 하네스."""

    def __init__(self, **over) -> None:  # noqa: ANN003
        self.sent: list[tuple[str, str, str]] = []
        self.tasks: list = []
        opts = dict(node='ICG', reenable_after=0.05, reply_timeout=0.05)
        opts.update(over)
        self.gauge = GaugeControl(
            opts['node'], opts['reenable_after'], self._spawn, self._emit,
            opts['reply_timeout'], enabled=opts.get('enabled', True),
            settle_after=opts.get('settle_after', 5.0),
            is_busy=opts.get('is_busy'))

    def _spawn(self, coro):  # noqa: ANN001, ANN202
        task = asyncio.ensure_future(coro)
        self.tasks.append(task)
        return task

    def _emit(self, dest: str, cmdword: str, body: str = '') -> str:
        self.sent.append((dest, cmdword, body))
        return '%s %s %s' % (dest, cmdword, body)

    @property
    def words(self) -> list[str]:
        return [b for _d, _c, b in self.sent]

    async def settle(self, seconds: float = 0.12) -> None:
        await asyncio.sleep(seconds)


# -- 끄기 -------------------------------------------------------------------


def test_the_gauge_is_turned_off_before_the_exposure():
    """⭐ `GO` 앞에서 끈다 -- 상대는 ICG 다."""
    async def run():  # noqa: ANN202
        h = Harness()
        assert h.gauge.before_exposure() is True
        assert h.sent == [('ICG', 'VACGAUGE', 'OFF')], h.sent
        assert h.gauge.wanted is False
        await h.gauge.close()
    asyncio.run(run())


def test_a_second_go_does_not_resend_off():
    """⛔ 되풀이하면 `DEWPRES` 결측 창만 늘어난다 (APPLYDIO 가 VCPU 재시작)."""
    async def run():  # noqa: ANN202
        h = Harness()
        h.gauge.before_exposure()
        assert h.gauge.before_exposure() is False
        assert h.words == ['OFF'], h.sent
        await h.gauge.close()
    asyncio.run(run())


def test_it_does_nothing_when_disabled():
    """ini 로 끌 수 있어야 한다 (ICG 없이 ICS 만 돌리는 벤치)."""
    async def run():  # noqa: ANN202
        h = Harness(enabled=False)
        assert h.gauge.before_exposure() is False
        h.gauge.after_acquisition()
        await h.settle()
        assert h.sent == []
        await h.gauge.close()
    asyncio.run(run())


# -- 되켜기 타이머 ----------------------------------------------------------


def test_the_gauge_comes_back_on_after_the_timer():
    """⭐ 취득이 끝나고 `reenable_after` 뒤에 켠다."""
    async def run():  # noqa: ANN202
        # ⚠️ 데드맨 시한을 길게 준다 -- 이 하네스는 답을 안 하므로, 짧게 두면
        # 데드맨이 먼저 울어 `wanted` 가 **모름**이 된다(그게 맞는 거동이다).
        # 여기서 보려는 것은 타이머이지 데드맨이 아니다.
        h = Harness(reenable_after=0.05, reply_timeout=5.0)
        h.gauge.before_exposure()
        h.gauge.after_acquisition()
        assert h.gauge.pending_reenable
        await h.settle(0.15)
        assert h.words == ['OFF', 'ON'], h.sent
        assert h.gauge.wanted is True
        await h.gauge.close()
    asyncio.run(run())


def test_a_new_exposure_cancels_the_pending_timer():
    """⛔ 안 취소하면 **노출 중에 켜진다** -- 이 기능이 막으려던 바로 그것."""
    async def run():  # noqa: ANN202
        h = Harness(reenable_after=0.08)
        h.gauge.before_exposure()
        h.gauge.after_acquisition()
        await asyncio.sleep(0.02)
        h.gauge.before_exposure()          # 새 노출이 들어왔다
        assert not h.gauge.pending_reenable
        await h.settle(0.15)
        assert h.words == ['OFF'], '타이머가 살아남아 켜 버렸다: %s' % h.sent
        await h.gauge.close()
    asyncio.run(run())


def test_a_rejected_go_heals_itself():
    """⭐ `GO` 가 거절되면 취득 종료가 안 온다 -- 그대로 두면 영영 꺼져 있다."""
    async def run():  # noqa: ANN202
        # ⚠️ 데드맨을 길게 -- 이 하네스는 답을 안 하므로 짧으면 상태가 모름이
        # 되고, 그러면 타이머가 만료돼도 켜지 않는다(그게 맞는 거동이다).
        h = Harness(reenable_after=0.05, reply_timeout=5.0)
        h.gauge.before_exposure()
        h.gauge.after_acquisition()        # 디스패처가 거절을 보고 부르는 자리
        await h.settle(0.15)
        assert h.words == ['OFF', 'ON'], h.sent
        await h.gauge.close()
    asyncio.run(run())


def test_closing_does_not_light_the_filament():
    """⭐ 프로그램이 내려간다고 필라멘트를 켤 이유가 없다."""
    async def run():  # noqa: ANN202
        h = Harness(reenable_after=0.05)
        h.gauge.before_exposure()
        h.gauge.after_acquisition()
        await h.gauge.close()
        await h.settle(0.15)
        assert h.words == ['OFF'], h.sent
        assert not h.gauge.pending_reenable
    asyncio.run(run())


# -- 응답 · 데드맨 ----------------------------------------------------------


def test_a_missing_reply_is_reported(caplog):  # noqa: ANN001
    """⚠️ 조용한 실패가 가장 나쁘다 -- 안 꺼진 채 찍는 상태다."""
    caplog.set_level(logging.WARNING)

    async def run():  # noqa: ANN202
        h = Harness(reply_timeout=0.03)
        h.gauge.before_exposure()
        await h.settle(0.10)
        await h.gauge.close()
    asyncio.run(run())
    assert any('답하지 않았다' in r.message for r in caplog.records), \
        [r.message for r in caplog.records]


def test_a_reply_clears_the_deadman(caplog):  # noqa: ANN001
    caplog.set_level(logging.WARNING)

    async def run():  # noqa: ANN202
        h = Harness(reply_timeout=0.05)
        h.gauge.before_exposure()
        h.gauge.note_reply('ICG>ICS DONE: VACGAUGE Gauge=OFF')
        await h.settle(0.12)
        await h.gauge.close()
    asyncio.run(run())
    assert not any('답하지 않았다' in r.message for r in caplog.records)


def test_an_error_reply_makes_the_state_unknown(caplog):  # noqa: ANN001
    """⛔ 거절당했으면 **껐다고 믿으면 안 된다** -- 다음 `GO` 가 다시 보낸다."""
    caplog.set_level(logging.WARNING)

    async def run():  # noqa: ANN202
        h = Harness()
        h.gauge.before_exposure()
        h.gauge.note_reply('ICG>ICS ERROR: VACGAUGE Gauge control not available')
        assert h.gauge.wanted is None
        # 상태가 모름이므로 다음 노출에서 **다시 보낸다**.
        assert h.gauge.before_exposure() is True
        assert h.words == ['OFF', 'OFF'], h.sent
        await h.gauge.close()
    asyncio.run(run())
    assert any('거절됐다' in r.message for r in caplog.records)


def test_the_summary_reads_back_the_state():
    async def run():  # noqa: ANN202
        h = Harness(reply_timeout=5.0)
        assert 'state=UNKNOWN' in h.gauge.summary()
        h.gauge.before_exposure()
        said = h.gauge.summary()
        assert 'state=OFF' in said and 'node=ICG' in said, said
        await h.gauge.close()
    asyncio.run(run())


# -- ⭐ 상태 기계 (운영자 정정 2026-09-04) ----------------------------------


def test_the_states_walk_off_pending_on():
    """⭐ 노출 앞 `OFF` -> 취득 종료 `PENDING_ON` -> 10분 뒤 `ON`."""
    async def run():  # noqa: ANN202
        h = Harness(reenable_after=0.05, reply_timeout=5.0)
        assert h.gauge.state == gc.UNKNOWN
        h.gauge.before_exposure()
        assert h.gauge.state == gc.OFF
        h.gauge.after_acquisition()
        assert h.gauge.state == gc.PENDING_ON
        # ⭐ 켜짐대기는 **아직 꺼져 있다**.
        assert h.gauge.wanted is False
        await h.settle(0.15)
        assert h.gauge.state == gc.ON
        await h.gauge.close()
    asyncio.run(run())


def test_a_new_exposure_moves_pending_back_to_off_without_sending():
    """⭐⭐ 운영자 지적 -- **명령을 안 보내도 상태는 옮긴다**.

    ⛔ 상태를 켜짐대기로 남겨 두면, 타이머 취소를 놓쳤을 때 만료 판정이 그것을
    보고 **다음 노출 도중에 켜 버린다**.
    """
    async def run():  # noqa: ANN202
        h = Harness(reenable_after=5.0, reply_timeout=5.0)
        h.gauge.before_exposure()
        h.gauge.after_acquisition()
        assert h.gauge.state == gc.PENDING_ON and h.gauge.pending_reenable
        assert h.gauge.before_exposure() is False    # 게이지는 이미 꺼져 있다
        assert h.gauge.state == gc.OFF, '상태가 켜짐대기로 남았다'
        assert not h.gauge.pending_reenable, '타이머가 안 풀렸다'
        assert h.words == ['OFF'], '이미 꺼져 있는데 또 보냈다: %s' % h.sent
        await h.gauge.close()
    asyncio.run(run())


def test_the_timer_checks_the_state_before_switching_on():
    """⛔⛔ **이중 안전장치** -- 취소를 놓쳐도 만료 시점에 상태를 다시 본다."""
    async def run():  # noqa: ANN202
        h = Harness(reenable_after=0.05, reply_timeout=5.0)
        h.gauge.before_exposure()
        h.gauge.after_acquisition()
        # 타이머는 살려 둔 채 상태만 노출 중으로 되돌린다 (취소를 놓친 상황).
        h.gauge.state = gc.OFF
        await h.settle(0.15)
        assert h.words == ['OFF'], '상태가 꺼짐인데 켰다: %s' % h.sent
    asyncio.run(run())


def test_an_unknown_state_drops_the_pending_timer():
    """⚠️ 모르는 상태에서 켜짐대기를 남기면 **모르는 채로 켠다**."""
    async def run():  # noqa: ANN202
        h = Harness(reenable_after=5.0, reply_timeout=5.0)
        h.gauge.before_exposure()
        h.gauge.after_acquisition()
        h.gauge.note_reply('ICG>ICS ERROR: VACGAUGE nope')
        assert h.gauge.state == gc.UNKNOWN
        assert not h.gauge.pending_reenable, '모르는 상태인데 타이머가 남았다'
        await h.gauge.close()
    asyncio.run(run())


def test_after_acquisition_is_ignored_when_not_off():
    """켜져 있거나 모르는 상태면 켤 것이 없다."""
    async def run():  # noqa: ANN202
        h = Harness(reply_timeout=5.0)
        h.gauge.after_acquisition()               # UNKNOWN
        assert not h.gauge.pending_reenable
        h.gauge.state = gc.ON
        h.gauge.after_acquisition()
        assert not h.gauge.pending_reenable
        await h.gauge.close()
    asyncio.run(run())


# -- 껐을 때의 안정화 대기 (운영자 지시 2026-09-04) --------------------------


def test_a_gauge_that_was_on_gets_time_to_actually_turn_off():
    """⭐ **켜져 있어서 껐으면 기다린다.**

    ⛔ `VACGAUGE OFF` 는 즉시가 아니다 -- ICG 가 `APPLYDIO09` 를 내고 그것이
    MOD10 VCPU 를 재시작한다.  `ccdflush = true` 면 그 사이에 `Prep`+`Flush` 가
    **필라멘트가 켜진 채로** 돌아 science 자료를 오염시킨다.
    """
    import time as _t

    async def run():  # noqa: ANN202
        h = Harness(settle_after=0.08)
        h.gauge.state = gc.ON
        assert h.gauge.before_exposure() is True, '켜져 있는데 안 껐다'
        t0 = _t.monotonic()
        await h.gauge.settle()
        return _t.monotonic() - t0

    assert asyncio.run(run()) >= 0.07


def test_an_already_dark_gauge_does_not_delay_the_next_frame():
    """⭐ 연속 촬영의 **둘째 장부터는 0초**다 (운영자 2026-09-04).

    노출이 1~2분이면 게이지는 이미 꺼져 있어 `before_exposure()` 가 명령을 아예
    안 보내고(`APPLYDIO` 결측 창을 되풀이하지 않는다), 그러면 기다릴 것도 없다.
    """
    import time as _t

    async def run():  # noqa: ANN202
        h = Harness(settle_after=5.0)
        h.gauge.state = gc.OFF
        assert h.gauge.before_exposure() is False, '이미 꺼졌는데 또 보냈다'
        t0 = _t.monotonic()
        await h.gauge.settle()
        return _t.monotonic() - t0

    assert asyncio.run(run()) < 0.5


def test_the_settle_deadline_is_used_once():
    """한 프레임에 여러 번 불려도 **한 번만** 기다린다 (두 컨트롤러가 부른다)."""
    import time as _t

    async def run():  # noqa: ANN202
        h = Harness(settle_after=0.08)
        h.gauge.state = gc.ON
        h.gauge.before_exposure()
        await h.gauge.settle()
        t0 = _t.monotonic()
        await h.gauge.settle()
        return _t.monotonic() - t0

    assert asyncio.run(run()) < 0.05


# -- 취득 중에는 무조건 안 켠다 (운영자 지시 2026-09-04) ---------------------


def test_the_timer_never_turns_it_on_during_an_acquisition():
    """⛔ **취득 중이면 무조건 안 켠다.**

    상태 확인만으로는 못 막는 길이 있었다: 취득 중에 들어온 `GO` 가
    *"already in progress"* 로 거절되면 그것도 `ERROR` 라 자가 치유가
    **돌고 있는 취득 중에** 타이머를 걸었고, 남은 노출이 10분을 넘으면
    **노출 도중에 켜졌다** -- 이 기능이 막으려던 바로 그 상태다.
    """
    async def run():  # noqa: ANN202
        h = Harness(reenable_after=0.03, reply_timeout=5.0,
                    is_busy=lambda: True)
        h.gauge.state = gc.ON
        h.gauge.before_exposure()          # -> OFF (명령을 보낸다)
        h.gauge.after_acquisition()        # -> PENDING_ON + 타이머
        await asyncio.sleep(0.10)          # 만료시킨다
        return h.gauge.state, list(h.words)

    state, words = asyncio.run(run())
    assert state == gc.PENDING_ON, '취득 중인데 상태가 %s 로 갔다' % state
    assert 'ON' not in words, '취득 중에 켰다: %r' % words


def test_readout_completion_restarts_the_ten_minutes():
    """⭐ 취득 중에 만료됐으면 **독출 완료 시점부터 다시 센다** (운영자 확정).

    ⛔ 종전 `after_acquisition()` 은 `state != OFF` 로 곧바로 돌아갔다 --
    켜짐대기인 채로 아무도 타이머를 다시 안 걸어 게이지가 **영영 안 켜졌다**.
    """
    async def run():  # noqa: ANN202
        busy = {'v': True}
        h = Harness(reenable_after=0.03, reply_timeout=5.0,
                    is_busy=lambda: busy['v'])
        h.gauge.state = gc.ON
        h.gauge.before_exposure()
        h.gauge.after_acquisition()
        await asyncio.sleep(0.10)          # 취득 중 만료 -- 안 켠다
        assert h.gauge.state == gc.PENDING_ON, h.gauge.state
        busy['v'] = False                  # 독출이 끝났다
        h.gauge.after_acquisition()        # 여기서부터 다시 10분
        await asyncio.sleep(0.10)
        return h.gauge.state, list(h.words)

    state, words = asyncio.run(run())
    assert state == gc.ON, '독출이 끝났는데 안 켰다 (상태 %s)' % state
    assert words.count('ON') == 1, '켜기를 되풀이했다: %r' % words


def test_a_broken_busy_hook_is_treated_as_busy():
    """⚠️ 배선이 **고장 나면** "취득 중" 으로 본다 -- 안 켜는 쪽이 안전하다.

    ⭐ 배선이 **아예 없는** 것(`is_busy=None`, 단위시험·하네스)과는 다르다 --
    그때는 검사를 건너뛴다.  아니면 그 자리에서 영영 안 켜진다.
    """
    async def run():  # noqa: ANN202
        def boom():  # noqa: ANN202
            raise RuntimeError('시퀀서를 못 읽었다')

        h = Harness(reenable_after=0.03, reply_timeout=5.0, is_busy=boom)
        h.gauge.state = gc.ON
        h.gauge.before_exposure()
        h.gauge.after_acquisition()
        await asyncio.sleep(0.10)
        return h.gauge.state, list(h.words)

    state, words = asyncio.run(run())
    assert state == gc.PENDING_ON and 'ON' not in words, (state, words)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""방금 끈 진공게이지 -> **첫 장 앞 flush 한 번** (운영자 지시 2026-09-15, DevNote 11.93).

운영자 문면: *"GO 로 ICG 에 `VACGAUGE OFF` 를 보낸 경우, `gauge_settle_after` 만큼 대기
후, ACF 또는 ini 설정에서 FirstFlush=0 이면 FirstFlush=1 로 노출 시퀀스 시작.  FirstFlush>0
이면 기존 설정대로.  이미 OFF 였으면 보내지도, 기다리지도 않고, FirstFlush 는 기존 설정대로."*
그리고 *"무조건 올려"* -- `EveryFlush` 는 보지 않는다.

세 층이 나눠 진다:

* `gaugectl.take_flush_request()` -- 껐다는 사실을 **한 번** 내준다 (GO 의 첫 프레임 몫).
* `ArchonController.trigger(first_flush=1)` -- **그 LOADPARAMS 에만** `FirstFlush` 를
  올려 싣고 곧바로 원래 값으로 되돌린다 (`flush_now()` 방식) -- science 는 프레임마다
  LOADPARAMS 라 설정값을 남겨 두면 매 장 flush 가 된다.  ⛔ 되돌림은 `finally` 라
  **오류·취소에도** 되돌리고, 되돌림마저 실패하면 이미 걸린 노출은 그대로 두고
  다음 LOADPARAMS 앞에서 다시 쓴다 (DevNote 11.96).  되쓰기가 또 깨지면 `RCONFIG` 로
  되읽어 메모리가 이미 원래 값이면 표시를 지우고 간다 -- 막다른 길이 없다.
* `ArchonBackend._first_flush_for_this_frame()` -- 둘을 잇는다 (두 컨트롤러에 같은 값).
  끝단 배선은 셔터 경로를 이 파일의 `Session` 시험이, DARK 경로를
  `test_ics_ops_commands.py` 의 예열 GO(`flushes == 1`)가 본다.
"""

from __future__ import annotations

import asyncio
import logging

import pytest

import ics_archon  # noqa: F401

from ics_archon.archon.backend import ArchonBackend  # noqa: E402
from ics_archon.archon.controller import ArchonController  # noqa: E402
from ics_archon.archon.protocol import ArchonError  # noqa: E402

from test_ccdflush import GUIDE_ACF, Ctrl, _slot_write  # noqa: E402
from test_gaugectl import Harness  # noqa: E402


# -- gaugectl: 껐다는 사실을 한 번만 -----------------------------------------


def test_the_request_is_raised_only_when_off_was_actually_sent():
    """⭐ 보냈으면 `True` 한 번, 둘째 장부터 `False`.  이미 꺼져 있던 GO 는 처음부터 `False`."""
    async def run():  # noqa: ANN202
        h = Harness()
        assert h.gauge.take_flush_request() is False        # 아직 GO 가 없다
        assert h.gauge.before_exposure('ON') is True        # 켜져 있었다 -> OFF 를 보냈다
        assert h.gauge.take_flush_request() is True         # 첫 장
        assert h.gauge.take_flush_request() is False        # 둘째 장
        # 다음 GO -- ICG 낱말이 OFF 라 안 보낸다 -> flush 요청도 없다.
        assert h.gauge.before_exposure('OFF') is False
        assert h.gauge.take_flush_request() is False
        await h.gauge.close()
    asyncio.run(run())


def test_a_go_that_died_without_a_frame_does_not_leak_the_request():
    """앞 GO 가 프레임 없이 죽어 남긴 요청은 다음 GO 의 판단이 지운다 -- 그 GO 가 안
    보냈으면 flush 도 없다."""
    async def run():  # noqa: ANN202
        h = Harness()
        h.gauge.before_exposure('WARMUP')                    # 보냈다 (예열 중도 켜진 것)
        assert h.gauge.before_exposure('OFF') is False       # 새 GO -- 이미 꺼져 있다
        assert h.gauge.take_flush_request() is False
        await h.gauge.close()
    asyncio.run(run())


def test_disabled_control_never_asks_for_a_flush():
    async def run():  # noqa: ANN202
        h = Harness(enabled=False)
        assert h.gauge.before_exposure('ON') is False
        assert h.gauge.take_flush_request() is False
        await h.gauge.close()
    asyncio.run(run())


# -- controller: 그 LOADPARAMS 에만 ------------------------------------------


def _p0_writes(ctrl: Ctrl) -> list[str]:
    return [c for c in ctrl.writes() if 'PARAMETER0=' in c]


def test_zero_is_raised_to_one_for_that_loadparams_and_put_back():
    """⭐ science ACF 원문 `FirstFlush=0` -> LOADPARAMS 앞 `1`, 뒤 `0`.  메모리도 0 으로 끝난다."""
    ctrl = Ctrl()
    assert ctrl.flag() == 'FirstFlush=0'
    asyncio.run(ctrl.trigger(0, noint_ms=0, suffix='x', first_flush=1))
    assert _p0_writes(ctrl) == [_slot_write(ctrl, 'FirstFlush=1'),
                                _slot_write(ctrl, 'FirstFlush=0')], ctrl.sent
    up = ctrl.sent.index(_slot_write(ctrl, 'FirstFlush=1'))
    load = ctrl.sent.index('LOADPARAMS')
    down = ctrl.sent.index(_slot_write(ctrl, 'FirstFlush=0'))
    assert up < load < down, ctrl.sent
    assert ctrl.loads() == ['LOADPARAMS']
    assert ctrl.flag() == 'FirstFlush=0'
    assert ctrl.config['PARAMETER0'] == 'FirstFlush=0'


def test_without_the_request_the_slot_is_not_touched():
    ctrl = Ctrl()
    asyncio.run(ctrl.trigger(0, noint_ms=0, suffix='x'))
    assert _p0_writes(ctrl) == [], ctrl.sent
    assert ctrl.loads() == ['LOADPARAMS']


def test_an_ini_override_above_zero_is_left_alone():
    """*"FirstFlush > 0 이면 기존 설정대로"* -- `ccdflush_first = 2` 가 앉아 있으면 그대로."""
    ctrl = Ctrl()
    asyncio.run(ctrl.set_flush_param('FirstFlush', 2))
    before = len(_p0_writes(ctrl))
    asyncio.run(ctrl.trigger(0, noint_ms=0, suffix='x', first_flush=1))
    assert len(_p0_writes(ctrl)) == before, ctrl.sent
    assert ctrl.flag() == 'FirstFlush=2'


def test_everyflush_does_not_matter():
    """⭐ 운영자 확정: *"무조건 올려"* -- `EveryFlush=1` 이어도 `FirstFlush` 를 올린다
    (첫 장 앞에 flush 둘).  `GO n` 을 컨트롤러 시퀀서로 옮기면 둘의 뜻이 갈린다."""
    ctrl = Ctrl()
    asyncio.run(ctrl.set_flush_param('EveryFlush', 1))
    asyncio.run(ctrl.trigger(0, noint_ms=0, suffix='x', first_flush=1))
    assert _p0_writes(ctrl) == [_slot_write(ctrl, 'FirstFlush=1'),
                                _slot_write(ctrl, 'FirstFlush=0')], ctrl.sent


def test_the_guide_constant_one_is_already_enough():
    """guide ACF 는 `FirstFlush=1` 상수 -- 올릴 것이 없다 (이 경로를 지날 일도 없지만)."""
    ctrl = Ctrl(GUIDE_ACF)
    asyncio.run(ctrl.trigger(0, noint_ms=0, suffix='x', first_flush=1))
    assert [c for c in ctrl.writes() if 'FirstFlush' in c] == [], ctrl.sent


def test_an_acf_without_the_slot_warns_and_goes_on(tmp_path, caplog):  # noqa: ANN001
    """슬롯이 없는 ACF(R2608 이하) -- 경고 한 줄, flush 없이 노출은 간다."""
    acf = tmp_path / 'old.acf'
    acf.write_text('[CONFIG]\n'
                   'PARAMETER0="ContinuousExposures=0"\n'
                   'PARAMETER1="IntMS=0"\n'
                   'PARAMETER2="NoIntMS=0"\n'
                   'PARAMETER3="Exposures=0"\n'
                   'PARAMETERS=4\n', encoding='ascii')
    ctrl = Ctrl(str(acf))
    caplog.set_level('WARNING')
    asyncio.run(ctrl.trigger(0, noint_ms=0, suffix='x', first_flush=1))
    assert 'no flush before the first frame' in caplog.text
    assert ctrl.loads() == ['LOADPARAMS']


# -- controller: 오류·취소에도 되돌린다 (DevNote 11.96) ----------------------
#
# ⛔ 종전에는 되돌림이 LOADPARAMS **뒤 한 줄**이라 그 사이 무엇이 깨져도(쓰기 실패·시한
# 초과·ABORT 의 취소) `FirstFlush=1` 이 설정 메모리에 남았다.  `set_config` 가 캐시를 먼저
# 바꾸므로 캐시도 1 -- 다음 판단은 *"이미 켜져 있다"* 로 보고 손대지 않았고, science 는
# 그 세션 내내 **매 장** flush 를 돌았다(+5.5 s).


def _trigger(ctrl: Ctrl, **kw):  # noqa: ANN003, ANN202
    return ctrl.trigger(0, noint_ms=0, suffix='x', **kw)


def _ends_clean(ctrl: Ctrl) -> None:
    """메모리·캐시가 둘 다 원래 값(0)이고, 마지막 `PARAMETER0` 쓰기가 되돌림이다."""
    assert ctrl.flag() == 'FirstFlush=0', ctrl.sent
    assert ctrl.config['PARAMETER0'] == 'FirstFlush=0'
    assert _p0_writes(ctrl)[-1] == _slot_write(ctrl, 'FirstFlush=0'), ctrl.sent


@pytest.mark.parametrize('exc', [ArchonError, TimeoutError])
@pytest.mark.parametrize('fail_on, land', [
    ('FirstFlush=1', False),     # 올림 쓰기 자체 -- 안 앉았다
    ('FirstFlush=1', True),      # 올림 쓰기 자체 -- 앉았는데 답을 잃었다
    ('=IntMS=', False),
    ('=NoIntMS=', True),
    ('=Exposures=', False),
    ('LOADPARAMS', False),
])
def test_a_failure_before_the_exposure_is_armed_puts_it_back(fail_on, land, exc):  # noqa: ANN001
    """⭐ 원래 예외가 **그대로** 올라오고, 되돌림이 나가고, 표는 없다(노출이 안 걸렸다)."""
    ctrl = Ctrl(fail_on=fail_on, land=land, fail_exc=exc)
    with pytest.raises(exc) as got:
        asyncio.run(_trigger(ctrl, first_flush=1))
    assert fail_on.strip('=') in str(got.value), '원래 예외가 가려졌다: %s' % got.value
    _ends_clean(ctrl)
    assert ctrl._pending_restore == {}           # noqa: SLF001  되돌림은 성공했다
    assert ctrl._queue == [] and ctrl.current_ticket is None   # noqa: SLF001


def test_after_a_failed_raise_the_next_frame_raises_and_puts_back_again():
    """⛔ 올림 쓰기가 깨진 뒤에도 캐시가 1 로 남지 않는다 -- 다음 `trigger(first_flush=1)`
    가 다시 **올리고 · 싣고 · 되돌린다**."""
    ctrl = Ctrl(fail_on='FirstFlush=1', land=True)
    with pytest.raises(ArchonError):
        asyncio.run(_trigger(ctrl, first_flush=1))
    ctrl.sent.clear()
    asyncio.run(_trigger(ctrl, first_flush=1))
    assert _p0_writes(ctrl) == [_slot_write(ctrl, 'FirstFlush=1'),
                                _slot_write(ctrl, 'FirstFlush=0')], ctrl.sent
    up = ctrl.sent.index(_slot_write(ctrl, 'FirstFlush=1'))
    assert up < ctrl.sent.index('LOADPARAMS') < ctrl.sent.index(
        _slot_write(ctrl, 'FirstFlush=0')), ctrl.sent
    _ends_clean(ctrl)


class _HangCtrl(Ctrl):
    """`hang_on` 글자가 든 명령에서 `release` 가 설 때까지 멈춘다 -- 진짜 취소를 걸 자리."""

    def __init__(self, hang_on: str, **kw) -> None:  # noqa: ANN003
        super().__init__(**kw)
        self.hang_on = hang_on
        self.release = asyncio.Event()

    async def cmd(self, command: str, timeout: float = 0.0) -> bytes:  # noqa: ANN001
        if self.hang_on and self.hang_on in command:
            self.hang_on = ''                      # 한 번만 멈춘다
            self.sent.append('(hang) ' + command)
            await self.release.wait()
            self.sent.pop(self.sent.index('(hang) ' + command))
        return await super().cmd(command, timeout)


async def _until(pred, what: str) -> None:  # noqa: ANN001
    for _ in range(500):
        if pred():
            return
        await asyncio.sleep(0.01)
    raise AssertionError('%s 를 못 봤다' % what)


def test_an_abort_during_loadparams_still_puts_it_back():
    """⭐ **진짜 취소** -- LOADPARAMS 가 도는 중에 태스크를 끊는다(ABORT 의 `_task.cancel()`).
    취소가 그대로 올라오고, 되돌림은 나간다."""
    async def run():  # noqa: ANN202
        ctrl = _HangCtrl('LOADPARAMS')
        task = asyncio.ensure_future(_trigger(ctrl, first_flush=1))
        await _until(lambda: '(hang) LOADPARAMS' in ctrl.sent, 'LOADPARAMS')
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return ctrl
    ctrl = asyncio.run(run())
    _ends_clean(ctrl)
    assert ctrl._pending_restore == {}           # noqa: SLF001


def test_a_second_cancel_does_not_cut_the_put_back():
    """⭐ ABORT 위에 종료가 겹친다 -- 되돌림 왕복 **도중**에 또 취소가 와도 왕복은 뒤에서
    끝까지 간다(`asyncio.shield`).  결과를 모르므로 표시는 남고, 다음 LOADPARAMS 앞에서
    한 번 더 쓴다(멱등)."""
    async def run():  # noqa: ANN202
        ctrl = _HangCtrl('FirstFlush=0')           # 되돌림 WCONFIG 에서 멈춘다
        task = asyncio.ensure_future(_trigger(ctrl, first_flush=1))
        await _until(lambda: any(s.startswith('(hang) ') for s in ctrl.sent), '되돌림')
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        # 노출은 이미 걸렸다 -- 표는 대기열에 있다.
        assert ctrl.current_ticket is not None and ctrl._queue   # noqa: SLF001
        assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001
        ctrl.release.set()
        await _until(lambda: ctrl.flag() == 'FirstFlush=0', '뒤에서 끝난 되돌림')
        # 다음 프레임 -- 남은 표시를 LOADPARAMS 앞에서 비운다.
        ctrl.sent.clear()
        await _trigger(ctrl)
        return ctrl
    ctrl = asyncio.run(run())
    assert ctrl.sent[0] == _slot_write(ctrl, 'FirstFlush=0'), ctrl.sent
    assert ctrl.sent.index(ctrl.sent[0]) < ctrl.sent.index('LOADPARAMS')
    assert ctrl._pending_restore == {}           # noqa: SLF001
    _ends_clean(ctrl)


def test_a_failed_put_back_does_not_kill_the_armed_exposure(caplog):  # noqa: ANN001
    """⛔ LOADPARAMS 가 성공했으면 노출은 **이미 돈다** -- 되돌림 하나가 실패했다고
    *"개시 실패"* 로 바꾸면 그 프레임은 파일 없이 사라진다.  표를 돌려주고, 오류 한 줄 +
    `config_dirty` + `_pending_restore` 를 남기고, 다음 LOADPARAMS 앞에서 다시 쓴다."""
    ctrl = Ctrl(fail_on='FirstFlush=0')
    with caplog.at_level(logging.ERROR, logger='ics_archon.ctrl'):
        ticket = asyncio.run(_trigger(ctrl, first_flush=1))
    assert ticket is ctrl.current_ticket and ctrl._queue == [ticket]   # noqa: SLF001
    assert ctrl.config_dirty is True
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001
    errs = [r for r in caplog.records if 'could not be put back' in r.getMessage()]
    assert errs, caplog.text
    assert '노출은 이미 걸렸다' in errs[0].detail, errs[0].detail     # 부르는 쪽이 준 사정
    assert ctrl.flag() == 'FirstFlush=1', '가짜가 되돌림을 거절했으니 메모리는 1 이다'

    # 다음 프레임(first_flush 없음) -- LOADPARAMS 앞에서 되쓴다.
    ctrl.release_current()
    ctrl.sent.clear()
    asyncio.run(_trigger(ctrl))
    assert ctrl.sent.index(_slot_write(ctrl, 'FirstFlush=0')) < ctrl.sent.index('LOADPARAMS')
    assert ctrl._pending_restore == {}           # noqa: SLF001
    _ends_clean(ctrl)


def test_a_failed_put_back_then_ccdflush_ends_at_zero():
    """되돌림 실패 뒤 `CCDFLUSH`(`flush_now`) -- `config_dirty` 가 되읽게 한 1 을 *"이미
    켜져 있다"* 로 보고 넘어가면 1 이 영구히 남는다.  먼저 되쓰고 판정한다."""
    ctrl = Ctrl(fail_on='FirstFlush=0')
    asyncio.run(_trigger(ctrl, first_flush=1))
    assert ctrl.flag() == 'FirstFlush=1'
    asyncio.run(ctrl.flush_now())
    _ends_clean(ctrl)
    assert ctrl._pending_restore == {}           # noqa: SLF001


@pytest.mark.parametrize('step, context', [
    ('LOADPARAMS', '노출이 걸렸는지 모른다'),      # 나갔는데 깨졌다 -- 앉았을 수 있다
    ('=IntMS=', '노출은 걸지 않았다'),            # LOADPARAMS 전에 깨졌다
])
def test_when_the_put_back_also_fails_the_original_error_wins(caplog, step, context):  # noqa: ANN001
    """그 걸음이 깨지고 되돌림도 깨진다 -- 올라오는 것은 **그 걸음의 예외**다.  오류 줄의
    사정은 부르는 쪽이 준다 -- ⛔ 종전 문면 *"이미 걸린 노출은 그대로 간다"* 는 노출을 걸기
    전에 깨진 이 경우에도 찍혔다."""
    ctrl = Ctrl(fail_on=(step, 'FirstFlush=0'), fail_times=2)
    with caplog.at_level(logging.ERROR, logger='ics_archon.ctrl'):
        with pytest.raises(ArchonError) as got:
            asyncio.run(_trigger(ctrl, first_flush=1))
    assert step.strip('=') in str(got.value), got.value
    assert ctrl.config_dirty is True
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001
    errs = [r for r in caplog.records if 'could not be put back' in r.getMessage()]
    assert errs, caplog.text
    assert context in errs[0].detail and '이미 걸렸다' not in errs[0].detail, errs[0].detail
    ctrl.sent.clear()
    asyncio.run(_trigger(ctrl))
    assert ctrl.sent.index(_slot_write(ctrl, 'FirstFlush=0')) < ctrl.sent.index('LOADPARAMS')
    _ends_clean(ctrl)


def test_a_retry_that_fails_again_refuses_to_arm():
    """되쓰기가 또 깨지면 **노출을 걸지 않는다** -- 아직 아무것도 안 걸었으니 GO 가
    깨끗하게 실패하는 편이 잘못된 설정으로 거는 것보다 낫다."""
    ctrl = Ctrl(fail_on='FirstFlush=0', fail_times=2)
    asyncio.run(_trigger(ctrl, first_flush=1))           # 되돌림 실패 (1회째)
    ctrl.release_current()
    ctrl.sent.clear()
    with pytest.raises(ArchonError):
        asyncio.run(_trigger(ctrl))                      # 되쓰기 실패 (2회째)
    assert 'LOADPARAMS' not in ctrl.sent and ctrl.loadparams_sent is False, ctrl.sent
    # ⭐ 올리기 전에 **되읽어 봤다** -- 메모리가 정말 1 이라 막는 것이다.
    assert any(c.startswith('RCONFIG') for c in ctrl.sent), ctrl.sent
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001


# -- 되돌림이 같은 식으로 계속 깨져도 막다른 길이 아니다 (DevNote 11.96) ----------------
#
# ⛔ 종전에는 strict 되쓰기(`_retry_pending_restore`)가 실패하면 그대로 올렸다 -- 같은 식으로
# 깨지는 되쓰기 하나가 **메모리가 이미 원래 값인데도** 세션 내내 GO·CCDFLUSH 를 막았다.
# 이제 실패하면 `RCONFIG` 로 되읽어 원래 값이면 표시를 지우고 간다.


def _refused(message: str) -> ArchonError:
    """`?NN` 거부 꼴 -- 컨트롤러가 명령을 거절했다(스트림은 멀쩡하다)."""
    return ArchonError(message, reply_error=True)


def test_a_refused_raise_and_a_refused_put_back_leave_nothing_pending(caplog):  # noqa: ANN001
    """⭐ 올림 쓰기가 거부되고 되돌림도 거부된다 -- 올림이 안 앉았으니 메모리는 원래 값이다.
    `_put_back` 이 **곧바로 되읽어**(거부는 스트림이 멀쩡하다) 표시를 안 남기고, 다음 장은
    되쓰기 없이 정상으로 건다."""
    ctrl = Ctrl(fail_on=('FirstFlush=1', 'FirstFlush=0'), fail_times=2, fail_exc=_refused)
    with caplog.at_level(logging.WARNING, logger='ics_archon.ctrl'):
        with pytest.raises(ArchonError) as got:
            asyncio.run(_trigger(ctrl, first_flush=1))
    assert 'FirstFlush=1' in str(got.value), '원래 예외(올림 거부)가 가려졌다: %s' % got.value
    assert ctrl._pending_restore == {}           # noqa: SLF001
    assert any('already holds it' in r.getMessage() for r in caplog.records), caplog.text
    assert not any('could not be put back' in r.getMessage() for r in caplog.records)

    ctrl.sent.clear()
    ticket = asyncio.run(_trigger(ctrl))
    assert ticket is ctrl.current_ticket, '다음 장이 걸리지 않았다'
    assert _p0_writes(ctrl) == [] and ctrl.loads() == ['LOADPARAMS'], ctrl.sent
    assert ctrl.flag() == 'FirstFlush=0'


def test_a_put_back_that_keeps_failing_is_dropped_once_memory_holds_it(caplog):  # noqa: ANN001
    """⭐ 되돌림이 **앉는데 답만 잃는다**(시한 초과 꼴) -- 두 번 다.  첫 실패는 스트림이 깨졌을
    수 있어 표시를 남기고, 다음 장의 strict 되쓰기가 또 깨지면 `RCONFIG` 로 되읽어 원래 값임을
    확인하고 **노출을 건다**."""
    ctrl = Ctrl(fail_on='FirstFlush=0', fail_times=2, land=True)
    asyncio.run(_trigger(ctrl, first_flush=1))           # 되돌림 실패 (1회째, 앉았다)
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001
    assert ctrl.flag() == 'FirstFlush=0', '가짜는 앉힌 뒤 던졌다 -- 메모리는 원래 값이다'
    ctrl.release_current()
    ctrl.sent.clear()
    with caplog.at_level(logging.WARNING, logger='ics_archon.ctrl'):
        ticket = asyncio.run(_trigger(ctrl))             # 되쓰기 실패 (2회째) -> 되읽기 -> 간다
    assert ticket is ctrl.current_ticket, '메모리가 멀쩡한데 GO 가 막혔다'
    assert ctrl.loads() == ['LOADPARAMS'], ctrl.sent
    reread = next(i for i, c in enumerate(ctrl.sent) if c.startswith('RCONFIG'))
    assert reread < ctrl.sent.index('LOADPARAMS'), ctrl.sent
    assert ctrl._pending_restore == {}           # noqa: SLF001
    assert any('already holds it -- going on' in r.getMessage()
               for r in caplog.records), caplog.text


def test_a_bypass_write_after_a_failed_put_back_leaves_memory_to_the_operator(caplog):  # noqa: ANN001
    """⭐ 되돌림이 실패한 뒤 운영자가 `ARCHON WCONFIG…` 로 그 줄을 직접 썼다 -- 표시를 비우고
    (로그 한 줄), 다음 장은 운영자 값을 **덮지 않는다** (DevNote 11.96).  ⚠️ 거부된 바이패스는
    메모리를 안 바꿨으니 표시를 남긴다."""
    ctrl = Ctrl(fail_on='FirstFlush=0')              # 되돌림만 실패 -- 메모리는 1
    asyncio.run(_trigger(ctrl, first_flush=1))
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001
    ctrl.release_current()

    ctrl.fail_on, ctrl.fail_times, ctrl.fail_exc = ('FirstFlush=2',), 1, _refused
    with pytest.raises(ArchonError):
        asyncio.run(ctrl.raw_command(_slot_write(ctrl, 'FirstFlush=2')))
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001

    with caplog.at_level(logging.WARNING, logger='ics_archon.ctrl'):
        asyncio.run(ctrl.raw_command(_slot_write(ctrl, 'FirstFlush=2')))
    assert ctrl._pending_restore == {}           # noqa: SLF001
    assert any('dropping the pending put-back' in r.getMessage()
               for r in caplog.records), caplog.text

    ctrl.sent.clear()
    asyncio.run(_trigger(ctrl))
    assert _p0_writes(ctrl) == [], '운영자 값을 덮었다: %r' % ctrl.sent
    assert ctrl.flag() == 'FirstFlush=2'


def test_a_bypass_write_to_another_line_keeps_the_pending_put_back(caplog):  # noqa: ANN001
    """⭐ 바이패스 `WCONFIG` 는 **그 줄만** 운영자에게 넘긴다 -- 다른 줄(여기서는 `IntMS`)을 쓴
    바이패스가 `FirstFlush` 의 못 되돌린 표시까지 비우면 설정 메모리에 1 이 남아 science 가
    **매 장** flush 를 돈다.  다음 장이 LOADPARAMS 앞에서 엄격히 되쓴다."""
    ctrl = Ctrl(fail_on='FirstFlush=0')              # 되돌림만 실패 -- 메모리는 1
    asyncio.run(_trigger(ctrl, first_flush=1))
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001
    ctrl.release_current()

    islot = ctrl.param_slots['IntMS']
    assert ctrl.configline[islot] != ctrl.configline['PARAMETER0']
    bypass = 'WCONFIG%04X%s=IntMS=5' % (ctrl.configline[islot], islot)
    with caplog.at_level(logging.WARNING, logger='ics_archon.ctrl'):
        asyncio.run(ctrl.raw_command(bypass))
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001
    assert not any('dropping the pending put-back' in r.getMessage()
                   for r in caplog.records), caplog.text

    ctrl.sent.clear()
    asyncio.run(_trigger(ctrl))
    assert ctrl.sent[0] == _slot_write(ctrl, 'FirstFlush=0'), '판정보다 먼저 되써야 한다'
    assert ctrl.flag() == 'FirstFlush=0', ctrl.sent
    assert ctrl._pending_restore == {}           # noqa: SLF001


def test_stop_still_goes_out_when_the_retry_fails(caplog):  # noqa: ANN001
    """⚠️ STOP 길(`set_exposures`)은 되쓰기가 깨져도 **멈추지 않는다** -- 되쓰기는
    `Exposures=0` 의 LOADPARAMS **뒤**다(DevNote 11.96, 멈춤을 늦추지 않는다).  경고만
    하고 표시는 둔다 -- 다음 GO 가 LOADPARAMS 앞에서 엄격히 다시 쓴다."""
    ctrl = Ctrl(fail_on='FirstFlush=0', fail_times=2)
    asyncio.run(_trigger(ctrl, first_flush=1))
    ctrl.sent.clear()
    with caplog.at_level(logging.WARNING, logger='ics_archon.ctrl'):
        asyncio.run(ctrl.set_exposures(0))
    assert ctrl.loads() == ['LOADPARAMS'], ctrl.sent
    assert ctrl.sent.index('LOADPARAMS') < ctrl.sent.index(
        _slot_write(ctrl, 'FirstFlush=0')), '되쓰기가 멈춤보다 앞섰다: %r' % ctrl.sent
    assert any('the stop went out anyway' in r.getMessage()
               for r in caplog.records), caplog.text
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001


def test_abort_cuts_first_and_puts_back_after_resettiming():
    """⭐ ABORT(`abort_now`)는 **`RESETTIMING` 뒤에** 되쓴다 -- 끊는 것은 `RESETTIMING`
    이라 그 앞에 왕복을 끼우면 셔터가 그만큼 늦게 닫힌다 (DevNote 11.96)."""
    ctrl = Ctrl(fail_on='FirstFlush=0')              # 되돌림만 실패 -- 표시가 남는다
    asyncio.run(_trigger(ctrl, first_flush=1))
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001
    ctrl.sent.clear()
    asyncio.run(ctrl.abort_now())
    back = ctrl.sent.index(_slot_write(ctrl, 'FirstFlush=0'))
    assert ctrl.sent.index('LOADPARAMS') < ctrl.sent.index('RESETTIMING') < back, ctrl.sent
    assert ctrl._pending_restore == {}           # noqa: SLF001
    _ends_clean(ctrl)


class _TimedCtrl(Ctrl):
    """명령마다 다른 `last_cmd_timing` 을 심는다 -- `DATE-OBS` 가 어느 왕복에서 오나."""

    async def cmd(self, command: str, timeout: float = 0.0) -> bytes:  # noqa: ANN001
        out = await super().cmd(command, timeout)
        self.last_cmd_timing = ((100.0, 100.2, 1000.0) if command == 'LOADPARAMS'
                                else (200.0, 200.001, 2000.0))
        return out


def test_the_arm_time_is_the_loadparams_round_trip_not_the_put_back():
    """⛔ 되돌림 `WCONFIG` 도 `last_cmd_timing` 을 덮는다 -- LOADPARAMS **곧바로** 읽지
    않으면 `DATE-OBS`(`armed_utc`)가 되돌림 왕복 시각이 된다."""
    ctrl = _TimedCtrl()
    ticket = asyncio.run(_trigger(ctrl, first_flush=1))
    assert ctrl.sent[-1] == _slot_write(ctrl, 'FirstFlush=0'), '되돌림이 마지막이어야 한다'
    assert ticket.armed_mono == pytest.approx(100.1)
    assert ticket.armed_utc == pytest.approx(1000.1)
    assert ticket.arm_rtt == pytest.approx(0.2)


def test_the_trigger_put_back_is_in_a_finally():
    """소스 수준 확인 -- 되돌림이 `finally` 안에 있고, 표가 그보다 **먼저** 대기열에 든다."""
    import inspect
    src = inspect.getsource(ArchonController.trigger)
    fin = src.index('        finally:')
    assert src.index('self._queue.append(ticket)') < fin < src.index(
        'self._put_back(*restore'), src


# -- backend: 둘을 잇는다 ------------------------------------------------------


class _Gauge:
    def __init__(self, answers) -> None:  # noqa: ANN001
        self._answers = list(answers)

    def take_flush_request(self) -> bool:
        return self._answers.pop(0) if self._answers else False


def test_the_backend_asks_once_per_frame_and_passes_one_or_none():
    be = ArchonBackend.__new__(ArchonBackend)
    be.gauge = _Gauge([True, False])
    assert be._first_flush_for_this_frame() == 1        # noqa: SLF001  첫 장
    assert be._first_flush_for_this_frame() is None     # noqa: SLF001  둘째 장
    be.gauge = None
    assert be._first_flush_for_this_frame() is None     # noqa: SLF001  게이지 제어 없음


def test_trigger_signature_accepts_first_flush():
    """배선 확인 -- 백엔드가 넘기는 키워드를 컨트롤러가 받는다."""
    import inspect
    assert 'first_flush' in inspect.signature(ArchonController.trigger).parameters


# -- 끝단: 셔터 경로 (`open_shutter`) 가 실제로 싣는가 (DevNote 11.96) ----------
#
# ⚠️ DARK 경로(`_readout_stream`)는 `test_ics_ops_commands.py` 의 예열 GO 가 이미 본다
# (ICG 가 없어 추적 상태가 UNKNOWN -> `VACGAUGE OFF` -> `flushes == 1`).  셔터 경로는
# 앱 수준에서 `flushes` 를 세는 시험이 없어서, `open_shutter` 의 `first_flush=` 를 빼도
# 떨어지는 시험이 없었다.


def _shutter_go(tmp_path, vacgauge: str):  # noqa: ANN001, ANN202
    """예열 뒤 `object`·`exp 1`·`go 2` 를 넣고 ICG 의 `HKDATA` 답에 `VACGAUGE=<vacgauge>`
    를 준다.  `(MK flush 증가, NT flush 증가, MK FirstFlush 줄, NT FirstFlush 줄, 보낸 줄)`."""
    from test_hk_wire import REPLY
    from test_ics_ops_commands import Session, flush_flag, until

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            # ⚠️ 답을 기다리는 창은 `hk_query_timeout x time_scale`(2.0 x 0.02 = 40 ms)
            # 라 부하가 있으면 이 시험의 답이 늦는다 -- 창을 1 s 로 넓힌다.  답이 오면
            # 곧바로 끝나므로 시간은 늘지 않는다.
            ses.app.acfg.hk_query_timeout = 50.0
            mk0, nt0 = ses.mk.flushes, ses.nt.flushes
            n = len(ses.sent)
            for line in ('abc>ICS object M31', 'abc>ICS exp 1', 'abc>ICS go 2'):
                ses.app.transport.feed(line)
                await asyncio.sleep(0.02)
            await until(lambda: any('ICG HKDATA NOW' in s for s in ses.sent[n:]),
                        what='GO 의 HKDATA NOW')
            ses.app.transport.feed('ICG>ICS DONE: HKDATA ' + REPLY % vacgauge)
            await ses.app.seq.wait()
            await asyncio.sleep(0.3)
            return (ses.mk.flushes - mk0, ses.nt.flushes - nt0,
                    flush_flag(ses.mk), flush_flag(ses.nt), ses.sent[n:])
    return asyncio.run(run())


def test_the_shutter_path_flushes_once_before_the_first_frame(tmp_path):  # noqa: ANN001
    """⭐ `VACGAUGE=ON` 답 -> `VACGAUGE OFF` -> **두 장인데 flush 는 컨트롤러마다 한 번**
    (첫 장만), 끝나면 설정 메모리는 `FirstFlush=0` 이다."""
    dmk, dnt, fmk, fnt, sent = _shutter_go(tmp_path, 'ON')
    assert [s for s in sent if 'ICG VACGAUGE OFF' in s], sent
    assert (dmk, dnt) == (1, 1), '셔터 경로의 첫 장 flush 가 한 번씩이어야 한다: %r' % ((dmk, dnt),)
    assert fmk == fnt == 'PARAMETER0=FirstFlush=0', (fmk, fnt)


def test_the_shutter_path_does_not_flush_when_the_gauge_was_already_off(tmp_path):  # noqa: ANN001
    """짝 -- `VACGAUGE=OFF` 답이면 안 보내고 flush 도 없다."""
    dmk, dnt, fmk, _fnt, sent = _shutter_go(tmp_path, 'OFF')
    assert not [s for s in sent if 'ICG VACGAUGE OFF' in s], sent
    assert (dmk, dnt) == (0, 0), (dmk, dnt)
    assert fmk == 'PARAMETER0=FirstFlush=0', fmk

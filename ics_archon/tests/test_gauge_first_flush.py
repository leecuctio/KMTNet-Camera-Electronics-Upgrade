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
  LOADPARAMS 라 설정값을 남겨 두면 매 장 flush 가 된다.
* `ArchonBackend._first_flush_for_this_frame()` -- 둘을 잇는다 (두 컨트롤러에 같은 값).
"""

from __future__ import annotations

import asyncio

import ics_archon  # noqa: F401

from ics_archon.archon.backend import ArchonBackend  # noqa: E402
from ics_archon.archon.controller import ArchonController  # noqa: E402

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

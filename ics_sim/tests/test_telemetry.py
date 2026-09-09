#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TC 중계(`telemetry.py`)의 **파생값** 회귀.

⭐ **이 파일이 있는 이유**: 벤치에서 guide 헤더의 `DSAZ`/`DSTELAZ`/`DAZERR` 이
`NC` 로 나왔는데, 원인은 결함이 아니라 **TC 가 방위를 안 보내는 것**이었다
(2026-09-08).  운영자가 실기 TC 담당자와 정한 결론이 이 파일의 못박음이다:

* `DSAZ` 와 `DSTELAZ` 는 **둘 다 `TCSSTATUS` 에 추가**된다 (TC 쪽 구현 대기).
  ⭐ 그때까지 우리가 할 일은 없다 -- 오면 실리고 없으면 `'NC'` 다.
* `DAZERR = DSAZ - DSTELAZ` 를 **-180 ~ +180 으로 접는다**.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                os.pardir)))

# -- 돔 방위 (운영자 확정 2026-09-09) --------------------------------------

def test_azimuth_is_not_borrowed_from_the_telescope_az():
    """⛔ `AZ` 를 `DSTELAZ` 로 **개명하지 않는다** (운영자 정정 2026-09-09).

    `DSAZ`·`DSTELAZ` 는 **둘 다 TC 가 `TCSSTATUS` 로 보낸다** -- 구현 전까지는
    `'NC'` 로 남는 것이 맞다.  ⚠️ 한때 *"돔 Az 를 TCS 가 모니 `AZ` 를 그대로
    쓰자"* 로 정했다가 되돌린 자리라, 다시 끌어다 쓰지 않도록 못박는다.
    ⭐ 고도는 다르다 -- `DSTEL`(DS 가 보고) -> `DSTELALT` 개명은 유지된다.
    """
    from ics_sim import telemetry
    assert 'AZ' not in telemetry._FITS_RENAME
    assert telemetry._FITS_RENAME['DSTEL'] == 'DSTELALT'


def test_azimuth_error_folds_into_plus_minus_180():
    """⭐ `DAZERR` 는 **-180 ~ +180 으로 접는다** (운영자: 270 -> -90).

    ⛔ 방위는 순환이라 그냥 빼면 반대 방향이 큰 값으로 보인다.
    """
    from ics_sim.telemetry import _sync_error_az as az
    assert az('270', '0') == '-90.0'
    assert az('0', '270') == '+90.0'
    assert az('10.5', '3.0') == '+7.5'
    assert az('359', '1') == '-2.0'
    assert az('1', '359') == '+2.0'
    assert az(None, '3') == 'NC'
    assert az('x', '3') == 'NC'


def test_altitude_error_is_not_folded():
    """⛔ 고도에는 접기를 쓰지 않는다 -- 순환이 아니라 그냥 큰 어긋남이다."""
    from ics_sim.telemetry import _sync_error
    assert _sync_error('270', '0') == '+270.0'

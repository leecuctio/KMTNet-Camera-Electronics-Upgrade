#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TC 중계(`telemetry.py`)의 **파생값** 회귀.

⭐ **이 파일이 있는 이유**: 벤치에서 guide 헤더의 `DSAZ`/`DSTELAZ`/`DAZERR` 이
`NC` 로 나왔는데, 원인은 결함이 아니라 **TC 가 방위를 안 보내는 것**이었다
(2026-09-08).  ⭐ 그 사실은 레거시 원천이 확증한다 -- `TCSAgent` 트리 전체에
`DSAZ`/`DSTELAZ` 가 **0건**이고 돔 블록이 내는 것은 고도(`DSALT`/`DSTEL`)뿐이다
(`TCSAgent/TCSAgent.latest/KMTNet/commands.c:2834`).

⭐⭐ **출처가 정해졌다 (운영자 확정 2026-09-11)**: 방위 셋은 **돔 제어
프로그램의 redis** 에서 읽는다 (`ics_sim/domeaz.py` · `[dome] source`).
종전에 *"TC 가 `TCSSTATUS` 에 추가할 때까지 우리가 할 일은 없다"* 로 적혀
있던 자리다.  redis 경로의 시험은 `tests/test_dome_redis.py` 에 있고, 이
파일은 **파생값 계산과 개명 금지**만 못박는다:

* `DAZERR = DSAZ - DSTELAZ` 를 **-180 ~ +180 으로 접는다** (redis 가
  `dome_del_az` 를 안 줄 때 쓰는 계산).
* `DALTERR` 는 **고도** 어긋남이고 접지 않는다 -- redis 와 무관하다.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                os.pardir)))

# -- 돔 방위 (운영자 확정 2026-09-09 · 출처 2026-09-11) --------------------

def test_azimuth_is_not_borrowed_from_the_telescope_az():
    """⛔ `AZ` 를 `DSTELAZ` 로 **개명하지 않는다** (운영자 정정 2026-09-09).

    `DSTELAZ` 는 **DS(돔)가 보고하는 망원경 방위**라 망원경 자신의 `AZ` 와
    다른 값이다 (견본에서도 `AZ='-0.3'` vs `DSTELAZ='12.1'`).  ⚠️ 한때 *"돔 Az
    를 TCS 가 모니 `AZ` 를 그대로 쓰자"* 로 정했다가 되돌린 자리라, 다시
    끌어다 쓰지 않도록 못박는다.
    ⭐ 출처가 redis 로 정해진 뒤에도(2026-09-11) 이 금지는 그대로다 -- 오히려
    구조적으로 굳었다: 방위는 `domeaz` 만 채운다.
    ⭐ 고도는 다르다 -- `DSTEL`(DS 가 보고) -> `DSTELALT` 개명은 유지된다.
    """
    from ics_sim import telemetry
    assert 'AZ' not in telemetry._FITS_RENAME
    assert telemetry._FITS_RENAME['DSTEL'] == 'DSTELALT'


def test_canned_telemetry_does_not_invent_a_dome_azimuth():
    """⛔ canned 가 *"TC 가 방위를 중계한다"* 를 모사하지 않는다 (2026-09-11).

    종전에는 `DSAZ='12.3'`·`DSTELAZ='12.1'` 을 지어내 넣었다.  ⭐ 그런데 TC 는
    방위를 **아예 보내지 않는다** (`TCSAgent` 트리에 0건) -- 방위의 원천은
    redis 다.  ⭐ **고도는 남는다**: `DSALT`/`DSTELALT` 는 실제로 오는 값이다.
    """
    from ics_sim import telemetry
    assert 'DSAZ' not in telemetry.CANNED_TCS
    assert 'DSTELAZ' not in telemetry.CANNED_TCS
    assert 'DSAZ' not in telemetry.CANNED_TCS_VALUES
    assert 'DSTELAZ' not in telemetry.CANNED_TCS_VALUES
    assert telemetry.CANNED_TCS_VALUES['DSALT'] == '87.7'
    assert telemetry.CANNED_TCS_VALUES['DSTELALT'] == '88.1'


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

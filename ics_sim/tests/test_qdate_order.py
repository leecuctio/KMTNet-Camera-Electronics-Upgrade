#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raw spec **5.7.1절** -- `QDATE`/`UDATE` 순서 규약 (normative).

v1.5 가 신설한 절이고, 같은 판에서 `aux_requery_after_shopen` 이 **3초에서
1초로** 내려갔다.  그 값은 지연일 뿐 아니라 **재질의가 걸리는 노출 문턱**이라,
내리는 순간 "어떤 노출이 노출 중 셔터 상태를 싣는가" 의 경계가 함께 움직인다.
그런데 그 문턱을 밟는 시험이 **하나도 없었다** -- 값만 바꿔도 조용히 지나간다.

이 파일이 다루는 것:

1. **`UDATE` ≤ `QDATE`** -- TC 원전 정의에서 구조적으로 따라 나온다
   (`*QDATE` = TC 가 응답을 조립하는 순간, `*UDATE` = 텔레메트리 패킷을
   마지막으로 받은 시각).  ICS 가 강제하는 규칙은 아니지만, **ICS 가 직접
   채우는 유일한 경로**(TC 무응답 폴백)에서는 우리 몫이다.
2. **재질의 문턱** -- `EXPTIME <= aux_requery_after_shopen` 이면 재질의하지
   않는다.  셔터가 이미 닫힌 뒤의 값을 노출 중 값이라고 싣게 되기 때문이다.
3. **DARK/BIAS 는 이 경로를 아예 지나지 않는다** (셔터를 안 여니 기다릴 것이
   없다) -- 5.7.1절 (c) 표의 첫 줄.
"""

from __future__ import annotations

import asyncio

import pytest

from ics_sim import telemetry
from ics_sim.config import SimConfig
from ics_sim.sequencer import Sequencer


def _sequencer(delay: float) -> Sequencer:
    """`_spawn_aux_requery` 의 문턱만 보려는 최소 조립.

    시퀀서 전체를 돌리지 않는다 -- 문턱은 순수 판정이라 그 판정만 밟으면
    되고, 전체를 돌리면 실패했을 때 원인이 어디인지 흐려진다.
    """
    cfg = SimConfig()
    cfg.timing.aux_requery_after_shopen = delay
    seq = Sequencer.__new__(Sequencer)      # __init__ 은 전송·상태를 요구한다
    seq.cfg = cfg
    return seq


# -- (a) UDATE <= QDATE ------------------------------------------------------

@pytest.mark.parametrize('key, q, u', [
    ('AUXSTATUS', 'AUXQDATE', 'AUXUDATE'),
    ('TCSSTATUS', 'TCSQDATE', 'TCSUDATE'),
])
def test_canned_fallback_never_stamps_udate_after_qdate(key, q, u):
    """TC 무응답 폴백은 **ICS 가 두 시각을 직접 찍는 유일한 자리**다.

    거꾸로 찍으면 raw 를 읽는 쪽이 전제해도 된다고 규격이 말한 부등식이
    우리 산출물에서만 깨진다 -- 그리고 그 파일들은 "TC 가 죽어 있었다" 는
    사실을 가장 확인하고 싶은 파일이다.
    """
    cfg = SimConfig()
    cfg.timing.tc_timeout_mode = 'canned'
    relay = telemetry.TelemetryRelay(cfg, lambda *a, **k: None)
    relay._apply_timeout(key)
    fields = dict(relay.aux_fields if key == 'AUXSTATUS' else relay.tcs_fields)
    assert fields.get(q), f'{q} 가 비었다 -- 폴백이 시각을 안 찍었다'
    assert fields.get(u), f'{u} 가 비었다'
    assert fields[u] <= fields[q], (
        f'{u}({fields[u]}) 가 {q}({fields[q]}) 보다 뒤다 -- 5.7.1절 (a) 위반. '
        'ISO 문자열은 사전순 비교가 곧 시각 비교다')


# -- (c) 재질의 문턱 ---------------------------------------------------------

@pytest.mark.parametrize('exptime, expect', [
    (0.5, False),    # 문턱 아래 -- 개시 직전 값을 그대로 쓴다
    (1.0, False),    # **경계는 포함**이다 (`exptime <= delay`)
    (1.001, True),   # 경계를 넘으면 재질의
    (30.0, True),
])
def test_requery_threshold_is_the_delay_itself(exptime, expect):
    """`EXPTIME <= aux_requery_after_shopen` 이면 재질의하지 않는다.

    ⚠️ **이 값은 지연이자 문턱이다.**  v1.5 에서 3초 -> 1초로 내리면서
    "개시 직전 값을 그대로 쓰는 구간" 이 3초 이하에서 **1초 이하**로 좁아졌다.
    다음에 이 값을 다시 만질 사람이 그 두 번째 뜻을 모르고 바꾸면, 어떤 노출이
    노출 중 셔터 상태를 싣는지가 조용히 달라진다.
    """
    seq = _sequencer(1.0)

    async def _ask() -> bool:
        # `create_task` 는 돌고 있는 루프를 요구한다 -- 실제 호출 자리도
        # 시퀀서 코루틴 안이므로 같은 조건에서 본다.
        task = seq._spawn_aux_requery(exptime)
        if task is None:
            return False
        task.cancel()
        return True

    assert asyncio.run(_ask()) is expect, (
        f'EXPTIME={exptime} · delay=1.0 에서 재질의 '
        f'{"해야" if expect else "하지 말아야"} 한다 (5.7.1절 (c) 표)')


def test_requery_can_be_turned_off_with_a_non_positive_delay():
    """`0` 이하면 갱신하지 않는다 -- ini 주석이 약속한 탈출구다."""
    async def _ask(delay: float):
        return _sequencer(delay)._spawn_aux_requery(30.0)

    for delay in (0.0, -1.0):
        assert asyncio.run(_ask(delay)) is None


def test_the_shipped_default_matches_the_spec():
    """기본값이 규격 5.7.1절의 **1초**여야 한다.

    3초로 되돌아가면 (c) 표의 `EXPTIME` 문턱도 함께 되돌아간다 -- 규격을
    고치지 않고 코드만 바꾸는 것이 그래서 위험하다 (OI-13).
    """
    assert SimConfig().timing.aux_requery_after_shopen == 1.0


def test_the_shipped_ini_agrees_with_the_default():
    """`ics_sim.ini` 가 코드 기본값과 **같은 값**을 적어야 한다.

    ⚠️ 이 값은 두 자리에 적혀 있다 -- 데이터클래스 기본값과 배포 ini.  운영은
    ini 를 읽으므로 **ini 가 낡으면 코드만 고친 것이 아무 효과가 없다.**
    실제로 v1.5 반영 때 `ics_archon.ini` 쪽이 `3.0` 으로 남아 있었다.
    """
    import configparser
    import pathlib

    ini = pathlib.Path(__file__).resolve().parents[1] / 'ics_sim.ini'
    assert ini.exists(), f'배포 ini 가 없다 ({ini})'
    cp = configparser.ConfigParser(inline_comment_prefixes=('#',))
    cp.read(ini, encoding='utf-8')
    got = cp['timing'].getfloat('aux_requery_after_shopen')
    assert got == SimConfig().timing.aux_requery_after_shopen == 1.0, (
        f'{ini.name} 의 aux_requery_after_shopen 이 {got} 다 -- 규격 5.7.1절의 '
        '1.0 과 어긋나면 재질의 문턱이 함께 어긋난다')

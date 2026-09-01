#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACF 타이밍 계산 -- guide 프레임 주기·트랜스퍼 지연.

근거는 `icg_archon/acftiming.py` 머리말 (실측 ACF 의 채널 라벨과 상태
정의로 확정한 노출 경계).  이 시험이 지키는 것은 셈법의 **자체 검산 앵커**와
실물 guide ACF 에서 나오는 값의 자릿수다 -- 정확한 실측은 첫 구동 몫이다.
"""

from __future__ import annotations

import os

import pytest

import ics_archon  # noqa: F401

from icg_archon import acftiming  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE_ACF = os.path.join(ROOT, 'acf', 'KMTK_GUI_162_STA0201_R2608.acf')


def test_tick_anchor_holds():
    """`NoIntUnit` 이 정확히 1 ms (=100,000 틱)여야 한다.

    ⭐ 이것이 틱 가정(100 MHz)과 행당 셈법을 **동시에** 검산한다 --
    스크립트가 그 값이 되도록 보정돼 있어서(파라미터 이름이 `NoIntMS` 다),
    어긋나면 둘 중 하나가 틀린 것이고 프레임 주기 계산 전체를 못 믿는다.
    """
    assert acftiming.verify_tick_anchor()


def test_parameters_parses_the_acf_form():
    got = acftiming.parameters({
        'PARAMETER2': '"IntMS=1000"', 'PARAMETER3': 'NoIntMS=500',
        'PARAMETER13': '"AT=100"', 'MOD3\\LABEL1': 'S1'})
    assert got == {'IntMS': 1000, 'NoIntMS': 500, 'AT': 100}


@pytest.mark.repo_only
def test_guide_acf_frame_period():
    """실물 guide ACF -- 최소 주기·트랜스퍼 지연이 예상 자릿수인가.

    폭이 아니라 **자릿수**를 본다 (계산이라 몇 % 는 어긋날 수 있다).
    이 시험이 잡으려는 것은 ACF 개정으로 주기가 통째로 달라지는 경우다 --
    그때는 `exptime_min` 대체값과 DevNote 9 의 수치를 함께 고쳐야 한다.
    """
    from ics_archon.archon.controller import ArchonController
    from icg_archon.config import IcgCfg

    icfg = IcgCfg()
    icfg.acf = {'G': GUIDE_ACF}
    ctrl = ArchonController('G', icfg)
    ctrl.parse_acf(GUIDE_ACF)          # 왕복 없음

    p = acftiming.parameters(ctrl.config)
    assert p['NoIntMS'] == 500 and p['Lines'] == 1033 and p['Pixels'] == 600

    t = acftiming.frame_timing(p, lines=p['Lines'], pixels=p['Pixels'])
    # 트랜스퍼는 밀리초 오더 (1033행 x 6상 x AT) -- 스미어가 짧다는 근거.
    assert 0.004 < t['transfer'] < 0.010
    # 독출은 1초 오더.
    assert 1.0 < t['readout'] < 2.0
    # 최소 주기 = NoIntMS + 트랜스퍼 + 독출 ≈ 1.9 s.
    assert 1.7 < t['floor'] < 2.1
    # 트리거 -> 트랜스퍼 지연 ≈ NoIntMS + 트랜스퍼 ≈ 0.5 s (DATE-OBS 보정분).
    assert 0.45 < t['trigger_to_transfer'] < 0.60


@pytest.mark.repo_only
def test_backend_uses_the_acf_floor_not_the_ini_fallback():
    """`frame_floor()` 가 ACF 계산값을 쓰는가 -- ini 대체값이 아니라."""
    from ics_sim import config as simcfg

    from icg_archon.backend import GuideBackend
    from icg_archon.config import load

    ini = os.path.join(ROOT, 'icg_archon.ini')
    icfg = load(ini)
    icfg.acf = {'G': GUIDE_ACF}
    icfg.exptime_min = 0.1              # 대체값을 일부러 낮춰 둔다
    be = GuideBackend(simcfg.load(ini), icfg)
    assert be.timing is not None, 'ACF 타이밍을 못 읽었다'
    assert be.frame_floor() > 1.5, 'ini 대체값이 이기면 안 된다'
    assert be.trigger_to_transfer() > 0.4

    # ⭐ **ini 값이 계산값을 밀어 올리면 안 된다** -- ACF 를 고쳐 주기를
    # 줄여도(NoIntMS -> 0) 낡은 ini 하한이 정상 요청을 거부하던 자리다.
    icfg.exptime_min = 99.0
    be2 = GuideBackend(simcfg.load(ini), icfg)
    assert be2.frame_floor() < 3.0, 'ini 가 계산값을 이기면 안 된다'


@pytest.mark.repo_only
def test_floor_follows_the_acf_when_noint_is_removed(tmp_path):
    """`NoIntMS` 를 0 으로 바꾸면 하한이 그만큼 내려가야 한다.

    운영자가 ACF 를 고칠 예정인 자리라(2026-08-31), 코드가 그 값을 **읽어**
    따라가는지 못박는다 -- 어딘가에 1.87 을 하드코딩해 두면 여기서 걸린다.
    """
    from ics_archon.archon.controller import ArchonController
    from icg_archon.config import IcgCfg

    icfg = IcgCfg()
    icfg.acf = {'G': GUIDE_ACF}
    ctrl = ArchonController('G', icfg)
    ctrl.parse_acf(GUIDE_ACF)
    p = acftiming.parameters(ctrl.config)

    with_noint = acftiming.frame_timing(p, lines=p['Lines'],
                                        pixels=p['Pixels'])
    p0 = dict(p, NoIntMS=0)
    without = acftiming.frame_timing(p0, lines=p0['Lines'],
                                     pixels=p0['Pixels'])
    # 정확히 NoIntMS 만큼 줄어든다 (500 ms).
    assert abs((with_noint['floor'] - without['floor']) - 0.5) < 0.01
    # 트리거->트랜스퍼 보정도 트랜스퍼 시간만 남는다.
    assert without['trigger_to_transfer'] < 0.02


# ---------------------------------------------------------------------------
# 시퀀서 pacing -- IntMS 환산과 하한 클램프 (운영자 확정 2026-08-31)
# ---------------------------------------------------------------------------

def _sim_backend(floor: float):  # noqa: ANN202
    """`frame_floor()` 만 고정한 대역 -- 환산 규칙만 본다."""
    from ics_sim import config as simcfg

    from icg_archon.backend import SimGuideBackend
    from icg_archon.config import IcgCfg

    icfg = IcgCfg()
    icfg.exptime_min = floor
    return SimGuideBackend(simcfg.SimConfig(), icfg)


def test_intms_is_exptime_minus_floor():
    """주기 = IntMS + 하한 이므로 `IntMS = EXPTIME - 하한` 이다."""
    be = _sim_backend(1.375)
    assert be.intms_for(1.375) == 0
    assert be.intms_for(2.0) == 625
    assert be.intms_for(10.0) == 8625
    # ms 반올림 -- 실현값은 그 반올림까지 반영한다.
    assert be.intms_for(2.0004) == 625
    assert abs(be.effective_exptime(2.0) - 2.0) < 1e-9


def test_short_exptime_is_clamped_not_rejected():
    """⭐ 하한보다 짧게 요청해도 **거부하지 않는다** -- 하한이 된다.

    운영자 확정(2026-08-31): "ExpTime 을 더 작게 설정해도 Minimum ExpTime
    으로".  헤더에는 요청값이 아니라 **실현값**이 실려야 한다 (10.1-1 이
    EXPTIME 을 실제 독출 개시 간격으로 정의한다).
    """
    be = _sim_backend(1.375)
    for req in (0.0, 0.5, 1.0, 1.3749):
        assert be.intms_for(req) == 0, '%g -> IntMS 는 0 이어야 한다' % req
        assert abs(be.effective_exptime(req) - 1.375) < 1e-9
    # 음수·이상값도 같은 규칙 (거부가 아니라 하한).
    assert be.intms_for(-5.0) == 0


def test_transfer_lag_includes_intms():
    """`DATE-OBS` 보정 = IntMS + NoIntMS + 트랜스퍼.

    시퀀서 pacing 에서는 적분이 프레임 안에 있으므로 `IntMS` 도 지연에
    들어간다 -- 안 넣으면 `DATE-OBS` 가 그만큼 이르다.
    """
    be = _sim_backend(1.0)
    assert abs(be.trigger_to_transfer(0) - 0.0) < 1e-9
    assert abs(be.trigger_to_transfer(2500) - 2.5) < 1e-9


@pytest.mark.repo_only
def test_real_backend_clamp_uses_the_acf_floor():
    """실기 백엔드는 ACF 계산 하한으로 클램프한다 (ini 대체값이 아니라)."""
    import os

    from ics_sim import config as simcfg

    from icg_archon.backend import GuideBackend
    from icg_archon.config import load

    ini = os.path.join(ROOT, 'icg_archon.ini')
    icfg = load(ini)
    icfg.acf = {'G': GUIDE_ACF}
    icfg.exptime_min = 0.1              # 대체값은 무시돼야 한다
    be = GuideBackend(simcfg.load(ini), icfg)
    floor = be.frame_floor()
    assert 1.7 < floor < 2.1            # NoIntMS=500 인 현행 ACF 기준
    assert be.intms_for(0.5) == 0
    assert abs(be.effective_exptime(0.5) - floor) < 1e-6
    assert be.intms_for(floor + 3.0) == 3000

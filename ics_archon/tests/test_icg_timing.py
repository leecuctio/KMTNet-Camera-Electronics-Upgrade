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

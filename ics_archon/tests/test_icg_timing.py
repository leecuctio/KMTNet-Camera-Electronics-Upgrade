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
GUIDE_ACF = os.path.join(ROOT, 'acf', 'KMTK_GUI_162_STA0201_R2614.acf')


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
    assert p['NoIntMS'] == 0 and p['Lines'] == 1033 and p['Pixels'] == 540

    t = acftiming.frame_timing(p, lines=p['Lines'], pixels=p['Pixels'])
    # 트랜스퍼는 밀리초 오더 (1033행 x 6상 x AT) -- 스미어가 짧다는 근거.
    assert 0.004 < t['transfer'] < 0.010
    # 독출은 1초 오더.
    assert 1.0 < t['readout'] < 2.0
    # 최소 주기 = NoIntMS + 트랜스퍼 + 독출 ≈ 1.25 s (R2610: NoIntMS=0 · Pixels=540).
    # ⚠️ 독출이 주기에 드는 것은 독출이 노출을 **막아서가 아니다** --
    # frame-transfer 라 image 는 독출 중에도 적분한다 (10.1-5).  다음
    # 트랜스퍼가 store 가 빌 때까지 못 오기 때문에 주기의 바닥이 된다.
    assert 1.2 < t['floor'] < 1.6
    # 트리거 -> 트랜스퍼 지연 = NoIntMS + 트랜스퍼 (DATE-OBS 보정분).
    # NoIntMS=0 이라 트랜스퍼만 남는다.
    assert t['trigger_to_transfer'] < 0.02


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
    assert be.frame_floor() > 1.0, 'ini 대체값이 이기면 안 된다'
    assert 0.004 < be.trigger_to_transfer() < 0.010

    # ⭐ **ini 값이 계산값을 밀어 올리면 안 된다** -- R2608->R2609 에서
    # 실제로 NoIntMS 를 0 으로 내렸고(주기 1.87 -> 1.37 s), 낡은 ini
    # 하한이 남아 있으면 정상 요청을 거부하게 되는 자리다.
    icfg.exptime_min = 99.0
    be2 = GuideBackend(simcfg.load(ini), icfg)
    assert be2.frame_floor() < 3.0, 'ini 가 계산값을 이기면 안 된다'


@pytest.mark.repo_only
def test_floor_follows_the_acf_when_noint_is_removed(tmp_path):
    """하한이 ACF 의 `NoIntMS` 를 그대로 따라가는가.

    운영자가 R2609 에서 `NoIntMS` 를 0 으로 내렸다(2026-08-31).  코드가 그
    값을 **읽어** 따라가는지 못박는다 -- 어딘가에 1.87 이나 1.37 을
    하드코딩해 두면 여기서 걸린다.
    """
    from ics_archon.archon.controller import ArchonController
    from icg_archon.config import IcgCfg

    icfg = IcgCfg()
    icfg.acf = {'G': GUIDE_ACF}
    ctrl = ArchonController('G', icfg)
    ctrl.parse_acf(GUIDE_ACF)
    p = acftiming.parameters(ctrl.config)

    assert p['NoIntMS'] == 0, 'R2609 는 NoIntMS=0 이다'
    without = acftiming.frame_timing(p, lines=p['Lines'],
                                     pixels=p['Pixels'])
    p5 = dict(p, NoIntMS=500)               # 구판(R2608) 값을 되살려 본다
    with_noint = acftiming.frame_timing(p5, lines=p5['Lines'],
                                        pixels=p5['Pixels'])
    # 정확히 NoIntMS 만큼 차이난다 (500 ms).
    assert abs((with_noint['floor'] - without['floor']) - 0.5) < 0.01
    # 트리거->트랜스퍼 보정도 현행에서는 트랜스퍼 시간만 남는다.
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
    assert 1.2 < floor < 1.6            # NoIntMS=0 인 현행 ACF(R2609) 기준
    assert be.intms_for(0.5) == 0
    # ⭐ 카드 해상도 1 ms (규격 10.1-1, 2026-09-05) -- 실현값을 ms 로 반올림한다.
    assert abs(be.effective_exptime(0.5) - round(floor, 3)) < 1e-9
    assert be.effective_exptime(2.0) == 2.0        # guideexp 2 -> 카드 '2' (정수형)
    assert be.intms_for(floor + 3.0) == 3000
    assert be.effective_exptime(floor + 3.0) == round(floor + 3.0, 3)


# ---------------------------------------------------------------------------
# `Pixels=600` 의 73개 -- 데이터시트 셈법과 트림 안전선 (DevNote 9.14, 2026-09-01)
# ---------------------------------------------------------------------------

def _guide_params():  # noqa: ANN202
    from ics_archon.archon.controller import ArchonController
    from icg_archon.config import IcgCfg

    icfg = IcgCfg()
    icfg.acf = {'G': GUIDE_ACF}
    ctrl = ArchonController('G', icfg)
    ctrl.parse_acf(GUIDE_ACF)
    return ctrl.config, acftiming.parameters(ctrl.config)


@pytest.mark.repo_only
def test_guide_acf_matches_the_ccd47_20_register_accounting():
    """⭐ 데이터시트 셈법이 ACF 와 여유 0 으로 맞는가 (규격 9.4절 · 9.14).

        8 BLANK | 15 DARK REF | 1 transition | 512 active  = 536 (절반)
        PreSkipPixels=8            PIXELCOUNT=528

    그리고 **디지타이즈 >= 저장** 이어야 한다 -- `Pixels` 를 트림하다 527 아래로
    내리면 실컬럼이 잘린다.  R2610 은 `Pixels=540`(디지타이즈 541)이다.
    """
    cfg, p = _guide_params()
    assert p['PreSkipPixels'] == 8, '데이터시트 BLANK 8 과 어긋난다'
    assert int(cfg['PIXELCOUNT']) == 15 + 1 + 512 == 528
    assert int(cfg['LINECOUNT']) == p['Lines'] == 1033, \
        'guide 는 FRAMEMODE=0 -- Lines 가 곧 프레임 높이다'
    # 10.3·10.6 이 무게를 실은 두 전제를 ACF 에서 직접 읽어 못박는다.
    assert cfg.get('FRAMEMODE', '0') == '0', \
        'guide 가 split 이면 HEIGHT 대체 경로(progress_of(0))가 50% 에 묶인다 (DevNote 10.3)'
    assert cfg.get('BIGBUF', '0') == '0', \
        'guide 는 버퍼 셋 전제다 -- 잠금 뒤 둘이 남는다 (fetch_timeout 안전선의 근거)'
    # LINE44 Pixels + LINE46 OverscanPixels + LINE47 인자 없는 CALL PixelFirst
    digitised = p['Pixels'] + p['OverscanPixels'] + 1
    assert digitised >= int(cfg['PIXELCOUNT']), \
        '디지타이즈(%d) < 저장(%s) -- 실컬럼이 잘린다' % (digitised, cfg['PIXELCOUNT'])
    # ⭐ 마법 숫자 대신 **물리 불변식**을 못박는다 (2026-09-03).
    #
    #     레지스터 절반 536 = BLANK 8 + 다크기준 15 + 전이 1 + active 512
    #     총 클록 = PreSkip + Pixels + PostSkip + Overscan + 1(LINE47)
    #
    # ⚠️ 총 클록이 536 아래로 내려가면 512번째 active 가 아직 출력단에
    # 도달하지 않는다 -- **절대 금지선**이다.
    clocks = (p['PreSkipPixels'] + p['Pixels']
              + p['PostSkipPixels'] + p['OverscanPixels'] + 1)
    assert clocks >= 536,         '총 클록 %d < 536 -- 레지스터를 다 못 쓴다 (실컬럼이 잘린다)' % clocks
    # ⭐ "버리는 수" == "레지스터 초과 클록" 이어야 한다.  ⚠️ 이 항등은
    # `Pixels` 를 제약하지 않는다 -- 대수적으로 소거된다.  제약하는 것은
    # **`PIXELCOUNT` == 536 - PreSkip - PostSkip** 이다(= 528).  즉 저장 창이
    # 실컬럼에 딱 맞는지, overscan 을 저장하기 시작했는지를 잡는다.
    surplus = digitised - int(cfg['PIXELCOUNT'])
    assert surplus == clocks - 536,         '버림 %d != 레지스터 초과 %d -- 저장 창이 실컬럼(528)을 벗어났나'         % (surplus, clocks - 536)
    # ⭐ 여분 자체의 제약 (문헌 권고 8~16, 직렬 트랩 시정수의 12~36배).
    # R2610 은 13 이다.  이쪽이 `Pixels` 를 실제로 못박는다.
    assert 1 <= surplus <= 32,         '여유 %d -- README "Pixels 여분은 몇이어야 하나" 절을 볼 것' % surplus


@pytest.mark.repo_only
def test_frame_flush_literal_is_independent_of_the_pixels_parameter():
    """`HorizontalShift(600)` 은 스크립트 리터럴이다 -- `Pixels` 트림과 무관.

    9.14 가 지적한 혼동 지점: 600 이 두 뜻으로 쓰인다.  트랜스퍼 시간은
    `Pixels` 를 바꿔도 **그대로**여야 하고, ACF 의 LINE12/LINE53 이 600 을
    적고 있어야 `acftiming._FRAME_HSHIFT` 가 그것을 비추는 게 맞다.
    """
    cfg, p = _guide_params()
    assert 'HorizontalShift(600)' in cfg['LINE12']
    assert 'HorizontalShift(600)' in cfg['LINE53']
    assert acftiming._FRAME_HSHIFT == 600  # noqa: SLF001
    t600 = acftiming.frame_timing(p, lines=p['Lines'], pixels=600)
    t529 = acftiming.frame_timing(p, lines=p['Lines'], pixels=529)
    assert t600['transfer'] == t529['transfer']
    assert t600['trigger_to_transfer'] == t529['trigger_to_transfer']
    # 움직이는 것은 독출(그래서 하한)뿐이다.
    assert t600['readout'] > t529['readout']


@pytest.mark.repo_only
def test_trimming_pixels_to_529_moves_only_the_floor_by_the_expected_amount():
    """9.14 의 수치를 코드가 재현하는가 -- 71 픽셀 x 1033 행 ≈ 146.7 ms."""
    _, p = _guide_params()
    t600 = acftiming.frame_timing(p, lines=p['Lines'], pixels=600)
    t529 = acftiming.frame_timing(p, lines=p['Lines'], pixels=529)
    saved = t600['floor'] - t529['floor']
    assert abs(saved - 0.1467) < 0.002, '절약 %.4f s' % saved
    assert t600['pixels'] == 600 and t529['pixels'] == 529
    assert 'Pixels 529' in acftiming.describe(t529)


@pytest.mark.repo_only
def test_read_timing_refuses_an_acf_without_pixels_instead_of_guessing(tmp_path):
    """`Pixels` 가 없으면 600 으로 셈하지 말고 **ini 대체값으로 물러나야** 한다.

    종전 `or 600` 대체값은 그럴싸한 하한을 내놓아 틀린 것이 안 보였다.
    """
    import re

    from ics_sim import config as simcfg

    from icg_archon.backend import GuideBackend
    from icg_archon.config import load

    with open(GUIDE_ACF, encoding='utf-8', errors='replace') as fh:
        src = fh.read()
    stripped = re.sub(r'^PARAMETER\d+="Pixels=\d+"\r?\n', '', src, flags=re.M)
    assert stripped != src, 'Pixels 줄을 못 지웠다'
    acf = tmp_path / 'no_pixels.acf'
    acf.write_text(stripped, encoding='utf-8', newline='')

    ini = os.path.join(ROOT, 'icg_archon.ini')
    icfg = load(ini)
    icfg.acf = {'G': str(acf)}
    icfg.exptime_min = 7.5                  # 눈에 띄는 대체값
    be = GuideBackend(simcfg.load(ini), icfg)
    assert be.timing is None, 'Pixels 없이 타이밍을 셈했다 -- 무엇으로?'
    assert be.frame_floor() == 7.5
    assert be.intms_for(7.5) == 0 and be.intms_for(10.0) == 2500


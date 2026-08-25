#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raw spec v1.3 5장 헤더 내용을 지킨다 (D-013 · D-016 · 판정 원장).

규격: `raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.4.md` 4·5장.
견본과의 바이트 대사는 `test_raw_draft.py`, 이름·번호·충돌은
`test_raw_pair.py` -- 이 파일은 **실제 노출 사이클이 만든 헤더의 내용**을
지킨다.  나눈 이유는 실패한 테스트 이름이 원인을 가리켜야 하기 때문이다.

**여기 있는 시험 대부분은 "조용한 실패" 를 잡는다.** raw spec 6장이 정리한
대로 헤더 카드가 없으면 converter 는 오류를 내지 않고 그럴듯한 기본값을
넣는다.  그러니 사람이 눈으로 볼 일이 없고, 시험이 유일한 방어선이다.
"""

from __future__ import annotations

import os
import re

import pytest

from conftest import drive, make_config

from ics_sim import rawcards, rawhdr

fits = pytest.importorskip('astropy.io.fits',
                           reason='헤더 검증에는 astropy 가 필요하다')

SCRIPT = ['OBS>ICS OBJECT BLG11', 'OBS>ICS EXP 5', 'OBS>ICS GO 1']


def _headers(tmp_path, **over):
    """노출 1회를 돌리고 `{DETID: header}` 를 돌려준다."""
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path),
                     **over)
    drive(SCRIPT, cfg)
    out = {}
    for name in sorted(os.listdir(tmp_path)):
        if name.endswith('.fits'):
            h = fits.getheader(os.path.join(tmp_path, name))
            out[str(h['DETID']).strip()] = h
    return out


# -- 카드 전량: 템플릿의 모든 카드가 실제로 실리나 ---------------------------

def test_every_template_card_is_written_in_both_files(tmp_path):
    """raw spec 7장 체크리스트 #3 -- 값 카드 135장 전량 존재.

    목록을 손으로 적지 않고 `rawcards.CARDS` 에서 뽑는다 -- 견본이 개정되면
    템플릿 대사(`test_raw_draft.py`)가 먼저 걸리고, 여기는 구현이 템플릿을
    따라오는지만 본다.
    """
    heads = _headers(tmp_path)
    assert set(heads) == {'MK', 'NT'}
    wanted = [k for k, kind, w, c in rawcards.CARDS if k != 'COMMENT']
    for tag, h in heads.items():
        missing = [k for k in wanted if k not in h]
        assert not missing, f'{tag} 파일에 필수 카드 누락: {missing}'


def test_bitpix_is_16_so_the_converter_can_read_it(tmp_path):
    """`BITPIX != 16` 이면 converter 가 그 자리에서 멈춘다 (raw spec 3장)."""
    for h in _headers(tmp_path).values():
        assert h['BITPIX'] == 16
        assert h['BZERO'] == 32768        # unsigned 16-bit zero point
        assert h['BSCALE'] == 1


# -- 5.9 pair 규칙: 상이 7장 / 나머지 동일 -----------------------------------

def test_pair_rule_exactly_seven_cards_differ(tmp_path):
    """raw spec 7장 체크리스트 #5.

    converter 는 MK 헤더만 읽으므로(master metadata), "나머지 동일" 이 깨지면
    NT 쪽 사실이 MEF 에서 **오류 없이** 사라진다.
    """
    heads = _headers(tmp_path)
    mk, nt = heads['MK'], heads['NT']
    skip = {'COMMENT', 'CHECKSUM', 'DATASUM'}
    diff = sorted(k for k in mk if k and k not in skip
                  and str(mk[k]) != str(nt.get(k)))
    assert diff == sorted(rawcards.PAIR_DIFF), diff


def test_detid_and_chmap_follow_the_amp_table(tmp_path):
    """`DETID`/`CHMAP_*` -- 4.5절 amp 전수 표의 투영 (pair 상이 5장)."""
    heads = _headers(tmp_path)
    for tag, h in heads.items():
        assert str(h['DETID']).strip() == tag
        for key, want in rawhdr.CHMAP[tag].items():
            assert str(h[key]).strip() == want, key


# -- 5.10 폐지·미기재 keyword 가 되살아나지 않게 -----------------------------

#: raw spec 5.10절의 미기재 카드 + 구판 구현이 만들다 폐지된 카드.
#: 되살아나면 규격과 구현이 갈라진 것이므로 여기서 잡는다.
RETIRED = (
    # 폐지·미도입 (5.10절 표)
    'UNIQNAME NAMECLSH PAIRFILE CTRLTAG RAWVER RAWPROD OSCNPATT ROWORDR '
    'RDDIRT RDDIRB MIDOSCT MIDOSCB MIDOVSCY CHIP1 CHIP2 CHIPS HEMODE '
    'NPHLINES CHKIMG CHKIMG_C FSADEW FSAALRM '
    # 파생 시각·WCS (DATE-OBS/EXPTIME 파생은 하류 몫)
    'JD MJD-OBS UT DARKTIME TSHOPEN TSHSHUT '
    # section·amp 식별 (4장 geometry 에서 계산 -- 중복은 불일치 원천)
    'CCDSEC AMPSEC DATASEC BIASSEC AMPID READDIR '
    # calibration (pipeline caldb 소관 -- 계층 규칙)
    'GAIN RDNOISE SATLEVEL LINMAX XTALKVER REFVER CATVER '
    # chiller 블록 (운영자 삭제 2026-08-21)
    'CHSTAT CHOP CHSET CHPROC '
    # 구판 geometry 선언 27장의 잔재
    'RAWNAX1 RAWNAX2 NXTILE RAWXTILE AMPDATA OVERSCNX PRESCANX OVERSCNY '
    'NSTRIP NEND AMPPCD STRIPDIR TOPROWS BOTROWS CHIPFLP READMODE READARCH '
    'CCDSUM '
    # 구판 detector/controller/전압 블록의 잔재
    'CAMNAME DETTYPE NCCD NAMPS DETSIZE CCDCOLS CCDROWS COLGAP ROWGAP '
    'CONTROLL NCTRL CTRLID CTRLVER CTRLSTAT CTRLERR BCKTEMP READTIME '
    'ACFFILE TIMCONF TIMVER BIASVER CLKVER WBTYPE ELECSYS SIGELEC '
    'CTRL1FW CTRL2FW FRAMENO BUFNO AMPMAP AMOD01 ACHN01 VOLTN VOLT1 VSET1 '
    'VMEA1 VOLTSTAT EXPMEAS SITEID FIELDID RAWGROUP CHIPLIST NUMFILES '
    'CREATOR DATE '
    # 레거시 판정 폐지 (D-013)
    'READOUT GAINDL PIXITIME DMAWAIT ICROLE CTCSOURC CTCFILE KBUILD MBUILD '
    'TBUILD NBUILD GBUILD RTD12 INPUTFMT CTRLNAME CTRLSN CTRLFW EXPID '
    'EXPNUM CCDTEMP1 CCDTEMP2 TELID TCSLIMIT EXECODE DSTEL'
).split()


def test_retired_cards_are_absent(tmp_path):
    heads = _headers(tmp_path)
    for tag, h in heads.items():
        revived = [card for card in RETIRED if card in h]
        assert not revived, (f'{tag} 에 폐지·미기재 카드가 되살아났다 '
                             f'(raw spec 5.10절): {revived}')


def test_no_card_beyond_the_template(tmp_path):
    """템플릿 밖의 카드가 없다 -- 견본이 카드 전량의 정본이다 (5장 머리말)."""
    allowed = {k for k, kind, w, c in rawcards.CARDS} | {'COMMENT', ''}
    for tag, h in _headers(tmp_path).items():
        extras = sorted({k for k in h.keys()} - allowed)
        assert not extras, f'{tag} 에 템플릿 밖 카드: {extras}'


# -- 5.5 DATASRC: 시뮬을 실물로 오인하지 않게 --------------------------------

def test_sim_frames_say_they_are_simulated(tmp_path):
    """`DATASRC=SIM`.  **이게 시뮬 프레임을 걸러내는 유일한 카드다.**"""
    for tag, h in _headers(tmp_path).items():
        assert str(h['DATASRC']).strip() == 'SIM', tag


def test_datasrc_vocabulary_is_the_v13_triple():
    """`ARCHON_SCIENCE`/`ARCHON_GUIDE`/`SIM` -- 구 `HEMODE` 를 흡수한 값 체계.

    모르는 백엔드는 `SIM` 으로 떨어뜨린다 -- 실물이라고 잘못 적는 쪽이 나쁘다.
    """
    assert rawhdr.datasrc_of('archon') == 'ARCHON_SCIENCE'
    assert rawhdr.datasrc_of('sim') == 'SIM'
    assert rawhdr.datasrc_of('') == 'SIM'
    assert rawhdr.datasrc_of('somethingelse') == 'SIM'
    assert rawhdr.DATASRC_GUIDE == 'ARCHON_GUIDE'     # icg 몫 (확장 규약)


# -- 5.2 geometry 선언 -------------------------------------------------------

def test_geometry_invariants_hold_in_the_written_header(tmp_path):
    """헤더에 실린 값끼리 4장 불변식을 만족해야 한다 (7장 체크리스트 #6)."""
    h = _headers(tmp_path)['MK']
    assert h['AMPNAX1'] == h['PRESCNX'] + h['IMAGEX'] + h['OVRSCNX'] == 1200
    assert h['AMPNAX2'] == h['PRESCNY'] + h['IMAGEY'] + h['OVRSCNY'] == 4700
    assert h['NAMPRAW'] == 2 * h['NAMPDET'] == 32
    assert rawhdr.RAW_NAXIS1 == 16 * h['AMPNAX1']
    assert rawhdr.RAW_NAXIS2 == 2 * h['AMPNAX2']
    # 2.4절 크기 등식 -- 깨지면 4장 해석이 어긋난 것이다
    assert (rawhdr.RAW_NAXIS1 * rawhdr.RAW_NAXIS2
            - h['NAMPRAW'] * h['AMPNAX1'] * h['IMAGEY']
            == rawhdr.RAW_NAXIS1 * 2 * h['OVRSCNY'])


def test_check_geometry_catches_a_broken_constant(monkeypatch):
    """불변식 검사가 **실제로 잡는지** 확인한다."""
    monkeypatch.setattr(rawhdr, 'IMAGEX', 1151)
    with pytest.raises(ValueError, match='불변식 위반'):
        rawhdr.check_geometry()


def test_check_geometry_catches_a_broken_chmap(monkeypatch):
    """CHMAP 불변식 (4.5절): 8토큰 · 접두=DETID 글자 · 채널 01–16 전량."""
    broken = {k: dict(v) for k, v in rawhdr.CHMAP.items()}
    broken['MK']['CHMAP_LT'] = 'M16,M15,M14,M13,M12,M11,M10,M10'  # M09 누락
    monkeypatch.setattr(rawhdr, 'CHMAP', broken)
    with pytest.raises(ValueError, match='채널 01–16'):
        rawhdr.check_geometry()


def test_overscny_is_the_frame_center_not_the_edge(tmp_path):
    """`OVRSCNY` 는 **영상 중앙** overscan 이다 (raw spec 4.2절).

    레거시 `OVERSCNY`(가장자리, 값 0)와 뜻이 달라 이름을 갈랐다 -- 레거시
    이름이 되살아나면 "위쪽 N행 자르기" 도구가 active 픽셀을 지운다.
    """
    h = _headers(tmp_path)['MK']
    assert 'OVERSCNY' not in h
    assert h['OVRSCNY'] == 84


# -- 5.4 노출 · 형 -----------------------------------------------------------

def test_exptime_is_integer_by_default_and_float_when_fractional():
    """`EXPTIME` 정수형 기본 · 소수점 아래 값이 있을 때만 실수형 (5.4절)."""
    base = dict(imgtype='OBJECT', objname='x', projid='x',
                date_obs='2026-08-22T00:00:00.000', filename='f',
                origname='f')
    whole = rawcards.render(rawhdr.build_pool(
        ctrltag='MK', site_code='KMTA', backend_name='sim', ics_build='x',
        ctrl_info={'units': ()}, ctrl_telem=None, sensors=None, cfg_site=None,
        cfg_camera=None, cfg_ctrl=None, rdmode='', telem_cards={},
        exptime=5.0, ledflash_ms=250, observer='x', **base))
    assert rawcards.value_of(whole, 'EXPTIME') == 5
    assert isinstance(rawcards.value_of(whole, 'EXPTIME'), int)
    assert rawcards.value_of(whole, 'LEDFLASH') == 250
    assert isinstance(rawcards.value_of(whole, 'LEDFLASH'), int)
    frac = rawcards.render(rawhdr.build_pool(
        ctrltag='MK', site_code='KMTA', backend_name='sim', ics_build='x',
        ctrl_info={'units': ()}, ctrl_telem=None, sensors=None, cfg_site=None,
        cfg_camera=None, cfg_ctrl=None, rdmode='', telem_cards={},
        exptime=0.5, ledflash_ms=0, observer='x', **base))
    assert rawcards.value_of(frac, 'EXPTIME') == 0.5


def test_missing_date_obs_omits_the_card():
    """`DATE-OBS` 결측이면 카드를 **내지 않는다** -- sentinel 로 가리면
    converter 의 실패 경로(C-6)가 발동하지 않는다 (raw spec 5.0절)."""
    cards = rawcards.render(rawhdr.build_pool(
        ctrltag='MK', site_code='KMTA', backend_name='sim', ics_build='x',
        ctrl_info={'units': ()}, ctrl_telem=None, sensors=None, cfg_site=None,
        cfg_camera=None, cfg_ctrl=None, rdmode='', telem_cards={},
        date_obs='', exptime=0, ledflash_ms=0, imgtype='BIAS', objname='x',
        projid='x', observer='x', filename='f', origname='f'))
    assert rawcards.value_of(cards, 'DATE-OBS') is None
    assert not any(k == 'DATE-OBS' for k, v, c in cards)


def test_date_obs_has_milliseconds_and_matches_across_the_pair(tmp_path):
    """`DATE-OBS` 밀리초 필수 · pair 동일 (셔터는 하나, 노출도 하나)."""
    heads = _headers(tmp_path)
    for tag, h in heads.items():
        assert re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}',
                            str(h['DATE-OBS'])), h['DATE-OBS']
        assert not str(h['DATE-OBS']).endswith('Z')   # TIMESYS 로 선언한다
    for card in ('DATE-OBS', 'EXPTIME', 'IMAGETYP', 'OBSTYPE', 'OBJECT',
                 'FILTER', 'TIMESYS'):
        assert heads['MK'][card] == heads['NT'][card], card


# -- 5.5 컨트롤러 정체 -------------------------------------------------------

def test_controller_identity_is_identical_in_both_files(tmp_path):
    """`CTRL1*`/`CTRL2*` 는 **양쪽에 같은 값** (5.9절 "반드시 동일").

    converter 는 MK 헤더만 읽으면서 두 대분 정체를 요구한다 -- NT 에만 있으면
    MEF 가 `UNKNOWN` 을 받는다, **오류 없이**.
    """
    heads = _headers(tmp_path)
    for card in ('CTRL1ID', 'CTRL1SN', 'CTRL1CFG',
                 'CTRL2ID', 'CTRL2SN', 'CTRL2CFG'):
        assert heads['MK'][card] == heads['NT'][card], card
        assert str(heads['MK'][card]).strip() not in ('', 'UNKNOWN'), card


def test_version_strings_are_owned_by_the_cfg_pointer(tmp_path):
    """타이밍·바이어스·클럭 버전 카드는 없다 -- 전부 `CTRLnCFG` 로 귀속
    (원장 확인 요망 8 종결).  `CAMVER`+`CTRLxCFG` 조합이 포장 규범 조항의
    고정 대상이다 (4.3절)."""
    h = _headers(tmp_path)['MK']
    for gone in ('TIMVER', 'BIASVER', 'CLKVER', 'CTRLVER', 'TIMCONF'):
        assert gone not in h, gone
    assert str(h['CTRL1CFG']).strip()
    assert str(h['CAMVER']).strip() == 'CEU-v2.1'


# -- 5.6 HK: 문자열 형 · sentinel --------------------------------------------

def test_hk_cards_are_signed_two_decimal_strings(tmp_path):
    """HK 온도 카드는 부호 포함 소수 2자리 **문자열** (raw spec 5.0절)."""
    h = _headers(tmp_path)['MK']
    assert isinstance(h['CCDTEMP'], str) and str(h['CCDTEMP']).startswith('-')
    assert isinstance(h['WALLBRD'], str) and str(h['WALLBRD']).startswith('+')
    assert float(h['DMPTEMP']) < -50
    # CCDTEMP1/2 는 후보 제외 확정 -- 대표 센서 1개만 싣는다
    assert 'CCDTEMP1' not in h and 'CCDTEMP2' not in h


def test_temp_cards_are_signed_two_decimal_strings():
    f = rawhdr.format_temp
    assert f(16.78) == '+16.78'
    assert f(-101.234) == '-101.23'
    assert f('-103.16') == '-103.16'
    for bad in (None, 'ERR', float('nan'), float('inf')):
        assert f(bad) == rawhdr.TEMP_NC == '-999.99', bad


def test_dewpres_formatting_and_rejection_rules():
    """측정값은 `x.xxe-x` 로, 0·음수·비수치·범위 밖은 전부 `9.99e-9` 로 접는다."""
    f = rawhdr.format_dewpres
    assert f(1.234e-4) == '1.23e-4'
    assert f('2.0e-6') == '2.00e-6'
    for bad in (0.0, -1.0, '0.00e-0', 'ERR', float('nan'), float('inf'),
                5.0e-9,      # 인정 하한(1e-8) 아래 -- sentinel 충돌 방어
                2.0e+3):     # 인정 상한 위
        assert f(bad) == rawhdr.DEWPRES_NC, bad


def test_fsa_cards_use_the_ens_style_and_the_hk_sentinel():
    """`FSATEMP`/`FSAHUM` -- ENS식 소수 1자리 잠정 (OI-16), sentinel 은
    HK 온도·습도 공통 `'-999.99'` (raw spec 5.0절이 FSA 2장을 명시)."""
    assert rawhdr.format_ens(23.44) == '23.4'
    assert rawhdr.format_ens(None) == '-999.99'
    h = rawhdr.thermal_header({'fsatemp': 23.4, 'fsahum': 12.3})
    assert h['FSATEMP'] == '23.4' and h['FSAHUM'] == '12.3'
    empty = rawhdr.thermal_header(None)
    assert empty['FSATEMP'] == '-999.99' and empty['FSAHUM'] == '-999.99'


def test_thermal_cards_survive_a_backend_that_reads_nothing():
    """센서를 하나도 못 읽어도 카드는 남는다 (raw spec 5.0절)."""
    h = rawhdr.thermal_header(None)
    assert str(h['CCDTEMP']) == rawhdr.TEMP_NC == '-999.99'
    assert str(h['DEWPRES']) == '9.99e-9'
    assert (str(h['DMPTEMP']) == str(h['WALLBRD']) == str(h['HEBOX'])
            == '-999.99')


def test_ccdtemp_uses_the_representative_sensor_only():
    """대표 센서는 `ccdtemp1` -- 백엔드가 `ccdtemp` 를 따로 줘도 무시한다."""
    h = rawhdr.thermal_header({'ccdtemp1': -100.0, 'ccdtemp2': -102.0,
                               'ccdtemp': 0.0})
    assert str(h['CCDTEMP']) == '-100.00', '대표 센서(ccdtemp1)가 아닌 값을 썼다'


def test_missing_representative_sensor_is_sentinel_with_a_warning(caplog):
    """대표 센서가 죽었을 때 이웃 값(ccdtemp2)으로 대체하지 않는다."""
    import logging
    with caplog.at_level(logging.WARNING):
        h = rawhdr.thermal_header({'ccdtemp2': -103.0})
    assert str(h['CCDTEMP']) == '-999.99'
    assert any('ccdtemp1' in r.message for r in caplog.records)


# -- 5.6 Cn_* 컨트롤러 텔레메트리 --------------------------------------------

def test_ctrl_telemetry_is_space_joined_and_identical_in_both_files(tmp_path):
    """`Cn_*` -- 공백 구분 나열, 자리=항목, pair 동일 (5.6·5.9절)."""
    heads = _headers(tmp_path)
    for card in ('C1_TEMP', 'C1_VOLT', 'C1_CURR',
                 'C2_TEMP', 'C2_VOLT', 'C2_CURR'):
        assert heads['MK'][card] == heads['NT'][card], card
    volt = str(heads['MK']['C1_VOLT']).split()
    assert len(volt) == len(rawhdr.VOLT_RAILS) == 7   # P2V5 … P35V


def test_ctrl_telemetry_formats_and_sentinels():
    h = rawhdr.ctrl_telemetry_header([
        {'temp': [40.12, 41.0], 'volt': [2.5119], 'curr': [0.0321]},
    ])
    assert h['C1_TEMP'] == '40.1 41.0'      # 온도 소수 1자리
    assert h['C1_VOLT'] == '2.512'          # 전압/전류 소수 3자리
    assert h['C1_CURR'] == '0.032'
    # 두 번째 컨트롤러 몫이 없으면 문자열 sentinel
    assert h['C2_TEMP'] == h['C2_VOLT'] == h['C2_CURR'] == 'NC'


# -- 5.3 측지값: 추측하지 않는다 ---------------------------------------------

SITE_GEODETIC = {
    'KMTC': ('KMTNet 1.6m #1', '-30:10:01.84', '+70:48:14.39', 2140),
    'KMTS': ('KMTNet 1.6m #2', '-32:22:42', '339:11:22', 1800),
    'KMTA': ('KMTNet 1.6m #3', '-31:16:24', '210:56:08', 1150),
}


@pytest.mark.parametrize('code', sorted(SITE_GEODETIC))
def test_site_geodetic_values_are_carried_verbatim(code):
    """세 사이트 값이 **문자 그대로** 실려야 한다 -- 정규화하면 레거시
    아카이브와 문자열 비교가 깨진다."""
    telescop, lat, lon, elev = SITE_GEODETIC[code]
    h = rawhdr.observatory_header(code)
    assert str(h['TELESCOP']) == telescop
    assert str(h['LATITUDE']) == lat
    assert str(h['LONGITUD']) == lon
    assert h['ELEVATIO'] == elev


@pytest.mark.parametrize('code', sorted(SITE_GEODETIC))
def test_longitude_is_west_positive_at_every_site(code):
    """`LONGITUD` 는 **서경 양수**다.

    세 사이트를 함께 확인하는 것이 요점이야 -- CTIO 만 90 미만이라 형태가 달라
    보여서, 하나만 보면 "동경으로 잘못 적혔나?" 하고 고치게 된다.  고치면
    **부호가 뒤집힌 좌표가 아카이브에 영구히 박힌다.**
    """
    east_deg = {'KMTC': -70.804, 'KMTS': 20.810, 'KMTA': 149.064}[code]
    lon = str(rawhdr.observatory_header(code)['LONGITUD']).lstrip('+')
    d, m, sec = (float(x) for x in lon.split(':'))
    west_deg = d + m / 60 + sec / 3600
    assert 0 <= west_deg < 360
    assert abs((-west_deg % 360) - (east_deg % 360)) < 0.01, (
        f'{code}: 서경 {west_deg} 가 동경 {east_deg} 와 맞지 않는다')


def test_testbed_has_no_coordinates_on_purpose():
    """테스트베드는 좌표를 **일부러** 비워 둔다 -- 아무 좌표나 넣으면 시험
    산출물이 실제 관측처럼 보인다.  `TELESCOP='Sim'` 만 규격이 정한 값이다
    (raw spec 5.3절)."""
    h = rawhdr.observatory_header('KMTT')
    assert str(h['LATITUDE']) == 'NC'
    assert str(h['TELESCOP']) == 'Sim'
    assert h['ELEVATIO'] == -1


def test_origin_is_where_the_file_was_generated():
    """`ORIGIN` = "이 파일이 생성된 곳" (raw spec 5.3절).

    관측소 raw = 관측소명 · 테스트베드 raw = `KASI`.  `[site]` ini 의
    `origin` 키가 유도값을 이긴다 (ICS INI 카드).
    """
    assert str(rawhdr.observatory_header('KMTC')['ORIGIN']) == 'CTIO'
    assert str(rawhdr.observatory_header('KMTT')['ORIGIN']) == 'KASI'
    h = rawhdr.observatory_header('KMTA', {'origin': 'KASI'})
    assert str(h['ORIGIN']) == 'KASI'
    assert str(h['OBSERVAT']) == 'SSO'    # OBSERVAT 는 안 바뀐다 (교차 검증 키)


def test_configured_site_values_win_over_the_table():
    """현장 설정이 정본이다."""
    h = rawhdr.observatory_header('KMTA', {'latitude': '-31:16:25',
                                           'elevatio': 1151})
    assert str(h['LATITUDE']) == '-31:16:25'
    assert h['ELEVATIO'] == 1151
    assert str(h['TELESCOP']) == 'KMTNet 1.6m #3'   # 설정에 없는 항목은 유지


def test_ics_ini_cards_are_editable_from_the_ini(tmp_path):
    """Source 가 `ICS INI` 인 카드는 전부 ini 에서 수정할 수 있다
    (운영자 지시 2026-08-22) -- `[camera]` 4장, `[controllers]` 6장+`RDMODE`,
    `[site]` `origin`.  채워진 INI 값은 백엔드 보고값을 이긴다."""
    ini = tmp_path / 'x.ini'
    ini.write_text(
        '[camera]\n'
        'detector = e2v CCD290-99B\n'
        'camver = CEU-v2.2\n'
        'instrume = KMTA 18k CCD\n'
        'fpaid = FPA#2\n'
        '[controllers]\n'
        'ctrl1_id = KMTA-SCI-101\n'
        'ctrl1_sn = STA-0288\n'
        'ctrl1_cfg = KMTA_SCI_101_R2609.1\n'
        'ctrl2_id = KMTA-SCI-102\n'
        'ctrl2_sn = STA-0289\n'
        'ctrl2_cfg = KMTA_SCI_102_R2609.1\n'
        'rdmode = FAST\n'
        '[site]\n'
        'origin = KASI\n', encoding='utf-8')
    from ics_sim import config as cfgmod
    cfg = cfgmod.load(str(ini))

    h = rawhdr.instrument_header('MK', 'KMTA', cfg.camera.as_dict())
    assert str(h['DETECTOR']) == 'e2v CCD290-99B'
    assert str(h['CAMVER']) == 'CEU-v2.2'
    assert str(h['INSTRUME']) == 'KMTA 18k CCD'
    assert str(h['FPAID']) == 'FPA#2'
    # 오버라이드가 없으면 확정 형식으로 유도된다 ('<SITE> 18k CCD')
    assert str(rawhdr.instrument_header('MK', 'KMTC')['INSTRUME']) == \
        'KMTC 18k CCD'

    info = {'units': (
        {'id': 'ARCHON-SIM-1', 'sn': 'SIM0001', 'cfg': 'SIM-cfg'},
        {'id': 'ARCHON-SIM-2', 'sn': 'SIM0002', 'cfg': 'SIM-cfg'})}
    ch = rawhdr.controller_header(info, backend_name='sim', ics_build='x',
                                  cfg_ctrl=cfg.controllers.overrides(),
                                  rdmode=cfg.controllers.rdmode)
    assert str(ch['CTRL1ID']) == 'KMTA-SCI-101'      # INI 가 SIM 더미를 이긴다
    assert str(ch['CTRL2SN']) == 'STA-0289'
    assert str(ch['CTRL1CFG']) == 'KMTA_SCI_101_R2609.1'
    assert str(ch['RDMODE']) == 'FAST'

    assert cfg.site_for('KMTA').get('origin') == 'KASI'


def test_rdmode_defaults_to_normal():
    ch = rawhdr.controller_header({'units': ()}, backend_name='sim',
                                  ics_build='x')
    assert str(ch['RDMODE']) == 'NORMAL'
    # 백엔드도 INI 도 없으면 **카드는 남기고 값은 sentinel** (규격 5.0절).
    # 1대만 운영할 때 빠진 쪽도 이 자리로 떨어진다 -- 카드를 빼면 pair 두
    # 파일의 카드 수가 달라져 converter 와 견본 대사가 구조 변경으로 읽는다.
    # ini 에 `none`/`NC` 라고 적은 것도 같은 뜻이다 (운영자 확정 2026-08-25).
    assert str(ch['CTRL1ID']) == 'NC'


# -- ICSBUILD ---------------------------------------------------------------

def test_icsbuild_carries_version_and_build_time(tmp_path):
    """`v<버전>:<빌드일시>Z` 형식 (운영자 확정 2026-08-22).

    끝의 `Z` 는 의도적이다 -- 시각 카드가 아니라 사람이 떼어 읽는 식별자라
    자체적으로 시간대를 지녀야 한다.  프로그램명은 없다 (식별은 `DATASRC`).
    """
    for tag, h in _headers(tmp_path).items():
        got = str(h['ICSBUILD']).strip()
        assert re.fullmatch(r'v\d+\.\d+\.\d+'
                            r':\d{4}-\d\d-\d\dT\d\d:\d\dZ', got), (tag, got)
        assert 'KX2016' not in got, '레거시 빌드 문자열이 남아 있다'
        assert not str(h['DATE-OBS']).endswith('Z'), (
            'FITS 시각 카드는 TIMESYS 로 선언하므로 Z 를 붙이지 않는다')


def test_build_id_composes_version_and_build_date():
    from ics_sim import __build_date__, __version__, build_id
    assert build_id() == f'v{__version__}:{__build_date__}'
    # ics_archon 재사용법: 자기 패키지의 두 값을 다 넘긴다
    assert build_id('2.0.0', '2027-01-01T00:00Z') == 'v2.0.0:2027-01-01T00:00Z'


# -- 백엔드가 실패해도 프레임을 버리지 않는다 --------------------------------

def test_a_backend_that_raises_does_not_lose_the_frame(tmp_path):
    """센서 한 채널 때문에 프레임을 버리면 손해가 훨씬 크다.

    실패는 sentinel 로 남기고 저장은 계속한다 -- "값이 없었다" 는 사실이
    헤더에 남으므로 조용한 오염이 되지 않는다.
    """
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path))

    import ics_sim.hardware.sim as simmod

    def boom(self, *a):
        raise RuntimeError('센서 버스 응답 없음')

    original = simmod.SimBackend.sensors
    simmod.SimBackend.sensors = boom
    try:
        drive(SCRIPT, cfg)
    finally:
        simmod.SimBackend.sensors = original

    written = [p for p in os.listdir(tmp_path) if p.endswith('.fits')]
    assert len(written) == 2, '헤더 값 하나 때문에 저장이 멈췄다'
    h = fits.getheader(os.path.join(tmp_path, sorted(written)[0]))
    assert str(h['CCDTEMP']).strip() == '-999.99'
    assert str(h['CTRL1ID']).strip()           # 다른 덩어리는 멀쩡하다


# -- 파일명 `<YYYYMMDD>` = 사이트별 관측일 (운영자 확정 2026-08-13) ----------

from datetime import datetime, timezone            # noqa: E402

from ics_sim import rawpair                        # noqa: E402

#: 운영자가 준 규칙을 **그대로** 표로 옮긴 것.  경계 시각과 그 1분 전후를 함께
#: 넣는 이유는 off-by-one 이 1년에 몇 번만 드러나는 부류라서다.
OBSDATE_CASES = [
    # (사이트, UT 시각, 기대 날짜)  -- 기준일은 2026-08-13
    ('KMTC', '00:00', '20260813'), ('KMTC', '16:29', '20260813'),
    ('KMTC', '16:30', '20260814'), ('KMTC', '23:59', '20260814'),
    ('KMTA', '00:00', '20260812'), ('KMTA', '01:29', '20260812'),
    ('KMTA', '01:30', '20260813'), ('KMTA', '23:59', '20260813'),
    ('KMTS', '00:00', '20260812'), ('KMTS', '10:29', '20260812'),
    ('KMTS', '10:30', '20260813'), ('KMTS', '23:59', '20260813'),
    ('KMTT', '00:00', '20260813'), ('KMTT', '23:59', '20260813'),
]


@pytest.mark.parametrize('site,hm,want', OBSDATE_CASES)
def test_observing_date_matches_the_operator_rule(site, hm, want):
    h, m = (int(x) for x in hm.split(':'))
    when = datetime(2026, 8, 13, h, m, tzinfo=timezone.utc)
    assert rawpair.observing_date(when, site) == want


def test_every_site_boundary_is_local_1230():
    """세 경계가 모두 **현지 12:30** 이어야 한다 -- 숫자 검산용 불변식."""
    utc_offset_hours = {'KMTC': -4, 'KMTS': +2, 'KMTA': +11}
    for site, off in utc_offset_hours.items():
        shift = rawpair.OBSDATE_SHIFT_MIN[site]
        boundary_ut_min = (-shift) % (24 * 60)
        local_min = (boundary_ut_min + off * 60) % (24 * 60)
        assert local_min == 12 * 60 + 30, (
            f'{site}: 경계가 현지 {local_min // 60}:{local_min % 60:02d} 다')


def test_unknown_site_code_falls_back_to_testbed():
    """`KMTC`/`KMTS`/`KMTA` 밖은 모두 `KMTT` (운영자 확정 2026-08-13)."""
    assert rawpair.normalize_site('KMTN') == 'KMTT'
    assert rawpair.normalize_site('') == 'KMTT'
    assert rawpair.normalize_site('kmtc') == 'KMTC'      # 대소문자 무관
    for real in ('KMTC', 'KMTS', 'KMTA'):
        assert rawpair.normalize_site(real) == real


def test_filename_date_uses_the_observing_date_not_the_utc_date(tmp_path):
    """실제로 쓴 파일 이름의 날짜부가 관측일 규칙을 따르나."""
    h = _headers(tmp_path)['MK']
    date_part = str(h['FILENAME']).split('.')[1]
    site = str(h['FILENAME']).split('.')[0]
    iso = str(h['DATE-OBS'])
    when = datetime.strptime(iso, '%Y-%m-%dT%H:%M:%S.%f').replace(
        tzinfo=timezone.utc)
    assert date_part == rawpair.observing_date(when, site)


# -- 5.4 IMAGETYP 통제 어휘: 명령 목록과 규격이 갈리면 안 된다 ---------------

def test_command_vocabulary_equals_the_spec_vocabulary():
    """ICS 가 받는 이미지 타입 = **raw spec 5.4절 `IMAGETYP` 어휘** 정확히.

    헤더가 실을 수 없는 값을 명령으로 받으면 규격 밖 값이 아카이브에 박힌다 --
    `IMAGETYP` 은 sentinel 조차 금지된 카드이고(5.0절) L1 파이프라인이 문자열
    비교로 검사하므로, 두 목록이 갈리면 조용히 틀린 값이 남는다.

    `STANDARD` 는 폐지했다 (운영자 확정 2026-08-22) -- 레거시 명령 테이블에는
    있었지만 규격 어휘에 없었다.  **값을 늘릴 일이 생기면 규격 5.4절과
    `state.IMAGE_TYPES` 를 함께 고친다** (운영자 지시).
    """
    from ics_sim.state import IMAGE_TYPES
    # 정본: raw spec 5.4절 `IMAGETYP` 값 칸
    spec_vocab = {'BIAS', 'DARK', 'OBJECT', 'FLAT', 'SKY', 'DOMEFLAT'}
    assert set(IMAGE_TYPES) == spec_vocab, (
        f'명령 어휘와 규격 어휘가 갈렸다 -- 명령만: '
        f'{set(IMAGE_TYPES) - spec_vocab} / 규격만: '
        f'{spec_vocab - set(IMAGE_TYPES)}')


def test_retired_standard_command_is_rejected():
    """`standard` 는 이제 `Didn't understand` 로 거부된다.

    레거시에는 있던 명령이라 **레거시와 갈라지는 지점**이다 -- 운영자가 "이제
    안 쓴다"고 확정했고, 실사용 `.osc` 22개·레거시 로그 샘플에 용례가 0건이라
    실운용에 닿지 않는다.  되살리려면 규격 5.4절 어휘부터 늘려야 한다.
    """
    from conftest import drive
    run = drive(['OBS>ICS standard std'])
    assert run.find("Didn't understand"), run.sent
    # 상태가 오염되지 않았는지 -- 거부이므로 imgtype 이 바뀌면 안 된다
    assert not [m for m in run.sent if 'ImageType=STANDARD' in m]

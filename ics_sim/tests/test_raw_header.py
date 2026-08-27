#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raw spec 5장 헤더 내용을 지킨다 (D-013 · D-016 · D-019 · 판정 원장).

규격: `raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.7.md` 4·5장.
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
    """raw spec 7장 체크리스트 #3 -- 값 카드 131장 전량 존재.

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


# -- 5.9 pair 규칙: 상이 6장 / 나머지 동일 (v1.6: 7 -> 6) --------------------

def test_pair_rule_exactly_six_cards_differ(tmp_path):
    """raw spec 7장 체크리스트 #5 -- **상이 6장** (v1.6 에서 7장에서 줄었다).

    converter 는 MK 헤더만 읽으므로(master metadata), "나머지 동일" 이 깨지면
    NT 쪽 사실이 MEF 에서 **오류 없이** 사라진다.

    ⚠️ `EXPID` 는 "반드시 동일" 쪽이다 -- `DETID` 필드가 없어 pair 양쪽이 같고, 그래서
    짝을 잇는 단일 키가 된다 (D-019).  여기 diff 에 뜨면 그 성질이 깨진 것이다.
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
    # standalone RTD 계통 HK 4장 (v1.5 폐지, 규격 5.10절)
    'AIR_IN AIR_OUT GLYC_IN GLYC_OUT '
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
    'TBUILD NBUILD GBUILD RTD12 INPUTFMT CTRLNAME CTRLSN CTRLFW '
    'EXPNUM CCDTEMP1 CCDTEMP2 TELID TCSLIMIT EXECODE DSTEL '
    # v1.6(D-019) 폐지 -- `EXPID` 가 대체한다.
    # ⚠️ `EXPID` 는 D-013 에서 폐지됐다가 **v1.6 에서 되살아났으므로** 이
    # 목록에 있으면 안 된다 (현행 카드다).  `EXPNUM` 은 여전히 미도입이다.
    'ORIGNAME'
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
    broken['MK']['CHMAP_LT'] = 'MD16,MD15,MD14,MD13,MD12,MD11,MD10,MD10'
    monkeypatch.setattr(rawhdr, 'CHMAP', broken)
    with pytest.raises(ValueError, match='채널 01–16'):
        rawhdr.check_geometry()


def test_chmap_tokens_are_four_chars(monkeypatch):
    """**토큰은 4자 `<chip><A|D><nn>` 이다** (v1.5 -- 3자 표기를 대체했다).

    구판 3자 토큰(`M16`)이 되살아나면 여기서 걸린다.  걸리지 않으면 파일에
    실린 뒤에 발견되고, 그때는 이미 아카이브에 들어가 있다.
    """
    broken = {k: dict(v) for k, v in rawhdr.CHMAP.items()}
    broken['MK']['CHMAP_LT'] = 'M16,M15,M14,M13,M12,M11,M10,M09'
    monkeypatch.setattr(rawhdr, 'CHMAP', broken)
    with pytest.raises(ValueError, match='4자가 아니다'):
        rawhdr.check_geometry()


def test_chmap_middle_letter_is_decided_by_the_channel_number(monkeypatch):
    """가운데 글자는 **번호만이 정한다** -- `01`–`08`=`A` · `09`–`16`=`D`.

    chip 이나 사분면에서 유추하면 안 된다 (raw spec 4.5절 · 부록 A: 채널 번호 =
    OS 번호 = 아래/위 half).  `IMGSEC` 의 구 `B-BOT` 이 원전 없는 표기로
    판정돼 `D-BOT` 이 된 것도 이 사슬이 닫혔기 때문이다 (OI-17 잔여 ①·②).
    """
    assert [rawhdr.chmap_section(n) for n in (1, 8, 9, 16)] == ['A', 'A', 'D', 'D']
    broken = {k: dict(v) for k, v in rawhdr.CHMAP.items()}
    # 채널 09–16 인데 `A` 로 적었다 -- 위 half 를 아래 half 라고 말하는 셈이다.
    broken['MK']['CHMAP_LT'] = 'MA16,MA15,MA14,MA13,MA12,MA11,MA10,MA09'
    monkeypatch.setattr(rawhdr, 'CHMAP', broken)
    with pytest.raises(ValueError, match='가운데 글자'):
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
                expid='f')
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
        projid='x', observer='x', filename='f', expid='f'))
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


def test_ccdtemp_is_one_representative_key_not_a_per_chip_pair():
    """대표 센서는 **`ccdtemp` 하나**다 -- chip 으로 규정하지 않는다.

    ⚠️ **종전에는 `ccdtemp1`(대표)/`ccdtemp2`(이웃) 두 키였고 `ccdtemp` 는
    "따로 줘도 무시하는" 키였다** (2026-08-27 정리).  센서가 듀어에 하나뿐이고
    chip 귀속 정보가 없다고 확정되면서, 무시 규칙의 존재 이유("두 번째 사실을
    만들지 않기")가 사라졌다 -- 그래서 `ccdtemp` 를 대표 이름으로 승격하고
    옛 두 키는 없앴다.
    """
    h = rawhdr.thermal_header({'ccdtemp': -100.0})
    assert str(h['CCDTEMP']) == '-100.00'
    # 옛 키는 **더 이상 읽지 않는다** -- 남겨 두면 두 이름이 공존한다.
    stale = rawhdr.thermal_header({'ccdtemp1': -100.0, 'ccdtemp2': -102.0})
    assert str(stale['CCDTEMP']) == '-999.99', '폐기한 옛 키를 아직 읽는다'


def test_missing_representative_sensor_is_sentinel_with_a_warning(caplog):
    """대표가 없으면 **다른 값으로 대체하지 않는다** -- sentinel + 경고.

    대체 후보가 눈에 보이는 것이 함정이다(`DMPTEMP` · `Cn_TEMP` 모듈 온도).
    """
    import logging
    with caplog.at_level(logging.WARNING):
        h = rawhdr.thermal_header({'dmptemp': -103.0})
    assert str(h['CCDTEMP']) == '-999.99'
    assert any('ccdtemp' in r.message for r in caplog.records)


# -- 5.6 Cn_* 컨트롤러 텔레메트리 --------------------------------------------

def test_ctrl_telemetry_is_pipe_joined_and_identical_in_both_files(tmp_path):
    """`Cn_*` -- **파이프(`|`) 구분** 나열, 자리=항목, pair 동일 (5.6·5.9절).

    구분자는 v1.6 에서 공백에서 파이프로 바뀌었다 -- 값에 이름표가 없어 경계를
    눈으로 세야 하는데 음수가 섞이면(`16.956 -17.067`) 공백으로는 안 갈렸다.
    """
    heads = _headers(tmp_path)
    for card in ('C1_TEMP', 'C1_VOLT', 'C1_CURR',
                 'C2_TEMP', 'C2_VOLT', 'C2_CURR'):
        assert heads['MK'][card] == heads['NT'][card], card
    volt = str(heads['MK']['C1_VOLT']).strip().split('|')
    assert len(volt) == len(rawhdr.VOLT_RAILS) == 7   # P2V5 … P35V


def test_ctrl_telemetry_formats_and_sentinels():
    """수치 표기 고정 -- 온도 1자리 · 전압/전류 3자리, 파이프 구분 (5.6절).

    ⚠️ 여기 넣는 목록은 자리 수가 규격(10/7)보다 짧다.  **표기만 보는 시험**
    이라 그렇게 뒀고, 그래서 `_join_readings` 가 "자리 수가 어긋난다" 를 에러
    로그로 남긴다 -- 그것이 맞는 동작이다 (실기에서 자리 수가 밀리면 값이
    다른 모듈 것으로 읽힌다).  자리 채움 자체는 아래 두 시험이 본다.
    """
    h = rawhdr.ctrl_telemetry_header([
        {'temp': [40.12, 41.0], 'volt': [2.5119], 'curr': [0.0321]},
    ])
    assert h['C1_TEMP'] == '40.1|41.0'      # 온도 소수 1자리 · 파이프 구분
    assert h['C1_VOLT'] == '2.512'          # 전압/전류 소수 3자리
    assert h['C1_CURR'] == '0.032'


def test_temp_mod_order_is_anchored_to_the_spec_table():
    """`TEMP_MOD_LABELS` 를 **규격 5.6.1절 표에 못박고**, `TEMP_MODS` 를 그
    자리에 1:1 로 묶는다.

    ⚠️ **두 튜플의 지위가 다르다.**  `TEMP_MOD_LABELS` 는 규격 5.6.1절 표
    그 자체이고, `TEMP_MODS`(Archon STATUS 필드명)는 **규격에 없다** -- 각
    자리에서 어떤 필드를 읽을지는 매뉴얼 p.47-49 근거의 구현 대응이다.
    그래서 앞은 규격 글자와, 뒤는 **자리 대응**과 대조한다.

    ⚠️ 이 저장소의 다른 시험은 전부 **상수를 기준으로** 기대값을 만든다 --
    `len(rawhdr.TEMP_MODS)` 로 자리 수를 세거나(아래 시험), labtest 내장 사본을
    `rawhdr` 와 대조하거나(`ics_archon/tests/test_labtest_spec_copy.py`).
    그래서 **원천인 이 튜플 자체가 틀리면 사본도 같이 틀린 채 전부 통과한다.**
    여기만 규격 표의 글자를 손으로 적어 앵커 노릇을 한다.

    자리가 곧 항목이라 순서가 하나만 밀려도 읽는 쪽이 **다른 모듈의 온도를
    본다** -- 값이 다 그럴듯한 범위라 눈으로도, 바이트 대사로도 안 잡힌다
    (견본은 sim 이 순서대로 준 값이라 라벨을 재배열해도 출력이 같다).
    """
    # raw spec 5.6.1절 "`Cn_TEMP` -- Archon 모듈 온도, science 컨트롤러 10자리"
    assert rawhdr.TEMP_MOD_LABELS == (
        'Backplane', 'Mod1:LVDS', 'Mod2:Driver', 'Mod3:Driver',
        'Mod4:LVXBias', 'Mod5:ADM', 'Mod8:ADM', 'Mod9:HVYBias',
        'Mod10:Driver', 'Mod11:Driver')
    # STATUS 필드명(규격 아님 -- 매뉴얼 p.47-49)이 그 자리와 1:1 이어야 한다.
    assert rawhdr.TEMP_MODS == (
        'BACKPLANE_TEMP', 'MOD1/TEMP', 'MOD2/TEMP', 'MOD3/TEMP', 'MOD4/TEMP',
        'MOD5/TEMP', 'MOD8/TEMP', 'MOD9/TEMP', 'MOD10/TEMP', 'MOD11/TEMP')
    assert len(rawhdr.TEMP_MODS) == len(rawhdr.TEMP_MOD_LABELS) == 10
    # 목록에 없는 모듈(6·7·12)은 자리를 차지하지 않는다 -- 자리 수가 구성이다.
    mods = [f.split('/')[0] for f in rawhdr.TEMP_MODS[1:]]
    assert mods == ['MOD1', 'MOD2', 'MOD3', 'MOD4', 'MOD5',
                    'MOD8', 'MOD9', 'MOD10', 'MOD11']
    assert len(set(mods)) == len(mods), '모듈이 겹친다'
    # 5.6.1절 전원 레일 7자리.
    assert rawhdr.VOLT_RAILS == (
        'P2V5', 'P5V', 'P6V', 'N6V', 'P17V', 'N17V', 'P35V')


def test_absent_controller_still_fills_every_field():
    """**전 자리 결측도 자리 수만큼 `NC` 다** (raw spec 5.6.1절).

    ⚠️ `'NC'` 한 토큰으로 내면 안 된다.  같은 절이 **자리 수 자체를 모듈 구성
    판별에 쓰라**고 규정하므로, 한 토큰짜리는 읽는 쪽에 "모듈 한 장짜리
    컨트롤러" 로 보인다.  규격이 전 자리 결측(STATUS 무응답 · 미장착 모듈)을
    "드물지 않다" 고 못박고 그 모습을 열 자리 `NC` 로 보인 것이 이 때문이다.
    """
    h = rawhdr.ctrl_telemetry_header([{'temp': [40.1], 'volt': [], 'curr': []}])
    assert h['C2_TEMP'] == '|'.join(['NC'] * len(rawhdr.TEMP_MODS))
    assert h['C2_VOLT'] == h['C2_CURR'] == '|'.join(
        ['NC'] * len(rawhdr.VOLT_RAILS))
    # 자리 수가 규격 표와 같아야 한다 -- 그것으로 구성을 읽기 때문이다.
    assert len(str(h['C2_TEMP']).split('|')) == 10
    assert len(str(h['C2_VOLT']).split('|')) == 7
    # 한 대분만 결측이어도 나머지 카드는 그대로다.
    assert h['C1_TEMP'] == '40.1'


def test_missing_field_inside_a_list_is_nc_not_none():
    """목록 안의 빈 자리도 `NC` -- `None` 이 `'None'` 으로 실리면 안 된다.

    `archon/parse.field_value()` 가 이미 sentinel 로 채워 보내지만, 나열 카드는
    **자리가 곧 항목**이라 여기가 마지막 방어선이다 (5.6.1절).
    """
    h = rawhdr.ctrl_telemetry_header([{'temp': [40.1, None, 42.3, '']}])
    assert str(h['C1_TEMP']).split('|')[:4] == ['40.1', 'NC', '42.3', 'NC']


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


def test_kasi_has_no_coordinates_on_purpose():
    """KASI(실험실)는 **좌표만** 일부러 비워 둔다 (raw spec OI-11).

    아무 좌표나 넣으면 시험 산출물이 실제 관측처럼 보인다.  다만 `TELESCOP` 은
    **값이 있다** -- D-017 항목 6 이 `'KMTNet 1.6m #0'` 으로 정했다 (5.3.1절).
    구 `KMTT` 판에서는 `'Sim'` 이었다.
    """
    h = rawhdr.observatory_header('KMTK')
    assert str(h['LATITUDE']) == 'NC'
    assert str(h['LONGITUD']) == 'NC'
    assert str(h['TELESCOP']) == 'KMTNet 1.6m #0'
    assert h['ELEVATIO'] == -1


@pytest.mark.parametrize('code, telescop, fpaid', [
    ('KMTC', 'KMTNet 1.6m #1', 'FPA#2'),
    ('KMTA', 'KMTNet 1.6m #3', 'FPA#1'),
    ('KMTS', 'KMTNet 1.6m #2', 'FPA#3'),
    ('KMTK', 'KMTNet 1.6m #0', 'FPA#0'),
])
def test_site_constants_table_5_3_1(code, telescop, fpaid):
    """5.3.1절 -- 사이트 하나가 `TELESCOP` 과 `FPAID` 를 함께 정한다.

    ⚠️ **망원경 번호와 FPA 번호는 관측소 셋 모두 어긋난다.**  이 시험이
    그 어긋남 자체를 못박는다 -- 다음 사람이 "오타네" 하고 맞추면 여기서
    걸린다.  맞추면 검출기 귀속이 통째로 틀어진다 (D-017 항목 6).
    """
    assert str(rawhdr.observatory_header(code)['TELESCOP']) == telescop
    assert rawhdr.fpaid_of(code) == fpaid
    assert str(rawhdr.instrument_header('MK', code)['FPAID']) == fpaid
    if code != 'KMTK':
        tel_no = telescop.rsplit('#', 1)[1]
        fpa_no = fpaid.rsplit('#', 1)[1]
        assert tel_no != fpa_no, (
            f'{code}: 망원경 #{tel_no} 와 FPA #{fpa_no} 가 같아졌다 -- '
            '5.3.1절은 관측소 셋 모두 어긋난다고 못박았다')


def test_ini_fpaid_wins_over_the_site_table():
    """현장이 정본이다 -- `[camera] fpaid` 가 사이트 유도값을 이긴다."""
    h = rawhdr.instrument_header('MK', 'KMTA', {'fpaid': 'FPA#9'})
    assert str(h['FPAID']) == 'FPA#9'


def test_origin_is_where_the_file_was_generated():
    """`ORIGIN` = "이 파일이 생성된 곳" (raw spec 5.3절).

    관측소 raw = 관측소명 · KASI(실험실) raw = `KASI`.  `[site]` ini 의
    `origin` 키가 유도값을 이긴다 (ICS INI 카드).  **D-017 이후 네 자리 모두
    `OBSERVAT` 와 값이 같지만 뜻이 달라 카드는 합치지 않는다.**
    """
    assert str(rawhdr.observatory_header('KMTC')['ORIGIN']) == 'CTIO'
    assert str(rawhdr.observatory_header('KMTK')['ORIGIN']) == 'KASI'
    assert str(rawhdr.observatory_header('KMTK')['OBSERVAT']) == 'KASI'
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
    ('KMTK', '00:00', '20260813'), ('KMTK', '23:59', '20260813'),
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


def test_unknown_site_code_falls_back_to_kasi():
    """`KMTC`/`KMTS`/`KMTA` 밖은 모두 `KMTK` (운영자 확정 2026-08-13).

    TC 가 보내는 `TELID` 에 사이트가 아닌 `KMTN`(pctcs 기본값, `pctcs.h:115`)이
    올 수 있어서 필요하다.
    """
    assert rawpair.normalize_site('KMTN') == 'KMTK'
    assert rawpair.normalize_site('') == 'KMTK'
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


# -- 5.0 카드 폭 초과: comment 를 먼저 자른다 (v1.6 신설) --------------------

def test_over_long_value_shortens_the_comment_first(caplog):
    """**폭이 모자라면 comment 를 먼저 줄인다** (raw spec **5.0절**, v1.6).

    값이 자료이고 comment 는 설명이기 때문이다.  `Cn_*` 나열 카드는 자리가 곧
    항목이라(5.6.1절) 값이 잘리면 **뒤 항목이 통째로 사라지는데 읽는 쪽은 그
    사실을 알 방법이 없다.**

    astropy 도 값이 길면 comment 를 먼저 줄이지만, 그 판단을 astropy 에 맡겨
    두면 다음 시험의 경우를 못 막는다.
    """
    from ics_sim import fitsout

    long = '|'.join(['-40.1'] * 10)               # 59자 -- 견본 폭(51) 초과
    value, comment = fitsout._fit_to_card('C1_TEMP', long, 'Ctrl-1 T[C]')
    assert value == long, '값이 온전해야 한다 -- 잘린 것은 comment 여야 한다'
    assert len(comment) < len('Ctrl-1 T[C]')

    card = str(fits.Card('C1_TEMP', value, comment))
    assert len(card) == 80 and card.count("'") == 2


def test_a_value_too_long_for_any_comment_is_cut_not_spilled_into_continue():
    """comment 를 다 지워도 넘치면 **값을 자르고 경고한다** (5.0절).

    ⚠️ 이 자리를 astropy 에 맡기면 안 된다 -- astropy 는 값을 자르지 않고
    `CONTINUE` 규약으로 **카드를 여러 장으로 늘린다.**  그러면 견본이 못박은
    **144 레코드 · 11,520 바이트**가 깨지고 경고는 한 줄도 안 뜬다.
    """
    from ics_sim import fitsout

    huge = 'X' * 120
    value, comment = fitsout._fit_to_card('OBJECT', huge, 'Name of object')
    assert comment == '' and len(value) == 68

    # 다듬은 뒤에는 카드가 정확히 한 장이다.
    assert len(str(fits.Card('OBJECT', value, comment))) == 80
    # 다듬지 않으면 세 장이 된다 -- 이 시험이 지키는 것이 그것이다.
    assert len(str(fits.Card('OBJECT', huge, 'Name of object'))) > 80


def test_the_sample_template_never_trips_the_width_rule():
    """견본 템플릿 카드는 **하나도** 다듬기에 걸리지 않는다.

    걸린다면 견본 자체가 80자를 넘는다는 뜻이고, 바이트 정본이 깨진 것이다.
    폭 규범이 견본 재현을 건드리지 않는다는 것을 여기서 못박는다.
    """
    from ics_sim import fitsout

    for key, kind, width, comment in rawcards.CARDS:
        if key == 'COMMENT' or kind != 'S':
            continue
        text = 'x' * width
        got, cut = fitsout._fit_to_card(key, text, comment)
        assert got == text and cut == comment, key


def test_a_long_observer_input_does_not_grow_the_header(tmp_path):
    """관측자가 긴 이름을 쳐도 헤더 레코드 수가 늘지 않는다.

    `OBJECT`/`OBSERVER`/`PROJID` 는 **관측자가 치는 값**이라 길이가 바깥에서
    온다 -- 규격이 정한 폭(18)을 넘겨 오는 것을 ICS 가 막을 방법이 없다.
    다듬지 않으면 astropy 가 `CONTINUE` 로 카드를 늘리고, 그 순간 견본이
    못박은 **2880B 정렬과 144 레코드**가 깨진다 (5.0절).
    """
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path))
    drive(['OBS>ICS OBJECT ' + 'X' * 100, 'OBS>ICS EXP 5', 'OBS>ICS GO 1'],
          cfg)
    names = [n for n in sorted(os.listdir(tmp_path)) if n.endswith('.fits')]
    assert names, '프레임이 저장되지 않았다'
    for name in names:
        path = os.path.join(tmp_path, name)
        with fits.open(path) as hdul:
            h = hdul[0].header
        assert 'CONTINUE' not in h, name
        assert len(str(h['OBJECT'])) <= 68, '값이 카드 한 장을 넘었다'
        # 헤더부가 2880B 정렬인지 -- 바이트로 직접 센다.
        with open(path, 'rb') as f:
            blob = f.read()
        end = blob.find(b'END' + b' ' * 77)
        assert end >= 0 and end % 80 == 0, name

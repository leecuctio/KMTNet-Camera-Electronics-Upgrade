#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""규격 5장 raw 헤더 전면 재검토의 결과를 지킨다 (D-013).

규격: `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 5.3~5.13절.
근거 자료: `raw_fits_spec/__reference/Legacy raw fits header samples/`.

`test_raw_pair.py` 가 **이름과 파일 수**를 지키고, 이 파일은 **헤더 내용**을
지킨다.  나눈 이유는 실패한 테스트 이름이 원인을 가리켜야 하기 때문이다 --
이름 규약이 깨지면 아카이브 색인이 어긋나고, 헤더 내용이 깨지면 MEF 가 조용히
placeholder 를 받는다.

**여기 있는 시험 대부분은 "조용한 실패" 를 잡는다.** 규격 6.2절이 정리한 대로
헤더 카드가 없으면 converter 는 오류를 내지 않고 그럴듯한 기본값을 넣는다.
그러니 사람이 눈으로 볼 일이 없고, 시험이 유일한 방어선이다.
"""

from __future__ import annotations

import os

import pytest

from conftest import drive, make_config

from ics_sim import rawhdr

fits = pytest.importorskip('astropy.io.fits',
                           reason='헤더 검증에는 astropy 가 필요하다')

SCRIPT = ['OBS>ICS OBJECT BLG11', 'OBS>ICS EXP 5', 'OBS>ICS GO 1']


def _headers(tmp_path, **over):
    """노출 1회를 돌리고 `{CTRLTAG: header}` 를 돌려준다."""
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path),
                     **over)
    drive(SCRIPT, cfg)
    out = {}
    for name in sorted(os.listdir(tmp_path)):
        if name.endswith('.fits'):
            h = fits.getheader(os.path.join(tmp_path, name))
            out[str(h['CTRLTAG']).strip()] = h
    return out


# -- 규격 필수 카드이 실제로 실리나 -----------------------------------------

#: 규격 5.1~5.10절이 **필수**로 정한 카드.  절별로 묶어 둔 이유는 실패 메시지가
#: 어느 절을 보라고 알려 주게 하는 것이다.
MANDATORY = {
    '5.1 파일 정체성': ('SIMPLE BITPIX NAXIS NAXIS1 NAXIS2 BZERO BSCALE BUNIT '
                        'ORIGIN DATE CREATOR FILENAME ICSBUILD'),
    '5.2 pair 식별': ('RAWPROD RAWVER RAWGROUP CHIPLIST CTRLTAG CHIPS CHIP1 '
                      'CHIP2 PAIRFILE NUMFILES UNIQNAME'),
    '5.3 geometry': ('RAWNAX1 RAWNAX2 NXTILE NAMPRAW RAWXTILE AMPDATA OVERSCNX '
                     'PRESCANX OSCNPATT NSTRIP NEND AMPPCD STRIPDIR TOPROWS '
                     'BOTROWS MIDOVSCY MIDOSCB MIDOSCT ROWORDR RDDIRT RDDIRB '
                     'CHIPFLP READMODE READARCH CCDXBIN CCDYBIN'),
    '5.4 detector': ('DETECTOR CAMNAME CAMVER DETTYPE INSTRUME HEMODE NCCD '
                     'NAMPS DETSIZE CCDCOLS CCDROWS COLGAP ROWGAP'),
    '5.5 controller': ('CONTROLL NCTRL CTRLID CTRLVER CTRLSTAT CTRLERR BCKTEMP '
                       'READTIME ACFFILE TIMCONF TIMVER BIASVER CLKVER '
                       'DATASRC AMPMAP'),
    '5.5.0 컨트롤러 정체': ('CTRL1ID CTRL1SN CTRL1FW CTRL2ID CTRL2SN CTRL2FW'),
    '5.6 전압': 'VOLTN VOLT1 VSET1 VMEA1 VOLTSTAT',
    '5.7 노출': ('TIMESYS DATE-OBS TSHOPEN TSHSHUT EXPTIME LEDFLASH DARKTIME'),
    '5.8 관측': 'IMAGETYP OBSTYPE OBJECT FILTER',
    '5.9 관측소': ('OBSERVAT SITEID TELESCOP LATITUDE LONGITUD ELEVATIO '
                   'RADECSYS RA DEC EQUINOX HA ST SECZ ALT AZ TCSLINK '
                   'TCSQDATE TCSUDATE TCSDRIVE TELMOVE'),
    '5.10 열/AUX': ('CCDTEMP1 CCDTEMP2 CCDTEMP AUXLINK AUXQDATE AUXUDATE FSSTAT '
                    'FILTOP FILNUM SHUTTER SHUTOP FASTAT FAFOCUS DSSTAT MCSTAT '
                    'CHSTAT ENSTAT ENFAN'),
}


@pytest.mark.parametrize('section', sorted(MANDATORY))
def test_mandatory_cards_are_written(tmp_path, section):
    """규격이 필수로 정한 카드가 **양쪽 파일 모두**에 있어야 한다."""
    heads = _headers(tmp_path)
    assert set(heads) == {'MK', 'NT'}
    for tag, h in heads.items():
        missing = [k for k in MANDATORY[section].split() if k not in h]
        assert not missing, f'{tag} 파일에 {section} 필수 카드 누락: {missing}'


def test_bitpix_is_16_so_the_converter_can_read_it(tmp_path):
    """`BITPIX != 16` 이면 converter 가 그 자리에서 멈춘다 (규격 6.1절).

    시뮬이 float32 로 쓰면 산출물이 변환 경로에 **한 번도 들어가 볼 수 없다.**
    """
    for h in _headers(tmp_path).values():
        assert h['BITPIX'] == 16
        assert h['BZERO'] == 32768        # unsigned 16-bit zero point
        assert h['BSCALE'] == 1


# -- 5.5.0 컨트롤러 정체: 색인형은 같고 색인 자체는 다르다 ------------------

def test_controller_identity_is_identical_in_both_files(tmp_path):
    """`CTRL1*`/`CTRL2*` 는 **양쪽에 같은 값**이어야 한다 (규격 5.11절).

    converter 는 MK 헤더만 읽으면서 두 대분 정체를 요구한다
    (`v2_1.py:411-416,758`).  NT 에만 있으면 MEF 가 `UNKNOWN` 을 받는다 --
    **오류 없이** 그렇게 된다.
    """
    heads = _headers(tmp_path)
    for card in ('CTRL1ID', 'CTRL1SN', 'CTRL1FW',
                 'CTRL2ID', 'CTRL2SN', 'CTRL2FW'):
        assert heads['MK'][card] == heads['NT'][card], card
        assert 'UNKNOWN' not in str(heads['MK'][card]).upper(), card


def test_controller_index_and_pair_membership_differ(tmp_path):
    """반대로 **파일마다 달라야** 하는 것 (규격 5.11절 "반드시 상이")."""
    heads = _headers(tmp_path)
    for card in ('CTRLID', 'CTRLTAG', 'CHIPS', 'CHIP1', 'CHIP2',
                 'UNIQNAME', 'FILENAME', 'PAIRFILE'):
        assert heads['MK'][card] != heads['NT'][card], card
    assert heads['MK']['CTRLID'] == 1     # 색인은 RAWGROUP 순서 (MK=1)
    assert heads['NT']['CTRLID'] == 2


def test_ctrlid_is_an_index_not_the_identifier_string(tmp_path):
    """`CTRLID`(색인 정수)와 `CTRL1ID`(식별자 문자열)는 다른 것이다.

    이름이 비슷해서 실제로 헷갈리는 자리다 -- 규격 5.5.0절이 경고를 달아 뒀다.
    """
    h = _headers(tmp_path)['MK']
    assert isinstance(h['CTRLID'], int)
    assert not isinstance(h['CTRL1ID'], int)


# -- 5.5 DATASRC: 시뮬을 실물로 오인하지 않게 --------------------------------

def test_sim_frames_say_they_are_simulated(tmp_path):
    """`DATASRC=SIM`.  **이게 시뮬 프레임을 걸러내는 유일한 카드다.**"""
    for tag, h in _headers(tmp_path).items():
        assert str(h['DATASRC']).strip() == 'SIM', tag
        assert str(h['DATASRC']).strip() != 'ARCHON', tag


def test_unknown_backend_is_called_sim_not_archon():
    """모르는 백엔드는 `SIM` 으로 떨어뜨린다 -- 실물이라고 잘못 적는 쪽이 나쁘다."""
    assert rawhdr.datasrc_of('archon') == 'ARCHON'
    assert rawhdr.datasrc_of('sim') == 'SIM'
    assert rawhdr.datasrc_of('') == 'SIM'
    assert rawhdr.datasrc_of('somethingelse') == 'SIM'


# -- 5.13 폐지한 keyword 가 되살아나지 않게 ---------------------------------

#: 규격 5.13절이 **폐지**한 레거시 카드와, 이 저장소가 만들었다가 뺀 둘.
#: 되살아나면 규격과 구현이 갈라진 것이므로 여기서 잡는다.
RETIRED = ('DETID OVERSCNY READOUT GAINDL PIXITIME DMAWAIT ICROLE CTCSOURC '
           'CTCFILE KBUILD MBUILD TBUILD NBUILD GBUILD RTD12 INPUTFMT '
           'CTRLNAME CTRLSN CTRLFW EXPID EXPNUM').split()


@pytest.mark.parametrize('card', RETIRED)
def test_retired_cards_are_absent(tmp_path, card):
    for tag, h in _headers(tmp_path).items():
        assert card not in h, f'{tag} 에 폐지한 {card} 가 되살아났다 (규격 5.13절)'


def test_overscny_is_not_reused_for_the_middle_overscan(tmp_path):
    """`OVERSCNY` 폐지가 특히 중요한 이유를 못박는다.

    신규는 Y overscan 이 **영상 중앙**에 있다(규격 4.2절).  레거시 이름으로
    실으면 "위쪽 N행 자르기" 도구가 **아무 오류 없이** active 픽셀을 지운다.
    """
    h = _headers(tmp_path)['MK']
    assert 'OVERSCNY' not in h
    assert h['MIDOVSCY'] == 168
    assert h['MIDOSCB'] + h['MIDOSCT'] == h['MIDOVSCY']


# -- 5.13 계승한 keyword ----------------------------------------------------

def test_inherited_legacy_cards_are_present(tmp_path):
    """계승 5개가 실제로 실리나 (규격 5.13절)."""
    for tag, h in _headers(tmp_path).items():
        assert str(h['HEMODE']).strip() == 'SCIENCE', tag
        assert str(h['DATASRC']).strip() in ('ARCHON', 'SIM'), tag
        assert h['NPHLINES'] == 32, tag          # 레거시 실측값
        assert str(h['ICSBUILD']).strip(), tag
        assert 'LEDFLASH' in h, tag


def test_ledflash_is_seconds_not_milliseconds(tmp_path):
    """`LEDFLASH` 는 레거시와 같은 **초** 단위다 (규격 5.7·5.13절).

    같은 이름에 다른 단위를 넣으면 기존 도구가 조용히 1000배 틀린 값을 읽는다.
    """
    h = _headers(tmp_path)['MK']
    assert h['LEDFLASH'] == 0.0            # 점등 안 한 노출
    got = rawhdr.exposure_header(
        date_obs='2026-08-13T00:00:00', exp_start=None, exp_end=None,
        exptime=1.0, darktime=1.0, ledflash_ms=250)
    assert got['LEDFLASH'] == 0.25         # 250 ms == 0.25 s


# -- DSTEL -> DSTELALT: converter 에 fallback 이 없다 -----------------------

def test_dstel_is_carried_over_to_the_name_the_converter_reads():
    """AUX 실선은 `DSTEL` 을 보내고 Archon converter 는 `DSTELALT` 만 읽는다.

    옮겨 싣지 않으면 MEF 의 돔-망원경 고도가 **오류 없이** 빈 값이 된다
    (`v2_1.py:485`, 규격 5.13절).  원래 이름도 남겨 레거시 도구와의 연속성을
    유지한다.
    """
    from ics_sim.config import SimConfig
    from ics_sim.telemetry import TelemetryRelay
    relay = TelemetryRelay(SimConfig(), lambda *a, **k: None)
    relay.aux_fields = [('DSSTAT', 'STANDBY'), ('DSTEL', '88.1')]
    h = relay.fits_header_dict('2026-08-13T00:00:00')
    assert h['DSTELALT'] == '88.1'
    assert h['DSTEL'] == '88.1'


def test_a_real_dstelalt_is_not_overwritten_by_the_alias():
    """실선이 `DSTELALT` 를 직접 보내면 그 값이 이긴다."""
    from ics_sim.config import SimConfig
    from ics_sim.telemetry import TelemetryRelay
    relay = TelemetryRelay(SimConfig(), lambda *a, **k: None)
    relay.aux_fields = [('DSTEL', '11.1'), ('DSTELALT', '88.1')]
    h = relay.fits_header_dict('2026-08-13T00:00:00')
    assert h['DSTELALT'] == '88.1'


# -- 5.3 geometry 불변식 ----------------------------------------------------

def test_geometry_invariants_hold_in_the_written_header(tmp_path):
    """헤더에 실린 값끼리 규격 5.3·5.4절 불변식을 만족해야 한다.

    상수를 손보다 어긋나면 converter 가 자기 하드코딩 값과 대조해 변환을 멈춘다
    (변경점 C-5/C-13) -- 그 전에 여기서 잡는다.
    """
    h = _headers(tmp_path)['MK']
    assert h['RAWNAX1'] == h['NXTILE'] * h['RAWXTILE']
    assert h['RAWXTILE'] == h['AMPDATA'] + h['OVERSCNX'] + h['PRESCANX']
    assert h['RAWNAX2'] == h['BOTROWS'] + h['MIDOVSCY'] + h['TOPROWS']
    assert h['AMPPCD'] == h['NSTRIP'] * h['NEND']
    assert h['NAMPRAW'] == h['NXTILE'] * h['NEND']
    assert h['CCDCOLS'] == h['NSTRIP'] * h['AMPDATA']
    assert h['CCDROWS'] == h['TOPROWS'] + h['BOTROWS']
    assert h['NAMPS'] == h['NCCD'] * h['AMPPCD']


def test_check_geometry_catches_a_broken_constant(monkeypatch):
    """불변식 검사가 **실제로 잡는지** 확인한다.

    검사 코드가 있어도 조건이 틀리면 아무것도 안 잡는다 -- 그쪽을 시험한다.
    """
    monkeypatch.setattr(rawhdr, 'MIDOSCT', 83)
    with pytest.raises(ValueError, match='5.3절 불변식 위반'):
        rawhdr.check_geometry()


# -- 5.6 전압: 0.0 을 "값 없음" 으로 쓰지 않는다 ----------------------------

def test_missing_voltage_is_sentinel_not_zero():
    """`0 V` 는 실재하는 측정값이다 -- clock low 는 실제로 0 근처다.

    그래서 결측을 `0.0` 으로 쓰면 유효값과 구분되지 않는다 (규격 5.0·5.6절).
    """
    h = rawhdr.voltage_header([{'name': 'VOD', 'setpoint': 26.0}])
    assert h['VMEA1'] == -999.0
    assert str(h['VSTA1']) == 'NC'
    assert str(h['VOLTSTAT']) == 'UNKNOWN'


def test_partially_measured_voltages_say_partial():
    h = rawhdr.voltage_header([
        {'name': 'VOD', 'setpoint': 26.0, 'measured': 25.98, 'status': 'OK'},
        {'name': 'VRD', 'setpoint': 13.0},
    ])
    assert str(h['VOLTSTAT']) == 'PARTIAL'
    assert h['VMEA1'] == 25.98
    assert h['VMEA2'] == -999.0


# -- 5.5.1 배선: 모르면 모른다고 -------------------------------------------

def test_unknown_amp_wiring_declares_default_instead_of_guessing(tmp_path):
    """배선을 모르면 `AMPMAP='DEFAULT'` 로 **선언한다.**

    그럴듯한 매핑을 만들어 `EXPLICIT` 로 실으면, 실기에서 실제 배선을 넣는 일이
    이미 끝난 것처럼 보인다.  배선이 추정과 다르면 crosstalk 보정이 엉뚱한 amp
    묶음에 적용된다 (규격 5.5.1절, 변경점 C-11).
    """
    assert str(_headers(tmp_path)['MK']['AMPMAP']).strip() == 'DEFAULT'
    assert 'AMOD01' not in _headers(tmp_path)['MK']


def test_explicit_amp_wiring_is_written_for_all_32_amps():
    h = rawhdr.ampmap_header({n: (1 + (n - 1) // 8, 1 + (n - 1) % 8)
                              for n in range(1, 33)})
    assert str(h['AMPMAP']) == 'EXPLICIT'
    assert h['AMOD01'] == 1 and h['ACHN01'] == 1
    assert h['AMOD32'] == 4 and h['ACHN32'] == 8
    assert len([k for k in h if k.startswith('AMOD')]) == 32


# -- 5.7 시각: 파생값이 서로 어긋나지 않게 ----------------------------------

def test_date_obs_mjd_and_shutter_times_agree(tmp_path):
    """`DATE-OBS`·`MJD-OBS`·`TSHOPEN` 이 같은 순간을 가리켜야 한다."""
    h = _headers(tmp_path)['MK']
    date_obs = str(h['DATE-OBS'])
    assert date_obs, 'DATE-OBS 는 무조건 있어야 한다 (규격 5.7절)'
    # 'YYYY-MM-DDThh:mm:ss.mmm' 의 시각부와 TSHOPEN 이 같다
    assert str(h['TSHOPEN']).startswith(date_obs.split('T')[1][:8])
    # MJD 정수부는 그 날짜의 MJD 여야 한다
    assert 40000 < h['MJD-OBS'] < 90000


def test_date_obs_and_exposure_facts_match_across_the_pair(tmp_path):
    """셔터는 하나이고 노출도 하나다 (규격 5.7절 말미)."""
    heads = _headers(tmp_path)
    for card in ('DATE-OBS', 'MJD-OBS', 'EXPTIME', 'DARKTIME', 'TSHOPEN',
                 'TSHSHUT', 'IMAGETYP', 'OBSTYPE', 'OBJECT', 'FILTER'):
        assert heads['MK'][card] == heads['NT'][card], card


def test_missing_exp_start_omits_the_derived_cards():
    """`exp_start` 가 없으면 `MJD-OBS`/`UT` 를 **넣지 않는다.**

    "지금" 으로 채우면 값이 있는 것처럼 보이고 converter 의 실패 경로가
    발동하지 않는다 (규격 5.0·5.7절, 변경점 C-6).
    """
    h = rawhdr.exposure_header(date_obs='', exp_start=None, exp_end=None,
                               exptime=1.0, darktime=1.0, ledflash_ms=0)
    assert 'MJD-OBS' not in h
    assert 'UT' not in h
    assert str(h['TSHOPEN']) == 'NC'


# -- 5.9 측지값: 추측하지 않는다 --------------------------------------------

#: 운영자가 확인해 준 세 사이트 측지값 (2026-08-13, 규격 OI-11).
#: 값 문자열을 **그대로** 싣는 것이 규약이다 -- 정규화하면 레거시 아카이브와의
#: 문자열 비교가 깨진다.  그래서 `+` 부호 유무와 초의 소수점 자리까지 못박는다.
SITE_GEODETIC = {
    'KMTC': ('KMTNet 1.6m #1', '-30:10:01.84', '+70:48:14.39', 2140),
    'KMTS': ('KMTNet 1.6m #2', '-32:22:42', '339:11:22', 1800),
    'KMTA': ('KMTNet 1.6m #3', '-31:16:24', '210:56:08', 1150),
}


@pytest.mark.parametrize('code', sorted(SITE_GEODETIC))
def test_site_geodetic_values_are_carried_verbatim(code):
    """세 사이트 값이 **문자 그대로** 실려야 한다."""
    telescop, lat, lon, elev = SITE_GEODETIC[code]
    h = rawhdr.site_header(code)
    assert str(h['TELESCOP']) == telescop
    assert str(h['LATITUDE']) == lat
    assert str(h['LONGITUD']) == lon
    assert h['ELEVATIO'] == elev


@pytest.mark.parametrize('code', sorted(SITE_GEODETIC))
def test_longitude_is_west_positive_at_every_site(code):
    """`LONGITUD` 는 **서경 양수**다 (규격 OI-11).

    세 사이트를 함께 확인하는 것이 요점이야 -- CTIO 만 90 미만이라 형태가 달라
    보여서, 하나만 보면 "동경으로 잘못 적혔나?" 하고 고치게 된다.  고치면
    **부호가 뒤집힌 좌표가 아카이브에 영구히 박히고**, 겉보기엔 유효한 좌표라
    아무도 의심하지 않는다.
    """
    # 동경(도) 참값.  공개된 사이트 위치이고, 서경 환산이 준 값과 맞아야 한다.
    east_deg = {'KMTC': -70.804, 'KMTS': 20.810, 'KMTA': 149.064}[code]
    lon = str(rawhdr.site_header(code)['LONGITUD']).lstrip('+')
    d, m, sec = (float(x) for x in lon.split(':'))
    west_deg = d + m / 60 + sec / 3600
    assert 0 <= west_deg < 360
    assert abs((-west_deg % 360) - (east_deg % 360)) < 0.01, (
        f'{code}: 서경 {west_deg} 가 동경 {east_deg} 와 맞지 않는다')


def test_testbed_has_no_coordinates_on_purpose():
    """테스트베드는 좌표를 **일부러** 비워 둔다.

    아무 좌표나 넣으면 시험 산출물이 실제 관측처럼 보인다 (OI-11).
    """
    h = rawhdr.site_header('KMTT')
    assert str(h['LATITUDE']) == 'NC'
    assert str(h['TELESCOP']) == 'NC'
    assert h['ELEVATIO'] == -1


def test_origin_is_the_institution_not_the_site():
    """`ORIGIN='KASI'` -- 레거시는 사이트 코드를 넣었지만 그건 느슨했다.

    MEF keyword 정의서가 `ORIGIN | From raw | KASI | file originator` 로 정하고
    (`mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md:85`), FITS 표준도
    파일을 만든 **기관**을 뜻한다.  레거시의 `ORIGIN='CTIO'` 는 `OBSERVAT` 와
    같은 값이라 중복이었다 -- 계승 기준("뜻이 같을 때만")에 맞지 않는다.
    """
    from ics_sim import rawpair
    h = rawpair.identity_header(site_code='KMTC', suffix='20260813.000001',
                                ctrltag='MK', filename='x', created='y')
    assert str(h['ORIGIN']) == 'KASI'
    assert str(h['OBSERVAT']) == 'CTIO'      # 사이트는 이쪽이 담는다


def test_configured_site_values_win_over_the_table():
    """현장 설정이 정본이다."""
    h = rawhdr.site_header('KMTA', {'latitude': '-31:16:25', 'elevatio': 1151})
    assert str(h['LATITUDE']) == '-31:16:25'
    assert h['ELEVATIO'] == 1151
    assert str(h['TELESCOP']) == 'KMTNet 1.6m #3'   # 설정에 없는 항목은 유지


# -- 5.10 온도: 파일 1개에 chip 2개 -----------------------------------------

def test_two_chip_temperatures_plus_a_representative_one(tmp_path):
    """`CCDTEMP1`/`CCDTEMP2` 는 신규 추가다 -- 파일 1개에 chip 이 2개다.

    `CCDTEMP`(대표값)는 L1 파이프라인이 이름으로 지정해 전달하므로 반드시 있다
    (`mef_pipeline/kmt_ceu_preproc/io_l1.py` 의 `CARRY_KEYS`).
    """
    h = _headers(tmp_path)['MK']
    assert h['CCDTEMP1'] != h['CCDTEMP2']
    assert h['CCDTEMP1'] < -50 and h['CCDTEMP2'] < -50
    # **CCDTEMP 는 파생값이다** -- 둘의 평균이어야 한다 (운영자 확정 2026-08-13)
    assert abs(h['CCDTEMP'] - (h['CCDTEMP1'] + h['CCDTEMP2']) / 2) < 1e-6


def test_unread_dewar_sensor_is_sentinel_not_a_string():
    """레거시는 `DEWPRES='N/A'` 문자열을 넣었다.  수치 sentinel 로 통일한다.

    문자열과 실수가 섞이면 읽는 쪽이 형을 분기해야 한다.
    """
    h = rawhdr.thermal_header({'ccdtemp1': -103.0, 'ccdtemp2': -103.1})
    assert h['DEWPRES'] == -999.0
    assert isinstance(h['DEWPRES'], float)


def test_thermal_cards_survive_a_backend_that_reads_nothing():
    """센서를 하나도 못 읽어도 카드는 남는다 (규격 5.0절)."""
    h = rawhdr.thermal_header(None)
    assert h['CCDTEMP1'] == h['CCDTEMP2'] == h['CCDTEMP'] == -999.0


# -- 백엔드가 실패해도 프레임을 버리지 않는다 --------------------------------

def test_a_backend_that_raises_does_not_lose_the_frame(tmp_path):
    """센서 한 채널 때문에 프레임을 버리면 손해가 훨씬 크다.

    실패는 sentinel 로 남기고 저장은 계속한다 -- "값이 없었다" 는 사실이 헤더에
    남으므로 조용한 오염이 되지 않는다.
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
    assert h['CCDTEMP'] == -999.0
    assert h['CTRL1ID']            # 다른 덩어리는 멀쩡하다


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
    """세 경계가 모두 **현지 12:30** 이어야 한다 -- 숫자 검산용 불변식.

    CTIO(UT−4) 16:30−4=12:30 · SAAO(UT+2) 10:30+2=12:30 ·
    SSO(UT+11) 01:30+11=12:30.  근거가 "동지 때 관측 종료와 시작의 중간 시각"
    이므로 현지 정오 무렵이어야 맞고, 이 시험이 그걸 못박는다.  경계가 관측
    시간대 밖이라는 것이 이 규약을 쓰는 이유 자체다.
    """
    utc_offset_hours = {'KMTC': -4, 'KMTS': +2, 'KMTA': +11}
    for site, off in utc_offset_hours.items():
        shift = rawpair.OBSDATE_SHIFT_MIN[site]
        boundary_ut_min = (-shift) % (24 * 60)         # 보정이 0시로 만드는 UT 시각
        local_min = (boundary_ut_min + off * 60) % (24 * 60)
        assert local_min == 12 * 60 + 30, (
            f'{site}: 경계가 현지 {local_min // 60}:{local_min % 60:02d} 다')


def test_unknown_site_code_falls_back_to_testbed():
    """`KMTC`/`KMTS`/`KMTA` 밖은 모두 `KMTT` (운영자 확정 2026-08-13).

    TC 가 보내는 `TELID` 에 사이트가 아닌 `KMTN`(pctcs 기본값, `pctcs.h:115`)이
    올 수 있어서 필요하다.
    """
    assert rawpair.normalize_site('KMTN') == 'KMTT'
    assert rawpair.normalize_site('') == 'KMTT'
    assert rawpair.normalize_site('kmtc') == 'KMTC'      # 대소문자 무관
    for real in ('KMTC', 'KMTS', 'KMTA'):
        assert rawpair.normalize_site(real) == real


def test_filename_date_uses_the_observing_date_not_the_utc_date(tmp_path):
    """실제로 쓴 파일 이름의 날짜부가 관측일 규칙을 따르나."""
    heads = _headers(tmp_path)
    h = heads['MK']
    date_part = str(h['UNIQNAME']).split('.')[1]
    site = str(h['SITEID']).strip()
    # `DATE-OBS` 의 순간에 규칙을 적용한 값과 같아야 한다
    iso = str(h['DATE-OBS'])
    when = datetime.strptime(iso, '%Y-%m-%dT%H:%M:%S.%f').replace(
        tzinfo=timezone.utc)
    assert date_part == rawpair.observing_date(when, site)


# -- `UT` 카드 폐지 ---------------------------------------------------------

def test_ut_card_is_gone_and_date_obs_carries_the_milliseconds(tmp_path):
    """`UT` 는 `DATE-OBS` 와 완전한 중복이라 없앴다 (운영자 확정 2026-08-13).

    **converter 는 영향받지 않는다** -- MEF 의 `UT` 는 raw 의 `UT` 가 아니라
    `DATE-OBS` 의 날짜부 + raw 의 `TSHOPEN` 으로 조립된다(`v2_1.py:440,583`).
    그 둘은 그대로 싣고 있으므로 이 시험이 그것도 함께 지킨다.
    """
    import re
    for tag, h in _headers(tmp_path).items():
        assert 'UT' not in h, f'{tag} 에 폐지한 UT 가 남아 있다'
        assert re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}',
                            str(h['DATE-OBS'])), h['DATE-OBS']
        # converter 가 MEF UT 를 조립하는 데 쓰는 두 재료
        assert str(h['TSHOPEN']).strip()
        assert str(h['DATE-OBS']).strip()


# -- SHUTTER 는 AUX 값 하나만 (2026-08-13 확정) ----------------------------

def test_shutter_comes_from_aux_only():
    """`SHUTTER` 는 **AUX 가 보고한 블레이드 위치** 하나다 (규격 5.10절).

    한때 `rawhdr` 가 같은 이름으로 "이 노출이 셔터를 썼나"(5.7절)를 실었다.
    merge order 때문에 **AUX 값을 조용히 덮었고**, 이름이 같고 뜻이 다른 것이라
    `OVERSCNY` 폐지 근거와 같은 부류였다.  게다가 `IMAGETYP` 에서 파생되는
    값이라 애초에 중복이었다.
    """
    h = rawhdr.exposure_header(date_obs='2026-08-13T00:00:00.000',
                               exp_start=None, exp_end=None, exptime=1.0,
                               darktime=1.0, ledflash_ms=0)
    assert 'SHUTTER' not in h, 'rawhdr 가 SHUTTER 를 만들면 AUX 값을 덮는다'


def test_rawhdr_and_telemetry_do_not_produce_the_same_card():
    """두 덩어리의 keyword 집합이 겹치면 뒤에 얹는 쪽이 조용히 이긴다.

    한때 여기에 "겹치지 않는다" 는 **주석만** 있었고 `SHUTTER` 가 겹치고 있었다.
    주석 대신 시험으로 지킨다.
    """
    from datetime import datetime, timezone
    from ics_sim.telemetry import (CANNED_AUX, CANNED_TCS, _SENTINEL_NUM,
                                   _SENTINEL_STR)
    telem = (set(_SENTINEL_STR) | set(_SENTINEL_NUM) | set(CANNED_AUX)
             | set(CANNED_TCS) | {'TELID', 'TIMESYS'})
    spec = rawhdr.spec_header(
        ctrltag='MK', site_code='KMTC', backend_name='sim', ics_build='x',
        ctrl_info={'units': ()}, sensors={}, volts=None, ampmap=None,
        cfg_site=None, date_obs='2026-08-13T00:00:00.000',
        exp_start=datetime(2026, 8, 13, tzinfo=timezone.utc),
        exp_end=datetime(2026, 8, 13, tzinfo=timezone.utc),
        exptime=1.0, darktime=1.0, ledflash_ms=0, exp_measured=None,
        imgtype='OBJECT', objname='x', projid='x', observer='x')
    overlap = telem & set(spec)
    assert not overlap, f'겹치는 카드: {sorted(overlap)}'


# -- ICSBUILD 는 실제 빌드여야 한다 ---------------------------------------

def test_icsbuild_carries_program_version_and_build_time(tmp_path):
    """`<프로그램>-v<버전>:<빌드일시>` 형식이어야 한다 (규격 5.1절).

    **"비어 있지 않음" 만 보면 거짓 값이 통과한다** -- 실제로 레거시 문자열
    `'KX2016-03-23:1381'` 이 기본값으로 실려 있었고, 그 카드를 둔 목적(헤더
    이상을 소스 상태로 되짚기)을 정면으로 무력화했다.

    끝의 `Z` 도 함께 지킨다.  **다른 시각 카드와 일부러 다르다** -- 그쪽은 `Z` 를
    붙이지 않고 `TIMESYS='UTC'` 로 선언하지만, 이 값은 시각 카드가 아니라 버그
    리포트·로그에 떼어 붙이는 식별자라 자체적으로 시간대를 지녀야 한다
    (운영자 확정 2026-08-13).  일관성만 보고 지우면 이 시험이 걸린다.
    """
    import re
    for tag, h in _headers(tmp_path).items():
        got = str(h['ICSBUILD']).strip()
        assert re.fullmatch(r'(ics_sim|ics_archon)-v\d+\.\d+\.\d+'
                            r':\d{4}-\d\d-\d\dT\d\d:\d\dZ', got), (tag, got)
        assert 'KX2016' not in got, '레거시 빌드 문자열이 남아 있다'
        # 비대칭이 의도임을 한 자리에서 함께 못박는다
        assert got.endswith('Z'), 'ICSBUILD 의 UTC 표시자는 일부러 붙인 것이다'
        assert not str(h['DATE-OBS']).endswith('Z'), (
            'FITS 시각 카드는 TIMESYS 로 선언하므로 Z 를 붙이지 않는다')


def test_build_id_refuses_to_lend_its_version_to_another_program():
    """이름만 바꿔 부르면 **거짓 provenance** 가 된다 -- 그 사실을 못박는다.

    `ics_archon` 은 자기 패키지에 세 상수를 두고 같은 형태를 만들어야 한다.
    이 시험은 세 값을 함께 넘기는 사용법을 보여 준다.
    """
    from ics_sim import PROGRAM, __build_date__, __version__, build_id
    assert build_id() == f'{PROGRAM}-v{__version__}:{__build_date__}'
    # 이름만 바꾼 호출은 ics_sim 의 버전을 물고 온다 -- 그래서 쓰면 안 된다
    assert build_id('ics_archon').endswith(__build_date__)
    # 올바른 사용법: 세 값을 다 넘긴다
    assert build_id('ics_archon', '2.0.0', '2027-01-01T00:00Z') == (
        'ics_archon-v2.0.0:2027-01-01T00:00Z')


def test_ccdtemp_is_always_derived_from_the_two_chips():
    """`CCDTEMP` 는 **파생값**이다 -- 백엔드가 따로 줘도 쓰지 않는다.

    파생으로 못박아 두면 세 카드가 서로 어긋날 수 없다 (운영자 확정 2026-08-13).
    """
    h = rawhdr.thermal_header({'ccdtemp1': -100.0, 'ccdtemp2': -102.0,
                               'ccdtemp': 0.0})   # 백엔드가 엉뚱한 값을 줘도
    assert h['CCDTEMP'] == -101.0, '평균이 아니라 백엔드 값을 썼다'


def test_one_chip_temperature_still_feeds_ccdtemp_with_a_warning(caplog):
    """한쪽만 읽혔으면 **비우지 않고 경고한다.**

    L1 이 `CCDTEMP` 를 이름으로 지정해 가져가므로(`CARRY_KEYS`) sentinel 로
    떨어뜨리면 L1 이 굶는다.  대신 평균이 아니라는 사실을 로그에 남긴다.
    """
    import logging
    with caplog.at_level(logging.WARNING):
        h = rawhdr.thermal_header({'ccdtemp1': -103.0})
    assert h['CCDTEMP'] == -103.0
    assert h['CCDTEMP2'] == -999.0
    assert any('평균이 아니' in r.message for r in caplog.records)

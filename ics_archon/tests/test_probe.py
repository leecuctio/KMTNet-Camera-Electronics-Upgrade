#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""실기 첫 실행 도구 (`tools/probe_archon.py`) 를 가짜 컨트롤러로 돌린다.

**도구 자체가 시험되지 않으면 실기 현장에서 처음 실행된다.**  거기서 오타로
죽으면 그 실행 기회를 잃는다 -- 그래서 세 단계를 전부 여기서 한 번 돌려 본다.
"""

from __future__ import annotations

import glob
import os
import sys

import pytest
from fake_archon import FakeArchon

_TOOLS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools')
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import probe_archon                                       # noqa: E402

INI = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    os.pardir, 'ics_archon.ini'))
NX, NY = 12, 4

ACF_TEXT = """[CONFIG]
TRIGOUTFORCE=0
TRIGOUTLEVEL=1
PARAMETER1="Exposures=1"
PARAMETER2="IntMS=0"
"""


@pytest.fixture(autouse=True)
def _clean_verdicts():  # noqa: ANN201
    probe_archon._verdicts.clear()       # noqa: SLF001
    yield


@pytest.fixture()
def fake():  # noqa: ANN201
    srv = FakeArchon(width=NX, height=NY)
    srv.start()
    yield srv
    srv.shutdown()


def run(args, tmp_path):  # noqa: ANN001
    """기하를 시험 크기로 줄여서 도구를 돌린다."""
    import ics_archon.config as acfg_mod
    real_load = acfg_mod.load

    def small(path):  # noqa: ANN001
        cfg = real_load(path)
        cfg.naxis1, cfg.naxis2 = NX, NY
        return cfg

    probe_archon.acfg_mod.load = small
    try:
        return probe_archon.main(args + ['-c', INI, '--out', str(tmp_path)])
    finally:
        probe_archon.acfg_mod.load = real_load


def marks():  # noqa: ANN201
    return [m for m, _ in probe_archon._verdicts]        # noqa: SLF001


def labels():  # noqa: ANN201
    return ' | '.join(l for _, l in probe_archon._verdicts)  # noqa: SLF001


def test_stage1_is_read_only_and_confirms_the_three_assumptions(fake, tmp_path):  # noqa: ANN001
    """1단계는 **전원을 켜지 않는다.**  그리고 잠정 3자리를 다 짚는다."""
    rc = run(['--host', '127.0.0.1', '--port', str(fake.port)], tmp_path)
    assert rc == 0, labels()
    assert probe_archon.BAD not in marks(), labels()

    # 전원을 건드리지 않았다 -- 1단계의 존재 이유다.
    assert 'POWERON' not in fake.seen
    assert 'POWEROFF' not in fake.seen
    assert not fake.powered

    # 세 가정을 다 확인했다.
    text = labels()
    assert '규격 5.6.1절 자리 표와 정합한다' in text     # STATUS 자리
    assert 'BUFnLINES' in text                          # 진행률
    assert '기하가 선언과 일치' in text                 # 산출물 기하
    assert 'BACKPLANE_ID' in text                       # CTRLnSN 원천


def test_stage1_reports_a_module_layout_that_breaks_the_field_table(tmp_path):  # noqa: ANN001
    """장착 모듈이 자리 표와 어긋나면 문제로 낸다.

    **이것이 미검증 1번의 실제 판정 경로다.**  조용히 넘기면 `Cn_TEMP` 의 자리가
    실물과 다른 채로 자료가 쌓인다.

    ⚠️ **판정 기준이 바뀌었다** (2026-08-27) -- 종전에는 "AD 모듈이 슬롯 5~8
    인가" 였고 실기 정상 구성(AD = 5·8)에서 오경보를 냈다.  지금은 자리 표
    (규격 5.6.1절)가 자리를 준 모듈과 실제 장착 모듈을 비교한다.
    """
    system = {'BACKPLANE_ID': 'AB', 'BACKPLANE_TYPE': '1',
              'BACKPLANE_VERSION': '1.0.408',
              'MOD3_TYPE': '17', 'MOD4_TYPE': '17',
              'MOD5_TYPE': '1', 'MOD6_TYPE': '1'}
    srv = FakeArchon(width=NX, height=NY, system=system)
    srv.start()
    try:
        rc = run(['--host', '127.0.0.1', '--port', str(srv.port)], tmp_path)
    finally:
        srv.shutdown()
    assert rc == 1
    text = labels()
    # 슬롯 6 은 장착됐지만 자리 표에 없고, 1·2·8·9·10·11 은 자리 표에 있는데 없다.
    assert '[6]' in text
    assert '자리 표의 슬롯' in text


def test_stage1_reports_each_missing_status_field(tmp_path):  # noqa: ANN001
    """온도 자리·전원 레일 결측을 **자리 하나씩** 보고한다."""
    from fake_archon import DEFAULT_STATUS
    status = dict(DEFAULT_STATUS)
    del status['MOD9/TEMP']
    del status['P6V_I']
    srv = FakeArchon(width=NX, height=NY, status=status)
    srv.start()
    try:
        rc = run(['--host', '127.0.0.1', '--port', str(srv.port)], tmp_path)
    finally:
        srv.shutdown()
    assert rc == 1
    text = labels()
    assert 'MOD9/TEMP' in text
    assert '전원 레일 결측: P6V' in text


def test_stage1_reports_a_geometry_mismatch(fake, tmp_path):  # noqa: ANN001
    """선언 기하와 다르면 본편이 fetch 앞에서 거부한다 -- 미리 알려 준다."""
    fake.width = NX * 2
    rc = run(['--host', '127.0.0.1', '--port', str(fake.port)], tmp_path)
    assert rc == 1
    assert '기하 불일치' in labels()


def test_stage2_checks_the_parameter_slots_without_writing(fake, tmp_path):  # noqa: ANN001
    """2단계도 읽기 전용이다 -- `RCONFIG` 로 확인만 한다."""
    acf = tmp_path / 'probe.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')
    rc = run(['--host', '127.0.0.1', '--port', str(fake.port),
              '--acf', str(acf)], tmp_path)
    assert rc == 0, labels()
    assert 'POWERON' not in fake.seen
    assert not any(c.startswith('WCONFIG') for c in fake.seen)
    assert 'CLEARCONFIG' not in fake.seen
    assert 'PARAMETER2' in labels() and 'PARAMETER1' in labels()
    # 설정을 아직 안 올린 컨트롤러는 **헛경보가 아니라 안내**다 (WARN).
    assert '비어 있다' in labels()
    assert probe_archon.BAD not in marks(), labels()


def test_stage2_flags_a_slot_the_acf_does_not_have(fake, tmp_path):  # noqa: ANN001
    """ACF 에 그 슬롯이 없으면 노출 시간이 **조용히** 안 바뀐다 -- 문제로 낸다."""
    acf = tmp_path / 'probe.acf'
    acf.write_text('[CONFIG]\nTRIGOUTFORCE=0\n', encoding='ascii')
    rc = run(['--host', '127.0.0.1', '--port', str(fake.port),
              '--acf', str(acf)], tmp_path)
    assert rc == 1
    assert "설정 줄 'PARAMETER2' 이 없다" in labels()


def test_stage3_measures_readout_and_writes_one_readable_fits(fake, tmp_path):  # noqa: ANN001
    """3단계 -- 전원 ON · 독출 시간 실측 · FETCH 속도 · FITS 1장.

    **`--expose` 를 줘야만 돈다**, 그리고 끝나면 반드시 `POWEROFF` 다.
    """
    acf = tmp_path / 'probe.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')
    rc = run(['--host', '127.0.0.1', '--port', str(fake.port),
              '--acf', str(acf), '--expose', '0', '--write',
              '--poll', '0.01', '--poweron-wait', '0'], tmp_path)
    assert rc == 0, labels()

    assert 'CLEARCONFIG' in fake.seen and 'APPLYALL' in fake.seen
    assert fake.seen.index('POWERON') < fake.seen.index('LOADPARAMS')
    assert fake.seen[-1] == 'POWEROFF', fake.seen[-6:]
    assert not fake.powered

    text = labels()
    assert 'FETCH' in text and 'FITS 저장' in text
    assert 'astropy 로 열린다' in text
    assert '2880 x' in text

    made = glob.glob(str(tmp_path / 'probe.*.MK.fits'))
    assert len(made) == 1, made
    from astropy.io import fits
    with fits.open(made[0]) as hdul:
        h = hdul[0].header
        assert (h['NAXIS1'], h['NAXIS2']) == (NX, NY)
        assert h['BITPIX'] == 16 and h['BZERO'] == 32768
        # 컨트롤러 유래 카드가 실값이다
        assert h['CTRL1SN'].strip() == '0024498A715E301C'
        # 규격 5.6.1절 -- science 는 열 자리다 (v1.5 전에는 잠정 5자리였다)
        assert len(h['C1_TEMP'].strip().split('|')) == 10
        assert len(h['C1_VOLT'].strip().split('|')) == 7
        assert len(h['C1_CURR'].strip().split('|')) == 7
        # 원천이 없는 것은 sentinel 로 남는다
        assert h['CCDTEMP'].strip() == '-999.99'
        # 관측 카드는 이 도구가 채우지 않는다 (TC 에 붙지 않는다)
        assert h['OBJECT'].strip() == 'PROBE'
        assert h['RA'].strip() == 'NC'


def test_stage3_powers_off_even_when_the_frame_fails(fake, tmp_path):  # noqa: ANN001
    """**전원을 켠 채로 끝나지 않는다.**  검출기 쪽 위험이다.

    기하 불일치로 3단계가 중간에 끊기는 경우를 만든다.
    """
    acf = tmp_path / 'probe.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')
    fake.width = NX * 2                  # 선언과 다르다
    rc = run(['--host', '127.0.0.1', '--port', str(fake.port),
              '--acf', str(acf), '--expose', '0', '--write',
              '--poll', '0.01', '--poweron-wait', '0'], tmp_path)
    assert rc == 1
    assert 'POWEROFF' in fake.seen and not fake.powered
    assert not glob.glob(str(tmp_path / '*.fits'))


def test_stage3_survives_a_controller_with_no_frames_yet(tmp_path):  # noqa: ANN001
    """**`REBOOT` 직후 -- 완료된 프레임이 하나도 없는 컨트롤러** (CCD `POWERON` 은
    버퍼를 지우지 않는다, DevNote 10.7).

    그때 `newest()` 는 `-1` 을 준다.  `prev + 1 = 0` 을 기다리면 컨트롤러가 첫
    프레임에 1 을 붙이는 순간 "0 을 지나쳤다" 가 되어 **첫 노출이 통째로
    버려진다** -- 실기 첫 실행에서 곧바로 걸릴 자리였다.
    """
    srv = FakeArchon(width=NX, height=NY, fresh=True)
    srv.start()
    try:
        acf = tmp_path / 'probe.acf'
        acf.write_text(ACF_TEXT, encoding='ascii')
        rc = run(['--host', '127.0.0.1', '--port', str(srv.port),
                  '--acf', str(acf), '--expose', '0', '--write',
                  '--poll', '0.01', '--poweron-wait', '0'], tmp_path)
    finally:
        srv.shutdown()
    assert rc == 0, labels()
    assert '완료된 프레임이 아직 없다' in labels()
    assert len(glob.glob(str(tmp_path / 'probe.*.fits'))) == 1


def test_stage1_reads_the_health_fields_and_the_bias_table(tmp_path):  # noqa: ANN001
    """P-g · P-h · P-i -- 실기에서 사람이 눈으로 확인할 자리들.

    ⚠️ **기본 가짜(`DEFAULT_STATUS`)는 `VALID`/`COUNT`/`LOG`/`POWER`/`OVERHEAT`
    를 안 낸다** -- 그것도 실재하는 경우(구 펌웨어)라 그대로 두고, 여기서는 다
    내는 `FULL_STATUS` 로 **확인 쪽 경로**를 밟는다.  둘 다 안 밟으면 실기에서
    처음 실행된다.

    바이어스 표는 **이름표를 ACF 에서, 값을 STATUS 에서** 읽는다 -- 두 dict 의
    키 문자열이 같아서(지령값 vs 실측값) 섞으면 그럴듯한 거짓말이 나온다.
    """
    from fake_archon import FULL_STATUS
    from test_monitor import ACF_BIAS, _bias_status

    status = dict(_bias_status(), **{k: FULL_STATUS[k] for k in
                                     ('VALID', 'COUNT', 'LOG', 'POWER',
                                      'OVERHEAT')})
    acf = tmp_path / 'bias.acf'
    acf.write_text(ACF_BIAS, encoding='ascii')

    srv = FakeArchon(width=NX, height=NY, status=status)
    srv.start()
    try:
        rc = run(['--host', '127.0.0.1', '--port', str(srv.port),
                  '--acf', str(acf)], tmp_path)
    finally:
        srv.shutdown()

    text = labels()
    assert rc == 0, text
    assert 'VALID = 1' in text
    assert 'COUNT = ' in text
    assert 'LOG = 0' in text                    # ⚠️ '0' 과 '보고 없음' 은 다르다
    assert 'POWER = 4' in text
    assert '전원 레일 7개가 정상 범위 안이다' in text
    assert '바이어스 16채널의 V/I 를 전부 읽었다' in text
    assert probe_archon.BAD not in marks(), text


# ---------------------------------------------------------------------------
# guide 유닛 (`--unit guide`) -- 자리 표·카드 표가 science 와 다르다
# ---------------------------------------------------------------------------
#
# ⭐ **왜 이 갈래가 필요한가** (2026-09-03).  guide 유닛은 자리 표가 규격 10.4절
# 8자리이고 장착이 3·4·5·6·7·9·10 이다.  science 10자리로 재면 1단계가
# `extra [6, 7]` + `missing [1, 2, 8, 11]` 을 **거짓으로** 보고한다 -- probe 는
# 실기에 붙이는 첫 도구라 그 오경보 하나가 진짜 문제를 덮는다.  아래 둘째 시험이
# **그 거짓 보고 자체**를 못박는다 (플래그를 지우면 빨개진다).

#: guide ACF `[SYSTEM]` 실측 (`acf/KMTK_GUI_162_STA0201_R2610.acf`) --
#: Driver 둘 · AD 둘 · HeaterX 둘 · HVXBias 하나, 1·2·8·11·12 는 빈 슬롯.
GUIDE_SYSTEM = {
    'BACKPLANE_TYPE': '1', 'BACKPLANE_REV': '5',
    'BACKPLANE_VERSION': '1.0.1252',
    'BACKPLANE_ID': '000000001A99369B',
    'MOD_PRESENT': '037C',
    'MOD1_TYPE': '0', 'MOD2_TYPE': '0', 'MOD3_TYPE': '1', 'MOD4_TYPE': '1',
    'MOD5_TYPE': '2', 'MOD6_TYPE': '2', 'MOD7_TYPE': '11', 'MOD8_TYPE': '0',
    'MOD9_TYPE': '8', 'MOD10_TYPE': '11', 'MOD11_TYPE': '0',
    'MOD12_TYPE': '0',
}

#: guide `STATUS` -- **8자리 온도 + 7레일 + `HEATER`**.  science 표에 있는
#: `MOD1/TEMP` 같은 자리는 **일부러 안 낸다**: 프로파일이 안 갈리면 그 자리를
#: 결측으로 세어 `문제` 가 나는 것이 아래 둘째 시험에서 드러난다.
GUIDE_STATUS = {
    'POWERGOOD': '1', 'VALID': '1', 'COUNT': '100', 'LOG': '0',
    'POWER': '4', 'OVERHEAT': '0',
    'BACKPLANE_TEMP': '30.9',
    'MOD3/TEMP': '31.1', 'MOD4/TEMP': '31.2', 'MOD5/TEMP': '32.3',
    'MOD6/TEMP': '32.4', 'MOD7/TEMP': '33.5', 'MOD9/TEMP': '34.6',
    'MOD10/TEMP': '34.7',
    'P2V5_V': '2.512', 'P2V5_I': '4.698',
    'P5V_V': '5.023', 'P5V_I': '4.487',
    'P6V_V': '5.834', 'P6V_I': '2.176',
    'N6V_V': '-5.945', 'N6V_I': '0.465',
    'P17V_V': '16.956', 'P17V_I': '0.454',
    'N17V_V': '-17.067', 'N17V_I': '0.443',
    'P35V_V': '35.089', 'P35V_I': '0.032',
    # PROVISIONAL -- 후보 셋 중 첫째.  실기 이름은 첫 구동에서 확정한다.
    'HEATER_V': '27.9', 'HEATER_I': '0.512',
}

# 층 2 -- guide 바이어스 **18채널**.  이름표는 ACF(`MOD9/HVxC_n`)에서, 값은
# STATUS(`MOD9/HVxC_Vn`/`_In`)에서 온다 (매뉴얼 p.48).  아래 `run_guide` 가
# `icg_archon.ini` 의 정본 ACF 를 그대로 쓰므로 이 자리가 비면 1단계가
# `문제` 를 낸다 -- 채워 두고 guide 층 2 경로를 함께 밟는다.
GUIDE_BIAS = {}
for _n in range(1, 7):                       # HVHC 여섯 (ABG·OG·TP24·…)
    GUIDE_BIAS['MOD9/HVHC_V%d' % _n] = '%.2f' % (24.0 + _n)
    GUIDE_BIAS['MOD9/HVHC_I%d' % _n] = '0.100'
for _n in range(1, 13):                      # HVLC 열둘 (VRD·OD 계열)
    GUIDE_BIAS['MOD9/HVLC_V%d' % _n] = '%.2f' % (10.0 + _n)
    GUIDE_BIAS['MOD9/HVLC_I%d' % _n] = '0.050'
GUIDE_STATUS.update(GUIDE_BIAS)

_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir))
GUIDE_INI = os.path.join(_ROOT, 'icg_archon.ini')


@pytest.fixture()
def guide_fake():  # noqa: ANN201
    srv = FakeArchon(width=NX, height=NY, system=GUIDE_SYSTEM,
                     status=GUIDE_STATUS)
    srv.start()
    yield srv
    srv.shutdown()


def run_guide(args, tmp_path):  # noqa: ANN001
    """`--unit guide` 로 돌린다 -- 기하만 시험 크기로 줄인다."""
    from icg_archon import config as icfg_mod
    real_load = icfg_mod.load

    def small(path):  # noqa: ANN001
        cfg = real_load(path)
        cfg.naxis1, cfg.naxis2 = NX, NY
        # ini 의 ACF 경로는 상대경로다 -- **실행 디렉터리에 기대지 않는다.**
        # 정본을 그대로 쓰되(층 2 이름표가 실물이어야 한다) 저장소 기준으로
        # 푼다.
        if cfg.acf.get('G') and not os.path.isabs(cfg.acf['G']):
            cfg.acf['G'] = os.path.normpath(
                os.path.join(_ROOT, cfg.acf['G']))
        return cfg

    icfg_mod.load = small
    try:
        return probe_archon.main(args + ['--unit', 'guide',
                                         '-c', GUIDE_INI,
                                         '--out', str(tmp_path)])
    finally:
        icfg_mod.load = real_load


def test_guide_profile_is_quiet_on_a_guide_unit(guide_fake, tmp_path):  # noqa: ANN001
    """guide 유닛 + `--unit guide` = **문제 0건.**"""
    rc = run_guide(['--host', '127.0.0.1', '--port', str(guide_fake.port)],
                   tmp_path)
    assert rc == 0, labels()
    assert probe_archon.BAD not in marks(), labels()

    text = labels()
    assert '규격 10.4절 자리 표와 정합한다' in text
    assert '8자리' in text
    assert '온도 슬롯 8개' in text
    # `HEATER` 는 결측이 아니라 PROVISIONAL 로 다룬다.
    assert 'HEATER 레일 필드 = HEATER_V' in text
    # 층 2 -- guide 는 18채널이다 (science 16 과 다르다)
    assert '바이어스 18채널의 V/I 를 전부 읽었다' in text
    # 1단계는 전원을 켜지 않는다 -- guide 도 같다.
    assert 'POWERON' not in guide_fake.seen and not guide_fake.powered


def test_science_profile_on_a_guide_unit_is_the_false_alarm(guide_fake, tmp_path):  # noqa: ANN001
    """⚠️ **`--unit` 을 안 주면 거짓 어긋남이 나온다** -- 그 사실을 못박는다.

    이 시험이 빨개지면 둘 중 하나다: 프로파일 갈래가 없어졌거나(플래그를
    지웠다), science 자리 표가 guide 와 같아졌거나.  둘 다 사람이 봐야 한다 --
    조용히 통과하면 실기 첫 화면의 오경보가 되살아난다.
    """
    rc = run(['--host', '127.0.0.1', '--port', str(guide_fake.port)], tmp_path)
    assert rc == 1
    text = labels()
    assert '자리 표에 없다' in text          # 장착 6·7 이 science 표 밖
    assert '자리 표의 슬롯' in text          # 1·2·8·11 이 무보고
    assert '온도 슬롯' in text and 'MOD1/TEMP' in text


def test_guide_stage3_writes_a_guide_header(guide_fake, tmp_path):  # noqa: ANN001
    """3단계 -- guide 카드 표로 파일 한 장.  `ICGBUILD` · 8자리 · `CTRL2*` 없음."""
    acf = tmp_path / 'guide.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')
    rc = run_guide(['--host', '127.0.0.1', '--port', str(guide_fake.port),
                    '--acf', str(acf), '--expose', '0', '--write',
                    '--poll', '0.01', '--poweron-wait', '0'], tmp_path)
    assert rc == 0, labels()
    assert guide_fake.seen[-1] == 'POWEROFF', guide_fake.seen[-6:]

    made = glob.glob(str(tmp_path / 'probe.*.G.fits'))
    assert len(made) == 1, made
    from astropy.io import fits
    with fits.open(made[0]) as hdul:
        h = hdul[0].header
        assert (h['NAXIS1'], h['NAXIS2']) == (NX, NY)
        # 규격 10.4절 -- 온도 여덟 · 레일 여덟 (science 는 열·일곱이다)
        assert len(h['C1_TEMP'].strip().split('|')) == 8
        assert len(h['C1_VOLT'].strip().split('|')) == 8
        assert len(h['C1_CURR'].strip().split('|')) == 8
        # 키 개명 -- guide 는 `ICGBUILD` 다 (10.3절)
        assert 'ICGBUILD' in h and 'ICSBUILD' not in h
        # 컨트롤러가 한 대라 `CTRL2*` 는 템플릿에 없다
        assert 'CTRL1ID' in h and 'CTRL2ID' not in h
        assert h['CTRL1SN'].strip() == '000000001A99369B'
        # 실물 백엔드로 적는다 -- 시뮬로 오인되면 규격 5.5절 방어가 무의미해진다
        assert h['DATASRC'].strip() == 'ARCHON_GUIDE'


def test_guide_rejects_a_science_tag(guide_fake, tmp_path):  # noqa: ANN001
    """`--unit guide --tag MK` 는 거부한다 -- guide 에 없는 어휘다.

    받아 주면 **조용히 다른 자리의 카드**가 만들어진다 (색인이 태그를 정한다).
    """
    rc = run_guide(['--host', '127.0.0.1', '--port', str(guide_fake.port),
                    '--tag', 'MK'], tmp_path)
    assert rc == 1
    assert '--tag MK 가 없다' in labels()


def test_guide_heater_field_absence_is_not_a_defect(tmp_path):  # noqa: ANN001
    """`HEATER` 이름이 후보에 없어도 **`문제` 가 아니다** (PROVISIONAL).

    실기 이름을 아직 모르는 자리를 결측으로 세면 첫 구동이 통째로 빨개진다 --
    그러면 같은 화면에 있는 진짜 결측을 못 읽는다 (F2 원칙).
    """
    status = {k: v for k, v in GUIDE_STATUS.items()
              if not k.startswith('HEATER')}
    srv = FakeArchon(width=NX, height=NY, system=GUIDE_SYSTEM, status=status)
    srv.start()
    try:
        rc = run_guide(['--host', '127.0.0.1', '--port', str(srv.port)],
                       tmp_path)
    finally:
        srv.shutdown()
    assert rc == 0, labels()
    text = labels()
    assert 'HEATER 레일 필드 = (후보 다 없다)' in text
    # 범위 판정도 일곱만 센다 -- p.41 표에 `HEATER`(+28 V)가 없다.
    assert '전원 레일 7개가 정상 범위 안이다' in text

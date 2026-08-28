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
    """**첫 전원 투입 -- 완료된 프레임이 하나도 없는 컨트롤러.**

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

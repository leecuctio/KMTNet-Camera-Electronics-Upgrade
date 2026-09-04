#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ini -> FITS 카드 전수 대조 -- **`Source` 가 `ICS INI` 인 카드가 다 물리나.**

판정 원장(`raw_fits_spec/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_
v1.15.md`) 3장 표의 `Source (* default)` 열이 정본이고, 그중 `ICS INI` 인 카드는
**전부 ini 에서 수정 가능해야 한다**(운영자 지시 2026-08-22, 원장 확인 요망 6).

원장이 `ICS INI` 로 못박은 14장:

    ORIGIN OBSERVAT TELESCOP LATITUDE LONGITUD ELEVATIO   (5.3 관측소)
    DETECTOR INSTRUME                                     (5.2 기기)
    CTRL1ID CTRL1SN CTRL1CFG CTRL2ID CTRL2SN CTRL2CFG     (5.5 컨트롤러)

여기에 Archon 세대에 신설돼 **같은 지시의 대상이 된** 3장을 더한다 (원장의
"도입 후보 카드" 표는 `Source` 열이 없다 -- DevNote 11.19 가 `[camera] fpaid`·
`[controllers] rdmode` ini 키를 그 지시로 신설했다):

    CAMVER FPAID RDMODE

**시험 방법은 하나뿐이다 -- 기본값과 다른 값을 넣고 파일에서 되읽는다.**
`ini 를 읽는가` 만 보면 "읽었지만 카드로 안 나갔다" 를 놓친다.  그리고 값이
기본값과 같으면 배선이 끊겨 있어도 통과한다.
"""

from __future__ import annotations

import asyncio
import configparser
import glob
import os

import pytest
from fake_archon import FakeArchon

from ics_archon import config as acfg_mod
from ics_archon.app import IcsArchon

from ics_sim import config as simcfg

NX, NY = 12, 4

ACF_TEXT = """[CONFIG]
TRIGOUTFORCE=0
PARAMETER1="Exposures=1"
PARAMETER2="IntMS=0"
"""

BASE_INI = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, 'ics_archon.ini'))

#: **기본값과 겹치지 않는 값들.**  겹치면 배선이 끊겨도 통과한다.
INI_OVERRIDES = {
    'node': {'observatory': 'SSO'},
    'site': {'telescop': 'PROBE-TELESCOPE 9.9m', 'latitude': '-12:34:56.78',
             'longitud': '123:45:67', 'elevatio': '4242',
             'origin': 'INIORIGIN'},
    'camera': {'detector': 'ini-DETECTOR-9', 'camver': 'ini-CAMVER-9',
               'instrume': 'ini INSTRUME 9k', 'fpaid': 'ini-FPA-9'},
    'controllers': {'ctrl1_id': 'INI-SCI-901', 'ctrl1_sn': 'INI-0901',
                    'ctrl1_cfg': 'INI_CFG_901', 'ctrl2_id': 'INI-SCI-902',
                    'ctrl2_sn': 'INI-0902', 'ctrl2_cfg': 'INI_CFG_902',
                    'rdmode': 'INIMODE'},
}

#: 카드 -> 헤더에 실려야 하는 값 (위 ini 에서 유도).
EXPECT = {
    # 5.3 관측소 -- `[site]` 덮어쓰기와 `[node] site/telid`
    'TELESCOP': 'PROBE-TELESCOPE 9.9m',
    'LATITUDE': '-12:34:56.78',
    'LONGITUD': '123:45:67',
    'ELEVATIO': 4242,
    'ORIGIN': 'INIORIGIN',
    'OBSERVAT': 'SSO',                  # telid=KMTA -> rawpair.OBSERVAT
    # 5.2 기기
    'DETECTOR': 'ini-DETECTOR-9',
    'CAMVER': 'ini-CAMVER-9',
    'INSTRUME': 'ini INSTRUME 9k',
    'FPAID': 'ini-FPA-9',
    # 5.5 컨트롤러 -- **ini 가 백엔드 보고값을 이긴다**
    'CTRL1ID': 'INI-SCI-901', 'CTRL1SN': 'INI-0901', 'CTRL1CFG': 'INI_CFG_901',
    'CTRL2ID': 'INI-SCI-902', 'CTRL2SN': 'INI-0902', 'CTRL2CFG': 'INI_CFG_902',
    'RDMODE': 'INIMODE',
}


def write_ini(tmp_path, overrides, acf: str, acf_nt: str = ''):  # noqa: ANN001
    """저장소 ini 를 읽어 덮어쓴 사본을 만든다.

    **밑바탕을 저장소 ini 로 두는 것이 요점이다** -- 시험용 ini 를 따로 쓰면
    실제로 배포되는 파일이 시험되지 않는다.
    """
    cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    cp.read(BASE_INI, encoding='utf-8')
    for sec, kv in overrides.items():
        if not cp.has_section(sec):
            cp.add_section(sec)
        for k, v in kv.items():
            cp[sec][k] = v
    # 시험 배선
    cp['archon']['ctrl_mk_host'] = '127.0.0.1'
    cp['archon']['ctrl_nt_host'] = '127.0.0.1'
    cp['archon']['acf_mk'] = acf
    cp['archon']['acf_nt'] = acf_nt or acf
    cp['archon']['naxis1'] = str(NX)
    cp['archon']['naxis2'] = str(NY)
    cp['archon']['poweron_wait'] = '0'
    cp['archon']['frame_poll'] = '0.01'
    cp['timing']['time_scale'] = '0.02'
    cp['transport']['bind_port'] = '0'
    cp['behavior']['console'] = 'false'
    cp['logging']['wire'] = 'false'
    path = str(tmp_path / 'test.ini')
    with open(path, 'w', encoding='utf-8') as f:
        cp.write(f)
    return path


async def _drive(ini, tmp_path, nt_port, script, settle=0.8):  # noqa: ANN001
    cfg = simcfg.load(ini)
    cfg.paths.data_dir = str(tmp_path / 'rawdata')
    cfg.paths.expnum_file = str(tmp_path / 'expnum')
    acfg = acfg_mod.load(ini)
    # ⛔ 허브 없이 도는 하네스 -- 기동의 XIS PING/PONG 검사를 끈다
    # (운영자 지시 2026-09-04로 신설).
    acfg.require_xis = False
    app = IcsArchon(cfg, acfg)
    app.backend.ctrls['NT'].link.port = nt_port
    await app.start()
    try:
        for line in script:
            app.transport.feed(line)
            await asyncio.sleep(0.02)
        await app.seq.wait()
        await asyncio.sleep(settle)
        return list(app.transport.sent_log)
    finally:
        await app.stop()


def run(tmp_path, overrides=None, script=None,  # noqa: ANN001
        acf_names=('test.acf', '')):
    #: `acf_names` -- (MK, NT).  NT 를 비우면 MK 것을 함께 쓴다.  파일명이
    #: 곧 `CTRL1CFG`/`CTRL2CFG` 파생의 입력이라 시험마다 갈아 끼울 수 있어야
    #: 한다 (`ics_archon.ini` 의 `[archon] acf_mk`/`acf_nt`).
    acfs = []
    for name in (acf_names[0], acf_names[1] or acf_names[0]):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ACF_TEXT, encoding='ascii')
        acfs.append(str(path))
    mk = FakeArchon(width=NX, height=NY)
    nt = FakeArchon(width=NX, height=NY)
    mk.start()
    nt.start()
    try:
        ini = write_ini(tmp_path, overrides or INI_OVERRIDES, acfs[0], acfs[1])
        cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        cp.read(ini, encoding='utf-8')
        cp['archon']['port'] = str(mk.port)
        with open(ini, 'w', encoding='utf-8') as f:
            cp.write(f)
        sent = asyncio.run(_drive(
            ini, tmp_path, nt.port,
            script or ['OBS>ICS projid ENG', 'OBS>ICS dark begin',
                       'OBS>ICS exp 1', 'OBS>ICS go']))
    finally:
        mk.shutdown()
        nt.shutdown()
    return sent


def headers(tmp_path):  # noqa: ANN201
    from astropy.io import fits
    out = {}
    for path in glob.glob(str(tmp_path / 'rawdata' / '*.fits')):
        with fits.open(path) as hdul:
            out[os.path.basename(path).split('.')[-2]] = dict(hdul[0].header)
    return out


# ---------------------------------------------------------------------------

def test_every_ics_ini_card_carries_the_ini_value(tmp_path):  # noqa: ANN001
    """원장 `Source = ICS INI` 17장이 **전부** ini 값을 싣는다.

    하나라도 코드 기본값이 남아 있으면 그 카드는 ini 로 못 고치는 것이고,
    관측소 반입 때 그 값이 조용히 틀린다 (`OBSERVAT` 은 파일명과 교차 검증되는
    유일한 하드 실패 카드다).
    """
    run(tmp_path)
    heads = headers(tmp_path)
    assert set(heads) == {'MK', 'NT'}, list(heads)

    wrong = []
    for tag, head in sorted(heads.items()):
        for card, want in EXPECT.items():
            got = head.get(card)
            got = got.strip() if isinstance(got, str) else got
            if got != want:
                wrong.append('%s %s: 기대 %r, 받음 %r' % (tag, card, want, got))
    assert not wrong, '\n'.join(wrong)


def test_ini_beats_the_controller_reported_serial(tmp_path):  # noqa: ANN001
    """`CTRLnSN` -- **ini 가 백엔드 보고값(BACKPLANE_ID)을 이긴다.**

    운영이 붙인 정체가 정본이라는 `[site]` 와 같은 원칙이다.  ini 를 비우면
    컨트롤러 값이 실려야 하고(그것도 확인한다), 채우면 ini 가 이긴다.
    """
    run(tmp_path)
    assert headers(tmp_path)['MK']['CTRL1SN'].strip() == 'INI-0901'

    empty = {k: dict(v) for k, v in INI_OVERRIDES.items()}
    empty['controllers'] = {k: '' for k in INI_OVERRIDES['controllers']}
    out2 = tmp_path / 'b'
    out2.mkdir()
    run(out2, empty)
    head = headers(out2)['MK']
    assert head['CTRL1SN'].strip() == '0024498A715E301C', 'SYSTEM 값이 안 실렸다'
    assert head['CTRL1CFG'].strip() == 'test', 'ACF 파일명이 안 실렸다'
    # ini 가 비면 ACF 이름에서 유도된다 -- 이 ACF 이름에는 토큰이 없으므로
    # 코드 기본값이 실리고, 그 값은 **`UNKNOWN`** 이다 (운영자 확정 2026-08-29).
    # `NORMAL` 로 두면 "정말 NORMAL" 과 구별되지 않는다.
    assert head['RDMODE'].strip() == 'UNKNOWN'


def test_site_switch_moves_geometry_and_observat_together(tmp_path):  # noqa: ANN001
    """**`[node] site` 한 줄이 좌표·관측소·파일명을 다 끌고 간다** (D-011/D-015).

    한쪽만 따라오면 **한 파일 안에서 사이트가 갈린다** -- converter 가 파일명
    `<SITE>` 와 `OBSERVAT` 를 교차 검증해 거부하는 유일한 하드 실패다.
    """
    over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
    over['node'] = {'observatory': 'CTIO'}
    over['site'] = {}                    # 덮어쓰기를 비워 사이트 표를 쓰게 한다
    run(tmp_path, over)
    names = sorted(os.path.basename(p)
                   for p in glob.glob(str(tmp_path / 'rawdata' / '*.fits')))
    assert names and all(n.startswith('KMTC.') for n in names), names
    head = headers(tmp_path)['MK']
    assert head['OBSERVAT'].strip() == 'CTIO'
    assert head['TELESCOP'].strip() == 'KMTNet 1.6m #1'   # '\\#' 탈출 해제
    assert head['LATITUDE'].strip() == '-30:10:01.84'
    assert head['ELEVATIO'] == 2140
    assert head['ORIGIN'].strip() == 'CTIO'
    # 파일명 <SITE> 와 OBSERVAT 가 같은 사이트를 가리킨다
    assert names[0].split('.')[0] == 'KMTC'


def test_kasi_leaves_the_coordinates_as_sentinels(tmp_path):  # noqa: ANN001
    """KASI(실험실)는 **좌표만** 일부러 비운다 -- 시험 산출물이 관측처럼
    보이면 안 된다.  `TELESCOP`/`FPAID` 는 D-017 항목 6 이 값을 정했다
    (raw spec 5.3.1절) -- 구 `TESTBED` 판의 `'Sim'` 을 대체한다."""
    over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
    over['node'] = {'observatory': 'KASI'}
    over['site'] = {}
    over['camera'] = {k: v for k, v in over.get('camera', {}).items()
                      if k != 'fpaid'}
    run(tmp_path, over)
    head = headers(tmp_path)['MK']
    assert head['OBSERVAT'].strip() == 'KASI'
    assert head['LATITUDE'].strip() == 'NC'
    assert head['LONGITUD'].strip() == 'NC'
    assert head['ELEVATIO'] == -1
    assert head['ORIGIN'].strip() == 'KASI'
    assert head['TELESCOP'].strip() == 'KMTNet 1.6m #0'
    assert head['FPAID'].strip() == 'FPA#0'


def test_archon_geometry_ini_reaches_naxis(tmp_path):  # noqa: ANN001
    """`[archon] naxis1/naxis2` 가 선언 카드이고 fetch 대조 기준이다."""
    run(tmp_path)
    head = headers(tmp_path)['MK']
    assert (head['NAXIS1'], head['NAXIS2']) == (NX, NY)


def test_rdmode_is_derived_from_the_acf_when_ini_is_empty(tmp_path):  # noqa: ANN001
    """컨트롤러는 적용 ACF 이름을 보고하지 않는다 -- 파일명이 유일한 근거다."""
    acf = tmp_path / 'KMTNet_Sci_comp_med_U13.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')
    over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
    over['controllers'] = {'rdmode': ''}
    mk = FakeArchon(width=NX, height=NY)
    nt = FakeArchon(width=NX, height=NY)
    mk.start()
    nt.start()
    try:
        ini = write_ini(tmp_path, over, str(acf))
        cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        cp.read(ini, encoding='utf-8')
        cp['archon']['port'] = str(mk.port)
        with open(ini, 'w', encoding='utf-8') as f:
            cp.write(f)
        asyncio.run(_drive(ini, tmp_path, nt.port,
                           ['OBS>ICS dark begin', 'OBS>ICS exp 1',
                            'OBS>ICS go']))
    finally:
        mk.shutdown()
        nt.shutdown()
    head = headers(tmp_path)['MK']
    assert head['RDMODE'].strip() == 'COMP'
    assert head['CTRL1CFG'].strip() == 'KMTNet_Sci_comp_med_U13'


def test_ctrlcfg_is_derived_from_the_acf_path(tmp_path):  # noqa: ANN001
    """`CTRL1CFG`/`CTRL2CFG` -- ini 가 비면 **적용 ACF 경로**에서 나온다.

    규격 v1.8 5.5절이 *"폴더 경로와 확장자(`.acf`/`.cfg`)를 뗀 이름"* 으로
    못박았다.  종전에는 `[controllers] ctrlN_cfg`(손편집)와 `[archon]
    acf_mk`/`acf_nt`(실제로 올리는 파일)가 별개 키여서 **둘이 어긋난 채로
    배포될 수 있었다** -- 그러면 그 사이트 자료만 영구히 다른 설정 이름을 단다.

    **MK/NT 에 서로 다른 이름을 준다** -- 한 이름으로 시험하면 배정이 뒤바뀌어도
    (`acf_mk` -> `CTRL2CFG`) 통과한다.  `.cfg` 도 같은 Archon 설정 파일이라
    함께 뗀다 (운영자 확인 2026-08-29).
    """
    over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
    over['controllers'] = {'ctrl1_cfg': '', 'ctrl2_cfg': ''}
    run(tmp_path, over,
        acf_names=(os.path.join('acf', 'KMTC_SCI_101_STA0284_R2608_MK.acf'),
                   os.path.join('acf', 'KMTC_SCI_102_STA0285_R2608_NT.cfg')))
    for tag, head in sorted(headers(tmp_path).items()):
        # pair 두 파일에 **두 대분이 같이** 실린다 (규격 5.9절)
        assert head['CTRL1CFG'].strip() == 'KMTC_SCI_101_STA0284_R2608_MK', tag
        assert head['CTRL2CFG'].strip() == 'KMTC_SCI_102_STA0285_R2608_NT', tag


def test_cfg_name_from_acf_only_strips_acf_and_cfg():
    """⚠️ **판 번호에 점이 들어간다** -- 범용 `splitext` 를 쓰면 깨진다.

    `KMTA_SCI_101_R2609.1.acf` 는 `splitext` 한 번으로도 맞지만, **확장자 없이
    적힌 경로**를 받으면 `splitext` 가 `.1` 을 먹어 판 번호가 조용히 달라진다.
    모르는 접미는 그대로 두는 것이 규칙이다 (운영자 확정 2026-08-29).
    """
    f = acfg_mod.cfg_name_from_acf
    assert f('~/AIC/Config/acf/KMTC_SCI_101_STA0284_R2608_MK.acf') ==         'KMTC_SCI_101_STA0284_R2608_MK'
    # 판 번호의 점을 먹지 않는다
    assert f('acf/KMTA_SCI_101_R2609.1.acf') == 'KMTA_SCI_101_R2609.1'
    assert f('acf/KMTA_SCI_101_R2609.1') == 'KMTA_SCI_101_R2609.1'
    # `.cfg` 도 뗀다.  대소문자는 무시하되 **뗀 뒤의 이름은 원문 그대로**다
    assert f('acf/KMTA_SCI_101_R2609.1.cfg') == 'KMTA_SCI_101_R2609.1'
    assert f('acf/KMTK_GUI_162_STA0201_R2610.ACF') == 'KMTK_GUI_162_STA0201_R2610'
    # 모르는 접미는 남긴다 -- 임의로 떼면 값이 소리 없이 달라진다
    assert f('acf/KMTA_SCI_101_R2609.1.txt') == 'KMTA_SCI_101_R2609.1.txt'
    # 유도 실패는 빈 문자열 (부르는 쪽이 손편집 값·백엔드 값에 맡긴다)
    assert f('') == '' and f(None) == '' and f('acf/.acf') == ''


def test_hand_typed_ctrlcfg_wins_but_the_mismatch_is_reported(tmp_path):  # noqa: ANN001
    """손편집 값이 이긴다 -- 대신 **어긋나면 기동에서 알린다.**

    `Source = ICS INI` 카드는 전부 ini 로 고칠 수 있어야 하므로(운영자 지시
    2026-08-22) 파생이 덮지 않는다.  그 대가로 "헤더가 주장하는 설정 파일 !=
    실제로 올리는 파일" 이 남는데, **그 어긋남은 자료를 봐도 드러나지 않는다** --
    이름이 그럴듯하면 아무도 의심하지 않는다.
    """
    acf = tmp_path / 'KMTC_SCI_101_STA0284_R2608_MK.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')

    def notes(ctrl1_cfg):  # noqa: ANN001
        over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
        over['controllers'] = {'ctrl1_cfg': ctrl1_cfg, 'ctrl2_cfg': ''}
        ini = write_ini(tmp_path, over, str(acf))
        cfg, acfg = simcfg.load(ini), acfg_mod.load(ini)
        from ics_archon.app import fill_controller_cfg_names
        fill_controller_cfg_names(cfg, acfg)
        return cfg, [n for n in acfg_mod.validate(
            acfg, tuple(cfg.node.ccds), cfg) if 'ctrl1_cfg' in n]

    # ① 손으로 다른 이름을 적어 두면 -- 그 값이 실리고, 경고가 남는다
    cfg, warned = notes('KMTC_SCI_101_STA0284_R2601_MK')
    assert cfg.controllers.ctrl1_cfg == 'KMTC_SCI_101_STA0284_R2601_MK'
    assert warned, '어긋난 것을 아무도 알리지 않는다'
    assert 'KMTC_SCI_101_STA0284_R2608_MK' in warned[0]

    # ② 비워 두면 파생이 채우고 -- 어긋날 수가 없으므로 조용하다
    cfg, warned = notes('')
    assert cfg.controllers.ctrl1_cfg == 'KMTC_SCI_101_STA0284_R2608_MK'
    assert not warned, warned

    # ③ `NC`(그 컨트롤러는 없다)는 파생이 덮지 않는다 -- 운영자 선언이다
    cfg, _ = notes('NC')
    assert cfg.controllers.ctrl1_cfg == 'NC'


def test_rdmode_mismatch_with_the_acf_name_is_reported(tmp_path):  # noqa: ANN001
    """`RDMODE` 도 **양방향**으로 본다 (2026-08-29).

    현행 ACF 이름 규칙에는 속도 토큰(`fast`/`comp`/`slow`)이 아예 없어서
    유도가 늘 실패한다 -- 그래서 ini 에 직접 적는다(현행 전부 `NORMAL`,
    운영자 확정).  ⚠️ **그러면 그 줄은 ACF 를 바꿔도 따라오지 않는다** --
    속도가 다른 ACF 를 올리고 이 줄을 안 고치면 헤더가 거짓말을 하고,
    자료만 봐서는 드러나지 않는다.  `CTRLnCFG` 어긋남과 같은 형태다.
    """
    def notes(acf_name, rdmode):  # noqa: ANN001
        acf = tmp_path / acf_name
        acf.write_text(ACF_TEXT, encoding='ascii')
        over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
        over['controllers'] = {'rdmode': rdmode}
        ini = write_ini(tmp_path, over, str(acf))
        cfg, acfg = simcfg.load(ini), acfg_mod.load(ini)
        from ics_archon.app import fill_controller_cfg_names
        fill_controller_cfg_names(cfg, acfg)
        return [n for n in acfg_mod.validate(
            acfg, tuple(cfg.node.ccds), cfg) if 'rdmode' in n]

    # ① 현행 이름 + ini 를 비우면 -- 유도가 실패한다는 사실을 알린다
    warned = notes('KMTC_SCI_101_STA0284_R2608_MK.acf', '')
    assert warned and '속도 토큰' in warned[0], warned

    # ② 현행 이름 + ini 에 NORMAL -- 조용하다 (운영자가 확정한 값이다)
    assert not notes('KMTC_SCI_101_STA0284_R2608_MK.acf', 'NORMAL')

    # ③ ⚠️ 속도가 다른 ACF 를 올렸는데 ini 는 NORMAL 그대로 -- 헤더가 거짓말한다
    warned = notes('KMTNet_Sci_fast_med_U13.acf', 'NORMAL')
    assert warned, 'ACF 는 FAST 인데 ini 가 NORMAL 인 것을 아무도 안 알린다'
    assert 'FAST' in warned[0]

    # ④ 둘이 맞으면 조용하다
    assert not notes('KMTNet_Sci_fast_med_U13.acf', 'FAST')


def test_fetch_buffers_are_checked_against_the_wrote_window(tmp_path):  # noqa: ANN001
    """⭐ **버퍼 수와 `Wrote` 창은 짝이다** -- 한쪽만 바꾸면 기동에서 알린다.

    저장이 밀리면 둘이 순서대로 일어난다: ① 창을 넘겨 OBSAgent 가
    `ExpStatus=ERROR`(**경고**) ② 호스트 버퍼 고갈 -> FETCH 지연 -> 컨트롤러
    버퍼가 덮여 **프레임 손실**.  ①이 먼저여야 *"경고는 떴지만 자료는 남았다"*
    구간이 생긴다 -- 조건이 `N x 주기 >= 창 - write_delay` 다.

    ⚠️ 이 짝이 조용히 끊기는 것이 오늘 하루 잡은 결함들과 같은 부류다
    (`RDMODE` 유도가 ACF 이름 규칙 바뀌며 끊긴 것 등).  그래서 t=0 에 본다.
    """
    acf = tmp_path / 'KMTC_SCI_101_STA0284_R2608_MK.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')

    def notes(buffers, window):  # noqa: ANN001
        over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
        ini = write_ini(tmp_path, over, str(acf))
        cfg, acfg = simcfg.load(ini), acfg_mod.load(ini)
        acfg.fetch_buffers, acfg.wrote_window = buffers, window
        return [n for n in acfg_mod.validate(
            acfg, tuple(cfg.node.ccds), cfg) if 'fetch_buffers' in n]

    # 25초 창 -- 2개면 충분하다 (N x 13.27 >= 25 - 3.4).  ⚠️ 아래 30초 창의 3개
    # 판정은 ceil(26.6 / 13.27) = ceil(2.0045) 로 문턱에 걸쳐 있다 -- write_delay
    # 가 3.46 을 넘으면 2 가 된다.
    assert not notes(2, 25.0)
    # ⚠️ 창을 30초로 늘리면 2개로는 부족해진다 -- 3개가 필요하다
    warned = notes(2, 30.0)
    assert warned, '창을 넓혔는데 버퍼가 그대로인 것을 아무도 안 알린다'
    assert '3 이상' in warned[0], warned
    # 3개로 올리면 조용하다
    assert not notes(3, 30.0)
    # 1개는 25초 창에서도 모자란다
    assert notes(1, 25.0)


def test_turning_off_both_fetch_guards_is_flagged_at_startup(tmp_path):  # noqa: ANN001
    """⚠️ **`lock_buffer` 와 `recheck_after_fetch` 는 짝이다** (2026-08-30).

    fetch 하는 동안(실측 3.2~3.5초) 버퍼가 덮이는 창을 보는 것은 둘 중 하나다 --
    `LOCKn`(**막는다**) 또는 fetch 뒤 재대조(막지는 못하고 **잡아서 버린다**).
    둘 다 끄면 그 창을 보는 것이 아무것도 없고, 덮이면 두 노출이 섞인 raw 가
    **아무 경고 없이** 나온다.  자료를 나중에 봐도 못 가르는 실패라 t=0 에서
    알린다.
    """
    acf = tmp_path / 'KMTC_SCI_101_STA0284_R2608_MK.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')

    def notes(lock, recheck):  # noqa: ANN001
        over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
        ini = write_ini(tmp_path, over, str(acf))
        cfg, acfg = simcfg.load(ini), acfg_mod.load(ini)
        acfg.lock_buffer, acfg.recheck_after_fetch = lock, recheck
        return [n for n in acfg_mod.validate(
            acfg, tuple(cfg.node.ccds), cfg) if 'recheck_after_fetch' in n]

    assert not notes(True, True)          # 기본 -- 이중이라 조용하다
    assert not notes(True, False)         # LOCK 이 막는다
    assert not notes(False, True)         # 재대조가 잡는다 (lock_buffer=false 로 되돌릴 때의 유일한 방어, DevNote 10.6)
    warned = notes(False, False)          # ⚠️ 아무도 안 본다
    assert warned, '둘 다 껐는데 아무도 안 알린다'
    assert '아무도 못 본다' in warned[0], warned


def test_d016_collision_check_is_on_even_when_write_fits_is_false(tmp_path):  # noqa: ANN001
    """**`[paths] write_fits` 가 D-016 선검사를 잠그면 안 된다.**

    시퀀서는 `resolve_pair_number(..., check=cfg.paths.write_fits)` 로 부른다 --
    그 플래그는 **시뮬이 더미 FITS 를 만드는가** 라는 뜻이고, archon 백엔드는
    그 값과 무관하게 항상 실파일을 쓴다.  그래서 `write_fits=false`(저장소 ini
    의 기본값!) 로 실기를 돌리면 **충돌 선검사가 꺼진 채 실파일이 나가** 같은
    이름을 조용히 덮어쓴다 -- D-016 이 막으려던 바로 그 일이다.

    같은 UT 날짜에 같은 번호로 두 번 저장해 번호가 밀리는지 본다.
    """
    over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
    over['paths'] = {'write_fits': 'false'}
    run(tmp_path, over)
    first = sorted(os.path.basename(p)
                   for p in glob.glob(str(tmp_path / 'rawdata' / '*.fits')))
    assert len(first) == 2, first

    # 번호를 되돌려 같은 이름을 다시 쓰게 만든다 (EXPNUM 기록을 지운다).
    os.remove(str(tmp_path / 'expnum'))
    run(tmp_path, over)
    after = sorted(os.path.basename(p)
                   for p in glob.glob(str(tmp_path / 'rawdata' / '*.fits')))
    assert len(after) == 4, (
        '같은 이름을 덮어썼다 -- D-016 선검사가 꺼져 있다: %r' % after)
    # 덮어쓰지 않았으면 번호가 밀렸고 EXPID 가 그 신호로 남는다 (D-019)
    from astropy.io import fits
    bumped = [n for n in after if n not in first]
    with fits.open(str(tmp_path / 'rawdata' / bumped[0])) as hdul:
        h = hdul[0].header
    # 충돌 신호 = `FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값 != `EXPID`
    assert h['FILENAME'].strip().rsplit('.', 1)[0] != h['EXPID'].strip(), (
        '번호가 밀렸는데 EXPID 가 같다 -- 충돌 신호가 없다')

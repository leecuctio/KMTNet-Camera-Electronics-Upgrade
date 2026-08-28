#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""컨트롤러 대수 -- `[archon] n_controllers` (운영자 지시 2026-08-24).

카메라는 컨트롤러 2대 구성이지만 실험실에서는 한 대만 놓고 취득한다.  그
차이를 **ini 한 줄**로 두고, 1대일 때 어느 쪽인지는 `[controllers]` 의
`ctrl1_id`(→`MK`) / `ctrl2_id`(→`NT`) **선언 여부**가 정한다.

⚠️ **1대 운영은 OBSAgent 규약을 만족하지 못한다** -- CCD 가 둘뿐이라
`Acquisition Complete.`/`Wrote` 가 4회가 아니라 2회다.  그것은 결함이 아니라
구성의 결과이고, 관측 시퀀스 시험은 2대에서 한다 (README "실기 첫 실행 4단계").

**빠진 컨트롤러의 헤더 카드는 빼지 않는다** -- 값만 규격 5.0절의 문자열
sentinel `'NC'` 다.  카드를 빼면 pair 두 파일의 카드 수가 달라져 converter 와
견본 대사가 그것을 구조 변경으로 읽는다.  ini 에 `NC` 라고 적은 것도 "없다"
는 뜻이라 같은 자리로 떨어진다 -- **ini 의 낱말과 카드의 낱말이 같다**
(운영자 확정 2026-08-25).
"""

from __future__ import annotations

import configparser
import os

import pytest

from ics_archon import config as acfg_mod

from ics_sim import rawhdr

BASE_INI = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, 'ics_archon.ini'))
CCDS = ('M', 'K', 'N', 'T')


def make_ini(tmp_path, n, ctrl1='', ctrl2='', hosts=True):  # noqa: ANN001
    """저장소 ini 를 밑바탕으로 대수·컨트롤러 선언만 바꾼 사본."""
    cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    cp.read(BASE_INI, encoding='utf-8')
    cp['archon']['n_controllers'] = str(n)
    if hosts:
        cp['archon']['ctrl_mk_host'] = '127.0.0.1'
        cp['archon']['ctrl_nt_host'] = '127.0.0.2'
    cp['controllers']['ctrl1_id'] = ctrl1
    cp['controllers']['ctrl2_id'] = ctrl2
    path = tmp_path / 'n.ini'
    with open(path, 'w', encoding='utf-8') as fh:
        cp.write(fh)
    return str(path)


# ---------------------------------------------------------------------------
# 대수 판정
# ---------------------------------------------------------------------------

def test_two_controllers_is_the_default_shape(tmp_path):  # noqa: ANN001
    cfg = acfg_mod.load(make_ini(tmp_path, 2))
    assert cfg.n_controllers == 2
    assert cfg.solo_tag == ''
    assert cfg.active_tags(CCDS) == ('MK', 'NT')


@pytest.mark.parametrize('ctrl1, ctrl2, tag', [
    # 한쪽만 적는 방식
    ('KMTA-SCI-101', '', 'MK'),
    ('', 'KMTA-SCI-102', 'NT'),
    # 둘 다 적고 한쪽을 "없음" 으로 두는 방식 -- **셋 다 같은 뜻이다**
    ('KMTA-SCI-101', 'NC', 'MK'),
    ('NC', 'KMTA-SCI-102', 'NT'),
    ('KMTA-SCI-101', 'nc', 'MK'),
    ('nc', 'KMTA-SCI-102', 'NT'),
])
def test_one_controller_takes_its_side_from_the_declaration(tmp_path, ctrl1,  # noqa: ANN001
                                                            ctrl2, tag):
    """`ctrl1_id` 가 있으면 MK, `ctrl2_id` 가 있으면 NT.

    **적는 방식이 둘이다** (운영자 확정 2026-08-25) -- 한쪽만 적어도 되고,
    둘 다 적고 한쪽을 `NC`(또는 빈 값)로 두어도 된다.  운영 ini 를
    2대 구성에서 그대로 가져와 한 줄만 `NC` 로 바꾸는 쓰임을 위한 것이다."""
    cfg = acfg_mod.load(make_ini(tmp_path, 1, ctrl1=ctrl1, ctrl2=ctrl2))
    assert cfg.n_controllers == 1
    assert cfg.solo_tag == tag
    assert cfg.active_tags(CCDS) == (tag,)


def test_the_index_alone_decides_the_tag_never_the_string(tmp_path):  # noqa: ANN001
    """⚠️ **색인이 태그를 정한다 -- 이름 문자열은 절대 읽지 않는다.**

    색인 1 = `[controllers] ctrl1_*` 로 정의한 컨트롤러 = **무조건 `MK`**,
    색인 2 = `ctrl2_*` = **무조건 `NT`** 다 (`rawpair.CONTROLLERS` 순서, 운영자
    확정 2026-08-25).  이름에 `NT` 가 들어 있든 `KMTA-SCI-102` 든 상관없다.

    이름으로 유추하면 **운영이 붙인 이름 한 번 바꾸는 것이 자료의 정체를
    바꾼다** -- 실험실에서 유닛을 바꿔 꽂아 `-101` 이 NT 자리에 오는 일이
    실제로 있고, 그때 정본은 **배선**이지 이름이 아니다.
    """
    for c1, c2, want in (
            ('KMTA-SCI-102-NT', 'NC', 'MK'),   # 이름은 NT 스러운데 색인 1
            ('NC', 'KMTA-SCI-101-MK', 'NT'),   # 이름은 MK 스러운데 색인 2
            ('NT', 'NC', 'MK'),                # 이름이 태그 문자열 그 자체
            ('NC', 'MK', 'NT'),
    ):
        cfg = acfg_mod.load(make_ini(tmp_path, 1, ctrl1=c1, ctrl2=c2))
        assert cfg.solo_tag == want, f'{c1!r}/{c2!r} -> {cfg.solo_tag}'
        assert cfg.active_tags(CCDS) == (want,)


def test_the_keys_may_be_omitted_entirely(tmp_path):  # noqa: ANN001
    """키를 아예 안 써도 된다 -- 빈 값 · `NC` 와 같다.

    2대 운영 ini 에서 쓰지 않는 쪽 세 줄을 통째로 지우는 쓰임이다.
    """
    import configparser as cpmod

    def build(drop, keep):  # noqa: ANN001
        cp = cpmod.ConfigParser(inline_comment_prefixes=('#', ';'))
        cp.read(BASE_INI, encoding='utf-8')
        cp['archon']['n_controllers'] = '1'
        cp['archon']['ctrl_mk_host'] = '127.0.0.1'
        cp['archon']['ctrl_nt_host'] = '127.0.0.2'
        for k in drop:
            cp.remove_option('controllers', k)
        for k, v in keep.items():
            cp['controllers'][k] = v
        path = tmp_path / ('drop_%s.ini' % '_'.join(drop))
        with open(path, 'w', encoding='utf-8') as fh:
            cp.write(fh)
        return acfg_mod.load(str(path))

    # ctrl2_* 를 통째로 지우고 ctrl1 만 남긴다 -> MK
    cfg = build(('ctrl2_id', 'ctrl2_sn', 'ctrl2_cfg'),
                {'ctrl1_id': 'KMTA-SCI-101'})
    assert cfg.solo_tag == 'MK'
    assert cfg.active_tags(CCDS) == ('MK',)

    # 반대로 ctrl1_* 를 지우고 ctrl2 만 -> NT
    cfg = build(('ctrl1_id', 'ctrl1_sn', 'ctrl1_cfg'),
                {'ctrl2_id': 'KMTA-SCI-102'})
    assert cfg.solo_tag == 'NT'
    assert cfg.active_tags(CCDS) == ('NT',)


def test_one_controller_with_both_declared_is_refused(tmp_path):  # noqa: ANN001
    """**어느 쪽인지 정할 수 없는 상태로 진행하지 않는다.**

    그대로 두면 엉뚱한 chip 이름(`MK` vs `NT`)으로 자료가 저장되고, 파일만
    봐서는 알 수 없다.
    """
    with pytest.raises(acfg_mod.ArchonConfigError):
        acfg_mod.load(make_ini(tmp_path, 1, ctrl1='A', ctrl2='B'))


def test_absent_markers_are_shared_with_the_header_layer():
    """"없음" 표기는 `ControllersCfg` 한 곳이 정한다.

    대수 판정(`declared`)과 헤더(`overrides`)가 같은 판정을 써야 "ini 에
    적었는데 한쪽만 반영" 이 생기지 않는다.
    """
    from ics_sim.config import ControllersCfg

    for mark in ('', ' ', 'NC', 'nc', ' nc '):
        assert ControllersCfg.is_absent(mark), mark
    assert not ControllersCfg.is_absent('KMTA-SCI-101')


def test_one_controller_with_nothing_declared_falls_back_to_mk(tmp_path):  # noqa: ANN001
    """아무것도 없으면 MK 로 보되 경고를 남긴다 (기동은 막지 않는다)."""
    cfg = acfg_mod.load(make_ini(tmp_path, 1))
    assert cfg.solo_tag == 'MK'


@pytest.mark.parametrize('n', [0, 3, 4, -1])
def test_out_of_range_counts_are_refused(tmp_path, n):  # noqa: ANN001
    """0 이거나 3 이상이면 **기동을 멈춘다** (경고가 아니라 오류)."""
    with pytest.raises(acfg_mod.ArchonConfigError):
        acfg_mod.load(make_ini(tmp_path, n))


def test_count_wins_over_the_wiring(tmp_path):  # noqa: ANN001
    """주소가 둘 다 있어도 `n_controllers=1` 이면 한 대만 쓴다.

    반대로 대수만 믿고 주소가 없는 태그를 쓰지도 않는다 -- 두 검사는 **모두**
    통과해야 그 컨트롤러가 산다.
    """
    cfg = acfg_mod.load(make_ini(tmp_path, 1, ctrl2='KMTA-SCI-102'))
    assert cfg.active_tags(CCDS) == ('NT',)

    # 대수는 2 인데 NT 주소가 없다 -> 경고와 함께 MK 만 남는다
    cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    cp.read(BASE_INI, encoding='utf-8')
    cp['archon']['n_controllers'] = '2'
    cp['archon']['ctrl_mk_host'] = '127.0.0.1'
    cp['archon']['ctrl_nt_host'] = ''
    path = tmp_path / 'half.ini'
    with open(path, 'w', encoding='utf-8') as fh:
        cp.write(fh)
    assert acfg_mod.load(str(path)).active_tags(CCDS) == ('MK',)


# ---------------------------------------------------------------------------
# 헤더 -- 빠진 컨트롤러도 카드는 남는다
# ---------------------------------------------------------------------------

def test_missing_controller_keeps_its_cards_with_the_nc_sentinel():
    """**카드를 빼지 않는다.**  값만 규격 5.0절의 문자열 sentinel `'NC'` 다."""
    head = rawhdr.controller_header(
        {'units': ()}, backend_name='archon', ics_build='v0',
        cfg_ctrl={1: {'id': 'KMTA-SCI-101', 'sn': 'STA-0288'}})
    for card in ('CTRL1ID', 'CTRL1SN', 'CTRL1CFG',
                 'CTRL2ID', 'CTRL2SN', 'CTRL2CFG'):
        assert card in head, f'{card} 카드가 빠졌다'
    assert head['CTRL1ID'] == 'KMTA-SCI-101'
    assert head['CTRL1SN'] == 'STA-0288'
    # 선언되지 않은 자리는 전부 sentinel
    assert head['CTRL1CFG'] == 'NC'
    assert head['CTRL2ID'] == 'NC'
    assert head['CTRL2SN'] == 'NC'
    assert head['CTRL2CFG'] == 'NC'


def test_nc_written_in_the_ini_falls_back_to_the_sentinel():
    """ini 의 `NC` 는 빈 값과 같다 -- 헤더에도 `NC` 가 실린다.

    **표기를 하나로 둔 것이 요점이다** (운영자 확정 2026-08-25).  규격 5.0절이
    문자열 sentinel 을 `'NC'` 로 정해 두었으므로 ini 에도 그 낱말을 쓴다 --
    적은 것이 그대로 카드가 되므로 "어느 표기가 맞나" 를 물을 일이 없다.
    """
    from ics_sim.config import ControllersCfg

    c = ControllersCfg(ctrl2_id='NC', ctrl2_sn='NC', ctrl2_cfg='NC')
    assert c.overrides() == {}, 'NC 는 오버라이드로 넘어가면 안 된다'

    head = rawhdr.controller_header(
        {'units': ()}, backend_name='archon', ics_build='v0',
        cfg_ctrl=c.overrides())
    assert head['CTRL2ID'] == 'NC'
    assert head['CTRL2SN'] == 'NC'
    assert head['CTRL2CFG'] == 'NC'


def test_nc_is_absent_in_both_layers():
    """`NC` 는 두 자리에서 같은 뜻이다 -- "없다".

    헤더에서는 sentinel 로 떨어지고(`overrides()` 가 뺀다), 대수 판정에서는
    선언으로 세지 않는다(`declared()`).  두 자리가 갈리면 "ini 에 적었는데
    한쪽만 반영" 이 된다.
    """
    from ics_sim.config import ControllersCfg

    c = ControllersCfg(ctrl1_id='NC', ctrl2_id='KMTA-SCI-102')
    assert c.declared(1) is False
    assert c.declared(2) is True
    assert 1 not in c.overrides()


# ---------------------------------------------------------------------------
# 저장 자리 선검사 (labtest v1.1.3 이 세운 규칙, 2026-08-28)
# ---------------------------------------------------------------------------
#
# **저장 경로가 틀렸다는 것이 드러나는 자리가 종전에는 `write_frame()` 이었다**
# -- 그 시점에는 이미 fetch 를 마친 뒤라 **다 읽어낸 노출을 잃는다.**  labtest 가
# 같은 이유로 이 검사를 `POWERON` 앞으로 올렸다.

def _sim_cfg(data_dir: str):  # noqa: ANN201
    """`_storage_checks` 가 보는 최소한의 `ics_sim` 설정."""
    from ics_sim import config as simcfg

    cfg = simcfg.SimConfig()
    cfg.paths.data_dir = data_dir
    return cfg


def _storage_notes(tmp_path, data_dir, **over):  # noqa: ANN001
    cfg = acfg_mod.ArchonCfg(**over)
    return acfg_mod._storage_checks(cfg, _sim_cfg(str(data_dir)))


def test_storage_check_does_not_create_a_missing_data_dir(tmp_path):  # noqa: ANN001
    """⚠️ **없다고 만들지 않는다** -- 마운트 지점을 가리면 자료가 숨는다.

    가장 흔한 원인이 "마운트가 안 붙었다" 인데, 그때 만들어 버리면 OS 디스크에
    쌓이기 시작하고 **나중에 마운트가 붙으면 그 자료가 통째로 안 보인다.**
    """
    missing = tmp_path / 'not-mounted'
    notes = _storage_notes(tmp_path, missing)
    assert len(notes) == 1 and '마운트' in notes[0]
    assert not missing.exists(), '검사가 폴더를 만들면 안 된다'


def test_storage_check_flags_a_tight_disk(tmp_path):  # noqa: ANN001
    """pair 한 장이 688 MiB 라, 여유가 그 열 배에 못 미치면 알린다.

    문턱을 절대값(GB)이 아니라 **pair 장수**로 둔 것이 요점이다 -- 기하가
    바뀌면 뜻이 함께 따라가야 한다.
    """
    data = tmp_path / 'data'
    data.mkdir()
    # 실물 기하(19200x9400)면 pair 한 장이 688 MiB 다.
    notes = _storage_notes(tmp_path, data)
    tight = [n for n in notes if '여유가' in n]
    # 이 기계의 여유에 따라 갈리므로 **문구가 아니라 계산**을 본다.
    import shutil as _shutil
    free = _shutil.disk_usage(str(data)).free
    need = rawhdr.RAW_NAXIS1 * rawhdr.RAW_NAXIS2 * 2 * 2 * acfg_mod.STORAGE_MIN_PAIRS
    assert bool(tight) == (free < need)


def test_storage_check_is_quiet_when_there_is_room(tmp_path):  # noqa: ANN001
    """작은 기하(시험용)에서는 조용해야 한다 -- 경고가 늘 뜨면 무시하게 된다."""
    data = tmp_path / 'data'
    data.mkdir()
    assert _storage_notes(tmp_path, data, naxis1=12, naxis2=4) == []


# ---------------------------------------------------------------------------
# 헤더에 실릴 ini 값의 비ASCII (labtest 3중 방어의 첫째, 2026-08-28)
# ---------------------------------------------------------------------------

def test_non_ascii_ini_values_are_flagged_at_startup():
    """한글 한 자가 섞이면 그 카드가 `????` 로 실린다 -- 기동에서 알린다.

    ⚠️ **기동을 막지는 않는다.**  labtest 는 거부하지만 그쪽은 사람이 붙어 있는
    실험실 스크립트이고, 여기는 OBSAgent 가 상대인 상주 프로그램이다 -- 카드
    한 장 때문에 관측을 통째로 못 하게 만드는 쪽이 더 나쁘다.
    """
    from ics_sim import config as simcfg

    cfg = simcfg.SimConfig()
    cfg.controllers.ctrl1_id = 'KMTA-SCI-101'
    cfg.camera.camver = 'CEU-차상목'            # 손편집 오염
    notes = acfg_mod._ascii_checks(cfg)
    assert len(notes) == 1 and 'camver' in notes[0]
    assert 'ctrl1_id' not in notes[0]           # ASCII 는 안 센다

    cfg.camera.camver = 'CEU-v2.1'
    assert acfg_mod._ascii_checks(cfg) == []

    # ⚠️ **사이트별 표도 본다** -- 실제로 쓰이는 것은 `[site.<코드>]` 쪽이라,
    # `[site]` 덮어쓰기만 검사하면 현장 값이 통째로 빠진다.
    from ics_sim.config import SiteCfg

    cfg.site_table['KMTK'] = SiteCfg(telescop='KMTNet 1.6m #0 실험실')
    notes = acfg_mod._ascii_checks(cfg)
    assert len(notes) == 1 and 'site.kmtk' in notes[0], notes


def test_the_ascii_check_covers_every_ini_sourced_header_field():
    """⚠️ **목록을 코드로 못박아 둔다** -- 카드가 늘면 검사가 따라가야 한다.

    `[site]`/`[camera]`/`[controllers]` 에 헤더 카드가 늘 때 이 목록만 안 늘면
    새 카드가 조용히 검사 밖으로 빠진다.  그 어긋남을 여기서 잡는다.
    """
    from ics_sim import config as simcfg

    covered = {(sec, f) for sec, fields in acfg_mod._HEADER_INI_FIELDS
               for f in fields}
    cfg = simcfg.SimConfig()
    for section, _fields in acfg_mod._HEADER_INI_FIELDS:
        block = getattr(cfg, section, None)
        assert block is not None, section
        for name in vars(block):
            if name.startswith('_') or not isinstance(getattr(block, name), str):
                continue
            assert (section, name) in covered, (
                '%s.%s 가 문자열인데 비ASCII 검사 목록에 없다 -- 헤더에 실리는 '
                '값이면 _HEADER_INI_FIELDS 에 넣을 것' % (section, name))

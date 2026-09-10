#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide 카드 템플릿·이름 규칙 검증.

규격: `raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.9.md` 9·10장.
정본: guide 견본 헤더 v1.10 (값 128 + COMMENT 8 + END 1 + 공백 7 = 144
레코드 = 11,520 B) -- science 의 `test_raw_draft.py` 와 같은 정신으로
**바이트 단위 재현**을 대사한다.
"""

from __future__ import annotations

import glob
import io
import os
import sys

import pytest

import ics_archon  # noqa: F401  -- _simpath 배선

from icg_archon import (guidecards,  # noqa: E402
                        guidehdr, guidepair)
from ics_archon.archon import fitswrite  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import gen_guidecards as gen  # noqa: E402


def _samples() -> list[str]:
    """G 견본 헤더 -- 경로 하드코딩 대신 glob (개명에 안 깨진다).

    science 쪽 교훈 그대로 -- 없으면 skip 이 아니라 **실패**다
    (`test_raw_draft.py`, 2026-08-22 사고).
    """
    pats = os.path.join(REPO, 'raw_fits_spec',
                        'header_samples', 'KMT?.*.G.fits.header.v*[0-9].txt')
    found = [p for p in glob.glob(pats) if '+LF' not in p]
    assert found, 'guide 견본 헤더를 찾지 못했다 -- raw_fits_spec/ 확인'
    return sorted(found)


@pytest.mark.repo_only
def test_template_matches_the_sample_generator():
    """`guidecards.CARDS` = 생성기가 견본에서 뽑은 것 **그대로**여야 한다.

    견본이 개정되면(v1.1 승격) `tools/gen_guidecards.py` 를 다시 돌려야
    하고, 안 돌리면 여기서 걸린다 -- science 의 "기계 사본 표류" 알람과
    같은 자리다.
    """
    cards, _values = gen.parse()
    # ⏳ **일부러 갈라 둔 자리는 먼저 적용한다** (`guidecards.SPEC_PENDING`).
    # ⛔ 그 목록 밖의 갈림은 여기서 그대로 걸린다 -- 견본이 개정되면
    # `tools/gen_guidecards.py` 를 다시 돌리고 목록을 비운다.
    assert tuple(guidecards.apply_pending(cards)) == tuple(guidecards.CARDS), (
        'guidecards.CARDS 가 견본과 갈렸다 (SPEC_PENDING 밖의 차이) -- '
        'tools/gen_guidecards.py 를 다시 돌려 갱신할 것')


@pytest.mark.repo_only
def test_sample_bytes_are_reproduced():
    """견본 값을 넣으면 견본이 **바이트 단위로** 재현돼야 한다.

    카드 순서·형·폭·comment·패딩(공백 12 레코드 포함)이 전부 이 한 판에
    걸린다 -- guide 저장 경로(`fitswrite.header_bytes` + `WIDTHS`)의 대사다.
    """
    for path in _samples():
        cards, values = gen.parse(path)
        # ⏳ **견본의 템플릿으로** 재현한다 -- `CARDS` 는 `SPEC_PENDING` 만큼
        # 앞서 있어 그대로 쓰면 이 대사가 성립하지 않는다.  ⭐ 그래도 값어치는
        # 그대로다: 카드 순서·형·폭·comment·패딩의 대사는 살아 있고, 갈린 자리
        # 하나는 바로 위 시험이 따로 못박는다.
        widths = {k: w for k, _t, w, _c in cards if k != 'COMMENT'}
        rendered = guidecards.render(values, cards=cards)
        blob = fitswrite.header_bytes(rendered, 4224, 1033, widths=widths)
        want = open(path, 'rb').read()
        assert blob == want, '%s 재현 실패' % os.path.basename(path)


def test_card_counts_match_the_spec():
    """값 128 + COMMENT 8 (10.2절) -- 구성이 밀리면 여기서 먼저 걸린다."""
    values = [k for k, *_ in guidecards.CARDS if k != 'COMMENT']
    comments = [k for k, *_ in guidecards.CARDS if k == 'COMMENT']
    assert len(values) == 128
    assert len(comments) == 8
    # 미수록 규정 (10.2절) -- CTRL2*/C2_* 는 아예 없어야 한다.
    for key in ('CTRL2ID', 'CTRL2SN', 'CTRL2CFG',
                'C2_TEMP', 'C2_VOLT', 'C2_CURR',
                'CHMAP_LT', 'CHMAP_LB', 'CHMAP_RT', 'CHMAP_RB'):
        assert key not in values, '%s 는 guide 템플릿에 없어야 한다' % key
    # 신설·개명 (10.3절).
    for key in ('CHMAP', 'IMGROT', 'ICGBUILD'):
        assert key in values, '%s 가 guide 템플릿에 있어야 한다' % key
    assert 'ICSBUILD' not in values


def test_shared_key_widths_differ_from_science_where_the_sample_says_so():
    """공유 키 8장의 폭이 science 와 다르다 -- `WIDTHS` 주입의 존재 이유.

    이 사실이 사라지면(견본 개정으로 폭이 통일되면) `WIDTHS` 특례를 걷어낼
    수 있다 -- 그때 이 시험을 갱신하며 그 판단을 남길 것.
    """
    from ics_sim import rawcards
    sci = {k: w for k, _t, w, _c in rawcards.CARDS if k != 'COMMENT'}
    diff = {k: (guidecards.WIDTHS[k], sci[k])
            for k in guidecards.WIDTHS
            if k in sci and guidecards.WIDTHS[k] != sci[k]}
    assert diff == {
        'DATASRC': (26, 24), 'CTRL1ID': (26, 24), 'CTRL1SN': (26, 24),
        'CTRL1CFG': (26, 29), 'RDMODE': (26, 24),
        'C1_TEMP': (49, 51), 'C1_VOLT': (49, 51), 'C1_CURR': (49, 51),
    }


def test_render_drops_unknown_keys_and_none_values():
    """science `rawcards.render()` 와 같은 규칙 -- 낯선 키 차단·결측 미기록."""
    pool = {'NOSUCH': 1, 'DATE-OBS': None, 'OBJECT': 'x'}
    cards = guidecards.render(pool)
    keys = [k for k, _v, _c in cards]
    assert 'NOSUCH' not in keys
    assert 'DATE-OBS' not in keys          # None -> 카드 미기록 (5.0절)
    assert guidecards.value_of(cards, 'OBJECT').rstrip() == 'x'


def test_datasrc_follows_the_backend_not_a_constant():
    """규격 5.5절 -- `DATASRC` 는 시뮬 오인을 막는 카드다 (백엔드 유도)."""
    from icg_archon import guidehdr

    assert guidehdr.datasrc_of('archon_guide') == 'ARCHON_GUIDE'
    assert guidehdr.datasrc_of('sim_guide') == 'SIM'
    # 모르는 이름은 실물이라고 적지 않는다 (science 와 같은 방침).
    assert guidehdr.datasrc_of('nosuch') == 'SIM'
    assert guidehdr.datasrc_of('') == 'SIM'


def test_guide_naming_and_identity():
    """9.2절 -- `.G` 단일 파일, `EXPID` 는 `DETID` 필드 없음 (D-019)."""
    assert guidepair.guide_stem('KMTA', '20260821.123456') == \
        'KMTA.20260821.123456.G'
    assert guidepair.exposure_id('KMTA', '20260821.123456') == \
        'KMTA.20260821.123456'
    path = guidepair.guide_path('/d', 'KMTA', '20260821.123456')
    assert path.endswith('KMTA.20260821.123456.G.fits')


def test_resolve_guide_number_bumps_on_collision(tmp_path):
    """D-016 선검사의 guide 판 -- 경로 하나, 점유 시 +1, 되감음."""
    site, date = 'KMTK', '20260831'
    # 3번을 점유해 두면 3 제안 -> 4 확정.
    taken = tmp_path / ('%s.%s.000003.G.fits' % (site, date))
    taken.write_bytes(b'')
    got = guidepair.resolve_guide_number(str(tmp_path), site, date, 3)
    assert got == 4
    # 빈 자리면 그대로.
    assert guidepair.resolve_guide_number(str(tmp_path), site, date, 7) == 7
    # 999999 되감음 (D-018).
    assert guidepair.resolve_guide_number(
        str(tmp_path), site, date, 999999 + 1) == 0


# -- OI-24 의 답 (운영자 2026-09-07) ---------------------------------------
#
# ⭐ 둘이 함께 정해졌다: `INSTRUME` 어휘는 `'<SITE코드> Guide CCDs'` 이고,
# **guide CCD 도 FPA 조립체에 들어간다** -- 그래서 `FPAID` 는 science 와 같은
# 사이트 유도를 탄다.  ⚠️ 이 자리는 판마다 뜻이 달랐다: ~2026-09-06 공백 18자
# -> 09-06 `'NC'`(귀속 미결) -> 09-07 유도.  옛 파일로 판을 가늠하지 말 것.
# ⏳ 규격 10.3·10.6절 문면 갱신은 다음 `main` 라운드.


def test_instrume_default_is_the_guide_vocabulary():
    """비우면 `'<SITE코드> Guide CCDs'` -- science 의 '18k CCD' 를 안 따른다."""
    from icg_archon import guidehdr
    assert guidehdr.instrument_header('KMTC', {})['INSTRUME'] == 'KMTC Guide CCDs'


def test_ini_overrides_instrume_detector_and_fpaid():
    """⭐ ini 에 적으면 그 값이 이긴다 (5.0절 'ICS INI' 출처 카드).

    ⚠️ `DETECTOR` 는 2026-09-07 까지 **ini 를 안 읽었다** -- 모듈 상수만 실어
    그 줄을 적은 사람은 바뀐 줄 알았다.  그 회귀를 여기서 막는다.
    """
    from icg_archon import guidehdr
    out = guidehdr.instrument_header('KMTC', {'instrume': 'X CAM',
                                              'detector': 'e2v X',
                                              'fpaid': 'FPA#9',
                                              'camver': 'CEU-v9'})
    assert out['INSTRUME'] == 'X CAM'
    assert out['DETECTOR'] == 'e2v X'
    assert out['FPAID'] == 'FPA#9'
    assert out['CAMVER'] == 'CEU-v9'


def test_fpaid_is_derived_from_the_site_like_science():
    """⭐ guide 도 FPA 조립체에 든다 (OI-24 종결) -- 5.3.1절 · D-017 항목 6.

    ⚠️ **망원경 번호와 FPA 번호는 관측소 셋 모두 어긋난다** -- 맞추면 검출기
    귀속이 틀어진다.  그래서 표를 그대로 못박는다.
    """
    from icg_archon import guidehdr
    got = {c: guidehdr.instrument_header(c, {})['FPAID']
           for c in ('KMTC', 'KMTA', 'KMTS', 'KMTK')}
    assert got == {'KMTC': 'FPA#2', 'KMTA': 'FPA#1',
                   'KMTS': 'FPA#3', 'KMTK': 'FPA#0'}, got


def test_an_unknown_site_still_gets_the_sentinel():
    """⛔ 모르는 사이트에 조립체 번호를 지어내지 않는다 -- 5.0절 sentinel."""
    from icg_archon import guidehdr
    assert guidehdr.instrument_header('XXXX', {})['FPAID'] == 'NC'


# ---------------------------------------------------------------------------
# ⛔ sentinel 을 금지한 카드 -- guide 도 같은 규격 조항을 진다 (감사 #22)
# ---------------------------------------------------------------------------


def test_the_guide_shares_the_science_forbidden_set():
    """guide 는 집합을 **수입한다** -- 사본을 두면 조용히 갈린다.

    규격 5.0절은 계통을 안 가린다.  ⚠️ guide 헤더도 `EXPTIME`·`DATE-OBS`·
    geometry 여덟을 다 싣는다.
    """
    from ics_sim import rawcards
    assert guidecards.NO_SENTINEL is rawcards.NO_SENTINEL
    names = {k for k, _kind, _w, _c in guidecards.CARDS}
    assert guidecards.NO_SENTINEL <= names


@pytest.mark.parametrize('key', sorted(guidecards.NO_SENTINEL))
def test_a_missing_forbidden_guide_card_is_left_out(key):
    """값 풀에 없으면 카드를 비운다 (첫 갈래)."""
    pool = {k: 1 for k, _kind, _w, _c in guidecards.CARDS if k != 'COMMENT'}
    pool.pop(key)
    out = guidecards.render(pool)
    assert key not in {k for k, _v, _c in out}, key


#: science 와 같은 이유로 `DATE-OBS`(문자열)는 이 갈래를 안 지난다.
_G_CASTABLE = sorted(k for k, kind, _w, _c in guidecards.CARDS
                     if k in guidecards.NO_SENTINEL and kind != 'S')


@pytest.mark.parametrize('key', _G_CASTABLE)
def test_an_uncastable_forbidden_guide_card_is_left_out(key):
    """형 변환이 깨져도 카드를 비운다 (둘째 갈래)."""
    pool = {k: 1 for k, _kind, _w, _c in guidecards.CARDS if k != 'COMMENT'}
    pool[key] = object()
    out = guidecards.render(pool)
    assert key not in {k for k, _v, _c in out}, key


# ---------------------------------------------------------------------------
# guide 헤더 기본값 둘 -- OBSTYPE=GUIDE · OBSERVER=KMTNetOp (운영자 2026-09-09)
# ---------------------------------------------------------------------------


def test_the_guide_presses_its_own_header_defaults():
    """⭐ 부모(`IcsState`)의 기본은 science 값이라 ICG 가 눌러 둔다.

    ⛔ 이 둘이 `cfg.hardware.backend = 'sim'` 과 같은 부류의 자리다 -- 부모를
    쓰되 계통이 다른 값만 갈아 끼운다.  ⚠️ **명령이 이걸 덮는다** (기본값일
    뿐이다).
    """
    from ics_sim.state import IcsState
    assert IcsState().obstype == 'SCIENCE'      # ICS 쪽 기본
    assert IcsState().observer == 'none'
    src = io.open(os.path.join(ROOT, 'icg_archon', 'app.py'),
                  encoding='utf-8').read()
    assert "self.state.obstype = 'GUIDE'" in src
    assert "self.state.observer = 'KMTNetOp'" in src


def test_the_guide_pool_carries_obstype_through():
    """`guidehdr.build_pool` 이 `obstype` 을 실제로 실어야 한다.

    ⛔ 배선이 빠지면 guide 헤더만 조용히 `IMAGETYP` 사본으로 돌아간다 --
    science 시험은 그것을 못 잡는다.
    """
    pool = guidehdr.build_pool(
        site_code='KMTA', ctrl_info={'units': ()},
        ctrl_telem=None, sensors=None, cfg_site=None, cfg_camera=None,
        cfg_ctrl=None, rdmode='', backend_name='sim', telem_cards={},
        date_obs='2026-08-22T00:00:00.000', exptime=1.0, ledflash_ms=0,
        imgtype='OBJECT', objname='x', projid='x', observer='KMTNetOp',
        filename='f', expid='f', obstype='GUIDE')
    assert pool['OBSTYPE'] == 'GUIDE'
    assert pool['IMAGETYP'] == 'OBJECT'
    assert pool['OBSERVER'] == 'KMTNetOp'


# ---------------------------------------------------------------------------
# guide 전용 카드 -- LEDFLASH 를 빼고 TRIGOUT 을 넣었다 (운영자 2026-09-09)
# ---------------------------------------------------------------------------


def test_trigout_sits_right_after_exptime_and_ledflash_is_gone():
    """⭐ 자리가 뜻이다 -- 운영자가 **`EXPTIME` 바로 다음**으로 지정했다.

    ⚠️ 장수는 안 변한다 (`LEDFLASH` 한 장을 `TRIGOUT` 한 장이 대신한다) --
    그래서 144 레코드·11,520 B 가 그대로다.
    """
    keys = [k for k, *_ in guidecards.CARDS]
    assert 'LEDFLASH' not in keys, 'guide 에서 LEDFLASH 는 빠졌다'
    assert keys[keys.index('EXPTIME') + 1] == 'TRIGOUT'
    kind = {k: t for k, t, _w, _c in guidecards.CARDS}
    assert kind['TRIGOUT'] == 'I'


def test_science_keeps_ledflash_and_has_no_trigout():
    """⛔ **두 계통이 갈린다** (운영자 2026-09-09) -- science 는 종전 그대로.

    ⚠️ 이 시험이 없으면 다음 사람이 *"두 템플릿을 맞춰야지"* 하고 science 를
    따라 고친다.
    """
    from ics_sim import rawcards
    sci = [k for k, *_ in rawcards.CARDS]
    assert 'LEDFLASH' in sci
    assert 'TRIGOUT' not in sci


def test_the_pending_divergence_list_is_exactly_this_one_swap():
    """⏳ 견본과의 갈림은 **이 하나**여야 한다.

    ⛔ 목록이 늘면 규격 갱신이 밀린 자리가 늘었다는 뜻이다 -- 다음 `main`
    라운드에서 견본을 고치고 목록을 비운다.
    """
    assert len(guidecards.SPEC_PENDING) == 1
    old, new = guidecards.SPEC_PENDING[0]
    assert old == 'LEDFLASH'
    assert new[0] == 'TRIGOUT'


def test_the_card_is_left_out_when_nobody_knows():
    """⛔ 모르면 **카드를 비운다** -- `0` 은 *"펄스가 없었다"* 는 단언이다."""
    base = dict(
        site_code='KMTA', ctrl_info={'units': ()}, ctrl_telem=None,
        sensors=None, cfg_site=None, cfg_camera=None, cfg_ctrl=None,
        rdmode='', backend_name='sim', telem_cards={},
        date_obs='2026-08-22T00:00:00.000', exptime=1.0, ledflash_ms=0,
        imgtype='OBJECT', objname='x', projid='x', observer='x',
        filename='f', expid='f')
    assert 'TRIGOUT' not in guidehdr.build_pool(**base)
    assert guidehdr.build_pool(trigout=True, **base)['TRIGOUT'] == 1
    assert guidehdr.build_pool(trigout=False, **base)['TRIGOUT'] == 0


def test_obstype_works_on_the_guide_node_too():
    """운영자: *"`OBSTYPE` 지정은 ICG와 ICS 둘 다 동일하게"*.

    ⭐ 기반 `Dispatcher` 의 명령이라 ICG 가 **상속으로** 갖는다 -- ⛔ 없앤
    명령 목록(`UNSUPPORTED`)과 도움말 `drop=` 어디에도 들어 있으면 안 된다.
    """
    from icg_archon.commands import IcgDispatcher
    assert hasattr(IcgDispatcher, 'cmd_obstype')
    assert 'OBSTYPE' not in IcgDispatcher.UNSUPPORTED


def test_the_trigout_window_takes_a_datetime_not_an_epoch():
    r"""⛔ **`t_prev` 는 `datetime` 이고 래치는 epoch 다** (2026-09-10 벤치).

    내가 epoch 인 줄 알고 그대로 넘겨 `go 10` 이 첫 저장에서 `TypeError` 로
    죽었다 -- ⚠️ **시험이 `trigger_was_high_between()` 을 직접 float 로만
    불러서** 그 경로를 한 번도 안 지났다.  이제 시퀀서가 변환하는 것을 본다.
    ⚠️ naive 가 들어오면 **UTC 로 본다** -- 지역시로 보면 시간대만큼 창이 어긋난다.
    """
    import io as _io
    import os as _os
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(root, 'icg_archon', 'sequencer.py'),
                   encoding='utf-8').read()
    body = src[src.index('        ctrl = getattr(self.backend, \'ctrl\', None)'):]
    body = body[:body.index('trigger_was_high_between(start, now)') + 40]
    assert '.timestamp()' in body, 'datetime 을 epoch 로 바꿔야 한다'
    assert 'tzinfo is None' in body, 'naive 는 UTC 로 본다'
    # ⭐ 실제로 datetime 을 넣어 봐서 터지지 않는지 -- 위 문자열 검사만으로는
    # "고쳤다고 믿는" 상태가 또 생긴다.
    import datetime as _dt
    import time as _time
    from ics_archon.archon.controller import ArchonController
    latch = ArchonController.__new__(ArchonController)
    latch._trig_spans = None
    latch.note_trigger_level(True)
    when = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=1)
    assert latch.trigger_was_high_between(when.timestamp(), _time.time()) is True

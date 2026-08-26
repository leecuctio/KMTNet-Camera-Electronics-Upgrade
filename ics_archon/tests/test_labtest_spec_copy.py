#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""labtest 스크립트 안의 **규격 사본**이 `ics_sim` 과 갈라지지 않았나.

**왜 있나.**  raw spec 5장이 개정되면 견본 pair 와 함께 바뀌어야 하는 기계
사본이 이 저장소에 **셋**이다 (`ics_sim/rawcards.py` · `_vendor/ics_sim/
rawcards.py` · labtest 스크립트 내장 `RAWCARDS`).  앞의 둘은
`tools/sync_vendor.py` 와 `test_vendor.py` 가 지키는데, **labtest 사본만
아무도 안 봤다.**

그 사본이 갈라지면 어떻게 되나: labtest 는 실험실 단독 취득에 쓰는 별개
도구이므로 `ics_archon` 시험이 전부 통과해도 조용하다.  그러다 실험실에서 찍은
파일만 카드 구성이 달라지고, converter 는 그것을 **구조 변경**으로 읽는다.
발견 시점은 이미 자료가 쌓인 뒤다.

raw spec v1.5 반영 때 실제로 그 위험이 드러났다 -- HK 4장 폐지·`CHMAP_*` 4자
토큰·comment 오타 2건이 전부 이 세 사본에 **각각** 들어가야 했다.

⚠️ **스크립트를 import 하지 않는다.**  최상단에서 실물 컨트롤러에 접속하므로
`ast` 로 상수 정의만 뽑아 읽는다 (`tests/verify_labtest_v12.py` 와 같은 수법).
"""

from __future__ import annotations

import ast
import io
import os

import pytest

import ics_archon  # noqa: F401  -- `_simpath` 가 형제/내장 `ics_sim` 을 배선한다

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ics_archon/
LABTEST = os.path.join(ROOT, 'scr_labtest', 'archon_kmtnet_labtest_v1.2.bigbuf.py')


def _funcs(*names):  # noqa: ANN202
    """labtest 소스에서 함수 정의만 뽑아 **격리된 이름공간에서 실행**한다.

    상수 대조(`_literal`)만으로는 못 잡는 것이 있다 -- 카드 절단 규범처럼
    **동작**이 규격 사항인 자리다.  `tests/verify_labtest_v12.py` 와 같은
    수법이고, 그쪽과 달리 필요한 함수만 가져온다.
    """
    src = io.open(LABTEST, encoding='utf-8-sig').read()
    tree = ast.parse(src)
    chunks = []
    for node in tree.body:
        got = None
        if isinstance(node, ast.FunctionDef) and node.name in names:
            got = node
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in names:
                    got = node
        if got is not None:
            chunks.append(ast.get_source_segment(src, got))
    ns: dict = {}
    exec(compile('\n\n'.join(chunks), LABTEST, 'exec'), ns)   # noqa: S102
    missing = [n for n in names if n not in ns]
    assert not missing, f'labtest 에 {missing} 정의가 없다'
    return ns


def _literal(name: str):  # noqa: ANN202
    """labtest 소스에서 최상단 상수 하나를 값으로 꺼낸다."""
    assert os.path.exists(LABTEST), (
        f'labtest 스크립트가 없다 ({LABTEST}) -- 1년 실사용으로 검증된 계보이고 '
        '실험실 단독 취득에 계속 쓰는 도구다')
    src = io.open(LABTEST, encoding='utf-8-sig').read()
    for node in ast.parse(src).body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(node.value)
    raise AssertionError(f'labtest 에 {name} 정의가 없다')


@pytest.mark.repo_only
def test_labtest_rawcards_matches_the_template():
    """내장 `RAWCARDS` = `ics_sim.rawcards.CARDS` **그대로**여야 한다.

    키 순서·형·패딩 폭·comment 까지 같아야 한다 -- 견본 pair 의 바이트가
    그 넷으로 결정되기 때문이다 (raw spec 5장 머리말).
    """
    from ics_sim import rawcards

    got = [tuple(c) for c in _literal('RAWCARDS')]
    want = [tuple(c) for c in rawcards.CARDS]
    assert len(got) == len(want), (
        f'카드 수가 다르다 -- labtest {len(got)} vs 템플릿 {len(want)}.  '
        'raw spec 5장이 개정되면 세 사본을 함께 고쳐야 한다')
    diff = [(i, a, b) for i, (a, b) in enumerate(zip(got, want)) if a != b]
    assert not diff, '어긋난 카드 %d장:\n%s' % (
        len(diff),
        '\n'.join(f'  #{i}\n    labtest {a!r}\n    템플릿  {b!r}'
                  for i, a, b in diff[:5]))


@pytest.mark.repo_only
def test_labtest_chmap_matches_the_source():
    """내장 `CHMAP` = `ics_sim.rawhdr.CHMAP` (raw spec 4.5절 배선표의 투영)."""
    from ics_sim import rawhdr

    assert _literal('CHMAP') == rawhdr.CHMAP, (
        'labtest 의 CHMAP 이 원천과 다르다 -- 토큰 표기가 갈리면 실험실 자료만 '
        '다른 채널 이름을 싣게 된다 (v1.5: 3자 -> 4자 <chip><A|D><nn>)')


@pytest.mark.repo_only
def test_labtest_site_table_matches_the_spec_5_3_1():
    """내장 `SITE_INFO` = raw spec 5.3.1절 사이트별 상수표.

    `<SITE>`↔`OBSERVAT` 불일치는 이 규격의 **유일한 하드 실패**이므로
    (2.2절), 이 표가 갈라지면 실험실 산출물 전량이 변환에서 거부된다.
    """
    from ics_sim import rawhdr, rawpair

    site_info = _literal('SITE_INFO')
    assert set(site_info) == set(rawpair.OBSERVAT), (
        f'사이트 코드 집합이 다르다 -- labtest {sorted(site_info)} vs '
        f'규격 {sorted(rawpair.OBSERVAT)}')
    for code, row in site_info.items():
        observat, origin, telescop, fpaid = row
        assert observat == rawpair.OBSERVAT[code], code
        assert origin == rawpair.ORIGIN_OF[code], code
        assert telescop == rawhdr.VERIFIED_SITES[code]['telescop'], code
        assert fpaid == rawhdr.fpaid_of(code), code


@pytest.mark.repo_only
def test_labtest_temp_mods_match_spec_5_6_1():
    """내장 `TEMP_MODS`/`VOLT_RAILS` = 규격 5.6.1절 자리 표.

    자리 자체가 항목이라 순서가 하나만 밀려도 실험실 자료의 온도가 **다른
    모듈 것으로 읽힌다** -- 값이 그럴듯해서 아무도 의심하지 않는다.
    """
    from ics_sim import rawhdr

    assert tuple(_literal('TEMP_MODS')) == rawhdr.TEMP_MODS
    assert tuple(_literal('VOLT_RAILS')) == rawhdr.VOLT_RAILS


@pytest.mark.repo_only
def test_labtest_field_sentinel_matches_spec_5_6_1():
    """내장 `FIELD_NC` = 나열 카드 결측 sentinel (`'NC'`, 규격 5.6.1절).

    ⚠️ 단일 HK 카드의 `TEMP_NC`(`'-999.99'`)와 **다른 값**이라 헷갈리기 쉽다.
    7자짜리로 되돌아가면 열 자리를 채웠을 때 79자가 되어 카드 폭을 넘기고,
    나열 카드에서 값이 잘리면 **뒤 항목이 조용히 사라진다.**
    """
    from ics_archon.archon import parse

    assert _literal('FIELD_NC') == parse.FIELD_NC == 'NC'
    assert _literal('TEMP_NC') == '-999.99', '단일 HK sentinel 은 그대로다'


@pytest.mark.repo_only
def test_labtest_number_space_matches_d018():
    """되감음 경계·상한이 `rawpair.NUM_SPACE` 와 같아야 한다 (D-018).

    labtest 는 실험실 DS 번호 체계 때문에 처음부터 6자리 전체를 돌았고,
    D-018 로 관측 운용 쪽이 그것과 같아졌다 -- 두 값이 다시 갈리면 같은
    디렉토리를 두 규칙이 쓰게 된다.
    """
    from ics_sim import rawpair

    src = io.open(LABTEST, encoding='utf-8-sig').read()
    body = src[src.index('def resolve_pair_number'):]
    body = body[:body.index('\ndef ', 1)]
    assert str(rawpair.NUM_SPACE) in body.replace('_', ''), (
        f'labtest 의 번호 공간이 {rawpair.NUM_SPACE} 가 아니다 (D-018)')


def test_the_shipped_archon_ini_agrees_with_the_spec_requery_delay():
    """`ics_archon.ini` 의 재질의 지연이 규격 5.7.1절 값이어야 한다.

    ⚠️ **이 값은 지연이자 재질의 문턱이다** -- `EXPTIME <= 이 값` 이면
    재질의하지 않는다.  실기가 읽는 것은 ini 이므로, 코드 기본값만 고치고
    ini 를 두면 **실기에서만 문턱이 다르다.**  v1.5 반영 1차에서 실제로
    `ics_sim.ini` 는 1.0 인데 `ics_archon.ini` 만 3.0 으로 남아 있었다.

    `repo_only` 를 붙이지 않는다 -- ini 는 배치본에도 함께 간다.
    """
    import configparser

    from ics_sim.config import SimConfig

    ini = os.path.join(ROOT, 'ics_archon.ini')
    assert os.path.exists(ini), f'실기 ini 가 없다 ({ini})'
    cp = configparser.ConfigParser(inline_comment_prefixes=('#',))
    cp.read(ini, encoding='utf-8')
    got = cp['timing'].getfloat('aux_requery_after_shopen')
    assert got == SimConfig().timing.aux_requery_after_shopen, (
        f'ics_archon.ini 의 aux_requery_after_shopen 이 {got} 인데 코드 '
        f'기본값은 {SimConfig().timing.aux_requery_after_shopen} 다 -- '
        '규격 5.7.1절과 함께 움직여야 한다')


@pytest.mark.repo_only
def test_labtest_card_width_rule_matches_spec_5_0():
    """labtest 의 `fits_card` 도 **comment 를 먼저 자른다** (규격 5.0절, v1.6).

    ⚠️ **v1.6 에서 규칙이 뒤집혔다** -- 종전에는 값을 자르고 comment 를 살렸다.
    본편은 `archon/fitswrite.card_image()` 가 그렇게 바뀌었는데 **labtest 사본만
    구 규칙으로 남아 있었다** (2026-08-26 전수 검사에서 발견).  그러면 실험실
    자료만 `Cn_*` 나열 카드의 **뒤 항목이 조용히 사라진다** -- 자리가 곧
    항목이라(5.6.1절) 읽는 쪽은 그 사실을 알 방법이 없다.
    """
    g = _funcs('fits_card')
    long = '|'.join(['-40.1'] * 10)               # 59자 -- 견본 폭(51) 초과
    assert len(long) == 59
    card = g['fits_card']('C1_TEMP', 'S', 51, 'Ctrl-1 T[C]', long)
    assert len(card) == 80
    assert card.count("'") == 2, '카드가 깨지면 파일 전체를 못 읽는다'
    assert long in card, '값이 온전해야 한다 -- 잘린 것은 comment 여야 한다'
    assert not card.rstrip().endswith('Ctrl-1 T[C]'), 'comment 가 줄어야 한다'

    # comment 를 다 지워도 안 들어가면 그때 값을 자른다 -- 인용부호는 산다.
    huge = '|'.join(['-999.99'] * 10)             # 79자 (구 sentinel 의 모습)
    card2 = g['fits_card']('C1_TEMP', 'S', 51, 'Ctrl-1 T[C]', huge)
    assert len(card2) == 80 and card2.count("'") == 2

    # 규격이 정한 `NC` 로 열 자리를 채우면 잘리지 않는다 (5.6.1절의 이유).
    ok = '|'.join(['NC'] * 10)
    card3 = g['fits_card']('C1_TEMP', 'S', 51, 'Ctrl-1 T[C]', ok)
    assert ok in card3 and card3.rstrip().endswith('Ctrl-1 T[C]')


@pytest.mark.repo_only
def test_labtest_quotes_inside_a_value_are_doubled():
    """값 안의 `'` 는 겹쳐 쓴다 (FITS 표준 4.2.1) -- 본편과 같은 방어다.

    안 겹치면 그 자리가 값의 끝으로 읽혀 **카드가 통째로 깨지는데** 경고가 한
    줄도 안 뜬다.  labtest 사본에만 이 방어가 없었다.
    """
    g = _funcs('fits_card')
    card = g['fits_card']('OBJECT', 'S', 18, 'Name of object', "O'Brien")
    assert "O''Brien" in card
    assert len(card) == 80


@pytest.mark.repo_only
def test_labtest_absent_controller_fills_every_field():
    """전 자리 결측도 **자리 수만큼** `NC` 다 (규격 5.6.1절).

    실험실은 컨트롤러 한 대만 돌리므로 나머지 한 벌이 늘 이 경우다 --
    `'NC'` 한 토큰이면 자리 수가 1이 되어 읽는 쪽에 모듈 구성이 달라 보인다.
    """
    g = _funcs('fits_card', 'status_number', 'all_fields_nc',
               'ctrl_telemetry_cards', 'FIELD_NC', 'TEMP_NC',
               'TEMP_MODS', 'VOLT_RAILS')
    cards = g['ctrl_telemetry_cards'](None, 1)
    for n in (1, 2):
        assert cards['C%d_TEMP' % n] == '|'.join(
            ['NC'] * len(g['TEMP_MODS']))
        assert cards['C%d_VOLT' % n] == cards['C%d_CURR' % n] == '|'.join(
            ['NC'] * len(g['VOLT_RAILS']))
    # 값이 있어도 미장착 컨트롤러 쪽은 자리를 채운 채로 남는다.
    status = {k: '40.1' for k in g['TEMP_MODS']}
    status.update({r + '_V': '5.0' for r in g['VOLT_RAILS']})
    status.update({r + '_I': '1.0' for r in g['VOLT_RAILS']})
    cards2 = g['ctrl_telemetry_cards'](status, 1)
    assert len(cards2['C1_TEMP'].split('|')) == len(g['TEMP_MODS'])
    assert cards2['C2_TEMP'] == '|'.join(['NC'] * len(g['TEMP_MODS']))

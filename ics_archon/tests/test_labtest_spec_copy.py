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
`ast` 로 상수 정의만 뽑아 읽는다 (`tests/verify_labtest_v11.py` 와 같은 수법).
"""

from __future__ import annotations

import ast
import io
import os

import pytest

import ics_archon  # noqa: F401  -- `_simpath` 가 형제/내장 `ics_sim` 을 배선한다

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ics_archon/
LABTEST = os.path.join(ROOT, 'archon_kmtnet_labtest_v1.1.bigbuf.py')


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
def test_labtest_temp_slots_match_spec_5_6_1():
    """내장 `TEMP_SLOTS`/`VOLT_RAILS` = 규격 5.6.1절 자리 표.

    자리 자체가 항목이라 순서가 하나만 밀려도 실험실 자료의 온도가 **다른
    모듈 것으로 읽힌다** -- 값이 그럴듯해서 아무도 의심하지 않는다.
    """
    from ics_sim import rawhdr

    assert tuple(_literal('TEMP_SLOTS')) == rawhdr.TEMP_SLOTS
    assert tuple(_literal('VOLT_RAILS')) == rawhdr.VOLT_RAILS


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

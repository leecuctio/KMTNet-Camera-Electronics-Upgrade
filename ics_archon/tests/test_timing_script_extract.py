#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`acf/acf_timing_script_*.txt` 가 현행 정본 ACF 의 충실한 추출본인가.

그 txt 둘은 **받은 파일이 아니라 파생물**이다(`../acf/README.md` "타이밍 스크립트
freeze 사본").  저장소 밖에 진실의 원천이 없으므로 **원본 ACF 와의 일치가
유일한 앵커**다 -- guide ACF 판이 오르면서 `LINE` 블록이 바뀌면 txt 는 조용히
낡고, 그것을 읽는 `DevNote.md` 9.10 의 분석과 `acf/README.md` 의 전수 대조
서술이 함께 거짓이 된다.  ⚠️ 이 시험이 지키는 것은 **런타임 안전이 아니라
기록의 참됨**이다 -- 이 txt 를 읽는 코드는 없다.

⚠️ **깨지면 코드가 아니라 txt 를 고친다:**

    python tools/extract_timing_script.py acf/*.acf --out acf/

⚠️ **범위는 정본 `acf/*.acf` 뿐이다.**  `acf/archive/` 와
`__ref_archon_control/acf/` 는 **역사적 판**이라, 스크립트가 정당하게 개정되면
현행 txt 와 안 맞는 것이 맞는 상태다 -- 거기까지 걸면 정상 동작을 결함이라고
우기는 시험이 된다.  보관함의 `*_R<YYMMDD>.txt` 도 같은 이유로 뺀다(freeze
사본이라 갈리는 것이 제 일이다).  ⭐ 2026-09-03 현재는 24장이 전부 두 판 중
하나와 같지만 그것은 **관찰이지 규약이 아니다**.
"""

from __future__ import annotations

import glob
import io
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import extract_timing_script as ets  # noqa: E402


def _txt(kind: str) -> str:
    """저장소의 발췌 txt -- CRLF 로 체크아웃돼 있어도 LF 로 맞춰 읽는다."""
    path = os.path.join(ROOT, 'acf', 'acf_timing_script_%s.txt' % kind)
    with io.open(path, encoding='latin-1', newline='') as fh:
        return fh.read().replace('\r\n', '\n')


def _current_acfs() -> list[str]:
    """정본 `acf/` 한 층만 (`archive/` 는 안 본다 -- 글롭이 한 층이다)."""
    return sorted(glob.glob(os.path.join(ROOT, 'acf', '*.acf')))


@pytest.mark.repo_only
def test_the_two_txt_are_faithful_extracts_of_the_current_acfs():
    """정본 ACF 일곱의 내장 스크립트가 두 txt 와 **바이트 동일**한가.

    ⭐ 판은 `BIGBUF` 로 가른다 (science 1 / guide 0) -- 파일명으로 가르면
    개명이 시험을 깬다(`../SMC_CLAUDE.md` 함정 4).
    """
    acfs = _current_acfs()
    assert len(acfs) >= 2, 'acf/ 에 ACF 가 없다 -- 저장소 트리가 맞는가'
    want = {'guide': _txt('guide'), 'science': _txt('science')}
    seen = set()
    for path in acfs:
        text, _declared, bigbuf = ets.extract(path)
        kind = ets.kind(bigbuf)
        seen.add(kind)
        assert text == want[kind], (
            '%s 의 타이밍 스크립트가 acf_timing_script_%s.txt 와 다르다 -- '
            'ACF 를 고쳤으면 txt 를 다시 뽑아라: '
            'python tools/extract_timing_script.py acf/*.acf --out acf/'
            % (os.path.basename(path), kind))
    assert seen == {'guide', 'science'}, \
        '두 판이 다 있어야 한다 -- 본 것: %s' % sorted(seen)


@pytest.mark.repo_only
def test_declared_lines_matches_the_extracted_and_txt_line_counts():
    """`LINES=` == 뽑은 줄 수 == txt 줄 수 (guide 120 · science 142).

    guide 는 R2613 에서 113 -> 120 (FlushFrame LINE113~119 신설, 11.31).
    science 는 R2609 에서 137 -> 142 (FlushFrame LINE137~141 신설, 2026-09-05).

    ⚠️ 두 txt 는 **끝 개행이 없다** (`'\\n'.join` 의 서명).  그래서 `wc -l` 은
    112/136 을 내놓는다 -- 줄 수는 `count('\\n') + 1` 로 센다.  개행을 채우면
    위 시험이 깨진다.
    """
    counts = {k: _txt(k).count('\n') + 1 for k in ('guide', 'science')}
    assert counts == {'guide': 120, 'science': 142}   # guide: R2613 FlushFrame 7줄 (11.31) · science: R2609 FlushFrame 5줄
    for path in _current_acfs():
        text, declared, bigbuf = ets.extract(path)
        assert declared is not None, '%s 에 LINES= 가 없다' % path
        assert declared == text.count('\n') + 1
        assert declared == counts[ets.kind(bigbuf)]


#: 줄머리 앵커를 뺀 **틀린** 스캔 -- 함정 1 을 재현하는 대조군이다.
_LOOSE_RE = re.compile(r'LINE(\d+)=(.*)$')


def _loose_extract(path: str) -> str:
    """`^` 를 빼고 훑으면 무엇이 나오나 -- `MOD10\\VCPU_LINE*` 까지 딸려 온다."""
    rows: dict[int, str] = {}
    with io.open(path, encoding='latin-1') as fh:
        for raw in fh:
            m = _LOOSE_RE.search(raw.rstrip('\r\n'))
            if m:
                rows[int(m.group(1))] = ets._unquote(m.group(2))  # noqa: SLF001
    return '\n'.join(rows[i] for i in range(max(rows) + 1))


@pytest.mark.repo_only
def test_the_line_key_must_be_anchored_or_the_vcpu_program_leaks_in():
    """⚠️ 함정 1 -- guide ACF 의 `MOD10\\VCPU_LINE*` 은 추출 대상이 아니다.

    같은 ACF 안에 **두 번째 내장 스크립트**가 있다 (MKS 356 진공게이지 VCPU
    프로그램 109줄, `icg_archon/hk.py` 의 `DewpresDecoder` 가 그 출력을 읽는다).

    ⭐ **앵커가 실제로 일을 하는지 대조군으로 확인한다.**  줄 수만 보면
    느슨한 스캔도 113 을 내놓아서(키 개수·최댓값이 그대로고 값만 덮인다)
    함정을 못 잡는다 -- 그래서 결과가 **달라야 한다**고 단언한다.
    """
    guide = [p for p in _current_acfs() if ets.extract(p)[2] == 0]
    assert guide, 'guide ACF(BIGBUF=0)가 없다'
    path = guide[0]
    with io.open(path, encoding='latin-1') as fh:
        assert 'VCPU_LINE0=' in fh.read(), \
            '견본이 바뀌었다 -- 함정이 아직 있는지 확인할 것'
    text, _declared, _ = ets.extract(path)
    assert _loose_extract(path) != text, (
        '앵커가 풀렸다 -- `^LINE\\d+=` 로 줄머리를 잡아야 VCPU 프로그램이 안 섞인다')


def test_unquote_strips_only_the_wrapping_pair():
    """⚠️ 함정 2 -- 규칙은 "값에 공백이 있으면 감싼다" 다.

    자료에 기대지 않고 합성 입력으로 못박는다.  `replace('"', '')` 로
    갈아타거나 무조건 `v[1:-1]` 을 쓰면 여기서 걸린다.
    """
    assert ets._unquote('"RESET; IF x GOTO y"') == 'RESET; IF x GOTO y'  # noqa: SLF001
    assert ets._unquote('Start:') == 'Start:'          # 라벨 -- 안 감쌈  # noqa: SLF001
    assert ets._unquote('') == ''                      # 빈 줄  # noqa: SLF001
    assert ets._unquote('X') == 'X'                    # 단일 토큰  # noqa: SLF001
    assert ets._unquote('PCLK') == 'PCLK'              # 무조건 v[1:-1] 이면 'CL'  # noqa: SLF001
    assert ets._unquote('""') == ''  # noqa: SLF001
    # 값 **안쪽** 따옴표는 살려야 한다 (24장에도 0건이지만 규칙은 이것이다).
    assert ets._unquote('"A; CALL F("x")"') == 'A; CALL F("x")'  # noqa: SLF001

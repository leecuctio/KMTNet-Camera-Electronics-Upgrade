#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""관측 시험 스크립트(`.osc`) -- **두 벌이 갈라지지 않게 지킨다.**

`aic_integration_test_v0.0.osc` 는 저장소에 두 벌 있다 (운영자 지시
2026-08-25):

    ics_sim/osc/       시뮬 연동 시험
    ics_archon/osc/    실기 연동 시험

같은 스크립트로 시뮬과 실기를 나란히 돌리기 위한 것인데, **사본이 둘이면
갈라진다.**  이 저장소는 그 부류로 여러 번 데였다 -- 견본 헤더의 기계 사본이
셋이라 `sync_vendor.py --check` 와 바이트 대사를 붙여 두었고(규약 1번), 그
경험이 말하는 것은 하나다: **사본을 두는 것 자체는 괜찮지만 어긋남을 잡는
장치가 없으면 안 된다.**

여기서 잡는 것은 둘이다.
  1. 두 벌이 **바이트 단위로 같은가**
  2. `ostart` 줄번호 표가 **실제 줄 번호와 맞는가** -- 블록을 더하거나 빼면
     머리말 표가 조용히 낡는데, 그러면 운영자가 엉뚱한 자리에서 시작한다
"""

from __future__ import annotations

import os
import re

import pytest

SCRIPT = 'aic_integration_test_v0.0.osc'
REPO = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))
COPIES = (os.path.join(REPO, 'ics_archon', 'osc', SCRIPT),
          os.path.join(REPO, 'ics_sim', 'osc', SCRIPT))


def read(path: str) -> bytes:
    with open(path, 'rb') as fh:
        return fh.read()


def effective_lines(text: str) -> list[str]:
    """`ostart` 가 세는 줄 -- **주석과 빈 줄을 뺀 것**.

    `+` 지시어와 관측줄을 함께 센다 (운영자 확인 2026-08-25).
    """
    out = []
    for raw in text.splitlines():
        t = raw.strip()
        if t and not t.startswith('#'):
            out.append(t)
    return out


def test_both_copies_are_byte_identical():
    """⚠️ **한쪽만 고치면 여기서 걸린다.**"""
    for path in COPIES:
        assert os.path.isfile(path), f'사본이 없다: {path}'
    a, b = (read(p) for p in COPIES)
    assert a == b, (
        '두 사본이 갈라졌다 -- 고친 쪽을 다른 쪽에 복사할 것:\n  %s\n  %s'
        % COPIES)


def test_the_ostart_table_matches_the_real_line_numbers():
    """머리말의 `ostart <번호>` 표가 실제 줄 번호와 맞아야 한다.

    블록을 더하거나 빼면 표가 조용히 낡고, 그러면 운영자가 **엉뚱한 자리에서
    시작한다** -- 돔셔터를 여는 블록으로 잘못 들어가는 것이 가장 나쁜 경우다.
    """
    text = read(COPIES[0]).decode('utf-8')
    lines = effective_lines(text)

    # 머리말 표:  #   ostart   7   P1  저녁 보정 ...
    table = re.findall(r'^#\s+ostart\s+(\d+)\s+(P\d)\b', text, re.M)
    assert table, '머리말에 ostart 표가 없다'

    for num, phase in table:
        idx = int(num)
        assert 1 <= idx <= len(lines), (
            f'{phase}: 줄번호 {idx} 가 범위를 벗어난다 (전체 {len(lines)}줄)')
        got = lines[idx - 1]
        assert got.startswith('+msgout') and phase in got, (
            f'{phase}: {idx}번째 유효 줄이 그 블록의 시작이 아니다 -> {got!r}')


def test_every_phase_marker_is_in_the_table():
    """블록을 새로 넣고 표에 안 적는 것도 막는다."""
    text = read(COPIES[0]).decode('utf-8')
    listed = {p for _n, p in
              re.findall(r'^#\s+ostart\s+(\d+)\s+(P\d)\b', text, re.M)}
    present = set(re.findall(r'^\+msgout\s+\[\[\s+(P\d)\b', text, re.M))
    missing = present - listed
    assert not missing, f'표에 없는 블록: {sorted(missing)}'


@pytest.mark.parametrize('path', COPIES)
def test_every_exposure_line_has_the_projid_column(path):  # noqa: ANN001
    """⚠️ **관측줄의 맨 앞은 `PROJID` 다** -- 빠지면 그 줄이 통째로 버려진다.

    obstool 은 관측줄을 이렇게 읽는다 (`loadconfig.c:1148`):

        PROJID LABEL RA DEC COPT IMGTYP OBJECT FILTER EXPTIME UTOBS UTTOL
        [VelRA VelDEC]

    `sscanf` 가 **최소 9열**을 요구하고(`rtn<9` 면 skip), 열이 하나 밀리면
    필터·노출시간 검사에서 걸려 결국 버려진다.

    2026-08-25 실측: `PROJID` 를 빠뜨려 **"0 of 26 exposures imported"** 가
    났다.  저장소의 옛 견본(`bak.sample.osc` 2017 · `functest.osc` 2020)이
    `ProjID` 열이 생기기 전(v0.6.4) 판이라 그대로 베낀 것이 원인이었다 --
    **오래된 예시를 베낄 때는 그 사이에 형식이 바뀌었는지 본다.**
    """
    text = read(path).decode('utf-8')
    bad = []
    for n, raw in enumerate(text.splitlines(), start=1):
        t = raw.strip()
        if not t or t.startswith('#') or t.startswith('+'):
            continue
        fields = t.split('#')[0].split()
        if len(fields) < 11:
            bad.append((n, len(fields), t[:60]))
    detail = '; '.join('%d행 %d열: %s' % b for b in bad)
    assert not bad, ('관측줄에 열이 모자란다 (PROJID 부터 UTTOL 까지 11열) -- ' + detail)


@pytest.mark.parametrize('path', COPIES)
def test_exposure_times_are_inside_the_accepted_range(path):  # noqa: ANN001
    """`ExpTime` 이 [0.05, 18000] 밖이면 그 줄이 버려진다 (BIAS 는 예외).

    `loadconfig.c:1398` -- 범위 밖은 경고와 함께 skip 이다.  BIAS 는 값을
    보지 않고 0 으로 못박으므로 `-` 로 두어도 된다.
    """
    text = read(path).decode('utf-8')
    bad = []
    for n, raw in enumerate(text.splitlines(), start=1):
        t = raw.strip()
        if not t or t.startswith('#') or t.startswith('+'):
            continue
        f = t.split('#')[0].split()
        imgtyp, exptime = f[5].upper(), f[8]
        if imgtyp == 'BIAS':
            continue                      # 값을 안 본다
        try:
            v = float(exptime)
        except ValueError:
            bad.append((n, exptime, '숫자가 아니다'))
            continue
        if not (0.05 <= v <= 18000.0):
            bad.append((n, exptime, '범위 밖'))
    assert not bad, '노출 시간이 거부된다: %r' % (bad,)


@pytest.mark.parametrize('path', COPIES)
def test_the_script_is_ascii_safe_where_the_wire_reads_it(path):  # noqa: ANN001
    """`+msgout` 문구는 ASCII 여야 한다.

    obstool 이 그것을 IMPv2 로 내보내고 전송 계층이 `decode('ascii')` 를
    하므로(레거시는 ASCII 프로토콜이다) 한글은 `?` 로 바뀐다 -- 로그 표식이
    깨지면 이 스크립트의 목적 자체가 사라진다.  주석은 상관없다.
    """
    text = read(path).decode('utf-8')
    for line in text.splitlines():
        if line.strip().startswith('+msgout'):
            assert line.isascii(), f'+msgout 에 비ASCII: {line!r}'

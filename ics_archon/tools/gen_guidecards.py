#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide 견본 헤더 -> `icg_archon/guidecards.py` 의 `CARDS` 리터럴 생성기.

    python tools/gen_guidecards.py            # CARDS 리터럴을 stdout 으로
    python tools/gen_guidecards.py --diff     # science 템플릿과 폭·comment 대조만

**생성기를 저장소에 두는 이유**: science 쪽 원장 v1.6 이 기계 추출 생성물인데
생성기가 scratchpad 에서 소실된 전례가 있다 (raw_fits_spec 이력).  견본이
개정될 때(v1.1 승격 등) 이 도구를 다시 돌려 `guidecards.CARDS` 를 갱신하고,
`tests/test_icg_cards.py` 가 견본과의 표류를 지킨다.

정본: `raw_fits_spec/KMTA.20260821.123456.G.fits.header.v0.0.txt`
(raw spec v1.9 10장 -- 값 카드 123 + COMMENT 8 + END 1 + 공백 12 = 144 레코드).
"""

from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                              # ics_archon/
REPO = os.path.dirname(ROOT)

#: 견본 정본 (glob 이 아니라 판 번호를 박아 둔다 -- 승격되면 여기부터 갱신).
SAMPLE = os.path.join(REPO, 'raw_fits_spec',
                      'KMTA.20260821.123456.G.fits.header.v0.0.txt')

CARD = 80
_INT = re.compile(r'^[+-]?\d+$')


def records(path: str) -> list[str]:
    """80자 레코드 목록.  블록 정렬이 깨져 있으면 그 자리에서 멈춘다."""
    with open(path, 'rb') as fh:
        blob = fh.read()
    if len(blob) % 2880:
        raise SystemExit('%s 가 2880B 정렬이 아니다 (%d B)' % (path, len(blob)))
    text = blob.decode('ascii')     # 견본은 ASCII 전용이다 (raw spec 5.0절)
    return [text[i:i + CARD] for i in range(0, len(text), CARD)]


def split_string_value(rest: str) -> tuple[str, int, str]:
    """`'...' / comment` -> (내용 원문, 패딩 폭, comment).

    값 안의 `''`(겹친 따옴표)를 닫는 따옴표로 오독하지 않는다.
    """
    assert rest.startswith("'"), rest
    i = 1
    while True:
        j = rest.index("'", i)
        if rest[j + 1:j + 2] == "'":
            i = j + 2
            continue
        break
    padded = rest[1:j]
    after = rest[j + 1:]
    comment = after.split(' / ', 1)[1].rstrip() if ' / ' in after else ''
    return padded.replace("''", "'"), len(padded), comment


def parse(path: str = SAMPLE):
    """견본 -> (cards, values).

    cards  = rawcards.CARDS 와 같은 꼴의 (key, kind, width, comment) 목록
             (COMMENT 카드 포함, END 이후 제외).
    values = {key: 견본 값} -- 바이트 대사 시험이 값 풀로 쓴다.  문자열은
             패딩을 뗀 내용(render 가 폭까지 되채운다).
    """
    cards: list[tuple[str, str, int, str]] = []
    values: dict[str, object] = {}
    for rec in records(path):
        if rec.startswith('END'):
            break
        if rec.startswith('COMMENT'):
            cards.append(('COMMENT', '', 0, rec[8:].rstrip()))
            continue
        key = rec[:8].rstrip()
        assert rec[8:10] == '= ', rec
        rest = rec[10:]
        if rest.startswith("'"):
            content, width, comment = split_string_value(rest)
            cards.append((key, 'S', width, comment))
            values[key] = content.rstrip()
            continue
        token = rest[:20].strip()
        after = rest[20:]
        comment = after.split(' / ', 1)[1].rstrip() if ' / ' in after else ''
        if token in ('T', 'F'):
            kind: str = 'L'
            values[key] = token == 'T'
        elif _INT.match(token):
            kind = 'I'
            values[key] = int(token)
        else:
            kind = 'R'
            values[key] = float(token)
        cards.append((key, kind, 0, comment))
    return cards, values


def emit(cards) -> str:  # noqa: ANN001
    out = ['CARDS: tuple[tuple[str, str, int, str], ...] = (']
    for key, kind, width, comment in cards:
        out.append('    (%r, %r, %d, %r),' % (key, kind, width, comment))
    out.append(')')
    return '\n'.join(out)


def diff_against_science(cards) -> int:  # noqa: ANN001
    """공유 키의 폭·형이 science 템플릿과 갈리면 알린다 (fitswrite `_WIDTH`
    가 science 표라, 공유 키의 guide 폭이 더 좁으면 저장 바이트가 어긋난다)."""
    sys.path.insert(0, ROOT)
    import ics_archon  # noqa: F401  -- _simpath 가 ics_sim 을 배선한다
    from ics_sim import rawcards
    sci = {k: (t, w) for k, t, w, _c in rawcards.CARDS if k != 'COMMENT'}
    bad = 0
    for key, kind, width, _comment in cards:
        if key == 'COMMENT' or key not in sci:
            continue
        st, sw = sci[key]
        if (st, sw) != (kind, width):
            print('  갈림: %-8s guide (%s,%d) vs science (%s,%d)'
                  % (key, kind, width, st, sw))
            bad += 1
    print('공유 키 대조 끝 -- 갈림 %d건' % bad)
    return bad


def main(argv=None) -> int:  # noqa: ANN001
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--diff', action='store_true',
                    help='science 템플릿과 폭·형 대조만 한다')
    args = ap.parse_args(argv)
    cards, values = parse()
    n_val = sum(1 for k, *_ in cards if k != 'COMMENT')
    n_com = len(cards) - n_val
    print('# 견본: %s' % os.path.relpath(SAMPLE, REPO), file=sys.stderr)
    print('# 값 카드 %d + COMMENT %d' % (n_val, n_com), file=sys.stderr)
    if args.diff:
        return 1 if diff_against_science(cards) else 0
    print(emit(cards))
    return 0


if __name__ == '__main__':
    sys.exit(main())

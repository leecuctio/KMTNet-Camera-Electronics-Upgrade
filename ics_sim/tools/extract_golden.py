#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract golden fixtures from XIS runtime logs.

시뮬 출력을 실측 레거시 시퀀스와 대조하려면 로그 발췌가 필요한데, 원본 로그는
`*.log` 로 gitignore 되어 있고 전량 아카이브는 `__localonly_*` 규약상 커밋하지
않는다.  그래서 **발췌본을 픽스처로 커밋**해 다른 컴퓨터에서도 테스트가 돌게
한다 (DevNote 8장).

사용법::

    # 시간 구간으로 잘라내기
    python tools/extract_golden.py <logfile> \
        --start 2024-03-03T22:22:15 --end 2024-03-03T22:25:00 \
        -o tests/fixtures/golden_dark_ctio_20240303.txt

    # 특정 문자열이 처음 나오는 지점 주변
    python tools/extract_golden.py <logfile> \
        --around 'Image 1 of 5 complete' --before 60 --after 900 \
        -o tests/fixtures/golden_gon5_ctio_20240102.txt

기본적으로 ICS 계통 메시지만 남기고 OBS>TC 폴링 같은 소음은 뺀다.
"""

from __future__ import annotations

import argparse
import re
import sys

_HEAD = re.compile(r'^(?P<ts>\S+) (?:\[(?P<iface>[^\]]*)\] )?(?P<body>.*)$')
_TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
_MSG = re.compile(r'^(?P<src>[A-Za-z0-9._]+)>(?P<dst>[A-Za-z0-9._]+)\b')

#: 남길 노드 -- ICS 계통과 그 상대(OBS/TC/XIS).
KEEP_SRC = frozenset({'ICS', 'K.IC', 'M.IC', 'T.IC', 'N.IC',
                      'K.CB', 'M.CB', 'T.CB', 'N.CB', 'OBS', 'TC', 'XIS'})

#: 초당 반복돼 시퀀스를 가리는 폴링 트래픽.
NOISE = (
    re.compile(r'^OBS>TC (TSTAT|ASTAT)\b'),
    re.compile(r'^TC>OBS DONE: UP\b'),
    re.compile(r'^gmon>obs\b', re.IGNORECASE),
    re.compile(r'^OBS>GMON\b'),
    re.compile(r'^abc>tc\b', re.IGNORECASE),
    re.compile(r"^TC>'?ABC\b"),
)


def is_noise(body: str) -> bool:
    return any(p.match(body) for p in NOISE)


def keep(body: str, all_nodes: bool) -> bool:
    m = _MSG.match(body)
    if not m:
        return False
    if is_noise(body):
        return False
    if all_nodes:
        return True
    return m.group('src').upper() in KEEP_SRC


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('logfile')
    p.add_argument('-o', '--out', help='출력 파일 (기본: stdout)')
    p.add_argument('--start', help='시작 타임스탬프 접두사')
    p.add_argument('--end', help='끝 타임스탬프 접두사 (미포함)')
    p.add_argument('--around', help='이 문자열이 처음 나오는 줄 주변을 잘라낸다')
    p.add_argument('--before', type=int, default=40, help='--around 앞쪽 줄 수')
    p.add_argument('--after', type=int, default=400, help='--around 뒤쪽 줄 수')
    p.add_argument('--all-nodes', action='store_true',
                   help='ICS 계통 외 노드도 남긴다')
    p.add_argument('--max-lines', type=int, default=400, help='최대 출력 줄 수')
    args = p.parse_args(argv)

    with open(args.logfile, 'r', encoding='utf-8', errors='replace') as fh:
        lines = fh.readlines()

    if args.around:
        hit = next((i for i, ln in enumerate(lines) if args.around in ln), None)
        if hit is None:
            print(f'not found: {args.around}', file=sys.stderr)
            return 1
        lo = max(0, hit - args.before)
        hi = min(len(lines), hit + args.after)
        window = lines[lo:hi]
    else:
        window = lines

    picked: list[str] = []
    for raw in window:
        m = _HEAD.match(raw.rstrip('\r\n'))
        if not m:
            continue
        ts, body = m.group('ts'), m.group('body')
        # 로그 맨 위의 "XIS runtime log (re)started at .." 처럼 타임스탬프가 아닌
        # 줄은 범위 비교에서 제외한다.  문자열 비교라 'XIS' 가 날짜보다 커서
        # end 조건에 걸려 즉시 멈추는 함정이 있다.
        if not _TIMESTAMP.match(ts):
            continue
        if args.start and ts < args.start:
            continue
        if args.end and ts >= args.end:
            break
        if not keep(body, args.all_nodes):
            continue
        picked.append(body)
        if len(picked) >= args.max_lines:
            break

    out = open(args.out, 'w', encoding='utf-8') if args.out else sys.stdout
    with out:
        out.write('# Golden fixture extracted from an XIS runtime log.\n'
                  '# 생성: tools/extract_golden.py\n'
                  '# 원본 로그는 비커밋(*.log / __localonly_*), 이 발췌만 커밋한다.\n'
                  '# 타임스탬프와 [iface] 태그는 제거하고 메시지 본문만 남긴다.\n')
        for body in picked:
            out.write(body + '\n')
    print(f'{len(picked)} messages', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

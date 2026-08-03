#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan XIS runtime logs for message shapes, contamination, and state transitions.

DevNote 5장(메시지 오염 버그)과 6장(전량 스캔 신규 발견)의 근거를 만든 도구다.
로그 자체는 저장소에 없지만(`__localonly_*` 규약) 이 스크립트를 남겨 두면 원본이
있는 컴퓨터에서 언제든 재검증할 수 있다.

원본 위치 (비커밋):
    ics_legacy/__sample_isislog/                 9개월, 3사이트 샘플
    ../../__localonly_isislogs/ISIS.ICSci.*/     전량 아카이브 (48GB, 1,113일)

사용법::

    # 커맨드워드 슬롯 분류 -- 오염의 직접 증거
    python tools/scan_legacy_logs.py slots  <logdir> -o slots.txt

    # 메시지 형태 목록 -- 샘플에 없던 시퀀스 찾기
    python tools/scan_legacy_logs.py shapes <logdir> -o shapes.txt

    # OBSAgent CamStatus 재생 -- 상태 전이 실측
    python tools/scan_legacy_logs.py camstatus <logdir>

    # 오염 패턴만 추려 테스트 픽스처로
    python tools/scan_legacy_logs.py patterns <logdir> -o tests/fixtures/bug_patterns.txt
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from collections import Counter

# XIS 로그 한 줄:  <timestamp> [<iface>] <src>><dst> ...
_HEAD = re.compile(r'^\S+ (?:\[[^\]]*\] )?')
_MSG = re.compile(r'^(?P<src>[A-Za-z0-9._]+)>(?P<dst>[A-Za-z0-9._]+) '
                  r'(?P<type>DONE:|STATUS:|ERROR:|WARNING:|FATAL:)(?P<rest>.*)$')

#: OBSAgent 의 CamStatus 에 영향을 주는 발신 노드 (commands.c 757-759).
SCI_NODES = frozenset({'ICS', 'K.IC', 'M.IC', 'T.IC', 'N.IC',
                       'K.CB', 'M.CB', 'T.CB', 'N.CB'})

_NUM = re.compile(r'(?<==)[^\s]+')
_QUOTED = re.compile(r"'[^']*'")
_PAREN = re.compile(r'\((?:[^()]*)\)')
_BARE_NUM = re.compile(r'\b\d+\b')


def iter_logs(paths: list[str]):
    """디렉토리/파일 인자를 *.log 목록으로 편다."""
    for arg in paths:
        if os.path.isdir(arg):
            yield from sorted(glob.glob(os.path.join(arg, '**', '*.log'),
                                        recursive=True))
        else:
            yield arg


def iter_messages(paths: list[str], sci_only: bool = True,
                  to_obs_only: bool = False):
    """로그 줄을 (src, dst, type, rest, body) 로 흘려보낸다."""
    files = list(iter_logs(paths))
    for i, path in enumerate(files):
        if i % 100 == 0:
            print(f'  [{i}/{len(files)}] {os.path.basename(path)}',
                  file=sys.stderr, flush=True)
        try:
            fh = open(path, 'r', encoding='utf-8', errors='replace')
        except OSError:
            continue
        with fh:
            for line in fh:
                body = _HEAD.sub('', line).rstrip('\r\n')
                m = _MSG.match(body)
                if not m:
                    continue
                src = m.group('src').upper()
                if sci_only and src not in SCI_NODES:
                    continue
                if to_obs_only and m.group('dst').upper() not in ('OBS', 'AL', 'ALL'):
                    continue
                yield src, m.group('dst').upper(), m.group('type'), \
                    m.group('rest'), body


def shape_of(text: str) -> str:
    """값을 '#' 으로 치환해 메시지 '형태'만 남긴다."""
    s = _QUOTED.sub("'S'", text)
    s = _PAREN.sub('(S)', s)
    s = _NUM.sub('#', s)
    return _BARE_NUM.sub('#', s)


def cmd_slot(rest: str) -> str:
    """타입 토큰 뒤에서 첫 key=value 앞까지 = 커맨드워드 슬롯 (공백 보존)."""
    tokens = rest.split(' ')
    for j, tok in enumerate(tokens):
        if tok and '=' in tok:
            return ' '.join(tokens[:j])[:60]
    return rest[:60]


# ---------------------------------------------------------------------------
# 서브커맨드
# ---------------------------------------------------------------------------

def do_slots(args: argparse.Namespace) -> None:
    """커맨드워드 슬롯을 원문 그대로 분류한다 -- 오염의 직접 증거."""
    counts: Counter[tuple[str, str, str]] = Counter()
    example: dict[tuple[str, str, str], str] = {}
    for src, _dst, mtype, rest, raw in iter_messages(args.paths):
        key = (src, mtype, cmd_slot(rest))
        counts[key] += 1
        example.setdefault(key, raw[:300])

    out = open(args.out, 'w', encoding='utf-8') if args.out else sys.stdout
    with out:
        out.write('=== command-word slot catalogue (spacing preserved) ===\n')
        for (src, mtype, slot), n in counts.most_common(args.limit):
            out.write(f'{n:10d}  {src:5s} {mtype:9s} slot=[{slot}]\n')
            out.write(f'            EX: {example[(src, mtype, slot)]}\n')


def do_shapes(args: argparse.Namespace) -> None:
    """메시지 형태 목록.  두 스캔 결과를 diff 하면 새 시퀀스가 드러난다."""
    counts: Counter[str] = Counter()
    example: dict[str, str] = {}
    for _src, _dst, _t, _rest, raw in iter_messages(args.paths):
        sh = shape_of(raw)
        counts[sh] += 1
        example.setdefault(sh, raw[:300])

    out = open(args.out, 'w', encoding='utf-8') if args.out else sys.stdout
    with out:
        for sh, n in counts.most_common(args.limit):
            out.write(f'{n:10d}  {sh[:280]}\n')
            out.write(f'            EX: {example[sh][:280]}\n')


def do_camstatus(args: argparse.Namespace) -> None:
    """OBSAgent 의 CamStatus 상태머신을 재생해 전이를 집계한다.

    **dest 필터가 중요하다.**  OBSAgent 는 자기 앞으로 온 메시지만 본다.
    이 필터를 빠뜨리면 ICS>N.IC STATUS: TCSSTATUS .. EXPSTATUS=INTEGRATING 같은
    IC 행 중계까지 먹여서 있지도 않은 역행 전이가 대량으로 잡힌다
    (DevNote 12장 정정 이력 참고).
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from ics_sim.obsagent_model import CamStatusReplay

    replay = CamStatusReplay()
    for _src, _dst, _t, _rest, raw in iter_messages(args.paths, to_obs_only=True):
        replay.feed(raw)

    print('=== observed CamStatus transitions (dest in OBS/AL/ALL) ===')
    for (a, b), n in replay.transitions.most_common():
        print(f'{n:9d}  {a} -> {b}')


def do_patterns(args: argparse.Namespace) -> None:
    """오염 패턴만 추려 테스트 픽스처로 만든다.

    산출물은 `ics_sim/tests/fixtures/bug_patterns.txt` 로, 검증기가 레거시 버그를
    실제로 잡아내는지 확인하는 역방향 테스트에 쓴다.  원본 로그가 없는 환경에서도
    테스트가 돌도록 이 파일은 git 에 커밋한다 (DevNote 8장).
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from ics_sim.emitter import validate

    counts: Counter[str] = Counter()
    example: dict[str, str] = {}
    for _src, _dst, _t, _rest, raw in iter_messages(args.paths):
        problems = validate(raw)
        if not problems:
            continue
        key = shape_of(raw)
        counts[key] += 1
        example.setdefault(key, raw[:300])

    out = open(args.out, 'w', encoding='utf-8') if args.out else sys.stdout
    with out:
        out.write('# Legacy ICS message-contamination samples.\n'
                  '# 생성: tools/scan_legacy_logs.py patterns <logdir>\n'
                  '# 원본: ics_legacy/__sample_isislog/ (+ __localonly_isislogs/)\n'
                  '# 각 줄은 ics_sim.emitter.validate() 가 위반으로 잡아야 한다.\n'
                  '# 형식: <관측 건수>\\t<메시지 원문>\n')
        for key, n in counts.most_common(args.limit):
            out.write(f'{n}\t{example[key]}\n')


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    for name, fn, helptext in (
        ('slots', do_slots, '커맨드워드 슬롯 분류 (오염 증거)'),
        ('shapes', do_shapes, '메시지 형태 목록'),
        ('camstatus', do_camstatus, 'OBSAgent CamStatus 재생'),
        ('patterns', do_patterns, '오염 패턴 픽스처 생성'),
    ):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument('paths', nargs='+', help='로그 디렉토리 또는 파일')
        sp.add_argument('-o', '--out', help='출력 파일 (기본: stdout)')
        sp.add_argument('--limit', type=int, default=400, help='출력 항목 수')
        sp.set_defaults(func=fn)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

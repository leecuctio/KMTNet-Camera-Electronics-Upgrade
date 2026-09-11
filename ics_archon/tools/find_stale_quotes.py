#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""문구를 바꾼 커밋에서 **그 문구를 가리키는 자리**를 찾는다.

    python tools/find_stale_quotes.py                    # 작업 트리의 변경분
    python tools/find_stale_quotes.py --rev HEAD~1       # 그 리비전 이후
    python tools/find_stale_quotes.py --path ics_archon/ics_archon/archon/

## 왜 있나

⚠️ **문구를 바꾸면 그것을 가리키는 자리도 함께 고쳐야 한다.**  로그 문구는
시험이 `assert '…' in caplog.text` 로 대사하고, 문서는 그 줄을 인용한다.
2026-09-10 에 **여섯 번**, 2026-09-11 에 **아홉 번** 그것으로 스위트가 깨졌다
(`DevNote.md` 11.80).  사람이 기억으로 훑는 것이 반복적으로 실패했다.

## 어떻게

`git diff` 의 `-` 줄에서 **사라진 문자열 조각**을 뽑고, 그 조각이

* **원천의 문자열 리터럴에는 더 이상 없는데**
* 시험·문서에는 **아직 남아 있는** 자리

를 낸다.

## ⛔ 이 도구는 전수 시험을 대신하지 못한다

⚠️ **미리 보는 체일 뿐이다.**  종전 판은 *"이 조각이 원천에 아직 있나"* 를
`git grep` 으로 파일 전체에서 봤는데, 같은 문구가 **주석이나 docstring 에
남아 있으면** *"안 없어졌다"* 로 읽혀 **진짜 파손을 통째로 걸러 냈다** --
2026-09-11 에 그렇게 다섯 건이 빠져나가 스위트가 빨개졌다.

⭐ 그래서 여기서는 **AST 로 문자열 리터럴만** 본다 (주석·docstring·프로즈 제외).
⛔ 그래도 **문면을 바꾼 커밋은 전수를 돌리고 나서 커밋한다** -- 시험이 짧은
조각(`'POWER 필드가 없다'`)으로 대사하거나 영문 조각을 보면 이 체로는 안 걸린다.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys

#: 저장소 뿌리 -- 이 파일이 `<repo>/ics_archon/tools/` 에 있다.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

#: 인용처로 훑을 곳.  ⚠️ `__` 폴더와 `archive/` 는 읽기전용 보관본이라 뺀다.
QUOTERS = (
    'ics_archon/tests/', 'ics_archon/DevNote.md', 'ics_archon/SMC_CLAUDE.md',
    'ics_archon/README.md', 'ics_archon/INSTALL.md',
    'ics_archon/bench_test_plan.md', 'ics_archon/icg_first_run.md',
    'ics_sim/tests/', 'ics_sim/DevNote.md',
)

HANGUL = re.compile(r'[가-힣]')
#: 검색에 쓸 조각 -- 한글이 이어지는 덩이, 또는 영문 낱말 셋 이상.
KO_CHUNK = re.compile(r'[가-힣][가-힣 ·]{3,}')
EN_CHUNK = re.compile(r'[a-z][a-z]+(?: [a-z][a-z]+){2,}')

#: ⭐ **고쳐야 하는 자리의 표지** -- 앞으로 쓰라는 지시들이다.
#: `grep` 조리법 · *"이 줄을 챙겨라"* · 알려진 flake 의 **서명** · 시험 대사.
ACTIONABLE = (
    'grep', 'assert', '챙긴다', '챙길', '서명', '찾아라', '뜨는 값',
    '로 볼 것', '확인할 것', '를 볼 것', '적어 두고',
)
#: ⚠️ **과거 로그를 인용한 자리의 표지** -- 그때 그렇게 찍혔다는 **증거**라
#: 고치지 않는다.  타임스탬프 · 로그 수준 접두 · 유닛 태그로 알아본다.
TRANSCRIPT = re.compile(
    r'^\s*(?:\[?\d\d:\d\d:\d\d|\d{2}:\d{2}|Warning:|Error:|Info:|[A-Z]:\s)'
    r'|(?:Warning|Error|INFO|WARNING|ERROR):\s*[A-Z]?:?\s')


#: `--all` 이면 가르지 않고 다 낸다.
SHOW_ALL = False


def classify(line: str) -> str:
    """인용 한 줄을 `'fix'` / `'transcript'` / `'prose'` 로 가른다.

    ⚠️ **다 내면 아무것도 안 내는 것과 같다** -- 이 저장소에는 과거 벤치 로그를
    통째로 인용한 문단이 많아서, 가르지 않으면 매번 스무 건이 나오고 사람이
    그것을 무시하는 것을 학습한다 (`telemetry.check_telid` 와 같은 규범).
    """
    if SHOW_ALL:
        return 'fix'
    body = line.split(':', 2)[-1]
    if TRANSCRIPT.search(body):
        return 'transcript'
    if any(mark in body for mark in ACTIONABLE):
        return 'fix'
    return 'prose'


def git(*args: str) -> str:
    out = subprocess.run(('git',) + args, cwd=ROOT, capture_output=True,
                         encoding='utf-8', errors='replace')
    return out.stdout


def removed_chunks(rev: str | None, paths: list[str]) -> set[str]:
    """diff 의 `-` 줄에 있던 문자열 조각."""
    args = ['diff', '-U0']
    if rev:
        args.append(rev)
    args += ['--'] + paths
    chunks: set[str] = set()
    for line in git(*args).splitlines():
        if not line.startswith('-') or line.startswith('---'):
            continue
        for a, b in re.findall(r"'([^']{4,})'|\"([^\"]{4,})\"", line[1:]):
            text = a or b
            for pat in (KO_CHUNK, EN_CHUNK):
                for chunk in pat.findall(text):
                    chunk = chunk.strip()
                    if len(chunk) >= 6:
                        chunks.add(chunk)
    return chunks


def source_literals(paths: list[str]) -> str:
    """원천의 **문자열 리터럴만** 이어붙인 텍스트.

    ⭐ 주석·docstring 을 뺀다 -- 그것이 이 도구의 요점이다.
    ⚠️ 모듈·클래스·함수의 첫 문장(docstring)은 `ast.get_docstring` 으로 가려
    낸다.  그 밖의 벗은 문자열(주석 대용으로 쓴 것)도 같은 자리라 뺀다.
    """
    blobs: list[str] = []
    for rel in paths:
        full = os.path.join(ROOT, rel)
        files = []
        if os.path.isdir(full):
            for base, _dirs, names in os.walk(full):
                if '__pycache__' in base:
                    continue
                files += [os.path.join(base, n) for n in names
                          if n.endswith('.py')]
        elif full.endswith('.py'):
            files = [full]
        for path in files:
            try:
                tree = ast.parse(open(path, encoding='utf-8').read())
            except (OSError, SyntaxError):
                continue
            docs = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef,
                                     ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = ast.get_docstring(node, clean=False)
                    if doc is not None:
                        docs.add(doc)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) \
                        and isinstance(node.value, str) \
                        and node.value not in docs:
                    blobs.append(node.value)
    return '\n'.join(blobs)


def main(argv: list[str] | None = None) -> int:
    # ⚠️ 윈도우 콘솔이 **cp949** 라 한글·기호가 있는 줄에서 그냥 터진다.
    # 찾은 자리를 못 보여 주면 도구의 존재 이유가 없어지므로 여기서 맞춘다.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, OSError):   # 파이프·리다이렉트
            pass

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--rev', default=None,
                    help='이 리비전 이후의 변경분 (기본: 작업 트리)')
    ap.add_argument('--path', action='append', default=None,
                    help='원천 경로 (여러 번 줄 수 있다)')
    ap.add_argument('--all', action='store_true',
                    help='과거 로그 인용·일반 프로즈까지 다 낸다')
    args = ap.parse_args(argv)
    if args.all:
        global SHOW_ALL
        SHOW_ALL = True

    paths = args.path or ['ics_archon/ics_archon/', 'ics_archon/icg_archon/',
                          'ics_sim/ics_sim/']
    chunks = removed_chunks(args.rev, paths)
    live = source_literals(paths)
    stale = [c for c in sorted(chunks) if c not in live]

    if not chunks:
        print('바뀐 문자열이 없다 (diff 가 비었다)')
        return 0
    print('사라진 조각 후보 %d개 중 원천에 더 없는 것 %d개'
          % (len(chunks), len(stale)))

    fix: list[tuple[str, list[str]]] = []
    quiet = {'transcript': 0, 'prose': 0}
    for chunk in stale:
        found = git('grep', '-n', '-F', chunk, '--', *QUOTERS).strip()
        if not found:
            continue
        keep = []
        for line in found.splitlines():
            kind = classify(line)
            if kind == 'fix':
                keep.append(line)
            else:
                quiet[kind] += 1
        if keep:
            fix.append((chunk, keep))

    for chunk, lines in fix:
        print('-' * 70)
        print('없어진 문구: %r' % chunk)
        for line in lines:
            print('   ', line)
    print('=' * 70)
    if fix:
        print('⚠️ **같은 커밋에서 고칠 자리 %d건** -- 지시·조리법·시험 대사'
              % len(fix))
    else:
        print('⭐ 고칠 자리 없음')
    if any(quiet.values()):
        print('   (안 낸 것: 과거 로그 인용 %d줄 · 일반 프로즈 %d줄 -- '
              '전자는 증거라 고치지 않는다.  `--all` 로 다 본다)'
              % (quiet['transcript'], quiet['prose']))
    print('⛔ 그래도 전수 스위트를 돌리고 나서 커밋할 것 '
          '(이 체는 짧은 조각·영문 조각을 놓친다)')
    return 0


if __name__ == '__main__':
    sys.exit(main())

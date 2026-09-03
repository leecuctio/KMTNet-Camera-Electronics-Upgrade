#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACF 에 박힌 **타이밍 스크립트**를 텍스트로 뽑는다 -- `acf/acf_timing_script_*.txt` 의 정본 절차.

그 txt 둘은 **받은 파일이 아니라 ACF 에서 뽑은 파생물**이다(2026-09-03 출처 확인,
`../acf/README.md` "타이밍 스크립트 freeze 사본" 절).  종전에는 뽑는 절차가
어디에도 없었고 DevNote 9.10 이 *"`tools/` 밖의 일회성 스크립트"* 라고만 적어
두었다 -- **그래서 이 파일이 있다.**  산문으로 적힌 규칙은 다음 사람이 틀리게
옮기기 쉽고, 아래 규칙에는 실제로 밟기 쉬운 함정이 셋 있다.

    python tools/extract_timing_script.py acf/KMTK_GUI_162_STA0201_R2610.acf
    python tools/extract_timing_script.py acf/*.acf --out acf/          # 다시 뽑기
    python tools/extract_timing_script.py acf/*.acf --check acf/        # 대조만

`tests/test_timing_script_extract.py` 가 `--check` 와 같은 대조를 건다.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys

#: `[CONFIG]` 의 타이밍 스크립트 줄.
#:
#: ⚠️ **줄머리에 앵커한다 (함정 1).**  `LINE<n>=` 을 부분문자열로 품은 키가
#: 22장에 **1,713개**나 더 있다 -- `TAPLINE<n>=` 427 · `MOD<n>\\VCPU_LINE<n>=`
#: 1,219 (MKS 356 진공게이지 VCPU 프로그램.  `icg_archon/hk.py` 의
#: `DewpresDecoder` 가 그 출력을 읽는다).  `^` 를 빼고 훑으면 탭 순서 값과
#: VCPU 프로그램이 스크립트 자리를 덮어쓴다 -- ⚠️ **줄 수는 그대로라서 줄 수
#: 대조로는 안 걸린다**(`tests/test_timing_script_extract.py` 가 대조군으로 잡는다).
_LINE_RE = re.compile(r'^LINE(\d+)=(.*)$')

#: 스크립트 줄 수를 선언하는 키 (`LINES=113` / `137`).  대조에 쓴다.
_LINES_RE = re.compile(r'^LINES=(\d+)\s*$')

#: science(1) / guide(0) 를 가르는 키.  ⚠️ **파일명으로 가르지 말 것** --
#: 개명이 시험을 한 번 깬 적이 있다(`../SMC_CLAUDE.md` 함정 4).
_BIGBUF_RE = re.compile(r'^BIGBUF=(\d+)\s*$')


def _unquote(value: str) -> str:
    """값을 감싼 큰따옴표 **한 쌍만** 벗긴다.

    ⚠️ **함정 2** -- 규칙은 **"값에 공백이 있으면 감싼다"** 다.  라벨 줄
    (`LINE0=Start:`)·빈 줄과 `X`/`SWLOW`/`PCLK` 같은 단일 토큰은 안 감싸여 있다
    (22장 전수 반례 0건).  ⚠️ "라벨과 빈 줄만 안 감싼다" 로 옮기면 `X` -> 빈
    문자열, `PCLK` -> `CL` 로 83 줄이 망가진다.  안 벗기면 guide 1,923 B /
    science 2,321 B 가 나와 저장소의 txt(1,765 / 2,137)와 안 맞는다.  값
    **안쪽** 따옴표는 22장에 0건이라 "한 쌍만" 규칙은 지금 검증 대상이 없다.

    ⚠️ 반대로 `tools/ics_archon_buftest.py` 의 `read_acf()` 처럼
    `replace('"', '')` 로 **전부** 지우면 값 안쪽의 따옴표까지 사라져 원문이
    바뀐다 -- 그 규칙을 여기 빌려 오지 말 것.
    """
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def extract(path: str) -> tuple[str, int | None, int | None]:
    """ACF 한 장에서 `(스크립트, 선언된 LINES, BIGBUF)`.

    스크립트는 **LF 기준 문자열 하나**이고 **끝 개행이 없다**.

    ⚠️ **함정 3 -- 끝 개행을 붙이지 말 것.**  `'\\n'.join(...)` 의 결과라
    그렇고, 그것이 저장소 txt 의 서명이다.  붙이면 1 B 늘어 ACF 와의 바이트
    동일성이 깨지고 DevNote 9.10 의 주장이 조용히 거짓이 된다.  그래서
    `wc -l` 은 112/136 을 내놓지만 실제 줄 수는 113/137 이다 (`LINES=` 와 일치).
    줄 수를 셀 때는 `grep -c ''` 나 `text.count('\\n') + 1` 을 쓴다.

    작업 트리 사본이 CRLF 일 수 있으므로(윈도우) 대조하는 쪽에서 CRLF -> LF 로
    정규화해서 비교한다 -- 저장소에 들어가는 바이트는 `.gitattributes` 의
    `*.txt text eol=lf` 로 어차피 LF 다.
    """
    lines: dict[int, str] = {}
    declared: int | None = None
    bigbuf: int | None = None
    with io.open(path, encoding='latin-1') as fh:
        for raw in fh:
            raw = raw.rstrip('\r\n')
            m = _LINE_RE.match(raw)
            if m:
                lines[int(m.group(1))] = _unquote(m.group(2))
                continue
            m = _LINES_RE.match(raw)
            if m:
                declared = int(m.group(1))
                continue
            m = _BIGBUF_RE.match(raw)
            if m:
                bigbuf = int(m.group(1))
    if not lines:
        raise ValueError('%s: LINE<n>= 이 하나도 없다 -- ACF 가 맞는가' % path)
    missing = [i for i in range(max(lines) + 1) if i not in lines]
    if missing:
        raise ValueError('%s: LINE 번호에 구멍이 있다 -- %s'
                         % (path, missing[:8]))
    text = '\n'.join(lines[i] for i in range(max(lines) + 1))
    if declared is not None and declared != len(lines):
        raise ValueError('%s: LINES=%d 인데 실제 %d 줄이다'
                         % (path, declared, len(lines)))
    return text, declared, bigbuf


def kind(bigbuf: int | None) -> str:
    """`BIGBUF` 로 판을 가른다 -- science(1, 768 MB x 2) / guide(0, 512 MB x 3)."""
    return 'guide' if bigbuf == 0 else 'science'


def _target(out_dir: str, bigbuf: int | None) -> str:
    return os.path.join(out_dir, 'acf_timing_script_%s.txt' % kind(bigbuf))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('acf', nargs='+', help='ACF 파일 (여럿 가능)')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--out', metavar='DIR',
                   help='DIR/acf_timing_script_{guide,science}.txt 로 쓴다 (LF)')
    g.add_argument('--check', metavar='DIR',
                   help='DIR 의 같은 이름과 대조만 한다 (안 맞으면 exit 1)')
    args = ap.parse_args(argv)

    bad = 0
    written: dict[str, tuple[str, str]] = {}     # kind -> (첫 입력, 그 본문)
    for path in args.acf:
        try:
            text, declared, bigbuf = extract(path)
        except (OSError, ValueError) as exc:
            print('ERROR %s' % exc, file=sys.stderr)
            bad += 1
            continue
        name = os.path.basename(path)
        # ⚠️ 같은 판 ACF 여럿을 한 파일에 쓴다 -- 서로 어긋나면 **마지막 것만
        # 남고** 조용히 지나가므로 여기서 잡는다.  판이 새로 갈렸다는 신호다.
        first, body = written.get(kind(bigbuf), (None, None))
        if first is not None and body != text:
            print('ERROR %s 와 %s 의 %s 스크립트가 다르다 -- 판이 갈렸다.  '
                  '한 판씩 따로 뽑아라' % (first, name, kind(bigbuf)),
                  file=sys.stderr)
            bad += 1
            continue
        written[kind(bigbuf)] = (name, text)
        if args.out:
            dst = _target(args.out, bigbuf)
            # ⚠️ 읽기(`extract`)와 **같은 latin-1** 로 쓴다 -- 임의 바이트를
            # 손실 없이 통과시키려는 것이다.  utf-8 로 쓰면 비ASCII 가 한 줄만
            # 있어도 바이트가 늘어 `--out` -> `--check` 왕복이 영구 DIFF 가 된다.
            with io.open(dst, 'w', encoding='latin-1', newline='\n') as fh:
                fh.write(text)
            print('%-46s -> %s  (%d 줄)' % (name, dst, text.count('\n') + 1))
        elif args.check:
            dst = _target(args.check, bigbuf)
            try:
                with io.open(dst, encoding='latin-1', newline='') as fh:
                    got = fh.read().replace('\r\n', '\n')
            except OSError as exc:
                print('ERROR %s' % exc, file=sys.stderr)
                bad += 1
                continue
            ok = got == text
            print('%-46s %s %s  (LINES=%s)'
                  % (name, 'OK  ' if ok else 'DIFF', os.path.basename(dst),
                     declared))
            bad += 0 if ok else 1
        else:
            sys.stdout.write(text + '\n')
    if bad:
        print('\n어긋난 것 %d -- 다시 뽑으려면 --out 을 준다.' % bad,
              file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())

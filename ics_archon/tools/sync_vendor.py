#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`ics_sim` 을 `ics_archon` 안으로 내장(vendor)한다 -- **독립 배포를 위해.**

    python tools/sync_vendor.py            # 동기화 (필요한 것만 바꾼다)
    python tools/sync_vendor.py --check    # 바꾸지 않고 어긋난 것만 알린다

## 왜 사본을 두나 -- 그리고 왜 사본이어도 괜찮나

`ics_archon` 은 `ics_sim` 의 시퀀서·명령 처리부·메시지 규약·헤더 층을 그대로
쓴다.  종전에는 **형제 폴더를 `sys.path` 에 넣어** 썼다 -- 사본을 만들면
`rawcards.py`(견본 pair 의 기계 사본)가 세 벌이 되고, raw spec 5장이 개정될 때
어긋난 하나를 놓칠 수 있어서였다.

**그 걱정의 실체는 "사본" 이 아니라 "몰래 갈라짐" 이다.**  갈라짐을 기계가
잡아 주면 사본을 두어도 된다 -- 그래서 여기서 함께 만드는 것이 두 가지다:

1. **`MANIFEST.sha256`** -- 내장한 파일마다 해시.  배포된 트리에서도 내장본이
   손상·손편집되지 않았는지 혼자 확인할 수 있다 (원천이 없어도 된다).
2. **`tests/test_vendor.py`** -- ① 내장본이 매니페스트와 맞나 ② **원천이 있으면
   원천과도 맞나**(저장소에서는 항상 있다) ③ 내장본만으로 실제 노출이 도나.

②가 개정 누락을 잡는다.  `ics_sim` 을 고치고 이 도구를 안 돌리면 저장소 시험이
**실패**한다 -- 조용히 지나가지 않는다.

## 무엇을 어디로

    ics_sim/ics_sim/**   ->   ics_archon/ics_archon/_vendor/ics_sim/**

`_vendor` 가 `sys.path` 에 들어가므로 내장본은 그냥 `import ics_sim` 으로 잡힌다
(코드의 import 문을 고치지 않는다 -- 고치면 그 순간 사본이 아니게 된다).

`__pycache__` 와 `.pytest_cache` 는 옮기지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(os.path.dirname(HERE), 'ics_archon')
VENDOR = os.path.join(PKG, '_vendor')
DEST = os.path.join(VENDOR, 'ics_sim')
MANIFEST = os.path.join(VENDOR, 'MANIFEST.sha256')

#: 원천.  `ICS_SIM_SRC` 로 덮을 수 있다.
SRC = os.environ.get('ICS_SIM_SRC') or os.path.normpath(
    os.path.join(os.path.dirname(HERE), os.pardir, 'ics_sim', 'ics_sim'))

SKIP_DIRS = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}
#: 옮기지 **않는** 것.  파생물과 편집기 찌꺼기뿐이다.
SKIP_SUFFIX = ('.pyc', '.pyo', '.pyd', '.so', '.orig', '.rej', '.bak', '~')
SKIP_NAMES = {'.DS_Store', 'Thumbs.db'}


def sources(root: str) -> list[str]:
    """옮길 파일의 상대경로 목록 (정렬).

    **`.py` 만 고르지 않는다.**  확장자로 고르면 원천에 자료 파일(템플릿·표·
    스키마)이 새로 생겼을 때 **조용히 빠진다** -- 매니페스트도 같은 목록으로
    만들어지므로 `test_vendor.py` 까지 초록으로 통과하고, 배치본에서 그 파일을
    처음 읽는 순간에야 드러난다.  그래서 방향을 뒤집었다: **파생물만 빼고 전부
    옮긴다.**  과하게 담기는 것은 매니페스트에 보이지만, 빠지는 것은 안 보인다.
    """
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            if name in SKIP_NAMES or name.endswith(SKIP_SUFFIX):
                continue
            out.append(os.path.relpath(os.path.join(base, name), root)
                       .replace(os.sep, '/'))
    return sorted(out)


def digest(path: str) -> str:
    """파일 해시.  **바이트 그대로** 읽는다 -- 줄끝까지 사본이어야 한다."""
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def read_manifest() -> dict[str, str]:
    if not os.path.isfile(MANIFEST):
        return {}
    out = {}
    with open(MANIFEST, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            h, _, rel = line.partition('  ')
            if h and rel:
                out[rel] = h
    return out


def write_manifest(rows: dict[str, str]) -> None:
    os.makedirs(VENDOR, exist_ok=True)
    with open(MANIFEST, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# ics_sim 내장본의 파일별 sha256.\n'
                 '# tools/sync_vendor.py 가 만든다 -- 손으로 고치지 말 것.\n'
                 '# 확인:  python tools/sync_vendor.py --check\n')
        for rel in sorted(rows):
            fh.write('%s  %s\n' % (rows[rel], rel))


def main(argv=None) -> int:  # noqa: ANN001
    ap = argparse.ArgumentParser(
        prog='sync_vendor',
        description='ics_sim 을 ics_archon 안으로 내장한다 (독립 배포용)')
    ap.add_argument('--check', action='store_true',
                    help='바꾸지 않고 어긋난 것만 알린다 (CI·시험용)')
    ap.add_argument('--src', default=SRC, help='원천 ics_sim 패키지 경로')
    args = ap.parse_args(argv)

    src = os.path.abspath(args.src)
    if not os.path.isfile(os.path.join(src, '__init__.py')):
        print("원천을 찾을 수 없다 -- '%s' 에 ics_sim 패키지가 없다.\n"
              'ICS_SIM_SRC 로 지정하거나 --src 를 주라.' % src, file=sys.stderr)
        return 2

    rel_src = sources(src)
    rel_dst = sources(DEST) if os.path.isdir(DEST) else []

    added = [r for r in rel_src if r not in rel_dst]
    removed = [r for r in rel_dst if r not in rel_src]
    changed = [r for r in rel_src if r in rel_dst
               and digest(os.path.join(src, r)) != digest(os.path.join(DEST, r))]

    print('원천   %s  (%d 파일)' % (src, len(rel_src)))
    print('내장본 %s  (%d 파일)' % (DEST, len(rel_dst)))
    for label, items in (('신규', added), ('삭제', removed), ('변경', changed)):
        if items:
            print('  %s %d: %s' % (label, len(items), ', '.join(items[:6])
                                   + (' …' if len(items) > 6 else '')))

    drift = added or removed or changed

    # 매니페스트 자체도 확인한다 -- 내장본이 원천과 같더라도 매니페스트가
    # 낡아 있으면 배포된 트리에서 자가 확인이 안 된다.
    #
    # ⚠️ **`--check` 만이 아니라 동기화 경로도 이 검사를 쓴다** (2026-08-26).
    # 종전에는 동기화 쪽이 `read_manifest()` 의 **존재 여부**만 보고 "이미
    # 동기 상태다" 로 빠져나갔다.  원천과 내장본을 **둘 다 손으로 같게
    # 고치면**(개정 반영에서 흔한 일이다) 옮길 파일이 없어 그 경로를 타는데,
    # 그때 매니페스트만 낡은 채로 남는다 -- 도구는 초록인데
    # `test_vendor.py` 는 빨갛고, 도구가 방금 "할 일 없다" 고 말한 뒤라
    # 원인을 찾기 어렵다.
    want = read_manifest()
    have = {r: digest(os.path.join(DEST, r)) for r in rel_dst}
    stale_manifest = want != have
    if stale_manifest:
        print('  매니페스트가 내장본과 어긋난다 (%d vs %d 항목)'
              % (len(want), len(have)))

    if args.check:
        drift = drift or stale_manifest
        print('\n%s' % ('어긋남 있음 -- 동기화가 필요하다 (--check 없이 다시 '
                        '돌려라)' if drift else '동기 상태다'))
        return 1 if drift else 0

    if not drift and not stale_manifest:
        print('\n이미 동기 상태다 -- 아무것도 바꾸지 않았다')
        return 0

    if not drift:
        # 파일은 같고 매니페스트만 낡았다 -- 다시 옮길 것 없이 해시만 고친다.
        write_manifest(have)
        print('\n매니페스트만 갱신했다 -- %d 파일 (내장본은 원천과 이미 같다)'
              % len(have))
        return 0

    # **디렉터리를 통째로 다시 만든다.**  파일만 덮으면 원천에서 지운 모듈이
    # 내장본에 남아, 있지도 않은 모듈을 import 하는 코드가 조용히 돈다.
    if os.path.isdir(DEST):
        shutil.rmtree(DEST)
    rows = {}
    for rel in rel_src:
        s = os.path.join(src, rel)
        d = os.path.join(DEST, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(s, d)          # 바이트 그대로 (줄끝 포함)
        rows[rel] = digest(d)
    write_manifest(rows)
    print('\n내장 완료 -- %d 파일, 매니페스트 갱신' % len(rows))
    print('시험으로 확인:  python -m pytest tests/test_vendor.py -q')
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`ics_sim` 층을 어디서 가져오나 -- **이 저장소에서 유일한 sys.path 손질이다.**

`ics_archon` 은 `ics_sim` 의 시퀀서·명령 처리부·메시지 규약·헤더 층을 그대로
쓴다 (`ics_archon/SMC_CLAUDE.md`).  그것을 **셋 중 하나**에서 찾는다:

| 순서 | 어디 | 언제 |
|---|---|---|
| 1 | `ICS_SIM_PATH` 환경변수 | 명시적으로 지정했을 때 (탈출구) |
| 2 | 형제 폴더 `../../ics_sim` | **저장소에서 개발할 때** -- 살아 있는 원천을 쓴다 |
| 3 | 내장본 `_vendor/ics_sim` | **독립 배포** -- `ics_archon/` 만 설치했을 때 |

**독립 실행이 요구사항이다** (운영자 확정 2026-08-23): `ics_sim` 을 설치하지
않고 `ics_archon` 만 두어도 돌아야 한다.  그래서 내장본이 있다.

## 사본을 두는 것이 왜 괜찮아졌나

종전에는 사본을 만들지 않았다 -- `rawcards.py`(견본 pair 의 기계 사본)가 세
벌이 되면 raw spec 5장 개정 때 어긋난 하나를 놓친다는 이유였다.  **그 걱정의
실체는 "사본" 이 아니라 "몰래 갈라짐" 이다.**  갈라짐을 기계가 잡으면 사본을
두어도 된다:

* `tools/sync_vendor.py` 가 내장하고 `_vendor/MANIFEST.sha256` 을 만든다.
* `tests/test_vendor.py` 가 ① 내장본이 매니페스트와 맞나(원천 없이도 확인 가능)
  ② **원천이 있으면 원천과도 맞나**(저장소에서는 항상 있다) ③ 내장본만으로
  실제 노출이 도나 -- 셋을 본다.

②가 개정 누락을 잡는다.  `ics_sim` 을 고치고 동기화를 안 하면 저장소 시험이
**실패한다** (skip 이 아니다 -- DevNote 11.21 의 교훈).

## 개발 중에는 형제가 이긴다

저장소에서는 2번이 3번보다 먼저다.  `ics_sim` 을 고치면 그 변경이 곧바로
`ics_archon` 시험에 반영돼야 하기 때문이다 -- 내장본이 이기면 "고쳤는데 안
바뀐다" 를 만든다.  둘이 갈라졌는지는 위 ②가 알려 준다.

나중에 `ics` 로 개명해 하나의 설치 패키지로 배포하면 이 파일은 사라진다.
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

#: 형제 저장소의 `ics_sim` (그 안에 `ics_sim/` 패키지가 있다)
_SIBLING = os.path.normpath(os.path.join(_HERE, os.pardir, os.pardir, 'ics_sim'))
#: 내장본을 담은 폴더 (그 안에 `ics_sim/` 패키지가 있다)
_VENDOR = os.path.join(_HERE, '_vendor')

#: 뒤늦게 바꿀 수 있게 남겨 둔다 -- 시험이 이것을 가리켜 실패 경로를 재현한다.
SIM_ROOT = os.environ.get('ICS_SIM_PATH') or ''

#: 실제로 고른 곳과 그 근거.  `ensure()` 가 채우고 기동 배너가 찍는다.
CHOSEN = ''
CHOSEN_WHY = ''


def _has_package(root: str) -> bool:
    return bool(root) and os.path.isfile(
        os.path.join(root, 'ics_sim', '__init__.py'))


def candidates() -> list[tuple[str, str]]:
    """찾아볼 곳 목록 `(근거, 경로)` -- 위 표의 순서 그대로."""
    out: list[tuple[str, str]] = []
    env = SIM_ROOT or os.environ.get('ICS_SIM_PATH') or ''
    if env:
        out.append(('ICS_SIM_PATH 환경변수', os.path.abspath(env)))
    out.append(('형제 저장소', _SIBLING))
    out.append(('내장본 (_vendor)', _VENDOR))
    return out


def ensure() -> str:
    """`ics_sim` 을 import 할 수 있게 만들고 그 뿌리 경로를 돌려준다."""
    global CHOSEN, CHOSEN_WHY
    if CHOSEN and _has_package(CHOSEN):
        return CHOSEN

    tried = []
    for why, root in candidates():
        tried.append('  %-22s %s%s' % (why, root,
                                       '' if _has_package(root) else '   (없음)'))
        if not _has_package(root):
            continue
        # **append 가 아니라 insert 다.**  같은 이름의 다른 패키지가 사이트
        # 패키지에 있으면 그쪽이 이긴다 -- 우리가 고른 것이 정본이어야 한다.
        if root not in sys.path:
            sys.path.insert(0, root)
        CHOSEN, CHOSEN_WHY = root, why
        return root

    raise ImportError(
        'ics_sim 패키지를 찾을 수 없다. 찾아본 곳:\n' + '\n'.join(tried) +
        '\n\n고치는 방법 셋 중 하나:\n'
        '  1) ICS_SIM_PATH 로 ics_sim 패키지의 **상위** 폴더를 지정한다\n'
        '  2) ics_sim/ 폴더를 ics_archon/ 과 형제로 둔다 (저장소 배치)\n'
        '  3) 내장본을 만든다:  python tools/sync_vendor.py\n'
        '     (독립 배포는 이 방법이다 -- ics_sim 을 설치하지 않아도 된다)')


def describe() -> str:
    """기동 배너용 한 줄 -- **어느 사본이 돌고 있나.**

    둘 이상 있을 수 있으므로(저장소 + 내장본) 어느 것을 골랐는지 보여 주는 것이
    진단의 출발점이다.
    """
    if not CHOSEN:
        return '(아직 정하지 않음)'
    return '%s  <- %s' % (CHOSEN, CHOSEN_WHY)

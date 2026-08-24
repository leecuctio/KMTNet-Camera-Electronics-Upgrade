#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""테스트 경로 배선.

`ics_archon` 패키지와 `tests/` 를 함께 import 할 수 있게 한다.  `ics_sim` 은
`ics_archon._simpath` 가 알아서 잡는다.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (_ROOT, os.path.join(_ROOT, 'tests')):
    if path not in sys.path:
        sys.path.insert(0, path)


def pytest_configure(config):  # noqa: ANN001, ANN201
    """`repo_only` 표식 등록.

    **저장소에서는 전부 돌린다.**  이 표식은 "안 돌려도 되는 시험" 이 아니라
    "배치본에는 원천이 없어서 못 돌리는 시험" 이라는 뜻이다 -- 저장소에서
    `-m "not repo_only"` 를 쓰면 벤더 표류와 견본 어긋남을 놓친다.
    """
    config.addinivalue_line(
        'markers',
        'repo_only: 저장소 트리에서만 돌아간다 (형제 ics_sim 원천 · '
        'raw_fits_spec 견본 pair 가 있어야 한다).  배치본에서는 '
        '-m "not repo_only" 로 뺀다')

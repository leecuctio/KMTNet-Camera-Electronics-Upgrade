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

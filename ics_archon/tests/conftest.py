#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""테스트 경로 배선.

`ics_archon` 패키지와 `tests/` 를 함께 import 할 수 있게 한다.  `ics_sim` 은
`ics_archon._simpath` 가 알아서 잡는다.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (_ROOT, os.path.join(_ROOT, 'tests')):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture(autouse=True)
def no_real_redis(request):
    """⛔⛔ **시험은 진짜 redis 에 붙지 않는다.**

    배포 `ics_archon.ini`/`icg_archon.ini` 는 `[dome] source = redis` 다 --
    실기에서 켜져 있어야 하니까.  그런데 이 스위트의 시험 대부분은 **그 ini 를
    밑바탕으로 읽어** 실제 노출을 돌린다(`test_ini_cards.py` 의 `write_ini()`
    등 열 남짓). 그대로 두면:

    * 개발 기계 -- 접속 거부라 `NC` 가 되고 시험은 통과한다.  다만 노출마다
      TCP 시도를 한다.
    * ⛔ **벤치·관측소 기계 -- 진짜 redis 가 돌고 있다.**  스위트가 그 서버의
      실값을 읽어 헤더에 싣고, `NC` 를 기대하는 시험이 **거기서만** 깨진다.
      DevNote 11.20 의 *"시뮬은 통과하는데 실기에서 깨진다"* 를 그대로 뒤집은
      부류이고, 기계마다 결과가 달라지는 것이 더 나쁘다.

    ⭐ 그래서 **한 자리에서 끈다.**  돔 경로를 일부러 시험하는 모듈은
    `pytestmark = pytest.mark.dome_redis` 로 빠져나간다 (그쪽은 가짜 서버를
    세운다).
    """
    if 'dome_redis' in request.keywords:
        yield
        return
    from ics_archon import _simpath      # `ics_sim` 을 sys.path 에 얹는다
    _simpath.ensure()
    from ics_sim import domeaz
    saved = domeaz.DomeRedis.enabled
    domeaz.DomeRedis.enabled = property(lambda self: False)
    try:
        yield
    finally:
        domeaz.DomeRedis.enabled = saved


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
    config.addinivalue_line(
        'markers',
        'dome_redis: 돔 redis 경로를 일부러 시험한다 -- `no_real_redis` 가드를 '
        '빠져나간다.  ⛔ 표식을 붙인 모듈은 **가짜 서버를 직접 세워야** 한다 '
        '(실서버 포트를 쓰면 기계마다 결과가 달라진다)')

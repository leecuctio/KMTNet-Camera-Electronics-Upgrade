#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""실기 두 앱의 콘솔 도움말이 자기 명령표와 어긋나지 않는가.

⭐ **이 파일이 있는 이유**: 2026-09-07 운영자 지적 -- *"콘솔 도움말이 낡았어.
신설 14개가 하나도 없고 기반 명령 `ABORT`·`STOP` 도 빠져 있어."*  손으로 한 번
고치면 **또 낡으므로**, 도움말을 절 목록으로 두고 `Dispatcher` 의 `cmd_*` 와
양방향으로 대조한다.  ⛔ 명령을 새로 넣고 `console_help()` 를 안 고치면 여기가
빨개진다.

`ics_sim` 쪽 기반 대조·`>NODE` 발신 시험은 `ics_sim/tests/test_console.py` 다.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ics_archon import _simpath  # noqa: E402,F401

from ics_sim import console  # noqa: E402

from ics_archon.app import IcsArchon, IcsDispatcher  # noqa: E402
from icg_archon.app import IcgArchon  # noqa: E402
from icg_archon.commands import IcgDispatcher  # noqa: E402

#: 콘솔 자체의 낱말 -- 명령표에 짝이 없는 것이 정상이다.
CONSOLE_WORDS = frozenset({'help', '?', 'quit', 'exit'})


def _check(sections, dispatcher_cls) -> None:  # noqa: ANN001
    listed = console.command_names(sections) - CONSOLE_WORDS
    real = console.dispatcher_commands(dispatcher_cls)
    dead = listed - real
    assert not dead, '도움말에 있는데 명령표에 없다: %s' % sorted(dead)
    missing = real - listed
    assert not missing, '명령표에 있는데 도움말에 없다: %s' % sorted(missing)


# `console_help()` 는 설정도 소켓도 안 만지는 순수 표라, 앱을 띄우지 않고
# **바운드 안 된 메서드**로 부른다 -- 실기 백엔드를 세우지 않으려는 것이다.
ICS_HELP = IcsArchon.console_help(None)
ICG_HELP = IcgArchon.console_help(None)


def test_ics_help_matches_dispatcher():
    _check(ICS_HELP, IcsDispatcher)


def test_icg_help_matches_dispatcher():
    _check(ICG_HELP, IcgDispatcher)


@pytest.mark.parametrize('word', ['ccdflush', 'ccdpowon', 'ccdpowoff',
                                  'archon', 'hk', 'hkdata'])
def test_ics_ops_commands_are_documented(word):
    """운영자 명령 넷 + HK 둘 -- 회귀 가드."""
    assert word in console.command_names(ICS_HELP)


@pytest.mark.parametrize('word', ['guideexp', 'expenable', 'radionode',
                                  'vacgauge', 'htrset', 'htrforce',
                                  'htrramp', 'htrpid', 'ccdflush',
                                  'ccdpowon', 'ccdpowoff', 'archon',
                                  'hk', 'hkdata'])
def test_icg_new_commands_are_documented(word):
    """⭐ 운영자가 *"신설 14개가 하나도 없다"* 고 한 그 열넷."""
    assert word in console.command_names(ICG_HELP)


@pytest.mark.parametrize('sections', [ICS_HELP, ICG_HELP])
def test_base_commands_survive_in_both(sections):
    """기반 명령이 앱 도움말에서도 살아 있다 (`extend_help` 가 꼬리만 민다)."""
    listed = console.command_names(sections)
    for word in ('go', 'stop', 'abort', 'status', 'expnum'):
        assert word in listed


@pytest.mark.parametrize('sections', [ICS_HELP, ICG_HELP])
def test_help_renders(sections):
    text = console.render_help(sections)
    assert '>NODE 메시지' in text
    for _title, entries in sections:
        for syntax, _desc in entries:
            assert syntax in text

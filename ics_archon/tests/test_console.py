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


@pytest.mark.parametrize('word', ['guiexp', 'expenable', 'radionode',
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


# ---------------------------------------------------------------------------
# `[logging] verbose` -- 화면만 간결, **파일은 언제나 전부** (2026-09-11)
# ---------------------------------------------------------------------------

def _fmt(record, *, with_detail):  # noqa: ANN001, ANN202
    """`_TailModule` 로 한 줄을 만든다 (화면/파일 두 서식을 흉내낸다)."""
    from ics_sim.__main__ import LOG_DATEFMT, LOG_FORMAT, _TailModule

    return _TailModule(LOG_FORMAT, datefmt=LOG_DATEFMT,
                       with_detail=with_detail).format(record)


def _record(msg, level=None, **extra):  # noqa: ANN001, ANN202
    import logging

    rec = logging.LogRecord('ics_sim.test', level or logging.INFO,
                            __file__, 1, msg, (), None)
    for key, val in extra.items():
        setattr(rec, key, val)
    return rec


def test_essential_filter_keeps_everything_unmarked():
    """⭐ **기본은 보인다** -- 표시를 빠뜨려도 정보가 사라지면 안 된다."""
    from ics_sim.__main__ import EssentialOnly

    keep = EssentialOnly()
    assert keep.filter(_record('anything')) is True
    assert keep.filter(_record('x', essential=True)) is True
    assert keep.filter(_record('x', essential=False)) is False


def test_wire_chatter_is_classified_by_command_word():
    """자동 왕복만 잡음이다 -- **명령과 그 응답은 아니다.**

    ⛔ 명령이 잡음으로 분류되면 ABC/OBSAgent 가 무엇을 시켰는지가 화면에서
    사라진다.
    """
    from ics_sim.transport import essential_wire, wire_command

    # 자동 왕복 -- 화면에서 뺀다.
    assert wire_command('ICG>TC AUXSTATUS') == 'AUXSTATUS'
    assert not essential_wire('ICG>TC AUXSTATUS')
    assert not essential_wire('TC>ICG DONE: TCSSTATUS TCSQDATE=2026-09-10T18:19:20')
    assert not essential_wire('ICG>AL PING')
    assert not essential_wire('XIS>ICG PONG')

    # 명령·상태·응답 -- 남는다.
    assert wire_command('ICG>ICG STATUS: GO PCTREAD=5') == 'GO'
    assert essential_wire('ICG>ICG STATUS: GO PCTREAD=5')
    assert essential_wire('ICG>ICG STATUS: EXPSTATUS=INTEGRATING')
    assert essential_wire('abc>ICG EXEC: go 10')
    assert essential_wire('ICG>abc DONE: GO EXPSTATUS=IDLE')
    # 깨진 줄에도 안 죽는다.
    assert wire_command('') == ''
    assert essential_wire('쓰레기')


def test_detail_is_dropped_only_on_the_concise_screen():
    """⭐ 같은 기록 하나가 **화면에서는 짧고 파일에서는 온전하다.**"""
    rec = _record('fetch frame 12: 8.3 MiB in 0.1s',
                  detail='buf 3, base 0xE0000000, lock=True')
    assert 'base 0xE0000000' not in _fmt(rec, with_detail=False)
    assert 'fetch frame 12' in _fmt(rec, with_detail=False)
    assert 'base 0xE0000000' in _fmt(rec, with_detail=True)


def test_logging_verbose_reads_the_ini_vocabulary(tmp_path):
    """`on/true/enable/1` 과 `off/false/disable/0` 을 같이 받는다."""
    from ics_sim import config as sim_config

    for word, want in (('off', False), ('false', False), ('0', False),
                       ('disable', False), ('on', True), ('enable', True)):
        path = tmp_path / ('v_%s.ini' % word)
        path.write_text('[logging]\nverbose = %s\n' % word, encoding='utf-8')
        cfg = sim_config.load(str(path))
        assert cfg.logging.verbose is want, word
    # 안 적으면 켜진 것이다 -- 조용해지는 쪽이 기본이면 안 된다.
    path = tmp_path / 'v_none.ini'
    path.write_text('[logging]\nlevel = info\n', encoding='utf-8')
    assert sim_config.load(str(path)).logging.verbose is True

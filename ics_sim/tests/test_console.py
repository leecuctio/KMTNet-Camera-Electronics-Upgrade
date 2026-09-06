#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""콘솔 -- 도움말이 명령표와 어긋나지 않는가 · `>NODE` 가 와이어로 나가는가.

⭐ **이 파일이 있는 이유**: 2026-09-07 에 운영자가 *"콘솔 도움말이 낡았어"* 라고
짚었다 -- 신설 14개가 하나도 없고 기반 명령 `ABORT`·`STOP` 도 빠져 있었다.
도움말을 손으로 고치는 것만으로는 **또 낡는다**.  그래서 도움말을 표(절 목록)로
두고 여기서 `Dispatcher` 의 `cmd_*` 와 **양방향**으로 대조한다.

같은 날 두 번째 결함: `>NODE 명령` 이 설명과 달리 **와이어로 안 나갔다** --
프로세스 안에서 `dispatch.handle()` 을 부를 뿐이라 남의 노드는 *"담당하는 노드가
아닙니다"* 로 막혔고, `icg_first_run` 3단계가 시키는 `ICG>XIS HOSTS` 를 **보낼
수단이 아예 없었다**.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ics_sim import console  # noqa: E402
from ics_sim.app import IcsSim  # noqa: E402
from ics_sim.commands import Dispatcher  # noqa: E402

from conftest import make_config  # noqa: E402


#: 콘솔 자체의 낱말 -- `Dispatcher` 에 짝이 없는 것이 정상이다.
CONSOLE_WORDS = frozenset({'help', '?', 'quit', 'exit'})


def check_help_matches(sections, dispatcher_cls) -> None:  # noqa: ANN001
    """도움말 <-> 명령표 양방향 대조 (다른 앱의 시험도 이것을 부른다)."""
    listed = console.command_names(sections) - CONSOLE_WORDS
    real = console.dispatcher_commands(dispatcher_cls)

    dead = listed - real
    assert not dead, ('도움말에 있는데 명령표에 없다: %s' % sorted(dead))
    missing = real - listed
    assert not missing, ('명령표에 있는데 도움말에 없다: %s' % sorted(missing))


# -- 도움말 ---------------------------------------------------------------

def test_base_help_matches_dispatcher():
    """기반 도움말이 `Dispatcher` 를 빠짐없이 싣는다."""
    check_help_matches(console.BASE_HELP, Dispatcher)


def test_help_carries_stop_and_abort():
    """⛔ 종전 도움말에 없던 둘 -- 회귀 가드."""
    listed = console.command_names(console.BASE_HELP)
    assert 'stop' in listed and 'abort' in listed


def test_extend_help_keeps_console_words_last():
    """앱 절은 `help`/`quit` **앞**에 끼워진다."""
    extra = ('시험', (('foo', '설명'),))
    got = console.extend_help(extra)
    assert got[-len(console.CONSOLE_TAIL):] == console.CONSOLE_TAIL
    assert extra in got
    # 기반 절이 앞에 그대로 산다
    assert got[:len(console.BASE_HELP_BODY)] == console.BASE_HELP_BODY


def test_render_help_has_every_entry():
    text = console.render_help(console.BASE_HELP)
    for _title, entries in console.BASE_HELP:
        for syntax, _desc in entries:
            assert syntax in text


def test_command_names_skips_shorthand_and_splits_alternatives():
    names = console.command_names(console.BASE_HELP)
    assert '>node' not in names and '>xis' not in names
    # `object|dark|bias|flat|sky|domeflat` 가 여섯으로 갈린다
    for word in ('object', 'dark', 'bias', 'flat', 'sky', 'domeflat'):
        assert word in names


# -- `>NODE` 원격 발신 -----------------------------------------------------

class _FakeTransport:
    def __init__(self, route) -> None:  # noqa: ANN001
        self._route = route
        self.sent: list[tuple[bytes, str]] = []

    def route_for(self, dest: str):  # noqa: ANN201
        return self._route

    def send(self, payload: bytes, dest: str) -> None:
        self.sent.append((payload, dest))


def _console(route=('127.0.0.1', 6660), **over):  # noqa: ANN001, ANN201
    app = IcsSim(make_config(**over))
    app.transport = _FakeTransport(route)
    return console.Console(app), app


def test_remote_goes_to_the_wire():
    """`>XIS HOSTS` -> `ICS>XIS HOSTS` 가 발신 큐로 간다."""
    con, _app = _console()
    line = con.send_remote('XIS', 'HOSTS')
    assert line == 'ICS>XIS HOSTS'
    assert con.app.transport.sent[0][1] == 'XIS'


def test_remote_keeps_the_operator_wording():
    """⭐ 친 문면 그대로 -- `EXEC:` 를 우리가 붙이지 않는다."""
    con, _app = _console()
    assert con.send_remote('XIS', 'EXEC: REMOVE G.IC') == 'ICS>XIS EXEC: REMOVE G.IC'
    assert con.send_remote('TC', 'status') == 'ICS>TC status'


def test_feed_routes_foreign_node_to_the_wire():
    """`>TC status` 가 `dispatch` 가 아니라 와이어로."""
    con, app = _console()
    called = []
    app.dispatch.handle = lambda msg, target: called.append(msg)  # noqa: ARG005
    con.feed('>TC status')
    assert not called
    assert con.app.transport.sent


def test_feed_keeps_our_own_nodes_in_process():
    """우리가 받는 노드(`K.IC`)는 종전대로 프로세스 안에서."""
    con, app = _console()
    called = []
    app.dispatch.handle = lambda msg, target: called.append(msg)  # noqa: ARG005
    con.feed('>K.IC status')
    assert len(called) == 1
    assert called[0].mtype == 'EXEC'
    assert not con.app.transport.sent


def test_remote_refuses_non_ascii():
    """⛔ 와이어는 ASCII 다 (규약 7-1) -- 한글은 보내지 않는다."""
    con, _app = _console()
    assert con.send_remote('TC', '상태') == ''
    assert not con.app.transport.sent


def test_remote_reports_missing_route():
    """direct-reply 인데 주소를 못 배웠으면 **버려지는 것을 알린다**."""
    con, _app = _console()
    con.app.transport = _FakeTransport(None)
    assert con.send_remote('TC', 'status') == ''
    assert not con.app.transport.sent


def test_remote_needs_a_body():
    con, _app = _console()
    assert con.send_remote('XIS', '') == ''
    assert not con.app.transport.sent


def test_bare_gt_is_rejected():
    con, _app = _console()
    con.feed('>')
    assert not con.app.transport.sent


def test_render_aligns_by_terminal_cells():
    """⛔ 한글은 두 칸이다 -- `len()` 으로 맞추면 설명 열이 밀린다."""
    assert console._cells('>NODE 메시지') == 6 + 3 * 2
    sections = (('시험', (('abc', '설명 A'), ('한글 둘', '설명 B'))),)
    a, b = console.render_help(sections).splitlines()[3:5]
    # ⚠️ 문자 인덱스로 견주면 안 된다 -- 그 둘은 **다른 것이 정상**이다.
    # 맞아야 하는 것은 앞부분이 차지하는 **칸 수**다.
    assert (console._cells(a[:a.index('설명 A')])
            == console._cells(b[:b.index('설명 B')]))
    assert a.index('설명 A') != b.index('설명 B')


def test_remote_section_comes_after_app_sections():
    """앱 절은 기반 명령 **바로 뒤**, 축약형 절 **앞**."""
    got = console.extend_help(('시험', (('foo', '설명'),)))
    titles = [t for t, _e in got]
    assert titles.index('시험') < titles.index('다른 노드로 보내기')

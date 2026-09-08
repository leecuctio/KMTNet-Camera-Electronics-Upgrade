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

import asyncio
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


def test_the_help_wording_for_stop_matches_the_norm():
    """⛔ **도움말 대사가 규범과 정반대였다** (2026-09-08 발견, 벤치 콘솔 실측).

    `stop` 이 *"적분을 끊고 readout·저장은 정상 수행"* 이라고 적혀 있었다 --
    2026-09-05(`93bfb08`)에 뒤집히기 **전**의 뜻이다.  정본은
    `Sequencer.stop_integration()`: **적분을 끊지 않는다.**

    ⭐ **막으라고 세운 장치가 안 막았다** -- `check_help_matches()` 는 도움말과
    `cmd_*` 를 양방향 대조하지만 **명령 이름만** 본다.  그래서 *"명령을 넣고
    도움말을 안 고치면 빨개진다"* 는 보장은 사는데, *"거동을 바꾸고 대사를 안
    고치면"* 은 안 잡혔다.  이 시험이 그 틈을 메운다.

    ⚠️ 운영자가 **콘솔에서 직접 읽는 문장**이라 조용한 오도가 비싸다 --
    이대로면 `stop` 을 `abort` 처럼 쓴다.
    """
    text = console.render_help(console.BASE_HELP)

    # ⛔ 뒤집히기 전의 뜻이 어디에도 남으면 안 된다.
    assert '적분을 끊고' not in text, text

    stop = _entry(console.BASE_HELP, 'stop')
    assert '저장' in stop and '다음' in stop, stop      # 마치고 · 다음을 안 건다

    abort = _entry(console.BASE_HELP, 'abort')
    assert '저장도 안 한다' in abort, abort              # 이쪽은 종전대로 맞다
    assert stop != abort, '둘이 같은 말이면 갈림이 사라진다'


def _entry(sections, name: str) -> str:  # noqa: ANN001
    """도움말 표에서 그 명령의 **대사**를 꺼낸다."""
    for _title, entries in sections:
        for word, said in entries:
            if word.split()[0] == name:
                return said
    raise AssertionError('%r 가 도움말에 없다' % name)


# -- 입력 고리 (`Console.run`) ---------------------------------------------
#
# ⭐ **이 절이 생긴 이유**: 2026-09-08 에 입력을 `sys.stdin.readline()` 에서
# `input(prompt)` 로 바꿨다 (프롬프트·화살표 이력, 운영자 요청).  ⛔ 두 함수는
# **빈 줄의 뜻이 다르다** -- `readline()` 의 `''` 는 EOF 지만 `input()` 은 그냥
# Enter 에도 `''` 를 준다.  그대로 뒀으면 **Enter 한 번에 콘솔이 죽는다.**


class _Loop(console.Console):
    """`run()` 만 도는 최소 콘솔 -- 앱도 라우터도 필요 없다."""

    def __init__(self) -> None:
        import types
        self.app = types.SimpleNamespace(
            cfg=types.SimpleNamespace(
                node=types.SimpleNamespace(ics_id='ICS')))
        self._stop = asyncio.Event()
        self.seen: list[str] = []

    def help_text(self) -> str:
        return ''

    # ⛔ 시험이 `$HOME` 에 이력 파일을 만들면 안 된다.
    def _load_history(self) -> None:
        pass

    def _save_history(self) -> None:
        pass

    def feed(self, line: str) -> None:
        self.seen.append(line)
        if line == 'quit':
            self.stop()


def _drive(monkeypatch, lines, tty):  # noqa: ANN001, ANN202
    """`lines` 를 콘솔에 먹이고 (본 줄, 프롬프트들) 을 돌려준다."""
    left = list(lines)
    prompts = []

    def _input(prompt=''):  # noqa: ANN001, ANN202
        prompts.append(prompt)
        if not left:
            raise EOFError
        return left.pop(0)

    def _readline():  # noqa: ANN202
        return left.pop(0) if left else ''

    monkeypatch.setattr('builtins.input', _input)
    monkeypatch.setattr(console.sys.stdin, 'isatty', lambda: tty,
                        raising=False)
    monkeypatch.setattr(console.sys.stdin, 'readline', _readline,
                        raising=False)
    con = _Loop()
    asyncio.run(con.run())
    return con.seen, prompts


def test_a_blank_line_does_not_end_the_console(monkeypatch):
    """⛔ **Enter 한 번에 콘솔이 죽으면 안 된다** -- 빈 줄은 EOF 가 아니다.

    `input()` 은 그냥 Enter 에도 `''` 를 준다.  종전 `readline()` 판에서는 `''`
    가 EOF 였으므로, 갈래를 안 갈랐으면 이 시험이 빨개진다.
    """
    seen, prompts = _drive(monkeypatch, ['', 'hk', '', 'quit'], tty=True)
    assert seen == ['', 'hk', '', 'quit'], seen
    assert prompts and all(p == 'ICS% ' for p in prompts), prompts


def test_ctrl_d_ends_the_console(monkeypatch):
    """⭐ TTY 에서 EOF 는 `EOFError`(Ctrl-D) 다 -- 그때는 끝난다."""
    seen, _prompts = _drive(monkeypatch, ['hk'], tty=True)
    assert seen == ['hk'], seen


def test_a_pipe_gets_no_prompt_and_ends_at_eof(monkeypatch):
    """⛔ TTY 가 아니면 **프롬프트를 안 띄우고** 종전 경로를 그대로 탄다.

    파이프로 먹이거나 로그로 흘릴 때 프롬프트가 섞이면 그 자체가 잡음이다.
    거기서는 `''` 가 EOF 다.
    """
    seen, prompts = _drive(monkeypatch, ['hk\n', 'go 1\n'], tty=False)
    assert seen == ['hk', 'go 1'], seen
    assert prompts == [], prompts


def test_the_active_prompt_is_cleared_when_not_waiting(monkeypatch):
    """⭐ 로그 처리기가 보는 `ACTIVE_PROMPT` 는 **기다릴 때만** 차 있어야 한다.

    안 그러면 콘솔이 안 기다리는데도 로그마다 헛 프롬프트가 다시 그려진다.
    """
    _drive(monkeypatch, ['quit'], tty=True)
    assert console.ACTIVE_PROMPT == '', console.ACTIVE_PROMPT


# -- 로그 한 줄의 꼴 -------------------------------------------------------
#
# ⭐ 콘솔 읽기 좋게 하려고 **시각 태그를 `[...]` 로** 감쌌다 (운영자 2026-09-08,
# OBSAgent 관례).  ⛔ 그 태그와 `Warning:`/`Error:` 앞머리는 **서로 걸린다** --
# `_TailModule` 이 **첫 공백**에서 갈라 시각 뒤에 낱말을 끼우므로, 태그 안에
# 공백이 생기면 조용히 어긋난다.  여기서 그 결합을 못박는다.


def _line(level, name, msg):  # noqa: ANN001, ANN202
    import logging

    from ics_sim import __main__ as sim_main
    fmt = sim_main._TailModule(sim_main.LOG_FORMAT,
                               datefmt=sim_main.LOG_DATEFMT)
    rec = logging.LogRecord(name, level, __file__, 1, msg, None, None)
    return fmt.format(rec)


def test_the_time_tag_is_bracketed():
    """⭐ `[2026-09-08T13:10:47.008] 본문` -- OBSAgent 와 같은 꼴."""
    import logging
    import re
    out = _line(logging.INFO, 'ics_sim.transport', 'ICG>XIS PING')
    assert re.match(r'^\[\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}\] ICG>XIS PING$',
                    out), out


def test_a_warning_word_goes_after_the_bracketed_tag():
    """⛔ 앞머리는 **시각 태그 뒤**에 온다 -- 대괄호가 그 가름을 안 깨야 한다."""
    import logging
    import re
    out = _line(logging.WARNING, 'ics_sim.hk', 'HK polling failed')
    assert re.match(r'^\[[^ ]+\] Warning: HK polling failed '
                    r'\(module: ics_sim\.hk\)$', out), out
    err = _line(logging.ERROR, 'icg_archon.cmd', 'nope')
    assert re.match(r'^\[[^ ]+\] Error: nope \(module: icg_archon\.cmd\)$',
                    err), err

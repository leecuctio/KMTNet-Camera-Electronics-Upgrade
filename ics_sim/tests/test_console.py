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
import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ics_sim import console  # noqa: E402
from ics_sim.app import IcsSim  # noqa: E402
from ics_sim.commands import Dispatcher  # noqa: E402

from conftest import make_config  # noqa: E402


#: 콘솔 자체의 낱말 -- `Dispatcher` 에 짝이 없는 것이 정상이다.
CONSOLE_WORDS = frozenset({'help', '?', 'quit', 'exit'})


def check_help_matches(sections, dispatcher_cls) -> None:  # noqa: ANN001
    """도움말 <-> 명령표 양방향 대조 (다른 앱의 시험도 이것을 부른다).

    ⭐ `dispatcher_cls.UNSUPPORTED` 는 **양쪽에서 뺀다** -- 그 명령은 핸들러가
    상속으로 있어도 `handle()` 이 거절하므로 *"이 노드의 명령"* 이 아니다.
    ⛔ 그래서 도움말에 있으면 그것이 오히려 잘못이다 (아래 `dead` 가 잡는다).
    """
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


def test_remote_is_one_line_on_screen_when_the_wire_log_is_on(capsys):  # noqa: ANN001
    """⛔ **한 메시지는 화면에 한 줄** -- 와이어 로그가 켜져 있으면 `transport.send`
    가 이미 그 줄을 냈으므로 콘솔은 **아무것도 안 찍는다** (종전에는 `  >>> …` 를
    또 찍어 두 줄이 됐다)."""
    import logging
    con, _app = _console()
    capsys.readouterr()                           # 조립 중 출력은 버린다
    con.app.cfg.logging.wire = True
    logger = logging.getLogger('ics_sim.transport')
    saved = logger.level
    logger.setLevel(logging.INFO)
    try:
        assert con.send_remote('TC', 'status') == 'ICS>TC status'
    finally:
        logger.setLevel(saved)
    assert capsys.readouterr().out == ''


def test_remote_prints_one_plain_line_when_the_wire_log_is_off(capsys):  # noqa: ANN001
    """와이어 로그가 꺼져 있으면 발신 확인이 화면에 하나도 없으므로 콘솔이 한 줄
    낸다 -- ⛔ 방향 표시(`>>>`) 없이 (운영자 2026-09-08)."""
    con, _app = _console()
    capsys.readouterr()                           # 조립 중 출력은 버린다
    con.app.cfg.logging.wire = False
    assert con.send_remote('TC', 'status') == 'ICS>TC status'
    out = capsys.readouterr().out
    assert out.strip() == 'ICS>TC status', out
    assert '>>>' not in out


class _Screen(logging.Handler):
    """화면 처리기 흉내 -- `EssentialOnly` 필터를 지나 **화면에 나갈** 로그 줄을 모은다."""

    def __init__(self, flt) -> None:  # noqa: ANN001
        super().__init__(logging.INFO)
        self.addFilter(flt)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        self.lines.append(record.getMessage())


@pytest.mark.parametrize('dest, rest, verbose', [
    ('TC', 'TCSSTATUS', False),
    ('TC', 'AUXSTATUS', False),
    ('XIS', 'PING', False),
    ('TC', 'status', False),                 # 함축 줄 -- 와이어 로그가 한 줄 낸다
    ('TC', 'TCSSTATUS', True),               # 자세한 화면 -- 와이어 로그가 한 줄 낸다
])
def test_remote_is_one_line_on_screen_whatever_the_verbosity(  # noqa: ANN001
        monkeypatch, capsys, dest, rest, verbose):
    """⛔ **간결한 화면에서 잡음 줄을 보내도 화면에 한 줄은 남는다** (2026-09-23 발견).

    출하값 `[behavior] verbose = off` + `[logging] wire = true` 에서 콘솔의
    `>TC TCSSTATUS`·`>TC AUXSTATUS`·`>XIS PING` 이 화면에 **아무것도 안 남겼다** --
    와이어 로그 줄은 잡음(`CHATTER_WORDS`)이라 화면 필터가 막고, 콘솔은 *"와이어
    로그가 이미 찍었다"* 고 보고 제 줄을 건너뛰었다.
    ⭐ 여기서는 운영자가 친 꼴 그대로(`>TC TCSSTATUS`) **`Console.feed`** 에 넣고,
    **진짜 `UdpEndpoint.send`** 가 로그를 낸다.  화면 필터(`EssentialOnly`)를 지난
    로그 줄과 콘솔의 stdout 을 **합쳐** 정확히 한 줄인지 본다.
    """
    from ics_sim import __main__ as sim_main

    app = IcsSim(make_config(transport__xis_host='127.0.0.1'))
    app.cfg.logging.wire = True
    con = console.Console(app)
    flt = sim_main.EssentialOnly()
    flt.enabled = not verbose
    monkeypatch.setattr(sim_main, '_SCREEN_FILTER', flt)
    screen = _Screen(flt)
    logger = logging.getLogger('ics_sim.transport')
    saved = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(screen)
    capsys.readouterr()                           # 조립 중 출력은 버린다
    try:
        con.feed('>%s %s' % (dest, rest))
    finally:
        logger.removeHandler(screen)
        logger.setLevel(saved)
    want = 'ICS>%s %s' % (dest, rest)
    assert app.transport.sent_log == [want]
    printed = [s.strip() for s in capsys.readouterr().out.splitlines() if s.strip()]
    assert len(screen.lines) + len(printed) == 1, (screen.lines, printed)
    assert (screen.lines + printed) == [want], (screen.lines, printed)


def test_python_dash_m_keeps_one_copy_of_the_main_module():
    """⛔ `python -m ics_sim` 에서 `ics_sim.__main__` 이 **한 벌만** 있어야 한다 (2026-09-23).

    `-m` 으로 띄우면 `__main__.py` 는 `__main__` 이라는 이름으로 돈다.  그때
    `from .__main__ import verbose_state`(`commands.cmd_verbose` ·
    `Console._wire_line_shown`)가 그 파일을 **새로 한 벌 더** 읽으면, 그 사본의
    `_SCREEN_FILTER` 는 빈 값이라 `VERBOSE OFF` 가 아무것도 안 바꾸고 콘솔은 늘
    *"자세한 화면"* 으로 본다.  ⭐ 돌고 있는 모듈이 그 이름으로도 올라가 있는지 본다.
    """
    import subprocess
    code = (
        'import contextlib, io, runpy, sys\n'
        "sys.argv = ['ics_sim', '--help']\n"
        'try:\n'
        '    with contextlib.redirect_stdout(io.StringIO()):\n'
        "        runpy.run_module('ics_sim', run_name='__main__', alter_sys=True)\n"
        'except SystemExit:\n'
        '    pass\n'
        "print(sys.modules['ics_sim.__main__'].__name__)\n")
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    run = subprocess.run([sys.executable, '-c', code], cwd=root,
                         capture_output=True, text=True, timeout=120)
    assert run.stdout.strip() == '__main__', (run.stdout, run.stderr)


def test_the_old_logging_verbose_key_is_warned_not_read(tmp_path, caplog):  # noqa: ANN001
    """⚠️ 옛 자리(`[logging] verbose`)의 값은 **안 읽고, 불러 올 때 한 번 알린다**.

    2026-09-11 에 `[behavior] verbose` 로 옮겼다.  ⛔ 조용히 지나가면 `off` 로
    적어 둔 운영자가 켜진 화면을 본다 -- `[node]` 의 옛 키(`site`/`telid`/
    `site_from_ip`)와 같은 대접이다 (`config.load`).
    """
    from ics_sim import config

    def load(text):  # noqa: ANN001, ANN202
        path = tmp_path / 'v.ini'
        path.write_text(text, encoding='utf-8')
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger='ics_sim.config'):
            cfg = config.load(str(path))
        hits = [r for r in caplog.records
                if r.name == 'ics_sim.config'
                and '[logging] verbose' in r.getMessage()]
        return cfg, hits

    cfg, hits = load('[logging]\nverbose = off\n')
    assert cfg.behavior.verbose is True          # 옛 자리의 `off` 는 안 먹는다
    assert len(hits) == 1, [r.getMessage() for r in caplog.records]
    assert '[behavior] verbose' in hits[0].getMessage()
    assert '2026-09-11' in hits[0].detail
    # 새 자리에만 적으면 조용하다.
    cfg, hits = load('[behavior]\nverbose = off\n\n[logging]\nwire = true\n')
    assert cfg.behavior.verbose is False and not hits


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


def _drive(monkeypatch, lines, tty, cls=None):  # noqa: ANN001, ANN202
    """`lines` 를 콘솔에 먹이고 (본 줄, 프롬프트들) 을 돌려준다.

    `lines` 에 **예외 객체**가 오면 그 차례에 입력 쪽이 그것을 던진다 -- 입력
    실패 갈래(`input failed: …`)를 흉내 낸다.  `cls` 는 `_Loop` 의 하위 클래스.
    """
    left = list(lines)
    prompts = []

    def _next():  # noqa: ANN202
        item = left.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def _input(prompt=''):  # noqa: ANN001, ANN202
        prompts.append(prompt)
        if not left:
            raise EOFError
        return _next()

    def _readline():  # noqa: ANN202
        return _next() if left else ''

    monkeypatch.setattr('builtins.input', _input)
    monkeypatch.setattr(console.sys.stdin, 'isatty', lambda: tty,
                        raising=False)
    monkeypatch.setattr(console.sys.stdin, 'readline', _readline,
                        raising=False)
    con = (cls or _Loop)()
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


# ⭐ **왜 끝났는지 말한다** (벤치 2026-09-15: 콘솔이 *"아무 메시지 없이"* 끝나
# 프로그램이 내려갔다 -- imagetyp 무언 종료).  원인을 좇는 단서가 종료 사유 한 줄
# `console closed (…)` 뿐이라, 그 줄의 사유 넷과 "명령 하나의 예외로 안 죽는다" 를
# 여기서 못박는다.  ⚠️ 이 문면은 인수인계 문서가 운영자에게 보라고 인용한다.

class _Boom(_Loop):
    """`boom` 에서 예외를 던지는 콘솔 -- 명령 하나의 실패를 흉내 낸다."""

    def feed(self, line: str) -> None:
        if line == 'boom':
            self.seen.append(line)
            raise RuntimeError('boom')
        super().feed(line)


def _closed_reasons(caplog):  # noqa: ANN001, ANN202
    return [r.getMessage() for r in caplog.records
            if r.name == 'ics_sim.console'
            and r.getMessage().startswith('console closed (')]


def test_one_failing_command_does_not_end_the_console(monkeypatch, caplog):  # noqa: ANN001
    """⛔ 명령 하나가 던진 예외로 콘솔(과 프로그램)이 죽지 않는다 -- 원문과 스택을
    ERROR 로 남기고 다음 줄을 받는다."""
    import logging
    with caplog.at_level(logging.INFO, logger='ics_sim.console'):
        seen, _prompts = _drive(monkeypatch, ['boom', 'hk', 'quit'], tty=True,
                                cls=_Boom)
    assert seen == ['boom', 'hk', 'quit'], seen
    failed = [r for r in caplog.records
              if r.name == 'ics_sim.console' and r.levelno == logging.ERROR
              and "console command failed -- 'boom'" in r.getMessage()]
    assert len(failed) == 1, [r.getMessage() for r in caplog.records]
    assert failed[0].exc_info, '스택이 남아야 원인을 좇는다'
    assert _closed_reasons(caplog) == [
        'console closed (quit) -- the program shuts down']


@pytest.mark.parametrize('lines, tty, why', [
    (['hk'], True, 'EOF (Ctrl-D)'),
    (['hk\n'], False, 'stdin EOF'),
    (['quit'], True, 'quit'),
    (['exit'], True, 'quit'),
    (['QUIT'], True, 'quit'),
    (['EXIT\n'], False, 'quit'),
    ([RuntimeError('lost sys.stdin')], True,
     'input failed: RuntimeError: lost sys.stdin'),
    ([ValueError('I/O operation on closed file')], False,
     'input failed: ValueError: I/O operation on closed file'),
    ([OSError(5, 'Input/output error')], True,
     'input failed: OSError: [Errno 5] Input/output error'),
    ([OSError(9, 'Bad file descriptor')], False,
     'input failed: OSError: [Errno 9] Bad file descriptor'),
])
def test_the_console_says_why_it_closed(monkeypatch, caplog, lines, tty, why):  # noqa: ANN001
    """종료 사유 한 줄 -- 종료 명령 · EOF(TTY 는 Ctrl-D, 파이프는 빈 읽기) · 입력 예외.

    ⭐ 종료 낱말은 **진짜 `Console.feed`** 가 처리한다 -- 대소문자를 안 가리는
    판정(`low in ('quit', 'exit')`)과 `stop()` 까지가 시험 대상이다.
    """
    class _Exit(_Loop):
        def feed(self, line: str) -> None:
            self.seen.append(line)
            if line.lower() in ('quit', 'exit'):
                console.Console.feed(self, line)

    with caplog.at_level(logging.INFO, logger='ics_sim.console'):
        _drive(monkeypatch, lines, tty=tty, cls=_Exit)
    assert _closed_reasons(caplog) == [
        'console closed (%s) -- the program shuts down' % why], (
        [r.getMessage() for r in caplog.records])


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

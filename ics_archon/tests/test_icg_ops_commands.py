#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CCD 조작 명령 넷 -- `CCDFLUSH` · `CCDPOWON`/`CCDPOWOFF` · `ARCHON` (운영자 지시 2026-09-05).

`test_icg_app.py` 와 같은 하네스 -- 소켓 없이 `transport.feed()` 로 명령을 주입하고
발신 로그를 대조한다.  주 경로는 Sim 백엔드(컨트롤러 없음)이고, 끝의 시험 하나가
실기 백엔드 + 가짜 컨트롤러 경로를 본다 (`test_icg_backend.py` 의 하네스).

여기는 **명령 층**만 본다 -- `flush_now`/`power_on`/`raw_command` 의 왕복 자체는
컨트롤러·백엔드 시험의 몫이다.
"""

from __future__ import annotations

import asyncio
import logging

import ics_archon  # noqa: F401

from ics_sim import emitter  # noqa: E402
from ics_sim.impv2 import MAX_LEN  # noqa: E402

from ics_archon.archon.protocol import ArchonError  # noqa: E402

from icg_archon import commands as icg_commands  # noqa: E402
from icg_archon.app import IcgArchon  # noqa: E402
from icg_archon.backend import GuideBackendError, SimGuideBackend  # noqa: E402

from test_icg_app import make_cfgs  # noqa: E402  -- 같은 하네스

WORDS = ('CCDFLUSH', 'CCDPOWON', 'CCDPOWOFF', 'ARCHON')


def _drive(tmp_path, script, before=None, gap=0.02, settle=0.1):  # noqa: ANN001, ANN202
    """대본을 먹이고 (app, 발신로그) 를 돌려준다 (`test_icg_app._drive_lines` 와 같다)."""
    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        if before:
            before(app)
        try:
            for line in script:
                app.transport.feed(line)
                await asyncio.sleep(gap)
            await app.seq.wait()
            await asyncio.sleep(settle)     # 늦은 DONE 의 flush
        finally:
            await app.stop()
        return app, [str(s) for s in app.transport.sent_log]
    return asyncio.run(run())


def _about(sent, word):  # noqa: ANN001, ANN202
    return [s for s in sent if word in s]


# ---------------------------------------------------------------------------
# Sim 백엔드 -- 정상 응답
# ---------------------------------------------------------------------------

def test_ccdflush_answers_flushed_1_on_the_sim_backend(tmp_path):  # noqa: ANN001
    """(a) `CCDFLUSH` -> `DONE: CCDFLUSH Flushed=1` -- 컨트롤러 없이도 돈다.

    히터·게이지는 `_ctrl()` 로 Sim 에서 거부되지만 이 넷은 **백엔드 표면**을
    부르므로 Sim 에서 `DONE` 이어야 한다 (원시 함수가 실기·Sim 둘 다 있다).
    """
    app, sent = _drive(tmp_path, ['abc>ICG CCDFLUSH'])
    said = _about(sent, 'CCDFLUSH')
    assert any(s.endswith('DONE: CCDFLUSH Flushed=1') for s in said), said
    assert not any('ERROR' in s for s in said), said
    assert app.emit.violations == [], app.emit.violations


def test_ccdpowon_and_ccdpowoff_answer_power_on_off(tmp_path):  # noqa: ANN001
    """(b) `CCDPOWON`/`CCDPOWOFF` -> `Power=ON`/`Power=OFF`."""
    app, sent = _drive(tmp_path, ['abc>ICG CCDPOWON', 'abc>ICG CCDPOWOFF'])
    assert any(s.endswith('DONE: CCDPOWON Power=ON') for s in sent), sent
    assert any(s.endswith('DONE: CCDPOWOFF Power=OFF') for s in sent), sent
    assert app.emit.violations == [], app.emit.violations


def test_archon_bypass_returns_the_reply_verbatim(tmp_path):  # noqa: ANN001
    """(c) `ARCHON STATUS` -> `DONE: ARCHON SIM (no controller): STATUS`.

    ⭐ 원문을 **대문자화하지 않는다** -- `WCONFIG` 본문(타이밍 스크립트 줄)은
    대소문자가 뜻이다.  공백만 접는다 (`controller.raw_command` 와 같은 규칙).
    """
    app, sent = _drive(tmp_path, ['abc>ICG ARCHON STATUS',
                                  'abc>ICG ARCHON   rconfig0001  '])
    said = _about(sent, 'DONE: ARCHON')
    assert any(s.endswith('DONE: ARCHON SIM (no controller): STATUS') for s in said), said
    assert any(s.endswith('DONE: ARCHON SIM (no controller): rconfig0001') for s in said), said
    assert app.emit.violations == [], app.emit.violations


def test_archon_without_a_command_is_a_usage_error(tmp_path):  # noqa: ANN001
    """(d) 빈 인자 -> `ERROR: ARCHON Usage: ARCHON <command>` (왕복 없음)."""
    _app, sent = _drive(tmp_path, ['abc>ICG ARCHON', 'abc>ICG ARCHON   '])
    said = _about(sent, 'ARCHON')
    assert len(said) == 2, said
    assert all('ERROR' in s and 'ARCHON <command>' in s for s in said), said


def test_the_argumentless_commands_refuse_extra_arguments(tmp_path):  # noqa: ANN001
    """⛔ 남는 인자를 조용히 버리지 않는다 (`_split` 규칙 -- *"넣었다고 믿는"* 자리 방지)."""
    _app, sent = _drive(tmp_path, ['abc>ICG CCDFLUSH now',
                                   'abc>ICG CCDPOWON 1',
                                   'abc>ICG CCDPOWOFF please'])
    assert sum('Usage:' in s for s in sent) == 3, sent
    assert not any('DONE' in s for s in sent
                   if any(w in s for w in WORDS)), sent


# ---------------------------------------------------------------------------
# 거부 -- 취득 중 · 다른 조작 왕복 중
# ---------------------------------------------------------------------------

def test_all_four_are_refused_during_acquisition(tmp_path):  # noqa: ANN001
    """(e) 취득 중이면 넷 다 `ERROR: … Exposure in progress -- ABORT first`.

    히터·게이지(`_busy_note`: 받되 표시)와 **반대**다 -- 진행 중 노출 위의
    `LOADPARAMS`/`POWEROFF`/원문 `RESETTIMING` 은 그 프레임을 망친다.
    ⚠️ `EXP 30` 이 의도다 (`time_scale=0.02` → 프레임당 0.6 s) -- 짧게 잡으면
    부하에서 취득이 먼저 끝나 `busy` 가 거짓으로 읽힌다 (heater 시험과 같은 주석).
    """
    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        try:
            app.transport.feed('abc>ICG EXP 30')
            await asyncio.sleep(0.02)
            app.transport.feed('abc>ICG GO 2')
            await asyncio.sleep(0.05)
            assert app.seq.busy, '취득이 안 돌고 있다 -- 시험 전제가 깨졌다'
            for line in ('abc>ICG CCDFLUSH', 'abc>ICG CCDPOWON',
                         'abc>ICG CCDPOWOFF', 'abc>ICG ARCHON STATUS'):
                app.transport.feed(line)
                await asyncio.sleep(0.02)
            await app.seq.wait()
            await asyncio.sleep(0.1)
        finally:
            await app.stop()
        return app, [str(s) for s in app.transport.sent_log]

    app, sent = asyncio.run(run())
    for word in WORDS:
        said = _about(sent, word)
        assert any('ERROR' in s and icg_commands.BUSY_REFUSAL in s
                   for s in said), (word, said)
        assert not any('DONE' in s for s in said), (word, said)
    # 거부가 취득을 건드리지 않았다 -- 2장이 그대로 저장됐다.
    assert '\n'.join(sent).count('Wrote LASTFILE=') == 2, sent
    assert app.emit.violations == [], app.emit.violations


def test_go_and_the_other_ops_wait_for_a_power_on_in_flight(tmp_path, monkeypatch):  # noqa: ANN001
    """⭐ `CCDPOWON` 이 왕복 중이면 `GO` 도, 다른 조작도 **거부**한다.

    `POWERON` 은 ack 직후 `powered=True` 가 되고 그 뒤 `poweron_wait`(12 s) 동안
    CCD flush 를 기다리는데, 그 사이의 `GO` 는 `prepare()` 가 전원을 건너뛰어
    flush 가 안 끝난 CCD 를 arm 한다 (`controller.power_on`).  시퀀서 `busy`
    는 이 왕복을 모르므로 디스패처가 따로 든다 (`_op_in_flight`).
    """
    async def slow_power(self, on):  # noqa: ANN001, ANN202, ARG001
        await asyncio.sleep(0.3)

    monkeypatch.setattr(SimGuideBackend, 'power_ccd', slow_power)
    app, sent = _drive(tmp_path, ['abc>ICG CCDPOWON', 'abc>ICG GUIDEEXP 1',
                                  'abc>ICG GO 1', 'abc>ICG CCDFLUSH',
                                  'abc>ICG ARCHON STATUS'], settle=0.5)
    text = '\n'.join(sent)
    assert 'ERROR: GO Busy with CCDPOWON' in text, sent
    assert 'ERROR: CCDFLUSH Busy with CCDPOWON' in text, sent
    assert 'ERROR: ARCHON Busy with CCDPOWON' in text, sent
    assert any(s.endswith('DONE: CCDPOWON Power=ON') for s in sent), sent
    assert 'Wrote LASTFILE=' not in text, 'GO 가 전원 왕복 중에 시작됐다'
    assert app.emit.violations == [], app.emit.violations


def test_a_failed_flush_is_reported_and_releases_the_gate(tmp_path, monkeypatch):  # noqa: ANN001
    """실패는 `ERROR: CCDFLUSH Failed: <이유>` -- 그리고 그 뒤 `GO` 가 다시 열린다.

    (`_op_in_flight` 가 `finally` 에서 풀리지 않으면 실패 한 번이 `GO` 를 영영 막는다.)
    """
    async def boom(self):  # noqa: ANN001, ANN202
        raise GuideBackendError('CCD flush failed: guide ACF has no FirstFlush')

    monkeypatch.setattr(SimGuideBackend, 'flush_ccd', boom)
    _app, sent = _drive(tmp_path, ['abc>ICG CCDFLUSH', 'abc>ICG GUIDEEXP 1',
                                   'abc>ICG GO 1'])
    assert any('ERROR: CCDFLUSH Failed: CCD flush failed' in s for s in sent), sent
    assert any('Wrote LASTFILE=' in s for s in sent), '실패 뒤 GO 가 막혀 있다'


# ---------------------------------------------------------------------------
# EXPENABLE 잠금과의 관계
# ---------------------------------------------------------------------------

def test_ccdflush_is_allowed_while_locked_and_says_so(tmp_path):  # noqa: ANN001
    """⭐ `EXPENABLE OFF` 여도 flush 는 된다 (노출이 아니다) -- 응답에 `ExpEnable=OFF`.

    `GO` 는 그대로 막힌다 -- 잠금 자체가 풀린 것이 아님을 함께 본다.
    """
    app, sent = _drive(tmp_path, ['abc>ICG EXPENABLE OFF', 'abc>ICG CCDFLUSH',
                                  'abc>ICG GUIDEEXP 1', 'abc>ICG GO 1'])
    assert any(s.endswith('DONE: CCDFLUSH Flushed=1 (ExpEnable=OFF)') for s in sent), sent
    assert any('Exposure is disabled (EXPENABLE OFF)' in s for s in sent), sent
    assert not app.expenable.allowed
    assert app.emit.violations == [], app.emit.violations


# ---------------------------------------------------------------------------
# ARCHON -- 거부·실패 구분 · 긴 응답
# ---------------------------------------------------------------------------

def test_archon_rejection_and_link_failure_are_told_apart(tmp_path, monkeypatch):  # noqa: ANN001
    """`?xx` 거부는 `rejected: <보낸 원문>`, 링크 실패는 `Failed: <이유>`.

    대응이 다르다 (`controller.cmd` 주석) -- 전자는 명령·ACF 를 보고, 후자는
    연결을 본다.  같은 `ERROR` 로 뭉개면 운영자가 어느 쪽을 볼지 모른다.
    """
    async def raw(self, text):  # noqa: ANN001, ANN202
        if text.startswith('BAD'):
            raise ArchonError('?01', cmd=text, reply_error=True)
        if text.startswith('SLOW'):
            raise ArchonError('SLOW reply timed out', cmd=text)
        return 'ok'

    monkeypatch.setattr(SimGuideBackend, 'raw_command', raw)
    app, sent = _drive(tmp_path, ['abc>ICG ARCHON BAD 1', 'abc>ICG ARCHON SLOW',
                                  'abc>ICG ARCHON GOOD'])
    assert any(s.endswith('ERROR: ARCHON rejected: BAD 1') for s in sent), sent
    assert any('ERROR: ARCHON Failed:' in s and 'timed out' in s for s in sent), sent
    assert any(s.endswith('DONE: ARCHON ok') for s in sent), sent
    assert app.emit.violations == [], app.emit.violations


def test_an_empty_archon_reply_is_named_not_blank(tmp_path, monkeypatch):  # noqa: ANN001
    """빈 성공 ack(`WCONFIG`/`LOADPARAMS`/`APPLY*`)는 `DONE: ARCHON` 만 나가면 *됐는지* 가 안 보인다."""
    async def raw(self, text):  # noqa: ANN001, ANN202, ARG001
        return ''

    monkeypatch.setattr(SimGuideBackend, 'raw_command', raw)
    _app, sent = _drive(tmp_path, ['abc>ICG ARCHON LOADPARAMS'])
    assert any(s.endswith('DONE: ARCHON (accepted, empty reply)') for s in sent), sent


def test_a_long_archon_reply_is_clipped_and_logged_in_full(tmp_path, monkeypatch, caplog):  # noqa: ANN001
    """`STATUS` 급(1~2 KB) 응답 -- 한 메시지 2048 을 넘기지 않고 전문은 로그에."""
    long = ' '.join('K%d=%d' % (i, i) for i in range(400))        # ≈ 3.4 KB
    assert len(long) > icg_commands.ARCHON_REPLY_MAX

    async def raw(self, text):  # noqa: ANN001, ANN202, ARG001
        return long

    monkeypatch.setattr(SimGuideBackend, 'raw_command', raw)
    caplog.set_level(logging.INFO, logger='icg_archon.cmd')
    app, sent = _drive(tmp_path, ['abc>ICG ARCHON STATUS'])
    said = _about(sent, 'DONE: ARCHON')
    assert len(said) == 1, sent
    line = said[0]
    assert len(line) <= MAX_LEN, len(line)
    assert ('...(+%d bytes truncated, see log)'
            % (len(long) - icg_commands.ARCHON_REPLY_MAX)) in line, line[-80:]
    assert long[:icg_commands.ARCHON_REPLY_MAX] in line
    assert any(long in r.getMessage() for r in caplog.records), '전문이 로그에 없다'
    assert app.emit.violations == [], app.emit.violations


# ---------------------------------------------------------------------------
# 위생 검사 -- 커맨드워드 등록
# ---------------------------------------------------------------------------

def test_the_words_are_registered_and_an_unregistered_word_is_what_the_check_catches():
    """(f) 넷이 `ICG_COMMANDS` 에 있고, 빠뜨리면 `unknown_cmdword` 로 운다.

    `emitter.validate()` 는 `KNOWN_COMMANDS` 밖의 커맨드워드를 `unknown_cmdword`
    로 적고 `emit.violations` 에 쌓는다 -- 위 `_drive` 시험들의 `violations == []`
    가 그것을 잡는다.  여기서는 우리 응답 문구 하나하나가 **다른 위반도** 안
    내는지(`stacked_cmdword` -- 본문 첫 토큰이 대문자 커맨드워드면 운다) 본다.
    """
    icg_commands.extend_vocabulary()
    assert set(WORDS) <= icg_commands.ICG_COMMANDS
    assert set(WORDS) <= emitter.KNOWN_COMMANDS
    for line, word in (
            ('ICG>abc DONE: CCDFLUSH Flushed=1 (ExpEnable=OFF)', 'CCDFLUSH'),
            ('ICG>abc DONE: CCDPOWON Power=ON', 'CCDPOWON'),
            ('ICG>abc DONE: CCDPOWOFF Power=OFF', 'CCDPOWOFF'),
            ('ICG>abc DONE: ARCHON SIM (no controller): STATUS', 'ARCHON'),
            ('ICG>abc DONE: ARCHON (accepted, empty reply)', 'ARCHON'),
            ('ICG>abc ERROR: ARCHON rejected: STATUS', 'ARCHON'),
            ('ICG>abc ERROR: ARCHON Usage: ARCHON <command>', 'ARCHON'),
            ('ICG>abc ERROR: CCDFLUSH ' + icg_commands.BUSY_REFUSAL, 'CCDFLUSH'),
            ('ICG>abc ERROR: GO Busy with CCDPOWON -- wait for its DONE', 'GO'),
            ('ICG>abc ERROR: CCDFLUSH Usage: CCDFLUSH (no arguments)', 'CCDFLUSH')):
        assert emitter.validate(line, word) == [], (line, emitter.validate(line, word))
    # ⭐ 등록을 빠뜨리면 이렇게 운다.
    assert emitter.validate('ICG>abc DONE: CCDFLUSHX Flushed=1',
                            'CCDFLUSHX') == ['unknown_cmdword']
    # ⚠️ 그리고 이렇게도 운다 -- 본문이 대문자 커맨드워드로 시작하면 (한때 `GO`
    #    거부 문구가 `CCDPOWON in progress …` 였다).
    assert 'stacked_cmdword' in emitter.validate(
        'ICG>abc ERROR: GO CCDPOWON in progress', 'GO')


# ---------------------------------------------------------------------------
# 실기 백엔드 + 가짜 컨트롤러 -- 왕복이 실제로 나간다
# ---------------------------------------------------------------------------

def test_real_backend_path_flushes_once_powers_and_bypasses(tmp_path, monkeypatch):  # noqa: ANN001
    """`GuideBackend` + `FakeArchon` -- 넷이 실제 왕복으로 무엇을 남기나.

    * `CCDFLUSH`: 가짜의 `flushes` 가 1 오르고 **프레임은 안 생기고**, 설정 메모리의
      `FirstFlush` 가 0 으로 되돌아온다 (`ACF_TEXT` 의 `PARAMETER0="FirstFlush=0"`;
      되쓰지 않으면 다음 LOADPARAMS 가 유령 flush 를 되살린다 -- DevNote 11.31).
      LOADPARAMS 는 한 번이다.
    * `CCDPOWOFF`/`CCDPOWON`: 가짜의 `powered` 가 따라 움직인다.
    * `ARCHON STATUS`: 가짜의 STATUS 본문(`POWERGOOD=1 …`)이 그대로 온다.
    * `ARCHON FOO`(가짜가 `?xx` 로 거부): `rejected: FOO`.
    """
    from fake_archon import FakeArchon
    from test_icg_backend import GUIDE_SYSTEM
    from test_icg_backend import make_cfgs as make_hw_cfgs

    fake = FakeArchon(width=8, height=4, readout_ticks=2, tick=0.01,
                      system=GUIDE_SYSTEM, nbuf=3, reject=('FOO',))
    fake.start()
    try:
        cfg, icfg = make_hw_cfgs(tmp_path, fake)
        cfg.transport.bind_port = 0
        cfg.transport.send_gap_ms = 0
        cfg.paths.expnum_file = str(tmp_path / 'icg.expnum')
        icfg.hk.interval = 3600.0
        icfg.hk.query_aux = False
        # 축소 기하(8x4) -- validate() 의 고정 기하 불변식은 실기 배선 전용
        # (`test_icg_backend._go_app` 과 같은 수법).
        import icg_archon.app as app_mod
        monkeypatch.setattr(app_mod, 'validate', lambda cfg, backend: [])
        app = IcgArchon(cfg, icfg, backend='icg_archon')

        def flush_slot_text():  # noqa: ANN202
            return next((v for v in fake.config.values() if 'FirstFlush=' in str(v)), '')

        async def wait_for(pred, what: str, n: int = 200) -> None:  # noqa: ANN001
            for _ in range(n):
                if pred():
                    return
                await asyncio.sleep(0.02)
            raise AssertionError('%s -- 기다려도 안 왔다.  sent=%r seen=%r'
                                 % (what, [str(m) for m in app.transport.sent_log][-6:],
                                    fake.seen[-10:]))

        def replied(word: str):  # noqa: ANN202
            return lambda: any(word in str(m) and ('DONE' in str(m) or 'ERROR' in str(m))
                               for m in app.transport.sent_log)

        async def run():  # noqa: ANN202
            await app.start()
            try:
                # 기동 접속(prepare: 접속·APPLYALL·POWERON)이 끝난 뒤에 시작한다.
                await wait_for(lambda: app.guide.ctrl.powered, '기동 접속(POWERON)')
                assert 'FirstFlush=0' in flush_slot_text(), flush_slot_text()
                app.transport.feed('abc>ICG CCDFLUSH')
                await wait_for(replied('CCDFLUSH'), 'CCDFLUSH 응답')
                await wait_for(lambda: getattr(fake, 'flushes', 0) >= 1, '가짜의 flush')
                app.transport.feed('abc>ICG CCDPOWOFF')
                await wait_for(replied('CCDPOWOFF'), 'CCDPOWOFF 응답')
                off_seen = fake.powered
                app.transport.feed('abc>ICG CCDPOWON')
                await wait_for(replied('CCDPOWON'), 'CCDPOWON 응답')
                on_seen = fake.powered
                app.transport.feed('abc>ICG ARCHON STATUS')
                await wait_for(replied('ARCHON'), 'ARCHON STATUS 응답')
                app.transport.feed('abc>ICG ARCHON FOO')
                await wait_for(lambda: any('rejected' in str(m)
                                           for m in app.transport.sent_log), 'ARCHON FOO 거부')
                await asyncio.sleep(0.05)
                return off_seen, on_seen
            finally:
                await app.stop()

        off_seen, on_seen = asyncio.run(run())
        sent = [str(m) for m in app.transport.sent_log]
        # ① flush 한 번 · 프레임 0 · FirstFlush=0 되쓰기 · LOADPARAMS 한 번
        assert any(s.endswith('DONE: CCDFLUSH Flushed=1') for s in sent), sent
        assert getattr(fake, 'flushes', 0) == 1, fake.__dict__.get('flushes')
        assert fake.frame_no == 0, 'flush 가 프레임을 만들었다 (%d)' % fake.frame_no
        assert 'FirstFlush=0' in flush_slot_text(), flush_slot_text()
        loads = [c for c in fake.seen if c.upper().startswith('LOADPARAMS')]
        assert len(loads) == 1, loads
        # ② 전원이 실제로 움직였다
        assert (off_seen, on_seen) == (False, True)
        assert any(s.endswith('DONE: CCDPOWOFF Power=OFF') for s in sent), sent
        assert any(s.endswith('DONE: CCDPOWON Power=ON') for s in sent), sent
        # ③ 바이패스 -- 응답 원문 · `?xx` 거부
        assert any('DONE: ARCHON' in s and 'POWERGOOD=1' in s for s in sent), sent
        assert any(s.endswith('ERROR: ARCHON rejected: FOO') for s in sent), sent
        assert app.emit.violations == [], app.emit.violations
    finally:
        fake.shutdown()

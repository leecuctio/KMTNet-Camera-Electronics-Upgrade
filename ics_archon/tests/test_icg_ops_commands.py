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

def test_three_are_refused_during_acquisition_and_archon_is_not(tmp_path):  # noqa: ANN001
    """(e) 취득 중이면 셋은 `ERROR: … Exposure in progress -- ABORT first`, `ARCHON` 은 받는다.

    히터·게이지(`_busy_note`: 받되 표시)와 **반대**다 -- 진행 중 노출 위의
    `LOADPARAMS`/`POWEROFF` 는 그 프레임을 망친다.  ⭐ `ARCHON` 은 제한이 없다 (운영자
    2026-09-05 "제한 없이 모두 풀어줘") -- 취득 중에도 원문이 나가고 `DONE` 이 온다.
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
    for word in [w for w in WORDS if w != 'ARCHON']:
        said = _about(sent, word)
        assert any('ERROR' in s and icg_commands.BUSY_REFUSAL in s
                   for s in said), (word, said)
        assert not any('DONE' in s for s in said), (word, said)
    said = _about(sent, 'ARCHON')
    assert any(s.endswith('DONE: ARCHON SIM (no controller): STATUS') for s in said), said
    assert not any(icg_commands.BUSY_REFUSAL in s for s in said), said
    # 거부가 취득을 건드리지 않았다 -- 2장이 그대로 저장됐다.
    assert '\n'.join(sent).count('Wrote LASTFILE=') == 2, sent
    assert app.emit.violations == [], app.emit.violations


def test_go_and_the_other_ops_wait_for_a_power_on_in_flight(tmp_path, monkeypatch):  # noqa: ANN001
    """⭐ `CCDPOWON` 이 왕복 중이면 `GO` 도, `CCDFLUSH` 도 **거부**한다 -- `ARCHON` 은 받는다.

    `POWERON` 은 ack 직후 `powered=True` 가 되고 그 뒤 `poweron_wait`(12 s) 동안
    CCD flush 를 기다리는데, 그 사이의 `GO` 는 `prepare()` 가 전원을 건너뛰어
    flush 가 안 끝난 CCD 를 arm 한다 (`controller.power_on`).  시퀀서 `busy`
    는 이 왕복을 모르므로 디스패처가 따로 든다 (`_op_in_flight`).
    """
    async def slow_power(self, on):  # noqa: ANN001, ANN202, ARG001
        await asyncio.sleep(0.3)

    monkeypatch.setattr(SimGuideBackend, 'power_ccd', slow_power)
    app, sent = _drive(tmp_path, ['abc>ICG CCDPOWON', 'abc>ICG GUIEXP 1',
                                  'abc>ICG GO 1', 'abc>ICG CCDFLUSH',
                                  'abc>ICG ARCHON STATUS'], settle=0.5)
    text = '\n'.join(sent)
    assert 'ERROR: GO Busy with CCDPOWON' in text, sent
    assert 'ERROR: CCDFLUSH Busy with CCDPOWON' in text, sent
    assert 'ERROR: ARCHON' not in text, sent          # 제한 없음 (2026-09-05)
    assert any(s.endswith('DONE: ARCHON SIM (no controller): STATUS') for s in sent), sent
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
    _app, sent = _drive(tmp_path, ['abc>ICG CCDFLUSH', 'abc>ICG GUIEXP 1',
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
                                  'abc>ICG GUIEXP 1', 'abc>ICG GO 1'])
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
      `FirstFlush=1`(`ACF_TEXT` 의 `PARAMETER0`, R2616 상수)은 **그대로**다 -- 호스트가
      쓰지 않는다 (DevNote 11.33).  LOADPARAMS 는 한 번이다.
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
                assert 'FirstFlush=1' in flush_slot_text(), flush_slot_text()
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
        # ① flush 한 번 · 프레임 0 · FirstFlush=1 그대로 · LOADPARAMS 한 번
        assert any(s.endswith('DONE: CCDFLUSH Flushed=1') for s in sent), sent
        assert getattr(fake, 'flushes', 0) == 1, fake.__dict__.get('flushes')
        assert fake.frame_no == 0, 'flush 가 프레임을 만들었다 (%d)' % fake.frame_no
        assert 'FirstFlush=1' in flush_slot_text(), flush_slot_text()
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


# -- Trigger Out (셔터 자리) -----------------------------------------------
#
# ⛔ **guide 에는 셔터가 없다** (frame-transfer).  기반의 `SHOPEN`/`SHCLOSE` 를
# 살려 두되 **Archon 의 Trigger Out 선**을 세우는 뜻으로 쓴다 (운영자 2026-09-08).
# ⭐ `TRIGOUTFORCE`(강제할지)와 `TRIGOUTLEVEL`(강제했을 때의 레벨)은 **다른
# 물건**이라, 핀을 실제로 HIGH 로 세우려면 둘 다 필요하다.
#
# ⛔ **guide 의 쉬는 상태는 `FORCE=1` + `LEVEL=0`** 이다 (운영자 확정
# 2026-09-08) -- 선을 우리가 붙들어 LOW 로 고정한다.  그래서 `SHCLOSE` 도,
# `SHOPEN` 의 자동 내림도 **강제를 풀지 않는다**.  종전 판은 `FORCE=0` 으로
# 내려놓아 선을 타이밍 스크립트에 넘겼고, `prepare()` 의 래치 탓에 재시작
# 전까지 안 돌아왔다 (벤치 2026-09-08).


#: 쉬는 상태로 시작하는 가짜 -- 평시 갈래를 재는 시험들이 쓴다.
RESTING = {'TRIGOUTLEVEL': '0', 'TRIGOUTFORCE': '1'}


class _Rec:
    """왕복을 **적용 단위로** 붙잡는 가짜 컨트롤러 표면.

    ⭐ `calls` 의 항목 하나가 `APPLYSYSTEM` **한 번**이다 -- 적용 횟수를 그대로
    셀 수 있어야 한다 (`SHOPEN` 이 평시에 한 번인 것이 이 판의 요점이다).
    항목 안의 차례는 **쓴 차례**(레벨이 먼저)다.
    ⚠️ 적용을 줄이는 이유가 *"VCPU 재시작 결측"* 은 **아니다** -- `APPLYSYSTEM`
    은 VCPU 를 안 건드린다(2026-09-08 실측).  이유는 **에지 시점**이다.
    """

    def __init__(self, held=None, wire=None):  # noqa: ANN001
        self.calls = []
        #: 우리가 들고 있는 값 (`ctrl.config` 대역).
        self.config = dict(held or {'TRIGOUTFORCE': '0', 'TRIGOUTLEVEL': '0'})
        #: ⛔ **컨트롤러가 실제로 든 값** -- 주면 캐시와 갈린다 (11.13 F5).
        self.wire = dict(wire) if wire is not None else None

    async def set_trigger(self, *, high=None, forced=None):  # noqa: ANN001, ANN202
        step = []
        if high is not None:
            step.append(('TRIGOUTLEVEL', bool(high)))
        if forced is not None:
            step.append(('TRIGOUTFORCE', bool(forced)))
        if not step:
            return                      # ⛔ 맨 APPLYSYSTEM 은 안 보낸다
        for key, want in step:
            self.config[key] = '1' if want else '0'
            if self.wire is not None:
                self.wire[key] = '1' if want else '0'
        self.calls.append(tuple(step))          # = APPLYSYSTEM 한 번

    async def set_trigger_forced(self, forced):  # noqa: ANN001, ANN202
        await self.set_trigger(forced=forced)

    async def set_trigger_level(self, high):  # noqa: ANN001, ANN202
        await self.set_trigger(high=high)

    def _held(self):  # noqa: ANN202
        return self.wire if self.wire is not None else self.config

    async def trigger_state(self):  # noqa: ANN202
        """`RCONFIG` 되읽기 -- ⛔ 캐시가 아니라 **컨트롤러가 든 값**이다."""
        held = self._held()
        return held['TRIGOUTLEVEL'], held['TRIGOUTFORCE']

    async def read_config(self, key):  # noqa: ANN001, ANN202
        """`RCONFIG` 대역 -- 조회가 **캐시가 아니라 여기를** 타야 한다."""
        return self._held()[key]


def _trig(tmp_path, script, held=None, settle=0.1, wire=None):  # noqa: ANN001, ANN202
    """스크립트를 먹이고 (적용 목록, 발신) 을 돌려준다."""
    rec = _Rec(held, wire)

    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        app = IcgArchon(cfg, icfg, backend='sim')
        app.guide.ctrl = rec
        await app.start()
        try:
            for line in script:
                app.transport.feed(line)
                await asyncio.sleep(0.05)
            await asyncio.sleep(settle)
        finally:
            await app.stop()
        return rec.calls, [str(s) for s in app.transport.sent_log]

    return asyncio.run(run())


def test_shopen_from_the_resting_state_is_a_single_apply(tmp_path):
    """⭐ 평시(`LEVEL=0`·`FORCE=1`)에는 **에지 하나**로 끝난다 -- 적용 1회.

    무장이 이미 돼 있으므로 되읽기 둘로 확인하고 건너뛴다 (운영자 2026-09-08).
    ⚠️ 되읽기는 왕복이지만 **적용이 아니다** -- 모듈을 안 건드린다.
    """
    calls, sent = _trig(tmp_path, ['abc>ICG SHOPEN 10'], held=dict(RESTING))
    assert calls[:1] == [(('TRIGOUTLEVEL', True),)], calls
    assert any('DONE: SHOPEN' in s and 'Sec=10' in s for s in sent), sent[-3:]
    assert not any('armed first' in s for s in sent), sent[-3:]


def test_shopen_arms_first_when_the_line_was_handed_over(tmp_path):
    """⛔ 쉬는 상태가 아니면 **무장 먼저** -- 그것도 한 번의 적용으로.

    ⭐ 무장을 앞세우는 값어치는 **에지를 마지막 한 쓰기가 만든다**는 것이다 --
    종전 판(`LEVEL=1` -> `FORCE=1`)은 앞 상태에 따라 에지가 첫 명령에서 나기도
    둘째에서 나기도 해서 시점을 못 짚었다.
    ⭐ 무장의 두 값이 **한 적용에 같이** 서므로 *"강제는 걸렸는데 레벨은 옛 값"*
    인 찰나가 없다 -- 여기서는 옛 레벨이 `1` 이라 그 찰나가 곧 헛 펄스다.
    """
    calls, sent = _trig(tmp_path, ['abc>ICG SHOPEN 10'],
                        held={'TRIGOUTLEVEL': '1', 'TRIGOUTFORCE': '0'})
    assert calls[:2] == [(('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True)),
                         (('TRIGOUTLEVEL', True),)], calls
    assert any('armed first' in s for s in sent), sent[-3:]


def test_a_lying_cache_does_not_make_shopen_do_nothing(tmp_path):
    """⛔ **캐시로 판단하면 안 된다** -- 이 시험이 그 자리를 막는다.

    `set_config` 는 **왕복이 실패해도 캐시를 먼저** 갈아 끼운다 (11.13 F5).
    그래서 캐시는 *"이미 `FORCE=1`"* 인데 컨트롤러는 `0` 인 경우가 실재한다.
    그 상태에서 무장을 건너뛰면 **선이 안 올라가는데 `DONE` 은 나간다** --
    결측보다 나쁜 종류다.  판단은 `RCONFIG` 되읽기여야 한다.
    """
    calls, _sent = _trig(tmp_path, ['abc>ICG SHOPEN 10'],
                         held=dict(RESTING),          # 캐시는 쉬는 상태라 말한다
                         wire={'TRIGOUTLEVEL': '0',   # ⛔ 실제로는 안 걸려 있다
                               'TRIGOUTFORCE': '0'})
    assert calls[:1] == [(('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True))], calls


def test_a_failed_state_read_back_arms_anyway(tmp_path):
    """⚠️ 되읽기가 실패하면 **무장한다** -- 모르면 세워 두는 쪽이 안전하다."""
    class _Blind(_Rec):
        async def trigger_state(self):  # noqa: ANN202
            raise RuntimeError('RCONFIG timeout')

    rec = _Blind(dict(RESTING))

    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        app = IcgArchon(cfg, icfg, backend='sim')
        app.guide.ctrl = rec
        await app.start()
        try:
            app.transport.feed('abc>ICG SHOPEN 10')
            await asyncio.sleep(0.15)
        finally:
            await app.stop()
        return rec.calls

    calls = asyncio.run(run())
    assert calls[:1] == [(('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True))], calls


def test_shopen_lowers_the_line_when_the_timer_expires(tmp_path):
    """⭐ **<초> 뒤에 스스로 내린다** -- 내림도 레벨 먼저다.

    ⚠️ 시한은 `cfg.scaled()` 를 타므로 시험 축척(0.02)에서 짧다.
    """
    calls, sent = _trig(tmp_path, ['abc>ICG SHOPEN 2'], settle=0.4,
                        held=dict(RESTING))
    assert calls == [(('TRIGOUTLEVEL', True),),
                     (('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True))], calls
    assert any('DONE: SHCLOSE' in s and 'auto' in s for s in sent), sent[-3:]
    # ⛔ 자동 내림도 **강제를 유지한다** -- 응답이 그 사실을 말해야 한다.
    assert any('TRIGOUTFORCE=1' in s and 'auto' in s for s in sent), sent[-3:]


def test_shclose_cancels_a_pending_shopen_timer(tmp_path):
    """⛔ 옛 타이머가 나중에 깨어나 **그때 세워져 있던 선을 내리면** 안 된다.

    ⚠️ 시한이 **명령 간격보다 길어야** 시험이 뜻을 갖는다 -- 축척 0.02 에서
    `SHOPEN 2` 는 0.04 s 라 `SHCLOSE` 가 닿기 전에 타이머가 먼저 터진다
    (그러면 취소를 안 해도 통과해 버린다).  `20` 이면 0.4 s 다.
    """
    calls, _sent = _trig(tmp_path, ['abc>ICG SHOPEN 20', 'abc>ICG SHCLOSE'],
                         settle=0.6, held=dict(RESTING))
    # 적용은 둘뿐이어야 한다 -- 타이머가 살아 있으면 하나가 더 붙는다.
    assert calls == [(('TRIGOUTLEVEL', True),),
                     (('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True))], calls


def test_shclose_drops_the_level_but_keeps_the_force(tmp_path):
    """⭐ **순서가 뜻이다** -- 레벨이 먼저다.  그리고 **강제는 유지한다**.

    거꾸로 강제를 먼저 만지면 그 찰나에 *옛* 레벨이 핀으로 나간다.
    ⛔ 끝이 `TRIGOUTFORCE=1` 이라 **guide 의 쉬는 상태로 돌아간다** -- 선은
    우리 손에 남고 레벨만 LOW 다.  `FORCE=0` 으로 내려놓으면 선이 타이밍
    스크립트 손에 넘어가 노출마다 흔들린다 (벤치 2026-09-08).
    """
    calls, sent = _trig(tmp_path, ['abc>ICG SHCLOSE'])
    # ⭐ **적용 한 번**에 둘이 같이 선다 -- 되읽기도 안 한다 (아낄 적용이 없다).
    assert calls == [(('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True))], calls
    assert any('DONE: SHCLOSE TRIGOUTLEVEL=0 TRIGOUTFORCE=1' in s
               for s in sent), sent[-3:]


def test_a_full_shopen_shclose_round_leaves_the_resting_state(tmp_path):
    """⛔ **한 바퀴 돌고 나면 쉬는 상태여야 한다** -- 벤치가 잡은 그 자리.

    운영자가 `shopen 10` 을 돌린 뒤 선이 `FORCE=0` 으로 남았고, 그 상태에서는
    **타이밍 스크립트가 선을 몬다.**  마지막 값만 본다 (순서는 위 시험들 몫).
    """
    calls, _sent = _trig(tmp_path, ['abc>ICG SHOPEN 20', 'abc>ICG SHCLOSE'],
                         settle=0.6, held=dict(RESTING))
    last = {}
    for step in calls:
        for key, want in step:
            last[key] = want
    assert last == {'TRIGOUTLEVEL': False, 'TRIGOUTFORCE': True}, calls


def test_shopen_needs_a_duration(tmp_path):
    """⛔ 인자가 없으면 거절한다 -- 얼마나 세울지가 명령의 핵심이다."""
    calls, sent = _trig(tmp_path, ['abc>ICG SHOPEN', 'abc>ICG SHOPEN abc'])
    assert calls == [], '거절하고도 왕복했다'
    assert sum('ERROR: SHOPEN' in s for s in sent) == 2, sent[-4:]


def test_trigoutforce_and_level_are_separate_keys(tmp_path):
    """둘은 **다른 설정 키**다 -- 한쪽만 세우면 한쪽만 간다."""
    calls, _sent = _trig(tmp_path, ['abc>ICG TRIGOUTFORCE ON',
                                    'abc>ICG TRIGOUTLEVEL HIGH'])
    assert calls == [(('TRIGOUTFORCE', True),),
                     (('TRIGOUTLEVEL', True),)], calls


def test_the_boolean_vocabulary_is_the_shared_one(tmp_path):
    """⭐ `true=enable=high=on=1` · `false=disable=low=off=0` (운영자 2026-09-08).

    ⛔ 어휘 밖은 **기본값으로 안 떨어뜨린다** -- 무엇이 허용인지 대고 거절한다.
    """
    calls, sent = _trig(tmp_path, ['abc>ICG TRIGOUTLEVEL enable',
                                   'abc>ICG TRIGOUTFORCE disable',
                                   'abc>ICG TRIGOUTLEVEL sideways'])
    assert calls == [(('TRIGOUTLEVEL', True),),
                     (('TRIGOUTFORCE', False),)], calls
    assert any('ERROR: TRIGOUTLEVEL' in s and 'Unrecognized' in s
               for s in sent), sent[-3:]


def test_no_argument_reads_back_from_the_controller(tmp_path):
    """인자가 없으면 조회 -- ⭐ **캐시가 아니라 `RCONFIG` 되읽기**다.

    히터 다섯과 같은 규약이다 (`commands.py` 머리말).  ⛔ `ctrl.config` 는
    `set_config` 가 **왕복 실패에도 먼저** 갈아 끼우므로 못 믿는다 -- 캐시를
    답하면 *"1 이라고 답하는데 실제 핀은 0"* 이 된다.
    """
    _calls, sent = _trig(tmp_path, ['abc>ICG TRIGOUTFORCE'],
                         held={'TRIGOUTFORCE': '1', 'TRIGOUTLEVEL': '0'})
    assert any('DONE: TRIGOUTFORCE TRIGOUTFORCE=1' in s for s in sent), sent[-3:]


def test_a_failed_read_back_is_not_hidden(tmp_path):
    """⛔ 되읽기가 실패하면 **답을 지어내지 않는다** -- ERROR 로 올린다."""
    class _Broken(_Rec):
        async def read_config(self, key):  # noqa: ANN001, ANN202
            raise RuntimeError('RCONFIG timeout')

    rec = _Broken()

    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        app = IcgArchon(cfg, icfg, backend='sim')
        app.guide.ctrl = rec
        await app.start()
        try:
            app.transport.feed('abc>ICG TRIGOUTLEVEL')
            await asyncio.sleep(0.15)
        finally:
            await app.stop()
        return [str(s) for s in app.transport.sent_log]

    sent = asyncio.run(run())
    assert any('ERROR: TRIGOUTLEVEL' in s and 'RCONFIG timeout' in s
               for s in sent), sent[-3:]

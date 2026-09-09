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
        # ⛔ **지속 파일을 tmp 로 돌린다** -- 안 하면 `EXPENABLE OFF` 가 작업
        # 폴더의 `icg_archon.expenable` 에 남아 **다음 시험의 `GO` 가 거절된다**
        # (2026-09-09 실제로 났다).  `_drive` 는 처음부터 이렇게 하고 있었다.
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        icfg.expnum_file = str(tmp_path / 'icg.expnum')
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
# ⛔ **guide 에는 셔터가 없다** (frame-transfer).  기반의 `TRIGOUT`/`TRIGOUT 0` 를
# 살려 두되 **Archon 의 Trigger Out 선**을 세우는 뜻으로 쓴다 (운영자 2026-09-08).
# ⭐ `TRIGOUTFORCE`(강제할지)와 `TRIGOUTLEVEL`(강제했을 때의 레벨)은 **다른
# 물건**이라, 핀을 실제로 HIGH 로 세우려면 둘 다 필요하다.
#
# ⛔ **guide 의 쉬는 상태는 `FORCE=1` + `LEVEL=0`** 이다 (운영자 확정
# 2026-09-08) -- 선을 우리가 붙들어 LOW 로 고정한다.  그래서 `TRIGOUT 0` 도,
# `TRIGOUT` 의 자동 내림도 **강제를 풀지 않는다**.  종전 판은 `FORCE=0` 으로
# 내려놓아 선을 타이밍 스크립트에 넘겼고, `prepare()` 의 래치 탓에 재시작
# 전까지 안 돌아왔다 (벤치 2026-09-08).


#: 쉬는 상태로 시작하는 가짜 -- 평시 갈래를 재는 시험들이 쓴다.
RESTING = {'TRIGOUTLEVEL': '0', 'TRIGOUTFORCE': '1'}


class _Rec:
    """왕복을 **적용 단위로** 붙잡는 가짜 컨트롤러 표면.

    ⭐ `calls` 의 항목 하나가 `APPLYSYSTEM` **한 번**이다 -- 적용 횟수를 그대로
    셀 수 있어야 한다 (`TRIGOUT` 이 평시에 한 번인 것이 이 판의 요점이다).
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
        # ⛔ **지속 파일을 tmp 로 돌린다** -- 안 하면 `EXPENABLE OFF` 가 작업
        # 폴더의 `icg_archon.expenable` 에 남아 **다음 시험의 `GO` 가 거절된다**
        # (2026-09-09 실제로 났다).  `_drive` 는 처음부터 이렇게 하고 있었다.
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        icfg.expnum_file = str(tmp_path / 'icg.expnum')
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


def test_trigout_from_the_resting_state_is_a_single_apply(tmp_path):
    """⭐ 평시(`LEVEL=0`·`FORCE=1`)에는 **에지 하나**로 끝난다 -- 적용 1회.

    무장이 이미 돼 있으므로 되읽기 둘로 확인하고 건너뛴다 (운영자 2026-09-08).
    ⚠️ 되읽기는 왕복이지만 **적용이 아니다** -- 모듈을 안 건드린다.
    """
    calls, sent = _trig(tmp_path, ['abc>ICG TRIGOUT 10'], held=dict(RESTING))
    assert calls[:1] == [(('TRIGOUTLEVEL', True), ('TRIGOUTFORCE', True))], calls
    assert any('DONE: TRIGOUT' in s and 'Sec=10' in s for s in sent), sent[-3:]


def test_trigout_writes_both_whatever_the_previous_state(tmp_path):
    """⭐ **판단을 안 한다** -- 앞 상태가 무엇이든 둘을 같이 쓴다 (적용 한 번).

    ⛔ 종전 판은 *"이미 무장 상태면 건너뛴다"* 를 `RCONFIG` 되읽기로 판단했다.
    늘 쓰면 그 판단이 필요 없고, **캐시가 거짓이면 조용히 아무것도 안 한다**는
    결함 부류도 함께 사라진다 (운영자 2026-09-09).
    ⚠️ 이 시험의 값어치는 **되읽기를 되살리려는 다음 사람을 막는 것**이다.
    """
    calls, _sent = _trig(tmp_path, ['abc>ICG TRIGOUT 10'],
                         held={'TRIGOUTLEVEL': '1', 'TRIGOUTFORCE': '0'})
    assert calls[:1] == [(('TRIGOUTLEVEL', True), ('TRIGOUTFORCE', True))], calls


def test_a_lying_cache_cannot_make_trigout_do_nothing(tmp_path):
    """⛔ 캐시가 *"이미 그 상태"* 라고 거짓말해도 **쓰기는 나간다**.

    `set_config` 는 왕복이 실패해도 캐시를 먼저 갈아 끼운다 (11.13 F5) -- 그
    캐시로 건너뛸지 판단하면 **선이 안 올라가는데 `DONE` 은 나간다**.
    """
    calls, _sent = _trig(tmp_path, ['abc>ICG TRIGOUT 10'],
                         held=dict(RESTING),
                         wire={'TRIGOUTLEVEL': '0', 'TRIGOUTFORCE': '0'})
    assert calls[:1] == [(('TRIGOUTLEVEL', True), ('TRIGOUTFORCE', True))], calls


def test_trigout_lowers_the_line_when_the_timer_expires(tmp_path):
    """⭐ **<초> 뒤에 스스로 내린다** -- 내림도 레벨 먼저다.

    ⚠️ 시한은 `cfg.scaled()` 를 타므로 시험 축척(0.02)에서 짧다.
    """
    calls, sent = _trig(tmp_path, ['abc>ICG TRIGOUT 2'], settle=0.4,
                        held=dict(RESTING))
    assert calls == [(('TRIGOUTLEVEL', True), ('TRIGOUTFORCE', True)),
                     (('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True))], calls
    assert any('DONE: TRIGOUT' in s and 'auto' in s for s in sent), sent[-3:]
    # ⛔ 자동 내림도 **강제를 유지한다** -- 응답이 그 사실을 말해야 한다.
    assert any('TRIGOUTFORCE=1' in s and 'auto' in s for s in sent), sent[-3:]


def test_trigout_zero_cancels_a_pending_timer(tmp_path):
    """⛔ 옛 타이머가 나중에 깨어나 **그때 세워져 있던 선을 내리면** 안 된다.

    ⚠️ 시한이 **명령 간격보다 길어야** 시험이 뜻을 갖는다 -- 축척 0.02 에서
    `TRIGOUT 2` 는 0.04 s 라 `TRIGOUT 0` 가 닿기 전에 타이머가 먼저 터진다
    (그러면 취소를 안 해도 통과해 버린다).  `20` 이면 0.4 s 다.
    """
    calls, _sent = _trig(tmp_path, ['abc>ICG TRIGOUT 20', 'abc>ICG TRIGOUT 0'],
                         settle=0.6, held=dict(RESTING))
    # 적용은 둘뿐이어야 한다 -- 타이머가 살아 있으면 하나가 더 붙는다.
    assert calls == [(('TRIGOUTLEVEL', True), ('TRIGOUTFORCE', True)),
                     (('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True))], calls


def test_trigout_zero_drops_the_level_but_keeps_the_force(tmp_path):
    """⭐ **순서가 뜻이다** -- 레벨이 먼저다.  그리고 **강제는 유지한다**.

    거꾸로 강제를 먼저 만지면 그 찰나에 *옛* 레벨이 핀으로 나간다.
    ⛔ 끝이 `TRIGOUTFORCE=1` 이라 **guide 의 쉬는 상태로 돌아간다** -- 선은
    우리 손에 남고 레벨만 LOW 다.  `FORCE=0` 으로 내려놓으면 선이 타이밍
    스크립트 손에 넘어가 노출마다 흔들린다 (벤치 2026-09-08).
    """
    calls, sent = _trig(tmp_path, ['abc>ICG TRIGOUT 0'])
    # ⭐ **적용 한 번**에 둘이 같이 선다 -- 되읽기도 안 한다 (아낄 적용이 없다).
    assert calls == [(('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True))], calls
    assert any('DONE: TRIGOUT TRIGOUTLEVEL=0 TRIGOUTFORCE=1' in s
               for s in sent), sent[-3:]


def test_a_full_trigout_round_leaves_the_resting_state(tmp_path):
    """⛔ **한 바퀴 돌고 나면 쉬는 상태여야 한다** -- 벤치가 잡은 그 자리.

    운영자가 `shopen 10` 을 돌린 뒤 선이 `FORCE=0` 으로 남았고, 그 상태에서는
    **타이밍 스크립트가 선을 몬다.**  마지막 값만 본다 (순서는 위 시험들 몫).
    """
    calls, _sent = _trig(tmp_path, ['abc>ICG TRIGOUT 20', 'abc>ICG TRIGOUT 0'],
                         settle=0.6, held=dict(RESTING))
    last = {}
    for step in calls:
        for key, want in step:
            last[key] = want
    assert last == {'TRIGOUTLEVEL': False, 'TRIGOUTFORCE': True}, calls


def test_trigout_needs_a_duration(tmp_path):
    """⛔ 인자가 없으면 거절한다 -- 얼마나 세울지가 명령의 핵심이다."""
    calls, sent = _trig(tmp_path, ['abc>ICG TRIGOUT', 'abc>ICG TRIGOUT abc'])
    assert calls == [], '거절하고도 왕복했다'
    assert sum('ERROR: TRIGOUT' in s for s in sent) == 2, sent[-4:]


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
        # ⛔ **지속 파일을 tmp 로 돌린다** -- 안 하면 `EXPENABLE OFF` 가 작업
        # 폴더의 `icg_archon.expenable` 에 남아 **다음 시험의 `GO` 가 거절된다**
        # (2026-09-09 실제로 났다).  `_drive` 는 처음부터 이렇게 하고 있었다.
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        icfg.expnum_file = str(tmp_path / 'icg.expnum')
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


def test_dmawait_is_refused_on_guide(tmp_path):
    """⛔ guide 엔 **광케이블 IC 가 없다** -- 감추지 않고 거절한다 (운영자 2026-09-08).

    `DMAWAIT` 는 레거시 IC 의 광케이블 통신 지연이다.  종전에는 상속으로 살아
    있어 `DONE: DMAWAIT DMAWaitTime=…` 을 **성공으로** 답했고 그 값은 아무 데도
    안 쓰였다 -- 거짓 성공이다.
    ⚠️ **도움말에서만 빼면 안 된다**: 응답은 하면서 표에서만 빼면 *"모르는
    명령"* 과 *"안 보이는 명령"* 이 구별되지 않는다.  그래서 응답도 멈춘다.
    """
    _calls, sent = _trig(tmp_path, ['abc>ICG DMAWAIT 5'])
    assert any('ERROR: DMAWAIT' in s and 'Not supported' in s
               for s in sent), sent[-3:]


def test_abort_cancels_a_running_trigout_and_lowers_the_line(tmp_path):
    """⛔ **ABORT 는 켜져 있던 LED 를 끄고 가야 한다** (운영자 2026-09-09).

    `ABORT` 의 `RESETTIMING` 은 **타이밍 코어만** 되돌리는데, 펄스 중에는
    `TRIGOUTFORCE=1` 이라 핀이 코어를 안 따라간다 -- 종전에는 타이머가 `<초>`
    뒤에 쓸 때까지 **선이 HIGH 로 남았다**.
    """
    calls, _sent = _trig(tmp_path, ['abc>ICG TRIGOUT 20', 'abc>ICG ABORT'],
                         held=dict(RESTING), settle=0.4)
    assert calls, 'TRIGOUT/ABORT 가 트리거 선을 아예 안 건드렸다'
    # 세움 하나 + ABORT 의 내림 하나.  타이머가 살아 있으면 하나가 더 붙는다.
    assert len(calls) == 2, calls
    last = {}
    for step in calls:
        for key, want in step:
            last[key] = want
    assert last == {'TRIGOUTLEVEL': False, 'TRIGOUTFORCE': True}, calls


def test_abort_without_a_pulse_writes_nothing(tmp_path):
    """⚠️ 펄스가 없었으면 **군더더기 왕복을 만들지 않는다**."""
    calls, _sent = _trig(tmp_path, ['abc>ICG go 2', 'abc>ICG ABORT'],
                         held=dict(RESTING), settle=0.3)
    assert calls == [], '펄스도 없는데 트리거 선을 건드렸다: %r' % calls


def test_expenable_off_also_releases_the_pulse(tmp_path):
    """⭐ `EXPENABLE OFF` 도 사이클을 세우는 경로다 -- **펄스도 끊는다**.

    ⚠️ `busy` 와 무관하다: 취득 중이 아니어도 펄스는 돌 수 있다.
    """
    calls, _sent = _trig(tmp_path,
                         ['abc>ICG TRIGOUT 20', 'abc>ICG EXPENABLE OFF'],
                         held=dict(RESTING), settle=0.4)
    assert len(calls) == 2, calls
    assert calls[1] == (('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True)), calls


def test_shutdown_lowers_a_running_pulse(tmp_path):
    """⛔ **종료가 펄스를 내리고 가야 한다** (운영자 2026-09-09).

    `spawn` 한 펄스 태스크는 종료가 `_tasks` 를 취소하면서 함께 죽는다 -- 그러면
    내림이 **영영 안 돌고** 사람 없는 채로 **LED 가 켜진 채** 프로세스가 끝난다.
    ⚠️ 그래서 `stop()` 은 `spawn` 이 아니라 **기다린다**.
    """
    rec = _Rec(dict(RESTING))

    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        # ⛔ **지속 파일을 tmp 로 돌린다** -- 안 하면 `EXPENABLE OFF` 가 작업
        # 폴더의 `icg_archon.expenable` 에 남아 **다음 시험의 `GO` 가 거절된다**
        # (2026-09-09 실제로 났다).  `_drive` 는 처음부터 이렇게 하고 있었다.
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        icfg.expnum_file = str(tmp_path / 'icg.expnum')
        app = IcgArchon(cfg, icfg, backend='sim')
        app.guide.ctrl = rec
        await app.start()
        app.transport.feed('abc>ICG TRIGOUT 20')
        await asyncio.sleep(0.15)
        await app.stop()                      # ← 여기서 내려야 한다
        return rec.calls

    calls = asyncio.run(run())
    assert calls[-1] == (('TRIGOUTLEVEL', False), ('TRIGOUTFORCE', True)), calls


def test_go_says_why_while_the_stop_tail_drains(tmp_path):
    """⭐ 뒷정리 중 `GO` 거절은 **이유를 말한다** (운영자 2026-09-09).

    ⛔ 기반은 `Data acquisition already in progress!` 하나로 답하는데, `STOP`
    뒤 꼬리 소화 구간에서는 **틀린 그림**이다 -- 저장은 이미 끝났고 컨트롤러
    꼬리를 기다리는 중이다 (벤치: `guiexp 15` 에서 32초).
    ⚠️ **거절 자체는 그대로**다 -- 그 꼬리를 다음 시퀀스가 제 첫 프레임으로
    알면 남의 픽셀이 정상 헤더로 저장된다 (9.15-(9)).
    """
    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        icfg.expnum_file = str(tmp_path / 'icg.expnum')
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        try:
            # ⭐ **사이클이 도는 중이고 뒷정리 단계**인 상태를 만든다.
            # ⚠️ `_settling` 만 세우면 안 된다 -- 그것은 다음 사이클 시작 때만
            # 내려가므로 `settling` 은 `busy` 와 함께 본다 (시험이 잡은 자리).
            app.seq._task = asyncio.ensure_future(asyncio.sleep(1))
            app.seq._settling = True
            app.transport.feed('abc>ICG go 1')
            await asyncio.sleep(0.1)
        finally:
            app.seq._settling = False
            app.seq._task.cancel()
            app.seq._task = None
            await app.stop()
        return [str(s) for s in app.transport.sent_log]

    sent = asyncio.run(run())
    assert any('ERROR: GO' in s and 'draining controller tail' in s
               for s in sent), sent[-3:]
    assert not any('already in progress' in s for s in sent), sent[-3:]


class _SlowRec(_Rec):
    """적용 하나가 `delay` 초 걸리는 컨트롤러 -- **FETCH 락 대기 대역**이다."""

    def __init__(self, delay, **kw):  # noqa: ANN001, ANN204
        super().__init__(**kw)
        self.delay = delay

    async def set_trigger(self, *, high=None, forced=None):  # noqa: ANN001, ANN202
        import asyncio
        await asyncio.sleep(self.delay)
        await super().set_trigger(high=high, forced=forced)


def _trig_slow(tmp_path, script, delay, settle=0.4, held=None):  # noqa: ANN001, ANN202
    """`_trig` 와 같되 **느린 컨트롤러**를 먹인다.  (적용목록, 발신) 을 준다."""
    import asyncio

    rec = _SlowRec(delay, held=held)

    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        icfg.expnum_file = str(tmp_path / 'icg.expnum')
        icfg.latency_warn_ms = 0.0          # ⭐ 전부 남긴다 (벤치와 같은 설정)
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


def test_trigout_pulse_width_does_not_inherit_the_startup_delay(tmp_path, caplog):
    """⭐ **밀려서 시작해도 폭은 맞는다** -- 시한을 `raise_line` **뒤부터** 잰다.

    ⏳ 운영자가 물은 것 (2026-09-09): *"guide 연속 노출 중 `trigout <sec>`
    실행 지연 여부"*.  ⛔ 실기에서 밀리는 원인은 `_locked_thread` 다 -- 모든
    왕복이 한 줄로 서므로 진행 중인 FETCH(guide 8.3 MiB ≈ 0.08 s, 잠금 상한
    `fetch_timeout` = 1 s) 뒤에 선다.  여기서는 그 대기를 **느린 컨트롤러**로
    대역한다.

    ⭐ **재는 것이 둘로 갈린다**: *시작이 밀리는 것* 과 *폭이 틀어지는 것*.
    앞은 어쩔 수 없지만 뒤는 광원 노출량을 바꾸므로 훨씬 나쁘다.  이 시험은
    **뒤가 앞에 안 물린다**를 못박는다 -- `asyncio.sleep` 이 올림 왕복 **뒤에**
    시작하므로 구조상 그렇고, 순서를 뒤집는 고침이 오면 여기서 깨진다.
    """
    import logging
    import re

    caplog.set_level(logging.INFO, logger='icg_archon.cmd')
    calls, _sent = _trig_slow(tmp_path, ['abc>ICG TRIGOUT 2'], delay=0.15,
                              settle=0.6, held=dict(RESTING))
    assert len(calls) == 2, calls              # 올림 한 번 · 내림 한 번

    text = caplog.text
    assert 'TRIGOUT 올림 지연' in text, text
    assert 'TRIGOUT 내림 지연' in text, text

    # ⭐ 올림은 대역한 대기(150 ms)만큼 밀렸다.
    up = re.search(r'TRIGOUT 올림 지연 -- 수신→완료 ([0-9.]+) ms', text)
    assert up is not None and float(up.group(1)) >= 140.0, text

    # ⭐ 그런데 **폭 오차는 그 밀림을 안 물려받는다** -- 남는 것은 내림 쪽
    # 대기뿐이라 대역값 언저리지, 그 두 배가 아니다.
    err = re.search(r'폭오차 ([+-][0-9.]+) ms', text)
    assert err is not None, text
    assert 0.0 <= float(err.group(1)) < 250.0, text


def test_hkdata_logs_its_latency(tmp_path):
    """⏳ `HKDATA` 도 **수신→완료**를 한 줄로 남긴다 (같은 실측 항목).

    ⚠️ 종전에는 `HKQDATE` 와 응답 로그 시각을 **눈으로 빼야** 했다 -- 연속
    노출 중에 여러 번 치며 재려면 그 뺄셈이 실측을 가로막는다.
    """
    import asyncio
    import logging

    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        icfg.expnum_file = str(tmp_path / 'icg.expnum')
        icfg.latency_warn_ms = 0.0
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        try:
            app.transport.feed('abc>ICG HKDATA')
            await asyncio.sleep(0.2)
        finally:
            await app.stop()

    import logging as _lg

    seen = []

    class _Grab(_lg.Handler):
        def emit(self, record):  # noqa: ANN001, ANN202
            seen.append(record.getMessage())

    lg = logging.getLogger('icg_archon.cmd')
    h = _Grab()
    lg.addHandler(h)
    old = lg.level
    lg.setLevel(logging.INFO)
    try:
        asyncio.run(run())
    finally:
        lg.removeHandler(h)
        lg.setLevel(old)

    assert any('HKDATA 지연' in m for m in seen), seen


def test_trigout_latency_is_logged_even_under_a_high_threshold(tmp_path, caplog):
    """⭐ **`TRIGOUT` 은 임계를 안 태고 늘 남긴다** (2026-09-09 정정).

    ⛔ 종전 판은 셋 다 `latency_warn_ms` 를 타게 했고, 그 근거로
    *"`HKDATA` 는 프레임마다 온다"* 를 적었다.  그 근거가 **틀렸다** --
    `_ask_icg('HKDATA')` 를 부르는 곳은 명령 처리기 둘뿐이고 주기
    발신자가 없다.  `TRIGOUT` 은 더욱 드물고(운영자가 칠 때뿐),
    ⭐ 그 지연 자체가 진단 값이라 높은 임계에도 숨으면 안 된다.

    ⚠️ 임계를 매우 크게(10 s) 두고도 줄이 남는지를 본다 --
    `always=True` 를 떼면 여기서 깨진다.
    """
    import asyncio
    import logging

    rec = _Rec(dict(RESTING))

    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        icfg.expnum_file = str(tmp_path / 'icg.expnum')
        icfg.latency_warn_ms = 10_000.0      # ⛔ 잠재울 만큼 높게
        app = IcgArchon(cfg, icfg, backend='sim')
        app.guide.ctrl = rec
        await app.start()
        try:
            app.transport.feed('abc>ICG TRIGOUT 2')
            await asyncio.sleep(0.3)
        finally:
            await app.stop()

    caplog.set_level(logging.INFO, logger='icg_archon.cmd')
    asyncio.run(run())
    assert 'TRIGOUT 올림 지연' in caplog.text, caplog.text
    assert 'TRIGOUT 내림 지연' in caplog.text, caplog.text


def test_trigout_subtracts_the_lowering_apply_from_the_pulse(tmp_path, caplog):
    """⭐ **폭이 요청값이 된다** -- 내림 적용시간을 잠들 시간에서 뻐다.

    ⛔ **벤치 실측이 앞 판을 뒤집었다** (2026-09-09): 요청 2 s 에 폭오차가
    **+235 ms 로 17회 내내 일정**했다.  낙 대기가 아니라 **내림 자신의
    `APPLYSYSTEM` 처리시간**(≈233 ms)이 통째로 폭에 들어간 것이다.
    ⚠️ 0.5 s 펀스라면 **+47 %** 다 -- 광원 노출량이 그만큼 틀린다.

    ⭐ 보정이 옆길로 새지 않는 근거: 적용 하나에 `C` 가 걸리고 핀이 그
    안 비율 `f` 에서 뒤집힌다면 HIGH 는 `t + fC`, LOW 는 `t + C + 잠 + fC`
    이므로 **폭 = 잠 + C** 이고 `f` 가 지워진다.  그래서 `잠 = <초> - C` 다.

    ⚠️ 여기서는 느린 컨트롤러(0.1 s)로 `C` 를 대역한다.  보정이 없으면
    폭오차가 **+100 ms** 로 나온다 -- 그것이 이 시험이 잡는 회귀다.
    """
    import logging
    import re

    caplog.set_level(logging.INFO, logger='icg_archon.cmd')
    # time_scale = 0.02 이므로 `trigout 20` 은 실제 0.4 s 펀스다.
    calls, _sent = _trig_slow(tmp_path, ['abc>ICG TRIGOUT 20'], delay=0.1,
                              settle=1.0, held=dict(RESTING))
    assert len(calls) == 2, calls

    err = re.search(r'폭오차 ([+-][0-9.]+) ms', caplog.text)
    assert err is not None, caplog.text
    got = float(err.group(1))
    # ⭐ 보정 전이면 +100 ms 다 -- 그 절반보다 작아야 보정이 먹은 것이다.
    assert abs(got) < 50.0, (got, caplog.text)
    assert '보정 -' in caplog.text, caplog.text

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""운영자 명령 넷 -- `CCDFLUSH` · `CCDPOWON` · `CCDPOWOFF` · `ARCHON` (운영자 지시 2026-09-05).

`ics_archon/app.py` 의 `IcsDispatcher` 가 `ics_sim` 디스패처에 덧댄 명령이다.  가짜
컨트롤러 2대(`fake_archon.FakeArchon`)를 상대로 **전 경로**를 돈다 -- 메시지 수신 ->
핸들러 -> 백엔드 원시 함수(`flush_ccd`/`power_ccd`/`raw_command`) -> 컨트롤러 왕복 ->
늦은 `DONE`/`ERROR`.

보는 것:

* (a) `CCDFLUSH` -- `DONE` · 가짜의 `flushes` 증가 · 설정 메모리 `FirstFlush` 가 0 으로 되돌아옴
* (b) `CCDPOWOFF`/`CCDPOWON` -- 가짜의 `powered` 토글 · `DONE` 문구
* (c) `ARCHON MK STATUS` -- `DONE` 본문에 `STATUS` 토큰 · 긴 응답은 잘리고 전문은 로그에
* (d) `ARCHON` 잘못된 태그 / 빈 명령 -- usage `ERROR`
* (e) 취득 중(`seq.busy`) -- 넷 다 거부, 컨트롤러에 아무것도 안 나간다
* (f) 발신 위생 -- `emitter.validate()` 가 `unknown_cmdword` 로 울지 않는다 (등록 안 하면 운다)

⚠️ science ACF 실물은 열지 않는다 -- 시험용 최소 ACF 에 파라미터 슬롯 셋만 넣는다.
`PARAMETER0="FirstFlush=0"` 이 있어야 `flush_now()` 가 돈다 (science R2609+ 전제).
"""

from __future__ import annotations

import asyncio
import logging
import os

import pytest
from fake_archon import FULL_STATUS, FakeArchon

from ics_archon import config as acfg_mod
from ics_archon.app import (ARCHON_REPLY_MAX, BUSY_TEXT, ICS_OPS_COMMANDS,
                            IcsArchon, extend_vocabulary, wire_text)

from ics_sim import config as simcfg
from ics_sim import emitter
from ics_sim.impv2 import MAX_LEN

NX, NY = 12, 4

#: 파라미터 슬롯 셋 -- `param_flush_slot`(PARAMETER0) · `param_exposures_slot`(1) ·
#: `param_intms_slot`(2) 의 기본값과 같은 자리다 (`config.ArchonCfg`).
ACF_TEXT = """[CONFIG]
TRIGOUTFORCE=0
PARAMETER0="FirstFlush=0"
PARAMETER1="Exposures=0"
PARAMETER2="IntMS=0"
"""

INI = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    os.pardir, 'ics_archon.ini'))

#: 첫 `GO` -- `prepare()` 가 ACF 를 파싱·적용하고 전원을 켠다.  `CCDFLUSH` 는 그 줄
#: 번호가 있어야 돈다 (아래 `test_ccdflush_before_any_go_says_why`).
WARMUP = ('OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go')


# ---------------------------------------------------------------------------
# 하네스 -- `test_backend.py` 의 `make_cfgs`/`_drive` 와 같은 틀
# ---------------------------------------------------------------------------

def make_cfgs(tmp_path, mk_port: int):  # noqa: ANN001
    acf = tmp_path / 'test.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')

    cfg = simcfg.load(INI)
    cfg.timing.time_scale = 0.02
    cfg.transport.bind_host = '127.0.0.1'
    cfg.transport.bind_port = 0
    cfg.transport.send_gap_ms = 0.0
    cfg.behavior.console = False
    cfg.logging.wire = False
    cfg.paths.data_dir = str(tmp_path / 'rawdata')
    cfg.paths.expnum_file = str(tmp_path / 'expnum')
    cfg.hardware.backend = 'archon'

    acfg = acfg_mod.load(INI)
    acfg.require_xis = False                   # 허브 없이 도는 하네스
    acfg.hosts = {'MK': '127.0.0.1', 'NT': '127.0.0.1'}
    acfg.acf = {'MK': str(acf), 'NT': str(acf)}
    acfg.naxis1, acfg.naxis2 = NX, NY
    acfg.poweron_wait = 0.0
    acfg.monitor = False                       # 감시 CSV 를 홈에 쌓지 않는다
    acfg.frame_poll = 0.01
    acfg.port = mk_port
    return cfg, acfg


class Session:
    """가짜 2대 + 기동한 `IcsArchon`.  `reply()` 로 명령 하나의 답을 기다린다."""

    def __init__(self, tmp_path, **fake_kw) -> None:  # noqa: ANN001
        fake_kw.setdefault('status', dict(FULL_STATUS))   # `VALID=` 가 있는 STATUS
        self.mk = FakeArchon(width=NX, height=NY, **fake_kw)
        self.nt = FakeArchon(width=NX, height=NY, **fake_kw)
        self.tmp_path = tmp_path
        self.app: IcsArchon | None = None

    async def __aenter__(self) -> 'Session':
        self.mk.start()
        self.nt.start()
        cfg, acfg = make_cfgs(self.tmp_path, self.mk.port)
        self.app = IcsArchon(cfg, acfg)
        self.app.backend.ctrls['NT'].link.port = self.nt.port
        await self.app.start()
        return self

    async def __aexit__(self, *exc) -> None:  # noqa: ANN002
        try:
            await self.app.stop()
        finally:
            self.mk.shutdown()
            self.nt.shutdown()

    @property
    def sent(self) -> list[str]:
        return list(self.app.transport.sent_log)

    async def warmup(self) -> None:
        """`GO` 한 장 -- ACF 파싱·적용, 전원 ON.  운영자도 이 순서로 쓴다."""
        for line in WARMUP:
            self.app.transport.feed(line)
            await asyncio.sleep(0.02)
        await self.app.seq.wait()
        await asyncio.sleep(0.3)

    async def reply(self, line: str, word: str, timeout: float = 5.0) -> str:
        """명령 한 줄을 넣고 **그 커맨드워드의** `DONE`/`ERROR` 한 줄을 기다린다."""
        start = len(self.app.transport.sent_log)
        self.app.transport.feed(line)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            for s in self.app.transport.sent_log[start:]:
                if (' DONE: %s' % word) in s or (' ERROR: %s' % word) in s:
                    return s
            await asyncio.sleep(0.01)
        raise AssertionError('%s 응답이 %gs 안에 없다: %r'
                             % (word, timeout, self.app.transport.sent_log[start:]))


async def until(pred, timeout: float = 2.0, what: str = '') -> None:  # noqa: ANN001
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if pred():
            return
        await asyncio.sleep(0.01)
    raise AssertionError('%s 를 %gs 안에 못 봤다' % (what or 'condition', timeout))


def body_of(line: str) -> str:
    """`src>dst DONE: CMD body` -> `body`."""
    return line.split(' ', 3)[3] if line.count(' ') >= 3 else ''


def flush_flag(fake: FakeArchon) -> str | None:
    """가짜 설정 메모리의 `FirstFlush=` 줄 (없으면 None)."""
    for text in fake.config.values():
        if 'FirstFlush=' in text:
            return text
    return None


def run(coro):  # noqa: ANN001, ANN201
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# (a) CCDFLUSH
# ---------------------------------------------------------------------------

def test_ccdflush_flushes_both_and_rewinds_the_flag(tmp_path):  # noqa: ANN001
    """`CCDFLUSH` -> `DONE: CCDFLUSH Flushed=MK,NT` · 두 가짜의 `flushes` +1 · 설정 메모리
    `FirstFlush` 는 0 으로 되돌아온다 (안 되돌리면 다음 LOADPARAMS 가 유령 flush 를 되살린다
    -- DevNote 11.31)."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            await s.warmup()
            assert getattr(s.mk, 'flushes', 0) == 0, 'GO 가 flush 를 만들었다 -- 전제가 깨졌다'
            line = await s.reply('OBS>ICS CCDFLUSH', 'CCDFLUSH')
            assert line.endswith('DONE: CCDFLUSH Flushed=MK,NT'), line
            # flush 프레임은 독출 시간만큼 걸린다 -- DONE 뒤에 완료된다.
            await until(lambda: getattr(s.mk, 'flushes', 0) == 1
                        and getattr(s.nt, 'flushes', 0) == 1, what='flushes')
            assert flush_flag(s.mk) == 'PARAMETER0=FirstFlush=0', s.mk.config
            assert flush_flag(s.nt) == 'PARAMETER0=FirstFlush=0', s.nt.config
            # 프레임은 만들지 않는다
            assert s.mk.frame_no == 1
            return s.sent, s.app.emit.violations
    sent, violations = run(body())
    assert violations == [], violations


def test_ccdflush_one_controller_only(tmp_path):  # noqa: ANN001
    """`CCDFLUSH nt` (소문자) -- NT 만 비운다.  `Flushed=NT`."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            await s.warmup()
            line = await s.reply('OBS>ICS CCDFLUSH nt', 'CCDFLUSH')
            assert line.endswith('DONE: CCDFLUSH Flushed=NT'), line
            await until(lambda: getattr(s.nt, 'flushes', 0) == 1, what='NT flush')
            await asyncio.sleep(0.2)
            assert getattr(s.mk, 'flushes', 0) == 0, 'MK 도 비웠다'
    run(body())


def test_ccdflush_rejects_a_bad_argument(tmp_path):  # noqa: ANN001
    """모르는 태그·인자 둘 -- usage.  ⭐ 태그 나열은 살아 있는 컨트롤러다."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            await s.warmup()
            for cmd in ('CCDFLUSH XX', 'CCDFLUSH MK NT'):
                line = await s.reply('OBS>ICS ' + cmd, 'CCDFLUSH')
                assert line.endswith('ERROR: CCDFLUSH usage: CCDFLUSH [MK|NT|ALL]'), line
            assert 'LOADPARAMS' not in s.mk.seen[-3:], s.mk.seen[-3:]
    run(body())


def test_ccdflush_before_any_go_says_why(tmp_path):  # noqa: ANN001
    """⚠️ 첫 `GO` 전에는 ACF 줄 번호가 없어 `WCONFIG` 를 못 쓴다.

    `flush_now()` 는 그 상태를 *"ACF has no FirstFlush parameter"* 로 말하는데 그것은
    증상이다 -- 디스패처가 먼저 걸러 **원인**(이 세션에서 ACF 미적재)을 말한다.
    """
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            line = await s.reply('OBS>ICS CCDFLUSH', 'CCDFLUSH')
            assert line.endswith('ERROR: CCDFLUSH Failed: ACF not loaded on MK,NT in '
                                 'this session -- run GO once first'), line
            assert 'LOADPARAMS' not in s.mk.seen
    run(body())


# ---------------------------------------------------------------------------
# (b) CCDPOWOFF / CCDPOWON
# ---------------------------------------------------------------------------

def test_ccdpow_toggles_power_and_reports_it(tmp_path):  # noqa: ANN001
    """`CCDPOWOFF` -> `Power=OFF Controllers=MK,NT`, 가짜 `powered` False;
    `CCDPOWON` -> `Power=ON …`, True.  `POWER` 필드도 따라 움직인다 (가짜 모사)."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            await s.warmup()
            assert s.mk.powered and s.nt.powered
            line = await s.reply('OBS>ICS CCDPOWOFF', 'CCDPOWOFF')
            assert line.endswith('DONE: CCDPOWOFF Power=OFF Controllers=MK,NT'), line
            assert not s.mk.powered and not s.nt.powered
            assert s.mk.status['POWER'] == '2'          # Off (p.47)
            line = await s.reply('OBS>ICS CCDPOWON', 'CCDPOWON')
            assert line.endswith('DONE: CCDPOWON Power=ON Controllers=MK,NT'), line
            assert s.mk.powered and s.nt.powered
            assert s.mk.status['POWER'] == '4'
            return s.app.emit.violations
    assert run(body()) == []


def test_ccdpowoff_one_controller(tmp_path):  # noqa: ANN001
    """`CCDPOWOFF MK` -- NT 는 그대로."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            await s.warmup()
            line = await s.reply('OBS>ICS CCDPOWOFF MK', 'CCDPOWOFF')
            assert line.endswith('DONE: CCDPOWOFF Power=OFF Controllers=MK'), line
            assert not s.mk.powered and s.nt.powered
    run(body())


def test_ccdpowon_refused_by_the_controller_is_an_error_in_ascii(tmp_path):  # noqa: ANN001
    """⚠️ 실기는 이 세션에 `APPLYALL` 이 없으면 `POWERON` 을 `?xx` 로 거부한다 (매뉴얼
    p.51, DevNote 10.2).  가짜 `applied=False` 가 그 상태다.

    `controller.power_on()` 의 진단 문구는 한글이라 와이어에서는 `?` 가 된다 -- 그래도
    **ASCII 한 줄**이어야 하고 `(see log)` 로 원문이 로그에 있음을 알린다.
    """
    async def body():  # noqa: ANN202
        async with Session(tmp_path, applied=False) as s:
            line = await s.reply('OBS>ICS CCDPOWON', 'CCDPOWON')
            assert ' ERROR: CCDPOWON Failed: ' in line, line
            assert line.isascii(), line
            assert '(see log)' in line, line
            assert not s.mk.powered
    run(body())


def test_ccdpowoff_not_confirmed_is_not_reported_as_done(tmp_path):  # noqa: ANN001
    """`controller.power_off()` 는 실패를 **올리지 않고** 로그만 남긴다 (`finally` 자리용).
    그대로 `DONE` 을 내면 전원이 살아 있는데 *OFF* 라고 답한다 -- 상태로 판정한다."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path, reject=('POWEROFF',)) as s:
            await s.warmup()
            assert s.mk.powered
            line = await s.reply('OBS>ICS CCDPOWOFF', 'CCDPOWOFF')
            assert line.endswith('ERROR: CCDPOWOFF Failed: POWEROFF not confirmed on '
                                 'MK,NT (see log)'), line
            assert s.mk.powered, '가짜가 거부했는데 상태가 바뀌었다'
    run(body())


# ---------------------------------------------------------------------------
# (c) ARCHON 바이패스
# ---------------------------------------------------------------------------

def test_archon_status_returns_the_raw_reply(tmp_path):  # noqa: ANN001
    """`ARCHON MK STATUS` -> `DONE: ARCHON MK VALID=1 COUNT=… POWERGOOD=1 …`."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            line = await s.reply('OBS>ICS ARCHON MK STATUS', 'ARCHON')
            assert ' DONE: ARCHON MK ' in line, line
            body_ = body_of(line)
            # 가짜 `FULL_STATUS` 의 첫 필드가 `POWERGOOD` 이고 `VALID` 는 뒤에 붙는다
            assert body_.startswith('MK POWERGOOD=1 '), body_
            assert 'VALID=1' in body_ and 'BACKPLANE_TEMP=' in body_, body_
            return s.app.emit.violations
    assert run(body()) == []


def test_archon_tag_is_case_insensitive_and_text_is_verbatim(tmp_path):  # noqa: ANN001
    """`ARCHON nt system` -- 태그는 대소문자 무관, 원문은 그대로 나간다 (가짜는 `SYSTEM`
    만 안다 -- 소문자 `system` 은 빈 성공으로 답하므로 원문 보존이 그대로 드러난다)."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            line = await s.reply('OBS>ICS ARCHON nt SYSTEM', 'ARCHON')
            assert body_of(line).startswith('NT BACKPLANE_TYPE=1 '), line
            assert 'SYSTEM' in s.nt.seen and 'SYSTEM' not in s.mk.seen
            # 원문 그대로 -- 소문자는 가짜가 모르는 명령이라 빈 응답
            line = await s.reply('OBS>ICS ARCHON NT system', 'ARCHON')
            assert line.endswith('DONE: ARCHON NT <empty reply>'), line
            assert s.nt.seen[-1] == 'system', s.nt.seen[-3:]
    run(body())


def test_archon_rejected_is_an_error_not_a_done(tmp_path):  # noqa: ANN001
    """컨트롤러가 `?xx` 로 거부하면 `ERROR: ARCHON <tag> rejected: <원문>`."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path, reject=('BOGUS',)) as s:
            line = await s.reply('OBS>ICS ARCHON MK BOGUS 1 2', 'ARCHON')
            assert line.endswith('ERROR: ARCHON MK rejected: BOGUS 1 2'), line
    run(body())


def test_archon_long_reply_is_truncated_and_logged_in_full(tmp_path, caplog):  # noqa: ANN001
    """`STATUS` 는 ~2 KB 다 -- 한 메시지 상한(2048) 안에 들도록 잘라 꼬리를 붙이고,
    **전문은 `log.info`** 로 남긴다."""
    caplog.set_level(logging.INFO, logger='ics_archon.app')
    padded = dict(FULL_STATUS, **{'PAD%03d' % i: 'x' * 24 for i in range(100)})

    async def body():  # noqa: ANN202
        async with Session(tmp_path, status=padded) as s:
            line = await s.reply('OBS>ICS ARCHON MK STATUS', 'ARCHON')
            return line, s.app.emit.violations
    line, violations = run(body())
    assert violations == []
    assert len(line) <= MAX_LEN, len(line)
    assert ' ...(+' in line and ' bytes truncated, see log)' in line, line[-80:]
    kept = body_of(line).split(' ...(+')[0]
    assert len(kept) <= len('MK ') + ARCHON_REPLY_MAX
    full = [r.message for r in caplog.records if 'ARCHON MK' in r.message and 'PAD099=' in r.message]
    assert full, '전문이 로그에 없다'


# ---------------------------------------------------------------------------
# (d) ARCHON usage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('cmd', ['ARCHON', 'ARCHON MK', 'ARCHON XX STATUS',
                                 'ARCHON STATUS'])
def test_archon_usage_errors(tmp_path, cmd):  # noqa: ANN001
    """태그가 빠졌거나 모르거나 명령이 비면 usage.  컨트롤러에는 아무것도 안 나간다."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            before = list(s.mk.seen), list(s.nt.seen)
            line = await s.reply('OBS>ICS ' + cmd, 'ARCHON')
            assert line.endswith('ERROR: ARCHON usage: ARCHON <MK|NT> <command>'), line
            await asyncio.sleep(0.05)
            assert (list(s.mk.seen), list(s.nt.seen)) == before
    run(body())


# ---------------------------------------------------------------------------
# (e) 취득 중이면 거부
# ---------------------------------------------------------------------------

def test_all_four_are_refused_while_acquiring(tmp_path):  # noqa: ANN001
    """`seq.busy` 가 참이면 넷 다 `Exposure in progress -- ABORT first` -- 컨트롤러에는
    아무것도 안 나간다 (진행 중 노출 위의 LOADPARAMS/POWEROFF/RESETTIMING 은 자료를 망친다)."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            await s.warmup()
            seq_cls = type(s.app.seq)
            keep = seq_cls.busy
            seq_cls.busy = property(lambda self: True)
            try:
                before = list(s.mk.seen), list(s.nt.seen)
                for cmd, word in (('CCDFLUSH', 'CCDFLUSH'), ('CCDPOWON MK', 'CCDPOWON'),
                                  ('CCDPOWOFF', 'CCDPOWOFF'),
                                  ('ARCHON MK RESETTIMING', 'ARCHON')):
                    line = await s.reply('OBS>ICS ' + cmd, word)
                    assert line.endswith('ERROR: %s %s' % (word, BUSY_TEXT)), line
                await asyncio.sleep(0.05)
                assert (list(s.mk.seen), list(s.nt.seen)) == before
                assert s.mk.powered
            finally:
                seq_cls.busy = keep
            return s.app.emit.violations
    assert run(body()) == []


def test_go_is_refused_while_an_operator_command_is_in_flight(tmp_path):  # noqa: ANN001
    """⭐ 반대 방향 -- `ARCHON MK STATUS` 가 도는 동안(가짜가 STATUS 를 0.5 s 늦춘다) 들어온
    `GO` 는 거부된다.  `CCDPOWOFF` 의 POWEROFF 가 아직 안 나갔는데 GO 가 `prepare()` 를
    지나면 노출 도중에 전원이 내려가는 것을 막는 자리다."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path, status_delay=0.5) as s:
            s.app.transport.feed('OBS>ICS dark begin')
            s.app.transport.feed('OBS>ICS exp 1')
            await asyncio.sleep(0.02)
            start = len(s.app.transport.sent_log)
            s.app.transport.feed('OBS>ICS ARCHON MK STATUS')
            await asyncio.sleep(0.05)
            line = await s.reply('OBS>ICS go', 'GO', timeout=0.3)
            assert line.endswith('ERROR: GO Operator command in progress (ARCHON) -- '
                                 'retry when it is DONE'), line
            assert not s.app.seq.busy
            # 바이패스는 그 뒤 정상 완료된다
            await until(lambda: any(' DONE: ARCHON MK ' in x
                                    for x in s.app.transport.sent_log[start:]),
                        timeout=3.0, what='ARCHON DONE')
            # 그리고 이제 GO 는 받는다 (성공한 GO 는 `noop` -- 시퀀서가 곧바로 busy 다)
            s.app.transport.feed('OBS>ICS go')
            await until(lambda: s.app.seq.busy, timeout=1.0, what='seq.busy')
            await s.app.seq.wait()
            await asyncio.sleep(0.3)
            assert any('Acquisition Complete.' in x for x in s.sent), s.sent[-5:]
    run(body())


def test_no_hardware_backend_is_an_error_not_a_silent_done(tmp_path):  # noqa: ANN001
    """`--backend sim` 에는 원시 함수가 없다 -- 조용히 `DONE` 을 내면 *"먹었는데 아무것도
    안 바뀜"* 이 된다."""
    async def body():  # noqa: ANN202
        cfg, acfg = make_cfgs(tmp_path, 4242)
        cfg.hardware.backend = 'sim'
        app = IcsArchon(cfg, acfg)
        await app.start()
        try:
            for cmd, word in (('CCDFLUSH', 'CCDFLUSH'), ('CCDPOWON', 'CCDPOWON'),
                              ('CCDPOWOFF', 'CCDPOWOFF'), ('ARCHON MK STATUS', 'ARCHON')):
                start = len(app.transport.sent_log)
                app.transport.feed('OBS>ICS ' + cmd)
                await asyncio.sleep(0.05)
                got = [x for x in app.transport.sent_log[start:] if word in x]
                assert got and got[0].endswith(
                    'ERROR: %s Controller is not available (no hardware backend)' % word), got
        finally:
            await app.stop()
    run(body())


# ---------------------------------------------------------------------------
# (f) 발신 위생
# ---------------------------------------------------------------------------

def test_the_vocabulary_is_registered_and_would_cry_without_it(monkeypatch):  # noqa: ANN001
    """`emitter.validate()` 는 `KNOWN_COMMANDS` 밖의 커맨드워드를 `unknown_cmdword` 로 운다
    (`emitter.py:170`, Emitter 는 그것을 `message hygiene violation` 경고 + `violations`
    누적으로 낸다).  등록을 빼면 실제로 그렇게 우는지 먼저 보고, 등록하면 조용한지 본다."""
    lines = [
        ('ICS>OBS DONE: CCDFLUSH Flushed=MK,NT', 'CCDFLUSH'),
        ('ICS>OBS DONE: CCDPOWON Power=ON Controllers=MK,NT', 'CCDPOWON'),
        ('ICS>OBS DONE: CCDPOWOFF Power=OFF Controllers=MK', 'CCDPOWOFF'),
        ('ICS>OBS DONE: ARCHON MK VALID=1 COUNT=101 LOG=0 POWER=4', 'ARCHON'),
        ('ICS>OBS DONE: ARCHON NT <empty reply>', 'ARCHON'),
        ('ICS>OBS ERROR: ARCHON usage: ARCHON <MK|NT> <command>', 'ARCHON'),
        ('ICS>OBS ERROR: ARCHON MK rejected: RESETTIMING', 'ARCHON'),
        ('ICS>OBS ERROR: CCDFLUSH %s' % BUSY_TEXT, 'CCDFLUSH'),
        # ⚠️ 커맨드워드를 본문 첫 토큰에 두면 등록 뒤에 `stacked_cmdword` 로 운다 --
        # 그래서 괄호 안에 넣었다 (`ERROR: GO CCDPOWON in progress …` 는 안 된다).
        ('ICS>OBS ERROR: GO Operator command in progress (CCDPOWON) -- retry when it is DONE',
         'GO'),
    ]
    # 등록이 없는 어휘로 되돌려 본다 -- 넷 다 운다 (GO 는 원래 어휘라 조용하다)
    monkeypatch.setattr(emitter, 'KNOWN_COMMANDS',
                        frozenset(emitter.KNOWN_COMMANDS - ICS_OPS_COMMANDS))
    crying = [(l, emitter.validate(l, w)) for l, w in lines]
    assert [p for _, p in crying if p] == [['unknown_cmdword']] * 8, crying
    # 등록하면 조용하다 -- 그리고 다른 위생 항목(stacked/repeated/type_in_body)도 없다
    extend_vocabulary()
    assert ICS_OPS_COMMANDS <= emitter.KNOWN_COMMANDS
    quiet = [(l, emitter.validate(l, w)) for l, w in lines]
    assert all(not p for _, p in quiet), quiet


def test_wire_text_is_ascii_one_line():
    """비ASCII 는 `?`, 개행·제어문자는 공백 하나로 -- 잘림 길이를 바이트로 셀 수 있다."""
    assert wire_text('MK: 연결이 없다\r\nA\tB') == 'MK: ??? ?? A B'
    assert wire_text('  VALID=1   COUNT=2  ') == 'VALID=1 COUNT=2'
    assert wire_text('').isascii() and wire_text('') == ''

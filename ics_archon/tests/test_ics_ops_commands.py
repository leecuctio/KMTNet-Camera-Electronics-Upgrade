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

#: 파라미터 셋 -- 실물 ACF 와 같은 자리다.  ⭐ 슬롯 **번호**는 이제 설정이
#: 아니라 **ACF 에서 이름으로 찾는다** (`controller._find_param_slots`,
#: 2026-09-12).  그래서 여기 번호가 밀려도 코드가 따라간다.
ACF_TEXT = """[CONFIG]
TRIGOUTFORCE=0
TRIGOUTLEVEL=0
PARAMETER0="FirstFlush=0"
PARAMETER1="IntMS=0"
PARAMETER2="Exposures=0"
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
            # ⭐ 예열 GO 가 flush 를 **한 번** 만든다 (2026-09-15, DevNote 11.93): 하네스에는
            # ICG 가 없어 HKDATA 답이 없고 추적 상태가 UNKNOWN 이라 `VACGAUGE OFF` 를 보내며,
            # 그러면 첫 장 앞에 FirstFlush 1 이 실린다.  그래서 **차분**으로 센다.
            mk0, nt0 = getattr(s.mk, 'flushes', 0), getattr(s.nt, 'flushes', 0)
            assert mk0 == nt0 == 1, '예열 GO 의 첫 장 flush 가 한 번이어야 한다'
            line = await s.reply('OBS>ICS CCDFLUSH', 'CCDFLUSH')
            assert line.endswith('DONE: CCDFLUSH Flushed=MK,NT'), line
            # flush 프레임은 독출 시간만큼 걸린다 -- DONE 뒤에 완료된다.
            await until(lambda: getattr(s.mk, 'flushes', 0) == mk0 + 1
                        and getattr(s.nt, 'flushes', 0) == nt0 + 1, what='flushes')
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
            mk0, nt0 = getattr(s.mk, 'flushes', 0), getattr(s.nt, 'flushes', 0)
            line = await s.reply('OBS>ICS CCDFLUSH nt', 'CCDFLUSH')
            assert line.endswith('DONE: CCDFLUSH Flushed=NT'), line
            await until(lambda: getattr(s.nt, 'flushes', 0) == nt0 + 1, what='NT flush')
            await asyncio.sleep(0.2)
            assert getattr(s.mk, 'flushes', 0) == mk0, 'MK 도 비웠다'
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

    ⭐ `controller.power_on()` 의 진단 문구는 **ASCII 영문**이고 예외 원문(`protocol` 의
    한글 문면)은 싣지 않는다 -- 거절 코드(`reply ?xx`)만 싣는다 (DevNote 11.96).  종전에는
    원문이 끼어 와이어에서 `?` 로 뭉개지고 `(see log)` 가 붙었다.
    """
    async def body():  # noqa: ANN202
        async with Session(tmp_path, applied=False) as s:
            line = await s.reply('OBS>ICS CCDPOWON', 'CCDPOWON')
            assert ' ERROR: CCDPOWON Failed: ' in line, line
            assert line.isascii(), line
            assert 'refused POWERON (reply ?' in line, line
            assert '(see log)' not in line, '진단 문면에 비ASCII 가 새 들어왔다: %s' % line
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

def test_three_are_refused_while_acquiring_and_archon_is_not(tmp_path):  # noqa: ANN001
    """`seq.busy` 가 참이면 셋은 `Exposure in progress -- ABORT first` -- 컨트롤러에는
    아무것도 안 나간다 (진행 중 노출 위의 LOADPARAMS/POWEROFF 는 자료를 망친다).
    ⭐ `ARCHON` 은 제한이 없다 (운영자 2026-09-05 "제한 없이 모두 풀어줘") -- 취득 중에도
    원문이 나가고 `DONE` 이 온다."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            await s.warmup()
            seq_cls = type(s.app.seq)
            keep = seq_cls.busy
            seq_cls.busy = property(lambda self: True)
            try:
                before = list(s.mk.seen), list(s.nt.seen)
                for cmd, word in (('CCDFLUSH', 'CCDFLUSH'), ('CCDPOWON MK', 'CCDPOWON'),
                                  ('CCDPOWOFF', 'CCDPOWOFF')):
                    line = await s.reply('OBS>ICS ' + cmd, word)
                    assert line.endswith('ERROR: %s %s' % (word, BUSY_TEXT)), line
                await asyncio.sleep(0.05)
                assert (list(s.mk.seen), list(s.nt.seen)) == before
                assert s.mk.powered
                # ⭐ ARCHON 은 취득 중에도 나간다 -- 원문이 컨트롤러에 닿고 DONE 이 온다.
                line = await s.reply('OBS>ICS ARCHON MK STATUS', 'ARCHON')
                assert ' DONE: ARCHON MK ' in line, line
                assert any(c.upper().startswith('STATUS') for c in s.mk.seen[len(before[0]):]), \
                    s.mk.seen[len(before[0]):]
            finally:
                seq_cls.busy = keep
            return s.app.emit.violations
    assert run(body()) == []


def test_go_is_refused_while_an_operator_command_is_in_flight(tmp_path, monkeypatch):  # noqa: ANN001
    """⭐ 반대 방향 -- `CCDPOWON MK` 가 도는 동안(`power_ccd` 를 0.5 s 늦춘다) 들어온 `GO` 는
    거부된다.  `CCDPOWOFF` 의 POWEROFF 가 아직 안 나갔는데 GO 가 `prepare()` 를 지나면
    노출 도중에 전원이 내려가는 것을 막는 자리다.  (종전에는 `ARCHON MK STATUS` 로 걸었는데
    `ARCHON` 은 2026-09-05 에 제한을 풀어 `GO` 를 막지 않는다 -- 아래 시험이 그것을 본다.)"""
    async def body():  # noqa: ANN202
        async with Session(tmp_path) as s:
            be_cls = type(s.app.backend)
            real = be_cls.power_ccd

            async def slow(self, *a, **kw):  # noqa: ANN001, ANN002, ANN003, ANN202
                await asyncio.sleep(0.5)
                return await real(self, *a, **kw)

            monkeypatch.setattr(be_cls, 'power_ccd', slow)
            s.app.transport.feed('OBS>ICS dark begin')
            s.app.transport.feed('OBS>ICS exp 1')
            await asyncio.sleep(0.02)
            start = len(s.app.transport.sent_log)
            s.app.transport.feed('OBS>ICS CCDPOWON MK')
            await asyncio.sleep(0.05)
            line = await s.reply('OBS>ICS go', 'GO', timeout=0.3)
            assert line.endswith('ERROR: GO Operator command in progress (CCDPOWON) -- '
                                 'retry when it is DONE'), line
            assert not s.app.seq.busy
            # 전원 명령은 그 뒤 정상 완료된다
            await until(lambda: any(' DONE: CCDPOWON ' in x
                                    for x in s.app.transport.sent_log[start:]),
                        timeout=3.0, what='CCDPOWON DONE')
            # 그리고 이제 GO 는 받는다 (성공한 GO 는 `noop` -- 시퀀서가 곧바로 busy 다)
            s.app.transport.feed('OBS>ICS go')
            await until(lambda: s.app.seq.busy, timeout=1.0, what='seq.busy')
            await s.app.seq.wait()
            await asyncio.sleep(0.3)
            assert any('Acquisition Complete.' in x for x in s.sent), s.sent[-5:]
    run(body())


def test_archon_in_flight_does_not_block_go(tmp_path):  # noqa: ANN001
    """⭐ `ARCHON MK STATUS` 가 도는 동안(가짜가 STATUS 를 0.5 s 늦춘다) 들어온 `GO` 는
    **받는다** -- `ARCHON` 은 `_op_inflight` 를 잡지 않는다 (운영자 2026-09-05 "제한 없이
    모두 풀어줘").  바이패스도 그 뒤 정상 완료된다."""
    async def body():  # noqa: ANN202
        async with Session(tmp_path, status_delay=0.5) as s:
            s.app.transport.feed('OBS>ICS dark begin')
            s.app.transport.feed('OBS>ICS exp 1')
            await asyncio.sleep(0.02)
            start = len(s.app.transport.sent_log)
            s.app.transport.feed('OBS>ICS ARCHON MK STATUS')
            await asyncio.sleep(0.05)
            s.app.transport.feed('OBS>ICS go')
            await until(lambda: s.app.seq.busy, timeout=1.0, what='seq.busy')
            assert not any('ERROR: GO' in x for x in s.app.transport.sent_log[start:]), \
                s.app.transport.sent_log[start:]
            await until(lambda: any(' DONE: ARCHON MK ' in x
                                    for x in s.app.transport.sent_log[start:]),
                        timeout=3.0, what='ARCHON DONE')
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


# -- 셔터 (Trigger Out) ----------------------------------------------------
#
# ⭐ **순서가 곧 규범이다** (운영자 확정 2026-09-09).  science 의 Trigger Out 은
# **실제 셔터**를 몰고, 평시 `TRIGOUTFORCE=0`(타이밍 스크립트가 몬다)이다.
#
#   SHOPEN <초> : LEVEL=1 + FORCE=1   (한 적용)
#   SHCLOSE     : LEVEL=0 + FORCE=0   (한 적용 -- 스크립트에 돌려준다)
#
# ⭐ **노출을 방해하지 않는 것이 우선**이다 (운영자 확정 2026-09-09).  무장
# (`LEVEL=0`+`FORCE=1`)을 앞세우면 그 한 적용 동안 핀이 강제 LOW 라 **노출 중
# 셔터가 잠깐 닫힌다** -- 그래서 둘을 같이 세운다.
# ⚠️ 대가: 에지를 보장하지 않고, `SHCLOSE` 도 적분 중이면 안 닫힌다.


def _trig_trace(fake, start: int) -> list[str]:  # noqa: ANN001
    """가짜가 받은 명령에서 **TRIGOUT 관련 자취**만 뽑는다 (순서 그대로)."""
    out = []
    for c in fake.seen[start:]:
        if 'TRIGOUTLE' in c:
            out.append('LEVEL')
        elif 'TRIGOUTFO' in c:
            out.append('FORCE')
        elif c.startswith('APPLYSYSTEM'):
            out.append('APPLY')
    return out


def _shutter_fake(ses):  # noqa: ANN001, ANN202
    """셔터를 모는 컨트롤러의 가짜 -- ACF 배선이 정한다."""
    be = ses.app.backend
    tags = [t for t in be.ctrls if be.acfg.drives_shutter(t)]
    assert tags, '셔터를 모는 컨트롤러가 없다 -- 시험 전제가 깨졌다'
    return ses.mk if tags[0] == 'MK' else ses.nt


def test_shopen_raises_both_in_one_apply(tmp_path):
    """⭐ `LEVEL=1`+`FORCE=1` 을 **한 적용**에 -- 노출을 안 끊는다.

    ⛔ 무장을 앞세우면(`LEVEL=0`+`FORCE=1` 먼저) 그 한 적용 동안 핀이 강제 LOW 라
    **노출 중 셔터가 잠깐 닫힌다**.  운영자가 그것을 피하는 쪽을 골랐다
    (2026-09-09) -- 이미 열려 있었다면 **그대로 열린 채**로 넘어간다.
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            fake = _shutter_fake(ses)
            n = len(fake.seen)
            ses.app.transport.feed('abc>ICS SHOPEN 20')
            await until(lambda: _trig_trace(fake, n).count('APPLY') >= 1,
                        what='SHOPEN 의 적용')
            return _trig_trace(fake, n)

    trace = asyncio.run(run())
    assert trace[:3] == ['LEVEL', 'FORCE', 'APPLY'], trace


def test_shclose_hands_the_line_back_in_one_apply(tmp_path):
    """⭐ `LEVEL=0`+`FORCE=0` 을 **한 적용**에 -- 선을 스크립트에 돌려준다.

    ⚠️ **적분 중이면 셔터가 안 닫힌다** -- 스크립트가 그 선을 HIGH 로 몰고
    있기 때문이고, 그것이 운영자가 고른 동작이다 (2026-09-09): 노출 중
    `SHCLOSE` 가 자료를 끊지 않는다.
    ⛔ 적분을 끊는 것은 `ABORT` 의 `abort_now()`(`Exposures=0` -> `RESETTIMING`)다 --
    `STOP` 은 안 끊는다.  `close_shutter()` 의 `FORCE=1`+`LEVEL=0` 은 호스트 카운트다운이
    먼저 끝났을 때 빛만 끊는다.
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            fake = _shutter_fake(ses)
            n = len(fake.seen)
            got = await ses.reply('abc>ICS SHCLOSE', 'SHCLOSE')
            return _trig_trace(fake, n), got

    trace, got = asyncio.run(run())
    assert trace == ['LEVEL', 'FORCE', 'APPLY'], trace
    assert 'Shutter=Closed' in got, got


def test_abort_cuts_the_integration_at_the_controller(tmp_path):
    r"""⛔ **ABORT 는 적분을 실제로 끊어야 한다** (운영자 지시 2026-09-09).

    종전에는 시퀀서가 태스크만 취소해서 **컨트롤러의 노출이 물리적으로 끝까지
    갔다** -- 프레임만 안 쓸 뿐 셔터도 `NoIntMS` 까지 열려 있었다.
    ⭐ 순서가 뜻이다: `Exposures=0`(LOADPARAMS) **먼저**, 그다음 `RESETTIMING`.
    `Start:` 둘째 줄이 `IF Exposures GOTO Exposure` 라, 남아 있으면 코어가
    곧바로 다음 노출을 시작한다.
    ⭐ 셔터는 이것만으로 닫힌다 -- `Start:` 첫 줄 상태 `RESET` 이 6비트를 전부
    0 으로 몬다 (ACF `STATE0\CONTROL="0,0"`).
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            fake = _shutter_fake(ses)
            n = len(fake.seen)
            ses.app.transport.feed('abc>ICS go 2')
            await asyncio.sleep(0.3)
            await ses.reply('abc>ICS abort', 'ABORT')
            await until(lambda: 'RESETTIMING' in fake.seen[n:],
                        what='ABORT 의 RESETTIMING')
            return fake.seen[n:]

    seen = asyncio.run(run())
    reset = seen.index('RESETTIMING')
    loads = [i for i, c in enumerate(seen[:reset]) if c == 'LOADPARAMS']
    assert loads, 'RESETTIMING 앞에 LOADPARAMS 가 없다 -- Exposures=0 을 안 걸었다'


def test_abort_closes_a_shutter_left_open_by_shopen(tmp_path):
    """⛔ **ABORT 는 `SHOPEN` 이 열어 둔 셔터를 닫고 가야 한다** (운영자 2026-09-09).

    `abort_now()` 의 `RESETTIMING` 은 **타이밍 코어만** 되돌리는데, `SHOPEN`
    중에는 `TRIGOUTFORCE=1` 이라 핀이 코어를 안 따라간다 -- 종전에는 타이머가
    `<초>` 뒤에 쓸 때까지 **셔터가 강제로 열린 채** 남았다.
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            fake = _shutter_fake(ses)
            ses.app.transport.feed('abc>ICS SHOPEN 20')
            await until(lambda: 'APPLYSYSTEM' in fake.seen[-4:],
                        what='SHOPEN 의 적용')
            n = len(fake.seen)
            ses.app.transport.feed('abc>ICS abort')
            await until(lambda: _trig_trace(fake, n).count('APPLY') >= 1,
                        what='ABORT 의 내림')
            return _trig_trace(fake, n)

    trace = asyncio.run(run())
    assert trace[:3] == ['LEVEL', 'FORCE', 'APPLY'], trace


# -- C1TRIGOUT / C2TRIGOUT (운영자 2026-09-12) -----------------------------
#
# ⭐ `SHOPEN`/`SHCLOSE` 와 갈라 둔 까닭: 그 둘은 *"셔터를 연다"* 라 `shutter_ctrl`
# 이 지정한 컨트롤러만 움직이는데, `CnTRIGOUT` 은 *"이 컨트롤러의 핀을 움직인다"*
# 라서 **지정 여부와 무관**하다 -- 배선 점검과 예비 유닛 시험에 그 길이 필요하다.
# ⚠️ 단위가 다르다 -- `SHOPEN` 은 **초**, `CnTRIGOUT` 은 **밀리초**.


def _cfg_value(fake, key):  # noqa: ANN001, ANN202
    """가짜의 **설정 메모리**에서 한 줄의 값 (줄 번호가 아니라 키로)."""
    for text in fake.config.values():
        if text.startswith(key + '='):
            return text.split('=', 1)[1]
    return None


def test_cntrigout_moves_the_unit_that_does_not_drive_the_shutter(tmp_path):
    """⭐⭐ **`shutter_ctrl` 이 안 고른 유닛도 움직인다** -- 이 명령의 존재 이유다.

    배포 ini 는 `shutter_ctrl = MK` 라 `SHOPEN` 은 NT 를 안 건드리는데,
    `C2TRIGOUT` 은 건드려야 한다.
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            be = ses.app.backend
            # 전제: MK 만 셔터를 몬다
            assert be.acfg.drives_shutter('MK')
            assert not be.acfg.drives_shutter('NT')
            n = len(ses.nt.seen)
            ses.app.transport.feed('abc>ICS C2TRIGOUT 50')
            await until(lambda: _trig_trace(ses.nt, n).count('APPLY') >= 1,
                        what='C2TRIGOUT 의 적용')
            return _trig_trace(ses.nt, n), _cfg_value(ses.nt, 'TRIGOUTLEVEL')

    trace, level = asyncio.run(run())
    # 올림은 `LEVEL=1`+`FORCE=1` 을 한 적용에 (SHOPEN 과 같은 알맹이)
    assert trace[:3] == ['LEVEL', 'FORCE', 'APPLY'], trace
    assert level == '1', level


def test_cntrigout_rests_where_the_unit_belongs(tmp_path):
    """⭐ 내려갈 **쉬는 상태가 갈린다** (운영자 규범 2026-09-12).

    | | `TRIGOUTLEVEL` | `TRIGOUTFORCE` |
    |---|---|---|
    | 셔터를 **모는** MK | `0` | `0` (스크립트에 돌려준다) |
    | **안 모는** NT | `0` | `1` (우리가 붙든다) |

    ⛔ 안 모는 쪽을 `FORCE=0` 으로 돌려주면 그 핀이 자기 타이밍 스크립트를
    따라가 노출마다 흔들린다.
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            for word, fake in (('C1TRIGOUT', ses.mk), ('C2TRIGOUT', ses.nt)):
                n = len(fake.seen)
                ses.app.transport.feed('abc>ICS %s 0' % word)
                await until(
                    lambda f=fake, k=n: _trig_trace(f, k).count('APPLY') >= 1,
                    what='%s 의 적용' % word)
            return (_cfg_value(ses.mk, 'TRIGOUTFORCE'),
                    _cfg_value(ses.mk, 'TRIGOUTLEVEL'),
                    _cfg_value(ses.nt, 'TRIGOUTFORCE'),
                    _cfg_value(ses.nt, 'TRIGOUTLEVEL'))

    mk_force, mk_level, nt_force, nt_level = asyncio.run(run())
    assert (mk_force, mk_level) == ('0', '0'), (mk_force, mk_level)
    assert (nt_force, nt_level) == ('1', '0'), (nt_force, nt_level)


def test_cntrigout_rejects_a_bad_duration(tmp_path):
    """⛔ 인자를 **기본값으로 떨어뜨리지 않는다** -- 없거나 이상하면 거절."""
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            out = []
            for body in ('', ' abc', ' -1'):
                ses.app.transport.feed('abc>ICS C1TRIGOUT%s' % body)
                await until(lambda n=len(out): len(
                    [m for m in ses.sent if 'ERROR' in m
                     and 'C1TRIGOUT' in m]) > n,
                    what='C1TRIGOUT 거절')
                out.append(1)
            return [m for m in ses.sent if 'ERROR' in m and 'C1TRIGOUT' in m]

    errs = asyncio.run(run())
    assert len(errs) == 3, errs
    assert any('Missing duration' in m for m in errs), errs
    assert sum('Invalid duration' in m for m in errs) == 2, errs


def test_cntrigout_is_registered_in_the_ics_vocabulary():
    """⭐ 발신 어휘에 등록돼야 `emitter.validate()` 가 안 운다."""
    from ics_archon.app import ICS_OPS_COMMANDS
    assert {'C1TRIGOUT', 'C2TRIGOUT'} <= ICS_OPS_COMMANDS


# -- 펄스를 끊는 자리 (DevNote 11.96) --------------------------------------
#
# ⭐ **끊는 쪽이 선을 책임진다** -- `ABORT`·종료(`release_pulse`), 다음 명령, 그리고
# 셔터를 모는 컨트롤러에서는 `SHOPEN`/`SHCLOSE` 와 `CnTRIGOUT` 이 서로를.
# ⚠️ 하네스 `time_scale` 은 0.02 다 -- `C1TRIGOUT 500000` 은 10 s, `SHOPEN 500` 도 10 s.


def _rest_values(fake):  # noqa: ANN001, ANN202
    return _cfg_value(fake, 'TRIGOUTLEVEL'), _cfg_value(fake, 'TRIGOUTFORCE')


def test_shutdown_rests_a_running_cntrigout_pulse(tmp_path):
    """⛔ **종료가 `C1TRIGOUT`/`C2TRIGOUT` 펄스를 끊고 쉬는 상태로 내린다**.

    종전 `release_pulse` 는 `SHOPEN` 타이머만 봐서, `CnTRIGOUT` 중에 종료하면
    `super().stop()` 의 취소가 내림을 건너뛰어 `TRIGOUTLEVEL=1`·`FORCE=1` 이 설정 메모리에
    남았다 -- 셔터를 모는 MK 면 사람 없는 채로 **셔터가 열린 채** 끝난다.
    ⭐ 각자 **자기 쉬는 상태**로 간다: 셔터를 모는 MK `('0','0')`, 안 모는 NT `('0','1')`.
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            for word, fake in (('C1TRIGOUT', ses.mk), ('C2TRIGOUT', ses.nt)):
                n = len(fake.seen)
                ses.app.transport.feed('abc>ICS %s 500000' % word)
                await until(lambda f=fake, k=n: _trig_trace(f, k).count('APPLY') >= 1,
                            what='%s 의 올림' % word)
            raised = (_rest_values(ses.mk), _rest_values(ses.nt))
        # `__aexit__` 가 `app.stop()` -> `release_pulse('shutdown')` 을 지났다.
        return raised, _rest_values(ses.mk), _rest_values(ses.nt)

    raised, mk, nt = asyncio.run(run())
    assert raised == (('1', '1'), ('1', '1')), raised
    assert mk == ('0', '0'), 'MK 가 쉬는 상태로 안 내려갔다: %r' % (mk,)
    assert nt == ('0', '1'), 'NT 가 쉬는 상태로 안 내려갔다: %r' % (nt,)


def test_abort_rests_a_running_cntrigout_pulse(tmp_path):
    """⭐ `ABORT` 도 `CnTRIGOUT` 펄스를 끊는다 -- ICG `TRIGOUT` 과 같은 규약이다.

    유휴 중 `ABORT` 는 컨트롤러를 안 만지므로(기반 `No acquisition in progress`) NT 에
    오는 적용은 `release_pulse` 의 내림 하나뿐이다.
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            n = len(ses.nt.seen)
            ses.app.transport.feed('abc>ICS C2TRIGOUT 500000')
            await until(lambda: _trig_trace(ses.nt, n).count('APPLY') >= 1,
                        what='C2TRIGOUT 의 올림')
            k = len(ses.nt.seen)
            ses.app.transport.feed('abc>ICS abort')
            await until(lambda: _trig_trace(ses.nt, k).count('APPLY') >= 1,
                        what='ABORT 의 내림')
            return _rest_values(ses.nt), dict(ses.app.dispatch._trigout_timers or {})  # noqa: SLF001

    nt, timers = asyncio.run(run())
    assert nt == ('0', '1'), nt
    assert not timers, '끊은 펄스의 핸들이 남았다: %r' % timers


def test_shopen_takes_the_line_from_a_pending_cntrigout(tmp_path):
    """⛔ `SHOPEN` 이 셔터를 모는 컨트롤러의 **대기 중 `CnTRIGOUT` 을 끊는다**.

    안 끊으면 `CnTRIGOUT` 의 옛 타이머가 깨어나 선을 `FORCE=0` 으로 돌려 **`SHOPEN` 이
    열겠다던 셔터가 도중에 스크립트로 넘어간다** (`_trigout_cmd` 가 반대 방향을 끊는
    것과 짝이다).
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            fake = _shutter_fake(ses)
            word = 'C1TRIGOUT' if fake is ses.mk else 'C2TRIGOUT'
            n = len(fake.seen)
            ses.app.transport.feed('abc>ICS %s 10000' % word)         # 0.2 s
            await until(lambda: _trig_trace(fake, n).count('APPLY') >= 1,
                        what='%s 의 올림' % word)
            k = len(fake.seen)
            ses.app.transport.feed('abc>ICS SHOPEN 100')             # 2.0 s
            await until(lambda: _trig_trace(fake, k).count('APPLY') >= 1,
                        what='SHOPEN 의 올림')
            await asyncio.sleep(0.5)             # `CnTRIGOUT` 의 시한(0.2 s)을 넘긴다
            return _trig_trace(fake, k), _rest_values(fake)

    trace, now = asyncio.run(run())
    assert trace == ['LEVEL', 'FORCE', 'APPLY'], '옛 CnTRIGOUT 타이머가 선을 내렸다: %r' % trace
    assert now == ('1', '1'), now


def test_abort_in_the_raise_window_still_rests_the_shutter(tmp_path, monkeypatch):  # noqa: ANN001
    """⛔ **올림 도중에 온 `ABORT` 도 `SHOPEN` 을 끊는다** (DevNote 11.96).

    종전에는 핸들을 올림(`raise_line` -- `WCONFIG` 둘 + `APPLYSYSTEM`) **뒤에** 태스크
    안에서 적어서, 그 창에 온 `ABORT`·종료가 펄스를 못 봤다 -- 올림이 끝나면 셔터가
    강제로 열린 채 `<초>` 동안 남았다.  ⭐ 지금은 `spawn` 하는 자리에서 적는다.
    올림을 0.3 s 늦춰 그 창에 `ABORT` 를 넣는다.
    """
    from ics_archon.archon import trigout as trig_mod
    real = trig_mod.raise_line

    async def slow_raise(ctrl):  # noqa: ANN001, ANN202
        await asyncio.sleep(0.3)
        await real(ctrl)

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            monkeypatch.setattr(trig_mod, 'raise_line', slow_raise)
            fake = _shutter_fake(ses)
            n = len(ses.sent)
            ses.app.transport.feed('abc>ICS SHOPEN 500')
            await asyncio.sleep(0.05)                    # 늦춘 올림의 창 안
            ses.app.transport.feed('abc>ICS abort')
            await asyncio.sleep(0.6)                     # 늦춘 올림이 끝났을 시각을 넘긴다
            opened = [s for s in ses.sent[n:] if 'Shutter=Open' in s]
            return _cfg_value(fake, 'TRIGOUTLEVEL'), opened

    level, opened = asyncio.run(run())
    assert level == '0', '창 안의 ABORT 를 놓쳐 셔터가 열린 채 남았다'
    assert opened == [], opened


@pytest.mark.parametrize('line, fake_name, rest', [
    ('SHOPEN 0.01', 'mk', ('0', '0')),       # 배포 ini 는 MK 가 셔터를 몬다 -- 스크립트에 반환
    ('C2TRIGOUT 10', 'nt', ('0', '1')),      # 안 모는 NT -- 붙든다
])
def test_shutdown_in_the_rest_window_still_rests_the_line(tmp_path, monkeypatch, caplog,  # noqa: ANN001
                                                          line, fake_name, rest):
    """⛔ **내림 도중에 온 종료도 펄스를 끊고 선을 내린다** (DevNote 11.96).

    종전에는 펄스 태스크가 핸들을 내림(`rest_line`) **앞에서** 지워서, 그 한 적용 동안
    `release_pulse('shutdown')` 이 펄스를 못 봤다 -- 이어지는 `super().stop()` 이 그
    태스크를 취소하면 내림이 끊겨 선이 `LEVEL=1`·`FORCE=1` 로 남는다.  ⭐ 지금은 핸들을
    내림 **뒤에** `finally` 에서 지운다.  내림을 0.3 s 늦춰 그 창에서 세션을 닫는다.
    ⚠️ `ABORT` 로는 이 결함이 안 보인다 -- 태스크가 안 취소되니 제 내림이 끝까지 간다.
    """
    from ics_archon.archon import trigout as trig_mod
    real = trig_mod.rest_line
    caplog.set_level(logging.WARNING, logger='ics_archon.app')

    async def slow_rest(ctrl, how):  # noqa: ANN001, ANN202
        await asyncio.sleep(0.3)
        await real(ctrl, how)

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            fake = getattr(ses, fake_name)
            monkeypatch.setattr(trig_mod, 'rest_line', slow_rest)
            n = len(fake.seen)
            ses.app.transport.feed('abc>ICS %s' % line)
            await until(lambda: _trig_trace(fake, n).count('APPLY') >= 1,
                        what='%s 의 올림' % line)
            # 시한(0.2 ms)은 지났고 늦춘 내림(0.3 s)의 창 안이다.
            await asyncio.sleep(0.05)
            d = ses.app.dispatch
            held = (d._shutter_timer if line.startswith('SHOPEN')          # noqa: SLF001
                    else (d._trigout_timers or {}).get('NT'))              # noqa: SLF001
            in_window = (held is not None and not held.done(),
                         _rest_values(fake))
        # `__aexit__` 가 `app.stop()` -> `release_pulse('shutdown')` 을 지났다.
        return in_window, _rest_values(fake)

    (alive, during), after = asyncio.run(run())
    assert alive, '내림 창에서 핸들이 이미 지워졌다 -- 종료가 이 펄스를 못 본다'
    assert during == ('1', '1'), during
    assert after == rest, '내림 창의 종료가 선을 HIGH 로 남겼다: %r' % (after,)
    assert any('shutdown -- cutting the running pulse' in r.getMessage()
               for r in caplog.records), [r.getMessage() for r in caplog.records]


def test_cntrigout_taking_a_both_shopen_rests_the_other_controller(tmp_path):
    """⛔ **`shutter_ctrl = both` 에서 `CnTRIGOUT` 이 `SHOPEN` 을 끊으면 다른 쪽도 내린다**
    (DevNote 11.96).

    `SHOPEN` 은 두 대를 다 올리는데 끊긴 `SHOPEN` 은 내림을 안 돌리고, `C1TRIGOUT` 은 MK 만
    만진다 -- 종전에는 NT 가 `TRIGOUTLEVEL=1`·`FORCE=1` 인 채 **핸들 없이** 남아 `ABORT`·
    종료도 못 찾았다 (셔터가 열린 채).  ⭐ NT 는 `SHOPEN` 의 쉬는 상태 `('0','0')` 로 가고,
    그 내림의 핸들은 끝나면 지워진다.  종료는 MK 의 `C1TRIGOUT` 을 끊어 `('0','0')` 로 내린다.
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            # ⚠️ 배포 ini 는 `shutter_ctrl = MK` -- 두 대가 다 셔터를 모는 배선으로 바꾼다.
            # 백엔드·컨트롤러가 같은 `acfg` 객체를 들고 있어 곧바로 먹는다.
            ses.app.acfg.shutter_ctrl = 'BOTH'
            await ses.warmup()
            be, d = ses.app.backend, ses.app.dispatch
            assert be.acfg.drives_shutter('MK') and be.acfg.drives_shutter('NT')
            m, n = len(ses.mk.seen), len(ses.nt.seen)
            ses.app.transport.feed('abc>ICS SHOPEN 500')                 # 10 s
            await until(lambda: _trig_trace(ses.mk, m).count('APPLY') >= 1
                        and _trig_trace(ses.nt, n).count('APPLY') >= 1,
                        what='SHOPEN 의 두 대 올림')
            opened = (_rest_values(ses.mk), _rest_values(ses.nt))
            m, n = len(ses.mk.seen), len(ses.nt.seen)
            ses.app.transport.feed('abc>ICS C1TRIGOUT 500000')           # 10 s
            await until(lambda: _trig_trace(ses.mk, m).count('APPLY') >= 1
                        and _trig_trace(ses.nt, n).count('APPLY') >= 1,
                        what='C1TRIGOUT 의 MK 올림과 NT 내림')
            await until(lambda: 'NT' not in (d._trigout_timers or {}),     # noqa: SLF001
                        what='NT 내림 핸들 정리')
            during = (_rest_values(ses.mk), _rest_values(ses.nt))
            shopen_gone = d._shutter_timer is None                         # noqa: SLF001
        return opened, during, shopen_gone, _rest_values(ses.mk), _rest_values(ses.nt)

    opened, during, shopen_gone, mk, nt = asyncio.run(run())
    assert opened == (('1', '1'), ('1', '1')), opened
    assert during == (('1', '1'), ('0', '0')), 'NT 가 SHOPEN 의 HIGH 로 남았다: %r' % (during,)
    assert shopen_gone
    assert mk == ('0', '0'), '종료가 MK 의 C1TRIGOUT 을 안 내렸다: %r' % (mk,)
    assert nt == ('0', '0'), nt


@pytest.mark.parametrize('line, word', [('SHOPEN 5', 'SHOPEN'),
                                        ('C2TRIGOUT 50', 'C2TRIGOUT')])
def test_a_trigger_line_failure_is_ascii_on_the_wire_and_raw_in_the_log(  # noqa: ANN001
        tmp_path, monkeypatch, caplog, line, word):
    """⛔ **한글 예외가 와이어에서 `?` 로만 남지 않는다** (DevNote 11.96).

    종전 `'Failed: %s' % exc` 는 컨트롤러 층의 한글 문구를 그대로 실어 와이어에서
    `?????` 가 됐고, 원문은 어디에도 없었다.  ⭐ 지금은 `_emit_failed` 가 **원문을 로그 오류
    한 줄에 먼저** 남기고, 와이어에는 ASCII 로 접은 문구 + `(see log)` 가 나간다.
    """
    from ics_archon.archon import trigout as trig_mod
    from ics_archon.archon.protocol import ArchonError
    caplog.set_level(logging.ERROR, logger='ics_archon.app')

    async def broken(ctrl):  # noqa: ANN001, ANN202
        raise ArchonError('%s: 연결이 끊겼다' % ctrl.tag)

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            monkeypatch.setattr(trig_mod, 'raise_line', broken)
            return await ses.reply('abc>ICS %s' % line, word)

    got = asyncio.run(run())
    assert got.isascii(), got
    assert (' ERROR: %s Failed: ' % word) in got and got.endswith('(see log)'), got
    raw = [r for r in caplog.records if '연결이 끊겼다' in r.getMessage()]
    assert raw and raw[0].levelno == logging.ERROR, [r.getMessage() for r in caplog.records]
    assert raw[0].getMessage().startswith('%s: raising the ' % word), raw[0].getMessage()


# -- 올림이 실패해도 · 종료 중이어도 선이 HIGH 로 남지 않는다 (DevNote 11.96) ----
#
# ⛔ 펄스 태스크는 올림이 실패하면 `finally` 에서 핸들을 지운다 -- 그때 선이 HIGH 면
# `ABORT`·종료도 못 찾는다.  그래서 올림 실패 가지에서 **올렸거나 올리려 한** 컨트롤러를
# 내려 본 뒤 답한다.  종료 쪽은 `stop()` 의 깃발(`stopping`)이 새 올림을 거절한다.


@pytest.mark.parametrize('sent_first', [False, True])
def test_a_failed_both_shopen_rests_what_it_raised(tmp_path, monkeypatch,  # noqa: ANN001
                                                   sent_first):
    """⛔ **`shutter_ctrl = both` 에서 NT 올림이 실패하면 올려 둔 MK 를 내린다**.

    종전에는 올림 고리가 NT 에서 예외로 빠져 곧바로 답하고 끝났다 -- MK 는
    `TRIGOUTLEVEL=1`·`FORCE=1` 인 채 핸들이 `finally` 에서 지워져 `ABORT`·종료도 못
    찾았다 (셔터가 강제로 열린 채).  ⭐ `sent_first` 는 `APPLYSYSTEM` 이 나간 뒤 시한을
    넘긴 꼴이다 -- NT 도 HIGH 라 **올리려 한** NT 까지 내린다.  내림은 답보다 앞이다.
    """
    from ics_archon.archon import trigout as trig_mod
    real = trig_mod.raise_line

    async def nt_fails(ctrl):  # noqa: ANN001, ANN202
        if ctrl.tag == 'NT':
            if sent_first:
                await real(ctrl)                 # 적용은 나갔는데 답을 못 받은 꼴
            raise TimeoutError('NT: APPLYSYSTEM 응답이 없다')
        await real(ctrl)

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            ses.app.acfg.shutter_ctrl = 'BOTH'
            await ses.warmup()
            monkeypatch.setattr(trig_mod, 'raise_line', nt_fails)
            n = len(ses.sent)
            got = await ses.reply('abc>ICS SHOPEN 500', 'SHOPEN')
            # ⭐ 답이 나온 **그 시점**의 값 -- 내림이 답보다 앞이어야 한다.
            at_reply = (_rest_values(ses.mk), _rest_values(ses.nt))
            opened = [s for s in ses.sent[n:] if 'Shutter=Open' in s]
            handle = ses.app.dispatch._shutter_timer                      # noqa: SLF001
        return got, at_reply, opened, handle

    got, (mk, nt), opened, handle = asyncio.run(run())
    assert ' ERROR: SHOPEN Failed: ' in got and got.isascii(), got
    assert mk == ('0', '0'), '올림이 실패한 SHOPEN 이 MK 를 HIGH 로 남겼다: %r' % (mk,)
    assert nt == ('0', '0'), '올리려 한 NT 를 안 내렸다: %r' % (nt,)
    assert opened == [], opened
    assert handle is None


def test_a_failed_cntrigout_raise_rests_the_line(tmp_path, monkeypatch):  # noqa: ANN001
    """⛔ `CnTRIGOUT` 도 같다 -- `APPLYSYSTEM` 이 나간 뒤 시한을 넘기면 선이 HIGH 인 채
    핸들이 지워진다.  ⭐ 그 컨트롤러의 쉬는 상태로 내린 뒤 답한다 (안 모는 NT `('0','1')`)."""
    from ics_archon.archon import trigout as trig_mod
    real = trig_mod.raise_line

    async def sent_then_timeout(ctrl):  # noqa: ANN001, ANN202
        await real(ctrl)
        raise TimeoutError('%s: APPLYSYSTEM 응답이 없다' % ctrl.tag)

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            monkeypatch.setattr(trig_mod, 'raise_line', sent_then_timeout)
            got = await ses.reply('abc>ICS C2TRIGOUT 500000', 'C2TRIGOUT')
            at_reply = _rest_values(ses.nt)
            timers = dict(ses.app.dispatch._trigout_timers or {})          # noqa: SLF001
        return got, at_reply, timers

    got, nt, timers = asyncio.run(run())
    assert ' ERROR: C2TRIGOUT Failed: ' in got, got
    assert nt == ('0', '1'), '올림이 실패한 C2TRIGOUT 이 NT 를 HIGH 로 남겼다: %r' % (nt,)
    assert 'NT' not in timers, timers


def test_shclose_rests_every_controller_even_when_one_fails(tmp_path, monkeypatch,  # noqa: ANN001
                                                            caplog):
    """⛔ **내림 고리는 하나가 실패해도 나머지를 다 내린다** -- 첫 실패는 다 돈 뒤에 답한다.

    종전에는 고리 전체가 한 `try` 라 MK 내림이 실패하면 NT 는 시도조차 안 됐다
    (`shutter_ctrl = both` 에서 NT 셔터가 열린 채).  실패한 MK 는 로그 오류 줄에 이름이 남는다.
    """
    from ics_archon.archon import trigout as trig_mod
    from ics_archon.archon.protocol import ArchonError
    real = trig_mod.rest_line
    caplog.set_level(logging.ERROR, logger='ics_archon.app')

    async def mk_fails(ctrl, how):  # noqa: ANN001, ANN202
        if ctrl.tag == 'MK':
            raise ArchonError('MK: 연결이 끊겼다')
        await real(ctrl, how)

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            ses.app.acfg.shutter_ctrl = 'BOTH'
            await ses.warmup()
            m, n = len(ses.mk.seen), len(ses.nt.seen)
            ses.app.transport.feed('abc>ICS SHOPEN 500')                 # 10 s
            await until(lambda: _trig_trace(ses.mk, m).count('APPLY') >= 1
                        and _trig_trace(ses.nt, n).count('APPLY') >= 1,
                        what='SHOPEN 의 두 대 올림')
            monkeypatch.setattr(trig_mod, 'rest_line', mk_fails)
            got = await ses.reply('abc>ICS SHCLOSE', 'SHCLOSE')
            return got, _rest_values(ses.mk), _rest_values(ses.nt)

    got, mk, nt = asyncio.run(run())
    assert ' ERROR: SHCLOSE Failed: ' in got, got
    assert nt == ('0', '0'), 'MK 실패 뒤에 NT 를 안 내렸다: %r' % (nt,)
    assert mk == ('1', '1'), mk                       # 실패한 쪽은 그대로 -- 답이 그것을 알린다
    assert any(r.getMessage().startswith('SHCLOSE: could not rest the MK trigger line')
               for r in caplog.records), [r.getMessage() for r in caplog.records]


def test_a_raise_after_the_shutdown_released_the_pulses_is_refused(tmp_path,  # noqa: ANN001
                                                                   monkeypatch):
    """⛔ **종료가 펄스를 내린 뒤 온 `SHOPEN`·`CnTRIGOUT` 은 선을 올리지 않는다**.

    종전에는 `release_pulse('shutdown')` 과 전송 닫기 사이에 온 올림이 새 펄스를 띄웠고,
    `super().stop()` 이 그 태스크를 내림 없이 취소했다 -- 선이 HIGH(MK 면 셔터가 열린 채)로
    남는다.  ⭐ `stop()` 이 첫 줄에서 `stopping` 을 세우고 명령 처리부가 ASCII 로 거절한다.
    `release_pulse` 를 감싸 **그 직후**에 명령을 넣는다 -- 실제 종료 순서 그대로다.
    """
    mark = {}

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            d = ses.app.dispatch
            real_release = d.release_pulse

            async def release_then_race(why):  # noqa: ANN001, ANN202
                cut = await real_release(why)
                mark['stopping'] = ses.app.stopping
                mark['mk'], mark['nt'] = len(ses.mk.seen), len(ses.nt.seen)
                mark['sent'] = len(ses.sent)
                ses.app.transport.feed('abc>ICS SHOPEN 5')
                ses.app.transport.feed('abc>ICS C2TRIGOUT 5000')
                return cut

            monkeypatch.setattr(d, 'release_pulse', release_then_race)
            assert ses.app.stopping is False
        # `__aexit__` 가 `app.stop()` 을 지났다 -- 그 안에서 위 두 명령이 왔다.
        return (ses.sent[mark['sent']:], _trig_trace(ses.mk, mark['mk']),
                _trig_trace(ses.nt, mark['nt']))

    sent, mk_trace, nt_trace = asyncio.run(run())
    assert mark['stopping'] is True
    for word in ('SHOPEN', 'C2TRIGOUT'):
        assert any(' ERROR: %s Shutting down -- not raised' % word in s for s in sent), sent
    assert all(s.isascii() for s in sent), sent
    assert mk_trace == [], '종료 중 SHOPEN 이 MK 를 올렸다: %r' % mk_trace
    assert nt_trace == [], '종료 중 C2TRIGOUT 이 NT 를 올렸다: %r' % nt_trace


def test_nan_and_inf_durations_never_raise_a_line(tmp_path):  # noqa: ANN001
    """⛔ `nan`·`inf` 는 거절한다 -- `float()` 은 받아 주지만 선을 올린 채 못 내린다.

    `nan` 은 `< 0` 비교를 빠져나가 펄스를 띄우고 `asyncio.sleep(nan)` 이 안 깨어 선이
    **HIGH 로 남는다**(`SHOPEN` 이면 셔터가 강제로 열린 채).  `inf` 는 영영 안 내린다
    (DevNote 11.96).
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            mk0, nt0 = len(ses.mk.seen), len(ses.nt.seen)
            n0 = len(ses.sent)
            for line in ('abc>ICS SHOPEN nan', 'abc>ICS SHOPEN inf',
                         'abc>ICS C1TRIGOUT nan', 'abc>ICS C2TRIGOUT inf'):
                ses.app.transport.feed(line)
            await until(lambda: len([m for m in ses.sent[n0:] if ' ERROR: ' in m]) >= 4,
                        what='nan/inf 거절 넷')
            await asyncio.sleep(0.2)
            return (ses.sent[n0:], _trig_trace(ses.mk, mk0), _trig_trace(ses.nt, nt0))

    sent, mk_trace, nt_trace = asyncio.run(run())
    assert sum('ERROR: SHOPEN Invalid exposure time' in s for s in sent) == 2, sent
    assert sum('Invalid duration' in s and 'TRIGOUT' in s for s in sent) == 2, sent
    assert mk_trace == [] and nt_trace == [], (mk_trace, nt_trace)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""텔레메트리 감시·기록 (층 1·2) -- 설계 규칙 넷과 D4·D5 회귀.

이 파일이 지키는 것은 **값이 아니라 규칙**이다.  값(실기 STATUS 의 실제 숫자)은
아직 못 봤고, 그것은 `tools/probe_archon.py` 1단계가 사람 눈으로 확인한다.
여기서 못박는 것은 그 값이 어떻게 다뤄져야 하는가다:

1. 헤더용 스냅샷과 살아 있는 스냅샷이 **갈려 있나** (섞이면 `Cn_TEMP` 의 뜻이
   조용히 바뀐다)
2. 감시가 `telemetry_enabled` 래치를 **안 건드리나** (F8 -- 취득 경로의 판단)
3. `VALID=0` 이 **헤더에서는** `NC` 이고 **기록에서는** 값으로 남나 (D4)
4. 첫 노출 전에 `-SYNCH` 가 뜨지 **않나** (D5/G5)
5. 열 구성이 바뀌면 파일이 **갈리나** (과거 행 오독 방지)
"""

from __future__ import annotations

import asyncio
import csv
import os
import time

import pytest
from fake_archon import DEFAULT_STATUS, DEFAULT_SYSTEM, FakeArchon

from ics_archon import config as acfg_mod
from ics_archon.archon import parse
from ics_archon.archon.backend import ArchonBackend
from ics_archon.archon.controller import ArchonController
from ics_archon.archon.monitor import TelemetryLog, TelemetryMonitor

#: 실기 science ACF 의 바이어스 이름표 그대로 (`KMTK_SCI_113_STA0200_R2608_MK`).
#: **16채널이 CCD 바이어스**이고, 이름표가 없는 채널은 세지 않는다.
ACF_BIAS = """[CONFIG]
PARAMETER1="Exposures=1"
PARAMETER2="IntMS=0"
MOD4\\LVHC_LABEL1=OG-A
MOD4\\LVHC_LABEL2=CLAMP_N-A
MOD4\\LVHC_LABEL3=CLAMP_P-A
MOD4\\LVHC_LABEL4=CLAMP_P-B
MOD4\\LVHC_LABEL5=CLAMP_N-B
MOD4\\LVHC_LABEL6=OG-B
MOD4\\LVLC_LABEL1=
MOD9\\HVHC_LABEL1=DD-B
MOD9\\HVHC_LABEL2=ODD-B
MOD9\\HVHC_LABEL3=ODA-B
MOD9\\HVHC_LABEL4=DD-A
MOD9\\HVHC_LABEL5=ODD-A
MOD9\\HVHC_LABEL6=ODA-A
MOD9\\HVLC_LABEL11=RDA-B
MOD9\\HVLC_LABEL12=RDD-B
MOD9\\HVLC_LABEL23=RDA-A
MOD9\\HVLC_LABEL24=RDD-A
MOD9\\HVLC_LABEL1=
MOD1\\LVDS_LABEL1=CLK
MOD10\\LABEL1=A1-B
"""


def _bias_status() -> dict:
    """`DEFAULT_STATUS` + 바이어스 16채널 실측값."""
    st = dict(DEFAULT_STATUS)
    for chan in range(1, 7):
        st['MOD4/LVHC_V%d' % chan] = '%.3f' % (-4.0 + chan * 0.1)
        st['MOD4/LVHC_I%d' % chan] = '%.3f' % (0.5 + chan * 0.01)
        st['MOD9/HVHC_V%d' % chan] = '%.3f' % (15.0 + chan * 0.5)
        st['MOD9/HVHC_I%d' % chan] = '%.3f' % (1.0 + chan * 0.02)
    for chan in (11, 12, 23, 24):
        st['MOD9/HVLC_V%d' % chan] = '12.010'
        st['MOD9/HVLC_I%d' % chan] = '0.220'
    return st


def _cfg(tmp_path, **over):  # noqa: ANN001
    cfg = acfg_mod.ArchonCfg()
    cfg.monitor_log = str(tmp_path / 'log')
    cfg.monitor_interval = 1.0
    cfg.hosts = {'MK': '127.0.0.1'}
    for key, value in over.items():
        setattr(cfg, key, value)
    return cfg


# ---------------------------------------------------------------------------
# parse -- 응답 자체의 건강 필드
# ---------------------------------------------------------------------------

def test_valid_has_three_states_not_two():
    """`None`(보고 없음)을 `False` 로 접으면 구 펌웨어가 통째로 NC 가 된다."""
    assert parse.status_valid({'VALID': '1'}) is True
    assert parse.status_valid({'VALID': '0'}) is False
    assert parse.status_valid({'POWERGOOD': '1'}) is None    # 필드가 없다
    assert parse.status_valid({}) is None
    assert parse.status_valid({'VALID': 'yes'}) is None      # 못 읽으면 보류


def test_log_count_tells_absent_from_zero():
    """`LOG` 에서 "보고 안 함" 과 "0개" 는 정반대 뜻이다."""
    assert parse.log_count({'LOG': '0'}) == 0
    assert parse.log_count({'COUNT': '3'}) is None


def test_valid_zero_makes_the_header_nc_but_keeps_the_record(monkeypatch):
    """D4 -- 같은 응답이 헤더에서는 `NC`, 기록에서는 값으로 남는다."""
    st = dict(DEFAULT_STATUS, VALID='0')
    assert parse.telemetry_of(st) == {}                      # 헤더 경로
    live = parse.telemetry_of(st, honour_valid=False)        # 기록 경로
    assert len(live['temp']) == len(parse.TEMP_MODS)
    assert live['temp'][0] == pytest.approx(31.5)


def test_valid_absent_still_carries_values():
    """F2 -- 보고하지 않는 필드를 이상으로 세지 않는다."""
    assert 'VALID' not in DEFAULT_STATUS
    assert parse.telemetry_of(DEFAULT_STATUS)['temp']


def test_invalid_status_suppresses_the_other_health_verdicts():
    """`VALID=0` 이면 나머지 필드는 무효다 -- 가짜 경보를 내면 안 된다.

    ⚠️ 이것이 없으면 무효 블록의 `POWER=0` 을 읽어 "전원 이상" 을 외치고, 그
    경보가 되풀이되면 사람이 **진짜 전원 이상도 무시**하게 된다.
    """
    garbage = dict(DEFAULT_STATUS, VALID='0', POWER='0', POWERGOOD='0',
                   OVERHEAT='1')
    bad = parse.health_problems(garbage)
    assert bad == ['VALID=0 (이 응답의 나머지 필드는 무효다 -- 판정을 보류한다)']
    # 유효한 응답에서는 종전대로 셋을 다 본다.
    assert len(parse.health_problems(dict(garbage, VALID='1'))) == 3


# ---------------------------------------------------------------------------
# parse -- 전원 레일 정상 범위 (매뉴얼 p.41)
# ---------------------------------------------------------------------------

def test_rail_limits_are_asymmetric():
    """±% 규칙을 쓰면 틀린다 -- `N6V` 는 −6.6 … −5.3 이다."""
    assert parse.RAIL_LIMITS['N6V'] == (-6.6, -5.3)
    assert parse.RAIL_LIMITS['P6V'] == (5.5, 6.6)
    # ⚠️ `P17V` 는 SMC_CLAUDE.md 로 옮겨 적은 표에서 빠져 있던 줄이다.
    assert parse.RAIL_LIMITS['P17V'] == (16.4, 17.5)
    assert set(parse.RAIL_LIMITS) == set(parse.VOLT_RAILS)


def test_rail_problems_flags_only_reported_rails():
    assert parse.rail_problems(DEFAULT_STATUS) == []
    bad = parse.rail_problems(dict(DEFAULT_STATUS, N6V_V='-4.900'))
    assert len(bad) == 1 and bad[0].startswith('N6V=')
    # 보고가 없는 레일은 세지 않는다 (안 쓰는 레일은 배선도 감시도 안 된다).
    thin = {k: v for k, v in DEFAULT_STATUS.items() if not k.startswith('P35V')}
    assert parse.rail_problems(thin) == []


def test_rail_limits_can_be_overridden_per_unit(tmp_path):  # noqa: ANN001
    """`[archon.rails]` 는 **적은 레일만** 덮는다 -- 나머지 판정이 안 사라진다."""
    ini = tmp_path / 'x.ini'
    ini.write_text('[archon]\nport = 4242\n\n'
                   '[archon.rails]\nn6v = -5.3, -6.6\n',   # 일부러 뒤집어 적었다
                   encoding='utf-8')
    cfg = acfg_mod.load(str(ini))
    assert cfg.rail_limits['N6V'] == (-6.6, -5.3)           # 바로잡아 쓴다
    assert cfg.rail_limits['P35V'] == parse.RAIL_LIMITS['P35V']


# ---------------------------------------------------------------------------
# parse -- 층 2 바이어스 (이름표는 ACF, 값은 STATUS)
# ---------------------------------------------------------------------------

def test_bias_channels_come_from_acf_labels(tmp_path):  # noqa: ANN001
    acf = tmp_path / 'b.acf'
    acf.write_text(ACF_BIAS, encoding='ascii')
    ctrl = ArchonController('MK', _cfg(tmp_path))
    ctrl.parse_acf(str(acf))                     # 왕복 없음 -- 파일만 읽는다

    channels = parse.bias_channels(ctrl.config)
    assert [label for _p, label in channels] == [
        'OG-A', 'CLAMP_N-A', 'CLAMP_P-A', 'CLAMP_P-B', 'CLAMP_N-B', 'OG-B',
        'DD-B', 'ODD-B', 'ODA-B', 'DD-A', 'ODD-A', 'ODA-A',
        'RDA-B', 'RDD-B', 'RDA-A', 'RDD-A']
    assert len(channels) == 16                   # 실기 science 구성
    # 이름표가 빈 채널과 바이어스가 아닌 LABEL 키(LVDS·클록)는 안 센다.
    assert all('LVDS' not in p and 'MOD10' not in p for p, _l in channels)
    assert channels[0][0] == 'MOD4/LVHC_1'


def test_bias_readings_read_status_not_the_acf(tmp_path):  # noqa: ANN001
    """⚠️ 두 dict 의 키 문자열이 같다 -- ACF 는 지령값, STATUS 는 실측값이다."""
    acf = tmp_path / 'b.acf'
    acf.write_text(ACF_BIAS, encoding='ascii')
    ctrl = ArchonController('MK', _cfg(tmp_path))
    ctrl.parse_acf(str(acf))
    channels = parse.bias_channels(ctrl.config)

    got = dict((label, volt)
               for label, volt, _i in parse.bias_readings(_bias_status(),
                                                          channels))
    assert got['OG-A'] == pytest.approx(-3.9)    # STATUS 값
    # 결측 채널은 자리를 비우지 않고 sentinel 로 남는다.
    thin = {k: v for k, v in _bias_status().items()
            if not k.startswith('MOD9/HVLC')}
    missing = dict((label, volt)
                   for label, volt, _i in parse.bias_readings(thin, channels))
    assert missing['RDA-B'] == parse.FIELD_NC
    assert missing['OG-A'] == pytest.approx(-3.9)


# ---------------------------------------------------------------------------
# 기록 -- 파일 가르기
# ---------------------------------------------------------------------------

def test_log_writes_one_header_and_rolls_over_by_date(tmp_path):  # noqa: ANN001
    log = TelemetryLog('MK', str(tmp_path), ['utc', 'a', 'event'])
    day1 = 1787000000.0                          # 2026-08-... UTC
    log.write(['t1', '1', ''], day1)
    log.write(['t2', '2', ''], day1 + 60)
    log.write(['t3', '3', ''], day1 + 86400 * 2)  # 다른 날
    log.close()

    files = sorted(os.listdir(tmp_path))
    assert len(files) == 2, files
    rows = list(csv.reader(open(tmp_path / files[0], encoding='utf-8')))
    assert rows[0] == ['utc', 'a', 'event']      # 헤더는 한 번만
    assert [r[0] for r in rows[1:]] == ['t1', 't2']


def test_log_splits_when_the_column_set_changes(tmp_path):  # noqa: ANN001
    """자리 수가 바뀌면 **과거 파일이 조용히 오독된다** -- 그래서 가른다."""
    when = 1787000000.0
    first = TelemetryLog('MK', str(tmp_path), ['utc', 'B_OG-A_V[V]', 'event'])
    first.write(['t1', '1.0', ''], when)
    first.close()
    # ACF 가 바뀌어 채널이 하나 늘었다고 하자.
    second = TelemetryLog('MK', str(tmp_path),
                          ['utc', 'B_OG-A_V[V]', 'B_OG-B_V[V]', 'event'])
    second.write(['t2', '1.0', '2.0', ''], when)
    second.close()

    files = set(os.listdir(tmp_path))
    assert files == {'telemetry.MK.20260817.csv',
                     'telemetry.MK.20260817.2.csv'}, files


# ---------------------------------------------------------------------------
# 감시 태스크
# ---------------------------------------------------------------------------

class _FakeCtrl:
    """왕복 없이 감시 루프만 도는 상대역."""

    tag = 'MK'

    def __init__(self, status=None, fail=False) -> None:  # noqa: ANN001
        self.config = {}
        self.status = {}                         # 헤더용 -- 감시가 안 건드린다
        self.status_live = {}
        self.status_live_at = 0.0
        self.status_live_fails = 0
        self.telemetry_enabled = True
        self._status = status if status is not None else _bias_status()
        self._fail = fail
        self.polls = 0

        class _Link:
            connected = True
            host, port = '127.0.0.1', 4242
        self.link = _Link()

    def parse_acf(self, path: str) -> None:
        ArchonController.parse_acf(self, path)   # 같은 코드를 그대로 쓴다

    async def connect(self) -> None:             # pragma: no cover
        pass

    async def refresh_status_live(self) -> bool:
        self.polls += 1
        if self._fail:
            self.status_live_fails += 1
            self.status_live = {}
            return False
        self.status_live = dict(self._status)
        self.status_live_at = time.time()
        return True


def _run_monitor(mon, ticks: int) -> None:  # noqa: ANN001
    async def go():
        task = asyncio.ensure_future(mon.run())
        while mon.ctrl.polls < ticks and not task.done():
            await asyncio.sleep(0.01)
        mon.stop()
        await asyncio.wait_for(task, timeout=5)
    asyncio.run(go())


def _rows(path: str):  # noqa: ANN201
    with open(path, encoding='utf-8', newline='') as fh:
        return list(csv.reader(fh))


def test_monitor_writes_fixed_columns_with_units(tmp_path):  # noqa: ANN001
    acf = tmp_path / 'b.acf'
    acf.write_text(ACF_BIAS, encoding='ascii')
    cfg = _cfg(tmp_path, acf={'MK': str(acf)}, monitor_interval=1.0)
    ctrl = _FakeCtrl()
    mon = TelemetryMonitor(ctrl, cfg, expstatus=lambda: 'READOUT')
    mon._stop = asyncio.Event()
    _run_monitor(mon, ticks=1)

    rows = _rows(mon.log.path)
    head = rows[0]
    assert head[:4] == ['utc', 'age_ms', 'lag_ms', 'expstatus']
    assert head[-1] == 'event'
    # 자리 = 항목.  온도 10 · 레일 7x2 · 바이어스 16x2.
    assert sum(1 for c in head if c.endswith('[C]')) == len(parse.TEMP_MODS)
    assert sum(1 for c in head if c.endswith('[A]')) == len(parse.VOLT_RAILS)
    assert sum(1 for c in head if c.endswith('[mA]')) == 16
    # ⚠️ 단위가 이름에 박혀 있어야 한다 -- 레일은 A, 바이어스는 mA 다.
    assert 'I1_P2V5[A]' in head and 'B_OG-A_I[mA]' in head
    assert 'T1_Backplane[C]' in head

    assert rows[1][head.index('event')] == 'start'
    sample = rows[2]
    assert len(sample) == len(head)
    assert sample[head.index('expstatus')] == 'READOUT'
    assert sample[head.index('T1_Backplane[C]')] == '31.5'
    assert sample[head.index('B_OG-A_V[V]')] == '-3.900'
    assert rows[-1][head.index('event')] == 'stop'


def test_monitor_keeps_invalid_samples(tmp_path):  # noqa: ANN001
    """`valid=0` 행도 버리지 않는다 -- 언제부터 이상했는지가 자료다."""
    cfg = _cfg(tmp_path)
    ctrl = _FakeCtrl(status=dict(DEFAULT_STATUS, VALID='0'))
    mon = TelemetryMonitor(ctrl, cfg)
    mon._stop = asyncio.Event()
    _run_monitor(mon, ticks=1)

    rows = _rows(mon.log.path)
    head = rows[0]
    sample = rows[2]
    assert sample[head.index('valid')] == '0'
    assert sample[head.index('T1_Backplane[C]')] == '31.5'   # 값은 남는다


def test_monitor_marks_failures_and_recovery(tmp_path):  # noqa: ANN001
    """원형 로그의 긴 공백이 "죽은 건가 끈 건가" 를 못 가렸다 -- 그 답이 이 열."""
    cfg = _cfg(tmp_path)
    ctrl = _FakeCtrl(fail=True)
    mon = TelemetryMonitor(ctrl, cfg)
    mon._stop = asyncio.Event()

    async def go():
        task = asyncio.ensure_future(mon.run())
        while ctrl.polls < 1 and not task.done():
            await asyncio.sleep(0.01)
        ctrl._fail = False
        while ctrl.polls < 4 and not task.done():
            await asyncio.sleep(0.01)
        mon.stop()
        await asyncio.wait_for(task, timeout=5)
    asyncio.run(go())

    head, *rows = _rows(mon.log.path)
    events = [r[head.index('event')] for r in rows]
    assert events[0] == 'start'
    assert 'poll_failed' in events and 'resumed' in events
    assert events[-1] == 'stop'
    # ⚠️ **`resumed` 는 한 번만 나야 한다** -- 회복 표시가 자기를 다시
    # 트리거하면 정상 구간이 통째로 `resumed` 로 찬다.
    assert events.count('resumed') == 1, events
    assert events[events.index('resumed') + 1] == '', events


def test_monitor_never_touches_the_header_snapshot(tmp_path):  # noqa: ANN001
    """규칙 -- 헤더용 `ctrl.status` 와 `telemetry_enabled` 는 감시의 것이 아니다.

    섞이면 `Cn_TEMP/VOLT/CURR` 의 뜻이 "노출 개시 시점 값" 에서 "마지막 폴링
    값" 으로 조용히 바뀌고, 폴링 간격·락 경합에 따라 노출마다 달라진다.
    """
    cfg = _cfg(tmp_path)
    ctrl = _FakeCtrl()
    ctrl.status = {'BACKPLANE_TEMP': '11.1'}     # 노출 개시에 언 값
    mon = TelemetryMonitor(ctrl, cfg)
    mon._stop = asyncio.Event()
    _run_monitor(mon, ticks=2)

    assert ctrl.status == {'BACKPLANE_TEMP': '11.1'}
    assert ctrl.telemetry_enabled is True
    assert ctrl.status_live['BACKPLANE_TEMP'] == '31.5'


def test_monitor_does_not_run_when_telemetry_is_off(tmp_path):  # noqa: ANN001
    """`telemetry=false` 의 뜻은 "왕복을 v1.0 계보와 같게 둔다" 이다."""
    cfg = _cfg(tmp_path, telemetry=False)
    mon = TelemetryMonitor(_FakeCtrl(), cfg)
    mon._stop = asyncio.Event()
    asyncio.run(asyncio.wait_for(mon.run(), timeout=5))
    assert mon.log is None
    assert not os.path.exists(cfg.monitor_log)


def test_monitor_refuses_an_unexpanded_tilde(tmp_path):  # noqa: ANN001
    """`~` 가 안 펼쳐지면 **cwd 아래 `~` 폴더**가 조용히 생긴다 -- 안 만든다."""
    cfg = _cfg(tmp_path, monitor_log='~/AIC/log')
    mon = TelemetryMonitor(_FakeCtrl(), cfg)
    mon._stop = asyncio.Event()
    asyncio.run(asyncio.wait_for(mon.run(), timeout=5))
    assert mon.log is None
    assert not os.path.exists('~')


# ---------------------------------------------------------------------------
# 컨트롤러 -- 살아 있는 스냅샷 · 진단
# ---------------------------------------------------------------------------

def test_live_refresh_does_not_flip_the_acquisition_latch(tmp_path):  # noqa: ANN001
    """규칙 2 -- 감시의 성공·실패가 취득 경로의 판단을 뒤집으면 안 된다 (F8)."""
    fake = FakeArchon(status=dict(DEFAULT_STATUS), system=dict(DEFAULT_SYSTEM),
                      status_delay=0.4)
    fake.start()
    try:
        cfg = _cfg(tmp_path, status_timeout=0.05, connect_retry=1)
        cfg.hosts = {'MK': '127.0.0.1'}
        cfg.port = fake.port
        ctrl = ArchonController('MK', cfg)

        async def go():
            await ctrl.connect()
            ctrl.status = {'BACKPLANE_TEMP': '9.9'}      # 노출 개시에 언 값
            ok = await ctrl.refresh_status_live()        # 시한 초과한다
            assert ok is False
            assert ctrl.status_live == {}                # 낡은 값은 버린다
            assert ctrl.status_live_fails == 1
            # ⚠️ 헤더 쪽은 그대로다.
            assert ctrl.telemetry_enabled is True
            assert ctrl.status == {'BACKPLANE_TEMP': '9.9'}
            # 그리고 되살아나면 실패 카운터가 0 으로 돌아간다.
            ctrl.cfg.status_timeout = 5.0
            assert await ctrl.refresh_status_live() is True
            assert ctrl.status_live_fails == 0
            assert ctrl.status_live_at > 0
            assert ctrl.status == {'BACKPLANE_TEMP': '9.9'}
            await ctrl.close()
        asyncio.run(go())
    finally:
        fake.shutdown()


def test_diagnostic_snapshot_survives_a_dead_link(tmp_path):  # noqa: ANN001
    """실패한 순간에 부르는 것이므로 **예외를 올리면 안 된다.**"""
    ctrl = ArchonController('MK', _cfg(tmp_path))
    line = asyncio.run(ctrl.diagnostic_snapshot())
    assert 'FRAME 질의 실패' in line


def test_frame_wait_deadline_starts_after_integration(tmp_path):  # noqa: ANN001
    """긴 DARK 이 헛 시한을 맞으면 안 된다 (labtest `exptime + FRAME_WAIT_MAX`).

    ⚠️ **고치기 전 판에서는 실패한다** -- 종전 계산이 `now + frame_timeout`
    이라, `IntMS` 를 걸고 **곧바로** 기다리는 DARK/BIAS 경로에서 적분 시간이
    상한을 넘으면 프레임이 정상으로 나오는 중에 `DMA WAIT TIMEOUT` 이 났다
    (셔터 노출은 시퀀서가 카운트다운을 다 하고 들어와서 안 걸린다).
    """
    from ics_archon.archon.controller import FrameTicket
    from ics_archon.archon.protocol import ArchonError

    fake = FakeArchon(status=dict(DEFAULT_STATUS), system=dict(DEFAULT_SYSTEM))
    fake.start()
    try:
        cfg = _cfg(tmp_path, frame_timeout=0.3, frame_poll=0.02,
                   connect_retry=1)
        cfg.hosts = {'MK': '127.0.0.1'}
        cfg.port = fake.port
        ctrl = ArchonController('MK', cfg)
        integrate = 1.0

        async def go():
            await ctrl.connect()
            ticket = FrameTicket(suffix='x', prev_frame=0,
                                 int_until=time.monotonic() + integrate)
            started = time.monotonic()
            with pytest.raises(ArchonError) as err:
                async for _pct in ctrl.wait_frame(ticket):
                    pass
            waited = time.monotonic() - started
            await ctrl.close()
            return waited, str(err.value)

        waited, message = asyncio.run(go())
        # 적분(1.0초)이 끝난 **뒤에** 0.3초를 센다 -- 종전 계산이면 0.3초에
        # 잘렸다.
        assert waited >= integrate, waited
        assert waited < integrate + 3.0, waited
        assert 'Sync In' in message                  # labtest 가 준 단서
    finally:
        fake.shutdown()


# ---------------------------------------------------------------------------
# D5 -- 첫 노출 전의 `-SYNCH`
# ---------------------------------------------------------------------------

def _backend(tmp_path):  # noqa: ANN001
    from ics_sim import config as simcfg
    cfg = simcfg.SimConfig()
    acfg = _cfg(tmp_path)
    acfg.hosts = {'MK': '127.0.0.1', 'NT': '127.0.0.1'}
    return ArchonBackend(cfg, acfg)


def test_synch_is_not_false_before_the_first_exposure(tmp_path):  # noqa: ANN001
    """G5/D5 -- 종전에는 첫 노출 전까지 **4채널 전부 `-SYNCH`** 로 보였다.

    `commands.py` 가 `ChannelState.synched` 기본값 `True` 를 백엔드 값으로
    덮으므로 침묵할 수 없다 -- 아무것도 모를 때는 "이상하다는 증거가 없다" 가
    맞다.
    """
    backend = _backend(tmp_path)
    ctrl = backend.ctrls['MK']
    assert ctrl.status == {} and ctrl.status_live == {}

    ctrl.link._sock = None
    assert backend.status('M')['synched'] is False       # 링크도 없다

    class _Up:
        connected = True
    ctrl.link = _Up()
    assert backend.status('M')['synched'] is True        # 링크는 올라왔다

    # 감시가 뜨면 그 값이 이긴다.
    ctrl.status_live = dict(DEFAULT_STATUS, POWERGOOD='0')
    assert backend.status('M')['synched'] is False


def test_synch_prefers_live_over_the_frozen_snapshot(tmp_path):  # noqa: ANN001
    backend = _backend(tmp_path)
    ctrl = backend.ctrls['MK']
    ctrl.status = dict(DEFAULT_STATUS, POWERGOOD='0')    # 노출 개시의 옛 값
    ctrl.status_live = dict(DEFAULT_STATUS, POWERGOOD='1')
    assert backend.status('M')['synched'] is True


# ---------------------------------------------------------------------------
# 배선 -- `IcsArchon` 이 실제로 감시를 띄우고 세우나
# ---------------------------------------------------------------------------

def test_app_starts_and_stops_the_monitors(tmp_path):  # noqa: ANN001
    """`app.py` 의 배선을 끝까지 돌린다 -- 여기가 안 덮이면 아무도 안 본다.

    ⚠️ **다른 시험들은 전부 `acfg.monitor = False` 로 둔다** (홈에 진짜 CSV 를
    쌓고 기동 시점에 링크를 잡기 때문이다).  그래서 `_start_monitors()` /
    `_stop_monitors()` 를 밟는 시험이 이것 하나뿐이다.

    보는 것 셋:

    1. 컨트롤러마다 파일이 하나씩 생기나 (`telemetry.<태그>.<날짜>.csv`)
    2. **`stop` 행이 남나** -- 원형 로그의 긴 공백이 "죽은 건가 끈 건가" 를 못
       가렸던 것이 이 행을 두는 이유다
    3. ⚠️ **헤더용 스냅샷이 안 오염됐나** -- 감시가 `ctrl.status` 를 덮으면
       `Cn_TEMP` 의 뜻이 조용히 바뀐다
    """
    import test_backend as tb
    from ics_archon.app import IcsArchon

    two = tb.TwoFakes()
    try:
        cfg, acfg, nt_port = tb.make_cfgs(tmp_path, two.mk, two.nt)
        acfg.monitor = True
        acfg.monitor_interval = 1.0             # 하한이 1.0 이다
        acfg.monitor_log = str(tmp_path / 'log')

        async def go():
            app = IcsArchon(cfg, acfg)
            app.backend.ctrls['NT'].link.port = nt_port
            await app.start()
            # 첫 표본이 나올 때까지만 기다린다 (start 행은 즉시 나간다).
            for _ in range(300):
                if all(m.ctrl.status_live for m in app._monitors):
                    break
                await asyncio.sleep(0.02)
            live = {t: dict(c.status_live) for t, c in app.backend.ctrls.items()}
            frozen = {t: dict(c.status) for t, c in app.backend.ctrls.items()}
            await app.stop()
            return live, frozen
        live, frozen = asyncio.run(go())
    finally:
        two.close()

    files = sorted(os.listdir(tmp_path / 'log'))
    assert len(files) == 2, files                # 컨트롤러당 하나
    assert all(f.startswith('telemetry.') and f.endswith('.csv') for f in files)

    for name in files:
        head, *rows = _rows(str(tmp_path / 'log' / name))
        events = [r[head.index('event')] for r in rows]
        assert events[0] == 'start'
        assert events[-1] == 'stop', events
        # ⚠️ **정상 종료에 `poll_failed` 가 섞이면 안 된다.**  세우라고 표시만
        # 하고 넘어가면 폴링 중이던 감시가 `POWEROFF`·`close()` 와 겹쳐 헛
        # 실패를 남기고, 그러면 **진짜 고장과 구별되지 않는다.**
        assert 'poll_failed' not in events, events
        assert 'offline' not in events, events
        assert 'BACKPLANE_TEMP' not in head       # 열 이름은 라벨이지 필드가 아니다
        assert 'T1_Backplane[C]' in head

    # 감시는 살아 있는 쪽만 채운다 -- 헤더용은 노출 개시에만 언다.
    assert all(v for v in live.values()), '감시가 아무것도 못 떴다'
    assert all(not f for f in frozen.values()), (
        '감시가 헤더용 스냅샷을 덮었다 -- Cn_TEMP 의 뜻이 바뀐다')


def test_app_connects_at_startup_even_with_monitoring_off(tmp_path):  # noqa: ANN001
    """**접속은 `monitor` 설정과 무관하다** (운영자 확정 2026-08-28).

    ⚠️ 처음 구현에서는 감시 태스크가 첫 폴링에서 자기가 접속을 열었다 -- 그러면
    `monitor = false` 가 **접속 시점까지 바꾼다.**  전제(일찍 접속돼 있을 것)를
    기능의 부수효과로 구현하면, 그 기능을 끄는 순간 전제도 함께 사라진다.
    """
    import test_backend as tb
    from ics_archon.app import IcsArchon

    two = tb.TwoFakes()
    try:
        cfg, acfg, nt_port = tb.make_cfgs(tmp_path, two.mk, two.nt)
        assert acfg.monitor is False            # make_cfgs 가 꺼 둔다

        async def go():
            app = IcsArchon(cfg, acfg)
            app.backend.ctrls['NT'].link.port = nt_port
            await app.start()
            up = {t: c.link.connected for t, c in app.backend.ctrls.items()}
            await app.stop()
            return up
        assert all(asyncio.run(go()).values())
    finally:
        two.close()


def test_startup_connect_failure_does_not_stop_the_app(tmp_path):  # noqa: ANN001
    """컨트롤러 전원이 나중에 들어오는 배치가 실재한다 -- 기동을 막지 않는다.

    막으면 그 배치가 통째로 못 돈다.  못 붙은 사실은 경고로 남고, 감시가
    주기마다 다시 시도한다(감시를 껐으면 첫 노출의 `prepare()` 가 시도한다).
    """
    import test_backend as tb
    from ics_archon.app import IcsArchon

    two = tb.TwoFakes()
    try:
        cfg, acfg, _nt_port = tb.make_cfgs(tmp_path, two.mk, two.nt)
        acfg.connect_retry = 1
        two.close()                              # 둘 다 죽여 놓고 띄운다

        async def go():
            app = IcsArchon(cfg, acfg)
            await app.start()                    # 예외가 나오면 안 된다
            up = any(c.link.connected for c in app.backend.ctrls.values())
            await app.stop()
            return up
        assert asyncio.run(go()) is False
    finally:
        two.close()


# ---------------------------------------------------------------------------
# 실기 ACF 정합 -- 층 2 의 열이 유닛마다 갈리지 않나
# ---------------------------------------------------------------------------

@pytest.mark.repo_only
def test_every_science_acf_declares_the_same_16_bias_channels():
    """**science 유닛 다섯이 같은 16채널을 선언한다** (2026-08-28 실측).

    이것이 깨지면 감시 CSV 의 **열 구성이 유닛마다 달라진다** -- 두 유닛의
    기록을 나란히 놓고 못 읽고, 나중에 층 2 를 헤더에 실을 때(D3) **자리 =
    항목** 규범이 유닛마다 다른 표를 요구하게 된다.  그 변화는 `CTRLnCFG`
    범프로 드러나야 하는 것이므로(규격 4.3절), 여기서 조용히 갈리면 안 된다.

    ⚠️ **guide 는 18채널이고 라벨도 다르다** -- 아래 시험이 그 사실을 못박는다.
    """
    import configparser
    import glob

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    science = sorted(glob.glob(os.path.join(root, 'acf', 'KMT*_SCI_*.acf')))
    assert len(science) == 5, science           # 실기 5종 (CTIO 2 · SAAO 1 · KASI 2)

    seen = {}
    for path in science:
        cp = configparser.RawConfigParser(strict=False)
        cp.read(path)
        cfg = {k.upper().replace(chr(92), '/'): v.replace('"', '')
               for k, v in cp.items('CONFIG')}
        seen[os.path.basename(path)] = tuple(
            label for _p, label in parse.bias_channels(cfg))

    expected = ('OG-A', 'CLAMP_N-A', 'CLAMP_P-A', 'CLAMP_P-B', 'CLAMP_N-B',
                'OG-B', 'DD-B', 'ODD-B', 'ODA-B', 'DD-A', 'ODD-A', 'ODA-A',
                'RDA-B', 'RDD-B', 'RDA-A', 'RDD-A')
    for name, labels in seen.items():
        assert labels == expected, name
    assert len(expected) == 16


@pytest.mark.repo_only
def test_guide_labels_contain_a_slash_which_matters_for_the_header():
    """⚠️ **guide 바이어스 라벨에 `/` 가 있다** (`VRDSR/L` 등, 2026-08-28 실측).

    CSV 열 이름으로는 무해하지만, **층 2 를 헤더에 실을 때(D3) 반드시 걸리는
    자리**다 -- 규격 5.6.1절이 "슬래시를 쓰지 말 것" 을 못박는다(FITS 의
    comment 구분자와 같은 글자라, 인용부호를 먼저 찾지 않는 파서에서 값이 첫
    슬래시에서 잘린다).  값이 아니라 라벨이라 지금은 안 걸리지만, 라벨을 카드
    이름·comment 로 옮기는 설계를 고르면 그때 걸린다.

    guide 는 **18채널**이라 science 10자리/8자리처럼 자리 수도 다르다.
    """
    import configparser
    import glob

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    guides = sorted(glob.glob(os.path.join(root, 'acf', 'kmtnet_guide_*.acf')))
    assert guides, 'guide ACF 가 없다'

    cp = configparser.RawConfigParser(strict=False)
    cp.read(guides[0])
    cfg = {k.upper().replace(chr(92), '/'): v.replace('"', '')
           for k, v in cp.items('CONFIG')}
    labels = [label for _p, label in parse.bias_channels(cfg)]
    assert len(labels) == 18, labels
    assert any('/' in label for label in labels), labels


@pytest.mark.parametrize('count_step, expect_fresh', [(1, '1'), (0, '0')])
def test_health_columns_carry_real_values_when_reported(tmp_path, count_step,  # noqa: ANN001
                                                        expect_fresh):
    """⚠️ **가짜가 실기보다 빈약하면 그 열은 한 번도 안 돌아 본다.**

    `DEFAULT_STATUS` 는 `VALID`/`COUNT`/`LOG`/`POWER`/`OVERHEAT` 를 **안 낸다** --
    그것도 실재하는 경우(구 펌웨어)라 지워서는 안 되지만, 그것만 있으면 기록의
    그 열들이 시험에서 늘 `NC` 다.  `FULL_STATUS` 가 매뉴얼 p.47 대로 다 내는
    쪽이고, 여기서 두 경로를 다 밟는다.

    `fresh` 는 `COUNT` 가 직전 행과 **달라졌나**다 -- `count_step=0` 이면
    컨트롤러가 같은 블록을 다시 준 경우이고, 그때 `0` 이 나와야 한다.
    """
    from fake_archon import FULL_STATUS

    cfg = _cfg(tmp_path)
    ctrl = _FakeCtrl(status=dict(FULL_STATUS))
    if count_step:
        # 폴링마다 COUNT 가 오르게 한다 (실기의 자기 주기 갱신을 흉내낸다).
        base = [int(FULL_STATUS['COUNT'])]

        async def _bump():
            base[0] += 1
            ctrl._status['COUNT'] = str(base[0])
            return await _FakeCtrl.refresh_status_live(ctrl)
        ctrl.refresh_status_live = _bump

    mon = TelemetryMonitor(ctrl, cfg)
    mon._stop = asyncio.Event()
    _run_monitor(mon, ticks=2)

    head, *rows = _rows(mon.log.path)
    samples = [r for r in rows if r[head.index('event')] == '']
    assert len(samples) >= 2, rows
    last = samples[-1]
    assert last[head.index('valid')] == '1'
    assert last[head.index('log_n')] == '0'      # ⚠️ '0' 과 NC 는 다른 뜻이다
    assert last[head.index('power')] == '4'
    assert last[head.index('overheat')] == '0'
    assert last[head.index('fresh')] == expect_fresh

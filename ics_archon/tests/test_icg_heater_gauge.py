#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""히터 다섯(`HTR*`)과 이온게이지(`VACGAUGE`) -- 운영자 확정 2026-09-04.

지키려는 것 넷:

* ⭐ **목표온도 한계에 상수가 없다** -- `HEATERASENSOR` 로 루프가 닫히는 센서를
  찾고 그 센서의 `SENSOR?LOWER/UPPERLIMIT` 를 쓴다.  ACF 가 바뀌면 따라온다.
* ⭐ **한계 밖은 거부가 아니라 클램프 + 응답 표시** (운영자 확정).
* ⭐ **전체가 아니라 그 모듈만 적용** -- 히터는 `APPLYMOD09`, 게이지는
  `APPLYDIO09`.  `APPLYALL` 은 CCD 클록·바이어스까지 다시 앉힌다.
* ⛔⛔ **게이지를 끈 동안 `DEWPRES` 를 싣지 않는다** -- MKS 356 은 이온게이지를
  끄면 Conductron 값을 계속 내보내고, 그 바닥값이 인정 범위 `[1e-8, 1e+3]` 를
  통과해 **정상으로 보이는 틀린 값**이 된다.

⭐ **키 이름은 손으로 적은 dict 가 아니라 실물 ACF 로 검증한다** -- `parse_acf`
가 `\\` 를 `/` 로 정규화하므로 표기를 잘못 적으면 조회가 다 빗나가는데, 가짜
dict 를 쓰면 그 상태로도 시험이 통과한다 (`test_icg_hk` 의 교훈).
"""

from __future__ import annotations

import asyncio
import os

import pytest

import ics_archon  # noqa: F401

from ics_archon.archon.controller import ArchonController, ArchonError  # noqa: E402

from icg_archon import gauge as gauge_mod  # noqa: E402
from icg_archon import heater  # noqa: E402
from icg_archon.config import IcgCfg, IcgConfigError, validate  # noqa: E402
from icg_archon.hk import HkMonitor  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE_ACF = os.path.join(ROOT, 'acf', 'KMTK_GUI_162_STA0201_R2610.acf')


class RecordingCtrl(ArchonController):
    """**실물 ACF 를 파싱한 진짜 컨트롤러 + 소켓만 가짜.**

    `cmd()` 하나만 갈아 끼우므로 줄 번호 조회·키 정규화·`RCONFIG` 응답 검사가
    **전부 실제 코드**를 지난다.  `sent` 에 나간 명령이 순서대로 쌓인다.
    """

    def __init__(self, acf: str = GUIDE_ACF) -> None:
        icfg = IcgCfg()
        icfg.acf = {'G': acf}
        super().__init__('G', icfg)
        self.parse_acf(acf)
        self.sent: list[str] = []
        self.fail_on = ''            # 이 글자가 든 명령을 실패시킨다

    async def cmd(self, command: str, timeout: float = 0.0) -> bytes:  # noqa: ANN001
        self.sent.append(command)
        if self.fail_on and self.fail_on in command:
            raise ArchonError('시험이 일부러 실패시킨 명령 -- %s' % command)
        if command.startswith('RCONFIG'):
            line = int(command[7:11], 16)
            for key, val in self.config.items():
                if self.configline.get(key) == line:
                    return ('%s=%s' % (key, val)).encode('ascii')
            return b''
        return b''

    def applies(self) -> list[str]:
        return [c for c in self.sent if c.startswith('APPLY')]

    def writes(self) -> list[str]:
        return [c for c in self.sent if c.startswith('WCONFIG')]


# -- 한계: ACF 를 두 걸음 탄다 ---------------------------------------------


def test_the_target_limits_come_from_the_acf_in_two_steps():
    """⭐ **상수 0개** -- 루프가 닫히는 센서를 찾고 그 센서의 한계를 쓴다.

    현행 guide ACF 는 `HEATERASENSOR=0` → `SENSORA`(`RTD9_DMP`, -150…50) 다.
    """
    ctrl = RecordingCtrl()
    lim = asyncio.run(heater.read_limits(ctrl))
    assert (lim.lo, lim.hi) == (-150.0, 50.0)
    assert lim.sensor == 'A'
    assert lim.label == 'RTD9_DMP'       # 출처를 응답에 적을 수 있어야 한다
    # 두 걸음이 실제로 두 번의 되읽기여야 한다 (센서 번호 → 그 센서의 한계).
    assert len(ctrl.sent) >= 3, ctrl.sent


def test_the_limits_follow_the_acf_when_the_loop_sensor_changes():
    """⭐ ACF 가 다른 센서로 루프를 닫으면 **한계도 따라간다.**

    `HEATERASENSOR` 를 1(B) 로 바꾸면 `SENSORB`(-120) 가 쓰여야 한다 -- 이게
    깨지면 한계가 사실은 코드에 박혀 있다는 뜻이다.
    """
    ctrl = RecordingCtrl()
    ctrl.config['MOD10/HEATERASENSOR'] = '1'
    lim = asyncio.run(heater.read_limits(ctrl))
    assert (lim.lo, lim.hi, lim.sensor) == (-120.0, 50.0, 'B')
    assert lim.label == 'RTD8_CCD'


def test_a_target_outside_the_limits_is_clamped_and_said_so():
    """⭐ **거부하지 않는다** -- 한계로 접고 접었다는 사실을 응답에 남긴다."""
    ctrl = RecordingCtrl()
    hot, note = asyncio.run(heater.set_target(ctrl, 60.0))
    assert hot == 50.0
    assert 'Clamped=60.00->50.00' in note
    assert 'SENSORA' in note and 'RTD9_DMP' in note   # 출처가 보여야 한다
    cold, note2 = asyncio.run(heater.set_target(ctrl, -200.0))
    assert cold == -150.0
    assert 'Clamped=-200.00->-150.00' in note2
    # 접힌 값이 **실제로 앉는다** -- 요청값이 아니라 클램프값을 쓴다.
    assert any('HEATERATARGET=-150' in c for c in ctrl.writes()), ctrl.writes()


def test_a_target_inside_the_limits_is_written_untouched():
    ctrl = RecordingCtrl()
    value, note = asyncio.run(heater.set_target(ctrl, -100.0))
    assert value == -100.0
    assert 'Clamped' not in note
    assert 'VCPU restarted' in note      # 결측 창은 늘 알린다
    assert any('MOD10/HEATERATARGET=-100' in c for c in ctrl.writes())


def test_the_target_is_not_written_when_the_limits_cannot_be_read():
    """⛔ 한계를 모르면 **쓰지 않는다** -- 클램프 없는 쓰기는 하지 않는다."""
    ctrl = RecordingCtrl()
    del ctrl.configline['MOD10/HEATERASENSOR']
    with pytest.raises(ArchonError):
        asyncio.run(heater.set_target(ctrl, -100.0))
    assert ctrl.writes() == []
    assert ctrl.applies() == []


# -- 적용 범위: 그 모듈만 -------------------------------------------------


def test_the_heater_applies_only_its_own_module():
    """⭐ `APPLYMOD09` 다 -- `APPLYALL` 이 아니다 (벤더 GUI 의 HeaterX Apply).

    ⚠️ 슬롯은 **0기점 16진**이라 MOD10 이 `09` 다.  1기점으로 보내면 옆
    모듈이 적용되고 그것은 조용히 틀린다.
    """
    ctrl = RecordingCtrl()
    asyncio.run(heater.set_enable(ctrl, True))
    assert ctrl.applies() == ['APPLYMOD09'], ctrl.applies()
    assert any('MOD10/HEATERAENABLE=1' in c for c in ctrl.writes())


def test_the_gauge_applies_the_dio_configuration():
    """게이지는 `APPLYDIO09` 다 -- DIO/VCPU 쪽 적용이다 (매뉴얼 p.53)."""
    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState()
    asyncio.run(state.set(ctrl, False))
    assert ctrl.applies() == ['APPLYDIO09'], ctrl.applies()
    assert any('MOD10/DIO_SOURCE3=0' in c for c in ctrl.writes())
    assert state.word == 'OFF'


def test_the_gauge_can_use_the_proven_diopower_key():
    """⭐ 벤치에서 `ionen` 이 안 통하면 **선례가 있는** 갈래로 한 줄만 바꾼다.

    보관함의 `…_goff_….acf` 가 형제 판과 **정확히 `MOD10\\DIO_POWER` 한 줄만**
    다르다 -- 선임이 실제로 쓴 길이다 (DevNote 11.19).
    """
    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState(gauge_mod.DIOPOWER)
    asyncio.run(state.set(ctrl, False))
    assert any('MOD10/DIO_POWER=0' in c for c in ctrl.writes()), ctrl.writes()
    assert not any('DIO_SOURCE3' in c for c in ctrl.writes())


# -- 상태: 거짓말하지 않는다 -----------------------------------------------


def test_the_gauge_state_is_read_back_from_the_controller_at_startup():
    """기동 상태는 **되읽은 설정값**이고 출처를 밝힌다 (게이지에 물은 게 아니다)."""
    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState()
    asyncio.run(state.load(ctrl))
    assert state.on is True              # ACF 출하값 DIO_SOURCE3=1
    assert state.origin == 'rconfig'


def test_an_unreadable_gauge_state_stays_unknown_and_does_not_block_dewpres():
    """⚠️ 못 읽으면 **모름**이다 -- 추측으로 ON 을 적지 않고, 막지도 않는다."""
    ctrl = RecordingCtrl()
    del ctrl.configline['MOD10/DIO_SOURCE3']
    state = gauge_mod.GaugeState()
    asyncio.run(state.load(ctrl))
    assert state.on is None and state.word == 'UNKNOWN'
    assert state.blocks_dewpres is False


def test_the_gauge_state_rolls_back_when_the_round_trip_fails():
    """⛔ 왕복이 실패하면 **껐다고 남겨 두지 않는다.**

    남겨 두면 반대 방향으로 거짓말한다 -- 필라멘트는 켜져 있는데 `DEWPRES` 만
    sentinel 로 내려가고, science 오염을 막으려던 명령이 조용히 무력해진다.
    """
    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState()
    asyncio.run(state.load(ctrl))
    assert state.on is True
    ctrl.fail_on = 'APPLYDIO'
    with pytest.raises(ArchonError):
        asyncio.run(state.set(ctrl, False))
    assert state.on is True, '실패한 왕복이 상태를 바꿨다'
    assert state.blocks_dewpres is False


def test_an_unknown_gauge_off_method_refuses_to_start():
    """⛔ 모르는 갈래로 기동하면 "껐다고 믿는데 안 꺼진" 상태가 된다."""
    with pytest.raises(ValueError):
        gauge_mod.GaugeState('powercycle')
    icfg = IcgCfg()
    icfg.acf = {'G': GUIDE_ACF}
    icfg.hosts = {'G': '10.0.0.162'}
    icfg.gauge_off_method = 'powercycle'
    with pytest.raises(IcgConfigError):
        validate(icfg, 'icg_archon')


# -- ⛔ Conductron 함정 -----------------------------------------------------


class _StatusCtrl:
    """`STATUS` 만 내는 최소 컨트롤러 -- 진공 VCPU 자리를 채운다."""

    def __init__(self) -> None:
        self.config: dict = {}
        self._alive = 1

    async def refresh_status_live(self) -> bool:
        # `6.93e-04` 10글자 + Alive.  Alive 는 바퀴마다 증가해야 신선하다.
        text = '6.93e-04  '
        self.status_live = {'MOD10/VCPU_OUTREG%d' % i: str(ord(c))
                            for i, c in enumerate(text)}
        self.status_live['MOD10/VCPU_OUTREG15'] = str(self._alive)
        self._alive += 1
        return True


def _monitor(tmp_path):  # noqa: ANN001, ANN202
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    return HkMonitor(_StatusCtrl(), icfg)


def test_dewpres_is_published_while_the_gauge_is_on(tmp_path):  # noqa: ANN001
    """기준선 -- 게이지가 켜져 있으면 값이 그대로 나간다."""
    mon = _monitor(tmp_path)
    mon.gauge = gauge_mod.GaugeState()
    mon.gauge.on = True
    asyncio.run(mon._tick(0.0))
    assert mon.sensors()['dewpres'] == '6.93e-04'


def test_dewpres_is_withheld_while_the_gauge_is_off(tmp_path):  # noqa: ANN001
    """⛔⛔ **끈 동안은 싣지 않는다** -- 그 값은 Conductron 이지 이온게이지가
    아니고, 바닥값이 `rawhdr` 의 인정 범위를 **통과해** 정상으로 보인다."""
    mon = _monitor(tmp_path)
    mon.gauge = gauge_mod.GaugeState()
    mon.gauge.on = False
    asyncio.run(mon._tick(0.0))
    assert 'dewpres' not in mon.sensors()


def test_turning_the_gauge_off_drops_the_previous_reading_at_once(tmp_path):  # noqa: ANN001
    """⭐ **직전 값을 즉시 버린다.**

    `sensors()` 의 신선도 창이 `interval*3`(기본 180초)이라, 안 버리면 껐는데도
    **3분 동안 옛 압력이 헤더로 나간다.**
    """
    mon = _monitor(tmp_path)
    mon.gauge = gauge_mod.GaugeState()
    mon.gauge.on = True
    asyncio.run(mon._tick(0.0))
    assert 'dewpres' in mon.sensors()
    mon.gauge.on = False                 # VACGAUGE OFF 가 일어난 순간
    asyncio.run(mon._tick(0.0))
    assert 'dewpres' not in mon.sensors(), '껐는데 옛 값이 남아 있다'


def test_the_log_records_why_the_vacuum_is_missing(tmp_path):  # noqa: ANN001
    """⭐ 결측의 **원인**을 로그에 남긴다 -- 안 그러면 나중에 "껐던 것" 과
    "게이지가 고장난 것" 을 구별할 수 없다 (DevNote 11.18-(3))."""
    import csv

    mon = _monitor(tmp_path)
    mon.gauge = gauge_mod.GaugeState()
    mon.gauge.on = False
    asyncio.run(mon._tick(0.0))
    name = [p for p in os.listdir(tmp_path) if p.startswith('hk.G.')][0]
    with open(os.path.join(tmp_path, name), encoding='utf-8', newline='') as fh:
        row = list(csv.DictReader(fh))[0]
    assert row['dewpres'] == ''                     # 헤더로는 안 간다
    assert row['gauge'] == 'OFF'                    # 원인이 남는다
    assert row['dewpres_conductron'] == '6.93e-04'  # 진단으로만 남는다


# -- 히터 나머지 셋: HTRFORCE · HTRRAMP · HTRPID ---------------------------
#
# ⭐ 지키려는 것 셋:
#   · **적용은 명령당 한 번** -- 파라미터를 둘·셋 만져도 VCPU 결측 창은 하나
#   · **범위 밖은 클램프가 아니라 거부** (`TARGET` 과 규약이 다른 것이 의도)
#   · **환산에 상수 0개** -- `RAMPRATE` 의 뜻은 ACF 의 `HEATERUPDATETIME` 이
#     정한다


def test_force_writes_both_keys_and_applies_once():
    """⭐ **적용은 한 번**이다 -- 키마다 적용하면 결측 창이 둘이 된다.

    ⚠️ 그리고 반쯤 적용된 창도 없어야 한다: `FORCE=1` 은 앉았는데
    `FORCELEVEL` 은 아직 옛 값인 상태로 한 주기가 돌면 안 된다.
    """
    ctrl = RecordingCtrl()
    note = asyncio.run(heater.set_force(ctrl, True, 3.5))
    assert any('MOD10/HEATERAFORCE=1' in c for c in ctrl.writes()), ctrl.writes()
    assert any('MOD10/HEATERAFORCELEVEL=3.5' in c for c in ctrl.writes())
    assert ctrl.applies() == ['APPLYMOD09'], ctrl.applies()
    # ⛔ PID 상한이 안 걸린다는 사실을 응답이 말해야 한다.
    assert 'HEATERALIMIT does not apply' in note
    assert 'VCPU restarted' in note


def test_turning_force_off_also_writes_the_level():
    """⚠️ `FORCE=0` 만 보내면 **잊고 있던 전압이 나중에 되살아난다.**

    다음에 누가 `HTRFORCE 1 …` 을 치기 전에 레벨이 옛 값으로 남아 있으면,
    그 사람이 넣은 값이 아닌 것이 나갈 수 있다.
    """
    ctrl = RecordingCtrl()
    note = asyncio.run(heater.set_force(ctrl, False, 0.0))
    assert any('MOD10/HEATERAFORCE=0' in c for c in ctrl.writes())
    assert any('MOD10/HEATERAFORCELEVEL=0' in c for c in ctrl.writes())
    assert 'HEATERALIMIT' not in note      # 끈 상태에서는 그 경고가 없다


@pytest.mark.parametrize('level', [-0.1, 25.1, 1e6])
def test_a_force_level_outside_the_module_range_is_refused(level):  # noqa: ANN001
    """⛔ **접지 않고 거부한다** -- 여기서 접으면 25 라고 친 사람에게 2.5 가 앉는다.

    ⭐ 별도 운영 상한은 없다 (운영자 확정 2026-09-04) -- 막는 것은 모듈이
    받는 범위 `0…25 V` 뿐이고, 그 안에서는 운영이 알아서 정한다.
    """
    ctrl = RecordingCtrl()
    with pytest.raises(ValueError):
        asyncio.run(heater.set_force(ctrl, True, level))
    assert ctrl.writes() == [] and ctrl.applies() == []


def test_the_ramp_rate_is_converted_with_the_acf_update_time():
    """⭐ **환산에 상수 0개** -- `RAMPRATE` 는 초당이 아니라 update time 당이다.

    현행 ACF 는 `HEATERUPDATETIME=1000` ms 라 `1` = 1 mK/s = 3.6 K/h 다.
    """
    ctrl = RecordingCtrl()
    note = asyncio.run(heater.set_ramp(ctrl, True, 1))
    assert '1 mK/s' in note and '3.6 K/h' in note, note
    assert 'UPDATETIME=1000ms' in note
    assert any('MOD10/HEATERARAMP=1' in c for c in ctrl.writes())
    assert any('MOD10/HEATERARAMPRATE=1' in c for c in ctrl.writes())
    assert ctrl.applies() == ['APPLYMOD09']


def test_the_conversion_follows_the_acf_when_the_update_time_changes():
    """⚠️ `UPDATETIME` 이 바뀌면 **같은 값의 뜻이 바뀐다** -- 1000 을 안 박았다.

    이게 깨지면 환산이 사실은 코드에 박혀 있다는 뜻이다.
    """
    ctrl = RecordingCtrl()
    ctrl.config['MOD10/HEATERUPDATETIME'] = '500'
    note = asyncio.run(heater.set_ramp(ctrl, True, 1))
    assert '2 mK/s' in note and '7.2 K/h' in note, note


def test_the_ramp_is_written_even_when_the_conversion_cannot_be_read():
    """⚠️ 환산을 못 읽어도 **명령은 수행한다** -- 다만 환산 문구는 뺀다.

    틀린 환산을 보이느니 안 보이는 편이 낫고, 그 때문에 램프 설정 자체를
    막을 이유는 없다.
    """
    ctrl = RecordingCtrl()
    del ctrl.configline['MOD10/HEATERUPDATETIME']
    note = asyncio.run(heater.set_ramp(ctrl, True, 4))
    assert 'mK/s' not in note
    assert 'VCPU restarted' in note
    assert any('MOD10/HEATERARAMPRATE=4' in c for c in ctrl.writes())


@pytest.mark.parametrize('rate', [0, 32768, -1])
def test_a_ramp_rate_outside_the_range_is_refused(rate):  # noqa: ANN001
    ctrl = RecordingCtrl()
    with pytest.raises(ValueError):
        asyncio.run(heater.set_ramp(ctrl, True, rate))
    assert ctrl.writes() == [] and ctrl.applies() == []


def test_pid_writes_three_gains_and_applies_once():
    """⭐ **이 명령이 있어야 히터가 데워진다** -- 현행 ACF 는 게인이 전부 0이다.

    ⚠️ 적용은 셋을 다 쓴 **뒤 한 번**이다 -- 게인마다 적용하면 결측 창이
    셋이 되고, 그 사이 반쯤 바뀐 게인으로 루프가 돈다.
    """
    ctrl = RecordingCtrl()
    note = asyncio.run(heater.set_pid(ctrl, 1.5, 0.25, 0))
    for key, val in (('P', '1.5'), ('I', '0.25'), ('D', '0')):
        assert any('MOD10/HEATERA%s=%s' % (key, val) in c
                   for c in ctrl.writes()), (key, ctrl.writes())
    assert ctrl.applies() == ['APPLYMOD09'], ctrl.applies()
    assert 'VCPU restarted' in note


@pytest.mark.parametrize('gains', [(-1, 0, 0), (0, 10000.1, 0), (0, 0, 1e9)])
def test_pid_gains_outside_the_range_are_refused(gains):  # noqa: ANN001
    """⛔ 하나라도 밖이면 **셋 다 안 쓴다** -- 반만 앉은 게인이 더 나쁘다."""
    ctrl = RecordingCtrl()
    with pytest.raises(ValueError):
        asyncio.run(heater.set_pid(ctrl, *gains))
    assert ctrl.writes() == [] and ctrl.applies() == []


# -- 조회: 캐시가 아니라 RCONFIG ------------------------------------------


@pytest.mark.parametrize('cmdword, want', [
    ('HTREN', 'Enable=0'),
    ('HTRSET', 'Target=0'),          # 현행 ACF 의 출하값
    ('HTRFORCE', 'Force=0 Level=0'),
    ('HTRRAMP', 'Ramp=0 RampRate=1'),
    ('HTRPID', 'P=0 I=0 D=0'),
])
def test_a_query_reads_the_group_back_from_the_controller(cmdword, want):  # noqa: ANN001
    """⭐ 이름표와 키의 짝은 `heater.GROUPS` 한 표가 정한다.

    ⚠️ 값은 **실물 ACF 에서 온다** -- 손으로 적은 dict 를 쓰면 키 표기를
    잘못 적어도 시험이 통과한다.
    """
    ctrl = RecordingCtrl()
    got = asyncio.run(heater.read_group(ctrl, cmdword))
    assert got == want, got
    # ⚠️ 되읽기다 -- 쓰기가 섞이면 안 된다.
    assert ctrl.writes() == [] and ctrl.applies() == []


def test_a_query_fails_whole_rather_than_answering_in_part():
    """⚠️ 일부만 답하면 나머지가 **옛 값인지 못 읽은 것인지** 구별되지 않는다."""
    ctrl = RecordingCtrl()
    del ctrl.configline['MOD10/HEATERAD']
    with pytest.raises(ArchonError):
        asyncio.run(heater.read_group(ctrl, 'HTRPID'))

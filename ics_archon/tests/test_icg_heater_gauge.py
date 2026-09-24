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
GUIDE_ACF = os.path.join(ROOT, 'acf', 'KMTK_GUI_162_STA0201_R2622.acf')


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
        #: 실패의 모양 -- `True` 면 컨트롤러의 `?xx` 거부(`reply_error=True`,
        #: 적용 안 됨이 확실), `False` 면 응답 유실(시한 초과·링크 끊김 -- 적용
        #: 여부를 모른다).  `fail_exc` 를 주면 그 예외를 그대로 던진다.
        self.fail_reply_error = False
        self.fail_exc: BaseException | None = None

    async def cmd(self, command: str, timeout: float = 0.0) -> bytes:  # noqa: ANN001
        self.sent.append(command)
        if self.fail_on and self.fail_on in command:
            if self.fail_exc is not None:
                raise self.fail_exc
            raise ArchonError('시험이 일부러 실패시킨 명령 -- %s' % command,
                              cmd=command, reply_error=self.fail_reply_error)
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
    hot, note = asyncio.run(heater.set_target(ctrl, True, 60.0))
    assert hot == 50.0
    assert 'Clamped=60.00->50.00' in note
    assert 'SENSORA' in note and 'RTD9_DMP' in note   # 출처가 보여야 한다
    cold, note2 = asyncio.run(heater.set_target(ctrl, True, -200.0))
    assert cold == -150.0
    assert 'Clamped=-200.00->-150.00' in note2
    # 접힌 값이 **실제로 앉는다** -- 요청값이 아니라 클램프값을 쓴다.
    assert any('HEATERATARGET=-150' in c for c in ctrl.writes()), ctrl.writes()


def test_a_target_inside_the_limits_is_written_untouched():
    ctrl = RecordingCtrl()
    value, note = asyncio.run(heater.set_target(ctrl, True, -100.0))
    assert value == -100.0
    assert 'Clamped' not in note
    assert 'VCPU restarted' in note      # 결측 창은 늘 알린다
    assert any('MOD10/HEATERATARGET=-100' in c for c in ctrl.writes())


def test_the_target_is_not_written_when_the_limits_cannot_be_read():
    """⛔ 한계를 모르면 **쓰지 않는다** -- 클램프 없는 쓰기는 하지 않는다."""
    ctrl = RecordingCtrl()
    del ctrl.configline['MOD10/HEATERASENSOR']
    with pytest.raises(ArchonError):
        asyncio.run(heater.set_target(ctrl, True, -100.0))
    assert ctrl.writes() == []
    assert ctrl.applies() == []


# -- 적용 범위: 그 모듈만 -------------------------------------------------


def test_the_heater_applies_only_its_own_module():
    """⭐ `APPLYMOD09` 다 -- `APPLYALL` 이 아니다 (벤더 GUI 의 HeaterX Apply).

    ⚠️ 슬롯은 **0기점 16진**이라 MOD10 이 `09` 다.  1기점으로 보내면 옆
    모듈이 적용되고 그것은 조용히 틀린다.
    """
    ctrl = RecordingCtrl()
    asyncio.run(heater.set_target(ctrl, True, -100.0))
    assert ctrl.applies() == ['APPLYMOD09'], ctrl.applies()
    # ⭐ `HTRSET` 은 **둘을 한 번에** 쓴다 (운영자 확정 2026-09-04) -- Enable 만
    # 앉고 목표는 옛 값인 창을 만들지 않는다.
    assert any('MOD10/HEATERAENABLE=1' in c for c in ctrl.writes())
    assert any('MOD10/HEATERATARGET=-100' in c for c in ctrl.writes())


def test_the_gauge_applies_the_dio_configuration():
    """게이지는 `APPLYDIO09` 다 -- DIO/VCPU 쪽 적용이다 (매뉴얼 p.53).

    ✅ **기본 갈래는 `diopower`** 다 -- 운영자가 `MOD10\\DIO_POWER=1/0` 으로
    On/Off 가 되는 것을 실측으로 확인했다 (2026-09-04).  보관함의
    `…_goff_….acf` 가 형제 판과 정확히 그 한 줄만 다른 것과도 맞는다.
    """
    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState()
    asyncio.run(state.set(ctrl, False))
    assert ctrl.applies() == ['APPLYDIO09'], ctrl.applies()
    assert any('MOD10/DIO_POWER=0' in c for c in ctrl.writes()), ctrl.writes()
    assert state.word == 'OFF'


def test_the_unverified_ionen_key_is_still_reachable():
    """⏳ `ionen` 은 **미검증이지만 지운 것이 아니다** -- ini 한 줄로 고른다.

    읽기를 살린 채 필라멘트만 끄는 쪽이라 실기에서 확인되면 그쪽이 낫다.
    ⚠️ 고르면 기동이 미검증이라고 경고한다 (`config.validate`).
    """
    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState(gauge_mod.IONEN)
    asyncio.run(state.set(ctrl, False))
    assert any('MOD10/DIO_SOURCE3=0' in c for c in ctrl.writes()), ctrl.writes()
    assert not any('DIO_POWER' in c for c in ctrl.writes())


def test_the_default_method_is_the_measured_one():
    """⚠️ 기본이 미검증 갈래로 되돌아가면 첫 관측에서 안 꺼질 수 있다."""
    assert gauge_mod.GaugeState().method == gauge_mod.DIOPOWER
    assert IcgCfg().gauge_off_method == gauge_mod.DIOPOWER


def test_choosing_the_unverified_method_warns_at_startup():
    """⏳ 미검증 갈래를 고른 것은 **조용하면 안 된다**."""
    icfg = IcgCfg()
    icfg.acf = {'G': GUIDE_ACF}
    icfg.hosts = {'G': '10.0.0.162'}
    icfg.gauge_off_method = gauge_mod.IONEN
    said = '\n'.join(validate(icfg, 'icg_archon'))
    assert 'ionen' in said and '미검증' in said, said


# -- 상태: 거짓말하지 않는다 -----------------------------------------------


def test_the_gauge_state_is_read_back_from_the_controller_at_startup():
    """기동 상태는 **되읽은 설정값**이고 출처를 밝힌다 (게이지에 물은 게 아니다)."""
    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState()
    asyncio.run(state.load(ctrl))
    # ⭐ **ACF 파일값을 그대로 읽는다** -- R2619 부터 `MOD10\DIO_POWER=0` 이다
    # (그 전 판은 1 이었고, science 노출 중 재실행이 게이지를 켜 버렸다).
    assert state.on is False
    assert state.origin == 'rconfig'


def test_an_unreadable_gauge_state_stays_unknown_and_does_not_block_dewpres():
    """⚠️ 못 읽으면 **모름**이다 -- 추측으로 ON 을 적지 않고, 막지도 않는다."""
    ctrl = RecordingCtrl()
    del ctrl.configline['MOD10/DIO_POWER']
    state = gauge_mod.GaugeState()
    asyncio.run(state.load(ctrl))
    assert state.on is None and state.word == 'UNKNOWN'
    assert state.blocks_dewpres is False


def test_the_gauge_state_rolls_back_when_the_round_trip_is_refused():
    """⛔ 적용이 안 된 것이 **확실한** 실패는 **직전 상태로 되돌린다**
    (`GaugeState.set` 머리말 표).

    확실한 경우는 둘이다 -- `APPLYDIO09` 를 컨트롤러가 `?xx` 로 거부했거나
    (`reply_error=True`), 그 앞의 `WCONFIG` 에서 멈춰 `APPLYDIO09` 가 아예 안
    나갔거나.  성공한 것처럼 남겨 두면 반대 방향으로 거짓말한다 -- 켜려다
    실패했는데 켰다고 남기면 열손실 센서 값이 `DEWPRES` 로 실리고, 끄려다
    실패했는데 껐다고 남기면 필라멘트는 켜져 있는데 `DEWPRES` 만 sentinel 로
    내려간다.
    """
    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState()
    asyncio.run(state.load(ctrl))
    assert state.on is False             # R2619 ACF 는 꺼진 채로 나온다
    ctrl.fail_on, ctrl.fail_reply_error = 'APPLYDIO', True
    with pytest.raises(ArchonError):
        asyncio.run(state.set(ctrl, True))
    assert state.on is False, '실패한 왕복이 상태를 바꿨다'
    # ⭐ 셋 다 돌아온다 -- `origin`·`on_at` 이 남으면 낱말(`WARMUP`)이 거짓이 된다.
    assert state.origin == 'rconfig' and state.on_at is None
    assert state.word == 'OFF'
    # ⭐ **방향이 뒤집혔다** (R2619 부터 ACF 가 꺼진 채로 나온다) -- 켜려다
    # 실패했으니 게이지는 여전히 꺼져 있고, 그러면 `DEWPRES` 를 **막아야**
    # 한다 (꺼도 같은 모듈의 열손실 센서가 값을 계속 낸다).
    assert state.blocks_dewpres is True

    # ② 반대 방향 -- 켜진 게이지를 끄려다 거부되면 **켜진 채**로 남는다.
    ctrl.fail_on = ''
    asyncio.run(state.set(ctrl, True))
    on_at = state.on_at
    assert state.on is True and on_at is not None
    ctrl.fail_on = 'APPLYDIO'
    with pytest.raises(ArchonError):
        asyncio.run(state.set(ctrl, False))
    assert state.on is True, '끄기에 실패했는데 껐다고 남겼다'
    assert state.origin == 'command' and state.on_at == on_at

    # ③ `WCONFIG` 에서 멈추면 **예외 종류와 무관하게** 되돌린다 -- 응답을 잃어도
    # `APPLYDIO09` 가 안 나갔으니 물리 상태는 직전 그대로다.
    ctrl.fail_on, ctrl.fail_reply_error = 'WCONFIG', False
    before = len(ctrl.applies())
    with pytest.raises(ArchonError):
        asyncio.run(state.set(ctrl, False))
    assert len(ctrl.applies()) == before, 'WCONFIG 가 실패했는데 적용을 냈다'
    assert state.on is True and state.on_at == on_at


@pytest.mark.parametrize('exc', [
    None,                                        # reply_error 없는 ArchonError
    TimeoutError('시험이 일부러 잃은 응답'),
    ConnectionResetError('시험이 일부러 끊은 링크'),   # OSError
], ids=['archon-no-reply', 'timeout', 'oserror'])
def test_a_lost_applydio_answer_leaves_the_gauge_unknown(exc):  # noqa: ANN001
    """⛔ `APPLYDIO09` 의 응답을 잃으면 **모름**이다 -- 직전 상태로 되돌리지 않는다.

    컨트롤러가 받아 **적용한 뒤 응답만 잃었을 수 있다**.  켜려다 그렇게 됐는데
    직전 `OFF` 로 되돌리면, 실제로는 켜졌을 수 있는 게이지를 `OFF` 라 적고 --
    ICS 는 `HKDATA NOW` 의 `VACGAUGE=OFF` 를 보면 `VACGAUGE OFF` 를 **건너뛰므로**
    (`ics_archon/gaugectl.py` `before_exposure`) 필라멘트가 켜진 채 science
    노출이 나간다.  `UNKNOWN` 이면 ICS 가 다음 science 노출 전에 `OFF` 를 보낸다.
    """
    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState()
    asyncio.run(state.load(ctrl))
    assert state.word == 'OFF'
    ctrl.fail_on, ctrl.fail_exc = 'APPLYDIO', exc
    with pytest.raises(type(exc) if exc is not None else ArchonError):
        asyncio.run(state.set(ctrl, True))
    assert ctrl.applies() == ['APPLYDIO09'], 'APPLYDIO09 가 나가야 이 갈래다'
    assert state.on is None and state.origin == 'failed' and state.on_at is None
    assert state.word == 'UNKNOWN', '적용 여부를 모르는데 상태를 단정했다'
    # 모름은 `DEWPRES` 를 막지 않는다 (`blocks_dewpres` 머리말).
    assert state.blocks_dewpres is False


def test_a_refused_applydio_puts_the_previous_value_back():
    """⭐ `APPLYDIO09` 가 거부되면 **설정 메모리에 직전 값을 되쓴다** (`WCONFIG` 한 번).

    `WCONFIG` 는 앉았으므로 메모리에 새 값이 남고, 뒤의 히터 쪽 `APPLYMOD09`
    (`HTR*` 명령 · 과열 차단)가 그 값을 적용할 수 있다 (`GaugeState.set` 머리말의
    *"새 값이 남는다"* 문단).  ⚠️ 되쓰기가 적용(`APPLY*`)을 또 내면 안 된다 --
    적용은 VCPU 를 재시작한다.  ⭐ 올라오는 예외는 **원래 것**(`APPLYDIO09` 거부)이다.
    """
    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState()
    asyncio.run(state.load(ctrl))
    assert state.word == 'OFF'
    ctrl.fail_on, ctrl.fail_reply_error = 'APPLYDIO', True
    with pytest.raises(ArchonError) as err:
        asyncio.run(state.set(ctrl, True))
    assert err.value.cmd == 'APPLYDIO09', '원래 예외가 아니다'
    assert [w.split('MOD10/')[-1] for w in ctrl.writes()] == [
        'DIO_POWER=1', 'DIO_POWER=0'], ctrl.writes()
    assert ctrl.applies() == ['APPLYDIO09'], '되쓰기가 적용을 또 냈다'
    assert ctrl.config['MOD10/DIO_POWER'] == '0'
    assert state.word == 'OFF' and state.origin == 'rconfig'

    # ② 직전 상태가 모름이면 **되쓸 값을 모르므로 쓰지 않는다** -- 모름 그대로.
    ctrl2 = RecordingCtrl()
    ctrl2.fail_on, ctrl2.fail_reply_error = 'APPLYDIO', True
    blank = gauge_mod.GaugeState()
    with pytest.raises(ArchonError):
        asyncio.run(blank.set(ctrl2, True))
    assert len(ctrl2.writes()) == 1, '모르는 직전 값을 지어내 되썼다'
    assert blank.word == 'UNKNOWN'


class _PutBackFailsCtrl(RecordingCtrl):
    """`APPLYDIO09` 는 거부(`?xx`)하고, 그 뒤 **되쓰기(`DIO_POWER=0`)는 응답을 잃는다.**"""

    async def cmd(self, command: str, timeout: float = 0.0) -> bytes:  # noqa: ANN001
        if command.startswith('APPLYDIO'):
            self.sent.append(command)
            raise ArchonError('시험이 일부러 거부한 명령 -- %s' % command,
                              cmd=command, reply_error=True)
        if command.startswith('WCONFIG') and command.endswith('DIO_POWER=0'):
            self.sent.append(command)
            raise TimeoutError('시험이 일부러 잃은 되쓰기 응답')
        return await super().cmd(command, timeout)


def test_a_failed_put_back_leaves_the_gauge_unknown_and_keeps_the_original_error(
        caplog):  # noqa: ANN001
    """⛔ 되쓰기도 실패하면 **모름** -- 메모리에 새 값이 남았을 수 있다.

    뒤의 히터 쪽 `APPLYMOD09` 가 그 값을 적용하면 게이지가 바뀌므로 직전 상태를
    단정하지 않는다.  ⭐ 되쓰기의 실패가 **원래 예외를 가리지 않는다** -- 올라오는
    것은 `APPLYDIO09` 거부이고, 되쓰기 실패는 경고 한 줄(영문 + `detail`)로 남는다.
    """
    import logging

    ctrl = _PutBackFailsCtrl()
    state = gauge_mod.GaugeState()
    asyncio.run(state.load(ctrl))
    assert state.word == 'OFF'
    with caplog.at_level(logging.WARNING, logger='icg_archon.gauge'):
        with pytest.raises(ArchonError) as err:
            asyncio.run(state.set(ctrl, True))
    assert err.value.cmd == 'APPLYDIO09' and err.value.reply_error is True
    assert state.on is None and state.origin == 'failed' and state.on_at is None
    assert state.word == 'UNKNOWN', '되쓰기가 실패했는데 직전 상태를 단정했다'
    warns = [r for r in caplog.records if 'could not put' in r.getMessage()]
    assert len(warns) == 1, [r.getMessage() for r in caplog.records]
    assert 'APPLYMOD09' in warns[0].detail and 'TimeoutError' in warns[0].detail


class _OverlapCtrl(RecordingCtrl):
    """두 `set()` 을 **겹치게** 하는 문 둘.

    * 첫 `APPLYDIO09` -- 나갔다고 알리고(`applydio_out`) 문(`lose`)이 열릴 때까지
      매달렸다가 **응답을 잃는다** (`TimeoutError` -- 적용 여부 모름).
    * `DIO_POWER=1` 을 쓰는 `WCONFIG` -- 문(`refuse`)이 열릴 때까지 매달렸다가
      **실패한다** (`WCONFIG` 실패 -- 미적용이 확실하다).
    """

    def __init__(self) -> None:
        super().__init__()
        self.applydio_out = asyncio.Event()
        self.lose = asyncio.Event()
        self.refuse = asyncio.Event()

    async def cmd(self, command: str, timeout: float = 0.0) -> bytes:  # noqa: ANN001
        if command.startswith('APPLYDIO') and not self.applydio_out.is_set():
            self.sent.append(command)
            self.applydio_out.set()
            await self.lose.wait()
            raise TimeoutError('시험이 일부러 잃은 APPLYDIO09 응답')
        if command.startswith('WCONFIG') and command.endswith('DIO_POWER=1'):
            self.sent.append(command)
            await self.refuse.wait()
            raise ArchonError('시험이 일부러 실패시킨 명령 -- %s' % command,
                              cmd=command)
        return await super().cmd(command, timeout)


def test_overlapping_gauge_commands_never_leave_a_stale_off():
    """⛔ 겹친 두 `set()` 이 **필라멘트가 켜졌을 수 있는데 `OFF`** 를 남기면 안 된다.

    `VACGAUGE` 는 명령마다 태스크를 띄우므로(`commands._do_vacgauge`) 두 호출이
    겹칠 수 있다.  켜진 게이지를 끄려던 앞 호출은 `APPLYDIO09` 응답을 잃어
    `UNKNOWN` 이 되고, 켜려던 뒤 호출은 `WCONFIG` 에서 실패해 직전 상태로
    되돌린다.  ⛔ 락이 없으면 뒤 호출의 직전 상태가 **앞 호출의 선반영 `OFF`**
    라서 `UNKNOWN` 을 `OFF` 로 덮는다 -- ICS 는 `VACGAUGE=OFF` 를 보면
    `VACGAUGE OFF` 를 건너뛰어 필라멘트가 켜진 채 science 노출이 나간다.
    ⭐ `GaugeState._lock` 이 둘을 한 줄로 세운다 (`GaugeState.set` 머리말).
    """
    async def scenario():  # noqa: ANN202
        ctrl = _OverlapCtrl()
        ctrl.config['MOD10/DIO_POWER'] = '1'          # 켜진 게이지에서 시작
        state = gauge_mod.GaugeState()
        await state.load(ctrl)
        assert state.word == 'ON'
        first = asyncio.create_task(state.set(ctrl, False))
        await ctrl.applydio_out.wait()                # 앞 호출이 APPLYDIO09 를 냈다
        second = asyncio.create_task(state.set(ctrl, True))
        for _ in range(10):                           # 뒤 호출이 갈 수 있는 데까지
            await asyncio.sleep(0)
        # ⭐ 뒤 호출은 앞 호출이 끝날 때까지 `WCONFIG` 도 내지 않는다.
        assert len(ctrl.writes()) == 1, ctrl.writes()
        ctrl.lose.set()
        with pytest.raises(TimeoutError):
            await first
        # ⚠️ 여기서 낱말을 보지 않는다 -- 락을 넘겨받은 뒤 호출이 벌써 선반영
        # (`WARMUP`)을 했을 수 있다.  보는 것은 뒤 호출이 끝난 뒤의 낱말이다.
        ctrl.refuse.set()
        with pytest.raises(ArchonError):
            await second
        return state, ctrl

    state, ctrl = asyncio.run(scenario())
    assert len(ctrl.writes()) == 2, ctrl.writes()
    assert state.word != 'OFF', '켜졌을 수 있는 게이지를 OFF 라 적었다'
    assert state.word == 'UNKNOWN' and state.origin == 'failed'


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
    ('HTRSET', 'Enable=0 Target=0'),   # 현행 ACF 의 출하값
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


# -- ⛔ 되먹임 센서 과열 차단 (운영자 지시 2026-09-06) ------------------------
#
# *"지정된 HEATER의 feedback sensor의 상한 설정을 넘으면 HEATER가 꺼지도록"* +
# *"이 값은 변동될 수 있어.  ACF의 설정을 따라가게 해야되."*
#
# 지키려는 것 다섯:
#   · ⭐ 상한이 **ACF 에서 온다** -- 코드에 50 이 없다
#   · ⭐ 루프 센서가 바뀌면 **보는 온도도 바뀐다**
#   · 끌 때 `FORCE`·`FORCELEVEL`·`ENABLE` **셋을 한 번에** (반쯤 꺼진 창이 없다)
#   · ⚠️ **결측으로는 안 끈다** -- 우리 히터 명령이 MOD10 VCPU 를 재시작해
#     STATUS 에 구멍을 내므로(11.18), 결측을 과열로 읽으면 우리 명령이 우리
#     차단을 부른다
#   · 같은 초과로 **두 번 쓰지 않는다** (매 바퀴 VCPU 를 재시작하게 된다)


def _status(**kw):  # noqa: ANN003, ANN202
    """STATUS 최소 dict.  ⚠️ 키 구분자는 `/` 다 (`parse_acf` 정규화 규약)."""
    out = {'VALID': '1'}
    out.update(kw)
    return out


def test_the_overtemp_limit_comes_from_the_acf_not_the_code():
    """⭐ **상수 0개** -- `HEATERASENSOR` → `SENSORA`(`RTD9_DMP`, 상한 50)."""
    ctrl = RecordingCtrl()
    guard = heater.OverTempGuard()
    note = asyncio.run(guard.check(ctrl, _status(**{'MOD10/TEMPA': '-120.0'})))
    assert guard.limits.hi == 50.0 and guard.limits.sensor == 'A'
    assert guard.limits.label == 'RTD9_DMP'
    assert note == '' and ctrl.writes() == []   # 정상 온도에서는 안 쓴다


def test_the_heater_is_turned_off_above_the_acf_upper_limit():
    """⛔ 강제도 PID 도 끈다 -- 한쪽만 끄면 **안 끈 것**이다."""
    ctrl = RecordingCtrl()
    guard = heater.OverTempGuard()
    note = asyncio.run(guard.check(ctrl, _status(**{'MOD10/TEMPA': '50.1'})))
    w = ctrl.writes()
    assert any('MOD10/HEATERAFORCE=0' in c for c in w), w
    assert any('MOD10/HEATERAFORCELEVEL=0' in c for c in w), w
    assert any('MOD10/HEATERAENABLE=0' in c for c in w), w
    # ⭐ 적용은 한 번 -- `DEWPRES` 결측 창도 하나여야 한다.
    assert ctrl.applies() == ['APPLYMOD09'], ctrl.applies()
    assert 'HEATER OFF' in note and '50.10' in note
    assert guard.tripped


def test_the_trip_follows_the_acf_when_the_upper_limit_changes():
    """⭐ ACF 상한을 30 으로 낮추면 **31 에서** 끊긴다 -- 50 이 코드에 없다는 증거."""
    ctrl = RecordingCtrl()
    ctrl.config['MOD10/SENSORAUPPERLIMIT'] = '30.0'
    guard = heater.OverTempGuard()
    asyncio.run(guard.check(ctrl, _status(**{'MOD10/TEMPA': '31.0'})))
    assert guard.tripped, 'ACF 상한을 안 따라갔다 -- 값이 코드에 박혀 있다'
    assert guard.limits.hi == 30.0


def test_the_guard_watches_the_sensor_the_loop_is_closed_on():
    """⭐ 루프가 B 로 닫히면 **A 가 아무리 뜨거워도** 안 끈다.

    되먹임이 아닌 센서로 끄면, 히터와 무관한 채널의 노이즈가 히터를 내린다.
    """
    ctrl = RecordingCtrl()
    ctrl.config['MOD10/HEATERASENSOR'] = '1'
    guard = heater.OverTempGuard()
    note = asyncio.run(guard.check(ctrl, _status(**{'MOD10/TEMPA': '999.0',
                                                    'MOD10/TEMPB': '-100.0'})))
    assert guard.limits.sensor == 'B'
    assert note == '' and not guard.tripped and ctrl.writes() == []


def test_a_missing_reading_does_not_turn_the_heater_off():
    """⚠️ **결측은 과열이 아니다.**

    히터·게이지 명령이 MOD10 VCPU 를 재시작해 STATUS 에 구멍을 낸다(11.18).
    결측으로 끄면 `HTRFORCE` 한 번이 자기 차단을 부른다.
    """
    ctrl = RecordingCtrl()
    guard = heater.OverTempGuard()
    note = asyncio.run(guard.check(ctrl, _status()))     # TEMPA 자체가 없다
    assert note == '' and not guard.tripped and ctrl.writes() == []


def test_the_same_excursion_is_not_written_twice():
    """⭐ 래치가 없으면 **매 바퀴 VCPU 를 재시작한다** (DEWPRES 가 영영 결측)."""
    ctrl = RecordingCtrl()
    guard = heater.OverTempGuard()
    st = _status(**{'MOD10/TEMPA': '60.0'})
    asyncio.run(guard.check(ctrl, st))
    n = len(ctrl.writes())
    assert asyncio.run(guard.check(ctrl, st)) == ''
    assert len(ctrl.writes()) == n, '같은 초과로 또 썼다'


def test_the_guard_rearms_after_the_temperature_returns():
    """⭐ 래치는 **중복 쓰기를 막는 것**이다 -- 돌아오면 풀린다.

    ⚠️ 다만 히터는 **꺼진 채로 남는다** -- 되켜는 것은 사람 몫이고, 그래서
    다시 넘으면 그때는 다시 끈다.
    """
    ctrl = RecordingCtrl()
    guard = heater.OverTempGuard()
    asyncio.run(guard.check(ctrl, _status(**{'MOD10/TEMPA': '60.0'})))
    asyncio.run(guard.check(ctrl, _status(**{'MOD10/TEMPA': '20.0'})))
    assert not guard.tripped
    n = len(ctrl.applies())
    asyncio.run(guard.check(ctrl, _status(**{'MOD10/TEMPA': '60.0'})))
    assert len(ctrl.applies()) == n + 1


def test_no_limit_means_no_trip_and_the_loop_still_lives():
    """⛔ 한계를 못 읽으면 **차단이 없다** -- 그 사실은 로그로 남기고 루프는 산다.

    `_StatusCtrl` 은 `read_config` 가 없다 -- 컨트롤러가 아직 안 붙은 모양이다.
    ⚠️ 여기서 예외가 새면 HK 루프가 통째로 죽는다.
    """
    guard = heater.OverTempGuard()
    note = asyncio.run(guard.check(_StatusCtrl(),
                                   _status(**{'MOD10/TEMPA': '99.0'})))
    assert note == '' and not guard.tripped


class _OverTempCtrl(RecordingCtrl):
    """실물 ACF + 과열 STATUS -- HK 루프를 통째로 지나게 한다."""

    def __init__(self, temp: str = '60.0') -> None:
        super().__init__()
        self._temp = temp

    async def refresh_status_live(self) -> bool:
        self.status_live = {'VALID': '1', 'MOD10/TEMPA': self._temp,
                            'MOD10/VCPU_OUTREG15': '1'}
        return True


def test_the_hk_loop_turns_the_heater_off_and_records_the_event(tmp_path):  # noqa: ANN001
    """⛔⛔ **STATUS 원값으로 판정한다.**

    ⚠️ 2026-09-06 까지는 `decode_rtd()` 가 ACF 한계 밖을 버려서 과열이
    `_sample` 에서 **결측으로만** 보였다 -- 그 폐기는 같은 날 운영자 지시로
    걷었다.  이제 값도 실리고 차단도 돈다: **둘 다** 확인한다.
    """
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    ctrl = _OverTempCtrl('60.0')
    mon = HkMonitor(ctrl, icfg)
    asyncio.run(mon._tick(0.0))
    assert any('MOD10/HEATERAENABLE=0' in c for c in ctrl.writes()), ctrl.writes()
    # ⭐ 과열 온도가 **그대로 실린다** -- 결측으로 위장되지 않는다.
    assert mon.sensors()['dmptemp'] == 60.0
    rows = list(tmp_path.glob('hk.G.*.csv'))
    assert rows, 'HK CSV 가 안 써졌다'
    assert 'HEATER OFF' in rows[0].read_text(encoding='utf-8')


# ---------------------------------------------------------------------------
# [icg] gauge_on_start -- 기동 때 켤지 끌지 (운영자 2026-09-10)
# ---------------------------------------------------------------------------


def test_the_acf_no_longer_turns_the_gauge_on():
    r"""⛔ **R2619 가 `MOD10\DIO_POWER` 을 `0` 으로 내렸다.**

    종전에는 ACF 가 `1` 이라 **ACF 적용마다 게이지가 켜졌고**, science 노출
    중에 ICG 를 재실행하면 필라멘트가 켜져 영상을 오염시켰다 (운영자가 벤치에서
    잡았다).  ⭐ 이제 파일이 꺼진 상태로 나오고, 켜는 것은 정책(`gauge_on_start`)
    이거나 ICS 의 `VACGAUGE ON` 이다.
    """
    import io as _io
    text = _io.open(GUIDE_ACF, encoding='latin-1').read()
    assert 'MOD10' + chr(92) + 'DIO_POWER=0' in text
    assert 'MOD10' + chr(92) + 'DIO_POWER=1' not in text


def test_gauge_on_start_defaults_to_off_and_only_takes_on_or_off():
    """⛔ **기본은 `off`** -- science 노출 중 재실행이 게이지를 켜면 안 된다.

    ⚠️ `keep` 은 없다: 기동이 늘 ACF 를 적용해 그 순간 값이 파일 값으로
    덮이므로 *"앞선 상태를 보존한다"* 가 성립하지 않는다.  뜻이 안 서는 값을
    받아 두면 문서가 거짓말한다.
    """
    from icg_archon.config import IcgCfg, IcgConfigError, load
    assert IcgCfg().gauge_on_start == 'off'
    import tempfile
    import os as _os
    for word, ok in (('on', True), ('off', True), ('keep', False),
                     ('yes', False)):
        fd, path = tempfile.mkstemp(suffix='.ini')
        with _os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write('[icg]\ngauge_on_start = %s\n' % word)
        try:
            if ok:
                assert load(path).gauge_on_start == word
            else:
                with pytest.raises(IcgConfigError):
                    load(path)
        finally:
            _os.unlink(path)


def test_startup_only_writes_when_the_readback_disagrees():
    """⭐ 이미 맞는 값이면 **왕복도 VCPU 구멍도 만들지 않는다.**

    `set()` 은 `APPLYDIO09` 라 모듈 VCPU 를 재시작하고 `DEWPRES` 에 구멍을
    낸다.  ACF 를 갓 적용한 정상 경로(파일이 `0`, 정책이 `off`)가 바로 이
    자리이므로 여기서 쓰면 매 기동마다 헛구멍이 난다.
    ⛔ **모르면 쓴다** -- 되읽기가 실패해 `None` 이면 추측하지 않고 맞춘다.
    """
    import io as _io
    import os as _os
    src = _io.open(_os.path.join(ROOT, 'icg_archon', 'app.py'),
                   encoding='utf-8').read()
    body = src[src.index('    async def _settle_gauge'):]
    body = body[:body.index('\n    async def stop')]
    assert 'if self.gauge.on is want:' in body, '되읽은 값과 견준다'
    assert 'return' in body


@pytest.mark.parametrize('reply_error, word, phrase', [
    (True, 'OFF', '직전 상태(OFF)로 되돌렸다'),
    (False, 'UNKNOWN', 'UNKNOWN'),
], ids=['refused', 'answer-lost'])
def test_a_startup_gauge_failure_says_which_state_it_left(
        reply_error, word, phrase, caplog):  # noqa: ANN001
    """⭐ 기동의 게이지 맞추기가 실패하면 **남은 상태를 그대로 말한다**.

    `set()` 이 적용 안 됨이 확실하면 되돌리고, `APPLYDIO09` 응답을 잃으면
    모름으로 둔다 -- 경고의 `detail` 이 둘을 갈라야 운영자가 무엇을 확인할지
    안다 (종전에는 늘 *"상태를 모른다"* 였다).
    """
    import logging
    import types

    from icg_archon.app import IcgArchon

    ctrl = RecordingCtrl()
    state = gauge_mod.GaugeState()
    asyncio.run(state.load(ctrl))
    assert state.word == 'OFF'
    ctrl.fail_on, ctrl.fail_reply_error = 'APPLYDIO', reply_error
    icfg = IcgCfg()
    icfg.gauge_on_start = 'on'                       # 켜려다 실패하게
    fake = types.SimpleNamespace(icfg=icfg, gauge=state,
                                 guide=types.SimpleNamespace(ctrl=ctrl))
    with caplog.at_level(logging.WARNING, logger='icg_archon.app'):
        asyncio.run(IcgArchon._settle_gauge(fake))
    assert state.word == word
    warns = [r for r in caplog.records
             if 'could not set the ion gauge' in r.getMessage()]
    assert len(warns) == 1, [r.getMessage() for r in caplog.records]
    assert phrase in warns[0].detail, warns[0].detail


def test_turning_it_on_starts_a_warmup_window():
    """⭐ **켠 직후에는 `WARMUP`** -- 측정이 아직 안 미덥다 (운영자 2026-09-10).

    ⛔ **켤 때마다** 그렇다 (기동이든 `VACGAUGE ON` 이든).
    ⚠️ 그동안 `DEWPRES` 를 **막는다** -- 안 미더운 값을 싣는 것이 sentinel 보다
    나쁘다 (규격 5.0절의 정신).
    """
    state = gauge_mod.GaugeState(warmup=10.0)
    asyncio.run(state.set(RecordingCtrl(), True))
    assert state.word == 'WARMUP'
    assert state.blocks_dewpres is True, '예열 중에는 DEWPRES 를 막는다'
    # 예열이 지나면 ON 이고 막지 않는다.
    state.warmup = 0.0
    assert state.word == 'ON'
    assert state.blocks_dewpres is False


def test_turning_it_off_clears_the_warmup():
    """⛔ 꺼진 것에 예열은 뜻이 없다."""
    state = gauge_mod.GaugeState(warmup=10.0)
    ctrl = RecordingCtrl()
    asyncio.run(state.set(ctrl, True))
    asyncio.run(state.set(ctrl, False))
    assert state.on_at is None
    assert state.word == 'OFF'
    assert state.warming is False


def test_a_gauge_found_already_on_is_not_called_warming():
    """⭐ **되읽은 `ON` 은 예열이 끝난 것으로 본다**.

    우리가 켠 것이 아니라 이미 켜져 있던 것이므로 언제 켜졌는지 알 수 없고,
    앞 세션이 켜 둔 것이라면 진작 예열이 끝났다.  ⛔ 모르는 것을 예열 중이라
    적으면 그것대로 거짓이다.
    """
    ctrl = RecordingCtrl()
    # R2619 ACF 는 0 이므로, **이미 켜져 있던** 상태를 흉내내려고 갈아 준다.
    ctrl.config['MOD10/DIO_POWER'] = '1'
    state = gauge_mod.GaugeState(warmup=10.0)
    asyncio.run(state.load(ctrl))
    assert state.on is True
    assert state.on_at is None
    assert state.word == 'ON', '되읽은 켬은 예열 중이 아니다'


def test_an_unknown_gauge_is_still_unknown():
    """⚠️ 모름은 그대로 `UNKNOWN` 이고 `DEWPRES` 를 막지 않는다."""
    state = gauge_mod.GaugeState()
    assert state.word == 'UNKNOWN'
    assert state.blocks_dewpres is False


def test_the_warmup_overlaps_the_ccd_flush_wait():
    """⭐ **게이지를 `POWERON` 앞에서 켠다** -- 두 대기가 겹쳐 기동이 안 느려진다.

    운영자 지시(2026-09-10): *"전원을 먼저 켜고 15초 대기 해야되"*.  ⭐ 우리
    기동은 `after_config`(ACF 적용 직후 · `POWERON` 앞)에서 게이지를 켜므로,
    예열 12초가 뒤따르는 CCD flush 대기와 **겹쳐서** 돈다.
    ⛔ `POWERON` **뒤**로 옮기면 둘이 직렬이 되어 기동이 그만큼 길어진다.
    """
    import io as _io
    import os as _os
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    app = _io.open(_os.path.join(root, 'icg_archon', 'app.py'),
                   encoding='utf-8').read()
    ctrl = _io.open(_os.path.join(root, 'ics_archon', 'archon',
                                  'controller.py'), encoding='utf-8').read()
    # 앱은 게이지 맞추기를 `_after_config` 에서 한다.
    body = app[app.index('    async def _after_config'):]
    body = body[:body.index('\n    async def _connect_controller')]
    assert 'await self._settle_gauge()' in body
    # 컨트롤러는 그 곁다리를 `power_on()` **앞**에서 부른다.
    prep = ctrl[ctrl.index('    async def prepare(self'):]
    prep = prep[:prep.index('\n    def _log_module_map')]
    assert (prep.index('await after_config()')
            < prep.index('await self.power_on(wait=self.power_wait)'))


def test_no_gauge_means_no_poweron_wait():
    """⭐ **예열할 게이지가 없으면 기다리지 않는다** (운영자 2026-09-10).

    전원 투입 자체는 실측 **약 1초**(`POWER=4 (On) 확인 -- 1.0초 걸렸다`)이고,
    남는 시간은 순전히 이온게이지 예열 몫이다.
    ⚠️ 판단을 **`gauge_on_start` 가 아니라 실제 상태**로 한다 -- 되읽기가
    실패해 모르면 켜질 수도 있으니 기다리는 쪽이 안전하다.
    """
    import io as _io
    import os as _os
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    app = _io.open(_os.path.join(root, 'icg_archon', 'app.py'),
                   encoding='utf-8').read()
    body = app[app.index('    async def _settle_gauge'):]
    body = body[:body.index(chr(10) + '    async def stop')]
    assert 'ctrl.power_wait = 0.0' in body
    assert 'self.gauge.on is False' in body, '모름일 때는 기다린다'

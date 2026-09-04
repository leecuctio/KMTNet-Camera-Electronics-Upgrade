#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide 듀어 히터 -- `MOD10`(HeaterX 모듈) 의 히터 채널을 조작한다.

명령 **다섯**의 살림집이다 -- 켜기/끄기(`HTREN`) · 목표온도(`HTRSET`) ·
강제 출력(`HTRFORCE`) · 램프(`HTRRAMP`) · PID 게인(`HTRPID`).  ⭐ 이름은
**`HTR` 접두로 통일**했다 (운영자 2026-09-04: *"HEATERSET 으로 했었는데
줄여서 HTRSET 같이 바꾸려고 해"*) -- 채널 구분자 `A` 도 없다(채널 B 는 안
쓴다, 11.14-(4)).  `commands.py` 는 인자 해석과 응답 문구만 맡고, ACF 키
조립·한계 조회·클램프·범위 검사·적용 순서는 여기 모아 둔다 (`expenable.py`
와 같은 구조).

⭐ **파라미터 여섯이 명령 다섯에 나뉜 경위**: 원 지시는 *"3개의 명령어를
만들고 arg 를 2개씩"* 이었는데, 그 뒤 **`HTRSET` 은 온도 하나만** 받기로
바뀌었다 (*"`HTREN` 이 별도로 있으니 온도만 넣으면 되고"*).  그래서
(ENABLE, TARGET) 이 둘로 갈라져 다섯이 됐고, `HTRPID` 가 뒤에 더해졌다.

⭐ **한계를 코드에 박지 않는다.**  목표온도의 상·하한은 컨트롤러를 **두 걸음**
읽어 얻는다:

    1. `MOD10\\HEATERASENSOR` -- *어느 RTD 로 PID 루프가 닫히는지* (0=A·1=B·2=C)
    2. 그 센서의 `MOD10\\SENSOR?LOWERLIMIT` / `SENSOR?UPPERLIMIT`

현행 guide ACF(R2610)는 `HEATERASENSOR=0` → `SENSORA`(`RTD9_DMP`) → **-150…50**
이다.  ⭐ 채널을 열거나 ACF 가 바뀌어도 코드가 따라온다 -- **상수 0개**
(DevNote 11.14-(3)).

⛔⛔ **적용이 그 모듈의 VCPU 를 재시작한다.**  `APPLYALL` 만이 아니라 **모듈
하나만 적용하는 `APPLYMOD09` 도** 그렇다 (매뉴얼 p.86).  guide 는 **진공
게이지를 같은 MOD10 의 VCPU 가 읽으므로 히터 명령 한 번이 `DEWPRES` 결측 창을
만든다** -- 그래서 이 모듈의 함수들은 응답에 붙일 **주석 문구를 함께 돌려준다**
(DevNote 11.18).  ⭐ 운영자 확정(2026-09-04): **결측은 받아들인다** -- 취득
중이어도 명령을 거부하지 않고 경고와 응답 표시로만 알린다.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

log = logging.getLogger('icg_archon.heater')

#: HeaterX 모듈의 **1기점 슬롯**.  `ArchonController.apply_module()` 이
#: 0기점 16진(`09`)으로 바꿔 보낸다 -- 여기서는 사람이 읽는 값으로 둔다.
SLOT = 10

#: 지금 쓰는 히터 채널.  ⭐ **한 곳에만 둔다** -- 채널 B 를 열 일이 생기면
#: 명령 인자 하나와 이 상수 하나가 전부다.  (B 는 DMP 에 센서가 하나뿐이라
#: CCD 온도를 보도록 되어 있고 배선도 어렵다 -- DevNote 11.14-(4).)
CH = 'A'

#: `HEATER?SENSOR` 의 값 → 센서 키의 글자.
SENSOR_LETTERS = 'ABC'


def heater_key(key: str, ch: str = CH) -> str:
    """`'ENABLE'` → `'MOD10\\HEATERAENABLE'`."""
    return 'MOD%d\\HEATER%s%s' % (SLOT, ch, key)


def sensor_key(key: str, idx: int) -> str:
    """`('LOWERLIMIT', 0)` → `'MOD10\\SENSORALOWERLIMIT'`."""
    return 'MOD%d\\SENSOR%s%s' % (SLOT, SENSOR_LETTERS[idx], key)


class Limits(NamedTuple):
    """목표온도의 인정 구간과 **그것이 어느 센서에서 왔는지**."""

    lo: float
    hi: float
    sensor: str            #: `'A'`/`'B'`/`'C'`
    label: str             #: 그 센서의 ACF 라벨 (`'RTD9_DMP'`)

    @property
    def source(self) -> str:
        """응답·로그에 붙일 출처 문구 -- **어디서 온 한계인지 남긴다**."""
        return 'SENSOR%s%s' % (self.sensor,
                              ' (%s)' % self.label if self.label else '')


async def read_limits(ctrl, ch: str = CH) -> Limits:  # noqa: ANN001
    """PID 루프가 닫히는 센서를 찾아 그 센서의 한계를 되읽는다 (두 걸음).

    ⚠️ `read_config()` 는 실패를 숨기지 않는다 -- 줄 번호를 모르거나 응답이
    다른 키면 `ArchonError` 다.  부르는 쪽이 잡아서 **명령을 거부**한다
    (한계를 모르는 채로 목표온도를 쓰면 클램프가 무의미해진다).
    """
    raw = await ctrl.read_config(heater_key('SENSOR', ch))
    idx = int(float(raw))
    if not 0 <= idx < len(SENSOR_LETTERS):
        raise ValueError('%s = %r 은 센서 번호가 아니다 (0..2)'
                         % (heater_key('SENSOR', ch), raw))
    lo = float(await ctrl.read_config(sensor_key('LOWERLIMIT', idx)))
    hi = float(await ctrl.read_config(sensor_key('UPPERLIMIT', idx)))
    try:
        label = (await ctrl.read_config(sensor_key('LABEL', idx))).strip()
    except Exception:                       # noqa: BLE001
        label = ''                          # 라벨은 있으면 좋은 것뿐이다
    if lo > hi:                             # ACF 가 뒤집혀 들어온 경우
        lo, hi = hi, lo
    return Limits(lo, hi, SENSOR_LETTERS[idx], label)


def clamp(celsius: float, lim: Limits) -> tuple[float, str]:
    """한계 밖이면 **거부하지 않고 한계로 접는다** + 사유 문구를 돌려준다.

    ⭐ 운영자 확정(2026-09-03) -- 내가 권한 *"상한은 거부"* 를 쓰지 않는다.
    **양쪽 클램프 + 경고**가 운영자 선택이다.  다만 접었다는 사실은 응답에
    반드시 남긴다 -- 안 그러면 *"넣은 값과 다른 값이 앉았는데 DONE"* 이 된다.
    """
    if celsius < lim.lo:
        return lim.lo, ('Clamped=%.2f->%.2f (lower limit of %s)'
                        % (celsius, lim.lo, lim.source))
    if celsius > lim.hi:
        return lim.hi, ('Clamped=%.2f->%.2f (upper limit of %s)'
                        % (celsius, lim.hi, lim.source))
    return celsius, ''


#: 적용이 진공 읽기를 끊는다는 사실을 응답에 붙이는 문구.  ⭐ `VACGAUGE` 와
#: 같은 규약이다 (DevNote 11.15-(1)·11.18-(3)).
VCPU_NOTE = 'VCPU restarted -- DEWPRES has a gap'


async def _write_and_apply(ctrl, *pairs) -> None:  # noqa: ANN001
    """`WCONFIG` 로 **여러 줄을 쓰고 적용은 한 번**만 한다.

    ⭐ `APPLYALL` 이 아니라 `APPLYMOD09` 다 -- 벤더 GUI 의 HeaterX 탭 Apply
    버튼이 하는 일이고(운영자 지적), 전체 적용은 CCD 클록·바이어스까지
    다시 앉히므로 취득 중에 부를 것이 아니다 (매뉴얼 p.52 대 p.51).

    ⚠️ **한 명령이 파라미터 둘·셋을 만져도 적용은 한 번이다.**  적용마다
    그 모듈의 VCPU 가 재시작되므로(`DEWPRES` 결측 창) 키마다 적용하면
    `HTRPID` 한 번이 결측 창을 **셋** 만든다.  ⭐ 그리고 반쯤 적용된 상태로
    한 주기가 도는 것도 막는다 -- `FORCE=1` 은 앉았는데 `FORCELEVEL` 은
    아직 옛 값인 창이 없어야 한다.
    """
    for key, value in pairs:
        await ctrl.set_config(key, value)
    await ctrl.apply_module(SLOT)


async def set_enable(ctrl, on: bool, ch: str = CH) -> str:  # noqa: ANN001
    """히터 Enable 을 쓴다 (`HEATER?ENABLE`).  응답 주석 문구를 돌려준다."""
    await _write_and_apply(ctrl, (heater_key('ENABLE', ch), '1' if on else '0'))
    log.info('히터 %s Enable=%d -- ⚠️ %s', ch, on, VCPU_NOTE)
    return VCPU_NOTE


async def set_target(ctrl, celsius: float,
                     ch: str = CH) -> tuple[float, str]:  # noqa: ANN001
    """목표온도를 쓴다 (`HEATER?TARGET`).  **앉은 값**과 주석 문구를 돌려준다.

    한계 조회 → 클램프 → `WCONFIG` → `APPLYMOD09` 순이다.  ⚠️ 한계를 못 읽으면
    쓰지 않고 올린다 -- 클램프 없는 쓰기는 하지 않는다.
    """
    lim = await read_limits(ctrl, ch)
    value, note = clamp(celsius, lim)
    if note:
        log.warning('HTRSET %.2f 는 %s 의 한계 [%.2f, %.2f] 밖이다 -- %.2f 로 '
                    '접어 넣는다', celsius, lim.source, lim.lo, lim.hi, value)
    await _write_and_apply(ctrl, (heater_key('TARGET', ch), '%g' % value))
    log.info('히터 %s Target=%.2f -- ⚠️ %s', ch, value, VCPU_NOTE)
    return value, ' '.join(x for x in (note, '(%s)' % VCPU_NOTE) if x)


async def read_settings(ctrl, ch: str = CH) -> dict:  # noqa: ANN001
    """`HTREN`·`HTRSET` 을 **컨트롤러에서 되읽는다** (`HKDATA` 응답용).

    ⚠️ 캐시(`ctrl.config`)가 아니라 `RCONFIG` 다 -- `set_config()` 가 왕복
    실패에도 캐시를 먼저 갈아 끼우므로 캐시는 *"보냈다"* 는 뜻밖에 없다
    (DevNote 11.14-(1) 의 세 층).  `HTROUT` 은 여기 없다 -- 그것은 `STATUS`
    의 `HEATER?OUTPUT` 실측이고 HK 경로가 읽는다.
    """
    out: dict[str, object] = {}
    for name, key in (('htren', 'ENABLE'), ('htrset', 'TARGET')):
        try:
            out[name] = (await ctrl.read_config(heater_key(key, ch))).strip()
        except Exception as exc:            # noqa: BLE001
            log.warning('히터 %s 되읽기 실패 -- %s', key, exc)
            out[name] = None
    return out


# -- 강제 출력 · 램프 · PID (운영자 확정 2026-09-04) -----------------------

#: `FORCELEVEL` 의 **모듈 범위** [V] (매뉴얼 p.60-61).  ⚠️ 이것은 안전선이
#: 아니라 *"모듈이 낼 수 있는 값"* 이다 -- 채널당 25 V ≈ 25 W (히터 전원
#: +28 V).  ⭐ **별도 운영 상한은 두지 않는다** (운영자 확정 2026-09-04:
#: *"FORCELEVEL 로 출력전압을 조절하니 상한은 두지 않아도 된다, 운영하는
#: 쪽에서 알아서 한다"*).  그래서 이 범위 밖만 거부하고, 대신 `FORCE=1` 인
#: 동안은 응답·로그에 상시 표시한다 (DevNote 11.13 F3 의 *"force 는 다른
#: 등급으로 다룬다"* 를 표시로 지킨다).
FORCELEVEL_MAX = 25.0

#: `P`/`I`/`D` 게인의 범위 (매뉴얼 p.60-61 -- HeaterX 는 소수를 받는다.
#: 백플레인 1.0.1054 이상이어야 하고 guide 는 1.0.1252 다).
PID_MAX = 10000.0

#: `RAMPRATE` 의 범위 [mK / **update time**] (매뉴얼 p.60-61).
RAMPRATE_MIN, RAMPRATE_MAX = 1, 32767

#: 모듈 단위 갱신 주기 키 -- **채널 글자가 없다**.  ⭐ ACF 소관이라 명령으로
#: 만지지 않고(운영자 확정), `RAMPRATE` 의 뜻을 환산해 보이는 데만 쓴다.
UPDATETIME_KEY = 'MOD%d\\HEATERUPDATETIME' % SLOT

#: `FORCE=1` 인 동안 응답·로그에 붙는 문구.  ⛔ **`HEATERALIMIT` 이 이 모드에는
#: 안 걸린다** -- 그 상한은 매뉴얼이 *"in PID mode"* 로 못박은 것이라, force
#: 중에는 온도와 무관하게 `FORCELEVEL` 이 그대로 나간다 (DevNote 11.13 F3).
FORCE_NOTE = ('FORCE mode -- HEATERALIMIT does not apply, output follows '
              'FORCELEVEL regardless of temperature')


def _in_range(name: str, value: float, lo: float, hi: float) -> None:
    """범위 밖이면 **거부**한다 (히터는 클램프하지 않는 자리다).

    ⚠️ `TARGET` 과 규약이 다른 것이 의도다 -- `TARGET` 은 *"어느 온도를
    노리나"* 라 접어도 뜻이 남지만, 여기 셋은 **모듈이 받는 값의 범위**여서
    밖의 값은 접을 것이 아니라 오타다.  접어 넣으면 *"25 라고 쳤는데 조용히
    2.5 가 앉는"* 반대 방향 사고가 난다.
    """
    if not lo <= value <= hi:
        raise ValueError('%s=%g 는 범위 밖이다 (%g..%g)' % (name, value, lo, hi))


async def set_force(ctrl, on: bool, level: float,  # noqa: ANN001
                    ch: str = CH) -> str:
    """강제 출력 (`HEATER?FORCE` · `HEATER?FORCELEVEL`).  주석 문구를 돌려준다.

    ⛔ **PID 를 우회한다** -- 켜면 센서 온도와 무관하게 `level` 이 그대로
    나가고 `HEATERALIMIT` 은 안 걸린다.  ⚠️ 그래서 **끌 때도 레벨을 함께
    쓴다**: `FORCE=0` 만 보내고 레벨을 옛 값으로 두면 다음에 누가 `FORCE=1`
    만 보냈을 때 **잊고 있던 전압이 되살아난다.**
    """
    _in_range('FORCELEVEL', level, 0.0, FORCELEVEL_MAX)
    await _write_and_apply(ctrl,
                           (heater_key('FORCE', ch), '1' if on else '0'),
                           (heater_key('FORCELEVEL', ch), '%g' % level))
    if on:
        log.warning('히터 %s **강제 출력** Force=1 Level=%.3f V -- %s.  ⚠️ %s',
                    ch, level, FORCE_NOTE, VCPU_NOTE)
        return '%s (%s)' % (FORCE_NOTE, VCPU_NOTE)
    log.info('히터 %s Force=0 Level=%.3f V -- ⚠️ %s', ch, level, VCPU_NOTE)
    return VCPU_NOTE


async def ramp_rate_note(ctrl, rate: int) -> str:  # noqa: ANN001
    """`RAMPRATE` 값의 **뜻을 환산해** 돌려준다 (`1 mK/s = 3.6 K/h`).

    ⭐ `RAMPRATE` 는 초당이 아니라 **update time 당**이라, `HEATERUPDATETIME`
    이 바뀌면 **같은 값의 뜻이 바뀐다** (DevNote 11.14-(3)).  그래서 1000 을
    코드에 박지 않고 **ACF 에서 읽어** 환산한다.  ⚠️ 못 읽으면 환산 없이
    빈 문구를 돌려준다 -- 틀린 환산을 보이느니 안 보이는 편이 낫다.
    """
    try:
        ms = float(await ctrl.read_config(UPDATETIME_KEY))
    except Exception as exc:                # noqa: BLE001
        log.warning('%s 를 못 읽어 RAMPRATE 환산을 생략한다 -- %s',
                    UPDATETIME_KEY, exc)
        return ''
    if ms <= 0:
        return ''
    mk_per_s = rate * 1000.0 / ms
    return '%.3g mK/s = %.3g K/h at UPDATETIME=%gms' % (
        mk_per_s, mk_per_s * 3.6, ms)


async def set_ramp(ctrl, on: bool, rate: int,  # noqa: ANN001
                   ch: str = CH) -> str:
    """목표온도 램프 (`HEATER?RAMP` · `HEATER?RAMPRATE`).  주석 문구를 돌려준다.

    켜면 `TARGET` 으로 **단번에 뛰지 않고** `rate` 씩 올라간다.  ⭐ 환산값을
    응답에 함께 실어 *"1 이 얼마나 느린가"* 를 운영자가 그 자리에서 알게
    한다 (`1` = 1 mK/s = 3.6 K/h -- 100 K 를 옮기는 데 하루가 넘는다).
    """
    _in_range('RAMPRATE', rate, RAMPRATE_MIN, RAMPRATE_MAX)
    conv = await ramp_rate_note(ctrl, rate)     # ⭐ 쓰기 **전에** 읽는다
    await _write_and_apply(ctrl,
                           (heater_key('RAMP', ch), '1' if on else '0'),
                           (heater_key('RAMPRATE', ch), '%d' % rate))
    log.info('히터 %s Ramp=%d RampRate=%d%s -- ⚠️ %s', ch, on, rate,
             ' (%s)' % conv if conv else '', VCPU_NOTE)
    return ' '.join(x for x in (conv, '(%s)' % VCPU_NOTE) if x)


async def set_pid(ctrl, p: float, i: float, d: float,  # noqa: ANN001
                  ch: str = CH) -> str:
    """PID 게인 셋 (`HEATER?P`/`?I`/`?D`).  주석 문구를 돌려준다.

    ⭐ **이 명령이 있어야 히터가 실제로 데워진다** -- 현행 guide ACF 는
    `HEATERAP=HEATERAI=HEATERAD=0` 이라, 출력 = P·오차 + I·오차합 + D·오차차분
    이 **게인 0 이라 목표를 아무리 줘도 0 V** 다 (DevNote 11.13 F1).

    ⚠️ **`IL`(적분항 상한)과 `UPDATETIME` 은 만지지 않는다** -- ACF 소관이다
    (운영자 확정).  실물이 `IL=1000` 이라 살아 있고, 0이면 `I` 를 줘도 적분항이
    묶여 안 듣는다.

    ⛔ **이름이 STATUS 와 겹친다** -- ACF 의 `HEATERAP`/`AI`/`AD` 는 **게인**
    인데 STATUS 의 같은 이름은 **각 항의 기여분**이다.  글자까지 같으니
    `ctrl.config` 와 `ctrl.status` 를 한 dict 로 합치지 말 것 (11.14-(1)).
    """
    for name, value in (('P', p), ('I', i), ('D', d)):
        _in_range(name, value, 0.0, PID_MAX)
    await _write_and_apply(ctrl,
                           (heater_key('P', ch), '%g' % p),
                           (heater_key('I', ch), '%g' % i),
                           (heater_key('D', ch), '%g' % d))
    log.info('히터 %s PID=%g/%g/%g -- ⚠️ %s', ch, p, i, d, VCPU_NOTE)
    return VCPU_NOTE


#: 명령어 → 조회가 되읽을 (이름표, ACF 키 꼬리) 짝.  ⭐ **응답의 이름표를 한
#: 곳에 모은다** -- 설정 응답과 조회 응답이 같은 낱말을 쓰게 하기 위해서다.
GROUPS = {
    'HTREN':    (('Enable', 'ENABLE'),),
    'HTRSET':   (('Target', 'TARGET'),),
    'HTRFORCE': (('Force', 'FORCE'), ('Level', 'FORCELEVEL')),
    'HTRRAMP':  (('Ramp', 'RAMP'), ('RampRate', 'RAMPRATE')),
    'HTRPID':   (('P', 'P'), ('I', 'I'), ('D', 'D')),
}


async def read_group(ctrl, cmdword: str, ch: str = CH) -> str:  # noqa: ANN001
    """조회 응답 본문을 만든다 -- **컨트롤러에서 되읽어** (`RCONFIG`).

    ⚠️ 캐시가 아니다 -- `set_config()` 가 왕복 실패에도 캐시를 먼저 갈아
    끼우므로 캐시는 *"보냈다"* 는 뜻밖에 없다 (DevNote 11.14-(1) 의 세 층).
    ⚠️ 하나라도 못 읽으면 `ArchonError` 로 올린다 -- 일부만 답하면 나머지가
    **옛 값인지 못 읽은 것인지** 구별되지 않는다.
    """
    parts = []
    for label, key in GROUPS[cmdword]:
        got = (await ctrl.read_config(heater_key(key, ch))).strip()
        parts.append('%s=%s' % (label, got))
    return ' '.join(parts)

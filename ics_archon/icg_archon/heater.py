#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide 듀어 히터 -- `MOD10`(HeaterX 모듈) 의 히터 채널을 조작한다.

명령 **넷**의 살림집이다 -- `HTRSET`(Enable+목표온도) · `HTRFORCE`(강제 출력) ·
`HTRRAMP`(램프) · `HTRPID`(PID 게인).  ⭐ 이름은
**`HTR` 접두로 통일**했다 (운영자 2026-09-04: *"HEATERSET 으로 했었는데
줄여서 HTRSET 같이 바꾸려고 해"*) -- 채널 구분자 `A` 도 없다(채널 B 는 안
쓴다, 11.14-(4)).  `commands.py` 는 인자 해석과 응답 문구만 맡고, ACF 키
조립·한계 조회·클램프·범위 검사·적용 순서는 여기 모아 둔다 (`expenable.py`
와 같은 구조).

⭐ **`HTREN` 은 없다 -- `HTRSET` 하나로 되돌렸다** (운영자 정정 2026-09-04:
*"커멘드는 분리하지 않고 원안대로 HTRSET 하나로"*).  경위: 원 지시가
*"3개의 명령어를 만들고 arg 를 2개씩"* 이었고, 중간에 *"`HTREN` 이 별도로 있으니
온도만"* 으로 갈렸다가 **원안으로 확정**됐다.  ⚠️ 그래서 명령은 `(ENABLE,
TARGET)` 를 **한 번에** 받는다.

⭐ **헤더는 다르다** -- FITS 카드로는 `HTREN`·`HTRSET`·`HTROUT`·`HTRFORCE` **넷을
따로** 싣는다(운영자 확정).  `HTRPID`·`HTRRAMP`·`FORCELEVEL` 은 **안 싣는다**.
⛔ 카드 신설은 **규격 개정이라 `main` 소관**이다 -- 이 폴더는 값을 만들 뿐이다.

⭐ **한계를 코드에 박지 않는다.**  목표온도의 상·하한은 컨트롤러를 **두 걸음**
읽어 얻는다:

    1. `MOD10\\HEATERASENSOR` -- *어느 RTD 로 PID 루프가 닫히는지* (0=A·1=B·2=C)
    2. 그 센서의 `MOD10\\SENSOR?LOWERLIMIT` / `SENSOR?UPPERLIMIT`

현행 guide ACF(R2610)는 `HEATERASENSOR=0` → `SENSORA`(`RTD9_DMP`) → **-150…50**
이다.  ⭐ 채널을 열거나 ACF 가 바뀌어도 코드가 따라온다 -- **상수 0개**
(DevNote 11.14-(3)).

⭐ **되먹임 센서 과열 차단이 여기 산다** (`OverTempGuard`, 운영자 지시
2026-09-06).  `HEATER?SENSOR` 로 루프가 닫히는 센서를 찾고 그 센서의
`SENSOR?UPPERLIMIT` 를 넘으면 히터를 끈다 -- **상수 0개**, ACF 가 바뀌면
따라온다.  ⚠️ 판정은 **HK 루프 주기**([hk] interval, 기본 60초)로만 돈다
-- 빠른 인터록이 아니라 **최후 방어선**이다.  DevNote 11.13 F3 이 경고한
*"추정으로 안전장치를 대신하지 말 것"* 의 반대쪽 함정(있으니 안심)에
빠지지 않도록 이 한계를 문서와 응답에 그대로 남긴다.

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


async def set_target(ctrl, on: bool, celsius: float,  # noqa: ANN001
                     ch: str = CH) -> tuple[float, str]:
    """`HTRSET` -- Enable 과 목표온도를 **한 번에** 쓴다.

    `(HEATER?ENABLE, HEATER?TARGET)` 둘을 쓰고 적용은 **한 번**이다 -- 적용마다
    MOD10 의 VCPU 가 재시작해 `DEWPRES` 결측 창이 생기므로(11.18), 그리고
    *"Enable 은 켜졌는데 목표는 옛 값"* 인 창을 만들지 않기 위해서다.

    한계 조회 → 클램프 → `WCONFIG` 둘 → `APPLYMOD09` 순이다.  ⚠️ 한계를 못
    읽으면 **쓰지 않고 올린다** -- 클램프 없는 쓰기는 하지 않는다.

    **앉은 목표값**과 주석 문구를 돌려준다.
    """
    lim = await read_limits(ctrl, ch)
    value, note = clamp(celsius, lim)
    if note:
        log.warning('HTRSET %.2f is outside the %s limits [%.2f, %.2f] -- '
                    'clamped to %.2f',
                    celsius, lim.source, lim.lo, lim.hi, value)
    await _write_and_apply(ctrl,
                           (heater_key('ENABLE', ch), '1' if on else '0'),
                           (heater_key('TARGET', ch), '%g' % value))
    log.info('heater %s Enable=%d Target=%.2f', ch, int(on), value,
             extra={'detail': '⚠️ %s' % VCPU_NOTE})
    return value, ' '.join(x for x in (note, '(%s)' % VCPU_NOTE) if x)


async def read_settings(ctrl, ch: str = CH) -> dict:  # noqa: ANN001
    """`HTREN`·`HTRSET` 을 **컨트롤러에서 되읽는다** (`HKDATA` 응답용).

    ⚠️ 캐시(`ctrl.config`)가 아니라 `RCONFIG` 다 -- `set_config()` 가 왕복
    실패에도 캐시를 먼저 갈아 끼우므로 캐시는 *"보냈다"* 는 뜻밖에 없다
    (DevNote 11.14-(1) 의 세 층).  `HTROUT` 은 여기 없다 -- 그것은 `STATUS`
    의 `MOD%d/HEATER%sOUTPUT` %% (SLOT, CH) 이고(FW 1.0.1252 type-11 경로가 출력 — 매뉴얼 p.48 'Heater only' 는 오기,
    DevNote 11.30) HK 경로(`hk.py`)가 읽는다.  ⏳ 그 값이 출력단 **측정값**
    인지 PID/FORCE **명령값**인지는 실기 미확인 -- 규격 OI-28.
    """
    out: dict[str, object] = {}
    for name, key in (('htren', 'ENABLE'), ('htrset', 'TARGET')):
        try:
            out[name] = (await ctrl.read_config(heater_key(key, ch))).strip()
        except Exception as exc:            # noqa: BLE001
            log.warning('heater readback failed for %s -- %s', key, exc)
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
    나가고 `HEATERALIMIT` 은 안 걸린다.

    ⭐ **`FORCE=0` 이면 출력이 꺼진다 (0 V)** -- 근거 등급 **운영자 확정
    (2026-09-06)**.  ⚠️ 매뉴얼(p.60-61)은 `FORCELEVEL` 의 범위만 적고 이 점을
    말하지 않는다.  실측이 아니므로 어긋나는 관찰이 나오면 이 주석부터 고칠 것.

    ⚠️ **그래도 끌 때 레벨을 함께 쓴다.**  종전 주석은 *"`FORCE=0` 만 보내면
    다음에 누가 `FORCE=1` 만 보냈을 때 옛 전압이 되살아난다"* 였는데, 그 경로는
    **이 명령으로는 도달할 수 없다** -- `commands.py` 가 인자를 정확히 둘로
    강제하고 이 함수가 두 키를 늘 한 쌍으로 쓰기 때문이다.  실제로 남는 창은
    **손 `WCONFIG` 로 `FORCE` 만 건드리는 경로**뿐이고, 레벨을 0 으로 두는
    비용이 0 이라 그 창을 닫는다.
    """
    _in_range('FORCELEVEL', level, 0.0, FORCELEVEL_MAX)
    await _write_and_apply(ctrl,
                           (heater_key('FORCE', ch), '1' if on else '0'),
                           (heater_key('FORCELEVEL', ch), '%g' % level))
    if on:
        log.warning('heater %s FORCED output Force=1 Level=%.3f V',
                    ch, level,
                    extra={'detail': '%s.  ⚠️ %s' % (FORCE_NOTE, VCPU_NOTE)})
        return '%s (%s)' % (FORCE_NOTE, VCPU_NOTE)
    log.info('heater %s Force=0 Level=%.3f V', ch, level,
             extra={'detail': '⚠️ %s' % VCPU_NOTE})
    return VCPU_NOTE


def temp_field(sensor: str) -> str:
    """`'A'` → `'MOD10/TEMPA'` -- 그 센서의 온도가 실리는 STATUS 필드.

    ⚠️ **구분자가 `/` 다.**  ACF 원문은 역슬래시인데 `parse_acf()` 가 읽으면서
    정규화한다 -- 역슬래시로 조회하면 한 채널도 안 맞는다 (`hk._limit_keys`
    가 같은 함정을 주석으로 남겨 뒀다).
    """
    return 'MOD%d/TEMP%s' % (SLOT, sensor)


def _as_float(raw):  # noqa: ANN001, ANN201
    """STATUS 값 → float, 못 읽으면 `None`."""
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


async def shutdown(ctrl, ch: str = CH) -> None:  # noqa: ANN001
    """히터를 **끈다** -- 강제도 PID 도.

    `FORCE`·`FORCELEVEL`·`ENABLE` 셋을 한 `_write_and_apply` 로 쓴다:

    * `FORCE=0` + `FORCELEVEL=0` -- 강제 경로를 끊고 **레벨까지 0 으로**.
      레벨을 남기면 다음에 누가 `ArchonGUI` 나 손 `WCONFIG` 로 `FORCE` 만
      켰을 때 잊고 있던 전압이 되살아난다 (`set_force` 와 같은 규약).
    * `ENABLE=0` -- PID 경로도 끊는다.  과열의 원인이 강제가 아니라 PID 일 수
      있으므로 **한쪽만 끄면 안 끈 것**이다.

    ⭐ 적용은 한 번이라 `DEWPRES` 결측 창도 하나다 (11.18).
    """
    await _write_and_apply(ctrl,
                           (heater_key('FORCE', ch), '0'),
                           (heater_key('FORCELEVEL', ch), '0'),
                           (heater_key('ENABLE', ch), '0'))


class OverTempGuard:
    """되먹임 센서가 **ACF 상한을 넘으면 히터를 끈다** (운영자 지시 2026-09-06).

    ⭐ **상수 0개.**  `HEATER?SENSOR` → 그 센서의 `SENSOR?UPPERLIMIT` 를
    컨트롤러에서 읽는다 (`read_limits`, `HTRSET` 클램프와 **같은 출처**).
    현행 guide ACF 는 `HEATERASENSOR=0` → `SENSORA`(`RTD9_DMP`) → 상한 **50.0**
    이고, ACF 가 바뀌면 따라온다.

    ⭐ **STATUS 원값을 본다.**  ⚠️ 2026-09-06 까지는 `hk.decode_rtd()` 가 한계
    밖을 버려서 과열이 `_sample` 에서 **결측으로만** 보였고, 그것이 이 차단을
    STATUS 로 짠 원래 이유였다.  같은 날 운영자 지시로 그 폐기를 걷었으므로
    이제는 `_sample` 로도 보이지만, **STATUS 를 계속 본다** -- `_tick` 안에서
    `_sample` 갱신보다 먼저 돌아 순서에 안 매이고, 창구를 한 겹 덜 탄다.

    ⚠️ **한계 셋** (다음 사람이 과신하지 않도록 여기 적어 둔다):

    1. **주기가 HK 루프**다 (`[hk] interval`, 기본 60초) -- 최대 그만큼 늦다.
       운영자 확정(2026-09-06): 추가 컨트롤러 왕복을 두지 않는다 (접속자가
       컨트롤러당 하나라 왕복이 취득과 락을 다툰다).  빨리 보려면 운영자가
       `interval` 을 낮춘다.
    2. **결측으로는 끄지 않는다** -- 히터·게이지 명령 자체가 MOD10 VCPU 를
       재시작해 STATUS 에 구멍을 내므로(11.18), 결측을 과열로 읽으면 우리
       명령이 우리 차단을 부른다.  대신 결측이 이어지면 경고를 남긴다.
    3. **한계는 한 번 읽어 캐시한다** -- ACF 를 갈아 끼우고 `APPLYALL` 을
       다시 돌렸다면 프로그램도 다시 띄울 것.

    ⭐ 래치는 **같은 초과로 두 번 쓰지 않기 위한 것**이다.  온도가 상한 아래로
    돌아오면 풀리지만 **히터는 꺼진 채로 남는다** -- 되켜는 것은 사람 몫이다.
    """

    def __init__(self, ch: str = CH) -> None:
        self.ch = ch
        #: 되읽은 한계 (`Limits`).  못 읽었으면 `None` -- 다음 바퀴에 다시 시도.
        self.limits = None
        #: 이미 껐나 -- 같은 초과로 반복해 쓰지 않기 위한 래치.
        self.tripped = False
        self._warned_limits = False
        self._warned_missing = False

    async def check(self, ctrl, status: dict) -> str:  # noqa: ANN001
        """한 바퀴.  껐으면 **사유 문구**, 아무 일도 없으면 `''`.

        부르는 쪽(`hk._tick`)이 그 문구를 CSV `event` 열에 남긴다.
        """
        if ctrl is None or not status:
            return ''
        if self.limits is None:
            try:
                self.limits = await read_limits(ctrl, self.ch)
            except Exception as exc:      # noqa: BLE001
                if not self._warned_limits:
                    self._warned_limits = True
                    log.error('heater over-temperature guard is NOT armed -- '
                              'cannot read the feedback sensor limits (%s)', exc,
                              extra={'detail': '⛔ 상한을 모르는 동안은 차단이 '
                                               '없다'})
                return ''
            log.info('heater over-temperature guard armed -- turns off above '
                     '%s %.2f °C', self.limits.source, self.limits.hi,
                     extra={'detail': '판정 주기는 HK 루프다'})
            self._warned_limits = False
        lim = self.limits
        val = _as_float(status.get(temp_field(lim.sensor)))
        if val is None:
            if not self._warned_missing:
                self._warned_missing = True
                log.warning('over-temperature guard: STATUS has no temperature '
                            'for the feedback sensor %s -- cannot judge',
                            lim.source,
                            extra={'detail': '결측으로는 끄지 않는다 (VCPU '
                                             '재시작 창이 이 모양이다)'})
            return ''
        self._warned_missing = False
        if val <= lim.hi:
            if self.tripped:
                self.tripped = False
                log.info('feedback sensor %s is back below the limit '
                         '(%.2f <= %.2f)', lim.source, val, lim.hi,
                         extra={'detail': '⚠️ 히터는 꺼진 채다.  다시 쓰려면 '
                                          'HTRSET / HTRFORCE 를 명시적으로 칠 것'})
            return ''
        if self.tripped:
            return ''                     # 이미 껐다 -- 같은 초과로 또 쓰지 않는다
        log.error('feedback sensor %s = %.2f °C is above the limit %.2f -- '
                  'turning the heater off', lim.source, val, lim.hi,
                  extra={'detail': 'FORCE·FORCELEVEL·ENABLE 셋을 내린다'})
        await shutdown(ctrl, self.ch)
        self.tripped = True
        log.error('heater %s turned off', self.ch,
                  extra={'detail': '⚠️ %s' % VCPU_NOTE})
        return ('HEATER OFF -- %s=%.2f > %.2f (over-temperature)'
                % (lim.source, val, lim.hi))


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
        log.warning('could not read %s -- skipping the RAMPRATE conversion '
                    '(%s)', UPDATETIME_KEY, exc)
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
    log.info('heater %s Ramp=%d RampRate=%d%s', ch, on, rate,
             ' (%s)' % conv if conv else '',
             extra={'detail': '⚠️ %s' % VCPU_NOTE})
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
    log.info('heater %s PID=%g/%g/%g', ch, p, i, d,
             extra={'detail': '⚠️ %s' % VCPU_NOTE})
    return VCPU_NOTE


#: 명령어 → 조회가 되읽을 (이름표, ACF 키 꼬리) 짝.  ⭐ **응답의 이름표를 한
#: 곳에 모은다** -- 설정 응답과 조회 응답이 같은 낱말을 쓰게 하기 위해서다.
GROUPS = {
    'HTRSET':   (('Enable', 'ENABLE'), ('Target', 'TARGET')),
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

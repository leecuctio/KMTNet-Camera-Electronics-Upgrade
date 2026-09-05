#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide ACF 타이밍 스크립트에서 프레임 주기를 **계산**한다.

## 왜 계산하나

노출 의미론(raw spec 10.1절)이 요구하는 두 값이 ACF 안에 있는데 코드가
그것을 몰랐다:

* **최소 프레임 주기** -- `EXPTIME`(독출 개시 간격)이 이보다 짧을 수 없다.
  종전 `exptime_min` 은 근거 없는 잠정값 1.0 s 였다.
* **트리거 -> 트랜스퍼 지연** -- 시퀀서는 트리거를 받고 `IntUnit(IntMS)` +
  `NoIntUnit(NoIntMS)` 를 돌린 **뒤에** 프레임 트랜스퍼를 한다.  `DATE-OBS`
  는 그 트랜스퍼(=독출 개시) 시각이므로(10.1-4·10.1-5), 호스트가 트리거를
  낸 시각을 그대로 적으면 그만큼 **이르다.**

## 노출 경계가 트랜스퍼라는 근거 (실측 ACF)

`MOD3\\LABEL1..3 = S1,S2,S3`(store) · `LABEL5..7 = I1,I2,I3`(image) 이고,
상태 정의가 이렇게 갈린다:

* `IMAGE1..6` -> **S 상만** 구동 -- `Line`(독출)·`SkipLine`(flush)이 쓴다.
  즉 **독출·유휴 중에 image 영역은 손대지 않는다** = 계속 적분한다.
  ⭐ R2612 부터 유휴 루프는 `SkipLine` 도 부르지 않는다(`LINE3="X; X(100)"`,
  운영자 2026-09-05) -- 유휴는 **클록 자체가 없는** 상태다.  `X` 는 모든
  채널 `keep` 이라 store 도 image 도 그대로 둔다.
* `FRAME1..6` -> **S + I 를 함께** 구동 -- `FrameShift(1033)` 이 쓴다.
  이것이 image -> store 전송, 곧 **노출 경계**다.

⭐ 그래서 호스트가 유휴 상태로 기다리는 동안에도 적분이 이어지고,
**노출 = 직전 트랜스퍼 ~ 이번 트랜스퍼**가 된다 (10.1절 그대로).  (구
R2611 까지의 유휴 `SkipLine` 은 store 만 비웠다 -- image 와 무관했으므로
그것을 뺀 R2612 에서도 이 결론은 그대로다.)

## 틱 가정

Archon 타이밍 코어는 100 MHz (틱 = 10 ns).  **스크립트가 그 앵커를 들고
있다** -- `NoIntUnit` 이 정확히 100,000 틱 = 1 ms 가 되도록 짜여 있어
(`NoIntMS` 라는 이름이 그 뜻이다), 계산이 그 값을 재현하지 못하면 틱
가정이나 셈법이 틀린 것이다.  `verify_tick_anchor()` 가 그 검산이다.

⚠️ **PROVISIONAL** -- 여기 값은 ACF 를 읽어 **계산**한 것이지 실측이 아니다.
첫 guide 구동에서 실제 프레임 간격을 재고, 어긋나면 이 모듈의 셈법(행당
틱)을 고친다.  계산이 실측보다 몇 % 짧게 나오는 것은 정상이다 -- 명령
왕복·버퍼 전환 같은 스크립트 밖 비용이 빠져 있다.
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger('icg_archon.acftiming')

#: 틱 [s].  100 MHz.
TICK = 1e-8

#: `NoIntUnit`/`IntUnit` 한 단위의 틱 -- 검산 앵커 (정확히 1 ms).
UNIT_TICKS = 100_000

_PARAM = re.compile(r'^\s*([A-Za-z_]\w*)\s*=\s*(-?\d+)\s*$')


def parameters(config: dict) -> dict[str, int]:
    """ACF `PARAMETERn="Name=값"` -> `{Name: 값}`.

    `controller.ArchonController.config`(ACF 설정 줄 표)를 그대로 받는다.
    """
    out: dict[str, int] = {}
    for key, raw in (config or {}).items():
        if not key.upper().startswith('PARAMETER'):
            continue
        m = _PARAM.match(str(raw).strip().strip('"'))
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


#: 이 모듈이 셈하는 **guide 타이밍 스크립트의 형태** -- 줄 번호와 그 줄에 있어야
#: 하는 호출.  science ACF 는 배치가 달라(`LINE11` 이 `IntUnit`,
#: `HorizontalSWShift(1200)`, `AT=2000`) 이 셈법을 씌우면 뜻 없는 수가 나온다
#: (DevNote 9.15).
_SHAPE = {
    # R2613+: 유휴 루프 첫 줄이 flush 검사, 끝에 FlushFrame 블록.  ⭐ 이 둘이
    # 없으면 '파라미터는 있는데 스크립트가 안 쓰는' R2611 같은 판이거나 구판이다
    # -- 호스트가 Exposures=n 으로 걸면 첫 장이 flush 없이 저장되므로 걸러야 한다.
    'LINE1': 'IF FirstFlush GOTO FlushFrame',
    'LINE11': 'CALL FrameShift(',
    'LINE12': 'CALL HorizontalShift(',
    'LINE47': 'CALL PixelFirst',
    'LINE48': 'CLAMP; X(',
    'LINE118': 'CALL SkipLine(FlushLines)',
}


def script_matches(config: dict) -> list[str]:
    """ACF 설정 줄 표가 이 모듈이 아는 형태인가 -- 어긋난 줄 목록 (비면 맞다)."""
    bad: list[str] = []
    for key, needle in _SHAPE.items():
        got = str((config or {}).get(key, ''))
        if needle not in got:
            bad.append('%s=%r' % (key, got))
    return bad


def verify_tick_anchor() -> bool:
    """`NoIntUnit` 셈이 정확히 1 ms 인가 -- 틱 가정·셈법의 자체 검산.

    `NOINT; CALL SmallIntUnit(502)`(1) + 502 x `SmallIntUnit`(199)
    + `X; X(99)`(100) + `X; RETURN`(1) = 100,000.
    """
    small = (1 + 11) + (1 + 11) + 6 * (1 + 28) + 1          # 199
    unit = 1 + 502 * small + (1 + 99) + 1
    return unit == UNIT_TICKS


#: 서브루틴 한 회의 틱 (guide 스크립트를 행 단위로 옮겨 센다).
_PIXEL_FIRST = (1 + 20) + 1 + 1 + 1 + 3 * (1 + 10) + (1 + 64) + (1 + 10) \
    + (1 + 64) + 1                                           # 199
_PIXEL = _PIXEL_FIRST + 1
_CLAMP_HOLD = 1 + 10000

#: `LINE12 DGLOW; CALL HorizontalShift(600)` -- 트랜스퍼 직후 직렬 레지스터를
#: **쓸어내는** 횟수.  ⚠️ 스크립트 **리터럴**이라 `Pixels` 파라미터와 무관하다:
#: 레지스터 절반(536 소자)을 넘기게 잡은 flush 수이고, `Pixels` 를 528/529 로
#: 트림해도(P-k, `acf/README.md`) 이 값은 그대로다.  `LINE53`(`SkipLine` 안)도 같다.
_FRAME_HSHIFT = 600


def _shift(n_phase: int, hold: int) -> int:
    return n_phase * (1 + hold) + 1


def skipline_ticks(params: dict[str, int]) -> int:
    """`SkipLine` 한 회의 틱 -- flush 가 store 1행을 버리는 비용.

    (R2611 까지는 유휴 루프도 이것을 불렀다.  R2612 부터 유휴는 `X; X(100)`
    으로 가만히 있으므로, 이 비용은 **flush 경로에서만** 든다.)

        LINE52  RGHIGH; CALL VerticalShift        1 + vshift
        LINE53  X; CALL HorizontalShift(600)      1 + hshift x 600
        LINE54  CLAMP; X(10000)                   _CLAMP_HOLD
        LINE55  NOCLAMP; RETURN SkipLine          1

    ⚠️ 디지타이즈가 없다 -- `Pixel` 루틴을 안 타므로 `Pixels` 와 **무관**하고
    `AT`·`ST` 로만 결정된다.  본 독출과 배율이 다른 이유가 여기다.
    """
    at = int(params.get('AT', 100))
    st = int(params.get('ST', 10))
    return (1 + _shift(6, at)
            + 1 + _shift(6, st) * _FRAME_HSHIFT
            + _CLAMP_HOLD + 1)


def flush_lines(params: dict[str, int], *, lines: int, pixels: int) -> int:
    """flush 프레임의 `SkipLine` 횟수 -- **본 독출 소요와 같아지는 수**.

    규격 10.1-2 (v1.10).  버릴 첫 프레임은 디지타이즈할 이유가 없어
    `SkipLine` 으로 비우는데, 그것이 본 독출보다 **빨리 끝나면 첫 저장
    프레임의 실적분이 `EXPTIME` 보다 짧아진다.**  그래서 횟수를 맞춘다.

    ⛔ **`Pixels`·`Lines`·`AT`·`ST` 중 하나라도 바뀌면 값이 바뀐다** -- 그리고
    민감도가 균등하지 않다 (현행 `Pixels=540 Lines=1033 AT=100 ST=10` 기준
    2448):

        Lines   정비례 (1:1)
        Pixels  600 이면 2692            (+10 %)
        AT      200 이면 2419            (-1 %)
        ST       20 이면 1433            (**-41 %**)

    `ST` 가 압도적인 것은 flush 쪽이 `SkipLine`(= AT·ST 만)인데 맞출 대상인
    본 독출은 디지타이징 `Pixel` 루틴이 대부분이라 `ST` 비중이 작기 때문이다
    -- 한쪽만 크게 움직인다.
    """
    return round(frame_timing(params, lines=lines, pixels=pixels)['readout']
                 / (skipline_ticks(params) * TICK))


def check_flush_lines(params: dict[str, int], *,
                      lines: int, pixels: int) -> tuple[int, int] | None:
    """ACF 의 `FlushLines` 가 계산값과 맞나 -- 어긋나면 `(ACF값, 계산값)`.

    ⭐ **파생값을 상수로 두는 대가를 여기서 치른다** (운영자 확정 2026-09-05:
    *"Pixels·Lines 를 바꾸는 것은 큰일이라 잘 없을 것"*).  `FlushLines` 와 그
    것을 낳는 넷이 **같은 파일에** 있고 아무도 대사하지 않으므로, 누가
    `Pixels` 만 고치면 **오류 없이 첫 저장 프레임의 실적분만 틀린다** -- 이
    검산이 그 조용한 어긋남을 소리 나게 만든다.  `GO` 마다 쓰지 않으므로
    (호스트가 계산해 넣는 안 대신) 기동 때 한 번만 본다.

    `FlushLines` 가 아예 없으면 `None` -- 아직 도입 전인 ACF 다.
    """
    if 'FlushLines' not in params:
        return None
    want = flush_lines(params, lines=lines, pixels=pixels)
    got = int(params['FlushLines'])
    return None if got == want else (got, want)


def frame_timing(params: dict[str, int], *,
                 lines: int, pixels: int) -> dict[str, float]:
    """프레임 한 장의 구간별 소요 [s].

    Args:
        params: `parameters()` 결과 (`NoIntMS`·`AT`·`ST`·`PreSkipPixels` 등).
        lines/pixels: 독출 행·열 (`Lines`/`Pixels`).

    Returns:
        `transfer`(트랜스퍼) · `readout`(독출) · `noint`(NoIntMS 대기) ·
        `floor`(IntMS=0 일 때의 최소 주기) · `trigger_to_transfer`
        (트리거 -> 트랜스퍼 지연, `IntMS` 는 뺀 상수분).
    """
    at = int(params.get('AT', 100))
    st = int(params.get('ST', 10))
    noint_ms = int(params.get('NoIntMS', 0))
    preskip = int(params.get('PreSkipPixels', 0))
    postskip = int(params.get('PostSkipPixels', 0))
    overpix = int(params.get('OverscanPixels', 0))
    vbin = max(int(params.get('VerticalBinning', 1)), 1)

    vshift = _shift(6, at)          # IMAGE1~6 (S 상) -- store 1행
    fshift = _shift(6, at)          # FRAME1~6 (S+I) -- 트랜스퍼 1행
    hshift = _shift(6, st)

    def run(n: int) -> int:
        return _PIXEL_FIRST + _PIXEL * (n - 1) if n > 0 else 0

    line = (1 + vshift * vbin
            + 1 + run(preskip)
            + 1 + run(pixels)
            + 1 + run(postskip)
            + 1 + run(overpix)
            + 1 + _PIXEL_FIRST
            + _CLAMP_HOLD + 1)

    transfer = 1 + fshift * lines + 1 + hshift * _FRAME_HSHIFT + _CLAMP_HOLD
    readout = line * lines
    noint = noint_ms * UNIT_TICKS

    t = {
        'transfer': transfer * TICK,
        'readout': readout * TICK,
        'noint': noint * TICK,
        'line': line * TICK,
        # 무엇을 셈했는지 같이 돌려준다 -- 로그에서 ACF 가 바뀐 것이 보이도록.
        'lines': float(lines),
        'pixels': float(pixels),
    }
    t['floor'] = t['noint'] + t['transfer'] + t['readout']
    # `IntMS` 는 호출측이 더한다 -- 상수분만 돌려준다.
    t['trigger_to_transfer'] = t['noint'] + t['transfer']
    # ⭐ 트리거 -> `FrameShift` **개시** (10.1-4 의 DATE-OBS 기준).  `IntUnit` 뒤
    # `NoIntUnit` 만 거치고 곧바로 LINE11 이다 -- transfer 항이 없다.
    t['to_frameshift'] = t['noint']
    # FrameShift 개시 -> 프레임 완료 (transfer + 독출).  완료 관측 시각에서
    # 이것을 빼면 그 프레임의 FrameShift 개시 = 다음 프레임의 DATE-OBS.
    t['frameshift_to_done'] = t['transfer'] + t['readout']
    # flush 프레임 (R2613 LINE115~118): FS + HS + CLAMP + SkipLine x FlushLines.
    # 규격 10.1-2 -- 본 독출 소요와 같아야 첫 저장 프레임의 실적분이 맞다.
    fl = params.get('FlushLines')
    t['flush'] = (transfer + skipline_ticks(params) * int(fl)) * TICK if fl else None
    return t


def describe(t: dict[str, float]) -> str:
    return ('Pixels %d x Lines %d -- 트랜스퍼 %.1f ms · 독출 %.0f ms · '
            'NoInt %.0f ms -> 최소 주기 %.3f s (트리거->트랜스퍼 %.0f ms)'
            % (t.get('pixels', 0), t.get('lines', 0),
               t['transfer'] * 1e3, t['readout'] * 1e3, t['noint'] * 1e3,
               t['floor'], t['trigger_to_transfer'] * 1e3))

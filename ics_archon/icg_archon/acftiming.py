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

## ⛔ 줄 번호로 색인하지 않는다 (운영자 지시 2026-09-06)

스크립트의 자리는 **`라벨:` 블록과 그 안의 호출 이름**으로 찾는다 -- `LINE12`
같은 번호로 집지 않는다.  근거는 실제로 겪은 일이다: R2617 이 `Exposure:`·
`FlushFrame:` 앞에 빈 줄을 하나씩 넣자 그 뒤 번호가 전부 밀렸고, 번호를 박아
둔 자리를 전수로 고쳐야 했다.  그때 **이미 틀어져 있던 주석 둘**도 나왔다
(유휴 루프를 `LINE3` 이라 적어 둔 것 -- R2613 부터 `LINE4` 였다).

⭐ 번호는 판마다 바뀌지만 **라벨과 호출 이름은 안 바뀐다** -- 바뀌면 그것이야말로
셈법을 다시 봐야 하는 변경이다.  그래서 형태 검사(`script_matches`)도, 스크립트
리터럴 읽기(`call_arg`)도 이름으로 간다.

## 노출 경계가 트랜스퍼라는 근거 (실측 ACF)

`MOD3\\LABEL1..3 = S1,S2,S3`(store) · `LABEL5..7 = I1,I2,I3`(image) 이고,
상태 정의가 이렇게 갈린다:

* `IMAGE1..6` -> **S 상만** 구동 -- `Line`(독출)·`SkipLine`(flush)이 쓴다.
  즉 **독출·유휴 중에 image 영역은 손대지 않는다** = 계속 적분한다.
  ⭐ R2612 부터 유휴 루프는 `SkipLine` 도 부르지 않는다 -- `Start:` 블록의
  대기가 `X; X(100)` 뿐이라(운영자 2026-09-05) **클록 자체가 없는** 상태다.
  `X` 는 모든 채널 `keep` 이라 store 도 image 도 그대로 둔다.
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

    ⚠️ **슬롯 번호(`PARAMETERn` 의 n)는 여기서 버린다** -- 이름으로 찾는다.
    구판 ACF 는 슬롯 0 이 `ContinuousExposures` 였고 현행은 `FirstFlush` 다.
    (슬롯 **순서**는 `LOADPARAMS` 적용 순서라 별개 문제이고, 그것은
    `ics_archon/config.py` 의 `param_*_slot` 이 든다.)
    """
    out: dict[str, int] = {}
    for key, raw in (config or {}).items():
        if not key.upper().startswith('PARAMETER'):
            continue
        m = _PARAM.match(str(raw).strip().strip('"'))
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


# -- 스크립트를 이름으로 읽는다 --------------------------------------------

_LINE_KEY = re.compile(r'^LINE(\d+)$')
#: `Exposure:` 처럼 **줄 전체가 라벨**인 것만.  `X; GOTO Start` 안의 콜론은 없다.
_LABEL = re.compile(r'^([A-Za-z_]\w*):$')


def script(config: dict) -> list[str]:
    """ACF 설정 줄 표 -> 타이밍 스크립트 (`LINE0`..`LINEn` 순서, 빈 줄 포함).

    ⚠️ 돌려주는 것은 **읽기 편의용 순서 목록**이다 -- 이 목록의 색인을 코드에
    박아 두지 말 것(그것이 곧 줄 번호 색인이다).  자리를 집을 때는 `blocks()`
    나 `call_arg()` 를 쓴다.
    """
    out: dict[int, str] = {}
    for key, raw in (config or {}).items():
        m = _LINE_KEY.match(str(key).upper())
        if m:
            out[int(m.group(1))] = str(raw).strip().strip('"').strip()
    if not out:
        return []
    return [out.get(i, '') for i in range(max(out) + 1)]


def blocks(config: dict) -> dict[str, list[str]]:
    """`라벨:` -> 그 아래 줄들 (다음 라벨 전까지; 빈 줄은 뺀다).

    ⭐ **블록으로 나누는 것이 요점이다** -- 같은 호출이 여러 블록에 나오기
    때문이다.  guide 는 `CALL FrameShift(1033)` 이 정상 경로(`Continuous:`)와
    flush 경로(`FlushFrame:`)에 하나씩, `CALL HorizontalShift(600)` 은 그 둘과
    `SkipLine:` 에 하나씩 있다.  블록을 안 가르면 어느 것을 집었는지 모른다.

    ⚠️ `Exposure:` 는 `Exposures--` 한 줄이고 곧바로 `Continuous:` 로
    **떨어져 내려온다** -- 독출 순서를 보려면 `Continuous:` 를 봐야 한다.
    """
    out: dict[str, list[str]] = {}
    cur: list[str] | None = None
    for text in script(config):
        m = _LABEL.match(text)
        if m:
            cur = out.setdefault(m.group(1), [])
            continue
        if cur is not None and text:
            cur.append(text)
    return out


def call_arg(config: dict, label: str, routine: str) -> int | None:
    """`<label>:` 블록의 `CALL <routine>(<정수>)` 인자.  없거나 정수가 아니면 `None`.

    ⭐ **스크립트 리터럴을 코드에 베끼지 않으려고 있다.**  `FrameShift(1033)` ·
    `HorizontalShift(600)` 은 파라미터가 아니라 스크립트에 박힌 수라, 상수로
    복사해 두면 ACF 만 고쳤을 때 **오류 없이 계산만 틀린다.**
    ⚠️ 인자가 파라미터 이름인 호출(`CALL Line(Lines)`)은 `None` -- 그런 것은
    `parameters()` 로 읽는다.
    """
    pat = re.compile(r'CALL\s+%s\s*\(\s*(-?\d+)\s*\)' % re.escape(routine))
    for text in blocks(config).get(label, []):
        m = pat.search(text)
        if m:
            return int(m.group(1))
    return None


#: 이 모듈이 셈하는 **guide 타이밍 스크립트의 형태** -- `(라벨, 그 블록에 있어야
#: 하는 줄의 정규식)`.  ⛔ **줄 번호가 아니다** (머리말).
#:
#: science ACF 는 배치가 달라 이 셈법을 씌우면 뜻 없는 수가 나온다 (DevNote
#: 9.15).  블록 기준으로도 깨끗이 갈린다 -- science 에는 `FrameShift:` 라벨이
#: 아예 없고(전면 독출이라 프레임 트랜스퍼가 없다) 수평 이송이
#: `HorizontalSWShift(1200)` 이다.
_SHAPE = (
    # R2613+: 유휴 루프가 flush 를 검사하고, `FlushFrame:` 블록이 있다.  ⭐ 이 둘이
    # 없으면 '파라미터는 있는데 스크립트가 안 쓰는' R2611 같은 판이거나 구판이다
    # -- 호스트가 Exposures=n 으로 걸면 첫 장이 flush 없이 저장되므로 걸러야 한다.
    ('Start', r'IF\s+FirstFlush\s+GOTO\s+FlushFrame'),
    ('Start', r'IF\s+Exposures\s+GOTO\s+Exposure'),
    # 정상 경로 -- 적분 · 트랜스퍼 · 레지스터 쓸기 · 행 독출.
    ('Continuous', r'CALL\s+IntUnit\('),
    ('Continuous', r'CALL\s+FrameShift\('),
    ('Continuous', r'CALL\s+HorizontalShift\('),
    ('Continuous', r'CALL\s+Line\('),
    # 행 독출 -- ⚠️ `$` 로 **인자 없는** 호출을 집는다(클록 +1 의 근거).
    ('Line', r'CALL\s+PixelFirst\s*$'),
    ('Line', r'CLAMP;\s*X\('),
    # 버리는 행 -- flush 비용의 단위.
    ('SkipLine', r'CALL\s+VerticalShift'),
    ('SkipLine', r'CALL\s+HorizontalShift\('),
    # flush 프레임 (규격 10.1-2).
    ('FlushFrame', r'CALL\s+FrameShift\('),
    ('FlushFrame', r'CALL\s+SkipLine\(FlushLines\)'),
)


def script_matches(config: dict) -> list[str]:
    """타이밍 스크립트가 이 모듈이 아는 형태인가 -- 어긋난 것 목록 (비면 맞다)."""
    blk = blocks(config)
    bad: list[str] = []
    for label, pattern in _SHAPE:
        body = blk.get(label)
        if body is None:
            msg = '%s: 라벨이 없다' % label
            if msg not in bad:
                bad.append(msg)
            continue
        if not any(re.search(pattern, text) for text in body):
            bad.append('%s: %s 를 부르는 줄이 없다' % (label, pattern))
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

#: `CALL HorizontalShift(600)` -- 트랜스퍼 직후 직렬 레지스터를 **쓸어내는** 횟수의
#: **대체값**이다.  정본은 스크립트이고 `call_arg()` 가 읽는다 -- 이 상수는 그것을
#: 못 읽었을 때만 쓴다(로그로 알린다).
#: ⚠️ 스크립트 **리터럴**이라 `Pixels` 파라미터와 무관하다: 레지스터 절반(536 소자)을
#: 넘기게 잡은 수이고, `Pixels` 를 528/529 로 트림해도(P-k, `acf/README.md`) 그대로다.
#: 같은 수가 세 자리에 있다 -- 정상 경로 · `SkipLine:` 안 · flush 경로.
_FRAME_HSHIFT = 600


def _shift(n_phase: int, hold: int) -> int:
    return n_phase * (1 + hold) + 1


def _hshift_count(config: dict, label: str) -> int:
    """`<label>:` 블록의 `HorizontalShift` 횟수 -- 못 읽으면 대체값."""
    n = call_arg(config, label, 'HorizontalShift')
    if n is None:
        if config:
            log.warning('could not read the HorizontalShift count in the %s: '
                        'block -- falling back to %d', label, _FRAME_HSHIFT)
        return _FRAME_HSHIFT
    return n


def skipline_ticks(params: dict[str, int], *, config: dict | None = None) -> int:
    """`SkipLine` 한 회의 틱 -- flush 가 store 1행을 버리는 비용.

    (R2611 까지는 유휴 루프도 이것을 불렀다.  R2612 부터 유휴는 `X; X(100)`
    으로 가만히 있으므로, 이 비용은 **flush 경로에서만** 든다.)

    `SkipLine:` 블록을 그대로 옮겨 센다:

        RGHIGH; CALL VerticalShift          1 + vshift
        DGHIGH; CALL HorizontalShift(600)   1 + hshift x 600   <- 600 은 스크립트에서 읽는다
        CLAMP;  X(10000)                    _CLAMP_HOLD
        NOCLAMP; RETURN SkipLine            1

    ⚠️ 디지타이즈가 없다 -- `Pixel` 루틴을 안 타므로 `Pixels` 와 **무관**하고
    `AT`·`ST` 로만 결정된다.  본 독출과 배율이 다른 이유가 여기다.

    Args:
        config: ACF 설정 줄 표.  주면 `HorizontalShift` 횟수를 스크립트에서
            읽는다; 없으면 대체값 `_FRAME_HSHIFT`.
    """
    at = int(params.get('AT', 100))
    st = int(params.get('ST', 10))
    n_h = _hshift_count(config or {}, 'SkipLine')
    return (1 + _shift(6, at)
            + 1 + _shift(6, st) * n_h
            + _CLAMP_HOLD + 1)


def flush_lines(params: dict[str, int], *, lines: int, pixels: int,
                config: dict | None = None) -> int:
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
    readout = frame_timing(params, lines=lines, pixels=pixels,
                           config=config)['readout']
    return round(readout / (skipline_ticks(params, config=config) * TICK))


def check_flush_lines(params: dict[str, int], *, lines: int, pixels: int,
                      config: dict | None = None) -> tuple[int, int] | None:
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
    want = flush_lines(params, lines=lines, pixels=pixels, config=config)
    got = int(params['FlushLines'])
    return None if got == want else (got, want)


def frame_timing(params: dict[str, int], *, lines: int, pixels: int,
                 config: dict | None = None) -> dict[str, float]:
    """프레임 한 장의 구간별 소요 [s].

    Args:
        params: `parameters()` 결과 (`NoIntMS`·`AT`·`ST`·`PreSkipPixels` 등).
        lines/pixels: 독출 행·열 (`Lines`/`Pixels` 파라미터).
        config: ACF 설정 줄 표.  주면 트랜스퍼의 **스크립트 리터럴**
            (`FrameShift(<행>)` · `HorizontalShift(<횟수>)`)을 이름으로 읽는다.
            ⭐ 안 주면 `lines` 와 `_FRAME_HSHIFT` 로 물러난다 -- 그것이 종전
            거동이고, `FrameShift` 의 인자가 `Lines` 와 **다른 판**에서는 틀린다.

    Returns:
        `transfer`(트랜스퍼) · `readout`(독출) · `noint`(NoIntMS 대기) ·
        `floor`(IntMS=0 일 때의 최소 주기) · `trigger_to_transfer`
        (트리거 -> 트랜스퍼 지연, `IntMS` 는 뺀 상수분) · `to_frameshift` ·
        `frameshift_to_done` · `flush`(`FlushLines` 가 있을 때).
    """
    cfg = config or {}
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

    def transfer_ticks(label: str) -> int:
        """`<label>:` 블록의 트랜스퍼 = FrameShift + 레지스터 쓸기 + clamp.

        ⭐ 행수를 **스크립트에서** 읽는다 -- `FrameShift(1033)` 은 리터럴이라
        `Lines` 파라미터와 우연히 같을 뿐이다(`acf/README.md` 파생값 표).
        """
        n_line = call_arg(cfg, label, 'FrameShift')
        return (1 + fshift * (n_line if n_line is not None else lines)
                + 1 + hshift * _hshift_count(cfg, label)
                + _CLAMP_HOLD)

    line = (1 + vshift * vbin
            + 1 + run(preskip)
            + 1 + run(pixels)
            + 1 + run(postskip)
            + 1 + run(overpix)
            + 1 + _PIXEL_FIRST
            + _CLAMP_HOLD + 1)

    transfer = transfer_ticks('Continuous')
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
    # `NoIntUnit` 만 거치고 곧바로 `FrameShift` 다 -- transfer 항이 없다.
    t['to_frameshift'] = t['noint']
    # FrameShift 개시 -> 프레임 완료 (transfer + 독출).  완료 관측 시각에서
    # 이것을 빼면 그 프레임의 FrameShift 개시 = 다음 프레임의 DATE-OBS.
    t['frameshift_to_done'] = t['transfer'] + t['readout']
    # flush 프레임 (`FlushFrame:` 블록): 그 블록의 트랜스퍼 + SkipLine x FlushLines.
    # 규격 10.1-2 -- 본 독출 소요와 같아야 첫 저장 프레임의 실적분이 맞다.
    fl = params.get('FlushLines')
    if fl:
        flush_transfer = transfer_ticks('FlushFrame') if cfg else transfer
        t['flush'] = (flush_transfer
                      + skipline_ticks(params, config=cfg) * int(fl)) * TICK
    else:
        t['flush'] = None
    return t


def describe(t: dict[str, float]) -> str:
    return ('Pixels %d x Lines %d -- 트랜스퍼 %.1f ms · 독출 %.0f ms · '
            'NoInt %.0f ms -> 최소 주기 %.3f s (트리거->트랜스퍼 %.0f ms)'
            % (t.get('pixels', 0), t.get('lines', 0),
               t['transfer'] * 1e3, t['readout'] * 1e3, t['noint'] * 1e3,
               t['floor'], t['trigger_to_transfer'] * 1e3))

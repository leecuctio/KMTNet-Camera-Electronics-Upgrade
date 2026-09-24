# -*- coding: utf-8 -*-
"""science ACF 타이밍 스크립트를 **틱 단위로 해석**해 프레임 주기를 계산한다.

## 왜 있나

`config.MIN_FRAME_PERIOD`(12.78 s)는 `fetch_timeout`·`fetch_buffers`·`wrote_window`
기동 검사의 입력인데, 종전에는 **손으로 센 상수**였다 (DevNote 8.13 의 틱 모형 ->
11.85-(10) 의 200틱 정정 -> 12.7753 s).  ACF 가 바뀌면(사다리 T2 -> 12.82 · T3 -> 13.06,
11.85-(7)) 사람이 다시 세어 상수를 고쳐야 했고, 안 고치면 **오류 없이 검사만 헐거워진다**.
이 모듈은 ACF 를 읽어 같은 수를 **기계로** 내고, 기동에서 상수와 대사한다
(`check_min_frame_period`).

## guide 의 `icg_archon/acftiming.py` 와 다른 점

guide 모듈은 서브루틴 한 회의 틱을 **스크립트에서 손으로 옮겨 상수로** 들고 있다
(`_PIXEL_FIRST = 199` 등).  판마다 그 상수를 대조해야 하고 science 에는 그대로 못 쓴다
(배치가 다르다 -- DevNote 9.15).  여기서는 **스크립트를 해석**한다:

* 줄 하나 = **1틱** + 붙은 것.  `X(n)` 은 그 상태를 n 틱 더 유지 (`RGHIGH; X(19)` = 20틱).
  `X(AT)` 처럼 인자가 파라미터 이름이면 그 값.
* `CALL Sub(k)` = 호출 줄 1틱 + 몸통 k 회.  ⭐ **첫 회는 `Sub:` 에서, 둘째부터는
  `RETURN <라벨>` 의 그 라벨에서 재진입한다** -- `PixelFirst:` 위에 `Pixel: RGHIGH` 한 줄이
  있어 첫 화소 = 호출줄 1 + 199, 둘째부터 = `Pixel:` 1 + 199 로 **둘 다 200틱** 이다
  (DevNote 11.85-(10), 운영자 지적).  `k=0` 이면 호출 자체가 없고 1틱 (매뉴얼 p.52 ·
  11.86-(12)).  인자가 없으면 1회.  반복 수는 **호출 시점 스냅샷**이다 (11.86-(12)).
* `RETURN`·`GOTO`·`IF p GOTO`·`p--` 도 각각 1틱.  라벨 줄·빈 줄·`#` 주석은 0.
* 틱 = 10 ns (100 MHz).  앵커: `NoIntUnit` 한 회가 **정확히 100,000틱 = 1 ms** 여야
  한다 (`verify_tick_anchor`) -- 셈법이 이것을 못 맞추면 신뢰하지 않는다.

⭐ 프레임 주기는 **실제로 돌려서** 잰다 -- `Start:` 에서 시작해 `IF`/`GOTO` 를 파라미터
값대로 따라가며 `FCLK` 줄(프레임 개시)을 두 번 지나는 사이의 틱이다.  그래서 `Start:`
루프의 몇 틱, `IntUnit(0)`/`NoIntUnit(0)` 의 호출 줄까지 다 들어간다.  종전 손셈
12.7753 s 는 `Lines x Line` 만 센 **독출**이고, 주기 바닥은 그보다 `HorizontalSWShift(1200)`
+ `CLAMP` 만큼(≈0.93 ms) 길다 -- 상수 12.78 은 둘 다 덮는다.

⛔ **줄 번호로 색인하지 않는다** (운영자 2026-09-06) -- 라벨과 호출 이름으로만 본다.
⛔ **guide 셈에는 쓰지 않는다** -- guide 는 `icg_archon/acftiming.py` 가 정본이다.  다만
시험이 이 해석기로 guide ACF 를 돌려 그 모듈의 `floor` 와 **교차 검증**한다 -- 두 셈법이
독립이라 맞으면 둘 다 맞는 것이다.

⚠️ **PROVISIONAL** -- 계산이지 실측이 아니다.  실측 근거는 10장(12.77 s · 368.0 행/초)
하나이고 R2613 의 셈(12.776 s)이 그 안에 든다.  파형 판(T2/T3)을 채택하면 벤치 BIAS
연속 주기로 다시 대조할 것 (`bench_test_plan.md`).
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger('ics_archon.acftiming')

#: 틱 [s].  100 MHz.
TICK = 1e-8

#: `NoIntUnit`/`IntUnit` 한 단위의 틱 -- 검산 앵커 (정확히 1 ms).
UNIT_TICKS = 100_000

#: 프레임 개시를 알리는 상태 -- `FCLK; CALL Line(Lines)` (DevNote 8.13).
FRAME_STATE = 'FCLK'


class TimingError(ValueError):
    """스크립트를 해석할 수 없다 -- 형태가 이 모듈이 아는 것과 다르다."""


_PARAM = re.compile(r'^\s*([A-Za-z_]\w*)\s*=\s*(-?\d+)\s*$')
_LINE_KEY = re.compile(r'^LINE(\d+)$')
_LABEL = re.compile(r'^([A-Za-z_]\w*):$')
_CALL = re.compile(r'^CALL\s+([A-Za-z_]\w*)\s*(?:\(\s*([A-Za-z_]\w*|-?\d+)\s*\))?$')
_RETURN = re.compile(r'^RETURN\s+([A-Za-z_]\w*)$')
_GOTO = re.compile(r'^GOTO\s+([A-Za-z_]\w*)$')
_IF = re.compile(r'^IF\s+([A-Za-z_]\w*)\s+GOTO\s+([A-Za-z_]\w*)$')
_DEC = re.compile(r'^([A-Za-z_]\w*)\s*--$')
_INC = re.compile(r'^([A-Za-z_]\w*)\s*\+\+$')
_HOLD = re.compile(r'^([A-Za-z_]\w*)\s*\(\s*([A-Za-z_]\w*|-?\d+)\s*\)$')


def parameters(config: dict) -> dict[str, int]:
    """ACF `PARAMETERn="Name=값"` -> `{Name: 값}` (슬롯 번호는 버린다 -- 이름으로 찾는다)."""
    out: dict[str, int] = {}
    for key, raw in (config or {}).items():
        if not str(key).upper().startswith('PARAMETER'):
            continue
        m = _PARAM.match(str(raw).strip().strip('"'))
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def script(config: dict) -> list[str]:
    """ACF 설정 줄 표 -> 타이밍 스크립트 (`LINE0`..`LINEn` 순서, 빈 줄 포함).

    `ArchonController.parse_acf()` 가 만든 `config`(키 대문자, 따옴표 제거)를 그대로
    받는다.  발췌 txt 를 읽었으면 `TimingScript.from_text()` 로.
    """
    out: dict[int, str] = {}
    for key, raw in (config or {}).items():
        m = _LINE_KEY.match(str(key).upper())
        if m:
            out[int(m.group(1))] = str(raw).strip().strip('"').strip()
    if not out:
        return []
    return [out.get(i, '') for i in range(max(out) + 1)]


class _Stmt:
    """스크립트 한 줄 -- `state`(1틱) + 명령 하나."""

    __slots__ = ('no', 'state', 'kind', 'a', 'b', 'text')

    def __init__(self, no: int, state: str, kind: str, a=None, b=None,  # noqa: ANN001
                 text: str = '') -> None:
        self.no, self.state, self.kind, self.a, self.b, self.text = \
            no, state, kind, a, b, text


class TimingScript:
    """해석된 타이밍 스크립트 -- 라벨 표 + 문장 목록.

    `stmts[i]` 는 `_Stmt` 이거나 라벨(`str`, 끝에 `:` 없음)이다.  라벨은 틱을 안 쓴다.
    """

    def __init__(self, lines: list[str]) -> None:
        self.stmts: list = []
        self.labels: dict[str, int] = {}
        for no, raw in enumerate(lines):
            text = raw.strip()
            if not text or text.startswith('#'):
                continue
            m = _LABEL.match(text)
            if m:
                self.labels[m.group(1)] = len(self.stmts)
                self.stmts.append(m.group(1))
                continue
            head, _, tail = text.partition(';')
            state, instr = head.strip(), tail.strip()
            if not state:
                raise TimingError('LINE%d: 상태 이름이 없다 -- %r' % (no, raw))
            self.stmts.append(self._parse(no, state, instr, text))
        self._memo: dict = {}

    @classmethod
    def from_config(cls, config: dict) -> 'TimingScript':
        lines = script(config)
        if not lines:
            raise TimingError('ACF 에 타이밍 스크립트(LINEn)가 없다')
        return cls(lines)

    @classmethod
    def from_text(cls, text: str) -> 'TimingScript':
        return cls(text.replace('\r\n', '\n').split('\n'))

    @staticmethod
    def _parse(no: int, state: str, instr: str, text: str) -> _Stmt:
        if not instr:
            return _Stmt(no, state, 'none', text=text)
        m = _CALL.match(instr)
        if m:
            return _Stmt(no, state, 'call', m.group(1), m.group(2), text)
        m = _RETURN.match(instr)
        if m:
            return _Stmt(no, state, 'return', m.group(1), text=text)
        m = _GOTO.match(instr)
        if m:
            return _Stmt(no, state, 'goto', m.group(1), text=text)
        m = _IF.match(instr)
        if m:
            return _Stmt(no, state, 'if', m.group(1), m.group(2), text)
        m = _DEC.match(instr)
        if m:
            return _Stmt(no, state, 'dec', m.group(1), text=text)
        m = _INC.match(instr)
        if m:
            return _Stmt(no, state, 'inc', m.group(1), text=text)
        m = _HOLD.match(instr)
        if m:
            return _Stmt(no, state, 'hold', m.group(1), m.group(2), text)
        raise TimingError('LINE%d: 모르는 명령 -- %r' % (no, text))

    # -- 값 --------------------------------------------------------------

    @staticmethod
    def _value(arg, params: dict[str, int], where: str) -> int:  # noqa: ANN001
        if arg is None:
            return 1                               # `CALL Sub` -- 1회
        if re.fullmatch(r'-?\d+', str(arg)):
            return int(arg)
        if arg not in params:
            raise TimingError('%s: 파라미터 %r 가 ACF 에 없다' % (where, arg))
        return int(params[arg])

    def _index(self, label: str, where: str) -> int:
        if label not in self.labels:
            raise TimingError('%s: 라벨 %r 이 없다' % (where, label))
        return self.labels[label]

    # -- 서브루틴 한 회 (분석적, 메모) ----------------------------------------

    def _iteration(self, entry: str, params: dict[str, int],
                   depth: int = 0) -> tuple[int, str, dict[str, int]]:
        """`entry` 라벨에서 `RETURN` 까지 한 회 -- `(틱, RETURN 라벨, {파라미터: 감소 수})`.

        서브루틴 안에서는 `GOTO`/`IF` 를 지원하지 않는다 (우리 스크립트에 없다 --
        나오면 셈이 아니라 해석기 확장이 필요한 변경이다).
        """
        key = (entry, tuple(sorted(params.items())))
        hit = self._memo.get(key)
        if hit is not None:
            return hit
        if depth > 16:
            raise TimingError('%s: 호출 깊이 16 초과 (매뉴얼 한계)' % entry)
        i = self._index(entry, 'CALL')
        ticks = 0
        decs: dict[str, int] = {}
        while i < len(self.stmts):
            st = self.stmts[i]
            i += 1
            if isinstance(st, str):
                continue                           # 흘러 들어가는 라벨
            ticks += 1
            where = 'LINE%d' % st.no
            if st.kind == 'hold':
                ticks += self._value(st.b, params, where)
            elif st.kind == 'call':
                reps = self._value(st.b, params, where)
                t, d = self._call(st.a, reps, params, depth + 1)
                ticks += t
                for k, v in d.items():
                    decs[k] = decs.get(k, 0) + v
            elif st.kind == 'dec':
                decs[st.a] = decs.get(st.a, 0) + 1
            elif st.kind == 'inc':
                decs[st.a] = decs.get(st.a, 0) - 1
            elif st.kind == 'return':
                out = (ticks, st.a, decs)
                self._memo[key] = out
                return out
            elif st.kind in ('goto', 'if'):
                raise TimingError('%s: 서브루틴 %s 안의 %s 는 지원하지 않는다'
                                  % (where, entry, st.kind.upper()))
        raise TimingError('%s: RETURN 없이 스크립트가 끝난다' % entry)

    def _call(self, sub: str, reps: int, params: dict[str, int],
              depth: int = 0) -> tuple[int, dict[str, int]]:
        """`CALL sub(reps)` 의 몸통 틱 (호출 줄의 1틱은 **안** 든다) + 파라미터 감소."""
        if reps <= 0:
            return 0, {}
        t1, ret, d1 = self._iteration(sub, params, depth)
        decs = dict(d1)
        ticks = t1
        if reps > 1:
            t2, _ret2, d2 = self._iteration(ret, params, depth)
            ticks += t2 * (reps - 1)
            for k, v in d2.items():
                decs[k] = decs.get(k, 0) + v * (reps - 1)
        return ticks, decs

    def call_ticks(self, sub: str, reps, params: dict[str, int]) -> int:  # noqa: ANN001
        """`CALL <sub>(<reps>)` 한 줄의 틱 -- 호출 줄 1 + 몸통.  `reps` 는 수나 파라미터 이름."""
        n = self._value(reps, params, 'CALL %s' % sub)
        return 1 + self._call(sub, n, params)[0]

    def body_ticks(self, sub: str, params: dict[str, int]) -> int:
        """서브루틴 **한 회**(첫 진입)의 틱 -- 호출 줄은 빼고."""
        return self._iteration(sub, params)[0]

    def reentry_ticks(self, sub: str, params: dict[str, int]) -> int:
        """둘째 회부터의 틱 -- `RETURN` 라벨에서 재진입한 한 회 (`Pixel` 이면 200)."""
        _t, ret, _d = self._iteration(sub, params)
        return self._iteration(ret, params)[0]

    # -- 최상위 흐름을 돌린다 ---------------------------------------------

    def simulate(self, params: dict[str, int], *, start: str = 'Start',
                 frames: int = 2, max_stmts: int = 10_000) -> list[tuple[str, int, int]]:
        """`start` 라벨부터 `IF`/`GOTO` 를 파라미터대로 따라가며 최상위 줄의 (상태, 개시 틱,
        LINE 번호) 를 모은다.  `FRAME_STATE` 를 `frames` 번 지난 뒤 `start` 라벨로 돌아오면
        멈춘다 (유휴 루프에 들어가기 전).

        ⚠️ `params` 는 복사해 쓴다 -- `Exposures--`·`FirstFlush--` 가 그 사본을 깎는다.
        `CALL` 몸통은 분석적으로 접으므로 4700행 x 1201화소도 즉시다.
        """
        p = dict(params)
        i = self._index(start, 'simulate')
        t = 0
        seen = 0
        marks: list[tuple[str, int, int]] = []
        steps = 0
        while i < len(self.stmts):
            st = self.stmts[i]
            if isinstance(st, str):
                if st == start and seen >= frames:
                    break
                i += 1
                continue
            steps += 1
            if steps > max_stmts:
                raise TimingError('simulate: %d 줄을 넘겨도 %s 를 %d번 못 지났다 -- '
                                  '파라미터가 유휴 루프에 갇혔나' % (max_stmts, FRAME_STATE, frames))
            marks.append((st.state, t, st.no))
            if st.state == FRAME_STATE:
                seen += 1
            t += 1
            where = 'LINE%d' % st.no
            if st.kind == 'hold':
                t += self._value(st.b, p, where)
            elif st.kind == 'call':
                reps = self._value(st.b, p, where)
                dt, decs = self._call(st.a, reps, p)
                t += dt
                for k, v in decs.items():             # 몸통의 `p--` (0 아래로는 안 간다, p.64)
                    p[k] = max(0, p.get(k, 0) - v)
            elif st.kind == 'dec':
                p[st.a] = max(0, p.get(st.a, 0) - 1)
            elif st.kind == 'inc':
                p[st.a] = p.get(st.a, 0) + 1
            elif st.kind == 'goto':
                i = self._index(st.a, where)
                continue
            elif st.kind == 'if':
                if self._value(st.a, p, where):
                    i = self._index(st.b, where)
                    continue
            elif st.kind == 'return':
                raise TimingError('%s: 최상위에서 RETURN 을 만났다' % where)
            i += 1
        return marks

    def frame_period_ticks(self, params: dict[str, int], **overrides: int) -> int:
        """`FCLK` 개시 사이의 틱 -- 프레임 주기.  `overrides` 로 파라미터를 덮어쓴다
        (`IntMS=0, NoIntMS=0, Exposures=2` 처럼)."""
        p = dict(params)
        p.update(overrides)
        marks = self.simulate(p, frames=2)
        fclk = [t for (s, t, _no) in marks if s == FRAME_STATE]
        if len(fclk) < 2:
            raise TimingError('%s 를 두 번 지나지 못했다 (%d번)' % (FRAME_STATE, len(fclk)))
        return fclk[1] - fclk[0]


def verify_tick_anchor(ts: TimingScript, params: dict[str, int]) -> bool:
    """`NoIntUnit` 한 회가 정확히 100,000틱(1 ms)인가 -- 셈법의 자체 검산."""
    try:
        return ts.body_ticks('NoIntUnit', params) == UNIT_TICKS
    except TimingError:
        return False


#: science 스크립트라야 셈하는 라벨·호출 -- 이것이 없으면 `frame_timing` 이 거절한다.
_REQUIRED = (('Continuous', 'Line'), ('Line', 'PixelFirst'), ('Line', 'VerticalShift'),
             ('Continuous', 'HorizontalSWShift'))


def script_matches(ts: TimingScript) -> list[str]:
    """science 형태인가 -- 어긋난 것 목록 (비면 맞다).  guide 는 `HorizontalSWShift` 가 없다."""
    bad: list[str] = []
    for label, sub in _REQUIRED:
        i = ts.labels.get(label)
        # ⚠️ 문구는 영문이다 -- guide `icg_archon/acftiming.py` 의 같은 목록과 같은 꼴이고,
        # `TimingError` 를 거쳐 기동의 영문 경고 줄(`backend._read_timing`)에 실린다.
        if i is None:
            bad.append('%s: label missing' % label)
            continue
        ok = False
        for st in ts.stmts[i + 1:]:
            if isinstance(st, str):
                break
            if st.kind == 'call' and st.a == sub:
                ok = True
                break
        if not ok:
            bad.append('%s: no CALL %s' % (label, sub))
    return bad


def frame_timing(config: dict, params: dict[str, int] | None = None) -> dict[str, float]:
    """science 프레임 한 장의 구간별 소요 [s] + 주기 바닥.

    Returns:
        `pixel`(화소 하나) · `line`(행 하나) · `readout`(`Lines` 행) · `sweep`
        (독출 앞 `HorizontalSWShift`+`CLAMP`) · `noint_acf`(ACF 의 `NoIntMS`, 호스트가
        덮어쓴다) · `floor`(`IntMS=0`·`NoIntMS=0`·flush 없음의 **프레임 주기**) ·
        `flush`(`FlushFrame` 한 회 = Prep+Flush) · `lines`·`pixels`(무엇을 셈했나).
        ⚠️ `floor` 는 `Exposures=n` 경로(`Start`->`Exposure`->`Continuous`)로 잰다 --
        continuous 경로도 같은 값이다 (flush 호출 줄이 없을 뿐, 1틱 차이).
    """
    ts = TimingScript.from_config(config)
    p = dict(params if params is not None else parameters(config))
    bad = script_matches(ts)
    if bad:
        raise TimingError('science 형태가 아니다 -- ' + '; '.join(bad))
    if not verify_tick_anchor(ts, p):
        raise TimingError('NoIntUnit 이 1 ms 가 아니다 -- 틱 셈법을 신뢰하지 않는다')
    for k in ('Lines', 'Pixels'):
        if k not in p:
            raise TimingError('파라미터 %s 가 없다' % k)
    base = dict(p, IntMS=0, NoIntMS=0, FirstFlush=0, EveryFlush=0,
                ContinuousExposures=0, Exposures=2)
    line = ts.body_ticks('Line', base)
    t = {
        'pixel': ts.reentry_ticks('PixelFirst', base) * TICK,
        'line': line * TICK,
        'readout': line * int(p['Lines']) * TICK,
        'sweep': _sweep_ticks(ts, base) * TICK,
        'noint_acf': int(p.get('NoIntMS', 0)) * UNIT_TICKS * TICK,
        'floor': ts.frame_period_ticks(base) * TICK,
        'lines': float(p['Lines']),
        'pixels': float(p['Pixels']),
    }
    try:
        t['flush'] = (ts.call_ticks('FlushFrame', 1, base) - 1) * TICK
    except TimingError:
        t['flush'] = None
    return t


def _sweep_ticks(ts: TimingScript, params: dict[str, int]) -> int:
    """`Continuous:` 블록에서 `NoIntUnit` 뒤 ~ `FCLK` 앞까지 (수평 쓸기 + clamp)."""
    i = ts.labels['Continuous']
    ticks = 0
    counting = False
    for st in ts.stmts[i + 1:]:
        if isinstance(st, str):
            continue
        if st.state == FRAME_STATE:
            break
        if counting:
            ticks += 1
            if st.kind == 'hold':
                ticks += ts._value(st.b, params, 'LINE%d' % st.no)
            elif st.kind == 'call':
                ticks += ts._call(st.a, ts._value(st.b, params, 'LINE%d' % st.no), params)[0]
        if st.kind == 'call' and st.a == 'NoIntUnit':
            counting = True
    return ticks


def describe(t: dict[str, float]) -> str:
    return ('Pixels %d x Lines %d -- 화소 %.2f us · 행 %.2f us · 독출 %.4f s · '
            '쓸기 %.2f ms -> 주기 바닥 %.4f s (flush %s)'
            % (t.get('pixels', 0), t.get('lines', 0), t['pixel'] * 1e6,
               t['line'] * 1e6, t['readout'], t['sweep'] * 1e3, t['floor'],
               ('%.3f s' % t['flush']) if t.get('flush') else '없음'))


#: 상수와 계산값의 허용 차 [s].  상수는 두 자리로 반올림한 값이라 몇 ms 는 뜻이 없다.
TOLERANCE = 0.05


def check_min_frame_period(t: dict[str, float], constant: float,
                           tol: float = TOLERANCE) -> tuple[str, str] | None:
    """계산 바닥과 `MIN_FRAME_PERIOD` 를 대사 -- 어긋나면 `(수준, 문구)`, 맞으면 `None`.

    ⛔ **바닥이 상수보다 짧은 쪽이 위험하다** -- `fetch_timeout < 상수` 를 통과한
    잠금이 실제 주기를 넘어 다음 장을 덮고(DevNote 10.6), `wrote_window` 셈의
    `need` 도 모자라게 나온다.  그쪽은 `error`, 반대(상수가 낡아 보수적)는 `warning`.
    """
    floor = t['floor']
    if floor < constant - tol:
        return ('error',
                'ACF 의 프레임 주기 바닥 %.4f s 가 MIN_FRAME_PERIOD %.2f 보다 짧다 -- '
                'fetch_timeout·wrote_window 검사가 헐겁다.  상수를 %.2f 로 내릴 것'
                % (floor, constant, floor))
    if floor > constant + tol:
        return ('warning',
                'ACF 의 프레임 주기 바닥 %.4f s 가 MIN_FRAME_PERIOD %.2f 보다 길다 -- '
                '상수가 낡았다(보수적이라 위험은 없다).  %.2f 로 올릴 것'
                % (floor, constant, floor))
    return None


def read_acf(path: str) -> dict:
    """ACF 파일 -> `parse_acf()` 와 같은 꼴의 설정 줄 표 (왕복 없음, 컨트롤러 객체 없음).

    못 읽으면 전부 `TimingError` 로 접는다 -- `configparser` 의 예외는 `ValueError` 가
    아니라서 그대로 두면 기동 셈이 호출자를 뚫고 나간다 (`[CONFIG]` 절이 없는 파일이
    실제로 그랬다 -- `tests/test_failures.py`).
    """
    import configparser
    import os
    if not os.path.isfile(path):
        raise TimingError('ACF 가 없다 -- %s' % path)
    cp = configparser.RawConfigParser(strict=False)
    try:
        cp.read(path)
        items = cp.items('CONFIG')
    except (configparser.Error, UnicodeDecodeError, ValueError) as exc:
        raise TimingError('ACF 를 읽을 수 없다 -- %s: %s'
                          % (type(exc).__name__, exc)) from None
    return {k.upper().replace('\\', '/'): v.replace('"', '')
            for k, v in items}


def _main(argv: list[str]) -> int:  # pragma: no cover -- 손 도구
    """`python -m ics_archon.archon.acftiming <acf>...` -- 판별 셈을 찍는다 (사다리 대조용)."""
    import configparser
    import os
    import sys
    if not argv:
        print('용법: python -m ics_archon.archon.acftiming acf/KMTC_SCI_101_STA0284_R2613_MK.acf ...')
        return 2
    rc = 0
    for path in argv:
        try:
            t = frame_timing(read_acf(path))
            print('%-40s %s' % (os.path.basename(path), describe(t)))
        except (TimingError, OSError, configparser.Error) as exc:
            print('%-40s ⛔ %s' % (os.path.basename(path), exc), file=sys.stderr)
            rc = 1
    return rc


if __name__ == '__main__':  # pragma: no cover
    import sys
    sys.exit(_main(sys.argv[1:]))

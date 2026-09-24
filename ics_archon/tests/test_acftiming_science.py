# -*- coding: utf-8 -*-
"""`ics_archon.archon.acftiming` -- science 타이밍 스크립트 해석기.

셋을 못박는다:

1. **셈법** -- 합성 스크립트로 `CALL Sub(k)` 재진입(첫 회 `Sub:`, 둘째부터 `RETURN` 라벨) ·
   `k=0` 이면 1틱 · `X(파라미터)` · `IF`/`GOTO` · `p--` 의 0 바닥 (DevNote 11.85-(10) ·
   11.86-(12) · 매뉴얼 p.52·p.64).
2. **R2613 의 수** -- 화소 200틱 · 행 271,814틱 · 독출 12.7753 s (DevNote 11.85-(10) 표와
   같아야 한다) · flush 5.54 s (ini 주석) · 바닥이 `MIN_FRAME_PERIOD` 12.78 안에 든다.
   사다리 T2 -> 12.82 · T3 -> 13.06 (11.85-(7)).
3. **독립 셈법과의 교차 검증** -- 같은 해석기로 guide ACF 를 돌리면
   `icg_archon.acftiming.frame_timing()['floor']` 와 20틱 안에서 같다.  guide 모듈은
   서브루틴 틱을 손으로 옮긴 상수이고 이쪽은 스크립트 해석이라 **서로 독립**이다.
"""
from __future__ import annotations

import glob
import logging
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ics_archon import config as acfg_mod                         # noqa: E402
from ics_archon.archon import acftiming as sci                    # noqa: E402
from ics_archon.archon.controller import ArchonController         # noqa: E402
from icg_archon import acftiming as gui                           # noqa: E402

ACF_MK = os.path.join(ROOT, 'acf', 'KMTC_SCI_101_STA0284_R2613_MK.acf')
GUIDE = os.path.join(ROOT, 'acf', 'KMTK_GUI_162_STA0201_R2622.acf')
BENCH = os.path.join(ROOT, 'acf', 'bench')


def _science_acfs() -> list[str]:
    return sorted(glob.glob(os.path.join(ROOT, 'acf', 'KMT?_SCI_*.acf')))


# ---------------------------------------------------------------------------
# 1. 셈법 -- 합성 스크립트
# ---------------------------------------------------------------------------

_SYNTH = """
Start:
RESET; IF Exposures GOTO Exposure
X; GOTO Start

Exposure:
X; Exposures--
X; CALL Flushy(Flushes)
FCLK; CALL Line(Lines)
X; GOTO Start

Line:
X; CALL VS(Bin)
RGHIGH; CALL PixelFirst(Pixels)
CLAMP; X(Hold)
NOCLAMP; RETURN Line

VS:
IMAGE1; X(AT)
X; RETURN VS

Pixel:
RGHIGH
PixelFirst:
RGHIGH; X(19)
S1LOW; X(177)
RGHIGH; RETURN Pixel

Flushy:
X; Flushes--
X; RETURN Flushy
"""


def _ts() -> sci.TimingScript:
    return sci.TimingScript.from_text(_SYNTH)


def test_reentry_makes_every_pixel_200_ticks():
    """첫 회는 `PixelFirst:`(199), 둘째부터 `Pixel:` 재진입(+1) -- 호출 줄 1틱까지 셈하면
    화소 하나가 **늘 200틱**이다 (11.85-(10))."""
    ts = _ts()
    p = {'Pixels': 5}
    assert ts.body_ticks('PixelFirst', p) == 199
    assert ts.reentry_ticks('PixelFirst', p) == 200
    assert ts.call_ticks('PixelFirst', 'Pixels', p) == 1 + 199 + 4 * 200


def test_zero_reps_is_one_tick_and_no_body():
    ts = _ts()
    assert ts.call_ticks('PixelFirst', 0, {}) == 1
    assert ts.call_ticks('VS', 'Bin', {'Bin': 0, 'AT': 100}) == 1


def test_hold_reads_parameter_and_literal():
    ts = _ts()
    assert ts.body_ticks('VS', {'AT': 2000}) == (1 + 2000) + 1
    assert ts.body_ticks('VS', {'AT': 0}) == 2


def test_missing_parameter_is_an_error_not_a_default():
    ts = _ts()
    with pytest.raises(sci.TimingError):
        ts.body_ticks('VS', {})


def test_frame_period_follows_if_goto_and_decrements():
    """`Exposures=2` 로 두 프레임을 돌리면 `FCLK` 둘 사이가 한 프레임이고, 그 뒤 `Start` 로
    돌아와 멈춘다.  `Flushes=1` 이면 첫 프레임 앞에서만 flush 가 돈다 (몸통의 `--` 가 사본을
    깎는다) -- 그래서 주기에는 안 든다."""
    ts = _ts()
    p = {'Exposures': 2, 'Flushes': 1, 'Lines': 3, 'Bin': 1, 'AT': 10, 'Pixels': 2,
         'Hold': 5}
    marks = ts.simulate(p, frames=2)
    fclk = [t for s, t, _ in marks if s == 'FCLK']
    assert len(fclk) == 2
    line = (1 + (1 + 10) + 1) + (1 + 199 + 200) + (1 + 5) + 1
    # FCLK 줄 1 + Line x3 + GOTO 1 + Start(IF 1) + Exposure(-- 1, CALL Flushy 1 [k=0])
    assert fclk[1] - fclk[0] == 1 + 3 * line + 1 + 1 + 1 + 1
    assert ts.frame_period_ticks(p) == fclk[1] - fclk[0]


def test_decrement_does_not_go_below_zero():
    """매뉴얼 p.64 -- 0 에서 더 깎아도 아무 일 없다.  `Flushes=0` 인데 `Flushy` 를 1회 강제로
    부르면 몸통의 `--` 가 돌아도 값은 0 에 머문다."""
    ts = _ts()
    p = {'Exposures': 1, 'Flushes': 0, 'Lines': 1, 'Bin': 1, 'AT': 1, 'Pixels': 1,
         'Hold': 1}
    ts.simulate(p, frames=1)          # 예외 없이 끝난다
    dt, decs = ts._call('Flushy', 1, p)
    assert dt == 2 and decs == {'Flushes': 1}


def test_goto_inside_a_subroutine_is_rejected():
    ts = sci.TimingScript.from_text("Sub:\nX; GOTO Sub\nX; RETURN Sub\n")
    with pytest.raises(sci.TimingError):
        ts.body_ticks('Sub', {})


def test_unknown_instruction_is_rejected_at_parse():
    with pytest.raises(sci.TimingError):
        sci.TimingScript.from_text("Start:\nX; FROB 3\n")


def test_stuck_idle_loop_is_reported():
    ts = _ts()
    with pytest.raises(sci.TimingError):
        ts.simulate({'Exposures': 0}, frames=1, max_stmts=50)


# ---------------------------------------------------------------------------
# 2. R2613 의 수
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def r2613():
    cfg = sci.read_acf(ACF_MK)
    return cfg, sci.parameters(cfg), sci.frame_timing(cfg)


def test_read_acf_matches_parse_acf(r2613):
    """`read_acf()` 는 `ArchonController.parse_acf()` 와 같은 표를 내야 한다 -- 기동 셈과
    `prepare()` 가 다른 파일을 읽는 일이 없게."""
    cfg, _p, _t = r2613
    ctrl = ArchonController('MK', acfg_mod.ArchonCfg(), log_tag=False)
    ctrl.parse_acf(ACF_MK)
    assert ctrl.config == cfg


def test_tick_anchor_holds_on_the_real_script(r2613):
    cfg, p, _t = r2613
    ts = sci.TimingScript.from_config(cfg)
    assert sci.verify_tick_anchor(ts, p)
    assert ts.body_ticks('IntUnit', p) == sci.UNIT_TICKS


def test_r2613_numbers_match_devnote(r2613):
    """DevNote 11.85-(10) 표: 화소 200틱 · 행 271,814틱 · 독출 12.7753 s.  독출은 `Lines x 행`
    이고 주기 바닥은 그 위에 쓸기(`HorizontalSWShift(1200)`+`CLAMP`) ≈0.93 ms 가 얹힌다."""
    _cfg, _p, t = r2613
    assert round(t['pixel'] / sci.TICK) == 200
    assert round(t['line'] / sci.TICK) == 271_814
    assert round(t['readout'], 4) == 12.7753
    assert round(t['sweep'] * 1e3, 2) == 0.93
    assert 12.776 < t['floor'] < 12.777
    assert t['floor'] > t['readout']


def test_r2613_flush_matches_the_ini_comment(r2613):
    """`ics_archon.ini` 주석: 켜면 프레임 주기가 **+5.54 s** (Prep 0.200 + Flush 5.332 +
    FlushPostMS 0.010)."""
    _cfg, _p, t = r2613
    assert round(t['flush'], 2) == 5.54


def test_every_flush_adds_the_flush_to_the_period(r2613):
    cfg, p, t = r2613
    ts = sci.TimingScript.from_config(cfg)
    base = dict(p, IntMS=0, NoIntMS=0, FirstFlush=0, ContinuousExposures=0, Exposures=2)
    with_flush = ts.frame_period_ticks(base, EveryFlush=1) * sci.TICK
    assert abs(with_flush - (t['floor'] + t['flush'])) < 1e-6
    # `FirstFlush=1` 은 첫 장 앞에서만 -- 둘째 프레임 주기에는 안 든다
    assert abs(ts.frame_period_ticks(base, FirstFlush=1) * sci.TICK - t['floor']) < 1e-6


def test_min_frame_period_constant_agrees_with_every_science_acf():
    """여덟 장 전부 같은 바닥이고 `MIN_FRAME_PERIOD` 와 허용 차 안이다 -- ACF 판을 올리면
    여기가 먼저 갈린다 (그때 상수를 고친다, `config.py`)."""
    floors = set()
    for path in _science_acfs():
        t = sci.frame_timing(sci.read_acf(path))
        assert sci.check_min_frame_period(t, acfg_mod.MIN_FRAME_PERIOD) is None, \
            (os.path.basename(path), t['floor'])
        floors.add(round(t['floor'], 6))
    assert len(floors) == 1, floors


def test_check_min_frame_period_directions():
    t = {'floor': 12.7762}
    assert sci.check_min_frame_period(t, 12.78) is None
    level, msg = sci.check_min_frame_period(t, 13.06)     # 상수가 바닥보다 길다 -- 위험
    assert level == 'error' and '12.78' in msg
    level, msg = sci.check_min_frame_period(t, 12.50)     # 상수가 낡아 보수적
    assert level == 'warning' and '12.78' in msg


@pytest.mark.parametrize('tail, expect', [('T0', 12.78), ('T1', 12.78),
                                          ('T2', 12.82), ('T3', 13.06), ('T4', 12.78)])
def test_bench_ladder_floors(tail, expect):
    """DevNote 11.85-(7): T2 채택시 12.82 · T3 채택시 13.06.  T1 은 파형만 바뀌어 ±0,
    T4 는 T3 의 정착 +6000 을 클램프 -6000 이 상쇄해 T0 과 같다 (`acf/bench/README.md`)."""
    path = os.path.join(BENCH, 'KMTC_SCI_101_STA0284_R2612_MK_%s.acf' % tail)
    if not os.path.exists(path):
        pytest.skip('사다리 파일이 없다: %s' % path)
    t = sci.frame_timing(sci.read_acf(path))
    assert round(t['floor'], 2) == expect


# ---------------------------------------------------------------------------
# 3. guide 모듈과의 교차 검증
# ---------------------------------------------------------------------------

def test_interpreter_reproduces_guide_module_floor():
    """독립 셈법 둘이 같은 답 -- guide ACF 를 이 해석기로 돌린 `FCLK` 주기가
    `icg_archon.acftiming.frame_timing()['floor']` 와 20틱(200 ns) 안이다.  guide 모듈은
    `Start:` 루프·`IntUnit(0)` 호출 줄 몇 틱을 안 세므로 정확히 같지는 않다."""
    cfg = sci.read_acf(GUIDE)
    p = sci.parameters(cfg)
    ts = sci.TimingScript.from_config(cfg)
    assert sci.verify_tick_anchor(ts, p)
    sim = ts.frame_period_ticks(dict(p, IntMS=0, NoIntMS=0, ContinuousExposures=0,
                                     Exposures=2))
    g = gui.frame_timing(p, lines=p['Lines'], pixels=p['Pixels'], config=cfg)
    assert 0 <= sim - round(g['floor'] / sci.TICK) <= 20
    assert round(g['floor'], 4) == 1.2506


def test_frame_timing_refuses_guide_shape():
    with pytest.raises(sci.TimingError):
        sci.frame_timing(sci.read_acf(GUIDE))


# ---------------------------------------------------------------------------
# 4. 백엔드 기동 검사
# ---------------------------------------------------------------------------

def _backend(acf: dict):  # noqa: ANN001
    from ics_sim import config as simcfg
    from ics_archon.archon.backend import ArchonBackend
    acfg = acfg_mod.ArchonCfg()
    acfg.hosts = {'MK': '127.0.0.1', 'NT': '127.0.0.1'}
    acfg.acf = acf
    return ArchonBackend(simcfg.SimConfig(), acfg)


def test_backend_reads_timing_at_startup_and_is_quiet_when_consistent(caplog):
    caplog.set_level(logging.INFO, logger='ics_archon.hw')
    nt = os.path.join(ROOT, 'acf', 'KMTC_SCI_102_STA0285_R2613_NT.acf')
    b = _backend({'MK': ACF_MK, 'NT': nt})
    assert set(b.timing) == {'MK', 'NT'}
    assert round(b.timing['MK']['floor'], 4) == round(b.timing['NT']['floor'], 4)
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_backend_flags_a_stale_constant_and_disagreeing_controllers(caplog):
    caplog.set_level(logging.INFO, logger='ics_archon.hw')
    t3 = os.path.join(BENCH, 'KMTC_SCI_102_STA0285_R2612_NT_T3.acf')
    if not os.path.exists(t3):
        pytest.skip('사다리 파일이 없다')
    _backend({'MK': ACF_MK, 'NT': t3})
    msgs = [(r.levelname, r.getMessage()) for r in caplog.records]
    assert any(lv == 'WARNING' and 'stale' in m for lv, m in msgs), msgs
    assert any(lv == 'ERROR' and 'disagree' in m for lv, m in msgs), msgs


def test_backend_only_warns_on_an_unreadable_acf(tmp_path, caplog):  # noqa: ANN001
    """`[CONFIG]` 절이 없는 파일 -- 기동 셈은 경고 한 줄로 물러나고 백엔드는 선다
    (`prepare()` 가 그 파일을 제대로 거절한다, `test_failures.py`)."""
    caplog.set_level(logging.INFO, logger='ics_archon.hw')
    bad = tmp_path / 'bad.acf'
    bad.write_text('[SOMETHINGELSE]\nx=1\n', encoding='ascii')
    b = _backend({'MK': str(bad)})
    assert b.timing == {}
    assert any(r.levelno == logging.WARNING and 'not computed' in r.getMessage()
               for r in caplog.records)


def test_backend_skips_quietly_without_an_acf(caplog):
    caplog.set_level(logging.INFO, logger='ics_archon.hw')
    b = _backend({})
    assert b.timing == {}
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]

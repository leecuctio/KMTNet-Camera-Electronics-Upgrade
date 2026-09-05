"""diagnostics.py + ptc.py 확장 검증 (pytest 불필요 — 단독 assert 스크립트).

testkit으로 bias 20장 + 6레벨 flat pair 세트를 생성(주입 gain 1.46,
curvature 0)하고, overscan 영역에만 신호 비례 누화(레벨 x 2e-4)를 adc_map
후처리로 주입한 뒤:
  - PTC gain 정량 회수 (±4%)
  - overscan-slope(CMRR 지표) 검출 (> 1e-4) + OSCAN_SLOPE 플래그
  - CSV 스키마(앰프별 요약 + pair별 ptc_points)
  - PNG 산출(존재 + >10KB)
  - ptc_points 하위호환 (기본 인자 유지, ovsc=None이면 oscan 키 없음)
  - fit_gain 반환 dict 불변
  - CLI(--roi-test) 경로
를 확인한다.
"""
from __future__ import annotations

import csv
import inspect
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kmt_cam_char import core                                   # noqa: E402
from kmt_cam_char import ptc                                    # noqa: E402
from kmt_cam_char.diagnostics import run_diagnostics            # noqa: E402
from kmt_cam_char.testkit import DATA_COLS, OVSC_COLS, SynthL0  # noqa: E402

GAIN_TRUE = 1.46
RN_TRUE_ADU = 3.5
XTALK = 2e-4                    # overscan으로 새는 신호 비례 누화
# 최대 레벨: roi_raw는 헤더 BZERO 적용 물리 unsigned ADU(0..65535)를
# 반환하므로 32768 랩 제약은 없다 — PTC 적합 범위가 SAT_GUARD(raw p99.9
# 60000 ADU) 아래에 머물도록만 레벨을 잡는다.
LEVELS = [500.0, 2000.0, 5000.0, 10000.0, 16000.0, 24000.0]


def make_ovsc_leak(level_adu: float):
    """생성 시 overscan 컬럼에만 level x XTALK [ADU]를 더하는 adc_map."""
    def f(code):
        c = code.astype(np.float64)
        c[:, DATA_COLS:DATA_COLS + OVSC_COLS] += level_adu * XTALK
        return np.rint(c)
    return f


def main() -> None:
    # 수치 경로는 matplotlib 없이 임포트 가능해야 한다
    assert "matplotlib.pyplot" not in sys.modules, \
        "diagnostics import pulled in matplotlib"

    tmp = Path(tempfile.mkdtemp(prefix="test_diagnostics_"))
    frames = tmp / "frames"
    kit = SynthL0(frames, seed=7, gain=GAIN_TRUE, rdnoise_adu=RN_TRUE_ADU)

    bias = kit.bias_set(20)
    flats, k = [], 0
    for lv in LEVELS:
        for _ in range(2):
            flats.append(kit.frame("f%04d" % k, lv, exptime=lv / 2000.0,
                                   adc_map=make_ovsc_leak(lv)))
            k += 1

    # -- ptc_points 하위호환 --------------------------------------------------
    sig = inspect.signature(ptc.ptc_points)
    params = list(sig.parameters)
    assert params[:4] == ["flat_pairs", "ext", "bias_adu", "rn_adu"], params
    assert sig.parameters["roi"].default is core.ROI
    assert sig.parameters["ovsc"].default is None

    ext0 = kit.extnames[0]
    with core.open_l0(bias[0]) as eb:
        # roi_raw 규약의 raw ADU 공간에서 측정한 bias/overscan 기준값
        bias_meas = float(np.median(core.roi_raw(eb, ext0, roi=kit.roi)))
        oscan_bias_meas = float(np.median(
            ptc.ovsc_section(eb, ext0, kit.roi[0], kit.ovsc)))
    with core.open_l0(flats[0]) as e1, core.open_l0(flats[1]) as e2:
        pts0 = ptc.ptc_points([(e1, e2)], ext0, bias_meas,
                              RN_TRUE_ADU, roi=kit.roi)   # ovsc 미지정
        assert len(pts0) == 1
        assert set(pts0[0]) == {"S", "V", "r", "exptime", "p999_raw"}, \
            "ovsc=None인데 점 dict 키가 달라짐 (하위호환 위반): %s" % pts0[0]
        assert abs(pts0[0]["S"] - LEVELS[0]) < 30.0, pts0[0]
        pts1 = ptc.ptc_points([(e1, e2)], ext0, bias_meas,
                              RN_TRUE_ADU, roi=kit.roi, ovsc=kit.ovsc)
        assert {"oscan1", "oscan2"} <= set(pts1[0])
        # overscan 중앙값은 bias overscan 부근 (레벨 500 누화 ~0.1 ADU)
        assert abs(pts1[0]["oscan1"] - oscan_bias_meas) < 5.0, pts1[0]

    # fit_gain 반환 dict 불변 (runner.py 계약)
    fk = set(ptc.fit_gain([]).keys())
    assert fk == {"gain", "gain_err", "curv_a", "n_pts", "n_rej", "status"}, fk

    # measure_bias: 쌍차분이 정의되지 않는 1장 입력은 명시적으로 거부
    # (조용한 rn=0/bias=0 반환이 하류 gain을 오염시키는 결함의 회귀 방지)
    from kmt_cam_char.diagnostics import measure_bias
    try:
        measure_bias(bias[:1], roi=kit.roi, ovsc=kit.ovsc)
    except ValueError as e:
        assert "need >= 2" in str(e), e
    else:
        raise AssertionError("measure_bias accepted a single bias frame")

    # -- 본 진단 실행 ----------------------------------------------------------
    outdir = tmp / "out"
    res = run_diagnostics(bias, flats, outdir, "TESTCAMP",
                          roi=kit.roi, ovsc=kit.ovsc)
    recs = res["records"]
    assert len(recs) == kit.namps, len(recs)
    ok_keys = {"gain", "gain_err", "curv_a", "n_pts", "n_rej",
               "resid_rms_pct", "status"}
    for r in recs:
        # 정량 회수: gain 1.46 ± 4%
        assert abs(r["gain"] - GAIN_TRUE) / GAIN_TRUE < 0.04, \
            "%s gain %.4f" % (r["extname"], r["gain"])
        # curvature 0 주입 -> 최대 신호에서 곡률 항 기여가 잡음 수준(<4%)
        assert abs(r["curvature"]) * max(LEVELS) * GAIN_TRUE < 0.04, \
            "%s curvature %.3e" % (r["extname"], r["curvature"])
        # overscan 절편은 bias overscan 레벨과 일치해야 한다
        assert abs(r["oscan_intercept"] - r["oscan_bias_adu"]) < 2.0, \
            (r["oscan_intercept"], r["oscan_bias_adu"])
        # read noise 회수
        assert abs(r["rn_adu"] - RN_TRUE_ADU) < 0.5, r["rn_adu"]
        assert abs(r["rn_e"] - RN_TRUE_ADU * GAIN_TRUE) < 1.0, r["rn_e"]
        # overscan 누화 기울기 검출 (주입 2e-4, 판정 한계 1e-4)
        assert np.isfinite(r["oscan_slope"]), r["extname"]
        assert r["oscan_slope"] > 1e-4, \
            "%s oscan_slope %.3e" % (r["extname"], r["oscan_slope"])
        assert r["oscan_slope"] < 4e-4, r["oscan_slope"]
        assert "OSCAN_SLOPE" in r["flags"], r["flags"]
        assert r["n_pairs"] == len(LEVELS), r["n_pairs"]
        assert r["fit_status"] == "OK", r["fit_status"]

    # -- CSV 스키마 ------------------------------------------------------------
    base = outdir / "diagnostics"
    csv_path = base / "diagnostics_TESTCAMP.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == kit.namps, len(rows)
    assert list(rows[0]) == ["extname", "ampid", "gain", "gain_err",
                             "curvature", "rn_adu", "rn_e", "bias_adu",
                             "oscan_slope", "n_pairs", "flags",
                             "campaign", "date", "config"], list(rows[0])
    for row in rows:
        assert abs(float(row["gain"]) - GAIN_TRUE) / GAIN_TRUE < 0.04
        assert float(row["oscan_slope"]) > 1e-4
        assert int(row["n_pairs"]) == len(LEVELS)
        assert "OSCAN_SLOPE" in row["flags"]
        assert row["campaign"] == "TESTCAMP", row["campaign"]
        assert row["date"] == "2026-09-04", row["date"]   # testkit DATE-OBS

    for ext in kit.extnames:
        pp = base / "ptc_points" / ("%s_ptc.csv" % ext)
        with pp.open(newline="", encoding="utf-8") as fh:
            prows = list(csv.DictReader(fh))
        assert list(prows[0]) == ["S", "V", "r", "oscan1", "oscan2",
                                  "exptime", "p999_raw"], list(prows[0])
        assert len(prows) == len(LEVELS), len(prows)
        for prow in prows:
            s, v = float(prow["S"]), float(prow["V"])
            assert abs(s / v - GAIN_TRUE) / GAIN_TRUE < 0.1, (s, v)
            assert float(prow["oscan1"]) > 0

    # -- PNG 산출 ---------------------------------------------------------------
    summ = base / "diagnostics_summary.png"
    assert summ.exists() and summ.stat().st_size > 10240, summ
    for ext in kit.extnames:
        p = base / "amps" / ("%s_diagnostics.png" % ext)
        assert p.exists() and p.stat().st_size > 10240, p

    # -- CLI (--roi-test) --------------------------------------------------------
    diag_py = Path(__file__).resolve().parents[1] / "diagnostics.py"
    cli_out = tmp / "out_cli"
    r = subprocess.run(
        [sys.executable, str(diag_py),
         "--bias", str(frames / "b*.fits"),
         "--flats", str(frames / "f*.fits"),
         "-o", str(cli_out), "--campaign", "CLICAMP", "--roi-test"],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    cli_csv = cli_out / "diagnostics" / "diagnostics_CLICAMP.csv"
    assert cli_csv.exists(), r.stdout + r.stderr
    with cli_csv.open(newline="", encoding="utf-8") as fh:
        crows = list(csv.DictReader(fh))
    assert len(crows) == kit.namps
    assert abs(float(crows[0]["gain"]) - GAIN_TRUE) / GAIN_TRUE < 0.04

    print("OK test_diagnostics (gain med %.4f, oscan_slope med %.2e)"
          % (float(np.median([r_["gain"] for r_ in recs])),
             float(np.median([r_["oscan_slope"] for r_ in recs]))))


if __name__ == "__main__":
    main()

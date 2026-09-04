"""linearity 확장(fit_ramp/build_points/dynamic_range/run_linearity) 검증.

testkit 합성 노출 램프에 비선형 S*(1-2e-7*S)와 램프 밝기 사인 드리프트
(0.5% 곱)를 주입하고, 기준노출(ref) 프레임으로 정규화했을 때
  - LINMAX(0.5%)가 주입 모델의 0.5% 이탈점(측정 도메인 24875 ADU) ±15%로
    회수되고,
  - linearizer 적용 후 잔차가 0.15% 미만이며,
  - ref 정규화를 켰을 때가 껐을 때보다 잔차가 개선됨
을 정량 확인한다. 산출 PNG/CSV는 존재와 크기(>10KB)만 확인한다.

단독 실행: /opt/miniconda3/bin/python test_linearity_ext.py  ("OK ..." 출력)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kmt_cam_char import linearity                      # noqa: E402
from kmt_cam_char.testkit import SynthL0                # noqa: E402

NONLIN_C = 2e-7
NONLIN = lambda s: s * (1.0 - NONLIN_C * s)             # noqa: E731
RATE = 2000.0           # ADU/s
REF_LEVEL = 20000.0     # 기준노출 신호 [ADU] (밝을수록 중앙값 잡음 유리)
# core.roi_raw는 헤더 BZERO 적용 물리 unsigned ADU(0..65535)라 32768 랩
# 제약은 없다. 램프는 주입 비선형의 0.5% 이탈점(~25000 ADU) 회수가 목적
# 이므로 신호 ~30000 ADU까지만 올린다 (raw p99.9 ~ 31500, 포화와 무관 —
# sat guard 65000은 전체 물리 코드축을 열어 두는 완화값).
LEVELS = [2000, 4500, 7000, 9500, 12000, 14500, 17000, 19500,
          22000, 24500, 26500, 28500, 30000]
SAT_GUARD = 65000.0
# 프레임 기하: 중앙값의 통계잡음+반정수 양자화가 LINMAX 회수 정밀도의
# 바닥이므로 ROI 픽셀 수를 기본(280x180)보다 키운다 (600x380).
NY, DATA_COLS = 640, 400
# 주입 모델의 |NL|=0.5% 이탈점: S_true=25000 -> 측정 도메인 24875 ADU
EXPECT_LINMAX05 = 25000.0 * (1.0 - NONLIN_C * 25000.0)


def make_ramp(kit):
    """flat_pairs로 노출 램프 + 스텝별 사인 드리프트 + 동시각 ref 프레임."""
    flat_paths, ref_paths = [], []
    for k, lv in enumerate(LEVELS):
        drift = 1.0 + 0.005 * np.sin(2.0 * np.pi * k / 5.0)
        scale = np.full(kit.namps, drift)
        (_, ps), = kit.flat_pairs([lv], per_level=1, rate_adu_s=RATE,
                                  prefix="f%02d_" % k, nonlin=NONLIN,
                                  level_scale=scale)
        flat_paths += ps
        ref_paths.append(kit.frame("r%04d" % k, REF_LEVEL,
                                   exptime=REF_LEVEL / RATE, nonlin=NONLIN,
                                   level_scale=scale))
    return flat_paths, ref_paths


def main():
    tmp = Path(tempfile.mkdtemp(prefix="test_linext_"))
    kit = SynthL0(tmp / "frames", seed=7, ny=NY, data_cols=DATA_COLS)
    flat_paths, ref_paths = make_ramp(kit)
    bias_paths = kit.bias_set(3)

    # -- build_points + fit_ramp: 정량 회수 (앰프 2개 표본) -----------------
    for ext in (kit.extnames[0], kit.extnames[-1]):
        pts = linearity.build_points(flat_paths, ext, roi=kit.roi,
                                     ovsc=kit.ovsc, ref_paths=ref_paths)
        assert len(pts) == len(LEVELS), len(pts)
        assert all(p["ref_S"] is not None for p in pts)
        res = linearity.fit_ramp(pts, sat_guard_adu=SAT_GUARD)
        assert res["status"] == "OK", res
        assert res["n_points"] == len(LEVELS), res["n_points"]
        assert res["ref_norm"] is True
        # 주입 드리프트 ptp = 1% 부근 (0.5% 사인 진폭)
        assert 0.4 < res["ref_drift_pct"] < 1.6, res["ref_drift_pct"]
        # rate ~ 2000 ADU/s, dt ~ 0 (합성엔 셔터 오프셋 없음)
        assert abs(res["rate_adu_s"] - RATE) / RATE < 0.02, res["rate_adu_s"]
        assert abs(res["dt_s"]) < 0.2, res["dt_s"]
        # LINMAX(0.5%) 회수: 주입 모델 이탈점 +-15%
        lm05 = res["linmax_05_adu"]
        assert abs(lm05 - EXPECT_LINMAX05) / EXPECT_LINMAX05 < 0.15, \
            (ext, lm05, EXPECT_LINMAX05)
        # 1% 이탈점(49500)은 램프 밖 -> ramp-limited로 S_max에 걸려야 한다
        assert res["linmax_10_adu"] >= lm05
        assert res["linmax_10_note"] == "ramp-limited", res["linmax_10_note"]
        # 보정 후 잔차 < 0.15%
        assert res["max_resid_pct_after"] < 0.15, res["max_resid_pct_after"]

        # ref 정규화 off: 드리프트가 잔차로 남아 성능이 나빠져야 한다
        pts_noref = [dict(p, ref_S=None) for p in pts]
        res_off = linearity.fit_ramp(pts_noref, sat_guard_adu=SAT_GUARD)
        assert res_off["status"] == "OK" and res_off["ref_norm"] is False
        assert res["max_resid_pct_after"] < res_off["max_resid_pct_after"], \
            (res["max_resid_pct_after"], res_off["max_resid_pct_after"])

    # -- dynamic_range 유틸 -------------------------------------------------
    d = linearity.dynamic_range(1000.0, 2.0, 5.0)
    assert abs(d["dr"] - 400.0) < 1e-9 and abs(d["dr_bit"]
                                               - np.log2(400.0)) < 1e-9
    assert linearity.dynamic_range(0.0, 2.0, 5.0) == {"dr": 0.0, "dr_bit": 0.0}

    # -- fit_ramp 경계: 점 부족 --------------------------------------------
    few = [{"t": 1.0, "S": 100.0, "ref_S": None}] * 3
    assert linearity.fit_ramp(few)["status"] == "TOO_FEW_POINTS"

    # -- run_linearity: CSV/PNG 산출물 --------------------------------------
    outdir = tmp / "out"
    run = linearity.run_linearity(flat_paths, outdir, "TESTCAMP",
                                  ref_paths=ref_paths, bias_paths=bias_paths,
                                  roi=kit.roi, ovsc=kit.ovsc,
                                  sat_guard_adu=SAT_GUARD)
    assert len(run["rows"]) == kit.namps
    assert all(str(r["STATUS"]).startswith("OK") for r in run["rows"])
    csv_path = Path(run["csv"])
    assert csv_path.name == "linearity_coeff_TESTCAMP.csv"
    lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].startswith("#")                     # 도메인 주석 헤더
    header = lines[1].split(",")
    for col in ("EXTNAME", "AMPID", "MODEL", "C0", "C1", "C2", "C3",
                "VALID_MIN", "VALID_MAX", "MAX_RESID_PCT_AFTER",
                "NL_RMS_PCT", "IMG_MINUS_OVSC_ADU",
                "CAMPAIGN", "DATE", "CONFIG"):
        assert col in header, col
    assert len(lines) == 2 + kit.namps
    # 계수/범위의 물리성: C0 = 1 고정(원점 제약), LINMAX05(raw)-bias ~ 주입
    # 이탈점, VALID_MAX = LINMAX(1%) raw
    row0 = dict(zip(header, lines[2].split(",")))
    assert row0["MODEL"] == "poly3"
    assert float(row0["C0"]) == 1.0, row0["C0"]
    lm05_sub = float(row0["LINMAX05_RAW"]) - float(row0["BIAS_ADU"])
    assert abs(lm05_sub - EXPECT_LINMAX05) / EXPECT_LINMAX05 < 0.15, lm05_sub
    assert float(row0["VALID_MAX"]) == float(row0["LINMAX10_RAW"])
    assert float(row0["MAX_RESID_PCT_AFTER"]) < 0.15
    # 잔차 RMS (results/README.md §3 필수 필드): 0 < rms <= max|NL|
    assert 0.0 < float(row0["NL_RMS_PCT"]) <= float(row0["NL_MAX_PCT"])
    assert float(row0["DR_BIT"]) > 10.0                 # ~30k*1.46/5.1e- 급
    # 환산 페데스탈 = 실제 차감한 오버스캔 중앙값; --bias 세트의 이미지
    # 준위와의 차이는 IMG_MINUS_OVSC_ADU에 별도 기록 (합성: 오프셋 ~0)
    assert abs(float(row0["IMG_MINUS_OVSC_ADU"])) < 2.0, \
        row0["IMG_MINUS_OVSC_ADU"]

    # poly_deg=4: 계수가 C4까지 온전히 기록되어야 한다 (잘림 회귀 방지)
    run4 = linearity.run_linearity(flat_paths, tmp / "out4", "TESTP4",
                                   ref_paths=ref_paths, roi=kit.roi,
                                   ovsc=kit.ovsc, poly_deg=4,
                                   sat_guard_adu=SAT_GUARD)
    r4 = run4["rows"][0]
    assert r4["MODEL"] == "poly4" and "C4" in r4, sorted(r4)
    res4 = run4["results"][r4["EXTNAME"]]
    assert len(res4["lin_c"]) == 5
    assert float(r4["C4"]) == float("%.8e" % res4["lin_c"][4]), r4["C4"]

    summary = Path(run["summary_png"])
    assert summary.exists() and summary.stat().st_size > 10 * 1024
    for ext, png in run["amp_pngs"].items():
        p = Path(png)
        assert p.exists() and p.stat().st_size > 10 * 1024, (ext, png)

    # -- CLI (인자 파싱 + roi/ovsc 오버라이드) ------------------------------
    cli_out = tmp / "out_cli"
    roi_s = "%d:%d,%d:%d" % (kit.roi[0].start, kit.roi[0].stop,
                             kit.roi[1].start, kit.roi[1].stop)
    ovsc_s = "%d:%d" % (kit.ovsc.start, kit.ovsc.stop)
    ampchar_csv = tmp / "ampchar.csv"
    ampchar_csv.write_text(
        "EXTNAME,GAIN,RDNOISE\n%s,2.0,7.0\n" % kit.extnames[0],
        encoding="utf-8")
    rc = linearity.main([
        "--flats", str(kit.outdir / "f*.fits"),
        "--refs", str(kit.outdir / "r*.fits"),
        "--bias", str(kit.outdir / "b*.fits"),
        "-o", str(cli_out), "--campaign", "CLITEST",
        "--config", "archon-v9.9", "--ampchar", str(ampchar_csv),
        "--roi", roi_s, "--ovsc", ovsc_s, "--sat-guard", str(SAT_GUARD),
    ])
    assert rc == 0
    cli_csv = cli_out / "linearity" / "linearity_coeff_CLITEST.csv"
    assert cli_csv.exists()
    clines = cli_csv.read_text(encoding="utf-8").strip().splitlines()
    chdr = clines[1].split(",")
    crow0 = dict(zip(chdr, clines[2].split(",")))
    # --config가 CONFIG 컬럼을 채운다 (results/README.md §3 필수 필드)
    assert crow0["CONFIG"] == "archon-v9.9", crow0["CONFIG"]
    # --ampchar 주입: 헤더 placeholder(1.46/5.11e-) 대신 실측 2.0/7.0으로
    # DR_BIT가 달라져야 한다: log2(LINMAX*2.0/7.0)
    lm10 = float(crow0["LINMAX10_RAW"]) - float(crow0["BIAS_ADU"])
    expect_bit = np.log2(lm10 * 2.0 / 7.0)
    assert abs(float(crow0["DR_BIT"]) - expect_bit) < 0.02, \
        (crow0["DR_BIT"], expect_bit)

    # -- 하위호환: fit_linearity 기존 시그니처/반환 -------------------------
    levels = [{"exptime": p["t"], "S": p["S"], "p999_raw": p["p999_raw"]}
              for p in linearity.build_points(flat_paths, kit.extnames[0],
                                              roi=kit.roi, ovsc=kit.ovsc)]
    old = linearity.fit_linearity(levels, 1000.0)
    assert old["status"] == "OK" and "linmax_raw_adu" in old

    print("OK test_linearity_ext")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

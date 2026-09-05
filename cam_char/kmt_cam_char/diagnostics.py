"""Per-amplifier PTC diagnostic pages and a camera-level summary.

Makes the plan's §6.4 sanity checks visual per amp (five panels a page):
    1  PTC V vs S (log-log): used/excluded pairs + V = S/g - a S^2 fit,
       g and a annotated
    2  apparent gain S/V vs S (V is already RN-subtracted in ptc.ptc_points)
       against the fitted g with a ±2% band — signal dependence check
    3  overscan level vs flat signal with the fitted slope annotated —
       a nonzero slope means signal leaking into the overscan (common-mode /
       CMRR problem in the video chain)
    4  pair ratio (r - 1)% vs S with the ±1% lamp-drift guard band
    5  PTC fit residuals [%] vs S

Camera summary (one page): GAIN / RDNOISE / bias level / curvature a /
overscan slope vs AMPID, median dashed line, outliers (median absolute
deviation criterion) in red.

Read noise and bias level come from the --bias set with the self-contained
pair-MAD estimator below (readnoise.measure_readnoise is pinned to the
production ROI/overscan geometry and must stay untouched, so the roi/ovsc
parameterized variant lives here).

Outputs under OUTDIR/diagnostics/:
    diagnostics_summary.png              camera-axis summary
    amps/<EXTNAME>_diagnostics.png       per-amp page
    diagnostics_<CAMPAIGN>.csv           one row per amp
    ptc_points/<EXTNAME>_ptc.csv         one row per usable flat pair

CLI:
    python diagnostics.py --bias 'b*.fits' --flats 'f*.fits' \
        -o OUTDIR --campaign NAME [--roi-test]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kmt_cam_char import core                            # noqa: E402
from kmt_cam_char.ptc import (                           # noqa: E402
    DRIFT_MAX, S_MIN_ADU, SAT_GUARD_ADU, fit_gain, ovsc_section, ptc_points)

OSCAN_SLOPE_LIMIT = 1e-4    # |d(oscan)/dS| above this: common-mode flag
OUTLIER_NMAD = 5.0          # summary-plot outlier criterion [MAD-sigmas]

CSV_COLS = ["extname", "ampid", "gain", "gain_err", "curvature",
            "rn_adu", "rn_e", "bias_adu", "oscan_slope", "n_pairs", "flags",
            "campaign", "date", "config"]
PT_COLS = ["S", "V", "r", "oscan1", "oscan2", "exptime", "p999_raw"]


# -- 수치 계산 (numpy만) ----------------------------------------------------

def measure_bias(bias_files: list, roi=core.ROI, ovsc=core.OVSC_REAL,
                 extnames=None) -> dict:
    """bias 쌍차분 MAD read noise + bias/overscan level (roi/ovsc 가변).

    {ext: {'rn_adu', 'bias_adu', 'oscan_bias_adu'}}

    쌍차분 추정이 정의되려면 bias 프레임이 2장 이상이어야 한다 — 부족하면
    rn/bias 0.0을 조용히 돌려주는 대신 명시적으로 거부한다 (0.0이 하류
    ptc_points의 bias 차감에 섞이면 gain이 크게 틀린 채 OK로 나간다).
    """
    if len(bias_files) < 2:
        raise ValueError("measure_bias: need >= 2 bias frames "
                         "(pair-difference RN), got %d" % len(bias_files))
    exps = [core.open_l0(p) for p in bias_files]
    try:
        if extnames is None:
            extnames = list(exps[0].amp_names)
        out = {}
        for ext in extnames:
            rns, levels, olev = [], [], []
            for e1, e2 in core.pairs(exps):
                a1 = core.roi_raw(e1, ext, roi=roi)
                a2 = core.roi_raw(e2, ext, roi=roi)
                rns.append(core.mad_std(a1 - a2) / np.sqrt(2.0))
                levels += [float(np.median(a1)), float(np.median(a2))]
            if ovsc is not None:
                for e in exps:
                    o = ovsc_section(e, ext, roi[0], ovsc)
                    olev.append(float(np.median(o)))
            out[ext] = {
                "rn_adu": float(np.median(rns)) if rns else float("nan"),
                "bias_adu": (float(np.median(levels)) if levels
                             else float("nan")),
                "oscan_bias_adu": (float(np.median(olev)) if olev
                                   else float("nan")),
            }
        return out
    finally:
        for e in exps:
            e.close()


def usable_mask(pts: list[dict], drift_max: float = DRIFT_MAX) -> list[bool]:
    """ptc.fit_gain과 동일한 사용 점 선별 기준 (플롯 구분용)."""
    return [abs(p["r"] - 1) <= drift_max and p["S"] > S_MIN_ADU
            and p["p999_raw"] < SAT_GUARD_ADU and p["V"] > 0 for p in pts]


def oscan_slope_fit(pts: list[dict]) -> dict:
    """overscan 중앙값 vs flat 신호 직선 적합 — 기울기 = CMRR 지표."""
    xy = [(p["S"], 0.5 * (p["oscan1"] + p["oscan2"]))
          for p in pts if "oscan1" in p]
    if len(xy) < 3:
        return {"slope": float("nan"), "intercept": float("nan"),
                "n": len(xy)}
    x = np.array([q[0] for q in xy])
    y = np.array([q[1] for q in xy])
    A = np.column_stack([np.ones(len(x)), x])
    (b, m), *_ = np.linalg.lstsq(A, y, rcond=None)
    return {"slope": float(m), "intercept": float(b), "n": len(x)}


def _flat_pairs(exps: list) -> list[tuple]:
    """동일 EXPTIME 그룹 내 경로순 인접 쌍 (runner.py 규약과 동일)."""
    by_t: dict[float, list] = {}
    for e in exps:
        by_t.setdefault(float(e.primary.get("EXPTIME", 0) or 0), []).append(e)
    out = []
    for t in sorted(by_t):
        grp = sorted(by_t[t], key=lambda e: str(e.path))
        out += [(grp[i], grp[i + 1]) for i in range(0, len(grp) - 1, 2)]
    return out


def diagnose_camera(bias_files: list, flat_files: list,
                    roi=core.ROI, ovsc=core.OVSC_REAL) -> list[dict]:
    """파일 목록 -> 앰프별 진단 레코드 (MEF 확장 순서).

    레코드: extname, ampid, gain, gain_err, curvature, rn_adu, rn_e,
    bias_adu, oscan_bias_adu, oscan_slope, oscan_intercept, n_pairs,
    flags, fit_status, resid_rms_pct, points(쌍별 dict 리스트).
    """
    rn = measure_bias(bias_files, roi=roi, ovsc=ovsc)
    exps = [core.open_l0(p) for p in flat_files]
    try:
        fps = _flat_pairs(exps)
        recs = []
        for g in exps[0].amps:
            ext = g.extname
            r = rn[ext]
            pts = ptc_points(fps, ext, r["bias_adu"], r["rn_adu"],
                             roi=roi, ovsc=ovsc)
            pfit = fit_gain(pts)
            osl = oscan_slope_fit(pts)
            gain = pfit.get("gain", 0.0)
            flags = []
            if pfit.get("status") != "OK":
                flags.append(str(pfit.get("status", "?")))
            if np.isfinite(osl["slope"]) and \
                    abs(osl["slope"]) > OSCAN_SLOPE_LIMIT:
                flags.append("OSCAN_SLOPE")
            recs.append({
                "extname": ext,
                "ampid": int(g.ampid),
                "gain": float(gain),
                "gain_err": float(pfit.get("gain_err", 0.0)),
                "curvature": float(pfit.get("curv_a", 0.0)),
                "rn_adu": r["rn_adu"],
                # gain 적합 실패(gain 0)면 RN[e-]는 미측정 — 0.000 e-가
                # '완벽한 잡음'으로 오독되지 않게 NaN으로 남긴다
                "rn_e": (r["rn_adu"] * float(gain) if float(gain) > 0
                         else float("nan")),
                "bias_adu": r["bias_adu"],
                "oscan_bias_adu": r["oscan_bias_adu"],
                "oscan_slope": osl["slope"],
                "oscan_intercept": osl["intercept"],
                "n_pairs": int(pfit.get("n_pts", 0)),
                "flags": ";".join(flags) or "OK",
                "fit_status": pfit.get("status", "?"),
                "resid_rms_pct": float(pfit.get("resid_rms_pct", 0.0)),
                "points": pts,
            })
        return recs
    finally:
        for e in exps:
            e.close()


# -- 산출물 ------------------------------------------------------------------

def write_outputs(recs: list[dict], outdir, campaign: str,
                  date: str = "", config: str = "") -> dict:
    """CSV + 앰프별 페이지 + 카메라 요약 PNG를 OUTDIR/diagnostics/에 쓴다."""
    base = Path(outdir) / "diagnostics"
    (base / "amps").mkdir(parents=True, exist_ok=True)
    (base / "ptc_points").mkdir(parents=True, exist_ok=True)

    csv_path = base / f"diagnostics_{campaign}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLS)
        for r in recs:
            w.writerow([r["extname"], r["ampid"],
                        "%.4f" % r["gain"], "%.4f" % r["gain_err"],
                        "%.4e" % r["curvature"],
                        "%.3f" % r["rn_adu"], "%.3f" % r["rn_e"],
                        "%.1f" % r["bias_adu"],
                        "%.4e" % r["oscan_slope"],
                        r["n_pairs"], r["flags"],
                        campaign, date, config])

    for r in recs:
        pp = base / "ptc_points" / f"{r['extname']}_ptc.csv"
        with pp.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(PT_COLS)
            for p in r["points"]:
                w.writerow(["%.2f" % p["S"], "%.3f" % p["V"],
                            "%.6f" % p["r"],
                            "%.3f" % p["oscan1"] if "oscan1" in p else "",
                            "%.3f" % p["oscan2"] if "oscan2" in p else "",
                            "%.3f" % p["exptime"], "%.1f" % p["p999_raw"]])

    for r in recs:
        plot_amp_page(r, campaign,
                      base / "amps" / f"{r['extname']}_diagnostics.png")
    plot_summary(recs, campaign, base / "diagnostics_summary.png")
    return {"dir": str(base), "csv": str(csv_path),
            "summary_png": str(base / "diagnostics_summary.png")}


def run_diagnostics(bias_files: list, flat_files: list, outdir,
                    campaign: str, roi=core.ROI,
                    ovsc=core.OVSC_REAL, config: str = "") -> dict:
    """진단 + 산출물 일괄 실행. {'records', 'dir', 'csv', 'summary_png'}."""
    recs = diagnose_camera(bias_files, flat_files, roi=roi, ovsc=ovsc)
    with core.open_l0(bias_files[0]) as e0:
        date = str(e0.primary.get("DATE-OBS", "")).strip()
    out = write_outputs(recs, outdir, campaign, date=date, config=config)
    out["records"] = recs
    return out


# -- 플롯 (matplotlib은 함수 안에서만) ----------------------------------------

def plot_amp_page(rec: dict, campaign: str, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pts = rec["points"]
    use = np.array(usable_mask(pts), dtype=bool) if pts else np.zeros(0, bool)
    S = np.array([p["S"] for p in pts])
    V = np.array([p["V"] for p in pts])
    rr = np.array([p["r"] for p in pts])
    gain, a = rec["gain"], rec["curvature"]

    fig, axs = plt.subplots(2, 3, figsize=(13.5, 7.5))
    fig.suptitle("[%s] %s (AMPID %d) - PTC diagnostics"
                 % (campaign, rec["extname"], rec["ampid"]))

    # 1 PTC log-log
    ax = axs[0, 0]
    pos = use & (V > 0)
    exc = ~use & (V > 0)
    if pos.any():
        ax.loglog(S[pos], V[pos], "o", ms=5, color="tab:blue", label="used")
    if exc.any():
        ax.loglog(S[exc], V[exc], "x", ms=6, color="tab:red",
                  label="excluded")
    if gain > 0 and len(S):
        grid = np.geomspace(max(S.min() * 0.7, 10.0), S.max() * 1.3, 256)
        model = grid / gain - a * grid ** 2
        ok = model > 0
        ax.loglog(grid[ok], model[ok], "-", color="k", lw=1,
                  label="V = S/g - aS$^2$")
    ax.text(0.04, 0.96, "g = %.4f e-/ADU\na = %.2e 1/ADU" % (gain, a),
            transform=ax.transAxes, va="top", fontsize=8,
            bbox=dict(fc="w", alpha=0.7, ec="0.7"))
    ax.set_xlabel("S [ADU]")
    ax.set_ylabel("V [ADU$^2$]")
    ax.set_title("PTC (pair variance)", fontsize=10)
    ax.legend(fontsize=7, loc="lower right")

    # 2 apparent gain vs S
    ax = axs[0, 1]
    if pos.any():
        ax.semilogx(S[pos], S[pos] / V[pos], "o", ms=5, color="tab:blue")
    if gain > 0:
        ax.axhline(gain, ls="--", color="k", lw=1, label="fit g")
        ax.axhspan(gain * 0.98, gain * 1.02, color="tab:green", alpha=0.15,
                   label="±2%")
    ax.set_xlabel("S [ADU]")
    ax.set_ylabel("S / V [e-/ADU]")
    ax.set_title("apparent gain (RN-subtracted V)", fontsize=10)
    ax.legend(fontsize=7)

    # 3 overscan level vs flat signal
    ax = axs[0, 2]
    ox = np.array([p["S"] for p in pts if "oscan1" in p])
    oy = np.array([0.5 * (p["oscan1"] + p["oscan2"])
                   for p in pts if "oscan1" in p])
    if len(ox):
        ax.plot(ox, oy, "o", ms=5, color="tab:blue")
        if np.isfinite(rec["oscan_slope"]):
            gx = np.linspace(0, ox.max() * 1.05, 64)
            ax.plot(gx, rec["oscan_intercept"] + rec["oscan_slope"] * gx,
                    "-", color="k", lw=1)
            ax.text(0.04, 0.96, "slope = %.2e ADU/ADU" % rec["oscan_slope"],
                    transform=ax.transAxes, va="top", fontsize=8,
                    bbox=dict(fc="w", alpha=0.7, ec="0.7"))
        if np.isfinite(rec.get("oscan_bias_adu", float("nan"))):
            ax.axhline(rec["oscan_bias_adu"], ls=":", color="0.4", lw=1,
                       label="bias-frame oscan")
            ax.legend(fontsize=7)
    else:
        ax.text(0.5, 0.5, "no overscan data", ha="center", va="center",
                transform=ax.transAxes)
    ax.set_xlabel("flat S [ADU]")
    ax.set_ylabel("overscan median [ADU]")
    ax.set_title("overscan vs signal (CMRR)", fontsize=10)

    # 4 pair ratio
    ax = axs[1, 0]
    if len(S):
        ax.semilogx(S, (rr - 1.0) * 100.0, "o", ms=5, color="tab:blue")
    ax.axhspan(-DRIFT_MAX * 100, DRIFT_MAX * 100, color="tab:green",
               alpha=0.15)
    ax.axhline(0.0, ls="--", color="k", lw=1)
    ax.set_xlabel("S [ADU]")
    ax.set_ylabel("(r - 1) [%]")
    ax.set_title("pair ratio (lamp drift guard ±1%)", fontsize=10)

    # 5 fit residuals
    ax = axs[1, 1]
    if gain > 0 and pos.any():
        model = S[pos] / gain - a * S[pos] ** 2
        ax.semilogx(S[pos], (V[pos] - model) / model * 100.0, "o", ms=5,
                    color="tab:blue")
    ax.axhline(0.0, ls="--", color="k", lw=1)
    ax.set_xlabel("S [ADU]")
    ax.set_ylabel("(V - fit) / fit [%]")
    ax.set_title("PTC fit residuals", fontsize=10)

    # 6 numbers panel
    ax = axs[1, 2]
    ax.axis("off")
    lines = [
        "campaign   %s" % campaign,
        "extname    %s   (AMPID %d)" % (rec["extname"], rec["ampid"]),
        "gain       %.4f +/- %.4f e-/ADU" % (rec["gain"], rec["gain_err"]),
        "curvature  %.3e 1/ADU" % rec["curvature"],
        "RN         %.3f ADU = %.3f e-" % (rec["rn_adu"], rec["rn_e"]),
        "bias       %.1f ADU" % rec["bias_adu"],
        "oscan slope %.3e ADU/ADU" % rec["oscan_slope"],
        "pairs used %d   fit %s" % (rec["n_pairs"], rec["fit_status"]),
        "fit resid  %.2f %% rms" % rec["resid_rms_pct"],
        "flags      %s" % rec["flags"],
    ]
    ax.text(0.02, 0.95, "\n".join(lines), transform=ax.transAxes,
            va="top", family="monospace", fontsize=9)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=110)
    plt.close(fig)


def plot_summary(recs: list[dict], campaign: str, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    amp = np.array([r["ampid"] for r in recs], dtype=float)
    metrics = [
        ("gain", "GAIN [e-/ADU]"),
        ("rn_e", "RDNOISE [e-]"),
        ("bias_adu", "BIAS LEVEL [ADU]"),
        ("curvature", "PTC curvature a [1/ADU]"),
        ("oscan_slope", "overscan slope [ADU/ADU]"),
    ]
    fig, axs = plt.subplots(5, 1, figsize=(10.5, 12), sharex=True)
    fig.suptitle("[%s] camera summary - PTC diagnostics (%d amps)"
                 % (campaign, len(recs)))
    for ax, (key, label) in zip(axs, metrics):
        v = np.array([float(r[key]) for r in recs])
        fin = np.isfinite(v)
        if fin.any():
            med = float(np.median(v[fin]))
            mad = core.mad_std(v[fin])
            out = fin & (np.abs(v - med) > OUTLIER_NMAD * mad) \
                if mad > 0 else np.zeros(len(v), bool)
            ax.plot(amp[fin & ~out], v[fin & ~out], "o", ms=4,
                    color="tab:blue")
            if out.any():
                ax.plot(amp[out], v[out], "o", ms=6, color="red",
                        label="outlier (>%g MAD)" % OUTLIER_NMAD)
                ax.legend(fontsize=7)
            ax.axhline(med, ls="--", color="k", lw=1)
        if key == "oscan_slope":
            ax.axhline(OSCAN_SLOPE_LIMIT, ls=":", color="0.4", lw=1)
            ax.axhline(-OSCAN_SLOPE_LIMIT, ls=":", color="0.4", lw=1)
        ax.set_ylabel(label, fontsize=9)
        ax.grid(alpha=0.25)
    axs[-1].set_xlabel("AMPID")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(path, dpi=110)
    plt.close(fig)


# -- CLI ---------------------------------------------------------------------

def main(argv=None) -> int:
    import argparse
    import glob as globmod

    ap = argparse.ArgumentParser(
        description="Per-amp PTC diagnostic pages + camera summary")
    ap.add_argument("--bias", required=True, help="bias frame glob")
    ap.add_argument("--flats", required=True, help="flat frame glob")
    ap.add_argument("-o", "--outdir", required=True, help="output directory")
    ap.add_argument("--campaign", required=True, help="campaign name")
    ap.add_argument("--config", default="",
                    help="Archon config version recorded in the config column")
    ap.add_argument("--roi-test", action="store_true", dest="roi_test",
                    help="use the testkit reduced-geometry roi/ovsc slices")
    a = ap.parse_args(argv)

    bias_files = sorted(globmod.glob(a.bias))
    flat_files = sorted(globmod.glob(a.flats))
    if len(bias_files) < 2 or not flat_files:
        print("ERROR: not enough frames (bias %d, need >= 2; flats %d)"
              % (len(bias_files), len(flat_files)), file=sys.stderr)
        return 1

    if a.roi_test:
        from kmt_cam_char import testkit
        roi = (slice(20, testkit.NY - 20),
               slice(10, testkit.DATA_COLS - 10))
        ovsc = slice(testkit.DATA_COLS,
                     testkit.DATA_COLS + testkit.OVSC_COLS)
    else:
        roi, ovsc = core.ROI, core.OVSC_REAL

    res = run_diagnostics(bias_files, flat_files, a.outdir, a.campaign,
                          roi=roi, ovsc=ovsc, config=a.config)
    recs = res["records"]
    print("[%s] %d amps (bias %d, flats %d) -> %s"
          % (a.campaign, len(recs), len(bias_files), len(flat_files),
             res["csv"]))
    for r in recs:
        if r["flags"] != "OK":
            print("  %-6s AMPID %2d: %s" % (r["extname"], r["ampid"],
                                            r["flags"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

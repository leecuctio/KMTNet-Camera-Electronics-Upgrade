"""ADC 코드 무결성 점검 — code histogram, bit 점유율, missing code, DNL.

계획서에 없는 신규 항목: CEU 16-bit ADC의 코드 레벨 결함(stuck bit,
missing code, DNL)을 실험실 bias/flat 세트에서 직접 확인한다. 코드축은
core 계층(unsigned_from_stored: 헤더 BZERO/BSCALE 적용)이 반환하는
**물리 ADC 코드축 0..65535 확정**이다 — 저장 규약(int16 + BZERO=32768)의
오프셋은 판독 시 제거되므로 히스토그램/missing/stuck/DNL 결과의 코드
번호는 실제 ADC 출력 코드와 일치한다.

방법 요약
  * code_histogram: ROI 픽셀의 uint16 코드 전역(65536-bin) 누적 히스토그램
    (전 프레임 합산).
  * bit_occupancy: 비트별 '1' 점유율. stuck bit 판정은 커버 대역폭
    (누적분포 1e-4 분위 대역 [lo, hi])이 2^bit 이상인 '시험 가능' 비트에
    한해 점유율 ~0(stuck-at-0) / ~1(stuck-at-1)로 내린다 — 신호가 낮아
    자연히 0인 상위 비트를 오검출하지 않기 위한 조건. 상위 비트를
    시험하려면 해당 비트 경계를 넘나드는 flat 레벨 세트가 필요하다.
  * missing_codes: 로컬 중앙값(window 33) >= 임계(기본 20 카운트)인
    잘 덮인 대역 안에서 카운트 0인 코드 — 대역 경계 판정이 곧 이 로컬
    중앙값 조건이다 (Poisson 바닥에서의 오검출 확률 exp(-20) 수준).
  * dnl_estimate: 완만 구간(로컬 중앙값 >= 100) 가정 아래
        DNL_c ~ counts_c / <window 내 leave-one-out 평균> - 1
    Poisson 기대 분산 (w/(w-1))/lambda 를 빼서 rms를 보고한다.
    커버 코드 수 < 64 이면 NaN — bias 단독처럼 분포 폭이 좁은 세트는
    로컬 평활 가정이 깨져 계통 오차가 크므로 무효 (flat 세트 권장).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

try:
    from . import core
except ImportError:                      # 스크립트 직접 실행 지원
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from kmt_cam_char import core

NCODES = 65536
BAND_Q = 1e-4                # 커버 대역 분위수 (양끝)
STUCK_EPS = 1e-6             # 점유율 0/1 판정 여유
MISSING_WINDOW = 33          # missing code 로컬 중앙값 창 [codes]
MISSING_MIN_MED = 20         # 커버 대역 판정 임계 [counts]
DNL_WINDOW = 9               # DNL 로컬 평활 창 [codes]
DNL_MIN_MED = 100            # DNL 완만 구간 임계 [counts]
DNL_MIN_CODES = 64           # 이보다 적으면 dnl_rms = NaN


def _codes(exp, extname: str, rows, cols) -> np.ndarray:
    """(rows, cols) 슬라이스의 물리 unsigned ADC 코드 (int64)."""
    hdu = exp.hdul[extname]
    a = core.unsigned_from_stored(hdu.section[rows, cols], hdu.header)
    return np.rint(a).astype(np.int64)


def _local_median(x: np.ndarray, w: int) -> np.ndarray:
    pad = w // 2
    xp = np.pad(x.astype(np.float64), pad, mode="edge")
    return np.median(sliding_window_view(xp, w), axis=1)


# ---------------------------------------------------------------------------
# 계산 함수 (numpy만으로 임포트 가능)
# ---------------------------------------------------------------------------
def code_histogram(paths: list, ext: str, roi=core.ROI) -> dict:
    """전 프레임 합산 uint16 코드 히스토그램. {counts(65536), n_samples}."""
    counts = np.zeros(NCODES, dtype=np.int64)
    for p in paths:
        with core.open_l0(p) as exp:
            u = _codes(exp, ext, roi[0], roi[1])
        counts += np.bincount(u.ravel(), minlength=NCODES)
    return {"counts": counts, "n_samples": int(counts.sum())}


def bit_occupancy(counts: np.ndarray) -> np.ndarray:
    """비트별 '1' 점유율 (길이 16, bit 0 = LSB)."""
    total = counts.sum()
    if total <= 0:
        return np.full(16, np.nan)
    codes = np.arange(NCODES, dtype=np.int64)
    return np.array([counts[(codes >> b) & 1 == 1].sum() for b in range(16)],
                    dtype=np.float64) / float(total)


def coverage_band(counts: np.ndarray, q: float = BAND_Q) -> tuple[int, int]:
    """누적분포 [q, 1-q] 분위 코드 대역 (lo, hi)."""
    tot = counts.sum()
    if tot <= 0:
        return 0, 0
    csum = np.cumsum(counts)
    lo = int(np.searchsorted(csum, q * tot, side="left"))
    hi = int(np.searchsorted(csum, (1.0 - q) * tot, side="left"))
    return lo, hi


def stuck_bits(counts: np.ndarray, eps: float = STUCK_EPS) -> list[dict]:
    """시험 가능한(대역폭 >= 2^bit) 비트 중 점유율 ~0/~1인 비트 목록."""
    occ = bit_occupancy(counts)
    lo, hi = coverage_band(counts)
    width = hi - lo
    out = []
    for b in range(16):
        if width < 2 ** b or not np.isfinite(occ[b]):
            continue                     # 이 데이터로는 시험 불가
        if occ[b] <= eps:
            out.append({"bit": b, "stuck_at": 0, "occupancy": float(occ[b])})
        elif occ[b] >= 1.0 - eps:
            out.append({"bit": b, "stuck_at": 1, "occupancy": float(occ[b])})
    return out


def missing_codes(counts: np.ndarray, window: int = MISSING_WINDOW,
                  min_med: int = MISSING_MIN_MED) -> dict:
    """커버 대역(로컬 중앙값 >= min_med) 안의 카운트 0 코드 목록."""
    med = _local_median(counts, window)
    idx = np.where((counts == 0) & (med >= min_med))[0]
    return {"missing": [int(i) for i in idx], "n_missing": int(idx.size)}


def dnl_estimate(counts: np.ndarray, window: int = DNL_WINDOW,
                 min_med: int = DNL_MIN_MED,
                 min_codes: int = DNL_MIN_CODES) -> dict:
    """완만 구간 로컬 히스토그램 기반 DNL 추정 (커버 부족 시 NaN).

    반환: {dnl_rms, n_codes, codes, dnl} — dnl_rms는 Poisson 기대 분산을
    차감한 값, codes/dnl은 사용 코드와 코드별 DNL (플롯용, 없으면 None).
    """
    x = counts.astype(np.float64)
    med = _local_median(x, window)
    loo = (np.convolve(x, np.ones(window), mode="same") - x) / (window - 1)
    mask = (med >= min_med) & (loo > 0)
    n_codes = int(mask.sum())
    if n_codes < min_codes:
        return {"dnl_rms": float("nan"), "n_codes": n_codes,
                "codes": None, "dnl": None}
    dnl = x[mask] / loo[mask] - 1.0
    poisson = (window / (window - 1.0)) / loo[mask]
    rms = float(np.sqrt(max(np.mean(dnl ** 2) - np.mean(poisson), 0.0)))
    return {"dnl_rms": rms, "n_codes": n_codes,
            "codes": np.where(mask)[0], "dnl": dnl}


# ---------------------------------------------------------------------------
# 플롯 (matplotlib은 함수 내부에서만 import)
# ---------------------------------------------------------------------------
def _plot_amp_page(path, ext: str, res: dict, campaign: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    counts = res["counts"]
    lo, hi = res["band"]
    pad = max(16, (hi - lo) // 10)
    x0, x1 = max(0, lo - pad), min(NCODES - 1, hi + pad)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    ax = axes[0]
    xs = np.arange(x0, x1 + 1)
    ax.step(xs, np.maximum(counts[x0:x1 + 1], 0.5), where="mid", lw=0.7,
            color="tab:blue")
    ax.set_yscale("log")
    for m in res["missing"]:
        ax.axvline(m, color="red", lw=0.8, alpha=0.8)
    ax.set_xlabel("ADC code")
    ax.set_ylabel("samples")
    ax.set_title("Code histogram (band %d..%d, missing in red)" % (lo, hi))
    ax = axes[1]
    occ = res["bit_occ"]
    stuck_set = {d["bit"] for d in res["stuck"]}
    colors = ["red" if b in stuck_set else "tab:gray" for b in range(16)]
    ax.bar(range(16), occ, color=colors)
    ax.axhline(0.5, color="k", ls="--", lw=0.8)
    ax.set_xlabel("bit (0 = LSB)")
    ax.set_ylabel("occupancy of '1'")
    ax.set_ylim(0, 1.05)
    ax.set_title("Bit occupancy (stuck in red)")
    ax = axes[2]
    dnl = res["dnl"]
    if dnl["codes"] is not None:
        ax.plot(dnl["codes"], dnl["dnl"], ".", ms=2, color="tab:blue")
        ax.axhline(0.0, color="k", lw=0.6)
        ax.set_xlabel("ADC code")
        ax.set_ylabel("DNL estimate")
        ax.set_title("DNL (rms=%.4f, %d codes)"
                     % (dnl["dnl_rms"], dnl["n_codes"]))
    else:
        ax.text(0.5, 0.5, "DNL: insufficient coverage\n(n_codes=%d)"
                % dnl["n_codes"], ha="center", va="center",
                transform=ax.transAxes)
        ax.set_axis_off()
    fig.suptitle("%s ADC check - %s" % (ext, campaign))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=110)
    plt.close(fig)


def _plot_summary(path, exts, ampids, per_amp: dict, campaign: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n_def = [per_amp[x]["n_missing"] + len(per_amp[x]["stuck"])
             for x in exts]
    occ_mean = np.nanmean(np.stack([per_amp[x]["bit_occ"] for x in exts]),
                          axis=0)
    stuck_any = set()
    for x in exts:
        stuck_any |= {d["bit"] for d in per_amp[x]["stuck"]}

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    ax = axes[0]
    colors = ["red" if b in stuck_any else "tab:gray" for b in range(16)]
    ax.bar(range(16), occ_mean, color=colors)
    ax.axhline(0.5, color="k", ls="--", lw=0.8)
    ax.set_xlabel("bit (0 = LSB)")
    ax.set_ylabel("mean occupancy")
    ax.set_ylim(0, 1.05)
    ax.set_title("Bit occupancy, amp mean (any-amp stuck in red)")
    ax = axes[1]
    colors = ["red" if d > 0 else "tab:blue" for d in n_def]
    ax.bar(ampids, n_def, color=colors)
    ax.set_xlabel("AMPID")
    ax.set_ylabel("missing + stuck")
    ax.set_title("Defect count per amp")
    ax = axes[2]
    worst = max(exts, key=lambda x: (per_amp[x]["n_missing"]
                                     + len(per_amp[x]["stuck"])))
    counts = per_amp[worst]["counts"]
    lo, hi = per_amp[worst]["band"]
    pad = max(16, (hi - lo) // 10)
    x0, x1 = max(0, lo - pad), min(NCODES - 1, hi + pad)
    xs = np.arange(x0, x1 + 1)
    ax.step(xs, np.maximum(counts[x0:x1 + 1], 0.5), where="mid", lw=0.7,
            color="tab:blue")
    ax.set_yscale("log")
    for m in per_amp[worst]["missing"]:
        ax.axvline(m, color="red", lw=0.8, alpha=0.8)
    ax.set_xlabel("ADC code")
    ax.set_ylabel("samples")
    ax.set_title("Histogram band, worst amp %s" % worst)
    fig.suptitle("adccheck summary - %s" % campaign)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 드라이버 + CSV
# ---------------------------------------------------------------------------
def _write_csv(path, header: list[str], rows: list[list]):
    with open(path, "w") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")


def run_adccheck(paths: list, outdir, campaign: str = "LAB",
                 roi=core.ROI, exts: list[str] | None = None) -> dict:
    """bias+flat 세트로 ADC 무결성 점검: OUTDIR/adccheck/ 아래 PNG/CSV."""
    paths = [str(p) for p in paths]
    if not paths:
        raise ValueError("run_adccheck: empty path list")
    with core.open_l0(paths[0]) as exp:
        if exts is None:
            exts = list(exp.amp_names)
        geo = {g.extname: (int(g.ampid), int(g.ctrlid)) for g in exp.amps}
        date = str(exp.primary.get("DATE-OBS", ""))
    exts = sorted(exts, key=lambda x: geo.get(x, (0, 0))[0])
    base = Path(outdir) / "adccheck"
    ampdir = base / "amps"
    ampdir.mkdir(parents=True, exist_ok=True)

    per_amp = {}
    for ext in exts:
        h = code_histogram(paths, ext, roi=roi)
        counts = h["counts"]
        res = {
            "counts": counts,
            "n_samples": h["n_samples"],
            "band": coverage_band(counts),
            "bit_occ": bit_occupancy(counts),
            "stuck": stuck_bits(counts),
        }
        miss = missing_codes(counts)
        res["missing"] = miss["missing"]
        res["n_missing"] = miss["n_missing"]
        res["dnl"] = dnl_estimate(counts)
        per_amp[ext] = res
        _plot_amp_page(ampdir / ("%s_adccheck.png" % ext), ext, res, campaign)

    header = ["EXTNAME", "AMPID", "N_SAMPLES", "BAND_LO", "BAND_HI",
              "N_STUCK", "STUCK_BITS", "N_MISSING", "MISSING_CODES",
              "DNL_RMS", "N_DNL_CODES", "CAMPAIGN", "DATE"]
    rows = []
    for ext in exts:
        r = per_amp[ext]
        stuck_s = ";".join("%d@%d" % (d["bit"], d["stuck_at"])
                           for d in r["stuck"]) or "-"
        mlist = r["missing"][:10]
        miss_s = ";".join(str(m) for m in mlist) or "-"
        if r["n_missing"] > 10:
            miss_s += ";+%dmore" % (r["n_missing"] - 10)
        rows.append([ext, geo.get(ext, (0, 0))[0], r["n_samples"],
                     r["band"][0], r["band"][1], len(r["stuck"]), stuck_s,
                     r["n_missing"], miss_s, "%.5g" % r["dnl"]["dnl_rms"],
                     r["dnl"]["n_codes"], campaign, date])
    csv_path = base / ("adccheck_%s.csv" % campaign)
    _write_csv(csv_path, header, rows)

    summary = base / "adccheck_summary.png"
    _plot_summary(summary, exts, [geo.get(x, (0, 0))[0] for x in exts],
                  per_amp, campaign)
    return {"per_amp": per_amp, "csv": str(csv_path),
            "summary_png": str(summary), "outdir": str(base)}


def main(argv=None):
    import argparse
    import glob as _glob
    ap = argparse.ArgumentParser(
        prog="adccheck",
        description="ADC code integrity check (histogram / bit occupancy / "
                    "missing codes / DNL)")
    ap.add_argument("--bias", default=None, help="bias L0 frame glob")
    ap.add_argument("--flats", default=None,
                    help="flat L0 frame glob (extends code coverage)")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--campaign", default="LAB")
    a = ap.parse_args(argv)
    paths = []
    for pat in (a.bias, a.flats):
        if pat:
            paths += sorted(_glob.glob(pat))
    if not paths:
        ap.error("--bias/--flats matched no files")
    res = run_adccheck(paths, a.outdir, campaign=a.campaign)
    print("adccheck: %d frames, %d amps -> %s"
          % (len(paths), len(res["per_amp"]), res["outdir"]))


if __name__ == "__main__":
    main()

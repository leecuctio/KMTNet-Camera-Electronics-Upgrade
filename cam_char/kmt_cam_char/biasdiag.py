"""Bias 구조·상관 진단 — 행/열 프로파일, FPN 분리, 잡음 PSD, 채널 상관.

계획서 §5.3-5.4의 bias 구조 분석과 §16(전자파 간섭·주변 장치)의
pickup/공통모드 진단이 공유하는 모듈. 모든 통계는 raw ADU(bias 포함),
픽셀 접근은 memmap section 슬라이스만 사용한다.

방법 요약
  * bias_profiles: 스택 평균 영상의 행/열 프로파일. 시간 잡음(RN)은
    프레임 쌍차분 MAD/sqrt(2), 고정패턴은 스택 공간 잡음에서
        FPN^2 = mad_std(stack)^2 - RN^2 / N_frames
    로 분리. difference image(첫 쌍차분 축소 영상 + 평균/RMS 통계),
    프레임 순번 vs bias 준위 drift 시계열(§5.4 drift plot), per-ADU bias
    히스토그램, overscan 평균 및 image-overscan 차이 병기.
  * noise_psd: 각 프레임의 행별(리드아웃 순서) Hann 창 rfft 파워를
    행·프레임 평균. 주파수축은 cycles/pixel(CSV에도 이 단위로 기록) —
    Hz 환산은 픽셀 클록 메타가 확정되면 f_Hz = f_cpp * f_pixclk 로 수행.
    백색 바닥(중앙값) 대비 5 sigma 이상의 로컬 최대를 피크로 보고
    (rms 등가 진폭 포함; 창 스캘럽 손실로 진폭은 최대 ~15% 과소평가 가능).
    프레임 차분을 쓰지 않으므로 위상 고정 pickup도 놓치지 않는다.
  * corr_matrix: 프레임 쌍차분(고정패턴 소거) 픽셀열의 채널 간 Pearson
    상관 — 같은 컨트롤러의 공통모드 잡음이 블록 상관으로 나타난다.
    같은 픽셀 인덱스(동일 ROI 슬라이스)로 정렬해 비교한다.

ovsc 파라미터: core.OVSC_REAL은 실기하 고정이므로 축소 합성 기하에서는
kit.ovsc 슬라이스를 넘긴다 (자체 _raw는 core.unsigned_from_stored로
BZERO/BSCALE 적용 물리 unsigned ADU를 반환 — core.roi_raw와 동일 스케일).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    from . import core
except ImportError:                      # 스크립트 직접 실행 지원
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from kmt_cam_char import core

PSD_SNR_MIN = 5.0            # 백색 바닥 대비 피크 판정 문턱 [sigma]
CORR_MAX_SAMPLES = 200_000   # 채널당 상관 표본 상한 (stride 서브샘플)
HIST_HALF_WIDTH = 10.0       # bias 히스토그램 범위 [sigma]


def _raw(exp, extname: str, rows, cols) -> np.ndarray:
    """임의 (rows, cols) 슬라이스의 물리 unsigned raw ADU (축소 기하 지원)."""
    hdu = exp.hdul[extname]
    return core.unsigned_from_stored(hdu.section[rows, cols], hdu.header)


def _shrink(a: np.ndarray, max_dim: int = 320) -> np.ndarray:
    """블록 평균으로 각 축을 max_dim 이하로 축약 (표시/보관용 축소 영상)."""
    fy = max(1, int(np.ceil(a.shape[0] / max_dim)))
    fx = max(1, int(np.ceil(a.shape[1] / max_dim)))
    ny, nx = a.shape[0] // fy * fy, a.shape[1] // fx * fx
    return a[:ny, :nx].reshape(ny // fy, fy, nx // fx, fx).mean(axis=(1, 3))


# ---------------------------------------------------------------------------
# 계산 함수 (numpy만으로 임포트 가능)
# ---------------------------------------------------------------------------
def bias_profiles(paths: list, ext: str, roi=core.ROI,
                  ovsc=core.OVSC_REAL) -> dict:
    """행/열 프로파일(스택 평균), FPN/RN 분리, difference image 통계.

    반환 dict 주요 키: row_profile, col_profile, bias_adu(중앙값),
    bias_mean_adu, bias_drift_adu, ovsc_adu, img_minus_ovsc_adu,
    rn_adu, fpn_adu, stack_std_adu, diff_mean_adu, diff_rms_adu,
    hist_edges/hist_counts, n_frames, levels_adu(프레임별 중앙값 —
    drift plot 축), diff_img(첫 쌍차분 축소 영상 — 계획서 §5.4의
    bias difference image).
    """
    if not paths:
        raise ValueError("bias_profiles: empty path list")
    n = 0
    sum_img = None
    prev = None
    rn_list: list[float] = []
    diff_mean: list[float] = []
    diff_rms: list[float] = []
    levels: list[float] = []
    means: list[float] = []
    ovsc_means: list[float] = []
    hist_edges = None
    hist_counts = None
    diff_img = None
    for p in paths:
        with core.open_l0(p) as exp:
            a = _raw(exp, ext, roi[0], roi[1])
            o = _raw(exp, ext, roi[0], ovsc)
        levels.append(float(np.median(a)))
        means.append(float(np.mean(a)))
        ovsc_means.append(float(np.mean(o)))
        sum_img = a.copy() if sum_img is None else sum_img + a
        n += 1
        if hist_edges is None:
            med0 = float(np.median(a))
            sig0 = max(core.mad_std(a), 1.0)
            lo = np.floor(med0 - HIST_HALF_WIDTH * sig0)
            hi = np.ceil(med0 + HIST_HALF_WIDTH * sig0)
            hist_edges = np.arange(lo, hi + 2.0) - 0.5
            hist_counts = np.zeros(len(hist_edges) - 1, dtype=np.int64)
        hist_counts += np.histogram(a, bins=hist_edges)[0]
        if prev is None:
            prev = a
        else:                            # 비중첩 연속 쌍
            d = a - prev
            rn_list.append(core.mad_std(d) / np.sqrt(2.0))
            diff_mean.append(float(np.mean(d)))
            diff_rms.append(core.mad_std(d))
            if diff_img is None:         # §5.4 bias difference image (축소)
                diff_img = _shrink(d)
            prev = None
    stack = sum_img / n
    rn = float(np.median(rn_list)) if rn_list else float("nan")
    stack_std = core.mad_std(stack)
    fpn = (float(np.sqrt(max(stack_std ** 2 - rn ** 2 / n, 0.0)))
           if np.isfinite(rn) else float("nan"))
    bias = float(np.median(levels))
    ovsc_mean = float(np.mean(ovsc_means))
    return {
        "n_frames": n,
        "bias_adu": bias,
        "bias_mean_adu": float(np.mean(means)),
        "bias_drift_adu": float(np.ptp(levels)),
        "ovsc_adu": ovsc_mean,
        "img_minus_ovsc_adu": bias - ovsc_mean,
        "rn_adu": rn,
        "fpn_adu": fpn,
        "stack_std_adu": float(stack_std),
        "row_profile": stack.mean(axis=1),
        "col_profile": stack.mean(axis=0),
        "diff_mean_adu": float(np.median(diff_mean)) if diff_mean
        else float("nan"),
        "diff_rms_adu": float(np.median(diff_rms)) if diff_rms
        else float("nan"),
        "hist_edges": hist_edges,
        "hist_counts": hist_counts,
        "levels_adu": levels,
        "diff_img": diff_img,
    }


def noise_psd(paths: list, ext: str, roi=core.ROI,
              snr_min: float = PSD_SNR_MIN) -> dict:
    """행방향(리드아웃 순서) 평균 power spectrum과 탁월 피크 목록.

    주파수 단위: cycles/pixel. 피크: 백색 바닥(중앙값) 대비 snr_min sigma
    이상의 로컬 최대, power 내림차순 [{freq_cpp, power, snr, amp_rms_adu}].
    """
    if not paths:
        raise ValueError("noise_psd: empty path list")
    acc = None
    nrow = 0
    ncols = None
    win = None
    wsum2 = None
    for p in paths:
        with core.open_l0(p) as exp:
            a = _raw(exp, ext, roi[0], roi[1])
        if ncols is None:
            ncols = a.shape[1]
            if ncols < 8:
                raise ValueError("noise_psd: ROI too narrow (%d cols)" % ncols)
            win = np.hanning(ncols)
            wsum2 = float(win.sum()) ** 2
        a = a - a.mean(axis=1, keepdims=True)      # 행 오프셋 제거
        f = np.fft.rfft(a * win, axis=1)
        pw = (np.abs(f) ** 2).sum(axis=0) * 2.0 / wsum2
        acc = pw if acc is None else acc + pw
        nrow += a.shape[0]
    psd = acc / nrow
    freq = np.fft.rfftfreq(ncols)                  # cycles/pixel
    body = psd[1:]
    floor = float(np.median(body))
    sig = float(1.4826 * np.median(np.abs(body - floor)))
    peaks = []
    for k in range(1, len(psd) - 1):
        if psd[k] > psd[k - 1] and psd[k] >= psd[k + 1]:
            snr = (psd[k] - floor) / max(sig, 1e-300)
            if snr >= snr_min:
                peaks.append({
                    "freq_cpp": float(freq[k]),
                    "power": float(psd[k]),
                    "snr": float(snr),
                    "amp_rms_adu": float(np.sqrt(max(psd[k] - floor, 0.0))),
                })
    peaks.sort(key=lambda d: -d["power"])
    return {"freq_cpp": freq, "psd": psd, "peaks": peaks,
            "floor": floor, "floor_sig": sig, "ncols": int(ncols),
            "n_rows_avg": int(nrow), "n_frames": len(paths)}


def corr_matrix(paths: list, exts: list[str] | None = None, roi=core.ROI,
                max_samples: int = CORR_MAX_SAMPLES) -> dict:
    """프레임 쌍차분 기반 채널 상관계수 행렬 (같은 픽셀 인덱스 정렬).

    반환: {exts, corr(NxN, 쌍 평균), ctrlid(채널별), n_pairs}.
    """
    prs = core.pairs(list(paths))
    if not prs:
        raise ValueError("corr_matrix: need >= 2 frames")
    acc = None
    n_pairs = 0
    ctrlid = None
    for p1, p2 in prs:
        with core.open_l0(p1) as e1, core.open_l0(p2) as e2:
            if exts is None:
                exts = list(e1.amp_names)
            if ctrlid is None:
                gmap = {g.extname: g.ctrlid for g in e1.amps}
                ctrlid = [int(gmap.get(x, 1)) for x in exts]
            vecs = []
            for ext in exts:
                d = (_raw(e1, ext, roi[0], roi[1])
                     - _raw(e2, ext, roi[0], roi[1])).ravel()
                step = max(1, d.size // max_samples)
                vecs.append(d[::step])
        c = np.corrcoef(np.stack(vecs))
        acc = c if acc is None else acc + c
        n_pairs += 1
    return {"exts": list(exts), "corr": acc / n_pairs,
            "ctrlid": ctrlid, "n_pairs": n_pairs}


# ---------------------------------------------------------------------------
# 플롯 (matplotlib은 함수 내부에서만 import)
# ---------------------------------------------------------------------------
def _outliers(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    med = np.median(v)
    s = 1.4826 * np.median(np.abs(v - med))
    lim = 5.0 * max(s, 1e-3 * max(abs(med), 1.0))
    return np.abs(v - med) > lim


def _plot_amp_page(path, ext: str, prof: dict, psd: dict, campaign: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(14.5, 7.5))
    ax = axes[0, 0]
    ax.plot(prof["row_profile"], lw=0.7, color="tab:blue")
    ax.set_xlabel("ROI row")
    ax.set_ylabel("stack mean [ADU]")
    ax.set_title("Row profile")
    ax = axes[0, 1]
    ax.plot(prof["col_profile"], lw=0.7, color="tab:blue")
    ax.set_xlabel("ROI column")
    ax.set_ylabel("stack mean [ADU]")
    ax.set_title("Column profile")
    ax = axes[0, 2]                       # §5.4 bias difference image
    if prof.get("diff_img") is not None:
        d = prof["diff_img"]
        vlim = 3.0 * max(prof["diff_rms_adu"], 1e-3)
        im = ax.imshow(d, origin="lower", aspect="auto", cmap="RdBu_r",
                       vmin=-vlim, vmax=vlim)
        fig.colorbar(im, ax=ax, shrink=0.85, label="pair diff [ADU]")
        ax.set_xlabel("ROI column (block)")
        ax.set_ylabel("ROI row (block)")
        ax.set_title("Bias difference image (frame pair 1)")
    else:
        ax.text(0.5, 0.5, "no frame pair", ha="center", va="center",
                transform=ax.transAxes, color="gray")
        ax.set_axis_off()
    ax = axes[1, 0]
    ax.semilogy(psd["freq_cpp"][1:], psd["psd"][1:], lw=0.7,
                color="tab:blue")
    ax.axhline(psd["floor"], color="gray", ls="--", lw=0.8,
               label="white floor")
    for pk in psd["peaks"][:3]:
        ax.plot([pk["freq_cpp"]], [pk["power"]], "rv", ms=6)
        ax.annotate("f=%.4g" % pk["freq_cpp"],
                    (pk["freq_cpp"], pk["power"]),
                    textcoords="offset points", xytext=(4, 4),
                    fontsize=7, color="red")
    ax.set_xlabel("frequency [cycles/pixel]")
    ax.set_ylabel("power [ADU^2]")
    ax.set_title("Row-direction noise PSD (Hann, row+frame avg)")
    ax.legend(fontsize=7, loc="upper right")
    ax = axes[1, 1]
    centers = 0.5 * (prof["hist_edges"][:-1] + prof["hist_edges"][1:])
    ax.step(centers, prof["hist_counts"], where="mid", lw=0.8,
            color="tab:blue")
    ax.set_yscale("log")
    ax.set_xlabel("raw ADU")
    ax.set_ylabel("pixels")
    ax.set_title("Bias histogram (all frames)")
    ax.text(0.02, 0.95,
            "bias=%.1f\nRN=%.2f ADU\nFPN=%.2f ADU\ndrift=%.2f ADU"
            % (prof["bias_adu"], prof["rn_adu"], prof["fpn_adu"],
               prof["bias_drift_adu"]),
            transform=ax.transAxes, va="top", fontsize=8)
    ax = axes[1, 2]                       # §5.4 bias drift plot (프레임 순번)
    lv = np.asarray(prof.get("levels_adu", []), dtype=float)
    if lv.size:
        ax.plot(np.arange(lv.size), lv, "o-", ms=3, lw=0.8,
                color="tab:blue")
        ax.axhline(prof["bias_adu"], color="gray", ls="--", lw=0.8,
                   label="median")
        ax.legend(fontsize=7)
        ax.set_title("Bias drift (ptp %.2f ADU)" % prof["bias_drift_adu"])
    else:
        ax.text(0.5, 0.5, "no frames", ha="center", va="center",
                transform=ax.transAxes, color="gray")
    ax.set_xlabel("frame sequence index")
    ax.set_ylabel("frame median [ADU]")
    fig.suptitle("%s bias diagnostics - %s" % (ext, campaign))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=110)
    plt.close(fig)


def _plot_summary(path, exts, ampids, ctrlids, rn, bias, fpn, corr,
                  campaign: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(13, 7))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.15, 1.0], hspace=0.45,
                          wspace=0.25)
    axh = fig.add_subplot(gs[:, 0])
    disp = corr.copy()
    np.fill_diagonal(disp, np.nan)
    off = disp[np.isfinite(disp)]
    vlim = min(1.0, max(0.3, 1.2 * float(np.max(np.abs(off)))
                        if off.size else 0.3))
    im = axh.imshow(disp, cmap="RdBu_r", vmin=-vlim, vmax=vlim,
                    interpolation="nearest")
    for k in range(1, len(ctrlids)):
        if ctrlids[k] != ctrlids[k - 1]:        # ctrl 블록 경계선
            axh.axhline(k - 0.5, color="k", lw=1.2)
            axh.axvline(k - 0.5, color="k", lw=1.2)
    fs = 7 if len(exts) <= 16 else 4
    axh.set_xticks(range(len(exts)))
    axh.set_xticklabels(exts, rotation=90, fontsize=fs)
    axh.set_yticks(range(len(exts)))
    axh.set_yticklabels(exts, fontsize=fs)
    fig.colorbar(im, ax=axh, shrink=0.85, label="pair-diff correlation")
    axh.set_title("Channel correlation matrix (ctrl blocks)")
    panels = [("RN [ADU]", rn), ("Bias [ADU]", bias), ("FPN [ADU]", fpn)]
    for row, (label, v) in enumerate(panels):
        ax = fig.add_subplot(gs[row, 1])
        v = np.asarray(v, dtype=float)
        x = np.asarray(ampids)
        bad = _outliers(v)
        ax.plot(x, v, "o-", ms=3, lw=0.6, color="tab:blue")
        if bad.any():
            ax.plot(x[bad], v[bad], "o", ms=5, color="red", zorder=5)
        ax.set_ylabel(label, fontsize=8)
        ax.grid(alpha=0.3)
        if row == len(panels) - 1:
            ax.set_xlabel("AMPID")
    fig.suptitle("biasdiag summary - %s" % campaign)
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


def _g(x) -> str:
    return "%.6g" % float(x)


def run_biasdiag(paths: list, outdir, campaign: str = "LAB",
                 roi=core.ROI, ovsc=core.OVSC_REAL,
                 exts: list[str] | None = None) -> dict:
    """bias 세트 전체 진단 실행: OUTDIR/biasdiag/ 아래 PNG/CSV 생성."""
    paths = [str(p) for p in paths]
    if len(paths) < 2:
        raise ValueError("run_biasdiag: need >= 2 bias frames")
    with core.open_l0(paths[0]) as exp:
        if exts is None:
            exts = list(exp.amp_names)
        geo = {g.extname: (int(g.ampid), int(g.ctrlid)) for g in exp.amps}
        date = str(exp.primary.get("DATE-OBS", ""))
    exts = sorted(exts, key=lambda x: geo.get(x, (0, 0))[0])
    base = Path(outdir) / "biasdiag"
    ampdir = base / "amps"
    ampdir.mkdir(parents=True, exist_ok=True)

    per_amp = {}
    for ext in exts:
        prof = bias_profiles(paths, ext, roi=roi, ovsc=ovsc)
        psd = noise_psd(paths, ext, roi=roi)
        per_amp[ext] = {"profiles": prof, "psd": psd}
        _plot_amp_page(ampdir / ("%s_biasdiag.png" % ext), ext, prof, psd,
                       campaign)
    corr = corr_matrix(paths, exts=exts, roi=roi)

    # 앰프별 CSV — 주파수 단위: cycles/pixel (Hz = f_cpp * pixel clock)
    header = ["EXTNAME", "AMPID", "CTRLID", "N_FRAMES", "BIAS_ADU",
              "BIAS_MEAN_ADU", "OVSC_ADU", "IMG_MINUS_OVSC_ADU",
              "BIAS_DRIFT_ADU", "RN_ADU", "FPN_ADU", "DIFF_RMS_ADU"]
    for i in (1, 2, 3):
        header += ["PEAK%d_FREQ_CPP" % i, "PEAK%d_AMP_ADU" % i,
                   "PEAK%d_SNR" % i]
    header += ["CAMPAIGN", "DATE"]
    rows = []
    for ext in exts:
        prof = per_amp[ext]["profiles"]
        pks = per_amp[ext]["psd"]["peaks"]
        ampid, ctrl = geo.get(ext, (0, 0))
        row = [ext, ampid, ctrl, prof["n_frames"], _g(prof["bias_adu"]),
               _g(prof["bias_mean_adu"]), _g(prof["ovsc_adu"]),
               _g(prof["img_minus_ovsc_adu"]), _g(prof["bias_drift_adu"]),
               _g(prof["rn_adu"]), _g(prof["fpn_adu"]),
               _g(prof["diff_rms_adu"])]
        for i in range(3):
            if i < len(pks):
                row += [_g(pks[i]["freq_cpp"]), _g(pks[i]["amp_rms_adu"]),
                        _g(pks[i]["snr"])]
            else:
                row += ["nan", "nan", "nan"]
        row += [campaign, date]
        rows.append(row)
    csv_path = base / ("biasdiag_%s.csv" % campaign)
    _write_csv(csv_path, header, rows)

    corr_csv = base / ("corr_matrix_%s.csv" % campaign)
    crows = [[exts[i]] + ["%.5f" % v for v in corr["corr"][i]]
             for i in range(len(exts))]
    _write_csv(corr_csv, ["EXTNAME"] + exts, crows)

    summary = base / "biasdiag_summary.png"
    _plot_summary(summary, exts, [geo.get(x, (0, 0))[0] for x in exts],
                  corr["ctrlid"],
                  [per_amp[x]["profiles"]["rn_adu"] for x in exts],
                  [per_amp[x]["profiles"]["bias_adu"] for x in exts],
                  [per_amp[x]["profiles"]["fpn_adu"] for x in exts],
                  corr["corr"], campaign)
    return {"per_amp": per_amp, "corr": corr, "csv": str(csv_path),
            "corr_csv": str(corr_csv), "summary_png": str(summary),
            "outdir": str(base)}


def main(argv=None):
    import argparse
    import glob as _glob
    ap = argparse.ArgumentParser(
        prog="biasdiag",
        description="Bias structure & correlation diagnostics "
                    "(plan sec. 5.3-5.4 / 16)")
    ap.add_argument("--bias", required=True, help="bias L0 frame glob")
    ap.add_argument("--flats", default=None,
                    help="accepted for CLI uniformity (unused)")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--campaign", default="LAB")
    a = ap.parse_args(argv)
    paths = sorted(_glob.glob(a.bias))
    if len(paths) < 2:
        ap.error("--bias matched %d files (need >= 2)" % len(paths))
    res = run_biasdiag(paths, a.outdir, campaign=a.campaign)
    print("biasdiag: %d frames, %d amps -> %s"
          % (len(paths), len(res["per_amp"]), res["outdir"]))


if __name__ == "__main__":
    main()

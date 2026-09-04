"""Linearity — 두 측정 경로가 이 모듈을 공유한다.

[A] Legacy dome ramp (fit_linearity — runner.py가 사용, 시그니처 불변):

  - the lamp runs in TWO regimes (bright for the short exposures, faint for
    the long ones), so exptime -> signal is NOT one relation across the set;
  - the bright regime carries a large t-independent pedestal (illumination
    accumulated during the slow legacy readout), so the model is
        S(t) = A + R t          (A = pedestal, NOT a shutter offset)

The fit therefore uses only the longest contiguous run of levels (sorted by
exptime) whose signal increases monotonically — the bright-lamp ramp — and
the derived nonlinearity is valid over that signal range only (recorded as
[s_range_lo, s_range_hi]; for LINMAX purposes this is the range that
matters, the top end). A true shutter-offset measurement needs the lab
campaign's dedicated procedure; dome sets cannot provide it.

    NL(S) = S_meas / S_fit - 1
    NL(S) ~ a1 S + a2 S^2          correction-form fit (through origin)
    S_true = S_meas (1 - a1 S_meas - a2 S_meas^2)

LINMAX (raw ADU) = bias + largest bias-subtracted S with |NL| <= 1%.

[B] Lab exposure-time ramp (build_points / fit_ramp — 계획서 §7·§9):

램프(고정 광원 + 노출시간 스캔) 프레임에서 앰프별로
    ① 기준노출(ref) 시계열로 램프 밝기 드리프트 정규화
           S_i <- S_i / (ref_i / ref0),   ref0 = median(ref)
    ② S(t)를 가중(저신호 우세, w = 1/S^2) 다항으로 적합하고 그 1차부
           S_lin(t) = R (t + dt)          (R = rate, dt = shutter/trigger offset)
       를 이상 응답으로 삼는다 (고차항 = 비선형 성분 흡수)
    ③ NL(S) = S / S_lin - 1  →  원점 통과 다항 모델 a1 S + ... + a_n S^n
    ④ |NL| <= 0.5% / 1.0% 최대 신호 LINMAX(0.5%), LINMAX(1.0%)
    ⑤ linearizer: 비율 S_true/S_meas 를 다항 1 + c1 S + ... (기본 3차,
       C0=1 고정 — NL(0)=0 제약, gain 자유도와 분리)으로 shot-noise 가중
       적합, 보정 후 잔차 max|S_corr/S_lin - 1| 를 유효범위에서 보고.

Dynamic range: DR = LINMAX·g / RN_e,  DR_bit = log2(DR)  (계획서 §9).

CLI:
    python linearity.py --flats 'ramp*.fits' [--refs 'ref*.fits']
        [--bias 'bias*.fits'] -o OUTDIR --campaign NAME [--config VER]
        [--ampchar amp_characterization.csv] [--roi y0:y1,x0:x1]
        [--ovsc x0:x1]
산출물: OUTDIR/linearity/{linearity_summary.png, amps/<EXT>_linearity.png,
linearity_coeff_<CAMPAIGN>.csv}  (results/README.md §3 스키마).
"""
from __future__ import annotations

import numpy as np

try:
    from .core import (OVSC_REAL, ROI, mad_std, open_l0, roi_raw,
                       unsigned_from_stored)
except ImportError:     # 직접 실행 (python linearity.py ...)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from kmt_cam_char.core import (OVSC_REAL, ROI, mad_std, open_l0,
                                   roi_raw, unsigned_from_stored)

NL_LIMIT = 0.01
SAT_GUARD_ADU = 60000.0
MIN_RUN_LEVELS = 4

NL_LIMITS_RAMP = (0.005, 0.01)      # LINMAX 기준 (0.5%, 1.0%)
POLY_DEG = 3                        # linearizer / ramp 다항 차수 기본값


# =========================================================================
# [A] legacy dome ramp — 기존 API (수정 금지 영역: runner.py 하위호환)
# =========================================================================

def _bright_run(levels: list[dict]) -> list[dict]:
    """Longest contiguous monotonically-increasing-S run in exptime order."""
    by_t = sorted(levels, key=lambda d: d["exptime"])
    best: list[dict] = []
    run: list[dict] = []
    for d in by_t:
        if not run or d["S"] > run[-1]["S"]:
            run.append(d)
        else:
            if len(run) > len(best):
                best = run
            run = [d]
    if len(run) > len(best):
        best = run
    return best


def fit_linearity(levels: list[dict], bias_adu: float) -> dict:
    """levels: [{'exptime', 'S' (bias-sub mean ADU), 'p999_raw'}] per level."""
    usable = [d for d in levels if d["S"] > 0]
    # 공유 p99.9 ceiling(하드 클립) 방어: SAT_GUARD_ADU는 물리 코드축 상수라
    # 그보다 낮은 클립(레거시 변환 데이터의 ~29-30k 물리 ADU 포화)을 거르지
    # 못한다. 서로 다른 레벨 >= 2개가 신호 최상단에서 같은 p99.9 값에 붙어
    # 있으면(하드 클립 plateau) 그 레벨들을 제외한다.
    if len(usable) >= 2:
        ptop = max(d["p999_raw"] for d in usable)
        smax = max(d["S"] for d in usable)
        tol = max(2.0, 1e-4 * ptop)
        ceil_ids = {id(d) for d in usable
                    if d["p999_raw"] >= ptop - tol and d["S"] >= 0.98 * smax}
        if len(ceil_ids) >= 2:
            usable = [d for d in usable if id(d) not in ceil_ids]
    run = [d for d in _bright_run(usable) if d["p999_raw"] < SAT_GUARD_ADU]
    if len(run) < MIN_RUN_LEVELS:
        return {"status": "TOO_FEW_LEVELS", "n_levels": len(run)}
    S = np.array([d["S"] for d in run])
    t = np.array([d["exptime"] for d in run])
    # S = A + R t (A: readout-illumination pedestal of the dome setup)
    A = np.column_stack([np.ones(len(t)), t])
    (ped, rate), *_ = np.linalg.lstsq(A, S, rcond=None)
    if rate <= 0:
        return {"status": "BAD_FIT", "n_levels": len(run)}
    fit = ped + rate * t
    nl = S / fit - 1.0
    B = np.column_stack([S, S ** 2])
    (a1, a2), *_ = np.linalg.lstsq(B, nl, rcond=None)
    grid = np.linspace(S.min(), S.max(), 2048)
    nl_grid = np.abs(a1 * grid + a2 * grid ** 2)
    ok = nl_grid <= NL_LIMIT
    linmax_sub = float(grid[ok][-1]) if ok.any() else float(S.min())
    return {
        "status": "OK",
        "n_levels": len(run),
        "rate_adu_s": float(rate),
        "pedestal_adu": float(ped),
        "lin_a1": float(a1),
        "lin_a2": float(a2),
        "nl_max_pct": float(np.max(np.abs(nl)) * 100.0),
        "resid_pct": float(np.std(nl) * 100.0),   # incl. lamp-drift systematic
        "linmax_raw_adu": float(linmax_sub + bias_adu),
        "linmax_note": "ramp-limited" if bool(ok.all()) else "measured",
        "s_range_lo": float(S.min() + bias_adu),
        "s_range_hi": float(S.max() + bias_adu),
    }


# =========================================================================
# [B] lab exposure-time ramp — 신규 API
# =========================================================================

def _ovsc_median(exp, extname: str, rows, ovsc=OVSC_REAL) -> float:
    """오버스캔 중앙값 [물리 unsigned raw ADU]. core.ovsc_raw는 OVSC_REAL
    고정이라 축소 합성 기하를 위해 직접 슬라이스하고, 스케일은
    core.unsigned_from_stored(BZERO/BSCALE 적용)로 roi_raw와 통일한다."""
    hdu = exp.hdul[extname]
    a = unsigned_from_stored(hdu.section[rows, ovsc], hdu.header)
    return float(np.median(a))


def _measure_series(paths: list, extnames: list[str], roi=ROI,
                    ovsc=OVSC_REAL) -> dict:
    """{ext: [{'t','S','p999_raw','ovsc_adu','path'}, ...]} — 파일당 1회
    오픈으로 모든 앰프의 ROI 중앙값(오버스캔 차감)을 측정한다."""
    out: dict = {e: [] for e in extnames}
    for p in paths:
        with open_l0(p) as exp:
            t = float(exp.primary.get("EXPTIME", 0) or 0)
            for e in extnames:
                a = roi_raw(exp, e, roi=roi)
                o = _ovsc_median(exp, e, roi[0], ovsc)
                out[e].append({
                    "t": t,
                    "S": float(np.median(a)) - o,
                    "p999_raw": float(np.percentile(a, 99.9)),
                    "ovsc_adu": o,
                    "path": str(p),
                })
    return out


def build_points(flat_paths: list, ext: str, roi=ROI, ovsc=OVSC_REAL,
                 ref_paths: list | None = None) -> list[dict]:
    """램프 프레임 목록 -> fit_ramp 입력 points.

    각 점: {'t' 노출시간[s], 'S' ROI 중앙값-오버스캔 중앙값[ADU],
    'ref_S' 그 스텝에 대응하는 기준노출 신호(없으면 None), 'p999_raw',
    'ovsc_adu', 'path'}.  ref는 취득 순서(경로 목록 순서)가 시간 순서라고
    가정하고 시퀀스 위치 기준 선형보간으로 각 램프 스텝에 배정한다.
    """
    meas = _measure_series(list(flat_paths), [ext], roi, ovsc)[ext]
    if ref_paths:
        refm = _measure_series(list(ref_paths), [ext], roi, ovsc)[ext]
        ref_s = np.array([m["S"] for m in refm], dtype=float)
        nf, nr = len(meas), len(refm)
        pos_f = np.linspace(0.0, 1.0, nf) if nf > 1 else np.zeros(1)
        pos_r = np.linspace(0.0, 1.0, nr) if nr > 1 else np.zeros(1)
        ref_at = np.interp(pos_f, pos_r, ref_s)
        for m, r in zip(meas, ref_at):
            m["ref_S"] = float(r)
    else:
        for m in meas:
            m["ref_S"] = None
    return meas


def fit_ramp(points: list[dict], poly_deg: int = POLY_DEG,
             nl_limits: tuple = NL_LIMITS_RAMP,
             sat_guard_adu: float = SAT_GUARD_ADU) -> dict:
    """노출 램프 points -> 선형성/linearizer 결과 dict (docstring [B] 참조).

    points: [{'t','S','ref_S'(옵션),'p999_raw'(옵션)}].  S는 bias(오버스캔)
    차감 ADU.  반환 linmax/lin_c 등은 모두 bias 차감 ADU 도메인이다.
    """
    pts = [dict(p) for p in points
           if p.get("S", 0.0) > 0 and p.get("t", 0.0) > 0
           and p.get("p999_raw", 0.0) < sat_guard_adu]
    if len(pts) < poly_deg + 2:
        return {"status": "TOO_FEW_POINTS", "n_points": len(pts)}

    # ① 기준노출 드리프트 정규화
    refs = [p.get("ref_S") for p in pts]
    ref_norm = all(r is not None and r > 0 for r in refs)
    if ref_norm:
        ref0 = float(np.median(np.asarray(refs, dtype=float)))
        for p in pts:
            p["ref_ratio"] = float(p["ref_S"] / ref0)
            p["S_norm"] = p["S"] / p["ref_ratio"]
    else:
        for p in pts:
            p["ref_ratio"] = 1.0
            p["S_norm"] = p["S"]

    t = np.array([p["t"] for p in pts], dtype=float)
    S = np.array([p["S_norm"] for p in pts], dtype=float)

    # ② 초기 기준선: S(t) 가중 다항 적합 (w=1/S^2: 저신호 우세) — 1차부가
    #    이상 응답, 고차항이 비선형 성분을 흡수한다. 고차 t-다항의 공선성이
    #    기울기 오차를 키우므로 ③에서 NL 모델과 자기일치 반복으로 조인다.
    t0 = float(t.max())
    At = np.vander(t / t0, poly_deg + 1, increasing=True)
    sw = 1.0 / np.maximum(S, 1.0)
    ph, *_ = np.linalg.lstsq(At * sw[:, None], S * sw, rcond=None)
    tpoly = [float(ph[k]) / t0 ** k for k in range(poly_deg + 1)]
    p0, p1 = tpoly[0], tpoly[1]
    if p1 <= 0:
        return {"status": "BAD_FIT", "n_points": len(pts)}

    # ③ 자기일치 반복: NL(S) 모델(절편+원점통과 2차; 절편 = 기준선 오차분)을
    #    적합해 데이터를 선형화한 뒤, 전체 점으로 순수 직선 S_lin = p0 + p1 t
    #    (shot-noise 가중 w=1/S)을 다시 적합한다. 절편항은 기준선에 흡수되어
    #    NL(0)=0 물리 제약이 유지된다.
    s0 = float(S.max())
    x = S / s0
    nl_deg = 2
    B0 = np.column_stack([x ** k for k in range(0, nl_deg + 1)])
    lw = 1.0 / np.sqrt(np.maximum(S, 1.0))
    Al = np.column_stack([np.ones_like(t), t])
    for _ in range(3):
        nl = S / (p0 + p1 * t) - 1.0
        ah, *_ = np.linalg.lstsq(B0, nl, rcond=None)
        S_lin = S / np.maximum(1.0 + B0 @ ah, 1e-3)      # 선형화된 신호
        (p0, p1), *_ = np.linalg.lstsq(Al * lw[:, None], S_lin * lw,
                                       rcond=None)
        if p1 <= 0:
            return {"status": "BAD_FIT", "n_points": len(pts)}
    rate, dt = p1, p0 / p1
    fit_lin = p0 + p1 * t
    nl = S / fit_lin - 1.0
    Bn = np.column_stack([x ** k for k in range(1, nl_deg + 1)])
    ah, *_ = np.linalg.lstsq(Bn, nl, rcond=None)
    nl_a = [float(ah[k - 1]) / s0 ** k for k in range(1, nl_deg + 1)]

    # ④ LINMAX: 모델 |NL|이 기준을 처음 넘는 지점 직전 (저->고 스캔)
    grid = np.linspace(1.0, S.max(), 4096)
    nl_grid = np.zeros_like(grid)
    for k, a in enumerate(nl_a, start=1):
        nl_grid += a * grid ** k
    linmax, linnote = [], []
    for lim in nl_limits:
        bad = np.abs(nl_grid) > lim
        if not bad.any():
            linmax.append(float(S.max()))
            linnote.append("ramp-limited")
        else:
            i = int(np.argmax(bad))
            linmax.append(float(grid[max(i - 1, 0)]))
            linnote.append("measured" if i > 0 else "below-range")

    # ⑤ linearizer: 비율 S_true/S_meas 다항 — C0=1 고정 (S->0에서 보정계수
    #    1, NL(0)=0 물리 제약 유지; 자유 절편은 별도 측정되는 gain과 퇴화).
    #    shot-noise 가중 w ~ S (Var(ratio) ∝ 1/(g·S): 저신호 비율 잡음 억제).
    ratio = fit_lin / S
    Ac = np.column_stack([x ** k for k in range(1, poly_deg + 1)])
    cw = np.sqrt(np.maximum(S, 1.0))
    ch, *_ = np.linalg.lstsq(Ac * cw[:, None], (ratio - 1.0) * cw, rcond=None)
    lin_c = [1.0] + [float(ch[k - 1]) / s0 ** k
                     for k in range(1, poly_deg + 1)]
    corr_fac = np.zeros_like(S)
    for k, c in enumerate(lin_c):
        corr_fac += c * S ** k
    nl_after = (S * corr_fac) / fit_lin - 1.0
    valid = S <= linmax[-1] * (1.0 + 1e-9)      # 유효범위(최대 기준의 LINMAX)
    if not valid.any():
        valid = np.ones_like(S, dtype=bool)
    max_resid_after = float(np.max(np.abs(nl_after[valid])))

    for p, nli, nla, sn in zip(pts, nl, nl_after, S):
        p["nl"] = float(nli)
        p["nl_after"] = float(nla)
        p["S_norm"] = float(sn)

    rr = np.array([p["ref_ratio"] for p in pts])
    return {
        "status": "OK",
        "n_points": len(pts),
        "ref_norm": bool(ref_norm),
        "ref_drift_pct": float(np.ptp(rr) * 100.0) if ref_norm else 0.0,
        "rate_adu_s": float(rate),
        "dt_s": float(dt),
        "tpoly": tpoly,
        "nl_a": nl_a,
        "nl_max_pct": float(np.max(np.abs(nl)) * 100.0),
        "nl_rms_pct": float(np.std(nl) * 100.0),
        "nl_limits": list(nl_limits),
        "linmax_05_adu": linmax[0],
        "linmax_05_note": linnote[0],
        "linmax_10_adu": linmax[-1],
        "linmax_10_note": linnote[-1],
        "lin_c": lin_c,
        "poly_deg": int(poly_deg),
        "max_resid_pct_after": max_resid_after * 100.0,
        "s_min_adu": float(S.min()),
        "s_max_adu": float(S.max()),
        "points": pts,
    }


def dynamic_range(linmax_adu: float, gain: float, rn_e: float) -> dict:
    """DR = LINMAX(bias 차감 ADU)·g / RN_e, DR_bit = log2(DR) (계획서 §9)."""
    if linmax_adu <= 0 or gain <= 0 or rn_e <= 0:
        return {"dr": 0.0, "dr_bit": 0.0}
    dr = float(linmax_adu * gain / rn_e)
    return {"dr": dr, "dr_bit": float(np.log2(dr))}


# -- 캠페인 러너 (순수 함수 + 아래 CLI) -----------------------------------

def run_linearity(flat_paths: list, outdir, campaign: str,
                  ref_paths: list | None = None,
                  bias_paths: list | None = None,
                  roi=ROI, ovsc=OVSC_REAL, poly_deg: int = POLY_DEG,
                  sat_guard_adu: float = SAT_GUARD_ADU,
                  config: str = "",
                  ampchar: dict | None = None) -> dict:
    """램프 세트 전체 처리: 앰프별 fit_ramp + PNG/CSV 산출.

    ampchar: {EXTNAME: {'gain', 'rn_e'}} — DR_BIT 계산용 실측 GAIN/RDNOISE
    주입(load_ampchar 참조). 없으면 L0 헤더값(placeholder일 수 있음)을 쓰고,
    둘 다 무효(<=0)이면 DR_BIT는 NaN으로 기록한다(0.0 = 미측정 혼동 방지).

    반환: {'results': {ext: fit_ramp dict}, 'rows': CSV 행, 'csv': 경로,
    'summary_png': 경로, 'amp_pngs': {ext: 경로}}.
    """
    from pathlib import Path
    flat_paths = sorted(flat_paths, key=str)
    if not flat_paths:
        raise ValueError("no flat frames")
    with open_l0(flat_paths[0]) as e0:
        extnames = list(e0.amp_names)
        date = str(e0.primary.get("DATE-OBS", "")).strip()
        hdr = {ext: {"ampid": int(e0.hdul[ext].header.get("AMPID", 0) or 0),
                     "gain": float(e0.hdul[ext].header.get("GAIN", 0) or 0),
                     "rn_e": float(e0.hdul[ext].header.get("RDNOISE", 0) or 0)}
               for ext in extnames}
    if ampchar:
        for ext in extnames:
            ac = ampchar.get(ext) or {}
            if float(ac.get("gain", 0) or 0) > 0:
                hdr[ext]["gain"] = float(ac["gain"])
            if float(ac.get("rn_e", 0) or 0) > 0:
                hdr[ext]["rn_e"] = float(ac["rn_e"])

    meas = _measure_series(flat_paths, extnames, roi, ovsc)
    refm = (_measure_series(sorted(ref_paths, key=str), extnames, roi, ovsc)
            if ref_paths else None)

    # raw ADU 환산 페데스탈: S에서 실제로 차감한 양(프레임별 오버스캔
    # 중앙값)의 캠페인 중앙값으로 통일한다. --bias 세트는 이미지 영역
    # bias 준위 측정용이며, 오버스캔과의 차이를 IMG_MINUS_OVSC_ADU로
    # 별도 기록한다 (환산에 섞으면 이미지-오버스캔 오프셋만큼 어긋남).
    bias_adu = {e: float(np.median([m["ovsc_adu"] for m in meas[e]]))
                for e in extnames}
    img_bias_adu: dict = {}
    if bias_paths:
        levels: dict = {e: [] for e in extnames}
        for p in sorted(bias_paths, key=str):
            with open_l0(p) as exp:
                for ext in extnames:
                    levels[ext].append(
                        float(np.median(roi_raw(exp, ext, roi=roi))))
        img_bias_adu = {e: float(np.median(levels[e])) for e in extnames}

    out = Path(outdir) / "linearity"
    (out / "amps").mkdir(parents=True, exist_ok=True)

    # linearizer 계수 컬럼: poly_deg에 맞춰 동적 생성 (기본 C0..C3;
    # poly_deg > 3 이어도 계수가 잘리지 않는다)
    ncoef = max(4, int(poly_deg) + 1)
    coef_cols = ["C%d" % k for k in range(ncoef)]

    results, rows, amp_pngs = {}, [], {}
    for ext in extnames:
        pts = meas[ext]
        if refm is not None:
            ref_s = np.array([m["S"] for m in refm[ext]], dtype=float)
            nf, nr = len(pts), len(ref_s)
            pos_f = np.linspace(0.0, 1.0, nf) if nf > 1 else np.zeros(1)
            pos_r = np.linspace(0.0, 1.0, nr) if nr > 1 else np.zeros(1)
            for m, r in zip(pts, np.interp(pos_f, pos_r, ref_s)):
                m["ref_S"] = float(r)
        else:
            for m in pts:
                m["ref_S"] = None
        res = fit_ramp(pts, poly_deg=poly_deg, sat_guard_adu=sat_guard_adu)
        results[ext] = res
        b = bias_adu[ext]
        h = hdr[ext]
        if res["status"] == "OK":
            if h["gain"] > 0 and h["rn_e"] > 0:
                drng = dynamic_range(res["linmax_10_adu"], h["gain"],
                                     h["rn_e"])
                dr_bit = round(drng["dr_bit"], 2)
            else:   # GAIN/RDNOISE 미확보: 0.0(=미측정 혼동) 대신 NaN
                dr_bit = float("nan")
            status = "OK"
            if res["linmax_10_note"] != "measured":
                status += ";" + res["linmax_10_note"].upper()
            cs = res["lin_c"] + [0.0] * (ncoef - len(res["lin_c"]))
            row = {
                "EXTNAME": ext, "AMPID": h["ampid"],
                "MODEL": "poly%d" % res["poly_deg"],
            }
            row.update({col: "%.8e" % v for col, v in zip(coef_cols, cs)})
            row.update({
                "VALID_MIN": round(res["s_min_adu"] + b),
                "VALID_MAX": round(res["linmax_10_adu"] + b),
                "MAX_RESID_PCT_AFTER": round(res["max_resid_pct_after"], 4),
                "LINMAX05_RAW": round(res["linmax_05_adu"] + b),
                "LINMAX10_RAW": round(res["linmax_10_adu"] + b),
                "NL_MAX_PCT": round(res["nl_max_pct"], 3),
                "NL_RMS_PCT": round(res["nl_rms_pct"], 4),
                "DT_S": round(res["dt_s"], 4),
                "RATE_ADU_S": round(res["rate_adu_s"], 2),
                "DR_BIT": dr_bit,
                "BIAS_ADU": round(b, 1),
                "STATUS": status,
            })
        else:
            row = {"EXTNAME": ext, "AMPID": h["ampid"], "MODEL": ""}
            row.update({col: "" for col in coef_cols})
            row.update({
                "VALID_MIN": -1, "VALID_MAX": -1,
                "MAX_RESID_PCT_AFTER": -1, "LINMAX05_RAW": -1,
                "LINMAX10_RAW": -1, "NL_MAX_PCT": -1, "NL_RMS_PCT": -1,
                "DT_S": 0, "RATE_ADU_S": 0, "DR_BIT": float("nan"),
                "BIAS_ADU": round(b, 1),
                "STATUS": res["status"],
            })
        row["IMG_MINUS_OVSC_ADU"] = (round(img_bias_adu[ext] - b, 2)
                                     if ext in img_bias_adu else "")
        row.update({"CAMPAIGN": campaign, "DATE": date, "CONFIG": config})
        rows.append(row)
        png = out / "amps" / ("%s_linearity.png" % ext)
        _plot_amp_page(ext, res, campaign, png)
        amp_pngs[ext] = str(png)

    rows.sort(key=lambda r: r["AMPID"])
    csv_path = out / ("linearity_coeff_%s.csv" % campaign)
    _write_csv(rows, csv_path)
    summary_png = out / "linearity_summary.png"
    _plot_summary(rows, campaign, summary_png)
    return {"results": results, "rows": rows, "csv": str(csv_path),
            "summary_png": str(summary_png), "amp_pngs": amp_pngs}


def _write_csv(rows: list[dict], path) -> None:
    import csv
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write("# linearizer: S_true = S_meas*(C0 + C1*S + ... + Cn*S^n),"
                 " C0 = 1 fixed, with S = overscan-subtracted ADU;"
                 " VALID_MIN/VALID_MAX and LINMAX*_RAW are raw ADU"
                 " (pedestal = campaign-median overscan level = BIAS_ADU,"
                 " the quantity actually subtracted from S);"
                 " VALID_MAX = LINMAX(|NL|<=1%)\n")
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def load_ampchar(path) -> dict:
    """amp characterization CSV (results/README.md §1 스키마) ->
    {EXTNAME: {'gain' [e-/ADU], 'rn_e' [e-]}}. 무효(<=0/결측) 값은 생략."""
    import csv
    out: dict = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            ext = str(row.get("EXTNAME", "")).strip()
            if not ext:
                continue
            rec = {}
            for key, col in (("gain", "GAIN"), ("rn_e", "RDNOISE")):
                try:
                    v = float(row.get(col, ""))
                except (TypeError, ValueError):
                    continue
                if v > 0:
                    rec[key] = v
            if rec:
                out[ext] = rec
    return out


# -- 플롯 (matplotlib은 여기서만 import) ----------------------------------

def _plot_amp_page(ext: str, res: dict, campaign: str, png_path) -> None:
    """앰프별 진단 페이지: S vs t / ref 드리프트 / 비선형 잔차 /
    보정 곡선 / 보정 후 잔차 / 수치 요약."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.2))
    fig.suptitle("%s  %s  linearity" % (campaign, ext), fontsize=12)
    if res.get("status") != "OK":
        for ax in axes.ravel():
            ax.axis("off")
        axes[0, 0].text(0.05, 0.5, "status: %s" % res.get("status"),
                        fontsize=14, color="red")
        fig.savefig(png_path, dpi=120)
        plt.close(fig)
        return

    pts = res["points"]
    t = np.array([p["t"] for p in pts])
    S = np.array([p["S_norm"] for p in pts])
    nl = np.array([p["nl"] for p in pts]) * 100.0
    nla = np.array([p["nl_after"] for p in pts]) * 100.0
    rr = np.array([p["ref_ratio"] for p in pts])
    rate, dt = res["rate_adu_s"], res["dt_s"]
    lm05, lm10 = res["linmax_05_adu"], res["linmax_10_adu"]
    sgrid = np.linspace(max(S.min(), 1.0), S.max(), 400)

    ax = axes[0, 0]     # S vs t + linear fit
    ax.plot(t, S, "o", ms=4, color="tab:blue", label="data")
    tt = np.linspace(0.0, t.max() * 1.05, 100)
    ax.plot(tt, rate * (tt + dt), "-", color="tab:orange", lw=1,
            label="R(t+dt)  R=%.1f ADU/s" % rate)
    ax.set_xlabel("exposure time [s]")
    ax.set_ylabel("signal S [ADU, bias-sub]")
    ax.legend(fontsize=7)
    ax.set_title("ramp + linear fit", fontsize=9)

    ax = axes[0, 1]     # ref drift
    if res["ref_norm"]:
        ax.plot(np.arange(len(rr)), (rr - 1.0) * 100.0, "o-", ms=3,
                color="tab:green", lw=0.8)
        ax.axhline(0.0, color="gray", lw=0.7)
        ax.set_xlabel("sequence index")
        ax.set_ylabel("ref drift [%]")
        ax.set_title("lamp drift (ref/ref0 - 1), ptp=%.2f%%"
                     % res["ref_drift_pct"], fontsize=9)
    else:
        ax.axis("off")
        ax.text(0.1, 0.5, "no reference frames\n(drift not normalized)",
                fontsize=10)

    ax = axes[0, 2]     # nonlinearity residual
    ax.plot(S, nl, "o", ms=4, color="tab:blue")
    nlg = np.zeros_like(sgrid)
    for k, a in enumerate(res["nl_a"], start=1):
        nlg += a * sgrid ** k
    ax.plot(sgrid, nlg * 100.0, "-", color="tab:orange", lw=1)
    for lim, ls in ((0.5, ":"), (1.0, "--")):
        ax.axhline(+lim, color="gray", ls=ls, lw=0.8)
        ax.axhline(-lim, color="gray", ls=ls, lw=0.8)
    ax.axvline(lm05, color="tab:red", ls=":", lw=1,
               label="LINMAX 0.5%%=%.0f" % lm05)
    ax.axvline(lm10, color="tab:red", ls="--", lw=1,
               label="LINMAX 1%%=%.0f" % lm10)
    ax.set_xlabel("S [ADU]")
    ax.set_ylabel("NL = S/fit - 1 [%]")
    ax.legend(fontsize=7)
    ax.set_title("nonlinearity residual", fontsize=9)

    ax = axes[1, 0]     # correction curve
    ax.plot(S, rate * (t + dt) / S, "o", ms=4, color="tab:blue",
            label="measured fit/S")
    cg = np.zeros_like(sgrid)
    for k, c in enumerate(res["lin_c"]):
        cg += c * sgrid ** k
    ax.plot(sgrid, cg, "-", color="tab:orange", lw=1,
            label="poly%d model" % res["poly_deg"])
    ax.set_xlabel("S [ADU]")
    ax.set_ylabel("S_true / S_meas")
    ax.legend(fontsize=7)
    ax.set_title("linearizer correction curve", fontsize=9)

    ax = axes[1, 1]     # residual after correction
    ax.plot(S, nla, "o", ms=4, color="tab:blue")
    ax.axhline(0.0, color="gray", lw=0.7)
    for lim in (+0.1, -0.1):
        ax.axhline(lim, color="gray", ls=":", lw=0.8)
    ax.axvline(lm10, color="tab:red", ls="--", lw=1)
    ax.set_xlabel("S [ADU]")
    ax.set_ylabel("residual after corr. [%]")
    ax.set_title("after linearizer (max %.3f%% in valid range)"
                 % res["max_resid_pct_after"], fontsize=9)

    ax = axes[1, 2]     # numbers
    ax.axis("off")
    lines = [
        "n_points        : %d" % res["n_points"],
        "ref normalized  : %s (ptp %.2f%%)" % (res["ref_norm"],
                                               res["ref_drift_pct"]),
        "rate            : %.2f ADU/s" % rate,
        "dt (shutter)    : %+.4f s (reference)" % dt,
        "max |NL|        : %.3f %%" % res["nl_max_pct"],
        "LINMAX 0.5%%     : %.0f ADU (%s)" % (lm05, res["linmax_05_note"]),
        "LINMAX 1.0%%     : %.0f ADU (%s)" % (lm10, res["linmax_10_note"]),
        "linearizer      : poly%d" % res["poly_deg"],
        "resid after corr: %.3f %% (max)" % res["max_resid_pct_after"],
    ]
    ax.text(0.02, 0.95, "\n".join(lines), family="monospace", fontsize=9,
            va="top")

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(png_path, dpi=120)
    plt.close(fig)


def _plot_summary(rows: list[dict], campaign: str, png_path) -> None:
    """카메라 요약: LINMAX(1%)·최대 비선형·dt·DR_bit vs AMPID (outlier 빨강)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    metrics = [
        ("LINMAX10_RAW", "LINMAX |NL|<=1% [raw ADU]"),
        ("NL_MAX_PCT", "max |NL| on ramp [%]"),
        ("DT_S", "dt shutter offset [s] (ref.)"),
        ("DR_BIT", "dynamic range [bit]"),
    ]
    amps = np.array([r["AMPID"] for r in rows], dtype=float)
    fig, axes = plt.subplots(len(metrics), 1, figsize=(11, 9.5), sharex=True)
    fig.suptitle("%s  linearity summary (%d amps)" % (campaign, len(rows)),
                 fontsize=12)
    for ax, (key, label) in zip(axes, metrics):
        v = np.array([float(r[key]) if str(r["STATUS"]).startswith("OK")
                      else np.nan for r in rows])
        ok = np.isfinite(v)
        ax.plot(amps[ok], v[ok], "o", ms=4, color="tab:blue")
        if ok.any():
            med = float(np.median(v[ok]))
            mad = mad_std(v[ok])
            ax.axhline(med, color="gray", ls="--", lw=0.7)
            if mad > 0:
                bad = ok & (np.abs(v - med) > 3.0 * mad)
                if bad.any():
                    ax.plot(amps[bad], v[bad], "o", ms=6, color="red",
                            label="outlier (>3 MAD)")
                    ax.legend(fontsize=7)
        if (~ok).any():
            for a in amps[~ok]:
                ax.axvline(a, color="red", lw=0.6, alpha=0.4)
        ax.set_ylabel(label, fontsize=8)
        ax.grid(alpha=0.25, lw=0.4)
    axes[-1].set_xlabel("AMPID")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(png_path, dpi=120)
    plt.close(fig)


# -- CLI ------------------------------------------------------------------

def _parse_roi(s: str):
    """'y0:y1,x0:x1' -> (slice, slice)."""
    ys, xs = s.split(",")
    y0, y1 = (int(v) for v in ys.split(":"))
    x0, x1 = (int(v) for v in xs.split(":"))
    return (slice(y0, y1), slice(x0, x1))


def main(argv=None) -> int:
    import argparse
    import glob as globmod
    ap = argparse.ArgumentParser(
        description="Exposure-ramp linearity + linearizer (lab campaign)")
    ap.add_argument("--flats", required=True, help="ramp flat glob")
    ap.add_argument("--refs", help="reference-exposure flat glob (drift norm)")
    ap.add_argument("--bias", help="bias frame glob (image-area bias level "
                                   "-> IMG_MINUS_OVSC_ADU diagnostic)")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--config", default="",
                    help="Archon config version recorded in the CONFIG column")
    ap.add_argument("--ampchar", default=None,
                    help="amp characterization CSV (EXTNAME/GAIN/RDNOISE) "
                         "for measured DR_BIT; without it the L0 header "
                         "placeholders are used")
    ap.add_argument("--roi", help="ROI override 'y0:y1,x0:x1' (default core.ROI)")
    ap.add_argument("--ovsc", help="overscan cols override 'x0:x1'")
    ap.add_argument("--sat-guard", type=float, default=SAT_GUARD_ADU,
                    help="drop frames with ROI p99.9 above this raw ADU")
    args = ap.parse_args(argv)

    flats = sorted(globmod.glob(args.flats))
    if not flats:
        print("ERROR: no flats match %r" % args.flats)
        return 1
    refs = sorted(globmod.glob(args.refs)) if args.refs else None
    biases = sorted(globmod.glob(args.bias)) if args.bias else None
    roi = _parse_roi(args.roi) if args.roi else ROI
    if args.ovsc:
        x0, x1 = (int(v) for v in args.ovsc.split(":"))
        ovsc = slice(x0, x1)
    else:
        ovsc = OVSC_REAL

    ampchar = load_ampchar(args.ampchar) if args.ampchar else None
    out = run_linearity(flats, args.outdir, args.campaign, ref_paths=refs,
                        bias_paths=biases, roi=roi, ovsc=ovsc,
                        sat_guard_adu=args.sat_guard, config=args.config,
                        ampchar=ampchar)
    n_ok = sum(1 for r in out["rows"] if str(r["STATUS"]).startswith("OK"))
    print("[%s] linearity: %d/%d amps OK -> %s"
          % (args.campaign, n_ok, len(out["rows"]), out["csv"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

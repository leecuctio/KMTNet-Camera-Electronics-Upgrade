"""Photon Transfer Curve gain with pair ratio-normalization and a
curvature (brighter-fatter) model.

Per flat pair at one level (review prescriptions applied):
    r = (m1 - bias) / (m2 - bias)            pair normalization
    reject pair if |r - 1| > drift_max        lamp-drift guard
    D = (F1 - bias) - r (F2 - bias)
    V = clipped_var(D)/2 - RN^2 (1+r^2)/2     [ADU^2]
    S = ((m1 - bias) + (m2 - bias)) / 2       [ADU, bias-subtracted]

Fit over the usable range (S_min < S, p99.9 < sat guard):
    V = S/g - a S^2        ->  gain g [e-/ADU], curvature a [1/ADU]
A windowed straight line would bias g by the arbitrary cut; the curvature
term absorbs the brighter-fatter/nonlinearity bend (Astier et al. 2019
motivates the S^2 term).

Optional diagnostics hooks (backward compatible): ``ptc_points`` accepts a
``roi`` slice override (reduced synthetic geometry) and an ``ovsc`` column
slice — when given, the per-frame serial-overscan medians (``oscan1``,
``oscan2``) are recorded on each point for the overscan-vs-signal
common-mode (CMRR) diagnostic in diagnostics.py.
"""
from __future__ import annotations

import numpy as np

from .core import ROI, clipped_var, roi_raw, unsigned_from_stored

DRIFT_MAX = 0.01
S_MIN_ADU = 300.0
SAT_GUARD_ADU = 60000.0     # raw p99.9 above this: exclude from the fit
                            # (physical 0..65535 code axis; ADC clip = 65535)
# Clipping below the static guard (e.g. legacy-converted frames saturate
# around 29-30 k on the physical axis) shows up as a variance collapse:
# reject points whose relative fit residual is more negative than
# max(COLLAPSE_NSIG * robust sigma, COLLAPSE_MIN).
COLLAPSE_NSIG = 4.0
COLLAPSE_MIN = 0.04         # at least 4% variance suppression required
COLLAPSE_PRE = 0.25         # median-gain pre-screen: V below 75% of S/g_med
                            # (a real curvature bend stays well above this)


def ovsc_section(exp, ext: str, rows, ovsc) -> np.ndarray:
    """Overscan columns for an arbitrary ``ovsc`` slice, physical unsigned
    raw ADU (float64).

    core.ovsc_raw is pinned to core.OVSC_REAL, so reduced synthetic
    geometries need a direct section read; core.unsigned_from_stored
    applies the header BZERO/BSCALE (same scale as core.roi_raw).
    """
    hdu = exp.hdul[ext]
    return unsigned_from_stored(hdu.section[rows, ovsc], hdu.header)


def ptc_points(flat_pairs: list[tuple], ext: str, bias_adu: float,
               rn_adu: float, roi=ROI, ovsc=None) -> list[dict]:
    """[{S, V, r, exptime, p999_raw}] for one amp over all usable pairs.

    roi   ROI slices for the pixel statistics (default: core.ROI).
    ovsc  optional overscan column slice; when given each point also
          carries 'oscan1'/'oscan2' (per-frame overscan medians, raw ADU).
    """
    pts = []
    for e1, e2 in flat_pairs:
        a1 = roi_raw(e1, ext, roi=roi)
        a2 = roi_raw(e2, ext, roi=roi)
        m1 = float(np.mean(a1)) - bias_adu
        m2 = float(np.mean(a2)) - bias_adu
        if m1 <= 0 or m2 <= 0:
            continue
        r = m1 / m2
        d = (a1 - bias_adu) - r * (a2 - bias_adu)
        v = clipped_var(d) / 2.0 - rn_adu ** 2 * (1 + r ** 2) / 2.0
        pt = {
            "S": (m1 + m2) / 2.0,
            "V": v,
            "r": r,
            "exptime": float(e1.primary.get("EXPTIME", 0) or 0),
            "p999_raw": float(np.percentile(a1, 99.9)),
        }
        if ovsc is not None:
            pt["oscan1"] = float(np.median(ovsc_section(e1, ext, roi[0], ovsc)))
            pt["oscan2"] = float(np.median(ovsc_section(e2, ext, roi[0], ovsc)))
        pts.append(pt)
    return pts


def fit_gain(pts: list[dict], drift_max: float = DRIFT_MAX,
             sat_guard_adu: float = SAT_GUARD_ADU) -> dict:
    """Weighted LSQ of V = S/g - a S^2 over usable points.

    sat_guard_adu  static raw-p99.9 exclusion threshold (physical code
                   axis).  Clipping BELOW this threshold (e.g. the
                   ~29-30 k physical-ADU ceiling of legacy-converted
                   frames, which the 60 k constant cannot see) is caught
                   adaptively: after each fit, points whose variance sits
                   far below the model (relative residual more negative
                   than max(COLLAPSE_NSIG*MAD, COLLAPSE_MIN)) are rejected
                   and the fit repeated — a clip suppresses pair variance
                   long before it flattens the mean signal.
    """
    use = [p for p in pts
           if abs(p["r"] - 1) <= drift_max and p["S"] > S_MIN_ADU
           and p["p999_raw"] < sat_guard_adu and p["V"] > 0]
    if len(use) < 3:
        return {"gain": 0.0, "gain_err": 0.0, "curv_a": 0.0,
                "n_pts": len(use), "n_rej": len(pts) - len(use),
                "status": "TOO_FEW_PAIRS"}
    S = np.array([p["S"] for p in use])
    V = np.array([p["V"] for p in use])
    A_all = np.column_stack([S, -S ** 2])

    def _wfit(keep):
        # weights ~ 1/Var(V); Var(V) ~ 2 V^2 / N_pix (N cancels in rel. wts)
        w = 1.0 / np.maximum(V[keep], 1.0) ** 2
        A = A_all[keep]
        Aw = A * w[:, None]
        cov = np.linalg.inv(A.T @ Aw)
        return cov @ (Aw.T @ V[keep]), cov, w

    keep = np.ones(len(use), dtype=bool)
    # pre-screen with the robust per-point gain: a grossly collapsed point
    # (fully clipped pair) would otherwise dominate the 1/V^2-weighted fit
    # and hide itself in the residuals.
    g_med = float(np.median(S / V))
    pre = V * g_med / S - 1.0 < -COLLAPSE_PRE
    if pre.any() and int((~pre).sum()) >= 3:
        keep &= ~pre
    c, cov, w = _wfit(keep)
    for _ in range(5):
        # variance-collapse rejection (clip/saturation missed by the guard)
        model = A_all @ c
        rr = V / np.maximum(np.abs(model), 1.0) - 1.0
        med = float(np.median(rr[keep]))
        sig = float(1.4826 * np.median(np.abs(rr[keep] - med)))
        bad = keep & (rr < -max(COLLAPSE_NSIG * sig, COLLAPSE_MIN))
        if not bad.any() or int(keep.sum() - bad.sum()) < 3:
            break
        keep &= ~bad
        c, cov, w = _wfit(keep)
    n_pts = int(keep.sum())
    n_rej = len(pts) - n_pts
    resid = V[keep] - A_all[keep] @ c
    dof = max(n_pts - 2, 1)
    scale = float((w * resid ** 2).sum() / dof)
    err = np.sqrt(np.diag(cov) * scale)
    inv_g, a = float(c[0]), float(c[1])
    if inv_g <= 0:
        return {"gain": 0.0, "gain_err": 0.0, "curv_a": a,
                "n_pts": n_pts, "n_rej": n_rej, "status": "BAD_FIT"}
    gain = 1.0 / inv_g
    return {
        "gain": gain,
        "gain_err": float(err[0]) * gain ** 2,
        "curv_a": a,
        "n_pts": n_pts,
        "n_rej": n_rej,
        "resid_rms_pct": float(np.sqrt(np.mean(
            (resid / np.maximum(V[keep], 1)) ** 2)) * 100.0),
        "status": "OK",
    }

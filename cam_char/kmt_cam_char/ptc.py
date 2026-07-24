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
"""
from __future__ import annotations

import numpy as np

from .core import clipped_var, roi_raw

DRIFT_MAX = 0.01
S_MIN_ADU = 300.0
SAT_GUARD_ADU = 60000.0     # raw p99.9 above this: exclude from the fit


def ptc_points(flat_pairs: list[tuple], ext: str, bias_adu: float,
               rn_adu: float) -> list[dict]:
    """[{S, V, r, exptime, p999_raw}] for one amp over all usable pairs."""
    pts = []
    for e1, e2 in flat_pairs:
        a1 = roi_raw(e1, ext)
        a2 = roi_raw(e2, ext)
        m1 = float(np.mean(a1)) - bias_adu
        m2 = float(np.mean(a2)) - bias_adu
        if m1 <= 0 or m2 <= 0:
            continue
        r = m1 / m2
        d = (a1 - bias_adu) - r * (a2 - bias_adu)
        v = clipped_var(d) / 2.0 - rn_adu ** 2 * (1 + r ** 2) / 2.0
        pts.append({
            "S": (m1 + m2) / 2.0,
            "V": v,
            "r": r,
            "exptime": float(e1.primary.get("EXPTIME", 0) or 0),
            "p999_raw": float(np.percentile(a1, 99.9)),
        })
    return pts


def fit_gain(pts: list[dict], drift_max: float = DRIFT_MAX) -> dict:
    """Weighted LSQ of V = S/g - a S^2 over usable points."""
    use = [p for p in pts
           if abs(p["r"] - 1) <= drift_max and p["S"] > S_MIN_ADU
           and p["p999_raw"] < SAT_GUARD_ADU and p["V"] > 0]
    n_rej = len(pts) - len(use)
    if len(use) < 3:
        return {"gain": 0.0, "gain_err": 0.0, "curv_a": 0.0,
                "n_pts": len(use), "n_rej": n_rej, "status": "TOO_FEW_PAIRS"}
    S = np.array([p["S"] for p in use])
    V = np.array([p["V"] for p in use])
    # weights ~ 1/Var(V); Var(V) ~ 2 V^2 / N_pix (N cancels in relative wts)
    w = 1.0 / np.maximum(V, 1.0) ** 2
    A = np.column_stack([S, -S ** 2])
    Aw = A * w[:, None]
    cov = np.linalg.inv(A.T @ Aw)
    c = cov @ (Aw.T @ V)
    resid = V - A @ c
    dof = max(len(use) - 2, 1)
    scale = float((w * resid ** 2).sum() / dof)
    err = np.sqrt(np.diag(cov) * scale)
    inv_g, a = float(c[0]), float(c[1])
    if inv_g <= 0:
        return {"gain": 0.0, "gain_err": 0.0, "curv_a": a,
                "n_pts": len(use), "n_rej": n_rej, "status": "BAD_FIT"}
    gain = 1.0 / inv_g
    return {
        "gain": gain,
        "gain_err": float(err[0]) * gain ** 2,
        "curv_a": a,
        "n_pts": len(use),
        "n_rej": n_rej,
        "resid_rms_pct": float(np.sqrt(np.mean((resid / np.maximum(V, 1)) ** 2))
                               * 100.0),
        "status": "OK",
    }

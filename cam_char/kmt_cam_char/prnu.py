"""PRNU (pixel response non-uniformity) and gain/level stability from the
repeat flat set (same exposure, ~19 frames).

PRNU: bias-subtracted, per-frame mean-normalized frames are median-stacked
(shot noise and CRs suppressed), the large-scale illumination surface is
removed with the pipeline's block-median smoother, and the small-scale RMS
is the PRNU. Electronics-only changes should leave PRNU intact — a big
before/after difference flags processing or assembly problems, not CCDs.

Stability: single-point PTC gain per consecutive frame pair of the repeat
set (g = S/V; illumination-drift-free by pair normalization) and the bias
sequence level trend -> within-night drift metrics.
"""
from __future__ import annotations

import numpy as np

from .core import clipped_var, mad_std, roi_raw
# core.py already put mef_pipeline on sys.path
from kmt_ceu_preproc.background import block_smooth  # noqa: E402

PRNU_SMOOTH_BOX = 64


def measure_prnu(repeat_exps: list, extname: str, bias_adu: float) -> dict:
    frames = []
    for e in repeat_exps:
        a = roi_raw(e, extname) - bias_adu
        m = float(np.mean(a))
        if m <= 0:
            continue
        frames.append(a / m)
    n_used = len(frames)
    if n_used < 5:
        return {"status": "TOO_FEW_FRAMES", "n": n_used}
    stack = np.median(np.stack(frames), axis=0)
    del frames
    smooth = block_smooth(stack.astype(np.float32), PRNU_SMOOTH_BOX)
    resid = stack - smooth
    prnu = mad_std(resid)
    return {"status": "OK", "n": n_used,
            "prnu_pct": float(prnu * 100.0),
            "largescale_pp_pct": float(np.ptp(smooth) * 100.0)}


def gain_series(repeat_exps: list, extname: str, bias_adu: float,
                rn_adu: float) -> dict:
    """Single-point PTC gain per consecutive pair -> within-night stability."""
    gains = []
    for i in range(len(repeat_exps) - 1):
        a1 = roi_raw(repeat_exps[i], extname)
        a2 = roi_raw(repeat_exps[i + 1], extname)
        m1 = float(np.mean(a1)) - bias_adu
        m2 = float(np.mean(a2)) - bias_adu
        if m1 <= 0 or m2 <= 0 or abs(m1 / m2 - 1) > 0.02:
            continue
        r = m1 / m2
        v = clipped_var((a1 - bias_adu) - r * (a2 - bias_adu)) / 2.0 \
            - rn_adu ** 2 * (1 + r ** 2) / 2.0
        s = (m1 + m2) / 2.0
        if v > 0:
            gains.append(s / v)
    if len(gains) < 3:
        return {"status": "TOO_FEW_PAIRS", "n": len(gains)}
    g = np.array(gains)
    return {"status": "OK", "n": len(g),
            "gain_med": float(np.median(g)),
            "gain_stab_pct": float(100.0 * mad_std(g) / np.median(g))}

"""Illumination (dark-sky flat) correction.

Twilight/dome flats do not share the night sky's illumination pattern across
a wide field (scattered light, pupil vignetting), leaving a smooth
large-scale photometric error after flat division. The master illumination
frame (calib-illum) is the block-median-smoothed, sky-normalized response
built from flat-fielded science frames of *different pointings* — the
per-field stellar-density gradients (severe toward the bulge) largely cancel
in the median across fields, while the instrument's illumination pattern is
common to all of them. Application divides it out like a flat:

    SCI /= illum_plane        (chip median response = 1)

Guard: the plane is clamped to [0.5, 2.0]; an illumination correction
should be a few-percent surface, so values far from 1 mean a bad master."""
from __future__ import annotations

import numpy as np

from . import CalHistRow

ILLUM_CLAMP = (0.5, 2.0)


def divide_illum(sci: np.ndarray, var: np.ndarray | None,
                 extname: str, master) -> tuple[float, int]:
    """Divide by the illumination response (in place).
    Returns (max deviation |resp-1|, n pixels clamped)."""
    p = master.plane(extname)
    lo, hi = ILLUM_CLAMP
    n_clamped = int(np.count_nonzero((p < lo) | (p > hi)))
    if n_clamped:
        p = np.clip(p, lo, hi)
    sci /= p
    if var is not None:
        var /= p * p
    return float(np.max(np.abs(p - 1.0))), n_clamped


def illum_calhist(master, enabled: bool, max_dev: float = 0.0) -> CalHistRow:
    if not enabled:
        return CalHistRow("ILLUM", False, params="disabled")
    if master is None:
        return CalHistRow("ILLUM", False, params="no master illumination (skipped)")
    return CalHistRow("ILLUM", True, calfile=master.name, calver=master.calver,
                      params=f"smooth response division, max |resp-1| {max_dev:.4f}")

"""Fringe-pattern subtraction (DES/PS1/SkyMapper style).

The master fringe (calib-fringe) stores, per amp, the small-scale fringe
pattern as a *fraction of the sky level*, built from many flat-fielded
science frames of different pointings. At run time the pattern is scaled to
each frame and subtracted:

    SCI -= a * fringe_plane

The scale a is fitted by clipped least squares on the strong-pattern pixels
(theoretical expectation a ~ sky_e; the fit absorbs airglow-spectrum
variations night to night). Amps whose template amplitude is negligible are
skipped — on detectors without measurable fringing (deep-depletion e2v in V)
this step becomes a recorded no-op rather than added noise."""
from __future__ import annotations

import numpy as np

from .. import MASK_BAD, MASK_SAT
from . import CalHistRow

MIN_TEMPLATE_MAD = 1e-4   # fraction of sky below which the template is noise
MIN_FIT_PIXELS = 2000
SCALE_CLIP = 3.0
_EXCLUDE = MASK_BAD | MASK_SAT


def fringe_scale(sci: np.ndarray, fringe: np.ndarray, mask: np.ndarray | None,
                 sky_e: float) -> tuple[float, int]:
    """Clipped LSQ amplitude of `fringe` in `sci` [e-]; (scale, n_pixels)."""
    f = fringe.astype(np.float64)
    mad_f = 1.4826 * float(np.median(np.abs(f - np.median(f))))
    if mad_f < MIN_TEMPLATE_MAD:
        return 0.0, 0
    # strongest ~30% of the template carries the fit (percentile, not MAD:
    # a bounded pattern can have max|f| below k*MAD)
    strong = np.abs(f) >= max(float(np.percentile(np.abs(f), 70.0)), 1e-6)
    if mask is not None:
        strong &= (mask & _EXCLUDE) == 0
    n = int(np.count_nonzero(strong))
    if n < MIN_FIT_PIXELS:
        return 0.0, n
    fv = f[strong]
    sv = sci[strong].astype(np.float64)
    sv = sv - np.median(sv)
    a = 0.0
    good = np.ones(len(fv), dtype=bool)
    for _ in range(3):
        denom = float((fv[good] ** 2).sum())
        if denom <= 0:
            return 0.0, n
        a = float((sv[good] * fv[good]).sum() / denom)
        resid = sv - a * fv
        sig = 1.4826 * float(np.median(np.abs(resid - np.median(resid))))
        if sig <= 0:
            break
        good = np.abs(resid) <= SCALE_CLIP * sig
        if good.sum() < MIN_FIT_PIXELS // 2:
            break
    # physical range guard: fringing is a positive fraction of the sky signal
    return float(np.clip(a, 0.0, 3.0 * max(sky_e, 1.0))), n


def subtract_fringe(sci: np.ndarray, mask: np.ndarray | None, extname: str,
                    master, sky_e: float) -> tuple[bool, float]:
    """Scaled template subtraction (in place). Returns (applied, scale_e)."""
    f = master.plane(extname)
    scale, _n = fringe_scale(sci, f, mask, sky_e)
    if scale <= 0.0:
        return False, 0.0
    sci -= np.float32(scale) * f
    return True, scale


def fringe_calhist(master, chip_scales: dict[str, float] | None,
                   enabled: bool) -> CalHistRow:
    if not enabled:
        return CalHistRow("FRINGE", False, params="disabled")
    if master is None:
        return CalHistRow("FRINGE", False, params="no master fringe (skipped)")
    if not chip_scales:
        return CalHistRow("FRINGE", False, calfile=master.name, calver=master.calver,
                          params="template amplitude negligible on all amps")
    med = float(np.median(list(chip_scales.values())))
    return CalHistRow("FRINGE", True, calfile=master.name, calver=master.calver,
                      params=f"scaled subtraction, median scale {med:.1f} e-")

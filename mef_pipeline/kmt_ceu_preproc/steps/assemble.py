"""CCD assembly: place DATASEC-trimmed amp arrays at their CCDSEC positions.

CHIPFLP='None' in the CEU L0 packing, so assembly is pure placement -- no
flips. Amp boundary pixels are flagged MASK_SEAM and per-boundary seam
metrics (median of adjacent-column/row differences) are returned for QA."""
from __future__ import annotations

import warnings

import numpy as np

from .. import MASK_BAD, MASK_NONLIN, MASK_SAT, MASK_SEAM
from ..geometry import AmpGeom, ccd_shape, section_slices


def assemble_ccd(geoms: list[AmpGeom], planes: dict[str, np.ndarray],
                 dtype, fill=0) -> np.ndarray:
    out = np.full(ccd_shape(geoms), fill, dtype=dtype)
    for g in geoms:
        out[section_slices(g.ccdsec)] = planes[g.extname]
    return out


def seam_positions(geoms: list[AmpGeom]) -> tuple[list[int], list[int]]:
    """Internal amp boundaries as 0-based CCD indices of the right/upper side."""
    xs = sorted({g.ccdsec[0] - 1 for g in geoms if g.ccdsec[0] > 1})
    ys = sorted({g.ccdsec[2] - 1 for g in geoms if g.ccdsec[2] > 1})
    return xs, ys


SEAM_EXCLUDE_BITS = MASK_BAD | MASK_SAT | MASK_NONLIN
SEAM_SKIP = 1   # boundary columns/rows skipped (fixed-pattern edge artifacts)
SEAM_BAND = 4   # columns/rows averaged on each side


def _band_profile(sci: np.ndarray, mask: np.ndarray | None, band_slice: slice,
                  axis: int) -> np.ndarray:
    """Per-row (axis=1) or per-column (axis=0) median over a narrow band."""
    band = np.take(sci, range(*band_slice.indices(sci.shape[axis])), axis=axis)
    if mask is not None:
        mband = np.take(mask, range(*band_slice.indices(mask.shape[axis])), axis=axis)
        band = np.where((mband & SEAM_EXCLUDE_BITS) == 0, band, np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN slice (dead amp)
        return np.nanmedian(band.astype(np.float64), axis=axis)


def _masked_median_step(sci: np.ndarray, mask: np.ndarray | None,
                        pos: int, axis: int) -> float:
    """Median step across a boundary at index pos (first pixel of the upper/
    right side), measured between SEAM_BAND-wide bands that skip SEAM_SKIP
    edge pixels, so fixed-pattern edge-column artifacts (already MASK_SEAM
    flagged) do not masquerade as amp-level calibration errors."""
    lo = _band_profile(sci, mask, slice(pos - SEAM_SKIP - SEAM_BAND, pos - SEAM_SKIP), axis)
    hi = _band_profile(sci, mask, slice(pos + SEAM_SKIP, pos + SEAM_SKIP + SEAM_BAND), axis)
    diff = hi - lo
    good = np.isfinite(diff)
    if not good.any():
        # a fully-flagged side (e.g. dead amp): calibration seam unmeasurable
        return 0.0
    return float(np.median(diff[good]))


def seam_metrics(sci: np.ndarray, geoms: list[AmpGeom],
                 mask: np.ndarray | None = None) -> dict[str, float]:
    """Median step across each internal boundary (robust to sky gradients).
    Flagged pixels (bad columns, saturation) are excluded so the metric
    measures amp-level calibration mismatch, not detector cosmetics."""
    xs, ys = seam_positions(geoms)
    metrics = {}
    for x in xs:
        metrics[f"x{x + 1}"] = _masked_median_step(sci, mask, x, axis=1)
    for y in ys:
        metrics[f"y{y + 1}"] = _masked_median_step(sci, mask, y, axis=0)
    return metrics


def flag_seams(mask: np.ndarray, geoms: list[AmpGeom]) -> None:
    """Flag the one-pixel columns/rows on both sides of internal boundaries."""
    xs, ys = seam_positions(geoms)
    for x in xs:
        mask[:, x - 1:x + 1] |= MASK_SEAM
    for y in ys:
        mask[y - 1:y + 1, :] |= MASK_SEAM


WCS_COPY_KEYS = ("CTYPE1", "CTYPE2", "CRVAL1", "CRVAL2",
                 "CD1_1", "CD1_2", "CD2_1", "CD2_2", "RADECSYS", "EQUINOX")


def ccd_wcs_cards(ref_geom: AmpGeom, ref_header) -> list[tuple[str, object, str]]:
    """Approximate CCD-level WCS: the reference amp's WCS with CRPIX shifted
    from amp-local (DATASEC origin) to assembled CCD pixels."""
    cards = []
    for k in WCS_COPY_KEYS:
        if k in ref_header:
            cards.append((k, ref_header[k], "approximate WCS from L0"))
    dx = (ref_geom.ccdsec[0] - 1) - (ref_geom.datasec[0] - 1)
    dy = (ref_geom.ccdsec[2] - 1) - (ref_geom.datasec[2] - 1)
    if "CRPIX1" in ref_header:
        cards.append(("CRPIX1", float(ref_header["CRPIX1"]) + dx, "shifted to CCD pixels"))
    if "CRPIX2" in ref_header:
        cards.append(("CRPIX2", float(ref_header["CRPIX2"]) + dy, "shifted to CCD pixels"))
    if cards:
        cards.append(("WCSAPPRX", True, "WCS is approximate; L1 astrometry pending"))
    return cards

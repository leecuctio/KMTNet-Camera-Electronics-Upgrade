"""CCD assembly: place DATASEC-trimmed amp arrays at their CCDSEC positions.

CHIPFLP='None' in the CEU L0 packing, so assembly is pure placement -- no
flips. Amp boundary pixels are flagged MASK_SEAM and per-boundary seam
metrics (median of adjacent-column/row differences) are returned for QA."""
from __future__ import annotations

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


def _masked_median_step(a: np.ndarray, b: np.ndarray,
                        ma: np.ndarray | None, mb: np.ndarray | None) -> float:
    diff = a - b
    if ma is not None:
        good = ((ma & SEAM_EXCLUDE_BITS) == 0) & ((mb & SEAM_EXCLUDE_BITS) == 0)
        if not good.any():
            # a fully-flagged side (e.g. dead amp): calibration seam unmeasurable
            return 0.0
        diff = diff[good]
    return float(np.median(diff))


def seam_metrics(sci: np.ndarray, geoms: list[AmpGeom],
                 mask: np.ndarray | None = None) -> dict[str, float]:
    """Median step across each internal boundary (robust to sky gradients).
    Flagged pixels (bad columns, saturation) are excluded so the metric
    measures amp-level calibration mismatch, not detector cosmetics."""
    xs, ys = seam_positions(geoms)
    metrics = {}
    for x in xs:
        metrics[f"x{x + 1}"] = _masked_median_step(
            sci[:, x], sci[:, x - 1],
            None if mask is None else mask[:, x],
            None if mask is None else mask[:, x - 1])
    for y in ys:
        metrics[f"y{y + 1}"] = _masked_median_step(
            sci[y, :], sci[y - 1, :],
            None if mask is None else mask[y, :],
            None if mask is None else mask[y - 1, :])
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

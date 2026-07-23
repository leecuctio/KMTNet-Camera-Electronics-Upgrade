"""Single-frame cosmic-ray flagging on the assembled CCD (flag-only).

Laplacian-style detector in pure numpy, tiled to bound memory: a pixel is a
CR candidate when its excess over the local 3x3 median is (a) significant
against the photon+read noise expected from that median, and (b) much
sharper than its neighborhood (the 3x3 median of the significance map),
which separates sub-PSF hits from stars even at KMTNet's marginal sampling
(FWHM ~2.5 px: a star's neighbors are also significant, a 1-2 px CR's are
not). Candidates are grown by one pixel and written to MASK_CR; science
pixel values are never modified (masking policy consistent with BPM).

Deliberately conservative for crowded bulge fields: saturated stars and two
pixels around them, existing BAD/NONLINEAR pixels, and amp-seam columns are
excluded. A QA warning is attached when the flagged fraction is unusually
high (false-positive storm guard)."""
from __future__ import annotations

import numpy as np

from .. import MASK_BAD, MASK_CR, MASK_NONLIN, MASK_SAT, MASK_SEAM
from . import CalHistRow

CR_SIGMA = 6.0          # significance of the 3x3-median excess
CR_SHARP = 2.0          # excess must be > CR_SHARP x its neighbor-ring significance
FINE_LIM = 2.0          # excess must be > FINE_LIM x the PSF-scale fine structure
CR_TILE = 512           # rows per tile
CR_MAX_FRACTION = 0.002  # QA warning above this flagged fraction
_EXCLUDE = MASK_BAD | MASK_SAT | MASK_NONLIN | MASK_SEAM


def _median3(a: np.ndarray) -> np.ndarray:
    """3x3 median of the interior of a (result shape: a[1:-1, 1:-1])."""
    h, w = a.shape
    stack = np.stack([a[1 + dy:h - 1 + dy, 1 + dx:w - 1 + dx]
                      for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
    return np.median(stack, axis=0)


_OFFS8 = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]


def _ring_median_at(snr: np.ndarray, ys: np.ndarray, xs: np.ndarray) -> np.ndarray:
    """Median of the 8 neighbors of snr (center excluded) at given pixels.

    Distinguishes CRs from steep PSF wings: a star pixel always has at least
    half its ring at comparable significance (the side toward the core),
    while a 1-2 px CR's ring is mostly noise even for a 2-px event.
    Evaluated only at candidate pixels (gather) — the full-frame median stack
    would dominate the runtime for no benefit."""
    p = np.pad(snr, 1, mode="edge")
    vals = np.stack([p[ys + 1 + dy, xs + 1 + dx] for dy, dx in _OFFS8])
    return np.median(vals, axis=0)


_OFFS7 = [(dy, dx) for dy in range(-3, 4) for dx in range(-3, 4)]


def _fine_structure_at(med3: np.ndarray, ys: np.ndarray, xs: np.ndarray,
                       noise_at: np.ndarray) -> np.ndarray:
    """Van Dokkum (2001) fine structure F = med3 - med7(med3), evaluated only
    at candidate pixels (true 2-D 7x7 median via gather; a separable median
    approximation fails on the symmetric shoulders of undersampled PSFs)."""
    m3p = np.pad(med3, 3, mode="edge")
    vals = np.stack([m3p[ys + 3 + dy, xs + 3 + dx] for dy, dx in _OFFS7])
    med7 = np.median(vals, axis=0)
    return np.clip(med3[ys, xs] - med7, 0.5 * noise_at, None)


def _dilate(b: np.ndarray, it: int = 1) -> np.ndarray:
    """8-neighborhood binary dilation."""
    out = b.copy()
    for _ in range(it):
        g = out.copy()
        g[1:, :] |= out[:-1, :]
        g[:-1, :] |= out[1:, :]
        g[:, 1:] |= out[:, :-1]
        g[:, :-1] |= out[:, 1:]
        g[1:, 1:] |= out[:-1, :-1]
        g[1:, :-1] |= out[:-1, 1:]
        g[:-1, 1:] |= out[1:, :-1]
        g[:-1, :-1] |= out[1:, 1:]
        out = g
    return out


def flag_cosmics(sci: np.ndarray, mask: np.ndarray, rn_e: float,
                 sigma: float = CR_SIGMA, sharp: float = CR_SHARP,
                 tile: int = CR_TILE) -> int:
    """Flag CR candidates into MASK_CR (in place). Returns the flagged count."""
    ny, nx = sci.shape
    rn2 = np.float32(max(rn_e, 1.0)) ** 2
    pad = 3
    n_cr = 0
    for y0 in range(0, ny, tile):
        y1 = min(ny, y0 + tile)
        a0, a1 = max(0, y0 - pad), min(ny, y1 + pad)
        s = sci[a0:a1]
        m = mask[a0:a1]
        med3 = _median3(s)                                  # (h-2, w-2)
        inner = s[1:-1, 1:-1]
        resid = inner - med3
        noise = np.sqrt(np.clip(med3, 0.0, None) + rn2)
        snr = resid / noise
        cand = snr > sigma
        m_in = m[1:-1, 1:-1]
        cand &= (m_in & _EXCLUDE) == 0
        # avoid the sharp edges of bleed trails: 2-px guard around saturation
        sat = _dilate((m[:, :] & MASK_SAT) > 0, it=2)[1:-1, 1:-1]
        cand &= ~sat
        del sat
        ys_c, xs_c = np.nonzero(cand)
        if len(ys_c):
            # ring test: a PSF pixel has half its ring (toward the core) at
            # comparable significance, a CR's ring median stays near noise
            ring = _ring_median_at(snr, ys_c, xs_c)
            keep = snr[ys_c, xs_c] > sharp * np.clip(ring, 0.0, None) + sigma
            ys_c, xs_c = ys_c[keep], xs_c[keep]
        if len(ys_c):
            # fine-structure test (van Dokkum 2001): stars keep extended flux
            # on the PSF scale (F large), 1-2 px CRs do not (F ~ noise floor)
            # — rejects the shoulders of undersampled PSFs that purely local
            # statistics cannot separate from hits
            fine = _fine_structure_at(med3, ys_c, xs_c, noise[ys_c, xs_c])
            keep = resid[ys_c, xs_c] > FINE_LIM * fine
            ys_c, xs_c = ys_c[keep], xs_c[keep]
        cand[:] = False
        if len(ys_c):
            cand[ys_c, xs_c] = True
        del med3, resid, noise, snr
        if cand.any():
            grown = _dilate(cand, it=1)
            # write back only the rows owned by this tile (overlap-safe)
            gy0 = a0 + 1                    # global row of grown[0]
            r0, r1 = max(y0, gy0), min(y1, a1 - 1)
            rows = slice(r0 - gy0, r1 - gy0)
            sub = mask[r0:r1, 1:-1]
            new = grown[rows] & ((sub & MASK_CR) == 0)
            sub[new] |= MASK_CR
            n_cr += int(np.count_nonzero(new))
    return n_cr


def cr_calhist(mode: str, sigma: float, chip_counts: dict[str, int],
               npix_total: int) -> CalHistRow:
    if mode == "off":
        return CalHistRow("CRFLAG", False, params="disabled")
    total = sum(chip_counts.values())
    frac = total / max(npix_total, 1)
    return CalHistRow("CRFLAG", True,
                      params=f"laplacian sigma={sigma:g}, sharp={CR_SHARP:g}; "
                             f"{total} px ({100 * frac:.4f}%) flagged")

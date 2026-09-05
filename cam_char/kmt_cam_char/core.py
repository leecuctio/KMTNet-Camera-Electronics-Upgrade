"""Shared helpers for the camera-characterization measurements.

All pixel access goes through the preprocessing package's L0 reader
(mock64 = future CEU format), with memmap ROI section reads so a
measurement touches only the bytes it needs.

Raw ADU convention: PHYSICAL unsigned ADU — the amp header's BZERO/BSCALE
applied to the stored values (L0 files are BITPIX=16 int16 + BZERO=32768,
so physical = stored + 32768, codes 0..65535), bias INCLUDED unless
stated. This is the same axis as io_l0.read_amp and is monotonic over the
full 16-bit range (no wrap at code 32768). Files without BZERO fall back
to the two's-complement unsigned cast (a < 0 -> a + 65536). Convert any
raw section read with ``unsigned_from_stored``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "mef_pipeline"))

from astropy.io import fits  # noqa: E402

from kmt_ceu_preproc.io_l0 import L0Exposure  # noqa: E402  (re-export)

# measurement ROI inside the 1152x4616 DATASEC (0-based row, col slices):
# generous margins against edge effects and amp-boundary artifacts
ROI = (slice(500, 4100), slice(100, 1050))
OVSC_REAL = slice(1152, 1184)     # first 32 REAL overscan columns of the mock
N_TRANSFER_SERIAL = 1152 + 27     # data columns + legacy prescan to the node


def open_l0(path) -> L0Exposure:
    return L0Exposure(path)


def _hdr_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def unsigned_from_stored(a, hdr) -> np.ndarray:
    """Stored section values -> physical unsigned raw ADU (float64).

    Applies the HDU header's BSCALE/BZERO manually (io_l0 opens with
    do_not_scale_image_data, so ``hdu.section`` returns stored int16) —
    same convention as io_l0.read_amp, but float64 and section-friendly.
    Headers without BZERO fall back to the legacy two's-complement
    unsigned cast (a < 0 -> a + 65536).
    """
    a = np.asarray(a, dtype=np.float64)
    bzero = hdr.get("BZERO")
    if bzero is None:
        return np.where(a < 0, a + 65536.0, a)
    bscale = _hdr_float(hdr.get("BSCALE", 1.0), 1.0)
    if bscale != 1.0:
        a = a * bscale
    return a + _hdr_float(bzero, 0.0)


def roi_raw(exp: L0Exposure, extname: str, roi=ROI) -> np.ndarray:
    """ROI of the amp DATASEC in physical unsigned raw ADU (float64,
    BZERO/BSCALE applied; memmap section read of just the ROI bytes)."""
    hdu = exp.hdul[extname]
    return unsigned_from_stored(hdu.section[roi[0], roi[1]], hdu.header)


def ovsc_raw(exp: L0Exposure, extname: str, rows=ROI[0]) -> np.ndarray:
    """Real overscan columns (first 32; trailing 16 mock cols are mirrored
    duplicates and MUST NOT be used for noise statistics) in physical
    unsigned raw ADU (float64, BZERO/BSCALE applied)."""
    hdu = exp.hdul[extname]
    return unsigned_from_stored(hdu.section[rows, OVSC_REAL], hdu.header)


def mad_std(a: np.ndarray) -> float:
    med = np.median(a)
    return float(1.4826 * np.median(np.abs(a - med)))


def clipped_var(a: np.ndarray, clip: float = 4.0) -> float:
    """Variance with one MAD-based clip round (CR/defect rejection)."""
    med = np.median(a)
    sig = 1.4826 * np.median(np.abs(a - med))
    if sig <= 0:
        return float(np.var(a))
    good = np.abs(a - med) <= clip * sig
    return float(np.var(a[good]))


def pairs(items: list) -> list[tuple]:
    """Non-overlapping consecutive pairs."""
    return [(items[i], items[i + 1]) for i in range(0, len(items) - 1, 2)]

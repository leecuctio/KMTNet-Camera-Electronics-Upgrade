"""Shared helpers for the camera-characterization measurements.

All pixel access goes through the preprocessing package's L0 reader
(mock64 = future CEU format), with memmap ROI section reads so a
measurement touches only the bytes it needs. Raw ADU convention: values
are unsigned (BZERO 32768 applied), bias INCLUDED unless stated.
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


def roi_raw(exp: L0Exposure, extname: str, roi=ROI) -> np.ndarray:
    """ROI of the amp DATASEC in raw unsigned ADU (float64)."""
    sec = exp.hdul[extname].section[roi[0], roi[1]]
    a = np.asarray(sec, dtype=np.float64)
    return np.where(a < 0, a + 65536.0, a)


def ovsc_raw(exp: L0Exposure, extname: str, rows=ROI[0]) -> np.ndarray:
    """Real overscan columns (first 32; trailing 16 mock cols are mirrored
    duplicates and MUST NOT be used for noise statistics)."""
    sec = exp.hdul[extname].section[rows, OVSC_REAL]
    a = np.asarray(sec, dtype=np.float64)
    return np.where(a < 0, a + 65536.0, a)


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

"""Variance plane initialization and propagation.

The variance plane is created once the science pixels are in electrons
(after gain), as var = RN^2 + max(sci, 0), i.e. read noise plus Poisson.
Later multiplicative steps (flat) propagate as var /= flat^2.
"""
from __future__ import annotations

import numpy as np


def init_variance(sci_e: np.ndarray, rn_e: float) -> np.ndarray:
    """var [e-^2] from science in electrons and read noise in electrons."""
    var = np.clip(sci_e, 0.0, None)
    var += np.float32(rn_e) ** 2
    return var.astype(np.float32, copy=False)


def read_noise_e(rdnoise_e: float, ovsc_rms_adu: float, gain_e_adu: float) -> float:
    """Read noise in electrons: header RDNOISE if measured, else overscan RMS."""
    if rdnoise_e and rdnoise_e > 0:
        return float(rdnoise_e)
    return float(ovsc_rms_adu) * float(gain_e_adu)

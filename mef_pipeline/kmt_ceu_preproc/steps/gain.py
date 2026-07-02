"""ADU -> electrons conversion using per-amp GAIN.

Real Archon L0 products currently carry GAIN=0.0 placeholders; in that case
1.0 e-/ADU is used and the L1 primary header records GAINAPPL=F so downstream
software knows the pixel unit is nominal, not measured."""
from __future__ import annotations

import numpy as np

from ..geometry import AmpGeom


def to_electrons(sci: np.ndarray, geom: AmpGeom,
                 default_gain: float = 1.0) -> tuple[float, bool]:
    """Multiply in place; returns (gain_used, measured?)."""
    measured = bool(geom.gain and geom.gain > 0)
    g = geom.gain if measured else default_gain
    if g != 1.0:
        sci *= np.float32(g)
    return float(g), measured

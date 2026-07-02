"""Saturation flagging on raw ADU values (before any subtraction)."""
from __future__ import annotations

import numpy as np

from .. import MASK_SAT
from ..geometry import AmpGeom, section_slices
from . import CalHistRow

DEFAULT_SATURATE = 62000.0


def flag_saturation(raw: np.ndarray, geom: AmpGeom, mask: np.ndarray,
                    level: float | None = None) -> tuple[int, CalHistRow]:
    """Flag DATASEC pixels at/above the saturation level. mask is DATASEC-shaped."""
    lvl = level if level and level > 0 else (
        geom.saturate if geom.saturate > 0 else DEFAULT_SATURATE)
    sat = raw[section_slices(geom.datasec)] >= np.float32(lvl)
    mask[sat] |= MASK_SAT
    n = int(np.count_nonzero(sat))
    return n, CalHistRow("SATURATION", True, params=f"level from SATURAT (default {DEFAULT_SATURATE:.0f})")

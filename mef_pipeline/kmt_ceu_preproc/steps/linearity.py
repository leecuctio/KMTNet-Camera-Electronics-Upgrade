"""Linearity correction and nonlinearity flagging.

No measured linearity coefficients exist yet (CALIBRATION_TRACKER: Rehearsal).
Until then this step only flags pixels above LINMAX; the correction itself is
a no-op that will consume a coefficient table version once measured."""
from __future__ import annotations

import numpy as np

from .. import MASK_NONLIN
from ..geometry import AmpGeom, section_slices
from . import CalHistRow


def flag_nonlinear(raw: np.ndarray, geom: AmpGeom, mask: np.ndarray) -> int:
    """Flag DATASEC pixels above LINMAX on raw ADU values. mask is DATASEC-shaped."""
    if not geom.linmax or geom.linmax <= 0:
        return 0
    nl = raw[section_slices(geom.datasec)] >= np.float32(geom.linmax)
    mask[nl] |= MASK_NONLIN
    return int(np.count_nonzero(nl))


def linearity_calhist(coeffs=None) -> CalHistRow:
    if coeffs is None:
        return CalHistRow("LINEARITY", False,
                          params="no measured coefficients; LINMAX flagging only")
    raise NotImplementedError("linearity correction awaits measured coefficients")

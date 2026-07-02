"""Amp-level master bias subtraction."""
from __future__ import annotations

import numpy as np

from . import CalHistRow


def subtract_bias(sci: np.ndarray, extname: str, master) -> None:
    """Subtract the master-bias plane for this amp (in ADU, DATASEC-trimmed)."""
    sci -= master.plane(extname)


def bias_calhist(master) -> CalHistRow:
    if master is None:
        return CalHistRow("BIAS", False, params="no master bias (skipped)")
    return CalHistRow("BIAS", True, calfile=master.name, calver=master.calver)

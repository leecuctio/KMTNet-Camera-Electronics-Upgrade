"""Master flat division with variance propagation."""
from __future__ import annotations

import numpy as np

from .. import MASK_BAD
from . import CalHistRow

MIN_RESPONSE = 0.1


def divide_flat(sci: np.ndarray, var: np.ndarray | None, mask: np.ndarray,
                extname: str, master, min_response: float = MIN_RESPONSE) -> int:
    """Divide by the normalized flat response; unusable response -> MASK_BAD.
    var may be None (VAR planes omitted by default since L1 PRODVER v1.1)."""
    f = master.plane(extname)
    bad = ~(f > min_response)
    if bad.any():
        f = np.where(bad, np.float32(1.0), f)
        mask[bad] |= MASK_BAD
    sci /= f
    if var is not None:
        var /= f * f
    return int(np.count_nonzero(bad))


def flat_calhist(master, min_response: float = MIN_RESPONSE) -> CalHistRow:
    if master is None:
        return CalHistRow("FLAT", False, params="no master flat (skipped)")
    return CalHistRow("FLAT", True, calfile=master.name, calver=master.calver,
                      params=f"min_response={min_response}")

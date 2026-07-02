"""Bad pixel mask application (flags only; pixel values are preserved)."""
from __future__ import annotations

import numpy as np

from . import CalHistRow


def apply_bpm(mask: np.ndarray, extname: str, master) -> int:
    plane = master.plane(extname).astype(np.uint8)
    mask |= plane
    return int(np.count_nonzero(plane))


def bpm_calhist(master) -> CalHistRow:
    if master is None:
        return CalHistRow("BPM", False, params="no bad pixel mask (skipped)")
    return CalHistRow("BPM", True, calfile=master.name, calver=master.calver)

"""Amp-level dark correction. Disabled by default (KMTNet operational
exposures are short); the structure is in place for when a measured master
dark and an enable decision exist (design doc open question #2)."""
from __future__ import annotations

import numpy as np

from . import CalHistRow


def subtract_dark(sci: np.ndarray, extname: str, master, exptime: float) -> None:
    """Subtract exposure-time-scaled master dark (master stored per second)."""
    sci -= master.plane(extname) * np.float32(exptime)


def dark_calhist(master, enabled: bool) -> CalHistRow:
    if not enabled or master is None:
        return CalHistRow("DARK", False, params="disabled (default)")
    return CalHistRow("DARK", True, calfile=master.name, calver=master.calver)

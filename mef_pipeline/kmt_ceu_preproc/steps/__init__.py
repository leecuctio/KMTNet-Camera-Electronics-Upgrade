"""Processing steps.

Each step operates on per-amp arrays (science, variance, mask) plus geometry,
and returns a CalHistRow recording what was applied. One CalHistRow per step
per exposure goes into the L1 CALHIST table; per-amp details go to QA JSON.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CalHistRow:
    step: str
    applied: bool
    calfile: str = ""
    calver: str = ""
    params: str = ""

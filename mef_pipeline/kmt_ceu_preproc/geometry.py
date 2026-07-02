"""FITS section parsing and amplifier geometry records."""
from __future__ import annotations

import re
from dataclasses import dataclass

_SECTION_RE = re.compile(r"^\[(\d+):(\d+),(\d+):(\d+)\]$")


def parse_section(text) -> tuple[int, int, int, int]:
    """'[x1:x2,y1:y2]' (1-based, inclusive) -> (x1, x2, y1, y2)."""
    m = _SECTION_RE.match(str(text).strip())
    if not m:
        raise ValueError(f"Invalid FITS section: {text!r}")
    x1, x2, y1, y2 = (int(g) for g in m.groups())
    if x2 < x1 or y2 < y1:
        raise ValueError(f"Unsupported (flipped/empty) FITS section: {text!r}")
    return x1, x2, y1, y2


def fmtsec(x1: int, x2: int, y1: int, y2: int) -> str:
    return f"[{x1}:{x2},{y1}:{y2}]"


def section_slices(sec: tuple[int, int, int, int]) -> tuple[slice, slice]:
    """(x1,x2,y1,y2) 1-based inclusive -> (yslice, xslice) for numpy arr[y, x]."""
    x1, x2, y1, y2 = sec
    return slice(y1 - 1, y2), slice(x1 - 1, x2)


def section_shape(sec: tuple[int, int, int, int]) -> tuple[int, int]:
    x1, x2, y1, y2 = sec
    return (y2 - y1 + 1, x2 - x1 + 1)


@dataclass
class AmpGeom:
    """Per-amplifier geometry and calibration metadata from L0 header/AMPINFO."""
    extname: str
    chip: str
    ampid: int          # global amplifier ID (1..64)
    ctrlid: int         # science controller ID (1 or 2)
    datasec: tuple      # active pixels in amp-local coords (x1,x2,y1,y2)
    biassec: tuple      # local serial overscan in amp-local coords
    ccdsec: tuple       # placement of DATASEC in CCD coords
    detsec: tuple       # placement in detector mosaic coords
    gain: float         # e-/ADU; <= 0 means placeholder (not yet measured)
    rdnoise: float      # e-;    <= 0 means placeholder
    saturate: float     # ADU saturation level
    linmax: float       # ADU linearity limit

    @property
    def data_shape(self) -> tuple[int, int]:
        return section_shape(self.datasec)


def ccd_shape(geoms: list[AmpGeom]) -> tuple[int, int]:
    """CCD pixel dimensions implied by the CCDSEC footprints of one chip."""
    nx = max(g.ccdsec[1] for g in geoms)
    ny = max(g.ccdsec[3] for g in geoms)
    return (ny, nx)


def ccd_detsec(geoms: list[AmpGeom]) -> tuple[int, int, int, int]:
    """Full-chip DETSEC implied by the amp DETSEC footprints of one chip."""
    return (
        min(g.detsec[0] for g in geoms),
        max(g.detsec[1] for g in geoms),
        min(g.detsec[2] for g in geoms),
        max(g.detsec[3] for g in geoms),
    )

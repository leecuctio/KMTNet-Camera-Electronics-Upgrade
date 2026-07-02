"""L1 CCD-level MEF writer.

Layout: PRIMARY + (SCI_x, VAR_x, MASK_x) per chip in CHIPLIST order + CALHIST.
HDUs are appended incrementally to a temporary file (bounding memory to one
CCD's planes) and the finished file replaces the target atomically."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import numpy as np
from astropy.io import fits

from . import MASK_BIT_DOC, PIPENAME, VERSION

L1_PRODVER = "v1.0"

# Keywords carried from the L0 primary header into the L1 primary header.
CARRY_KEYS = (
    "ORIGIN", "OBSERVAT", "SITEID", "TELESCOP", "INSTRUME", "CAMNAME",
    "OBJECT", "FIELDID", "PROJID", "IMAGETYP", "OBSTYPE", "EXPTIME",
    "DARKTIME", "FILTER", "DATE-OBS", "JD", "MJD-OBS", "TIMESYS",
    "RA", "DEC", "EQUINOX", "RADECSYS", "CCDTEMP", "CHIPLIST", "MOCKDATA",
)


def utcnow_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "")


def build_primary_header(l0_primary, prov: dict) -> fits.Header:
    h = fits.Header()
    h["DATAPROD"] = ("L1_CCD", "data product type")
    h["PRODVER"] = (L1_PRODVER, "L1 product format version")
    h["CREATOR"] = (f"{PIPENAME}_{VERSION}", "L1 creation program")
    h["PIPEVER"] = (f"{PIPENAME}-{VERSION}", "preprocessing pipeline version")
    h["DATE"] = (utcnow_iso(), "date L1 file was generated")
    h["BUNIT"] = (prov.get("bunit", "electron"), "science pixel unit")
    for k in CARRY_KEYS:
        if k in l0_primary:
            h[k] = (l0_primary[k], l0_primary.comments[k])
    h["L0FILE"] = (prov.get("l0file", ""), "source L0 amp MEF")
    if prov.get("l0sha256"):
        h["L0SHA256"] = (prov["l0sha256"], "SHA256 of source L0 file")
    for key, label in (("bias", "CALBIAS"), ("dark", "CALDARK"),
                       ("flat", "CALFLAT"), ("bpm", "CALBPM")):
        name, ver = prov.get(key, ("", ""))
        h[label] = (name, f"master {key} file")
        h[label + "V"] = (ver, f"master {key} version")
    h["GAINAPPL"] = (bool(prov.get("gainappl", False)),
                     "measured amp gains applied (F: nominal 1.0)")
    h["XTALKAPL"] = (bool(prov.get("xtalkapl", False)), "crosstalk correction applied")
    for line in MASK_BIT_DOC:
        h.add_comment(line)
    return h


def build_plane_header(kind: str, chip: str, extras=None) -> fits.Header:
    """kind in ('SCI', 'VAR', 'MASK')."""
    h = fits.Header()
    h["EXTNAME"] = (f"{kind}_{chip}", f"{kind} plane of CCD {chip}")
    h["EXTTYPE"] = (f"CCD_{kind}", "L1 CCD-level plane")
    h["CHIPID"] = (chip, "CCD identifier")
    h["CCDNAME"] = (f"KMTNet CCD {chip}", "CCD name")
    if kind == "SCI":
        h["BUNIT"] = ("electron", "science pixel unit")
    elif kind == "VAR":
        h["BUNIT"] = ("electron**2", "variance pixel unit")
    else:
        for line in MASK_BIT_DOC:
            h.add_comment(line)
    if extras:
        for item in extras:
            if len(item) == 3:
                key, value, comment = item
                h[key] = (value, comment)
            else:
                key, value = item
                h[key] = value
    return h


def calhist_hdu(rows, timestamp: str | None = None) -> fits.BinTableHDU:
    ts = timestamp or utcnow_iso()
    cols = fits.ColDefs([
        fits.Column(name="STEP", format="16A", array=[r.step for r in rows]),
        fits.Column(name="APPLIED", format="L", array=[r.applied for r in rows]),
        fits.Column(name="CALFILE", format="80A", array=[r.calfile for r in rows]),
        fits.Column(name="CALVER", format="24A", array=[r.calver for r in rows]),
        fits.Column(name="PARAMS", format="80A", array=[r.params for r in rows]),
        fits.Column(name="DATE", format="19A", array=[ts] * len(rows)),
    ])
    return fits.BinTableHDU.from_columns(cols, name="CALHIST")


class IncrementalMEFWriter:
    """Append HDUs one by one to a temp file; atomic replace on finalize."""

    def __init__(self, out_path, primary_header: fits.Header | None = None):
        self.out_path = Path(out_path)
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.tmp = self.out_path.with_name(f".{self.out_path.name}.tmp-{os.getpid()}")
        fits.PrimaryHDU(header=primary_header).writeto(self.tmp, overwrite=True)
        self._finalized = False

    def append_image(self, data: np.ndarray, header: fits.Header | None = None):
        hdu = fits.ImageHDU(data=data, header=header)
        with fits.open(self.tmp, mode="append") as hdul:
            hdul.append(hdu)

    def append_hdu(self, hdu):
        with fits.open(self.tmp, mode="append") as hdul:
            hdul.append(hdu)

    def finalize(self):
        os.replace(self.tmp, self.out_path)
        self._finalized = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self._finalized:
            try:
                self.tmp.unlink()
            except FileNotFoundError:
                pass
        return False

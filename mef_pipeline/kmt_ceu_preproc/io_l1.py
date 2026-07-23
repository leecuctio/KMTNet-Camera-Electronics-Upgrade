"""L1 CCD-level MEF writer.

Layout: PRIMARY + SCI_x[, VAR_x] per chip in CHIPLIST order + CALHIST.
The VAR plane is written only on request (--with-var); MASK planes go to a
separate .mask.mef.fits file, only on request (--mask-file) — both defaults
keep the science product lean, and the reconstruction/consumption recipes
are documented as COMMENT cards in the primary header. HDUs are appended
incrementally to a temporary file (bounding memory to one CCD's planes) and
the finished file replaces the target atomically."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import numpy as np
from astropy.io import fits

from . import MASK_BIT_DOC, PIPENAME, VERSION

L1_PRODVER = "v1.4"

# processing methods and formulas, recorded verbatim in every L1 primary header
PROCESSING_DOC = [
    "---- processing methods (kmt_ceu_preproc) ----",
    "OVERSCAN: row-wise clipped mean of BIASSEC, running-median smoothed.",
    "  Guard: if |level - OVSCLVL(master bias)| > 100 ADU the overscan is",
    "  contaminated (follows the sky); OVSCLVL constant is subtracted",
    "  instead and the amp is flagged NO_OVERSCAN_FIT.",
    "BIAS: SCI -= master bias plane (overscan-corrected, per amp, ADU).",
    "GAIN: SCI[e-] = ADU * GAIN(amp). GAINAPPL=F means nominal 1.0 e-/ADU.",
    "FLAT: SCI /= response (chip median response = 1); resp<0.1 -> BAD.",
    "FRINGE (see CALFRNG): SCI -= a * fringe_plane[fraction of sky]; the",
    "  scale a is a clipped LSQ fit per amp; negligible templates skipped.",
    "ILLUM (see CALILLM): SCI /= smooth dark-sky response (chip median 1).",
    "AMPMATCH: per-CCD least squares over amp-boundary zone medians m,",
    "  multiplicative: s_a*m_a = s_b*m_b, mean(log s)=0 (level preserved);",
    "  additive: o_a+m_a = o_b+m_b. Overscan-fallback chips are matched",
    "  additively, anchored on healthy amps. Factors: AMC* in SCI headers.",
    "CRFLAG (CRMODE): 3x3-median Laplacian significance > sigma AND",
    "  sharper than 2x its 3x3-median -> MASK bit 64 (flag only, grown 1px;",
    "  pixel values unchanged). CRCOUNT per SCI header.",
    "SKYMODEL (SKYSUB): 256px clipped-median mesh, bilinear; measured to",
    "  SKYLVL/SKYRMS/SKYGRADX/SKYGRADY; subtracted only when SKYSUB=T.",
    "ASTROMETRY: stars matched to WCSCAT; TAN fit of CD+CRPIX (CRVAL",
    "  fixed): (xi,eta) = CD @ (pix - CRPIX). Solved: WCSSOLVE=T + WCSRMS;",
    "  failed: WCSSOLVE=F + reason in WCSFAIL (approximate WCS kept).",
    "PHOTZP: ZPMAG = clipped median(m_ref + 2.5 log10(flux_e/EXPTIME)) of",
    "  aperture (r=4px, annulus 8-12px) stars matched to WCSCAT. m_ref per",
    "  ZPREF: 'GSPC-Vjkc'/'GSPC-Ijkc' = Gaia DR3 synthetic JKC photometry",
    "  (Montegriffo+23; validated-range flag, |C*|<3sig blend cut, RUWE",
    "  cut) - filter-native, no color term; 'GaiaG' = raw G fallback",
    "  (approximate, relative tracking only; reason in QA zp_ref note).",
    "VAR (see VARINCL) = (RDNOISE**2 + SCI*flat) / flat**2 [electron**2],",
    "  flat from CALFLAT plane, RDNOISE [e-] from L0 amp header/AMPINFO.",
    "  (fringe/illum/sky corrections perturb this reconstruction by their",
    "  own small amplitudes; --with-var stores the exact propagated VAR.)",
    "MASK (separate file, see MASKFILE): bits 1=BAD 2=SATURATED",
    "  4=NONLINEAR 8=XTALK 16=AMP_SEAM 32=NO_OVERSCAN_FIT 64=COSMIC_RAY.",
]

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
        # no comment: the 64-char digest plus any comment exceeds one card
        h["L0SHA256"] = prov["l0sha256"]
    for key, label in (("bias", "CALBIAS"), ("dark", "CALDARK"),
                       ("flat", "CALFLAT"), ("bpm", "CALBPM"),
                       ("fringe", "CALFRNG"), ("illum", "CALILLM")):
        name, ver = prov.get(key, ("", ""))
        h[label] = (name, f"master {key} file")
        h[label + "V"] = (ver, f"master {key} version")
    h["GAINAPPL"] = (bool(prov.get("gainappl", False)),
                     "measured amp gains applied (F: nominal 1.0)")
    h["XTALKAPL"] = (bool(prov.get("xtalkapl", False)), "crosstalk correction applied")
    h["VARINCL"] = (bool(prov.get("varincl", False)), "variance planes included")
    h["MASKFILE"] = (prov.get("maskfile", ""), "mask MEF ('': none)")
    h["CRMODE"] = (prov.get("crmode", "off"), "cosmic-ray flagging mode")
    h["SKYSUB"] = (bool(prov.get("skysub", False)),
                   "sky background model subtracted from SCI")
    h["WCSCAT"] = (prov.get("wcscat", ""), "astrometric reference catalog")
    h["WCSNSOLV"] = (int(prov.get("wcsnsolv", 0)), "CCDs with solved WCS")
    h["ZPNMEAS"] = (int(prov.get("zpnmeas", 0)),
                    "CCDs with measured photometric zero point")
    for line in PROCESSING_DOC:
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


def build_mask_primary_header(l0_primary, l1_name: str) -> fits.Header:
    h = fits.Header()
    h["DATAPROD"] = ("L1_MASK", "data product type")
    h["PRODVER"] = (L1_PRODVER, "L1 product format version")
    h["CREATOR"] = (f"{PIPENAME}_{VERSION}", "mask creation program")
    h["DATE"] = (utcnow_iso(), "date mask file was generated")
    h["L1FILE"] = (l1_name, "science L1 of this mask")
    for k in ("OBSERVAT", "OBJECT", "FILTER", "EXPTIME", "DATE-OBS", "MJD-OBS", "MOCKDATA"):
        if k in l0_primary:
            h[k] = (l0_primary[k], l0_primary.comments[k])
    for line in MASK_BIT_DOC:
        h.add_comment(line)
    return h


def mask_name_for(l1_name: str) -> str:
    return l1_name.replace(".mef.fits", ".mask.mef.fits")


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

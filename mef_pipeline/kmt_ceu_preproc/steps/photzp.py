"""Approximate photometric zero point against the astrometric catalog.

After a successful WCS solution the detected stars are re-measured with a
small circular aperture (local annulus sky), matched to the reference
catalog, and the zero point

    ZPMAG = median( G_ref + 2.5 log10(flux_e / EXPTIME) )

is recorded per CCD (ZPMAG/ZPRMS/ZPNSTAR keywords + QA). This is an
*approximate* calibration: the reference magnitude is Gaia G with no color
term, so the absolute scale carries a filter-dependent offset — but the
night-to-night and chip-to-chip *relative* behaviour (transparency, clouds,
illumination residuals) is tracked, which is what the survey QA and the
difference-imaging photometry need first. A proper filter transformation
belongs to the later photometric-calibration stage."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from .. import MASK_BAD, MASK_CR, MASK_NONLIN, MASK_SAT
from ..astrometry import _match_closest, clean_families, detect_stars
from . import CalHistRow

AP_RADIUS_PX = 4.0        # aperture radius (~1.6" at 0.4"/px)
ANN_IN_PX = 8
ANN_OUT_PX = 12
MATCH_TOL_PX = 3.0
MIN_ZP_STARS = 10
MAX_ZP_STARS = 400
ZP_CLIP = 2.5
_EXCLUDE = MASK_BAD | MASK_SAT | MASK_NONLIN | MASK_CR


@dataclass
class ZPResult:
    measured: bool
    reason: str = ""
    zp: float = 0.0
    rms: float = 0.0
    n_star: int = 0

    def qa(self) -> dict:
        return {"measured": self.measured, "reason": self.reason,
                "zp": round(self.zp, 4), "rms": round(self.rms, 4),
                "n_star": self.n_star}


def _aperture_grids():
    r = int(ANN_OUT_PX)
    gy, gx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.hypot(gx, gy)
    return r, d <= AP_RADIUS_PX, (d >= ANN_IN_PX) & (d <= ANN_OUT_PX)


def aperture_photometry(sci: np.ndarray, mask: np.ndarray | None,
                        xy: np.ndarray) -> np.ndarray:
    """Aperture-minus-annulus-sky flux [e-] per (x, y); NaN where unusable."""
    r, ap, ann = _aperture_grids()
    ny, nx = sci.shape
    flux = np.full(len(xy), np.nan)
    for i, (x, y) in enumerate(xy):
        cx, cy = int(round(x)), int(round(y))
        if not (r <= cx < nx - r and r <= cy < ny - r):
            continue
        win = sci[cy - r:cy + r + 1, cx - r:cx + r + 1].astype(np.float64)
        if mask is not None:
            mwin = mask[cy - r:cy + r + 1, cx - r:cx + r + 1]
            if (mwin[ap] & _EXCLUDE).any():
                continue
            ann_good = ann & ((mwin & _EXCLUDE) == 0)
        else:
            ann_good = ann
        if np.count_nonzero(ann_good) < 12:
            continue
        sky = float(np.median(win[ann_good]))
        flux[i] = float(win[ap].sum()) - sky * int(np.count_nonzero(ap))
    return flux


def measure_zp(sci: np.ndarray, mask: np.ndarray | None, wcs_cards: list,
               ref: np.ndarray, exptime: float) -> ZPResult:
    """Zero point of one assembled CCD. `ref` is (n, >=3): RA, DEC, GMAG.
    wcs_cards: solved WCS cards for this CCD (from AstrometryResult)."""
    if exptime <= 0:
        return ZPResult(False, reason="NO_EXPTIME")
    if ref.ndim != 2 or ref.shape[1] < 3:
        return ZPResult(False, reason="NO_REF_MAG")
    gmag = ref[:, 2]
    has_g = np.isfinite(gmag)
    if np.count_nonzero(has_g) < MIN_ZP_STARS:
        return ZPResult(False, reason="NO_REF_MAG")

    hdr = fits.Header()
    hdr["NAXIS"] = 2
    hdr["NAXIS2"], hdr["NAXIS1"] = sci.shape
    for item in wcs_cards:
        hdr[item[0]] = item[1]
    try:
        w = WCS(hdr)
    except Exception as err:
        return ZPResult(False, reason=f"BAD_WCS({err})")

    stars = clean_families(detect_stars(sci, mask, nmax=MAX_ZP_STARS, sigma=5.0))
    if len(stars) < MIN_ZP_STARS:
        return ZPResult(False, reason=f"FEW_STARS({len(stars)})")

    refg = ref[has_g]
    ref_px = np.column_stack(w.all_world2pix(refg[:, 0], refg[:, 1], 0,
                                             quiet=True, tolerance=1e-6, maxiter=30))
    ny, nx = sci.shape
    inb = ((ref_px[:, 0] > 0) & (ref_px[:, 0] < nx)
           & (ref_px[:, 1] > 0) & (ref_px[:, 1] < ny))
    if np.count_nonzero(inb) < MIN_ZP_STARS:
        return ZPResult(False, reason="FEW_REF_IN_FIELD")
    ridx = np.nonzero(inb)[0]
    idet, jref = _match_closest(stars[:, :2], ref_px[ridx], MATCH_TOL_PX)
    if len(idet) < MIN_ZP_STARS:
        return ZPResult(False, reason=f"FEW_MATCHES({len(idet)})")

    flux = aperture_photometry(sci, mask, stars[idet, :2])
    ok = np.isfinite(flux) & (flux > 0)
    if np.count_nonzero(ok) < MIN_ZP_STARS:
        return ZPResult(False, reason=f"FEW_FLUXES({int(np.count_nonzero(ok))})")
    g = refg[ridx[jref[ok]], 2]
    zps = g + 2.5 * np.log10(flux[ok] / exptime)

    good = np.isfinite(zps)
    for _ in range(2):
        med = float(np.median(zps[good]))
        sig = 1.4826 * float(np.median(np.abs(zps[good] - med)))
        if sig <= 0:
            break
        good &= np.abs(zps - med) <= ZP_CLIP * sig
    n = int(np.count_nonzero(good))
    if n < MIN_ZP_STARS:
        return ZPResult(False, reason=f"FEW_AFTER_CLIP({n})")
    med = float(np.median(zps[good]))
    sig = 1.4826 * float(np.median(np.abs(zps[good] - med)))
    return ZPResult(True, zp=med, rms=sig, n_star=n)


def photzp_calhist(enabled: bool, results: dict[str, ZPResult],
                   catname: str = "") -> CalHistRow:
    if not enabled:
        return CalHistRow("PHOTZP", False, params="disabled")
    done = {c: r for c, r in results.items() if r.measured}
    if not done:
        reasons = ",".join(sorted({r.reason for r in results.values()})) or "no CCDs"
        return CalHistRow("PHOTZP", False, calfile=catname,
                          params=f"not measured: {reasons}"[:80])
    med = float(np.median([r.zp for r in done.values()]))
    return CalHistRow("PHOTZP", True, calfile=catname,
                      params=f"Gaia-G aperture ZP (no color term), "
                             f"{len(done)} CCDs, median {med:.3f}")

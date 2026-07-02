"""Astrometric solution for assembled CCD images (TAN plate fit).

Starting from the approximate WCS inherited from L0, unsaturated stars are
detected on the assembled CCD, matched to a reference catalog (RA/Dec), and
a 6-parameter linear TAN solution is fitted:

    (xi, eta) = CD @ (pixel - CRPIX)        CRVAL (tangent point) kept fixed

xi/eta are the standard tangent-plane coordinates of the catalog positions.
The fit is iterated with a shrinking match radius. On success the SCI header
WCS is replaced (WCSSOLVE=T, WCSAPPRX=F, WCSRMS/WCSNSTAR/WCSNREF/WCSNMAT);
on any failure the approximate WCS is kept and WCSSOLVE=F with the reason in
WCSFAIL, so downstream software can tell solved from unsolved chips.

Pure numpy + astropy.wcs; no external solver or network access required.
The reference catalog is a FITS binary table with RA/DEC columns in degrees
(e.g. produced by the make-refcat CLI command from a solved/first exposure,
or an external Gaia extract)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from . import MASK_BAD, MASK_NONLIN, MASK_SAT

DETECT_SIGMA = 5.0
MAX_STARS = 200
BORDER_PX = 16
MIN_SEPARATION = 8
MATCH_TOL_PX = (15.0, 5.0, 3.0)   # per fit iteration
MIN_MATCH = 10
MAX_RMS_ARCSEC = 1.5
SHIFT_SEARCH_PX = 600.0           # global-offset search radius (TCS repeatability)
SHIFT_BIN_PX = 8.0
DETECT_EXCLUDE = MASK_BAD | MASK_SAT | MASK_NONLIN


@dataclass
class AstrometryResult:
    solved: bool
    reason: str = ""
    n_det: int = 0
    n_ref: int = 0
    n_match: int = 0
    rms_arcsec: float = 0.0
    cards: list = field(default_factory=list)

    def qa(self) -> dict:
        return {"solved": self.solved, "reason": self.reason,
                "n_det": self.n_det, "n_ref": self.n_ref,
                "n_match": self.n_match, "rms_arcsec": round(self.rms_arcsec, 4)}


# -- star detection ----------------------------------------------------------

def detect_stars(sci: np.ndarray, mask: np.ndarray | None = None,
                 nmax: int = MAX_STARS, sigma: float = DETECT_SIGMA) -> np.ndarray:
    """Bright unsaturated star centroids: array of (x, y, flux), 0-based pix."""
    sub = sci[::4, ::4]
    bg = float(np.median(sub))
    noise = float(1.4826 * np.median(np.abs(sub - bg))) or 1.0
    cand = sci > np.float32(bg + sigma * noise)
    if mask is not None:
        cand &= (mask & DETECT_EXCLUDE) == 0
    b = BORDER_PX
    cand[:b, :] = cand[-b:, :] = False
    cand[:, :b] = cand[:, -b:] = False
    ys, xs = np.nonzero(cand)
    if ys.size == 0:
        return np.empty((0, 3))
    vals = sci[ys, xs]
    keep = np.ones(ys.size, dtype=bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                keep &= vals >= sci[ys + dy, xs + dx]
    ys, xs, vals = ys[keep], xs[keep], vals[keep]
    order = np.argsort(vals)[::-1]
    sel: list[tuple[int, int]] = []
    for i in order:
        y, x = int(ys[i]), int(xs[i])
        if all(abs(y - yy) >= MIN_SEPARATION or abs(x - xx) >= MIN_SEPARATION
               for yy, xx in sel):
            sel.append((y, x))
            if len(sel) >= 2 * nmax:
                break
    gy, gx = np.mgrid[-3:4, -3:4]
    stars = []
    for y, x in sel:
        win = sci[y - 3:y + 4, x - 3:x + 4].astype(np.float64) - bg
        if mask is not None:
            win = np.where((mask[y - 3:y + 4, x - 3:x + 4] & DETECT_EXCLUDE) == 0, win, 0.0)
        win = np.clip(win, 0.0, None)
        flux = win.sum()
        if flux <= 0:
            continue
        stars.append((x + (win * gx).sum() / flux, y + (win * gy).sum() / flux, flux))
        if len(stars) >= nmax:
            break
    return np.array(stars) if stars else np.empty((0, 3))


# -- tangent-plane math ------------------------------------------------------

def _tan_plane(ra_deg: np.ndarray, dec_deg: np.ndarray,
               ra0_deg: float, dec0_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Standard coordinates (xi, eta) in degrees about the tangent point."""
    ra, dec = np.radians(ra_deg), np.radians(dec_deg)
    ra0, dec0 = np.radians(ra0_deg), np.radians(dec0_deg)
    d = np.sin(dec) * np.sin(dec0) + np.cos(dec) * np.cos(dec0) * np.cos(ra - ra0)
    xi = np.cos(dec) * np.sin(ra - ra0) / d
    eta = (np.sin(dec) * np.cos(dec0) - np.cos(dec) * np.sin(dec0) * np.cos(ra - ra0)) / d
    return np.degrees(xi), np.degrees(eta)


def _nearest_match(det_xy: np.ndarray, ref_xy: np.ndarray,
                   tol_px: float) -> tuple[np.ndarray, np.ndarray]:
    """Indices (det, ref) of mutual nearest pairs within tol_px."""
    d2 = ((det_xy[:, None, :] - ref_xy[None, :, :]) ** 2).sum(axis=2)
    jref = d2.argmin(axis=1)
    dmin = d2[np.arange(len(det_xy)), jref]
    ok = dmin <= tol_px ** 2
    idet = np.nonzero(ok)[0]
    jref = jref[ok]
    # drop reference stars claimed by more than one detection
    uniq, counts = np.unique(jref, return_counts=True)
    good_ref = set(uniq[counts == 1])
    keep = np.array([j in good_ref for j in jref], dtype=bool)
    return idet[keep], jref[keep]


def _estimate_shift(det_xy: np.ndarray, ref_px: np.ndarray,
                    search: float = SHIFT_SEARCH_PX,
                    bin_px: float = SHIFT_BIN_PX) -> tuple[float, float, int]:
    """Global (dx, dy) between detections and projected references via the
    mode of pairwise offsets — handles TCS pointing errors far beyond the
    fine matching radius. Returns (dx, dy, votes_at_peak)."""
    d = det_xy[:, None, :] - ref_px[None, :, :]
    d = d.reshape(-1, 2)
    inside = (np.abs(d[:, 0]) < search) & (np.abs(d[:, 1]) < search)
    d = d[inside]
    if len(d) == 0:
        return 0.0, 0.0, 0
    nbins = int(2 * search / bin_px)
    hist, xe, ye = np.histogram2d(d[:, 0], d[:, 1], bins=nbins,
                                  range=[[-search, search], [-search, search]])
    i, j = np.unravel_index(np.argmax(hist), hist.shape)
    votes = int(hist[i, j])
    cx, cy = (xe[i] + xe[i + 1]) / 2, (ye[j] + ye[j + 1]) / 2
    near = (np.abs(d[:, 0] - cx) < 1.5 * bin_px) & (np.abs(d[:, 1] - cy) < 1.5 * bin_px)
    if near.any():
        cx, cy = float(np.median(d[near, 0])), float(np.median(d[near, 1]))
    return cx, cy, votes


# -- solver -------------------------------------------------------------------

def solve_tan(sci: np.ndarray, mask: np.ndarray | None, wcs_header: fits.Header,
              ref_radec: np.ndarray, min_match: int = MIN_MATCH,
              max_rms: float = MAX_RMS_ARCSEC) -> AstrometryResult:
    """Fit CD+CRPIX against the catalog; never raises on bad data."""
    try:
        w = WCS(wcs_header)
    except Exception as err:
        return AstrometryResult(False, reason=f"BAD_WCS({err})")
    if not w.has_celestial:
        return AstrometryResult(False, reason="NO_INITIAL_WCS")

    stars = detect_stars(sci, mask)
    if len(stars) < min_match:
        return AstrometryResult(False, reason=f"FEW_STARS({len(stars)})",
                                n_det=len(stars), n_ref=len(ref_radec))
    det_xy = stars[:, :2]

    ny, nx = sci.shape
    ra0, dec0 = (float(v) for v in w.wcs.crval)

    # global pointing-offset pre-estimation (TCS repeatability >> fine radius)
    ref_px = np.column_stack(w.wcs_world2pix(ref_radec[:, 0], ref_radec[:, 1], 0))
    inb = ((ref_px[:, 0] > -SHIFT_SEARCH_PX) & (ref_px[:, 0] < nx + SHIFT_SEARCH_PX)
           & (ref_px[:, 1] > -SHIFT_SEARCH_PX) & (ref_px[:, 1] < ny + SHIFT_SEARCH_PX))
    if np.count_nonzero(inb) >= min_match:
        dx, dy, votes = _estimate_shift(det_xy, ref_px[inb])
        if votes >= min_match and (abs(dx) > 1.0 or abs(dy) > 1.0):
            w.wcs.crpix = w.wcs.crpix + np.array([dx, dy])

    n_match = 0
    rms = 0.0
    for tol in MATCH_TOL_PX:
        ref_px = np.column_stack(w.wcs_world2pix(ref_radec[:, 0], ref_radec[:, 1], 0))
        inb = ((ref_px[:, 0] > -tol) & (ref_px[:, 0] < nx + tol)
               & (ref_px[:, 1] > -tol) & (ref_px[:, 1] < ny + tol))
        ref_idx = np.nonzero(inb)[0]
        if len(ref_idx) < min_match:
            return AstrometryResult(False, reason=f"FEW_REF_IN_FIELD({len(ref_idx)})",
                                    n_det=len(stars), n_ref=len(ref_radec))
        idet, jref = _nearest_match(det_xy, ref_px[ref_idx], tol)
        n_match = len(idet)
        if n_match < min_match:
            return AstrometryResult(False, reason=f"FEW_MATCHES({n_match})",
                                    n_det=len(stars), n_ref=len(ref_idx))
        sel = ref_radec[ref_idx[jref]]
        xi, eta = _tan_plane(sel[:, 0], sel[:, 1], ra0, dec0)
        # linear fit: xi = a0 + a1 x + a2 y ; eta = b0 + b1 x + b2 y (0-based pix)
        X = np.column_stack([np.ones(n_match), det_xy[idet, 0], det_xy[idet, 1]])
        a, *_ = np.linalg.lstsq(X, xi, rcond=None)
        b, *_ = np.linalg.lstsq(X, eta, rcond=None)
        cd = np.array([[a[1], a[2]], [b[1], b[2]]])
        if abs(np.linalg.det(cd)) < 1e-16:
            return AstrometryResult(False, reason="SINGULAR_FIT",
                                    n_det=len(stars), n_ref=len(ref_idx), n_match=n_match)
        crpix0 = -np.linalg.solve(cd, np.array([a[0], b[0]]))  # 0-based
        w.wcs.cd = cd
        w.wcs.crpix = crpix0 + 1.0  # FITS 1-based
        model = X @ np.column_stack([a, b])
        resid = np.column_stack([xi, eta]) - model
        rms = float(np.sqrt(np.mean(resid ** 2)) * 3600.0)

    if rms > max_rms:
        return AstrometryResult(False, reason=f"HIGH_RMS({rms:.2f}as)",
                                n_det=len(stars), n_ref=len(ref_radec), n_match=n_match,
                                rms_arcsec=rms)
    cards = [
        ("CRVAL1", float(w.wcs.crval[0]), "solved WCS"),
        ("CRVAL2", float(w.wcs.crval[1]), "solved WCS"),
        ("CRPIX1", float(w.wcs.crpix[0]), "solved WCS"),
        ("CRPIX2", float(w.wcs.crpix[1]), "solved WCS"),
        ("CD1_1", float(w.wcs.cd[0, 0]), "solved WCS"),
        ("CD1_2", float(w.wcs.cd[0, 1]), "solved WCS"),
        ("CD2_1", float(w.wcs.cd[1, 0]), "solved WCS"),
        ("CD2_2", float(w.wcs.cd[1, 1]), "solved WCS"),
        ("WCSAPPRX", False, "WCS solved against reference catalog"),
    ]
    return AstrometryResult(True, n_det=len(stars), n_ref=len(ref_radec),
                            n_match=n_match, rms_arcsec=rms, cards=cards)


# -- reference catalog I/O -----------------------------------------------------

def load_refcat(path) -> np.ndarray:
    """FITS bintable with RA/DEC columns (deg) -> (n, 2) array."""
    with fits.open(path) as hdul:
        for hdu in hdul[1:]:
            names = {n.upper(): n for n in hdu.columns.names}
            if "RA" in names and "DEC" in names:
                return np.column_stack([
                    np.asarray(hdu.data[names["RA"]], dtype=np.float64),
                    np.asarray(hdu.data[names["DEC"]], dtype=np.float64)])
    raise ValueError(f"No RA/DEC binary table in {path}")


DEDUP_ARCSEC = 2.0


def _dedup_radec(ra, dec, flux) -> np.ndarray:
    """Keep the brightest entry per ~2 arcsec cell (merging repeat visits)."""
    order = np.argsort(flux)[::-1]
    ra, dec, flux = ra[order], dec[order], flux[order]
    cell = DEDUP_ARCSEC / 3600.0
    key_dec = np.round(dec / cell).astype(np.int64)
    key_ra = np.round(ra * np.cos(np.radians(dec)) / cell).astype(np.int64)
    _, first = np.unique(np.column_stack([key_ra, key_dec]), axis=0, return_index=True)
    return np.sort(order[np.sort(first)])  # original indices, brightest per cell


def make_refcat(l1_paths, out_path, nmax_per_chip: int = MAX_STARS,
                sigma: float = DETECT_SIGMA) -> dict:
    """Extract a reference catalog from one or more L1 files using their
    (approximate or solved) WCS. Stars from repeat visits of the same field
    are merged (brightest per ~2 arcsec); multiple pointings simply extend
    the sky coverage. A sibling .mask. file is used when present."""
    if isinstance(l1_paths, (str, Path)):
        l1_paths = [l1_paths]
    rows = {"RA": [], "DEC": [], "FLUX": [], "CHIP": []}
    for l1_path in l1_paths:
        l1_path = Path(l1_path)
        mask_path = l1_path.with_name(l1_path.name.replace(".mef.fits", ".mask.mef.fits"))
        with fits.open(l1_path) as hdul:
            mask_hdul = fits.open(mask_path) if mask_path.exists() else None
            try:
                for hdu in hdul[1:]:
                    if not hdu.name.startswith("SCI_"):
                        continue
                    chip = hdu.name.split("_")[1]
                    mask = None
                    if mask_hdul is not None and f"MASK_{chip}" in mask_hdul:
                        mask = np.asarray(mask_hdul[f"MASK_{chip}"].data)
                    stars = detect_stars(np.asarray(hdu.data), mask,
                                         nmax=nmax_per_chip, sigma=sigma)
                    if not len(stars):
                        continue
                    w = WCS(hdu.header)
                    ra, dec = w.wcs_pix2world(stars[:, 0], stars[:, 1], 0)
                    rows["RA"] += list(ra)
                    rows["DEC"] += list(dec)
                    rows["FLUX"] += list(stars[:, 2])
                    rows["CHIP"] += [chip] * len(stars)
            finally:
                if mask_hdul is not None:
                    mask_hdul.close()
    ra = np.asarray(rows["RA"], dtype=np.float64)
    dec = np.asarray(rows["DEC"], dtype=np.float64)
    flux = np.asarray(rows["FLUX"], dtype=np.float64)
    keep = _dedup_radec(ra, dec, flux) if len(ra) else np.array([], dtype=int)
    chips = np.asarray(rows["CHIP"])
    cols = fits.ColDefs([
        fits.Column("RA", "D", unit="deg", array=ra[keep]),
        fits.Column("DEC", "D", unit="deg", array=dec[keep]),
        fits.Column("FLUX", "E", array=flux[keep]),
        fits.Column("CHIP", "1A", array=chips[keep]),
    ])
    tbl = fits.BinTableHDU.from_columns(cols, name="REFCAT")
    tbl.header["NSRC"] = (len(l1_paths), "L1 files the catalog was extracted from")
    tbl.header["SRCFILE"] = (Path(l1_paths[0]).name, "first source L1 file")
    fits.HDUList([fits.PrimaryHDU(), tbl]).writeto(out_path, overwrite=True)
    return {"n_stars": int(len(keep)), "path": str(out_path)}

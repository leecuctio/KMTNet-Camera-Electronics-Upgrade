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


# ============================================================================
# Full-field TAN-SIP solver and per-chip template initial values (v1.4).
# Procedure established on 011103-011107 vs Gaia DR3: KMTNet prime-focus
# distortion reaches 17-54 arcsec at chip corners, so the linear solve_tan is
# only used as a seed; the field is grown annulus by annulus from the
# best-matching zone and fitted with SIP order 3. All matching/evaluation is
# SIP-aware (all_world2pix; wcs_world2pix would silently ignore SIP).
# ============================================================================

NOMINAL_PIX_SCALE = 0.395          # arcsec/px, measured vs Gaia DR3 (2026-07-02)
SOLVE_NMAX = 800
SOLVE_SIGMA = 4.0
FAMILY_SEP_PX = 25                 # blooming families: keep brightest only
SEED_ZONES = 4
SEED_SEARCH_PX = 700.0
SEED_MIN_VOTES = 8
GROW_START_PX = 2500.0
GROW_STEP_PX = 1500.0
GROW_TOL_PX = 12.0
CLIP_PX = 2.5
FINAL_TOL_PX = 5.0
FIELD_MIN_MATCH = 50


def clean_families(stars: np.ndarray, sep: int = FAMILY_SEP_PX) -> np.ndarray:
    """Keep only the brightest detection within `sep` px (saturated blooms
    produce several wing peaks around one star)."""
    if not len(stars):
        return stars
    order = np.argsort(stars[:, 2])[::-1]
    keep: list[int] = []
    for i in order:
        if all(max(abs(stars[i, 0] - stars[j, 0]),
                   abs(stars[i, 1] - stars[j, 1])) >= sep for j in keep):
            keep.append(int(i))
    return stars[np.array(keep, int)]


def tan_plane_inverse(xi_deg: float, eta_deg: float,
                      ra0_deg: float, dec0_deg: float) -> tuple[float, float]:
    """Inverse gnomonic: tangent-plane offsets (deg) about (ra0, dec0) -> sky."""
    xi, eta = np.radians(xi_deg), np.radians(eta_deg)
    ra0, dec0 = np.radians(ra0_deg), np.radians(dec0_deg)
    den = np.cos(dec0) - eta * np.sin(dec0)
    ra = ra0 + np.arctan2(xi, den)
    dec = np.arctan((np.sin(dec0) + eta * np.cos(dec0)) / np.hypot(xi, den))
    return float(np.degrees(ra)) % 360.0, float(np.degrees(dec))


def parse_pointing(header) -> tuple[float, float] | None:
    """Telescope pointing from RA/DEC keywords (sexagesimal or degrees)."""
    ra, dec = header.get("RA"), header.get("DEC")
    if ra is None or dec is None:
        return None
    try:
        if isinstance(ra, str) and ":" in ra:
            h, m, s = (float(x) for x in ra.split(":"))
            ra_deg = 15.0 * (h + m / 60 + s / 3600)
        else:
            ra_deg = float(ra)
        if isinstance(dec, str) and ":" in dec:
            p = dec.strip()
            sign = -1.0 if p.startswith("-") else 1.0
            d, m, s = (float(x) for x in p.lstrip("+-").split(":"))
            dec_deg = sign * (d + m / 60 + s / 3600)
        else:
            dec_deg = float(dec)
    except (TypeError, ValueError):
        return None
    if not (0.0 <= ra_deg < 360.0 and -90.0 <= dec_deg <= 90.0):
        return None
    return ra_deg, dec_deg


def load_astrom_template() -> dict | None:
    """Per-chip representative initial WCS (data/astrom_template.json),
    derived from Gaia solutions of frames 011103-011106."""
    path = Path(__file__).parent / "data" / "astrom_template.json"
    if not path.exists():
        return None
    import json
    return json.loads(path.read_text(encoding="utf-8"))


def template_wcs_header(chip: str, ra_pointing: float, dec_pointing: float,
                        nx: int, ny: int, template: dict) -> fits.Header | None:
    """Initial-guess header from the per-chip template + telescope pointing.
    Includes the mean SIP distortion, so the remaining error is mostly the
    TCS pointing offset (absorbed by the seed shift)."""
    t = template.get("chips", {}).get(chip)
    if t is None:
        return None
    ra_c, dec_c = tan_plane_inverse(t["dxi_deg"], t["deta_deg"],
                                    ra_pointing, dec_pointing)
    h = fits.Header()
    h["NAXIS"] = 2
    h["NAXIS1"], h["NAXIS2"] = nx, ny
    h["CTYPE1"], h["CTYPE2"] = "RA---TAN-SIP", "DEC--TAN-SIP"
    h["CRVAL1"], h["CRVAL2"] = ra_c, dec_c
    h["CRPIX1"], h["CRPIX2"] = template["crpix"]
    (h["CD1_1"], h["CD1_2"]), (h["CD2_1"], h["CD2_2"]) = t["cd"]
    h["A_ORDER"] = h["B_ORDER"] = int(template.get("sip_order", 3))
    for k, v in t.get("sip_a", {}).items():
        h[k] = v
    for k, v in t.get("sip_b", {}).items():
        h[k] = v
    h["WCSAPPRX"] = True
    return h


def rescale_cd_to_nominal(header: fits.Header) -> fits.Header:
    """Force the initial CD matrix to the measured plate scale (0.395)."""
    try:
        cd = np.array([[header["CD1_1"], header["CD1_2"]],
                       [header["CD2_1"], header["CD2_2"]]], dtype=float)
    except KeyError:
        return header
    scale = np.sqrt(abs(np.linalg.det(cd))) * 3600.0
    if 0.2 < scale < 0.8 and abs(scale - NOMINAL_PIX_SCALE) > 1e-4:
        cd *= NOMINAL_PIX_SCALE / scale
        (header["CD1_1"], header["CD1_2"]), (header["CD2_1"], header["CD2_2"]) = cd
    return header


def _match_closest(det_xy: np.ndarray, ref_px: np.ndarray,
                   tol: float) -> tuple[np.ndarray, np.ndarray]:
    """Nearest match keeping the closest claim per reference star."""
    d2 = ((det_xy[:, None, :] - ref_px[None, :, :]) ** 2).sum(axis=2)
    jr = d2.argmin(axis=1)
    dm = d2[np.arange(len(det_xy)), jr]
    ok = dm <= tol * tol
    best: dict[int, int] = {}
    for k in np.nonzero(ok)[0]:
        j = int(jr[k])
        if j not in best or dm[k] < dm[best[j]]:
            best[j] = int(k)
    ks = np.array(sorted(best.values()), int)
    if len(ks) == 0:
        return np.array([], int), np.array([], int)
    return ks, jr[ks]


def _all_w2p(w: WCS, radec: np.ndarray) -> np.ndarray:
    return np.column_stack(w.all_world2pix(radec[:, 0], radec[:, 1], 0,
                                           quiet=True, tolerance=1e-6, maxiter=30))


def solve_field(sci: np.ndarray, mask: np.ndarray | None, wcs_header,
                ref_radec: np.ndarray, min_match: int = FIELD_MIN_MATCH,
                max_rms: float = MAX_RMS_ARCSEC) -> AstrometryResult:
    """Full-chip TAN-SIP(3) solution against a reference catalog."""
    from astropy.coordinates import SkyCoord
    from astropy.wcs.utils import fit_wcs_from_points
    import astropy.units as u

    try:
        w = WCS(wcs_header)
    except Exception as err:
        return AstrometryResult(False, reason=f"BAD_WCS({err})")
    if not w.has_celestial:
        return AstrometryResult(False, reason="NO_INITIAL_WCS")

    ny, nx = sci.shape
    stars = clean_families(detect_stars(sci, mask, nmax=SOLVE_NMAX, sigma=SOLVE_SIGMA))
    if len(stars) < min_match:
        return AstrometryResult(False, reason=f"FEW_STARS({len(stars)})",
                                n_det=len(stars), n_ref=len(ref_radec))

    # seed: strongest zone of the detection-reference offset histogram
    ref_px0 = _all_w2p(w, ref_radec)
    best = None
    for zi in range(SEED_ZONES):
        for zj in range(SEED_ZONES):
            x0, x1 = zj * nx / SEED_ZONES, (zj + 1) * nx / SEED_ZONES
            y0, y1 = zi * ny / SEED_ZONES, (zi + 1) * ny / SEED_ZONES
            ds = stars[(stars[:, 0] >= x0) & (stars[:, 0] < x1)
                       & (stars[:, 1] >= y0) & (stars[:, 1] < y1)]
            rs = ref_px0[(ref_px0[:, 0] >= x0 - SEED_SEARCH_PX)
                         & (ref_px0[:, 0] < x1 + SEED_SEARCH_PX)
                         & (ref_px0[:, 1] >= y0 - SEED_SEARCH_PX)
                         & (ref_px0[:, 1] < y1 + SEED_SEARCH_PX)]
            if len(ds) < 5 or len(rs) < 5:
                continue
            dx, dy, votes = _estimate_shift(ds[:, :2], rs,
                                            search=SEED_SEARCH_PX, bin_px=8.0)
            if best is None or votes > best[0]:
                best = (votes, dx, dy, (x0 + x1) / 2, (y0 + y1) / 2)
    if best is None or best[0] < SEED_MIN_VOTES:
        return AstrometryResult(False, n_det=len(stars), n_ref=len(ref_radec),
                                reason=f"NO_SEED_ZONE({0 if best is None else best[0]})")
    _, dx, dy, sx, sy = best
    w.wcs.crpix = w.wcs.crpix + np.array([dx, dy])
    r_det = np.hypot(stars[:, 0] - sx, stars[:, 1] - sy)

    def match(wq, sel, tol):
        ref_px = _all_w2p(wq, ref_radec)
        inb = ((ref_px[:, 0] > -50) & (ref_px[:, 0] < nx + 50)
               & (ref_px[:, 1] > -50) & (ref_px[:, 1] < ny + 50))
        ridx = np.nonzero(inb)[0]
        ds = np.nonzero(sel)[0]
        if not len(ds) or not len(ridx):
            return np.array([], int), np.array([], int)
        ki, kj = _match_closest(stars[ds][:, :2], ref_px[ridx], tol)
        return ds[ki], ridx[kj]

    fitted = False
    pi = pj = np.array([], int)
    R = GROW_START_PX
    while True:
        pi, pj = match(w, r_det < R, GROW_TOL_PX)
        if len(pi) >= 12:
            deg = 2 if len(pi) < 120 else 3
            for _ in range(2):
                sky = SkyCoord(ref_radec[pj, 0] * u.deg, ref_radec[pj, 1] * u.deg)
                w2 = fit_wcs_from_points((stars[pi, 0], stars[pi, 1]), sky,
                                         projection="TAN", sip_degree=deg)
                px = _all_w2p(w2, ref_radec[pj])
                d = np.hypot(*(stars[pi, :2] - px).T)
                good = d <= CLIP_PX
                if good.all():
                    break
                pi, pj = pi[good], pj[good]
            w = w2
            fitted = True
        if R > 20000:
            break
        R += GROW_STEP_PX
    if not fitted:
        return AstrometryResult(False, reason="NO_FIT",
                                n_det=len(stars), n_ref=len(ref_radec))

    pi, pj = match(w, np.ones(len(stars), bool), FINAL_TOL_PX)
    if len(pi) < min_match:
        return AstrometryResult(False, reason=f"FEW_MATCHES({len(pi)})",
                                n_det=len(stars), n_ref=len(ref_radec),
                                n_match=len(pi))
    cd = w.pixel_scale_matrix
    scale = float(np.sqrt(abs(np.linalg.det(cd))) * 3600.0)
    px = _all_w2p(w, ref_radec[pj])
    d = np.hypot(*(stars[pi, :2] - px).T) * scale
    rms = float(np.sqrt(np.mean(d ** 2)))
    if rms > max_rms:
        return AstrometryResult(False, reason=f"HIGH_RMS({rms:.2f}as)",
                                n_det=len(stars), n_ref=len(ref_radec),
                                n_match=len(pi), rms_arcsec=rms)
    h = w.to_header(relax=True)
    cards = [("CTYPE1", "RA---TAN-SIP", "solved WCS"),
             ("CTYPE2", "DEC--TAN-SIP", "solved WCS"),
             ("CRVAL1", float(h["CRVAL1"]), "solved WCS"),
             ("CRVAL2", float(h["CRVAL2"]), "solved WCS"),
             ("CRPIX1", float(h["CRPIX1"]), "solved WCS"),
             ("CRPIX2", float(h["CRPIX2"]), "solved WCS"),
             ("CD1_1", float(cd[0, 0]), "solved WCS"),
             ("CD1_2", float(cd[0, 1]), "solved WCS"),
             ("CD2_1", float(cd[1, 0]), "solved WCS"),
             ("CD2_2", float(cd[1, 1]), "solved WCS"),
             ("A_ORDER", int(h["A_ORDER"]), "SIP order"),
             ("B_ORDER", int(h["B_ORDER"]), "SIP order")]
    for k in sorted(h.keys()):
        if k.startswith(("A_", "B_")) and not k.endswith("ORDER"):
            cards.append((k, float(h[k]), "SIP distortion"))
    cards.append(("WCSAPPRX", False, "WCS solved against reference catalog"))
    return AstrometryResult(True, n_det=len(stars), n_ref=len(ref_radec),
                            n_match=len(pi), rms_arcsec=rms, cards=cards)


def fetch_gaia_cone(ra_deg: float, dec_deg: float, radius_arcmin: float = 100.0,
                    gmax: float = 19.0, out_path=None, timeout: int = 240):
    """Gaia DR3 cone from VizieR (network required) -> (n,3) array or FITS."""
    import subprocess
    url = ("https://vizier.cds.unistra.fr/viz-bin/asu-tsv?-source=I/355/gaiadr3"
           f"&-c={ra_deg:.5f}%20{dec_deg:+.5f}&-c.rm={radius_arcmin:.1f}"
           f"&-out=RA_ICRS,DE_ICRS,Gmag&Gmag=%3C{gmax:g}&-out.max=200000")
    raw = subprocess.run(["curl", "-s", "--max-time", str(timeout), url],
                         capture_output=True, text=True, check=True).stdout
    rows = []
    for line in raw.splitlines():
        if not line or line.startswith(("#", "-", "RA_", "deg")):
            continue
        p = line.split("\t")
        if len(p) >= 3:
            try:
                rows.append((float(p[0]), float(p[1]), float(p[2])))
            except ValueError:
                continue
    data = np.array(rows)
    if out_path is None:
        return data
    cols = fits.ColDefs([
        fits.Column("RA", "D", unit="deg", array=data[:, 0]),
        fits.Column("DEC", "D", unit="deg", array=data[:, 1]),
        fits.Column("GMAG", "E", array=data[:, 2]),
    ])
    tbl = fits.BinTableHDU.from_columns(cols, name="REFCAT")
    tbl.header["CATALOG"] = ("GaiaDR3(VizieR)", "source catalog")
    tbl.header["CONERA"] = (ra_deg, "cone center RA [deg]")
    tbl.header["CONEDEC"] = (dec_deg, "cone center DEC [deg]")
    tbl.header["CONERAD"] = (radius_arcmin, "cone radius [arcmin]")
    tbl.header["GMAGMAX"] = (gmax, "magnitude limit")
    fits.HDUList([fits.PrimaryHDU(), tbl]).writeto(out_path, overwrite=True)
    return data

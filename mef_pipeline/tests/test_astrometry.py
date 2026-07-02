import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from kmt_ceu_preproc.astrometry import (detect_stars, load_refcat, make_refcat,
                                        solve_tan)

RNG = np.random.default_rng(7)
NY, NX = 400, 400


def true_wcs_header() -> fits.Header:
    h = fits.Header()
    h["NAXIS"], h["NAXIS1"], h["NAXIS2"] = 2, NX, NY
    h["CTYPE1"], h["CTYPE2"] = "RA---TAN", "DEC--TAN"
    h["CRVAL1"], h["CRVAL2"] = 150.0, -30.0
    h["CRPIX1"], h["CRPIX2"] = 200.0, 200.0
    h["CD1_1"], h["CD1_2"] = -1e-4, 0.0
    h["CD2_1"], h["CD2_2"] = 0.0, 1e-4
    return h


def render_field(n_stars=80):
    """Gaussian stars at random pixels; returns (image, star_xy, catalog_radec)."""
    xy = np.column_stack([RNG.uniform(30, NX - 30, n_stars),
                          RNG.uniform(30, NY - 30, n_stars)])
    img = np.full((NY, NX), 100.0, dtype=np.float32)
    yy, xx = np.mgrid[0:NY, 0:NX]
    for x, y in xy:
        img += 5000.0 * np.exp(-(((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.2 ** 2)))
    img += RNG.normal(0, 2.0, img.shape).astype(np.float32)
    w = WCS(true_wcs_header())
    ra, dec = w.wcs_pix2world(xy[:, 0], xy[:, 1], 0)
    return img, xy, np.column_stack([ra, dec])


class TestAstrometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.img, cls.xy, cls.cat = render_field()

    def test_detect_stars(self):
        stars = detect_stars(self.img, sigma=5.0)
        self.assertGreater(len(stars), 50)
        # every detection should sit near a true star
        d = np.sqrt(((stars[:, None, :2] - self.xy[None, :, :]) ** 2).sum(axis=2))
        self.assertLess(float(np.median(d.min(axis=1))), 0.3)

    def test_solve_recovers_perturbed_wcs(self):
        hdr = true_wcs_header()
        hdr["CRPIX1"] += 6.0     # perturb the initial guess
        hdr["CRPIX2"] -= 8.0
        rot = np.radians(0.3)    # small rotation error
        cd = np.array([[hdr["CD1_1"], hdr["CD1_2"]], [hdr["CD2_1"], hdr["CD2_2"]]])
        r = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
        cd = cd @ r
        hdr["CD1_1"], hdr["CD1_2"] = cd[0]
        hdr["CD2_1"], hdr["CD2_2"] = cd[1]
        res = solve_tan(self.img, None, hdr, self.cat)
        self.assertTrue(res.solved, res.reason)
        self.assertLess(res.rms_arcsec, 0.1)
        self.assertGreaterEqual(res.n_match, 40)
        # solved WCS must map detected pixels onto the catalog
        solved = fits.Header(true_wcs_header())
        for k, v, *_ in res.cards:
            solved[k] = v
        w = WCS(solved)
        ra, dec = w.wcs_pix2world(self.xy[:, 0], self.xy[:, 1], 0)
        sep = np.hypot((ra - self.cat[:, 0]) * np.cos(np.radians(dec)),
                       dec - self.cat[:, 1]) * 3600.0
        self.assertLess(float(np.median(sep)), 0.1)

    def test_solve_recovers_large_pointing_offset(self):
        # TCS repeatability can exceed the fine match radius: the global-offset
        # pre-estimation must still lock on (here 120 px ~ 43 arcsec off)
        hdr = true_wcs_header()
        hdr["CRPIX1"] += 120.0
        hdr["CRPIX2"] -= 90.0
        res = solve_tan(self.img, None, hdr, self.cat)
        self.assertTrue(res.solved, res.reason)
        self.assertLess(res.rms_arcsec, 0.1)

    def test_failure_flags(self):
        hdr = true_wcs_header()
        flat_img = np.full((NY, NX), 100.0, dtype=np.float32)
        res = solve_tan(flat_img, None, hdr, self.cat)
        self.assertFalse(res.solved)
        self.assertTrue(res.reason.startswith("FEW_STARS"))
        far = self.cat + np.array([5.0, 5.0])  # catalog far off the field
        res = solve_tan(self.img, None, hdr, far)
        self.assertFalse(res.solved)
        self.assertTrue(res.reason.startswith(("FEW_REF_IN_FIELD", "FEW_MATCHES")))

    def test_refcat_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            l1 = Path(tmp) / "kmtc.20260101.000001.ceu.l1ccd.mef.fits"
            hdr = true_wcs_header()
            hdr["EXTNAME"] = "SCI_M"
            fits.HDUList([fits.PrimaryHDU(),
                          fits.ImageHDU(data=self.img, header=hdr)]).writeto(l1)
            out = Path(tmp) / "refcat.fits"
            res = make_refcat(l1, out)
            self.assertGreater(res["n_stars"], 50)
            cat = load_refcat(out)
            self.assertEqual(cat.shape[1], 2)
            # extracted catalog should solve the same image
            sol = solve_tan(self.img, None, true_wcs_header(), cat)
            self.assertTrue(sol.solved, sol.reason)
            self.assertLess(sol.rms_arcsec, 0.05)


if __name__ == "__main__":
    unittest.main()

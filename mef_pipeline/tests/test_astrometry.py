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


def big_field(n_stars=300, ny=800, nx=800, seed=11):
    rng = np.random.default_rng(seed)
    hdr = fits.Header()
    hdr["NAXIS"], hdr["NAXIS1"], hdr["NAXIS2"] = 2, nx, ny
    hdr["CTYPE1"], hdr["CTYPE2"] = "RA---TAN", "DEC--TAN"
    hdr["CRVAL1"], hdr["CRVAL2"] = 150.0, -30.0
    hdr["CRPIX1"], hdr["CRPIX2"] = nx / 2, ny / 2
    hdr["CD1_1"], hdr["CD1_2"] = -1.0975e-4, 0.0
    hdr["CD2_1"], hdr["CD2_2"] = 0.0, 1.0975e-4
    xy = np.column_stack([rng.uniform(30, nx - 30, n_stars),
                          rng.uniform(30, ny - 30, n_stars)])
    img = np.full((ny, nx), 100.0, dtype=np.float32)
    yy, xx = np.mgrid[0:ny, 0:nx]
    for x, y in xy:
        img += 4000.0 * np.exp(-(((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.2 ** 2)))
    img += rng.normal(0, 2.0, img.shape).astype(np.float32)
    w = WCS(hdr)
    ra, dec = w.wcs_pix2world(xy[:, 0], xy[:, 1], 0)
    return img, hdr, np.column_stack([ra, dec])


class TestSolveField(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kmt_ceu_preproc.astrometry import solve_field
        cls.solve_field = staticmethod(solve_field)
        cls.img, cls.true_hdr, cls.cat = big_field()

    def test_solves_realistic_initial_error(self):
        # shift + rotation + the 1.3% legacy scale error, like real frames
        hdr = self.true_hdr.copy()
        hdr["CRPIX1"] += 80.0
        hdr["CRPIX2"] -= 60.0
        cd = np.array([[hdr["CD1_1"], hdr["CD1_2"]], [hdr["CD2_1"], hdr["CD2_2"]]])
        rot = np.radians(0.3)
        cd = cd @ np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
        cd *= 1.013
        (hdr["CD1_1"], hdr["CD1_2"]), (hdr["CD2_1"], hdr["CD2_2"]) = cd
        res = self.solve_field(self.img, None, hdr, self.cat)
        self.assertTrue(res.solved, res.reason)
        self.assertGreaterEqual(res.n_match, 120)
        self.assertLess(res.rms_arcsec, 0.1)
        keys = [c[0] for c in res.cards]
        self.assertIn("A_ORDER", keys)
        self.assertIn(("WCSAPPRX"), keys)

    def test_flags_without_stars(self):
        flat = np.full((800, 800), 100.0, dtype=np.float32)
        res = self.solve_field(flat, None, self.true_hdr, self.cat)
        self.assertFalse(res.solved)
        self.assertTrue(res.reason.startswith("FEW_STARS"))


class TestTemplate(unittest.TestCase):
    def test_parse_pointing(self):
        from kmt_ceu_preproc.astrometry import parse_pointing
        h = fits.Header()
        h["RA"], h["DEC"] = "10:57:21.00", "-14:26:22.3"
        ra, dec = parse_pointing(h)
        self.assertAlmostEqual(ra, 164.3375, places=4)
        self.assertAlmostEqual(dec, -14.4395, places=3)
        h["RA"], h["DEC"] = 200.5, -30.25
        self.assertEqual(parse_pointing(h), (200.5, -30.25))
        self.assertIsNone(parse_pointing(fits.Header()))

    def test_rescale_cd(self):
        from kmt_ceu_preproc.astrometry import (NOMINAL_PIX_SCALE,
                                                rescale_cd_to_nominal)
        h = fits.Header()
        h["CD1_1"], h["CD1_2"] = -0.4004 / 3600, 0.0
        h["CD2_1"], h["CD2_2"] = 0.0, 0.4004 / 3600
        rescale_cd_to_nominal(h)
        scale = np.sqrt(abs(h["CD1_1"] * h["CD2_2"])) * 3600
        self.assertAlmostEqual(scale, NOMINAL_PIX_SCALE, places=5)

    def test_template_header(self):
        from kmt_ceu_preproc.astrometry import (load_astrom_template,
                                                template_wcs_header)
        tmpl = load_astrom_template()
        self.assertIsNotNone(tmpl, "data/astrom_template.json missing")
        h = template_wcs_header("M", 164.3375, -14.4395, 9216, 9232, tmpl)
        self.assertEqual(h["CTYPE1"], "RA---TAN-SIP")
        w = WCS(h)
        scale = np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix))) * 3600
        self.assertAlmostEqual(scale, 0.3952, places=3)
        # chip M center sits NE of the pointing by ~0.77 deg
        ra, dec = (float(v) for v in w.all_pix2world([[4608, 4616]], 0)[0])
        sep = np.hypot((ra - 164.3375) * np.cos(np.radians(dec)), dec + 14.4395)
        self.assertAlmostEqual(sep, 0.773, delta=0.02)
        self.assertIsNone(template_wcs_header("X", 164.0, -14.0, 100, 100, tmpl))

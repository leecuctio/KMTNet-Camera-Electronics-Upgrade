"""Unit tests for the v1.6 survey-standard steps:
fringe, illumination, cosmic-ray flagging, sky model, photometric zero point."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from astropy.io import fits  # noqa: E402
from astropy.wcs import WCS  # noqa: E402

import fixtures  # noqa: E402
from kmt_ceu_preproc import MASK_CR, MASK_SAT  # noqa: E402
from kmt_ceu_preproc.background import block_smooth  # noqa: E402
from kmt_ceu_preproc.calib.caldb import CalDB  # noqa: E402
from kmt_ceu_preproc.calib.masters import (build_master_fringe,  # noqa: E402
                                           build_master_illum)
from kmt_ceu_preproc.pipeline import PipelineConfig  # noqa: E402
from kmt_ceu_preproc.steps.crflag import flag_cosmics  # noqa: E402
from kmt_ceu_preproc.steps.fringe import fringe_scale, subtract_fringe  # noqa: E402
from kmt_ceu_preproc.steps.illum import divide_illum  # noqa: E402
from kmt_ceu_preproc.steps.photzp import measure_zp  # noqa: E402
from kmt_ceu_preproc.steps.sky import sky_model  # noqa: E402


class FakeMaster:
    name = "fake_master.fits"
    calver = "TEST-1"

    def __init__(self, planes: dict):
        self._planes = planes

    def plane(self, extname: str) -> np.ndarray:
        return self._planes[extname].astype(np.float32)


def gaussian_star(shape, x0, y0, amp, sigma=1.2):
    y, x = np.mgrid[:shape[0], :shape[1]]
    return amp * np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * sigma ** 2))


class TestSkyModel(unittest.TestCase):
    def test_gradient_recovered_and_subtracted(self):
        ny, nx = 640, 512
        y = np.arange(ny)[:, None]
        sci = (100.0 + 0.05 * y * np.ones((1, nx))).astype(np.float32)
        stats = sky_model(sci.copy(), None, box=128, subtract=False)
        self.assertAlmostEqual(stats["sky_med_e"], 100 + 0.05 * ny / 2, delta=2.0)
        self.assertAlmostEqual(stats["grad_y_e"], 0.05 * (ny - 128), delta=3.0)
        self.assertAlmostEqual(stats["grad_x_e"], 0.0, delta=0.5)
        sub = sci.copy()
        stats2 = sky_model(sub, None, box=128, subtract=True)
        self.assertTrue(stats2["subtracted"])
        # interior residual after subtraction is small (edges extrapolate)
        inner = sub[128:-128, 128:-128]
        self.assertLess(float(np.median(np.abs(inner))), 0.5)

    def test_masked_stars_ignored(self):
        rng = np.random.default_rng(1)
        sci = rng.normal(200.0, 3.0, (512, 512)).astype(np.float32)
        mask = np.zeros_like(sci, dtype=np.uint8)
        sci[100:110, 100:110] = 60000.0
        mask[100:110, 100:110] = MASK_SAT
        stats = sky_model(sci, mask, box=128)
        self.assertAlmostEqual(stats["sky_med_e"], 200.0, delta=1.0)


class TestCRFlag(unittest.TestCase):
    def _frame(self):
        rng = np.random.default_rng(7)
        sky, rn = 400.0, 5.0
        sci = rng.normal(sky, np.sqrt(sky + rn ** 2), (600, 500)).astype(np.float32)
        return sci, rn

    def test_crs_flagged_stars_kept(self):
        sci, rn = self._frame()
        # stars (FWHM ~2.8 px, marginally sampled like KMTNet)
        star_xy = [(100, 100), (250, 300), (400, 150), (120, 450)]
        for x0, y0 in star_xy:
            sci += gaussian_star(sci.shape, x0, y0, 30000.0).astype(np.float32)
        # single/double-pixel cosmic rays
        cr_xy = [(50, 200), (300, 50), (450, 400), (200, 480)]
        for x0, y0 in cr_xy:
            sci[y0, x0] += 5000.0
        sci[300, 51] += 4000.0     # 2-px event
        mask = np.zeros(sci.shape, dtype=np.uint8)
        n = flag_cosmics(sci, mask, rn)
        self.assertGreaterEqual(n, len(cr_xy))
        for x0, y0 in cr_xy:
            self.assertTrue(mask[y0, x0] & MASK_CR, f"CR at ({x0},{y0}) missed")
        for x0, y0 in star_xy:
            core = mask[y0 - 1:y0 + 2, x0 - 1:x0 + 2] & MASK_CR
            self.assertFalse(core.any(), f"star core at ({x0},{y0}) falsely flagged")

    def test_saturation_guard(self):
        sci, rn = self._frame()
        mask = np.zeros(sci.shape, dtype=np.uint8)
        sci[200:220, 200:203] = 65000.0        # bleed-like column
        mask[200:220, 200:203] |= MASK_SAT
        flag_cosmics(sci, mask, rn)
        near = mask[198:222, 198:205] & MASK_CR
        self.assertFalse(near.any(), "flags adjacent to saturation")


class TestFringe(unittest.TestCase):
    def _pattern(self, shape):
        y, x = np.mgrid[:shape[0], :shape[1]]
        return (np.sin(2 * np.pi * x / 7.3) * np.sin(2 * np.pi * y / 11.1)).astype(np.float32)

    def test_scale_fit_and_subtraction(self):
        rng = np.random.default_rng(3)
        shape = (400, 300)
        f = 0.02 * self._pattern(shape)               # 2% of sky template
        sky = 1500.0
        sci = (sky + sky * f + rng.normal(0, 4.0, shape)).astype(np.float32)
        master = FakeMaster({"A01T": f})
        before = float(np.std(sci - block_smooth(sci, 64)))
        applied, scale = subtract_fringe(sci, None, "A01T", master, sky)
        self.assertTrue(applied)
        self.assertAlmostEqual(scale, sky, delta=0.1 * sky)
        after = float(np.std(sci - block_smooth(sci, 64)))
        self.assertLess(after, 0.3 * before)

    def test_negligible_template_skipped(self):
        rng = np.random.default_rng(4)
        f = rng.normal(0, 1e-6, (200, 150)).astype(np.float32)   # noise template
        sci = np.full((200, 150), 900.0, dtype=np.float32)
        applied, scale = subtract_fringe(sci, None, "A01T", FakeMaster({"A01T": f}), 900.0)
        self.assertFalse(applied)
        self.assertEqual(scale, 0.0)
        self.assertTrue(np.all(sci == 900.0))

    def test_scale_zero_when_no_fringe_in_data(self):
        f = 0.02 * self._pattern((400, 300))
        rng = np.random.default_rng(5)
        sci = (2000.0 + rng.normal(0, 5.0, (400, 300))).astype(np.float32)
        scale, n = fringe_scale(sci, f, None, 2000.0)
        self.assertLess(scale, 0.05 * 2000.0)


class TestIllum(unittest.TestCase):
    def test_divide_and_clamp(self):
        plane = np.full((100, 80), 1.05, dtype=np.float32)
        plane[0, 0] = 3.0                     # out-of-range -> clamped
        sci = np.full((100, 80), 210.0, dtype=np.float32)
        var = np.full((100, 80), 210.0, dtype=np.float32)
        dev, n_cl = divide_illum(sci, var, "A01T", FakeMaster({"A01T": plane}))
        self.assertEqual(n_cl, 1)
        self.assertAlmostEqual(float(sci[50, 40]), 200.0, places=3)
        self.assertAlmostEqual(float(var[50, 40]), 210.0 / 1.05 ** 2, places=2)
        self.assertAlmostEqual(dev, 1.0, places=3)   # clamped max = 2.0


class TestSkyMastersBuilders(unittest.TestCase):
    """calib-fringe / calib-illum end-to-end on synthetic mini L0 frames."""

    def _make_frames(self, tmp, modulate, n=4):
        paths = []
        for k in range(n):
            def amp_adu(extname, _k=k):
                base = fixtures.default_amp_adu(extname)      # 500 ramp + 100 data
                ny, nx = base.shape
                mod = modulate(extname, ny, nx, _k)
                base[:, :fixtures.NDATA] += mod[:, :fixtures.NDATA]
                return base
            p = tmp / f"synth_obj_{k}.fits"
            fixtures.make_synth_l0(p, imagetyp="OBJECT", amp_adu=amp_adu,
                                   filt="I", exptime=60.0,
                                   date_obs=f"2026-06-30T0{k}:00:00")
            paths.append(str(p))
        return paths

    def test_fringe_builder_recovers_pattern(self):
        y, x = np.mgrid[:fixtures.NY, :fixtures.NX]
        pattern = np.sin(2 * np.pi * x / 5.7) * np.sin(2 * np.pi * y / 4.3)

        def modulate(extname, ny, nx, k):
            return 10.0 * pattern            # 10 ADU fringe on ~100 ADU signal

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            paths = self._make_frames(tmp, modulate)
            caldb = CalDB(tmp / "caldb")
            out = tmp / "master_fringe_I.fits"
            res = build_master_fringe(paths, out, caldb, PipelineConfig(),
                                      bias_path=None, flat_path=None, box=8)
            self.assertGreater(res["median_amp"], 1e-3)
            with fits.open(out) as hdul:
                plane = np.asarray(hdul["M01T"].data, dtype=np.float64)
            pat = pattern[:, :fixtures.NDATA] - pattern[:, :fixtures.NDATA].mean()
            corr = np.corrcoef(plane.ravel(), pat.ravel())[0, 1]
            self.assertGreater(corr, 0.7, f"template/injection corr {corr:.2f}")
            self.assertIsNotNone(caldb.find("MFRINGE", filt="I"))

    def test_illum_builder_recovers_gradient(self):
        def modulate(extname, ny, nx, k):
            gx = np.linspace(-0.1, 0.1, nx)[None, :]     # +-10% illumination slope
            return 100.0 * gx * np.ones((ny, 1))

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            paths = self._make_frames(tmp, modulate)
            caldb = CalDB(tmp / "caldb")
            out = tmp / "master_illum_I.fits"
            res = build_master_illum(paths, out, caldb, PipelineConfig(),
                                     bias_path=None, flat_path=None, box=8)
            with fits.open(out) as hdul:
                plane = np.asarray(hdul["M01T"].data, dtype=np.float64)
            left = float(np.median(plane[:, :4]))
            right = float(np.median(plane[:, -4:]))
            self.assertGreater(right - left, 0.05, "gradient not recovered")
            self.assertLess(abs(float(np.median(plane)) - 1.0), 0.02)
            self.assertIsNotNone(caldb.find("MILLUM", filt="I"))


class TestPhotZP(unittest.TestCase):
    def test_zp_recovered(self):
        ny = nx = 512
        zp_true, exptime = 25.0, 60.0
        sky = 100.0
        sci = np.full((ny, nx), sky, dtype=np.float32)
        rng = np.random.default_rng(11)
        xs = rng.uniform(60, nx - 60, 30)
        ys = rng.uniform(60, ny - 60, 30)
        # enforce minimum separation for the detector
        keep = []
        for i in range(30):
            if all(max(abs(xs[i] - xs[j]), abs(ys[i] - ys[j])) > 40 for j in keep):
                keep.append(i)
        xs, ys = xs[keep], ys[keep]
        sigma = 1.2
        fluxes = 10 ** rng.uniform(4.2, 5.2, len(xs))
        for x0, y0, fl in zip(xs, ys, fluxes):
            amp = fl / (2 * np.pi * sigma ** 2)
            sci += gaussian_star(sci.shape, x0, y0, amp, sigma).astype(np.float32)

        hdr = fits.Header()
        hdr["NAXIS"] = 2
        hdr["NAXIS1"], hdr["NAXIS2"] = nx, ny
        hdr["CTYPE1"], hdr["CTYPE2"] = "RA---TAN", "DEC--TAN"
        hdr["CRVAL1"], hdr["CRVAL2"] = 150.0, -30.0
        hdr["CRPIX1"], hdr["CRPIX2"] = nx / 2, ny / 2
        hdr["CD1_1"], hdr["CD1_2"] = -1e-4, 0.0
        hdr["CD2_1"], hdr["CD2_2"] = 0.0, 1e-4
        w = WCS(hdr)
        ra, dec = w.all_pix2world(xs, ys, 0)
        gmag = zp_true - 2.5 * np.log10(fluxes / exptime)
        ref = np.column_stack([ra, dec, gmag])
        cards = [(k, hdr[k]) for k in
                 ("CTYPE1", "CTYPE2", "CRVAL1", "CRVAL2", "CRPIX1", "CRPIX2",
                  "CD1_1", "CD1_2", "CD2_1", "CD2_2")]
        res = measure_zp(sci, None, cards, ref, exptime)
        self.assertTrue(res.measured, res.reason)
        self.assertGreaterEqual(res.n_star, 10)
        self.assertAlmostEqual(res.zp, zp_true, delta=0.05)

    def test_requires_gmag(self):
        sci = np.full((256, 256), 100.0, dtype=np.float32)
        ref2 = np.zeros((50, 2))
        res = measure_zp(sci, None, [("CTYPE1", "RA---TAN")], ref2, 60.0)
        self.assertFalse(res.measured)
        self.assertEqual(res.reason, "NO_REF_MAG")


if __name__ == "__main__":
    unittest.main()

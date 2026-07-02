"""End-to-end test on a synthetic miniature night: 3 bias + 2 flats + 1 object
-> master bias/flat/BPM -> L1, with checkable arithmetic (gain 2.0 e-/ADU)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from astropy.io import fits

import fixtures
from fixtures import GAIN, NDATA, NY, RDNOISE, make_synth_l0
from kmt_ceu_preproc import MASK_BAD, MASK_SAT
from kmt_ceu_preproc.calib.bpm import build_bpm
from kmt_ceu_preproc.calib.caldb import CalDB
from kmt_ceu_preproc.calib.masters import build_master_bias, build_master_flat
from kmt_ceu_preproc.pipeline import PipelineConfig, l1_name_for, process_exposure

RAMP = lambda: 500.0 + 0.2 * np.arange(NY)[:, None]  # noqa: E731

BIAS_PATTERN = 4.0  # ADU checkerboard amplitude


def bias_adu(extname):
    adu = np.zeros((NY, fixtures.NX)) + RAMP()
    yy, xx = np.mgrid[0:NY, 0:fixtures.NX]
    adu[:, :NDATA] += BIAS_PATTERN * ((xx + yy) % 2)[:, :NDATA]
    return adu


def flat_adu(extname):
    adu = bias_adu(extname)
    adu[:, :NDATA] += 20000.0
    return adu


SKY_ADU = 100.0
STAR_ADU = 5000.0


def object_adu(extname):
    adu = bias_adu(extname)
    adu[:, :NDATA] += SKY_ADU
    if extname == "M01T":
        adu[10:14, 5:9] += STAR_ADU     # star block
        adu[30, 3] = 65000.0            # saturated pixel
    return adu


class TestEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.out = root / "l1"
        cls.caldb = CalDB(cls.out / "caldb")
        cls.config = PipelineConfig(expected_amps=4, overscan_smooth=5,
                                    compute_sha256=False, with_mask_file=True)
        biases = [make_synth_l0(root / f"bias{i}.fits", "BIAS", bias_adu, exptime=0)
                  for i in range(3)]
        flats = [make_synth_l0(root / f"flat{i}.fits", "FLAT", flat_adu) for i in range(2)]
        cls.obj = make_synth_l0(root / "kmtc.20260630.000001.ceu.l0amp.mock64.mef.fits",
                                "OBJECT", object_adu)
        cls.bias_res = build_master_bias(
            biases, cls.out / "caldb" / "master_bias.fits", cls.caldb, cls.config)
        cls.flat_res = build_master_flat(
            flats, cls.out / "caldb" / "master_flat_V.fits", cls.caldb, cls.config,
            bias_path=cls.out / "caldb" / "master_bias.fits")
        cls.bpm_res = build_bpm(cls.out / "caldb" / "master_flat_V.fits",
                                cls.out / "caldb" / "bpm.fits", cls.caldb)
        cls.qa = process_exposure(cls.obj, cls.caldb, cls.out, cls.config)
        cls.l1_path = cls.out / cls.qa["l1_file"]
        cls.mask_path = cls.out / cls.l1_path.name.replace(".mef.fits", ".mask.mef.fits")
        # second run with VAR planes enabled, mask file off (defaults elsewhere)
        var_config = PipelineConfig(expected_amps=4, overscan_smooth=5,
                                    compute_sha256=False, with_var=True)
        cls.out_var = root / "l1var"
        qa_var = process_exposure(cls.obj, cls.caldb, cls.out_var, var_config)
        cls.l1_var_path = cls.out_var / qa_var["l1_file"]

    def read_mask(self, chip="M"):
        with fits.open(self.mask_path) as hdul:
            return np.asarray(hdul[f"MASK_{chip}"].data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_l1_naming(self):
        self.assertEqual(l1_name_for(self.obj), "kmtc.20260630.000001.ceu.l1ccd.mef.fits")

    def test_master_bias_recovers_pattern(self):
        with fits.open(self.out / "caldb" / "master_bias.fits") as hdul:
            plane = np.asarray(hdul["M01T"].data)
            yy, xx = np.mgrid[0:NY, 0:NDATA]
            odd = ((xx + yy) % 2) == 1
            amp = float(np.median(plane[odd]) - np.median(plane[~odd]))
            self.assertAlmostEqual(amp, BIAS_PATTERN, delta=0.5)

    def test_master_flat_is_unity(self):
        with fits.open(self.out / "caldb" / "master_flat_V.fits") as hdul:
            for ext in ("M01T", "M02B"):
                med = float(np.median(np.asarray(hdul[ext].data)))
                self.assertAlmostEqual(med, 1.0, delta=0.01)

    def test_l1_structure_and_verify(self):
        with fits.open(self.l1_path) as hdul:
            hdul.verify("exception")
            names = [h.name for h in hdul]
            self.assertEqual(names, ["PRIMARY", "SCI_M", "CALHIST"])
            ph = hdul[0].header
            self.assertEqual(ph["DATAPROD"], "L1_CCD")
            self.assertEqual(ph["BUNIT"], "electron")
            self.assertTrue(ph["GAINAPPL"])
            self.assertFalse(ph["XTALKAPL"])
            self.assertFalse(ph["VARINCL"])
            self.assertEqual(ph["MASKFILE"], self.mask_path.name)
            self.assertEqual(ph["WCSNSOLV"], 0)
            # processing methods documented as COMMENT cards
            comments = "\n".join(str(c) for c in ph["COMMENT"])
            self.assertIn("AMPMATCH", comments)
            self.assertIn("(RDNOISE**2 + SCI*flat) / flat**2", comments)
            self.assertIn("s_a*m_a = s_b*m_b", comments)
            self.assertIn("(xi,eta) = CD @ (pix - CRPIX)", comments)
            sh = hdul["SCI_M"].header
            self.assertFalse(sh["WCSSOLVE"])
            self.assertEqual(sh["WCSFAIL"], "NO_REFCAT")
            self.assertEqual(ph["CALBIAS"], "master_bias.fits")
            self.assertEqual(hdul["SCI_M"].header["BUNIT"], "electron")
            self.assertEqual(hdul["SCI_M"].data.shape, (80, 48))
            steps = list(hdul["CALHIST"].data["STEP"])
            self.assertIn("OVERSCAN", steps)
            self.assertIn("ASSEMBLE", steps)
            applied = dict(zip(hdul["CALHIST"].data["STEP"],
                               hdul["CALHIST"].data["APPLIED"]))
            self.assertTrue(applied["BIAS"])
            self.assertFalse(applied["DARK"])
            self.assertFalse(applied["XTALK"])
            self.assertTrue(applied["AMPMATCH"])
            self.assertEqual(hdul["SCI_M"].header["AMMODE"], "multiplicative")

    def test_mask_file_layout(self):
        self.assertTrue(self.mask_path.exists())
        with fits.open(self.mask_path) as hdul:
            hdul.verify("exception")
            self.assertEqual([h.name for h in hdul], ["PRIMARY", "MASK_M"])
            self.assertEqual(hdul[0].header["DATAPROD"], "L1_MASK")
            self.assertEqual(hdul[0].header["L1FILE"], self.l1_path.name)
            self.assertEqual(hdul["MASK_M"].data.dtype, np.uint8)

    def test_mask_file_off_by_default(self):
        mask_sibling = self.l1_var_path.with_name(
            self.l1_var_path.name.replace(".mef.fits", ".mask.mef.fits"))
        self.assertFalse(mask_sibling.exists())
        with fits.open(self.l1_var_path) as hdul:
            self.assertEqual(hdul[0].header["MASKFILE"], "")
            self.assertNotIn("MASK_M", [h.name for h in hdul])

    def test_sky_level_in_electrons(self):
        with fits.open(self.l1_path) as hdul:
            sci = np.asarray(hdul["SCI_M"].data)
            mask = self.read_mask()
            sky = np.median(sci[(mask == 0)])
            self.assertAlmostEqual(float(sky), SKY_ADU * GAIN, delta=3.0)

    def test_star_and_saturation(self):
        with fits.open(self.l1_path) as hdul:
            sci = np.asarray(hdul["SCI_M"].data)
            mask = self.read_mask()
            # M01T ccdsec y 41:80, star at amp (y 10:14, x 5:9) -> ccd rows 50:54
            star = sci[50:54, 5:9] - SKY_ADU * GAIN
            self.assertAlmostEqual(float(np.median(star)), STAR_ADU * GAIN,
                                   delta=0.02 * STAR_ADU * GAIN)
            self.assertTrue(mask[70, 3] & MASK_SAT)  # amp y 30 -> ccd row 70

    def test_variance_plane_with_var(self):
        with fits.open(self.l1_var_path) as hdul:
            names = [h.name for h in hdul]
            self.assertEqual(names, ["PRIMARY", "SCI_M", "VAR_M", "CALHIST"])
            self.assertTrue(hdul[0].header["VARINCL"])
            self.assertEqual(hdul["VAR_M"].header["BUNIT"], "electron**2")
            var = np.asarray(hdul["VAR_M"].data)
            good = self.read_mask() == 0
            expected = SKY_ADU * GAIN + RDNOISE ** 2
            self.assertAlmostEqual(float(np.median(var[good])), expected,
                                   delta=0.05 * expected)

    def test_var_and_default_sci_identical(self):
        with fits.open(self.l1_path) as h1, fits.open(self.l1_var_path) as h2:
            self.assertTrue(np.array_equal(h1["SCI_M"].data, h2["SCI_M"].data))

    def test_astrometry_failure_flag_with_refcat(self):
        root = Path(self.tmp.name)
        cat = root / "tiny_refcat.fits"
        cols = fits.ColDefs([fits.Column("RA", "D", array=[150.0, 150.001]),
                             fits.Column("DEC", "D", array=[-30.0, -30.001])])
        fits.HDUList([fits.PrimaryHDU(),
                      fits.BinTableHDU.from_columns(cols)]).writeto(cat)
        cfg = PipelineConfig(expected_amps=4, overscan_smooth=5,
                             compute_sha256=False, refcat=str(cat))
        qa = process_exposure(cls_obj := self.obj, self.caldb, root / "l1ast", cfg)
        astro = qa["ccds"]["M"]["astrometry"]
        self.assertFalse(astro["solved"])
        self.assertTrue(astro["reason"].startswith(("FEW_", "NO_")))
        with fits.open(root / "l1ast" / qa["l1_file"]) as hdul:
            self.assertFalse(hdul["SCI_M"].header["WCSSOLVE"])
            self.assertTrue(str(hdul["SCI_M"].header["WCSFAIL"]).startswith(("FEW_", "NO_")))
            self.assertEqual(hdul[0].header["WCSNSOLV"], 0)

    def test_seams_small(self):
        for chip, rec in self.qa["ccds"].items():
            self.assertLess(rec["seam_max_abs_e"], 2.0)

    def test_ampmatch_corrects_gain_drift(self):
        root = Path(self.tmp.name)

        def drift_adu(extname):
            adu = bias_adu(extname)
            adu[:, :NDATA] += SKY_ADU * (1.05 if extname == "M02T" else 1.0)
            return adu

        obj = make_synth_l0(root / "kmtc.20260630.000002.ceu.l0amp.mock64.mef.fits",
                            "OBJECT", drift_adu)
        qa = process_exposure(obj, self.caldb, self.out, self.config)
        ccd = qa["ccds"]["M"]
        am = ccd["ampmatch"]
        self.assertEqual(am["mode"], "multiplicative")
        self.assertLess(am["corr"]["M02T"], 1.0)   # drifted amp scaled back down
        # a 5% gain drift would leave a ~10 e- seam; matching removes it
        self.assertLess(ccd["seam_max_abs_e"], 1.0)

    def test_overscan_contamination_recovery(self):
        root = Path(self.tmp.name)

        def contaminated_adu(extname):
            adu = bias_adu(extname)
            adu[:, :NDATA] += SKY_ADU
            if extname == "M01T":
                adu += 300.0                     # whole-amp baseline jump
                adu[:, NDATA:] += SKY_ADU        # overscan follows the sky too
            return adu

        obj = make_synth_l0(root / "kmtc.20260630.000003.ceu.l0amp.mock64.mef.fits",
                            "OBJECT", contaminated_adu)
        qa = process_exposure(obj, self.caldb, self.out, self.config)
        self.assertTrue(qa["amps"]["M01T"]["ovsc_fallback"])
        self.assertFalse(qa["amps"]["M02T"]["ovsc_fallback"])
        ccd = qa["ccds"]["M"]
        # fallback chip is matched additively, anchored on the healthy amps
        self.assertEqual(ccd["ampmatch"]["mode"], "additive")
        self.assertLess(ccd["seam_max_abs_e"], 2.0)
        from kmt_ceu_preproc import MASK_NOOVSC
        mask_file = self.out / qa["l1_file"].replace(".mef.fits", ".mask.mef.fits")
        with fits.open(self.out / qa["l1_file"]) as hdul, fits.open(mask_file) as mh:
            sci = np.asarray(hdul["SCI_M"].data)
            mask = np.asarray(mh["MASK_M"].data)
            # M01T occupies ccd rows 41:80, cols 1:24; the whole amp carries the
            # NO_OVERSCAN_FIT flag (expected), so only exclude the other bits
            sel = (mask[45:75, 12:22] & ~np.uint8(MASK_NOOVSC)) == 0
            zone = sci[45:75, 12:22][sel]
            self.assertAlmostEqual(float(np.median(zone)), SKY_ADU * GAIN, delta=5.0)
            self.assertTrue((mask[45:75, 2:22] & MASK_NOOVSC).all())
            self.assertEqual(int(mask[10, 10]) & MASK_NOOVSC, 0)

    def test_qa_record(self):
        self.assertEqual(self.qa["masters"]["bias"], "master_bias.fits")
        self.assertEqual(len(self.qa["amps"]), 4)
        self.assertGreater(self.qa["amps"]["M01T"]["n_sat"], 0)
        self.assertTrue(all(a["gain_measured"] for a in self.qa["amps"].values()))


if __name__ == "__main__":
    unittest.main()

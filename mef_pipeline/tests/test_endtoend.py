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
                                    compute_sha256=False)
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
        # second run with VAR planes enabled (non-default)
        var_config = PipelineConfig(expected_amps=4, overscan_smooth=5,
                                    compute_sha256=False, with_var=True)
        cls.out_var = root / "l1var"
        qa_var = process_exposure(cls.obj, cls.caldb, cls.out_var, var_config)
        cls.l1_var_path = cls.out_var / qa_var["l1_file"]

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
            self.assertEqual(names, ["PRIMARY", "SCI_M", "MASK_M", "CALHIST"])
            ph = hdul[0].header
            self.assertEqual(ph["DATAPROD"], "L1_CCD")
            self.assertEqual(ph["BUNIT"], "electron")
            self.assertTrue(ph["GAINAPPL"])
            self.assertFalse(ph["XTALKAPL"])
            self.assertFalse(ph["VARINCL"])
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

    def test_sky_level_in_electrons(self):
        with fits.open(self.l1_path) as hdul:
            sci = np.asarray(hdul["SCI_M"].data)
            mask = np.asarray(hdul["MASK_M"].data)
            sky = np.median(sci[(mask == 0)])
            self.assertAlmostEqual(float(sky), SKY_ADU * GAIN, delta=3.0)

    def test_star_and_saturation(self):
        with fits.open(self.l1_path) as hdul:
            sci = np.asarray(hdul["SCI_M"].data)
            mask = np.asarray(hdul["MASK_M"].data)
            # M01T ccdsec y 41:80, star at amp (y 10:14, x 5:9) -> ccd rows 50:54
            star = sci[50:54, 5:9] - SKY_ADU * GAIN
            self.assertAlmostEqual(float(np.median(star)), STAR_ADU * GAIN,
                                   delta=0.02 * STAR_ADU * GAIN)
            self.assertTrue(mask[70, 3] & MASK_SAT)  # amp y 30 -> ccd row 70

    def test_variance_plane_with_var(self):
        with fits.open(self.l1_var_path) as hdul:
            names = [h.name for h in hdul]
            self.assertEqual(names, ["PRIMARY", "SCI_M", "VAR_M", "MASK_M", "CALHIST"])
            self.assertTrue(hdul[0].header["VARINCL"])
            self.assertEqual(hdul["VAR_M"].header["BUNIT"], "electron**2")
            var = np.asarray(hdul["VAR_M"].data)
            mask = np.asarray(hdul["MASK_M"].data)
            good = mask == 0
            expected = SKY_ADU * GAIN + RDNOISE ** 2
            self.assertAlmostEqual(float(np.median(var[good])), expected,
                                   delta=0.05 * expected)

    def test_var_and_default_sci_identical(self):
        with fits.open(self.l1_path) as h1, fits.open(self.l1_var_path) as h2:
            self.assertTrue(np.array_equal(h1["SCI_M"].data, h2["SCI_M"].data))
            self.assertTrue(np.array_equal(h1["MASK_M"].data, h2["MASK_M"].data))

    def test_seams_small(self):
        for chip, rec in self.qa["ccds"].items():
            self.assertLess(rec["seam_max_abs_e"], 2.0)

    def test_qa_record(self):
        self.assertEqual(self.qa["masters"]["bias"], "master_bias.fits")
        self.assertEqual(len(self.qa["amps"]), 4)
        self.assertGreater(self.qa["amps"]["M01T"]["n_sat"], 0)
        self.assertTrue(all(a["gain_measured"] for a in self.qa["amps"].values()))


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from kmt_ceu_preproc.geometry import AmpGeom
from kmt_ceu_preproc.steps.overscan import correct_overscan, sliding_median


def make_geom():
    return AmpGeom(
        extname="M01T", chip="M", ampid=1, ctrlid=1,
        datasec=(1, 24, 1, 40), biassec=(25, 30, 1, 40),
        ccdsec=(1, 24, 41, 80), detsec=(1, 24, 41, 80),
        gain=2.0, rdnoise=4.0, saturate=60000, linmax=58000)


class TestOverscan(unittest.TestCase):
    def test_row_level_removed(self):
        geom = make_geom()
        ny, nx = 40, 30
        rng = np.random.default_rng(42)
        level = 500.0 + 0.5 * np.arange(ny)
        raw = np.tile(level[:, None], (1, nx)).astype(np.float32)
        raw[:, :24] += 100.0  # signal in the data region
        raw += rng.normal(0, 2.0, (ny, nx)).astype(np.float32)
        stats, row = correct_overscan(raw, geom, smooth=5)
        self.assertTrue(row.applied)
        # data region should now be ~100 ADU, overscan ~0
        self.assertAlmostEqual(float(np.median(raw[:, :24])), 100.0, delta=2.0)
        self.assertAlmostEqual(float(np.median(raw[:, 24:])), 0.0, delta=2.0)
        self.assertAlmostEqual(stats["ovsc_rms_adu"], 2.0, delta=1.0)
        self.assertEqual(stats["ovsc_cols_used"], 6)

    def test_use_cols_ignores_mirrored(self):
        geom = make_geom()
        raw = np.full((40, 30), 500.0, dtype=np.float32)
        raw[:, 27:] = 9000.0  # corrupted trailing overscan columns
        correct_overscan(raw, geom, use_cols=3, smooth=1)
        self.assertAlmostEqual(float(np.median(raw[:, :24])), 0.0, delta=0.01)

    def test_outlier_rejection(self):
        geom = make_geom()
        raw = np.full((40, 30), 500.0, dtype=np.float32)
        raw[:, 24:] += np.random.default_rng(0).normal(0, 1.0, (40, 6)).astype(np.float32)
        raw[10, 25] = 60000.0  # cosmic ray in overscan
        correct_overscan(raw, geom, smooth=1)
        self.assertLess(abs(float(np.median(raw[10, :24]))), 3.0)

    def test_sliding_median(self):
        a = np.array([1.0, 1.0, 10.0, 1.0, 1.0])
        out = sliding_median(a, 3)
        self.assertEqual(out[2], 1.0)
        self.assertEqual(len(out), 5)


if __name__ == "__main__":
    unittest.main()

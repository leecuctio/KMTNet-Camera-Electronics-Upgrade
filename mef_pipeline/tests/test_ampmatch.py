import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from kmt_ceu_preproc import MASK_BAD
from kmt_ceu_preproc.steps.ampmatch import adjacent_pairs, match_amps
from test_assemble import geoms_2x2


def make_planes(values):
    geoms = geoms_2x2()
    sci = {g.extname: np.full((40, 24), float(v), dtype=np.float32)
           for g, v in zip(geoms, values)}
    mask = {g.extname: np.zeros((40, 24), dtype=np.uint8) for g in geoms}
    return geoms, sci, mask


class TestAmpMatch(unittest.TestCase):
    def test_adjacent_pairs(self):
        geoms = geoms_2x2()
        pairs = adjacent_pairs(geoms)
        axes = sorted(axis for _, _, axis in pairs)
        self.assertEqual(axes, ["x", "x", "y", "y"])
        for a, b, axis in pairs:
            if axis == "x":
                self.assertEqual(a.ccdsec[1] + 1, b.ccdsec[0])
            else:
                self.assertEqual(a.ccdsec[3] + 1, b.ccdsec[2])

    def test_multiplicative_matching(self):
        geoms, sci, mask = make_planes([1000.0, 1050.0, 1000.0, 1000.0])
        res = match_amps(geoms, sci, mask, mode="multiplicative", width=10)
        self.assertTrue(res.applied)
        self.assertEqual(res.mode, "multiplicative")
        meds = [float(np.median(sci[g.extname])) for g in geoms]
        self.assertLess(max(meds) - min(meds), 1.0)
        # CCD-average preserved: correction factors multiply to ~1
        prod = float(np.prod(list(res.corrections.values())))
        self.assertAlmostEqual(prod, 1.0, delta=0.01)
        self.assertLess(res.corrections["M02T"], 1.0)

    def test_auto_picks_additive_for_faint_sky(self):
        geoms, sci, mask = make_planes([5.0, 8.0, 5.0, 5.0])
        res = match_amps(geoms, sci, mask, mode="auto", width=10, sky_min_e=100.0)
        self.assertEqual(res.mode, "additive")
        meds = [float(np.median(sci[g.extname])) for g in geoms]
        self.assertLess(max(meds) - min(meds), 0.5)
        # mean level preserved
        self.assertAlmostEqual(float(np.mean(meds)), 5.75, delta=0.1)

    def test_dead_amp_left_unconstrained(self):
        geoms, sci, mask = make_planes([1000.0, 1050.0, 1000.0, 1000.0])
        dead = geoms[3].extname  # M02B
        mask[dead][:] = MASK_BAD
        before = sci[dead].copy()
        res = match_amps(geoms, sci, mask, mode="multiplicative", width=10)
        self.assertTrue(res.applied)
        self.assertEqual(res.corrections[dead], 1.0)
        self.assertTrue(np.array_equal(sci[dead], before))
        meds = [float(np.median(sci[g.extname])) for g in geoms[:3]]
        self.assertLess(max(meds) - min(meds), 1.0)

    def test_additive_large_offset_with_anchor(self):
        # baseline-jump recovery: one amp off by +600, trusted amps anchor the
        # level so only the bad amp moves (fallback-chip scenario)
        geoms, sci, mask = make_planes([1600.0, 1000.0, 1000.0, 1000.0])
        anchor = {g.extname for g in geoms[1:]}
        res = match_amps(geoms, sci, mask, mode="additive", width=10,
                         max_add=2000.0, anchor=anchor)
        self.assertTrue(res.applied)
        self.assertAlmostEqual(res.corrections["M01T"], -600.0, delta=1.0)
        for ext in anchor:
            self.assertAlmostEqual(res.corrections[ext], 0.0, delta=1.0)
        meds = [float(np.median(sci[g.extname])) for g in geoms]
        self.assertLess(max(meds) - min(meds), 1.0)
        self.assertAlmostEqual(float(np.median(sci["M01T"])), 1000.0, delta=1.0)

    def test_off_when_everything_masked(self):
        geoms, sci, mask = make_planes([1000.0, 1050.0, 1000.0, 1000.0])
        for g in geoms:
            mask[g.extname][:] = MASK_BAD
        res = match_amps(geoms, sci, mask, mode="multiplicative", width=10)
        self.assertFalse(res.applied)


if __name__ == "__main__":
    unittest.main()

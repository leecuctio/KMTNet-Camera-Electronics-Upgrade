"""Tests for the v1.7 photometric-ZP reference chain:
GaiaLocal store schema v2 (ruwe/vmag/imag) and select_zp_refs."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kmt_ceu_preproc.gaialocal import DTYPE, GaiaLocal, _cell_name  # noqa: E402
from kmt_ceu_preproc.steps.photzp import select_zp_refs  # noqa: E402

V1_DTYPE = np.dtype([("ra", "f8"), ("dec", "f8"), ("gmag", "f4"),
                     ("pmra", "f4"), ("pmdec", "f4")])


class TestGaiaLocalV2(unittest.TestCase):
    def test_phot_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            cat = GaiaLocal(Path(td) / "store")
            n = 50
            rng = np.random.default_rng(2)
            ra = 260.0 + rng.uniform(0, 0.5, n)
            dec = -30.0 + rng.uniform(0, 0.5, n)
            g = rng.uniform(12, 18, n)
            cat.ingest_arrays(ra, dec, g, ruwe=np.full(n, 1.1),
                              vmag=g + 0.5, imag=g - 1.0, source="t")
            cone = GaiaLocal(Path(td) / "store").cone(260.25, -29.75, 1.0,
                                                      with_phot=True)
            self.assertEqual(cone.shape, (n, 6))
            order_g = np.sort(cone[:, 2])
            self.assertTrue(np.allclose(np.sort(g), order_g, atol=1e-3))
            self.assertTrue(np.allclose(cone[:, 3] - cone[:, 2], 0.5, atol=1e-3))
            self.assertTrue(np.allclose(cone[:, 4] - cone[:, 2], -1.0, atol=1e-3))
            self.assertTrue(np.allclose(cone[:, 5], 1.1, atol=1e-4))

    def test_v1_store_reads_with_nan_phot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "store"
            root.mkdir(parents=True)
            old = np.zeros(5, dtype=V1_DTYPE)
            old["ra"] = 260.0 + np.arange(5) * 0.01
            old["dec"] = -30.0
            old["gmag"] = 15.0
            np.save(root / _cell_name(-31, 17), old)   # dec -30 -> band -31? no
            # compute the correct cell for (260, -30.0): band floor(-30/1) = -30
            np.save(root / _cell_name(-30, 17), old)
            cone = GaiaLocal(root).cone(260.02, -29.999, 0.5, with_phot=True)
            self.assertGreaterEqual(len(cone), 5)
            sel = np.isfinite(cone[:, 2])
            self.assertTrue(np.isnan(cone[sel, 3]).all())   # vmag NaN
            self.assertTrue(np.isnan(cone[sel, 5]).all())   # ruwe NaN
            # legacy astrometry paths still work
            c3 = GaiaLocal(root).cone(260.02, -29.999, 0.5, with_gmag=True)
            self.assertEqual(c3.shape[1], 3)

    def test_ingest_upgrades_v1_cell(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "store"
            root.mkdir(parents=True)
            old = np.zeros(3, dtype=V1_DTYPE)
            old["ra"] = np.array([10.0, 10.001, 10.002])
            old["dec"] = 20.5
            old["gmag"] = 14.0
            np.save(root / _cell_name(20, 0), old)
            cat = GaiaLocal(root)
            cat.ingest_arrays([10.01], [20.5], [15.0], ruwe=[1.0],
                              vmag=[15.4], imag=[14.1], source="new")
            merged = np.load(root / _cell_name(20, 0))
            self.assertEqual(merged.dtype, DTYPE)
            self.assertEqual(len(merged), 4)


class TestSelectZPRefs(unittest.TestCase):
    def _ref6(self, n=40, ruwe=1.0, v=16.0, i=15.0):
        rng = np.random.default_rng(5)
        ra = 260 + rng.uniform(0, 1, n)
        dec = -30 + rng.uniform(0, 1, n)
        return np.column_stack([ra, dec, np.full(n, 17.0), np.full(n, v),
                                np.full(n, i), np.full(n, ruwe)])

    def test_native_I_with_ruwe_cut(self):
        ref = self._ref6()
        ref[:5, 5] = 3.0                       # 5 bad-RUWE stars
        out, name, note = select_zp_refs(ref, "I", ruwe_max=1.4)
        self.assertEqual(name, "GSPC-Ijkc")
        self.assertEqual(len(out), 35)
        self.assertTrue(np.allclose(out[:, 2], 15.0))
        self.assertIn("ruwe<=1.4", note)

    def test_native_V(self):
        out, name, _ = select_zp_refs(self._ref6(), "V")
        self.assertEqual(name, "GSPC-Vjkc")
        self.assertTrue(np.allclose(out[:, 2], 16.0))

    def test_ruwe_relaxed_when_starving(self):
        ref = self._ref6(n=40, ruwe=2.5)       # crowded field: all RUWE high
        out, name, note = select_zp_refs(ref, "I", ruwe_max=1.4)
        self.assertEqual(name, "GSPC-Ijkc")
        self.assertEqual(len(out), 40)         # cut relaxed, not starved
        self.assertIn("relaxed", note)

    def test_ruwe_unknown_no_cut(self):
        ref = self._ref6()
        ref[:, 5] = np.nan
        out, name, note = select_zp_refs(ref, "I")
        self.assertEqual(len(out), 40)
        self.assertIn("unknown", note)

    def test_fallback_to_G_when_no_native_mags(self):
        ref = self._ref6()
        ref[:, 4] = np.nan                     # no I mags at all
        out, name, note = select_zp_refs(ref, "I")
        self.assertEqual(name, "GaiaG")
        self.assertTrue(np.allclose(out[:, 2], 17.0))
        self.assertIn("GSPC_FALLBACK", note)

    def test_no_native_band_filter(self):
        out, name, note = select_zp_refs(self._ref6(), "R")
        self.assertEqual(name, "GaiaG")
        self.assertIn("NO_NATIVE_BAND", note)

    def test_g_only_and_positions_only(self):
        n = 20
        ref3 = np.column_stack([np.full(n, 260.0), np.full(n, -30.0),
                                np.full(n, 17.0)])
        out, name, note = select_zp_refs(ref3, "I")
        self.assertEqual(name, "GaiaG")
        self.assertIn("REF_HAS_G_ONLY", note)
        out2, name2, note2 = select_zp_refs(ref3[:, :2], "I")
        self.assertEqual(len(out2), 0)
        self.assertEqual(note2, "NO_REF_MAG")


if __name__ == "__main__":
    unittest.main()

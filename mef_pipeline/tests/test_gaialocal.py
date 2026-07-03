import gzip
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from astropy.io import fits

from kmt_ceu_preproc.gaialocal import (GaiaLocal, ingest_fits_refcat,
                                       ingest_gaia_csv)


def synth_sky(n=4000, seed=3):
    """Stars in two patches: one across the RA 0/360 wrap, one at dec -30."""
    rng = np.random.default_rng(seed)
    ra1 = (rng.uniform(-2, 2, n // 2)) % 360.0
    dec1 = rng.uniform(-1.5, 1.5, n // 2)
    ra2 = rng.uniform(150, 154, n - n // 2)
    dec2 = rng.uniform(-31.5, -28.5, n - n // 2)
    ra = np.concatenate([ra1, ra2])
    dec = np.concatenate([dec1, dec2])
    g = rng.uniform(10, 19, n)
    pmra = rng.normal(0, 10, n)
    pmdec = rng.normal(0, 10, n)
    return ra, dec, g, pmra, pmdec


def brute_cone(ra, dec, ra0, dec0, radius):
    d = (ra - ra0 + 180.0) % 360.0 - 180.0
    sep = np.hypot(d * np.cos(np.radians(dec)), dec - dec0)
    return sep <= radius


class TestGaiaLocal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cat = GaiaLocal(Path(self.tmp.name) / "store")
        self.ra, self.dec, self.g, self.pmra, self.pmdec = synth_sky()
        self.cat.ingest_arrays(self.ra, self.dec, self.g, self.pmra, self.pmdec)

    def tearDown(self):
        self.tmp.cleanup()

    def test_cone_matches_brute_force(self):
        for ra0, dec0, r in ((0.5, 0.0, 1.0), (359.6, -0.4, 0.8),
                             (152.0, -30.0, 1.2)):
            got = self.cat.cone(ra0, dec0, r)
            want = int(brute_cone(self.ra, self.dec, ra0, dec0, r).sum())
            self.assertEqual(len(got), want, f"cone({ra0},{dec0},{r})")

    def test_gmax_and_max_refs(self):
        full = self.cat.cone(152.0, -30.0, 1.2)
        cut = self.cat.cone(152.0, -30.0, 1.2, gmax=15.0)
        sel = brute_cone(self.ra, self.dec, 152.0, -30.0, 1.2) & (self.g < 15.0)
        self.assertEqual(len(cut), int(sel.sum()))
        self.assertLess(len(cut), len(full))
        capped = self.cat.cone(152.0, -30.0, 1.2, max_refs=50)
        self.assertEqual(len(capped), 50)

    def test_reingest_dedups(self):
        before = self.cat.stats()["rows"]
        self.cat.ingest_arrays(self.ra, self.dec, self.g, self.pmra, self.pmdec)
        self.assertEqual(self.cat.stats()["rows"], before)

    def test_pm_propagation(self):
        tmp2 = Path(self.tmp.name) / "pm"
        cat = GaiaLocal(tmp2)
        cat.ingest_arrays([100.0], [-30.0], [12.0], [100.0], [-50.0])
        base = cat.cone(100.0, -30.0, 0.5)                # epoch None: catalog epoch
        moved = cat.cone(100.0, -30.0, 0.5, epoch=2026.0)  # +10 yr
        dra = (moved[0, 0] - base[0, 0]) * np.cos(np.radians(-30.0)) * 3.6e6
        ddec = (moved[0, 1] - base[0, 1]) * 3.6e6
        self.assertAlmostEqual(dra, 1000.0, delta=1.0)     # 100 mas/yr * 10 yr
        self.assertAlmostEqual(ddec, -500.0, delta=1.0)

    def test_ingest_fits_refcat(self):
        p = Path(self.tmp.name) / "refcat.fits"
        cols = fits.ColDefs([
            fits.Column("RA", "D", array=[10.0, 10.1]),
            fits.Column("DEC", "D", array=[-5.0, -5.1]),
            fits.Column("GMAG", "E", array=[12.0, 13.0])])
        fits.HDUList([fits.PrimaryHDU(),
                      fits.BinTableHDU.from_columns(cols)]).writeto(p)
        cat = GaiaLocal(Path(self.tmp.name) / "s2")
        n = ingest_fits_refcat(cat, p)
        self.assertEqual(n, 2)
        self.assertEqual(len(cat.cone(10.05, -5.05, 0.5)), 2)

    def test_ingest_gaia_csv(self):
        p = Path(self.tmp.name) / "gaia.csv.gz"
        lines = ["solution_id,ra,dec,pmra,pmdec,phot_g_mean_mag",
                 "1,20.0,-10.0,5.0,-3.0,14.5",
                 "2,20.1,-10.1,,null,17.2",
                 "3,20.2,-10.2,1.0,1.0,19.9"]
        with gzip.open(p, "wt") as f:
            f.write("\n".join(lines) + "\n")
        cat = GaiaLocal(Path(self.tmp.name) / "s3")
        n = ingest_gaia_csv(cat, p, gmax=19.0)
        self.assertEqual(n, 2)  # G=19.9 filtered out
        cone = cat.cone(20.05, -10.05, 0.5)
        self.assertEqual(len(cone), 2)


if __name__ == "__main__":
    unittest.main()

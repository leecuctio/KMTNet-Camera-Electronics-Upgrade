import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from astropy.io import fits

from kmt_ceu_preproc import MASK_SEAM
from kmt_ceu_preproc.geometry import AmpGeom
from kmt_ceu_preproc.steps.assemble import (assemble_ccd, ccd_wcs_cards,
                                            flag_seams, seam_metrics,
                                            seam_positions)


def geoms_2x2():
    common = dict(chip="M", ctrlid=1, gain=2.0, rdnoise=4.0,
                  saturate=60000, linmax=58000,
                  datasec=(1, 24, 1, 40), biassec=(25, 30, 1, 40))
    return [
        AmpGeom(extname="M01T", ampid=1, ccdsec=(1, 24, 41, 80), detsec=(1, 24, 41, 80), **common),
        AmpGeom(extname="M02T", ampid=2, ccdsec=(25, 48, 41, 80), detsec=(25, 48, 41, 80), **common),
        AmpGeom(extname="M01B", ampid=3, ccdsec=(1, 24, 1, 40), detsec=(1, 24, 1, 40), **common),
        AmpGeom(extname="M02B", ampid=4, ccdsec=(25, 48, 1, 40), detsec=(25, 48, 1, 40), **common),
    ]


class TestAssemble(unittest.TestCase):
    def test_placement(self):
        geoms = geoms_2x2()
        planes = {g.extname: np.full((40, 24), float(g.ampid), dtype=np.float32)
                  for g in geoms}
        ccd = assemble_ccd(geoms, planes, np.float32)
        self.assertEqual(ccd.shape, (80, 48))
        self.assertEqual(ccd[79, 0], 1.0)   # M01T upper-left
        self.assertEqual(ccd[79, 47], 2.0)  # M02T upper-right
        self.assertEqual(ccd[0, 0], 3.0)    # M01B lower-left
        self.assertEqual(ccd[0, 47], 4.0)   # M02B lower-right

    def test_seam_positions_and_metric(self):
        geoms = geoms_2x2()
        self.assertEqual(seam_positions(geoms), ([24], [40]))
        planes = {g.extname: np.full((40, 24), 100.0, dtype=np.float32) for g in geoms}
        planes["M02T"] += 5.0
        planes["M02B"] += 5.0
        ccd = assemble_ccd(geoms, planes, np.float32)
        seams = seam_metrics(ccd, geoms)
        self.assertAlmostEqual(seams["x25"], 5.0)
        self.assertAlmostEqual(seams["y41"], 0.0)

    def test_flag_seams(self):
        geoms = geoms_2x2()
        mask = np.zeros((80, 48), dtype=np.uint8)
        flag_seams(mask, geoms)
        self.assertTrue((mask[:, 23:25] & MASK_SEAM).all())
        self.assertTrue((mask[39:41, :] & MASK_SEAM).all())
        self.assertEqual(mask[10, 10], 0)

    def test_wcs_shift(self):
        g = geoms_2x2()[0]  # ccdsec starts at (1,41), datasec at (1,1)
        hdr = fits.Header()
        hdr["CTYPE1"], hdr["CRVAL1"], hdr["CRPIX1"] = "RA---TAN", 150.0, 10.0
        hdr["CRPIX2"] = 20.0
        cards = dict((k, v) for k, v, *_ in ccd_wcs_cards(g, hdr))
        self.assertEqual(cards["CRPIX1"], 10.0)       # x unshifted
        self.assertEqual(cards["CRPIX2"], 20.0 + 40)  # y shifted by ccdsec offset
        self.assertTrue(cards["WCSAPPRX"])


if __name__ == "__main__":
    unittest.main()

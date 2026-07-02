import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from kmt_ceu_preproc.geometry import (ccd_shape, fmtsec, parse_section,
                                      section_shape, section_slices)


class TestSections(unittest.TestCase):
    def test_parse_roundtrip(self):
        self.assertEqual(parse_section("[1:1152,4617:9232]"), (1, 1152, 4617, 9232))
        self.assertEqual(fmtsec(*parse_section("[25:30,1:40]")), "[25:30,1:40]")

    def test_parse_rejects_bad(self):
        for bad in ("", "1:2,3:4", "[1:2;3:4]", "[2:1,1:4]", "[a:b,c:d]"):
            with self.assertRaises(ValueError):
                parse_section(bad)

    def test_slices_match_shape(self):
        sec = parse_section("[25:30,11:40]")
        arr = np.zeros((50, 60))
        sub = arr[section_slices(sec)]
        self.assertEqual(sub.shape, section_shape(sec))
        self.assertEqual(sub.shape, (30, 6))

    def test_slices_one_based_inclusive(self):
        arr = np.arange(20).reshape(4, 5)
        sub = arr[section_slices((2, 3, 1, 2))]  # x 2..3, y 1..2
        self.assertTrue((sub == np.array([[1, 2], [6, 7]])).all())


class TestCcdShape(unittest.TestCase):
    def test_shape_from_ccdsec(self):
        class G:
            def __init__(self, ccdsec):
                self.ccdsec = ccdsec
        geoms = [G((1, 24, 41, 80)), G((25, 48, 1, 40))]
        self.assertEqual(ccd_shape(geoms), (80, 48))


if __name__ == "__main__":
    unittest.main()

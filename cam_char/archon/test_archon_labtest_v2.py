#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_archon_labtest_v2.py -- unittest coverage for the v2 acquisition
script, run end-to-end against the protocol simulator (no hardware).

    python3 -m unittest cam_char/archon/test_archon_labtest_v2.py -v
    (or, from this directory:  python3 -m unittest test_archon_labtest_v2 -v)
"""

import logging
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archon_kmtnet_labtest_v2 as labtest  # noqa: E402
from archon_simulator import ArchonSimulator  # noqa: E402

logging.basicConfig(level=logging.WARNING)


MINI_ACF = """[CONFIG]
TRIGOUTFORCE=1
PARAMETER1="Exposures=0"
PARAMETER2="IntMS=0"
LINECOUNT=64
PIXELCOUNT=128
"""


def write_mini_acf(directory):
    path = os.path.join(directory, 'mini.acf')
    with open(path, 'w', encoding='ascii') as handle:
        handle.write(MINI_ACF)
    return path


class PlanCountsTest(unittest.TestCase):
    """Frame plans must reproduce the v1.0 dataset sizes exactly."""

    def test_dataset_frame_counts(self):
        self.assertEqual(len(labtest.build_plan(labtest.XTALK)), 21)
        self.assertEqual(len(labtest.build_plan(labtest.DARK)), 63)
        self.assertEqual(len(labtest.build_plan(labtest.IFLAT)), 116)
        self.assertEqual(len(labtest.build_plan(labtest.GXT)), 15)

    def test_iflat_structure(self):
        plan = labtest.build_plan(labtest.IFLAT)
        self.assertEqual(plan[0].kind, 'ref')
        kinds = [job.kind for job in plan]
        self.assertEqual(kinds.count('ref'), 29)
        self.assertEqual(kinds.count('dark'), 3)
        self.assertEqual(kinds.count('obj'), 84)

    def test_intms_within_20bit_limit(self):
        for spec in labtest.DATASET_SPECS.values():
            for exptime in spec.exptimes:
                self.assertLessEqual(exptime, labtest.INTMS_MAX)


class FitsWriterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='fits_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_fits_blocking_and_header(self):
        width, height = 100, 37
        pixels = np.arange(width * height, dtype='<u2')
        path = os.path.join(self.tmp, 'test.fits')
        labtest.write_fits(path, pixels, width, height,
                           [('EXPTIME', 1.5, 'seconds'),
                            ('SHUTOPEN', True, ''),
                            ('IMAGETYP', 'FLAT', '')])
        size = os.path.getsize(path)
        self.assertEqual(size % labtest.FITS_BLOCK, 0)

        with open(path, 'rb') as handle:
            header = handle.read(labtest.FITS_BLOCK).decode('ascii')
            data = handle.read()
        cards = {header[i:i + 80][:8].strip(): header[i:i + 80]
                 for i in range(0, len(header), 80)}
        self.assertIn('= %20d' % width, cards['NAXIS1'])
        self.assertIn('= %20d' % height, cards['NAXIS2'])
        self.assertIn('END', cards)

        # BZERO convention: stored value = raw + 0x8000 (mod 2^16), big-endian
        stored = np.frombuffer(data[:width * height * 2], dtype='>u2')
        self.assertEqual(int(stored[0]), 0x8000)
        self.assertEqual(int(stored[5]), 5 + 0x8000)

    def test_pixel_count_mismatch_raises(self):
        with self.assertRaises(ValueError):
            labtest.write_fits(os.path.join(self.tmp, 'bad.fits'),
                               np.zeros(10, dtype='<u2'), 4, 4, [])


class SimulatorEndToEndTest(unittest.TestCase):
    """Full protocol round-trip against the simulator."""

    @classmethod
    def setUpClass(cls):
        cls.sim = ArchonSimulator(time_scale=0.02, readout_time=0.05).start()
        cls.tmp = tempfile.mkdtemp(prefix='labtest_')
        cls.acf = write_mini_acf(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        cls.sim.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def make_lab(self, **kwargs):
        opts = labtest.LabOptions(poll_interval=0.02, readout_timeout=10.0,
                                  power_timeout=5.0, progress=False, **kwargs)
        client = labtest.ArchonClient('127.0.0.1', port=self.sim.port,
                                      command_timeout=5.0)
        client.connect(retries=0)
        return labtest.LabArchon(client, opts=opts)

    def test_error_reply_raises_command_error(self):
        lab = self.make_lab()
        try:
            with self.assertRaises(labtest.ArchonCommandError):
                lab.client.command('BOGUSCOMMAND')
            # the connection must remain usable afterwards
            self.assertIn('POWER', lab.client.get_status())
        finally:
            lab.client.close()

    def test_apply_acf_verify_power_expose(self):
        lab = self.make_lab()
        try:
            lab.apply_acf(self.acf)
            self.assertIn('TRIGOUTFORCE', lab.config_index)

            lab.power_on()
            pixels, meta = lab.expose(500, shutter_open=True)

            self.assertEqual(meta['width'], self.sim.width)
            self.assertEqual(meta['height'], self.sim.height)
            self.assertEqual(pixels.size, self.sim.width * self.sim.height)
            np.testing.assert_array_equal(
                pixels, self.sim.expected_pattern(meta['frame']))
            # trigger timestamps encode the unscaled IntMS
            self.assertAlmostEqual(meta['exp_measured_s'], 0.5, places=3)

            # a second exposure must advance the frame counter
            _, meta2 = lab.expose(0, shutter_open=False)
            self.assertEqual(meta2['frame'], meta['frame'] + 1)

            lab.power_off()
        finally:
            lab.client.close()

    def test_expose_rejects_out_of_range_intms(self):
        lab = self.make_lab()
        try:
            lab.apply_acf(self.acf)
            lab.power_on()
            with self.assertRaises(ValueError):
                lab.expose(labtest.INTMS_MAX + 1, shutter_open=False)
            lab.power_off()
        finally:
            lab.client.close()

    def test_loadparams_fallback_path(self):
        lab = self.make_lab(use_fast_params=False)
        try:
            lab.apply_acf(self.acf)
            lab.power_on()
            pixels, meta = lab.expose(100, shutter_open=False)
            self.assertEqual(pixels.size, self.sim.width * self.sim.height)
            lab.power_off()
        finally:
            lab.client.close()

    def test_run_dataset_writes_fits_files(self):
        # inject a tiny 2-frame spec at unused type digit 9
        labtest.DATASET_SPECS[9] = labtest.DatasetSpec(
            'Mini', True, 1, (0, 100))
        storage = os.path.join(self.tmp, 'data')
        run = labtest.RunConfig(name='t', acf_path=self.acf,
                                dataset_id=7099, storage=storage)
        lab = self.make_lab()
        try:
            written = labtest.run_dataset(
                lab, run, prefix='SIM', unit_id=7,
                notifier=labtest.Notifier(), log=logging.getLogger('test'))
        finally:
            lab.client.close()
            labtest.DATASET_SPECS.pop(9)

        self.assertEqual(len(written), 2)
        for path in written:
            self.assertTrue(os.path.exists(path))
            self.assertEqual(os.path.getsize(path) % labtest.FITS_BLOCK, 0)
        self.assertIn('DS7099', os.path.dirname(written[0]))
        self.assertTrue(os.path.basename(written[0]).startswith('SIM.'))


if __name__ == '__main__':
    unittest.main()

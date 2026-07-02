"""Synthetic miniature L0 amp MEF for unit tests.

One chip 'M', 4 amps (2 strips x TOP/BOT), DATA_LEFT packing:
amp image 30x40 = 24 data cols + 6 overscan cols, 40 rows.
Same HDU layout as real L0 products (PRIMARY + amps + 4 tables)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from astropy.io import fits

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

NX, NY = 30, 40
NDATA, NOVSC = 24, 6
GAIN, RDNOISE = 2.0, 4.0
SATURATE, LINMAX = 60000, 58000

AMP_DEFS = [
    # extname, ampid, datasec, biassec, ccdsec (== detsec here)
    ("M01T", 1, "[1:24,1:40]", "[25:30,1:40]", "[1:24,41:80]"),
    ("M02T", 2, "[1:24,1:40]", "[25:30,1:40]", "[25:48,41:80]"),
    ("M01B", 3, "[1:24,1:40]", "[25:30,1:40]", "[1:24,1:40]"),
    ("M02B", 4, "[1:24,1:40]", "[25:30,1:40]", "[25:48,1:40]"),
]


def default_amp_adu(extname: str) -> np.ndarray:
    """Row ramp everywhere + flat 100 ADU signal in the data region."""
    adu = np.zeros((NY, NX), dtype=np.float64)
    adu += 500.0 + 0.2 * np.arange(NY)[:, None]
    adu[:, :NDATA] += 100.0
    return adu


def make_synth_l0(path, imagetyp="OBJECT", amp_adu=None, exptime=100.0,
                  filt="V", xtalkcal=False, xtalk_coef=None,
                  date_obs="2026-06-30T01:00:00") -> Path:
    """amp_adu: callable extname -> float ADU array (NY, NX)."""
    amp_adu = amp_adu or default_amp_adu
    ph = fits.Header()
    ph["OBSERVAT"] = "CTIO"
    ph["CHIPLIST"] = "M"
    ph["IMAGETYP"] = imagetyp
    ph["OBSTYPE"] = imagetyp
    ph["OBJECT"] = "SYNTH"
    ph["EXPTIME"] = exptime
    ph["FILTER"] = filt
    ph["DATE-OBS"] = date_obs
    ph["MJD-OBS"] = 61221.0
    ph["JD"] = 2461221.5
    ph["XTALKCAL"] = bool(xtalkcal)
    ph["MOCKDATA"] = True
    hdus = [fits.PrimaryHDU(header=ph)]

    for extname, ampid, datasec, biassec, ccdsec in AMP_DEFS:
        adu = np.clip(np.rint(amp_adu(extname)), 0, 65535).astype(np.uint16)
        h = fits.Header()
        h["EXTNAME"] = extname
        h["CHIPID"] = "M"
        h["AMPID"] = ampid
        h["CTRLID"] = 1
        h["DATASEC"] = datasec
        h["BIASSEC"] = biassec
        h["CCDSEC"] = ccdsec
        h["DETSEC"] = ccdsec
        h["GAIN"] = GAIN
        h["RDNOISE"] = RDNOISE
        h["SATURAT"] = SATURATE
        h["LINMAX"] = LINMAX
        h["CTYPE1"], h["CTYPE2"] = "RA---TAN", "DEC--TAN"
        h["CRVAL1"], h["CRVAL2"] = 150.0, -30.0
        h["CRPIX1"], h["CRPIX2"] = 10.0, 20.0
        h["CD1_1"], h["CD1_2"] = -1e-4, 0.0
        h["CD2_1"], h["CD2_2"] = 0.0, 1e-4
        hdus.append(fits.ImageHDU(data=adu, header=h))

    n = len(AMP_DEFS)
    ampinfo = fits.BinTableHDU.from_columns(fits.ColDefs([
        fits.Column("EXTNAME", "8A", array=[a[0] for a in AMP_DEFS]),
        fits.Column("AMPID", "I", array=[a[1] for a in AMP_DEFS]),
        fits.Column("CHIPID", "1A", array=["M"] * n),
        fits.Column("CTRLID", "I", array=[1] * n),
        fits.Column("DATASEC", "24A", array=[a[2] for a in AMP_DEFS]),
        fits.Column("BIASSEC", "24A", array=[a[3] for a in AMP_DEFS]),
        fits.Column("CCDSEC", "24A", array=[a[4] for a in AMP_DEFS]),
        fits.Column("DETSEC", "24A", array=[a[4] for a in AMP_DEFS]),
        fits.Column("GAIN", "E", array=[GAIN] * n),
        fits.Column("RDNOISE", "E", array=[RDNOISE] * n),
        fits.Column("SATLEVEL", "J", array=[SATURATE] * n),
        fits.Column("LINMAX", "J", array=[LINMAX] * n),
    ]), name="AMPINFO")
    src, tgt = np.meshgrid(np.arange(1, n + 1), np.arange(1, n + 1), indexing="ij")
    coef = np.zeros(n * n)
    if xtalk_coef:
        for (s, t), c in xtalk_coef.items():
            coef[(s - 1) * n + (t - 1)] = c
    xtalkinfo = fits.BinTableHDU.from_columns(fits.ColDefs([
        fits.Column("SOURCE_AMP", "I", array=src.ravel()),
        fits.Column("TARGET_AMP", "I", array=tgt.ravel()),
        fits.Column("XTALK_COEF", "D", array=coef),
    ]), name="XTALKINFO")
    voltinfo = fits.BinTableHDU.from_columns(fits.ColDefs([
        fits.Column("VOLTNAME", "16A", array=["VOD"]),
        fits.Column("SETPOINT", "E", array=[0.0]),
    ]), name="VOLTINFO")
    telemetry = fits.BinTableHDU.from_columns(fits.ColDefs([
        fits.Column("CTRLID", "I", array=[1]),
        fits.Column("STATUS", "12A", array=["UNKNOWN"]),
    ]), name="TELEMETRY")
    hdus += [ampinfo, xtalkinfo, voltinfo, telemetry]
    fits.HDUList(hdus).writeto(path, overwrite=True)
    return Path(path)

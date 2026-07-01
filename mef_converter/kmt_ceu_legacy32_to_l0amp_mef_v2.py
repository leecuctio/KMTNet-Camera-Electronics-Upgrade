#!/usr/bin/env python3
"""
KMT-CEU legacy 32-amplifier MEF -> mock 64-amplifier L0 MEF converter (v2.0).

Purpose
-------
The new KMT-CEU electronics (2 x STA Archon controllers) read each science CCD
with 16 amplifiers = 8 vertical strips x 2 readout ends (TOP/BOT), producing the
64-amplifier L0 "amp raw" MEF product defined by

    kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py  (v2.1.1, authoritative converter)
    KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md
    KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx

Until real 64-amp Archon frames exist, pipeline development needs many mock
64-amp MEF images. This tool manufactures them from *real* legacy data: a legacy
32-amplifier MEF from the old KMTNet camera (e.g. kmtc.20260630.011111.fits).

This v2.0 is a clean standalone rewrite of kmt_ceu_legacy32_to_l0amp_mef_v1.py
(v1.1). It has no dependency on the authoritative converter module; all geometry,
header and binary-table generation is self-contained (pure Python + NumPy for
writing; astropy only for reading the legacy MEF).

Legacy 32-amp layout (per amplifier extension)
    NAXIS1 = 1211, NAXIS2 = 9232
    PRESEC  = [1:27,   1:9232]   (27 prescan cols, dropped)
    DATASEC = [28:1179, 1:9232]  (1152 active cols)
    BIASSEC = [1180:1211,1:9232] (32 serial overscan cols)
    -> 8 strips/CCD x 4 CCDs (M,K,N,T) = 32 amplifiers.

Mock 64-amp layout (per amplifier extension)
    NAXIS1 = 1200, NAXIS2 = 4616
    DATASEC = [1:1152,1:4616]    (active pixels - ALL 64 amps, uniform)
    BIASSEC = [1153:1200,1:4616] (local overscan - ALL 64 amps, uniform)
    -> 16 amplifiers/CCD (8 strips x TOP/BOT) x 4 CCDs = 64 amplifiers.

Conversion (physically motivated mockup)
    Each legacy full-height strip (9232 rows) is split into a TOP half (CCD rows
    4617:9232 -> ext <chip><strip>T) and a BOT half (CCD rows 1:4616 -> ext
    <chip><strip>B), emulating the new "read each strip from both ends"
    architecture. Strips are matched to new amplifiers by CCD geometry (CCDSEC),
    NOT by the amp label, because on K and N chips the legacy numbering runs
    opposite to the strip position (legacy K01 = CCD strip 8, K08 = strip 1).
    No image flips are applied anywhere: legacy data is stored in CCD
    orientation and stays that way (CHIPFLP='None').

Uniform DATA_LEFT packing
    The CEU ICD puts the overscan on the readout-node side (left of the data for
    amps 5-8 / 13-16). For this mockup every amp is instead packed DATA_LEFT:
    active pixels at [1:1152], overscan at [1153:1200]. The same star therefore
    has the same in-amp (x, y) position in all 64 amplifier images and the
    pipeline can assume one uniform geometry. The deviation is recorded in
    AMPPACK='DATA_LEFT' and GEOMVER='CEU-L0AMP-v2.1-mockU1'.

    The 48-column overscan is built from the 32 real legacy overscan columns
    plus the trailing 16 columns mirrored (deterministic, real bias-level pixels
    with real read noise, no RNG).

Coordinates carried over from the legacy file
    - Approximate per-amp WCS is inherited from the legacy per-strip WCS by a
      pure CRPIX shift: CRPIX1_new = CRPIX1_legacy - 27 (prescan removed),
      CRPIX2_new = CRPIX2_legacy - 4616 for TOP amps (0 for BOT). CRVAL / CD /
      CTYPE are copied unchanged, so the ds9 sky readout of a star matches the
      legacy display (verified to ~1e-4 arcsec). No EQUINOX/RADESYS is written
      in the extensions, exactly like the legacy extensions, so WCS libraries
      interpret both files in the same default frame. Final astrometry is an L1
      product; this WCS is a placeholder that is *consistent* with the legacy.
    - IRAF physical coordinates: LTV1=0, LTV2=-4616 (TOP) / 0 (BOT), LTM=1, so
      the ds9 "physical" (x, y) of a star is identical in both files:
      x = CCD-strip column 1..1152, y = CCD row 1..9232.
    - DTV/DTM map PHYSICAL pixels to the full KMTNet mosaic per the ds9/IRAF
      convention (detector = DTM x physical + DTV): DTV1 = DETX0-1 and
      DTV2 = CHIP_Y0-1 for both ends, self-consistent with DETSEC. (The legacy
      files' own DTV2 = DETY0 carries a +1 quirk vs their DETSEC; the mock uses
      the self-consistent value, so ds9 "detector" y differs from the legacy
      display by exactly 1 pixel. Physical and sky coordinates match exactly.)

Keyword policy
    - Every keyword that can be filled is filled:
      observation / site / telescope / exposure / focus / dome / thermal values
      from the legacy primary header; structural, geometry, detector and
      electronics keywords exactly as the CEU L0 spec defines them; per-amp
      GAIN / RDNOISE from the legacy strip values (shared by the TOP/BOT
      halves).
    - Keywords that cannot be filled for a legacy conversion are marked "na":
      string keywords get the literal 'na' (MKFILE, NTFILE, RAWGROUP, per-amp
      RAWFILE / RAWDATA / RAWBIAS, absent observation keywords), while
      integer-typed keywords/columns get -1 so downstream int() parsing of
      spec-typed keywords keeps working (NUMFILES, RAWNAX1, RAWNAX2, MIDOVSCY,
      AMPINFO RAWX0..RAWY1). Legacy valueless cards (TSHSHUT, DSUP, ...) are
      detected and treated as absent -> 'na'.
    - Mockup provenance is recorded: MOCKDATA, ORIGFILE, ORIGFMT, ORIGNAMP,
      ORIGCAM, ORIGRDO, CONVPROG, CONVDATE, CONVNOTE, AMPPACK, GEOMVER.

Output HDU layout (identical to the real 64-amp L0 product; 69 HDUs)
    PRIMARY
    M01T..M08T, M01B..M08B
    K01T..K08T, K01B..K08B
    N01T..N08T, N01B..N08B
    T01T..T08T, T01B..T08B
    AMPINFO, XTALKINFO, VOLTINFO, TELEMETRY

Usage
    python3 kmt_ceu_legacy32_to_l0amp_mef_v2.py legacy1.fits [legacy2.fits ...]
        [-d OUTDIR] [-o OUTPUT (single input only)] [-f]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import struct
from pathlib import Path

import numpy as np
from astropy.io import fits

# --------------------------------------------------------------------------- #
# Versions and sentinels
# --------------------------------------------------------------------------- #
BLOCK = 2880
SOFTWARE_VERSION = "v2.0"
CONVPROG = f"kmt_ceu_legacy32_to_l0amp_mef_{SOFTWARE_VERSION}"
PRODUCT_VERSION = "v2.1.1"                    # CEU L0 MEF format compatibility
GEOMETRY_VERSION = "CEU-L0AMP-v2.1-mockU1"    # mock uniform DATA_LEFT packing

NA = "na"                 # string sentinel for un-fillable keywords
NA_INT = -1               # numeric sentinel for un-fillable integer columns

# --------------------------------------------------------------------------- #
# CEU 64-amp geometry (per KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0)
# --------------------------------------------------------------------------- #
CCD_COLS = 9216
CCD_ROWS = 9232
GAP_COLS = 460
GAP_ROWS = 933
AMP_COLS = 1200            # NAXIS1 per amp image (data + local overscan)
AMP_DATA_COLS = 1152       # active columns per amp
OVERSCAN_X = 48            # local overscan columns per amp
PRESCAN_X = 0
HALF_ROWS = 4616           # NAXIS2 per amp image (TOP or BOT half)
PIX_SIZE = 10.0
PIX_SCALE = 0.400
DETSIZE = "[1:18892,1:19397]"

CHIP_ORDER = ["M", "K", "N", "T"]
AMP_BASE = {"M": 0, "K": 16, "N": 32, "T": 48}
CHIP_X0 = {"M": 1, "K": CCD_COLS + GAP_COLS + 1, "N": 1, "T": CCD_COLS + GAP_COLS + 1}
CHIP_Y0 = {"M": CCD_ROWS + GAP_ROWS + 1, "K": CCD_ROWS + GAP_ROWS + 1, "N": 1, "T": 1}

CHIPFLP = "None"           # no chip-dependent OSU-style flip at L0 packing
STRIPDIR = "+X"
AMPPACK = "DATA_LEFT"      # mock uniform packing: data [1:1152], overscan [1153:1200]

DATASEC_UNIFORM = f"[1:{AMP_DATA_COLS},1:{HALF_ROWS}]"
BIASSEC_UNIFORM = f"[{AMP_DATA_COLS + 1}:{AMP_COLS},1:{HALF_ROWS}]"
PRESEC_STR = f"[1:0,1:{HALF_ROWS}]"

# Per-strip WCS keywords inherited from the legacy extension headers.
WCS_KEYS = ("CTYPE1", "CTYPE2", "CRVAL1", "CRVAL2", "CRPIX1", "CRPIX2",
            "CD1_1", "CD1_2", "CD2_1", "CD2_2")


# --------------------------------------------------------------------------- #
# Minimal standalone FITS writer (same conventions as the CEU v2.1.1 converter)
# --------------------------------------------------------------------------- #
def pad_header(b: bytes) -> bytes:
    return b + b" " * ((-len(b)) % BLOCK)


def pad_data(b: bytes) -> bytes:
    return b + b"\0" * ((-len(b)) % BLOCK)


def fits_value(v):
    if isinstance(v, bool):
        return f"{'T' if v else 'F':>20}"
    if isinstance(v, int) and not isinstance(v, bool):
        return f"{v:20d}"
    if isinstance(v, float):
        # Shortest round-trip representation (full double precision). The old
        # %.10G formatting truncated JD by ~30 s and CRVAL by ~1e-4 arcsec.
        s = repr(v).upper()
        if len(s) <= 20:
            return f"{s:>20}"
        return f"{v:20.16G}"
    if v is None:
        return "''"
    s = str(v).replace("'", "''")
    return f"'{s}'"


def card(key: str, value=None, comment: str | None = None) -> bytes:
    if key in ("COMMENT", "HISTORY"):
        line = f"{key:<8} {'' if value is None else str(value)}"
        return line[:80].ljust(80).encode("ascii", errors="replace")
    k = key[:8].ljust(8)
    if value is None:
        line = k
    else:
        line = f"{k}= {fits_value(value)}"
        if comment:
            line += f" / {comment}"
    return line[:80].ljust(80).encode("ascii", errors="replace")


def header_bytes(cards: list[bytes]) -> bytes:
    return pad_header(b"".join(cards + [card("END")]))


def bintable_bytes(extname: str, columns, rows, extra_cards=None) -> bytes:
    def sz(fmt):
        if fmt.endswith("A"):
            n = fmt[:-1]
            return int(n) if n else 1
        return {"I": 2, "J": 4, "E": 4, "D": 8}[fmt]

    rowlen = sum(sz(fmt) for _, fmt, _ in columns)
    cards = [
        card("XTENSION", "BINTABLE", "Binary table extension"),
        card("BITPIX", 8, "8-bit bytes"),
        card("NAXIS", 2, "2-D binary table"),
        card("NAXIS1", rowlen, "bytes per row"),
        card("NAXIS2", len(rows), "number of rows"),
        card("PCOUNT", 0),
        card("GCOUNT", 1),
        card("TFIELDS", len(columns), "number of columns"),
        card("EXTNAME", extname),
    ]
    if extra_cards:
        cards.extend(extra_cards)
    for i, (name, fmt, unit) in enumerate(columns, 1):
        cards.append(card(f"TTYPE{i}", name))
        cards.append(card(f"TFORM{i}", fmt))
        if unit:
            cards.append(card(f"TUNIT{i}", unit))
    data = bytearray()
    for row in rows:
        for name, fmt, _unit in columns:
            val = row.get(name)
            if fmt.endswith("A"):
                n = int(fmt[:-1]) if fmt[:-1] else 1
                s = "" if val is None else str(val)
                data.extend(s.encode("ascii", errors="replace")[:n].ljust(n, b" "))
            elif fmt == "I":
                data.extend(struct.pack(">h", int(val)))
            elif fmt == "J":
                data.extend(struct.pack(">i", int(val)))
            elif fmt == "E":
                data.extend(struct.pack(">f", float(val)))
            elif fmt == "D":
                data.extend(struct.pack(">d", float(val)))
            else:
                raise ValueError(fmt)
    return header_bytes(cards) + pad_data(bytes(data))


# --------------------------------------------------------------------------- #
# 64-amp geometry helpers
# --------------------------------------------------------------------------- #
def strip_id(amp: int) -> int:
    """Vertical strip 1..8 for amp sequence 1..16 (1-8 TOP, 9-16 BOT)."""
    return ((amp - 1) % 8) + 1


def end_id(amp: int) -> str:
    return "TOP" if amp <= 8 else "BOT"


def extname_for(chip: str, amp: int) -> str:
    return f"{chip}{strip_id(amp):02d}{'T' if amp <= 8 else 'B'}"


def ccdsec(amp: int):
    """Active amp section in CCD coordinates (x1, x2, y1, y2), 1-based."""
    x1 = (strip_id(amp) - 1) * AMP_DATA_COLS + 1
    x2 = strip_id(amp) * AMP_DATA_COLS
    if amp <= 8:
        y1, y2 = HALF_ROWS + 1, CCD_ROWS
    else:
        y1, y2 = 1, HALF_ROWS
    return x1, x2, y1, y2


def detsec(chip: str, amp: int):
    """Active amp section in full KMTNet mosaic coordinates."""
    x1, x2, y1, y2 = ccdsec(amp)
    return (CHIP_X0[chip] + x1 - 1, CHIP_X0[chip] + x2 - 1,
            CHIP_Y0[chip] + y1 - 1, CHIP_Y0[chip] + y2 - 1)


def fmtsec(x1, x2, y1, y2) -> str:
    return f"[{x1}:{x2},{y1}:{y2}]"


def jd_from_datetime(d: dt.datetime) -> float:
    year, month = d.year, d.month
    day = d.day + (d.hour + (d.minute + (d.second + d.microsecond / 1e6) / 60.0) / 60.0) / 24.0
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5


# --------------------------------------------------------------------------- #
# Legacy header value access with the "na" policy
# --------------------------------------------------------------------------- #
def sv(hdr: dict, key: str, default=NA):
    """String value from the legacy header; missing/blank -> default (na)."""
    v = hdr.get(key.upper())
    s = "" if v is None else str(v).strip()
    return s if s != "" else default


def nv(hdr: dict, key: str, default):
    """Numeric value from the legacy header; unparsable -> default."""
    v = hdr.get(key.upper(), default)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    try:
        s = str(v).strip()
        return int(s) if isinstance(default, int) else float(s)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# Legacy MEF ingestion
# --------------------------------------------------------------------------- #
def clean_primary_dict(ph) -> dict:
    """Uppercase {keyword: value} dict of a legacy primary header.

    Legacy headers contain non-standard valueless cards (e.g. 'TSHSHUT   / ...',
    'DSUP   / ...'); astropy surfaces their comment tail as the value string.
    Those are dropped here so the converter's "na" policy applies to them.
    """
    out = {}
    for k in ph.keys():
        if not k or k in ("COMMENT", "HISTORY"):
            continue
        v = ph[k]
        if isinstance(v, fits.card.Undefined):
            continue
        if isinstance(v, str) and v.strip().startswith("/"):
            continue                    # valueless card: comment leaked into value
        out[k.upper()] = v
    return out


_SEC_RE = re.compile(r"\[(\d+):(\d+),(\d+):(\d+)\]")


def parse_sec(text: str):
    m = _SEC_RE.match(str(text).replace(" ", ""))
    if not m:
        raise ValueError(f"cannot parse section {text!r}")
    return tuple(int(x) for x in m.groups())


def strip_from_ccdsec(ccdsec_text: str) -> int:
    """CCD strip number 1..8 from a legacy CCDSEC (label-independent)."""
    x0, _x1, _y0, _y1 = parse_sec(ccdsec_text)
    return (x0 - 1) // AMP_DATA_COLS + 1


def read_legacy(path: Path):
    """Read a legacy 32-amp MEF.

    Returns
        primary_hdr : uppercase {keyword: value} dict of the primary header
        strips      : {chip: {strip 1..8: {'active','overscan','gain','rdnoise',
                                           'xoff','wcs','legacy_ext'}}}
    """
    strips: dict[str, dict[int, dict]] = {c: {} for c in CHIP_ORDER}
    with fits.open(path, do_not_scale_image_data=True, memmap=True) as hdul:
        primary_hdr = clean_primary_dict(hdul[0].header)

        for hdu in hdul[1:]:
            ext = str(hdu.header.get("EXTNAME", "")).strip()
            if len(ext) < 3 or ext[0] not in strips:
                continue
            chip = ext[0]
            hdr = hdu.header
            strip = strip_from_ccdsec(hdr["CCDSEC"])
            if strip in strips[chip]:
                raise ValueError(
                    f"{ext}: duplicate CCD strip {strip} for chip {chip} "
                    f"(CCDSEC collision with {strips[chip][strip]['legacy_ext']})")
            dx0, dx1, _dy0, _dy1 = parse_sec(hdr["DATASEC"])
            bx0, bx1, _by0, _by1 = parse_sec(hdr["BIASSEC"])
            data = np.asarray(hdu.data, dtype=">i2")   # raw int16 stored values
            if data.shape != (CCD_ROWS, hdr["NAXIS1"]):
                raise ValueError(f"{ext}: unexpected shape {data.shape}")
            active = data[:, dx0 - 1:dx1]              # (9232, 1152)
            overscan = data[:, bx0 - 1:bx1]            # (9232, 32)
            if active.shape[1] != AMP_DATA_COLS:
                raise ValueError(f"{ext}: DATASEC width {active.shape[1]} != {AMP_DATA_COLS}")

            def _fval(k, default=0.0):
                try:
                    return float(hdr.get(k, default))
                except (TypeError, ValueError):
                    return default

            strips[chip][strip] = {
                "active": np.ascontiguousarray(active),
                "overscan": np.ascontiguousarray(overscan),
                "gain": _fval("GAIN"),
                "rdnoise": _fval("RDNOISE"),
                "xoff": dx0 - 1,        # legacy prescan columns before the data (27)
                "wcs": {k: hdr[k] for k in WCS_KEYS if k in hdr},
                "legacy_ext": ext,
            }

    for chip in CHIP_ORDER:
        missing = [s for s in range(1, 9) if s not in strips[chip]]
        if missing:
            raise ValueError(f"CCD {chip}: missing legacy strips {missing}")
    return primary_hdr, strips


# --------------------------------------------------------------------------- #
# Mock amp pixel assembly (uniform DATA_LEFT packing)
# --------------------------------------------------------------------------- #
def build_overscan48(overscan_half: np.ndarray) -> np.ndarray:
    """48-column overscan from the 32 real legacy columns + trailing 16 mirrored."""
    n_have = overscan_half.shape[1]                 # 32
    if n_have >= OVERSCAN_X:
        return np.ascontiguousarray(overscan_half[:, :OVERSCAN_X])
    pad = OVERSCAN_X - n_have                       # 16
    mirror = overscan_half[:, n_have - pad:n_have][:, ::-1]
    return np.ascontiguousarray(np.concatenate([overscan_half, mirror], axis=1))


def build_amp_image(strip_info: dict, amp: int) -> np.ndarray:
    """One mock 64-amp image (4616 x 1200): data [1:1152], overscan [1153:1200]."""
    if amp <= 8:                                    # TOP end -> CCD rows 4617:9232
        rows = slice(HALF_ROWS, CCD_ROWS)
    else:                                           # BOT end -> CCD rows 1:4616
        rows = slice(0, HALF_ROWS)
    active_half = strip_info["active"][rows, :]     # (4616, 1152)
    os48 = build_overscan48(strip_info["overscan"][rows, :])  # (4616, 48)

    img = np.empty((HALF_ROWS, AMP_COLS), dtype=">i2")
    img[:, :AMP_DATA_COLS] = active_half
    img[:, AMP_DATA_COLS:] = os48
    return img


# --------------------------------------------------------------------------- #
# PRIMARY header
# --------------------------------------------------------------------------- #
def primary_cards(ph: dict, legacy_path: Path, out_path: Path):
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "")
    date_obs = sv(ph, "DATE-OBS", now)
    try:
        if "T" in date_obs:
            jd_obs = jd_from_datetime(dt.datetime.fromisoformat(date_obs.replace("Z", "+00:00")))
        else:
            jd_obs = jd_from_datetime(dt.datetime.now(dt.timezone.utc))
    except Exception:
        jd_obs = jd_from_datetime(dt.datetime.now(dt.timezone.utc))
    mjd_obs = jd_obs - 2400000.5

    tshopen = sv(ph, "TSHOPEN", "")
    ut = f"{date_obs[:10]}T{tshopen}" if tshopen and tshopen != NA else date_obs

    return [
        card("SIMPLE", True, "FITS standard"),
        card("BITPIX", 16, "bits per pixel in image extensions"),
        card("NAXIS", 0, "primary HDU has no image array"),
        card("EXTEND", True, "file contains extensions"),
        card("ORIGIN", sv(ph, "ORIGIN", "KASI"), "FITS file originator"),
        card("DATE", now, "date FITS file was generated"),
        card("CREATOR", CONVPROG, "MEF creation program"),

        card("COMMENT", "Mockup provenance: built from a legacy 32-amplifier MEF"),
        card("MOCKDATA", True, "pixels are real legacy data, geometry is mock 64-amp"),
        card("ORIGFILE", legacy_path.name, "source legacy MEF file"),
        card("ORIGFMT", "32AMP_MEF", "source product format"),
        card("ORIGNAMP", 32, "amplifiers in source product"),
        card("ORIGCAM", "KMTNet legacy camera", "source camera/electronics"),
        card("ORIGRDO", sv(ph, "READOUT"), "legacy READOUT amplifier set"),
        card("CONVPROG", CONVPROG, "legacy->64amp mockup converter"),
        card("CONVDATE", now, "UTC time of mockup conversion"),
        card("CONVNOTE", "strip split TOP/BOT; uniform data[1:1152]+os[1153:1200]"),
        card("AMPPACK", AMPPACK, "mock packing: data [1:1152], overscan [1153:1200]"),
        card("GEOMVER", GEOMETRY_VERSION, "geometry version (mock uniform packing)"),

        card("COMMENT", "KMT-CEU L0 Raw 64-amplifier MEF product"),
        card("COMMENT", "Primary raw archive/product for amplifier-level calibration"),
        card("BUNIT", sv(ph, "BUNIT", "ADU"), "units of image pixel values"),
        card("DATAPROD", "L0_AMP", "data product type"),
        card("PRODVER", PRODUCT_VERSION, "product format version"),

        card("COMMENT", "Raw Archon file provenance (no Archon raw for a mock:"),
        card("COMMENT", "string keywords = 'na', integer keywords = -1)"),
        card("RAWGROUP", NA, "raw Archon file grouping convention"),
        card("CHIPLIST", "M,K,N,T", "official science chip order"),
        card("MKFILE", NA, "source MK raw FITS file"),
        card("NTFILE", NA, "source NT raw FITS file"),
        card("NUMFILES", NA_INT, "number of raw files used (-1 = na)"),
        card("RAWNAX1", NA_INT, "raw Archon image width (-1 = na)"),
        card("RAWNAX2", NA_INT, "raw Archon image height (-1 = na)"),
        card("RAWXTILE", AMP_COLS, "amp tile width"),
        card("AMPDATA", AMP_DATA_COLS, "active columns per amp tile"),
        card("OVERSCNX", OVERSCAN_X, "X overscan columns per amp tile"),
        card("PRESCANX", PRESCAN_X, "X prescan columns per amp tile"),
        card("MIDOVSCY", NA_INT, "middle Y overscan rows (-1 = na)"),
        card("TOPROWS", HALF_ROWS, "active TOP-half rows"),
        card("BOTROWS", HALF_ROWS, "active BOT-half rows"),
        card("CHIPFLP", CHIPFLP, "no chip-dependent OSU-style flip applied"),

        card("COMMENT", "Detector and camera information"),
        card("DETECTOR", sv(ph, "DETECTOR", "e2v CCD290-99"), "detector model"),
        card("CAMNAME", "KMT-CEU", "camera electronics upgrade system"),
        card("CAMVER", "CEU-v2.1", "camera/electronics version"),
        card("DETTYPE", "SCIENCE", "science detector data product"),
        card("NCCD", 4, "number of science CCDs"),
        card("NAMPS", 64, "total amplifiers"),
        card("AMPPCD", 16, "amplifiers per CCD"),
        card("NSTRIP", 8, "vertical strips per CCD"),
        card("NEND", 2, "top and bottom readout ends per strip"),
        card("CCDXBIN", nv(ph, "CCDXBIN", 1), "CCD X-axis binning factor"),
        card("CCDYBIN", nv(ph, "CCDYBIN", 1), "CCD Y-axis binning factor"),
        card("READMODE", "64AMP", "64-amplifier readout mode"),
        card("READARCH", "8STRIPx2END", "8 strips read from top and bottom"),
        card("PIXSCALE", PIX_SCALE, "unbinned pixel scale [arcsec/pixel]"),
        card("PIXSIZE", PIX_SIZE, "unbinned pixel size [micron]"),
        card("DETSIZE", DETSIZE, "KMTNet mosaic size in pixels"),
        card("COLGAP", GAP_COLS, "horizontal inter-CCD gap in pixels"),
        card("ROWGAP", GAP_ROWS, "vertical inter-CCD gap in pixels"),

        card("COMMENT", "Observatory and exposure information"),
        card("OBSERVAT", sv(ph, "OBSERVAT"), "observatory site"),
        card("SITEID", sv(ph, "OBSERVAT"), "site identifier"),
        card("TELESCOP", sv(ph, "TELESCOP", "KMTNet 1.6m"), "telescope name"),
        card("LATITUDE", sv(ph, "LATITUDE"), "site latitude"),
        card("LONGITUD", sv(ph, "LONGITUD"), "site longitude"),
        card("ELEVATIO", nv(ph, "ELEVATIO", 0), "site elevation [m]"),
        card("OBSERVER", sv(ph, "OBSERVER"), "observer(s)"),
        card("OBJECT", sv(ph, "OBJECT"), "name of object observed"),
        card("FIELDID", sv(ph, "FIELDID", sv(ph, "OBJECT")), "KMTNet field identifier"),
        card("PROJID", sv(ph, "PROJID"), "project or observing program ID"),
        card("IMAGETYP", sv(ph, "IMAGETYP"), "type of observation"),
        card("OBSTYPE", sv(ph, "OBSTYPE"), "type of observation"),
        card("EXPTIME", nv(ph, "EXPTIME", 0.0), "exposure time [s]"),
        card("DARKTIME", nv(ph, "DARKTIME", 0.0), "cumulative dark time [s]"),
        card("TSHOPEN", sv(ph, "TSHOPEN"), "shutter open time"),
        card("TSHSHUT", sv(ph, "TSHSHUT"), "shutter close time"),
        card("FILENAME", out_path.name, "MEF filename"),
        card("UNIQNAME", sv(ph, "UNIQNAME"), "unique filename"),

        card("COMMENT", "Instrument/electronics configuration"),
        card("INSTRUME", sv(ph, "INSTRUME", "KMTS"), "instrument name"),
        card("CONTROLL", "STA ARCHON", "controller type"),
        card("NCTRL", 2, "number of science Archon controllers"),
        card("CTRL1ID", sv(ph, "CTRL1ID", "UNKNOWN"), "science controller 1 ID"),
        card("CTRL1SN", sv(ph, "CTRL1SN", "UNKNOWN"), "science controller 1 serial number"),
        card("CTRL1FW", sv(ph, "CTRL1FW", "UNKNOWN"), "science controller 1 firmware"),
        card("CTRL2ID", sv(ph, "CTRL2ID", "UNKNOWN"), "science controller 2 ID"),
        card("CTRL2SN", sv(ph, "CTRL2SN", "UNKNOWN"), "science controller 2 serial number"),
        card("CTRL2FW", sv(ph, "CTRL2FW", "UNKNOWN"), "science controller 2 firmware"),
        card("WBTYPE", "STA Differential Board", "wall board type"),
        card("ELECSYS", "KMT-CEU", "electronics system"),
        card("SIGELEC", "STA_DIFF_VIDEO", "signal readout/video-chain electronics"),
        card("TIMCONF", "CEU_TIM_v1.0", "CCD clock and timing configuration"),
        card("CTRLVER", sv(ph, "CTRLVER", "ARCHON-v1.0"), "controller system version"),
        card("TIMVER", sv(ph, "TIMVER", "TIM-v1.0"), "timing script version"),
        card("XTALKVER", sv(ph, "XTALKVER", "UNMEASURED"), "crosstalk model version"),
        card("XTALKCAL", False, "crosstalk coefficients are placeholders"),
        card("BIASVER", sv(ph, "BIASVER", "BIAS-v1.0"), "bias configuration version"),
        card("CLKVER", sv(ph, "CLKVER", "CLK-v1.0"), "clock configuration version"),
        card("PIPEVER", CONVPROG, "converter version"),
        card("REFVER", sv(ph, "REFVER", "N/A"), "reference image version"),
        card("CATVER", sv(ph, "CATVER", "N/A"), "catalog version"),

        card("COMMENT", "TCS pointing information"),
        card("TCSLINK", sv(ph, "TCSLINK"), "TCS communications link status"),
        card("TCSARC", sv(ph, "TCSARC"), "TCS auto recovery mode status"),
        card("TCSQDATE", sv(ph, "TCSQDATE"), "UTC date/time of last TCS query"),
        card("TCSUDATE", sv(ph, "TCSUDATE"), "UTC date/time of last TCS update"),
        card("TIMESYS", sv(ph, "TIMESYS", "UTC"), "time system"),
        card("DATE-OBS", date_obs, "UTC date/time at start of observation"),
        card("MJD-OBS", mjd_obs, "modified Julian date at start"),
        card("JD", jd_obs, "Julian date at start"),
        card("UT", ut, "UTC timestamp"),
        card("RADECSYS", sv(ph, "RADECSYS", "ICRS"), "telescope coordinate system"),
        card("RA", sv(ph, "RA", "00:00:00.00"), "telescope RA"),
        card("DEC", sv(ph, "DEC", "+00:00:00.0"), "telescope DEC"),
        card("EQUINOX", nv(ph, "EQUINOX", 2000.0), "coordinate system equinox"),
        card("HA", sv(ph, "HA"), "hour angle at start"),
        card("ST", sv(ph, "ST"), "local sidereal time at start"),
        card("SECZ", sv(ph, "SECZ"), "secant of zenith distance"),
        card("ALT", sv(ph, "ALT"), "telescope altitude [deg]"),
        card("AZ", sv(ph, "AZ"), "telescope azimuth [deg]"),
        card("TCSDRIV", sv(ph, "TCSDRIVE", sv(ph, "TCSDRIV")), "telescope drive status"),
        card("TELMOVE", sv(ph, "TELMOVE"), "telescope motion status"),

        card("COMMENT", "Filter/shutter, FSA, focus, dome, and thermal info"),
        card("AUXLINK", sv(ph, "AUXLINK"), "AUX control system communication status"),
        card("AUXARC", sv(ph, "AUXARC"), "AUX link auto recovery status"),
        card("AUXQDATE", sv(ph, "AUXQDATE"), "UTC date/time of last AUX query"),
        card("AUXUDATE", sv(ph, "AUXUDATE"), "UTC date/time of last AUX update"),
        card("FSSTAT", sv(ph, "FSSTAT"), "filter-shutter subsystem status"),
        card("FILTOP", sv(ph, "FILTOP"), "filter operational status"),
        card("FILNUM", sv(ph, "FILNUM"), "filter selector position number"),
        card("FILTER", sv(ph, "FILTER"), "filter name in beam"),
        card("SHUTOP", sv(ph, "SHUTOP"), "shutter operational status"),
        card("SHUTTER", sv(ph, "SHUTTER"), "shutter position"),
        card("FSATEMP", sv(ph, "FSATEMP"), "FSA internal temperature [C]"),
        card("FSAHUM", sv(ph, "FSAHUM"), "FSA internal relative humidity [%]"),
        card("FSADEW", sv(ph, "FSADEW"), "FSA internal dew point [C]"),
        card("FSAALRM", sv(ph, "FSAALRM"), "FSA environmental alarm status"),
        card("FASTAT", sv(ph, "FASTAT"), "focus actuator subsystem status"),
        card("FAFOCUS", sv(ph, "FAFOCUS"), "focus position offset [mm]"),
        card("FATILTNS", sv(ph, "FATILTNS"), "focus tilt NS offset [arcsec]"),
        card("FATILTEW", sv(ph, "FATILTEW"), "focus tilt EW offset [arcsec]"),
        card("FAPOSS", sv(ph, "FAPOSS"), "south focus actuator position [mm]"),
        card("FALIMS", sv(ph, "FALIMS"), "south focus actuator limit status"),
        card("FAPOSE", sv(ph, "FAPOSE"), "east focus actuator position [mm]"),
        card("FALIME", sv(ph, "FALIME"), "east focus actuator limit status"),
        card("FAPOSW", sv(ph, "FAPOSW"), "west focus actuator position [mm]"),
        card("FALIMW", sv(ph, "FALIMW"), "west focus actuator limit status"),
        card("DSSTAT", sv(ph, "DSSTAT"), "dome shutter status"),
        card("DSUP", sv(ph, "DSUP"), "upper dome shutter position"),
        card("DSLW", sv(ph, "DSLW"), "lower dome shutter position"),
        card("DSSAF", sv(ph, "DSSAF"), "dome safety status"),
        card("DSAUTO", sv(ph, "DSAUTO"), "dome auto sync status"),
        card("DSALT", sv(ph, "DSALT"), "dome slit altitude [deg]"),
        card("DSAZ", sv(ph, "DSAZ"), "dome slit azimuth [deg]"),
        card("DSTELALT", sv(ph, "DSTELALT", sv(ph, "DSTEL")), "telescope altitude used by dome [deg]"),
        card("DSTELAZ", sv(ph, "DSTELAZ"), "telescope azimuth used by dome [deg]"),
        card("DALTERR", sv(ph, "DALTERR"), "dome-telescope altitude difference [deg]"),
        card("DAZERR", sv(ph, "DAZERR"), "dome-telescope azimuth difference [deg]"),
        card("MCSTAT", sv(ph, "MCSTAT"), "mirror cover status"),
        card("MCPOS", sv(ph, "MCPOS"), "mirror cover position [%]"),
        card("CHSTAT", sv(ph, "CHSTAT"), "chiller status"),
        card("ENSTAT", sv(ph, "ENSTAT"), "environmental control system status"),
        card("ENFAN", sv(ph, "ENFAN"), "environmental system fan state"),
        card("CCDTEMP", sv(ph, "CCDTEMP"), "CCD temperature [C]"),
        card("DEWPRES", sv(ph, "DEWPRES"), "dewar pressure"),
        card("PT30N1", sv(ph, "PT30N1"), "cooler temperature sensor 1 [C]"),
        card("PT30N2", sv(ph, "PT30N2"), "cooler temperature sensor 2 [C]"),
        card("CHARCOAL", sv(ph, "CHARCOAL"), "charcoal getter temperature [C]"),
        card("AIR_IN", sv(ph, "AIR_IN"), "air inlet temperature [C]"),
        card("AIR_OUT", sv(ph, "AIR_OUT"), "air outlet temperature [C]"),
        card("GLYC_IN", sv(ph, "GLYC_IN"), "glycol inlet temperature [C]"),
        card("GLYC_OUT", sv(ph, "GLYC_OUT"), "glycol outlet temperature [C]"),
        card("CHKIMG", sv(ph, "CHKIMG"), "image check status"),
        card("CHKIMG_C", sv(ph, "CHKIMG_C"), "image check comment"),
    ]


# --------------------------------------------------------------------------- #
# Amplifier image extension header
# --------------------------------------------------------------------------- #
def amp_cards(chip: str, amp: int, ph: dict, strip_info: dict):
    ext = extname_for(chip, amp)
    cx1, cx2, cy1, cy2 = ccdsec(amp)
    dx1, dx2, dy1, dy2 = detsec(chip, amp)
    global_amp = AMP_BASE[chip] + amp
    read_dir = "-Y" if amp <= 8 else "+Y"

    # TOP amps hold legacy CCD rows 4617..9232 as image rows 1..4616.
    y_shift = HALF_ROWS if amp <= 8 else 0
    x_shift = strip_info.get("xoff", 27)            # legacy prescan columns

    date_obs = sv(ph, "DATE-OBS", "")
    tshopen = sv(ph, "TSHOPEN", "")
    ut = f"{date_obs[:10]}T{tshopen}" if tshopen and tshopen != NA and date_obs else \
        (date_obs if date_obs else NA)

    # Approximate WCS inherited from the legacy per-strip WCS by a CRPIX shift:
    #   x_legacy = x_mock + prescan(27),  y_legacy = y_mock + 4616 (TOP) / 0 (BOT)
    w = strip_info.get("wcs", {})
    if all(k in w for k in WCS_KEYS):
        wcs_cards = [
            card("CTYPE1", str(w["CTYPE1"]), "coordinate type"),
            card("CTYPE2", str(w["CTYPE2"]), "coordinate type"),
            card("CRVAL1", float(w["CRVAL1"]), "reference RA [deg] (from legacy WCS)"),
            card("CRVAL2", float(w["CRVAL2"]), "reference DEC [deg] (from legacy WCS)"),
            card("CRPIX1", float(w["CRPIX1"]) - x_shift, "ref pixel (legacy CRPIX1 - prescan)"),
            card("CRPIX2", float(w["CRPIX2"]) - y_shift, "ref pixel (legacy CRPIX2 - Y shift)"),
            card("CD1_1", float(w["CD1_1"]), "coordinate transform matrix (legacy)"),
            card("CD1_2", float(w["CD1_2"]), "coordinate transform matrix (legacy)"),
            card("CD2_1", float(w["CD2_1"]), "coordinate transform matrix (legacy)"),
            card("CD2_2", float(w["CD2_2"]), "coordinate transform matrix (legacy)"),
        ]
    else:                                           # no legacy WCS: placeholder
        wcs_cards = [
            card("CTYPE1", "RA---TAN", "coordinate type"),
            card("CTYPE2", "DEC--TAN", "coordinate type"),
            card("CRVAL1", 0.0, "placeholder coordinate reference RA [deg]"),
            card("CRVAL2", 0.0, "placeholder coordinate reference DEC [deg]"),
            card("CRPIX1", 0.0, "placeholder coordinate reference pixel"),
            card("CRPIX2", 0.0, "placeholder coordinate reference pixel"),
            card("CD1_1", -PIX_SCALE / 3600.0, "coordinate transform matrix"),
            card("CD1_2", 0.0, "coordinate transform matrix"),
            card("CD2_1", 0.0, "coordinate transform matrix"),
            card("CD2_2", PIX_SCALE / 3600.0, "coordinate transform matrix"),
        ]

    return [
        card("XTENSION", "IMAGE", "image extension"),
        card("BITPIX", 16, "array data type"),
        card("NAXIS", 2, "number of array dimensions"),
        card("NAXIS1", AMP_COLS, "amp image width including overscan"),
        card("NAXIS2", HALF_ROWS, "amp image active rows"),
        card("PCOUNT", 0),
        card("GCOUNT", 1),
        card("BZERO", 32768, "unsigned 16-bit zero point"),
        card("BSCALE", 1, "default scale"),
        card("BUNIT", sv(ph, "BUNIT", "ADU"), "pixel unit"),
        card("EXTNAME", ext, "amplifier image extension"),
        card("EXTTYPE", "AMP_RAW", "L0 amplifier raw image"),
        card("REALDATA", True, "actual amplifier data from legacy raw"),
        card("MOCKDATA", True, "mock 64-amp geometry built from legacy 32-amp"),
        card("DATAPROD", "L0_AMP", "data product type"),
        card("CHIPID", chip, "CCD identifier"),
        card("CCDNAME", f"KMTNet CCD {chip}", "CCD name"),
        card("AMPID", global_amp, "global amplifier ID"),
        card("AMPSEQ", amp, "amplifier sequence within CCD"),
        card("STRIPID", strip_id(amp), "vertical strip ID"),
        card("ENDID", end_id(amp), "readout end ID"),
        card("AMPNAME", ext, "amplifier name"),
        card("RAWFILE", NA, "source raw FITS file (mock: no Archon raw)"),
        card("ORIGFILE", strip_info.get("origfile", NA), "source legacy MEF file"),
        card("ORIGEXT", strip_info.get("legacy_ext", NA), "source legacy extension"),
        card("CTRLID", 1 if chip in ("M", "K") else 2, "science controller ID"),
        card("MODULE", 1 + ((amp - 1) // 8), "controller module placeholder"),
        card("CHANNEL", 1 + ((amp - 1) % 8), "controller channel placeholder"),
        card("CHIPFLP", CHIPFLP, "no chip-dependent OSU-style flip applied"),
        card("STRIPDIR", STRIPDIR, "strip number direction in CEU L0 packing"),
        card("READDIR", read_dir, "physical readout direction placeholder"),
        card("AMPPACK", AMPPACK, "mock packing: data [1:1152], overscan [1153:1200]"),
        card("CCDSUM", "1 1", "on-chip binning factors"),
        card("CCDSEC", fmtsec(cx1, cx2, cy1, cy2), "amplifier section in CCD coords"),
        card("AMPSEC", fmtsec(cx1, cx2, cy1, cy2), "amplifier section in CCD coords"),
        card("DETSEC", fmtsec(dx1, dx2, dy1, dy2), "amplifier coords on detector mosaic"),
        card("RAWDATA", NA, "source raw data section (mock: no Archon raw)"),
        card("RAWBIAS", NA, "source raw overscan section (mock: no Archon raw)"),
        card("DATASEC", DATASEC_UNIFORM, "active data section (uniform mock packing)"),
        card("PRESEC", PRESEC_STR, "no prescan in mock amp image"),
        card("BIASSEC", BIASSEC_UNIFORM, "local overscan section (uniform mock packing)"),
        card("TRIMSEC", DATASEC_UNIFORM, "trimmed data section (uniform mock packing)"),
        card("RAWNAX1", NA_INT, "source raw image width (-1 = na)"),
        card("RAWNAX2", NA_INT, "source raw image height (-1 = na)"),
        card("RAWXTILE", AMP_COLS, "amp tile width"),
        card("AMPDATA", AMP_DATA_COLS, "active columns per amp tile"),
        card("OVERSCNX", OVERSCAN_X, "X overscan columns per amp tile"),
        card("PRESCANX", PRESCAN_X, "X prescan columns per amp tile"),
        card("MIDOVSCY", NA_INT, "middle Y overscan rows (-1 = na)"),
        card("GAIN", strip_info["gain"], "amp gain [e-/ADU] (legacy 32-amp value)"),
        card("RDNOISE", strip_info["rdnoise"], "read noise [e-] (legacy 32-amp value)"),
        card("SATURAT", 62000, "saturation level placeholder [ADU]"),
        card("LINMAX", 58000, "linearity maximum placeholder [ADU]"),
        card("FILTER", sv(ph, "FILTER"), "filter name in beam"),
        card("PROJID", sv(ph, "PROJID"), "project ID"),
        card("IMAGETYP", sv(ph, "IMAGETYP"), "type of observation"),
        card("OBJECT", sv(ph, "OBJECT"), "object name"),
        card("OBSTYPE", sv(ph, "OBSTYPE"), "type of observation"),
        card("RA", sv(ph, "RA", "00:00:00.00"), "telescope RA"),
        card("DEC", sv(ph, "DEC", "+00:00:00.0"), "telescope DEC"),
        card("HA", sv(ph, "HA"), "hour angle"),
        card("ST", sv(ph, "ST"), "local sidereal time"),
        card("SECZ", sv(ph, "SECZ"), "airmass"),
        card("ALT", sv(ph, "ALT"), "telescope altitude [deg]"),
        card("AZ", sv(ph, "AZ"), "telescope azimuth [deg]"),
        card("UT", ut, "UTC timestamp"),
        *wcs_cards,
        card("WCSDIM", 2, "coordinate system dimensionality"),
        # IRAF physical / mosaic transforms so ds9 physical coords match the
        # legacy display: physical x = strip column 1..1152, y = CCD row 1..9232.
        # NOTE: no EQUINOX/RADESYS here, exactly like the legacy extensions, so
        # WCS libraries interpret both files in the same (default ICRS) frame.
        card("LTV1", 0.0, "CCD-strip to image transform (x)"),
        card("LTV2", float(-y_shift), "CCD to image transform (y; TOP half shifted)"),
        card("LTM1_1", 1.0, "CCD to image transform"),
        card("LTM1_2", 0.0, "CCD to image transform"),
        card("LTM2_1", 0.0, "CCD to image transform"),
        card("LTM2_2", 1.0, "CCD to image transform"),
        # ds9/IRAF convention: detector = DTM x PHYSICAL + DTV (not image+DTV),
        # so with physical y already the CCD row, DTV2 = CHIP_Y0-1 for BOTH ends
        # (dy1-1-y_shift). Verified: physical + DTV == DETSEC for all 64 amps.
        card("DTV1", float(dx1 - 1), "physical to detector mosaic transform (x)"),
        card("DTV2", float(dy1 - 1 - y_shift), "physical to detector mosaic transform (y)"),
        card("DTM1_1", 1.0, "physical to detector mosaic transform"),
        card("DTM1_2", 0.0, "physical to detector mosaic transform"),
        card("DTM2_1", 0.0, "physical to detector mosaic transform"),
        card("DTM2_2", 1.0, "physical to detector mosaic transform"),
    ]


# --------------------------------------------------------------------------- #
# Binary tables
# --------------------------------------------------------------------------- #
def table_defs():
    amp_cols = [
        ("EXTNAME", "8A", ""), ("AMPID", "I", ""), ("CHIPID", "1A", ""),
        ("STRIPID", "I", ""), ("ENDID", "3A", ""), ("STRIPDIR", "2A", ""),
        ("AMPSEQ", "I", ""), ("AMPNAME", "5A", ""), ("RAWFILE", "32A", ""),
        ("CTRLID", "I", ""), ("MODULE", "I", ""), ("CHANNEL", "I", ""),
        ("CCDSEC", "24A", ""), ("AMPSEC", "24A", ""), ("DETSEC", "28A", ""),
        ("RAWDATA", "32A", ""), ("RAWBIAS", "32A", ""),
        ("DATASEC", "24A", ""), ("PRESEC", "18A", ""), ("BIASSEC", "24A", ""), ("TRIMSEC", "24A", ""),
        ("CHIPFLP", "8A", ""), ("READDIR", "2A", ""),
        ("GAIN", "E", "e-/ADU"), ("RDNOISE", "E", "e-"), ("SATLEVEL", "J", "ADU"), ("LINMAX", "J", "ADU"),
        ("RAWX0", "J", "pixel"), ("RAWX1", "J", "pixel"), ("RAWY0", "J", "pixel"), ("RAWY1", "J", "pixel"),
        ("AMPX0", "J", "pixel"), ("AMPX1", "J", "pixel"), ("AMPY0", "J", "pixel"), ("AMPY1", "J", "pixel"),
        ("DETX0", "J", "pixel"), ("DETX1", "J", "pixel"), ("DETY0", "J", "pixel"), ("DETY1", "J", "pixel"),
        ("XTALKGROUP", "8A", ""),
    ]
    xtalk_cols = [
        ("SOURCE_AMP", "I", ""), ("TARGET_AMP", "I", ""), ("XTALK_COEF", "D", ""),
        ("XTALK_ERROR", "D", ""), ("XTALK_VERSION", "16A", ""), ("MEASURE_DATE", "19A", "UTC"), ("STATUS", "12A", ""),
    ]
    volt_cols = [("VOLTNAME", "16A", ""), ("SETPOINT", "E", ""), ("MEASURED", "E", ""), ("UNIT", "8A", ""), ("STATUS", "12A", "")]
    tel_cols = [("CTRLID", "I", ""), ("FWVERSION", "16A", ""), ("BOARDTEMP", "E", "deg C"), ("READTIME", "E", "s"), ("STATUS", "12A", ""), ("ERRORFLAG", "I", "")]
    return amp_cols, xtalk_cols, volt_cols, tel_cols


def ampinfo_rows(strips: dict):
    rows = []
    for chip in CHIP_ORDER:
        for amp in range(1, 17):
            ext = extname_for(chip, amp)
            info = strips[chip][strip_id(amp)]
            cx1, cx2, cy1, cy2 = ccdsec(amp)
            dx1, dx2, dy1, dy2 = detsec(chip, amp)
            rows.append({
                "EXTNAME": ext,
                "AMPID": AMP_BASE[chip] + amp,
                "CHIPID": chip,
                "STRIPID": strip_id(amp),
                "ENDID": end_id(amp),
                "STRIPDIR": STRIPDIR,
                "AMPSEQ": amp,
                "AMPNAME": ext,
                "RAWFILE": NA,
                "CTRLID": 1 if chip in ("M", "K") else 2,
                "MODULE": 1 + ((amp - 1) // 8),
                "CHANNEL": 1 + ((amp - 1) % 8),
                "CCDSEC": fmtsec(cx1, cx2, cy1, cy2),
                "AMPSEC": fmtsec(cx1, cx2, cy1, cy2),
                "DETSEC": fmtsec(dx1, dx2, dy1, dy2),
                "RAWDATA": NA,
                "RAWBIAS": NA,
                "DATASEC": DATASEC_UNIFORM,
                "PRESEC": PRESEC_STR,
                "BIASSEC": BIASSEC_UNIFORM,
                "TRIMSEC": DATASEC_UNIFORM,
                "CHIPFLP": CHIPFLP,
                "READDIR": "-Y" if amp <= 8 else "+Y",
                "GAIN": info["gain"],
                "RDNOISE": info["rdnoise"],
                "SATLEVEL": 62000,
                "LINMAX": 58000,
                "RAWX0": NA_INT, "RAWX1": NA_INT, "RAWY0": NA_INT, "RAWY1": NA_INT,
                "AMPX0": cx1, "AMPX1": cx2, "AMPY0": cy1, "AMPY1": cy2,
                "DETX0": dx1, "DETX1": dx2, "DETY0": dy1, "DETY1": dy2,
                "XTALKGROUP": f"C{1 if chip in ('M', 'K') else 2}M{1 + ((amp - 1) // 8)}",
            })
    return rows


def xtalk_rows():
    today = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "")
    return [{"SOURCE_AMP": s, "TARGET_AMP": t, "XTALK_COEF": 0.0, "XTALK_ERROR": 0.0,
             "XTALK_VERSION": "UNMEASURED", "MEASURE_DATE": today, "STATUS": "PLACEHOLDER"}
            for s in range(1, 65) for t in range(1, 65)]


def volt_rows():
    return [{"VOLTNAME": n, "SETPOINT": 0.0, "MEASURED": 0.0, "UNIT": "V", "STATUS": "UNKNOWN"}
            for n in ["VOD", "VRD", "VOG", "VSS", "VDD", "PCLKH", "PCLKL", "SCLKH", "SCLKL"]]


def telemetry_rows():
    return [
        {"CTRLID": 1, "FWVERSION": "UNKNOWN", "BOARDTEMP": -999.0, "READTIME": -1.0, "STATUS": "UNKNOWN", "ERRORFLAG": -1},
        {"CTRLID": 2, "FWVERSION": "UNKNOWN", "BOARDTEMP": -999.0, "READTIME": -1.0, "STATUS": "UNKNOWN", "ERRORFLAG": -1},
    ]


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def default_output_name(legacy_path: Path, primary_hdr: dict, outdir: Path) -> Path:
    m = re.match(r"^(kmt[a-z]?)\.(\d{8})\.(\d{6})", legacy_path.name)
    if m:
        obs = str(primary_hdr.get("OBSERVAT", "")).upper()
        prefix = {"CTIO": "kmtc", "SAAO": "kmts", "SSO": "kmta"}.get(obs, m.group(1))
        root = f"{prefix}.{m.group(2)}.{m.group(3)}"
    else:
        root = legacy_path.stem
    return outdir / f"{root}.ceu.l0amp.mock64.mef.fits"


def convert(legacy_path: Path, out_path: Path) -> Path:
    primary_hdr, strips = read_legacy(legacy_path)
    for chip in CHIP_ORDER:
        for s in strips[chip]:
            strips[chip][s]["origfile"] = legacy_path.name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp-{os.getpid()}")
    try:
        with tmp_path.open("wb") as fout:
            fout.write(header_bytes(primary_cards(primary_hdr, legacy_path, out_path)))
            for chip in CHIP_ORDER:
                for amp in range(1, 17):
                    info = strips[chip][strip_id(amp)]
                    fout.write(header_bytes(amp_cards(chip, amp, primary_hdr, info)))
                    fout.write(pad_data(build_amp_image(info, amp).tobytes(order="C")))
            amp_cols, xtalk_cols, volt_cols, tel_cols = table_defs()
            fout.write(bintable_bytes("AMPINFO", amp_cols, ampinfo_rows(strips), [
                card("NAMP", 64, "number of amplifier rows"),
                card("GEOMVER", GEOMETRY_VERSION, "geometry version (mock uniform packing)"),
                card("AMPPACK", AMPPACK, "mock packing: data [1:1152], overscan [1153:1200]"),
                card("RAWGROUP", NA, "raw grouping (mock: no Archon raw)"),
            ]))
            fout.write(bintable_bytes("XTALKINFO", xtalk_cols, xtalk_rows(), [
                card("NXTALK", 4096, "number of crosstalk matrix rows"),
                card("XTALKVER", "UNMEASURED", "placeholder crosstalk version"),
                card("XTALKCAL", False, "replace coefficients after calibration"),
            ]))
            fout.write(bintable_bytes("VOLTINFO", volt_cols, volt_rows(), [
                card("BIASVER", "UNKNOWN", "bias setting version"),
                card("CLKVER", "UNKNOWN", "clock setting version"),
                card("VOLTSTAT", "UNKNOWN", "voltage telemetry status"),
            ]))
            fout.write(bintable_bytes("TELEMETRY", tel_cols, telemetry_rows(), [
                card("NCTRL", 2, "number of science controllers"),
                card("TELSTAT", "UNKNOWN", "telemetry status"),
            ]))
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise
    return out_path


def main():
    p = argparse.ArgumentParser(
        description="Convert legacy 32-amp KMTNet MEF into a mock 64-amp KMT-CEU L0 MEF (v2.0)")
    p.add_argument("inputs", nargs="+", help="legacy 32-amp MEF file(s)")
    p.add_argument("-d", "--outdir", default=".", help="output directory")
    p.add_argument("-o", "--output", default=None,
                   help="explicit output path (only valid with a single input)")
    p.add_argument("-f", "--force", action="store_true", help="overwrite existing output")
    args = p.parse_args()

    if args.output and len(args.inputs) != 1:
        p.error("--output can only be used with a single input file")

    outdir = Path(args.outdir).resolve()
    for inp in args.inputs:
        legacy = Path(inp).resolve()
        if not legacy.exists():
            raise FileNotFoundError(legacy)
        with fits.open(legacy, memmap=True) as h:
            phdr = clean_primary_dict(h[0].header)
        out = Path(args.output).resolve() if args.output else default_output_name(legacy, phdr, outdir)
        if out.exists() and not args.force:
            raise FileExistsError(f"Output exists: {out}; use -f to overwrite")
        convert(legacy, out)
        print(f"{legacy.name} -> {out}")


if __name__ == "__main__":
    main()

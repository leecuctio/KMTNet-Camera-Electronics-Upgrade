#!/usr/bin/env python3
"""
KMT-CEU Archon MK/NT raw FITS to L0 64-amplifier MEF converter.

Input raw files:
  <SITE>.YYYYMMDD.NNNNNN.MK.fits  -> M, K chips
  <SITE>.YYYYMMDD.NNNNNN.NT.fits  -> N, T chips
  <SITE> in {KMTC=CTIO, KMTS=SAAO, KMTA=SSO, KMTK=KASI} (DECISION_LOG D-011, D-017)

Output L0 Raw MEF layout:
  PRIMARY
  M01T ... M08T, M01B ... M08B
  K01T ... K08T, K01B ... K08B
  N01T ... N08T, N01B ... N08B
  T01T ... T08T, T01B ... T08B
  AMPINFO
  XTALKINFO
  VOLTINFO
  TELEMETRY

The L0 product preserves each amplifier image separately, including its local
overscan pixels, to support amplifier-level overscan/bias/gain/crosstalk
calibration before any CCD-level image assembly.

v2.1.1 changes:
  - use datetime.timezone.utc instead of datetime.UTC for Python 3.9/3.10 compatibility
  - write FITS logical values in standard right-aligned format
  - parse FITS card comments without splitting quoted string values
  - write output through a temporary file before atomic replacement

v2.1.2 changes:
  - write header floats with shortest round-trip representation; the old
    %.10G formatting truncated JD by ~30 s and made JD inconsistent with
    MJD-OBS in the primary header (same fix as kmt_ceu_legacy32_to_l0amp_mef_v2)

v2.1.3 changes:
  - PIX_SCALE 0.400 -> 0.395 arcsec/px: plate scale measured against Gaia DR3
    (16 chip solutions on 2026-06-30 frames: 0.3952 +/- 0.00001 arcsec/px);
    affects the PIXSCALE card and the placeholder CD matrix

v2.2.0 changes (D-011):
  - raw filename prefix is now a site code (KMTC/KMTS/KMTA/KMTT) instead of
    the fixed literal KMTN; default_output_name() derives the output MEF
    prefix from the filename site code and cross-checks it against the
    OBSERVAT header (mismatch is an error); find_pair() is prefix-agnostic
    and unchanged

v2.3.0 changes:
  - --ampchar CSV (cam_char/results schema, keyed by EXTNAME) stamps
    measured GAIN/RDNOISE/SATURAT/LINMAX into the amp extension headers and
    the AMPINFO table; values <= 0 or missing keep the placeholders, and an
    AMPCHAR primary card records the table name. Same mechanism as
    kmt_ceu_legacy32_to_l0amp_mef_v2. Follows the raw spec keyword layering
    rule (2026-08-22): gain/noise never ride in the Archon raw header - they
    enter the chain here, at raw -> L0.

v2.4.0 changes (D-017):
  - testbed site code retired: KMTT/TESTBED -> KMTK/KASI (DECISION_LOG
    D-017, 2026-08-25; the testbed sits at KASI, and KMTT's T read like the
    T chip). default_output_name() now accepts KMTK filenames and
    cross-checks them against OBSERVAT=KASI; L0 MEF prefix kmtt -> kmtk.
    KMTT-named files are no longer recognized - no data was ever produced
    under that code.

v2.5.0 changes (C-5 / C-11 / C-12 / C-13 / C-17 / C-18, plus the MEF-side
                WCS and FITS-conformance items):
  - SKY WCS IS REAL. CRVAL/CRPIX were hardcoded 0.0 on all 64 extensions, so
    every L0 resolved to RA~359.93 Dec~+0.25 with no error raised anywhere.
    Now CRVAL = the TCS boresight, parsed from RA (sexagesimal HOURS, x15)
    and DEC (sexagesimal DEGREES, sign applied to the whole value), and it is
    identical on all 64 extensions; CRPIX carries the whole per-amp offset
    from the boresight mosaic pixel, including +48 for the left-overscan
    strips 5-8.  CD stays uniform on all 64 amps: raw spec 4.3 is normative
    that the raw frame is stored in ascending CCD order in BOTH axes, so the
    serial/parallel readout direction and the e2v A/D section alternation
    never reach the stored pixel order and must NOT flip CD.  The WCS is TCS
    derived and never fitted. Its ONLY job is to be the initial guess the L1
    astrometric step starts its Gaia fit from, so it carries the pipeline's
    own flags - WCSNAME='TCS-SEED', WCSAPPRX=T, WCSSOLVE=F - which that step
    flips to WCSAPPRX=F / WCSSOLVE=T (plus WCSRMS/WCSNSTAR/WCSNREF/WCSNMAT,
    catalogue in WCSCAT) once the Gaia solution lands, and leaves at F with a
    reason in WCSFAIL when it does not. When RA/DEC are unparseable every WCS
    card is OMITTED rather than defaulted (raw spec 5.0: never write a
    plausible wrong value) and WCSOMIT=T says so.
  - Frame types that never see sky get no seed at all. BIAS, DARK and
    DOMEFLAT cannot yield an astrometric solution, so a seed for them has no
    consumer - and sky coordinates on a frame that saw no sky are exactly the
    syntactically-valid-but-wrong value raw spec 5.0 forbids. Those carry
    WCSSKY=F + WCSOMIT=T, and the L1 step skips astrometry with the reason
    NOT_SKY_FRAME instead of reporting a failed solve on every calibration
    frame of the night. SKY (twilight flat) normally shows enough stars to
    solve, so it keeps its seed, as does OBJECT; plain FLAT is ambiguous in
    the IMAGETYP vocabulary and is treated as solvable, because a wrong skip
    is silent while a wrong attempt costs one flag. The IRAF pixel transforms
    LTV/LTM/DTV/DTM are written for every frame type - they describe the
    detector, not the sky.
  - IRAF physical/detector transforms LTV/LTM/DTV/DTM/ATV/ATM added, so ds9
    physical = CCD column/row and detector = mosaic pixel.  Invariant held by
    construction and asserted in the .hdu_verify.txt sidecar:
        CRPIX1 - LTV1 + DTV1 == BORESIGHT_X      (and the same in Y)
  - C-17: convert() read nt_hdr and then never used it, so N/T amps were
    stamped from the MK header.  amp_header()/write_amp_hdu()/ampinfo_rows()
    now take the owning chip's header.  This matters because CHMAP_* is one
    of the six cards raw spec 5.9 requires to DIFFER between pair members.
  - C-11: MODULE/CHANNEL were invented from the amp index.  They are now
    derived from the raw CHMAP_LT/LB/RT/RB tokens (4-char <chip><A|D><nn>)
    and cross-checked against the embedded Detector_Ch_to_AmpID_Map v1.1.
    Channel identity is published as CTRUNIT/CCDPORT/CHANNAME/CHANNUM/IMGSEC
    and XTALKGROUP is redefined on the real controller-port grouping.  A
    mismatch sets CHMAPOK=F and writes HISTORY lines rather than passing
    silently.
  - C-18: VOLTINFO/TELEMETRY are no longer all-placeholder.  Cn_VOLT/Cn_CURR
    are the 7 power-supply rails P2V5/P5V/P6V/N6V/P17V/N17V/P35V and Cn_TEMP
    is 10 Archon module temperatures with slot 1 = Backplane (raw spec
    5.6.1); the rails become VOLTINFO rows and slot 1 becomes
    TELEMETRY.BOARDTEMP.  The 9 CCD bias/clock rows have no source in the new
    raw and now carry -999.0/'PLACEHOLDER' instead of 0.0/'UNKNOWN', because
    0.0 V is a legal VSS reading and disguised missing data as a real one.
  - C-5/C-13: check_raw_geometry() compares the raw's own geometry
    declarations against this converter's hardcoded constants instead of
    ignoring them.  A changed raw declaration used to shift every slice with
    no error at all.
  - FITS conformance: fits_value() wrote string values in free format, so
    XTENSION= 'IMAGE' broke the fixed-format rule for mandatory string
    keywords - fitsverify rejected the file while astropy.verify(), the only
    check the release gate runs, passed.  Strings are now padded to the
    8-character minimum.  card() silently produced an UNBALANCED closing
    quote for any string value >= 69 chars; it now truncates inside the
    quotes and warns.  EQUINOX was relayed as the raw's STRING '2000.000'
    and is now a float.  RADESYS is written alongside the deprecated
    RADECSYS (which mef_pipeline matches by literal name, so it stays).
    CHECKSUM/DATASUM are written on every HDU.
  - Provenance: EXPID/DATASRC/FPAID/CTRL1CFG/CTRL2CFG/ICSBUILD/RDMODE and the
    HK block (HKUDATE/DMPTEMP/WALLBRD/HEBOX/HTR*/ENS1-7/Cn_*) are carried
    instead of dropped; UNIQNAME is retired (D-016/D-019 - identity is
    FILENAME + EXPID); ORIGIN is the constant 'KASI' (the MEF is a pipeline
    product, not an observatory raw); UT is assembled from DATE-OBS instead
    of the retired TSHOPEN, which left its time part blank.
  - PRODVER v2.1.1 -> v2.2.0 (new product keywords and AMPINFO columns).
    GEOMVER is unchanged - no amp ordering, section or layout change (D-004).
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import os
import re
import math
import shutil
import struct
import sys
import warnings
from pathlib import Path

import numpy as np

class ConverterWarning(UserWarning):
    """Anything the operator must see, on EVERY occurrence.

    Python's default filter prints one warning per source line per process, so
    a batch converting a night of exposures would report the first bad frame
    and stay silent for the rest.  main() registers 'always' for this class.
    """


BLOCK = 2880
SOFTWARE_VERSION = "v2.5.0"
PRODUCT_VERSION = "v2.2.0"  # v2.5.0: new WCS/IRAF/identity cards + AMPINFO columns
GEOMETRY_VERSION = "CEU-L0AMP-v2.1"  # unchanged: no ordering/section/layout change

# D-011 (2026-08-10): raw filename site code <-> L0 MEF filename prefix.
# The site code equals the TC telemetry TELID convention.
# D-017 (2026-08-25): KMTT/TESTBED retired -> KMTK/KASI.
SITE_PREFIX = {"KMTC": "kmtc", "KMTS": "kmts", "KMTA": "kmta", "KMTK": "kmtk"}
# OBSERVAT header value -> L0 MEF filename prefix (used for cross-check/fallback).
OBS_PREFIX = {"CTIO": "kmtc", "SAAO": "kmts", "SSO": "kmta", "KASI": "kmtk"}

CCD_COLS = 9216
CCD_ROWS = 9232
GAP_COLS = 460
GAP_ROWS = 933
RAW_NAXIS1 = 19200
RAW_NAXIS2 = 9400
RAW_XTILE = 1200
AMP_DATA_COLS = 1152
OVERSCAN_X = 48
PRESCAN_X = 0
ACTIVE_HALF_ROWS = 4616
MIDDLE_OVERSCAN_Y = 168
PIX_SIZE = 10.0
PIX_SCALE = 0.395  # arcsec/px, measured vs Gaia DR3 (was 0.400 nominal)

CHIP_ORDER = ["M", "K", "N", "T"]
TAG_TO_CHIPS = {"MK": ["M", "K"], "NT": ["N", "T"]}
CHIP_TO_TAG = {"M": "MK", "K": "MK", "N": "NT", "T": "NT"}
AMP_BASE = {"M": 0, "K": 16, "N": 32, "T": 48}
CHIP_X0 = {"M": 1, "K": CCD_COLS + GAP_COLS + 1, "N": 1, "T": CCD_COLS + GAP_COLS + 1}
CHIP_Y0 = {"M": CCD_ROWS + GAP_ROWS + 1, "K": CCD_ROWS + GAP_ROWS + 1, "N": 1, "T": 1}

# CEU convention: no chip-dependent OSU-style image flip at L0 packing stage.
CHIPFLP = "None"
STRIPDIR = "+X"

# --- approximate sky WCS -------------------------------------------------
# Boresight (tangent point) in DETSIZE mosaic pixels.  Recovered from the
# operational legacy KMTNet WCS, where CRPIX1 + (DETSEC.x1 - 1) - LTV1 is
# 9418.0 on all 32 extensions of files from two sites nine years apart, and
# CRPIX2 + (DETSEC.y1 - 1) - LTV2 is 9699.0 = (1 + 19397)/2, the exact
# DETSIZE centre.  The legacy files put N/T one pixel lower (9698.0); that is
# their documented DTV2-vs-DETSEC off-by-one, not physics, so all four chips
# use 9699.0 here.
# NOTE the X value is 28.5 px (11.3") from the geometric centre 9446.5.  No
# document in the spec corpus explains the offset.  It is either a real
# optical boresight offset or the legacy authors omitting their 27-column
# prescan.  It is adopted because it is what 20 years of KMTNet archive use;
# one Gaia-matched on-sky frame would settle it.  It only has to be close
# enough for the L1 Gaia fit to converge, and 11" is well inside its capture
# radius, but it is published as BOREPIXX/BOREPIXY so a later solution can be
# differenced against it.
BORESIGHT_X = 9418.0
BORESIGHT_Y = 9699.0
CD_SCALE = PIX_SCALE / 3600.0        # deg/px
# The L0 WCS exists for ONE purpose: to be the initial guess the L1
# astrometric step starts its Gaia fit from.  It is not a product WCS and
# nothing should measure a position with it.  The flag vocabulary is the
# pipeline's own (mef_pipeline/kmt_ceu_preproc/astrometry.py):
#   WCSAPPRX=T  approximate; the Gaia fit has not replaced it yet
#   WCSSOLVE=F  no astrometric solution has been attempted on this product
# and after the L1 Gaia solve those become WCSAPPRX=F / WCSSOLVE=T alongside
# WCSRMS / WCSNSTAR / WCSNREF / WCSNMAT, with the catalogue named in WCSCAT.
# A failed solve keeps this seed and records WCSSOLVE=F + WCSFAIL.
WCSNAME_L0 = "TCS-SEED"

# Which frame types actually see sky.  IMAGETYP's controlled vocabulary is
# BIAS / DARK / OBJECT / FLAT / SKY / DOMEFLAT (raw spec 5.4).
#   BIAS, DARK   - shutter closed, no light at all
#   DOMEFLAT     - illuminated screen inside a closed dome
# Those three can never yield an astrometric solution, so a seed WCS for them
# has no consumer: its only purpose is to start the L1 Gaia fit, and that fit
# will not run.  Writing sky coordinates onto a frame that saw no sky is the
# "syntactically valid, quietly wrong" value raw spec 5.0 forbids.
#   OBJECT       - science field
#   SKY          - twilight/sky flat; normally shows enough stars to solve
# Plain FLAT is ambiguous in the vocabulary (the dome case has its own value),
# so it is treated as sky-bearing: attempting and failing costs one flagged
# solve, while wrongly skipping silently loses astrometry that was available.
NOSKY_IMAGETYP = frozenset(("BIAS", "DARK", "DOMEFLAT"))

# --- Archon house-keeping slot ordering (raw spec v1.13 5.6.1) -----------
# The values carry no labels; they can only be decoded with these tables.
# Modules 6, 7 and 12 do not occupy a slot, so the slot COUNT is itself a
# configuration discriminator - a different count means a different camera.
# Kept in full because it is the only record of what the ten unlabelled
# Cn_TEMP values mean; slot 1 (Backplane) is the one the MEF consumes.
CTRL_TEMP_SLOTS = ("Backplane", "Mod1:LVDS", "Mod2:Driver", "Mod3:Driver",
                   "Mod4:LVXBias", "Mod5:ADM", "Mod8:ADM", "Mod9:HVYBias",
                   "Mod10:Driver", "Mod11:Driver")
# Power-supply rails, NOT CCD bias voltages.  Cn_VOLT and Cn_CURR share the
# order.  The guide controller has an eighth (HEATER) rail; a science frame
# must never be decoded with the guide table.
CTRL_RAILS = ("P2V5", "P5V", "P6V", "N6V", "P17V", "N17V", "P35V")
RAILREF = "RAWSPEC-v1.13-5.6.1"
# CCD bias/clock names the MEF has always declared.  The raw card family that
# fed them (VOLT<n>/VSET<n>/VMEA<n>) was retired, so they stay unmeasured.
BIAS_CLOCK_VOLTNAMES = ("VOD", "VRD", "VOG", "VSS", "VDD",
                        "PCLKH", "PCLKL", "SCLKH", "SCLKL")
HK_REAL_SENTINEL = -999.0            # raw spec 5.0 Real sentinel
HK_INT_SENTINEL = -1                 # raw spec 5.0 Integer sentinel

# --- CCD output channel map ---------------------------------------------
# raw_fits_spec/Detector_Ch_to_AmpID_Map_v1.1.txt, transcribed.  amps 1-8 are
# the TOP end and 9-16 the BOT end; within each end the amp index ascends
# with raw X.  Embedded rather than read at runtime because this file is a
# standalone script that must convert without its sibling spec tree.
AMPID_MAP_VERSION = "Detector_Ch_to_AmpID_Map_v1.1"
_AMPID_MAP_SRC = {
    "M": ("MD16 MD15 MD14 MD13 MD12 MD11 MD10 MD09",
          "MA01 MA02 MA03 MA04 MA05 MA06 MA07 MA08"),
    "K": ("KA08 KA07 KA06 KA05 KA04 KA03 KA02 KA01",
          "KD09 KD10 KD11 KD12 KD13 KD14 KD15 KD16"),
    "N": ("NA08 NA07 NA06 NA05 NA04 NA03 NA02 NA01",
          "ND09 ND10 ND11 ND12 ND13 ND14 ND15 ND16"),
    "T": ("TD16 TD15 TD14 TD13 TD12 TD11 TD10 TD09",
          "TA01 TA02 TA03 TA04 TA05 TA06 TA07 TA08"),
}
AMPID_MAP = {(chip, half * 8 + i + 1): tok
             for chip, rows in _AMPID_MAP_SRC.items()
             for half, row in enumerate(rows)
             for i, tok in enumerate(row.split())}

# --- raw geometry declarations to cross-check (C-5 / C-13) ---------------
# The converter slices with its own constants.  If a raw declaration ever
# disagrees, the pixels come out of the wrong place and nothing raises.
RAW_GEOM_EXPECT = {
    "NAXIS1": RAW_NAXIS1,
    "NAXIS2": RAW_NAXIS2,
    "AMPNAX1": RAW_XTILE,
    "AMPNAX2": RAW_NAXIS2 // 2,
    "IMAGEX": AMP_DATA_COLS,
    "IMAGEY": ACTIVE_HALF_ROWS,
    "PRESCNX": PRESCAN_X,
    "PRESCNY": 0,
    "OVRSCNX": OVERSCAN_X,
    "OVRSCNY": MIDDLE_OVERSCAN_Y // 2,
    "NAMPDET": 16,
    "NAMPRAW": 32,
}
# PIX_SCALE alone sets the whole CD matrix, and the binning factors decide
# whether any of the section arithmetic means anything, so they are compared
# too - as floats, with a tolerance.
RAW_GEOM_EXPECT_FLOAT = {
    "PIXSCALE": (PIX_SCALE, 1e-6),
    "PIXSIZE": (PIX_SIZE, 1e-6),
    "CCDXBIN": (1.0, 1e-9),
    "CCDYBIN": (1.0, 1e-9),
}

# Values that mean "no measurement", not a number.
_NULLISH = {"", "NC", "N/A", "NA", "NONE", "UNKNOWN", "-", "--"}


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
        if not math.isfinite(v):
            raise ValueError("non-finite value cannot be written to a FITS card")
        # Shortest round-trip representation (full double precision). The old
        # %.10G formatting truncated JD by ~30 s and CRVAL by ~1e-4 arcsec.
        s = repr(v).upper()
        if len(s) <= 20:
            return f"{s:>20}"
        # repr is the shortest round-trip form; when even that overflows the
        # 20-character value field, step down one significant digit at a time
        # rather than jumping straight to 16.
        for prec in range(17, 6, -1):
            s = f"{v:.{prec}G}"
            if len(s) <= 20:
                return f"{s:>20}"
        return f"{v:20.6G}"
    # FITS fixed format: a string value is left-justified from column 11 and
    # padded to at least 8 characters.  Writing it free-format leaves
    # XTENSION= 'IMAGE' one character short of the standard, which fitsverify
    # rejects on every extension while astropy.verify() passes it.
    s = str(v).replace("'", "''")
    # Minimum 8 characters inside the quotes, and the whole token padded to
    # the 20-character fixed-format value field (columns 11-30) so comments
    # start where cfitsio and astropy expect.  This is not cosmetic: those
    # tools verify CHECKSUM by substituting zeros into their OWN rendering of
    # the card, so a card padded differently verifies as corrupt.
    return ("'" + s.ljust(8) + "'").ljust(20)


def card(key: str, value=None, comment: str | None = None) -> bytes:
    if key in ("COMMENT", "HISTORY"):
        line = f"{key:<8} {'' if value is None else str(value)}"
        return line[:80].ljust(80).encode("ascii", errors="replace")
    if len(key) > 8:
        _warn(f"FITS keyword longer than 8 characters, truncated: {key!r}")
    k = key[:8].ljust(8)
    if value is None:
        return k.ljust(80).encode("ascii", errors="replace")
    body = fits_value(value)
    if len(k) + 2 + len(body) > 80:
        if isinstance(value, (bool, int, float)):
            raise ValueError(f"numeric value too wide for a FITS card: {key}={value!r}")
        # Blindly slicing the finished line to 80 used to cut a long string
        # value in half and leave the closing quote off, producing a card no
        # FITS reader can parse.  Truncate inside the quotes instead, and say
        # so - a silently shortened provenance string is still a lie.
        room = 80 - len(k) - 2 - 2
        raw = str(value)
        while len(raw.replace("'", "''")) > room:
            raw = raw[:-1]
        _warn(f"FITS string value truncated to fit one card: {key!r}")
        body = "'" + raw.replace("'", "''").ljust(8) + "'"
    line = f"{k}= {body}"
    if comment:
        line = (line + f" / {comment}")[:80]
    return line.ljust(80).encode("ascii", errors="replace")


def header_bytes(cards: list[bytes]) -> bytes:
    return pad_header(b"".join(cards + [card("END")]))


# --- FITS checksum (Seaman/Pence/Rots) ----------------------------------

def _fits_sum32(buf: bytes, acc: int = 0) -> int:
    """32-bit ones-complement sum over 4-byte groups; buf must be padded."""
    a = np.frombuffer(buf, dtype=">u2")
    hi = int(a[0::2].sum(dtype=np.uint64)) + (acc >> 16)
    lo = int(a[1::2].sum(dtype=np.uint64)) + (acc & 0xFFFF)
    while hi > 0xFFFF or lo > 0xFFFF:
        hicarry, locarry = hi >> 16, lo >> 16
        hi = (hi & 0xFFFF) + locarry
        lo = (lo & 0xFFFF) + hicarry
    return (hi << 16) + lo


_CHECKSUM_EXCLUDE = (0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40,
                     0x5B, 0x5C, 0x5D, 0x5E, 0x5F, 0x60)


def _checksum_encode(value: int) -> str:
    """Encode the complement of a 32-bit checksum as 16 ASCII characters."""
    value = ~value & 0xFFFFFFFF
    asc = [0] * 16
    for i in range(4):
        byte = (value >> (24 - 8 * i)) & 0xFF
        quotient, remainder = divmod(byte, 4)
        ch = [quotient + 0x30] * 4
        ch[0] += remainder
        again = True
        while again:                       # step off ASCII punctuation
            again = False
            for bad in _CHECKSUM_EXCLUDE:
                for j in (0, 2):
                    if ch[j] == bad or ch[j + 1] == bad:
                        ch[j] += 1
                        ch[j + 1] -= 1
                        again = True
        for j in range(4):
            asc[4 * j + i] = ch[j]
    return "".join(chr(asc[(i + 15) % 16]) for i in range(16))


_CHECKSUM_STUB = b"CHECKSUM= '0000000000000000'"


def hdu_bytes(cards: list[bytes], data: bytes = b"") -> bytes:
    """One complete HDU with DATASUM and CHECKSUM filled in.

    An L0 MEF is an archive master; without these an undetected bit flip in
    700 MB of pixels looks exactly like real data.
    """
    data = pad_data(data)
    cards = list(cards) + [
        card("DATASUM", str(_fits_sum32(data)), "data unit checksum"),
        card("CHECKSUM", "0" * 16, "HDU checksum, FITS convention"),
    ]
    hdr = header_bytes(cards)
    enc = _checksum_encode(_fits_sum32(hdr, _fits_sum32(data)))
    if hdr.count(_CHECKSUM_STUB) != 1:
        raise ValueError("CHECKSUM placeholder not found exactly once")
    hdr = hdr.replace(_CHECKSUM_STUB, b"CHECKSUM= '" + enc.encode("ascii") + b"'", 1)
    return hdr + data


def parse_fits_value(txt: str):
    txt = txt.strip()
    if not txt:
        return ""
    if txt in ("T", "F"):
        return txt == "T"
    if txt.startswith("'"):
        m = re.match(r"'(.*)'", txt)
        return (m.group(1) if m else txt.strip("'")).replace("''", "'").strip()
    try:
        if any(ch in txt for ch in ".EeDd"):
            return float(txt.replace("D", "E").replace("d", "e"))
        return int(txt)
    except Exception:
        return txt


def split_fits_value_comment(txt: str):
    in_quote = False
    i = 0
    while i < len(txt):
        ch = txt[i]
        if ch == "'":
            if in_quote and i + 1 < len(txt) and txt[i + 1] == "'":
                i += 2
                continue
            in_quote = not in_quote
        elif ch == "/" and not in_quote:
            return txt[:i], txt[i + 1:]
        i += 1
    return txt, ""


def _is_end_card(raw80: bytes) -> bool:
    """True only for the real END card.

    Matching on a b"END" prefix also matches ENDID, which the MEF's own amp
    headers carry - a header reader written that way stops three cards in and
    reports a one-block header.
    """
    pad = b" \x00\t\r\n"
    return raw80[:8].strip(pad) == b"END" and not raw80[8:].strip(pad)


def read_primary_header(path: Path):
    blocks = []
    with path.open("rb") as f:
        while True:
            block = f.read(BLOCK)
            if not block:
                raise ValueError(f"No END card in FITS header: {path}")
            blocks.append(block)
            if any(_is_end_card(block[i:i+80]) for i in range(0, BLOCK, 80)):
                break
    raw_cards = []
    for block in blocks:
        for i in range(0, BLOCK, 80):
            raw80 = block[i:i+80]
            raw_cards.append(raw80.decode("ascii", errors="replace"))
            if _is_end_card(raw80):
                break
        if raw_cards and _is_end_card(raw_cards[-1].encode("ascii", errors="replace")):
            break
    hdr = {}
    for c in raw_cards:
        key = c[:8].strip().upper()
        if not key or key in ("COMMENT", "HISTORY", "END") or "=" not in c:
            continue
        val, _comment = split_fits_value_comment(c.split("=", 1)[1])
        hdr[key] = parse_fits_value(val)
    return hdr, len(blocks) * BLOCK


def hval(hdr: dict, key: str, default=""):
    return hdr.get(key.upper(), default)


def memmap_raw(path: Path):
    hdr, offset = read_primary_header(path)
    bitpix = int(hval(hdr, "BITPIX"))
    naxis1 = int(hval(hdr, "NAXIS1"))
    naxis2 = int(hval(hdr, "NAXIS2"))
    if bitpix != 16:
        raise ValueError(f"Only BITPIX=16 is supported, but {path.name} has {bitpix}")
    arr = np.memmap(path, dtype=">i2", mode="r", offset=offset, shape=(naxis2, naxis1))
    return hdr, arr


def find_pair(input_path: Path):
    name = input_path.name
    if name.endswith(".MK.fits"):
        mk = input_path
        nt = input_path.with_name(name.replace(".MK.fits", ".NT.fits"))
    elif name.endswith(".NT.fits"):
        nt = input_path
        mk = input_path.with_name(name.replace(".NT.fits", ".MK.fits"))
    else:
        raise ValueError("Input file must end with .MK.fits or .NT.fits")
    return mk, nt


def default_output_name(mk_path: Path, outdir: Path, mk_hdr: dict):
    m = re.match(r"^(KMTC|KMTS|KMTA|KMTK)\.(\d{8})\.(\d{6})\.MK\.fits$", mk_path.name)
    obs = str(hval(mk_hdr, "OBSERVAT", "KMT")).upper()
    obs_prefix = OBS_PREFIX.get(obs)
    if m:
        # D-011: the filename site code drives the output prefix; OBSERVAT
        # must agree so a misdeployed config or renamed file fails loudly.
        prefix = SITE_PREFIX[m.group(1)]
        if obs_prefix is not None and obs_prefix != prefix:
            raise ValueError(
                "Filename site code %s conflicts with OBSERVAT=%s (D-011)"
                % (m.group(1), obs))
        root = f"{m.group(2)}.{m.group(3)}"
    else:
        # The filename does not follow the D-011 grammar. D-020 settled that a
        # site outside the four is never quietly normalized - the site drags
        # the filename, the coordinates, ORIGIN and the observing-night
        # boundary with it, so one typo changes the identity of the data. We
        # still convert (the pixels are fine and the operator can always pass
        # -o), but the degraded prefix is said out loud instead of appearing
        # in a filename nobody looks at twice.
        prefix = obs_prefix or "kmt"
        if obs_prefix is None:
            _warn("%s: filename does not match <SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits "
                  "and OBSERVAT=%r is not one of CTIO/SSO/SAAO/KASI; the output "
                  "prefix falls back to %r. Pass -o to name it yourself (D-011, "
                  "D-020)." % (mk_path.name, obs, prefix))
        else:
            _warn("%s: filename does not match the D-011 grammar "
                  "<SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits; the output prefix %r is "
                  "taken from OBSERVAT=%r instead of the filename."
                  % (mk_path.name, prefix, obs))
        root = mk_path.stem.replace(".MK", "")
    return outdir / f"{prefix}.{root}.ceu.l0amp.mef.fits"


def strip_id(amp: int) -> int:
    return ((amp - 1) % 8) + 1


def end_id(amp: int) -> str:
    return "TOP" if amp <= 8 else "BOT"


def extname_for(chip: str, amp: int) -> str:
    return f"{chip}{strip_id(amp):02d}{'T' if amp <= 8 else 'B'}"


def is_bias_right(amp: int) -> bool:
    return (1 <= amp <= 4) or (9 <= amp <= 12)


def raw_x_sections(chip: str, amp: int):
    base = 0 if chip in ("M", "N") else 9600
    tile0 = base + (strip_id(amp) - 1) * RAW_XTILE
    if is_bias_right(amp):
        raw_data = (tile0 + 1, tile0 + AMP_DATA_COLS)
        raw_bias = (tile0 + AMP_DATA_COLS + 1, tile0 + RAW_XTILE)
        loc_data = (1, AMP_DATA_COLS)
        loc_bias = (AMP_DATA_COLS + 1, RAW_XTILE)
    else:
        raw_bias = (tile0 + 1, tile0 + OVERSCAN_X)
        raw_data = (tile0 + OVERSCAN_X + 1, tile0 + RAW_XTILE)
        loc_bias = (1, OVERSCAN_X)
        loc_data = (OVERSCAN_X + 1, RAW_XTILE)
    return raw_data, raw_bias, loc_data, loc_bias


def raw_y_section(amp: int):
    if amp <= 8:
        return RAW_NAXIS2 - ACTIVE_HALF_ROWS + 1, RAW_NAXIS2
    return 1, ACTIVE_HALF_ROWS


def ccdsec(amp: int):
    x1 = (strip_id(amp) - 1) * AMP_DATA_COLS + 1
    x2 = strip_id(amp) * AMP_DATA_COLS
    if amp <= 8:
        y1, y2 = ACTIVE_HALF_ROWS + 1, CCD_ROWS
    else:
        y1, y2 = 1, ACTIVE_HALF_ROWS
    return x1, x2, y1, y2


def detsec(chip: str, amp: int):
    x1, x2, y1, y2 = ccdsec(amp)
    return CHIP_X0[chip] + x1 - 1, CHIP_X0[chip] + x2 - 1, CHIP_Y0[chip] + y1 - 1, CHIP_Y0[chip] + y2 - 1


def fmtsec(x1, x2, y1, y2):
    return f"[{x1}:{x2},{y1}:{y2}]"


# --- value coercion ------------------------------------------------------
# The raw relays TCS/HK/AUX readings as legacy-format padded STRINGS, and
# that pass-through is deliberate: it keeps the type uniform across twenty
# years of archive.  So these helpers are used only where the MEF value must
# be numeric (EQUINOX, AIRMASS, table columns), never to rewrite the relayed
# string cards.

def _warn(msg: str):
    warnings.warn(msg, ConverterWarning, stacklevel=2)


def _num(value):
    """float() of a raw card value, or None when it carries no measurement."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value) if math.isfinite(value) else None
        except OverflowError:       # a 400-digit integer from a corrupt card
            return None
    txt = str(value).strip()
    if not txt or txt.upper() in _NULLISH:
        return None
    try:
        out = float(txt)
    except ValueError:
        return None
    # 'nan'/'inf' parse happily and then render as NAN/INF, which is not a
    # FITS number; int() of them raises. Treat them as no measurement.
    return out if math.isfinite(out) else None


def fnum(hdr: dict, key: str, default=None):
    v = _num(hval(hdr, key, ""))
    return default if v is None else v


def inum(hdr: dict, key: str, default=None):
    v = _num(hval(hdr, key, ""))
    return default if v is None else int(round(v))


# --- pointing -> approximate sky WCS ------------------------------------

_SEX_RE = re.compile(r"^\s*([+-]?)\s*(\d+)[:\s](\d+)[:\s]([\d.]+)\s*$")


def ra_hours_to_deg(txt):
    """'hh:mm:ss.ss' in sexagesimal HOURS -> degrees, or None."""
    mo = _SEX_RE.match(str(txt))
    if not mo:
        return None
    sign = -1.0 if mo.group(1) == "-" else 1.0
    h, mi, sec = float(mo.group(2)), float(mo.group(3)), float(mo.group(4))
    # A truncated or corrupted TCS string often still looks sexagesimal.
    # Wrapping it into a valid-looking angle is the failure mode this whole
    # module exists to avoid, so refuse instead.
    if h >= 24.0 or mi >= 60.0 or sec >= 60.0:
        return None
    return (sign * (h + mi / 60.0 + sec / 3600.0) * 15.0) % 360.0


def dec_sex_to_deg(txt):
    """'+dd:mm:ss.s' in sexagesimal DEGREES -> degrees, or None.

    The sign applies to the WHOLE value: '-30:00:00.4' is -30.00011, not
    -29.99989.  Getting this wrong is silent and grows with the arcmin field.
    """
    mo = _SEX_RE.match(str(txt))
    if not mo:
        return None
    sign = -1.0 if mo.group(1) == "-" else 1.0
    d, mi, sec = float(mo.group(2)), float(mo.group(3)), float(mo.group(4))
    if mi >= 60.0 or sec >= 60.0:
        return None
    val = sign * (d + mi / 60.0 + sec / 3600.0)
    return val if -90.0 <= val <= 90.0 else None


def wcs_pointing(hdr: dict):
    """(ra_deg, dec_deg) from the raw TCS cards, or (None, None).

    (None, None) means write no WCS card at all.  CTYPE without CRVAL is not
    safe - readers default CRVAL to 0.0 and the field silently lands near the
    vernal equinox, which is precisely the bug this release fixes.
    """
    ra = ra_hours_to_deg(hval(hdr, "RA", ""))
    dec = dec_sex_to_deg(hval(hdr, "DEC", ""))
    if ra is None or dec is None:
        return None, None
    return ra, dec


def sees_sky(hdr: dict) -> bool:
    """Is an astrometric solution meaningful for this frame?

    Decided from IMAGETYP alone.  SHUTTER and EXPTIME look like corroboration
    but are not: the raw spec records that the AUX block can be sampled before
    the shutter opens, so SHUTTER='CLOSED' appears on real OBJECT frames.
    An unknown or missing IMAGETYP is treated as sky-bearing, because the cost
    of a wrong skip is silent and the cost of a wrong attempt is one flag.
    """
    return str(hval(hdr, "IMAGETYP", "")).strip().upper() not in NOSKY_IMAGETYP


def crpix_for(chip: str, amp: int):
    """Boresight position inside this amp's 1200x4616 array, 1-based.

    The first ACTIVE column of the array is mosaic column detsec()[0].  It
    sits at local x=1 on the right-overscan strips 1-4 but at local x=49 on
    the left-overscan strips 5-8, so those amps carry a +48 term.  Y has no
    in-array prescan or overscan - the middle rows are dropped by the slicer.
    """
    dx1, _dx2, dy1, _dy2 = detsec(chip, amp)
    x0loc = 1 if is_bias_right(amp) else OVERSCAN_X + 1
    return (BORESIGHT_X - dx1 + x0loc, BORESIGHT_Y - dy1 + 1)


def iraf_transforms(chip: str, amp: int):
    """(ltv1, ltv2, dtv1, dtv2) for the ds9/IRAF coordinate chain.

        image    = LTM x physical + LTV      physical = CCD column/row
        detector = DTM x physical + DTV      detector = mosaic pixel

    Every matrix is the identity: raw spec 4.3 requires each amp to be stored
    in ascending CCD order on both axes, so nothing is mirrored and the
    varying overscan side moves only the offset.
    """
    cx1, _cx2, cy1, _cy2 = ccdsec(amp)
    _rd, _rb, loc_data, _lb = raw_x_sections(chip, amp)
    return (float(loc_data[0] - cx1), float(1 - cy1),
            float(CHIP_X0[chip] - 1), float(CHIP_Y0[chip] - 1))


# --- Archon house-keeping ------------------------------------------------

def parse_pipe_list(txt, nslot: int, label: str = ""):
    """Split a pipe-delimited Cn_* card into exactly nslot floats.

    Returns (values, state) where values has length nslot with float or None
    entries and state is OK / PARTIAL / NC / UNKNOWN.  Never raises: a bad HK
    string must not cost us the pixels.
    """
    raw = "" if txt is None else str(txt).strip()
    if not raw:
        return [None] * nslot, "UNKNOWN"
    tokens = [t.strip() for t in raw.split("|")]
    if len(tokens) != nslot:
        # The slot count is a configuration discriminator - a guide frame has
        # 8 rails where science has 7, so a mismatch is worth saying out loud.
        _warn("%s: expected %d HK slots, found %d - the slot count is a "
              "camera-configuration discriminator" % (label or "HK", nslot, len(tokens)))
    vals = []
    for i in range(nslot):
        tok = tokens[i] if i < len(tokens) else ""
        vals.append(None if (not tok or tok.upper() in _NULLISH) else _num(tok))
    ngood = sum(1 for v in vals if v is not None)
    state = "OK" if ngood == nslot else ("NC" if ngood == 0 else "PARTIAL")
    return vals, state


def read_ctrl_hk(hdr: dict, n: int):
    """One controller's HK triple.

    Cn_* is identical in both pair members (raw spec 5.9 lists the six cards
    that differ, and these are not among them), so one header is enough.
    """
    temps, st = parse_pipe_list(hval(hdr, "C%d_TEMP" % n, ""),
                                len(CTRL_TEMP_SLOTS), "C%d_TEMP" % n)
    volts, sv = parse_pipe_list(hval(hdr, "C%d_VOLT" % n, ""),
                                len(CTRL_RAILS), "C%d_VOLT" % n)
    currs, sc = parse_pipe_list(hval(hdr, "C%d_CURR" % n, ""),
                                len(CTRL_RAILS), "C%d_CURR" % n)
    states = (st, sv, sc)
    if all(x == "UNKNOWN" for x in states):
        status = "UNKNOWN"                  # cards absent from this raw
    elif all(x == "OK" for x in states):
        status = "OK"
    elif all(x in ("NC", "UNKNOWN") for x in states):
        # All 24 slots NC together means the controller marked its STATUS
        # response VALID=0.  That is an invalid reading, NOT a sensor fault,
        # and downstream must not score it as hardware trouble.
        status = "NC"
    else:
        status = "PARTIAL"
    return {"temps": temps, "volts": volts, "currs": currs, "status": status}


# --- CCD output channel map (C-11) ---------------------------------------

def parse_chmap(mk_hdr: dict, nt_hdr: dict):
    """{(chip, amp): identity dict} from the raw CHMAP_LT/LB/RT/RB cards.

    CHMAP_* is one of the six cards raw spec 5.9 requires to DIFFER between
    the MK and NT members, so each chip is read from its own file's header.
    """
    chmap = {}
    for tag, hdr in (("MK", mk_hdr), ("NT", nt_hdr)):
        left, right = TAG_TO_CHIPS[tag]
        for chip, half in ((left, "L"), (right, "R")):
            port = "A" if half == "L" else "B"
            for amp in range(1, 17):
                cardname = "CHMAP_%s%s" % (half, "T" if amp <= 8 else "B")
                tokens = [t.strip() for t in
                          str(hval(hdr, cardname, "")).split(",") if t.strip()]
                idx = strip_id(amp) - 1
                tok = tokens[idx] if idx < len(tokens) else ""
                # <chip><A|D><nn>; the e2v image section comes from the token
                # itself, never hardcoded - it alternates per chip.
                # A token must be <chip><A|D><nn> for THIS chip with nn in
                # 1..16.  Any other form is not a channel we can name: a
                # cross-patched controller whose token names another CCD's
                # amplifier is the case that matters most, so it must fall all
                # the way back rather than publish a real-looking identity.
                sect = tok[1] if len(tok) >= 4 and tok[1] in ("A", "D") else ""
                num = HK_INT_SENTINEL
                if sect and tok[0] != chip:
                    sect = ""
                elif sect:
                    try:
                        n = int(tok[2:])
                    except (ValueError, IndexError):
                        n = -1
                    if 1 <= n <= 16:
                        num = n
                    else:
                        sect = ""
                chmap[(chip, amp)] = {
                    "CTRUNIT": tag,
                    "CCDPORT": port if sect else "?",
                    "CHANNAME": tok if sect else "UNKNOWN",
                    "CHANNUM": num,
                    "IMGSEC": ("%s-%s" % (sect, end_id(amp))) if sect else "UNKNOWN",
                    "CHMAPSRC": cardname,
                }
    return chmap


def validate_chmap(chmap: dict):
    """(ok, messages) comparing the raw CHMAP against the AmpID map.

    A miswired or re-configured controller otherwise yields correctly shaped,
    wrongly labelled amplifiers - and nothing downstream can tell.
    """
    bad = []
    for chip in CHIP_ORDER:
        for amp in range(1, 17):
            want = AMPID_MAP[(chip, amp)]
            got = chmap.get((chip, amp), {}).get("CHANNAME", "UNKNOWN")
            if got != want:
                bad.append("%s: raw CHMAP %s, expected %s"
                           % (extname_for(chip, amp), got, want))
    return (not bad), bad


# --- raw geometry cross-check (C-5 / C-13) -------------------------------

# raw spec 5.9: exactly these six cards may differ between the MK and NT
# members of a pair.  Everything else is required to be identical, which is
# what makes it safe for the converter to read HK and pointing from one file.
PAIR_MAY_DIFFER = ("DETID", "FILENAME", "CHMAP_LT", "CHMAP_LB", "CHMAP_RT", "CHMAP_RB")
PAIR_MUST_MATCH = ("EXPID", "DATE-OBS", "EXPTIME", "OBJECT", "IMAGETYP", "FILTER",
                   "RA", "DEC", "RADECSYS", "EQUINOX",
                   "CTRL1ID", "CTRL1SN", "CTRL2ID", "CTRL2SN",
                   "C1_TEMP", "C1_VOLT", "C1_CURR",
                   "C2_TEMP", "C2_VOLT", "C2_CURR", "HKUDATE", "CCDTEMP")


def check_raw_pair(mk_hdr: dict, nt_hdr: dict):
    """Messages for cards that must be identical across the pair but are not.

    The two files are written independently by two controllers.  The converter
    reads pointing and house-keeping from the MK member alone, which is only
    sound while this holds - so it is checked rather than assumed.
    """
    bad = []
    for key in PAIR_MUST_MATCH:
        a = str(hval(mk_hdr, key, "")).strip()
        b = str(hval(nt_hdr, key, "")).strip()
        if a != b:
            bad.append("%s differs: MK=%r NT=%r" % (key, a[:28], b[:28]))
    for key, want in (("DETID", ("MK", "NT")),):
        if (str(hval(mk_hdr, key, "")).strip() == str(hval(nt_hdr, key, "")).strip()
                and str(hval(mk_hdr, key, "")).strip()):
            bad.append("%s is the same in both members; expected %s/%s"
                       % (key, want[0], want[1]))
    return bad


def check_raw_geometry(hdr: dict, path: Path):
    """Messages for every raw geometry declaration that contradicts us.

    This converter slices with hardcoded constants.  Before this check, a raw
    that declared a different tile width was sliced at the old offsets and
    produced a complete, plausible, wrong MEF without raising anything.
    """
    bad = []
    for key, want in sorted(RAW_GEOM_EXPECT.items()):
        got = _num(hval(hdr, key, ""))
        if got is None:
            continue                     # absent: nothing declared to compare
        if int(got) != int(want):
            bad.append("%s: %s=%d but this converter assumes %d"
                       % (path.name, key, int(got), int(want)))
    for key, (want, tol) in sorted(RAW_GEOM_EXPECT_FLOAT.items()):
        got = _num(hval(hdr, key, ""))
        if got is None:
            continue
        if abs(got - want) > tol:
            bad.append("%s: %s=%g but this converter assumes %g"
                       % (path.name, key, got, want))
    detid = str(hval(hdr, "DETID", "")).strip()
    want_detid = "NT" if path.name.endswith(".NT.fits") else "MK"
    if detid and detid != want_detid:
        bad.append("%s: DETID=%s, expected %s" % (path.name, detid, want_detid))
    return bad


def jd_from_datetime(d: dt.datetime) -> float:
    year, month = d.year, d.month
    day = d.day + (d.hour + (d.minute + (d.second + d.microsecond/1e6)/60.0)/60.0)/24.0
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return int(365.25*(year+4716)) + int(30.6001*(month+1)) + day + b - 1524.5


def primary_cards(mk_hdr: dict, mk_path: Path, nt_path: Path,
                  out_path: Path, pointing=(None, None), sky: bool = True,
                  chmap_ok: bool = True,
                  chmap_msgs=(), geom_msgs=(), pair_msgs=(), ampchar_name: str = ""):
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "")
    date_obs = str(hval(mk_hdr, "DATE-OBS", now))
    try:
        if "T" in date_obs:
            jd_obs = jd_from_datetime(dt.datetime.fromisoformat(date_obs.replace("Z", "+00:00")))
        else:
            jd_obs = jd_from_datetime(dt.datetime.now(dt.timezone.utc))
    except Exception:
        jd_obs = jd_from_datetime(dt.datetime.now(dt.timezone.utc))
    mjd_obs = jd_obs - 2400000.5
    ra_deg, dec_deg = pointing
    wcs_written = bool(sky and ra_deg is not None and dec_deg is not None)
    exptime = fnum(mk_hdr, "EXPTIME", 0.0)

    def v(k, d=""):
        return hval(mk_hdr, k, d)

    cards = [
        card("SIMPLE", True, "FITS standard"),
        card("BITPIX", 16, "bits per pixel in image extensions"),
        card("NAXIS", 0, "primary HDU has no image array"),
        card("EXTEND", True, "file contains extensions"),
        # "where this file was made".  The MEF is a KASI pipeline product
        # even when the raw came from a mountain, so this is a constant and
        # not a copy of the raw's ORIGIN.
        card("ORIGIN", "KASI", "FITS file originator"),
        card("DATE", now, "date FITS file was generated"),
        card("CREATOR", f"kmt_ceu_l0amp_mknt2mef_{SOFTWARE_VERSION}", "MEF creation program"),
        card("COMMENT", "KMT-CEU L0 Raw 64-amplifier MEF product"),
        card("COMMENT", "Primary raw archive/product for amplifier-level calibration"),
        card("BUNIT", v("BUNIT", "ADU"), "units of image pixel values"),
        card("DATAPROD", "L0_AMP", "data product type"),
        card("PRODVER", PRODUCT_VERSION, "product format version"),
        card("GEOMVER", GEOMETRY_VERSION, "geometry definition version"),

        card("COMMENT", "Raw Archon file provenance"),
        card("RAWGROUP", "MKNT", "raw Archon file grouping convention"),
        card("CHIPLIST", "M,K,N,T", "official science chip order"),
        card("MKFILE", mk_path.name, "source MK raw FITS file"),
        card("NTFILE", nt_path.name, "source NT raw FITS file"),
        card("NUMFILES", 2, "number of raw files used"),
        card("EXPID", v("EXPID", ""), "exposure identifier from the ICS counter"),
        card("DETID", "MKNT", "raw detector pairs combined in this MEF"),
        card("DATASRC", v("DATASRC", "UNKNOWN"), "pixel data source type"),
        card("FPAID", v("FPAID", "UNKNOWN"), "focal plane assembly ID"),
        card("RAWNAX1", RAW_NAXIS1, "raw Archon image width"),
        card("RAWNAX2", RAW_NAXIS2, "raw Archon image height"),
        card("RAWXTILE", RAW_XTILE, "raw amp tile width"),
        card("AMPDATA", AMP_DATA_COLS, "active columns per amp tile"),
        card("OVERSCNX", OVERSCAN_X, "X overscan columns per amp tile"),
        card("PRESCANX", PRESCAN_X, "X prescan columns per amp tile"),
        card("MIDOVSCY", MIDDLE_OVERSCAN_Y, "middle Y overscan rows"),
        card("TOPROWS", ACTIVE_HALF_ROWS, "active TOP-half rows"),
        card("BOTROWS", ACTIVE_HALF_ROWS, "active BOT-half rows"),
        card("CHIPFLP", CHIPFLP, "no chip-dependent OSU-style flip applied"),

        card("COMMENT", "Detector and camera information"),
        card("DETECTOR", v("DETECTOR", "e2v CCD290-99"), "detector model"),
        card("CAMNAME", "KMT-CEU", "camera electronics upgrade system"),
        card("CAMVER", "CEU-v2.1", "camera/electronics version"),
        card("DETTYPE", "SCIENCE", "science detector data product"),
        card("NCCD", 4, "number of science CCDs"),
        card("NAMPS", 64, "total amplifiers"),
        card("AMPPCD", 16, "amplifiers per CCD"),
        card("NSTRIP", 8, "vertical strips per CCD"),
        card("NEND", 2, "top and bottom readout ends per strip"),
        card("CCDXBIN", v("CCDXBIN", 1), "CCD X-axis binning factor"),
        card("CCDYBIN", v("CCDYBIN", 1), "CCD Y-axis binning factor"),
        card("READMODE", "64AMP", "64-amplifier readout mode"),
        card("READARCH", "8STRIPx2END", "8 strips read from top and bottom"),
        card("PIXSCALE", PIX_SCALE, "unbinned pixel scale [arcsec/pixel]"),
        card("PIXSIZE", PIX_SIZE, "unbinned pixel size [micron]"),
        card("DETSIZE", "[1:18892,1:19397]", "KMTNet mosaic size in pixels"),
        card("COLGAP", GAP_COLS, "horizontal inter-CCD gap in pixels"),
        card("ROWGAP", GAP_ROWS, "vertical inter-CCD gap in pixels"),

        card("COMMENT", "Observatory and exposure information"),
        card("OBSERVAT", v("OBSERVAT", ""), "observatory site"),
        card("SITEID", v("OBSERVAT", ""), "site identifier"),
        card("TELESCOP", v("TELESCOP", "KMTNet 1.6m"), "telescope name"),
        card("LATITUDE", v("LATITUDE", ""), "site latitude"),
        card("LONGITUD", v("LONGITUD", ""), "site longitude"),
        card("ELEVATIO", inum(mk_hdr, "ELEVATIO", HK_INT_SENTINEL), "site elevation [m]"),
        card("OBSERVER", v("OBSERVER", ""), "observer(s)"),
        card("OBJECT", v("OBJECT", ""), "name of object observed"),
        card("FIELDID", v("FIELDID", v("OBJECT", "")), "KMTNet field identifier"),
        card("PROJID", v("PROJID", ""), "project or observing program ID"),
        card("IMAGETYP", v("IMAGETYP", ""), "type of observation"),
        card("OBSTYPE", v("OBSTYPE", ""), "type of observation"),
        card("EXPTIME", exptime, "exposure time [s]"),
        # The new raw carries no DARKTIME; EXPTIME is the honest lower bound
        # and keeps the card floating-point either way.
        card("DARKTIME", fnum(mk_hdr, "DARKTIME", exptime), "cumulative dark time [s]"),
        card("LEDFLASH", fnum(mk_hdr, "LEDFLASH", 0.0), "projector LED flash [ms]"),
        card("TSHOPEN", v("TSHOPEN", ""), "shutter open time"),
        card("TSHSHUT", v("TSHSHUT", ""), "shutter close time"),
        card("FILENAME", out_path.name, "MEF filename"),
        # UNIQNAME retired with D-016/D-019: identity is FILENAME + EXPID.
        # Its raw source is gone, so the card could only ever be blank.

        card("COMMENT", "Instrument/electronics configuration"),
        card("INSTRUME", v("INSTRUME", "KMTS"), "instrument name"),
        card("CONTROLL", "STA ARCHON", "controller type"),
        card("NCTRL", 2, "number of science Archon controllers"),
        card("CTRL1ID", v("CTRL1ID", "UNKNOWN"), "science controller 1 ID"),
        card("CTRL1SN", v("CTRL1SN", "UNKNOWN"), "science controller 1 serial number"),
        card("CTRL1FW", v("CTRL1FW", "UNKNOWN"), "science controller 1 firmware"),
        card("CTRL2ID", v("CTRL2ID", "UNKNOWN"), "science controller 2 ID"),
        card("CTRL2SN", v("CTRL2SN", "UNKNOWN"), "science controller 2 serial number"),
        card("CTRL2FW", v("CTRL2FW", "UNKNOWN"), "science controller 2 firmware"),
        # The ACF config names are what the timing/bias/clock version strings
        # are attributed to, so without them the MEF cannot say how the CCDs
        # were actually clocked.
        card("CTRL1CFG", v("CTRL1CFG", "UNKNOWN"), "controller 1 Archon config name"),
        card("CTRL2CFG", v("CTRL2CFG", "UNKNOWN"), "controller 2 Archon config name"),
        card("ICSBUILD", v("ICSBUILD", "UNKNOWN"), "acquisition software version/build"),
        card("RDMODE", v("RDMODE", "UNKNOWN"), "controller readout mode setting"),
        card("WBTYPE", "STA Differential Board", "wall board type"),
        card("ELECSYS", "KMT-CEU", "electronics system"),
        card("SIGELEC", "STA_DIFF_VIDEO", "signal readout/video-chain electronics"),
        card("TIMCONF", "CEU_TIM_v1.0", "CCD clock and timing configuration"),
        card("CTRLVER", v("CTRLVER", "ARCHON-v1.0"), "controller system version"),
        card("TIMVER", v("TIMVER", "TIM-v1.0"), "timing script version"),
        card("XTALKVER", v("XTALKVER", "UNMEASURED"), "crosstalk model version"),
        card("XTALKCAL", False, "crosstalk coefficients are placeholders"),
        card("BIASVER", v("BIASVER", "BIAS-v1.0"), "bias configuration version"),
        card("CLKVER", v("CLKVER", "CLK-v1.0"), "clock configuration version"),
        card("PIPEVER", f"kmt_ceu_l0amp_mknt2mef-{SOFTWARE_VERSION}", "converter version"),
        card("REFVER", v("REFVER", "N/A"), "reference image version"),
        card("CATVER", v("CATVER", "N/A"), "catalog version"),

        card("COMMENT", "TCS pointing information"),
        card("TCSLINK", v("TCSLINK", ""), "TCS communications link status"),
        card("TCSARC", v("TCSARC", ""), "TCS auto recovery mode status"),
        card("TCSQDATE", v("TCSQDATE", ""), "UTC date/time of last TCS query"),
        card("TCSUDATE", v("TCSUDATE", ""), "UTC date/time of last TCS update"),
        card("TIMESYS", v("TIMESYS", "UTC"), "time system"),
        card("DATE-OBS", date_obs, "UTC date/time at start of observation"),
        card("MJD-OBS", mjd_obs, "modified Julian date at start"),
        card("JD", jd_obs, "Julian date at start"),
        # Was assembled from DATE-OBS's date part plus the retired TSHOPEN,
        # so the time part was empty; and across UTC midnight the two halves
        # came from different days.  DATE-OBS already carries milliseconds.
        card("UT", date_obs, "UTC timestamp at start of observation"),
        # RADECSYS is deprecated in the FITS standard, but mef_pipeline
        # matches it by literal name, so both spellings are written.
        card("RADECSYS", v("RADECSYS", "ICRS"), "telescope coordinate system"),
        card("RADESYS", v("RADECSYS", "ICRS"), "FITS-standard name for RADECSYS"),
        # No default.  '00:00:00.00' / '+00:00:00.0' is a syntactically valid
        # coordinate that nothing downstream can distinguish from a real
        # pointing - exactly the failure this release exists to remove.
        card("RA", v("RA"), "telescope RA") if str(v("RA")).strip() else None,
        card("DEC", v("DEC"), "telescope DEC") if str(v("DEC")).strip() else None,
        # Decimal pointing so nothing downstream has to re-parse sexagesimal
        # and re-make the negative-declination sign error.
        card("RA_DEG", ra_deg, "telescope RA [deg]") if ra_deg is not None else None,
        card("DEC_DEG", dec_deg, "telescope Dec [deg]") if dec_deg is not None else None,
        # EQUINOX must be floating point; the raw relays the string '2000.000'.
        card("EQUINOX", fnum(mk_hdr, "EQUINOX", 2000.0), "coordinate system equinox"),
        card("HA", v("HA", ""), "hour angle at start"),
        card("ST", v("ST", ""), "local sidereal time at start"),
        card("SECZ", v("SECZ", ""), "secant of zenith distance"),
        card("AIRMASS", fnum(mk_hdr, "SECZ"), "airmass = sec(ZD) at start")
            if fnum(mk_hdr, "SECZ") is not None else None,
        card("ALT", v("ALT", ""), "telescope altitude [deg]"),
        card("AZ", v("AZ", ""), "telescope azimuth [deg]"),
        card("TCSTIME", v("TCSTIME", ""), "TCS time system"),
        card("TCSDRIV", v("TCSDRIVE", v("TCSDRIV", "")), "telescope drive status"),
        card("TELMOVE", v("TELMOVE", ""), "telescope motion status"),

        card("COMMENT", "Seed WCS for the L1 Gaia astrometric fit"),
        card("COMMENT", "  Not a product WCS. It exists to give the L1 solver a"),
        card("COMMENT", "  starting point; positions must come from the solved"),
        card("COMMENT", "  L1 WCS (WCSSOLVE=T, WCSAPPRX=F, catalogue in WCSCAT)."),
        card("COMMENT", "  WCSSKY=F (BIAS/DARK/DOMEFLAT) means no sky was seen,"),
        card("COMMENT", "  so no seed is written and L1 skips astrometry - that"),
        card("COMMENT", "  is not a failed solution."),
        # The per-amp CRVAL/CRPIX/CD live on the extensions; these publish the
        # constants they are built from so a later astrometric solution can be
        # differenced against them without reading this source file.  They are
        # written only when a WCS was actually written, so the primary cannot
        # advertise a named WCS for a file that has none.
        card("WCSSKY", bool(sky), "frame sees sky; astrometry is applicable"),
        card("BOREPIXX", BORESIGHT_X, "boresight X in DETSIZE mosaic pixels")
            if wcs_written else None,
        card("BOREPIXY", BORESIGHT_Y, "boresight Y in DETSIZE mosaic pixels")
            if wcs_written else None,
        card("WCSNAME", WCSNAME_L0, "seed WCS for the L1 Gaia fit")
            if wcs_written else None,
        card("WCSOMIT", not wcs_written,
             "no seed WCS: frame sees no sky" if not sky
             else "no seed WCS: TCS pointing unusable"),
        card("WCSAPPRX", True, "WCS is approximate; L1 astrometry pending")
            if wcs_written else None,
        # Never T at L0 - no CEU frame has ever been fitted to stars here.
        # The L1 Gaia step is what sets this to T.
        card("WCSSOLVE", False, "no astrometric solution attempted yet"),
        card("CHMAPOK", bool(chmap_ok), "raw CHMAP agrees with the AmpID map"),
        card("AMPIDMAP", AMPID_MAP_VERSION, "channel-to-AmpID map revision"),

        card("COMMENT", "Filter/shutter, FSA, focus, dome, and thermal info"),
        card("AUXLINK", v("AUXLINK", ""), "AUX control system communication status"),
        card("AUXARC", v("AUXARC", ""), "AUX link auto recovery status"),
        card("AUXQDATE", v("AUXQDATE", ""), "UTC date/time of last AUX query"),
        card("AUXUDATE", v("AUXUDATE", ""), "UTC date/time of last AUX update"),
        card("FSSTAT", v("FSSTAT", ""), "filter-shutter subsystem status"),
        card("FILTOP", v("FILTOP", ""), "filter operational status"),
        card("FILNUM", v("FILNUM", ""), "filter selector position number"),
        card("FILTER", v("FILTER", ""), "filter name in beam"),
        card("SHUTOP", v("SHUTOP", ""), "shutter operational status"),
        card("SHUTTER", v("SHUTTER", ""), "shutter position"),
        card("FSATEMP", v("FSATEMP", ""), "FSA internal temperature [C]"),
        card("FSAHUM", v("FSAHUM", ""), "FSA internal relative humidity [%]"),
        card("FSADEW", v("FSADEW", ""), "FSA internal dew point [C]"),
        card("FSAALRM", v("FSAALRM", ""), "FSA environmental alarm status"),
        card("FASTAT", v("FASTAT", ""), "focus actuator subsystem status"),
        card("FAFOCUS", v("FAFOCUS", ""), "focus position offset [mm]"),
        card("FATILTNS", v("FATILTNS", ""), "focus tilt NS offset [arcsec]"),
        card("FATILTEW", v("FATILTEW", ""), "focus tilt EW offset [arcsec]"),
        card("FAPOSS", v("FAPOSS", ""), "south focus actuator position [mm]"),
        card("FALIMS", v("FALIMS", ""), "south focus actuator limit status"),
        card("FAPOSE", v("FAPOSE", ""), "east focus actuator position [mm]"),
        card("FALIME", v("FALIME", ""), "east focus actuator limit status"),
        card("FAPOSW", v("FAPOSW", ""), "west focus actuator position [mm]"),
        card("FALIMW", v("FALIMW", ""), "west focus actuator limit status"),
        card("DSSTAT", v("DSSTAT", ""), "dome shutter status"),
        card("DSUP", v("DSUP", ""), "upper dome shutter position"),
        card("DSLW", v("DSLW", ""), "lower dome shutter position"),
        card("DSSAF", v("DSSAF", ""), "dome safety status"),
        card("DSAUTO", v("DSAUTO", ""), "dome auto sync status"),
        card("DSALT", v("DSALT", ""), "dome slit altitude [deg]"),
        card("DSAZ", v("DSAZ", ""), "dome slit azimuth [deg]"),
        card("DSTELALT", v("DSTELALT", ""), "telescope altitude used by dome [deg]"),
        card("DSTELAZ", v("DSTELAZ", ""), "telescope azimuth used by dome [deg]"),
        card("DALTERR", v("DALTERR", ""), "dome-telescope altitude difference [deg]"),
        card("DAZERR", v("DAZERR", ""), "dome-telescope azimuth difference [deg]"),
        card("MCSTAT", v("MCSTAT", ""), "mirror cover status"),
        card("MCPOS", v("MCPOS", ""), "mirror cover position [%]"),
        card("CHSTAT", v("CHSTAT", ""), "chiller status"),
        card("ENSTAT", v("ENSTAT", ""), "environmental control system status"),
        card("ENFAN", v("ENFAN", ""), "environmental system fan state"),
        # HK block.  Every reading is relayed as the raw's string, which is
        # deliberate (raw spec 5.0): the pass-through is what keeps the type
        # uniform across the archive.  Out-of-range and unconnected readings
        # come through as they are and must NOT be folded into a sentinel -
        # hiding them would disguise, say, heater overheating as a dead
        # sensor.  '-999.99' means the device gave no value; DEWPRES uses
        # '9.99e-9', which during a science exposure is the ion gauge being
        # switched off on purpose, not a fault.
        card("HKUDATE", v("HKUDATE", ""), "UTC time of oldest HK sample"),
        card("CCDTEMP", v("CCDTEMP", ""), "CCD temperature [C]"),
        card("DEWPRES", v("DEWPRES", ""), "dewar pressure [torr]"),
        card("PT30N1", v("PT30N1", ""), "cooler temperature sensor 1 [C]"),
        card("PT30N2", v("PT30N2", ""), "cooler temperature sensor 2 [C]"),
        card("CHARCOAL", v("CHARCOAL", ""), "charcoal getter temperature [C]"),
        card("DMPTEMP", v("DMPTEMP", ""), "DMP temperature [C]"),
        card("WALLBRD", v("WALLBRD", ""), "wall board temperature [C]"),
        # Radionode sensor: its sample time is NOT in HKUDATE and can be up
        # to 600 s older.
        card("HEBOX", v("HEBOX", ""), "HE box internal temperature [C]"),
        card("HTREN", v("HTREN", ""), "dewar heater enable state"),
        card("HTRSET", v("HTRSET", ""), "dewar heater target temperature [C]"),
        card("HTROUT", v("HTROUT", ""), "dewar heater output voltage [V]"),
        card("HTRFORCE", v("HTRFORCE", ""), "dewar heater forced-output mode"),
        card("AIR_IN", v("AIR_IN", ""), "air inlet temperature [C]"),
        card("AIR_OUT", v("AIR_OUT", ""), "air outlet temperature [C]"),
        card("GLYC_IN", v("GLYC_IN", ""), "glycol inlet temperature [C]"),
        card("GLYC_OUT", v("GLYC_OUT", ""), "glycol outlet temperature [C]"),
        card("CHKIMG", v("CHKIMG", ""), "image check status"),
        card("CHKIMG_C", v("CHKIMG_C", ""), "image check comment"),
    ]

    # Environment sensors and the raw controller telemetry strings.  The
    # Cn_* cards are also parsed into VOLTINFO/TELEMETRY, but the strings are
    # kept verbatim as well: the slot ordering is a spec table, so a future
    # reader who disagrees with our decoding can still redo it from here.
    for i in range(1, 8):
        cards.append(card("ENS%d" % i, v("ENS%d" % i, ""),
                          "environment sensor %d [C or %%RH]" % i))
    for n in (1, 2):
        cards.append(card("C%d_TEMP" % n, v("C%d_TEMP" % n, ""),
                          "Ctrl-%d module temperatures [C]" % n))
        cards.append(card("C%d_VOLT" % n, v("C%d_VOLT" % n, ""),
                          "Ctrl-%d rail voltages [V]" % n))
        cards.append(card("C%d_CURR" % n, v("C%d_CURR" % n, ""),
                          "Ctrl-%d rail currents [A]" % n))
    cards.append(card("RAILREF", RAILREF, "rail/module slot order reference"))

    if ampchar_name:
        cards.append(card("AMPCHAR", ampchar_name[:40],
                          "amp characterization table stamped into headers"))

    # Provenance trail.  HISTORY, not COMMENT: these are statements about how
    # the file came to be, and they must survive being read back.
    cards.append(card("HISTORY", "L0 MEF built by %s %s"
                      % (Path(__file__).name, SOFTWARE_VERSION)))
    cards.append(card("HISTORY", "  from %s" % mk_path.name))
    cards.append(card("HISTORY", "  and  %s" % nt_path.name))
    cards.append(card("HISTORY", "  at %s UTC" % now))
    # Say what this file actually is. The unconditional version claimed a
    # TCS-pointing seed on BIAS/DARK/DOMEFLAT products that carry no WCS at
    # all - a plausible-but-false statement of exactly the kind D-023 exists
    # to remove.
    if wcs_written:
        cards.append(card("HISTORY", "WCS is the TCS-pointing seed for the L1 "
                                     "Gaia fit (WCSAPPRX=T,"))
        cards.append(card("HISTORY", "  WCSSOLVE=F); it has not been fitted to "
                                     "stars at this stage"))
    elif not sky:
        cards.append(card("HISTORY", "No sky WCS: IMAGETYP=%s sees no sky, so the"
                          % (str(v("IMAGETYP", "")).strip() or "?")))
        cards.append(card("HISTORY", "  L1 Gaia fit does not apply (WCSSKY=F)"))
    else:
        cards.append(card("HISTORY", "No sky WCS: the TCS pointing did not parse,"))
        cards.append(card("HISTORY", "  so every WCS card was omitted (WCSOMIT=T)"))
    # One message per card, split so the value we actually assumed survives:
    # card() truncates the finished line at 80, so a prefix plus a long
    # message silently loses its tail - which is the only number a reader
    # needs.
    for msg in list(geom_msgs)[:8]:
        cards.append(card("HISTORY", "RAW GEOMETRY MISMATCH"))
        for chunk in (msg[i:i + 68] for i in range(0, min(len(msg), 204), 68)):
            cards.append(card("HISTORY", "  " + chunk))
    for msg in list(pair_msgs)[:8]:
        cards.append(card("HISTORY", "RAW PAIR MISMATCH"))
        for chunk in (msg[i:i + 68] for i in range(0, min(len(msg), 204), 68)):
            cards.append(card("HISTORY", "  " + chunk))
    if not chmap_ok:
        cards.append(card("HISTORY", "CHMAP does not match %s:" % AMPID_MAP_VERSION))
        for msg in list(chmap_msgs)[:8]:
            cards.append(card("HISTORY", "  %s" % msg[:62]))
        if len(chmap_msgs) > 8:
            cards.append(card("HISTORY", "  ... and %d more"
                              % (len(chmap_msgs) - 8)))

    # Cards built conditionally above are None when their source did not
    # parse; dropping them is deliberate - an absent card is honest, a
    # defaulted one is a plausible wrong value (raw spec 5.0).
    return [c for c in cards if c is not None]


def load_ampchar(path) -> dict:
    """amp characterization CSV (cam_char/results schema) -> {EXTNAME: row}.
    Values <= 0 or missing keep the default/placeholder."""
    import csv
    table = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = str(row.get("EXTNAME", "")).strip()
            if key:
                table[key] = row
    return table


def _ac_val(ac: dict, key: str, default, cast=float):
    # Operator-supplied CSV is the other way a non-finite number can reach a
    # card: 'inf' survives float(), passes `v > 0`, and is then written as a
    # bare INF token that no FITS reader will parse (or blows up int()).
    raw = _num(ac.get(key, ""))
    if raw is None:
        return default
    try:
        v = cast(raw)
    except (TypeError, ValueError, OverflowError):
        return default
    return v if v > 0 else default


def amp_header(chip: str, amp: int, chip_hdr: dict, raw_file: str,
               chmap: dict, pointing=(None, None), sky: bool = True,
               ampchar: dict | None = None):
    """Header cards for one amplifier extension.

    chip_hdr is the header of the raw file that actually CONTAINS this chip.
    It used to always be the MK header, which silently stamped N and T amps
    with M/K electronics identity - CHMAP_* is one of the six cards raw spec
    5.9 requires to differ between the pair members.
    """
    ext = extname_for(chip, amp)
    ac = (ampchar or {}).get(ext, {})
    gain = _ac_val(ac, "GAIN", 0.0)
    rdnoise = _ac_val(ac, "RDNOISE", 0.0)
    saturat = _ac_val(ac, "SATURAT", 62000, int)
    linmax = _ac_val(ac, "LINMAX", 58000, int)
    raw_data, raw_bias, loc_data, loc_bias = raw_x_sections(chip, amp)
    ry1, ry2 = raw_y_section(amp)
    cx1, cx2, cy1, cy2 = ccdsec(amp)
    dx1, dx2, dy1, dy2 = detsec(chip, amp)
    global_amp = AMP_BASE[chip] + amp
    read_dir = "-Y" if amp <= 8 else "+Y"
    ident = chmap.get((chip, amp), {})
    ltv1, ltv2, dtv1, dtv2 = iraf_transforms(chip, amp)
    # ONE tangent point for the whole mosaic, taken from the MK member and
    # passed in.  Reading it per chip would let an MK/NT pointing disagreement
    # split the focal plane across two tangent points with nothing to show for
    # it - the M/K half and the N/T half would simply be somewhere else.
    ra_deg, dec_deg = pointing
    cp1, cp2 = crpix_for(chip, amp)

    def v(k, d=""):
        return hval(chip_hdr, k, d)

    cards = [
        card("XTENSION", "IMAGE", "image extension"),
        card("BITPIX", 16, "array data type"),
        card("NAXIS", 2, "number of array dimensions"),
        card("NAXIS1", RAW_XTILE, "amp image width including overscan"),
        card("NAXIS2", ACTIVE_HALF_ROWS, "amp image active rows"),
        card("PCOUNT", 0),
        card("GCOUNT", 1),
        card("BZERO", hval(chip_hdr, "BZERO", 32768), "unsigned 16-bit zero point"),
        card("BSCALE", hval(chip_hdr, "BSCALE", 1), "default scale"),
        card("BUNIT", v("BUNIT", "ADU"), "pixel unit"),
        card("EXTNAME", ext, "amplifier image extension"),
        card("EXTTYPE", "AMP_RAW", "L0 amplifier raw image"),
        card("REALDATA", True, "actual amplifier data from Archon raw"),
        card("DATAPROD", "L0_AMP", "data product type"),
        card("CHIPID", chip, "CCD identifier"),
        card("CCDNAME", f"KMTNet CCD {chip}", "CCD name"),
        card("AMPID", global_amp, "global amplifier ID"),
        card("AMPSEQ", amp, "amplifier sequence within CCD"),
        card("STRIPID", strip_id(amp), "vertical strip ID"),
        card("ENDID", end_id(amp), "readout end ID"),
        card("AMPNAME", ext, "amplifier name"),
        card("RAWFILE", raw_file, "source raw FITS file"),
        card("CTRLID", 1 if chip in ("M", "K") else 2, "science controller ID"),
        # Electronics identity, read from the raw CHMAP_* cards rather than
        # guessed from the amp index.  MODULE/CHANNEL used to be
        # 1+((amp-1)//8) and 1+((amp-1)%8), which matches no real wiring: the
        # CCD output channels run 1-16 per chip and the TOP/BOT halves take
        # opposite ends on different chips.
        card("CTRUNIT", ident.get("CTRUNIT", "??"), "raw controller unit"),
        card("CCDPORT", ident.get("CCDPORT", "?"), "controller port feeding this CCD"),
        card("CHANNAME", ident.get("CHANNAME", "UNKNOWN"), "CCD output channel token"),
        card("CHANNUM", ident.get("CHANNUM", HK_INT_SENTINEL), "CCD output channel number"),
        card("IMGSEC", ident.get("IMGSEC", "UNKNOWN"), "e2v image section and readout end"),
        card("CHMAPSRC", ident.get("CHMAPSRC", "UNKNOWN"), "raw card this identity came from"),
        card("MODULE", {"A": 1, "B": 2}.get(ident.get("CCDPORT"), HK_INT_SENTINEL),
             "controller port index"),
        card("CHANNEL", ident.get("CHANNUM", HK_INT_SENTINEL), "CCD output channel number"),
        card("CHIPFLP", CHIPFLP, "no chip-dependent OSU-style flip applied"),
        card("STRIPDIR", STRIPDIR, "strip number direction in CEU L0 packing"),
        card("READDIR", read_dir, "physical readout direction placeholder"),
        card("CCDSUM", "1 1", "on-chip binning factors"),
        card("CCDSEC", fmtsec(cx1, cx2, cy1, cy2), "amplifier section in CCD coords"),
        card("AMPSEC", fmtsec(cx1, cx2, cy1, cy2), "amplifier section in CCD coords"),
        card("DETSEC", fmtsec(dx1, dx2, dy1, dy2), "amplifier coords on detector mosaic"),
        card("RAWDATA", fmtsec(raw_data[0], raw_data[1], ry1, ry2), "source raw data section"),
        card("RAWBIAS", fmtsec(raw_bias[0], raw_bias[1], ry1, ry2), "source raw overscan section"),
        card("DATASEC", fmtsec(loc_data[0], loc_data[1], 1, ACTIVE_HALF_ROWS), "active data section"),
        card("PRESEC", "[1:0,1:4616]", "no prescan in Archon raw"),
        card("BIASSEC", fmtsec(loc_bias[0], loc_bias[1], 1, ACTIVE_HALF_ROWS), "local overscan section"),
        card("TRIMSEC", fmtsec(loc_data[0], loc_data[1], 1, ACTIVE_HALF_ROWS), "trimmed data section"),
        card("RAWNAX1", RAW_NAXIS1, "source raw image width"),
        card("RAWNAX2", RAW_NAXIS2, "source raw image height"),
        card("RAWXTILE", RAW_XTILE, "raw amp tile width"),
        card("AMPDATA", AMP_DATA_COLS, "active columns per amp tile"),
        card("OVERSCNX", OVERSCAN_X, "X overscan columns per amp tile"),
        card("PRESCANX", PRESCAN_X, "X prescan columns per amp tile"),
        card("MIDOVSCY", MIDDLE_OVERSCAN_Y, "middle Y overscan rows ignored"),
        card("GAIN", gain, "amp gain [e-/ADU] (measured)" if gain > 0
             else "gain placeholder [e-/ADU]"),
        card("RDNOISE", rdnoise, "read noise [e-] (measured)" if rdnoise > 0
             else "read noise placeholder [e-]"),
        card("SATURAT", saturat, "saturation level [ADU] (measured)"
             if _ac_val(ac, "SATURAT", 0, int) > 0
             else "saturation level placeholder [ADU]"),
        card("LINMAX", linmax, "linearity maximum [ADU] (measured)"
             if _ac_val(ac, "LINMAX", 0, int) > 0
             else "linearity maximum placeholder [ADU]"),
        card("FILTER", v("FILTER", ""), "filter name in beam"),
        card("PROJID", v("PROJID", ""), "project ID"),
        card("IMAGETYP", v("IMAGETYP", ""), "type of observation"),
        card("OBJECT", v("OBJECT", ""), "object name"),
        card("OBSTYPE", v("OBSTYPE", ""), "type of observation"),
        # Same rule as the primary: no default. A syntactically valid
        # '00:00:00.00' is indistinguishable from a real pointing.
        card("RA", v("RA"), "telescope RA") if str(v("RA")).strip() else None,
        card("DEC", v("DEC"), "telescope DEC") if str(v("DEC")).strip() else None,
        card("HA", v("HA", ""), "hour angle"),
        card("ST", v("ST", ""), "local sidereal time"),
        card("SECZ", v("SECZ", ""), "airmass"),
        card("ALT", v("ALT", ""), "telescope altitude [deg]"),
        card("AZ", v("AZ", ""), "telescope azimuth [deg]"),
        # Same fix as the primary: the DATE-OBS-date + TSHOPEN-time assembly
        # left the time part blank and took its two halves from different days
        # across UTC midnight.
        card("UT", v("DATE-OBS", ""), "UTC timestamp at start of observation"),
        card("AIRMASS", fnum(chip_hdr, "SECZ"), "airmass = sec(ZD) at start")
            if fnum(chip_hdr, "SECZ") is not None else None,

        # IRAF/ds9 coordinate chain, so ds9 "physical" reads out as the CCD
        # column/row and "detector" as the mosaic pixel:
        #     image    = LTM x physical + LTV
        #     detector = DTM x physical + DTV
        # Every matrix is the identity - raw spec 4.3 requires each amp to be
        # stored in ascending CCD order on both axes, so the varying overscan
        # side moves the offset and mirrors nothing.
        card("LTV1", ltv1, "CCD to image transform (x)"),
        card("LTV2", ltv2, "CCD to image transform (y; TOP half shift)"),
        card("LTM1_1", 1.0, "CCD to image transform"),
        card("LTM1_2", 0.0, "CCD to image transform"),
        card("LTM2_1", 0.0, "CCD to image transform"),
        card("LTM2_2", 1.0, "CCD to image transform"),
        card("ATV1", 0.0, "CCD to amplifier transform"),
        card("ATV2", 0.0, "CCD to amplifier transform"),
        card("ATM1_1", 1.0, "CCD to amplifier transform"),
        card("ATM1_2", 0.0, "CCD to amplifier transform"),
        card("ATM2_1", 0.0, "CCD to amplifier transform"),
        card("ATM2_2", 1.0, "CCD to amplifier transform"),
        card("DTV1", dtv1, "CCD to detector mosaic transform (x)"),
        card("DTV2", dtv2, "CCD to detector mosaic transform (y)"),
        card("DTM1_1", 1.0, "CCD to detector mosaic transform"),
        card("DTM1_2", 0.0, "CCD to detector mosaic transform"),
        card("DTM2_1", 0.0, "CCD to detector mosaic transform"),
        card("DTM2_2", 1.0, "CCD to detector mosaic transform"),
    ]

    # Approximate sky WCS.  The tangent point is the telescope boresight and
    # is therefore IDENTICAL on all 64 extensions; CRPIX carries the whole
    # per-amp offset.  That is what the operational KMTNet WCS does.
    #
    # CD is identical on all 64 amps too.  It is tempting to flip its signs
    # per amp because the serial readout direction changes at the strip 4/5
    # boundary, the parallel direction changes between the TOP and BOT
    # halves, and the e2v image section (A/D) alternates per chip - but none
    # of that reaches the stored pixel order: raw spec 4.3 requires the raw
    # frame to be written in ascending CCD coordinate on both axes for every
    # amp, and the K/N 180-degree mounting is already absorbed by the
    # channel-to-tile ordering.  Flipping CD here would break 32 of 64 amps.
    #
    # If the pointing did not parse we write NO WCS card at all.  CTYPE
    # without CRVAL is worse than nothing: readers default CRVAL to 0.0 and
    # the field lands near the vernal equinox with no warning.
    if sky and ra_deg is not None and dec_deg is not None:
        cards += [
            card("WCSAXES", 2, "number of WCS axes"),
            card("CTYPE1", "RA---TAN", "RA, gnomonic (TAN) projection"),
            card("CTYPE2", "DEC--TAN", "Dec, gnomonic (TAN) projection"),
            card("CUNIT1", "deg", "angle unit of axis 1"),
            card("CUNIT2", "deg", "angle unit of axis 2"),
            card("CRVAL1", ra_deg, "RA of tangent point = boresight [deg]"),
            card("CRVAL2", dec_deg, "Dec of tangent point = boresight [deg]"),
            card("CRPIX1", cp1, "boresight X in this amp array [px]"),
            card("CRPIX2", cp2, "boresight Y in this amp array [px]"),
            card("CD1_1", -CD_SCALE, "deg/px, +x = -RA (East left)"),
            card("CD1_2", 0.0, "no rotation/skew in the L0 approximate WCS"),
            card("CD2_1", 0.0, "no rotation/skew in the L0 approximate WCS"),
            card("CD2_2", CD_SCALE, "deg/px, +y = +Dec (North up)"),
            # Frame relayed from the raw, not hardcoded: CRVAL comes from the
            # raw RA/DEC, so it must carry the frame the raw declared for them.
            # RADECSYS is the deprecated spelling but mef_pipeline copies it by
            # literal name into the CCD-level WCS, so both are written here as
            # well as in the primary.
            card("RADECSYS", v("RADECSYS", "ICRS"), "telescope coordinate system"),
            card("RADESYS", v("RADECSYS", "ICRS"), "reference frame of CRVAL1/CRVAL2"),
            card("EQUINOX", fnum(chip_hdr, "EQUINOX", 2000.0), "coordinate system equinox"),
            card("WCSNAME", WCSNAME_L0, "seed WCS for the L1 Gaia fit"),
            # Same two flags the L1 astrometric step reads and then flips, so
            # the state travels in ONE vocabulary from L0 to L1 rather than
            # each stage inventing its own.
            card("WCSAPPRX", True, "WCS is approximate; L1 astrometry pending"),
            card("WCSSOLVE", False, "no astrometric solution attempted yet"),
            card("WCSDIM", 2, "coordinate system dimensionality"),
        ]
    else:
        # Every WCS card goes, WCSDIM included.  The MEF keyword spec lists
        # WCSDIM among the required amp-extension WCS set, but a lone
        # dimensionality card describing a WCS that is not there is worse than
        # its absence; WCSOMIT makes the deviation machine-detectable.
        # WCSAPPRX is not written here: it says "the WCS present is
        # approximate", and there is no WCS present to describe.
        cards += [
            card("WCSOMIT", True,
                 "no seed WCS: frame sees no sky" if not sky
                 else "no seed WCS: TCS pointing unusable"),
            card("WCSSOLVE", False, "no astrometric solution attempted yet"),
        ]
    cards.append(card("WCSSKY", bool(sky),
                      "frame sees sky; astrometry is applicable"))
    return [c for c in cards if c is not None]


def bintable_bytes(extname: str, columns, rows, extra_cards=None):
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
        cards.extend(c for c in extra_cards if c is not None)
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
                enc = s.encode("ascii", errors="replace")
                if len(enc) > n:
                    # A truncated sentinel reads like real data and silently
                    # disagrees with the same value in the extension header.
                    _warn("%s.%s: value %r truncated to %d characters"
                          % (extname, name, s, n))
                data.extend(enc[:n].ljust(n, b" "))
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
    return hdu_bytes(cards, bytes(data))


def ampinfo_rows(mk_path: Path, nt_path: Path, chmap: dict,
                 wcs_written: bool = True, ampchar: dict | None = None):
    rows = []
    rawfile_by_chip = {"M": mk_path.name, "K": mk_path.name, "N": nt_path.name, "T": nt_path.name}
    for chip in CHIP_ORDER:
        for amp in range(1, 17):
            ext = extname_for(chip, amp)
            ac = (ampchar or {}).get(ext, {})
            raw_data, raw_bias, loc_data, loc_bias = raw_x_sections(chip, amp)
            ry1, ry2 = raw_y_section(amp)
            cx1, cx2, cy1, cy2 = ccdsec(amp)
            dx1, dx2, dy1, dy2 = detsec(chip, amp)
            ident = chmap.get((chip, amp), {})
            ltv1, ltv2, dtv1, dtv2 = iraf_transforms(chip, amp)
            # CRPIX is the boresight position in this amp's frame. With no
            # seed WCS there is no boresight - the primary withholds
            # BOREPIXX/BOREPIXY and no amp header carries CRVAL - so a number
            # here would be a reference pixel pointing at nothing, and a
            # consumer building a WCS from AMPINFO alone would pair it with a
            # defaulted CRVAL=0. That is the failure this release removed.
            # LTV/DTV stay: they are detector geometry, true for any frame.
            cp1, cp2 = crpix_for(chip, amp) if wcs_written else (
                HK_REAL_SENTINEL, HK_REAL_SENTINEL)
            rows.append({
                "EXTNAME": ext,
                "AMPID": AMP_BASE[chip] + amp,
                "CHIPID": chip,
                "STRIPID": strip_id(amp),
                "ENDID": end_id(amp),
                "STRIPDIR": STRIPDIR,
                "AMPSEQ": amp,
                "AMPNAME": ext,
                "RAWFILE": rawfile_by_chip[chip],
                "CTRLID": 1 if chip in ("M", "K") else 2,
                "MODULE": {"A": 1, "B": 2}.get(ident.get("CCDPORT"), HK_INT_SENTINEL),
                "CHANNEL": ident.get("CHANNUM", HK_INT_SENTINEL),
                "CCDSEC": fmtsec(cx1, cx2, cy1, cy2),
                "AMPSEC": fmtsec(cx1, cx2, cy1, cy2),
                "DETSEC": fmtsec(dx1, dx2, dy1, dy2),
                "RAWDATA": fmtsec(raw_data[0], raw_data[1], ry1, ry2),
                "RAWBIAS": fmtsec(raw_bias[0], raw_bias[1], ry1, ry2),
                "DATASEC": fmtsec(loc_data[0], loc_data[1], 1, ACTIVE_HALF_ROWS),
                "PRESEC": "[1:0,1:4616]",
                "BIASSEC": fmtsec(loc_bias[0], loc_bias[1], 1, ACTIVE_HALF_ROWS),
                "TRIMSEC": fmtsec(loc_data[0], loc_data[1], 1, ACTIVE_HALF_ROWS),
                "CHIPFLP": CHIPFLP,
                "READDIR": "-Y" if amp <= 8 else "+Y",
                "GAIN": _ac_val(ac, "GAIN", 0.0),
                "RDNOISE": _ac_val(ac, "RDNOISE", 0.0),
                "SATLEVEL": _ac_val(ac, "SATURAT", 62000, int),
                "LINMAX": _ac_val(ac, "LINMAX", 58000, int),
                "RAWX0": raw_data[0], "RAWX1": raw_data[1],
                "RAWY0": ry1, "RAWY1": ry2,
                "AMPX0": cx1, "AMPX1": cx2, "AMPY0": cy1, "AMPY1": cy2,
                "DETX0": dx1, "DETX1": dx2, "DETY0": dy1, "DETY1": dy2,
                # Crosstalk group is now the real readout grouping the raw
                # declares - one controller port, 16 CCD output channels -
                # instead of the invented C<n>M<n> index.
                "XTALKGROUP": "%s-%s" % (ident.get("CTRUNIT", "??"),
                                         ident.get("CCDPORT", "?")),
                "CHANNAME": ident.get("CHANNAME", "UNKNOWN"),
                "CHANNUM": ident.get("CHANNUM", HK_INT_SENTINEL),
                "CCDPORT": ident.get("CCDPORT", "?"),
                "IMGSEC": ident.get("IMGSEC", "UNKNOWN"),
                "CTRUNIT": ident.get("CTRUNIT", "??"),  # noqa: E501
                "CHMAPSRC": ident.get("CHMAPSRC", "UNKNOWN"),
                "CRPIX1": cp1, "CRPIX2": cp2,
                "LTV1": ltv1, "LTV2": ltv2,
                "DTV1": dtv1, "DTV2": dtv2,
            })
    return rows


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
        # Appended, so every existing column keeps its index.
        # Widths hold the FALLBACKS ('UNKNOWN'), not just the good values -
        # a truncated sentinel reads like data and silently disagrees with the
        # same field in the extension header.
        ("CHANNAME", "8A", ""), ("CHANNUM", "I", ""), ("CCDPORT", "2A", ""),
        ("IMGSEC", "8A", ""), ("CTRUNIT", "2A", ""), ("CHMAPSRC", "8A", ""),
        ("CRPIX1", "D", "pixel"), ("CRPIX2", "D", "pixel"),
        ("LTV1", "D", "pixel"), ("LTV2", "D", "pixel"),
        ("DTV1", "D", "pixel"), ("DTV2", "D", "pixel"),
    ]
    xtalk_cols = [
        ("SOURCE_AMP", "I", ""), ("TARGET_AMP", "I", ""), ("XTALK_COEF", "D", ""),
        ("XTALK_ERROR", "D", ""), ("XTALK_VERSION", "16A", ""), ("MEASURE_DATE", "19A", "UTC"), ("STATUS", "12A", ""),
    ]
    volt_cols = [("VOLTNAME", "16A", ""), ("SETPOINT", "E", ""), ("MEASURED", "E", ""), ("UNIT", "8A", ""), ("STATUS", "12A", "")]
    tel_cols = [("CTRLID", "I", ""), ("FWVERSION", "16A", ""), ("BOARDTEMP", "E", "deg C"), ("READTIME", "E", "s"), ("STATUS", "12A", ""), ("ERRORFLAG", "I", "")]
    return amp_cols, xtalk_cols, volt_cols, tel_cols


def xtalk_rows():
    today = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "")
    return [{"SOURCE_AMP": s, "TARGET_AMP": t, "XTALK_COEF": 0.0, "XTALK_ERROR": 0.0, "XTALK_VERSION": "UNMEASURED", "MEASURE_DATE": today, "STATUS": "PLACEHOLDER"}
            for s in range(1,65) for t in range(1,65)]


def volt_rows(mk_hdr: dict):
    """VOLTINFO: the CCD bias/clock placeholders, then the measured rails.

    The 9 bias/clock rows still have no source - the raw card family that fed
    them (VOLT<n>/VSET<n>/VMEA<n>) was retired - so they now carry -999.0 and
    STATUS='PLACEHOLDER'.  They used to carry 0.0/'UNKNOWN', and 0.0 V is a
    perfectly legal VSS reading, so missing data was indistinguishable from a
    real measurement.

    The rails that follow ARE measured, from Cn_VOLT/Cn_CURR.  They are power
    supply rails, not CCD bias voltages, which is why they are named C<n>_<rail>
    and do not overwrite the nine above.
    """
    rows = [{"VOLTNAME": n, "SETPOINT": HK_REAL_SENTINEL,
             "MEASURED": HK_REAL_SENTINEL, "UNIT": "V", "STATUS": "PLACEHOLDER"}
            for n in BIAS_CLOCK_VOLTNAMES]
    for n in (1, 2):
        hk = read_ctrl_hk(mk_hdr, n)
        absent = hk["status"] == "UNKNOWN"     # the cards are not in the raw
        for suffix, unit, series in (("", "V", hk["volts"]),
                                     ("_I", "A", hk["currs"])):
            for rail, val in zip(CTRL_RAILS, series):
                if val is not None:
                    status = "MEASURED"
                elif absent:
                    status = "UNKNOWN"            # nothing was ever reported
                else:
                    status = "NC"                 # reported, marked invalid
                rows.append({
                    "VOLTNAME": "C%d_%s%s" % (n, rail, suffix),
                    "SETPOINT": HK_REAL_SENTINEL,      # nominal not in the raw
                    "MEASURED": HK_REAL_SENTINEL if val is None else val,
                    "UNIT": unit,
                    "STATUS": status,
                })
    return rows


def volt_status(rows):
    """OK / PARTIAL / UNKNOWN over the measured rail rows only.

    The nine bias/clock rows are permanently unmeasured, so including them
    would pin this to PARTIAL forever and it would stop meaning anything.
    """
    rail = [r for r in rows if r["VOLTNAME"][:3] in ("C1_", "C2_")]
    if not rail:
        return "UNKNOWN"
    states = {r["STATUS"] for r in rail}
    if states == {"MEASURED"}:
        return "OK"
    if states == {"UNKNOWN"}:
        return "UNKNOWN"          # the Cn_* cards are not in the raw at all
    if states <= {"NC", "UNKNOWN"}:
        # Reported and marked VALID=0 - an invalid response, not a sensor
        # fault and not missing cards.  Downstream must not score it as
        # hardware trouble, so the distinction is preserved.
        return "NC"
    return "PARTIAL"


def telemetry_rows(mk_hdr: dict):
    """TELEMETRY: one row per science controller.

    BOARDTEMP is slot 1 of Cn_TEMP - the Backplane sensor, which is the one
    the retired BCKTEMP card named this column as its destination.  Do not
    average the ten slots: the others are module temperatures.

    FWVERSION, READTIME and ERRORFLAG keep their sentinels because the new
    raw deliberately carries no source for them - controller errors are
    monitored on a separate path, and synthesising a value here would be read
    downstream as a controller assertion.
    """
    rows = []
    for n in (1, 2):
        hk = read_ctrl_hk(mk_hdr, n)
        board = hk["temps"][0] if hk["temps"] else None
        rows.append({
            "CTRLID": n,
            "FWVERSION": "UNKNOWN",
            "BOARDTEMP": HK_REAL_SENTINEL if board is None else board,
            "READTIME": -1.0,
            "STATUS": hk["status"],
            "ERRORFLAG": HK_INT_SENTINEL,
        })
    return rows


def telemetry_status(rows):
    states = {r["STATUS"] for r in rows}
    if states == {"OK"}:
        return "OK"
    if states == {"NC"}:
        return "NC"            # VALID=0 response, not missing cards
    if states <= {"UNKNOWN"}:
        return "UNKNOWN"
    return "PARTIAL"


def write_amp_hdu(fout, chip: str, amp: int, chip_hdr: dict, raw_data: np.ndarray,
                  raw_file: str, chmap: dict, pointing=(None, None),
                  sky: bool = True, ampchar: dict | None = None):
    raw_sec_data, raw_sec_bias, loc_data, loc_bias = raw_x_sections(chip, amp)
    ry1, ry2 = raw_y_section(amp)
    stripe = np.empty((ACTIVE_HALF_ROWS, RAW_XTILE), dtype=">i2")
    d = raw_data[ry1-1:ry2, raw_sec_data[0]-1:raw_sec_data[1]]
    b = raw_data[ry1-1:ry2, raw_sec_bias[0]-1:raw_sec_bias[1]]
    stripe[:, loc_data[0]-1:loc_data[1]] = d
    stripe[:, loc_bias[0]-1:loc_bias[1]] = b
    fout.write(hdu_bytes(amp_header(chip, amp, chip_hdr, raw_file, chmap,
                                    pointing, sky, ampchar),
                         stripe.tobytes(order="C")))


def convert(mk_path: Path, nt_path: Path, out_path: Path,
            ampchar: dict | None = None, ampchar_name: str = ""):
    mk_hdr, mk_data = memmap_raw(mk_path)
    nt_hdr, nt_data = memmap_raw(nt_path)
    if mk_data.shape != (RAW_NAXIS2, RAW_NAXIS1):
        raise ValueError(f"MK has unexpected shape {mk_data.shape}")
    if nt_data.shape != (RAW_NAXIS2, RAW_NAXIS1):
        raise ValueError(f"NT has unexpected shape {nt_data.shape}")

    # The two raw files are written independently by two controllers, so
    # nothing but this stops us stapling two different exposures together.
    mk_exp = str(hval(mk_hdr, "EXPID", "")).strip()
    nt_exp = str(hval(nt_hdr, "EXPID", "")).strip()
    if mk_exp and nt_exp and mk_exp != nt_exp:
        raise ValueError("EXPID mismatch between pair members: %s has %s, %s has %s"
                         % (mk_path.name, mk_exp, nt_path.name, nt_exp))

    # C-5/C-13: compare the raw's own geometry declarations with the
    # constants used to slice it.  Recorded in HISTORY rather than fatal, so
    # an operator can still get the pixels out of a frame with a stale card.
    geom_msgs = check_raw_geometry(mk_hdr, mk_path) + check_raw_geometry(nt_hdr, nt_path)
    for msg in geom_msgs:
        _warn("raw geometry disagrees with the converter: %s" % msg)

    # The converter reads pointing and house-keeping from the MK member only,
    # which raw spec 5.9 permits. Check that the permission still holds.
    pair_msgs = check_raw_pair(mk_hdr, nt_hdr)
    for msg in pair_msgs:
        _warn("raw pair members disagree: %s" % msg)

    # ONE tangent point for the whole mosaic. If the two members disagree the
    # pair check above has already said so; we still use MK's, because two
    # tangent points in one mosaic is not a thing a WCS can express.
    pointing = wcs_pointing(mk_hdr)
    # A seed WCS only earns its place on a frame that can be solved.
    sky = sees_sky(mk_hdr)
    wcs_written = bool(sky and pointing[0] is not None)
    if not sky:
        print("%s: IMAGETYP=%s sees no sky; writing no seed WCS "
              "(L1 astrometry is not applicable, not failed)"
              % (mk_path.name, str(hval(mk_hdr, "IMAGETYP", "")).strip() or "?"),
              file=sys.stderr)
    elif pointing[0] is None:
        _warn("TCS pointing did not parse (RA=%r DEC=%r); no WCS card will be "
              "written" % (hval(mk_hdr, "RA", ""), hval(mk_hdr, "DEC", "")))

    # C-11: amplifier electronics identity, per chip, from its own file.
    chmap = parse_chmap(mk_hdr, nt_hdr)
    chmap_ok, chmap_msgs = validate_chmap(chmap)
    if not chmap_ok:
        _warn("raw CHMAP does not match %s (%d amps); CHMAPOK=F"
              % (AMPID_MAP_VERSION, len(chmap_msgs)))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp-{os.getpid()}")
    try:
        with tmp_path.open("wb") as fout:
            pcards = primary_cards(mk_hdr, mk_path, nt_path, out_path,
                                   pointing=pointing, sky=sky, chmap_ok=chmap_ok,
                                   chmap_msgs=chmap_msgs, geom_msgs=geom_msgs,
                                   pair_msgs=pair_msgs,
                                   ampchar_name=ampchar_name if ampchar else "")
            fout.write(hdu_bytes(pcards))
            for chip in CHIP_ORDER:
                is_mk = CHIP_TO_TAG[chip] == "MK"
                data = mk_data if is_mk else nt_data
                # Each chip's cards come from the file that actually holds it.
                chip_hdr = mk_hdr if is_mk else nt_hdr
                raw_file = mk_path.name if is_mk else nt_path.name
                for amp in range(1, 17):
                    write_amp_hdu(fout, chip, amp, chip_hdr, data, raw_file,
                                  chmap, pointing, sky, ampchar)
            amp_cols, xtalk_cols, volt_cols, tel_cols = table_defs()
            fout.write(bintable_bytes("AMPINFO", amp_cols,
                                      ampinfo_rows(mk_path, nt_path, chmap,
                                                   wcs_written, ampchar), [
                card("NAMP", 64, "number of amplifier rows"),
                card("GEOMVER", GEOMETRY_VERSION, "geometry definition version"),
                card("RAWGROUP", "MKNT", "raw grouping"),
            ]))
            fout.write(bintable_bytes("XTALKINFO", xtalk_cols, xtalk_rows(), [
                card("NXTALK", 4096, "number of crosstalk matrix rows"),
                card("XTALKVER", "UNMEASURED", "placeholder crosstalk version"),
                card("XTALKCAL", False, "replace coefficients after calibration"),
            ]))
            vrows = volt_rows(mk_hdr)
            fout.write(bintable_bytes("VOLTINFO", volt_cols, vrows, [
                card("BIASVER", "UNKNOWN", "bias setting version"),
                card("CLKVER", "UNKNOWN", "clock setting version"),
                card("VOLTSTAT", volt_status(vrows), "voltage telemetry status"),
                card("NVOLT", len(vrows), "number of voltage table rows"),
                card("RAILREF", RAILREF, "rail/module slot order reference"),
            ]))
            trows = telemetry_rows(mk_hdr)
            fout.write(bintable_bytes("TELEMETRY", tel_cols, trows, [
                card("NCTRL", 2, "number of science controllers"),
                card("TELSTAT", telemetry_status(trows), "telemetry status"),
            ]))
        os.replace(tmp_path, out_path)
        return {"pointing": pointing, "sky": sky,
                "imagetyp": str(hval(mk_hdr, "IMAGETYP", "")).strip(),
                "geom_msgs": geom_msgs,
                "pair_msgs": pair_msgs, "chmap_ok": chmap_ok,
                "chmap_msgs": chmap_msgs,
                "voltstat": volt_status(vrows),
                "telstat": telemetry_status(trows)}
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _iter_hdus(path: Path):
    """Yield (header_dict, header_bytes, data_offset, data_bytes) per HDU."""
    size = path.stat().st_size
    off = 0
    with path.open("rb") as f:
        while off < size:
            f.seek(off)
            blocks = []
            while True:
                blk = f.read(BLOCK)
                if not blk:
                    return
                blocks.append(blk)
                if any(_is_end_card(blk[i:i+80]) for i in range(0, BLOCK, 80)):
                    break
            raw = b"".join(blocks)
            hdr = {}
            for blk in blocks:
                for i in range(0, BLOCK, 80):
                    c = blk[i:i+80].decode("ascii", errors="replace")
                    key = c[:8].strip().upper()
                    if key and key not in ("COMMENT", "HISTORY", "END") and "=" in c:
                        val, _cm = split_fits_value_comment(c.split("=", 1)[1])
                        hdr.setdefault(key, parse_fits_value(val))
            naxis = int(hdr.get("NAXIS", 0) or 0)
            npix = 1
            for i in range(1, naxis + 1):
                npix *= int(hdr.get("NAXIS%d" % i, 0) or 0)
            nbytes = 0
            if naxis:
                nbytes = (abs(int(hdr.get("BITPIX", 8))) // 8
                          * int(hdr.get("GCOUNT", 1) or 1)
                          * (int(hdr.get("PCOUNT", 0) or 0) + npix))
            nbytes += (-nbytes) % BLOCK
            yield hdr, raw, off + len(raw), nbytes
            off += len(raw) + nbytes


def _hdu_checksum_ok(path: Path, raw_hdr: bytes, data_off: int, data_len: int) -> bool:
    """A conforming HDU sums to all ones over header + data."""
    acc = _fits_sum32(raw_hdr)
    if data_len:
        with path.open("rb") as f:
            f.seek(data_off)
            left = data_len
            while left:
                chunk = f.read(min(left, 8 << 20))
                if not chunk:
                    return False
                acc = _fits_sum32(chunk, acc)
                left -= len(chunk)
    return acc == 0xFFFFFFFF


def write_hdu_verify(out_path: Path, report: dict | None = None) -> Path:
    """Write the <output>.hdu_verify.txt structural report.

    Self-contained on purpose: the converter depends on numpy alone, and a
    verification step that needs a library the converter does not have is a
    verification step that silently stops being run.
    """
    lines = ["KMT-CEU L0 MEF structural verification", "", "file: %s" % out_path.name, ""]
    report = report or {}
    names, bad_sum, no_sum, n_amp, amp_hdrs = [], [], [], 0, []
    prim = {}
    for idx, (hdr, raw, doff, dlen) in enumerate(_iter_hdus(out_path)):
        ext = str(hdr.get("EXTNAME", "PRIMARY")).strip() or "PRIMARY"
        names.append(ext)
        if idx == 0:
            prim = hdr
        if str(hdr.get("EXTTYPE", "")).strip() == "AMP_RAW":
            n_amp += 1
            amp_hdrs.append((ext, hdr))
        if "CHECKSUM" not in hdr and "DATASUM" not in hdr:
            # An HDU that never carried a checksum is not a corrupt HDU.
            # Products written before v2.2.0 have none at all.
            no_sum.append("%d:%s" % (idx, ext))
        elif not _hdu_checksum_ok(out_path, raw, doff, dlen):
            bad_sum.append("%d:%s" % (idx, ext))
    lines.append("HDU count            : %d (expected 69)" % len(names))
    lines.append("amplifier image HDUs : %d (expected 64)" % n_amp)
    lines.append("trailing tables      : %s" % ", ".join(names[-4:]))
    if bad_sum:
        sum_state = "FAILED on " + ", ".join(bad_sum[:8]) + (
            " ..." if len(bad_sum) > 8 else "")
    elif no_sum and len(no_sum) == len(names):
        sum_state = ("not written - this product predates v2.2.0, which is "
                     "not a failure")
    elif no_sum:
        sum_state = ("%d of %d HDUs verify; %d carry no checksum card"
                     % (len(names) - len(no_sum), len(names), len(no_sum)))
    else:
        sum_state = "all %d HDUs verify" % len(names)
    lines.append("CHECKSUM/DATASUM     : %s" % sum_state)
    lines.append("")
    lines.append("Sky WCS")
    solved = bool(prim.get("WCSSOLVE", False))
    with_wcs = [(n, h) for n, h in amp_hdrs if "CRVAL1" in h]
    if not amp_hdrs:
        lines.append("  NOT APPLICABLE     : this file has no amplifier "
                     "extensions")
    elif not with_wcs and not prim.get("WCSSKY", True):
        lines.append("  NOT APPLICABLE     : IMAGETYP=%s sees no sky, so no seed"
                     % (prim.get("IMAGETYP", "?")))
        lines.append("                       WCS was written. L1 skips "
                     "astrometry; that is not a failure.")
    elif not with_wcs:
        lines.append("  NO WCS WRITTEN     : %s"
                     % ("the TCS pointing did not parse, so every WCS card "
                        "was omitted" if prim.get("WCSOMIT")
                        else "no amp extension carries CRVAL1 (cause not "
                             "recorded in the primary)"))
        lines.append("  amp extensions carrying a WCS : 0 of %d" % len(amp_hdrs))
    else:
        lines.append("  WCSNAME            : %s" % prim.get("WCSNAME", "(absent)"))
        lines.append("  role               : seed (initial guess) for the L1 "
                     "Gaia astrometric fit")
        lines.append("  WCSAPPRX / WCSSOLVE: %s / %s  %s"
                     % (prim.get("WCSAPPRX", "?"), prim.get("WCSSOLVE", "?"),
                        "" if solved else
                        "(not yet fitted - do not measure positions with this)"))
        if "RA_DEG" in prim and "DEC_DEG" in prim:
            lines.append("  tangent point      : RA %.6f  Dec %+.6f [deg]"
                         % (float(prim["RA_DEG"]), float(prim["DEC_DEG"])))
        else:
            lines.append("  tangent point      : NOT PUBLISHED - the primary "
                         "carries no RA_DEG/DEC_DEG")
        if "BOREPIXX" in prim and "BOREPIXY" in prim:
            lines.append("  boresight pixel    : (%.1f, %.1f) in %s"
                         % (float(prim["BOREPIXX"]), float(prim["BOREPIXY"]),
                            prim.get("DETSIZE", "?")))
        else:
            lines.append("  boresight pixel    : NOT PUBLISHED")
        lines.append("  amp extensions carrying a WCS : %d of %d"
                     % (len(with_wcs), len(amp_hdrs)))
        # Read back from the cards that were actually written. Recomputing
        # them from the same functions that produced them would agree with
        # itself no matter what landed in the file.
        crv = {(h.get("CRVAL1"), h.get("CRVAL2")) for _n, h in with_wcs}
        cdm = {(h.get("CD1_1"), h.get("CD1_2"), h.get("CD2_1"), h.get("CD2_2"))
               for _n, h in with_wcs}
        lines.append("  distinct CRVAL     : %d (must be 1 - one tangent point "
                     "for the mosaic)" % len(crv))
        lines.append("  distinct CD matrix : %d (must be 1 - no per-amp flips)"
                     % len(cdm))
        bx, by = prim.get("BOREPIXX"), prim.get("BOREPIXY")
        worst, worst_at, missing, checked = 0.0, "all equal", [], 0
        for name, h in with_wcs:
            try:
                dx = abs(float(h["CRPIX1"]) - float(h["LTV1"]) + float(h["DTV1"]) - float(bx))
                dy = abs(float(h["CRPIX2"]) - float(h["LTV2"]) + float(h["DTV2"]) - float(by))
            except (KeyError, TypeError, ValueError):
                missing.append(name)
                continue
            checked += 1
            if max(dx, dy) > worst:
                worst, worst_at = max(dx, dy), name
        if checked:
            lines.append("  CRPIX-LTV+DTV      : max deviation from the boresight "
                         "= %g px over %d amps (worst %s)" % (worst, checked, worst_at))
        else:
            # Never print a passing number for a check that could not run.
            lines.append("  CRPIX-LTV+DTV      : NOT CHECKED - no amp carries the "
                         "full CRPIX/LTV/DTV set")
        if missing:
            lines.append("  MISSING WCS/IRAF CARDS on %d amps: %s%s"
                         % (len(missing), ", ".join(missing[:8]),
                            " ..." if len(missing) > 8 else ""))
    lines.append("")
    lines.append("Amplifier identity")
    lines.append("  CHMAPOK            : %s  (%s)"
                 % (prim.get("CHMAPOK", "?"), prim.get("AMPIDMAP", "?")))
    for msg in list(report.get("chmap_msgs", []))[:8]:
        lines.append("    ! %s" % msg)
    lines.append("")
    geom = list(report.get("geom_msgs", []))
    pair = list(report.get("pair_msgs", []))
    lines.append("Raw cross-checks")
    if not report:
        # These two live only in convert()'s report; they cannot be recovered
        # from the finished file. Printing "agree" without them would claim a
        # check that never ran.
        lines.append("  geometry declarations : not reported "
                     "(sidecar written without the converter report)")
        lines.append("  pair consistency      : not reported")
    else:
        lines.append("  geometry declarations : %s"
                     % ("agree with the converter" if not geom
                        else "%d MISMATCH(ES)" % len(geom)))
        for msg in geom[:8]:
            lines.append("    ! %s" % msg)
        lines.append("  pair consistency      : %s"
                     % ("MK and NT agree" if not pair
                        else "%d MISMATCH(ES)" % len(pair)))
        for msg in pair[:8]:
            lines.append("    ! %s" % msg)
    lines.append("")
    lines.append("Calibration state (D-005: placeholders are not calibration)")
    lines.append("  XTALKCAL           : %s" % prim.get("XTALKCAL", "?"))
    lines.append("  WCSSOLVE           : %s   (L1 Gaia fit sets this)" % solved)
    lines.append("")
    lines.append("versions: CREATOR=%s PRODVER=%s GEOMVER=%s"
                 % (prim.get("CREATOR", "?"), prim.get("PRODVER", "?"),
                    prim.get("GEOMVER", "?")))
    path = out_path.with_suffix(out_path.suffix + ".hdu_verify.txt")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_summary(out_path: Path, report: dict):
    if report is None:
        # Silence here would be four confident statements about a file this
        # function never looked at.
        raise ValueError("write_summary needs convert()'s report dict")
    ra_deg, _dec = report.get("pointing", (None, None))
    geom_msgs = list(report.get("geom_msgs", []))
    pair_msgs = list(report.get("pair_msgs", []))
    if not report.get("sky", True):
        wcs_block = ("Seed sky WCS:\n"
                     "  NOT WRITTEN - IMAGETYP=%s sees no sky (bias/dark/dome\n"
                     "  flat), so an astrometric solution is not applicable and\n"
                     "  a seed has no consumer. WCSSKY=F. L1 skips astrometry;\n"
                     "  that is not a failed solution.\n"
                     "  The IRAF pixel transforms LTV/LTM/DTV/DTM are still\n"
                     "  written - they describe the detector, not the sky."
                     % (report.get("imagetyp") or "?"))
    elif ra_deg is None:
        wcs_block = ("Seed sky WCS:\n"
                     "  NOT WRITTEN - the TCS pointing did not parse, so every\n"
                     "  WCS card was omitted rather than defaulted")
    else:
        wcs_block = ("Seed sky WCS:\n"
                     "  tangent point = TCS boresight, identical CRVAL on all 64 extensions\n"
                     "  per-amp offset carried by CRPIX from mosaic pixel (%s, %s)\n"
                     "  WCSNAME = %s, WCSAPPRX = T, WCSSOLVE = F\n"
                     "  role: initial guess for the L1 Gaia astrometric fit.\n"
                     "  Not a product WCS - measure positions only from the\n"
                     "  solved L1 WCS (WCSSOLVE = T, catalogue in WCSCAT)."
                     % (BORESIGHT_X, BORESIGHT_Y, WCSNAME_L0))
    if geom_msgs or pair_msgs:
        geom_title = ("Archon raw geometry ASSUMED BY THIS CONVERTER\n"
                      "  WARNING: %d raw cross-check mismatch(es) - see the\n"
                      "  .hdu_verify.txt sidecar:" % (len(geom_msgs) + len(pair_msgs)))
    else:
        geom_title = "Verified Archon raw geometry:"
    _state = {"OK": "measured from %s",
              "PARTIAL": "PARTLY measured from %s - some slots NC",
              "NC": "NOT measured - controller reported VALID=0 (%s all NC)",
              "UNKNOWN": "NOT measured - %s absent from the raw"}
    volt_state = _state.get(report.get("voltstat", "UNKNOWN"),
                            "unknown state (%s)") % "Cn_VOLT / Cn_CURR"
    tel_state = _state.get(report.get("telstat", "UNKNOWN"),
                           "unknown state (%s)") % "Cn_TEMP"
    digest = sha256_file(out_path)
    summary = out_path.with_suffix(out_path.suffix + ".summary.txt")
    txt = f"""KMT-CEU L0 64-amplifier MEF conversion summary

Output file:
  {out_path.name}

Output layout:
  PRIMARY
  M01T..M08T, M01B..M08B
  K01T..K08T, K01B..K08B
  N01T..N08T, N01B..N08B
  T01T..T08T, T01B..T08B
  AMPINFO
  XTALKINFO
  VOLTINFO
  TELEMETRY

Product rationale:
  L0 Raw MEF preserves 64 amplifier images separately, including local overscan.
  This supports amplifier-level overscan correction, bias/gain/read-noise calibration,
  crosstalk correction, bias jump diagnosis, and safer treatment of sources crossing
  amplifier boundaries before CCD-level image assembly.

{geom_title}
  MK -> M,K
  NT -> N,T
  CHIPLIST = M,K,N,T
  RAWNAX1 = {RAW_NAXIS1}
  RAWNAX2 = {RAW_NAXIS2}
  RAWXTILE = {RAW_XTILE}
  active columns per amp = {AMP_DATA_COLS}
  X overscan per amp = {OVERSCAN_X}
  middle Y overscan = {MIDDLE_OVERSCAN_Y}
  TOP active rows = {ACTIVE_HALF_ROWS}
  BOT active rows = {ACTIVE_HALF_ROWS}

CEU orientation convention:
  no chip-dependent OSU-style flip
  amp 1-8 = TOP half
  amp 9-16 = BOT half
  raw is stored in ascending CCD order on both axes, so the CD matrix is
  identical on all 64 amps and no amp image is mirrored

{wcs_block}

Calibration state (D-005: placeholders are not calibration):
  GAIN/RDNOISE/SATURAT/LINMAX  placeholder unless --ampchar was given
  XTALKINFO                    placeholder, XTALKCAL = F
  VOLTINFO  CCD bias/clock     placeholder, no source in the raw
  VOLTINFO  controller rails   {volt_state}
  TELEMETRY BOARDTEMP/STATUS   {tel_state}
  TELEMETRY FWVERSION/READTIME/ERRORFLAG   no source in the raw

File size:
  {out_path.stat().st_size / 1024 / 1024:.2f} MiB

SHA256:
  {digest}
"""
    summary.write_text(txt, encoding="utf-8")
    return summary


def gzip_file(path: Path, level: int = 5) -> Path:
    gz = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as fi, gzip.open(gz, "wb", compresslevel=level) as fo:
        shutil.copyfileobj(fi, fo, length=1024*1024)
    sha = sha256_file(gz)
    gz.with_suffix(gz.suffix + ".sha256.txt").write_text(f"{sha}  {gz.name}\n", encoding="utf-8")
    return gz


def main():
    parser = argparse.ArgumentParser(description="Convert KMT-CEU Archon MK/NT raw FITS to L0 64-amplifier MEF")
    parser.add_argument("input", help="MK or NT raw FITS file")
    parser.add_argument("-o", "--output", default=None, help="output L0 MEF FITS path")
    parser.add_argument("-d", "--outdir", default=".", help="output directory if --output is omitted")
    parser.add_argument("-f", "--force", action="store_true", help="overwrite existing output")
    parser.add_argument("--gzip", action="store_true", help="also create .gz compressed copy")
    parser.add_argument("--ampchar", default=None,
                        help="amp characterization CSV (cam_char/results schema): "
                             "stamps measured GAIN/RDNOISE/SATURAT/LINMAX into the "
                             "amp headers and AMPINFO instead of the placeholders")
    args = parser.parse_args()
    # Report every occurrence, not just the first per source line - but
    # APPEND, so an operator running the night batch under -W error still gets
    # a geometry or CHMAP mismatch escalated to a failure instead of one line
    # of stderr among forty exposures.
    warnings.filterwarnings("always", category=ConverterWarning, append=True)

    ampchar = load_ampchar(args.ampchar) if args.ampchar else None
    ampchar_name = Path(args.ampchar).name if args.ampchar else ""
    inp = Path(args.input).resolve()
    mk, nt = find_pair(inp)
    # A half pair is a real, intended outcome: the two controllers store
    # independently and one can fail while the other succeeds.  An L0 MEF
    # still needs both, so this is an error - but it is a skip-this-exposure
    # error, not a sign that anything is corrupt.
    for side in (mk, nt):
        if not side.exists():
            raise FileNotFoundError(
                "%s is missing, so this exposure is a half pair; skip it "
                "rather than treating it as a failure (raw spec 2.1)" % side.name)
    mk_hdr, _ = read_primary_header(mk)
    out = Path(args.output).resolve() if args.output else default_output_name(mk, Path(args.outdir).resolve(), mk_hdr)
    if out.exists() and not args.force:
        raise FileExistsError(f"Output exists: {out}; use -f to overwrite")
    report = convert(mk, nt, out, ampchar=ampchar, ampchar_name=ampchar_name)
    summary = write_summary(out, report)
    verify = write_hdu_verify(out, report)
    print(out)
    print(summary)
    print(verify)
    if args.gzip:
        print(gzip_file(out))


if __name__ == "__main__":
    main()

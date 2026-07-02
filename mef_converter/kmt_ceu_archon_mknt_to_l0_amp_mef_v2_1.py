#!/usr/bin/env python3
"""
KMT-CEU Archon MK/NT raw FITS to L0 64-amplifier MEF converter.

Input raw files:
  KMTN.YYYYMMDD.NNNNNN.MK.fits  -> M, K chips
  KMTN.YYYYMMDD.NNNNNN.NT.fits  -> N, T chips

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
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import os
import re
import shutil
import struct
from pathlib import Path

import numpy as np

BLOCK = 2880
SOFTWARE_VERSION = "v2.1.2"
PRODUCT_VERSION = "v2.1.1"  # L0 MEF format unchanged by v2.1.2 float-precision fix
GEOMETRY_VERSION = "CEU-L0AMP-v2.1"

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
PIX_SCALE = 0.400

CHIP_ORDER = ["M", "K", "N", "T"]
TAG_TO_CHIPS = {"MK": ["M", "K"], "NT": ["N", "T"]}
CHIP_TO_TAG = {"M": "MK", "K": "MK", "N": "NT", "T": "NT"}
AMP_BASE = {"M": 0, "K": 16, "N": 32, "T": 48}
CHIP_X0 = {"M": 1, "K": CCD_COLS + GAP_COLS + 1, "N": 1, "T": CCD_COLS + GAP_COLS + 1}
CHIP_Y0 = {"M": CCD_ROWS + GAP_ROWS + 1, "K": CCD_ROWS + GAP_ROWS + 1, "N": 1, "T": 1}

# CEU convention: no chip-dependent OSU-style image flip at L0 packing stage.
CHIPFLP = "None"
STRIPDIR = "+X"


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


def read_primary_header(path: Path):
    blocks = []
    with path.open("rb") as f:
        while True:
            block = f.read(BLOCK)
            if not block:
                raise ValueError(f"No END card in FITS header: {path}")
            blocks.append(block)
            if any(block[i:i+80].startswith(b"END") for i in range(0, BLOCK, 80)):
                break
    raw_cards = []
    for block in blocks:
        for i in range(0, BLOCK, 80):
            c = block[i:i+80].decode("ascii", errors="replace")
            raw_cards.append(c)
            if c.startswith("END"):
                break
        if raw_cards and raw_cards[-1].startswith("END"):
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
    m = re.match(r"^KMTN\.(\d{8})\.(\d{6})\.MK\.fits$", mk_path.name)
    root = f"{m.group(1)}.{m.group(2)}" if m else mk_path.stem.replace(".MK", "")
    obs = str(hval(mk_hdr, "OBSERVAT", "KMT")).upper()
    prefix = {"CTIO": "kmtc", "SAAO": "kmts", "SSO": "kmta"}.get(obs, "kmt")
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


def jd_from_datetime(d: dt.datetime) -> float:
    year, month = d.year, d.month
    day = d.day + (d.hour + (d.minute + (d.second + d.microsecond/1e6)/60.0)/60.0)/24.0
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return int(365.25*(year+4716)) + int(30.6001*(month+1)) + day + b - 1524.5


def primary_cards(mk_hdr: dict, mk_path: Path, nt_path: Path, out_path: Path):
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

    def v(k, d=""):
        return hval(mk_hdr, k, d)

    cards = [
        card("SIMPLE", True, "FITS standard"),
        card("BITPIX", 16, "bits per pixel in image extensions"),
        card("NAXIS", 0, "primary HDU has no image array"),
        card("EXTEND", True, "file contains extensions"),
        card("ORIGIN", v("ORIGIN", "KASI"), "FITS file originator"),
        card("DATE", now, "date FITS file was generated"),
        card("CREATOR", f"kmt_ceu_l0amp_mknt2mef_{SOFTWARE_VERSION}", "MEF creation program"),
        card("COMMENT", "KMT-CEU L0 Raw 64-amplifier MEF product"),
        card("COMMENT", "Primary raw archive/product for amplifier-level calibration"),
        card("BUNIT", v("BUNIT", "ADU"), "units of image pixel values"),
        card("DATAPROD", "L0_AMP", "data product type"),
        card("PRODVER", PRODUCT_VERSION, "product format version"),

        card("COMMENT", "Raw Archon file provenance"),
        card("RAWGROUP", "MKNT", "raw Archon file grouping convention"),
        card("CHIPLIST", "M,K,N,T", "official science chip order"),
        card("MKFILE", mk_path.name, "source MK raw FITS file"),
        card("NTFILE", nt_path.name, "source NT raw FITS file"),
        card("NUMFILES", 2, "number of raw files used"),
        card("RAWNAX1", RAW_NAXIS1, "raw Archon image width"),
        card("RAWNAX2", RAW_NAXIS2, "raw Archon image height"),
        card("RAWXTILE", RAW_XTILE, "raw amp tile width"),
        card("AMPDATA", AMP_DATA_COLS, "active columns per amp tile"),
        card("OVERSCNX", OVERSCAN_X, "X overscan columns per amp tile"),
        card("PRESCANX", PRESCAN_X, "X prescan columns per amp tile"),
        card("MIDOVSCY", MIDDLE_OVERSCAN_Y, "middle Y overscan rows"),
        card("TOPROWS", ACTIVE_HALF_ROWS, "active TOP-half rows"),
        card("BOTROWS", ACTIVE_HALF_ROWS, "active BOT-half rows"),
        card("CHIPFLP", "None", "no chip-dependent OSU-style flip applied"),

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
        card("ELEVATIO", v("ELEVATIO", ""), "site elevation [m]"),
        card("OBSERVER", v("OBSERVER", ""), "observer(s)"),
        card("OBJECT", v("OBJECT", ""), "name of object observed"),
        card("FIELDID", v("FIELDID", v("OBJECT", "")), "KMTNet field identifier"),
        card("PROJID", v("PROJID", ""), "project or observing program ID"),
        card("IMAGETYP", v("IMAGETYP", ""), "type of observation"),
        card("OBSTYPE", v("OBSTYPE", ""), "type of observation"),
        card("EXPTIME", v("EXPTIME", 0.0), "exposure time [s]"),
        card("DARKTIME", v("DARKTIME", 0.0), "cumulative dark time [s]"),
        card("TSHOPEN", v("TSHOPEN", ""), "shutter open time"),
        card("TSHSHUT", v("TSHSHUT", ""), "shutter close time"),
        card("FILENAME", out_path.name, "MEF filename"),
        card("UNIQNAME", v("UNIQNAME", ""), "unique filename"),

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
        card("UT", (str(date_obs)[:10] + "T" + str(v("TSHOPEN", ""))) if v("TSHOPEN", "") else date_obs, "UTC timestamp"),
        card("RADECSYS", v("RADECSYS", "ICRS"), "telescope coordinate system"),
        card("RA", v("RA", "00:00:00.00"), "telescope RA"),
        card("DEC", v("DEC", "+00:00:00.0"), "telescope DEC"),
        card("EQUINOX", v("EQUINOX", 2000.0), "coordinate system equinox"),
        card("HA", v("HA", ""), "hour angle at start"),
        card("ST", v("ST", ""), "local sidereal time at start"),
        card("SECZ", v("SECZ", ""), "secant of zenith distance"),
        card("ALT", v("ALT", ""), "telescope altitude [deg]"),
        card("AZ", v("AZ", ""), "telescope azimuth [deg]"),
        card("TCSDRIV", v("TCSDRIVE", v("TCSDRIV", "")), "telescope drive status"),
        card("TELMOVE", v("TELMOVE", ""), "telescope motion status"),

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
        card("CCDTEMP", v("CCDTEMP", ""), "CCD temperature [C]"),
        card("DEWPRES", v("DEWPRES", ""), "dewar pressure"),
        card("PT30N1", v("PT30N1", ""), "cooler temperature sensor 1 [C]"),
        card("PT30N2", v("PT30N2", ""), "cooler temperature sensor 2 [C]"),
        card("CHARCOAL", v("CHARCOAL", ""), "charcoal getter temperature [C]"),
        card("AIR_IN", v("AIR_IN", ""), "air inlet temperature [C]"),
        card("AIR_OUT", v("AIR_OUT", ""), "air outlet temperature [C]"),
        card("GLYC_IN", v("GLYC_IN", ""), "glycol inlet temperature [C]"),
        card("GLYC_OUT", v("GLYC_OUT", ""), "glycol outlet temperature [C]"),
        card("CHKIMG", v("CHKIMG", ""), "image check status"),
        card("CHKIMG_C", v("CHKIMG_C", ""), "image check comment"),
    ]
    return cards


def amp_header(chip: str, amp: int, mk_hdr: dict, raw_file: str):
    ext = extname_for(chip, amp)
    raw_data, raw_bias, loc_data, loc_bias = raw_x_sections(chip, amp)
    ry1, ry2 = raw_y_section(amp)
    cx1, cx2, cy1, cy2 = ccdsec(amp)
    dx1, dx2, dy1, dy2 = detsec(chip, amp)
    global_amp = AMP_BASE[chip] + amp
    read_dir = "-Y" if amp <= 8 else "+Y"

    def v(k, d=""):
        return hval(mk_hdr, k, d)

    return [
        card("XTENSION", "IMAGE", "image extension"),
        card("BITPIX", 16, "array data type"),
        card("NAXIS", 2, "number of array dimensions"),
        card("NAXIS1", RAW_XTILE, "amp image width including overscan"),
        card("NAXIS2", ACTIVE_HALF_ROWS, "amp image active rows"),
        card("PCOUNT", 0),
        card("GCOUNT", 1),
        card("BZERO", hval(mk_hdr, "BZERO", 32768), "unsigned 16-bit zero point"),
        card("BSCALE", hval(mk_hdr, "BSCALE", 1), "default scale"),
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
        card("MODULE", 1 + ((amp - 1) // 8), "controller module placeholder"),
        card("CHANNEL", 1 + ((amp - 1) % 8), "controller channel placeholder"),
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
        card("GAIN", 0.0, "gain placeholder [e-/ADU]"),
        card("RDNOISE", 0.0, "read noise placeholder [e-]"),
        card("SATURAT", 62000, "saturation level placeholder [ADU]"),
        card("LINMAX", 58000, "linearity maximum placeholder [ADU]"),
        card("FILTER", v("FILTER", ""), "filter name in beam"),
        card("PROJID", v("PROJID", ""), "project ID"),
        card("IMAGETYP", v("IMAGETYP", ""), "type of observation"),
        card("OBJECT", v("OBJECT", ""), "object name"),
        card("OBSTYPE", v("OBSTYPE", ""), "type of observation"),
        card("RA", v("RA", "00:00:00.00"), "telescope RA"),
        card("DEC", v("DEC", "+00:00:00.0"), "telescope DEC"),
        card("HA", v("HA", ""), "hour angle"),
        card("ST", v("ST", ""), "local sidereal time"),
        card("SECZ", v("SECZ", ""), "airmass"),
        card("ALT", v("ALT", ""), "telescope altitude [deg]"),
        card("AZ", v("AZ", ""), "telescope azimuth [deg]"),
        card("UT", (str(v("DATE-OBS", ""))[:10] + "T" + str(v("TSHOPEN", ""))) if v("TSHOPEN", "") else v("DATE-OBS", ""), "UTC timestamp"),
        card("CTYPE1", "RA---TAN", "coordinate type"),
        card("CTYPE2", "DEC--TAN", "coordinate type"),
        card("CRVAL1", 0.0, "placeholder coordinate reference RA [deg]"),
        card("CRVAL2", 0.0, "placeholder coordinate reference DEC [deg]"),
        card("CRPIX1", 0.0, "placeholder coordinate reference pixel"),
        card("CRPIX2", 0.0, "placeholder coordinate reference pixel"),
        card("CD1_1", -PIX_SCALE/3600.0, "coordinate transform matrix"),
        card("CD1_2", 0.0, "coordinate transform matrix"),
        card("CD2_1", 0.0, "coordinate transform matrix"),
        card("CD2_2", PIX_SCALE/3600.0, "coordinate transform matrix"),
        card("WCSDIM", 2, "coordinate system dimensionality"),
    ]


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


def ampinfo_rows(mk_path: Path, nt_path: Path):
    rows = []
    rawfile_by_chip = {"M": mk_path.name, "K": mk_path.name, "N": nt_path.name, "T": nt_path.name}
    for chip in CHIP_ORDER:
        for amp in range(1, 17):
            ext = extname_for(chip, amp)
            raw_data, raw_bias, loc_data, loc_bias = raw_x_sections(chip, amp)
            ry1, ry2 = raw_y_section(amp)
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
                "RAWFILE": rawfile_by_chip[chip],
                "CTRLID": 1 if chip in ("M", "K") else 2,
                "MODULE": 1 + ((amp - 1)//8),
                "CHANNEL": 1 + ((amp - 1)%8),
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
                "GAIN": 0.0,
                "RDNOISE": 0.0,
                "SATLEVEL": 62000,
                "LINMAX": 58000,
                "RAWX0": raw_data[0], "RAWX1": raw_data[1],
                "RAWY0": ry1, "RAWY1": ry2,
                "AMPX0": cx1, "AMPX1": cx2, "AMPY0": cy1, "AMPY1": cy2,
                "DETX0": dx1, "DETX1": dx2, "DETY0": dy1, "DETY1": dy2,
                "XTALKGROUP": f"C{1 if chip in ('M','K') else 2}M{1 + ((amp-1)//8)}",
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


def volt_rows():
    return [{"VOLTNAME": n, "SETPOINT": 0.0, "MEASURED": 0.0, "UNIT": "V", "STATUS": "UNKNOWN"}
            for n in ["VOD", "VRD", "VOG", "VSS", "VDD", "PCLKH", "PCLKL", "SCLKH", "SCLKL"]]


def telemetry_rows():
    return [
        {"CTRLID": 1, "FWVERSION": "UNKNOWN", "BOARDTEMP": -999.0, "READTIME": -1.0, "STATUS": "UNKNOWN", "ERRORFLAG": -1},
        {"CTRLID": 2, "FWVERSION": "UNKNOWN", "BOARDTEMP": -999.0, "READTIME": -1.0, "STATUS": "UNKNOWN", "ERRORFLAG": -1},
    ]


def write_amp_hdu(fout, chip: str, amp: int, mk_hdr: dict, raw_data: np.ndarray, raw_file: str):
    raw_sec_data, raw_sec_bias, loc_data, loc_bias = raw_x_sections(chip, amp)
    ry1, ry2 = raw_y_section(amp)
    stripe = np.empty((ACTIVE_HALF_ROWS, RAW_XTILE), dtype=">i2")
    d = raw_data[ry1-1:ry2, raw_sec_data[0]-1:raw_sec_data[1]]
    b = raw_data[ry1-1:ry2, raw_sec_bias[0]-1:raw_sec_bias[1]]
    stripe[:, loc_data[0]-1:loc_data[1]] = d
    stripe[:, loc_bias[0]-1:loc_bias[1]] = b
    fout.write(header_bytes(amp_header(chip, amp, mk_hdr, raw_file)))
    fout.write(pad_data(stripe.tobytes(order="C")))


def convert(mk_path: Path, nt_path: Path, out_path: Path):
    mk_hdr, mk_data = memmap_raw(mk_path)
    nt_hdr, nt_data = memmap_raw(nt_path)
    if mk_data.shape != (RAW_NAXIS2, RAW_NAXIS1):
        raise ValueError(f"MK has unexpected shape {mk_data.shape}")
    if nt_data.shape != (RAW_NAXIS2, RAW_NAXIS1):
        raise ValueError(f"NT has unexpected shape {nt_data.shape}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp-{os.getpid()}")
    try:
        with tmp_path.open("wb") as fout:
            fout.write(header_bytes(primary_cards(mk_hdr, mk_path, nt_path, out_path)))
            for chip in CHIP_ORDER:
                data = mk_data if CHIP_TO_TAG[chip] == "MK" else nt_data
                raw_file = mk_path.name if CHIP_TO_TAG[chip] == "MK" else nt_path.name
                for amp in range(1, 17):
                    write_amp_hdu(fout, chip, amp, mk_hdr, data, raw_file)
            amp_cols, xtalk_cols, volt_cols, tel_cols = table_defs()
            fout.write(bintable_bytes("AMPINFO", amp_cols, ampinfo_rows(mk_path, nt_path), [
                card("NAMP", 64, "number of amplifier rows"),
                card("GEOMVER", GEOMETRY_VERSION, "geometry definition version"),
                card("RAWGROUP", "MKNT", "raw grouping"),
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_summary(out_path: Path):
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

Verified Archon raw geometry:
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
    args = parser.parse_args()

    inp = Path(args.input).resolve()
    mk, nt = find_pair(inp)
    if not mk.exists():
        raise FileNotFoundError(mk)
    if not nt.exists():
        raise FileNotFoundError(nt)
    mk_hdr, _ = read_primary_header(mk)
    out = Path(args.output).resolve() if args.output else default_output_name(mk, Path(args.outdir).resolve(), mk_hdr)
    if out.exists() and not args.force:
        raise FileExistsError(f"Output exists: {out}; use -f to overwrite")
    convert(mk, nt, out)
    summary = write_summary(out)
    print(out)
    print(summary)
    if args.gzip:
        print(gzip_file(out))


if __name__ == "__main__":
    main()

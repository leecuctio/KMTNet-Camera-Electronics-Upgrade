#!/usr/bin/env python3
"""
KMT-CEU legacy 32-amplifier MEF -> new 64-amplifier L0 MEF mockup converter.

Purpose
-------
The new KMT-CEU electronics (2 x STA Archon controllers) read each science CCD
with 16 amplifiers = 8 vertical strips x 2 readout ends (TOP/BOT), producing the
64-amplifier L0 "amp raw" MEF product defined by

    kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py  (v2.1.1)
    KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md
    KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx

Until real 64-amp Archon frames exist we still need many mock 64-amp MEF images
to build and exercise the pre-processing / data-reduction pipeline. This tool
manufactures such mock images from *real* legacy data: a legacy 32-amplifier MEF
(old KMTNet camera, e.g. kmtc.20260630.011092.fits) in which each CCD is read by
8 amplifiers, one per full-height strip.

Legacy 32-amp layout (per amplifier extension)
    NAXIS1 = 1211, NAXIS2 = 9232
    PRESEC  = [1:27,   1:9232]   (27 prescan cols, dropped)
    DATASEC = [28:1179, 1:9232]  (1152 active cols)
    BIASSEC = [1180:1211,1:9232] (32 serial overscan cols)
    -> 8 strips/CCD x 4 CCDs (M,K,N,T) = 32 amplifiers.

New 64-amp mock layout (per amplifier extension)
    NAXIS1 = 1200, NAXIS2 = 4616
    DATASEC = [1:1152,1:4616]    (active pixels - ALL 64 amps, uniform)
    BIASSEC = [1153:1200,1:4616] (local overscan - ALL 64 amps, uniform)
    -> 16 amplifiers/CCD (8 strips x TOP/BOT) x 4 CCDs = 64 amplifiers.

    NOTE (v1.1): the CEU ICD puts the overscan on the readout-node side, i.e.
    left of the data for amps 5-8 / 13-16. For this mockup every amp is packed
    DATA_LEFT instead, so the same star has the same in-amp (x, y) position in
    all 64 amplifier images and the pipeline can assume one uniform geometry.
    The deviation is recorded in AMPPACK='DATA_LEFT' and GEOMVER='...-mockU1'.

Coordinates carried over from the legacy file (v1.1)
    - Approximate per-amp WCS is inherited from the legacy per-strip WCS by a
      pure CRPIX shift: CRPIX1_new = CRPIX1_legacy - 27 (prescan removed),
      CRPIX2_new = CRPIX2_legacy - 4616 for TOP amps (0 for BOT). CRVAL / CD /
      CTYPE are copied unchanged, so the ds9 sky readout of a star matches the
      legacy display exactly (final astrometry still comes later, at L1).
    - IRAF physical coordinates: LTV1=0, LTV2=-4616 (TOP) / 0 (BOT), LTM=1,
      so ds9 "physical" (x, y) of a star is identical in both files:
      x = CCD-strip column 1..1152, y = CCD row 1..9232.
    - DTV/DTM map image pixels to the full KMTNet mosaic (matches DETSEC).

Conversion (physically motivated mockup)
    For each CCD strip, the legacy full-height amp image (9232 rows) is split into
    a TOP half (CCD rows 4617:9232) and a BOT half (CCD rows 1:4616), emulating the
    new "read each strip from both ends" architecture. Each half keeps its real
    1152 active columns and real serial-overscan pixels; the 48-column new overscan
    is built from the 32 real legacy overscan columns (last 16 mirrored) so the
    overscan carries a realistic bias level and read noise for overscan-correction
    testing.

    Strips are matched to new amplifiers by CCD geometry (CCDSEC), NOT by the amp
    label, because on K and N chips the legacy numbering runs opposite to the strip
    position (legacy K01 = CCD strip 8, K08 = strip 1, likewise N).

Keyword policy (per user request)
    - Every keyword that can be filled is filled.
      * Observation / site / telescope / exposure / focus / dome / thermal keywords
        are taken from the legacy primary header.
      * New-format structural, geometry, detector and electronics keywords are
        emitted exactly as the authoritative 64-amp converter defines them, so the
        mock file is HDU-for-HDU and keyword-for-keyword a valid CEU L0 product.
      * Per-amp GAIN / RDNOISE are populated from the legacy strip values (shared by
        the TOP/BOT halves) so gain/read-noise pipeline steps have usable numbers.
    - Keywords that genuinely cannot be filled for this conversion are set to "na":
      * Archon raw-frame provenance that does not exist for a legacy conversion
        (MKFILE, NTFILE, NUMFILES, RAWGROUP, RAWNAX1, RAWNAX2, MIDOVSCY, and the
        per-amp RAWFILE / RAWDATA / RAWBIAS; numeric raw-frame bounds -> -1).
      * Any observation keyword absent from the legacy header (empty -> "na").
    - Honest mockup provenance is recorded (ORIGFILE, ORIGFMT, CONVPROG, CONVDATE,
      MOCKDATA, CONVNOTE ...).

Output HDU layout (identical to the real 64-amp L0 product)
    PRIMARY
    M01T..M08T, M01B..M08B
    K01T..K08T, K01B..K08B
    N01T..N08T, N01B..N08B
    T01T..T08T, T01B..T08B
    AMPINFO, XTALKINFO, VOLTINFO, TELEMETRY
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits

# Import the authoritative 64-amp converter to reuse its geometry, header and
# binary-table builders so the mockup is structurally identical to real output.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1 as ceu  # noqa: E402

SOFTWARE_VERSION = "legacy32-to-l0amp-v1.1"
CONVPROG = f"kmt_ceu_legacy32_to_l0amp_mef_{SOFTWARE_VERSION}"

NA = "na"                 # string sentinel for un-fillable keywords
NA_INT = -1               # numeric sentinel for un-fillable integer columns

LEGACY_STRIP_COLS = ceu.AMP_DATA_COLS        # 1152 active columns per strip
LEGACY_HALF_ROWS = ceu.ACTIVE_HALF_ROWS      # 4616 rows per TOP/BOT half
CCD_ROWS = ceu.CCD_ROWS                      # 9232 rows per full strip

# v1.1 uniform mock packing: data always left, overscan always right, so a star
# has the same in-amp (x, y) in every amplifier image (deviates from the ICD,
# which puts the overscan on the readout-node side for amps 5-8/13-16).
DATA_X0, DATA_X1 = 1, ceu.AMP_DATA_COLS               # [1:1152]
BIAS_X0, BIAS_X1 = ceu.AMP_DATA_COLS + 1, ceu.RAW_XTILE  # [1153:1200]
DATASEC_UNIFORM = f"[{DATA_X0}:{DATA_X1},1:{LEGACY_HALF_ROWS}]"
BIASSEC_UNIFORM = f"[{BIAS_X0}:{BIAS_X1},1:{LEGACY_HALF_ROWS}]"
AMPPACK = "DATA_LEFT"
MOCK_GEOMVER = f"{ceu.GEOMETRY_VERSION}-mockU1"

# Per-strip WCS keywords inherited from the legacy extension headers.
WCS_KEYS = ("CTYPE1", "CTYPE2", "CRVAL1", "CRVAL2", "CRPIX1", "CRPIX2",
            "CD1_1", "CD1_2", "CD2_1", "CD2_2")

# Primary keywords that describe a real Archon raw frame and therefore cannot be
# filled when the source is a legacy 32-amp MEF.
PRIMARY_NA = {"MKFILE", "NTFILE", "NUMFILES", "RAWGROUP", "RAWNAX1", "RAWNAX2", "MIDOVSCY"}
# Amp/AMPINFO keywords tied to the (non-existent) Archon raw frame.
AMP_NA = {"RAWFILE", "RAWDATA", "RAWBIAS", "RAWNAX1", "RAWNAX2", "MIDOVSCY"}


# --------------------------------------------------------------------------- #
# Small helpers for editing module-generated FITS cards
# --------------------------------------------------------------------------- #
def parse_card(cbytes: bytes):
    """Return (key, value, comment, raw_str) for a module-generated 80-byte card."""
    s = cbytes.decode("ascii", errors="replace")
    key = s[:8].strip()
    if key in ("COMMENT", "HISTORY", "END", "") or s[8:10] != "= ":
        return key, None, None, s
    valpart, comment = ceu.split_fits_value_comment(s[10:])
    value = ceu.parse_fits_value(valpart)
    return key, value, (comment.strip() or None), s


def transform_cards(cards, force_na: set, gain=None, rdnoise=None):
    """Apply the keyword policy to a list of module-generated card bytes.

    - keys in `force_na`        -> value "na" (comment preserved)
    - empty-string values       -> value "na" (no source in legacy header)
    - GAIN / RDNOISE            -> legacy strip value (if provided)
    """
    out = []
    for c in cards:
        key, value, comment, _ = parse_card(c)
        if value is None:            # COMMENT / HISTORY / END -> keep verbatim
            out.append(c)
            continue
        if key in force_na:
            out.append(ceu.card(key, NA, comment))
        elif key == "GAIN" and gain is not None:
            out.append(ceu.card(key, float(gain), "amp gain [e-/ADU] (legacy 32-amp value)"))
        elif key == "RDNOISE" and rdnoise is not None:
            out.append(ceu.card(key, float(rdnoise), "read noise [e-] (legacy 32-amp value)"))
        elif isinstance(value, str) and value == "":
            out.append(ceu.card(key, NA, comment))
        else:
            out.append(c)
    return out


def override_cards(cards, repl: dict):
    """Replace the value/comment of existing cards; repl maps key -> (value, comment)."""
    out = []
    for c in cards:
        key = c[:8].decode("ascii", errors="replace").strip()
        if key in repl:
            v, comment = repl[key]
            out.append(ceu.card(key, v, comment))
        else:
            out.append(c)
    return out


def insert_after(cards, anchor_key: str, new_cards):
    """Insert `new_cards` right after the first card whose key == anchor_key."""
    out = []
    inserted = False
    for c in cards:
        out.append(c)
        if not inserted and c[:8].decode("ascii", errors="replace").strip() == anchor_key:
            out.extend(new_cards)
            inserted = True
    if not inserted:
        out.extend(new_cards)
    return out


# --------------------------------------------------------------------------- #
# Legacy MEF ingestion
# --------------------------------------------------------------------------- #
_SEC_RE = re.compile(r"\[(\d+):(\d+),(\d+):(\d+)\]")


def parse_sec(text: str):
    m = _SEC_RE.match(str(text).replace(" ", ""))
    if not m:
        raise ValueError(f"cannot parse section {text!r}")
    return tuple(int(x) for x in m.groups())


def strip_from_ccdsec(ccdsec_text: str) -> int:
    x0, _x1, _y0, _y1 = parse_sec(ccdsec_text)
    return (x0 - 1) // LEGACY_STRIP_COLS + 1


def read_legacy(path: Path):
    """Read a legacy 32-amp MEF.

    Returns
        primary_hdr : uppercase {keyword: value} dict of the primary header
        strips      : {chip: {strip_id: {'active','overscan','gain','rdnoise'}}}
    """
    strips: dict[str, dict[int, dict]] = {c: {} for c in ceu.CHIP_ORDER}
    with fits.open(path, do_not_scale_image_data=True, memmap=True) as hdul:
        ph = hdul[0].header
        primary_hdr = {}
        for key in ph.keys():
            if not key or key in ("COMMENT", "HISTORY", ""):
                continue
            primary_hdr[key.upper()] = ph[key]

        for hdu in hdul[1:]:
            ext = str(hdu.header.get("EXTNAME", "")).strip()
            if len(ext) < 3 or ext[0] not in strips:
                continue
            chip = ext[0]
            hdr = hdu.header
            strip = strip_from_ccdsec(hdr["CCDSEC"])
            dx0, dx1, _dy0, _dy1 = parse_sec(hdr["DATASEC"])
            bx0, bx1, _by0, _by1 = parse_sec(hdr["BIASSEC"])
            data = np.asarray(hdu.data, dtype=">i2")   # raw int16 stored values
            if data.shape != (CCD_ROWS, hdr["NAXIS1"]):
                raise ValueError(f"{ext}: unexpected shape {data.shape}")
            active = data[:, dx0 - 1:dx1]              # (9232, 1152)
            overscan = data[:, bx0 - 1:bx1]            # (9232, 32)
            if active.shape[1] != LEGACY_STRIP_COLS:
                raise ValueError(f"{ext}: DATASEC width {active.shape[1]} != {LEGACY_STRIP_COLS}")
            def _fval(k, default=0.0):
                try:
                    return float(hdr.get(k, default))
                except (TypeError, ValueError):
                    return default
            wcs = {k: hdr[k] for k in WCS_KEYS if k in hdr}
            strips[chip][strip] = {
                "active": np.ascontiguousarray(active),
                "overscan": np.ascontiguousarray(overscan),
                "gain": _fval("GAIN"),
                "rdnoise": _fval("RDNOISE"),
                "legacy_ext": ext,
                "xoff": dx0 - 1,        # legacy prescan columns before the data (27)
                "wcs": wcs,             # legacy per-strip WCS (full-strip image coords)
            }

    for chip in ceu.CHIP_ORDER:
        missing = [s for s in range(1, 9) if s not in strips[chip]]
        if missing:
            raise ValueError(f"CCD {chip}: missing legacy strips {missing}")
    return primary_hdr, strips


def build_overscan48(overscan_half: np.ndarray) -> np.ndarray:
    """Build a 48-column new overscan block from a 32-column legacy overscan half.

    The 32 real overscan columns are kept; the remaining 16 columns are the
    trailing 16 legacy columns mirrored, so the block is continuous and made
    entirely of real bias-level pixels (deterministic, no RNG).
    """
    n_have = overscan_half.shape[1]                 # 32
    n_need = ceu.OVERSCAN_X                          # 48
    if n_have >= n_need:
        return np.ascontiguousarray(overscan_half[:, :n_need])
    pad = n_need - n_have                            # 16
    mirror = overscan_half[:, n_have - pad:n_have][:, ::-1]
    return np.ascontiguousarray(np.concatenate([overscan_half, mirror], axis=1))


def build_amp_image(strip_info: dict, amp: int) -> np.ndarray:
    """Assemble one new 64-amp image (4616 x 1200) from a legacy strip half.

    v1.1: uniform DATA_LEFT packing — active pixels at [1:1152] and overscan at
    [1153:1200] for every amplifier, so the same star lands on the same in-amp
    (x, y) in all 64 amplifier images.
    """
    active_full = strip_info["active"]              # (9232, 1152) int16, CCD orientation
    os_full = strip_info["overscan"]                # (9232, 32)
    if amp <= 8:                                    # TOP end -> CCD rows 4617:9232
        rows = slice(LEGACY_HALF_ROWS, CCD_ROWS)
    else:                                           # BOT end -> CCD rows 1:4616
        rows = slice(0, LEGACY_HALF_ROWS)
    active_half = active_full[rows, :]              # (4616, 1152)
    os_half = os_full[rows, :]                      # (4616, 32)
    os48 = build_overscan48(os_half)                # (4616, 48)

    img = np.empty((LEGACY_HALF_ROWS, ceu.RAW_XTILE), dtype=">i2")
    img[:, DATA_X0 - 1:DATA_X1] = active_half
    img[:, BIAS_X0 - 1:BIAS_X1] = os48
    return img


# --------------------------------------------------------------------------- #
# Header construction
# --------------------------------------------------------------------------- #
def provenance_cards(legacy_path: Path, primary_hdr: dict, now: str):
    legacy_det = str(primary_hdr.get("READOUT", NA)).strip() or NA
    return [
        ceu.card("COMMENT", "Mockup provenance: built from a legacy 32-amplifier MEF"),
        ceu.card("MOCKDATA", True, "pixels are real legacy bias, geometry is mock 64-amp"),
        ceu.card("ORIGFILE", legacy_path.name, "source legacy MEF file"),
        ceu.card("ORIGFMT", "32AMP_MEF", "source product format"),
        ceu.card("ORIGNAMP", 32, "amplifiers in source product"),
        ceu.card("ORIGCAM", "KMTNet legacy camera", "source camera/electronics"),
        ceu.card("ORIGRDO", legacy_det, "legacy READOUT amplifier set"),
        ceu.card("CONVPROG", CONVPROG, "legacy->64amp mockup converter"),
        ceu.card("CONVDATE", now, "UTC time of mockup conversion"),
        ceu.card("CONVNOTE", "strip split TOP/BOT; uniform data[1:1152]+os[1153:1200]"),
        ceu.card("AMPPACK", AMPPACK, "mock packing: data [1:1152], overscan [1153:1200]"),
        ceu.card("GEOMVER", MOCK_GEOMVER, "geometry version (mock uniform packing)"),
    ]


def make_primary(legacy_path: Path, primary_hdr: dict, out_path: Path):
    dummy = Path(NA)
    cards = ceu.primary_cards(primary_hdr, dummy, dummy, out_path)
    cards = transform_cards(cards, PRIMARY_NA)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "")
    # override generator identity, then splice in mockup provenance
    cards = [ceu.card("CREATOR", CONVPROG, "MEF creation program") if c[:8].decode().strip() == "CREATOR" else c
             for c in cards]
    cards = [ceu.card("PIPEVER", CONVPROG, "converter/pipeline version") if c[:8].decode().strip() == "PIPEVER" else c
             for c in cards]
    cards = insert_after(cards, "CREATOR", provenance_cards(legacy_path, primary_hdr, now))
    return ceu.header_bytes(cards)


def make_amp_header(chip: str, amp: int, primary_hdr: dict, strip_info: dict):
    cards = ceu.amp_header(chip, amp, primary_hdr, raw_file=NA)
    cards = transform_cards(cards, AMP_NA, gain=strip_info["gain"], rdnoise=strip_info["rdnoise"])

    # TOP amps hold legacy CCD rows 4617..9232 as image rows 1..4616.
    y_shift = LEGACY_HALF_ROWS if amp <= 8 else 0
    x_shift = strip_info.get("xoff", 27)            # legacy prescan columns

    # v1.1 uniform DATA_LEFT packing (same star -> same in-amp x,y in all amps)
    repl = {
        "DATASEC": (DATASEC_UNIFORM, "active data section (uniform mock packing)"),
        "BIASSEC": (BIASSEC_UNIFORM, "local overscan section (uniform mock packing)"),
        "TRIMSEC": (DATASEC_UNIFORM, "trimmed data section (uniform mock packing)"),
    }

    # Approximate WCS inherited from the legacy per-strip WCS by a CRPIX shift:
    #   x_legacy = x_mock + prescan(27),  y_legacy = y_mock + 4616 (TOP) / 0 (BOT)
    w = strip_info.get("wcs", {})
    if all(k in w for k in WCS_KEYS):
        repl.update({
            "CTYPE1": (str(w["CTYPE1"]), "coordinate type"),
            "CTYPE2": (str(w["CTYPE2"]), "coordinate type"),
            "CRVAL1": (float(w["CRVAL1"]), "reference RA [deg] (from legacy WCS)"),
            "CRVAL2": (float(w["CRVAL2"]), "reference DEC [deg] (from legacy WCS)"),
            "CRPIX1": (float(w["CRPIX1"]) - x_shift, "ref pixel (legacy CRPIX1 - prescan)"),
            "CRPIX2": (float(w["CRPIX2"]) - y_shift, "ref pixel (legacy CRPIX2 - Y shift)"),
            "CD1_1": (float(w["CD1_1"]), "coordinate transform matrix (legacy)"),
            "CD1_2": (float(w["CD1_2"]), "coordinate transform matrix (legacy)"),
            "CD2_1": (float(w["CD2_1"]), "coordinate transform matrix (legacy)"),
            "CD2_2": (float(w["CD2_2"]), "coordinate transform matrix (legacy)"),
        })
    cards = override_cards(cards, repl)

    # IRAF physical / mosaic transforms so ds9 physical coords match the legacy
    # display: physical x = strip column 1..1152, physical y = CCD row 1..9232.
    dx1, _dx2, dy1, _dy2 = ceu.detsec(chip, amp)
    extra = [
        ceu.card("AMPPACK", AMPPACK, "mock packing: data [1:1152], overscan [1153:1200]"),
        # NOTE: no EQUINOX/RADESYS here, exactly like the legacy extensions, so
        # WCS libraries interpret both files in the same (default ICRS) frame.
        ceu.card("LTV1", 0.0, "CCD-strip to image transform (x)"),
        ceu.card("LTV2", float(-y_shift), "CCD to image transform (y; TOP half shifted)"),
        ceu.card("LTM1_1", 1.0, "CCD to image transform"),
        ceu.card("LTM1_2", 0.0, "CCD to image transform"),
        ceu.card("LTM2_1", 0.0, "CCD to image transform"),
        ceu.card("LTM2_2", 1.0, "CCD to image transform"),
        ceu.card("DTV1", float(dx1 - 1), "image to detector mosaic transform (x)"),
        ceu.card("DTV2", float(dy1 - 1), "image to detector mosaic transform (y)"),
        ceu.card("DTM1_1", 1.0, "image to detector mosaic transform"),
        ceu.card("DTM1_2", 0.0, "image to detector mosaic transform"),
        ceu.card("DTM2_1", 0.0, "image to detector mosaic transform"),
        ceu.card("DTM2_2", 1.0, "image to detector mosaic transform"),
    ]
    cards = insert_after(cards, "WCSDIM", extra)
    return ceu.header_bytes(cards)


# --------------------------------------------------------------------------- #
# Binary tables
# --------------------------------------------------------------------------- #
def make_ampinfo(strips: dict):
    rows = ceu.ampinfo_rows(Path(NA), Path(NA))
    by_ext = {r["EXTNAME"]: r for r in rows}
    for chip in ceu.CHIP_ORDER:
        for amp in range(1, 17):
            ext = ceu.extname_for(chip, amp)
            r = by_ext[ext]
            info = strips[chip][ceu.strip_id(amp)]
            r["GAIN"] = info["gain"]
            r["RDNOISE"] = info["rdnoise"]
            r["RAWFILE"] = NA
            r["RAWDATA"] = NA
            r["RAWBIAS"] = NA
            for k in ("RAWX0", "RAWX1", "RAWY0", "RAWY1"):
                r[k] = NA_INT
            # v1.1 uniform DATA_LEFT packing (must match the image headers)
            r["DATASEC"] = DATASEC_UNIFORM
            r["BIASSEC"] = BIASSEC_UNIFORM
            r["TRIMSEC"] = DATASEC_UNIFORM
    amp_cols, _x, _v, _t = ceu.table_defs()
    return ceu.bintable_bytes("AMPINFO", amp_cols, rows, [
        ceu.card("NAMP", 64, "number of amplifier rows"),
        ceu.card("GEOMVER", MOCK_GEOMVER, "geometry version (mock uniform packing)"),
        ceu.card("AMPPACK", AMPPACK, "mock packing: data [1:1152], overscan [1153:1200]"),
        ceu.card("RAWGROUP", NA, "raw grouping (mock: no Archon raw)"),
    ])


def make_other_tables():
    _a, xtalk_cols, volt_cols, tel_cols = ceu.table_defs()
    xtalk = ceu.bintable_bytes("XTALKINFO", xtalk_cols, ceu.xtalk_rows(), [
        ceu.card("NXTALK", 4096, "number of crosstalk matrix rows"),
        ceu.card("XTALKVER", "UNMEASURED", "placeholder crosstalk version"),
        ceu.card("XTALKCAL", False, "replace coefficients after calibration"),
    ])
    volt = ceu.bintable_bytes("VOLTINFO", volt_cols, ceu.volt_rows(), [
        ceu.card("BIASVER", "UNKNOWN", "bias setting version"),
        ceu.card("CLKVER", "UNKNOWN", "clock setting version"),
        ceu.card("VOLTSTAT", "UNKNOWN", "voltage telemetry status"),
    ])
    tel = ceu.bintable_bytes("TELEMETRY", tel_cols, ceu.telemetry_rows(), [
        ceu.card("NCTRL", 2, "number of science controllers"),
        ceu.card("TELSTAT", "UNKNOWN", "telemetry status"),
    ])
    return xtalk, volt, tel


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


def convert(legacy_path: Path, out_path: Path):
    primary_hdr, strips = read_legacy(legacy_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp-{os.getpid()}")
    try:
        with tmp_path.open("wb") as fout:
            fout.write(make_primary(legacy_path, primary_hdr, out_path))
            for chip in ceu.CHIP_ORDER:
                for amp in range(1, 17):
                    info = strips[chip][ceu.strip_id(amp)]
                    fout.write(make_amp_header(chip, amp, primary_hdr, info))
                    fout.write(ceu.pad_data(build_amp_image(info, amp).tobytes(order="C")))
            fout.write(make_ampinfo(strips))
            for tbl in make_other_tables():
                fout.write(tbl)
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
        description="Convert legacy 32-amp KMTNet MEF into a mock 64-amp KMT-CEU L0 MEF")
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
        hdr, _strips = None, None
        # read only the primary header quickly for naming
        with fits.open(legacy, memmap=True) as h:
            phdr = {k.upper(): h[0].header[k] for k in h[0].header.keys()
                    if k and k not in ("COMMENT", "HISTORY", "")}
        out = Path(args.output).resolve() if args.output else default_output_name(legacy, phdr, outdir)
        if out.exists() and not args.force:
            raise FileExistsError(f"Output exists: {out}; use -f to overwrite")
        convert(legacy, out)
        print(f"{legacy.name} -> {out}")


if __name__ == "__main__":
    main()

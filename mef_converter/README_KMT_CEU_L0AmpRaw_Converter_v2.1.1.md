# KMT-CEU L0 64-Amplifier Raw MEF Converter v2.1.1

Final check date: 2026-06-22

## Purpose

This package contains the converter for the KMT-CEU science camera output produced by two STA Archon controllers. It converts the verified MK/NT Archon raw FITS pair into a primary L0 64-amplifier raw MEF product.

The generated L0 product preserves each amplifier image separately, including local overscan pixels, so amplifier-level overscan, bias, gain, read-noise, crosstalk, bias-jump, and boundary-source effects can be handled before CCD-level image assembly.

## Main Script

```text
kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py
```

Internal version metadata:

```text
CREATOR = kmt_ceu_l0amp_mknt2mef_v2.1.1
PRODVER = v2.1.1
PIPEVER = kmt_ceu_l0amp_mknt2mef-v2.1.1
GEOMVER = CEU-L0AMP-v2.1
```

## Input Files

The converter expects one file from a matching MK/NT pair. If the MK file is supplied, the NT file is found automatically by filename, and vice versa.

```text
KMTN.YYYYMMDD.NNNNNN.MK.fits  -> M, K chips
KMTN.YYYYMMDD.NNNNNN.NT.fits  -> N, T chips
```

Verified sample pair:

```text
KMTN.20260116.000001.MK.fits
KMTN.20260116.000001.NT.fits
```

## Output MEF Layout

```text
PRIMARY
M01T ... M08T, M01B ... M08B
K01T ... K08T, K01B ... K08B
N01T ... N08T, N01B ... N08B
T01T ... T08T, T01B ... T08B
AMPINFO
XTALKINFO
VOLTINFO
TELEMETRY
```

Expected HDU count:

```text
69 = PRIMARY + 64 amplifier image HDUs + 4 binary table HDUs
```

## Run Command

From the project directory:

```bash
python3 mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  KMTN.20260116.000001.MK.fits \
  -o kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits \
  -f --gzip
```

One-line version:

```bash
python3 mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py KMTN.20260116.000001.MK.fits -o kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits -f --gzip
```

Options:

| Option | Meaning |
| --- | --- |
| `-o`, `--output` | Output L0 MEF FITS path |
| `-d`, `--outdir` | Output directory when `--output` is omitted |
| `-f`, `--force` | Overwrite an existing output file |
| `--gzip` | Also create a `.fits.gz` compressed copy and SHA256 file |

## Final Verification Result

The v2.1.1 converter was run on the verified sample MK/NT pair. The generated output passed strict Astropy verification.

```text
verify ok
HDU count = 69
first HDUs = PRIMARY, M01T, M02T, M03T, M04T, M05T
last HDUs = AMPINFO, XTALKINFO, VOLTINFO, TELEMETRY
M01T shape = (4616, 1200)
AMPINFO rows = 64
XTALKINFO rows = 4096
VOLTINFO rows = 9
TELEMETRY rows = 2
gzip -t = ok
```

Generated sample files in the working directory:

```text
kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits
kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz
kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.summary.txt
kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz.sha256.txt
```

Current gzip SHA256:

```text
7a55e7573eac899cd4b3c50b5dc747efe362a49bef505c1f0f90f53f68760289  kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz
```

The large raw and generated FITS data products are not included in the code release ZIP.

## v2.1.1 Final Changes

- Uses `datetime.timezone.utc` for Python 3.9/3.10 compatibility.
- Writes FITS logical card values in standard right-aligned format.
- Keeps software/product version separate from geometry version.
- Parses FITS card comments without splitting `/` characters inside quoted string values.
- Writes output through a temporary file, then atomically replaces the final path after successful conversion.
- Preserves the CEU L0 policy: no chip-dependent OSU-style flip at the L0 packing stage.

## Remaining Calibration Notes

- `GAIN`, `RDNOISE`, `SATURAT`, `LINMAX`, `XTALKINFO`, `VOLTINFO`, and `TELEMETRY` values are placeholders until measured calibration and Archon telemetry values are available.
- `READDIR` is currently encoded as TOP=`-Y`, BOT=`+Y`; final direction should be confirmed with flat/star sequence tests.
- When reading scaled image data with Astropy, use `memmap=False` or `do_not_scale_image_data=True` because the image HDUs include `BZERO/BSCALE`.


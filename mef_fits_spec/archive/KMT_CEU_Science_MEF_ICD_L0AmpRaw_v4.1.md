# KMT-CEU Science MEF ICD - L0 64-Amplifier Raw Product

Archon MK/NT raw verified, MKNT chip order, amp-level primary raw archive

**v4.1 | 2026-08-10** (v4.0: 2026-06-19)

> 이 md 파일은 `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.docx`와 동일 내용의 diff 가능한 기준본이다. 둘은 항상 같은 개정으로 갱신한다.

| Item | Value |
| --- | --- |
| Document purpose | Define the KMT-CEU Archon science raw MEF interface and L0/L1 product policy. |
| Primary L0 raw product | 64 amplifier image extensions with local overscan retained. |
| Secondary L1 product | Calibrated CCD-level SCI_M, SCI_K, SCI_N, SCI_T after amp-level calibration. |
| Raw file naming | `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK\|NT>.fits`, `<SITE>` in {KMTC, KMTS, KMTA, KMTT} (v4.1, D-011) |
| Verified raw files | `KMTN.20260116.000001.MK.fits` and `KMTN.20260116.000001.NT.fits` (pre-D-011 naming; verification record) |
| Official chip order | M, K, N, T |
| Raw grouping | MK -> M,K; NT -> N,T |

## 1. Executive decision update

This revision updates the science MEF policy from a CCD-level raw product to a 64-amplifier L0 raw product. The change is motivated by data-reduction requirements: amplifier-level offset, overscan, gain, read-noise, crosstalk, bias-jump, and boundary-source effects must be corrected before constructing full CCD images.

- The primary raw archive and calibration input shall be L0 64-amplifier MEF.
- Each amplifier extension shall preserve its local active pixels and local overscan pixels.
- CCD-level SCI_M, SCI_K, SCI_N, and SCI_T images shall be generated only after amplifier-level calibration.
- The MKNT order is retained because it follows the verified Archon controller grouping and existing converter flow.

| Product level | MEF image layout | Main purpose | Status |
| --- | --- | --- | --- |
| L0 Raw | 64 amp extensions + binary tables | Raw archive, overscan/bias/gain/crosstalk calibration, debugging | Primary raw product |
| L1 Calibrated | SCI_M, SCI_K, SCI_N, SCI_T + calibration history | Calibrated CCD images for astrometry, DIA, photometry | Derived product |
| L2 Science | Difference images, catalogs, light curves | Science analysis outputs | Pipeline product |

## 2. Verified Archon raw geometry

The actual Archon test files show a two-file science raw structure. The MK file carries the M and K chip data and the observation metadata. The NT file carries the N and T chip data.

**Changed in v4.1 (OI-8):** v4.0 stated, based on the verification-time sample, that the NT file "may contain only a minimal FITS header". This is no longer permitted. **Both MK and NT files shall carry the complete required header set** defined in `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` chapter 5. Rationale: (1) the NT file must be interpretable on its own to be a complete archive asset, (2) controller 2 identity/telemetry exists only in the NT header, and (3) pair-consistency checks require the same keys on both sides.

| Raw file | Contains chips | Role |
| --- | --- | --- |
| `<SITE>.YYYYMMDD.NNNNNN.MK.fits` | M, K | Master metadata source and pixel data source |
| `<SITE>.YYYYMMDD.NNNNNN.NT.fits` | N, T | Pixel data source; full required header (v4.1, was "may be minimal" in v4.0) |

| Quantity | Verified value | Interpretation |
| --- | --- | --- |
| RAWNAX1 | 19200 | 16 x 1200 pixel amp tiles in X |
| RAWNAX2 | 9400 | 4616 lower active rows + 168 middle Y overscan + 4616 upper active rows |
| RAWXTILE | 1200 | 1152 active columns + 48 overscan columns |
| AMPDATA | 1152 | Active columns per amplifier tile |
| OVERSCNX | 48 | Local X overscan columns per amplifier tile |
| PRESCANX | 0 | No local X prescan in verified Archon raw |
| MIDOVSCY | 168 | Middle Y overscan rows between lower and upper active halves |

### 2.1 Raw file naming (v4.1, D-011)

The raw pair filename prefix is a **4-letter uppercase site code**, replacing the fixed literal `KMTN` of v4.0. The site code equals the TC telemetry `TELID` convention, so it is an extension of an existing identifier, not a new one.

```text
<SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits
<SITE>.<YYYYMMDD>.<NNNNNN>.NT.fits
```

| `<SITE>` | Site | `OBSERVAT` header | L0 MEF prefix |
| --- | --- | --- | --- |
| `KMTC` | CTIO | `CTIO` | `kmtc` |
| `KMTS` | SAAO | `SAAO` | `kmts` |
| `KMTA` | SSO | `SSO` | `kmta` |
| `KMTT` | Testbed (lab, demonstration, full rehearsal) | `TESTBED` | `kmtt` |

- `<YYYYMMDD>`: 8 digits, observing-night date.
- `<NNNNNN>`: exposure sequence number, **6 digits, zero-padded**, identical on both pair members.
- The `.MK.fits` / `.NT.fits` suffixes are case-sensitive; the converter pairs files by these strings.
- The filename `<SITE>` must agree with the `OBSERVAT` header; the converter (v2.2.0) derives the output MEF prefix from the filename site code and raises an error on mismatch.
- The `Wrote` logical names sent to OBSAgent keep the legacy `KMTN<chip>` form and are **not** affected by this change (DECISION_LOG D-010/D-011).
- Rationale, mapping authority, and failure modes: `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` section 2.3 and DECISION_LOG D-011.

## 3. Chip order and amplifier numbering

The official science chip order for this ICD is M, K, N, T. This follows the raw file grouping and the converter loop structure.

| Chip | Raw source | Global amplifier range | Image extension order |
| --- | --- | --- | --- |
| M | MK | 1-16 | M01T..M08T, M01B..M08B |
| K | MK | 17-32 | K01T..K08T, K01B..K08B |
| N | NT | 33-48 | N01T..N08T, N01B..N08B |
| T | NT | 49-64 | T01T..T08T, T01B..T08B |

```text
CHIPLIST = 'M,K,N,T'
RAWGROUP = 'MKNT'
M: AMPID  1-16
K: AMPID 17-32
N: AMPID 33-48
T: AMPID 49-64
```

## 4. Legacy OSU orientation vs CEU Archon orientation

In the legacy OSU electronics, M/T and K/N were historically treated as different orientation groups. In the CEU Archon system, all science CCDs are read using the same top/bottom dual-end scheme, and no chip-dependent OSU-style image flip is applied at L0 packing.

| Item | Legacy OSU camera | KMT-CEU Archon L0 |
| --- | --- | --- |
| Chip-dependent flip | M/T and K/N orientation groups existed | No chip-dependent flip; CHIPFLP=None |
| Y-direction distinction | Could depend on chip group | Depends only on TOP/BOT end |
| TOP/BOT mapping | Not the controlling convention | amp 1-8 = TOP, amp 9-16 = BOT for every chip |
| Raw archive requirement | Historical stripe/amp conventions | Explicit 64 amp extensions plus AMPINFO |

## 5. L0 64-amplifier MEF structure

The L0 raw MEF stores each amplifier as an image extension. Each amp image is 1200 x 4616 pixels and includes the 1152 active columns plus 48 local overscan columns. This makes amplifier-level calibration direct and reproducible.

```text
PRIMARY
M01T M02T M03T M04T M05T M06T M07T M08T
M01B M02B M03B M04B M05B M06B M07B M08B
K01T ... K08T, K01B ... K08B
N01T ... N08T, N01B ... N08B
T01T ... T08T, T01B ... T08B
AMPINFO
XTALKINFO
VOLTINFO
TELEMETRY
```

| Extension class | NAXIS1 | NAXIS2 | Content |
| --- | --- | --- | --- |
| Amp image extension | 1200 | 4616 | One amplifier half-strip with active + local overscan |
| AMPINFO | - | - | Authoritative 64-row amplifier geometry/electronics map |
| XTALKINFO | - | - | 64 x 64 crosstalk model table; calibration values may be placeholders initially |
| VOLTINFO | - | - | Bias and clock voltage settings/telemetry |
| TELEMETRY | - | - | Archon controller status and readout telemetry |

## 6. Why L0 must preserve 64 amplifier images

The main driver is not file size but photometric correctness. If raw data are assembled into four CCD images before amp-level calibration, amplifier boundary discontinuities can contaminate PSF/DIA photometry, especially in crowded fields.

- Amplifier offsets must be measured and corrected using the local overscan for each amplifier.
- Gain and read-noise differences are amplifier properties and should be applied before CCD assembly.
- Crosstalk and bias jumps are electronics effects and are best diagnosed in amplifier coordinates.
- If a star crosses an amp boundary, uncorrected offsets can distort the PSF and produce incorrect fluxes.
- Crowded-field DIA and PSF photometry should operate on CCD images only after amp-level corrections are complete.

| Risk in CCD-level raw storage | Consequence | 64-amp L0 mitigation |
| --- | --- | --- |
| Amp boundary hidden inside SCI image | Boundary offset correction becomes indirect and fragile | Boundary is explicit through extension and AMPINFO |
| Local overscan removed or separated | Bias tracking is harder | Overscan remains in each amp extension |
| Source crossing two amps | Wrong PSF/background if offsets differ | Correct each amp first, then assemble CCD image |
| Electronics artifact diagnosis | Root cause may be obscured | Artifact remains associated with AMPID/CTRLID/CHANNEL |

## 7. Amp extension section definitions

The local image coordinate system of each L0 amp extension is 1200 x 4616. DATASEC and BIASSEC are local to this extension, while CCDSEC and DETSEC map the same pixels to CCD and mosaic coordinates.

| Amp group | Local DATASEC | Local BIASSEC | Meaning |
| --- | --- | --- | --- |
| amps 1-4 and 9-12 | [1:1152,1:4616] | [1153:1200,1:4616] | Overscan is on the right side |
| amps 5-8 and 13-16 | [49:1200,1:4616] | [1:48,1:4616] | Overscan is on the left side |

| Amp range | ENDID | CCDSEC Y range | Raw Y source |
| --- | --- | --- | --- |
| 1-8 | TOP | 4617:9232 | 4785:9400 |
| 9-16 | BOT | 1:4616 | 1:4616 |

## 8. AMPINFO binary table

AMPINFO is the authoritative machine-readable map from image extension to raw pixel source, CCD coordinates, detector mosaic coordinates, and electronics channel identity.

| Column group | Representative columns | Purpose |
| --- | --- | --- |
| Identity | EXTNAME, AMPID, CHIPID, STRIPID, ENDID, AMPNAME | Identify each amplifier extension |
| Raw source | RAWFILE, RAWDATA, RAWBIAS | Trace exact source pixels in MK/NT raw files |
| Geometry | CCDSEC, AMPSEC, DETSEC, DATASEC, BIASSEC, TRIMSEC | Map between local, CCD, and detector coordinates |
| Electronics | CTRLID, MODULE, CHANNEL, XTALKGROUP | Map amp to controller and electronics chain |
| Calibration | GAIN, RDNOISE, SATLEVEL, LINMAX | Store amp-level calibration parameters |
| Orientation | CHIPFLP, READDIR, STRIPDIR | Record CEU orientation convention |

## 9. XTALKINFO, VOLTINFO, and TELEMETRY

| Table | Rows in sample | Required role |
| --- | --- | --- |
| XTALKINFO | 4096 | 64 x 64 source-target crosstalk coefficients. Placeholder values are allowed only before calibration. |
| VOLTINFO | instrument dependent | Bias and clock voltage setpoints and measured values. |
| TELEMETRY | 2 | Controller-level firmware, temperature, readtime, status, and error flags. |

## 10. Recommended processing sequence

1. Read L0 64-amplifier MEF and AMPINFO.
2. Apply local overscan correction to each amplifier extension using BIASSEC.
3. Apply amp-level bias, gain, read-noise, linearity, saturation, and bad-pixel masks.
4. Apply crosstalk correction using XTALKINFO after coefficients are calibrated.
5. Inspect amp boundary seams and bias-jump signatures.
6. Assemble calibrated SCI_M, SCI_K, SCI_N, and SCI_T CCD images.
7. Run astrometry, DIA, PSF photometry, catalog matching, and light-curve generation.

## 11. Converter implementation status

The companion converter (`kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`, v2.2.0) implements the L0 64-amplifier MEF structure from verified MK/NT raw images. It creates 64 amp image HDUs and the four required binary tables. Since v2.2.0 it also derives the output prefix from the filename site code and cross-checks it against `OBSERVAT` (section 2.1).

```bash
python kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  KMTA.20260116.000001.MK.fits \
  -o kmta.20260116.000001.ceu.l0amp.mef.fits \
  -f --gzip
```

| Generated file | Description |
| --- | --- |
| kmta.20260116.000001.ceu.l0amp.mef.fits | Full-size L0 64-amplifier MEF sample |
| kmta.20260116.000001.ceu.l0amp.mef.fits.gz | Compressed copy for transfer |
| kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py | Converter script implementing this ICD revision |
| *.summary.txt and *.hdu_verify.txt | Conversion and HDU verification summaries |

## 12. Open items and cautions

- READDIR is encoded as TOP=-Y and BOT=+Y as a placeholder convention; final direction should be confirmed with flat/star sequence tests.
- XTALKINFO values in the current sample are placeholders and must not be used as real calibration coefficients.
- VOLTINFO and TELEMETRY are placeholders when the raw header does not provide actual Archon telemetry; the required raw-header telemetry set is defined in `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` chapter 5.
- L1 CCD-level images should be generated only after amp-level calibration and seam verification.
- The L0 product is larger and more complex than the CCD-level product, but it is more appropriate for precision photometry and long-term reprocessing.
- Sample raw pairs produced before D-011 keep the `KMTN.*` names in verification records; rename both pair members to the site-coded form when re-running them through converter v2.2.0 defaults.

## 13. Revision history

| Version | Date | Change |
| --- | --- | --- |
| v2.0 | 2026-06-19 | Archon MK/NT raw structure verified; MKNT order introduced. |
| v3.0 | 2026-06-19 | Removed chip-dependent legacy flip; common TOP/BOT CEU geometry documented. |
| v4.0 | 2026-06-19 | Changed primary raw MEF product to L0 64-amplifier extensions; CCD-level product demoted to L1 calibrated output. |
| v4.1 | 2026-08-10 | Raw filename prefix changed from literal `KMTN` to site code `<SITE>` in {KMTC, KMTS, KMTA, KMTT} (section 2.1, DECISION_LOG D-011); NT header completeness now required, "minimal NT header" allowance removed (section 2, raw_fits_spec OI-8); converter reference updated to v2.2.0 with filename/`OBSERVAT` cross-check; md master copy of this ICD introduced alongside the docx. |

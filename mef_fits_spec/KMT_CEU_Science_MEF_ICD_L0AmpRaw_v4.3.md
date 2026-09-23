# KMT-CEU Science MEF ICD - L0 64-Amplifier Raw Product

Archon MK/NT raw verified, MKNT chip order, amp-level primary raw archive

**v4.3 | 2026-09-23** (v4.2: 2026-09-04 · v4.1: 2026-08-10 · v4.0: 2026-06-19)

> 이 md 파일은 `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.docx`와 동일 내용의 diff 가능한 기준본이다. 둘은 항상 같은 개정으로 갱신한다.

| Item | Value |
| --- | --- |
| Document purpose | Define the KMT-CEU Archon science raw MEF interface and L0/L1 product policy. |
| Primary L0 raw product | 64 amplifier image extensions with local overscan retained. |
| Secondary L1 product | Calibrated CCD-level SCI_M, SCI_K, SCI_N, SCI_T after amp-level calibration. |
| Raw file naming | `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK\|NT>.fits`, `<SITE>` in {KMTC, KMTS, KMTA, KMTK} (v4.1, D-011; fourth code v4.2, D-017) |
| Verified raw files | `KMTN.20260116.000001.MK.fits` and `KMTN.20260116.000001.NT.fits` (pre-D-011 naming; verification record) |
| Official chip order | M, K, N, T |
| Raw grouping | MK -> M,K; NT -> N,T |
| Product format version | `PRODVER = 'v2.2.0'` (was `v2.1.1`; v4.3, D-023) |
| Geometry version | `GEOMVER = 'CEU-L0AMP-v2.1'` — **unchanged by v4.3**; amp ordering, sections and HDU layout are identical to v4.2 |
| Reference converter | `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` **v2.5.0** (the filename keeps the `_v2_1` suffix; `SOFTWARE_VERSION` states the revision) |

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

**Changed in v4.1 (OI-8):** v4.0 stated, based on the verification-time sample, that the NT file "may contain only a minimal FITS header". This is no longer permitted. **Both MK and NT files shall carry the complete required header set** defined in `raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.13.md` chapter 5 (the v1.2 "Raw FITS Pair Spec" was renamed and superseded at raw spec v1.9; the old file is in `raw_fits_spec/archive/`). Rationale: (1) the NT file must be interpretable on its own to be a complete archive asset, (2) controller 2 identity/telemetry exists only in the NT header, and (3) pair-consistency checks require the same keys on both sides.

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

### 2.1 Raw file naming (v4.1, D-011 · v4.2, D-017)

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
| `KMTK` | KASI (lab, demonstration, full rehearsal) | `KASI` | `kmtk` |

**Changed in v4.2 (D-017):** the fourth site code `KMTT`/`TESTBED` is retired and replaced by `KMTK`/`KASI`. The testbed is a purpose, not a place - the place is KASI, and `ORIGIN` already used `KASI`; `KMTT`'s trailing `T` also read like the T chip next to channel labels. No data was ever produced under the `KMTT` code.

**Changed in v4.3 (D-020):** a site code outside the four is **not** normalized. v4.2 stated that such values are "normalized to `KMTK` with a warning on the acquisition side" (D-017 item 3); DECISION_LOG **D-020** (2026-08-24, later than D-017 and superseding D-015) settled the opposite and raw spec v1.13 section 2.2 carries it: the effective site is set by the ICS configuration line `[node] observatory`, whose vocabulary is the same four values as `OBSERVAT` (`CTIO`, `SSO`, `SAAO`, `KASI`), and **a value outside them refuses to start** rather than falling back. The reason is that the site drags the filename `<SITE>`, the site coordinates, `ORIGIN` and the observing-night boundary with it, so one typo would change the identity of the data wholesale. The TC-supplied `TELID` is used for a cross-check warning only and never influences the filename.

- `<YYYYMMDD>`: 8 digits, observing-night date.
- `<NNNNNN>`: exposure sequence number, **6 digits, zero-padded**, identical on both pair members.
- The `.MK.fits` / `.NT.fits` suffixes are case-sensitive; the converter pairs files by these strings.
- The filename `<SITE>` must agree with the `OBSERVAT` header; the converter (v2.5.0) derives the output MEF prefix from the filename site code and raises an error on mismatch.
- The `Wrote` logical names sent to OBSAgent keep the legacy `KMTN<chip>` form and are **not** affected by this change (DECISION_LOG D-010/D-011).
- Rationale, mapping authority, and failure modes: `raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.13.md` section 2.2 (site-code table) and section 2.3 (exposure numbering and name-collision handling), DECISION_LOG D-011 · D-017.

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

**Unchanged in v4.3:** the HDU inventory and order below are identical to v4.2 — 69 HDUs = PRIMARY + 64 amp IMAGE + 4 BINTABLE, `GEOMVER = 'CEU-L0AMP-v2.1'`. `PRODVER` moves to `v2.2.0` for new keywords and new `AMPINFO` columns only (D-004 manages software/product and geometry versions separately). The extension order and the amp array dimensions do not depend on `IMAGETYP`: the BIAS and OBJECT products verified for this revision have the identical HDU list.

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
| VOLTINFO | - | - | CCD bias/clock rows (no raw source; permanently unmeasured) plus measured Archon controller power-supply rail voltages **and currents** — see section 9 |
| TELEMETRY | - | - | One row per science controller (`NCTRL` rows); measured board temperature plus firmware, readtime, status and error flags — see section 9 |

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

**Note added in v4.3 (D-023 decision 4):** "no chip-dependent flip" is a statement about L0 **packing**, not about residual rotation left in the pixels. Raw spec v1.13 section 4.3 is normative that the raw frame is stored in ascending CCD coordinate on **both** axes — a requirement, not an observation — so the serial/parallel readout direction, the TOP/BOT end, and the e2v A/D image section never reach the stored pixel order, and the 180-degree mounting of K and N is already absorbed by the channel-to-tile ordering. It follows that the seed WCS `CD` matrix (section 7.1) is **identical on all 64 amplifiers and must not be sign-flipped per chip or per readout end**. Flipping it misplaces 32 of the 64 amplifiers.

## 7. Amp extension section definitions

The local image coordinate system of each L0 amp extension is 1200 x 4616. DATASEC and BIASSEC are local to this extension, while CCDSEC and DETSEC map the same pixels to CCD and mosaic coordinates.

The amp numbers in this section are `AMPSEQ` (1-16 **within a chip**), not the global `AMPID` of section 3. The rule is identical on all four chips.

| Amp group (`AMPSEQ`) | Local DATASEC | Local BIASSEC | Local TRIMSEC | Local PRESEC | Meaning |
| --- | --- | --- | --- | --- | --- |
| 1-4 and 9-12 (32 amps) | [1:1152,1:4616] | [1153:1200,1:4616] | [1:1152,1:4616] | [1:0,1:4616] | Overscan is on the right side |
| 5-8 and 13-16 (32 amps) | [49:1200,1:4616] | [1:48,1:4616] | [49:1200,1:4616] | [1:0,1:4616] | Overscan is on the left side |

| Amp range (`AMPSEQ`) | ENDID | CCDSEC Y range | Raw Y source | DETSEC Y (M, K) | DETSEC Y (N, T) |
| --- | --- | --- | --- | --- | --- |
| 1-8 | TOP | 4617:9232 | 4785:9400 | 14782:19397 | 4617:9232 |
| 9-16 | BOT | 1:4616 | 1:4616 | 10166:14781 | 1:4616 |

### 7.1 Seed WCS placement and state (v4.3, D-023)

The sky WCS on an L0 amp extension is the **seed** for the L1 Gaia astrometric fit. It is not a product WCS: no position may be measured from it. Positions come only from the solved L1 WCS. Card-level definitions are in `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md` section 5.5; this section fixes placement, the state vocabulary, and the handoff.

**Placement.** The PRIMARY HDU carries the frame-level state and the boresight pixel and carries **no** `CTYPE`/`CRVAL`/`CRPIX`/`CD`. The sky WCS itself lives on the 64 amp extensions.

| HDU | Seed WCS cards |
| --- | --- |
| PRIMARY | `WCSSKY`, `WCSOMIT`, `WCSSOLVE`, and — only when a seed is written — `WCSNAME`, `WCSAPPRX`, `BOREPIXX`, `BOREPIXY` |
| Amp extension | `WCSAXES`, `CTYPE1/2`, `CUNIT1/2`, `CRVAL1/2`, `CRPIX1/2`, `CD1_1`, `CD1_2`, `CD2_1`, `CD2_2`, `RADECSYS`, `RADESYS`, `EQUINOX`, `WCSNAME`, `WCSAPPRX`, `WCSSOLVE`, `WCSDIM`, `WCSSKY` |
| AMPINFO | `CRPIX1`, `CRPIX2` columns (section 8) |

**One tangent point.** All 64 extensions share one `CRVAL`, the telescope boresight parsed from the TCS `RA`/`DEC`. Every per-amp offset is carried by `CRPIX`, computed from the boresight mosaic pixel (`BOREPIXX`, `BOREPIXY`) and the amplifier's `DETSEC` origin, **plus 48 in `CRPIX1` for the left-overscan strips** (`AMPSEQ` 5-8 and 13-16, section 7). The invariant, asserted in the `.hdu_verify.txt` sidecar, is

```text
CRPIX1 - LTV1 + DTV1 == BOREPIXX          (and the same in Y)
```

**One CD matrix.** `CD` is identical on all 64 amplifiers and is never sign-flipped per chip or per readout end — see the note in section 4.

**State vocabulary.** L0 writes the same flags the L1 astrometric step reads and then flips, so the state travels in one vocabulary instead of each stage inventing its own.

| Stage | Flags |
| --- | --- |
| L0 (this product) | `WCSNAME = 'TCS-SEED'`, `WCSAPPRX = T`, `WCSSOLVE = F` |
| L1, Gaia solution succeeded | `WCSAPPRX = F`, `WCSSOLVE = T`, plus `WCSRMS`, `WCSNSTAR`, `WCSNREF`, `WCSNMAT`; catalogue in the L1 primary `WCSCAT`, solved-CCD count in `WCSNSOLV` |
| L1, Gaia solution failed | the seed is kept, `WCSSOLVE = F`, reason in `WCSFAIL` |

**Three states, and when no WCS is written at all.** A conforming L0 product legitimately carries no sky WCS in two of them.

| `WCSSKY` | `WCSOMIT` | Condition | Seed WCS |
| --- | --- | --- | --- |
| `T` | `F` | `IMAGETYP` ∈ {`OBJECT`, `SKY`, `FLAT`} and the TCS pointing parses | written |
| `T` | `T` | pointing did not parse | **omitted entirely** |
| `F` | `T` | `IMAGETYP` ∈ {`BIAS`, `DARK`, `DOMEFLAT`} — the frame saw no sky | **omitted entirely** |

⛔ When the seed is omitted it is omitted **whole**, `WCSDIM` included. A `CTYPE` without a `CRVAL` is worse than nothing: readers default `CRVAL` to 0.0 and the field silently resolves near the vernal equinox. `WCSOMIT = T` is the machine-readable statement that the absence is intended. For the same reason `AMPINFO.CRPIX1`/`CRPIX2` carry the -999.0 sentinel in a product with no seed, and `RA`/`DEC` are omitted rather than defaulted when the TCS strings do not parse.

⛔ `WCSSKY = F` is **not** a failed astrometric solution. L1 skips the fit with reason `NOT_SKY_FRAME`; a pipeline must not count those frames as failures.

**Handoff to L1.** The L0 seed-state cards (`WCSNAME`, `WCSAPPRX`, `WCSSOLVE`, `WCSOMIT`, `BOREPIXX`, `BOREPIXY`) are **not** propagated into the L1 primary — they would announce "not solved" over SCI extensions the L1 step has just solved. The live state at L1 is per-SCI (`WCSSOLVE`/`WCSAPPRX`/`WCSRMS`) plus `WCSCAT`/`WCSNSOLV` in the L1 primary.

### 7.2 IRAF pixel transforms (v4.3, D-023)

Every amp extension carries the IRAF section transforms, so that in ds9 `physical` is the CCD column/row and `detector` is the mosaic pixel.

| Group | Cards | Maps amp-local pixels to |
| --- | --- | --- |
| Image <-> CCD | `LTV1`, `LTV2`, `LTM1_1`, `LTM1_2`, `LTM2_1`, `LTM2_2` | CCD coordinates (`CCDSEC`) |
| Image <-> amplifier | `ATV1`, `ATV2`, `ATM1_1`, `ATM1_2`, `ATM2_1`, `ATM2_2` | Amplifier coordinates (`AMPSEC`) |
| Image <-> detector mosaic | `DTV1`, `DTV2`, `DTM1_1`, `DTM1_2`, `DTM2_1`, `DTM2_2` | Mosaic coordinates (`DETSEC`) |

All matrices are the identity: raw spec v1.13 section 4.3 stores every amplifier in ascending CCD order on both axes, so nothing is mirrored and the varying overscan side moves only the offset.

⭐ **These are written for every frame type, including frames with `WCSSKY = F`.** They describe the detector, not the sky, and master bias/dark/flat assembly needs them. `LTV1`/`LTV2`/`DTV1`/`DTV2` are also `AMPINFO` columns (section 8).

## 8. AMPINFO binary table

AMPINFO is the authoritative machine-readable map from image extension to raw pixel source, CCD coordinates, detector mosaic coordinates, and electronics channel identity.

| Column group | Representative columns | Purpose |
| --- | --- | --- |
| Identity | EXTNAME, AMPID, CHIPID, STRIPID, ENDID, AMPNAME | Identify each amplifier extension |
| Raw source | RAWFILE, RAWDATA, RAWBIAS | Trace exact source pixels in MK/NT raw files |
| Geometry | CCDSEC, AMPSEC, DETSEC, DATASEC, BIASSEC, TRIMSEC | Map between local, CCD, and detector coordinates |
| Electronics | CTRLID, MODULE, CHANNEL, XTALKGROUP | Map amp to controller and electronics chain |
| Channel identity (**new in v4.3**, C-11) | CTRUNIT, CCDPORT, CHANNAME, CHANNUM, IMGSEC, CHMAPSRC | Publish the raw `CHMAP_*` channel token each amplifier was taken from |
| Seed-WCS and pixel-transform offsets (**new in v4.3**, D-023) | CRPIX1, CRPIX2, LTV1, LTV2, DTV1, DTV2 | Per-amp offsets of the section 7.1 seed WCS and the section 7.2 transforms |
| Calibration | GAIN, RDNOISE, SATLEVEL, LINMAX | Store amp-level calibration parameters |
| Orientation | CHIPFLP, READDIR, STRIPDIR | Record CEU orientation convention |

AMPINFO has **52 columns** in `PRODVER v2.2.0` (40 in `v2.1.1`). **The 12 new columns are appended at the end, so every existing positional index is unchanged** (D-023 item 8ⓑ).

**Changed in v4.3 (C-11):** `MODULE` and `CHANNEL` were previously derived from the amplifier index and matched no real wiring. They are now read from the raw `CHMAP_LT`/`LB`/`RT`/`RB` tokens and cross-checked against `Detector_Ch_to_AmpID_Map_v1.1.txt`; the PRIMARY `CHMAPOK` card records the result. `CHANNEL` is the CCD output channel and runs **1-16** per chip (it was documented as 1-8); `MODULE` is the controller port index (1 = A, 2 = B) with -1 as the sentinel; `XTALKGROUP` is regrouped on the real controller port (`MK-A`, `MK-B`, `NT-A`, `NT-B`).

⛔ `CRPIX1`/`CRPIX2` carry the -999.0 sentinel when the product has no seed WCS (section 7.1). `LTV`/`DTV` are always real.

## 9. XTALKINFO, VOLTINFO, and TELEMETRY

| Table | Rows in sample | Required role |
| --- | --- | --- |
| XTALKINFO | 4096 (64 x 64) | 64 x 64 source-target crosstalk coefficients. Placeholder values are allowed only before calibration; `XTALKCAL = T` is permitted only when measured coefficients are present. **Unchanged in v4.3.** |
| VOLTINFO | `NVOLT` is authoritative (37 in the v2.5.0 science product) | 9 CCD bias/clock rows with no raw source (`SETPOINT`/`MEASURED` = -999.0, `STATUS` = `PLACEHOLDER`), followed by the measured Archon controller power-supply rows: `NCTRL` x 7 rails x {voltage, current} = 28. ⛔ **Do not hard-code the row count** — read `NVOLT`. |
| TELEMETRY | `NCTRL` (2 in the science product) | One row per science controller. `BOARDTEMP` is **measured** — slot 1 of `Cn_TEMP`, the Backplane sensor; do not average the ten module slots. `STATUS` is derived per controller. `FWVERSION` (`'UNKNOWN'`), `READTIME` (-1.0) and `ERRORFLAG` (-1) stay sentinels: the raw deliberately carries no source for them and controller errors are monitored on a separate path. |

## 10. Recommended processing sequence

1. Read L0 64-amplifier MEF and AMPINFO.
2. Apply local overscan correction to each amplifier extension using BIASSEC.
3. Apply amp-level bias, gain, read-noise, linearity, saturation, and bad-pixel masks.
4. Apply crosstalk correction using XTALKINFO after coefficients are calibrated.
5. Inspect amp boundary seams and bias-jump signatures.
6. Assemble calibrated SCI_M, SCI_K, SCI_N, and SCI_T CCD images.
7. Run astrometry. When `WCSSKY = T` and a seed is present, start the Gaia fit from the L0 seed WCS (section 7.1) and flip `WCSAPPRX`/`WCSSOLVE` in place rather than creating new cards; when `WCSSKY = F`, skip astrometry with reason `NOT_SKY_FRAME` — that is not a failed solution. Do not propagate the L0 seed-state cards into the L1 primary.
8. Run DIA, PSF photometry, catalog matching, and light-curve generation.

## 11. Converter implementation status

The companion converter (`kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`, **v2.5.0**; the filename keeps the `_v2_1` suffix — `SOFTWARE_VERSION` states the revision) implements the L0 64-amplifier MEF structure from verified MK/NT raw images. It creates 64 amp image HDUs and the four required binary tables. Since v2.2.0 it also derives the output prefix from the filename site code and cross-checks it against `OBSERVAT` (section 2.1); v2.4.0 recognizes the D-017 site-code set (`KMTK`/`KASI` replacing `KMTT`/`TESTBED`). Since v2.3.0 the `--ampchar` option stamps measured per-amp `GAIN`/`RDNOISE`/`SATURAT`/`LINMAX` (cam_char results CSV) into the amp headers and `AMPINFO` in place of the placeholders. **v2.5.0 (D-023)** writes the real seed WCS and its state flags (section 7.1), the IRAF pixel transforms (section 7.2), the channel identity read from the raw `CHMAP_*` cards (section 8, C-11), and the measured controller rails and board temperatures in `VOLTINFO`/`TELEMETRY` (section 9, C-18). It also cross-checks the raw's own geometry declarations against its constants (C-5/C-13) and against the pair member (raw spec 5.9), and writes fixed-format string values, `RADESYS` alongside the deprecated `RADECSYS`, and `CHECKSUM`/`DATASUM` on every HDU, so the product passes `fitsverify` and not only `astropy.verify()`. It writes `PRODVER = 'v2.2.0'` with `GEOMVER = 'CEU-L0AMP-v2.1'`.

```bash
python kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  raw/science/archon+header/KMTK.20260915.000034.MK.fits \
  -o kmtk.20260915.000034.ceu.l0amp.mef.fits \
  -f --gzip
```

| Generated file | Description |
| --- | --- |
| kmtk.20260915.000034.ceu.l0amp.mef.fits | Full-size L0 64-amplifier MEF sample |
| kmtk.20260915.000034.ceu.l0amp.mef.fits.gz | Compressed copy for transfer |
| kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py | Converter script implementing this ICD revision |
| *.summary.txt and *.hdu_verify.txt | Conversion and HDU verification summaries; `.hdu_verify.txt` also asserts the section 7.1 boresight invariant |
| *.fits.gz.sha256.txt | SHA-256 checksum of the compressed copy |

## 12. Open items and cautions

- READDIR is encoded as TOP=-Y and BOT=+Y as a placeholder convention; final direction should be confirmed with flat/star sequence tests.
- XTALKINFO values in the current sample are placeholders and must not be used as real calibration coefficients.
- **Changed in v4.3 (D-023, C-18):** VOLTINFO and TELEMETRY are no longer wholly placeholder. The Archon controller power-supply rails (`Cn_VOLT`/`Cn_CURR`) and module temperatures (`Cn_TEMP`) are supplied by the raw header — `raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.13.md` sections 5.6 and 5.6.1 define the cards and the slot order, and the PRIMARY `RAILREF` card records which slot-order revision the product was built against. What remains placeholder is exactly what has no raw source: the 9 CCD bias/clock VOLTINFO rows (the `VOLT<n>`/`VSET<n>`/`VMEA<n>` card family was retired) and TELEMETRY `FWVERSION`/`READTIME`/`ERRORFLAG`. Those carry the raw spec section 5.0 sentinels -999.0 / -1 / `'UNKNOWN'` with `STATUS = 'PLACEHOLDER'` — **not** 0.0, because 0.0 V is a legal `VSS` reading and would disguise missing data as a measurement.
- **The VOLTINFO row count is not fixed.** Read `NVOLT` (section 9). Hard-coding it breaks release gates and readers alike.
- **`BOREPIXX` = 9418.0 sits 28.5 px (11.3 arcsec) from the geometric mosaic centre 9446.5, while `BOREPIXY` = 9699.0 is exactly the centre.** The value is recovered rather than invented — it reproduces on all 32 extensions of operational legacy files from two sites nine years apart, and the CEU reference converter's mock64 output reproduces it — but the offset may be a legacy double-subtraction of a 27-column prescan. It is harmless for a seed (verification converged from a seed 28 arcsec off, well inside the solver's capture radius) and does not block release. One Gaia-matched on-sky exposure closes it.
- **The uniform `CD` matrix of section 7.1 rests on raw spec v1.13 section 4.3 being honoured in practice.** That clause is normative rather than observational, but its compliance test (flat/star sequence, raw spec OI-3) has not been run and the 180-degree mounting of K and N is still open (raw spec OI-17 item 3). ⛔ If section 4.3 turns out to be broken on the bench, the affected 32 amplifiers need a `CD` sign change **and** a matching `CRPIX` mirror — flipping the sign alone is the wrong repair.
- L1 CCD-level images should be generated only after amp-level calibration and seam verification.
- The L0 product is larger and more complex than the CCD-level product, but it is more appropriate for precision photometry and long-term reprocessing.
- Sample raw pairs produced before D-011 keep the `KMTN.*` names in verification records; rename both pair members to the site-coded form when re-running them through converter v2.2.0+ defaults.

## 13. Revision history

| Version | Date | Change |
| --- | --- | --- |
| v2.0 | 2026-06-19 | Archon MK/NT raw structure verified; MKNT order introduced. |
| v3.0 | 2026-06-19 | Removed chip-dependent legacy flip; common TOP/BOT CEU geometry documented. |
| v4.0 | 2026-06-19 | Changed primary raw MEF product to L0 64-amplifier extensions; CCD-level product demoted to L1 calibrated output. |
| v4.1 | 2026-08-10 | Raw filename prefix changed from literal `KMTN` to site code `<SITE>` in {KMTC, KMTS, KMTA, KMTT} (section 2.1, DECISION_LOG D-011); NT header completeness now required, "minimal NT header" allowance removed (section 2, raw_fits_spec OI-8); converter reference updated to v2.2.0 with filename/`OBSERVAT` cross-check; md master copy of this ICD introduced alongside the docx. |
| v4.2 | 2026-09-04 | Fourth site code retired: `KMTT`/`TESTBED` -> `KMTK`/`KASI` (section 2.1, DECISION_LOG D-017, 2026-08-25; the testbed sits at KASI). L0 MEF prefix `kmtt` -> `kmtk`. Converter reference updated to v2.4.0 (D-017 site-code set; v2.3.0 added `--ampchar` measured GAIN/RDNOISE stamping). No geometry change - `GEOMVER` unchanged. |
| v4.3 | 2026-09-23 | L0 sky WCS specified as the **seed** for the L1 Gaia fit rather than a product WCS: new sections 7.1 (placement, one shared tangent point, uniform `CD`, the `WCSSKY`/`WCSOMIT` states, the L0 -> L1 handoff) and 7.2 (IRAF `LTV`/`LTM`, `ATV`/`ATM`, `DTV`/`DTM`, written for every frame type) (DECISION_LOG D-023, 2026-09-23). Section 4 gains the note that "no chip-dependent flip" must not be read as a reason to flip `CD` for K and N. `AMPINFO` 40 -> 52 columns, appended at the end so existing indices are unchanged; `CHANNEL` 1-8 -> 1-16, `MODULE` redefined as the controller port and `XTALKGROUP` regrouped on it, all now read from the raw `CHMAP_*` cards (section 8, C-11). `VOLTINFO` 9 -> 37 rows with the 28 measured controller rails of C-18, and `TELEMETRY` `BOARDTEMP` measured; section 12's "placeholder when the raw gives no telemetry" clause rewritten and `NVOLT` made the row-count authority (section 9). Section 10 step 7 states the seed handoff. Converter reference updated to v2.5.0; `PRODVER` v2.1.1 -> v2.2.0. Stale references to the retired `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` replaced by `KMT_CEU_Raw_FITS_Specification_v1.13.md` in sections 2, 2.1 and 12, and the section 11 sample repointed at a raw pair that exists. New open items: the `BOREPIXX` offset, the raw spec 4.3 compliance test, and the VOLTINFO row-count rule. No geometry change - `GEOMVER` unchanged. |

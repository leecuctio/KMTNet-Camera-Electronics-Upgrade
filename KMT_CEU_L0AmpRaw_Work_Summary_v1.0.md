# KMT-CEU L0 64-Amplifier Raw MEF 작업 정리

작성일: 2026-06-19
최종 점검일: 2026-06-22

## 1. 문서 목적

이 문서는 현재까지 정리한 KMT-CEU Science MEF ICD 방향, Archon MK/NT raw 검증 결과, L0 64-amplifier MEF product 정책, converter 코드 분석, 실행 결과, 수정 사항, CLI 실행 방법을 하나로 묶은 작업 기록이다.

기준 ICD 문서:

- `mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx`

기준 converter:

- `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`

최신 생성 산출물:

- `kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits`
- `kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz`
- `kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.summary.txt`
- `kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz.sha256.txt`

## 2. ICD v4.0 핵심 결정

v4.0 ICD의 가장 중요한 변경은 science MEF raw product를 CCD-level raw image가 아니라 L0 64-amplifier MEF로 정의한 것이다.

결정 사항:

- Primary raw archive 및 calibration input은 L0 64-amplifier MEF이다.
- 각 amplifier extension은 local active pixels와 local overscan pixels를 함께 보존한다.
- CCD-level `SCI_M`, `SCI_K`, `SCI_N`, `SCI_T` 이미지는 amp-level calibration 이후 생성하는 L1 calibrated product이다.
- MKNT order는 검증된 Archon controller grouping과 기존 converter 흐름을 따른다.

Product level 정책:

| Product level | MEF image layout | Main purpose | Status |
| --- | --- | --- | --- |
| L0 Raw | 64 amp extensions + binary tables | Raw archive, overscan/bias/gain/crosstalk calibration, debugging | Primary raw product |
| L1 Calibrated | `SCI_M`, `SCI_K`, `SCI_N`, `SCI_T` + calibration history | Astrometry, DIA, photometry용 calibrated CCD images | Derived product |
| L2 Science | Difference images, catalogs, light curves | Science analysis outputs | Pipeline product |

## 3. 검증된 Archon Raw 구조

검증 raw files:

- `KMTN.20260116.000001.MK.fits`
- `KMTN.20260116.000001.NT.fits`

Raw grouping:

| Raw file | Contains chips | Role |
| --- | --- | --- |
| `KMTN.YYYYMMDD.NNNNNN.MK.fits` | M, K | Master metadata source and pixel data source |
| `KMTN.YYYYMMDD.NNNNNN.NT.fits` | N, T | Pixel data source. Header metadata may be minimal. |

검증 geometry:

| Quantity | Value | Meaning |
| --- | ---: | --- |
| `RAWNAX1` | 19200 | 16 x 1200 pixel amp tiles in X |
| `RAWNAX2` | 9400 | 4616 lower active rows + 168 middle Y overscan + 4616 upper active rows |
| `RAWXTILE` | 1200 | 1152 active columns + 48 overscan columns |
| `AMPDATA` | 1152 | Active columns per amplifier tile |
| `OVERSCNX` | 48 | Local X overscan columns per amplifier tile |
| `PRESCANX` | 0 | No local X prescan in verified Archon raw |
| `MIDOVSCY` | 168 | Middle Y overscan rows between lower and upper active halves |

## 4. Chip Order 및 Amplifier Numbering

Official science chip order:

```text
M, K, N, T
```

Raw grouping:

```text
MK -> M,K
NT -> N,T
```

Amplifier numbering:

| Chip | Raw source | Global amplifier range | Image extension order |
| --- | --- | --- | --- |
| M | MK | 1-16 | `M01T`..`M08T`, `M01B`..`M08B` |
| K | MK | 17-32 | `K01T`..`K08T`, `K01B`..`K08B` |
| N | NT | 33-48 | `N01T`..`N08T`, `N01B`..`N08B` |
| T | NT | 49-64 | `T01T`..`T08T`, `T01B`..`T08B` |

Converter constants:

```python
CHIP_ORDER = ["M", "K", "N", "T"]
CHIP_TO_TAG = {"M": "MK", "K": "MK", "N": "NT", "T": "NT"}
AMP_BASE = {"M": 0, "K": 16, "N": 32, "T": 48}
```

## 5. CEU Archon Orientation 정책

Legacy OSU electronics에서는 M/T와 K/N이 서로 다른 orientation group으로 취급되었다. CEU Archon L0 packing에서는 chip-dependent OSU-style image flip을 적용하지 않는다.

정책:

- `CHIPFLP = "None"`
- `STRIPDIR = "+X"`
- amp 1-8은 TOP half
- amp 9-16은 BOT half
- L0 stage에서는 chip별 flip 없이 raw pixel source를 amp extension으로 분리한다.

READDIR placeholder:

```text
TOP: -Y
BOT: +Y
```

이 값은 최종 flat/star sequence test로 확인이 필요하다.

## 6. L0 64-Amplifier MEF 구조

L0 output layout:

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

Amp image extension:

| Extension class | NAXIS1 | NAXIS2 | Content |
| --- | ---: | ---: | --- |
| Amp image extension | 1200 | 4616 | One amplifier half-strip with active + local overscan |

Binary tables:

| Table | Role |
| --- | --- |
| `AMPINFO` | Authoritative 64-row amplifier geometry/electronics map |
| `XTALKINFO` | 64 x 64 crosstalk model table. 현재 값은 placeholder |
| `VOLTINFO` | Bias and clock voltage settings/telemetry. 현재 값은 placeholder |
| `TELEMETRY` | Archon controller status/readout telemetry. 현재 값은 placeholder |

## 7. Amp Section 정의

각 L0 amp extension의 local coordinate는 `1200 x 4616`이다.

Local section:

| Amp group | Local `DATASEC` | Local `BIASSEC` | Meaning |
| --- | --- | --- | --- |
| amps 1-4 and 9-12 | `[1:1152,1:4616]` | `[1153:1200,1:4616]` | Overscan on right side |
| amps 5-8 and 13-16 | `[49:1200,1:4616]` | `[1:48,1:4616]` | Overscan on left side |

Y section:

| Amp range | ENDID | CCDSEC Y range | Raw Y source |
| --- | --- | --- | --- |
| 1-8 | TOP | `4617:9232` | `4785:9400` |
| 9-16 | BOT | `1:4616` | `1:4616` |

## 8. Converter v2.1.1 코드 분석 요약

파일:

- `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`

전체 성격:

- 순수 Python + NumPy 기반 독립형 FITS writer이다.
- Astropy를 사용하지 않고 FITS header card, image HDU, binary table bytes를 직접 생성한다.
- raw FITS primary image는 `np.memmap`으로 읽는다.
- output FITS는 순차적으로 file handle에 직접 write한다.

주요 함수:

| Function | Role |
| --- | --- |
| `read_primary_header()` | FITS primary header를 직접 읽고 key/value dict 생성 |
| `memmap_raw()` | BITPIX=16 raw primary image를 big-endian int16 memmap으로 mapping |
| `find_pair()` | 입력이 MK 또는 NT일 때 counterpart raw file 찾기 |
| `raw_x_sections()` | amp별 raw active/bias X section 및 local DATASEC/BIASSEC 계산 |
| `raw_y_section()` | TOP/BOT별 raw Y section 계산 |
| `ccdsec()` | amp별 CCD coordinate section 계산 |
| `detsec()` | chip 위치와 gap을 반영한 detector mosaic coordinate 계산 |
| `primary_cards()` | primary HDU cards 생성 |
| `amp_header()` | 각 amplifier image extension header 생성 |
| `bintable_bytes()` | binary table HDU bytes 생성 |
| `ampinfo_rows()` | 64-row AMPINFO table 내용 생성 |
| `write_amp_hdu()` | raw data/bias slice를 local amp extension layout으로 배치 |
| `convert()` | 전체 conversion orchestration |
| `write_summary()` | conversion summary text 생성 |
| `gzip_file()` | gzip copy 및 gzip sha256 생성 |

Conversion flow:

```text
input MK or NT
-> find MK/NT pair
-> read MK primary header as master metadata
-> memmap MK and NT raw image arrays
-> write primary HDU
-> for chip in M,K,N,T:
     select MK or NT raw array
     for amp in 1..16:
       slice raw active and bias pixels
       assemble 1200 x 4616 amp stripe
       write IMAGE extension
-> write AMPINFO
-> write XTALKINFO
-> write VOLTINFO
-> write TELEMETRY
-> write summary
-> optional gzip
```

## 9. v2.1.1과 v2/v2.1의 차이

v2.1.1은 geometry를 바꾼 버전이 아니라 compatibility, FITS 표준성, 배포 안정성을 정리한 patch 버전이다.

v2.1 변경 사항:

- `datetime.UTC` 대신 `datetime.timezone.utc` 사용
- Python 3.9/3.10 compatibility 향상
- `PRODVER`, `CAMVER`, `PIPEVER`, `GEOMVER`를 v2.1 문자열로 갱신

v2.1.1에서 적용한 수정:

- FITS logical card value를 표준 포맷으로 출력하도록 수정
- `CREATOR`가 v2.0으로 남아 있던 것을 v2.1.1로 정정
- FITS header value/comment parsing에서 quoted string 내부의 `/` 문자를 안전하게 처리
- output FITS를 임시 파일에 먼저 쓴 뒤 성공 시 `os.replace()`로 교체하여 partial output 위험 감소
- software/product version은 `v2.1.1`, geometry version은 `CEU-L0AMP-v2.1`로 분리

수정된 logical card 출력 예:

```text
SIMPLE  =                    T
EXTEND  =                    T
```

## 10. CLI 실행 방법

터미널에서 작업 디렉토리로 이동:

```bash
cd "/Users/leecu/LEECU/WORK/2026/4.작업/KMTNet-CEU"
```

Converter 실행:

```bash
python3 kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  KMTN.20260116.000001.MK.fits \
  -o kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits \
  -f --gzip
```

One-line version:

```bash
python3 kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py KMTN.20260116.000001.MK.fits -o kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits -f --gzip
```

Options:

| Option | Meaning |
| --- | --- |
| `-o` | Output FITS path 지정 |
| `-f` | 기존 output이 있어도 overwrite |
| `--gzip` | `.fits.gz` compressed copy 생성 |

## 11. 생성 산출물 및 검증 결과

최신 산출물:

| File | Size |
| --- | ---: |
| `kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits` | 677M |
| `kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz` | 188M |
| `kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.summary.txt` | 1.1K |
| `kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz.sha256.txt` | 116B |

Current gzip SHA256:

```text
7a55e7573eac899cd4b3c50b5dc747efe362a49bef505c1f0f90f53f68760289  kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz
```

Astropy validation:

```text
verify ok
```

HDU structure:

```text
HDU count = 69
PRIMARY
64 amplifier IMAGE extensions
AMPINFO
XTALKINFO
VOLTINFO
TELEMETRY
```

Representative data check:

```text
M01T shape = (4616, 1200)
AMPINFO rows = 64
XTALKINFO rows = 4096
VOLTINFO rows = 9
TELEMETRY rows = 2
```

Version metadata after fix:

```text
CREATOR = kmt_ceu_l0amp_mknt2mef_v2.1.1
PRODVER = v2.1.1
PIPEVER = kmt_ceu_l0amp_mknt2mef-v2.1.1
GEOMVER = CEU-L0AMP-v2.1
```

## 12. 확인된 주의사항 및 개선 후보

현재 converter는 L0 64-amplifier MEF product 생성 목적에는 맞게 동작한다. 다만 운영용으로 더 튼튼하게 만들기 위해 아래 항목을 후속 개선 후보로 남긴다.

1. Placeholder calibration values

`GAIN`, `RDNOISE`, `SATURAT`, `LINMAX`, `XTALKINFO`, `VOLTINFO`, `TELEMETRY` 값은 현재 placeholder 성격이다. 실제 calibration 및 Archon telemetry 확보 후 갱신해야 한다.

2. READDIR final confirmation

현재 `READDIR`은 TOP=`-Y`, BOT=`+Y` placeholder convention이다. flat/star sequence test로 최종 확인해야 한다.

3. Astropy memmap behavior

Image HDU에 `BZERO/BSCALE`이 있으므로 Astropy에서 scaled image data를 memmap으로 직접 읽을 때 제한이 있다. 검증이나 분석 시에는 `memmap=False` 또는 `do_not_scale_image_data=True`를 사용하면 된다.

## 13. 현재 결론

현재 작업 상태에서 KMT-CEU Science MEF raw product 방향은 L0 64-amplifier MEF로 정리되었다. Converter v2.1.1은 검증된 MK/NT Archon raw geometry를 기준으로 64개 amplifier image extension과 4개 binary table을 생성하며, 최신 수정 후 Astropy FITS verification을 통과한다.

즉, 현 단계 산출물은 다음 목적에 사용할 수 있다.

- Archon MK/NT raw의 amp-level L0 archive sample
- AMPINFO 기반 geometry/electronics mapping 검토
- overscan, bias, gain, read-noise, crosstalk, bias-jump calibration pipeline 설계
- L1 CCD-level calibrated product 생성 로직의 입력 형식 기준

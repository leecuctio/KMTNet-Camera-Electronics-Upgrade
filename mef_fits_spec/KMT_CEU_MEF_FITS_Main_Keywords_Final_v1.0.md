# KMT-CEU 신규 전자부 카메라 MEF FITS 주요 키워드 최종 정리

버전: v1.0  
작성일: 2026-06-22  
기준 converter: `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` v2.1.1  
기준 ICD: `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx`

## 1. 문서 목적

이 문서는 STA Archon controller 2개를 사용하는 KMT-CEU 신규 전자부 카메라가 완성된 뒤, science raw output을 MEF FITS로 저장할 때 사용해야 할 주요 FITS keyword와 binary table column을 정리한 최종 운영 기준 문서이다.

본 문서의 기본 원칙은 다음과 같다.

- Primary L0 raw archive product는 64-amplifier MEF이다.
- 각 amplifier image extension은 local active pixels와 local overscan pixels를 함께 보존한다.
- CCD-level `SCI_M`, `SCI_K`, `SCI_N`, `SCI_T` 이미지는 amp-level calibration 이후 생성하는 L1 product이다.
- `MK` raw file은 M,K chip을 담고, `NT` raw file은 N,T chip을 담는다.
- 공식 chip order는 `M,K,N,T`이다.
- CEU Archon L0 packing 단계에서는 legacy OSU식 chip-dependent image flip을 적용하지 않는다.

## 2. MEF Product 구조

L0 MEF의 HDU 구성은 다음 순서를 따른다.

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

Expected HDU count:

```text
69 = PRIMARY + 64 amplifier IMAGE extensions + 4 BINTABLE extensions
```

주요 extension의 역할은 다음과 같다.

| HDU | 역할 |
| --- | --- |
| `PRIMARY` | 전체 observation, product, camera/electronics, raw provenance metadata |
| Amp image HDUs | 각 amplifier의 `1200 x 4616` raw image. active `1152` columns와 local overscan `48` columns 포함 |
| `AMPINFO` | 64개 amplifier의 authoritative geometry/electronics/calibration map |
| `XTALKINFO` | 64 x 64 source-target crosstalk coefficient table |
| `VOLTINFO` | bias/clock voltage setpoint 및 measured telemetry |
| `TELEMETRY` | Archon controller firmware, temperature, readout status, error flag |

## 3. Keyword 작성 정책

Keyword 상태는 아래와 같이 구분한다.

| 상태 | 의미 |
| --- | --- |
| Required | 운영 FITS에서 반드시 유효한 값을 가져야 하는 항목 |
| Generated | converter가 geometry 또는 output context에서 자동 생성하는 항목 |
| From raw | MK primary header 또는 observatory system에서 전달되어야 하는 항목 |
| Calibration | calibration database 또는 commissioning 이후 실측값으로 채워야 하는 항목 |
| Placeholder allowed | commissioning 전에는 placeholder를 허용하되 science processing 전 교체해야 하는 항목 |

운영 기준:

- 시간 keyword는 UTC 기준으로 기록한다.
- FITS 표준 keyword는 8자 제한을 따른다. 예: `ELEVATIO`, `CONTROLL`, `TCSDRIV`.
- `DATE-OBS`, `MJD-OBS`, `JD`는 같은 exposure start time을 표현해야 한다.
- `BZERO/BSCALE`은 unsigned 16-bit raw image 해석을 위해 image extension에 유지한다.
- `XTALKCAL=False`인 파일의 `XTALKINFO` 값은 real correction coefficient로 사용하지 않는다.

## 4. PRIMARY HDU 주요 Keywords

### 4.1 FITS Standard 및 Product Identity

| Keyword | 상태 | 예시 | 설명 |
| --- | --- | --- | --- |
| `SIMPLE` | Required | `T` | FITS standard file |
| `BITPIX` | Required | `16` | image extension의 pixel type 기준 |
| `NAXIS` | Required | `0` | primary HDU에는 image array 없음 |
| `EXTEND` | Required | `T` | extension 포함 |
| `ORIGIN` | From raw | `KASI` | file originator |
| `DATE` | Generated | UTC ISO time | MEF 생성 시각 |
| `CREATOR` | Generated | `kmt_ceu_l0amp_mknt2mef_v2.1.1` | MEF 생성 프로그램 |
| `BUNIT` | From raw | `ADU` | pixel unit |
| `DATAPROD` | Required | `L0_AMP` | product type |
| `PRODVER` | Generated | `v2.1.1` | product format/software version |
| `PIPEVER` | Generated | `kmt_ceu_l0amp_mknt2mef-v2.1.1` | converter/pipeline version |

### 4.2 Raw Provenance 및 Archon Geometry

| Keyword | 상태 | 값/예시 | 설명 |
| --- | --- | --- | --- |
| `RAWGROUP` | Required | `MKNT` | raw file grouping convention |
| `CHIPLIST` | Required | `M,K,N,T` | 공식 science chip order |
| `MKFILE` | Generated | `KMTN.20260116.000001.MK.fits` | source MK raw FITS |
| `NTFILE` | Generated | `KMTN.20260116.000001.NT.fits` | source NT raw FITS |
| `NUMFILES` | Required | `2` | MEF 생성에 사용한 raw file 수 |
| `RAWNAX1` | Required | `19200` | Archon raw image width |
| `RAWNAX2` | Required | `9400` | Archon raw image height |
| `RAWXTILE` | Required | `1200` | amplifier tile width |
| `AMPDATA` | Required | `1152` | active columns per amp tile |
| `OVERSCNX` | Required | `48` | local X overscan columns |
| `PRESCANX` | Required | `0` | X prescan columns |
| `MIDOVSCY` | Required | `168` | middle Y overscan rows |
| `TOPROWS` | Required | `4616` | TOP active rows |
| `BOTROWS` | Required | `4616` | BOT active rows |
| `CHIPFLP` | Required | `None` | L0 packing에서 chip-dependent flip 없음 |

### 4.3 Detector 및 Camera Configuration

| Keyword | 상태 | 예시 | 설명 |
| --- | --- | --- | --- |
| `DETECTOR` | From raw | `e2v CCD290-99` | detector model |
| `CAMNAME` | Required | `KMT-CEU` | camera/electronics upgrade system |
| `CAMVER` | Required | `CEU-v2.1` | camera/electronics version |
| `DETTYPE` | Required | `SCIENCE` | detector data type |
| `NCCD` | Required | `4` | science CCD 수 |
| `NAMPS` | Required | `64` | 총 amplifier 수 |
| `AMPPCD` | Required | `16` | CCD당 amplifier 수 |
| `NSTRIP` | Required | `8` | CCD당 vertical strip 수 |
| `NEND` | Required | `2` | strip당 TOP/BOT readout ends |
| `CCDXBIN` | From raw | `1` | CCD X binning |
| `CCDYBIN` | From raw | `1` | CCD Y binning |
| `READMODE` | Required | `64AMP` | readout mode |
| `READARCH` | Required | `8STRIPx2END` | readout architecture |
| `PIXSCALE` | Required | `0.400` | arcsec/pixel |
| `PIXSIZE` | Required | `10.0` | micron |
| `DETSIZE` | Required | `[1:18892,1:19397]` | mosaic detector size |
| `COLGAP` | Required | `460` | inter-CCD column gap |
| `ROWGAP` | Required | `933` | inter-CCD row gap |

### 4.4 Observatory, Exposure, Object

| Keyword | 상태 | 설명 |
| --- | --- | --- |
| `OBSERVAT` | From raw | observatory site. output prefix 결정에도 사용 |
| `SITEID` | From raw | site identifier |
| `TELESCOP` | From raw | telescope name |
| `LATITUDE` | From raw | site latitude |
| `LONGITUD` | From raw | site longitude |
| `ELEVATIO` | From raw | site elevation in meters |
| `OBSERVER` | From raw | observer(s) |
| `OBJECT` | From raw | observed object or field |
| `FIELDID` | From raw | KMTNet field identifier |
| `PROJID` | From raw | observing program ID |
| `IMAGETYP` | From raw | observation image type |
| `OBSTYPE` | From raw | observation type |
| `EXPTIME` | From raw | exposure time in seconds |
| `DARKTIME` | From raw | cumulative dark time in seconds |
| `TSHOPEN` | From raw | shutter open time |
| `TSHSHUT` | From raw | shutter close time |
| `FILTER` | From raw | filter name |
| `FILENAME` | Generated | output MEF filename |
| `UNIQNAME` | From raw | unique filename or exposure ID |

### 4.5 Electronics 및 Calibration Version

| Keyword | 상태 | 예시 | 설명 |
| --- | --- | --- | --- |
| `INSTRUME` | From raw | `KMTS` | instrument name |
| `CONTROLL` | Required | `STA ARCHON` | controller type |
| `NCTRL` | Required | `2` | science Archon controller 수 |
| `CTRL1ID` | From raw | site dependent | controller 1 ID |
| `CTRL1SN` | From raw | site dependent | controller 1 serial number |
| `CTRL1FW` | From raw | site dependent | controller 1 firmware |
| `CTRL2ID` | From raw | site dependent | controller 2 ID |
| `CTRL2SN` | From raw | site dependent | controller 2 serial number |
| `CTRL2FW` | From raw | site dependent | controller 2 firmware |
| `WBTYPE` | Required | `STA Differential Board` | wall board type |
| `ELECSYS` | Required | `KMT-CEU` | electronics system |
| `SIGELEC` | Required | `STA_DIFF_VIDEO` | signal chain electronics |
| `TIMCONF` | Calibration | `CEU_TIM_v1.0` | timing configuration |
| `CTRLVER` | Calibration | `ARCHON-v1.0` | controller system version |
| `TIMVER` | Calibration | `TIM-v1.0` | timing script version |
| `XTALKVER` | Calibration | `UNMEASURED` before calibration | crosstalk model version |
| `XTALKCAL` | Required | `False` before calibration | true only when real coefficients are available |
| `BIASVER` | Calibration | `BIAS-v1.0` | bias configuration version |
| `CLKVER` | Calibration | `CLK-v1.0` | clock configuration version |
| `REFVER` | Calibration | `N/A` or reference version | reference image version |
| `CATVER` | Calibration | `N/A` or catalog version | catalog version |

### 4.6 Time 및 TCS Pointing

| Keyword | 상태 | 설명 |
| --- | --- | --- |
| `TCSLINK` | From raw | TCS link status |
| `TCSARC` | From raw | TCS auto recovery status |
| `TCSQDATE` | From raw | last TCS query time |
| `TCSUDATE` | From raw | last TCS update time |
| `TIMESYS` | Required | time system. default `UTC` |
| `DATE-OBS` | Required | UTC exposure start time |
| `MJD-OBS` | Generated | modified Julian date at exposure start |
| `JD` | Generated | Julian date at exposure start |
| `UT` | From raw/Generated | UTC timestamp |
| `RADECSYS` | From raw | coordinate system. default `ICRS` |
| `RA` | From raw | telescope right ascension |
| `DEC` | From raw | telescope declination |
| `EQUINOX` | From raw | coordinate equinox |
| `HA` | From raw | hour angle |
| `ST` | From raw | local sidereal time |
| `SECZ` | From raw | secant of zenith distance |
| `ALT` | From raw | telescope altitude |
| `AZ` | From raw | telescope azimuth |
| `TCSDRIV` | From raw | telescope drive status |
| `TELMOVE` | From raw | telescope motion status |

### 4.7 Auxiliary, Focus, Dome, Thermal Keywords

아래 keyword는 observatory operation 및 quality control을 위해 유지한다. 값은 가능한 경우 raw header 또는 control system telemetry에서 가져온다.

| Group | Keywords |
| --- | --- |
| AUX link | `AUXLINK`, `AUXARC`, `AUXQDATE`, `AUXUDATE` |
| Filter/shutter | `FSSTAT`, `FILTOP`, `FILNUM`, `FILTER`, `SHUTOP`, `SHUTTER` |
| FSA environment | `FSATEMP`, `FSAHUM`, `FSADEW`, `FSAALRM` |
| Focus actuator | `FASTAT`, `FAFOCUS`, `FATILTNS`, `FATILTEW`, `FAPOSS`, `FALIMS`, `FAPOSE`, `FALIME`, `FAPOSW`, `FALIMW` |
| Dome | `DSSTAT`, `DSUP`, `DSLW`, `DSSAF`, `DSAUTO`, `DSALT`, `DSAZ`, `DSTELALT`, `DSTELAZ`, `DALTERR`, `DAZERR` |
| Mirror/chiller/environment | `MCSTAT`, `MCPOS`, `CHSTAT`, `ENSTAT`, `ENFAN` |
| Thermal/dewar | `CCDTEMP`, `DEWPRES`, `PT30N1`, `PT30N2`, `CHARCOAL`, `AIR_IN`, `AIR_OUT`, `GLYC_IN`, `GLYC_OUT` |
| Image check | `CHKIMG`, `CHKIMG_C` |

## 5. Amplifier Image Extension 주요 Keywords

각 amplifier image extension은 `NAXIS1=1200`, `NAXIS2=4616`이다. `DATASEC`과 `BIASSEC`은 각 extension 내부의 local coordinate이며, `CCDSEC`과 `DETSEC`은 같은 active pixel의 CCD/mosaic coordinate를 나타낸다.

### 5.1 Standard Image Extension

| Keyword | 상태 | 예시 | 설명 |
| --- | --- | --- | --- |
| `XTENSION` | Required | `IMAGE` | image extension |
| `BITPIX` | Required | `16` | raw image data type |
| `NAXIS` | Required | `2` | two-dimensional image |
| `NAXIS1` | Required | `1200` | amp image width including overscan |
| `NAXIS2` | Required | `4616` | active half rows |
| `PCOUNT` | Required | `0` | FITS extension parameter count |
| `GCOUNT` | Required | `1` | FITS group count |
| `BZERO` | Required | `32768` | unsigned 16-bit zero point |
| `BSCALE` | Required | `1` | pixel scale factor |
| `BUNIT` | From raw | `ADU` | pixel unit |

### 5.2 Amp Identity 및 Raw Provenance

| Keyword | 상태 | 예시 | 설명 |
| --- | --- | --- | --- |
| `EXTNAME` | Required | `M01T` | image extension name |
| `EXTTYPE` | Required | `AMP_RAW` | L0 amplifier raw image |
| `REALDATA` | Required | `T` | actual amplifier data from raw |
| `DATAPROD` | Required | `L0_AMP` | data product type |
| `CHIPID` | Required | `M`, `K`, `N`, `T` | CCD identifier |
| `CCDNAME` | Generated | `KMTNet CCD M` | CCD name |
| `AMPID` | Required | `1` to `64` | global amplifier ID |
| `AMPSEQ` | Required | `1` to `16` | amplifier sequence within CCD |
| `STRIPID` | Required | `1` to `8` | vertical strip ID |
| `ENDID` | Required | `TOP` or `BOT` | readout end |
| `AMPNAME` | Required | `M01T` | amplifier name |
| `RAWFILE` | Generated | MK or NT filename | source raw FITS file |
| `CTRLID` | Required | `1` or `2` | science Archon controller ID |
| `MODULE` | Generated/Calibration | `1` or `2` | controller module mapping |
| `CHANNEL` | Generated/Calibration | `1` to `8` | controller channel mapping |

Controller mapping convention:

| Chips | `CTRLID` | Raw source |
| --- | ---: | --- |
| M, K | 1 | MK |
| N, T | 2 | NT |

### 5.3 Geometry, Orientation, Section Keywords

| Keyword | 상태 | 설명 |
| --- | --- | --- |
| `CHIPFLP` | Required | `None`; no chip-dependent OSU-style flip at L0 |
| `STRIPDIR` | Required | strip number direction. current convention `+X` |
| `READDIR` | Placeholder allowed | TOP=`-Y`, BOT=`+Y`; final confirmation by flat/star tests |
| `CCDSUM` | From raw | binning factors. current `1 1` |
| `CCDSEC` | Required | active amp section in CCD coordinates |
| `AMPSEC` | Required | amplifier section in CCD coordinates |
| `DETSEC` | Required | active amp section in full mosaic coordinates |
| `RAWDATA` | Required | source raw active-pixel section |
| `RAWBIAS` | Required | source raw overscan section |
| `DATASEC` | Required | active section in local amp image |
| `PRESEC` | Required | no prescan. current `[1:0,1:4616]` |
| `BIASSEC` | Required | local overscan section |
| `TRIMSEC` | Required | local trimmed active section |

Local section convention:

| Amp group | `DATASEC` | `BIASSEC` |
| --- | --- | --- |
| amps 1-4 and 9-12 | `[1:1152,1:4616]` | `[1153:1200,1:4616]` |
| amps 5-8 and 13-16 | `[49:1200,1:4616]` | `[1:48,1:4616]` |

TOP/BOT Y convention:

| Amp range | `ENDID` | `CCDSEC` Y range | Raw Y source |
| --- | --- | --- | --- |
| 1-8 | `TOP` | `4617:9232` | `4785:9400` |
| 9-16 | `BOT` | `1:4616` | `1:4616` |

### 5.4 Amp-level Calibration Keywords

| Keyword | 상태 | 설명 |
| --- | --- | --- |
| `GAIN` | Calibration | amp gain in e-/ADU |
| `RDNOISE` | Calibration | amp read noise in electrons |
| `SATURAT` | Calibration | saturation level in ADU |
| `LINMAX` | Calibration | linearity maximum in ADU |

운영 전환 기준:

- commissioning 전에는 placeholder를 허용할 수 있다.
- photometry/DIA용 L1 product 생성 전에는 amp별 실측 calibration value로 교체해야 한다.
- 동일 값은 image extension header와 `AMPINFO` table 양쪽에서 일관되어야 한다.

### 5.5 Amp Extension Observation 및 WCS Keywords

Amp extension에도 quick-look 및 downstream compatibility를 위해 주요 observation keyword를 반복 기록한다.

| Group | Keywords |
| --- | --- |
| Observation | `FILTER`, `PROJID`, `IMAGETYP`, `OBJECT`, `OBSTYPE` |
| Pointing | `RA`, `DEC`, `HA`, `ST`, `SECZ`, `ALT`, `AZ`, `UT` |
| WCS placeholder | `CTYPE1`, `CTYPE2`, `CRVAL1`, `CRVAL2`, `CRPIX1`, `CRPIX2`, `CD1_1`, `CD1_2`, `CD2_1`, `CD2_2`, `WCSDIM` |

주의:

- L0 amp extension의 WCS는 full astrometric solution이 아니라 placeholder 성격이다.
- 최종 science WCS는 amp-level calibration 후 생성되는 L1 CCD-level image에서 확정한다.

## 6. AMPINFO Binary Table

`AMPINFO`는 image extension header와 동일한 geometry/electronics 정보를 machine-readable table로 제공한다. Pipeline은 가능하면 `AMPINFO`를 authoritative map으로 사용한다.

Extension header keywords:

| Keyword | 값 | 설명 |
| --- | --- | --- |
| `EXTNAME` | `AMPINFO` | table name |
| `NAMP` | `64` | number of amplifier rows |
| `GEOMVER` | `CEU-L0AMP-v2.1` | geometry definition version |
| `RAWGROUP` | `MKNT` | raw grouping |

Columns:

| Column | Format | Unit | 설명 |
| --- | --- | --- | --- |
| `EXTNAME` | `8A` |  | image extension name |
| `AMPID` | `I` |  | global amplifier ID |
| `CHIPID` | `1A` |  | chip ID |
| `STRIPID` | `I` |  | strip ID |
| `ENDID` | `3A` |  | TOP/BOT |
| `STRIPDIR` | `2A` |  | strip direction |
| `AMPSEQ` | `I` |  | amp sequence in CCD |
| `AMPNAME` | `5A` |  | amp name |
| `RAWFILE` | `32A` |  | source raw file |
| `CTRLID` | `I` |  | controller ID |
| `MODULE` | `I` |  | controller module |
| `CHANNEL` | `I` |  | electronics channel |
| `CCDSEC` | `24A` |  | CCD section |
| `AMPSEC` | `24A` |  | amp section |
| `DETSEC` | `28A` |  | detector mosaic section |
| `RAWDATA` | `32A` |  | source raw active section |
| `RAWBIAS` | `32A` |  | source raw overscan section |
| `DATASEC` | `24A` |  | local data section |
| `PRESEC` | `18A` |  | local prescan section |
| `BIASSEC` | `24A` |  | local overscan section |
| `TRIMSEC` | `24A` |  | local trimmed active section |
| `CHIPFLP` | `8A` |  | chip flip convention |
| `READDIR` | `2A` |  | readout direction |
| `GAIN` | `E` | e-/ADU | amp gain |
| `RDNOISE` | `E` | e- | read noise |
| `SATLEVEL` | `J` | ADU | saturation level |
| `LINMAX` | `J` | ADU | linearity maximum |
| `RAWX0`, `RAWX1`, `RAWY0`, `RAWY1` | `J` | pixel | raw section numeric bounds |
| `AMPX0`, `AMPX1`, `AMPY0`, `AMPY1` | `J` | pixel | CCD/amp bounds |
| `DETX0`, `DETX1`, `DETY0`, `DETY1` | `J` | pixel | detector mosaic bounds |
| `XTALKGROUP` | `8A` |  | crosstalk/electronics group |

## 7. XTALKINFO Binary Table

`XTALKINFO` stores source-target crosstalk coefficients for 64 amplifiers.

Extension header keywords:

| Keyword | 값 | 설명 |
| --- | --- | --- |
| `EXTNAME` | `XTALKINFO` | table name |
| `NXTALK` | `4096` | 64 x 64 rows |
| `XTALKVER` | `UNMEASURED` before calibration | crosstalk model version |
| `XTALKCAL` | `False` before calibration | true only after real coefficient calibration |

Columns:

| Column | Format | Unit | 설명 |
| --- | --- | --- | --- |
| `SOURCE_AMP` | `I` |  | source amplifier ID |
| `TARGET_AMP` | `I` |  | target amplifier ID |
| `XTALK_COEF` | `D` |  | crosstalk coefficient |
| `XTALK_ERROR` | `D` |  | coefficient uncertainty |
| `XTALK_VERSION` | `16A` |  | coefficient set version |
| `MEASURE_DATE` | `19A` | UTC | measurement date |
| `STATUS` | `12A` |  | `PLACEHOLDER`, `VALID`, `RETIRED`, etc. |

운영 기준:

- `XTALKCAL=False`이면 correction에 사용하지 않는다.
- 실측 후 `XTALK_COEF`, `XTALK_ERROR`, `XTALK_VERSION`, `MEASURE_DATE`, `STATUS`를 갱신한다.
- source-target ordering은 global `AMPID` 1-64를 기준으로 한다.

## 8. VOLTINFO Binary Table

`VOLTINFO`는 Archon/clock/bias voltage의 setpoint와 measured telemetry를 저장한다.

Extension header keywords:

| Keyword | 값 | 설명 |
| --- | --- | --- |
| `EXTNAME` | `VOLTINFO` | table name |
| `BIASVER` | `UNKNOWN` before commissioning | bias setting version |
| `CLKVER` | `UNKNOWN` before commissioning | clock setting version |
| `VOLTSTAT` | `UNKNOWN` before telemetry integration | voltage telemetry status |

Columns:

| Column | Format | Unit | 설명 |
| --- | --- | --- | --- |
| `VOLTNAME` | `16A` |  | voltage name |
| `SETPOINT` | `E` |  | commanded setpoint |
| `MEASURED` | `E` |  | measured value |
| `UNIT` | `8A` |  | unit, usually `V` |
| `STATUS` | `12A` |  | voltage telemetry status |

초기 voltage names:

```text
VOD, VRD, VOG, VSS, VDD, PCLKH, PCLKL, SCLKH, SCLKL
```

운영 기준:

- 신규 전자부 완성 후 Archon telemetry에서 실제 measured value를 채워야 한다.
- voltage setting 변경 시 `BIASVER` 또는 `CLKVER`를 갱신한다.

## 9. TELEMETRY Binary Table

`TELEMETRY`는 controller-level health/status 정보를 기록한다. 신규 전자부는 science Archon controller 2개를 사용하므로 기본 row 수는 2이다.

Extension header keywords:

| Keyword | 값 | 설명 |
| --- | --- | --- |
| `EXTNAME` | `TELEMETRY` | table name |
| `NCTRL` | `2` | number of science controllers |
| `TELSTAT` | `UNKNOWN` before telemetry integration | telemetry status |

Columns:

| Column | Format | Unit | 설명 |
| --- | --- | --- | --- |
| `CTRLID` | `I` |  | controller ID |
| `FWVERSION` | `16A` |  | firmware version |
| `BOARDTEMP` | `E` | deg C | controller board temperature |
| `READTIME` | `E` | s | readout time |
| `STATUS` | `12A` |  | controller status |
| `ERRORFLAG` | `I` |  | controller error flag |

운영 기준:

- `CTRLID=1`은 M,K chips를 담당한다.
- `CTRLID=2`는 N,T chips를 담당한다.
- `FWVERSION`, `BOARDTEMP`, `READTIME`, `STATUS`, `ERRORFLAG`는 exposure별 telemetry에서 채워야 한다.

## 10. 카메라 완성 후 반드시 확정해야 할 값

신규 전자부 카메라가 완성되면 아래 값은 placeholder가 아니라 실측/운영값으로 채워야 한다.

| 항목 | 관련 keywords/tables | 확정 방법 |
| --- | --- | --- |
| Controller identity | `CTRL1ID`, `CTRL1SN`, `CTRL1FW`, `CTRL2ID`, `CTRL2SN`, `CTRL2FW`, `TELEMETRY` | Archon controller inventory 및 firmware report |
| Timing configuration | `TIMCONF`, `TIMVER`, `CTRLVER` | final Archon timing script |
| Voltage telemetry | `VOLTINFO`, `BIASVER`, `CLKVER`, `VOLTSTAT` | electronics commissioning telemetry |
| Amp gain/read-noise | `GAIN`, `RDNOISE`, `AMPINFO` | bias/flat/photon-transfer calibration |
| Saturation/linearity | `SATURAT`, `SATLEVEL`, `LINMAX` | linearity sequence |
| Crosstalk | `XTALKINFO`, `XTALKVER`, `XTALKCAL` | bright source/crosstalk calibration |
| Read direction | `READDIR` | flat/star sequence orientation test |
| WCS reference | amp WCS placeholder, L1 WCS | L1 astrometric solution |
| Observatory metadata | `OBSERVAT`, `SITEID`, `LATITUDE`, `LONGITUD`, `ELEVATIO` | site configuration database |

## 11. 최소 검증 Checklist

운영 MEF를 release 또는 archive에 넣기 전 다음 항목을 확인한다.

| Check | 기대값 |
| --- | --- |
| FITS verify | Astropy `verify('exception')` 통과 |
| HDU count | 69 |
| First HDU | `PRIMARY` |
| Last four HDUs | `AMPINFO`, `XTALKINFO`, `VOLTINFO`, `TELEMETRY` |
| Amp image size | every amp HDU `(4616, 1200)` |
| `AMPINFO` rows | 64 |
| `XTALKINFO` rows | 4096 |
| `VOLTINFO` rows | instrument voltage row count |
| `TELEMETRY` rows | 2 |
| `CHIPLIST` | `M,K,N,T` |
| `RAWGROUP` | `MKNT` |
| `CHIPFLP` | `None` |
| `DATASEC`/`BIASSEC` | local overscan preserved |
| gzip integrity | `gzip -t` 통과 |

검증 예:

```bash
python3 -c "from astropy.io import fits; hdul=fits.open('output.fits', memmap=False); hdul.verify('exception'); print(len(hdul)); hdul.close()"
gzip -t output.fits.gz
```

## 12. L1 Product 생성 시 주의

L1 CCD-level images는 L0 amp image를 그대로 이어 붙여 만드는 단순 제품이 아니다. 다음 처리가 완료된 뒤 생성해야 한다.

1. 각 amp의 `BIASSEC` 기반 local overscan correction
2. amp-level bias correction
3. amp-level gain/read-noise/linearity/saturation correction
4. bad pixel mask 적용
5. `XTALKINFO`의 calibrated coefficient 기반 crosstalk correction
6. amp boundary seam 및 bias-jump 확인
7. calibrated CCD image assembly

따라서 L1 `SCI_M`, `SCI_K`, `SCI_N`, `SCI_T` product에는 L0 provenance와 calibration history를 반드시 남겨야 한다.

## 13. Revision History

| Version | Date | Change |
| --- | --- | --- |
| v1.0 | 2026-06-22 | 신규 전자부 카메라 완성 후 사용할 L0 MEF FITS 주요 keyword 최종 정리 |


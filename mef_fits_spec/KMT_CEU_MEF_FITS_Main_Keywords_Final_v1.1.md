# KMT-CEU 신규 전자부 카메라 MEF FITS 주요 키워드 최종 정리

버전: v1.1  
작성일: 2026-09-23  
기준 converter: `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` **v2.5.0** (product `PRODVER` **v2.2.0**, `GEOMVER` `CEU-L0AMP-v2.1` 불변)  
기준 ICD: `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md` (docx 동본)

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
| `VOLTINFO` | CCD bias/clock 자리(공급원 없음) + 컨트롤러 전원 레일 실측 전압·전류 (§8) |
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
| `CREATOR` | Generated | `kmt_ceu_l0amp_mknt2mef_v2.5.0` | MEF 생성 프로그램 (software version) |
| `BUNIT` | From raw | `ADU` | pixel unit |
| `DATAPROD` | Required | `L0_AMP` | product type |
| `PRODVER` | Generated | `v2.2.0` | product format version. software version과 분리해서 올린다 (D-004) |
| `PIPEVER` | Generated | `kmt_ceu_l0amp_mknt2mef-v2.5.0` | converter/pipeline version (software version) |
| `GEOMVER` | Generated | `CEU-L0AMP-v2.1` | geometry definition version. PRIMARY와 `AMPINFO` extension header가 같은 값을 가진다. amp ordering/section/HDU layout이 바뀔 때만 올린다 (D-004) |

### 4.2 Raw Provenance 및 Archon Geometry

| Keyword | 상태 | 값/예시 | 설명 |
| --- | --- | --- | --- |
| `RAWGROUP` | Required | `MKNT` | raw file grouping convention |
| `CHIPLIST` | Required | `M,K,N,T` | 공식 science chip order |
| `MKFILE` | Generated | `KMTK.20260915.000034.MK.fits` | source MK raw FITS. `<SITE>` ∈ {`KMTC`, `KMTS`, `KMTA`, `KMTK`} (ICD v4.3 §2.1 — D-011, D-017). `KMTT`는 폐지되었다 |
| `NTFILE` | Generated | `KMTK.20260915.000034.NT.fits` | source NT raw FITS. 같은 규칙 |
| `NUMFILES` | Required | `2` | MEF 생성에 사용한 raw file 수 |
| `EXPID` | From raw | `KMTK.20260915.000034` | ICS 카운터가 배정한 exposure 식별자. `FILENAME`과 함께 이 노출의 정체를 이룬다 (D-016 · D-019 — `UNIQNAME` 폐지) |
| `DETID` | Generated | `MKNT` | 이 MEF가 합친 raw detector pair. raw 한 장은 `MK` 또는 `NT`이고 MEF는 둘을 합치므로 항상 `MKNT` |
| `DATASRC` | From raw | `ARCHON_SCIENCE` | pixel data source type — 실기 취득분과 시뮬레이션분을 가른다 |
| `FPAID` | From raw | `FPA#0` | focal plane assembly ID |
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
| `PIXSCALE` | Required | `0.395` | unbinned pixel scale [arcsec/pixel]. Gaia DR3 대조 **실측값** 0.3952±0.00001 (2026-06-30, 16 chip 해) — 구 nominal `0.400`은 폐기되었다. ⭐ 이 값 하나가 seed WCS의 `CD` 행렬 전체를 정한다 (`CD` = ∓`PIXSCALE`/3600 deg/px). converter는 raw의 `PIXSCALE` 선언을 이 값과 대조하고 어긋나면 경고한다 |
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
| `DARKTIME` | From raw | cumulative dark time in seconds. 신규 raw는 이 카드를 싣지 않으므로 `EXPTIME`을 하한으로 쓴다 |
| `LEDFLASH` | From raw | projector LED flash duration [ms] |
| `TSHOPEN` | From raw | shutter open time |
| `TSHSHUT` | From raw | shutter close time |
| `FILTER` | From raw | filter name |
| `FILENAME` | Generated | output MEF filename. `EXPID`(§4.2)와 함께 이 노출의 정체를 이룬다 |
| ~~`UNIQNAME`~~ | Retired | **기록하지 않는다.** raw 공급원이 D-016/D-019로 폐지되어 v2.5.0 이전에는 항상 빈 카드였다. 정체는 `FILENAME` + `EXPID`가 진다. ⛔ 되살리지 말 것 |

### 4.5 Electronics 및 Calibration Version

| Keyword | 상태 | 예시 | 설명 |
| --- | --- | --- | --- |
| `INSTRUME` | From raw | `KMTK 18k CCD` | instrument name. 사이트 코드(`<SITE>` prefix)가 아니라 기기명이다 |
| `CONTROLL` | Required | `STA ARCHON` | controller type |
| `NCTRL` | Required | `2` | science Archon controller 수 |
| `CTRL1ID` | From raw | site dependent | controller 1 ID |
| `CTRL1SN` | From raw | site dependent | controller 1 serial number |
| `CTRL1FW` | From raw | site dependent | controller 1 firmware |
| `CTRL2ID` | From raw | site dependent | controller 2 ID |
| `CTRL2SN` | From raw | site dependent | controller 2 serial number |
| `CTRL2FW` | From raw | site dependent | controller 2 firmware |
| `CTRL1CFG` | From raw | `KMTK_SCI_113_STA0200_R2613_MK` | controller 1 Archon config (ACF) name. 타이밍·바이어스·클럭 버전 문자열이 여기로 귀속된다 |
| `CTRL2CFG` | From raw | `KMTK_SCI_112_STA0212_R2613_NT` | controller 2 Archon config (ACF) name |
| `ICSBUILD` | From raw | `v0.0.0:2026-08-28T04:00Z` | acquisition software version/build |
| `RDMODE` | From raw | `NORMAL` | controller readout mode setting. `READMODE`(§4.3, `64AMP`)와 다른 항목이다 |
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
| `AMPCHAR` | Conditional | `amp_characterization_LEGACY-CTIO-20260611.csv` | amp characterization table 파일명. `--ampchar`로 실측 `GAIN`/`RDNOISE`/`SATURAT`/`LINMAX`를 스탬핑한 경우에만 기록한다. 이 카드가 없으면 §5.4 값은 placeholder다 (D-005) |

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
| `UT` | Generated | UTC timestamp. `DATE-OBS`에서 조립한다 — 폐지된 `TSHOPEN`은 시각 부분을 비운 채 넘어온다. `DATE-OBS`/`MJD-OBS`/`JD`/`UT`는 같은 exposure start time이다 |
| `RADECSYS` | From raw | coordinate system. default `ICRS`. **폐기 철자지만 유지한다** — L1 `steps/assemble.py`가 이 이름을 문자 그대로 복사한다 |
| `RADESYS` | Generated | FITS 표준 철자. `RADECSYS`와 같은 값을 병기한다 |
| `RA` | From raw | telescope right ascension — 6진 **시(hours)**. ⛔ 도(degree)가 아니다 |
| `DEC` | From raw | telescope declination — 6진 도. 부호는 **값 전체**에 적용한다 (`-30:00:00.4` = −30.00011, −29.99989이 아니다) |
| `RA_DEG` | Generated | telescope RA [deg] = `RA` × 15. seed WCS `CRVAL1`이 이 값이다 (§5.5). 파싱 실패 시 **기록하지 않는다** |
| `DEC_DEG` | Generated | telescope Dec [deg]. seed WCS `CRVAL2`가 이 값이다. 파싱 실패 시 기록하지 않는다 |
| `EQUINOX` | Generated | coordinate equinox. **float로 쓴다** — raw는 문자열 `'2000.000'`으로 넘기는데 그대로 중계하면 FITS 표준 위반이고 fitsverify가 거부한다 |
| `HA` | From raw | hour angle |
| `ST` | From raw | local sidereal time |
| `SECZ` | From raw | secant of zenith distance (raw가 주는 문자열 그대로) |
| `AIRMASS` | Generated | airmass = sec(ZD) at start [float]. `SECZ`를 수치화한 같은 양이다 |
| `ALT` | From raw | telescope altitude |
| `AZ` | From raw | telescope azimuth |
| `TCSTIME` | From raw | TCS time system. default `UTC` |
| `TCSDRIV` | From raw | telescope drive status |
| `TELMOVE` | From raw | telescope motion status |

### 4.7 Seed WCS 상태, 프레임 종류, 채널 맵 검증 (v1.1, D-023)

L0 amp extension의 sky WCS는 **L1 Gaia 측성의 seed**이고 산출 WCS가 아니다. PRIMARY는 그 seed가 실렸는지, 안 실렸다면 왜인지만 선언한다. 좌표 카드 자체는 64개 extension이 가진다 (§5.5). ⛔ PRIMARY에는 `CTYPE`/`CRVAL`/`CRPIX`/`CD`를 쓰지 않는다 — `NAXIS=0`이라 쓸 자리가 없고, IRAF `INHERIT` 혼동만 부른다.

| Keyword | 상태 | 예시 | 설명 |
| --- | --- | --- | --- |
| `WCSSKY` | Required | `T` | 이 프레임이 하늘을 보는가. `IMAGETYP` ∈ {`BIAS`, `DARK`, `DOMEFLAT`}이면 `F`. **항상 기록한다** |
| `WCSOMIT` | Required | `F` | seed WCS를 쓰지 않았는가. `WCSSKY=F`이거나 TCS 포인팅이 파싱되지 않으면 `T` |
| `WCSSOLVE` | Required | `F` | 측성 해가 있는가. L0에서는 **항상 `F`**. L1 Gaia 해가 성공하면 `T`로 뒤집는다 |
| `WCSNAME` | Conditional | `TCS-SEED` | seed를 쓴 경우에만 기록한다 |
| `WCSAPPRX` | Conditional | `T` | WCS가 근사인가. seed를 쓴 경우에만 기록하고 L0에서는 항상 `T`. L1 Gaia 해가 성공하면 `F`로 뒤집는다 |
| `BOREPIXX` | Conditional | `9418.0` | boresight의 `DETSIZE` 모자이크 X 픽셀. seed를 쓴 경우에만 기록한다 |
| `BOREPIXY` | Conditional | `9699.0` | boresight의 모자이크 Y 픽셀 |
| `CHMAPOK` | Required | `T` | raw `CHMAP_*`가 `Detector_Ch_to_AmpID_Map`과 일치하는가 (C-11). 어긋나면 `F`이고 `HISTORY`에 amp별로 남는다 |
| `AMPIDMAP` | Required | `Detector_Ch_to_AmpID_Map_v1.1` | 대조에 쓴 채널↔AmpID 맵 판 |
| `RAILREF` | Required | `RAWSPEC-v1.13-5.6.1` | `Cn_VOLT`/`Cn_TEMP` 자리 순서 규격 판 (§8) |

**상태 어휘는 파이프라인 것을 그대로 쓴다.** L0가 "아직 아님" 값으로 미리 싣고 L1은 카드를 만드는 대신 값만 뒤집는다.

| 단계 | 플래그 |
| --- | --- |
| L0 (이 산출물) | `WCSNAME='TCS-SEED'` · `WCSAPPRX=T` · `WCSSOLVE=F` |
| L1 Gaia 해 성공 | `WCSAPPRX=F` · `WCSSOLVE=T` + `WCSRMS`/`WCSNSTAR`/`WCSNREF`/`WCSNMAT`, 카탈로그는 L1 primary `WCSCAT`, 해 성공 CCD 수는 `WCSNSOLV` |
| L1 Gaia 해 실패 | seed 유지 · `WCSSOLVE=F` + 사유 `WCSFAIL` |

⛔ **`WCSSKY=F`는 실패가 아니다.** L1은 사유 `NOT_SKY_FRAME`으로 측성을 건너뛴다. 하룻밤 바이어스 20장을 실패 20건으로 세면 안 된다.

⛔ **L0의 seed 상태 카드는 L1 primary로 넘기지 않는다** — `WCSNAME`·`WCSAPPRX`·`WCSSOLVE`·`WCSOMIT`·`BOREPIXX`·`BOREPIXY`는 `io_l1.CARRY_EXCLUDE`에 있다. 안 그러면 Gaia로 푼 SCI 위에서 primary가 "안 풀렸음"을 선언한다.

### 4.8 Auxiliary, Focus, Dome, Thermal Keywords

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
| `CTRUNIT` | From raw | `MK` or `NT` | 이 chip을 담은 raw 컨트롤러 유닛 |
| `CCDPORT` | From raw | `A` or `B` | 이 CCD를 읽는 컨트롤러 포트. 불명이면 `?` |
| `CHANNAME` | From raw | `MD16` | CCD 출력 채널 토큰 `<chip><A\|D><nn>` (raw `CHMAP_*`, 4자 — 구 3자 파서는 고쳐야 한다). 불명이면 `UNKNOWN` |
| `CHANNUM` | From raw | `1` to `16` | CCD 출력 채널 번호. 불명이면 `-1` |
| `IMGSEC` | From raw | `D-TOP` | e2v image section과 독출 단. chip마다 A/D 귀속이 갈린다 |
| `CHMAPSRC` | From raw | `CHMAP_LT` | 이 정체를 읽어 온 raw 카드 |
| `MODULE` | From raw | `1` or `2` | 컨트롤러 포트 index (1 = A, 2 = B). 불명이면 `-1` |
| `CHANNEL` | From raw | `1` to `16` | CCD 출력 채널 번호 (= `CHANNUM`). 불명이면 `-1` |

**v1.1 (C-11):** `MODULE`/`CHANNEL`은 예전에 amp 번호에서 지어낸 값이었고 실배선과 달랐다. 이제 raw `CHMAP_LT`/`LB`/`RT`/`RB` 토큰에서 끌어내고 `Detector_Ch_to_AmpID_Map_v1.1`과 대조한다 (PRIMARY `CHMAPOK`). `CHANNEL` 범위가 **1–8에서 1–16으로** 바뀌었다 — CCD 출력 채널은 chip당 16개다.

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

### 5.5 Amp Extension Observation, Seed WCS, IRAF 변환 Keywords

Amp extension에도 quick-look 및 downstream compatibility를 위해 주요 observation keyword를 반복 기록한다.

| Group | Keywords |
| --- | --- |
| Observation | `FILTER`, `PROJID`, `IMAGETYP`, `OBJECT`, `OBSTYPE` |
| Pointing | `RA`, `DEC`, `HA`, `ST`, `SECZ`, `AIRMASS`, `ALT`, `AZ`, `UT` |
| Frame class | `WCSSKY` |

⛔ `RA`/`DEC`는 파싱되지 않으면 **기록하지 않는다.** `'00:00:00.00'` 같은 기본값을 쓰지 않는다 — 형식은 유효하고 뜻은 틀린 좌표라 하류에서 걸러지지 않는다 (raw spec 5.0).

#### Seed WCS (v1.1, D-023)

이 WCS의 용도는 **L1 Gaia 측성의 초기값 하나뿐이다.** 산출 WCS가 아니므로 ⛔ 이것으로 좌표를 재면 안 된다. 위치는 해가 풀린 L1 WCS에서만 나온다. 상태 플래그의 뜻과 L0→L1 인계는 §4.7에 있다.

| Keyword | 상태 | 예시 | 설명 |
| --- | --- | --- | --- |
| `WCSAXES` | Conditional | `2` | WCS 축 수 |
| `CTYPE1` / `CTYPE2` | Conditional | `RA---TAN` / `DEC--TAN` | gnomonic(TAN) 투영 |
| `CUNIT1` / `CUNIT2` | Conditional | `deg` | 축 단위 |
| `CRVAL1` / `CRVAL2` | Conditional | `198.144583` / `1.395667` | tangent point = 망원경 boresight [deg]. **64개 extension 전부 같은 값**이다 |
| `CRPIX1` / `CRPIX2` | Conditional | `9418.0` / `-5082.0` | 이 amp 배열에서의 boresight 위치 [px]. amp별 어긋남은 전부 여기가 진다 |
| `CD1_1` … `CD2_2` | Conditional | `∓PIXSCALE/3600`, off-diagonal `0.0` | **64 amp 전부 동일**하다 |
| `RADECSYS` / `RADESYS` | Conditional | `ICRS` | `CRVAL`의 기준계. raw가 선언한 값을 중계한다 |
| `EQUINOX` | Conditional | `2000.0` | float |
| `WCSNAME` | Conditional | `TCS-SEED` | 이 WCS의 정체 |
| `WCSAPPRX` / `WCSSOLVE` | Conditional | `T` / `F` | §4.7의 상태 어휘 |
| `WCSDIM` | Conditional | `2` | coordinate system dimensionality |
| `WCSOMIT` | Conditional | `T` | seed를 쓰지 않은 경우에만 기록한다 |

**tangent point는 하나다.** 64개 extension이 같은 `CRVAL`을 공유하고, amp별 어긋남은 `CRPIX`가 전부 진다. `CRPIX`는 boresight 모자이크 픽셀(`BOREPIXX`/`BOREPIXY`)과 그 amp의 `DETSEC` 원점에서 계산하며, **overscan이 왼쪽인 strip(`AMPSEQ` 5–8·13–16)은 `CRPIX1`에 +48**을 더한다. 불변식은

```text
CRPIX1 - LTV1 + DTV1 == BOREPIXX          (Y도 같다)
```

**`CD` 행렬은 64 amp 전부 동일하고 amp별 부호 반전을 하지 않는다.** serial 독출 방향(strip 1–4 ↔ 5–8) · TOP/BOT · e2v image section(A/D)이 chip마다 갈리지만 ⛔ 그 중 어느 것도 저장 순서에 닿지 않는다 — raw spec 4.3이 raw 프레임을 두 축 모두 CCD 좌표 오름차순으로 저장하도록 **요구**하고, K·N의 180° 장착은 채널→타일 순서가 이미 흡수한다. ⚠️ ICD §4의 "chip-dependent flip을 적용하지 않는다"만 읽고 뒤집으면 **64 중 32 amp가 어긋난다** (ICD v4.3 §4 주석).

⛔ **seed를 쓰지 않을 때는 위 카드를 하나도 쓰지 않는다 — `WCSDIM` 포함.** `CTYPE`만 있고 `CRVAL`이 없으면 리더가 `CRVAL=0`을 기본값으로 삼아 춘분점 근방으로 조용히 풀린다. `WCSOMIT=T`가 그 부재가 의도된 것임을 기계가 읽을 수 있게 남긴다.

#### IRAF 픽셀 변환 (v1.1, D-023)

| Group | Keywords | 대응 |
| --- | --- | --- |
| image ↔ CCD | `LTV1`, `LTV2`, `LTM1_1`, `LTM1_2`, `LTM2_1`, `LTM2_2` | `CCDSEC` |
| image ↔ amplifier | `ATV1`, `ATV2`, `ATM1_1`, `ATM1_2`, `ATM2_1`, `ATM2_2` | `AMPSEC` |
| image ↔ detector mosaic | `DTV1`, `DTV2`, `DTM1_1`, `DTM1_2`, `DTM2_1`, `DTM2_2` | `DETSEC` |

행렬은 전부 항등이다 — raw spec 4.3이 모든 amp를 두 축 오름차순으로 저장하므로 거울상이 없고, 갈리는 overscan 방향은 offset만 옮긴다.

⭐ **이 셋은 프레임 종류와 무관하게 항상 기록한다** — `WCSSKY=F`인 프레임에도 쓴다. 검출기 좌표지 하늘 좌표가 아니고, 마스터 프레임 조립이 쓴다.

## 6. AMPINFO Binary Table

`AMPINFO`는 image extension header와 동일한 geometry/electronics 정보를 machine-readable table로 제공한다. Pipeline은 가능하면 `AMPINFO`를 authoritative map으로 사용한다.

Extension header keywords:

| Keyword | 값 | 설명 |
| --- | --- | --- |
| `EXTNAME` | `AMPINFO` | table name |
| `NAMP` | `64` | number of amplifier rows |
| `GEOMVER` | `CEU-L0AMP-v2.1` | geometry definition version. PRIMARY의 동명 카드와 항상 같은 값이어야 한다 (§4.1) |
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
| `CHANNEL` | `I` |  | CCD 출력 채널 번호 1–16 (구 1–8). 불명 `-1` |
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
| `XTALKGROUP` | `8A` |  | crosstalk/electronics group. v1.1부터 실제 컨트롤러 포트 기준 (`MK-A`, `MK-B`, `NT-A`, `NT-B`) |
| `CHANNAME` | `8A` |  | CCD 출력 채널 토큰 (`MD16`). 불명 `UNKNOWN` |
| `CHANNUM` | `I` |  | CCD 출력 채널 번호 1–16. 불명 `-1` |
| `CCDPORT` | `2A` |  | 컨트롤러 포트 `A`/`B`. 불명 `?` |
| `IMGSEC` | `8A` |  | e2v image section과 독출 단 (`D-TOP`). 불명 `UNKNOWN` |
| `CTRUNIT` | `2A` |  | raw 컨트롤러 유닛 `MK`/`NT` |
| `CHMAPSRC` | `8A` |  | 이 정체를 읽어 온 raw 카드 (`CHMAP_LT`) |
| `CRPIX1` | `D` | pixel | seed WCS 기준픽셀 X. ⛔ seed가 없으면 `-999.0` |
| `CRPIX2` | `D` | pixel | seed WCS 기준픽셀 Y. ⛔ seed가 없으면 `-999.0` |
| `LTV1` | `D` | pixel | image↔CCD 변환 offset X. 프레임 종류와 무관하게 항상 실값 |
| `LTV2` | `D` | pixel | image↔CCD 변환 offset Y |
| `DTV1` | `D` | pixel | image↔detector mosaic 변환 offset X |
| `DTV2` | `D` | pixel | image↔detector mosaic 변환 offset Y |

컬럼 수는 `PRODVER v2.2.0`에서 **52개**다 (`v2.1.1`은 40개). ⭐ **새 12개는 표 끝에 덧붙였으므로 기존 컬럼의 위치 색인은 그대로다** (D-023 항목 8ⓑ).

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
| `VOLTSTAT` | `OK` / `PARTIAL` / `NC` / `UNKNOWN` | voltage telemetry status. `NC`는 컨트롤러가 `VALID=0`으로 응답한 것이고 `UNKNOWN`은 카드 자체가 없는 것이다 — 구분해서 싣는다 |
| `NVOLT` | `37` | 이 표의 행 수. ⛔ **행 수의 정본은 이 카드다** — 37을 상수로 박지 말 것 |
| `RAILREF` | `RAWSPEC-v1.13-5.6.1` | 레일·모듈 자리 순서 규격 판. 값에 이름표가 없으므로 이 판 없이는 해석할 수 없다 |

Columns:

| Column | Format | Unit | 설명 |
| --- | --- | --- | --- |
| `VOLTNAME` | `16A` |  | voltage name |
| `SETPOINT` | `E` |  | commanded setpoint |
| `MEASURED` | `E` |  | measured value |
| `UNIT` | `8A` |  | unit, usually `V` |
| `STATUS` | `12A` |  | voltage telemetry status |

행 구성 (v1.1, C-18):

| 구간 | 행 수 | `VOLTNAME` | 값 |
| --- | ---: | --- | --- |
| CCD bias/clock | 9 | `VOD`, `VRD`, `VOG`, `VSS`, `VDD`, `PCLKH`, `PCLKL`, `SCLKH`, `SCLKL` | **공급원 없음.** `SETPOINT`/`MEASURED` = `-999.0`, `STATUS` = `PLACEHOLDER` |
| 컨트롤러 레일 전압 | `NCTRL` × 7 | `C1_P2V5` … `C1_P35V`, `C2_*` | raw `Cn_VOLT` 실측, `UNIT` = `V` |
| 컨트롤러 레일 전류 | `NCTRL` × 7 | `C1_P2V5_I` … `C1_P35V_I`, `C2_*` | raw `Cn_CURR` 실측, `UNIT` = `A` |

레일 순서는 `P2V5`, `P5V`, `P6V`, `N6V`, `P17V`, `N17V`, `P35V` 고정이다 (raw spec 5.6.1). science 컨트롤러는 7자리이고 guide는 8자리(`HEATER` 추가)이므로 ⛔ science 프레임을 guide 표로 해석하면 안 된다.

운영 기준:

- ⛔ **9개 bias/clock 행은 `0.0`이 아니라 `-999.0`이다.** `0.0 V`는 `VSS`의 정상값이라 결측을 실측처럼 보이게 한다. 그 카드 계열(`VOLT<n>`/`VSET<n>`/`VMEA<n>`)은 폐지되었으므로 commissioning 전까지 공급원이 없다.
- 레일 값은 raw가 주므로 placeholder가 아니다. 다만 `SETPOINT`은 raw에 없어 `-999.0`이다.
- voltage setting 변경 시 `BIASVER` 또는 `CLKVER`를 갱신한다.

## 9. TELEMETRY Binary Table

`TELEMETRY`는 controller-level health/status 정보를 기록한다. 신규 전자부는 science Archon controller 2개를 사용하므로 기본 row 수는 2이다.

Extension header keywords:

| Keyword | 값 | 설명 |
| --- | --- | --- |
| `EXTNAME` | `TELEMETRY` | table name |
| `NCTRL` | `2` | number of science controllers |
| `TELSTAT` | `OK` / `PARTIAL` / `NC` / `UNKNOWN` | telemetry status. `VOLTSTAT`과 같은 어휘다 |

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
- `BOARDTEMP`는 **실측이다** — raw `Cn_TEMP`의 **1번 자리(`Backplane`)** 다 (C-18). ⛔ 10개 모듈 자리를 평균하지 않는다.
- `STATUS`는 `Cn_*` 세 카드에서 유도한다.
- ⛔ `FWVERSION`(`UNKNOWN`)·`READTIME`(`-1.0`)·`ERRORFLAG`(`-1`)는 sentinel로 남는다. 신규 raw가 공급원을 **의도적으로** 싣지 않는다 — 컨트롤러 오류는 별도 경로로 감시한다. 지어내면 하류가 컨트롤러의 주장으로 읽는다.

## 10. 카메라 완성 후 반드시 확정해야 할 값

신규 전자부 카메라가 완성되면 아래 값은 placeholder가 아니라 실측/운영값으로 채워야 한다.

| 항목 | 관련 keywords/tables | 확정 방법 |
| --- | --- | --- |
| Controller identity | `CTRL1ID`, `CTRL1SN`, `CTRL1FW`, `CTRL2ID`, `CTRL2SN`, `CTRL2FW`, `TELEMETRY` | Archon controller inventory 및 firmware report |
| Timing configuration | `TIMCONF`, `TIMVER`, `CTRLVER` | final Archon timing script |
| Voltage telemetry | `VOLTINFO` 의 9개 bias/clock 행, `BIASVER`, `CLKVER` | electronics commissioning telemetry. 컨트롤러 레일 28행은 이미 raw 실측으로 채워진다 (C-18) |
| Amp gain/read-noise | `GAIN`, `RDNOISE`, `AMPINFO` | bias/flat/photon-transfer calibration |
| Saturation/linearity | `SATURAT`, `SATLEVEL`, `LINMAX` | linearity sequence |
| Crosstalk | `XTALKINFO`, `XTALKVER`, `XTALKCAL` | bright source/crosstalk calibration |
| Read direction | `READDIR` | flat/star sequence orientation test |
| WCS 기준 | L0 seed WCS (`WCSAPPRX=T`, `WCSSOLVE=F`), L1 solved WCS | L1 Gaia 측성 해가 `WCSAPPRX=F`·`WCSSOLVE=T`로 뒤집는다. L0 seed 자체는 별로 검증된 적이 없다 |
| Observatory metadata | `OBSERVAT`, `SITEID`, `LATITUDE`, `LONGITUD`, `ELEVATIO` | site configuration database |

## 11. 최소 검증 Checklist

운영 MEF를 release 또는 archive에 넣기 전 다음 항목을 확인한다.

| Check | 기대값 |
| --- | --- |
| FITS verify | Astropy `verify('exception')` 통과 |
| FITS 고정형식 | `fitsverify` 0 error. ⚠️ Astropy만으로는 부족하다 — 문자열 값이 free format이면 Astropy는 통과시키고 `fitsverify`는 거부한다 |
| HDU count | 69 |
| First HDU | `PRIMARY` |
| Last four HDUs | `AMPINFO`, `XTALKINFO`, `VOLTINFO`, `TELEMETRY` |
| Amp image size | every amp HDU `(4616, 1200)` |
| `AMPINFO` rows | 64 |
| `XTALKINFO` rows | 4096 |
| `VOLTINFO` rows | `NVOLT`와 일치 (2-controller science 산출물은 37) |
| `TELEMETRY` rows | 2 |
| `CHIPLIST` | `M,K,N,T` |
| `RAWGROUP` | `MKNT` |
| `CHIPFLP` | `None` |
| Seed WCS | `WCSSKY=T`이면 64 extension 전부 `CRVAL`·`CD` 동일, `CRPIX1 - LTV1 + DTV1 == BOREPIXX`. `WCSSKY=F`이면 WCS 카드 0개 + `WCSOMIT=T` |
| 채널 맵 | `CHMAPOK=T` |
| Checksum | 전 HDU `CHECKSUM`/`DATASUM` 검증 통과 |
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
| v1.1 | 2026-09-23 | converter v2.5.0 / `PRODVER` v2.2.0 반영 (DECISION_LOG **D-023**). §4.7 신설 — seed WCS 상태·프레임 종류(`WCSSKY`)·채널 맵 검증(`CHMAPOK`), 구 §4.7은 §4.8로. §5.5 전면 개정 — amp WCS를 "placeholder"에서 **L1 Gaia 측성의 seed**로 규정하고 `WCSNAME`/`WCSAPPRX`/`WCSSOLVE` 상태 어휘와 전면 생략 규칙을 명시, IRAF `LTV`/`ATV`/`DTV` 군 신설. §5.2 채널 정체 6장 신설, `CHANNEL` 범위 1–8 → **1–16**, `MODULE` 재정의 (C-11). §6 `AMPINFO` 40 → **52 컬럼** (끝에 덧붙여 기존 색인 불변). §8 `VOLTINFO` 9 → **37행** 구성표와 `NVOLT`/`RAILREF` 신설, bias/clock 자리 `0.0` → `-999.0` (C-18). §9 `TELEMETRY` `BOARDTEMP` 실측 명시. `PIXSCALE` `0.400` → **`0.395`** (Gaia DR3 실측 — 이 값이 seed `CD`를 정한다). `UNIQNAME` 폐지 명시 (D-016·D-019). `EXPID`·`DETID`·`DATASRC`·`FPAID`·`CTRLnCFG`·`ICSBUILD`·`RDMODE`·`LEDFLASH`·`AMPCHAR`·`GEOMVER`·`RADESYS`·`RA_DEG`/`DEC_DEG`·`AIRMASS`·`TCSTIME` 등 provenance/좌표 카드 수록. §11 체크리스트에 `fitsverify`·seed WCS 불변식·`CHMAPOK`·checksum 추가. 기준 converter v2.2.0 → v2.5.0, 기준 ICD v4.1 → **v4.3**. geometry 불변 — `GEOMVER` 유지 |


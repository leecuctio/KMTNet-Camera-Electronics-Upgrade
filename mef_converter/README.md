# KMTNet-CEU MEF Converter

최종 갱신일: 2026-09-04

## 목적

이 디렉토리는 KMT-CEU Archon MK/NT raw FITS를 **L0 64-amplifier raw MEF**로 변환하는 converter와 그 참고 문서를 모은 곳이다. 생성되는 MEF의 데이터 산출물 규격(keyword/ICD)은 [`../mef_fits_spec/`](../mef_fits_spec/README.md)에서 관리한다.

`mef_fits_spec/`(규격)과 `mef_converter/`(구현)을 분리해, 규격 변경과 코드 변경을 독립적으로 추적한다.

## 현재 기준선

| 구분 | 파일 | 버전 |
| --- | --- | --- |
| Converter (최종 실행 파일) | [`kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) | v2.5.0 |
| Product version (`PRODVER`) | — | `v2.2.0` |
| Geometry version (`GEOMVER`) | — | `CEU-L0AMP-v2.1` (불변) |
| 기준 ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.2.md` (docx 동본) | v4.2 |

## 디렉토리 구조

| 경로 | 내용 |
| --- | --- |
| `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` | 현행 converter (순수 Python + NumPy, 독립형 FITS writer) |
| `kmt_ceu_legacy32_to_l0amp_mef_v2.py` | 구형 32-amp MEF → 신형 64-amp L0 MEF **목업** 변환기 v2.0 (독립 실행형, 파이프라인 개발용) |
| `run_kmt_ceu_l0amp_example.sh` | 실행 예제 (실행 위치와 무관하게 동작) |
| `README_KMT_CEU_L0AmpRaw_Converter_v2.1.1.md` | 상세 사용법/검증 결과 |
| `KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` / `.docx` | 작업 정리 (md가 diff 기준본, docx는 배포본) |
| `archive/` | 구버전/개발 스크립트 보관. 운영 기준이 아님 |

## 실행

repo 루트에서:

```bash
python3 mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  raw/KMTA.20260116.000001.MK.fits \
  -o kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits \
  -f --gzip
```

또는 예제 스크립트 (입력/출력 기본값은 repo 루트 기준, `$1`/`$2`로 변경 가능):

```bash
bash mef_converter/run_kmt_ceu_l0amp_example.sh
```

### seed sky WCS — L1 Gaia 측성의 초기값 (v2.5.0)

v2.4.0 까지 amp extension 의 `CRVAL1/2`·`CRPIX1/2` 는 **0.0 하드코딩 placeholder** 였다.
CTYPE/CD 는 유효했으므로 ds9·astropy 가 오류 없이 **춘분점 근방(RA≈359.9, Dec≈+0.25)** 으로
풀었다 — 조용히 틀린 좌표라 하류에서 걸러지지 않았다.

v2.5.0 은 TCS 포인팅에서 WCS 를 만든다.

- **tangent point = 망원경 boresight** — `RA`(6진 **시**, ×15) · `DEC`(6진 **도**, 부호는 값 전체에)
  에서 계산하고, **64개 extension 전부 같은 `CRVAL`** 을 싣는다. amp 별 어긋남은 전부 `CRPIX` 가 진다.
  boresight 는 DETSIZE 모자이크 픽셀 `(BORESIGHT_X, BORESIGHT_Y) = (9418.0, 9699.0)` 이고
  primary `BOREPIXX`/`BOREPIXY` 로 공개한다.
- **strip 5–8 은 `CRPIX1` 에 +48** — overscan 이 타일 왼쪽이라 active 첫 열이 local x=49 다.
- **CD 행렬은 64 amp 전부 동일하다.** serial 독출 방향(strip 1–4 vs 5–8) · TOP/BOT · e2v
  image section(A/D) 이 chip 마다 갈리지만 **저장 순서에는 닿지 않는다** — raw spec 4.3 이
  raw 프레임을 두 축 모두 CCD 좌표 오름차순으로 저장하도록 **요구**하고, K·N 의 180° 장착은
  채널→타일 순서가 이미 흡수한다. 여기서 부호를 뒤집으면 64 중 32 amp 가 틀어진다.
- **이 WCS 의 용도는 단 하나 — L1 Gaia 측성의 초기값이다.** 산출 WCS 가 아니므로 이것으로
  좌표를 재면 안 된다. 상태 플래그는 파이프라인이 이미 쓰고 있는 어휘를 그대로 쓴다
  (`kmt_ceu_preproc/astrometry.py`):

  | 단계 | 플래그 |
  | --- | --- |
  | **L0 (이 변환기)** | `WCSNAME='TCS-SEED'` · `WCSAPPRX=T` · `WCSSOLVE=F` |
  | **L1 Gaia 해 성공** | `WCSAPPRX=F` · `WCSSOLVE=T` · `WCSRMS`/`WCSNSTAR`/`WCSNREF`/`WCSNMAT`, 카탈로그는 primary `WCSCAT`, 해 성공 CCD 수는 `WCSNSOLV` |
  | **L1 Gaia 해 실패** | seed 를 그대로 두고 `WCSSOLVE=F` + 사유 `WCSFAIL` |

  L0 가 `WCSCAL` 같은 새 이름을 만들지 않고 `WCSAPPRX`/`WCSSOLVE` 를 **"아직 아님" 값으로**
  미리 실어두므로, L1 은 새 카드를 만드는 게 아니라 **값만 뒤집는다**.
- **하늘을 안 보는 프레임에는 seed 를 아예 쓰지 않는다** (`WCSSKY`).
  `IMAGETYP` 통제 어휘(raw spec 5.4: `BIAS`/`DARK`/`OBJECT`/`FLAT`/`SKY`/`DOMEFLAT`)로 가른다.

  | `IMAGETYP` | `WCSSKY` | seed WCS | L1 측성 |
  | --- | :---: | :---: | --- |
  | `BIAS` · `DARK` · `DOMEFLAT` | `F` | **안 씀** (`WCSOMIT=T`) | 건너뜀 — 사유 `NOT_SKY_FRAME`, **실패가 아니다** |
  | `OBJECT` · `SKY`(박명 플랫) · `FLAT` | `T` | 씀 | 시도 |

  하늘을 안 본 프레임에 하늘 좌표를 박아 두는 것은 raw spec 5.0 이 금지한 *"형식만 유효한
  틀린 값"* 이다. 또 이 플래그가 없으면 하룻밤 바이어스 20장이 각각 `WCSSOLVE=F` + `WCSFAIL`
  을 남겨 **실패 20건처럼 읽힌다** — 실제로는 해당 없음이다.
  `SKY` 는 대체로 별이 보이므로 seed 를 싣고 정상적으로 시도한다. `FLAT` 은 어휘상 돔/박명이
  갈리지 않으므로 **시도하는 쪽**으로 둔다 (잘못 건너뛰면 조용히 손해, 잘못 시도하면 플래그 하나).
  ⚠️ `LTV/LTM/DTV/DTM` 은 **프레임 종류와 무관하게 항상** 쓴다 — 검출기 좌표지 하늘 좌표가 아니다.
  파이프라인 쪽은 `pipeline.py` 가 `WCSSKY` 를 읽어 분기하고, 카드가 없는 옛 L0 는 `True` 로 본다.
- **L0 의 seed 플래그는 L1 primary 로 넘어가지 않는다** — `io_l1.CARRY_EXCLUDE` 에
  `WCSNAME`·`WCSAPPRX`·`WCSSOLVE`·`WCSOMIT`·`BOREPIXX`·`BOREPIXY` 를 넣었다. 안 그러면 Gaia 로
  푼 SCI 위에 primary 가 "안 풀렸음" 을 선언한다.
- **포인팅이 파싱되지 않으면 WCS 카드를 하나도 쓰지 않는다** (`WCSOMIT=T`).
  `CTYPE` 만 있고 `CRVAL` 이 없으면 리더가 `CRVAL=0` 을 기본값으로 삼아 위의 버그가 그대로
  되살아난다. 기본값으로 메우지 않고 **빼는** 쪽이 정직하다.
- **seed 로서 실제로 동작함을 확인했다.** `ccd_wcs_cards()` 가 L0 WCS 를 CCD 좌표로 옮겨
  `solve_field()` 에 넘기는 경로에서, TCS 포인팅 오차 28″ + 회전 0.25° + 스케일 0.4% 를 준
  합성 별밭을 **163개 매칭 · rms 0.157″ 로 수렴**시킨다. 같은 시험에서 패치 전 L0
  (`CRVAL=0`·`CRPIX=0`) 는 `NO_SEED_ZONE` 으로 **시작조차 못 한다.**
- **IRAF physical/detector 변환** `LTV/LTM`·`DTV/DTM`·`ATV/ATM` 을 실어 ds9 의 physical =
  CCD 열/행, detector = 모자이크 픽셀이 된다. 불변식
  `CRPIX - LTV + DTV == boresight` 가 64 amp 전부에서 성립하고, `.hdu_verify.txt` 가
  **파일에서 읽어** 확인한다.

### 검증 · 교차확인 (v2.5.0)

- **`<output>.hdu_verify.txt`** — HDU 수·amp 수·`CHECKSUM/DATASUM`·WCS 상태·`CHMAPOK`·
  raw 교차확인 결과를 적는다. 값은 전부 **산출물에서 읽는다**.
- **C-5/C-13** `check_raw_geometry()` — raw 가 스스로 선언한 geometry(`AMPNAX*`·`IMAGEX/Y`·
  `OVRSCNX/Y`·`PIXSCALE`·binning …)를 converter 상수와 맞댄다. 종전에는 raw 선언이 바뀌어도
  **오류 없이** 엉뚱한 자리에서 잘라냈다.
- **raw pair 일관성** — raw spec 5.9 가 "반드시 동일" 로 규정한 카드를 MK/NT 사이에서 대조한다.
  converter 가 포인팅·HK 를 MK 에서만 읽으므로 그 전제를 확인하는 것이다.
- 어긋남은 `ConverterWarning` (매 노출마다 발화) · primary `HISTORY` · 두 sidecar 에 모두 남는다.
  `-W error` 로 돌리면 실패로 올라간다.

### FITS 표준 적합성 (v2.5.0)

문자열 값을 free format 으로 써서 `XTENSION= 'IMAGE'` 가 고정형식 규칙을 어겼다.
`astropy.verify()` 는 통과시켰고 릴리스 게이트는 그것만 봤지만 **fitsverify 는 129개 오류**로
거부했다. 이제 값 필드를 20자로 채워 `fitsverify` **0 error / 0 warning** 이다.
`card()` 가 69자 이상 문자열에서 닫는 따옴표를 빠뜨리던 것, `EQUINOX` 가 문자열이던 것도 고쳤고,
모든 HDU 에 `CHECKSUM`/`DATASUM` 을 쓴다.

### amp 정체 · 컨트롤러 텔레메트리 (C-11 · C-17 · C-18, v2.5.0)

- **C-17**: `convert()` 가 `nt_hdr` 를 읽고 쓰지 않아 **N·T amp 가 MK 헤더로 스탬핑**됐다.
  이제 각 chip 은 자기 파일의 헤더를 쓴다 — `CHMAP_*` 는 raw spec 5.9 가 pair 사이에서
  **달라야 한다**고 규정한 여섯 카드 중 하나다.
- **C-11**: `MODULE`/`CHANNEL` 이 amp 번호에서 지어낸 값이었다. 이제 raw `CHMAP_LT/LB/RT/RB`
  토큰(`<chip><A|D><nn>`)에서 끌어내고, 내장한 `Detector_Ch_to_AmpID_Map v1.1` 과 대조한다.
  `CTRUNIT`·`CCDPORT`·`CHANNAME`·`CHANNUM`·`IMGSEC` 를 공개하고 `XTALKGROUP` 을 실제 포트
  기준으로 재정의한다. 어긋나면 `CHMAPOK=F` + `HISTORY`.
- **C-18**: `Cn_VOLT`/`Cn_CURR` 는 전원 레일 7자리(P2V5·P5V·P6V·N6V·P17V·N17V·P35V),
  `Cn_TEMP` 는 모듈 온도 10자리(1번=Backplane) 다(raw spec 5.6.1). 레일은 `VOLTINFO` 행으로,
  Backplane 은 `TELEMETRY.BOARDTEMP` 로 들어간다. **`VOLTINFO` 행 수가 9 → 37 로 늘었다.**
  CCD bias/clock 9행은 신규 raw 에 공급원이 없어 `-999.0`/`PLACEHOLDER` 다 — 종전의
  `0.0`/`UNKNOWN` 은 0.0 V 가 `VSS` 의 정상값이라 결측을 실측처럼 보이게 했다.
  `NC`(컨트롤러가 `VALID=0` 응답) 와 `UNKNOWN`(카드 자체가 없음) 을 구분해 싣는다.

### amp별 실측 GAIN/RDNOISE 주입 (`--ampchar`, v2.3.0)

raw spec의 계층 규칙(2026-08-22 운영자 확정: gain/noise는 **raw 미기재 · L0 재량 · L1 필수**)에 따라,
amp별 실측 `GAIN`/`RDNOISE`/`SATURAT`/`LINMAX`는 취득 SW가 아니라 **이 변환 단계**에서 들어간다.
cam_char 캠페인 결과 CSV(`../cam_char/results/amp_characterization_*.csv` 스키마, `EXTNAME` 키)를 주면
amp extension header와 `AMPINFO` 테이블 양쪽에 스탬핑하고(≤0/누락 값은 placeholder 유지),
primary `AMPCHAR` 카드에 테이블 이름을 기록한다. legacy 목업 변환기의 `--ampchar`와 동일 메커니즘.

```bash
python3 mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  raw/KMTA.20260116.000001.MK.fits -f \
  --ampchar cam_char/results/amp_characterization_ARCHON-SSO-20260904.csv
```

MK 또는 NT 중 하나만 지정하면 짝 파일을 자동으로 찾는다. 옵션(`-o`, `-d`, `-f`, `--gzip`)은 상세 README 참조. 대용량 raw/generated FITS는 `.gitignore`로 제외되며 로컬 `raw/` 디렉토리에서 다룬다.

## Mockup 생성 (구형 32-amp MEF → 신형 64-amp L0 MEF)

신규 전자부 실제 관측 자료가 없는 동안, 전처리/자료처리 파이프라인 개발·검증에 쓸 신형 64-amp MEF 목업을 **구형 카메라 32-amp MEF**에서 만든다. 각 CCD를 8개 amp가 strip 전체(9232행)로 읽던 구형 자료를, strip을 CCD 좌표(`CCDSEC`) 기준으로 TOP/BOT 절반(4616행)씩 나눠 신형 16-amp/CCD 구조로 재배치한다. K·N 칩은 구형 라벨 번호가 strip 위치와 반대이므로 **이름이 아닌 기하로 매칭**한다.

- 픽셀은 구형 실측 값을 그대로 보존(활성 1152열 + 실측 오버스캔). 신형 오버스캔 48열은 구형 32열 오버스캔에서 결정론적으로 구성한다.
- **균일 패킹**: 64개 amp 모두 `DATASEC=[1:1152,1:4616]`, `BIASSEC=[1153:1200,1:4616]` (data-left). 같은 별이 모든 amp 영상에서 동일한 in-amp (x,y)에 놓인다. ICD는 amp 5–8/13–16의 오버스캔을 왼쪽에 두므로 이 목업은 의도적 편차이며 `AMPPACK='DATA_LEFT'`, `GEOMVER='CEU-L0AMP-v2.1-mockU1'`로 기록한다.
- **WCS/좌표 이식**: 구형 strip별 WCS를 CRPIX 이동(x−27 프리스캔, TOP은 y−4616)으로 합성해 ds9 sky 좌표가 구형 표시와 일치(v2.0은 최단왕복 부동소수점 기록으로 오차 ≈0, 기계 정밀도). `LTV1/LTV2/LTM`(IRAF physical) 기록으로 ds9 physical 좌표가 구형 파일과 동일: x=strip 열 1–1152, y=CCD 행 1–9232 (TOP amp는 `LTV2=-4616`). `DTV/DTM`은 ds9/IRAF 규약(detector = DTM×physical + DTV)에 맞춰 `DETSEC`과 자기일관: `DTV2=CHIP_Y0-1` (양 끝 공통).
- 채울 수 있는 관측/사이트/노출 키워드는 구형 primary header에서 채운다. 이 변환에서 채울 수 없는 값은 **문자열 키워드는 `na`**, **정수형 키워드/컬럼은 `-1`**(예: `NUMFILES`, `RAWNAX1/2`, `MIDOVSCY`, AMPINFO `RAWX0..RAWY1`)로 표시해 downstream의 `int()` 파싱을 보존한다. 구형의 valueless 카드(TSHSHUT, DSUP 등)는 감지해 `na` 처리. `MOCKDATA=T`(primary+각 amp), `ORIGFILE`/`ORIGEXT`/`CONVPROG` 등 목업 provenance를 기록한다.
- 출력 구조는 실제 64-amp L0 제품과 HDU·키워드가 동일(HDU 69개, amp `1200×4616`, `AMPINFO/XTALKINFO/VOLTINFO/TELEMETRY`). `JD`/`MJD-OBS`는 완전 정밀도로 기록되어 상호 일치.

```bash
# 단일 파일
python3 mef_converter/kmt_ceu_legacy32_to_l0amp_mef_v2.py raw/kmtc.20260630.011092.fits -d raw -f

# 여러 장 일괄 (구형 원본만 정확히 지정 — 목업 산출물 재입력 방지)
ls -1 raw | grep -E '^kmtc\.[0-9]{8}\.[0-9]{6}\.fits$' | sed 's|^|raw/|' \
  | xargs python3 mef_converter/kmt_ceu_legacy32_to_l0amp_mef_v2.py -d raw -f
```

출력 파일명: `<prefix>.<YYYYMMDD>.<NNNNNN>.ceu.l0amp.mock64.mef.fits`.

## archive

| 파일 | 비고 |
| --- | --- |
| `archive/kmt_ceu_archon_mknt_to_l0_amp_mef_v2.py` | 현행 `v2_1`로 대체된 구버전 |
| `archive/kmt_ceu_legacy32_to_l0amp_mef_v1.py` | 목업 변환기 구버전 (v2.0으로 대체: DTV2/JD 정밀도/valueless 카드/정수 na 수정) |
| `archive/kmtn2mef_dev_v0.4_debug7_yoverscanfix_midoverscan.py` | 개발/디버그 스크립트 |

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| 데이터 규격 (keyword/ICD) | `../mef_fits_spec/README.md` |
| L0→L1 전처리 파이프라인 | `../mef_pipeline/README.md` |
| 기술 결정 기록 | `../project_management/governance/DECISION_LOG.md` |
| Release 점검 | `../project_management/release/RELEASE_CHECKLIST.md` |
| Calibration 추적 | `../project_management/science/CALIBRATION_TRACKER.md` |
| 프로젝트 관리 보드 | `../project_management/README.md` |

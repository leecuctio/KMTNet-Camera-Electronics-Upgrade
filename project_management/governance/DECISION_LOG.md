# KMTNet-CEU Decision Log

최종 갱신일: 2026-09-23

> ⚠️ **`ics_archon` 은 `main` 에 아직 없다.**  실기 ICS 는
> **`ics-archon-v1.0-build` 브랜치에서 진행 중**이고 **추후 `main` 합류
> 예정**이다 (합류 시점은 v0 완성 또는 v1 즈음 — 운영자 판단).
> 이 문서가 `ics_archon/…` 경로나 그 구현을 인용하는 곳은 **전부 그 브랜치**를
> 가리킨다.  `main` 의 `ics_sim` 도 아직 구판이라(예: `siteid.py` 잔존)
> **여기 적힌 "구현 완료" 는 그 브랜치 기준**이다.

## D-001: Primary raw archive product는 L0 64-amplifier MEF로 한다

날짜: 2026-06-22

상태: Accepted

결정:

- CCD-level raw image가 아니라 64개 amplifier image extension을 가진 L0 MEF를 primary raw archive로 둔다.
- 각 amp extension은 active pixels와 local overscan pixels를 함께 보존한다.

근거:

- overscan, bias, gain, read-noise, crosstalk, bias jump, amplifier boundary source 처리를 CCD 조립 전에 수행할 수 있다.
- L1 CCD-level calibrated image는 L0 amp-level calibration 이후 파생하는 것이 안전하다.

영향:

- L0 output HDU count는 `69 = PRIMARY + 64 IMAGE + 4 BINTABLE`이다.
- L1 product에서 `SCI_M`, `SCI_K`, `SCI_N`, `SCI_T`를 생성한다.

## D-002: 공식 chip order는 M, K, N, T로 한다

날짜: 2026-06-22

상태: Accepted

결정:

- Science chip order는 `M,K,N,T`이다.
- MK raw file은 M,K chip을 담고 NT raw file은 N,T chip을 담는다.

근거:

- 검증된 Archon controller grouping과 converter 흐름이 이 구조를 따른다.

영향:

- Output extension 순서는 `M01T..M08T`, `M01B..M08B`, 그 다음 K, N, T 순서이다.
- `AMP_BASE`는 M=0, K=16, N=32, T=48이다.

## D-003: CEU Archon L0 packing에서는 OSU식 chip-dependent flip을 적용하지 않는다

날짜: 2026-06-22

상태: Accepted

결정:

- `CHIPFLP = "None"`
- `STRIPDIR = "+X"`
- L0 stage에서는 chip별 flip 없이 raw pixel source를 amp extension으로 분리한다.

근거:

- L0은 raw archive와 amp-level calibration input이므로, legacy electronics orientation 보정은 이후 단계에서 명시적으로 다루는 편이 안전하다.

영향:

- Orientation 관련 변경은 geometry 변경으로 취급한다.
- `READDIR`은 아직 placeholder이며 flat/star sequence test로 확인해야 한다.

## D-004: Software/product version과 geometry version을 분리한다

날짜: 2026-06-22

상태: Accepted

결정:

- Software/product version은 `v2.1.1` 형식으로 관리한다.
- Geometry version은 `CEU-L0AMP-v2.1`처럼 별도 keyword로 관리한다.

근거:

- FITS card formatting, parser 수정, atomic write 같은 patch 변경은 geometry 변경이 아니다.
- Amp ordering, sections, orientation, HDU layout 변경은 더 큰 영향이 있으므로 별도 추적이 필요하다.

영향:

- Patch release에서는 `PRODVER`, `PIPEVER`, `CREATOR`를 갱신하되, geometry가 변하지 않으면 `GEOMVER`는 유지한다.
- Geometry 변경 시 ICD와 keyword 문서를 함께 갱신한다.

## D-005: Placeholder calibration 값은 운영 calibration으로 간주하지 않는다

날짜: 2026-06-22

상태: Accepted

결정:

- 현재 `GAIN`, `RDNOISE`, `SATURAT`, `LINMAX`, `XTALKINFO`, `VOLTINFO`, `TELEMETRY`는 commissioning 전 placeholder로 관리한다.
- `XTALKCAL=True`는 real crosstalk coefficient가 들어간 경우에만 사용한다.

근거:

- Placeholder가 과학 처리 단계에서 실측 calibration으로 오해되면 downstream 결과가 오염될 수 있다.

영향:

- Calibration 관련 작업은 P0 backlog로 유지한다.
- Release note와 README에 placeholder 상태를 명시한다.

## D-006: L1 픽셀 단위는 electrons로 한다

날짜: 2026-07-02

상태: Accepted

결정:

- L1 `SCI` 픽셀은 amp별 `GAIN`을 적용한 electrons 단위(`BUNIT='electron'`)로 기록한다.
- `GAIN`이 placeholder(<=0)면 1.0 e-/ADU를 적용하고 primary header에 `GAINAPPL=F`로 기록한다.

근거:

- amp 간 gain 차이를 조립 전에 제거해 amp seam을 최소화한다.
- downstream 분석에서 amp별 gain을 다시 다룰 필요가 없다.

영향:

- variance plane은 electrons²로 초기화(RN² + Poisson)하고 flat에서 전파한다.
- 실측 gain 반영(KMT-001)은 파이프라인 코드 수정 없이 L0 헤더 갱신만으로 적용된다.

## D-007: L1 제품은 단일 MEF(SCI ×CCD + CALHIST; VAR/MASK는 옵션)로 한다

날짜: 2026-07-02 (같은 날 개정 2회: VAR 기본 제외, MASK 별도 파일 분리)

상태: Accepted (Amended ×2)

결정:

- L1 제품은 노출당 1개 MEF로 하며, 기본 구조는 `PRIMARY` + `CHIPLIST` 순서의
  `SCI_x`(x=M,K,N,T) 4 image HDU + `CALHIST` binary table이다.
- 파일명은 `<prefix>.<YYYYMMDD>.<NNNNNN>.ceu.l1ccd.mef.fits`로 한다.
- 주요 보정 방법·수식은 primary header COMMENT("processing methods")로 제품 안에 기록한다.

개정 (2026-07-02, VAR 기본 제외):

- VAR plane은 L1에 이미 있는 정보로 완전 재구성 가능하므로
  (`VAR = (RDNOISE² + SCI×flat) / flat²`; flat은 `CALFLAT` 참조, RDNOISE는 L0
  amp header/AMPINFO) 기본 제외한다. `VARINCL=F`와 재구성식을 primary header에 기록한다.
- 필요 시 `run --with-var`로 생성한다 (`VARINCL=T`).
- L1 `PRODVER`: v1.0 → v1.1.

개정 2 (2026-07-02, MASK 별도 파일 분리):

- MASK plane은 본 MEF에서 제외하고, `run --mask-file` 옵션 시 별도
  `*.l1ccd.mask.mef.fits`(PRIMARY + MASK×4, uint8)로 생성한다. 기본은 미생성.
- 본 MEF의 `MASKFILE` 키워드가 연결을 기록한다 ('' = 미생성).
- 주의: MASK의 SATURATED/NONLINEAR 비트는 raw ADU 기준 판정이라 L1에서 재구성
  불가하다. 마스크가 필요한 후속 처리를 계획하면 `--mask-file`을 켜야 한다.
- L1 `PRODVER`: v1.1 → v1.2 (기본 노출당 약 1.36 GB).

근거:

- 노출 단위 관리·전송·provenance 추적이 단순하다.
- calibration history(단계·교정자료 버전·파라미터)를 제품 내부에 보존해야 한다 (규격 §12).
- VAR 제거로 노출당 약 3.1 GB → 1.7 GB (44% 절감), 정보 손실 없음.

영향:

- 기본 L1 파일 크기는 노출당 약 1.36 GB(float32 SCI ×4)이며 보관 정책은 KMT-009와 함께 다룬다.
- MASK bits: 1=BAD, 2=SATURATED, 4=NONLINEAR, 8=XTALK, 16=AMP_SEAM, 32=NO_OVERSCAN_FIT.
- 추가 절감이 필요하면 fpack 타일 압축(SCI 양자화)을 후속 검토한다.

## D-008: 전처리 파이프라인의 종점은 CCD 조립 + astrometry로 한다

날짜: 2026-07-02 (같은 날 개정: astrometry를 전처리에 포함)

상태: Accepted (Amended)

결정:

- L0→L1 전처리는 amp 교정 후 CCD 조립, 그리고 조립된 CCD에 대한 astrometric
  solution까지 수행한다: L0에서 물려받은 근사 WCS를 초기값으로 별을 검출해
  기준성표(`--refcat`, FITS RA/DEC 테이블)와 매칭하고 TAN 6-parameter fit
  ((ξ,η)=CD·(pix−CRPIX), CRVAL 고정)으로 WCS 키워드를 갱신한다.
- 성공 시 `WCSSOLVE=T`/`WCSAPPRX=F` + `WCSRMS`/`WCSNMAT`; 실패(성표 없음, 별/매칭
  부족, RMS 초과) 시 근사 WCS를 유지하고 `WCSSOLVE=F` + 사유(`WCSFAIL`)를 기록한다.
- 기준성표는 `make-refcat`(첫 노출 부트스트랩) 또는 외부 성표(Gaia 추출)로 공급한다.
- photometric zeropoint는 후단 파이프라인 몫이다.
- dark 보정은 구조만 두고 기본 off로 한다 (Rehearsal dark 특성 확인 후 결정).

근거:

- CCD 전체 영상이 조립되는 시점이 astrometry의 자연스러운 위치이며, 순수
  numpy+astropy 구현으로 외부 solver 의존성이 없다.
- 실패를 명시적으로 플래그하면 후단이 unsolved WCS를 오용하지 않는다.

영향:

- L1 소비자는 `WCSSOLVE`로 solved/approximate WCS를 구분해야 한다.
- 절대 astrometry 품질은 기준성표 품질에 종속된다 (부트스트랩 성표는 상대 정렬).
- CR rejection은 전처리에 포함하지 않는다 (후단, 필요 시 옵션).


## D-009: Archon raw pair 파일명은 ICD v4.0 형식을 유지한다

날짜: 2026-08-07

상태: **Superseded by D-011 (2026-08-10)** — prefix가 사이트 코드로 개정되었다.
필드 폭·6자리 zero-padding 규칙은 D-011에 그대로 승계된다.

결정:

- Archon 컨트롤러 구성이 저장하는 science raw 파일명은
  `KMTN.<YYYYMMDD>.<NNNNNN>.MK.fits` / `KMTN.<YYYYMMDD>.<NNNNNN>.NT.fits`이다.
- `<NNNNNN>`은 6자리 고정폭이며 0으로 좌측 패딩한다.

근거:

- ICD v4.0에서 검증된 형식이고 converter의 `find_pair()`,
  `default_output_name()`이 이미 이 형식을 인식한다.
- 레거시 파일명의 CCD 문자 슬롯을 되살리는 대안은 OBSAgent `FitsNum` 파서를
  만족시키려는 목적이었으나, D-010이 그 문제를 메시지 계층에서 해결하므로
  파일명을 타협할 이유가 없어졌다.

영향:

- Converter 변경 없음.
- 6자리 zero-padding은 필수 조건이다. 어기면:
  (1) pair 양쪽 파일명이 어긋난 경우(예: 한쪽만 5자리) `find_pair()`의
  문자열 치환(`.MK.fits` ↔ `.NT.fits`)이 존재하지 않는 짝 이름을 만들어
  `FileNotFoundError`가 난다 — 양쪽이 똑같이 자릿수를 어기면 짝 자체는
  찾아진다;
  (2) `default_output_name()`의 정규식 `^KMTN\.(\d{8})\.(\d{6})\.MK\.fits$`
  불일치로 출력 MEF 이름이 fallback 경로로 빠진다 (양쪽이 같이 어겨도 발생);
  (3) raw 파일명 자체는 OBSAgent에 가지 않지만(D-010), 같은 일련번호에서
  만들어지는 `Wrote` 논리 이름의 `<NNNNNN>`이 함께 자릿수를 어기면 OBSAgent의
  `FitsNum` 15자 슬라이스가 밀린다.
- 상세 규격은 `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 2.3절.

## D-010: raw 저장 단위와 OBSAgent 통보 단위를 분리한다

날짜: 2026-08-07

상태: Accepted

결정:

- raw FITS는 **컨트롤러 단위**로 저장한다 (노출 1회당 2개: MK, NT).
- ICS가 OBSAgent로 내보내는 저장 완료 통보는 **CCD 단위로 4회** 유지한다.
  파일 1개를 다 쓴 시점에 그 파일이 담은 chip 2개분 메시지를 함께 낸다.
- 메시지의 `LASTFILE`에는 레거시 형태의 논리 이름
  `KMTN<chip 소문자>.<YYYYMMDD>.<NNNNNN>.fits`를 싣는다.

```text
KMTC.20260807.012345.MK.fits 저장 시   (물리 파일명 표기는 D-011 반영)
  STATUS: Wrote LASTFILE=/data/KMTNm.20260807.012345.fits
  STATUS: Wrote LASTFILE=/data/KMTNk.20260807.012345.fits
```

근거:

- OBSAgent는 `Wrote` 4회로 `FitsSaved=1`을 세우고 `"KMTN"` 위치 +6부터 15자를
  잘라 `FitsNum`으로 쓴다 (`commands.c` 776-784). 파일 2개를 그대로 통보하면
  `Wrote`가 2회뿐이라 매 노출 25초 타임아웃 경로로 빠진다.
- `ICS>OBS`의 메시지 타입은 원래 `STATUS: Wrote`이다 (DevNote 6.1 실측 로그).
  SSO의 `STATUS:` 결함은 `CB>ICS` 구간이라 무관하다.
- OBSAgent를 고치지 않고 ICS 발신 계층만으로 규약을 만족시킬 수 있다.

영향:

- OBSAgent 변경 없음. `count_wrote=4`, `FitsNum='20260807.012345'` 성립.
- **`LASTFILE`이 실재하는 경로가 아니게 된다.** 논리 이름에 해당하는 파일은
  디스크에 없다. 아카이브·DTS·QL 도구는 `LASTFILE` 대신 raw 헤더의
  `FILENAME` / `EXPID` / `CTRLTAG`를 근거로 삼아야 한다.
  *(이 문구는 이후 세 번 개정됐다 — `EXPID`는 구판 규격 v1.2 2.3.1절에서
  삭제됐다가(2026-08-12) **D-019 에서 되살아났고**, 근거는 `FILENAME`(+`ORIGNAME`, D-016) 을 거쳐 최종
  **`FILENAME`(+`EXPID`)** 다. `CTRLTAG`는 미도입.)*
- `ics_sim`의 `sequencer.py` `_store()`와 `state.py`가 저장 경로와 논리 이름을
  분리하도록 바뀌어야 한다 (규격 C-16).
- 상세 규격은 `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 2.5절.

## D-011: raw pair 파일명 prefix를 사이트 코드로 한다 (D-009 개정)

> ⚠️ **D-017 (2026-08-25) 로 개정** — `<SITE>` 넷째 코드가 **`KMTK`(KASI)** 다. 그 밖의 규칙(필드 폭·6자리 zero-padding·`Wrote` 논리 이름)은 유효하다.

날짜: 2026-08-10

상태: Accepted (D-009를 대체한다)

결정:

- Archon 컨트롤러 구성이 저장하는 science raw 파일명은
  `<SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits` / `<SITE>.<YYYYMMDD>.<NNNNNN>.NT.fits`이다.
- `<SITE>`는 4자 대문자 사이트 코드이며 TC 텔레메트리 `TELID` 규약과 동일하다:

  | 코드 | 사이트 |
  | --- | --- |
  | `KMTC` | CTIO |
  | `KMTS` | SAAO |
  | `KMTA` | SSO |
  | `KMTT` | 테스트베드 — 실험실·데모·Full Rehearsal 데이터 |

  > ⚠️ **D-017 (2026-08-25)로 개정됨** — 넷째 코드가 `KMTT`(TESTBED) 에서 **`KMTK`(KASI)** 로 바뀌었다. 이 표는 당시 기록으로 남긴다.

- 필드 폭·구분자·`<NNNNNN>` 6자리 zero-padding 규칙은 D-009와 동일하게
  유지한다 (자릿수 위반의 결과도 D-009 영향 절과 동일).
- `Wrote` 논리 이름(D-010)은 변경하지 않는다 — 계속 `KMTN<chip 소문자>.…`.

근거:

- raw 파일명에 사이트 정보가 없으면 3사이트 데이터를 한 저장소·분석 풀에
  모을 때 동명 충돌이 난다 — cam_char LEGACY 캠페인(3사이트 데이터 통합
  분석)에서 이미 실제 워크플로로 확인된 시나리오다.
- 사이트 코드는 기존 `TELID` 값(KMTC/KMTS/KMTA)과 L0 MEF 소문자
  prefix(kmtc/kmts/kmta) 규약을 그대로 따른다 — 새 규약이 아니라 기존
  식별자를 파일명으로 확장하는 것이다.
- D-010이 물리 파일명과 OBSAgent 메시지 계층을 분리해 두어, 물리 파일명의
  소비자는 converter·실험실 스크립트·아카이브 도구뿐이다. 또한 `KMTC` 등은
  `KMTN` 부분 문자열을 포함하지 않으므로, 물리 경로가 메시지에 섞여도
  OBSAgent `FitsNum` 파서가 오반응할 수 없다.
- 실기 raw가 아직 생산되지 않았고 `ics_archon`의 `write_fits()`가 스텁인
  지금이 변경 비용이 최소인 유일한 시점이다. SSO 설치(2026-10) 이후에는
  아카이브 이력이 쌓여 사실상 변경 불가가 된다.

영향:

- Converter (`kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`, v2.2.0):
  `default_output_name()` 정규식을 사이트 코드 형식으로 개정하고, 출력 MEF
  prefix를 파일명 사이트 코드에서 유도하되 `OBSERVAT` 헤더와 교차 검증한다
  (불일치 = 오류). `find_pair()`는 prefix 무관(`.MK.fits`↔`.NT.fits` 치환)이라
  변경 없음.
- ICS: 사이트 코드는 설정(`[node] site`/`telid`)에서 얻는다. 설정 오배포
  방어로 ① config 로드 시 `site`↔`telid` 정합 검증, ② 운영 시 실측 TC
  텔레메트리의 `TELID`와 불일치하면 경고를 둔다. 물리 파일명 생성기는
  ics_archon 단계 C-16 구현에 반영한다.
- ICD v4.0 → v4.1 개정 (NT 헤더 완전성 OI-8과 함께 반영).
- OBSAgent, `Wrote` 논리 이름, 레거시 아카이브 문서, 과거 검증 기록
  (CR-001, Work Summary v1.0 등)은 변경하지 않는다.
- 실험실 특성 측정 스크립트(`cam_char/archon/`)의 캠페인 파일명 체계는
  별개 도메인으로 유지하되, 사이트 raw 규격과의 경계를 문서에 명시한다.
- 상세 규격은 `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 2.3절.

---

## D-012: 하드웨어 백엔드 계약을 컨트롤러 단위로 개정한다

날짜: 2026-08-11
관련: D-010 (통보 분리) · D-011 (사이트 코드) · `raw_fits_spec` 변경점 C-8/C-16
상태: **Accepted** — `ics_sim`에 구현 완료, 실기(`archon.py`)는 이 계약으로 채운다.

결정:

- `ics_sim/ics_sim/hardware/base.py`의 저장 메서드를 CCD 단위
  `write_fits(ccd, path, header)`에서 **컨트롤러 단위**
  `write_frame(controller, chips, path, header)`로 개정한다.
- 저장 단위(컨트롤러 1파일)와 통보 단위(CCD 4회 `Wrote`)의 분리는 **시퀀서가**
  담당하고 백엔드는 관여하지 않는다. 파일명 fail-safe도 시퀀서가 처리해
  백엔드에는 이미 확정된 경로가 내려온다.
- 물리/논리 파일명 생성과 규격 5.1·5.2절 정체성 카드는 신설
  `ics_sim/ics_sim/rawpair.py`로 모은다.
- **시뮬 백엔드도 같은 계약을 구현한다.** 픽셀은 더미이고 크기도 실물
  (19200×9400)이 아니지만 파일 구성·이름·헤더는 규격 그대로다.

근거:

- 종전 시그니처로는 실기의 저장 단위를 **표현할 수 없었다.** 노출 1회가 만드는
  물리 파일은 컨트롤러당 1개(MK/NT 2개)이고 각각 chip 2개분 픽셀을 담는다
  (`raw_fits_spec` 2.1·2.3절, ICD v4.1 2.1·3절). DevNote 9.1이 이 개정 필요성을
  이미 적어 두었으나 결정 기록이 없었다.
- **시뮬에 먼저 구현하면 하드웨어 없이 D-010/D-011을 검증할 수 있다.** 실물
  OBSAgent로 `Wrote` 4회·논리 이름·`FitsNum` 파싱을 확인하는 것이 가능해지므로,
  규약 리스크를 Archon 도착 전에 소진한다. `ExpNum` 값 결함이 실물 연동에서야
  드러난 경위(DevNote 12.14)가 이 순서를 택한 직접적인 이유다.
- 가이드 계통도 Archon이다 — 신규 계통도(`KMTNet Cam Architecture R2.0`)에서
  Unit 3이 가이드 CCD 4대를 읽는다. 계약을 컨트롤러 단위로 잡아 두면 `icg`가
  같은 계약을 재사용한다. CCD 단위로 좁게 두면 두 번 만들어야 했다.

영향:

- `hardware/base.py` · `sim.py` · `archon.py`(스텁) · `sequencer._store()` ·
  신설 `rawpair.py` · `telemetry.py`(sentinel 분리, C-9). 테스트 16개 추가.
- **OBSAgent는 변경 없다.** 통보가 논리 이름 그대로이므로 `count_wrote`·
  `FitsNum`·타임아웃 창이 모두 종전과 같다 (기존 규약 테스트 177개 전부 통과).
- `LASTFILE`이 실재 경로가 아니게 되는 D-010의 부작용이 시뮬에서도 실제로
  발생한다 — 아카이브·DTS 도구는 raw 헤더의 `UNIQNAME`/`FILENAME`/`CTRLTAG`를
  근거로 삼아야 한다 (`EXPID`는 구판 규격 v1.2 2.3.1절에서 삭제했다 — 2026-08-12).
  *(D-016 개정: 근거 삼총사는 `FILENAME`(+`ORIGNAME`) 로 대체 — `UNIQNAME`
  폐지, `CTRLTAG` 미도입. **D-019 재개정: `ORIGNAME` → `EXPID`.**)*
- 실기 전환 시 `archon.py`의 `write_frame()`만 채우면 되고, 시퀀서·명령
  처리부·메시지 규약은 무개정이다 (DevNote 1.2의 2단계 약속 유지).
- 상세 규격은 `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 2.3·2.5절,
  구현 경위는 `ics_sim/DevNote.md` 11.13.

---

## D-013: 레거시 raw keyword 를 하나씩 판정하고, 컨트롤러 정체는 색인형으로 싣는다

> ⚠️ **판정 방법(레거시 카드를 하나씩 맞대어 판정과 근거를 남긴다)과 컨트롤러 정체를 두 대분 싣는 원칙은 유효하다. 개칭 `DSTEL` → `DSTELALT` 와 계승 `ICSBUILD` 도 그대로다. 다만 아래 항목은 뒤이은 판정으로 개정됐다** — 카드별 현행 판정의 정본은 원장(`raw_fits_spec` 의 Header_and_Refs) 3·6·7·8·9장과 raw spec 5장이다. 이 결정이 가리킨 규격 5.5.0·5.13절은 구판 v1.2 의 절 번호이고, 5.13절의 판정표는 지금 원장 6장(계승·개칭)·8장(폐지 카드)·9장(레거시 123개 전량 귀속)이 잇는다.
>
> - **`CTRL1FW`/`CTRL2FW` 필수 → 싣지 않는다.** 펌웨어·버전 문자열은 적용 ACF 파일명 **`CTRLnCFG`** 로 귀속됐다(원장 v1.8 3.3절 `X`). 현행 색인형 정체는 `CTRLnID`·`CTRLnSN`·`CTRLnCFG` 이고, 두 대분을 양쪽 파일에 모두 싣는 것은 그대로다(raw spec 5.5절).
> - **`HEMODE`·`NPHLINES` 계승 → 싣지 않는다**(원장 v1.8 6장 `X` — `HEMODE` 는 `DATASRC`·`CTRLnID` 와 중복이다. raw spec 5.10절 폐지·미도입 목록).
> - **`DATASRC` 값 `ARCHON`/`SIM` → `ARCHON_SCIENCE`/`ARCHON_GUIDE`/`SIM`**(원장 v1.8 6장 · raw spec 5.5절).
> - **`LEDFLASH` 는 계승을 유지하되 단위가 [seconds] → [milliseconds] 정수로 바뀌었다.** 구판 v1.2 5.13절의 계승 조건("단위(초)를 유지한다")을 원장 v1.11 이 번복했다(운영자 확정 2026-08-22 — 정수형을 지키면서 1초 미만 값이 잘리지 않게 하려는 것이다). 레거시와 이름이 같고 단위가 1000배 다르므로 카드 comment 가 단위를 밝힌다(원장 6장). ⚠️ 레거시 값과 바로 비교하지 않는다. 또 이 카드는 **science 전용**이다 — guide 는 그 자리에 `TRIGOUT` 을 싣는다(raw spec 5.4절).
> - **`DETID` 폐지 → 철회.** 값을 `MK`/`NT`(어느 컨트롤러의 파일인가)로 재정의해 되살렸다(원장 v1.3 · raw spec 5.2절). 여기 적힌 폐지 근거는 옛 정의(파일 1개 = CCD 1개)에 대한 것이라 원장 8장에 기록으로 남아 있다.
> - **"런타임 상태는 단수형으로 둔다"의 여섯 장은 전부 raw 에 없다.** `CTRLSTAT`·`CTRLERR`·`FRAMENO`·`BUFNO` 는 원장 v1.9 7장 `X` 이고, `BCKTEMP` 는 컨트롤러별 나열 카드 **`C1_*`/`C2_*`**(`TEMP`·`VOLT`·`CURR`, raw spec 5.6·5.6.1절)로 바뀌었고, `READTIME` 은 현행 규격에 카드가 없다. ⚠️ 그 `Cn_*` 는 **두 대분을 양쪽 파일에 같은 값으로** 싣는다(raw spec 5.9절 "반드시 동일") — 런타임 상태도 색인형이 된 것이다.
> - **C-17·C-18 은 converter v2.5.0 이 반영했다** (D-023 · `mef_converter/README.md`) — 영향 셋째 항목의 "LEECU 쪽에서 처리한다" 는 닫혔다.

날짜: 2026-08-13
관련: D-010 · D-011 · D-012 · `raw_fits_spec` 5.5.0 · 5.13절 · 변경점 C-17 · C-18
상태: **Accepted (Amended)** — 판정 항목 일부가 원장 v1.3·v1.8·v1.9·v1.11 판정으로 개정됐다(머리 배너) — 규격 반영 완료, `ics_sim` 구현 진행.

결정:

- **레거시 raw 헤더 실측본 123개 카드를 규격과 하나씩 맞대어 판정한다.** 101개는
  이미 대응물이 있었고, 대응물이 없던 22개를 **계승 5 · 개칭 1 · 폐지 16** 으로
  정리했다 (규격 5.13절에 근거와 함께 표로 남겼다).
  - 계승: `DATASRC`(값을 `ARCHON`/`SIM` 으로 재정의) · `HEMODE` · `LEDFLASH` ·
    `ICSBUILD` · `NPHLINES`
  - 개칭: `DSTEL` → **`DSTELALT`**
  - 폐지: `DETID` · `OVERSCNY` · `READOUT` · `GAINDL` · `PIXITIME` · `DMAWAIT` ·
    `ICROLE` · `CTCSOURC` · `CTCFILE` · `KBUILD`~`GBUILD`(5개) · `RTD12` ·
    `INPUTFMT`
- **컨트롤러 정체는 파일마다 두 대분을 색인형으로 싣는다** — `CTRL1ID`/`CTRL1SN`/
  `CTRL1FW`/`CTRL2ID`/`CTRL2SN`/`CTRL2FW` 를 필수로 하고, 종전의 단수형
  `CTRLNAME`/`CTRLSN`/`CTRLFW` 는 폐지한다. 색인은 `RAWGROUP` 순서(`1`=MK,
  `2`=NT)이고 두 파일에서 값이 같다.
- **런타임 상태는 색인형으로 만들지 않는다** — `CTRLSTAT`/`CTRLERR`/`BCKTEMP`/
  `READTIME`/`FRAMENO`/`BUFNO` 는 단수형으로 둔다.

근거:

- **판정을 남기지 않으면 폐지가 누락으로 오해된다.** 20년치 아카이브와 비교하는
  다음 사람이 `DETID` 나 `KBUILD` 가 없는 것을 보고 되살리려 할 것이다. 폐지도
  결정이므로 근거가 있어야 한다.
- **`CTRL<n>*` 는 converter 가 이미 그 이름으로 읽고 있다.** `primary_cards()` 는
  `mk_hdr` 하나만 받아 `v("CTRL1ID","UNKNOWN")` 으로 색인 이름을 직접 읽는다
  (`v2_1.py:411-416,758`). 종전 규격 5.5절은 단수형을 싣고 converter 가 색인형으로
  옮긴다고 적었으나 **converter 는 그런 변환을 하지 않는다.** 그대로 두면 MEF 의
  컨트롤러 정체가 전부 `UNKNOWN` 이 되고, **오류 없이** 그렇게 된다.
- **레거시가 같은 구조를 이미 썼다.** raw 파일마다 `KBUILD`/`MBUILD`/`TBUILD`/
  `NBUILD`/`GBUILD` 를 다 실어서 한 장만 열어도 카메라 전체 전자부 상태를 알 수
  있게 했다. 색인형은 그 취지의 계승이다.
- **정체와 런타임 상태를 가른 이유**: 노출 1회 안에서 컨트롤러의 정체는 달라질 수
  없으므로 양쪽에 실어도 어긋날 수 없다. 반면 보드 온도·독출 시간·오류 플래그는
  실제로 다르므로, MK 헤더에 두 대분 실으면 NT 자신의 헤더와 어긋날 수 있는 값이
  생긴다 (규격 5.12절 "중복은 불일치의 원천").
- **`OVERSCNY` 폐지는 이름 계승이 안전하지 않을 수 있음을 보여준다.** 레거시의
  Y overscan 은 가장자리를, 신규는 **영상 중앙**을 뜻한다(규격 4.2절). 이름을
  물려주면 "위쪽 N행 자르기" 도구가 **아무 오류 없이** active 픽셀을 지운다.
  계승은 기본값이 아니라 뜻이 같을 때만 하는 선택이다.

영향:

- 규격 5.1·5.4·5.5·5.5.0·5.7·5.11·5.13절, 변경점 C-17·C-18.
- `ics_sim` — `rawpair.py` 에 규격 5.3~5.9 카드 생성부 추가, 백엔드에서 온도·
  컨트롤러 정체를 받아 오는 경로 신설, AUX 실선 `DSTEL` → `DSTELALT` 옮겨 싣기.
- **converter 는 우리가 고치지 않는다** (`mef_converter/` 는 읽기 전용). C-17·C-18
  로 남겨 LEECU 쪽에서 처리한다.
- 상세 경위는 `ics_sim/DevNote.md` 11.14.

---

## D-014: 파일명 날짜부는 사이트별 관측일로 한다

> ⚠️ **개정 셋** — 관측일 규약(UT 에 보정을 더한 뒤 날짜만 취한다) · 관측소 세 곳의 경계 · `DATE-OBS` 밀리초 · raw `UT` 폐지는 유효하다.
>
> - **표 넷째 행**: `TESTBED KMTT` → **`KASI KMTK`**(D-017, 2026-08-25), 그 보정 `0` → **`+9:00`**(경계 UT 15:00 = KST 00:00, 관측일 = KST 날짜 — 운영자 확정 2026-09-12 · raw spec v1.14 2.2절, 경위는 **D-017 머리 배너**).
> - **결정 셋째 항목의 `DATE-OBS` 시점** — `SHOPEN` 지시 시점은 셔터 노출에만 맞는다. `DATE-OBS` 는 **모든 영상(`DARK`·`BIAS` 포함)의 적분 개시 시각**이다 — 셔터 노출은 ICS 가 셔터 개방을 지시한 시각, 셔터 없는 노출은 컨트롤러에 적분을 건 시각, guide 는 트랜스퍼 개시(운영자 확정 2026-09-23 · raw spec v1.14 5.4절 · 10.1-4). 날짜·시각을 모두 담고 밀리초까지 필수라는 조항은 유효하다.
> - **결정 끝 항목**(`<SITE>` 를 네 코드 밖이면 `KMTT` 로 떨어뜨린다) → **D-020(2026-08-24)이 정규화를 폐지했다** — 넷 밖의 값은 **기동을 거부한다**. D-017 은 떨어지는 자리를 `KMTK` 로 옮겼었다. 근거 끝 항목과 영향의 "`app.py` 가 사이트 코드를 정규화해 넘긴다" 도 당시 기록이다 — `rawpair.normalize_site()` 는 남아 있으나 `<SITE>` 를 정하는 경로가 아니다(D-020 영향).

날짜: 2026-08-13
관련: D-009 · D-011 · D-013 · `raw_fits_spec` 2.3·5.7·5.13절 · OI-10 종결 · OI-12 해소
상태: **Accepted (Amended)** — 이충욱(LEECU) 협의 후 운영자 확정, `ics_sim` 구현 완료. 넷째 사이트 행(D-017 · KASI 보정 `+9:00`) · `DATE-OBS` 시점(적분 개시 — 2026-09-23) · 정규화 항목(D-020)이 개정됐다(머리 배너).

결정:

- **파일명 `<YYYYMMDD>` 는 그 사이트의 관측일이다.** UT 시각에 사이트별 보정을
  더한 뒤 날짜만 취한다.

  | 사이트 | 경계 UT | 보정 | 현지 시각 |
  |---|---:|---:|---:|
  | CTIO `KMTC` | 16:30 | `+7:30` | 12:30 |
  | SAAO `KMTS` | 10:30 | `−10:30` | 12:30 |
  | SSO `KMTA` | 01:30 | `−1:30` | 12:30 |
  | TESTBED `KMTT` | — | `0` | (해당 없음) |

  > ⚠️ **D-017 (2026-08-25)로 개정됨** — `TESTBED KMTT` 자리는 **`KASI KMTK`** 다. 보정 `0` 과 세 관측소 경계는 그대로다.
  >
  > ⚠️ **KASI 의 보정은 `+9:00` 으로 개정됐다** (운영자 확정 2026-09-12) — 경계 UT 15:00 = KST 00:00 이라 관측일이 곧 KST 날짜다. 바로 위 줄의 "보정 `0`" 은 그 전까지의 규칙이다. 세 관측소 경계는 그대로다 (경위는 D-017 머리 배너).
  >
  > ⚠️ **'현지 시각' 열의 12:30 은 숫자 검산용이다** — CTIO UTC−4(표준시) · SAAO UTC+2 · SSO UTC+11(일광절약시)로 셈한 값이다. 민간 시각으로는 계절에 따라 CTIO 13:30 또는 SSO 11:30 이 된다. 규범값은 **경계 UT** 열이다.

  근거는 **각 사이트 동지 때 관측 종료와 관측 시작 사이의 중간 시각**이다.
- **`<YYYYMMDD>` 는 `DATE-OBS` 의 날짜와 일반적으로 다르다 — 그것이 의도다.**
  한 관측 야간이 하나의 날짜로 묶이는 것이 목적이고, `DATE-OBS` 는 그와 무관하게
  그 노출의 실제 UT 순간을 담는다.
- **`DATE-OBS` 는 `SHOPEN` 지시 시점의 UT 를 날짜·시각 모두 담고, 초는 소수점
  셋째자리(밀리초)까지 필수다.**

  > ⚠️ **2026-09-23 운영자 확정으로 개정됨** — 시점은 **그 영상의 적분 개시**다(`DARK`·`BIAS` 포함, raw spec v1.14 5.4절). `SHOPEN` 지시 시점은 셔터 노출의 경우다. 밀리초 조항은 그대로다. 경위는 머리 배너.

- **`UT` 카드는 폐지한다** — `DATE-OBS` 와 완전한 중복이다.
- **`<SITE>` 는 `KMTC`/`KMTS`/`KMTA` 밖의 값을 모두 `KMTT` 로 떨어뜨린다.**

  > ⛔ **D-020 (2026-08-24)이 대체했다** — 넷 밖의 값은 떨어뜨리지 않고 **기동을 거부한다**(D-017 은 떨어지는 자리를 `KMTK` 로 옮겼었다). 이 줄과 근거 끝 항목은 당시 기록이다.

근거:

- **종전 잠정안(UT 날짜)에는 조용한 결함이 있었다.** UT 날짜의 경계는 UT 자정이고,
  그게 **CTIO 현지 20시 · SAAO 현지 22시**로 관측 시간대 안이다. 취득 SW 는
  파일명 날짜부를 프레임 개시(`INITIALIZE`)에 정하고 `DATE-OBS` 는 그로부터 약
  7.6초 뒤(`initialize_ack` 0.40 + `erase_sec` 7.24) 셔터 개방 시점에 찍으므로,
  그 창이 UT 자정을 걸치면 **파일명은 어제 · `DATE-OBS` 는 오늘**이 된다. 오류는
  나지 않는다 — 파일명으로 야간을 묶는 도구가 그 프레임을 엉뚱한 날짜에 넣고,
  변경점 C-4 의 pair 일관성 검사도 MK·NT 가 똑같이 어긋나므로 잡지 못한다.
  두 사이트에서 매 야간 한 번씩 프레임 경계가 그 부근을 지난다.
- **관측일 기준은 그 결함을 구조적으로 없앤다.** 경계가 현지 12:30 이라 관측
  중에는 지나가지 않는다. 잔여 위험은 현지 12:30 무렵의 주간 교정 프레임뿐이고
  (bias/dome flat) 오류로 이어지지 않는다.
- **구현은 보정을 더한 뒤 날짜만 취하는 한 줄이어야 한다.** 경계 시각을 `if` 로
  나열하면 `<`/`<=` 를 잘못 잡는 off-by-one 이 생기고, 그건 **1년에 몇 번만
  드러나는** 부류다. 보정 방식은 경계에서 정확히 `00:00` 이 되므로 그 실수가
  성립하지 않는다.
- **검산 불변식**: 세 경계가 모두 현지 12:30 이다. 숫자를 고칠 일이 생기면 이걸로
  확인한다. 시험이 이 불변식을 직접 지킨다.
- **`UT` 폐지가 안전한 근거**: MEF 의 `UT` 는 raw 의 `UT` 가 아니라 `DATE-OBS` 의
  날짜부 + raw 의 `TSHOPEN` 으로 조립된다(`v2_1.py:440,583`). 둘 다 그대로 싣고
  있으므로 MEF 산출물은 변하지 않는다. OBSAgent 도 `DATE-OBS` 를 파싱하지 않는다
  (`OBSAgent.latest/KMTObs/commands.c` 전량에 주석 한 줄뿐).
- **`KMTT` 로 떨어뜨리는 것이 곧 안전은 아니다.** converter 정규식이 네 코드만
  받으므로 낯선 값을 그대로 싣는 것보다는 낫지만, 실제 관측 자료가 `KMTT` 이름으로
  저장되면 사이트 정체를 잃는다. 그래서 정규화가 실제로 일어나면 경고를 남긴다.

영향:

- 규격 2.3·5.7·5.13·8장, OI-10 종결, OI-12 해소.
- `ics_sim` — `rawpair.observing_date()`·`normalize_site()` 신설,
  `IcsState.site_code`·`obs_date()`, `app.py` 가 사이트 코드를 정규화해 넘긴다,
  `stamp_compact()` 는 "파일명에 쓰지 말 것" 으로 격하, `DATE-OBS`·TCS 중계가
  밀리초, `rawhdr` 에서 `UT` 카드 제거. 시험 282개(관측일 19개 추가).
- **OBSAgent 는 변경 없다** — 날짜부는 `Wrote` 논리 이름 안에서 형태(8자리)가
  같고, `FitsNum` 15자 슬라이스도 그대로다.
- 상세 경위는 `ics_sim/DevNote.md` 11.15.

---

## D-015: ~~사이트는 호스트 IP 로 판정하고, 그 판정이 설정을 이긴다~~

> ⛔ **D-020 (2026-08-24) 이 대체한다** — 사이트 판별은 **`[node] observatory` 설정
> 한 줄**이 정본이고, **호스트 IP 판정은 쓰지 않는다.** `ics_sim/ics_sim/siteid.py`
> 와 `site_from_ip` 는 **삭제됐다** — 되살리지 말 것.  결정문과 근거는 **D-020**.
>
> 아래 본문은 **이력으로 남긴다** — 판정을 다시 도입하자는 제안이 나올 때 당시
> 근거와 D-020 의 반대 근거가 **함께** 필요하다.

> ⚠️ D-017 (2026-08-25) 로 사이트 코드가 개정됐다 — 아래 본문의 `KMTT`(벤치)는 전부 **`KMTK`(KASI)** 로 읽는다.

날짜: 2026-08-13
관련: D-011 (사이트 코드 prefix) · D-014 (관측일) · **D-017** · **D-020**(대체) · `operations/ICS_DEPLOYMENT_CHECKLIST.md` · ACT-008 · ACT-009
상태: **Superseded by D-020 (2026-08-24)** — 구현도 함께 삭제됐다. 종전: Accepted, `ics_sim` 구현 완료(시험 308개).

결정:

- **실효 사이트는 호스트 자기 IPv4 주소의 `/24` 대역으로 판정한다.**

  | 대역 | 사이트 |
  |---|---|
  | `192.168.14.0/24` | CTIO `KMTC` |
  | `192.168.13.0/24` | SAAO `KMTS` |
  | `192.168.15.0/24` | SSO `KMTA` |
  | 그 밖 전부 | 벤치 `KMTT` |

  > ⚠️ **D-017 (2026-08-25)로 개정됨** — 떨어지는 코드가 **`KMTK`(KASI)** 다. ⛔ **판정 규칙 자체는 D-020 이 대체했다** (2026-08-24).

- **판정이 `[node] site` 를 이긴다.** ini 값은 버리지 않고 대조해 경고를 남긴다.
  `[node] site_from_ip = false` 로 끌 수 있고, 시험이 그 경로를 쓴다.
- **`KMTC`/`KMTS`/`KMTA` 밖의 사이트 코드는 모두 `KMTT`** 로 정규화한다. *(D-017 로 **`KMTK`** 개정)*
- **기동 시 사이트 정체 배너**를 한 덩어리로 남긴다 — 사이트·판정 근거·
  `TELESCOP`·좌표·관측일 경계·**파일명 예시**·`data_dir`·`EXPNUM`·`DATASRC`.
- **TC 의 `TELID` 는 교차검증에만 쓴다** — **서로 다른 값마다 한 번씩** 경고하고
  (값이 오가도 이미 말한 값은 다시 말하지 않는다), 파일명에는 영향을 주지 않는다.
- **교차검증은 전부 경고다.** 관측을 막지 않는다.

근거:

- **오배포는 설정 안의 어떤 값으로도 잡을 수 없다.** `[node] site` 한 줄이 사이트
  코드 → 좌표 → 관측일 경계 → 파일명을 다 끌고 가므로, 설정 묶음을 통째로 잘못
  복사하면 **모든 값이 서로 일관되게 틀린다.** converter 의 교차검증(파일명
  `<SITE>` ↔ `OBSERVAT`)도 둘 다 우리 설정에서 나와 무력하다. 잡으려면 **설정
  밖에서 오는 신호**가 필요하고, 호스트 주소가 그것이다 — ini 를 복사해도 IP 는
  따라오지 않는다.
- **판정이 이겨야 하는 이유는 벤치 요구사항이다.** 벤치는 사이트 이름을
  `kmtnet-sso`/`kmtnet-ctio`/`kmtnet-kasi`/`kmtnet-helab` 등 무엇으로 두더라도
  **파일명이 `KMTT.…`** 여야 한다(운영자 확정). 설정이 이기면 그게 성립하지 않는다.
- **TC 의 `TELID` 를 정본으로 쓰지 않은 이유**: 그 값은 `pctcs.ini` 의
  `FITS_TELID` 설정이고(`commands.c:1999` → `aux.FitsTelID`,
  `loadconfig.c:512-514`) 기본값이 사이트가 아닌 `KMTN` 이다(`pctcs.h:115`).
  즉 **또 하나의 수동 설정**이라 같은 사람이 같은 실수를 할 수 있고, TC 가 안
  뜨거나 미설정이면 실자료가 `KMTT` 로 떨어질 수 있다. 다만 **독립된 두 번째
  설정**이므로 어긋남 자체는 정보가 된다 → 경고로만 쓴다. 상류 개선은 ACT-008.
- **레거시도 IP 로 사이트를 갈랐고, 그 방식의 결함까지 우리가 이미 기록해 뒀다.**
  `ics_legacy_report.md:763` 이 `192.168.15.109` 를 통째로 박았고 `:784` 가
  "SSO 의 XIS 주소가 바뀌면 갑자기 매 노출 경고" 라고 비판했다. 그래서 **`/24`
  대역만** 보고 호스트 옥텟은 보지 않는다. 신규는 머신 7대가 2대로 통합돼
  (DevNote 9.1) 레거시의 역할-옥텟 지도가 아예 무효이기도 하다.
- **인터페이스 netmask 를 쓰지 않는다.** 13/14/15 가 인접해서 누군가 `/22` 로
  잡아 두면 **세 사이트가 한 망으로 합쳐진다.** literal `/24` 로만 비교한다.
- **주소를 하나만 보지 않는다.** 신규 호스트는 multi-homed 다 — Archon 망이
  `10.0.0.0/24` 로 실재한다(`cam_char/archon/campaign_example.ini:15`). 어느
  주소가 잡히는지가 OS 의 인터페이스 순서에 좌우되면 안 된다.
- **경고만 하고 관측을 막지 않는 이유**: 판정이 틀릴 수 있고(망 개편, NIC 다운),
  좋은 야간을 잘못된 이유로 멈추는 비용이 오라벨 비용보다 클 수 있다. 대신
  **t=0 에 배너로 보여주는 쪽**에 투자했다.
- **오탐을 막는 것이 설계의 절반이다.** 오탐이 잦은 검사는 사람이 무시하는 것을
  학습시켜 **검사가 없는 것보다 나쁘다.** 그래서 (1) `TELID` 는 서로 다른 값마다
  한 번씩만 경고, (2) 값이 없는 것은 불일치가 아님, (3) canned 텔레메트리는 우리
  설정을 복사한 값이라 교차검증 입력으로 인정하지 않음(거짓 일치가 불일치보다
  위험하다), (4) 벤치·오프라인 호스트는 조용함. 시험 절반이 "경고가 안 뜬다" 를
  지킨다.

영향:

- `ics_sim` — 신설 `siteid.py`, `config.SiteCfg`/`site_table`/`site_for()`/
  `[node] site_from_ip`, `app._resolve_site()`·`log_identity_banner()`·
  `_warn_if_real_frames_would_be_labelled_bench()`,
  `telemetry.check_telid()`. 시험 26개 신설(`test_site_id.py`), 총 308개.
- 신설 `operations/ICS_DEPLOYMENT_CHECKLIST.md`.
- **미확인**: 신규 CEU 망의 대역이 문서화되지 않았다(ACT-009). 코드 주석과
  체크리스트에 *inferred* 로 명시해 두었다.
- 상세 경위는 `ics_sim/DevNote.md` 11.16.

---

## D-016: raw 파일명 충돌 시 노출 번호를 증가시켜 저장한다 (`UNIQNAME` 폐지)

> ⚠️ **D-018 (2026-08-25) 로 항목 1·2 개정** — 번호 공간 **`000000`–`999999`**, 되감음 **1000000**, 상한 **1000000회**. 나머지 항목은 유효하다.

날짜: 2026-08-21 (운영자 등재 승인 2026-08-22)
관련: D-010 · D-011 · D-012(일부 대체) · D-013 · D-014 · `raw_fits_spec` 확인 요망 종결분(Header_and_Refs v1.12)
상태: **Accepted** — 규격 문서 반영 완료(`raw_fits_spec/archive/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md` Part 2 — 그 판은 `archive/` 로 갔다), **구현 완료** (충돌 선검사·번호 증가 — `ics-archon-v1.0-build`, `main` 합류 대기).

결정:

1. **파일 번호 공간은 `000000`–`099999`** 이며 카운터는 100000 도달 시 `000000` 으로 초기화한다 (레거시 관례 계승).
   > ⚠️ **D-018 (2026-08-25)로 개정됨** — 공간은 **`000000`–`999999`**, 되감음은 **1000000**, 항목 2 의 상한은 **1000000회** 다. 나머지 규칙(선검사·카운터 동기화·실패 조건 하나)은 그대로다.
2. **쓰기 전에 후보 번호 N 의 MK · NT 두 경로를 모두 선검사**하고, 점유 시 N+1(099999 를 넘으면 000000 으로 되감음)로 재검사한다. **+1 증가가 100000회를 초과하면 멈추고 ERROR 를 출력하며 저장하지 않는다** — 상한 100000회 = 번호 공간 정확히 한 바퀴. 실패 조건은 이것 하나뿐이다.
3. 둘 다 빈 N 을 확정하고 **카운터를 N 으로 동기화**한다 (평소 노출 번호 영속화 경로 그대로, 옛값→새값 점프는 경고 로그).
> ⚠️ **D-019 (2026-08-26) 로 항목 4·5 개정** — `ORIGNAME` 을 폐지하고 **`EXPID`**(`<SITE>.<YYYYMMDD>.<NNNNNN>`, **pair 양쪽 동일**)가 대신한다. 충돌 신호는 `FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값과의 비교다. 나머지 항목은 유효하다.

4. **`UNIQNAME` 을 폐지한다.** `FILENAME` = 실제 저장명이자 **아카이브 유일 키**, `ORIGNAME` = 카운터가 처음 배정한 이름 — 두 카드를 모든 파일에 **항상** 기록한다. **충돌 신호 = `FILENAME ≠ ORIGNAME`** (값 비교 — 카드 존재가 아니다). `ORIGNAME` 결측은 충돌이 아니라 헤더 결함으로 분류한다. 아카이브 근거는 **`FILENAME`(+`ORIGNAME`)** 이고 pair 쪽 식별은 `FILENAME` `DETID` 필드(`.MK`/`.NT`) 치환으로 유도한다 — `CTRLTAG` · `PAIRFILE` 카드는 싣지 않는다(v1.9 미도입 확정). `NAMECLSH` 카드와 `clash/` 격리(구 규격 2.3.1)를 폐지한다.
5. 같은 노출의 재저장(유령 중복)은 **fail-open** 이며, raw 헤더 층(아카이브 색인·DTS·QL)의 `FILENAME ≠ ORIGNAME` 필터가 거른다는 전제를 요구사항으로 둔다.
6. OBSAgent `Wrote` 논리 이름의 번호는 **실제 저장 번호**를 쓴다 — raw 카드 `CTRLTAG` 미도입은 D-010 의 OBSAgent 논리 이름 규약과 무관하다(규약 불변).
7. **단일 쓰기 주체(ICS 하나) 전제** — 선검사와 쓰기 사이의 경쟁은 없다. 이 전제를 규격에 명시한다.

근거:

- **무인 운영에서 방금 취득한 데이터가 격리되지 않고 밤이 계속된다.** 카운터 되감김(재시작 등)이 원인이면 충돌 1회로 원인 전체가 자가 치유된다 — 선검사 루프가 점유 구간을 지나 빈 번호에 착지하고 카운터가 따라간다.
- **신호를 카드 존재에서 값 비교로 옮기면 카드 구성이 모든 파일에서 균일**해져 쓰기 분기가 없다. 상한 100000회 = 번호 공간 한 바퀴로 종료가 보장된다.
- **`UNIQNAME` 폐지**: "불변 정본 키"라는 뜻이 이탈했고(충돌 시 실명과 갈라진다), 유일성은 번호 증가 방식이 `FILENAME` 에 구조로 보장한다 — 뜻이 바뀐 이름은 계승하지 않는다(D-013 원칙).

영향:

- 구 규격 v1.2 의 2.3.1절 전면 대체 · 5.2절(`UNIQNAME`·`NAMECLSH` 폐지, `ORIGNAME` 신설) · 5.11절(pair 규칙) — 재작성판(V1)이 흡수한다. 상세: `raw_fits_spec/archive/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md` **Part 2** (통합 문서의 현행 판은 `raw_fits_spec/README.md` 의 '현재 기준선' 표를 볼 것 — Part 2 의 절 번호는 v0.5 기준이라 그 판을 가리킨다).
- **D-010 · D-012 의 "아카이브 근거 삼총사 `UNIQNAME`/`FILENAME`/`CTRLTAG`" 문구를 `FILENAME`(+`ORIGNAME`) 로 개정한다** — `CTRLTAG` 는 v1.9 미도입 확정, pair 식별은 `FILENAME` `DETID` 필드가 담당.
- `ics_sim` — `rawpair.py`(선검사 루프·되감음·상한, clash 격리 제거, `UNIQNAME` 제거, `ORIGNAME` 항상 기록) · `state.py`(카운터 동기화·순환) · `sequencer._store()`(확정 이름만 수령) · `tests/test_raw_header.py`(RETIRED 에 `UNIQNAME`·`NAMECLSH` 추가, 충돌·되감음·상한 시험 신설).
- converter — C-항목 신설: MEF `UNIQNAME` 공급원 변경 또는 동반 폐지 (LEECU 판단, 통합 문서 Part 1 §1).


## D-017: 사이트 코드 넷째 자리를 KASI 로 한다 (`TESTBED`/`KMTT` 폐지, D-011 개정)

> ⚠️ **항목 3·4·6 이 개정됐다** — 값 어휘 넷(항목 1·2)과 대응, `ORIGIN`·`OBSERVAT` 를 합치지 않는 것(항목 5), 사이트별 기본값 표와 망원경·FPA 번호가 어긋난다는 주의(항목 6 의 표)는 유효하다.
>
> - **항목 3** 의 정규화 조항 → **D-020**(2026-08-24): 넷 밖의 값은 **기동을 거부한다** (본문에 취소선).
> - **항목 4** 의 `KMTK` 보정 `0` → **`+9:00`** (운영자 확정 2026-09-12 · raw spec v1.14 2.2절). 경계는 UT 15:00 = **KST 00:00** 이고, 관측일은 곧 **KST 날짜**다. 관측소 셋의 근거(동지 때 관측 종료와 시작의 중간)는 관측 야간이 없는 실험실에는 성립하지 않는다. 그래서 KST 자정을 쓰고, 벤치에서 사람이 보는 날짜와 파일 이름의 날짜가 같아진다. 관측소 셋의 검산 불변식(현지 12:30)은 그대로이고 KASI 는 그 셈 밖이다. 구현은 `ics-archon-v1.0-build` 의 `rawpair.OBSDATE_SHIFT_MIN`(`982ebe5`, 2026-09-13)이고 `main` 은 합류 대기다 — `main` 의 `ics_sim/ics_sim/rawpair.py` 는 지금도 `'KMTK': 0` 이다. ⚠️ **그 구현이 없는 코드(`982ebe5` 이전의 브랜치 · 합류 전 `main` 의 `ics_sim`)로 찍은 KASI 파일·로그의 `<YYYYMMDD>` 는 보정 0(UT 날짜)이다** — 그 가운데 KST 09:00 이전에 찍은 프레임은 하루 앞선 이름을 가지므로, 옛 KASI 자료를 날짜로 묶을 때는 이 경계를 감안한다. DevNote(`ics_sim`·`ics_archon`)에는 이 결정의 항목이 없고, 결정의 근거 문면은 그 브랜치 `ics_sim/ics_sim/rawpair.py` 의 보정표 주석이다.
> - **항목 6** 의 "낱개 설정을 두지 않는다" → **raw spec 5.3.1절이 정한 값별 덮어쓰기 경로**가 정본이다. 사이트 하나가 기본값을 정하는 것은 맞다. 다만 이 결정을 실은 raw spec v1.5 의 5.3.1절부터 이미 *"ICS INI 에 값이 있으면 그쪽이 이긴다"*(`[site.<이름>]`·`[site]`)였다. 현행 5.3.1절은 이렇게 가른다: `TELESCOP`·`ORIGIN`·측지값 셋은 `[site.<이름>]`·`[site]` 가 이기고, `FPAID` 는 `[camera] fpaid` 가 이기며(`[site.*]` 로는 못 바꾼다), ⛔ `OBSERVAT` 는 덮어쓸 수 없다.
> - 영향 둘째 항목의 **"바꾸지 않으면 KASI 자료가 짝 탐색에 걸리지 않는다"는 틀린 서술이다.** 그 정규식은 출력 MEF 이름을 짓는 `default_output_name()` 에만 있고, 짝을 찾는 `find_pair()` 는 `.MK.fits`↔`.NT.fits` 접미사만 바꿔 끼운다(사이트 코드와 무관하다). 바꾸지 않았다면 KASI 자료는 짝은 찾되 출력 이름이 fallback 경로로 빠졌을 것이다.

날짜: 2026-08-25
관련: D-011(개정) · D-014 · D-015 · `raw_fits_spec` raw spec v1.5
상태: **Accepted (Amended)** — 항목 3 의 정규화 조항은 **D-020 이 대체**했다 (2026-08-24) · 항목 4 의 `KMTK` 보정은 **`+9:00`** 으로 개정됐다 (운영자 확정 2026-09-12) · 항목 6 의 "낱개 설정 없음" 은 raw spec 5.3.1절의 덮어쓰기 경로가 대체한다 (머리 배너) — raw spec v1.5 반영 완료, **구현 완료**(`rawpair.KASI_SITE` · `site_of_observatory()` — `ics-archon-v1.0-build` 브랜치, **`main` 합류 예정**).

결정:

1. **`OBSERVAT` 의 값은 `CTIO` · `SSO` · `SAAO` · `KASI` 넷뿐이다.** `TESTBED` 를 폐지한다.
2. **파일명 접두어 `<SITE>` 는 `KMTC` · `KMTA` · `KMTS` · `KMTK` 넷뿐이다.** `KMTT` 를 폐지하고 그 자리를 **`KMTK`** 가 대신한다.
3. 대응은 `KMTC`=CTIO · `KMTA`=SSO · `KMTS`=SAAO · **`KMTK`=KASI** 이다. ~~네 코드 밖의 값은 전부 `KMTK` 로 정규화하고 경고를 남긴다(구 규칙의 `KMTT` 자리를 그대로 승계).~~ ⚠️ **정규화 조항은 D-020(2026-08-24)이 대체했다** — 넷 밖의 값은 정규화하지 않고 **기동을 거부한다**. 사이트가 파일명·좌표·`ORIGIN`·관측일 경계를 함께 끌고 가므로 조용히 떨어뜨리면 오타 하나가 자료의 정체를 통째로 바꾼다. 규격 쪽은 raw spec v1.13 2.2절이, 산출물 쪽은 ICD v4.3 §2.1 이 D-020 기준으로 정리됐다(운영자 확정 2026-09-23).
4. 관측일 보정(D-014)에서 `KMTK` 의 보정은 **0** 이다 — 구 `KMTT` 와 같다. 세 관측소 경계가 모두 현지 12:30 이라는 검산 불변식은 변하지 않는다.
   > ⚠️ **2026-09-12 운영자 확정으로 개정됨** — `KMTK` 의 보정은 **`+9:00`**(경계 UT 15:00 = KST 00:00, 관측일 = KST 날짜, raw spec v1.14 2.2절)이다. 그 구현이 없는 코드(`982ebe5` 이전의 브랜치 · 합류 전 `main` 의 `ics_sim`)로 찍은 KASI 파일은 보정 0(UT 날짜)이다. 경위는 머리 배너.
5. `ORIGIN` 은 종전대로 `SSO`/`CTIO`/`SAAO`/`KASI` 다. **이 개정으로 `ORIGIN` 과 `OBSERVAT` 의 값이 네 자리 모두 일치하게 된다** — 두 카드의 뜻(생성처 vs 관측소)은 여전히 다르므로 카드를 합치지 않는다.
6. **사이트가 정해지면 `TELESCOP` 과 `FPAID` 도 함께 정해진다** (운영자 확정 2026-08-25). ICS INI 는 사이트 하나를 받아 전부 유도하며 낱개 설정을 두지 않는다.
   > ⚠️ **"낱개 설정을 두지 않는다" 는 raw spec 5.3.1절의 값별 덮어쓰기 경로가 대체한다** — 사이트가 정하는 것은 **기본값**이다. `TELESCOP` 은 `[site.<이름>]`·`[site]`, `FPAID` 는 `[camera] fpaid` 가 이긴다. 경위는 머리 배너.

   | 사이트 | `<SITE>` | `OBSERVAT` | `ORIGIN` | `TELESCOP` | `FPAID` |
   | --- | :---: | :---: | :---: | --- | :---: |
   | CTIO | `KMTC` | `CTIO` | `CTIO` | `'KMTNet 1.6m #1'` | `'FPA#2'` |
   | SSO | `KMTA` | `SSO` | `SSO` | `'KMTNet 1.6m #3'` | `'FPA#1'` |
   | SAAO | `KMTS` | `SAAO` | `SAAO` | `'KMTNet 1.6m #2'` | `'FPA#3'` |
   | KASI | `KMTK` | `KASI` | `KASI` | `'KMTNet 1.6m #0'` | `'FPA#0'` |

   **망원경 번호와 FPA 번호는 일치하지 않는다** — CTIO 망원경 `#1`·FPA `#2`, SSO 망원경 `#3`·FPA `#1`, SAAO 망원경 `#2`·FPA `#3` 으로 **관측소 셋 다 어긋난다**(KASI 만 `#0`/`#0` 으로 같은데 이는 우연이다). 망원경 번호는 설치 순서이고 `FPAID` 는 조립체 정체이며 조립체는 사이트 간 이동이 가능하다. 어긋남을 오타로 보고 맞추면 검출기 귀속이 틀어진다.

   SSO 값은 **레거시 실측으로 확인**됐다(`KMTNk.20170209.044131.Rawheader.txt`: `OBSERVAT='SSO'` + `TELESCOP='KMTNet 1.6m #3'`). 나머지 셋은 운영자 제시분이다. 망원경 번호는 설치 순서이고 `FPAID` 는 조립체 정체이며 조립체는 사이트 간 이동이 가능하다. 어긋남을 오타로 보고 맞추면 검출기 귀속이 틀어진다.

근거:

- **`TESTBED` 는 장소가 아니라 용도였다.** 나머지 셋이 전부 관측소 이름인데 한 자리만 성격이 달라, `OBSERVAT`(관측소) 카드의 값 공간이 균질하지 않았다. 실제로 그 자리에서 자료를 만드는 곳은 KASI 이고, `ORIGIN` 은 이미 `KASI` 를 쓰고 있었다 — 같은 장소를 두 카드가 다른 이름으로 부르고 있었던 셈이다.
- **`KMTT` 의 `T` 는 T chip 과 눈으로 충돌한다.** 파일명·채널 표기가 함께 놓이는 문맥(`CHMAP_*` 의 `T01`…)에서 오독을 부른다. `KMTK` 는 KASI 의 머리글자이고 chip 문자 M·K·N·T 중 `K` 와 겹치지만 접두어 자리에서만 쓰이므로 혼동 여지가 작다.

영향:

- **raw spec v1.5** — 2.2절 `<SITE>` 표·정규화 규칙·관측일 보정, 5.3절 `OBSERVAT`·`ORIGIN` 행. 반영 완료.
- **converter (LEECU 소관, C-항목 신설)** — 파일명 정규식 `^(KMTC|KMTS|KMTA|KMTT)\.` 의 넷째 대안을 `KMTK` 로 바꿔야 한다. **바꾸지 않으면 KASI 자료가 짝 탐색에 걸리지 않는다.** *(⚠️ 오기 — `find_pair()` 는 접미사만 바꿔 끼우므로 짝은 찾는다. 걸리는 것은 출력 MEF 이름이다(`default_output_name()` 의 fallback 경로). 머리 배너)* L0 MEF prefix `kmtt` → `kmtk` 도 함께. ✅ **반영 완료 (2026-09-04)** — converter v2.4.0(정규식·`SITE_PREFIX`/`OBS_PREFIX`) · ICD v4.2 판올림(§2.1, 구 v4.1 은 archive).
- **`ics_sim` / `ics_archon`** — `rawpair.OBSERVAT`·`ORIGIN_OF`·`TESTBED_SITE`·`normalize_site()`·관측일 보정표, `config._SITE_TELID`, `state.site_code` 기본값, `ics_sim.ini` 주석. ⚠️ **사이트 판별이 `OBSERVATORY` 기준으로 개정된 `ics-archon-v1.0-build` 에서 함께 처리한다** — `main` 의 `ics_sim` 은 IP 판별 구판이라 여기서 고치면 머지가 충돌한다.
- **D-011 의 `<SITE>` 표를 대체한다.** ⛔ D-015(호스트 IP 판정)는 그 뒤 **폐지**됐고(2026-08-24), 사이트 판별은 `[node] observatory` 한 줄이다.

## D-018: 노출 번호 공간을 6자리 전부로 확장한다 (D-016 항목 1·2 개정)

날짜: 2026-08-25
관련: D-016(항목 1·2 개정) · D-011 · D-014
상태: **Accepted** — raw spec v1.5 반영 완료, **구현 완료**(`rawpair.NUM_SPACE = 1_000_000`, 되감음·상한 — `ics-archon-v1.0-build` 브랜치, **`main` 합류 예정**).

결정:

1. **번호 공간은 `000000`–`999999`** 다. 파일명 `<NNNNNN>` 의 6자리를 전부 쓴다.
2. 카운터는 **1000000 도달 시 `000000` 으로 되감는다.**
3. D-016 항목 2 의 충돌 회피 루프에서 **되감음 경계는 999999→000000**, **상한은 1000000회**(공간 정확히 한 바퀴)다. 실패 조건이 그것 하나뿐이라는 규칙은 변하지 않는다.
4. 자릿수·zero-padding 규칙(6자리 고정폭, 0 좌측 패딩)은 D-011 그대로다 — **파일명 형식은 바뀌지 않는다.**

근거:

- **구 상한 `099999` 는 6자리 중 다섯 자리만 쓰는 규칙이라 맨 앞 자리가 항상 `0` 이었다.** 레거시 관례를 그대로 옮긴 것인데, 형식이 6자리인 이상 번호 공간도 6자리인 편이 규칙이 하나 줄어든다 — "6자리 고정폭"과 "10만 상한"을 따로 기억할 필요가 없다.
- **번호 공간이 10배가 되면 되감김 자체가 드물어진다.** D-016 이 다루는 충돌은 되감김이 주된 원인이므로, 공간 확장은 그 원인을 직접 줄인다.
- 상한이 100000회에서 1000000회로 늘어도 **종료 보장은 그대로**다 — 여전히 "공간 한 바퀴"이고, 루프가 그 횟수에 이르렀다면 저장 자리가 실제로 가득 찬 것이다.

영향:

- **raw spec v1.5** — 2.3절 항목 1·2. 반영 완료.
- **`ics_sim` / `ics_archon`** — `rawpair.py` 되감음 경계·상한 상수, `state.py` 카운터 순환, 충돌·되감음·상한 시험의 경계값. ⚠️ D-017 과 같은 이유로 **`ics-archon-v1.0-build` 에서 함께 처리한다.**
- **converter (LEECU)** — 정규식이 `\d{6}` 이라 형식 변화가 없다. **영향 없음.**
- 기존 `0xxxxx` 자료와 충돌하지 않는다 — 새 공간이 옛 공간을 포함한다.

## D-019: 노출 정체성 카드를 `EXPID` 로 한다 (`ORIGNAME` 폐지, D-016 항목 4·5 개정)

날짜: 2026-08-26
관련: D-016(항목 4·5 개정) · D-010 · D-012 · 구판 규격 v1.2 **2.3.1절**(`EXPID` 를 삭제했던 조항, 2026-08-12 — 이 항목이 되살린다) · `raw_fits_spec` raw spec v1.6
상태: **Accepted** — raw spec v1.6 반영 완료, **구현 완료**(`EXPID` 카드 · 견본 pair 반영 — `ics-archon-v1.0-build` 브랜치, **`main` 합류 예정**).

결정:

1. **`ORIGNAME` 을 폐지하고 `EXPID` 를 신설한다.** 값은 **`<SITE>.<YYYYMMDD>.<NNNNNN>`** — 카운터가 이 노출에 **처음 배정한** 식별자이고, 모든 파일에 항상 기록한다.
2. **`EXPID` 에는 `DETID` 필드(`.MK`/`.NT`)가 없다.** 따라서 **pair 양쪽에서 값이 같다** — 구 `ORIGNAME` 은 `DETID` 필드를 달아 상이였다.
3. **5.9절 "반드시 상이" 가 7장에서 6장으로 준다** — `DETID` · `CHMAP_LT/LB/RT/RB` · `FILENAME`. `EXPID` 는 "반드시 동일" 쪽이다.
4. **충돌 신호 = `FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값 ≠ `EXPID`** (값 비교 — 카드 존재가 아니다). `EXPID` 결측은 충돌이 아니라 헤더 결함으로 분류한다. `DETID` 필드 제거는 이미 D-016 항목 5(짝 이름 유도)가 규정한 연산이다.
5. **`FILENAME` 의 comment 를 `'FITS file name as written to storage'` 로 바꾼다.** 종전 `'Filename assigned by ICS'` 는 `ORIGNAME` 의 `'Original filename assigned by ICS counter'` 와 똑같이 "ICS 가 배정" 계열이라 **둘의 차이가 comment 에서 드러나지 않았다.**
6. 견본 pair 의 노출 번호를 `012345`/`012340` 에서 **`123456`/`123450`** 으로 옮기고 **견본 파일 이름도 함께 옮긴다** — D-018 로 번호 공간이 6자리 전부가 됐으므로 맨 앞 자리가 `0` 이 아닌 값을 보인다. 충돌 사례(`FILENAME` ≠ `EXPID`)는 유지한다.

근거:

- **짝을 잇는 단일 키가 카드 추가 없이 생긴다.** 지금까지 pair 를 묶으려면 파일명에서 `.MK`↔`.NT` 를 치환해야 했다(D-016 항목 5). `EXPID` 는 양쪽에 같은 값이 있으므로 **그 카드 하나로 묶인다** — 폐지된 `PAIRFILE` 이 하려던 일을 중복 카드 없이 해낸다. MEF 조립에서 특히 값싸다.
- **두 정체성 카드의 뜻이 comment 에서 갈린다.** 충돌이 났을 때 "어느 쪽이 디스크의 이름인가" 가 이 두 카드의 요점인데, 종전에는 두 comment 가 같은 계열이라 그 요점이 보이지 않았다.
- **잃는 것은 충돌 판별의 한 단계**다 — 문자열 직접 비교에서 "`DETID` 필드를 뗀 뒤 비교" 로 는다. 다만 그 연산은 이미 규격이 정의해 둔 것이라 새 규칙이 아니다.

⚠️ **`EXPID` 는 한때 폐지됐던 이름을 되살린 것이다** (구판 v1.2 2.3.1절, 2026-08-12 운영자 확정 삭제). 그때의 삭제 근거 셋 중 둘은 이미 해소됐다:

| 당시 근거 | 지금 |
| --- | --- |
| **중복 제거** — `FILENAME`·`UNIQNAME`·`EXPID`·`EXPNUM` 넷이 같은 정보를 담아 서로 어긋날 수 있다 | **해소** — `UNIQNAME`·`EXPNUM` 은 폐지됐고, 이번엔 `ORIGNAME` 을 **대체**하므로 카드 수가 늘지 않는다 |
| **MEF 목적지 중복** — MEF 정의서가 `UNIQNAME` 을 *"unique filename or exposure ID"* 로 받는데 전달할 값이 둘이 된다 | **해소** — `UNIQNAME` 폐지로 소멸 |
| **레거시 연속성** — `EXPID` 는 이 저장소가 새로 만든 낱말이고 레거시·MEF·converter 어디에도 없다 | **유효하나**, pair 를 잇는 단일 키라는 이득이 이를 넘는다고 판단했다 |

⚠️ 당시 실제 사고였던 **"`EXPID` 가 실수 카드로 저장돼 zero-padding 이 파괴됐다"**(`'20260811.000010'` → `20260811.00001`, DevNote 11.13.2)는 **값이 `<SITE>` 접두로 시작해 숫자로 읽힐 여지가 없어** 구조적으로 막힌다. 규격 5.0절의 "식별자 keyword 는 문자열 카드 필수" 규칙과 이중 방어다.

영향:

- **raw spec v1.6** — 2.3절 4·6항 및 폐지 목록 · 5.0절 · 5.4절 표 · 5.9절(상이 7→6) · 5.10절 · 검증 체크리스트 4·5항 · 견본 pair 4장(파일 이름 포함). 반영 완료.
- **판정 원장 v1.14 · 통합 문서 v0.6** — 제자리 개정 완료.
- **converter (LEECU 소관, C-항목)** — ⓐ `ORIGNAME` 을 읽던 자리를 `EXPID` 로 옮긴다 ⓑ 충돌 판별이 "`DETID` 필드를 뗀 뒤 비교" 로 한 단계 는다 ⓒ **짝 탐색을 파일명 파싱 없이 `EXPID` 하나로** 할 수 있게 된다.
- **`ics_sim` / `ics_archon`** — `rawcards.CARDS`·`PAIR_DIFF`(7→6) · `rawhdr.exposure_header` · `sequencer`(`name_stem()` 호출이 빠지고 `orig_suffix` 를 그대로 싣는다) · `emitter` · labtest 내장 템플릿 · 시험 3종 · `_vendor`. ⚠️ **D-017 과 같은 이유로 `ics-archon-v1.0-build` 에서 처리한다** — `main` 의 `ics_sim` 은 구판이라 여기서 고치면 머지가 충돌한다.

---

## D-020: 사이트 판별은 `[node] observatory` 설정 한 줄로 한다 (D-015 대체)

날짜: 2026-08-24
관련: **D-015**(대체 대상) · D-011(사이트 코드 prefix) · D-014(관측일) · **D-017**(사이트 코드 넷) · `operations/ICS_DEPLOYMENT_CHECKLIST.md` · ACT-008 · ACT-009
상태: **Accepted** — ⚠️ **구현은 `ics-archon-v1.0-build` 에 있고 `main` 은 합류 대기다** (`main` 트리에는 `siteid.py` 가 아직 있다). 그 브랜치에서 `ics_sim`/`ics_archon` 구현 완료(`siteid.py` 삭제) + raw spec 2.2절 제자리 정정(2026-08-29).

결정:

1. **실효 사이트는 ICS 설정 `[node] observatory` 한 줄이 정한다.** 값 어휘는 FITS `OBSERVAT` 카드와 같은 **`CTIO` · `SSO` · `SAAO` · `KASI`** 넷이다 (D-017). 적은 값이 **그대로 카드**가 되므로 ini 를 보면 헤더에 무엇이 실릴지 그대로 보인다.
2. **그 넷 밖의 값은 기동을 거부한다.** 조용히 `KASI` 로 떨어뜨리지 않는다 (`rawpair.site_of_observatory()` 가 `ValueError`). ⚠️ 구판 `observatory = TESTBED` 로 설치된 사본은 **기동하지 않는다** — `KASI` 로 고치고 `[site.testbed]` 절도 `[site.kasi]` 로 바꿔야 한다.
3. **호스트 IP 판정(D-015)을 폐지한다.** `ics_sim/ics_sim/siteid.py` · `site_from_ip` · `tests/test_site_id.py` 를 **삭제한다** — 되살리지 말 것.
4. **그 한 줄에서 `telid` · `site` · 좌표 · `ORIGIN` · `INSTRUME` · `TELESCOP` · `FPAID` 가 함께 유도된다.** 사이트를 옮겨 배포할 때 고치는 것은 이 한 줄뿐이다.
5. **TC 의 `TELID` 는 교차검증 경고에만 쓴다** — 서로 다른 값마다 한 번씩만 경고하고, 파일명에는 영향을 주지 않는다 (D-015 에서 유지).

근거:

- **두 위험 중 하나를 골라야 했고, 더 나쁜 쪽을 막았다.** D-015 는 *"설정 묶음을 통째로 잘못 복사한 배포"* 를 막으려 했다. 그러나 그 방식은 **반대 위험**을 안고 있다 — **NIC 이 내려가거나 낯선 대역에 붙으면 진짜 관측 자료가 벤치 이름(`KMTK`)으로 저장된다.** 앞의 위험은 배포 절차로 잡을 수 있지만, 뒤의 위험은 **관측 중에 일어나고 아무도 못 잡는다.**
- **자료의 정체가 망 상태에 좌우되면 안 된다.** 사이트는 파일명 `<SITE>` · 좌표 · `ORIGIN` · 관측일 경계를 함께 끌고 간다. 그것이 **NIC 이 살아 있는가**에 달려 있는 구조는, 값이 틀렸을 때 원인이 자료 어디에도 남지 않는다.
- **관대함을 뺀 것이 이 결정의 절반이다.** D-015 는 모르는 코드를 `KMTK` 로 정규화했다 — 그 관대함이 곧 *"관측소 자료를 실험실 이름으로 아카이브에 들여보내는 경로"* 였다. D-020 은 **모르는 값에 기동을 거부**해 그 경로를 막는다.
- **어휘를 `OBSERVAT` 카드와 같게 둔 것이 요점이다.** ini 에 적은 낱말이 그대로 헤더 카드가 되므로 규격·converter 를 고칠 일이 없고, 사람이 ini 만 보고 결과를 안다.

영향:

- `ics_sim` — **`siteid.py` · `tests/test_site_id.py` 삭제**(시험 28개 제거, 사이트 시험 11개 신설). ⚠️ **`ics-archon-v1.0-build` 에서다** — `main` 트리에는 아직 남아 있다. `NodeCfg.observatory` 신설 + `site`/`telid` 유도, `rawpair.site_of_observatory()`/`SITE_OF_OBSERVATORY`, `config` 의 낡은 키 경고(`site`·`telid`·`site_from_ip`). ⚠️ `rawpair.normalize_site()` 는 **남아 있으나 `<SITE>` 결정 경로가 아니다** — 관측일 경계 계산의 내부 안전망과 TC `TELID` 대조용이다.
- **`operations/ICS_DEPLOYMENT_CHECKLIST.md` 가 유일한 방어가 된다** — 판정이 대신 잡아 주지 않으므로 기동 배너 확인을 건너뛰면 안 된다.
- **ACT-009 의 성격이 바뀐다** — "대역이 바뀌면 실자료가 KMTK 로 저장된다" 는 위험이 사라졌다. 남는 필요는 **배선·방화벽·노드 주소**를 확정하는 망 문서 자체다.
- **raw spec 2.2절** — `<SITE>` 필드 설명의 *"실효 사이트는 호스트 IP 로 판정하며 판정이 설정을 이긴다 (D-015)"* 와 *"넷 밖은 `KMTK` 로 정규화"* 를 이 결정으로 고쳤다 (v1.8 제자리 정정, 2026-08-29). ✅ 그 정정은 `41845da`(2026-08-30) 로 **`main` 에 합류**했고 그 뒤 판의 규격 2.2절에도 그대로 있다. ⚠️ **그 문장은 v1.3~v1.8 여섯 판을 그대로 통과했다** — 판올림이 "이번에 바꿀 것" 만 보고 본문 나머지는 복사되기 때문이다.
- 상세 경위는 `ics_sim/DevNote.md` **11.27**, 문서 정합 경위는 `ics_archon/DevNote.md` **6장** (⚠️ 그 노트는 `ics-archon-v1.0-build` 에만 있다 — `main` 에 `ics_archon/` 이 아직 없다).

## D-021: 돔 방위 세 카드(`DSTELAZ`·`DSAZ`·`DAZERR`)는 **redis 에서만** 읽는다

날짜: 2026-09-11
관련: **D-013**(레거시 raw keyword 판정) · raw spec **5.7절** · 원장 3.6절 · ACT-008 · `ics_archon/DevNote.md` **11.79**(경위) · 11.52(이 결정이 대체한 종전 결론)
상태: **Accepted** — ⚠️ **구현은 `ics-archon-v1.0-build` 에 있고 `main` 은 합류 대기다.** 그 브랜치에서 ICS·ICG 구현 완료 + 시험 39개 신설. ✅ **규격 본문 정정은 raw spec v1.13 에서 끝났다** (2026-09-12) — 5.7절 돔 행을 셋으로 가르고 Source 를 `REDIS (dome control)` 로, 규약을 **5.7.3절**로 신설했다. ⚠️ 이 절은 브랜치에서 `main` 으로 옮겨 실은 사본이다 — 브랜치 쪽 같은 절의 이 줄도 합류 때 함께 맞출 것.

결정:

1. **돔 방위 셋의 원천은 돔 제어 프로그램의 redis 다.** 서버는 `127.0.0.1:6379`, 키는 `dome_tel_az` → `DSTELAZ` · `dome_az` → `DSAZ` · `dome_del_az` → **`DAZERR`** 다. 서버·포트·키 이름은 ini `[dome]` 소관이고, **어느 키가 어느 카드로 가는지는 코드에 둔다**(`domeaz.CARD_OF` — 규격 5.7절 소관이라 운용이 바꿀 값이 아니다).
2. **출처는 한 번에 하나다.** `[dome] source = redis` 면 그 세 카드는 **redis 만** 본다 — TC 가 나중에 `TCSSTATUS` 에 그 이름을 실어 보내도 쓰지 않는다. `off` 면 종전 경로(와이어값 + `DAZERR` 는 ICS 계산)가 그대로 돈다. ⛔ 두 출처를 섞지 않는 이유는 **헤더만 보고는 어느 쪽 값인지 가릴 수 없기** 때문이다.
3. **키가 없으면 카드는 `NC` 다.** 돔 제어 프로그램이 키에 **TTL(수백 ms)** 을 걸어 두므로 *"키가 없다"* 가 곧 *"지금 자료가 없다"* 다. ⛔ **직전 값을 캐시해 이어 싣지 않는다** — 돔이 멈춘 뒤에도 마지막 방위가 노출마다 새 값처럼 나가면, 헤더만 보는 하류(converter·아카이브)에 그것이 낡았다는 사실이 어디에도 안 남는다.
4. **`dome_del_az` 만 없으면 `DAZERR` 를 나머지 둘로 계산한다** (−180 ~ +180 접기). 규격 5.7절이 원래 정한 `ICS calculation` 이고 피연산값도 redis 것이라 2번을 벗어나지 않는다. ⛔ 손에 든 값 둘로 낼 수 있는 것을 `NC` 로 싣는 것은 실측을 버리는 것이다.
5. **`DALTERR` 는 이 결정 밖이다.** 그 카드는 **고도** 어긋남(`DSALT` − `DSTELALT`)이고 피연산값이 `AUXSTATUS` 에서 실제로 온다. ⛔ 방위값으로 덮지 않는다 — 시험이 못박는다.
6. **의존성을 더하지 않는다.** `redis-py` 를 쓰지 않고 표준 `asyncio` 스트림으로 `MGET` 한 번을 주고받는다. ICS·ICG 의 런타임 의존은 `python3-numpy` 하나 그대로다.

근거:

- **TC 는 돔 방위를 아예 보내지 않는다 — 원천으로 확인했다.** `TCSAgent/TCSAgent.latest/KMTNet/commands.c:2834` 가 돔 블록으로 내는 것은 `DSUP DSLW DSSAF DSAUTO DSALT DSTEL` 뿐이고, **TCSAgent 트리 전체에 `DSAZ`/`DSTELAZ` 가 0건**이다. 11.52 의 *"TC 쪽 구현 대기"* 는 오지 않을 것을 기다린 것이었고, 벤치 헤더의 `NC` 는 결함이 아니었다.
- **규격이 이 길을 이미 열어 두었다.** 5.7절의 돔 카드 Source 가 `TCS relay or REDIS` 다(원장 v1.10_revision, 운영자 5차 개정). 새 경로를 만든 것이 아니라 열려 있던 갈래를 실현했다.
- **신선도가 값의 일부다.** Radionode `stale_after` · 진공 `Alive` 카운터와 같은 규범이다 — 낡은 값을 이어 싣는 것은 결측을 없애는 것이 아니라 **틀릴 수 있는 값으로 덮는 것**이고 규격 5.0절 sentinel 의 정신에 어긋난다.
- **`off` 를 남긴 것은 규격 견본을 지키기 위해서다.** 견본 pair 의 바이트 대사(`ics_sim/tests/test_raw_draft.py`)가 세 값을 **와이어에 실어 역산**하는 자료다. 무조건 redis 로 못박으면 정본 재현이 깨진다 — 눈금 하나로 갈라 두 경로를 다 지켰고, 어느 쪽이든 출처는 하나다.

영향:

- **취득 경로가 redis 서버를 읽게 됐다.** ⭐ 그 서버는 **설치 사이트에 이미 있다**(운영자 확인 2026-09-11) -- 새로 들이는 것이 아니다. 안 떠 있거나 돔 제어 프로그램이 키를 안 쓰면 세 카드가 `NC` 다. ⭐ **노출은 막지 않는다** — 접속 거부·시한 초과·프로토콜 오류가 전부 "자료 없음" 으로 접히고, 읽기는 `TCSSTATUS` 질의와 나란히 돌아 노출 시간에 더해지지 않는다.
- **읽는 시점이 계통마다 다르다** — science 는 노출 개시(`DATE-OBS` 를 찍는 그 순간), guide 는 **프레임마다**다. guide 주기 1.3초가 키 TTL 보다 길어 `GO` 당 한 번이면 둘째 장부터 TTL 이 지난 값을 싣는다.
- **`DAZERR` 의 성격이 계산에서 중계로 바뀐다.** ✅ 규격 본문은 **raw spec v1.13 5.7절에서 정정했다**(2026-09-12) — `DAZERR` 의 Source 는 `REDIS (dome control) or ICS calculation`(계산은 키가 없을 때만 도는 예비 경로)이고, `DSAZ`/`DSTELAZ` 행은 `TCS relay` 를 빼고 `REDIS (dome control)` 이다 (TC 가 안 보낸다는 것이 확인됐다).
- **`telemetry.CANNED_TCS` 에서 방위 두 값을 뺐다** — `DSAZ='12.3'`/`DSTELAZ='12.1'` 을 지어내 넣던 것이 *"TC 가 방위를 중계한다"* 는 거짓을 모사하고 있었다. 고도(`DSALT`/`DSTELALT`)는 남는다.
- **시험이 실서버에 붙지 못하게 막았다** — 배포 ini 가 `source = redis` 이고 `ics_archon` 스위트 대부분이 그 ini 로 실제 노출을 돌리는데, **벤치·관측소 기계에는 진짜 redis 가 돌고 있다**. `tests/conftest.py` 의 autouse 가드가 한 자리에서 끄고, 돔 경로를 보는 모듈만 표식으로 빠져나가 가짜 서버를 세운다. 코드 기본값을 `off` 로 둔 것도 같은 이유다.
- 상세 경위는 `ics_archon/DevNote.md` **11.79**.

## D-022: 저장되지 않은 프레임은 노출 번호를 소비하지 않는다

날짜: 2026-09-07 (운영자 확정) · 등재 2026-09-12
관련: **D-016**(충돌 시 번호 증가) · **D-018**(번호 공간 6자리) · raw spec **2.3절 8항** · 5.4.1절 · 9.2절 · 10.1-6·10.1-7 · `ics_archon/DevNote.md` **11.40**(첫 확정: `ABORT`) · **11.41**(규범을 넓힌 경위)
상태: **Accepted** — ⚠️ **구현은 `ics-archon-v1.0-build` 에 있고 `main` 은 합류 대기다.** 그 브랜치에서 ICS·ICG 양쪽 시퀀서에 배선 완료 + 시험 15개 신설.

결정:

1. **파일이 하나도 생기지 않은 프레임은 노출 번호를 먹지 않는다.** 취득 SW 는 그 프레임이 집었던 번호를 **기록에서 되감아**, 같은 프로세스에서든 재시작 뒤에든 다음 노출이 그 번호를 쓴다. 아카이브의 노출 번호는 **연속이 원칙**이다.
2. **되감는 자리 넷** — `ABORT` · guide `GUIEXPCTRL`(`EXPENABLE=FALSE`) · guide 취득 SW 의 **정상 종료** · 백엔드 실패(`DMA WAIT TIMEOUT` 등).
3. ⛔ **`STOP` 은 번호를 먹는다** — 그때 노출 중이던 프레임을 **저장한 뒤** 멈추기 때문이다 (raw spec 5.4.1절). 같은 이유로 **반쪽 pair**(한쪽 컨트롤러만 저장 성공)도 그 번호는 소비된 것이다.
4. **결번을 허용하는 예외 넷** — ① 취득 SW 가 **내부 오류**로 죽은 프레임(시퀀서 상태를 모르는 채 번호를 손대지 않는다) ② **번호 공간 고갈**(되감아도 같은 벽이다) ③ **노출 번호 기록 파일을 못 읽은 기동** ④ **종료 시 저장 상한을 넘겨 독출은 됐으나 파일을 못 낸** 프레임. ⭐ **이 정도의 결번은 받아들인다**(운영자 판단 2026-09-07).
5. ⛔ **번호의 구멍만 보고 원인을 추측하지 않는다** — 넷 다 취득 SW 로그에 자국이 남으므로 그때의 로그를 본다. 거꾸로 **결번을 `ABORT` 의 증거로 읽어서도 안 된다.**
6. ⛔ **되감는 것은 *기록*뿐이고 진행 중인 카운터 값은 건드리지 않는다** — 같은 프로세스의 번호 재사용은 이미 현행 거동이고, 둘을 같이 건드리면 진행 중인 노출 번호 질의(OBSAgent `ExpNum`)까지 흔들린다.

근거:

- **①(재사용)과 ②(건너뛰기) 중 ①을 골랐다** (운영자 2026-09-07). 같은 사건에 두 답이 있던 비대칭 — *같은 프로세스는 번호를 재사용하고 재시작은 건너뛰던 것* — 을 없애는 데 둘 다 쓸 수 있었으나, ①의 값어치는 **아카이브 번호의 연속성**이다.
- **②를 버린 논거는 "구멍이 `ABORT` 인지 사고인지 구별할 수 없다"** 였다. 사고의 흔적은 로그와 `ERROR` 통보가 남기지 번호 구멍이 남기는 것이 아니다.
- **`ABORT` 하나로는 부족했다** — `BackendError` 를 던지는 자리(`DMA WAIT TIMEOUT` 등)가 벤치에서 흔할 실패라, 거기를 막지 않으면 구멍이 계속 생겨 ①을 고른 실효가 깎인다. 그래서 규범의 문장 자체를 *"`ABORT` 는"* 에서 **"파일이 안 생긴 프레임은"** 으로 넓혔다 (11.41).
- **안전 조건은 하나다** — *"번호를 집었고 그 프레임은 저장까지 못 갔다"* 를 뜻하는 플래그가 이미 있었고(번호를 집을 때 서고 저장이 끝나면 내려간다), 되감기는 그 플래그가 참일 때만 돈다. **저장을 마친 프레임의 번호는 되감기가 건드릴 수 없다.**
- **사고사는 보호된다** — 되감기는 명시적 경로에서만 불리고, *죽은 프로세스는 아무것도 되감지 못한다.* 노출 중 프로세스가 죽었을 때 재실행이 같은 번호로 덮어쓰는 것을 막는 종전 보호(번호를 쓰는 시점에 기록)는 그대로다.

영향:

- **하류(아카이브·DTS·색인)** — 노출 번호의 구멍은 **정상 상태가 아니다**. 다만 ⛔ **연속성을 무결성 판정의 근거로 삼지는 않는다** — 구멍의 뜻은 그때의 취득 SW 로그가 정하고, 파일 쪽 유일 키는 여전히 `FILENAME` 이다 (D-016).
- **guide 도 같다** — 카운터 기록이 설정파일 이름을 따라 갈리므로 science 와 독립이고(raw spec 9.2절), 규범은 양쪽에 같이 걸린다.
- ⚠️ **벤치 계획서의 기대값이 뒤집혔다** — 옛 계획서로 재면 "틀렸다" 로 읽는다.

---

## D-023: L0 MEF 의 sky WCS 는 Gaia 측성의 **seed** 다 — 산출 WCS 가 아니다

날짜: 2026-09-23 (운영자 확정)
관련: **D-003**(CHIPFLP/orientation) · **D-004**(software/product/geometry 버전 분리) · **D-005**(placeholder ≠ calibration) · **D-013**(레거시 keyword 판정 · C-항목을 LEECU 몫으로 남김) · **D-016**·**D-019**(`UNIQNAME` 폐지, 정체는 `FILENAME`+`EXPID`) · 변경점 **C-5 · C-11 · C-12 · C-13 · C-17 · C-18** · raw spec **4.3절**(포장 순서 규범) · **5.0절**(sentinel 금지) · **5.4절**(`IMAGETYP` 어휘) · **5.6.1절**(`Cn_*` 자리) · **5.9절**(pair 일관성) · `mef_fits_spec` Main Keywords **§5.5** · ICD **v4.2 §7·§12** · `Detector_Ch_to_AmpID_Map_v1.1` · 구현 커밋 `3e82467`(converter) · `ef2d834`(preproc)
상태: **Accepted** — ✅ **`main` 합류 완료** (2026-09-23: PR #15 `cb6fbca` 구현·규격, PR #16 `cec2016` §2.1 D-020 정리). 영향 첫 항목의 문서 갱신도 완료다. ⏳ 남은 셋은 이 저장소에서 닫을 수 없다 — `.docx` 배포본(`python-docx` 부재) · `raw_fits_spec/__reference/` 의 바이트 동일 사본(읽기 전용, ICS 몫) · 항목 3 의 `BORESIGHT_X`(seed 로서는 무해하므로 릴리스를 막지 않고, Gaia 매칭 실관측 1장으로 닫는다).

결정:

1. **L0 amp extension 의 sky WCS 는 L1 Gaia 측성의 초기값으로만 존재한다.** 산출 WCS 가 아니므로 ⛔ **이것으로 좌표를 재지 않는다** — 위치는 해가 풀린 L1 WCS 에서만 나온다. Main Keywords §5.5 가 이 카드군을 *"placeholder 성격"* 이라 부른 것을 v2.4.0 은 **`CRVAL=CRPIX=0.0` 으로 문자 그대로** 구현했고, `CTYPE`/`CD` 는 유효했으므로 모든 L0 가 오류 없이 **춘분점 근방(RA≈359.93 · Dec≈+0.25)** 으로 풀렸다. 그것은 placeholder 가 아니라 raw spec 5.0 절이 금지한 *"형식만 유효한 틀린 값"* 이다.
2. **상태 어휘는 새로 만들지 않고 파이프라인 것을 그대로 쓴다.** L0 가 `WCSNAME='TCS-SEED'` · **`WCSAPPRX=T`** · **`WCSSOLVE=F`** 를 *"아직 아님"* 값으로 미리 싣고, L1 측성 단계는 카드를 **만드는 것이 아니라 값만 뒤집는다** — 성공하면 `WCSAPPRX=F`·`WCSSOLVE=T` + `WCSRMS`/`WCSNSTAR`/`WCSNREF`/`WCSNMAT`(카탈로그는 primary `WCSCAT`, 해 성공 CCD 수는 `WCSNSOLV`), 실패하면 seed 를 그대로 두고 `WCSSOLVE=F` + 사유 `WCSFAIL`. ⛔ **`WCSCAL` 같은 L0 전용 이름을 두지 않는다** — 같은 사실에 두 어휘가 생기면 하류가 어느 쪽을 봐야 할지 알 수 없다.
3. **tangent point 는 망원경 boresight 하나이고 64개 extension 이 같은 `CRVAL` 을 공유한다.** amp 별 어긋남은 전부 `CRPIX` 가 진다. boresight 는 DETSIZE 모자이크 픽셀 **(9418.0, 9699.0)** 이고 primary `BOREPIXX`/`BOREPIXY` 로 공개한다. overscan 이 왼쪽인 strip 5–8 은 `CRPIX1` 에 **+48**. ⏳ **미결**: `BORESIGHT_X=9418.0` 은 기하학적 모자이크 중심 9446.5 에서 **28.5 px(11.3″) 벗어나 있고 Y 만 정확히 중심**이다 — 레거시가 27열 prescan 을 이중으로 뺀 자국일 수 있다. seed 로서는 무해하나(아래 근거) **Gaia 매칭 실관측 1장이면 닫힌다.**
4. **`CD` 행렬은 64 amp 전부 동일하고 amp 별 부호 반전을 하지 않는다.** serial 독출 방향(strip 1–4 ↔ 5–8) · TOP/BOT · e2v image section(A/D) 이 chip 마다 갈리지만 ⛔ **그 중 어느 것도 저장 순서에는 닿지 않는다** — raw spec 4.3 절이 raw 프레임을 두 축 모두 CCD 좌표 오름차순으로 저장하도록 **요구**하고(관찰이 아니라 요구사항이다), K·N 의 180° 장착은 채널→타일 순서가 이미 흡수한다. ⚠️ ICD §4 의 *"chip-dependent flip 을 적용하지 않는다"*(D-003)만 읽으면 *"그러면 회전이 픽셀에 남아 있으니 K·N 의 CD 를 뒤집어야 한다"* 로 읽히는데 **그 독해는 틀렸고, 뒤집으면 64 중 32 amp 가 어긋난다.**
5. **포인팅이 파싱되지 않으면 WCS 카드를 하나도 쓰지 않는다** (`WCSOMIT=T`). ⛔ **기본 좌표로 메우지 않는다** — `CTYPE` 만 있고 `CRVAL` 이 없으면 리더가 `CRVAL=0` 을 기본값으로 삼아 1번의 버그가 그대로 되살아난다. `WCSDIM` 도 함께 뺀다(Main Keywords §5.5 의 필수 목록에서 벗어나는 자리라 `WCSOMIT` 으로 기계 판별을 남긴다).
6. **하늘을 보지 않는 프레임에는 seed 를 쓰지 않는다** — `IMAGETYP` ∈ {`BIAS`, `DARK`, `DOMEFLAT`} 이면 `WCSSKY=F` · `WCSOMIT=T` 이고, L1 은 측성을 **시도하지 않고** 사유를 `NOT_SKY_FRAME` 으로 남긴다. ⛔ **이것은 실패가 아니다.** `OBJECT`·`SKY`(박명 플랫)·`FLAT` 은 `WCSSKY=T` 로 seed 를 싣는다 — `SKY` 는 대체로 별이 보이고, `FLAT` 은 어휘가 돔/박명을 가르지 않으므로(별도 `DOMEFLAT` 이 있다) **시도하는 쪽**에 둔다. ⭐ **`LTV`/`LTM`·`DTV`/`DTM`·`ATV`/`ATM` 은 프레임 종류와 무관하게 항상 싣는다** — 검출기 좌표지 하늘 좌표가 아니고, 마스터 프레임 조립에 필요하다.
7. **L0 의 seed 상태 카드는 L1 primary 로 넘기지 않는다.** `WCSNAME`·`WCSAPPRX`·`WCSSOLVE`·`WCSOMIT`·`BOREPIXX`·`BOREPIXY` 를 `io_l1.CARRY_EXCLUDE` 에 넣는다. L1 primary 는 L0 primary 를 통째로 물려받으므로, 그대로 두면 **Gaia 로 푼 SCI 위에서 primary 가 "안 풀렸음" 을 선언한다.** 살아 있는 상태는 SCI 별 `WCSSOLVE`/`WCSAPPRX`/`WCSRMS` 와 primary 의 `WCSCAT`/`WCSNSOLV` 다.
8. **`PRODVER` 를 `v2.1.1` → `v2.2.0` 으로 올리고 `GEOMVER` 는 유지한다** (D-004 적용 — amp 순서·구간·배치가 바뀌지 않았다). 범프를 부르는 포맷 변경은 ⓐ 신규 키워드군(WCS seed · IRAF 변환 · amp 정체 · 프레임 종류) ⓑ **`AMPINFO` 컬럼 40 → 52**(끝에 덧붙여 기존 색인 불변) ⓒ **`VOLTINFO` 행 9 → 37**(C-18: 컨트롤러 레일 실측 28행 추가) ⓓ `UNIQNAME` 폐지(D-016/D-019 의 귀결 — 공급원이 사라져 항상 빈 카드였다) ⓔ `CHANNEL` 값 범위 1–8 → **1–16**(C-11: CCD 출력 채널은 chip 당 16개다).

근거:

- **조용히 틀리는 쪽이 비어 있는 쪽보다 위험하다.** 원장 13장이 이미 *"조용히 **틀린 값**이 들어가는 쪽이 더 위험하다 — `DATE-OBS`(변환 시각) · **`RA`/`DEC`(그럴듯한 좌표)**"* 라고 적어 두었다. v2.4.0 의 `CRVAL=0` 은 정확히 그 목록의 사례였고, **오류를 내지 않았기 때문에** 아무도 걸러내지 못했다. 5번(전면 생략)과 6번(프레임 종류)은 같은 원칙의 적용이다 — 하늘을 안 본 프레임에 하늘 좌표를 박아 두는 것도 같은 부류의 거짓이다.
- **어휘를 새로 만들지 않은 이유는 인계가 이미 설계돼 있었기 때문이다.** `astrometry.py` 머리말이 *"Starting from the approximate WCS inherited from L0"* 라 적고, `steps/assemble.py::ccd_wcs_cards()` 는 복사한 카드에 문자 그대로 `"approximate WCS from L0"` 주석을 달고 `WCSAPPRX=True` 를 붙인다. **받는 쪽 규약이 먼저 있었고 L0 가 그것을 안 채웠던 것**이지, 규약이 없던 것이 아니다.
- **`BORESIGHT` 는 지어낸 값이 아니라 복원한 값이다.** 운용 중인 레거시 32-extension 파일에서 `CRPIX1 − LTV1 + (DETSEC.x1−1)` 이 **CTIO(2026)·SSO(2017) 두 사이트 32개 extension 전부에서 9418.0**, Y 는 9699.0(= DETSIZE 중심 (1+19397)/2)으로 나온다. CEU 참조 변환기(`kmt_ceu_legacy32_to_l0amp_mef_v2.py`)의 mock64 산출물도 같은 값을 재현한다. ⭐ **seed 로서 11.3″ 는 무해하다** — 검증에서 **28″ 어긋난 seed 로도 수렴**했으므로 solver 의 capture radius 안이고, 그래서 이 미결이 릴리스를 막지 않는다.
- **4번은 규격이 요구사항으로 못박은 사실에 기댄다.** raw spec 4.3 절은 *"raw 프레임은 검출기 공간 순서로 완전 정렬되어 저장된다 … 이것은 관찰이 아니라 **요구사항**이다"* 라고 적는다. 즉 독출 방향은 overscan 이 타일의 어느 쪽에 붙는지만 정하고 픽셀 순서는 건드리지 않는다. ⏳ 단 그 조항의 준수 시험(flat/star 수열, raw spec **OI-3**)은 아직 돌지 않았고 K·N 180° 장착(**OI-17 ③**)도 열려 있다 — **4.3 절이 실기에서 깨지면 그 32 amp 는 `CD` 부호와 `CRPIX` 대칭 이동이 함께 필요하다**(부호만 뒤집는 것은 틀린 수정이다).
- **6번의 값어치는 QA 가독성이다.** 플래그가 없으면 하룻밤 바이어스 20장이 각각 `WCSSOLVE=F` + `WCSFAIL` 을 남겨 **실패 20건처럼 읽힌다** — 실제로는 해당 없음이다. 별 검출이 돌지 않으므로 처리 시간도 준다.
- **릴리스 게이트가 못 잡던 것이 있었다.** `fits_value()` 가 문자열 값을 free format 으로 써서 `XTENSION= 'IMAGE'` 가 고정형식 규칙을 어겼는데, RELEASE_CHECKLIST §3 이 요구하는 `astropy.verify('exception')` 은 **통과**시켰고 **fitsverify 는 129개 오류로 거부**했다(64 image HDU × 2 + `EQUINOX`). 값 필드를 20자로 채워 지금은 0 error 다. 같은 경로에서 69자 이상 문자열의 **닫는 따옴표 누락**과, `ENDID` 카드를 `END` 로 오인해 헤더 리더가 세 카드 만에 멈추던 것도 함께 닫혔다.
- **끝까지 확인했다.** 별밭 OBJECT raw pair 를 만들어(`mef_converter/tools/make_starfield_raw.py`, 별 6000개 · TCS 포인팅 오차 +26″/−19″ · 회전 0.18° · 스케일 1.003) L0 → L1 전 구간을 돌렸다: **4개 CCD 전부 해 성공**(`WCSNSOLV=4`, RMS 0.028–0.035″), 해가 **진짜 하늘과 중앙값 0.002–0.004″** 로 일치, L1 primary 에 L0 seed 카드 0장. 같은 raw 를 v2.4.0 으로 변환해 같은 조건에 넣으면 별은 789개 똑같이 검출하면서 **매칭 0건 · `NO_SEED_ZONE`** 으로 시작조차 못 한다. ⭐ 이 결과는 **converter 의 amp 패킹·구간 기하가 픽셀 단위로 맞다는 독립 검증**이기도 하다 — 64 amp 중 하나라도 자리가 틀렸으면 그 amp 의 별이 계통적으로 어긋나 잔차가 터진다.

영향:

- ✅ **문서 갱신 완료 (2026-09-23)**:
  - `release/RELEASE_CHECKLIST.md` **§4** `VOLTINFO` row count 9 → 37 (`NVOLT` 대조로 점검), **§3** 에 `fitsverify` 0 error 추가.
  - `sop/SOP_MEF_CONVERTER_RUN.md` 버전표 v2.5.0 / `PRODVER` v2.2.0, `.hdu_verify.txt` sidecar, 검증 스니펫 기대값.
  - `mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` → **v1.1**: §4.7 신설(seed WCS 상태·`WCSSKY`·`CHMAPOK`), §5.5 전면 개정, §5.2 채널 정체(C-11, `CHANNEL` 1–16), §6 `AMPINFO` 40 → 52 컬럼, §8 `VOLTINFO` 9 → 37행, `PIXSCALE` `0.400` → **`0.395`**(규격에 남아 있던 실제 오류), `UNIQNAME` 폐지 명시.
  - `mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.2.md` → **v4.3**: §7.1·§7.2 신설(하위절로 넣어 §8~§13 번호를 밀지 않았다 — 이 원장과 raw spec 이 "ICD §7·§12" 를 인용한다), §4 에 `CD` 무반전 주석, §9·§12 재작성, 폐지된 `Pair_Spec_v1.2` 참조 정정.
  - 구판 둘은 `mef_fits_spec/archive/` 로. 파일명을 참조하던 트리 내 9개 파일 갱신.
- ⏳ **남은 것 — 이 저장소에서 닫을 수 없다**:
  - **`.docx` 배포본 미생성.** `python-docx` 가 없어 `md_to_docx.py` 를 돌리지 못했다. 현행 배포본이 없는 상태이고 명령은 `mef_fits_spec/README.md` 에 적어 두었다.
  - **`raw_fits_spec/__reference/` 의 Keywords v1.0 바이트 동일 사본**이 v1.1 판올림으로 어긋난다. `__` 접두 폴더는 읽기 전용(운영자 확정 2026-08-22)이라 ICS 쪽 몫이다. ICD 국문본(`…_v4.1_KO.md`, 그쪽 유일본)도 v4.3 기준 두 판 뒤처진다.
  - ✅ **ICD §2.1 의 사이트 코드 정규화 충돌은 D-020 쪽으로 정리됐다** (운영자 확정 2026-09-23). 넷 밖의 값은 정규화하지 않고 **기동을 거부한다**. ICD v4.3 §2.1 에 "Changed in v4.3 (D-020)" 문단을 넣고, **D-017 항목 3 의 정규화 조항을 취소선 처리**해 원장이 스스로 모순되지 않게 했다(D-017 상태는 `Accepted (Amended)`). converter 의 파일명 fallback 도 같은 취지로 **조용하지 않게** 만들었다 — D-011 문법에 안 맞는 이름은 계속 변환하되(픽셀은 멀쩡하고 `-o` 로 이름을 줄 수 있다) 접두어가 격하됐다는 것을 경고로 남긴다.
- **하류 호환은 유지된다.** `WCSSKY` 카드가 없는 옛 L0 는 `True` 로 읽어 종전 동작 그대로다. `AMPINFO` 신규 컬럼은 **끝에 덧붙여** 기존 색인이 불변이고, `VOLTINFO`/`TELEMETRY` 는 전처리가 **존재만 확인**하므로 행 수 변화가 안전하다. `RADECSYS` 는 `steps/assemble.py` 가 **이름으로** 복사하므로 폐기 철자를 그대로 두고 `RADESYS` 를 병기했다.
- **seed 우선순위는 바뀌지 않았다.** `pipeline.py` 는 여전히 per-chip 템플릿(`data/astrom_template.json`, 평균 SIP 왜곡 포함)을 L0 seed 보다 **우선**하고 L0 는 템플릿·포인팅이 없을 때의 **대체 경로**다. 템플릿이 왜곡을 싣고 L0 TAN seed 는 못 실으므로 그 순서가 맞다 — 이번에 고친 것은 **그 대체 경로가 실제로는 동작하지 않던 것**이다.
- ⏳ **`WCSCAL` 이라는 이름을 쓴 중간본이 있었다** — 2번으로 폐기했다. 되살리지 말 것.
- ⚠️ **견본 `KMTK.20260915.000034` 는 `IMAGETYP='BIAS'` 다** — 6번에 따라 그 MEF 에는 이제 sky WCS 가 없다. seed 를 보려면 `IMAGETYP` 을 `OBJECT` 로 바꾼 사본이나 위 별밭 생성기를 쓴다.

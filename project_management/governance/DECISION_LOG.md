# KMTNet-CEU Decision Log

최종 갱신일: 2026-08-22

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
  *(이 문구는 이후 세 번 개정됐다 — `EXPID`는 D-013에서 폐지됐다가 **D-019
  에서 되살아났고**, 근거는 `FILENAME`(+`ORIGNAME`, D-016) 을 거쳐 최종
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
  근거로 삼아야 한다 (`EXPID`는 D-013 에서 폐지했다).
  *(D-016 개정: 근거 삼총사는 `FILENAME`(+`ORIGNAME`) 로 대체 — `UNIQNAME`
  폐지, `CTRLTAG` 미도입. **D-019 재개정: `ORIGNAME` → `EXPID`.**)*
- 실기 전환 시 `archon.py`의 `write_frame()`만 채우면 되고, 시퀀서·명령
  처리부·메시지 규약은 무개정이다 (DevNote 1.2의 2단계 약속 유지).
- 상세 규격은 `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 2.3·2.5절,
  구현 경위는 `ics_sim/DevNote.md` 11.13.

---

## D-013: 레거시 raw keyword 를 하나씩 판정하고, 컨트롤러 정체는 색인형으로 싣는다

날짜: 2026-08-13
관련: D-010 · D-011 · D-012 · `raw_fits_spec` 5.5.0 · 5.13절 · 변경점 C-17 · C-18
상태: **Accepted** — 규격 반영 완료, `ics_sim` 구현 진행.

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

날짜: 2026-08-13
관련: D-009 · D-011 · D-013 · `raw_fits_spec` 2.3·5.7·5.13절 · OI-10 종결 · OI-12 해소
상태: **Accepted** — 이충욱(LEECU) 협의 후 운영자 확정, `ics_sim` 구현 완료.

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

  근거는 **각 사이트 동지 때 관측 종료와 관측 시작 사이의 중간 시각**이다.
- **`<YYYYMMDD>` 는 `DATE-OBS` 의 날짜와 일반적으로 다르다 — 그것이 의도다.**
  한 관측 야간이 하나의 날짜로 묶이는 것이 목적이고, `DATE-OBS` 는 그와 무관하게
  그 노출의 실제 UT 순간을 담는다.
- **`DATE-OBS` 는 `SHOPEN` 지시 시점의 UT 를 날짜·시각 모두 담고, 초는 소수점
  셋째자리(밀리초)까지 필수다.**
- **`UT` 카드는 폐지한다** — `DATE-OBS` 와 완전한 중복이다.
- **`<SITE>` 는 `KMTC`/`KMTS`/`KMTA` 밖의 값을 모두 `KMTT` 로 떨어뜨린다.**

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

## D-015: 사이트는 호스트 IP 로 판정하고, 그 판정이 설정을 이긴다

> ⚠️ **D-017 (2026-08-25) 로 코드 개정** — 이 항목 본문의 `KMTT`(벤치)는 전부 **`KMTK`(KASI)** 로 읽는다. 판정 규칙 자체는 유효하다.

날짜: 2026-08-13
관련: D-011 (사이트 코드 prefix) · D-014 (관측일) · `operations/ICS_DEPLOYMENT_CHECKLIST.md` · ACT-008 · ACT-009
상태: **Accepted** — `ics_sim` 구현 완료 (시험 308개).

결정:

- **실효 사이트는 호스트 자기 IPv4 주소의 `/24` 대역으로 판정한다.**

  | 대역 | 사이트 |
  |---|---|
  | `192.168.14.0/24` | CTIO `KMTC` |
  | `192.168.13.0/24` | SAAO `KMTS` |
  | `192.168.15.0/24` | SSO `KMTA` |
  | 그 밖 전부 | 벤치 `KMTT` |

  > ⚠️ **D-017 (2026-08-25)로 개정됨** — 떨어지는 코드가 **`KMTK`(KASI)** 다. 판정 규칙(IP 대역·판정이 ini 를 이김)은 그대로다.

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
상태: **Accepted** — 규격 문서 반영 완료(`raw_fits_spec/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md` Part 2), `ics_sim` 구현 예정.

결정:

1. **파일 번호 공간은 `000000`–`099999`** 이며 카운터는 100000 도달 시 `000000` 으로 초기화한다 (레거시 관례 계승).
   > ⚠️ **D-018 (2026-08-25)로 개정됨** — 공간은 **`000000`–`999999`**, 되감음은 **1000000**, 항목 2 의 상한은 **1000000회** 다. 나머지 규칙(선검사·카운터 동기화·실패 조건 하나)은 그대로다.
2. **쓰기 전에 후보 번호 N 의 MK · NT 두 경로를 모두 선검사**하고, 점유 시 N+1(099999 를 넘으면 000000 으로 되감음)로 재검사한다. **+1 증가가 100000회를 초과하면 멈추고 ERROR 를 출력하며 저장하지 않는다** — 상한 100000회 = 번호 공간 정확히 한 바퀴. 실패 조건은 이것 하나뿐이다.
3. 둘 다 빈 N 을 확정하고 **카운터를 N 으로 동기화**한다 (평소 노출 번호 영속화 경로 그대로, 옛값→새값 점프는 경고 로그).
> ⚠️ **D-019 (2026-08-26) 로 항목 4·5 개정** — `ORIGNAME` 을 폐지하고 **`EXPID`**(`<SITE>.<YYYYMMDD>.<NNNNNN>`, **pair 양쪽 동일**)가 대신한다. 충돌 신호는 `FILENAME` 의 `.MK`/`.NT` 꼬리를 뗀 값과의 비교다. 나머지 항목은 유효하다.

4. **`UNIQNAME` 을 폐지한다.** `FILENAME` = 실제 저장명이자 **아카이브 유일 키**, `ORIGNAME` = 카운터가 처음 배정한 이름 — 두 카드를 모든 파일에 **항상** 기록한다. **충돌 신호 = `FILENAME ≠ ORIGNAME`** (값 비교 — 카드 존재가 아니다). `ORIGNAME` 결측은 충돌이 아니라 헤더 결함으로 분류한다. 아카이브 근거는 **`FILENAME`(+`ORIGNAME`)** 이고 pair 쪽 식별은 `FILENAME` 꼬리(`.MK`/`.NT`) 치환으로 유도한다 — `CTRLTAG` · `PAIRFILE` 카드는 싣지 않는다(v1.9 미도입 확정). `NAMECLSH` 카드와 `clash/` 격리(구 규격 2.3.1)를 폐지한다.
5. 같은 노출의 재저장(유령 중복)은 **fail-open** 이며, raw 헤더 층(아카이브 색인·DTS·QL)의 `FILENAME ≠ ORIGNAME` 필터가 거른다는 전제를 요구사항으로 둔다.
6. OBSAgent `Wrote` 논리 이름의 번호는 **실제 저장 번호**를 쓴다 — raw 카드 `CTRLTAG` 미도입은 D-010 의 OBSAgent 논리 이름 규약과 무관하다(규약 불변).
7. **단일 쓰기 주체(ICS 하나) 전제** — 선검사와 쓰기 사이의 경쟁은 없다. 이 전제를 규격에 명시한다.

근거:

- **무인 운영에서 방금 취득한 데이터가 격리되지 않고 밤이 계속된다.** 카운터 되감김(재시작 등)이 원인이면 충돌 1회로 원인 전체가 자가 치유된다 — 선검사 루프가 점유 구간을 지나 빈 번호에 착지하고 카운터가 따라간다.
- **신호를 카드 존재에서 값 비교로 옮기면 카드 구성이 모든 파일에서 균일**해져 쓰기 분기가 없다. 상한 100000회 = 번호 공간 한 바퀴로 종료가 보장된다.
- **`UNIQNAME` 폐지**: "불변 정본 키"라는 뜻이 이탈했고(충돌 시 실명과 갈라진다), 유일성은 번호 증가 방식이 `FILENAME` 에 구조로 보장한다 — 뜻이 바뀐 이름은 계승하지 않는다(D-013 원칙).

영향:

- 구 규격 v1.2 의 2.3.1절 전면 대체 · 5.2절(`UNIQNAME`·`NAMECLSH` 폐지, `ORIGNAME` 신설) · 5.11절(pair 규칙) — 재작성판(V1)이 흡수한다. 상세: `raw_fits_spec/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md` **Part 2**.
- **D-010 · D-012 의 "아카이브 근거 삼총사 `UNIQNAME`/`FILENAME`/`CTRLTAG`" 문구를 `FILENAME`(+`ORIGNAME`) 로 개정한다** — `CTRLTAG` 는 v1.9 미도입 확정, pair 식별은 `FILENAME` 꼬리가 담당.
- `ics_sim` — `rawpair.py`(선검사 루프·되감음·상한, clash 격리 제거, `UNIQNAME` 제거, `ORIGNAME` 항상 기록) · `state.py`(카운터 동기화·순환) · `sequencer._store()`(확정 이름만 수령) · `tests/test_raw_header.py`(RETIRED 에 `UNIQNAME`·`NAMECLSH` 추가, 충돌·되감음·상한 시험 신설).
- converter — C-항목 신설: MEF `UNIQNAME` 공급원 변경 또는 동반 폐지 (LEECU 판단, 통합 문서 Part 1 §1).


## D-017: 사이트 코드 넷째 자리를 KASI 로 한다 (`TESTBED`/`KMTT` 폐지, D-011 개정)

날짜: 2026-08-25
관련: D-011(개정) · D-014 · D-015 · `raw_fits_spec` raw spec v1.5
상태: **Accepted** — raw spec v1.5 반영 완료, `ics_sim` 구현 대기.

결정:

1. **`OBSERVAT` 의 값은 `CTIO` · `SSO` · `SAAO` · `KASI` 넷뿐이다.** `TESTBED` 를 폐지한다.
2. **파일명 접두어 `<SITE>` 는 `KMTC` · `KMTA` · `KMTS` · `KMTK` 넷뿐이다.** `KMTT` 를 폐지하고 그 자리를 **`KMTK`** 가 대신한다.
3. 대응은 `KMTC`=CTIO · `KMTA`=SSO · `KMTS`=SAAO · **`KMTK`=KASI** 이며, 네 코드 밖의 값은 전부 `KMTK` 로 정규화하고 경고를 남긴다(구 규칙의 `KMTT` 자리를 그대로 승계).
4. 관측일 보정(D-014)에서 `KMTK` 의 보정은 **0** 이다 — 구 `KMTT` 와 같다. 세 관측소 경계가 모두 현지 12:30 이라는 검산 불변식은 변하지 않는다.
5. `ORIGIN` 은 종전대로 `SSO`/`CTIO`/`SAAO`/`KASI` 다. **이 개정으로 `ORIGIN` 과 `OBSERVAT` 의 값이 네 자리 모두 일치하게 된다** — 두 카드의 뜻(생성처 vs 관측소)은 여전히 다르므로 카드를 합치지 않는다.
6. **사이트가 정해지면 `TELESCOP` 과 `FPAID` 도 함께 정해진다** (운영자 확정 2026-08-25). ICS INI 는 사이트 하나를 받아 전부 유도하며 낱개 설정을 두지 않는다.

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
- **converter (LEECU 소관, C-항목 신설)** — 파일명 정규식 `^(KMTC|KMTS|KMTA|KMTT)\.` 의 넷째 대안을 `KMTK` 로 바꿔야 한다. **바꾸지 않으면 KASI 자료가 짝 탐색에 걸리지 않는다.** L0 MEF prefix `kmtt` → `kmtk` 도 함께.
- **`ics_sim` / `ics_archon`** — `rawpair.OBSERVAT`·`ORIGIN_OF`·`TESTBED_SITE`·`normalize_site()`·관측일 보정표, `config._SITE_TELID`, `state.site_code` 기본값, `ics_sim.ini` 주석. ⚠️ **사이트 판별이 `OBSERVATORY` 기준으로 개정된 `ics-archon-v1.0-build` 에서 함께 처리한다** — `main` 의 `ics_sim` 은 IP 판별 구판이라 여기서 고치면 머지가 충돌한다.
- **D-011 의 `<SITE>` 표를 대체한다.** D-015(호스트 IP 판정)의 판정 대상 코드도 `KMTT`→`KMTK` 로 읽는다.

## D-018: 노출 번호 공간을 6자리 전부로 확장한다 (D-016 항목 1·2 개정)

날짜: 2026-08-25
관련: D-016(항목 1·2 개정) · D-011 · D-014
상태: **Accepted** — raw spec v1.5 반영 완료, `ics_sim` 구현 대기.

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
관련: D-016(항목 4·5 개정) · D-010 · D-012 · **D-013**(`EXPID` 를 폐지했던 결정 — 이 항목이 되살린다) · `raw_fits_spec` raw spec v1.6
상태: **Accepted** — raw spec v1.6 반영 완료, `ics_sim`/`ics_archon` 구현 대기.

결정:

1. **`ORIGNAME` 을 폐지하고 `EXPID` 를 신설한다.** 값은 **`<SITE>.<YYYYMMDD>.<NNNNNN>`** — 카운터가 이 노출에 **처음 배정한** 식별자이고, 모든 파일에 항상 기록한다.
2. **`EXPID` 에는 컨트롤러 태그(`.MK`/`.NT`)가 없다.** 따라서 **pair 양쪽에서 값이 같다** — 구 `ORIGNAME` 은 꼬리를 달아 상이였다.
3. **5.9절 "반드시 상이" 가 7장에서 6장으로 준다** — `DETID` · `CHMAP_LT/LB/RT/RB` · `FILENAME`. `EXPID` 는 "반드시 동일" 쪽이다.
4. **충돌 신호 = `FILENAME` 의 `.MK`/`.NT` 꼬리를 뗀 값 ≠ `EXPID`** (값 비교 — 카드 존재가 아니다). `EXPID` 결측은 충돌이 아니라 헤더 결함으로 분류한다. 꼬리 제거는 이미 D-016 항목 5(짝 이름 유도)가 규정한 연산이다.
5. **`FILENAME` 의 comment 를 `'FITS file name as written to storage'` 로 바꾼다.** 종전 `'Filename assigned by ICS'` 는 `ORIGNAME` 의 `'Original filename assigned by ICS counter'` 와 똑같이 "ICS 가 배정" 계열이라 **둘의 차이가 comment 에서 드러나지 않았다.**
6. 견본 pair 의 노출 번호를 `012345`/`012340` 에서 **`123456`/`123450`** 으로 옮기고 **견본 파일 이름도 함께 옮긴다** — D-018 로 번호 공간이 6자리 전부가 됐으므로 맨 앞 자리가 `0` 이 아닌 값을 보인다. 충돌 사례(`FILENAME` ≠ `EXPID`)는 유지한다.

근거:

- **짝을 잇는 단일 키가 카드 추가 없이 생긴다.** 지금까지 pair 를 묶으려면 파일명에서 `.MK`↔`.NT` 를 치환해야 했다(D-016 항목 5). `EXPID` 는 양쪽에 같은 값이 있으므로 **그 카드 하나로 묶인다** — 폐지된 `PAIRFILE` 이 하려던 일을 중복 카드 없이 해낸다. MEF 조립에서 특히 값싸다.
- **두 정체성 카드의 뜻이 comment 에서 갈린다.** 충돌이 났을 때 "어느 쪽이 디스크의 이름인가" 가 이 두 카드의 요점인데, 종전에는 두 comment 가 같은 계열이라 그 요점이 보이지 않았다.
- **잃는 것은 충돌 판별의 한 단계**다 — 문자열 직접 비교에서 "꼬리를 뗀 뒤 비교" 로 는다. 다만 그 연산은 이미 규격이 정의해 둔 것이라 새 규칙이 아니다.

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
- **converter (LEECU 소관, C-항목)** — ⓐ `ORIGNAME` 을 읽던 자리를 `EXPID` 로 옮긴다 ⓑ 충돌 판별이 "꼬리를 뗀 뒤 비교" 로 한 단계 는다 ⓒ **짝 탐색을 파일명 파싱 없이 `EXPID` 하나로** 할 수 있게 된다.
- **`ics_sim` / `ics_archon`** — `rawcards.CARDS`·`PAIR_DIFF`(7→6) · `rawhdr.exposure_header` · `sequencer`(`name_stem()` 호출이 빠지고 `orig_suffix` 를 그대로 싣는다) · `emitter` · labtest 내장 템플릿 · 시험 3종 · `_vendor`. ⚠️ **D-017 과 같은 이유로 `ics-archon-v1.0-build` 에서 처리한다** — `main` 의 `ics_sim` 은 구판이라 여기서 고치면 머지가 충돌한다.

# KMTNet-CEU Decision Log

최종 갱신일: 2026-07-02

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

## D-007: L1 제품은 단일 MEF(SCI/MASK ×CCD + CALHIST, VAR는 옵션)로 한다

날짜: 2026-07-02 (같은 날 개정: VAR 기본 제외)

상태: Accepted (Amended)

결정:

- L1 제품은 노출당 1개 MEF로 하며, 기본 구조는 `PRIMARY` + `CHIPLIST` 순서의
  `SCI_x`/`MASK_x`(x=M,K,N,T) 8 image HDU + `CALHIST` binary table이다.
- 파일명은 `<prefix>.<YYYYMMDD>.<NNNNNN>.ceu.l1ccd.mef.fits`로 한다.

개정 (2026-07-02, VAR 기본 제외):

- VAR plane은 L1에 이미 있는 정보로 완전 재구성 가능하므로
  (`VAR = (RDNOISE² + SCI×flat) / flat²`; flat은 `CALFLAT` 참조, RDNOISE는 L0
  amp header/AMPINFO) 기본 제외한다. `VARINCL=F`와 재구성식을 primary header에 기록한다.
- 필요 시 `run --with-var`로 생성한다 (`VARINCL=T`).
- MASK는 raw ADU 기준으로 판정한 SATURATED/NONLINEAR 비트가 L1에서 재구성
  불가하므로 유지한다 (전체의 ~11%, 압축 시 미미).
- L1 `PRODVER`: v1.0 → v1.1.

근거:

- 노출 단위 관리·전송·provenance 추적이 단순하다.
- calibration history(단계·교정자료 버전·파라미터)를 제품 내부에 보존해야 한다 (규격 §12).
- VAR 제거로 노출당 약 3.1 GB → 1.7 GB (44% 절감), 정보 손실 없음.

영향:

- L1 파일 크기는 노출당 약 1.7 GB(float32 SCI ×4 + uint8 MASK ×4)이며 보관 정책은 KMT-009와 함께 다룬다.
- MASK bits: 1=BAD, 2=SATURATED, 4=NONLINEAR, 8=XTALK, 16=AMP_SEAM, 32=NO_OVERSCAN_FIT.
- 추가 절감이 필요하면 fpack 타일 압축(MASK 무손실, SCI 양자화)을 후속 검토한다.

## D-008: 전처리 파이프라인의 종점은 CCD 조립 + 근사 WCS로 한다

날짜: 2026-07-02

상태: Accepted

결정:

- L0→L1 전처리는 amp 교정 후 CCD 조립과 L0에서 물려받은 근사 WCS(`WCSAPPRX=T`) 기록까지 수행한다.
- 정밀 astrometry와 photometric zeropoint는 후단 파이프라인 몫이다.
- dark 보정은 구조만 두고 기본 off로 한다 (Rehearsal dark 특성 확인 후 결정).

근거:

- 전처리와 astrometry의 외부 의존성(기준 성표, 매칭 도구)을 분리해 freeze 위험을 줄인다.

영향:

- L1 소비자는 `WCSAPPRX=T`인 WCS를 근사값으로 취급해야 한다.
- CR rejection은 전처리에 포함하지 않는다 (후단, 필요 시 옵션).


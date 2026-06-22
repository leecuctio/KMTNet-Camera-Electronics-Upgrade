# KMTNet-CEU Decision Log

최종 갱신일: 2026-06-22

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


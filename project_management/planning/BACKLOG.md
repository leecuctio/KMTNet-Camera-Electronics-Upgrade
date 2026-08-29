# KMTNet-CEU Backlog

최종 갱신일: 2026-08-29

상태 값: `Todo`, `In Progress`, `Blocked`, `Done`

## Now

| ID | 영역 | 우선순위 | 상태 | 다음 행동 | 완료 조건 |
| --- | --- | --- | --- | --- | --- |
| KMT-001 | Calibration | P0 | Todo | Amp별 `GAIN`, `RDNOISE`, `SATURAT`, `LINMAX` 실측 계획과 데이터 출처 확정 | Placeholder 대신 실측값이 converter/header/table에 반영되고 calibration version이 기록됨 |
| KMT-002 | Orientation | P0 | Todo | flat/star sequence test로 TOP/BOT `READDIR` 확인 | `READDIR` 정책이 코드, ICD, keyword 문서에 일관되게 반영됨 |
| KMT-003 | Crosstalk | P0 | Todo | 64 x 64 crosstalk 측정 절차와 coefficient table 포맷 확정 | `XTALKINFO`가 실측값을 담고 `XTALKCAL=True`, `XTALKVER`가 유효 버전을 가짐 |
| KMT-004 | Telemetry | P0 | Todo | Archon controller, voltage, temperature, status telemetry source 확인 | `VOLTINFO`와 `TELEMETRY`가 운영 데이터로 채워짐 |

## Next

| ID | 영역 | 우선순위 | 상태 | 다음 행동 | 완료 조건 |
| --- | --- | --- | --- | --- | --- |
| KMT-005 | Validation | P1 | Todo | repeatable validation script 작성 | HDU count, extension names, shapes, table rows, selected keywords, gzip test, SHA256가 한 번에 검증됨 |
| KMT-006 | Packaging | P1 | Todo | release package 생성 절차를 스크립트화 | release 폴더, ZIP, checksum, README 포함 여부를 재현 가능하게 생성 |
| KMT-007 | Tests | P1 | Todo | header parsing, section calculation, pair finding 단위 테스트 추가 | raw 대용 small fixture 또는 synthetic FITS로 주요 함수 테스트 가능 |
| KMT-008 | Documentation | P1 | Todo | ICD, keyword 정리, README 간 version/value mismatch 점검 | 세 문서의 product/version/geometry/HDU 정책이 서로 일치 |
| KMT-009 | Data policy | P1 | Todo | 대용량 raw/generated FITS 보관 위치와 배포 제외 기준 정리 | release ZIP에는 코드/문서/checksum만 포함되고 대용량 데이터는 별도 보관 정책을 따름 |
| KMT-013 | Guider | P1 | Todo | gmon v2 커미셔닝(`gmon/DESIGN.md` §10): 원시 지오메트리(추가 9행·채널당 16컬럼 성격)·칩↔방위 매핑·표시 회전각·픽셀스케일(0.52″/px 가정) 실측, 신규 ICS 파일 저장 규약·TCS `fttgoto` 규약 확인 후 `dry_run` 해제 | §10 체크리스트 7항목이 실측값으로 `gmon.conf`에 반영되고 사이트에서 야간 무인 동작(감시→분할→FWHM→스냅샷→그래프→초점 보정) 확인 |

## Later

| ID | 영역 | 우선순위 | 상태 | 다음 행동 | 완료 조건 |
| --- | --- | --- | --- | --- | --- |
| KMT-010 | L1 pipeline | P2 | Done | (완료) `mef_pipeline/` v1.0: 설계 + full chain 구현 + mock 야간 검증 | `SCI_M`, `SCI_K`, `SCI_N`, `SCI_T` 생성 규칙과 calibration history 정의 |
| KMT-011 | Operations | P2 | Todo | 운영 command template와 failure recovery 절차 정리 | 관측일별 batch conversion과 실패 재시도 기준이 문서화됨 |
| KMT-012 | Provenance | P2 | Todo | raw input, converter, calibration DB, output checksum provenance 모델 정리 | 각 output이 입력 raw와 calibration 버전을 추적 가능 |

## 완료된 기준 항목

| ID | 영역 | 완료일 | 결과 |
| --- | --- | --- | --- |
| KMT-D001 | Product policy | 2026-06-22 | L0 raw product를 64-amplifier MEF로 확정 |
| KMT-D002 | Geometry | 2026-06-22 | MK -> M,K 및 NT -> N,T raw grouping과 19200 x 9400 geometry 검증 |
| KMT-D003 | Converter | 2026-06-22 | Converter v2.1.1 sample run 및 FITS verification 통과 |
| KMT-D004 | Release | 2026-06-22 | v2.1.1 release ZIP 및 checksum 생성 |
| KMT-D005 | L1 pipeline | 2026-07-02 | L0→L1 전처리 파이프라인 v1.0 구현 (`mef_pipeline/`), electrons/단일 MEF/근사 WCS 확정 (D-006~D-008), mock 야간(40노출) 검증 |
| KMT-D006 | Astrometry | 2026-07-03 | Gaia DR3 절대 astrometry (TAN–SIP3, 칩별 템플릿 초기값, plate scale 0.3952″/px 실측→CR-002), 야간 105/112칩 해결(rms 중앙값 0.31″), 로컬 Gaia 스토어(`gaia-ingest`/`--gaia-local`)로 사이트 오프라인 지원 |
| KMT-D007 | Guider | 2026-08-29 | 가이드 카메라 시상 모니터 v2 구현 (`gmon/`) — Archon 단일 FITS(4224×1033, 실측 지오메트리) 4칩 분할, SExtractor/PSFEx FWHM, 운용판(2026-03 SAAO) 형식 파리티, 3창 GUI(제어부/PSF 스냅샷/그래프), 별 주입 시험기·테스트 5종. 합성(FWHM 3.5px 오차 ≤1.9%)·실프레임 주입(500성, 산포 10%) 검증 통과 |


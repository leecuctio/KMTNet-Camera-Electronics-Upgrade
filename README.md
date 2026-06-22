# KMTNet Camera Electronics Upgrade (CEU)

KMTNet 광시야 탐사 카메라의 기존 **OSU 전자부**를 **STA Archon 컨트롤러 + Production Wallboard** 기반 신규 전자부로 교체하는 업그레이드 프로젝트의 작업 저장소입니다.

이 저장소는 프로젝트 관리 문서, MEF FITS 데이터 규격, L0 변환기 코드를 한곳에서 관리합니다.

## 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 공식 명칭 | KMTNet Wallboard and Camera Electronics Upgrade Project |
| 약칭 | KMTNet Camera Electronics Upgrade (CEU) |
| 목적 | OSU 전자부 → STA Archon + Production Wallboard 전환으로 장기 운영 안정성 확보 |
| 대상 사이트 | SSO (호주), CTIO (칠레), SAAO (남아공) |
| 주요 기간 | 2026-06 ~ 2026-12 |
| Project Manager | 이충욱 |
| 전환 전략 | SSO를 prototype site로 먼저 적용한 뒤 CTIO, SAAO로 순차 확산 |

## 저장소 구성

| 경로 | 내용 | 시작 문서 |
| --- | --- | --- |
| [`mef_converter/`](mef_converter/) | Archon MK/NT raw → L0 64-amplifier MEF 변환기와 참고 문서 | [README](mef_converter/README.md) |
| [`mef_fits_spec/`](mef_fits_spec/) | MEF FITS 데이터 산출물 규격 (keyword 정의 + ICD) | [README](mef_fits_spec/README.md) |
| [`project_management/`](project_management/) | 일정·governance·사이트·물류·형상관리 등 프로젝트 관리 보드 | [README](project_management/README.md) |
| `KMTNet_CEU_PMP_Final_v1.0.docx` | 프로젝트 관리 계획서(PMP) 원본 | — |

## 어디서 시작하나

- **프로젝트 관리 · 일정 · 역할 · 리스크** → [project_management/README.md](project_management/README.md)
- **카메라 출력 데이터 형식 · FITS keyword · ICD** → [mef_fits_spec/README.md](mef_fits_spec/README.md)
- **L0 변환기 사용 · 실행 방법** → [mef_converter/README.md](mef_converter/README.md)

## 현재 기준선

| 항목 | 값 |
| --- | --- |
| Primary 제품 | KMT-CEU L0 64-amplifier raw MEF |
| Converter | `mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.1.1) |
| Geometry version | `CEU-L0AMP-v2.1` |
| 기준 ICD | `mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx` (v4.0) |
| 카메라 구성 | science CCD 4개 (M, K, N, T), amplifier 64개, STA Archon controller 2대 |

> 변환기와 L0 제품 구조는 확정·검증되었고, `GAIN`/`RDNOISE`/`READDIR`/crosstalk/telemetry 등은 commissioning 이후 실측값으로 채웁니다. 남은 작업은 [planning/BACKLOG.md](project_management/planning/BACKLOG.md)에서 추적합니다.

## 일정 요약 (사이트 적용)

| 사이트 | 역할 | 목표 일정 |
| --- | --- | --- |
| SSO | Prototype Site | 2026-10-19 ~ 10-23 |
| CTIO | Second Site | 2026-11-17 ~ 11-20 |
| SAAO | Final Site | 2026-12-08 ~ 12-11 |

상세 마일스톤·Gate 기준: [schedule/SITE_UPGRADE_MILESTONES.md](project_management/schedule/SITE_UPGRADE_MILESTONES.md)

## 저장소 관리 정책

- Git에는 **소스 코드 · 문서 · 프로젝트 관리 문서**만 담습니다.
- 대용량 raw/generated FITS, gzip, release ZIP은 `.gitignore`로 제외하며, 파일명 · SHA256 · 생성 command를 문서에 기록해 별도 위치에서 관리합니다.
- 변경·형상 관리 기준은 [governance/](project_management/governance/)와 [configuration/](project_management/configuration/)를 따릅니다.
- 내부 프로젝트 저장소이므로 외부 공유 시 접근 권한과 공개 범위에 유의합니다.

# KMTNet-CEU Project Management

최종 갱신일: 2026-06-22

## 목적

이 폴더는 KMT-CEU 신규 전자부 카메라의 L0 64-amplifier raw MEF converter 및 관련 문서, 검증 산출물을 관리하기 위한 작업 보드이다.

현재 관리 기준은 로컬 작업 폴더에 정리된 다음 산출물이다.

- `mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx`
- `mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`
- `mef_converter/README_KMT_CEU_L0AmpRaw_Converter_v2.1.1.md`
- `mef_converter/KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md`
- `mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`
- `KMT_CEU_L0AmpRaw_Converter_v2.1.1_release.zip`

MEF FITS keyword 정의서와 ICD는 `mef_fits_spec/`에서 관리하며, 현행/구버전 기준은 `mef_fits_spec/README.md`를 따른다.

## 현재 기준선

| 항목 | 기준 |
| --- | --- |
| Product | KMT-CEU L0 64-amplifier raw MEF |
| Primary raw archive | 64 amp IMAGE extensions + binary tables |
| Converter | `mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` |
| Software/Product version | `v2.1.1` |
| Geometry version | `CEU-L0AMP-v2.1` |
| ICD 기준 | `mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx` |
| Keyword 기준 | `mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` |
| 검증 raw | `KMTN.20260116.000001.MK.fits`, `KMTN.20260116.000001.NT.fits` |
| 검증 output | `kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz` |
| gzip SHA256 | `7a55e7573eac899cd4b3c50b5dc747efe362a49bef505c1f0f90f53f68760289` |

## 관리 원칙

- L0 raw archive는 CCD-level image가 아니라 64 amplifier MEF이다.
- 각 amp extension은 active pixels와 local overscan pixels를 함께 보존한다.
- CCD-level `SCI_M`, `SCI_K`, `SCI_N`, `SCI_T`는 L1 calibrated product에서 생성한다.
- CEU Archon L0 packing 단계에서는 legacy OSU식 chip-dependent flip을 적용하지 않는다.
- `GAIN`, `RDNOISE`, `SATURAT`, `LINMAX`, `XTALKINFO`, `VOLTINFO`, `TELEMETRY`의 placeholder 값은 운영 calibration 값으로 오인하지 않는다.
- `XTALKCAL=True`는 실측 crosstalk coefficient가 들어간 경우에만 허용한다.

## 현재 상태

| 구분 | 상태 |
| --- | --- |
| L0 product 방향 | 확정 |
| MK/NT raw geometry | 검증 완료 |
| Converter v2.1.1 | 샘플 raw 기준 동작 검증 |
| FITS verification | 통과 |
| Release ZIP | 생성 완료 |
| Calibration values | 실측값 대기 |
| READDIR | flat/star sequence test로 최종 확인 필요 |
| 운영 telemetry | Archon/TCS/auxiliary 실데이터 연동 필요 |

## 디렉토리 구조

| 디렉토리 | 용도 |
| --- | --- |
| `planning/` | backlog, WBS, action item 관리 |
| `governance/` | 의사결정, RACI, gate review, 변경관리 |
| `schedule/` | master milestone, site upgrade 일정 |
| `sites/` | SSO, CTIO, SAAO 사이트별 실행 계획 |
| `logistics/` | 배송, 통관, 장비/예비품 추적 |
| `configuration/` | configuration baseline, software freeze, 변경 통제 |
| `science/` | science verification, calibration 추적 |
| `operations/` | recovery/rollback, 회의/커뮤니케이션 운영 |
| `release/` | converter/release package 점검 |
| `documents/` | 외부 유입 원본문서와 문서 인벤토리 |
| `templates/` | 주간보고, site log, gate review template |

## 핵심 관리 파일

| 파일 | 용도 |
| --- | --- |
| `planning/BACKLOG.md` | 남은 일, 우선순위, 완료 조건 |
| `planning/WBS.md` | work package와 주요 산출물 |
| `planning/ACTION_REGISTER.md` | 담당자별 action item 추적 |
| `governance/DECISION_LOG.md` | 확정된 기술 결정과 근거 |
| `governance/RACI.md` | work package별 책임 매트릭스 |
| `governance/TEAM_ROLES_AND_RESPONSIBILITIES.md` | 참여 연구원별 역할·책임·대리 |
| `governance/GATE_REVIEW_PLAN.md` | Gate 1-4 승인 기준 |
| `governance/CHANGE_CONTROL.md` | freeze 이후 변경 승인/rollback 기록 |
| `governance/RISK_REGISTER.md` | 주요 리스크와 완화 조치 |
| `schedule/SITE_UPGRADE_MILESTONES.md` | SSO, CTIO, SAAO 사이트별 업그레이드 마일스톤 |
| `sites/SSO/SITE_PLAN.md` | SSO 현장 적용 계획 |
| `sites/CTIO/SITE_PLAN.md` | CTIO 현장 적용 계획 |
| `sites/SAAO/SITE_PLAN.md` | SAAO 현장 적용 계획 |
| `logistics/LOGISTICS_PLAN.md` | 해운/항공 배송 계획 |
| `logistics/EQUIPMENT_TRACKER.md` | 주요 장비와 현장 도착 상태 |
| `configuration/CONFIGURATION_CONTROL.md` | repository, baseline, freeze 관리 |
| `science/SCIENCE_VERIFICATION_PLAN.md` | 과학 검증 항목과 합격 기준 |
| `operations/RECOVERY_ROLLBACK_PLAN.md` | 장애 단계별 복구/rollback 절차 |
| `operations/SAFETY_HANDLING_PLAN.md` | 현장 안전과 카메라 취급 기준 |
| `release/RELEASE_CHECKLIST.md` | 버전 릴리스 전 점검 절차 |
| `documents/SOURCE_DOCUMENTS.md` | 외부 유입 문서, 원본 위치, 해시, 내용 요약 |
| `documents/DOCUMENTATION_PLAN.md` | QA 기록, site report, closeout 문서 관리 |

## Git 관리 기준

- Git에는 소스 코드, 문서, 프로젝트 관리 문서를 담는다.
- Raw FITS, generated MEF FITS, gzip FITS, conversion summary, checksum sidecar, release ZIP은 `.gitignore`로 제외한다.
- 대용량 데이터 산출물은 파일명, SHA256, 생성 command를 문서에 기록하고 실제 파일은 별도 저장소 또는 데이터 보관 위치에서 관리한다.
- release ZIP은 Git에 직접 넣기보다 release checklist를 통해 재생성 가능한 산출물로 관리한다.

## 작업 흐름

1. 변경 전 `planning/BACKLOG.md`에서 작업 ID를 확인한다.
2. 코드, ICD, keyword, sample output 중 영향을 받는 산출물을 함께 확인한다.
3. 변경 후 converter 실행, FITS 검증, HDU/keyword/summary/checksum을 확인한다.
4. geometry 또는 product 정책이 바뀌면 `governance/DECISION_LOG.md`에 결정 기록을 남긴다.
5. configuration이나 software freeze 이후 변경은 `governance/CHANGE_CONTROL.md`와 `configuration/CONFIGURATION_CONTROL.md`에 남긴다.
6. 배포 전 `release/RELEASE_CHECKLIST.md`를 기준으로 release 폴더와 ZIP을 다시 만든다.

## 버전 규칙

| 변경 유형 | 예시 | 권장 처리 |
| --- | --- | --- |
| Patch | FITS card formatting, parser bug, README correction | `v2.1.x` |
| Product/software minor | keyword 추가, CLI 옵션 추가, table column 추가 | `v2.x.0` |
| Geometry change | amp ordering, section, chip orientation, HDU layout 변경 | `GEOMVER` 갱신 및 ICD major/minor 갱신 |
| Calibration update | 실측 gain/read-noise/crosstalk/telemetry 반영 | calibration version keyword 갱신 |

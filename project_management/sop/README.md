# KMTNet-CEU SOP (Standard Operating Procedure)

최종 갱신일: 2026-09-15 (SOP 목록 갱신)

## 목적

이 폴더는 여러 모듈/현장에 걸쳐 반복 수행되는 주요 작업의 표준 절차(SOP)를 모아 관리한다.
장애 대응이나 안전수칙처럼 이미 `operations/`에 자리잡은 절차는 그대로 두고, 여기에는 "정상 운영 중 반복되는 주요 작업"의 단계별 절차를 담는다.

## 관리 원칙

- 파일명은 `SOP_<작업명>.md` 형식을 따른다 (예: `SOP_MEF_CONVERTER_RUN.md`).
- SOP는 실제 작업 경험이 쌓인 뒤 작성한다. 미완성 초안은 문서 상단에 `[DRAFT]`를 표기한다.
- 현장(SSO/CTIO/SAAO) 작업 중 발견한 절차 개선사항은 해당 SOP에 즉시 반영하고, 개정 이력을 문서 하단에 남긴다 (`sites/README.md`의 Cross-Site 원칙 참조).
- 다른 폴더의 절차성 문서(`operations/RECOVERY_ROLLBACK_PLAN.md`, `operations/SAFETY_HANDLING_PLAN.md` 등)와 내용이 겹치는 경우, 중복 작성하지 않고 상호 참조 링크만 남긴다.

## SOP 목록

| 파일 | 대상 작업 | 상태 |
| --- | --- | --- |
| [`SOP_MEF_CONVERTER_RUN.md`](SOP_MEF_CONVERTER_RUN.md) | Archon MK/NT raw → L0 64-amp MEF 변환 실행 | 확정 (v2.4.0 / PRODVER v2.1.1 기준) |
| [`SOP_SITE_DEPLOYMENT.md`](SOP_SITE_DEPLOYMENT.md) | SSO/CTIO/SAAO 현장 전자부 배포 절차 | **[DRAFT]** — SSO 시행 전 계획 문서 기반, 실제 작업 후 개정 예정 |
| [`SOP_CAMCHAR_CALIBRATION.md`](SOP_CAMCHAR_CALIBRATION.md) | cam_char 카메라 특성 측정(GAIN/RDNOISE/SATURAT/LINMAX) 캠페인 실행 | 확정 (LEGACY 32-amp 캠페인 재현 기준, 명령 실행 검증) |

작성된 SOP가 생기면 위 표에 항목을 추가한다.

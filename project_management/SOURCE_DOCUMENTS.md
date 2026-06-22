# KMTNet-CEU Source Documents

최종 갱신일: 2026-06-22

## 관리 원칙

- 외부에서 받은 PDF, DOCX, 발표/공유본은 `project_management/source_documents/` 아래에 보관한다.
- 동일 문서가 여러 파일명으로 유입되면 SHA256을 비교한 뒤 하나의 관리본만 남긴다.
- 문서에서 추출한 일정, gate, risk, deliverable은 별도 관리 문서에 구조화해서 반영한다.

## 등록 문서

| ID | 파일 | 형식 | 버전 | SHA256 | 상태 |
| --- | --- | --- | --- | --- | --- |
| SRC-001 | `source_documents/KMTNet_CEU_PMP_Final_v1.0.pdf` | PDF | v1.0 | `8ed053f9f3f9a7e572fc876ddf419f930ef47d53a17750985be4457f27d4753f` | Managed |

## SRC-001: KMTNet CEU PMP Final v1.0

원 유입 파일:

- `/Users/leecu/Downloads/TalkFile_KMTNet_CEU_PMP_Final_v1.0.pdf.pdf`

관리 파일:

- `project_management/source_documents/KMTNet_CEU_PMP_Final_v1.0.pdf`

판정:

- Downloads 유입본은 기존 프로젝트 루트의 `KMTNet_CEU_PMP_Final_v1.0.pdf`와 SHA256이 동일했다.
- 중복 파일을 늘리지 않기 위해 기존 Git 관리본을 `project_management/source_documents/` 아래로 이동했다.

내용 요약:

- 공식명칭: KMTNet Wallboard and Camera Electronics Upgrade Project
- 약칭: KMTNet Camera Electronics Upgrade (CEU) Project
- Project Manager: 이충욱
- 대상 사이트: SSO, CTIO, SAAO
- 주요 작업 기간: 2026년 6월 - 2026년 12월
- 핵심 목적: OSU 기반 기존 카메라 전자부를 STA Archon 기반 전자부와 Production Wallboard로 전환해 장기 운영 안정성을 확보
- 적용 전략: 2026년 10월 SSO를 prototype site로 먼저 적용한 뒤, 2026년 11월 CTIO, 2026년 12월 SAAO 순서로 확산
- 핵심 성공조건: Production Wallboard 납품/수락, software demonstration, full rehearsal, SSO 운영 데이터 검토, science verification/acceptance, configuration control

관리 반영:

- 사이트별 일정과 gate는 `SITE_UPGRADE_MILESTONES.md`에 구조화했다.
- 남은 calibration, telemetry, validation 작업은 `BACKLOG.md`에서 추적한다.
- 확정된 product/geometry/software 관리 정책은 `DECISION_LOG.md`에 기록한다.


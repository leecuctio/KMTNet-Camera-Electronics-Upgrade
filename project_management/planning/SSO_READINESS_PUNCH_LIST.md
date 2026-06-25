# KMTNet-CEU SSO 적용 전 진행상태 점검 펀치리스트 (Punch List)

최종 갱신일: 2026-06-25

연계 문서: `schedule/SITE_UPGRADE_MILESTONES.md`, `planning/ACTION_REGISTER.md`, `planning/BACKLOG.md`, `governance/GATE_REVIEW_PLAN.md`, `governance/RISK_REGISTER.md`, `logistics/EQUIPMENT_TRACKER.md`, `operations/COMMUNICATION_PLAN.md`

## 1. 목적과 사용법

SSO(호주) 현장 적용일(2026-10-19) 전까지 **2주 단위**로 프로젝트 진행상태를 점검하기 위한 펀치리스트다.
- 각 체크포인트(CP)마다 **상시 반복 점검 항목**(2절)을 모두 확인하고, 그 시점의 **핵심 게이트 항목**(3절)이 닫혔는지 판단한다.
- 미완료(open) 항목은 4절 펀치리스트 표에 `□`로 남기고, 완료되면 `☑`와 완료일·근거(commit/report)를 기록한다.
- 체크포인트 점검 결과로 새 action이 나오면 `planning/ACTION_REGISTER.md`에 `ACT-XXX`로 등록한다.
- 상태 표기: `□` 미완료 · `◑` 진행중 · `☑` 완료 · `⚠` 리스크/지연

> 이 펀치리스트는 SSO 적용 전까지만 사용한다. CTIO·SAAO 점검은 SSO Operation Review 이후 별도 갱신한다.

## 2. 체크포인트 일정 (2주 단위)

| CP | 점검일 | 점검 시점 핵심 마일스톤 | Owner |
| --- | --- | --- | --- |
| CP-01 | 2026-06-30 | M1 Project Planning Complete, baseline 문서 확정 | 이충욱 |
| CP-02 | 2026-07-14 | M2 HE Box 개조, M3 OSU SW review 진행 점검 | 차상목, 홍성욱 |
| CP-03 | 2026-07-28 | M2/M3 완료, M4 Wallboard 납품·해운 준비 | 차상목, 이용석 |
| CP-04 | 2026-08-11 | M4 Wallboard 납품, **M5 Software Demonstration (Gate 1)**, M6 해운 출고 | 이충욱, 차상목 |
| CP-05 | 2026-08-25 | Gate 1 결과 확인, Full Rehearsal·항공 준비 | 차상목, 홍성욱 |
| CP-06 | 2026-09-08 | M7 항공 출고, **M8 Full Rehearsal (Gate 2)**, Software Freeze 준비 | 전체 |
| CP-07 | 2026-09-22 | M8/M9 완료 확인, **Software Freeze(09-15) 적용**, 장비 현지 도착 | 김동진, 김재우 |
| CP-08 | 2026-10-06 | **M10 Go/No-Go Review**, SSO 출국 최종 점검 | 이충욱 |
| — | 2026-10-19 | **SSO Upgrade 시작** (현장 작업은 `sites/SSO/SITE_PLAN.md`) | 전체 |

## 3. 체크포인트별 핵심 게이트 항목

각 체크포인트에서 아래 항목이 닫혔는지 확인한다. 지연 시 `⚠`로 표기하고 영향과 대응을 5절에 기록한다.

| CP | 닫혀야 하는 핵심 항목 | 판정 기준 |
| --- | --- | --- |
| CP-01 | WBS·RACI·Risk·역할 baseline 확정 | M1 문서 세트 확정 |
| CP-02 | HE Box Archon 3대 장착 구조 확정, OSU review 착수 | ACT-002 진행, M3 착수 |
| CP-03 | HE Box 개조 완료, OSU review 완료, Wallboard 납품 일정 확정 | M2/M3 Done, M4 일정 확정 |
| CP-04 | Wallboard 납품·acceptance, **Gate 1 통과**, 해운 출고 | Bias/Dark/FITS/legacy SW control 성공, 해운 선적 |
| CP-05 | Gate 1 후속조치 종료, Full Rehearsal 준비 완료, 항공 패킹 | rehearsal 선행조건 충족 |
| CP-06 | 항공 출고, **Gate 2(Full Rehearsal) 통과**, freeze 직전 코드 정리 | End-to-End + burn-in 성공 |
| CP-07 | **Software Freeze 적용**, Science Verification 완료, 핵심 장비 현지 도착 | freeze 기록, M9 Done, 화물 도착 확인 |
| CP-08 | **Go/No-Go = Go**, recovery/rollback·SOP·spare 준비 | M10 출국 승인 |

## 4. 펀치리스트 항목 (영역별 상시 점검)

매 체크포인트에서 아래 항목을 점검한다. 완료 시 `☑`와 완료일/근거를 기록한다.

### 4.1 Project Management / Schedule
- □ 마일스톤(M1–M10) 일정 대비 진행 상태가 schedule 문서와 일치
- □ `planning/ACTION_REGISTER.md`의 open action에 지연 항목 없음
- □ Gate 1/2 entry/exit 기준 충족 여부 갱신
- □ 주간 CEU 회의 결정사항이 DECISION_LOG에 반영됨

### 4.2 Hardware (HE Box / Wallboard / PCC)
- □ HE Box Archon 3대 장착 구조 확정 및 개조 완료 (ACT-002)
- □ Production Wallboard 납품·acceptance 완료 (M4)
- □ PCC 운용/교체 판단 및 spare parts inventory 확인
- □ 카메라 탈거·장착 절차(SOP)와 공구·치구 준비

### 4.3 Software / Configuration
- □ OSU Software Review 완료 (M3, Rick review 포함)
- □ Software Demonstration success criteria 확정 (ACT-001) 및 Gate 1 통과 (M5)
- □ CEU repository baseline·freeze 절차 확정 (ACT-004)
- □ Software Freeze(2026-09-15) 적용 및 freeze 이후 변경 통제 확인
- □ Calibration/orientation/crosstalk/telemetry 백로그(KMT-001~004) 진행 상태

### 4.4 Logistics
- □ Master equipment list 분리·확정 (ACT-003)
- □ 해운 출고(M6, 2026-08 초) — 클린부스/PCC/대형품
- □ 항공 출고(M7, 2026-09 초) — Wallboard/Controller/Computer
- □ 통관 및 SSO 현지 화물 도착 확인 (`logistics/EQUIPMENT_TRACKER.md`)

### 4.5 Integration / Science
- □ Full Rehearsal(M8) End-to-End + burn-in 성공, Gate 2 통과
- □ Science Verification(M9) Bias/Dark/Gain/Read Noise/Crosstalk pass/fail 기준 확정 (ACT-005)
- □ 시험관측(관측 프로그램) 절차 준비 — 이상민 주도

### 4.6 Site Readiness (SSO)
- □ SSO pre-site checklist / Day 0 readiness 확정 (ACT-006)
- □ 클린부스·네트워크·전원·작업공간 준비 확인
- □ Recovery/Rollback 및 spare 교체 절차 준비 (`operations/RECOVERY_ROLLBACK_PLAN.md`)
- □ 선발대 구성 및 현장 안전/취급 기준 확인 (`operations/SAFETY_HANDLING_PLAN.md`)

### 4.7 Risk
- □ `governance/RISK_REGISTER.md` 주요 리스크 상태 갱신
- □ Wallboard 납품 지연 / SW migration 지연 / shipping 지연 영향 점검
- □ 신규 리스크 등록 및 완화 조치 책임자 지정

## 5. 점검 기록 (체크포인트별)

각 체크포인트 점검 후 결과를 한 줄로 남긴다.

| CP | 점검일 | 종합 상태 | 지연/이슈 (⚠) | 신규 Action | 점검자 |
| --- | --- | --- | --- | --- | --- |
| CP-01 | 2026-06-30 | | | | |
| CP-02 | 2026-07-14 | | | | |
| CP-03 | 2026-07-28 | | | | |
| CP-04 | 2026-08-11 | | | | |
| CP-05 | 2026-08-25 | | | | |
| CP-06 | 2026-09-08 | | | | |
| CP-07 | 2026-09-22 | | | | |
| CP-08 | 2026-10-06 | | | | |

## 6. 운영 규칙

- 점검은 Weekly CEU Meeting과 별개로, 2주마다 본 펀치리스트 전체를 검토하는 자리에서 수행한다.
- open 항목 중 due가 Gate와 연결된 것은 `governance/GATE_REVIEW_PLAN.md`에도 반영한다.
- 지연(⚠) 항목은 다음 체크포인트까지의 복구 계획과 책임자를 5절 비고에 남긴다.
- Go/No-Go(CP-08)에서 미해결 핵심 게이트 항목이 있으면 SSO 출국을 보류한다.

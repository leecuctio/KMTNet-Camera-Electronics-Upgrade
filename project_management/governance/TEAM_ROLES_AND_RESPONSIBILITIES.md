# KMTNet-CEU Team Roles & Responsibilities

최종 갱신일: 2026-06-23

기준 문서: `documents/source_documents/KMTNet_CEU_PMP_Final_v1.0.pdf`

연계 문서: `governance/RACI.md`, `planning/WBS.md`, `planning/ACTION_REGISTER.md`, `operations/COMMUNICATION_PLAN.md`

## 목적

이 문서는 KMTNet Camera Electronics Upgrade (CEU) 프로젝트에 참여하는 각 연구원의
역할(Role)과 책임(Responsibility)을 명확히 정의한다. `governance/RACI.md`가
work package별 책임 매트릭스를 제공한다면, 이 문서는 **사람 중심**으로
각자의 담당 영역·핵심 책임·의사결정 권한·대리(backup)를 정리해 누가 무엇을
책임지는지 한눈에 알 수 있도록 한다.

> RACI 매트릭스와 이 문서의 내용이 충돌하면, 두 문서를 함께 갱신해 일치시킨다.

## 역할 정의 (Role Definitions)

| 역할 | 설명 |
| --- | --- |
| Project Manager (PM) | 전체 일정·예산·리스크·Gate 승인을 총괄하고 최종 의사결정을 책임진다. |
| Hardware Lead | HE Box 개조, Wallboard/Archon 장착·인수, 예비품 등 하드웨어 준비를 책임진다. |
| Software Lead | OSU 소프트웨어 검토, Archon 인터페이스, FITS 산출물, 관측 스크립트 이관을 책임진다. |
| Network/Configuration Lead | 네트워크 구성, repository baseline, software freeze, 형상 통제를 책임진다. |
| Science Verification Lead | Bias/Dark/Gain/Read Noise/Crosstalk/First Light 검증과 합격 기준을 책임진다. |
| Logistics Lead | 배송 목록, packing, 해운/항공, 통관, 현지 수령을 책임진다. |
| Documentation Lead | SOP, Configuration Manual, site report, Final Report 등 문서 산출물을 책임진다. |
| External Partner | STA, Tom, Rick 등 외부 협력 인력으로 자문·제작·인수에 참여한다. |

## 참여 연구원별 역할과 책임 (Member Roles & Responsibilities)

### 이충욱 — Project Manager (총괄)

- 주 역할: Project Manager / WP1, WP10 Accountable
- 핵심 책임
  - 전체 일정·예산·리스크 총괄 및 주간 CEU 회의 주관
  - Gate 1–4 최종 승인 (`governance/GATE_REVIEW_PLAN.md`)
  - 사이트 전환 전략(SSO → CTIO → SAAO) 결정 및 Go/No-Go 판단
  - 외부 협력기관(STA, 사이트 운영기관) 대외 창구
- 의사결정 권한: 프로젝트 전반 최종 결정권, freeze 이후 변경 승인
- 대리(Backup): 이동주

### 이동주 — Project Management 지원 / Documentation

- 주 역할: WP1 Responsible, WP4·WP10 참여
- 핵심 책임
  - PMP·일정표 유지, action register 및 주간 보고 정리
  - 문서 산출물(SOP, Final Report) 작성 지원
  - 물류 목록·통관 서류 정리 지원
- 의사결정 권한: 문서 관리 기준 제안, PM 부재 시 대리
- 대리(Backup): 홍성욱

### 차상목 — Hardware & Software Lead

- 주 역할: WP2 Hardware / WP3 Software Primary Owner
- 핵심 책임
  - HE Box 개조 및 Archon 장착 구조 확정 (ACT-002)
  - Wallboard 제작/인수 점검 (STA, Tom과 협의)
  - OSU → Archon 소프트웨어 이관 및 Software Demonstration 범위 확정 (ACT-001)
  - **카메라 탈거·장착 작업 주도** (이용석 공동 주도, 이상민 보조)
  - **클린부스 조립 최종 검토** (조립은 이용석·이상민 수행)
  - 현장 설치 및 시험관측 핵심 인력
- 의사결정 권한: 하드웨어·소프트웨어 기술 결정 제안, geometry 변경 시 DECISION_LOG 기록
- 대리(Backup): 홍성욱(SW), 이용석(HW)

### 홍성욱 — Software / Documentation

- 주 역할: WP3 Software Responsible, WP10 Documentation Responsible
- 핵심 책임
  - Archon 인터페이스·FITS 산출물·관측 스크립트 이관 (차상목과 공동)
  - Software Demonstration success criteria 정의 (ACT-001)
  - Configuration Manual 및 software 관련 문서화
  - Full Rehearsal 참여
- 의사결정 권한: 소프트웨어 산출물 기준 제안
- 대리(Backup): 차상목

### 이용석 — Hardware / Logistics

- 주 역할: WP2 Hardware Responsible, WP4 Logistics Primary Owner
- 핵심 책임
  - HE Box 개조 및 예비품 준비 (차상목과 공동, ACT-002)
  - 해운/항공 master equipment list 분리·관리 (ACT-003)
  - **카메라 탈거·장착 작업 주도** (차상목 공동 주도, 이상민 보조)
  - **클린부스(clean booth) 조립 주도** (이상민과 공동, 최종 검토는 차상목)
  - 현장 장비 수령 및 설치 참여
  - SSO pre-site checklist / Day 0 readiness 확정 (ACT-006)
- 의사결정 권한: 물류·하드웨어 준비 일정 제안
- 대리(Backup): 이동주(물류), 차상목(하드웨어)

### 김동진 — Network / Configuration Lead

- 주 역할: WP3 Network/Configuration Responsible
- 핵심 책임
  - 사이트 네트워크 구성 및 연결 검증
  - CEU repository baseline 및 software freeze 절차 확정 (ACT-004)
  - 형상 통제(configuration control) 및 변경 추적
  - SSO pre-site checklist 참여 (ACT-006), Full Rehearsal 참여
- 의사결정 권한: configuration baseline·freeze 기준 제안
- 대리(Backup): 홍성욱

### 이상민 — Test Observation / Software / Site Support

- 주 역할: WP3 Consulted, WP5·WP7 site Responsible, 시험관측 주도
- 핵심 책임
  - **카메라 업그레이드 후 관측 프로그램을 이용한 시험관측 주도 수행**
  - **클린부스(clean booth) 조립 주도** (이용석과 공동, 최종 검토는 차상목)
  - **카메라 탈거·장착 작업 보조** (차상목·이용석 주도, 이상민 보조)
  - 소프트웨어 이관·네트워크 구성 자문
  - SSO pre-site checklist / Day 0 readiness 확정 참여 (ACT-006)
  - Full Rehearsal 및 현장 설치 참여
- 의사결정 권한: 시험관측 수행·판정 제안, 현장 기술 이슈 제안
- 대리(Backup): 김동진

### 김재우 — Science Verification Lead

- 주 역할: WP6 Science Verification Accountable & Responsible
- 핵심 책임
  - Bias/Dark/Gain/Read Noise/Crosstalk/First Light 검증 항목과 pass/fail 기준 확정 (ACT-005)
  - `science/SCIENCE_VERIFICATION_PLAN.md` 및 `science/CALIBRATION_TRACKER.md` 관리
  - 실측 calibration 값 산출 및 L0 product 품질 판정
  - Full Rehearsal Go/No-Go 자료 검토(Consulted)
- 의사결정 권한: science 합격 판정권 (Gate 승인 입력)
- 대리(Backup): 차상목

### 외부 협력 인력 (External Partners)

| 인력/기관 | 역할 | 주요 책임 |
| --- | --- | --- |
| STA | Wallboard 제작·공급사 | Production Wallboard 제작, Archon 컨트롤러 공급, 기술 지원 |
| Tom | STA 측 기술 협력 | Wallboard 제작/인수 자문 (Consulted) |
| Rick | 소프트웨어 자문 | Software Migration 자문 (Consulted) |

## 책임 요약 매트릭스

| 영역 | 1차 책임 | 지원/공동 | 자문 |
| --- | --- | --- | --- |
| Project Management | 이충욱 | 이동주 | 차상목, 홍성욱 |
| Hardware (HE Box/Wallboard) | 차상목, 이용석 | — | 이상민, Tom, STA |
| Software Migration | 차상목, 홍성욱 | — | Rick, 김동진, 이상민 |
| Network/Configuration | 김동진 | — | 홍성욱, 이상민 |
| Logistics | 이용석, 이동주 | — | 차상목 |
| Science Verification | 김재우 | — | 차상목, 홍성욱 |
| 카메라 탈거·장착 | 차상목, 이용석 | 이상민 | Tom, STA |
| 클린부스 조립 | 이용석, 이상민 | — | 차상목(최종 검토) |
| 시험관측 (관측 프로그램) | 이상민 | 차상목, 홍성욱 | 김재우 |
| Documentation | 홍성욱, 이동주 | 이충욱 | 김동진, 차상목 |
| Site Upgrade | 차상목, 이용석, 이상민, 김동진 | — | Tom, STA |

## 운영 규칙

- 담당자가 변경되거나 부재 시 이 문서, `governance/RACI.md`, `planning/ACTION_REGISTER.md`를 함께 갱신한다.
- 각 1차 책임자는 자신의 영역에 해당하는 action item을 `planning/ACTION_REGISTER.md`에서 직접 추적한다.
- Gate 승인 권한과 절차는 `governance/GATE_REVIEW_PLAN.md`를 따른다.
- 회의체별 참여자와 보고 흐름은 `operations/COMMUNICATION_PLAN.md`를 따른다.
- freeze 이후 변경은 `governance/CHANGE_CONTROL.md`에 승인자와 rollback 방법을 남긴다.

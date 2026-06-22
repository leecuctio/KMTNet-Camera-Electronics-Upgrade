# KMTNet-CEU Site Upgrade Milestones

최종 갱신일: 2026-06-22

기준 문서: `documents/source_documents/KMTNet_CEU_PMP_Final_v1.0.pdf`, `KMTNet_CEU_PMP_Final_v1.0.docx`

## 1. 전체 적용 전략

KMTNet CEU는 세 사이트를 한 번에 병렬 전환하지 않고, SSO를 prototype site로 먼저 적용한 뒤 CTIO, SAAO 순서로 확산한다.

| 순서 | 사이트 | 역할 | 목표 일정 | 핵심 판단 |
| --- | --- | --- | --- | --- |
| 1 | SSO | Prototype Site | 2026-10-19 to 2026-10-23 | 첫 현장 적용, 절차 검증, 운영 데이터 확보 |
| 2 | CTIO | Second Site | 2026-11-17 to 2026-11-20 | SSO 교훈 반영 후 반복 적용 |
| 3 | SAAO | Final Site | 2026-12-08 to 2026-12-11 | 최종 사이트 적용 및 프로젝트 closeout 준비 |

핵심 원칙:

- SSO 현장 작업 결과와 최소 1주일 이상의 운영 데이터를 검토한 후 CTIO를 진행한다.
- SSO에서 발견된 문제, 부품 누락, 절차 개선사항은 CTIO 작업 전 SOP에 반영한다.
- CTIO 결과는 SAAO 작업 전 최종 절차 보정에 반영한다.
- Science Acceptance는 기술 동작 확인과 별도로 김재우 주관 데이터 품질 검증을 통과해야 한다.

## 2. Master Milestones

| ID | Milestone | Target | Owner | Gate/Notes |
| --- | --- | --- | --- | --- |
| M1 | Project Planning Complete | 2026-06 | 이충욱 | WBS, 역할, 리스크 초안 확정 |
| M2 | HE Box Modification Complete | 2026-07 | 차상목, 이용석 | Archon 3대 장착 구조 확정 |
| M3 | OSU Software Review Complete | 2026-07 | 차상목, 홍성욱 | Rick review 포함 |
| M4 | Production Wallboard Delivery | 2026-08 | STA, 차상목 | Critical |
| M5 | Software Demonstration | 2026-08 | 차상목, 홍성욱 | Gate 1 |
| M6 | Sea Freight Shipment | 2026-08 초 | 이용석, 이동주 | 클린부스, PCC, 대형품 |
| M7 | Air Freight Shipment | 2026-09 초 | 이용석, 이동주 | Wallboard, Controller, Computer |
| M8 | Full Rehearsal | 2026-09 | 전체 | Gate 2 |
| M9 | Science Verification | 2026-09 | 김재우 | 실험실 데이터 검증 |
| M10 | Go/No-Go Review | 2026-09 말 | 이충욱 | SSO 출국 승인 |
| M11 | SSO Upgrade | 2026-10-19 to 2026-10-23 | 전체 | Prototype Site |
| M12 | SSO Operation Review | 2026-10 말 | 이충욱, 김재우 | CTIO 진행 승인 |
| M13 | CTIO Upgrade | 2026-11-17 to 2026-11-20 | 전체 | SSO 교훈 반영 |
| M14 | SAAO Upgrade | 2026-12-08 to 2026-12-11 | 전체 | 최종 사이트 |
| M15 | Final Acceptance | 2026-12 말 | 이충욱, 김재우 | Gate 4 |

## 3. Gate Criteria

| Gate | Timing | Entry Criteria | Exit Criteria | Decision Authority |
| --- | --- | --- | --- | --- |
| Gate 1 Software Demonstration | 2026-08 중 | Archon/prototype 또는 production electronics 준비 | Bias, Dark, FITS, legacy software control 성공 | 이충욱 |
| Gate 2 Full Rehearsal | 2026-09 | Production Wallboard, release candidate software, HE Box 준비 | Full observatory simulation 및 burn-in 성공 | 이충욱 |
| Gate 3 SSO Acceptance | 2026-10 말 | SSO 설치 완료 | Engineering observation 및 김재우 데이터 품질 승인 | 이충욱, 김재우 |
| Gate 4 Final Acceptance | 2026-12 말 | 3개 사이트 설치 완료 | Science Acceptance 및 문서화 완료 | 이충욱 |

추가 일정 통제:

- Software Freeze Date: 2026-09-15
- Freeze 이후 허용: bug fix, 현장 장애 대응 수정
- Freeze 이후 금지: 신규 기능 추가, architecture 변경, 검증되지 않은 설정 변경

## 4. Site 1: SSO Upgrade

역할: Prototype Site  
목표 일정: 2026-10-19 to 2026-10-23

### 선행 조건

| 구분 | 완료 기준 |
| --- | --- |
| Production Wallboard | 납품 및 acceptance 완료 |
| Software Demonstration | Bias, Dark, FITS, legacy SW control 성공 |
| Full Rehearsal | End-to-End operation 및 burn-in 성공 |
| Logistics | 핵심 장비 현지 도착 확인 |
| Recovery Plan | rollback 및 spare 교체 절차 준비 |
| Science Verification | 김재우 사전 검토 완료 |
| Site Preparation | 화물 도착, 통관, 작업공간, 클린부스, 네트워크, 전원 확인 |

### 현장 작업 마일스톤

| Day | Task | Owner | Acceptance |
| --- | --- | --- | --- |
| D-1 / Day 0 | 선발대 현장 확인, 클린부스/네트워크/작업공간 준비 | 이용석, 김동진, 이상민 | 작업 가능 상태 확인 |
| Day 1 | 카메라 탈거 및 작업공간 이동 | 차상목, 이용석, 이상민 | 카메라 안전 탈거 |
| Day 2 | 카메라 분해 및 Wallboard 교체 | 차상목, STA, Tom | 전자부 체결 및 1차 검사 |
| Day 3 | 재조립, 진공 형성, PCC 교체 또는 기존 PCC 유지 판단 | 차상목, 이상민 | 진공 및 냉각 안정화 |
| Day 4 | Readout test, engineering observation, site acceptance | 전체, 김재우 원격/현장 검토 | SSO Acceptance |

### SSO 완료 조건

- Bias, Dark, FITS 생성이 정상 동작한다.
- Multi-controller readout 및 data transfer가 정상이다.
- 진공, 냉각, PCC 운용이 안정적이다.
- Engineering observation과 science review를 통과한다.
- 작업 기록, 사진 기록, configuration log, site report가 남는다.
- SSO 운영 데이터 검토 결과 CTIO 진행이 승인된다.

## 5. Site 2: CTIO Upgrade

역할: Second Site  
목표 일정: 2026-11-17 to 2026-11-20

### 선행 조건

| 구분 | 완료 기준 |
| --- | --- |
| SSO Acceptance | SSO engineering/science acceptance 완료 |
| SSO Operation Review | 최소 1주일 이상의 운영 데이터 검토 완료 |
| SOP Update | SSO에서 확인된 문제와 개선사항 반영 |
| Parts/Tools Review | SSO에서 확인된 누락 품목, spare, cable, tool 보완 |
| Configuration Baseline | CTIO 적용 전 software/configuration baseline 고정 |
| Logistics | CTIO 현장 화물 도착, 통관, 작업공간, 네트워크 확인 |

### 현장 작업 마일스톤

| Phase | Task | Acceptance |
| --- | --- | --- |
| Pre-site | 화물, 작업공간, 클린부스, 네트워크, 전원 확인 | 작업 가능 상태 확인 |
| Day 1 | 카메라 탈거 및 작업공간 이동 | 카메라 안전 탈거 |
| Day 2 | 카메라 분해 및 Wallboard 교체 | 전자부 체결 및 1차 검사 |
| Day 3 | 재조립, 진공 형성, PCC 운용 판단 | 진공 및 냉각 안정화 |
| Day 4 | Readout test, engineering observation, site acceptance | CTIO Acceptance |

### CTIO 완료 조건

- SSO에서 갱신한 SOP가 현장에서 문제 없이 적용된다.
- Bias, Dark, FITS, readout, data transfer가 정상 동작한다.
- CTIO site-specific metadata, controller ID/SN/FW, network/configuration 기록이 남는다.
- Science Verification에서 다음 사이트 진행에 문제가 없다고 판단한다.
- SAAO 작업 전 최종 절차 보정 사항이 정리된다.

## 6. Site 3: SAAO Upgrade

역할: Final Site  
목표 일정: 2026-12-08 to 2026-12-11

### 선행 조건

| 구분 | 완료 기준 |
| --- | --- |
| CTIO Acceptance | CTIO engineering/science acceptance 완료 |
| SOP Final Update | SSO/CTIO 교훈 반영 완료 |
| Final Parts Check | 남은 site 적용에 필요한 spare, cable, tool 확인 |
| Configuration Baseline | SAAO 적용 전 software/configuration baseline 고정 |
| Logistics | SAAO 현장 화물 도착, 통관, 작업공간, 네트워크 확인 |

### 현장 작업 마일스톤

| Phase | Task | Acceptance |
| --- | --- | --- |
| Pre-site | 화물, 작업공간, 클린부스, 네트워크, 전원 확인 | 작업 가능 상태 확인 |
| Day 1 | 카메라 탈거 및 작업공간 이동 | 카메라 안전 탈거 |
| Day 2 | 카메라 분해 및 Wallboard 교체 | 전자부 체결 및 1차 검사 |
| Day 3 | 재조립, 진공 형성, PCC 운용 판단 | 진공 및 냉각 안정화 |
| Day 4 | Readout test, engineering observation, site acceptance | SAAO Acceptance |

### SAAO 완료 조건

- 세 번째 사이트 적용이 완료되고, 동일 운영 기준으로 안정 동작한다.
- Bias, Dark, FITS, readout, data transfer가 정상 동작한다.
- SAAO site-specific metadata, controller ID/SN/FW, network/configuration 기록이 남는다.
- Science Acceptance 및 closeout 문서화에 필요한 최종 데이터가 확보된다.

## 7. Cross-Site Deliverables

| Group | Deliverables |
| --- | --- |
| Project Management | PMP, WBS, Gantt Chart, Risk Register, RACI Matrix |
| Hardware | Production Wallboard, Wallboard Acceptance Report, HE Box Verification, PCC Inventory, Spare Parts Inventory |
| Software | OSU Software Review, Architecture Document, Archon Interface Software, Software Demonstration Report, Release Package |
| Logistics | Master Equipment List, Shipping List, Packing List, Sea/Air Freight Verification, Site Delivery Record |
| Integration | Hardware/Software/Network Integration Reports, CCD Readout Verification, Burn-in Report, Full Rehearsal Report |
| Science | Bias/Dark/Gain/Read Noise/Crosstalk Reports, Engineering Observation Report, Science Acceptance Report |
| Site | SSO/CTIO/SAAO Work Plan, Work Log, Photo Archive, Configuration Log, Acceptance Test Report, Upgrade Report |
| Closeout | Camera Upgrade SOP, Removal SOP, Reassembly SOP, Vacuum SOP, Archon Configuration Manual, Maintenance Manual, Final Report |

## 8. 주요 리스크와 사이트 진행 영향

| Risk | 영향 | 사이트 진행 통제 |
| --- | --- | --- |
| Production Wallboard 납품 지연 | SSO 일정 직접 지연 | Gate 1/2 재조정 |
| Software Migration 지연 | Bias/Dark/FITS 및 remote operation 불가 | 2026-08 software demonstration 통과 전 SSO 진행 금지 |
| Full Rehearsal 실패 | 현장 시행착오 증가 | Gate 2 통과 전 출국 승인 금지 |
| Shipping/Customs 지연 | 장비 현지 도착 실패 | 해운 2026-08 초, 항공 2026-09 초 출고 및 최소 2주 여유 확보 |
| 진공/냉각 문제 | 현장 acceptance 실패 | O-ring/seal, leak test, PCC fallback 준비 |
| Configuration 혼선 | 사이트별 동작 차이 및 rollback 어려움 | 단일 repository, baseline, software freeze 적용 |
| 과학 데이터 품질 미달 | 다음 사이트 진행 불가 | rehearsal와 각 site acceptance에서 조기 검증 |

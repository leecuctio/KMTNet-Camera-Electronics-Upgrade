[DRAFT] SOP: 현장 배포 (신규 전자부 사이트 적용)

최종 갱신일: 2026-09-16

> **[DRAFT]**: SSO 현장 적용(2026-10-19~11-01)이 아직 시작되지 않은 시점에 계획 문서(`SITE_PLAN.md`, `SITE_UPGRADE_MILESTONES.md` 등) 기준으로 작성했다. SSO 실제 작업 후 절차 순서/소요/문제점을 반영해 초안 표기를 해제한다.

## 목적

신규 전자부(Production Wallboard, Archon Controller, HE Box 등)를 SSO → CTIO → SAAO 순서로 현장에 적용하는 표준 절차를 정의한다. 사이트별 캘린더 일자는 다르지만, 아래 단계 순서·게이트·문서화 요구사항은 세 사이트에 공통 적용한다.

이 SOP는 **오케스트레이션 문서**다 — 각 단계의 상세 체크리스트/기준은 기존 관리 문서를 그대로 따르고, 여기서는 중복 작성하지 않고 링크만 남긴다. 세부 절차가 SOP 본문과 다르면 링크된 원본 문서가 우선한다.

## 적용 대상 사이트

| 순서 | 사이트 | 역할 | 목표 일정 | 사이트별 세부계획 |
| --- | --- | --- | --- | --- |
| 1 | SSO | Prototype Site | 2026-10-19 ~ 11-01 | [`sites/SSO/SITE_PLAN.md`](../sites/SSO/SITE_PLAN.md) |
| 2 | CTIO | Second Site | 2026-11-11 ~ 11-26 | [`sites/CTIO/SITE_PLAN.md`](../sites/CTIO/SITE_PLAN.md) |
| 3 | SAAO | Final Site | 2026-12-06 ~ 12-21 | [`sites/SAAO/SITE_PLAN.md`](../sites/SAAO/SITE_PLAN.md) |

전체 순서/근거는 [`schedule/SITE_UPGRADE_MILESTONES.md`](../schedule/SITE_UPGRADE_MILESTONES.md) 1절 참조. SSO는 기능시험 기반 acceptance이며, 신규 전자부의 첫 온스카이 확인은 CTIO에서 수행한다(SSO 온스카이 commissioning은 2027-02 별도 진행).

## 사전조건 (출국 전)

- [ ] Gate 1 Software Demonstration 통과 — Bias/Dark/FITS/legacy SW control 성공
- [ ] Gate 2 Full Rehearsal 통과 — full observatory simulation/burn-in 성공 (게이트 기준: [`governance/GATE_REVIEW_PLAN.md`](../governance/GATE_REVIEW_PLAN.md))
- [ ] Software Freeze 이후 baseline 확정, freeze 이후 금지 변경사항 없음 확인 ([`configuration/SOFTWARE_FREEZE.md`](../configuration/SOFTWARE_FREEZE.md), [`configuration/CONFIGURATION_CONTROL.md`](../configuration/CONFIGURATION_CONTROL.md))
- [ ] 핵심 장비(Production Wallboard, Archon Controller, Control Computer 등) 현지 도착 확인, 최소 2주 여유 ([`logistics/EQUIPMENT_TRACKER.md`](../logistics/EQUIPMENT_TRACKER.md), [`logistics/LOGISTICS_PLAN.md`](../logistics/LOGISTICS_PLAN.md))
- [ ] Recovery/Rollback plan 준비 완료 ([`operations/RECOVERY_ROLLBACK_PLAN.md`](../operations/RECOVERY_ROLLBACK_PLAN.md))
- [ ] Science Verification 사전 검토 완료 (Science Verification Lead) ([`science/SCIENCE_VERIFICATION_PLAN.md`](../science/SCIENCE_VERIFICATION_PLAN.md))
- [ ] 화물 도착, 통관, 작업공간, 클린부스, 네트워크, 전원 준비 확인 (사이트별 SITE_PLAN.md 선행 조건 항목)
- [ ] (2번째 사이트부터) 직전 사이트 acceptance 완료 + 직전 사이트에서 나온 SOP/부품 개선사항이 본 문서와 장비 목록에 반영됨 ([`sites/README.md`](../sites/README.md) Cross-Site 원칙)
- [ ] Go/No-Go Review 통과 (출국 승인, Project Manager)

## 절차

### 1. 현지 도착 및 site readiness 확인

- 화물 도착/통관/작업공간/클린부스/네트워크/전원을 현장에서 재확인한다.
- 매일 작업 시작 전 안전 브리핑 및 안전 체크리스트를 수행한다 ([`operations/SAFETY_HANDLING_PLAN.md`](../operations/SAFETY_HANDLING_PLAN.md)).
- 당일자 Work Log를 시작한다 ([`templates/SITE_WORK_LOG_TEMPLATE.md`](../templates/SITE_WORK_LOG_TEMPLATE.md)).

### 2. 카메라 및 HE Box 제거

- 중량물 취급 절차와 ESD 대응을 적용한다.
- SSO(첫 사이트)는 작업 기간 중 망원경 밸런스 유지를 위해 더미 HE박스를 장착한다. CTIO/SAAO는 사이트별 SITE_PLAN.md의 해당 절차를 따른다.

### 3. Wallboard 교체 / 진공 펌핑 / 냉각 시작

- 핵심 작업. 진공 작업 전 O-ring/flange/feedthrough 상태를 확인한다.
- 듀어 진공 해제(Venting)·재조립 후 펌핑(Pump-down)의 상세 절차, 부품/Spare 목록, 체크리스트는 [`SOP_DEWAR_VACUUM_VENTING_PUMPING.md`](SOP_DEWAR_VACUUM_VENTING_PUMPING.md)를 그대로 따른다.
- 문제 발생 시 Recovery Level 2(Wallboard/cable) 또는 Level 3(진공/냉각)을 적용한다 ([`operations/RECOVERY_ROLLBACK_PLAN.md`](../operations/RECOVERY_ROLLBACK_PLAN.md)).

### 4. HE Box 컨트롤러 재구성 + 제어 컴퓨터 셋업

- 냉각 진행과 병행 가능. 네트워크/제어 컴퓨터 설정은 Configuration Owner 승인 기준을 따른다.

### 5. ICS 사이트 설정 배포 및 정체 확인 — 필수 게이트

- **자료를 한 장이라도 찍기 전에** [`operations/ICS_DEPLOYMENT_CHECKLIST.md`](../operations/ICS_DEPLOYMENT_CHECKLIST.md) 절차를 그대로 수행한다: `[node] observatory` 한 줄만 변경 → 기동 → 정체 배너(사이트/TELESCOP/FPAID/좌표/관측일 경계/파일명 예시/backend/EXPNUM) 전 항목 확인.
- 경고(모르는 observatory 값, 백엔드-사이트 불일치, TELID 불일치 등)가 뜨면 원인을 해소하기 전까지 다음 단계(자료 취득)로 진행하지 않는다.
- 이 단계를 건너뛰면 잘못된 사이트 코드/좌표/관측일 경계가 자료에 영구히 박힐 수 있다 (해당 문서 참조).

### 6. 영상확인 및 1차 튜닝

- Bias, Dark, FITS 생성이 정상 동작하는지 확인한다.
- Multi-controller readout 및 data transfer가 정상인지 확인한다.

### 7. 시험관측 / 캘리브레이션

- Gain/Read Noise/Crosstalk 등 항목별로 Science Verification Lead의 검토를 받는다 ([`science/SCIENCE_VERIFICATION_PLAN.md`](../science/SCIENCE_VERIFICATION_PLAN.md) Verification Matrix).
- CTIO/SAAO는 온스카이 시험관측을 포함한다 — 박수와 순서는 사이트별 SITE_PLAN.md를 따른다(CTIO 5박, SAAO 5박; 날씨 여유 확보 목적). SSO는 온스카이 없이 기능시험까지만 수행한다.

### 8. Acceptance 판정 (Gate)

- 현장 시험관측 결과 기반 GO/NOGO와 Science Acceptance(Science Verification Lead)를 함께 결정한다. 판정 기준과 승인권자는 [`governance/GATE_REVIEW_PLAN.md`](../governance/GATE_REVIEW_PLAN.md)의 해당 Gate(SSO=Gate 3, CTIO/SAAO는 사이트별 acceptance 절차)를 따른다.
- CTIO/SAAO에서 영상이 비정상 판정이면 출발 일정을 연장하고 문제를 해결한 뒤 재판정한다(사이트별 SITE_PLAN.md 참조). 정상 판정 전에는 철수하지 않는다.
- 비정상 상황이 장비 손상 위험/일정 지연/과학관측 영향이 큰 수준이면 Recovery Level 4(현장 적용 실패)를 검토한다.

### 9. 마무리 작업

- (해당 시) 더미 HE박스를 실제 HE박스로 교체한다.
- 카메라를 최종 보관 상태로 두고 냉각기를 off한다.
- 철수 전 현장 정리 및 최종 점검을 수행한다.

### 10. 기록 / 문서화

- [ ] Work Log, Photo Archive 완료 ([`templates/SITE_WORK_LOG_TEMPLATE.md`](../templates/SITE_WORK_LOG_TEMPLATE.md))
- [ ] Site Configuration Log 갱신 ([`configuration/CONFIGURATION_CONTROL.md`](../configuration/CONFIGURATION_CONTROL.md) Site Configuration Log)
- [ ] Incident 발생 시 Incident Log 갱신 ([`operations/RECOVERY_ROLLBACK_PLAN.md`](../operations/RECOVERY_ROLLBACK_PLAN.md))
- [ ] Site Acceptance 기록 갱신 ([`science/SCIENCE_VERIFICATION_PLAN.md`](../science/SCIENCE_VERIFICATION_PLAN.md) Site Acceptance 기록)
- [ ] Gate Decision Record 갱신 ([`governance/GATE_REVIEW_PLAN.md`](../governance/GATE_REVIEW_PLAN.md) Decision Record)
- [ ] Site Report 작성

### 11. 다음 사이트 반영

- 이번 사이트에서 발견한 문제, 누락 품목, 절차 개선사항을 정리해 다음 사이트 출발 전 아래에 반영한다:
  - 본 SOP(개정 이력에 기록)
  - [`logistics/EQUIPMENT_TRACKER.md`](../logistics/EQUIPMENT_TRACKER.md) / [`logistics/LOGISTICS_PLAN.md`](../logistics/LOGISTICS_PLAN.md) 보완 품목
  - 다음 사이트 SITE_PLAN.md 선행 조건
- Cross-Site 원칙: SSO 교훈 → CTIO 반영, CTIO 교훈 → SAAO 최종 절차 보정 ([`sites/README.md`](../sites/README.md)).

## 역할 (1차 책임 기준)

세부 역할·대리자는 [`governance/TEAM_ROLES_AND_RESPONSIBILITIES.md`](../governance/TEAM_ROLES_AND_RESPONSIBILITIES.md) 참조.

| 단계/영역 | 1차 책임 |
| --- | --- |
| 전체 총괄, Gate 승인, GO/NOGO | Project Manager (이충욱) |
| 카메라 탈거·장착, Wallboard/HE Box 교체 실무 | 차상목, 이용석 (실무 공동: 이상민) |
| 클린부스 조립 | 이용석, 이상민 (최종 검토: 차상목) |
| 네트워크/ICS 설정, configuration baseline | 김동진 |
| 시험관측(관측 프로그램) 수행 | 이상민 |
| Science Verification / Acceptance 판정 | Science Verification Lead (김재우) |
| 물류(배송/통관/현지 수령) | 이용석, 이동주 |
| 문서화(Work Log, Site Report 등) | 홍성욱, 이동주 |

## 관련 문서

| 영역 | 문서 |
| --- | --- |
| 전체 일정/마일스톤 | `../schedule/SITE_UPGRADE_MILESTONES.md` |
| 사이트별 세부 계획 | `../sites/SSO/SITE_PLAN.md`, `../sites/CTIO/SITE_PLAN.md`, `../sites/SAAO/SITE_PLAN.md` |
| ICS 배포/사이트 정체 확인 | `../operations/ICS_DEPLOYMENT_CHECKLIST.md` |
| 안전/취급 | `../operations/SAFETY_HANDLING_PLAN.md` |
| Recovery/Rollback | `../operations/RECOVERY_ROLLBACK_PLAN.md` |
| Gate 기준 | `../governance/GATE_REVIEW_PLAN.md` |
| Configuration/Freeze | `../configuration/CONFIGURATION_CONTROL.md`, `../configuration/SOFTWARE_FREEZE.md` |
| Science Verification | `../science/SCIENCE_VERIFICATION_PLAN.md` |
| 물류 | `../logistics/LOGISTICS_PLAN.md`, `../logistics/EQUIPMENT_TRACKER.md` |
| Work Log 템플릿 | `../templates/SITE_WORK_LOG_TEMPLATE.md` |
| 역할/책임 | `../governance/TEAM_ROLES_AND_RESPONSIBILITIES.md` |

## 개정 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-09-15 | 최초 작성. SSO 출국 전 계획(SITE_PLAN.md, SITE_UPGRADE_MILESTONES.md) 및 관련 운영 문서를 기준으로 3사이트 공통 절차 정리 |
| 2026-09-15 | CTIO/SAAO 출장 일정 변경 반영: CTIO 출발 하루 앞당김(11-12→11-11)·온스카이 4박→5박, SAAO 온스카이 3박→4박·복귀 하루 연장(12-20→12-21) |
| 2026-09-15 | 3단계에 `SOP_DEWAR_VACUUM_VENTING_PUMPING.md` 링크 추가 (Dewar 진공 해제/펌핑 상세 절차 신설) |
| 2026-09-16 | SAAO 온스카이 4박→5박 재정의 반영(마지막 온스카이일에 마무리·판정 결합, CTIO와 동일 구성) |

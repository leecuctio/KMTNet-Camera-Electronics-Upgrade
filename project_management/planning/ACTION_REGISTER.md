# KMTNet-CEU Action Register

최종 갱신일: 2026-08-28

상태 값: `Open`, `In Progress`, `Blocked`, `Done`, `Dropped`

| ID | 등록일 | 영역 | Action | Owner | Due | 상태 | Next Check |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ACT-001 | 2026-06-22 | Software | 2026-08 Software Demonstration 범위와 demo success criteria 확정 | 차상목, 홍성욱 | 2026-08 | Open | Weekly CEU Meeting |
| ACT-002 | 2026-06-22 | Hardware | HE Box Archon 3대 장착 구조와 개조 완료 기준 확정 | 차상목, 이용석 | 2026-07 | Done | 2026-07-22 완료 — 장착 구조 확정 및 개조용 부품 가공 완료 |
| ACT-003 | 2026-06-22 | Logistics | 해운/항공 품목을 master equipment list로 분리 | 이용석, 이동주 | 2026-07 | In Progress | **2026-08-23 해운분 물품 본원 → 배송업체 인계 완료** (M6). 항공분(2026-09 초 출고) 목록·출고 준비 잔여 |
| ACT-004 | 2026-06-22 | Configuration | CEU repository baseline과 freeze 절차 확정 | 김동진 | 2026-09-15 | Open | Configuration review |
| ACT-005 | 2026-06-22 | Science | Bias/Dark/Gain/Read Noise/Crosstalk 검증 데이터와 pass/fail 기준 확정 | 김재우 | 2026-09 | Open | Science review |
| ACT-006 | 2026-06-22 | Site | SSO pre-site checklist와 Day 0 readiness 기준 확정 | 이용석, 김동진, 이상민 | 2026-10 | Open | Go/No-Go Review |
| ACT-007 | 2026-08-13 | Site | SSO Wallboard 교체 전문가 Tom O'Brien 방문용역 협의·계약 | 이충욱 | 2026-09 | In Progress | 일정(10-18~11-01)·지원조건(항공/일비/자문료) 제안 발송, Tom 검토·회신 대기 중 — **2026-08-23 기준 협의 계속**. 서면 자문은 Greg 참여 확정으로 보완 (TEAM_ROLES 외부 협력 표) |
| ACT-008 | 2026-08-13 | Software | **pctcs 의 `FITS_TELID` 를 AUX 하드웨어에서 받아오도록 개선 요청** — 현재는 `pctcs.ini` 수동 설정이고 기본값이 사이트가 아닌 `KMTN`(`pctcs.h:115`)이라, ICS 가 사이트 정체를 교차검증할 때 독립적 근거가 되지 못한다. pctcs 자기 주석이 원래 의도를 적어 두었다(`loadconfig.c:177` *"this info will be get from AUX"*) | 이충욱 | 미정 | Open | ICS 쪽은 이것에 의존하지 않도록 구현됐다(D-015) — 개선되면 경고의 신뢰도가 올라갈 뿐이다 |
| ACT-009 | 2026-08-13 | Configuration | **신규 CEU 망의 사이트별 IP 대역을 문서로 확정** — 저장소에 CEU 망 문서가 없다. ⚠️ **ICS 쪽 결합은 없어졌다 (2026-08-24)**: 사이트 자동 판정(D-015)이 폐지되고 `[node] observatory` 한 줄이 정본이 되면서 `siteid.py` 를 지웠다. 대역이 바뀌어도 **자료의 사이트 정체는 이제 영향받지 않는다.** 망 문서 자체의 필요(배선·방화벽·노드 주소)는 남으므로 항목은 유지한다 | 김동진, 차상목 | 2026-09-15 | Open | ~~`ics_sim/ics_sim/siteid.py` `SITE_SUBNETS`~~ (파일 폐지). 현행 사이트 판별은 `operations/ICS_DEPLOYMENT_CHECKLIST.md` 와 DECISION_LOG **D-017** · DevNote 11.27 |
| ACT-011 | 2026-08-13 | Software | **raw ↔ MEF 키워드 대응표 검토** (289행 전수) — Archon setup·구성·유닛 텔레메트리 카드의 **이름과 카드 구성**을 확정한다. `__reference/` 는 MEF 목적지(표 컬럼)를 전부 정의하지만 raw 쪽 카드 이름은 하나도 정의하지 않아, 취득 SW 가 일방적으로 정한 상태다. 실기가 이 이름으로 자료를 쌓은 뒤 다른 이름이 채택되면 **그때까지의 아카이브가 영구히 읽히지 않는다**. 잔여 미결 4건은 통합 문서 §6 | 차상목, 이충욱 | 2026-09 | Open | `raw_fits_spec/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.14.md` — **판정 원장**: 0장 준거 순위·판정 구간 + 3~9장 카드별 판정(레거시 123개 전량 귀속) + 각 장 `Use in MEF` 열(구 전수 대응표 289행) · `raw_fits_spec/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.6.md` §6 — MEF/converter 쪽 미결 4건. 확정 후 규격 5장에 반영. ※ 구 검토 문서(키워드맵 v0.7)는 흡수 완료로 폐기(운영자 재가 2026-08-22) |
| ACT-010 | 2026-08-13 | Site | **Day 0 배포 체크리스트에 ICS 사이트 정체 확인을 포함** (ACT-006 하위) — `operations/ICS_DEPLOYMENT_CHECKLIST.md` 신설했다. 기동 배너의 사이트·좌표·관측일 경계·`DATASRC` 를 확인하는 절차다 | 이상민, 차상목 | 2026-10 | Open | ACT-006 의 Day 0 readiness 기준에 이 문서를 참조로 넣는다 |
| ACT-012 | 2026-08-28 | Site | **카메라 현지 재설치 리허설 결과 검토 종합 회의 (2026-09-01)** — 리허설 과정에서 도출된 수정사항과 준비사항을 전 팀원이 검토·확정한다. 결과는 SOP·pre-site checklist(ACT-006)·장비 보완 목록에 반영하고, Gate 2(Full Rehearsal) 판정의 입력으로 쓴다 | 이충욱 (주관), 전체 | 2026-09-01 | Open | 회의 결과의 액션은 즉시 ACT-XXX 로 등재, 결정사항은 DECISION_LOG 에 기록 |

## 사용 규칙

- 회의 중 새 작업이 나오면 즉시 `ACT-XXX`로 추가한다.
- 완료된 항목은 결과 문서나 commit hash가 있으면 `Next Check` 칸에 기록한다.
- due date가 gate와 연결된 항목은 `governance/GATE_REVIEW_PLAN.md`에도 반영한다.


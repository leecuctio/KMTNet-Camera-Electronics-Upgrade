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
| ACT-008 | 2026-08-13 | Software | **FITS 헤더에 들어갈 망원경(TCS) 쪽 키워드를 믿을 수 있는 곳에서 받아오게 하기** — 기존 TCS 프로그램(pctcs)은 이 값을 설정 파일에 손으로 적어 두는 방식이라, 카메라 제어(ICS)가 "지금 어느 사이트인가"를 이중으로 확인할 때 근거로 쓰기 어려웠다 | 이상민 | 2026-08 | Done | **2026-08 말 완료** — 이상민이 개발한 **TCS 시뮬레이터**가 FITS 헤더용 키워드의 공급원 역할을 하므로 목적 달성. (참고: ICS 자체는 애초에 이 값에 의존하지 않게 만들어져 있어, 이 개선은 확인 기능의 신뢰도를 높이는 효과) |
| ACT-009 | 2026-08-13 | Configuration | **사이트별 네트워크 IP 대역을 문서로 확정** — 현재는 기존 대역(192.168.13/14/15)을 그대로 쓴다는 구두 확인뿐, 문서가 없다. ⚠️ **관측 자료의 사이트 정체는 이제 여기에 걸려 있지 않다 (2026-08-24 변경)** — ICS 가 IP 로 사이트를 자동 판정하던 방식(D-015)을 **D-020** 이 대체해 **설정 한 줄(`[node] observatory`)이 정본**이 되면서, 대역이 바뀌어도 자료 이름은 영향받지 않는다. 남는 필요는 **배선·방화벽·노드 주소**를 확정하는 망 문서 자체다 | 김동진, 차상목 | 2026-09-15 | Open | ~~`ics_sim/ics_sim/siteid.py` `SITE_SUBNETS`~~ (파일 폐지). 현행 사이트 판별은 `operations/ICS_DEPLOYMENT_CHECKLIST.md` · DECISION_LOG **D-020**(D-015 대체)/**D-017** · DevNote 11.27 |
| ACT-011 | 2026-08-13 | Software | **raw 영상의 FITS 헤더 키워드 이름 확정** — raw(취득 원본)와 MEF(가공본)의 키워드가 똑같을 필요는 없다. **이미 정의되어 있는 MEF 키워드가 가공 후에도 그대로 유지되도록, 영상 획득 소프트웨어가 키워드 이름을 MEF 기준에 맞춰 쓰면 된다.** 이 방향은 **2026-08-25 회의에서 확정**되었고, 남은 일은 차상목이 취득 코드에 적용하는 것뿐이다 | 차상목 | 2026-09 | In Progress | **방향 확정(08-25), 코드 적용 잔여** — SW freeze(09-15) 전 적용 확인. 키워드별 상세 판정 기록은 `raw_fits_spec/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.16.md`(판정 원장) 참조 |
| ACT-010 | 2026-08-13 | Site | **Day 0 배포 체크리스트에 ICS 사이트 정체 확인을 포함** (ACT-006 하위) — `operations/ICS_DEPLOYMENT_CHECKLIST.md` 신설했다. 기동 배너의 사이트·좌표·관측일 경계·`DATASRC` 를 확인하는 절차다 | 이상민, 차상목 | 2026-10 | Open | ACT-006 의 Day 0 readiness 기준에 이 문서를 참조로 넣는다 |
| ACT-012 | 2026-08-28 | Site | **카메라 현지 재설치 리허설 결과 검토 종합 회의 (2026-09-01)** — 리허설 과정에서 도출된 수정사항과 준비사항을 전 팀원이 검토·확정한다. 결과는 SOP·pre-site checklist(ACT-006)·장비 보완 목록에 반영하고, Gate 2(Full Rehearsal) 판정의 입력으로 쓴다 | 이충욱 (주관), 전체 | 2026-09-01 | Open | **아젠다 확정: `../meetings/AGENDA_2026-09-01_COMPREHENSIVE_REVIEW.md`** (4시간, 파트별 발표 + 미해결 항목 종합). 회의 결과의 액션은 즉시 ACT-XXX 로 등재, 결정사항은 DECISION_LOG 에 기록 |

## 사용 규칙

- 회의 중 새 작업이 나오면 즉시 `ACT-XXX`로 추가한다.
- 완료된 항목은 결과 문서나 commit hash가 있으면 `Next Check` 칸에 기록한다.
- due date가 gate와 연결된 항목은 `governance/GATE_REVIEW_PLAN.md`에도 반영한다.


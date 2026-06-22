# KMTNet-CEU Documentation Plan

최종 갱신일: 2026-06-22

## QA 기록 원칙

- 작업 전 카메라, HE Box, 케이블, PCC 배관, 전산실 상태를 사진으로 기록한다.
- 작업 중 모든 케이블 연결, 제거 부품, 교체 부품, configuration 변경을 기록한다.
- 작업 후 Bias, Dark, Flat, Engineering Image, First Light 데이터를 기준으로 site report를 작성한다.
- SSO 작업 기록은 CTIO 및 SAAO의 표준절차서 초안으로 사용한다.

## 필수 문서 산출물

| Group | Deliverables | 관리 위치 |
| --- | --- | --- |
| Project Management | PMP, WBS, Gantt Chart, Risk Register, RACI Matrix | `planning/`, `governance/` |
| Hardware | Wallboard Acceptance Report, HE Box Verification, PCC Inventory, Spare Parts Inventory | `logistics/`, `sites/` |
| Software | OSU Software Review, Architecture Document, Archon Interface Software, Software Demonstration Report, Release Package | `configuration/`, `release/` |
| Logistics | Master Equipment List, Shipping List, Packing List, Sea/Air Freight Verification, Site Delivery Record | `logistics/` |
| Integration | Hardware/Software/Network Integration Reports, CCD Readout Verification, Burn-in Report, Full Rehearsal Report | `governance/`, `science/` |
| Science | Bias/Dark/Gain/Read Noise/Crosstalk Reports, Engineering Observation Report, Science Acceptance Report | `science/` |
| Site | SSO/CTIO/SAAO Work Plan, Work Log, Photo Archive, Configuration Log, Acceptance Test Report, Upgrade Report | `sites/` |
| Closeout | Camera Upgrade SOP, Removal SOP, Reassembly SOP, Vacuum SOP, Archon Configuration Manual, Maintenance Manual, Final Report | `documents/` |

## 파일명 규칙

- 날짜가 필요한 기록: `YYYYMMDD_site_topic.md`
- Site report: `SSO_SITE_REPORT_YYYYMMDD.md`
- Gate review: `GATE1_SOFTWARE_DEMO_YYYYMMDD.md`
- 외부 원본문서: `documents/source_documents/`에 원본명을 최대한 유지


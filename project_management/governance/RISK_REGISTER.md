# KMTNet-CEU Risk Register

최종 갱신일: 2026-06-22

상태 값: `Open`, `Monitoring`, `Mitigated`, `Closed`

| ID | Risk | Probability | Impact | Owner | Mitigation | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Production Wallboard 납품 지연 | M | H | 차상목 | STA 주간 확인, 일정 지연 시 즉시 Gate 재조정 | Open |
| R2 | Software Migration 지연 | H | H | 차상목, 홍성욱 | 2026-08 Software Demonstration, Rick 협의 | Open |
| R3 | Full Rehearsal 실패 | M | H | 전체 | 실제 현장과 동일한 Full Observatory Simulation 수행 | Open |
| R4 | Shipping/Customs 지연 | M | H | 이용석, 이동주 | 해운 2026-08 초, 항공 2026-09 초 출고, 통관 추적 | Open |
| R5 | 진공 형성 실패 | L-M | H | 차상목 | 예비 O-ring/seal, leak test procedure 확보 | Open |
| R6 | 핵심 인력 부재 | M | M-H | 이충욱 | 차상목 backup 이상민, SW backup 홍성욱 | Open |
| R7 | PCC 배송 지연 | M | L-M | 이용석 | 동일 제품 사용, 기존 PCC fallback 운용 | Open |
| R8 | Configuration 혼선 | M | H | 김동진 | Repository, baseline, software freeze 적용 | Open |
| R9 | 현장 작업공간/네트워크 준비 미흡 | M | M | 김동진, 이용석 | 선발대 사전 확인 | Open |
| R10 | 과학 데이터 품질 미달 | L-M | H | 김재우 | Rehearsal 단계에서 조기 검증 | Open |

## Gate 연결

- R1, R2, R3, R4는 Gate 1/2와 SSO Go/No-Go에 직접 연결된다.
- R8은 Software Freeze와 모든 site acceptance에 영향을 준다.
- R10은 SSO Acceptance와 CTIO/SAAO 진행 승인 조건이다.


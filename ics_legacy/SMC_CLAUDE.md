# SMC_CLAUDE.md

`ics_legacy/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md) 참고.

## 진행 중인 작업: 레거시 ICS/ISIS 조사 → 신규 Python ICS 개발

**목표**: 기존(legacy) ICS/ISIS 카메라 제어 시스템을 문서화하고, 이를 바탕으로 신규 Python 기반 ICS를 새로 개발한다.

**현재 상태 (2026-07-21 기준)**
- 이 폴더(`ics_legacy/`)에 레거시 시스템 원본 자료(프로토콜 스펙, 명령어 문서, ISIS 클라이언트 라이브러리 문서, 실측 로그 샘플)와 분석 보고서를 정리해 둠.
- **핵심 산출물**: [ics_legacy_report.md](ics_legacy_report.md) — 아키텍처, IMPv2.5 프로토콜, ICS/IC 명령어 레퍼런스, 실제 로그 기반 트랜잭션 분석, 에러/경고 패턴을 정리한 보고서. **레거시 시스템을 파악할 때는 원본 문서를 다시 파기 전에 이 보고서부터 읽을 것.**
- 신규 Python ICS 구현은 **아직 시작 전** — 보고서 작성(조사)까지만 완료된 상태.

**핵심 아키텍처 요약** (자세한 근거는 보고서 참고)
- 대상: KMTNet(칠레 CTIO / 남아공 SAAO / 호주 SSO) 배포본. 사이트별 모자이크 카메라 = 과학채널 K/M/T/N(K=master) + 가이드채널 G.
- 통신 허브: 스펙상 명칭 **ISIS**, 실제 런타임에서는 **XIS**로 동작.
- 프로토콜: **IMPv2.5** — 텍스트 기반, `src>dest Message_Type Command_Word Message_Body\r` 포맷, `REQ:/EXEC:/DONE:/STATUS:/ERROR:/WARNING:/FATAL:` 7종 메시지 타입, `key=value` 파라미터.
- 노드 디렉토리: `ICS`(카메라 통합제어) / `{K,M,T,N,G}.IC`(채널별 제어) / `{K,M,T,N,G}.CB`(채널별 디스크·전송 컨트롤러) / `TC`(망원경 제어) / `OBS`(관측 콘솔) / `ICG`(가이드용 ICS) / `ABC`(가이드용 자동관측 제어기) / `GMON`(상태 모니터링).
- 알려진 캐비어트: ICS 6자리 vs 채널 4자리 EXPNUM 불일치(→ `INITIALIZE`로 우회), `BIN/ROI/DISPL/STOP/ABORT/MOVIE`는 명령어만 있고 미구현.

**참고 원본 자료 위치 (git 미포함, 로컬 전용 — 다른 컴퓨터에서 clone하면 없음)**
- `__sample_isislog/` (이 폴더 바로 아래) — 3개 사이트 ISIS 로그 샘플 (저장소 `.gitignore`의 `*.log` 규칙으로 git 미추적, 이 컴퓨터 로컬에만 존재)
- `../../__localonly_isislogs/` — 이 저장소 **바깥**(`CEU/` 폴더 직속, 저장소의 상위 디렉토리)에 있는 전체 원본 로그 아카이브. 참고용으로만 로컬 보관, git과 무관.
- 위 두 로그 자료가 필요한데 다른 컴퓨터에 없다면, 원본 보관 위치(로그를 추출해온 소스)에서 다시 받아와야 함 — git clone만으로는 로그 원본이 따라오지 않는다.

## 다음에 이어서 할 만한 일
- `ics_legacy_report.md`를 계속 보완 (원본 소스코드 `ISISclient.zip`/`pctcs.zip` 분석 등, 아직 미검토)
- 신규 Python ICS 설계/구현 착수

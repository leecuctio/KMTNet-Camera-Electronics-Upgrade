# SMC_CLAUDE.md

`ics_legacy/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md) 참고.

## 진행 중인 작업: 레거시 ICS/ISIS 조사 → 신규 Python ICS 개발

**목표**: 기존(legacy) ICS/ISIS 카메라 제어 시스템을 문서화하고, 이를 바탕으로 신규 Python 기반 ICS를 새로 개발한다.

**현재 상태 (2026-07-28 기준)**
- 이 폴더(`ics_legacy/`)의 자료(프로토콜 스펙, 명령어 문서, ISIS 클라이언트 라이브러리 문서, 1998년 원조 ICIMACS 논문, 실측 로그 샘플, 원본 소스코드)를 **전부 검토 완료**하고 분석 보고서로 정리해 둠. 조사 단계는 사실상 마무리된 상태.
- **핵심 산출물**: [ics_legacy_report.md](ics_legacy_report.md) — 아키텍처(1998년 기원 포함), IMPv2.5 프로토콜, ICS/IC 명령어 레퍼런스, 실제 로그 기반 트랜잭션 분석(BLG 과학노출·자동가이딩 포함), 에러/경고 패턴, 레퍼런스 C 클라이언트 라이브러리(`ISISclient.zip`/`pctcs.zip`/`dispatcher.cpp`) 소스 분석을 정리한 보고서. **레거시 시스템을 파악할 때는 원본 문서를 다시 파기 전에 이 보고서부터 읽을 것.**
- 신규 Python ICS 구현은 **아직 시작 전**.
- 참고: `CCD status (20220826.emaitoSET).pdf`는 2026-07-28에 사용자가 이 폴더에서 제거함(ICS 범주 밖으로 판단, 다른 곳으로 이동) — 폴더에 없어도 정상 상태.

**핵심 아키텍처 요약** (자세한 근거는 보고서 참고)
- 대상: KMTNet(칠레 CTIO / 남아공 SAAO / 호주 SSO) 배포본. 사이트별 카메라 = 과학 CCD 4개(K/M/T/N, 각각 별도 `.IC`/`.CB` 노드, K=master, CCD당 리드아웃 채널 8개) + 가이드 CCD 4개(전부 `G.IC` 노드 하나가 통합 제어, CCD당 리드아웃 채널 2개). 이 리드아웃 채널 수는 legacy 시스템 기준이며, 신규 Archon 업그레이드 스펙(../README.md)과는 별개.
- 통신 허브: 스펙상 명칭 **ISIS**, 실제 런타임에서는 **XIS**로 동작.
- 프로토콜: **IMPv2.5** — 텍스트 기반, `src>dest Message_Type Command_Word Message_Body\r` 포맷, `REQ:/EXEC:/DONE:/STATUS:/ERROR:/WARNING:/FATAL:` 7종 메시지 타입, `key=value` 파라미터. **전송 계층은 UDP**(connectionless, `sendto`/`recvfrom`) — 노드 등록이 "최신 연결이 이전 것을 대체"하는 방식으로 동작하는 근본 원인.
- 노드 디렉토리: `ICS`(카메라 통합제어) / `{K,M,T,N,G}.IC`(디바이스별 제어) / `{K,M,T,N,G}.CB`(디바이스별 디스크·전송 컨트롤러) / `TC`(망원경 제어) / `OBS`(관측 콘솔) / `ICG`(가이드용 ICS) / `ABC`(가이드용 자동관측 제어기) / `GMON`(상태 모니터링).
- 알려진 캐비어트: ICS 6자리 vs CCD 4자리 EXPNUM 불일치(→ `INITIALIZE`로 우회), `BIN/ROI/DISPL/STOP/ABORT/MOVIE`는 명령어만 있고 미구현. 메시지 타입/커맨드 워드는 대소문자 무관 매칭, `REQ:`는 관례상 리터럴로 안 보냄.

**참고 원본 자료 위치 (git 미포함, 로컬 전용 — 다른 컴퓨터에서 clone하면 없음)**
- `__sample_isislog/` (이 폴더 바로 아래) — 3개 사이트 XIS(ISIS) 런타임 로그 샘플 (저장소 `.gitignore`의 `*.log` 규칙으로 git 미추적, 이 컴퓨터 로컬에만 존재). **ICS는 자체 로그가 없으므로 ICS 동작을 보려면 이 XIS 로그를 봐야 함.** `KMTNx.yyyymmdd.nnnnnn.fits`는 ICS가 획득한 실제 관측 영상 파일이지 로그가 아님(실물 파일은 이 저장소에 없음).
- `../../__localonly_isislogs/` — 이 저장소 **바깥**(`CEU/` 폴더 직속, 저장소의 상위 디렉토리)에 있는 전체 원본 로그 아카이브. 참고용으로만 로컬 보관, git과 무관.
- 위 두 로그 자료가 필요한데 다른 컴퓨터에 없다면, 원본 보관 위치(로그를 추출해온 소스)에서 다시 받아와야 함 — git clone만으로는 로그 원본이 따라오지 않는다.

## 다음에 이어서 할 만한 일
- 신규 Python ICS 설계/구현 착수 (조사는 이제 충분히 완료된 상태)

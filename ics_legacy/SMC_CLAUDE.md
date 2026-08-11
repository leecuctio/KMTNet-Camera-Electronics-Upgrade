# SMC_CLAUDE.md

`ics_legacy/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md) 참고.

## 큰 그림: 레거시 3부작 중 하나

KMTNet 레거시 관측 소프트웨어를 세 폴더로 나눠 각각 분석해 두었다. 세 프로그램은 **같은 ICIMACS 시스템의 서로 다른 조각**이므로, 하나를 파악할 때 나머지도 함께 참조하는 것이 좋다.

| 폴더 | 프로그램 | ICIMACS 노드 | 역할 |
|---|---|---|---|
| **`ics_legacy/`** (이 폴더) | ICS / ICG / ISIS(XIS) | `ICS`, `ICG`, `XIS`, `*.IC`, `*.CB` | 카메라 통합제어(과학+가이드) + 메시지 허브 + 프로토콜 |
| [`../TCSAgent/`](../TCSAgent/SMC_CLAUDE.md) | TCS Agent (`pctcs`) | `TC` | 망원경/부속장치 제어 브리지 |
| [`../OBSAgent/`](../OBSAgent/SMC_CLAUDE.md) | OBS Agent (`obstool`) | `OBS` | 관측자 CLI + 스크립트 자동관측 |

이 폴더는 **시스템의 토대**(프로토콜·허브·카메라)를 다루므로, 셋 중 **먼저 읽어야 할 문서**다. 이 폴더 안에는 보고서가 **2종**(전체 시스템용 + ICG 전용) 있다 — 아래 참고.

## 진행 중인 작업: 레거시 조사 → 신규 Python ICS 개발

**목표**: 기존(legacy) ICS/ISIS 카메라 제어 시스템을 문서화하고, 이를 바탕으로 신규 Python 기반 ICS를 새로 개발한다.

**현재 상태 (2026-07-29 기준)**
- 이 폴더의 자료(프로토콜 스펙, 명령어 문서, ISIS 클라이언트 라이브러리 문서, 1998년 원조 ICIMACS 논문, 실측 로그 샘플, 원본 소스코드, 배경 논문/포스터까지)를 **전부 검토 완료**하고 분석 보고서로 정리해 둠. 마지막까지 미검토로 남아있던 `spie3.pdf`(OSU ISL 연구소 소개)와 `P-atwood-poster.pdf`(MODS CCD 포스터)도 2026-07-29에 검토·색인 마감 — 조사 단계는 완전히 종료.
- **핵심 산출물 (2종)**: **레거시 시스템을 파악할 때는 원본 문서를 다시 파기 전에 이 보고서들부터 읽을 것.**
  - [ics_legacy_report.md](ics_legacy_report.md) — 시스템 전체. 1절 개요(1998년 ICIMACS 기원) · 2절 IMPv2.5 프로토콜 · 3절 ICS/IC 명령어 · 4절 실측 트랜잭션(DARK, BLG 과학노출+가이딩, GMON) · 5절 에러 패턴 · 6절 자료 색인 · 7절 C 클라이언트 라이브러리 소스 분석 · **8절 신규 Python 구현(8.0절에 확정 구조)**
  - [icg_legacy_report.md](icg_legacy_report.md) — **`ICG` 노드 전용 기술 레퍼런스**(2026-07-29 신규 작성). ICG는 자체 문서·소스가 없어 **XIS 로그 실측이 유일한 근거**다. 가이드 노출 오케스트레이션, `G.IC`/`G.CB` 디스크 계층, ICS와의 상세 비교(7절), 신규 `icg` 구현 명세(9절).
- 신규 Python ICS 구현은 **아직 시작 전** (설계 방향은 아래 확정).

## 신규 Python 시스템 구조 (2026-07-29 사용자 확정)

레거시의 다수 노드를 **두 개의 Python 프로그램으로 통합**한다:

| 신규 프로그램 | 흡수하는 레거시 노드 | 노드 수 |
|---|---|---|
| **`ics`** (과학) | `ICS` + `K/M/T/N.IC`(4) + `K/M/T/N.CB`(4) | 9 |
| **`icg`** (가이드) | `ICG` + `G.IC` + `G.CB` | 3 |

- 두 프로그램은 **분리 유지**(제어 주체·타이밍·명령 세트가 다름 — icg 보고서 7절에 근거 정리). 단 **공통 로직은 공유 라이브러리로** 뺄 것(IMPv2 노드, TC 질의·FITS 헤더 중계, SYNCHRONIZE, 디스크 이중버퍼) — 레거시도 동일 코드베이스(`KX` 빌드)로 추정되므로 원 구조에도 부합.
- **구현 순서 권고**: 단순한 `icg`(단일 IC/CB, 동기화 문제 없음)를 먼저 만들어 골격 검증 → `ics`로 확장.
- **OBSAgent는 개정하지 않는다 (확정)**. 통합 `ics`가 내부적으로 4개 CCD를 한 프로그램에서 다루더라도, **바깥으로는 기존과 동일하게 CCD별 메시지("Acquisition Complete." 4회 등)를 그대로 발신**해 OBSAgent의 `CamStatus`가 무개정으로 동작하게 한다. 지켜야 할 정확한 발신 규약은 [ics_legacy_report.md](ics_legacy_report.md) **8.0.1절**에 표로 정리돼 있다(소스 실측 기반).
  - 핵심: 발신 노드 ID는 `ICS`/`{K,M,T,N}.IC`/`{K,M,T,N}.CB` 중 하나여야 필터를 통과(통합 노드가 전부 `ICS` 이름으로 보내도 OK) · `Acquisition Complete.`(마침표 포함)와 `Wrote`는 **각 4회** 필요 · 파일명 `KMTN<CCD>.<yyyymmdd>.<nnnnnn>.fits` 형식이 `FitsNum` 파싱에 물려 있음 · `READY`는 메시지가 아니라 **`IDLE_3` 후 12.2초 타이머**로 전이(소스에 `Disk Write Complete` 파서 없음 — 문서/주석과 실제 구현이 어긋나는 지점).
  - **비대칭 주의**: OBSAgent는 `ICG`/`G.IC`/`G.CB` 발신 메시지를 명시적으로 무시(v0.3.2~)하므로 **신규 `icg`는 이 하위호환 부담이 전혀 없다** — 메시지 형식을 자유롭게 현대화 가능.
- 미결정 사항: 계통 간 `SYNCHRONIZE` 채널 존치 여부, 디스크 이중화(DISK0/DISK1) 존치 여부, 가이드 파일명 규칙 통일 여부, ABC 존치 여부.

## 핵심 아키텍처 요약 (자세한 근거는 보고서 참고)

- 대상: KMTNet(칠레 CTIO / 남아공 SAAO / 호주 SSO) 배포본. 사이트별 카메라 = 과학 CCD 4개(K/M/T/N, 각각 별도 `.IC`/`.CB` 노드, K=master, CCD당 리드아웃 채널 8개) + 가이드 CCD 4개(전부 `G.IC` 노드 하나가 통합 제어, CCD당 리드아웃 채널 2개). 이 리드아웃 채널 수는 legacy 기준이며, 신규 Archon 업그레이드 스펙([../README.md](../README.md))과는 별개.
- 통신 허브: 스펙상 명칭 **ISIS**, 실제 런타임에서는 **XIS**로 동작.
- 프로토콜: **IMPv2.5** — 텍스트 기반, `src>dest Message_Type Command_Word Message_Body\r` 포맷, `REQ:/EXEC:/DONE:/STATUS:/ERROR:/WARNING:/FATAL:` 7종 메시지 타입, `key=value` 파라미터. **전송 계층은 UDP**(connectionless, `sendto`/`recvfrom`) — 노드 등록이 "최신 연결이 이전 것을 대체"하는 방식으로 동작하는 근본 원인.
- 노드 디렉토리: `ICS`(카메라 통합제어) / `{K,M,T,N,G}.IC`(디바이스별 제어) / `{K,M,T,N,G}.CB`(디바이스별 디스크·전송 컨트롤러) / `TC`(망원경 제어 → [TCSAgent](../TCSAgent/SMC_CLAUDE.md)) / `OBS`(관측 콘솔 → [OBSAgent](../OBSAgent/SMC_CLAUDE.md)) / `ICG`(가이드용 ICS) / `ABC`(가이드용 자동관측 제어기) / `GMON`(상태 모니터링 — UDP로 OBS 노드에 `sysstatus`를 초당 질의하고, OBSAgent의 `GetSysStatus()` 응답 문자열을 받는 방식. 같은 정보가 `/data/Logs/ObsStatus.txt` 파일로도 5초마다 기록됨, [OBSAgent 보고서](../OBSAgent/obsagent_report.md) 7절 참고).
- 알려진 캐비어트: ICS 6자리 vs CCD 4자리 EXPNUM 불일치(→ `INITIALIZE`로 우회), `BIN/ROI/DISPL/STOP/ABORT/MOVIE`는 명령어만 있고 미구현. 메시지 타입/커맨드 워드는 대소문자 무관 매칭, `REQ:`는 관례상 리터럴로 안 보냄.

## 자료 위치와 git 상태

- **이 폴더의 문서·소스는 git에 커밋·push 완료** — 다른 컴퓨터에서 clone하면 그대로 따라온다. (반면 `../TCSAgent/`, `../OBSAgent/`는 **아직 커밋 전**이라 clone에 포함되지 않는다.)
- **`__sample_isislog/samples_for_bug.txt` 는 예외적으로 커밋한다** — 사용자가 직접 추린 메시지 오염 사례 2,755행이고, `.txt` 라 `*.log` 규칙에 걸리지 않는다. `ics_legacy_report.md` 5.6절의 근거이며, 여기서 파생한 테스트 픽스처가 `../ics_sim/tests/fixtures/bug_patterns.txt` 에 있다.
- **로그 자료는 git 미포함, 로컬 전용**:
  - `__sample_isislog/` (이 폴더 바로 아래) — 3개 사이트 XIS(ISIS) 런타임 로그 샘플. 저장소 `.gitignore`의 `*.log` 규칙으로 git 미추적, 이 컴퓨터 로컬에만 존재. **ICS는 자체 로그가 없으므로 ICS 동작을 보려면 이 XIS 로그를 봐야 한다.**
  - `../../__localonly_isislogs/` — 저장소 **바깥**(`CEU/` 폴더 직속)에 있는 전체 원본 로그 아카이브. 참고용 로컬 보관, git과 무관.
  - 다른 컴퓨터에 이 로그가 필요하면 원본 보관 위치에서 다시 받아와야 한다 — clone만으로는 따라오지 않는다.
- `KMTNx.yyyymmdd.nnnnnn.fits`는 ICS가 획득한 **실제 관측 영상 파일**이지 로그가 아니다(실물은 이 저장소에 없고, 로그 안에 파일명만 기록됨).
- `CCD status (20220826.emaitoSET).pdf`는 2026-07-28에 이 폴더에서 제거되어 [`../OBSAgent/`](../OBSAgent/)로 이동함(ICS 범주 밖으로 판단) — 이 폴더에 없어도 정상.

## 진행 상황 갱신 (2026-08-03) — 신규 `ics` 착수, 시뮬레이터 완성

**조사 단계는 끝났고 구현이 시작됐다.** 결과물은 [`../ics_sim/`](../ics_sim/) 이다.

- 신규 `ics` 의 **첫 실행 산출물**로 레거시 호환 시뮬레이터를 만들었다. 전체 노출 사이클(DARK/BIAS/OBJECT), `GO n` 다중 노출, 전 명령 디스패치, 텔레메트리 중계가 동작하고 **테스트 107개가 통과**한다.
- 다음 단계는 `ics_sim/hardware/archon.py` 에 실제 CCD 구동 코드를 넣는 것이다. 시퀀서·명령 처리부·메시지 규약은 **무개정**으로 간다.
- **[`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 가 신규 개발의 중심 문서**다. 사양·판단 근거·조사 이력·정정 이력·백로그가 전부 들어 있다.

이 과정에서 **로그 아카이브 전량**(`__localonly_isislogs/`, 48GB, 1,113일분)을 스캔해 이 폴더의 보고서를 보강·정정했다:

| 갱신 | 위치 |
|---|---|
| **ICS 메시지 오염 버그** — 커맨드워드 슬롯이 비워지지 않는 문제. 이번 조사 최대 발견 | `ics_legacy_report.md` **5.6절 신설** |
| **`GO n` 다중 노출 시퀀스** — 샘플엔 0건이었다 | 〃 **3.5절 신설** |
| **OBSAgent 규약 6개 항목 추가** — `ExpNum` 자동 질의, 수신 9노드, 타임아웃 4종, `Wrote` 중계 경로, 텔레메트리 역순, 상태 전이 실측 | 〃 **8.0.1절 보강** |
| **정정: 디스크는 이중이 아니라 최대 4중** (그리고 신규에선 폐지) | 〃 1.4·4.2절 |
| `CHA`/`C1` 노드, AUXSTATUS 사이트별 차이, 새 에러·경고, 형식 변형 | 〃 1.3·5.2·5.3·5.4절 |
| 가이드 계통에 적용되는 결론 (디스크 폐지, 오염 방지 규칙, 제약 비대칭) | `icg_legacy_report.md` **9.5절 신설** |
| `ExpNum` 왕복의 목적과 내력, 상태 전이 정정, `GO n` 경로 | `../OBSAgent/obsagent_report.md` **6.1절 신설** · 7절 보강 |

스캔 도구는 [`../ics_sim/tools/scan_legacy_logs.py`](../ics_sim/tools/scan_legacy_logs.py) 에 남아 있어 로그가 있는 컴퓨터에서 재검증할 수 있다.

## 로그 아카이브가 판정 도구로 쓰였다 (2026-08-11)

실물 연동 시험에서 신규 `ics` 의 `ExpNum` 응답 값이 한 칸 밀리는 것이 드러났는데, **우리 버그인지 OBSAgent 의 오래된 표시 버그인지** 가릴 수단이 없었다. 48GB 아카이브가 갈랐다 — CTIO `isis.20250401.log` 에서 `DONE: EXPNUM` 응답과 **같은 노출의 `Wrote` 파일명**을 대조하니 연속 3 사이클 모두 응답이 한 칸 앞섰다(레거시는 N+1). 우리 쪽 결함으로 확정.

> **이 폴더 자료의 쓰임새가 하나 늘었다.** 지금까지 아카이브는 *"레거시가 무엇을 했는가"* 를 알아내는 데 썼는데, 이번엔 **신규 구현과 레거시 중 어느 쪽이 틀렸는지 판정**하는 데 썼다. 규약을 로그에서 뽑을 때 **메시지의 존재만 보고 값의 의미를 안 보면** 같은 함정이 반복된다 — 경위는 [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 12.14.

대조 방법(다른 항목에도 그대로 쓸 수 있다):

```bash
grep -aE "DONE: EXPNUM|Wrote LASTFILE" isis.2025MMDD.log | head -20
```

## 다음에 이어서 할 만한 일

- ~~**실제 OBSAgent 연동 시험**~~ — **1차 완료 (2026-08-11).** XIS 허브에 `ics_sim`·실물 TCSAgent·실물 OBSAgent 를 함께 물려 노출 사이클 전 구간을 통과시켰다. **8.0.1절 규약이 실물에서 처음 검증됐고**, 빠져 있던 항목 하나(`ExpNum` 값)를 그 자리에서 찾았다. `.osc` 스크립트 관측은 아직 — 결과는 [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 3.7.
- **`ics_sim/hardware/archon.py` 구현** — 실제 CCD 구동. 계약과 참고 자산은 [DevNote 9장](../ics_sim/DevNote.md).
- **신규 `icg` 착수** — 명세는 [icg_legacy_report.md](icg_legacy_report.md) 9절(+2026-08-03에 추가된 9.5절). `ics_sim` 의 공통 로직(IMPv2 노드, 텔레메트리 중계, 메시지 위생 규칙, 설정 체계)을 그대로 가져다 쓸 수 있다.
- 선행 결정 필요: SYNCHRONIZE 존치 여부, 가이드 파일명 규칙, ABC 존치 여부. (**디스크 이중화는 폐지로 확정**됐다 — 1.4절)
- 주변 시스템 설계 인풋: [../TCSAgent/tcsagent_report.md](../TCSAgent/tcsagent_report.md) 11절(망원경 인터페이스, `copt` 스펙화) · [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md) 11절(상태머신, `.osc` 파서, Redis 상태버스).

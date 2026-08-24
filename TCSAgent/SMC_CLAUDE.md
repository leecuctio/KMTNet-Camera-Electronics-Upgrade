# SMC_CLAUDE.md

`TCSAgent/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md) 참고.

## 이 폴더가 다루는 것: TCS Agent (레거시 망원경 제어 인터페이스)

**TCS Agent**(실행파일 `pctcs`, ICIMACS 노드명 **`TC`**)는 카메라 시스템(ICIMACS)과 망원경 제어 시스템(TCS) 사이를 잇는 브리지 프로그램이다. OSU의 원조 `pctcs Agent v3.3.1`(Yale 1m/ANDICAM용)을 KASI가 KMTNet에 맞게 개조한 것으로, 개발/유지보수는 차상목(chasm@kasi.re.kr).

**현재 상태 (2026-07-29 기준)**
- 이 폴더의 자료(공식 매뉴얼 R4.0, v1.7.2 소스코드, 설정/데이터 파일, 버전 이력, **`__reference/`의 저수준 프로토콜 규격 3종까지**)를 **검토 완료**하고 분석 보고서로 정리해 둠.
- **핵심 산출물**: [tcsagent_report.md](tcsagent_report.md) — 시스템 구조, 원본 대비 KMTNet 개조 내역, 설치/빌드, 런타임 설정, 전체 명령어 레퍼런스, **매뉴얼에 없는 실제 기능**(아래 참고), 버전 이력, 신규 구현 시 고려사항. **이 소프트웨어를 파악할 때는 원본 PDF/소스를 다시 파기 전에 이 보고서부터 읽을 것.**
- 분석 대상 버전: **v1.7.2** (`TCSAgent.latest/KMTNet/pctcs.h`의 `APP_VER` 기준)

## 핵심 사실 요약 (자세한 근거는 보고서 참고)

- **구조**: TCP 클라이언트 2개 + UDP 노드 1개를 한 프로세스가 겸한다.
  - ICIMACS 쪽 ← **UDP/IMPv2** → 노드 `TC` (포트 6606)
  - 망원경 마운트 쪽 ← **TCP** → `Telcom`(포트 5750, PC-TCS의 시리얼을 네트워크로 중계하는 별도 프로그램)
  - 부속장치 쪽 ← **TCP** → `AUX` 제어 SW(포트 5752, 필터/셔터/포커서/돔셔터/거울냉각/환경센서)
- **원본 대비 최대 변경점**: 원본은 PC-TCS와 RS-232 시리얼 직결이었으나, KMTNet판은 이를 Telcom TCP + AUX TCP 2개 링크로 교체하고 자동 재연결(ArcMode)·링크 상태 관리를 신설했다.
- **TCS 링크와 AUX 링크는 독립적으로 상태 관리**된다 (`UP`/`IDLE`/`DOWN`, 각각 다른 타임아웃 기준).
- **카메라 셔터는 이 프로그램이 제어하지 않는다** — ICS가 HE box를 통해 TTL 신호로 직접 여닫고, TCS Agent/AUX는 그 상태를 모니터링만 한다(Full/Half 2중 블레이드, 개폐 각 5초 — AUX 규격 문서로 상세 확인, 보고서 9.2절). 운영상 매우 중요한 구분.
- **사이트별 설정 파일 매핑 확정**(ini 헤더 근거): `kmtnc`=CTIO, `kmtns`=SAAO, `kmtna`=SSO(Australia), `kmtnt`=**TestBed**(실관측소 아님). `.sta.ini` 변형 = Standalone 모드용(ID `TC.STA`, 포트 5755).
- **운영 배치**: Guide server(ICGui)에서 `tcstart`로 실행(관측 후에도 켜둠). 배포는 `scr/tcupdate`가 개발 트리(`/home/kasi/TCSAgent/`)→런타임(`/home/dts/`)으로 복사하며, 사이트별 cortable을 `offset_blg.table` 고정 이름으로 배포한다. 이 저장소 스냅샷은 `sysid="kmtnt"`(TestBed) 상태.

## 가장 중요한 발견: 공식 매뉴얼이 실제 기능을 다 담고 있지 않다

공식 매뉴얼 **R4.0(2020-11-10)의 명령어 표는 실제 v1.7.2 소스와 어긋난다.** 아래 명령들은 실제로 동작하지만 R3/R4 어디에도 문서화돼 있지 않다:

`catalog`(`cat`) · `tmradec`(`tmr`) · `tmobject`(`tmo`) · `tmelaz`(`tme`) · `tstow`(`stow`) · `oo` · `cc` · `concise` · `tick`(경과시간 측정) · `treq`(PCTCS-NG REQUEST 조회 — `tcmd`의 COMMAND와 대비)

(주의: `dtiltp`/`fttgotop`은 소스에 함수는 있으나 **명령 테이블에서 주석 처리되어 비활성** — 동작하는 명령 목록에 넣으면 안 됨. 보고서 9절 정정 참고.)

특히 **`copt` 포인팅 보정 옵션**(`tmradec`/`tmobject`의 3번째 인자)이 문서화 공백의 핵심이다:
- `1` = **BLG 보정** — 목적지 시각각(HA)을 계산해 사이트별 보정 테이블(`cortable/offset_{ctio,saao,sso}.table.<날짜>`)로 마운트의 비선형 지향 오차를 보정. KMTNet Bulge 서베이 관측이 실제로 이 경로를 탄다.
- `k`/`m`/`t`/`n` = 모자이크 중심 대신 **특정 CCD를 시야 중심에** 오게 하는 오프셋 (CCD 간격 상수: RA 63′, Dec 66′)
- 이 보정의 기준점이 버전에 따라 N→K→C(모자이크 중심)로 재정의돼 왔다(v1.6.7~1.6.9) — **현재 정본은 소스코드뿐이다.**

## 폴더 구성과 자료 상태

| 항목 | 내용 | 검토 |
|---|---|---|
| `KMTNet TCS Agent R4.0.pdf` | 공식 매뉴얼 최신판(40p, 상세) | 완료 — 보고서의 주 근거 |
| `KMTNet TCS Agent R3.pdf` | 구판 매뉴얼 | 미검토(R4.0으로 대체) |
| `TCSAgent.latest/KMTNet/` | v1.7.2 소스 + `ini`/`catalog`/`cortable`/`scr` | 완료(핵심 함수 확인) |
| `TCSAgent.latest/UpdateNotes.v1.7.2.txt` | v1.5.2~v1.7.2 버전 이력 | 완료 |
| `__reference/PCTCS Communications.pdf`, `TelcomDoc.pdf`, `KMTNet AUX control remote commands(...).pdf` | PC-TCS/Telcom/AUX 저수준 프로토콜 원본 규격 | **검토 완료(2026-07-29)** — 보고서 9.2절에 요약 (PCTCS-NG 패킷, 150자 텔레메트리, AUX 서브시스템 6종·응답 규약) |
| `__reference/PC_TCS_version_6.pdf` | 상용 PC-TCS v6 자체 매뉴얼 | 미검토 — 마운트 제어 내부까지 팔 때만 필요 |
| `__reference/ISISclient/`, `__reference/hiredis/` | 빌드 의존 라이브러리 사본 (ISISclient는 OBSAgent 쪽과 **동일 파일** 확인) | ISISclient는 [../ics_legacy/ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 7절에서 이미 분석 완료 |
| `TCSAgent.v1.7.2.zip` | 배포 압축본 (`.gitignore`의 `*.zip`로 git 미추적) | 미압축, `.latest`와 동일 추정 |

**git 상태**: 커밋되어 있다 — **136 파일 추적 중**(2026-08-11 확인). *"아직 커밋되지 않았다"* 던 2026-07-29 자 서술은 낡은 것이라 정정했다. `*.zip`(배포본)은 `.gitignore` 로 제외된다. `__reference/ISISclient/libisis.a` 는 커밋돼 있지만 **2014년 non-PIC 빌드라 요즘 리눅스에서는 링크되지 않는다** — 소스에서 재빌드해야 한다([tcsagent_report.md](tcsagent_report.md) 12.1 ④).

## 재빌드와 실행 (2026-08-11 실측)

**[`build-local.sh`](build-local.sh)** 한 줄이면 된다. 저장소를 건드리지 않고 `~/AIC` 아래 작업 사본에서 빌드하고 설정까지 만든다.

```bash
./build-local.sh --site kmtna        # kmtna=SSO kmtnc=CTIO kmtns=SAAO kmtnt=TestBed
~/AIC/build/TCSAgent/pctcs ~/AIC/Config/pctcs.ini
```

Ubuntu 24.04 / g++ 13.3.0 에서 실제로 빌드해 `ics_sim`·XIS 와 연동까지 확인했다. **원 배포본(2014~2018, CentOS 계열)과 12년치 툴체인 차이로 그냥은 안 넘어가는 것이 여섯 가지 있고**, 그중 하나(`rl_refresh_line()` 을 readline 초기화 전에 호출)는 **빌드는 되고 실행이 즉사하는** 부류다. 전부 [tcsagent_report.md](tcsagent_report.md) **12절**에 정리했고 스크립트가 처리한다.

### 설치 자리를 옮겨도 재빌드는 필요 없다 (2026-08-24)

로그 경로 둘이 소스에 `#define` 으로 박혀 있는데, 성질이 다르다.

| | 언제 쓰이나 | ini 로 바꿀 수 있나 |
|---|---|---|
| `DEFAULT_LOGFILE` | `loadconfig.c:155` 이 **기본값**으로 넣고 ini 의 `LOGFILE` 이 덮어쓴다 | ✅ 된다 |
| `TEMP_LOGFILE` | `main.c:263` 이 **ini 를 읽기 전에** 연다 (기동 배너를 담는 자리) | ❌ 원리상 불가 |

`TEMP_LOGFILE` 은 그래서 **`/tmp/pctcs.temp.log` 로 고정**했다 (운영자 요청
2026-08-24). 설치 루트와 무관해졌으므로 **`~/AIC` 를 어디로 옮기든 `pctcs`
재빌드가 필요 없다.** 그 파일은 수 초만 살고 `loadconfig` 뒤에 ini 의
`LOGFILE` 자리로 `mv` 되므로(`main.c:321`) **최종 로그 위치는 여전히 ini 가
정한다** — 운영상 보이는 것은 하나도 바뀌지 않는다.

실행으로 드러난 레거시 결함 둘도 같은 절에 있다 — `ISISclient/isisutils.c` 의 `ISODate()` 버퍼 초과(호출마다 9바이트, 20년 묵음)와 `main.c` 의 `sprintf` 오버플로 6곳(verbose 모드에서만 발현).

> ⚠️ **`TCS_Host`/`AUX_Host` 를 사이트 기본값으로 두고 시험하지 말 것.** `192.168.15.60`(SSO) 은 실제 필터·셔터·포커서·돔셔터를 제어하는 AUX 컴퓨터와 Telcom 이다. 벤치에서는 `127.0.0.1` — 스크립트가 그렇게 생성한다.

## 관련 문서 (같은 시스템의 다른 조각)

세 보고서가 KMTNet ICIMACS 시스템의 서로 다른 면을 다룬다 — 상호 참조하며 읽을 것:
- [../ics_legacy/ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) — **ICS**(카메라 통합제어) + IMPv2.5 프로토콜 + ISIS/XIS 허브. 이 폴더의 `TC` 노드가 그 문서의 노드 디렉토리에 있는 `TC`다.
- [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md) — **OBS Agent**(관측자용 CLI/스크립트 관측). TCSAgent 코드베이스를 포크해 만들어졌고, TCS Agent의 명령어를 거의 그대로 감싸서 제공한다.

## ▶ 다음 세션에서 바로 할 일 — Telcom/AUX 시뮬레이터 연동

`pctcs` 가 **SSO AIC 리눅스(`kmtnet-sso`)에 빌드돼 떠 있고** XIS 허브에 `TC` 로 등록된 상태다. Telcom/AUX 실물이 없어 두 링크는 `DOWN` 이다. KASI 가 만들어 둔 **시뮬레이터를 같은 머신에 설치하면 `pctcs.ini` 의 `TCS_Host`/`AUX_Host` 가 이미 `127.0.0.1` 이라 그대로 맞물린다.**

판정 세 가지:

1. 두 링크가 `DOWN` → **`UP`**  (`info` · `tstat` · `astat`)
2. `tstat`/`astat` 이 **실제 텔레메트리 값**을 돌려준다 (지금은 `DOWN 1 <UTC>` 뿐)
3. **`ics_sim` 의 텔레메트리 중계가 실값을 받는다** — 신규 ICS 는 노출마다 `AUXSTATUS`/`TCSSTATUS` 를 `TC` 에 질의해 각 IC 로 중계하는데, 지금은 무응답이라 `tc_timeout_mode=passthrough` 로 빈 필드를 채우고 있다. **FITS 헤더의 AUX/TCS 키워드가 처음으로 실값을 받는 자리다**

벤치 구성과 지난 결과는 [`../ics_sim/SMC_CLAUDE.md`](../ics_sim/SMC_CLAUDE.md) "이어서 시작하는 자리", 빌드는 [`build-local.sh`](build-local.sh).

## 다음에 이어서 할 만한 일

- `copt` 보정 로직(BLG 오프셋 테이블 + CCD 중심 오프셋)의 정식 스펙 문서화 — 현재 소스코드가 유일한 정본
- 신규 Python 구현 착수 시: 보고서 11절(신규 구현 고려사항) 참고. 저수준 프로토콜(9.2절)이 이제 정리돼 있으므로, 신규 TCS 인터페이스 설계의 하부 규격 인풋으로 활용
- (완료됨: `__reference/` 프로토콜 PDF 검토, 사이트-ini 매핑 확인 — 2026-07-29)

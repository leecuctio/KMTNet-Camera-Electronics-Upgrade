# SMC_CLAUDE.md

`TCSAgent/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md) 참고.

## 이 폴더가 다루는 것: TCS Agent (레거시 망원경 제어 인터페이스)

**TCS Agent**(실행파일 `pctcs`, ICIMACS 노드명 **`TC`**)는 카메라 시스템(ICIMACS)과 망원경 제어 시스템(TCS) 사이를 잇는 브리지 프로그램이다. OSU의 원조 `pctcs Agent v3.3.1`(Yale 1m/ANDICAM용)을 KASI가 KMTNet에 맞게 개조한 것으로, 개발/유지보수는 차상목(chasm@kasi.re.kr).

**현재 상태 (2026-07-28 기준)**
- 이 폴더의 자료(공식 매뉴얼 R4.0, v1.7.2 소스코드, 설정/데이터 파일, 버전 이력)를 **검토 완료**하고 분석 보고서로 정리해 둠.
- **핵심 산출물**: [tcsagent_report.md](tcsagent_report.md) — 시스템 구조, 원본 대비 KMTNet 개조 내역, 설치/빌드, 런타임 설정, 전체 명령어 레퍼런스, **매뉴얼에 없는 실제 기능**(아래 참고), 버전 이력, 신규 구현 시 고려사항. **이 소프트웨어를 파악할 때는 원본 PDF/소스를 다시 파기 전에 이 보고서부터 읽을 것.**
- 분석 대상 버전: **v1.7.2** (`TCSAgent.latest/KMTNet/pctcs.h`의 `APP_VER` 기준)

## 핵심 사실 요약 (자세한 근거는 보고서 참고)

- **구조**: TCP 클라이언트 2개 + UDP 노드 1개를 한 프로세스가 겸한다.
  - ICIMACS 쪽 ← **UDP/IMPv2** → 노드 `TC` (포트 6606)
  - 망원경 마운트 쪽 ← **TCP** → `Telcom`(포트 5750, PC-TCS의 시리얼을 네트워크로 중계하는 별도 프로그램)
  - 부속장치 쪽 ← **TCP** → `AUX` 제어 SW(포트 5752, 필터/셔터/포커서/돔셔터/거울냉각/환경센서)
- **원본 대비 최대 변경점**: 원본은 PC-TCS와 RS-232 시리얼 직결이었으나, KMTNet판은 이를 Telcom TCP + AUX TCP 2개 링크로 교체하고 자동 재연결(ArcMode)·링크 상태 관리를 신설했다.
- **TCS 링크와 AUX 링크는 독립적으로 상태 관리**된다 (`UP`/`IDLE`/`DOWN`, 각각 다른 타임아웃 기준).
- **카메라 셔터는 이 프로그램이 제어하지 않는다** — ICS가 HE box를 통해 TTL 신호로 직접 여닫고, TCS Agent/AUX는 그 상태를 모니터링만 한다. 운영상 매우 중요한 구분.
- **사이트별 설정 파일이 4종**(`ini/pctcs.kmtn{a,c,s,t}.ini`)인데, 알려진 관측소는 3곳(CTIO/SAAO/SSO)이다. 나머지 하나(`kmtnt`)가 어느 사이트/용도인지는 **미확인** — 각 ini의 `TCS_Host`/`AUX_Host` 값을 실제 배정과 대조해 확인 필요.

## 가장 중요한 발견: 공식 매뉴얼이 실제 기능을 다 담고 있지 않다

공식 매뉴얼 **R4.0(2020-11-10)의 명령어 표는 실제 v1.7.2 소스와 어긋난다.** 아래 명령들은 실제로 동작하지만 R3/R4 어디에도 문서화돼 있지 않다:

`catalog`(`cat`) · `tmradec`(`tmr`) · `tmobject`(`tmo`) · `tmelaz`(`tme`) · `tstow`(`stow`) · `oo` · `cc` · `concise` · `dtiltp` · `fttgotop` · `tick` · `treq`

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
| `__reference/*.pdf` | PC-TCS/Telcom/AUX 저수준 프로토콜 원본 규격 4종 | **미검토** — R4.0의 요약 설명으로 갈음. `tcmd`/`acmd`가 실제로 실어나르는 원시 프로토콜을 파고들 때 필요 |
| `__reference/ISISclient/`, `__reference/hiredis/` | 빌드 의존 라이브러리 사본 (ISISclient는 OBSAgent 쪽과 **동일 파일** 확인) | ISISclient는 [../ics_legacy/ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 7절에서 이미 분석 완료 |
| `TCSAgent.v1.7.2.zip` | 배포 압축본 (`.gitignore`의 `*.zip`로 git 미추적) | 미압축, `.latest`와 동일 추정 |

**git 상태 주의**: 이 폴더는 **아직 git에 커밋되지 않았다**(전체 untracked). 다른 컴퓨터에서 clone하면 이 폴더 자체가 없다. 커밋하더라도 `*.zip`, `test.*`, `.o`/`.a` 빌드산출물은 `.gitignore`로 제외된다.

## 관련 문서 (같은 시스템의 다른 조각)

세 보고서가 KMTNet ICIMACS 시스템의 서로 다른 면을 다룬다 — 상호 참조하며 읽을 것:
- [../ics_legacy/ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) — **ICS**(카메라 통합제어) + IMPv2.5 프로토콜 + ISIS/XIS 허브. 이 폴더의 `TC` 노드가 그 문서의 노드 디렉토리에 있는 `TC`다.
- [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md) — **OBS Agent**(관측자용 CLI/스크립트 관측). TCSAgent 코드베이스를 포크해 만들어졌고, TCS Agent의 명령어를 거의 그대로 감싸서 제공한다.

## 다음에 이어서 할 만한 일

- `__reference/`의 저수준 프로토콜 PDF 4종 검토 — `tcmd`/`acmd` 원시 명령 계층까지 파고들 때 필요
- 사이트별 ini 4종(`kmtna/c/s/t`)과 실제 관측소 배정 대조 확인
- `copt` 보정 로직(BLG 오프셋 테이블 + CCD 중심 오프셋)의 정식 스펙 문서화 — 현재 소스코드가 유일한 정본
- 신규 Python 구현 착수 시: 보고서 11절(신규 구현 고려사항) 참고

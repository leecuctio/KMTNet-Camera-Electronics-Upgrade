# TCS Agent (KMTNet) — 기술 분석 보고서

이 문서는 `TCSAgent/` 폴더에 있는 자료(공식 매뉴얼, 원본 소스코드, 설정 파일, 참고 문서)를 바탕으로 KMTNet TCS Agent 소프트웨어를 분석한 것이다. **배경지식이 없는 사람도 읽을 수 있도록** 관련 용어와 맥락부터 설명한다.

- 근거 자료: `KMTNet TCS Agent R4.0.pdf`(공식 매뉴얼, KASI 차상목 작성), `TCSAgent.latest/KMTNet/*`(v1.7.2 소스코드 및 설정/데이터 파일), `__reference/*`(저수준 프로토콜 원본 문서)
- 대상 버전: **v1.7.2** (소스코드 `pctcs.h`의 `APP_VER` 확인, `TCSAgent.v1.7.2.zip`과 일치)
- 공식 매뉴얼 버전: Rev.4 (2020-11-10) — 단, 아래 9절에서 설명하듯 매뉴얼이 다루지 못하는 v1.5.2~v1.7.2 사이 추가 기능이 존재한다.

---

## 1. 한눈에 보기

**TCS Agent**는 "망원경(TCS, Telescope Control System)"과 "카메라/관측 제어 시스템(ICIMACS)" 사이를 이어주는 다리 역할을 하는 프로그램이다. 실행 파일 이름은 `pctcs`이고, ICIMACS 네트워크 안에서는 노드 이름 **`TC`**로 불린다 — [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md)에서 정리한 노드 디렉토리의 `TC` 항목이 바로 이 프로그램이다.

역할을 한 줄씩 풀면:
- 카메라 쪽(ICS 등)이 이해하는 메시지 프로토콜(**IMPv2**, 텍스트 기반 `src>dest 메시지` 형식)과 망원경 하드웨어가 이해하는 저수준 프로토콜을 서로 통역한다.
- 사람이 터미널에서 직접 타이핑해 망원경을 제어/점검할 수 있는 명령줄 인터페이스(TC%)도 제공한다.
- 망원경의 상태(좌표, 추적 여부 등)와 부속장치(필터, 셔터, 돔, 포커서 등) 상태를 계속 수집해 카메라 쪽에 알려준다.
- 통신이 끊기면 자동으로 재연결을 시도한다.

**원본**: 이 프로그램의 뿌리는 OSU(Ohio State University) 천문학과 Richard Pogge가 만든 **pctcs Agent**(정확히는 v3.3.1)로, 원래 미국 Yale 1-m 망원경/ANDICAM 계측기에서 쓰이던 것이다. [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 7.4절에서 다룬 `pctcs`(ComSoft PC-TCS 전용 filter/agent)의 **KMTNet 맞춤 개조판**이 바로 이 TCS Agent다. KASI KMTNet팀의 차상목이 KMTNet 시스템에 맞게 대폭 수정·확장해왔다(2014년부터 현재 v1.7.2까지).

---

## 2. 왜 이런 프로그램이 필요한가 — KMTNet 망원경 제어 하드웨어 구조

KMTNet 망원경의 제어 시스템은 원래 **ComSoft社의 PC-TCS**라는 상용 망원경 제어 소프트웨어를 기반으로 한다. PC-TCS는 원래 시리얼(RS-232)로만 통신하도록 만들어진 오래된(Windows 98 시절) 프로그램이라, 요즘 네트워크 기반 시스템과 바로 연결할 수 없다. KMTNet은 이를 해결하기 위해 다음과 같은 2단 구조를 쓴다:

```
[ICIMACS 쪽]                        [망원경 제어 시스템(TCS) 쪽]
GUI ↔ ICG.IS(가이드) ↔                PCTCS (Win98)
        TCS Agent(TC)  ─UDP(IMP)─       └─ 망원경 마운트(가대) 직접 구동
        ↔ ICS.IS(과학)                   │  RS-232, ComSoft Native 프로토콜
                                          ▼
                                   AUX (WinXP) 컴퓨터
                                   ├─ Telcom (TCP 서버) — PCTCS를 TCP로 중계
                                   └─ AUX 제어 GUI SW (TCP 서버) — 필터/셔터/
                                       포커서/돔셔터/거울냉각 등 부속장치 제어
```

- **PC-TCS**: 망원경 마운트(가대, mount) 자체의 구동을 담당하는 원조 상용 소프트웨어. 지금도 Windows 98 위에서 그대로 돌아가며, 시리얼로만 통신한다.
- **Telcom**: PC-TCS의 시리얼 신호를 네트워크(TCP)로 중계해주는 별도 프로그램("PCTCS-NG Network Protocol"이라는 규격을 씀). AUX 컴퓨터(WinXP) 위에서 실행된다.
- **AUX 제어 소프트웨어**: 필터/셔터, 포커서(초점 액추에이터), 돔 셔터, 거울 냉각기(chiller), 환경 센서 등 "망원경 부속장치"를 제어하는 별도 GUI 프로그램. 이것도 TCP 서버를 내장하고 있다(자체 "KMTNet Auxiliary control software – Remote commands" 규격).
- **TCS Agent**: 이 두 TCP 서버(Telcom, AUX)의 **클라이언트**이면서, 동시에 ICIMACS 쪽으로는 UDP로 IMPv2 메시지를 주고받는 **노드(TC)** 역할을 한다. 즉 TCS Agent 혼자서 "TCP 클라이언트 2개 + UDP 노드 1개"를 겸한다.

## 3. 원본(pctcs Agent) 대비 KMTNet 개조 내역

R4.0 매뉴얼(2.2절)에 정리된 원본 대비 주요 개조 사항:

| 항목 | 원본 (Yale 1-m/ANDICAM) | KMTNet 개조 |
|---|---|---|
| PC-TCS 통신 | RS-232 시리얼 직접 연결 | Telcom을 거친 TCP/IP (PCTCS-NG 프로토콜) |
| 부속장치 제어 | 없음 | AUX TCP/IP 통신 신설 |
| 링크 복구 | — | 자동 재연결(auto recovery) 루틴 + 링크 상태 모니터링 신설 |
| 텔레메트리 | PC-TCS만 | PC-TCS + AUX 양쪽 다 |
| 고수준 명령 | 기본 이동 명령 위주 | 가이딩 오프셋, goto, offset, 필터 교체, 포커스/tip-tilt 조정 등 신설 |
| 설정 파일 | 기본 항목 | Telcom/AUX 서버 정보, 통신 제어, HW 스펙 등으로 확장 |

TCS/AUX 두 링크는 독립적으로 상태를 관리한다: PC-TCS 시리얼 스트림이 죽으면 TCS 링크는 `IDLE`, Telcom과의 TCP 연결이 끊기면 `DOWN`. AUX는 명령 송수신 실패나 TCP 단절 시 `DOWN`. 자동복구(ArcMode)가 켜져 있으면 `ArcInt` 간격으로 재연결을 시도한다.

## 4. 설치와 빌드

- **소스 구성 (10개 파일)**: `00README.txt`, `pctcs.h`(헤더), `main.c`(메인 루프), `loadconfig.c`(설정 파일 로더), `comsoft.c`(PC-TCS/AUX 통신 유틸리티), `commands.h`/`commands.c`(명령어 처리), `pctcs.ini`(기본 설정), `Makefile`, `build`(빌드 스크립트), `pctcs`(빌드된 실행파일)
- **빌드 의존성**: OSU ISIS 클라이언트 라이브러리(`/home/dts/ISIS/client`에 설치, [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 7절에서 분석한 그 `libisis.a`와 동일 계보) + GNU Readline 라이브러리
- **빌드 방법**: `make`가 아니라 전용 `build` 스크립트 사용 (`g++`로 컴파일, `-lisis -lreadline -lhistory -lncurses -lm` 링크)
- **실행**: `./pctcs [설정파일경로]` — 인자를 안 주면 기본값 `/home/dts/Config/pctcs.ini` 사용
- **KASI 운영 설치 위치**: ICS 서버의 `/home/dts/Agents/pctcs/KMTNet`(소스), `/home/dts/bin/pctcs`(실행파일), `/home/dts/Config/pctcs.ini`(설정) — 유지보수 계정 `kasi`/`kasimain`. 구버전 압축파일은 `Backup.KMTNet/`에 보관.
- KMTN_Startup 스크립트가 기동 시 `/home/dts/bin/pctcs`로 TCS Agent를 실행한다.
- **실행 서버(운영 배치)**: 관측자는 **Guide server(ICGui)** 터미널에서 `tcstart` 명령으로 실행한다(작은 xterm에 `pctcs` 창이 뜸). Guide server 불능 시 Spare/Science server에서도 실행 가능. 관측 후에도 계속 켜두고, 관측 전에 한 번 재실행하는 것이 운영 관례다. 신버전에 문제가 있으면 `tcstart.old`로 직전 버전을 실행한다. (OBSAgent 릴리스노트 v1.1.3의 운영 안내 기준 — [obsagent_report.md](../OBSAgent/obsagent_report.md) 참고)
- **배포 스크립트 (`scr/tcupdate`)가 배포 구조의 정본이다**: 개발 트리는 `/home/kasi/TCSAgent/KMTNet/`이고, `tcupdate`가 실행파일→`/home/dts/bin/`, 사이트별 ini→`/home/dts/Config/pctcs.ini`, 카탈로그(`pctcs.<site>.cat`, `blg.cat`, `NEA_TF-*.cat` 등)→`/home/dts/catalog/`, **사이트별 보정 테이블 `cortable/offset_<site>.table`→`/home/dts/cortable/offset_blg.table`(고정 이름)**으로 복사한다. 즉 런타임의 `offset_blg.table`은 항상 "현재 사이트용 테이블의 사본"이며, 소스 트리에 있는 `cortable/offset_blg.table`도 그 산출물이다. 이 저장소의 스냅샷은 `tcupdate`에 `sysid="kmtnt"`(TestBed)가 활성화된 상태로 저장돼 있다.

## 5. 런타임 설정 파일 (`pctcs.ini`)

ISIS 클라이언트 표준 설정 포맷(`Keyword Value`, `#` 주석, 대소문자 무관)을 확장한 것이다. 주요 키워드:

| 구분 | 키워드 | 의미 |
|---|---|---|
| 동작모드 | `Mode` | `Standalone`(임의 IMPv2 클라이언트 응답) 또는 `ISISclient`(지정된 ISIS 허브만 응답) |
| ISIS 서버 | `ISISID`, `ISISHost`, `ISISPort` | (ISISclient 모드일 때만 의미 있음) — [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md)의 `XIS` 허브에 해당 |
| 자기 자신 | `ID`(=`TC`), `Port`(기본 6606) | TCS Agent 자신의 노드명/UDP 포트 |
| TCS(Telcom) 서버 | `TCS_Host`, `TCS_Port`(기본 5750), `TCS_TelID`, `TCS_SysID` | Telcom 접속 정보 |
| AUX 서버 | `AUX_Host`, `AUX_Port`(기본 5752), `AUX_TelID`, `AUX_SysID` | AUX 제어 SW 접속 정보 |
| 타임아웃 | `Timeout_PCTCS`, `Timeout_Telcom` | 링크를 IDLE/DOWN으로 판단하는 기준 시간(초) |
| 갱신주기 | `UpdateInt_TCS`(최소 0.5초), `UpdateInt_AUX`(최소 0.1초) | 텔레메트리 갱신 간격 |
| 자동복구 | `AutoRecovery_TCS/AUX`, `ArcInt`(최소 0.5초) | 링크 자동 재연결 여부/간격 |
| HW 스펙 | `TCS_Guide_Step_RA/Dec`(arcsec/encoder count), `TCS_Guide_MinOff_RA/Dec`, `AUX_FS_Filter/Shutter_OpTime`, `AUX_FA_ActNum_South/East/West` | 가이딩 스텝 크기, 최소 오프셋(이보다 작으면 무시), 필터/셔터 동작 소요시간, tip-tilt 액추에이터 번호 매핑 |
| 실행 플래그 | `VERBOSE`, `DEBUG`, `DOLOG`, `LOGFILE` | 콘솔 출력/디버그/로깅 설정 |

실제 사이트별 설정은 `TCSAgent.latest/KMTNet/ini/pctcs.kmtn{a,c,s,t}.ini`(및 `.sta.ini`)로 나뉘어 있다. **사이트-코드 매핑은 각 ini 파일 헤더 주석으로 확정**된다:

| 파일 | 시스템 명칭 (ini 헤더) | 관측소 |
|---|---|---|
| `pctcs.kmtnc.ini` | KMTNet-CTIO (KMTNC) | 칠레 CTIO |
| `pctcs.kmtns.ini` | KMTNet-SAAO (KMTNS) | 남아공 SAAO |
| `pctcs.kmtna.ini` | KMTNet-SSO (KMTNA) | 호주 SSO (**A**ustralia) |
| `pctcs.kmtnt.ini` | KMTNet-**TestBed** | 테스트베드 (실관측소 아님) |

- `.sta.ini` 변형(예: `pctcs.kmtnc.sta.ini`)은 **Standalone 모드용** 설정이다 — `Mode Standalone`, 노드 ID `TC.STA`, 포트 5755(운영용 6606과 분리), 로깅 주기 30초(운영용 5초보다 느슨). ISIS 허브 없이 시험 구동할 때 쓰는 것으로, 운영 설정과 나란히 유지된다.
- 실전 ini에는 R4.0 매뉴얼의 키워드 표에 없는 항목도 있다: `LoggingInt_TCS`/`LoggingInt_AUX`(상태 로깅 주기, 운영 5.0초), `VERLOG`(verbose 로그), `CATFILE`(기동 시 자동 로드할 카탈로그 파일, 기본 `/home/dts/catalog/pctcs.cat` — 9절의 `catalog` 명령과 연동).

## 6. 명령어 레퍼런스 (공식 매뉴얼 R4.0 기준)

명령은 로컬 콘솔(키보드)과 원격(IMPv2, 다른 노드가 UDP로 보내는 메시지) 양쪽에서 동일하게 쓸 수 있다. `EXEC:`류 명령(예: `quit`)은 원격에서는 명시적 `EXEC:` 타입으로만 허용되고 권장되지 않는다.

### 6.1 Client 명령 (프로그램 자체 제어)
`quit`(종료) · `init`/`reset`(TCS+AUX 링크 초기화) · `close`(링크 닫기) · `arc`(자동복구 토글) · `info`(설정 조회) · `version` · `verbose`/`debug`(출력모드 토글) · `history` · `!!`/`!cmd`(직전 명령 반복) · `help`/`?`

### 6.2 TCS 명령 (망원경 마운트)
| 명령 | 인자 | 설명 |
|---|---|---|
| `tcsinit`/`tcsreset`/`tcsclose`/`tcsarc` | - | TCS(Telcom) 링크 제어 |
| `tcsstatus` | - | TCS 상태를 IMPv2 형식으로 반환 |
| `tstat` | - | TCS 상태를 경량(사람 아닌 기계용) 형식으로 반환 |
| `traw` | - | 가장 최근 PC-TCS 원본 텔레메트리 문자열 그대로 반환(디버깅용) |
| `tsync` | - | PC-TCS 시계를 로컬 시스템 시계와 동기화 (자정 근처엔 주의) |
| `tcmd` | `<원본명령>` | PC-TCS "COMSOFT Native Protocol" 원본 명령을 그대로 전달 |
| `tguide` | `<RA_offset> <Dec_offset>` [arcsec] | 가이딩 오프셋(RA/Dec 축 각각 별도 명령됨) |
| `tgoto` | `<RA> <Dec>` [J2000] | 절대 좌표로 이동 |
| `toffset` | `<RA_offset> <Dec_offset>` | 상대 오프셋 이동 |
| `tstop` | - | 이동 중지 |
| `tdi` | - | 현재 위치를 명령된 위치로 강제 동기화(망원경 없이 SW 테스트용) |

### 6.3 AUX 명령 (부속장치: 필터/셔터/포커서/돔/거울냉각/환경)
| 명령 | 인자 | 설명 |
|---|---|---|
| `auxinit`/`auxreset`/`auxclose`/`auxarc` | - | AUX 링크 제어 |
| `auxstatus`/`astat` | - | AUX 전체 상태(IMPv2 형식 / 경량 형식) |
| `acmd` | `<원본명령>` | AUX 제어 SW 원본 명령 그대로 전달 |
| `filter` | `<fnum>` (0~4) | 필터 교체 |
| `fsastat` | - | 필터/셔터 상태만 경량 조회 |
| `dfocus` | `<Δfocus>` [mm] | 초점 상대 이동 |
| `dtilt` | `<Δtilt_NS> <Δtilt_EW>` [arcsec] | tip-tilt 상대 조정 (원격은 EXEC만) |
| `fttgoto` | `<focus>` (`<tilt_NS> <tilt_EW>`) | 초점/tip-tilt 절대 위치 이동 |
| `fttstat` | - | 초점/tip-tilt 상태 경량 조회 |

> **주의(운영상 중요)**: 카메라 셔터 자체는 TCS Agent가 제어하지 않는다! 셔터는 ICS가 HE(Head Electronics) box를 통해 TTL 신호(HIGH/LOW)로 직접 여닫는다. TCS Agent/AUX의 "Filter/Shutter" 상태는 그 결과를 **모니터링**할 뿐이다 — 카메라 제어 소프트웨어는 셔터를 열기 전 `STANDBY` 상태를 확인하고, 닫을 때는 `OPENING`/`OPENED` 상태를 확인해야 한다(R4.0 6.1절).

### 6.4 상태/텔레메트리 문자열 필드 요약

- **TCS**: `DATE-OBS/TIME-OBS`(조회 시각) `DATE-UP/TIME-UP`(수신 시각) `RA/DEC/EQUINOX/HA/ST/SECZ/ALT/AZ`(좌표) `TCSLINK`(Up/Idle/Down) `TELMOVE`(이동축) `TCSLIMIT`(리밋 상태) `TCSDRIVE`(구동 활성화 여부) `EXECODE`(명령 실행결과 코드)
- **AUX**: 하위시스템별로 접두어가 붙는다 — `FS:`(Filter/Shutter), `FA:`(Focus Actuator, 남/동/서 3개 액추에이터의 절대위치·리밋), `DS:`(Dome Shutter), `MC:`(Mirror Cover), `CH:`(거울냉각 Chiller), `EN:`(환경센서 7개 + 팬)

> **`FA:` 의 "남/동/서" 는 단순화된 명명이다 (2026-08-11 확인).** 실제 배치는 3점 지지 120° 삼각형이고 세 점은 방위 180°(S) · 60° · 300° 에 있다 — 뒤의 둘은 물리적으로 **NE / NW** 이며, TCSAgent 가 이를 `EAST` / `WEST` 로 줄여 부른다. `S` 만 이름이 그대로다. 이 명명 차이는 `KMTNet Architecture R2.pdf`(레거시 계통도)의 액추에이터 라벨과 대조할 때 걸리므로 아래를 기준으로 삼는다:
>
> | | 기하 | 번호↔방위 대응 |
> |---|---|---|
> | 어디에 있나 | **소스 하드코딩** (`commands.c:3442-3447`, `pctcs.h` 의 `RAC 1008.8`·`SQRT3`·`MAX_DELTATILT 5000.0`) | **ini 설정** (`AUX_FA_ActNum_{South,East,West}`, `loadconfig.c:688-724`) |
> | 바꿀 수 있나 | 아니다. 코드 수정 사안 | 그렇다. 사이트별로 다를 수 있게 만들어져 있다 |
>
> **현재 값은 4개 사이트가 전부 같다** — `South=2 · East=1 · West=3` (`pctcs.kmtn{a,c,s,t}.ini` 전수 확인, `pctcs.h:181-183` 의 기본값과도 동일). `loadconfig.c:772` 가 셋이 서로 다른지 검사한다.
>
> **이 ini 값이 최종 확인된 설치 위치다** (운영자 확인, 2026-08-11). `dtilt <dtns> <dtew>` 의 부호 규약(*"positive when N/E goes up and S/W goes down"*)이 이 대응에 그대로 걸려 있으므로, 액추에이터 번호의 정본은 항상 **운영 ini** 다.
>
> ⚠️ **계통도 PDF 의 액추에이터 위치 라벨(`#1 NW`/`#3 NE`)은 ini 와 좌우가 반대로 읽히지만, 이는 미해결 항목이 아니다** — 그 부분은 아주 오래전에 작성된 것이고 이후 실측으로 확정된 것이 ini 쪽이다(운영자 확인). **PDF 의 FA 위치 불일치는 무시한다.** 두 자료를 대조하다 이 차이를 발견해 ini 를 "고치려" 드는 일이 없도록 여기 남긴다.

## 7. 소프트웨어 테스트/시뮬레이션

망원경/부속장치 없이도 소프트웨어만 테스트할 수 있도록 지원한다:
- PC-TCS는 데모(DEMO) 버전을 쓰면 좋고, 원본 버전을 써도 `tstop`/`tdi` 명령으로 "가짜 이동 완료" 처리가 가능하다.
- AUX 쪽은 전용 데모 프로그램이 있고, 원본에는 없는 시뮬레이션 명령을 추가로 제공한다: `acmd simul cshut high/low`(카메라 셔터 TTL 입력 흉내), `acmd simul staterr <subsys>`(특정 서브시스템 에러 흉내), `acmd simul clearerr`(에러 해제).
- `netcat`(nc)으로 Telcom/AUX 서버에 직접 접속해 원본 프로토콜 메시지를 주고받아보는 것도 매뉴얼에 예시로 나온다 (`nc <IP> 5750` 등).

## 8. 버전 이력 요약 (`UpdateNotes.v1.7.2.txt` 기준, v1.5.2 ~ v1.7.2)

| 버전 | 주요 변경 |
|---|---|
| v1.5.2 | `catalog`, `tmradec`/`tmr`, `tmobject`/`tmo`, `tmelaz`/`tme` 명령 신설 — RA/Dec 객체 카탈로그 도입 |
| v1.5.3/4 | HA 문자열 버그 수정, BLG 오프셋 보정에 목적지 HA 적용하도록 수정 |
| v1.5.5 | 포인팅 모델링 유틸리티 `oo`, `cc <x> <y>` 추가 |
| v1.6.0 | 이벤트 로그 파일 출력 추가, `tgoto` Dec 부호 버그 수정 |
| v1.6.1 | TSTAT/ASTAT 로그 파일 분리 출력, `LoggingInt_TCS/AUX`·`VERLOG` 설정 추가, AUXSTATUS의 `FILTER` 필드 정리 |
| v1.6.2 | `traw`(원본 텔레메트리 문자열)를 로그에 추가 |
| v1.6.3 | 텔레메트리 필드(Alt/Az/SecZ/RA/DEC) 검증·오류 로깅 강화 |
| v1.6.4 | 좌표 변환 함수 `trans1060()` 반올림 오차 개선 |
| v1.6.5 | 텔레메트리 패킷 디코딩 실패 시 재시도 로직 추가 |
| v1.6.6 | 카탈로그 입력 유연화, `TCSLIMIT`/`LimitStatus`에 복합 상태(RA+Dec 등) 라벨 추가, `history` 명령 개선 |
| v1.6.7~1.6.9 | K/M/T/N CCD 중심 오프셋 보정 기준점을 N→K→C(모자이크 중심)로 순차 변경 |
| v1.7.0 | `tstow`(`stow`) 명령 신설 — 망원경 스토우(파킹) 위치 이동 |
| v1.7.2 (2018-01-01) | `acmd` 응답 포맷 정리 |

## 9. 공식 매뉴얼(R3/R4)에 없는 실제 기능 — 소스코드 대조 결과

공식 매뉴얼 R4.0(2020-11-10 개정)의 명령어 표(5.1절)와 실제 v1.7.2 소스(`commands.h`)의 명령어 목록을 대조한 결과, **아래 명령들은 실제로 존재하고 동작하지만 R3/R4 매뉴얼 어디에도 문서화되어 있지 않다.** 신규 Python 구현이나 향후 유지보수 시 이 문서(및 소스코드)를 반드시 참고해야 한다.

| 명령 | 기능 (소스코드 `commands.c` 확인) |
|---|---|
| `catalog` (`cat`) | RA/Dec 객체 카탈로그 파일(기본 `/home/dts/catalog/pctcs.cat` — v1.7.2 소스 `pctcs.h:112`의 `DEFAULT_CATFILE`, 5절의 `CATFILE` 서술·전체 ini와 일치. 종전 표기 `/home/dts/Config/pctcs.cat`은 v1.5.2 당시 UpdateNotes의 값이라 v1.7.2와 다르다 — 정정 2026-08-08)을 메모리에 로드. 인자 없이 실행하면 로드된 카탈로그 데이터 목록 출력 |
| `tmradec` (`tmr`) | `<RA> <DEC> (<copt>)` — 좌표로 이동하되, 보정 옵션(`copt`)에 따라 좌표를 실시간으로 보정한 뒤 이동. 아래 9.1절 참고 |
| `tmobject` (`tmobj`/`tmo`) | `<객체명> (<copt>)` — `catalog`로 로드해둔 카탈로그에서 객체명으로 좌표를 찾아 `tmradec`와 동일하게 이동 |
| `tmelaz` (`tme`) | 고도/방위각(El/Az)으로 직접 이동 |
| `tstow` (`stow`) | 망원경을 스토우(파킹) 위치로 이동 (`MOVSTOW` 원본 명령 전송) |
| `oo`, `cc <x> <y>` | 포인팅 모델링 보조 유틸리티 (v1.5.5 도입) |
| `concise` (`con`) | verbose 모드 강제 해제 |
| `treq` | `<키워드>` — PCTCS-NG **REQUEST** 패킷을 Telcom에 직접 전송해 텔레메트리 개별 값(RA/DEC/HA/EL/AZ/SECZ/JD 등)을 조회. `tcmd`가 COMMAND(제어) 패킷을 보내는 것과 대비되는 조회 전용 통로 (v1.3.0, 소스 주석에 "for Skip's UI") |
| `tick` | `0`으로 기준점을 잡고 이후 호출마다 경과시간을 측정·출력하는 시간 태그 유틸리티 (v1.4.4, 성능/타이밍 진단용) |

> **정정 (비활성 명령)**: `dtiltp`/`fttgotop`은 소스에 함수(`cmd_adtiltp`/`cmd_afttgotop` — `dtilt`/`fttgoto`의 극좌표(theta/tilt) 버전)가 존재하지만, **명령 테이블 등록이 주석 처리되어 v1.7.2에서 실행되지 않는다**(`commands.h` 149-150행). help 텍스트에서도 주석 처리돼 있다. 즉 "구현됐다가 비활성화된" 명령이며, 위 표의 나머지 명령들처럼 실제로 동작하는 것은 아니다.

### 9.1 포인팅 보정 옵션(`copt`) — `tmradec`/`tmobject`의 핵심 기능

`tmradec <RA> <DEC> <copt>`의 `copt` 인자는 단순 이동이 아니라 **KMTNet 모자이크 카메라의 물리적 구조를 반영한 좌표 보정**을 수행한다:

- **`0`(기본값)**: 보정 없음, 입력 좌표로 그대로 이동
- **`1` (BLG 보정)**: **KMTNet Bulge(BLG) 서베이 필드 전용 포인팅 보정.** 목적지의 시각각(HA, Hour Angle)을 계산한 뒤, 사이트별 보정 테이블(`cortable/offset_{ctio,saao,sso}.table.<날짜>`, HA에 따른 RA/Dec 보정값 3열 텍스트)을 참조해 망원경 마운트의 알려진 비선형 지향 오차를 보정한다. `ics_legacy_report.md`의 4.3절에서 실측 로그로 확인한 실제 BLG 서베이 관측(`OBJECT BLG11` 등)이 바로 이 보정을 거쳐 지향된 것으로 보인다.
- **`k/K`, `m/M`, `t/T`, `n/N`**: 모자이크 중심(C) 대신 **특정 CCD(K/M/T/N)를 시야 중심에 오도록** 하는 오프셋. 소스코드 상수로 CCD 간 각거리가 `ad_ra = 63'/15(시간각 환산)`, `ad_dec = 66'`로 정의돼 있다 — 즉 인접 CCD 사이 간격이 약 63~66각분(약 1도)임을 의미한다. 버전 이력(9.1~1.6.9)을 보면 이 보정의 기준점이 "N에서 본 오프셋" → "K에서 본 오프셋" → "모자이크 중심(C)에서 본 오프셋"으로 여러 차례 재정의되었다 — 실측 지오메트리를 다듬어온 과정으로 보인다.

`catalog` 파일(`pctcs.cat`)의 실제 예시:
```
# Columns: OBJECT  RA  DEC  (default COPT)  #comments..
BLG01  17:54:52.760  -31:10:58.70  1
BLG02  17:54:52.760  -29:01:25.10  1
...
```
필드명(`BLG01`, `BLG02`...)이 [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 4.3절 실측 로그에서 본 `OBJECT BLG11` 등과 동일한 명명 체계임을 확인했다 — 즉 카메라(ICS)가 FITS 헤더/파일명에 쓰는 필드 이름과 TCS Agent가 실제 지향에 쓰는 카탈로그가 같은 필드 코드를 공유한다. **배포 주체는 OBSAgent로 확인됐다 (2026-08-08)**: `.osc` 노출 라인 한 줄이 `RA`/`DEC`/`COPT`와 `OBJECT`(필드명)를 함께 담고([obsagent_report.md](../OBSAgent/obsagent_report.md) 5절), 스크립트 관측 시 OBSAgent가 좌표는 `tmr <RA> <DEC> <copt>` 로 TC에(OBSAgent `KMTObs/commands.c` 5765~5768행), 대상 이름은 `<imgtyp> <object>`(예: `object BLG01`)로 ICS에(5960~5961행) 각각 보낸다. 즉 스크립트 관측은 `tmradec` 경로라 TCS 쪽 카탈로그(`pctcs.cat`)를 거치지 않으며, `pctcs.cat`은 수동/`tmobject`용으로 같은 필드명 체계를 **병행 유지**하는 별도 테이블이다(이중 관리 문제와 단일 소스 통합 권고는 11절 참고).

## 9.2 저수준 프로토콜 요약 — `tcmd`/`treq`/`acmd`가 실어나르는 것

`__reference/`의 원본 규격 3종을 직접 검토한 결과다. TCS Agent(그리고 이를 감싸는 OBSAgent)의 명령이 최종적으로 어떤 원시 프로토콜로 변환되는지의 정본.

**(1) PCTCS-NG 패킷 (Telcom, TCP 5750)** — `COMSOFT Legacy PC-TCS Communications` 문서 기준:
```
<TELID> <SYSID> <PID> COMMAND <Native명령...>   ← tcmd 경로 (제어)
<TELID> <SYSID> <PID> REQUEST <키워드>          ← treq 경로 (조회)
```
- `TELID`는 Telcom 실행 인자로 지정(예: KMTNET), `SYSID`는 항상 `TCS`, `PID`는 응답에 그대로 반사되는 시퀀스 번호. CR 종단.
- REQUEST 키워드: `ALL`(150자 텔레메트리 전체)/`RA`/`DEC`/`HA`/`ST`/`EL`/`AZ`/`SECZ`/`EQ`/`JD`/`MOTION`/`FOCUS`/`DOME` 등.
- Telcom(`telcom.exe`, WinXP 콘솔 앱, C.Johnson 2013)은 이 TCP 패킷을 PC-TCS의 RS-232(9600,N,8,1) Native 프로토콜로 중계하는 브리지일 뿐이다.

**(2) COMSOFT Native 프로토콜 (PC-TCS 본체)**:
- PC-TCS는 **150자 고정 컬럼 텔레메트리 스트림**을 계속 방송한다 — `traw` 명령이 돌려주는 그 문자열이다. 컬럼 위치로 파싱: 1=이동상태, 4-12=RA, 14-22=Dec, 25-33=HA, 44-48=고도, 57-61=SecZ, 63-70=COM채널별 **명령 실행코드**(E/e=실행됨, 1=Bogus Request, 2=Bogus Data, 3=Unrecognized, C=checksum 오류 — 6.4절 `EXECODE`의 원천), 72-75=리밋/드라이브, 85-93=JD, 97=초점, 111-120=UT.
- 명령은 대문자 ASCII + CR. TCS Agent 명령과의 대응: `tstop`→`CANCEL`, `tstow`→`MOVSTOW`, `tdi`→`DECLAREINIT`, `tguide`→`RADECGUIDE`, `tmelaz`→`ELAZ`, 좌표 이동→`MANUAL`+`NEXTRA`/`NEXTDEC`+`MOVNEXT` 계열, `tsync`→`SETTIME`/`SETDATE`(**두 명령이 분리돼 있어서** 자정 부근 동기화에 주의가 필요한 것).
- Telcom 문서판 명령 목록에는 Native 문서판에 없는 확장도 있다: `ASTEROID`/`COMET`/`ORBIT`(궤도 요소로 이동+자동 비항성 레이트), 행성/달/태양 위치 명령, `BIASRA`/`BIASDEC`(축별 바이어스 레이트 — OBSAgent NST 기능의 하부 수단), `STEPRA`/`STEPDEC`(엔코더 스텝 단위 이동) 등.

**(3) AUX 원격명령 (TCP 5752)** — `KMTNet AUX control remote commands(v20140908)`(작성: 차상목/KASI) 기준:
```
<TELID> AUX <PID> <SUBSYSTEM> <COMMAND> [인자...]   (LF 종단 — Telcom의 CR와 다름!)
```
- 서브시스템 6종: `FOCUSER`(3-액추에이터 초점/tip-tilt, ±10mm, `GOTO_A1~3`/`GOTO_ALL`/`OFFSET`/`HOME` — 배치와 번호 대응은 6.4절 블록), `SHUTTER`(돔셔터, `BOTH/UPPER/LOWER OPEN|CLOSE`, `GOTO <고도>`, **Auto-sync 모드**=`SET_ASYNC ON` 시 망원경 고도를 자동 추종), `FILTERS`(필터 슬라이드 4개 `SET_F1~4 IN|OUT` + 카메라 셔터 리밋 감시), `M1COVER`(주경 커버 0~100%), `CHILLER`(냉각수 온도/전원), `ENVIRON`(온습도 센서 7개 + 거울셀 팬).
- 공통 응답: `OK`(ACK) / `BAD`(NACK) / `WAIT`(이전 동작 미완) / `ERROR`, `STATUS` 조회 응답: `NC`/`STANDBY`/`RUNNING`/`ERROR`. TELID/System이 틀리면 **무응답**.
- **카메라 셔터의 정체가 이 문서에 상세히 나온다**: Full(하단)/Half(상단) 2중 블레이드 구조로, ICS→HE box의 TTL 신호(HIGH=열기 시작, LOW=닫기 시작)로만 구동된다(6.3절 주의사항의 근거). 개방/폐쇄 각 5초, 닫힘 후 재장전(reloading) 시퀀스 존재 — [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 로그의 `SHUTTER_OPSTAT`(STANDBY/OPENING/OPENED/CLOSING/RELOADING) 상태 명칭이 이 문서의 OpStatus 정의와 정확히 일치한다. 노출시간이 5초보다 짧으면 Full 블레이드가 다 열리기 전에 Half 블레이드가 닫히기 시작하는 "이동 슬릿" 동작이 된다.

## 10. 참고 원본 자료 색인

| 경로 | 내용 | 상태 |
|---|---|---|
| `KMTNet TCS Agent R4.0.pdf` | 공식 매뉴얼 최신판(2020-11-10, S. Cha) | 검토 완료, 본 보고서의 주 근거 |
| `KMTNet TCS Agent R3.pdf` | 공식 매뉴얼 구판 | 미검토(R4.0으로 대체됨) |
| `TCSAgent.latest/KMTNet/` | v1.7.2 소스코드, ini/catalog/cortable 설정·데이터 | 검토 완료 (핵심 소스 함수 확인) |
| `TCSAgent.latest/UpdateNotes.v1.7.2.txt` | v1.5.2~v1.7.2 버전별 변경 이력 | 검토 완료 |
| `TCSAgent.v1.7.2.zip` | 위 소스와 동일 버전의 압축 배포본 | 압축 파일이라 미압축, 내용은 `.latest`와 동일 추정 |
| `__reference/KMTNet AUX control remote commands(v20140908).pdf` | AUX 제어 SW 저수준 원격명령 규격 (`acmd`가 전달하는 실제 프로토콜, 작성: 차상목/KASI) | **검토 완료** — 9.2절 (3)에 요약 |
| `__reference/PCTCS Communications.pdf` | COMSOFT Native(150자 텔레메트리+명령) + PCTCS-NG(TELID/SYSID/PID 패킷) 원본 규격 | **검토 완료** — 9.2절 (1)(2)에 요약 |
| `__reference/TelcomDoc.pdf` | Telcom(telcom.exe) 사용법 + NG 프로토콜/REQUEST 키워드/직접명령 목록 (C.Johnson, 2013) | **검토 완료** — 9.2절에 반영 |
| `__reference/PC_TCS_version_6.pdf` | 상용 PC-TCS v6 자체 사용자 매뉴얼 | 미검토 (상용 SW 자체 문서 — 마운트 제어 내부까지 팔 때만 필요) |
| `__reference/IMPv2.5Protocol1.pdf` | [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 2절에서 이미 상세 분석한 것과 동일 파일 | 기존 분석으로 대체 |
| `__reference/ISISclient/` | 빌드 의존 라이브러리 사본 — OBSAgent 쪽 `ISISclient/`와 **동일 파일** 확인 | [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 7절 분석으로 대체 |
| `__reference/hiredis/` | Redis C 클라이언트 라이브러리 사본 (외부 오픈소스). TCS Agent 자체는 Redis를 쓰지 않으므로 참고용으로 함께 보관된 것으로 보임 — 실제 Redis 사용처는 [OBSAgent](../OBSAgent/obsagent_report.md) | 미검토 |

## 11. 신규 Python 구현 시 참고 사항

- TCS Agent는 본질적으로 "**두 개의 TCP 클라이언트(Telcom, AUX) + 한 개의 UDP IMPv2 노드**"라는 조합이다. Python으로 재구현한다면 `asyncio`로 TCP 클라이언트 2개와 UDP 소켓 1개를 동시에 다루는 구조가 자연스럽다.
- TCS 링크와 AUX 링크는 **완전히 독립적으로 상태를 관리**해야 한다(Up/Idle/Down 각각 다른 타임아웃 기준). 이 분리를 신규 구현에서도 유지할 가치가 있다.
- **셔터는 TCS Agent/AUX가 아니라 ICS가 직접 TTL로 제어**한다는 구조(6절 주의사항)는 신규 시스템에서도 그대로 가져갈지, 아니면 통합할지 결정이 필요한 지점이다.
- `copt` 기반 좌표 보정(9.1절)은 **공식 문서화가 안 된 채로 운영에 쓰이고 있는 로직**이다. 신규 구현 시 이 보정 테이블(`cortable/offset_*.table`)과 알고리즘을 그대로 이식할지, 정식으로 스펙을 정리해 재구현할지 결정하고 문서화해야 한다 — 현재는 소스코드가 유일한 정본(source of truth)이다.
- 카탈로그(`pctcs.cat`)의 필드 코드가 OBSAgent 쪽(관측 스크립트)의 필드 코드와 겹치는 것으로 보이므로, 신규 구현에서는 "필드 이름 → 좌표" 테이블을 TCS 쪽과 카메라 쪽이 이중 관리하지 않도록 단일 소스로 통합하는 것을 고려할 만하다.
- 버전 이력(8절)에서 보듯 이 프로그램은 10년 넘게 실운영 중 발견된 자잘한 버그(반올림 오차, 부호 오류, 자정 처리 등)를 계속 고쳐온 결과물이다. 신규 구현 시 이런 엣지케이스들을 자체적으로 다시 겪지 않도록, 버전별 변경 이력을 회귀 테스트 체크리스트로 활용할 만하다.

---

## 12. 재빌드와 설치 (2026-08-11 실측)

`ics_sim` 실물 연동 시험을 위해 **Ubuntu 24.04 / g++ 13.3.0 에서 v1.7.2 를 빌드해 기동했다.** OBSAgent 가 개정하지 않기로 확정돼 있고 TCS Agent 도 당분간 그대로 쓰므로, 신규 `ics` 전환 뒤에도 **두 에이전트는 계속 빌드돼야 한다.**

> 원 배포본(2014~2018, CentOS 계열)과 12년치 툴체인 차이로 그냥은 넘어가지 않는 것이 일곱 가지 있고, 그중 둘은 **빌드는 되는데 실행이 안 되는** 부류다. 실행 중에 레거시 결함 둘도 드러났다. **원인과 근거는 [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 3.7.1 에 정리했다** — 아래는 결과와 절차만 다룬다.

### 12.1 빌드

```bash
./build-local.sh --site kmtna      # 의존성 점검 → libisis.a 재빌드 → pctcs 빌드 → ini 생성
```

스크립트가 필요한 교정을 전부 적용하고 저장소는 건드리지 않는다(작업 사본에서 빌드). 의존 패키지는 `build-essential` · `libreadline-dev` · `libncurses-dev`.

산출물과 배치 — XIS 와 같은 뿌리에 모아 두면 판정 근거를 한자리에서 회수할 수 있다:

```
~/AICS/bin/isis                     XIS v2.9.1
~/AICS/Config/{isis,ics_sim,pctcs,obstool}.ini
~/AICS/Logs/{TC,OBS}/               에이전트 로그
~/AICS/build/ISISclient/            재빌드된 libisis.a (OBSAgent 와 공용)
~/AICS/build/TCSAgent/pctcs         v1.7.2
```

### 12.2 설정 — 사이트 ini 에서 바꾸는 네 줄

| 키 | 벤치 값 | 이유 |
|---|---|---|
| `ISISHost` | `127.0.0.1` | XIS 가 같은 머신 |
| **`TCS_Host`** | **`127.0.0.1`** | ⚠️ 아래 |
| **`AUX_Host`** | **`127.0.0.1`** | ⚠️ 아래 |
| `LOGFILE` | `~/AICS/Logs/TC/tc` | `/data` 는 권한 없음. 디렉토리는 미리 만들어야 한다 |
| `CATFILE` | 작업 사본의 `catalog/pctcs.cat` | 없어도 기동은 되고 `tmobject` 만 못 쓴다 |

> ⚠️ **`TCS_Host`/`AUX_Host` 를 운영 값으로 두고 시험하지 말 것.** 사이트 기본값 `192.168.15.60`(SSO)은 실제 필터·셔터·포커서·돔셔터를 제어하는 **AUX 컴퓨터와 Telcom** 이고(§2), TCS Agent 는 기동 즉시 접속해 폴링을 시작한다. `127.0.0.1` 이면 즉시 연결 거부 → 링크 `DOWN` 으로 깔끔히 떨어진다(도달 불가 주소는 오히려 connect 가 타임아웃까지 매달린다).

### 12.3 기동 결과

```
> Event Logging started successfully
> 40 of 54 data imported from catfile ...
- Started TCS Agent as ISIS client node TC on kmtnet-sso port 6606
- PCTCS Telcom tcp link init failed !       ← 하드웨어 없음, 정상
- AUX ctrl link init failed !               ← 〃
TC%
```

- XIS 콘솔 `HOSTS` 에 `TC` 가 `127.0.0.1:6606` 으로 등록
- `OBS>TC TSTAT`/`ASTAT` 가 허브를 거쳐 왕복 (`TC>OBS DONE: DOWN 1 <UTC>` · `… KMTA`)
- `ics_sim` 이 노출 중 보내는 `AUXSTATUS`/`TCSSTATUS` 질의가 실물 응답을 받는다 — 종전에는 `tc_timeout_mode=passthrough` 로 빈 필드를 채우던 경로다

**다음 단계** — Telcom/AUX 시뮬레이터를 같은 머신에 설치하면 `127.0.0.1` 설정이 그대로 유효해지고 두 링크가 `DOWN` → `UP` 이 된다. 그때 `tstat`/`astat` 의 실제 텔레메트리와 `ics_sim` 의 FITS 헤더(AUX/TCS 키워드)가 처음으로 실값을 받는다.

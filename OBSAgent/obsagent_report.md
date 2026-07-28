# OBS Agent (KMTNet) — 기술 분석 보고서

이 문서는 `OBSAgent/` 폴더 자료(공식 매뉴얼, 개발자 커맨드/함수 레퍼런스, 원본 소스코드, 실제 관측 스크립트 예제)를 바탕으로 KMTNet **OBS Agent**(관측 프로그램)를 분석한 것이다. **배경지식이 없어도 읽을 수 있도록** 필요한 맥락부터 설명한다.

- 근거 자료: `KMTNet 스크립트 관측 방법 (Rev.0.1).pdf`(공식 매뉴얼 초안, KASI), `OBSAgent.latest/`(v1.2.0 소스코드·설정·스크립트), `Commands.v1.0.txt`/`Functions.v1.0.txt`/`Ref.ObsStatus.txt`/`UpdateNotes.v1.1.txt`(개발자 레퍼런스), `OBSAgent_release_note_v1.1.3_R240718.*`
- 대상 버전: **v1.2.0** (소스 `obstool.h`의 `APP_VER` 확인, `OBSAgent.v1.2.0.win.zip`과 일치)
- 공식 매뉴얼은 "Rev.0.1"(초안) 상태로, 문서 곳곳에 "자세한 설명 필요"라는 저자의 메모가 남아 있다 — 이 보고서는 그 공백을 소스코드·개발자 문서로 최대한 메웠다.

---

## 1. 한눈에 보기

**OBS Agent**(실행파일 `obstool`, 또는 작은 xterm 창으로 실행하는 `obstart`)는 관측자가 실제로 마주 앉아 쓰는 **명령줄 관측 프로그램**이다. ICIMACS 네트워크에서는 노드 이름 **`OBS`**로 불리며 — [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md)에서 정리한 `OBS` 노드가 바로 이 프로그램이다. 실측 로그에서 본 `OBS>ICS ...`, `OBS>TC ...` 메시지들은 전부 이 OBS Agent가 관측자 대신(혹은 스크립트를 대신 실행하며) 보낸 것이다.

역할:
- **카메라(ICS)**와 **망원경(TCS Agent)** 양쪽에 원격으로 명령을 보내고 상태를 조회하는 통합 명령줄 인터페이스
- 미리 작성한 **관측 스크립트(.osc 파일)** 를 읽어들여 순서대로 자동 실행하는 "스크립트 관측" 기능
- 카메라·망원경·돔·필터 등 시스템 전반의 상태를 계속 감시하며 이상 상황을 관측자에게 경고
- 돔 회전/조명 등 웹 릴레이(Web relay) 기반 보조 장비 제어

**계보**: OBSAgent는 원래 별도로 새로 짠 프로그램이 아니라, **TCSAgent의 코드베이스(v1.6.1/v1.6.6)를 그대로 재사용해서 만들어졌다**(`UpdateNotes.v1.1.txt`의 v0.0.5 항목: "OBSAgent v0.0 re-creation, re-using TCSAgent flatform and code of TCSAgent v1.6.1"). 그래서 [tcsagent_report.md](../TCSAgent/tcsagent_report.md)에서 분석한 ISIS 클라이언트 라이브러리 사용 방식, `pctcs.h`류 헤더 패턴, `copt`(포인팅 보정 옵션)·`offset_blg()` 함수 등을 OBSAgent도 그대로 공유한다. 이후 2017년 말부터 2024년까지 독자적으로 크게 확장되어(§8 버전이력 참고) 지금은 TCSAgent보다 훨씬 큰 프로그램이 되었다.

## 2. 시스템 안에서의 위치

```
관측자(사람) 또는 관측 스크립트(.osc)
        │
        ▼
   OBS Agent (노드: OBS)  ── UDP/IMPv2 ──┬── ICS (카메라 통합제어, K/M/T/N/G.IC)
                                          └── TC (TCS Agent → PC-TCS/Telcom, AUX)
        │
        └── HTTP(Curl) ── Web Relay(돔 회전/조명 등)
        └── Redis ────── newTCS 상태 서버(돔 상태 등, 2024년 이후 도입)
```

OBS Agent는 [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md)·[tcsagent_report.md](../TCSAgent/tcsagent_report.md)에서 각각 분석한 ICS 명령어 전체와 TCS Agent 명령어 전체를 **그대로 다 알고 있다** — 이 프로그램 하나가 카메라·망원경 양쪽의 프론트엔드 역할을 겸한다. 여기에 더해 돔(Dome) 회전·조명, 거울셀 팬(mirror cell fan) 등 ICS/TCS Agent가 다루지 않는 나머지 하드웨어는 **웹 릴레이(HTTP)**와 **Redis**(2024년 도입된 "newTCS" 시스템)로 직접 제어/조회한다.

## 3. 실행과 기본 사용법

- 실행: 터미널에서 `obstool`(전체 창) 또는 `obstart`(작은 xterm)
- 구버전으로 되돌리기: 업데이트 후 예기치 못한 오류가 있으면 `obstool.old`/`obstart.old`로 이전 버전 실행 가능 — 즉 운영진이 항상 최신판과 직전판을 나란히 유지해둔다
- 도움말: 프롬프트에서 `help` 또는 `?`
- 종료: 창을 그냥 닫지 말고 반드시 `quit` 입력 (정상 종료 필요)
- 스크립트 파일 기본 경로: `/home/dts/osc/`
- **중요한 운영 규칙**: ICS를 재시작했을 때는 TCS Agent와 OBS Agent도 함께 재시작해야 한다 (연결 상태가 꼬이는 것을 방지)

## 4. 명령어 레퍼런스 (v1.0.2 기준, `Commands.v1.0.txt`)

명령이 매우 많으므로 기능별로 묶어 정리한다. (공식 Rev.0.1 매뉴얼의 명령어 표보다 최신·완전한 목록이다 — 매뉴얼에는 없는 돔/릴레이/Redis/유틸리티 계열이 여기 추가돼 있다.)

### 4.1 Client 명령
`quit`/`init`(재시작)/`info`/`version`/`timetag`(콘솔에 시각 표시 토글)/`verbose`/`concise`/`debug`/`history`/`!!`/`!cmd`/`help`

### 4.2 TCS 명령 (망원경) — [tcsagent_report.md](../TCSAgent/tcsagent_report.md) 6.2절과 거의 동일
`tcsinit`/`tcsreset`/`tcsclose`/`tcsarc`/`tcsstatus`/`tstat`/`traw`/`tsync`/`tcmd`/`treq`/`tmradec`(`tmr`)/`tmobject`(`tmo`)/`tmelaz`(`tme`)/`tmoffset`(`toff`)/`tguide`(`tgui`)/`tstop`/`tstow`(`stow`, "추적 끄고 천정 스토우 위치로 이동")/`tdi`/`cc`,`oo`(포인팅 모델링) + **OBSAgent 전용 추가**: `nstset`/`nston`/`nstoff` (비항성 추적, Non-Sidereal Tracking — 소행성 등 움직이는 천체 추적용)

### 4.3 AUX 명령 (필터/셔터/포커스) — TCSAgent와 동일
`auxinit`/`auxreset`/`auxclose`/`auxarc`/`auxstatus`/`astat`/`acmd`/`fsastat`(`fs`)/`filter`/`filname`/`fttstat`(`ft`)/`dfocus`/`dtilt`/`fttgoto`

### 4.4 ICS 명령 (카메라) — [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 3.1/3.2절과 거의 동일
`status`(ICS)/`kstatus`/`mstatus`/`tstatus`/`nstatus`/`gstatus`(채널별 IC 상태)/`acqstatus`/`filename`/`expnum`/`dmawait`/`datasource`/`ledflash`/`observer`/`projid`/`exp`/`object`·`bias`·`dark`·`flat`·`sky`·`domeflat`·`standard`/`go`

### 4.5 상태/서브시스템 명령 (OBSAgent 고유)
| 명령 | 설명 |
|---|---|
| `expinfo`(`ee`) | 현재 노출 정보 조회 (§6 참고) |
| `sysstat`(`ss`) | 관측시스템 전체 상태 조회 (§7 참고) |
| `domestat`(`dstat`) | Redis/Relay/AuxStatus 종합해 돔 상태 갱신·조회 |
| `override`(`ovr`) | 특정 연결 실패를 무시하도록 설정: 인자 `i`(ISIS)/`t`(TCS)/`a`(AUX)/`*`(전체)/`?`(조회) |
| `dlamp` | 돔플랫용 램프 전원 on/off |
| `dlight` | 돔 LED 조명 전원 on/off |
| `mcfan` | 거울셀 냉각팬 전원 on/off |
| `tpad` | PC-TCS 패들(N/S/E/W 버튼) 4방향 on/off |
| `drot`(`dr`) | 돔 회전 상태 조회/갱신 |

이 계열은 전부 **웹 릴레이(HTTP, ezCurl 라이브러리 사용)** 또는 **Redis**(newTCS)로 직접 통신한다 — ICS나 TCS Agent를 거치지 않는, OBSAgent만의 독자적인 하드웨어 제어 경로다.

### 4.6 유틸리티 명령
`ecmd`(`ec`, 쉘 외부명령 실행)·`dtchk`(FITS 파일이 `/data`에서 `/data/YYYYMMDD`로 정상 이전됐는지 점검 후 종료)·`redisget`/`redisset`/`redislocal`·`warning`(경고 점멸 on/off)·`msgout`·`sleep`·`tick`·`noop`(스크립트용 더미 명령)·`getut`(`ut`)·`getjd`(`jd`)·`getlst`(`lst`)·`getalt`(`alt`, RA/Dec/시각으로 고도·방위각·시각각·대기질량 계산)

> `getjd`/`getlst`/`getalt` 계열은 **USNO NOVAS 천문계산 라이브러리**를 이식해 만든 `calculation.c`를 쓴다(v0.8.8 도입) — 이 계산이 도입되기 전에는 시각각(HA)을 구하려면 반드시 PC-TCS가 살아있어야 했는데, 이후로는 **망원경 연결 없이도** 스크립트의 고도/시각각을 미리 계산할 수 있게 됐다.

### 4.7 스크립트 관측 명령 (§5에서 상세 설명)
`oscript`(`osc`)/`oline`/`olabel`/`oobject`/`ostat`(`os`)/`olast`/`ostart`/`ostop`/`oabort`/`opause`(`op`)/`oresume`(`or`)/`oprepare`/`odelay`(`delay`)

## 5. 관측 스크립트 (`.osc`) 문법

`.osc` 파일은 한 줄에 **명령 하나** 또는 **노출 한 장**을 정의하는 텍스트 파일이다.

- `#`으로 시작하는 줄과 빈 줄은 주석(무시)
- `+`로 시작하는 줄은 **명령어 라인**: `+<명령어> <인자...>` (예: `+projid BLG`, `+ostart 6`) — 대소문자 구분 없음, 인터랙티브 프롬프트에 치는 명령과 완전히 동일
- 그 외 모든 줄은 **노출 라인**이며, 공백으로 구분된 10개 컬럼을 갖는다:

```
LABEL  RA  DEC  COPT  IMGTYP  OBJECT  FILTER  EXPTIME  UTOBS  UTTOL
```

| 컬럼 | 의미 |
|---|---|
| `LABEL` | 사람이 알아보기 위한 설명(라인 검색용, FITS에는 안 들어감) |
| `RA`/`DEC` | J2000 좌표 `hh:mm:ss.s`/`+dd:mm:ss.s`. `-`(하이픈)을 넣으면 망원경을 움직이지 않음(트래킹 유지) |
| `COPT` | 포인팅 보정 옵션. `1`=BLG 보정 적용, `0`/`-`=미적용. [tcsagent_report.md](../TCSAgent/tcsagent_report.md) 9.1절의 `tmradec`용 `copt`와 동일한 값 |
| `IMGTYP` | `object`/`dark`/`bias`/`flat`/`domeflat`/`sky` 중 하나 |
| `OBJECT` | FITS 헤더 `OBJECT` 키워드에 그대로 들어감 |
| `FILTER` | 필터 이름 또는 슬라이드 번호 |
| `EXPTIME` | 노출시간(초), 최소 0.1초 |
| `UTOBS` | 이 시각에 노출 시작 (ISO `yyyy-mm-ddThh:mm:ss.s`). 미지정 시 `-` |
| `UTTOL` | `UTOBS` 허용 오차(초). 오차 안에 시작 못 하면 그 줄은 건너뛰고 다음 줄로. 미지정 시 `-`(=시간 무관, 순차 실행) |

### 5.1 반복(루프)과 흐름 제어

`+ostart <줄번호>`를 스크립트 라인 사이에 넣으면 **그 줄번호부터 다시 실행**하도록 되돌아간다 — 실제 SN(초신성) 서베이 스크립트(`sn.2017.osc`)에서는 관측 가능한 대상군이 새벽까지 바뀌는 것을 반영해 `+ostart 22`처럼 특정 구간을 계속 반복시킨다. [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 4.3절 실측 로그에서 본 "`OBJECT BLG11` → `BLG12` → ... 반복" 패턴이 바로 이 `+ostart` 루프 메커니즘으로 만들어진 것이다.

- `+ostop`: 현재 노출 완료 후 스크립트 정지
- `+opause`: 그 자리에서 일시정지(관측자 개입 대기) → `oresume`으로 이어서 진행
- `+oabort`: 노출 중이든 아니든 즉시 전체 중단

### 5.2 실제 예제 (공식 매뉴얼 `sample.osc`에서 발췌)

```
+ProjID ALL
+Datasource CTC
+DMAWait 500
+Observer KMTNet observer

+projid BLG
# LABEL RA DEC COPT IMGTYP OBJECT FILTER EXPTIME UTOBS UTTOL
BLG-NORMAL-1015 17:54:24 -31:08:00 1 object BLG01 I 60 - -   # Line number = 6
BLG-NORMAL-1016 17:54:24 -29:01:30 1 object BLG02 I 60 - -
...
BLG-NORMAL-1021 17:54:07 -31:15:30 1 object BLG41 I 60 - -
+ostart 6   # 'BLG-NORMAL-1015' 줄부터 다시 반복

+ProjID NEO
2011WO41 00:53:20.0 -27:00:00.0 0 object S29000 R 42 2017-08-08T05:50:00 20  # UTOBS±20초 안에 시작
...

+ProjID ALL
morning.domeflat - - - domeflat dflat r 20 - -
...
+stow
+opause    # 관측자가 확인 후 'oresume'
+acmd m1cover close
+opause    # 거울 커버 닫힘 대기
morning.dark - - - dark dark n 60 - -
...
morning.bias - - - bias bias n - - -
```

이 예시 하나에 KMTNet 실제 운영 패턴이 거의 다 들어있다: 서베이(BLG) 반복 노출, 시각지정(NEO 소행성) 관측, 아침 캘리브레이션(돔플랫→스토우→거울커버닫기→다크→바이어스) 자동화, 그리고 사람 개입이 필요한 지점에서의 `opause`.

## 6. 노출 상태 추적 — `CamStatus` / `ExpStatus`

OBSAgent는 ICS가 보내는 원시 메시지(`EXPSTATUS=...`, `Shutter=Open`, `PCTREAD=...`, `Wrote ...` 등, [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 5절 참고)를 실시간으로 해석해서 **자체적인 상태 머신**을 유지한다. 스크립트 관측 프로세스는 이 상태만 보고 다음 행동(다음 노출 준비, GO 명령 등)을 결정한다 — ICS 원시 메시지를 직접 파싱하지 않는다.

**`CamStatus`** (ICS/IC 메시지 기반):
`NC`(미연결) → `PREP_I`(초기화중) → `PREP_E`(플러싱) → `INT_1`(적분 시작, ICS 기준) → `INT_2`(K.IC로부터 "Shutter=Open" 수신) → `INT_3`(K.IC로부터 "Remaining=" 수신) → `CLOSING`("Shutter=Closed") → `READ_1`(ICS의 "EXPSTATUS=READOUT") → `READ_2`/`READ_3`(K.IC의 1번째/2번째 "PCTREAD=") → `IDLE_1`(1번째 IC의 "Acquisition Complete") → `IDLE_2`(4번째, 즉 전 채널의 "Acquisition Complete") → `IDLE_3`(ICS의 "EXPSTATUS=IDLE") → **`READY`**(모든 IC의 "Disk Write Complete" 수신, 또는 `IDLE_3` 도달 12초 후 강제 전환) — 그 외 `CHECK`(알수없음), `CRASHED`(IC 응답 없음/초기화 실패 등)

> **중요 제약**: `EXP`/`OBJECT`/`DARK`/`BIAS`/`FLAT`/`PROJID`/`OBSERVER` 명령은 `CamStatus`가 `READY`일 때만 유효하고, **`GO` 명령은 `IDLE_3` 또는 `READY`일 때만** 실행 가능하다 — 즉 이전 노출의 파일 저장까지 다 끝나야 다음 설정 변경/노출 시작이 허용된다. 이는 [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 4.3절에서 확인한 "readout 도중 다음 필드 명령이 이미 들어옴" 파이프라이닝과는 다른 층위의 이야기다 — ICS 자체는 readout 중에도 명령을 받아주지만, **OBSAgent는 안전을 위해 `READY` 상태 전까지 다음 스크립트 라인 실행을 미룬다**(단 "다음 노출 준비"용 망원경 이동/필터 변경은 `oprepare` 옵션에 따라 readout 중에 미리 실행될 수 있다, §7 참고).

**`ExpStatus`** (`CamStatus`를 스크립트 관측 관점으로 재분류한 것, `expinfo` 명령으로 조회):
`CHECK`/`STANDBY`(스크립트 미실행 중 대기)/`CMDED`(GO 명령 직후)/`WAITING`(스크립트 실행 중 망원경 준비 대기)/`FLUSH`/`EXPOSURE`/`READOUT`/`FINISH`/`ERROR`(FITS 쓰기 미완료 등)

`expinfo` 반환 예시:
```
DONE:/EXP.INFO: ExpStatus=EXPOSURE ExpNum=20240628.012345  ExpStart=2024-07-01T12:34:56.789  ExpProg=40/60     FitsNum=20231002.012344
```

## 7. 시스템 상태 파일 — `sysstat` / `/data/Logs/ObsStatus.txt`

OBSAgent는 백그라운드에서 5초 간격으로 카메라·망원경·돔 상태를 하나의 텍스트 파일 `/data/Logs/ObsStatus.txt`로 계속 덮어써서 저장한다(`WriteObsStatus()`). 이 파일은 [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) 4.6절에서 분석한 **`GMON`(모니터링 클라이언트)이 `sysstatus`로 조회하는 내용과 완전히 동일한 포맷**이다 — 즉 GMON은 이 파일(또는 이를 만드는 것과 동일한 내부 함수 `GetSysStatus()`)이 산출하는 요약 문자열을 실시간으로 받아보는 것이다.

파일 구성(`Ref.ObsStatus.txt` 근거): `CamStatus`/`FitsSaved`/`ExpSet`/`ExpRem`(카메라) · `TelStatus`/`RA`/`DEC`/`HA`/`SecZ`/`Alt`/`Az`/`Move`/`Limit`/`Drive`(망원경) · `FILTSTAT`/`FILTER`/`SHUTSTAT`/`SHUTTER`/`FOCUS`/`TILT`/`SENS`/`FAN`(AUX) · `DomeRot`/`DomeShut`(돔, 2024년 추가) · `OscStatus`/`LINE#`/`CMD#`/`EXP#`(스크립트 진행) · `ExpStatus`/`ExpNum`/`ExpStart`/`ExpProg`/`FitsNum`/`FitsOsc`(현재 노출) · 그리고 스크립트의 다음 실행 예정 줄들을 미리보기로 몇 줄 덧붙임.

`TelStatus` 값 중 `TRACKINGS`("안정적으로 추적 중")는 [ics_legacy_report.md](../ics_legacy/ics_legacy_report.md)의 실측 GMON 로그에서 본 `TelStatus=TRACKINGS`와 정확히 일치한다.

## 8. 버전 이력 하이라이트 (`UpdateNotes.v1.1.txt`, v0.0.5 ~ v1.2.0 "reserved")

전체 이력이 매우 길어(2017-08-07 ~ 2024년), 주요 전환점만 요약한다.

| 시기 | 버전 | 주요 사건 |
|---|---|---|
| 2017-08 | v0.0.5 | TCSAgent v1.6.1 코드를 재사용해 OBSAgent 탄생 |
| 2017-11~12 | v0.0.6~0.0.9 | 관측 스크립트 구조/로딩 기능 최초 구현 |
| 2018-01 | v0.1.0~0.3.2 | 스크립트 실행 엔진(진행/정지/중단/재개), `kstatus`~`gstatus`, `acqstatus`/`expnum` 등 채널별 명령 추가 |
| 2019~2020 | v0.3.3~0.4.9 | 노출 잔여시간 표시, 포인팅 오차·리밋 경고, `CamStatus`에 `READY` 상태 도입 |
| 2020-09~12 | v0.5.0~0.6.1 | 고도/시각각 계산 기능, override 명령, 리밋 경고 강화 |
| 2021 | v0.6.2~0.7.4 | UTOBS/UTTOL(시각 지정 관측) 도입, `+ProjID` 스크립트 컬럼화 |
| 2022 | v0.7.5~0.9.2 | **비항성추적(NST)** 도입(소행성 등 이동 천체 추적), 돔 회전/조명/거울팬 릴레이 제어(`dlamp`/`dlight`/`mcfan`/`tpad`/`drot`) 신설 |
| 2022-08 | v0.8.8~0.8.9 | USNO NOVAS 라이브러리 이식 → 망원경 연결 없이 HA/고도 계산 가능 |
| 2023-11~2024-06 | v0.9.2~0.9.9 | **Redis(newTCS) 연동** 시작(`redisget`/`redisset`), 돔 상태를 Redis+웹릴레이+AUX 3원 소스로 종합 판단하는 로직 정착 |
| 2024-07 | v1.0.0~1.0.9 | `expinfo`/`ExpStatus` 상태머신 정식 도입, 관측상태 파일(`/data/Logs/ObsStatus.txt`) 5초 주기 기록 시작 |
| 2024-08 | v1.1.0~1.1.4 | 돔 회전/셔터 완료 대기 플래그, 로그 필드 확장, 돔 회전 대기 고도 기준 85→82도 조정 |
| (예정) | v1.2.0 "reserved" | `dlamp`/`dlight`/`mcfan`/`tpad` 무인자 실행 시 실제 상태 반환, Redis 타임아웃/돔회전 고도 설정을 설정파일 항목화 — **모터/창문/HVAC 제어는 아직 미구현**으로 명시됨 |

**계보상 흥미로운 점**: 이 프로그램은 처음엔 "TCS Agent를 베껴 만든 관측 콘솔"이었지만, 지금은 **스크립트 자동관측 엔진 + 상태머신 + 돔/릴레이/Redis 통합 제어**까지 갖춘, 사실상 KMTNet 관측 운영의 두뇌 역할을 하는 프로그램으로 성장했다.

## 9. 소스 구성

```
OBSAgent.latest/
├── KMTObs/                  ← OBSAgent 본체 소스 (실행파일: obstool)
│   ├── main.c, commands.c/h, obstool.h, calculation.c(USNO NOVAS), loadconfig.c
│   ├── ini/                 ← 사이트별 설정 (kmtna/kmtnc/kmtns.ini)
│   ├── csh/                 ← 실행/유틸 쉘스크립트 (obstart, obstool, repeat.*.csh 등)
│   └── osc/                 ← 실제 사용된 관측 스크립트 대량 보관 (BLG/SN/NEO/domeflat/공학점검 등)
├── ISISclient/              ← ISIS 클라이언트 라이브러리 (TCSAgent/ICS와 동일 계보, ics_legacy_report.md 7절 참고)
└── hiredis/                 ← Redis C 클라이언트 라이브러리 (newTCS 연동용, v0.9.3부터)
```

`KMTObs/osc/` 폴더에는 실제 운영에 쓰인 스크립트가 방대하게 남아있다 — BLG 필드 반복 서베이, SN 타겟 리스트, NEO 시각지정 관측, 돔플랫/다크/바이어스 캘리브레이션, 공학점검(`eng/` 하위, 초점 이탈 테스트 등), 최근 사이트 확장(`site.23.10/`) 스크립트까지. 신규 시스템 설계 시 이 실제 스크립트들을 회귀 테스트 케이스로 활용할 만하다.

## 10. 참고 원본 자료 색인

| 경로 | 내용 | 상태 |
|---|---|---|
| `KMTNet 스크립트 관측 방법 (Rev.0.1).pdf` | 공식 매뉴얼 초안(관측자용) | 검토 완료 — 단, 초안이라 일부 항목("자세한 설명 필요")은 미완성 |
| `OBSAgent.latest/Commands.v1.0.txt` | 최신 전체 명령어 레퍼런스 | 검토 완료, 본 보고서 4절의 주 근거 |
| `OBSAgent.latest/Functions.v1.0.txt` | 소스코드 함수/선언 목록 | 검토 완료 |
| `OBSAgent.latest/Ref.ObsStatus.txt` | 상태 파일 포맷 상세 | 검토 완료, 본 보고서 7절의 주 근거 |
| `OBSAgent.latest/UpdateNotes.v1.1.txt` | v0.0.5~v1.2.0(예정) 버전 이력 | 검토 완료, 본 보고서 8절의 주 근거 |
| `OBSAgent.latest/READMEold` | 구버전 README | 미검토(최신 문서로 대체됨) |
| `OBSAgent_release_note_v1.1.3_R240718.pdf/docx` | v1.1.3 공식 릴리스 노트 | 미검토(UpdateNotes.v1.1.txt와 내용 중복 추정) |
| `OBSAgent.latest/KMTObs/osc/*` | 실제 운영 관측 스크립트 대량 | 대표 예시만 검토(공식 매뉴얼의 sample.osc/sn.2017.osc) |
| `OBSAgent.v1.1.4.zip`, `OBSAgent.v1.2.0.win.zip` | 배포 압축본 | 미압축(내용은 `.latest`와 동일 추정) |
| `CCD status (20220826.emaitoSET).pdf` | CCD 상태 문서 | 이 폴더로 이동됨(2026-07-28, ics_legacy에서 이동) — 미검토, OBSAgent 분석과 직접 관련 낮음 |

## 11. 신규 Python 구현 시 참고 사항

- OBSAgent는 사실상 **ICS 클라이언트 + TCS Agent 클라이언트 + 상태머신 + 스크립트 인터프리터 + 돔/릴레이 제어기**를 한 프로세스에 합쳐놓은 것이다. 신규 구현에서는 이 책임들을 분리(스크립트 엔진, 상태머신, 하드웨어 어댑터)하는 편이 유지보수에 유리할 수 있다 — 실제로 지금 소스도 "재사용→확장"을 반복하며 커진 흔적이 역력하다(§8).
- **`CamStatus`/`ExpStatus` 상태머신**(§6)은 ICS의 원시 텍스트 메시지 파싱에 전적으로 의존한다. 신규 ICS가 좀 더 구조화된 상태 이벤트(예: 명시적 `state` 필드가 있는 JSON)를 제공한다면, 이 파싱 로직 전체를 훨씬 단순화할 수 있다.
- **`.osc` 스크립트 포맷**(§5)은 이미 방대한 실사용 스크립트 자산(§9)이 존재하므로, 완전히 새 포맷으로 갈아엎기보다는 **호환 파서를 신규 시스템에 유지**하는 쪽이 마이그레이션 비용을 크게 줄인다.
- **Redis 도입(2023년 이후, newTCS)**은 AUX/PC-TCS 폴링을 보완/대체하는 방향으로 가고 있다는 신호다 — 신규 Python ICS/TCS 설계 시 애초에 상태 버스로 Redis(또는 유사 pub/sub)를 채택하는 것을 적극 검토할 만하다. 지금 OBSAgent가 Redis·웹릴레이·AUX 세 곳에서 돔 상태를 따로 모아 판정하는 로직(§4.5, `UpdateDomeStatus()`)은 과도기적 임시 구조로 보인다.
- 비항성추적(NST, §4.2), 시각지정 관측(UTOBS/UTTOL, §5), 포인팅 보정(`copt`/BLG offset, [tcsagent_report.md](../TCSAgent/tcsagent_report.md) 9.1절)은 전부 **공식 매뉴얼에 없거나 초안 수준으로만 언급된 핵심 운영 기능**이다. 신규 구현 전 이 세 기능은 반드시 소스코드 수준에서 재확인하고 정식 스펙으로 문서화해야 한다.
- `dtchk`, `getjd`/`getlst`/`getalt`(USNO NOVAS) 같은 유틸리티는 관측 운영에 실질적으로 필요했던 기능들이므로, 신규 시스템에서도 동등한 기능(파일 이관 점검, 천문 계산)을 어떤 형태로든 제공해야 한다.

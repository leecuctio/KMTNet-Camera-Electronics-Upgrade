# Legacy ICS / XIS(ISIS) System — Technical Reference Report

이 문서는 `ics_legacy/` 폴더에 수집된 자료(프로토콜 스펙, ICS 명령어 문서, 3개 관측소 ISIS 런타임 로그 샘플)를 바탕으로, 기존(legacy) ICS·ISIS 시스템의 아키텍처·통신 프로토콜·명령어·출력 메시지를 정리한 것이다. 신규 Python 기반 ICS 개발의 참고 자료로 사용한다.

- 대상 시스템: **ICIMACS** (Instrument Control & IMage ACquisition System, OSU 개발) 계열, KMTNet(칠레 CTIO/남아공 SAAO/호주 SSO 3개 사이트) 배포본
- 근거 자료: `IMPv2.5Protocol1.pdf`, `IC_commands_R20220302.docx`, `__sample_isislog/{isislog.ctio,isislog.saao,isislog.sso}/*.log`

---

## 1. 시스템 개요

### 1.1 ICIMACS와 KMTNet

**ICIMACS**(Instrument Control and IMage ACquisition System)는 OSU(Ohio State University)가 개발한 천문 관측기기 제어용 프로그램군의 총칭이다. 이 프로그램군은 텍스트 기반 메시징 프로토콜(IMP, 아래 2절)로 서로 통신한다.

이 폴더의 로그 샘플은 **KMTNet**(Korea Microlensing Telescope Network) 배포본으로 확인된다 — 파일명이 `KMTNx.yyyymmdd.nnnnnn.fits` 형태이고, 로그 내 상태 메시지에 `TELID=KMTC`(CTIO), `TELID=KMTS`(SSO) 값이 실제로 나타난다. 3개 사이트 각각에 동일한 구조의 시스템이 배포되어 있다:

| 사이트 코드 | 관측소 |
|---|---|
| CTIO | Cerro Tololo Inter-American Observatory (칠레) |
| SAAO | South African Astronomical Observatory (남아공) |
| SSO | Siding Spring Observatory (호주) |

각 사이트의 모자이크 카메라는 4개의 과학 채널(**K, M, T, N** — 파일 접두어 `KMTN` + 채널문자)과 1개의 가이드 채널(**G**, 파일 접두어 `KMTNg`)로 구성된다. K채널이 "master" 역할을 한다 (예: `ERASE`, `SHOPEN`, `SHCLOSE`는 K에서만 동작).

### 1.2 통신 허브: ISIS / XIS

- 스펙 문서상의 공식 명칭은 **ISIS**(Integrated Science Instrument Server)이나, 실제 배포된 실행 파일/런타임 로그에서는 자기 자신을 **XIS**로 칭한다 (`XIS runtime log (re)started at UTC ...`). 즉 이 배포본에서 ISIS 허브 프로그램의 노드 이름/바이너리 이름이 `XIS`이다.
- ISIS/XIS는 IMPv2.5 프로토콜을 사용해 여러 노드(프로그램) 사이의 메시지를 중계하는 **메시지 라우팅 허브**다.
- **노드 등록 방식**: 별도의 명시적 등록 절차 없음. 프로그램이 실행되며 XIS에 아무 메시지(보통 `PING`)를 보내는 순간 그 소스 주소(IP:port)가 해당 노드 ID로 등록된다. 동일 노드 ID로 재등록(재시작 등)이 발생하면 **최신 연결이 이전 연결을 대체**한다 — 충돌 감지나 거부 로직은 없다.

### 1.3 노드(프로그램) 디렉토리

로그에서 관측된 전체 노드 목록과 역할:

| 노드 코드 | 역할 | 비고 |
|---|---|---|
| `XIS` | 메시지 허브 (ISIS) | 전체 노드의 중앙 라우터, heartbeat/PING-PONG 처리, `TIME` 서비스 제공 |
| `ICS` | 카메라 통합 제어 (상위) | `/dev/ttyS0` 시리얼 포트로 연결된 경우가 많음. `OBS`로부터 명령을 받아 4개 과학 채널(K/M/T/N `.IC`)에 동기화된 명령을 전파 |
| `K.IC`,`M.IC`,`T.IC`,`N.IC` | 채널별 카메라 제어(Instrument Control) | 개별 CCD 노출/파일명/센서 제어. K가 master |
| `G.IC` | 가이드 채널 카메라 제어 | 과학 채널과 별도 계통 |
| `K.CB`,`M.CB`,`T.CB`,`N.CB`,`G.CB` | 채널별 Camera Body 컨트롤러 | 디스크 초기화/마운트/파일 전송(`TRANSFER`) 담당, 실측정 데이터 쓰기(`Wrote LASTFILE=...`) 보고 |
| `TC` | 망원경 제어(Telescope Control) | 좌표·상태 텔레메트리(`TSTAT`/`ASTAT`) 응답, `AUXSTATUS`/`TCSSTATUS` 소스 |
| `OBS` | 관측 시퀀서/옵저버 콘솔 | 사람 또는 스크립트가 명령을 입력하는 최상위 클라이언트. `ICS`/`TC`에 명령 발행 |
| `ICG` | 가이드 카메라 상위 제어 | `ICS`의 가이드용 대응물, `G.IC`에 명령 전파 |
| `ABC` | 자동관측 제어기 | `ICG`에 가이드 노출/`GO` 명령 발행 (자동화된 관측 스케줄러로 추정) |
| `GMON` | 모니터링 클라이언트 | `OBS`에 `sysstatus`를 초당 폴링해 카메라·망원경 통합 상태 조회 (대시보드/모니터링용) |
| `AL` / `ALL` | 브로드캐스트 예약 주소 | 모든 노드에 메시지 전파 |

포트 관례 (로그에서 관측):
- IC 계열(`*.IC`, `ICG`): TCP 6600
- CB 계열(`*.CB`): TCP 10601
- `TC`: TCP 6606
- `OBS`: TCP 6650
- `ICS`: 시리얼(`/dev/ttyS0`), 사이트에 따라 TCP일 수도 있음

---

## 2. 통신 프로토콜 — IMPv2.5

출처: `__ICIMACS/IMPv2.5Protocol1.pdf` (OSU-MODS-2008-xxx, R.W. Pogge & J.A. Mason, 2008)

### 2.1 메시지 포맷

```
src>dest Message_Type Command_Word Message_Body\r
```

- `src`, `dest`: 노드 이름 (2~8자, `[A-Z0-9._]`, 대소문자 구분 없음)
- 구분자: `>` (노드명 사이, 공백 불가), 그 외 토큰은 공백(space)으로 구분
- 종료 문자: `\r` (ASCII 13). `\n`/`\0`는 허용 안 됨 (malformed 처리)
- 최대 메시지 길이: 2048자
- `AL`/`ALL`: 브로드캐스트 예약 주소

### 2.2 메시지 타입 7종

| 타입 | 의미 | 특징 |
|---|---|---|
| `REQ:` | 명령 요청 (기본값, 생략 가능) | 양방향 — 반드시 DONE/STATUS/에러로 응답 필요 |
| `EXEC:` | 실행권한(override) 명령 요청 | 원격에서 민감 명령(QUIT 등)을 실행하려면 명시적으로 필요 |
| `DONE:` | 명령 완료 확인 | 트랜잭션 종료, 응답 불필요 |
| `STATUS:` | 진행상황/상태 정보 | 완료 아님, 응답 불필요 |
| `ERROR:` | 에러(실행 실패) | 구문/검증/실행오류 |
| `WARNING:` | 경고 (명령은 계속 진행됨) | 이후 DONE 또는 ERROR로 트랜잭션 종료 필요 |
| `FATAL:` | 심각한 오류, 물리적 개입 필요 | "안전 모드" 진입 권장 |

키보드 인터페이스 관례: 콘솔에서 타이핑한 명령은 "자기 자신에게 보내는 EXEC:" 로 취급 (예: `status` == `cam>cam EXEC: status\r`). `>NODE cmd` 축약형으로 특정 노드에 전송 가능.

### 2.3 메시지 본문 (key=value)

```
DONE: FILTER FILTPOS=1 FILTNAME='SDSS u'
ERROR: filter Requested filter 42 is out of range: must be 1..12
```

- 숫자: `key=value` (예: `Filter=3`)
- 불리언: `T`/`F` (대소문자 무관)
- 문자열: 단어 하나는 그대로, 여러 단어는 `'...'` 또는 `(...)`로 감쌈
- 상태 플래그: `+FLAG`(활성) / `-FLAG`(비활성)

### 2.4 Out-of-band 메시지

- `PING` / `PONG`: 소프트웨어 핸드셰이킹 (기동 시 자기소개, 브로드캐스트 가능)
- Heartbeat: 헤더만 있는 빈 메시지 (`tcs>isis\r`) — 노드 생존 신호

### 2.5 비정상 메시지(OoPS) 처리 원칙

- **Malformed**(헤더/종료문자 이상): 무시, 로그만 남기고 응답하지 않음. 절대 ERROR로 응답하지 않음
- **Extraneous**(프로토콜 자체를 안 따름): 무시. 비호환 장치와 통신해야 하면 별도 "filter/agent" 프로그램으로 변환
- **Oversized**(2048자 초과): malformed로 간주하되, 실무적으로는 8192바이트(BUFSIZ)까지 수용 후 프로그래머에게 오류 통지 권장

---

## 3. ICS 명령어 레퍼런스

출처: `IC_commands_R20220302.docx`

### 3.1 ICS 레벨 명령 (카메라 통합 제어)

| 명령 | 설명 |
|---|---|
| `STATUS` | ICS 설정 상태 반환 |
| `ACQSTATUS` | IC K/M/T/N 연결 및 초기화 상태 반환 |
| `FILENAME` | ICS 자체 설정 파일이름 반환 |
| `SYNCHRONIZE` | 현재 IMGTYPE/OBJNAME/EXP/OBSERVER/PROJID 값 반환. 각 IC가 기동 시 이 명령으로 ICS와 동기화 |
| `EXPNUM <n>` | 파일 일련번호 설정 (`KMTNx.yyyymmdd.nnnnnn.fits`, 6자리) |
| `TIME` | OS/FITS/RTC 시각 정보 반환 |
| `BIN <n>` | *(미구현)* CCD binning — 명령 목록에만 존재 |
| `ROI` | *(예약, 미동작)* Region of interest |
| `DISPL` | *(예약, 미동작)* |
| `LEDFLASH <x>` | 점검용 LED 점등시간(ms). 0=점등 안 함 |
| `PROJID <id>` | 관측 프로젝트 ID (FITS 헤더용, CCD 구동에는 영향 없음) |
| `OBSERVER <name>` | 관측자 이름 (띄어쓰기 허용, FITS 헤더용) |
| `EXP <x.x>` | 노출시간(EXPTIME) 설정 |
| `BIAS <objname>` | IMAGETYP=BIAS, OBJECT=<objname>. 노출 0초, 셔터 안 열림 |
| `DARK <objname>` | IMAGETYP=DARK. 셔터 안 열림 |
| `OBJECT <objname>` | IMAGETYP=OBJECT. 셔터 정상 노출 |
| `FLAT` / `SKY` / `DOMEFLAT` / `STANDARD <objname>` | 각각 해당 IMAGETYP 설정, 동작은 OBJECT와 동일 |
| `GO` | 노출 1장: configuration→flushing→integration→shutter wait→readout→FITS 저장, 진행상황 계속 보고 |
| `GO <n>` | n장 반복 노출 |
| `STOP` | *(미구현)* integration 중지 후 readout/저장 |
| `ABORT` | *(미구현)* 전체 중지, readout/저장 안 함 |
| `MOVIE` | *(미구현)* |
| `ICS>TC AUXSTATUS` / `TCSSTATUS` | ICS가 TC(TCSAgent)에 AUX/TCS 상태 요청 |

> 매개변수 생략 시 대부분 현재 설정값 반환. 대부분의 설정 명령은 ICS→각 IC로 그대로 전파되어 전체 동기화됨.

### 3.2 IC K/M/T/N 채널 레벨 명령

| 명령 | 설명 |
|---|---|
| `STATUS` | 해당 채널 설정 상태 반환 |
| `DMAWAIT <n>` | Optical fiber 통신 지연 설정 (저장 오류 완화용) |
| `DATASOURCE <ADC\|CTC>` | onboard crosstalk 보정: ADC=원본 그대로, CTC=보정 후 전송 |
| `LEDFLASH <x>` | *(현재 기능 없음)* |
| `FILENAME` | 해당 채널 저장 파일이름 반환 |
| `EXPNUM <n>` | 채널 자체 파일 일련번호 (**4자리**, `KMTNx.yyyymmdd.nnnn.fits`) — ICS의 6자리와 자릿수가 다름 (3.4절 참고) |
| `INITIALIZE <suffix>` | 파일명 suffix를 임의로 전체 설정 (`KMTNx.<suffix>.fits`). 보통 ICS가 날짜+6자리 번호를 만들어 각 IC에 이 명령으로 동기화 |
| `ERASE` | CCD flushing 시작. **K(master)에서만 동작** |
| `SHOPEN <x.x> [<sourceID> USESTATUS]` | 셔터 개방 x.x초. sourceID 지정 시 남은시간 STATUS 주기 보고. **K master만** |
| `SHCLOSE` | 셔터 즉시 닫기 (강제 중단용). **K master만** |
| `FLASHNOW <n>` | LED n시간만큼 점등 |
| `GO <sourceID>` | 채널 readout 시작 (M/N/T에 먼저 명령 후 마지막에 K master) |
| `TIME` | 시각 정보 반환 |
| `PROJID` / `OBSERVER` / `EXP` / `BIAS` / `DARK` / `OBJECT` / `FLAT` / `SKY` / `DOMEFLAT` / `STANDARD` | ICS 레벨과 동일 의미, 채널 단위로 적용 |
| `ICS>K/M/T/N.IC STATUS: AUXSTATUS ..` | ICS가 보내는 AUX 상태 — 채널이 저장해두었다가 FITS 헤더에 기록 |
| `ICS>K/M/T/N.IC STATUS: TCSSTATUS ..` | 상동, TCS 상태 |

### 3.3 표준 관측 시퀀스 예시 (문서 원문)

```
LEDFLASH 20000
PROJID ENG
OBJECT led
EXP 10

EXPNUM or INITIALIZE
  EXPNUM n                (suffix가 yyyymmdd.####으로 설정됨. ####에 n이 들어감)
  INITIALIZE <suffix>     (suffix는 아무거나 넣을 수 있음. 관측에서는 20190624.000001와 같이 넣어줌)
ERASE
SHOPEN 10 (or SHOPEN 10 OBS USESTATUS)
FLASHNOW 20000
GO (or GO OBS)
```

SHOPEN 전후로 `STATUS: AUXSTATUS ..` / `STATUS: TCSSTATUS ..`를 보내면 해당 정보가 FITS 헤더용으로 기록된다.

### 3.4 알려진 캐비어트 / 운영 노트 (문서 개정이력에서)

- **자릿수 불일치**: ICS는 6자리(`nnnnnn`), 개별 IC는 4자리(`nnnn`) 일련번호 사용. IC에서 6자리로 맞추려면 `EXPNUM` 대신 `INITIALIZE <전체suffix>`를 써야 함 — 관측에서는 항상 ICS가 `INITIALIZE`로 날짜+6자리를 각 IC에 내려 동기화한다.
- `LEDFLASH` 관련 이슈가 SAAO 현장 테스트(2018-03-15)에서 보고됨: OSU 원본 코드에서 문제였던 현상이 재현 안 됨 (IC2.img 버전 차이로 추정), `LEDFLASH 0` 설정도 문제없이 동작 확인됨.
- `OBSAgent`에 `ACQSTATUS`, `EXPNUM` 명령 그룹 추가 필요 (미해결 항목으로 문서에 기록됨).
- `BIN`, `ROI`, `DISPL`, `STOP`, `ABORT`, `MOVIE`는 명령어 리스트/파서에는 존재하나 실제 구현되어 있지 않음 — 신규 구현 시 "명령이 정의돼 있다고 곧 동작한다는 뜻은 아님"을 유의해야 함.

---

## 4. 실측 로그 기반 관측 트랜잭션 분석

출처: `IC_commands_R20220302.docx`에 포함된 `isis.20171110.log` 발췌 + `__sample_isislog/isislog.{ctio,saao,sso}/*.log`

### 4.1 기동 시퀀스 (PING/PONG 등록)

```
XIS runtime log (re)started at UTC 2024-01-01T23:12:49.915355
2024-01-01T23:12:49.915360 [192.168.14.108:6606] TC>AL ping
2024-01-01T23:12:49.915387 XIS>TC PONG
2024-01-01T23:12:49.915742 [192.168.14.104:10601] T.CB>TC PONG
2024-01-01T23:12:49.915788 [192.168.14.103:10601] M.CB>TC PONG
...
```

`TC`가 `AL`(브로드캐스트)로 `ping`을 보내면, 각 노드가 순서대로 `PONG`으로 응답하며 자연스럽게 XIS에 등록된다 (2.2절 "노드 등록 방식" 참고). 소문자 `ping`도 대문자 `PING`과 동일하게 처리됨 — 실제 구현은 명령어 대소문자를 구분하지 않는다(스펙상 key=value의 T/F만 명시적으로 대소문자 무관이라 되어 있으나, 실측 로그상 커맨드 워드 자체도 case-insensitive로 동작).

### 4.2 DARK 노출 전체 트랜잭션 (K채널, 문서 부록에서)

```
OBS>ICS projid obs               → ICS>OBS DONE: PROJID  ProjID=OBS         (ICS가 K.IC에도 전파)
OBS>ICS dark begin                → ICS>OBS DONE: DARK  ImageType=DARK ObjectName='begin' EXP=30
OBS>ICS exp 30                    → ICS>OBS DONE: EXP  ExpTime=30 seconds.
OBS>ICS go
  ICS>K.IC INITIALIZE 20171111.050722
    K.IC>ICS DONE: INITIALIZE  Initialization Complete.
  ICS>K.IC ERASE                                  (( K only ))
  ICS>K.IC STATUS: AUXSTATUS  ENS7=... FASTAT=STANDBY ... EXPSTATUS=ERASE
    K.IC>ICS DONE:   Erase Cycle Complete.
  ICS>K.IC STATUS: TCSSTATUS  DATE-OBS=... RA=... DEC=... EXPSTATUS=INTEGRATING
  ICS>K.IC GO OBS                                 (( after GO OBS to M.IC/N.IC/T.IC ))
    K.IC>ICS STATUS: GO
    K.IC>OBS STATUS: GO  PCTREAD=6 .. 17 .. 28 .. ... 94   (( only to sourceID ))
    K.IC>OBS STATUS: GO  PCTREAD=100 Acquisition Complete. Disk Transfer Starting.
    K.IC>ICS STATUS: GO  Acquisition Complete
  ICS>OBS DONE:   EXPSTATUS=IDLE
  K.IC>K.CB TRANSFER DISK1 1 ICS
  K.IC>XIS PING  →  XIS>K.IC PONG
  K.IC>ICS STATUS: GO  Disk Write Complete        (( XIS PONG 응답 이후 ))
  K.CB>ICS DONE: Wrote LASTFILE=/mnt/ICSData/KMTNk.20171111.050722.fits RATE=408038 KB/sec
  K.CB>K.IC DONE DISK1 1
  K.CB>K.IC REQ SWAP  →  K.IC>K.CB ACK SWAP
```

**해석 포인트**
- `OBS`는 오직 `ICS`(시리얼)/`TC`에만 명령하고, 개별 채널(`K.IC` 등)과는 직접 통신하지 않는다 — ICS가 4개 과학 채널에 명령을 "부채꼴로" 전파하는 중계자 역할.
- `GO`는 `M.IC`/`N.IC`/`T.IC`에 먼저 내려간 뒤 마지막에 K(master)에 내려간다. K가 readout 진행률(`PCTREAD=`)을 요청자(sourceID, 여기선 `OBS`)에게만 보고한다.
- 노출 상태 머신은 `AUXSTATUS`/`TCSSTATUS`의 `EXPSTATUS` 필드로 추적 가능: `ERASE → INTEGRATING → READOUT → WRITING/IDLE`.
- 파일 쓰기 완료는 `K.IC`가 아니라 `K.CB`(카메라 바디 컨트롤러)가 `DONE: Wrote LASTFILE=...`로 보고한다. 디스크는 `DISK0`/`DISK1` 이중화되어 있고, 쓰기 후 `REQ SWAP`/`ACK SWAP`으로 다음 노출을 위해 디스크를 교대한다.
- `K.IC>XIS PING`/`PONG` 왕복은 실제 파일 전송(disk write) 완료를 알리는 타이밍 신호로 재사용되고 있다 (`STATUS: GO Disk Write Complete    (( after PONG response from XIS ))`) — 프로토콜 스펙에는 없는, 이 배포본만의 관례적 사용법.

### 4.3 가이드 채널(G) / 자동관측(ABC↔ICG) 트랜잭션

```
abc>icg guideexp 10        →  ICG>ABC DONE: GUIDEEXP  GuideExp=10 seconds.
                               ICG>G.IC GUIDEEXP 10 → G.IC>ICG DONE: GUIDEEXP  GuideExp=10 seconds.
abc>icg go
  ICG>G.IC INITIALIZE 20240102T002045
  ICG>ABC STATUS: GO   EXPSTATUS=INITIALIZING
  ICG>G.IC GO 1 ABC
  G.IC>ABC STATUS: GO   EXPSTATUS=INTEGRATING
  G.IC>ABC STATUS: GO   EXPSTATUS=READOUT
  G.IC>ABC STATUS: GO  Acquisition Complete  EXPSTATUS=WRITING
  G.IC>G.CB  TRANSFER DISK0 4 ABC
  G.CB>ABC DONE: Wrote LASTFILE=/mnt/ICSData/KMTNgs.20240102T002045.0001.fits RATE=634908 KB/sec
```

가이드 채널은 과학 채널(K/M/T/N)과 완전히 분리된 병렬 계통이다: `ICG`가 `ICS`의 역할을, `ABC`가 `OBS`의 역할을 한다. 파일명 형식도 다르다(`KMTNgs.<timestamp>.<seq>.fits`, ISO 타임스탬프 기반 suffix).

### 4.4 모니터링 (GMON)

```
gmon>obs sysstatus
OBS>GMON DONE: CamStatus=READY FitsSaved=1 ExpSet=0 ExpRem=0 TelStatus=TRACKINGS
  RA=03:44:13.15 DEC=-16:02:53.1 ... TELID=KMTC FILTER=V SHUTTER=CLOSED FOCUS=-1.105 ... FAN=ON
```

`GMON`은 초당 `sysstatus`를 `OBS`에 폴링해 카메라·망원경 통합 상태를 하나의 요약 메시지로 받는다 (대시보드/모니터링 전용 경량 조회 채널로 추정, 명령어 문서에는 없고 로그에서만 확인됨).

---

## 5. 출력 메시지 / 에러 패턴 (실제 로그 기반)

### 5.1 정상 완료(DONE) 예시

```
DONE: DMAWAIT  DMAWaitTime=500
DONE: DATASOURCE   DataSource=ADC
DONE: LEDFLASH  LEDFlashTime=1
DONE: PROJID  ProjID=OBS
DONE: EXP  ExpTime=30 seconds.
DONE: INITIALIZE  Initialization Complete.
DONE:   Erase Cycle Complete.
DONE: Wrote LASTFILE=/mnt/ICSData/KMTNk.20171111.050722.fits RATE=408038 KB/sec
```

### 5.2 진행상황(STATUS) — GO 시퀀스

```
STATUS: GO
STATUS: GO  PCTREAD=xx                                            (( only to sourceID ))
STATUS: GO  PCTREAD=100 Acquisition Complete. Disk Transfer Starting.  (( only to sourceID ))
STATUS: GO  Acquisition Complete
STATUS: GO  Disk Write Complete    (( XIS PONG 응답 후 ))
```

### 5.3 상태 덤프 — AUXSTATUS / TCSSTATUS (FITS 헤더용 텔레메트리)

```
STATUS: AUXSTATUS  ENS7=0.0 ENS6=19.2 ... ENFAN=OFF ENSTAT=STANDBY CHSTAT=NC MCPOS=0 MCSTAT=STANDBY
  DSSTAT=NC FAPOSW=-4.222 FAPOSE=-7.187 FAPOSS=-5.631 FASTAT=STANDBY
  SHUTTER=CLOSED SHUTOP=STANDBY FILTER=V FILNUM=3 FILTOP=STANDBY FSSTAT=STANDBY
  AUXUDATE=... AUXARC=Enabled AUXLINK=Up TELID=KMTS TIMESYS=UTC
  KBUILD=... MBUILD=... TBUILD=... NBUILD=... GBUILD=... ICSBUILD=... EXPSTATUS=ERASE

STATUS: TCSSTATUS  DATE-OBS=... EXECODE=E TCSDRIVE=Disabled TCSLIMIT=No TELMOVE=Idle
  AZ=0.0 ALT=90.0 SECZ=1.00 ST=05:20:19 HA=+00:00:00 EQUINOX=2000.000
  DEC=-32:13:39.5 RA=05:19:44.75 TCSARC=Enabled TCSLINK=Up EXPSTATUS=INTEGRATING
```

이 두 메시지는 ICS가 각 채널(`K.IC` 등)에 주기적으로 전달하며, 채널은 이를 그대로 저장해두었다가 FITS 파일 저장 시 헤더에 기록한다(3.2절). `EXPSTATUS` 필드가 트랜잭션 전체의 상태 머신을 나타낸다.

### 5.4 에러(ERROR) 패턴 — 실제 발생 사례

```
ICS>OBS ERROR: EXP  Cannot change EXPTIME for ImgType=BIAS
```
→ IMAGETYP이 BIAS로 설정된 상태에서 `EXP`(노출시간) 변경을 시도하면 거부됨 (BIAS는 정의상 0초 고정). ICS→전 채널로 동일 에러가 전파된다.

```
G.IC>ABC ERROR: GO  DMA WAIT TIMEOUT. EXPOSURES ABORTED. EXPSTATUS=ERROR
```
→ 가이드 채널에서 DMA(광케이블) 응답 타임아웃 시 발생, 자동으로 노출이 중단되고 `EXPSTATUS=ERROR`로 천이. 로그 샘플에서 반복적으로 (수 분 간격) 발생한 사례가 다수 확인됨 — 운영 중 흔한 장애 패턴으로 보인다.

### 5.5 경고(WARNING) 패턴 — 파일명 충돌

```
K.CB>OBS WARNING: FITS file '/mnt/ICSData/KMTNk.20250902.050666.fits' already exists, writing as '/mnt/ICSData/250902.000.fits' instead
```
→ 계산된 파일명이 이미 존재할 경우, 덮어쓰지 않고 대체 파일명(`<yymmdd>.<순번>.fits`)으로 자동 저장 후 WARNING으로 통지. 데이터 유실 방지 목적의 안전장치.

> 샘플 로그 전체(9개월치, 3개 사이트)에서 `FATAL:` 메시지는 관측되지 않았다 — 실제 운영 중 물리적 개입이 필요한 심각 오류는 드물게 발생하거나 별도 채널로 처리되는 것으로 보인다.

---

## 6. 참고 원본 자료 색인

| 경로 | 내용 |
|---|---|
| `IC_commands_R20220302.docx` | ICS/IC 명령어 정식 레퍼런스, 예시 시퀀스, 운영 노트 (2022-03-02 개정) |
| `CCD status (20220826.emaitoSET).pdf` | CCD 상태 관련 문서 (미검토) |
| `__ICIMACS/IMPv2.5Protocol1.pdf` | IMPv2.5 프로토콜 정식 스펙 (OSU, 2008) |
| `__ICIMACS/obsguide.pdf` / `.ps` | 관측 가이드 |
| `__ICIMACS/SPIE_ICIMACS_560_1.pdf` | ICIMACS 관련 SPIE 논문 |
| `__ICIMACS/ISISclient docu/*.pdf` | MODS(OSU) 참조 구현의 ISIS 클라이언트 라이브러리 Doxygen 문서 (`isisclient.cpp/h`, `dispatcher.cpp/h`) — 원조 C++ 클라이언트 아키텍처 참고용 |
| `__ICIMACS/original codes/ISISclient.zip`, `pctcs.zip` | 원본 소스코드 (미검토, 필요시 추가 분석 가능) |
| `__ICIMACS/osu etc/mosaic.pdf` 등 | OSU 모자이크 카메라 관련 부속자료 |
| `__sample_isislog/isislog.{ctio,saao,sso}/isis.*.log` | 3개 사이트, 2024~2025년 실제 ISIS 런타임 로그 샘플 (본 보고서 4~5절의 실측 근거) |

---

## 7. 신규 Python ICS 개발 시 고려사항 (메모)

- 프로토콜(IMPv2.5)은 언어/OS 무관, ASCII 텍스트 기반이라 Python 소켓 구현에 특별한 장벽 없음. `\r` 종료, 최대 2048자, `key=value` 파싱만 구현하면 됨.
- 노드 등록에 별도 API가 없으므로, 신규 구현도 "연결 후 PING" 만으로 XIS(ISIS)에 등록되는 기존 관례를 그대로 따라야 상호운용 가능.
- 문서상 "미구현"으로 명시된 명령(`BIN`,`ROI`,`DISPL`,`STOP`,`ABORT`,`MOVIE`)은 legacy에서도 동작하지 않았던 것이므로, 신규 구현 시 이를 실제로 구현할지 legacy와 동일하게 스텁으로 둘지 결정 필요.
- `EXPNUM`(4자리, 채널) vs `EXPNUM`(6자리, ICS) 자릿수 불일치는 `INITIALIZE`로 우회하는 것이 legacy의 실제 운영 방식 — 신규 구현에서는 애초에 자릿수를 통일하는 것을 검토할 만함.
- `K.IC>XIS PING/PONG` 을 디스크 쓰기 완료 타이밍 신호로 쓰는 관례(4.2절)는 프로토콜 스펙에 없는 legacy 특유의 관행이므로, 신규 구현에서 그대로 가져갈지 명시적 완료 신호로 대체할지 검토 필요.

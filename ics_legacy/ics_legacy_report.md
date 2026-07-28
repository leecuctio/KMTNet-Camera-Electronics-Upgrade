# Legacy ICS / XIS(ISIS) System — Technical Reference Report

이 문서는 `ics_legacy/` 폴더에 수집된 자료(프로토콜 스펙, ICS 명령어 문서, 3개 관측소 ISIS 런타임 로그 샘플)를 바탕으로, 기존(legacy) ICS·ISIS 시스템의 아키텍처·통신 프로토콜·명령어·출력 메시지를 정리한 것이다. 신규 Python 기반 ICS 개발의 참고 자료로 사용한다.

- 대상 시스템: **ICIMACS** (Instrument Control & IMage ACquisition System, OSU 개발) 계열, KMTNet(칠레 CTIO/남아공 SAAO/호주 SSO 3개 사이트) 배포본
- 근거 자료: `IMPv2.5Protocol1.pdf`, `IC_commands_R20220302.docx`, `__sample_isislog/{isislog.ctio,isislog.saao,isislog.sso}/*.log`

---

## 1. 시스템 개요

### 1.1 ICIMACS와 KMTNet

**ICIMACS**(Instrument Control and IMage ACquisition System)는 OSU(Ohio State University)가 개발한 천문 관측기기 제어용 프로그램군의 총칭이다. 이 프로그램군은 텍스트 기반 메시징 프로토콜(IMP, 아래 2절)로 서로 통신한다.

이 폴더의 로그 샘플은 **KMTNet**(Korea Microlensing Telescope Network) 배포본으로 확인된다 — 로그에 기록된 관측 데이터 파일명이 `KMTNx.yyyymmdd.nnnnnn.fits` 형태이고(1.2절 참고), 로그 내 상태 메시지에 `TELID=KMTC`(CTIO), `TELID=KMTS`(SSO) 값이 실제로 나타난다. 3개 사이트 각각에 동일한 구조의 시스템이 배포되어 있다:

| 사이트 코드 | 관측소 |
|---|---|
| CTIO | Cerro Tololo Inter-American Observatory (칠레) |
| SAAO | South African Astronomical Observatory (남아공) |
| SSO | Siding Spring Observatory (호주) |

각 사이트의 카메라는 **과학 CCD 4개(K, M, T, N — 파일 접두어 `KMTN` + CCD ID 문자)와 가이드 CCD 4개**로 구성된다. 과학 CCD는 디바이스 별로 각각의 `.IC`/`.CB` 노드(`K.IC`,`M.IC`,...)를 갖지만, **가이드 CCD 4개는 소프트웨어적으로 단일 노드 `G.IC` 하나가 통합 제어**한다(개별 가이드 CCD마다 별도 노드가 있는 것이 아님). K가 과학 CCD의 "master" 역할을 한다 (예: `ERASE`, `SHOPEN`, `SHCLOSE`는 K에서만 동작).

> **용어 구분 주의**: 여기서 "K/M/T/N/G" 구분자는 서로 다른 CCD(물리적 detector 단위)를 가리키는 이 보고서의 용어다. 이와 별도로 각 CCD는 **리드아웃 채널(amplifier)** 단위로 병렬 판독되는데, legacy 시스템 기준 **과학 CCD 1개당 8개, 가이드 CCD 1개당 2개**의 리드아웃 채널로 운영된다 — `x.IC`(예 `K.IC`)와 거기 연결된 컨트롤러 하드웨어가 CCD 1개의 리드아웃 채널 최대 8개를 처리하는 단위다. (참고: 신규 STA Archon 기반 업그레이드 시스템은 CCD당 리드아웃 채널 수가 다르다 — [../README.md](../README.md)의 "amplifier 64개(과학 CCD 4개 기준)" 참고, 이는 legacy와 무관한 신규 시스템 스펙이다.)

### 1.2 통신 허브: ISIS / XIS

- 스펙 문서상의 공식 명칭은 **ISIS**(Integrated Science Instrument Server)이나, 실제 배포된 실행 파일/런타임 로그에서는 자기 자신을 **XIS**로 칭한다 (`XIS runtime log (re)started at UTC ...`). 즉 이 배포본에서 ISIS 허브 프로그램의 노드 이름/바이너리 이름이 `XIS`이다.
- ISIS/XIS는 IMPv2.5 프로토콜을 사용해 여러 노드(프로그램) 사이의 메시지를 중계하는 **메시지 라우팅 허브**다.
- **노드 등록 방식**: 별도의 명시적 등록 절차 없음. 프로그램이 실행되며 XIS에 아무 메시지(보통 `PING`)를 보내는 순간 그 소스 주소(IP:port)가 해당 노드 ID로 등록된다. 동일 노드 ID로 재등록(재시작 등)이 발생하면 **최신 연결이 이전 연결을 대체**한다 — 충돌 감지나 거부 로직은 없다.
- **로깅 구조**: **ICS는 자체 로그 파일을 남기지 않는다.** 모든 노드 간 메시지는 허브인 XIS를 거쳐가므로, XIS가 자신을 지나는 모든 트랜잭션을 하나의 런타임 로그로 기록한다(`__sample_isislog/isislog.{ctio,saao,sso}/isis.*.log`). 따라서 **ICS(또는 다른 어떤 노드)의 동작을 분석하려면 그 노드 자신의 로그가 아니라 XIS 로그를 참고해야 한다** — 이 보고서 4~5절의 모든 트랜잭션 분석도 XIS 로그 기준이다.
  - `KMTNx.yyyymmdd.nnnnnn.fits` 파일명은 ICS가 실제로 획득한 **관측 영상 데이터 파일**이지 로그가 아니다. 이 저장소에는 그 실물 FITS 파일이 없고, XIS 로그에는 `K.CB>ICS DONE: Wrote LASTFILE=/mnt/ICSData/KMTNk.....fits RATE=... KB/sec` 형태로 "그 파일이 이런 이름/속도로 쓰였다"는 메시지만 기록된다(5.1절 참고).

### 1.3 노드(프로그램) 디렉토리

로그에서 관측된 전체 노드 목록과 역할:

| 노드 코드 | 역할 | 비고 |
|---|---|---|
| `XIS` | 메시지 허브 (ISIS) | 전체 노드의 중앙 라우터, heartbeat/PING-PONG 처리, `TIME` 서비스 제공 |
| `ICS` | 카메라 통합 제어 (상위) | `/dev/ttyS0` 시리얼 포트로 연결된 경우가 많음. `OBS`로부터 명령을 받아 4개 과학 CCD(K/M/T/N `.IC`)에 동기화된 명령을 전파 |
| `K.IC`,`M.IC`,`T.IC`,`N.IC` | 디바이스별 카메라 제어(Instrument Control) | 개별 CCD 노출/파일명/센서 제어. K가 master |
| `ICG` | 가이드 카메라 상위 제어 | `ICS`의 가이드용 대응물, `G.IC`에 명령 전파 |
| `G.IC` | 가이드 CCD 4개 통합 제어 | 과학 CCD와 별도 계통. 가이드 CCD 4개를 이 노드 하나가 전부 제어 (개별 가이드 CCD별 노드 없음) |
| `K.CB`,`M.CB`,`T.CB`,`N.CB`,`G.CB` | 디바이스별 Camera Body 컨트롤러 | 디스크 초기화/마운트/파일 전송(`TRANSFER`) 담당, 실측정 데이터 쓰기(`Wrote LASTFILE=...`) 보고 |
| `TC` | 망원경 제어(Telescope Control) | 좌표·상태 텔레메트리(`TSTAT`/`ASTAT`) 응답, `AUXSTATUS`/`TCSSTATUS` 소스 |
| `OBS` | 관측 시퀀서/옵저버 콘솔 | 사람 또는 스크립트가 명령을 입력하는 최상위 클라이언트. `ICS`/`TC`에 명령 발행 |
| `ABC` | 자동관측 제어기 | `ICG`에 가이드 노출/`GO` 명령 발행 (자동화된 관측 스케줄러로 추정) |
| `GMON` | 모니터링 클라이언트 | `OBS`에 `sysstatus`를 초당 폴링해 카메라·망원경 통합 상태 조회 (대시보드/모니터링용) |
| `AL` / `ALL` | 브로드캐스트 예약 주소 | 모든 노드에 메시지 전파 |

포트 관례 (로그에서 관측):
- IC 계열(`*.IC`, `ICG`): 6600
- CB 계열(`*.CB`): 10601
- `TC`: 6606
- `OBS`: 6650
- `ICS`: 시리얼(`/dev/ttyS0`), 사이트에 따라 소켓일 수도 있음

> **전송 계층은 TCP가 아니라 UDP다** (근거: `ISISclient.zip`의 `isissocket.c`, 아래 7절 참고). 각 노드는 `SOCK_DGRAM` 소켓 하나를 자기 포트에 bind하고 `sendto`/`recvfrom`으로만 통신한다 — 연결(connection) 개념 자체가 없다. 1.2절의 "노드 등록/대체" 동작은 사실 이 UDP 특성의 직접적 결과다: XIS는 단지 "노드ID → 가장 최근에 그 ID로 데이터그램을 보낸 (IP,port)" 매핑 테이블을 유지할 뿐이고, 같은 ID로 새 데이터그램이 오면 그 주소로 덮어쓴다. TCP처럼 세션을 맺고 끊는 절차가 없으니 "충돌 감지·거부"라는 개념 자체가 성립하지 않는다.

### 1.4 ICIMACS 아키텍처의 기원 (1998 SPIE 논문, `SPIE_ICIMACS_560_1.pdf`)

노드 이름·디스크 이중화 패턴 등 지금 KMTNet 배포본에 남아있는 관례들이 어디서 비롯됐는지, 1998년 OSU의 원조 ICIMACS 발표 논문(Atwood, Mason, et al., SPIE Vol. 3355)으로 확인된다.

- **노드 이름의 유래**: 원래 ICIMACS는 PC/Unix 혼합 네트워크로, 역할별 컴퓨터에 다음과 같은 이름을 붙였다 — `IC`(**I**nstrument **C**omputer, 검출기 시퀀서 구동·실시간 처리), `HE`(**H**ead **E**lectronics, 검출기/셔터/LED 신호 처리), `IE`(**I**nstrument **E**lectronics, 메커니즘 모터 제어), `WC`(**W**orkstation **C**omputer, Unix 워크스테이션과의 이더넷 연결 + FITS 변환), `CB`(**C**aliban 프로그램, WC와 Sparcstation 사이 SCSI 버스의 데이터를 Sparcstation 파일시스템으로 옮기는 프로그램). **KMTNet의 `K.IC`/`K.CB` 노드 이름은 바로 이 `IC`/`CB` 계보를 그대로 물려받은 것.**
- **디스크 이중화의 유래**: 1998년 당시 SCSI-2(10Mbyte/sec) 버스 한 쌍에 디스크 2개를 연결해, 한쪽에 쓰는 동안 다른 쪽을 읽어 스왑하는 방식으로 "헤드 재배치 시간"을 감추는 성능 최적화였다. **지금 KMTNet 로그의 `DISK0`/`DISK1` + `TRANSFER`/`REQ SWAP`/`ACK SWAP` 패턴(4.2절)은 이 1998년 SCSI 하드웨어 제약의 논리적 흔적**이다 — `mnt/ICSData`처럼 네트워크 스토리지를 쓰는 지금 환경에서는 원래의 성능상 이유가 그대로 적용되지 않을 가능성이 크다.
- **초기 메시지 프로토콜(IMPv1 원형)**: 이 논문이 설명하는 프로토콜은 `주소헤더 메시지\r` 형태(`XX>YY`, 2글자 고정 노드명)에 `STATUS/DONE/WARNING/ERROR/FATAL` 5종 메시지 타입만 있고 `REQ:`/`EXEC:`는 아직 없다 — IMPv2.5(2절)의 시조 격인 초기 버전.
- **`OBS`의 원조는 Ariel/Prospero**: 논문에서 언급된 사용자 인터페이스 프로그램 "Ariel"과 "Prospero"(Unix 워크스테이션에서 대화형으로 명령을 내리는 프론트엔드, `obsguide.pdf` 참고)가 지금 KMTNet의 `OBS` 노드 역할의 원형이다.

**참고 (`obsguide.pdf`, Prospero Observer's Guide, 1999)**: KMTNet 원본이 아니라 다른 OSU 계측기(OSIRIS@CTIO)용 관측자 가이드지만, 지금 KMTNet 로그에서 관측된 관례의 원조를 확인할 수 있었다 — 5.5절에서 정리한 "파일명이 이미 존재하면 대체 파일명으로 저장 후 WARNING" 안전장치가, 이 문서에 설명된 1999년 당시 Prospero의 "fail-safe unique name" 관례(`YYMMDD` + 2글자 계측기 코드 + base-36 확장자)와 동일한 설계 원칙이다.

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
| `ICS>TC AUXSTATUS` / `TCSSTATUS` | ICS가 TC(TCSAgent)에 AUX/TCS 상태 요청 — 목적과 정확한 시점은 5.3절 참고 |

> 매개변수 생략 시 대부분 현재 설정값 반환. 대부분의 설정 명령은 ICS→각 IC로 그대로 전파되어 전체 동기화됨.

### 3.2 IC K/M/T/N 디바이스별 명령

| 명령 | 설명 |
|---|---|
| `STATUS` | 해당 CCD 설정 상태 반환 |
| `DMAWAIT <n>` | Optical fiber 통신 지연 설정 (저장 오류 완화용) |
| `DATASOURCE <ADC\|CTC>` | onboard crosstalk 보정: ADC=원본 그대로, CTC=보정 후 전송 |
| `LEDFLASH <x>` | *(현재 기능 없음)* |
| `FILENAME` | 해당 CCD 저장 파일이름 반환 |
| `K/M/T/N.IC>ICS SYNCHRONIZE` | 자신(IC)이 `ICS`로 `SYNCHRONIZE` 요청을 보내, 돌아오는 `DONE: SYNCHRONIZE IMGTYPE=... OBJNAME=... EXP=... OBSERVER=... PROJID=...` 값으로 스스로를 동기화. **다만 이 요청을 먼저 보내지 않아도, `ICS`가 아닌 제3의 호스트에서든 `DONE: SYNCHRONIZE ...` 메시지가 들어오면 그걸로 동기화가 이루어진다** — 즉 IC 쪽은 요청-응답이 아니라 "그 형태의 메시지가 오면 무조건 반영"하는 수동적 리스너에 가깝다 |
| `EXPNUM <n>` | CCD 자체 파일 일련번호 (**4자리**, `KMTNx.yyyymmdd.nnnn.fits`) — ICS의 6자리와 자릿수가 다름 (3.4절 참고) |
| `INITIALIZE <suffix>` | 파일명 suffix를 임의로 전체 설정 (`KMTNx.<suffix>.fits`). 보통 ICS가 날짜+6자리 번호를 만들어 각 IC에 이 명령으로 동기화 |
| `ERASE` | CCD flushing 시작. **K(master)에서만 동작** |
| `SHOPEN <x.x> [<sourceID> USESTATUS]` | 셔터 개방 x.x초. sourceID 지정 시 남은시간 STATUS 주기 보고. **K master만** |
| `SHCLOSE` | 셔터 즉시 닫기 (강제 중단용). **K master만** |
| `FLASHNOW <n>` | LED n시간만큼 점등 |
| `GO <sourceID>` | CCD readout 시작 (M/N/T에 먼저 명령 후 마지막에 K master) |
| `TIME` | 시각 정보 반환 |
| `PROJID` / `OBSERVER` / `EXP` / `BIAS` / `DARK` / `OBJECT` / `FLAT` / `SKY` / `DOMEFLAT` / `STANDARD` | ICS 레벨과 동일 의미, CCD 단위로 적용 |
| `ICS>K/M/T/N.IC STATUS: AUXSTATUS ..` | ICS가 보내는 AUX 상태 — 해당 CCD가 저장해두었다가 FITS 헤더에 기록 |
| `ICS>K/M/T/N.IC STATUS: TCSSTATUS ..` | 상동, TCS 상태 |

### 3.3 표준 관측 시퀀스 예시

**(1) 장비 점검용 LED 프로젝터 시험 시퀀스 (문서 원문)**

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

SHOPEN 전후로 `STATUS: AUXSTATUS ..` / `STATUS: TCSSTATUS ..`를 보내면 해당 정보가 FITS 헤더용으로 기록된다 (정확한 시점은 5.3절 참고).

**(2) 실제 서베이 관측 시퀀스 — BLG(Bulge) 필드**

위 예시는 장비 점검용 LED 시험 촬영이고, 실제 KMTNet 마이크로렌징 서베이 관측은 이런 형태다(`OBS`가 사람 대신 스크립트/자동 스케줄러로 명령을 발행):

```
ProjID BLG
OBJECT BLG11
exp 60.0
Go
```

`BLG11`, `BLG12`, ... 처럼 `OBJECT` 값을 서베이 필드 코드로 바꿔가며 반복 노출하는 것이 실제 관측의 기본 패턴이다. 이 명령 4줄만으로는 실제로 오가는 전체 메시지(각 CCD로의 전파, `INITIALIZE`/`ERASE`/`SHOPEN`/`GO` 전개, 완료 보고 등)를 다 보여주지 못한다 — **실제 전체 트랜잭션과 정확한 명령어 시퀀스·타이밍은 이 예시가 아니라 4.3절의 실측 로그 트랜잭션과 `__sample_isislog/` 원본 로그를 참고할 것.** 필드마다, 노출시간마다, 사이트마다 세부 흐름이 조금씩 다를 수 있다.

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

### 4.2 DARK 노출 전체 트랜잭션 (K, 문서 부록에서)

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
- `OBS`는 오직 `ICS`(시리얼)/`TC`에만 명령하고, 개별 CCD(`K.IC` 등)과는 직접 통신하지 않는다 — ICS가 4개 과학 CCD에 명령을 "부채꼴로" 전파하는 중계자 역할.
- `GO`는 `M.IC`/`N.IC`/`T.IC`에 먼저 내려간 뒤 마지막에 K(master)에 내려간다. K가 readout 진행률(`PCTREAD=`)을 요청자(sourceID, 여기선 `OBS`)에게만 보고한다.
- 노출 상태 머신은 `AUXSTATUS`/`TCSSTATUS`의 `EXPSTATUS` 필드로 추적 가능: `ERASE → INTEGRATING → READOUT → WRITING/IDLE`.
- 파일 쓰기 완료는 `K.IC`가 아니라 `K.CB`(카메라 바디 컨트롤러)가 `DONE: Wrote LASTFILE=...`로 보고한다. 디스크는 `DISK0`/`DISK1` 이중화되어 있고, 쓰기 후 `REQ SWAP`/`ACK SWAP`으로 다음 노출을 위해 디스크를 교대한다.
- `K.IC>XIS PING`/`PONG` 왕복은 실제 파일 전송(disk write) 완료를 알리는 타이밍 신호로 재사용되고 있다 (`STATUS: GO Disk Write Complete    (( after PONG response from XIS ))`) — 프로토콜 스펙에는 없는, 이 배포본만의 관례적 사용법.

### 4.3 실제 과학 노출(BLG 서베이 필드) 트랜잭션 — 자동 가이딩 연동

출처: `__sample_isislog/isislog.ctio/isis.20240303.log` (2024-03-04 UTC 06:49~06:51 구간, CTIO 사이트). 3.3절 (2)의 개략 예시를 실제 로그로 완전히 펼친 것이다.

```
OBS>ICS OBJECT BLG11          → ICS>OBS DONE: OBJECT  ImageType=OBJECT ObjectName='BLG11' EXP=10   (ICS가 K/M/T/N.IC에도 전파)
OBS>ICS exp 60.0               → ICS>OBS DONE: EXP  ExpTime=60 seconds.
OBS>ICS Go
  ICS>G.IC INITIALIZE 20240304T064947
  ICS>K.IC INITIALIZE 20240304.039497                 (( M/T/N도 동일 ))
    K.IC>ICS DONE: INITIALIZE  Initialization Complete.
  ICS>K.IC ERASE
    K.IC>ICS DONE:   Erase Cycle Complete.
  ICS>K.IC SHOPEN 60 OBS USESTATUS                     (( DARK/BIAS와 달리 실제 노출시간만큼 셔터 개방 ))
    K.IC>OBS STATUS: SHOPEN  Shutter=Open
    K.IC>OBS STATUS: SHOPEN  Integration Remaining=54 .. 49 .. 43 .. ... 1 sec.   (( only to sourceID, 60초 카운트다운 ))
    K.IC>OBS STATUS:   Shutter=Closed Integration Remaining=0 sec.

  << 노출 진행 중 - 가이드 채널이 과학 노출과 별개 타이밍으로 동시 진행 >>
  abc>icg go
    ICG>G.IC GO 1 ABC
    G.IC>ABC STATUS: GO  EXPSTATUS=INTEGRATING → READOUT → WRITING → IDLE
    G.IC>G.CB TRANSFER DISK0 4 ABC
    G.CB>ABC DONE: Wrote LASTFILE=/mnt/ICSData/KMTNgs.20240304T064955.0001.fits RATE=281096 KB/sec
    G.CB>ABC DONE: Wrote LASTFILE=/mnt/ICSData/KMTNge.20240304T064955.0001.fits RATE=863645 KB/sec
    G.CB>ABC DONE: Wrote LASTFILE=/mnt/ICSData/KMTNgn.20240304T064955.0001.fits RATE=884042 KB/sec
    G.CB>ABC DONE: Wrote LASTFILE=/mnt/ICSData/KMTNgw.20240304T064955.0001.fits RATE=872799 KB/sec

  << 노출 내내 수 초 간격으로 반복되는 망원경 초점/tip-tilt 자동보정 >>
  abc>tc fttgoto -0.992
    TC>'ABC DONE: goto focus and tip-tilt commanded

  ICS>M.IC GO OBS / ICS>T.IC GO OBS / ICS>N.IC GO OBS   (( readout 시작, K master는 마지막 ))
  ICS>K.IC GO OBS
    K.IC>OBS STATUS: GO  PCTREAD=6 .. 17 .. (진행 중)

  << 다음 필드 준비 명령이 이전 노출 readout 도중에 이미 들어옴 >>
  OBS>ICS ProjID BLG            → ICS>OBS DONE: PROJID  ProjID=BLG EXPSTATUS=READOUT
  OBS>ICS OBJECT BLG12          (( 다음 필드로 전환, 이전 노출은 여전히 readout 진행 중 ))
```

**해석 포인트**
- 실제 서베이 관측은 `OBJECT <필드명>`(`BLG11`, `BLG12`, ...)으로 필드를 바꿔가며 반복 노출한다. `BLG`는 Bulge(은하 중심 방향, 마이크로렌징 서베이의 주요 타깃 영역) 필드 코드로 보인다.
- BIAS/DARK와 달리 실제 노출은 `SHOPEN <exptime> <sourceID> USESTATUS`로 노출시간만큼 셔터를 열고, `Integration Remaining=xx sec.`으로 카운트다운을 sourceID(`OBS`)에게 계속 보고한다.
- 과학 CCD(K/M/T/N) 노출이 진행되는 동안 **가이드 채널(`G.IC`, `ABC`/`ICG`)도 완전히 독립적으로 동시에 노출·저장을 수행**한다 — `abc>icg go`는 과학 노출과 별개 타이밍으로 트리거된다. 두 계통은 통신상 완전히 분리돼 있지만 물리적으로는 같은 망원경·같은 시간대를 공유한다.
- 가이드 CCD 4개의 실제 방위별 파일 접두어가 로그에서 확인된다: `KMTNgs`(south) / `KMTNge`(east) / `KMTNgn`(north) / `KMTNgw`(west) — 1.1절의 "가이드 CCD 4개"가 4방위 배치임을 보여준다.
- `abc>tc fttgoto <focus>`는 노출 내내 수 초 간격으로 반복되는 망원경 초점/tip-tilt 자동보정 명령이다 — 가이드 CCD 영상으로 계산한 보정값을 `ABC`가 `TC`에 실시간으로 피드백하는 오토가이딩 루프로 보인다.
- **파이프라이닝**: 한 노출의 readout이 아직 끝나지 않은 시점(`PCTREAD` 진행 중)에 이미 다음 필드의 `ProjID`/`OBJECT` 명령이 들어온다 — ICS/IC가 "노출 중 설정 변경 금지" 같은 잠금을 걸지 않고, 다음 노출 준비를 이전 readout과 겹쳐 진행하도록 허용한다. 서베이 처리량(cadence) 확보를 위한 설계로 보인다.

### 4.4 가이드 CCD(G) / 자동관측(ABC↔ICG) 트랜잭션

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

가이드 계통은 과학 CCD(K/M/T/N)와 완전히 분리된 병렬 구조다: `ICG`가 `ICS`의 역할을, `ABC`가 `OBS`의 역할을 하며, `G.IC` 하나가 가이드 CCD 4개를 전부 통합 제어한다(1.1절). 파일명 형식도 다르다(`KMTNgs.<timestamp>.<seq>.fits`, ISO 타임스탬프 기반 suffix). `ICG`도 `ICS`와 마찬가지로 `TC`에 자체적으로 `AUXSTATUS`/`TCSSTATUS`를 조회해 `G.IC`에 전달하는 것으로 보이나(4.3절), 그 정확한 타이밍까지는 로그로 확인하지 못했다.

### 4.5 모니터링 (GMON)

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

이 두 메시지는 `ICS`가 `TC`에 조회(3.1절의 `ICS>TC AUXSTATUS`/`TCSSTATUS`)한 결과를 각 과학 CCD(`K/M/T/N.IC`, 3.2절의 `ICS>K/M/T/N.IC STATUS: AUXSTATUS/TCSSTATUS ..`)에 전달하는 것이다. 해당 CCD는 이를 그대로 저장해두었다가 FITS 파일 저장 시 헤더에 기록한다. `EXPSTATUS` 필드가 트랜잭션 전체의 상태 머신(`ERASE → INTEGRATING → READOUT → WRITING/IDLE`)을 나타낸다.

**목적**: 두 상태 모두 관측 데이터의 **FITS 헤더에 기록할 망원경/장비 정보**를 채우기 위한 것이다 — AUXSTATUS는 필터/초점스테이지/환경(온도, 팬 등) 정보, TCSSTATUS는 좌표(RA/DEC/AZ/ALT)·노출시작시각(`DATE-OBS`) 등 망원경 지향 정보다. CCD 구동 자체에는 영향을 주지 않는다.

**정확한 시점** (4.2/4.3절 실측 로그로 확인, "주기적"으로 오는 게 아니라 노출 1회당 정확히 각 한 번씩, 서로 다른 시점에 전달됨):

1. `ICS`는 `ERASE`를 K에 내리는 시점에 맞춰 `ICS>TC AUXSTATUS`와 `ICS>TC TCSSTATUS`를 **한 번에 묶어서 순서대로 질의**한다(TC가 거의 즉시 `DONE:`으로 응답).
2. **AUXSTATUS는 곧바로** 과학 CCD 4개(`K/M/T/N.IC`)에 전달된다 — 메시지에 `EXPSTATUS=ERASE` 태그가 붙어 "플러싱 중 스냅샷"임을 알 수 있다. 환경/필터 정보는 상대적으로 덜 시간에 민감하므로 질의 즉시 전달. (가이드 CCD `G.IC`는 이 전달 대상에 포함되지 않는다 — `ICG`가 별도로 조회해 자체 전달하는 것으로 보인다, 4.4절 참고.)
3. **TCSSTATUS는 곧바로 전달되지 않는다.** `ERASE` 사이클이 끝나 셔터가 열릴 때(`SHOPEN`, 실제 노출의 경우)까지 기다렸다가 전달된다 — 메시지에 `EXPSTATUS=INTEGRATING` 태그가 붙고, 메시지 안의 `DATE-OBS` 값은 (질의 시각이 아니라) 실제 셔터 개방 시각과 일치한다. 즉 TCS 조회 자체는 미리 해두지만, **셔터가 실제로 열린 시점의 타임스탬프를 `DATE-OBS`로 확정한 뒤에야** 각 CCD로 내보낸다 — FITS 헤더의 `DATE-OBS`/좌표가 "노출 시작 순간"을 정확히 반영하도록 하기 위한 설계로 보인다.
4. DARK/BIAS처럼 셔터를 열지 않는 노출도 `ERASE` 완료 시점을 "논리적 노출 시작"으로 취급해 동일하게 TCSSTATUS를 전달한다(4.2절 예시 참고).

### 5.4 에러(ERROR) 패턴 — 실제 발생 사례

```
ICS>OBS ERROR: EXP  Cannot change EXPTIME for ImgType=BIAS
```
→ IMAGETYP이 BIAS로 설정된 상태에서 `EXP`(노출시간) 변경을 시도하면 거부됨 (BIAS는 정의상 0초 고정). ICS→전 CCD로 동일 에러가 전파된다.

```
G.IC>ABC ERROR: GO  DMA WAIT TIMEOUT. EXPOSURES ABORTED. EXPSTATUS=ERROR
```
→ 가이드 CCD에서 DMA(광케이블) 응답 타임아웃 시 발생, 자동으로 노출이 중단되고 `EXPSTATUS=ERROR`로 천이. 로그 샘플에서 반복적으로 (수 분 간격) 발생한 사례가 다수 확인됨 — 운영 중 흔한 장애 패턴으로 보인다.

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
| `IC_commands_R20220302.docx` / `.pdf` | **검토 완료** — ICS/IC 명령어 정식 레퍼런스, 예시 시퀀스, 운영 노트 (2022-03-02 개정). 두 형식 내용 동일 확인(3절 근거) |
| ~~`CCD status (20220826.emaitoSET).pdf`~~ | 2026-07-28 사용자가 폴더에서 제거함 — ICS 범주 밖(CCD 자체 상태/특성화 문서)이라 판단, 다른 위치(추정: `cam_char/` 관련)로 이동. 본 보고서와 무관 |
| `__ICIMACS/IMPv2.5Protocol1.pdf` | **검토 완료** — IMPv2.5 프로토콜 정식 스펙 (OSU, 2008). 2절 근거 |
| `__ICIMACS/SPIE_ICIMACS_560_1.pdf` | **검토 완료** — 1998년 원조 ICIMACS SPIE 논문. IC/HE/IE/WC/CB 노드 이름의 유래, SCSI 이중 디스크 아키텍처, IMPv1 원형 프로토콜 확인. 1.4절 근거 |
| `__ICIMACS/obsguide.pdf` | **검토 완료** — *Prospero Observer's Guide* (1999, OSU OSIRIS@CTIO용). KMTNet 고유 문서는 아니지만 `OBS` 노드의 원형(Ariel/Prospero)과 "파일명 충돌 시 fail-safe unique name" 관례의 기원 확인. 1.4/5.5절 근거 |
| `__ICIMACS/obsguide.ps` | 위 문서의 PostScript 원본(미검토, PDF와 동일 추정) |
| `__ICIMACS/ISISclient docu/*.pdf` | **검토 완료** — MODS(OSU) 참조 구현의 ISIS 클라이언트 라이브러리 + `dispatcher.cpp/h`(Qt GUI 클라이언트 발신 큐) Doxygen 문서. 7절 근거 |
| `__ICIMACS/original codes/ISISclient.zip` | **검토 완료** — 범용 C 클라이언트 라이브러리(`libisis.a`) 원본. 7.1~7.3절 근거 |
| `__ICIMACS/original codes/pctcs.zip` | **검토 완료** — PC-TCS 망원경 제어기용 IMPv2 "agent" 프로그램 원본 (Yale1m/Sim 두 배포본). 7.4절 근거 |
| `__ICIMACS/osu etc/mosaic.pdf` | **검토 완료, KMTNet과 무관** — OSU의 별개 적외선 카메라 "MOSAIC"(MDM/KPNO용) SPIE 논문. ICIMACS가 여러 계측기에 재사용된 사례 중 하나일 뿐, KMTNet 배포본과 직접 관련 없음 |
| `__ICIMACS/osu etc/P-atwood-poster.pdf`, `spie3.pdf` | 미검토 — 파일명·크기상 OSU 계측기 관련 학회 포스터/논문으로 추정, 배경자료 성격이라 낮은 우선순위로 보류 |
| `__ICIMACS/osu etc/*.url`, `__ICIMACS/*.url` | OSU 웹페이지 바로가기(오래된 링크, 대부분 접속 불가 추정) — 미검토 |
| `__sample_isislog/isislog.{ctio,saao,sso}/isis.*.log` | 3개 사이트, 2024~2025년 실제 ISIS 런타임 로그 샘플 (본 보고서 4~5절의 실측 근거) |

---

## 7. 레퍼런스 C 클라이언트 라이브러리 분석 (`ISISclient.zip`, `pctcs.zip`)

`__ICIMACS/original codes/`의 원본 소스코드를 직접 확인한 결과. `IMPv2.5Protocol1.pdf`(2절)는 프로토콜의 "규격"만 정의하고 전송 매체를 특정하지 않는데, 이 라이브러리는 OSU가 실제로 배포한 **레퍼런스 구현**이라 스펙에 없는 구체적인 동작 방식을 보여준다. 단, 이 라이브러리는 주석상 2003~2004년 작성된 **IMPv2**(Command_Word 분리 요구가 추가되기 이전) 버전 기준이라, IMPv2.5와 완전히 동일하지는 않다.

### 7.1 라이브러리 구조 (`libisis.a`)

4개 모듈로 구성 (`isisclient.h`가 전체를 묶는 헤더):

| 파일 | 역할 |
|---|---|
| `isismessage.c` | 메시지 조립/분해: `ISISMessage()`, `SplitMessage()` |
| `isissocket.c` | UDP 소켓 I/O: `OpenClientSocket`, `ReadClientSocket`, `SendToISISServer`, `ReplyToRemHost` |
| `isisserial.c` | 시리얼 포트 I/O: `OpenSerialPort`, `SetSerialPort`, `ReadSerialPort`, `WriteSerialPort` |
| `isisutils.c` | 문자열/시간 유틸리티: `UTCDate`, `UTCTime`, `ISODate`, `GetFineTime`, `MilliSleep` 등 |

모든 클라이언트 런타임 상태는 `isisclient_t`(`client_info`) 구조체 하나에 담긴다 — ISIS 서버 주소/포트, 자신의 소켓 FD·ID·포트, standalone 모드용 원격 호스트 정보, verbose/debug/logging 플래그 등. 신규 Python 구현에서 클라이언트 설정 객체를 설계할 때 참고할 만한 최소 구성이다.

### 7.2 메시지 파싱의 실제 동작 (`isismessage.c`)

- `SplitMessage()`는 주소 헤더(`from>dest`)를 먼저 분리한 뒤, 두 번째 토큰이 `STATUS:/DONE:/ERROR:/WARNING:/FATAL:/EXEC:/REQ:` 중 하나인지 **`strcasecmp`로 대소문자 무관 비교**한다. 4.1절에서 관찰된 "소문자 `ping`, `dark begin`도 대문자와 동일하게 처리됨" 현상은 바로 이 구현에서 비롯된 것 — 스펙 문서는 key=value의 T/F만 대소문자 무관이라고 명시하지만, 실제 구현은 메시지 타입·커맨드 워드 전체를 대소문자 무관으로 다룬다.
- 이 레퍼런스 구현은 메시지 타입 뒤 나머지 전체를 통째로 `msgbody`로 넘긴다 — **`Command_Word`와 `Message_Body`를 분리하는 파싱 로직이 라이브러리 레벨엔 없다.** (IMPv2.5에서 요구하는 Command_Word 분리·매칭은 각 애플리케이션이 자체적으로 구현해야 함을 의미한다.)
- `ISISMessage()`로 메시지를 만들 때 `REQ:` 타입은 **항상 타입 문자열 없이 암묵적으로 전송**된다 (`case REQ: ... sprintf(tmpstr,"%s>%s %s\r", ...)` — `REQ:` 리터럴을 붙이지 않음). 즉 레퍼런스 구현에서 명시적 `REQ:` 문자열은 사실상 만들어지지 않으며, 수신측이 무타입 메시지를 REQ로 해석하는 관례에 전적으로 의존한다.
- `isisutils.c`의 `GetArg()`(명령 인자 추출 유틸)는 **공백(space) 기준 단순 토큰화**일 뿐이다. 프로토콜 스펙(2.3절)이 설명하는 "여러 단어는 `'...'` 또는 `(...)`로 감싼다"는 규칙을 이 공용 유틸리티가 대신 처리해주지 않는다 — 즉 따옴표·괄호로 묶인 다중 단어 인자(예: `Observer=(Pogge, DePoy, and Mason)`)를 올바르게 추출하는 책임은 라이브러리가 아니라 각 애플리케이션의 몫이다.

### 7.3 전송 계층 (`isissocket.c`, `isisserial.c`)

- **UDP**: `socket(AF_INET, SOCK_DGRAM, 0)` + `bind()`로 자기 포트를 확보하고, ISIS 서버로는 `sendto()`(`SendToISISServer`), 마지막으로 자신에게 메시지를 보낸 원격 호스트에는 `ReplyToRemHost()`로 응답한다. `ReadClientSocket()`은 `recvfrom()`으로 들어온 데이터그램의 발신 IP:port를 그때그때 기록한다 — **연결 상태를 유지하지 않는 stateless 구조**이며, 이것이 1.2/2절에서 정리한 "재등록 시 최신 연결이 이전 것을 대체" 동작의 근본 원인이다.
- **Serial**: `open(ttydev, O_RDWR|O_NDELAY)`로 논블로킹 오픈. 표준 설정은 **9600 baud, 8 data bits, 1 stop bit, no parity (9600 8N1)**.

### 7.4 "filter/agent" 패턴 실례 — `pctcs`

2.5절에서 언급한 "비호환 장치는 별도 filter/agent 프로그램으로 변환" 관례의 실제 사례다. `pctcs`(PC-TCS agent)는 ComSoft社 PC-TCS 망원경 컨트롤러가 시리얼로 약 200ms 간격으로 계속 흘려보내는 텔레메트리를 읽어, IMPv2 호환 `STATUS:` 메시지로 번역해 배포하는 독립 프로그램이다 (Yale 1m/시뮬레이터 두 배포본 확인). `select()`로 시리얼 포트·표준입력(readline 기반 콘솔)·UDP 소켓을 동시에 감시하는 구조이며, ISIS 클라이언트 모드/standalone 모드 양쪽으로 실행 가능하다. 소스 주석에 "based on fwagent"라는 기록이 있어, 이런 "레거시 장비 ↔ IMPv2 번역기" agent가 여러 종류(필터휠 등) 존재했던 것으로 보인다.

### 7.5 발신 메시지 큐잉 패턴 — `dispatcher.cpp/h` (MODS Qt GUI 클라이언트)

`ISISclient docu/dispatcher.cpp.pdf`, `dispatcher.h.pdf`에서 확인. 이건 ISIS 서버가 아니라 MODS(OSU 분광기)용 Qt 기반 GUI 클라이언트(modsUI)에 쓰인 **발신 메시지 큐**로, KMTNet 코드 자체는 아니지만 신규 구현에 참고할 만한 범용 패턴이다.

- `Dispatcher`는 `QThread`를 상속한 큐 스레드: `addMessage(host, msg)`로 메시지를 큐에 쌓으면, 별도 스레드가 하나씩 꺼내 `dispatch` 시그널로 내보내고, **설정 가능한 cadence(기본 딜레이)만큼 대기한 뒤 다음 메시지를 처리**한다 (`dispatchCadence`, 기본 단위 msec).
- `abort()`로 큐를 즉시 비우고 중단 가능, `numPending()`/`queueList()`로 큐 상태 조회 가능, 뮤텍스로 스레드 안전성 확보.
- **의의**: 같은 수신 노드로 메시지를 너무 빨리 연속으로 쏘면(예: 여러 IC에 순차 명령을 뿌릴 때) 수신측이 처리를 못 따라가거나 UDP 유실이 생길 수 있는데, 이런 속도 제한(rate-limit)이 있는 발신 큐를 별도 컴포넌트로 두는 게 legacy에서도 쓰인 검증된 패턴이다. 신규 Python ICS에서 `asyncio.Queue` + 주기적 dequeue 태스크로 동일한 패턴을 재현할 만하다.

---

## 8. 신규 Python ICS 개발 시 고려사항 (메모)

- 프로토콜(IMPv2.5) 자체는 언어/OS 무관, ASCII 텍스트 기반이라 Python 구현에 특별한 장벽 없음. `\r` 종료, 최대 2048자, `key=value` 파싱만 구현하면 됨.
- **전송은 UDP** (7.3절) — Python에서는 `socket.SOCK_DGRAM` + `sendto`/`recvfrom`으로 구현. TCP처럼 연결·재연결·소켓 유지 로직을 고민할 필요가 없는 대신, 메시지 유실/중복에 대한 방어(타임아웃 재시도 등)는 애플리케이션 레벨에서 직접 챙겨야 한다.
- 노드 등록에 별도 API가 없으므로, 신규 구현도 "자기 포트에 UDP 소켓 열고 PING 한 번 보내기"만으로 XIS(ISIS)에 등록되는 기존 관례를 그대로 따라야 상호운용 가능.
- 메시지 타입/커맨드 워드 매칭은 **대소문자 무관**으로 구현해야 legacy 노드들과 호환된다 (7.2절). `REQ:`는 관례상 절대 리터럴로 보내지 않는다.
- `Command_Word`와 나머지 `Message_Body`를 분리하는 파싱은 라이브러리가 아니라 애플리케이션 책임이라는 점(7.2절)을 신규 구현 설계에 반영할 것 — 공통 파서 계층에서 이 분리까지 끝내주는 편이 legacy보다 개선된 지점이 될 수 있음.
- 문서상 "미구현"으로 명시된 명령(`BIN`,`ROI`,`DISPL`,`STOP`,`ABORT`,`MOVIE`)은 legacy에서도 동작하지 않았던 것이므로, 신규 구현 시 이를 실제로 구현할지 legacy와 동일하게 스텁으로 둘지 결정 필요.
- `EXPNUM`(4자리, CCD) vs `EXPNUM`(6자리, ICS) 자릿수 불일치는 `INITIALIZE`로 우회하는 것이 legacy의 실제 운영 방식 — 신규 구현에서는 애초에 자릿수를 통일하는 것을 검토할 만함.
- `K.IC>XIS PING/PONG` 을 디스크 쓰기 완료 타이밍 신호로 쓰는 관례(4.2절)는 프로토콜 스펙에 없는 legacy 특유의 관행이므로, 신규 구현에서 그대로 가져갈지 명시적 완료 신호로 대체할지 검토 필요.
- 비호환 레거시 장비(예: 시리얼로 독자 포맷을 쏟아내는 컨트롤러)를 새 시스템에 물려야 한다면, `pctcs` 같은 "filter/agent" 패턴(7.4절)을 그대로 채택할 만하다 — 굳이 메인 ICS에 특수 파싱 로직을 넣기보다, 별도의 작은 번역 프로세스로 분리하는 것이 legacy에서도 검증된 접근.
- `SYNCHRONIZE` 동기화는 legacy에서 요청-응답이 아니라 "`DONE: SYNCHRONIZE ...` 형태의 메시지가 오면 보낸 주체와 무관하게 그냥 반영"하는 수동 리스너 방식으로 동작한다(3.2절). 신규 구현에서 상태 동기화를 설계할 때 이 "누가 보냈든 상관없이 상태를 흡수하는" 느슨한 모델을 그대로 둘지, 발신자를 검증하는 명시적 요청-응답 모델로 바꿀지 결정이 필요하다.
- **발신 메시지 큐/속도 제한**: `dispatcher.cpp/h`(7.5절)처럼, 여러 수신 노드에 순차적으로 명령을 뿌릴 때 UDP 유실이나 수신측 처리 지연을 막기 위한 rate-limited 발신 큐를 두는 게 legacy에서도 쓰인 패턴이다. Python에서는 `asyncio.Queue` + 주기적 dequeue 태스크로 재현 가능하고, 신규 구현에서도 채택을 검토할 만함.
- **다중 단어 인자 파싱 개선**: legacy 공용 유틸리티(`GetArg`, 7.2절)는 따옴표/괄호로 묶인 다중 단어 값(`Observer=(Pogge, DePoy, and Mason)` 같은 형태)을 실제로는 처리하지 못하고, 각 애플리케이션이 알아서 해야 했다. 신규 구현에서는 공통 파서 계층에 이 처리를 제대로 넣는 것이 legacy 대비 개선 포인트가 될 수 있음.
- **디스크 이중화(`DISK0`/`DISK1`, 1.4/4.2절)는 1998년 SCSI 하드웨어 제약에서 비롯된 성능 최적화**였다는 점을 감안할 것 — 지금처럼 네트워크 스토리지(`/mnt/ICSData`)를 쓰는 환경에서 이 패턴을 그대로 유지할 이유가 있는지(예: 쓰기 도중 파일 접근 충돌 방지 등 다른 이유로 여전히 유효한지), 아니면 단순화할 수 있는지 신규 설계에서 검토할 만함.
- **파일명 fail-safe 관례는 계속 가져갈 가치가 있음**: "계산된 파일명이 이미 존재하면 조용히 덮어쓰지 않고 대체 이름으로 저장 + WARNING"(5.5절)은 1999년 Prospero 시절부터 이어진 데이터 유실 방지 안전장치(1.4절)로, legacy에서 여러 세대에 걸쳐 검증된 설계다. 신규 구현에서 굳이 없앨 이유가 없어 보임.

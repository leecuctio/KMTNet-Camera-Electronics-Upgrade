# Legacy ICS / XIS(ISIS) System — Technical Reference Report

이 문서는 `ics_legacy/` 폴더에 수집된 자료(프로토콜 스펙, ICS 명령어 문서, 3개 관측소 ISIS 런타임 로그 샘플)를 바탕으로, 기존(legacy) ICS·ISIS 시스템의 아키텍처·통신 프로토콜·명령어·출력 메시지를 정리한 것이다. 신규 Python 기반 ICS 개발의 참고 자료로 사용한다.

- 대상 시스템: **ICIMACS** (Instrument Control & IMage ACquisition System, OSU 개발) 계열, KMTNet(칠레 CTIO/남아공 SAAO/호주 SSO 3개 사이트) 배포본
- 근거 자료: `IMPv2.5Protocol1.pdf`, `IC_commands_R20220302.docx`, `__sample_isislog/{isislog.ctio,isislog.saao,isislog.sso}/*.log`

> **2026-08-03 개정**: 로그 아카이브 **전량**(`__localonly_isislogs/`, CTIO 634일 + SAAO 273일 + SSO 206일 = 48GB, 1,113일분)을 기계적으로 스캔해 샘플 9개월치에 없던 시퀀스와 메시지를 찾아냈다. 그 결과 아래가 새로 들어가거나 정정됐다:
> - **5.6절 신설** — ICS 메시지 오염 버그(커맨드워드 슬롯이 비워지지 않는 문제). 이번 조사에서 가장 실질적인 발견이다.
> - **3.5절 신설** — `GO n` 다중 노출 시퀀스(`Image n of N complete.`). 샘플에는 한 건도 없었다.
> - **정정** — 디스크는 이중화가 아니라 **최대 4중화**(1.4/4.2절)
> - **보강** — `CHA`/`C1` 노드(1.3절) · AUXSTATUS 필드셋의 사이트별 차이와 중계 실패 형태(5.3절) · 새 에러·경고(5.4절) · 형식 변형(5.2절) · 8.0.1절의 OBSAgent 규약 6개 항목
>
> 스캔 도구는 [`../ics_sim/tools/scan_legacy_logs.py`](../ics_sim/tools/scan_legacy_logs.py) 에 남겨 두어 원본 로그가 있는 컴퓨터에서 재검증할 수 있다. 로그 자체는 `__localonly_*` 규약에 따라 비커밋이다. 신규 시뮬레이터 구현과 그 판단 근거는 [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 참고.

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
| `TC` | 망원경 제어(Telescope Control) | 좌표·상태 텔레메트리(`TSTAT`/`ASTAT`) 응답, `AUXSTATUS`/`TCSSTATUS` 소스. **실체는 TCS Agent(`pctcs`) — [../TCSAgent/tcsagent_report.md](../TCSAgent/tcsagent_report.md)에서 별도 분석** |
| `OBS` | 관측 시퀀서/옵저버 콘솔 | 사람 또는 스크립트가 명령을 입력하는 최상위 클라이언트. `ICS`/`TC`에 명령 발행. **실체는 OBS Agent(`obstool`) — [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md)에서 별도 분석** |
| `ABC` | 자동관측 제어기 | `ICG`에 가이드 노출/`GO` 명령 발행 (자동화된 관측 스케줄러로 추정) |
| `GMON` | 모니터링 클라이언트 | `OBS`에 `sysstatus`를 초당 폴링해 카메라·망원경 통합 상태 조회 (대시보드/모니터링용). 응답 문자열은 OBSAgent의 `GetSysStatus()`가 생성하며, 같은 정보가 `/data/Logs/ObsStatus.txt`에도 5초마다 기록된다 ([OBSAgent 보고서](../OBSAgent/obsagent_report.md) 7절) |
| `AL` / `ALL` | 브로드캐스트 예약 주소 | 모든 노드에 메시지 전파 |
| `CHA` | **미확정 — 엔지니어링/운영자 콘솔로 추정** | 전량 스캔에서 새로 발견(SSO, 2024-06-28 전후 2,441회). `ICS`와 개별 IC 양쪽에 `EXPNUM`·`INITIALIZE`를 보내고 응답을 받는다: `ICS>CHA DONE: EXPNUM  Filename=20240628.021488`, `M.IC>CHA DONE: INITIALIZE  Initialization Complete.` |
| `C1` | **미확정 — 전송 요청 주체** | `T.IC>T.CB TRANSFER DISK0 <n> C1` (CTIO 3~6회). `ICS`/`OBS`/`ABC` 외의 sourceID |

> **문서에 없는 노드가 실재한다는 점이 신규 설계에 함의가 있다.** IMPv2에는 노드 인증 개념이 없고 레거시도 발신자를 가리지 않았다. 운영 중 임시 도구를 붙이는 관행이 있었다는 뜻이므로, **신규 구현도 발신 노드 화이트리스트를 두지 않는 편이 낫다** — 프로토콜에 맞는 메시지면 누가 보냈든 처리하고 요청자에게 응답한다.
>
> (덧붙여 `K.IC>0 STATUS: ...` 처럼 수신 노드명이 `0` 으로 파괴된 사례도 1건 있으나, 이는 실재 노드가 아니라 5.6절의 전송 손상 사례다.)

### 1.3.1 실제 배치 구조 — VDOS IC + 리눅스 relay (2026-08-04 신규)

`__dts_legacy/`(ICS 컴퓨터 `dts` 폴더 백업, 6절 참고)의 설정 파일들로 **로그만으로는 보이지 않던 물리 구조**가 드러났다.

**IC/ICS 는 리눅스 프로그램이 아니라 VDOS(DOS 계열) 머신에서 돈다.** `Config/*.IC.ini` 는 그 머신의 부팅·설정 파일이다:

```
# Config/K.IC.ini            # Config/ICS.ini           # Config/G.IC.ini
C:\0ICCFG\IC.INI             C:\0ICCFG\IC.INI           C:\0ICCFG\IC.INI
  INSTRUMENT=KMTNk             INSTRUMENT=ICS             INSTRUMENT=KMTNg
  ICHOST=K.IC                  ICHOST=ICS                 ICHOST=G.IC
  CBHOST=K.CB                                             CBHOST=G.CB
  ISISHOST=K.IS                ISISHOST=ICS.IS            ISISHOST=G.IS
C:\0ICBOOT\IC.BAT            C:\0ICBOOT\IC.BAT          C:\0ICBOOT\IC.BAT
  CD \KMTS                     CD \KMTX                   CD \KMTG
  IC.BAT                       IC.BAT                     IC.BAT
```

여기서 세 가지가 확정된다.

**① `ICS` 는 IC 와 같은 소프트웨어다.** 별도 프로그램이 아니라 같은 `IC.BAT` 를 `INSTRUMENT=ICS` 로 설정해 돌린다. 프로그램 디렉토리만 `\KMTX`(eXecutive)로 다르다. **이것이 `ICS` 와 `K.IC` 가 5.6절의 메시지 오염 버그를 똑같이 공유하는 이유다** — 같은 코드베이스이기 때문이다.

**② BUILD 문자열의 접두어는 프로그램 디렉토리 이름이다.** 5.3절 AUXSTATUS 꼬리의 정체가 풀린다:

| 노드 | `INSTRUMENT=` | 디렉토리 | 텔레메트리 BUILD |
|---|---|---|---|
| `ICS` | `ICS` | `\KMTX` | `ICSBUILD=**KX**2016-03-23:1381` |
| `K/M/T/N.IC` | `KMTNk` 등 | `\KMTS` | `KBUILD=**KS**2016-01-13:1370` |
| `G.IC` | `KMTNg` | `\KMTG` | `GBUILD=**KG**2016-06-02:1407` |

`STATUS` 응답의 `Inst=KMTNk` 값도 이 `INSTRUMENT=` 설정에서 온다.

**③ VDOS IC 는 별도 하드웨어가 아니라 리눅스 호스트 위의 KVM 게스트다.**

`__localonly_dts.icsci/memo.txt` 에 IC 이미지의 위치가 적혀 있다:

```
# IC2 path on Sci/Gui/Spa      cd /var/libvirt/images
# IC2 path on K/M/T/N/G/Sp     cd /var/lib/libvirt/images
```

`libvirt/images` 는 **KVM 가상머신 디스크 이미지** 경로다. 즉 `IC2.img` 는 VDOS 게스트의 디스크이고, 같은 백업의 `VMFolder/` 에 그 근거가 더 있다 — **SeaBIOS 1.7.4**(QEMU/KVM 게스트용 BIOS)와 데이터 디스크 라벨(`DISK1.BUS1.03/13/13`), 홈 디렉토리의 `.virt-manager` 설정.

이미지 파일명이 빌드를 담고 있다 — `IC2.KX20160323.1381_icsci_ctio` 는 **CTIO icsci 의 ICS 게스트**(빌드 `KX2016-03-23:1381`, ②의 `ICSBUILD` 와 일치)를 뜻한다.

> **`TRANSFER DISK<n>` 의 정체가 여기서 풀린다.** 4.2절의 `DISK0`~`DISK3`(6.2절에서 최대 4중으로 정정)은 물리 SCSI 디스크가 아니라 **VDOS 게스트에 붙인 가상 디스크**다. 1998년 SCSI 이중버퍼 패턴이 가상화 환경으로 그대로 이식돼 살아남은 것이다. 게스트가 가상 디스크에 쓰면 호스트의 Caliban(`*.CB`)이 그것을 읽어 `/mnt/ICSData` 로 옮긴다.

**④ 리눅스 `isisrelay` 가 UDP↔시리얼을 중계한다.** `Config/isisrelay.ini`:

```
UDPPort 6600                 # 이 포트로 받아서
TTYPort /dev/ttyS0           # 시리얼로 VDOS IC 에 넘긴다
Speed 9600  DataBits 8  StopBits 1  Parity 0
ISISHost 192.168.14.109      # XIS 로 올려보낸다
ISISPort 6660
```

XIS 설정(`Config/isis.ini`)의 주석도 이를 뒷받침한다 — *"Ping the isisrelays on all the IC machines, **this reaches the VDOS ICs**"*. 즉 로그에 보이는 `[192.168.14.102:6600] K.IC>XIS PONG` 은 **relay 가 VDOS IC 의 응답을 UDP 로 올려준 것**이다. 각 IC 가 자기 로컬 relay 를 `K.IS`/`G.IS`/`ICS.IS` 라는 이름으로 알지만(`ISISHOST=` 항목), relay 가 투명하게 중계하므로 **로그에 `.IS` 노드는 나타나지 않는다.**

```
   icsci 서버 (.109)              IC 머신 (.102~.108, 리눅스 호스트)
   ┌──────────────────┐           ┌──────────────────────────────────┐
   │ XIS  (UDP 6660)  │◄─UDP 6600►│ isisrelay                        │
   │ OBS  (UDP 6650)  │           │      ▲ 가상 시리얼 9600          │
   │                  │           │      ▼                           │
   │ /dev/ttyS0       │           │ ┌────────────────────────────┐   │
   │   115200 ────────┼───┐       │ │ KVM 게스트 (VDOS)          │   │
   └──────────────────┘   │       │ │  IC2.img,  \KMTS           │   │
                          │       │ │  가상디스크 DISK0~3        │   │
      ICS 게스트 (VDOS)   │       │ └────────────────────────────┘   │
      IC2.KX…, \KMTX  ◄───┘       │ Caliban CB (UDP 10601)           │
                                  │   └─ 가상디스크를 읽어           │
                                  │      /mnt/ICSData 로 전송        │
                                  └──────────────────────────────────┘
```

**⑤ `SP` 노드가 존재한다 — 예비 IC 로 보인다.** `Config/SP.IC.ini`(`INSTRUMENT=KMTNsp`, `ICHOST=SP.IC`, `CBHOST=SP.CB`, `CD \KMTS`)와 `cb_SP.ini`·`isisSP.ini`·`calibanSP.ini` 가 존재한다. 과학 IC 와 같은 `\KMTS` 를 쓰므로 **과학 CCD 계열의 예비기**로 판단된다. XIS preset 목록의 `192.168.14.107 6600`(로그에 트래픽이 전혀 없는 주소)이 이 노드 자리로 보인다.

> **신규 설계 함의**: 신규 `ics` 는 이 3계층(VDOS IC + relay + XIS)을 **한 프로그램으로 대체**한다. relay 계층과 시리얼 구간이 통째로 사라지므로 5.6.3절의 전송 손상도 함께 사라진다. 다만 **XIS 와의 인터페이스는 그대로 유지**해야 한다 — XIS 입장에서는 relay 가 있던 자리에 신규 `ics` 가 들어오는 것으로 보여야 한다.

포트 관례 (로그에서 관측):
- IC 계열(`*.IC`, `ICG`): 6600
- CB 계열(`*.CB`): 10601
- `TC`: 6606
- `OBS`: 6650
- `XIS`(허브 자신): 6660 (CTIO 기준 — OBSAgent의 런타임 설정 `ISISPort 6660`에서 확인, [OBSAgent 보고서](../OBSAgent/obsagent_report.md) 3.1절)
- `ICS`: 시리얼(`/dev/ttyS0`), 사이트에 따라 소켓일 수도 있음

> **전송 계층은 TCP가 아니라 UDP다** (근거: `ISISclient.zip`의 `isissocket.c`, 아래 7절 참고). 각 노드는 `SOCK_DGRAM` 소켓 하나를 자기 포트에 bind하고 `sendto`/`recvfrom`으로만 통신한다 — 연결(connection) 개념 자체가 없다. 1.2절의 "노드 등록/대체" 동작은 사실 이 UDP 특성의 직접적 결과다: XIS는 단지 "노드ID → 가장 최근에 그 ID로 데이터그램을 보낸 (IP,port)" 매핑 테이블을 유지할 뿐이고, 같은 ID로 새 데이터그램이 오면 그 주소로 덮어쓴다. TCP처럼 세션을 맺고 끊는 절차가 없으니 "충돌 감지·거부"라는 개념 자체가 성립하지 않는다.

### 1.4 ICIMACS 아키텍처의 기원 (1998 SPIE 논문, `SPIE_ICIMACS_560_1.pdf`)

노드 이름·디스크 이중화 패턴 등 지금 KMTNet 배포본에 남아있는 관례들이 어디서 비롯됐는지, 1998년 OSU의 원조 ICIMACS 발표 논문(Atwood, Mason, et al., SPIE Vol. 3355)으로 확인된다.

- **노드 이름의 유래**: 원래 ICIMACS는 PC/Unix 혼합 네트워크로, 역할별 컴퓨터에 다음과 같은 이름을 붙였다 — `IC`(**I**nstrument **C**omputer, 검출기 시퀀서 구동·실시간 처리), `HE`(**H**ead **E**lectronics, 검출기/셔터/LED 신호 처리), `IE`(**I**nstrument **E**lectronics, 메커니즘 모터 제어), `WC`(**W**orkstation **C**omputer, Unix 워크스테이션과의 이더넷 연결 + FITS 변환), `CB`(**C**aliban 프로그램, WC와 Sparcstation 사이 SCSI 버스의 데이터를 Sparcstation 파일시스템으로 옮기는 프로그램). **KMTNet의 `K.IC`/`K.CB` 노드 이름은 바로 이 `IC`/`CB` 계보를 그대로 물려받은 것.**
- **디스크 다중화의 유래**: 1998년 당시 SCSI-2(10Mbyte/sec) 버스 한 쌍에 디스크 2개를 연결해, 한쪽에 쓰는 동안 다른 쪽을 읽어 스왑하는 방식으로 "헤드 재배치 시간"을 감추는 성능 최적화였다. **지금 KMTNet 로그의 `DISK<n>` + `TRANSFER`/`REQ SWAP`/`ACK SWAP` 패턴(4.2절)은 이 1998년 SCSI 하드웨어 제약의 논리적 흔적**이다 — `/mnt/ICSData`처럼 네트워크 스토리지를 쓰는 지금 환경에서는 원래의 성능상 이유가 그대로 적용되지 않는다.

  > **정정 (2026-08-03, 전량 스캔)**: 샘플 로그에 `DISK0`/`DISK1`만 나와 "이중화"로 서술했으나, 실제로는 **최대 4중(`DISK0`~`DISK3`)** 이다.
  >
  > | 사이트 | K master | M/T/N |
  > |---|---|---|
  > | CTIO | `DISK0`(85,940) · `DISK2`(258) | 주로 `DISK0` |
  > | SSO | `DISK1`(20,470) · `DISK2`(14,823) · **`DISK3`(177)** | `DISK0`/`DISK1` |
  > | SAAO | `DISK0`/`DISK1` | `DISK0`/`DISK1` |
  >
  > **신규 설계에서는 폐지한다.** 다중화의 두 근거가 모두 사라지기 때문이다 — (1) SCSI 시절 성능 최적화는 현대 스토리지에서 의미가 없고, (2) NFS로 Science server에 옮기는 시간 확보는 **관측자료 취합 서버 역할과 기기제어·자료획득 역할(`x.IC`)을 단일 PC에 통합**하면 불필요하다. 신규는 설정파일에 저장 경로 하나만 둔다([`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 6.2·11.1절).
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
  - **전량 스캔 확인 (2026-08-03)**: 이 6개 명령은 48GB 로그 전량에서 **송수신 0건**이다. 문서상 "미구현"이 운용에서도 한 번도 시도되지 않았음이 확인된다. 같은 스캔에서 `FATAL:` 메시지도 **0건**으로, 샘플 기준 관찰이 전량에서도 유지된다.

### 3.5 `GO n` 다중 노출 시퀀스 (2026-08-03 신규)

`GO` 에 프레임 수를 주면 ICS가 **`GO` 재발행 없이 스스로** 다음 프레임을 이어간다. 샘플 로그 9개월치에는 한 건도 없었고 전량 스캔에서 처음 확인됐다.

핵심은 **중간 프레임의 종료 알림이 `DONE:` 이 아니라 `STATUS:` 라는 점**이다:

```
ICS>OBS STATUS: Image 1 of 5 complete. EXPSTATUS=IDLE     ← 프레임 1 종료 (STATUS:)
ICS>OBS STATUS: EXPSTATUS=INITIALIZING                    ← 프레임 2 시작 (자동)
ICS>OBS STATUS: EXPSTATUS=ERASE
ICS>OBS STATUS: Wrote LASTFILE=…KMTNm.20240103.023885.fits …   ← 프레임 1의 저장 완료가
ICS>OBS STATUS: Wrote LASTFILE=…KMTNk…                          ← 프레임 2 준비 중에 도착
ICS>OBS STATUS: Wrote LASTFILE=…KMTNn…                          ← (파이프라인)
ICS>OBS STATUS: Wrote LASTFILE=…KMTNt…
ICS>OBS STATUS: EXPSTATUS=INTEGRATING
ICS>OBS STATUS: Shutter=Closed Integration Remaining=0 sec. EXPSTATUS=INTEGRATING
ICS>OBS STATUS: EXPSTATUS=READOUT
ICS>OBS STATUS: Image 2 of 5 complete. EXPSTATUS=IDLE
…
ICS>OBS DONE: EXPSTATUS=IDLE                              ← 마지막 프레임만 DONE:
```

**근거**
- CTIO에서 `Image 1 of 5`(1,254) · `2 of 5`(1,250) · `3 of 5`(1,246) · `4 of 5`(1,244)가 관측되고 **`5 of 5`는 0건**이다 → 마지막 프레임은 일반 `DONE: EXPSTATUS=IDLE` 로 끝난다. `of 4`(13) · `of 3`(8) · `of 2`(23)도 같은 패턴.
- **OBSAgent 소스가 이를 뒷받침한다** — `commands.c` 765행 주석: *"msg type of 'EXPSTATUS=IDLE' is STATUS in the case of 'go n' command, added here at v0.3.0"*. v0.3.0이 바로 이 경로 때문에 `STATUS:` 에도 `EXPSTATUS=IDLE` 핸들러를 넣었다.
- SSO에서는 `GO` 접수 직후 `ICS>OBS STATUS: GO  EXPSTATUS=INITIALIZING` 형태도 7회 관측된다.

**신규 구현 시 주의할 타이밍 제약**: 프레임 N의 `Wrote` 4개가 프레임 N+1의 `INITIALIZING`/`ERASE` **이후**에 도착하지만, 프레임 N+1의 `EXPSTATUS=READOUT`/`PCTREAD=` 가 OBSAgent의 `count_wrote` 를 0으로 리셋하기 **전**에는 다 들어와야 한다. 어기면 `FitsSaved` 가 영영 1이 되지 않는다(8.0.1절).

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
  > **주의**: 이 `Disk Write Complete` 메시지는 레거시에 실재하지만, **OBSAgent는 이 문자열을 파싱하지 않는다**(소스에 핸들러 없음 — [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md) 6절 정정 참고). OBSAgent가 파일 저장 완료를 판단하는 근거는 `K.CB`의 `Wrote` 메시지 **4회 누적**이고, `READY` 전이는 타이머다. 신규 `ics`가 이 메시지를 계속 보낼지는 자유(보내도 무해하나 OBSAgent 동작에는 영향 없음).

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

가이드 계통은 과학 CCD(K/M/T/N)와 분리된 병렬 구조다: `ICG`가 `ICS`의 역할을, `ABC`가 `OBS`의 역할을 하며, `G.IC` 하나가 가이드 CCD 4개를 전부 통합 제어한다(1.1절). 파일명 형식도 다르다(`KMTNgs.<timestamp>.<seq>.fits`, ISO 타임스탬프 기반 suffix).

> **→ ICG 노드 전용 심화 분석은 [icg_legacy_report.md](icg_legacy_report.md)** 참고. 위에서 "로그로 확인하지 못했다"고 남겨둔 `ICG`의 `TC` 질의 타이밍은 그 보고서에서 확정됐다(**GO 접수 직후·노출 시작 전**에 `AUXSTATUS`+`TCSSTATUS`를 페어로 질의 — 과학 계통이 셔터 OPEN 시 질의하는 것과 다름). 그 밖에 ICG의 전체 명령어 목록, 기동 시퀀스, `G.CB` 디스크 계층, ICS와의 상세 비교도 그쪽에 정리돼 있다.
>
> 또한 두 계통이 "완전 분리"라는 서술에는 **예외가 하나 있다**: `ICG`는 자기 설정 스냅샷(`STATUS: SYNCHRONIZE`)을 `G.IC`뿐 아니라 **과학 IC 4개에도** 브로드캐스트한다(icg 보고서 5.1절). 계통 간 유일한 결합 지점이다.

### 4.5 모니터링 (GMON)

```
gmon>obs sysstatus
OBS>GMON DONE: CamStatus=READY FitsSaved=1 ExpSet=0 ExpRem=0 TelStatus=TRACKINGS
  RA=03:44:13.15 DEC=-16:02:53.1 ... TELID=KMTC FILTER=V SHUTTER=CLOSED FOCUS=-1.105 ... FAN=ON
```

`GMON`은 초당 `sysstatus`를 `OBS`에 폴링해 카메라·망원경 통합 상태를 하나의 요약 메시지로 받는다. 이 채널의 정체는 이후 OBSAgent 분석으로 확정됐다: `sysstatus`는 OBSAgent(OBS 노드)의 정식 명령이고, 응답 문자열(`CamStatus=... TelStatus=... ...`)은 OBSAgent 내부의 `GetSysStatus()`가 생성한다. 같은 정보가 `/data/Logs/ObsStatus.txt` 파일로도 5초마다 기록된다 — 상세 포맷과 상태값 정의는 [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md) 6~7절 참고.

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

**전량 스캔에서 추가로 확인된 형식 변형 (2026-08-03)**

| 변형 | 내용 |
|---|---|
| `-FIBERS` | `K.IC>ICS DONE: STATUS  Inst=KMTNk … **-FIBERS** +SYNCH …` — 광케이블 미연결 상태. 샘플엔 `+FIBERS`만 있었다. `Driving=0`/`1` 도 함께 변한다 |
| `FLASHNOW` 실사용 | `K.IC>ICS DONE: FLASHNOW  LED Flash Done.` (CTIO 4,700+회). 3.3절의 LED 프로젝터 점검 시퀀스가 실제 운용에서 정기적으로 돈다 |
| `EXP=0` 인 DARK | `ICS>OBS DONE: DARK  ImageType=DARK ObjectName='end' EXP=0` — 관측 종료 시 관례적으로 찍는 이름 `end` |
| `SYNCHRONIZE` 두 타입 | `DONE:`(CTIO 2,230회)와 `STATUS:`(1,284회) **양쪽 모두**로 발신된다. 샘플엔 `STATUS:` 만 있었다 |
| `Wrote` 타입의 사이트 차이 | CTIO는 `K.CB>ICS DONE: Wrote …`, SSO는 `K.CB>ICS STATUS: Wrote …`. 빌드 차이로 보인다. **OBSAgent 동작에는 영향이 없다** — `case DONE:` 에는 `Wrote` 핸들러가 없어서, 어느 쪽이든 OBSAgent가 세는 것은 `ICS>OBS STATUS: Wrote …` **중계**뿐이다(8.0.1절) |

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

#### 5.3.1 필드 순서가 역순으로 뒤집힌다 (2026-08-03 신규)

`TC>ICS DONE: AUXSTATUS` 의 필드 순서와 `ICS>*.IC STATUS: AUXSTATUS` 의 순서가 **정확히 역순**이다. 스택에 쌓았다 빼는 구현으로 보인다.

```
TC→ICS : AUXQDATE=.. TIMESYS=.. TELID=.. AUXLINK=.. ... ENS2=.. ENS1=..
ICS→IC : ENS7=.. ENS6=.. ... AUXLINK=.. TELID=.. TIMESYS=.. AUXQDATE=..
         + KBUILD=.. MBUILD=.. TBUILD=.. NBUILD=.. GBUILD=.. ICSBUILD=.. EXPSTATUS=..
```

TCSSTATUS도 마찬가지이며, ICS가 `DATE-OBS` 를 **맨 앞에** 덧붙이고 `EXPSTATUS` 를 맨 뒤에 붙인다.

#### 5.3.2 필드 집합이 사이트마다 다르다 (2026-08-03 신규)

| | CTIO / SAAO | SSO |
|---|---|---|
| 돔 필드 | 없음 | `DSSTAT` 앞에 `DSTEL DSALT DSAUTO DSSAF DSLW DSUP` 추가 |
| `GBUILD` | 빈 값 (`GBUILD=`) | 채워짐 (`GBUILD=KG2016-06-02:1407`) |

**신규 구현 권고**: 사이트별 필드 테이블을 따로 두지 말고 **받은 `key=value` 를 순서 그대로 보존해 역순으로 되돌려 보낸다**(pass-through). ICS가 알아야 할 것은 "어디까지가 TC 필드이고 어디부터 내가 붙이는 꼬리인지"뿐이다. FITS 헤더 생성에 특정 필드가 필요한데 없으면 **없다는 것이 드러나는 sentinel**(수치 `0`, 문자열 `NC`)로 채운다 — 레거시의 `GBUILD=`(빈 값)·`DSSTAT=NC` 관례와 같은 방식이다. 테이블을 유지하면 사이트가 늘거나 AUX 펌웨어가 바뀔 때마다 코드를 고쳐야 한다.

#### 5.3.3 TC 질의 실패 시의 중계 형태 (2026-08-03 신규)

```
ICS>N.IC STATUS: AUXSTATUS  KBUILD=… MBUILD=… TBUILD=… NBUILD=… GBUILD= ICSBUILD=… EXPSTATUS=ERASE
```

TC 질의가 실패하면 **TC 필드 전체가 비고 ICS가 덧붙이는 꼬리만** 남은 채 그대로 중계된다(CTIO 4회, SSO 144회). **노출은 중단되지 않고 진행되며**, 그 노출의 FITS 헤더는 망원경 정보가 빈 채로 저장된다. 신규 구현에서도 이 동작(진행 우선)을 유지하되, 헤더가 비었다는 사실이 사후에 드러나도록 sentinel을 쓰는 편이 낫다.

### 5.4 에러(ERROR) 패턴 — 실제 발생 사례

```
ICS>OBS ERROR: EXP  Cannot change EXPTIME for ImgType=BIAS
```
→ IMAGETYP이 BIAS로 설정된 상태에서 `EXP`(노출시간) 변경을 시도하면 거부됨 (BIAS는 정의상 0초 고정). ICS→전 CCD로 동일 에러가 전파된다.

```
G.IC>ABC ERROR: GO  DMA WAIT TIMEOUT. EXPOSURES ABORTED. EXPSTATUS=ERROR
```
→ 가이드 CCD에서 DMA(광케이블) 응답 타임아웃 시 발생, 자동으로 노출이 중단되고 `EXPSTATUS=ERROR`로 천이. 로그 샘플에서 반복적으로 (수 분 간격) 발생한 사례가 다수 확인됨 — 운영 중 흔한 장애 패턴으로 보인다.

**전량 스캔에서 새로 확인된 에러 (2026-08-03)**

```
ICS>OBS ERROR: GO  Data acquisition already in progress! EXPSTATUS=<현재상태>
```
→ 노출 진행 중 `GO` 재발행을 거부한다. OBSAgent도 `CamStatus` 가 `IDLE_3`/`READY` 가 아니면 `GO` 를 막지만(8.0.1절), **ICS 자체 방어선이 따로 있다.**

```
*.IC>OBS ERROR: DATASOURCE  Invalid selection for DataSource. ADC, CTC, and SIM are valid. DataSource=<현재값>
```
→ **문서에 없던 제3의 값 `SIM` 이 존재한다.** 3.2절 명령표에는 `ADC`/`CTC` 만 적혀 있으나 파서는 `SIM` 도 받는다. 신규 설계에서 **시뮬레이션 데이터 소스로 재활용할 가치가 크다** — 실제로 신규 시뮬레이터의 백엔드가 자신을 `DataSource=SIM` 으로 보고한다.

```
K.CB>ICS ERROR: No SIMPLE card in FITS file #2, skipping...        (SSO)
```
→ CB가 쓰다 만/손상된 FITS를 만났을 때. 디스크 슬롯 번호가 함께 나온다.

```
*.IC>ICS ERROR: <cmd>  Didn't understand <cmd> <args> ?
```
→ 파서가 인식하지 못한 명령의 거부 형식. 실제로는 전송 손상으로 명령어가 깨졌을 때 주로 나타난다(5.6.3절).

### 5.5 경고(WARNING) 패턴 — 파일명 충돌

```
K.CB>OBS WARNING: FITS file '/mnt/ICSData/KMTNk.20250902.050666.fits' already exists, writing as '/mnt/ICSData/250902.000.fits' instead
```
→ 계산된 파일명이 이미 존재할 경우, 덮어쓰지 않고 대체 파일명(`<yymmdd>.<순번>.fits`)으로 자동 저장 후 WARNING으로 통지. 데이터 유실 방지 목적의 안전장치.

> **정정 (2026-08-03)**: 이 경고는 `OBS` 뿐 아니라 **`ICS` 로도 발신된다** — `N.CB>ICS WARNING: FITS file '...' already exists, ...`. 두 수신자 모두 실측됐다.

> 샘플 로그 전체(9개월치, 3개 사이트)에서 `FATAL:` 메시지는 관측되지 않았다 — 실제 운영 중 물리적 개입이 필요한 심각 오류는 드물게 발생하거나 별도 채널로 처리되는 것으로 보인다. **전량 스캔(48GB, 1,113일)에서도 `FATAL:` 은 0건**으로, 이 관찰이 유지된다.

---

## 5.6 ICS 메시지 오염 버그 (2026-08-03 신규)

> 48GB 전량 스캔의 가장 실질적인 발견이다. 신규 구현이 **재현하지 말아야 할** 동작이므로 별도 절로 정리한다. 신규 시뮬레이터의 대응은 [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 5장.

IMPv2 메시지는 `src>dest <TYPE> <커맨드워드> <본문>` 구조다. **레거시 ICS/IC는 이 커맨드워드 슬롯을 "가장 최근에 처리한 메시지"의 것으로 채운 채 비우지 않는다.** 명령에 대한 직접 응답이 아닌 **비동기 상태 메시지**(카운트다운, `EXPSTATUS` 전이 등)에서 그 잔재가 그대로 드러난다.

### 5.6.1 현상 A — 스테일 커맨드워드 (결정론적, 대량)

CTIO 634일 기준 실측:

| 오염된 발신 | 건수 |
|---|---:|
| `ICS>OBS STATUS:  STATUS: EXPSTATUS=INTEGRATING` | 173,635 |
| `K.IC>OBS STATUS: REQ  Integration Remaining=54 sec.` | 148,430 |
| `K.IC>OBS STATUS: SHOPEN  Integration Remaining=14 sec.` | 93,724 |
| `K.IC>OBS STATUS: DATASOURCE  Integration Remaining=5 sec.` | 39,614 |
| `K.IC>ICS DONE: REQ  Erase Cycle Complete.` | 31,604 |
| `K.IC>OBS STATUS: FLASHNOW  Integration Remaining=… sec.` | 4,522 |
| `K.IC>ICS DONE: DONE  Erase Cycle Complete.` | 276 |
| `ICS>OBS ERROR: SYNCHRONIZE  Failed to Start acquisition on one or more ICs` | 122 |
| `K.IC>OBS STATUS: SHCLOSE  Integration Remaining=165 sec.` | 113 |
| `K.IC>ICS DONE: DATASOURCE  Erase Cycle Complete.` | 101 |
| `K.IC>{OBS,ICS} STATUS: FOUND  Integration Remaining=…` | 103 |
| `K.IC>OBS STATUS: {DONE,PROJID,OBJECT,PING,PONG,STATUS,EXP}  Integration Remaining=…` | 각 1~154 |
| `ICS>OBS STATUS: PING  Remaining=24 sec. of 30 sec.` | 5 |
| `ICS>OBS ERROR: EXPNUM  Failed to Start acquisition on one or more ICs` | 1 |

**올바른 형태**는 같은 본문이 빈 커맨드워드로 나가는 것이다 — `K.IC>OBS STATUS: Integration Remaining=9 sec.`(152,847회), `K.IC>ICS DONE: Erase Cycle Complete.`(141,435회).

**증거 세 가지**

1. **같은 본문이 제각각인 커맨드워드를 달고 나간다.** `Integration Remaining=` 하나만 놓고 봐도 빈 값 / `REQ` / `SHOPEN` / `DATASOURCE` / `FLASHNOW` / `DONE` / `PROJID` / `OBJECT` / `PING` / `PONG` / `FOUND` / `STATUS` / `EXP` 가 모두 관측된다.
2. **`REQ`·`DONE`·`PONG`·`FOUND` 같은 프로토콜 키워드가 커맨드워드 자리에 나타난다.** 검증된 명령 테이블이 아니라 **직전 파싱 토큰**에서 슬롯이 채워졌다는 뜻이다. `REQ` 가 1위인 것은 IMPv2에서 타입 생략 시 암묵 기본값이 `REQ` 이기 때문으로 보인다.
3. **인과가 로그에서 직접 보인다.** SSO `isis.20240111.log` 등에서 `OBS>*.IC datasource ctc` → `*.IC>OBS DONE: DATASOURCE  DataSource=…` 직후, 같은 노출의 다음 비동기 카운트다운이 `K.IC>OBS STATUS: DATASOURCE  Integration Remaining=5 sec.` 로 나간다. 명령을 받은 적 없는 `PING`/`PONG` 까지 슬롯에 남는 것도 같은 경로다.

### 5.6.2 현상 B — 누적(2단계 이상) 오염

잔재가 하나로 끝나지 않고 **겹쳐 쌓이며 본문을 밀어내 소실**시킨다:

| 실측 | 사이트/건수 | 해석 |
|---|---|---|
| `ICS>OBS STATUS: SYNCHRONIZE STATUS:` | CTIO 14 | 커맨드워드 `SYNCHRONIZE` + 잔재 `STATUS:` + **본문 완전 소실** |
| `ICS>OBS STATUS: PING STATUS: EXPSTATUS=INTEGRATING` | SSO 1 | 잔재 2개(`PING`,`STATUS:`)가 연달아 |
| `K.IC>ICS DONE: EXP  FLAT  ImageType=FLAT ObjectName='flat' EXP=30` | CTIO 각 IC 2 | 커맨드워드 **2개**(`EXP`,`FLAT`) 적층 |
| `ICS>OBS DONE: PROJID  ProjID=ALL BIAS BIAS` | SAAO 5 | 이전 메시지 잔재가 **꼬리에 2회 반복** |
| `ICS>OBS STATUS: EXPNUM` | CTIO 1 | 슬롯만 남고 본문 전부 소실 |
| `ICS>OBS STATUS: : EXPSTATUS=INTEGRATING` | CTIO 1 | 슬롯이 콜론 한 글자로 잘림 |

### 5.6.3 현상 C — 버퍼 겹침·전송 절단 (비결정론적, 데이터 손실 동반)

문자열이 **중간부터 겹쳐 쓰여** 토큰이 깨진다. 발신·수신 양쪽에서 관측된다:

```
K.IC>ICS DONE: INITIALIZitialization Complete.     ← "INITIALIZE"+"Initialization Complete." 겹침
ICS>T.IC STATUS: TCSSTATUS  DATE5-04-03T06:26:41   ← "DATE-OBS=2025"가 "DATE5"로 (7자 소실)
ICS>T.IC STATUS: AUXTATUS  ENS7=…                  ← "AUXSTATUS" → "AUXTATUS"
M.IC>ICS ERROR: OBCT  Didn't understand OBCT BLG37 ?           ← 수신측: "OBJECT"가 "OBCT"로
K.IC>ICS ERROR: N  Didn't understand N 60 OBS USESTATUS ?      ← "SHOPEN 60 …"이 "N 60 …"로
K.IC>ICS ERROR: EN  Didn't understand EN 60 OBS USESTATUS ?    ← 〃 (SSO)
M.IC>ICS ERROR: STATUSTUS  Didn't understand STATUSTUS  DATE-OBS= ?   ← 두 메시지 접합 (SAAO)
K.IC>0 STATUS: EXP  Integration Remaining=145 sec.             ← 수신 노드명이 "0"으로 파괴
```

**운영 영향이 실재한다**: `SHOPEN 60 OBS USESTATUS` 가 `N 60 …` 으로 깨져 K.IC가 거부한 건은 **셔터가 열리지 않은 노출**을 뜻한다.

**원인 추정과 그 함의**: 이 계열 손상은 **`ICS`↔`XIS` 링크에 집중된다.** 1.3절 포트 표에서 보듯 이 구간만 시리얼(`/dev/ttyS0`)이고 나머지 노드는 전부 UDP다. **신규 시스템이 UDP로 가면 이 계열 손상은 구조적으로 사라진다** — 셔터가 열리지 않은 노출 같은 실제 데이터 손실이 없어진다는 뜻이므로, 그 자체로 전환의 근거가 된다.

### 5.6.4 신규 구현이 지켜야 할 규칙

1. **커맨드워드를 매 메시지마다 명시적으로 정한다.** 비동기 상태 메시지는 빈 문자열을 **명시적으로** 넘긴다. 전역/멤버 상태에서 물려받는 경로를 만들지 않는다.
2. **메시지 조립은 매번 새 버퍼.** 재사용 버퍼 금지.
3. **`EXPSTATUS=` 알림은 상태 전이 시점에 1회씩만, `OBS` 로만** 보낸다(8.0.1절 (6)).
4. **송신 직전 자체 검증**을 넣는다 — 본문에 메시지 타입 키워드 재등장 금지, 커맨드워드 적층 금지, 본문과 커맨드워드의 정합 확인.
5. **수신은 관대하게** — 깨진 명령은 크래시 없이 레거시와 같은 `ERROR: <cmd>  Didn't understand <cmd> <args> ?` 로 거부한다.

> **중요**: 이 버그는 **OBSAgent 동작에 영향이 없다.** OBSAgent의 `CamStatus` 는 커맨드워드가 아니라 본문 부분문자열만 보기 때문이다(8.0.1절). 그래서 레거시가 수년간 이 상태로 운용될 수 있었다. 신규 구현에서 고치는 것은 정확성과 디버깅 편의를 위한 것이지 호환성 때문이 아니다.

### 5.6.5 왜 `ICS` 와 `K.IC` 가 같은 버그를 갖는가 (2026-08-04 확인)

5.6.1절 표를 보면 오염이 `ICS` 와 `K.IC` 양쪽에서 똑같은 형태로 나타난다. 처음에는 "같은 코드베이스로 추정"이라고만 적었는데, **1.3.1절에서 확정됐다** — `ICS` 는 별도 프로그램이 아니라 IC 와 **같은 `IC.BAT` 소프트웨어**를 `INSTRUMENT=ICS` 로 설정해 돌리는 것이다(프로그램 디렉토리만 `\KMTX` vs `\KMTS`).

즉 이 버그는 **IC 소프트웨어 한 곳의 결함**이고, ICS·K/M/T/N.IC·G.IC 가 전부 같은 증상을 보이는 것이 당연하다. 빌드 시점이 달라(`KX2016-03-23` vs `KS2016-01-13` vs `KG2016-06-02`) 세부 빈도에는 차이가 있을 수 있다.

**IC(VDOS) 소스는 이 저장소에 없다.** `__dts_legacy/` 는 리눅스 측(icsci 서버) 백업이라 XIS 서버·relay·Caliban 소스는 있으나, VDOS 머신에서 도는 `\KMTS`/`\KMTX`/`\KMTG` 프로그램은 포함되지 않았다. 따라서 **버그의 정확한 코드 위치는 여전히 미확인**이며, 5.6절의 분석은 로그 실측 기반이다.

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
| `__ICIMACS/osu etc/spie3.pdf` | **검토 완료** — OSU ISL(Imaging Sciences Laboratory) 연구소 소개 논문(~1998). ICIMACS를 만든 조직의 배경: "소프트웨어 최소화" 철학, IFPS/OSIRIS/MOSAIC/ANDICAM 등 계측기 목록. ANDICAM(CTIO 1m)이 여기 등장 — [TCSAgent](../TCSAgent/tcsagent_report.md)의 원조(pctcs Agent, Yale 1m/ANDICAM용)와 연결되는 배경. KMTNet 직접 관련 정보는 없음 |
| `__ICIMACS/osu etc/P-atwood-poster.pdf` | **검토 완료** — "Early Results from the MODS 8k x 3k CCDs"(B. Atwood, OSU) 포스터. LBT MODS 분광기용 e2v CCD231-68 + ICIMACS 검출기 전자부 초기 결과(2009년경). KMTNet 직접 관련 없음, 배경자료로 마감 |
| `__ICIMACS/osu etc/*.url`, `__ICIMACS/*.url` | OSU 웹페이지 바로가기(오래된 링크, 대부분 접속 불가 추정) — 미검토 |
| `__sample_isislog/isislog.{ctio,saao,sso}/isis.*.log` | 3개 사이트, 2024~2025년 실제 ISIS 런타임 로그 샘플 (본 보고서 4~5절의 실측 근거). `*.log` 는 `.gitignore` 로 **비커밋** |
| `__sample_isislog/samples_for_bug.txt` | **검토 완료** — 사용자가 직접 추린 메시지 오염 사례 2,755행 (5.6절 근거). `.txt` 라 **커밋 대상** |
| `__sample_isislog/samples_for_bug_integrat.txt` | **검토 완료** — 노출 국면(`INTEGRATING`)·카운트다운 구간 발췌 3,061행. 5.6.1절의 스테일 커맨드워드(`REQ`/`SHOPEN`/`DATASOURCE`)와 "셔터 닫힌 뒤에도 `EXPSTATUS=INTEGRATING` 반복" 패턴의 근거. **커밋 대상** |
| `__sample_isislog/samples_for_bug_pctread.txt` | **검토 완료** — readout 진행률 발췌 2,940행(노출 294회분). `6·17·28·39·50·61·72·83·94·100` 이 **각각 정확히 294회**로 편차 0 — 레거시 IC 가 진행률을 실제 픽셀 카운트가 아니라 **고정 스텝**으로 보고했음을 보여준다(5.2절). **커밋 대상** |
| `../../__localonly_isislogs/ISIS.ICSci.{CTIO,SAAO,SSO}.*` | **전량 검토 완료 (2026-08-03)** — CTIO 634일(28GB, 2024-01-01~2025-09-30) + SAAO 273일(11GB, 2025) + SSO 206일(8.6GB, 2024-01-01~2024-07-25) = **48GB, 1,113일분**. 3.5·5.2·5.3·5.4·5.6·6절 신규 항목의 근거. `__localonly_*` 규약에 따라 **비커밋** |
| **`__dts_legacy/dts.icsci.*.{ctio,saao,sso}/`** | **2026-08-04 신규** — ICS 컴퓨터(icsci 서버)의 `dts` 폴더를 사이트별로 백업한 것 중 **소스·설정만 선별**해 커밋(2,830 파일 / 24.7 MB). **ISIS/XIS 서버 소스 전체**를 포함한다. 1.3.1·5.6.5·8.0.1절의 근거 |
| `../../__localonly_dts.icsci/` | 위 백업의 **원본 전량과 부속 자료**(10,289 파일 / 580 MB). `__localonly_*` 규약에 따라 **비커밋**:<br>· `dts.icsci.20190326.{ctio,saao,sso}/` — 압축 푼 원본 442 MB. 커밋본에서 뺀 `Tools/`(서드파티 109 MB/사이트) · `catalog/` · `osc/` · 빌드산출물(`.o` `.a` `.tar`) · 홈 디렉토리 dotfile(**`.ssh`/`.gnupg` 포함 — 자격증명 우려로 제외**)이 들어 있다<br>· `dts.icsci.20190326.*.zip` — 원본 압축본<br>· `memo.txt` — IC2 이미지 경로 (1.3.1③의 근거)<br>· `IC2.KX20160323.1381_icsci_ctio/` — ICS VM 이미지를 놓을 자리 (현재 비어 있음) |

**`__dts_legacy/` 안에서 특히 중요한 것**

| 경로 | 내용 |
|---|---|
| `EXEC_ISIS/server/` | **XIS 서버 소스 전체** — `clients.c`(클라이언트 테이블) · `messages.c`(라우팅·브로드캐스트) · `interfaces.c`(`handShake()`) · `main.c`(기동 순서) · `loadconfig.c` · `xisisserver.h`. 8.0.1절 (13)의 근거 |
| `ISIS_V1/server/` | 구버전 ISIS 서버 소스 (비교용) |
| `EXEC_ISIS/client/`, `ISIS_V1/client/` | ISIS 클라이언트 라이브러리. `../TCSAgent/__reference/ISISclient` 와 `../OBSAgent/OBSAgent.latest/ISISclient` 에도 같은 것이 있다 |
| `Config/isis.ini` | **운영 중인 XIS 설정** — `ServerID XIS` / `ServerPort 6660` / `TTYPort /dev/ttyS0 115200` / `UDPPort` preset 13줄 |
| `Config/{K,M,T,N,G,SP}.IC.ini`, `Config/ICS.ini` | **VDOS IC 부팅·설정 파일** — 1.3.1절의 근거 |
| `Config/isisrelay.ini`, `ISIS_V1/relay/` | UDP↔시리얼 중계기 설정과 소스 |
| `Agents_V1/Caliban/src/` | **`*.CB` 노드(Caliban)의 소스** — `TransferDisk.c` · `InitDisk.c` · `UseDisk.c` · `AckDisk.c` 등. 4.2절 디스크 핸드셰이크의 구현체 (미검토) |
| `Agents_V1/tvdisp/` | 표시용 에이전트 (미검토) |

> **미검토로 남긴 것**: `Agents_V1/Caliban/src/`(CB 노드 소스)와 `Agents_V1/tvdisp/`. 신규 설계에서 CB 계층은 통째로 내부화되어 사라지므로(8.0절) 우선순위가 낮다고 판단했다. 다만 **`TransferDisk.c`/`InitDisk.c` 는 4.2절 디스크 핸드셰이크와 5.5절 파일명 fail-safe 의 실제 구현**이므로, 그 동작을 정확히 알아야 할 일이 생기면 여기부터 볼 것.
>
> **IC(VDOS) 본체 소스는 이 백업에 없다** — `\KMTS`/`\KMTX`/`\KMTG` 프로그램은 KVM 게스트의 디스크 이미지(`IC2.img`, 1.3.1③) 안에 있고 이 백업은 리눅스 호스트 측이다. 5.6절 오염 버그의 코드 위치를 확정하려면 그 이미지가 필요하다.
>
> **`IC2.img` 를 확보하면 할 수 있는 것**: 이미지는 8 GB 이지만 실제 프로그램은 `\KMTS`/`\KMTX`/`\KMTG` 디렉토리 몇 MB 다. 7-Zip 이나 loop 마운트로 그 부분만 뽑아내면 (a) 로그에 한 번도 안 나온 메시지까지 포함한 **완전한 메시지 카탈로그**, (b) `printf` 포맷 문자열에서 **메시지 조립 구조** — 5.6절 오염의 메커니즘을 직접 확인할 실마리, (c) 세 디렉토리 비교로 ICS/IC/ICG 의 차이를 얻을 수 있다.
> 다만 **16비트 DOS 바이너리 역어셈블은 실용적이지 않다.** 소스가 함께 들어 있지 않다면 문자열·포맷 추출까지가 현실적인 선이다.

> **재검증 방법**: 위 로그가 있는 컴퓨터에서 [`../ics_sim/tools/scan_legacy_logs.py`](../ics_sim/tools/scan_legacy_logs.py) 로 언제든 다시 돌릴 수 있다.
> ```bash
> python tools/scan_legacy_logs.py slots     <logdir>   # 커맨드워드 슬롯 분류 (5.6절)
> python tools/scan_legacy_logs.py shapes    <logdir>   # 메시지 형태 목록 (새 시퀀스 발굴)
> python tools/scan_legacy_logs.py camstatus <logdir>   # OBSAgent CamStatus 재생 (8.0.1절)
> ```
> 로그 없이도 검증이 되도록 발췌본은 `../ics_sim/tests/fixtures/` 에 커밋해 두었다.

**이 폴더의 산출 문서 (분석 결과물)**

| 문서 | 범위 |
|---|---|
| `ics_legacy_report.md` (본 문서) | 시스템 전체 — 아키텍처, IMPv2.5 프로토콜, ICS/IC 명령어, 과학 노출 트랜잭션, ISIS 클라이언트 라이브러리 |
| [`icg_legacy_report.md`](icg_legacy_report.md) | **`ICG` 노드 전용 기술 레퍼런스** — 가이드 계통 오케스트레이션, `G.IC`/`G.CB` 계층, ICS와의 상세 비교, 신규 `icg` 구현 명세. 근거는 전적으로 위 XIS 로그 실측 |
| [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) | **신규 시뮬레이터 개발 노트** — 본 보고서의 규약을 실제로 구현·검증한 결과. 설계 결정 기록, 정정 이력, 개선 백로그 |

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

**후속 확인**: KMTNet이 실제 운영 중인 `TC` 노드가 바로 이 `pctcs`의 직계 후손이다 — KASI가 시리얼 직결을 Telcom TCP + AUX TCP로 바꾸고 크게 확장한 버전(v1.7.2)을 별도 분석했다. [../TCSAgent/tcsagent_report.md](../TCSAgent/tcsagent_report.md) 참고. 나아가 관측 콘솔 `OBS` 노드(OBSAgent)도 그 TCSAgent 코드베이스를 다시 포크해 만든 것이다([../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md)) — 즉 여기서 분석한 `pctcs` 소스가 KMTNet 레거시 제어 프로그램 전체 계보의 뿌리다.

### 7.5 발신 메시지 큐잉 패턴 — `dispatcher.cpp/h` (MODS Qt GUI 클라이언트)

`ISISclient docu/dispatcher.cpp.pdf`, `dispatcher.h.pdf`에서 확인. 이건 ISIS 서버가 아니라 MODS(OSU 분광기)용 Qt 기반 GUI 클라이언트(modsUI)에 쓰인 **발신 메시지 큐**로, KMTNet 코드 자체는 아니지만 신규 구현에 참고할 만한 범용 패턴이다.

- `Dispatcher`는 `QThread`를 상속한 큐 스레드: `addMessage(host, msg)`로 메시지를 큐에 쌓으면, 별도 스레드가 하나씩 꺼내 `dispatch` 시그널로 내보내고, **설정 가능한 cadence(기본 딜레이)만큼 대기한 뒤 다음 메시지를 처리**한다 (`dispatchCadence`, 기본 단위 msec).
- `abort()`로 큐를 즉시 비우고 중단 가능, `numPending()`/`queueList()`로 큐 상태 조회 가능, 뮤텍스로 스레드 안전성 확보.
- **의의**: 같은 수신 노드로 메시지를 너무 빨리 연속으로 쏘면(예: 여러 IC에 순차 명령을 뿌릴 때) 수신측이 처리를 못 따라가거나 UDP 유실이 생길 수 있는데, 이런 속도 제한(rate-limit)이 있는 발신 큐를 별도 컴포넌트로 두는 게 legacy에서도 쓰인 검증된 패턴이다. 신규 Python ICS에서 `asyncio.Queue` + 주기적 dequeue 태스크로 동일한 패턴을 재현할 만하다.

---

## 8. 신규 Python ICS 개발 시 고려사항 (메모)

### 8.0 확정된 신규 구조 (2026-07-29)

신규 시스템은 **`ics`와 `icg` 두 프로그램으로 분리**하되, 각각이 레거시의 여러 노드를 흡수한다:

| 신규 프로그램 | 흡수하는 레거시 노드 | 노드 수 |
|---|---|---|
| **`ics`** (과학) | `ICS` + `K/M/T/N.IC` + `K/M/T/N.CB` | **9** |
| **`icg`** (가이드) | `ICG` + `G.IC` + `G.CB` | **3** ([icg_legacy_report.md](icg_legacy_report.md) 참고) |

**신규 `ics` 관점에서 내부화되어 사라지는 경계** (아래 절들에서 분석한 프로토콜이 함수 호출로 대체됨):
- `ICS → K/M/T/N.IC`: 4개 CCD에 대한 동기화된 명령 전파(`GO`, `INITIALIZE`, 설정 브로드캐스트) — 4노드 동시 제어가 **프로그램 내부의 병렬 처리 문제**로 바뀐다. 지금 로그에서 보이는 "4개 IC의 응답을 각각 기다렸다가 다음 단계로" 하는 조율이 내부 상태머신으로 흡수된다.
- `K/M/T/N.IC ↔ K/M/T/N.CB`: `TRANSFER DISK<n> 1 ICS` / `DONE DISK<n>` / `REQ SWAP`↔`ACK SWAP` / 디스크 초기화 핸드셰이크(4.2절) — 전부 내부 이벤트·큐로 대체
- `K.IC>XIS PING/PONG`을 디스크 쓰기 완료 신호로 쓰던 관례(4.2절) — 내부 완료 콜백으로 대체되어 이 편법 자체가 불필요해진다

**유지해야 할 외부 인터페이스**:
- **`OBS`(OBSAgent)와의 메시지 호환 — 확정 방침**: 통합 후에도 **OBSAgent는 개정하지 않는다.** 신규 `ics`가 내부적으로는 4개 CCD를 한 프로그램에서 다루더라도, **바깥으로는 기존과 동일하게 CCD별 메시지(특히 "Acquisition Complete." 4회)를 그대로 발신**해 OBSAgent의 `CamStatus` 상태머신이 무개정으로 동작하게 한다. 구체적 규약은 아래 8.0.1절.
- `TC`(TCS Agent) 질의, `XIS` 허브 등록, 신규 `icg`와의 `SYNCHRONIZE`(유지/폐지 결정 필요)

#### 8.0.1 OBSAgent 호환 규약 (신규 `ics`가 지켜야 할 발신 규칙)

OBSAgent v1.2.0 소스(`commands.c` 748~865행, `main.c` 주기 루프)를 실측해 도출한 **정확한 규약**이다. 상세 근거는 [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md) 6절 참고.

**(1) 발신 노드 ID**: `CamStatus`에 영향을 주려면 발신자가 `ICS` / `{K,M,T,N}.IC` / `{K,M,T,N}.CB` 중 하나여야 한다(대소문자 무관). **통합 `ics`가 단일 노드 `ICS`로 등록해 모든 메시지를 `ICS` 이름으로 보내도 전부 이 필터를 통과**하므로, CCD별 가짜 노드 ID를 유지할 필요는 없다. (단 `ICG`/`G.IC`/`G.CB` 이름으로는 무시되므로, 신규 `icg`는 이 규약과 무관하다 — 아래 (5)번.)

**(2) 노출 1회당 반드시 발신해야 할 메시지 시퀀스** (`STATUS:` 타입, 본문에 해당 문자열 포함):

| 순서 | 메시지 본문 키 | 유발되는 CamStatus | 발신 횟수 |
|---|---|---|---|
| 1 | `EXPSTATUS=INITIALIZING` | `PREP_I` | 1 |
| 2 | `EXPSTATUS=ERASE` | `PREP_E` | 1 |
| 3 | `EXPSTATUS=INTEGRATING` | `INT_1` | 1 |
| 4 | `Shutter=Open` | `INT_2` (노출 시작 시각 기록) | 1 |
| 5 | `Remaining=` | `INT_3` | 1회 이상(주기 갱신) |
| 6 | `Shutter=Closed` | `CLOSING` | 1 |
| 7 | `EXPSTATUS=READOUT` | `READ_1` | 1 |
| 8 | `PCTREAD=` | `READ_2` → `READ_3` (카운터 리셋) | **2회 이상** |
| 9 | `Acquisition Complete.` | `IDLE_1` → 4회째에 `IDLE_2` | **정확히 4회 이상** |
| 10 | `EXPSTATUS=IDLE` | `IDLE_3` | 1 |
| 11 | `Wrote ... KMTNx.yyyymmdd.nnnnnn.fits ...` | 4회째에 `FitsSaved=1` | **4회 이상** |

**(3) 개수 규약이 핵심**: `Acquisition Complete.`(**마침표 포함**)와 `Wrote`는 각각 **4회 누적**되어야 `IDLE_2`/`FitsSaved=1`에 도달한다. 통합 후에도 CCD 4개분을 각각 보내면 기존 동작이 그대로 재현된다. `PCTREAD=` 수신이 두 카운터를 0으로 리셋하므로, 노출 사이클 순서를 지키는 것도 중요하다.

**(4) 형식 의존성 2건**:
- `Wrote` 메시지에서 `"KMTN"` 문자열 위치+6부터 15자를 잘라 `FitsNum`으로 표시한다 → **파일명 `KMTN<CCD>.<8자리날짜>.<6자리번호>.fits` 형식 유지 필수**.
- `READY`는 메시지가 아니라 **`IDLE_3` 후 약 12.2초 타이머**로 전이된다(소스에 `Disk Write Complete` 파서가 없음). 즉 신규 `ics`가 "저장 완료" 메시지를 새로 만들어 보내도 `READY`를 앞당길 수 없다 — 노출 간 최소 12초 간격은 OBSAgent 쪽 상수(`force_ready=270`)에 의해 정해진다는 뜻이다. 이 지연이 신규 시스템에서 문제가 된다면 그때는 OBSAgent 개정이 필요하다.

**(5) 신규 `icg`는 이 규약에서 자유롭다**: OBSAgent는 v0.3.2부터 `ICG`/`G.IC`/`G.CB` 발신 메시지를 **명시적으로 무시**한다(가이드가 같은 문자열을 뿌려도 과학 상태머신이 오염되지 않도록). 따라서 신규 `icg`는 메시지 형식을 자유롭게 현대화해도 OBSAgent에 영향이 없다 — `ics`와 `icg`의 하위호환 부담이 **비대칭**이라는 뜻이다.

---

#### 8.0.1 보강 (2026-08-03) — 실행 검증에서 추가된 6개 항목

아래는 위 (1)~(5)를 실제로 구현·실행해 검증하는 과정([`../ics_sim/`](../ics_sim/))에서 **새로 확인되거나 빠져 있던** 항목이다. 전부 `ics_sim/tests/test_obsagent_contract.py` 가 자동 검증한다.

**(6) 수신은 9개 노드 ID 전부 필요 — 발신과 비대칭이다**

위 (1)항은 "발신 노드 ID를 전부 `ICS` 로 해도 필터를 통과한다"만 서술했는데, **수신 쪽은 그렇지 않다.** OBSAgent는 명령마다 수신 노드를 달리 지정한다:

| OBSAgent 명령 | 보내는 곳 | 소스 |
|---|---|---|
| `status` · `acqstatus` · `filename` · `expnum` · `ledflash` · `observer` · `projid` · `exp` · `go` · 이미지타입 7종 | `ICS` | `commands.c` 1889·1915·1939 |
| `kstatus` · `mstatus` · `tstatus` · `nstatus` | `K.IC` · `M.IC` · `T.IC` · `N.IC` | 2015~2080 |
| `dmawait` | `K.IC` | 1968 |
| `datasource` | `K.IC` · `M.IC` · `T.IC` · `N.IC` (4회) | 1987 |

→ **통합 `ics` 가 `ICS` 하나로만 등록하면 `kstatus`/`dmawait`/`datasource` 가 도달조차 하지 않는다.** 9개 ID(`ICS` + `{K,M,T,N}.IC` + `{K,M,T,N}.CB`) 전부로 받아야 한다.

**(7) `ExpNum` 자동 질의에 반드시 응답해야 한다**

`commands.c` 797~803행: readout 중 **첫 `PCTREAD=`** 를 받아 `READ_1` 일 때 OBSAgent가 **스스로** `OBS>ICS ExpNum` 을 보낸다.

```
OBS>ICS ExpNum
ICS>OBS DONE: EXPNUM  Filename=20250902.057288 EXPSTATUS=READOUT
```

- 응답의 `Filename=` 값(**정확히 15자**, `strncpy(expinfo.strNextNum, pstr+9, 15)`)이 `expinfo.strNextNum` 이 되고, 다음 노출의 `Shutter=Open`(또는 `EXPSTATUS=INTEGRATING`) 시점에 `strCurNum` 으로 승격된다.
- **목적**: 카메라 제어가 아니라 **상태 표시용**이다. `expinfo`/`ee` 명령의 반환 문자열과 `/data/Logs/ObsStatus.txt` 의 `EXP.INFO:` 줄에 있는 `ExpNum` 필드를 채우는 **유일한 경로**다.
- **내력** (소스 서두 개정이력 주석 218~229행): **v1.0.1(2024-07-01)** *"Add ExpNum query to ICS and ExpNum(strNextNum/strCurNum) update"* 로 추가. `expinfo` 명령은 v1.0.0(2024-06-29), `ObsStatus.txt` 는 v1.0.3~1.0.4(2024-07-05)에 추가됐다. 후속 디버깅: v1.0.6(`dStartTime` 누락) · v1.0.7~1.0.8(SSO ExpNum 오류) · v1.0.9(`strPreNum`/`FitsOsc`) · **v1.1.3(2024-07-18)** *"Debug momentary unmatch of ExpNum and ExpStatus, Debug missing ExpNum/ExpStart update in dark/bias mode"*.
- **응답하지 않으면**: 카메라 동작 자체는 정상이지만 `ExpNum` 이 갱신되지 않아 `expinfo`·`ObsStatus.txt`·`GMON` 표시가 이전 값이나 `00000000.000000` 에 머문다.
- 실측: CTIO 아카이브에서 **125,451회**. **2024-03 로그에는 없고 2025 로그에만 있는 것이 v1.0.1 도입 시점(2024-07)과 정확히 일치한다.**

**(8) 하드 타임아웃 4종의 정확한 창** (`main.c` 650~708, 1카운트 ≈ 0.045초)

| 조건 | 상수 | 시간 | 초과 시 |
|---|---|---|---|
| 1번째 → 4번째 `Acquisition Complete.` | `force_idle=40` | ≈1.8초 | `IDLE_3` 강제 + **`opause`(스크립트 정지)** + `ERROR: Acquisition is not fully completed !!` |
| 4번째 `Acquisition Complete.` → `EXPSTATUS=IDLE` | `force_idle/2=20` | ≈0.9초 | `IDLE_3` 강제 + `WARNING: No 'EXPSTATUS=IDLE' message from ICS` |
| `IDLE_3` 진입 → 4번째 `Wrote` | `force_fitssaved=560` | ≈25초 | `FitsSaved=1` 강제 + `WARNING: Writing FITS data is not fully completed !!` + `ExpStatus=ERROR` |
| `IDLE_3` → `READY` | `force_ready=270` | ≈12.2초 | (정상 전이, 위 (4)항) |

실측 레거시는 4개 `Acquisition Complete.` 가 ~3ms 안에, `EXPSTATUS=IDLE` 이 0.38초 뒤에 도착한다. **첫 번째 창을 넘기면 야간 스크립트 관측이 실제로 멈춘다**는 점이 특히 중요하다.

**(9) `Wrote` 가 OBSAgent에 닿는 경로는 ICS 중계다**

`K.CB>ICS DONE: Wrote …` 는 **`ICS` 앞으로** 가고, OBSAgent가 실제로 세는 것은 `ICS>OBS STATUS: Wrote LASTFILE=… RATE=…` **중계 메시지 4개**다. 근거: `case DONE:` 블록에는 `Wrote` 핸들러가 없다(`commands.c` 935~966). 위 (2)항 표의 11번 항목이 이 중계를 뜻한다.

**(10) 텔레메트리는 필드 순서를 뒤집어 중계한다**

5.3.1절 참고. 그리고 필드 집합이 사이트마다 다르므로(5.3.2절) **pass-through 로 다루고 없는 필드는 sentinel 로 채우는 편**이 낫다.

**(11) 상태 전이는 선형이 아니며, `EXPSTATUS=` 과다 발신은 역행을 만든다**

샘플 로그(노출 약 28,200회)에 CamStatus 체인을 재생한 실측 결과 (**`dest ∈ {OBS, AL, ALL}` 필터 적용**):

| 전이 | 트리거 | 횟수 |
|---|---|---:|
| `INT_1 → INT_2` | `Shutter=Open` | 26,701 |
| `INT_2 → INT_3` | `Remaining=` | 26,706 |
| `INT_3 → CLOSING` | `Shutter=Closed` | 27,073 |
| **`INT_1 → CLOSING`** (INT_2·INT_3 건너뜀) | `Shutter=Closed` | **1,252** |
| **`INT_1 → INT_3`** (INT_2 건너뜀) | `Remaining=` | **262** |
| **`INT_2 → CLOSING`** (INT_3 건너뜀) | `Shutter=Closed` | **91** |
| **역행 (`INT_3 → INT_1` 등)** | — | **0** |

- `Shutter=Closed Integration Remaining=0 sec.` 은 `Remaining=` 을 품고 있어도 체인 순서상 **항상 `CLOSING`** 이 된다. 다만 앞선 순수 `Remaining=` 카운트다운이 이미 `INT_3` 을 만들어 두므로 `INT_2 → CLOSING` 직행은 0.34%에 불과하다.
- **흔한 건너뜀은 `INT_1 → CLOSING`** 이다 — DARK/BIAS는 `Shutter=Open` 이 없기 때문이다. **그럼에도 `Shutter=Closed` 는 보내므로 `CLOSING` 은 정상적으로 밟힌다.** 신규도 이 관례를 유지해야 한다(없애면 `CLOSING` 을 건너뛴다).
- **역행이 0건인 이유가 중요하다.** 레거시가 `EXPSTATUS=` 를 담은 텔레메트리 중계를 마구 뿌려도 안전했던 것은 **그것이 `OBS` 가 아니라 `*.IC` 앞으로 갔기 때문**이다. 통합 `ics` 는 IC들이 내부 객체가 되어 그 중계가 사라지는데, 편의상 **브로드캐스트(`AL`)하거나 `OBS` 로도 보내면 `CamStatus` 가 `INT_1` 으로 역행해 스크립트 관측이 깨진다.**
  → **`EXPSTATUS=` 를 포함한 메시지는 노출 상태가 실제로 전이한 시점에 정확히 1회씩만, `OBS` 로만 보낸다.** 레거시처럼 셔터가 닫힌 뒤에도 `INTEGRATING` 을 반복해서는 안 된다.

**(12) `GO n` 다중 노출의 종료 알림은 `STATUS:` 다**

3.5절 참고 — 중간 프레임은 `STATUS: Image n of N complete. EXPSTATUS=IDLE`, 마지막 프레임만 `DONE: EXPSTATUS=IDLE`. 그리고 프레임 N의 `Wrote` 4개가 프레임 N+1의 `PCTREAD=` **전에** 도착해야 `FitsSaved` 가 선다.

**(13) XIS 노드 등록 — 서버 소스로 확정 (2026-08-04)**

`__dts_legacy/.../EXEC_ISIS/server/` 의 XIS 서버 소스로 신규 통합 `ics` 의 등록 방식이 확정됐다.

- **클라이언트 테이블은 노드 ID 로만 키잉된다.** `clients.c` `updateHosts()` 가 `strcmp(testStr, clientTab[i].ID)==0` 로만 비교하고(ID는 대문자 정규화), 주소는 저장·갱신만 될 뿐 비교에 쓰이지 않는다. **주소 충돌 검사 로직 자체가 없다.**
  → **통합 `ics` 가 소켓 하나에서 9개 노드 ID 를 전부 등록해도 안전하다.** 노드마다 포트를 따로 열 필요가 없다.
  → `messages.c` 의 브로드캐스트 코드가 *"clients that share the same port as the sending host"* 를 명시적으로 다루므로, **한 포트를 여러 클라이언트가 공유하는 것은 설계상 예상된 상황**이다.
- **등록 방법은 "그 이름으로 아무 메시지나 보내기"** 뿐이다. 별도 API 가 없다. 따라서 **수신하려는 9개 ID 전부로 한 번씩 보내야** 그 이름 앞으로 오는 명령(`kstatus`/`dmawait`/`datasource`)이 도달한다.
- **XIS 재시작 시 재등록**: `interfaces.c` `handShake()` 가 `"<ServerID>>AL PING\r"` 을 **모든 시리얼 포트 + `isis.ini` 의 preset UDP 목록**에 개별 전송한다(IP 브로드캐스트가 아니다). 돌아오는 PONG 으로 테이블을 다시 채운다.
  → **신규 `ics` 는 이 브로드캐스트 PING 에 9개 ID 전부로 PONG 해야 한다.** 하나만 답하면 나머지 8개가 죽는다. 레거시는 노드마다 프로세스가 따로라 각자 답했다.
  → **신규 `ics` 의 주소를 XIS `isis.ini` 의 `UDPPort` 목록에 추가**해야 재시작 시 PING 을 받는다. 지금 `.109`(OBS)가 목록에 없어 재시작 직후 `No Route to Destination Host OBS` 가 나는 것과 같은 문제가 생긴다.
- **테이블 크기는 `MAXCLIENTS 64`** — 현재 13개 안팎이므로 여유는 충분하다.
- **`AL` 브로드캐스트는 슬롯 전수 순회**라, 9개 ID 가 같은 주소면 같은 데이터그램을 9번 받는다. 기능상 문제는 없으나 수신 트래픽이 9배가 된다.
- **미해결**: `xisisserver.h` 는 `MAXPRESET 8` 인데 CTIO `isis.ini` 에는 `UDPPort` 가 13줄이고 `loadconfig.c` 는 초과분을 버린다. 그런데 재시작 로그에는 9번째 이후 노드도 PONG 을 보낸다 → **배포 바이너리가 다른 값으로 빌드됐을 가능성**(ini 주석은 "max 32"). 실물에서 XIS 콘솔 `info` 로 `NumPreset/MaxPreset` 을 확인할 것.

> 상세한 조사 과정과 코드 인용은 [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 3.1.1절.

**공통 로직은 공유 라이브러리로**: IMPv2 노드(UDP·파서·등록), `TC` 질의와 FITS 헤더 중계, `SYNCHRONIZE`, 디스크 이중버퍼, 파일명 fail-safe는 `ics`/`icg`가 사실상 동일하다. 레거시도 동일 코드베이스(`KX` 빌드)로 추정되므로 이 공유는 원 구조에도 부합한다. 구현 순서는 **단순한 `icg`를 먼저** 만들어 골격을 검증한 뒤 `ics`로 확장하는 편이 안전하다([icg_legacy_report.md](icg_legacy_report.md) 7.3절).

### 8.1 프로토콜·구현 세부 고려사항

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

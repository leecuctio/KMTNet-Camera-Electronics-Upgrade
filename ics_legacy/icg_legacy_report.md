# ICG (Guide-camera Integrator) — Technical Reference Report

KMTNet 레거시 관측 시스템의 **`ICG` 노드**(가이드 카메라 통합제어)에 대한 기술 레퍼런스다. [ics_legacy_report.md](ics_legacy_report.md)가 시스템 전체(ICS·프로토콜·허브)를 다루는 데 비해, 이 문서는 **가이드 계통의 상위 제어자인 ICG 하나를 깊이 파서** 명령어·트랜잭션·에러 패턴을 정리한다. **배경지식이 없어도 읽을 수 있도록** 맥락부터 설명한다.

- **근거 자료**: ICG는 자체 문서·소스코드·로그가 이 저장소에 **없다**. 유일한 정본은 `__sample_isislog/`의 XIS(ISIS 허브) 런타임 로그(3개 사이트 × 2024~2025년 샘플, 총 ~2.7GB)이며, 이 보고서의 모든 서술은 그 로그에서 실측 추출한 것이다. 아래 정량 수치(명령 횟수 등)는 이 로그 샘플 전체 집계 기준이다.
- 프로토콜(IMPv2.5)과 노드 개념은 [ics_legacy_report.md](ics_legacy_report.md) 1~2절을 먼저 읽으면 좋다.

> **신규 개발 방향 (2026-07-29 확정)**: 신규 Python 시스템은 **`ics`와 `icg` 두 프로그램으로 분리**하되, 각각이 레거시의 여러 노드를 흡수한다.
> - **신규 `ics`** = 레거시 `ICS` + `K/M/T/N.IC` 4개 + `K/M/T/N.CB` 4개 (총 9개 노드)
> - **신규 `icg`** = 레거시 `ICG` + `G.IC` + `G.CB` (총 3개 노드) ← **이 보고서가 다루는 범위 전체**
>
> 따라서 이 보고서는 단순한 레거시 기록이 아니라 **신규 `icg`가 구현해야 할 기능의 명세서**로도 읽어야 한다. 어떤 통신 경계가 프로그램 내부로 사라지고 어떤 것이 외부 인터페이스로 남는지는 §9에서 정리했다.

---

## 1. 한눈에 보기

**ICG**(Instrument Control – Guide로 추정)는 **ICS의 가이드 카메라판**이다. KMTNet 카메라는 과학 CCD 4개(K/M/T/N)와 **가이드 CCD 4개**(4방위 배치: south/east/north/west)를 갖는데, 과학 쪽을 `ICS`가 통합 제어하듯 가이드 쪽을 `ICG`가 통합 제어한다.

```
      과학 계통                          가이드 계통
  OBS (관측 콘솔) ──┐              ABC (자동 가이딩 제어) ──┐
                    ▼                                       ▼
  ICS (과학 통합제어)               ICG (가이드 통합제어)  ← 이 문서의 대상
                    │                                       │
        ┌───┬───┬───┼───┐                                   │
        ▼   ▼   ▼   ▼                                       ▼
      K.IC M.IC T.IC N.IC                                 G.IC (가이드 CCD 4개 통합)
        │   │   │   │                                       │
      K.CB M.CB T.CB N.CB                                 G.CB (디스크/전송)
                    
              TC (TCS Agent) ←── 양쪽 계통이 각자 AUXSTATUS/TCSSTATUS 질의
```

핵심 역할 4가지 (전부 로그에서 실측 확인):
1. **가이드 노출 오케스트레이션**: `ABC`의 `go` 한 마디를 받아 `INITIALIZE`(파일명 시퀀스 초기화) → TCS/AUX 상태 수집 → `G.IC`에 헤더 정보 전달 → `GO` 발행의 전체 시퀀스로 풀어낸다.
2. **FITS 헤더용 망원경 정보 중계**: 노출마다 `TC`에 `AUXSTATUS`/`TCSSTATUS`를 질의해 `G.IC`에 `STATUS:` 메시지로 전달한다 — ICS가 과학 CCD에 하는 것과 같은 역할의 가이드판.
3. **설정 브로드캐스트(SYNCHRONIZE)**: 자신의 현재 설정(IMGTYPE/OBJNAME/EXP/OBSERVER/PROJID)을 `G.IC`뿐 아니라 **과학 IC 4개에도** 주기적으로 뿌린다(아래 5.1절 — 이 보고서의 주요 신규 발견).
4. **가이드 노출시간 관리**: `GUIDEEXP` 명령을 받아 저장하고 `G.IC`에 전파한다.

**ICS와의 결정적 차이**: ICS는 관측자(OBS)가 부리는 노드지만, ICG를 부리는 것은 사람이 아니라 **`ABC`(자동 가이딩 제어기)**다. 가이드 계통 전체가 자동 루프(ABC가 가이드 영상을 보고 `TC`에 초점/tip-tilt 보정을 피드백)의 부품으로 동작한다.

## 2. 시스템 안에서의 위치와 배치

- **노드명 `ICG`, UDP 포트 6600** (IC 계열 표준 포트).
- **실행 호스트**: CTIO 로그 기준 ICG는 `192.168.14.108`에서 실행된다 — 같은 호스트에 `TC`(:6606)와 `ABC`(임시 포트)도 있다. 즉 **ICG·TC(TCS Agent)·ABC는 모두 Guide server(ICGui)에서 함께 돈다**. 반면 `XIS`/`OBS`는 `.109`(Science server), `K/M/T/N.IC`는 `.102~.105`, `G.IC`는 `.106`의 별도 호스트다. 이는 [obsagent_report.md](../OBSAgent/obsagent_report.md) 3절의 "TCSAgent는 Guide server에서 실행" 운영 안내와 정확히 합치하는 실측 증거다.
- 사이트별 IP 대역: `192.168.14.x`=CTIO(KMTC), `192.168.13.x`=SAAO(KMTS), `192.168.15.x`=SSO(KMTA) — 세 사이트 로그 모두에서 동일한 호스트 배치 패턴(x.106=G.IC, x.108=ICG/TC/ABC)이 확인된다.

## 3. 통신 상대와 트래픽 프로필 (로그 샘플 전체 집계)

| 방향 | 상대 | 내용 | 횟수 (대략) |
|---|---|---|---|
| 수신 | `ABC` | `go`(가이드 노출 트리거), `guideexp <초>` | go 51,466 / guideexp 151 |
| 수신 | `G.IC` | `STATUS: GO ...`(노출 진행 보고), `DONE:`/`ERROR:` 응답 | STATUS 146,120 |
| 수신 | `TC` | `DONE: AUXSTATUS/TCSSTATUS`(질의 응답) | 102,862 |
| 발신 | `G.IC` | `INITIALIZE`, `GO`, `GUIDEEXP`, `STATUS 1`, `STATUS:`(TCS/AUX 중계, SYNCHRONIZE) | ~103,000 |
| 발신 | `TC` | `AUXSTATUS` + `TCSSTATUS` 질의 (노출당 1회씩 페어) | 각 51,431 |
| 발신 | `ABC` | `STATUS: GO ...`(진행 중계), `DONE: GUIDEEXP` | 51,431 + 150 |
| 발신 | `K/M/T/N.IC` | `STATUS 1` 조회 + `STATUS: SYNCHRONIZE` 브로드캐스트 | 각 ~405 |
| 발신 | `XIS` | `TIME`(시각 질의), `PONG` | 수십 회 |

수치가 말해주는 것: **GO 횟수(51,466) ≈ TCSSTATUS/AUXSTATUS 질의 횟수(각 51,431) ≈ ABC로의 진행 중계 횟수(51,431)** — 즉 "가이드 노출 1회 = TC 질의 1페어 = ABC 보고 1세트"라는 대응이 통계적으로 증명된다.

## 4. 명령어 레퍼런스

### 4.1 ICG가 받는 명령 (수신 인터페이스)

| 명령 | 발신자 | 인자 | 동작 |
|---|---|---|---|
| `GO` | `ABC` | 없음 | 가이드 노출 1사이클 전체를 오케스트레이션 (5.3절) |
| `GUIDEEXP` | `ABC` | `<초>` | 가이드 노출시간 설정. 즉시 `DONE: GUIDEEXP GuideExp=<n> seconds.` 응답 후 `G.IC`에 같은 명령 전파 (5.2절) |
| `PING` | `TC`, `XIS` 등 | 없음 | `PONG` 응답 (IMPv2 표준 생존 확인) |

관측된 수신 명령은 이게 전부다 — **ICG의 외부 인터페이스는 극도로 단순**하다(명령 2개 + ping). 노출 설정의 나머지(IMGTYPE, OBJNAME 등)는 ICG가 자체 보유한 값을 쓰며, 이를 바꾸는 명령은 로그 샘플에서 관측되지 않았다(ICS의 `OBJECT`/`DARK`/`EXP` 같은 설정 명령이 ICG에도 있을 가능성은 있으나 미확인 — 8절).

### 4.2 ICG가 보내는 명령 (발신 인터페이스)

| 명령/메시지 | 수신자 | 내용 |
|---|---|---|
| `INITIALIZE <yyyymmddThhmmss>` | `G.IC` | 타임스탬프 기반 파일명 시퀀스 초기화 — 가이드 파일명 `KMTNg?.<timestamp>.<seq>.fits`의 `<timestamp>` 부분이 여기서 온다 |
| `GO 1 ABC` | `G.IC` | 노출 시작. 인자 `1`=프레임 수, `ABC`=진행 보고(STATUS:)를 받을 노드 지정 — **회신 대상을 명령 인자로 위임**하는 패턴 (G.IC의 진행 보고가 ICG를 거치지 않고 ABC로 직행하는 이유) |
| `GUIDEEXP <초>` | `G.IC` | 노출시간 전파 |
| `STATUS 1` | `G.IC`, `K/M/T/N.IC` | IC 생존/식별 조회. 응답: `DONE: STATUS Inst=KMTNg +FIBERS +SYNCH Build=KG2016-06-02:1407` 형식(빌드 버전 포함) |
| `STATUS: SYNCHRONIZE IMGTYPE=... OBJNAME=... EXP=... OBSERVER=... PROJID=...` | `G.IC`, `K/M/T/N.IC` | 자기 설정 스냅샷 브로드캐스트 (5.1절) |
| `STATUS: AUXSTATUS <키=값 나열>` / `STATUS: TCSSTATUS <키=값 나열>` | `G.IC` | FITS 헤더용 망원경/부속장치 정보 중계 (5.4절) |
| `AUXSTATUS`, `TCSSTATUS` | `TC` | 위 중계의 원천 질의 |
| `TIME` | `XIS` | 허브의 시각 서비스 질의. 응답의 ISO 시각을 INITIALIZE 타임스탬프 등에 사용하는 것으로 보임 |

## 5. 트랜잭션 상세 (실측 로그 주해)

### 5.1 기동/점검 시퀀스 — 과학 IC까지 포함한 SYNCHRONIZE

로그에서 하루 수 회 관측되는 시퀀스(2024-01-03 CTIO 실측, 요약):

```
ICG>XIS TIME                       ← 허브 시각 질의
XIS>ICG DONE: TIME DATE=... TIMESYS=UTC
ICG>G.IC STATUS 1                  ← 5개 IC 전부에 생존/식별 조회
ICG>K.IC STATUS 1  (M/T/N 동일)
G.IC>ICG DONE: STATUS  Inst=KMTNg  +FIBERS +SYNCH Build=KG2016-06-02:1407
K.IC>ICG DONE: STATUS  Inst=KMTNk  DetectorID=K Driving=1 +FIBERS +SYNCH Build=KS2016-01-13:1370
  (M/T/N 동일 — Driving=0/1로 구동 여부 구분)
ICG>G.IC STATUS: SYNCHRONIZE   IMGTYPE=DARK OBJNAME=end EXP=30 OBSERVER=kwon_min_kyung PROJID=OBS
ICG>K.IC STATUS: SYNCHRONIZE   IMGTYPE=DARK OBJNAME=end EXP=30 ...  (M/T/N 동일)
```

**주목할 점**:
- ICG가 **가이드 CCD(G.IC)뿐 아니라 과학 IC 4개(K/M/T/N.IC)에도** `STATUS 1` 조회와 `STATUS: SYNCHRONIZE` 브로드캐스트를 보낸다. 즉 SYNCHRONIZE는 "통합제어자(ICS/ICG)가 자기 설정 스냅샷을 모든 IC에 알리는" 시스템 공용 관례이고, 과학/가이드 계통이 통신상 완전히 분리돼 있다는 서술([ics_legacy_report.md](ics_legacy_report.md) 4.4절)에 대한 **예외 지점**이 바로 이 동기화 채널이다.
- `STATUS` 응답에 각 IC의 **빌드 버전**(`Build=KS2016-01-13:1370` 등)이 실려온다 — ICG는 이 값들을 모아뒀다가 노출 시 헤더 정보에 붙인다(5.4절의 `KBUILD=...GBUILD=...ICSBUILD=...`).
- 위 실측 예의 설정값(`IMGTYPE=DARK OBJNAME=end EXP=30`)은 ICG가 마지막으로 갖고 있던 값이 그대로 브로드캐스트됨을 보여준다(관측 종료 시점의 dark 설정 잔재).

### 5.2 가이드 노출시간 설정 (GUIDEEXP)

```
abc>icg guideexp 10
ICG>ABC DONE: GUIDEEXP  GuideExp=10 seconds.     ← 즉시 접수 응답
ICG>G.IC GUIDEEXP 10                              ← G.IC에 전파
G.IC>ICG DONE: GUIDEEXP  GuideExp=10 seconds.    ← G.IC 접수 확인
```

ABC가 관측 세트 시작 시점에 설정하며(로그 샘플에서 151회 — GO 대비 1/340 빈도), 이후의 모든 `GO`가 이 노출시간을 쓴다.

### 5.3 가이드 노출 사이클 (GO) — 전체 시퀀스

2024-01-03 CTIO 실측 원문(주소/반복 생략, 시각은 UT):

```
00:21:43.675  abc>icg go                                   ← ABC의 트리거 (인자 없음, 소문자)
00:21:44.037  ICG>G.IC INITIALIZE 20240103T002144          ← 파일명 타임스탬프 초기화
00:21:44.041  ICG>ABC STATUS: GO   EXPSTATUS=INITIALIZING  ← ABC에 첫 진행 보고
00:21:44.042  ICG>TC AUXSTATUS                             ← 부속장치 상태 질의
00:21:44.042  TC>ICG DONE: AUXSTATUS AUXQDATE=... FILNUM=4 FILTER=B SHUTOP=OPENING SHUTTER=OPEN
              FAFOCUS=-1.350 ... ENS1=19.8 ... (필터/셔터/초점/환경 전체)
00:21:44.044  ICG>TC TCSSTATUS                             ← 망원경 좌표 질의
00:21:44.044  TC>ICG DONE: TCSSTATUS RA=03:48:57.56 DEC=-16:24:22.7 HA=-01:19:55 SECZ=1.08
              ALT=67.2 AZ=122.2 TELMOVE=Idle TCSLIMIT=No ... EXECODE=E
00:21:44.217  ICG>G.IC STATUS: AUXSTATUS  ENS7=0.0 ... FILTER=B ... AUXQDATE=...
              KBUILD=KS2016-01-13:1370 MBUILD=... TBUILD=... NBUILD=... GBUILD=KG2016-06-02:1407
              ICSBUILD=KX2016-03-23:1381 EXPSTATUS=INITIALIZING     ← AUX 정보+빌드버전 중계
00:21:44.246  ICG>G.IC STATUS: TCSSTATUS  DATE-OBS=2024-01-03T00:21:44 EXECODE=E ... RA=... 
              EXPSTATUS=INITIALIZING                                ← TCS 정보+DATE-OBS 중계
00:21:46.232  ICG>G.IC GO 1 ABC                            ← 노출 시작 (보고 대상=ABC 위임)
00:21:46.322  G.IC>ICG STATUS: GO  StartReadoutError=0     ← 시작 확인(ICG에)
00:21:46.412  G.IC>ABC STATUS: GO   EXPSTATUS=INTEGRATING  ← 이후 진행 보고는 ABC로 직행
00:21:56.311  G.IC>ABC STATUS: GO   EXPSTATUS=READOUT
   ...        G.IC>ABC STATUS: GO  Acquisition Complete  EXPSTATUS=WRITING
   ...        G.IC>G.CB TRANSFER DISK0 4 ABC               ← 디스크 전송도 보고 대상=ABC
   ...        G.CB>ABC DONE: Wrote LASTFILE=/mnt/ICSData/KMTNgs.20240103T002144.0001.fits RATE=...
              (ge/gn/gw 3개 파일 동일 — 가이드 CCD 4방위 각 1파일)
```

**구조적 특징**:
- ICG는 **점화만 하고 빠지는** 설계다: `GO 1 ABC`로 보고 대상을 ABC에 위임한 뒤, 노출 진행(INTEGRATING→READOUT→WRITING)과 파일 저장 보고는 전부 `G.IC`/`G.CB`→`ABC` 직행이다. ICG를 경유시키지 않아 자동 가이딩 루프의 지연을 줄이는 구조.
- **TCS/AUX 질의 시점이 ICS와 다르다**: ICS는 셔터 OPEN 시점에 질의하지만([ics_legacy_report.md](ics_legacy_report.md) 4.7절), ICG는 **GO 접수 직후·노출 시작 전**에 질의한다. 가이드 노출(수 초~10초)은 짧아서 노출 전 스냅샷으로 충분하다는 설계로 보인다.
- 파일명 규칙: `KMTNg{s,e,n,w}.<INITIALIZE 타임스탬프>.<시퀀스>.fits` — 과학 CCD의 날짜+일련번호 방식(`KMTNx.yyyymmdd.nnnnnn.fits`)과 달리 ISO 타임스탬프 기반이다.
- 사이클 주기: 실측 로그에서 `abc>icg go`는 약 1.5~2분 간격으로 반복된다(과학 노출과 독립 타이밍).

### 5.4 FITS 헤더용 정보 중계의 세부 특징

ICG가 TC 응답을 G.IC에 중계할 때 그대로 전달하지 않고 가공한다:
1. **키 순서가 역순으로 뒤집힌다** (TC 응답이 `AUXQDATE=... → ENS7=...` 순이면 중계는 `ENS7=... → AUXQDATE=...` 순) — 내부 파서가 키-값을 스택형으로 재조립함을 시사.
2. **빌드 버전 6종을 덧붙인다**: `KBUILD`/`MBUILD`/`TBUILD`/`NBUILD`/`GBUILD`/`ICSBUILD` — 5.1절의 `STATUS 1` 조회로 수집해둔 값. FITS 헤더에 소프트웨어 버전 이력을 남기기 위한 것으로 보인다. (`ICSBUILD=KX2016-03-23:1381`이라는 키 이름은 ICG 자신의 빌드를 "ICS" 계열 이름으로 기록함을 시사 — ICG가 ICS와 같은 코드베이스(KX 빌드)의 다른 인스턴스일 가능성, 8절 참고.)
3. **`DATE-OBS`를 추가한다**: TCSSTATUS 중계에는 원본에 없는 `DATE-OBS=<현재 ISO 시각>`이 붙는다 — 가이드 FITS의 관측시각 헤더 필드용.
4. 끝에 `EXPSTATUS=<현재 상태>`를 붙여 "이 스냅샷이 노출의 어느 단계에서 찍힌 것인지"를 표시한다.

### 5.5 하위 계층: G.IC ↔ G.CB (디스크 쓰기)

신규 `icg`가 함께 흡수할 계층이므로 별도로 정리한다. `G.CB`는 **포트 10601**(IC 계열 6600과 다름)에서 동작하며, 노출 데이터를 실제 디스크에 쓰는 역할이다.

**런타임 사이클** (실측, 2024-01-04 CTIO):
```
G.IC>G.CB  TRANSFER DISK1 4 ABC          ← 디스크 지정 + 파일 4개 + 보고 대상 위임
G.CB>ABC   DONE: Wrote LASTFILE=/mnt/ICSData/KMTNgs.20240103T002517.0001.fits RATE=673953 KB/sec
G.CB>ABC   DONE: Wrote ... KMTNge... / KMTNgn... / KMTNgw...   (4방위 각 1파일)
G.CB>G.IC  DONE DISK1 4                  ← 상위(G.IC)에는 완료 요약만
G.CB>G.IC  REQ SWAP                      ← 디스크 교대 요청
G.IC>G.CB  ACK SWAP                      ← 승인 → 다음 노출은 DISK0 사용
```

- **`TRANSFER <디스크> <개수> <보고대상>`** — 두 번째 인자가 **가이드는 `4`**(CCD 4개분 파일), 과학은 `1`(CCD 1개분). 세 번째 인자로 보고 대상을 위임하는 것은 §5.3의 `GO 1 ABC`와 동일한 패턴이다.
- **`REQ SWAP`/`ACK SWAP` 핸드셰이크**가 `DISK0`↔`DISK1` 이중 버퍼 교대의 실제 메커니즘이다(CTIO 로그 기준 G.CB에서 25,506회 관측). 이 이중화는 1998년 SCSI 시대의 성능 최적화에서 유래한다([ics_legacy_report.md](ics_legacy_report.md) 1.4절).
- 초기화 시퀀스(과학 CB 실측이지만 구조는 동일): `REQ INITDISK` → `INIT DISK 128 400128` → `FOUND DISK1.BUS1.<날짜>.`/`FOUND ALL` → `USE DISK0 <물리디스크>` → `USING DISK0` → `ACK DISK` → `REQ MOUNT` → `FOUND MOUNT UNIX:\CB\/mnt/ICSData` → `FOUND MOUNT ALL`. 물리 디스크를 논리 슬롯(DISK0/1)에 바인딩하는 구조.
- 과학 계통은 디스크가 **3개**(`DISK0`/`DISK1`/`DISK2`) 관측되는 반면 가이드는 2개다.

## 6. 에러/경고 패턴 (실측)

| 메시지 | 의미/맥락 |
|---|---|
| `G.IC>ICG ERROR: GO  Wrong CBB program running. Expected GUIDE, found SCIENCE` | **가이드/과학 컨트롤러 펌웨어가 구분됨**을 보여주는 에러 — G.IC 쪽 CBB(컨트롤러 보드)에 과학용 프로그램이 로드된 채 가이드 GO가 들어온 경우. 하드웨어 셋업 오류 감지 사례 (6회 관측) |
| `XIS>ICG ERROR: No Route to Destination Host G.IC - host is unknown/unlisted` (K.IC 동일) | 대상 IC가 XIS에 미등록(다운/재시작 중) 상태일 때 허브가 돌려주는 라우팅 에러 — [ics_legacy_report.md](ics_legacy_report.md) 1.2절의 "노드 등록" 개념의 실패 사례 |
| `G.IC>ABC ERROR: GO  DMA WAIT TIMEOUT. EXPOSURES ABORTED. EXPSTATUS=ERROR` | 가이드 CCD의 DMA(광케이블) 응답 타임아웃 — ICG가 아니라 ABC에 직접 보고됨(보고 위임 구조 때문). 로그에서 반복적으로 관측되는 흔한 장애 ([ics_legacy_report.md](ics_legacy_report.md) 5절) |
| `G.IC>ICG STATUS: GO  StartReadoutError=0` | 에러가 아니라 정상 시작 확인(에러 카운트 0). GO마다 두 번 연속 출력되는 특이 패턴(`GO`가 중복 표기된 `STATUS: GO GO StartReadoutError=0` 포함) |

## 7. ICS와의 비교 — 신규 `ics`/`icg` 분리 설계의 근거

두 계통은 "같은 역할의 쌍둥이"처럼 보이지만, 실제로는 아래처럼 여러 축에서 다르다. 신규 시스템에서 `ics`와 `icg`를 **별도 프로그램으로 분리**하는 결정은 이 차이들에 의해 뒷받침된다.

### 7.1 구조·규모 차이

| 항목 | ICS 계통 (과학) | ICG 계통 (가이드) |
|---|---|---|
| **통합 대상 노드 수** | **9개** — `ICS` + `K/M/T/N.IC`(4) + `K/M/T/N.CB`(4) | **3개** — `ICG` + `G.IC` + `G.CB` |
| 물리 CCD | 4개 (각각 별도 IC 노드) | 4개 (**전부 `G.IC` 1노드가 통합 제어**) |
| CCD당 리드아웃 채널 | 8 | 2 |
| CB(디스크) 계층 | CCD당 1개씩 4노드 병렬 | 1노드가 4CCD분 전부 처리 |
| `TRANSFER` 인자 | `TRANSFER DISK<n> **1** ICS` (CCD 1개분) | `TRANSFER DISK<n> **4** ABC` (4CCD 한 번에) |
| 디스크 슬롯 | `DISK0`/`DISK1`/`DISK2` (3개 관측) | `DISK0`/`DISK1` (2개) |
| 노드 간 동기화 부담 | **높음** — 4개 IC의 노출을 동시 트리거하고 4개 CB의 완료를 각각 수집 | **낮음** — 단일 IC/CB라 동기화 불필요 |

### 7.2 제어 흐름·인터페이스 차이

| 항목 | ICS (과학) | ICG (가이드) |
|---|---|---|
| 부리는 주체 | `OBS` (사람/스크립트 → OBSAgent) | **`ABC`** (자동 가이딩 루프) |
| 수신 명령 세트 | OBJECT/DARK/BIAS/FLAT/EXP/PROJID/OBSERVER/GO 등 다수 | **`GO`/`GUIDEEXP` 단 2개** (로그 관측 기준) |
| GO 인자 | `GO <n>` | `GO`(수신) → `GO 1 ABC`(G.IC로 발행, **보고 대상 위임**) |
| 진행 보고 경로 | IC → `ICS` → `OBS` (상위 경유) | IC/CB → **`ABC` 직행** (ICG 우회) |
| TCS/AUX 질의 시점 | **셔터 OPEN 시** | **GO 직후·노출 시작 전** |
| 노출 주기 | 수 분 (과학 노출) | 1.5~2분, 노출 자체는 ~10초 |
| 파일명 | `KMTNx.yyyymmdd.nnnnnn.fits` (날짜+일련번호) | `KMTNg{s,e,n,w}.<ISO타임스탬프>.<seq>.fits` |
| 접속 방식 | 시리얼(`/dev/ttyS0`) 경유 사례 다수 | UDP 6600 (일반 IC와 동일) |
| 실행 호스트 | Science server 계열 | **Guide server** (`TC`·`ABC`와 동거) |
| 상태머신 소비자 | **OBSAgent가 원시 메시지를 파싱해 `CamStatus` 유지** → 메시지 하위호환 의무 있음 | **없음** — OBSAgent가 `ICG`/`G.IC`/`G.CB` 발신 메시지를 명시적으로 무시(v0.3.2~). ABC가 자체 소비 |
| SYNCHRONIZE | 과학 IC에 전파 | **5개 IC 전부에 전파** — 두 계통이 만나는 유일한 지점 |

### 7.3 신규 설계에서의 함의

- **통합 난이도가 비대칭적이다.** 신규 `ics`는 9개 노드의 기능을, 신규 `icg`는 3개 노드의 기능을 흡수한다. 특히 `ics`는 "4개 IC를 동기 트리거하고 4개 CB의 완료를 각각 기다리는" 다중 병렬 제어가 프로그램 내부 문제로 바뀌는 반면, `icg`는 단일 IC/CB라 이 복잡성이 애초에 없다. **`icg`를 먼저 구현해 공통 골격(IMPv2 노드, TC 질의·헤더 중계, 노출 상태머신, 디스크 쓰기)을 검증한 뒤 `ics`로 확장**하는 순서가 위험이 적다.
- **하위호환 부담도 비대칭이다 (중요).** 신규 `ics`는 OBSAgent를 개정하지 않기로 확정됐으므로 "Acquisition Complete." 4회 등 **레거시 메시지 규약을 그대로 지켜야** 한다([ics_legacy_report.md](ics_legacy_report.md) 8.0.1절). 반면 OBSAgent는 v0.3.2부터 `ICG`/`G.IC`/`G.CB` 발신 메시지를 **명시적으로 무시**하므로(가이드 문자열이 과학 상태머신을 오염시키지 않도록 도입된 필터), **신규 `icg`는 메시지 형식을 자유롭게 현대화해도 된다.** 가이드 쪽 소비자는 `ABC` 하나뿐이다.
- **두 프로그램을 분리하는 것이 옳은 이유**: 명령 세트·제어 주체(OBS vs ABC)·타이밍(수 분 vs 초 단위 루프)·보고 경로가 전부 다르다. 특히 가이드는 지연에 민감한 자동 루프의 부품이라 과학 노출의 무거운 파이프라인과 한 프로세스에 묶으면 서로 방해할 수 있다.
- **그럼에도 공유해야 할 것**: IMPv2 파서·XIS 등록·`TC` 질의와 FITS 헤더 중계·`SYNCHRONIZE`·디스크 이중버퍼 로직은 양쪽이 사실상 동일하다(레거시도 같은 `KX` 코드베이스로 추정, §8). **공유 라이브러리로 분리**하고 두 프로그램이 이를 import하는 구조를 권장한다 — "프로그램 분리"와 "코드 공유"는 양립한다.
- **계통 간 결합 지점은 `SYNCHRONIZE` 하나뿐**이다(§5.1). 신규 설계에서 이 채널을 유지할지(두 프로그램 간 설정 동기화) 폐지할지 명시적으로 결정해야 한다 — 레거시에서는 ICG가 과학 IC에까지 자기 설정을 뿌리는 다소 의외의 동작이었다.

## 8. 한계와 미확인 사항

- **소스코드·문서 부재**: ICG의 실행파일 위치, 설정 파일, 명령어 전체 목록은 미확인이다. `ICSBUILD=KX2016-03-23:1381`이라는 빌드 표기(ICS와 같은 `KX` 계열)로 보아 **ICS와 동일 코드베이스를 가이드용 설정으로 실행한 인스턴스**일 가능성이 높지만, 소스 없이는 확정할 수 없다.
- **설정 변경 명령 미관측**: IMGTYPE/OBJNAME 등을 바꾸는 명령이 ICG에 들어오는 장면이 로그 샘플에 없다(SYNCHRONIZE 브로드캐스트로 값의 존재만 확인). ICS와 동일 코드베이스라면 같은 설정 명령(OBJECT/DARK/EXP...)을 받을 것으로 추정된다.
- **ABC의 정체**: ABC는 소문자 명령·임시 포트 사용(OBSAgent와 같은 클라이언트형 패턴)으로 보아 별도의 자동 가이딩 프로그램인데, 이 저장소에는 ABC 자료도 없다. ABC가 `TC`에 보내는 `fttgoto` 반복(오토가이딩 초점/tip-tilt 피드백)은 [ics_legacy_report.md](ics_legacy_report.md) 4.3절 참고.
- 로그 샘플은 2024~2025년 일부 기간이므로, 저빈도 명령(연 1회 수준의 유지보수 명령 등)은 잡히지 않았을 수 있다.

## 9. 신규 Python `icg` 구현 명세 (확정 설계 기준)

신규 `icg` = 레거시 **`ICG` + `G.IC` + `G.CB`** 3개 노드의 통합. 이 절은 그 관점에서 무엇을 내부로 흡수하고 무엇을 외부에 남길지 정리한다.

### 9.1 흡수하는 3개 층의 책임

| 레거시 노드 | 신규 `icg`가 맡을 책임 | 근거 절 |
|---|---|---|
| `ICG` | 노출 사이클 오케스트레이션, `TC` 질의(AUXSTATUS/TCSSTATUS), FITS 헤더 정보 가공·주입, 빌드버전 수집, `SYNCHRONIZE` 브로드캐스트 | §5.1, §5.3, §5.4 |
| `G.IC` | 가이드 CCD 4개 노출 제어·리드아웃, 노출 상태 전이(INTEGRATING→READOUT→WRITING), `INITIALIZE` 파일명 시퀀스 관리 | §5.3 |
| `G.CB` | 디스크 쓰기(4파일/사이클), `DISK0`/`DISK1` 이중버퍼 교대, 마운트/초기화, 쓰기 완료·전송률 보고 | §5.5 |

### 9.2 내부화되어 사라지는 통신 경계

아래는 지금 UDP 메시지로 오가지만 신규 구현에서는 **함수 호출·내부 이벤트로 대체**된다. 즉 이 부분의 프로토콜 호환성은 신경 쓸 필요가 없다:

- `ICG → G.IC`: `INITIALIZE <ts>`, `GO 1 ABC`, `GUIDEEXP <n>`, `STATUS 1`, `STATUS: AUXSTATUS/TCSSTATUS` 중계 → **헤더 정보를 메시지로 말아 보낼 필요 없이 노출 객체에 직접 주입**
- `G.IC → G.CB`: `TRANSFER DISK<n> 4 ABC`, `ACK SWAP` / `G.CB → G.IC`: `DONE DISK<n> 4`, `REQ SWAP`, 초기화 핸드셰이크 전체 → **내부 큐/상태 전이**
- 사이클당 UDP 왕복이 최소 10여 회 줄어든다. 특히 §5.4의 "키를 역순으로 재조립해 중계"하는 기묘한 가공이 통째로 불필요해진다.

### 9.3 반드시 유지해야 할 외부 인터페이스

| 상대 | 인터페이스 | 비고 |
|---|---|---|
| `ABC`(또는 후속 가이딩 제어기) | `go`, `guideexp <초>` 수신 / 노출 진행·파일 저장 보고 발신 | **가이드 계통의 유일한 메시지 소비자.** ABC를 존치한다면 이 규약만 맞추면 되고, ABC도 재작성한다면 형식을 자유롭게 재설계 가능(OBSAgent는 가이드 메시지를 무시하므로 제약 없음, §7.3) |
| `TC` (TCS Agent) | `AUXSTATUS`/`TCSSTATUS` 질의 | [tcsagent_report.md](../TCSAgent/tcsagent_report.md) 참고. newTCS 전환 시 이 경로가 Redis로 바뀔 수 있음 |
| `XIS` (허브) | 노드 등록(PING), `TIME` 질의, PONG 응답 | 레거시 노드와 공존하려면 필수 |
| 신규 `ics` | `SYNCHRONIZE` 설정 동기화 | **유지/폐지 결정 필요** — 레거시에서 ICG가 과학 IC에까지 뿌리던 채널(§5.1) |
| 파일시스템 | `/mnt/ICSData`에 `KMTNg{s,e,n,w}.<ts>.<seq>.fits` | 파일명 규칙 유지 여부 결정 필요(과학 쪽과 형식이 다름) |

### 9.4 설계 권고

- **`ics`와 공유 라이브러리를 둘 것.** IMPv2 노드(UDP 소켓·파서·등록), `TC` 질의와 FITS 헤더 중계, `SYNCHRONIZE`, 디스크 이중버퍼, 파일명 fail-safe 관례는 두 프로그램이 사실상 동일하다. 레거시도 같은 코드베이스(`ICSBUILD=KX...`, §8)로 추정되므로 이 공유는 원래 구조에도 부합한다. **프로그램 분리와 코드 공유는 양립한다.**
- **`icg`를 먼저 만들 것.** 단일 IC/단일 CB라 다중 노드 동기화 문제가 없어 골격 검증에 적합하다(§7.3).
- **보고 위임(`GO 1 ABC`) 패턴은 pub/sub으로 일반화.** 진행 보고 수신자를 명령 인자로 지정해 중간자를 우회시킨 설계는 지연에 민감한 가이딩 루프에 유효했다. Redis pub/sub이나 asyncio 브로드캐스트의 "토픽 구독"이 자연스러운 현대적 대응물이다.
- **헤더 스냅샷 시점을 스펙으로 명시.** 레거시는 `ICS`가 셔터 OPEN 시, `ICG`가 노출 시작 전에 TCS 상태를 찍는데 그 규칙이 코드에만 존재한다. 신규는 노출 유형별로 "언제 찍는가"를 문서화된 규칙으로 정의할 것.
- **빌드 버전 헤더 기록은 유지.** 노출마다 관련 소프트웨어 버전 전체를 FITS에 남기는 관례(`KBUILD`~`ICSBUILD`)는 재처리 시 추적성에 유용하다. 신규에서는 "통합된 `ics`/`icg` 각각의 버전 + 공유 라이브러리 버전"으로 항목이 단순해진다.
- **`Wrong CBB program running` 류의 하드웨어 모드 검증은 계속 필요**(§6) — 가이드/과학 컨트롤러 펌웨어 구분은 물리적 제약이라 소프트웨어 통합과 무관하게 남는다.
- **디스크 이중화(`DISK0`/`DISK1`)의 존치 여부 재검토.** 1998년 SCSI 제약에서 유래한 최적화이며, 지금은 `/mnt/ICSData` 네트워크 스토리지를 쓴다. 쓰기 중 접근 충돌 방지 같은 다른 이유로 여전히 유효한지 확인 후 결정할 것.

## 10. 관련 문서

- [ics_legacy_report.md](ics_legacy_report.md) — 시스템 전체(ICS·IMPv2.5·XIS 허브·노드 디렉토리). 특히 4.4절(가이드 트랜잭션 개요)·4.3절(BLG 노출 중 가이딩)·5절(에러 패턴)이 이 문서와 상보적
- [../TCSAgent/tcsagent_report.md](../TCSAgent/tcsagent_report.md) — ICG가 질의하는 `TC` 노드(AUXSTATUS/TCSSTATUS의 생산자)
- [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md) — 과학 계통의 관측 콘솔(가이드 계통의 ABC에 대응하는 위치)

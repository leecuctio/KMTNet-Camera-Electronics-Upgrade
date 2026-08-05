# ics_sim — KMTNet ICS 시뮬레이터

레거시 ICS(ICIMACS / IMPv2.5)와 호환되는 메시지를 내는 카메라 통합제어 프로그램. 카메라 하드웨어 없이 실제 **OBSAgent·GMON 을 물려서** 관측 시퀀스를 돌려볼 수 있다.

바깥으로는 레거시와 같은 규약을, 안으로는 신규 통합 구조(`ICS` + `K/M/T/N.IC` + `K/M/T/N.CB` = 9노드)를 따른다. 다음 단계에서 하드웨어 계층만 갈아끼우면 실제 CCD 를 구동하는 `ics` 가 된다.

> **설계 근거·조사 이력·개발 지침은 [DevNote.md](DevNote.md) 에 있다.** 이 README 는 실행 방법만 다룬다.

---

## 필요 환경

- Python 3.10+
- 필수 의존성 **없음** (표준 라이브러리만)
- 선택: `numpy`, `astropy` — `--fits` 로 더미 FITS 를 만들 때만
- 테스트: `pytest`

---

## 빠르게 돌려보기

```bash
cd ics_sim
python -m ics_sim --time-scale 0.1
```

콘솔이 뜨면 레거시 ICS 와 똑같이 타이핑한다:

```
projid obs
dark begin
exp 30
go
```

송수신 메시지가 그대로 출력된다:

```
>>> ICS>OBS STATUS: EXPSTATUS=INITIALIZING
>>> ICS>K.IC INITIALIZE 20260803.000001
>>> K.IC>ICS DONE: INITIALIZE Initialization Complete.
>>> ICS>OBS STATUS: EXPSTATUS=ERASE
...
>>> K.IC>OBS STATUS: GO PCTREAD=6
>>> K.IC>OBS STATUS: GO PCTREAD=100 Acquisition Complete. Disk Transfer Starting.
>>> ICS>OBS DONE: EXPSTATUS=IDLE
>>> ICS>OBS STATUS: Wrote LASTFILE=./icsdata/KMTNk.20260803.000001.fits RATE=1064218 KB/sec
```

`go 5` 로 다중 노출, `>K.IC status` 로 특정 노드에 직접 명령, `help` 로 도움말, `quit` 로 종료.

---

## 실행 모드

### 혼자 돌리기 (direct-reply)

`[transport] xis_host` 가 비어 있으면 받은 주소로 그대로 되돌려 보낸다. XIS 허브 없이 UDP 로 명령을 직접 쏘아 전체 사이클을 확인할 수 있다. **기본 모드.**

### XIS 허브에 붙이기

```bash
python -m ics_sim --xis-host 192.168.14.101 --xis-port 6660
```

모든 발신이 허브를 거친다. 실제 배치 형태이고, 이 상태로 OBSAgent 를 물리면 규약 검증이 실물로 된다.

기동하면 **9개 노드 ID 전부로 PING** 을 보내 XIS 에 등록한다:

```
ICS>AL PING    K.IC>AL PING   M.IC>AL PING   T.IC>AL PING   N.IC>AL PING
               K.CB>AL PING   M.CB>AL PING   T.CB>AL PING   N.CB>AL PING
```

`ICS` 하나만 등록하면 OBSAgent 의 `kstatus`/`dmawait`/`datasource` 가 도달하지 않는다 — 그 명령들은 개별 IC 주소로 오기 때문이다.

> **9개 ID 가 같은 (IP,port) 를 써도 된다** — XIS 서버 소스로 확인했다(2026-08-04). 클라이언트 테이블은 **노드 ID 만으로 키잉**되고 주소 충돌 검사가 없으며, `messages.c` 는 여러 클라이언트가 한 포트를 공유하는 경우를 명시적으로 다룬다. 소켓 하나로 9개 ID 를 등록하는 현재 방식이 안전하다. 근거와 논의 전 과정은 [DevNote 3.1.1](DevNote.md).
>
> XIS 를 재시작하면 `XIS>AL PING` 이 오고, 시뮬은 여기에 **9개 ID 전부로 PONG** 을 돌려 자동 재등록된다. 다만 그 PING 을 받으려면 시뮬 주소가 XIS `isis.ini` 의 `UDPPort` 목록에 있어야 한다(운영 측 작업, 한 줄).
>
> `[transport] register_all_nodes = false` 로 끌 수는 있으나 그러면 개별 IC 명령을 받지 못한다.
>
> ⚠️ `bind_host` 기본값이 `127.0.0.1` 이라 **로컬에서만 받는다.** 외부 장비와 붙이려면 `ics_sim.ini` 에서 `0.0.0.0` 으로 바꿀 것 (CLI 인자는 없다).

> 실제 배치에서 ICS↔XIS 링크만 시리얼(`/dev/ttyS0`)이지만, 시뮬은 UDP 만 쓴다. 이유는 [DevNote 15장](DevNote.md#15-범위-밖과-그-이유).

### FITS 실제 생성

```bash
python -m ics_sim --fits --data-dir ./icsdata
```

`numpy`/`astropy` 가 있으면 AUX/TCS 텔레메트리를 헤더에 넣은 더미 FITS 4개를 노출마다 저장한다.

### 레거시 오염 재현

```bash
python -m ics_sim --bug-compat
```

레거시의 커맨드워드 오염을 의도적으로 재현한다. 골든 대조용이며 **기본은 꺼짐**. 자세한 내용은 [DevNote 5장](DevNote.md#5-메시지-오염-버그--원인-분석과-신규-설계-대응).

원인 코드까지 확정돼 있다 — 레거시 ICS 의 `SUB Prt` 가 첫 낱말이 콜론으로 끝나기만 하면 포트별 `CommandEcho` 를 무조건 끼워 넣고, 그 슬롯은 정상 운용 중 비워지지 않는다. 같은 함수가 노출 중 모든 콜론 메시지에 ` EXPSTATUS=` 접미사도 붙인다. `ics_sim` 은 커맨드워드를 매 메시지 인자로 받고 `emitter.validate()` 로 적층·재등장을 잡아 이 경로를 구조적으로 갖지 않는다.

### AUX control 서버 연동

셔터 개폐 때 KMTNet AUX control software 에 TCP 로 커맨드를 보낸다. `ics_sim.ini` 에서 켠다:

```ini
[auxcontrol]
enabled     = true
AUX_Host    = 127.0.0.1 (Local)     # 괄호 설명은 무시된다
AUX_Port    = 5752
AUX_TelID   = KMTNET
AUX_SysID   = AUX
shopen_cmd  = FILTERS SET_SH OPEN
shclose_cmd = FILTERS SET_SH CLOSE
```

키 이름과 형식은 TCSAgent 의 `pctcs.kmtn*.ini` 와 같다 — **같은 AUX 서버를 가리키므로** 그쪽 설정을 그대로 복사해 넣을 수 있다. 오가는 전문은 이렇다:

```
셔터 열림  →  KMTNET AUX ICS1 FILTERS SET_SH OPEN
              KMTNET AUX ICS1 OK
셔터 닫힘  →  KMTNET AUX ICS2 FILTERS SET_SH CLOSE
              KMTNET AUX ICS2 OK
```

`OK` 는 통과, `BAD` 는 빨강 경고, `WAIT` 는 청록 경고, **무응답도 빨강 경고**다. 규격상 `AUX_TelID`/`AUX_SysID` 가 틀리면 서버가 **응답 자체를 하지 않으므로**, 조용한 실패를 눈에 띄게 만들었다. 어느 경우든 **노출은 끝까지 진행한다.**

DARK/BIAS 는 셔터를 열지 않으므로 아무것도 보내지 않는다.

> ⚠️ **이 경로는 하드웨어 트리거의 시뮬레이션용 대체물이다.** 실제 시스템에는 셔터를 여닫는 SW 명령이 없고 HE 박스의 TTL 신호가 그 역할을 한다. `--backend archon` 으로 실기를 돌릴 때는 `enabled = false` 로 꺼야 구동원이 겹치지 않는다(설정 검증이 경고한다). 자세한 내용은 [DevNote 9.2.2](DevNote.md).

### 결함 주입

```bash
python -m ics_sim --inject acq_short,wrote_drop
```

| 값 | 재현하는 상황 |
|---|---|
| `init_fail` | `ERROR: Failed to initialize one or more ICs` |
| `acq_short` | `Acquisition Complete.` 를 3회만 → OBSAgent 의 `opause` 경로 |
| `wrote_drop` | `Wrote` 하나 누락 → `FitsSaved` 가 서지 않음 |
| `dma_timeout` | `DMA WAIT TIMEOUT. EXPOSURES ABORTED.` |
| `shopen_corrupt` | 전송 손상으로 셔터가 열리지 않는 노출 |
| `tc_timeout` | TC 무응답 → 빈 텔레메트리로 진행 |

---

## 설정

모든 동작 파라미터는 [`ics_sim.ini`](ics_sim.ini) 에서 편집한다. 주석은 `#` 하나이고 **줄 어디에나** 올 수 있으며 `#` 앞의 내용은 유효하다.

```ini
[timing]
erase_sec = 7.24        # ERASE -> Erase Cycle Complete.  (XIS 로그 실측)
```

CLI 인자가 같은 키를 덮어쓴다. 전 항목 설명은 [DevNote 7장](DevNote.md#7-설정파일-레퍼런스-ics_simini).

주요 스위치:

| 인자 | 설명 |
|---|---|
| `-c` / `--config <파일>` | 설정파일 경로 (기본 `ics_sim.ini`) |
| `--time-scale 0.1` | 10배 빠르게 (테스트용) |
| `--node-mode merged` | 발신 이름을 전부 `ICS` 로 (통합 노드 형태) |
| `--backend archon` | 실기 백엔드 (현재 스텁) |
| `--no-console` | 키보드 인터페이스 없이 |
| `--quiet-wire` | 메시지 출력 끄기 |
| `--log-level debug` | 로그 상세도 |

`--bind-port`·`--xis-host`·`--xis-port`·`--data-dir`·`--fits`/`--no-fits`·`--bug-compat`·`--inject` 도 같은 방식으로 ini 값을 덮어쓴다. 전체 목록은 `python -m ics_sim --help`.

---

## 테스트

```bash
python -m pytest tests -q
```

| 파일 | 지키는 것 |
|---|---|
| `test_obsagent_contract.py` | OBSAgent 호환 규약 전체 — 상태 전이, 개수 규약, 타임아웃 창, `ExpNum` 왕복, `GO n` |
| `test_emitter_hygiene.py` | 메시지 오염 방지 (정방향 + 레거시 샘플 역방향 검증) |
| `test_sequence_golden.py` | 레거시 실측 시퀀스와 대조 |
| `test_stop_abort.py` | STOP/ABORT — 레거시 분기·거부 문자열, 중지 후 IDLE 복귀 |
| `test_auxcontrol.py` | AUX 연동 — 가짜 AUX 서버로 실제 TCP 왕복, 어떤 응답에도 노출 완주 |
| `test_impv2.py` | 프로토콜 파싱 |

---

## 조사 도구

레거시 로그가 있는 컴퓨터에서 실행한다. 로그 자체는 저장소에 없다(`*.log` / `__localonly_*` 비커밋).

```bash
# 커맨드워드 슬롯 분류 -- 메시지 오염의 직접 증거
python tools/scan_legacy_logs.py slots <logdir> -o slots.txt

# 메시지 형태 목록 -- 두 스캔을 diff 하면 새 시퀀스가 드러난다
python tools/scan_legacy_logs.py shapes <logdir> -o shapes.txt

# OBSAgent CamStatus 재생 -- 상태 전이 실측
python tools/scan_legacy_logs.py camstatus <logdir>

# 오염 패턴만 추려 테스트 픽스처로
python tools/scan_legacy_logs.py patterns <logdir> -o tests/fixtures/bug_patterns.txt

# 골든 픽스처 생성
python tools/extract_golden.py <logfile> --around 'Image 1 of 5 complete' -o out.txt
```

### 레거시 ICS 소스 꺼내 보기

레거시의 실제 동작을 확인해야 할 때는 VDOS 디스크 이미지를 열면 된다. **IC/ICS 는 FreeBASIC 으로 작성돼 있고 소스가 실행파일과 함께 들어 있다.** raw MBR + FAT32 라 마운트도 관리자 권한도 필요 없다:

```bash
7z x "<이미지>/IC2.img" -o<대상> -y -r 'FREEBASI\KMTX\*' 'FREEBASI\SHARE\*'
```

읽을 것은 `KMTX\PAP7KX.{BAS,CMD,CCD}`(ICS 본체)와 `SHARE\PAP7{.INC,COM.INC,.CMD}`(공용·통신). 이미지는 `__localonly_*` 라 비커밋이며, 절차와 근거는 [DevNote 2.2](DevNote.md).

---

## 구조

```
ics_sim/
├── __main__.py     CLI 진입점
├── app.py          기동·종료·노드 등록
├── config.py       설정 로드 + 자가검증
├── impv2.py        IMPv2.5 파싱/조립
├── transport.py    UDP (XIS 경유 / direct-reply)
├── nodes.py        9개 노드 수신 라우팅
├── state.py        노출 설정 + CCD별 상태
├── telemetry.py    TC 질의 · 역순 중계
├── emitter.py      메시지 방출 + 오염 검증   ← 모든 발신 문자열이 여기 한 곳에
├── sequencer.py    노출 상태머신
├── commands.py     명령 디스패치
├── fitsout.py      FITS 생성 (헤더는 실기와 같은 경로)
├── auxcontrol.py   AUX control 서버 TCP 연동 (셔터 개폐 통보)
├── console.py      로컬 키보드 인터페이스
├── obsagent_model.py   OBSAgent CamStatus 모델 (테스트용 재구현)
└── hardware/       base.py 계약 · sim.py (현재) / archon.py (다음 단계)
```

**레거시와의 차이** — `ROI`/`DISPL`/`MOVIE` 는 레거시 ICS 명령 테이블에 **아예 없어서** 핸들러를 두지 않았다. 레거시와 똑같이 `ERROR: … Didn't understand … ?` 로 거부된다. `BIN` 만 아직 스텁이다(`strict_legacy` 면 무응답). 근거는 [DevNote 6.8](DevNote.md).

`STOP`/`ABORT` 는 레거시 분기를 그대로 옮겨 **구현되어 있다**:

```
OBS>ICS stop     적분만 끊고 readout·저장은 정상 진행
OBS>ICS abort    전부 중지 (readout·저장 안 함), EXPSTATUS=IDLE 통보
```

노출 중이 아니면 레거시와 같은 문구로 거부한다 — `No integration in progress. Nothing to stop.` / `No acquisition in progress. Nothing to abort.` 단 **수락 시의 `DONE:` 본문은 실측 근거가 없어 우리가 정한 것**이다([DevNote 9.2.1](DevNote.md)).

---

## 관련 문서

- [DevNote.md](DevNote.md) — 설계 근거 · 조사 이력 · 개발 지침
- [../ics_legacy/ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) — 레거시 ICS/XIS 전체 분석
- [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md) — OBSAgent 분석
- [SMC_CLAUDE.md](SMC_CLAUDE.md) — 작업 이어갈 때의 컨텍스트

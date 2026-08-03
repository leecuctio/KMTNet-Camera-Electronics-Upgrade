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

> ⚠️ **미해결 항목**: 이러면 9개 ID 가 전부 같은 (IP,port) 를 가리키게 되는데, **레거시 배치에는 그런 사례가 없어 XIS 가 이를 받아주는지 확인되지 않았다.** 실물 XIS 에 붙였을 때 `kstatus` 가 도달하지 않으면 노드별 소켓 방식으로 바꿔야 한다. 배경·근거·전환 조건은 [DevNote 3.1.1](DevNote.md). `[transport] register_all_nodes = false` 로 끌 수는 있으나 그러면 개별 IC 명령을 받지 못한다.
>
> `bind_host` 기본값이 `127.0.0.1` 이라 **로컬에서만 받는다.** 외부 장비와 붙이려면 `0.0.0.0` 으로 바꿀 것.

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
| `--time-scale 0.1` | 10배 빠르게 (테스트용) |
| `--node-mode merged` | 발신 이름을 전부 `ICS` 로 (통합 노드 형태) |
| `--backend archon` | 실기 백엔드 (현재 스텁) |
| `--no-console` | 키보드 인터페이스 없이 |
| `--quiet-wire` | 메시지 출력 끄기 |

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

# 골든 픽스처 생성
python tools/extract_golden.py <logfile> --around 'Image 1 of 5 complete' -o out.txt
```

---

## 구조

```
ics_sim/
├── config.py       설정 로드 + 자가검증
├── impv2.py        IMPv2.5 파싱/조립
├── transport.py    UDP (XIS 경유 / direct-reply)
├── nodes.py        9개 노드 수신 라우팅
├── state.py        노출 설정 + CCD별 상태
├── telemetry.py    TC 질의 · 역순 중계
├── emitter.py      메시지 방출 + 오염 검증
├── sequencer.py    노출 상태머신
├── commands.py     명령 디스패치
├── obsagent_model.py   OBSAgent CamStatus 모델
└── hardware/       sim.py (현재) / archon.py (다음 단계)
```

---

## 관련 문서

- [DevNote.md](DevNote.md) — 설계 근거 · 조사 이력 · 개발 지침
- [../ics_legacy/ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) — 레거시 ICS/XIS 전체 분석
- [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md) — OBSAgent 분석
- [SMC_CLAUDE.md](SMC_CLAUDE.md) — 작업 이어갈 때의 컨텍스트

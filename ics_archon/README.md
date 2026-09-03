# ics_archon — 실기 ICS (STA Archon 제어)

`ics_sim/`(시퀀서·명령 처리부·메시지 규약·헤더 층)과 이 폴더의 Archon 제어
코드를 합친 **실기 취득 프로그램**이다.  최종적으로 `ics` 로 개명해 운영
배포한다.

```bash
cd ics_archon
python -m ics_archon                 # ics_archon.ini 를 읽는다
python -m ics_archon --backend sim   # 컨트롤러를 만지지 않고 메시지 층만
```

> **현재 판 `v0.0.0` — 실기 왕복은 한 번도 돌리지 않았다.**  가짜 컨트롤러
> (`tests/fake_archon.py`)로 전 경로가 돌고 견본 헤더와 바이트 단위로 일치하지만,
> 실물 Archon 과의 왕복·독출 시간·픽셀 배치는 미검증이다.  잠정인 자리는
> 코드에 `PROVISIONAL` 로 표시했고 목록은 [SMC_CLAUDE.md](SMC_CLAUDE.md) 에 있다.

## 파일 구성

| 파일 | 정체 |
|---|---|
| [`ics_archon/`](ics_archon/) | ✅ **실기 취득 프로그램** (`v0.0.0`) — `ics_sim` 을 가져다 쓰고 그 아래 Archon 층을 채운다 |
| [`ics_archon.ini`](ics_archon.ini) | 설정 — `[archon]` 절이 컨트롤러 배선이다.  **`hk_latest`** 가 icg 의 HK 스냅샷 경로(5.6절 HK 카드의 원천)다 |
| [`icg_archon/`](icg_archon/) | ✅ **실기 ICG** (`v0.0.0`, 2026-08-31 신설) — guide 유닛 취득(raw spec v1.9 **9·10장**: `<SITE>.<날짜>.<번호>.G.fits`, frame-transfer 의미론) + **HK 취득·로깅**(1분 — Ctrl·진공·RTD·Radionode·AUX).  `python -m icg_archon` / `--backend sim`.  경위·판단은 [DevNote 9장](DevNote.md) |
| [`icg_archon.ini`](icg_archon.ini) | icg 설정 — `[icg]` 가 guide 컨트롤러 배선, `[hk]` 가 로깅, `[radionode]` 가 Tapaculo365 Open API 접속(콘솔의 "OPENAPI 매뉴얼" 값을 옮겨 적는다) |
| [`tools/gen_guidecards.py`](tools/gen_guidecards.py) | guide 견본 헤더 → `icg_archon/guidecards.py` 생성기 — 견본이 개정되면(v1.1 승격) 다시 돌린다.  `--diff` 는 science 폭 대조만 |
| [`INSTALL.md`](INSTALL.md) | ⭐ **벤치 설치 문서** — `~/AIC` 한 벌 세우기(XIS·OBSAgent·TCSAgent·ICS) · 기존 설치 이전 · 이상할 때 |
| [`tests/`](tests/) | **실기 없이 돌리는 검증** — `python -m pytest tests` (**300항목**, 약 4분). 배치본은 `-m "not repo_only"` (**244항목**).  ⚠️ 숫자를 손으로 유지하지 말 것 -- `python -m pytest --collect-only -q` 꼬리가 정본이다.  ⚠️ `ics_sim` 스위트와 **동시에 돌리지 말 것** — 부하로 `test_shutdown_waits_for_frames…` 가 간헐 실패한다 |
| [`tools/probe_archon.py`](tools/probe_archon.py) | ⭐ **실기 첫 실행 도구** — 미검증 3자리를 컨트롤러에 직접 물어본다 (1단계는 전원을 켜지 않는다) |
| [`tools/ics_archon_buftest.py`](tools/ics_archon_buftest.py) | **`LOCK`/`FETCH` 2x2 회귀 시험** — 엔진 라인 속도를 `idle`·`lock`·`fetch`·`nolock` 넷으로 견준다 (본편 무수정). 2026-09-01 실기 결론은 [`archon_lock_fetch_report.md`](archon_lock_fetch_report.md) |
| [`tools/extract_timing_script.py`](tools/extract_timing_script.py) | **ACF 의 타이밍 스크립트를 뽑는다** — `acf/acf_timing_script_{guide,science}.txt` 의 절차 정본. `--check` 로 대조, `--out` 으로 재추출.  ACF 를 고쳤으면 반드시 다시 뽑는다 (`tests/test_timing_script_extract.py` 가 지킨다) |
| [`tools/sync_vendor.py`](tools/sync_vendor.py) | **`ics_sim` 내장본 동기화** — `ics_archon` 만으로 돌게 만드는 자리. `--check` 로 확인만 |
| `ics_archon/_vendor/ics_sim/` | **내장본** (원천의 사본 + `MANIFEST.sha256`). 손으로 고치지 말고 `sync_vendor.py` 로 갱신한다 |
| [`acf/`](acf/) | **Archon 설정 파일 정본** (현행 6개 = science 5 + guide 1, `archive/` 구판 4개, 타이밍 스크립트 발췌 txt 2장) — 컨트롤러에 그대로 밀어 넣는 설정·타이밍. `BIGBUF` 가 science(1)/guide(0)를 가른다.  목록·주의는 [`acf/README.md`](acf/README.md) |
| [`scr_labtest/README_labtest.md`](scr_labtest/README_labtest.md) | ⭐ **실험실 취득 스크립트에 관한 모든 것** — 돌리기 전에 손볼 자리 · 첫 실행 점검 · 경고의 뜻 · 변경 내역 · 판 이력 |
| [`scr_labtest/archon_kmtnet_labtest_v1.3.bigbuf.py`](scr_labtest/archon_kmtnet_labtest_v1.3.bigbuf.py) | ✅ **현행 실험실 취득 스크립트** (`v1.3.4`, science 유닛).  유닛별 사본 셋(`KMTC-102`·`KMTC-113`·`KMTS-101`)이 나란히 있고 `tests/test_labtest_spec_copy.py` 가 표류를 막는다 |
| [`scr_labtest/archon_kmtnet_labtest_v1.3.smallbuf.py`](scr_labtest/archon_kmtnet_labtest_v1.3.smallbuf.py) | **small buffer 주소 지정 참고 코드** (`v1.3.4`) — 그 자체는 science 스크립트다.  guide 를 세울 때 본다 |
| [`tests/verify_labtest_v13.py`](tests/verify_labtest_v13.py) | **labtest 전용 검증** (32항목, 실패 0이어야 한다) — `python tests/verify_labtest_v13.py`.  읽기전용 자리 1건은 POSIX 에서만 돌고 윈도우에서는 `SKIP` |
| ⭐ [`DevNote.md`](DevNote.md) | **개발 노트** — 과정·판단 근거·시사점. "왜 이렇게 됐나" 는 여기 |
| [`SMC_CLAUDE.md`](SMC_CLAUDE.md) | **인수인계** — 상태 · 브랜치 · 절대 깨뜨리면 안 되는 것 · Archon 매뉴얼이 말하는 것(**확인 상태 표시**) |
| `__ref_archon_control/` | **읽기 전용 참조** — v1.0 원본 2부 + STA Archon 매뉴얼(2021-02-23) + ZTF Readout Notes(2014-10-30).  ⚠️ **매뉴얼은 판정 근거가 아니다** — 현행 FW 와 양방향으로 어긋날 수 있다(DevNote 8.7) |

`__` 접두 폴더는 읽기 전용이다 — 편집이 필요하면 이 루트로 사본을 떠서
작업한다(운영자 규칙 2026-08-22). `scr_labtest/` 의 **v1.1~v1.3.4 계보가 바로 그
사본**이고, v1.0 원본은 `__ref_archon_control/` 에 남아 있어 이력이 보존된다.

> **용량 메모** (2026-08-22 실측): `__ref_archon_control/` 의 PDF 2부(4.1 MB)는
> 저장소에 **각각 한 부뿐이다** — `cam_char/archon/` 을 포함해 다른 사본이 없다.
> 중복인 것은 v1.0 스크립트 2개(루트 사본)뿐이고 합쳐 100 KB 다.  저장소 전체
> 중복은 **21.3 MiB / 608 그룹**이고 그중 **20.5 MiB 가 `ics_legacy/`**(3사이트
> DTS 백업이 같은 파일을 3~9벌 보유) 다 — 나중에 용량을 확보할 때 볼 곳은
> 거기다.  `raw_fits_spec/__reference/` 가 PDF 포함 46개를 추적하는 선례가
> 있어 참조 자료를 저장소에 두는 것 자체는 이 저장소의 관례다.

## 실험실 취득 스크립트 — 핵심 참고사항

세부는 전부 **[README_labtest.md](scr_labtest/README_labtest.md)** 에 있다. 여기서는
폴더를 처음 보는 사람이 알아야 할 것만 적는다.

- **현행은 `v1.1.2`** (science 유닛, BIGBUF=1). v1.0 원본은 **실제로 돌려서 쓰던
  검증된 코드**이고, v1.1 은 그 위에 raw spec 을 얹은 개정판이다.
- **컨트롤러와의 왕복에서 v1.1 이 추가한 명령은 `STATUS` 하나뿐**이다. 그래서
  `TELEMETRY_ENABLE = False` 로 두면 왕복이 v1.0 과 완전히 같아진다 — 실기에서
  문제가 보일 때 원인을 가르는 첫 수단이다.
- **실기로는 한 번도 돌리지 않았다.** 헤더·파일명·검증 하네스는 통과했지만
  POWERON → FETCH 왕복은 미검증이다.
- **산출물 규격이 통째로 바뀌었다** — 파일명 `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits`,
  헤더 **144 레코드**(값 카드 131 + COMMENT 8 + `END` 1 + 공백 4 = 4x2880 =
  11,520B, 견본 바이트 재현), 날짜는 UTC. **기존 분석 스크립트는 glob 패턴과
  카드명을 갱신해야 한다.** ⚠️ raw spec v1.5(2026-08-26 반영)로 `<SITE>` 넷째
  코드가 `KMTT`→**`KMTK`**, HK 4장 폐지, `CHMAP_*` 토큰 3자→**4자** 가 됐고,
  **v1.6 으로 `ORIGNAME` → `EXPID`**(값에 `DETID` 필드(`.MK`/`.NT`)가 없어 pair 양쪽이
  같다 — 짝을 잇는 단일 키다) · `Cn_*` 나열 구분자가 공백 → **`|`** 가 됐다.
- **같은 UT 날짜의 재실행은 멱등하지 않다** (D-016 이 번호를 밀어 올린다 —
  v1.0 은 덮어썼다). 날짜가 다르면 영향 없다.
- **첫 실기 실행은 1프레임 연막시험으로.** 활성 실행 블록 그대로면 63프레임 /
  21.18 GiB 다.
- **헤더에 들어가는 손편집 문자열은 ASCII 전용**이다. 한글 한 자로 FITS 가
  통째로 깨지므로 기동에서 거부한다.
- **guide 유닛은 미개정** — guide raw 규격이 아직 없어서다.

## 본편 `ics_archon/` — 구성

`ics_sim` 의 시퀀서·명령 처리부·메시지 규약·헤더 층을 그대로 쓴다.  **독립
배포를 위해 내장본을 함께 들고 다니고**(`_vendor/ics_sim`), 저장소에서는 형제
원천이 이긴다 — 탐색 순서와 갈라짐 방지는 위 "설치 · 배치" 참조.

| 모듈 | 하는 일 |
|---|---|
| `archon/protocol.py` | 저수준 왕복 — 텍스트/이진 프레이밍, 참조번호, 시한 초과 후 재동기 |
| `archon/parse.py` | `SYSTEM`/`STATUS`/`FRAME` 해석. **왕복이 없어** 실기 응답 한 줄로 재현할 수 있다 |
| `archon/controller.py` | 컨트롤러 한 대의 제어 시퀀스 — ACF · 전원 · 노출 · 독출 · FETCH (asyncio) |
| `archon/monitor.py` | 텔레메트리 주기 감시·기록 (층 1·2) — CSV, `~/AIC/log/` |
| `archon/fitswrite.py` | raw pair 바이트 기록 — 견본 v1.0 이 정본, 데이터부 2880B 패딩 |
| `archon/backend.py` | `ics_sim` `DetectorBackend` 구현 (D-012) |
| `app.py` · `__main__.py` | `ics_sim.IcsSim` 에 백엔드를 끼우고 `ICSBUILD`/`RDMODE`/`CTRLnCFG`/종료를 갈아낀다 |
| `config.py` | `[archon]` 절 |

### 계약과 실기의 어긋남 — 백엔드가 흡수하는 셋

| 계약 | 실기 | 흡수 방식 |
|---|---|---|
| `initialize(ccd, …)` CCD 4회 | 컨트롤러 2대 | suffix 로 중복 제거 — `APPLYALL` 은 프레임마다 되풀이할 수 없다 |
| `erase(ccd)` master 한 번 | 두 대 다 비워야 한다 | 살아 있는 컨트롤러 전부에 퍼뜨린다 |
| 노출을 걸 자리가 없다 | `IntMS` + `LOADPARAMS` | 셔터 노출은 `open_shutter()`, DARK/BIAS 는 `readout()` 첫머리 |

**적분은 컨트롤러가 잰다.**  시퀀서의 카운트다운은 관측자 알림이고 하드웨어를
몰지 않는다.  그래서 `STOP` 은 적분을 자르지 못하고 셔터만 강제로 닫는다 —
근거와 한계는 `archon/controller.py` 머리말에 있다.

## 텔레메트리 감시·기록 (층 1·2)

컨트롤러 온도 10 + 전원 레일 7×2 + **바이어스 16채널 V/I** 를 주기적으로 떠서
CSV 로 남긴다.  원장 v1.14 가 `CCDTEMP` 대표 센서를 두고 **"센서 이상은 취득 SW
로그가 담는다"** 고 약속해 뒀는데 그 로그가 없었다 — 이것이 그 이행물이다.

```
~/AIC/log/telemetry.MK.20260828.csv        # 컨트롤러당 · 날짜당 하나
~/AIC/log/telemetry.NT.20260828.csv
```

| 열 | 무엇 |
|---|---|
| `utc` `age_ms` `lag_ms` | 시각 · 값의 나이 · **주기가 밀린 정도** |
| `expstatus` | ⚠️ 이 온도가 **독출 중 값인지 대기 중 값인지** — 사후에 시각으로 맞출 수 없다 |
| `valid` `count` `fresh` `log_n` | 응답 자체의 건강 (`fresh` = `COUNT` 가 직전 행과 달라졌나) |
| `power` `powergood` `overheat` | 전원·과열 |
| `T1..T10 [C]` | 규격 5.6.1절 **자리 = 항목** (열 이름이 `rawhdr.TEMP_MOD_LABELS`) |
| `V1..V7 [V]` `I1..I7 [A]` | 시스템 레일 — ⚠️ 전류 단위 **A** |
| `rail_flag` | 매뉴얼 p.41 정상 범위 이탈 (막지는 않는다) |
| `B_<라벨>_V [V]` `_I [mA]` | 바이어스 — ⚠️ 전류 단위 **mA**.  이름표는 **ACF** 에서 온다 |
| `event` | `start` `stop` `offline` `poll_failed` `resumed` |

**설정** (`[archon]`):

```ini
monitor          = true      # telemetry=false 면 이 값과 무관하게 안 돈다
monitor_interval = 20.0      # 수십 초 ~ 수 분 (운영자 확정)
monitor_log      = ~/AIC/log
```

### 접속자는 컨트롤러당 하나다 (운영자 확정 2026-08-28)

**본편이 기동에서 컨트롤러에 접속하고, 그 뒤에 감시를 시작한다.**  science
컨트롤러는 `ics_archon` 이, guide 는 `icg_archon` 이 맡고 **한 컨트롤러에 여러
노드가 붙는 구성은 두지 않는다.**  감시는 별개 프로세스가 아니라 이 프로세스
안의 태스크이고 **같은 소켓·같은 락**을 탄다.

- 접속은 `monitor` 설정과 **무관하다** — `monitor = false` 로 둬도 기동에서
  붙는다(그 스위치는 CSV 기록과 주기 폴링만 끈다).
- 기동 접속이 실패해도 **기동을 막지 않는다** — 컨트롤러 전원이 나중에 들어오는
  배치가 실재한다.  감시가 `monitor_interval` 마다 다시 시도하고, 감시를 껐으면
  첫 노출의 `prepare()` 가 시도한다.
- ⚠️ 그래서 **본편이 떠 있는 동안에는 STA GUI 도 `probe_archon` 도 붙이지
  않는다** — 설정으로 피하는 것이 아니라 **본편을 내리고 쓴다.**  Rev F
  백플레인(KASI 벤치기 `KMTK_SCI_113` · guide 유닛)은 동시 접속이 하나뿐이고
  (매뉴얼 p.15), Rev H(4접속)에서도 규칙은 같다.

**알아 둘 것 넷:**

1. **헤더용 값과 다른 자리에 든다.**  `Cn_TEMP/VOLT/CURR` 의 뜻은 여전히 "노출
   개시 시점 값" 이고, 감시는 `ctrl.status_live` 만 갱신한다.  섞으면 카드의
   뜻이 **폴링 간격·락 경합에 따라 노출마다 달라지는 값**으로 조용히 바뀐다.
2. **FETCH 가 락을 344 MiB 동안 쥔다** — 그동안 주기가 밀린다.  그것은 오류가
   아니라 `lag_ms` 에 적을 사실이고, **밀린 만큼 몰아서 뜨지 않는다.**
3. **`valid=0` 행도 버리지 않는다** — 언제부터 이상했는지가 자료다.  같은 응답이
   **헤더에서는 `NC`** 로 떨어진다(D4).
4. **`FETCHLOG` 는 쓰지 않는다** — `LOG=n` 한 열만 남긴다 (왕복 0).  드레인
   승격은 `probe_archon` 1단계로 한 번 보고 판단한다.

## 프레임이 안 나올 때 — `Sync In` 부터 본다

실기에서 **프레임이 한 장도 안 나오던 증상**의 원인은 `Sync In` 이 물려 상대
컨트롤러가 클록을 잡고 있던 것이었다 (labtest 2026-08-27 종결).  그때 관측된
조합이 이것이다:

```
POWER=4  POWERGOOD=1  FRAME=0/0/0  (영구)
```

**`POWERGOOD=1` 은 하드웨어 정상을 보장하지 않는다** — 컨트롤러 **자기 전원만**
보고하고 외부 클록 의존을 보지 않는다.  그래서 `ics_archon` 은 프레임 대기에
시한을 두고, **시한을 넘기면 진단 한 장을 항상 남긴다**(`frame_dump` 설정과
무관):

```
ERROR ... 프레임 대기 시한 초과 -- RBUF=0 WBUF=0  FRAME=0/0/0  COMPLETE=0/0/0
          LINES=0/0/0  POWER=4  POWERGOOD=1  OVERHEAT=0  TIMER=...
```

| 보이는 것 | 뜻 |
|---|---|
| `FRAME` 이 안 오름 | 노출 미개시 — `LOADPARAMS`·타이밍·**Sync In** |
| `FRAME` 은 오르는데 `COMPLETE=0` | 독출이 버퍼를 못 채운다 — 기하·tap |
| `TIMER` 가 안 변함 | 타이밍 코어 정지 |

평상시에 계속 보고 싶으면 `[archon] frame_dump = 5` (초).  ⚠️ **정상 취득이
도는 동안은 꺼 둔다** — 한 번에 왕복이 셋 는다.

⚠️ **시한은 적분이 끝난 뒤부터 센다** (`frame_timeout`).  DARK/BIAS 는 컨트롤러가
적분을 재므로 `IntMS` 를 걸고 곧바로 기다리는데, 시한을 지시 시점부터 세면
600초 dark 가 300초 상한에 걸려 **정상 프레임 중에 `DMA WAIT TIMEOUT`** 이 난다.

## 설치 · 배치 (리눅스)

**`ics_archon/` 하나만 두면 돌아간다.** `ics_sim` 을 설치하지 않아도 된다 —
그 층을 `ics_archon/ics_archon/_vendor/ics_sim/` 로 **내장해서 함께 들고 다닌다**
(운영자 확정 2026-08-23). 파이썬이라 빌드·설치 단계도 없다.

```
/home/<사용자>/
├── CEU/                          개발용 클론 — 여기서 고치고 커밋한다
└── AIC/                         운영 자리 (레거시 dts 처럼 역할 기준)
    ├── src/ics_archon/           ★ 배포본 — 이 폴더 하나면 된다
    │   ├── ics_archon/           패키지 (_vendor/ics_sim 포함)
    │   ├── tools/  tests/
    │   └── ics_archon.ini        (참조용 원본. 실제 설정은 Config/ 로)
    ├── bin/
    │   ├── xis…                  컴파일 산출물 (관례상 여기)
    │   └── ics_archon            얇은 실행 래퍼 (6절)
    ├── Config/
    │   ├── ics_archon.ini        ← 배포본 사본을 고쳐 쓴다
    │   ├── ics_archon.expnum     ← 노출 번호 (ini 옆으로 자동 결정)
    │   └── acf/                  ← Archon 설정 파일
    ├── Logs/ics_archon.log
    └── data/                     ← raw pair. 실제 디렉터리든 심볼릭 링크든 된다
```

### 왜 내장본인가 — 그리고 갈라지지 않는 근거

`ics_archon` 은 `ics_sim` 의 시퀀서·명령 처리부·메시지 규약·헤더 층을 그대로
쓴다. 종전에는 형제 폴더를 `sys.path` 에 넣었는데, 그러면 **두 폴더를 항상 함께
옮겨야 했다.**

사본을 두면 갈라진다 — 그것이 종전에 사본을 안 만든 이유였다. **그 걱정의 실체는
"사본" 이 아니라 "몰래 갈라짐" 이다.** 갈라짐을 기계가 잡으면 사본을 두어도 된다:

| 겹 | 무엇을 잡나 | 원천이 없어도 되나 |
|---|---|---|
| `_vendor/MANIFEST.sha256` | 내장본 손상·손편집 | ✅ 배포된 트리의 자가 진단 |
| `tests/test_vendor.py` ② | **원천과 갈라짐** (개정 누락) | ❌ 저장소에서만 |
| `tests/test_vendor.py` ③ | 배선이 틀려 독립 실행이 안 되는 것 | ✅ |

③은 **`ics_archon/` 만 떼어 놓은 임시 트리에서 실제로 노출을 돌려** 확인한다.

`ics_sim` 을 고쳤으면 동기화한다 — 안 하면 저장소 시험이 **실패**한다:

```bash
python3 tools/sync_vendor.py            # 동기화
python3 tools/sync_vendor.py --check    # 확인만 (CI)
```

### 탐색 순서

| 순서 | 어디 | 언제 |
|---|---|---|
| 1 | `ICS_SIM_PATH` 환경변수 | 명시적 지정 (탈출구) |
| 2 | 형제 폴더 `../ics_sim` | **저장소에서 개발할 때** — 살아 있는 원천 |
| 3 | 내장본 `_vendor/ics_sim` | **독립 배포** |

기동 배너의 `ics_sim` 줄이 **어느 것을 골랐는지** 찍는다. 셋 다 없으면 찾아본
경로를 다 찍고 멈춘다 — 조용히 실패하지 않는다.

### 1. 준비

| | |
|---|---|
| Python | **3.10 이상** |
| 필수 | **`numpy`** — FITS 저장형 변환. 없으면 백엔드가 **기동에서 거부**한다 |
| 선택 | `astropy` — `probe_archon` 되읽기 확인과 시험에만. **취득에는 필요 없다** |
| 시험 | `pytest` |

### 2. 자리 만들기

```bash
mkdir -p ~/AIC/{src,bin,Config/acf,Logs,data}
```

`~/AIC/data` 를 다른 디스크로 보내려면 실제 디렉터리 대신 링크를 둔다
(대상이 **먼저** 있어야 한다 — 끊긴 링크면 거부된다):

```bash
mkdir -p /mnt/bigdisk/data && ln -s /mnt/bigdisk/data ~/AIC/data
```

### 3. 배포본 놓기

**방법 A — 폴더만 복사** (가장 단순. `ics_sim` 이 필요 없다):

```bash
cd ~/CEU && git checkout ics_archon-v0.1.0
python3 ics_archon/tools/sync_vendor.py --check     # 내장본이 최신인지
rsync -a --delete --exclude='__pycache__' --exclude='__ref_archon_control' \
      ics_archon/  ~/AIC/src/ics_archon/
```

**방법 B — 배포용 클론** (되짚기가 쉽다. `git describe` 로 "무엇이 돌고 있나"):

```bash
git clone <저장소> ~/AIC/src/CEU
cd ~/AIC/src/CEU && git checkout ics_archon-v0.1.0
git describe --tags
```
→ 이 경우 실행 경로는 `~/AIC/src/CEU/ics_archon` 이고, 형제 `ics_sim` 이 함께
있으므로 **탐색 순서 2번**(원천)이 쓰인다.

> **개발 클론(`~/CEU`)에서 직접 돌리지 않는다.** 야간에 `git pull` 이나 브랜치
> 전환이 일어나면 돌고 있는 코드가 바뀐다.

### 4. 설정

```bash
cp ~/AIC/src/ics_archon/ics_archon.ini ~/AIC/Config/ics_archon.ini
cp <어딘가>/KMTNet_Sci_*.acf            ~/AIC/Config/acf/
```

고칠 것 — **`[archon]` 이 컨트롤러 배선이다**:

```ini
[node]
observatory  = KASI                 # **사이트를 정하는 단 하나의 값**
                                    #   CTIO | SSO | SAAO | KASI
                                    #   적은 값이 그대로 OBSERVAT 카드가 되고,
                                    #   사이트 코드 KMTC/KMTA/KMTS/KMTK 가 유도돼
                                    #   파일명·좌표·ORIGIN·INSTRUME·TELESCOP·
                                    #   FPAID 를 함께 끌고 간다.  모르는 값은
                                    #   기동 거부.  ⚠️ D-017: 구 TESTBED/KMTT
                                    #   는 폐지됐다 -- 남아 있으면 기동이 멈춘다
ic_ids       = M.IC, K.IC           # 유닛 한 대만 돌릴 때 (2대면 4개)
cb_ids       = M.CB, K.CB

[paths]
data_dir     = ~/AIC/data
expnum_file  =                      # 비우면 ini 옆 ics_archon.expnum

[archon]
n_controllers = 1                   # 유닛 한 대만 돌릴 때.  2대면 2
ctrl_mk_host = 10.0.0.13
acf_mk       = ~/AIC/Config/acf/KMTC_SCI_101_STA0284_R2608_MK.acf
monitor      = true                 # 텔레메트리 주기 감시·기록 (위 절)
                                    #   ⚠️ 접속은 이 값과 무관하다 -- 본편이
                                    #   기동에서 붙는다.  이 스위치는 CSV 기록과
                                    #   주기 폴링만 끈다
monitor_log  = ~/AIC/log            # ⚠️ data_dir 밑에 두지 말 것
fetch_buffers = 2                   # 호스트 수신·저장 버퍼 (컨트롤러당)
wrote_window  = 25.0                # OBSAgent force_fitssaved 창 [s] -- 선언값
full_flush_on_erase = false         # clock 개선으로 별도 erase 를 하지 않는다
lock_buffer   = true                # fetch 중 프레임 버퍼를 LOCKn 으로 잠근다
fetch_timeout = 10                  # FETCH 상한 = 잠금 상한 -- 주기(13.27초) 아래 (DevNote 10.6)
recheck_after_fetch = true          # fetch 뒤에 덮이지 않았는지 한 번 더 대조

[controllers]
ctrl1_id     = KMTA-SCI-101         # 비우면 컨트롤러 보고값(BACKPLANE_ID)
ctrl1_sn     = STA-0288
ctrl1_cfg    =                      # 비우면 [archon] acf_mk 에서 파생 (아래)

[logging]
file         = ~/AIC/Logs/ics_archon.log
```

> ⭐ **호스트 수신 버퍼는 링이다** (2026-08-29). `[archon] fetch_buffers`(기본 **2**)
> 만큼만 잡아 **재사용**하고, 다 차면 FETCH 가 **기다리며 그 횟수를 센다**
> (`buf_waits`). 종전에는 프레임마다 344 MiB 를 새로 잡아 저장이 밀리면 메모리가
> 조용히 늘었다. ⚠️ **`wrote_window` 와 짝이다** — `N = ceil((창 − write_delay) /
> 주기)`. 25초 창엔 2개, **30초로 넓히면 3개**가 필요하고 기동에서 검사한다.
> 2개 = 1.4 GB · 3개 = 2.2 GB (벤치 RAM 32 GB).

> ⚠️ **매뉴얼은 판정 근거가 아니다** (운영자 2026-08-30). 개정판이 2021-02-23 이라
> **현행 FW 가 매뉴얼을 다 반영하지 않은 부분도, 반대로 매뉴얼에 있는데 FW 에 없는
> 경우도 있었다.** ⭐ **판단 근거는 실측**이고, 매뉴얼은 *무엇을 재야 하는지* 알려
> 주는 가설 생성기다. `lock_buffer` 기본값이 `true` 인 것도 *"매뉴얼이 그렇다"* 가
> 아니라 **실측으로 값이 확인됐기 때문**이다 (2026-09-01, 두 유닛) — 대가 0(`lock` =
> `idle` = 368 행/초), 지킬 구간 실재(`nolock` 에서 경계가 걸리면 엔진이 읽는 중인 버퍼로
> 옮겨온다, 2/2). 자세한 것은 `DevNote.md` 8.7 · 10.6.

> ⭐ **`FETCH` 로그 줄이 잠금 관측값을 싣는다** — `[lock=True RBUF=1 WBUF=0->2]`.
> `LOCK1` 을 보냈는데 `RBUF` 가 1 이 아니면 경고가 뜬다(그때는 `recheck_after_fetch` 가
> 유일한 방어다). ✅ 두 FW(1252·1261)에서 **15/15 반영**을 확인했으므로(2026-09-01,
> DevNote 10.4) 이 경고는 **FW 회귀 신호**다 — 종전의 "`RBUF` 미구현일 수 있다" 는 닫혔다.
> 왕복은 안 늘었다(덮임 대조가 이미 읽는 `FRAME` 에서 뽑는다).

> ⭐ **fetch 중에 버퍼가 덮이는 것을 두 겹으로 막는다** (2026-08-30).
> `lock_buffer`(기본 `true`)가 `LOCKn` 으로 **막고**, `recheck_after_fetch`
> (기본 `true`)가 fetch 뒤에 한 번 더 대조해 **덮였으면 그 자료를 버린다**.
> fetch 앞의 대조는 직전 한 순간만 보는데 fetch 자체가 3.2~3.5초라(2026-09-01 실측), 그 사이에 덮이면
> **앞뒤가 다른 누더기 파일**이 길이·헤더 정상으로 나온다 — 로그에도 안 남는다.
> ⭐ **`lock_buffer = false` 로 둘 때 `recheck_after_fetch` 가 필요하다.**
> ⚠️ **둘 다 끄지 말 것** — 그러면 그 창을 보는 것이 아무것도 없고, 기동
> 교차검사가 그 조합을 알린다. 잠겨 있으면 재대조는 절대 안 걸리므로 켜 두는
> 값이 사실상 없다(왕복 하나).

> ⛔ **`full_flush_on_erase` 기본값은 `false` 다** (운영자 확정 2026-08-29) —
> *"clock 을 개선해서 별도 erase 를 하지 않고 바로 노출을 시작한다"*. ⚠️ 켜면
> 노출마다 **독출 1회분(실측 12.77초 — 사강 `NoIntMS` 0.5 가 붙으면 13.27초, DevNote 10.4)**
> 이 더 붙어 주기가 13.27 → 약 26초가 된다 (추정).

> **`CTRL1CFG`/`CTRL2CFG` 는 ACF 경로에서 나온다** (2026-08-29 v1.8 확정, 현행 규격 v1.9 5.5절).
> `[controllers] ctrlN_cfg` 를 **비워 두면** `[archon] acf_mk`/`acf_nt` 에서
> **폴더와 확장자(`.acf`/`.cfg`)를 뗀 이름**이 실린다 —
> `~/AIC/Config/acf/KMTC_SCI_101_STA0284_R2608_MK.acf` →
> `'KMTC_SCI_101_STA0284_R2608_MK'`.  적어 두면 **그 값이 이기고**, 파생값과
> 다르면 기동에서 경고한다(헤더가 주장하는 설정 파일과 실제로 올리는 파일이
> 갈린 자료는 나중에 봐도 드러나지 않는다).  `RDMODE` 와 같은 규칙이다.

> **`~` 는 펼쳐진다** (`data_dir` · `expnum_file` · `logging file` · `acf_*`).
> **상대경로는 권하지 않는다** — ini 위치가 아니라 **실행한 디렉터리** 기준으로
> 풀려서, 띄우는 방법이 바뀌면 자료가 조용히 다른 곳에 쌓인다.
>
> **로그는 반드시 파일로 받는다.** 터미널 스크롤백은 페인 폭 경계에서 한 글자씩
> 먹혀 와이어 손상과 구분이 안 된다 (DevNote 3.7.2 실측).

### 5. 돌리기

```bash
cd ~/AIC/src/ics_archon
python3 -m ics_archon -c ~/AIC/Config/ics_archon.ini
```

**첫 실행은 본편이 아니라 `probe_archon` 1단계부터** — 아래 "실기 첫 실행 절차".

```bash
python3 tools/probe_archon.py -c ~/AIC/Config/ics_archon.ini --host 10.0.0.13
```

### 6. 실행 래퍼 (`~/AIC/bin/ics_archon`)

`cd` 를 사람이 기억하지 않게 한다. **작업 디렉터리를 못박는 것이 요점**이다 —
상대경로 설정과 `_simpath` 탐색이 둘 다 여기에 걸린다.

```sh
#!/bin/sh
# ~/AIC/bin/ics_archon -- 실기 ICS 실행 래퍼
set -eu
AIC="$HOME/AIC"
cd "$AIC/src/ics_archon"
exec python3 -m ics_archon -c "$AIC/Config/ics_archon.ini" "$@"
```

```bash
chmod +x ~/AIC/bin/ics_archon
~/AIC/bin/ics_archon --backend sim      # 컨트롤러를 안 만지고 메시지 층만
```

### 7. 서비스로 돌릴 때

콘솔(stdin)을 쓰지 않으므로 `[behavior] console = false` 로 둔다.

```ini
[Service]
WorkingDirectory=/home/<사용자>/AIC/src/ics_archon
ExecStart=/home/<사용자>/AIC/bin/ics_archon
Restart=on-failure
```

### 8. 여러 구성을 나란히

**ini 를 나누면 노출 번호도 자동으로 나뉜다** (`expnum` 이 ini 이름을 따른다):

```
~/AIC/Config/ics_archon.ini      →  ics_archon.expnum
~/AIC/Config/ics_archon_lab.ini  →  ics_archon_lab.expnum
```

### 갱신 · 되돌리기

```bash
cd ~/AIC/src/ics_archon
python3 -m pytest tests -q -m "not repo_only"      # 배치본 -- 실패 0
```

⚠️ **배치본에서는 `-m "not repo_only"` 를 붙인다.**  붙이지 않으면 17개가
실패하는데 설치가 깨진 것이 아니다 — 그 17개는 **저장소에만 있는 원천**을
대조하는 시험이라 배치본에는 대조할 상대가 없다.

| `repo_only` 표식 | 개수 | 왜 |
|---|---|---|
| `test_fitswrite.py` 견본 pair 바이트 재현 | 4 | 견본 pair 파일이 배포 트리 밖(`raw_fits_spec/`)에 있다 |
| `test_labtest_spec_copy.py` labtest 규격 사본 대조 | 9 | 원천 `ics_sim` 이 배치본에 없다 (같은 파일의 배포 ini 대조 1건은 표식이 없다 — ini 는 배치본에도 간다).  **상수 대조만이 아니라 카드 절단 규범·나열 자리 채움 같은 동작도 본다** (v1.6) |
| `test_vendor.py` 벤더 표류 대조 | 4 | 형제 `ics_sim/` 원천이 배치본에 없다 |

**223 통과 · 실패 0 이 배치본의 기대값이다** (2026-08-31 실측).  그 밖의 실패는 정상이 아니다.

⚠️ **저장소에서는 `-m "not repo_only"` 를 쓰지 말 것.**  표식의 뜻은 "안 돌려도
되는 시험" 이 아니라 "배치본에는 대조할 원천이 없다" 다.  저장소에서 빼면
**벤더 표류와 견본 어긋남을 놓친다** — 그 둘이 raw spec 5장 개정이 왔을 때
울리는 알람이다.  **2026-08-26 의 v1.5 반영이 그 알람으로 시작됐다.**
저장소에서는 표식 없이 전부 돌린다 (**300항목** = 배치본 244 + `repo_only` 56).

- **야간에는 갱신하지 않는다.** 돌고 있는 코드가 바뀐다.
- `~/AIC/Config/` 의 ini 는 배포본 밖이라 **덮이지 않는다.** 새 키가 생겼는지는
  `diff ~/AIC/Config/ics_archon.ini ~/AIC/src/ics_archon/ics_archon.ini`.
- 되돌리기: 방법 A 는 이전 태그에서 다시 `rsync`, 방법 B 는 `git checkout <태그>`.
- FITS `ICSBUILD` 가 `v<버전>:<빌드일시>` 를 싣는다. **손으로 적는 값**이므로
  (`ics_archon/__init__.py`) 소스를 고쳤으면 같이 올려야 하고, 그래서 헤더에서
  "이 자료를 만든 코드" 를 되짚을 수 있다.

## 실기 첫 실행 절차

**본편을 그냥 돌리지 말 것.** 미검증 3자리가 한꺼번에 걸리면 원인을 가릴 수
없다. `tools/probe_archon.py` 가 위험이 낮은 것부터 하나씩 확인한다 — 본편과
**같은 모듈**을 쓰므로 여기서 통과한 것은 본편에서도 통과한다.

⚠️ **본편을 내리고 돌린다.**  `ics_archon` 은 기동에서 컨트롤러에 접속하고
**접속자는 컨트롤러당 하나**다(운영자 확정 2026-08-28).  Rev F 백플레인은 동시
접속이 하나뿐이라(매뉴얼 p.15) 물리적으로도 못 붙고, Rev H 라도 같은 규칙이다.

### 1단계 — 읽기 전용 (전원을 켜지 않는다)

```bash
python tools/probe_archon.py --host 10.0.0.13
```

`SYSTEM`·`STATUS`·`FRAME` 원문을 다 찍고, 가정을 대조한다 — 장착 모듈이 규격
5.6.1절 자리 표와 맞는지 · 온도 슬롯·전원 레일 결측 · 기하 vs 선언 ·
`BUFnLINES` 존재 · `Cn_*` 카드의 폭(견본 51자를 넘으면 규격 5.0절대로
**comment 가 먼저 줄고**, 66자를 넘어야 값이 잘린다) · **`Cn_TEMP` 자리 수가
규격 5.6.1절 표와 같은지**.
**여기서 `문제` 가 하나라도 나오면 그것부터 고친다.**

여기에 **감시가 기다리는 확인 항목**도 함께 나온다 (2026-08-28 추가):

| 보이는 것 | 무엇을 판정하나 |
|---|---|
| `VALID` / `COUNT` / `LOG` 보고 여부 | D4(무효 응답 → 헤더 `NC`) · 기록의 `fresh`/`log_n` 열이 살아 있나 |
| 전원 레일 정상 범위 (p.41) | `rail_flag` 열의 기준.  유닛이 다르면 `[archon.rails]` 로 덮는다 |
| **바이어스 채널 표** | 층 2 — 이름표는 **ACF**, 값은 **STATUS** 다.  ⚠️ 두 dict 의 키 문자열이 같으니 섞어 읽지 말 것 |

⚠️ **`LOG` 은 여기서 사람이 한 번 보고 판단할 것이 있다** — 값의 상한, 로그 한
줄의 생김새(자체 시각·심각도가 붙나).  항목이 **모듈·채널 수준의 정체**를 담으면
(`MOD9 HVHC4 failed to reach setpoint` 같은) `FETCHLOG` 드레인을 넣을 값이 있고,
`config applied` 수준이면 **안 쓴다**(우리 로그가 이미 더 잘 담는다).

### 2단계 — ACF 대조 (여전히 읽기 전용)

```bash
python tools/probe_archon.py --host 10.0.0.13 --acf acf/KMTC_SCI_101_STA0284_R2608_MK.acf
```

`[archon] param_intms_slot`/`param_exposures_slot` 이 그 ACF 에 있는지, 컨트롤러
메모리의 같은 줄 번호가 그 키인지 `RCONFIG` 로 확인만 한다. **어긋난 채로
돌리면 노출 시간이 조용히 안 바뀐다.**

### 3단계 — 프레임 1장 ⚠️ 전원 ON

```bash
python tools/probe_archon.py --host 10.0.0.13 --acf acf/... --expose 0 --write
```

`--expose` 를 준 경우에만 돈다. 셔터는 열지 않는다(`TRIGOUTFORCE=1`). 끝나면
무슨 일이 있어도 `POWEROFF`. **여기서 나오는 값이 3단계의 산출물이다** —
독출 실측 시간 · 진행률 보고 횟수 · FETCH MiB/s · FITS 1장(`probe.*.fits`,
관측 번호 공간을 건드리지 않는다).

⭐ **`POWERON` 로그도 여기서 처음 본다** (2026-08-28 추가) — flush 대기
(`poweron_wait`, 기본 12초) **안에서** `STATUS` 를 되물어 `POWER=4` 를
확인하고 `POWER=4 (On) 확인 -- N초` 를 남긴다.  **`N` 이 실측 램프 시간**이라
12초가 충분한지의 근거가 된다.  4 에 못 닿으면 `ERROR` 한 줄이 나가지만
**막지는 않는다** — 값이 아직 실기 미검증이라 오독으로 관측을 세우는 쪽이 더
나쁘다.  ⚠️ 대기 시간 자체는 램프가 아니라 **CCD flush** 를 기다리는 것이라
`POWER=4` 를 봤다고 줄이지 말 것.

> 실측한 독출 시간을 `[timing]` 에 넣고, `write_delay + FETCH + 저장`이
> **25초 창**(`[obsagent] force_fitssaved`)에 들어가는지 확인한다.

### 4단계 — 본편, 실험실 1유닛

실험실은 유닛이 한 대이므로 `MK` pair 만 돌린다. `ics_archon.ini` 세 곳:

```ini
[node]
ic_ids = M.IC, K.IC        # NT 를 빼면 그 파일은 생기지 않는다
cb_ids = M.CB, K.CB
master = K

[controllers]
ctrl1_id = KMTA-SCI-101    # **선언한 쪽이 그 한 대다** (색인 1 = MK)

[archon]
n_controllers = 1          # 1 또는 2.  그 밖은 기동 거부
ctrl_mk_host = 10.0.0.13
acf_mk       = acf/KMTC_SCI_101_STA0284_R2608_MK.acf
```

> `n_controllers = 1` 이면 `[controllers] ctrl1_id`(→`MK`) / `ctrl2_id`(→`NT`)
> 의 **선언 여부**가 어느 컨트롤러인지 정한다.  둘 다 선언하면 기동을 거부한다.
> ⚠️ **색인이 태그를 정하고 이름 문자열은 읽지 않는다** — 이름 끝 번호
> (`101`/`103`/`104`…)는 유닛마다 다르고 색인과 관계없다.  정본은 배선
> (`ctrl_mk_host`/`ctrl_nt_host`)이다.
> "없음" 은 빈 값 · `NC` 가 같은 뜻이라 **한쪽만 적어도, 둘 다 적고
> 한쪽을 `NC` 로 둬도 된다.**  빠진 쪽의 `CTRLnID/SN/CFG` 카드는 **빼지 않고**
> 값에 규격 5.0절 sentinel `NC` 가 실린다.

```bash
python -m ics_archon
```

콘솔에서 `projid ENG` → `dark begin` → `exp 1` → `go`. OBSAgent 없이
direct-reply 로 전 경로가 돈다.

> ⚠️ **이 구성은 OBSAgent 규약을 만족하지 못한다** — `Acquisition Complete.` 와
> `Wrote` 가 4회가 아니라 2회다(CCD 가 둘이니까). 관측 시퀀스 시험은 유닛 2대가
> 붙은 뒤에 한다. 4단계의 목적은 **취득·저장 경로**를 실기로 확인하는 것이다.

### 5단계 — 유닛 2대 + OBSAgent

`ic_ids` 를 4개로 돌리고 `ctrl_nt_host`/`acf_nt` 를 채운다. 여기서 비로소
`Acquisition Complete.` 4회 · `Wrote` 4회 · 시간 창 3종이 검증된다.

## 아직 없는 것 (v0.0)

**요약** — LED 프로젝터 배선 · binning · 바이어스 측정값의 헤더 수록(로그만
있다).  ~~듀어·환경 HK~~ 와 ~~guide 계통~~ 은 **2026-08-31 `icg_archon` 신설**로
경로가 생겼다 — HK 는 `[archon] hk_latest` 로 icg 스냅샷을 읽고(icg 가 꺼져
있으면 종전대로 sentinel), guide 취득은 `icg_archon/` 이 맡는다 (실기 미검증).

⚠️ **각 항목의 근거와 착수 조건은 [SMC_CLAUDE.md](SMC_CLAUDE.md) 에 있다** —
여기 두면 "쓰는 법" 과 "남은 일" 이 섞인다.


## 관련 문서

| 문서 | 위치 |
|---|---|
| **경위·판단 (왜 그렇게 정했나)** | ⭐ [`DevNote.md`](DevNote.md) — **이 폴더의 개발 노트** |
| 〃 (`ics_sim` 층 · 2026-08-26 이전 실기분) | [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 11.22~11.30 |
| 산출 규격 (raw FITS pair) | [`../raw_fits_spec/`](../raw_fits_spec/README.md) |
| 헤더 카드 템플릿 (공유 원천) | `../ics_sim/ics_sim/rawcards.py` |
| 백엔드 계약 | `../ics_sim/ics_sim/hardware/base.py` (D-012) |
| L0 MEF ICD · converter | `../mef_fits_spec/` · `../mef_converter/` |

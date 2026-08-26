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
| [`ics_archon.ini`](ics_archon.ini) | 설정 — `[archon]` 절이 컨트롤러 배선이다 |
| [`INSTALL.md`](INSTALL.md) | ⭐ **벤치 설치 문서** — `~/AIC` 한 벌 세우기(XIS·OBSAgent·TCSAgent·ICS) · 기존 설치 이전 · 이상할 때 |
| [`tests/`](tests/) | **실기 없이 돌리는 검증** — `python -m pytest tests` (110항목). 배치본은 `-m "not repo_only"` (103항목) |
| [`tools/probe_archon.py`](tools/probe_archon.py) | ⭐ **실기 첫 실행 도구** — 미검증 3자리를 컨트롤러에 직접 물어본다 (1단계는 전원을 켜지 않는다) |
| [`tools/sync_vendor.py`](tools/sync_vendor.py) | **`ics_sim` 내장본 동기화** — `ics_archon` 만으로 돌게 만드는 자리. `--check` 로 확인만 |
| `ics_archon/_vendor/ics_sim/` | **내장본** (원천의 사본 + `MANIFEST.sha256`). 손으로 고치지 말고 `sync_vendor.py` 로 갱신한다 |
| [`scr_labtest/README_labtest.md`](scr_labtest/README_labtest.md) | ⭐ **실험실 취득 스크립트에 관한 모든 것** — 돌리기 전에 손볼 자리 · 첫 실행 점검 · 경고의 뜻 · 변경 내역 · 판 이력 |
| [`scr_labtest/archon_kmtnet_labtest_v1.2.bigbuf.py`](scr_labtest/archon_kmtnet_labtest_v1.2.bigbuf.py) | ✅ **현행 실험실 취득 스크립트** (`v1.2.0`, science 유닛) |
| [`scr_labtest/archon_kmtnet_labtest_v1.0.smallbuf.py`](scr_labtest/archon_kmtnet_labtest_v1.0.smallbuf.py) | **guide 유닛용 참고 사본** — 원본 그대로, 미개정 |
| [`tests/verify_labtest_v12.py`](tests/verify_labtest_v12.py) | **labtest 전용 검증** (19항목) — `python tests/verify_labtest_v12.py` |
| [`SMC_CLAUDE.md`](SMC_CLAUDE.md) | **인수인계** — 상태 · 브랜치 · 절대 깨뜨리면 안 되는 것 · Archon 매뉴얼 확정 사실 |
| `__ref_archon_control/` | **읽기 전용 참조** — v1.0 원본 2부 + STA Archon 매뉴얼(2021-02-23) + ZTF Readout Notes(2014-10-30) |

`__` 접두 폴더는 읽기 전용이다 — 편집이 필요하면 이 루트로 사본을 떠서
작업한다(운영자 규칙 2026-08-22). v1.1 이 바로 그 사본이고, v1.0 원본은
`__ref_archon_control/` 에 남아 있어 이력이 보존된다.

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
| `archon/fitswrite.py` | raw pair 바이트 기록 — 견본 v1.0 이 정본, 데이터부 2880B 패딩 |
| `archon/backend.py` | `ics_sim` `DetectorBackend` 구현 (D-012) |
| `app.py` · `__main__.py` | `ics_sim.IcsSim` 에 백엔드를 끼우고 `ICSBUILD`/`RDMODE`/종료를 갈아낀다 |
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
acf_mk       = ~/AIC/Config/acf/KMTNet_Sci_fast_med_U13.acf

[controllers]
ctrl1_id     = KMTA-SCI-101         # 비우면 컨트롤러 보고값(BACKPLANE_ID)
ctrl1_sn     = STA-0288

[logging]
file         = ~/AIC/Logs/ics_archon.log
```

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

**135 통과 · 실패 0 이 배치본의 기대값이다.**  그 밖의 실패는 정상이 아니다.

⚠️ **저장소에서는 `-m "not repo_only"` 를 쓰지 말 것.**  표식의 뜻은 "안 돌려도
되는 시험" 이 아니라 "배치본에는 대조할 원천이 없다" 다.  저장소에서 빼면
**벤더 표류와 견본 어긋남을 놓친다** — 그 둘이 raw spec 5장 개정이 왔을 때
울리는 알람이다.  **2026-08-26 의 v1.5 반영이 그 알람으로 시작됐다.**
저장소에서는 표식 없이 전부 돌린다 (**152항목** = 배치본 135 + `repo_only` 17).

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

### 1단계 — 읽기 전용 (전원을 켜지 않는다)

```bash
python tools/probe_archon.py --host 10.0.0.13
```

`SYSTEM`·`STATUS`·`FRAME` 원문을 다 찍고, 가정을 대조한다 — AD 모듈 슬롯(5~8) ·
온도 슬롯·전원 레일 결측 · 기하 vs 선언 · `BUFnLINES` 존재 · `Cn_*` 카드의 폭
(견본 51자를 넘으면 규격 5.0절대로 **comment 가 먼저 줄고**, 66자를 넘어야
값이 잘린다) · **`Cn_TEMP` 자리 수가 규격 5.6.1절 표와 같은지**.
**여기서 `문제` 가 하나라도 나오면 그것부터 고친다.**

### 2단계 — ACF 대조 (여전히 읽기 전용)

```bash
python tools/probe_archon.py --host 10.0.0.13 --acf acf/KMTNet_Sci_fast_med_U13.acf
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
acf_mk       = acf/KMTNet_Sci_fast_med_U13.acf
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

- **듀어·환경 HK** (`sensors()`) — 공급 3계통(ICG RTD · standalone RTD ·
  Tapaculo)을 읽는 경로가 없다.  labtest 도 안 읽으므로 **옮겨올 원형이 없다.**
  `CCDTEMP` 를 비롯한 5.6절 카드가 sentinel 로 실린다.
- **LED 프로젝터** (`flash_led`) — 실기 배선이 미확정이라 값만 기억하고
  하드웨어를 만지지 않는다.
- **guide 계통** — guide raw 규격이 아직 없다.  착수 시 smallbuf 구성 +
  `DATASRC='ARCHON_GUIDE'` + `CTRL1xx` 한 벌 규약 (raw spec 5.5절).
- **binning** (`BIN` 명령) — `ics_sim` 쪽도 스텁이다.

## 관련 문서

| 문서 | 위치 |
|---|---|
| 경위·판단 (왜 그렇게 정했나) | [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 11.19~11.26 |
| 산출 규격 (raw FITS pair) | [`../raw_fits_spec/`](../raw_fits_spec/README.md) |
| 헤더 카드 템플릿 (공유 원천) | `../ics_sim/ics_sim/rawcards.py` |
| 백엔드 계약 | `../ics_sim/ics_sim/hardware/base.py` (D-012) |
| L0 MEF ICD · converter | `../mef_fits_spec/` · `../mef_converter/` |

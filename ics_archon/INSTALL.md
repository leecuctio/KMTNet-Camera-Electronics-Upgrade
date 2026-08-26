# 벤치 설치 — `~/AIC` 한 벌 세우기

리눅스 기계(**AIC**)에 관측 계통 전체를 처음부터 세우는 절차다.  다섯 프로그램이
같은 설치 루트 `~/AIC` 를 공유한다.

| 프로그램 | 정체 | 언어 | 설치 방식 |
|---|---|---|---|
| **XIS** (`isis`·`isisd`) | 메시지 허브 | C | `build-local.sh` 가 `~/AIC/bin/` 에 설치 |
| **OBSAgent** (`obstool`) | 관측자 콘솔 | C | 빌드 후 **손으로** `bin/` 에 복사 |
| **TCSAgent** (`pctcs`) | 망원경·AUX 제어 | C | 〃 |
| **`ics_sim`** | 카메라 통합제어 (시뮬) | Python | 설치 없음 — 체크아웃에서 실행 |
| **`ics_archon`** | 카메라 통합제어 (실기) | Python | 〃 |

> **이미 `~/AICS` 로 돌고 있는 기계**는 아래 [기존 설치 이전](#기존-설치-이전) 으로.

---

## 0. 의존 패키지

```bash
sudo apt install build-essential libreadline-dev libcurl4-openssl-dev python3-numpy
```

| 패키지 | 누가 쓰나 |
|---|---|
| `build-essential` | `make`·`ar`·`ranlib`·`g++` — C 프로그램 셋 다 |
| `libreadline-dev` | XIS · OBSAgent · TCSAgent |
| `libcurl4-openssl-dev` | **OBSAgent 만** (v1.0.0 부터 `-lcurl`) |
| `python3-numpy` | **`ics_archon` 필수** — FITS 저장형 변환.  없으면 백엔드가 **기동에서 거부**한다 |

Python 은 **3.10 이상**.  `astropy` 는 선택이다 — `tools/probe_archon.py` 의 되읽기
확인과 시험에만 쓰고 **취득 경로에는 필요 없다**.  시험을 돌리려면 `pytest`.

## 1. 저장소

```bash
git clone https://github.com/leecuctio/KMTNet-Camera-Electronics-Upgrade.git \
          ~/CEU/KMTNet-Camera-Electronics-Upgrade
cd ~/CEU/KMTNet-Camera-Electronics-Upgrade
git checkout ics-archon-v1.0-build
```

SSH 키를 쓰는 기계라면 `git@github.com:leecuctio/KMTNet-Camera-Electronics-Upgrade.git`.

⚠️ **`ics_archon` 은 아직 `main` 에 없다** — 브랜치를 반드시 갈아탈 것.  `main` 을
그대로 쓰면 설치 루트가 옛 `AICS` 로 잡힌다.

## 2. 자리 만들기

```bash
mkdir -p ~/AIC/{src,bin,Config/acf,Logs,data,osc}
```

`~/AIC/data` 를 다른 디스크로 보내려면 실제 디렉터리 대신 링크를 둔다:

```bash
mkdir -p /mnt/bigdisk/data && ln -s /mnt/bigdisk/data ~/AIC/data
```

⚠️ **링크 대상이 먼저 있어야 한다** — 끊긴 링크면 `makedirs(exist_ok=True)` 가
`FileExistsError` 로 거부한다 (`exist_ok` 는 `isdir` 을 본다).

### `~/AIC` 아래 무엇이 무엇인가

| 자리 | 성질 | 지워도 되나 |
|---|---|---|
| `build/` | **전부 생성물** | ✅ 언제든 |
| `bin/` | 설치된 실행 파일 | ✅ 다시 만들면 됨 |
| `Config/` | 설정 + **`*.expnum`(노출 번호 카운터)** | ❌ **절대 금지** |
| `Logs/` · `data/` | 로그 · 취득 자료 | ❌ |
| `osc/` | 관측 스크립트(`.osc`) — 저장소에서 복사해 둔다 | ✅ 다시 복사하면 됨 |

## 3. C 프로그램 셋 빌드

⚠️ **작업 디렉터리는 저장소 체크아웃이다** — 아래 `./...` 경로가 그 기준이다.

```bash
cd ~/CEU/KMTNet-Camera-Electronics-Upgrade
bash ./ics_sim/xis/build-local.sh --build-dir ~/AIC/build/xis --prefix ~/AIC
bash ./OBSAgent/build-local.sh --site kmtna
bash ./TCSAgent/build-local.sh --site kmtna
```

- **`--site`**: `kmtna`=SSO(기본) · `kmtnc`=CTIO · `kmtns`=SAAO · `kmtnt`=TestBed
- ⚠️ **XIS 만 `--prefix` 를 꼭 줘야 한다.**  기본값이 `$HOME/xis` 다.  OBS/TCS 는
  기본이 `$HOME/AIC` 라 생략해도 된다
- **순서는 상관없다** — 두 에이전트가 공유하는 `libisis.a` 를 이제 둘 다 **항상
  다시 만든다**
- 세 스크립트 모두 **설정 파일이 이미 있으면 건드리지 않는다** (2026-08-24 실측:
  XIS 재빌드가 `isis.ini` 를 보존한다).  다시 만들려면 해당 `.ini` 를 지우고 실행

> `bash ` 를 앞에 붙이는 것은 실행 비트가 없을 때다.  `./OBSAgent/build-local.sh`
> 가 `Permission denied` 면 그것이다.

> **세 스크립트가 `~/AIC/bin/` 까지 설치한다.**  따로 복사할 필요가 없다.
> ⚠️ 돌고 있는 실행 파일에는 `install` 이 실패한다(`Text file busy`) — 빌드 전에
> 내릴 것.

## 4. Python 계통 설정

```bash
cp ics_sim/ics_sim.ini       ~/AIC/Config/ics_sim.ini
cp ics_archon/ics_archon.ini ~/AIC/Config/ics_archon.ini
cp <어딘가>/KMTNet_Sci_*.acf ~/AIC/Config/acf/
```

관측 스크립트(`.osc`)는 `~/AIC/osc/` 에 둔다 — obstool 이 절대경로로 읽는다:

```bash
cp ics_sim/osc/*.osc ~/AIC/osc/
```

`ics_sim`·`ics_archon` 은 설치하지 않고 체크아웃에서 돌린다.  배포본을 따로 두려면
[README.md](README.md) "3. 배포본 놓기" 의 방법 A(폴더 복사) / B(배포용 클론).

> **개발 클론에서 직접 돌리지 않는다.**  야간에 `git pull` 이나 브랜치 전환이
> 일어나면 돌고 있는 코드가 바뀐다.

고칠 것은 `[node] observatory`(사이트 — `KASI`/`CTIO`/`SSO`/`SAAO`)와
`[archon]`(컨트롤러 배선 · `n_controllers`) 이다 — 자세히는
[README.md](README.md) "4. 설정".

## 5. 확인

```bash
for f in ~/AIC/bin/*; do printf '%-10s AICS:%s\n' "$(basename $f)" \
  "$(strings $f | grep -c AICS)"; done          # 전부 0
grep -rn 'AICS' ~/AIC/Config/                    # 아무것도 안 나와야 한다
strings ~/AIC/bin/obstool | grep -E 'tmp/obs|OBSSTATFILE'   # 4줄
strings ~/AIC/bin/pctcs   | grep 'tmp/pctcs'                # 1줄
```

`AICS` 가 남아 있으면 그 바이너리·설정은 **옛 판**이다.

## 6. 기동

창 네 개로 띄운다.

```bash
# 창 0  XIS   (-f 와 경로 사이에 공백 금지)
~/AIC/bin/isis -f$HOME/AIC/Config/isis.ini

# 창 1  ICS   ⚠️ 패키지를 담은 폴더에서 띄운다
cd ~/CEU/KMTNet-Camera-Electronics-Upgrade/ics_sim
python3 -m ics_sim -c ~/AIC/Config/ics_sim.ini --xis-host 127.0.0.1 --xis-port 6660

# 창 2  TC
~/AIC/bin/pctcs ~/AIC/Config/pctcs.ini

# 창 3  OBS   ← 마지막.  기동 중에 TC 와 ICS 둘 다에 접속한다
~/AIC/bin/obstool ~/AIC/Config/obstool.ini
```

**순서가 있다: XIS → ICS → TC → OBS.**  허브(XIS)가 먼저 서야 나머지가 등록할
수 있고, **OBS 는 기동 중에 TC 와 ICS 둘 다에 접속하므로 맨 뒤**다.

⚠️ **Python 쪽은 작업 디렉터리가 중요하다.**  패키지가 `ics_sim/ics_sim/` 구조라
`python3 -m ics_sim` 은 **패키지를 담고 있는 폴더**(`.../ics_sim`)에서 쳐야 한다 --
저장소 루트에서 치면 `No module named ics_sim` 이다.  실기는 `.../ics_archon` 에서
`python3 -m ics_archon -c ~/AIC/Config/ics_archon.ini`.

설정은 `-c` 가 절대경로라 어디서 띄우든 같은 것을 읽는다.  **다만 ini 안에
상대경로를 적으면 그때는 cwd 기준으로 풀리므로** 자료가 띄운 자리에 따라 다른 곳에
쌓인다 -- `data_dir` 등은 `~` 나 절대경로로 적을 것.

| 포트 | 누구 |
|---|---|
| 6660 | XIS 허브 |
| 6650 | OBSAgent |
| 6606 | TCSAgent |

⚠️ **`isis` 는 `-f` 와 경로 사이에 공백을 넣으면 안 된다.**  `main.c` 가
`sscanf(*argv,"f%s",...)` 로 읽어서 공백을 주면 죽는다.  그리고 대화형이
기본이라 TTY 가 필요하다 — `ssh` 로 띄울 거면 `tmux` 안에서.

⚠️ **6650 은 `ics_sim/tools/xis_probe.py` 도 쓴다.**  프로브가 떠 있으면 `obstool`
이 못 올라온다 — 띄우기 전에 끌 것.

기대하는 것:

- XIS 콘솔 `HOSTS` 에 `ICS`·`OBS`·`TC` 가 `127.0.0.1` 로 등록
- `OBS%` 프롬프트.  Redis/웹릴레이 접속 실패 경고는 **정상**이다(3회 연속 실패하면
  스스로 모니터링을 끈다)
- `TC%` 프롬프트와 `> Event Logging started successfully`.  Telcom/AUX 가 없으면
  두 링크는 `DOWN` — **정상**이다
- `OBS% status` → ICS 응답 · `OBS% kstatus` → `K.IC` 응답
- `watch -n 1 cat ~/AIC/Logs/ObsStatus.txt` — CamStatus 실시간(5초 주기)

---

## 기존 설치 이전

`~/AICS` 로 돌고 있던 기계를 `~/AIC` 로 옮길 때.  **폴더 이름만 바꾸면 안 된다** —
설정 파일과 실행 파일 **안에** 옛 경로가 들어 있다.

```bash
# 1) 전부 내린다
pkill -f 'bin/isis'; pkill -f obstool; pkill -f pctcs; pkill -f ics_sim

# 2) 폴더
mv ~/AICS ~/AIC

# 3) 설정 파일 안의 절대경로
grep -rl 'AICS' ~/AIC/Config/ 2>/dev/null | xargs -r sed -i 's|AICS|AIC|g'

# 4) 최신 코드
cd ~/CEU/KMTNet-Camera-Electronics-Upgrade
git fetch origin && git checkout ics-archon-v1.0-build && git pull

# 5) 생성물을 버리고 다시 빌드 (Config/ 는 건드리지 않는다)
rm -rf ~/AIC/build/ISISclient ~/AIC/build/OBSAgent ~/AIC/build/TCSAgent
bash ./ics_sim/xis/build-local.sh --build-dir ~/AIC/build/xis --prefix ~/AIC
bash ./OBSAgent/build-local.sh
bash ./TCSAgent/build-local.sh
```

⚠️ 4·5 단계의 `./...` 는 **저장소 체크아웃 기준**이다.  `~/AIC` 에서 치면
`No such file or directory` 가 난다.

> 5 단계의 빌드가 `~/AIC/bin/` 까지 갈아 끼운다 — 손으로 복사할 것이 없다.

그다음 **5. 확인**을 돌린다.

### 왜 이만큼 해야 하나

| 어디 | 무엇이 박혀 있나 |
|---|---|
| `Config/*.ini` | `build-local.sh` 가 로그·카탈로그 경로를 **절대경로로 펼쳐** 써 놓는다 (`isis.ini` `ServerLog` · `pctcs.ini` `LOGFILE`/`CATFILE` · `obstool.ini` `LOGFILE`) |
| `bin/obstool`·`bin/pctcs` | `TEMP_*LOGFILE` — **ini 를 읽기 전에 열려 설정으로 못 고친다.**  옛 판을 띄우면 로그 파일을 못 열고 시작한다 |
| `bin/isis` | `--prefix` 가 컴파일 상수(`CONFIG`/`LOGS`).  기동에서 `-f` 로 ini 를 명시하므로 당장 깨지지는 않지만 기본값이 죽은 경로를 가리킨다 |

⚠️ **`~/AIC/Config/*.expnum` 은 노출 번호 카운터다.**  `mv` 로 옮기면 따라오지만,
`Config/` 를 지우고 새로 만들면 **번호가 1 로 되돌아간다** — 2026-08-11 에
`FitsNum=00000000.000000` 로 실제로 겪었고 OBSAgent 파싱까지 깨졌다.  옮긴 뒤
`cat ~/AIC/Config/ics_sim.expnum` 으로 확인할 것.

> **이 판을 처음 적용할 때만 다시 빌드하면 된다.**  그 뒤로는 설치 자리를 또
> 옮겨도 재빌드가 필요 없다 — `TEMP_*LOGFILE` 이 `/tmp` 로 빠졌고
> `ObsStatus.txt` 는 ini 키 `OBSSTATFILE` 이 생겼다.

---

## 이상할 때

| 증상 | 원인·처방 |
|---|---|
| `Permission denied` | 실행 비트가 없다 → `bash ./OBSAgent/build-local.sh` 또는 `chmod +x` |
| `relocation R_X86_64_32 … can not be used when making a PIE object` | 낡은 `libisis.a` 를 물었다 → `rm -rf ~/AIC/build/ISISclient` 후 재빌드 |
| `Text file busy` | 돌고 있는 실행 파일에 `install` 했다 → 먼저 내릴 것 |
| `sed: no input files` | `grep` 이 아무것도 못 찾았다는 뜻이고 **무해하다**.  `xargs -r` 를 쓰면 안 뜬다 |
| `./ics_sim/... : No such file or directory` | 작업 디렉터리가 저장소가 아니다 → `cd ~/CEU/KMTNet-Camera-Electronics-Upgrade` |
| `No module named ics_sim` | 저장소 루트에서 쳤다 → `cd .../ics_sim` (패키지를 담은 폴더) |
| 로그가 안 써진다 | 바이너리에 옛 경로가 박힌 것 → **5. 확인** 의 `strings` 대조 |
| 노출 번호가 1 로 돌아갔다 | `Config/*.expnum` 을 잃었다 → 백업에서 되돌리고, 다시는 `Config/` 를 지우지 말 것 |
| `obstool` 이 안 뜬다 | 포트 6650 을 `xis_probe.py` 가 쥐고 있다 |

## 관련 문서

| 문서 | 무엇 |
|---|---|
| [README.md](README.md) | `ics_archon` 구성 · 배포본 놓기 · 설정 · **실기 첫 실행 5단계** |
| `ArchonGUI/QT_INSTALL.md` (브랜치 `archongui-analysis`) | **ArchonGUI**(STA Qt5 GUI) 빌드용 Qt5 설치 · `Unknown module(s)` 처방. ⚠️ 이 브랜치에는 없다 — `ics_archon` 과 무관해 따로 관리한다 |
| [SMC_CLAUDE.md](SMC_CLAUDE.md) | 인수인계 — 절대 깨뜨리면 안 되는 것 · 결정사항 · Archon 매뉴얼 확정 사실 |
| [`../OBSAgent/SMC_CLAUDE.md`](../OBSAgent/SMC_CLAUDE.md) · [`../TCSAgent/SMC_CLAUDE.md`](../TCSAgent/SMC_CLAUDE.md) | 각 에이전트 재빌드 걸림돌 · 경로 상수의 성질 |
| [`../ics_sim/xis/xis.md`](../ics_sim/xis/xis.md) | XIS 빌드 걸림돌 · 설정 파일 함정 3종 |
| [`../ics_sim/README.md`](../ics_sim/README.md) | `ics_sim` 실행 · 실물 연동 시험 |

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
mkdir -p ~/AIC/{src,bin,Config/acf,Logs,data,osc,log}
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
| `log/` | **텔레메트리 감시 기록**(`telemetry.<MK\|NT>.<YYYYMMDD>.csv`) | ⚠️ 아래 |
| `osc/` | 관측 스크립트(`.osc`) — 저장소에서 복사해 둔다 | ✅ 다시 복사하면 됨 |

⚠️ **`log/` 와 `Logs/` 는 다른 것이다** (대소문자만 다르다 — 리눅스에서는
갈리지만 눈으로는 안 갈린다).  `Logs/` 는 레거시 C 계통(obstool·XIS)의 자리이고
`log/` 는 `ics_archon` 의 텔레메트리 CSV 다.  **`data/` 밑에 두지 않은 것이
요구사항이다** — 자료와 함께 굴러가면 아카이브 정책에 걸린다 (운영자 확정
2026-08-27).  지워도 프로그램은 돌지만, **센서 표류를 되짚을 유일한 기록**이라
자료와 같은 기간 보존하는 편이 맞다.  자리는 `[archon] monitor_log` 로 옮길 수
있다.

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

### ⚠️ 벤치 네트워크 -- 광 링크가 안 섰다 (2026-08-24 실측, 2026-09-04 등재)

⛔ **실기에 붙기 전에 이것부터.**  `kmtnet-sso` 의 광 포트 둘이 **링크가 안 섰고**,
그 실측이 지금까지 **문서에 없었다**(당시 기록만 있고 등재 안 됨).

| 인터페이스 | 종류 | 실측 |
|---|---|---|
| `eno16795` | RJ45 | **carrier=1 -- SSH·인터넷 경로**(`100.51.1.22`).  ⛔ **건드리지 말 것** |
| `eno16805`/`16815`/`16825` | RJ45 | 미사용 |
| **`eno17395np0`** | SFP+ (Dell WTRD1) | LC · 850nm(SR 멀티모드) · Tx **−2.25 dBm 정상** · Rx **−4.51 dBm 정상 수신 중** · **carrier=0** |
| **`eno17405np1`** | SFP+ (Dell WTRD1) | Tx·Rx 모두 **−40.00 dBm**, low alarm On → **자기 레이저가 꺼져 있다** |

⭐⭐ **원인 단서 -- 속도가 안 맞는다.**  Archon 매뉴얼 p.9 는
*"via a **gigabit** Ethernet connection (either copper or fiber)"* 라고 적는다 --
**Archon 은 1 Gbps 전용**인데 호스트 모듈은 **10G SFP+** 다.  SFP+ 는 구리처럼
자동협상을 하지 않으므로 **파장이 같아도(850nm) 링크가 서지 않는다.**
⚠️ `np0` 의 Rx 가 건강한 것은 **상대→우리** 가닥만 증명한다 -- 우리 레이저가 켜진
것은 **우리→상대** 가닥의 증거가 못 된다(모듈 출구에서 잰 값이다).

**해결안 (2026-08-24 제시, ⏳ 운영자 판단 대기)**

| 안 | 무엇 |
|---|---|
| A | 호스트 모듈을 **1000BASE-SX 1G SFP** 로 교체 |
| B | **기가비트 스위치** 경유 |
| C | **Archon Rev H 의 구리 기가비트 포트**로 직결 (호스트 남는 RJ45 3개 활용) |
| D | `np1` 모듈 불량 여부를 두 모듈 **서로 바꿔 꽂아** 먼저 가른다 |

### ✅ 해결됐다 -- 스위치 포트를 고정 1G 로 (운영자 2026-09-04)

⭐ **광 스위치허브의 포트별 auto-negotiation 을 해제하고 고정 1 G 로 설정해서
해결했다.**  위 진단(Archon 은 1 Gbps 전용 · SFP+ 는 자동협상을 안 한다)이 맞았고,
해결안 **B(기가비트 스위치 경유)** 를 택한 뒤 **협상을 끄고 속도를 못박은 것**이
마지막 한 걸음이었다.  그래서 09-01~02 실기 시험이 `10.0.0.101`·`10.0.0.113` 에
붙었다.

⭐ **왜 이 해결이 듣는가 -- 갈래가 둘이다** (운영자 2026-09-04)

1. **속도** -- Archon 은 1 Gbps 전용이고 SFP+ 는 구리처럼 자동협상을 하지 않는다.
2. ⭐ **모듈 호환성** -- **auto-negotiation 은 제조사별 SFP 모듈 호환성과도
   걸린다.**  운영자 경험: *"어떤 제조사 것은 되고 어떤 제조사 것은 안 되는 경우가
   있었는데, auto-negotiation 을 해제하고 1 G 로 고정하니 되는 경우가 있었다."*
   ⚠️ 그러니 **모듈을 바꿨을 때 잘 되던 링크가 깨질 수 있고, 처방은 같다** --
   협상을 끄고 속도를 못박는다.  (참고: 카드가 서드파티 SFP 를 거부하는 계통도
   있다 -- Intel 계열은 `dmesg` 에 `unsupported SFP+ module` 을 남기고
   `allow_unsupported_sfp=1` 로 푼다.  우리 카드는 Broadcom `bnxt_en` 이고 모듈은
   **Dell WTRD1** 이다.)

⭐ **그래서 진단 순서가 이것이다** -- 링크가 안 서면 **① 스위치 포트 설정(협상·속도)
② 모듈 제조사·조합 ③ 케이블(Tx/Rx 가닥)** 순으로 본다.  모듈·케이블부터 보면
헛돈다.

#### ⚠️ IT 관리자에게 넘길 것 (이 설정을 아는 사람이 있어야 한다)

| 항목 | 내용 |
|---|---|
| 스위치 포트 | **auto-negotiation 해제 + 고정 1 G** -- 광 스위치허브의 **포트별** 설정이다.  ⛔ **스위치를 교체하거나 포트를 옮기면 따라오지 않는다** |
| 모듈 교체 시 | 제조사가 바뀌면 **되던 링크가 깨질 수 있다** -- 같은 처방(협상 해제·속도 고정)을 새 포트에도 적용 |
| 호스트 주소 | `np0` **10.0.0.201/24** · `np1` **10.0.0.202/24**, GW·DNS 없음.  ⛔ 관리 NIC(`eno16795`, SSH 경로)는 건드리지 않는다 |
| ARP | 두 광포트만 `arp_ignore=1`·`arp_announce=2` (같은 `/24` 를 두 NIC 에 나눠 주므로 필수) |
| ⏳ **`np1` 모듈** | Tx·Rx 모두 **−40.00 dBm**, low alarm On = **자기 레이저가 꺼져 있다.**  조치(재삽입 · 두 모듈 교차 확인 · 교체)는 **이행 기록이 없다** -- guide 유닛을 그 포트에 붙일 거라면 **먼저 가를 것** |

**호스트 주소 배정 (2026-08-24 확정)**

| 자리 | 값 |
|---|---|
| `eno17395np0` | **10.0.0.201/24** |
| `eno17405np1` | **10.0.0.202/24** |
| 게이트웨이 · DNS | **설정하지 않는다** |
| 유닛 가용 범위 | **10.0.0.2 ~ 10.0.0.254** (`.201`·`.202` 제외.  ⚠️ `.255` 는 브로드캐스트) |

- 영구 설정은 **새 파일 `/etc/netplan/90-archon-fiber.yaml` 로만** 쓴다 --
  ⛔ 기존 netplan 파일(SSH 경로)은 손대지 않는다.  `optional: true` 를 넣는다
  (링크가 없으면 부팅이 2분 늦어진다).
- ⚠️ **두 NIC 에 같은 `/24` 를 나눠 주므로 ARP flux 방어가 필수**다 --
  `/etc/sysctl.d/90-archon-arp.conf` 에 **두 광포트만** `arp_ignore=1` ·
  `arp_announce=2` (관리 NIC 는 손대지 않는다).  종전에 브리지(`br0`)로 묶었다가
  "어느 포트에 뭐가 붙었나" 를 잃어서 **포트별 배정으로 되돌렸다.**
- ⚠️ **유닛 IP 는 "100 + 유닛번호" 체계**로 보인다 -- 지금 붙은 것이
  **`10.0.0.113`**(KMTK-SCI-113)이고 guide 는 `.162`(GUI-162)다.  실험실 규약
  `AC13A = 10.0.0.13` 과 다르므로 `ics_archon.ini` 주석의 `.13` 예시를 현장 값으로
  읽을 것.
- MTU 는 **1500** 이다.  점보프레임을 쓸 계획이면 NIC·스위치·컨트롤러를 **다** 맞춰야 한다.

### 포트 배정표

| 포트 | 누구 | 근거 |
|---|---|---|
| **6600** | **ICS** (`ics_archon` · `ics_sim`) | 레거시 IC 계열 표준 포트 |
| **6601** | **ICG** (`icg_archon`) | ⭐ **신규 배정 (2026-09-03)** — 아래 주의 |
| 6660 | XIS 허브 | 레거시 (`isis.ini` `ServerPort`) |
| 6650 | OBSAgent | 레거시 |
| 6606 | TCSAgent | 레거시 |

⚠️ **ICG 포트를 6600 으로 되돌리지 말 것.**  레거시는 IC 계열과 `ICG` 가 **다
6600** 이고 **호스트로** 갈랐다(`ICG` 는 Guide server `.108`, ICS·XIS 는 Science
server `.109`).  신규는 한 호스트에 둘을 올리는 배치가 실재하므로 포트로 가른다 —
`ics_sim` 기본값도 6600 이라 **비워 두면 같은 값으로 떨어진다**(뒤에 뜨는 쪽이
bind 실패).  `icg_archon` 기동 검사가 그 경우를 알린다.

> 같은 호스트에 포트를 둘 두는 것 자체는 레거시 관례이기도 하다 — 허브
> `isis.ini` 의 preset 에 `.108` 이 **6600**(ICG)·**6606**(TC) 두 줄로 있다.

⚠️ **허브 쪽 배치도 함께 고쳐야 한다** — XIS `isis.ini` 의
`UDPPort <ip> 6600` preset 이 ICG 호스트를 6600 으로 가리키면 **기동 핑이 새
포트에 안 닿는다.**  치명적이지는 않다(우리 `register()` 의 PING 으로 동적
등록은 된다) 하지만 허브가 "기동에 전원을 핑한다" 는 성질을 잃는다.
⛔ 저장소의 `ics_sim/xis/install/config/*/isis.ini` 는 **레거시 운영 설정의
보관본**이므로 고치지 말 것 — 신규 배치용 설정은 별개다.

> 레거시에는 CB 계열 **10601** 도 있었다 (`G.CB` 등).  신규는 `*.CB` 를 프로그램
> 안으로 흡수했으므로 그 포트는 쓰지 않는다.

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
| `ArchonGUI/QT_INSTALL.md` (브랜치 `archongui-study`) | **ArchonGUI**(STA Qt5 GUI) 빌드용 Qt5 설치 · `Unknown module(s)` 처방. ⚠️ 이 브랜치에는 없다 — `ics_archon` 과 무관해 따로 관리한다 |
| [SMC_CLAUDE.md](SMC_CLAUDE.md) | 인수인계 — 절대 깨뜨리면 안 되는 것 · 결정사항 · Archon 매뉴얼 확정 사실 |
| [`../OBSAgent/SMC_CLAUDE.md`](../OBSAgent/SMC_CLAUDE.md) · [`../TCSAgent/SMC_CLAUDE.md`](../TCSAgent/SMC_CLAUDE.md) | 각 에이전트 재빌드 걸림돌 · 경로 상수의 성질 |
| [`../ics_sim/xis/xis.md`](../ics_sim/xis/xis.md) | XIS 빌드 걸림돌 · 설정 파일 함정 3종 |
| [`../ics_sim/README.md`](../ics_sim/README.md) | `ics_sim` 실행 · 실물 연동 시험 |

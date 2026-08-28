# gmon v2 — KMTNet 가이드 카메라 시상(FWHM) 모니터

KMTNet 카메라 전자부 업그레이드(CEU)에 맞춘 가이드 카메라 시상 모니터링 시스템.
STA Archon 컨트롤러 1대 + CCD47-20 가이드 CCD 4칩(N, S, E, W) 구성용이며,
2018년 레거시(`old/`, wish/Perl/IRAF 기반)를 Python으로 재작성한 것이다.

모든 파일명 규약·CLI·설정 키·데이터 형식의 **원 계약은 [DESIGN.md](DESIGN.md)** 이다.
이 README와 DESIGN.md가 다르면 DESIGN.md가 우선한다.

---

## 1. 개요

- 신규 아콘 컨트롤러는 4칩 × 2채널 = **8채널을 한 장의 FITS(4224×1033, uint16)** 로 저장한다.
  (레거시 ICS는 칩별 `KMTNg{n,e,w,s}.<ts>.<seq>.fits` 4장을 만들어 주었음 — 분할 단계가 새로 필요.)
- 처리 흐름:

  1. **gwatch** — 수신 디렉토리(`run/incoming/`)에 새 원시 프레임이 들어오면 감지
  2. **gsplit** — 단일 4224×1033 프레임을 칩별(N/S/E/W) 1024×1024 FITS 4장으로 분할
     (채널 스티칭 + 페데스탈 단차 보정)
  3. **gpsf** — 칩별 SExtractor → PSFEx 실행, PSF FWHM(픽셀→arcsec) 추출,
     `run/data/fwYYMMDD.dat`·`run/log/logfile.txt`에 기록, 결과 JSON 생성
  4. **gsnap** — 3×3 나침반 배치 PSF 스냅샷 PNG 생성 (ds9/XPA 우선, matplotlib 폴백)
  5. **gplot** — gnuplot으로 밤새 FWHM·온도·초점 실시간 그래프
  6. **gmon(GUI)** — 위 전체의 시작/정지 + **온도 기반 초점 보정**
     (`ref = slope*T − (base + dfocus)`)을 TCS로 전송 (AUTO/MAN, dry-run 안전장치)

## 2. 아키텍처

```
                       ┌───────────────────────────────┐
                       │   gmon.py  (Tkinter GUI 관제탑) │
                       │  ON/OFF · AUTO/MAN · dfocus ± │
                       └────┬───────────┬──────────────┘
        시작·정지 (pidfile+SIGTERM)      │ FocusController: ref = slope*T-(base+dfocus)
             │                          │ UDP "abc>tc fttgoto <ref>"  (dry_run=yes면 로그만)
     ┌───────┴────────┐                 ▼
     ▼                ▼            TCS/ICS (192.168.13.109:6660)
 gwatch.py        gplot.py
 (감시 데몬)      (gnuplot 그래프) ◄──── run/data/fwYYMMDD.dat
     │
     │ run/incoming/*.fits  (새 파일, mtime 안정화 대기)
     ▼
 gsplit.py ──► run/work/KMTNg{n,s,e,w}.<stem>.fits   (4칩 분할, 페데스탈 보정)
     ▼
 gpsf.py   ──► sex → psfex → FWHM
     │         ├─ run/data/fwYYMMDD.dat        (append, gplot 입력)
     │         ├─ run/log/logfile.txt          (상세 로그 + fwAVG)
     │         └─ run/work/result.<stem>.json  (gsnap 전달용)
     ▼
 gsnap.py  ──► run/snap/psf.snap.<stem>.png    (3×3 스냅샷; ds9/XPA 우선, mpl 폴백)
```

런타임 산출물 루트는 `[paths] runroot`(기본 `gmon/run/`, git 미추적):

| 디렉토리         | 내용                                       |
|------------------|--------------------------------------------|
| `run/incoming/`  | 원시 프레임 수신 (gwatch 감시 대상)        |
| `run/processed/` | 처리 완료된 원본 보관 (`delete_raw=no` 시) |
| `run/failed/`    | 파이프라인 실패 노출 원본 보존 (`delete_raw`와 무관하게 삭제 안 함; incoming으로 되돌리면 재처리) |
| `run/work/`      | 분할 FITS·카탈로그·PSF·result JSON         |
| `run/snap/`      | 스냅샷 PNG                                 |
| `run/data/`      | `fwYYMMDD.dat` (밤 단위)                   |
| `run/log/`       | `logfile.txt` + 프로세스별 `<name>.log`    |
| `run/pid/`       | `<name>.pid` (단일 실행 보장)              |

## 3. 레거시(old/) → v2 대응표

| 레거시 (2018)              | 역할                                     | v2 후속                              |
|----------------------------|------------------------------------------|--------------------------------------|
| `old/gmon` (wish GUI)      | ON/OFF·AUTO/MAN·dfocus±·초점 UDP 전송    | `gmon.py` (Tkinter GUI)              |
| `old/do-Monitoring` (Perl) | 노출 루프·셔터 확인·파일 이동            | `gwatch.py` (수신 디렉토리 감시)     |
| (없음)                     | —                                        | `gsplit.py` (**신규**: 단일 FITS 분할) |
| `old/do-sex.psfex` (Perl)  | sex→psfex→FWHM 기록→ds9 스냅샷           | `gpsf.py` + `gsnap.py`               |
| `old/do-plotFWHM` (Perl)   | gnuplot 실시간 그래프                    | `gplot.py`                           |
| `old/do-killPlot`          | `killall`로 일괄 종료                    | `gmon.py` OFF (pidfile 기반 SIGTERM) |
| `old/gmon.cfg`             | dfocus 영속                              | `run/dfocus.txt`                     |
| (SAAO `run/tcon`, `nc -u`) | TCS 서버 질의(auxstatus)·fttgoto·dtilt   | `gtcs.py` (질의/이동 클라이언트 + CLI) |
| `old/default.sex` 등       | sex/psfex 설정                           | `config/` (default.sex 등 5종)       |

### 주요 개선

- **단일 FITS 분할 신설**(`gsplit.py`): 8채널 프레임 → 칩별 4장. 채널별 바이어스
  페데스탈 단차 보정(`pedestal_match`), 지오메트리 전부 `gmon.conf`로 설정 가능.
- **fwAVG 버그 수정**: 레거시 `do-sex.psfex`는 평균 계산에서 W를 2회 더하고 S를
  누락했다(`(N+E+W+W)/4`). 또한 4칩이 모두 유효할 때만 값을 냈다.
  v2는 **유효한 칩들만의 산술평균**(DESIGN §5.5).
- **IRAF/gethead 의존 제거**: 헤더 읽기·배경 stddev를 astropy/numpy로 대체
  (레거시는 `gethead` + IRAF `x_images.e imstatistics`).
- **`ps | grep` → pidfile**: 중복 실행 방지를 `run/pid/<name>.pid`로 일원화,
  종료도 `killall` 대신 pidfile 대상 SIGTERM (다른 프로세스 오폭 방지).
- **하드코딩 상수 → gmon.conf**: 픽셀 스케일 0.52, 초점 기울기 −0.067, 안전범위,
  ds9 회전각, stddev 측정 영역 등 전부 설정 키로 이동 (DESIGN §4).
- **dry_run 안전장치**: `[ics] dry_run=yes`(기본)면 TCS/ICS로 실제 UDP를 보내지
  않고 로그만 남긴다. 커미셔닝 확인 후 해제.
- **원본 무단 삭제 제거**: 레거시는 처리 전 `rm -rf *.fits`를 수행했다. v2 기본은
  `delete_raw=no` — 처리 후 원본을 `run/processed/`로 이동·보존.
  파이프라인이 실패한 노출의 원본은 `delete_raw=yes`여도 삭제하지 않고
  `run/failed/`로 보존 이동하며 재처리 기록(`processed.list`)에도 남기지 않는다
  — 장애(예: sex 미설치, 디스크 풀) 해소 후 `run/incoming/`으로 되돌리면 재처리.
- 스냅샷 PNG(`run/snap/psf.snap.<stem>.png`)가 이미 있으면 해당 노출 재처리 생략
  (레거시 파리티 유지).

## 4. 요구사항·설치

| 구성요소     | 요구                          | 비고                                        |
|--------------|-------------------------------|---------------------------------------------|
| Python       | 3.9+                          | numpy, astropy 필수 / matplotlib (스냅샷 폴백) |
| SExtractor   | 2.x (`sex`)                   | 소스 검출·카탈로그                          |
| PSFEx        | 3.x (`psfex`)                 | PSF 모형·FWHM                               |
| gnuplot      | qt/x11/pngcairo 터미널 중 하나 | FWHM 그래프                                 |
| ds9 + xpaset | 선택                          | 없으면 스냅샷이 matplotlib 폴백으로 동작 (ds9가 안 떠 있으면 gsnap이 `[paths] ds9`로 기동 시도 — 레거시 파리티) |

- 개발·시험 Mac 예: python `/opt/miniconda3/bin/python`(astropy 7.2, numpy 2.4,
  matplotlib 3.10), sex `/opt/homebrew/bin/sex`(v2.28), psfex `/opt/local/bin/psfex`(v3.24),
  gnuplot 6.0. xpaset 없음 → mpl 폴백 경로로 시험.
- 별도 설치 절차 없음: 이 디렉토리를 그대로 두고 쓰면 된다. 외부 도구가 PATH에
  없으면 `gmon.conf [paths]`에 절대경로를 적는다 (`python`, `sex`, `psfex`,
  `gnuplot`, `ds9`, `xpaset`).
- 사이트 이관 시 확인: `[site] night_offset_hours`(밤 파일명 계산),
  `[ics] host/port`, `[watch] pattern`.
- sex/psfex 설정 파일은 `config/`에 있으며 `gpsf.py`가 자동 참조한다
  (`default.sex`, `default.param.psfex`, `default.psfex`, `default.conv`, `default.nnw`).

## 5. 빠른 시작

### 5.1 합성 프레임으로 전 체인 데모 (하드웨어 불필요)

```sh
cd gmon
PY=/opt/miniconda3/bin/python

# 1) 합성 원시 프레임 생성 (4224x1033, 별 40개, FWHM 3.5px)
$PY tools/make_synthetic.py -o synth.20260829.101530.fits --fwhm-px 3.5 --nstars 40

# 1') 또는 실제 아콘 프레임 위에 별 주입 (--base; 헤더·페데스탈은 실프레임 것 유지)
#     예: raw/modtm.20260527.214204.sim.fits 가 이렇게 만든 시험 영상
$PY tools/make_synthetic.py -o modtm.20260527.214204.sim.fits \
    --base ../raw/modtm.20260527.214204.fits --fwhm-px 3.8 --nstars 60 \
    --seed 214204 --truth modtm.20260527.214204.sim.truth.json

# 2) 수신 디렉토리에 투입 (run/ 하위는 도구가 자동 생성)
mkdir -p run/incoming
mv synth.20260829.101530.fits run/incoming/

# 3) 감시 루프 1회 실행: gsplit → gpsf → gsnap 자동 수행
$PY gwatch.py --once

# 4) 결과 확인
ls run/work/KMTNg*.20260829.101530.fits      # 분할 FITS 4장 (n/s/e/w)
cat run/work/result.20260829.101530.json     # 칩별 fwhm_px/fwhm_as/sd, fwavg_as
open run/snap/psf.snap.20260829.101530.png   # 3x3 스냅샷 (Linux: xdg-open)
cat run/data/fw*.dat                         # fw 데이터 (한 줄 추가됨)

# 5) 그래프 1회 렌더 (창 없이 PNG로)
$PY gplot.py --oneshot --term png --out fwplot.png
```

원시 샘플이 있으면 같은 방식으로 `raw/modtm.*.fits`를 `run/incoming/`에 복사해
시험할 수 있다 (일부 샘플은 파일 끝이 잘려 있어 astropy 경고가 나오지만 처리된다).

각 단계를 따로 돌릴 수도 있다:

```sh
$PY gsplit.py run/incoming/modtm.20260527.195724.fits --json   # 분할만
$PY gpsf.py 20260527.195724                                    # sex+psfex+기록
$PY gsnap.py run/work/result.20260527.195724.json --backend mpl
```

### 5.2 실전 운용 (야간 관측)

```sh
cd gmon
/opt/miniconda3/bin/python gmon.py
```

GUI는 **독립 창 3개**로 구성된다:
- **제어부** (메인 창) — 레거시 배치 버튼 + 상태 라벨 + SNAP/PLOT 버튼
- **PSF 스냅샷** (별도 창) — 최신 `psf.snap.*.png` 3초 주기 자동 갱신
- **FWHM 그래프** (별도 창) — `refresh_sec` 주기로 gplot을 PNG 렌더해 표시

서브 창은 닫아도 숨김일 뿐이며 제어부의 **SNAP**/**PLOT** 버튼으로 다시 연다.
제어부 창을 닫으면 GUI 전체가 종료된다(데몬은 유지). GUI가 떠 있는 동안
gwatch는 외부 gnuplot 라이브 창을 띄우지 않으며(그래프는 전용 창으로 표시),
GUI는 중복 실행되지 않는다(`run/pid/gmon.pid`). GUI 없이 headless로 돌리면
기존처럼 외부 gnuplot 라이브 창이 뜬다.

1. **ON** — gwatch(감시 데몬)와 gplot(그래프)을 기동. ICS가 저장한 프레임이
   `run/incoming/`에 도착할 때마다 자동으로 분할→FWHM→스냅샷→그래프 갱신.
2. **AUTO** — `period_sec`(기본 120초) 주기로 최신 온도(T)에서
   `ref = slope*T − (base + dfocus)`를 계산해 TCS로 전송(`gtcs` 경유
   `abc>tc fttgoto <ref>`). 안전범위 `[safe_min, safe_max]` 밖이거나 직전
   주기 계산값 대비 `|Δ| ≥ max_jump`이면 그 주기는 보류. 비교 기준은 전송
   여부와 무관하게 매 주기 갱신되므로(레거시 `dref` 동일) 점프가 지속돼도
   다음 주기에는 전송이 재개된다.
   온도 출처는 `[focus] temp_source`: 기본 `auto` = 오늘 밤 fw파일의
   TEMP(=ENS3, 운용판 파리티) 우선, fw가 없거나 `fw_stale_sec`(기본 900초)보다
   오래되면 **TCS `auxstatus`의 `ENS<temp_sensor>`로 폴백** — 밤 시작 등
   관측 전에도 초점 보정이 동작한다. 제어부 하단 TCS 라벨에 서버에서 읽은
   온도·현재 초점(FAFOCUS)·틸트·셔터 상태가 `status_sec` 주기로 표시된다.
3. **MAN** — 현재 ref를 1회 즉시 전송 (안전범위만 검사).
4. **±step / ±big_step** — dfocus를 `step`(기본 0.005) 또는 `big_step`(기본
   0.5, 운용판 2021-01 "big adjust") 단위로 조정. `run/dfocus.txt`에 영속되어
   재시작 후에도 유지.
5. **OFF** — pidfile 기반 SIGTERM으로 gwatch/gplot 정지 (`killall` 안 씀).

초점 명령이 실제로 나가려면 `gmon.conf`에서 `[ics] dry_run = no`로 바꿔야 한다.
기본값 `yes`에서는 전송할 명령을 로그에만 남긴다.

## 6. 각 도구 CLI 요약 (DESIGN §6)

모든 도구는 `-c/--config <gmon.conf>`를 지원하며, 기본은 스크립트 옆 `gmon.conf`.

```
gsplit.py  RAW.fits [-o OUTDIR] [--json]     → 4파일 생성, stdout에 경로/JSON
gpsf.py    STEM 또는 --raw RAW.fits [--workdir D]  → sex+psfex+기록, result JSON 출력
gsnap.py   result.<stem>.json [--backend auto|ds9|mpl]  → PNG 생성
gplot.py   [--oneshot] [--term qt|x11|png] [--out FILE] [--datafile F]  → 그래프
gtcs.py    auxstatus | fttgoto FOC [TNS TEW] | dtilt DNS DEW | raw CMD  → TCS 질의/이동
gwatch.py  [--once] [--foreground]           → 감시 루프 (pidfile 단일 실행)
gmon.py                                       → GUI (내부에서 gwatch/gplot 기동·정지)
tools/make_synthetic.py -o OUT.fits [--fwhm-px 3.5] [--nstars 40] [--truth J.json]
                        [--fwhm-scatter 0.1] [--base RAW.fits] [--extra-noise ADU]
                        (base=실프레임 별 주입, fwhm-scatter=별별 FWHM 산포 비율)
```

- 종료코드: 성공 0, 부분 실패(일부 칩) 2, 완전 실패 1.
- 단일 실행 보장: `run/pid/<name>.pid` (`ps|grep` 사용 금지).
- 모든 실행 로그: `run/log/<name>.log` (stdout에도 출력).

## 7. 데이터 형식

### 7.1 분할 산출물 (gsplit, DESIGN §5.1)

- 파일명: `<prefix><p>.<stem>.fits`, p ∈ {n, s, e, w}, prefix 기본 `KMTNg`.
- stem 규칙: 원본 basename에서 `.fits` 제거 후, **첫 토큰이 숫자로 시작하지 않으면
  첫 토큰 제거** (결과가 비면 전체 유지).
  예: `modtm.20260527.195724.fits` → stem `20260527.195724`
  → `KMTNgn.20260527.195724.fits`.
- float32, BZERO 없음. 크기 기본 1024×1024
  (= (raw_ny − y_trim_bottom − y_trim_top) × (left_active폭 + right_active폭)).
- 헤더: 원본 전체 전파 + 추가 키

  | 키         | 의미                                  |
  |------------|---------------------------------------|
  | `GCHIP`    | 칩 방위 (n/s/e/w)                     |
  | `GSEG1`, `GSEG2` | 사용한 세그먼트 인덱스 (0–7)    |
  | `GGEOMVER` | 지오메트리 버전 (`GMON-GEOM-v1`)      |
  | `GPED1`, `GPED2` | 채널별 적용 페데스탈 오프셋(ADU) |
  | `GRAWFILE` | 원본 파일명                           |

### 7.2 fw 데이터 파일 (gpsf가 append, DESIGN §5.2)

- 경로: `run/data/fw%y%m%d.dat` — 밤 = localtime + `night_offset_hours`(기본 −8h).
- 한 줄 (공백 구분, **운용판(2026-03 SAAO) do-plotFWHM 호환** — 2018-11-30 개정 형식):

  ```
  YY:MM:DD:HH:MM:SS  fwN  fwE  fwW  fwS  FOCUS  TEMP  SECZ
  ```

  | 열 | 값                        | 비고                                       |
  |----|---------------------------|--------------------------------------------|
  | 1  | `YY:MM:DD:HH:MM:SS`       | 관측시각 로컬 기준 (DATE-OBS/TIME-OBS 우선, 없으면 처리 시각) |
  | 2–5| fwN fwE fwW fwS (arcsec)  | 소수 2자리, 실패 칩은 0.00                 |
  | 6  | FOCUS                     | 헤더에서, 결측("___")이면 직전 줄 값 계승  |
  | 7  | TEMP                      | 헤더에서, 결측이면 직전 줄 값 계승 (초점 보정 T 입력) |
  | 8  | SECZ                      | 헤더에서, 없으면 0.0                       |

  실제 예 (v2 생성):

  ```
  26:08:29:03:10:29 2.11 2.11 2.10 2.10 -6.798 6.6 1.27
  ```

  구형 파일(2018판 `DD:HH:MM:SS`, 예: `old/fw181022.dat`)도 gplot이 1열의
  콜론 수로 자동 판별해 그대로 그린다.

### 7.3 결과 사이드카 JSON: `run/work/result.<stem>.json` (DESIGN §5.4)

gpsf → gsnap 전달용. 키:

```
stem
chips { n|s|e|w : { fwhm_px, fwhm_as, sd, psf_file, snap_file, ok } }
fwavg_as            ← 유효(ok) 칩들의 산술평균
header { SECZ, FOCUS, TILTEW, TILTNS, ESW, T123, ALT, AZ, DATEOBS, TIMEOBS }
raw_file
```

헤더 키가 원본에 없으면 값은 `"___"` (레거시 gethead 관례).

### 7.4 기타

- 상세 로그 `run/log/logfile.txt`: 레거시 형식 유지 + fwAVG 필드 추가 (DESIGN §5.3).
- 스냅샷 `run/snap/psf.snap.<stem>.png`: **기준 화면
  `old/psf.snap.20181003T011100.0001.fits.png`과 동일 구성** — 3×3 나침반
  배치(중앙=정보 패널, 상=N, 좌=E, 우=W, 하=S, 각 ~200px, 전체 ~600×649),
  각 PSF 타일은 ds9 `zoom 16` 파리티로 중앙 ~13픽셀만 확대, 위 `sdX=` /
  아래 `fwX=` 빨간 라벨 + 초록 등고선, 중앙 패널에 노출 id·SecZ·Focus·
  TiltEW/NS·ESW·T123·ALT/AZ(빨강)와 fwAVG(초록), 하단에 그레이 컬러바
  스트립(눈금 수치). 이 파일이 존재하면 해당 노출은 재처리하지 않는다.
- 그래프(gplot): 기준 화면 `old/kmtnet_saao_fw.png` 표기 파리티 — 좌상단
  파란 UTC 타임스탬프, `<사이트> FFT (FWHM-FOCUS-TEMP) Monitoring` 제목,
  범례 dT/North/East/West/South/Airmass/Estimate/Focus, y2 Focus(mm)
  −8.0~−5.0 (0.5 간격), 마지막 점의 파란 `g=… F=…` 라벨.

## 8. 커미셔닝 체크리스트 (DESIGN §10 확장)

현장(하늘·실기기)에서 확정한 뒤 `gmon.conf`를 갱신해야 하는 항목들.

1. **추가 9행의 위치(상/하)와 채널당 16컬럼(528−512)의 성격**
   - 확인: 바이어스/다크 프레임을 여러 장 받아 원시 프레임의 맨 위/맨 아래 행별
     중앙값 프로파일을 비교한다 — 더미/오버스캔 행이 위인지 아래인지, 각 세그먼트의
     왼쪽 16컬럼이 프리스캔(레벨만 있음)인지 실픽셀인지 본다. 분할 결과
     `KMTNg*.fits`에 별상이 잘리거나 더미띠가 남으면 즉시 드러난다.
   - 갱신 키: `[geometry] y_trim_bottom`, `y_trim_top`, `left_active`, `right_active`.
2. **칩↔방위 매핑과 ds9 회전각**
   - 확인: 하늘에서 망원경을 북/동으로 소량 이동시키며 각 칩에서 별이 움직이는
     방향을 본다. 스냅샷의 N/E/W/S 타일 배치가 실제 방위와 일치하는지 확인.
   - 갱신 키: `[chips] order` (세그먼트쌍→방위), `[display] rot_n/rot_e/rot_w/rot_s`.
3. **픽셀 스케일 (현 0.52″/px 가정)**
   - 확인: 분리각을 아는 별쌍 또는 astrometry.net 해로 분할 FITS의 실측 스케일을
     구한다. fw 값(arcsec)이 DIMM 등 독립 시상계와 계통 차이가 나면 이 값을 의심.
   - 갱신 키: `[pipeline] pixel_scale`.
4. **채널 반전 여부(현 direct)와 GAIN/SATUR_LEVEL(현 16비트 65535)**
   - 확인: 접합부(칩 중앙 세로선)를 가로지르는 별이 매끄럽게 이어지는지 본다.
     어긋나면 반전 필요. 포화 별의 피크 ADU로 SATUR_LEVEL, 플랫 2장 분산법으로
     GAIN을 확인한다.
   - 갱신: `[geometry] flip_right_x`, (필요 시) `[geometry] pedestal_match`;
     GAIN/SATUR_LEVEL은 `config/default.sex`.
5. **신규 ICS의 파일 저장 경로·파일명 규약**
   - 확인: ICS가 실제로 쓰는 저장 디렉토리와 파일명(예: `modtm.<날짜>.<시각>.fits`
     형태 유지 여부)을 확인. stem 규칙(§7.1)이 새 파일명에서 올바른
     `날짜.시각`을 뽑는지 `gsplit.py <파일> --json`으로 점검.
   - 갱신 키: `[watch] pattern`, `[paths] runroot`(수신 위치가 다르면 링크/마운트
     구성), 필요 시 `[watch] poll_sec`, `settle_sec`.
6. **TCS 초점 명령(`tc fttgoto`) 규약 유지 여부 → dry_run 해제**
   - 확인: `dry_run=yes` 상태로 AUTO를 돌려 `run/log/`의 로그에 찍히는
     `abc>tc fttgoto <ref>` 값이 합리적인지(안전범위, max_jump 동작 포함) 며칠
     검증한 뒤, TCS 측과 명령 규약·호스트/포트를 재확인하고 해제한다.
   - 갱신 키: `[ics] dry_run`(→ `no`), `host`, `port`;
     초점 모델은 `[focus] slope/base/safe_min/safe_max/max_jump/period_sec`.

보조 항목: 그래프 초점축 범위 `[plot] y2_range`는 계절에 따라 재조정
(레거시도 연 2회 수정했음), 사이트 시간대에 맞는 `[site] night_offset_hours` 확인.

## 9. 시험

pytest 불필요 — 각 `tests/test_*.py`는 단독 실행되는 assert 스크립트다
(실패 시 비0 종료, 성공 시 마지막 줄에 `OK <이름>` 출력).

```sh
# 전체 실행 (기본 인터프리터: /opt/miniconda3/bin/python, PY로 변경 가능)
sh tests/run_tests.sh
PY=/usr/bin/python3 sh tests/run_tests.sh

# 개별 실행
/opt/miniconda3/bin/python tests/test_split.py     # 분할 지오메트리·stem·헤더 키
/opt/miniconda3/bin/python tests/test_pipeline.py  # 합성 프레임 전 체인 (sex/psfex 필요)
/opt/miniconda3/bin/python tests/test_plot.py      # gplot --oneshot PNG + 라이브 모드 생존 (old/fw181022.dat 활용)
/opt/miniconda3/bin/python tests/test_focus.py     # FocusController (안전범위·max_jump·dry_run)
/opt/miniconda3/bin/python tests/test_watch.py     # gwatch 원본 정리 (실패→failed/ 보존, 스킵→processed/·삭제)
```

시험은 `run/`을 건드리지 않고 각자 임시 디렉토리를 사용한다.

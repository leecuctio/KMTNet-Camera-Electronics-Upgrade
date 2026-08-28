# gmon v2 — Archon 가이드 카메라 시상 모니터 설계서

작성: 2026-08-29 · 대상: KMTNet CEU 가이드 카메라 (STA Archon 1대 + CCD47-20 × 4)

이 문서는 모든 컴포넌트가 따라야 하는 **계약(contract)** 이다. 구현 시 이 문서의
파일명 규약·CLI 인터페이스·설정 키·데이터 형식을 변경하지 않는다.

## 1. 배경

레거시 시스템(`gmon/old/`)은 ICS가 칩별로 분리된 `KMTNg{n,e,w,s}.<ts>.<seq>.fits`
4장을 만들어 주는 전제였다. 신규 아콘 컨트롤러는 **4칩 × 2채널 = 8채널을 한 장의
FITS(4224×1033, uint16)** 로 저장하므로, 분할 단계가 새로 필요하다.

레거시 파이프라인: gmon(wish GUI) → do-Monitoring(노출 루프) → do-sex.psfex
(sex→psfex→FWHM→기록) → do-plotFWHM(gnuplot) + ds9/XPA 스냅샷 캡처.

## 2. 실측으로 확인된 원시 프레임 지오메트리 (2026-08-29, raw/ 샘플 7장)

- `NAXIS1=4224 = 8 세그먼트 × 528컬럼`, `NAXIS2=1033 = 1024 + 9`
- 채널 쌍 = 인접 세그먼트 쌍: 칩 k ← 세그먼트 (2k, 2k+1).
  근거: 실험실 프레임(temp_*)에서 seg4·seg5만 동시에 신호가 있음(칩 1개 연결).
- **스티칭은 direct(뒤집기 없음)** 가 접합부 연속성 최소 불연속(0.5~8.5 ADU vs
  뒤집기 시 20~90 ADU). 아콘 설정이 이미 물리 순서로 저장하는 것으로 보임.
- 채널별 바이어스 페데스탈이 서로 다름(약 1000~1100 ADU) → 스티칭 시 단차 보정 필요.
- 추가 9행의 위치(상/하)와 채널당 16컬럼(528−512)의 성격(프리스캔/다크 기준열)은
  샘플만으로 확정 불가 → **모두 gmon.conf로 설정 가능하게 하고, 기본값은 아래
  §4 [geometry]. 커미셔닝 때 재확인 항목.**
- 셔터 없는 프레임트랜스퍼 스미어(수직 램프)가 존재할 수 있음(관측 시 셔터 사용 여부에 따름).

## 3. 신규 구성 (파일 배치)

```
gmon/
  DESIGN.md            ← 이 문서 (계약)
  README.md            개요·설치·사용·커미셔닝 체크리스트
  gmon.conf            단일 INI 설정 (아래 §4)
  gmon.py              Tkinter GUI 관제탑 (레거시 gmon 후속)
  gwatch.py            수신 디렉토리 감시 데몬 (do-Monitoring 후속)
  gsplit.py            원시 프레임 → 4칩 FITS 분할기 (신규)
  gpsf.py              sex+psfex 실행, FWHM 추출·기록 (do-sex.psfex 후속)
  gsnap.py             3×3 PSF 스냅샷 PNG (ds9/XPA 우선, matplotlib 폴백)
  gplot.py             gnuplot 실시간 FWHM 그래프 (do-plotFWHM 후속)
  gtcs.py              TCS/ICS UDP 클라이언트 — auxstatus 질의·fttgoto/dtilt
                       (레거시 nc -w 1 -u 파리티; old/gmon·tcon의 서버 통신 후속)
  gcommon.py           공용: 설정 로더, 밤 파일명, pidfile, 로깅
  config/
    default.sex  default.param.psfex  default.psfex  default.conv  default.nnw
  tools/
    make_synthetic.py  합성 원시 프레임 생성기 (시험용)
  tests/
    run_tests.sh  test_split.py  test_pipeline.py  test_plot.py  test_focus.py
  old/                 레거시 (보존, 수정 금지)
```

런타임 산출물 루트는 `[paths] runroot` (기본 `gmon/run/`, git 미추적):
`run/incoming/`(수신) `run/work/`(분할·카탈로그·PSF) `run/snap/`(PNG)
`run/data/`(fwYYMMDD.dat) `run/log/`(logfile.txt, 프로세스 로그) `run/pid/`.

## 4. gmon.conf (INI) — 키 계약

```ini
[site]
name = SSO
night_offset_hours = -8     ; 밤 파일명 계산: localtime + offset (레거시 동일)

[paths]
runroot   = run             ; gmon.conf 위치 기준 상대경로 허용
configdir = config
python    = /opt/miniconda3/bin/python
sex       = sex             ; PATH 또는 절대경로
psfex     = psfex
gnuplot   = gnuplot
ds9       = ds9
xpaset    = xpaset

[watch]
pattern        = *.fits     ; incoming 감시 글롭
poll_sec       = 2
settle_sec     = 2          ; mtime 안정화 대기 (쓰다 만 파일 방지)
delete_raw     = no         ; 처리 후 원본: no=보존(processed/로 이동), yes=삭제

[geometry]
raw_nx        = 4224
raw_ny        = 1033
nseg          = 8
seg_width     = 528
; 세그먼트 내 활성 컬럼 [시작,끝) — 왼쪽/오른쪽 채널 각각
left_active   = 16,528
right_active  = 0,512
; 행 트리밍 (커미셔닝 때 확정; 현 샘플은 최소 1행(맨 아래)이 더미)
y_trim_bottom = 9
y_trim_top    = 0
; 채널 좌우 반전: 실측상 불필요. 필요 시 칩별 "left,right" 플래그
flip_right_x  = no
; 스티칭 단차 보정: 채널별 중앙값을 접합부에서 일치시킴
pedestal_match = yes

[chips]
; 세그먼트쌍(0-기준) → 방위. 사용자 정의: 칩 순서 N, S, E, W
order  = n,s,e,w            ; 칩0=(seg0,1)=n, 칩1=(seg2,3)=s, 칩2=(seg4,5)=e, 칩3=(seg6,7)=w
prefix = KMTNg              ; 분할 산출물 접두 (레거시 호환)

[pipeline]
pixel_scale   = 0.52        ; arcsec/px (레거시 가이더 값, 커미셔닝 때 재확인)
min_fwhm_px   = 1.0         ; 이 미만이면 실패 처리(0.0 포함)
stat_region   = 10,500,70,970  ; 배경 stddev 측정 x1,x2,y1,y2 (1-기준, 레거시 동일)

[display]
backend      = auto         ; auto|ds9|mpl  (auto: xpaset 있으면 ds9)
; ds9 타일 회전(도) — 레거시 값, 커미셔닝 때 재확인
rot_n = 90
rot_e = 180
rot_w = 0
rot_s = 270
zoom  = 16

[plot]
term        = qt            ; qt|x11|png
size        = 800,380       ; 그래프 창 크기 (운용판 2026-03 파리티)
refresh_sec = 10
y_fwhm_max  = 12
y2_range    = -8.0,-5.0     ; 초점축 범위 (운용판 2026-03 값; y2tics 0.5 간격)

[focus]
slope     = -0.067          ; ref = slope*T - (base + dfocus)
base      = 5.56            ; SAAO 운용판 2026-03 값 (22-05-06 4.145→5.56); 사이트별 재보정
dfocus    = 0.000           ; GUI ±로 갱신, gmon.conf에 저장하지 않고 run/dfocus.txt에 영속
step      = 0.005           ; 운용판 파리티 (2018판 0.001 → 운용판 0.005)
big_step  = 0.5             ; 운용판 2021-01 "big adjust" 버튼 (±0.5)
safe_min  = -8.0
safe_max  = -5.0            ; 운용판 2026-03-13 재정의 (-8.0 < ref < -5.0)
max_jump  = 0.1             ; AUTO에서 직전 ref와 차이가 이 이상이면 전송 보류
period_sec = 120
temp_source  = auto         ; 온도 출처: fw|tcs|auto (auto=fw 우선, 서버 폴백)
temp_sensor  = 3            ; TCS auxstatus의 ENS<n> (fw TEMP=ENS3 동일 센서)
fw_stale_sec = 900          ; auto에서 fw 마지막 기록의 신선도 한계(초)

[ics]
mode     = file             ; file=수신 디렉토리 감시(기본) | legacy-udp=레거시 트리거
host     = 192.168.13.109
port     = 6660
dry_run  = yes              ; yes면 이동 명령(fttgoto/dtilt) 미전송 (질의는 허용)
timeout_sec  = 1.0          ; UDP 응답 대기 (레거시 nc -w 1 파리티)
from         = abc          ; ISIS 라우팅 발신자 ("<from>><tc> <명령>")
tc           = tc
status_query = yes          ; GUI의 주기 auxstatus 상태 표시
status_sec   = 10
```

## 5. 데이터 형식 계약

### 5.1 분할 산출물 (gsplit)
- 파일명: `<prefix><p>.<stem>.fits`, p∈{n,s,e,w}, `<stem>` = 원본 파일명에서
  `.fits` 제거 (예: `modtm.20260527.195724` → `KMTNgn.modtm.20260527.195724.fits`
  가 아니라 **stem 전체 유지**: `KMTNgn.20260527.195724.fits`처럼 원본이
  `<이름>.<날짜>.<시각>.fits`면 이름 부분을 제거하고 날짜.시각만 취한다.
  규칙: stem = 원본 basename에서 `.fits` 제거 후, 첫 토큰이 **숫자로 시작하지
  않으면** 첫 토큰 제거. 결과가 비면 전체 stem 사용.)
- float32, 헤더: 원본 전체 전파 + `GCHIP`(n/s/e/w), `GSEG1`,`GSEG2`(세그 인덱스),
  `GGEOMVER='GMON-GEOM-v1'`, `GPED1`,`GPED2`(적용한 페데스탈 오프셋),
  `GRAWFILE`(원본명). BZERO 없는 float 저장.
- 크기: (raw_ny − y_trim_bottom − y_trim_top) × (left_active폭 + right_active폭)
  = 기본 1024 × 1024.

### 5.2 fw 데이터 파일 (gpsf가 append) — **운용판(2026-03 SAAO) do-plotFWHM 호환 필수**
- 경로: `run/data/fw%y%m%d.dat` (밤 = localtime + night_offset_hours)
- 한 줄: `YY:MM:DD:HH:MM:SS fwN fwE fwW fwS FOCUS TEMP SECZ`
  (운용판 2018-11-30 개정 형식 — gnuplot timefmt `%y:%m:%d:%H:%M:%S`)
- fw*는 arcsec 소수2자리. FOCUS/TEMP는 헤더 결측("___") 시 같은 fw파일의
  직전 줄 값을 계승(운용판 파리티), 직전 줄이 없으면 0.0. SECZ 결측은 0.0.
- 시각은 관측시각(DATE-OBS/TIME-OBS 있으면 그것, 없으면 처리 시각) 로컬 기준.
- gplot은 구형 파일(2018판 `%d:%H:%M:%S`)도 시각 토큰의 콜론 수(5 vs 3)로
  자동 판별해 그린다 (old/fw181022.dat 시험 데이터 호환).

### 5.3 상세 로그: `run/log/logfile.txt` — 레거시 형식 유지 + fwAVG (아래 5.5) 추가.

### 5.4 결과 사이드카: `run/work/result.<stem>.json`
gpsf → gsnap 전달용. 키: `stem, chips{n|s|e|w: {fwhm_px, fwhm_as, sd, psf_file,
snap_file, ok}}, fwavg_as, header{SECZ,FOCUS,TILTEW,TILTNS,ESW,T123,ALT,AZ,
DATEOBS,TIMEOBS}, raw_file` (헤더 키 없으면 값 `"___"`).

### 5.5 fwAVG = **유효한 칩들의 산술평균** (레거시 버그: W 2회/S 누락 — 수정).

### 5.6 스냅샷 PNG: `run/snap/psf.snap.<stem>.png` — 존재하면 해당 노출 재처리
생략(레거시 파리티). **기준 화면: `old/psf.snap.20181003T011100.0001.fits.png`.**
- 3×3 배치(각 타일 ~200px, 전체 ~600×649): 중앙=정보 패널, 상=N, 좌=E, 우=W,
  하=S (나침반 배치), 모서리=검은 빈 칸, 타일 사이 밝은 분리선.
- 각 PSF 타일: psfex 스냅샷의 **중앙부만 확대** — ds9 `zoom 16`과 동일하게
  타일에는 중앙 약 200/zoom ≈ 12~13픽셀만 보이는 큰 픽셀 룩. minmax 그레이 +
  초록 등고선(~5레벨) + 빨간 라벨: 위 `sdX=…`, 아래 `fwX=…`.
- 중앙 정보 패널(위→아래, 빨강): `<stem>.fits`, `SecZ=`, `Focus=`, `TiltEW=`,
  `TiltNS=`, `ESW=`, `T123=`, `ALT/AZ=`, 그리고 초록 `fwAVG=`.
- 하단: 그레이스케일 컬러바 스트립(눈금 수치 포함, ds9 캡처 파리티).

## 6. CLI 계약 (모두 `-c/--config <gmon.conf>` 지원, 기본은 스크립트 옆 gmon.conf)

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
                        ; base=실프레임 별 주입, fwhm-scatter=별별 FWHM 산포 비율
```

- 종료코드: 성공 0, 부분 실패(일부 칩) 2, 완전 실패 1.
- 단일 실행 보장: `run/pid/<name>.pid` (ps|grep 사용 금지).
- 모든 실행 로그: `run/log/<name>.log` (stdout에도 출력).

## 7. 프로세스 오케스트레이션

gwatch가 새 파일 감지 → gsplit(라이브러리 호출 또는 서브프로세스) → gpsf →
gsnap → gplot 기동 확인(안 떠 있으면 기동). GUI(gmon.py)는 gwatch/gplot의
시작·정지(pidfile 기반 SIGTERM)와 초점 AUTO/MAN 루프를 담당하고, **독립 창
3개**로 표시한다: 제어부(메인 창) / PSF 스냅샷 창(run/snap 최신
psf.snap.*.png 자동 감지, 3초 주기) / FWHM 그래프 창(gplot --oneshot
--term png 주기 렌더 → run/work/gui_fwplot.png). 서브 창은 닫으면 숨김이며
제어부 SNAP/PLOT 버튼으로 다시 연다. GUI는 run/pid/gmon.pid를 획득하며
(단일 실행), 이 pidfile이 살아 있는 동안 gwatch.ensure_gplot은 외부 gnuplot
라이브 창을 띄우지 않는다. killall 금지.

## 8. 초점 제어 (gmon.py 내 FocusController 클래스 — tests/test_focus.py 대상)

- `ref = slope * T − (base + dfocus)`; T = 최신 fw파일 마지막 줄의 TEMP 필드
  (공백분리 7번째). 상수 출처: SAAO 운용판 2026-03 (slope −0.067, base 5.56,
  안전범위 −8.0~−5.0). GUI에는 ±step(0.005) 버튼과 ±big_step(0.5) 버튼
  (운용판 2021-01 "big adjust") 총 4개를 둔다.
- **서버 질의 (gtcs.py, tests/test_tcs.py 대상)**: ISIS 허브(host:port)로
  `<from>>tc auxstatus` UDP 질의 → KEY=VALUE 응답 파싱 (근거:
  TCSAgent/TCSAgent.latest/KMTNet/commands.c cmd_auxstatus). 온도 ENS1..7,
  현재 초점 FAFOCUS, 틸트 FATILTNS/EW, 셔터 SHUTTER, 액추에이터 FAPOSS/E/W.
  temp_source=auto면 fw파일이 없거나 fw_stale_sec보다 오래됐을 때 서버
  ENS<temp_sensor>로 온도를 폴백한다 (레거시 old/gmon에 주석으로 남아 있던
  `tc auxstat` 직접 질의의 복원 — 밤 시작 등 fw 데이터가 없어도 AUTO 동작).
- 이동 명령은 gtcs 경유: `fttgoto <foc> [<tns> <tew>]`(절대),
  `dtilt <dns> <dew>`(상대 틸트 — 레거시 tcon 파리티). dry_run=yes면 이동은
  로그만 남기고 질의는 정상 수행. GUI는 status_query=yes일 때 백그라운드
  스레드로 auxstatus를 status_sec 주기 질의해 상태 라벨에 표시한다.
- 안전범위 [safe_min, safe_max] 밖이면 전송 안 함.
- AUTO: period_sec 주기, 직전 전송값과 |Δ| ≥ max_jump이면 보류(레거시 의미 유지).
- MAN: 1회 즉시 전송(안전범위만 검사).
- 전송: UDP로 `abc>tc fttgoto <ref>` (ics.host:port). `dry_run=yes`면 로그만.
- dfocus는 `run/dfocus.txt`에 영속 (레거시 gmon.cfg 대체).

## 9. 시험 환경 (이 Mac)

- python: `/opt/miniconda3/bin/python` (astropy 7.2, numpy 2.4, matplotlib 3.10)
- sex: `/opt/homebrew/bin/sex`, psfex: `/opt/local/bin/psfex`,
  gnuplot: `/opt/homebrew/bin/gnuplot` (버전에 qt/pngcairo 있음), xpaset 없음(→mpl 폴백 경로 시험).
- 실제 원시 샘플: `raw/modtm.*.fits` 4장, `raw/temp_4224x1033_*.fits` 3장
  (modtm 2장은 파일 끝이 2496바이트 잘려 있음 — astropy가 경고 후 읽음. 분할기는
  잘린 파일도 경고만 내고 처리해야 함).
- 레거시 fw 샘플: `gmon/old/fw181022.dat` (gplot 시험용).

## 10. 커미셔닝 때 확정할 항목 (README에도 명시)

1. 추가 9행의 위치(상/하)와 16컬럼의 성격 → [geometry] 갱신
2. 칩↔방위 매핑([chips] order)과 ds9 회전각 — 하늘에서 별로 확인
3. 픽셀 스케일(0.52 가정) 실측
4. 채널 반전 여부 재확인(현 direct), GAIN/SATUR_LEVEL(현 16비트 65535)
5. 신규 ICS의 파일 저장 경로·파일명 규약 → [watch] pattern, stem 규칙
6. TCS 초점 명령(`tc fttgoto`) 규약 유지 여부 → dry_run 해제
7. legacy-udp 모드 사용 시: 운용판 do-Monitoring(2020-02)은 과학 CCD 읽기와의
   크로스토크 회피를 위해 `gmon>obs sysstatus`로 과학 노출 잔여시간 >15s일
   때만 가이드 노출(`icg go`)을 트리거함 — 신규 ICS 규약 확정 시 반영 여부 결정

## 11. 운용판(2026-03 SAAO 스냅샷) 파리티 근거

`~/Desktop/남아공-FSA.upgrade/192.168.13.108-gmon/saao.run.tar`에서 추출한
실제 운용 스크립트(2026-03-14 기준) 대비 이 설계가 채택한 값:

| 항목 | 2018판(old/) | 운용판(2026-03) | v2 채택 |
|---|---|---|---|
| fw 시각 형식 | `%d:%H:%M:%S` | `%y:%m:%d:%H:%M:%S` (18-11-30~) | 운용판 (+구형 자동판별) |
| FOCUS/TEMP 결측 | 0.0 | 직전 줄 값 계승 | 운용판 |
| fwAVG | W 2회/S 누락 버그 | 4칩 평균(수정됨) | 운용판 |
| base | 4.7 | 5.56 (22-05-06~) | 운용판 |
| 안전범위 | −8.0~−3.0 | −8.0~−5.0 (26-03-13~) | 운용판 |
| dfocus step | ±0.001 | ±0.005 + big ±0.5 (21-01~) | 운용판 |
| 그래프 y2 | −6.6~−4.8 | −8.0~−5.0, y2tics 0.5 | 운용판 |
| 그래프 크기 | 기본 | x11 800×380 | 운용판 |
| 노출 트리거 | tc auxstatus 셔터 | obs sysstatus 잔여>15s (20-02~) | §10-7 커미셔닝 항목 |

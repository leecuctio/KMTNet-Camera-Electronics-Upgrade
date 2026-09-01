# Archon `LOCK`/`FETCH`/프레임 버퍼 운영 -- 실기 시험 보고서

- **시험일**: 2026-09-01 ~ 02 (KASI 벤치, `kmtnet-sso`)
- **대상**: KMTC-SCI-101 (`10.0.0.101`, STA0284, FW 1.0.1261 / 백플레인 REV 7) ·
  KMTK-SCI-113 (`10.0.0.113`, STA0200, FW 1.0.1252 / REV 5).  둘 다 `BIGBUF=1`(768 MB x 2) ·
  `FRAMEMODE=2` · 19200 x 9400 x 16bit = 344.2 MiB/프레임.  ACF 는 `[CONFIG]` 959 키 중
  `IP`·`TAPLINES`(빈 꼬리)만 다르다.
- **도구**: `tools/ics_archon_buftest.py`(2x2, 본편 무수정) · `tools/probe_archon.py` ·
  운영자 `ArchonGUI` · 매뉴얼 `Archon_manual_20210223.pdf`
- **경위·판단·계측 결함**: [DevNote 10장](DevNote.md).  이 문서는 **결과와 실행법**만 싣는다.

## 1. 결론

| 물음 | 답 |
|---|---|
| FETCH 하는 동안 다음 프레임의 readout 이 멈추나 | **아니다.**  엔진은 FETCH 중에도 만속(368 행/초)으로 쓴다.  GUI 에서 보였던 "정지" 는 FETCH 중 상태 폴이 버려져 **화면이 얼어붙은 것**이다 |
| `LOCKn` 이 FW 에 반영되나 | **예, 매번.**  `LOCK` 직후 `RBUF` 가 잠근 버퍼를 가리킴 15/15 (1261 8 · 1252 7) |
| `LOCKn` 이 fetch 를 느리게 하거나 엔진을 멈추나 | **아니다.**  `lock` 조건 = `idle` 조건 = 368.0 행/초.  20초(> 프레임 주기)를 쥐어도 감속 0 |
| 버퍼 둘 중 하나를 잠그면 엔진은 | **잠긴 버퍼를 피한다.**  남는 버퍼가 없으면 **쓰던 버퍼를 재사용**해 다음 프레임을 쓴다 (멈추지 않는다) |
| `LOCK` 없이 fetch 하면 | 프레임 경계가 fetch 안에 걸릴 때(약 26%) **엔진이 읽는 중인 버퍼를 집어 간다** -- 두 유닛에서 2/2 관측.  받은 자료는 두 노출이 섞인다 |
| **`[archon] lock_buffer`** | **`true` 유지 (종결).**  대가 0, 지킬 구간 실재 |
| `BUFnFRAME` 을 리셋하는 사건 | **`REBOOT` 만** (첫 프레임 = 1).  CCD `POWEROFF/ON` · `WARMBOOT` 는 이어진다 |
| `POWERON` 의 전제 | **`APPLYALL`** (매뉴얼 p.51).  그 세션에서 안 했으면 `?xx` 로 거부 |

## 2. 실측값

| 항목 | 값 | 비고 |
|---|---|---|
| 독출 라인 속도 | **368.0 행/초** (두 유닛 동일, ±0.1%) | `BUFnLINES` 진행.  8.13 틱 모형 예측 12.8초와 일치 |
| 독출 시간 (4700행) | **12.77초** | |
| 프레임 사이 사강 | **0.50초** = `NoIntMS=500` | 타이밍 스크립트 `NoIntUnit(NoIntMS)` |
| 프레임 주기 (`IntMS=0`) | **13.27초** | `MIN_FRAME_PERIOD` 12.0 의 갱신값 |
| FETCH 344.2 MiB | 101: **3.34~3.49초 / 99~103 MiB/s** · 113: **3.20~3.36초 / 103~107 MiB/s** | 벤치 리눅스 → 10.0.0.x 직결 |
| FITS 저장 (astropy) | 1.21초 | probe 3단계 |
| `LOADPARAMS` → 첫 프레임 완료 | 13.44초 | probe 3단계, 진행률 보고 50회 |
| 프레임 버퍼 기하 | `BUFnWIDTH=19200` · `BUFnHEIGHT=9400` · `BUFnLINES` 최대 **4700** | `FRAMEMODE=2` → 라인클록 하나가 두 행 |
| `BUF1BASE` | 101: **0x20000000** · 113: **0xA0000000** | 고정값(APPLYALL·프레임과 무관).  유닛마다 다르다 → `BUFnBASE` 를 읽는 설계가 옳다 |
| 101 `BUF2BASE`/`BUF3BASE` | 0x50000000 / 0x60000000 | BUF1→BUF2 = 768 MiB (`BIGBUF`) |
| `FRAME` / `SYSTEM` / `STATUS` 필드 수 | 60 / 54 / 196 | `FRAME` 은 버퍼 3개분을 항상 낸다 |

### 2x2 요약 (사강 보정 후, 중앙값 [행/초])

| 조건 | 101 (1261/REV 7) | 113 (1252/REV 5) |
|---|---|---|
| `idle` (5초 대기) | 368.0 | 368.2 (368.2~370.9) |
| `lock` (`LOCKn` 만, 5초) | 368.0 | 368.0 (366.0~368.2) |
| `fetch` (`LOCKn`+FETCH) | 368.0 | 368.1 (368.0~368.3) |
| `nolock` (FETCH 만) | 368.0 | 368.3 (368.2~368.3) |
| `lock` 20초 (> 주기) | 368.0 | -- |

### GUI 재관측 (운영자, 결정적)

> FETCH 동안 `STATUS` `COUNT` 가 멈춰 있고, line 은 **~10 에서 멈춰 있다가 FETCH 완료 후
> ~1500 에서 다시 시작**한다.

`1490 행 ÷ 368 행/초 = 4.05초` = FETCH 시간.  엔진은 계속 썼고 표시만 멈췄다.

## 3. 운용에 걸리는 것

1. **`lock_buffer = true` 를 유지한다.**  근거는 위 표.
2. ⚠️ **잠금은 프레임 주기(13.27초) 안에 풀어야 한다.**  잠금 중 엔진은 버퍼 하나로 돌며
   다음 프레임이 앞 프레임을 덮는다.  실측 fetch 3.4초라 3.8배 여유지만
   **`[archon] fetch_timeout = 30` 이 주기보다 크다** -- 상한까지 끌면 다음 장을 잃는다.
   → 주기 아래(예 10초)로 내릴 것.
3. ⚠️ **`PCTREAD` 가 50% 를 못 넘는다** (`parse.progress` 가 `BUFnLINES/BUFnHEIGHT`).
   OBSAgent 에 그대로 보고된다.  분모를 `LINECOUNT` 로.
4. `config.MIN_FRAME_PERIOD` 12.0 → 13.27.
5. **본편·`probe`·`buftest` 어느 것도 `APPLYALL` 을 대신하지 않는다.**  컨트롤러를 재부팅했거나
   설정을 새로 올렸으면 GUI(또는 `probe --expose`)로 Apply All 을 먼저.  `POWERON` 거부가
   그 신호다.  부팅 시 자동 적용은 ACF `APPLYALL=0`·`POWERON=0` 이라 없다.
6. `WARMBOOT` 은 프레임 카운터·프레임 버퍼 정보를 지우지 않는다.  `REBOOT` 은 지운다(첫
   프레임 1) -- FPGA 펌웨어를 다시 읽으므로 Apply All 도 다시.

## 4. 재현 명령 (벤치, `ics_archon/` 에서)

```bash
# 1단계 -- 읽기 전용 (전원 안 켬).  FW/REV, RBUF, BUFnBASE
python3 -u tools/ics_archon_buftest.py --host 10.0.0.101 --acf acf/KMTC_SCI_101_STA0284_R2608_MK.acf --tag MK

# 2단계 -- 2x2 (전원 켬, 연속 노출).  요약이 넷 다 ~368 / 100% 여야 한다
python3 -u tools/ics_archon_buftest.py --host 10.0.0.101 --acf acf/KMTC_SCI_101_STA0284_R2608_MK.acf --tag MK \
    --stage stall --rounds 4 --csv buftest_KMTC101.csv

# H3 최악 -- 잠금을 주기보다 길게
python3 -u tools/ics_archon_buftest.py --host 10.0.0.101 --acf acf/KMTC_SCI_101_STA0284_R2608_MK.acf --tag MK \
    --stage stall --rounds 3 --hold 20 --csv buftest_KMTC101_hold20.csv

# POWERON 이 거부되면 -- 읽기 전용 진단 (POWER 값 · 설정 줄 대조)
python3 -u tools/probe_archon.py --host 10.0.0.101 --acf acf/KMTC_SCI_101_STA0284_R2608_MK.acf
```

지킬 것: 한 번에 한 대 · 컨트롤러당 접속자 하나(GUI 끊고) · `-u` 로 돌려 `tee` 에 실시간 출력.

### 요약 읽는 법

- 넷의 중앙값이 같고 **최소~최대 폭이 좁으면** 정지 없음 + 사강 모형(`NoIntMS`) 정상.
- `*N` 은 그 표본이 프레임 경계를 N 번 넘었다는 표시.  보정 뒤에도 값이 같아야 한다.
- `lock`·`fetch` 줄의 `RBUF=` 뒤에 `(기대N)` 이 붙으면 `LOCK` 이 그 FW 에서 반영되지 않은 것.
- `nolock` 표본이 `*1` 인데 `WBUF` 가 **받던 버퍼 쪽으로** 움직였으면 그 표본의 자료는 누더기다
  (CSV `buf` == `wbuf1`).  정상이고, 그것이 `LOCK` 이 막는 것이다.

## 5. 자료

벤치 `~/`: `buftest_KMTC101.csv`(⚠️ stride 결함 원본, 증거로 보존) · `buftest_KMTC101_v2.csv` ·
`buftest_KMTC101_hold20.csv` · `buftest_KMTK113.csv` · `buftest_stage*_*.log` ·
`probe_stage*_KMTC101.log` · `frames_KMTC101*/` · `ics_archon/probe/probe.20260901T073638.MK.fits`.
저장소: `664e8f0`(계측 결함 넷) · `c5b6626`(사강 보정).

## 6. 미결

- `BUFnFRAME` 의 비트 폭 (65535 초과 여부) -- 두 유닛 다 `REBOOT` 직후라 카운터가 작다.
- 쓰는 중인 버퍼의 **부분 fetch**(매뉴얼 p.70)가 실기에서 성립하는지 -- 급하지 않다.
- 8.9 원문의 "FETCH 7초" -- 재관측에서는 4초.  그때 GUI 의 호스트·링크가 기록에 없다.
- `LOCKT` · `AUTOFETCH` (FW 명령표에는 있고 매뉴얼에 없다) -- STA 문의.

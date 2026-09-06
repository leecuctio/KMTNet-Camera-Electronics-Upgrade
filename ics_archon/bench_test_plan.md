# 실기·실측 시험 계획 — 다음 세션이 여기서 시작한다

**작성 2026-09-06** (운영자 지시: *"다음 세션에서 RADIONODE 자료획득 시험부터 진행하고, 앞서 정리한
실측 필요 미결사항들 시험할 거니까 … 다음세션 처음에 참고할 실기/실측 시험 항목 및 필요 내용도 함께
잘 남겨줘"*).

이 문서는 **무엇을 어떤 순서로 재고, 무엇이 있어야 잴 수 있고, 어떤 값이 나오면 무엇이 닫히는가**를
적는다.  경위·논증은 `DevNote.md`, guide 첫 구동의 단계별 절차는 [`icg_first_run.md`](icg_first_run.md)
에 있다 — 이 문서는 그 둘을 **시험 순서로** 엮는다.

쪽 표시: **[ICG]** guide 취득(`icg_archon`) · **[ICS]** science 취득(`ics_archon`) · **[공통]**

---

## 0단계 — 시작 전 준비물 ⚠️ **없으면 1단계가 막힌다**

### (a) RADIONODE 자격증명 — ⛔ **운영자만 할 수 있다** (콘솔 접근)

코드가 대신 못 하는 것 넷이다 (DevNote 2266, 9.7):

| # | 준비물 | 어디서 |
|---|---|---|
| 1 | **계정 등급** — Open API 를 쓸 수 있는 등급인가 | Tapaculo365 콘솔 |
| 2 | **API KEY / SECRET** + OPENAPI 매뉴얼의 **base URL · 경로 · rate limit** | 관리자 이름 → 고객사 정보 변경 → API KEY/SECRET |
| 3 | **사이트 LoRa 게이트웨이 기종** (사설 LNS 경로가 가능한지 판단용) | 현장 확인 |
| 4 | **장치 SEND INTERVAL** 결정 — 1분은 배터리가 닳는다, **2~5분 절충 권장** | 콘솔 |

⛔ **KEY/SECRET 실값을 저장소 `icg_archon.ini` 에 적지 말 것.**  한 번 커밋되면 이력 재작성 없이는
못 뺀다.  **벤치 설치본 `~/AIC/etc/icg_archon.ini` 에만** 적는다.  절차는 `README.md` 의
"Radionode 자격증명" 절.

⭐ `stale_after` 는 **SEND INTERVAL 의 약 3배**로 맞춘다 (현재 600 s = 3분 간격 전제).  ④를 정하면
이 값도 함께 고친다 — 안 고치면 멀쩡한 표본을 낡았다고 버리거나, 낡은 값을 헤더에 싣는다.

### (b) 그 밖

- 벤치 네트워크에서 **인터넷이 되는가** — `openapi` 백엔드는 인터넷이 있어야 한다.  끊기면
  `HEBOX`/`FSATEMP`/`FSAHUM` 이 그동안 sentinel 이고, 운영자는 그 결측을 받아들이지 않는다(2026-09-04).
- guide 유닛 `10.0.0.162` 접속 · ACF **`KMTK_GUI_162_STA0201_R2617.acf`** 적용 여부.
- science 는 **`KMT?_SCI_*_R2611_*.acf`** 6장이 현행이다.
- ⭐ **장치 MAC / 시리얼** — 벤치 ini 의 `[radionode.hebox]`·`[radionode.fsa]` 에 적을 값.
  ⚠️ 자격증명 넷과 **별개**다.  이것이 어긋나면 3(`CONNECT`)은 통과하는데 4(`HK`)에서
  값이 계속 sentinel 로 남아, 원인을 "인터넷/계정 등급" 으로 오진하기 쉽다.
- **`stale_after`** = 장치 SEND INTERVAL 의 **3배** 로 맞춘다 (0단계 (a) 4번에서 정한 값).

---

## 1단계 — RADIONODE 자료획득 시험 ⭐ **다음 세션 첫 항목**

> ⚠️ **1단계는 전원을 올리지 않는다.**  아래 절차 1~5 는 헤더가 필요 없고
> 컨트롤러 전원과도 무관하다 — 그래서 `icg_first_run` 보다 **먼저** 돌릴 수 있다.
> ⛔ **헤더를 봐야 하는 항목(구 6·7·8)은 `1-B` 로 갈랐다** — 그것은 `go 1`,
> 곧 **첫 전원 인가**를 요구하므로 [`icg_first_run.md`](icg_first_run.md)
> **0~4단계를 먼저 마쳐야 한다**.

**닫히는 것**: 규격 `OI-16`(Radionode 원값 포맷) · 5.8절 *"원값 그대로 싣기"* 확정 · HK 5장 중
`HEBOX`/`FSATEMP`/`FSAHUM` 의 실기 경로.

### 절차

| # | 하는 것 | 기대 | 실측 |
|---|---|---|---|
| 1 | 벤치 ini 에 자격증명 4개를 적고 ICG 기동 | 기동 로그에 Radionode 폴러가 뜬다 | |
| 2 | `RADIONODE STATUS` | 폴링 상태 + 장치 둘(`hebox`·`fsa`)의 접속 상태 | |
| 3 | (ini 가 `off` 였다면) `RADIONODE CONNECT` | `off` → `openapi` 로 올라가고 폴링 루프가 뜬다. ⚠️ 자격증명이 모자라면 **무엇이 없는지 대고 거절**한다 | |
| 4 | 1~2 폴링 주기 기다린 뒤 `HK` | `HEBOX=` `FSATEMP=` `FSAHUM=` 이 **실값**으로 보인다 (sim 고정 상수가 아님) | |
| 5 | ⭐ **원값 포맷을 그대로 적어 둔다** | Open API 응답의 원문 표기(소수 자리·부호·단위) — 이것이 `OI-16` 의 답이다 | |

### 판정 (1단계)

- **통과**: 4 가 실값이고 5 에 원값 표기를 적어 왔다.
- **멈출 조건**
  - 3 에서 자격증명 거절 → 0단계 (a) 로 돌아간다.
  - ⭐ **3 은 통과했는데 4 가 계속 sentinel** → 0단계 (a) 로 통째로 돌아가지 말 것.
    장치 **MAC/시리얼**이 ini 의 `[radionode.hebox]`/`[radionode.fsa]` 와 맞는지,
    `stale_after` 가 **SEND INTERVAL 의 3배**인지부터 본다 (그 둘이 준비물 표에 없어
    실제로 여기서 막힌다).
  - 폴링이 아예 안 뜨면 `RADIONODE STATUS` 의 `backend=` 를 본다 — 기본이 `off` 다.

---

## 1-B 단계 — Radionode 값이 **헤더에 실리나** ⚠️ **전원이 올라간 뒤**

⛔ **전제**: [`icg_first_run.md`](icg_first_run.md) **0~4단계 완료** — Apply All ·
`probe_archon.py --unit guide` · **Config 슬롯/줄 번호 대조** · `POWERON`.
⚠️ **슬롯 대조를 건너뛰고 `go` 를 돌리지 말 것** — `set_config` 가 엉뚱한 줄을 고치면
`EXPTIME` 이 안 바뀐 채 파일이 저장되고, 그 파일은 겉보기에 멀쩡해서 **나중에 못 걸러낸다**.

| # | 하는 것 | 기대 | 실측 |
|---|---|---|---|
| 1 | `go 1` 뒤 FITS 헤더 | `HEBOX`/`FSATEMP`/`FSAHUM` 이 sentinel 이 아니다.  `FSATEMP` 는 **부호 있는 `+23.4` 꼴**, `FSAHUM` 은 **무부호** (규격 5.0) | |
| 2 | ⭐ **`HKUDATE` 가 실린다** | 2026-09-06 에 고친 자리다 — guide 헤더의 `HKUDATE` 가 종전엔 늘 `NC` 였다.  **가장 낡은 표본시각**이 19자로 실려야 한다 | |
| 3 | 장치 하나를 끊고(`RADIONODE DISCONNECT hebox`) `stale_after` 를 넘긴 뒤 헤더 | 그 카드만 sentinel 로 떨어지고 나머지는 산다 | |

### 판정 (1-B)

- **통과**: 1·2 가 실값이고 3 이 sentinel 로 정확히 떨어진다.
- **멈출 조건**: 1 에서 부호 규약이 어긋나면 `rawhdr.format_temp`/`format_ens` 를 먼저
  본다(규격 5.0 · 5.8).  ⛔ 첫 `go` 가 `POWERON` 을 `?xx` 로 거절당하면 **Apply All 이
  없었던 것**이다 — 다시 돌리지 말고 `icg_first_run` 0단계로 돌아간다.
- ⚠️ `sim` 백엔드는 고정 상수를 내고 **헤더 경로로는 안 나간다** — 배선 확인용이지 이 시험의 답이 아니다.

---

## 2단계 — guide 첫 구동 실측 [ICG]

절차는 [`icg_first_run.md`](icg_first_run.md) 0~6단계 그대로.  이 문서는 **그 표에서 닫히는 미결**만
짚는다.

| 항목 | 쪽 | 준비물 | 판정 | 닫히는 것 |
|---|---|---|---|---|
| `RESETTIMING` 뒤 파라미터 RAM 보존 | ICG | `abort` 한 번 | abort 뒤 flush 가 **정확히 한 번** 돌면 RAM 이 보존된 것 | DevNote 11.32-(1) ⏳ |
| `go 1` 뒤 FRAME 카운터 +1 | ICG | `go 1` | 카운터 증가분이 **1** (flush 는 프레임을 안 만든다) | `OI-26` |
| **STOP 뒤 꼬리 flush** | ICG | `go 5` 중 `stop` | 마지막 저장 뒤 `FRAME` 불변 + **≈1.25 s 클록** 한 번 | DevNote 11.33-(1) ⏳ |
| 기본 노출시간 실측 | ICG | `guideexp 1.3` 연속 | 주기 중앙값이 **1.2506 s** 계산값과 몇 % 안에 드나 | `acftiming` PROVISIONAL 해제 |
| `FlushLines`=2448 실측 | ICG | flush 소요 계측 | 본 독출(1.2439 s)과 같은가 | `OI-26` |
| guide `STATUS` 원문 확보 | ICG | `archon STATUS` | 응답 원문을 **파일로 저장소에** 남긴다 (한 번도 남은 적이 없다) | `OI-25` 전제 |
| `HTROUT` 이 측정값인가 명령값인가 | ICG 원천 | ⚠️ **아래 "히터 강제 출력 — 안전 봉투" 절차대로만** | 명령값이면 즉시 따라오고, 측정값이면 지연·오차가 있다 | `OI-28` |
| `PIXSCALE` | ICG | 하늘 실측 | 0.49 / 0.51 / 0.52 중 확정 | `OI-22` |
| 추가 9행 위치·칩 방위 | ICG | 프레임 검사 | 상/하 위치와 `CHMAP`/`IMGROT` 값 | `OI-21` |

### ⛔ 히터 강제 출력 — 안전 봉투 (`OI-28` 실측용)

⚠️ **`HTRFORCE 1` 은 PID 를 우회한다** — `HEATERALIMIT`(25 V)은 **PID 모드 전용**이라
강제 모드에서는 안 걸린다.  즉 **온도와 무관하게 지시한 전압이 그대로 나간다.**
⭐ 코드에 운영 상한(`heater_force_max`)을 **일부러 두지 않았으므로**(값 미정, DevNote
11.14-(3)) **그 상한이 사는 자리는 이 문서뿐이다.**

**절차** (한 걸음씩, 각 걸음마다 `CCDTEMP`·`DMPTEMP` 를 본다)

| # | 명령 | 확인 |
|---|---|---|
| 1 | `HTREN 0` | 히터 사용을 먼저 끈다 — PID 와 강제가 겹치지 않게 |
| 2 | `HTRFORCE 1 1.0` | `HTROUT` 이 **1.0 V 부근**을 보고하나.  ⭐ 즉시 따라오면 명령값, 지연·오차가 있으면 측정값 |
| 3 | 30초 유지 | `CCDTEMP`·`DMPTEMP` 가 **오르기 시작하는가** |
| 4 | `HTRFORCE 1 2.0` | 같은 관찰.  ⛔ **2.0 V 를 넘기지 않는다** |
| 5 | ⛔ **`HTRFORCE 0 0`** | 강제 해제 + **레벨까지 0 으로**.  `HTROUT` 이 0 으로 떨어지는지 확인 |

⛔ **멈출 조건 — 하나라도 걸리면 즉시 `HTRFORCE 0 0`**

- `CCDTEMP` 또는 `DMPTEMP` 가 **1 K 이상 오르면** 즉시 중단한다.
- `HTROUT` 이 지시값보다 **크게** 나오면 즉시 중단한다 (강제 경로가 예상과 다르다).
- `HTROUT` 이 `NC` 로 오면 되읽기 경로가 없는 것이다 — 강제를 더 올리지 말고 `OI-25` 로 돌아간다.
- 진공(`DEWPRES`)이 흔들리면 중단한다 — 히터가 예상 밖 부하에 걸린 것이다.

⚠️ **되돌림을 반드시 확인할 것** — `HTRFORCE 0` 만 치면 **`FORCELEVEL` 이 남는다.**
다음 사람이 `HTRFORCE 1` 을 치는 순간 **옛 전압이 되살아난다.**  반드시 레벨까지 `0`
으로 되돌리고 `HKDATA`/`HK` 로 `HTROUT=0` 을 눈으로 확인한 뒤 끝낸다.

⚠️ **`APPLYMOD` 가 MOD10 VCPU 를 재시작한다** (DevNote 11.18) — 이 절차를 도는 동안
`DEWPRES` 가 한동안 결측일 수 있다.  그것은 고장이 아니다.

### DG 정적 덤프 실측 (FRAME6 후속 판 **R2618** 판단)

[`icg_first_run.md`](icg_first_run.md) 의 **부록 "DG 정적 덤프 실측"** 에 단계(A~E)·판정표·멈출 조건이
있다.  ⭐ **약한 균일광**이 필요하다 — 어둠에서는 `go 1` 의 첫 flush 가 image/store 를 비워 신호가 안 남는다.

---

## 3단계 — science 쪽 [ICS]

| 항목 | 준비물 | 판정 | 닫히는 것 |
|---|---|---|---|
| `ccdflush=true` 주기 | 벤치 ini 에서 켜고 한 장 | 주기가 `SkipLine(FlushLines)` 만큼 늘어난다 (10장 실측 13.27 s 는 **끈 상태** 값) | DevNote 11.33-(2) ⏳ |
| 행 순서·독출 방향 | flat/star sequence | amp 별 물리 독출 방향 → 4.5절 표에 열 추가 | `OI-3` |
| 중앙 168행 분배 | bias 통계 | 84/84 인가 | `OI-4` |
| 셔터 상태 반영 지연 | `SHOPEN` + 1초 재질의 | AUX 상태기계가 넘어가 있나 | `OI-13` |

---

## 4단계 — 코드 후속 (실측이 아니라 구현)

| 항목 | 쪽 | 내용 |
|---|---|---|
| 예측 폴링 | ICG | `DATE-OBS` 폴링 편향(평균 +0.25 s) 제거 — `icg_archon/sequencer.py` |
| `HTREN`·`HTRSET`·`HTRFORCE` 표본 배선 | ICG 원천 | `hk.py` 의 `_sample`/`_COLUMNS` 에 없다.  되읽기 함수는 `heater.py` 에 있다 → `OI-25` 잔여 |
| `BUFnTIMESTAMP` + TIMER↔UT 상관 | 공통 | `ics_archon/archon/parse.py` |
| flake | ICS | `tests/test_failures.py::test_shutdown_waits_for_frames_that_are_still_being_saved` |

---

## 기록 규칙

- 실측값은 **이 문서의 "실측" 칸**에 적고, 경위·판단은 `DevNote.md` 에.  결과·실행법은 보고서와
  `icg_first_run.md` 에 (문서 층을 섞지 않는다).
- ⏳ 가 닫히면 `DevNote.md` 의 해당 절과 규격 `OI-` 행에 **✅ 표시**를 함께 단다 — 한쪽만 고치면
  다음 사람이 열린 줄 안다.
- 규격을 고쳐야 하면 **`main` 워크트리**에서, 커밋은 **라운드 끝에 하나로**
  (`../SMC_CLAUDE.md` 커밋 규약).

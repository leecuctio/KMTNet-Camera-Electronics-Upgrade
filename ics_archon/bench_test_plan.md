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

---

## 1단계 — RADIONODE 자료획득 시험 ⭐ **다음 세션 첫 항목**

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
| 6 | `go 1` 뒤 FITS 헤더 | `HEBOX`/`FSATEMP`/`FSAHUM` 이 sentinel 이 아니다.  `FSATEMP` 는 **부호 있는 `+23.4` 꼴**, `FSAHUM` 은 **무부호** (규격 5.0) | |
| 7 | ⭐ **`HKUDATE` 가 실린다** | 2026-09-06 에 고친 자리다 — guide 헤더의 `HKUDATE` 가 종전엔 늘 `NC` 였다.  **가장 낡은 표본시각**이 19자로 실려야 한다 | |
| 8 | 장치 하나를 끊고(`RADIONODE DISCONNECT hebox`) `stale_after` 를 넘긴 뒤 헤더 | 그 카드만 sentinel 로 떨어지고 나머지는 산다 | |

### 판정

- **통과**: 4~7 이 전부 실값이고 8 이 sentinel 로 정확히 떨어진다.
- **멈출 조건**: 3 에서 자격증명 거절 → 0단계 (a) 로 돌아간다.  6 에서 부호 규약이 어긋나면
  `rawhdr.format_temp`/`format_ens` 를 먼저 본다(규격 5.0 · 5.8).
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
| `HTROUT` 이 측정값인가 명령값인가 | ICG 원천 | `HTRFORCE` 로 출력을 강제하고 `HTROUT` 변화를 본다 | 명령값이면 즉시 따라오고, 측정값이면 지연·오차가 있다 | `OI-28` |
| `PIXSCALE` | ICG | 하늘 실측 | 0.49 / 0.51 / 0.52 중 확정 | `OI-22` |
| 추가 9행 위치·칩 방위 | ICG | 프레임 검사 | 상/하 위치와 `CHMAP`/`IMGROT` 값 | `OI-21` |

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

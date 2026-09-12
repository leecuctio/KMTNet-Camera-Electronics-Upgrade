# Raw FITS 헤더 개정에 따른 MEF ICD · MEF Converter 개정 및 검토 사항

**v0.10 (Draft)** · 2026-09-12 · **돔 방위 셋 출처 · `OBSTYPE` 어휘 · HK 완료형 정정** (raw spec v1.13 동반) — 기록 행 둘 신설(**돔 방위 셋 = 돔 제어 프로그램 redis**, **`OBSTYPE` 이 계통 식별로**)  · C-신설 HK 히터 넷 행의 *"구현 전에는 항상 `'NC'`"* 를 **배선 완료**로 고치고 **`HKUDATE` 가 Radionode 3장의 나이를 말하지 않는다**는 경고를 더했다 · Part 2 머리말에 **저장 안 된 프레임은 번호를 소비하지 않는다**(raw spec 2.3절 8항 · D-022) · `PRESCNX` 행에 guide 값(**16**, dark reference columns)과 확인 요망 10 종결 · ICD **v4.2** · converter **v2.4.0** 표기.  ⭐ **셋 다 converter 동작 불변** — 값 공급 계통과 사실 서술의 변경이다.  구판 v0.9 = 2026-09-04 · v0.8 = 2026-08-30 · v0.7 = 2026-08-29 · **Part 1** = 헤더 카드 개정이 MEF 쪽 3자(ICD **v4.2** · MEF keyword 정의서 v1.0 · converter **v2.4.0**)에 요구하는 개정 목록 · **Part 2** = raw 파일 번호 · 정체성 · 충돌 처리 재설계와 그 MEF 파급

> **⚠️ main 영향 검토 (2026-08-30, raw spec v1.9 발행 후 전수 재검 — 제자리 추기)** — `raw_fits_spec/` 밖에서 확인된 파급과 처리 상태:
>
> - ✅ **main 에서 고쳤다** (커밋 `58bf083`): ① `project_management/governance/DECISION_LOG.md` **D-020** 의 "main 의 규격은 아직 구 문장이다" — `41845da` 합류로 거짓이 된 서술을 정정 ② 같은 문서 **D-016** 의 통합문서 현행 참조 `v0.7` → `v0.8` ③ **루트 `README.md`** 의 raw_fits_spec 설명 — pair 전용 → guide 포함 (2곳).
> - 📌 **보고만 — 각 소관에서 처리한다** (다른 작업자의 main 작업물을 이 자리에서 고치지 않는다 — 운영자 2026-08-30):
>   1. **ICD v4.1 (`../mef_fits_spec/`) 의 죽은 경로 참조** — `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 는 2026-08-22 개명 이후 존재하지 않는 경로다 (현행은 `KMT_CEU_Raw_FITS_Specification_v1.9.md`). 이번 v1.9 변경과 무관한 **기존 결함**이며, ⚠️ **LEECU — 다음 ICD 개정 때 참조 갱신 요청** (이 문서 Part 1 전달분에 포함).
>   2. **gmon**: 프레임 기하는 규격 9장과 **완전 일치** (4224×1033 · 채널 528 = 16+512 · y_trim 9). 유일한 어긋남은 **칩 순서**(견본 `CHMAP`/`IMGROT` = N·E·S·W vs `gmon.conf` 잠정 n,s,e,w) — 규격 **OI-21** 로 등재됐고, `gmon/DESIGN.md` 에 규격 9.2/9.4 포인터를 넣는 것은 gmon 세션 몫.
>   3. **9/1 회의 아젠다 부록**의 "raw 규격 v1.7" 은 "2026-08-28 기준" 이 명시된 스냅샷이라 거짓이 아니다 — 회의 전에 기준일째 갱신할지만 판단하면 된다.
>   4. DECISION_LOG **D-020 상태줄** "main 트리에는 `siteid.py` 가 아직 있다" 는 확인 결과 **여전히 사실** — 유지 (ics_sim 합류 대기 서술).

> **v0.8 개정 (2026-08-30)** — **환경 센서 장치명 `Tapaculo` → `Radionode`** (운영자 지시 2026-08-30, raw spec v1.9 동반). 출처 표기 `Tapaculo sensor` → `Radionode sensor`, 본문 표기 전량 교체 — 장치는 같고 이름만 바뀌었으므로 **C-항목·판단 요청 내용에는 변화가 없다.** 구판(`archive/`)의 `Tapaculo` 는 같은 장치다. ⚠️ raw spec v1.9 가 **guide raw FITS 를 9·10장으로 신설**했지만 guide 는 converter·MEF 경로를 타지 않으므로(소비자는 `gmon`) **이 문서에 새 C-항목은 없다.**

> **제자리 개정 (2026-08-25) — raw spec v1.5 5장 검토 라운드 반영.** 판 이름은 그대로 두고 내용만 보강했다(참조 안정성 — raw spec·README 가 이 파일명을 가리킨다). 반영: ① **D-017 사이트 코드** — `TESTBED`/`KMTT` 폐지, `KASI`/`KMTK`. §1 의 철회됐던 `OBSERVAT` 항목을 **C-재개** 로 되살렸고 §3 의 "파일명 체계 불변" 기술을 정정했다 ② **D-018 번호 공간** `000000`–`999999`(Part 2 §2·§3) ③ **`CHMAP_*` 토큰 3자→4자** `<chip><A\|D><nn>`(C-11 · §2 — **구 3자 파서는 고쳐야 한다**) ④ **HK 카드 4장 폐지**(`AIR_IN`/`AIR_OUT`/`GLYC_IN`/`GLYC_OUT`) — §1 HK 항목 ④ · §4 신설 ⑤ **`IMGSEC` `B-BOT`→`D-BOT`**(OI-17 잔여 ①·② 종결, §5) ⑥ **`TELESCOP`/`FPAID` 사이트별 상수표**(D-017 항목 6, §4) ⑦ OI-13 재질의 3초→1초.
>
> **제자리 개정 (2026-08-26) — raw spec v1.6 반영.** ⑧ **`ORIGNAME` 폐지 · `EXPID` 신설** (운영자 확정).  값이 `<SITE>.<YYYYMMDD>.<NNNNNN>` 으로 **`DETID` 필드가 없어 pair 양쪽에서 같다** — 5.9절 "반드시 상이" 가 **7장 → 6장**이 됐다.  **converter 파급 둘**: ⓐ `ORIGNAME` 을 읽던 자리는 `EXPID` 로 옮긴다 ⓑ 충돌 판별이 "두 값 직접 비교" 에서 **`FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 뒤 비교**로 한 단계 는다.  **얻는 것**: `EXPID` 가 pair 양쪽에 같은 값이라 **짝 탐색을 파일명 파싱 없이 이 카드 하나로** 할 수 있다(폐지된 `PAIRFILE` 이 하려던 일).  ⑨ `FILENAME` comment 개정.
>
> **v0.6 에서 바뀐 것 — raw spec 발행에 따른 정합 (2026-08-22).** ① 재작성판 **`KMT_CEU_Raw_FITS_Specification`(raw spec)** 이 발행되어 구 규격 참조를 전부 현행판으로 교체했다 — 이후 운영자 1~4장 검토 반영판 **v1.4** 로 갱신(X overscan `RRRRLLLL` 확정 → §3·§5 의 4:4 vs 5:3 항목 종결). ② **Part 2 를 파급 요약으로 축약** — 번호·충돌·정체성의 정본이 raw spec 2.3절과 DECISION_LOG **D-016** 으로 옮겨졌으므로, 본문(§1~§5·§8)을 걷어내고 MEF/구현 파급(구 §6·§7)만 남겼다(내용 이중화 방지). 전신 v0.5 는 `archive/`.

> **v0.5 에서 바뀐 것 — 두 문서를 하나로 합쳤다 (운영자 지시 2026-08-22).**
>
> 1. **통합**: `KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.4.md`(→ Part 1)와 `KMT_CEU_Raw_Numbering_and_Identity_v0.2.md`(→ Part 2)를 이 문서로 합쳤다. 두 전신은 `archive/` 로 옮긴다. Part 를 가른 이유: **Part 1 은 LEECU 가 실행할 항목**이고 **Part 2 는 raw 쪽 규격 결정(+일부 MEF 파급)** 이라 주인이 다르다.
> 2. **구 검토 문서의 잔여 안건 이관**: 미결 4건(`NCTRL` 정의 · `CTRLID` 개칭 · `SATURAT`/`SATLEVEL` 통일 · `DATASRC`/설정 포인터의 MEF 목적지)을 Part 1 §6 으로 옮겼다 — 이로써 살아있는 내용은 전부 이 문서와 Header_and_Refs 로 흡수됐다.
> 3. **Header_and_Refs v1.11 반영**: 돔 Source 변경(`AUX relay` → `TCS relay or REDIS`, `DALTERR`/`DAZERR` = `ICS calculation`) · `LEDFLASH` 단위 변경([seconds] → [milliseconds] 정수) · `ICSBUILD` 형식 변경(프로그램명 제거) — 셋 다 converter 동작에는 영향이 없어 **기록 행**으로 남겼다(§1 끝).

> **v0.4 에서 바뀐 것 — 운영자 3차 개정(Header_and_Refs v1.9) 반영**: ① **`READMODE` 값 충돌 종결** — raw 쪽은 **`RDMODE` 로 개명 도입**(독출 속도 모드 선언), MEF `READMODE`(`'64AMP'`)는 그대로. ② **raw 신설 카드 `CAMVER` · `RDMODE` · `C1_`/`C2_` 계열** — converter 미독, 도입 시 pass-through 후보로 §2 대응표에 추가. ③ **C-후보 신설** — MEF `VOLTINFO`/`TELEMETRY` 를 raw `Cn_VOLT`·`Cn_CURR`·`Cn_TEMP` 에서 채우는 안. ④ **raw 미도입 확정 반영** — `CTRLTAG`·`PAIRFILE`·`OSCNPATT`·`RDDIRT`/`RDDIRB`·`MIDOSC*`·전압 색인 계열: C-5/C-12 문구를 "규격 조항 + 표본 검증" 기반으로 조정.
>
> **v0.3**: HK 재구성 확정(`WALLBOAR`→`WALLBRD`, 출처 3계통) · C-신설 2건(MEF `UT` 조립 원천 · `DARKTIME` 공급원). **v0.2**: `OBSERVAT` 값 재정의 C-항목(이후 철회로 종결). **Part 2 의 전신 이력** — v0.2: `CTRLTAG`·`PAIRFILE` 미도입 확정 반영(삼총사 문구에서 `CTRLTAG` 제거) · v0.1: 충돌 번호 증가 설계 최초 기록.

> `mef_converter/` 는 읽기 전용(LEECU 소관)이므로 Part 1 은 **변경 요청 목록**이지 변경 자체가 아니다. raw 쪽 근거는 `KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.19.md`(확인 요망 11건 전량 종결 + 판정 준거 0장)와 Part 2(**D-016 등재 완료**), 검토 세션 기록([`SMC_CLAUDE.md`](SMC_CLAUDE.md))이다. raw spec v1.3 발행에 따라 v0.6 으로 판을 올렸다.

---

# Part 1 — 헤더 카드 개정에 따른 MEF ICD · 정의서 · Converter 개정 사항

## 1. Converter 변경점(C-*) 신설 · 개정

| 항목 | 내용 | 판단 요청 |
| --- | --- | --- |
| **C-신설: MEF `UNIQNAME` 공급원** | raw `UNIQNAME` 폐지 후 `v2_1.py:405`의 `v("UNIQNAME","")`가 **항상 빈 문자열**을 반환한다(오류 없음) | 대안 (a) raw `FILENAME` 카드에서 채움 (b) 디스크 파일명(`mk_path`)에서 파생 — 이미 AMPINFO `RAWFILE`이 같은 원천을 씀 (c) MEF `UNIQNAME` 자체를 폐지 — MEF `FILENAME` · `RAWFILE`로 충분. **raw 쪽 권고: (c) 검토, 최소 (b)** |
| **C-재개: `OBSERVAT`·`<SITE>` 사이트 코드 (D-017, 2026-08-25)** | v0.2 에 등재됐다가 2026-08-21 에 **철회·종결**됐던 항목이 **되살아났다.** 운영자가 `TESTBED`/`KMTT` 를 폐지하고 **`KASI`/`KMTK`** 로 확정했다 — `OBSERVAT` ∈ {`CTIO`,`SSO`,`SAAO`,`KASI`}, 파일명 접두어 ∈ {`KMTC`,`KMTA`,`KMTS`,`KMTK`}. `ics_sim` 반영 완료(`rawpair.OBSERVAT`·`ORIGIN_OF`·`KASI_SITE`·보정표·`config._SITE_TELID`·~~`siteid.BENCH_SITE`~~ — ⚠️ **`siteid.py` 는 그 뒤 브랜치 `ics-archon-v1.0-build` 에서 삭제됐다**(D-015 IP 판정 폐기 → **D-020**, 2026-08-24. 사이트 판별은 `[node] observatory` 한 줄이다). **`main` 트리에는 아직 남아 있다** — 이 문서 머리말 ④ 와 같은 사실이다). | ✅ **converter 반영 완료 (2026-09-04, v2.4.0 · LEECU)** — 파일명 정규식 넷째 대안 `KMTK`, `SITE_PREFIX`/`OBS_PREFIX` `KMTK`/`KASI`, L0 MEF prefix `kmtk`. **ICD 도 v4.2 로 판올림**(§2.1 표·개정 이력, 구 v4.1 은 `archive/`). ⚠️ 이 표시는 원래 **v0.8 에 제자리로** 달렸는데 (커밋 `f4c7e5e`) v0.9 판올림이 v0.8 을 `archive/` 로 보내 고아가 된 것을 옮겨 온 것이다 |
| **C-신설(경미): MEF `ORIGIN` 을 상수로** | `ORIGIN` 개념이 **"이 파일이 생성된 곳"** 으로 확정됐다: 관측소 raw = 관측소 이름 · 테스트베드 raw = `KASI` · **KASI 파이프라인 산출물 = `KASI`**. 현행 converter 는 raw `ORIGIN` 을 MEF 로 복사한다(`v2_1.py:341`, `v("ORIGIN","KASI")`) — MEF 는 파이프라인 산출물이므로 개념과 어긋난다 | MEF PRIMARY 의 `ORIGIN` 을 복사 대신 **상수 `'KASI'`** 로 기록. 한 줄 수정, 긴급도 낮음(관측소 raw 를 KASI 서버에서 변환하는 현행 흐름에서만 차이 발생) |
| C-신설(선택): `EXPID` pass-through | 충돌 신호(`FILENAME` 의 `DETID` 필드를 뗀 값 ≠ `EXPID`)는 raw에만 있다. MEF 층 충돌 필터가 필요할 때만 추가. **v1.6 개정 — 구 `ORIGNAME`** | raw 헤더 층 필터가 기본이므로 필수 아님 |
| **C-11 개정** | ⚠️ **토큰 폭이 3자→4자로 바뀌었다 (2026-08-25, raw spec v1.5)** — `<chip><A\|D><nn>`(01–08=`A`·09–16=`D`). 구 3자(`M16`)를 파싱하는 코드는 고쳐야 한다. amp `MODULE`/`CHANNEL` 공급원: 구 규격의 `AMOD<nn>`/`ACHN<nn>` 색인형 65장 → **`CHMAP_LT`/`CHMAP_LB`/`CHMAP_RT`/`CHMAP_RB` 4장**으로 재설계됐다. 현행 추정식(`MODULE=1+((amp-1)//8)`, `CHANNEL=1+((amp-1)%8)`, 'placeholder' 주석)은 실배선(CCD 출력 채널이 chip당 1–16, TOP/BOT 대역이 chip마다 반대)과 다르다 | `XTALKGROUP` 파생도 이 값 기준으로 재정의. `AMPMAP` 선언 카드는 폐지 방향 |
| C-5 · C-13 개정 | "raw geometry 선언 카드 대조" → **포장 규범 조항 + 표본 검증** 체계로 재조정 — `OSCNPATT` 는 raw **미도입 확정**(v1.9), `ROWORDR` 와 함께 규격 조항으로 이관. 대조표에 2장의 이름 대응을 명시 | |
| C-12 | amp `READDIR` 공급원 후보였던 `RDDIRT`/`RDDIRB` 는 raw **미도입 확정**(v1.9) — 대조 근거를 카드가 아니라 **규격 조항 + 표본 검증**으로 갱신. OI-3(실기 확인) 유지 | |
| **C-신설: HK 온도 카드 재구성** (2026-08-21) | 온도센서 구성 변경으로 raw 의 Camera System House Keeping 블록이 재편됐다 — **신설 `DMPTEMP`(DMP 온도) · `WALLBRD`(wallboard 온도 — v0.2 의 `WALLBOAR` 에서 개명) · `HEBOX`(HE box 내부 온도)**, `AIR_IN`/`AIR_OUT`/`GLYC_IN`/`GLYC_OUT` comment 정의 확정(AIR는 열교환기 기준 — IN이 따뜻한 쪽, 레거시 의미 유지), `DEWPRES` 단위 [torr] · 포맷 `x.xxe-x` · **측정불가 sentinel `9.99e-9`**(값 0/이상값/게이지 비숫자 — 규격 5.0 sentinel 표에 DEWPRES 전용 예외로 등재 필요), **`CCDTEMP` 의미 변경**: 구 설계(`CCDTEMP1`·`CCDTEMP2` 평균 파생, D-013)에서 **실측 센서 1개 값**(comment `CCD temperature` — chip 귀속 `M` 은 2026-08-30 제거)으로. `RTD12` 폐지는 확정대로(D-013). **출처 확정(v0.3)** — `CCDTEMP`·`DEWPRES`·`PT30N*`·`CHARCOAL`·`DMPTEMP`·`WALLBRD` = ICG RTD measurement / `AIR_*`·`GLYC_*` = standalone RTD readout unit / `HEBOX` = Radionode sensor | ① converter 가 `DMPTEMP`/`WALLBRD`/`HEBOX` 를 읽지 않음 — MEF 로 보내려면 읽기 추가 ② MEF/L1 의 `CCDTEMP` 정의를 "평균 파생"에서 "대표 센서 실측"으로 갱신 (L1 `CARRY_KEYS` 가 `CCDTEMP` 이름을 요구하므로 이름은 불변) ③ `CCDTEMP1`/`CCDTEMP2` 후보는 **제외 확정**(운영자, 2026-08-21) — 평균 파생 설계 폐기에 따름 ④ ⚠️ **추가 (2026-08-25): `AIR_IN`·`AIR_OUT`·`GLYC_IN`·`GLYC_OUT` 4장이 raw 에서 폐지됐다** (운영자 확정, raw spec v1.5 — 5.6절 18장→14장, 5.10절 폐지 목록 등재). `mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` Thermal/dewar 행이 아직 넷을 싣고 있고 converter 도 pass-through 한다 — **raw 가 공급을 끊으므로 MEF 쪽에서 함께 폐지할지, 다른 공급원을 둘지 LEECU 판단이 필요하다.** standalone RTD 계통이 raw 헤더에서 완전히 비었다 ⑤ ⚠️ **추가 (2026-09-06): 한계 밖·미연결 실측값이 걸러지지 않고 그대로 온다** (raw spec 5.0절 *"실측값은 버리지 않는다"*, 운영자 확정). 온도 카드는 ACF 센서 한계를 넘어도, 채널이 미연결이어도(≈`'-273.20'`) 값이 실리고 sentinel `'-999.99'` 는 **장치가 값을 주지 않은 자리**에만 온다. ⛔ **하류가 이 값을 정상 측정으로 세면 안 되고, 반대로 sentinel 로 접어 버려도 안 된다** — 한계 밖을 감추면 히터 과열 같은 이상 상태가 센서 고장으로 위장된다(그래서 걷은 규정이다). `CCDTEMP` 는 L1 `CARRY_KEYS` 가 이름으로 실어 나르므로 **MEF/L1 쪽 품질 판정이 이 성질을 알고 있어야 한다** — LEECU 확인 대상. ⚠️ `DEWPRES` 만 예외로 범위 밖을 `'9.99e-9'` 로 접는다(위 항목 · C-신설 게이지 Off 행) |
| **C-신설: HK 히터 넷 · `HKUDATE`** (2026-09-04, raw spec v1.10) | raw HK 블록에 **5장이 늘었다** — `HKUDATE`(**guide 유닛 실측값 중 가장 오래된 표본시각**, 19자) 와 듀어 히터 넷 `HTREN`·`HTRSET`·`HTROUT`·`HTRFORCE`. ⭐ `HKUDATE` 의 셈은 `ICG RTD` 7장 + `ICG heater` 넷만이고 **`Radionode` 3장(`HEBOX`·`FSATEMP`·`FSAHUM`)의 표본시각은 넣지 않는다**(운영자 확정 2026-09-08, raw spec 5.6절). 출처 계통 **`ICG heater`** 신설로 HK 공급 계통이 둘 → 셋이 됐다. 값은 층이 갈린다 — `RCONFIG` **되읽기**(`HTREN`·`HTRSET`·`HTRFORCE`, *명령이 아니라 컨트롤러가 받아들인 값*)와 `STATUS` **`MOD10/HEATERAOUTPUT`**(`HTROUT` — FW 1.0.1252 로 키 확인, 측정/명령값 여부 OI-28). ⚠️ `HTROUT`(0~25 V)는 guide 헤더의 `HEATER` 레일(`HEATER_V`, 공칭 +28 V)과 **다른 것**이다 | ① converter 는 5장을 **읽지 않는다** — `DMPTEMP`/`WALLBRD`/`HEBOX` 와 같은 처지(위 HK 온도 항목 ①)라 **MEF 로 보낼지 LEECU 판단**이 필요하다 ② ⚠️ **sentinel 어휘가 늘었다** — HK **상태 낱말**(`HTREN`·`HTRFORCE`)과 HK **전압**(`HTROUT`)의 측정불가는 **`'NC'`** 다(온도의 `'-999.99'` · `DEWPRES` 의 `'9.99e-9'` 와 별개). 하류 파서가 `'NC'` 를 모르면 숫자 변환에서 깨진다 ③ ✅ **다섯 카드 전부 원천이 배선됐다** — `HTROUT` 은 `STATUS` 의 `MOD10/HEATERAOUTPUT`(2026-09-05), `HTREN`·`HTRSET`·`HTRFORCE` 는 HK 한 바퀴(기본 60 s)마다의 `RCONFIG` 되읽기(2026-09-09), `HKUDATE` 는 두 창구가 같은 셈을 쓴다(2026-09-06).  실기에서 실값이 실리므로 ⛔ **하류가 *"구현 전에는 항상 `'NC'`"* 를 전제로 파서를 짜면 안 된다** — `'NC'` 는 되읽기가 실패했거나(ACF 적용 중·파싱 전) 표본이 낡은 구간의 표시다 (raw spec 5.6.2절 · 구 ~~OI-25~~ 종결).  ⏳ 값의 **뜻**(출력단 측정값이냐 명령값이냐)만 아직 미확정이다 — raw spec **OI-28**  ④ ⛔ **`HKUDATE` 로 `HEBOX`·`FSATEMP`·`FSAHUM` 의 나이를 판단하면 안 된다** — 그 셋(`Radionode` 계통)은 시각 셈에서 빠지므로 이 카드보다 최대 600 s 더 낡을 수 있다(raw spec 5.6절, 운영자 확정 2026-09-08).  MEF 로 그 세 값을 올릴 때 `HKUDATE` 를 그 시각으로 쓰면 **어긋난다** — 그 셋의 나이는 raw 헤더만으로는 알 수 없고 ICG 의 HK CSV 에만 남는다 |
| **C-신설: `DEWPRES` 게이지 Off 구간** (2026-09-04, raw spec v1.10) | 진공 이온게이지 필라멘트가 science 영상에 영향을 주므로 **science 노출 중에는 게이지를 끈다**(ICS 가 노출 앞에 `VACGAUGE OFF`, **독출 완료** 뒤 `gauge_reenable_after`(기본 10분)에 `ON` — 셔터 닫힘 기준이 아니다). 그 구간의 `DEWPRES` 는 **`'9.99e-9'`** 이고 이는 **결측이 아니라 의도된 상태**다. ⭐ **sentinel 이 정상인 구간은 셋이다** — ① 끈 동안(끈 것을 **아는 순간부터** 즉시) ② **켠 뒤 예열 중**(`gauge_warmup_wait`, 기본 12 s — 켤 때마다) ③ **연속 노출 사이**(취득 중이면 켜지 않고 켜짐대기로 남긴다). ⚠️ 게이지 상태를 **모를 때는 막지 않는다** | ⚠️ **하류가 이 값을 고장으로 세면 안 된다** — 정상 관측분의 상당수가 그렇게 나온다. ⚠️ **구간이 셋이라 sentinel 이 노출 직후에도, 연속 노출 내내도 이어진다** — "한 노출에 한 번" 으로 가정한 탐지기는 오탐한다. ⭐ `ON` 뒤 첫 실값은 **최악 약 2분** 늦을 수 있다(예열 + 모듈 VCPU 재시작 바퀴). ⛔ **Conductron 함정**: 이온게이지를 꺼도 같은 모듈의 열손실 센서가 값을 계속 내보내고 그 값이 인정 범위 `[1e-8, 1e+3]` 를 **경고 없이 통과한다** — 끈 동안 오는 값을 실으면 *"정상으로 보이는 틀린 값"* 이 남는다. guide FITS 도 같은 게이지라 그 구간에는 **양쪽이 동시에 sentinel** 이다 |
| **C-신설: 반쪽 pair** (2026-09-04, raw spec v1.10 2.1절) | 두 컨트롤러가 **나란히** 프레임을 받고 각자 저장이 끝나는 대로 파일을 내며, **한쪽이 실패해도 성공한 쪽은 저장한다.** 그래서 `…MK.fits` 나 `…NT.fits` **한쪽만 있는 노출 번호가 실재**한다 — 결측이 아니라 의도된 부분 성공이다 | ⚠️ **converter 의 짝 탐색이 이 경우를 오류로 세면 안 된다** — 짝이 없는 노출은 **건너뛰되 실패로 세지 않는 것**이 규격 의도다(7장 체크리스트 2번이 경고로 내려갔다). 현행 짝 탐색이 어떻게 동작하는지 확인 필요 |
| **C-신설: MEF `UT` 조립 원천** (2026-08-21) | raw 가 `TSHOPEN`/`TSHSHUT` 를 싣지 않는 것으로 판정됐다(Header_and_Refs v1.9 3.2절). converter 는 `DATE-OBS` 날짜부 + raw `TSHOPEN` 으로 MEF `UT` 를 조립하므로(`v2_1.py:440` · `:583`) **MEF `UT` 시각부가 빈다** — 오류 없음 | `UT` 조립 원천을 `DATE-OBS` 의 시각부로 교체 (`DATE-OBS` 는 밀리초까지 담는다, D-014) |
| C-신설(경미): MEF `DARKTIME` 공급원 | raw `DARKTIME` 미기재 판정 — 값이 `EXPTIME` 과 동일해 파생으로 충분(v1.9 3.2절). 현행 converter 기본값 `0.0` 이 MEF 에 박힌다 | `EXPTIME` 값으로 파생 기록, 또는 MEF `DARKTIME` 폐지 판단 |
| **C-후보 신설: MEF `VOLTINFO`/`TELEMETRY` 공급원** (2026-08-22) | raw 가 컨트롤러별 텔레메트리 카드 **`C1_TEMP`·`C1_VOLT`·`C1_CURR` / `C2_*`** 를 도입했다(v1.9, 구 `BCKTEMP` 확장) — MEF `VOLTINFO`/`TELEMETRY` 를 실측값으로 채울 원천이 처음 생겼다. converter 는 이 카드들을 아직 읽지 않는다 | 현행 placeholder 경로(C-18)를 raw `Cn_*` 기반 채움으로 **대체**하는 안 — 도입 시 읽기 추가 + 조립 규칙 정의 — **모듈·레일 자리 순서 명세는 raw spec 5.6.1절에 수록됐다** (v1.5, 2026-08-25) |
| (기록) `DATASRC` 값 체계 확장 · chiller 블록 미기재 | `ARCHON`/`SIM` → **`ARCHON_SCIENCE`/`ARCHON_GUIDE`/`SIM`**(`HEMODE` 흡수) · chiller 4장(`CHSTAT` `CHOP` `CHSET` `CHPROC`)은 raw 미기재 **확정**(운영자가 초안에서 삭제, 2026-08-21 · 재삭제 검증 2026-08-22) | converter 는 `DATASRC`/`CHOP`/`CHSET`/`CHPROC` 를 읽지 않고 `CHSTAT` 는 기본값 `""` 경로 — 영향 없음/경미, 기록만 |
| (기록, v0.5) 돔 Source 변경 · `LEDFLASH` 단위 변경 · `ICSBUILD` 형식 변경 | ① 돔 카드(`DSSTAT`~`DSTELAZ`)의 공급원이 `AUX relay` → **`TCS relay or REDIS`**(newTCS 편입), `DALTERR`/`DAZERR` 는 **`ICS calculation`** — 값 공급 계통의 변경이지 카드 이름·형식 변경이 아니다 ② `LEDFLASH` 단위 [seconds] → **[milliseconds] 정수**(운영자 확정 2026-08-22 — 카드 comment 가 단위 명시) ③ `ICSBUILD` 형식 `<프로그램>-v<버전>:<빌드일시>` → **`v<버전>:<빌드일시>Z`**(프로그램 식별은 `DATASRC` 담당) | 셋 다 converter 미독 카드(`LEDFLASH` `ICSBUILD`) 또는 pass-through 값이라 **converter 동작 불변 — 기록만**. 단 하류 도구가 `LEDFLASH` 를 초로 읽지 않게 ICD/정의서 부속 문서에 단위 변경을 전파할 것 |
| **(기록, v0.10) 돔 방위 셋 출처 = 돔 제어 프로그램 redis** (2026-09-11, D-021 · CR-003 · raw spec v1.13) | `DSAZ` · `DSTELAZ` · `DAZERR` 의 공급원이 `TCS relay or REDIS` / `ICS calculation` → **`REDIS (dome control)`** 로 바뀌었다 — 돔 제어 프로그램이 `dome_az` · `dome_tel_az` · `dome_del_az` 에 TTL 수백 ms 로 싣는 값을 ICS·ICG 가 직접 읽고, 키가 없으면 `NC` 다(옛 값을 이어 싣지 않는다). ⭐ **`DAZERR` 의 성격이 계산에서 중계로 바뀐다** — `ICS calculation`(`DSAZ`−`DSTELAZ`, −180~+180 접기)은 `dome_del_az` 만 없을 때의 예비 경로로 남는다. `DALTERR` 는 그대로 `ICS calculation`(고도차, 접기 없음) | **값 공급 계통의 변경이지 카드 이름·형·pass-through 여부의 변경이 아니다 — converter 동작 불변, 기록만.** 단 하류 문서가 `DAZERR` 를 *"ICS 파생값"* 으로 적어 둔 곳이 있으면 **실측 중계값(예비 경로만 파생)** 으로 고칠 것 |
| **(기록, v0.10) `OBSTYPE` 어휘 변경** (운영자 확정 2026-09-09 · raw spec v1.13) | raw `OBSTYPE` 이 `IMAGETYP` 의 사본에서 **어느 계통이 찍었나**로 갈렸다 — science `SCIENCE` · guide `GUIDE`(`OBSTYPE` 명령으로 지정, 대문자로 접음). converter 는 이 값을 **그대로 복사**하므로 **동작 불변**이고, L1 전처리는 `OBSTYPE` 을 읽지 않는다(`IMAGETYP` 만 문자열 비교한다) | ⚠️ **기록만 — converter 수정 없음.** 다만 ① MEF Keywords 정의서 v1.0 의 `OBSTYPE` 설명 *"observation type"* 이 이제 프레임 종류가 아니다(§4 등재) ② `mef_pipeline` 의 시험 고정자료가 `OBSTYPE` 을 `IMAGETYP` 값으로 채워 **옛 규약을 재현**한다 — 하류가 두 카드를 동의어로 보지 않게 LEECU 확인 |

## 1.1 raw spec v1.13 헤더 변경 — science ↔ guide 대비표 (2026-09-12)

**이 판이 헤더에 남기는 변경 전량이다.**  ⭐ **카드 수와 레코드 수는 양쪽 다 안 바뀐다** —
science 값 136장 · 180 레코드 · 14,400 B, guide 값 128장 · 144 레코드 · 11,520 B.
⛔ **converter 동작도 불변**이다 — 이름·형·pass-through 여부가 그대로이고 바뀐 것은
**값·출처·comment** 다.  `×` = 해당 없음.

| # | 카드 · 자리 | science (`MK`·`NT`) | guide (`G`) | 무엇이 바뀌었나 | 규격 |
| ---: | --- | --- | --- | --- | --- |
| 1 | `LEDFLASH` | **유지** (`I`, [ms]) | ⛔ **삭제** | guide 는 점검용 LED 를 쓰지 않는다 | 5.4 · 10.2 · 10.3 |
| 2 | **`TRIGOUT`** | × | ⭐ **신설** — `EXPTIME` 다음, `I`, `1` = 그 프레임의 노출 창에 Trigger Out 이 HIGH 였다.  모르면 sentinel `-1` | `LEDFLASH` 자리를 1:1 로 대신한다 — **장수 불변** | 10.3 |
| 3 | `OBSTYPE` | 값 **`'SCIENCE'`** | 값 **`'GUIDE'`** | ⛔ `IMAGETYP` 의 **사본이 아니다** — *어느 계통이 찍었나* 로 뜻이 갈렸다.  계통 기본값이고 `OBSTYPE` 명령이 덮는다.  **견본 3장의 값도 고쳤다** | 5.4 · 10.3 |
| 4 | `INSTRUME` | 그대로 (`'<SITE> 18k CCD'`) | ⭐ **`'<SITE> Guide CCDs'`** 확정 | OI-24 잔여 하나가 닫혔다 (복수형 `s`) | 10.3 · 10.6 |
| 5 | `FPAID` | 그대로 (사이트 유도) | ⭐ **science 와 같은 사이트 유도** | guide CCD 도 FPA 조립체에 든다 — 종전의 *"귀속 확인 대기"* 가 닫혔다 | 5.3.1 · 10.3 |
| 6 | `FSATEMP` `FSAHUM` | **소수 2자리** (`'+22.35'` · `'47.67'`) | **소수 2자리** | Radionode 원값이 2자리다(실측).  ⛔ *"ENS식 1자리"* 유추는 폐기 — `ENS1`–`ENS7` 은 *"중계 그대로"* 라 출처가 다르다.  ~~OI-16~~ 종결 | 5.0 · 5.8 |
| 7 | `PRESCNX` / `OVRSCNX` | 그대로 (`0` / `48`) | ⭐ **`16` / `0`** | 채널 선두 16 은 **CCD 의 dark reference columns 를 읽은 값**이라 prescan 귀속이다(CU 협의 완료).  ⛔ 합 불변식은 어느 쪽이든 통과하지만 converter 는 **자리로** 영상 좌표를 셈한다 | 9.1 · 9.4 · 10.3 |
| 8 | `CHMAP` comment | × (science 는 `CHMAP_*` 4장) | ⭐ **`[TBC]` 제거** | 5.0절에 *"comment 에 검토 표식을 싣지 않는다"* 를 규범으로 세웠다 — 값의 확정 여부는 문서(OI-21)가 든다 | 5.0 · 10.3 |
| 9 | 블록 `COMMENT` 2장 | **밑줄 추가** | **밑줄 추가** | `Exposure Information`(밑줄 47) · `Camera System House Keeping Data`(밑줄 35) 만 나머지 다섯과 달랐다.  규칙(78열까지)도 5.0절에 명문화 | 5.0 |
| 10 | `HTREN` `HTRSET` `HTROUT` `HTRFORCE` | 카드는 **그대로** | 카드는 **그대로** | ⭐ 바뀐 것은 **원천 배선**이다 — 넷 다 실기에서 실값이 실린다(설정 셋은 HK 바퀴의 `RCONFIG` 되읽기).  ~~OI-25~~ 종결.  ⛔ 하류가 *"구현 전이라 늘 `NC`"* 를 전제하면 안 된다 | 5.6.2 · 8장 |
| 11 | `HKUDATE` | 셈 규칙 **규범화** | 셈 규칙 **규범화** | **guide 유닛 실측 중 가장 오래된 표본시각**이고 `Radionode` 3장은 셈에서 뺀다.  ⛔ 그래서 이 카드로 `HEBOX`·`FSATEMP`·`FSAHUM` 의 나이를 판단하면 안 된다 | 5.6 · 10.4 |
| 12 | `DSAZ` `DSTELAZ` `DAZERR` | 출처 **redis** | 출처 **redis** | 돔 제어 프로그램이 실어 두는 값을 직접 읽는다(**D-021**).  키 TTL 이 지나면 `NC` — 옛 값을 이어 싣지 않는다.  ⭐ **읽는 시점이 다르다**: science 는 노출 개시 1회, guide 는 **프레임마다** | 5.7 · 5.7.3 · 10.1 |
| 13 | `DALTERR` | **불변** (`ICS calculation`) | **불변** | 고도차라 이 결정 밖이다 — ⛔ 방위값으로 덮지 않는다 | 5.7 · 5.7.3 |
| 14 | `DEWPRES` | sentinel 구간 **넓힘** | sentinel 구간 **넓힘** | 게이지 Off 뿐 아니라 **예열·재점등 대기** 구간도 `'9.99e-9'` 다(최악 약 2분).  같은 게이지라 양쪽이 동시에 sentinel | 5.6 · 10.4 |
| 15 | HK 온도 카드 전반 | **실측 보존** | **실측 보존** | 센서 한계 밖·미연결 값(≈`'-273.20'`)도 그대로 싣는다 — sentinel 은 장치가 값을 안 준 자리에만.  ⚠️ 하류는 **물리적으로 말이 안 되는 값**을 만날 수 있다 | 5.0 · 5.6 · 10.4 |
| 16 | (카드 아님) 노출 번호 | **규범 신설** | **규범 신설** | 저장되지 않은 프레임은 번호를 **소비하지 않는다**(**D-022**).  `STOP` 은 저장을 마치므로 먹고, 반쪽 pair 도 한쪽만 저장되면 소비다.  결번 허용 예외 넷 | 2.3-8 · 5.4.1 · 9.2 |

> ⚠️ **하류(LEECU)가 실제로 손댈 것은 둘뿐이다** — ① MEF Keywords 정의서의 `OBSTYPE`
> 설명(*"observation type"* 이 이제 프레임 종류가 아니다) ② `DAZERR` 를 *"ICS 파생값"*
> 으로 적어 둔 자리(실측 중계값으로).  나머지는 **기록**이다.
>
> ⛔ **guide 는 MEF 경로가 없다** (소비자는 `gmon`) — 위 표의 guide 열 변경은 converter
> 에 닿지 않는다.  다만 **7번(`PRESCNX`)은 gmon 의 분할·좌표 셈이 따라야 한다.**

## 2. raw ↔ MEF 키워드 이름 대응 (raw 개명 · 신설분)

raw 쪽 Detector/Amplifier 블록 확정(2026-08-21)으로 이름이 갈라진 것들이다. converter는 이 카드들을 읽지 않으므로 당장 동작은 안 바뀌지만, **C-5 대조를 붙일 때 이 대응이 없으면 어긋남을 잡을 수 없다.**

| raw (신) | MEF / converter 쪽 | 비고 |
| --- | --- | --- |
| `AMPNAX1` = 1200 | `RAWXTILE` | 값 동일, 이름 상이 |
| `AMPNAX2` = 4700 | (없음) | NAXIS2/NEND 타일 규약 값 |
| `IMAGEX` = 1152 | `AMPDATA` | |
| `IMAGEY` = 4616 | (카드 없음 — 상수 `ACTIVE_HALF_ROWS`, amp extension NAXIS2) | |
| `PRESCNX` = 0 (science) / **16** (guide) | `PRESCANX` | 레거시 실측 27과 분리하려고 raw 쪽을 개명 — ✅ 삼자 모순은 **원장 v1.13 확인 요망 10 에서 종결**(키워드 변경 계승, 운영자 확정 2026-08-22).  ⚠️ **guide 는 값이 0 이 아니다** — 채널 선두 16 이 CCD 의 **dark reference columns** 를 읽은 값이라 `PRESCNX=16`·`OVRSCNX=0` 이다(raw spec v1.13 · 10.3절, 운영자 확정 2026-09-08).  guide 는 MEF 경로가 없어 converter 파급은 없지만 **gmon 쪽 분할·좌표 셈은 이 귀속을 따라야 한다** |
| `PRESCNY` = 0 | (없음) | |
| `OVRSCNX` = 48 | `OVERSCNX` | 레거시 실측 32와 분리하려고 raw 쪽을 개명 |
| `OVRSCNY` = 84 | (없음 — `MIDOVSCY`=168=2×84 관계, 분배는 OI-4) | |
| `NAMPDET` = 16 | `AMPPCD`(정의서) | raw는 `NAMPS` · `AMPPCD` 폐지 (Header_and_Refs v1.6 8.1절) |
| `NAMPRAW` = 32 | (없음 — raw 파일 단위 개념) | |
| `CHMAP_LT/LB/RT/RB` | AMPINFO `MODULE` · `CHANNEL` (C-11) | 값 = CCD 출력 채널, **고정 4자 토큰 8개** — `<chip><A\|D><nn>`, 01–08=`A` · 09–16=`D` (raw spec v1.5, 2026-08-25 개정. **구 3자 `M16` 을 파싱하는 코드는 고쳐야 한다**) |
| `DETID` = 'MK'/'NT' | ((TBD)) | MEF 목적지 미정 — 레거시 계승, 값 재정의(pair) |
| `FILENAME` | MEF `FILENAME`(자체 생성) · AMPINFO `RAWFILE` | converter는 raw `FILENAME` **카드**를 읽지 않음(디스크명만 사용) |
| `EXPID` (v1.6 — 구 `ORIGNAME`) | (없음 — 선택 pass-through, §1) | **pair 양쪽 동일** — 짝 탐색 키로 쓸 수 있다 |
| `UNIQNAME` (폐지) | MEF `UNIQNAME` | §1 C-신설 참조 |
| `DMPTEMP` (신설) | (없음 — 도입 시 pass-through 추가) | HK 재구성, §1 참조 |
| `WALLBRD` (신설) | (없음 — 도입 시 pass-through 추가) | 〃 |
| `HEBOX` (신설) | (없음 — 도입 시 pass-through 추가) | 〃 |
| `CCDTEMP` (의미 변경) | MEF `CCDTEMP` (L1 `CARRY_KEYS`) | 평균 파생 → 대표 센서 실측, §1 참조 |
| `TCSTIME` (신설) | (없음) | TCS 시각계 선언 — `TIMESYS`(ICS)와 분리 |
| `CTRL1CFG` / `CTRL2CFG` (신설) | (없음 — raw 전용 설정 포인터) | 버전 문자열 6장을 귀속 (v1.9 3.3절). MEF 목적지 검토는 §6-4 |
| `CAMVER` (신설, v1.9) | (없음 — 도입 시 pass-through 후보) | 카메라 시스템 버전 선언. converter 미독. ⚠️ **값이 올라가도 신호 계통은 그대로일 수 있다** — 듀어 RTD 의 배치·귀속 변경도 범프 사유이기 때문이다(raw spec 4.3절). 이 값을 캘리브레이션 게이팅의 세대 판별에 쓰는 쪽은 `CAMVER` 값↔구성 대장(raw spec OI-29)으로 HW 세대 변경과 RTD 재배치를 갈라 봐야 한다 |
| `RDMODE` (신설, v1.9) | MEF `READMODE`(`'64AMP'`) 와 **별개 — 대응 없음** | raw 독출 속도 모드 선언. 구 `READMODE` 이름 충돌의 해소형(§3 참조). converter 미독 |
| `C1_TEMP`·`C1_VOLT`·`C1_CURR` / `C2_*` (신설, v1.9) | MEF `VOLTINFO`/`TELEMETRY` (C-후보, §1) | 컨트롤러별 텔레메트리(구 `BCKTEMP` 확장). converter 미독 — 도입 시 pass-through 후보 |

## 3. ICD v4.1 개정 후보

- **`OVERSCNY` 이름 위험의 문서화 (v1.10 지시)**: 레거시 `OVERSCNY` 는 가장자리 Y overscan(값 0), 신규는 **영상 중앙**(168행) — 이름을 물려주면 "위쪽 N행 자르기" 도구가 active 픽셀을 지운다. raw 는 **`OVRSCNY`**(amp 당 84, frame-center side)로 개명해 잘림을 방지했다. **ICD/정의서에 이 위험 사유와 개명 사실을 기록**해 하류 도구 작성자가 레거시 이름을 재사용하지 않게 할 것 (MEF 는 `MIDOVSCY` 계열 유지).
- **§12 (open items)**: raw 텔레메트리 집합의 위임 대상이 구 규격 5장 → 재작성판으로 바뀐다. 참조 갱신.
- ~~**`READMODE` 값 충돌**: ICD/정의서는 `READMODE='64AMP'`(구조 선언), raw 초안은 `'FAST'`(독출 속도 모드)로 쓰려 했다 — 같은 이름, 다른 뜻. 이름 분리 필요~~ → **해소(v1.9)**: raw 쪽이 **`RDMODE`** 로 개명 도입되어 이름이 갈라졌다 — MEF `READMODE='64AMP'` 는 그대로, **ICD 개정 항목 없음**.
- **AMPINFO의 상류 공급원 명시**: "authoritative 64-row map"의 배선 열(MODULE/CHANNEL)이 converter 추정식이 아니라 **raw `CHMAP_*` + 재작성판의 amp 전수 표**에서 온다는 것을 명시.
- **overscan 좌우 패턴 — 종결(2026-08-22)**: 신규는 **`RRRRLLLL`(4:4) 확정**이다(실제 획득 자료 육안 확인, raw spec 4.1절). 레거시 MEF `AMPSEC` 의 M/T=5:3 · K/N=3:5 는 레거시 계통의 관찰이므로 신규 L0 에 적용하지 말 것 — ICD·정의서가 레거시 패턴을 전제하고 있으면 갱신 대상이다. geometry 가 바뀌면 **raw 쪽은 `CAMVER`(HW)/`CTRLxCFG`(설정) 범프 · MEF 쪽은 `GEOMVER` 동반 범프** — `RAWVER` 는 미도입 확정이다(Header_and_Refs v1.13 확인 요망 11: 규격/구성 버전은 `CAMVER`·`CTRLxCFG`·`DETID`·`CHMAP_*` 조합으로 파악).
- ⚠️ **파일명 `<SITE>` 넷째 코드 개정 (D-017, 2026-08-25) — ICD §2.1 갱신 필요.** `KMTT`(TESTBED) → **`KMTK`(KASI)**. **converter 정규식 `^(KMTC\|KMTS\|KMTA\|KMTT)\.` 의 넷째 대안을 바꾸지 않으면 KASI 자료가 `find_pair()` 에 걸리지 않는다.** L0 MEF prefix `kmtt`→`kmtk` 도 함께. **형식(필드 폭·구분자·6자리 zero-padding)은 불변**이고 바뀐 것은 코드 하나다.
- **번호 공간 확대 (D-018, 2026-08-25)**: `000000`–`099999` → **`000000`–`999999`**. 정규식이 `\d{6}` 이라 **converter·ICD 형식 영향은 없다** — 다만 "앞자리가 항상 `0`" 을 전제한 도구가 있다면 그건 깨진다.
- 충돌 번호 증가 시에도 파일명 형식은 같고 번호만 다르다.

## 4. MEF Keywords 정의서 v1.0 개정 후보

- **`XTALKVER` · `REFVER` · `CATVER` 의 계층 규칙 (운영자 확정 2026-08-22)**: 이 셋의 정본은 **pipeline calibration DB** 다(C-14) — HW·성능 변화 없이도 pipeline setup 에서 바뀔 수 있는 값이라 raw 는 싣지 않는다. **전처리 전 MEF(L0)에 넣을지는 pipeline 팀 판단**이고, **전처리 후 산출물(L1)에는 필수**다 — 보정에 실제 적용한 버전이므로. 정의서/ICD 에 이 계층을 명시할 것.
- `UNIQNAME` 항목: 공급원 변경 또는 폐지(§1 C-신설과 연동).
- `NAMPS`=64 · `AMPPCD`=16: raw 쪽 폐지(v1.6 8.1)와의 관계 명시 — MEF 유지 여부는 LEECU 판단(MEF는 카메라 전체 관점이라 유지가 자연스러울 수 있음).
- ⚠️ **Thermal/dewar 행에서 `AIR_IN`·`AIR_OUT`·`GLYC_IN`·`GLYC_OUT` 4장의 거취 (2026-08-25)**: raw spec v1.5 가 이 넷을 **폐지**했다(5.6절 18장→14장, 5.10절 등재). 정의서 v1.0 은 아직 넷을 싣고 converter 도 pass-through 한다 — **raw 가 공급을 끊으므로 MEF 에서도 폐지할지, 다른 공급원을 둘지 LEECU 판단이 필요하다.** 이로써 `standalone RTD readout unit` 계통이 raw 헤더에서 완전히 비었다(공급은 `ICG RTD`·`Radionode` 둘만 남는다).
- **사이트별 상수표 신설 (D-017 항목 6, raw spec 5.3.1절)**: `TELESCOP` = CTIO `#1` · SSO `#3` · SAAO `#2` · KASI `#0` / `FPAID` = CTIO `FPA#2` · SSO `FPA#1` · SAAO `FPA#3` · KASI `FPA#0`. ⚠️ **망원경 번호와 FPA 번호는 관측소 셋 모두 어긋난다** — MEF 쪽에서 둘을 맞추는 파생을 넣으면 검출기 귀속이 틀어진다.
- **`OBSTYPE` 정의 갱신 (운영자 확정 2026-09-09)**: raw `OBSTYPE` 은 프레임의 종류가 아니라 **관측 계통**(`SCIENCE`/`GUIDE`)이다 — 정의서 v1.0 의 *"observation type"* 설명을 갱신하고, `IMAGETYP` 의 동의어로 읽는 하류 코드가 없는지 확인할 것.
- (기록) 레거시 MEF의 `AMPNAME2`('im16')가 배선 identity를 헤더에 실은 선례 — `CHMAP_*` 채택의 계보.

## 5. 미결(OI-*)과의 연동

| OI | 이 검토와의 접점 |
| --- | --- |
| OI-3 (`ROWORDR`/`RDDIR*`) | 포장 규범 조항 이관 후 flat/star 시험은 "사실 확인"이 아니라 **준수 검증**이 된다 |
| OI-4 (중앙 168행 분배) | raw `OVRSCNY`=84는 타일 규약 값이다. 물리 분배는 실측 후 `MIDOSCT`/`MIDOSCB`로 |
| ~~OI-17 잔여 ①·②~~ | **종결 (2026-08-25)** — 운영자가 **채널 번호 = OS 번호**를 확정(잔여 ②)했고, 그로써 `채널 09–16 = OS9–16 = 위 half = 섹션 D` 가 e2v 데이터시트까지 이어져 `IMGSEC` 의 `B-BOT` 16행이 **`D-BOT`** 으로 정정됐다(잔여 ①). 기계 정본이 `Detector_Ch_to_AmpID_Map_v1.1.txt` 로 판올림됐다 — **구 v1.0(3자 토큰·`B-BOT`)을 읽는 도구는 고쳐야 한다.** 잔여는 ③(K·N 조 180° 회전 장착 확인)뿐 |
| OI-13 (셔터 반영 지연) | 재질의 지연이 **3초 → 1초**로 바뀌었다(운영자 2026-08-25, raw spec 5.7.1절). `AUXQDATE` 가 `DATE-OBS` 뒤로 가는 경로의 문턱도 `EXPTIME > 1 s` 로 함께 내려간다 |
| ~~(신규 제안)~~ | ~~X overscan 패턴 4:4 vs 5:3 검증~~ — **종결(2026-08-22)**: 실제 획득 자료 육안 확인으로 `RRRRLLLL`(4:4) 확정 (raw spec 4.1절) |

## 6. MEF/converter 쪽 미결 안건 (v0.5 신설 — 구 검토 문서에서 이관)

구 검토 문서(raw ↔ MEF 키워드 대응표)의 팀원 검토 요청 항목 중 Header_and_Refs 사이클이 흡수하지 않은 **MEF/converter 쪽 안건 4건**이다. 이 이관으로 그 문서의 살아있는 내용은 전부 흡수됐고 문서 자체는 폐기됐다(운영자 재가 2026-08-22) — 판정 준거는 Header_and_Refs **0장**으로 편입됐다.

1. **`NCTRL` 정의** — converter 가 `2` 를 하드코딩한다(`v2_1.py:410`). **과학 2대만 센 값**인데 Archon 은 3대(과학 2 + 가이드 1)다. `NCTRL` 이 "과학" 인지 "전체" 인지 ICD 침묵 구간이라 정의가 필요하다.
2. **`CTRLID` 개칭 검토** — MEF amp `CTRLID`/`TELEMETRY.CTRLID` 는 색인 정수(`1`/`2`)인데 raw/MEF PRIMARY 의 `CTRL1ID`(식별자 **문자열** `'KMTA-SCI-101'`)와 이름이 너무 닮았다. `CTRLIDX` 등 개칭 검토.
3. **`SATURAT` ↔ `SATLEVEL` 통일** — converter **내부에서** 이름이 갈린다: amp 헤더는 `SATURAT`, `AMPINFO` 컬럼은 `SATLEVEL`. 어느 쪽으로 통일할지.
4. **`DATASRC` · 설정 포인터의 MEF 목적지** — ① `DATASRC` 는 **시뮬 프레임이 실측으로 오인되는 것을 막는 유일한 카드**인데 L0 MEF 에 자리가 없다 — pass-through 신설 여부. ② 설정 provenance 포인터는 구 `ACFFILE` 이 폐지되고 **`CTRL1CFG`/`CTRL2CFG`** 로 대체됐는데(v1.9) 역시 MEF 목적지가 없다 — MEF 에도 자리를 만들지.

> 나머지도 흡수 완료다 — **판정 준거·구간 산정**은 Header_and_Refs **0장**, **카드 전수 대응표**는 같은 문서 각 장의 `Use in MEF` 열(구 `MEF 목적지`), **MEF 표 HDU 컬럼**은 원래부터 MEF 규격(ICD v4.1 §8 · Main_Keywords) 소관이다. 재작성판 V1 의 amp 전수 표·기계 사본은 `__reference/Detector_Ch_to_AmpID_Map` 계열이 원자료다.

---

# Part 2 — raw 파일 번호 · 정체성 · 충돌 처리 (파급 요약)

> **정본 이동 완료**: 설계 전문은 **raw spec 2.3절**([`KMT_CEU_Raw_FITS_Specification_v1.13.md`](KMT_CEU_Raw_FITS_Specification_v1.13.md))과 DECISION_LOG **D-016**(Accepted, 2026-08-22)이다. 이 Part 는 MEF/구현 쪽 파급만 남긴다 — 골자: 충돌 시 노출 번호 증가(공간 **000000–999999**, 선검사, 상한 **1000000회** — **D-018**, 2026-08-25 로 구 `099999`·100000회를 대체) · `FILENAME`(유일 키) + `ORIGNAME`(불일치 = 충돌 신호) · `UNIQNAME`/`NAMECLSH`/`clash/`/`PAIRFILE`/`CTRLTAG` 폐지 · **저장되지 않은 프레임은 번호를 소비하지 않는다**(raw spec 2.3절 8항, 운영자 확정 2026-09-07 — 아카이브 번호는 연속이 원칙이고 결번은 예외 넷뿐이다).

> ⚠️ **아카이브·색인 도구에 주는 뜻** — 노출 번호의 **구멍은 정상 상태가 아니다**(예외 넷: 취득 SW 내부 오류 · 번호 공간 고갈 · 번호 기록 파일 읽기 실패 · 종료 저장 상한 초과). 그러나 **연속성을 무결성 판정의 근거로 삼지는 않는다** — 구멍의 뜻은 그때의 ICS 로그가 정하고, 파일 쪽 유일 키는 여전히 `FILENAME` 이다.

## 1. 하류 도구 요구사항

- 충돌 필터는 **raw 헤더 층**(아카이브 색인 · DTS · QL)에서 **`FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값 ≠ `EXPID`** 로 돈다 (v1.6 — 구 `FILENAME ≠ ORIGNAME`). 재저장 유령 중복은 fail-open — 이 필터가 거른다는 전제가 요구사항이다.
- 아카이브 근거는 **`FILENAME`(+`EXPID`)**. pair 쪽 식별은 `FILENAME` 의 `DETID` 필드 `.MK`↔`.NT` 치환 — **또는 `EXPID` 가 양쪽 같으므로 그 값으로 묶어도 된다** (v1.6).
- MEF 층 필터가 필요해지면 converter 변경점에 `EXPID` pass-through 를 추가한다 (Part 1 §1).

## 2. MEF / converter 연동

converter(v2.4.0)는 raw `UNIQNAME` 을 읽어 MEF `UNIQNAME` 으로 옮긴다(`v2_1.py:423` — v2.3.0·v2.4.0 증분으로 행이 밀렸다). 폐지 후 이 값은 **오류 없이 빈 문자열**이 된다 — 대응은 C-항목으로 LEECU 이관 (Part 1 §1).

## 3. ics_sim 구현 영향 (구현 일감)

| 파일 | 변경 |
| --- | --- |
| `rawpair.py` | 선검사 루프(되감음 · 상한 100000회 → **D-018 로 1000000회**) 신설, clash 격리 로직 제거, `UNIQNAME` 제거, `ORIGNAME` 항상 기록 (**v1.6 에서 `EXPID` 로 대체 — 반영은 `ics-archon-v1.0-build` 몫**) |
| `state.py` | 확정 N 으로 카운터 동기화, **000000–999999 순환** (D-018, 2026-08-25 — 구 `099999`) · **`rewind_expnum()`** — 저장 못 한 프레임의 번호 기록 되감기 (raw spec 2.3절 8항, 2026-09-07. 반영은 `ics-archon-v1.0-build` 몫 — 이미 들어가 있다) |
| `sequencer._store()` | 확정된 이름만 수령 (이름 결정은 rawpair 몫) |
| `tests/test_raw_header.py` | `UNIQNAME` 필수 목록 제거·RETIRED 추가, `NAMECLSH` 시험 교체, 평시 `FILENAME`==`ORIGNAME` 불변식(**v1.6: `DETID` 필드 뗀 값 == `EXPID`**), 충돌·되감음·상한 시험 신설 |

---

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| raw 헤더 카드 판정 원장 | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.19.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.19.md) |
| 1위 준거 ICD | [`../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.2.md`](../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.2.md) |
| MEF keyword 정의서 | [`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`](../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md) |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) (v2.4.0) |
| **raw spec (현행)** | [`KMT_CEU_Raw_FITS_Specification_v1.13.md`](KMT_CEU_Raw_FITS_Specification_v1.13.md) — 구판(v1.2 구명 Pair_Spec · v1.3)은 `archive/` |
| 전신 문서 | `archive/KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.4.md` · `archive/KMT_CEU_Raw_Numbering_and_Identity_v0.2.md` |
| 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |
| 검토 진행 상태 | [`SMC_CLAUDE.md`](SMC_CLAUDE.md) |

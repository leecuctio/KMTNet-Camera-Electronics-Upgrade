# raw FITS ↔ MEF FITS 키워드 대응표 (검토용 v0.7)

**상태: 검토용 — 규격이 아니다.** 팀원 간 검토 후 확정 사항을 `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 5장에 반영한다. 등재는 ACTION_REGISTER **ACT-011**.

작성 2026-08-13 · 개정 2026-08-18 · **저장소 실물에서 기계적으로 추출**했다

> **v0.7 에서 바뀐 것 — raw 쪽 기준선을 레거시 raw 실측본으로 바꿨다.** v0.5 는 raw 열을 `ics_sim` 이 현재 쓰는 헤더에서 뽑았다. **`ics_sim` 은 미완성 구현이고 이 검토가 끝난 뒤 규격대로 다시 구현할 대상**이므로, 그 출력을 raw 쪽 사실로 삼으면 근거가 또 순환한다. raw 열은 이제 `KMTNk.20170209.044131.Rawheader.txt` **레거시 raw 실측 헤더(keyword 123개)** 를 기준으로 판정하고, 거기 없는 카드는 `ᴺ` 로 표시했다(4장).
>
> **그 결과 v0.5 의 "구현 구멍 16개" 가 두 부류로 갈라졌다.** `DSUP` `DSLW` `DSSAF` `DSAUTO` `DSALT` **다섯은 레거시 raw 에 이미 있다** — 설계에 있는 것을 `ics_sim` 이 아직 안 쓸 뿐이라 **결정할 것이 없고 계승하면 된다.** 나머지만 진짜 신규 판단 대상이다(2.3절).
>
> **함께 세운 것 — 준수 우선순위.** v0.5 는 *"코드가 최종본이다"* 라고 선언하고 문서와 코드를 대등하게 놓았다. 그 틀에서는 converter 의 placeholder 가 *"정본이 그렇다"* 로 읽혀 **ICD 미준수를 미준수라고 부를 수 없었다.** v0.7 은 0장에 순위를 세우고 그에 맞춰 1.1 · 2장 · 3.0절을 다시 짰다. **대응표(4장)의 행 구성 자체는 v0.5 와 같다** — 판정의 틀과 raw 열의 뜻이 바뀌었다.
>
> (v0.6 은 준수 우선순위만 세운 중간판이었다. v0.7 이 그 내용을 온전히 포함하므로 저장소에는 남기지 않았다.)
>
> 함께 바로잡은 것 둘: (1) 버전 문자열 9종이 *"`__reference/` 문서에도 없다"* 는 **사실이 아니었다** — 정의서에 값까지 있다(2.4절). (2) **레거시 MEF 헤더를 판정 근거로 쓴 자리**를 배경지식으로 내렸다(0.1 · 2.4 · 5.4절).

> **읽는 순서**: 3장에서 Archon 관련 카드를 그룹별로 훑고(검토 포인트가 붙어 있다), 필요하면 4장 전수 표에서 개별 카드를 찾는다. 결정이 필요한 것은 5장에 모았다.

## 0. 준수 우선순위와 뽑은 방법

### 0.1 무엇을 따르는가 — 순위

**검토 대상 MEF 는 `mef_converter/` 의 변환 코드가 만드는 L0 MEF 다.** 그 헤더가 무엇을 담아야 하는지를 정할 때 아래 순위를 따른다.

| 순위 | 무엇 | 현행성 | 이 검토에서의 지위 |
| --- | --- | --- | --- |
| **1** | `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` | **현행** (2026-08-10 신규 개정) | **준거.** 어긋나면 아래가 틀린 것이다 |
| **2** | `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) | 현행 | **검토 대상 L0 MEF 의 산출 주체.** 아래 0.2 참조 |
| **3** | `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` | **부분 갱신** | 참고. 단 **PRIMARY keyword 층의 유일한 문서 근거** |
| — | `KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` | **미갱신** | **판정 근거로 쓰지 않는다.** 작업 이력 기록 |
| — | `__reference/Legacy raw fits header samples/` 의 **MEF** 헤더 33건 | — | **배경지식.** 판정 근거가 아니다 |
| **raw 기준선** | 〃 의 **raw** 헤더 1건 — `KMTNk.20170209.044131.Rawheader.txt`, keyword **123개** | 2017→2021 사실상 불변 | **raw 쪽이 실제로 무엇을 싣는지의 기준선이다.** 계승 판정(규격 5.13절)의 근거이자 **4장 raw 열의 출처** |
| — | `ics_sim` 의 현재 헤더 출력 | **미완성 구현** | **판정 근거로 쓰지 않는다.** 이 검토가 끝난 뒤 규격대로 다시 구현할 대상이므로, 현재 출력을 raw 쪽 사실로 삼으면 근거가 순환한다 |

3위가 3위인 이유는 그 문서가 스스로 밝힌다 — 머리말이 *"기준 converter: `…v2_1.py` v2.2.0"* 이다. **converter 를 따라 적은 파생물이므로 원본보다 위일 수 없다.**

> ⚠️ **`__reference/` 사본 둘은 ICD v4.1 대조를 거치지 않았다.** 원본이 `mef_fits_spec/` · `mef_converter/` 에 있는 바이트 동일 사본이므로 **이 검토에서 고치지 않는다.** 상태만 적어 둔다.
>
> | 사본 | 확인된 상태 |
> | --- | --- |
> | `Main_Keywords v1.0` | ICD v4.1 개정 커밋에서 **8줄만 바뀌었다** — 머리말 기준 버전 2줄 + `MKFILE`/`NTFILE` 예시 파일명 2줄. 본문 대조 흔적이 없고 버전·작성일이 `v1.0`/`2026-06-22` 그대로라 **겉보기로는 미개정으로 읽힌다.** 본문에 `CREATOR`=`…_v2.1.1` · `PIPEVER`=`…-v2.1.1` 잔재가 남아 있다 (converter 실제 값은 `v2.2.0`. `PRODVER`=`v2.1.1` 은 코드가 의도적으로 고정한 것이라 맞다) |
> | `Work_Summary v1.0` | **2026-06-22 이후 갱신되지 않았다.** 기준 ICD 가 `v4.0.docx`, 파일명이 `KMTN.*`(D-011 이전), converter 가 `v2.1.1` 이다. 특히 **NT 헤더를 *"Header metadata may be minimal"* 이라 적고 있는데 이는 ICD v4.1 §2 가 OI-8 로 뒤집어 금지한 서술이다** |

### 0.2 순위 2위(converter)는 둘로 갈라 읽는다

converter 는 **준거이면서 동시에 수정 대상**이다. 한 낱말로 부르면 C-11 · C-12 · C-17 · C-18 을 무엇이라 불러야 할지 정해지지 않는다.

| converter 의 무엇 | 지위 |
| --- | --- |
| **산출물 구조** — HDU 구성, 카드 이름, 표 컬럼 | **준거 2위** |
| **값을 채우는 동작** — 읽음 / 하드코딩 / placeholder (3.0절) | **미완 구현.** 준거가 아니다 |

### 0.3 ICD 가 침묵하는 구간이 있다 — 이 검토의 과녁

**ICD v4.1 에는 PRIMARY keyword 목록이 없다.** 규정하는 것은 구조(§5) · amp section(§7) · `AMPINFO` 컬럼군(§8) · 표 역할(§9)이다. 그래서 두 구간을 갈라 읽어야 한다.

| 구간 | 판정 방법 |
| --- | --- |
| **ICD 가 규정한 구간** | converter 는 구현체다. 어긋나면 **converter 가 틀린 것**이고, 판정이 자동으로 나온다 |
| **ICD 가 침묵하는 구간** | converter 는 정본이 아니라 **"현재 구현"** 이다. **이 구간이 곧 이 검토가 결정해야 할 곳**이다 |

5장 검토 요청 10항목 중 **4(버전 문자열 9종) · 5(`NCTRL`) · 6(`DATASRC`) · 7(`ACFFILE`)** 이 정확히 침묵 구간에 있다. 구간 크기는 2.1절에서 센다.

### 0.4 카드를 어디서 뽑았나

| 무엇 | 어디서 | 왜 |
| --- | --- | --- |
| **MEF 키워드** | `mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` **코드** | 검토 대상 L0 MEF 를 실제로 만드는 것이 이 코드다. **다만 "코드가 정본"이라는 뜻은 아니다** — 0.1 · 0.2 참조 |
| **raw 키워드** | `__reference/Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt` — **레거시 raw 실측 헤더 123개** | **정착된 설계다.** 신규 raw 가 무엇을 계승하고 무엇을 새로 만드는지가 여기서 갈린다 |
| 참고 (근거 아님) | `ics_sim` 의 `rawhdr` · `rawpair` · `telemetry` 출력 | **미완성 구현이다.** 현재 무엇을 쓰는지는 3장 `converter` 열 옆의 참고 사항일 뿐, raw 쪽 사실이 아니다 |
| 준거 대조 | `mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` (1위) · `…Main_Keywords_Final_v1.0.md` (3위) | 0.1 의 순위대로 |

추출은 `card(...)` 호출을 **괄호 균형으로 파싱**하고 줄번호로 HDU 에 귀속시킨다 — 처음에 함수별로 잘라 파싱했다가 `extra_cards=[…]` 안의 5장(`GEOMVER` `TELSTAT` `NAMP` `NXTALK` `EXTTYPE`)을 놓쳤다.

> **용어**: 이 문서에서 **`L0 MEF`** 는 converter 가 만드는 검토 대상 산출물이고, **`레거시 MEF`** 는 `xkmta.20170209.*` 실측 헤더다. 둘을 그냥 "MEF" 로 부르지 않는다 — v0.5 에서 이 둘이 섞여 2.4절의 오류가 생겼다.

## 1. 요약

| | 개수 |
| --- | ---: |
| MEF 키워드 (converter 코드가 만드는 것) | **236** |
| 대응표가 다루는 raw 카드 | **188** |
| 양쪽에 있는 것 | **135** |
| MEF 에만 | **101** |
| raw 에만 | **53** |

raw 쪽 188개를 **레거시 raw 실측본 123개**에 대면 이렇게 갈린다 (v0.7, 1.2절):

| | 개수 |
| --- | ---: |
| 레거시 raw 에 **있다** — 계승 대상 | **101** |
| 레거시 raw 에 **없다** — 신규 제안, 이번 검토가 정할 것 (`ᴺ`) | **84** |
| FITS 표준 카드라 별도 (`ᶠ`) | **3** |

표기: `ᴬ` = AUX/TCS 중계(pass-through) · `ᶠ` = FITS 표준 카드 · **`ᴺ` = 레거시 raw 실측본에 없는 신규 카드**

### 1.1 이름 합의가 안 된 상태다

**raw 헤더의 Archon setup·구성·유닛 텔레메트리 카드 이름을 취득 SW 쪽에서 일방적으로 정했다.** 이름과 카드 구성을 확정하기 전에 대조가 필요하다.

확인된 사실:

| | |
| --- | --- |
| 준거 문서(0.1 의 1·3위)가 정의하는 것 | **L0 MEF 목적지** — `VOLTINFO` 컬럼 6/6, `TELEMETRY` 컬럼 5/5, `AMPINFO` 컬럼 3/3 모두 정의됨 |
| 준거 문서가 정의하지 않는 것 | **raw 쪽 카드 이름** — `VOLTN`·`VSET<n>`·`VMEA<n>` 0/5, `CTRLFW`·`BCKTEMP`·`ACFFILE` 0/7, `AMPMAP`·`AMOD`·`ACHN` 0/3 |

ICD 와 정의서는 L0 MEF 가 무엇을 담아야 하는지를 정하고 raw 쪽은 다루지 않는다 — raw 쪽을 정하는 것이 `raw_fits_spec/` 이므로 당연한 상태다. 문제는 **목적지는 합의됐는데 출발지 이름은 합의되지 않았다**는 것이다.

> **미루면 비싸지는 이유**: 실기가 이 이름으로 자료를 쌓기 시작한 뒤 converter 쪽에서 다른 이름을 고르면, 그때까지의 아카이브는 **영구히 읽히지 않는다.** 파일명·`OBSERVAT` 처럼 되돌릴 수 없는 부류다.

### 1.2 raw 쪽 기준선은 레거시 raw 실측본이다

**`ics_sim` 이 지금 무엇을 쓰는지는 raw 쪽 사실이 아니다.** 미완성 구현이고, 이 검토의 결론대로 다시 구현할 대상이다. 그 출력을 근거로 삼으면 *"취득 SW 가 정한 이름을 취득 SW 의 출력으로 확인하는"* 순환이 된다 — 2.4절의 버전 문자열과 같은 종류의 오류다.

그래서 raw 쪽 기준선은 **레거시 raw 실측 헤더**다. 2017→2021 사실상 불변이어서 **정착된 설계**로 읽을 수 있다.

| | 개수 |
| --- | ---: |
| 레거시 raw 실측 keyword (`COMMENT` 제외) | **123** |
| 그중 converter 가 실제로 읽는 것 | **78** |
| converter 가 읽는데 **레거시 raw 에 없는 것** | **26** |

converter 가 raw 에서 읽으려는 keyword 는 모두 **104개**이고, 그중 78개는 레거시가 이미 싣던 것이라 **계승하면 끝난다.** 남은 26개가 2.3절이다.

> 이 갈래가 규격 5.13절(계승 · 개칭 · 폐지 판정, D-013)과 같은 근거 위에 선다. 5.13 이 *레거시 카드를 어떻게 할 것인가*를 정했다면, 여기 26개는 *레거시에 없던 것을 새로 만들 것인가*를 정한다.

## 2. 준거 대비 현재 상태

0.1 의 순위로 읽는다. **2.1 이 침묵 구간의 크기**를, 2.2 가 ICD 규정 구간의 미준수를, 2.3 이 취득 SW 쪽 구멍을, **2.4 가 v0.5 의 사실관계 오류 정정**을 담는다.

### 2.1 이름은 다르지 않다 — 갈리는 것은 준거다

converter 가 `card()` 로 만드는 **헤더 카드 이름 210개** 중 3위 정의서에 정의가 없는 것은 **3개**뿐이고(`COMMENT`·`END`·`TFIELDS`, 전부 FITS 구조 카드) 반대 방향(문서에만 있고 코드가 안 만드는 것)도 없다 — `GEOMVER`·`TELSTAT`·`NAMP`·`NXTALK` 는 표 HDU 의 `extra_cards` 에서 실제로 만들어진다. **converter 가 문서 밖 이름을 발명한 사례는 없다.**

(1장의 `236` 은 표 컬럼까지 포함한 수이고, 여기 `210` 은 `card()` 호출로 만드는 헤더 카드 이름만 센 것이다.)

**그런데 같은 210개를 1위 준거인 ICD v4.1 에 대면 36개만 나오고 174개(83%)가 없다.**

| ICD v4.1 에 | 개수 | 성격 |
| --- | ---: | --- |
| 등장한다 | **36** | **전량이 §7 amp section · §8 `AMPINFO` 컬럼 · geometry 계열**이다 — `DATASEC` `BIASSEC` `CCDSEC` `DETSEC` `AMPSEC` `TRIMSEC` `AMPID` `CHIPID` `STRIPID` `ENDID` `MODULE` `CHANNEL` `CTRLID` `READDIR` `CHIPFLP` `STRIPDIR` `GAIN` `RDNOISE` `LINMAX` `RAWFILE` `RAWDATA` `RAWBIAS` 등 |
| 없다 | **174** | **PRIMARY 의 관측·provenance·환경 keyword 전량** |

그러니 이 검토의 대립은 이름 충돌이 아니라 **준거의 공백**이다. 판정이 두 갈래로 갈린다(0.3절):

- **ICD 가 말하는 36개 구간** — 어긋나면 converter 가 틀린 것이다. 2.2 · 2.3 이 이 구간이다.
- **ICD 가 침묵하는 174개 구간** — converter 의 현재 동작은 "사실"일 뿐 "정본"이 아니다. **5장 검토 요청 대부분이 여기 있다.**

### 2.2 ICD 규정 구간의 미준수 — 준거는 실측을 요구하는데 코드는 고정값을 쓴다

| MEF 위치 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | 코드가 넣는 값 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | 문서가 요구하는 것 &nbsp; | 변경점 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| --- | --- | --- | --- |
| `TELEMETRY` 표 전체 | `FWVERSION='UNKNOWN'` ·<br>`BOARDTEMP=-999.0` ·<br>`READTIME=-1.0` ·<br>`STATUS='UNKNOWN'` ·<br>`ERRORFLAG=-1` | 컨트롤러 실측 | **C-18** — `telemetry_rows()` 가<br>**헤더 인자를 아예 안 받는다** |
| `VOLTINFO` 표 전체 | 9행 모두 `SETPOINT=0.0` ·<br>`MEASURED=0.0` ·<br>`STATUS='UNKNOWN'` | 전압 실측 | **C-18** — `volt_rows()` 도 헤더 인자 없음 |
| `XTALKINFO` 표 전체 | 4096행 모두 `0.0` ·<br>`'UNMEASURED'` ·<br>`'PLACEHOLDER'` | calibration DB | 규격 5.12 가 caldb 소관으로 정리 |
| amp `MODULE` / `CHANNEL` | `1+(amp-1)//8` · `1+(amp-1)%8`<br>**추정식** (소스가 스스로<br>*"placeholder"* 라 적었다) | 실제 배선 | **C-11** — 틀리면 `XTALKGROUP` 이 틀려<br>**crosstalk 계수 측정이 무의미해진다** |
| amp `READDIR` | `amp<=8` 이면 `-Y` 하드코딩 | raw `RDDIRT` /<br>`RDDIRB` | **C-12** |
| `AMPINFO` 표 헤더<br>`TELSTAT` | `'UNKNOWN'` 고정 | 양쪽 `CTRLSTAT` 에서<br>파생 | **C-15** |
| PRIMARY `CONTROLL` ·<br>`NCTRL` · `TIMCONF` ·<br>`WBTYPE` · `ELECSYS` ·<br>`SIGELEC` | 소스에<br>**문자열 리터럴로 하드코딩**<br>(`:409`,`:410`,`:417`~`:420`) | raw 헤더에서 | raw 값이 현재 미사용. 사이트별로 갈리는 순간<br>필요해진다 |
| `TELEMETRY` 표 2번 row | MK 헤더만 읽어 채울 근거가<br>없다 | 컨트롤러 2대분 | **C-17** — `convert()` 가 `mk_hdr` 하나만<br>넘긴다 |
| geometry 선언 전체 | 읽지 않고 자기 상수를 쓴다 | raw 선언과 대조 | **C-5 · C-13** |

### 2.3 converter 가 읽는데 레거시 raw 에 없는 것 — **신규로 만들지 정해야 하는 26개**

converter 가 `v("KEY", "")` 로 raw 에서 읽는 keyword 104개 중 **레거시 raw 실측본에 없는 것이 26개**다.

> ⚠️ **v0.5 정정.** v0.5 는 이것을 *"`ics_sim` 이 쓰지 않는 16개"* 로 셌다. 기준을 미완성 구현에 둔 탓에 **성격이 다른 둘이 한 묶음에 들어가 있었다** — 아래 표의 "계승" 행이 그것이다. `DSUP` `DSLW` `DSSAF` `DSAUTO` `DSALT` 다섯은 **레거시 raw 에 이미 있으므로 결정할 것이 없다.** `ics_sim` 이 아직 안 쓸 뿐이고, 그것은 구현 일감이지 검토 안건이 아니다.

| 묶음 | 카드 | 판정 |
| --- | --- | --- |
| **계승** (레거시에 있음) | `DSUP` `DSLW` `DSSAF` `DSAUTO` `DSALT` `DSSTAT` … | **안건 아님.** 규격대로 실으면 된다 |
| Archon 정체·버전 | `CTRL1ID` `CTRL1SN` `CTRL1FW` `CTRL2ID` `CTRL2SN` `CTRL2FW`<br>`CTRLVER` `TIMVER` `BIASVER` `CLKVER` | **10개.** 3장 A·B절 · 2.4절 |
| calibration DB 소관 | `CATVER` `REFVER` `XTALKVER` | **3개.** 규격 5.12 가 caldb 로 정리했다 — **안 싣는 것이 맞다** |
| 돔 확장 | `DSAZ` `DSTELAZ` `DALTERR` `DAZERR` (+ `DSTELALT` 는 레거시 `DSTEL` 의 개칭) | **4개 + 개칭 1.** 레거시에 없다 |
| FSA 환경 | `FSATEMP` `FSAHUM` `FSADEW` `FSAALRM` | **4개.** 레거시에 없다 |
| 영상 점검 | `CHKIMG` `CHKIMG_C` | **2개.** 레거시에 없다 |
| 관측 식별 | `FIELDID` | **1개** |
| 이름 fallback | `TCSDRIV` | 구멍이 아니다 — converter 가 `TCSDRIVE`(레거시가 쓰는 8자 이름)를 먼저 본다 |

**실제 결정 대상은 돔 확장 4 + FSA 4 + 영상 점검 2 = 10개**다. Archon 10개는 신규 전자부에 필연적으로 따라오는 것이라 *만들지 말지*가 아니라 *어떤 이름으로*가 쟁점이고(3장), calibration 3개는 이미 닫혔다.

| 묶음 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | 카드 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | 현재 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| --- | --- | --- |
| 돔 | `DSUP` `DSLW` `DSSAF` `DSAUTO` `DSALT` `DSAZ` `DSTELALT` `DSTELAZ`<br>`DALTERR` `DAZERR` | MEF 가 **빈 문자열**을 받는다 |
| FSA 환경 | `FSATEMP` `FSAHUM` `FSADEW` `FSAALRM` | 〃 |
| 영상 점검 | `CHKIMG` `CHKIMG_C` | 〃 |

> **없으면 무슨 일이 나나**: converter 는 카드가 없어도 오류를 내지 않고 `""` 를 채운다. 그래서 **L0 MEF 에 빈 문자열이 조용히 들어간다** — *"TC 가 안 보냈다"* 와 *"그런 장치가 없다"* 와 *"이 규격을 모르는 취득 SW"* 가 구분되지 않는다. 규격 5.0·5.9절이 "값이 없었다" 를 sentinel 로 **헤더에 남기라**고 정한 이유다.
>
> **그런데 sentinel 이 답이 아닐 수 있다**: 레거시 CTIO AUX 는 돔 필드를 보내지 않았고(SSO 만 보냈다), **FSA·영상점검 6개는 레거시 raw 어디에도 없다.** 없는 장치를 `NC` 로 채우면 *"TC 가 안 보냄"* 과 *"그런 장치가 없음"* 이 다시 섞인다. 그래서 5.4절 9번이 **sentinel 로 채울지 규격에서 뺄지**를 묻는다.

### 2.4 v0.5 정정 — 버전 문자열 9종은 "문서에 없는" 것이 아니라 **근거가 순환하는** 것이다

**v0.5 는 이 아홉 개가 *"`__reference/` 문서에도 없다"* 고 적었다. 사실이 아니다.** 3위 정의서 `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` 에 아홉 개 전부가 **값까지** 정의돼 있다.

| keyword | 정의서 분류 | 정의서의 값 | 위치 |
| --- | --- | --- | --- |
| `CAMVER` | Required | `CEU-v2.1` | `:119` |
| `WBTYPE` | Required | `STA Differential Board` | `:173` |
| `ELECSYS` | Required | `KMT-CEU` | `:174` |
| `SIGELEC` | Required | `STA_DIFF_VIDEO` | `:175` |
| `TIMCONF` | Calibration | `CEU_TIM_v1.0` | `:176` |
| `CTRLVER` | Calibration | `ARCHON-v1.0` | `:177` |
| `TIMVER` | Calibration | `TIM-v1.0` | `:178` |
| `BIASVER` | Calibration | `BIAS-v1.0` | `:181` |
| `CLKVER` | Calibration | `CLK-v1.0` | `:182` |

converter 의 하드코딩 문자열과 **문자 그대로 일치**한다. 그리고 그 정의서는 머리말에서 스스로 *"기준 converter: `…v2_1.py` v2.2.0"* 을 밝힌다. 즉 방향은 이렇다 — **converter 가 값을 정하고 → 정의서가 그것을 받아적고 → raw 가 정의서를 근거로 싣는다.** (v0.5 의 *"converter 하드코딩을 미러링한 상태"* 라는 서술 자체는 옳았다. 틀린 것은 *"문서에 없다"* 쪽이다.)

**그리고 1위 준거인 ICD v4.1 에는 아홉 개가 하나도 없다** — 2.1절이 센 174개 침묵 구간에 속한다. 그러므로 물음은 *"문서에 있느냐"* 가 아니라 이것이다:

> **ICD 가 요구한 적 없는 provenance 문자열을, raw 가 계속 실어야 하는가.**

덧붙여 v0.5 가 인용한 *"UNKNOWN before commissioning"* 은 아홉 개 전체의 분류가 아니다. 정의서 `VOLTINFO` 헤더 칸(`:423`-`:424`)의 **`BIASVER`·`CLKVER` 둘**에만 붙어 있다. *"두 문서가 서로 다른 상태를 요구한다"* 는 v0.5 의 서술은 이 둘에 한해서만 성립한다.

> 레거시 실측 grep 이 **0건**인 것은 맞다. 다만 **레거시 MEF 33건은 배경지식이므로 판정 근거가 아니고**(0.1절), 이 아홉 개에 대해서는 **레거시 raw 헤더 1건에 없다**는 사실만 근거가 된다.

## 3. Archon setup · 구성 · 유닛 텔레메트리 — 그룹별 검토

**이 장이 검토의 본체다.** raw 헤더의 Archon 관련 카드를 규격 절 단위로 묶고 `converter` 현재 동작과 검토 포인트를 붙였다.  카드 전수는 4장이다.

### 3.0 converter 의 현재 상태는 세 가지다

대조표를 읽을 때 이 구분이 핵심이다. **이 셋은 전부 0.2 절의 "값을 채우는 동작" 이므로 준거가 아니라 현재 구현이다.**

| 표기 | 뜻 | 함의 |
| --- | --- | --- |
| **읽음** | converter 가 raw 헤더에서 값을 꺼낸다 | **raw 가 정본.** 이름이 틀리면 L0 MEF 가 `UNKNOWN` 을 받는다 |
| **하드코딩** | converter 가 **같은 값을 소스에 문자열로** 갖고 있다 | raw 카드가 지금은 중복이다. 사이트별로 값이 갈리는 순간 필요해진다 |
| **placeholder** | converter 가 고정값으로 채운다 (raw 를 볼 통로가 없다) | raw 는 **아카이브 기록으로만** 남는다. 연결이 변경점 대상 |

여기에 **ICD 가 그 자리를 규정했는가**를 겹쳐 읽으면 무게가 정해진다.

| | ICD 가 규정한 자리 | ICD 가 침묵하는 자리 |
| --- | --- | --- |
| **placeholder** | **ICD 미준수다.** §12 가 *"placeholder 는 raw 헤더가 실측 텔레메트리를 주지 않을 때"* 로 한정하고 **필요한 raw 텔레메트리 집합은 우리 규격 5장이 정의한다**고 역참조한다 → **C-12 · C-17 · C-18** | 아카이브 기록으로만 남는다. 목적지를 만들지 말지가 5.3절 결정 사항 |
| **하드코딩** | 대조 대상이 있으므로 raw 선언과 맞추면 된다 | **근거가 순환한다** — 2.4절의 버전 문자열 9종이 이 칸이다 |

### 3.A 컨트롤러 정체 (규격 5.5.0)

| raw 카드 | 담는 것 | MEF 목적지 | 출처 | converter | 검토 포인트 |
| --- | --- | --- | --- | --- | --- |
| `CTRL1ID` | 컨트롤러 1 식별자 문자열 | PRIMARY `CTRL1ID` | SITE | **읽음** | 색인 `1`=MK·`2`=NT 로 정했다. 이 대응이 맞나 |
| `CTRL1SN` | 컨트롤러 1 시리얼 | PRIMARY `CTRL1SN` | ARCHON | **읽음** | |
| `CTRL1FW` | 컨트롤러 1 firmware | PRIMARY `CTRL1FW` | ARCHON | **읽음** | |
| `CTRL2ID` · `CTRL2SN` · `CTRL2FW` | 컨트롤러 2 | PRIMARY 동명 | 〃 | **읽음** | |
| `CTRLID` | **이 파일의 컨트롤러 색인** (`1`/`2`) | amp `CTRLID` · `TELEMETRY.CTRLID` | ACQ | 안 읽음 (chip 에서 계산) | ⚠️ `CTRL1ID`(문자열 이름)와 **이름이 너무 닮았다.** 개칭 검토 대상 — 예: `CTRLIDX` |

> **왜 색인형(`CTRL<n>*`)인가**: converter 가 **MK 헤더만** 읽으면서(`convert()` 가 두 chip 에 `mk_hdr` 를 넘긴다) 두 대분 정체를 요구한다. 단수형으로 두면 MEF 가 전부 `UNKNOWN` 을 받는다. 레거시도 같은 구조였다 — raw 파일마다 `KBUILD`/`MBUILD`/`TBUILD`/`NBUILD` 를 다 실었다.

### 3.B 컨트롤러 구성 · 버전 (규격 5.5)

| raw 카드 | 값(현행) | MEF 목적지 | converter | 검토 포인트 |
| --- | --- | --- | --- | --- |
| `CTRLVER` | `'ARCHON-v1.0'` | PRIMARY `CTRLVER` | **읽음** | |
| `TIMVER` | `'TIM-v1.0'` | PRIMARY `TIMVER` | **읽음** | |
| `BIASVER` | `'BIAS-v1.0'` | PRIMARY/`VOLTINFO` `BIASVER` | **읽음** | |
| `CLKVER` | `'CLK-v1.0'` | PRIMARY/`VOLTINFO` `CLKVER` | **읽음** | |
| `CONTROLL` | `'STA ARCHON'` | PRIMARY `CONTROLL` | **하드코딩** (`v2_1.py:409`) | |
| `NCTRL` | `2` | PRIMARY `NCTRL` | **하드코딩** (`:410`) | ⚠️ **과학 2대만 센 값이다.** Archon 은 3대(과학 2 + 가이드 1) — `NCTRL` 이 "과학" 인지 "전체" 인지 정의가 필요 |
| `TIMCONF` | `'CEU_TIM_v1.0'` | PRIMARY `TIMCONF` | **하드코딩** (`:420`) | |
| `WBTYPE` | `'STA Differential Board'` | PRIMARY `WBTYPE` | **하드코딩** (`:417`) | |
| `ELECSYS` | `'KMT-CEU'` | PRIMARY `ELECSYS` | **하드코딩** (`:418`) | |
| `SIGELEC` | `'STA_DIFF_VIDEO'` | PRIMARY `SIGELEC` | **하드코딩** (`:419`) | |

> ⚠️ **이 아홉 문자열은 근거가 없는 것이 아니라 근거가 순환한다.** 자세한 것은 2.4절 — 요지는 **converter 가 값을 정하고 → 정의서가 그것을 받아적고 → raw 가 정의서를 근거로 싣는데, 정작 1위 준거인 ICD v4.1 에는 아홉 개가 하나도 없다**는 것이다.
>
> 그래서 물어야 할 것: **무엇을 추적하는 버전인가 · 누가 부여하나 · 언제 올리나.** ACF 가 바뀌어도 이 문자열이 안 움직이면 **"없음" 보다 나쁘다** — 진짜 provenance 처럼 읽히기 때문이다.
>
> 후보: (가) 실제 추적 대상이 있는 것만 남기고 나머지 폐지 (나) `ACFFILE` 에서 파생 (다) 형식·등록처·증가 조건을 규정하고 유지

### 3.C 컨트롤러 런타임 (규격 5.5)

| raw 카드 | 담는 것 | MEF 목적지 | 출처 | converter | 검토 포인트 |
| --- | --- | --- | --- | --- | --- |
| `CTRLSTAT` | `OK`/`WARN`/`ERROR` | `TELEMETRY.STATUS` | ARCHON | **placeholder** | |
| `CTRLERR` | 오류 플래그 | `TELEMETRY.ERRORFLAG` | ARCHON | **placeholder** | |
| `BCKTEMP` | 백플레인 온도 [degC] | `TELEMETRY.BOARDTEMP` | ARCHON | **placeholder** | 이름이 `BOARDTEMP` 와 다르다 — 맞출까 |
| `READTIME` | 독출 소요 [s] | `TELEMETRY.READTIME` | ACQ | **placeholder** | |
| `ACFFILE` | 적용된 Archon 설정 파일 | **없음** | ACQ | 안 읽음 | ⚠️ MEF 목적지가 없다. **설정 provenance 의 유일한 포인터**이므로 MEF 에도 자리를 만들까 |
| `NPHLINES` | preheat line 수 | **없음** | ACQ | 안 읽음 | 레거시 계승. 정본은 `ACFFILE` 이 가리키는 timing script |
| `DATASRC` | `ARCHON`/`SIM` | **없음** | ACQ | 안 읽음 | ⚠️ **시뮬 프레임을 실측으로 오인하는 것을 막는 유일한 카드.** MEF 로도 전달돼야 하지 않나 |
| `FRAMENO` | 컨트롤러 frame counter | **없음** | ARCHON | 안 읽음 | 진단용. 유지 확정(2026-08-13) |
| `BUFNO` | 사용한 frame buffer | **없음** | ARCHON | 안 읽음 | 〃 |

> **placeholder 인 이유**: `telemetry_rows()` 가 **헤더 인자를 아예 받지 않는다** (`v2_1.py`, 인자 목록이 비어 있다). 그래서 raw 가 이 값들을 정확히 실어도 MEF `TELEMETRY` 표는 `UNKNOWN`·`-999.0`·`-1` 로 남는다. 변경점 **C-18**.
>
> 추가로 **C-17**: `convert()` 가 `mk_hdr` 하나만 넘기므로 `TELEMETRY` 표의 **2번 row(=NT)** 를 채울 근거가 없다. 정체는 색인형으로 양쪽에 실었지만(A절) **런타임 상태는 파일마다 실제로 다르므로 복제할 수 없다.**

### 3.D 전압 텔레메트리 (규격 5.6)

| raw 카드 | `VOLTINFO` 컬럼 | converter | 검토 포인트 |
| --- | --- | --- | --- |
| `VOLTN` | (row 수) | **placeholder** | ⚠️ **색인형 구성 자체가 검토 대상.** 아래 참고 |
| `VOLT<n>` | `VOLTNAME` | 〃 | |
| `VSET<n>` | `SETPOINT` | 〃 | |
| `VMEA<n>` | `MEASURED` | 〃 | |
| `VUNI<n>` | `UNIT` | 〃 | |
| `VSTA<n>` | `STATUS` | 〃 | |
| `VOLTSTAT` | `VOLTINFO` 헤더 `VOLTSTAT` | 〃 | |

최소 9종: `VOD` `VRD` `VOG` `VSS` `VDD` `PCLKH` `PCLKL` `SCLKH` `SCLKL`

> **색인형을 고른 이유**: FITS keyword 8자 제한 안에서 항목 수를 늘릴 수 있고 `VOLTINFO` 컬럼과 1:1 대응한다. 9종 × 5필드 = **45장**이 헤더에 들어간다.
>
> 대안: (가) 이름 기반 — `VSET_VOD` 처럼 (8자 초과라 `HIERARCH` 필요) (나) 전압을 raw 헤더에 넣지 않고 별도 산출물로 (다) 현행 색인형 유지
>
> `volt_rows()` 도 헤더 인자를 받지 않는다 — **C-18**.

### 3.E amp ↔ 전자계통 배선 (규격 5.5.1)

| raw 카드 | 담는 것 | MEF 목적지 | converter | 검토 포인트 |
| --- | --- | --- | --- | --- |
| `AMPMAP` | `EXPLICIT`/`DEFAULT` 선언 | 없음 | 안 읽음 | |
| `AMOD<nn>` | raw-local amp `nn` 의 module | amp `MODULE` | 안 읽음 (**amp 번호에서 추정**) | ⚠️ 32 + 32 = **64장**이 헤더에 들어간다. 구성 재검토 대상 |
| `ACHN<nn>` | 〃 video channel | amp `CHANNEL` | 〃 | |

> converter 는 `MODULE = 1 + (amp-1)//8`, `CHANNEL = 1 + (amp-1)%8` 로 **추정**하고 소스에 *"placeholder"* 라고 적어 두었다. 배선이 이 가정과 다르면 **`XTALKGROUP` 이 틀려 crosstalk 계수 측정 자체가 무의미해진다.** 변경점 **C-11**.
>
> 대안: (가) 현행 색인형 64장 (나) 문자열 한 장으로 압축 — 예: `AMPWIRE='1:1,1:2,…'` (다) 배선표를 raw 가 아니라 calibration DB 에

### 3.F geometry 선언 (규격 5.3) — MEF 목적지가 없는 그룹

`OSCNPATT` `ROWORDR` `RDDIRT` `RDDIRB` `NXTILE` `NAMPRAW` `MIDOSCB` `MIDOSCT` `CCDCOLS` `CCDROWS` `AMPPCD` `DETSIZE` `COLGAP` `ROWGAP` — **전부 안 읽음.**

목적이 다르다: MEF 로 전달하는 값이 아니라 **converter 가 자기 하드코딩 상수와 대조해 불일치를 잡게 하려는 선언**이다(규격 5.3 서두, 변경점 **C-5·C-13**). converter 쪽 대조가 아직 없으므로 지금은 선언만 있다.

취득 SW 쪽 방어는 붙였다 — `ics_sim/tests/test_geometry_vs_converter.py` 가 converter 를 import 해 선언과 맞댄다. 어느 쪽이 바뀌어도 그 시험이 걸린다.

> `RDDIRT`/`RDDIRB` 는 MEF amp `READDIR` 로 가야 하는데 converter 가 `amp<=8` 이면 `-Y` 로 하드코딩한다 — 변경점 **C-12**.

## 4. 전체 카드 대응표 (289행)

MEF 쪽은 **converter 코드**에서 뽑았고, **raw 쪽은 레거시 raw 실측 헤더(`KMTNk.20170209.044131.Rawheader.txt`, keyword 123개)를 기준으로 판정**했다. 한쪽에만 있는 카드도 빠뜨리지 않았다.

**v0.7 에서 raw 열의 뜻이 바뀌었다.** v0.5 에서는 *"`ics_sim` 이 이 카드를 쓴다"* 였고, 지금은 *"신규 raw 가 이 카드를 싣는다(계승이든 신설이든)"* 이다. `ics_sim` 의 현재 출력은 판정에 쓰지 않는다 — 미완성 구현이기 때문이다(1.2절).

표기: `ᴬ` = AUX/TCS 중계(pass-through) · `ᶠ` = FITS 표준 카드 · **`ᴺ` = 레거시 raw 실측본에 없는 신규 카드(84장)** · `—` = 그쪽에 대응물 없음

> `ᴺ` 이 붙지 않은 raw 카드는 **레거시가 이미 싣던 것**이라 계승 판정(규격 5.13절)이 끝나 있다. **결정이 필요한 것은 `ᴺ` 쪽**이다.

### 4.A MEF PRIMARY (154장)

| MEF 키워드 | raw 카드 | 용도 / 설명 | 유의사항 |
| --- | --- | --- | --- |
| `AIR_IN` | `AIR_IN` | air inlet temperature [C] |  |
| `AIR_OUT` | `AIR_OUT` | air outlet temperature [C] |  |
| `ALT` | `ALT` ᴬ | telescope altitude [deg] |  |
| `AMPDATA` | `AMPDATA` ᴺ | active columns per amp tile |  |
| `AMPPCD` | `AMPPCD` ᴺ | amplifiers per CCD |  |
| `AUXARC` | `AUXARC` ᴬ | AUX link auto recovery status |  |
| `AUXLINK` | `AUXLINK` ᴬ | AUX control system communication status |  |
| `AUXQDATE` | `AUXQDATE` ᴬ | UTC date/time of last AUX query |  |
| `AUXUDATE` | `AUXUDATE` ᴬ | UTC date/time of last AUX update |  |
| `AZ` | `AZ` ᴬ | telescope azimuth [deg] |  |
| `BIASVER` | `BIASVER` ᴺ | bias configuration version |  |
| `BITPIX` | `BITPIX` ᶠ | bits per pixel in image extensions |  |
| `BOTROWS` | `BOTROWS` ᴺ | active BOT-half rows |  |
| `BUNIT` | `BUNIT` | units of image pixel values |  |
| `CAMNAME` | `CAMNAME` ᴺ | camera electronics upgrade system |  |
| `CAMVER` | `CAMVER` ᴺ | camera/electronics version |  |
| `CATVER` | — | catalog version |  |
| `CCDTEMP` | `CCDTEMP` | CCD temperature [C] |  |
| `CCDXBIN` | `CCDXBIN` | CCD X-axis binning factor |  |
| `CCDYBIN` | `CCDYBIN` | CCD Y-axis binning factor |  |
| `CHARCOAL` | `CHARCOAL` | charcoal getter temperature [C] |  |
| `CHIPFLP` | `CHIPFLP` ᴺ | no chip-dependent OSU-style flip applied | raw 선언을 읽지 않고 상수를<br>쓴다. D-003 으로 `None` 확정 |
| `CHIPLIST` | `CHIPLIST` ᴺ | official science chip order |  |
| `CHKIMG` | — | image check status |  |
| `CHKIMG_C` | — | image check comment |  |
| `CHSTAT` | `CHSTAT` ᴬ | chiller status |  |
| `CLKVER` | `CLKVER` ᴺ | clock configuration version |  |
| `COLGAP` | `COLGAP` ᴺ | horizontal inter-CCD gap in pixels |  |
| `CONTROLL` | `CONTROLL` ᴺ | controller type | converter 가 `"STA ARCHON"` 을<br>**하드코딩**(`:409`). raw 값은 현재 미사용 |
| `CREATOR` | `CREATOR` ᴺ | MEF creation program |  |
| `CTRL1FW` | `CTRL1FW` ᴺ | science controller 1 firmware |  |
| `CTRL1ID` | `CTRL1ID` ᴺ | science controller 1 ID | converter 가 **MK 헤더만** 읽으므로 raw<br>가 두 대분을 색인형으로 실어야 한다.<br>없으면 MEF 가 `UNKNOWN` — 오류 없이. ⚠️<br>raw `CTRLID`(색인 정수)와 이름이 닮았다 |
| `CTRL1SN` | `CTRL1SN` ᴺ | science controller 1 serial number |  |
| `CTRL2FW` | `CTRL2FW` ᴺ | science controller 2 firmware |  |
| `CTRL2ID` | `CTRL2ID` ᴺ | science controller 2 ID | 〃 |
| `CTRL2SN` | `CTRL2SN` ᴺ | science controller 2 serial number |  |
| `CTRLVER` | `CTRLVER` ᴺ | controller system version | converter 가 raw 를 읽는다(기본 `ARCHON-v1.0`).<br>근거 없는 버전 문자열 9종 중 하나(ACT-011) |
| `DALTERR` | — | dome-telescope altitude difference [deg] |  |
| `DARKTIME` | `DARKTIME` | cumulative dark time [s] |  |
| `DATAPROD` | — | data product type |  |
| `DATE` | `DATE` ᴺ | date FITS file was generated |  |
| `DATE-OBS` | `DATE-OBS` ᴬ | UTC date/time at start of observation | ⚠️ **없으면 변환 시각(now)으로 대체된다** —<br>MEF 의 `DATE-OBS` / `MJD-OBS` / `JD` 가 전부<br>관측과 무관해지고 **오류는 나지 않는다**(규격<br>6.2, C-6). raw 는 밀리초까지 필수 |
| `DAZERR` | — | dome-telescope azimuth difference [deg] |  |
| `DEC` | `DEC` ᴬ | telescope DEC |  |
| `DETECTOR` | `DETECTOR` | detector model |  |
| `DETSIZE` | `DETSIZE` ᴺ | KMTNet mosaic size in pixels |  |
| `DETTYPE` | `DETTYPE` ᴺ | science detector data product |  |
| `DEWPRES` | `DEWPRES` | dewar pressure |  |
| `DSALT` | `DSALT` ᴬ | dome slit altitude [deg] | **레거시 raw 에 있다** — 계승 대상이고<br>`ics_sim` 이 아직 안 쓸 뿐이다 |
| `DSAUTO` | `DSAUTO` ᴬ | dome auto sync status | **레거시 raw 에 있다** — 계승 대상이고<br>`ics_sim` 이 아직 안 쓸 뿐이다 |
| `DSAZ` | — | dome slit azimuth [deg] |  |
| `DSLW` | `DSLW` ᴬ | lower dome shutter position | **레거시 raw 에 있다** — 계승 대상이고<br>`ics_sim` 이 아직 안 쓸 뿐이다 |
| `DSSAF` | `DSSAF` ᴬ | dome safety status | **레거시 raw 에 있다** — 계승 대상이고<br>`ics_sim` 이 아직 안 쓸 뿐이다 |
| `DSSTAT` | `DSSTAT` ᴬ | dome shutter status |  |
| `DSTELALT` | — | telescope altitude used by dome [deg] | ⚠️ AUX 실선은 `DSTEL` 을 보내고 Archon<br>converter 는 `DSTELALT` 만 읽는다(fallback<br>없음) — ICS 가 옮겨 싣는다 |
| `DSTELAZ` | — | telescope azimuth used by dome [deg] |  |
| `DSUP` | `DSUP` ᴬ | upper dome shutter position | **레거시 raw 에 있다** — 계승 대상이고<br>`ics_sim` 이 아직 안 쓸 뿐이다 |
| `ELECSYS` | `ELECSYS` ᴺ | electronics system | converter 하드코딩(`:418`). 〃 |
| `ELEVATIO` | `ELEVATIO` | site elevation [m] |  |
| `ENFAN` | `ENFAN` ᴬ | environmental system fan state |  |
| `ENSTAT` | `ENSTAT` ᴬ | environmental control system status |  |
| `EQUINOX` | `EQUINOX` ᴬ | coordinate system equinox |  |
| `EXPTIME` | `EXPTIME` | exposure time [s] |  |
| `EXTEND` | `EXTEND` ᶠ | file contains extensions |  |
| `FAFOCUS` | `FAFOCUS` ᴬ | focus position offset [mm] |  |
| `FALIME` | `FALIME` ᴬ | east focus actuator limit status |  |
| `FALIMS` | `FALIMS` ᴬ | south focus actuator limit status |  |
| `FALIMW` | `FALIMW` ᴬ | west focus actuator limit status |  |
| `FAPOSE` | `FAPOSE` ᴬ | east focus actuator position [mm] |  |
| `FAPOSS` | `FAPOSS` ᴬ | south focus actuator position [mm] |  |
| `FAPOSW` | `FAPOSW` ᴬ | west focus actuator position [mm] |  |
| `FASTAT` | `FASTAT` ᴬ | focus actuator subsystem status |  |
| `FATILTEW` | `FATILTEW` ᴬ | focus tilt EW offset [arcsec] |  |
| `FATILTNS` | `FATILTNS` ᴬ | focus tilt NS offset [arcsec] |  |
| `FIELDID` | `FIELDID` ᴺ | KMTNet field identifier |  |
| `FILENAME` | `FILENAME` | MEF filename | **실제로 쓴 이름**(확장자 없음).<br>평소엔 `UNIQNAME` 과 같다 |
| `FILNUM` | `FILNUM` ᴬ | filter selector position number |  |
| `FILTER` | `FILTER` ᴬ | filter name in beam |  |
| `FILTOP` | `FILTOP` ᴬ | filter operational status |  |
| `FSAALRM` | — | FSA environmental alarm status |  |
| `FSADEW` | — | FSA internal dew point [C] |  |
| `FSAHUM` | — | FSA internal relative humidity [%] |  |
| `FSATEMP` | — | FSA internal temperature [C] |  |
| `FSSTAT` | `FSSTAT` ᴬ | filter-shutter subsystem status |  |
| `GLYC_IN` | `GLYC_IN` | glycol inlet temperature [C] |  |
| `GLYC_OUT` | `GLYC_OUT` | glycol outlet temperature [C] |  |
| `HA` | `HA` ᴬ | hour angle at start |  |
| `IMAGETYP` | `IMAGETYP` | type of observation |  |
| `INSTRUME` | `INSTRUME` | instrument name |  |
| `JD` | — | Julian date at start | converter 가 `DATE-OBS` 에서<br>계산. raw 는 싣지 않는다 |
| `LATITUDE` | `LATITUDE` | site latitude |  |
| `LONGITUD` | `LONGITUD` | site longitude |  |
| `MCPOS` | `MCPOS` ᴬ | mirror cover position [%] |  |
| `MCSTAT` | `MCSTAT` ᴬ | mirror cover status |  |
| `MIDOVSCY` | `MIDOVSCY` ᴺ | middle Y overscan rows |  |
| `MJD-OBS` | `MJD-OBS` ᴺ | modified Julian date at start |  |
| `MKFILE` | — | source MK raw FITS file |  |
| `NAMPS` | `NAMPS` | total amplifiers |  |
| `NAXIS` | `NAXIS` ᶠ | primary HDU has no image array |  |
| `NCCD` | `NCCD` ᴺ | number of science CCDs |  |
| `NCTRL` | `NCTRL` ᴺ | number of science Archon controllers | converter 가 `2` 를 **하드코딩**(`:410`). ⚠️<br>**과학 2대만 센 값** — Archon 은 3대(과학 2<br>+ 가이드 1). 정의 확인 필요(ACT-011) |
| `NEND` | `NEND` ᴺ | top and bottom readout ends per strip |  |
| `NSTRIP` | `NSTRIP` ᴺ | vertical strips per CCD |  |
| `NTFILE` | — | source NT raw FITS file |  |
| `NUMFILES` | `NUMFILES` ᴺ | number of raw files used |  |
| `OBJECT` | `OBJECT` | name of object observed |  |
| `OBSERVAT` | `OBSERVAT` | observatory site | 파일명 `<SITE>` 와 **교차검증**한다 — 불일치는<br>변환 오류(D-011). 둘 다 우리 설정에서 나오므로<br>사이트 오배포는 못 잡는다(D-015) |
| `OBSERVER` | `OBSERVER` | observer(s) |  |
| `OBSTYPE` | `OBSTYPE` | type of observation |  |
| `ORIGIN` | `ORIGIN` | FITS file originator |  |
| `OVERSCNX` | `OVERSCNX` | X overscan columns per amp tile |  |
| `PIPEVER` | — | converter version |  |
| `PIXSCALE` | `PIXSCALE` | unbinned pixel scale [arcsec/pixel] |  |
| `PIXSIZE` | `PIXSIZE` | unbinned pixel size [micron] |  |
| `PRESCANX` | `PRESCANX` | X prescan columns per amp tile |  |
| `PRODVER` | — | product format version |  |
| `PROJID` | `PROJID` | project or observing program ID |  |
| `PT30N1` | `PT30N1` | cooler temperature sensor 1 [C] |  |
| `PT30N2` | `PT30N2` | cooler temperature sensor 2 [C] |  |
| `RA` | `RA` ᴬ | telescope RA |  |
| `RADECSYS` | `RADECSYS` | telescope coordinate system |  |
| `RAWGROUP` | `RAWGROUP` ᴺ | raw Archon file grouping convention |  |
| `RAWNAX1` | `RAWNAX1` ᴺ | raw Archon image width |  |
| `RAWNAX2` | `RAWNAX2` ᴺ | raw Archon image height |  |
| `RAWXTILE` | `RAWXTILE` ᴺ | raw amp tile width |  |
| `READARCH` | `READARCH` ᴺ | 8 strips read from top and bottom |  |
| `READMODE` | `READMODE` ᴺ | 64-amplifier readout mode |  |
| `REFVER` | — | reference image version |  |
| `ROWGAP` | `ROWGAP` ᴺ | vertical inter-CCD gap in pixels |  |
| `SECZ` | `SECZ` ᴬ | secant of zenith distance |  |
| `SHUTOP` | `SHUTOP` ᴬ | shutter operational status | 셔터 운용 상태. `NC` / `STANDBY` / `OPENING` /<br>`OPENED` / `CLOSING` / `RELOADING` / `ERROR` &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| `SHUTTER` | `SHUTTER` ᴬ | shutter position | AUX 가 보고한 셔터 상태.<br>`OPEN`(개방중·개방·폐쇄중) / `CLOSED` /<br>`UNKNOWN`. **`SHUTOP` 의 순수 함수**이고<br>"완전 개방" 이 아니다 |
| `SIGELEC` | `SIGELEC` ᴺ | signal readout/video-chain electronics | converter 하드코딩(`:419`). 〃 |
| `SIMPLE` | `SIMPLE` ᶠ | FITS standard |  |
| `SITEID` | `SITEID` ᴺ | site identifier |  |
| `ST` | `ST` ᴬ | local sidereal time at start |  |
| `TCSARC` | `TCSARC` ᴬ | TCS auto recovery mode status |  |
| `TCSDRIV` | — | telescope drive status |  |
| `TCSLINK` | `TCSLINK` ᴬ | TCS communications link status |  |
| `TCSQDATE` | `TCSQDATE` ᴬ | UTC date/time of last TCS query |  |
| `TCSUDATE` | `TCSUDATE` ᴬ &nbsp;&nbsp; | UTC date/time of last TCS update |  |
| `TELESCOP` | `TELESCOP` | telescope name |  |
| `TELMOVE` | `TELMOVE` ᴬ | telescope motion status |  |
| `TIMCONF` | `TIMCONF` ᴺ | CCD clock and timing configuration | converter 하드코딩(`:420`). 근거 없는<br>버전 문자열 9종 중 하나(ACT-011) |
| `TIMESYS` | `TIMESYS` ᴬ | time system |  |
| `TIMVER` | `TIMVER` ᴺ | timing script version |  |
| `TOPROWS` | `TOPROWS` ᴺ | active TOP-half rows |  |
| `TSHOPEN` | `TSHOPEN` | shutter open time |  |
| `TSHSHUT` | `TSHSHUT` | shutter close time |  |
| `UNIQNAME` | `UNIQNAME` | unique filename | **정본 식별자.** 항상 정규 형태이고 어떤<br>경우에도 바뀌지 않는다 — 이름이 겹쳐<br>격리된 파일도 이 값은 그대로다(2.3.1) |
| `UT` | — | UTC timestamp | `DATE-OBS` 날짜부 + raw `TSHOPEN`<br>으로 **조립**한다. raw 의 `UT`<br>카드는 폐지했고 영향 없다 |
| `WBTYPE` | `WBTYPE` ᴺ | wall board type | converter 하드코딩(`:417`). 〃 |
| `XTALKCAL` | — | crosstalk coefficients are placeholders |  |
| `XTALKVER` &nbsp;&nbsp;&nbsp;&nbsp; | — | crosstalk model version |  |

### 4.B MEF amp extension (73장)

| MEF 키워드 | raw 카드 | 용도 / 설명 | 유의사항 |
| --- | --- | --- | --- |
| `ALT` | `ALT` ᴬ | telescope altitude [deg] |  |
| `AMPDATA` | `AMPDATA` ᴺ | active columns per amp tile |  |
| `AMPID` | — | global amplifier ID |  |
| `AMPNAME` | — | amplifier name |  |
| `AMPSEC` | — | amplifier section in CCD coords |  |
| `AMPSEQ` | — | amplifier sequence within CCD |  |
| `AZ` | `AZ` ᴬ | telescope azimuth [deg] |  |
| `BIASSEC` | — | local overscan section |  |
| `BITPIX` | `BITPIX` ᶠ | bits per pixel in image extensions |  |
| `BSCALE` | `BSCALE` ᶠ | default scale |  |
| `BUNIT` | `BUNIT` | units of image pixel values |  |
| `BZERO` | `BZERO` ᶠ | unsigned 16-bit zero point | ⚠️ 없으면 `32768` 을 가정 — raw 가 signed<br>면 **전 픽셀이 32768 어긋난다**(규격 6.2) |
| `CCDNAME` | — | CCD name |  |
| `CCDSEC` | — | amplifier section in CCD coords |  |
| `CCDSUM` | `CCDSUM` ᴺ | on-chip binning factors |  |
| `CD1_1` | — | coordinate transform matrix |  |
| `CD1_2` | — | coordinate transform matrix |  |
| `CD2_1` | — | coordinate transform matrix |  |
| `CD2_2` | — | coordinate transform matrix |  |
| `CHANNEL` | — | controller channel placeholder | ⚠️ `1+(amp-1)%8` 추정식. raw<br>`ACHN<nn>` 미연결 — **C-11** |
| `CHIPFLP` | `CHIPFLP` ᴺ | no chip-dependent OSU-style flip applied | raw 선언을 읽지 않고 상수를<br>쓴다. D-003 으로 `None` 확정 |
| `CHIPID` | — | CCD identifier |  |
| `CRPIX1` | — | placeholder coordinate reference pixel |  |
| `CRPIX2` | — | placeholder coordinate reference pixel |  |
| `CRVAL1` | — | placeholder coordinate reference RA<br>[deg] |  |
| `CRVAL2` | — | placeholder coordinate reference DEC<br>[deg] |  |
| `CTRLID` | `CTRLID` ᴺ | science controller ID | ⚠️ **색인 정수**(`1` / `2`)이고<br>`CTRL1ID`(식별자 문자열)와 다르다. converter<br>는 raw 를 안 읽고 chip 에서 계산한다 → raw<br>카드가 현재 미사용. 개칭 검토 대상(ACT-011) |
| `CTYPE1` | — | coordinate type |  |
| `CTYPE2` | — | coordinate type |  |
| `DATAPROD` | — | data product type |  |
| `DATASEC` | — | active data section |  |
| `DEC` | `DEC` ᴬ | telescope DEC |  |
| `DETSEC` | — | amplifier coords on detector mosaic |  |
| `ENDID` | — | readout end ID |  |
| `EXTNAME` | — | amplifier image extension |  |
| `EXTTYPE` | — | L0 amplifier raw image |  |
| `FILTER` | `FILTER` ᴬ | filter name in beam |  |
| `GAIN` | — | gain placeholder [e-/ADU] | placeholder `0.0`. calibration DB<br>소관 — raw 에 넣지 않는다(규격 5.12) |
| `GCOUNT` | — | — |  |
| `HA` | `HA` ᴬ | hour angle at start |  |
| `IMAGETYP` | `IMAGETYP` | type of observation |  |
| `LINMAX` | — | linearity maximum placeholder [ADU] | placeholder `58000`. 〃 |
| `MIDOVSCY` | `MIDOVSCY` ᴺ | middle Y overscan rows |  |
| `MODULE` | — | controller module placeholder | ⚠️ `1+(amp-1)//8` **추정식**이고 소스가 스스로<br>*"placeholder"* 라 적었다. raw `AMOD<nn>` 미연결<br>— 배선이 다르면 `XTALKGROUP` 이 틀려<br>**crosstalk 계수 측정이 무의미해진다**. **C-11** |
| `NAXIS` | `NAXIS` ᶠ | primary HDU has no image array |  |
| `NAXIS1` | `NAXIS1` ᶠ | amp image width including overscan |  |
| `NAXIS2` | `NAXIS2` ᶠ | amp image active rows |  |
| `OBJECT` | `OBJECT` | name of object observed |  |
| `OBSTYPE` | `OBSTYPE` | type of observation |  |
| `OVERSCNX` | `OVERSCNX` | X overscan columns per amp tile |  |
| `PCOUNT` | — | — |  |
| `PRESCANX` | `PRESCANX` | X prescan columns per amp tile |  |
| `PRESEC` | — | no prescan in Archon raw |  |
| `PROJID` | `PROJID` | project or observing program ID |  |
| `RA` | `RA` ᴬ | telescope RA |  |
| `RAWBIAS` | — | source raw overscan section |  |
| `RAWDATA` | — | source raw data section |  |
| `RAWFILE` | — | source raw FITS file |  |
| `RAWNAX1` | `RAWNAX1` ᴺ | raw Archon image width |  |
| `RAWNAX2` | `RAWNAX2` ᴺ | raw Archon image height |  |
| `RAWXTILE` | `RAWXTILE` ᴺ | raw amp tile width |  |
| `RDNOISE` | — | read noise placeholder [e-] | placeholder `0.0`. 〃 |
| `READDIR` | — | physical readout direction placeholder | ⚠️ `amp<=8` 이면 `-Y` 로 **하드코딩**.<br>raw `RDDIRT` / `RDDIRB` 미연결 — **C-12** |
| `REALDATA` | — | actual amplifier data from Archon raw |  |
| `SATURAT` | — | saturation level placeholder [ADU] | ⚠️ amp 헤더는 `SATURAT`, `AMPINFO` 컬럼은<br>`SATLEVEL` — **converter 내부에서 이름이 갈린다**.<br>둘 다 placeholder(62000) |
| `SECZ` | `SECZ` ᴬ | secant of zenith distance |  |
| `ST` | `ST` ᴬ | local sidereal time at start |  |
| `STRIPDIR` | `STRIPDIR` ᴺ &nbsp;&nbsp;&nbsp;&nbsp; | strip number direction in CEU L0 packing | raw 선언을 읽지 않고 상수를 쓴다. raw 좌표계 기준<br>`+X` — K·N 이 180° 회전 장착이라 CCD 기준과 다르다 |
| `STRIPID` | — | vertical strip ID |  |
| `TRIMSEC` | — | trimmed data section |  |
| `UT` | — | UTC timestamp | `DATE-OBS` 날짜부 + raw `TSHOPEN`<br>으로 **조립**한다. raw 의 `UT`<br>카드는 폐지했고 영향 없다 |
| `WCSDIM` | — | coordinate system dimensionality |  |
| `XTENSION` &nbsp;&nbsp;&nbsp;&nbsp; | — | image extension |  |

### 4.C MEF `AMPINFO` 컬럼 (40장)

| MEF 키워드 | raw 카드 | 용도 / 설명 | 유의사항 |
| --- | --- | --- | --- |
| `AMPID` | — | global amplifier ID |  |
| `AMPNAME` | — | amplifier name |  |
| `AMPSEC` | — | amplifier section in CCD coords |  |
| `AMPSEQ` | — | amplifier sequence within CCD |  |
| `AMPX0` | — | — |  |
| `AMPX1` | — | — |  |
| `AMPY0` | — | — |  |
| `AMPY1` | — | — |  |
| `BIASSEC` | — | local overscan section |  |
| `CCDSEC` | — | amplifier section in CCD coords |  |
| `CHANNEL` | — | controller channel placeholder | ⚠️ `1+(amp-1)%8` 추정식. raw<br>`ACHN<nn>` 미연결 — **C-11** |
| `CHIPFLP` | `CHIPFLP` ᴺ | no chip-dependent OSU-style flip applied | raw 선언을 읽지 않고 상수를<br>쓴다. D-003 으로 `None` 확정 |
| `CHIPID` | — | CCD identifier |  |
| `CTRLID` | `CTRLID` ᴺ | science controller ID | ⚠️ **색인 정수**(`1` / `2`)이고<br>`CTRL1ID`(식별자 문자열)와 다르다. converter<br>는 raw 를 안 읽고 chip 에서 계산한다 → raw<br>카드가 현재 미사용. 개칭 검토 대상(ACT-011) |
| `DATASEC` | — | active data section |  |
| `DETSEC` | — | amplifier coords on detector mosaic |  |
| `DETX0` | — | — |  |
| `DETX1` | — | — |  |
| `DETY0` | — | — |  |
| `DETY1` | — | — |  |
| `ENDID` | — | readout end ID |  |
| `EXTNAME` | — | amplifier image extension |  |
| `GAIN` | — | gain placeholder [e-/ADU] | placeholder `0.0`. calibration DB<br>소관 — raw 에 넣지 않는다(규격 5.12) |
| `LINMAX` | — | linearity maximum placeholder [ADU] | placeholder `58000`. 〃 |
| `MODULE` | — | controller module placeholder | ⚠️ `1+(amp-1)//8` **추정식**이고 소스가 스스로<br>*"placeholder"* 라 적었다. raw `AMOD<nn>` 미연결<br>— 배선이 다르면 `XTALKGROUP` 이 틀려<br>**crosstalk 계수 측정이 무의미해진다**. **C-11** |
| `PRESEC` | — | no prescan in Archon raw |  |
| `RAWBIAS` | — | source raw overscan section |  |
| `RAWDATA` | — | source raw data section |  |
| `RAWFILE` | — | source raw FITS file |  |
| `RAWX0` | — | — |  |
| `RAWX1` | — | — |  |
| `RAWY0` | — | — |  |
| `RAWY1` | — | — |  |
| `RDNOISE` | — | read noise placeholder [e-] | placeholder `0.0`. 〃 |
| `READDIR` | — | physical readout direction placeholder | ⚠️ `amp<=8` 이면 `-Y` 로 **하드코딩**.<br>raw `RDDIRT` / `RDDIRB` 미연결 — **C-12** |
| `SATLEVEL` | — | — | ⚠️ amp 헤더의 같은 값이<br>`SATURAT` 이다 — 이름 불일치 |
| `STRIPDIR` | `STRIPDIR` ᴺ &nbsp;&nbsp;&nbsp;&nbsp; | strip number direction in CEU L0 packing | raw 선언을 읽지 않고 상수를 쓴다. raw 좌표계 기준<br>`+X` — K·N 이 180° 회전 장착이라 CCD 기준과 다르다 |
| `STRIPID` | — | vertical strip ID |  |
| `TRIMSEC` | — | trimmed data section |  |
| `XTALKGROUP` &nbsp;&nbsp; | — | — | `MODULE` 에서 파생 → 위 추정이 틀리면 함께 틀린다 |

### 4.D MEF `TELEMETRY` 컬럼 (6장)

| MEF 키워드 | raw 카드 | 용도 / 설명 | 유의사항 |
| --- | --- | --- | --- |
| `BOARDTEMP` | — | — | ⚠️ 같은 이유로 `-999.0` 고정. raw `BCKTEMP` 와<br>**이름도 다르다** — 맞출지 검토(ACT-011). **C-18** |
| `CTRLID` | `CTRLID` ᴺ | science controller ID | ⚠️ **색인 정수**(`1` / `2`)이고<br>`CTRL1ID`(식별자 문자열)와 다르다. converter<br>는 raw 를 안 읽고 chip 에서 계산한다 → raw<br>카드가 현재 미사용. 개칭 검토 대상(ACT-011) |
| `ERRORFLAG` | — | — | ⚠️ `-1` 고정. raw `CTRLERR`<br>와 연결 안 됨 — **C-18** |
| `FWVERSION` &nbsp;&nbsp;&nbsp; | — | — | ⚠️ `telemetry_rows()` 가<br>**헤더 인자를 안 받아** `"UNKNOWN"` 고정.<br>raw `CTRL<n>FW` 와 연결 안 됨 — **C-18** |
| `READTIME` | `READTIME` ᴺ &nbsp;&nbsp;&nbsp;&nbsp; | `TELEMETRY.READTIME` [s] &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | ⚠️ `-1.0` 고정. raw `READTIME`<br>과 연결 안 됨 — **C-18** |
| `STATUS` | — | — |  |

### 4.E MEF `VOLTINFO` 컬럼 (5장)

| MEF 키워드 | raw 카드 | 용도 / 설명 | 유의사항 |
| --- | --- | --- | --- |
| `MEASURED` | — | — | ⚠️ `0.0` 고정. raw `VMEA<n>` 미연결 — **C-18** |
| `SETPOINT` | — | — | ⚠️ `0.0` 고정. raw `VSET<n>` 미연결 — **C-18** |
| `STATUS` | — | — |  |
| `UNIT` | — | — |  |
| `VOLTNAME` &nbsp;&nbsp;&nbsp;&nbsp; | — &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | — &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | ⚠️ `volt_rows()` 도 헤더 인자를 안 받아 9종<br>고정값. raw `VOLT<n>` 과 연결 안 됨 — **C-18** &nbsp;&nbsp;&nbsp; |

### 4.F MEF `XTALKINFO` 컬럼 (7장)

| MEF 키워드 | raw 카드 | 용도 / 설명 | 유의사항 |
| --- | --- | --- | --- |
| `MEASURE_DATE` | — | — |  |
| `SOURCE_AMP` | — | — |  |
| `STATUS` | — | — |  |
| `TARGET_AMP` | — | — |  |
| `XTALK_COEF` | — | — | placeholder `0.0` × 4096행.<br>`xtalk_rows()` 도 헤더 인자를 안 받는다 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| `XTALK_ERROR` | — | — |  |
| `XTALK_VERSION` | — &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | — &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | placeholder `'UNMEASURED'` |

### 4.G MEF 표 HDU 헤더 (19장)

| MEF 키워드 | raw 카드 | 용도 / 설명 | 유의사항 |
| --- | --- | --- | --- |
| `BIASVER` | `BIASVER` ᴺ | bias configuration version |  |
| `BITPIX` | `BITPIX` ᶠ | bits per pixel in image extensions |  |
| `CLKVER` | `CLKVER` ᴺ | clock configuration version |  |
| `EXTNAME` | — | amplifier image extension |  |
| `GCOUNT` | — | — |  |
| `GEOMVER` | — | geometry definition version | `AMPINFO` 표 헤더. geometry 가<br>바뀌면 `RAWVER` 와 함께 올린다(OI-3) |
| `NAMP` | — | number of amplifier rows |  |
| `NAXIS` | `NAXIS` ᶠ | primary HDU has no image array |  |
| `NAXIS1` | `NAXIS1` ᶠ | amp image width including overscan |  |
| `NAXIS2` | `NAXIS2` ᶠ | amp image active rows |  |
| `NCTRL` | `NCTRL` ᴺ | number of science Archon controllers &nbsp;&nbsp;&nbsp; | converter 가 `2` 를 **하드코딩**(`:410`). ⚠️<br>**과학 2대만 센 값** — Archon 은 3대(과학 2<br>+ 가이드 1). 정의 확인 필요(ACT-011) |
| `NXTALK` | — | number of crosstalk matrix rows |  |
| `PCOUNT` | — | — |  |
| `RAWGROUP` | `RAWGROUP` ᴺ | raw Archon file grouping convention |  |
| `TELSTAT` | — | telemetry status | ⚠️ 코드가 `"UNKNOWN"` 고정. raw 의 `CTRLSTAT`<br>두 개에서 파생해야 한다 — **변경점 C-15** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| `VOLTSTAT` | `VOLTSTAT` ᴺ &nbsp;&nbsp;&nbsp;&nbsp; | voltage telemetry status |  |
| `XTALKCAL` | — | crosstalk coefficients are placeholders |  |
| `XTALKVER` | — | crosstalk model version |  |
| `XTENSION` &nbsp;&nbsp;&nbsp;&nbsp; | — | image extension |  |

### 4.H raw 에만 있는 카드 (53장)

MEF 로 가지 않는다.  용도는 (1) converter 교차검증 선언, (2) pair 식별, (3) 아카이브 기록 세 가지다.

| raw 카드 | 용도 / 설명 | 유의사항 |
| --- | --- | --- |
| `ACFFILE` ᴺ | 적용된 Archon 설정 파일 | 적용된 Archon 설정 파일.<br>**설정 provenance 의 유일한 포인터**인데<br>MEF 목적지가 없다(ACT-011) |
| `AMPMAP` ᴺ | `EXPLICIT`이면 아래 표가 유효. `DEFAULT`면 converter의<br>추정식을 쓴다는 선언 | `EXPLICIT` / `DEFAULT` 선언. `DEFAULT` 는<br>converter 의 추정식을 쓰겠다는 **명시적 선언**이다 |
| `BCKTEMP` ᴺ | `TELEMETRY.BOARDTEMP` [degC] |  |
| `BUFNO` ᴺ | 사용한 Archon frame buffer | 사용한 Archon frame buffer. 〃 |
| `CCDCOLS` ᴺ | chip 1개의 active column (`NSTRIP × AMPDATA`) |  |
| `CCDROWS` ᴺ | chip 1개의 active row (`TOPROWS + BOTROWS`) |  |
| `CCDTEMP1` ᴺ | `CHIP1` 온도 [degC] | CHIP1 온도. `CCDTEMP` 는 이 둘의 **평균으로 파생**한다 |
| `CCDTEMP2` ᴺ | `CHIP2` 온도 [degC] | CHIP2 온도. 〃 |
| `CHECKSUM` ᶠ | FITS 표준 checksum |  |
| `CHIP1` ᴺ | X 1–9600 절반의 chip |  |
| `CHIP2` ᴺ | X 9601–19200 절반의 chip |  |
| `CHIPS` ᴺ | 이 파일에 담긴 chip (X 낮은 쪽부터) |  |
| `CHOP` ᴬ | — |  |
| `CHPROC` ᴬ | — |  |
| `CHSET` ᴬ | — |  |
| `CTRLERR` ᴺ | `TELEMETRY.ERRORFLAG` |  |
| `CTRLSTAT` ᴺ | `TELEMETRY.STATUS` |  |
| `CTRLTAG` ᴺ | **이 파일이 pair의 어느 쪽인가** | 이 파일이 pair 의 어느 쪽인가. 〃 |
| `DATASRC` | **`ARCHON` / `SIM`** — 레거시 계승(5.13절). 픽셀이<br>실제 컨트롤러에서 왔는지 시뮬레이터가 만든 것인지.<br>**시뮬 프레임이 실측으로 오인되는** **것을**<br>**막는 유일한 카드다** | ⚠️ **`ARCHON` / `SIM` — 시뮬 프레임이**<br>**실측으로 오인되는 것을 막는 유일한**<br>**카드.** MEF 목적지가 없다(ACT-011) |
| `DATASUM` ᶠ | FITS 표준 datasum |  |
| `ENS1` ᴬ | — |  |
| `ENS2` ᴬ | — |  |
| `ENS3` ᴬ | — |  |
| `ENS4` ᴬ | — |  |
| `ENS5` ᴬ | — |  |
| `ENS6` ᴬ | — |  |
| `ENS7` ᴬ | — |  |
| `EXECODE` ᴺ ᴬ | ICS relay 필드 |  |
| `FRAMENO` ᴺ | controller frame counter | 컨트롤러 frame counter. 진단용, MEF 목적지 없음 |
| `HEMODE` | **`SCIENCE` / `GUIDE`** — 레거시 계승(5.13절). Archon<br>3대 중 1대가 guide 전용이므로 이 구분이 살아 있다 | `SCIENCE` / `GUIDE`. Archon 3대 중<br>1대가 guide 전용이라 구분이 살아 있다 |
| `ICSBUILD` | **취득 프로그램의 빌드 식별자** — 레거시 계승(5.13절).<br>형식은 `<프로그램>-v<버전>:<빌드일시(UTC)>` | `<프로그램>-v<버전>:<빌드일시(UTC)>`.<br>파이썬이라 빌드 시각을 코드에 손으로 적는다 |
| `LEDFLASH` | 점검용 LED 프로젝터 점등 시간 [초]. `0`이면 점등 안<br>함. **레거시 계승(5.13절)** — 램프로 만든 실험실 flat<br>을 하늘 자료로 오인하지 않게 하는 카드다. 단위는<br>레거시와 같은 **초**를 유지한다(ICS 내부는 ms 이므로<br>나눠서 싣는다) | 점검용 LED 점등 시간 [**초**]. 램프<br>flat 을 하늘 자료로 오인하지 않게 한다 |
| `MIDOSCB` ᴺ | 그중 BOT half에서 나온 row 수 (**실측 확인 필요**) |  |
| `MIDOSCT` ᴺ | 그중 TOP half에서 나온 row 수 (**실측 확인 필요**) |  |
| `NAMPRAW` ᴺ | **이 파일에 담긴 amplifier 수** (chip 2 × amp 16) |  |
| `NPHLINES` | preheat line 수 — 레거시 계승(5.13절). ADC/비디오단을<br>안정시키려 독출 전에 버리는 dummy line. 값의 정본은<br>`ACFFILE`이 가리키는 timing script 다 | preheat line 수. 값의 정본은<br>`ACFFILE` 이 가리키는 timing script |
| `NXTILE` ᴺ | X 방향 amp tile 수 (chip 2 × strip 8) |  |
| `OSCNPATT` ᴺ | strip 1–8의 overscan 위치 (R=오른쪽, L=왼쪽).<br>**근거는 converter의** **`is_bias_right()`** —<br>`strip_id(amp)=((amp-1)%8)+1`,<br>`is_bias_right(amp)= 1≤amp≤4 or 9≤amp≤12`, amp<br>1–8=TOP·9–16=BO | **근거는 converter 의 `is_bias_right()`**(`:253-266`)<br>— strip 1~4=R, 5~8=L. converter 가 이 카드를 읽지<br>않아 **선언과 하드코딩이 갈라져도 변환 쪽에서 못**<br>**잡는다**(C-5/C-13). 취득 SW 쪽 방어는<br>`test_geometry_vs_converter.py` |
| `PAIRFILE` ᴺ | 짝의 이름. **`FILENAME` 과 같은 형태(확장자**<br>**없음)** | 짝의 이름. converter 는 CLI 로 두 경로를 받으므로 읽지<br>않는다 — **아카이브 도구용이고 그 도구가 아직 없다** |
| `RAWPROD` ᴺ | 이 파일이 CEU Archon science raw임을 선언 | raw 산출물 선언. MEF 는 `DATAPROD` 를 따로 만든다 |
| `RAWVER` ᴺ | **raw 규격/geometry 버전.** 4장이 바뀌면 올린다 | raw 규격/geometry 버전. 4장이 바뀌면 올린다 |
| `RDDIRB` ᴺ | **BOT amp의 물리적 독출 진행 방향** | 〃 |
| `RDDIRT` ᴺ | **TOP amp의 물리적 독출 진행 방향.** MEF amp header<br>`READDIR`로 전달 | MEF amp `READDIR` 로 가야 하는데 converter<br>가 하드코딩(C-12). 실기 확인 필요(OI-3) |
| `ROWORDR` ᴺ | **4.2절 행 순서 규약. 잘못 쓰면 TOP** **half가**<br>**Y 반전된다** | TOP half 의 행 순서 규약.<br>**잘못 쓰면 TOP half 가 Y**<br>**반전된다.** 실기 확인 필요(OI-3) |
| `TCSDRIVE` ᴬ | 망원경 구동 상태.<br>**converter는 `TCSDRIVE`를 먼저 찾고**<br>**없으면 `TCSDRIV`를 본다.**<br>**`TCSDRIVE`(8자)로 쓸 것** |  |
| `TCSLIMIT` ᴺ ᴬ &nbsp;&nbsp; | — |  |
| `TELID` ᴺ ᴬ | ICS relay의 telescope ID |  |
| `VMEA<n>` ᴺ | `MEASURED` |  |
| `VOLT<n>` ᴺ | `VOLTNAME` |  |
| `VOLTN` ᴺ | — |  |
| `VSET<n>` ᴺ | `SETPOINT` |  |
| `VSTA<n>` ᴺ | — |  |
| `VUNI<n>` ᴺ | — |  |

## 5. 팀원 간 검토 요청

v0.1 · v0.2 의 요청을 합치고 중복을 걷었다.  **3장 그룹별 검토 → 이 목록** 순으로 보면 된다.

### 5.1 이름을 정해야 하는 것

1. **`CTRLID` 개칭** — 색인 정수(`1`/`2`)인데 `CTRL1ID`(식별자 **문자열**)와 이름이 너무 닮았다. `CTRLIDX` 등으로 바꿀까? (3장 A절)
2. **`BCKTEMP` ↔ MEF `BOARDTEMP`** — raw 쪽 이름을 MEF 컬럼에 맞출까? (3장 C절)
3. **`SATURAT` ↔ `SATLEVEL`** — **converter 내부에서** 이름이 갈린다(amp 헤더는 `SATURAT`, `AMPINFO` 컬럼은 `SATLEVEL`). 어느 쪽으로 통일할까? (4장 B·C절)

### 5.2 정의를 정해야 하는 것

4. **버전 문자열 9종** (`CAMVER` `CTRLVER` `TIMCONF` `TIMVER` `BIASVER` `CLKVER` `WBTYPE` `ELECSYS` `SIGELEC`) — **근거가 순환한다**(2.4절). converter 가 값을 정하고 → 3위 정의서가 그것을 받아적고 → raw 가 정의서를 근거로 싣는데, **1위 준거인 ICD v4.1 에는 아홉 개가 하나도 없다.** **무엇을 추적하고 · 누가 부여하고 · 언제 올리나?**
   ACF 가 바뀌어도 이 문자열이 안 움직이면 **"없음" 보다 나쁘다** — 진짜 provenance 처럼 읽히기 때문이다.
   후보: (가) 실제 추적 대상이 있는 것만 남기고 폐지 (나) `ACFFILE` 에서 파생 (다) 형식·등록처·증가 조건을 규정하고 유지
5. **`NCTRL`** — 과학 2대인가 전체 3대(가이드 포함)인가? 지금 값 `2` 는 과학만 센 것이다. ICD 침묵 구간이라 **결정해 주기 전에는 정답이 없다.**

### 5.3 MEF 목적지를 만들어야 하는 것

6. **`DATASRC`** — `ARCHON`/`SIM`. **시뮬 프레임이 실측으로 오인되는 것을 막는 유일한 카드**인데 L0 MEF 에 자리가 없다. 사라져도 되나?
7. **`ACFFILE`** — **설정 provenance 의 유일한 포인터**인데 역시 MEF 목적지가 없다.

### 5.4 카드 구성을 정해야 하는 것

8. **색인형 109장** — 전압 45장(`VOLT`/`VSET`/`VMEA`/`VUNI`/`VSTA` × 9) + amp 배선 64장(`AMOD`/`ACHN` × 32).
   대안: (가) 현행 유지 (나) 문자열 한 장으로 압축 — 예: `AMPWIRE='1:1,1:2,…'` (다) calibration DB 로 이전
9. **2.3절에서 레거시에 없는 10개** — 돔 확장 4(`DSAZ` `DSTELAZ` `DALTERR` `DAZERR`) · FSA 환경 4(`FSATEMP` `FSAHUM` `FSADEW` `FSAALRM`) · 영상 점검 2(`CHKIMG` `CHKIMG_C`). sentinel 로 채우는 게 맞나, 아니면 규격에서 빼는 게 맞나?
   **FSA·영상점검 6개는 레거시 raw 헤더에 없었다**(레거시 MEF 는 배경지식이므로 판정 근거가 아니다). 없는 하드웨어를 `NC` 로 채우면 "TC 가 안 보냄" 과 "그런 장치가 없음" 이 섞인다.
   **v0.5 가 여기 넣었던 `DSUP` `DSLW` `DSSAF` `DSAUTO` `DSALT` 다섯은 빠졌다** — 레거시 raw 에 있으므로 계승이지 안건이 아니다(2.3절).

### 5.5 시점을 정해야 하는 것

10. **변경점 C-5 · C-11 · C-12 · C-13 · C-15 · C-17 · C-18** — 전부 converter 쪽 작업이라 취득 SW 가 손대지 않는다. **붙는 시점에 따라 raw 가 지금 실어야 하는 범위가 달라진다.**

## 6. 관련 문서

- raw 규격 — `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 5장(키워드) · 7장(변경점 C-*) · 9장(미결 OI-*)
- **1위 준거** — `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` (`__reference/` 에 바이트 동일 사본)
- **2위 산출 주체** — `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0). 구조는 준거, 값 채움 동작은 미완 구현 (0.2절)
- **3위 정의서** — `../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`. **ICD v4.1 대조 미완** (0.1절 주의)
- **raw 기준선** — `__reference/Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt` (레거시 raw 실측 keyword 123개, 4장 raw 열의 출처)
- 배경지식 — 같은 디렉토리의 **레거시 MEF** 헤더 33건 · `../mef_converter/KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md`(**미갱신**, 판정 근거 아님)
- 결정 기록 — `../project_management/governance/DECISION_LOG.md` D-012 · D-013 · D-014 · D-015
- 취득 SW 구현 — `../ics_sim/ics_sim/rawhdr.py` · `rawpair.py` · `telemetry.py`, 경위는 `../ics_sim/DevNote.md` 11.14
- 등재 — `../project_management/planning/ACTION_REGISTER.md` **ACT-011**

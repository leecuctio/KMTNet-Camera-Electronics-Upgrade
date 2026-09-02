# ArchonGUI 분석 — 소스 3판 · 매뉴얼 대조

작성일: **2026-09-02**

## 대상 판

| 별칭 | 경로(`ArchonGUI/__reference/` 아래) | 정체 |
|---|---|---|
| **stock** | `archongui_v1.0.1259_20250825/` | STA 원본 배포본. 소스 mtime 2024-11-02 |
| **KMTNet** | `archongui_v1.0.1259.KMTNet_20250827/` | KMTNet 개조판. 개조 mtime 2025-08-27 |
| **SSO** | `archongui_v1.0.1259.KMTNet_20260118_SSO/` | 위 개조판을 SSO 리눅스에서 빌드만 한 사본. 2026-01-18 |
| 매뉴얼 | `Archon_manual_20210223.pdf` | STA Archon Manual, Rev 1.0.1166, 2021-02-23, 103쪽 |
| 노트 | `Archon_Readout_Notes_20141030.pdf` | D. Hale(Caltech), ZTF용 독출 노트, 15쪽 |
| 펌웨어 | `ArchonFW/` | `.mcs` **4종** (2026-09-03 에 Rev H 1271 이 추가되고 폴더명이 `ArchonFW_20250825` → `ArchonFW` 로 바뀌었어) |
| 실기 ACF | `__reference/acf/` | **12종** + 타이밍 스크립트 (science 4 · guide 8, 2026-09-03 확충). §5.7 |

줄번호는 별말 없으면 **SSO 트리 기준**이야. stock 은 두 곳 개조 때문에 뒤쪽 줄이 2씩 당겨져 있어(예: RAWSEL 저장은 SSO 2469 = stock 2467).

## 근거 등급 범례

| 표시 | 뜻 |
|---|---|
| **[확정]** | 원문을 직접 봤어 — 소스 `파일:줄`, 매뉴얼 `p.NN`, 실기 ACF 값 |
| **[실측]** | 실기 벤치에서 측정으로 닫혔어 (2026-09-01~02 KASI) |
| **[유력]** | 강한 정황 + 반대 증거 없음. 다만 직접 원문 확인은 못 했어 |
| **[추정]** | 그럴듯한 해석일 뿐, 대안 해석이 살아 있어 |
| **[확인불가]** | 지금 가진 자료로는 못 가려 |
| **[실측대상]** | 실기에 물어봐야만 닫히는 것 |

> 원칙 하나 먼저 명확히 해둘게. **매뉴얼은 정본이 아니야.** 판번이 1.0.1166(2021-02-23)인데 우리 실기 백플레인 FW 는 1.0.1252, GUI 는 1.0.1259 야. 90~100 빌드만큼 뒤처져 있고, 실제로 11군데가 어긋나(§4.6, §10.6). 매뉴얼은 **구조를 이해하는 출처**로 쓰고, 값·범위·명령 목록의 판정은 소스와 실측으로 가야 해.

---

# 1. 한눈에

가장 중요한 결론 여덟 개야.

| # | 결론 | 등급 | 근거 |
|---|---|---|---|
| 1 | **실질적인 판은 세 개가 아니라 둘이야.** KMTNet 과 SSO 는 `src/` 바이트가 완전히 같아(전 파일 diff 무소득). SSO 는 2026-01-18 에 리눅스에서 **빌드만 한 사본**이고, 차이는 `Makefile*`·`.qmake.stash` 뿐이야 | [확정] | `diff -rq` 무출력 |
| 2 | **stock → KMTNet 개조는 `archongui.cpp` 딱 두 곳.** ① 버전 문자열(`:55`) ② Raw Channel Select 콤보 라벨 목록(`:733~738`). 그 밖의 20개 파일·qwt 116개는 손 안 댔어 | [확정] | `diff -r src` 결과가 이 두 덩이뿐 |
| 3 | ⭐ **raw 채널 개조는 의도는 타당한데 구현이 반쪽이야.** 라벨만 ADM 탭 번호로 바꾸고 값을 만드는 `currentIndex()` 는 그대로 뒀어. 첫 블록(1~18)은 우연히 맞고, 둘째 블록(55~72)은 **36 만큼 밀려**. 게다가 되읽기가 15 로 잘려서 ACF 왕복이 깨져 | [유력] (등급 분해는 §2.2(f)(g)) | `archongui.cpp:733~738` vs `:2469`, `:2568` |
| 4 | **벤더 GUI 도 매 프레임 `LOCK`→`FETCH`→`LOCK0` 을 해.** 우리 ICS 루프와 알고리즘이 같아 — "LOCK 이 fetch 를 방해한다" 가설은 이미 죽었어 | [실측] | 다른 세션 결론 인용, §12 |
| 5 | ⭐ **raw 영역은 이미지 fetch 크기에 안 섞여.** `frame_size = (samplemode?4:2)*w*h` 로 이미지를 받고, raw 는 `baseaddr+BUFnRAWOFFSET` 에서 **별도 2차 fetch** 야. 우리 `parse.py` 의 `data_bytes` 는 옳아 — 결함 아니야 | [확정] | `archon.cpp:1282~1289`, `:1361~1364` |
| 6 | **`LOCKT`·`AUTOFETCH` 는 벤더 GUI 소스에도 없어.** `grep -rn "LOCKT\|AUTOFETCH" src/*.cpp src/*.h` → **0건**. GUI 의 "Auto Fetch" 는 체크박스 이름일 뿐이고 와이어 명령 `AUTOFETCH` 와 무관해. ⭐ 그리고 새로 받은 **FW 1271 에는 `LOCKT` 이 없고 `FASTAUTOFETCH` 가 새로 생겼어**(§10.1.1) | [확정] / 1271 대조는 [유력] | grep · FW 이미지 문자열 대조 |
| 7 | **모듈 형 번호의 정본은 `archon.h` 의 0~19 야.** 매뉴얼 p.46 은 6(ATLAS)이 빠졌고 "16+: Unknown" 이라 우리 science 의 비디오 모듈 두 장(형 17 ADM)이 통째로 Unknown 으로 찍혀 | [확정] | `archon.h:29~48` vs 매뉴얼 p.46 |
| 8 | **설정 적용에 "부분 갱신" 이란 게 없어.** 어느 Apply 버튼을 눌러도 `POLLOFF`→`CLEARCONFIG`→`WCONFIG` 전체 재전송→`POLLON`→`APPLYxxx` 야. 슬롯 하나만 Apply 해도 수천 줄이 다시 올라가 | [확정] | `archon.cpp:1406~1436` |

---

# 2. 세 판의 차이 — 그리고 raw 채널 개조의 진상

## 2.1 판별 대조표

| 항목 | stock | KMTNet | SSO |
|---|---|---|---|
| 경로 | `archongui_v1.0.1259_20250825/` | `..._20250827/` | `..._20260118_SSO/` |
| `src/` 파일 수 | 20 + qwt 116 | 동일 | 동일 |
| `src/` 내용 | — | stock 대비 2곳 | **KMTNet 과 바이트 동일** |
| 소스 mtime | 2024-11-02 | 2025-08-27 | 2026-01-18(복사 시각) |
| `archongui.pro` | 동일(3판 모두) | 동일 | 동일 |
| `archongui.pro.user` | **없음** | 있음 | 있음(KMTNet 것과 md5 동일) |
| 빌드 산출물 | 없음 | 없음 | `Makefile`·`Makefile.Debug`·`Makefile.Release`·`.qmake.stash` |
| 판정 | 원본 | **실질 개조본** | 개조본의 빌드 사본 |

세 판의 `src/` 를 다 비교하면 이게 전부야 [확정]:

```
55c55
< 	GUIVersion = "Archon GUI 1.0.1259";
---
>     GUIVersion = "Archon GUI 1.0.1259.KMTNet";

734,736c734,738
< 	for (i = 1; i <= 32; i++)
< 		rawsel->addItem(QString::number(i));
< 	gl->addWidget(rawsel, y++, 1);
---
>     for (i =  1; i <= 18; i++)
>         rawsel->addItem(QString::number(i));
>     for (i = 55; i <= 72; i++)
>         rawsel->addItem(QString::number(i));
>     gl->addWidget(rawsel, y++, 1);
```

개조된 줄은 원본의 **탭 들여쓰기 대신 스페이스**를 써 — 편집 흔적이 그대로 남아 있어. 그리고 `archongui.pro.user` 를 열어보면 개조 환경까지 나와 [확정]:

- `<!-- Written by QtCreator 3.2.1, 2025-08-27T04:54:11. -->`
- 킷 이름 `Desktop Qt 5.3 MinGW 32bit`
- 작업 경로 `C:/Users/kmtnet/Downloads/archongui (2)/archongui.pro`

즉 **윈도우 머신에서 `kmtnet` 계정이 Qt Creator 3.2.1 로 열어 고쳤어.** Qt Creator 기본 편집기가 스페이스 들여쓰기를 쓰니까 위 흔적과 앞뒤가 맞아. 그런데 정작 SSO 빌드는 리눅스 Qt 5.15.13 / g++ 13.3 으로 했고, `Makefile.Release` 의 `DISTDIR` 이 `/home/rtkmtnet/SMC/archongui_v1.0.1259.KMTNet_20250827/...` 를 가리켜 — **SSO 사본이 20250827 트리를 그대로 옮겨 빌드한 것**이라는 증거야 [확정].

## 2.2 ⭐ raw 채널 개조의 진상 (이 보고서의 핵심 절)

### (a) 매뉴얼이 규정한 것 — `RAWSEL` 의 정의

매뉴얼은 **두 군데**에서 `RAWSEL` 을 정의해 [확정]:

> **p.56** — "RAWSEL — Select the AD channel for raw data capture, **from 0 to 15**."
>
> **p.70** — "Set the RAWSEL key to the desired AD channel (**0 for channel 1 of the ADC module in slot 5 through 15 for channel 4 of the ADC module in slot 8**)."

그리고 GUI 장에서 화면 라벨 규약도 못박아 [확정]:

> **p.76** — "The Raw Channel Select field selects the raw capture channel. **1 - 4 selects a channel from the first ADC slot, 5 - 8 from the second ADC slot, etc.**"

세 문장을 합치면 규약은 이래.

- 비디오 슬롯은 **5·6·7·8 넷**. 물리적 제약이야 — p.20 이 "ADC modules can only be installed in the **central 4 slots (5-8)**, which have an additional connector that carries the high speed ADC data" 라고 적어놨고, 그 J4 커넥터가 그 4칸에만 있어(Figure 10, p.21) [확정].
- 고전 AD 는 슬롯당 4채널 → 전역 채널 1~16, `RAWSEL` 은 그 **0기점**이라 0~15.
- 산식은 **슬롯 점유 여부와 무관한 고정 사상**이야. 슬롯 6·7 이 비어 있어도 번호가 당겨지지 않아.

```
RAWSEL = (slot - 5) × 슬롯당채널수 + (channel - 1)          ← 0기점
탭 번호 = (slot - 5) × 슬롯당채널수 + channel                ← 1기점, TAPLINE 이 쓰는 번호
```

같은 p.70 이 TAPLINE 쪽 산식도 규정해 [확정]:

> AD: "'tap' is a string of the form **ADnd**, where n is 1 to 16 … 1 for the first channel from an ADC module in backplane slot 5 … up to 16 for the fourth channel from an ADC module in backplane slot 8."
>
> ADM: "'tap' is of the form **AMnd**, where **n is 1 to 72** … **ADM channels 1 to 18 map to slot 5, channels 19 to 36 map to slot 6, and so on.**"

| 모듈형 | 슬롯당 채널 | 슬롯5 | 슬롯6 | 슬롯7 | 슬롯8 | 상한 | 접두 |
|---|---|---|---|---|---|---|---|
| AD (형 2) | 4 | 1–4 | 5–8 | 9–12 | 13–16 | 16 | `AD` |
| ADM (형 17) | 18 | **1–18** | 19–36 | 37–54 | **55–72** | 72 | `AM` |

실기 ACF 와 정확히 맞아떨어져 [확정]: science 는 ADM 이 슬롯 5·8 → 탭 `AM1L`~`AM16R` + `AM55L`~`AM70R` (32탭). guide 는 AD 가 슬롯 5·6 → `AD1`~`AD8` (8탭).

### (b) 결정적 증거 — GUI 는 `currentIndex()` 를 값으로 써

여기가 갈림길이야. 콤보박스에 채운 숫자는 **라벨일 뿐**이고, 설정에 들어가는 값은 **선택 순번**이야 [확정].

```cpp
// archongui.cpp:2469  (parseUI — 저장·전송 경로)
config.insert("RAWSEL", QString::number(rawsel->currentIndex()));
```

```cpp
// archongui.cpp:2568  (updateUI — 불러오기 경로)
rawsel->setCurrentIndex(qBound(0, config.value("RAWSEL").toInt(), 15));
```

**이 두 줄은 stock 과 글자 하나 안 다르게 똑같아** (stock 의 `:2467`, `:2566`). 즉 **KMTNet 개조가 손대지 않은 줄이야** [확정]. `addItem` 에 `userData` 를 붙이지도 않았으니 라벨과 값을 잇는 다른 통로도 없어.

stock 에서는 항목이 `"1"`~`"32"` 로 연속이라 `인덱스 = 라벨 − 1` 이 성립해서 매뉴얼 규약(라벨 = 값+1)과 우연히 맞아떨어졌어. **그런데 KMTNet 목록은 18 에서 55 로 건너뛰어서 그 등식이 깨져.**

### (c) 산식 대조 — 어디서 어긋나나

| 사용자가 고른 라벨 | 콤보 인덱스 | 전송되는 `RAWSEL` | 매뉴얼 고정사상이 요구하는 값 | 판정 |
|---|---|---|---|---|
| 1 | 0 | 0 | 0 | ✅ 맞아 |
| 18 | 17 | 17 | 17 | ✅ 맞아 |
| **55** | 18 | **18** | **54** | ⚠️ **36 밀림** |
| **70** | 33 | **33** | **69** | ⚠️ 36 밀림 |
| **72** | 35 | **35** | **71** | ⚠️ 36 밀림 |

- **첫 블록(라벨 1~18 → 인덱스 0~17)은 정합해.** (라벨−1) 이 인덱스와 같아서 우연히 맞은 거야.
- **둘째 블록(라벨 55~72 → 인덱스 18~35)은 어긋나.** 필요값 54~71 인데 18~35 가 나가 — **정확히 36 만큼 모자라.**
- 그리고 개조판이 낼 수 있는 최대 `RAWSEL` 은 **35** 야. 슬롯 8 대역(54~71)에는 **개조판도 못 닿아.** stock(최대 31)보다 4 늘어난 게 전부인 셈이야.

라벨 "55"(= 슬롯 8 의 첫 채널 AM55)를 고르면 나가는 `RAWSEL=18` 은 매뉴얼 고정사상으로는 **AM19 = 슬롯 6 의 첫 채널**이야. 그런데 science 실기는 `MOD6_TYPE=0` — **빈 슬롯**이야 [확정].

### (d) 왕복 파손 — 개조와 무관한 stock 결함이 겹쳐

`archongui.cpp:2568` 의 `qBound(0, …, 15)` 는 **매뉴얼 p.56 의 옛 상한 0~15 가 화석처럼 남은 줄**이야. 콤보 항목은 stock 32칸, KMTNet 36칸인데 되읽기는 15 까지만 받아 [확정]. 결과는 이래.

1. ACF 에 `RAWSEL=54` 가 적혀 있어도, 파일을 열면 콤보가 **인덱스 15(라벨 "16")** 로 조용히 잘려.
2. 그 상태에서 아무 Apply 나 누르면 `parseUI()` 가 **`RAWSEL=15` 를 컨트롤러에 써버려.**
3. ACF 를 다시 저장하면 파일 값까지 15 로 덮여.

경고도 로그도 없어. **즉 KMTNet 이 새로 붙인 55~72 구간은 세션 안에서 고를 수는 있어도 파일로 왕복시키면 절대 살아남지 못해.** 개조가 완결되려면 이 줄도 같이 고쳐야 해(`qBound(0, …, rawsel->count()-1)`).

### (e) 실사용 흔적 — 없어

| ACF | `RAWENABLE` | `RAWSEL` | 개조판 GUI 표시 | stock GUI 표시 | 클램프(≤15) |
|---|---|---|---|---|---|
| science (`KMTK_SCI_113`, `KMTC_SCI_101`) | 1 | **3** | "4" | "4" | 통과 |
| guide (`KMTK_GUI_162`) | 1 | **4** | "5" | "5" | 통과 |

둘 다 첫 블록(≤15)만 써 [확정]. 그래서 **현행 ACF 로는 stock 과 개조판이 완전히 같게 동작해.** 개조가 의미를 갖는 건 라벨 19 이상(인덱스 18↑)을 고를 때뿐인데, 바로 거기가 값이 어긋나는 지점이야. 개조자가 실제로 슬롯 8 raw 를 떠 봤다면 이상을 눈치챘을 텐데, ACF 가 3/4 인 걸 보면 **이 경로를 한 번도 안 밟은 것으로 보여** [유력].

두 실측값 자체는 규약과 모순이 없어 — science `RAWSEL=3` → AM4 = 슬롯 5 ADM 의 4번 채널(TAPLINE 1–16 안에 있음). guide `RAWSEL=4` → AD5 = 슬롯 6 AD 의 1번 채널(`MOD6_TYPE=2`, TAPLINE 에 AD5–8 있음). 둘 다 정상이야 [확정].

### (f) 남은 유보 — 정직하게

여기가 중요해. 위 판정을 **확정으로 올리면 안 되는 이유**가 셋 있어.

1. **매뉴얼은 고전 AD(4채널) 기준 0~15 만 적어.** ADM 이 슬롯당 18채널이라는 것과 `RAWSEL` 상한이 71 이라는 건 **매뉴얼 어디에도 없어.** 그건 우리 프로젝트의 ACF 실측(슬롯5→1.., 슬롯8→55.. 로 3칸에 54 차이 → 슬롯당 18)과 `ics_archon/archon/parse.py` 주석("ADM 18채널·18bit·12.5MHz")에서 온 거야. 그러므로 **"둘째 블록이 36 밀렸다" 는 유력한 추론이지 매뉴얼로 확정된 사실이 아니야** → **[유력], 최종 판정은 [실측대상]**.
2. **대안 해석 (B) 가 아직 살아 있어.** 현행 FW 가 `RAWSEL` 을 "**장착된 AD 계열 모듈만 조밀하게 센 순번**" 으로 해석한다면(슬롯5 ADM = 0~17, 슬롯8 ADM = 18~35), 개조는 **의도대로 정확히 동작해.** 36개 항목 = ADM 2장 × 18채널이라는 수치도 절묘하게 맞고, 개조자가 값 변환 없이 라벨만 고친 것도 (B)를 전제했다는 정황이야. 다만 (B)는 ⓐ 매뉴얼 p.70 이 슬롯을 **점유 여부와 무관하게 균등 분할**한다고 규정한 것과 어긋나고, ⓑ stock 의 32항목을 설명 못 해. → **[확인불가]**
3. **stock 목록 `1..32` 의 출처를 확정 못 했어.** 소스에는 맨 리터럴 하나뿐이고(`for(i=1;i<=32;i++)`), 32 를 만드는 상수·계산·주석이 **소스 어디에도 없어** [확정]. 매뉴얼 상한은 16. 4슬롯 × 8채널(ADX/ADF 급)로 읽으면 딱 떨어지지만, `AD`/`ADF`/`ADX`/`ADLN` 클래스가 전부 클램프 4칸(`AD_COUNT = 4`)이라 GUI 로는 8채널짜리 모듈이 없어. → **[추정], 근거 없음**.

그리고 하나 더 — **산식은 GUI 에 없어.** GUI 는 TAPLINE 을 **자유 텍스트로만** 다뤄(`archongui.cpp:1428~1445`, `2476~2478`). `AM<n><L|R>` 이름을 파싱하거나 슬롯→채널 산식을 계산하는 코드가 GUI 에는 **0줄**이야 — `grep '"AM' *.cpp` 도 무소득 [확정]. 산식은 전적으로 펌웨어 쪽 지식이고, 그래서 **GUI 소스만으로는 ADM 채널 수도, `RAWSEL` 해석도 확정할 수 없어.**

### (g) 개조 판정 요약

| 항목 | 판정 | 등급 |
|---|---|---|
| 개조의 **의도** | 타당해. 둘째 ADM(슬롯 8, AM55~72) 채널을 raw 로 보고 싶었던 거고, stock 라벨 1~32 로는 그 이름을 화면에 띄울 수조차 없었어 | [유력] |
| 라벨 선택(슬롯 전폭 18채널씩) | 매뉴얼 p.70 의 18채널 구조와 정확히 맞는 선택이야 | [확정] |
| 첫 블록 (라벨 1~18 → 값 0~17) | **맞아.** (라벨−1)=인덱스라 우연히 정합 | [확정] |
| 둘째 블록 (라벨 55~72 → 값 18~35) | ⚠️ **36 만큼 밀렸어.** 필요값 54~71 | [유력] / 최종 [실측대상] |
| 왕복(불러오기) | ⚠️ **깨져.** `qBound(…,15)` 가 잘라내 | [확정] |
| 실사용 흔적 | **없어.** 실기 ACF 는 3·4 | [확정] |
| 고치려면 | `:2469` 를 `currentText().toInt()-1` (또는 사상표)로, `:2568` 의 상한을 `count()-1` 로. **단 실측으로 (A)/(B) 를 먼저 가른 뒤에** | — |

### (h) 판정을 닫는 실측 절차

1. science 컨트롤러에 `RAWENABLE=1`, `RAWSEL=54` 를 ACF 텍스트 편집(또는 `WCONFIG` 직접)으로 넣고 `APPLYCDS`.
   - `?xx` 거부가 나오는지 → FW 가 16 이상을 아예 안 받으면 (B)도 (A)도 아닌 제3의 답이야.
   - `FRAME` 응답의 `BUFnRAWBLOCKS` 가 정상으로 잡히는지 확인.
2. raw 파형이 **슬롯 8 ADM 의 채널 1(AM55)** 로 나오는지 대조(슬롯 8 에만 신호를 넣고 보는 게 제일 깔끔해).
3. 안 나오면 `RAWSEL=18` 로 같은 시험. 여기서 슬롯 8 이 나오면 **(B) 확정 → 개조가 옳고 고칠 건 클램프뿐**이야.
4. GUI 로는 두 값 다 입력이 안 돼(클램프). 파일을 손으로 고치거나 GUI 밖 경로로 넣어야 해.

---

# 3. 전체 구조

## 3.1 파일별 역할 (줄 수 포함)

`src/` 는 자체 소스 20개(`.cpp` 10 + `.h` 10, 합 **13,870줄**) + `src/qwt/` 116개야 [확정].

| 파일 | 줄 | 역할 | 도메인 지식 |
|---|---:|---|---|
| `archongui.cpp` | **4,383** | GUI 본체. 위젯 트리, 탭 13개, 폴링, ACF/NCF 입출력, 영상·플롯·PTC·FITS | 최다 |
| `archongui.h` | 386 | `TArchonGUI` 선언. `RMap` 네 개(`system`/`status`/`frameStatus`/`config`)가 여기 | |
| `modules.cpp` | **5,350** | 모듈 클래스 15개 구현. UI 생성 · 설정키 조립 · STATUS 파싱 | 모듈별 전부 |
| `modules.h` | 715 | `TModule` 기반 + 파생 15개 선언. 채널 수 상수 | |
| `archon.cpp` | **1,707** | 통신 스레드. 와이어 프로토콜, 명령 함수, 플래시, `fetchFrame` | 프로토콜 전부 |
| `archon.h` | 154 | `Archon` 선언. `BURST_LEN` · `RAW_BLOCK_SIZE` · `MOD_TYPE_*` · `POWER_STATES` | **형 번호 정본** |
| `imagewidget.cpp` | 435 | 픽셀 → QImage 렌더링. LUT, 확대, 마우스 규약 | 없음 |
| `imagewidget.h` | 60 | | |
| `frames.cpp` | 253 | `TFrameBuffer` — malloc/free 래퍼 | **없음** |
| `frames.h` | 34 | 필드 9개. `m_hdr` 가 16/32bit 분기 | |
| `imagescrollwidget.cpp` | 74 | `ImageWidget` 을 `QScrollArea` 로 감싼 껍데기 | 없음 |
| `imagescrollwidget.h` | 30 | | |
| `powerwidget.cpp` | 62 | 색칠한 네모 하나 = 전원 표시등 | 없음 |
| `powerwidget.h` | 47 | | |
| `simpleprogress.cpp` | 55 | 자작 진행바(`QProgressBar` 대체) | 없음 |
| `simpleprogress.h` | 48 | | |
| `updatetimer.cpp` | 42 | `msleep(500); emit update();` 무한반복 스레드 | 없음 |
| `updatetimer.h` | 23 | | |
| `main.cpp` | **12** | `QApplication` + `argv[1]` 을 열 프레임 파일로 전달 | 없음 |
| `src/qwt/` | 116 파일 | 플롯 라이브러리(벤더 동봉) | — |

도메인 지식이 `archon.cpp`(프로토콜) · `archongui.cpp`(화면·파일) · `modules.cpp`(모듈)에만 몰려 있고, 나머지 11개는 **전부 바보 부품**이야. 프로토콜 문자열이나 ACF 키가 단 하나도 안 나와 [확정].

## 3.2 스레드 모델 — 딱 셋

| 스레드 | 클래스 | 하는 일 | 이벤트 루프 |
|---|---|---|---|
| **GUI** | `TArchonGUI` | 위젯 전부 + `poll()` 슬롯까지 여기서 돌아 | 있음 |
| **통신** | `Archon : QThread` | 소켓을 독점. 명령 문자열 하나를 받아 TCP 로 주고받고 시그널로 결과 반환 | **없음**(`exec()` 안 부름, `forever` 폴링 루프) |
| **틱** | `TUpdateTimer : QThread` | `while(!thread_exit){ msleep(500); emit update(); }` — 그게 다야 | 없음 |

핵심 설계 두 가지 [확정]:

- **`socket` 을 `run()` 안에서 생성해**(`archon.cpp:57`). 즉 `QTcpSocket` 이 작업자 스레드에 귀속돼서 GUI 스레드가 소켓을 건드릴 일이 원천적으로 없어. 그래서 락 하나(`mutex`)로 **명령 인수인계만** 지키면 돼.
- **명령 슬롯은 깊이 1짜리 우편함이야.** 큐가 아니야. `command()` 세 오버로드(`archon.cpp:184~227`)가 전부 이 모양이야:

```cpp
mutex.lock();
if (CommandInProgress) { mutex.unlock(); return 1; }   // 바쁘면 즉시 거절 — 명령은 버려져
CommandInProgress = true;
NewCommand = cmd;
mutex.unlock();
return 0;
```

`getResult()`(`archon.cpp:229~245`)는 `!CommandInProgress` 가 될 때까지 `msleep(50)` 으로 도는 **바쁜 대기**야. GUI 스레드에서 부르면 이벤트 루프가 그동안 멈춰. 그래서 사용자 동작 슬롯들은 첫 줄에 `getResult()` 를 놓아 "직전 폴링이 끝날 때까지 기다렸다가 새로 던진다" 로 써.

프레임 데이터용 락은 **완전히 별개**야 — `frames`(`QVector<TFrameBuffer>`)와 `frameMutex` 가 `archon.h:74~75` 에서 **public** 이고, 명령용 `mutex`(private, `:88`)와 안 겹쳐. 프레임은 GUI 가 직접 만지고, 명령 인수인계는 안 만지는 구조야 [확정].

## 3.3 계층 다이어그램

```
                         main.cpp (12줄)  --argv[1]-->  열 프레임 파일
                              |
                    +---------v------------------------------------------+
                    |  GUI 스레드   TArchonGUI (archongui.cpp 4383줄)     |
                    |                                                    |
   TUpdateTimer --> |  poll()  --STATUS/FRAME 번갈아--+                   |
   (500 ms 틱)      |                                 |                   |
                    |  RMap system      <--msgSystem--+                   |
                    |  RMap status      <--msgStatus--+   (큐 연결)        |
                    |  RMap frameStatus <--msgFrameStatus                 |
                    |  RMap config      --setConfig()-+                   |
                    |       ^  v                      |                   |
                    |  parseUI / updateUI             |                   |
                    |       ^  v                      |                   |
                    |  위젯 트리                       |                   |
                    |   |- 고정 탭 13개                |                   |
                    |   +- 모듈 탭 N개 <-- TModule 파생 15종 (modules.cpp) |
                    |        +- systemTabs / waveformTabs / vcpuTabs      |
                    |  ImageScrollWidget -> ImageWidget -> TFrameBuffer   |
                    +----------------+-----------------------------------+
                                     | command() — 깊이 1 슬롯
                    +----------------v-----------------------------------+
                    |  통신 스레드  Archon : QThread (archon.cpp 1707줄)   |
                    |   run(): forever { 명령 꺼내기 -> if/else 디스패치    |
                    |                    -> msleep(10) -> interfaceFlush()}|
                    |   interfaceCommand()        <- 텍스트 1:1           |
                    |   interfaceBinaryCommand()  <- 이진 1024 B 블록      |
                    |   frames[] + frameMutex  (public — GUI 가 직접 만짐) |
                    +----------------+-----------------------------------+
                                     | QTcpSocket, TCP 4242
                    +----------------v-----------------------------------+
                    |  Archon 백플레인 (X12, Rev F, FW 1.0.1252)          |
                    |   슬롯 1..12 -> 모듈 FPGA (타이밍 코어 · VCPU)       |
                    |   DDR3 2 GB -> 프레임 버퍼 512 MB x 3               |
                    +----------------------------------------------------+
```

## 3.4 고정 탭 13개

`fixedTabs = 13` (`archongui.cpp:107`). 소스 주석은 "Twelve tabs" 라는데 실제로는 13개야 — 주석이 낡았어 [확정].

| idx | 탭 | 만든 줄 | 역할 |
|---:|---|---:|---|
| 0 | System | 114 | 백플레인·모듈 인벤토리, 프레임버퍼 3행 + Fetch, 컨트롤러 네트워크 설정, Status, Power 레일표, 트리거·팬·부팅 옵션 |
| 1 | Timing Script | 519 | 스크립트 편집 + Load Timing / Reset / Hold / Release |
| 2 | Timing States | 546 | 상태 목록 + Control 탭 + 모듈별 신호 탭 |
| 3 | Parameters | 624 | 파라미터·상수 + Apply / Test |
| 4 | VCPU | 653 | 모듈별 VCPU 탭 컨테이너 |
| 5 | CDS / Deint | 661 | SHP/SHD, PCLKDELAY, SAMPLEMODE, PIXELCOUNT/LINECOUNT, FRAMEMODE, BIGBUF, **RAW\* 전부**, TAPLINE |
| **6** | **Image** | 771 | 영상 표시 |
| 7 | Horizontal Plot | 862 | |
| 8 | Vertical Plot | 892 | |
| 9 | PTC Plot | 922 | |
| **10** | **Raw Image** | 965 | |
| 11 | Horizontal Raw Plot | 1018 | |
| 12 | Vertical Raw Plot | 1050 | |
| 13~ | Slot N: TYPE | `modules.cpp` | 모듈 탭. `parseSystem()` 이 만들고 지워 |

**인덱스 6·10 이 하드코딩돼 있어** — `imageMouseXY` 는 `currentIndex()==6` 일 때만(`:3005`), `rawImageMouseXY` 는 `==10` 일 때만(`:3118`), 커맨드라인 로드 성공 시 `setCurrentIndex(6)`(`:1252`). 탭을 하나 끼워넣으면 세 군데가 어긋나 [확정].

## 3.5 `-small` 인자와 첫 인자 함정

`-small` 은 중앙 위젯을 `QScrollArea` 에 넣는 것 **딱 하나**야(`:58~68`). 그런데 `main.cpp:9` 가 `TArchonGUI w(a.arguments().value(1))` 로 **첫 인자를 무조건 열 파일명으로** 넘겨. 그래서 `archongui -small` 로 실행하면 `loadFilename == "-small"` 이 되고, 파일 열기는 실패하지만 그 전에 `filenameLabel->setText("-small")` 을 해버려서 **상태바에 "-small" 이 파일명처럼 남아**(`:3694~3698`). 파일과 옵션을 같이 주려면 `archongui frame.raw -small` 순서로 줘야 해 [확정].

---

# 4. 통신 프로토콜

## 4.1 와이어 형식

매뉴얼 p.45 와 `archon.cpp:318~383` 이 완전히 일치해 [확정].

| 방향 | 형식 | 비고 |
|---|---|---|
| 요청 | `>XX<명령>\n` | `>` + **대문자 2자리 16진** 참조번호 + 명령 + LF(0x0A). CR 안 씀. 인코딩 Latin-1 |
| 성공 | `<XX<응답>\n` | 앞 3바이트(`<XX`)를 떼고 나머지를 반환(`:366`). **ASCII 응답에 `:` 는 없어** |
| 오류 | `?XX\n` | 이유는 안 알려줘. `LOGERROR("Error parsing command")` → 반환 1 (`:369~370`) |
| 이진 | `<XX:` + **정확히 1024 B** | 4바이트 프리앰블 + 원시 데이터, **종료 개행 없음** |

접속은 **TCP 포트 4242 하드코딩**(`archongui.cpp:2668`), 기본 주소 `10.0.0.2`(`:86`). 포트를 바꿀 UI 가 없어 [확정].

> ⚠️ System 탭의 "Network Configuration"(`leIP`/`leNetmask`/`leGateway`, `:305~313`)은 **접속용이 아니야.** 컨트롤러 자신의 IP 설정값이고 `config` 의 `IP`/`NETMASK`/`GATEWAY` 키로 들어가 `APPLYNET` 으로 써넣는 거야. 이름이 비슷해서 헷갈리기 딱 좋아.

## 4.2 참조번호와 재동기화

```cpp
socket->readAll();                      // 335  잔류 바이트 폐기
last_msgref = msgref;                   // 336
msgref = (msgref + 1) & 0xFF;           // 337  0x00~0xFF 순환
cmd.prepend(">" + hex(last_msgref, 2)); // 338
```

- `msgref` 는 **명령을 실제로 보낼 때만** 증가해. `cmd` 가 비어 있으면 336~338 을 통째로 건너뛰어.
- **참조번호가 안 맞는 줄은 조용히 버려지고 루프가 계속 돌아**(`:362`). `break` 도 `LOGERROR` 도 없어. 늦게 온 이전 응답이 현재 명령을 오염시키지 않게 하는 장치야.
- `?` 조차 참조번호가 맞아야 오류로 잡혀(`:369`).

`last_msgref` 가 지역변수가 아니라 **멤버**(`archon.h:107~108`)인 이유가 핵심이야. `VERIFY`·`FETCH` 는 명령 하나에 컨트롤러가 **블록 여러 개를 연달아** 보내는데(매뉴얼 p.50~51), 그 블록들이 **전부 같은 참조번호**를 달고 와. 그래서 호출부가 두 번째부터 `s.clear()` 로 **빈 명령**을 넘겨서 아무것도 안 보내고 `last_msgref` 를 보존한 채 다음 블록만 읽어(`:979~980`, `:1354~1356`) [확정].

> ⚠️ 잔가지 결함: `response.mid(1,2).toInt(&ok,16)` 에서 **`ok` 를 검사 안 해**(`:362`, `:432`, `:509`). 16진이 아니면 `toInt` 가 0 을 반환하는데 마침 `last_msgref` 가 0 이면 엉뚱한 줄이 매칭될 수 있어. `msgref` 는 256번마다 0 을 지나가 [확정, 심각도 낮음].

## 4.3 ⭐ 인식 못 한 명령 = 무응답

매뉴얼 p.45 가 명시해 [확정]:

> "Unrecognized commands are ignored."

즉 오타 명령은 `?` **조차 안 와.** 그러면:

1. 명령은 이미 나갔고 `msgref` 도 소비됐어
2. 응답 루프가 `waitForReadyRead(10)` 을 돌며 대기
3. `timeout`(보통 5초)을 **통째로 소모**한 뒤 `LOGERROR("Timeout waiting for response")`(`:356`)
4. 로그에 `! interfaceCommand: Timeout waiting for response (…archon.cpp:356)` 찍고 반환 1
5. `run()` 루프 끝의 `interfaceFlush()`(`:174`)가 늦게 온 응답을 버려줘서 다음 명령은 안 오염돼

**재시도는 없어.** 그리고 컨트롤러는 **절대 먼저 말을 안 걸어**(매뉴얼 p.45: "The controller only responds to commands, it never initiates a message"). 그래서 프레임이 완성돼도 푸시 알림 같은 건 없고 호스트가 `FRAME` 을 폴링해야 해.

`DIRECT` 명령창(`archon.cpp:1676~1687`)으로 사용자가 아무 문자열이나 보낼 수 있으니 이 경로는 실제로 밟히는 경로야.

## 4.4 명령 목록과 타임아웃

| 명령 | GUI 함수 | 타임아웃 | 매뉴얼 | 비고 |
|---|---|---:|---|---|
| `SYSTEM` | `getSystem()` | 5 s | p.46 | 연결 시 1회. 모듈 탭이 생기는 유일한 계기 |
| `STATUS` | `getStatus()` | 5 s | p.47~49 | 폴링. `LOG=n` 만큼 `FETCHLOG` 반복 |
| `FRAME` | `getFrameStatus()` | 5 s | p.50 | 폴링 |
| `FETCHLOG` | (getStatus 안) | 5 s | p.50 | 가장 오래된 로그 1건 |
| `TIMER` | — | — | p.49 | **GUI 는 안 써** |
| `WCONFIG…` | `writeConfig()` | 5 s | p.51 | 최대 16384줄, 줄당 2048자 |
| `RCONFIG…` | — | — | p.51 | **GUI 는 안 써** |
| `CLEARCONFIG` | `writeConfig()` | 5 s | p.51 | |
| `APPLYALL` | `applyAll()` | **30 s** | p.51 | 끝나면 **CCD 전원 OFF** |
| `APPLYSYSTEM` | `applySystem()` | 5 s | p.53 | |
| `APPLYCDS` | `applyCDS()` | 5 s | p.53 | RAW\*·TAPLINE\*·SHP/SHD·FRAMEMODE |
| `APPLYMODxx` | `applyModule()` | 10 s | p.52 | `xx` 는 **0기점 2자리 16진**. 슬롯5 → `APPLYMOD04` |
| `APPLYDIOxx` | `applyModuleDIO()` | 10 s | p.53 | DIO **+ VCPU** |
| `APPLYNET` | `applyNet()` | 5 s | p.53 | **연결 끊겨** |
| `LOADTIMING` | `loadTiming()` | 5 s | p.51 | **코어 리셋** |
| `LOADPARAMS` | `loadParams()` | 5 s | p.52 | 리셋 없음. 목록 첫 번째부터 하나씩 |
| `LOADPARAM p` | `loadParam()` | 5 s | p.52 | 하나만 |
| `PREPPARAM` / `FASTLOADPARAM` / `FASTPREPPARAM` | — | — | p.52 | **GUI 는 안 써** |
| `RESETTIMING` | `resetTiming()` | 5 s | p.52 | 스크립트 1행부터 재시작 |
| `HOLDTIMING` / `RELEASETIMING` | | 5 s | p.52 | 다중 컨트롤러 동기용 쌍 |
| `POWERON` / `POWEROFF` | | **30 s** | p.51 | **`APPLYALL` 이 전제** |
| `LOCKn` (n=1..3) | `lockFrame()` | 5 s | p.50 | **n=0 이면 전체 해제** |
| `FETCH<8hex><8hex>` | `fetchFrame()` | 5 s(무음 기준) | p.51 | 1024 B 블록 단위 |
| `ERASE<8hex><8hex>` | `flash()` | **3 s** | p.50 | 섹터 하나당 |
| `FLASH<addr><2048자>` | `flash()` | 5 s | p.51 | 명령 1줄이 2,061~2,065자 |
| `VERIFY<addr><cnt>` | `verify()` | 2 s/블록 | p.51 | 그룹 256블록 = 256 KiB |
| `ERASEMODxx` | `flashMod()` | **200 s** | p.50 | 모듈 전체를 한 번에 |
| `FLASHMOD` / `VERIFYMOD` | | 5 s / 2 s | p.50 | 그룹 16블록 = 16 KiB |
| `REBOOT` / `WARMBOOT` | | 5 s | p.51 | 둘 다 **연결 끊겨**. 반환값 무시 |
| `FLASHACTIVECONFIG` / `ERASESTOREDCONFIG` | | **60 s** | p.52~53 | **반환값 무시 — 저장 실패가 GUI 에 안 알려져** |
| **`POLLON` / `POLLOFF`** | `writeConfig()` 내부 | 5 s | **없음** | 미문서 명령 |
| **`BIASPOLLON` / `BIASPOLLOFF`** | `pollOn()`/`pollOff()`, 플래시 계열 | 5 s | **없음** | 미문서 명령 |
| **`ATLASMOVE`** | `atlasMove()` | 5 s | **없음** | 미문서 명령 |
| `LOCKNEWEST` | `lockNewestFrame()` | — | — | **GUI 내부 이름.** 결국 `LOCK`+n 을 보내(`:673`) |

기본값 `ARCHON_TIMEOUT = 5000` ms (`archon.cpp:15`) [확정]. 매뉴얼에는 **명령 소요시간이 한 줄도 안 적혀 있어** [확인불가].

> ⚠️ **`POLLON/POLLOFF` 와 `BIASPOLLON/BIASPOLLOFF` 는 서로 다른 명령이야.** `writeConfig()` 는 `POLLOFF`/`POLLON` 을 쓰고(`:1413`, `:1428`), `Archon::pollOn()/pollOff()` 는 `BIASPOLLON`/`BIASPOLLOFF` 를 써(`:1498`, `:1511`), 플래시·검증 계열도 전부 `BIASPOLL*` 을 써. **GUI 바닥의 "Polling On/Off" 버튼은 바이어스 폴링을 끄는 거지 GUI 의 500 ms 틱을 끄는 게 아니야.** 함수명이 헷갈리게 붙어 있고, 둘 다 매뉴얼에 없어서 정확한 의미 차이는 [확인불가].

## 4.5 오류 처리 · 부분 실패

`LOGERROR` 매크로(`archon.cpp:10`)가 `__LINE__` 을 저장해서 **로그만 보고 소스 몇 번째 줄에서 터졌는지** 바로 알 수 있어. 형식은 `! 함수명: 메시지 (파일:줄)` 이고 `!` 로 시작하는 게 오류 관례야 [확정].

**모든 명령 함수가 `int` 를 반환하고 0=성공 / 1=실패로 통일돼 있어. 예외 없어.** 전달은 명령 함수 → `run()` 의 `result` → 다음 루프에서 `CommandResult` → `getResult()` → GUI.

**재시도 루프가 파일 전체에 하나도 없어.** 타임아웃 한 번, 프리앰블 불일치 한 번, `?` 한 번 → 즉시 실패야. 유일한 자가치유는 `interfaceCommand` 첫머리의 **자동 재연결**(`:326~330`)이야 — 소켓이 끊겨 있으면 명령 전에 다시 붙어.

`interfaceFlush()`(`:547~553`)는 `waitForReadyRead(10)` 후 `readAll()` 로 있는 걸 전부 버려. **`run()` 루프 끝에서 매 바퀴** 불리고(`:174`), `getSystem`/`getStatus`/`getFrameStatus`/`writeConfig`/`flash`/`verify`/`flashMod`/`verifyMod` 시작에서도 불려. 이유는 명확해 — **이 프로토콜엔 스트림 재동기화 수단이 없어.** 텍스트는 참조번호로 걸러내지만 이진은 프리앰블 4바이트가 어긋나는 순간 끝이야. "느슨하게 자주 버린다" 가 유일한 방어책이야 [확정].

부분 실패가 남기는 상태 [확정]:

| 상황 | 남는 상태 |
|---|---|
| `writeConfig` 중간 실패 | 설정 메모리가 `CLEARCONFIG` 된 뒤 **반쯤 채워진 채로 남아.** 오류 경로(`:1432~1435`)는 `POLLON` 만 되돌리고 설정은 복구 안 해 |
| `flash` 중간 실패 | PROM 이 반쯤 소거/기록된 상태. `BIASPOLLON` 만 복구 |
| `fetchFrame` 중간 실패 | 호스트 버퍼는 `Locked=false` 로 되돌려(`:1397~1400`). 하지만 **컨트롤러 쪽 `LOCKn` 은 안 풀려** — `LOCK0`(`:1386`)에 도달 못 하니까 |
| 타임아웃 | 상태 없음. `run()` flush 가 정리 |

## 4.6 ⭐ 매뉴얼과 소스가 어긋나는 곳

| # | 항목 | 매뉴얼(2021-02-23) | 소스 / 실기 | 심각도 |
|---|---|---|---|---|
| 1 | `MODn_TYPE` 목록 | "16+: Unknown"(p.46), 6 이 아예 빠짐 | `archon.h:29~48` 이 0~19 전부 보유. 17=ADM 이 우리 science 비디오 모듈 | ⭐⭐⭐ |
| 2 | `RAWSEL` 범위 | 0~15 (p.56, p.70) | stock 콤보 32칸, KMTNet 36칸 | ⭐⭐ |
| 3 | `ADXCDS`/`ADXRAW` | 설정 키 사전에 **없음** | 실기 science ACF 에 `=0` 으로 존재. GUI 가 읽고 씀 | ⭐⭐ |
| 4 | `POLLON`/`POLLOFF`/`BIASPOLL*` | **없음** | `writeConfig`·플래시 계열이 실제로 보냄 | ⭐⭐ |
| 5 | `ATLASMOVE` | **없음** | `atlasMove()` 가 보냄 | ⭐ |
| 6 | `FLASH` 주소 자릿수 | 4자리만 (p.51) | X16 이면 **8자리**(`archon.cpp:874`) | ⭐ |
| 7 | `VERIFY` 인자 | 4+4자리 (p.51) | X16 이면 **8+8자리**(`:973`) | ⭐ |
| 8 | `EXTCLKPRESENT` | STATUS 목록에 **없음** | GUI 가 읽음(`archongui.cpp:2205`) | ⭐ |
| 9 | `POWER_ID` | SYSTEM 목록에 **없음**(부록 A p.96 엔 있음) | GUI 가 읽음. 12자리 16진 | ⭐ |
| 10 | `FRAMEnBASE` vs `BUFnBASE` | p.71 본문 `FRAMEnBASE`, p.50 키 목록 `BUFnBASE` | 실제는 **`BUFnBASE`** | ⭐ |
| 11 | p.47 STATUS 표 정렬 | 키 열과 주석 열이 **한 칸씩 어긋난 채 인쇄됨** | 키 이름만 믿고 주석 정렬은 믿으면 안 돼 | ⭐ |
| 12 | 바이트 순서 | **한 줄도 없음** | 변환 코드가 없으니 **호스트 네이티브 = x86 리틀엔디언 uint16** [유력] | ⭐ |
| 13 | ADM 용 `STATEn/MODi` 형식 | **없음** | `ADM::usesClocks()` 가 false — ADM 은 타이밍 상태를 안 가짐 [유력] | ⭐ |

방향은 한결같아 — **FW 와 GUI 가 매뉴얼보다 앞서 있어.** 구조(슬롯·탭 체계)는 완벽히 들어맞는데, 범위·자릿수·명령 목록 같은 세부는 낡았어.

## 4.7 Rev F 동시 접속 1개 — 운영 제약

매뉴얼 p.15 [확정]:

> "Rev F and older backplanes **can only support a single connection at a time**. … **Rev H backplanes currently support up to four simultaneous connections.**"

우리 실기 대조 [실측]:

| 유닛 | FW | `BACKPLANE_REV` | Rev 문자 | 동시 접속 |
|---|---|---|---|---|
| KMTC-SCI-101 | 1.0.1261 | **7** | **H** | 최대 4 |
| KMTK-SCI-113 | 1.0.1252 | **5** | **F** | **1** |

즉 **113 유닛에서는 ICS 가 소켓을 잡고 있으면 ArchonGUI 가 못 붙어.** "동시에 둘 다" 는 구조적으로 불가능해. 101 은 Rev H 라 4개까지 되지만, 두 클라이언트가 같은 컨트롤러 상태를 동시에 바꾸는 건 별개 문제야. **운영 절차에 명시해둬야 할 값이야.**

프로세서도 달라 — Rev F 이하는 Kintex 7 FPGA 안의 32비트 소프트코어, Rev H 는 64비트 ARM(p.15). 네트워크는 **1 Gbps 전용**이고 10/100 하위호환이 안 돼.

---

# 5. 설정·적용 계통

## 5.1 ACF 형식과 세 가지 키 표기

ACF 는 **Windows INI 형식**이고 절이 딱 둘이야(매뉴얼 p.73) [확정]:

- `[SYSTEM]` — `SYSTEM` 명령 응답을 그대로 저장. 컨트롤러 없이도 GUI 가 구성을 보여주고 오프라인 편집을 할 수 있게 하려는 거야.
- `[CONFIG]` — 컨트롤러로 보낼 설정 key/value 전부.

GUI 는 **파서를 직접 안 짰어.** `QSettings(filename, QSettings::IniFormat)` 에 통째로 맡겼어(`archongui.cpp:1280~1307` 읽기, `:1309~1340` 쓰기). 그래서 세 가지 표기가 갈려 [확정]:

| 문맥 | 표기 | 예 | 왜 |
|---|---|---|---|
| 코드 안 `config` 맵 / 와이어 `WCONFIG` / 매뉴얼 p.57~63 | **슬래시** | `MOD5/CLAMP1` | 코드가 `key + "/CLAMP1"` 로 조립(`modules.cpp:625` 등) |
| ACF `[CONFIG]` 절 | **역슬래시** | `MOD5\CLAMP1=0.0` | QSettings 가 INI 로 쓸 때 키 안의 `/` 를 `\` 로 이스케이프 |
| SYSTEM 응답 / ACF `[SYSTEM]` 절 | **밑줄** | `MOD5_TYPE=17` | 계층 키가 아니라 처음부터 밑줄. 변환 대상이 아님 |
| STATUS 응답 / `status` 맵 | **슬래시** | `MOD5/TEMPA` | 컨트롤러가 그대로 내보냄. 매뉴얼 p.47~48 도 슬래시 |

변환 코드가 소스 어디에도 없어(`replace()` 는 확장자 치환 두 곳뿐) — **역슬래시는 오직 `.acf` 파일 안에서만 존재하는 표기야** [확정]. 증거 하나 더: QSettings 를 안 거치고 손으로 쓰는 `.ncf` 경로에서는 `MOD%1/VCPU_LINE%2` 처럼 **슬래시가 그대로 파일에 나가**(`archongui.cpp:1477`).

값에 쉼표가 들어가는 것(TAPLINE, `STATEn/MODi`)은 **큰따옴표로 감싸**(매뉴얼 부록 A p.96). **키 순서는 상관없어**(노트 p.5).

`.ncf`("nice") 는 diff·리뷰용 변형이야. 절이 `[SYSTEM]` `[CONFIG]` `[TIMINGSCRIPT]` `[PARAMETERS]` `[CONSTANTS]` `[TAPLINES]` `[STATE]`×N `[VCPUn]`×N `[END]` 로 나뉘고, 리스트 키의 **번호를 빼서 본문 그대로** 적어. 정렬도 `QCollator(numericMode)` 로 자연 정렬이라 `LINE2` 가 `LINE10` 앞에 와. 읽고 나면 `parseSystem(); updateUI();` 로 ACF 경로와 똑같이 합류해 — **겉모습만 다른 같은 config 맵이야** [확정].

## 5.2 주요 설정 키 (CDS/Deint 계열)

| 키 | 정의 | 실기 science | 실기 guide | 근거 |
|---|---|---|---|---|
| `FRAMEMODE` | 0=top / 1=bottom / **2=split**(탭 목록 앞 절반은 위, 뒤 절반은 아래) | **2** | 0 | p.56, p.69~70 |
| `BIGBUF` | 0 = 512 MB × 3, 1 = **768 MB × 2**(버퍼 3 미사용) | **1** | 0 | p.55, p.71 |
| `SAMPLEMODE` | 0 = 16bit, 1 = 32bit(HDR) | **0** | 0 | p.56, p.71 |
| `LINECOUNT` | **탭 하나당** 라인 수, 1~65535 | 4700 | 1033 | p.54, p.69 |
| `PIXELCOUNT` | **탭 하나당** 픽셀 수 (상한 미문서) | 1200 | 528 | p.56, p.69 |
| `SHP1`/`SHP2` | 리셋 레벨 적분 구간 | 72 / 112 | — | p.69 |
| `SHD1`/`SHD2` | 비디오 레벨 적분 구간 | 136 / 200 | — | p.69 |
| `TAPLINES` / `TAPLINE<n>` | 탭 정의 줄 수(0~63) / `"tap,gain,offset"`. **`n` 은 0기점** | 32 | 8 | p.56, p.70 |
| `RAWENABLE` | 0/1 | **1** | **1** | p.56 |
| `RAWSEL` | raw 캡처 채널, **0기점** | **3** | **4** | p.56, p.70 |
| `RAWSTARTLINE`/`RAWENDLINE` | raw 캡처 라인 구간 | 300 / 400 | 0 / 200 | p.56 |
| `RAWSTARTPIXEL` | 라인마다 raw 시작 픽셀 | 1144 | 0 | p.56 |
| `RAWSAMPLES` | 라인당 raw 샘플 수. **1024 배수로 올림** | 8192 | 4096 | p.56, p.70 |
| `ADXCDS` / `ADXRAW` | **매뉴얼에 없음.** ADX 모듈 전용 스위치. `ADXRAW=1` 이면 raw 축이 2.5 ns(400 MHz) | 0 / 0 | (키 없음) | GUI 만 |
| `LINESCAN` | 1 이면 라인마다 FRAME 이 올라가는 타이밍 | — | — | p.56, Rev E+ / build ≥1028 |

**"per tap" 이 핵심이야.** `LINECOUNT`/`PIXELCOUNT` 는 전체 이미지 크기가 아니라 **채널 하나가 읽는 영역**이야 [확정].

`ADXCDS`/`ADXRAW` 가 guide ACF 에 **없는** 건 의미가 있어 — GUI 는 숨겨진 위젯의 키를 아예 안 써(`if (!adxraw->isHidden())`, `:2456`, `:2462`). 그 위젯은 **X12 + `BACKPLANE_REV ≥ 4` + build ≥ 930** 일 때만 보여. 즉 science 는 조건을 통과했고, **guide 백플레인은 Rev D 이하이거나 빌드 930 미만**이라는 뜻이야 [유력] — guide 의 `BACKPLANE_REV`/`VERSION` 을 아직 안 받아서 [확인불가].

## 5.3 `writeConfig()` — 모든 적용의 공통 전처리

`archon.cpp:1406~1436` [확정]:

```
interfaceFlush()
POLLOFF                                    ← 폴링 정지
CLEARCONFIG                                ← 설정 메모리 통째로 비움
WCONFIG0000<KEY>=<VALUE>                   ← config 맵 전부, 한 줄씩
WCONFIG0001<KEY>=<VALUE>
   ...
POLLON                                     ← 폴링 재개
```

줄 조립은 이래(`:1421`):

```cpp
s = QString("WCONFIG%1%2=%3").arg(line, 4, 16, QChar('0')).toUpper().arg(i.key()).arg(i.value());
```

`.toUpper()` 가 `%2`/`%3` **치환 전에** 걸려 있어서 **줄 번호 16진만 대문자화되고 키·값의 대소문자는 보존돼.** 이게 맞는 동작이야 — 타이밍 스크립트나 파라미터 이름은 대소문자를 지켜야 하거든 [확정].

⚠️ **`config` 는 `QMap<QString,QString>` 이라 키 사전순으로 순회해**(`archon.h:50`). ACF 에 적힌 순서가 아니라 **알파벳 순서**로 줄 번호가 매겨져. FW 가 키 이름으로 파싱하니 실질 문제는 없어 보이는데, `RCONFIG` 로 되읽으면 줄 순서가 원본과 다르다는 건 알아둬야 해 [확정].

## 5.4 APPLY 계열의 차이

| 함수 | `writeConfig()` 선행 | 보내는 명령 | 타임아웃 | 매뉴얼 설명 |
|---|:---:|---|---:|---|
| `applyAll()` | ✅ | `APPLYALL` | 30 s | p.51 전체 설정 파싱·적용. **끝나면 CCD 전원 OFF** |
| `applySystem()` | ✅ | `APPLYSYSTEM` | 5 s | p.53 백플레인 시스템 설정(주로 트리거 제어) |
| `applyCDS()` | ✅ | `APPLYCDS` | 5 s | p.53 디인터레이싱·CDS 설정 |
| `applyModule(slot)` | ✅ | `APPLYMOD`+`hex(slot-1,2)` | 10 s | p.52 모듈 xx 설정 |
| `applyModuleDIO(slot)` | ✅ | `APPLYDIO`+`hex(slot-1,2)` | 10 s | p.53 모듈 xx 의 **DIO + VCPU** 설정 |
| `applyNet()` | ✅ | `APPLYNET` | 5 s | p.53 현재 설정의 IP·포트로 통신 전환 |
| `loadTiming()` | ✅ | `LOADTIMING` | 5 s | p.51 스크립트+파라미터 컴파일·적용. **코어 리셋** |
| `loadParams()` | ✅ | `LOADPARAMS` | 5 s | p.52 파라미터 전부. 리셋 없음 |
| `loadParam(name)` | ✅ | `LOADPARAM <name>` | 5 s | p.52 하나만 |
| `direct(cmd)` | ❌ | 사용자 문자열 그대로 | 5 s | 미문서(GUI 전용 통로) |
| `atlasMove(params)` | ❌ | `ATLASMOVE`+... | 5 s | **매뉴얼에 없음** |

핵심을 한 줄로 [확정]: **`writeConfig()` 뒤에 붙는 `APPLYxxx` 한 단어가 "설정 메모리의 어느 부분을 하드웨어에 반영할지" 를 고르는 거야. 설정 업로드 자체는 항상 전체야.** 부분 갱신 같은 최적화가 없어. `applyModule` 만 눌러도 수천 줄이 다시 올라가.

모든 Apply 슬롯이 똑같은 4단 관용구를 써:

```cpp
if (!connected) { logMessage("Archon not connected."); return; }
parseUI();                     // 위젯 → config (전 모듈 전수)
archon->getResult();           // 진행 중 명령(폴링) 대기
archon->setConfig(config);
e = archon->getResult();
if (!e) { archon->command("<APPLY…>"); archon->getResult(); }
```

## 5.5 ⭐ 순서 의존성

**A. 함수 내부 (코드가 강제해)**

```
interfaceFlush → POLLOFF → CLEARCONFIG → WCONFIG×N → POLLON → APPLYxxx
```

`POLLOFF` 가 먼저인 건 배경 폴링이 `WCONFIG` 수천 줄 사이에 끼어드는 걸 막으려는 거야. 그런데 `POLLON` 이 `APPLYxxx` **앞에** 있어서(`:1428` → `:1444`), 적용 자체는 폴링이 켜진 채로 일어나 [확정].

**B. 함수 사이 (호출자 책임 — 코드가 강제 안 해)**

1. **`APPLYALL` → `POWERON`** — 매뉴얼 p.51: "An APPLYALL is required before this operation." 그리고 `APPLYALL` 직후엔 전원이 꺼져 있으니 반드시 `POWERON` 을 따로 해야 해. `powerOn()`(`:1468~1479`)은 이걸 확인 안 해 [확정]. 실기에서도 `APPLYALL` 안 하면 `?xx` 거부야 [실측].
2. **`APPLYALL` → `LOADTIMING` → `LOADPARAM(S)`** — `LOADTIMING` 이 코어를 리셋하니까, 파라미터 미세조정은 그 뒤에 해야 리셋 없이 반영돼.
3. **`APPLYNET` 은 맨 마지막** — IP 가 바뀌면 그 순간 연결이 끊겨. 매뉴얼 p.44 절차: Apply Network Configuration → (오류 메시지 뜨는 게 정상) → Disconnect → 새 주소로 Connect → `FLASHACTIVECONFIG` 로 영구화.
4. **`FLASHACTIVECONFIG` 는 원하는 설정이 적용된 뒤에.**
5. **`RESETTIMING`/`HOLDTIMING`/`RELEASETIMING`/`POWERON`/`POWEROFF`/`POLLON`/`POLLOFF` 는 `writeConfig()` 를 안 불러.** 이미 적용된 상태 위에서만 동작해. **설정을 바꾸고 이것들만 누르면 아무 효과 없어** [확정].
6. **`HOLDTIMING` → (각 시스템에 적용) → `RELEASETIMING`** 쌍이 다중 컨트롤러 동기 절차야(p.19). 데이지체인이면 시스템 간 약 10 ns + 케이블 지연이 남아.

## 5.6 결함 — 적용 계통에서 찾은 것

| # | 내용 | 위치 | 등급 |
|---|---|---|---|
| C1 | **`CONFIG` 가 `result` 를 갱신 안 해** → `setConfig` 뒤 `getResult()` 가 **직전 통신 명령의 결과**를 반환. GUI 가 이걸로 `APPLYxxx` 실행 여부를 결정해서, 직전에 아무 명령이나 실패했으면 `APPLYALL` 이 조용히 건너뛰어져. 같은 패턴이 7개 Apply 슬롯 전부에 있어 | `archon.cpp:77~81` + `archongui.cpp:1622~1627` 등 | 중 |
| C2 | `writeConfig` 중간 실패 시 설정 메모리가 **반쯤 지워진 채** 남고 복구 안 됨. 이 상태에서 `APPLYALL` 하면 반쪽 설정이 적용돼 | `archon.cpp:1415~1427` | 중 |
| C3 | **`parseUI()` 첫 줄이 `config.clear()`** 라 저장 시 config 는 위젯에서 재구성돼. ① 숨은 위젯 키(`EXTCLOCK`/`TRIGOUTPOWER`/`PCLKDELAY`/`ADXRAW`/`ADXCDS`/`LINESCAN`)가 빠지고 ② **이 GUI 가 모르는 키는 전부 유실돼.** ACF 왕복이 무손실이 아니야 | `archongui.cpp:2422`, `:2428~2467` | 중 |
| C4 | `openNiceFile()` 이 파싱 중단 시 `goto done` 으로 빠져서 **조용히 반쪽만 로드** | `archongui.cpp:1364`, `:1485` | 하 |
| C5 | `updateUI()` 의 상태 복원이 상태마다 `config.keys()` 를 전수 순회 — O(상태수 × 전체키수) | `archongui.cpp:2607~2617` | 하(성능) |
| C6 | `WCONFIG` 는 키 하나당 왕복 한 번이라 수천 키면 그만큼 왕복이 생겨. Apply All 이 오래 걸리는 이유가 여기 | `archon.cpp:1415~1427` | 정보 |

> C3 은 우리한테 특히 중요해. **같은 ACF 를 다른 하드웨어(또는 미연결 상태)에서 열었다 저장하면 키 집합이 달라져.** ACF 를 GUI 로 왕복시키는 습관은 위험해.

---

## 5.7 보유 ACF 전수 (2026-09-03 반입분 포함)

`__reference/acf/` 에 실기 ACF **12개 + 타이밍 스크립트 1개**가 들어왔어. 전수로 훑은 결과야 [확정].

| 구분 | 파일 | 탭 | 접두 | 비디오 슬롯 | 탭 번호 | `RAWSEL` | 기하 |
|---|---|---:|---|---|---|---:|---|
| science | `KMTC_SCI_101` MK · `KMTC_SCI_102` NT · `KMTK_SCI_113` MK/NT · `KMTS_SCI_101` MK | 32 | `AM` | 5, 8 | **1–16, 55–70** | **3** | 1200×4700 |
| guide | `KMTK_GUI_162` · `kmtnet_guide_*` 6종 | 8 | `AD` | 5, 6 | **1–8** | **4** | 528×1033 |

⭐ **12개 전부가 `RAWSEL ≤ 4` 야** — §2.2(e) 에서 "실사용 흔적 없음" 의 근거가 **2개에서 12개로 늘었어.** 둘째 블록(라벨 55~72)을 쓴 ACF 는 **하나도 없어** [확정]. 그리고 science 넷이 탭 구성까지 완전히 같아서, §2.2(a) 의 ADM 18채널 사상이 유닛 넷에서 재확인돼.

### 5.7.1 ⭐ `for1110` ↔ `for1259` — GUI 판별 ACF 가 실재해

guide ACF 가 **같은 설정의 두 판**으로 들어왔어: `..._for1110_*` 과 `..._for1259_*`. 뒤 숫자는 GUI/FW 빌드 번호야(1259 = 우리가 분석한 그 GUI). 두 쌍을 키 단위로 대조했어 [확정].

| 항목 | 결과 |
|---|---|
| 키 수 | 1110 = **1061** → 1259 = **1064** |
| 1110 에만 있는 키 | ⭐ **0개** |
| 1259 에만 있는 키 | **3개** — `GATEWAY` · `NETMASK` · `TRIGINEDGE` |
| 값이 바뀐 키 | 3~4개 (아래) |

```
MOD10\SENSORALOWERLIMIT   -150.0 → -150      (서식 정규화)
MOD10\SENSORBLOWERLIMIT    -30.0 → -30       (서식 정규화)
MOD10\SENSORBUPPERLIMIT     70.0 → 60        ⚠️ 값이 진짜로 바뀜
MOD7\SENSORALOWERLIMIT      -220 → -230      ⚠️ 값이 진짜로 바뀜
```

⚠️ **처음엔 이걸 §11.3 C3(모르는 키 유실)의 실물 증거로 읽었는데 틀렸어.** 줄 단위 `diff` 가 `MOD7\...` 블록을 통째로 삭제로 보여줬지만, 그건 **두 파일의 키 정렬 순서가 달라서** 생긴 착시였어 — 키 집합으로 대조하니 `MOD7` 키는 **양쪽 다 88개**로 같아. **잃은 키는 0개야.**

그래서 이 자료가 실제로 말해주는 건 이거야:

1. **판올림 방향(1110 → 1259)은 안전해.** 새 GUI 가 아는 키가 **상위집합**이라 잃는 게 없고, 오히려 신설 기능 셋(`GATEWAY`·`NETMASK`·`TRIGINEDGE`)이 붙어. `APPLYNET` 계통과 외부 트리거 극성이 그 판에 생겼다는 뜻이야 [유력].
2. ⚠️ **위험한 건 반대 방향이야.** 1259 판 ACF 를 **옛 GUI(1110)로 열어 저장하면** 저 세 키가 사라져 — C3 가 경고하는 그 경로야. 등급은 [유력](이 자료로 직접 관측한 건 아니야).
3. **GUI 는 저장할 때 실수 서식을 정규화해**(`-150.0` → `-150`). 그래서 **ACF 를 바이트로 비교하면 안 되고 키·값 단위로 비교해야 해** [확정]. 우리 대조 도구에 그대로 걸리는 이야기야.
4. `SENSORBUPPERLIMIT 70→60`, `MOD7\SENSORALOWERLIMIT -220→-230` 은 서식이 아니라 **운영자가 실제로 고친 값**으로 보여 [추정] — 판별 차이로 오해하면 안 돼.

### 5.7.2 `goff` 판 — 딱 한 키

`kmtnet_guide_STA0291_103_R2601_for1259.acf` 와 `..._goff_...` 의 차이는 **정확히 한 줄**이야 [확정]:

```
MOD10\DIO_POWER=1   →   0
```

`goff` = **게이지 off**. HeaterX(MOD10)의 DIO 전원을 내려 진공 게이지를 끄고 기동하는 판이야. `icg_archon` 이 게이지 전원 대기를 건너뛰는 경로를 가질 수 있다는 기존 관측과 정합해.

### 5.7.3 `acf_timing_script.txt` — 타이밍 상태기계 원본

guide 타이밍 스크립트 전문이야. `Start` → `Exposure`/`Continuous` 분기와 `IntUnit(IntMS)` · `NoIntUnit(NoIntMS)` · `HorizontalSWShift(1200)` · `CLAMP`/`NOCLAMP` · `SkipLine`/`Line` 호출 구조가 보여. 다른 세션이 프레임 사이 사강 0.50초를 `NoIntMS=500` 으로 동정한 근거가 이 파일의 `NoIntUnit(NoIntMS)` 줄이야.

---

# 6. 프레임 취득 사슬

## 6.1 왜 잠금이 필요한가

매뉴얼 p.15·p.71 이 근거를 줘 [확정]. 백플레인 DDR3 2 GB 중 512 MB 는 프로세서용이고 **위쪽 1.5 GB 가 프레임 버퍼**야.

| `BIGBUF` | 버퍼 | 크기 | 베이스 주소 |
|---|---|---|---|
| 0 | 3개 | 512 MB | `0xA0000000` / `0xC0000000` / `0xE0000000` |
| **1** (우리 science) | **2개** | **768 MB** | `0xA0000000` / `0xD0000000` (버퍼 3 미사용) |

디인터레이싱 엔진이 새 프레임을 시작하면(`PIXEL` 상승 때 `FRAME` 이 high) **잠기지 않은 다음 버퍼를 스스로 잡아서** 쓰기 시작하고, 다 차면 `BUFnCOMPLETE` 를 세워. 그러니까 호스트가 읽는 중인 버퍼를 잠가두지 않으면 **엔진이 바로 그 버퍼를 골라 덮어써.** 보통 읽기용 1개 + 쓰기용 1개가 동시에 잠겨 있는 게 정상 상태야.

실측으로도 확인됐어 [실측]: **`LOCK` 없이 fetch 하면 약 26% 확률로 엔진이 쓰는 중인 버퍼를 집어가서 두 노출이 섞여.** → `lock_buffer=true` 로 종결.

## 6.2 사슬 — `FRAME` → `LOCK` → `FETCH` → `LOCK0`

```
[GUI 500 ms 틱] poll() ──"FRAME"──▶ Archon::getFrameStatus()
        ↓ msgFrameStatus(RMap)
   parseFrameStatus()  (archongui.cpp:2362~2413)
        · BUFn* 를 3행 표에 뿌림
        · COMPLETE(=C) 인 버퍼 중 Frame 번호 최대인 것 선택
        · cbAutoFetch 켜져 있고 fetchedframe 과 다르면 ↓
   fetchFrame(int frame)  (archongui.cpp:1831)   ← 딱 두 줄
        archon->command("LOCK", QString::number(frame + 1));   // 0기점 → 1기점
        archon->command("FETCH");
        ↓
   Archon::fetchFrame()  (archon.cpp:1247~1404)
        1. getFrameStatus(quiet=true) 로 기하 파악
        2. 호스트 버퍼 확보 (frameMutex)
        3. FETCH<baseaddr><lines>            ← 이미지
        4. FETCH<baseaddr+rawoffset><lines>  ← raw (2차)
        5. LOCK0  →  emit newFrame()
        ↓
   TArchonGUI::newFrame()  (archongui.cpp:3138~3187)
```

`fetchFrame(int)` 의 인자는 **0기점 버퍼 인덱스**인데 명령은 1기점이라 `+1` 이 붙어(`archongui.cpp:1831`) [확정]. System 탭의 Fetch 버튼 3개도 `QSignalMapper` 로 같은 슬롯에 물려 있어.

## 6.3 `fetchFrame()` 5단계

**1단계 — 컨트롤러 쪽 기하 파악** (`archon.cpp:1263~1290`) [확정]

```cpp
rbuf       = frameStatus["RBUF"];              // 현재 읽기 잠금된 버퍼
framenum   = frameStatus["BUF{rbuf}FRAME"];
baseaddr   = frameStatus["BUF{rbuf}BASE"];
framew     = frameStatus["BUF{rbuf}WIDTH"];
frameh     = frameStatus["BUF{rbuf}HEIGHT"];
samplemode = frameStatus["BUF{rbuf}SAMPLE"];

if (samplemode) frame_size = 4 * framew * frameh;   // :1282
else            frame_size = 2 * framew * frameh;   // :1284
lines  = ceil(frame_size / 1024);
chunks = ceil(frame_size / 1 MiB);
rawsize   = rawblocks * rawlines * RAW_BLOCK_SIZE;  // :1289
rawoffset = frameStatus["BUF{rbuf}RAWOFFSET"];
```

`framenum==0` 이거나 폭·높이가 0 이하면 그냥 `return 0` — 빈 프레임은 조용히 무시(`:1293~1294`).

**2단계 — 호스트 버퍼 확보** (`:1296~1335`, `frameMutex` 보호)

`frames` 벡터에서 **`Locked` 가 아니면서 `Frame` 번호가 가장 작은(가장 오래된)** 것을 골라. 크기가 안 맞으면 `setSize()`/`setRawSize()` 로 재할당하고, 할당 실패한 버퍼는 후보에서 빼. 못 찾으면 `"Dropped frame, no buffer available to fill"`(`:1331`).

**3단계 — 이미지 페치** (`:1337~1359`)

```cpp
s = "FETCH" + hex(baseaddr, 8) + hex(lines, 8);    // 1339
for (chunk = 0; chunk < chunks; chunk++) {
    interfaceBinaryCommand(s, p, qMin(bytes_remaining, chunk_size), ARCHON_TIMEOUT, false);
    s.clear();                                      // 1356 ← 두 번째부터 빈 명령
    ...
}
```

**`FETCH` 명령은 딱 한 번만 나가고**, 컨트롤러가 `lines` 개 블록을 쭉 흘려보내면 호스트가 **1 MiB(`chunk_size = 1024 * BURST_LEN`)** 씩 잘라 받는 구조야 [확정].

**4단계 — ⭐ raw 페치** (`:1360~1384`) — **완전히 별개의 2차 fetch 야.**

```cpp
bytes_remaining = rawsize;                          // 1361
lines  = (rawsize + line_size - 1) / line_size;     // 1362
chunks = (rawsize + chunk_size - 1) / chunk_size;   // 1363
s = "FETCH" + hex(baseaddr + rawoffset, 8) + hex(lines, 8);   // 1364
```

진행률 문구도 따로야 — 이미지는 `"Fetching frame..."`(`:1353`), raw 는 `"Fetching raw frame..."`(`:1378`). 프레임 버퍼도 이미지용(`setSize`)과 raw 용(`setRawSize`)이 별도 배열이야(`frames.h:14~15`).

**5단계 — 반납과 통보** (`:1385~1393`): `LOCK0` → `frameMutex` 잡고 `Locked=false` → `emit newFrame()`.

## 6.4 ⭐ raw 는 이미지 크기에 안 섞여 — `data_bytes` 정합

이게 우리한테 제일 중요한 확인이야 [확정].

| | ArchonGUI | 우리 `ics_archon/archon/parse.py:113` |
|---|---|---|
| 이미지 바이트 | `(samplemode ? 4 : 2) * framew * frameh` | `data_bytes = (4 if samplemode else 2) * width * height` |
| raw | **별도 2차 `FETCH`**, 주소 `baseaddr + BUFnRAWOFFSET`, 크기 `BUFnRAWBLOCKS * BUFnRAWLINES * 2048` | (안 읽음) |

**완전히 같아.** 그러니까 실기 ACF 가 `RAWENABLE=1` 인데도 우리가 raw 를 안 읽는 건 **정상이야. 결함이 아니야.** raw 를 읽고 싶으면 이미지 fetch 를 끝낸 뒤 두 번째 `FETCH` 를 별도로 내면 돼.

## 6.5 버퍼 관리 — 호스트 쪽

호스트 버퍼는 **딱 2개**야 — `archon->frames.resize(2)` (`archongui.cpp:1230`) [확정]. 컨트롤러 쪽 3개(또는 BIGBUF 2개)와 별개야.

이중 잠금 구조:

| 층 | 무엇을 지키나 |
|---|---|
| `frameMutex` (public) | `frames` 벡터의 메타데이터(`Locked`, `Frame`) 갱신을 원자적으로 |
| `TFrameBuffer::Locked` (bool) | 그 버퍼의 픽셀 데이터를 지금 누가 쓰고 있는지 — 뮤텍스가 아니라 소유권 표식 |

**Archon 스레드는 가장 오래된 것을 잡고, GUI 는 가장 최신 것을 잡아.** 서로 반대쪽 끝을 무는 구조야 [확정]:

```cpp
// archon.cpp:1298~1326  — 생산자: Locked 아닌 것 중 Frame 최소
// archongui.cpp:3138~3187 — 소비자: Locked 아닌 것 중 Frame 최대
archon->frameMutex.lock();
archon->frames[displayindex].Locked = false;   // 이전 표시 버퍼 반납
updateDiffStats(displayindex, newindex);
archon->frames[newindex].Locked = true;        // 새 표시 버퍼 점유
archon->frameMutex.unlock();
```

⚠️ **여유가 없는 설정이야.** GUI 가 표시용으로 1개를 물고 있으면 남는 건 1개뿐이야. 그리고 `updateDiffStats()` 가 `frameMutex` 를 쥔 채 이미지 연산을 해(`:3164`) — 그동안 Archon 스레드의 `fetchFrame` 이 버퍼 확보 단계에서 대기해. 정합성은 맞지만 **페치가 GUI 연산에 물리는 구조**야 [확정].

## 6.6 `TFrameBuffer` — 필드와 재사용 규칙

| 필드 | 형 | 실제 동작 |
|---|---|---|
| `NewFlag` | bool | **죽은 필드.** 선언 한 줄뿐이고 읽지도 쓰지도 않아. 생성자에서 초기화조차 안 해 |
| `Frame` | int | `BUFnFRAME` 값. **비어있음 표시로 -1**. "가장 오래된 버퍼 고르기" 의 정렬 키 |
| `Data` | `unsigned short*` | 디인터레이스 끝난 **이미지** 픽셀. HDR 일 땐 소비자가 `quint32*` 로 캐스팅 |
| `RawData` | `unsigned short*` | raw 샘플. **항상 16bit** — HDR 개념이 아예 없어 |
| `Locked` | bool | 소유권 표식 |
| `m_width`/`m_height` | int | **바이트가 아니라 표본 수** |
| `m_rawwidth`/`m_rawheight` | int | raw 치수. `rawwidth = rawblocks * 2048/2 = rawblocks × 1024 샘플` |
| `m_hdr` | bool | "표본이 16bit 대신 32bit" 플래그 |

재사용 판정이 재밌어 [확정] (`frames.cpp:157`, `:172`):

```cpp
if ((m_width == width) && (m_height == height) && (m_hdr == hdr) && Data) return 0;  // 그대로 씀
...
else if ((m_width * m_height != width * height) || (m_hdr != hdr))                   // 이때만 free+malloc
```

즉 **가로세로가 바뀌어도 `w*h` 곱이 같고 표본 폭이 같으면 재할당을 안 해.** science 한 장이 수백 MB 급이라 프레임마다 malloc/free 를 반복하지 않으려는 거야.

## 6.7 픽셀 해석 — 16bit / 32bit(HDR)

분기의 유일한 원천은 **`SAMPLEMODE`** 야. 사슬 전체 [확정]:

```
[GUI 콤보]  samplemode ("NORMAL"=0 / "HDR"=1)   archongui.cpp:692~694
   ↓ Apply
[ACF/CONFIG]  SAMPLEMODE = currentIndex()        archongui.cpp:2453
   ↓ WCONFIG → FW
[FRAME 응답]  BUFnSAMPLE                          archon.cpp:1280
   ↓
[호스트]  frame_size = 4 or 2 × w × h             archon.cpp:1281~1284
          setSize(framew, frameh, samplemode)     archon.cpp:1308
   ↓
[버퍼]  malloc(w*h*sizeof(ushort)*(hdr?2:1))      frames.cpp:176
   ↓ isHDR()
[표시]  16bit → Data[] 그대로 + grayscale[65536]
        32bit → (quint32*)Data, 값 >>12 후 grayscalehdr[1048576]   ← 상위 20bit 만 씀
```

**실기(`SAMPLEMODE=0`)에서는 32bit 경로를 한 번도 안 타.** KMTNet 운영에서 HDR 코드는 죽은 경로야 [확정].

raw 는 `SAMPLEMODE` 와 무관하게 **항상 16bit** 야.

## 6.8 이진 전송 상수와 타임아웃

| 상수 | 값 | 의미 |
|---|---|---|
| `BURST_LEN` (`archon.h:17`) | **1024** | 프로토콜이 못박은 이진 블록 크기(매뉴얼 p.45). `FLASH` 한 번의 바이트 수이자 `FETCH`/`VERIFY` 의 카운트 단위 |
| `RAW_BLOCK_SIZE` (`archon.h:20`) | **2048** | raw 블록 크기. `BURST_LEN` 과 **무관한 별개 단위** |
| `chunk_size` (`archon.cpp:1254`) | `1024 * BURST_LEN` = **1 MiB** | `interfaceBinaryCommand` 한 번에 받는 양 |

`RAW_BLOCK_SIZE=2048` 이 매뉴얼 p.70 의 "rounded up to the next even block size (a multiple of 1024)" 와 맞물려 — 샘플이 16비트니까 **1024 샘플 = 2048 바이트 = raw 블록 1개**야. science `RAWSAMPLES=8192` = 정확히 8블록, `RAWSTARTLINE=300`/`RAWENDLINE=400` → 101 라인 → raw 크기 8×101×2048 ≈ **1.65 MB** [확정].

이진 오버로드 두 개의 결정적 차이 [확정]:

| | (a) `QByteArray&` (`:385~455`) | (b) `char*, int length` (`:457~545`) |
|---|---|---|
| 받는 양 | **정확히 1블록** | `length` 만큼 **여러 블록 연속** |
| 타임아웃 | 재시작 없음 — 2초 안에 1024 B 못 받으면 실패 | **무음 구간 기준** — 바이트 올 때마다 `t.start()`(`:521`) |
| 꼬리 | — | `qMin(BURST_LEN, length)` 로 딱 필요한 만큼만 복사. 남는 바이트는 `interfaceFlush()` 가 치워 |
| 쓰임 | `verify()`, `verifyMod()` | **`fetchFrame()` 뿐** |

(b)의 무음 기준 타임아웃이 **수백 MB 페치가 5초 제한에 안 걸리는 이유**야.

## 6.9 실측 수치

[실측] (2026-09-01~02 KASI 벤치, `ics_archon/archon_lock_fetch_report.md`):

| 항목 | 값 |
|---|---|
| 독출 속도 | **368.0 행/초** (FETCH 중에도 이 만속을 유지해) |
| 4700행 독출 | 12.77 초 |
| 프레임 주기 | 13.27 초 |
| FETCH 344.2 MiB | 3.2~3.5 초 (약 100 MiB/s) |
| `LOCKn` 반영률 | 15/15. fetch 를 느리게 하지도 엔진을 멈추지도 않아 |
| `BUFnFRAME` 리셋 | **`REBOOT` 만.** `WARMBOOT`·CCD `POWEROFF/ON` 은 프레임 번호가 이어져 |

⭐ **GUI 의 "독출 정지" 는 표시 착시였어.** 재관측에서 라인 표시가 10 → 1500 으로 점프했는데, 1490행 ÷ 368 = 4.05초 = FETCH 시간이야. 기전은 §7.5 의 "폴링 버려짐" 이야.

## 6.10 프레임 사슬의 결함

| # | 내용 | 위치 | 등급 |
|---|---|---|---|
| F1 | `lockNewestFrame()` 이 **`BUFnCOMPLETE` 를 안 봐** — 채워지는 중인 버퍼를 잠글 수 있어. GUI 자동 경로는 `parseFrameStatus()` 가 `framecomplete[i]` 를 확인하고 `LOCK`+번호를 직접 지정해서 이 함수를 안 써 | `archon.cpp:658~681` | 하(잠복) |
| F2 | 호스트 프레임 버퍼가 **2개뿐** — GUI 표시 중 새 프레임이 오면 여유가 없어 | `archongui.cpp:1230` | 하 |
| F3 | `openHDRFrame()` 이 read 실패 경로에서 **`frameMutex.unlock()` 을 안 해** → **교착.** 이후 프레임 수신이 통째로 멈춰. `openFrame` 쪽은 제대로 풀어 | `archongui.cpp:3806~3812` | **높음(실버그)** |
| F4 | `TFrameBuffer` 복사 생성자가 `other.Data==0` 분기에서 **`RawData`·`m_rawwidth`·`m_rawheight`·`m_hdr` 를 미초기화** → 나중에 쓰레기 포인터를 `free()` 해. 지금은 값 복사가 안 일어나서 안 터져 | `frames.cpp:23~26` | 하(잠복) |
| F5 | 픽셀 복사가 `memcpy` 가 아니라 **원소 단위 for 루프** | `frames.cpp:38~39` 등 | 하(성능) |
| F6 | 자동 페치가 **폴링 콜백 안에서** `getResult()` 로 GUI 를 블로킹 | `archongui.cpp:2411` → `:1838` | 하 |

---

# 7. 모듈 체계

## 7.1 ⭐ 형 번호표 (정본)

**정본은 `archon.h:29~48` 이야.** 매뉴얼 p.46 은 15까지만 유효하고, 6 이 빠졌고, 16~18 이 틀렸어 [확정].

| 형 | `archon.h` 매크로 | 인스턴스화되는 클래스 | 매뉴얼 p.46 | 판정 |
|---:|---|---|---|---|
| 0 | `MOD_TYPE_NONE` | **없음** (빈 슬롯, `continue`) | None | 일치 |
| 1 | `MOD_TYPE_DRIVER` | `DRIVER` | Driver | 일치 |
| 2 | `MOD_TYPE_AD` | `AD` | AD | 일치 |
| 3 | `MOD_TYPE_LVBIAS` | `LVBIAS` | LVBias | 일치 |
| 4 | `MOD_TYPE_HVBIAS` | `HVBIAS` | HVBias | 일치 |
| 5 | `MOD_TYPE_HEATER` | `HEATER` | Heater | 일치 |
| **6** | **`MOD_TYPE_ATLAS`** | `ATLAS` | **(없음 — 5 다음이 7)** | ⚠️ **매뉴얼 누락** |
| 7 | `MOD_TYPE_HS` | `HS` | HS | 일치 |
| 8 | `MOD_TYPE_HVXBIAS` | `HVBIAS` (**공유**) | HVXBias | 일치 |
| 9 | `MOD_TYPE_LVXBIAS` | `LVBIAS` (**공유**) | LVXBias | 일치 |
| 10 | `MOD_TYPE_LVDS` | `LVDS` | LVDS | 일치 |
| 11 | `MOD_TYPE_HEATERX` | `HEATERX` | HeaterX | 일치 |
| 12 | `MOD_TYPE_XVBIAS` | `XVBIAS` | XVBias | 일치 |
| 13 | `MOD_TYPE_ADF` | `ADF` | ADF | 일치 |
| 14 | `MOD_TYPE_ADX` | `ADX` | ADX | 일치 |
| 15 | `MOD_TYPE_ADLN` | `ADLN` | ADLN | 일치 |
| **16** | **`MOD_TYPE_DRIVERX`** | `DRIVERX` | **"16+: Unknown"** | ⚠️ 충돌 |
| **17** | **`MOD_TYPE_ADM`** | `ADM` | **"16+: Unknown"** | ⚠️ **치명적 충돌** — 우리 science 비디오 모듈 |
| **18** | **`MOD_TYPE_HVYBIAS`** | `HVBIAS` (**공유**) | **"16+: Unknown"** | ⚠️ 충돌 |
| 19 | `MOD_TYPE_UNKNOWN` | **없음** (센티널, `continue`) | — | GUI 전용 |

**구현이 없는 형은 없어.** 실 모듈 형 1~18 전부 대응 클래스가 있고, 3형이 클래스를 공유해(8·18 → `HVBIAS`, 9 → `LVBIAS`). 형 18종 → 클래스 15개. 디스패치는 `archongui.cpp:2127~2149` 의 `switch(id)` 딱 한 곳이야 [확정].

공유 클래스는 **탭 라벨만** 형 번호로 갈라 붙여 — 설정 키도 STATUS 필드도 전부 `HVLC_*`/`HVHC_*`, `LVLC_*`/`LVHC_*` 로 똑같아. 실기 science 의 MOD9=8(HVXBias) 도 GUI 상으로는 그냥 HVBIAS 취급이야 [확정].

## 7.2 클래스 계층과 채널 수

계층은 완전히 평평해 — `TModule`(순수 가상 7개) → 파생 15개, 2단계 끝. 중간 계층도 헬퍼 기반 클래스도 없어서 DIO 8채널 블록이나 VCPU 16레지스터 블록이 **클래스 5개에 통째로 복붙**돼 있어 [확정].

| 클래스 | 형 | 채널 구성 | 설정 키 접두 | DIO | VCPU | STATUS |
|---|---|---|---|:---:|:---:|---|
| `DRIVER` | 1 | **8채널** (±13 V, slew 0.001~1000 V/µs) | `LABEL/FASTSLEWRATE/SLOWSLEWRATE/ENABLE/SOURCE<1-8>` | — | — | **없음** |
| `DRIVERX` | 16 | **12채널** | 동일 5종 `<1-12>` | — | — | **없음** |
| `AD` | 2 | 4클램프 + **Preamp Gain** | rev≤C: `CLAMPLOW/HIGH`, rev≥D: `CLAMP1..4`, `PREAMPGAIN` | — | — | **없음** |
| `ADF` | 13 | 4클램프 + Cal | `CLAMP1..4` | — | — | **없음** |
| `ADX` | 14 | 4클램프 | `CLAMP1..4` | — | — | **없음** |
| `ADLN` | 15 | 4클램프 + Cal | `CLAMP1..4` | — | — | **없음** |
| **`ADM`** | **17** | **아무것도 없음. 빈 탭 하나** | **없음** | — | — | **없음** |
| `LVBIAS` | 3, 9 | `LVLC` **24** + `LVHC` **6** = 30 | `LVLC_LABEL/V/ORDER<1-24>`, `LVHC_LABEL/V/IL/ORDER/ENABLE<1-6>` | 8 | ✅ | V/I + DINPUTS + OUTREG |
| `HVBIAS` | 4, 8, 18 | `HVLC` **24** + `HVHC` **6** = 30 | `HVLC_*<1-24>`, `HVHC_*<1-6>` | — | — | V/I 만 |
| `XVBIAS` | 12 | `XVP` 4 + `XVN` 4 | `XVP_*<1-4>`, `XVN_*<1-4>` | — | — | V/I |
| `HEATER` | 5 | 히터 2 + 센서 **2**(A,B) | `HEATER{A,B}*`, `SENSOR{A,B}*` | 8 | ✅ | TEMPA/B + PID항 |
| `HEATERX` | 11 | 히터 2 + 센서 **3**(A,B,C) | `HEATER{A,B}LABEL` 등 + `SENSOR{A,B,C}{LABEL,TYPE,CURRENT,UPPERLIMIT,LOWERLIMIT,FILTER}` | 8 | ✅ | + **TEMPC** |
| `HS` | 7 | LVDS 클럭 **12** + MAG/OFS 쌍 | `HS_LABEL/MAG_LABEL/MAG_V/OFS_LABEL/OFS_V<1-12>` | 4 | ✅ | MAG/OFS V·I |
| `LVDS` | 10 | LVDS 클럭 **16** | `LVDS_LABEL<1-16>` | 4 | ✅ | DINPUTS + OUTREG 만 |
| `ATLAS` | 6 | TEC, 이온펌프, RTD 8, Hall 3, LED 3, 진공, 모터 3축 | `TECENABLE/IONENABLE/LED<1-3>` | — | — | **유일하게 물리량 환산** |

VCPU 를 가진 클래스 = DIO 를 가진 클래스 = `applyModuleDIO` 를 부르는 클래스로 **완전히 겹쳐** — `LVBIAS`·`HEATER`·`HS`·`LVDS`·`HEATERX` 다섯이야 [확정].

바이어스 네 접두의 뜻 [확정]:

| 접두 | 풀이 | 채널 | 라벨 | 전압 범위 | 채널당 전류 |
|---|---|---:|---|---|---|
| `LVLC_*` | **L**ow **V**oltage / **L**ow **C**urrent | 24 | LV1–LV24 | −14.000 … +14.000 V | 10 mA |
| `LVHC_*` | Low Voltage / **H**igh **C**urrent | 6 | LV25–LV30 | −14.000 … +14.000 V | **500 mA** |
| `HVLC_*` | **H**igh **V**oltage / Low Current | 24 | HV1–HV24 | 0.000 … +31.000 V | 10 mA |
| `HVHC_*` | High Voltage / High Current | 6 | HV25–HV30 | 0.000 … +31.000 V | **250 mA** |

모듈 한 장당 **30채널**이고, **모듈 전체 합계 전류는 1 A 를 못 넘어** (매뉴얼 p.11, p.29, p.31).

## 7.3 ⭐ `ADM` 은 사실상 빈 껍데기

KMTNet science 에 직결되는 중요한 사실이야 [확정]. `ADM` 클래스(`modules.cpp:1228~1276`)는 전부가 이래:

- `createUI()`: `systemTabs()` 에 **빈 `QWidget` 탭 하나** 붙이고 `"Slot n: ADM"` 이름표만 달고 끝
- `parseUI()` / `updateUI()`: **본문 없음** → 설정 키를 하나도 안 만들고 안 읽어
- `setClocks()`/`getClocks()`/`clockChanged()`/`copyClocks()`/`pasteClocks()`: 전부 no-op
- `parseStatus()`: 빈 함수
- `waveformTabs`/`vcpuTabs` 에 **아무것도 안 붙임**
- `usesClocks()` 만 **`false`** 를 돌려줘 — 15개 중 유일해
- 유일한 멤버 `rev` 는 생성자에서 채워지고 **어디서도 안 쓰여** (죽은 코드)

그래서 science 실기의 MOD5·MOD8 ADM 은 GUI 상 **탭 이름 말고는 아무 조작 지점이 없어.** 클램프도, 프리앰프 게인도, 클록도, 상태 표시도 없어. 실기 science ACF 에 `MOD5\…`/`MOD8\…` 키가 **0개**이고 `STATE0\MOD5`/`STATE0\MOD8` 도 아예 없는 게 정상인 이유가 이거야 [확정].

ADM 채널 설정은 전적으로 `[TAPLINES]` 와 CDS/Deint 탭(SHP/SHD, RAWSEL, PIXELCOUNT/LINECOUNT, FRAMEMODE, SAMPLEMODE) 쪽에서만 이뤄지고, 나머지는 펌웨어 몫이야.

> ⚠️ 그래서 **ADM 의 clamp/gain 을 설정할 수단이 있는지 자체가 [확인불가]** 야. GUI 에 UI 도 설정 키도 없고 ACF 에도 없어. 정말 무설정인지, 다른 경로가 있는지 확인 못 했어.

## 7.4 설정 키 인덱스 규약

| 대상 | 기점 | 예 |
|---|---|---|
| 슬롯 `<n>` (설정·STATUS·SYSTEM) | **1기점** | `MOD5/CLAMP1`, `MOD5_TYPE`, `MOD5/TEMPA` |
| 채널 `<m>` (대부분) | **1기점** | `LABEL1..8`, `LVLC_V1..24`, `LVDS_LABEL1..16` |
| 리스트 줄 번호 | **0기점** | `LINE<n>`, `PARAMETER<n>`, `CONSTANT<n>`, **`TAPLINE<n>`**, `STATE<n>`, `VCPU_LINE<j>` |
| VCPU 레지스터 | **0기점** | `VCPU_INREG0..15`, `VCPU_OUTREG0..15`. GUI 라벨도 `REG0`..`REG15` |
| **명령의 슬롯 인자** | **0기점 2자리 16진** | 슬롯 5 → `APPLYMOD04`, `APPLYDIO04` |

DIO 방향 키만 형태가 두 갈래야 [확정]:
- 8채널짜리(LVBIAS/HEATER/HEATERX): **`DIO_DIR12`, `DIO_DIR34`, `DIO_DIR56`, `DIO_DIR78`** (두 채널 묶음)
- 4채널짜리(HS/LVDS): **`DIO_DIR1`..`DIO_DIR4`**

콤보박스 값은 전부 `currentIndex()` 라서 **문자열이 아니라 정수**로 저장돼 — `DIO_SOURCE` 0=Low/1=High/2=Clocked/**3=VCPU**, `DIO_DIR` 0=Input/1=Output, `DIO_POWER` 0/1, AD `PREAMPGAIN` 0=LOW/1=HIGH.

## 7.5 펌웨어 빌드 게이팅 — ACF 호환성의 핵심

모듈 생성자가 `MOD<slot>_VERSION` 의 세 번째 필드를 `build`, `BACKPLANE_VERSION` 세 번째를 `backplane_build` 로 담아두고, **위젯과 키를 통째로 켜고 꺼** [확정]:

| 조건 | 효과 |
|---|---|
| `DRIVER` `SOURCE` 열: `build ≥ 1063 && backplane_build ≥ 1064` | 조건 미달이면 `SOURCE<m>` 키가 **아예 안 생겨** |
| `HVBIAS` 파형 탭: `build > 832` | 미달이면 `STATE<n>/MOD<i>` 에 **그 키가 통째로 사라져** |
| `LVBIAS` 상태 CSV: `build ≥ 833` | 16필드 → **19필드** (뒤에 `biasCmd, biasChannel, biasVoltage`) |
| `XVBIAS` 파형 탭: `build ≥ 1090` | 6필드 추가 |
| `AD` 클램프: `MOD_REV ≤ 'C'` | `CLAMPHIGH`/`CLAMPLOW` 2키 vs `CLAMP1..4` 4키 |
| `HEATERX` 필터: `build ≥ 1046 && backplane ≥ 1049` | `SENSORxFILTER` |

> **결과적으로 같은 ACF 라도 붙어 있는 보드의 펌웨어 빌드에 따라 GUI 가 만들어 내는 키 집합이 달라져.** ACF 호환성을 판단할 때 반드시 기억해야 할 지점이야.

실기 검증 [확정]: science `MOD*_VERSION=1.0.1175 ≥ 1063`, `BACKPLANE_VERSION=1.0.1252 ≥ 1064` → `SOURCE` 키가 나오는 게 앞뒤가 맞아. `STATE0\MOD4` = **19필드**(LVXBias, ≥833), `STATE0\MOD9` = **3필드**(HVXBias, DIO 없음), `STATE0\MOD1` = **40필드**(LVDS 16×2 + DIO 4×2) — 코드와 정확히 일치해.

## 7.6 상태(state) 편집 구조

타이밍 상태 하나 = `lwStates` 의 `QListWidgetItem` 하나. `Qt::UserRole` 에 `QVariantMap` 이 붙어 있어 [확정].

- `"NAME"` — 상태 이름 (저장할 때 **맵이 아니라 목록 위젯 텍스트**로 덮어씀)
- `"CONTROL"` — `"<clock16진>,<keep16진>"`. `CONTROL_COUNT = 6` 비트: **Bit0=INT, 1=FRAME, 2=LINE, 3=PIXEL, 4=TRIGA, 5=TRIGB**
- **`"MOD<slot>"`** — 모듈 하나가 통째로 차지하는 **쉼표 구분 CSV 한 줄**. 위치 기반 인코딩이라 **필드 순서와 개수가 곧 스키마**고 이름표는 안 실려

평탄화되면 `STATE<i>/CONTROL`, `STATE<i>/MOD5`, `STATE<i>/NAME` 이 돼 — 매뉴얼 p.55·p.67 과 일치해.

`stateChanged()` ↔ `clockChanged()` 무한 재귀는 `clock_lock` 이라는 bool 하나로 막아. 둘 다 GUI 스레드 전용이라 그걸로 충분해. **`getClocks` 는 항상 전 모듈을 훑어** — 한 채널만 고쳐도 그 상태의 모든 모듈 CSV 가 다시 쓰여 [확정].

기본값이 `"FF"` 야 — CONTROL 키가 없는 상태는 6비트 전부 1로 읽혀서 **"모든 클럭 체크 + 모든 Keep 체크"** 가 돼. 즉 **미지정 = 이전 값 유지**가 기본이고, 새 상태를 만들면 전부 Keep 으로 시작해.

⚠️ 클립보드 복붙(`Ctrl+C`/`Ctrl+V`)에 **탭 이름이나 모듈 형 검사가 전혀 없어** — DRIVER 탭에서 복사한 걸 LVDS 탭에 붙여도 그냥 위치대로 들어가. 그리고 **상태 이름 중복 검사가 어디에도 없어** [확정].

## 7.7 ⭐ KMTNet 실기 구성 대조

science (`BACKPLANE_TYPE=1` X12, `REV=5` Rev F, `VERSION=1.0.1252`) [확정]:

| 슬롯 | `MODn_TYPE` | 모듈 | GUI 클래스 | 매뉴얼 배치 규칙 | VCPU 탭 | STATUS 필드 |
|---:|---:|---|---|---|:---:|---|
| 1 | 10 | LVDS | `LVDS` | 제약 없음 ✅ | ✅ | `DINPUTS`, `VCPU_OUTREG0..15` |
| 2 | 1 | Driver | `DRIVER` | 제약 없음 ✅ | — | **없음** |
| 3 | 1 | Driver | `DRIVER` | 제약 없음 ✅ | — | **없음** |
| 4 | 9 | LVXBias | `LVBIAS` (공유) | 슬롯 3-4 또는 9-12 ✅ | ✅ | `LVLC_V/I1..24`, `LVHC_V/I1..6`, `DINPUTS`, `VCPU_OUTREG*` |
| **5** | **17** | **ADM** | `ADM` (빈 껍데기) | 비디오 슬롯 5-8 ✅ | — | **없음** |
| 6 | 0 | **빈 슬롯** | — | | | |
| 7 | 0 | **빈 슬롯** | — | | | |
| **8** | **17** | **ADM** | `ADM` (빈 껍데기) | 비디오 슬롯 5-8 ✅ | — | **없음** |
| 9 | 8 | HVXBias | `HVBIAS` (공유) | 슬롯 3-4 또는 9-12 ✅ | — | `HVLC_V/I1..24`, `HVHC_V/I1..6` |
| 10 | 1 | Driver | `DRIVER` | ✅ | — | **없음** |
| 11 | 1 | Driver | `DRIVER` | ✅ | — | **없음** |
| 12 | 0 | **빈 슬롯** | — | | | |

- TAPLINE 32줄: `AM1L`~`AM16R`(슬롯5 ADM 18채널 중 16개) + `AM55L`~`AM70R`(슬롯8 ADM 18채널 중 16개). 4K×4K 8-amp CCD 두 장 → 채널 16개씩 [확정].
- Driver 4장 × 8채널 = **32채널**. ACF 의 `LABEL`/`FASTSLEWRATE`/`SLOWSLEWRATE`/`ENABLE`/`SOURCE` 가 각각 32개인 게 정확히 이거야 [확정].
- **VCPU 탭이 뜨는 건 슬롯 1(LVDS)과 슬롯 4(LVXBias) 둘뿐**이야.
- **Driver 4장과 ADM 2장은 모듈 STATUS 표시가 0개**야. 온도 `MOD<n>/TEMP` 만 부모(`archongui.cpp:2340~2342`)가 찍어.

guide (`KMTK_GUI_162`) [확정]:

| 슬롯 | `MODn_TYPE` | 모듈 | VCPU | 비고 |
|---:|---:|---|:---:|---|
| 3, 4 | 1 | Driver | — | |
| **5, 6** | **2** | **AD** (4채널 ×2) | — | TAPLINE `AD1`~`AD8` |
| 7, 10 | 11 | HeaterX | ✅ | 센서 A/B/C ×2장 = **온도 6채널 + 히터 4개** |
| 9 | 8 | HVXBias | — | |

## 7.8 모듈 체계의 결함

| # | 내용 | 위치 | 등급 |
|---|---|---|---|
| M1 | **`VCPU_INREG` off-by-one.** 쓰기는 `.arg(i)`(0기점), 읽기는 `.arg(i+1)`(1기점). **5개 클래스 전부** 같은 버그(복붙 탓). ACF 왕복에서 VCPU 입력 레지스터가 **한 칸 밀리고 마지막 하나를 잃어** | `modules.cpp:1640` vs `:1681`, `:2624`/`:2691`, `:3583`/`:3615`, `:3998`/`:4026`, `:4737`/`:4812` | **중(잠복)** |
| M2 | `TModule` 에 **가상 소멸자 없음.** 기반 포인터로 `delete` — 현재는 파생이 할 일이 없어 사고는 안 나지만 UB | `modules.h:9~26`, `archongui.cpp:2123` | 하 |
| M3 | `usesClocks()` 가 **순수 가상인데 호출하는 곳이 0곳** — 죽은 인터페이스 | `modules.h:12` | 정보 |
| M4 | `DRIVER::updateUI()` 가 `leSlowSlewRates[i]->setText()` 를 **두 번** 호출 (DriverX 도 동일) | `modules.cpp:173`, `:175` | 정보 |
| M5 | `DRIVERX` 는 `Source` 열 UI 를 **조건 없이 만드는데** parseUI/updateUI 는 `build≥1063` 로 막아 → 구펌웨어에서 칸은 보이는데 저장이 안 돼. `DRIVER` 는 UI 생성도 같이 막아서 **일관성이 없어** | `modules.cpp:311~313` vs `:403` | 하 |
| M6 | `MAX_MODULES=16` 이라 12슬롯(X12) 백플레인에서도 모듈 12~15 를 허용. 실제 방어는 `MOD<n>_TYPE` 이 비어서 걸리는 것뿐 | `archon.h:27` | 하 |
| M7 | `ATLAS` 의 STATUS 키는 `TEC_ENABLE`(밑줄 있음)인데 설정 키는 `TECENABLE`(밑줄 없음) — 오타가 아니라 실제로 그래 | `modules.cpp:3213` vs `:3088` | 정보 |
| M8 | `HEATERX` 의 STATUS 온도 필드는 `TEMPA/B/C` 인데 UI 라벨과 설정 키는 `SENSORA/B/C` 계열 — 이름 체계가 STATUS 와 CONFIG 사이에서 어긋나 | `modules.cpp:4924` vs `:4699` | 정보 |
| M9 | `HEATERAP`/`AI`/`AD` 가 **설정 키(PID 게인)로도, STATUS 필드(현재 P/I/D 항 기여분)로도** 같은 문자열을 써. 맵이 달라서 충돌은 안 나지만 문서에서 헷갈리기 딱 좋아 | `modules.cpp:2579~2586` vs `:2814~2816` | 정보 |

---

# 8. 영상·해석 기능

## 8.1 표시

| 기능 | 동작 | 근거 |
|---|---|---|
| 이미지 모드 | **Nearest(0) / Max(1) / Min(2)**. 다운샘플 박스 안에서 `qMax`/`qMin` | `archongui.cpp:812~814`, `imagewidget.cpp:431` |
| ⚠️ 모드가 먹히는 조건 | **`zoom ≥ 1.0` 이면 모드를 통째로 무시하고 무조건 Nearest.** 즉 **축소할 때만** Max/Min 이 의미 있어 | `imagewidget.cpp:98`, `:156` |
| raw 경로 | **모드 분기가 아예 없어.** 항상 Nearest, 항상 16bit | `imagewidget.cpp:75~88` |
| LUT | 16bit: `grayscale[65536]`, HDR: `grayscalehdr[1048576]`(값 `>>12`, 상위 20bit) | `imagewidget.cpp:412~427` |
| 게인 슬라이더 | 이미지 −1000~1000 → `exp(v/100)` (e^±10). **raw 는 `exp(v/200)`** (e^±5) — 감도 절반 | `archongui.cpp:3009~3016`, `:3122~3129` |
| 오프셋 | −65535~65535. **HDR 만 ×16** (16bit 눈금을 20bit 공간으로 환산) | `imagewidget.cpp:417` |
| `fitGainOffset()` | 신호 박스(없으면 전체)의 min/max 로 화면 0~255 를 꽉 채우게 자동 맞춤. **raw 탭엔 없어** | `archongui.cpp:3025~3089` |
| 확대 | ×2 / 1:1 / ÷2. `ImageScrollWidget::setZoom` 이 **중심 픽셀을 유지**하도록 스크롤바를 다시 놓아 | `imagescrollwidget.cpp:23~37` |

⚠️ 매 `setLUT` 호출마다 **1,114,112칸 LUT 를 통째로 다시 계산해.** 슬라이더가 `setTracking(true)` 라 드래그 중 계속 돌아 — 느린 이유가 이거야 [확정].

마우스 규약 [확정]:

| 버튼 | 동작 | 표시 |
|---|---|---|
| 좌클릭 릴리스 | 수평/수직 절단선 지정 | 수평 빨강, 수직 파랑 |
| 우클릭 드래그 | **신호 박스** | 초록 |
| 가운데 드래그 | **노이즈 박스** | 노랑 |
| 이동 | 좌표·값 보고 | 상태바 `X: … Y: … Value: …` |

## 8.2 통계

`updateStats()` (`archongui.cpp:3221~3323`) [확정]:

```
N = (x2-x1+1)(y2-y1+1)
신호:  mean_s = Σv / N,  var_s = Σ(v-mean_s)² / N,  std_s = √var_s
노이즈: mean_n, std_n  동일 산식
signal = mean_s - mean_n
DR     = 20·log10(signal / std_n)  [dB]   (std_n==0 이면 0)
```

> ⚠️ **표준편차가 N 나눗셈(모집단)이야.** N−1 이 아니야. 작은 박스에서는 읽기잡음을 살짝 낮게 줘. 잡음 측정용으로 쓸 때 알아둬야 해.

`updateDiffStats(prev, next)` (`:3325~3439`) [확정]:

```
diffmean = Σ(f1-f2) / N
diffvar  = Σ(f1-f2-diffmean)² / (2N)      ← ★ 2로 나눠
```

**2N 나눗셈이 핵심**이야. 독립인 두 프레임을 빼면 분산이 2배가 되니까 되돌리는 거고, 그래서 `diffvar` 는 **고정패턴잡음(FPN)이 상쇄된 한 프레임의 잡음 분산 추정치**야. 두 프레임의 크기·HDR 이 다르면 조기 반환해.

## 8.3 플롯

```
수평: hy[i] = Data[m_hplot*w + i]      (i=0..w-1)
      H Avg 체크 → hy[i] = mean_{j=y1..y2} Data[j*w+i]   (신호 박스의 세로 구간 평균)
수직: vy[i] = Data[i*w + m_vplot]      (i=0..h-1)
      V Avg 체크 → vy[i] = mean_{j=x1..x2} Data[i*w+j]
```

raw 판(`updateRawStats` `:3898`, `updateRawPlots` `:3965`)은 구조는 같은데 **HDR 분기가 없고**(raw 는 항상 16bit) `dv`/DR 계산도 없어. x축 제목만 `ADXRAW` 에 따라 갈려 [확정]:

- `ADXRAW=0` → **"Sample (10ns)"** — 100 MHz
- `ADXRAW=1` → **"Sample (2.5ns)"** — 400 MHz

우리 science 는 `ADXRAW=0` 이라 10 ns 축이야. ⚠️ **ADM 전용 눈금이 없어.** ADM 은 12.5 MHz 로 샘플해서 18비트를 16비트로 자른 뒤 **8번 복제(디더링 섞어서)** 하니까(매뉴얼 p.12, p.69), **ADM raw 는 10 ns 축에 그려지지만 실제 유효 샘플은 8틱마다 하나**야. 파형 읽을 때 감안해야 해 [확정].

> 그래서 매뉴얼 p.69 가 **SHP/SHD 를 8의 배수로 두라고 권고해.** science ACF 의 `SHP1=72 SHP2=112 SHD1=136 SHD2=200` 은 **전부 8의 배수**야 — 규약을 지키고 있어 [확정].

## 8.4 PTC (Photon Transfer Curve)

축은 **x = Signal [ADU], y = Variance [ADU²]**, 선형축이야(`archongui.cpp:940~941`) [확정].

| 함수 | 하는 일 |
|---|---|
| `snapPTC()` (`:3570`) | 누적 개시만. `ptccount = ptctotal = N`, `ptcmean = ptcvar = 0`. **계산이 여기 없어** |
| **누적 본체** (`:3392~3438`) | **`updateDiffStats()` 안에 숨어 있어.** 새 프레임마다 `ptcmean += (신호박스평균 − 노이즈박스평균)`, `ptcvar += diffvar`, `ptccount--`. 0 이 되면 `ptctotal` 로 나눠 점 하나 삽입 |
| `resetPTC()` (`:3579`) | 점 전부 날려 |
| `savePTC()` (`:3587`) | **현재 작업 디렉터리에 고정 이름 `ptc.txt`**. 경로 선택도, 덮어쓰기 경고도, `fopen` 실패 검사도 없어 |

⭐ **게인(e−/ADU)은 코드 어디에도 없어** [확정]. `ptcx`/`ptcy` 를 쓰는 곳은 삽입·그리기·저장뿐이고, 기울기 적합도 역수도 `e-/ADU` 라는 문자열도 없어. **GUI 는 축만 그려.** 게인은 사람이 밖에서 내야 해:

```
광자잡음 지배 구간에서  Var = Signal / g   (g = e-/ADU)
→  g = 1 / (PTC 기울기)
```

읽기잡음(y절편)도 풀웰(꺾이는 지점)도 GUI 는 안 알려줘.

PTC 쓸 때 조심할 것 [확정]:

1. 첫 프레임은 그냥 넘어가 — 누적이 `updateDiffStats` 에서 일어나고 그건 **직전 표시 프레임이 있을 때만** 불려.
2. `diffvar` 는 "직전 표시 프레임 − 새 프레임" **연속 쌍**마다 계산돼. 프레임 2,3,4 를 받으면 (2,3),(3,4) 두 쌍이고 3이 양쪽에 들어가 — **쌍이 독립이 아니야.** 평균은 맞지만 오차 추정엔 편향이 있어.
3. 두 프레임의 크기나 HDR 이 다르면 `updateDiffStats` 가 조기 반환하는데 **`ptccount` 는 안 줄어** → 설정을 바꾸면 PTC 누적이 조용히 멈춘 채 남아.
4. 노이즈 박스를 안 그렸으면 1픽셀 평균이 바이어스로 쓰여. **신호 박스와 노이즈 박스를 둘 다** 제대로 잡아야 해.

## 8.5 파일 입출력

### `.raw` — 헤더 없는 순수 덤프

```
저장: <leBaseFilename>_<w>x<h>_<frame>.raw
내용: Data 를 그대로 write. HDR 이면 4바이트/샘플, 아니면 2바이트/샘플.
raw:  <Base>_<w>x<h>_<frame>_raw.raw  — 항상 2바이트/샘플
```

**메타데이터가 하나도 없어. 치수는 오직 파일 이름에만 들어 있어** [확정]. 읽을 때는 정규식 `_(\d+)x` 로 폭을 뽑고, 못 뽑거나 `size % w != 0` 이면 대화상자로 물어봐. `h = size / w`, **항상 16비트로 가정**해.

`saveSequence()` 는 `savecount` 만 세팅하고 `newFrame()` 이 그만큼 자동 저장해. `cbSaveAll` 은 무제한.

### FITS — 별도 경로, 엔지니어링용

`saveFITS()` (`:4150~4254`)가 쓰는 헤더는 **딱 7개**야 [확정]:

```
SIMPLE = T
BITPIX = 16 (HDR 이면 32)
NAXIS  = 2
NAXIS1 = w,  NAXIS2 = h
BZERO  = 32768 (또는 2147483648)
BSCALE = 1
END + 2880 패딩
데이터: 빅엔디언 변환 + 부호비트 토글 (buf[x] ^ 0x8000 / dbuf[x] ^ 0x80000000)
```

> ⚠️ **노출시간·온도·타임스탬프·탭 구성·게인/오프셋·관측 대상 — 아무것도 없어.** 이 GUI 의 FITS 는 **엔지니어링 확인용**이지 관측 산출물이 아니야. KMTNet raw spec 이 요구하는 헤더는 ICS 쪽에서 따로 만들어야 해.
> 그리고 **`saveFITS`/`openFITS` 는 이미지 프레임 전용**이야. **raw 프레임을 FITS 로 내보내는 경로가 없어** — raw 는 `.raw` 덤프뿐이야.

`openFITS()` 는 `BITPIX`/`NAXIS1`/`NAXIS2` **세 개만** 해석하고 `BZERO`/`BSCALE` 도 안 읽어 — 즉 **자기가 쓴 FITS 만 제대로 읽어** [확정].

### 플롯 txt

| 함수 | 파일 (고정 이름, 현재 작업 디렉터리) | 헤더 | 서식 |
|---|---|---|---|
| `saveHPlot` / `saveVPlot` | `hplot.txt` / `vplot.txt` | `Pixel\tSignal` | **`%0.0lf`** |
| `saveRawHPlot` / `saveRawVPlot` | `rawhplot.txt` / `rawvplot.txt` | 〃 | **`%0.0lf`** |
| `savePTC` | `ptc.txt` | `Signal\tVariance` | `%0.6lf` |

> ⚠️ 플롯 4종이 **`%0.0lf` — 소수점을 버려.** H/V Avg 로 평균낸 값도 정수로 잘려. **평균 잡음 분석에 이 파일을 쓰면 안 돼.** PTC 만 소수 6자리로 살아 있어 [확정].
> ⚠️ 다섯 함수 전부 **`fopen` 반환값을 검사 안 해** — 쓰기 권한 없는 디렉터리에서 실행하면 널 역참조로 죽어.

## 8.6 영상 계통의 결함

| # | 내용 | 위치 | 등급 |
|---|---|---|---|
| I1 | `openHDRFrame()` read 실패 시 `frameMutex.unlock()` 누락 → **교착** | `archongui.cpp:3806~3812` | **높음** |
| I2 | `ImageWidget::m_mode` **생성자 초기화 누락** + 콤보 연결이 `addItem` **뒤**라 최초 `currentIndexChanged(0)` 를 못 받아. 사용자가 콤보를 한 번도 안 건드리면 미정의값 → **축소하는 순간 Max/Min 중 아무 쪽으로 튀어.** 확대 상태에선 안 드러나 | `imagewidget.cpp:6~35`, `archongui.cpp:812~815` | 중 |
| I3 | 플롯 txt 가 `%0.0lf` — 평균값 소수점 소실 | `:3596`/`:3605`/`:4051`/`:4060` | 중 |
| I4 | `fopen` 실패 미검사 → 널 역참조 | 위 4개 + `:3587` | 중 |
| I5 | 크기/HDR 불일치로 `updateDiffStats` 조기 반환할 때 `ptccount` 를 안 줄여 → PTC 누적이 조용히 멈춤 | `:3336~3343` vs `:3394` | 중 |
| I6 | `zoomFit()` 이 raw 치수를 무시하고 `f->width()/height()` 사용. 지금은 raw 탭에 버튼이 없어 잠복 | `imagescrollwidget.cpp:45~58` | 하 |
| I7 | `openFITS` 가 `BZERO`/`BSCALE` 무시 → 외부 FITS 오독 가능 | `:4256` | 하 |
| I8 | `openFrame()` 두 판이 60여 줄 중복 | `:3614` / `:3686` | 하 |
| I9 | 65536칸 `vx`/`vy` 를 만들고 안 씀 — 히스토그램 잔해 | `:3237~3240`, `:3913~3916` | 정보 |
| I10 | `openHDRFrame` 은 `do-while` 이라 파일명에 폭이 박혀 있어도 **무조건 한 번 물어봐**. `openFrame` 의 `while` 과 달라 | `:3790~3799` | 정보 |

---

# 9. 전원·감시

## 9.1 `POWER` 상태 6종

`archon.h:52` 의 `POWER_STATES` 와 매뉴얼 p.47 이 일치해 [확정].

| 값 | 상수 | 매뉴얼 뜻 | GUI 표시등 색 | 툴팁 |
|---:|---|---|---|---|
| 0 | `PWR_UNKNOWN` | "usually an internal error" | 짙은 회색 | UNKNOWN |
| 1 | `PWR_NOT_CONFIGURED` | "no configuration applied" (= APPLYALL 전) | 회색 | NOT CONFIGURED |
| 2 | `PWR_OFF` | "power to the CCD is off" | **빨강** | OFF |
| 3 | `PWR_INTERMEDIATE` | "some modules have enabled power to the CCD, some have not" | 노랑 | INTERMEDIATE |
| 4 | `PWR_ON` | "Power to the CCD is on" | **초록** | ON |
| 5 | `PWR_STANDBY` | "System is in standby" | 파랑 | STANDBY |

표시등 위젯(`PowerWidget`)은 **색칠한 네모 하나**가 전부야 — 30×10 px, 검정 1px 테두리. **문구는 위젯이 안 갖고 있고 전부 밖에서 `setToolTip()` 으로 붙여**서 마우스를 올려야 보여 [확정].

> 중요한 구분: **`POWER` 는 "CCD 로 가는 바이어스/클록 전원" 상태야. 컨트롤러 자체 전원이 아니야.** 컨트롤러 공급전원 건강은 `POWERGOOD` 이 담당해. **두 축을 섞어서 하나의 "정상" 지표로 만들면 안 돼.**

## 9.2 🐞 `PWR_STANDBY` early return — 가장 위험한 표시 버그

`archongui.cpp:2234~2239` [확정]:

```cpp
else if (u == PWR_STANDBY)
{
    wPower->setToolTip("STANDBY");
    wPower->setColor(Qt::blue);
    return;                      // ← 2238
}
```

`parseStatus()` 전체를 그 자리에서 끝내버려. 그래서 **전원이 STANDBY 인 동안에는 그 아래가 통째로 갱신을 멈춰**:

- 백플레인 온도 (`:2251~2253`)
- OVERHEAT / POWERFAIL 경고 (`:2255~2262`)
- **전원 레일 전압·전류 24칸 전부** (`:2263~2334`)
- 모듈 온도 12칸과 모듈별 `parseStatus()` (`:2340~2344`)

다른 5개 분기엔 `return` 이 없어 — **딱 STANDBY 만 그래서 복붙 실수로 보여.** 화면 증상은 "스탠바이로 넘어가는 순간 온도·전압 판이 마지막 값에서 얼어붙는다" 야. **표시만 죽고 제어는 멀쩡하니까 조용히 오해를 부르는 종류야.** 우리 ICS 는 이걸 절대 흉내내면 안 돼.

## 9.3 전원 레일 정상 범위 (매뉴얼 p.41)

표준 Archon, `Souriau 28-pin UT002028PH` 원형 커넥터 [확정]:

| 레일 | Power Good Range | 실기 사용 |
|---|---|---|
| +2.5 V Digital | **+2.1 … +2.9 V** | ✅ (백플레인 **필수**) |
| +5 V Digital | **+4.4 … +5.6 V** | ✅ (백플레인 **필수**) |
| +6 V Analog | **+5.5 … +6.6 V** | ✅ (ADM 이 요구) |
| −6 V Analog | **−5.3 … −6.6 V** | ✅ (ADM 이 요구) |
| +17 V Analog | **+16.4 … +17.5 V** | ✅ |
| −17 V Analog | **−16.6 … −17.7 V** | ✅ |
| +35 V Analog | **+34.3 … +36.0 V** | ✅ |
| −35 V Analog | **−33.8 … −35.9 V** | ❌ **표준 PSU 가 안 만들어** |
| Heater | **+18.0 … +36.0 V** | (히터 쓸 때) |
| User | **+18.0 … +36.0 V** | ❌ |
| Fan (+12 V) | 팬에 직결 | ✅ |

XV 섀시 변형(p.42)은 세 줄만 달라 — `-35V` → **−100 V(−97 … −103 V)**, `User` → **+100 V(+97 … +103 V)**.

### ⭐ "7개냐 8개냐" 정리

세 숫자가 서로 달라서 헷갈리기 딱 좋아. 층위를 나눠야 해 [확정]:

| 세는 기준 | 개수 | 목록 |
|---|---:|---|
| **Power Good Range 가 정의된 레일** (p.41) | **8** | P2V5·P5V·P6V·N6V·P17V·N17V·P35V·**N35V** (+ HEATER·USER 로 범위 항목은 10) |
| **표준 PSU 가 실제로 만드는 전압** (p.43) | **7** | "+2.5V, +5V, +6V, -6V, +17V, -17V, and +35V" — **N35V 는 안 만들어** |
| 파워보드 감시 스위치 (Figure 28, p.42) | 10 | 위 8 + `HEATERGOOD` + `USERGOOD` (+ 종합 `PWRGOOD`) |
| **STATUS 가 보고하는 V/I 쌍** (p.47) | **12** | 위 8 + P100V + N100V + USER + HEATER |

⚠️ 매뉴얼 자체 모순이야 — p.44 전력소비 표에 `-35V` 열이 없고 p.43 본문도 안 만든다는데, p.41 표와 Figure 28 에는 버젓이 있어. **하드웨어 배선은 있고 표준 PSU 가 안 채우는 구조로 보여** [유력].

알람 임계값을 만든다면 **8개 기준 표(p.41)** 를 쓰되, **안 쓰는 레일(N35V·USER·P100V·N100V)은 감시 스위치가 꺼져 있어서 값이 0 근처로 나와. 0 을 알람으로 처리하면 안 돼** [확정].

### `POWERGOOD` 의 정확한 의미

- 매뉴얼 정의는 한 줄뿐 — "n = 1 when system power supply is good" (p.47).
- 실체는 파워보드의 종합 신호 `PWRGOOD` 이고, 백플레인이 P9 의 IDC 케이블로 받아(Figure 8, p.20).
- ⚠️ 즉 **`POWERGOOD=1` 은 "여덟 레일 전부 정상" 이 아니라 "P1/P7 스위치로 감시하도록 켜둔 레일 전부 정상" 이야.** 꺼진 레일은 판정에 안 들어가 [확정].
- 그래서 **레일별 `_V` 값을 p.41 범위와 따로 대조하는 이중 확인**이 필요해.

모듈 쪽 보호도 이중이야 — 각 Driver/Bias 모듈이 시스템 레일을 **하드웨어 비교기로 상시 감시**하다가 범위를 벗어나면 CCD 로 가는 포토아이솔레이터를 전부 열어버려. FPGA 가 리셋돼도 릴레이가 열리고, **재구성 전에는 다시 안 닫혀** (p.11, p.27, p.29, p.31, p.33) [확정].

## 9.4 STATUS 필드 전수

### 시스템 헤더 (p.47)

| 키 | 뜻 | 단위·범위 | GUI 표시 |
|---|---|---|---|
| `VALID` | "n = 1 if **remaining status fields are valid**" | 0/1 | Status 그룹 "Status Valid" — **숫자로 찍기만 해** |
| `COUNT` | 시스템 상태가 갱신된 횟수 | 무단위 카운터 (랩어라운드 [확인불가]) | "Status Count" |
| `LOG` | 대기 중인 로그 개수 | 개수 | **화면엔 안 떠.** 이 수만큼 `FETCHLOG` 를 반복해 로그창에 뿌려 |
| `POWER` | §9.1 | 0~5 | 표시등 색 |
| `POWERGOOD` | 공급전원 종합 | 0/1 | 0 이면 `POWERFAIL` 문구 |
| `OVERHEAT` | 과열 | 0/1 | 1 이면 `OVERHEAT` 문구 |
| `BACKPLANE_TEMP` | 백플레인 온도 | **℃** | 소수 1자리 + `" C"` |
| `FANTACH` | 팬 속도 (**Rev F only**) | RPM | "Fan Speed (RPM)" |
| `EXTCLKPRESENT` | **매뉴얼 목록에 없음** | — | "Present"/"Absent" |

### 전압 레일 V/I 쌍 12개 = 24 필드 (p.47)

`P2V5`, `P5V`, `P6V`, `N6V`, `P17V`, `N17V`, `P35V`, `N35V`, `P100V`, `N100V`, `USER`, `HEATER` 각각에 `_V`, `_I`.

> ⚠️ **단위 함정**: **시스템 레일 전류는 A** 인데(`P2V5_I=f ; … current in A`, p.47), **모듈 바이어스 전류는 mA** 야(`MODm/LVLC_In=f ; … in mA`, p.48). 섞으면 안 돼 [확정].

### 모듈별 필드 (p.48~49)

| 키 | 조건 | 단위 |
|---|---|---|
| `MODm/TEMP` | 모든 모듈 | **℃**. GUI 는 모듈 클래스가 아니라 **부모가 파싱**해(`archongui.cpp:2340`) |
| `MODm/LVLC_Vn`/`_In` (n=1..24), `MODm/LVHC_Vn`/`_In` (n=1..6) | LV(X)Bias | V / **mA** |
| `MODm/HVLC_Vn`/`_In` (24), `MODm/HVHC_Vn`/`_In` (6) | HV(X/Y)Bias | V / **mA** |
| `MODm/TEMPA`, `TEMPB` | Heater(X) | ⚠️ **K (켈빈)** — ℃ 아니야 |
| `MODm/TEMPC` | **HeaterX 전용** | **K** |
| `MODm/HEATERAOUTPUT`, `HEATERBOUTPUT` | Heater(X) | V |
| `MODm/HEATERAP`/`AI`/`AD`, `BP`/`BI`/`BD` | Heater(X) | P/I/D 항 기여분, 부호있는 정수 |
| `MODm/DINPUTS` | LV(X)Bias·Heater(X) 는 **8자**, HS·LVDS 는 **4자** | 각 자리 0/1 |
| `MODm/MAG_Vn`/`_In`, `OFS_Vn`/`_In` (n=1..12) | HS | V / mA |
| `MODm/XVP_Vn`/`_In`, `XVN_Vn`/`_In` (n=1..4) | XVBias | V / mA |
| `MODm/RTDn` (1..8), `HALLn` (1..3), `VAC`, `TEC_*`, `ION_*` | Atlas | RTD 는 **저항** → `convrtd()` 로 ℃ 환산 |
| `MODm/VCPU_OUTREGn` (**n=0..15**) | DIO 있는 모듈 | unsigned 16bit |

⚠️ **또 하나의 단위 함정**: HeaterX 설정(target·limit)은 **℃**(p.60~61)인데 STATUS 보고(`TEMPA` 등)는 **K**(p.48)야. **반드시 변환해야 해** [확정].

`DRIVER`·`DRIVERX`·`AD`·`ADF`·`ADX`·`ADLN`·`ADM` 일곱 클래스는 `parseStatus()` 가 **빈 함수**야 — STATUS 에서 아무것도 안 읽어 [확정].

## 9.5 ⚠️ `VALID` 를 GUI 는 게이트로 안 써

매뉴얼 p.47 은 `VALID=0` 이면 **그 응답의 나머지 STATUS 필드가 전부 무효**라고 규정해. "일부만 무효" 라는 단서는 어디에도 없어 [확정].

그런데 **stock GUI 는 `VALID` 를 숫자로 화면에 찍기만 해**(`archongui.cpp:2195`). 그 아래 `BACKPLANE_TEMP`·전압·`OVERHEAT`·`POWERGOOD` 갱신은 `VALID` 와 **무관하게 그냥 진행돼.** GUI 전체에서 "VALID" 문자열은 그 한 줄이 유일해 [확정].

> **GUI 를 정본으로 삼아 흉내내면 무효 데이터를 그대로 표시하게 돼.** 우리 ICS 는 `VALID=1` 일 때만 나머지를 채택하도록 규정해두는 게 맞아. 그리고 `COUNT` 를 같이 봐야 신선도까지 잡혀 — 값이 안 늘면 컨트롤러가 내부 상태 레지스터를 갱신 못 하고 있다는 뜻이거든(p.74).
>
> 매뉴얼은 `VALID` 가 언제 0 이 되는지, 0 일 때 필드에 뭐가 들어오는지(직전 값 유지? 0? 쓰레기?)를 **안 적어놨어** [확인불가]. **실측대상**이야.

## 9.6 ⭐ 폴링 구조

### 주기 — 500 ms 고정

```cpp
// archongui.cpp:1224~1227
// Start timer for polling at 5Hz          ← 주석이 낡았어
updateTimer = new TUpdateTimer(this);
connect(updateTimer, SIGNAL(update()), this, SLOT(poll()));
updateTimer->startUpdateTimer(500);
```

⚠️ **주석은 5 Hz 라는데 실제 인자는 500 ms = 2 Hz 야.** 그리고 `poll()` 은 **한 틱에 명령 하나만** 내니까 STATUS 와 FRAME 은 **각각 약 1 Hz** 야 [확정]. (200 → 500 으로 늘리면서 주석을 안 고친 걸로 보여.)

`TUpdateTimer` 는 전부 43줄짜리고 실행부가 이게 다야:

```cpp
void TUpdateTimer::run() { while (!thread_exit) { msleep(updateInterval); emit update(); } }
```

파일 머리 주석이 존재 이유를 밝혀 — **"QTimer 가 산발적으로 CPU 를 크게 먹어서 QTimer 대신 쓴다"**(`updatetimer.cpp:3~5`). 조절 수단은 시작 인자 하나뿐이고 **돌기 시작한 뒤엔 주기를 못 바꿔.** 드리프트 보정도 없어 [확정].

### `poll()` 의 명령 순서

```cpp
// archongui.cpp:2833~2851
switch (pollstep) {
case 0: if (!archon->command("STATUS")) pollstep++; break;
case 1: if (!archon->command("FRAME"))  pollstep++; break;
}
if (pollstep > 1) pollstep = 0;
```

**STATUS → FRAME → STATUS → FRAME …** 무한 교대. 딱 이 둘뿐이야. `SYSTEM` 은 폴링에 안 들어가 — **연결 시 1회**(그리고 파일 로드 시 `parseSystem()` 재호출)뿐이야 [확정].

핵심 두 가지:

1. **`command()` 가 성공(0)했을 때만 `pollstep++`.** 거절(1)당하면 단계를 그대로 두고 다음 틱에 같은 명령을 다시 시도해 — 교대 순서가 절대 안 깨져. 자연스러운 백프레셔야.
2. **`poll()` 은 `getResult()` 를 안 불러.** 던져놓고 바로 반환하는 fire-and-forget 이라 GUI 가 안 멈춰.

### ⭐ 명령이 버려지는 기전 — "화면이 얼어붙는" 착시의 정체

`Archon::command()` 는 **`CommandInProgress` 면 큐에 안 쌓고 즉시 거절(return 1)** 해(`archon.cpp:187`). 그래서 **FETCH 가 도는 동안에는 `FRAME` 응답이 한 번도 안 와** [확정].

실측으로 확인됐어 [실측]: FETCH 중에도 엔진은 **368.0 행/초 만속**으로 계속 써. 재관측에서 라인 표시가 10 → 1500 으로 점프했고, 1490행 ÷ 368 = 4.05초 = FETCH 시간이야. **즉 "독출 정지" 는 표시 착시였고, 기전이 바로 이 "폴 거절" 이야.**

### 폴링이 다른 명령과 겹칠 때 — 4중 방어 [확정]

| 방어 | 내용 |
|---|---|
| (a) **같은 스레드** | `poll()` 도 버튼 슬롯도 전부 GUI 스레드 이벤트 루프에서 실행돼. 인터리빙 자체가 없어 |
| (b) **사용자 동작은 먼저 비워** | 거의 모든 동작 슬롯 첫 줄이 `archon->getResult()`. 최악의 경우 5초까지 GUI 가 굳어 |
| (c) **폴링은 순번을 지키며 재시도** | 위 `pollstep` 로직 |
| (d) **오래 걸린 뒤엔 몰아서 나가** | `getResult()` 가 이벤트 루프를 안 돌리니 큐 연결된 `update()` 가 쌓여. 작업이 끝나면 쌓인 `poll()` 이 우르르 실행되는데 대부분 거절돼서 no-op 이 돼 |

⚠️ 예외 하나: **자동 페치가 폴링 콜백 안에서 GUI 를 막아.** `parseFrameStatus()` 끝에서 Auto Fetch 가 켜져 있으면 `fetchFrame()` 을 부르고, 그 안에서 `getResult()` 를 두 번 불러(`:1838`, `:1840`). **폴링이 부른 슬롯 안에서 블로킹하는 유일한 경로**야.

### 로그 수집도 폴링의 부산물

`getStatus()` 는 응답의 `LOG=n` 만큼 `FETCHLOG` 를 반복해서 컨트롤러 로그를 GUI 로그창으로 끌어와(`archon.cpp:600~606`) [확정]. **컨트롤러는 절대 먼저 말을 안 거니까 이 폴링이 유일한 비동기 통보 경로야.** 폴링을 끄면 컨트롤러 로그도 안 들어와.

로그창(`telog`)은 읽기전용 `QPlainTextEdit` 이고 **최대 1000블록** — 오래된 줄은 자동으로 밀려나가 [확정].

## 9.7 `RMap` 파싱 규칙 — 엄격해

`getSystem()`/`getStatus()`/`getFrameStatus()` 셋이 완전히 동일한 규칙을 써 [확정]:

```cpp
map.clear();
interfaceFlush();
interfaceCommand("SYSTEM", s, ARCHON_TIMEOUT, false);   // log=false ← 로그창 도배 방지
fields = s.split(' ');
foreach (field, fields) {
    tokens = field.split('=');
    if (tokens.count() != 2) LOGERROR("...");           // 정확히 2조각이 아니면 실패
    map.insert(tokens[0], tokens[1]);
}
```

1. 응답은 공백 구분 `KEY=VALUE` 나열이어야 해 (매뉴얼 p.45).
2. **값에 공백이 있으면 안 돼** — 그 토큰이 꼴을 못 갖춰서 전체 파싱이 실패해.
3. **값에 `=` 가 있어도 안 돼** — `split('=')` 가 3조각을 내서 실패. `1.0.1252` 처럼 점은 괜찮아.
4. ⚠️ 토큰 하나만 어긋나도 **맵 전체가 버려지는 게 아니라, 그 시점까지 채워진 부분 맵이 시그널로 나가.** 오류 경로에서도 `emit msgSystem(system)` 을 하거든.

`SYSTEM` 응답 키는 매뉴얼 p.46 의 9종 + **`POWER_ID`**(매뉴얼 목록엔 없고 부록 A p.96 엔 있어) = 10종이야. GUI 가 읽는 것도 정확히 이 10종이야 [확정]. `MOD_PRESENT` 는 **16진 비트필드, LSB=슬롯1** 이고 부록 A 의 `MOD_PRESENT=14`(= 슬롯 3·5)로 규약을 검증했어 [확정].

---

# 10. 펌웨어·빌드

## 10.1 보유 `.mcs` 4종

> **2026-09-03 갱신** — 운영자가 **Rev H 백플레인 이미지(FW 1.0.1271)** 를 받아 넣었고, 폴더명이 `ArchonFW_20250825` → **`ArchonFW`** 로 바뀌었어. 아래 표·판정은 그 뒤 상태야.

| 파일 | 크기(B) | md5 | 데이터 레코드 | 펼친 크기 | mtime |
|---|---:|---|---:|---:|---|
| `archonbackplanerevf_1_0_1252.mcs` | 19,579,653 | `96d9c5f4…0e8c` | 444,952 | 6.79 MiB | 2024-04-13 |
| ⭐ `archonbackplanerevh_1_0_1271.mcs` | 17,904,281 | `c59ba314…47a6` | 397,837 | 6.07 MiB | **2026-09-03** |
| `archondriverrevd_1_0_1175.mcs` | 1,276,689 | `bd8d3d6e…bcce` | 29,013 | 0.44 MiB | 2021-08-07 |
| `archonhvxbiasreva_1_0_1175.mcs` | 1,276,689 | `bb4a23fd…6f97` | 29,013 | 0.44 MiB | 2021-08-07 |

**넷 다 Intel HEX 로 온전해 — 체크섬 오류 0건** [확정]. 레코드 구성은 확장선형주소(형 04) + 데이터(형 00) + EOF(형 01) 셋뿐이야.

⭐ driver 와 hvxbias 는 **크기가 같고 md5 는 다르고, 레코드 개수와 주소 범위(0x0~0x71544)까지 정확히 같아** [확정]. **같은 FPGA 부품 · 같은 빌드 도구라 이미지 길이가 같고 내용만 다른 거야** — 앞서 [추정] 이었던 걸 레코드 수·주소 범위 대조로 [유력] 로 올렸어.

백플레인 둘의 주소 범위는 달라 [확정]: **1252 는 0x0~0x8682A0**, **1271 은 0x0~0xA21048** 이야. 1271 이 주소 범위는 더 넓은데 펼친 바이트는 더 적어(6.07 vs 6.79 MiB) — **비트스트림이 더 성기게 배치됐다는 뜻**이야. 둘 다 X12 백플레인 FW 영역 8 MiB(섹터 0–127) 안에 들어가.

> 단위 주의: 다른 세션이 DevNote 8.11 에서 적은 "압축 해제 후 7.1 MB" 는 **십진 MB** 야 (7,119,232 B). 위 표의 6.79 MiB 와 같은 값이고 모순이 아니야.

### 10.1.1 ⭐ FW 1252 ↔ 1271 명령표 대조 (2026-09-03 신규)

두 백플레인 이미지를 펼쳐(형 00 레코드만 모아 `unhexlify`) ASCII 구간을 뽑고 명령 디스패치 표를 대조했어 [확정].

| 토큰 | 1252 (Rev F) | 1271 (Rev H) | 판정 |
|---|---|---|---|
| **`LOCKT`** | 있음 (1건, 널종단) | **0건** | ⭐ **1271 에서 빠졌어** |
| **`FASTAUTOFETCH`** | **0건** | 있음 (1건, 널종단) | ⭐ **1271 에 새로 생겼어** |
| `AUTOFETCH` | 있음 (`<SFAUTOFETCH=%d`) | 있음 (`@<SFAUTOFETCH=%d`) | 양쪽 유지 |
| `LOCKNEWEST` | 0건 | 0건 | ⭐ FW 명령이 아님이 **재확인**됐어 |

1271 표 순서 (`FETCHLOG` 다음부터):

```
SYSTEM STATUS TIMER FRAME FETCHLOG LOCK VERIFYMOD ERASEMOD FLASHMOD
FLASHACTIVECONFIG ERASESTOREDCONFIG ERASE FLASH VERIFY AUTOFETCH FASTAUTOFETCH
WCONFIG RCONFIG CLEARCONFIG APPLYNET POWEROFF POLLON POLLOFF BIASPOLLON
BIASPOLLOFF LOADTIMING LOADPARAMS RESETTIMING HOLDTIMING RELEASETIMING
APPLYMOD APPLYDIO APPLYSYSTEM APPLYCDS ATLASMOVE CLEARAD CALAD WARMBOOT REBOOT
```

⚠️ **"문자열이 없다" 를 "명령이 없다" 로 곧장 읽으면 안 돼** — 좋은 반례가 같은 자료 안에 있어. `FETCH` 는 1271 에서 **독립 문자열로 0건**인데, 이건 링커가 `AUTOFETCH`/`FASTAUTOFETCH` 의 **꼬리로 공유**해 버려서야(널종단 검색으로는 2건 잡혀). `FETCH` 가 사라졌을 리는 없어 — GUI 가 그걸로 실기에서 프레임을 받고 있으니까.
그래서 `LOCKT` 판정에도 같은 유보가 붙어: `LOCKT` 는 다른 토큰의 꼬리가 될 수 없고(`LOCK` 은 접두라 공유가 안 돼) 널종단 검색에서도 0건이라 **[유력]** 이지만, 빌드마다 문자열 풀 방식이 달라질 수 있어서 **[확정] 은 아니야.**

이게 뜻하는 것:

- 다른 세션의 미결 *"`LOCKT`·`AUTOFETCH` 가 1261 에도 있나"* 에 **부분적으로 답이 나왔어.** 1261 은 여전히 없지만, 그보다 새 판인 **1271 에서는 `LOCKT` 이 없고 `FASTAUTOFETCH` 가 생겼어.**
- `FASTAUTOFETCH` 는 **매뉴얼에도, 벤더 GUI 소스에도 없어** [확정]. 이름만 보면 자동 송출의 빠른 판인데 **뜻은 몰라.**
- ⚠️ **STA 문의 목록에 `FASTAUTOFETCH` 를 추가해야 해.** 그리고 `LOCKT` 은 "1252 에 있다가 1271 에서 없어진 명령" 이라는 이력까지 같이 물어보면 좋아.
- ⚠️ **셋 다 때려보지 마.** 자동 송출 계열이면 링크에 프레임이 쏟아지거나 상태가 바뀔 수 있어.

## 10.2 `.mcs` 파싱 — `readMCS()`

`archon.cpp:683~743` [확정]:

1. **`ba.fill(0xFF, flash_size)`** — 지워진 플래시 기본값이 0xFF 라 안 쓴 영역은 자동으로 "빈 줄" 취급
2. 줄마다: `:` 로 시작 안 하면 **조용히 건너뜀**
3. **레코드 타입 00 (Data)**: `addr += segaddr`, `addr+len > flash_size` 면 `"File too large"`, 아니면 2자리씩 잘라 기록
4. **레코드 타입 04 (Extended Linear Address)**: `segaddr = (앞 4자리 16진) << 16`
5. **그 밖(01 EOF, 02, 03, 05)은 전부 무시**

⚠️ **체크섬을 전혀 검증하지 않아.** 각 줄 끝의 체크섬 바이트를 읽지도 않아. 손상된 MCS 를 그대로 굽고, 잡히는 건 그 뒤의 `verify()` 단계에서야 [확정].

## 10.3 플래시 크기와 영역

**백플레인** (`archon.cpp:761~787`) — `BACKPLANE_TYPE` 으로 갈라져. 섹터는 65536 B 고정 [확정].

| | X12 (`TYPE=1`) — **우리 실기** | X16 (`TYPE=2`) |
|---|---|---|
| `flash_size` | **16 MiB** | 32 MiB |
| `sectors` | 256 | 512 |
| FW 영역 | 섹터 0–127 → `0x000000`–`0x7FFFFF` (8 MiB) | 섹터 0–255 (16 MiB) |
| Code 영역 | 섹터 128–191 → `0x800000`–`0xBFFFFF` (4 MiB) | 섹터 256–319 |
| (틈) | 없음 | 섹터 320–383 **건너뜀** |
| Config 영역 | 섹터 192–255 → `0xC00000`–`0xFFFFFF` (4 MiB) | 섹터 384–447 |
| `FLASH` 주소 | `hex(addr>>8, 4)` — **4자리** | `hex(addr, 8)` — **8자리** |

X12 의 "block address" 는 **바이트 주소를 256 으로 나눈 값**이야. 1024바이트 줄 하나당 4씩 증가해. **2021 매뉴얼은 4자리 형식만 문서화하고 X16 8자리 변형은 없어** [확정].

**모듈** (`flashMod` `:1042~1074`, `verifyMod` `:1173~1196`) — `MOD<n>_TYPE` 으로 갈라져 [확정]:

| 모듈 형 | `flash_size` |
|---|---|
| 기본 (DRIVER, AD, LVBIAS, HVBIAS, HEATER, ATLAS, HS, HVXBIAS, HVYBIAS, LVXBIAS, LVDS, HEATERX, XVBIAS, ADF, ADLN, DRIVERX) | **1 MiB** |
| **`MOD_TYPE_ADM` (17)** | **4 MiB** |
| **`MOD_TYPE_ADX` (14)** | **8 MiB** |

즉 우리 science 는 슬롯 5·8 만 4 MiB, 나머지는 1 MiB 야. 모듈 `FLASHMOD` 주소는 **항상 4자리** — 최대 8 MiB 라 `>>8` 하면 0x8000 까지고 4자리로 충분해.

## 10.4 ⭐ 파일명 검증 규칙과 REV ↔ Rev 문자 대응

플래시 전에 **파일명 접두를 반드시 맞춰봐** [확정]:

```
백플레인: "archonbackplane" [+ "x16" if X16] + "rev" + ('a' + BACKPLANE_REV)
모듈:     "archon" + <형별 기본이름> + "rev" + ('a' + MOD<n>_REV)
```

형별 기본 이름은 `archondriver`, `archondriverx`, `archonad`, `archonadf`, `archonadln`, **`archonadm`**, `archonadx`, `archonlvbias`, `archonhvbias`, `archonheater`, `archonatlas`, `archonhs`, `archonhvxbias`, `archonhvybias`, `archonlvxbias`, `archonlvds`, `archonheaterx`, `archonxvbias` 야.

**REV 숫자 ↔ Rev 문자 대응** (`'A' + n`) [확정]:

| REV 숫자 | 0 | 1 | 2 | 3 | 4 | **5** | 6 | **7** | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rev 문자 | A | B | C | D | E | **F** | G | **H** | I | J | K |

실기 대조 [확정]:

| 대상 | `_REV` | Rev 문자 | 기대 파일명 접두 | 보유 여부 |
|---|---:|---|---|---|
| 백플레인 (113) | 5 | **F** | `archonbackplanerevf` | ✅ `archonbackplanerevf_1_0_1252.mcs` — **판번까지 일치** |
| 백플레인 (101) | **7** | **H** | `archonbackplanerevh` | ⭐ ✅ `archonbackplanerevh_1_0_1271.mcs` (2026-09-03 반입) — **Rev 는 맞고 판번은 더 새것**(실기 1261 < 1271) |
| Driver | 3 | D | `archondriverrevd` | ✅ `archondriverrevd_1_0_1175.mcs` |
| HVXBias | 0 | A | `archonhvxbiasreva` | ✅ `archonhvxbiasreva_1_0_1175.mcs` |
| ADM | 1 | B | `archonadmrevb` | ❌ **없어** |
| LVXBias · LVDS | — | — | — | ❌ 없어 |
| guide 의 AD | 10 | K | `archonadrevk` | ❌ 없어 |

> ⚠️ **이미지는 유닛의 Rev 에 맞는 것만 써.** `archonbackplanerevf_…` 는 113(Rev F)용, `archonbackplanerevh_…` 는 101(Rev H)용이야. 서로 바꿔 쓰면 **파일명 검증에서 걸려서 아예 못 굽고**, 억지로 굽는 것도 안 돼 [확정].
>
> ⭐ **2026-09-03 갱신 — 101 용 이미지가 생겼어.** 다만 **판번이 실기와 달라**: 101 에 올라가 있는 건 **1.0.1261** 인데 받은 이미지는 **1.0.1271** 이야. 즉 이건 *복구용 같은 판*이 아니라 **판올림(upgrade)** 이야.
> ⚠️ **굽기 전에 판올림 여부를 운영자가 결정해야 해.** 1271 은 1261 과 명령표가 다르고(`LOCKT` 제거 · `FASTAUTOFETCH` 추가, §10.1.1), 그 차이가 우리 ICS 나 벤더 GUI 에 어떤 영향을 주는지 **아직 확인 못 했어** [실측대상]. 굽는 순간 되돌릴 이미지(1261)가 우리에게 없다는 것도 같이 봐야 해.
>
> 그리고 **ADM 펌웨어 `.mcs` 가 없어** — 우리 science 비디오 모듈 두 장이 바로 그건데.

## 10.5 플래시 절차

`flash()` (`archon.cpp:746~897`) [확정]:

```
1. 파일명 접두 검증
2. readMCS()  (체크섬 미검증)
3. BIASPOLLOFF
4. 섹터 소거: ERASE + hex(i*0x10000,8) + "00010000"   ← 타임아웃 3 s / 섹터
   진행 메시지 "Erasing PROM... (this can take up to 10 minutes)"
5. 1024 B 줄 단위 기록:
     · Abort 검사
     · 전부 0xFF 면 건너뜀      ← 소거 후 상태와 같아. FW 대부분이 빈 영역이라 시간을 크게 줄여
     · 선택 안 한 영역·틈 건너뜀
     · FLASH + 주소 + 2048자 16진 (명령 1줄이 2,061~2,065자)
6. verify() 자동 호출        ← 플래시는 항상 검증까지 해
7. BIASPOLLON 복구
```

`verify()` 는 `group_size = 256` 이라 한 그룹이 **256블록 × 1024 B = 256 KiB** 야. `VERIFY` 명령 한 번에 256블록이 흘러나오고 매 블록마다 같은 `last_msgref` 로 프리앰블을 대조해.

모듈 쪽은 좀 달라 — 소거가 **`ERASEMOD` 한 번에 모듈 전체**(타임아웃 **200,000 ms**)고, 검증 그룹이 16블록 = 16 KiB 야.

⚠️ **비대칭 하나**: `flashMod` 는 0xFF 줄 건너뛰기를 하는데 **`verifyMod` 는 건너뛰기 없이 전 영역을 다 읽어.** ADX 8 MiB 모듈이면 8192블록을 전부 받아. 백플레인 `verify()` 는 영역 건너뛰기가 있는데 모듈 쪽만 없어 [확정].

⚠️ **Reboot · Erase Stored Config · Flash 계열에 확인 대화상자가 하나도 없어.** 메뉴를 잘못 누르면 곧장 실행돼. 게다가 `sPROMFilename` 기본값이 **개발자 로컬 경로 `D:/Archon/RevC/...`** 로 박혀 있어(`archongui.cpp:39`) [확정].

`REBOOT` vs `WARMBOOT` 차이 (매뉴얼 p.51) [확정]:

| | `REBOOT` | `WARMBOOT` |
|---|---|---|
| 대상 | 백플레인 + **모든 모듈 FPGA** 가 설정 메모리에서 펌웨어 재로드 | **백플레인 프로세서만** 재시작 |
| FPGA 펌웨어 재로드 | ✅ | ❌ |
| 연결 | 끊김 | 끊김 |
| `BUFnFRAME` 리셋 | ✅ [실측] | ❌ (프레임 번호가 이어져) [실측] |

`reboot`/`warmboot` 가 반환값을 무시하는 건 합리적이야 — 컨트롤러가 응답을 주기 전에 링크를 끊으니 타임아웃이 정상 동작이거든. 반면 **`flashactiveconfig`/`erasestoredconfig` 가 반환값을 무시하는 건 설계 결함으로 보여** — 저장 실패가 GUI 에 전혀 안 알려져(로그 창에만 떠) [확정].

## 10.6 빌드 환경

### 프로젝트 파일 — 3판 동일

`archongui.pro` 는 **세 판이 완전히 같아** [확정]:

```
TEMPLATE = app
TARGET   = archongui
QT      += core widgets network concurrent svg
CONFIG  += debug_and_release
HEADERS += $$files(src/*.h)      SOURCES += $$files(src/*.cpp)
DEFINES += QWT_MOC_INCLUDE=1
HEADERS += $$files(src/qwt/*.h)  SOURCES += $$files(src/qwt/*.cpp)
INCLUDEPATH += src/qwt
win32 { LIBS += -lws2_32 }
```

`$$files(...)` 글롭이라 **파일을 추가하면 자동으로 잡혀.** 그리고 **qwt 를 외부 라이브러리로 링크하지 않고 소스째 동봉해서 같이 컴파일해** — 배포 의존성을 줄이려는 선택이야.

`readme.txt` 는 **Qt 5.2 기준**이라고 적혀 있어 [확정] — "Archon GUI is tested using Qt 5.2".

### 두 개의 서로 다른 빌드 환경

| | STA/KMTNet 편집 환경 | SSO 빌드 환경 |
|---|---|---|
| 출처 | `archongui.pro.user` | `Makefile.Release`, `.qmake.stash` |
| OS | **Windows** | **Linux** |
| Qt | **5.3, MinGW 32bit** 킷 | **5.15.13** (`/usr/lib/qt5/bin/qmake`, qmake 3.1) |
| 컴파일러 | MinGW g++ | **g++ 13.3.0**, C++ 표준 `201703L` |
| 작업 경로 | `C:/Users/kmtnet/Downloads/archongui (2)/` | `/home/rtkmtnet/SMC/archongui_v1.0.1259.KMTNet_20250827/` |
| 도구 | **QtCreator 3.2.1**, 기록 시각 `2025-08-27T04:54:11` | qmake + make |
| 산출물 | 없음(소스만) | `release/archongui` |

SSO 빌드 플래그 [확정]:

```
CXXFLAGS = -pipe -O2 -Wall -Wextra -D_REENTRANT -fPIC
DEFINES  = -DQWT_MOC_INCLUDE=1 -DQT_NO_DEBUG -DQT_SVG_LIB -DQT_WIDGETS_LIB
           -DQT_GUI_LIB -DQT_NETWORK_LIB -DQT_CONCURRENT_LIB -DQT_CORE_LIB
LFLAGS   = -Wl,-O1
LIBS     = libQt5Svg libQt5Widgets libQt5Gui libQt5Network libQt5Concurrent libQt5Core -lGL -lpthread
TARGET   = release/archongui
```

> ⭐ **정황 정리**: 개조는 2025-08-27 에 **윈도우에서 Qt Creator 3.2.1(Qt 5.3 MinGW 킷)로** 이뤄졌고, 그 트리를 SSO 리눅스로 옮겨 **2026-01-18 에 Qt 5.15 / g++ 13 으로 빌드**했어. `.pro.user` 의 md5 가 두 KMTNet 사본에서 같으니 SSO 사본은 편집을 더 하지 않은 순수 복사본이야 [확정].
>
> Qt 5.2~5.3 을 상정한 코드를 Qt 5.15 / C++17 / g++ 13 으로 빌드한 거라 **경고가 상당히 났을 가능성이 높은데, 빌드 로그가 없어서 [확인불가]** 야. 재빌드할 일이 생기면 로그를 남겨두는 게 좋아.

### 판 호환성

| 조합 | 판정 |
|---|---|
| stock GUI ↔ 실기 (FW 1252/1261) | 문제없어. `RAWSEL≤15` 라 개조 유무가 차이를 안 만들어 [확정] |
| KMTNet GUI ↔ 실기 | 현행 ACF 로는 stock 과 **완전히 동일하게 동작** [확정] |
| GUI 1.0.1259 ↔ FW 1.0.1252 (113) | 위젯 게이팅이 `build`/`rev` 로 걸려서 정합. `REV=5`·`build=1252` 면 **External Clock 체크박스와 Trigger Out Power 가 숨겨지고** 나머지는 다 보여 [확정] |
| GUI 1.0.1259 ↔ FW 1.0.1261 (101) | **[확인불가]** — 101 의 `SYSTEM` 응답을 GUI 로 받아본 기록이 없어. 게이팅 임계값(1042/1179/930/1028/1046/1049/1063/1064/833/1090) 이 전부 1261 미만이라 **기능이 더 열릴 뿐 깨질 이유는 없어 보여** [유력] |
| ACF 를 GUI 로 왕복 | ⚠️ **무손실이 아니야.** §5.6 C3 참고 |
| `archonbackplanerevf_1_0_1252.mcs` ↔ 101 | ❌ **부적합.** 101 은 Rev H |

---

# 11. ics_archon 관점의 시사점

세 갈래로 나눴어 — **벤더 코드가 확인해주는 것 / 우리가 놓쳤을 수 있는 것 / 고칠 것**.

## 11.1 ✅ 확인해주는 것 — 우리가 맞았어

| # | 항목 | 벤더 코드의 증언 | 등급 |
|---|---|---|---|
| A1 | **`data_bytes` 산식** | `frame_size = (samplemode ? 4 : 2) * framew * frameh` (`archon.cpp:1282~1284`). 우리 `parse.py:113` 의 `data_bytes = (4 if samplemode else 2) * width * height` 와 **완전히 같아** | [확정] |
| A2 | **raw 를 안 읽는 게 정상** | raw 는 이미지 fetch 에 안 섞이고 `baseaddr + BUFnRAWOFFSET` 에서 **별도 2차 `FETCH`** 야(`:1361~1364`). 크기도 `BUFnRAWBLOCKS × BUFnRAWLINES × 2048` 로 따로 계산해. 실기 ACF 가 `RAWENABLE=1` 인데 우리가 raw 를 안 읽는 건 **결함이 아니야** | [확정] |
| A3 | **`LOCK`→`FETCH`→`LOCK0` 루프** | 벤더 GUI 가 매 프레임 똑같이 해(`archongui.cpp:1831`, `archon.cpp:1386`). 우리 ICS 와 알고리즘이 같아 | [확정] |
| A4 | **`lock_buffer=true`** | `LOCK` 없이 fetch 하면 약 26% 확률로 두 노출이 섞여 | [실측] |
| A5 | **`BURST_LEN=1024`** · **`POWER_STATES` 0~5** | `archon.h:17`, `:52`. 우리 값과 양쪽 일치 | [확정] |
| A6 | **모듈 형 17=ADM · 18=HVYBias** | 우리가 ACF 실측으로 넣은 두 값을 `archon.h:46~47` 이 **확인**해줘 | [확정] |
| A7 | **`APPLYALL` 이 `POWERON` 의 전제** | 매뉴얼 p.51 + 실기 `?xx` 거부 | [실측] |
| A8 | **`RAW_BLOCK_SIZE=2048` = 1024 샘플** | `archon.h:20` + `setRawSize(rawblocks*2048/2, rawlines)`(`:1315`). 매뉴얼 p.70 "multiple of 1024" 와 자기정합적. science `RAWSAMPLES=8192` = 정확히 8블록 | [확정] |
| A9 | **키 표기 정규화** | 코드·프로토콜·매뉴얼은 전부 `/`, `.acf` 파일만 `\`. `\`→`/` 로 정규화하면 매뉴얼 p.57~63 표기와 그대로 대응돼 | [확정] |

## 11.2 ⚠️ 놓쳤을 수 있는 것 — 확인해봐야 해

| # | 항목 | 내용 | 우리 쪽 조치 |
|---|---|---|---|
| B1 | ⭐ **모듈 형 6 · 16** | `parse.py::MODULE_TYPES` 에 **6(ATLAS)이 아예 빠져 있고** 16 을 "모른다" 로 뒀어. `archon.h` 정본은 **6=ATLAS, 16=DRIVERX** 야. 둘 다 지금 닫을 수 있어 | 표에 추가 |
| B2 | ⭐ **raw 2차 fetch 경로** | raw 를 읽고 싶으면 이미지 fetch 뒤에 `FETCH<baseaddr+RAWOFFSET><lines>` 를 한 번 더 내면 돼. `RAWENABLE=1` 로 운영 중이니 **언제든 켤 수 있는 기능**이야. 지금 안 읽는 건 결함이 아니지만, **쓰려면 코드를 추가해야 해** | 필요 시 구현. 크기 = `BUFnRAWBLOCKS × BUFnRAWLINES × 2048`, 폭 = `BUFnRAWBLOCKS × 1024` 샘플, 항상 16bit |
| B3 | ⭐ **`LOCKT` / `AUTOFETCH` / `FASTAUTOFETCH`** | FW 1252 표에는 `LOCKT`·`AUTOFETCH` 가 있는데(다른 세션 발견) **벤더 GUI 소스에는 0건**이야 — STA 자기 클라이언트도 안 써. ⭐ **1271 에서는 `LOCKT` 이 빠지고 `FASTAUTOFETCH` 가 생겼어**(§10.1.1). ⚠️ **셋 다 때려보지 마.** GUI 의 "Auto Fetch" 체크박스는 이 명령들과 **무관해** — GUI 가 `LOCK`+`FETCH` 를 스스로 반복하는 것뿐이야 | STA 문의에 첨부 |
| B4 | ⭐ **폴링 버려짐** | `command()` 는 바쁘면 **큐에 안 쌓고 거절**(`archon.cpp:187`). 그래서 FETCH 동안 `FRAME` 응답이 한 번도 안 와 — GUI 가 얼어붙어 보이는 착시의 기전이야. **우리 ICS 는 이걸 흉내내면 안 돼.** 상태 폴링과 데이터 fetch 를 분리하거나, 최소한 "폴이 밀렸다" 를 로그로 남겨야 해 | 설계 반영 |
| B5 | ⭐ **`APPLYALL` 전제** | `APPLYALL` **끝나면 CCD 전원이 꺼진 상태**가 돼(p.51). 그래서 `APPLYALL` → `POWERON` 을 반드시 이어서 해야 해. 그리고 `RESETTIMING`/`HOLDTIMING`/`POWERON` 같은 명령은 `writeConfig()` 를 **안 부르니까**, 설정을 바꾸고 이것들만 내면 **아무 효과 없어** | 절차 규정 |
| B6 | **부분 적용이란 게 없어** | 벤더는 어느 Apply 든 `CLEARCONFIG` + 전체 재전송이야. 우리가 "슬롯 하나만 갱신" 을 하고 싶다면 **GUI 동작을 따라하지 말고 프로토콜 수준에서 따로 설계**해야 해 | 설계 판단 |
| B7 | **`VALID` 게이트** | 매뉴얼 p.47 은 `VALID=0` 이면 나머지 STATUS 가 전부 무효라고 규정하는데 **GUI 는 게이트로 안 써.** 우리는 `VALID=1` 일 때만 채택하도록 규정하고, `COUNT` 로 신선도까지 봐야 해 | 규정 |
| B8 | **단위 4종** | 시스템 레일 전류 **A** / 모듈 바이어스 전류 **mA** / 백플레인·모듈 온도 **℃** / **히터 센서 온도 K** (설정 target·limit 은 ℃). 섞으면 안 돼 | 변환 명시 |
| B9 | **`POWER` ≠ `POWERGOOD`** | `POWER` 는 CCD 전원, `POWERGOOD` 은 컨트롤러 공급전원. 그리고 `POWERGOOD=1` 은 **"감시하도록 켜둔 레일만" 정상**이라는 뜻이야. 레일별 `_V` 를 p.41 범위와 따로 대조하는 이중 확인이 필요하고, **안 쓰는 레일(N35V·USER·P100V·N100V)은 알람에서 빼야 해** | 알람 설계 |
| B10 | **Rev F 동시 접속 1개** | 113(Rev F)은 ICS 와 GUI 가 **동시에 못 붙어**. 101(Rev H)은 4개까지. 운영 절차에 명시 | 문서화 |
| B11 | **인식 못 한 명령 = 무응답** | 오타 명령은 `?` 조차 안 와. **타임아웃이 없으면 그냥 멈춰.** 통신 계층 규약에 규정해둬야 해 | 규정 |
| B12 | **TAPLINE 산식으로 슬롯 역산** | FITS 헤더에 채널→슬롯→물리 앰프를 기록할 때 쓰면 돼 — ADM 은 `slot = 5 + (ch-1)/18`, AD 는 `slot = 5 + (ch-1)/4` | 헤더 작성 |
| B13 | **SHP/SHD 8의 배수** | ADM 은 12.5 MHz 샘플을 8회 복제(디더링)하니까 8의 배수가 권고야(p.69). science ACF 는 이미 지키고 있어(72/112/136/200) — **바꿀 때 깨뜨리지 않게 규정해둬야 해** | 검증 규칙 추가 |
| B14 | **바이트 순서** | 매뉴얼 무언급. GUI 는 소켓 바이트를 `unsigned short*` 버퍼에 **그대로 복사**하고 변환 코드가 없어 → **호스트 네이티브(x86 리틀엔디언 uint16)** | [유력]. 우리도 같게 |

## 11.3 🔧 고칠 것 / 흉내내지 말 것

| # | 항목 | 벤더 결함 | 우리가 할 것 |
|---|---|---|---|
| C1 | **`RAWSEL` 왕복** | `qBound(0,…,15)` 가 16 이상을 조용히 깎아(`archongui.cpp:2568`) | 우리 파서는 **깎지 말고 원값 보존**. 값 검증은 별도 경고로 |
| C2 | **`VCPU_INREG` off-by-one** | 쓰기 0기점 / 읽기 1기점, **5개 클래스 전부** | 우리는 **0기점으로 통일**. 다만 컨트롤러 기대값은 [실측대상] |
| C3 | **모르는 키 유실** | `parseUI()` 가 `config.clear()` 후 위젯에서 재구성 → GUI 가 모르는 키가 전부 사라져 | 우리는 **원본 키를 보존하고 아는 키만 덮어쓰기** |
| C4 | **`PWR_STANDBY` early return** | STANDBY 면 온도·전압·모듈 상태 갱신이 통째로 멈춰 | 절대 흉내내지 마. STANDBY 도 나머지를 정상 갱신 |
| C5 | **`CONFIG` 가 결과를 갱신 안 함** | `setConfig` 뒤 `getResult()` 가 **직전 명령의 결과**를 반환 → `APPLYxxx` 가 조용히 건너뛰어질 수 있어 | 우리 명령 계층은 **명령마다 결과를 짝지어 돌려주기** |
| C6 | **재시도 없음** | 타임아웃 한 번에 즉시 실패 | 재시도 정책을 명시적으로 정하기(다만 부작용 있는 명령은 재시도 금지) |
| C7 | **MCS 체크섬 미검증** | 손상된 이미지를 그대로 구워 | 우리가 플래시를 다룰 일이 생기면 **체크섬 먼저 검증** |
| C8 | **확인 대화상자 없음** | Reboot·Erase Stored Config·Flash 가 곧장 실행돼 | 파괴적 명령은 **2단 확인** |
| C9 | **`ptc.txt`/`hplot.txt` 고정 이름 + `%0.0lf`** | 현재 작업 디렉터리 덮어쓰기, 평균값 소수점 소실 | 우리 산출물은 경로 지정 + 충분한 자릿수 |
| C10 | **FITS 헤더 7개뿐** | 노출시간·온도·탭 구성 아무것도 없어 | **KMTNet raw spec 헤더는 전적으로 ICS 몫**이야. GUI FITS 를 참고하면 안 돼 |
| C11 | **`WCONFIG` 키 순서** | `QMap` 사전순이라 ACF 원본 순서와 달라 | FW 가 키 이름으로 파싱하니 문제는 없지만, `RCONFIG` 되읽기 비교 시 순서를 기대하면 안 돼 |
| C12 | **부분 실패 복구 없음** | `writeConfig` 중간 실패 시 설정 메모리가 반쯤 지워진 채 남아 | 우리는 실패 시 **상태를 로그로 남기고 재적용을 강제** |

---

# 12. 다른 세션 결과와의 관계

⚠️ **`ics-archon-v1.0-build` 세션이 같은 GUI 소스를 이미 읽었어.** 아래 왼쪽 칸은 **그쪽 공로**야. 출처: `ics_archon/DevNote.md` 8.2갱신 · 8.10 · 8.11 · 10장, `ics_archon/archon_lock_fetch_report.md`.

## 12.1 그쪽이 이미 낸 것 (인용)

| 그쪽 발견 | 근거 자리 | 출처 |
|---|---|---|
| 벤더 GUI 가 **매 프레임 `LOCK`→`FETCH`→`LOCK0`** 을 한다 | `archongui.cpp:1831` · `archon.cpp:1386` | DevNote 8.2 |
| Auto Fetch 를 켜면 Exposures=N 연속 취득에서 완료 버퍼마다 자동으로 그 절차 | `archongui.cpp:288` · `:2408` | DevNote 8.2 |
| → **우리 ICS 루프와 알고리즘이 같다.** "LOCK 이 fetch 를 방해한다"(H1) 가 죽었다 | | DevNote 8.2 갱신 |
| `Archon` 은 **소켓 하나 + 워커 하나**, 명령 동시 하나 | `archon.cpp:59` | DevNote |
| 화면 갱신 타이머가 `STATUS`→`FRAME` 을 번갈아 낸다 | `archongui.cpp:2833 poll()` | DevNote |
| ⭐ `command()` 는 `CommandInProgress` 면 **큐에 안 쌓고 거절**(return 1) → 그 폴은 버려진다 | `archon.cpp:187` | DevNote 8.10 |
| → **FETCH 동안 `FRAME` 응답이 한 번도 안 온다** = 화면이 얼어붙는다(착시의 기전) | | DevNote 8.10 |
| `LOCKNEWEST` 는 **GUI 내부 편의 이름**, 결국 "LOCK"+(buf+1) 을 보낸다. FW 명령표에 없다 | `archon.cpp:673` | DevNote |
| 실기 종결: FETCH 중에도 엔진은 **368.0 행/초 만속**. "정지" 는 표시 착시 (라인 10→1500 점프, 1490÷368=4.05초) | | `archon_lock_fetch_report.md` |
| `LOCKn` 은 FW 에 매번 반영(15/15). fetch 를 느리게도 엔진을 멈추게도 안 한다 | | 〃 |
| `LOCK` 없이 fetch 하면 **약 26% 확률**로 두 노출이 섞인다 → `lock_buffer=true` 종결 | | 〃 |
| `POWERON` 의 전제는 **`APPLYALL`**. 안 했으면 `?xx` 거부 | 매뉴얼 p.51 | 〃 |
| `BUFnFRAME` 리셋은 **`REBOOT` 만.** `WARMBOOT`·CCD `POWEROFF/ON` 은 이어진다 | | 〃 |
| 실측: 4700행 12.77초 · 프레임 주기 13.27초 · FETCH 344.2 MiB 3.2~3.5초(약 100 MiB/s) | | 〃 |
| 유닛 차이: **KMTC-SCI-101 = FW 1.0.1261 / REV 7** · **KMTK-SCI-113 = FW 1.0.1252 / REV 5** | | 〃 |
| FW 1252 이미지에서 **매뉴얼에 없는 명령 둘: `LOCKT` · `AUTOFETCH`** 발견 (`<SFAUTOFETCH=%d` 문자열도). 방법은 Intel HEX 타입 00 만 모아 unhexlify → `[ -~]{4,}` ASCII 추출, 압축 해제 후 7.1 MB | | DevNote 8.11 |

## 12.2 이 보고서가 새로 보탠 것

| # | 새로 보탠 것 | 성격 | 근거 |
|---|---|---|---|
| N1 | ⭐ **`LOCKT`·`AUTOFETCH` 는 벤더 GUI 소스에도 0건.** STA 자기 클라이언트도 안 써. GUI 의 "Auto Fetch" 체크박스는 와이어 명령 `AUTOFETCH` 와 **무관** | 그쪽 미결(STA 문의)에 **결정적 보강** | `grep -rn "LOCKT\|AUTOFETCH" src/*.cpp src/*.h` → 0건 |
| N7 | ⭐ **FW 1252 ↔ 1271 명령표 대조** — 1271 에서 **`LOCKT` 제거 · `FASTAUTOFETCH` 신설**. `LOCKNEWEST` 는 양쪽 0건이라 **"FW 명령이 아니다" 가 재확인**됐어. 그리고 `FETCH` 가 1271 에서 독립 문자열로 안 잡히는 것이 **"문자열 부재 ≠ 명령 삭제" 의 반례** | 그쪽 미결 V7("1261 에도 있나")에 **부분 답** + 문의 항목 하나 추가 | §10.1.1 |
| N2 | ⭐⭐ **raw 는 이미지 fetch 크기에 안 섞여. `data_bytes` 는 옳고, raw 는 별도 2차 fetch** | **결함 의심 해소** | `archon.cpp:1282~1289`, `:1361~1364` |
| N3 | ⭐⭐ **raw 채널 개조의 진상 전모** — 매뉴얼 정의, `currentIndex()` 증거, 36 밀림 산식, 왕복 파손, 실사용 흔적 없음, 남은 유보 (A)/(B) | **완전히 새 층** | §2.2 전체 |
| N4 | ⭐ **모듈 형 번호 정본 0~19.** `parse.py::MODULE_TYPES` 의 **6 누락**과 **16 미상**을 둘 다 닫음 | **우리 코드 직접 수정거리** | `archon.h:29~48` |
| N5 | **REV 숫자 ↔ Rev 문자 대응 규칙**(`'A'+n`)과 플래시 파일명 검증 규칙. → `archonbackplanerevf_1_0_1252.mcs` 는 **113 전용**, 101(Rev H)용 이미지는 **없음**. ADM `.mcs` 도 없음 | **자산 재고 판정** | `archon.cpp:761~787`, `:1055~1100` |
| N6 | **`.mcs` 3종의 Intel HEX 레코드 수 대조** — driver 와 hvxbias 가 데이터 29,013 · EOF 1 · 확장주소 8 로 **완전히 같아** → "같은 부품·같은 도구" 를 [추정]에서 [유력]로 승급. 백플레인은 444,952 레코드 = **7,119,232 B** 로 DevNote 8.11 의 7.1 MB 와 일치 | 등급 승급 + 교차검증 | 직접 계산 |
| N7 | **개조 환경 특정** — `archongui.pro.user` 가 **QtCreator 3.2.1 / 2025-08-27T04:54:11 / Qt 5.3 MinGW 32bit / `C:/Users/kmtnet/Downloads/archongui (2)/`** 를 기록. 스페이스 들여쓰기 흔적과 앞뒤가 맞아 | **새 사실** | `.pro.user` 원문 |
| N8 | **SSO 빌드 환경 특정** — Qt 5.15.13 / g++ 13.3 / `-O2 -Wall -Wextra` / `DISTDIR=/home/rtkmtnet/SMC/archongui_v1.0.1259.KMTNet_20250827/` → SSO 사본이 20250827 트리의 빌드본임을 증명 | **새 사실** | `Makefile.Release`, `.qmake.stash` |
| N9 | **폴링 주기 정정** — 그쪽은 "5Hz 타이머" 라고 썼는데, **주석이 5Hz 일 뿐 실제는 500 ms = 2 Hz 틱**이고 교대라 **STATUS·FRAME 각각 1 Hz** 야 | **정정** | `archongui.cpp:1224~1227`, `updatetimer.cpp:34~41` |
| N10 | **모듈 체계 전층** — 클래스 15개 ↔ 형 18종 대응, 공유 클래스 3개, **ADM 이 빈 껍데기**, 설정 키 인덱스 규약, **펌웨어 빌드 게이팅이 키 집합을 바꾼다**, KMTNet science/guide 슬롯 대조 | **새 층** | §7 전체 |
| N11 | **설정 적용 계통** — `writeConfig` 의 6단 순서, **부분 적용이 없다**, 함수 사이 순서 의존성 6가지, 세 가지 키 표기(`/` `\` `_`)의 메커니즘 | **새 층** | §5 전체 |
| N12 | **영상·해석** — 통계 산식(모집단 N 나눗셈), `diffvar` 의 **2N 나눗셈**, **PTC 게인이 코드에 없다**, FITS 헤더 7개뿐, 플롯 txt 가 `%0.0lf` | **새 층** | §8 전체 |
| N13 | **전원·감시** — p.41 레일 범위표, **"7개냐 8개냐" 층위 정리**, `POWER` vs `POWERGOOD` 구분, **`PWR_STANDBY` early return 버그**, **GUI 가 `VALID` 를 게이트로 안 쓴다** | **새 층** | §9 전체 |
| N14 | **매뉴얼 어긋남 13건 + 11건 표** (§4.6, §10.6) — "매뉴얼 비권위" 원칙의 구체 증거 목록 | **새 층** | §4.6 |
| N15 | **결함 목록 40여 건** — C1~C6(설정), F1~F6(프레임), I1~I10(영상), M1~M9(모듈), D-계열(프로토콜). 특히 **`openHDRFrame` 뮤텍스 미해제 교착**과 **`VCPU_INREG` off-by-one** | **새 층** | 각 절 결함표 |

---

# 13. 미해결 · 다음에 볼 것

## 13.1 ⭐ 실측으로만 닫히는 것

| # | 항목 | 왜 코드로 못 닫나 | 실측 방법 | 우선순위 |
|---|---|---|---|---|
| **U1** | **`RAWSEL` 이 ADM 환경에서 전역 AM 번호(0~71)인가, 장착 모듈 순번(0~35)인가** | 산식이 GUI 에 0줄이고 매뉴얼은 AD 기준 0~15 만 규정해. **KMTNet 개조의 정오를 가르는 핵심** | science 에 `RAWENABLE=1`+`RAWSEL=54` 를 ACF 직접 편집으로 넣고 `APPLYCDS` → raw 파형이 슬롯 8 ADM 채널 1(AM55)인지 확인. 아니면 `RAWSEL=18` 로 반복. GUI 로는 클램프 때문에 입력 불가 | **최상** |
| **U2** | **FW 가 `RAWSEL ≥ 16` 을 받는가** | 매뉴얼 상한이 15 라 거부할 가능성이 남아 있어 | `WCONFIG` 로 직접 넣고 `APPLYCDS` → `?xx` 거부 여부, `FRAME` 의 `BUFnRAWBLOCKS` 정상 여부 | **최상** (U1 의 전제) |
| U3 | **ADM 의 슬롯당 채널 수가 정말 18인가** | 매뉴얼 p.70 이 규정하지만 **GUI 소스에는 ADM 채널 상수가 아예 없어**. 우리 근거는 ACF 역산(슬롯5→1.., 슬롯8→55.. = 3칸에 54 차이) | ADM 채널 19~54 대역에 신호를 넣어 탭이 잡히는지 | 상 |
| U4 | **`VCPU_INREG` 를 컨트롤러가 0기점으로 기대하는가 1기점인가** | 매뉴얼에 VCPU `INREG` 항목 자체가 없어. `VCPU_LINE<j>` 가 0기점인 걸 보면 **0기점이 맞을 가능성이 높아** [유력] | VCPU 코드를 넣고 `INREG0` 에 값을 써서 반응 확인 | 중 (지금 VCPU 를 안 쓰면 잠복) |
| U5 | **`VALID=0` 일 때 나머지 필드에 뭐가 들어오나** | 매뉴얼이 안 적어놨어(직전 값 유지? 0? 쓰레기?) | `VALID=0` 을 만나는 순간의 STATUS 원문을 통째로 기록 | 중 |
| U6 | **`POLLON`/`POLLOFF` 와 `BIASPOLLON`/`BIASPOLLOFF` 의 정확한 의미 차이** | 넷 다 매뉴얼에 없어 | 각각 보내고 STATUS `COUNT` 증가 여부·바이어스 V/I 갱신 여부 비교 | 중 |
| U7 | **`LOCKT` / `AUTOFETCH` / `FASTAUTOFETCH` 의 의미** | FW 이미지 문자열에만 있고 매뉴얼·GUI 어디에도 없어. `LOCKT` 은 1252 에 있다가 **1271 에서 사라졌고**, `FASTAUTOFETCH` 는 **1271 에 새로 생겼어**. ⚠️ **때려보지 마** | **STA 문의.** "벤더 GUI 도 안 쓴다" + 판별 이력을 근거로 첨부 | 중 |
| U8 | **101 유닛(Rev H / FW 1261)에서 GUI 1259 가 정상 동작하는가** | 101 의 `SYSTEM` 응답을 GUI 로 받아본 기록이 없어 | 101 에 GUI 를 붙여 모듈 탭이 정상 생성되는지, 게이팅으로 위젯이 더 열리는지 확인 | 중 |
| U9 | **ADM 에 clamp/gain 설정 수단이 있는가** | GUI 에 UI 도 설정 키도 없고 ACF 에도 0개. 정말 무설정인지 확인 못 했어 | STA 문의 또는 FW 이미지 문자열 조사 | 중 |
| U10 | **`ERASE` 3초 타임아웃이 실기에서 충분한가** | 다른 명령(5초)보다 짧아. 느린 PROM 을 만나면 걸릴 여지 | 플래시를 실제로 할 일이 생기면 관찰 | 하 |

## 13.2 자료로 못 가리는 것 (추가 자료가 필요해)

| # | 항목 | 필요한 것 |
|---|---|---|
| V1 | **stock 콤보 상한 32 의 출처** | 소스엔 맨 리터럴, 매뉴얼엔 16. "4슬롯×8채널" 은 [추정]. **더 최신 매뉴얼이나 릴리스 노트**가 필요해 |
| V2 | **ADF(13)·ADX(14)·ADLN(15) 의 채널 수** | 2021 매뉴얼에 하드웨어 장이 아예 없어. GUI 도 클램프 4칸만 알아 |
| V3 | **X16 백플레인의 슬롯 수·ADC 슬롯 위치** | 매뉴얼 전체에서 "X16" 은 p.46 한 줄뿐이야 |
| V4 | **guide 시스템의 `BACKPLANE_REV`/`VERSION`** | guide ACF 에 `ADXCDS`/`ADXRAW` 키가 없는 이유를 설명하는 값. **guide ACF `[SYSTEM]` 절만 받으면 즉시 닫혀** |
| V5 | ~~**101(Rev H)용 백플레인 `.mcs`**~~ | ✅ **해소(2026-09-03)** — `archonbackplanerevh_1_0_1271.mcs` 반입. ⚠️ 다만 **판번이 1271 이라 실기 1261 의 복구본이 아니라 판올림**이야(§10.4) |
| V6 | **ADM 모듈 `.mcs`** | 우리 science 비디오 모듈 두 장의 펌웨어 이미지가 없어 |
| V7 | **101 유닛이 지금 돌리는 FW 1261 이미지** | 여전히 없어. 보유는 1252·1271 둘이라 **1261 의 명령표는 직접 못 봐.** 다만 1252 와 1271 을 대조해 변화 방향은 잡았어(§10.1.1). 1261 은 그 사이 판이라 `LOCKT` 유무가 **[확인불가]** |
| V8 | **SSO 빌드 로그** | Qt 5.2~5.3 상정 코드를 Qt 5.15/C++17/g++13 으로 빌드한 거라 경고가 많았을 가능성. 재빌드 시 로그를 남겨두는 게 좋아 |
| V9 | **XVBias 양전압 상한** | 매뉴얼 내부 모순 — p.10·p.63 은 +95 V, p.33 은 +91 V. 실기 미사용이라 급하진 않아 |

## 13.3 우리 코드에 지금 바로 반영할 것

| # | 대상 | 조치 | 근거 |
|---|---|---|---|
| W1 | `ics_archon/archon/parse.py::MODULE_TYPES` | **6 = ATLAS** 추가, **16 = DRIVERX** 확정 | `archon.h:34`, `:45` |
| W2 | 같은 곳 | 17=ADM · 18=HVYBias 는 **확인 완료** — 주석에 "GUI `archon.h` 로 교차확인(2026-09-02)" 명기 | `archon.h:46~47` |
| W3 | `parse.py:113` `data_bytes` | **변경 불필요.** 벤더와 동일함을 확인했다는 주석만 추가 | `archon.cpp:1282~1284` |
| W4 | raw 미독출 | **결함 아님.** DevNote 에 "raw 는 별도 2차 fetch 라 이미지 크기와 무관" 을 기록 | `archon.cpp:1361~1364` |
| W5 | 통신 계층 문서 | **Rev F 동시 접속 1개** · **인식 못 한 명령은 무응답(타임아웃 필수)** 두 조항 추가 | 매뉴얼 p.15, p.45 |
| W6 | STATUS 처리 | **`VALID=1` 게이트** + `COUNT` 신선도 판정 규정 추가 | 매뉴얼 p.47, p.74 |
| W7 | 알람 설계 | `POWER`/`POWERGOOD` 분리, 레일별 p.41 범위 이중확인, **미사용 레일 제외** | 매뉴얼 p.41~43 |
| W8 | 단위 처리 | 시스템 레일 **A** / 모듈 바이어스 **mA** / 백플레인·모듈 온도 **℃** / 히터 센서 **K** | 매뉴얼 p.47~48, p.60~61 |
| W9 | ACF 파서 | `\` → `/` 정규화, **모르는 키 보존**, `RAWSEL` 원값 보존(깎지 않기) | §5.1, §5.6 C3 |
| W10 | ACF 검증 규칙 | ADM 슬롯이 있으면 **SHP/SHD 가 8의 배수인지 검사** | 매뉴얼 p.69 |
| W11 | STA 문의서 | `LOCKT`/`AUTOFETCH` 에 **"벤더 클라이언트도 안 쓴다"** 를 보태기 | §12.2 N1 |
| W12 | 자산 대장 | `archonbackplanerevf_1_0_1252.mcs` 는 **113 전용**이라고 명기. 101용·ADM용 이미지 부재를 기록 | §10.4 |

---

## 부록 — 이 보고서를 만든 자료

- 소스 3판 정독 결과 8건 (`scratchpad/wf2/read_*.md`) — 통신층 · GUI 골격 · 영상/플롯 · 모듈 계층 · 모듈 구현 · 보조 위젯 · 매뉴얼 프로토콜 · 매뉴얼 모듈
- 통합 지침서 (`scratchpad/synthesis_brief.md`) — raw 채널 결론 정정, 다른 세션 결과, 실기 ACF 실측, 판별 차이
- 빌드·펌웨어 절은 이 세션에서 **원문을 직접 확인**했어: `archongui.pro`, `readme.txt`, `.qmake.stash`, `Makefile`, `Makefile.Release`, `archongui.pro.user`, `ArchonFW/*.mcs` **4종** (크기·md5·Intel HEX 레코드 수·체크섬 전수 검증·1252↔1271 문자열 대조), `diff -r` 세 판 전수, `wc -l` 20개 파일, `grep` 검증 여러 건
- 실기 ACF 12종 + `acf_timing_script.txt` (`__reference/acf/`) — 탭·`RAWSEL`·기하 전수 대조, `for1110`↔`for1259` 키 단위 대조 (§5.7)
- 매뉴얼 전문 추출본 (`scratchpad/wf2/manual.txt`) 및 Readout Notes 추출본 (`scratchpad/wf2/notes.txt`)

`__reference/` 는 **읽기만 했고 어떤 파일도 편집·생성하지 않았어.**

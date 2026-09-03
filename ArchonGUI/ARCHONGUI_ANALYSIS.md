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
| 펌웨어 | `ArchonFW/` | `.mcs` **4종** (2026-09-03 에 Rev H 1271 이 추가되고 폴더명이 `ArchonFW_20250825` → `ArchonFW` 로 바뀌었다) |
| 실기 ACF | `__reference/acf/` | **13종** + 타이밍 스크립트 **2종**(science·guide) — **science 6 · guide 7**, 2026-09-03 확충. §5.7 |

줄번호는 별말 없으면 **SSO 트리 기준**이다. stock 은 두 곳 개조 때문에 뒤쪽 줄이 2씩 당겨져 있다(예: RAWSEL 저장은 SSO 2469 = stock 2467).

## 근거 등급 범례

| 표시 | 뜻 |
|---|---|
| **[확정]** | 원문을 직접 확인했다 — 소스 `파일:줄`, 매뉴얼 `p.NN`, 실기 ACF 값 |
| **[실측]** | 실기 벤치에서 측정으로 닫혔다 (2026-09-01~02 KASI) |
| **[유력]** | 강한 정황 + 반대 증거 없음. 다만 직접 원문 확인은 하지 못했다 |
| **[추정]** | 그럴듯한 해석일 뿐, 대안 해석이 살아 있다 |
| **[확인불가]** | 지금 가진 자료로는 가리지 못한다 |
| **[실측대상]** | 실기에 물어봐야만 닫히는 것 |

> 원칙 하나 먼저 명확히 해둔다. **매뉴얼은 정본이 아니다.** 판번이 1.0.1166(2021-02-23)인데 우리 실기 백플레인 FW 는 1.0.1252, GUI 는 1.0.1259 다. 90~100 빌드만큼 뒤처져 있고, 실제로 11군데가 어긋난다(§4.6, §10.6). 매뉴얼은 **구조를 이해하는 출처**로 쓰고, 값·범위·명령 목록의 판정은 소스와 실측으로 가야 한다.

---

# 1. 한눈에

가장 중요한 결론 아홉 개다.

| # | 결론 | 등급 | 근거 |
|---|---|---|---|
| 1 | **실질적인 판은 세 개가 아니라 둘이다.** KMTNet 과 SSO 는 `src/` 바이트가 완전히 같다(전 파일 diff 무소득). SSO 는 2026-01-18 에 리눅스에서 **빌드만 한 사본**이고, 차이는 `Makefile*`·`.qmake.stash` 뿐이다 | [확정] | `diff -rq` 무출력 |
| 2 | **stock → KMTNet 개조는 `archongui.cpp` 딱 두 곳.** ① 버전 문자열(`:55`) ② Raw Channel Select 콤보 라벨 목록(`:733~738`). 그 밖의 20개 파일·qwt 116개는 손대지 않았다 | [확정] | `diff -r src` 결과가 이 두 덩이뿐 |
| 3 | ⭐ **raw 채널 개조는 의도는 타당하나 구현이 틀렸다.** 라벨만 ADM 탭 번호로 바꾸고 값을 만드는 `currentIndex()` 는 그대로 두었다. 첫 블록(1~18)은 우연히 맞고, **둘째 블록(55~72)이 쓰는 18~35 는 어떤 해석으로도 슬롯 8 을 가리키지 못한다**(2차 검토에서 대안 해석이 반증됐다). 되읽기 `qBound(…,15)` 는 **FW 가 71 까지 받으므로 순수 GUI 결함**이다 | [확정](틀렸다는 것) / 올바른 값은 [실측대상] | `archongui.cpp:733~738` vs `:2469`·`:2568` · FW 0x59b7b4 |
| 4 | **벤더 GUI 도 매 프레임 `LOCK`→`FETCH`→`LOCK0` 을 한다.** 우리 ICS 루프와 알고리즘이 같다 — "LOCK 이 fetch 를 방해한다" 가설은 이미 죽었다 | [실측] | 다른 세션 결론 인용, §12 |
| 5 | ⭐ **raw 영역은 이미지 fetch 크기에 섞이지 않는다.** `frame_size = (samplemode?4:2)*w*h` 로 이미지를 받고, raw 는 `baseaddr+BUFnRAWOFFSET` 에서 **별도 2차 fetch** 다. 우리 `parse.py` 의 `data_bytes` 는 옳다 — 결함이 아니다 | [확정] | `archon.cpp:1282~1289`, `:1361~1364` |
| 6 | **`LOCKT`·`AUTOFETCH` 는 벤더 GUI 소스에도 없다.** `grep -rn "LOCKT\|AUTOFETCH" src/*.cpp src/*.h` → **0건**. GUI 의 "Auto Fetch" 는 체크박스 이름일 뿐이고 와이어 명령 `AUTOFETCH` 와 무관하다. ⭐ 그리고 새로 받은 **FW 1271 에는 `LOCKT` 이 없고 `FASTAUTOFETCH` 가 새로 생겼다**(§10.1.1) | [확정] / 1271 대조는 [유력] | grep · FW 이미지 문자열 대조 |
| 7 | **모듈 형 번호의 정본은 `archon.h` 의 0~19 다.** 매뉴얼 p.46 은 6(ATLAS)이 빠졌고 "16+: Unknown" 이라 우리 science 의 비디오 모듈 두 장(형 17 ADM)이 통째로 Unknown 으로 찍힌다 | [확정] | `archon.h:29~48` vs 매뉴얼 p.46 |
| 8 | ⭐ **펌웨어 판올림 1261→1271 은 ACF 문법을 바꾸지 않는다.** `[CONFIG]` 키 집합과 STATUS/SYSTEM/FRAME 응답 필드가 두 판 완전히 동일하다. 두 판의 차이 상당수는 판올림이 아니라 **CPU 교체**(MicroBlaze→AArch64)의 부산물이다 | [확정] | §10.7, FW 문자열 전수 대조 |
| 9 | **설정 적용에 "부분 갱신" 이란 것이 없다.** 어느 Apply 버튼을 눌러도 `POLLOFF`→`CLEARCONFIG`→`WCONFIG` 전체 재전송→`POLLON`→`APPLYxxx` 다. 슬롯 하나만 Apply 해도 수천 줄이 다시 올라간다 | [확정] | `archon.cpp:1406~1436` |

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

세 판의 `src/` 를 다 비교하면 이것이 전부다 [확정]:

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

개조된 줄은 원본의 **탭 들여쓰기 대신 스페이스**를 쓴다 — 편집 흔적이 그대로 남아 있다. 그리고 `archongui.pro.user` 를 열어보면 개조 환경까지 나온다 [확정]:

- `<!-- Written by QtCreator 3.2.1, 2025-08-27T04:54:11. -->`
- 킷 이름 `Desktop Qt 5.3 MinGW 32bit`
- 작업 경로 `C:/Users/kmtnet/Downloads/archongui (2)/archongui.pro`

즉 **윈도우 머신에서 `kmtnet` 계정이 Qt Creator 3.2.1 로 열어 고쳤다.** Qt Creator 기본 편집기가 스페이스 들여쓰기를 쓰므로 위 흔적과 앞뒤가 맞는다. 그런데 정작 SSO 빌드는 리눅스 Qt 5.15.13 / g++ 13.3 으로 했고, `Makefile.Release` 의 `DISTDIR` 이 `/home/rtkmtnet/SMC/archongui_v1.0.1259.KMTNet_20250827/...` 를 가리킨다 — **SSO 사본이 20250827 트리를 그대로 옮겨 빌드한 것**이라는 증거다 [확정].

## 2.2 ⭐ raw 채널 개조의 진상 (이 보고서의 핵심 절)

### (a) 매뉴얼이 규정한 것 — `RAWSEL` 의 정의

매뉴얼은 **두 군데**에서 `RAWSEL` 을 정의한다 [확정]:

> **p.56** — "RAWSEL — Select the AD channel for raw data capture, **from 0 to 15**."
>
> **p.70** — "Set the RAWSEL key to the desired AD channel (**0 for channel 1 of the ADC module in slot 5 through 15 for channel 4 of the ADC module in slot 8**)."

그리고 GUI 장에서 화면 라벨 규약도 못박는다 [확정]:

> **p.76** — "The Raw Channel Select field selects the raw capture channel. **1 - 4 selects a channel from the first ADC slot, 5 - 8 from the second ADC slot, etc.**"

세 문장을 합치면 규약은 다음과 같다.

- 비디오 슬롯은 **5·6·7·8 넷**. 물리적 제약이다 — p.20 이 "ADC modules can only be installed in the **central 4 slots (5-8)**, which have an additional connector that carries the high speed ADC data" 라고 적어놓았고, 그 J4 커넥터가 그 4칸에만 있다(Figure 10, p.21) [확정].
- 고전 AD 는 슬롯당 4채널 → 전역 채널 1~16, `RAWSEL` 은 그 **0기점**이라 0~15.
- 산식은 **슬롯 점유 여부와 무관한 고정 사상**이다. 슬롯 6·7 이 비어 있어도 번호가 당겨지지 않는다.

```
RAWSEL = (slot - 5) × 슬롯당채널수 + (channel - 1)          ← 0기점
탭 번호 = (slot - 5) × 슬롯당채널수 + channel                ← 1기점, TAPLINE 이 쓰는 번호
```

같은 p.70 이 TAPLINE 쪽 산식도 규정한다 [확정]:

> AD: "'tap' is a string of the form **ADnd**, where n is 1 to 16 … 1 for the first channel from an ADC module in backplane slot 5 … up to 16 for the fourth channel from an ADC module in backplane slot 8."
>
> ADM: "'tap' is of the form **AMnd**, where **n is 1 to 72** … **ADM channels 1 to 18 map to slot 5, channels 19 to 36 map to slot 6, and so on.**"

| 모듈형 | 슬롯당 채널 | 슬롯5 | 슬롯6 | 슬롯7 | 슬롯8 | 상한 | 접두 |
|---|---|---|---|---|---|---|---|
| AD (형 2) | 4 | 1–4 | 5–8 | 9–12 | 13–16 | 16 | `AD` |
| ADM (형 17) | 18 | **1–18** | 19–36 | 37–54 | **55–72** | 72 | `AM` |

실기 ACF 와 정확히 맞아떨어진다 [확정]: science 는 ADM 이 슬롯 5·8 → 탭 `AM1L`~`AM16R` + `AM55L`~`AM70R` (32탭). guide 는 AD 가 슬롯 5·6 → `AD1`~`AD8` (8탭).

### (b) 결정적 증거 — GUI 는 `currentIndex()` 를 값으로 쓴다

여기가 갈림길이다. 콤보박스에 채운 숫자는 **라벨일 뿐**이고, 설정에 들어가는 값은 **선택 순번**이다 [확정].

```cpp
// archongui.cpp:2469  (parseUI — 저장·전송 경로)
config.insert("RAWSEL", QString::number(rawsel->currentIndex()));
```

```cpp
// archongui.cpp:2568  (updateUI — 불러오기 경로)
rawsel->setCurrentIndex(qBound(0, config.value("RAWSEL").toInt(), 15));
```

**이 두 줄은 stock 과 글자 하나 다르지 않게 똑같다** (stock 의 `:2467`, `:2566`). 즉 **KMTNet 개조가 손대지 않은 줄이다** [확정]. `addItem` 에 `userData` 를 붙이지도 않았으므로 라벨과 값을 잇는 다른 통로도 없다.

stock 에서는 항목이 `"1"`~`"32"` 로 연속이라 `인덱스 = 라벨 − 1` 이 성립해서 매뉴얼 규약(라벨 = 값+1)과 우연히 맞아떨어졌다. **그런데 KMTNet 목록은 18 에서 55 로 건너뛰므로 그 등식이 깨진다.**

### (c) 산식 대조 — 어디서 어긋나나

| 사용자가 고른 라벨 | 콤보 인덱스 | 전송되는 `RAWSEL` | 매뉴얼 고정사상이 요구하는 값 | 판정 |
|---|---|---|---|---|
| 1 | 0 | 0 | 0 | ✅ 맞다 |
| 18 | 17 | 17 | 17 | ✅ 맞다 |
| **55** | 18 | **18** | **54** | ⚠️ **36 밀림** |
| **70** | 33 | **33** | **69** | ⚠️ 36 밀림 |
| **72** | 35 | **35** | **71** | ⚠️ 36 밀림 |

- **첫 블록(라벨 1~18 → 인덱스 0~17)은 정합한다.** (라벨−1) 이 인덱스와 같아서 우연히 맞은 것이다.
- **둘째 블록(라벨 55~72 → 인덱스 18~35)은 어긋난다.** 필요값 54~71 인데 18~35 가 나간다 — **정확히 36 만큼 모자란다.**
- 그리고 개조판이 낼 수 있는 최대 `RAWSEL` 은 **35** 이다. 슬롯 8 대역(54~71)에는 **개조판도 닿지 못한다.** stock(최대 31)보다 4 늘어난 것이 전부인 셈이다.

라벨 "55"(= 슬롯 8 의 첫 채널 AM55)를 고르면 나가는 `RAWSEL=18` 은 매뉴얼 고정사상으로는 **AM19 = 슬롯 6 의 첫 채널**이다. 그런데 science 실기는 `MOD6_TYPE=0` — **빈 슬롯**이다 [확정].

### (d) 왕복 파손 — 개조와 무관한 stock 결함이 겹친다

`archongui.cpp:2568` 의 `qBound(0, …, 15)` 는 **매뉴얼 p.56 의 옛 상한 0~15 가 화석처럼 남은 줄**이다. 콤보 항목은 stock 32칸, KMTNet 36칸인데 되읽기는 15 까지만 받는다 [확정]. 결과는 다음과 같다.

1. ACF 에 `RAWSEL=54` 가 적혀 있어도, 파일을 열면 콤보가 **인덱스 15(라벨 "16")** 로 조용히 잘린다.
2. 그 상태에서 아무 Apply 나 누르면 `parseUI()` 가 **`RAWSEL=15` 를 컨트롤러에 써버린다.**
3. ACF 를 다시 저장하면 파일 값까지 15 로 덮인다.

경고도 로그도 없다. **즉 KMTNet 이 새로 붙인 55~72 구간은 세션 안에서 고를 수는 있어도 파일로 왕복시키면 절대 살아남지 못한다.** 개조가 완결되려면 이 줄도 같이 고쳐야 한다(`qBound(0, …, rawsel->count()-1)`).

### (e) 실사용 흔적 — 없다

| ACF | `RAWENABLE` | `RAWSEL` | 개조판 GUI 표시 | stock GUI 표시 | 클램프(≤15) |
|---|---|---|---|---|---|
| science (`KMTK_SCI_113`, `KMTC_SCI_101`) | 1 | **3** | "4" | "4" | 통과 |
| guide (`KMTK_GUI_162`) | 1 | **4** | "5" | "5" | 통과 |

둘 다 첫 블록(≤15)만 쓴다 [확정]. 그래서 **현행 ACF 로는 stock 과 개조판이 완전히 같게 동작한다.** 개조가 의미를 갖는 것은 라벨 19 이상(인덱스 18↑)을 고를 때뿐인데, 바로 거기가 값이 어긋나는 지점이다. 개조자가 실제로 슬롯 8 raw 를 떠 봤다면 이상을 눈치챘을 텐데, ACF 가 3/4 인 것을 보면 **이 경로를 한 번도 밟지 않은 것으로 보인다** [유력].

두 실측값 자체는 규약과 모순이 없다 — science `RAWSEL=3` → AM4 = 슬롯 5 ADM 의 4번 채널(TAPLINE 1–16 안에 있음). guide `RAWSEL=4` → AD5 = 슬롯 6 AD 의 1번 채널(`MOD6_TYPE=2`, TAPLINE 에 AD5–8 있음). 둘 다 정상이다 [확정].

### (f) ⭐ 2차 검토 갱신 (2026-09-03) — 펌웨어 디스어셈블로 대부분이 닫혔다

1차 검토는 "산식이 GUI 에 0줄이라 확정할 수 없다" 로 멈췄다. 2차에서 **Rev H 펌웨어(1271, AArch64)를 디스어셈블**해 파서 코드를 직접 읽었고, 세 가지가 확정됐다.

| 물음 | 1차 판정 | 2차 결과 | 근거 |
|---|---|---|---|
| ADM 이 슬롯당 18채널인가 | [유력] (ACF 역산) | ✅ **[확정]** | `>P%05X` 채널 파워다운 마스크 생성 루프가 비트 0–3(4개) + 비트 4–17(14개) = **18비트**를 만든다 (0x5b5e44~0x5b5e78) |
| 탭 번호 상한 | 매뉴얼 p.70 의 `AMnd, n is 1 to 72` | ✅ **[확정]** | 탭 파서가 `AM` 경로에서 `cmp #71` 로 거른다(0x58aefc). `AD` 경로는 `cmp #15`(0x58b15c) → **AD1~AD16 · AM1~AM72** |
| AD/ADM 슬롯 위치 | 매뉴얼 p.20 "중앙 4슬롯" | ✅ **[확정]** | 탭→슬롯 조회가 두 경로 모두 `+4` 를 더한다(`슬롯 = 탭/18 + 4`) → **0기점 4~7 = 1기점 5~8 고정** |
| **FW 가 `RAWSEL ≥ 16` 을 받는가** (U2) | [확인불가] | ✅ **[확정] 받는다** | `RAWSEL` 파서 상한이 **`cmp #71`** 이다 (0x59b7b4) |

⭐ **그래서 `qBound(0, …, 15)`(`archongui.cpp:2568`)는 FW 제약이 아니라 순수한 GUI 결함임이 확정됐다.** 매뉴얼 p.56 의 "0 to 15" 를 옛 AD 기준으로 적어 둔 것이 GUI 에 화석으로 남은 것이다.

⭐⭐ **대안 해석 (B)가 반증됐다.** 1차에서 살려 두었던 *"FW 가 장착된 AD 모듈만 조밀하게 센다(0~35)"* 라는 해석은 성립하지 않는다 — ⓐ `RAWSEL` 상한이 **35 가 아니라 71** 이고, ⓑ 탭→슬롯 계산이 `탭/18 + 4` 라는 **고정 분할**이어서 슬롯 점유 여부를 보지 않는다 [확정]. 즉 개조판이 둘째 블록에 써 넣는 **18~35 는 어떤 해석으로도 슬롯 8 을 가리키지 못한다.**

### (f-2) ⚠️ 다만 "올바른 값" 이 무엇인지는 아직 갈리지 않았다

여기서 새 미묘함이 하나 나왔다. 탭 파서는 `AM<n>` 을 **내부 인덱스로 재배치**한다 (0x58af04~0x58af38). `n = AM번호 − 1`, `q = n/18`, `r = n%18` 일 때

```
r ≤ 3  →  내부 인덱스 = r + 4q          (0…15)
r > 3  →  내부 인덱스 = r + 14q + 12    (16…71)
```

각 ADM 슬롯의 **앞 4채널이 고전 4채널 AD 와 같은 인덱스 공간(0–15)** 을 차지하고 나머지 14채널이 16–71 에 배치되는 구조다. 그런데 **`RAWSEL` 은 파싱한 값을 이 재배치 없이 그대로 저장한다**(`str w0,[x20,#0x138]`).

⚠️ **그러므로 `RAWSEL` 이 어느 공간의 값인지가 미결이다.** 상한이 71 이라는 사실은 두 후보를 가르지 못한다 — **두 공간 모두 0~71** 이기 때문이다.

| 후보 | `AM55`(슬롯 8 첫 채널)에 필요한 `RAWSEL` |
|---|---|
| (가) `AM번호 − 1` 공간 | **54** |
| (나) 내부 인덱스 공간 (재배치가 소비 지점에서 일어남) | **12** (`n=54, q=3, r=0 → 0 + 4×3`) |

**어느 쪽이든 개조판이 쓰는 18 은 아니다** — 이 점은 확정이다. 다만 보고서가 1차에서 단언한 *"필요값은 54~71"* 은 **(가)를 전제한 것이고, (나)라면 틀리다.** 등급을 **[실측대상]** 으로 내린다.

> 파서 상한만 읽고 소비 지점을 추적하지 못한 것이 이 미결의 원인이다. 소비 지점은 함수 전체에서 베이스 레지스터를 유지하는 코드라 정적으로 짚지 못했다.

### (f-3) 그 밖에 남은 유보

1. **모든 코드 근거는 1271(Rev H · AArch64) 것이다.** 1252(Rev F)는 MicroBlaze 소프트코어라 디스어셈블하지 못했다(capstone 에 백엔드가 없다). 따라서 **Rev F 두 대(`KMTK_SCI_113` · `KMTK_GUI_162`)에 대해서는 위 확정이 그대로 적용된다고 단정할 수 없다** → 그쪽은 **[유력]**. 다만 두 판의 설정 키 문자열 테이블이 **완전히 대응**하므로(§10.7) 상한 로직까지 달라졌을 개연성은 낮다.
2. **stock 목록 `1..32` 의 출처**는 여전히 확정하지 못했다. 소스에는 맨 리터럴뿐이다. 다만 2차에서 채널 파워다운 명령이 **`>P%X`(4채널) · `>P%02X`(8채널) · `>P%05X`(18채널) 세 종류**임을 확인했으므로, **8채널 AD 계열 모듈이 실재한다**는 것까지는 뒷받침된다 [유력]. "4슬롯 × 8채널 = 32" 라는 읽기는 여전히 **[추정]** 이다.
3. **산식은 GUI 에 없다.** GUI 는 TAPLINE 을 자유 텍스트로만 다룬다(`archongui.cpp:1428~1445`, `2476~2478`). `AM<n><L|R>` 을 파싱하거나 슬롯→채널 산식을 계산하는 코드가 **0줄**이다 — `grep '"AM' *.cpp` 무소득 [확정]. 산식은 전적으로 펌웨어 쪽 지식이다.

### (g) 개조 판정 요약 (2차 갱신)

| 항목 | 판정 | 등급 |
|---|---|---|
| 개조의 **의도** | 타당하다. 둘째 ADM(슬롯 8) 채널을 raw 로 보려던 것이고, stock 라벨 1~32 로는 그 이름을 화면에 띄울 수조차 없었다 | [유력] |
| 라벨 선택(슬롯 전폭 18채널씩) | 매뉴얼 p.70 및 **펌웨어 탭 파서(`AM1~AM72`)** 와 맞는 선택이다 | [확정] |
| 첫 블록 (라벨 1~18 → 값 0~17) | **맞다.** (라벨−1)=인덱스라 우연히 정합 | [확정] |
| 둘째 블록 (라벨 55~72 → 값 18~35) | ⚠️ **틀렸다.** 필요값은 (가)54~71 또는 (나)12~15·58~71 인데 **어느 쪽도 18~35 가 아니다** | **[확정]**(틀렸다는 것) / 올바른 값은 [실측대상] |
| 왕복(불러오기) | ⚠️ **깨진다.** `qBound(…,15)` 가 잘라내며, **FW 는 71 까지 받으므로 이는 순수 GUI 결함이다** | [확정] |
| 실사용 흔적 | **없다.** 보유 ACF 13종 전부 `RAWSEL ≤ 4` | [확정] |
| 고치려면 | `:2469` 를 라벨→값 사상표로, `:2568` 의 상한을 `count()-1` 로. **단 (가)/(나)를 실측으로 먼저 가른 뒤에** | — |

### (h) 판정을 닫는 실측 절차 (2차 갱신)

2차 검토로 **"18~35 는 틀렸다"** 까지는 코드로 닫혔다. 남은 것은 **(가) `AM번호−1` 공간인가, (나) 내부 인덱스 공간인가** 하나뿐이고, 이것은 실기로만 갈린다.

1. science 컨트롤러(ADM 이 슬롯 5·8)에 `RAWENABLE=1` 과 아래 값을 **ACF 텍스트 편집 또는 `WCONFIG` 직접**으로 넣고 `APPLYCDS`. GUI 로는 `qBound(…,15)` 때문에 입력할 수 없다.
2. **`RAWSEL=54`** 로 시험 → raw 파형이 **슬롯 8 ADM 의 1번 채널(`AM55`)** 로 나오면 **(가) 확정**.
3. 아니면 **`RAWSEL=12`** 로 반복 → 여기서 슬롯 8 이 나오면 **(나) 확정**.
4. 대조군으로 **`RAWSEL=16`** 을 넣어 본다. (나)라면 이것이 **슬롯 5 의 5번째 채널(`AM5`)** 이어야 한다 — (가)라면 `AM17`(슬롯 5 의 17번째)이다. 두 해석이 **가장 크게 갈리는 지점**이라 판별력이 높다.
5. 각 단계에서 `?xx` 거부가 나오는지, `FRAME` 응답의 `BUFnRAWBLOCKS`/`BUFnRAWLINES` 가 정상으로 잡히는지 함께 본다. **파서 상한이 71 이므로 거부는 나오지 않아야 한다** — 나온다면 Rev 별 차이를 의심할 것.

> ⚠️ **슬롯 8 에만 신호를 넣고 보는 것이 가장 깔끔하다.** 두 ADM 이 같은 신호를 받으면 어느 슬롯이 잡혔는지 구별되지 않는다.
>
> ⚠️ **Rev F 유닛(113)에서도 한 번 확인할 것.** 위 코드 근거는 Rev H(1271) 것이고, Rev F 는 CPU 자체가 다르다(§10.7).

---

# 3. 전체 구조

## 3.1 파일별 역할 (줄 수 포함)

`src/` 는 자체 소스 20개(`.cpp` 10 + `.h` 10, 합 **13,870줄**) + `src/qwt/` 116개다 [확정].

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

도메인 지식이 `archon.cpp`(프로토콜) · `archongui.cpp`(화면·파일) · `modules.cpp`(모듈)에만 몰려 있고, 나머지 11개는 **전부 바보 부품**이다. 프로토콜 문자열이나 ACF 키가 단 하나도 나오지 않는다 [확정].

## 3.2 스레드 모델 — 딱 셋

| 스레드 | 클래스 | 하는 일 | 이벤트 루프 |
|---|---|---|---|
| **GUI** | `TArchonGUI` | 위젯 전부 + `poll()` 슬롯까지 여기서 돈다 | 있음 |
| **통신** | `Archon : QThread` | 소켓을 독점. 명령 문자열 하나를 받아 TCP 로 주고받고 시그널로 결과 반환 | **없음**(`exec()` 안 부름, `forever` 폴링 루프) |
| **틱** | `TUpdateTimer : QThread` | `while(!thread_exit){ msleep(500); emit update(); }` — 그게 전부다 | 없음 |

핵심 설계 두 가지 [확정]:

- **`socket` 을 `run()` 안에서 생성한다**(`archon.cpp:57`). 즉 `QTcpSocket` 이 작업자 스레드에 귀속되어 GUI 스레드가 소켓을 건드릴 일이 원천적으로 없다. 그래서 락 하나(`mutex`)로 **명령 인수인계만** 지키면 된다.
- **명령 슬롯은 깊이 1짜리 우편함이다.** 큐가 아니다. `command()` 세 오버로드(`archon.cpp:184~227`)가 전부 이 모양이다:

```cpp
mutex.lock();
if (CommandInProgress) { mutex.unlock(); return 1; }   // 바쁘면 즉시 거절 — 명령은 버려져
CommandInProgress = true;
NewCommand = cmd;
mutex.unlock();
return 0;
```

`getResult()`(`archon.cpp:229~245`)는 `!CommandInProgress` 가 될 때까지 `msleep(50)` 으로 도는 **바쁜 대기**다. GUI 스레드에서 호출하면 이벤트 루프가 그동안 멈춘다. 그래서 사용자 동작 슬롯들은 첫 줄에 `getResult()` 를 놓아 "직전 폴링이 끝날 때까지 기다렸다가 새로 던진다" 로 쓴다.

프레임 데이터용 락은 **완전히 별개**다 — `frames`(`QVector<TFrameBuffer>`)와 `frameMutex` 가 `archon.h:74~75` 에서 **public** 이고, 명령용 `mutex`(private, `:88`)와 겹치지 않는다. 프레임은 GUI 가 직접 만지고, 명령 인수인계는 만지지 않는 구조다 [확정].

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

`fixedTabs = 13` (`archongui.cpp:107`). 소스 주석은 "Twelve tabs" 라고 하지만 실제로는 13개다 — 주석이 낡았다 [확정].

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
| 13~ | Slot N: TYPE | `modules.cpp` | 모듈 탭. `parseSystem()` 이 만들고 지운다 |

**인덱스 6·10 이 하드코딩되어 있다** — `imageMouseXY` 는 `currentIndex()==6` 일 때만(`:3005`), `rawImageMouseXY` 는 `==10` 일 때만(`:3118`), 커맨드라인 로드 성공 시 `setCurrentIndex(6)`(`:1252`). 탭을 하나 끼워넣으면 세 군데가 어긋난다 [확정].

## 3.5 `-small` 인자와 첫 인자 함정

`-small` 은 중앙 위젯을 `QScrollArea` 에 넣는 것 **딱 하나**다(`:58~68`). 그런데 `main.cpp:9` 가 `TArchonGUI w(a.arguments().value(1))` 로 **첫 인자를 무조건 열 파일명으로** 넘긴다. 그래서 `archongui -small` 로 실행하면 `loadFilename == "-small"` 이 되고, 파일 열기는 실패하지만 그 전에 `filenameLabel->setText("-small")` 을 해버려서 **상태바에 "-small" 이 파일명처럼 남는다**(`:3694~3698`). 파일과 옵션을 같이 주려면 `archongui frame.raw -small` 순서로 주어야 한다 [확정].

---

# 4. 통신 프로토콜

## 4.1 와이어 형식

매뉴얼 p.45 와 `archon.cpp:318~383` 이 완전히 일치한다 [확정].

| 방향 | 형식 | 비고 |
|---|---|---|
| 요청 | `>XX<명령>\n` | `>` + **대문자 2자리 16진** 참조번호 + 명령 + LF(0x0A). CR 안 씀. 인코딩 Latin-1 |
| 성공 | `<XX<응답>\n` | 앞 3바이트(`<XX`)를 떼고 나머지를 반환(`:366`). **ASCII 응답에 `:` 는 없다** |
| 오류 | `?XX\n` | 이유는 알려주지 않는다. `LOGERROR("Error parsing command")` → 반환 1 (`:369~370`) |
| 이진 | `<XX:` + **정확히 1024 B** | 4바이트 프리앰블 + 원시 데이터, **종료 개행 없음** |

접속은 **TCP 포트 4242 하드코딩**(`archongui.cpp:2668`), 기본 주소 `10.0.0.2`(`:86`). 포트를 바꿀 UI 는 없다 [확정].

> ⚠️ System 탭의 "Network Configuration"(`leIP`/`leNetmask`/`leGateway`, `:305~313`)은 **접속용이 아니다.** 컨트롤러 자신의 IP 설정값이고 `config` 의 `IP`/`NETMASK`/`GATEWAY` 키로 들어가 `APPLYNET` 으로 써넣는 것이다. 이름이 비슷해서 혼동하기 쉽다.

## 4.2 참조번호와 재동기화

```cpp
socket->readAll();                      // 335  잔류 바이트 폐기
last_msgref = msgref;                   // 336
msgref = (msgref + 1) & 0xFF;           // 337  0x00~0xFF 순환
cmd.prepend(">" + hex(last_msgref, 2)); // 338
```

- `msgref` 는 **명령을 실제로 보낼 때만** 증가한다. `cmd` 가 비어 있으면 336~338 을 통째로 건너뛴다.
- **참조번호가 맞지 않는 줄은 조용히 버려지고 루프가 계속 돈다**(`:362`). `break` 도 `LOGERROR` 도 없다. 늦게 온 이전 응답이 현재 명령을 오염시키지 않게 하는 장치다.
- `?` 조차 참조번호가 맞아야 오류로 잡힌다(`:369`).

`last_msgref` 가 지역변수가 아니라 **멤버**(`archon.h:107~108`)인 이유가 핵심이다. `VERIFY`·`FETCH` 는 명령 하나에 컨트롤러가 **블록 여러 개를 연달아** 보내는데(매뉴얼 p.50~51), 그 블록들이 **전부 같은 참조번호**를 달고 온다. 그래서 호출부가 두 번째부터 `s.clear()` 로 **빈 명령**을 넘겨서 아무것도 보내지 않고 `last_msgref` 를 보존한 채 다음 블록만 읽는다(`:979~980`, `:1354~1356`) [확정].

> ⚠️ 잔가지 결함: `response.mid(1,2).toInt(&ok,16)` 에서 **`ok` 를 검사하지 않는다**(`:362`, `:432`, `:509`). 16진이 아니면 `toInt` 가 0 을 반환하는데 마침 `last_msgref` 가 0 이면 엉뚱한 줄이 매칭될 수 있다. `msgref` 는 256번마다 0 을 지나간다 [확정, 심각도 낮음].

## 4.3 ⭐ 인식 못 한 명령 = 무응답

매뉴얼 p.45 가 명시한다 [확정]:

> "Unrecognized commands are ignored."

즉 오타 명령은 `?` **조차 오지 않는다.** 그러면:

1. 명령은 이미 나갔고 `msgref` 도 소비되었다
2. 응답 루프가 `waitForReadyRead(10)` 을 돌며 대기
3. `timeout`(보통 5초)을 **통째로 소모**한 뒤 `LOGERROR("Timeout waiting for response")`(`:356`)
4. 로그에 `! interfaceCommand: Timeout waiting for response (…archon.cpp:356)` 찍고 반환 1
5. `run()` 루프 끝의 `interfaceFlush()`(`:174`)가 늦게 온 응답을 버리므로 다음 명령은 오염되지 않는다

**재시도는 없다.** 그리고 컨트롤러는 **절대 먼저 말을 걸지 않는다**(매뉴얼 p.45: "The controller only responds to commands, it never initiates a message"). 그래서 프레임이 완성되어도 푸시 알림 같은 것은 없고 호스트가 `FRAME` 을 폴링해야 한다.

`DIRECT` 명령창(`archon.cpp:1676~1687`)으로 사용자가 아무 문자열이나 보낼 수 있으니 이 경로는 실제로 밟히는 경로다.

## 4.4 명령 목록과 타임아웃

| 명령 | GUI 함수 | 타임아웃 | 매뉴얼 | 비고 |
|---|---|---:|---|---|
| `SYSTEM` | `getSystem()` | 5 s | p.46 | 연결 시 1회. 모듈 탭이 생기는 유일한 계기 |
| `STATUS` | `getStatus()` | 5 s | p.47~49 | 폴링. `LOG=n` 만큼 `FETCHLOG` 반복 |
| `FRAME` | `getFrameStatus()` | 5 s | p.50 | 폴링 |
| `FETCHLOG` | (getStatus 안) | 5 s | p.50 | 가장 오래된 로그 1건 |
| `TIMER` | — | — | p.49 | **GUI 는 쓰지 않는다** |
| `WCONFIG…` | `writeConfig()` | 5 s | p.51 | 최대 16384줄, 줄당 2048자 |
| `RCONFIG…` | — | — | p.51 | **GUI 는 쓰지 않는다** |
| `CLEARCONFIG` | `writeConfig()` | 5 s | p.51 | |
| `APPLYALL` | `applyAll()` | **30 s** | p.51 | 끝나면 **CCD 전원 OFF** |
| `APPLYSYSTEM` | `applySystem()` | 5 s | p.53 | |
| `APPLYCDS` | `applyCDS()` | 5 s | p.53 | RAW\*·TAPLINE\*·SHP/SHD·FRAMEMODE |
| `APPLYMODxx` | `applyModule()` | 10 s | p.52 | `xx` 는 **0기점 2자리 16진**. 슬롯5 → `APPLYMOD04` |
| `APPLYDIOxx` | `applyModuleDIO()` | 10 s | p.53 | DIO **+ VCPU** |
| `APPLYNET` | `applyNet()` | 5 s | p.53 | **연결이 끊긴다** |
| `LOADTIMING` | `loadTiming()` | 5 s | p.51 | **코어 리셋** |
| `LOADPARAMS` | `loadParams()` | 5 s | p.52 | 리셋 없음. 목록 첫 번째부터 하나씩 |
| `LOADPARAM p` | `loadParam()` | 5 s | p.52 | 하나만 |
| `PREPPARAM` / `FASTLOADPARAM` / `FASTPREPPARAM` | — | — | p.52 | **GUI 는 쓰지 않는다** |
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
| `REBOOT` / `WARMBOOT` | | 5 s | p.51 | 둘 다 **연결이 끊긴다**. 반환값 무시 |
| `FLASHACTIVECONFIG` / `ERASESTOREDCONFIG` | | **60 s** | p.52~53 | **반환값 무시 — 저장 실패가 GUI 에 알려지지 않는다** |
| **`POLLON` / `POLLOFF`** | `writeConfig()` 내부 | 5 s | **없음** | 미문서 명령 |
| **`BIASPOLLON` / `BIASPOLLOFF`** | `pollOn()`/`pollOff()`, 플래시 계열 | 5 s | **없음** | 미문서 명령 |
| **`ATLASMOVE`** | `atlasMove()` | 5 s | **없음** | 미문서 명령 |
| `LOCKNEWEST` | `lockNewestFrame()` | — | — | **GUI 내부 이름.** 결국 `LOCK`+n 을 보낸다(`:673`) |

기본값 `ARCHON_TIMEOUT = 5000` ms (`archon.cpp:15`) [확정]. 매뉴얼에는 **명령 소요시간이 한 줄도 적혀 있지 않다** [확인불가].

> ⚠️ **`POLLON/POLLOFF` 와 `BIASPOLLON/BIASPOLLOFF` 는 서로 다른 명령이다.** `writeConfig()` 는 `POLLOFF`/`POLLON` 을 쓰고(`:1413`, `:1428`), `Archon::pollOn()/pollOff()` 는 `BIASPOLLON`/`BIASPOLLOFF` 를 쓰며(`:1498`, `:1511`), 플래시·검증 계열도 전부 `BIASPOLL*` 을 쓴다. **GUI 바닥의 "Polling On/Off" 버튼은 바이어스 폴링을 끄는 것이지 GUI 의 500 ms 틱을 끄는 것이 아니다.** 함수명이 혼동하기 쉽게 붙어 있고, 둘 다 매뉴얼에 없어서 정확한 의미 차이는 [확인불가].

## 4.5 오류 처리 · 부분 실패

`LOGERROR` 매크로(`archon.cpp:10`)가 `__LINE__` 을 저장해서 **로그만 보고 소스 몇 번째 줄에서 터졌는지** 바로 알 수 있다. 형식은 `! 함수명: 메시지 (파일:줄)` 이고 `!` 로 시작하는 것이 오류 관례다 [확정].

**모든 명령 함수가 `int` 를 반환하고 0=성공 / 1=실패로 통일되어 있다. 예외는 없다.** 전달은 명령 함수 → `run()` 의 `result` → 다음 루프에서 `CommandResult` → `getResult()` → GUI.

**재시도 루프가 파일 전체에 하나도 없다.** 타임아웃 한 번, 프리앰블 불일치 한 번, `?` 한 번 → 즉시 실패다. 유일한 자가치유는 `interfaceCommand` 첫머리의 **자동 재연결**(`:326~330`)이다 — 소켓이 끊겨 있으면 명령 전에 다시 접속한다.

`interfaceFlush()`(`:547~553`)는 `waitForReadyRead(10)` 후 `readAll()` 로 있는 것을 전부 버린다. **`run()` 루프 끝에서 매 바퀴** 불리고(`:174`), `getSystem`/`getStatus`/`getFrameStatus`/`writeConfig`/`flash`/`verify`/`flashMod`/`verifyMod` 시작에서도 불린다. 이유는 명확하다 — **이 프로토콜에는 스트림 재동기화 수단이 없다.** 텍스트는 참조번호로 걸러내지만 이진은 프리앰블 4바이트가 어긋나는 순간 끝이다. "느슨하게 자주 버린다" 가 유일한 방어책이다 [확정].

부분 실패가 남기는 상태 [확정]:

| 상황 | 남는 상태 |
|---|---|
| `writeConfig` 중간 실패 | 설정 메모리가 `CLEARCONFIG` 된 뒤 **반쯤 채워진 채로 남는다.** 오류 경로(`:1432~1435`)는 `POLLON` 만 되돌리고 설정은 복구하지 않는다 |
| `flash` 중간 실패 | PROM 이 반쯤 소거/기록된 상태. `BIASPOLLON` 만 복구 |
| `fetchFrame` 중간 실패 | 호스트 버퍼는 `Locked=false` 로 되돌린다(`:1397~1400`). 하지만 **컨트롤러 쪽 `LOCKn` 은 풀리지 않는다** — `LOCK0`(`:1386`)에 도달하지 못하기 때문이다 |
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
| 8 | `EXTCLKPRESENT` | STATUS 목록에 **없음** | GUI 가 읽음(`archongui.cpp:2207`) | ⭐ |
| 9 | `POWER_ID` | SYSTEM 목록에 **없음**(부록 A p.96 엔 있음) | GUI 가 읽음. 12자리 16진 | ⭐ |
| 10 | `FRAMEnBASE` vs `BUFnBASE` | p.71 본문 `FRAMEnBASE`, p.50 키 목록 `BUFnBASE` | 실제는 **`BUFnBASE`** | ⭐ |
| 11 | p.47 STATUS 표 정렬 | 키 열과 주석 열이 **한 칸씩 어긋난 채 인쇄됨** | 키 이름만 믿고 주석 정렬은 믿으면 안 된다 | ⭐ |
| 12 | 바이트 순서 | **한 줄도 없음** | 변환 코드가 없으니 **호스트 네이티브 = x86 리틀엔디언 uint16** [유력] | ⭐ |
| 13 | ADM 용 `STATEn/MODi` 형식 | **없음** | `ADM::usesClocks()` 가 false — ADM 은 타이밍 상태를 안 가짐 [유력] | ⭐ |

방향은 한결같다 — **FW 와 GUI 가 매뉴얼보다 앞서 있다.** 구조(슬롯·탭 체계)는 완벽히 들어맞지만, 범위·자릿수·명령 목록 같은 세부는 낡았다.

## 4.7 Rev F 동시 접속 1개 — 운영 제약

매뉴얼 p.15 [확정]:

> "Rev F and older backplanes **can only support a single connection at a time**. … **Rev H backplanes currently support up to four simultaneous connections.**"

우리 실기 대조 [실측]:

| 유닛 | 장비번호 | FW | `BACKPLANE_REV` | Rev 문자 | 동시 접속 |
|---|---|---|---|---|---|
| KMTC-SCI-101 | STA0284 | 1.0.1261 | **7** | **H** | 최대 4 |
| KMTC-SCI-102 | STA0285 | 1.0.1261 | **7** | **H** | 최대 4 |
| KMTS-SCI-101 | STA0286 | 1.0.1261 | **7** | **H** | 최대 4 |
| **KMTS-SCI-102** | **STA0287** | **1.0.1261** | **7** | **H** | 최대 4 |
| **KMTS-GUI-161** | **STA0291** | **1.0.1261** | **7** | **H** | 최대 4 |
| KMTK-SCI-113 | STA0200 | 1.0.1252 | **5** | **F** | **1** |
| KMTK-GUI-162 | STA0201 | 1.0.1252 | **5** | **F** | **1** |

⭐ **보유 ACF 13종의 `[SYSTEM]` 절을 전수 대조한 결과다** (2026-09-03) [확정]. `BACKPLANE_TYPE=1`(X12)은 7대 전부 같다.

### ⚠️ 이 표는 **함대 전수가 아니라 "우리가 ACF 를 가진 대수"** 다

이 구별을 놓치면 판올림 범위를 잘못 잡는다. `raw_fits_spec/__reference/Archon_Unit_Info.txt` 가 적는 **관측소 함대는 9대**다 [확정]:

| 사이트 | SCI-101 | SCI-102 | GUI-161 |
|---|---|---|---|
| **KMTC**(CTIO) | STA0284 ✅ | STA0285 ✅ | STA0290 ❌ |
| **KMTS**(SAAO) | STA0286 ✅ | STA0287 ✅ | STA0291 ✅ |
| **KMTA**(SSO) | STA0288 ❌ | STA0289 ❌ | STA0292 ❌ |

✅ = ACF 보유(Rev 확인됨) · ❌ = **ACF 없음 → Rev 미확인**

여기서 두 가지가 따라온다 [확정]:

1. **ACF 로 Rev H 가 확인된 다섯은 전부 관측소 함대 유닛이다** — KMTC-SCI-101 · KMTC-SCI-102 · KMTS-SCI-101 · KMTS-SCI-102 · KMTS-GUI-161.
2. **Rev F 두 대(`KMTK_SCI_113` · `KMTK_GUI_162`)는 함대가 아니라 KASI 벤치기다.** `KMTK` 는 위 원장에 없다. 즉 **관측소에는 Rev F 가 하나도 확인되지 않았고**, Rev F 결론이 적용되는 곳은 벤치뿐이다.

⚠️ **함대 9대 중 4대(STA0288 · 0289 · 0290 · 0292)는 Rev 를 모른다.** 굽는 범위를 정할 때 "Rev H 다섯" 은 **확인된 상한이지 함대 전수가 아니다** — 나머지 넷의 `SYSTEM` 응답을 받기 전에는 함대 차원의 판올림 계획을 세울 수 없다(§10.12).

> 유닛 이름 주의: ACF 파일명의 `_103` 같은 꼬리는 **IP 끝자리**이고 유닛 이름이 아니다(원장 각주 *"ID number = IP address"*). `STA0291` 의 정식 이름은 **KMTS-GUI-161** 이다.

즉 **Rev F 두 대(113 · GUI-162, 둘 다 KASI 벤치)에서는 ICS 가 소켓을 잡고 있으면 ArchonGUI 가 접속하지 못한다.** "동시에 둘 다" 는 구조적으로 불가능하다. Rev H 는 4개까지 가능하지만, 두 클라이언트가 같은 컨트롤러 상태를 동시에 바꾸는 것은 별개 문제다. **운영 절차에 명시해두어야 할 값이다.**

프로세서도 다르다 — Rev F 이하는 Kintex 7 FPGA 안의 32비트 소프트코어, Rev H 는 64비트 ARM(p.15). 네트워크는 **1 Gbps 전용**이고 10/100 하위호환이 되지 않는다.

---

# 5. 설정·적용 계통

## 5.1 ACF 형식과 세 가지 키 표기

ACF 는 **Windows INI 형식**이고 절이 딱 둘이다(매뉴얼 p.73) [확정]:

- `[SYSTEM]` — `SYSTEM` 명령 응답을 그대로 저장. 컨트롤러 없이도 GUI 가 구성을 보여주고 오프라인 편집을 할 수 있게 하려는 것이다.
- `[CONFIG]` — 컨트롤러로 보낼 설정 key/value 전부.

GUI 는 **파서를 직접 짜지 않았다.** `QSettings(filename, QSettings::IniFormat)` 에 통째로 맡겼다(`archongui.cpp:1280~1307` 읽기, `:1309~1340` 쓰기). 그래서 세 가지 표기가 갈린다 [확정]:

| 문맥 | 표기 | 예 | 왜 |
|---|---|---|---|
| 코드 안 `config` 맵 / 와이어 `WCONFIG` / 매뉴얼 p.57~63 | **슬래시** | `MOD5/CLAMP1` | 코드가 `key + "/CLAMP1"` 로 조립(`modules.cpp:631` 등) |
| ACF `[CONFIG]` 절 | **역슬래시** | `MOD5\CLAMP1=0.0` | QSettings 가 INI 로 쓸 때 키 안의 `/` 를 `\` 로 이스케이프 |
| SYSTEM 응답 / ACF `[SYSTEM]` 절 | **밑줄** | `MOD5_TYPE=17` | 계층 키가 아니라 처음부터 밑줄. 변환 대상이 아님 |
| STATUS 응답 / `status` 맵 | **슬래시** | `MOD5/TEMPA` | 컨트롤러가 그대로 내보냄. 매뉴얼 p.47~48 도 슬래시 |

변환 코드가 소스 어디에도 없다(`replace()` 는 확장자 치환 두 곳뿐) — **역슬래시는 오직 `.acf` 파일 안에서만 존재하는 표기다** [확정]. 증거 하나 더: QSettings 를 거치지 않고 손으로 쓰는 `.ncf` 경로에서는 `MOD%1/VCPU_LINE%2` 처럼 **슬래시가 그대로 파일에 나간다**(`archongui.cpp:1480`).

값에 쉼표가 들어가는 것(TAPLINE, `STATEn/MODi`)은 **큰따옴표로 감싼다**(매뉴얼 부록 A p.96). **키 순서는 상관없다**(노트 p.5).

`.ncf`("nice") 는 diff·리뷰용 변형이다. 절이 `[SYSTEM]` `[CONFIG]` `[TIMINGSCRIPT]` `[PARAMETERS]` `[CONSTANTS]` `[TAPLINES]` `[STATE]`×N `[VCPUn]`×N `[END]` 로 나뉘고, 리스트 키의 **번호를 빼서 본문 그대로** 적는다. 정렬도 `QCollator(numericMode)` 로 자연 정렬이라 `LINE2` 가 `LINE10` 앞에 온다. 읽고 나면 `parseSystem(); updateUI();` 로 ACF 경로와 똑같이 합류한다 — **겉모습만 다른 같은 config 맵이다** [확정].

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

**"per tap" 이 핵심이다.** `LINECOUNT`/`PIXELCOUNT` 는 전체 이미지 크기가 아니라 **채널 하나가 읽는 영역**이다 [확정].

`ADXCDS`/`ADXRAW` 가 guide ACF 에 **없는** 것은 의미가 있다 — GUI 는 숨겨진 위젯의 키를 아예 쓰지 않는다(`if (!adxraw->isHidden())`, `:2456`, `:2462`). 그 위젯은 **X12 + `BACKPLANE_REV ≥ 4` + build ≥ 930** 일 때만 보인다. 즉 science 는 조건을 통과했고, **guide 백플레인은 Rev D 이하이거나 빌드 930 미만**이라는 뜻이다 [유력] — guide 의 `BACKPLANE_REV`/`VERSION` 을 아직 받지 못했으므로 [확인불가].

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

줄 조립은 다음과 같다(`:1421`):

```cpp
s = QString("WCONFIG%1%2=%3").arg(line, 4, 16, QChar('0')).toUpper().arg(i.key()).arg(i.value());
```

`.toUpper()` 가 `%2`/`%3` **치환 전에** 걸려 있어서 **줄 번호 16진만 대문자화되고 키·값의 대소문자는 보존된다.** 이것이 맞는 동작이다 — 타이밍 스크립트나 파라미터 이름은 대소문자를 지켜야 하기 때문이다 [확정].

⚠️ **`config` 는 `QMap<QString,QString>` 이라 키 사전순으로 순회한다**(`archon.h:50`). ACF 에 적힌 순서가 아니라 **알파벳 순서**로 줄 번호가 매겨진다. FW 가 키 이름으로 파싱하므로 실질 문제는 없어 보이나, `RCONFIG` 로 되읽으면 줄 순서가 원본과 다르다는 점은 알아두어야 한다 [확정].

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

핵심을 한 줄로 [확정]: **`writeConfig()` 뒤에 붙는 `APPLYxxx` 한 단어가 "설정 메모리의 어느 부분을 하드웨어에 반영할지" 를 고르는 것이다. 설정 업로드 자체는 항상 전체다.** 부분 갱신 같은 최적화가 없다. `applyModule` 만 눌러도 수천 줄이 다시 올라간다.

모든 Apply 슬롯이 똑같은 4단 관용구를 쓴다:

```cpp
if (!connected) { logMessage("Archon not connected."); return; }
parseUI();                     // 위젯 → config (전 모듈 전수)
archon->getResult();           // 진행 중 명령(폴링) 대기
archon->setConfig(config);
e = archon->getResult();
if (!e) { archon->command("<APPLY…>"); archon->getResult(); }
```

## 5.5 ⭐ 순서 의존성

**A. 함수 내부 (코드가 강제한다)**

```
interfaceFlush → POLLOFF → CLEARCONFIG → WCONFIG×N → POLLON → APPLYxxx
```

`POLLOFF` 가 먼저인 것은 배경 폴링이 `WCONFIG` 수천 줄 사이에 끼어드는 것을 막으려는 것이다. 그런데 `POLLON` 이 `APPLYxxx` **앞에** 있어서(`:1428` → `:1444`), 적용 자체는 폴링이 켜진 채로 일어난다 [확정].

**B. 함수 사이 (호출자 책임 — 코드가 강제하지 않는다)**

1. **`APPLYALL` → `POWERON`** — 매뉴얼 p.51: "An APPLYALL is required before this operation." 그리고 `APPLYALL` 직후엔 전원이 꺼져 있으니 반드시 `POWERON` 을 따로 해야 한다. `powerOn()`(`:1468~1479`)은 이를 확인하지 않는다 [확정]. 실기에서도 `APPLYALL` 을 하지 않으면 `?xx` 거부다 [실측].
2. **`APPLYALL` → `LOADTIMING` → `LOADPARAM(S)`** — `LOADTIMING` 이 코어를 리셋하므로, 파라미터 미세조정은 그 뒤에 해야 리셋 없이 반영된다.
3. **`APPLYNET` 은 맨 마지막** — IP 가 바뀌면 그 순간 연결이 끊긴다. 매뉴얼 p.44 절차: Apply Network Configuration → (오류 메시지가 뜨는 것이 정상) → Disconnect → 새 주소로 Connect → `FLASHACTIVECONFIG` 로 영구화.
4. **`FLASHACTIVECONFIG` 는 원하는 설정이 적용된 뒤에.**
5. **`RESETTIMING`/`HOLDTIMING`/`RELEASETIMING`/`POWERON`/`POWEROFF`/`POLLON`/`POLLOFF` 는 `writeConfig()` 를 부르지 않는다.** 이미 적용된 상태 위에서만 동작한다. **설정을 바꾸고 이것들만 누르면 아무 효과가 없다** [확정].
6. **`HOLDTIMING` → (각 시스템에 적용) → `RELEASETIMING`** 쌍이 다중 컨트롤러 동기 절차다(p.19). 데이지체인이면 시스템 간 약 10 ns + 케이블 지연이 남는다.

## 5.6 결함 — 적용 계통에서 찾은 것

> ⚠️ **번호 주의**: 이 표의 `C1`~`C6` 은 **이 절 안에서만 유효한 국소 번호**이고, §11.3 의 `C1`~`C32`(우리가 답습하지 말 것)와 **별개 체계**다. 인용할 때 절 번호를 함께 적을 것.

| # | 내용 | 위치 | 등급 |
|---|---|---|---|
| C1 | **`CONFIG` 가 `result` 를 갱신하지 않는다** → `setConfig` 뒤 `getResult()` 가 **직전 통신 명령의 결과**를 반환. GUI 가 이것으로 `APPLYxxx` 실행 여부를 결정하므로, 직전에 아무 명령이나 실패했으면 `APPLYALL` 이 조용히 건너뛰어진다. 같은 패턴이 7개 Apply 슬롯 전부에 있다 | `archon.cpp:77~81` + `archongui.cpp:1622~1627` 등 | 중 |
| C2 | `writeConfig` 중간 실패 시 설정 메모리가 **반쯤 지워진 채** 남고 복구 안 됨. 이 상태에서 `APPLYALL` 하면 반쪽 설정이 적용된다 | `archon.cpp:1415~1427` | 중 |
| C3 | **`parseUI()` 첫 줄이 `config.clear()`** 라 저장 시 config 는 위젯에서 재구성된다. ① 숨은 위젯 키(`EXTCLOCK`/`TRIGOUTPOWER`/`PCLKDELAY`/`ADXRAW`/`ADXCDS`/`LINESCAN`)가 빠지고 ② **이 GUI 가 모르는 키는 전부 유실된다.** ACF 왕복이 무손실이 아니다 | `archongui.cpp:2422`, `:2428~2467` | 중 |
| C4 | `openNiceFile()` 이 파싱 중단 시 `goto done` 으로 빠져서 **조용히 반쪽만 로드** | `archongui.cpp:1364`, `:1485` | 하 |
| C5 | `updateUI()` 의 상태 복원이 상태마다 `config.keys()` 를 전수 순회 — O(상태수 × 전체키수) | `archongui.cpp:2607~2617` | 하(성능) |
| C6 | `WCONFIG` 는 키 하나당 왕복 한 번이라 수천 키면 그만큼 왕복이 생긴다. Apply All 이 오래 걸리는 이유가 여기에 있다 | `archon.cpp:1415~1427` | 정보 |

> C3 은 우리에게 특히 중요하다. **같은 ACF 를 다른 하드웨어(또는 미연결 상태)에서 열었다 저장하면 키 집합이 달라진다.** ACF 를 GUI 로 왕복시키는 습관은 위험하다.

---

## 5.7 보유 ACF 전수 (2026-09-03 반입분 포함)

`__reference/acf/` 에 실기 ACF **12개 + 타이밍 스크립트 2개**(science·guide)가 들어왔다. 전수로 훑은 결과다 [확정].

| 구분 | 파일 | 탭 | 접두 | 비디오 슬롯 | 탭 번호 | `RAWSEL` | 기하 |
|---|---|---:|---|---|---|---:|---|
| science | `KMTC_SCI_101` MK · `KMTC_SCI_102` NT · `KMTK_SCI_113` MK/NT · `KMTS_SCI_101` MK | 32 | `AM` | 5, 8 | **1–16, 55–70** | **3** | 1200×4700 |
| guide | `KMTK_GUI_162` · `kmtnet_guide_*` 6종 | 8 | `AD` | 5, 6 | **1–8** | **4** | 528×1033 |

⭐ **12개 전부가 `RAWSEL ≤ 4` 다** — §2.2(e) 에서 "실사용 흔적 없음" 의 근거가 **2개에서 12개로 늘었다.** 둘째 블록(라벨 55~72)을 쓴 ACF 는 **하나도 없다** [확정]. 그리고 science 넷이 탭 구성까지 완전히 같아서, §2.2(a) 의 ADM 18채널 사상이 유닛 넷에서 재확인된다.

### 5.7.1 ⭐ `for1110` ↔ `for1259` — GUI 판별 ACF 가 실재한다

guide ACF 가 **같은 설정의 두 판**으로 들어왔다: `..._for1110_*` 과 `..._for1259_*`. 뒤 숫자는 GUI/FW 빌드 번호다(1259 = 우리가 분석한 그 GUI). 두 쌍을 키 단위로 대조했다 [확정].

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

⚠️ **처음에는 이것을 §11.3 C3(모르는 키 유실)의 실물 증거로 읽었으나 틀렸다.** 줄 단위 `diff` 가 `MOD7\...` 블록을 통째로 삭제로 보여줬지만, 그것은 **두 파일의 키 정렬 순서가 달라서** 생긴 착시였다 — 키 집합으로 대조하니 `MOD7` 키는 **양쪽 다 88개**로 같다. **잃은 키는 0개다.**

그래서 이 자료가 실제로 말해주는 것은 다음과 같다:

1. **판올림 방향(1110 → 1259)은 안전하다.** 새 GUI 가 아는 키가 **상위집합**이라 잃는 것이 없고, 오히려 신설 기능 셋(`GATEWAY`·`NETMASK`·`TRIGINEDGE`)이 붙는다. `APPLYNET` 계통과 외부 트리거 극성이 그 판에 생겼다는 뜻이다 [유력].
2. ⚠️ **위험한 것은 반대 방향이다.** 1259 판 ACF 를 **옛 GUI(1110)로 열어 저장하면** 저 세 키가 사라진다 — C3 가 경고하는 그 경로다. 등급은 [유력](이 자료로 직접 관측한 것은 아니다).
3. **GUI 는 저장할 때 실수 서식을 정규화한다**(`-150.0` → `-150`). 그래서 **ACF 를 바이트로 비교하면 안 되고 키·값 단위로 비교해야 한다** [확정]. 우리 대조 도구에 그대로 걸리는 이야기다.
4. `SENSORBUPPERLIMIT 70→60`, `MOD7\SENSORALOWERLIMIT -220→-230` 은 서식이 아니라 **운영자가 실제로 고친 값**으로 보인다 [추정] — 판별 차이로 오해하면 안 된다.

### 5.7.2 `goff` 판 — 딱 한 키

`kmtnet_guide_STA0291_103_R2601_for1259.acf` 와 `..._goff_...` 의 차이는 **정확히 한 줄**이다 [확정]:

```
MOD10\DIO_POWER=1   →   0
```

`goff` = **게이지 off**. HeaterX(MOD10)의 DIO 전원을 내려 진공 게이지를 끄고 기동하는 판이다. `icg_archon` 이 게이지 전원 대기를 건너뛰는 경로를 가질 수 있다는 기존 관측과 정합한다.

### 5.7.3 타이밍 상태기계 원본 — science · guide 두 벌

타이밍 스크립트는 ACF 안에 **`LINE<n>=` 키로** 들어 있다. 값은 큰따옴표로 감싸여 있고, 라벨 줄(`Start:`)과 빈 줄은 따옴표 없이 들어간다. 그것을 풀어 쓴 것이 `acf/` 의 두 텍스트 파일이다 [확정].

| 파일 | 출처 ACF | 줄 수 |
|---|---|---:|
| `acf_timing_script_science.txt` | `KMTK_SCI_113_STA0200_R2608_MK.acf` 의 `LINE0~136` | 137 |
| `acf_timing_script_guide.txt` | `KMTK_GUI_162_STA0201_R2608.acf` 의 `LINE0~112` | 113 |

> ⚠️ **정정** — 처음 반입된 `acf_timing_script.txt` 를 guide 것으로 적었으나 **틀렸다. science 것이다.** 줄 단위로 대조하니 science ACF 와 **완전 일치**(137줄 전부, 끝 개행만 차이)했고 guide 와는 유사도 0.67 이었다. 그래서 파일을 `_science` 로 개명하고, guide 판을 ACF 에서 따로 뽑아 넣었다.

**둘이 갈리는 자리** — 골격(`Start` → `Exposure`/`Continuous` 분기, `IntUnit(IntMS)`, `NoIntUnit(NoIntMS)`)은 같은데 독출부가 다르다 [확정]:

| | science | guide |
|---|---|---|
| 노출 앞단 | `#X; CALL Prep` · `#X; CALL Flush` (둘 다 `#` 로 꺼져 있다) | 없음 |
| 수평 이송 | `X; CALL HorizontalSWShift(1200)` | `DGHIGH; CALL FrameShift(1033)` → `DGLOW; CALL HorizontalShift(600)` |
| 라인 수 | `Line(Lines)` + `SkipLine(Pre/PostSkipLines)` + `Line(OverscanLines)` | 프레임 이송 1033 = `LINECOUNT` |

⭐ guide 의 `FrameShift(1033)` 이 `LINECOUNT=1033` 과 같고, `HorizontalShift(600)` 은 `PIXELCOUNT=528` 보다 크다는 점이 눈에 띈다 — guide 의 "Pixels=600 vs 528" 논의와 같은 자리다.

다른 세션이 프레임 사이 사강 0.50초를 `NoIntMS=500` 으로 동정한 근거가 두 파일 공통의 `NOINT; CALL NoIntUnit(NoIntMS)` 줄이다.

---

### 5.7.4 ⭐ guide 의 frame transfer — 어떤 클럭으로 이루어지는가 (2026-09-03)

guide 는 **병렬 클럭 계통이 두 벌**이고, frame transfer 는 그 둘을 어떻게 조합하느냐로 이루어진다. 상태 정의(`STATEn\MODi`)를 매뉴얼 p.67 의 클럭 드라이버 형식 `d1level,d1slew,d1keep,…,d8keep`(8채널 × 3 = 24필드, **`keep=0` 일 때만 구동**)으로 풀어 확인했다 [확정].

**클럭 배선** (`KMTK_GUI_162_STA0201_R2608.acf` 의 `MODn\LABELi`) [확정]:

| 모듈 | ch | 라벨 | 역할 |
|---|---|---|---|
| **MOD3** (Driver) | 1–3 | `S1 S2 S3` | **저장부(store) 병렬 3상** |
| MOD3 | 5–7 | `I1 I2 I3` | **이미지부(image) 병렬 3상** |
| **MOD4** (Driver) | 1–3 | `R1R/R2L` `R2R/R1L` `R3R/R3L` | 직렬 레지스터 3상 (좌·우 분할 출력) |
| MOD4 | 4 | `RGR/RGL` | 리셋 게이트 |
| MOD4 | 6 | `DG` | 덤프 게이트 |

전압 상수는 병렬 `A_HIGH=12 V` / `A_LOW=0 V`(슬루 100 V/µs), 직렬 `S_HIGH=10` / `S_LOW=1`(200), `RG 12/0`, `DG 12/0`(슬루 10) 이다.

⚠️ **이름 함정** — 타이밍 스크립트의 상태 이름 `S1HIGH`/`S2LOW`/`S3HIGH` 는 MOD3 의 `S1~S3`(store)가 **아니라 MOD4 의 직렬 레지스터**를 구동한다. 상태 이름의 `S` 는 **S**erial, MOD3 채널 라벨의 `S` 는 **S**tore 다 [확정].

**병렬 상태 두 벌** — 같은 3상 6단 순서를 어디에 적용하느냐만 다르다 [확정]:

| 단계 | `IMAGE1..6` (유휴·독출용) | `FRAME1..6` (전송용) |
|---|---|---|
| 1 | S2→H | S2→H **· I2→H** |
| 2 | S1→L | S1→L **· I1→L** |
| 3 | S3→H | S3→H **· I3→H** |
| 4 | S2→L | S2→L **· I2→L** |
| 5 | S1→H | S1→H **· I1→H** |
| 6 | S3→L (+DG→0) | S3→L **· I3→L** (+DG→0) |

6단 한 바퀴가 **한 행 이송**이다. `IMAGE*` 는 store 만, `FRAME*` 는 store 와 image 를 **한 몸으로** 민다.

**전송이 일어나는 자리** (`acf_timing_script_guide.txt`):

```
X;       CALL IntUnit(IntMS)         ← 적분 (클럭 정지)
NOINT;   CALL NoIntUnit(NoIntMS)     ← 적분 종료 표시 + 사강
DGHIGH;  CALL FrameShift(1033)       ← ⭐ frame transfer
DGLOW;   CALL HorizontalShift(600)   ← 직렬 레지스터 비움
CLAMP;   X(10000)
NOCLAMP; CALL SkipLine(PreSkipLines)
FCLK;    CALL Line(Lines)            ← 독출 — VerticalShift = IMAGE* = store 만
```

`FrameShift` 는 `FRAME1;X(AT)` … `FRAME6;X(AT)` 이고 `AT=100` 이다. `CALL FrameShift(1033)` 이 1033 행을 image→store 로 통째로 민다. 100 MHz 틱으로 환산하면 행당 607 틱, 전체 **약 6.3 ms** 다 [유력 — 틱 모형은 다른 세션이 `NoIntUnit` = 정확히 100,000 틱으로 검산한 것에 기댄다].

그 뒤 `Line(Lines)` 가 부르는 `VerticalShift` 는 `IMAGE*` = **store 만** 구동한다. 따라서 **독출하는 동안 image 부는 이미 다음 노출을 적분한다** — frame transfer 의 값어치가 정확히 이 점이다 [확정].

**유휴 상태의 flush** — `Start:` 루프가 `X; CALL SkipLine` 을 계속 돈다. `SkipLine` 한 번은 `VerticalShift`(607 틱) + `HorizontalShift(600)`(40,200) + `CLAMP;X(10000)` 로 **약 0.51 ms** 이므로, store 를 초당 약 2,000 행꼴로 비운다. ⭐ **이때 구동되는 것은 `IMAGE*` 뿐이므로 image 부는 건드리지 않는다** [확정] — full-frame 계 검출기에서 유휴 flush 가 노출부를 흔들지 않는지가 관심사인데, guide 는 store 만 훑는다.

⚠️ **`DG` 의 기능 해석은 유보한다.** `DGHIGH` 로 한 번 올라간 뒤 각 행의 `FRAME6` 단계가 `DG→A_LOW`(0 V)로 내리므로 **첫 행 구간에만 실질적으로 high** 다 [확정]. 이름(dump gate)과 배치로 보면 전송 시작 시 원치 않는 전하를 드레인으로 버리는 용도로 읽히지만, **그것은 해석이고 ACF 가 말해 주는 바가 아니다** [추정]. 확정하려면 이 검출기의 데이터시트가 필요하다.

> science 는 `FrameShift`·`DG` 가 아예 없고 `HorizontalSWShift(1200)` 을 쓴다(§5.7.3) — **frame transfer 구조가 아니다.**

---

## 5.8 ⭐ 트리거·부팅 설정 키 11종과 위젯 게이팅

1차 보고서는 System 탭 체크박스에서 나가는 설정 키 11종을 다루지 않았다. 이들은 `archongui.cpp:479~500` 에서 만들어지고 `parseUI()` 의 `:2424~2444` 에서 `config` 로 들어간다 [확정].

⚠️ **핵심은 "게이팅" 이다.** 이 중 여섯 개는 **`if (!위젯->isHidden())` 로 감싸여 있어**, 위젯이 숨겨지면 **키 자체가 ACF 에 기록되지 않는다.** 숨김 여부는 `parseSystem()` 이 `BACKPLANE_TYPE`·`BACKPLANE_REV`·`BACKPLANE_VERSION` 으로 정한다(`archongui.cpp:1936~2010`).

### 5.9.1 키 · 게이팅 · 실기값

`BACKPLANE_TYPE=1`(X12) 기준이다. `j` = `BACKPLANE_REV` 정수값(표시 문자는 `'A'+j`, 즉 Rev F ↔ `j=5`, Rev H ↔ `j=7`), `build` = `BACKPLANE_VERSION` 의 셋째 절.

| 설정 키 | 위젯 라벨 | 기록 조건 | 숨김 규칙 (근거) | KMTNet 7대 | 실기 ACF 값 |
|---|---|---|---|---|---|
| `TRIGOUTFORCE` | Trigger Out Force | **무조건** | — | 기록 | `0` (12/12) |
| `TRIGOUTLEVEL` | Trigger Out Level | **무조건** | — | 기록 | `0` (12/12) |
| `TRIGOUTINVERT` | Trigger Out Invert | **무조건** | — | 기록 | `0` (12/12) |
| `TRIGOUTPOWER` | Trigger Out Power | `!isHidden()` | `j ≥ 5` 이면 **숨김** (`:2005~2008`) | **미기록** | ACF 13종 어디에도 **없음** |
| `TRIGINENABLE` | Trigger In Enable | **무조건** | — | 기록 | `0` (12/12) |
| `TRIGININVERT` | Trigger In Invert | **무조건** | — | 기록 | `0` (12/12) |
| `TRIGINEDGE` | Trigger In Edge Mode | `!isHidden()` | `build < 1179` **또는** `j < 5` 이면 숨김 (`:1967~1968`, `:1986`) | 기록 | `0` (10/12 — `for1110` 2종에만 없음, §5.7.1 참조) |
| `EXTCLOCK` | External Clock | `!isHidden()` | `j ≥ 4` 이면 **숨김** (`:1988~1990`) | **미기록** | ACF 13종 어디에도 **없음** |
| `FANDISABLE` | Fan Disable | `!isHidden()` | `j < 5` 이면 숨김 (`:1985`) | 기록 | `0` (12/12) |
| **`APPLYALL`** | **Apply All At Startup** | `!isHidden()` | `build < 1042` 이면 숨김 (`:1961~1965`) | 기록 | **`0` (12/12)** |
| **`POWERON`** | **Power On At Startup** | `!isHidden()` | 〃 | 기록 | **`0` (12/12)** |

참고로 같은 함수의 나머지 게이트도 함께 적어 둔다 — `ADXRAW`/`ADXCDS`/`PCLKDELAY` 는 `j<4` 또는 (`j≥4` 이고 `build<930`) 이면 숨김, `LINESCAN` 은 `j<4` 또는 (`j≥4` 이고 `build<1028`) 이면 숨김이다(`:1969~1999`). `IP`·`NETMASK`·`GATEWAY` 는 **게이팅 없이 무조건 기록**된다(`:2442~2444`).

⭐ **KMTNet 7대는 게이팅상 완전히 동질이다** [확정]. Rev F 는 `j=5`·`build=1252`, Rev H 는 `j=7`·`build=1261` 인데 `930`·`1028`·`1042`·`1179`·`j≥4`·`j≥5` 여섯 임계를 **모두 같은 쪽으로 통과**한다. 따라서 **7대 사이에서 ACF 를 교차로 열어도 키 가시성은 달라지지 않는다** — C16(파일 `[SYSTEM]` 이 하드웨어를 덮어씀)의 피해가 우리 자산 안에서는 키 소실로까지 번지지 않는다는 뜻이다. 다만 C16 의 나머지 위험(모듈 형 재생성·잘못된 전제로 Apply All)은 그대로 남는다.

### 5.9.2 ⭐ `APPLYALL`·`POWERON` 은 **명령이 아니라 부팅 자동 적용 설정**이다

1차 보고서 §4.4·§5.5·§11.2 는 `APPLYALL`·`POWERON` 을 **명령** 이름으로만 쓴다. 그런데 **동명의 설정 키가 따로 있고**, 그 뜻은 위젯 라벨 그대로 **"Apply All At Startup" · "Power On At Startup"** 이다 [확정]. 문서에서 반드시 갈라 적어야 한다.

- KMTNet 두 판(Rev F build 1252 · Rev H build 1261) 모두 `build ≥ 1042` 라 **위젯이 보이고 키가 실제로 저장된다** [확정].
- **실기 ACF 13종 전부 `APPLYALL=0` · `POWERON=0`** 이다 [확정].
- → **컨트롤러는 부팅 시 스스로 설정 적용도 전원 투입도 하지 않는다.** ICS 가 매번 명시적으로 `APPLYALL`·`POWERON` 을 내야 한다. §5.5(순서 의존성)의 근거를 하나 더 얻은 셈이다.
- ⚠️ 뒤집으면, 누군가 GUI 에서 이 체크박스를 켜서 저장·플래시하면 **컨트롤러가 ICS 모르게 부팅 직후 전원을 올리고 설정을 적용한다.** 우리 기동 절차의 전제(전원은 ICS 가 올린다)가 깨지므로, **ICS 는 접속 직후 `RCONFIG` 로 이 두 키가 `0` 인지 확인**하는 편이 낫다.

### 5.9.3 트리거 계통 실기 결론

`TRIGINENABLE=0` 이 13종 전부다 [확정] → **외부 트리거 입력이 어디에도 켜져 있지 않다.** 노출 개시는 전적으로 소프트웨어 경로(`LOADPARAM Exposures`, §5.9.6)다. `TRIGOUT*` 도 전부 0 이라 셔터·외부 기기로 나가는 트리거 출력도 쓰지 않는다 → **ICS 는 트리거 배선을 고려할 필요가 없다** [확정].
`TRIGOUTPOWER`(Rev ≥ F 에서 사라짐)·`EXTCLOCK`(Rev ≥ E 에서 사라짐)은 **하드웨어 세대가 지나면서 폐기된 기능**으로 보인다 [유력] — 우리 키 표에는 "현행 백플레인에서는 존재하지 않음" 으로 적어 둔다.

### 5.9.4 ⭐ §5.7.1 갱신 — `for1110`↔`for1259` 키 차이의 원인 판정

1차 보고서 §5.7.1 은 `for1259` 에만 있는 세 키(`GATEWAY`·`NETMASK`·`TRIGINEDGE`)를 "신설 기능 셋" 으로 [유력] 처리했다. **게이팅 규칙으로 설명되는지 검토한 결과는 다음과 같다.**

**(1) 이 판의 게이팅으로는 설명되지 않는다** [확정].
두 파일(`kmtnet_guide_STA0201_162_R2601_for1110.acf` ↔ `..._for1259.acf`)의 `[SYSTEM]` 을 직접 읽으면 **양쪽 다 `BACKPLANE_REV=5` · `BACKPLANE_VERSION=1.0.1252` · `BACKPLANE_TYPE=1`** 로 **완전히 같다.** 1259 판 GUI 의 규칙에 넣으면 `build=1252 ≥ 1179` 이고 `j=5 ≥ 5` 라 `cbTrigInEdge` 는 **보이고** 키는 기록된다. 즉 **같은 GUI 로 두 파일을 열면 둘 다 `TRIGINEDGE` 를 쓴다.** `GATEWAY`·`NETMASK` 는 아예 게이팅이 없다(`:2442~2444`).

**(2) 그러므로 원인은 파일을 저장한 GUI 판본이다** [유력].
`for1110` 판에는 세 위젯이 **존재하지 않았고**, `for1259` 판에서 신설됐다고 보는 것이 남는 설명이다. 1259 소스의 `build < 1179` 게이트가 그 **간접 증거**다 — `TRIGINEDGE` 는 펌웨어 빌드 1179 에서 생긴 기능이므로 빌드 1110 시절 GUI 에 있을 수 없다. `GATEWAY`/`NETMASK` 도 `APPLYNET` 계통과 함께 그 사이에 들어온 것으로 본다.
⚠️ **[확정]으로 올리지 못하는 이유**: 1110 판 GUI 소스를 갖고 있지 않다. 확정하려면 그 소스나 그 판의 릴리스 노트가 필요하다.

**(3) 파일 이름의 숫자가 무엇을 가리키는지 좁혀진다** [확정].
§5.7.1 은 "뒤 숫자는 GUI/FW 빌드 번호다" 로 두 가능성을 뭉쳐 놓았다. 그런데 **두 파일의 `[SYSTEM]` 이 똑같이 `1.0.1252`** 이므로, 숫자는 **대상 컨트롤러 FW 판이 아니라 그 파일을 저장·사용할 GUI 판**을 가리킨다. `for1110` 은 "빌드 1110 판 GUI 로 다루는 사본" 이라는 뜻이다.

**(4) §5.7.1 항목 2(역방향 위험)의 근거가 보강된다** — 등급은 **[유력] 유지**.
"1259 판 ACF 를 옛 GUI 로 열어 저장하면 세 키가 사라진다" 는 서술은, 두 파일이 **정확히 그 세 키만큼 차이 난다**는 실물 대조로 뒷받침된다. 다만 그 유실을 직접 관측한 것은 아니고 1110 GUI 소스도 없으므로 [유력] 이 맞다.

**(5) 1259 판 안에서도 같은 유실이 일어나는 조건이 있다** [확정] — 세 가지다.
① **C30**: `BACKPLANE_VERSION` 파싱 실패로 `build=0` 이 되면 `APPLYALL`·`POWERON`·`TRIGINEDGE`·`ADXRAW`·`ADXCDS`·`PCLKDELAY`·`LINESCAN` 이 통째로 빠진다.
② `BACKPLANE_REV < 5` 인 ACF 를 열면 `TRIGINEDGE`·`FANDISABLE` 이 빠진다.
③ `BACKPLANE_TYPE=2`(X16) 이면 다른 게이트 묶음이 걸린다.
KMTNet 7대는 ①~③ 어디에도 해당하지 않는다.

> **우리가 할 것.** ACF 왕복 도구는 **키 집합 차이를 원본 대비로 반드시 보고**한다. "GUI 판별 사본" 같은 것을 만들지 않고, **미지 키를 보존**하는 한 벌만 유지한다(§11.3 C3 방침).

### 5.9.5 (§5.5·§4.4 보강) `Test` 버튼 = `LOADPARAM Exposures`

```cpp
// archongui.cpp:1672~1682
void TArchonGUI::test() {
    if (!connected) { logMessage("Archon not connected."); return; }
    archon->getResult();
    archon->command("LOADPARAM", "Exposures");   // 파라미터 이름이 코드에 박혀 있다
    archon->getResult();
}
```

**stock GUI 의 노출 개시 수단이 바로 이것이다** [확정]. 파라미터 이름 `Exposures` 는 **대소문자까지 실기 ACF 와 정확히 일치**하며 13종 전부 `PARAMETERn="Exposures=0"` 를 가진다(`ContinuousExposures` 도 함께). §11.1 "우리가 맞았다" 목록에 넣을 확증이다.
※ 곁가지: `TArchonGUI::testButton()`(`:4095~4113`)은 **죽은 코드**다 — 연결 줄이 주석 처리돼 있고(`:511~512`), 게다가 파라미터 이름을 대문자 `"EXPOSURES"` 로 적어 ACF 와 어긋난다 [확정]. 벤더 소스에서 이름을 따올 때 이쪽을 집으면 안 된다.

### 5.9.6 (§7.7 정정) `MOD9_TYPE` 이 유닛마다 다르다

§7.7 science 표는 슬롯 9 를 `8`(HVXBias)로 못박았으나, 실기 ACF **7대분** 전수 대조 결과 갈린다 [확정].

| ACF | `MOD9_TYPE` | GUI 클래스 | 탭 라벨 |
|---|---:|---|---|
| `KMTC_SCI_101`(STA0284, Rev H) | **18** | `HVBIAS` | `Slot 9: HVYBIAS` |
| `KMTC_SCI_102`(STA0285, Rev H) | **18** | 〃 | 〃 |
| `KMTS_SCI_101`(STA0286, Rev H) | **18** | 〃 | 〃 |
| **`KMTS_SCI_102`(STA0287, Rev H)** | **18** | 〃 | 〃 |
| `KMTK_SCI_113`(STA0200, Rev F) | 8 | 〃 | `Slot 9: HVXBIAS` |
| `KMTK_GUI_162`(STA0201, Rev F) | 8 | 〃 | 〃 |
| `KMTS_GUI_161`(STA0291, Rev H) | 8 | 〃 | 〃 |

**science Rev H 4대(101 · 102 · KMTS-101 · KMTS-102)만 HVYBias(형 18)로 교체돼 있다.** guide 는 Rev H 여도 형 8 그대로다. GUI 는 형 4·8·18 을 같은 `HVBIAS` 클래스로 처리하고(`archongui.cpp:2136~2138`) **탭 이름만 갈라 붙이므로**(`modules.cpp:1967~1972`) 설정 키·STATUS 필드는 `HVLC_*`/`HVHC_*` 로 동일하다 → ACF 호환성 문제는 없다 [확정].
→ 조치: ICS 모듈 형 표에 **18 을 반드시 넣고**, "science = HVXBias" 서술은 **Rev F 한정**으로 좁힌다.
곁가지: `HVBIAS` UI 의 전압 칸 머리글 `"V (0..31)"` 은 **형과 무관하게 고정**이고(`modules.cpp:1860`) `QValidator` 가 붙어 있지 않다 — HVYBias 하드웨어의 실제 범위가 다르더라도 GUI 는 경고 없이 `WCONFIG` 로 내보낸다 [확정].

### 5.9.7 (§9.4 보강) ⚠️ GUI 는 온도를 **변환하지 않는다** — 라벨은 전부 "(C)"

§9.4 는 "STATUS `TEMPA` 는 K, 설정은 ℃ 이므로 변환해야 한다" 고 경고하는데, **GUI 자신이 변환하지 않는다는 사실**은 빠져 있다.

```cpp
// modules.cpp:4924~4926  (HEATERX::parseStatus)
ta = data.value(key + "/TEMPA", "-").toDouble(&ok);
if (ok) SensorA->setText(flt(ta, 0, 6));      // 원값 그대로
```
그 값을 받는 라벨은 `"Reading (C):"`(`modules.cpp:4211`), 플롯 축은 `"Temperature A (C)"`(`:4536`·`:4552`·`:4568`), 저장 머리글도 `"Temp A (C)"`(`:4843`) 다. HEATER(형 5)도 같다(`:2802~2807`, 라벨 `:2157`, 축 `:2430`/`:2445`, 머리글 `:2721`).
반면 **설정 쪽은 확실히 ℃ 다** [확정] — guide 실측 `MOD10\SENSORALOWERLIMIT=-180.0` · `MOD10\SENSORCLOWERLIMIT=-240.0` · `UPPERLIMIT=50.0`.

→ 매뉴얼(p.48 = K)과 GUI(라벨 ℃·무변환)가 **정면으로 어긋난다.** 매뉴얼은 판정 근거가 아니므로([Manual not authoritative] 원칙) **실측으로 가른다.**
**[실측대상]**: guide 컨트롤러에서 `STATUS` 의 `MOD7/TEMPA` 를 한 번 읽는다 — 약 `250` 이면 K, 약 `-23` 이면 ℃ 다. 운영자가 GUI 화면에서 읽은 온도와 우리 값을 비교할 때 이 차이를 모르면 **273 만큼 어긋난다.**

### 5.9.8 (§7.2 보강) 온도 센서 형 열거값과 실기 구성

§7.2 는 `SENSOR{A,B,C}TYPE` 키 이름만 적고 값의 뜻을 적지 않았다.

| 인덱스 | `HEATER`(형 5) `modules.cpp:2175~2178` | `HEATERX`(형 11) `modules.cpp:4224~4228` |
|---:|---|---|
| 0 | DT-670 | DT-670 |
| 1 | DT-470 | DT-470 |
| 2 | **RTD100** | **RTD100** |
| 3 | RTD400 | RTD400 |
| 4 | (없음) | **RTD1000** |

앞 4개가 두 형에서 동일하고 HEATERX 가 하나 늘린 형태라 **값 호환은 유지된다** [확정].
실기 guide 는 `MOD7_TYPE=11` · `MOD10_TYPE=11`(둘 다 HEATERX)이고 `SENSOR{A,B,C}TYPE=2` → **RTD100 6채널**이다 [확정]. 여기값은 `SENSOR{A,B,C}CURRENT=100000`, 필터는 `FILTER=0` 이다.
⚠️ 두 함정을 함께 적어 둔다.
① 읽기가 `qBound(0, …, count()-1)` 로 잘라내므로(`modules.cpp:4775~4777`) HEATERX 에서 저장한 `4`(RTD1000)를 HEATER 모듈에서 열면 **말없이 `3`(RTD400)으로 바뀐다** — 형 사이 ACF 이식 시 함정이다(C26 의 사례) [확정].
② `SENSORACURRENT` 의 **GUI 기본값은 `10000`**(`modules.cpp:4778`)인데 **실기값은 `100000`** 이다 — 키가 빠진 채 열리면 여기값이 **10배 작아진다** [확정].

### 5.9.9 (§9.4·§8.5 보강) guide 의 히터 4개는 **전부 꺼져 있다** — 온도계 전용

guide ACF 전수 확인 [확정]:
```
MOD7\HEATERAENABLE=0   MOD7\HEATERBENABLE=0   MOD7\HEATER{A,B}TARGET=0
MOD10\HEATERAENABLE=0  MOD10\HEATERBENABLE=0  MOD10\HEATER{A,B}TARGET=0
PID 게인(HEATER{A,B}{P,I,D}) 도 전부 0
```
science ACF 에는 히터·센서 키가 **0개**다(모듈 구성에 Heater 계열이 없다) [확정].
→ **Archon 은 온도 제어를 하지 않는다. guide 의 HeaterX 2장은 센서 6채널 읽기 전용으로만 쓰인다.** ICS 온도 계통 설계 판단에 직접 걸리는 사실이다.

### 5.9.10 (§8.5 표 보강) `heaterplots.txt` — 다섯 번째 고정이름 파일

```cpp
// modules.cpp:2718~2725 (HEATER) / :4840~4847 (HEATERX)
FILE *fout = fopen("heaterplots.txt","w");   // 반환값 미검사
fprintf(fout, "Time (s)\tTemp A (C)\tTemp B (C)\tTemp C (C)\n");
```
- 현재 작업 디렉터리에 **고정 이름**, 덮어쓰기 경고 없음, `fopen` 반환값 미검사(§8.6 I4 와 동종) [확정].
- **모듈마다 같은 파일명을 쓴다.** guide 는 HeaterX 가 슬롯 7·10 **두 장**이라 **한쪽 Save Plots 가 다른 쪽 결과를 지운다** [확정].
- 누적은 `parseStatus()` 안에서 일어나며(`:2820`·`:4945`) 500 ms 폴링마다 한 점, **10 000점 링버퍼**(`:2823~2828`·`:4948~4954`) → **약 83분치만 남는다** [확정].
- 버튼은 Enable/Disable Plotting · Save Plots 세 개(`:2460~2468`·`:4516~4524`). **GUI 가 제공하는 유일한 온도 추이 기록 수단**이므로 §8.5 표에 넣는다.
- 값 서식은 `%0.6lf` 라 §11.3 C9 가 지적한 `%0.0lf` 소실 문제는 여기엔 없다 [확정].

### 5.9.11 (§6.1 보강) `FRAME` 응답 키 이름과 `BUFnBASE` 기본값 함정

§6.1 이 버퍼 기점을 다루면서도 **`BUF1BASE`·`BUF2BASE`·`BUF3BASE`·`BUFnFRAME` 이라는 키 이름 자체가 본문에 한 번도 나오지 않는다** — 우리가 `FRAME` 응답을 파싱할 때 필요한 이름이다.

```cpp
// archon.cpp:1273~1277
if      (rbuf == 1) baseaddr = frameStatus.value("BUF1BASE", "2684354560").toUInt(); // 0xA0000000
else if (rbuf == 2) baseaddr = frameStatus.value("BUF2BASE", "3221225472").toUInt(); // 0xC0000000
else                baseaddr = frameStatus.value("BUF3BASE", "3758096384").toUInt(); // 0xE0000000
```
§6.1 은 `BIGBUF=1`(실기 science)에서 버퍼 2 의 기점을 **`0xD0000000`** 이라고 적었다. `FRAME` 응답에 `BUF2BASE` 가 빠지면 이 기본값 `0xC0000000` 이 쓰여 **256 MB 어긋난 주소를 FETCH 한다** [확정] — 응답이 온전한 한 드러나지 않는 잠복 결함이다.
→ 우리는 **기본값 없이 `FRAME` 응답에서 반드시 읽고, 없으면 실패**로 처리한다.

### 5.9.12 (§11.3 C3 영향범위 확대) `parseUI()` 는 저장 때만 불리지 않는다

§11.3 C3 은 "저장 시 `config` 가 위젯에서 재구성돼 미지 키가 유실된다" 로 적혀 있는데, `parseUI()` 는 **`connectClicked()` 의 첫 줄에서도 불린다**(`archongui.cpp:2663`). `moduleCommand()`(`:1823`)·`applyNet()`(`:4122`)·`testButton()`(`:4104`)도 같다 [확정].
→ **"ACF 열기 → Connect → Apply" 라는 가장 흔한 순서에서 이미 미지 키가 사라진 상태다.** C3 의 영향 범위를 "저장" 이 아니라 **"거의 모든 사용자 동작"** 으로 넓혀 적어야 한다.

### 5.9.13 한 줄 보강 묶음

| 항목 | 내용 | 근거 | 등급 |
|---|---|---|---|
| TCP 포트 | `4242` 가 **상수로 박혀 있고 UI 입력 칸이 없다**. 통신 스레드는 포트를 `0~65535` 로 검증하지만(`archon.cpp:100~106`) **그 경로는 절대 실패하지 않는다.** §3 다이어그램의 "TCP 4242" 가 바꿀 수 있는 값처럼 읽히지 않게 한 줄 붙인다 | `archongui.cpp:2667~2669` | [확정] |
| `.ncf` 슬롯 16 유실 | `saveNiceFile()` 의 VCPU 루프가 `for (i = 1; i < MAX_MODULES; i++)` → `i = 1..15`. 모듈 키는 1기점(`MOD1`~`MOD16`) 이므로 **X16 백플레인 슬롯 16 의 VCPU 코드는 `.ncf` 로 저장되지 않는다.** X12 실기에서는 드러나지 않으나 M6 과 같은 뿌리의 off-by-one | `archongui.cpp:1598` | [확정] |
| `LOCKNEWEST` 사용처 0 | 소스 전체에서 **호출처가 정확히 0곳**이다. `archon.cpp:94` 의 디스패치 분기가 유일한 등장. §6 F1 의 "GUI 자동 경로는 쓰지 않는다" 를 **"아무도 쓰지 않는다"** 로 명확히 할 수 있다 | `archon.cpp:94`·`:658~681` | [확정] |
| AD 캘리브레이션 UI 도달 불가 | `CLEARAD<n>`/`CALAD<n>,v1..v8` UI 는 `rev ≥ 'G'` **그리고** `ENABLE_AD_CALIBRATION` 둘 다여야 뜨는데 **매크로가 `0` 이라 이 빌드에서는 절대 뜨지 않는다.** 명령 이름만 적힌 §4.4 에 "이 빌드에서는 도달 불가" 를 덧붙인다 | `archon.h:5`, `modules.cpp:560`·`:658~675` | [확정] |
| `QValidator` 전무 | 설정값 입력칸에 **검증기가 하나도 붙어 있지 않다.** `"V (0..31)"`·`"Clamp (-2.5V..2.5V)"` 는 **라벨 텍스트일 뿐**이고 범위를 벗어난 값도 그대로 `WCONFIG` 로 나간다 → **범위 검증은 전적으로 ICS 몫**이다 | `modules.cpp:1860`·`:533~546` | [확정] |
| `nextFrame()` 순환 | 마지막으로 연 파일이 있는 디렉터리의 `*.raw` 를 이름순으로 훑고 **끝에 닿으면 처음으로 되돌아간다.** 목록에 `_raw.raw`(raw 채널 덤프)도 섞이므로 이미지와 raw 덤프를 같은 폴더에 저장하면 번갈아 열린다 | `archongui.cpp:3753~3765` | [확정] |
| `ATLASMOVE` 와이어 형식 | `ATLASMOVE<슬롯 0기점 2자리 16진> <모터번호> <스텝>` — `moduleCommand()` 가 `slot-1` 을 넣고(`:1825`) `atlasMove()` 가 `hex(i,2)` 로 붙인다. **`APPLYMODxx` 와 같은 0기점 2자리 16진 규약**이다. KMTNet 은 Atlas 를 쓰지 않으나 §4.4 가 "미문서 명령" 으로만 적어 두었으므로 형식 한 줄을 보탠다 | `archon.cpp:1698~1699`, `modules.cpp:3107~3133` | [확정] |
| 단축키 부재 | 단축키는 **모듈 파형 탭의 `Ctrl+C`/`Ctrl+V` 뿐**이다. 메뉴는 `&` 니모닉만 있고 Open/Save 에 `Ctrl+O`/`Ctrl+S` 조차 없다 | `modules.cpp:590~593`, `archongui.cpp:1110~1186` | [확정] |

---

# 6. 프레임 취득 사슬

## 6.1 왜 잠금이 필요한가

매뉴얼 p.15·p.71 이 근거를 제공한다 [확정]. 백플레인 DDR3 2 GB 중 512 MB 는 프로세서용이고 **위쪽 1.5 GB 가 프레임 버퍼**다.

| `BIGBUF` | 버퍼 | 크기 | 베이스 주소 |
|---|---|---|---|
| 0 | 3개 | 512 MB | `0xA0000000` / `0xC0000000` / `0xE0000000` |
| **1** (우리 science) | **2개** | **768 MB** | `0xA0000000` / `0xD0000000` (버퍼 3 미사용) |

디인터레이싱 엔진이 새 프레임을 시작하면(`PIXEL` 상승 때 `FRAME` 이 high) **잠기지 않은 다음 버퍼를 스스로 잡아서** 쓰기 시작하고, 다 차면 `BUFnCOMPLETE` 를 세운다. 따라서 호스트가 읽는 중인 버퍼를 잠가두지 않으면 **엔진이 바로 그 버퍼를 골라 덮어쓴다.** 보통 읽기용 1개 + 쓰기용 1개가 동시에 잠겨 있는 것이 정상 상태다.

실측으로도 확인됐다 [실측]: **`LOCK` 없이 fetch 하면 약 26% 확률로 엔진이 쓰는 중인 버퍼를 집어가서 두 노출이 섞인다.** → `lock_buffer=true` 로 종결한다.

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

`fetchFrame(int)` 의 인자는 **0기점 버퍼 인덱스**인데 명령은 1기점이라 `+1` 이 붙는다(`archongui.cpp:1831`) [확정]. System 탭의 Fetch 버튼 3개도 `QSignalMapper` 로 같은 슬롯에 물려 있다.

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

`framenum==0` 이거나 폭·높이가 0 이하면 그냥 `return 0` — 빈 프레임은 조용히 무시한다(`:1293~1294`).

**2단계 — 호스트 버퍼 확보** (`:1296~1335`, `frameMutex` 보호)

`frames` 벡터에서 **`Locked` 가 아니면서 `Frame` 번호가 가장 작은(가장 오래된)** 것을 고른다. 크기가 맞지 않으면 `setSize()`/`setRawSize()` 로 재할당하고, 할당에 실패한 버퍼는 후보에서 제외한다. 찾지 못하면 `"Dropped frame, no buffer available to fill"`(`:1331`).

**3단계 — 이미지 페치** (`:1337~1359`)

```cpp
s = "FETCH" + hex(baseaddr, 8) + hex(lines, 8);    // 1339
for (chunk = 0; chunk < chunks; chunk++) {
    interfaceBinaryCommand(s, p, qMin(bytes_remaining, chunk_size), ARCHON_TIMEOUT, false);
    s.clear();                                      // 1356 ← 두 번째부터 빈 명령
    ...
}
```

**`FETCH` 명령은 딱 한 번만 나가고**, 컨트롤러가 `lines` 개 블록을 쭉 흘려보내면 호스트가 **1 MiB(`chunk_size = 1024 * BURST_LEN`)** 씩 잘라 받는 구조다 [확정].

**4단계 — ⭐ raw 페치** (`:1360~1384`) — **완전히 별개의 2차 fetch 다.**

```cpp
bytes_remaining = rawsize;                          // 1361
lines  = (rawsize + line_size - 1) / line_size;     // 1362
chunks = (rawsize + chunk_size - 1) / chunk_size;   // 1363
s = "FETCH" + hex(baseaddr + rawoffset, 8) + hex(lines, 8);   // 1364
```

진행률 문구도 별도다 — 이미지는 `"Fetching frame..."`(`:1353`), raw 는 `"Fetching raw frame..."`(`:1378`). 프레임 버퍼도 이미지용(`setSize`)과 raw 용(`setRawSize`)이 별도 배열이다(`frames.h:14~15`).

**5단계 — 반납과 통보** (`:1385~1393`): `LOCK0` → `frameMutex` 잡고 `Locked=false` → `emit newFrame()`.

## 6.4 ⭐ raw 는 이미지 크기에 섞이지 않는다 — `data_bytes` 정합

이것이 우리에게 가장 중요한 확인이다 [확정].

| | ArchonGUI | 우리 `ics_archon/archon/parse.py:113` |
|---|---|---|
| 이미지 바이트 | `(samplemode ? 4 : 2) * framew * frameh` | `data_bytes = (4 if samplemode else 2) * width * height` |
| raw | **별도 2차 `FETCH`**, 주소 `baseaddr + BUFnRAWOFFSET`, 크기 `BUFnRAWBLOCKS * BUFnRAWLINES * 2048` | (안 읽음) |

**완전히 같다.** 따라서 실기 ACF 가 `RAWENABLE=1` 인데도 우리가 raw 를 읽지 않는 것은 **정상이다. 결함이 아니다.** raw 를 읽으려면 이미지 fetch 를 끝낸 뒤 두 번째 `FETCH` 를 별도로 내면 된다.

## 6.5 버퍼 관리 — 호스트 쪽

호스트 버퍼는 **딱 2개**다 — `archon->frames.resize(2)` (`archongui.cpp:1230`) [확정]. 컨트롤러 쪽 3개(또는 BIGBUF 2개)와 별개다.

이중 잠금 구조:

| 층 | 무엇을 지키나 |
|---|---|
| `frameMutex` (public) | `frames` 벡터의 메타데이터(`Locked`, `Frame`) 갱신을 원자적으로 |
| `TFrameBuffer::Locked` (bool) | 그 버퍼의 픽셀 데이터를 지금 누가 쓰고 있는지 — 뮤텍스가 아니라 소유권 표식 |

**Archon 스레드는 가장 오래된 것을 잡고, GUI 는 가장 최신 것을 잡는다.** 서로 반대쪽 끝을 무는 구조다 [확정]:

```cpp
// archon.cpp:1298~1326  — 생산자: Locked 아닌 것 중 Frame 최소
// archongui.cpp:3138~3187 — 소비자: Locked 아닌 것 중 Frame 최대
archon->frameMutex.lock();
archon->frames[displayindex].Locked = false;   // 이전 표시 버퍼 반납
updateDiffStats(displayindex, newindex);
archon->frames[newindex].Locked = true;        // 새 표시 버퍼 점유
archon->frameMutex.unlock();
```

⚠️ **여유가 없는 설정이다.** GUI 가 표시용으로 1개를 점유하고 있으면 남는 것은 1개뿐이다. 그리고 `updateDiffStats()` 가 `frameMutex` 를 쥔 채 이미지 연산을 수행한다(`:3164`) — 그동안 Archon 스레드의 `fetchFrame` 이 버퍼 확보 단계에서 대기한다. 정합성은 맞지만 **페치가 GUI 연산에 물리는 구조**다 [확정].

## 6.6 `TFrameBuffer` — 필드와 재사용 규칙

| 필드 | 형 | 실제 동작 |
|---|---|---|
| `NewFlag` | bool | **죽은 필드.** 선언 한 줄뿐이고 읽지도 쓰지도 않는다. 생성자에서 초기화조차 하지 않는다 |
| `Frame` | int | `BUFnFRAME` 값. **비어있음 표시로 -1**. "가장 오래된 버퍼 고르기" 의 정렬 키 |
| `Data` | `unsigned short*` | 디인터레이스 끝난 **이미지** 픽셀. HDR 일 때는 소비자가 `quint32*` 로 캐스팅 |
| `RawData` | `unsigned short*` | raw 샘플. **항상 16bit** — HDR 개념이 아예 없다 |
| `Locked` | bool | 소유권 표식 |
| `m_width`/`m_height` | int | **바이트가 아니라 표본 수** |
| `m_rawwidth`/`m_rawheight` | int | raw 치수. `rawwidth = rawblocks * 2048/2 = rawblocks × 1024 샘플` |
| `m_hdr` | bool | "표본이 16bit 대신 32bit" 플래그 |

재사용 판정이 흥미롭다 [확정] (`frames.cpp:157`, `:172`):

```cpp
if ((m_width == width) && (m_height == height) && (m_hdr == hdr) && Data) return 0;  // 그대로 씀
...
else if ((m_width * m_height != width * height) || (m_hdr != hdr))                   // 이때만 free+malloc
```

즉 **가로세로가 바뀌어도 `w*h` 곱이 같고 표본 폭이 같으면 재할당을 하지 않는다.** science 한 장이 수백 MB 급이라 프레임마다 malloc/free 를 반복하지 않으려는 것이다.

## 6.7 픽셀 해석 — 16bit / 32bit(HDR)

분기의 유일한 원천은 **`SAMPLEMODE`** 다. 사슬 전체 [확정]:

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

**실기(`SAMPLEMODE=0`)에서는 32bit 경로를 한 번도 타지 않는다.** KMTNet 운영에서 HDR 코드는 죽은 경로다 [확정].

raw 는 `SAMPLEMODE` 와 무관하게 **항상 16bit** 다.

## 6.8 이진 전송 상수와 타임아웃

| 상수 | 값 | 의미 |
|---|---|---|
| `BURST_LEN` (`archon.h:17`) | **1024** | 프로토콜이 못박은 이진 블록 크기(매뉴얼 p.45). `FLASH` 한 번의 바이트 수이자 `FETCH`/`VERIFY` 의 카운트 단위 |
| `RAW_BLOCK_SIZE` (`archon.h:20`) | **2048** | raw 블록 크기. `BURST_LEN` 과 **무관한 별개 단위** |
| `chunk_size` (`archon.cpp:1254`) | `1024 * BURST_LEN` = **1 MiB** | `interfaceBinaryCommand` 한 번에 받는 양 |

`RAW_BLOCK_SIZE=2048` 이 매뉴얼 p.70 의 "rounded up to the next even block size (a multiple of 1024)" 와 맞물린다 — 샘플이 16비트이므로 **1024 샘플 = 2048 바이트 = raw 블록 1개**다. science `RAWSAMPLES=8192` = 정확히 8블록, `RAWSTARTLINE=300`/`RAWENDLINE=400` → 101 라인 → raw 크기 8×101×2048 ≈ **1.65 MB** [확정].

이진 오버로드 두 개의 결정적 차이 [확정]:

| | (a) `QByteArray&` (`:385~455`) | (b) `char*, int length` (`:457~545`) |
|---|---|---|
| 받는 양 | **정확히 1블록** | `length` 만큼 **여러 블록 연속** |
| 타임아웃 | 재시작 없음 — 2초 안에 1024 B 를 받지 못하면 실패 | **무음 구간 기준** — 바이트 올 때마다 `t.start()`(`:521`) |
| 꼬리 | — | `qMin(BURST_LEN, length)` 로 딱 필요한 만큼만 복사. 남는 바이트는 `interfaceFlush()` 가 정리한다 |
| 쓰임 | `verify()`, `verifyMod()` | **`fetchFrame()` 뿐** |

(b)의 무음 기준 타임아웃이 **수백 MB 페치가 5초 제한에 걸리지 않는 이유**다.

## 6.9 실측 수치

[실측] (2026-09-01~02 KASI 벤치, `ics_archon/archon_lock_fetch_report.md`):

| 항목 | 값 |
|---|---|
| 독출 속도 | **368.0 행/초** (FETCH 중에도 이 만속을 유지한다) |
| 4700행 독출 | 12.77 초 |
| 프레임 주기 | 13.27 초 |
| FETCH 344.2 MiB | 3.2~3.5 초 (약 100 MiB/s) |
| `LOCKn` 반영률 | 15/15. fetch 를 느리게 하지도 엔진을 멈추지도 않는다 |
| `BUFnFRAME` 리셋 | **`REBOOT` 만.** `WARMBOOT`·CCD `POWEROFF/ON` 은 프레임 번호가 이어진다 |

⭐ **GUI 의 "독출 정지" 는 표시 착시였다.** 재관측에서 라인 표시가 10 → 1500 으로 점프했는데, 1490행 ÷ 368 = 4.05초 = FETCH 시간이다. 기전은 §7.5 의 "폴링 버려짐" 이다.

## 6.10 프레임 사슬의 결함

| # | 내용 | 위치 | 등급 |
|---|---|---|---|
| F1 | `lockNewestFrame()` 이 **`BUFnCOMPLETE` 를 보지 않는다** — 채워지는 중인 버퍼를 잠글 수 있다. GUI 자동 경로는 `parseFrameStatus()` 가 `framecomplete[i]` 를 확인하고 `LOCK`+번호를 직접 지정하므로 이 함수를 사용하지 않는다 | `archon.cpp:658~681` | 하(잠복) |
| F2 | 호스트 프레임 버퍼가 **2개뿐** — GUI 표시 중 새 프레임이 오면 여유가 없다 | `archongui.cpp:1230` | 하 |
| F3 | `openHDRFrame()` 이 read 실패 경로에서 **`frameMutex.unlock()` 을 하지 않는다** → **교착.** 이후 프레임 수신이 통째로 멈춘다. `openFrame` 쪽은 제대로 해제한다 | `archongui.cpp:3804·3816~3821` | **높음(실버그)** |
| F4 | `TFrameBuffer` 복사 생성자가 `other.Data==0` 분기에서 **`RawData`·`m_rawwidth`·`m_rawheight`·`m_hdr` 를 미초기화** → 나중에 쓰레기 포인터를 `free()` 한다. 지금은 값 복사가 일어나지 않아 문제가 드러나지 않는다 | `frames.cpp:23~26` | 하(잠복) |
| F5 | 픽셀 복사가 `memcpy` 가 아니라 **원소 단위 for 루프** | `frames.cpp:38~39` 등 | 하(성능) |
| F6 | 자동 페치가 **폴링 콜백 안에서** `getResult()` 로 GUI 를 블로킹 | `archongui.cpp:2411` → `:1838` | 하 |

---

# 7. 모듈 체계

## 7.1 ⭐ 형 번호표 (정본)

**정본은 `archon.h:29~48` 이다.** 매뉴얼 p.46 은 15까지만 유효하고, 6 이 빠졌고, 16~18 이 틀렸다 [확정].

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

**구현이 없는 형은 없다.** 실 모듈 형 1~18 전부 대응 클래스가 있고, 3형이 클래스를 공유한다(8·18 → `HVBIAS`, 9 → `LVBIAS`). 형 18종 → 클래스 15개. 디스패치는 `archongui.cpp:2127~2149` 의 `switch(id)` 딱 한 곳이다 [확정].

공유 클래스는 **탭 라벨만** 형 번호로 갈라 붙인다 — 설정 키도 STATUS 필드도 전부 `HVLC_*`/`HVHC_*`, `LVLC_*`/`LVHC_*` 로 똑같다. 실기 science 의 MOD9=8(HVXBias) 도 GUI 상으로는 그냥 HVBIAS 취급이다 [확정].

## 7.2 클래스 계층과 채널 수

계층은 완전히 평평하다 — `TModule`(순수 가상 7개) → 파생 15개, 2단계 끝. 중간 계층도 헬퍼 기반 클래스도 없어서 DIO 8채널 블록이나 VCPU 16레지스터 블록이 **클래스 5개에 통째로 복붙**돼 있다 [확정].

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

VCPU 를 가진 클래스 = DIO 를 가진 클래스 = `applyModuleDIO` 를 부르는 클래스로 **완전히 겹친다** — `LVBIAS`·`HEATER`·`HS`·`LVDS`·`HEATERX` 다섯이다 [확정].

바이어스 네 접두의 뜻 [확정]:

| 접두 | 풀이 | 채널 | 라벨 | 전압 범위 | 채널당 전류 |
|---|---|---:|---|---|---|
| `LVLC_*` | **L**ow **V**oltage / **L**ow **C**urrent | 24 | LV1–LV24 | −14.000 … +14.000 V | 10 mA |
| `LVHC_*` | Low Voltage / **H**igh **C**urrent | 6 | LV25–LV30 | −14.000 … +14.000 V | **500 mA** |
| `HVLC_*` | **H**igh **V**oltage / Low Current | 24 | HV1–HV24 | 0.000 … +31.000 V | 10 mA |
| `HVHC_*` | High Voltage / High Current | 6 | HV25–HV30 | 0.000 … +31.000 V | **250 mA** |

모듈 한 장당 **30채널**이고, **모듈 전체 합계 전류는 1 A 를 넘지 못한다** (매뉴얼 p.11, p.29, p.31).

## 7.3 ⭐ `ADM` 은 사실상 빈 껍데기

KMTNet science 에 직결되는 중요한 사실이다 [확정]. `ADM` 클래스(`modules.cpp:1228~1276`)는 전부가 이렇다:

- `createUI()`: `systemTabs()` 에 **빈 `QWidget` 탭 하나** 붙이고 `"Slot n: ADM"` 이름표만 달고 끝
- `parseUI()` / `updateUI()`: **본문 없음** → 설정 키를 하나도 만들지 않고 읽지 않는다
- `setClocks()`/`getClocks()`/`clockChanged()`/`copyClocks()`/`pasteClocks()`: 전부 no-op
- `parseStatus()`: 빈 함수
- `waveformTabs`/`vcpuTabs` 에 **아무것도 안 붙임**
- `usesClocks()` 만 **`false`** 를 돌려준다 — 15개 중 유일하다
- 유일한 멤버 `rev` 는 생성자에서 채워지고 **어디서도 쓰이지 않는다** (죽은 코드)

그래서 science 실기의 MOD5·MOD8 ADM 은 GUI 상 **탭 이름 말고는 아무 조작 지점이 없다.** 클램프도, 프리앰프 게인도, 클록도, 상태 표시도 없다. 실기 science ACF 에 `MOD5\…`/`MOD8\…` 키가 **0개**이고 `STATE0\MOD5`/`STATE0\MOD8` 도 아예 없는 것이 정상인 이유가 이것이다 [확정].

ADM 채널 설정은 전적으로 `[TAPLINES]` 와 CDS/Deint 탭(SHP/SHD, RAWSEL, PIXELCOUNT/LINECOUNT, FRAMEMODE, SAMPLEMODE) 쪽에서만 이뤄지고, 나머지는 펌웨어 몫이다.

> ⚠️ 그래서 **ADM 의 clamp/gain 을 설정할 수단이 있는지 자체가 [확인불가]** 다. GUI 에 UI 도 설정 키도 없고 ACF 에도 없다. 정말 무설정인지, 다른 경로가 있는지 확인하지 못했다.

## 7.4 설정 키 인덱스 규약

| 대상 | 기점 | 예 |
|---|---|---|
| 슬롯 `<n>` (설정·STATUS·SYSTEM) | **1기점** | `MOD5/CLAMP1`, `MOD5_TYPE`, `MOD5/TEMPA` |
| 채널 `<m>` (대부분) | **1기점** | `LABEL1..8`, `LVLC_V1..24`, `LVDS_LABEL1..16` |
| 리스트 줄 번호 | **0기점** | `LINE<n>`, `PARAMETER<n>`, `CONSTANT<n>`, **`TAPLINE<n>`**, `STATE<n>`, `VCPU_LINE<j>` |
| VCPU 레지스터 | **0기점** | `VCPU_INREG0..15`, `VCPU_OUTREG0..15`. GUI 라벨도 `REG0`..`REG15` |
| **명령의 슬롯 인자** | **0기점 2자리 16진** | 슬롯 5 → `APPLYMOD04`, `APPLYDIO04` |

DIO 방향 키만 형태가 두 갈래다 [확정]:
- 8채널짜리(LVBIAS/HEATER/HEATERX): **`DIO_DIR12`, `DIO_DIR34`, `DIO_DIR56`, `DIO_DIR78`** (두 채널 묶음)
- 4채널짜리(HS/LVDS): **`DIO_DIR1`..`DIO_DIR4`**

콤보박스 값은 전부 `currentIndex()` 라서 **문자열이 아니라 정수**로 저장된다 — `DIO_SOURCE` 0=Low/1=High/2=Clocked/**3=VCPU**, `DIO_DIR` 0=Input/1=Output, `DIO_POWER` 0/1, AD `PREAMPGAIN` 0=LOW/1=HIGH.

## 7.5 펌웨어 빌드 게이팅 — ACF 호환성의 핵심

모듈 생성자가 `MOD<slot>_VERSION` 의 세 번째 필드를 `build`, `BACKPLANE_VERSION` 세 번째를 `backplane_build` 로 담아두고, **위젯과 키를 통째로 켜고 끈다** [확정]:

| 조건 | 효과 |
|---|---|
| `DRIVER` `SOURCE` 열: `build ≥ 1063 && backplane_build ≥ 1064` | 조건 미달이면 `SOURCE<m>` 키가 **아예 생기지 않는다** |
| `HVBIAS` 파형 탭: `build > 832` | 미달이면 `STATE<n>/MOD<i>` 에 **그 키가 통째로 사라진다** |
| `LVBIAS` 상태 CSV: `build ≥ 833` | 16필드 → **19필드** (뒤에 `biasCmd, biasChannel, biasVoltage`) |
| `XVBIAS` 파형 탭: `build ≥ 1090` | 6필드 추가 |
| `AD` 클램프: `MOD_REV ≤ 'C'` | `CLAMPHIGH`/`CLAMPLOW` 2키 vs `CLAMP1..4` 4키 |
| `HEATERX` 필터: `build ≥ 1046 && backplane ≥ 1049` | `SENSORxFILTER` |

> **결과적으로 같은 ACF 라도 붙어 있는 보드의 펌웨어 빌드에 따라 GUI 가 만들어 내는 키 집합이 달라진다.** ACF 호환성을 판단할 때 반드시 기억해야 할 지점이다.

실기 검증 [확정]: science `MOD*_VERSION=1.0.1175 ≥ 1063`, `BACKPLANE_VERSION=1.0.1252 ≥ 1064` → `SOURCE` 키가 나오는 것이 앞뒤가 맞다. `STATE0\MOD4` = **19필드**(LVXBias, ≥833), `STATE0\MOD9` = **3필드**(HVXBias, DIO 없음), `STATE0\MOD1` = **40필드**(LVDS 16×2 + DIO 4×2) — 코드와 정확히 일치한다.

## 7.6 상태(state) 편집 구조

타이밍 상태 하나 = `lwStates` 의 `QListWidgetItem` 하나. `Qt::UserRole` 에 `QVariantMap` 이 붙어 있다 [확정].

- `"NAME"` — 상태 이름 (저장할 때 **맵이 아니라 목록 위젯 텍스트**로 덮어씀)
- `"CONTROL"` — `"<clock16진>,<keep16진>"`. `CONTROL_COUNT = 6` 비트: **Bit0=INT, 1=FRAME, 2=LINE, 3=PIXEL, 4=TRIGA, 5=TRIGB**
- **`"MOD<slot>"`** — 모듈 하나가 통째로 차지하는 **쉼표 구분 CSV 한 줄**. 위치 기반 인코딩이라 **필드 순서와 개수가 곧 스키마**이고 이름표는 실리지 않는다

평탄화되면 `STATE<i>/CONTROL`, `STATE<i>/MOD5`, `STATE<i>/NAME` 이 된다 — 매뉴얼 p.55·p.67 과 일치한다.

`stateChanged()` ↔ `clockChanged()` 무한 재귀는 `clock_lock` 이라는 bool 하나로 막는다. 둘 다 GUI 스레드 전용이라 그것으로 충분하다. **`getClocks` 는 항상 전 모듈을 훑는다** — 한 채널만 고쳐도 그 상태의 모든 모듈 CSV 가 다시 쓰인다 [확정].

기본값이 `"FF"` 다 — CONTROL 키가 없는 상태는 6비트 전부 1로 읽혀서 **"모든 클럭 체크 + 모든 Keep 체크"** 가 된다. 즉 **미지정 = 이전 값 유지**가 기본이고, 새 상태를 만들면 전부 Keep 으로 시작한다.

⚠️ 클립보드 복붙(`Ctrl+C`/`Ctrl+V`)에 **탭 이름이나 모듈 형 검사가 전혀 없다** — DRIVER 탭에서 복사한 것을 LVDS 탭에 붙여도 그냥 위치대로 들어간다. 그리고 **상태 이름 중복 검사가 어디에도 없다** [확정].

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
- Driver 4장 × 8채널 = **32채널**. ACF 의 `LABEL`/`FASTSLEWRATE`/`SLOWSLEWRATE`/`ENABLE`/`SOURCE` 가 각각 32개인 것이 정확히 이것이다 [확정].
- **VCPU 탭이 뜨는 것은 슬롯 1(LVDS)과 슬롯 4(LVXBias) 둘뿐**이다.
- **Driver 4장과 ADM 2장은 모듈 STATUS 표시가 0개**다. 온도 `MOD<n>/TEMP` 만 부모(`archongui.cpp:2340~2342`)가 찍는다.

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
| M1 | **`VCPU_INREG` off-by-one.** 쓰기는 `.arg(i)`(0기점), 읽기는 `.arg(i+1)`(1기점). **5개 클래스 전부** 같은 버그(복붙 탓). ACF 왕복에서 VCPU 입력 레지스터가 **한 칸 밀리고 마지막 하나를 잃는다** | `modules.cpp:1640` vs `:1681`, `:2624`/`:2691`, `:3583`/`:3615`, `:3998`/`:4026`, `:4737`/`:4812` | **중(잠복)** |
| M2 | `TModule` 에 **가상 소멸자 없음.** 기반 포인터로 `delete` — 현재는 파생이 할 일이 없어 사고는 나지 않지만 UB | `modules.h:9~26`, `archongui.cpp:2123` | 하 |
| M3 | `usesClocks()` 가 **순수 가상인데 호출하는 곳이 0곳** — 죽은 인터페이스 | `modules.h:17` | 정보 |
| M4 | `DRIVER::updateUI()` 가 `leSlowSlewRates[i]->setText()` 를 **두 번** 호출 (DriverX 도 동일: `:414`·`:416`) | `modules.cpp:176`, `:178` | 정보 |
| M5 | `DRIVERX` 는 `Source` 열 UI 를 **조건 없이 만드는데** parseUI/updateUI 는 `build≥1063` 로 막는다 → 구펌웨어에서 칸은 보이는데 저장이 안 된다. `DRIVER` 는 UI 생성도 같이 막아서 **일관성이 없다** | `modules.cpp:311~313` vs `:403` | 하 |
| M6 | `MAX_MODULES=16` 이라 12슬롯(X12) 백플레인에서도 모듈 12~15 를 허용. 실제 방어는 `MOD<n>_TYPE` 이 비어서 걸리는 것뿐 | `archon.h:27` | 하 |
| M7 | `ATLAS` 의 STATUS 키는 `TEC_ENABLE`(밑줄 있음)인데 설정 키는 `TECENABLE`(밑줄 없음) — 오타가 아니라 실제로 그렇다 | `modules.cpp:3213` vs `:3088` | 정보 |
| M8 | `HEATERX` 의 STATUS 온도 필드는 `TEMPA/B/C` 인데 UI 라벨과 설정 키는 `SENSORA/B/C` 계열 — 이름 체계가 STATUS 와 CONFIG 사이에서 어긋난다 | `modules.cpp:4924` vs `:4699` | 정보 |
| M9 | `HEATERAP`/`AI`/`AD` 가 **설정 키(PID 게인)로도, STATUS 필드(현재 P/I/D 항 기여분)로도** 같은 문자열을 쓴다. 맵이 달라서 충돌은 나지 않지만 문서에서 헷갈리기 딱 좋다 | `modules.cpp:2579~2586` vs `:2814~2816` | 정보 |

---

# 8. 영상·해석 기능

## 8.1 표시

| 기능 | 동작 | 근거 |
|---|---|---|
| 이미지 모드 | **Nearest(0) / Max(1) / Min(2)**. 다운샘플 박스 안에서 `qMax`/`qMin` | `archongui.cpp:812~814`, `imagewidget.cpp:431` |
| ⚠️ 모드가 먹히는 조건 | **`zoom ≥ 1.0` 이면 모드를 통째로 무시하고 무조건 Nearest.** 즉 **축소할 때만** Max/Min 이 의미 있다 | `imagewidget.cpp:98`, `:156` |
| raw 경로 | **모드 분기가 아예 없다.** 항상 Nearest, 항상 16bit | `imagewidget.cpp:75~88` |
| LUT | 16bit: `grayscale[65536]`, HDR: `grayscalehdr[1048576]`(값 `>>12`, 상위 20bit) | `imagewidget.cpp:412~427` |
| 게인 슬라이더 | 이미지 −1000~1000 → `exp(v/100)` (e^±10). **raw 는 `exp(v/200)`** (e^±5) — 감도 절반 | `archongui.cpp:3009~3016`, `:3122~3129` |
| 오프셋 | −65535~65535. **HDR 만 ×16** (16bit 눈금을 20bit 공간으로 환산) | `imagewidget.cpp:425` |
| `fitGainOffset()` | 신호 박스(없으면 전체)의 min/max 로 화면 0~255 를 꽉 채우게 자동 맞춤. **raw 탭엔 없다** | `archongui.cpp:3025~3089` |
| 확대 | ×2 / 1:1 / ÷2. `ImageScrollWidget::setZoom` 이 **중심 픽셀을 유지**하도록 스크롤바를 다시 놓는다 | `imagescrollwidget.cpp:23~37` |

⚠️ 매 `setLUT` 호출마다 **1,114,112칸 LUT 를 통째로 다시 계산한다.** 슬라이더가 `setTracking(true)` 라 드래그 중 계속 돈다 — 느린 이유가 이것이다 [확정].

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

> ⚠️ **표준편차가 N 나눗셈(모집단)이다.** N−1 이 아니다. 작은 박스에서는 읽기잡음을 살짝 낮게 준다. 잡음 측정용으로 쓸 때 알아두어야 한다.

`updateDiffStats(prev, next)` (`:3325~3439`) [확정]:

```
diffmean = Σ(f1-f2) / N
diffvar  = Σ(f1-f2-diffmean)² / (2N)      ← ★ 2로 나눠
```

**2N 나눗셈이 핵심**이다. 독립인 두 프레임을 빼면 분산이 2배가 되므로 되돌리는 것이고, 그래서 `diffvar` 는 **고정패턴잡음(FPN)이 상쇄된 한 프레임의 잡음 분산 추정치**다. 두 프레임의 크기·HDR 이 다르면 조기 반환한다.

## 8.3 플롯

```
수평: hy[i] = Data[m_hplot*w + i]      (i=0..w-1)
      H Avg 체크 → hy[i] = mean_{j=y1..y2} Data[j*w+i]   (신호 박스의 세로 구간 평균)
수직: vy[i] = Data[i*w + m_vplot]      (i=0..h-1)
      V Avg 체크 → vy[i] = mean_{j=x1..x2} Data[i*w+j]
```

raw 판(`updateRawStats` `:3898`, `updateRawPlots` `:3965`)은 구조는 같은데 **HDR 분기가 없고**(raw 는 항상 16bit) `dv`/DR 계산도 없다. x축 제목만 `ADXRAW` 에 따라 갈린다 [확정]:

- `ADXRAW=0` → **"Sample (10ns)"** — 100 MHz
- `ADXRAW=1` → **"Sample (2.5ns)"** — 400 MHz

우리 science 는 `ADXRAW=0` 이라 10 ns 축이다. ⚠️ **ADM 전용 눈금이 없다.** ADM 은 12.5 MHz 로 샘플해서 18비트를 16비트로 자른 뒤 **8번 복제(디더링 섞어서)** 하므로(매뉴얼 p.12, p.69), **ADM raw 는 10 ns 축에 그려지지만 실제 유효 샘플은 8틱마다 하나**다. 파형 읽을 때 감안해야 한다 [확정].

> 그래서 매뉴얼 p.69 가 **SHP/SHD 를 8의 배수로 두라고 권고한다.** science ACF 의 `SHP1=72 SHP2=112 SHD1=136 SHD2=200` 은 **전부 8의 배수**다 — 규약을 지키고 있다 [확정].

## 8.4 PTC (Photon Transfer Curve)

축은 **x = Signal [ADU], y = Variance [ADU²]**, 선형축이다(`archongui.cpp:940~941`) [확정].

| 함수 | 하는 일 |
|---|---|
| `snapPTC()` (`:3570`) | 누적 개시만. `ptccount = ptctotal = N`, `ptcmean = ptcvar = 0`. **계산이 여기 없다** |
| **누적 본체** (`:3392~3438`) | **`updateDiffStats()` 안에 숨어 있다.** 새 프레임마다 `ptcmean += (신호박스평균 − 노이즈박스평균)`, `ptcvar += diffvar`, `ptccount--`. 0 이 되면 `ptctotal` 로 나눠 점 하나 삽입 |
| `resetPTC()` (`:3579`) | 점 전부 날린다 |
| `savePTC()` (`:3587`) | **현재 작업 디렉터리에 고정 이름 `ptc.txt`**. 경로 선택도, 덮어쓰기 경고도, `fopen` 실패 검사도 없다 |

⭐ **게인(e−/ADU)은 코드 어디에도 없다** [확정]. `ptcx`/`ptcy` 를 쓰는 곳은 삽입·그리기·저장뿐이고, 기울기 적합도 역수도 `e-/ADU` 라는 문자열도 없다. **GUI 는 축만 그린다.** 게인은 사람이 밖에서 내야 한다:

```
광자잡음 지배 구간에서  Var = Signal / g   (g = e-/ADU)
→  g = 1 / (PTC 기울기)
```

읽기잡음(y절편)도 풀웰(꺾이는 지점)도 GUI 는 알려주지 않는다.

PTC 쓸 때 조심할 것 [확정]:

1. 첫 프레임은 그냥 넘어간다 — 누적이 `updateDiffStats` 에서 일어나고 그것은 **직전 표시 프레임이 있을 때만** 불린다.
2. `diffvar` 는 "직전 표시 프레임 − 새 프레임" **연속 쌍**마다 계산된다. 프레임 2,3,4 를 받으면 (2,3),(3,4) 두 쌍이고 3이 양쪽에 들어간다 — **쌍이 독립이 아니다.** 평균은 맞지만 오차 추정엔 편향이 있다.
3. 두 프레임의 크기나 HDR 이 다르면 `updateDiffStats` 가 조기 반환하는데 **`ptccount` 는 줄지 않는다** → 설정을 바꾸면 PTC 누적이 조용히 멈춘 채 남는다.
4. 노이즈 박스를 그리지 않았으면 1픽셀 평균이 바이어스로 쓰인다. **신호 박스와 노이즈 박스를 둘 다** 제대로 잡아야 한다.

## 8.5 파일 입출력

### `.raw` — 헤더 없는 순수 덤프

```
저장: <leBaseFilename>_<w>x<h>_<frame>.raw
내용: Data 를 그대로 write. HDR 이면 4바이트/샘플, 아니면 2바이트/샘플.
raw:  <Base>_<w>x<h>_<frame>_raw.raw  — 항상 2바이트/샘플
```

**메타데이터가 하나도 없다. 치수는 오직 파일 이름에만 들어 있다** [확정]. 읽을 때는 정규식 `_(\d+)x` 로 폭을 뽑고, 뽑지 못하거나 `size % w != 0` 이면 대화상자로 물어본다. `h = size / w`, **항상 16비트로 가정**한다.

`saveSequence()` 는 `savecount` 만 세팅하고 `newFrame()` 이 그만큼 자동 저장한다. `cbSaveAll` 은 무제한.

### FITS — 별도 경로, 엔지니어링용

`saveFITS()` (`:4150~4254`)가 쓰는 헤더는 **딱 7개**다 [확정]:

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

> ⚠️ **노출시간·온도·타임스탬프·탭 구성·게인/오프셋·관측 대상 — 아무것도 없다.** 이 GUI 의 FITS 는 **엔지니어링 확인용**이지 관측 산출물이 아니다. KMTNet raw spec 이 요구하는 헤더는 ICS 쪽에서 따로 만들어야 한다.
> 그리고 **`saveFITS`/`openFITS` 는 이미지 프레임 전용**이다. **raw 프레임을 FITS 로 내보내는 경로가 없다** — raw 는 `.raw` 덤프뿐이다.

`openFITS()` 는 `BITPIX`/`NAXIS1`/`NAXIS2` **세 개만** 해석하고 `BZERO`/`BSCALE` 도 읽지 않는다 — 즉 **자기가 쓴 FITS 만 제대로 읽는다** [확정].

### 플롯 txt

| 함수 | 파일 (고정 이름, 현재 작업 디렉터리) | 헤더 | 서식 |
|---|---|---|---|
| `saveHPlot` / `saveVPlot` | `hplot.txt` / `vplot.txt` | `Pixel\tSignal` | **`%0.0lf`** |
| `saveRawHPlot` / `saveRawVPlot` | `rawhplot.txt` / `rawvplot.txt` | 〃 | **`%0.0lf`** |
| `savePTC` | `ptc.txt` | `Signal\tVariance` | `%0.6lf` |

> ⚠️ 플롯 4종이 **`%0.0lf` — 소수점을 버린다.** H/V Avg 로 평균낸 값도 정수로 잘린다. **평균 잡음 분석에 이 파일을 쓰면 안 된다.** PTC 만 소수 6자리로 살아 있다 [확정].
> ⚠️ 다섯 함수 전부 **`fopen` 반환값을 검사하지 않는다** — 쓰기 권한 없는 디렉터리에서 실행하면 널 역참조로 죽는다.

## 8.6 영상 계통의 결함

| # | 내용 | 위치 | 등급 |
|---|---|---|---|
| I1 | `openHDRFrame()` read 실패 시 `frameMutex.unlock()` 누락 → **교착** | `archongui.cpp:3804·3816~3821` | **높음** |
| I2 | `ImageWidget::m_mode` **생성자 초기화 누락** + 콤보 연결이 `addItem` **뒤**라 최초 `currentIndexChanged(0)` 를 받지 못한다. 사용자가 콤보를 한 번도 건드리지 않으면 미정의값 → **축소하는 순간 Max/Min 중 아무 쪽으로 튄다.** 확대 상태에선 드러나지 않는다 | `imagewidget.cpp:6~35`, `archongui.cpp:812~815` | 중 |
| I3 | 플롯 txt 가 `%0.0lf` — 평균값 소수점 소실 | `:3596`/`:3605`/`:4051`/`:4060` | 중 |
| I4 | `fopen` 실패 미검사 → 널 역참조 | 위 4개 + `:3587` | 중 |
| I5 | 크기/HDR 불일치로 `updateDiffStats` 조기 반환할 때 `ptccount` 를 줄이지 않아 → PTC 누적이 조용히 멈춤 | `:3336~3343` vs `:3394` | 중 |
| I6 | `zoomFit()` 이 raw 치수를 무시하고 `f->width()/height()` 사용. 지금은 raw 탭에 버튼이 없어 잠복 | `imagescrollwidget.cpp:45~58` | 하 |
| I7 | `openFITS` 가 `BZERO`/`BSCALE` 무시 → 외부 FITS 오독 가능 | `:4256` | 하 |
| I8 | `openFrame()` 두 판이 60여 줄 중복 | `:3614` / `:3686` | 하 |
| I9 | 65536칸 `vx`/`vy` 를 만들고 안 씀 — 히스토그램 잔해 | `:3237~3240`, `:3913~3916` | 정보 |
| I10 | `openHDRFrame` 은 `do-while` 이라 파일명에 폭이 박혀 있어도 **무조건 한 번 물어본다**. `openFrame` 의 `while` 과 다르다 | `:3790~3799` | 정보 |

---

# 9. 전원·감시

## 9.1 `POWER` 상태 6종

`archon.h:52` 의 `POWER_STATES` 와 매뉴얼 p.47 이 일치한다 [확정].

| 값 | 상수 | 매뉴얼 뜻 | GUI 표시등 색 | 툴팁 |
|---:|---|---|---|---|
| 0 | `PWR_UNKNOWN` | "usually an internal error" | 짙은 회색 | UNKNOWN |
| 1 | `PWR_NOT_CONFIGURED` | "no configuration applied" (= APPLYALL 전) | 회색 | NOT CONFIGURED |
| 2 | `PWR_OFF` | "power to the CCD is off" | **빨강** | OFF |
| 3 | `PWR_INTERMEDIATE` | "some modules have enabled power to the CCD, some have not" | 노랑 | INTERMEDIATE |
| 4 | `PWR_ON` | "Power to the CCD is on" | **초록** | ON |
| 5 | `PWR_STANDBY` | "System is in standby" | 파랑 | STANDBY |

표시등 위젯(`PowerWidget`)은 **색칠한 네모 하나**가 전부다 — 30×10 px, 검정 1px 테두리. **문구는 위젯이 갖고 있지 않고 전부 밖에서 `setToolTip()` 으로 붙여**서 마우스를 올려야 보인다 [확정].

> 중요한 구분: **`POWER` 는 "CCD 로 가는 바이어스/클록 전원" 상태다. 컨트롤러 자체 전원이 아니다.** 컨트롤러 공급전원 건강은 `POWERGOOD` 이 담당한다. **두 축을 섞어서 하나의 "정상" 지표로 만들면 안 된다.**

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

`parseStatus()` 전체를 그 자리에서 끝내버린다. 그래서 **전원이 STANDBY 인 동안에는 그 아래가 통째로 갱신을 멈춘다**:

- 백플레인 온도 (`:2251~2253`)
- OVERHEAT / POWERFAIL 경고 (`:2255~2262`)
- **전원 레일 전압·전류 24칸 전부** (`:2263~2334`)
- 모듈 온도 12칸과 모듈별 `parseStatus()` (`:2340~2344`)

다른 5개 분기엔 `return` 이 없다 — **딱 STANDBY 만 그러하므로 복붙 실수로 보인다.** 화면 증상은 "스탠바이로 넘어가는 순간 온도·전압 판이 마지막 값에서 얼어붙는다" 이다. **표시만 죽고 제어는 멀쩡하므로 조용히 오해를 부르는 종류다.** 우리 ICS 는 이를 절대 답습하면 안 된다.

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
| −35 V Analog | **−33.8 … −35.9 V** | ❌ **표준 PSU 가 만들지 않는다** |
| Heater | **+18.0 … +36.0 V** | (히터 쓸 때) |
| User | **+18.0 … +36.0 V** | ❌ |
| Fan (+12 V) | 팬에 직결 | ✅ |

XV 섀시 변형(p.42)은 세 줄만 다르다 — `-35V` → **−100 V(−97 … −103 V)**, `User` → **+100 V(+97 … +103 V)**.

### ⭐ "7개냐 8개냐" 정리

세 숫자가 서로 달라서 혼동하기 딱 좋다. 층위를 나눠야 한다 [확정]:

| 세는 기준 | 개수 | 목록 |
|---|---:|---|
| **Power Good Range 가 정의된 레일** (p.41) | **8** | P2V5·P5V·P6V·N6V·P17V·N17V·P35V·**N35V** (+ HEATER·USER 로 범위 항목은 10) |
| **표준 PSU 가 실제로 만드는 전압** (p.43) | **7** | "+2.5V, +5V, +6V, -6V, +17V, -17V, and +35V" — **N35V 는 만들지 않는다** |
| 파워보드 감시 스위치 (Figure 28, p.42) | 10 | 위 8 + `HEATERGOOD` + `USERGOOD` (+ 종합 `PWRGOOD`) |
| **STATUS 가 보고하는 V/I 쌍** (p.47) | **12** | 위 8 + P100V + N100V + USER + HEATER |

⚠️ 매뉴얼 자체의 모순이다 — p.44 전력소비 표에 `-35V` 열이 없고 p.43 본문도 만들지 않는다고 하는데, p.41 표와 Figure 28 에는 버젓이 있다. **하드웨어 배선은 있고 표준 PSU 가 채우지 않는 구조로 보인다** [유력].

알람 임계값을 만든다면 **8개 기준 표(p.41)** 를 쓰되, **안 쓰는 레일(N35V·USER·P100V·N100V)은 감시 스위치가 꺼져 있어서 값이 0 근처로 나온다. 0 을 알람으로 처리하면 안 된다** [확정].

### `POWERGOOD` 의 정확한 의미

- 매뉴얼 정의는 한 줄뿐 — "n = 1 when system power supply is good" (p.47).
- 실체는 파워보드의 종합 신호 `PWRGOOD` 이고, 백플레인이 P9 의 IDC 케이블로 받는다(Figure 8, p.20).
- ⚠️ 즉 **`POWERGOOD=1` 은 "여덟 레일 전부 정상" 이 아니라 "P1/P7 스위치로 감시하도록 켜둔 레일 전부 정상" 이다.** 꺼진 레일은 판정에 들어가지 않는다 [확정].
- 그래서 **레일별 `_V` 값을 p.41 범위와 따로 대조하는 이중 확인**이 필요하다.

모듈 쪽 보호도 이중이다 — 각 Driver/Bias 모듈이 시스템 레일을 **하드웨어 비교기로 상시 감시**하다가 범위를 벗어나면 CCD 로 가는 포토아이솔레이터를 전부 열어버린다. FPGA 가 리셋돼도 릴레이가 열리고, **재구성 전에는 다시 닫히지 않는다** (p.11, p.27, p.29, p.31, p.33) [확정].

## 9.4 STATUS 필드 전수

### 시스템 헤더 (p.47)

| 키 | 뜻 | 단위·범위 | GUI 표시 |
|---|---|---|---|
| `VALID` | "n = 1 if **remaining status fields are valid**" | 0/1 | Status 그룹 "Status Valid" — **숫자로 찍기만 한다** |
| `COUNT` | 시스템 상태가 갱신된 횟수 | 무단위 카운터 (랩어라운드 [확인불가]) | "Status Count" |
| `LOG` | 대기 중인 로그 개수 | 개수 | **화면엔 뜨지 않는다.** 이 수만큼 `FETCHLOG` 를 반복해 로그창에 뿌린다 |
| `POWER` | §9.1 | 0~5 | 표시등 색 |
| `POWERGOOD` | 공급전원 종합 | 0/1 | 0 이면 `POWERFAIL` 문구 |
| `OVERHEAT` | 과열 | 0/1 | 1 이면 `OVERHEAT` 문구 |
| `BACKPLANE_TEMP` | 백플레인 온도 | **℃** | 소수 1자리 + `" C"` |
| `FANTACH` | 팬 속도 (**Rev F only**) | RPM | "Fan Speed (RPM)" |
| `EXTCLKPRESENT` | **매뉴얼 목록에 없음** | — | "Present"/"Absent" |

### 전압 레일 V/I 쌍 12개 = 24 필드 (p.47)

`P2V5`, `P5V`, `P6V`, `N6V`, `P17V`, `N17V`, `P35V`, `N35V`, `P100V`, `N100V`, `USER`, `HEATER` 각각에 `_V`, `_I`.

> ⚠️ **단위 함정**: **시스템 레일 전류는 A** 인데(`P2V5_I=f ; … current in A`, p.47), **모듈 바이어스 전류는 mA** 이다(`MODm/LVLC_In=f ; … in mA`, p.48). 섞으면 안 된다 [확정].

### 모듈별 필드 (p.48~49)

| 키 | 조건 | 단위 |
|---|---|---|
| `MODm/TEMP` | 모든 모듈 | **℃**. GUI 는 모듈 클래스가 아니라 **부모가 파싱**한다(`archongui.cpp:2340`) |
| `MODm/LVLC_Vn`/`_In` (n=1..24), `MODm/LVHC_Vn`/`_In` (n=1..6) | LV(X)Bias | V / **mA** |
| `MODm/HVLC_Vn`/`_In` (24), `MODm/HVHC_Vn`/`_In` (6) | HV(X/Y)Bias | V / **mA** |
| `MODm/TEMPA`, `TEMPB` | Heater(X) | ⚠️ **K (켈빈)** — ℃ 가 아니다 |
| `MODm/TEMPC` | **HeaterX 전용** | **K** |
| `MODm/HEATERAOUTPUT`, `HEATERBOUTPUT` | Heater(X) | V |
| `MODm/HEATERAP`/`AI`/`AD`, `BP`/`BI`/`BD` | Heater(X) | P/I/D 항 기여분, 부호있는 정수 |
| `MODm/DINPUTS` | LV(X)Bias·Heater(X) 는 **8자**, HS·LVDS 는 **4자** | 각 자리 0/1 |
| `MODm/MAG_Vn`/`_In`, `OFS_Vn`/`_In` (n=1..12) | HS | V / mA |
| `MODm/XVP_Vn`/`_In`, `XVN_Vn`/`_In` (n=1..4) | XVBias | V / mA |
| `MODm/RTDn` (1..8), `HALLn` (1..3), `VAC`, `TEC_*`, `ION_*` | Atlas | RTD 는 **저항** → `convrtd()` 로 ℃ 환산 |
| `MODm/VCPU_OUTREGn` (**n=0..15**) | DIO 있는 모듈 | unsigned 16bit |

⚠️ **또 하나의 단위 함정**: HeaterX 설정(target·limit)은 **℃**(p.60~61)인데 STATUS 보고(`TEMPA` 등)는 **K**(p.48)이다. **반드시 변환해야 한다** [확정].

`DRIVER`·`DRIVERX`·`AD`·`ADF`·`ADX`·`ADLN`·`ADM` 일곱 클래스는 `parseStatus()` 가 **빈 함수**다 — STATUS 에서 아무것도 읽지 않는다 [확정].

## 9.5 ⚠️ `VALID` 를 GUI 는 게이트로 쓰지 않는다

매뉴얼 p.47 은 `VALID=0` 이면 **그 응답의 나머지 STATUS 필드가 전부 무효**라고 규정한다. "일부만 무효" 라는 단서는 어디에도 없다 [확정].

그런데 **stock GUI 는 `VALID` 를 숫자로 화면에 찍기만 한다**(`archongui.cpp:2197`). 그 아래 `BACKPLANE_TEMP`·전압·`OVERHEAT`·`POWERGOOD` 갱신은 `VALID` 와 **무관하게 그냥 진행된다.** GUI 전체에서 "VALID" 문자열은 그 한 줄이 유일하다 [확정].

> **GUI 를 정본으로 삼아 답습하면 무효 데이터를 그대로 표시하게 된다.** 우리 ICS 는 `VALID=1` 일 때만 나머지를 채택하도록 규정해두는 것이 맞다. 그리고 `COUNT` 를 같이 보아야 신선도까지 확인된다 — 값이 늘지 않으면 컨트롤러가 내부 상태 레지스터를 갱신하지 못하고 있다는 뜻이다(p.74).
>
> 매뉴얼은 `VALID` 가 언제 0 이 되는지, 0 일 때 필드에 뭐가 들어오는지(직전 값 유지? 0? 쓰레기?)를 **적어놓지 않았다** [확인불가]. **실측대상**이다.

## 9.6 ⭐ 폴링 구조

### 주기 — 500 ms 고정

```cpp
// archongui.cpp:1224~1227
// Start timer for polling at 5Hz          ← 주석이 낡았어
updateTimer = new TUpdateTimer(this);
connect(updateTimer, SIGNAL(update()), this, SLOT(poll()));
updateTimer->startUpdateTimer(500);
```

⚠️ **주석은 5 Hz 라고 하지만 실제 인자는 500 ms = 2 Hz 이다.** 그리고 `poll()` 은 **한 틱에 명령 하나만** 내므로 STATUS 와 FRAME 은 **각각 약 1 Hz** 이다 [확정]. (200 → 500 으로 늘리면서 주석을 고치지 않은 것으로 보인다.)

`TUpdateTimer` 는 전부 43줄짜리고 실행부는 이것이 전부다:

```cpp
void TUpdateTimer::run() { while (!thread_exit) { msleep(updateInterval); emit update(); } }
```

파일 머리 주석이 존재 이유를 밝힌다 — **"QTimer 가 산발적으로 CPU 를 크게 먹어서 QTimer 대신 쓴다"**(`updatetimer.cpp:3~5`). 조절 수단은 시작 인자 하나뿐이고 **돌기 시작한 뒤에는 주기를 바꾸지 못한다.** 드리프트 보정도 없다 [확정].

### `poll()` 의 명령 순서

```cpp
// archongui.cpp:2833~2851
switch (pollstep) {
case 0: if (!archon->command("STATUS")) pollstep++; break;
case 1: if (!archon->command("FRAME"))  pollstep++; break;
}
if (pollstep > 1) pollstep = 0;
```

**STATUS → FRAME → STATUS → FRAME …** 무한 교대. 딱 이 둘뿐이다. `SYSTEM` 은 폴링에 들어가지 않는다 — **연결 시 1회**(그리고 파일 로드 시 `parseSystem()` 재호출)뿐이다 [확정].

핵심 두 가지:

1. **`command()` 가 성공(0)했을 때만 `pollstep++`.** 거절(1)당하면 단계를 그대로 두고 다음 틱에 같은 명령을 다시 시도한다 — 교대 순서가 절대 깨지지 않는다. 자연스러운 백프레셔다.
2. **`poll()` 은 `getResult()` 를 부르지 않는다.** 던져놓고 바로 반환하는 fire-and-forget 이므로 GUI 가 멈추지 않는다.

### ⭐ 명령이 버려지는 기전 — "화면이 얼어붙는" 착시의 정체

`Archon::command()` 는 **`CommandInProgress` 면 큐에 쌓지 않고 즉시 거절(return 1)** 한다(`archon.cpp:187`). 그래서 **FETCH 가 도는 동안에는 `FRAME` 응답이 한 번도 오지 않는다** [확정].

실측으로 확인됐다 [실측]: FETCH 중에도 엔진은 **368.0 행/초 만속**으로 계속 쓴다. 재관측에서 라인 표시가 10 → 1500 으로 점프했고, 1490행 ÷ 368 = 4.05초 = FETCH 시간이다. **즉 "독출 정지" 는 표시 착시였고, 기전이 바로 이 "폴 거절" 이다.**

### 폴링이 다른 명령과 겹칠 때 — 4중 방어 [확정]

| 방어 | 내용 |
|---|---|
| (a) **같은 스레드** | `poll()` 도 버튼 슬롯도 전부 GUI 스레드 이벤트 루프에서 실행된다. 인터리빙 자체가 없다 |
| (b) **사용자 동작은 먼저 비운다** | 거의 모든 동작 슬롯 첫 줄이 `archon->getResult()`. 최악의 경우 5초까지 GUI 가 굳는다 |
| (c) **폴링은 순번을 지키며 재시도** | 위 `pollstep` 로직 |
| (d) **오래 걸린 뒤에는 몰아서 나간다** | `getResult()` 가 이벤트 루프를 돌리지 않으므로 큐 연결된 `update()` 가 쌓인다. 작업이 끝나면 쌓인 `poll()` 이 우르르 실행되는데 대부분 거절되어 no-op 이 된다 |

⚠️ 예외 하나: **자동 페치가 폴링 콜백 안에서 GUI 를 막는다.** `parseFrameStatus()` 끝에서 Auto Fetch 가 켜져 있으면 `fetchFrame()` 을 부르고, 그 안에서 `getResult()` 를 두 번 부른다(`:1838`, `:1840`). **폴링이 부른 슬롯 안에서 블로킹하는 유일한 경로**다.

### 로그 수집도 폴링의 부산물

`getStatus()` 는 응답의 `LOG=n` 만큼 `FETCHLOG` 를 반복해서 컨트롤러 로그를 GUI 로그창으로 끌어온다(`archon.cpp:600~606`) [확정]. **컨트롤러는 절대 먼저 말을 걸지 않으므로 이 폴링이 유일한 비동기 통보 경로다.** 폴링을 끄면 컨트롤러 로그도 들어오지 않는다.

로그창(`telog`)은 읽기전용 `QPlainTextEdit` 이고 **최대 1000블록** — 오래된 줄은 자동으로 밀려난다 [확정].

## 9.7 `RMap` 파싱 규칙 — 엄격하다

`getSystem()`/`getStatus()`/`getFrameStatus()` 셋이 완전히 동일한 규칙을 쓴다 [확정]:

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

1. 응답은 공백 구분 `KEY=VALUE` 나열이어야 한다 (매뉴얼 p.45).
2. **값에 공백이 있으면 안 된다** — 그 토큰이 꼴을 갖추지 못해 전체 파싱이 실패한다.
3. **값에 `=` 가 있어도 안 된다** — `split('=')` 가 3조각을 내서 실패. `1.0.1252` 처럼 점은 괜찮다.
4. ⚠️ 토큰 하나만 어긋나도 **맵 전체가 버려지는 것이 아니라, 그 시점까지 채워진 부분 맵이 시그널로 나간다.** 오류 경로에서도 `emit msgSystem(system)` 을 하기 때문이다.

`SYSTEM` 응답 키는 매뉴얼 p.46 의 9종 + **`POWER_ID`**(매뉴얼 목록엔 없고 부록 A p.96 엔 있다) = 10종이다. GUI 가 읽는 것도 정확히 이 10종이다 [확정]. `MOD_PRESENT` 는 **16진 비트필드, LSB=슬롯1** 이고 부록 A 의 `MOD_PRESENT=14`(= 슬롯 3·5)로 규약을 검증했다 [확정].

---

# 10. 펌웨어·빌드

## 10.1 보유 `.mcs` 4종

> **2026-09-03 갱신** — 운영자가 **Rev H 백플레인 이미지(FW 1.0.1271)** 를 받아 넣었고, 폴더명이 `ArchonFW_20250825` → **`ArchonFW`** 로 바뀌었다. 아래 표·판정은 그 뒤 상태다.

| 파일 | 크기(B) | md5 | 데이터 레코드 | 펼친 크기 | mtime |
|---|---:|---|---:|---:|---|
| `archonbackplanerevf_1_0_1252.mcs` | 19,579,653 | `96d9c5f4…0e8c` | 444,952 | 6.79 MiB | 2024-04-13 |
| ⭐ `archonbackplanerevh_1_0_1271.mcs` | 17,904,281 | `c59ba314…47a6` | 397,837 | 6.07 MiB | **2026-09-03** |
| `archondriverrevd_1_0_1175.mcs` | 1,276,689 | `bd8d3d6e…bcce` | 29,013 | 0.44 MiB | 2021-08-07 |
| `archonhvxbiasreva_1_0_1175.mcs` | 1,276,689 | `bb4a23fd…6f97` | 29,013 | 0.44 MiB | 2021-08-07 |

**넷 다 Intel HEX 로 온전하다 — 체크섬 오류 0건** [확정]. 레코드 구성은 확장선형주소(형 04) + 데이터(형 00) + EOF(형 01) 셋뿐이다.

⭐ driver 와 hvxbias 는 **크기가 같고 md5 는 다르고, 레코드 개수와 주소 범위(0x0~0x71544)까지 정확히 같다** [확정]. **같은 FPGA 부품 · 같은 빌드 도구라 이미지 길이가 같고 내용만 다른 것이다** — 앞서 [추정] 이었던 것을 레코드 수·주소 범위 대조로 [유력] 로 올렸다.

백플레인 둘의 주소 범위는 다르다 [확정]: **1252 는 0x0~0x8682A0**, **1271 은 0x0~0xA21048** 이다. 1271 이 주소 범위는 더 넓은데 펼친 바이트는 더 적다(6.07 vs 6.79 MiB) — **비트스트림이 더 성기게 배치됐다는 뜻**이다. 둘 다 X12 백플레인 FW 영역 8 MiB(섹터 0–127) 안에 들어간다.

> 단위 주의: 다른 세션이 DevNote 8.11 에서 적은 "압축 해제 후 7.1 MB" 는 **십진 MB** 다 (7,119,232 B). 위 표의 6.79 MiB 와 같은 값이고 모순이 아니다.

### 10.1.1 ⭐ FW 1252 ↔ 1271 명령표 대조 (2026-09-03 신규)

두 백플레인 이미지를 펼쳐(형 00 레코드만 모아 `unhexlify`) ASCII 구간을 뽑고 명령 디스패치 표를 대조했다 [확정].

| 토큰 | 1252 (Rev F) | 1271 (Rev H) | 판정 |
|---|---|---|---|
| **`LOCKT`** | 있음 (1건, 널종단) | **0건** | ⭐ **1271 에서 빠졌다** |
| **`FASTAUTOFETCH`** | **0건** | 있음 (1건, 널종단) | ⭐ **1271 에 새로 생겼다** |
| `AUTOFETCH` | 있음 (`<SFAUTOFETCH=%d`) | 있음 (`@<SFAUTOFETCH=%d`) | 양쪽 유지 |
| `LOCKNEWEST` | 0건 | 0건 | ⭐ FW 명령이 아님이 **재확인**됐다 |

1271 표 순서 (`FETCHLOG` 다음부터):

```
SYSTEM STATUS TIMER FRAME FETCHLOG LOCK VERIFYMOD ERASEMOD FLASHMOD
FLASHACTIVECONFIG ERASESTOREDCONFIG ERASE FLASH VERIFY AUTOFETCH FASTAUTOFETCH
WCONFIG RCONFIG CLEARCONFIG APPLYNET POWEROFF POLLON POLLOFF BIASPOLLON
BIASPOLLOFF LOADTIMING LOADPARAMS RESETTIMING HOLDTIMING RELEASETIMING
APPLYMOD APPLYDIO APPLYSYSTEM APPLYCDS ATLASMOVE CLEARAD CALAD WARMBOOT REBOOT
```

⚠️ **"문자열이 없다" 를 "명령이 없다" 로 곧장 읽으면 안 된다** — 좋은 반례가 같은 자료 안에 있다. `FETCH` 는 1271 에서 **독립 문자열로 0건**인데, 이건 링커가 `AUTOFETCH`/`FASTAUTOFETCH` 의 **꼬리로 공유**해 버렸기 때문이다(널종단 검색으로는 2건 잡힌다). `FETCH` 가 사라졌을 리는 없다 — GUI 가 그것으로 실기에서 프레임을 받고 있기 때문이다.
그래서 `LOCKT` 판정에도 같은 유보가 붙는다: `LOCKT` 는 다른 토큰의 꼬리가 될 수 없고(`LOCK` 은 접두라 공유가 안 된다) 널종단 검색에서도 0건이라 **[유력]** 이지만, 빌드마다 문자열 풀 방식이 달라질 수 있어서 **[확정] 은 아니다.**

이것이 뜻하는 것:

- 다른 세션의 미결 *"`LOCKT`·`AUTOFETCH` 가 1261 에도 있나"* 에 **부분적으로 답이 나왔다.** 1261 은 여전히 없지만, 그보다 새 판인 **1271 에서는 `LOCKT` 이 없고 `FASTAUTOFETCH` 가 생겼다.**
- `FASTAUTOFETCH` 는 **매뉴얼에도, 벤더 GUI 소스에도 없다** [확정]. 이름만 보면 자동 송출의 빠른 판인데 **뜻은 모른다.**
- ⚠️ **STA 문의 목록에 `FASTAUTOFETCH` 를 추가해야 한다.** 그리고 `LOCKT` 은 "1252 에 있다가 1271 에서 없어진 명령" 이라는 이력까지 같이 물어보는 것이 좋다.

### 10.1.2 ⭐ `AUTOFETCH` 계열의 송출 형식 — `<QF…` (2026-09-03 발견)

명령 이름만이 아니라 **형식 문자열**을 대조하면 이 계열이 무엇인지 윤곽이 잡힌다 [확정].

| 형식 문자열 | 1252 (Rev F) | 1271 (Rev H) |
|---|---|---|
| `<SFAUTOFETCH=%d ` | 있음 | 있음 |
| **`<QF%d%08X%04X%04X%08X%08X`** | **없음** | **있음** |

`<QF…` 가 `FASTAUTOFETCH` 와 **함께** 1271 에 들어왔다. 필드 구성은 `%d`(십진) + `%08X`(32비트) + `%04X`·`%04X`(16비트 둘) + `%08X%08X`(32비트 둘)이다.

**해석** — 프레임번호 · 버퍼 주소 · 폭 · 높이 · 64비트 타임스탬프로 읽힌다. 같은 이미지에 `TIMER=%08X%08X` 가 있어(§4.4) 마지막 두 칸이 타임스탬프 쌍이라는 것이 뒷받침된다. 즉 **`AUTOFETCH` 계열은 컨트롤러가 프레임을 자발적으로 밀어 보내는 모드**이고, 호스트가 `FRAME` 을 폴링하고 `FETCH` 를 거는 왕복이 필요 없어지는 구조로 보인다.

⚠️ **등급은 [유력] 이다.** 인접한 형식 문자열에서 읽어낸 추론이고 코드를 본 것이 아니다. 필드 대응(어느 `%08X` 가 주소인지 등)은 **[추정]** 이다.

⭐ **이 형식 문자열을 STA 문의서에 그대로 인용할 것.** *"`<QF%d%08X%04X%04X%08X%08X` 가 `FASTAUTOFETCH` 의 송출 헤더인가, 필드 순서는 무엇인가"* 로 물으면 답을 받기 쉽고, **실기에 명령을 때려 볼 이유가 없어진다.**

### 10.1.3 ⭐ 채택 판단 — `AUTOFETCH`/`FASTAUTOFETCH` 는 쓰지 않는다

**현황**: `ics_archon` 은 이 계열을 쓰지 않는다. 코드에 0건이고, 문서에 나오는 것은 *"⛔ `AUTOFETCH`·`LOCKT` 는 보내지 않는다 — 뜻을 모른다"* 라는 **금지 규칙**뿐이다 (`DevNote.md:2094`, `tools/ics_archon_buftest.py:61`) [확정].

**성능상 필요가 없다** [실측]:

| 항목 | 값 |
|---|---|
| science 프레임 주기 | 13.27 초 |
| 독출 (4700행 @ 368.0 행/초) | 12.77 초 |
| FETCH 344.2 MiB | 3.2~3.5 초 (약 100 MiB/s) |

FETCH 가 주기의 약 4분의 1만 점유한다. guide 는 프레임이 훨씬 작아 여유가 더 크다. 폴링 비용도 `FRAME` 명령 한 번이라 무시할 수준이다 — **병목이 fetch 개시 지연에 있지 않다.**

**오히려 잃는 것이 있다.** 이쪽이 더 중요하다:

| # | 근거 | 등급 |
|---|---|---|
| 1 | **프레임 귀속 보장이 깨진다.** 본 프로젝트의 규약은 "최신 프레임" 을 집는 것이 아니라 **`내 번호` 를 담은 버퍼를 찾고, 못 찾으면 저장하지 않는 것**이다(`parse.find_frame`). 밀어 보내기는 컨트롤러 일정으로 도착하므로 그 대응을 다시 세워야 한다 | [확정] |
| 2 | ⭐ **`LOCK` 을 건너뛸 가능성이 크다.** `LOCK` 없이 fetch 하면 약 **26% 확률로 두 노출이 섞인다**(§12, 실기 2/2 관측). 그것이 `lock_buffer=true` 를 종결시킨 근거다. 밀어 보내기가 호스트 `LOCK` 없이 동작한다면 그 실패를 되살리는 셈이고, **경고 없이 조용히 섞이는** 부류라 가장 나쁘다 | [실측] |
| 3 | **판올림에 묶인다.** `FASTAUTOFETCH` 는 1271 에만 있다. 채택하면 113(1252)과 101 에서 코드 경로가 갈라진다 — 현재는 두 유닛을 같은 경로로 운용한다 | [확정] |
| 4 | **참조 동작이 없다.** 매뉴얼에도 없고 STA 자기 GUI 도 쓰지 않으므로, 무엇이 정상인지 비교할 대상이 없다 | [확정] |

**결론: 채택하지 않고 금지 규칙을 유지한다.** 값어치가 생길 만한 자리를 굳이 꼽자면 guide 를 지금보다 훨씬 빠른 주기로 돌려야 할 때인데, **현재 guide 주기로는 그럴 이유가 없다.**
- ⚠️ **셋 다 임의로 실행하지 말 것.** 자동 송출 계열이면 링크에 프레임이 쏟아지거나 상태가 바뀔 수 있다.

## 10.2 `.mcs` 파싱 — `readMCS()`

`archon.cpp:683~743` [확정]:

1. **`ba.fill(0xFF, flash_size)`** — 지워진 플래시 기본값이 0xFF 라 안 쓴 영역은 자동으로 "빈 줄" 취급
2. 줄마다: `:` 로 시작 안 하면 **조용히 건너뜀**
3. **레코드 타입 00 (Data)**: `addr += segaddr`, `addr+len > flash_size` 면 `"File too large"`, 아니면 2자리씩 잘라 기록
4. **레코드 타입 04 (Extended Linear Address)**: `segaddr = (앞 4자리 16진) << 16`
5. **그 밖(01 EOF, 02, 03, 05)은 전부 무시**

⚠️ **체크섬을 전혀 검증하지 않는다.** 각 줄 끝의 체크섬 바이트를 읽지도 않는다. 손상된 MCS 를 그대로 굽고, 잡히는 것은 그 뒤의 `verify()` 단계에서다 [확정].

## 10.3 플래시 크기와 영역

**백플레인** (`archon.cpp:761~787`) — `BACKPLANE_TYPE` 으로 갈라진다. 섹터는 65536 B 고정 [확정].

| | X12 (`TYPE=1`) — **우리 실기** | X16 (`TYPE=2`) |
|---|---|---|
| `flash_size` | **16 MiB** | 32 MiB |
| `sectors` | 256 | 512 |
| FW 영역 | 섹터 0–127 → `0x000000`–`0x7FFFFF` (8 MiB) | 섹터 0–255 (16 MiB) |
| Code 영역 | 섹터 128–191 → `0x800000`–`0xBFFFFF` (4 MiB) | 섹터 256–319 |
| (틈) | 없음 | 섹터 320–383 **건너뜀** |
| Config 영역 | 섹터 192–255 → `0xC00000`–`0xFFFFFF` (4 MiB) | 섹터 384–447 |
| `FLASH` 주소 | `hex(addr>>8, 4)` — **4자리** | `hex(addr, 8)` — **8자리** |

X12 의 "block address" 는 **바이트 주소를 256 으로 나눈 값**이다. 1024바이트 줄 하나당 4씩 증가한다. **2021 매뉴얼은 4자리 형식만 문서화하고 X16 8자리 변형은 없다** [확정].

**모듈** (`flashMod` `:1042~1074`, `verifyMod` `:1173~1196`) — `MOD<n>_TYPE` 으로 갈라진다 [확정]:

| 모듈 형 | `flash_size` |
|---|---|
| 기본 (DRIVER, AD, LVBIAS, HVBIAS, HEATER, ATLAS, HS, HVXBIAS, HVYBIAS, LVXBIAS, LVDS, HEATERX, XVBIAS, ADF, ADLN, DRIVERX) | **1 MiB** |
| **`MOD_TYPE_ADM` (17)** | **4 MiB** |
| **`MOD_TYPE_ADX` (14)** | **8 MiB** |

즉 우리 science 는 슬롯 5·8 만 4 MiB, 나머지는 1 MiB 다. 모듈 `FLASHMOD` 주소는 **항상 4자리** — 최대 8 MiB 라 `>>8` 하면 0x8000 까지고 4자리로 충분하다.

## 10.4 ⭐ 파일명 검증 규칙과 REV ↔ Rev 문자 대응

플래시 전에 **파일명 접두를 반드시 대조할 것** [확정]:

```
백플레인: "archonbackplane" [+ "x16" if X16] + "rev" + ('a' + BACKPLANE_REV)
모듈:     "archon" + <형별 기본이름> + "rev" + ('a' + MOD<n>_REV)
```

형별 기본 이름은 `archondriver`, `archondriverx`, `archonad`, `archonadf`, `archonadln`, **`archonadm`**, `archonadx`, `archonlvbias`, `archonhvbias`, `archonheater`, `archonatlas`, `archonhs`, `archonhvxbias`, `archonhvybias`, `archonlvxbias`, `archonlvds`, `archonheaterx`, `archonxvbias` 다.

**REV 숫자 ↔ Rev 문자 대응** (`'A' + n`) [확정]:

| REV 숫자 | 0 | 1 | 2 | 3 | 4 | **5** | 6 | **7** | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rev 문자 | A | B | C | D | E | **F** | G | **H** | I | J | K |

실기 대조 [확정]:

| 대상 | `_REV` | Rev 문자 | 기대 파일명 접두 | 보유 여부 |
|---|---:|---|---|---|
| 백플레인 — **Rev F 2대** (113 · GUI-162, FW 1252) | 5 | **F** | `archonbackplanerevf` | ✅ `archonbackplanerevf_1_0_1252.mcs` — **판번까지 일치**(같은 판이므로 구울 이유가 없다) |
| 백플레인 — **Rev H 5대** (KMTC-SCI-101 · KMTC-SCI-102 · KMTS-SCI-101 · KMTS-SCI-102 · KMTS-GUI-161, FW 1261) | **7** | **H** | `archonbackplanerevh` | ⭐ ✅ `archonbackplanerevh_1_0_1271.mcs` (2026-09-03 반입) — **Rev 는 맞고 판번은 더 새것**(실기 1261 < 1271) |
| Driver | 3 | D | `archondriverrevd` | ✅ `archondriverrevd_1_0_1175.mcs` |
| HVXBias | 0 | A | `archonhvxbiasreva` | ✅ `archonhvxbiasreva_1_0_1175.mcs` |
| ADM | 1 | B | `archonadmrevb` | ❌ **없다** |
| LVXBias · LVDS | — | — | — | ❌ 없다 |
| guide 의 AD | 10 | K | `archonadrevk` | ❌ 없다 |

> ⚠️ **이미지는 유닛의 Rev 에 맞는 것만 사용할 것.** `archonbackplanerevf_…` 는 113(Rev F)용, `archonbackplanerevh_…` 는 101(Rev H)용이다. 서로 바꿔 쓰면 **파일명 검증에서 걸려서 아예 굽지 못하고**, 억지로 굽는 것도 안 된다 [확정].
>
> ⭐ **2026-09-03 갱신 — Rev H 용 이미지가 생겼다.** 다만 **판번이 실기와 다르다**: Rev H 유닛들에 올라가 있는 것은 **1.0.1261** 인데 받은 이미지는 **1.0.1271** 이다. 즉 이것은 *복구용 같은 판*이 아니라 **판올림(upgrade)** 이다.
>
> ⚠️ **그리고 대상이 한 대가 아니다.** ACF 전수 대조 결과 Rev H 는 **다섯**이다(§4.7). 한 대에 구우면 나머지 셋과 FW 판이 갈리므로, **어느 범위까지 올릴지를 먼저 정해야 한다.** Rev F 두 대(113 · GUI-162)는 보유 이미지가 실기와 **같은 판(1252)** 이라 구울 이유가 없다.
> ⚠️ **굽기 전에 판올림 여부를 운영자가 결정해야 한다.** 1271 은 1261 과 명령표가 다르고(`LOCKT` 제거 · `FASTAUTOFETCH` 추가, §10.1.1), 그 차이가 우리 ICS 나 벤더 GUI 에 어떤 영향을 주는지 **아직 확인하지 못했다** [실측대상]. 굽는 순간 되돌릴 이미지(1261)가 우리에게 없다는 것도 같이 봐야 한다.
>
> 그리고 **ADM 펌웨어 `.mcs` 가 없다** — 우리 science 비디오 모듈 두 장이 바로 그것이다.

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
     · 전부 0xFF 면 건너뜀      ← 소거 후 상태와 같다. FW 대부분이 빈 영역이라 시간을 크게 줄인다
     · 선택 안 한 영역·틈 건너뜀
     · FLASH + 주소 + 2048자 16진 (명령 1줄이 2,061~2,065자)
6. verify() 자동 호출        ← 플래시는 항상 검증까지 해
7. BIASPOLLON 복구
```

`verify()` 는 `group_size = 256` 이라 한 그룹이 **256블록 × 1024 B = 256 KiB** 다. `VERIFY` 명령 한 번에 256블록이 흘러나오고 매 블록마다 같은 `last_msgref` 로 프리앰블을 대조한다.

모듈 쪽은 다소 다르다 — 소거가 **`ERASEMOD` 한 번에 모듈 전체**(타임아웃 **200,000 ms**)고, 검증 그룹이 16블록 = 16 KiB 다.

⚠️ **비대칭 하나**: `flashMod` 는 0xFF 줄 건너뛰기를 하는데 **`verifyMod` 는 건너뛰기 없이 전 영역을 다 읽는다.** ADX 8 MiB 모듈이면 8192블록을 전부 받는다. 백플레인 `verify()` 는 영역 건너뛰기가 있는데 모듈 쪽만 없다 [확정].

⚠️ **Reboot · Erase Stored Config · Flash 계열에 확인 대화상자가 하나도 없다.** 메뉴를 잘못 누르면 곧장 실행된다. 게다가 `sPROMFilename` 기본값이 **개발자 로컬 경로 `D:/Archon/RevC/...`** 로 박혀 있다(`archongui.cpp:39`) [확정].

`REBOOT` vs `WARMBOOT` 차이 (매뉴얼 p.51) [확정]:

| | `REBOOT` | `WARMBOOT` |
|---|---|---|
| 대상 | 백플레인 + **모든 모듈 FPGA** 가 설정 메모리에서 펌웨어 재로드 | **백플레인 프로세서만** 재시작 |
| FPGA 펌웨어 재로드 | ✅ | ❌ |
| 연결 | 끊김 | 끊김 |
| `BUFnFRAME` 리셋 | ✅ [실측] | ❌ (프레임 번호가 이어진다) [실측] |

`reboot`/`warmboot` 가 반환값을 무시하는 것은 합리적이다 — 컨트롤러가 응답을 주기 전에 링크를 끊으니 타임아웃이 정상 동작이다. 반면 **`flashactiveconfig`/`erasestoredconfig` 가 반환값을 무시하는 것은 설계 결함으로 보인다** — 저장 실패가 GUI 에 전혀 알려지지 않는다(로그 창에만 표시된다) [확정].

## 10.6 빌드 환경

### 프로젝트 파일 — 3판 동일

`archongui.pro` 는 **세 판이 완전히 같다** [확정]:

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

`$$files(...)` 글롭이라 **파일을 추가하면 자동으로 잡힌다.** 그리고 **qwt 를 외부 라이브러리로 링크하지 않고 소스째 동봉해서 같이 컴파일한다** — 배포 의존성을 줄이려는 선택이다.

`readme.txt` 는 **Qt 5.2 기준**이라고 적혀 있다 [확정] — "Archon GUI is tested using Qt 5.2".

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

> ⭐ **정황 정리**: 개조는 2025-08-27 에 **윈도우에서 Qt Creator 3.2.1(Qt 5.3 MinGW 킷)로** 이뤄졌고, 그 트리를 SSO 리눅스로 옮겨 **2026-01-18 에 Qt 5.15 / g++ 13 으로 빌드**했다. `.pro.user` 의 md5 가 두 KMTNet 사본에서 같으니 SSO 사본은 편집을 더 하지 않은 순수 복사본이다 [확정].
>
> Qt 5.2~5.3 을 상정한 코드를 Qt 5.15 / C++17 / g++ 13 으로 빌드한 것이라 **경고가 상당히 났을 가능성이 높은데, 빌드 로그가 없어서 [확인불가]** 다. 재빌드할 일이 생기면 로그를 남겨두는 것이 좋다.

### 판 호환성

| 조합 | 판정 |
|---|---|
| stock GUI ↔ 실기 (FW 1252/1261) | 문제없다. `RAWSEL≤15` 라 개조 유무가 차이를 만들지 않는다 [확정] |
| KMTNet GUI ↔ 실기 | 현행 ACF 로는 stock 과 **완전히 동일하게 동작** [확정] |
| GUI 1.0.1259 ↔ FW 1.0.1252 (113) | 위젯 게이팅이 `build`/`rev` 로 걸려서 정합. `REV=5`·`build=1252` 면 **External Clock 체크박스와 Trigger Out Power 가 숨겨지고** 나머지는 다 보인다 [확정] |
| GUI 1.0.1259 ↔ FW 1.0.1261 (101) | **[확인불가]** — 101 의 `SYSTEM` 응답을 GUI 로 받아본 기록이 없다. 게이팅 임계값(1042/1179/930/1028/1046/1049/1063/1064/833/1090) 이 전부 1261 미만이라 **기능이 더 열릴 뿐 깨질 이유는 없어 보인다** [유력] |
| ACF 를 GUI 로 왕복 | ⚠️ **무손실이 아니다.** §5.6 C3 참고 |
| `archonbackplanerevf_1_0_1252.mcs` ↔ 101 | ❌ **부적합.** 101 은 Rev H |

---

## 10.7 ⭐ 이미지 내부 분석 — 방법과 아키텍처 판정

§10.1.1 은 `.mcs` 를 펼쳐 **ASCII 문자열만** 대조한 것이었다. 이번에는 거기서 더 들어가 **1271 이미지를 디스어셈블**했다. 그 결과 §10.1 계열의 여러 판정이 등급이 바뀌었고, 한 건은 사실관계가 틀렸다.

### (a) 방법과 그 한계

| 단계 | 내용 | 적용 대상 |
|---|---|---|
| 1 | `.mcs` 에서 형 00 레코드만 모아 `unhexlify` → 평문 바이너리 | 4종 전부 |
| 2 | NUL 로 앞뒤가 끊긴 구간만 채택(`(?<=\x00)[\x20-\x7e]{2,}(?=\x00)`) — 비트스트림 잡음 배제 | 4종 전부 |
| 3 | **capstone(AArch64) 디스어셈블**, `adrp`+`add` 문자열 참조와 조건 분기 역추적 | **1271 만** |
| 4 | 로드 주소 보정 **+0x18** (`RAWENABLE`/`RAWSEL` 오류 문자열 4개로 교차검증) | 1271 만 |

⚠️ **이 절의 코드 근거는 전부 1271(Rev H) 한 판뿐이다.** capstone 에 MicroBlaze 백엔드가 없어 **1252(Rev F)는 디스어셈블하지 못했다.** 따라서 Rev F 유닛(**KMTK_SCI_113 · KMTK_GUI_162**)에 대해서는 **문자열 대조 결과만 유효**하고, 코드에서 읽어낸 수치·분기 판정은 그대로 옮길 수 없다. 이 절은 아래 원칙으로 등급을 매겼다.

| 근거의 성질 | 등급 |
|---|---|
| 두 이미지 모두에서 문자열을 직접 확인 | [확정] |
| 1271 디스어셈블 원문 — Rev H 유닛에 한정 | [확정] |
| 1271 디스어셈블 원문을 **Rev F 로 옮겨 적용** | [유력] 이하로 강등 |
| 문자열 인접·정황에서 읽은 해석 | [유력] 또는 [추정] |

### (b) ⭐ 아키텍처 판정 — 매뉴얼 p.15 와 정확히 맞는다

| 이미지 | 헤더 | 플랫폼 | 근거 | 등급 |
|---|---|---|---|---|
| `…revf_1_0_1252` | 싱크워드 `aa995566` | Xilinx 7-series 비트스트림 + **32비트 소프트코어(MicroBlaze 계열, LE)** | 명령 워드가 LE 로 `0xB0`(IMM)·`0xB8`(BRI)·`0x30`(ADDIK)·`0xE8`(LWI) 패턴. 서식문자열이 `%lld`·`%016llX` → **`long` 이 32비트** | 32비트 코어 [확정] / MicroBlaze 지목 [유력] |
| `…revh_1_0_1271` | `665599aa` + `XNLX` | **Zynq UltraScale+ MPSoC 부트이미지 (ARM Cortex-A53, AArch64)** | `xqspipsu.c`·`xuartps.c`·**`xcsudma_intr.c`**(ZynqMP CSU DMA 전용)·newlib 3.3.0 경로 문자열. 서식문자열이 `%ld`·`%016lX` → **`long` 이 64비트**. capstone AArch64 로 전 구간이 정상 해독됨 | [확정] |
| `…driverrevd_1_0_1175` | `aa995566` | 순수 FPGA 비트스트림 | NUL 종단 ASCII 27개, 전부 잡음 — **CPU 문자열 테이블이 없다** | [확정] |
| `…hvxbiasreva_1_0_1175` | `aa995566` | 순수 FPGA 비트스트림 | 같은 이유(2개) | [확정] |

**매뉴얼 p.15 가 이것을 그대로 적어 두었다** [확정]:

> "Processing is done by a 32-bit soft processor embedded in the backplane Kintex 7 FPGA for older systems, and by a 64-bit ARM processor for Rev H backplanes."

즉 **이미지에서 읽어낸 것과 매뉴얼 서술이 처음으로 완전히 일치한 사례**다. §4.6·§10.6 에서 매뉴얼이 11군데 어긋났던 것과 대비된다 — *매뉴얼은 값·목록에서는 낡았지만 하드웨어 구조 서술은 아직 쓸 만하다* 는 뜻으로 읽어야 한다.

같은 p.15 가 두 가지를 더 뒷받침한다.

| 매뉴얼 p.15 서술 | 이미지·소스 쪽 대응 | 등급 |
|---|---|---|
| "X12 … of which **4 can be ADC modules**" | 1271 코드의 탭→슬롯 조회가 항상 `+4` 를 더한다 → **AD/ADM 슬롯은 0기점 4–7 = 1기점 5–8 고정** | [확정](Rev H) |
| "Rev F and older … **single connection at a time**. Rev H … **up to four simultaneous connections**" | §4.7 의 운영 제약과 일치. 1271 에만 있는 신규 네트워크 로그군(§10.10)이 이 갈래에 붙는다 | [확정] |

### (c) ⚠️ 두 판 차이의 상당수는 "판올림" 이 아니라 "CPU 교체" 의 부산물이다

**이 절에서 가장 오해하기 쉬운 지점이므로 먼저 명확히 해둔다.** 1252 와 1271 의 문자열 차이를 나열하면 꽤 많아 보이지만, **그중 상당수는 기능 변경이 아니라 `long` 의 폭이 32→64비트로 바뀌면서 서식문자열이 따라 바뀐 것**이다. 출력 결과는 완전히 같다.

| 1252 (32비트) | 1271 (64비트) | 실제 출력 | 판정 |
|---|---|---|---|
| `TIMER=%08X%08X` | `TIMER=%016lX` | 16자리 hex 동일 | **무변경** [확정] |
| `BACKPLANE_ID=%016llX` | `BACKPLANE_ID=%016lX` | 동일 | **무변경** [확정] |
| `POWER_ID=%012llX` | `POWER_ID=%012lX` | 동일 | **무변경** [확정] |
| `MOD%d/HEATERA{P,I,D}=%lld` 외 6종 | `…=%ld` | 동일 | **무변경** [확정] |
| `>VL%04X%010llX` | `>VL%04X%010lX` | 동일(모듈 송신 명령) | **무변경** [확정] |
| `<%02X` · `<%02X%s\n` · `?%02X` | `<%c%c` · `<%c%c%s\n` · `?%c%c` | §10.8(c) 참조 — GUI 에 무해 | **무변경** [확정] |

> **판올림 검토에서 세야 할 것은 이 표에 있는 항목이 아니다.** 실제 변경은 §10.9(오토페치 헤더) · §10.10(신규 기능) · §10.11(신규 모듈 형) 셋뿐이다.

### (d) 빌드 시각

1271 안에 `Aug 30 2026` / `10:19:49` / `10:20:02` 가 박혀 있다(Xilinx BSP 의 `__DATE__`/`__TIME__`) [확정 · 문자열]. 이것이 **이미지 전체의 빌드 시각**이라는 해석은 [유력]이다 — BSP 만 그때 빌드됐을 가능성이 남는다.

1252 에는 날짜 문자열이 **없다** [확정]. 즉 두 판의 빌드 시각을 나란히 비교할 수단은 없다.

⚠️ **운영 판단에 직결되는 사실 하나**: 우리가 받은 이미지는 **반입일(2026-09-03) 기준 나흘 전에 빌드된 것**이다. 현장 운용 이력이 사실상 없는 판이다(§10.12).

---

## 10.8 ⭐⭐ ACF 호환성 판정 — 판올림이 ACF 문법을 바꾸지 않는다

**판올림 검토의 핵심 결론이다.** 결론부터 적는다.

> ### 1252 ↔ 1271 사이에서 `[CONFIG]` 키 집합은 완전히 동일하다. STATUS/SYSTEM/FRAME 응답 필드도 추가·삭제가 **0건**이다. [확정]
>
> ### 즉 **1261 → 1271 판올림은 ACF 문법을 바꾸지 않는다.** [유력] — 등급 근거는 (d) 참조.

### (a) `[CONFIG]` 키 전수 대조

두 이미지의 파서 문자열 테이블에서 대문자 식별자를 순서대로 뽑아 집합 대조했다(1252 229개 / 1271 219개). **양쪽에만 있는 키로 실질적인 것은 아래 두 건뿐이고, 나머지 차이는 전부 링커의 문자열 꼬리 공유 또는 짧은 리터럴 인라인화로 설명된다** [확정].

| 토큰 | 1252 | 1271 | 설명 | 판정 |
|---|---|---|---|---|
| `LINE` | 독립 존재 | `RAWSTARTLINE\0`·`TAPLINE\0`·`VCPU_LINE\0` 의 **꼬리**로 존재(0x5e3068 외 4곳) | 링커 접미 공유 | 양쪽 기능 있음 [확정] |
| `FETCH` | 독립 존재 | `AUTOFETCH\0`·`FASTAUTOFETCH\0` 의 **꼬리**(0x5e7a8c, 0x5e7aa0) | 링커 접미 공유 | 양쪽 기능 있음 [확정] |
| `LED` | 독립 존재 | `LED\0` **0건**. 그러나 `Error parsing LED channel`·`Invalid LED channel`·`Error parsing LED source`·`Invalid LED source`·`Error setting LED sources`·`>L%02X` 는 **전부 남아 있다** | 3자 리터럴 인라인화 | **기능 제거 아님** [유력] |
| `NZ`·`NC`·`OR` | 독립 존재 | 0건 | 2–3자 리터럴은 AArch64 GCC 가 즉치 비교로 인라인 | 판정 불가, 기능은 있을 것 [추정] |
| **`LOCKT`** | 있음 | **0건** | 같은 길이대의 `LOCK`·`ERASE`·`FLASH`·`VERIFY`·`POLLON` 은 1271 에 전부 리터럴로 남아 있다 → **이 길이대는 인라인되지 않는다** | **실제로 빠졌을 가능성이 높다** [유력] |
| **`FASTAUTOFETCH`** | 0건 | 있음 | 짝이 되는 신규 응답 헤더까지 함께 생겼다(§10.9) | **신규 명령** [확정] |

> ⭐ **§10.1.1 의 `LOCKT` 판정을 [유력] 그대로 유지한다.** 다만 근거가 보강됐다 — 이번에는 "같은 길이대의 다른 명령 5개는 남아 있다" 는 **대조군**이 생겼다. 그리고 **GUI 는 `LOCKT` 를 한 번도 보내지 않고**(`archon.cpp` 는 `LOCK`/`LOCK0`/`LOCK<n>` 만 송신), `ics_archon` 도 금지 규칙으로 막아 두었으므로 **실무 영향은 어느 쪽이든 0이다** [확정].

그 밖의 차이는 **비교 순서**뿐이다: `CLEARAD CALAD REBOOT WARMBOOT`(1252) ↔ `CLEARAD CALAD WARMBOOT REBOOT`(1271). 의미 없다 [확정].

### (b) 확정된 공통 키 전수 (파서 테이블 순서, 두 판 동일)

ACF 를 손으로 검증할 때의 정본으로 쓸 수 있다 [확정].

| 구획 | 키 |
|---|---|
| **[CONFIG] 시스템/타이밍** | `IF GOTO CALL RETURN IP PORT NETMASK GATEWAY LINESCAN LINECOUNT LINES LINE STATES STATE PARAMETERS PARAMETER CONSTANTS CONSTANT SHP1 SHP2 SHD1 SHD2 PCLKDELAY RAWENABLE RAWSEL RAWSTARTLINE RAWENDLINE RAWSTARTPIXEL RAWSAMPLES SAMPLEMODE PIXELCOUNT FRAMEMODE BIGBUF ADXRAW ADXCDS TAPLINES TAPLINE TRIGOUTFORCE TRIGOUTLEVEL TRIGOUTINVERT TRIGOUTPOWER TRIGINENABLE TRIGININVERT TRIGINEDGE EXTCLOCK FANDISABLE APPLYALL POWERON MOD VCPU_LINES VCPU_LINE VCPU_INREG LABEL` |
| **MODn/ 드라이버** | `FASTSLEWRATE SLOWSLEWRATE SOURCE ENABLE` |
| **MODn/ AD 계열** | `CLAMPHIGH CLAMPLOW CLAMP PREAMPGAIN` |
| **MODn/ LV Bias** | `LVLC_LABEL LVHC_LABEL DIO_LABEL LVLC_V LVLC_ORDER LVHC_V LVHC_ORDER LVHC_ENABLE LVHC_IL DIO_SOURCE DIO_DIR DIO_POWER` |
| **MODn/ HV Bias** | `HVLC_LABEL HVHC_LABEL HVLC_V HVLC_ORDER HVHC_V HVHC_ORDER HVHC_ENABLE HVHC_IL` |
| **MODn/ Heater** | `HEATERAENABLE HEATERBENABLE HEATERAFORCE HEATERBFORCE HEATERAFORCELEVEL HEATERBFORCELEVEL HEATERASENSOR HEATERBSENSOR HEATERASENSORTYPE HEATERBSENSORTYPE SENSORALOWERLIMIT SENSORAUPPERLIMIT SENSORBLOWERLIMIT SENSORBUPPERLIMIT HEATERALIMIT HEATERBLIMIT HEATERATARGET HEATERBTARGET HEATERAP HEATERBP HEATERAI HEATERBI HEATERAD HEATERBD HEATERAIL HEATERBIL HEATERUPDATETIME HEATERARAMP HEATERBRAMP HEATERARAMPRATE HEATERBRAMPRATE VACENABLE` |
| **MODn/ Atlas** | `TECENABLE IONENABLE LED` |
| **MODn/ HS** | `HS_LABEL MAG_LABEL OFS_LABEL MAG_V OFS_V` |
| **MODn/ LVDS** | `LVDS_LABEL` |
| **MODn/ HeaterX** | `HEATERALABEL HEATERBLABEL SENSORALABEL SENSORBLABEL SENSORCLABEL SENSORATYPE SENSORBTYPE SENSORCTYPE SENSORACURRENT SENSORBCURRENT SENSORCCURRENT SENSORCLOWERLIMIT SENSORCUPPERLIMIT SENSORAFILTER SENSORBFILTER SENSORCFILTER` |
| **MODn/ XV Bias** | `XVP_LABEL XVN_LABEL XVP_V XVP_ORDER XVP_ENABLE XVN_V XVN_ORDER XVN_ENABLE` |
| **[STATE] 절** | `NAME CONTROL` |

우리 실기 science 의 ACF 가 쓰는 키는 이 안에 전부 들어 있다. **ADM(형 17) 슬롯용 `MODn/` 키가 목록에 하나도 없는 것**도 §7.3 의 결론(ADM 은 빈 껍데기)과 정확히 맞는다 [확정].

### (c) STATUS / SYSTEM / FRAME 응답 필드 대조

`=` 와 `%` 를 함께 가진 응답 서식 문자열을 두 판에서 전수 추출해 대조했다(1252 144개 / 1271 145개).

**추가되거나 빠진 필드는 하나도 없다** [확정]. 차이는 §10.7(c) 의 서식 폭 변경과 아래 한 건뿐이다.

| 1252 | 1271 | 성격 |
|---|---|---|
| `Unexpected ADC latency measured (slot %d)` | `Unexpected ADC latency measured (slot %d = %d)` | ⭐ **1271 이 실측치를 함께 찍는다** — 순수 진단 개선 [확정] |

STATUS 필드 순서도 두 판이 같다 [확정]:
`VALID COUNT LOG POWER POWERGOOD OVERHEAT EXTCLKPRESENT BACKPLANE_TEMP P2V5_V/I P5V_V/I P6V_V/I N6V_V/I P17V_V/I N17V_V/I P35V_V/I N35V_V/I P100V_V/I N100V_V/I USER_V/I HEATER_V/I FANTACH` → 이어서 `MOD%d/…` 군.

**응답 접두 서식이 바뀐 것은 GUI·ICS 양쪽에 무해하다** [확정]. 1252 는 파싱한 참조번호를 대문자 2자리 hex 로 **재포맷**하고(`<%02X`), 1271 은 받은 두 글자를 **그대로 되울린다**(`<%c%c`). GUI 는 `>` + `hex(msgref,2).toUpper()` 로 보내고 응답을 `response.mid(1,2).toInt(&ok,16)` 로 되읽으므로(`archon.cpp:337-338, 362`) 어느 쪽이든 같은 값이 나온다. `ics_archon` 도 같은 규약이다.

> ⚠️ 다만 **되울림 방식은 잘못된 참조번호를 정정해 주지 않는다.** 소문자 hex 를 보내면 1252 는 대문자로 되돌려 주고 1271 은 소문자 그대로 되돌려 준다. 두 구현 다 `toInt(16)`/`int(...,16)` 로 받으므로 실무 영향은 없다 [확정]. 그러나 **응답을 문자열로 비교하는 소비자가 있다면 그쪽은 깨진다** [유력].

### (d) ⚠️ 이 판정의 진짜 한계 — 우리는 1261 을 보지 못했다

**여기서 등급을 정직하게 갈라야 한다.**

| 명제 | 근거 | 등급 |
|---|---|---|
| **1252 ↔ 1271** 의 키 집합·응답 필드가 같다 | 두 이미지를 직접 대조했다 | **[확정]** |
| **1261 → 1271** 이 ACF 문법을 바꾸지 않는다 | 1261 이미지가 **우리에게 없다**. 다만 1252 와 1271 이라는 **19빌드 폭의 양 끝에서 키 집합이 완전히 같으므로**, 그 사이에 낀 1261 에서만 키가 늘었다 줄었다 할 개연성은 매우 낮다 | **[유력]** |
| Rev F 유닛(113 · GUI-162)의 파서 수치 상한이 Rev H 와 같다 | 문자열 테이블이 완전히 대응하나 **1252 를 디스어셈블하지 못했다** | **[추정]** |

> **실무 결론은 [유력] 로도 충분하다.** 우리가 굽는 대상은 **ACF 로 확인된 Rev H 다섯**이고, 그 유닛에 지금 올라가 있는 1261 과 굽게 될 1271 사이에서 ACF 를 다시 쓸 일은 없다는 뜻이기 때문이다. 다만 **보고서에는 "1261 을 직접 확인한 것이 아니다" 를 반드시 남겨야 한다** — 뒤에 문제가 생겼을 때 이 문장이 있고 없고가 갈린다.

---

## 10.9 ⭐ 오토페치 송출 헤더가 바뀌었다 — §10.1.2 정정

### (a) 사실

| 항목 | 1252 (Rev F) | 1271 (Rev H) | 등급 |
|---|---|---|---|
| 명령 `AUTOFETCH` | 있음 (`<SFAUTOFETCH=%d`) | 있음 (`@<SFAUTOFETCH=%d`) | [확정] |
| 명령 `FASTAUTOFETCH` | **없음** | **있음** | [확정] |
| **송출 헤더** | **`<XF:`** (고정 4바이트, 뒤에 바이너리) | **없음** | [확정] |
| **송출 헤더** | 없음 | **`<QF%d%08X%04X%04X%08X%08X`** | [확정] |

### (b) ⭐ 헤더 설계의 뜻 — 두 판 모두 "hex 가 아닌 글자" 를 표지로 쓴다

`FETCH` 응답의 프리앰블은 `<` + 참조번호 2자리 hex + `:` 이다(`archon.cpp:509`). **`<XF:` 는 그와 글자 수가 같고 자리도 같은데, 첫 글자가 `X` 라서 hex 로 해석될 수 없다.** `<QF…` 의 `Q` 도 마찬가지다. 즉 **두 판 모두 "이것은 요청에 대한 응답이 아니라 자발적 송출이다" 를 참조번호 자리의 비-hex 글자로 표시하도록 설계돼 있다** [유력].

그렇다면 두 판의 차이는 다음과 같이 읽힌다 [추정]:

- 1252 `<XF:` — **고정 4바이트 표지 + 바이너리**. `FETCH` 응답과 **프레이밍이 같다**. 즉 `FETCH` 용으로 쓴 수신 코드를 거의 그대로 재사용할 수 있다.
- 1271 `<QF…` — **자기서술형 텍스트 헤더**. 프레임번호·주소·폭·높이·타임스탬프로 보이는 6필드를 헤더가 직접 싣는다. 수신 측이 `FRAME` 을 따로 물어보지 않아도 되도록 바꾼 것으로 읽힌다.

### (c) ⚠️ 기존 §10.1.2 의 정정 사항 — 두 곳이 틀렸다

**§10.1.2 는 `<XF:` 의 존재를 몰랐다.** 그 때문에 두 가지가 어긋난다.

| # | §10.1.2 의 서술 | 실제 | 조치 |
|---|---|---|---|
| 1 | `<QF…` 가 1271 에만 있으므로 "`FASTAUTOFETCH` 와 **함께 들어온** 신설 형식" 이라고 읽었다 | 사실관계는 맞으나 **결론이 틀렸다.** 1252 에도 오토페치 송출 헤더가 이미 있었다(`<XF:`). 따라서 `<QF…` 는 *없던 기능이 생긴 것*이 아니라 **있던 송출 헤더가 교체된 것**이다 | ⭐ **표에 `<XF:` 행을 추가하고 "신설" → "교체" 로 고칠 것** |
| 2 | *"같은 이미지에 `TIMER=%08X%08X` 가 있어(§4.4) 마지막 두 칸이 타임스탬프 쌍이라는 것이 뒷받침된다"* | ⚠️ **틀렸다.** `TIMER=%08X%08X` 는 **1252** 의 서식이고, `<QF…` 가 있는 **1271 의 `TIMER` 서식은 `%016lX` 한 칸**이다(§10.7(c)). 같은 이미지 안의 뒷받침이 아니다 | ⭐ **이 문장을 삭제할 것.** `<QF…` 필드 대응 해석은 뒷받침을 잃었으므로 [유력]→**[추정]** 으로 강등 |

정정 후의 등급 정리:

| 명제 | 등급 |
|---|---|
| `<XF:`(1252) → `<QF…`(1271) 로 오토페치 송출 헤더가 **교체됐다** | [확정] |
| `<QF…` 가 `FASTAUTOFETCH`(또는 `AUTOFETCH`)의 송출 헤더다 | [유력] |
| `<QF…` 의 필드 대응(프레임번호·주소·폭·높이·타임스탬프) | **[추정]** (강등) |

### (d) 영향 범위

| 대상 | 영향 | 등급 |
|---|---|---|
| **벤더 GUI 1259** | **없다.** GUI 는 `AUTOFETCH` 계열을 **전혀 보내지 않는다** — `grep -rn "LOCKT\|AUTOFETCH" src/*.cpp src/*.h` 0건. 화면의 "Auto Fetch" 체크박스는 GUI 내부의 반복 `FETCH` 를 켜는 것이지 와이어 명령이 아니다 | [확정] |
| **`ics_archon`** | **없다.** 이 계열은 코드에 0건이고 금지 규칙으로 막혀 있다(`DevNote.md:2094`, `tools/ics_archon_buftest.py:61`) | [확정] |
| **오토페치 스트림을 직접 받는 외부 소비자** | **깨진다.** 프레이밍 자체가 "고정 4바이트 + 바이너리" 에서 "가변 길이 텍스트 헤더" 로 바뀌었다 | [확정] |

> **§10.1.3 의 채택 판단(오토페치 계열을 쓰지 않는다)은 그대로 유효하다.** 오히려 근거가 하나 늘었다 — **송출 헤더가 판 사이에 이미 한 번 바뀐 전례가 있다.** 문서화되지 않은 형식에 의존하면 다음 판올림에서 또 깨진다는 뜻이다 [확정].

---

## 10.10 1271 에 새로 들어온 것 — 신규 기능·진단·네트워크

§10.8 이 "ACF 는 안 바뀌었다" 를 확정했으므로, 실제 변경은 아래로 좁혀진다.

| # | 변경 | 성격 | 등급 |
|---|---|---|---|
| 1 | **`FASTAUTOFETCH` 명령 신설** + 송출 헤더 `<XF:`→`<QF…` 교체 | 기능 추가 + **비호환 변경**(우리는 미사용) | [확정] |
| 2 | **네트워크 스택 개편** | 아래 (a) | [유력] |
| 3 | **`NET ID` / `NET RESET` UDP 대역외 명령** | 아래 (b) | [유력] |
| 4 | **진단 개선** — `Unexpected ADC latency measured (slot %d = %d)` 가 실측치를 함께 찍는다 | 순수 개선 | [확정] |
| 5 | **`assertion "%s" failed: file "%s", line %d%s%s`** — newlib assert 가 들어 있다 | 진단 | [확정] |
| 6 | **`flash_test:` 계열** — `wrsr error`, `we error`, `set QE to 1 complete` | QSPI 플래시 자체 시험 루틴 | [확정] |
| 7 | **모듈 형 19(ADQ 로 보임) 지원** | 아래 §10.11 | [유력] |
| 8 | **`LOCKT` 소멸** | 우리는 미사용 | [유력] |

### (a) 네트워크 스택 개편

1271 에만 있는 로그 문자열군 [확정]:

```
Network startup
Network loop begun
Network link up
Network link down
Applying new network configuration, IP: %d.%d.%d.%d
```

1252 에는 대응 문자열이 하나도 없다. **CPU 가 MicroBlaze+lwIP 계열에서 Cortex-A53 로 바뀌면 네트워크 스택도 통째로 갈아엎을 수밖에 없으므로, 이것 자체는 §10.7(c) 가 말한 "CPU 교체의 부산물" 로 보는 것이 자연스럽다** [유력]. 매뉴얼 p.15 의 *"Rev H backplanes currently support up to four simultaneous connections"* 도 같은 갈래다.

⚠️ **다만 판올림 위험 평가에서는 이 항목이 가장 무겁다.** 링크가 살아 있어야 되돌릴 수 있는데, 바뀐 부분이 바로 그 링크이기 때문이다(§10.12).

### (b) `NET ID` / `NET RESET` — UDP 대역외 관리 경로

1271 에만 있는 문자열 4개 [확정]:

```
NET ID
NET ID UDP command received
NET RESET
NET RESET UDP command received
```

**해석**: TCP 4242 세션과 별개로 **UDP 로 받는 대역외(out-of-band) 관리 명령**이 신설된 것으로 보인다 [유력]. `NET ID` 는 브로드캐스트 탐색(장비가 자기 IP/ID 를 알리는 용도), `NET RESET` 은 네트워크 설정 초기화로 읽힌다 [추정].

⭐ **이것은 판올림 위험을 낮출 수 있는 요소다.** 판올림 뒤 IP 설정이 어긋나 TCP 로 못 붙는 상황이 와도 UDP 탐색·초기화 경로가 살아 있다면 복구할 수 있기 때문이다. **다만 포트 번호도 패킷 형식도 우리는 모른다.**

> ⭐ **STA 문의 목록에 추가할 것** — *"1271 의 `NET ID`/`NET RESET` UDP 명령은 어느 포트에서 어떤 형식으로 받는가. 네트워크 설정이 어긋났을 때 복구 수단으로 쓸 수 있는가."* 이 답이 있으면 §10.12 의 되돌리기 위험이 실질적으로 줄어든다.

⚠️ **동시에 보안 면에서는 새 노출면이다.** 인증 없는 UDP 명령이 `NET RESET` 을 받는다면, 관측 중 오작동·오송신 한 방으로 링크가 끊길 수 있다. 컨트롤러는 전용 네트워크 포트에 물려 두라는 매뉴얼 p.15 의 권고를 **판올림 후에는 더 엄격히 지켜야 한다** [유력].

### (c) 모듈 명령 어휘의 변화

1271 에만 있는 모듈 송신 명령 두 개: **`>AF`**, **`>AQAA`** [확정]. 둘 다 AD 네임스페이스에서 쓰이고 형 19(ADQ)와 짝을 이룬다(§10.11).

그 밖의 모듈 명령 어휘(드라이버 `>D…`, AD `>A…`/`>P…`/`>C…`/`>G…`/`>W…`, 바이어스 `>B…`, 히터 `>H…`, VCPU `>V…`)는 **두 판이 동일**하다 [확정]. 즉 **우리 실기에 꽂힌 모듈(Driver Rev D · ADM · AD · LVXBias · HVXBias · LVDS · HeaterX)과 백플레인 사이의 명령 어휘는 판올림으로 바뀌지 않는다.**

---

## 10.11 ⭐ 모듈 형 19 — `ADQ` 로 보이고, GUI 의 센티널과 정면으로 충돌한다

### (a) 형 19 가 실재한다 — 비트마스크가 증거다

1271 코드의 "이 슬롯이 AD 계열인가" 판정은 **상수 비트마스크 한 개**로 이뤄진다 [확정 · 1271 코드 원문]:

```
005b4aa0  mov  x11, #0xe004
005b4acc  movk x11, #0xa, lsl #16      ; x11 = 0x000A_E004
005b4bac  lsr  x9, x11, x9             ; (mask >> 모듈타입) & 1
```

`0x000AE004` 의 켜진 비트는 **{2, 13, 14, 15, 17, 19}** 다.

| 비트 | 형 | 이름 | 출처 |
|---:|---:|---|---|
| 2 | 2 | AD | `archon.h:31` |
| 13 | 13 | ADF | `archon.h:42` |
| 14 | 14 | ADX | `archon.h:43` |
| 15 | 15 | ADLN | `archon.h:44` |
| 17 | 17 | **ADM** | `archon.h:46` |
| **19** | **19** | **?? — GUI 에 대응 모듈 없음** | — |

### (b) 형 19 = `ADQ` [유력]

세 가지가 한 곳으로 모인다.

| 근거 | 내용 | 등급 |
|---|---|---|
| 1 | 1271 에만 있는 오류 문자열 **`Error configuring ADQ (slot %d)`**. 1252 에는 `ADQ` 문자열이 **전혀 없다** | [확정] |
| 2 | 1271 에만 있는 신규 AD 계열 모듈 명령 **`>AF`**, **`>AQAA`** — `AQ` 는 이름과 맞아떨어진다 | [확정] |
| 3 | 형 19 의 설정 디스패치가 **AD 네임스페이스(0x58c96c)로 간다** — 형 2·13·14·15 와 같은 자리다. 즉 `CLAMP1..4`·`PREAMPGAIN` 을 쓰는 계열이다 | [확정 · 1271 코드] |

→ **형 19 = `ADQ`, 1271 에서 신설된 AD 계열 비디오 모듈** [유력]. 매뉴얼에도 GUI 에도 없는 모듈이다.

⚠️ **채널 수는 모른다** [확인불가]. 채널 파워다운 명령이 `>P%X`(4비트) · `>P%02X`(8비트) · `>P%05X`(18비트=ADM) 세 종류인데, 어느 것이 ADQ 몫인지 이 이미지만으로는 가르지 못했다.

### (c) ⚠️ GUI `archon.h` 는 19 를 센티널로 쓴다 — 충돌이다

**이것이 이 절에서 실무적으로 가장 중요한 발견이다.**

`archon.h:48` 이 `#define MOD_TYPE_UNKNOWN 19` 로 **19 를 "유효 범위의 끝" 표지로** 쓰고 있고, GUI 는 그것을 **상한 비교**로 쓴다 [확정]:

| 위치 | 코드 | 형 19 가 들어오면 |
|---|---|---|
| `archongui.cpp:2038` | `if ((id <= MOD_TYPE_NONE) \|\| (id >= MOD_TYPE_UNKNOWN))` | 슬롯 표에 **`"Unknown"`** 으로 찍히고 rev·version·id 칸이 **전부 비워진다** |
| `archongui.cpp:2127` | 같은 조건 → `continue` | **모듈 객체를 만들지 않는다** → 탭 없음, 설정 키 없음, STATUS 파싱 없음 |
| `archon.cpp:1053` (`flashMod`) | 같은 조건 → `LOGERROR("Empty or unknown module")` | **펌웨어를 구울 수 없다** |
| `archon.cpp:1184` (`verifyMod`) | 같은 조건 → 같은 오류 | **검증할 수 없다** |

즉 **ADQ 모듈이 꽂힌 백플레인에 GUI 1259 를 붙이면, 그 슬롯은 "Unknown" 으로 표시되고 조작·플래시가 전부 막힌다** [확정].

> ⭐ **판정: 이것은 GUI 쪽 결함이다.** 형 번호를 열거 상수의 마지막 값으로 두고 그것을 상한 비교에 재사용하면, **FW 가 형을 하나 늘릴 때마다 GUI 가 그 모듈을 "없는 것" 으로 만든다.** 1271 이 실제로 형을 하나 늘렸으므로 이 결함은 **가설이 아니라 이미 실현된 상태**다.
>
> ⚠️ **다만 KMTNet 실기에는 ADQ 모듈이 없다** — science 는 슬롯 5·8 의 ADM(형 17), guide 는 슬롯 5·6 의 AD(형 2)다(§7.7). 따라서 **지금 당장 우리에게 나타나는 증상은 없다** [확정]. 나중에 비디오 모듈을 교체·증설할 때 되살아나는 종류의 결함이다.

**§7.8(모듈 체계의 결함)에 항목 하나를 보탤 것을 제안한다.**

| # | 내용 | 위치 | 등급 |
|---|---|---|---|
| **M10** | **형 번호 센티널과 상한 비교의 겸용.** `MOD_TYPE_UNKNOWN 19` 를 `id >= MOD_TYPE_UNKNOWN` 상한으로 4곳에서 재사용한다. FW 1271 이 형 19(ADQ)를 실제로 쓰기 시작했으므로 **GUI 1259 는 ADQ 슬롯을 표시·조작·플래시하지 못한다.** 센티널을 255 등으로 옮기거나 상한을 별도 상수로 분리해야 한다 | `archon.h:48`, `archongui.cpp:2038`·`:2127`, `archon.cpp:1053`·`:1184` | **중(잠복)** |

### (d) ⭐ 우리 `parse.py` 에 대한 시사점

`ics_archon/archon/parse.py` 의 두 상수와 대조했다.

| 우리 상수 | 현재 값 | FW 1271 비트마스크와 대조 | 판정 |
|---|---|---|---|
| **`AD_TYPES`** | `frozenset({2, 13, 14, 15, 17})` | FW 마스크 `{2,13,14,15,17,19}` 에서 **19 를 뺀 것과 정확히 일치** | ✅ **펌웨어가 우리 집합을 확인해 주었다** [확정] |
| **`MODULE_TYPES`** | `0~18` 전량(19 없음) | FW 에 형 19 가 실재한다 | ⚠️ 형 19 가 오면 이름표가 없다 |

두 가지를 구분해서 처리할 것을 제안한다.

1. ⭐ **`AD_TYPES` 는 지금 값이 맞다.** 여기에 근거가 하나 늘었다 — 지금까지는 매뉴얼 p.46 + `archon.h` 열거 + 실기 ACF 였는데, 이제 **백플레인 FW 가 실제 판정에 쓰는 비트마스크 원문**이 근거로 붙는다. 이것이 가장 상위 근거다. 주석에 `0x000AE004` 와 그 근거 주소(`0x5b4aa0`/`0x5b4acc`/`0x5b4bac`, 이미지 `archonbackplanerevh_1_0_1271.mcs`)를 남길 만하다.
2. **`MODULE_TYPES` 에 19 를 넣을지는 서두르지 않는다.** 이름이 `ADQ` 라는 것 자체가 [유력]일 뿐이고, KMTNet 구성에는 없는 모듈이다. **`AD_TYPES` 에는 넣지 않는다** — §7.1 의 원칙(*이름표를 늘리는 것과 판정을 늘리는 것은 다르다*)이 여기에도 그대로 적용된다.
3. ⭐ **다만 `archon.h` 가 저지른 실수는 답습하지 않아야 한다.** 우리 쪽에 `19` 를 "알 수 없음" 의 뜻으로 쓰는 자리가 생기면 같은 함정에 빠진다. **모르는 형 번호는 `MODULE_TYPES` 조회 실패로 처리하고, 별도 센티널 상수를 만들지 않는 현재 방식이 옳다** [확정].

⚠️ 그리고 §7.1 형 번호표의 **형 19 행(`MOD_TYPE_UNKNOWN` / "GUI 전용")에 각주를 달아야 한다** — *"FW 1271 은 형 19 를 실제 AD 계열 모듈(ADQ 로 보임)로 쓴다. GUI 의 센티널 용법과 충돌한다"*.

---

## 10.12 ⭐ 판올림 실행 판단 — ACF 로 확인된 Rev H 다섯을 1261 → 1271 로 구워도 되는가

§10.4 가 *"굽기 전에 판올림 여부를 운영자가 결정해야 한다"* 로 열어 둔 물음에, 이번 분석이 답할 수 있는 만큼 답한다.

### (a) 판단 재료 정리

| # | 재료 | 방향 | 등급 |
|---|---|---|---|
| 1 | **ACF 문법이 바뀌지 않는다.** `[CONFIG]` 키·STATUS/SYSTEM/FRAME 필드 추가·삭제 0 | ✅ **찬성** | 1252↔1271 [확정] / 1261→1271 [유력] |
| 2 | **모듈 명령 어휘가 바뀌지 않는다.** 우리가 쓰는 모듈 7종 전부 | ✅ 찬성 | [확정] |
| 3 | **프레임 사슬(`FRAME`→`LOCK`→`FETCH`→`LOCK0`)이 바뀌지 않는다.** 명령·응답 서식 모두 동일 | ✅ 찬성 | [확정] |
| 4 | **진단이 개선된다.** ADC latency 실측치 표기, assert, flash 자체시험 | ✅ 찬성 | [확정] |
| 5 | **우리가 쓰지 않는 것만 바뀌었다.** `LOCKT`(미사용) · 오토페치 헤더(미사용) · ADQ(미보유) | ✅ 찬성 | [확정] |
| 6 | ⚠️ **되돌릴 이미지가 없다.** Rev H 유닛의 현행 1261 `.mcs` 를 우리는 갖고 있지 않다 | ❌ **반대 — 가장 무겁다** | [확정] |
| 7 | ⚠️ **1261 자체를 확인하지 못했다.** 보유·분석한 것은 1252 와 1271 이다. 1261→1271 판정은 양 끝을 재서 사이를 추정한 것 | ❌ 반대 | [확정] |
| 8 | ⚠️ **네트워크 스택이 개편됐다.** 되돌리기가 의존하는 바로 그 경로다 | ❌ 반대 | [유력] |
| 9 | ⚠️ **빌드 시각이 2026-08-30 이다.** 반입 나흘 전 — 현장 운용 이력이 사실상 없다 | ❌ 반대 | 빌드일 [유력] |
| 10 | ⚠️ **대상이 다섯이고, 그것이 전부가 아니다.** ACF 로 Rev H 가 확인된 것은 KMTC-SCI-101 · KMTC-SCI-102 · KMTS-SCI-101 · KMTS-SCI-102 · KMTS-GUI-161 이다. 한 대만 구우면 FW 판이 갈린다 | ⚖️ 절차 제약 | [확정] |
| 11 | ⚠️ **플래시 UI 에 확인 대화상자가 없다.** 메뉴를 잘못 누르면 곧장 실행된다(§10.5) | ⚖️ 절차 위험 | [확정] |
| 12 | **판올림해야 할 적극적 이유가 없다.** 1271 의 신규 기능(FASTAUTOFETCH · ADQ)은 **우리가 쓰지 않거나 갖고 있지 않은 것**이다 | ❌ 반대 | [확정] |

### (b) ⭐ 결론

> ### **지금 굽지 않는다.** 기술적으로는 안전해 보이지만, **되돌릴 수단이 없는 상태에서 얻을 것이 없는 판올림**이기 때문이다.
>
> 판정 등급: **[유력]** — 위험이 크다는 판정이 아니라, **이득이 0에 가깝다는 판정**이다.

논리를 한 줄로 적으면 이렇다. **§10.8 이 "구워도 ACF·프레임 사슬은 안 깨진다" 를 보였고, 동시에 §10.10 이 "구워서 새로 얻는 것도 없다" 를 보였다.** 위험이 낮아도 이득이 0이면 되돌릴 수 없는 조작을 할 이유가 없다. 게다가 위험이 낮다는 판정 자체가 **1261 을 직접 보지 못한 채 양 끝을 재서 낸 것**이다.

### (c) 그래도 굽는다면 — 만족해야 할 선행 조건

운영 사정으로 판올림이 필요해지면, 아래를 **순서대로** 채운 뒤에 진행할 것을 제안한다.

| 순 | 조건 | 이유 |
|---:|---|---|
| 1 | **STA 로부터 `archonbackplanerevh_1_0_1261.mcs` 를 확보한다** | 되돌리기 수단. 이것 하나로 판단이 뒤집힌다 — **가장 값싸고 가장 효과가 큰 조치** |
| 2 | **`NET ID`/`NET RESET` UDP 경로의 포트·형식을 STA 에 확인한다**(§10.10(b)) | TCP 로 못 붙는 상황의 대역외 복구 경로 |
| 3 | **`FASTAUTOFETCH` 의 뜻과 `<QF…` 필드 순서를 함께 문의한다**(§10.1.3) | 이미 문의 목록에 있다. 같은 편에 실어 보낼 것 |
| 4 | **관측 임계도가 가장 낮은 1대에 먼저 굽는다** | 다섯을 한꺼번에 올리지 않는다. §10.4 의 "어느 범위까지 올릴지" 에 대한 답 |
| 5 | **그 1대에서 회귀 확인**: ① `SYSTEM`/`STATUS` 전 필드 수신 ② 현행 ACF 그대로 `WCONFIG`→`APPLYALL` ③ `FRAME`→`LOCK`→`FETCH`→`LOCK0` 프레임 100장 ④ **ACF 왕복 무손실 확인** ⑤ 벤더 GUI 접속·표시 | §10.8 의 [유력] 판정을 실측으로 [확정]으로 올리는 절차 |
| 6 | **최소 한 주기(관측 1주) 운용 뒤 나머지 4대** | 판이 갈린 상태를 오래 끌지 않되, 한 번에 전부 잃지도 않는다 |

⚠️ **Rev F 2대(KMTK_SCI_113 · KMTK_GUI_162)는 이 논의의 대상이 아니다.** 보유 이미지가 실기와 **같은 판(1252)** 이고, `archonbackplanerevf_…` 는 Rev H 유닛에 파일명 검증에서 걸려 아예 굽히지 않는다(§10.4) [확정]. **그리고 Rev F 는 애초에 다른 CPU 이므로**(§10.7(b)) 1271 계열 이미지가 존재할 수도 없다.

### (d) 이 판정이 닫히려면 필요한 것 [실측대상]

| # | 미결 | 닫는 방법 |
|---|---|---|
| 1 | 1261 의 `[CONFIG]` 키 집합·응답 필드 | 1261 이미지 확보 후 같은 방법으로 대조. 또는 **실기 101 에 붙어 `SYSTEM`/`STATUS` 응답을 그대로 받아 두는 것**만으로도 (c)-5 의 비교 기준이 생긴다 — **판올림 전에 반드시 떠 둘 것** |
| 2 | 1252(Rev F)의 파서 수치 상한 | MicroBlaze 디스어셈블러(`mb-objdump`·Ghidra) 또는 실기 응답 |
| 3 | `FASTAUTOFETCH`·`<QF…`·`NET *` 의 정확한 규약 | STA 문의 |
| 4 | ADQ(형 19)의 정체·채널 수 | STA 문의. 우리 구성에는 없으므로 우선순위 낮음 |

---

## 부록 — 이 절이 근거로 삼은 것

| 자료 | 위치 |
|---|---|
| 펌웨어 원본(읽기전용) | `ArchonGUI/__reference/ArchonFW/` — `.mcs` 4종 |
| 작업 사본(펼친 바이너리) | 세션 스크래치패드 `pass2/fwbin/` |
| 디스어셈블 대상 | `archonbackplanerevh_1_0_1271` 만 (AArch64, capstone). 주소는 **로드 주소 기준**, 파일 오프셋 = 주소 − 0x18 |
| 벤더 소스 | `archongui_v1.0.1259.KMTNet_20260118_SSO/src/archon.h`·`archon.cpp`·`archongui.cpp` |
| 매뉴얼 | `Archon_manual_20210223.pdf` p.15(백플레인 X12 · CPU · 접속 수), p.46(형 번호표) |
| 우리 코드 | `ics_archon/ics_archon/archon/parse.py` — `MODULE_TYPES`, `AD_TYPES` |

---

# 11. ics_archon 관점의 시사점

세 갈래로 나눴다 — **벤더 코드가 확인해주는 것 / 우리가 놓쳤을 수 있는 것 / 고칠 것**.

## 11.1 ✅ 확인해주는 것 — 우리가 맞았다

| # | 항목 | 벤더 코드의 증언 | 등급 |
|---|---|---|---|
| A1 | **`data_bytes` 산식** | `frame_size = (samplemode ? 4 : 2) * framew * frameh` (`archon.cpp:1282~1284`). 우리 `parse.py:113` 의 `data_bytes = (4 if samplemode else 2) * width * height` 와 **완전히 같다** | [확정] |
| A2 | **`raw 를 안 읽는 것이 정상`** | raw 는 이미지 fetch 에 안 섞이고 `baseaddr + BUFnRAWOFFSET` 에서 **별도 2차 `FETCH`** 이다(`:1361~1364`). 크기도 `BUFnRAWBLOCKS × BUFnRAWLINES × 2048` 로 따로 계산한다. 실기 ACF 가 `RAWENABLE=1` 인데 우리가 raw 를 안 읽는 것은 **결함이 아니다** | [확정] |
| A3 | **`LOCK`→`FETCH`→`LOCK0` 루프** | 벤더 GUI 가 매 프레임 똑같이 한다(`archongui.cpp:1831`, `archon.cpp:1386`). 우리 ICS 와 알고리즘이 같다 | [확정] |
| A4 | **`lock_buffer=true`** | `LOCK` 없이 fetch 하면 약 26% 확률로 두 노출이 섞인다 | [실측] |
| A5 | **`BURST_LEN=1024`** · **`POWER_STATES` 0~5** | `archon.h:17`, `:52`. 우리 값과 양쪽 일치 | [확정] |
| A6 | **모듈 형 17=ADM · 18=HVYBias** | 우리가 ACF 실측으로 넣은 두 값을 `archon.h:46~47` 이 **확인**해 준다 | [확정] |
| A7 | **`APPLYALL` 이 `POWERON` 의 전제** | 매뉴얼 p.51 + 실기 `?xx` 거부 | [실측] |
| A8 | **`RAW_BLOCK_SIZE=2048` = 1024 샘플** | `archon.h:20` + `setRawSize(rawblocks*2048/2, rawlines)`(`:1315`). 매뉴얼 p.70 "multiple of 1024" 와 자기정합적. science `RAWSAMPLES=8192` = 정확히 8블록 | [확정] |
| A9 | **키 표기 정규화** | 코드·프로토콜·매뉴얼은 전부 `/`, `.acf` 파일만 `\`. `\`→`/` 로 정규화하면 매뉴얼 p.57~63 표기와 그대로 대응된다 | [확정] |

## 11.2 ⚠️ 놓쳤을 수 있는 것 — 확인해 봐야 한다

| # | 항목 | 내용 | 우리 쪽 조치 |
|---|---|---|---|
| B1 | ⭐ **모듈 형 6 · 16** | `parse.py::MODULE_TYPES` 에 **6(ATLAS)이 아예 빠져 있고** 16 을 "모른다" 로 뒀다. `archon.h` 정본은 **6=ATLAS, 16=DRIVERX** 이다. 둘 다 지금 닫을 수 있다 | 표에 추가 |
| B2 | ⭐ **raw 2차 fetch 경로** | raw 를 읽고 싶으면 이미지 fetch 뒤에 `FETCH<baseaddr+RAWOFFSET><lines>` 를 한 번 더 내면 된다. `RAWENABLE=1` 로 운영 중이니 **언제든 켤 수 있는 기능**이다. 지금 안 읽는 것은 결함이 아니지만, **쓰려면 코드를 추가해야 한다** | 필요 시 구현. 크기 = `BUFnRAWBLOCKS × BUFnRAWLINES × 2048`, 폭 = `BUFnRAWBLOCKS × 1024` 샘플, 항상 16bit |
| B3 | ⭐ **`LOCKT` / `AUTOFETCH` / `FASTAUTOFETCH`** | FW 1252 표에는 `LOCKT`·`AUTOFETCH` 가 있는데(다른 세션 발견) **벤더 GUI 소스에는 0건**이다 — STA 자기 클라이언트도 쓰지 않는다. ⭐ **1271 에서는 `LOCKT` 이 빠지고 `FASTAUTOFETCH` 가 생겼다**(§10.1.1). 송출 형식은 `<QF…` 로 보인다(§10.1.2). ⚠️ **셋 다 임의로 실행하지 말 것.** GUI 의 "Auto Fetch" 체크박스는 이 명령들과 **무관하다** — GUI 가 `LOCK`+`FETCH` 를 스스로 반복하는 것뿐이다. **채택 판단은 §10.1.3 — 쓰지 않는다** | STA 문의에 첨부 |
| B3-1 | ⭐ **`LOCKT` 제거가 우리에게 주는 영향 — 없다** | 본 프로젝트는 `LOCK<n>`·`LOCK0` 만 보낸다(`controller.py:1186`·`:1270`). `LOCKT` 은 코드에 0건이고 문서에서도 금지 규칙으로만 나온다. 그리고 우리가 쓰는 잠금 경로의 보고 형식(`RBUF=%u` · `WBUF=%u` · `BUFnRAWBLOCKS/RAWLINES`)은 **1252 와 1271 이 문자열까지 동일**하다 | 조치 불필요. 다만 접두 매칭 때문에 1271 에서 `LOCKT` 을 보내면 이제 **`LOCK` 에 인자 `T…` 로 붙어 조용히 오해석**되므로 "보내지 않는다" 규칙은 유지한다 |
| B4 | ⭐ **폴링 버려짐** | `command()` 는 바쁘면 **큐에 안 쌓고 거절**(`archon.cpp:187`). 그래서 FETCH 동안 `FRAME` 응답이 한 번도 오지 않는다 — GUI 가 얼어붙어 보이는 착시의 기전이다. **우리 ICS 는 이것을 답습하면 안 된다.** 상태 폴링과 데이터 fetch 를 분리하거나, 최소한 "폴이 밀렸다" 를 로그로 남겨야 한다 | 설계 반영 |
| B5 | ⭐ **`APPLYALL` 전제** | `APPLYALL` **끝나면 CCD 전원이 꺼진 상태**가 된다(p.51). 그래서 `APPLYALL` → `POWERON` 을 반드시 이어서 해야 한다. 그리고 `RESETTIMING`/`HOLDTIMING`/`POWERON` 같은 명령은 `writeConfig()` 를 **부르지 않으므로**, 설정을 바꾸고 이것들만 내면 **아무 효과 없다** | 절차 규정 |
| B6 | **부분 적용이란 것이 없다** | 벤더는 어느 Apply 든 `CLEARCONFIG` + 전체 재전송이다. 우리가 "슬롯 하나만 갱신" 을 하고 싶다면 **GUI 동작을 따라하지 말고 프로토콜 수준에서 따로 설계**해야 한다 | 설계 판단 |
| B7 | **`VALID` 게이트** | 매뉴얼 p.47 은 `VALID=0` 이면 나머지 STATUS 가 전부 무효라고 규정하는데 **GUI 는 게이트로 쓰지 않는다.** 우리는 `VALID=1` 일 때만 채택하도록 규정하고, `COUNT` 로 신선도까지 봐야 한다 | 규정 |
| B8 | **단위 4종** | 시스템 레일 전류 **A** / 모듈 바이어스 전류 **mA** / 백플레인·모듈 온도 **℃** / **히터 센서 온도 K** (설정 target·limit 은 ℃). 섞으면 안 된다 | 변환 명시 |
| B9 | **`POWER` ≠ `POWERGOOD`** | `POWER` 는 CCD 전원, `POWERGOOD` 은 컨트롤러 공급전원. 그리고 `POWERGOOD=1` 은 **"감시하도록 켜둔 레일만" 정상**이라는 뜻이다. 레일별 `_V` 를 p.41 범위와 따로 대조하는 이중 확인이 필요하고, **안 쓰는 레일(N35V·USER·P100V·N100V)은 알람에서 빼야 한다** | 알람 설계 |
| B10 | **Rev F 동시 접속 1개** | 113(Rev F)은 ICS 와 GUI 가 **동시에 붙지 못한다**. 101(Rev H)은 4개까지. 운영 절차에 명시 | 문서화 |
| B11 | **인식 못 한 명령 = 무응답** | 오타 명령은 `?` 조차 오지 않는다. **타임아웃이 없으면 그대로 멈춘다.** 통신 계층 규약에 규정해 두어야 한다 | 규정 |
| B12 | **TAPLINE 산식으로 슬롯 역산** | FITS 헤더에 채널→슬롯→물리 앰프를 기록할 때 쓰면 된다 — ADM 은 `slot = 5 + (ch-1)/18`, AD 는 `slot = 5 + (ch-1)/4` | 헤더 작성 |
| B13 | **SHP/SHD 8의 배수** | ADM 은 12.5 MHz 샘플을 8회 복제(디더링)하므로 8의 배수가 권고다(p.69). science ACF 는 이미 지키고 있다(72/112/136/200) — **바꿀 때 깨뜨리지 않도록 규정해 두어야 한다** | 검증 규칙 추가 |
| B14 | **바이트 순서** | 매뉴얼 무언급. GUI 는 소켓 바이트를 `unsigned short*` 버퍼에 **그대로 복사**하고 변환 코드가 없다 → **호스트 네이티브(x86 리틀엔디언 uint16)** | [유력]. 우리도 같게 |

## 11.3 🔧 고칠 것 / 답습하지 말 것

| # | 항목 | 벤더 결함 | 우리가 할 것 |
|---|---|---|---|
| C1 | **`RAWSEL` 왕복** | `qBound(0,…,15)` 가 16 이상을 조용히 깎는다(`archongui.cpp:2568`). ⭐ **이것이 FW 제약이 아니라 GUI 결함임이 확정됐다** — FW 파서 상한은 **71** 이다(FW 1271 `0x59b7b4`) [확정] | 우리 파서는 **깎지 말고 원값 보존**. 검증은 **0~71 로**(15 가 아니다). 범위 밖이면 경고만 |
| C2 | **`VCPU_INREG` off-by-one** | 쓰기 0기점 / 읽기 1기점, **5개 클래스 전부**. ⭐ **맞는 쪽은 0기점(쓰기)이고 읽기 경로가 틀렸다** — FW 는 `cmp #15` 로 0~15 를 받는다(FW 1271 `0x58c074`) [확정] | 우리는 **0기점으로 통일**(방침 유지, 근거 확정). 컨트롤러 기대값은 **Rev H 에 한해 확정**, Rev F 는 [추정] |
| C3 | **모르는 키 유실** | `parseUI()` 가 `config.clear()` 후 위젯에서 재구성 → GUI 가 모르는 키가 전부 사라진다 | 우리는 **원본 키를 보존하고 아는 키만 덮어쓰기** |
| C4 | **`PWR_STANDBY` early return** | STANDBY 면 온도·전압·모듈 상태 갱신이 통째로 멈춘다 | 절대 답습하지 말 것. STANDBY 도 나머지를 정상 갱신 |
| C5 | **`CONFIG` 가 결과를 갱신 안 함** | `setConfig` 뒤 `getResult()` 가 **직전 명령의 결과**를 반환 → `APPLYxxx` 가 조용히 건너뛰어질 수 있다 | 우리 명령 계층은 **명령마다 결과를 짝지어 돌려주기** |
| C6 | **재시도 없음** | 타임아웃 한 번에 즉시 실패 | 재시도 정책을 명시적으로 정하기(다만 부작용 있는 명령은 재시도 금지) |
| C7 | **MCS 체크섬 미검증** | 손상된 이미지를 그대로 굽는다 | 우리가 플래시를 다룰 일이 생기면 **체크섬 먼저 검증** |
| C8 | **확인 대화상자 없음** | Reboot·Erase Stored Config·Flash 가 곧장 실행된다 | 파괴적 명령은 **2단 확인** |
| C9 | **`ptc.txt`/`hplot.txt` 고정 이름 + `%0.0lf`** | 현재 작업 디렉터리 덮어쓰기, 평균값 소수점 소실 | 우리 산출물은 경로 지정 + 충분한 자릿수 |
| C10 | **FITS 헤더 7개뿐** | 노출시간·온도·탭 구성 아무것도 없다 | **KMTNet raw spec 헤더는 전적으로 ICS 몫**이다. GUI FITS 를 참고하면 안 된다 |
| C11 | **`WCONFIG` 키 순서** | `QMap` 사전순이라 ACF 원본 순서와 다르다 | FW 가 키 이름으로 파싱하므로 문제는 없지만, `RCONFIG` 되읽기 비교 시 순서를 기대하면 안 된다 |
| C12 | **부분 실패 복구 없음** | `writeConfig` 중간 실패 시 설정 메모리가 반쯤 지워진 채 남는다 | 우리는 실패 시 **상태를 로그로 남기고 재적용을 강제** |

---

### §11.3 이어붙임 — 2차 검토 추가분 (C13~C32)

> 아래는 1차 보고서 §11.3 의 C1~C12 표에 그대로 이어 붙이는 행이다. 열 구성은 기존과 같다.
> `벤더 결함` 칸 끝에 **도달** (실기에서 성립하는 조건) 과 **등급** (심각도 + 근거등급) 을 담았다.
>
> ⚠️ **등급 재검토 원칙.** 여기 실린 것은 전부 **GUI C++ 소스**를 읽은 결과이므로 코드 사실 자체는
> Rev F·Rev H 구분 없이 `[확정]` 이다. 다만 **도달 조건이 컨트롤러 펌웨어 거동에 의존하는 항목**은
> 근거가 다른 세션의 Rev H(FW 1.0.1261, AArch64) 실측뿐이고 **Rev F(FW 1.0.1252, MicroBlaze)는
> 디스어셈블도 실측도 없다.** 해당 항목은 Rev F 유닛(`KMTK_SCI_113` · `KMTK_GUI_162`)에 대해
> 등급을 한 단 낮춰 `[추정]` 으로 표기했다.

| # | 항목 | 벤더 결함 | 우리가 할 것 |
|---|---|---|---|
| C13 | **파일 열기가 워커의 프레임 버퍼를 재할당** | `Archon::fetchFrame()` 은 `frameMutex` 를 풀고(`archon.cpp:1335`) 원시 포인터로 수백 MiB 를 쏟는다 — **`Locked` 플래그가 유일한 보호**다. 그런데 `openFrame`/`openFrame(QString)`/`openFITS` 의 빈 버퍼 탐색은 `highestindex` 를 조건 없이 매 바퀴 덮어써(`archongui.cpp:3653~3661`) **전부 잠긴 경우 잠긴 버퍼를 `setSize()`** 하고, `openHDRFrame()` 은 아예 **조건 없이 모든 `Locked` 를 내린다**(`:3805~3807`). `setSize()` 는 치수가 다르면 `free`+`malloc` 한다(`frames.cpp:174~176`) — **워커가 해제된 영역에 계속 쓴다** | **도달**: 호스트 버퍼 2개가 모두 잠긴 구간이 자동 페치 중 매 프레임 존재하고, 그때 File→Open raw/FITS 를 실행하면 성립. 창 길이는 페치 시간에 비례하므로 science(1200×4700)는 넉넉하고 **guide(528×1033)는 짧다** ─ **등급 높음 [확정]**(코드) / 창 길이는 [추정] | 버퍼 소유권을 **플래그+관행이 아니라 이동(move)/큐**로 넘겨 두 곳이 같은 포인터를 못 잡게 한다. **"쓸 버퍼가 없다" 는 명시적 실패**로 규정하고 아무 인덱스로 떨어뜨리지 않는다 |
| C14 | **`setSize()` 반환값을 4곳 전부 무시** | `frames.cpp:176~185` 는 `malloc` 실패 시 **`Data=0` 으로 두면서 `m_width`/`m_height` 는 요청값 그대로 남기고 `-1`** 을 준다. GUI 는 네 곳 모두 반환값을 버리고 곧장 `QFile::read((char*)…Data, size)` 로 간다(`archongui.cpp:3671/3674`·`3736/3739`·`3814/3816`·`4359/4361`). **정작 `Archon::fetchFrame()` 은 같은 호출을 제대로 검사한다**(`archon.cpp:1308`·`1315`) — 벤더도 실패를 아는데 GUI 만 빠뜨렸다 | **도달**: `malloc` 실패. 현장 판이 **Qt 5.3 MinGW 32bit**(§11.2 N7)라 2 GiB 주소공간에 프레임 2개 + raw 2개 + LUT 8.9 MiB 가 들어가 **단편화 시 대형 연속 블록 실패가 드물지 않다** ─ **등급 높음 [확정]**(코드) / 실패 빈도 [추정] | 할당·크기변경 함수는 **성공했을 때만 상태를 바꾼다**. "실패했는데 필드 일부만 갱신된 객체" 를 만들지 않는다 |
| C15 | **`LOCK` 결과를 버리고 `FETCH`** | `TArchonGUI::fetchFrame()` 은 `LOCK` 의 `getResult()` 를 **받아놓고 쓰지 않은 채** `FETCH` 를 낸다(`archongui.cpp:1830~1841`). `Archon::lockFrame()` 은 인자 오류·5초 타임아웃·`?` 셋 다 1 을 반환한다(`archon.cpp:642~656`). LOCK 이 실패하면 `Archon::fetchFrame()` 이 `FRAME` 을 다시 물어 **직전에 잠겨 있던(또는 아무것도 안 잠긴) 버퍼를 읽는다.** 오류 표시는 로그 한 줄뿐이고 이미지는 정상처럼 뜨며 `cbSaveAll` 이면 디스크에도 간다 | **도달**: 인자는 항상 유효하므로 실효 경로는 **LOCK 타임아웃 또는 `?`**. 결과 그림은 다른 세션이 실측한 **"LOCK 없이 fetch 하면 약 26% 로 두 노출이 섞인다"** 그 상태다 ─ **등급 높음 [확정]**(코드). ⚠️ **26% 실측은 Rev H 유닛 것**이며 Rev F(1252)는 미실측 [추정] | `LOCK`+`FETCH` 를 **한 트랜잭션**으로 묶는다. LOCK 실패 시 FETCH 금지·프레임 폐기, 폐기 사실은 로그가 아니라 **취득 결과 객체**로 상위에 올린다. "결과를 받아놓고 안 쓰는" 자리는 전수 점검 |
| C16 | **파일의 `[SYSTEM]` 이 하드웨어 정보를 덮어쓴다** | `openFile()` 이 ACF 의 `[SYSTEM]` 으로 `system` 맵을 갈아치우고 `parseSystem()` 을 부른다(`archongui.cpp:1290~1296`). `parseSystem()` 은 백플레인 형·REV·펌웨어 빌드를 **다시 판정**하고 모듈 객체를 전부 `delete` 후 파일의 `MODn_TYPE` 으로 재생성한다(`:2120~2151`). 그런데 `SYSTEM` 명령은 **접속 순간 딱 한 번**만 나가고(`:2652`) `poll()` 은 `STATUS`/`FRAME` 만 낸다 → **한 번 덮어쓰면 세션 끝까지 복구되지 않는다.** 파일 값과 실제 값을 **비교하는 코드가 한 줄도 없다** | **도달**: 접속 확인조차 없어 파일을 열기만 하면 성립. KMTNet 은 Rev H 5대·Rev F 2대에 ACF 13종을 한 폴더에 두므로, 101(Rev H·1261) 에 붙은 채 113 용 ACF(Rev F·1252) 를 여는 것으로 충분하다 ─ **등급 높음 [확정]** | **실장비 `SYSTEM` 을 권위로** 삼는다. 파일의 `[SYSTEM]` 과 다르면 차이를 나열하고, `MODn_TYPE`·`BACKPLANE_REV`·`BACKPLANE_VERSION` 불일치는 **경고가 아니라 거부** |
| C17 | **`QSettings::status()` 미확인** | `openFile()`(`:1290`)·`saveFile()`(`:1321`) 둘 다 상태를 보지 않는다. **저장**: `QSettings` 는 파괴자에서 조용히 쓰므로 권한·디스크 문제로 실패해도 사용자는 저장된 줄 안다. **읽기**: 파싱 실패면 `allKeys()` 가 비고, `config.clear()` 뒤 아무것도 안 들어간 채 `updateUI()` 가 **모든 위젯을 기본값으로** 채운다 → 그대로 Apply All 하면 **기본값이 실장비에 적용된다(바이어스 전압 포함)** | **도달**: 저장은 읽기 전용 경로·네트워크 마운트 끊김, 읽기는 `.acf` 아닌 파일 선택이나 깨진 ACF. 대화상자 필터는 사용자가 바꿀 수 있다 ─ **등급 높음 [확정]** | 설정 입출력은 **왕복 검증까지가 한 동작**이다. 쓰고 되읽어 키 수·값을 대조하고, 읽을 때 **키 수 0 또는 필수 키 부재는 오류**로 친다. "빈 설정을 성공적으로 로드했다" 는 결과를 만들지 않는다 |
| C32 | ⭐ **`openHDRFrame()` 오류 경로가 `frameMutex` 를 잠근 채 반환** | `:3804` 에서 `frameMutex.lock()` 한 뒤 읽기 실패 시 `:3820` 에서 **`unlock()` 없이 `return`** 한다. 같은 함수의 나머지 세 형제(`:3678`·`:3743`·`:4365`)는 전부 오류 경로에서 푼다 — 이 한 곳만 빠졌다. 이후 워커의 `Archon::fetchFrame()`(`archon.cpp:1297`) 과 GUI 의 통계 경로(`archongui.cpp:3145`) 가 **영구 교착**된다 | **도달**: HDR raw 파일 열기 중 읽기 실패(파일 잘림·매체 오류) 한 번. 폭 입력 대화상자가 `size % w` 만 보므로 잘린 파일도 여기까지 온다 ─ **등급 높음 [확정]**. ※ bug.md 미수록, 이번 재검증에서 새로 찾았다 | 락 획득·해제를 **문맥 관리자(`with`)로만** 한다. 우리 `_lock` 아래 왕복은 `_locked_thread()` 로만 이라는 기존 규칙이 정확히 이 결함을 막는 규칙이다 |
| C18 | **워터마크를 발행 전에 올린다** | `poll()` 의 자동 페치가 `fetchedframe = newestframe;` 을 **먼저** 하고 `fetchFrame()` 을 뒤에 부른다(`archongui.cpp:2407~2411`). LOCK/FETCH 가 실패해도 워터마크는 이미 올라가 있어 다음 폴에서 조건이 안 걸리고 **그 프레임은 재시도 없이 영구 유실**된다. C15 와 겹치면 유실이 아니라 **오염된 프레임이 정상으로 기록**된다 | **도달**: 자동 페치가 켜진 상태에서 LOCK/FETCH 가 한 번 실패하면 즉시 ─ **등급 중 [확정]** | "처리 완료" 표시는 **성공 확인 뒤**에 올린다. 취득 루프의 `last_fetched` 류 갱신은 **성공 분기 안에만** 둔다 |
| C19 | **통계·PTC 기본 관심영역이 1픽셀** | 생성자에서 `statX1..statY2` 가 전부 0 이다(`imagewidget.cpp:15~18`). `fitGainOffset()` 만 "두 점이 같으면 전면" 특례를 가지고(`archongui.cpp:3042~3047`), `updateStats()`(`:3243~3246`)·`updateDiffStats()`(`:3351~`)·`updatePlots()`(`:3474~`)·raw 계열(`:3918~`)에는 **그 특례가 없다** → Signal·Noise·DR·DiffVar 와 **PTC 누적 전체가 픽셀 한 개**로 계산된다 | **도달**: 프로그램 기동 직후 사용자가 이미지 위에 상자를 그리기 전까지 **항상**. 화면에는 숫자가 멀쩡히 나와 알아챌 단서가 없다 ─ **등급 중 [확정]** | "영역 미지정" 의 기본 의미를 **한 곳에서** 정하고 모든 소비자가 그것을 쓴다. **통계 결과에는 항상 표본 수를 함께 실어** 1픽셀 평균이 조용히 통과하지 못하게 한다 |
| C21 | **파괴적 명령 도중 종료 시 최대 200초 정지** | `Archon::~Archon()` 은 `Abort=true` 후 `wait()` 만 한다(`archon.cpp:41~47`). 워커는 `Abort` 를 **`forever` 머리와 청크 경계에서만** 보는데 `interfaceCommand` 한 번의 타임아웃이 `ERASEMOD` 는 **200 000 ms**(`:1119`), `FLASHACTIVECONFIG`/`ERASESTOREDCONFIG` 는 60 000 ms(`:1024`·`:1032`), `POWERON`/`POWEROFF`/`APPLYALL` 은 30 000 ms 다 | **도달**: 모듈 PROM 소거 중 창을 닫으면 창은 사라지고 프로세스가 남아 OS 가 "응답 없음" 을 띄운다. 사용자가 강제 종료하면 **PROM 이 반쯤 지워진 채 남는다** ─ **등급 중 [확정]**(타임아웃 상수는 GUI 소스, FW 무관) | 취소 신호는 **블로킹 대기의 안쪽까지** 들어가야 한다. 긴 대기는 취소 가능한 조각으로 쪼개고, **취소 불가 구간(PROM 소거)은 애초에 취소를 거부**하고 이유를 알린다. 컨트롤러 취소안전(`df4d4fc`) 이 겨눈 지점이 이것이다 |
| C22 | **저장 파일명이 프레임번호뿐 → 재부팅 후 조용한 덮어쓰기** | `_%1x%2_%3.raw`(`archongui.cpp:3842`) / `.fits`(`:4170`) 의 셋째 항이 `displayframe`(= 컨트롤러 `BUFnFRAME`) 이다. 존재 확인도 덮어쓰기 확인도 없고 `cbSaveAll` 이면 프레임마다 자동으로 쓴다. §11.3 C9(`ptc.txt` 고정 이름)와 달리 **이름이 가변인데도 충돌한다** | **도달**: `REBOOT` 뒤 같은 base filename 으로 취득을 재개하면 이전 `_4700x1000_1.fits …` 가 차례로 덮어써진다. ⚠️ **"`BUFnFRAME` 리셋은 `REBOOT` 뿐" 은 다른 세션의 Rev H 실측**이며 Rev F(1252)에서 같은지는 확인하지 못했다 ─ **등급 중, Rev H [실측] / Rev F [추정]** | 산출물 이름은 **단조 증가가 보장되는 값**(UTC 타임스탬프 + 관측 일련번호)으로 짓는다. **리셋되는 컨트롤러 카운터를 단독 키로 쓰지 않는다.** 덮어쓰기는 기본 금지 |
| C23 | **`command()` 34 호출 중 32개가 반환값 무시** | `archon->command(` 는 34곳, 반환값을 보는 곳은 `poll()` 두 곳뿐이다(`:2840`·`:2844`). `getResult()` 는 55곳에서 불리는데 값을 쓰는 곳은 9곳이다. 무시되는 쪽에 `LOCK`·`FETCH`·`FLASH`·`POWERON`·`POWEROFF`·`REBOOT`·`APPLYALL`·`CONNECT` 가 전부 있다 | **도달**: 지금은 대부분 무해한데, 그 이유가 **`getResult()` 의 `msleep(50)` 스핀이 GUI 스레드를 통째로 막아**(`archon.cpp:229~245`) 명령이 끼어들 수 없기 때문이다 — **벤더의 안전성은 "GUI 를 얼려서" 얻은 것**이다 ─ **등급 중 [확정]** | ⭐ **우리 ICS 는 GUI 를 얼릴 수 없으므로 벤더가 우연히 얻은 직렬화가 없다.** 명령 발행 API 는 "거절됨" 을 반환값이 아니라 **예외 또는 결과 객체**로 돌려 **무시가 문법적으로 불가능**하게 만든다 |
| C26 | **조용한 `qBound` 클램프는 `RAWSEL` 만이 아니다** (C1 확대) | 같은 형태가 최소 30곳이다 — `archongui.cpp:2555`(`SAMPLEMODE`)·`:2558`(`FRAMEMODE`)·`:2568`(`RAWSEL`), `modules.cpp` 27곳(`PREAMPGAIN`·`DIO_SOURCE*`·`DIO_DIR*`·`DIO_POWER`·`HEATER?SENSOR`·`SENSOR?TYPE`·`SENSOR?FILTER`·`TECENABLE`·`IONENABLE`·`LED*`). 전부 **`&ok` 없는 `toInt()`** 위에 얹혀 있어 ① 비었거나 숫자가 아니면 **0**, ② 상한 초과면 **최댓값으로 깎임** 두 변조가 겹치고, `parseUI()` 가 위젯 인덱스를 그대로 써내므로 **깎인 값이 ACF 에 확정 기록**된다 | **도달**: ACF 를 GUI 로 열었다 저장하면 성립. 실기 ACF 13종에 상한 초과 값은 **없다**(전수 확인) — 지금 손상은 `RAWSEL` 개조분에 국한되나 **펌웨어가 항목을 늘리면 GUI 의 상한이 먼저 낡는다** ─ **등급 중 [확정]** | 파서는 **깎지 말고 원값을 보존**하고 범위 위반은 **별도 경고 목록**으로 낸다(C1 방침 확장). **`toInt()` 실패와 "값이 0" 을 절대 같은 결과로 만들지 않는다** |
| C27 | **`VCPU_LINES` 부재 시 위젯이 초기화되지 않는다 + 반복 상한 없음** | `count = config.value(key+"/VCPU_LINES").toInt(&ok); if (ok) { teVCPU->clear(); … }`(`modules.cpp:3605~3612` 외 4개 클래스 동형). 키가 없으면 `ok=false` 라 **`clear()` 조차 실행되지 않아** 직전 내용이 남고 `parseUI()` 가 그것을 이 모듈 코드로 써낸다. 또한 **`count` 에 상한이 없다** — `VCPU_LINES=2000000000` 이면 `appendPlainText` 를 20억 번 돈다 | **도달**: `openFile()` 은 `parseSystem()` 이 모듈 객체를 재생성하므로 막히고, `openNiceFile()` 계열과 모듈 재생성이 없는 경로에서만 열린다 ─ **등급 하 [유력]**. 반복 상한 부재는 별개로 **[확정]** | "키 없음" 과 "키가 0" 을 구분하되 **어느 쪽이든 상태를 초기화**한다. 파일에서 온 **반복 횟수·배열 길이에는 항상 상한**을 건다 |
| C30 | **펌웨어 빌드 파싱 실패가 키를 지운다** | `build = system.value("BACKPLANE_VERSION").section('.',2).toInt();`(`archongui.cpp:1936~1938`) — `&ok` 가 없다. 값이 없거나 절이 셋이 안 되면 `build=0` 이 되어 `<930`·`<1028`·`<1042`·`<1179` **게이트가 전부 걸리고**, `parseUI()` 는 `if (!widget->isHidden())` 로 감싸 저장하므로(`:2427~2441`) `ADXRAW`·`ADXCDS`·`PCLKDELAY`·`LINESCAN`·`APPLYALL`·`POWERON`·`TRIGINEDGE` 가 **저장 ACF 에서 통째로 사라진다** — C3 유실이 여기서 한 번 더 발동한다 | **도달**: 실기 ACF 13종은 전부 `1.0.12xx` 라 현재는 안 걸린다(전수 확인). 손으로 편집한 ACF, 판번호 형식 변경 시 열린다 ─ **등급 하 [확정]**(코드) / 현행 자료 기준 **미도달** | 버전 문자열 파싱은 **실패를 실패로 반환**하고, 실패 시 게이팅을 적용하지 말고 **작업을 중단**한다. "모르면 가장 보수적으로" 가 여기서는 **키를 지우는** 동작이라 안전하지 않다 |

**보조 갱신 — 기존 M1 의 등급 승급 [확정]**

1차 보고서는 M1(`VCPU_INREG` off-by-one, 쓰기 0기점 / 읽기 1기점)을 「중(잠복)」 으로 두었으나 **잠복이 아니다.**
버그가 있는 5개 클래스는 `LVBIAS`(`modules.cpp:1640` vs `:1681`) · `HEATER`(`:2624`/`:2691`) · `HS`(`:3583`/`:3615`) · `LVDS`(`:3998`/`:4026`) · `HEATERX`(`:4737`/`:4812`) 인데,
KMTNet science 구성은 `MOD1_TYPE=10`(**LVDS**) · `MOD4_TYPE=9`(**LVXBIAS → LVBIAS 클래스**) 로 **둘 다 버그 클래스**이고, 해당 ACF 에 `MOD1\VCPU_INREG0`~`15` 와 `MOD4\VCPU_INREG0`~`15` 가 **각각 16개씩 실재한다.**
→ 그 ACF 를 벤더 GUI 로 열었다 저장하면 `INREG0` 이 버려지고 `INREG1..15` 가 한 칸씩 내려앉으며 `INREG15` 자리가 `"0"` 으로 채워진다. 현재 값이 전부 0 이라 안 보일 뿐이다.
**등급: 「중(잠복)」 → 「중(실기 도달 확정)」.** 운영 규칙으로 **`VCPU_INREG` 를 가진 ACF 는 벤더 GUI 왕복 금지**를 못 박는다.

**선별에서 뺀 것 (한 줄 이유)**

| # | 뺀 이유 |
|---|---|
| C20 | `.mcs` 타입 04 확장주소가 `int` 로 음수화 → 상한 검사 우회. 코드 결함은 [확정] 이나 **`ics_archon` 은 플래시 굽기 기능을 갖지 않는다** — 기존 C7(체크섬 미검증)에 조건부로 흡수한다 |
| C24 | `TFrameBuffer` 복사·대입이 `Data==0` 을 안 본다. 도달에 `malloc` 실패 **와** `QVector` 원소 값복사가 동시에 필요한데 `frames.resize(2)` 가 한 번뿐이라 **현재 도달 경로가 없다**. 교훈은 C14 와 같다 |
| C25 | `saveFITS()` `goto error` 가 `linebuf`/`dlinebuf` 를 안 푼다. **C++ 수동 자원관리 고유 문제**로, 파이썬 `with`/`try-finally` 를 쓰는 우리 설계에 시사점이 없다 |
| C28 | `stateChanged()` 의 `toInt(&ok,16)` 플래그 무시. 실기 ACF 13종은 전 state 에 `CONTROL` 이 있어(science 29/29, guide 32/32) **도달하지 않고**, 교훈은 C26·C30 과 동일하다 |
| C29 | `SimpleProgress` 가 `pe->rect()` 로 막대 폭 계산. **순수 표시 결함**이라 프로토콜·설정·자료 무결성 어디에도 걸리지 않는다 |
| C31 | 워커 소켓 1회 누수 + 유휴 100 Hz 스핀. 종료 시 1회라 실해가 없고, 유휴 폴링은 우리 통신 계층이 이미 다른 구조다 |

---

---

# 12. 다른 세션 결과와의 관계

⚠️ **`ics-archon-v1.0-build` 세션이 같은 GUI 소스를 이미 읽었다.** 아래 왼쪽 칸은 **그쪽 공로**다. 출처: `ics_archon/DevNote.md` 8.2갱신 · 8.10 · 8.11 · 10장, `ics_archon/archon_lock_fetch_report.md`.

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
| N8 | ⭐ **`AUTOFETCH` 계열 송출 형식 `<QF…` 를 찾았다** (1271 신설, 1252 에 없음). 그리고 **채택하지 않는다는 판단**을 근거 4가지와 함께 정리했다(§10.1.2·§10.1.3). `LOCKT` 제거가 우리에게 무영향임도 확정했다 | 그쪽 미결(STA 문의)을 **구체적 질문으로 바꿔 준다** | §10.1.2 |
| N1 | ⭐ **`LOCKT`·`AUTOFETCH` 는 벤더 GUI 소스에도 0건.** STA 자기 클라이언트도 쓰지 않는다. GUI 의 "Auto Fetch" 체크박스는 와이어 명령 `AUTOFETCH` 와 **무관** | 그쪽 미결(STA 문의)에 **결정적 보강** | `grep -rn "LOCKT\|AUTOFETCH" src/*.cpp src/*.h` → 0건 |
| N7 | ⭐ **FW 1252 ↔ 1271 명령표 대조** — 1271 에서 **`LOCKT` 제거 · `FASTAUTOFETCH` 신설**. `LOCKNEWEST` 는 양쪽 0건이라 **"FW 명령이 아니다" 가 재확인**됐다. 그리고 `FETCH` 가 1271 에서 독립 문자열로 안 잡히는 것이 **"문자열 부재 ≠ 명령 삭제" 의 반례** | 그쪽 미결 V7("1261 에도 있나")에 **부분 답** + 문의 항목 하나 추가 | §10.1.1 |
| N2 | ⭐⭐ **raw 는 이미지 fetch 크기에 안 섞여. `data_bytes` 는 옳고, raw 는 별도 2차 fetch** | **결함 의심 해소** | `archon.cpp:1282~1289`, `:1361~1364` |
| N3 | ⭐⭐ **raw 채널 개조의 진상 전모** — 매뉴얼 정의, `currentIndex()` 증거, 36 밀림 산식, 왕복 파손, 실사용 흔적 없음, 남은 유보 (A)/(B) | **완전히 새 층** | §2.2 전체 |
| N4 | ⭐ **모듈 형 번호 정본 0~19.** `parse.py::MODULE_TYPES` 의 **6 누락**과 **16 미상**을 둘 다 닫음 | **우리 코드 직접 수정거리** | `archon.h:29~48` |
| N5 | **REV 숫자 ↔ Rev 문자 대응 규칙**(`'A'+n`)과 플래시 파일명 검증 규칙. → `archonbackplanerevf_1_0_1252.mcs` 는 **113 전용**, 101(Rev H)용 이미지는 **없음**. ADM `.mcs` 도 없음 | **자산 재고 판정** | `archon.cpp:761~787`, `:1055~1100` |
| N6 | **`.mcs` 3종의 Intel HEX 레코드 수 대조** — driver 와 hvxbias 가 데이터 29,013 · EOF 1 · 확장주소 8 로 **완전히 같다** → "같은 부품·같은 도구" 를 [추정]에서 [유력]로 승급. 백플레인은 444,952 레코드 = **7,119,232 B** 로 DevNote 8.11 의 7.1 MB 와 일치 | 등급 승급 + 교차검증 | 직접 계산 |
| N7 | **개조 환경 특정** — `archongui.pro.user` 가 **QtCreator 3.2.1 / 2025-08-27T04:54:11 / Qt 5.3 MinGW 32bit / `C:/Users/kmtnet/Downloads/archongui (2)/`** 를 기록. 스페이스 들여쓰기 흔적과 앞뒤가 맞는다 | **새 사실** | `.pro.user` 원문 |
| N8 | **SSO 빌드 환경 특정** — Qt 5.15.13 / g++ 13.3 / `-O2 -Wall -Wextra` / `DISTDIR=/home/rtkmtnet/SMC/archongui_v1.0.1259.KMTNet_20250827/` → SSO 사본이 20250827 트리의 빌드본임을 증명 | **새 사실** | `Makefile.Release`, `.qmake.stash` |
| N9 | **폴링 주기 정정** — 그쪽은 "5Hz 타이머" 라고 썼는데, **주석이 5Hz 일 뿐 실제는 500 ms = 2 Hz 틱**이고 교대라 **STATUS·FRAME 각각 1 Hz** 이다 | **정정** | `archongui.cpp:1224~1227`, `updatetimer.cpp:34~41` |
| N10 | **모듈 체계 전층** — 클래스 15개 ↔ 형 18종 대응, 공유 클래스 3개, **ADM 이 빈 껍데기**, 설정 키 인덱스 규약, **펌웨어 빌드 게이팅이 키 집합을 바꾼다**, KMTNet science/guide 슬롯 대조 | **새 층** | §7 전체 |
| N11 | **설정 적용 계통** — `writeConfig` 의 6단 순서, **부분 적용이 없다**, 함수 사이 순서 의존성 6가지, 세 가지 키 표기(`/` `\` `_`)의 메커니즘 | **새 층** | §5 전체 |
| N12 | **영상·해석** — 통계 산식(모집단 N 나눗셈), `diffvar` 의 **2N 나눗셈**, **PTC 게인이 코드에 없다**, FITS 헤더 7개뿐, 플롯 txt 가 `%0.0lf` | **새 층** | §8 전체 |
| N13 | **전원·감시** — p.41 레일 범위표, **"7개냐 8개냐" 층위 정리**, `POWER` vs `POWERGOOD` 구분, **`PWR_STANDBY` early return 버그**, **GUI 가 `VALID` 를 게이트로 안 쓴다** | **새 층** | §9 전체 |
| N14 | **매뉴얼 어긋남 13건 + 11건 표** (§4.6, §10.6) — "매뉴얼 비권위" 원칙의 구체 증거 목록 | **새 층** | §4.6 |
| N15 | **결함 목록 40여 건** — C1~C6(설정), F1~F6(프레임), I1~I10(영상), M1~M9(모듈), D-계열(프로토콜). 특히 **`openHDRFrame` 뮤텍스 미해제 교착**과 **`VCPU_INREG` off-by-one** | **새 층** | 각 절 결함표 |

---

# 13. 미해결 · 다음에 볼 것

## 13.0 ⭐ 펌웨어 디스어셈블로 닫힌 것 (2026-09-03)

2차 검토에서 `archonbackplanerevh_1_0_1271.mcs` 를 **AArch64 코드로 디스어셈블**해, 지금까지
"매뉴얼에 없다 / GUI 소스에 없다" 로 미결이던 항목 여럿을 **코드 원문**으로 닫았다.

### A.0 이 절의 근거가 어디까지 미치는가 — 먼저 읽을 것

| 이미지 | 실기 대응 | 해석 수준 | 이 절의 근거력 |
|---|---|---|---|
| `archonbackplanerevh_1_0_1271` | Rev H 5대(KMTC_SCI_101 · KMTC_SCI_102 · KMTS_SCI_101 · KMTS_SCI_102 · KMTS_GUI_161)가 돌리는 **1261 의 판올림판** | **명령어 단위 디스어셈블 성공**(Zynq UltraScale+ / Cortex-A53) | **코드 원문** |
| `archonbackplanerevf_1_0_1252` | Rev F 2대(**KMTK_SCI_113 · KMTK_GUI_162**)의 **현행 이미지** | **디스어셈블 실패**(MicroBlaze 소프트코어, capstone 백엔드 없음) | **문자열 대조만** |

따라서 아래 모든 수치·분기 근거는 **1271 기준**이다. **Rev F 유닛에는 그대로 옮기면 안 된다.**
Rev F 에 대해서는 §A.3 의 강등표를 함께 읽어야 한다. 다만 두 판의 **파서 문자열 테이블이 완전히
대응하므로**(설정 키 집합 동일, STATUS 필드 동일) 상한 로직까지 달라졌을 개연성은 낮다.

### A.1 ⭐ 종결표

| # | 항목 | 종결 내용 | 근거 | 등급 (Rev H / Rev F) |
|---|---|---|---|---|
| **U2** | FW 가 `RAWSEL ≥ 16` 을 받는가 | **받는다.** 파서 상한이 `cmp #71` 이다(0기점 0~71, 뺄셈 보정 없음). → **GUI 의 `qBound(0,…,15)` 는 FW 제약이 아니라 GUI 결함**이 확정 | FW 1271 `0x59b7b4` · `archongui.cpp:2568` | **[확정]** / [추정] |
| **U3** | ADM 슬롯당 채널 수가 18인가 | **18이 맞다.** `>P%05X` 채널 파워다운 마스크 생성 루프가 비트 0–3(4개)+비트 4–17(14개)=**18비트**를 만든다 | FW 1271 `0x5b5e44`~`0x5b5e78` | **[확정]** / **[유력]**(실기 ACF 교차, §A.4) |
| **U4** | `VCPU_INREG` 가 0기점인가 1기점인가 | **0기점 0~15.** `cmp #15; b.hi` 로 끝이고 **뺄셈 보정이 없다.** 대조군 `MOD<n>` 은 `sub #1` 뒤 `cmp #11` 로 **1기점 1~12** → 두 기점이 코드에서 대비되어 판정이 확정 | FW 1271 `0x58c074`(INREG) · `0x58bf98`(MOD) | **[확정]** / [추정] |
| **U5** | `VALID=0` 일 때 나머지 STATUS 필드 | **필드 구성은 그대로다.** STATUS 조립부에 **`VALID` 값에 대한 분기가 없고**, `VALID=%d ` → `COUNT=%u ` → 나머지 전부를 조건 없이 잇는다. 값은 마지막 폴링 스냅샷(또는 초기값 0) | FW 1271 `0x5b8e50`~`0x5b8ed8` | **[확정]** / [추정] |
| **U6** | `POLLON/OFF` 와 `BIASPOLLON/OFF` 의 차이 | **서로 다른 두 개의 독립 전역 플래그**이고(A=`0x5f369c`, B=`0x5f3df0`), 네 핸들러 모두 **대입 한 줄이 전부**이며 다른 부수효과가 없다. **한쪽이 다른 쪽을 포함하지 않는다** | FW 1271 `0x5badbc`~`0x5badf0` | 구조 **[확정]** / [추정]<br>**의미는 [실측대상] — 항목 존치** |
| **U9** | ADM 에 clamp/gain 설정 수단이 있는가 | **없다. 문자열이 없는 게 아니라 코드에 경로 자체가 없다.** 모듈 설정 디스패치에 **타입 17 케이스가 없어**(비교조차 없이 무시 경로로 낙하) `MOD5/CLAMP1=…` 같은 줄은 **오류도 없이 버려진다.** 참고로 `CLAMP<n>` 은 1~4, `PREAMPGAIN` 은 0~1 이며 둘 다 **AD 네임스페이스 전용**이다 | FW 1271 디스패치 전수(§A.2.6) · `0x58c9b8`(CLAMP) · `0x58ef54`(PREAMPGAIN) · `0x5b4af8`(타입 17=ADM) | **[확정]** / **[유력]** |
| **V2** | ADF(13)·ADX(14)·ADLN(15) 의 채널 수 | **부분 진전.** 탭 접두 `AD<n>` 상한이 **16**(=4채널×4슬롯)이므로 **AD/ADF/ADX/ADLN 은 슬롯당 4채널로 다뤄진다.** 다만 채널 파워다운 명령이 `>P%X`(4) · `>P%02X`(8) · `>P%05X`(18) **세 종류**여서 **8채널짜리 AD 계열이 따로 존재**한다 | FW 1271 `0x58b15c`(AD 상한 16) · 명령 문자열 3종 | 4채널 취급 **[확정]** / **[실측]**(guide ACF, §A.4)<br>8채널 계열 존재 **[유력]**<br>**어느 타입인지 [확인불가] — 항목 존치** |
| **V3** | X16 백플레인의 슬롯 수·ADC 슬롯 위치 | **부분 진전.** 탭 파서의 상한(`AD`≤16 · `AM`≤72)과 탭→슬롯 보정(**두 경로 모두 `+4`**)이 **상수로 박혀 있고 백플레인 타입 분기를 찾지 못했다.** → X16 에서도 비디오 슬롯은 **0기점 4~7(1기점 5~8) 4칸**일 것 | FW 1271 `0x58aefc` · `0x58b15c` · 탭→슬롯 조회 두 경로 | **[추정]**<br>(분기 부재는 전수 확인이 아니다)<br>**X16 자체는 여전히 [확인불가] — 항목 존치** |
| **V4** | guide 의 `BACKPLANE_REV`/`VERSION` | **이미 닫힘(✅ 2026-09-03).** 이번에 **보강만** 되었다 — `ADXCDS`/`ADXRAW` 는 **1252·1271 두 판의 파서 키 테이블에 모두 있다**. "guide ACF 에 그 키가 없다"는 옛 전제가 틀렸다는 정정이 펌웨어 쪽에서도 확인된다 | FW 1252/1271 키 집합 대조 | **[확정]** (변동 없음) |
| U1 | `RAWSEL` 이 전역 AM 번호인가 장착 순번인가 | **닫히지 않았다. 다만 실측 설계가 확정됐다.** U2 가 닫혀 전제가 사라졌고, 코드상 **`RAWSEL` 값에는 AM 경로의 /18 재배치가 적용되지 않는다**(파싱값을 그대로 저장). 즉 `RAWSEL` 은 **내부 인덱스 0–71** 이지 `AM번호−1` 이 아니다 → ADM 슬롯 1 의 5번째 채널은 탭 표기 `AM5`, `RAWSEL` 값 **16** | FW 1271 `0x59b7b4` + `str w0,[x20,#0x138]` · §A.2.3 변환식 | 코드 사실 **[확정]**<br>**실기 대응은 [실측대상] — 항목 존치(최상)** |

### A.2 항목별 근거 원문

#### A.2.1 U2 — `RAWSEL` 상한은 71 이다

```
; FW 1271, 0x59b7b4
cmp  w0, #0x47          ; 71
b.hi -> "RAW select out of range"
```

뺄셈 보정이 없으므로 **0기점 0~71** 이다. 매뉴얼이 규정한 상한 15 는 **AD 4채널 시절의 값**이고,
현행 FW 는 ADM 4슬롯×18채널 = 72채널을 전제로 상한이 잡혀 있다.

그러므로 다음이 확정된다.

- `archongui.cpp:2568` 의 `rawsel->setCurrentIndex(qBound(0, config.value("RAWSEL").toInt(), 15));`
  는 **FW 제약을 반영한 방어가 아니라, GUI 가 16 이상을 조용히 깎아 버리는 결함**이다.
  ACF→GUI→ACF 왕복만으로 `RAWSEL` 이 파손된다.
- 우리 파서는 **원값을 보존**해야 한다(§11.3 C1 유지, 다만 근거가 [유력]→[확정]으로 승급).
- 실기 ACF 13종은 전부 `RAWSEL=3` 또는 `4` 라 **왕복 파손이 아직 드러나지 않았을 뿐**이다 [확정].

#### A.2.2 U3 — ADM 은 18채널이다

```
; FW 1271, 0x5b5e44~0x5b5e78  (">P%05X" 마스크 생성)
cmp x0, #4              ; 앞 4채널 → 비트 0..3
...
mov x1, #0
ldr w3,[x28, x1, lsl #2]
add w0, w1, #4          ; 비트 위치 4..17
lsl w0, w4, w0
orr w0, w2, w0
cmp x1, #0xe            ; 14회
b.ne <loop>
```

4 + 14 = **18비트**. `%05X`(5자리 hex = 20비트)는 18비트를 담기 위한 폭이다.
매뉴얼 p.70 의 "ADM 18채널" 이 코드로 확인됐고, §7.3 이 지적한 "GUI 에 ADM 채널 상수가 아예 없다"
는 **GUI 쪽 결손일 뿐 펌웨어는 정확히 18을 안다**는 뜻이 된다.

#### A.2.3 AM 번호 ↔ 내부 채널 인덱스 (U1·U3 공통 기반) [확정]

`n = AM번호 − 1`(0…71), `q = n / 18`, `r = n % 18` 일 때

- `r ≤ 3` → 내부 인덱스 `= r + 4q` (0…15)
- `r > 3` → 내부 인덱스 `= r + 14q + 12` (16…71)

| 슬롯 `q` | 1기점 슬롯 | AM 번호 | 내부 인덱스 |
|---:|---:|---|---|
| 0 | 5 | AM1–AM4 / AM5–AM18 | 0–3 / 16–29 |
| 1 | 6 | AM19–AM22 / AM23–AM36 | 4–7 / 30–43 |
| 2 | 7 | AM37–AM40 / AM41–AM54 | 8–11 / 44–57 |
| 3 | 8 | AM55–AM58 / AM59–AM72 | 12–15 / 58–71 |

**각 ADM 슬롯의 앞 4채널이 기존 4채널 AD 모듈과 같은 인덱스 공간(0–15)을 차지한다.**
그래서 `AD1` 과 `AM1` 은 같은 물리 채널이고, ADM 의 5번째 채널부터는 `AM` 표기로만 지정된다.
탭→슬롯 조회는 두 경로 모두 `+4` 를 더한다(`슬롯 = 탭/4 + 4` / `탭/18 + 4`, 0기점)
→ **§11.2 B12 의 산식 `slot = 5 + (ch-1)/18` · `5 + (ch-1)/4` 가 코드로 확정된다.**

#### A.2.4 U4 — `VCPU_INREG` 는 0기점, `MOD<n>` 은 1기점

```
; FW 1271, 0x58c074   (VCPU_INREG)
cmp  w0, #15
b.hi -> "VCPU input register number out of range"     ; 뺄셈 보정 없음 → 0..15

; FW 1271, 0x58bf94~0x58bfa0   (MOD<n>) — 대조군
ldr  w0,[sp,#0xdc]
sub  w0, w0, #1                                        ; 1을 뺀다
cmp  w0, #0xb                                          ; 11
b.hi -> "Error parsing module number"                  ; → 1..12
```

같은 파서 안에서 **한쪽은 `sub #1` 이 있고 한쪽은 없다.** 컴파일 산물의 우연이 아니라
**두 키의 기점이 실제로 다르다**는 뜻이다.

→ §11.3 **C2 판정**: GUI 는 같은 값을 **쓸 때 0기점 · 읽을 때 1기점**으로 다루는 off-by-one 이
5개 클래스 전부에 있는데, **맞는 쪽은 0기점(쓰기)이고 읽기 경로가 틀렸다** [확정].
우리 쪽 "0기점으로 통일" 방침이 옳았음이 확인되며, C2 에 달아 둔 "컨트롤러 기대값은 [실측대상]"
단서는 **Rev H 에 한해 해제**한다.

#### A.2.5 U5 — STATUS 는 `VALID` 로 필드를 생략하지 않는다

```
; FW 1271, 0x5b8e50~0x5b8ed8
ldr  w2,[x21,#0x80]     ; VALID 값(전역 하나)
add  x1,x1,#0x308       ; "VALID=%d "
bl   sprintf
ldr  w2,[x20,#4]
add  x1,x1,#0x318       ; "COUNT=%u "
bl   sprintf
bl   #0x5bbf5c          ; 나머지 필드 전부 — 조건 분기 없음
```

**`VALID` 값을 읽어 찍기만 하고 분기하지 않는다.**
→ `VALID=0` 응답도 필드 개수·이름·순서가 동일하고, 값은 **마지막 스냅샷이 그대로** 나온다.
`VALID` 는 "이 스냅샷을 믿어도 되는가" 를 알리는 플래그일 뿐 필드를 생략하지 않는다.

**우리 `honour_valid` 설계의 근거가 이것이다** — 값이 비지 않고 **낡은 값이 그대로 오므로**,
게이트를 걸지 않으면 정지된 값을 신선한 값으로 오인한다. §11.2 B7 · §13.3 W6 의
"`VALID=1` 게이트 + `COUNT` 신선도 판정" 이 필수임이 코드로 뒷받침된다.

#### A.2.6 U9 — ADM 에는 clamp/gain 경로가 없다

모듈 설정 디스패치 전수(FW 1271):

| 모듈 타입 | 분기 대상 | 네임스페이스 |
|---:|---|---|
| 1 DRIVER | `0x58cacc` | 드라이버 |
| **2 AD** | **`0x58c96c`** | **AD (`CLAMPHIGH`/`CLAMPLOW`/`CLAMP`/`PREAMPGAIN`)** |
| 3 LVBIAS | `0x58c798` | LV Bias |
| 4 HVBIAS | `0x58c498` | HV Bias |
| 5 HEATER | `0x595fb0` | Heater |
| 6 ATLAS | `0x58c60c` | Atlas |
| 7 HS | `0x595e60` | HS |
| 8 HVXBIAS | `0x58c490` 경유 | HV Bias 공유 |
| 9 LVXBIAS | `0x58c798` | LV Bias 공유 |
| 10 LVDS | `0x58df28` | LVDS |
| 11 HEATERX | `0x58cc08` | HeaterX |
| 12 XVBIAS | `0x58d3c0` | XV Bias |
| **13/14/15 ADF/ADX/ADLN** | **`0x58cbf0` → `0x58c96c`** | **AD 공유** |
| 16 DRIVERX | `0x58d2a4` | DriverX |
| **17 ADM** | **비교 자체가 없음 → `0x58bef4`(무시)** | **없음** |
| 18 HVYBIAS | `0x58c498` | HV Bias 공유 |
| **19 (ADQ 로 추정)** | **`0x58c96c`** | **AD 공유** |

`MOD5/CLAMP1=…` · `MOD5/PREAMPGAIN=…` 를 ADM 슬롯에 써도 **오류도 안 내고 조용히 버려진다.**
채널 첨자·값 범위도 확정했다.

```
; 0x58c9b8   CLAMP 채널 첨자
ldrb w0,[x0,#0xca5] ; sub w0,w0,#0x31 ('1') ; cmp w0,#3 ; b.hi -> "Invalid clamp channel"
→ CLAMP1 ~ CLAMP4
; 0x58ef54   PREAMPGAIN
cmp w1,#1 ; b.hi   → 0 ~ 1
```

하드웨어 명령으로도 갈린다. ADM 관련 명령은 `>P%05X`(채널 파워다운) **하나뿐**이고,
클램프/게인용 `>C%08X` · `>CA%08X` · `>CB%08X` · `>G%X` 는 **AD 네임스페이스 처리부에서만** 쓰인다.

→ **§7.3 의 "ADM 의 clamp/gain 설정 수단이 있는지 자체가 [확인불가]" 는 폐기하고 "설계상 없음
[확정](Rev H)" 으로 고쳐 쓴다.** GUI 에 UI 가 없는 것도, 실기 science ACF 에 `MOD5\…`/`MOD8\…`
키가 0개인 것도 **결손이 아니라 펌웨어와 일치하는 정상**이다.

#### A.2.7 V2 — AD 계열 채널 수

- 탭 접두 `AD<n>` 상한 **16**(`0x58b15c`, `cmp #0xf; b.ls`) = 4채널 × 4슬롯
  → **AD/ADF/ADX/ADLN(그리고 타입 19)은 같은 파서·같은 탭 인덱스 공간을 쓰고, 슬롯당 4채널로
  다뤄진다** [확정]. 타입별 채널 수 상수는 분리해 내지 못했다.
- 그런데 채널 파워다운 명령이 **세 종류**다: `>P%X`(4비트) · `>P%02X`(8비트) · `>P%05X`(18비트).
  → **8채널짜리 AD 계열 모듈이 따로 존재한다** [유력]. **어느 타입인지는 이 이미지만으로 못 가른다**
  [확인불가]. 클램프 보정 데이터는 타입과 무관하게 항상 8개 값이다(`>W%04X` ×8).
- 곁가지로 **타입 19 = ADQ**(1271 신설, `Error configuring ADQ (slot %d)` · `>AF` · `>AQAA`) 가
  드러났다 [유력]. GUI 1259 의 열거값(19=`MOD_TYPE_UNKNOWN`)을 넘어선 값이므로 **GUI 1259 로는
  ADQ 를 다룰 수 없다.** 1252 에는 `ADQ` 문자열이 전혀 없다.

#### A.2.8 V3 — X16 에 대해 말할 수 있는 것

탭 파서의 상한(`AD`≤16, `AM`≤72)과 탭→슬롯 보정(`+4`)은 **즉치 상수**이고, 그 부근에서
`BACKPLANE_TYPE` 을 읽는 분기를 찾지 못했다. 그러므로 **X16 백플레인이라도 비디오 슬롯은
여전히 4칸(1기점 5~8)이고 탭 번호 공간도 그대로일 것** [추정] 이다.

⚠️ 이것은 **분기가 없다는 전수 확인이 아니라 해당 구간에서 못 찾았다는 뜻**이다.
실기 7대는 전부 `BACKPLANE_TYPE=1`(X12) 이라 실측으로 가릴 수도 없다.
**V3 는 존치하되, "X16 은 슬롯 수만 다르고 비디오 슬롯 위치는 같을 가능성이 높다" 를 덧붙인다.**

### A.3 ⚠️ Rev F(1252 / MicroBlaze) 등급 강등표

**KMTK_SCI_113 · KMTK_GUI_162 두 대에는 위 근거가 직접 미치지 않는다.**
`.mcs` 는 확보했으나 **MicroBlaze 디스어셈블러가 없어 코드로 읽지 못했다**(capstone 백엔드 부재).
1252 에서 회수한 것은 **문자열 테이블뿐**이다.

| 사실 | Rev H(1271) | Rev F(1252) | Rev F 등급의 근거와 한계 |
|---|:---:|:---:|---|
| `[CONFIG]` 키 집합이 동일하다 | [확정] | **[확정]** | 문자열 테이블 전수 대조. **코드가 아니라 문자열이지만 이 항목은 문자열이 곧 증거다** |
| STATUS 필드 이름·순서가 동일하다 | [확정] | **[확정]** | 〃 (서식 폭 `%lld`↔`%ld` 차이는 **CPU 교체의 부산물**이고 출력은 같다) |
| ADM = 타입 17, 18채널 | [확정] | **[유력]** | 코드 근거 없음. 그러나 **실기 Rev F science ACF 가 `AM55`~`AM70` 을 쓰며 정상 운영 중**(§A.4) |
| 탭→슬롯 `+4`, 비디오 슬롯 5~8 | [확정] | **[유력]** | 〃 (guide ACF 의 `AD1`~`AD8` ↔ 슬롯 5·6 이 산식과 정합) |
| AD 계열 슬롯당 4채널 | [확정] | **[실측]** | guide 실기가 8탭(2슬롯×4)으로 운용 중 |
| **`RAWSEL` 상한 71** | [확정] | **[추정]** | 코드 근거 전무. 실기 ACF 는 전부 `RAWSEL=3/4` 라 **16 이상을 넣어 본 적이 없다.** ⚠️ **113 에서 `RAWSEL≥16` 을 시도하기 전에 반드시 개별 확인** |
| **`VCPU_INREG` 0~15 (0기점)** | [확정] | **[추정]** | 오류 문자열은 양판 공통이나 **상한값과 기점은 문자열로 알 수 없다** |
| **STATUS 에 `VALID` 분기 없음** | [확정] | **[추정]** | 설계상 안전: 만약 1252 가 필드를 생략하더라도 우리 파서는 **필드 부재로 감지**하므로 `honour_valid` 는 어느 쪽이든 성립 |
| **ADM 에 clamp/gain 경로 없음** | [확정] | **[유력]** | 디스패치를 못 읽었다. 정황으로 실기 Rev F science ACF 가 `MOD5\…`/`MOD8\…` 키 **0개**로 무탈 운영 중 |
| **`POLL` / `BIASPOLL` 이 별개 플래그** | [확정] | **[추정]** | 명령 4종은 양판 공통 문자열이나 **핸들러 내용은 못 읽었다** |
| §C 의 수치 상한 전수표 | [확정] | **[추정]** | **표 전체가 1271 코드다.** Rev F 적용은 개연성 판단이지 근거가 아니다 |

> **강등의 근거이자 동시에 위안**: 두 판의 파서 **문자열 테이블이 완전히 대응**한다(키 229/219개
> 집합 일치, 차이는 링커 접미 공유·짧은 리터럴 인라인으로 설명된다). 파서 구조가 같은데 상한
> 상수만 갈아끼웠을 개연성은 낮다. 그럼에도 **"낮다" 는 [확정]이 아니다.**
> 최종 확정 경로는 둘이다 — **(a)** MicroBlaze 디스어셈블러(`mb-objdump` / Ghidra)를 붙인다,
> **(b)** 113 에 경계값을 넣고 `?xx` 거부 여부를 본다. [실측대상]

### A.4 Rev F 에서 회수한 교차근거 (실기 ACF)

Rev F 이미지를 못 읽은 대신, **1252 가 실제로 받아들여 운영 중인 ACF** 에서 근거를 회수했다.
"파서가 거부하지 않았다" 는 상한에 대한 **하한 증거**가 된다.

| 관측 | 파일 | 1271 코드가 말하는 것 | 판정 |
|---|---|---|---|
| 탭 `AM1`~`AM16` + `AM55`~`AM70`, `TAPLINES=33` | `KMTK_SCI_113_STA0200_R2608_*.acf` | `AM` 상한 72, `q=n/18` → AM55 는 **q=3 = 슬롯 8 의 첫 채널** | **18채널 배치가 Rev F 에서도 성립** [유력]. `AM<n>` 상한이 **최소 70 이상**임은 [실측] |
| 탭 `AD1`~`AD8`, `TAPLINES=9` | `KMTK_GUI_162_STA0201_R2608.acf` | `AD` 상한 16, `슬롯 = 탭/4 + 4` → AD1–4=슬롯 5, AD5–8=슬롯 6 | **guide 의 AD 2장(슬롯 5·6)·슬롯당 4채널과 정확히 일치** [실측] |
| `MOD5\…`/`MOD8\…` 키 0개 | science ACF 전부 | 타입 17 에 설정 디스패치 없음 | **U9 의 정황 보강** [유력] |
| `RAWSEL=3` 또는 `4` (13종 전부) | 전 ACF | 상한 71 | **16 이상을 넣어 본 적이 없다** → U1/U2 실측은 **여전히 필요** [실측대상] |
| `FRAMEMODE=0/2` · `PIXELCOUNT=528/1200` · `LINECOUNT=1033/4700` · `RAWSAMPLES=4096/8192` · `SAMPLEMODE=0` · `PCLKDELAY=0` | 전 ACF | §C 표의 각 범위 | **실기 값이 전부 표 범위 안이다** — 표와 운영 현실이 모순되지 않음 [확정] |

---

---

## 13.1 ⭐ 실측으로만 닫히는 것

| # | 항목 | 왜 코드로 못 닫나 | 실측 방법 | 우선순위 |
|---|---|---|---|---|
| # | 항목 | 왜 코드로 못 닫나 | 실측 방법 | 우선순위 |
|---|---|---|---|---|
| **U1** | ⭐ **`RAWSEL` 이 (가) `AM번호−1` 공간인가 (나) 내부 인덱스 공간인가** | **전제가 정리됐다(§13.0).** 대안 해석 "장착 모듈 순번(0~35)" 은 **반증됐다** — 상한이 71 이고 탭→슬롯이 `탭/18+4` 고정 분할이다. 다만 FW 가 `RAWSEL` 을 파싱값 그대로 저장하고 AM 경로의 `/18` 재배치를 **파싱 시점에** 적용하지 않는다는 사실만으로 "내부 인덱스" 로 단정할 수는 없다 — **재배치가 소비 지점에서 일어날 수 있고, 두 공간 모두 0~71 이라 상한으로는 갈리지 않는다** | ⭐ **`RAWSEL=16` 이 판별력이 가장 높다.** (나)면 슬롯 5 의 5번째 채널(`AM5`), (가)면 `AM17` 이다. 이어 `RAWSEL=54`(가) 와 `RAWSEL=12`(나) 로 슬롯 8 첫 채널을 교차 확인한다. 상세 절차는 §2.2(h) | **최상** |
| ~~**U2**~~ | ~~**FW 가 `RAWSEL ≥ 16` 을 받는가**~~ | ✅ **해소(2026-09-03)** — 파서 상한이 `cmp #71` 이다(FW 1271 `0x59b7b4`). **받는다** [확정]. → `archongui.cpp:2568` 의 `qBound(0,…,15)` 는 **FW 제약이 아니라 GUI 결함**이 확정(§11.3 C1). ⚠️ Rev F(113)에 대해서는 [추정]이므로 113 에서 시도하기 전 개별 확인 | | |
| ~~U3~~ | ~~**ADM 의 슬롯당 채널 수가 정말 18인가**~~ | ✅ **해소(2026-09-03)** — `>P%05X` 마스크 생성 루프가 4+14=**18비트**를 만든다(FW 1271 `0x5b5e44`~`0x5b5e78`) [확정]. Rev F 는 실기 ACF 의 `AM55`~`AM70` 로 [유력] | | |
| ~~U4~~ | ~~**`VCPU_INREG` 를 컨트롤러가 0기점으로 기대하는가 1기점인가**~~ | ✅ **해소(2026-09-03)** — **0기점 0~15** 이다(FW 1271 `0x58c074`, `cmp #15; b.hi`, 뺄셈 보정 없음). 대조군 `MOD<n>` 은 `sub #1` 뒤 `cmp #11` 로 1기점(`0x58bf98`) [확정]. → §11.3 **C2 의 "쓰기 0기점" 이 옳다** | | |
| ~~U5~~ | ~~**`VALID=0` 일 때 나머지 필드에 뭐가 들어오나**~~ | ✅ **해소(2026-09-03)** — STATUS 조립부에 **`VALID` 분기가 없다**(FW 1271 `0x5b8e50`~`0x5b8ed8`). 필드 구성은 동일하고 값은 **마지막 스냅샷이 그대로** 나온다 [확정]. → `VALID=1` 게이트가 **없으면 낡은 값을 신선한 값으로 오인**한다(§13.3 W6 강화) | | |
| U6 | **`POLLON`/`POLLOFF` 와 `BIASPOLLON`/`BIASPOLLOFF` 의 정확한 의미 차이** | ⭐ **절반 닫혔다(§13.0)** — **서로 다른 두 개의 독립 전역 플래그**이고 각 핸들러는 **대입 한 줄이 전부**다(FW 1271 `0x5badbc`~`0x5badf0`) [확정]. 한쪽이 다른 쪽을 포함하지 않는다. **남은 것은 "각 플래그가 무엇을 켜는가" 뿐** — 폴링 루프가 베이스 레지스터를 함수 전체에서 유지해 정적으로 못 짚었다 | 넷을 각각 보내고 ① STATUS `COUNT` 증가 여부 ② **백플레인 계열 필드**(`P2V5_V`, `FANTACH`) 갱신 여부 ③ **모듈 바이어스 V/I** 갱신 여부를 따로 본다. 플래그가 둘이므로 **2×2 조합 4가지를 다 봐야** 한다 | 중 |
| U7~U8 | (변동 없음) | | | |
| ~~U9~~ | ~~**ADM 에 clamp/gain 설정 수단이 있는가**~~ | ✅ **해소(2026-09-03)** — **없다.** 모듈 설정 디스패치에 **타입 17 케이스 자체가 없어** `MOD<n>/CLAMP*`·`PREAMPGAIN` 은 오류 없이 버려진다(FW 1271, §13.0 A.2.6) [확정]. `CLAMP<n>`=1~4 · `PREAMPGAIN`=0~1 은 **AD 네임스페이스 전용**. Rev F 는 [유력]. → **§7.3 의 [확인불가] 를 "설계상 없음" 으로 고친다** | | |
| U10 | (변동 없음) | | | |

## 13.2 자료로 못 가리는 것 (추가 자료가 필요하다)

| # | 항목 | 필요한 것 |
|---|---|---|
| V1 | **stock 콤보 상한 32 의 출처** | 소스엔 맨 리터럴, 매뉴얼엔 16. "4슬롯×8채널" 은 [추정]. **더 최신 매뉴얼이나 릴리스 노트**가 필요하다 |
| V2 | **ADF(13)·ADX(14)·ADLN(15) 의 채널 수** | ⭐ **부분 진전(§13.0 A.2.7)** — 탭 접두 `AD<n>` 상한이 16 이므로 **AD/ADF/ADX/ADLN 은 슬롯당 4채널로 다뤄진다** [확정]. 다만 채널 파워다운 명령이 `>P%X`(4) · `>P%02X`(8) · `>P%05X`(18) 세 종류여서 **8채널 AD 계열이 따로 존재한다** [유력]. **어느 타입인지는 [확인불가]** — 이 세 타입은 AD(2)·타입19 와 **같은 파서를 공유**해 코드에서 분리되지 않는다. 여전히 **하드웨어 장이 있는 최신 매뉴얼이나 STA 답변**이 필요하다. 실기 7대에는 이 세 타입이 없으므로 급하지 않다 |
| V3 | **X16 백플레인의 슬롯 수·ADC 슬롯 위치** | ⭐ **부분 진전(§13.0 A.2.8)** — 탭 상한(`AD`≤16 · `AM`≤72)과 탭→슬롯 보정(`+4`)이 **즉치 상수**이고 백플레인 타입 분기를 찾지 못했다 → **X16 이라도 비디오 슬롯은 1기점 5~8 의 4칸일 것** [추정]. ⚠️ 분기 부재를 전수 확인한 것은 아니다. 실기 7대가 전부 `BACKPLANE_TYPE=1`(X12)이라 **실측으로도 못 가린다.** 매뉴얼 전체에서 "X16" 은 p.46 한 줄뿐인 상황이 그대로다 |
| V4 | ~~**guide 시스템의 `BACKPLANE_REV`/`VERSION`**~~ | ✅ **해소(2026-09-03)** — (기존 문구 유지) · ⭐ **보강**: `ADXCDS`/`ADXRAW` 는 **FW 1252·1271 두 판의 파서 키 테이블에 모두 존재**한다. "guide ACF 에 그 키가 없다" 던 옛 전제가 틀렸다는 정정이 펌웨어 쪽에서도 확인된다 [확정] |
| V5 | ~~**101(Rev H)용 백플레인 `.mcs`**~~ | ✅ **해소(2026-09-03)** — `archonbackplanerevh_1_0_1271.mcs` 반입. ⚠️ 다만 **판번이 1271 이라 실기 1261 의 복구본이 아니라 판올림**이다(§10.4) |
| V6 | **ADM 모듈 `.mcs`** | (변동 없음) 다만 **백플레인이 ADM 에 보내는 명령 어휘는 전수 확보**했다 — `>P%05X` 하나뿐이고 clamp/gain 명령은 오지 않는다(§13.0 A.2.6). STA 문의 시 인용 가능 |
| V7 | **101 유닛이 지금 돌리는 FW 1261 이미지** | 여전히 없다. 보유는 1252·1271 둘이라 **1261 의 명령표는 직접 보지 못한다.** 다만 1252 와 1271 을 대조해 변화 방향은 잡았다(§10.1.1). 1261 은 그 사이 판이라 `LOCKT` 유무가 **[확인불가]** |
| V8 | **SSO 빌드 로그** | Qt 5.2~5.3 상정 코드를 Qt 5.15/C++17/g++13 으로 빌드한 거라 경고가 많았을 가능성. 재빌드 시 로그를 남겨 두는 것이 좋다 |
| V9 | **XVBias 양전압 상한** | 매뉴얼 내부 모순 — p.10·p.63 은 +95 V, p.33 은 +91 V. 실기 미사용이라 급하지는 않다 |

## 13.3 우리 코드에 지금 바로 반영할 것

| # | 대상 | 조치 | 근거 |
|---|---|---|---|
| W1 | `ics_archon/archon/parse.py::MODULE_TYPES` | **6 = ATLAS** 추가, **16 = DRIVERX** 확정 | `archon.h:35`, `:45` |
| W2 | 같은 곳 | 17=ADM · 18=HVYBias 는 **확인 완료** — 주석에 "GUI `archon.h` 로 교차확인(2026-09-02)" 명기 | `archon.h:46~47` |
| W3 | `parse.py:113` `data_bytes` | **변경 불필요.** 벤더와 동일함을 확인했다는 주석만 추가 | `archon.cpp:1282~1284` |
| W4 | raw 미독출 | **결함 아님.** DevNote 에 "raw 는 별도 2차 fetch 라 이미지 크기와 무관" 을 기록 | `archon.cpp:1361~1364` |
| W5 | 통신 계층 문서 | **Rev F 동시 접속 1개** · **인식 못 한 명령은 무응답(타임아웃 필수)** 두 조항 추가 | 매뉴얼 p.15, p.45 |
| W6 | STATUS 처리 | **`VALID=1` 게이트** + `COUNT` 신선도 판정 규정 추가 | 매뉴얼 p.47, p.74 |
| W7 | 알람 설계 | `POWER`/`POWERGOOD` 분리, 레일별 p.41 범위 이중확인, **미사용 레일 제외** | 매뉴얼 p.41~43 |
| W8 | 단위 처리 | 시스템 레일 **A** / 모듈 바이어스 **mA** / 백플레인·모듈 온도 **℃** / 히터 센서 **K** | 매뉴얼 p.47~48, p.60~61 |
| W9 | ACF 파서 | `\` → `/` 정규화, **모르는 키 보존**, `RAWSEL` 원값 보존(깎지 않기) | §5.1, §5.6 C3 |
| W10 | ACF 검증 규칙 | ADM 슬롯이 있으면 **SHP/SHD 가 8의 배수인지 검사** | 매뉴얼 p.69 |
| W11 | STA 문의서 | `LOCKT`/`AUTOFETCH` 에 **"벤더 클라이언트도 안 쓴다"** 를 보태고, **`<QF%d%08X%04X%04X%08X%08X` 형식 문자열을 인용**해 `FASTAUTOFETCH` 의 송출 형식을 직접 묻기 | §12.2 N1 · §10.1.2 |
| W12 | 자산 대장 | `archonbackplanerevf_1_0_1252.mcs` 는 **113 전용**이라고 명기. 101용·ADM용 이미지 부재를 기록 | §10.4 |

---
| # | 대상 | 조치 | 근거 |
|---|---|---|---|
| W13 | ACF 검증 도구 | **§13.4 상한표를 규칙으로 이식**한다. 특히 `RAWSEL` 0~71 · `VCPU_INREG` 0~15 · `PIXELCOUNT`/`LINECOUNT` **하한 1** · `FRAMEMODE` 0~3 · `TECENABLE`/`IONENABLE` **0~2** | §13.4 |
| W14 | 같은 곳 | **"조용히 버려지는 키" 경고**를 추가한다 — ADM(타입 17) 슬롯의 `CLAMP*`/`PREAMPGAIN`, 모듈 타입과 어긋나는 `MOD<n>/…` 키. FW 는 오류를 내지 않는다 | §13.0 A.2.6 |
| W15 | STATUS 처리(`honour_valid`) | **설계 근거 확정.** `VALID=0` 이어도 **필드는 그대로 오고 값만 낡았다** → 게이트가 없으면 정지값을 신선값으로 오인한다. `COUNT` 신선도 판정을 **함께** 규정 | §13.0 A.2.5 |
| W16 | 채널↔슬롯 변환 | §11.2 B12 의 산식이 **코드로 확정**됐다: `AM` → `슬롯 = (n−1)/18 + 5`, `AD` → `슬롯 = (n−1)/4 + 5`. FITS 헤더 작성에 그대로 사용 | §13.0 A.2.3 |
| W17 | 자산·운영 대장 | **Rev F(113·162)에는 1271 근거가 미치지 않는다**를 명기. 특히 **113 에서 `RAWSEL ≥ 16` 을 시도하기 전 개별 확인**. MicroBlaze 디스어셈블(`mb-objdump`/Ghidra)을 후속 과제로 등록 | §13.0 A.3 |

## 13.4 ⭐ FW 파서 수치 상한 전수표 (ACF 검증 규칙 정본)

**FW 1271 코드에서 직접 읽은 값이다** [확정 · Rev H].
⚠️ **Rev F(1252)에 대해서는 이 표 전체가 [추정]** 이다(§13.0 A.3). MicroBlaze 를 못 읽었다.

**우리 ACF 검증 도구가 그대로 쓸 수 있는 값이다.** 범위 밖 값은 FW 가 `?xx` 로 거부하므로,
검증기는 **적용 전에 걸러 낼 수 있다**. "★" 는 실기 ACF 로 교차확인된 행이다.

| 키 | 허용 범위 | FW 1271 위치 | 비고 · 검증기 조치 |
|---|---|---|---|
| ★ `MOD<n>` | **1 ~ 12** | `0x58bf98` | **1기점**(`sub #1` 후 `cmp #11`). X12 12슬롯 |
| `RAWENABLE` | 0 ~ 1 | `0x59b804` | |
| ⭐★ **`RAWSEL`** | **0 ~ 71** | `0x59b7b4` | **0기점, 보정 없음.** 값은 **내부 채널 인덱스**이지 `AM번호−1` 이 아니다(§13.0 A.2.3). **GUI 의 15 클램프는 결함** — 우리 파서는 **원값 보존** |
| `RAWSTARTLINE` | 0 ~ 65535 | `0x59b140` | |
| `RAWENDLINE` | 0 ~ 65535 | `0x59b0f8` | |
| `RAWSTARTPIXEL` | 0 ~ 65535 | `0x59af78` | |
| ★ `RAWSAMPLES` | 0 ~ 67,107,840 (`0x3FFFC00`) | `0x59af24` | 이후 **1024 올림**. 매뉴얼 p.70 "multiple of 1024" 와 정합. 실기 4096·8192 |
| ★ `SAMPLEMODE` | 0 ~ 1 | `0x59ada4` | 1=32bit(HDR) |
| ★ `PIXELCOUNT` | **1 ~ 65535** | `0x59ad60` | **0 은 거부된다**(하한이 1) |
| ★ `LINECOUNT` | **1 ~ 65535** | `0x58c30c` | **0 은 거부된다** |
| `LINESCAN` | 0 ~ 1 | `0x58c2a8` | |
| ★ **`FRAMEMODE`** | **0 ~ 3** | `0x59abdc` | 실기 0·2 사용 |
| `BIGBUF` | 0 ~ 1 | `0x59ab98` | |
| ★ `ADXRAW` / `ADXCDS` | 0 ~ 1 | `0x59b548` / `0x59b4e4` | **두 키 모두 1252·1271 공통**(§13.2 V4) |
| ★ `PCLKDELAY` | 0 ~ 255 | `0x59b990` | |
| `LINES` / `LINE<n>` | 0 ~ 2047 | `0x58c3dc` / `0x58c6f4` | |
| `STATES` / `STATE<n>` | 0 ~ 2047 | `0x58c44c` / `0x58d148` | |
| `PARAMETERS` / `PARAMETER<n>` | 0 ~ 255 | `0x59900c` / `0x59a184` | |
| `CONSTANTS` / `CONSTANT<n>` | 0 ~ 255 | `0x59a024` / `0x59bd9c` | |
| ★ `TAPLINES` / `TAPLINE<n>` | 0 ~ 255 | `0x59b330` / `0x59b2b4` | 실기 9·32·33 |
| ★ 탭 토큰 `AD<n>` | **1 ~ 16** | `0x58b15c` | 4채널 × 4슬롯. `슬롯 = (n−1)/4 + 5` |
| ★ 탭 토큰 `AM<n>` | **1 ~ 72** | `0x58aefc` | 18채널 × 4슬롯. `슬롯 = (n−1)/18 + 5` |
| ★ 탭 방향 문자 | **`L` / `R` 뿐** | `0x58af3c` | 그 외는 `Invalid tap direction` |
| ⭐ **`VCPU_INREG<n>`** | **0 ~ 15** | `0x58c074` | **0기점**(§13.0 A.2.4) |
| `VCPU_LINE<n>` / `VCPU_LINES` | 0 ~ 511 | `0x599190` / `0x5992a8` | |
| `IP` / `NETMASK` / `GATEWAY` 각 옥텟 | 0 ~ 255 | `0x58be70` 외 | |
| `TRIGOUT*` · `TRIGIN*` · `FANDISABLE` · `APPLYALL` · `POWERON` | 0 ~ 1 | — | |
| **`CLAMP<n>` 채널 첨자** | **1 ~ 4** | `0x58c9cc` | **AD 네임스페이스 전용. ADM 슬롯에 쓰면 무시된다** |
| **`PREAMPGAIN`** | **0 ~ 1** | `0x58ef54` | 〃 |
| 드라이버류 채널 첨자 | 모듈 타입별 0~3 / 0~5 / 0~7 / 0~11 / 0~23 | `0x58d4d0` 외 | 실기 Driver 8채널판 |
| `DIO_SOURCE` DIO 라인 | 0~3 또는 0~7 (모듈별) | `0x58e98c` / `0x592900` | |
| `DIO_POWER` | 0 ~ 1 | `0x58dfe4` | |
| `LVHC_IL` / `HVHC_IL` 전류제한 | 0 ~ 250 / 0 ~ 500 | `0x59979c` / `0x59c3fc` | 단위 mA |
| **`TECENABLE` / `IONENABLE`** | **0 ~ 2** | `0x595d30` / `0x595e40` | **0/1 이 아니라 3값이다** |
| `HEATER{A,B}SENSOR` | 0~1 또는 0~2 (모듈별) | — | |
| `SENSOR{A,B,C}TYPE` | 0 ~ 5 | — | |
| `SENSOR{A,B,C}FILTER` | 0 ~ 8 | — | |
| `HEATER{A,B}{ENABLE,FORCE,RAMP}` | 0 ~ 1 | — | |
| `VACENABLE` | 0 ~ 1 | `0x5968e0` | |

**검증기가 이 표를 넘어서 봐야 할 것 두 가지**

1. **범위는 통과하지만 무시되는 키** — ADM 슬롯의 `CLAMP*`/`PREAMPGAIN`, 그리고 모듈 타입과
   맞지 않는 모든 `MOD<n>/…` 키. **FW 는 오류를 내지 않고 버린다**(§13.0 A.2.6).
   검증기가 **경고를 내주지 않으면 아무도 모른다.**
2. **SHP/SHD 8의 배수**(ADM 슬롯이 있을 때, 매뉴얼 p.69, §13.3 W10). 이건 파서 상한이 아니라
   **하드웨어 권고**라 FW 가 걸러 주지 않는다.

---

## 부록 — 이 보고서를 만든 자료

- 소스 3판 정독 결과 8건 (`scratchpad/wf2/read_*.md`) — 통신층 · GUI 골격 · 영상/플롯 · 모듈 계층 · 모듈 구현 · 보조 위젯 · 매뉴얼 프로토콜 · 매뉴얼 모듈
- 통합 지침서 (`scratchpad/synthesis_brief.md`) — raw 채널 결론 정정, 다른 세션 결과, 실기 ACF 실측, 판별 차이
- 빌드·펌웨어 절은 이 세션에서 **원문을 직접 확인**했다: `archongui.pro`, `readme.txt`, `.qmake.stash`, `Makefile`, `Makefile.Release`, `archongui.pro.user`, `ArchonFW/*.mcs` **4종** (크기·md5·Intel HEX 레코드 수·체크섬 전수 검증·1252↔1271 문자열 대조), `diff -r` 세 판 전수, `wc -l` 20개 파일, `grep` 검증 여러 건
- 실기 ACF 13종 + `acf_timing_script_science.txt` · `acf_timing_script_guide.txt` (`__reference/acf/`) — 탭·`RAWSEL`·기하 전수 대조, `for1110`↔`for1259` 키 단위 대조, 타이밍 스크립트 ACF `LINE<n>` 역추출 검증 (§5.7)
- 매뉴얼 전문 추출본 (`scratchpad/wf2/manual.txt`) 및 Readout Notes 추출본 (`scratchpad/wf2/notes.txt`)

`__reference/` 는 **읽기만 했고 어떤 파일도 편집·생성하지 않았다.**

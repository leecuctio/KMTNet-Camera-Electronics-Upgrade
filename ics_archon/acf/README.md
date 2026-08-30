# Archon 설정 파일 (`.acf`)

컨트롤러에 올리는 **설정·타이밍 정본**이다. 취득 스크립트가
`CLEARCONFIG` → `WCONFIG`(전 줄) → `APPLYALL` 순으로 그대로 밀어 넣는다
(`../scr_labtest/README_labtest.md`).

벤치에서는 `~/AIC/Config/acf/` 에 두고, 스크립트의 `UNIT_ACF_SCI_NORMAL` 이
`../Config/acf/…` 로 가리킨다.

## 목록

| 파일 | 유닛 | `TAPLINES` | `BIGBUF` | **저장** 픽셀/탭 × 줄 | IP |
|---|---|---:|---:|---|---|
| `KMTC_SCI_101_STA0284_R2608_MK.acf` | CTIO science 1 (MK) | 33 | 1 | **1200** × 4700 | `.101` |
| `KMTC_SCI_102_STA0285_R2608_NT.acf` | CTIO science 2 (NT) | 33 | 1 | **1200** × 4700 | `.102` |
| `KMTS_SCI_101_STA0286_R2608_MK.acf` | SAAO science 1 (MK) | 33 | 1 | **1200** × 4700 | `.101` |
| `KMTK_SCI_113_STA0200_R2608_MK.acf` | KASI 시험 유닛 (MK) | **32** | 1 | **1200** × 4700 | `.113` |
| `KMTK_SCI_113_STA0200_R2608_NT.acf` | KASI 시험 유닛 (NT) | 33 | 1 | **1200** × 4700 | `.113` |
| `KMTK_GUI_162_STA0201_R2608.acf` | KASI guide ⭐ **현행 유일본** | 9 | **0** | **528** × 1033 | `.162` |

⚠️ **이 열은 `PIXELCOUNT` × `LINECOUNT` 다 -- 타이밍 파라미터가 아니다.**
바로 아래 절이 그 둘을 가른다.  ⚠️ **v1.7 까지 이 열은 타이밍 쪽 값
(`Pixels=1201`/`600`)을 싣고 있었다** (2026-08-29 정정).

⚠️ **구 `KMTT_SCI_113…` 2장은 폐기했다** (2026-08-27, 운영자) — `KMTT` 는
**D-017 에서 폐지된 사이트 코드**이고, `KMTK_…` 가 그 개명본이다(내용 동일함을
대조로 확인). 되살릴 일이 있으면 git 이력에 있다.

## ⚠️ 읽는 픽셀 수와 **저장되는** 픽셀 수가 다르다 (2026-08-29 확인)

**타이밍 파라미터 `Pixels` 는 시퀀서가 몇 개를 디지타이즈하나이고, 프레임에 실제로
담기는 것은 `PIXELCOUNT` 다.**  Archon GUI 에서는 **CDS/Deint 탭의 "Pixels per
Tap"** 이 그 값이다 (운영자 확인 2026-08-29).

| | 시퀀서가 디지타이즈 | **프레임에 저장** | 버려짐 |
|---|---:|---:|---:|
| guide | `Pixels=600` + 1 = **601** | `PIXELCOUNT=`**528** | 73 |
| science | `Pixels=1201` + 1 = **1202** | `PIXELCOUNT=`**1200** | 2 |

    LINE43  LCLK;   CALL SkipPixelFirst(PreSkipPixels)    8   버리며 지나감(디지타이즈 안 함)
    LINE44  RGHIGH; CALL PixelFirst(Pixels)             600   디지타이즈
    LINE45  RGHIGH; CALL SkipPixelFirst(PostSkipPixels)   0
    LINE46  RGHIGH; CALL PixelFirst(OverscanPixels)       0
    LINE47  RGHIGH; CALL PixelFirst                       1   ← 인자 없는 호출 = 1개 더

**그래서 저장 영상은 채널(탭)당 528 컬럼**이고, guide 프레임 전체는
**8탭 × 528 = `NAXIS1=4224`**, `NAXIS2=1033` 이다.  science 는 16탭 × 1200 =
`NAXIS1=19200`, 2 × 4700 = `NAXIS2=9400` (`../ics_archon.ini` 의 `naxis1`/`naxis2`).

**근거가 셋 일치한다** -- ① ACF 의 `PIXELCOUNT` ② Archon GUI 의 "Pixels per Tap"
③ **`gmon` v2 의 실측 7장**(`main` 브랜치, `gmon/DESIGN.md` 2절: "`NAXIS1=4224 =
8 세그먼트 × 528컬럼`").

⚠️ **science 의 여유 2 와 guide 의 73 은 성격이 다르다.**  science 쪽은 파이프라인
flush 여유로 읽히는데, guide 는 73개를 클록해 놓고 버린다 -- **픽셀 클록 구간의 약
12%** 다.  보관본까지 대조하면 **여섯 판이 전부 600/528 로 같아서**(`R2601`·
`R0827` 계열, 그리고 다른 유닛 `STA0291` 까지) 최근에 잘못 건드린 것이 아니라
처음부터 그런 설정이다.

⏳ **`Pixels` 를 528 로 줄일 수 있는지는 실기 시험 항목이다** (운영자 2026-08-29).
판정법은 **같은 조건에서 `Pixels=600` 과 `Pixels=528` 프레임을 찍어 바이트 비교** --
같으면 저장 창이 앞 528 이고 무손실로 트림된다.  ⚠️ **줄이더라도 `LINE47` 의 인자
없는 `CALL PixelFirst`(+1)는 남길 것** -- 그것이 flush 여유이고, science 가 1200
저장에 1202 를 도는 이유다.  트림하면 ACF 개정이므로 판 번호가 오르고 규격 4.3절의
`CTRLnCFG` 범프 사유가 된다.

⚠️ **"600 중 어느 528 인가" 는 `gmon` 과 공유하는 물음이다.**  `gmon/DESIGN.md`
10절이 "채널당 16컬럼(528−512)의 성격(프리스캔/다크 기준열)"을 커미셔닝 확인
항목으로 올려 두었다 -- 같은 답을 두 문서가 기다린다.

⭐ **`gmon` 은 이미 가정을 선언해 두었다** (`main` 브랜치 `gmon/gmon.conf`
`[geometry]`).  소비자 쪽의 현행 전제이므로 guide raw 규격을 세울 때 **이것과
어긋나면 분할이 깨진다**:

    raw_nx = 4224 · raw_ny = 1033 · nseg = 8 · seg_width = 528
    left_active  = 16,528     왼쪽 채널: 앞 16 컬럼이 비활성
    right_active = 0,512      오른쪽 채널: 뒤 16 컬럼이 비활성
    y_trim_bottom = 9         추가 9행은 아래쪽으로 가정

즉 **16 컬럼이 채널 쌍의 바깥쪽에 붙는다**는 가정이다.  ⭐ 그것이 **규격 4.1절의
science X overscan 패턴(`RRRRLLLL`, side varies)과 같은 부류**다 -- science 는
`AMPNAX1 = 1200 = PRESCNX(0) + IMAGEX(1152) + OVRSCNX(48)` 이고 prescan 을 아예
기록하지 않는다(`rawhdr.py`).  guide 528 = 16 + 512 도 같은 모양으로 읽힌다.
**두 계통이 같은 규범을 따르는 것이 자연스럽고, 그러면 guide 규격은 science 의
자리 잡는 방식을 그대로 물려받으면 된다** -- 다만 아직 실측 확정은 아니다.

⭐ 그리고 **`AMPNAX1`/`AMPNAX2` 가 곧 `PIXELCOUNT`/`LINECOUNT` 다** (1200 / 4700).
규격이 이미 프레임 버퍼 값을 쓰고 있었다 -- 틀렸던 것은 이 표뿐이다.

## guide 정본을 하나로 줄였다 (2026-08-28, 운영자)

**넷을 두던 자리에 최종본 하나만 둔다.**  이름도 science 와 같은 규칙으로
맞췄다:

    kmtnet_guide_STA0201_162_R0827_for1259_rtd9cal.acf
      -> KMTK_GUI_162_STA0201_R2608.acf          **내용은 바이트가 같다** (대조 확인)

빠진 셋 — `R0827_for1110_rtd9cal` 하나와 스왑 **전** `_TBC` 판 둘(`R2601_
for1110` · `R2601_for1259`) — 은 지운 것이 아니라
[`../__ref_archon_control/acf/`](../__ref_archon_control/acf/) 로 옮겼다.  그
폴더가 **벤더·실기에서 받은 원본 보관용**이다(운영자 2026-08-28) — 개명 전
`R0827_for1259_rtd9cal` 원본과 현행 science 다섯의 원본, 그리고 다른 guide
유닛(`STA0291`)의 ACF 둘도 함께 있다.  ⚠️ 그 사본들은 **줄 끝이 CRLF(원본
그대로)** 이고 저장소 정본은 LF 다 — 내용은 같다.

⚠️ **`archive/` 는 여전히 필요하다** — 거기 있는 `R2601_…_rtd9cal` 둘은
**limit 정정 전** 판이고, 그 내용은 `__ref_archon_control/acf/` 에 없다.  둘을
같은 것으로 보고 지우지 말 것.

⭐ **판 번호가 이제 규칙에 맞는다.**  `R0827` 은 `MMDD` 라 `YYMM` 규칙의
예외였고 **숫자로 정렬하면 구판보다 앞에 왔는데**(0827 < 2601), `R2608` 로
바뀌면서 그 예외가 없어졌다.  아래 절의 정정 내용은 그대로 유효하다 — 판
번호만 바뀌었고 바이트는 같다.

## `R2608` (구 `R0827`) — MOD10 센서 B/C limit 정정 (2026-08-27)

**MOD10 의 센서 B/C 위치를 맞바꿨을 때(`_rtd9cal` 판) 라벨만 옮기고 limit 설정을
안 옮겼다.**  그래서 CCD 채널이 벽면보드용 범위를, 벽면보드가 CCD 용 범위를 쓰고
있었다.  운영자 확정(2026-08-27)으로 바로잡고 판을 `R2601` → `R0827` 로 올렸다
(2026-08-28 에 규칙에 맞춰 `R2608` 로 다시 표기했다 — 내용은 그대로다).

    MOD10\SENSORBLABEL      = RTD8_CCD1  ->  RTD8_CCD     (칩 번호 표기 제거)
    MOD10\SENSORBLOWERLIMIT = -30        ->  -120         (B = RTD8_CCD)
    MOD10\SENSORBUPPERLIMIT = 60 / 70.0  ->  50.0
    MOD10\SENSORCLOWERLIMIT = -120       ->  -30          (C = RTD5_WB)
    MOD10\SENSORCUPPERLIMIT = 50.0       ->  70.0

**왜 중요한가** — `SENSORx{LOWER,UPPER}LIMIT` 는 RTD 변환의 유효 범위다.  CCD
채널 하한이 −30 이면 **−30 아래를 읽을 수 없다**(운용 온도가 −100 대다).  그리고
그 채널이 raw spec `CCDTEMP` 의 **유일한 원천**이므로 대체 센서도 없다.
결측 판정을 값이 아니라 **이 한계로** 하는 것이 규범이다 -- 미연결 채널이
`-273.2` 만 내는 것이 아니라 `-196.9`~`-206.1` 처럼 **그럴듯한 값도 흘리기**
때문이다 (실측 확인, `../SMC_CLAUDE.md` "실측 로그 판정").

⚠️ **`_TBC` 판 둘(`R2601`, 스왑 전)은 손대지 않았다** -- 그 판에서는 limit 이
이미 라벨과 맞다.  고치면 옛 배치의 이력이 사라진다.  지금은
`../__ref_archon_control/acf/` 에 있다.

⚠️ **저장소 사본을 고친 것이 실기에 반영되는 것은 아니다** -- 유닛에 올려
`APPLYALL` 을 해야 적용된다.  그리고 `__ref_archon_control/` 의 실험실
스크립트들(`archon_kmtnet_guide_tvm_v0.9….py` · `modtm_*.py` · `tvm_gui_goff_
v0.7….py`)의 `UNIT_ACF` 가 **구 파일명을 가리키므로 작업본에서 함께 고쳐야
한다** (그 폴더는 참고 원본 보관용이라 여기서 고치지 않는다).

정정 **전** 판은 `archive/` 에 있다.

## 읽을 때 알아둘 것

**모듈 구성이 science 와 guide 에서 다르다** (`[SYSTEM]` 의 `MODn_TYPE`,
`0` = 빈 슬롯).  `Cn_TEMP` 자리 표(규격 5.6.1절)가 여기서 갈린다:

| | 장착 슬롯 | 자리 수 (백플레인 포함) |
|---|---|---:|
| science 다섯 | 1·2·3·4·5·8·9·10·11 | **10** |
| guide | 3·4·5·6·7·9·10 | **8** |

science 쪽은 `rawhdr.TEMP_MODS` 와 정확히 같고, `__ref_archon_control/
modtm_sci_*.py`(실사용본)가 `STATUS` 에서 읽는 자리와도 같다 — 규격과 무관하게
쓰인 스크립트가 같은 표에 닿았다는 것이 **자리 표의 독립 확인**이다.
guide 8자리는 **raw spec 10.4절이 정본**이다 — v1.9 에서 `OI-19` 종결, 이 ACF
`[SYSTEM]` 과 `modtm_gui_*` 두 근거 일치 (첫 guide 구동 때 STATUS 재확인만 남는다).
형 번호는 science 가 `17`(ADM)·`18`(HVYBias), guide 가 `2`(AD)·`11`(HeaterX)·
`8`(HVXBias) 다.

**`BIGBUF` 가 science/guide 를 가른다.** science 는 `1`(768 MB × 2), guide 는
`0`(512 MB × 3). `../scr_labtest/` 에 smallbuf 사본을 남겨 둔 근거가 이것이다
— guide 취득 스크립트를 만들 때 버퍼 주소 지정이 참고가 된다. 다만 bigbuf 판은
`FETCH` 주소를 프레임 상태의 `BUFnBASE` 에서 읽어 **설계상 구성 무관**이므로
그쪽을 출발점으로 삼아도 된다(실기 검증은 첫 guide 구동 때).

**MK/NT ACF 는 구조적으로 동등하다.** 2026-08-27 에 `KMTC_SCI_101`↔`102` 를
전수 대조한 결과, `[CONFIG]` 항목 959개의 **집합이 같고** 다른 값은 33개뿐이며
그 전부가 `IP` 와 **amp 배정**(`TAPLINEn`)이다 — 검출기 조가 다르니 당연하다.
※ 섹션 순서만 다르다(MK 는 `[SYSTEM]` 먼저, NT 는 `[CONFIG]` 먼저). `configparser`
가 읽으므로 동작에는 영향이 없다.

**`TAPLINES` 가 33 과 32 로 갈리는 것은 기능 차이가 아니다.** 실제 tap 은
어느 판이든 **science 32개 · guide 8개**로 같고, 끝에 **빈 `TAPLINEn` 이 하나
붙었느냐**가 값을 1 올린 것뿐이다 (GUI 저장 시 생기는 꼬리로 보인다):

| | `TAPLINES` | 실제 tap | 마지막 항목 |
|---|---:|---:|---|
| science 대부분 · guide | 33 · 9 | 32 · 8 | `TAPLINE32`·`TAPLINE8` = 빈값 |
| `KMTK_SCI_113…MK.acf` | 32 | 32 | 빈 항목 없음 |

※ 2026-08-27 에 "amp 하나가 빠진 것 아니냐" 로 의심했다가 전수 대조로 해소했다.
`TAPLINES` 값만 보고 판단하지 말고 **빈 항목을 뺀 실제 tap 수**를 셀 것.

⚠️ **줄 끝은 LF 로 정규화된다** (`.gitattributes` 의 `*.acf text eol=lf`).
전 계통 리눅스 구동이고, CRLF 로 체크아웃되면 값 뒤에 `\r` 이 붙는 파서를
만나 조용히 틀리기 때문이다. Archon GUI 가 내보낸 원본(CRLF)과는 바이트가
다르니, GUI 로 되불러 편집할 일이 있으면 변환이 필요할 수 있다.

## 판 표기

`R2608` · `R2601` 은 ACF 개정 번호이고 **`YYMM`** 으로 읽는다.  파일명 규칙:

```
<SITE>_<역할>_<유닛번호>_<시리얼>_<ACF판>[_<검출기조>].acf
```

역할은 `SCI`(science) · `GUI`(guide) 다.  **검출기조(`_MK`/`_NT`)는 science
에만 붙는다** -- guide 는 유닛당 검출기가 하나라 가를 것이 없다.

유닛 ↔ 시리얼 대응의 정본은 `../../raw_fits_spec/__reference/Archon_Unit_Info.txt`
다 (`KMTC-SCI-101` ↔ `STA0284` 등).

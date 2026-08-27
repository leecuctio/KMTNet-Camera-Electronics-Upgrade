# Archon 설정 파일 (`.acf`)

컨트롤러에 올리는 **설정·타이밍 정본**이다. 취득 스크립트가
`CLEARCONFIG` → `WCONFIG`(전 줄) → `APPLYALL` 순으로 그대로 밀어 넣는다
(`../scr_labtest/README_labtest.md`).

벤치에서는 `~/AIC/Config/acf/` 에 두고, 스크립트의 `UNIT_ACF_SCI_NORMAL` 이
`../Config/acf/…` 로 가리킨다.

## 목록

| 파일 | 유닛 | `TAPLINES` | `BIGBUF` | Pixels × Lines | IP |
|---|---|---:|---:|---|---|
| `KMTC_SCI_101_STA0284_R2608_MK.acf` | CTIO science 1 (MK) | 33 | 1 | 1201 × 4700 | `.101` |
| `KMTC_SCI_102_STA0285_R2608_NT.acf` | CTIO science 2 (NT) | 33 | 1 | 1201 × 4700 | `.102` |
| `KMTS_SCI_101_STA0286_R2608_MK.acf` | SAAO science 1 (MK) | 33 | 1 | 1201 × 4700 | `.101` |
| `KMTK_SCI_113_STA0200_R2608_MK.acf` | KASI 시험 유닛 (MK) | **32** | 1 | 1201 × 4700 | `.113` |
| `KMTK_SCI_113_STA0200_R2608_NT.acf` | KASI 시험 유닛 (NT) | 33 | 1 | 1201 × 4700 | `.113` |
| `kmtnet_guide_STA0201_162_R2601_for1110.acf` | guide (센서 B/C 스왑 **전**) | 9 | **0** | 600 × 1033 | `.162` |
| `kmtnet_guide_STA0201_162_R2601_for1259.acf` | guide (센서 B/C 스왑 **전**) | 9 | **0** | 600 × 1033 | `.162` |
| `kmtnet_guide_STA0201_162_R0827_for1110_rtd9cal.acf` | guide (RTD9 보정 + **limit 정정**) | 9 | **0** | 600 × 1033 | `.162` |
| `kmtnet_guide_STA0201_162_R0827_for1259_rtd9cal.acf` | guide (RTD9 보정 + **limit 정정**) ⭐ 현행 | 9 | **0** | 600 × 1033 | `.162` |

⚠️ **구 `KMTT_SCI_113…` 2장은 폐기했다** (2026-08-27, 운영자) — `KMTT` 는
**D-017 에서 폐지된 사이트 코드**이고, `KMTK_…` 가 그 개명본이다(내용 동일함을
대조로 확인). 되살릴 일이 있으면 git 이력에 있다.

## `R0827` — MOD10 센서 B/C limit 정정 (2026-08-27)

**MOD10 의 센서 B/C 위치를 맞바꿨을 때(`_rtd9cal` 판) 라벨만 옮기고 limit 설정을
안 옮겼다.**  그래서 CCD 채널이 벽면보드용 범위를, 벽면보드가 CCD 용 범위를 쓰고
있었다.  운영자 확정(2026-08-27)으로 바로잡고 판을 `R2601` → `R0827` 로 올렸다.

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

⚠️ **`_TBC` 판 둘(`R2601`)은 손대지 않았다** -- 스왑 **전** 배치이고 그 판에서는
limit 이 이미 라벨과 맞다.  고치면 옛 배치의 이력이 사라진다.

⚠️ **`R0827` 은 판 번호 규칙의 예외다** -- `R2608`·`R2601` 은 `YYMM` 으로 읽히는데
이것은 운영자가 정한 `MMDD`(2026-08-27) 다.  **숫자 크기로 정렬하면 구판보다
앞에 온다**(0827 < 2601) -- 순서는 파일명이 아니라 이 절과 git 이력으로 판단할 것.

⚠️ **저장소 사본을 고친 것이 실기에 반영되는 것은 아니다** -- 유닛에 올려
`APPLYALL` 을 해야 적용된다.  그리고 실험실 TVM 감시 스크립트
(`../__ref_archon_control/archon_kmtnet_guide_tvm_v0.9….py`)의 `UNIT_ACF` 가
**구 파일명을 가리키므로 함께 고쳐야 한다** (그 폴더는 참고 원본 보관용이라
여기서 고치지 않았다).

구판은 `archive/` 에 있다.

## 읽을 때 알아둘 것

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
전 계통 리눅스 구동이고, CRLF 로 체크아웃되면 값 뒤에 `
` 이 붙는 파서를
만나 조용히 틀리기 때문이다. Archon GUI 가 내보낸 원본(CRLF)과는 바이트가
다르니, GUI 로 되불러 편집할 일이 있으면 변환이 필요할 수 있다.

## 판 표기

`R2608` · `R2601` · `R0827` 은 ACF 개정 번호다 (`R0827` 은 위 예외 참조).
파일명 규칙:

```
<SITE>_<역할>_<유닛번호>_<시리얼>_<ACF판>_<검출기조>.acf
```

유닛 ↔ 시리얼 대응의 정본은 `../../raw_fits_spec/__reference/Archon_Unit_Info.txt`
다 (`KMTC-SCI-101` ↔ `STA0284` 등).

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
| `KMTT_SCI_113_STA0200_R2608_MK.acf` | 시험 유닛 (MK) | **32** | 1 | 1201 × 4700 | `.113` |
| `KMTT_SCI_113_STA0200_R2608_NT.acf` | 시험 유닛 (NT) | 33 | 1 | 1201 × 4700 | `.113` |
| `kmtnet_guide_STA0201_162_R2601_for1110.acf` | guide | 9 | **0** | 600 × 1033 | `.162` |
| `kmtnet_guide_STA0201_162_R2601_for1110_rtd9cal.acf` | guide (RTD9 보정) | 9 | **0** | 600 × 1033 | `.162` |
| `kmtnet_guide_STA0201_162_R2601_for1259.acf` | guide | 9 | **0** | 600 × 1033 | `.162` |
| `kmtnet_guide_STA0201_162_R2601_for1259_rtd9cal.acf` | guide (RTD9 보정) | 9 | **0** | 600 × 1033 | `.162` |

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

⚠️ **`KMTT_SCI_113…MK.acf` 만 `TAPLINES=32`** 다. 나머지 science 판은 전부 33
이다. 시험 유닛이라 당장 쓰이지 않지만, 쓰기 전에 의도한 값인지 확인할 것.

## 판 표기

`R2608` · `R2601` 은 ACF 개정 번호다. 파일명 규칙:

```
<SITE>_<역할>_<유닛번호>_<시리얼>_<ACF판>_<검출기조>.acf
```

유닛 ↔ 시리얼 대응의 정본은 `../../raw_fits_spec/__reference/Archon_Unit_Info.txt`
다 (`KMTC-SCI-101` ↔ `STA0284` 등).

# 레거시 FITS 헤더 실측본 — 무엇이 무엇인가

운영자가 레거시 KMTNet 시스템의 실제 FITS 헤더를 덤프해 넣어 준 자료다. **신규 Archon raw pair 헤더 설계의 1차 근거**이며, 판정 결과는 `../../KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` **5.13절**에 표로 남겼다.

## 파일 구성 (35개)

| 파일 | 정체 | 이 규격에서의 위치 |
| --- | --- | --- |
| `KMTNk.20170209.044131.Rawheader.txt` | **레거시 raw 헤더.** 2017-02-09 SSO, CCD `K`, 9688×9232, 123개 카드 | ⭐ **신규 raw pair 에 대응하는 유일한 실측본.** 5.13절 판정의 근거 |
| `xkmta.20170209.044131.MEF.header.txt` | 같은 노출을 레거시가 MEF 로 변환한 것의 **PRIMARY** 헤더 | raw → MEF 로 무엇이 전달되는지 |
| `xkmta.20170209.044131.MEF.<CHIP><nn>header.txt` (32개) | 같은 MEF 의 **amp extension** 헤더. chip `M`/`K`/`N`/`T` × stripe `01`~`08` | amp 단위 좌표·WCS 관례 |
| `KMTNc.20210503.030331.header.txt` | ⚠️ **raw 가 아니다.** `DETID='C'`, 1616×1616 — **raw 영상의 ROI 조각들을 모자이크로 재구성한 combination 산출물**(운영자 확인) | 검출기가 아니므로 규격 범위 밖 |

## 읽을 때 주의할 것 셋

**1. raw 실측은 1건뿐이다.** `KMTNc.20210503` 이 2021년 자료라서 "raw 2건, 4년간 불변" 으로 읽고 싶어지지만 그건 raw 가 아니다. 두 파일의 keyword 집합은 `INPUTFMT` 하나만 다른데, 그것이 뒷받침하는 사실은 *"raw 헤더가 4년간 안 바뀌었다"* 가 아니라 **"같은 헤더 틀을 raw 와 조합 산출물에 함께 썼다"** 다. 후자도 틀이 정착돼 있었다는 근거는 되지만, 시간에 따른 안정성의 근거는 아니다.

**2. MEF PRIMARY 는 raw 헤더를 거의 그대로 복사한 것이다.** 두 파일을 나란히 놓고 보면 1~128행이 사실상 같고, MEF 쪽에만 `DETSIZE`·`UT`·`NUMFILES`·`<CHIP>CCDFILE`·`COLGAP`·`ROWGAP`·`MIDJD`·`MIDHJD`·`LJD` 가 더 있다. **그래서 MEF PRIMARY 가 필요한 값은 raw 가 실어야 한다** — 이 원칙이 규격 5.5.0절(컨트롤러 정체를 색인형으로 싣기)의 뿌리다.

**3. 값 없는 카드가 그대로 남아 있다.** `GAINDL`·`PIXITIME`·`TSHSHUT`·`RTD12` 는 `KEYWORD / comment` 형태로 **값이 없다.** 4년(실제로는 그 이상)치 아카이브가 이 상태로 쌓였다. 규격 5.0절이 *"결측이면 카드를 넣지 않는다"* 로 정한 근거가 여기 있다.

## 덤프 형식

`KMTNk...Rawheader.txt` 는 keyword 와 `=` 사이가 **탭**이고, MEF 쪽은 FITS 80칼럼 원문이다. 파싱할 때 둘을 같은 정규식으로 다루면 raw 쪽을 놓친다.

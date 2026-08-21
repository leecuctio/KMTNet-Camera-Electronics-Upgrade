# raw FITS 헤더 카드 — converter 가 읽는 것 · 읽지 않는 것 · 폐지된 것

**v1.1** · 생성 2026-08-18 · **원천에서 기계 추출했다** — 손으로 옮겨 적은 표가 아니다.

| 항목 | 값 |
| --- | --- |
| 대상 converter | `../../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) |
| 3장 추출 | `card("<MEF>", v("<raw>", <기본값>), …)` 호출을 정규식으로 파싱 |
| 6장 출처 | `../KMT_CEU_Raw_to_MEF_Keyword_Map_v0.7_REVIEW.md` 4.H 절 |
| 7장 출처 | DECISION_LOG **D-013** (Accepted) — 표 본문은 아래 raw pair 규격 5.13절 |
| 레거시 대조본 | `Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt` (keyword 123개) |

> **이 문서에서 "규격" 은 `../KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`(raw pair 규격) 를 가리킨다.**
>
> ⚠️ 그 문서는 **((재작성중))** 이라 절 번호가 바뀔 수 있다. 아래에서 `규격 5.12` 처럼 절을 적은 곳은 **지금 그 내용이 어디 있는지 알려주는 포인터일 뿐 근거가 아니다.** 확정된 근거는 `../../project_management/governance/DECISION_LOG.md` 의 **D-번호**다 — 이 문서가 기대는 것은 D-011(사이트 코드 파일명) · **D-013**(레거시 keyword 판정) 이고 둘 다 Accepted 다.

> **v1.1 에서 늘어난 것**: v1.0 은 *converter 가 읽는 카드*만 다뤘다. 그래서 `DETID` 처럼 **레거시에 있었지만 폐지된 카드**를 찾으면 어디에도 없어 *"빠진 것인가"* 를 판단할 수 없었다. v1.1 은 6장(raw 에만 있는 카드 53장)과 7장(폐지 17장)을 더해 **레거시 123개를 전량 귀속**시킨다 — 8장이 그 대조표다.

## 1. 요약

| | 개수 |
| --- | ---: |
| **converter 가 raw 에서 읽는다** (3~5장) | **104** |
| &nbsp;&nbsp;— `card()` 로 곧바로 들어간다 | 102 |
| &nbsp;&nbsp;— `card()` 밖에서 쓰인다 (`DATE-OBS` · `TCSDRIV`) | 2 |
| **raw 에만 있다 — converter 가 읽지 않는다** (6장) | **53** |
| **폐지됐다 — 신규 raw 가 싣지 않는다** (7장) | **17** |

읽는 104개를 레거시 raw 실측본에 대면:

| | 개수 |
| --- | ---: |
| 레거시 raw 에 **있다** — 계승하면 끝난다 | **78** |
| 레거시 raw 에 **없다** — 신규 판단 대상 | **26** |

> **전부 MK 헤더에서만 읽는다.** `convert()` 가 두 chip 에 `mk_hdr` 하나만 넘기므로 NT 헤더는 현재 반영되지 않는다 (변경점 C-17).

## 2. 표 보는 법

| 열 | 뜻 |
| --- | --- |
| **레거시** | `O` = 레거시 raw 실측본에 있다(계승) · **`X`** = 없다(신규 결정 대상) |
| **MEF 목적지** | 그 값이 들어가는 MEF 카드. `+amp` 는 amp extension 에도 반복 기록된다는 표시 |
| **없을 때** | raw 에 그 카드가 없을 때 converter 가 대신 넣는 값. **오류는 나지 않는다** |

표기: `ᴬ` = AUX/TCS 중계(pass-through) · `ᶠ` = FITS 표준 카드

> **`X` 가 전부 결함인 것은 아니다.** raw 가 실을 필요가 없다고 이미 정리된 것도 `X` 로 나온다 — 3.3절의 `XTALKVER` · `REFVER` · `CATVER` 가 그렇다. 각 표 아래 주석이 그 구분을 적어 둔다.

## 3.1 관측소 · 검출기 · 관측 식별

| raw 키워드 | 레거시 | MEF 목적지 | 없을 때 |
| --- | :---: | --- | --- |
| `ORIGIN` | O | `ORIGIN` | `"KASI"` |
| `BUNIT` | O | `BUNIT` `+amp` | `"ADU"` |
| `DETECTOR` | O | `DETECTOR` | `"e2v CCD290-99"` |
| `CCDXBIN` | O | `CCDXBIN` | `1` |
| `CCDYBIN` | O | `CCDYBIN` | `1` |
| `OBSERVAT` | O | `OBSERVAT` · `SITEID` | `""` |
| `TELESCOP` | O | `TELESCOP` | `"KMTNet 1.6m"` |
| `LATITUDE` | O | `LATITUDE` | `""` |
| `LONGITUD` | O | `LONGITUD` | `""` |
| `ELEVATIO` | O | `ELEVATIO` | `""` |
| `OBSERVER` | O | `OBSERVER` | `""` |
| `OBJECT` | O | `OBJECT` `+amp` | `""` |
| `FIELDID` | **X** | `FIELDID` | `v("OBJECT", "")` ← fallback |
| `PROJID` | O | `PROJID` `+amp` | `""` |
| `IMAGETYP` | O | `IMAGETYP` `+amp` | `""` |
| `OBSTYPE` | O | `OBSTYPE` `+amp` | `""` |
| `INSTRUME` | O | `INSTRUME` | `"KMTS"` |
| `UNIQNAME` | O | `UNIQNAME` | `""` |

**신규는 `FIELDID` 하나뿐이다.** 없으면 `OBJECT` 값이 그대로 들어간다 — 레거시가 필드명을 `OBJECT` 에 넣던 관행을 코드가 흡수한 형태다.

**`OBSERVAT` 는 이 문서에서 유일하게 "없거나 어긋나면 변환이 멈추는" 카드다.** `SITEID` 로도 복제되고, converter v2.2.0 이 **파일명의 사이트 코드와 교차 검증**한다 — 불일치는 오류다 (D-011). 나머지 카드는 전부 조용히 기본값으로 지나간다.

> ⚠️ **기본값이 진짜 값처럼 보이는 넷**: `ORIGIN="KASI"` · `DETECTOR="e2v CCD290-99"` · `TELESCOP="KMTNet 1.6m"` · `INSTRUME="KMTS"`. raw 가 안 실으면 이 값들이 사이트·망원경과 무관하게 박힌다.
>
> 레거시 실측본과 대면 어긋남이 보인다 — 레거시는 `TELESCOP='KMTNet 1.6m #3'` 으로 **망원경 번호까지** 싣고, `OBSERVAT='SSO'` 인데 `INSTRUME='KMTS'` 다. 실측 1건이라 단정할 수는 없으나 **최소한 `INSTRUME` 와 사이트가 함께 움직이지는 않는다.**

## 3.2 노출 · 시각

| raw 키워드 | 레거시 | MEF 목적지 | 없을 때 |
| --- | :---: | --- | --- |
| `EXPTIME` | O | `EXPTIME` | `0.0` |
| `DARKTIME` | O | `DARKTIME` | `0.0` |
| `TSHOPEN` | O | `TSHOPEN` | `""` |
| `TSHSHUT` | O | `TSHSHUT` | `""` |
| `TIMESYS` | O | `TIMESYS` | `"UTC"` |

**이 그룹에서 가장 중요한 `DATE-OBS` 는 이 표에 없다** — `card()` 밖에서 쓰이므로 4장에 있다.

`TSHOPEN` 은 MEF `UT` 조립에도 쓰인다. converter 가 `DATE-OBS` 의 날짜부에 raw `TSHOPEN` 을 붙여 만들기 때문에(`v2_1.py:440` · `:583`), **raw 의 `UT` 카드를 폐지해도 MEF `UT` 는 영향을 받지 않는다** (7장).

> ⚠️ `EXPTIME` · `DARKTIME` 의 기본값이 `0.0` 이다 — 카드가 없으면 **"노출 0초"** 라는 유효해 보이는 값이 들어간다.

## 3.3 Archon 정체 · 버전

| raw 키워드 | 레거시 | MEF 목적지 | 없을 때 |
| --- | :---: | --- | --- |
| `CTRL1ID` | **X** | `CTRL1ID` | `"UNKNOWN"` |
| `CTRL1SN` | **X** | `CTRL1SN` | `"UNKNOWN"` |
| `CTRL1FW` | **X** | `CTRL1FW` | `"UNKNOWN"` |
| `CTRL2ID` | **X** | `CTRL2ID` | `"UNKNOWN"` |
| `CTRL2SN` | **X** | `CTRL2SN` | `"UNKNOWN"` |
| `CTRL2FW` | **X** | `CTRL2FW` | `"UNKNOWN"` |
| `CTRLVER` | **X** | `CTRLVER` | `"ARCHON-v1.0"` |
| `TIMVER` | **X** | `TIMVER` | `"TIM-v1.0"` |
| `BIASVER` | **X** | `BIASVER` | `"BIAS-v1.0"` |
| `CLKVER` | **X** | `CLKVER` | `"CLK-v1.0"` |
| `XTALKVER` | **X** | `XTALKVER` | `"UNMEASURED"` |
| `REFVER` | **X** | `REFVER` | `"N/A"` |
| `CATVER` | **X** | `CATVER` | `"N/A"` |

**13개 전부 레거시 raw 에 없다.** 다만 성격이 둘로 갈린다.

**`XTALKVER` · `REFVER` · `CATVER` 셋은 raw 가 실을 필요가 없다.** converter 가 읽기는 하지만 raw 에 그 카드가 없으므로 **기본값(`"UNMEASURED"` · `"N/A"`)으로 채워지고, 지금은 그것이 맞는 상태다.** 규격 5.12 절이 *"현행 converter 는 이 값들을 MK 헤더에서 읽고 있지만 실제로는 calibration DB 소관"* 이라고 정리했고, caldb 주입으로 바꾸는 것이 **변경점 C-14** 다. 즉 이 셋의 `X` 는 결함이 아니라 **의도된 상태**다.

나머지 10개는 신규 전자부에 필연적으로 따라오는 것이라 쟁점이 *만들지 말지*가 아니라 **어떤 이름으로** 다.

**`CTRL1*` · `CTRL2*` 가 색인형인 이유**: converter 가 **MK 헤더만** 읽으면서(`convert()` 가 두 chip 에 `mk_hdr` 하나만 넘긴다) 컨트롤러 두 대분 정체를 요구한다. 단수형으로 두면 MEF 가 전부 `UNKNOWN` 을 받는다. 레거시도 raw 파일마다 `KBUILD`/`MBUILD`/`TBUILD`/`NBUILD` 를 다 실어 같은 구조였다 — 그 넷은 7장에서 폐지되고 `CTRL1FW`/`CTRL2FW` 가 자리를 물려받았다.

> ⚠️ **버전 문자열의 기본값이 진짜 provenance 처럼 보인다** — `"ARCHON-v1.0"` · `"TIM-v1.0"` · `"BIAS-v1.0"` · `"CLK-v1.0"`. raw 가 안 실어도 MEF 에 그럴듯한 버전이 박히고 오류는 나지 않는다. 이 값들의 **근거가 순환하는 문제**는 검토 문서 2.4절에 있다.

## 3.4 TCS 링크 · 포인팅

| raw 키워드 | 레거시 | MEF 목적지 | 없을 때 |
| --- | :---: | --- | --- |
| `TCSLINK` | O | `TCSLINK` | `""` |
| `TCSARC` | O | `TCSARC` | `""` |
| `TCSQDATE` | O | `TCSQDATE` | `""` |
| `TCSUDATE` | O | `TCSUDATE` | `""` |
| `RADECSYS` | O | `RADECSYS` | `"ICRS"` |
| `RA` | O | `RA` `+amp` | `"00:00:00.00"` |
| `DEC` | O | `DEC` `+amp` | `"+00:00:00.0"` |
| `EQUINOX` | O | `EQUINOX` | `2000.0` |
| `HA` | O | `HA` `+amp` | `""` |
| `ST` | O | `ST` `+amp` | `""` |
| `SECZ` | O | `SECZ` `+amp` | `""` |
| `ALT` | O | `ALT` `+amp` | `""` |
| `AZ` | O | `AZ` `+amp` | `""` |
| `TCSDRIVE` | O | `TCSDRIV` | `v("TCSDRIV", "")` ← fallback |
| `TELMOVE` | O | `TELMOVE` | `""` |

**전부 레거시 계승이다.** 4장의 `TCSDRIV` 만 `X` 인데 그것도 구멍이 아니다 — converter 가 **`TCSDRIVE`(8자)를 먼저 보고** 없을 때만 `TCSDRIV` 를 본다. 레거시가 쓰는 이름이 `TCSDRIVE` 이므로 **raw 는 `TCSDRIVE` 로 쓰면 된다.**

> ⚠️ **`RA` · `DEC` 의 기본값이 빈 문자열이 아니다** — `"00:00:00.00"` · `"+00:00:00.0"`. 카드가 없으면 **형식이 유효한 그럴듯한 좌표**가 들어가서 하류에서 걸러지지 않는다. `EQUINOX` 도 `2000.0` 이 들어간다.

## 3.5 AUX — 링크 · 필터/셔터 · 초점

| raw 키워드 | 레거시 | MEF 목적지 | 없을 때 |
| --- | :---: | --- | --- |
| `AUXLINK` | O | `AUXLINK` | `""` |
| `AUXARC` | O | `AUXARC` | `""` |
| `AUXQDATE` | O | `AUXQDATE` | `""` |
| `AUXUDATE` | O | `AUXUDATE` | `""` |
| `FSSTAT` | O | `FSSTAT` | `""` |
| `FILTOP` | O | `FILTOP` | `""` |
| `FILNUM` | O | `FILNUM` | `""` |
| `FILTER` | O | `FILTER` `+amp` | `""` |
| `SHUTOP` | O | `SHUTOP` | `""` |
| `SHUTTER` | O | `SHUTTER` | `""` |
| `FSATEMP` | **X** | `FSATEMP` | `""` |
| `FSAHUM` | **X** | `FSAHUM` | `""` |
| `FSADEW` | **X** | `FSADEW` | `""` |
| `FSAALRM` | **X** | `FSAALRM` | `""` |
| `FASTAT` | O | `FASTAT` | `""` |
| `FAFOCUS` | O | `FAFOCUS` | `""` |
| `FATILTNS` | O | `FATILTNS` | `""` |
| `FATILTEW` | O | `FATILTEW` | `""` |
| `FAPOSS` | O | `FAPOSS` | `""` |
| `FALIMS` | O | `FALIMS` | `""` |
| `FAPOSE` | O | `FAPOSE` | `""` |
| `FALIME` | O | `FALIME` | `""` |
| `FAPOSW` | O | `FAPOSW` | `""` |
| `FALIMW` | O | `FALIMW` | `""` |

**24개 중 신규는 FSA 환경 4개(`FSATEMP` `FSAHUM` `FSADEW` `FSAALRM`)뿐**이고 나머지 20개는 레거시 계승이다.

FSA 4개는 **레거시 raw 어디에도 없다.** 그래서 sentinel 로 채우는 것이 오히려 정보를 흐릴 수 있다 — 없는 장치를 `NC` 로 적으면 *"TC 가 안 보냄"* 과 *"그런 장치가 없음"* 이 섞인다. 검토 문서 5.4절 9번이 이것을 묻는다.

`SHUTTER` 는 `SHUTOP` 의 **순수 함수**이고 "완전 개방" 을 뜻하지 않는다 — `OPEN` 이 개방중·개방·폐쇄중을 모두 덮는다 (규격 5.10 의 통제 어휘).

## 3.6 AUX — 돔 · 미러커버

| raw 키워드 | 레거시 | MEF 목적지 | 없을 때 |
| --- | :---: | --- | --- |
| `DSSTAT` | O | `DSSTAT` | `""` |
| `DSUP` | O | `DSUP` | `""` |
| `DSLW` | O | `DSLW` | `""` |
| `DSSAF` | O | `DSSAF` | `""` |
| `DSAUTO` | O | `DSAUTO` | `""` |
| `DSALT` | O | `DSALT` | `""` |
| `DSAZ` | **X** | `DSAZ` | `""` |
| `DSTELALT` | **X** | `DSTELALT` | `""` |
| `DSTELAZ` | **X** | `DSTELAZ` | `""` |
| `DALTERR` | **X** | `DALTERR` | `""` |
| `DAZERR` | **X** | `DAZERR` | `""` |
| `MCSTAT` | O | `MCSTAT` | `""` |
| `MCPOS` | O | `MCPOS` | `""` |

**돔 필드는 셋으로 갈린다** — 계승 6(`DSSTAT` `DSUP` `DSLW` `DSSAF` `DSAUTO` `DSALT`) · 신규 4(`DSAZ` `DSTELAZ` `DALTERR` `DAZERR`) · 개칭 1(`DSTELALT`).

`DSTELALT` 는 레거시 `DSTEL` 의 개칭이다 (D-013). **AUX 실선은 여전히 `DSTEL` 을 보내고 converter 는 `DSTELALT` 만 읽는다(fallback 없음)** — 그 사이를 ICS 가 옮겨 실어야 한다.

> 계승 6개는 `ics_sim` 이 아직 쓰지 않는다. **레거시 설계에 이미 있으므로 검토 안건이 아니라 구현 일감이다.**

## 3.7 AUX — 열 환경 · 영상 점검

| raw 키워드 | 레거시 | MEF 목적지 | 없을 때 |
| --- | :---: | --- | --- |
| `CHSTAT` | O | `CHSTAT` | `""` |
| `ENSTAT` | O | `ENSTAT` | `""` |
| `ENFAN` | O | `ENFAN` | `""` |
| `CCDTEMP` | O | `CCDTEMP` | `""` |
| `DEWPRES` | O | `DEWPRES` | `""` |
| `PT30N1` | O | `PT30N1` | `""` |
| `PT30N2` | O | `PT30N2` | `""` |
| `CHARCOAL` | O | `CHARCOAL` | `""` |
| `AIR_IN` | O | `AIR_IN` | `""` |
| `AIR_OUT` | O | `AIR_OUT` | `""` |
| `GLYC_IN` | O | `GLYC_IN` | `""` |
| `GLYC_OUT` | O | `GLYC_OUT` | `""` |
| `CHKIMG` | **X** | `CHKIMG` | `""` |
| `CHKIMG_C` | **X** | `CHKIMG_C` | `""` |

**14개 중 신규는 `CHKIMG` · `CHKIMG_C` 둘뿐**이고, 이 둘도 레거시 raw 에 없어 FSA 4개와 같은 물음에 걸린다 (검토 문서 5.4절 9번).

`CCDTEMP` 는 레거시 계승이지만 **신규 raw 에서는 `CCDTEMP1` · `CCDTEMP2` 의 평균으로 파생한다** (D-013). chip 별 온도 두 카드는 raw 에만 남고 MEF 로는 평균 하나만 간다.

## 4. `card()` 밖에서 쓰이는 둘

| raw 키워드 | 레거시 | 쓰임새 |
| --- | :---: | --- |
| `DATE-OBS` | O | `DATE-OBS` · `MJD-OBS` · `JD` · `UT` 를 여기서 파생시킨다. ⚠️ **없으면 변환 시각(now)으로 대체**되어 네 카드가 전부 관측과 무관해지고 **그래도 오류가 나지 않는다** (규격 6.2, C-6) |
| `TCSDRIV` | **X** | `TCSDRIVE` 가 없을 때만 보는 fallback 이다. 레거시가 쓰는 이름은 8자 `TCSDRIVE` 이므로 **구멍이 아니다** |

**이 문서 전체에서 가장 위험한 카드가 `DATE-OBS` 다.** 다른 카드는 없으면 빈 문자열이 들어가 나중에라도 눈에 띄지만, `DATE-OBS` 는 **그럴듯한 시각**으로 채워져 티가 나지 않는다.

## 5. `hval()` 로 직접 읽는 것

`v()` 를 거치지 않고 변환 로직이 직접 읽는 카드다. MEF 카드로 옮기는 것이 아니라 **픽셀 해석과 검증에 쓴다.**

| raw 키워드 | 쓰임새 |
| --- | --- |
| `BITPIX` · `BSCALE` · `BZERO` | 픽셀 값 복원 (`BITPIX=16` + `BZERO=32768` 부호없는 저장) |
| `NAXIS1` · `NAXIS2` | raw 영상 크기 확인 (`19200 x 9400`) |
| `OBSERVAT` | 파일명 사이트 코드와 **교차 검증** — 불일치는 오류 (v2.2.0, D-011) |

## 6. raw 에만 있는 카드 — converter 가 읽지 않는다 (53장)

**MEF 로 가지 않는다.** 용도는 (1) converter 교차검증 선언, (2) pair 식별, (3) 아카이브 기록 세 가지다. 검토 문서 v0.7 의 4.H 절과 같은 내용이고, `레거시` 열만 이 문서 방식으로 다시 매겼다.

| raw 카드 | 레거시 | 용도 / 설명 | 유의사항 |
| --- | :---: | --- | --- |
| `ACFFILE` | **X** | 적용된 Archon 설정 파일 | 적용된 Archon 설정 파일.<br>**설정 provenance 의 유일한 포인터**인데<br>MEF 목적지가 없다(ACT-011) |
| `AMPMAP` | **X** | `EXPLICIT`이면 아래 표가 유효. `DEFAULT`면 converter의<br>추정식을 쓴다는 선언 | `EXPLICIT` / `DEFAULT` 선언. `DEFAULT` 는<br>converter 의 추정식을 쓰겠다는 **명시적 선언**이다 |
| `BCKTEMP` | **X** | `TELEMETRY.BOARDTEMP` [degC] |  |
| `BUFNO` | **X** | 사용한 Archon frame buffer | 사용한 Archon frame buffer. 〃 |
| `CCDCOLS` | **X** | chip 1개의 active column (`NSTRIP × AMPDATA`) |  |
| `CCDROWS` | **X** | chip 1개의 active row (`TOPROWS + BOTROWS`) |  |
| `CCDTEMP1` | **X** | `CHIP1` 온도 [degC] | CHIP1 온도. `CCDTEMP` 는 이 둘의 **평균으로 파생**한다 |
| `CCDTEMP2` | **X** | `CHIP2` 온도 [degC] | CHIP2 온도. 〃 |
| `CHECKSUM` | **X** | FITS 표준 checksum |  |
| `CHIP1` | **X** | X 1–9600 절반의 chip |  |
| `CHIP2` | **X** | X 9601–19200 절반의 chip |  |
| `CHIPS` | **X** | 이 파일에 담긴 chip (X 낮은 쪽부터) |  |
| `CHOP` | O | — |  |
| `CHPROC` | O | — |  |
| `CHSET` | O | — |  |
| `CTRLERR` | **X** | `TELEMETRY.ERRORFLAG` |  |
| `CTRLSTAT` | **X** | `TELEMETRY.STATUS` |  |
| `CTRLTAG` | **X** | **이 파일이 pair의 어느 쪽인가** | 이 파일이 pair 의 어느 쪽인가. 〃 |
| `DATASRC` | O | **`ARCHON` / `SIM`** — 레거시 계승(5.13절). 픽셀이<br>실제 컨트롤러에서 왔는지 시뮬레이터가 만든 것인지.<br>**시뮬 프레임이 실측으로 오인되는** **것을**<br>**막는 유일한 카드다** | ⚠️ **`ARCHON` / `SIM` — 시뮬 프레임이**<br>**실측으로 오인되는 것을 막는 유일한**<br>**카드.** MEF 목적지가 없다(ACT-011) |
| `DATASUM` | **X** | FITS 표준 datasum |  |
| `ENS1` | O | — |  |
| `ENS2` | O | — |  |
| `ENS3` | O | — |  |
| `ENS4` | O | — |  |
| `ENS5` | O | — |  |
| `ENS6` | O | — |  |
| `ENS7` | O | — |  |
| `EXECODE` | **X** | ICS relay 필드 |  |
| `FRAMENO` | **X** | controller frame counter | 컨트롤러 frame counter. 진단용, MEF 목적지 없음 |
| `HEMODE` | O | **`SCIENCE` / `GUIDE`** — 레거시 계승(5.13절). Archon<br>3대 중 1대가 guide 전용이므로 이 구분이 살아 있다 | `SCIENCE` / `GUIDE`. Archon 3대 중<br>1대가 guide 전용이라 구분이 살아 있다 |
| `ICSBUILD` | O | **취득 프로그램의 빌드 식별자** — 레거시 계승(5.13절).<br>형식은 `<프로그램>-v<버전>:<빌드일시(UTC)>` | `<프로그램>-v<버전>:<빌드일시(UTC)>`.<br>파이썬이라 빌드 시각을 코드에 손으로 적는다 |
| `LEDFLASH` | O | 점검용 LED 프로젝터 점등 시간 [초]. `0`이면 점등 안<br>함. **레거시 계승(5.13절)** — 램프로 만든 실험실 flat<br>을 하늘 자료로 오인하지 않게 하는 카드다. 단위는<br>레거시와 같은 **초**를 유지한다(ICS 내부는 ms 이므로<br>나눠서 싣는다) | 점검용 LED 점등 시간 [**초**]. 램프<br>flat 을 하늘 자료로 오인하지 않게 한다 |
| `MIDOSCB` | **X** | 그중 BOT half에서 나온 row 수 (**실측 확인 필요**) |  |
| `MIDOSCT` | **X** | 그중 TOP half에서 나온 row 수 (**실측 확인 필요**) |  |
| `NAMPRAW` | **X** | **이 파일에 담긴 amplifier 수** (chip 2 × amp 16) |  |
| `NPHLINES` | O | preheat line 수 — 레거시 계승(5.13절). ADC/비디오단을<br>안정시키려 독출 전에 버리는 dummy line. 값의 정본은<br>`ACFFILE`이 가리키는 timing script 다 | preheat line 수. 값의 정본은<br>`ACFFILE` 이 가리키는 timing script |
| `NXTILE` | **X** | X 방향 amp tile 수 (chip 2 × strip 8) |  |
| `OSCNPATT` | **X** | strip 1–8의 overscan 위치 (R=오른쪽, L=왼쪽).<br>**근거는 converter의** **`is_bias_right()`** —<br>`strip_id(amp)=((amp-1)%8)+1`,<br>`is_bias_right(amp)= 1≤amp≤4 or 9≤amp≤12`, amp<br>1–8=TOP·9–16=BO | **근거는 converter 의 `is_bias_right()`**(`:253-266`)<br>— strip 1~4=R, 5~8=L. converter 가 이 카드를 읽지<br>않아 **선언과 하드코딩이 갈라져도 변환 쪽에서 못**<br>**잡는다**(C-5/C-13). 취득 SW 쪽 방어는<br>`test_geometry_vs_converter.py` |
| `PAIRFILE` | **X** | 짝의 이름. **`FILENAME` 과 같은 형태(확장자**<br>**없음)** | 짝의 이름. converter 는 CLI 로 두 경로를 받으므로 읽지<br>않는다 — **아카이브 도구용이고 그 도구가 아직 없다** |
| `RAWPROD` | **X** | 이 파일이 CEU Archon science raw임을 선언 | raw 산출물 선언. MEF 는 `DATAPROD` 를 따로 만든다 |
| `RAWVER` | **X** | **raw 규격/geometry 버전.** 4장이 바뀌면 올린다 | raw 규격/geometry 버전. 4장이 바뀌면 올린다 |
| `RDDIRB` | **X** | **BOT amp의 물리적 독출 진행 방향** | 〃 |
| `RDDIRT` | **X** | **TOP amp의 물리적 독출 진행 방향.** MEF amp header<br>`READDIR`로 전달 | MEF amp `READDIR` 로 가야 하는데 converter<br>가 하드코딩(C-12). 실기 확인 필요(OI-3) |
| `ROWORDR` | **X** | **4.2절 행 순서 규약. 잘못 쓰면 TOP** **half가**<br>**Y 반전된다** | TOP half 의 행 순서 규약.<br>**잘못 쓰면 TOP half 가 Y**<br>**반전된다.** 실기 확인 필요(OI-3) |
| `TCSDRIVE` | O | 망원경 구동 상태.<br>**converter는 `TCSDRIVE`를 먼저 찾고**<br>**없으면 `TCSDRIV`를 본다.**<br>**`TCSDRIVE`(8자)로 쓸 것** |  |
| `TCSLIMIT` &nbsp;&nbsp; | **X** | — |  |
| `TELID` | **X** | ICS relay의 telescope ID |  |
| `VMEA<n>` | **X** | `MEASURED` |  |
| `VOLT<n>` | **X** | `VOLTNAME` |  |
| `VOLTN` | **X** | — |  |
| `VSET<n>` | **X** | `SETPOINT` |  |
| `VSTA<n>` | **X** | — |  |
| `VUNI<n>` | **X** | — |  |

> 이 53장은 **converter 가 읽지 않으므로 이름을 틀려도 변환이 조용히 지나간다.** 3장 카드와 달리 MEF 에 `UNKNOWN` 조차 남지 않는다 — 어긋남이 드러나는 곳이 없다는 뜻이다. `OSCNPATT` · `ROWORDR` · `RDDIRT` · `RDDIRB` 처럼 **converter 하드코딩과 대조하라고 만든 선언**이 특히 그렇다 (변경점 C-5 · C-13).

## 7. 폐지된 레거시 카드 (17장)

**신규 raw 는 이 카드들을 싣지 않는다.** D-013 이 레거시 123개를 하나씩 판정해 101개는 이미 대응물이 있었고, 대응물이 없던 22개를 **계승 5 · 개칭 1 · 폐지 16** 으로 갈랐다. 여기에 규격 카드 `UT` 하나가 함께 폐지됐다.

> `DETID` 처럼 **레거시 헤더에는 있는데 3장에도 6장에도 없는 카드**를 찾았다면 여기에 있다. 빠뜨린 것이 아니라 **폐지된 것**이다.

| 폐지 카드 | 폐지 근거 | 대신 보는 것 |
| --- | --- | --- |
| `DETID` | 파일 1개 = CCD 1개 전제의 카드. 신규는 파일 1개에 chip 2개다 | `CTRLTAG` · `CHIPS` · `CHIP1` · `CHIP2` (더 정확하다) |
| `OVERSCNY` | ⚠️ **이름을 물려주면 자료가 깎인다.** 레거시는 Y overscan 이 `0`(없음)이었고 있었다면 **가장자리**를 뜻했다. 신규는 Y overscan 이 **영상 중앙**에 있다(4.2절). `OVERSCNY=168`을 본 도구가 "위쪽 168행 자르기"를 하면 active 픽셀을 지운다 | `MIDOVSCY` · `MIDOSCB` · `MIDOSCT` (위치가 이름에 들어 있다) |
| `READOUT` (`'ARLBRL'`) | 8-amp CCD 의 amp 조합 부호. 64-amp 구조를 표현할 수 없다 | `READMODE`(`'64AMP'`) · `READARCH`(`'8STRIPx2END'`) · `OSCNPATT` |
| `GAINDL` | **레거시 4년치에서 값이 비어 있던 카드다**(`GAINDL / comment` 형태). 계승할 관례가 없다 | `ACFFILE` · `TIMCONF` · `TIMVER` 가 timing script 를 가리킨다 |
| `PIXITIME` | 〃 (같은 이유, 같은 자리) | 〃 |
| `DMAWAIT` | master IC 가 slave 의 DMA 설정을 기다리는 시간. Archon 에는 master/slave DMA 가 없다 | `READTIME` · `BUFNO` |
| `ICROLE` | `'MASTER'`/`'SLAVE'`. Archon 과학 컨트롤러 2대는 대등하고, 셔터는 ICS 가 AUX 로 직접 구동한다 | `CTRLID` · `CTRL<n>ID` |
| `CTCSOURC` | CTC(전하전송 보정) 계수의 출처. Archon 은 컨트롤러에서 CTC 를 하지 않는다 | (해당 없음) |
| `CTCFILE` | 〃 | `ACFFILE` 이 그 자리다 |
| `KBUILD` | CCD 별 IC 의 소프트웨어 빌드. CCD 별 IC 가 없어졌다. **다만 "모든 파일이 전체 전자부 상태를 안다"는 취지는 계승했다** — 5.5.0절 `CTRL<n>*` | `CTRL1FW` · `CTRL2FW` |
| `MBUILD` | 〃 | 〃 |
| `TBUILD` | 〃 | 〃 |
| `NBUILD` | 〃 | 〃 |
| `GBUILD` | 〃. guide 는 이 규격 범위 밖이고 `HEMODE` 로 구분한다 | 〃 |
| `RTD12` | **값도 주석도 없는 빈 카드**가 4년치 아카이브에 남아 있었다. RTD 채널 12 자리로 보이나 채워진 적이 없다 | (없음). 5.0절 "결측이면 카드를 넣지 않는다"가 이 사례를 막는다 |
| `INPUTFMT` | *"Format of file from which image was read"*. 프레임이 컨트롤러에서 TCP 로 직접 오므로 "읽어 들인 파일" 이 없다 | (해당 없음) |
| `UT` | **`DATE-OBS` 와 완전한 중복.** 레거시가 둘 다 실은 것은 `UT` 에 `TSHOPEN`(백분초)을 붙여 정밀도를 보태려던 것인데, `DATE-OBS` 를 밀리초까지 쓰기로 하면서 이유가 없어졌다 (2026-08-13 확정) | `DATE-OBS` (밀리초 포함). MEF `UT` 는 converter 가 `DATE-OBS` 날짜부 + `TSHOPEN` 으로 조립하므로 영향 없다 |

> ⚠️ **`OVERSCNY` 가 이 목록에서 가장 위험한 축이다.** 이름을 그대로 물려주면 **자료가 깎인다** — 레거시는 Y overscan 이 가장자리였고 신규는 영상 중앙이라(규격 4.2절), `OVERSCNY=168` 을 본 도구가 "위쪽 168행 자르기" 를 하면 active 픽셀을 지운다. 이름이 같아서 조용히 틀리는 부류다.

계승 5 · 개칭 1 은 폐지되지 않았으므로 3장·6장에 들어 있다 — `DATASRC` `HEMODE` `LEDFLASH` `ICSBUILD` `NPHLINES` 와 `DSTEL` → **`DSTELALT`**.

## 8. 레거시 123개 전량 귀속

레거시 raw 실측본의 keyword 가 **하나도 빠짐없이** 어딘가에 귀속되는지 확인한 표다. 이 문서를 읽다가 *"이 카드는 어디 갔지"* 가 나오면 여기서 찾는다.

| 어디로 갔나 | 개수 | 어느 장 |
| --- | ---: | --- |
| converter 가 읽는다 | **78** | 3장 · 4장 |
| 구조 카드 — `hval()` 로 읽는다 | **5** | 5장 |
| 폐지됐다 | **16** | 7장 |
| 신규 규격에 대응물이 있으나 converter 가 읽지 않는다 | **24** | 6장 · 아래 |
| **합계** | **123** | |

마지막 24개는 이렇다 — 계승 5(`DATASRC` `HEMODE` `LEDFLASH` `ICSBUILD` `NPHLINES`) · 개칭 1(`DSTEL`→`DSTELALT`) · 나머지는 신규 규격이 **다른 이름이나 더 정확한 카드로 대체**했거나 converter 가 자기 상수를 쓰는 것들이다:

| `SIMPLE` · `NAXIS` · `NAMPS` · `OVERSCNX` · `PRESCANX` · `PIXSCALE` · `PIXSIZE` · `NPHLINES` · `DATASRC` · `HEMODE` · `LEDFLASH` · `FILENAME` · `ICSBUILD` · `DSTEL` · `CHOP` · `CHSET` · `CHPROC` · `ENS1` · `ENS2` · `ENS3` · `ENS4` · `ENS5` · `ENS6` · `ENS7` |
| --- |

## 9. 종합

- **기본값이 거의 전부 `""` 나 `"UNKNOWN"` 이다.** 카드가 없어도 변환은 성공하고, **L0 MEF 에 빈 문자열이 조용히 들어간다.**
- **오류로 걸리는 것은 `OBSERVAT` 하나**(파일명 교차 검증)다. 나머지는 전부 조용히 지나간다.
- 조용히 **틀린 값**이 들어가는 쪽이 더 위험하다 — `DATE-OBS`(변환 시각) · `RA`/`DEC`(그럴듯한 좌표) · `EXPTIME`/`DARKTIME`(0초) · 버전 문자열(그럴듯한 provenance).
- `X` 26개 중 **`XTALKVER` · `REFVER` · `CATVER` 셋은 결함이 아니다** — 규격 5.12 가 calibration DB 소관으로 정리했고 변경점 C-14 가 caldb 주입으로 바꾼다.
- **6장 53장은 어긋나도 드러나지 않는다** — converter 가 읽지 않으므로 MEF 에 흔적이 남지 않는다.
- **폐지 카드를 이름만 보고 되살리면 안 된다** — `OVERSCNY` 가 그 예다 (7장).
- 그룹별 주의사항은 **각 표 아래**에 붙였다.

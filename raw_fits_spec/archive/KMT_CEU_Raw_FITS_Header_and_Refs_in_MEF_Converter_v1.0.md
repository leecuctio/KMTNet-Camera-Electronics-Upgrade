# converter 가 raw FITS 헤더에서 읽는 keyword

생성 2026-08-18 · **소스에서 기계 추출했다** — 손으로 옮겨 적은 표가 아니다.

| 항목 | 값 |
| --- | --- |
| 대상 converter | `../../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) |
| 추출 방법 | `card("<MEF>", v("<raw>", <기본값>), …)` 호출을 정규식으로 파싱 |
| 레거시 대조본 | `Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt` (keyword 123개) |
| 관련 검토 문서 | `../KMT_CEU_Raw_to_MEF_Keyword_Map_v0.7_REVIEW.md` (ACT-011) |

## 1. 요약

| | 개수 |
| --- | ---: |
| `card()` 로 곧바로 들어가는 keyword | **102** |
| `card()` 밖에서 쓰이는 keyword (`DATE-OBS` · `TCSDRIV`) | **2** |
| **converter 가 raw 에서 읽는 keyword 총계** | **104** |

레거시 raw 실측본 대비 (총계 104개 기준):

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

`TSHOPEN` 은 MEF `UT` 조립에도 쓰인다. converter 가 `DATE-OBS` 의 날짜부에 raw `TSHOPEN` 을 붙여 만들기 때문에(`v2_1.py:440` · `:583`), **raw 의 `UT` 카드를 폐지해도 MEF `UT` 는 영향을 받지 않는다** (규격 5.13).

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

**`CTRL1*` · `CTRL2*` 가 색인형인 이유**: converter 가 **MK 헤더만** 읽으면서(`convert()` 가 두 chip 에 `mk_hdr` 하나만 넘긴다) 컨트롤러 두 대분 정체를 요구한다. 단수형으로 두면 MEF 가 전부 `UNKNOWN` 을 받는다. 레거시도 raw 파일마다 `KBUILD`/`MBUILD`/`TBUILD`/`NBUILD` 를 다 실어 같은 구조였다.

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

## 6. 종합

- **기본값이 거의 전부 `""` 나 `"UNKNOWN"` 이다.** 카드가 없어도 변환은 성공하고, **L0 MEF 에 빈 문자열이 조용히 들어간다.**
- **오류로 걸리는 것은 `OBSERVAT` 하나**(파일명 교차 검증)다. 나머지는 전부 조용히 지나간다.
- 조용히 **틀린 값**이 들어가는 쪽이 더 위험하다 — `DATE-OBS`(변환 시각) · `RA`/`DEC`(그럴듯한 좌표) · `EXPTIME`/`DARKTIME`(0초) · 버전 문자열(그럴듯한 provenance).
- `X` 26개 중 **`XTALKVER` · `REFVER` · `CATVER` 셋은 결함이 아니다** — 규격 5.12 가 calibration DB 소관으로 정리했고 변경점 C-14 가 caldb 주입으로 바꾼다.
- 그룹별 주의사항은 **각 표 아래**에 붙였다.

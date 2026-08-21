# Raw FITS 헤더 개정에 따른 MEF ICD · MEF Converter 개정 및 검토 사항

**v0.5 (Draft)** · 2026-08-22 · **Part 1** = 헤더 카드 개정이 MEF 쪽 3자(ICD v4.1 · MEF keyword 정의서 v1.0 · converter v2.2.0)에 요구하는 개정 목록 · **Part 2** = raw 파일 번호 · 정체성 · 충돌 처리 재설계와 그 MEF 파급

> **v0.5 에서 바뀐 것 — 두 문서를 하나로 합쳤다 (운영자 지시 2026-08-22).**
>
> 1. **통합**: `KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.4.md`(→ Part 1)와 `KMT_CEU_Raw_Numbering_and_Identity_v0.2.md`(→ Part 2)를 이 문서로 합쳤다. 두 전신은 `archive/` 로 옮긴다. Part 를 가른 이유: **Part 1 은 LEECU 가 실행할 항목**이고 **Part 2 는 raw 쪽 규격 결정(+일부 MEF 파급)** 이라 주인이 다르다.
> 2. **키워드맵 잔여 안건 이관**: `KMT_CEU_Raw_to_MEF_Keyword_Map_v0.7_REVIEW.md` 5장에만 남아 있던 미결 4건(`NCTRL` 정의 · `CTRLID` 개칭 · `SATURAT`/`SATLEVEL` 통일 · `DATASRC`/설정 포인터의 MEF 목적지)을 Part 1 §6 으로 옮겼다 — 이로써 키워드맵의 살아있는 내용은 전부 이 문서와 Header_and_Refs 로 흡수됐다.
> 3. **Header_and_Refs v1.11 반영**: 돔 Source 변경(`AUX relay` → `TCS relay or REDIS`, `DALTERR`/`DAZERR` = `ICS calculation`) · `LEDFLASH` 단위 변경([seconds] → [milliseconds] 정수) · `ICSBUILD` 형식 변경(프로그램명 제거) — 셋 다 converter 동작에는 영향이 없어 **기록 행**으로 남겼다(§1 끝).

> **v0.4 에서 바뀐 것 — 운영자 3차 개정(Header_and_Refs v1.9) 반영**: ① **`READMODE` 값 충돌 종결** — raw 쪽은 **`RDMODE` 로 개명 도입**(독출 속도 모드 선언), MEF `READMODE`(`'64AMP'`)는 그대로. ② **raw 신설 카드 `CAMVER` · `RDMODE` · `C1_`/`C2_` 계열** — converter 미독, 도입 시 pass-through 후보로 §2 대응표에 추가. ③ **C-후보 신설** — MEF `VOLTINFO`/`TELEMETRY` 를 raw `Cn_VOLT`·`Cn_CURR`·`Cn_TEMP` 에서 채우는 안. ④ **raw 미도입 확정 반영** — `CTRLTAG`·`PAIRFILE`·`OSCNPATT`·`RDDIRT`/`RDDIRB`·`MIDOSC*`·전압 색인 계열: C-5/C-12 문구를 "규격 조항 + 표본 검증" 기반으로 조정.
>
> **v0.3**: HK 재구성 확정(`WALLBOAR`→`WALLBRD`, 출처 3계통) · C-신설 2건(MEF `UT` 조립 원천 · `DARKTIME` 공급원). **v0.2**: `OBSERVAT` 값 재정의 C-항목(이후 철회로 종결). **Part 2 의 전신 이력** — v0.2: `CTRLTAG`·`PAIRFILE` 미도입 확정 반영(삼총사 문구에서 `CTRLTAG` 제거) · v0.1: 충돌 번호 증가 설계 최초 기록.

> `mef_converter/` 는 읽기 전용(LEECU 소관)이므로 Part 1 은 **변경 요청 목록**이지 변경 자체가 아니다. raw 쪽 근거는 `KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.12.md`(확인 요망 11건 전량 종결)와 Part 2(**D-016 등재 완료**), 검토 세션 기록([`SMC_CLAUDE.md`](SMC_CLAUDE.md))이다. 규격 재작성판(V1) 발행 시 이 문서도 판을 올린다.

---

# Part 1 — 헤더 카드 개정에 따른 MEF ICD · 정의서 · Converter 개정 사항

## 1. Converter 변경점(C-*) 신설 · 개정

| 항목 | 내용 | 판단 요청 |
| --- | --- | --- |
| **C-신설: MEF `UNIQNAME` 공급원** | raw `UNIQNAME` 폐지 후 `v2_1.py:405`의 `v("UNIQNAME","")`가 **항상 빈 문자열**을 반환한다(오류 없음) | 대안 (a) raw `FILENAME` 카드에서 채움 (b) 디스크 파일명(`mk_path`)에서 파생 — 이미 AMPINFO `RAWFILE`이 같은 원천을 씀 (c) MEF `UNIQNAME` 자체를 폐지 — MEF `FILENAME` · `RAWFILE`로 충분. **raw 쪽 권고: (c) 검토, 최소 (b)** |
| ~~`OBSERVAT` 관련~~ (v0.2 등재 → **종결**) | 사이트 코드 재정의안이 **철회**되고 `OBSERVAT` 는 현행 체계 그대로 `TESTBED`/`CTIO`/`SAAO`/`SSO` 로 확정됐다(운영자, 2026-08-21) | **개정 항목 없음** — converter 교차검증·ICD 2.1·`rawpair.py` 와 완전 정합 |
| **C-신설(경미): MEF `ORIGIN` 을 상수로** | `ORIGIN` 개념이 **"이 파일이 생성된 곳"** 으로 확정됐다: 관측소 raw = 관측소 이름 · 테스트베드 raw = `KASI` · **KASI 파이프라인 산출물 = `KASI`**. 현행 converter 는 raw `ORIGIN` 을 MEF 로 복사한다(`v2_1.py:341`, `v("ORIGIN","KASI")`) — MEF 는 파이프라인 산출물이므로 개념과 어긋난다 | MEF PRIMARY 의 `ORIGIN` 을 복사 대신 **상수 `'KASI'`** 로 기록. 한 줄 수정, 긴급도 낮음(관측소 raw 를 KASI 서버에서 변환하는 현행 흐름에서만 차이 발생) |
| C-신설(선택): `ORIGNAME` pass-through | 충돌 신호(`FILENAME ≠ ORIGNAME`)는 raw에만 있다. MEF 층 충돌 필터가 필요할 때만 추가 | raw 헤더 층 필터가 기본이므로 필수 아님 |
| **C-11 개정** | amp `MODULE`/`CHANNEL` 공급원: 구 규격의 `AMOD<nn>`/`ACHN<nn>` 색인형 65장 → **`CHMAP_LT`/`CHMAP_LB`/`CHMAP_RT`/`CHMAP_RB` 4장**으로 재설계됐다. 현행 추정식(`MODULE=1+((amp-1)//8)`, `CHANNEL=1+((amp-1)%8)`, 'placeholder' 주석)은 실배선(CCD 출력 채널이 chip당 1–16, TOP/BOT 대역이 chip마다 반대)과 다르다 | `XTALKGROUP` 파생도 이 값 기준으로 재정의. `AMPMAP` 선언 카드는 폐지 방향 |
| C-5 · C-13 개정 | "raw geometry 선언 카드 대조" → **포장 규범 조항 + 표본 검증** 체계로 재조정 — `OSCNPATT` 는 raw **미도입 확정**(v1.9), `ROWORDR` 와 함께 규격 조항으로 이관. 대조표에 2장의 이름 대응을 명시 | |
| C-12 | amp `READDIR` 공급원 후보였던 `RDDIRT`/`RDDIRB` 는 raw **미도입 확정**(v1.9) — 대조 근거를 카드가 아니라 **규격 조항 + 표본 검증**으로 갱신. OI-3(실기 확인) 유지 | |
| **C-신설: HK 온도 카드 재구성** (2026-08-21) | 온도센서 구성 변경으로 raw 의 Camera System House Keeping 블록이 재편됐다 — **신설 `DMPTEMP`(DMP 온도) · `WALLBRD`(wallboard 온도 — v0.2 의 `WALLBOAR` 에서 개명) · `HEBOX`(HE box 내부 온도)**, `AIR_IN`/`AIR_OUT`/`GLYC_IN`/`GLYC_OUT` comment 정의 확정(AIR는 열교환기 기준 — IN이 따뜻한 쪽, 레거시 의미 유지), `DEWPRES` 단위 [torr] · 포맷 `x.xxe-x` · **측정불가 sentinel `9.99e-9`**(값 0/이상값/게이지 비숫자 — 규격 5.0 sentinel 표에 DEWPRES 전용 예외로 등재 필요), **`CCDTEMP` 의미 변경**: 구 설계(`CCDTEMP1`·`CCDTEMP2` 평균 파생, D-013)에서 **실측 센서 1개 값**("CCD temperature M")으로. `RTD12` 폐지는 확정대로(D-013). **출처 확정(v0.3)** — `CCDTEMP`·`DEWPRES`·`PT30N*`·`CHARCOAL`·`DMPTEMP`·`WALLBRD` = ICG RTD measurement / `AIR_*`·`GLYC_*` = standalone RTD readout unit / `HEBOX` = Tapaculo sensor | ① converter 가 `DMPTEMP`/`WALLBRD`/`HEBOX` 를 읽지 않음 — MEF 로 보내려면 읽기 추가 ② MEF/L1 의 `CCDTEMP` 정의를 "평균 파생"에서 "대표 센서 실측"으로 갱신 (L1 `CARRY_KEYS` 가 `CCDTEMP` 이름을 요구하므로 이름은 불변) ③ `CCDTEMP1`/`CCDTEMP2` 후보는 **제외 확정**(운영자, 2026-08-21) — 평균 파생 설계 폐기에 따름 |
| **C-신설: MEF `UT` 조립 원천** (2026-08-21) | raw 가 `TSHOPEN`/`TSHSHUT` 를 싣지 않는 것으로 판정됐다(Header_and_Refs v1.9 3.2절). converter 는 `DATE-OBS` 날짜부 + raw `TSHOPEN` 으로 MEF `UT` 를 조립하므로(`v2_1.py:440` · `:583`) **MEF `UT` 시각부가 빈다** — 오류 없음 | `UT` 조립 원천을 `DATE-OBS` 의 시각부로 교체 (`DATE-OBS` 는 밀리초까지 담는다, D-014) |
| C-신설(경미): MEF `DARKTIME` 공급원 | raw `DARKTIME` 미기재 판정 — 값이 `EXPTIME` 과 동일해 파생으로 충분(v1.9 3.2절). 현행 converter 기본값 `0.0` 이 MEF 에 박힌다 | `EXPTIME` 값으로 파생 기록, 또는 MEF `DARKTIME` 폐지 판단 |
| **C-후보 신설: MEF `VOLTINFO`/`TELEMETRY` 공급원** (2026-08-22) | raw 가 컨트롤러별 텔레메트리 카드 **`C1_TEMP`·`C1_VOLT`·`C1_CURR` / `C2_*`** 를 도입했다(v1.9, 구 `BCKTEMP` 확장) — MEF `VOLTINFO`/`TELEMETRY` 를 실측값으로 채울 원천이 처음 생겼다. converter 는 이 카드들을 아직 읽지 않는다 | 현행 placeholder 경로(C-18)를 raw `Cn_*` 기반 채움으로 **대체**하는 안 — 도입 시 읽기 추가 + 조립 규칙(모듈 순서 명세는 raw 규격 수록 예정) 정의 |
| (기록) `DATASRC` 값 체계 확장 · chiller 블록 미기재 | `ARCHON`/`SIM` → **`ARCHON_SCIENCE`/`ARCHON_GUIDE`/`SIM`**(`HEMODE` 흡수) · chiller 4장(`CHSTAT` `CHOP` `CHSET` `CHPROC`)은 raw 미기재 **확정**(운영자가 초안에서 삭제, 2026-08-21 · 재삭제 검증 2026-08-22) | converter 는 `DATASRC`/`CHOP`/`CHSET`/`CHPROC` 를 읽지 않고 `CHSTAT` 는 기본값 `""` 경로 — 영향 없음/경미, 기록만 |
| (기록, v0.5) 돔 Source 변경 · `LEDFLASH` 단위 변경 · `ICSBUILD` 형식 변경 | ① 돔 카드(`DSSTAT`~`DSTELAZ`)의 공급원이 `AUX relay` → **`TCS relay or REDIS`**(newTCS 편입), `DALTERR`/`DAZERR` 는 **`ICS calculation`** — 값 공급 계통의 변경이지 카드 이름·형식 변경이 아니다 ② `LEDFLASH` 단위 [seconds] → **[milliseconds] 정수**(운영자 확정 2026-08-22 — 카드 comment 가 단위 명시) ③ `ICSBUILD` 형식 `<프로그램>-v<버전>:<빌드일시>` → **`v<버전>:<빌드일시>Z`**(프로그램 식별은 `DATASRC` 담당) | 셋 다 converter 미독 카드(`LEDFLASH` `ICSBUILD`) 또는 pass-through 값이라 **converter 동작 불변 — 기록만**. 단 하류 도구가 `LEDFLASH` 를 초로 읽지 않게 ICD/정의서 부속 문서에 단위 변경을 전파할 것 |

## 2. raw ↔ MEF 키워드 이름 대응 (raw 개명 · 신설분)

raw 쪽 Detector/Amplifier 블록 확정(2026-08-21)으로 이름이 갈라진 것들이다. converter는 이 카드들을 읽지 않으므로 당장 동작은 안 바뀌지만, **C-5 대조를 붙일 때 이 대응이 없으면 어긋남을 잡을 수 없다.**

| raw (신) | MEF / converter 쪽 | 비고 |
| --- | --- | --- |
| `AMPNAX1` = 1200 | `RAWXTILE` | 값 동일, 이름 상이 |
| `AMPNAX2` = 4700 | (없음) | NAXIS2/NEND 타일 규약 값 |
| `IMAGEX` = 1152 | `AMPDATA` | |
| `IMAGEY` = 4616 | (카드 없음 — 상수 `ACTIVE_HALF_ROWS`, amp extension NAXIS2) | |
| `PRESCNX` = 0 | `PRESCANX` | 레거시 실측 27과 분리하려고 raw 쪽을 개명 — ⚠️ 삼자 모순 재확정 대기(Header_and_Refs 확인 요망 10) |
| `PRESCNY` = 0 | (없음) | |
| `OVRSCNX` = 48 | `OVERSCNX` | 레거시 실측 32와 분리하려고 raw 쪽을 개명 |
| `OVRSCNY` = 84 | (없음 — `MIDOVSCY`=168=2×84 관계, 분배는 OI-4) | |
| `NAMPDET` = 16 | `AMPPCD`(정의서) | raw는 `NAMPS` · `AMPPCD` 폐지 (Header_and_Refs v1.6 8.1절) |
| `NAMPRAW` = 32 | (없음 — raw 파일 단위 개념) | |
| `CHMAP_LT/LB/RT/RB` | AMPINFO `MODULE` · `CHANNEL` (C-11) | 값 = CCD 출력 채널, 자릿수 고정 3자 토큰 8개 |
| `DETID` = 'MK'/'NT' | ((TBD)) | MEF 목적지 미정 — 레거시 계승, 값 재정의(pair) |
| `FILENAME` | MEF `FILENAME`(자체 생성) · AMPINFO `RAWFILE` | converter는 raw `FILENAME` **카드**를 읽지 않음(디스크명만 사용) |
| `ORIGNAME` | (없음 — 선택 pass-through, §1) | |
| `UNIQNAME` (폐지) | MEF `UNIQNAME` | §1 C-신설 참조 |
| `DMPTEMP` (신설) | (없음 — 도입 시 pass-through 추가) | HK 재구성, §1 참조 |
| `WALLBRD` (신설) | (없음 — 도입 시 pass-through 추가) | 〃 |
| `HEBOX` (신설) | (없음 — 도입 시 pass-through 추가) | 〃 |
| `CCDTEMP` (의미 변경) | MEF `CCDTEMP` (L1 `CARRY_KEYS`) | 평균 파생 → 대표 센서 실측, §1 참조 |
| `TCSTIME` (신설) | (없음) | TCS 시각계 선언 — `TIMESYS`(ICS)와 분리 |
| `CTRL1CFG` / `CTRL2CFG` (신설) | (없음 — raw 전용 설정 포인터) | 버전 문자열 6장을 귀속 (v1.9 3.3절). MEF 목적지 검토는 §6-4 |
| `CAMVER` (신설, v1.9) | (없음 — 도입 시 pass-through 후보) | 카메라 시스템 버전 선언. converter 미독 |
| `RDMODE` (신설, v1.9) | MEF `READMODE`(`'64AMP'`) 와 **별개 — 대응 없음** | raw 독출 속도 모드 선언. 구 `READMODE` 이름 충돌의 해소형(§3 참조). converter 미독 |
| `C1_TEMP`·`C1_VOLT`·`C1_CURR` / `C2_*` (신설, v1.9) | MEF `VOLTINFO`/`TELEMETRY` (C-후보, §1) | 컨트롤러별 텔레메트리(구 `BCKTEMP` 확장). converter 미독 — 도입 시 pass-through 후보 |

## 3. ICD v4.1 개정 후보

- **`OVERSCNY` 이름 위험의 문서화 (v1.10 지시)**: 레거시 `OVERSCNY` 는 가장자리 Y overscan(값 0), 신규는 **영상 중앙**(168행) — 이름을 물려주면 "위쪽 N행 자르기" 도구가 active 픽셀을 지운다. raw 는 **`OVRSCNY`**(amp 당 84, frame-center side)로 개명해 잘림을 방지했다. **ICD/정의서에 이 위험 사유와 개명 사실을 기록**해 하류 도구 작성자가 레거시 이름을 재사용하지 않게 할 것 (MEF 는 `MIDOVSCY` 계열 유지).
- **§12 (open items)**: raw 텔레메트리 집합의 위임 대상이 구 규격 5장 → 재작성판으로 바뀐다. 참조 갱신.
- ~~**`READMODE` 값 충돌**: ICD/정의서는 `READMODE='64AMP'`(구조 선언), raw 초안은 `'FAST'`(독출 속도 모드)로 쓰려 했다 — 같은 이름, 다른 뜻. 이름 분리 필요~~ → **해소(v1.9)**: raw 쪽이 **`RDMODE`** 로 개명 도입되어 이름이 갈라졌다 — MEF `READMODE='64AMP'` 는 그대로, **ICD 개정 항목 없음**.
- **AMPINFO의 상류 공급원 명시**: "authoritative 64-row map"의 배선 열(MODULE/CHANNEL)이 converter 추정식이 아니라 **raw `CHMAP_*` + 재작성판의 amp 전수 표**에서 온다는 것을 명시.
- **overscan 좌우 패턴 검증**: 레거시 MEF `AMPSEC` 실측이 M/T=5:3, K/N=3:5 방향 패턴을 보였는데 신규는 4:4(`RRRRLLLL`)를 전제한다 — 같은 e2v CCD290-99이므로 한쪽이 틀렸다. 검증 표본(`KMTN.20260116.000001`) overscan 열 통계로 확정하고, geometry 가 바뀌면 **raw 쪽은 `CAMVER`(HW)/`CTRLxCFG`(설정) 범프 · MEF 쪽은 `GEOMVER` 동반 범프** — `RAWVER` 는 미도입 확정이다(Header_and_Refs v1.12 확인 요망 11: 규격/구성 버전은 `CAMVER`·`CTRLxCFG`·`DETID`·`CHMAP_*` 조합으로 파악).
- 파일명 체계(D-011)는 **불변** — 충돌 번호 증가 시에도 형식은 같고 번호만 다르다. `find_pair()` · 정규식 영향 없음.

## 4. MEF Keywords 정의서 v1.0 개정 후보

- **`XTALKVER` · `REFVER` · `CATVER` 의 계층 규칙 (운영자 확정 2026-08-22)**: 이 셋의 정본은 **pipeline calibration DB** 다(C-14) — HW·성능 변화 없이도 pipeline setup 에서 바뀔 수 있는 값이라 raw 는 싣지 않는다. **전처리 전 MEF(L0)에 넣을지는 pipeline 팀 판단**이고, **전처리 후 산출물(L1)에는 필수**다 — 보정에 실제 적용한 버전이므로. 정의서/ICD 에 이 계층을 명시할 것.
- `UNIQNAME` 항목: 공급원 변경 또는 폐지(§1 C-신설과 연동).
- `NAMPS`=64 · `AMPPCD`=16: raw 쪽 폐지(v1.6 8.1)와의 관계 명시 — MEF 유지 여부는 LEECU 판단(MEF는 카메라 전체 관점이라 유지가 자연스러울 수 있음).
- (기록) 레거시 MEF의 `AMPNAME2`('im16')가 배선 identity를 헤더에 실은 선례 — `CHMAP_*` 채택의 계보.

## 5. 미결(OI-*)과의 연동

| OI | 이 검토와의 접점 |
| --- | --- |
| OI-3 (`ROWORDR`/`RDDIR*`) | 포장 규범 조항 이관 후 flat/star 시험은 "사실 확인"이 아니라 **준수 검증**이 된다 |
| OI-4 (중앙 168행 분배) | raw `OVRSCNY`=84는 타일 규약 값이다. 물리 분배는 실측 후 `MIDOSCT`/`MIDOSCB`로 |
| OI-9 (배선 실측) | `CHMAP_*` 값의 실측 확정 + Archon module/channel 층(`XTALKCAL=True` 전제). CCD 출력 채널 라벨과 Archon tap의 대응은 STA 문서/Tom O'Brien 협의 |
| (신규 제안) | **X overscan 패턴 4:4 vs 5:3 검증** — 검증 표본 overscan 열 통계로 flat 없이 즉시 가능. OI로 등재 요청 |

## 6. 키워드맵 v0.7 에서 이관한 미결 안건 (v0.5 신설)

`KMT_CEU_Raw_to_MEF_Keyword_Map_v0.7_REVIEW.md` 5장(팀원 간 검토 요청)의 항목 중 Header_and_Refs 사이클이 흡수하지 않은 **MEF/converter 쪽 안건 4건**이다. 이 이관으로 키워드맵의 살아있는 내용은 전부 흡수됐고, 키워드맵은 `archive/` 로 이동했다(운영자 재가 2026-08-22).

1. **`NCTRL` 정의** — converter 가 `2` 를 하드코딩한다(`v2_1.py:410`). **과학 2대만 센 값**인데 Archon 은 3대(과학 2 + 가이드 1)다. `NCTRL` 이 "과학" 인지 "전체" 인지 ICD 침묵 구간이라 정의가 필요하다.
2. **`CTRLID` 개칭 검토** — MEF amp `CTRLID`/`TELEMETRY.CTRLID` 는 색인 정수(`1`/`2`)인데 raw/MEF PRIMARY 의 `CTRL1ID`(식별자 **문자열** `'KMTA-SCI-101'`)와 이름이 너무 닮았다. `CTRLIDX` 등 개칭 검토.
3. **`SATURAT` ↔ `SATLEVEL` 통일** — converter **내부에서** 이름이 갈린다: amp 헤더는 `SATURAT`, `AMPINFO` 컬럼은 `SATLEVEL`. 어느 쪽으로 통일할지.
4. **`DATASRC` · 설정 포인터의 MEF 목적지** — ① `DATASRC` 는 **시뮬 프레임이 실측으로 오인되는 것을 막는 유일한 카드**인데 L0 MEF 에 자리가 없다 — pass-through 신설 여부. ② 설정 provenance 포인터는 구 `ACFFILE` 이 폐지되고 **`CTRL1CFG`/`CTRL2CFG`** 로 대체됐는데(v1.9) 역시 MEF 목적지가 없다 — MEF 에도 자리를 만들지.

> 키워드맵의 나머지(카드 전수 대응표 · 준수 우선순위 · MEF 인벤토리 236장 분석)는 **배경 자료**로서 archive 의 v0.7 원본을 참조한다 — 재작성판 V1 의 amp 전수 표·기계 사본 작성 시 원자료가 된다.

---

# Part 2 — raw 파일 번호 · 정체성 · 충돌 처리 (재작성판 Pair Spec 흡수 예정분)

> **지위**: 2026-08-20~21 raw 헤더 검토(ACT-011)에서 확정한 설계의 기록이다. 구 규격 `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`(⛔ 재작성중)의 **2.3.1절(이름 충돌 격리)과 5.2절 일부(`UNIQNAME` · `NAMECLSH`)를 대체**한다. **✅ DECISION_LOG 에 `D-016` 으로 등재 완료(운영자 승인, 2026-08-22)** — 확정된 근거는 `../project_management/governance/DECISION_LOG.md` 의 D-016 이고, §8 은 그 등재 원문이다. **재작성판 V1 이 이 내용을 2.3/5.2절로 흡수하면 Part 2 는 파급 요약과 포인터로 줄인다.**

## 1. 파일 번호 공간과 카운터

- `<NNNNNN>`은 6자리 zero-padding(D-011, 불변)이며 유효값은 **000000–099999** 십만 개다(레거시 관례 계승).
- 카운터는 099999 다음(100000 도달 시) **000000으로 초기화**한다.
- 파일명 형식 · `<SITE>` · 관측일 날짜부 규칙은 D-011 · D-014 그대로다. 충돌 처리(§2)는 번호만 바꾸고 형식은 바꾸지 않는다.

## 2. 파일명 충돌 처리 — 번호 증가 (구 2.3.1 `clash/` 격리 대체)

1. 카운터가 후보 번호 N을 제안한다.
2. **쓰기 전에** 후보 N의 MK · NT **두 경로를 모두 존재 검사**한다. 하나라도 점유되어 있으면 N+1로 재검사한다. 099999를 넘으면 000000으로 되감는다.
3. +1 증가가 **100000회를 초과하면 멈추고 ERROR 메시지를 출력하며 저장하지 않는다.** 상한 100000회 = 번호 공간 정확히 한 바퀴 — 초과는 공간 전체 점유 또는 근본 고장을 뜻하므로 조용한 우회는 없다.
4. 둘 다 빈 N을 확정하고 **카운터를 N으로 동기화**한다. 평소 노출 번호 영속화 경로를 그대로 쓰고, 옛값→새값 점프는 경고 로그로 남긴다.
5. MK · NT를 쓴다. 증가가 있었으면 `FILENAME ≠ ORIGNAME`으로 사건이 헤더에 남는다(§3).

- **전제**: 이 저장 디렉토리에 쓰는 주체는 ICS 하나뿐이다 — 선검사와 쓰기 사이의 경쟁은 없다.
- **효과**: 무인 운영에서 방금 취득한 데이터가 격리되지 않고 밤이 계속된다. 카운터 되감김(재시작 등)이 원인이면 충돌 1회로 원인 전체가 자가 치유된다 — 선검사 루프가 점유 구간을 지나 빈 번호에 착지하고 카운터가 따라간다.
- **폐지**: `clash/` 격리 디렉토리, `.clash<UTC>` 접미사.

## 3. 정체성 카드 — `FILENAME` · `ORIGNAME`

```text
FILENAME= 'KMTA.20260821.012345.MK' / Filename assigned by ICS
ORIGNAME= 'KMTA.20260821.012340.MK' / Original filename assigned by ICS counter
```

- 두 카드는 **모든 raw 파일에 항상** 기록한다. 값은 확장자 없는 실명 형식이며 FITS **문자열 카드 필수**다(zero-padding 보존 — 숫자 카드로 쓰면 앞자리 0이 부서진다).
- `FILENAME` = 실제 저장명. **아카이브 · DTS · 색인의 유일 키**다(유일성은 §2의 증가 방식이 구조로 보장한다).
- `ORIGNAME` = 카운터가 이 노출에 **처음 배정한 이름**. 연쇄 증가의 중간값이 아니라 최초 제안 하나만 기록한다.
- **충돌 신호 = `FILENAME ≠ ORIGNAME`** (값 비교). 카드의 존재 여부가 아니다. 평시에는 두 값이 같다.
- `ORIGNAME` 결측은 충돌이 아니라 **헤더 결함**(규격 이전 작성기)으로 분류한다 — 빈 값과의 비교로 가짜 신호를 만들지 않는다.
- pair 규칙: 두 카드 모두 pair 간 서로 다르다(`.MK`/`.NT` 꼬리). 충돌 증가 시 두 파일이 **함께** 같은 번호로 증가하므로, 각 파일 안의 (FILENAME, ORIGNAME) 불일치 여부는 pair 양쪽에서 동일하다.
- `PAIRFILE` 카드는 **v1.9 에서 미도입 확정** — 짝 이름은 `FILENAME` 에서 `.MK` ↔ `.NT` 치환으로 규약상 유도된다(충돌 증가가 pair 동시이므로 항상 성립). 구 v1.2 의 "PAIRFILE은 명목 이름으로 열화될 수 있다" 조항은 카드와 함께 폐지된다.

## 4. 폐지 항목

| 폐지 | 사유 | 대신 보는 것 |
| --- | --- | --- |
| `UNIQNAME` | "불변 정본 키"라는 뜻이 이탈했다 — 유일성은 증가 방식이 `FILENAME`에 구조로 보장한다. 뜻이 바뀐 이름은 계승하지 않는다(D-013 원칙) | `FILENAME`(유일 키) + `ORIGNAME`(사건 기록) |
| `NAMECLSH` | 신호가 카드 존재에서 값 비교로 이동했다 | `FILENAME ≠ ORIGNAME` |
| `clash/` · `.clash` 접미사 | 격리 방식 자체가 번호 증가로 대체됐다 | §2 |

- ics_sim의 RETIRED(부활 금지) 목록에 `UNIQNAME` · `NAMECLSH`를 추가한다.
- D-010 · D-012의 "아카이브 근거 삼총사 `UNIQNAME`/`FILENAME`/`CTRLTAG`" 문구는 **`FILENAME`(+`ORIGNAME`)**로 개정한다 — raw 카드 `CTRLTAG` 는 v1.9 에서 **미도입 확정**이고, pair 쪽 식별은 `FILENAME` 꼬리(`.MK`/`.NT`)가 담당한다.

## 5. 하류 도구 요구사항

- 충돌 필터는 **raw 헤더 층**(아카이브 색인 · DTS · QL)에서 `FILENAME ≠ ORIGNAME`으로 돈다.
- 아카이브 근거는 **`FILENAME`(+`ORIGNAME`)** 이다. pair 쪽 식별(짝 파일 찾기)은 `FILENAME` 꼬리 `.MK` ↔ `.NT` 치환으로 한다 — `PAIRFILE` · `CTRLTAG` 카드는 raw 에 없다(v1.9 미도입 확정).
- 같은 노출의 재저장(유령 중복)은 fail-open이다 — 위 필터가 걸러낸다는 전제를 **요구사항**으로 둔다.
- MEF 층 필터가 필요해지면 converter 변경점에 `ORIGNAME` pass-through를 추가한다(→ Part 1 §1).
- OBSAgent `Wrote` 논리 이름의 번호는 **실제 저장 번호**를 쓴다(D-010 형식 불변).

## 6. MEF / converter 연동

converter(v2.2.0)는 raw `UNIQNAME`을 읽어 MEF `UNIQNAME`으로 옮긴다(`v2_1.py:405`). `UNIQNAME` 폐지 후 이 값은 **오류 없이 빈 문자열**이 된다 — 대응은 C-항목으로 LEECU에 이관한다. 상세: Part 1 §1.

## 7. ics_sim 구현 영향

| 파일 | 변경 |
| --- | --- |
| `rawpair.py` | 선검사 루프(되감음 · 상한 100000회) 신설, clash 격리 로직 제거, `UNIQNAME` 제거, `ORIGNAME` 항상 기록 |
| `state.py` | 확정 N으로 카운터 동기화, 000000–099999 순환 |
| `sequencer._store()` | 확정된 이름만 수령(이름 결정은 rawpair 몫) |
| `tests/test_raw_header.py` | `UNIQNAME` 필수 목록에서 제거하고 RETIRED에 추가, `NAMECLSH` 시험 교체, 평시 `FILENAME`==`ORIGNAME` 불변식, 충돌 시나리오 · 되감음 · 상한 시험 신설 |

## 8. 결정문 (DECISION_LOG **D-016 등재 완료**, 2026-08-22)

> **D-016: raw 파일명 충돌 시 노출 번호를 증가시켜 저장한다 (`UNIQNAME` 폐지)** / 날짜: 2026-08-21 (운영자 등재 승인 2026-08-22) / 관련: D-010 · D-011 · D-012(일부 대체) · D-013 · D-014 / 상태: **Accepted** — 정본은 `../project_management/governance/DECISION_LOG.md`
>
> **결정**: (1) 파일 번호 공간은 000000–099999이며 카운터는 100000 도달 시 000000으로 초기화한다(레거시 관례). (2) 쓰기 전 후보 N의 MK · NT 두 경로를 선검사하고, 점유 시 N+1(099999 넘으면 000000)로 재검사한다. +1이 100000회를 초과하면 멈추고 ERROR를 출력하며 저장하지 않는다. (3) 확정 N으로 카운터를 동기화한다. (4) `UNIQNAME`을 폐지한다. `FILENAME` = 실제 저장명이자 아카이브 유일 키, `ORIGNAME` = 카운터가 처음 배정한 이름이며 두 카드를 모든 파일에 항상 기록한다 — `FILENAME ≠ ORIGNAME`이 충돌 신호다. 아카이브 근거는 **`FILENAME`(+`ORIGNAME`)** 이고 pair 쪽 식별은 `FILENAME` 꼬리(`.MK`/`.NT`) 치환으로 유도한다 — `CTRLTAG` · `PAIRFILE` 카드는 싣지 않는다(v1.9 미도입 확정). `NAMECLSH` · `clash/` 격리를 폐지한다. (5) 재저장 유령 중복은 fail-open이며 raw 헤더 층 필터가 거른다. (6) OBSAgent Wrote 논리 이름은 실제 번호를 쓴다 — raw 카드 `CTRLTAG` 미도입은 D-010 의 OBSAgent 논리 이름 규약과 무관하다(규약 불변). (7) 단일 쓰기 주체(ICS) 전제.
>
> **근거**: 무인 운영에서 취득 데이터가 격리되지 않는다. 충돌 1회로 카운터 되감김이 자가 치유된다. 신호는 두 정체 카드의 값 비교로 남기며, 카드 구성이 모든 파일에서 균일해 쓰기 분기가 없다. 상한 100000회 = 번호 공간 한 바퀴로 종료가 보장된다.
>
> **영향**: 구 규격 2.3.1 전면 대체 · 5.2(`UNIQNAME` · `NAMECLSH` 폐지, `ORIGNAME` 신설) · 5.11(pair 규칙) · D-010/D-012 삼총사 문구(**`FILENAME`(+`ORIGNAME`)** 로 개정, `CTRLTAG` 제외) / ics_sim `rawpair.py` · `state.py` · `test_raw_header.py` / converter C-항목 신설(MEF `UNIQNAME` 공급원) / 하류 필터 요구사항 명문화.

---

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| raw 헤더 카드 판정 원장 | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.12.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.12.md) |
| 1위 준거 ICD | [`../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md`](../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md) |
| MEF keyword 정의서 | [`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`](../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md) |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) (v2.2.0) |
| 구 규격 (대체 대상) | [`KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`](KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md) ⛔ ((재작성중)) |
| 키워드맵 (배경 자료, 이관 완료) | `archive/KMT_CEU_Raw_to_MEF_Keyword_Map_v0.7_REVIEW.md` (2026-08-22 이동) |
| 전신 문서 | `archive/KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.4.md` · `archive/KMT_CEU_Raw_Numbering_and_Identity_v0.2.md` |
| 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |
| 검토 진행 상태 | [`SMC_CLAUDE.md`](SMC_CLAUDE.md) |

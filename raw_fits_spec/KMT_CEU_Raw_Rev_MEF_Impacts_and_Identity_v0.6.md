# Raw FITS 헤더 개정에 따른 MEF ICD · MEF Converter 개정 및 검토 사항

**v0.6 (Draft)** · 2026-08-22 · **Part 1** = 헤더 카드 개정이 MEF 쪽 3자(ICD v4.1 · MEF keyword 정의서 v1.0 · converter v2.2.0)에 요구하는 개정 목록 · **Part 2** = raw 파일 번호 · 정체성 · 충돌 처리 재설계와 그 MEF 파급

> **v0.6 에서 바뀐 것 — raw spec v1.3 발행에 따른 정합 (2026-08-22).** ① 재작성판 **`KMT_CEU_Raw_FITS_Specification_v1.3.md`(raw spec)** 이 발행되어 구 규격 참조를 전부 현행판으로 교체했다. ② **Part 2 를 파급 요약으로 축약** — 번호·충돌·정체성의 정본이 raw spec 2.3절과 DECISION_LOG **D-016** 으로 옮겨졌으므로, 본문(§1~§5·§8)을 걷어내고 MEF/구현 파급(구 §6·§7)만 남겼다(내용 이중화 방지). 전신 v0.5 는 `archive/`.

> **v0.5 에서 바뀐 것 — 두 문서를 하나로 합쳤다 (운영자 지시 2026-08-22).**
>
> 1. **통합**: `KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.4.md`(→ Part 1)와 `KMT_CEU_Raw_Numbering_and_Identity_v0.2.md`(→ Part 2)를 이 문서로 합쳤다. 두 전신은 `archive/` 로 옮긴다. Part 를 가른 이유: **Part 1 은 LEECU 가 실행할 항목**이고 **Part 2 는 raw 쪽 규격 결정(+일부 MEF 파급)** 이라 주인이 다르다.
> 2. **키워드맵 잔여 안건 이관**: `KMT_CEU_Raw_to_MEF_Keyword_Map_v0.7_REVIEW.md` 5장에만 남아 있던 미결 4건(`NCTRL` 정의 · `CTRLID` 개칭 · `SATURAT`/`SATLEVEL` 통일 · `DATASRC`/설정 포인터의 MEF 목적지)을 Part 1 §6 으로 옮겼다 — 이로써 키워드맵의 살아있는 내용은 전부 이 문서와 Header_and_Refs 로 흡수됐다.
> 3. **Header_and_Refs v1.11 반영**: 돔 Source 변경(`AUX relay` → `TCS relay or REDIS`, `DALTERR`/`DAZERR` = `ICS calculation`) · `LEDFLASH` 단위 변경([seconds] → [milliseconds] 정수) · `ICSBUILD` 형식 변경(프로그램명 제거) — 셋 다 converter 동작에는 영향이 없어 **기록 행**으로 남겼다(§1 끝).

> **v0.4 에서 바뀐 것 — 운영자 3차 개정(Header_and_Refs v1.9) 반영**: ① **`READMODE` 값 충돌 종결** — raw 쪽은 **`RDMODE` 로 개명 도입**(독출 속도 모드 선언), MEF `READMODE`(`'64AMP'`)는 그대로. ② **raw 신설 카드 `CAMVER` · `RDMODE` · `C1_`/`C2_` 계열** — converter 미독, 도입 시 pass-through 후보로 §2 대응표에 추가. ③ **C-후보 신설** — MEF `VOLTINFO`/`TELEMETRY` 를 raw `Cn_VOLT`·`Cn_CURR`·`Cn_TEMP` 에서 채우는 안. ④ **raw 미도입 확정 반영** — `CTRLTAG`·`PAIRFILE`·`OSCNPATT`·`RDDIRT`/`RDDIRB`·`MIDOSC*`·전압 색인 계열: C-5/C-12 문구를 "규격 조항 + 표본 검증" 기반으로 조정.
>
> **v0.3**: HK 재구성 확정(`WALLBOAR`→`WALLBRD`, 출처 3계통) · C-신설 2건(MEF `UT` 조립 원천 · `DARKTIME` 공급원). **v0.2**: `OBSERVAT` 값 재정의 C-항목(이후 철회로 종결). **Part 2 의 전신 이력** — v0.2: `CTRLTAG`·`PAIRFILE` 미도입 확정 반영(삼총사 문구에서 `CTRLTAG` 제거) · v0.1: 충돌 번호 증가 설계 최초 기록.

> `mef_converter/` 는 읽기 전용(LEECU 소관)이므로 Part 1 은 **변경 요청 목록**이지 변경 자체가 아니다. raw 쪽 근거는 `KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.13.md`(확인 요망 11건 전량 종결)와 Part 2(**D-016 등재 완료**), 검토 세션 기록([`SMC_CLAUDE.md`](SMC_CLAUDE.md))이다. raw spec v1.3 발행에 따라 v0.6 으로 판을 올렸다.

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
- **overscan 좌우 패턴 검증**: 레거시 MEF `AMPSEC` 실측이 M/T=5:3, K/N=3:5 방향 패턴을 보였는데 신규는 4:4(`RRRRLLLL`)를 전제한다 — 같은 e2v CCD290-99이므로 한쪽이 틀렸다. 검증 표본(`KMTN.20260116.000001`) overscan 열 통계로 확정하고, geometry 가 바뀌면 **raw 쪽은 `CAMVER`(HW)/`CTRLxCFG`(설정) 범프 · MEF 쪽은 `GEOMVER` 동반 범프** — `RAWVER` 는 미도입 확정이다(Header_and_Refs v1.13 확인 요망 11: 규격/구성 버전은 `CAMVER`·`CTRLxCFG`·`DETID`·`CHMAP_*` 조합으로 파악).
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

# Part 2 — raw 파일 번호 · 정체성 · 충돌 처리 (파급 요약)

> **정본 이동 완료**: 설계 전문은 **raw spec v1.3 의 2.3절**([`KMT_CEU_Raw_FITS_Specification_v1.3.md`](KMT_CEU_Raw_FITS_Specification_v1.3.md))과 DECISION_LOG **D-016**(Accepted, 2026-08-22)이다. 이 Part 는 MEF/구현 쪽 파급만 남긴다 — 골자: 충돌 시 노출 번호 증가(공간 000000–099999, 선검사, 상한 100000회) · `FILENAME`(유일 키) + `ORIGNAME`(불일치 = 충돌 신호) · `UNIQNAME`/`NAMECLSH`/`clash/`/`PAIRFILE`/`CTRLTAG` 폐지.

## 1. 하류 도구 요구사항

- 충돌 필터는 **raw 헤더 층**(아카이브 색인 · DTS · QL)에서 `FILENAME ≠ ORIGNAME` 으로 돈다. 재저장 유령 중복은 fail-open — 이 필터가 거른다는 전제가 요구사항이다.
- 아카이브 근거는 **`FILENAME`(+`ORIGNAME`)**. pair 쪽 식별은 `FILENAME` 꼬리 `.MK`↔`.NT` 치환.
- MEF 층 필터가 필요해지면 converter 변경점에 `ORIGNAME` pass-through 를 추가한다 (Part 1 §1).

## 2. MEF / converter 연동

converter(v2.2.0)는 raw `UNIQNAME` 을 읽어 MEF `UNIQNAME` 으로 옮긴다(`v2_1.py:405`). 폐지 후 이 값은 **오류 없이 빈 문자열**이 된다 — 대응은 C-항목으로 LEECU 이관 (Part 1 §1).

## 3. ics_sim 구현 영향 (구현 일감)

| 파일 | 변경 |
| --- | --- |
| `rawpair.py` | 선검사 루프(되감음 · 상한 100000회) 신설, clash 격리 로직 제거, `UNIQNAME` 제거, `ORIGNAME` 항상 기록 |
| `state.py` | 확정 N 으로 카운터 동기화, 000000–099999 순환 |
| `sequencer._store()` | 확정된 이름만 수령 (이름 결정은 rawpair 몫) |
| `tests/test_raw_header.py` | `UNIQNAME` 필수 목록 제거·RETIRED 추가, `NAMECLSH` 시험 교체, 평시 `FILENAME`==`ORIGNAME` 불변식, 충돌·되감음·상한 시험 신설 |

---

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| raw 헤더 카드 판정 원장 | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.13.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.13.md) |
| 1위 준거 ICD | [`../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md`](../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md) |
| MEF keyword 정의서 | [`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`](../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md) |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) (v2.2.0) |
| **raw spec (현행)** | [`KMT_CEU_Raw_FITS_Specification_v1.3.md`](KMT_CEU_Raw_FITS_Specification_v1.3.md) — 구판 v1.2 는 `archive/`(구명 Pair_Spec) |
| 키워드맵 (배경 자료, 이관 완료) | `archive/KMT_CEU_Raw_to_MEF_Keyword_Map_v0.7_REVIEW.md` (2026-08-22 이동) |
| 전신 문서 | `archive/KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.4.md` · `archive/KMT_CEU_Raw_Numbering_and_Identity_v0.2.md` |
| 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |
| 검토 진행 상태 | [`SMC_CLAUDE.md`](SMC_CLAUDE.md) |

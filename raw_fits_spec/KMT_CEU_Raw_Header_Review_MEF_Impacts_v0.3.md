# Raw 헤더 개정에 따른 MEF ICD · 정의서 · Converter 개정 사항

**v0.3 (Draft)** · 2026-08-21 · raw 헤더 검토(ACT-011)가 MEF 쪽 3자 — ICD v4.1(1위 준거) · MEF keyword 정의서 v1.0 · converter v2.2.0 — 에 미치는 개정 필요 사항의 전달 목록

> **v0.3 에서 바뀐 것**: HK 재구성 확정 반영 — **`WALLBOAR` → `WALLBRD` 개명**(운영자 확정) · 출처 3계통(`ICG RTD measurement` / `standalone RTD readout unit` / `Tapaculo sensor`) 명시. **C-신설 2건** — MEF `UT` 조립 원천(raw `TSHOPEN`/`TSHSHUT` 폐지 대응) · MEF `DARKTIME` 공급원(raw 폐지, `EXPTIME` 파생). `DATASRC` 값 체계 확장·`CHSTAT` 미기재 판정은 기록만. raw 쪽 근거는 Header_and_Refs **v1.8**.

> **v0.2 에서 바뀐 것**: **`OBSERVAT` 값 재정의 C-항목 추가**(1장) — 확정 초안이 `OBSERVAT` 값을 사이트 코드(`KMTT/KMTC/KMTA/KMTS`)로 바꿨는데, 이는 converter 의 유일한 하드-실패 검사와 상충한다. Header_and_Refs 문서의 v1.7 개정(3장 신형식 표 · 7장 판정 · 8.2 폐지)과 동기.

> `mef_converter/`는 읽기 전용(LEECU 소관)이므로 이 문서는 **변경 요청 목록**이지 변경 자체가 아니다. raw 쪽 근거는 `KMT_CEU_Raw_Numbering_and_Identity_v0.1.md`(번호 · 정체성 · 충돌)와 검토 세션 기록([`SMC_CLAUDE.md`](SMC_CLAUDE.md) ▶절)이다. raw 쪽 카드 이름 · 값은 아직 Draft이며, 확정 시점(D-등재 · 규격 재작성판)에 이 문서도 판을 올린다.

## 1. Converter 변경점(C-*) 신설 · 개정

| 항목 | 내용 | 판단 요청 |
| --- | --- | --- |
| **C-신설: MEF `UNIQNAME` 공급원** | raw `UNIQNAME` 폐지 후 `v2_1.py:405`의 `v("UNIQNAME","")`가 **항상 빈 문자열**을 반환한다(오류 없음) | 대안 (a) raw `FILENAME` 카드에서 채움 (b) 디스크 파일명(`mk_path`)에서 파생 — 이미 AMPINFO `RAWFILE`이 같은 원천을 씀 (c) MEF `UNIQNAME` 자체를 폐지 — MEF `FILENAME` · `RAWFILE`로 충분. **raw 쪽 권고: (c) 검토, 최소 (b)** |
| ~~`OBSERVAT` 관련~~ (v0.2 등재 → **종결**) | 사이트 코드 재정의안이 **철회**되고 `OBSERVAT` 는 현행 체계 그대로 `TESTBED`/`CTIO`/`SAAO`/`SSO` 로 확정됐다(운영자, 2026-08-21) | **개정 항목 없음** — converter 교차검증·ICD 2.1·`rawpair.py` 와 완전 정합 |
| **C-신설(경미): MEF `ORIGIN` 을 상수로** | `ORIGIN` 개념이 **"이 파일이 생성된 곳"** 으로 확정됐다: 관측소 raw = 관측소 이름 · 테스트베드 raw = `KASI` · **KASI 파이프라인 산출물 = `KASI`**. 현행 converter 는 raw `ORIGIN` 을 MEF 로 복사한다(`v2_1.py:341`, `v("ORIGIN","KASI")`) — MEF 는 파이프라인 산출물이므로 개념과 어긋난다 | MEF PRIMARY 의 `ORIGIN` 을 복사 대신 **상수 `'KASI'`** 로 기록. 한 줄 수정, 긴급도 낮음(관측소 raw 를 KASI 서버에서 변환하는 현행 흐름에서만 차이 발생) |
| C-신설(선택): `ORIGNAME` pass-through | 충돌 신호(`FILENAME ≠ ORIGNAME`)는 raw에만 있다. MEF 층 충돌 필터가 필요할 때만 추가 | raw 헤더 층 필터가 기본이므로 필수 아님 |
| **C-11 개정** | amp `MODULE`/`CHANNEL` 공급원: 구 규격의 `AMOD<nn>`/`ACHN<nn>` 색인형 65장 → **`CHMAP_LT`/`CHMAP_LB`/`CHMAP_RT`/`CHMAP_RB` 4장**으로 재설계됐다. 현행 추정식(`MODULE=1+((amp-1)//8)`, `CHANNEL=1+((amp-1)%8)`, 'placeholder' 주석)은 실배선(CCD 출력 채널이 chip당 1–16, TOP/BOT 대역이 chip마다 반대)과 다르다 | `XTALKGROUP` 파생도 이 값 기준으로 재정의. `AMPMAP` 선언 카드는 폐지 방향 |
| C-5 · C-13 개정 | "raw geometry 선언 카드 대조" → **포장 규범 조항 + 표본 검증** 체계로 재조정 예정(`OSCNPATT` · `ROWORDR`는 규격 조항으로 이관 방향). 대조표에 2장의 이름 대응을 명시 | |
| C-12 | amp `READDIR` 공급원(`RDDIRT`/`RDDIRB`) 문구를 규격 이관에 맞춰 갱신. OI-3(실기 확인) 유지 | |
| **C-신설: HK 온도 카드 재구성** (2026-08-21) | 온도센서 구성 변경으로 raw 의 Camera System House Keeping 블록이 재편됐다 — **신설 `DMPTEMP`(DMP 온도) · `WALLBRD`(wallboard 온도 — v0.2 의 `WALLBOAR` 에서 개명) · `HEBOX`(HE box 내부 온도)**, `AIR_IN`/`AIR_OUT`/`GLYC_IN`/`GLYC_OUT` comment 정의 확정(AIR는 열교환기 기준 — IN이 따뜻한 쪽, 레거시 의미 유지), `DEWPRES` 단위 [torr] · 포맷 `x.xxe-x` · **측정불가 sentinel `9.99e-9`**(값 0/이상값/게이지 비숫자 — 규격 5.0 sentinel 표에 DEWPRES 전용 예외로 등재 필요), **`CCDTEMP` 의미 변경**: 구 설계(`CCDTEMP1`·`CCDTEMP2` 평균 파생, D-013)에서 **실측 센서 1개 값**("CCD temperature M")으로. `RTD12` 폐지는 확정대로(D-013). **출처 확정(v0.3)** — `CCDTEMP`·`DEWPRES`·`PT30N*`·`CHARCOAL`·`DMPTEMP`·`WALLBRD` = ICG RTD measurement / `AIR_*`·`GLYC_*` = standalone RTD readout unit / `HEBOX` = Tapaculo sensor | ① converter 가 `DMPTEMP`/`WALLBRD`/`HEBOX` 를 읽지 않음 — MEF 로 보내려면 읽기 추가 ② MEF/L1 의 `CCDTEMP` 정의를 "평균 파생"에서 "대표 센서 실측"으로 갱신 (L1 `CARRY_KEYS` 가 `CCDTEMP` 이름을 요구하므로 이름은 불변) ③ `CCDTEMP1`/`CCDTEMP2` 후보는 **제외 확정**(운영자, 2026-08-21) — 평균 파생 설계 폐기에 따름 |
| **C-신설: MEF `UT` 조립 원천** (2026-08-21) | raw 가 `TSHOPEN`/`TSHSHUT` 를 싣지 않는 것으로 판정됐다(Header_and_Refs v1.8 3.2절). converter 는 `DATE-OBS` 날짜부 + raw `TSHOPEN` 으로 MEF `UT` 를 조립하므로(`v2_1.py:440` · `:583`) **MEF `UT` 시각부가 빈다** — 오류 없음 | `UT` 조립 원천을 `DATE-OBS` 의 시각부로 교체 (`DATE-OBS` 는 밀리초까지 담는다, D-014) |
| C-신설(경미): MEF `DARKTIME` 공급원 | raw `DARKTIME` 미기재 판정 — 값이 `EXPTIME` 과 동일해 파생으로 충분(v1.8 3.2절). 현행 converter 기본값 `0.0` 이 MEF 에 박힌다 | `EXPTIME` 값으로 파생 기록, 또는 MEF `DARKTIME` 폐지 판단 |
| (기록) `DATASRC` 값 체계 확장 · chiller 블록 미기재 | `ARCHON`/`SIM` → **`ARCHON_SCIENCE`/`ARCHON_GUIDE`/`SIM`**(`HEMODE` 흡수) · chiller 4장(`CHSTAT` `CHOP` `CHSET` `CHPROC`)은 raw 미기재 **확정**(운영자가 초안에서 삭제, 2026-08-21) | converter 는 `DATASRC`/`CHOP`/`CHSET`/`CHPROC` 를 읽지 않고 `CHSTAT` 는 기본값 `""` 경로 — 영향 없음/경미, 기록만 |

## 2. raw ↔ MEF 키워드 이름 대응 (raw 개명 · 신설분)

raw 쪽 Detector/Amplifier 블록 확정(2026-08-21)으로 이름이 갈라진 것들이다. converter는 이 카드들을 읽지 않으므로 당장 동작은 안 바뀌지만, **C-5 대조를 붙일 때 이 대응이 없으면 어긋남을 잡을 수 없다.**

| raw (신) | MEF / converter 쪽 | 비고 |
| --- | --- | --- |
| `AMPNAX1` = 1200 | `RAWXTILE` | 값 동일, 이름 상이 |
| `AMPNAX2` = 4700 | (없음) | NAXIS2/NEND 타일 규약 값 |
| `IMAGEX` = 1152 | `AMPDATA` | |
| `IMAGEY` = 4616 | (카드 없음 — 상수 `ACTIVE_HALF_ROWS`, amp extension NAXIS2) | |
| `PRESCNX` = 0 | `PRESCANX` | 레거시 실측 27과 분리하려고 raw 쪽을 개명 |
| `PRESCNY` = 0 | (없음) | |
| `OVRSCNX` = 48 | `OVERSCNX` | 레거시 실측 32와 분리하려고 raw 쪽을 개명 |
| `OVRSCNY` = 84 | (없음 — `MIDOVSCY`=168=2×84 관계, 분배는 OI-4) | |
| `NAMPDET` = 16 | `AMPPCD`(정의서) | raw는 `NAMPS` · `AMPPCD` 폐지 (Header_and_Refs v1.6 8.1절) |
| `NAMPRAW` = 32 | (없음 — raw 파일 단위 개념) | |
| `CHMAP_LT/LB/RT/RB` | AMPINFO `MODULE` · `CHANNEL` (C-11) | 값 = CCD 출력 채널, 자릿수 고정 3자 토큰 8개 |
| `DETID` = 'MK'/'NT' | ((TBD)) | MEF 목적지 미정 — 레거시 계승, 값 재정의(pair) |
| `FILENAME` | MEF `FILENAME`(자체 생성) · AMPINFO `RAWFILE` | converter는 raw `FILENAME` **카드**를 읽지 않음(디스크명만 사용) |
| `ORIGNAME` | (없음 — 선택 pass-through, 1장) | |
| `UNIQNAME` (폐지) | MEF `UNIQNAME` | 1장 C-신설 참조 |
| `DMPTEMP` (신설) | (없음 — 도입 시 pass-through 추가) | HK 재구성, 1장 참조 |
| `WALLBRD` (신설) | (없음 — 도입 시 pass-through 추가) | 〃 |
| `HEBOX` (신설) | (없음 — 도입 시 pass-through 추가) | 〃 |
| `CCDTEMP` (의미 변경) | MEF `CCDTEMP` (L1 `CARRY_KEYS`) | 평균 파생 → 대표 센서 실측, 1장 참조 |
| `TCSTIME` (신설) | (없음) | TCS 시각계 선언 — `TIMESYS`(ICS)와 분리 |
| `CTRL1CFG` / `CTRL2CFG` (신설) | (없음 — raw 전용 설정 포인터) | 버전 문자열 6장을 귀속 (v1.8 3.3절) |

## 3. ICD v4.1 개정 후보

- **§12 (open items)**: raw 텔레메트리 집합의 위임 대상이 구 규격 5장 → 재작성판으로 바뀐다. 참조 갱신.
- **`READMODE` 값 충돌**: ICD/정의서는 `READMODE='64AMP'`(구조 선언), raw 초안은 `'FAST'`(독출 속도 모드)로 쓰려 했다 — **같은 이름, 다른 뜻. 이름 분리 필요**(예: raw 속도 모드는 `READSPD`류 별도 키워드). raw 쪽 미결.
- **AMPINFO의 상류 공급원 명시**: "authoritative 64-row map"의 배선 열(MODULE/CHANNEL)이 converter 추정식이 아니라 **raw `CHMAP_*` + 재작성판의 amp 전수 표**에서 온다는 것을 명시.
- **overscan 좌우 패턴 검증**: 레거시 MEF `AMPSEC` 실측이 M/T=5:3, K/N=3:5 방향 패턴을 보였는데 신규는 4:4(`RRRRLLLL`)를 전제한다 — 같은 e2v CCD290-99이므로 한쪽이 틀렸다. 검증 표본(`KMTN.20260116.000001`) overscan 열 통계로 확정하고, geometry가 바뀌면 `RAWVER` · `GEOMVER` 동반 범프.
- 파일명 체계(D-011)는 **불변** — 충돌 번호 증가 시에도 형식은 같고 번호만 다르다. `find_pair()` · 정규식 영향 없음.

## 4. MEF Keywords 정의서 v1.0 개정 후보

- `UNIQNAME` 항목: 공급원 변경 또는 폐지(1장 C-신설과 연동).
- `NAMPS`=64 · `AMPPCD`=16: raw 쪽 폐지(v1.6 8.1)와의 관계 명시 — MEF 유지 여부는 LEECU 판단(MEF는 카메라 전체 관점이라 유지가 자연스러울 수 있음).
- (기록) 레거시 MEF의 `AMPNAME2`('im16')가 배선 identity를 헤더에 실은 선례 — `CHMAP_*` 채택의 계보.

## 5. 미결(OI-*)과의 연동

| OI | 이 검토와의 접점 |
| --- | --- |
| OI-3 (`ROWORDR`/`RDDIR*`) | 포장 규범 조항 이관 후 flat/star 시험은 "사실 확인"이 아니라 **준수 검증**이 된다 |
| OI-4 (중앙 168행 분배) | raw `OVRSCNY`=84는 타일 규약 값이다. 물리 분배는 실측 후 `MIDOSCT`/`MIDOSCB`로 |
| OI-9 (배선 실측) | `CHMAP_*` 값의 실측 확정 + Archon module/channel 층(`XTALKCAL=True` 전제). CCD 출력 채널 라벨과 Archon tap의 대응은 STA 문서/Tom O'Brien 협의 |
| (신규 제안) | **X overscan 패턴 4:4 vs 5:3 검증** — 검증 표본 overscan 열 통계로 flat 없이 즉시 가능. OI로 등재 요청 |

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| raw 번호 · 정체성 · 충돌 처리 (Draft) | [`KMT_CEU_Raw_Numbering_and_Identity_v0.1.md`](KMT_CEU_Raw_Numbering_and_Identity_v0.1.md) |
| 1위 준거 ICD | [`../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md`](../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md) |
| MEF keyword 정의서 | [`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`](../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md) |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) (v2.2.0) |
| converter가 읽는 것 · 읽지 않는 것 | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.8.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.8.md) |

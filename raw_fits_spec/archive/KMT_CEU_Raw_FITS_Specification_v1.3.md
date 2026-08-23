# KMT-CEU Raw FITS Specification

**v1.3** · 2026-08-22 · **현행** — 2026-08-18~22 전면 재검토(확인 요망 11건 전량 종결 · D-016 등재)를 반영한 재작성판. 구 문서명 "KMT-CEU Raw FITS Pair 규격"(v1.2, `archive/`)을 개명·대체한다. 이 문서를 **raw spec(로우 스펙)** 이라 부른다.

| 연동 | 값 |
| --- | --- |
| 정본 헤더 견본 | [`KMTA.20260818.012345.MK.fits.header.v1.0.txt`](KMTA.20260818.012345.MK.fits.header.v1.0.txt) · [`…NT.fits.header.v1.0.txt`](KMTA.20260818.012345.NT.fits.header.v1.0.txt) — 5장 카드 전량의 **바이트 단위 견본**(각 143카드 = 값 135 + COMMENT 7 + END) |
| 카드 판정 원장 (배경·경위) | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.13.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.13.md) — 이하 **원장**. 카드별 계승/개칭/폐지 근거, converter 대조, 레거시 123개 전량 귀속 |
| MEF·파이프라인 파급 | [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.6.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.6.md) — 이하 **통합 문서**. LEECU 전달용 C-항목·이름 대응 |
| 결정 기록 | `../project_management/governance/DECISION_LOG.md` — D-002(chip order) · D-010(Wrote 분리) · D-011(파일명) · D-012(백엔드 계약) · D-013(레거시 판정) · D-014(관측일) · D-015(사이트 판정) · **D-016(충돌·정체성)** |
| 연동 ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` (v4.1) |
| 연동 converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) |
| Amp 배선 맵 (기계 사본) | [`__reference/Detector_Ch_to_AmpID_Map_v1.0.txt`](__reference/Detector_Ch_to_AmpID_Map_v1.0.txt) — 4.5절 표의 기계 가독 정본 |
| 검출기 데이터시트 | `__reference/CCD290-99 datasheet (V2 - Aug 2016).pdf` (e2v A1A-778871 V2) — 부록 A 의 원전 |

> **절 구성이 구판(v1.2)과 다르다.** 구판 절 번호를 인용한 문서·코드 주석(`규격 5.7절` 등)은 이 판 기준으로 재확인할 것. 배경·경위 설명은 이 문서에 다시 적지 않는다 — **원장**과 **통합 문서**의 장·절을 가리킨다.

## 1. 목적과 범위

STA Archon science controller 2대가 노출 1회당 만드는 **raw FITS pair(MK · NT)** 의 파일 구조, 픽셀 배치, 헤더 keyword 를 정의한다. 판정 기준은 한 문장이다:

> **raw pair 가 이 규격을 만족하면, converter 는 placeholder 없이 L0 MEF 를 실제 값으로 채울 수 있어야 한다.**

| 구분 | 대상 | 규격 |
| --- | --- | --- |
| **입력 (이 문서)** | Archon raw FITS pair (MK, NT) | `raw_fits_spec/` |
| 출력 | L0 64-amplifier MEF | `../mef_fits_spec/` |
| 변환 | raw pair → L0 MEF | `../mef_converter/` |
| 후처리 | L0 → L1 calibrated CCD | `../mef_pipeline/` |

**범위 밖** — raw 헤더에 넣지 않는다 (5.10절):

- amp별 `GAIN`/`RDNOISE`/`SATLEVEL`/`LINMAX`, crosstalk 계수, **`XTALKVER`/`REFVER`/`CATVER`** — pipeline calibration DB 소관. HW·성능 변화 없이도 pipeline setup 에서 바뀌는 값이라 취득 시점의 raw 에 실으면 곧 낡는다. **계층 규칙: raw 미기재 · L0 수록은 pipeline 팀 판단 · L1(전처리 후)은 필수 수록** (운영자 확정 2026-08-22, 통합 문서 §4).
- WCS 해 — L0 은 placeholder, 확정 해는 L1.
- Guide/focus CCD 자료.

구현 주체: 신규 ICS(`../ics_sim/` — 시뮬 구현·검증, 실기는 `hardware/archon.py`) · 실험실 취득(`../cam_char/archon/`) · converter(읽기 전용, LEECU 소관).

## 2. Raw FITS Pair

### 2.1 노출 1회 = 파일 2개

| Raw file | 담는 chip | Controller | 비고 |
| --- | --- | ---: | --- |
| `…MK.fits` | M, K | 1 (`<SITE>-SCI-101`) | converter 가 **헤더를 읽는 쪽** (master metadata) |
| `…NT.fits` | N, T | 2 (`<SITE>-SCI-102`) | **완전성 동일 요구** — 5장의 필수 keyword 를 전부 채운다 (ICD v4.1, OI-8 종결) |

공식 chip order 는 `M,K,N,T` (D-002). NT 파일도 단독으로 해석 가능해야 아카이브 자산으로 온전하다.

### 2.2 파일명

**형식 (D-011):**

```text
<SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits
<SITE>.<YYYYMMDD>.<NNNNNN>.NT.fits
```

- `<SITE>` — 4자 대문자 사이트 코드, TC 텔레메트리 `TELID` 규약과 동일. **이 넷 밖의 값은 전부 `KMTT` 로 정규화**하고 경고를 남긴다. 실효 사이트는 호스트 IP 로 판정하며 판정이 설정을 이긴다 (D-015).

  | `<SITE>` | 사이트 | `OBSERVAT` | L0 MEF prefix |
  | --- | --- | --- | --- |
  | `KMTC` | CTIO | `CTIO` | `kmtc` |
  | `KMTS` | SAAO | `SAAO` | `kmts` |
  | `KMTA` | SSO | `SSO` | `kmta` |
  | `KMTT` | 테스트베드 | `TESTBED` | `kmtt` |

- `<YYYYMMDD>` — **그 사이트의 관측일** (D-014): UT 에 사이트별 보정을 더한 뒤 날짜만 취한다. 경계는 CTIO UT 16:30(`+7:30`) · SAAO UT 10:30(`−10:30`) · SSO UT 01:30(`−1:30`) · KMTT 보정 0. **검산 불변식: 세 경계가 모두 현지 12:30.** 구현은 "보정 후 날짜만 취하는 한 줄"이어야 한다 — 경계를 `if` 로 나열하면 off-by-one 이 1년에 몇 번만 드러난다. **`<YYYYMMDD>` 는 `DATE-OBS` 의 날짜와 일반적으로 다르며 그것이 의도다** — 둘을 같다고 가정하는 도구를 만들면 안 된다.
- `<NNNNNN>` — **6자리 고정폭, 0 좌측 패딩** 노출 번호. pair 양쪽 동일. converter 정규식(`^(KMTC|KMTS|KMTA|KMTT)\.(\d{8})\.(\d{6})\.MK\.fits$`)과 `find_pair()`(`.MK.fits`↔`.NT.fits` 치환)가 이 형식에 걸려 있다 — 자릿수 위반은 짝 탐색 실패 또는 fallback 경로다.
- **파일명 `<SITE>` 와 헤더 `OBSERVAT` 는 일치해야 한다** — converter 가 교차 검증하며 **불일치는 이 규격에서 유일한 하드 실패**다 (5.3절).

### 2.3 노출 번호와 이름 충돌 처리 (D-016)

**충돌 시 격리·개명 대신 노출 번호를 증가시켜 저장한다.** 정본은 DECISION_LOG **D-016** (Accepted, 2026-08-22).

1. 번호 공간은 **`000000`–`099999`** — 카운터는 100000 도달 시 `000000` 으로 되감는다 (레거시 관례).
2. 쓰기 전에 후보 N 의 **MK·NT 두 경로를 모두 선검사** — 점유 시 N+1 재검사(099999 넘으면 000000). **+1 이 100000회(공간 한 바퀴)를 초과하면 멈추고 ERROR, 저장하지 않는다.** 실패 조건은 이것 하나뿐이다.
3. 확정 N 으로 **카운터를 동기화**한다 (평소 영속화 경로 그대로, 점프는 경고 로그).
4. **정체성 카드 둘을 모든 파일에 항상 기록한다:**

   ```text
   FILENAME= 'KMTA.20260818.012345.MK' / Filename assigned by ICS
   ORIGNAME= 'KMTA.20260818.012340.MK' / Original filename assigned by ICS counter
   ```

   `FILENAME` = 실제 저장명(확장자 없음) — **아카이브·DTS·색인의 유일 키**. `ORIGNAME` = 카운터가 처음 배정한 이름. **충돌 신호 = `FILENAME ≠ ORIGNAME`** (값 비교 — 카드 존재가 아니다). `ORIGNAME` 결측은 충돌이 아니라 헤더 결함으로 분류한다. 둘 다 **FITS 문자열 카드 필수** — 숫자 카드는 zero-padding 을 파괴한다 (5.0절).
5. 충돌 증가는 pair 동시이므로 **짝 이름은 `FILENAME` 의 `.MK`↔`.NT` 치환으로 항상 유도**된다 — `PAIRFILE`·`CTRLTAG` 카드는 없다.
6. 재저장(유령 중복)은 fail-open — **raw 헤더 층 필터(`FILENAME ≠ ORIGNAME`)가 거른다는 것이 하류 도구 요구사항**이다. MEF 층 필터가 필요해지면 `ORIGNAME` pass-through 를 C-항목으로 추가한다 (통합 문서 §1).
7. 전제: 저장 디렉토리의 쓰기 주체는 **ICS 하나뿐**이다.

> 폐지: `UNIQNAME` · `NAMECLSH` · `clash/` 격리 · `PAIRFILE` · `CTRLTAG` · `EXPID`/`EXPNUM`. 경위는 원장 8.2절, 통합 문서 Part 2.

### 2.4 크기

| 항목 | 값 |
| --- | ---: |
| 파일당 픽셀 | 19200 × 9400 = 180,480,000 |
| 파일당 데이터 | ≈ 344.2 MiB |
| Pair 1쌍 | ≈ 688.5 MiB |

raw pair 픽셀 총수 − L0 MEF amp 픽셀 총수(64 × 1200 × 4616) = **정확히 middle Y overscan 블록**(2 × 19200 × 168 = 6,451,200). 이 등식이 깨지면 4장 해석이 어긋난 것이다.

### 2.5 저장 완료 통보 — ICS `Wrote` 규약 (D-010 · D-012)

파일은 컨트롤러 단위 2개, OBSAgent 통보는 **레거시 그대로 CCD 단위 4회**. 논리 이름은 `KMTN<chip 소문자>.<YYYYMMDD>.<NNNNNN>.fits` — **`KMTN` prefix 는 물리 파일명의 사이트 코드와 무관하게 불변**이다 (OBSAgent `FitsNum` 파서 기준점).

- 프레임 N 의 `Wrote` 4회는 프레임 N+1 의 `EXPSTATUS=READOUT` 발신 **이전**에 내보낸다 — READOUT~첫 `PCTREAD=` 사이 약 2.7초는 함정 창이다 (구판 2.5절 실측 근거, OBSAgent `commands.c` 812–816).
- 이름 충돌로 번호가 증가하면 ICS 가 **WARNING 로그**를 남긴다 (2.3절 — 격리·개명 통보는 폐지).
- **`LASTFILE` 은 실재 경로가 아니다.** 하류 도구의 근거는 raw 헤더의 **`FILENAME`(+`ORIGNAME`)** 이다 (D-016). 논리 이름 ↔ 실제 파일 대응은 `FILENAME` 꼬리와 chip order 규약에서 나온다.

## 3. 파일 구조

| 요구 | 값 | 근거 |
| --- | --- | --- |
| HDU 구성 | **single HDU** (PRIMARY 에 이미지) | converter 가 첫 END 직후부터 픽셀을 memmap |
| `BITPIX` | **16** | 다르면 converter 즉시 실패 |
| 픽셀 표현 | big-endian signed 16-bit + `BZERO=32768` (unsigned 관례) | converter 가 `>i2` 로 읽어 그대로 MEF 기록 |
| `NAXIS1` / `NAXIS2` | **19200 / 9400** | 다르면 converter 즉시 실패 |
| 패딩 | 헤더·데이터 모두 2880 B 블록 | FITS 표준 |
| 압축 | 파일 내부 압축 금지 (전송용 `.gz` 는 파일 단위 별도) | |
| Binning | **1×1 전용** (`CCDXBIN`/`CCDYBIN` 2·3 은 reserved) | OI-5 |

## 4. 픽셀 배치 (Raw Geometry)

### 4.1 X 방향 — 16개 amp tile

```text
X:  1 ....................... 9600 | 9601 ..................... 19200
    첫 번째 chip (M 또는 N)          두 번째 chip (K 또는 T)
    strip 1..8 × 1200 col            strip 1..8 × 1200 col
```

tile 1개 = **1200 col = active 1152 + X overscan 48**, prescan 0 (`AMPNAX1 = PRESCNX + IMAGEX + OVRSCNX`).

X overscan 의 좌우는 strip 으로 정해진다 — **전제 패턴 `RRRRLLLL`** (strip 1–4 = 오른쪽 48, strip 5–8 = 왼쪽 48). ⚠️ **이 패턴은 검증 표본 대조가 남아 있다**: 레거시 MEF `AMPSEC` 실측이 M/T=5:3 · K/N=3:5 방향 패턴을 보여 4:4 전제와 상충한다 — 확정 전까지 "상충 증거 있음"으로 다룬다 (8장 OI-15, 통합 문서 §3·§5).

### 4.2 Y 방향 — 상·하 분할 독출과 중앙 overscan

```text
Y:  1 ..... 4616 | 4617 ..... 4784 | 4785 ..... 9400
    BOT active     middle Y overscan   TOP active
    (4616 rows)    (168 rows)          (4616 rows)
```

- CCD 1개(9232행)를 8개 strip 이 상·하 양 끝에서 동시에 읽는다 — X tile 1개 = amp 2개(TOP/BOT), 파일 1개 = chip 2 × amp 16 = **amp 32개**.
- 중앙 168행은 양 half 의 active 를 다 읽은 뒤 추가 clocking 된 Y overscan 이다 (`AMPNAX2 = PRESCNY + IMAGEY + OVRSCNY` = 0+4616+84, ×2 half). half 별 분배(84/84 여부)는 실측 확정 전이다 (OI-4).
- ⚠️ **레거시 `OVERSCNY` 와 뜻이 다르다** — 레거시는 가장자리(값 0), 신규는 **영상 중앙**. 그래서 이름을 `OVRSCNY` 로 갈랐다 (원장 8장). 이름만 보고 "위쪽 N행 자르기"를 하는 도구는 active 픽셀을 지운다.

### 4.3 포장 규범 조항 (normative)

> **raw 프레임은 검출기 공간 순서로 완전 정렬되어 저장된다** — X 는 타일 내·타일 간 모두 CCD 좌표 오름차순, Y 는 양 half 모두 CCD 좌표 오름차순(TOP half 는 독출 순서가 아니라 **CCD 좌표 순서**로 기록 — raw row 4785 ↔ CCD row 4617).

- 이것은 관찰이 아니라 **요구사항**이다. 구판의 `ROWORDR`·`OSCNPATT` 카드는 폐지되고 이 조항으로 이관됐다 (원장 7장).
- **고정 대상 = `CAMVER`(HW) + `CTRLxCFG`(FW/설정)** — 포장이 바뀌는 원인은 HW·설정 변경뿐이므로 그 둘의 범프가 판별 신호다. 별도 규격 버전 카드(`RAWVER`)는 두지 않는다 (원장 확인 요망 11, 5.10절).
- flat/star sequence 시험(OI-3)은 이 조항의 **준수 검증**이다. 취득 SW 쪽 상시 방어는 `ics_sim/tests/test_geometry_vs_converter.py` (코드-대-코드 대조).

### 4.4 amp 1개의 raw 좌표

| Amp 범위 | half | raw Y 구간 | CCD Y 구간 |
| --- | --- | --- | --- |
| 1–8 | TOP | 4785 : 9400 | 4617 : 9232 |
| 9–16 | BOT | 1 : 4616 | 1 : 4616 |

strip = ((amp−1) mod 8) + 1. tile X 구간은 `X0 + (s−1)·1200 + 1 … X0 + s·1200` (X0: 첫 chip 0, 둘째 chip 9600).

### 4.5 Amp 전수 표 (64행)

**기계 가독 정본은 [`__reference/Detector_Ch_to_AmpID_Map_v1.0.txt`](__reference/Detector_Ch_to_AmpID_Map_v1.0.txt)** 이고 아래 표는 그 전개다. 헤더의 `CHMAP_LT/LB/RT/RB` 카드(5.2절)는 이 표의 CCD 출력 채널 열을 raw X 오름차순으로 투영한 것이다.

| Raw file | 사분면 | Port | CCD 출력 채널 (raw X 오름차순, tile 1→8) | IMGSEC | MEF AmpID | 검증 상태 |
| --- | --- | :---: | --- | :---: | --- | --- |
| MK | 좌반 TOP (`CHMAP_LT`) | A | M16, M15, M14, M13, M12, M11, M10, M09 | D-TOP | 01–08 | 배선표 v1.0 (2026-08-21 검토 완료) |
| MK | 좌반 BOT (`CHMAP_LB`) | A | M01, M02, M03, M04, M05, M06, M07, M08 | A-BOT | 09–16 | 〃 |
| MK | 우반 TOP (`CHMAP_RT`) | B | K08, K07, K06, K05, K04, K03, K02, K01 | A-TOP | 17–24 | 〃 |
| MK | 우반 BOT (`CHMAP_RB`) | B | K09, K10, K11, K12, K13, K14, K15, K16 | B-BOT | 25–32 | 〃 |
| NT | 좌반 TOP (`CHMAP_LT`) | A | N08, N07, N06, N05, N04, N03, N02, N01 | A-TOP | 33–40 | 〃 |
| NT | 좌반 BOT (`CHMAP_LB`) | A | N09, N10, N11, N12, N13, N14, N15, N16 | B-BOT | 41–48 | 〃 |
| NT | 우반 TOP (`CHMAP_RT`) | B | T16, T15, T14, T13, T12, T11, T10, T09 | D-TOP | 49–56 | 〃 |
| NT | 우반 BOT (`CHMAP_RB`) | B | T01, T02, T03, T04, T05, T06, T07, T08 | A-BOT | 57–64 | 〃 |

- 검증 불변식: 카드당 8토큰 · `CHMAP_L*` 접두 = `DETID[0]` · `CHMAP_R*` 접두 = `DETID[1]` · chip 당 채널 01–16 전량 · pair 합계 64.
- **TOP/BOT 대역이 chip 마다 반대**다 (M: TOP=16–09 / K: TOP=08–01 등) — converter 현행 추정식(`MODULE`/`CHANNEL`)과 다르므로 MEF 쪽 재정의가 C-11 이다 (통합 문서 §1).
- `IMGSEC` 의 `A`/`D` 는 **e2v 데이터시트의 image section 명칭으로 확인**됐다 — A = 아래 half(레지스터 E/F, OS1–8), D = 위 half(레지스터 G/H, OS9–16). 부록 A 참조. ⚠️ **`B` 표기는 데이터시트에 없다**(섹션은 A·D 뿐) — K·N 조의 `B-BOT` 이 무엇을 가리키는지 해명이 남았다 (OI-17 잔여). amp 별 물리 독출 방향은 클럭 결선(ACF) 소관이라 실기 확인 대상이다 (OI-3 · OI-9).

## 5. 헤더 Keyword 규격

**정본 견본은 헤더 초안 v1.0 pair** — 카드 순서·comment·패딩까지 바이트 단위 기준이다. 이 장의 표는 그 견본의 전 카드(값 135장)를 블록 순서대로 규정한다. 카드별 판정 경위는 원장 3·6·7·8장.

### 5.0 작성 정책

| 상태 | 의미 |
| --- | --- |
| 필수 | 없으면 L0 MEF 가 틀린 값을 갖거나 변환이 실패한다 — 5장 전 카드가 원칙적으로 필수다 |

| 형 | 표기 | Sentinel (값 없음) |
| --- | --- | --- |
| 문자열 `S` | FITS 문자열 카드 | `'NC'` (레거시 관례) |
| 정수 `I` | | `-1` |
| 실수 `R` | | `-999.0` |
| **HK 온도·습도** | **문자열** — 부호 포함 소수 2자리(`'-101.23'`/`'+16.78'`), FSA 2장은 ENS식(소수 1자리) | **`'-999.99'` 단일값** — 온도로는 불가능, 습도로는 음수 (기각 사유: 원장 v1.12 changelog) |
| `DEWPRES` | 문자열 `x.xxe-x` [torr] | `'9.99e-9'` (0·음수·비수치·범위 밖 전부) |

공통 규칙:

- keyword 8자 이내, `HIERARCH` 금지. 시각은 전부 UTC (`TIMESYS='UTC'` 선언, 값에 `Z` 를 붙이지 않는다 — 예외는 `ICSBUILD`).
- **식별자 keyword 는 문자열 카드 필수** (`FILENAME` `ORIGNAME` `OBSERVAT` `ORIGIN` `DETID` 등) — 숫자 카드는 zero-padding 을 파괴한다 (`'…000010'` → `…00001`). 검사는 값이 아니라 **카드의 형**을 본다.
- **HK 온도·습도 카드는 전부 문자열** — 레거시 계승(`CCDTEMP='-103.16'`), converter pass-through 라 아카이브 전체의 형이 통일된다 (원장 3.7절).
- `EXPTIME` · `DATE-OBS` · geometry keyword 에는 sentinel 을 쓰지 않는다 — 취득 SW 가 구조적으로 아는 값이며, 못 채우면 그 노출은 결함이다 (카드를 비워 변환 실패 경로가 발동하게 한다).
- **Source 가 `ICS INI` 인 카드는 전부 `ics_sim`/`ics_archon` 의 ini 에서 수정 가능해야 한다** (운영자 지시 2026-08-22 — `[camera]` · `[controllers]` · `[site]`/`[site.<코드>]` 절).

출처 어휘: `ICS INI`(설정) · `ICS code`(취득 SW 산출) · `user input/selection` · `TCS relay` / `AUX relay`(TC 중계) · `TCS relay or REDIS`(newTCS 계통) · `Archon`(컨트롤러) · `ICG RTD` / `standalone RTD` / `Tapaculo`(HK 실측 3계통) · `ICS calculation`(파생).

### 5.1 FITS 표준 · 구조 (8장)

| Keyword | 형 | 값 | 출처 |
| --- | :---: | --- | --- |
| `SIMPLE` | L | `T` | ICS code |
| `BITPIX` | I | `16` | ICS code |
| `NAXIS` | I | `2` | ICS code |
| `NAXIS1` | I | `19200` | ICS code |
| `NAXIS2` | I | `9400` | ICS code |
| `BSCALE` | I | `1` — comment `PHYSICAL=INTEGER*BSCALE+BZERO` | ICS code |
| `BZERO` | I | `32768` | ICS code |
| `BUNIT` | S | `'ADU'` | ICS code |

### 5.2 Instrument · Detector (23장)

| Keyword | 형 | 값 | 출처 |
| --- | :---: | --- | --- |
| `INSTRUME` | S | `'<SITE코드> 18k CCD'` (예 `'KMTA 18k CCD'`) | ICS INI |
| `CAMVER` | S | `'CEU-v2.1'` — **HW·성능상 변경이 있을 때만 올린다**: 전자부 세대 판별의 참조점 | ICS INI |
| `FPAID` | S | `'FPA#1'` — 검출기 조립 정체 | ICS INI |
| `DETECTOR` | S | `'e2v CCD290-99'` | ICS INI |
| `DETID` | S | `'MK'` / `'NT'` — **이 파일의 detector pair** (pair 상이, 5.9절) | ICS code |
| `PIXSIZE` | R | `10.0` [μm] | ICS code |
| `PIXSCALE` | R | `0.395` [arcsec/px] (Gaia DR3 실측 갱신값) | ICS code |
| `CCDXBIN` `CCDYBIN` | I | `1` (2·3 reserved — OI-5) | ICS code* / user selection |
| `NAMPDET` | I | `16` — detector 당 amp 수 | ICS code |
| `NAMPRAW` | I | `32` — 이 파일의 amp 수 | ICS code |
| `AMPNAX1` | I | `1200` = `PRESCNX`+`IMAGEX`+`OVRSCNX` | ICS code |
| `AMPNAX2` | I | `4700` = `PRESCNY`+`IMAGEY`+`OVRSCNY` | ICS code |
| `IMAGEX` `IMAGEY` | I | `1152` · `4616` | ICS code |
| `PRESCNX` `PRESCNY` | I | `0` · `0` (side varies / frame-edge side) — 레거시 `PRESCANX`(27)의 **키워드 변경 계승** (원장 확인 요망 10) | ICS code |
| `OVRSCNX` `OVRSCNY` | I | `48` (side varies) · `84` (**frame-center side**) | ICS code |
| `CHMAP_LT` `CHMAP_LB` `CHMAP_RT` `CHMAP_RB` | S | CCD 출력 채널 8토큰, raw X 오름차순 (4.5절 표 — pair 상이) | ICS code |

축별 합 불변식이 comment 에 자체 문서화된다. `AMPNAX1/2` 값이 바뀌는 것은 geometry 변경 = `CAMVER`/`CTRLxCFG` 범프 사안 (4.3절).

### 5.3 Observatory (7장)

| Keyword | 형 | 값 | 출처 |
| --- | :---: | --- | --- |
| `ORIGIN` | S | **"이 파일이 생성된 곳"** — 관측소 raw = `SSO`/`CTIO`/`SAAO`, 테스트베드 raw = `KASI` (KASI 파이프라인 산출물도 `KASI` — MEF 는 상수화 C-항목) | ICS INI (사이트 유도) |
| `OBSERVAT` | S | `TESTBED`/`CTIO`/`SAAO`/`SSO` — **파일명 `<SITE>` 와 교차 검증, 불일치는 변환 오류** (유일한 하드 실패) | ICS INI |
| `TELESCOP` | S | `'KMTNet 1.6m #1/#2/#3'` (테스트베드 `Sim`) | ICS INI |
| `LATITUDE` | S | `'-31:16:24'` 등 — 문자열 그대로 (정규화 금지) | ICS INI |
| `LONGITUD` | S | **서경** `[deg W]` — SSO `'210:56:08'` 등. 동경으로 고치면 부호 뒤집힌 좌표가 박힌다 | ICS INI |
| `ELEVATIO` | I | 사이트 고도 [m] | ICS INI |
| `OBSERVER` | S | `'KMTNetOp'`* / user input | ICS code* / user input |

측지 실측값·서경 규약 검증은 구판 OI-11 기록(archive v1.2 9장) 참조. 테스트베드는 좌표를 **일부러 비워** sentinel 을 싣는다.

### 5.4 Exposure · 파일 정체성 (10장)

| Keyword | 형 | 값 | 출처 |
| --- | :---: | --- | --- |
| `PROJID` | S | `'OBS'`* / `'ENG'` 등 | ICS code* / user input |
| `IMAGETYP` | S | `BIAS`* / `DARK` / `OBJECT` / `FLAT` / `SKY` / `DOMEFLAT` | ICS code* / user selection |
| `OBJECT` | S | 대상명 (`'bias'`* 등) | ICS code* / user input |
| `OBSTYPE` | S | `IMAGETYP` 과 동일 어휘 | `IMAGETYP`* / user input |
| `EXPTIME` | **I/R** | **정수형 기본, 소수점 아래 값이 있을 때만 실수형** [seconds] | ICS code* / user input |
| `LEDFLASH` | I | 점검용 LED 점등 시간 — **[milliseconds] 정수**. ⚠️ 레거시([seconds])와 단위가 다르다 — comment 가 단위를 명시한다 (원장 6장) | ICS code |
| `TIMESYS` | S | `'UTC'` 고정 — comment `ICS Time System` (TCS 쪽은 `TCSTIME`, 5.7절) | ICS code |
| `DATE-OBS` | S | ICS 가 `SHOPEN` 을 지시한 UTC — **밀리초 필수** (`2026-08-21T12:34:56.789`). sentinel 금지 — 없으면 MEF 시각 전체가 변환 시각으로 오염된다 | ICS code |
| `FILENAME` | S | 실제 저장명, 확장자 없음 — **아카이브 유일 키** (2.3절, pair 상이) | ICS code |
| `ORIGNAME` | S | 카운터 최초 배정명 — `FILENAME` 과의 불일치 = 충돌 신호 (pair 상이) | ICS code |

### 5.5 Controller · ICS (9장)

| Keyword | 형 | 값 | 출처 |
| --- | :---: | --- | --- |
| `DATASRC` | S | `ARCHON_SCIENCE` / `ARCHON_GUIDE` / `SIM` — **시뮬 프레임 오인을 막는 유일한 카드** + 작성 프로그램 식별 | ICS code |
| `CTRL1ID` `CTRL1SN` | S | `'<SITE>-SCI-101'` (ID 숫자 = IP) · `'STA-0288'` — 실값 원자료 `__reference/Archon_Unit_Info.txt` | ICS INI |
| `CTRL1CFG` | S | 적용된 Archon 설정 파일명 (`'KMTA_SCI_101_R2609.1'`) — **타이밍·바이어스·클럭 버전 문자열은 전부 이 파일로 귀속** (개별 버전 카드 없음) | ICS INI |
| `CTRL2ID` `CTRL2SN` `CTRL2CFG` | S | 컨트롤러 2 (`-102` · `'STA-0289'` · …) — **두 대분을 양쪽 파일에 모두 싣는다** (converter 가 MK 만 읽으므로) | ICS INI |
| `ICSBUILD` | S | **`v<버전>:<빌드일시(UTC)Z>`** (예 `'v0.1.2:2026-08-21T18:09Z'`) — 프로그램명 없음(식별은 `DATASRC`), 끝의 `Z` 는 의도적 | ICS code |
| `RDMODE` | S | 독출 모드 (`'NORMAL'` 등) — MEF `READMODE`(`'64AMP'`, 구조 선언)와 **별개** | ICS INI / ICS code |

guide FITS 는 `CTRL1xx` 한 벌만 싣고, 컨트롤러 수가 늘면 `CTRLnxx` 벌이 늘어나는 확장 규약이다.

### 5.6 Camera System House Keeping (18장)

전부 **문자열** (5.0절 형 규칙). 공급 3계통 — `ICG RTD`(Archon 쪽) · `standalone RTD`(별도 판독 장치) · `Tapaculo`(환경 센서, 5.8절 FSA).

| Keyword | 값 | 출처 |
| --- | --- | --- |
| `DEWPRES` | `'1.23e-4'` [torr] — sentinel `'9.99e-9'` | ICG RTD |
| `CCDTEMP` | **실측 대표 센서 1개** ("CCD temperature M") [deg C] — L1 `CARRY_KEYS` 가 이름으로 요구, 평균 파생 아님 | ICG RTD |
| `DMPTEMP` | DMP 온도 [deg C] | ICG RTD |
| `PT30N1` `PT30N2` | PT-30 cold-end #1/#2 [deg C] | ICG RTD |
| `CHARCOAL` | charcoal canister [deg C] | ICG RTD |
| `WALLBRD` | wallboard [deg C] | ICG RTD |
| `HEBOX` | HE box 내부 [deg C] | Tapaculo |
| `AIR_IN` `AIR_OUT` | 열교환기 흡기/배기 [deg C] — **IN 이 따뜻한 쪽** (레거시 의미 유지) | standalone RTD |
| `GLYC_IN` `GLYC_OUT` | HE box 유입/배출 glycol [deg C] | standalone RTD |
| `C1_TEMP` `C1_VOLT` `C1_CURR` | 컨트롤러 1 모듈별 온도/전압/전류 — **공백 구분 나열, 자리 = 항목** (전압 순서: P2V5 P5V P6V N6V P17V N17V P35V) | Archon |
| `C2_TEMP` `C2_VOLT` `C2_CURR` | 컨트롤러 2 동형 | Archon |

`Cn_*` 는 MEF `VOLTINFO`/`TELEMETRY` 를 실측으로 채울 원천이다 (C-후보, 통합 문서 §1). NT 파일의 `CCDTEMP` 대표 센서 귀속은 확인 항목 (8장).

### 5.7 TCS Information and Status (27장)

TCS 중계값은 문자열로 싣는다 (레거시 계승). 시각 카드는 `Z` 없이 (`TCSTIME` 이 시각계 선언).

| Keyword | 값 | 출처 |
| --- | --- | --- |
| `TCSLINK` | `Up` / `Idle` / `Down` | ICS code |
| `TCSARC` | `Enabled` 등 — 링크 자동복구 모드 | ICS code |
| `TCSQDATE` `TCSUDATE` | 마지막 TCS 질의/갱신 UTC (밀리초) | ICS code |
| `TCSTIME` | TCS 가 보고한 time system (`'UTC'`) — `TIMESYS`(ICS)와 분리 | TCS relay |
| `RADECSYS` | `'ICRS'` | TCS relay |
| `RA` `DEC` `EQUINOX` `HA` `ST` `SECZ` `ALT` `AZ` | 포인팅 (`'hh:mm:ss.ss'` 등 레거시 형식) | TCS relay |
| `TCSDRIVE` `TELMOVE` | 구동/모션 상태 — **`TCSDRIVE`(8자)로 쓴다** (converter 우선 탐색 이름) | TCS relay |
| `DSSTAT` `DSUP` `DSLW` `DSSAF` `DSAUTO` `DSALT` `DSAZ` `DSTELALT` `DSTELAZ` | 돔 셔터·지향 — **newTCS 편입으로 출처가 TCS 계통** (원장 3.6절). `DSTELALT` 는 레거시 `DSTEL` 의 개칭 — 중계 필드명이 무엇이든 ICS 가 이 카드명으로 싣는다 | TCS relay or REDIS |
| `DALTERR` `DAZERR` | 돔–망원경 지향차 [deg] | ICS calculation |

### 5.8 AUX Information and Status (33장)

| Keyword | 값 | 출처 |
| --- | --- | --- |
| `AUXLINK` | `Up` / `Down` | ICS code |
| `AUXARC` `AUXQDATE` `AUXUDATE` | 링크 복구 모드 · 질의/갱신 UTC | ICS code |
| `FSSTAT` `FILTOP` `FILNUM` `FILTER` | 필터-셔터 계통 상태 · 필터 | AUX relay |
| `SHUTOP` | `NC`/`STANDBY`/`OPENING`/`OPENED`/`CLOSING`/`RELOADING`/`ERROR` | AUX relay |
| `SHUTTER` | `OPEN`/`CLOSED`/`UNKNOWN` — **`SHUTOP` 의 순수 함수**, "완전 개방"을 뜻하지 않는다. `SHOPEN`+3초 재질의로 노출 중 값 반영 (OI-13) | AUX relay |
| `FASTAT` `FAFOCUS` `FATILTNS` `FATILTEW` `FAPOSS` `FALIMS` `FAPOSE` `FALIME` `FAPOSW` `FALIMW` | 초점 액추에이터 | AUX relay |
| `MCSTAT` `MCPOS` | 미러 커버 | AUX relay |
| `ENSTAT` `ENFAN` `ENS1`–`ENS7` | 환경 계통 (ENS 값은 중계 그대로, 소수 1자리) | AUX relay |
| `FSATEMP` `FSAHUM` | FSA 내부 온도/습도 — ENS식 표기 잠정 (**Tapaculo 원값 포맷 확인 후 최종** — 8장) | Tapaculo |

### 5.9 Pair 일관성 규칙

| 구분 | Keywords |
| --- | --- |
| **반드시 상이 (7장)** | `DETID` · `CHMAP_LT` `CHMAP_LB` `CHMAP_RT` `CHMAP_RB` · `FILENAME` `ORIGNAME` (`.MK`↔`.NT` 꼬리) |
| **반드시 동일** | **위 7장을 뺀 전부** — 컨트롤러 정체 색인형(`CTRL1*`/`CTRL2*`)과 `Cn_*` 텔레메트리도 양쪽에 같은 값을 싣는다 |

충돌 증가 시 두 파일이 함께 같은 번호로 증가하므로 (`FILENAME`,`ORIGNAME`) 불일치 여부도 pair 양쪽에서 동일하다 (D-016).

### 5.10 raw 에 넣지 않는 keyword

| 분류 | 대표 | 이유 |
| --- | --- | --- |
| MEF 구조·산출물 정체 | `EXTNAME` `DATAPROD` `PRODVER` `GEOMVER` `CREATOR`(MEF) 등 | converter 가 생성 |
| Section 좌표·amp 식별 | `CCDSEC` `AMPSEC` `DATASEC` `BIASSEC` `AMPID` `READDIR` 등 | 4장 geometry 에서 계산 — 중복은 불일치 원천 |
| Calibration | `GAIN` `RDNOISE` `SATLEVEL` `LINMAX` · crosstalk 전체 · **`XTALKVER` `REFVER` `CATVER`** | pipeline caldb 소관 — **계층 규칙**(1장): raw 미기재 · L0 재량 · L1 필수 |
| WCS · 파생 시각 | `CTYPE*` … · `JD` `MJD-OBS` `UT` `DARKTIME` `TSHOPEN` `TSHSHUT` | L1 / `DATE-OBS`·`EXPTIME` 파생 |
| 폐지·미도입 | `UNIQNAME` `NAMECLSH` `PAIRFILE` `CTRLTAG` `RAWVER` `RAWPROD` `OSCNPATT` `ROWORDR` `RDDIRT/B` `MIDOSC*` `CHIP1/2` `CHIPS` `HEMODE` `NPHLINES` `CHKIMG(_C)` chiller 4장 `FSADEW` `FSAALRM` 전압 색인 계열 `AMOD/ACHN` 등 | 판정 근거는 **원장 7·8장** (전량 귀속) |

**규격/구성 버전의 자기 선언 카드는 없다** — `CAMVER`(HW) · `CTRLxCFG`(FW/설정) · `DETID` · `CHMAP_*` 조합으로 파악한다 (원장 확인 요망 11).

## 6. MEF · Pipeline · Calibration 연동

raw 사용자를 위한 요점 — 상세와 LEECU 실행 목록은 **통합 문서** (Part 1 = C-항목, Part 2 = 정체성).

| 항목 | 요점 |
| --- | --- |
| 변환 하드 실패 | **`OBSERVAT` ↔ 파일명 불일치 하나뿐** — 나머지 결측은 조용히 기본값이 된다 |
| 조용한 오염 (위험) | `DATE-OBS` 없으면 변환 시각으로 대체 · `RA`/`DEC` 는 형식 유효한 기본 좌표 · `EXPTIME` 기본 0 — **결측을 sentinel 로 가리지 말 것** (5.0절) |
| MEF `UNIQNAME` | raw `UNIQNAME` 폐지로 공급원 변경 필요 (C-항목) — 하류 색인 키는 **`FILENAME`(+`ORIGNAME`)** |
| MEF `ORIGIN` | 파이프라인 산출물이므로 **상수 `'KASI'`** 가 맞다 (경미 C-항목) |
| amp `MODULE`/`CHANNEL` | converter 추정식이 실배선과 다르다 — **`CHMAP_*` + 4.5절 표** 기준 재정의 (C-11), `XTALKGROUP` 파생 포함 |
| MEF `UT`/`DARKTIME` | raw `TSHOPEN`/`DARKTIME` 미기재 — `DATE-OBS`/`EXPTIME` 에서 조립·파생으로 교체 (C-항목) |
| MEF `VOLTINFO`/`TELEMETRY` | raw `Cn_*` (5.6절)로 placeholder 대체 가능 (C-후보) |
| `LEDFLASH` | **단위가 [ms] 로 바뀌었다** — 레거시([s]) 값과 1000배 차이, comment 가 단위 명시. 하류 도구에 전파할 것 |
| `OVERSCNY` | 레거시와 뜻이 다르다 (가장자리 → 중앙) — 레거시 이름을 재사용하지 말 것 (ICD 개정 후보) |
| `CCDTEMP` | 평균 파생 → **대표 센서 실측**으로 의미 변경 — L1 `CARRY_KEYS` 이름은 불변 |
| `XTALKVER` `REFVER` `CATVER` | raw 미기재 · **L0 수록은 pipeline 팀 판단 · L1 필수** (1장 계층 규칙) |

## 7. 검증 체크리스트

| # | 검사 | 기준 |
| --- | --- | --- |
| 1 | 파일 구조 | single HDU · `BITPIX=16` · `BZERO=32768` · 19200×9400 · 2880 패딩 (3장) |
| 2 | 파일명 | 정규식 일치 · 6자리 zero-padding · pair 양쪽 존재 · `<SITE>`↔`OBSERVAT` 일치 (2.2절) |
| 3 | 카드 전량 | 견본 v1.0 대비 값 카드 135장 전량 존재, 카드 **형** 일치 (식별자 = 문자열) |
| 4 | 정체성 | `FILENAME`=실명 · `ORIGNAME` 존재 · 평시 두 값 동일 (2.3절) |
| 5 | Pair 규칙 | 상이 7장 / 나머지 동일 (5.9절) |
| 6 | geometry 선언 | `AMPNAX1 = PRESCNX+IMAGEX+OVRSCNX` · `AMPNAX2 = PRESCNY+IMAGEY+OVRSCNY` · `CHMAP` 불변식 (4.5절) |
| 7 | 포장 | flat/star 시험으로 4.3절 조항 준수 검증 (OI-3) |
| 8 | sentinel | 금지 카드(`DATE-OBS` 등)에 sentinel 없음 · HK sentinel `'-999.99'` / `'9.99e-9'` 만 사용 |

자동 검증 구현: `ics_sim/tests/test_raw_header.py` · `test_raw_pair.py` · `test_geometry_vs_converter.py`.

## 8. Open Items

| ID | 항목 | 내용 · 조치 |
| --- | --- | --- |
| OI-3 | 행 순서·독출 방향 실기 확인 | 4.3절 포장 조항의 준수 검증 (flat/star sequence). amp 별 물리 독출 방향 확정 → 4.5절 표에 열 추가 |
| OI-4 | 중앙 168행 분배 | 84/84 여부 timing script + bias 통계로 확정 (`MIDOSCT`/`MIDOSCB` 는 미도입 — 확정값은 규격에 기록) |
| OI-5 | Binning | 1×1 전용. `CCDXBIN`/`CCDYBIN` 2·3 reserved — 계획 확정 시 geometry 확장 |
| OI-7 | raw 무결성 | `CHECKSUM`/`DATASUM` 미도입 — 도입 여부 결정 대기 |
| OI-9 | 배선 실측 | 4.5절 표의 실기 대조 (`XTALKCAL=True` 전제조건). CCD 채널 라벨 ↔ Archon tap 대응은 STA 문서/Tom O'Brien 협의 |
| OI-13 | 셔터 상태 반영 지연 | `SHOPEN`+3초 재질의 시점에 AUX 상태기계가 넘어가 있는지 벤치 실측 (`aux_requery_after_shopen`) |
| OI-15 | **X overscan 패턴 4:4 vs 5:3** | 레거시 MEF `AMPSEC` 실측과 신규 전제의 상충 — 검증 표본(`KMTN.20260116.000001`) overscan 열 통계로 즉시 확인 가능 (4.1절) |
| OI-16 | Tapaculo 원값 포맷 | `FSATEMP`/`FSAHUM`(+`HEBOX`) 원값 포맷 확인 후 "원값 그대로 싣기"로 최종 확정 (5.8절) |
| OI-17 | e2v 데이터시트 대응 (**부분 종결** — 원전 확보 2026-08-22, 부록 A 신설) | 확인된 것: `A`/`D` = image section 명칭, 레지스터 E/F·G/H, OS1–16, prescan 27(레거시 `PRESCANX=27` 의 원전). **잔여**: ① `IMGSEC` 의 `B` 표기 해명 ② CCD 출력 채널(`M01` 등) ↔ OS 번호 대응 확정 ③ K·N 조가 M·T 조와 IMGSEC 체계가 다른 이유(180° 회전 장착 추정 — OI-15 와 연동) |
| OI-18 | NT 파일 `CCDTEMP` 귀속 | 대표 센서("M")가 NT 파일에서도 그대로인지 확인 (5.6절) |
| — | subframe/ROI | **이 규격은 전면 독출 전용** — 부분 독출은 원점 카드가 없어 표현 불가. 필요 시 별도 확장 (원장 10장 제기) |

해결된 구판 OI(1·2·6·8·10·11·12)의 경위는 archive 의 v1.2 9장.

## 9. 관련 문서

| 문서 | 위치 |
| --- | --- |
| 카드 판정 원장 | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.13.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.13.md) |
| MEF 파급 · 정체성 | [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.6.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.6.md) |
| L0 MEF ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` |
| MEF keyword 정의서 | `../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` |
| Converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) |
| 결정 기록 | `../project_management/governance/DECISION_LOG.md` |
| 신규 ICS 구현·개발 노트 | `../ics_sim/` · `../ics_sim/DevNote.md` |
| 구판 | `archive/KMT_CEU_Raw_FITS_Specification_v1.2.md` (구명 Pair_Spec) · 헤더 초안 이력은 운영자 외부 백업 |

## 10. Revision History

| Version | Date | Change |
| --- | --- | --- |
| v1.0~v1.2 | 2026-08-06 ~ 08-13 | 구판 "Raw FITS Pair 규격" — 이력은 archive 판 11장 |
| — | 2026-08-18 | 전면 재검토 개시 (⛔ 재작성중) — 검토는 키워드맵 v0.7 → 원장 v1.7~v1.13 사이클로 진행 |
| **v1.3** | **2026-08-22** | **재작성판 발행 + 문서명 변경**(Pair_Spec → Specification). 확인 요망 11건 전량 종결분 반영: 헤더 5장을 **초안 v1.0 pair(135 값 카드) 기준으로 전면 교체** — Detector 블록 타일 해부(`PRESCNX/Y`·`OVRSCNX/Y`·`CHMAP_*`) · `FILENAME`/`ORIGNAME` 정체성(D-016, `UNIQNAME`·`NAMECLSH`·`clash/`·`PAIRFILE`·`CTRLTAG` 폐지) · 컨트롤러 블록(`CTRLxID/SN/CFG` · `ICSBUILD` 신형식 · `RDMODE`) · HK 재구성(문자열 형 · sentinel `'-999.99'`/`'9.99e-9'` · `Cn_*`) · 돔 출처 TCS 편입 · `EXPTIME` 조건부 형 · `LEDFLASH` [ms]. **4.3 포장 규범 조항 신설**(`ROWORDR`/`OSCNPATT` 카드 대체, 고정 = `CAMVER`+`CTRLxCFG`) · **4.5 amp 전수 표 신설**(기계 사본 = 채널맵 v1.0). 규격 버전 카드 미도입 확정. XTALKVER 계층 규칙(raw/L0/L1) 명시. OI 재편(15~18 신설) |
| v1.3 | 2026-08-22 | 제자리 개정(발행 당일 보강): **부록 A 신설 — e2v CCD290-99 데이터시트(V2 2016-08, `__reference` 확보) 대응.** 4.5절 `IMGSEC` 의 `A`/`D` = image section 명칭 확인(`B` 는 원전에 없음 — 해명 잔여), 레지스터 1152 active + prescan 27 = 레거시 `PRESCANX=27` 의 원전 확인, 독출 방향 = 클럭 결선(ACF) 소관 확인. OI-17 부분 종결, K·N 회전 장착 추정을 OI-15 와 연동 |

## 부록 A. e2v CCD290-99 데이터시트 대응

원전: `__reference/CCD290-99 datasheet (V2 - Aug 2016).pdf` (e2v A1A-778871 Version 2). 이 규격의 값과 원전의 대응:

| 항목 | 데이터시트 | 이 규격 | 정합 |
| --- | --- | --- | --- |
| 픽셀 | 10 μm square, image area 9216 × 9232 | `PIXSIZE=10.0` · `CCDCOLS=9216`(=8×`IMAGEX`) · `CCDROWS=9232`(=2×`IMAGEY`) | ✓ |
| Image section | **A**(아래 half) · **D**(위 half), 각 9216 × 4616 | `IMAGEY=4616` · 4.2절 상·하 분할 · 4.5절 `IMGSEC` 의 `A`/`D` | ✓ |
| Register section | 1179 elements = **1152 active + 27 pre-scan** (아래 E/F · 위 G/H, 각 3구획) | `IMAGEX=1152`. **레거시 `PRESCANX=27` 의 원전이 이 27 이다** — 신규는 prescan 을 기록하지 않으므로 `PRESCNX=0` (tile 1200 = 1152 + `OVRSCNX` 48) | ✓ |
| 출력 | **OS1–OS8**(아래, Connector-1) · **OS9–OS16**(위, Connector-2), 각 출력에 dummy(DOS) 짝 — 차동 프리앰프용 | `NAMPDET=16`. `WBTYPE='STA Differential Board'`(MEF 쪽)가 dummy 출력 활용 구조 | ✓ |
| 독출 모드 | full-frame / **split full-frame** — 전송 방향은 클럭 결선으로 선택 (A→E · D→G 가 분할 독출, 역방향 가능) | 4.2절 상·하 동시 독출. **amp 별 물리 독출 방향은 데이터시트가 고정하지 않는다** — ACF(=`CTRLxCFG`) 소관, 실기 확인 OI-3 | ✓ (방향은 OI-3) |
| Dump drain | fixed-barrier dump drain (고속 폐기) | preheat/dump 운용은 timing script 소관 — raw 카드 없음 (`NPHLINES` 미도입, 원장 6장) | ✓ |

**IMGSEC 문자에 대한 판정** — 채널맵의 `A`/`D` 는 위 image section 명칭과 일치한다: M·T chip 은 `A-BOT`(섹션 A 가 프레임 아래)·`D-TOP`, K·N chip 은 `A-TOP`(섹션 A 가 프레임 **위**)·`B-BOT`. 섹션 A 가 위로 가는 배치는 **die 의 180° 회전 장착**을 시사하며, M·T 조와 K·N 조가 갈리는 것은 레거시 MEF `AMPSEC` 의 M/T=5:3 vs K/N=3:5 패턴(OI-15)과 같은 짝이다 — 두 관찰이 같은 원인(장착 방향)일 가능성을 실기에서 함께 확인할 것. **`B` 표기는 데이터시트에 없다**(image section 은 A·D 뿐, 레지스터는 E/F/G/H) — 원전 해명이 OI-17 의 잔여다.

# KMT-CEU Raw FITS Specification

**v1.8** · 2026-08-29 · **현행** — 2026-08-18~22 전면 재검토(확인 요망 11건 전량 종결 · D-016 등재)를 반영한 재작성판. v1.4 가 운영자 1~4장 검토 반영판, v1.5 가 5장(헤더 keyword) 검토 개시분이고, **v1.6 은 노출 정체성 카드를 개정한다** (`ORIGNAME` → **`EXPID`**). 구 문서명 "KMT-CEU Raw FITS Pair 규격"(v1.2, `archive/`)을 개명·대체한다. 이 문서를 **raw spec(로우 스펙)** 이라 부른다.  **v1.8 은 `OI-9` 를 폐기하고 `CTRLnCFG` 예시를 실제 ACF 이름 규칙에 맞춘다.**

| 연동 | 값 |
| --- | --- |
| 정본 헤더 견본 | [`KMTA.20260821.123456.MK.fits.header.v1.0.txt`](KMTA.20260821.123456.MK.fits.header.v1.0.txt) · [`…NT.fits.header.v1.0.txt`](KMTA.20260821.123456.NT.fits.header.v1.0.txt) — 5장 카드 전량의 **바이트 단위 견본**(각 **144 레코드 = 값 카드 131 + COMMENT 8 + END 1 + 공백 4**, 정확히 4×2880 = 11,520 바이트 — `END` 는 140번째이고 그 뒤 4장은 블록을 채우는 공백 레코드다). 메모장용 사본 `…_REFTEXT.txt` 는 카드마다 LF 를 넣고 끝에 `#EOF` 를 붙인 것으로, **LF 를 걷어내면 정본과 바이트 동일**하다 |
| 카드 판정 원장 (배경·경위) | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.15.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.15.md) — 이하 **원장**. 카드별 계승/개칭/폐지 근거, converter 대조, 레거시 123개 전량 귀속 |
| MEF·파이프라인 파급 | [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.7.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.7.md) — 이하 **통합 문서**. LEECU 전달용 C-항목·이름 대응 |
| 결정 기록 | `../project_management/governance/DECISION_LOG.md` — D-002(chip order) · D-010(Wrote 분리) · D-011(파일명) · D-012(백엔드 계약) · D-013(레거시 판정) · D-014(관측일) · D-015(사이트 판정) · **D-016(충돌·정체성)** |
| 연동 ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` (v4.1) |
| 연동 converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) |
| Amp 배선 맵 (기계 사본) | [`Detector_Ch_to_AmpID_Map_v1.1.txt`](Detector_Ch_to_AmpID_Map_v1.1.txt) — 4.5절 표의 기계 가독 정본. v1.0(`__reference/`)은 3자 채널 표기 · `IMGSEC:B-BOT` 판이고 **이 판이 대체한다** |
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
<SITE>.<YYYYMMDD>.<NNNNNN>.<DETID>.fits

  예:  KMTA.20260821.123456.MK.fits
       KMTA.20260821.123456.NT.fits
```

- `<SITE>` — 4자 대문자 사이트 코드, TC 텔레메트리 `TELID` 규약과 동일. **이 넷 밖의 값은 전부 `KMTK` 로 정규화**하고 경고를 남긴다. 실효 사이트는 호스트 IP 로 판정하며 판정이 설정을 이긴다 (D-015).

  | `<SITE>` | 사이트 | `OBSERVAT` | L0 MEF prefix |
  | --- | --- | --- | --- |
  | `KMTC` | CTIO | `CTIO` | `kmtc` |
  | `KMTS` | SAAO | `SAAO` | `kmts` |
  | `KMTA` | SSO | `SSO` | `kmta` |
  | `KMTK` | KASI | `KASI` | `kmtk` |

- `<YYYYMMDD>` — **그 사이트의 관측일** (D-014): UT 에 사이트별 보정을 더한 뒤 날짜만 취한다. 경계는 CTIO UT 16:30(`+7:30`) · SAAO UT 10:30(`−10:30`) · SSO UT 01:30(`−1:30`) · KMTK 보정 0. **검산 불변식: 세 경계가 모두 현지 12:30.** 구현은 "보정 후 날짜만 취하는 한 줄"이어야 한다 — 경계를 `if` 로 나열하면 off-by-one 이 1년에 몇 번만 드러난다. **`<YYYYMMDD>` 는 `DATE-OBS` 의 날짜와 일반적으로 다르며 그것이 의도다** — 둘을 같다고 가정하는 도구를 만들면 안 된다.
- `<NNNNNN>` — **6자리 고정폭, 0 좌측 패딩** 노출 번호. pair 양쪽 동일. converter 정규식(`^(KMTC|KMTS|KMTA|KMTK)\.(\d{8})\.(\d{6})\.MK\.fits$`)과 `find_pair()`(`.MK.fits`↔`.NT.fits` 치환)가 이 형식에 걸려 있다 — 자릿수 위반은 짝 탐색 실패 또는 fallback 경로다.
- `<DETID>` — **검출기 조 식별자** `MK` / `NT`. 값은 헤더 `DETID` 카드와 **같다** (5.2절) — 파일명에서 이 필드만 pair 양쪽이 다르다. 이 규격에서 "`FILENAME` 의 `DETID` 필드를 뗀 값" 은 이 넷째 필드를 제거한 `<SITE>.<YYYYMMDD>.<NNNNNN>` 를 뜻하며, 그것이 `EXPID` 와 같은 형식이다 (2.3절 충돌 판별).
- **파일명 `<SITE>` 와 헤더 `OBSERVAT` 는 일치해야 한다** — converter 가 교차 검증하며 **불일치는 이 규격에서 유일한 하드 실패**다 (5.3절).

### 2.3 노출 번호와 이름 충돌 처리 (D-016)

**충돌 시 격리·개명 대신 노출 번호를 증가시켜 저장한다.** 정본은 DECISION_LOG **D-016** (Accepted, 2026-08-22).

1. 번호 공간은 **`000000`–`999999`** — 6자리를 전부 쓰며 카운터는 1000000 도달 시 `000000` 으로 되감는다 (**D-018** — 구 `099999` 상한을 대체한다).
2. 쓰기 전에 후보 N 의 **MK·NT 두 경로를 모두 선검사** — 점유 시 N+1 재검사(999999 넘으면 000000). **+1 이 1000000회(공간 한 바퀴)를 초과하면 멈추고 ERROR, 저장하지 않는다.** 실패 조건은 이것 하나뿐이다.
3. 확정 N 으로 **카운터를 동기화**한다 (평소 영속화 경로 그대로, 점프는 경고 로그).
4. **정체성 카드 둘을 모든 파일에 항상 기록한다:**

   ```text
   FILENAME= 'KMTA.20260821.123456.MK' / FITS file name as written to storage
   EXPID   = 'KMTA.20260821.123450' / Exposure identifier assigned by ICS counter
   ```

   `FILENAME` = **실제 저장명**(확장자 없음) — 아카이브·DTS·색인의 유일 키. `EXPID` = **카운터가 처음 배정한 노출 식별자**로, `<SITE>.<YYYYMMDD>.<NNNNNN>` 이고 **`DETID` 필드(`.MK`/`.NT`)가 없다.**

   - **충돌 신호 = `FILENAME` 의 `DETID` 필드를 뗀 값 ≠ `EXPID`** (값 비교 — 카드 존재가 아니다). `EXPID` 결측은 충돌이 아니라 헤더 결함으로 분류한다.
   - **`EXPID` 는 pair 양쪽에서 같다** — `DETID` 필드가 없기 때문이다. 그래서 짝을 잇는 **단일 키**가 되고, `PAIRFILE`(폐지)이 하려던 일을 카드 추가 없이 해낸다 (5.9절).
   - 둘 다 **FITS 문자열 카드 필수** — 숫자 카드는 zero-padding 을 파괴한다 (5.0절). `EXPID` 값이 `<SITE>` 접두로 시작하는 것이 그 위반을 **구조적으로** 막는다(숫자로 읽힐 여지가 없다).
5. 충돌 증가는 pair 동시이므로 **짝 이름은 `FILENAME` 의 `DETID` 필드(`.MK`↔`.NT`) 치환으로 항상 유도**된다 — `PAIRFILE`·`CTRLTAG` 카드는 없다.
   ⚠️ OBSAgent 통보(`Wrote`)의 `LASTFILE` 은 CCD 단위 **논리 이름**이라 **실재 경로가 아니다**(D-010) — 아카이브·DTS·색인 도구는 반드시 이 카드(`FILENAME`)를 근거로 삼는다. 통보 규약 자체는 취득 SW 소관이다(`../ics_sim/DevNote.md` 3.2).
6. 재저장(유령 중복)은 fail-open — **raw 헤더 층 필터(`FILENAME` ≠ `EXPID`)가 거른다는 것이 하류 도구 요구사항**이다. MEF 층 필터가 필요해지면 `EXPID` pass-through 를 C-항목으로 추가한다 (통합 문서 §1).
7. 전제: 저장 디렉토리의 쓰기 주체는 **ICS 하나뿐**이다.

> 폐지: `UNIQNAME` · `NAMECLSH` · `clash/` 격리 · `PAIRFILE` · `CTRLTAG` · `EXPNUM` · **`ORIGNAME`**(v1.6 — `EXPID` 가 대체). 경위는 원장 8.2절, 통합 문서 Part 2.
>
> ⚠️ **`EXPID` 는 한때 폐지됐다가 v1.6 에서 되살아난 이름이다** (구판 v1.2 2.3.1절에서 2026-08-12 에 삭제). 그때의 삭제 근거 셋 중 둘은 이미 해소됐다 — **중복 제거**(당시 `FILENAME`·`UNIQNAME`·`EXPID`·`EXPNUM` 넷이 같은 정보를 담았는데, `UNIQNAME`·`EXPNUM` 이 폐지되고 이번엔 `ORIGNAME` 을 **대체**하므로 카드 수가 늘지 않는다)와 **MEF 목적지 중복**(`UNIQNAME` 폐지로 소멸). 남은 근거 "이 저장소가 새로 만든 낱말" 은 유효하나, **pair 를 잇는 단일 키**라는 이득이 그것을 넘는다고 판단했다. ⚠️ 당시 실제 사고(`EXPID` 가 실수 카드로 저장돼 zero-padding 파괴)는 **값에 `<SITE>` 접두를 두어 구조적으로 막았다** — 5.0절 형 규칙과 이중이다.

### 2.4 크기

| 항목 | 값 |
| --- | ---: |
| 파일당 픽셀 | 19200 × 9400 = 180,480,000 |
| 파일당 데이터 | ≈ 344.2 MiB |
| Pair 1쌍 | ≈ 688.5 MiB |

raw pair 픽셀 총수 − L0 MEF amp 픽셀 총수(64 × 1200 × 4616) = **정확히 middle Y overscan 블록**(2 × 19200 × 168 = 6,451,200). 이 등식이 깨지면 4장 해석이 어긋난 것이다.

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

X overscan 의 좌우는 strip 으로 정해진다 — **`RRRRLLLL`** (strip 1–4 = 오른쪽 48, strip 5–8 = 왼쪽 48). **실제 획득 자료 육안 확인으로 확정**(운영자, 2026-08-22).

### 4.2 Y 방향 — 상·하 분할 독출과 중앙 overscan

```text
Y:  1 ..... 4616 | 4617 .. 4700 | 4701 .. 4784 | 4785 ..... 9400
    BOT active     BOT Y ovrscn   TOP Y ovrscn   TOP active
    (4616 rows)    (84 rows)      (84 rows)      (4616 rows)
                 | middle Y overscan (168 rows)|
```

- CCD 1개(9232행)를 8개 strip 이 상·하 양 끝에서 동시에 읽는다 — X tile 1개 = amp 2개(TOP/BOT), 파일 1개 = chip 2 × amp 16 = **amp 32개**.
- 중앙 168행은 양 half 의 active 를 다 읽은 뒤 추가 clocking 된 Y overscan 이며, **타일 규약상 half 당 84행**이다 (`AMPNAX2 = PRESCNY + IMAGEY + OVRSCNY` = 0+4616+84, ×2 half). 물리 clocking 이 정확히 84/84 로 갈리는지는 실측 확인 대상이다 (OI-4).
- ⚠️ **레거시 `OVERSCNY` 와 뜻이 다르다** — 레거시는 가장자리(값 0), 신규는 **영상 중앙**. 그래서 이름을 `OVRSCNY` 로 갈랐다 (원장 8장). 이름만 보고 "위쪽 N행 자르기"를 하는 도구는 active 픽셀을 지운다.

### 4.3 포장 규범 조항 (normative)

> **raw 프레임은 검출기 공간 순서로 완전 정렬되어 저장된다** — X 는 타일 내·타일 간 모두 CCD 좌표 오름차순, Y 는 양 half 모두 CCD 좌표 오름차순(TOP half 는 독출 순서가 아니라 **CCD 좌표 순서**로 기록 — raw row 4785 ↔ CCD row 4617).

- 이것은 관찰이 아니라 **요구사항**이다. 구판의 `ROWORDR`·`OSCNPATT` 카드는 폐지되고 이 조항으로 이관됐다 (원장 7장).
- **고정 대상 = `CAMVER`(HW) + `CTRLxCFG`(FW/설정)** — 포장이 바뀌는 원인은 HW·설정 변경뿐이므로 그 둘의 범프가 판별 신호다. 별도 규격 버전 카드(`RAWVER`)는 두지 않는다 (원장 확인 요망 11, 5.10절).
- flat/star sequence 시험(OI-3)은 이 조항의 **준수 검증**이다. 취득 SW 쪽 상시 방어는 `ics_sim/tests/test_geometry_vs_converter.py` (코드-대-코드 대조).

### 4.4 amp 1개의 raw 좌표

| AmpID 범위 (MEF AmpID — 4.5절) | half | raw Y 구간 | CCD Y 구간 |
| --- | :---: | --- | --- |
| 01–08 · 17–24 · 33–40 · 49–56 | TOP | 4785 : 9400 | 4617 : 9232 |
| 09–16 · 25–32 · 41–48 · 57–64 | BOT | 1 : 4616 | 1 : 4616 |

**half 판정**: `((AmpID − 1) // 8)` 이 짝수면 TOP, 홀수면 BOT — chip 마다 8개씩 TOP/BOT 이 교대한다. chip 내 strip 은 `((AmpID − 1) mod 8) + 1`, tile X 구간은 `X0 + (s−1)·1200 + 1 … X0 + s·1200` (X0 = 그 chip 의 시작 offset: 첫 chip 0, 둘째 chip 9600).

### 4.5 Amp 전수 표 (64행)

**기계 가독 정본은 [`Detector_Ch_to_AmpID_Map_v1.1.txt`](Detector_Ch_to_AmpID_Map_v1.1.txt)** 이고 아래 표는 그 전개다. 헤더의 `CHMAP_LT/LB/RT/RB` 카드(5.2절)는 이 표의 CCD 출력 채널 열을 raw X 오름차순으로 투영한 것이다.

| Raw file | 사분면 | Port | CCD 출력 채널 (raw X 오름차순, tile 1→8) | IMGSEC | MEF AmpID | 검증 상태 |
| --- | --- | :---: | --- | :---: | --- | --- |
| MK | 좌반 TOP (`CHMAP_LT`) | A | MD16, MD15, MD14, MD13, MD12, MD11, MD10, MD09 | D-TOP | 01–08 | 배선표 v1.0 (2026-08-21 검토 완료) |
| MK | 좌반 BOT (`CHMAP_LB`) | A | MA01, MA02, MA03, MA04, MA05, MA06, MA07, MA08 | A-BOT | 09–16 | 〃 |
| MK | 우반 TOP (`CHMAP_RT`) | B | KA08, KA07, KA06, KA05, KA04, KA03, KA02, KA01 | A-TOP | 17–24 | 〃 |
| MK | 우반 BOT (`CHMAP_RB`) | B | KD09, KD10, KD11, KD12, KD13, KD14, KD15, KD16 | D-BOT | 25–32 | 〃 |
| NT | 좌반 TOP (`CHMAP_LT`) | A | NA08, NA07, NA06, NA05, NA04, NA03, NA02, NA01 | A-TOP | 33–40 | 〃 |
| NT | 좌반 BOT (`CHMAP_LB`) | A | ND09, ND10, ND11, ND12, ND13, ND14, ND15, ND16 | D-BOT | 41–48 | 〃 |
| NT | 우반 TOP (`CHMAP_RT`) | B | TD16, TD15, TD14, TD13, TD12, TD11, TD10, TD09 | D-TOP | 49–56 | 〃 |
| NT | 우반 BOT (`CHMAP_RB`) | B | TA01, TA02, TA03, TA04, TA05, TA06, TA07, TA08 | A-BOT | 57–64 | 〃 |

- **토큰 형식 `<chip><A|D><nn>` — 4자 고정** (운영자 확정 2026-08-25). 가운데 글자는 채널 번호에서 결정된다: **01–08 = `A` · 09–16 = `D`** (e2v image section, 부록 A). 종전 3자 표기(`M16`)를 대체한다.
- 검증 불변식: 카드당 8토큰 · 토큰 4자 · `CHMAP_L*` 첫 글자 = `DETID[0]` · `CHMAP_R*` 첫 글자 = `DETID[1]` · 가운데 글자가 번호 규칙과 일치 · chip 당 채널 01–16 전량 · pair 합계 64.
- **TOP/BOT 대역이 chip 마다 반대**다 (M: TOP=16–09 / K: TOP=08–01 등) — converter 현행 추정식(`MODULE`/`CHANNEL`)과 다르므로 MEF 쪽 재정의가 C-11 이다 (통합 문서 §1).
- `IMGSEC` 의 `A`/`D` 는 **e2v 데이터시트의 image section 명칭으로 확인**됐다 — A = 아래 half(레지스터 E/F, OS1–8), D = 위 half(레지스터 G/H, OS9–16). 부록 A 참조. ✅ **구 `B-BOT` 은 `D-BOT` 으로 정정됐다 (운영자 확정 2026-08-25 — OI-17 잔여 ① 종결).** 채널↔OS 대응 확정(잔여 ② 종결)으로 `채널 09–16 = OS9–16 = 위 half = 섹션 D` 가 데이터시트까지 이어지고, 데이터시트에 `B` 섹션이 없으므로 `B` 는 **원전 없는 표기**였다(부록 A). 이제 `IMGSEC` 은 **앞 글자 = image section(A·D) · 뒤 = raw 타일 위치(TOP·BOT)** 로 두 축이 깨끗하게 분리된다. `D` 가 TOP·BOT 양쪽에 나타나는 것은 모순이 아니다 — 위 half 가 chip 장착 방향에 따라 raw 아래쪽에 놓이기 때문이고, **그 방향이 갈리는 이유(K·N 조 180° 회전 장착)가 OI-17 의 마지막 잔여 ③** 이다. amp 별 물리 독출 방향은 클럭 결선(ACF) 소관이라 실기 확인 대상이다 (OI-3).

## 5. 헤더 Keyword 규격

**정본 견본은 헤더 초안 v1.0 pair** — 카드 순서·comment·패딩까지 바이트 단위 기준이다. 이 장의 표는 그 견본의 전 카드(**값 131장** — v1.5 에서 HK 4장 폐지, v1.6 에서 `ORIGNAME`→`EXPID` 대체라 장수는 그대로)를 블록 순서대로 규정한다. 카드별 판정 경위는 원장 3·6·7·8장.

### 5.0 작성 정책

| 상태 | 의미 |
| --- | --- |
| 필수 | 없으면 L0 MEF 가 틀린 값을 갖거나 변환이 실패한다 — 5장 전 카드가 원칙적으로 필수다 |

| 형 | 표기 | Sentinel (값 없음) |
| --- | --- | --- |
| 문자열 `S` | FITS 문자열 카드 | `'NC'` (레거시 관례) |
| 정수 `I` | | `-1` |
| 실수 `R` | | `-999.0` |
| **HK 온도·습도** | **문자열** — 부호 포함 소수 2자리(`'-101.23'`/`'+16.78'`), FSA 2장은 ENS식(소수 1자리) | **`'-999.99'` 단일값** (⚠️ **`Cn_*` 나열 카드 안의 결측 자리는 `NC`** — 5.6.1절) — 온도로는 불가능, 습도로는 음수 (기각 사유: 원장 v1.12 changelog) |
| `DEWPRES` | 문자열 `x.xxe-x` [torr] | `'9.99e-9'` (0·음수·비수치·범위 밖 전부) |

**카드 폭 초과 시 — comment 를 뒤에서 자른다** (운영자 확정 2026-08-26).

FITS 카드는 80자 고정이다. 값이 길어 `KEY = '값' / comment` 가 80자를 넘으면 **comment 를 뒤에서 잘라** 80자를 맞춘다 — **값은 자르지 않는다.**

- **값이 자료이고 comment 는 설명이기 때문이다.** 특히 `Cn_*` 나열 카드는 **자리가 곧 항목**이라(5.6.1절) 값이 잘리면 뒤 항목이 통째로 사라지는데, 읽는 쪽은 그 사실을 알 방법이 없다. comment 가 잘리는 것은 눈에 보이는 손실이고, 자리 뜻의 정본은 어차피 **5.6.1절 표**다.
- comment 를 전부 잘라도 넘치면(값만으로 68자 초과) 그때는 값을 자르고 **경고를 남긴다** — 규격 위반 상태이므로 조용히 지나가면 안 된다. `Cn_*` 는 결측 자리를 `NC` 로 두어 이 경우가 실제로 오지 않게 했다 (5.6.1절).

공통 규칙:

- keyword 8자 이내, `HIERARCH` 금지. 시각은 전부 UTC (`TIMESYS='UTC'` 선언, 값에 `Z` 를 붙이지 않는다 — 예외는 `ICSBUILD`).
- **식별자 keyword 는 문자열 카드 필수** (`FILENAME` `EXPID` `OBSERVAT` `ORIGIN` `DETID` 등) — 숫자 카드는 zero-padding 을 파괴한다 (`'…000010'` → `…00001`). 검사는 값이 아니라 **카드의 형**을 본다.
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
| `FPAID` | S | 검출기 조립 정체 — 사이트별 상수, **5.3.1절 표** (견본 = SSO 이므로 `'FPA#1'`) | ICS INI |
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
| `CHMAP_LT` `CHMAP_LB` `CHMAP_RT` `CHMAP_RB` | S | CCD 출력 채널 8토큰, 토큰 형식 `<chip><A\|D><nn>`(4자), raw X 오름차순 (4.5절 표 — pair 상이) | ICS code |

축별 합 불변식이 comment 에 자체 문서화된다. `AMPNAX1/2` 값이 바뀌는 것은 geometry 변경 = `CAMVER`/`CTRLxCFG` 범프 사안 (4.3절).

### 5.3 Observatory (7장)

| Keyword | 형 | 값 | 출처 |
| --- | :---: | --- | --- |
| `ORIGIN` | S | **"이 파일이 생성된 곳"** — `SSO`/`CTIO`/`SAAO`/`KASI` (KASI 파이프라인 산출물도 `KASI` — MEF 는 상수화 C-항목). **D-017 이후 `OBSERVAT` 와 값이 같다** — 뜻은 다르지만(생성처 vs 관측소) 네 자리 모두 일치한다 | ICS INI (사이트 유도) |
| `OBSERVAT` | S | `CTIO`/`SSO`/`SAAO`/`KASI` (D-017 — `TESTBED` 폐지) — **파일명 `<SITE>` 와 교차 검증, 불일치는 변환 오류** (유일한 하드 실패) | ICS INI |
| `TELESCOP` | S | 사이트별 상수 — **5.3.1절 표** | ICS INI |
| `LATITUDE` | S | `'-31:16:24'` 등 — 문자열 그대로 (정규화 금지) | ICS INI |
| `LONGITUD` | S | **서경** `[deg W]` — SSO `'210:56:08'` 등. 동경으로 고치면 부호 뒤집힌 좌표가 박힌다 | ICS INI |
| `ELEVATIO` | I | 사이트 고도 [m] | ICS INI |
| `OBSERVER` | S | `'KMTNetOp'`* / user input | ICS code* / user input |

측지 실측값·서경 규약 검증은 구판 OI-11 기록(archive v1.2 9장) 참조. KASI 는 좌표를 **일부러 비워** sentinel 을 싣는다.

#### 5.3.1 사이트별 상수 (normative)

사이트가 정해지면 아래 다섯 값이 **기본값으로 함께 정해진다** — ICS 는 사이트 하나에서 전부 유도한다. 다만 **ICS INI 에 값이 있으면 그쪽이 이긴다**(`[site.<이름>]`·`[site]` — 현장이 정본이라는 기존 규칙, `rawhdr.site_header()`). 표는 설정이 없을 때의 기본값이자 대조 기준이다.

| 사이트 | `<SITE>` (파일명) | `OBSERVAT` | `ORIGIN` | `TELESCOP` | `FPAID` |
| --- | :---: | :---: | :---: | --- | :---: |
| CTIO | `KMTC` | `CTIO` | `CTIO` | `'KMTNet 1.6m #1'` | `'FPA#2'` |
| SSO | `KMTA` | `SSO` | `SSO` | `'KMTNet 1.6m #3'` | `'FPA#1'` |
| SAAO | `KMTS` | `SAAO` | `SAAO` | `'KMTNet 1.6m #2'` | `'FPA#3'` |
| KASI | `KMTK` | `KASI` | `KASI` | `'KMTNet 1.6m #0'` | `'FPA#0'` |

> ⚠️ **망원경 번호와 FPA 번호는 일부러 다르다 — 맞추려 들면 안 된다.** CTIO 는 망원경 `#1` 인데 FPA 는 `#2`, SSO 는 망원경 `#3` 인데 FPA 는 `#1`, SAAO 는 망원경 `#2` 인데 FPA 는 `#3` 이다. **세 사이트 모두 어긋난다.** 망원경 번호는 설치 순서, `FPAID` 는 **검출기 조립체 자체의 정체**이고 조립체는 사이트 간 이동이 가능하므로 두 번호가 일치할 이유가 없다. 어긋난 것을 오타로 보고 "고치면" 자료의 검출기 귀속이 통째로 틀어진다.

- `FPA#0` 은 KASI(실험실) 조립체다 — 관측소 셋이 `#1`–`#3` 을 쓰므로 `0` 이 남는 자리다.
- **KASI 는 망원경·FPA 둘 다 `#0`** 이다(운영자 확정 2026-08-25) — 관측소 셋이 `#1`–`#3` 을 쓰므로 `0` 이 남는 자리다. 종전 테스트베드 값 `'Sim'` 을 대체한다. ⚠️ **KASI 에서 두 번호가 일치하는 것은 우연이다** — 위 경고대로 관측소 셋은 전부 어긋난다. `#0`/`#0` 을 보고 "원래 같은 번호"로 읽으면 안 된다.
- **`TELESCOP` 의 SSO 값은 레거시 실측으로 확인됐다** — `__reference/Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt` 가 `OBSERVAT='SSO'` 와 `TELESCOP='KMTNet 1.6m #3'` 을 함께 싣는다. 저장소에 실측이 있는 사이트는 SSO 뿐이고 CTIO·SAAO·KASI 값은 운영자 제시분이다.
- `<SITE>`↔`OBSERVAT` 교차 검증(2.2절)은 이 표의 두 열이 근거다 — **불일치가 이 규격의 유일한 하드 실패**다.

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
| `EXPID` | S | 카운터 최초 배정 노출 식별자 `<SITE>.<YYYYMMDD>.<NNNNNN>` — **`DETID` 필드 없음 → pair 동일**. `FILENAME` 의 `DETID` 필드를 뗀 값과 불일치 = 충돌 신호 (2.3절) | ICS code |

### 5.5 Controller · ICS (9장)

| Keyword | 형 | 값 | 출처 |
| --- | :---: | --- | --- |
| `DATASRC` | S | `ARCHON_SCIENCE` / `ARCHON_GUIDE` / `SIM` — **시뮬 프레임 오인을 막는 유일한 카드** + 작성 프로그램 식별 | ICS code |
| `CTRL1ID` `CTRL1SN` | S | `'<SITE>-SCI-101'` (ID 숫자 = IP) · `'STA-0288'` — 실값 원자료 `__reference/Archon_Unit_Info.txt` | ICS INI |
| `CTRL1CFG` | S | 적용된 Archon 설정 파일명 (`'KMTA_SCI_101_STA0288_R2608_MK'`) — **폴더 경로와 확장자(`.acf`/`.cfg`)를 뗀 이름**이다(v1.8). **타이밍·바이어스·클럭 버전 문자열은 전부 이 파일로 귀속** (개별 버전 카드 없음) | ICS INI |
| `CTRL2ID` `CTRL2SN` `CTRL2CFG` | S | 컨트롤러 2 (`-102` · `'STA-0289'` · …) — **두 대분을 양쪽 파일에 모두 싣는다** (converter 가 MK 만 읽으므로) | ICS INI |
| `ICSBUILD` | S | **`v<버전>:<빌드일시(UTC)Z>`** (예 `'v0.1.2:2026-08-21T18:09Z'`) — 프로그램명 없음(식별은 `DATASRC`), 끝의 `Z` 는 의도적 | ICS code |
| `RDMODE` | S | 독출 모드 (`'NORMAL'` 등) — MEF `READMODE`(`'64AMP'`, 구조 선언)와 **별개** | ICS INI / ICS code |

guide FITS 는 `CTRL1xx` 한 벌만 싣고, 컨트롤러 수가 늘면 `CTRLnxx` 벌이 늘어나는 확장 규약이다.

### 5.6 Camera System House Keeping (14장)

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
| `C1_TEMP` `C1_VOLT` `C1_CURR` | 컨트롤러 1 모듈별 온도/전압/전류 — **`\|` 구분 나열, 자리 = 항목**. 자리 순서 명세는 **5.6.1절** | Archon |
| `C2_TEMP` `C2_VOLT` `C2_CURR` | 컨트롤러 2 동형 — 자리 순서 동일 | Archon |

`Cn_*` 는 MEF `VOLTINFO`/`TELEMETRY` 를 실측으로 채울 원천이다 (C-후보, 통합 문서 §1). NT 파일의 `CCDTEMP` 대표 센서 귀속은 확인 항목 (8장).

#### 5.6.1 `Cn_*` 자리 순서 (명세)

`Cn_TEMP` · `Cn_VOLT` · `Cn_CURR` 은 **파이프(`|`)로 구분한 나열**이고 **자리(토큰 위치) 자체가 항목을 뜻한다** — 값에 이름표가 없으므로 읽는 쪽은 아래 표로만 해석한다. 자리 순서는 규격 사항이며, 모듈 구성이 바뀌면 `CAMVER`(HW) · `CTRLnCFG`(설정) 범프로 드러난다 (4.3절 포장 규범 조항과 같은 원리).

**`Cn_TEMP` — Archon 모듈 온도, science 컨트롤러 10자리** (n = 1 · 2)

| 자리 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 항목 | `Backplane` | `Mod1:LVDS` | `Mod2:Driver` | `Mod3:Driver` | `Mod4:LVXBias` | `Mod5:ADM` | `Mod8:ADM` | `Mod9:HVYBias` | `Mod10:Driver` | `Mod11:Driver` |

`Mod<n>` = Archon 백플레인 **모듈** `n` (`Mod` = Module), 콜론 뒤는 모듈 종류. 1번 자리 `Backplane` 만 모듈 번호 체계 밖이다. **목록에 없는 모듈(6 · 7 · 12)은 자리를 차지하지 않는다** — 자리 수는 장착·보고되는 모듈 수를 따르므로 자리 수 자체가 구성 판별에 쓰인다.

**`Cn_VOLT` · `Cn_CURR` — 전원 레일 7자리** (두 카드 같은 순서)

| 자리 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 레일 | P2V5 | P5V | P6V | N6V | P17V | N17V | P35V |

**구분자와 결측 자리 (운영자 확정 2026-08-26)**

- **구분자는 파이프(`|`) 다** — 공백 하나였던 것을 바꿨다. 값에 이름표가 없어 경계를 눈으로 세야 하는데, 음수가 섞이면(`16.956 -17.067 35.089`) 공백만으로는 갈리지 않는다. **폭 비용은 없다**(구분자는 어느 쪽이든 1자). 구분자 뒤에 공백을 넣지 않는다 — 10자리에서 9자가 늘어 폭을 넘긴다.
  - ⚠️ **슬래시(`/`)는 쓰지 않는다** — FITS 의 comment 구분자와 같은 글자다. 인용부호 안이라 표준 파서(astropy·cfitsio)는 값을 온전히 읽지만, **인용부호를 먼저 찾지 않는 도구**(`awk -F'/'`·정규식 절단)에서는 값이 첫 슬래시에서 잘린다. 견본은 사람이 눈으로 보고 grep 하는 바이트 정본이므로 그 위험을 지지 않는다.
  - 마크다운 문서의 **표 안에서 인용할 때만** `\|` 로 이스케이프한다 — 카드에 실리는 값은 순수한 `|` 다.
- **결측 자리는 `NC`** 다 — 5.0절의 문자열 sentinel 그대로다. 단일 HK 온도 카드(`CCDTEMP` 등)의 `'-999.99'` 와 **다르다**: 나열 카드에서 7자짜리 sentinel 이 열 자리를 채우면 79자가 되어 카드 폭을 크게 넘긴다. `NC` 면 29자로 들어간다. **실기에서 전 자리가 결측인 경우(STATUS 무응답·미장착 모듈)는 드물지 않다.**
- **자리는 비우지 않는다** — 결측이어도 `NC` 로 자리를 채운다. 건너뛰면 뒤 항목이 앞으로 당겨져 읽는 쪽이 구분할 방법이 없다.

    C1_TEMP = '40.1|41.2|42.3|43.4|44.5|45.6|46.7|47.8|48.9|49.0' / Ctrl-1 T[C]
    C1_VOLT = '2.512|5.023|5.834|-5.945|16.956|-17.067|35.089'    / Ctrl-1 V[V]
    C1_TEMP = 'NC|NC|NC|NC|NC|NC|NC|NC|NC|NC'                     / Ctrl-1 T[C]   (전 자리 결측)

**guide 컨트롤러**(`DATASRC = 'ARCHON_GUIDE'`)는 모듈 구성이 달라 `C1_TEMP` 가 **8자리**다 — Backplane · Mod3 Driver · Mod4 Driver · Mod5 AD · Mod6 AD · Mod7 HeaterX · Mod9 HVYBias · Mod10 HeaterX. 전원 레일 7자리는 science 와 같다. ⚠️ guide 순서는 **원장 7장 기재분이고 실기 대조 전이다** (OI-19).

> **표기 체계 (운영자 확정 2026-08-25)** — 종전 표기 `S<n>`(Slot)을 **`Mod<n>`(Module)** 로 바꿨다. Archon 백플레인의 그 자리를 가리키는 정확한 이름이 모듈이기 때문이다. 2번 자리의 `M1` 은 **`Mod1` 의 오타였다**(운영자 확인) — 다른 체계가 아니라 같은 모듈 번호이고, 원장 7장의 "Slot1 LVDS" 와도 같은 자리를 가리킨다. **이로써 열 자리 중 `Backplane` 을 뺀 아홉이 모두 `Mod<n>` 한 체계로 통일됐다.** 자리 순서 자체에는 처음부터 이견이 없었다.

### 5.7 TCS Information and Status (27장)

TCS 중계값은 문자열로 싣는다 (레거시 계승). 시각 카드는 `Z` 없이 (`TCSTIME` 이 시각계 선언).

| Keyword | 값 | 출처 |
| --- | --- | --- |
| `TCSLINK` | `Up` / `Idle` / `Down` | TCS relay |
| `TCSARC` | `Enabled` 등 — 링크 자동복구 모드 | TCS relay |
| `TCSQDATE` `TCSUDATE` | 마지막 TCS 질의/갱신 UTC (밀리초) — 순서 규약은 **5.7.1절** | TCS relay |
| `TCSTIME` | TCS 가 보고한 time system (`'UTC'`) — `TIMESYS`(ICS)와 분리 | TCS relay |
| `RADECSYS` | `'ICRS'` | TCS relay |
| `RA` `DEC` `EQUINOX` `HA` `ST` `SECZ` `ALT` `AZ` | 포인팅 (`'hh:mm:ss.ss'` 등 레거시 형식) | TCS relay |
| `TCSDRIVE` `TELMOVE` | 구동/모션 상태 — **`TCSDRIVE`(8자)로 쓴다** (converter 우선 탐색 이름) | TCS relay |
| `DSSTAT` `DSUP` `DSLW` `DSSAF` `DSAUTO` `DSALT` `DSAZ` `DSTELALT` `DSTELAZ` | 돔 셔터·지향 — **newTCS 편입으로 출처가 TCS 계통** (원장 3.6절). `DSTELALT` 는 레거시 `DSTEL` 의 개칭 — 중계 필드명이 무엇이든 ICS 가 이 카드명으로 싣는다 | TCS relay or REDIS |
| `DALTERR` `DAZERR` | 돔–망원경 지향차 [deg] | ICS calculation |

#### 5.7.1 `QDATE` / `UDATE` 순서 규약 (normative)

`TCSQDATE`·`TCSUDATE`·`AUXQDATE`·`AUXUDATE` 는 **ICS 가 만드는 값이 아니라 TC(TCSAgent · AUXAgent) 응답 필드를 그대로 중계한 것**이다. ICS 가 직접 채우는 경우는 TC 무응답 폴백(`tc_timeout_mode=canned`)뿐이다. 따라서 아래 부등식은 ICS 가 강제하는 규칙이 아니라 **TC 의 스탬프 방식에서 따라 나오는 성질**이며, raw 를 읽는 쪽은 이 순서를 전제해도 된다.

**두 시각의 정의** — TC 원전 주석(`TCSAgent/TCSAgent.latest/KMTNet/commands.c:1553` · `:2902`)

| 카드 | 원전 표현 | 스탬프 시점 |
| --- | --- | --- |
| `*QDATE` | query time | ICS 의 질의를 받아 **TC 가 응답을 조립하는 순간**의 현재 UTC |
| `*UDATE` | updated time | TC 가 망원경·AUX 로부터 **텔레메트리 패킷을 마지막으로 받은** 시각 |

**(a) `UDATE` ≤ `QDATE`** — `UDATE` 는 이미 받아 둔 패킷의 시각이고 `QDATE` 는 그 값을 꺼내 응답을 만드는 시각이므로 **구조적으로 뒤집힐 수 없다**. 두 값의 차가 곧 헤더에 실린 TCS/AUX 값의 **나이(staleness)** 다. 레거시 실측(`KMTNk.20170209.044131`)에서 AUX 98 ms · TCS 703 ms 였다.

**(b) 기준은 `QDATE`** 다. `UDATE` 는 TC 의 폴링 주기에 딸린 값이라 노출과 직접 묶이지 않는다 — 노출과의 관계를 따질 때는 `QDATE` 만 본다.

**(c) `QDATE` 의 자리는 `DATE-OBS`(= ICS 가 `SHOPEN` 을 지시한 시각, 5.4절) 전후**이고 경로에 따라 앞뒤가 갈린다.

| 경로 | `TCSQDATE` | `AUXQDATE` |
| --- | --- | --- |
| **DARK / BIAS** (셔터 안 엶) | ERASE 단계 질의 → **`< DATE-OBS`** | 노출 개시 **직전** 질의 → **`< DATE-OBS`** |
| **셔터 노출**, `EXPTIME > 1 s` | 위와 같음 → **`< DATE-OBS`** | `SHOPEN`+**1 s** 재질의 → **`> DATE-OBS`** |
| **셔터 노출**, `EXPTIME ≤ 1 s` | 위와 같음 → **`< DATE-OBS`** | 재질의 없음(개시 직전 값 유지) → **`< DATE-OBS`** |

셔터 노출에서 AUX 를 다시 묻는 것은 블레이드가 움직일 시간을 주기 위해서다 — `SHUTTER` 는 `SHUTOP` 의 순수 함수라(5.8절) 개시 직전 값은 아직 `CLOSED` 다. **노출이 재질의 시점보다 짧으면 재질의하지 않는다**: 셔터가 이미 닫힌 뒤의 값을 노출 중 값으로 싣게 되기 때문이다. 지연은 ICS INI 의 `aux_requery_after_shopen` 이고 **벤치 실측 확정 전이다 (OI-13)**.

> ⚠️ **재질의는 신규 ICS 고유 동작이다 — 레거시에 선례가 없다.** 레거시 실측은 `IMAGETYP='OBJECT'` · `EXPTIME=30` 프레임인데도 `AUXQDATE` 가 `DATE-OBS` 보다 10.0 s 앞서고(`TCSQDATE` 는 6.6 s 앞) `SHUTTER='CLOSED'` 가 실려 있다 — 셔터가 열린 뒤 다시 묻지 않았다는 뜻이다. 그 값이 노출과 무관하다는 것이 재질의를 넣은 이유다.

> **정본 견본은 BIAS 라 (c) 표의 첫 줄만 담는다.** 셔터 노출의 `AUXQDATE > DATE-OBS` 는 견본에 실물이 없으므로 **이 절이 유일한 근거**다.

### 5.8 AUX Information and Status (33장)

| Keyword | 값 | 출처 |
| --- | --- | --- |
| `AUXLINK` | `Up` / `Down` | AUX relay |
| `AUXARC` `AUXQDATE` `AUXUDATE` | 링크 복구 모드 · 질의/갱신 UTC — 순서 규약은 **5.7.1절** | AUX relay |
| `FSSTAT` `FILTOP` `FILNUM` `FILTER` | 필터-셔터 계통 상태 · 필터 | AUX relay |
| `SHUTOP` | `NC`/`STANDBY`/`OPENING`/`OPENED`/`CLOSING`/`RELOADING`/`ERROR` | AUX relay |
| `SHUTTER` | `OPEN`/`CLOSED`/`UNKNOWN` — **`SHUTOP` 의 순수 함수**, "완전 개방"을 뜻하지 않는다. `SHOPEN`+1초 재질의로 노출 중 값 반영 (5.7.1절 · OI-13) | AUX relay |
| `FASTAT` `FAFOCUS` `FATILTNS` `FATILTEW` `FAPOSS` `FALIMS` `FAPOSE` `FALIME` `FAPOSW` `FALIMW` | 초점 액추에이터 | AUX relay |
| `MCSTAT` `MCPOS` | 미러 커버 | AUX relay |
| `ENSTAT` `ENFAN` `ENS1`–`ENS7` | 환경 계통 (ENS 값은 중계 그대로, 소수 1자리) | AUX relay |
| `FSATEMP` `FSAHUM` | FSA 내부 온도/습도 — ENS식 표기 잠정 (**Tapaculo 원값 포맷 확인 후 최종** — 8장) | Tapaculo |

### 5.9 Pair 일관성 규칙

| 구분 | Keywords |
| --- | --- |
| **반드시 상이 (6장)** | `DETID` · `CHMAP_LT` `CHMAP_LB` `CHMAP_RT` `CHMAP_RB` · `FILENAME` (`DETID` 필드만 다르다) |
| **반드시 동일** | **위 6장을 뺀 전부** — 컨트롤러 정체 색인형(`CTRL1*`/`CTRL2*`)과 `Cn_*` 텔레메트리, 그리고 **`EXPID`** 도 양쪽에 같은 값을 싣는다 |

⚠️ **v1.6 에서 7장 → 6장이 됐다.** 구 `ORIGNAME` 은 `DETID` 필드를 달아 상이였는데, 이를 대체한 `EXPID` 는 그 필드가 없어 **양쪽 동일**이다. 그래서 `EXPID` 가 **짝을 잇는 단일 키**가 된다 — MEF 조립에서 두 파일을 묶을 때 파일명 파싱 없이 이 카드 하나로 짝지을 수 있고, 폐지된 `PAIRFILE` 이 하려던 일을 카드 추가 없이 해낸다.

충돌 증가 시 두 파일이 함께 같은 번호로 증가하므로 (`FILENAME`,`EXPID`) 불일치 여부도 pair 양쪽에서 동일하다 (D-016).

### 5.10 raw 에 넣지 않는 keyword

| 분류 | 대표 | 이유 |
| --- | --- | --- |
| MEF 구조·산출물 정체 | `EXTNAME` `DATAPROD` `PRODVER` `GEOMVER` `CREATOR`(MEF) 등 | converter 가 생성 |
| Section 좌표·amp 식별 | `CCDSEC` `AMPSEC` `DATASEC` `BIASSEC` `AMPID` `READDIR` 등 | 4장 geometry 에서 계산 — 중복은 불일치 원천 |
| Calibration | `GAIN` `RDNOISE` `SATLEVEL` `LINMAX` · crosstalk 전체 · **`XTALKVER` `REFVER` `CATVER`** | pipeline caldb 소관 — **계층 규칙**(1장): raw 미기재 · L0 재량 · L1 필수 |
| WCS · 파생 시각 | `CTYPE*` … · `JD` `MJD-OBS` `UT` `DARKTIME` `TSHOPEN` `TSHSHUT` | L1 / `DATE-OBS`·`EXPTIME` 파생 |
| 폐지·미도입 | `UNIQNAME` `NAMECLSH` `PAIRFILE` `CTRLTAG` **`ORIGNAME`**(v1.6 폐지 — `EXPID` 가 대체) `RAWVER` `RAWPROD` `OSCNPATT` `ROWORDR` `RDDIRT/B` `MIDOSC*` `CHIP1/2` `CHIPS` `HEMODE` `NPHLINES` `CHKIMG(_C)` chiller 4장 `FSADEW` `FSAALRM` 전압 색인 계열 `AMOD/ACHN` · **`AIR_IN` `AIR_OUT` `GLYC_IN` `GLYC_OUT`**(v1.5 폐지) 등 | 판정 근거는 **원장 7·8장** (전량 귀속) |

**규격/구성 버전의 자기 선언 카드는 없다** — `CAMVER`(HW) · `CTRLxCFG`(FW/설정) · `DETID` · `CHMAP_*` 조합으로 파악한다 (원장 확인 요망 11).

## 6. MEF · Pipeline · Calibration 연동

raw 사용자를 위한 요점 — 상세와 LEECU 실행 목록은 **통합 문서** (Part 1 = C-항목, Part 2 = 정체성).

| 항목 | 요점 |
| --- | --- |
| 변환 하드 실패 | **`OBSERVAT` ↔ 파일명 불일치 하나뿐** — 나머지 결측은 조용히 기본값이 된다 |
| 조용한 오염 (위험) | `DATE-OBS` 없으면 변환 시각으로 대체 · `RA`/`DEC` 는 형식 유효한 기본 좌표 · `EXPTIME` 기본 0 — **결측을 sentinel 로 가리지 말 것** (5.0절) |
| MEF `UNIQNAME` | raw `UNIQNAME` 폐지로 공급원 변경 필요 (C-항목) — 하류 색인 키는 **`FILENAME`(+`EXPID`)**. ⚠️ v1.6 개정 — 구 `ORIGNAME` 을 읽던 코드는 `EXPID` 로 옮겨야 한다 |
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
| 3 | 카드 전량 | 견본 v1.0 대비 값 카드 131장 전량 존재, 카드 **형** 일치 (식별자 = 문자열). `END` 뒤 공백 레코드는 값으로 세지 않는다 |
| 4 | 정체성 | `FILENAME`=실명 · `EXPID` 존재 · 평시 `FILENAME` 의 `DETID` 필드 뗀 값 = `EXPID` (2.3절) |
| 5 | Pair 규칙 | 상이 **6장** / 나머지 동일 — **`EXPID` 는 pair 양쪽 동일** (5.9절) |
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
| OI-13 | 셔터 상태 반영 지연 | `SHOPEN`+**1초** 재질의(5.7.1절) 시점에 AUX 상태기계가 넘어가 있는지 벤치 실측 (`aux_requery_after_shopen`). 값이 바뀌면 5.7.1절 (c) 표의 `EXPTIME` 문턱도 함께 바뀐다 |
| ~~OI-15~~ | ~~X overscan 패턴 4:4 vs 5:3~~ | **종결 (2026-08-22)** — 실제 획득 자료 육안 확인으로 `RRRRLLLL`(4:4) 확정(운영자, 4.1절). 레거시 MEF `AMPSEC` 의 M/T=5:3 · K/N=3:5 는 레거시 계통의 관찰이며 신규에 적용되지 않는다 |
| OI-16 | Tapaculo 원값 포맷 | `FSATEMP`/`FSAHUM`(+`HEBOX`) 원값 포맷 확인 후 "원값 그대로 싣기"로 최종 확정 (5.8절) |
| OI-17 | e2v 데이터시트 대응 (**부분 종결** — 원전 확보 2026-08-22, 부록 A 신설) | 확인된 것: `A`/`D` = image section 명칭, 레지스터 E/F·G/H, OS1–16, prescan 27(레거시 `PRESCANX=27` 의 원전). ~~① `IMGSEC` 의 `B` 표기~~ **종결 (2026-08-25)** — 원전 없는 표기로 판정, `D-BOT` 으로 정정. ~~② CCD 출력 채널 ↔ OS 번호 대응~~ **종결 (2026-08-25)** — 번호가 그대로 대응한다(운영자 확정). **잔여 ③ 뿐**: K·N 조가 M·T 조와 IMGSEC 배치가 갈리는 이유(180° 회전 장착 추정 — OI-15 와 연동) |
| OI-18 | NT 파일 `CCDTEMP` 귀속 | 대표 센서("M")가 NT 파일에서도 그대로인지 확인 (5.6절) |
| OI-19 | guide 컨트롤러 `Cn_TEMP` 자리 순서 | 5.6.1절의 guide 8자리(Backplane · Mod3 · Mod4 · Mod5 · Mod6 · Mod7 · Mod9 · Mod10)는 **원장 7장 기재분이고 실기 대조 전**이다. guide FITS 규격을 세울 때 실측으로 확정 |
| — | subframe/ROI | **이 규격은 전면 독출 전용** — 부분 독출은 원점 카드가 없어 표현 불가. 필요 시 별도 확장 (원장 10장 제기) |

해결된 구판 OI(1·2·6·8·10·11·12)의 경위는 archive 의 v1.2 9장.

## 9. 관련 문서

| 문서 | 위치 |
| --- | --- |
| 카드 판정 원장 | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.15.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.15.md) |
| MEF 파급 · 정체성 | [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.7.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.7.md) |
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
| — | 2026-08-18 | 전면 재검토 개시 (⛔ 재작성중) — 검토는 원장(Header_and_Refs) v1.7~v1.14 사이클로 진행 |
| **v1.8** | **2026-08-29** | **`OI-9` 폐기 + `CTRLnCFG` 예시 정합** (운영자 확정). ① **`OI-9`(배선 실측) 폐기** — 종결이 아니라 폐기다. *"실측하여 raw spec 과 mef spec 에 다 정리해놓았고, 이들 문서를 통해 통제하므로"*. 배선은 이제 **4.5절 amp 전수 표**와 `CHMAP_LT/LB/RT/RB` 가 싣고, MEF 쪽은 ICD 의 `AMPINFO` 가 통제한다 — 열린 물음이 아니라 **문서가 관리하는 값**이 됐다. 8장 OI 표의 행과 4.5절 본문의 `(OI-3 · OI-9)` 참조를 함께 걷어냈다. ② **`CTRLnCFG` 예시를 실제 ACF 이름 규칙에 맞췄다** — 5장 예시가 `'KMTA_SCI_101_R2609.1'` 로 **시리얼·검출기조가 빠진 모양**이었다. 실제 규칙은 `<SITE>_<역할>_<유닛번호>_<시리얼>_<ACF판>[_<검출기조>]` 이고(`ics_archon/acf/README.md`), 값은 **폴더 경로와 확장자(`.acf`/`.cfg`)를 뗀 이름**임을 명시했다. 견본 pair 4장은 이미 새 값(`KMTA_SCI_101_STA0288_R2608_MK` · `…_102_STA0289_R2608_NT`)으로 고쳐져 있다 — **견본 판은 올리지 않았다**(변경이 마이너, 운영자 확정). ⚠️ ini 값에서 확장자를 떼는 것은 **코드 개정 사안**이고 `ics_archon` 브랜치 몫이다 — 규격이 먼저 서고 코드가 뒤따른다. |
| **v1.7** | **2026-08-26** | **파일명 넷째 필드에 이름을 준다 — `<DETID>`** (운영자 지시). ① **2.2절 문법을 `<SITE>.<YYYYMMDD>.<NNNNNN>.<DETID>.fits` 로** 고치고 필드 설명을 신설했다. 앞 세 자리만 이름이 있고 **넷째만 리터럴 `MK`/`NT`** 였던 탓에, D-019 를 쓰는 문서들이 그 필드를 "꼬리"·"태그" 라는 관용어로 제각각 불렀다 — 값은 정확히 `DETID` 카드의 값이다. **"꼬리를 뗀 값" 이 D-019 의 핵심 판정 규칙인데 그 대상에 이름이 없던 것이 근본 원인**이다. ② 그에 따라 2.3절 충돌 판별·5항 짝 이름 유도·5.9절 pair 규칙의 "꼬리"/"태그" 를 **`DETID` 필드**로 통일했다(DECISION_LOG D-019 · 통합 문서 · README 동반 개정). 규칙 자체는 그대로다 — 부르는 이름만 정해졌다. ③ **`__reference/Detector_Ch_to_AmpID_Map_v1.0.txt` 삭제**(운영자): 4자 채널 표기 이전 판이고 `B-BOT` 오기를 담고 있어 **혼동만 준다**. v1.6 ⑪ 의 "v1.0 은 원본 기록으로 남는다" 를 철회한다 — 원본이 필요하면 git 이력(`44ab878`~)에 있다. |
| v1.7 | 2026-08-26 | 제자리 보강(발행 당일): ① 첫 판이 "꼬리"만 훑어 **`FILENAME` 의 "태그"** 표기 셋을 놓쳤다 — 2.3절 4항 · 5.4절 `EXPID` 행 · 7장 체크리스트 4번. 같은 판이 "꼬리·태그를 `DETID` 필드로 통일했다" 고 선언했으므로 **선언과 본문이 어긋난 상태**였다. ② `EXPID` 설명의 "컨트롤러 태그 없음" 도 **"`DETID` 필드 없음"** 으로 — 필드에 이름이 생긴 마당에 없는 것을 옛 관용어로 부를 이유가 없다. ⚠️ 코드의 "컨트롤러 태그"(`config.py` 의 태그→IP·태그→ACF 사상 등)는 **파일명 필드가 아니라 컨트롤러 식별 개념**이라 그대로 둔다. |
| **v1.6** | **2026-08-26** | **노출 정체성 카드 개정 (운영자 확정).** ① **`ORIGNAME` 폐지 · `EXPID` 신설** — 값이 `<SITE>.<YYYYMMDD>.<NNNNNN>` 으로 **컨트롤러 태그가 없어 pair 양쪽에서 같다.** 그래서 5.9절 "반드시 상이" 가 **7장 → 6장**이 되고, 짝을 잇는 **단일 키**가 카드 추가 없이 생긴다(폐지된 `PAIRFILE` 의 역할). 충돌 판별은 `FILENAME` 의 `.MK`/`.NT` 꼬리를 뗀 값과 비교하는 것으로 바뀐다 — 종전의 문자열 직접 비교보다 한 단계 늘지만, 꼬리 제거는 이미 2.3절 5항이 규정한 연산이다. ⚠️ **`EXPID` 는 2026-08-12 에 삭제됐던 이름을 되살린 것**이다(구판 v1.2 2.3.1절) — 되살린 근거와 당시 삭제 근거의 대조는 2.3절 폐지 목록 아래 경고에 적었다. 당시 실제 사고였던 "실수 카드로 저장돼 zero-padding 파괴"(원장·DevNote 11.13.2)는 **값이 `<SITE>` 접두로 시작해 숫자로 읽힐 여지가 없어** 구조적으로 막힌다. ② **`FILENAME` comment 개정** — `'Filename assigned by ICS'` → **`'FITS file name as written to storage'`**. 종전 문구는 `ORIGNAME`(`'Original filename assigned by ICS counter'`)과 똑같이 "ICS 가 배정" 계열이라 **둘의 차이가 comment 에서 드러나지 않았다** — 충돌이 났을 때 어느 쪽이 디스크의 이름인지가 이 두 카드의 요점이다. ③ **견본 노출 번호 `012345`/`012340` → `123456`/`123450`** — D-018 로 번호 공간이 6자리 전부가 됐으므로 맨 앞 자리가 `0` 이 아닌 값을 보인다(구 `099999` 상한의 잔상을 없앤다). 충돌 사례(`FILENAME` ≠ `EXPID`)는 유지했다. **견본 파일 이름도 함께 옮겼다** — `KMTA.20260821.123456.{MK,NT}.fits.header.v1.0[_REFTEXT].txt`. v1.4 가 맞춰 둔 정합("`FILENAME` = 실제 저장명" 규칙의 유일한 바이트 기준물이 스스로 그 규칙을 지킨다)을 이어간다. 견본은 **144 레코드 · 값 카드 131 · 11,520 바이트 그대로**다. ④ **`Cn_*` 나열 카드 개정** (운영자 확정): 구분자 **공백 → 파이프(`\|`)**(값에 이름표가 없어 경계를 눈으로 세야 하는데 음수가 섞이면 공백으로는 갈리지 않는다 — 폭 비용은 0). ⚠️ 슬래시는 FITS comment 구분자와 겹쳐 순진한 파서에서 값이 잘리므로 쓰지 않는다 · comment **`Ctr-n` → `Ctrl-n`** · **결측 자리 sentinel 을 `NC` 로**(단일 HK 카드의 `'-999.99'` 와 다르다 — 7자짜리가 열 자리를 채우면 79자로 폭을 크게 넘기는데 `NC` 면 29자다. STATUS 무응답·미장착 모듈로 전 자리가 결측인 경우는 드물지 않다). ⑤ **5.0절에 카드 폭 초과 규범 신설** — 80자를 넘으면 **comment 를 뒤에서 자르고 값은 자르지 않는다**(값이 자료이고 comment 는 설명이며, `Cn_*` 는 자리가 곧 항목이라 값이 잘리면 뒤 항목이 조용히 사라진다). comment 를 다 잘라도 넘치면 값을 자르되 **경고를 남긴다**. |
| **v1.5** | **2026-08-25** | **5장 검토 개시분.** ① **5.6.1절 신설 — `Cn_*` 자리 순서 명세**(운영자 제시): `Cn_TEMP` science 10자리(`Backplane` · `M1:LVDS` · `S2:Driver` · `S3:Driver` · `S4:LVXBias` · `S5:ADM` · `S8:ADM` · `S9:HVYBias` · `S10:Driver` · `S11:Driver` — 운영자 원문 표기 그대로) · `Cn_VOLT`/`Cn_CURR` 7자리(P2V5 P5V P6V N6V P17V N17V P35V, 종전 5.6절 괄호 주석에서 승격) · guide 8자리는 원장 기재분으로 **OI-19** 신설. 원장 7장이 "이 순서를 raw FITS spec 에 명세로 수록"으로 남겨 둔 항목을 닫는다. ② **견본 헤더 comment 오타 2건 정정**(운영자) — `Telesope`→`Telescope`(`ALT`) · `Acutator`→`Actuator`(`FASTAT`). 레거시 계승 과정에서 딸려 온 오타이고, `__reference/` 의 레거시 실측 헤더는 사실 기록이므로 그대로 둔다. 꼬리 `#EOF` 4바이트를 떼어 **견본이 정확히 4×2880 = 11,520 바이트**가 됐다(종전 11,524 는 2880 의 배수가 아니었다). 메모장용 사본 `…_REFTEXT.txt` 2장 신설. ③ 머리말 견본 카드 수 정정 — "143카드 = 값 135 + COMMENT 7 + END" → **144 레코드 = 값 135 + COMMENT 8 + END 1**(COMMENT 실측 8장) ④ **5.7.1절 신설 — `QDATE`/`UDATE` 순서 규약**(normative). 이 값들이 ICS 산출이 아니라 **TC 응답 중계**임을 명시하고(5.7·5.8 출처 열 `ICS code`→`TCS relay`/`AUX relay` 정정 — 원장 v1.14 와 정합), TC 원전 정의(`commands.c:1553`·`:2902`)로부터 **`UDATE` ≤ `QDATE`** 를 세웠다. **기준은 `QDATE`**, 자리는 `DATE-OBS`(=`SHOPEN` 지시 시각) 전후이며 경로별로 갈린다(DARK/BIAS = 개시 직전 · 셔터 노출 = `SHOPEN`+1 s 재질의). **견본 시각 카드 4장을 이 규약대로 정정** — 08-22 판은 `UDATE` 를 `QDATE` 뒤로, `QDATE` 를 `DATE-OBS` 뒤로 두어 소스 정의·레거시 실측(`KMTNk.20170209`)·시뮬 구현 셋 모두와 어긋나 있었다. 재질의 지연 **3 s → 1 s**(OI-13).  ⑤ **`Cn_*` 자리 표기 `S<n>`(Slot) → `Mod<n>`(Module)**(운영자 확정) — 2번 자리의 `M1` 은 **`Mod1` 의 오타였다**(운영자 확인). `Backplane` 을 뺀 아홉 자리가 한 체계로 통일됐고 원장 7장의 "Slot1 LVDS" 와도 정합한다. 5.6.1절의 표기 확인 대기가 닫혔다.  ⑥ **`CHMAP_*` 토큰을 3자에서 4자 `<chip><A\|D><nn>` 으로**(운영자 확정): 채널 **01–08 = `A` · 09–16 = `D`**(e2v image section, 부록 A). 견본 8장·4.5절 표·5.2절 행 반영. 80칼럼 예산상 견본 comment 를 `CCD output ch,…`→`CCD out ch,…` 로 줄였다. 이 규칙이 4.5절 `IMGSEC` 의 `B-BOT` 을 `D-BOT` 으로 지목했고 **⑩ 에서 확정됐다**.  ⑦ **사이트 코드 개정 (D-017)** — `OBSERVAT` = `CTIO`/`SSO`/`SAAO`/**`KASI`**, 파일명 접두어 = `KMTC`/`KMTA`/`KMTS`/**`KMTK`**. `TESTBED`·`KMTT` 폐지.  ⑧ **노출 번호 공간 개정 (D-018)** — `000000`–**`999999`**, 되감음 1000000→`000000`, 충돌 루프 상한 1000000회 (D-016 항목 1·2 대체).  ⑨ **5.3.1절 신설 — 사이트별 상수표**(운영자 확정, D-017 항목 6): `TELESCOP` = CTIO `#1` · SSO `#3` · SAAO `#2`, `FPAID` = CTIO `FPA#2` · SSO `FPA#1` · SAAO `FPA#3` · KASI `FPA#0`. **견본 값은 손대지 않았다** — 견본은 SSO(`KMTA`)이고 `TELESCOP='KMTNet 1.6m #3'` · `FPAID='FPA#1'` 둘 다 이 표와 맞는다. 5.2절 `FPAID` 행과 5.3절 `TELESCOP` 행은 값을 빼고 5.3.1절로 위임했다(같은 값이 세 자리에 흩어지면 갈라진다). **KASI `TELESCOP` = `'KMTNet 1.6m #0'`**(운영자 확정, 구 테스트베드 값 `'Sim'` 대체) — KASI 만 망원경·FPA 가 둘 다 `#0` 인데 우연이며 관측소 셋은 전부 어긋난다. SSO 값은 **레거시 실측**(`KMTNk.20170209`: `OBSERVAT='SSO'`+`TELESCOP='KMTNet 1.6m #3'`)이 뒷받침한다. ⑩ **`IMGSEC` 의 `B` 종결 — OI-17 잔여 ①·② 동시 해소**(운영자 확정). 채널 번호 = OS 번호가 확정되어(잔여 ②) `채널 09–16 = OS9–16 = 위 half = 섹션 D` 가 데이터시트까지 이어지고, 데이터시트에 `B` 섹션이 없으므로 배선표의 `B-BOT` 16행(K·N 조 채널 09–16)은 원전 없는 오기로 판정돼 **`D-BOT`** 으로 정정했다. 이제 `IMGSEC` 은 앞 = image section(A·D) · 뒤 = raw 타일 위치(TOP·BOT) 두 축으로 분리된다. **OI-17 잔여는 ③(K·N 180° 회전 장착 확인) 하나뿐.** ⑪ **기계 정본 판 올림 — `Detector_Ch_to_AmpID_Map_v1.1.txt`**: ⑥ 의 4자 채널 표기와 ⑩ 의 `D-BOT` 을 반영한 64행. `__` 접두 폴더 읽기 전용 규칙(운영자 2026-08-22)에 따라 `__reference/` 의 v1.0 을 편집하지 않고 **사본을 sub레포 루트로 올려** 고쳤다. ⚠️ **v1.7 에서 그 v1.0 은 삭제됐다** — 구 표기·`B-BOT` 오기가 혼동만 주기 때문이고, 원본은 git 이력에 남는다. 4.5절·머리말의 참조를 v1.1 로 옮겼다. ⑫ **HK 카드 4장 폐지 (운영자 확정)** — `AIR_IN` · `AIR_OUT` · `GLYC_IN` · `GLYC_OUT`(standalone RTD 계통, 5.6절). 5.6절이 **18장 → 14장**, 견본 값 카드가 **135 → 131** 이 됐다. 견본은 **`END` 뒤에 공백 레코드 4장을 채워** 144 레코드·4×2880 = 11,520 바이트를 유지한다(FITS 표준 패딩, 3장). 5.10절 폐지 목록에 등재했다. |
| **v1.4** | **2026-08-22** | **운영자 1~4장 검토 반영.** ① **2.5절(ICS `Wrote` 통보 규약) 삭제** — 취득 SW 소관이라 raw 규격의 몫이 아니다(정본은 `ics_sim/DevNote.md` 3.2). raw 사용자가 알아야 할 "`LASTFILE` 은 실재 경로가 아니다"만 2.3절 5항으로 흡수. ② **4.1 X overscan `RRRRLLLL` 확정** — 실제 획득 자료 육안 확인(운영자), "검증 표본 대조 남음" 경고 삭제 · **OI-15 종결**. ③ **4.2 다이어그램에 BOT/TOP Y overscan 84/84 분리 표시**(타일 규약 층 — 물리 clocking 분배는 OI-4 유지). ④ **견본 헤더 파일명을 규격에 정합** — `KMTA.20260818.…` → **`KMTA.20260821.…`** (MK·NT): 견본의 `DATE-OBS` 2026-08-21T12:34:56.789 에 SSO 관측일 보정(2.2절)을 적용하면 관측일이 `20260821` 이라 **파일명 쪽이 틀렸다**. 2.3절 예시 블록도 견본 값과 일치시켰다 — "`FILENAME` = 실제 저장명"이라는 규칙의 유일한 바이트 기준물이 스스로 그 규칙을 지키게 됐다. ⑤ 4.4 열 제목 `Amp 범위` → **`AmpID 범위`**, 값도 **MEF AmpID(01–64) 기준으로 정합**(구 표의 `1–8`/`9–16` 은 chip 로컬 번호라 MEF AmpID 로 읽으면 절반만 맞았다 — 우반 chip 의 `17–24` 도 TOP) + half 판정식 명시. ※ 5장 이후는 팀 협의 후 별도 판에서 다룬다 |
| v1.3 | 2026-08-22 | **재작성판 발행 + 문서명 변경**(Pair_Spec → Specification). 확인 요망 11건 전량 종결분 반영: 헤더 5장을 **초안 v1.0 pair(135 값 카드) 기준으로 전면 교체** — Detector 블록 타일 해부(`PRESCNX/Y`·`OVRSCNX/Y`·`CHMAP_*`) · `FILENAME`/`ORIGNAME` 정체성(D-016, `UNIQNAME`·`NAMECLSH`·`clash/`·`PAIRFILE`·`CTRLTAG` 폐지) · 컨트롤러 블록(`CTRLxID/SN/CFG` · `ICSBUILD` 신형식 · `RDMODE`) · HK 재구성(문자열 형 · sentinel `'-999.99'`/`'9.99e-9'` · `Cn_*`) · 돔 출처 TCS 편입 · `EXPTIME` 조건부 형 · `LEDFLASH` [ms]. **4.3 포장 규범 조항 신설**(`ROWORDR`/`OSCNPATT` 카드 대체, 고정 = `CAMVER`+`CTRLxCFG`) · **4.5 amp 전수 표 신설**(기계 사본 = 채널맵 v1.0). 규격 버전 카드 미도입 확정. XTALKVER 계층 규칙(raw/L0/L1) 명시. OI 재편(15~18 신설) |
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

**IMGSEC 문자에 대한 판정** — 채널맵의 `A`/`D` 는 위 image section 명칭과 일치한다: M·T chip 은 `A-BOT`(섹션 A 가 프레임 아래)·`D-TOP`, K·N chip 은 `A-TOP`(섹션 A 가 프레임 **위**)·`D-BOT`(구 `B-BOT`, 2026-08-25 정정). 섹션 A 가 위로 가는 배치는 **die 의 180° 회전 장착**을 시사한다 — M·T 조와 K·N 조가 갈리는 이유가 그것인지 확인이 **OI-17 의 마지막 잔여 ③** 이다. (X overscan 좌우 패턴은 조와 무관하게 `RRRRLLLL` 로 확정됐다 — 4.1절.) **`B` 표기는 데이터시트에 없다**(image section 은 A·D 뿐, 레지스터는 E/F/G/H).

**채널 ↔ OS 대응이 확정되면서(운영자 2026-08-25, OI-17 잔여 ② 종결) 사슬이 닫혔다**:

```
채널 nn  =  OS nn            (운영자 확정 2026-08-25)
OS 1–8   =  아래 half = 섹션 A   (데이터시트)
OS 9–16  =  위 half   = 섹션 D   (데이터시트)
────────────────────────────────────────────
채널 01–08 = A · 09–16 = D      ← 5.2/4.5절 CHMAP 토큰 규칙의 근거
```

따라서 **`B` 를 image section 으로 읽을 자리가 없다.** 배선표 v1.0 의 `B-BOT` 16행(K·N 조 채널 09–16)은 `D-BOT` 의 오기였고 **운영자 확정으로 정정됐다 (2026-08-25, OI-17 잔여 ① 종결)** — 4.5절 표와 기계 정본 `Detector_Ch_to_AmpID_Map_v1.1.txt` 양쪽에 반영됐다.

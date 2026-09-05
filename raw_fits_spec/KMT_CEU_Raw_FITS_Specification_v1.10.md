# KMT-CEU Raw FITS Specification

**v1.9** · 2026-08-30 · **현행** — 2026-08-18~22 전면 재검토(확인 요망 11건 전량 종결 · D-016 등재)를 반영한 재작성판. v1.4 가 운영자 1~4장 검토 반영판, v1.5 가 5장(헤더 keyword) 검토 개시분이고, **v1.6 은 노출 정체성 카드를 개정한다** (`ORIGNAME` → **`EXPID`**). 구 문서명 "KMT-CEU Raw FITS Pair 규격"(v1.2, `archive/`)을 개명·대체한다. 이 문서를 **raw spec(로우 스펙)** 이라 부른다.  **v1.9 는 guide raw FITS 를 9·10장으로 신설하고**(운영자 확정 2026-08-29 — science 와 섞지 않는 별도 장) **환경 센서 장치명을 `Tapaculo` 에서 `Radionode` 로 바꾼다**(운영자 지시 2026-08-30).

| 연동 | 값 |
| --- | --- |
| 정본 헤더 견본 | [`header_samples/KMTA.20260821.123456.MK.fits.header.v1.10.txt`](header_samples/KMTA.20260821.123456.MK.fits.header.v1.10.txt) · [`…NT.…v1.10.txt`](header_samples/KMTA.20260821.123456.NT.fits.header.v1.10.txt) — 5장 카드 전량의 **바이트 단위 견본**(각 **180 레코드 = 값 카드 136 + COMMENT 8 + END 1 + 공백 35**, 정확히 5×2880 = 14,400 바이트 — `END` 는 145번째이고 그 뒤 35장은 블록을 채우는 공백 레코드다. ⚠️ **v1.10 에서 4블록 → 5블록이 됐다**: HK 카드 5장 신설로 값이 131 → 136 이 되어 144 레코드를 넘겼다). 메모장용 사본 **`…v1.10+LF.txt`**(14,585 B)는 카드마다 LF 를 넣고 끝에 `#EOF` 를 붙인 것으로, **LF 와 꼬리 `#EOF` 를 함께 걷어내면 정본과 바이트 동일**하다.  ⭐ **v1.10 에서 견본 6장을 `header_samples/` 로 모으고 이름을 통일했다** — 판 번호를 규격과 같은 `v1.10` 으로, 메모장 사본의 꼬리를 `_REFTEXT` 에서 **`+LF`** 로 (운영자 지시 2026-09-04) |
| guide 헤더 견본 | [`header_samples/KMTA.20260821.123456.G.fits.header.v1.10.txt`](header_samples/KMTA.20260821.123456.G.fits.header.v1.10.txt) — **v1.10 정본** (구 v0.0 확정 초안, 운영자 2026-08-30 — v1.10 에서 판 번호를 규격과 통일했다. **144 레코드 = 값 카드 128 + COMMENT 8 + END 1 + 공백 7**, 정확히 4×2880 = 11,520 바이트 — 패딩 2026-08-30, v1.10 에서 공백 12 → 7). ⭐ guide 는 패딩 여유가 있어 **4블록 그대로**다. 메모장용 사본 **`…v1.10+LF.txt`**(11,669 B — LF 와 꼬리 `#EOF` 를 함께 걷어내면 정본과 바이트 동일). ⏳ 10장과의 **카드 단위 대사 확인 목록은 [`SMC_CLAUDE.md`](SMC_CLAUDE.md)** 에 남아 있다 — 판 번호를 통일했다고 그 확인이 닫힌 것은 아니다 |
| 카드 판정 원장 (배경·경위) | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.16.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.16.md) — 이하 **원장**. 카드별 계승/개칭/폐지 근거, converter 대조, 레거시 123개 전량 귀속 |
| MEF·파이프라인 파급 | [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.8.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.8.md) — 이하 **통합 문서**. LEECU 전달용 C-항목·이름 대응 |
| 결정 기록 | `../project_management/governance/DECISION_LOG.md` — D-002(chip order) · D-010(Wrote 분리) · D-011(파일명) · D-012(백엔드 계약) · D-013(레거시 판정) · D-014(관측일) · ~~D-015~~(사이트 IP 판정 — **D-020 이 대체**) · **D-016(충돌·정체성)** · **D-017**(사이트 코드 넷) · **D-020(사이트 판별 = `[node] observatory`)** |
| 연동 ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` (v4.1) |
| 연동 converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) |
| Amp 배선 맵 (기계 사본) | [`Detector_Ch_to_AmpID_Map_v1.1.txt`](Detector_Ch_to_AmpID_Map_v1.1.txt) — 4.5절 표의 기계 가독 정본. 구 v1.0(3자 채널 표기 · `IMGSEC:B-BOT` 판)은 **v1.7 에서 삭제됐다** — 원본은 git 이력(`44ab878`~) |
| 검출기 데이터시트 | `__reference/CCD290-99 datasheet (V2 - Aug 2016).pdf` (e2v A1A-778871 V2) — 부록 A 의 원전 |
| guide 검출기 자료 | `__reference/CCD47-20.pdf` (e2v CCD47-20 데이터시트) · `__reference/guide_ccd_format.xlsx` (guide 프레임 구성 원자료, 운영자 제시 2026-08-30) — 9장의 원전 |

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
- ~~Guide~~/focus CCD 자료 — **guide raw FITS 는 v1.9 부터 이 문서 9·10장이 다룬다** (운영자 확정 2026-08-29 — 별도 장, science 와 섞지 않는다). **1~8장과 부록 A 는 science raw pair 전용**이며, 이 장들의 "raw"·"pair" 는 guide 를 포함하지 않는다. **focus CCD 자료는 여전히 범위 밖이다** — guide 프레임을 이용한 초점 측정은 소비자(`gmon`) 소관이다.

구현 주체: 신규 ICS(`../ics_sim/` — 시뮬 구현·검증, 실기는 `hardware/archon.py`) · 실험실 취득(`../cam_char/archon/`) · converter(읽기 전용, LEECU 소관).

## 2. Raw FITS Pair

### 2.1 노출 1회 = 파일 2개

| Raw file | 담는 chip | Controller | 비고 |
| --- | --- | ---: | --- |
| `…MK.fits` | M, K | 1 (`<SITE>-SCI-101`) | converter 가 **헤더를 읽는 쪽** (master metadata) |
| `…NT.fits` | N, T | 2 (`<SITE>-SCI-102`) | **완전성 동일 요구** — 5장의 필수 keyword 를 전부 채운다 (ICD v4.1, OI-8 종결) |

공식 chip order 는 `M,K,N,T` (D-002). NT 파일도 단독으로 해석 가능해야 아카이브 자산으로 온전하다.

⭐ **한쪽만 남는 노출이 실재한다 (v1.10, normative).**  두 컨트롤러는 프레임을 **나란히** 받고 **각자 저장이 끝나는 대로** 파일을 낸다.  한쪽이 독출·수신에 실패해도 **성공한 쪽은 저장한다** — 실패한 쪽의 티켓만 버리고, **둘 다 실패했을 때만** 그 노출이 실패로 끝난다.  그래서 **`…MK.fits` 나 `…NT.fits` 한쪽만 있는 노출 번호가 생길 수 있다.**  ⛔ 이것은 결측이 아니라 **의도된 부분 성공**이다 — 한쪽 실패로 성한 쪽까지 버리면 되돌릴 수 없는 관측 손실이 된다.  ⚠️ 그래서 **"pair 양쪽 존재" 는 하드 실패 조건이 아니다** (7장 체크리스트 2번) — 하류(MEF converter)는 짝이 없는 노출을 **건너뛰되 오류로 세지 않는다**.  pair 일관성 규칙(5.9절)은 **두 파일이 다 있을 때만** 적용된다.

### 2.2 파일명

**형식 (D-011):**

```text
<SITE>.<YYYYMMDD>.<NNNNNN>.<DETID>.fits

  예:  KMTA.20260821.123456.MK.fits
       KMTA.20260821.123456.NT.fits
```

- `<SITE>` — 4자 대문자 사이트 코드, TC 텔레메트리 `TELID` 규약과 동일. **실효 사이트는 ICS 설정 `[node] observatory` 한 줄이 정한다** (값 어휘는 `OBSERVAT` 카드와 같은 `CTIO`/`SSO`/`SAAO`/`KASI`, D-017). **그 넷 밖의 값은 기동을 거부한다** — 조용히 `KMTK` 로 떨어뜨리지 않는다: 사이트는 파일명 `<SITE>`·좌표·`ORIGIN`·관측일 경계를 함께 끌고 가므로 오타 하나가 자료의 정체를 통째로 바꾼다. ⚠️ **호스트 IP 로 판정하던 규약(D-015)은 D-020 이 대체했다** (2026-08-24) — NIC 이 내려가거나 낯선 대역에 붙으면 진짜 관측 자료가 벤치 이름으로 저장되는 반대 위험 때문이다. TC 가 보내는 `TELID` 는 **교차검증 경고에만** 쓰고 파일명에는 영향을 주지 않는다.

  | `<SITE>` | 사이트 | `OBSERVAT` | L0 MEF prefix |
  | --- | --- | --- | --- |
  | `KMTC` | CTIO | `CTIO` | `kmtc` |
  | `KMTS` | SAAO | `SAAO` | `kmts` |
  | `KMTA` | SSO | `SSO` | `kmta` |
  | `KMTK` | KASI | `KASI` | `kmtk` |

- `<YYYYMMDD>` — **그 사이트의 관측일** (D-014): UT 에 사이트별 보정을 더한 뒤 날짜만 취한다. 경계는 CTIO UT 16:30(`+7:30`) · SAAO UT 10:30(`−10:30`) · SSO UT 01:30(`−1:30`) · KMTK 보정 0. **검산 불변식: 세 경계가 모두 현지 12:30.** 구현은 "보정 후 날짜만 취하는 한 줄"이어야 한다 — 경계를 `if` 로 나열하면 off-by-one 이 1년에 몇 번만 드러난다. **`<YYYYMMDD>` 는 `DATE-OBS` 의 날짜와 일반적으로 다르며 그것이 의도다** — 둘을 같다고 가정하는 도구를 만들면 안 된다.
- `<NNNNNN>` — **6자리 고정폭, 0 좌측 패딩** 노출 번호. pair 양쪽 동일. converter 정규식(`^(KMTC|KMTS|KMTA|KMTK)\.(\d{8})\.(\d{6})\.MK\.fits$`)과 `find_pair()`(`.MK.fits`↔`.NT.fits` 치환)가 이 형식에 걸려 있다 — 자릿수 위반은 짝 탐색 실패 또는 fallback 경로다.
- `<DETID>` — **검출기 조 식별자** `MK` / `NT`. 값은 헤더 `DETID` 카드와 **같다** (5.2절) — 파일명에서 이 필드만 pair 양쪽이 다르다. 이 규격에서 "`FILENAME` 의 `DETID` 필드를 뗀 값" 은 이 넷째 필드를 제거한 `<SITE>.<YYYYMMDD>.<NNNNNN>` 를 뜻하며, 그것이 `EXPID` 와 같은 형식이다 (2.3절 충돌 판별). guide raw FITS 의 이 필드 값은 **`G`** 다 — 9.2절 (guide 는 pair 가 없고, 이 장의 pair 서술은 guide 에 적용되지 않는다).
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

**정본 견본은 헤더 초안 v1.0 pair** — 카드 순서·comment·패딩까지 바이트 단위 기준이다. 이 장의 표는 그 견본의 전 카드(**값 136장** — v1.5 에서 HK 4장 폐지, v1.6 에서 `ORIGNAME`→`EXPID` 대체라 장수는 그대로였고, **v1.10 에서 HK 5장 신설로 131 → 136**)를 블록 순서대로 규정한다. 카드별 판정 경위는 원장 3·6·7·8장.

### 5.0 작성 정책

| 상태 | 의미 |
| --- | --- |
| 필수 | 없으면 L0 MEF 가 틀린 값을 갖거나 변환이 실패한다 — 5장 전 카드가 원칙적으로 필수다 |

| 형 | 표기 | Sentinel (값 없음) |
| --- | --- | --- |
| 문자열 `S` | FITS 문자열 카드 | `'NC'` (레거시 관례) |
| 정수 `I` | | `-1` |
| 실수 `R` | | `-999.0` |
| **HK 온도·습도** | **문자열** — 부호 포함 소수 2자리(`'-101.23'`/`'+16.78'`).  ⭐ **`FSATEMP` 도 부호를 붙인다**(소수 1자리, `'+23.4'` — v1.10, 아래 부호 규약).  `FSAHUM` 은 습도라 부호 없음 | **`'-999.99'` 단일값** (⚠️ **`Cn_*` 나열 카드 안의 결측 자리는 `NC`** — 5.6.1절) — 온도로는 불가능, 습도로는 음수 (기각 사유: 원장 v1.12 changelog) |
| `DEWPRES` | 문자열 `x.xxe-x` [torr] | `'9.99e-9'` (0·음수·비수치·범위 밖 전부) |
| **HK 전압** (`HTROUT`) | 문자열 — 소수 3자리, **부호 없음** | **`'NC'`** (v1.10 신설 — 전압은 `'-999.99'` 가 실값과 구별되지 않는다) |
| **HK 상태 낱말** (`HTREN`·`HTRFORCE`) | 문자열 — `'ON'`/`'OFF'` | **`'NC'`** ⛔ 모르는 것을 `'OFF'` 로 적지 않는다 (v1.10 신설) |

**⭐ 온도값에는 언제나 부호를 붙인다** (운영자 확정 2026-09-04, v1.10 신설).

`'+16.78'` 처럼 양수에도 `+` 를 적는다.  ⚠️ 이유는 **읽는 쪽이 부호 유무로 자리를
가늠하지 않게** 하려는 것이다 — 같은 계통에서 어떤 값은 부호가 있고 어떤 값은
없으면 정렬·파싱이 값에 따라 갈린다.

적용 범위:

* ✅ **온도 카드 전부** — `CCDTEMP` `DMPTEMP` `PT30N1` `PT30N2` `CHARCOAL`
  `WALLBRD` `HEBOX` `HTRSET`, 그리고 **`FSATEMP`**(v1.10 에서 편입).
* ⛔ **온도가 아닌 것은 대상이 아니다** — `HTROUT`(전압) · `DEWPRES`(압력) ·
  `FSAHUM`(습도) · `Cn_VOLT`/`Cn_CURR`.  음수는 값 자체로 드러난다.
* ⛔ **`ENS1`–`ENS7` 은 예외다** — 5.8절이 *"중계 그대로"* 로 규정한 값이라
  우리가 표기를 만들지 않는다.  ⚠️ 그 카드의 comment 가 `in deg C or percent RH`
  라 **온도 자리가 섞여 있지만**, 어느 자리가 온도인지의 명세가 없으므로 부호
  규약을 적용하지 않는다.
* ⛔ **`Cn_TEMP` 는 예외다 — 부호를 붙이지 않는다** (운영자 확정 2026-09-05).
  구판의 *"이번 판 제외"* 를 **영구 예외로 확정**한 것이다.  근거 둘:
  * **science 는 카드에 안 들어간다.**  10자리 × `nn.n` = 49자를 인용 필드 51 에
    담고 있는데, 자리마다 `+` 를 주면 **59자**가 되어 **8자를 넘긴다** — 그러면
    "카드 폭 초과 시 comment 를 뒤에서 자른다" 규칙이 걸려 `/ Ctrl-1 T[C]` 가
    잘려 나간다.  ⚠️ guide 는 8자리라 47자로 **들어가긴 한다**(폭 49) — 그러나
    **한쪽만 부호를 주면 규약이 컨트롤러별로 갈린다.**  같은 이름의 카드가
    파일 종류에 따라 표기가 다른 것이 폭 몇 자보다 나쁘다.
  * **부호가 읽는 쪽에 주는 것이 없다.**  이 카드는 사람이 눈으로 훑는 스칼라가
    아니라 **자리로 해석하는 기계 판독 나열**이다(5.6.1절) — 파서는 `+` 가 있든
    없든 같은 수를 얻는다.  부호 규약의 목적은 *"온도 카드를 눈으로 볼 때 부호가
    빠진 것인지 양수인지 헷갈리지 않게"* 인데 여기엔 그 독자가 없다.

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

출처 어휘: `ICS INI`(설정) · `ICS code`(취득 SW 산출) · `user input/selection` · `TCS relay` / `AUX relay`(TC 중계) · `TCS relay or REDIS`(newTCS 계통) · `Archon`(컨트롤러) · `ICG RTD` / `standalone RTD`(v1.5 폐지로 현행 수록 카드 없음) / `Radionode`(HK 실측 계통) · `ICS calculation`(파생).

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
| `CTRL1CFG` | S | 적용된 Archon 설정 파일명 (`'KMTA_SCI_101_STA0288_R2609_MK'`) — **폴더 경로와 확장자(`.acf`/`.cfg`)를 뗀 이름**이다(v1.8). **타이밍·바이어스·클럭 버전 문자열은 전부 이 파일로 귀속** (개별 버전 카드 없음) | ICS INI |
| `CTRL2ID` `CTRL2SN` `CTRL2CFG` | S | 컨트롤러 2 (`-102` · `'STA-0289'` · …) — **두 대분을 양쪽 파일에 모두 싣는다** (converter 가 MK 만 읽으므로) | ICS INI |
| `ICSBUILD` | S | **`v<버전>:<빌드일시(UTC)Z>`** (예 `'v0.1.2:2026-08-21T18:09Z'`) — 프로그램명 없음(식별은 `DATASRC`), 끝의 `Z` 는 의도적 | ICS code |
| `RDMODE` | S | 독출 모드 (`'NORMAL'` 등) — MEF `READMODE`(`'64AMP'`, 구조 선언)와 **별개** | ICS INI / ICS code |

컨트롤러 수가 늘면 `CTRLnxx` 벌이 늘어나는 확장 규약이다. guide FITS 의 컨트롤러 카드 취급은 **10장이 정한다** — 실재하는 컨트롤러 1 의 한 벌만 싣고 **`CTRL2*` 는 싣지 않는다** (운영자 확정 2026-08-30, 견본 v0.0 반영. 검토 중의 "`NC` 로 채우기" 안은 채택되지 않았다 — 구판 v1.8 의 "`CTRL1xx` 한 벌만 싣는다" 와 결과가 같다).

### 5.6 Camera System House Keeping (19장)

전부 **문자열** (5.0절 형 규칙). 공급 계통 **셋** — `ICG RTD`(Archon 쪽) · `ICG heater`(듀어 히터 제어·실측, **v1.10 신설**) · `Radionode`(환경 센서 — **구칭 `Tapaculo`**, 운영자 지시로 2026-08-30 개명. 구판·아카이브 문서의 `Tapaculo` 표기는 같은 장치다. 5.8절 FSA). ⚠️ 넷째 계통이던 `standalone RTD`(별도 판독 장치)는 **v1.5 의 4장 폐지로 현행 수록 카드가 없다** (5.10절).

⭐ **이 블록의 값은 ICS 가 자기 컨트롤러에서 읽는 것이 아니다** — 듀어·환경 계통은 guide 유닛에 물려 있어 **ICG 만 만질 수 있고**, ICS 는 ICIMACS 왕복(`HKDATA`)으로 받는다. `Cn_*` 두 행만 ICS 자기 컨트롤러(`Archon`)의 값이다.

⚠️ **`DEWPRES` 가 sentinel 인 것이 정상인 구간이 있다** — 진공 이온게이지의 필라멘트가 science 영상에 영향을 주므로 **science 노출 중에는 게이지를 끈다**(ICS 가 노출 앞에 `VACGAUGE OFF`, 독출 완료 10분 뒤 `ON`). 끈 동안 압력을 읽을 수 없어 이 카드는 `'9.99e-9'` 로 실린다 — **결측이 아니라 의도된 상태**다.
⛔ 그리고 **끈 동안 오는 값을 실으면 안 된다**: 이온게이지를 꺼도 같은 모듈의 열손실(Conductron) 센서가 값을 계속 내보내는데, 그 값이 인정 범위 `[1e-8, 1e+3]` 안이라 **경고 없이 통과한다** (실제 1e-6 인데 헤더에는 `1.00e-4` 같은 그럴듯한 값). ⚠️ guide FITS 도 **같은 게이지**를 쓰므로 그 구간에는 양쪽이 동시에 sentinel 이다.
⚠️ 히터·게이지 명령은 `APPLYMOD`/`APPLYDIO` 로 그 모듈의 VCPU 를 재시작시키므로, 명령이 나간 프레임의 `DEWPRES` 가 결측일 수 있다 (규범이 아니라 읽는 쪽 안내).

| Keyword | 값 | 출처 |
| --- | --- | --- |
| `HKUDATE` | `'2026-09-04T09:10:33'` — **이 블록 값들의 취득 시각** (초 단위 19자, `Z` 없음 — 시간계는 `TIMESYS` 가 선언한다). 못 받았으면 sentinel `'NC'` | ICG RTD |
| `DEWPRES` | `'1.23e-4'` [torr] — sentinel `'9.99e-9'` | ICG RTD |
| `CCDTEMP` | **실측 대표 센서 1개** [deg C] — comment 는 **`CCD temperature`** (chip 귀속 표기 `M` 은 운영자 지시로 **2026-08-30 제거**, 견본 3장 제자리 반영 — 구 이월 대기 1번). L1 `CARRY_KEYS` 가 이름으로 요구, 평균 파생 아님 | ICG RTD |
| `DMPTEMP` | DMP 온도 [deg C] | ICG RTD |
| `PT30N1` `PT30N2` | PT-30 cold-end #1/#2 [deg C] | ICG RTD |
| `CHARCOAL` | charcoal canister [deg C] | ICG RTD |
| `WALLBRD` | wallboard [deg C] | ICG RTD |
| `HEBOX` | HE box 내부 [deg C] | Radionode |
| `HTREN` | 듀어 히터 사용 여부 — **`'ON'`/`'OFF'`** (낱말). 못 읽으면 sentinel `'NC'` | ICG heater |
| `HTRSET` | 히터 목표온도 `'-100.10'` [deg C] — **부호 필수**(5.0절). sentinel `'-999.99'` | ICG heater |
| `HTROUT` | 히터 **출력 전압**(`STATUS` `MOD10/HEATERAOUTPUT`) `'3.512'` [V] — 부호 없음. sentinel `'NC'`. ⏳ 측정값인지 명령값인지는 **OI-28** | ICG heater |
| `HTRFORCE` | 강제 출력 모드 — **`'ON'`/`'OFF'`**. sentinel `'NC'` | ICG heater |
| `C1_TEMP` `C1_VOLT` `C1_CURR` | 컨트롤러 1 모듈별 온도/전압/전류 — **`\|` 구분 나열, 자리 = 항목**. 자리 순서 명세는 **5.6.1절** | Archon |
| `C2_TEMP` `C2_VOLT` `C2_CURR` | 컨트롤러 2 동형 — 자리 순서 동일 | Archon |

`Cn_*` 는 MEF `VOLTINFO`/`TELEMETRY` 를 실측으로 채울 원천이다 (C-후보, 통합 문서 §1). NT 파일의 `CCDTEMP` 대표 센서 귀속은 확인 항목 (8장).

#### 5.6.2 히터 카드 넷 — 값의 층과 이름 규칙 (v1.10)

⭐ **되읽기의 층이 카드마다 다르다.**  `HTREN`·`HTRSET`·`HTRFORCE` 는 컨트롤러
설정 메모리를 **되읽은**(`RCONFIG`) 값이고, `HTROUT` 은 `STATUS` 의
**`MOD10/HEATERAOUTPUT`**(히터 채널 A)이다 — 백플레인 FW 1.0.1252(guide 실기와 같은 판) 이미지 분석으로 HeaterX(type 11) STATUS 경로가 이 키를 출력함을 확인 — 매뉴얼 p.48 의 "Heater only" 는 FW 와 어긋난 오기.  ⏳ 그 값이 출력단 **측정값**인지 PID/FORCE **명령값**인지는
실기 미확인(**OI-28**) — 확정 전까지 "실제로 내는" 은 "모듈이 `STATUS` 로 보고하는" 으로 읽을 것.  ⛔ 호스트가 *"보냈다"* 고 기억하는 캐시는 원천이 아니다 --
설정 왕복이 실패해도 캐시는 먼저 갈아 끼워지므로, 그것을 실으면 **컨트롤러에
안 들어간 값이 헤더에 남는다.**

⚠️ **명령의 모양과 카드의 모양이 다르다.**  운영 명령은 사용 여부와 목표온도를
한 명령(`HTRSET`, 인자 둘)으로 받지만, 카드는 `HTREN` 과 `HTRSET` 으로 **나뉘어**
실린다 — 카드는 각 값을 따로 읽을 수 있어야 한다.

⚠️ `HTRSET` 은 **클램프된 값**이 실린다.  목표온도가 모듈·센서의 한계를 넘으면
명령이 한계로 접고 그 사실을 응답에 적는데, 카드는 `RCONFIG` 되읽기라 **실제로
앉은 값**이 실린다 — 요청값이 아니다.

⛔ **`HTROUT`(히터 채널 출력, 0~25 V)과 guide 전원 레일 `HEATER`(`STATUS` `HEATER_V`/`HEATER_I` — 매뉴얼 p.47 · FW 1.0.1252; PSU 공칭 +28 V, power-good +18~+36 V(p.41); 10.4절
`C1_VOLT` 8번째 자리)는 서로 다른 값이다.**  전자는 히터가 지금 내는 출력이고
후자는 그 히터에 공급되는 전원이다.

⭐ **낱말 표기의 정본은 한 곳이다** — 설정 원값 `0`/`1` 을 `'OFF'`/`'ON'` 으로
옮기는 것은 ICG 한 곳에서만 한다.  두 곳에서 하면 갈린다.  ⛔ **못 읽었으면
`'OFF'` 로 적지 않는다** — 모르는 것을 껐다고 적으면 거짓말이 되므로 `'NC'` 다.

⏳ **`HTROUT` 의 원천 구현은 대기 중이다** — 그 값은 HK 취득이 주기마다 뜨는
`STATUS` 스냅샷의 **`MOD10/HEATERAOUTPUT`** 키에 있고(FW 1.0.1252 확인 — 실기 응답 실물은 첫 구동 대기)(`C1_TEMP` 를 채우는 그 응답), 거기서 꺼내면 왕복이 늘지
않는다.  구현 전에는 이 카드가 sentinel 로 실린다.

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

**guide 컨트롤러**(`DATASRC = 'ARCHON_GUIDE'`)는 모듈 구성이 달라 `C1_TEMP` 가 **8자리**다 — 자리 표와 근거는 **10.4절(guide 장)이 정본**이다 (v1.9 에서 OI-19 종결 — 구판이 여기 적었던 `Mod9 HVYBias` 는 `HVXBias` 의 오기였다). 전원 레일도 guide 는 **8자리**다 — 7레일 뒤에 guide 전용 `HEATER`(+28 V)가 붙는다 (10.4절, 운영자 확정 2026-08-30).

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

`TCSQDATE`·`TCSUDATE`·`AUXQDATE`·`AUXUDATE` 는 **ICS 가 만드는 값이 아니라 TC(TCSAgent · AUXAgent) 응답 필드를 그대로 중계한 것**이다. ⭐ **ICS 가 이 네 카드를 직접 지어내는 경로는 없다** — TC 무응답 폴백(`tc_timeout_mode=canned`)조차 **직전 실응답의 값을 그대로 두거나, 그것도 없으면 아예 싣지 않는다**(하류가 5.0절 sentinel `NC` 로 채운다, 운영자 지시 2026-09-04). 폴백이 우리 시계로 채우면 *"TC 가 찍은 시각"* 이라는 카드에 **우리 시계**가 실려 5.7.2절 시각 비교가 언제나 0 을 내고 **"시계가 맞다" 로 오독된다** — 값이 낡았다는 사실은 그 시각 자체가 말해야 한다. 따라서 아래 부등식은 ICS 가 강제하는 규칙이 아니라 **TC 의 스탬프 방식에서 따라 나오는 성질**이며, raw 를 읽는 쪽은 이 순서를 전제해도 된다.

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
| `FSATEMP` `FSAHUM` | FSA 내부 온도/습도 — ENS식 표기 잠정 (**Radionode 원값 포맷 확인 후 최종** — 8장) | Radionode |

### 5.9 Pair 일관성 규칙

⚠️ **적용 전제 — 두 파일이 다 있을 때다** (2.1절). 한쪽만 남은 노출에는 이 절의 어느 항목도 걸지 않는다.

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
| 2 | 파일명 | 정규식 일치 · 6자리 zero-padding · `<SITE>`↔`OBSERVAT` 일치 (2.2절). **pair 양쪽 존재는 경고이지 실패가 아니다** — 한쪽만 남는 노출은 의도된 부분 성공이다 (2.1절, v1.10) |
| 3 | 카드 전량 | 견본 v1.0 대비 값 카드 136장 전량 존재, 카드 **형** 일치 (식별자 = 문자열). `END` 뒤 공백 레코드는 값으로 세지 않는다 (science 35장 · guide 7장) |
| 4 | 정체성 | `FILENAME`=실명 · `EXPID` 존재 · 평시 `FILENAME` 의 `DETID` 필드 뗀 값 = `EXPID` (2.3절) |
| 5 | Pair 규칙 | 상이 **6장** / 나머지 동일 — **`EXPID` 는 pair 양쪽 동일** (5.9절) |
| 6 | geometry 선언 | `AMPNAX1 = PRESCNX+IMAGEX+OVRSCNX` · `AMPNAX2 = PRESCNY+IMAGEY+OVRSCNY` · `CHMAP` 불변식 (4.5절) |
| 7 | 포장 | flat/star 시험으로 4.3절 조항 준수 검증 (OI-3) |
| 8 | sentinel | 금지 카드(`DATE-OBS` 등)에 sentinel 없음 · HK sentinel 은 `'-999.99'`(온도·습도) / `'9.99e-9'`(`DEWPRES`) / **`'NC'`**(상태 낱말·전압·시각, v1.10) 만 사용 |

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
| OI-25 | HK 신설 5장의 원천 배선 | ⛔ **`HKUDATE`·`HTREN`·`HTRSET`·`HTROUT`·`HTRFORCE` 다섯 다 실기 원천이 아직 안 닿았다.** 카드·형·자리·sentinel 은 서 있고 시뮬은 실값을 내지만, 실기 경로(`icg_archon` HK 스냅샷 → `ics_archon.sensors()`)가 **이 다섯 키를 아직 담지 않아** 실기에서는 전부 sentinel 로 실린다. 되읽기 함수 자체는 있다(`icg_archon/heater.py` 가 `HTREN`·`HTRSET` 을 `RCONFIG` 로 읽는다) — 빠진 것은 **HK 표본기가 그것을 주기적으로 담는 일**이고, `HTRFORCE` 되읽기와 `HTROUT`(`STATUS` `MOD10/HEATERAOUTPUT` — `icg_archon/hk.py` 에 그 키를 읽는 줄이 없다)은 코드가 **아직 0줄**이다. ⚠️ guide `.162` 의 **`STATUS` 응답 실물이 저장소에 한 번도 남은 적이 없다** — 첫 구동에서 원문을 파일로 남긴다. ⭐ `HKUDATE` 는 통과 경로가 섰다 — 스냅샷에서 **가장 낡은 표본시각**을 싣는다(실제보다 신선하다고 말하지 않으려는 것) |
| OI-28 | `HTROUT` 값의 의미 | `MOD10/HEATERAOUTPUT` 이 히터 출력단 **측정값**인지 PID/FORCE **명령값**(DAC 설정)인지 미확정 — FW 1.0.1252 는 모듈 구조체 값을 ×1e-3 으로 찍을 뿐, 그 자리를 채우는 쪽(모듈 리드백 vs 백플레인 명령)은 백플레인 FW 만으로는 못 추적한다(HeaterX 모듈 자체 FW 는 보유 이미지에 없음). 매뉴얼도 *"heater A output in V"* 라고만 한다. **첫 구동 FORCE 실험으로 닫는다**(`icg_first_run.md`): `HEATERAENABLE=0` 인 채 `FORCELEVEL` 1.000→2.000 으로 바꿔 `STATUS` 값이 정확히 설정값을 따르면 **명령값**(→ 5.6.2절 "실제 출력" 을 "출력 설정" 으로 정정), 부하·단자 전압을 따라가면 **측정값** |
| OI-16 | Radionode 원값 포맷 | `FSATEMP`/`FSAHUM`(+`HEBOX`) 원값 포맷 확인 후 "원값 그대로 싣기"로 최종 확정 (5.8절) |
| OI-17 | e2v 데이터시트 대응 (**부분 종결** — 원전 확보 2026-08-22, 부록 A 신설) | 확인된 것: `A`/`D` = image section 명칭, 레지스터 E/F·G/H, OS1–16, prescan 27(레거시 `PRESCANX=27` 의 원전). ~~① `IMGSEC` 의 `B` 표기~~ **종결 (2026-08-25)** — 원전 없는 표기로 판정, `D-BOT` 으로 정정. ~~② CCD 출력 채널 ↔ OS 번호 대응~~ **종결 (2026-08-25)** — 번호가 그대로 대응한다(운영자 확정). **잔여 ③ 뿐**: K·N 조가 M·T 조와 IMGSEC 배치가 갈리는 이유(180° 회전 장착 추정 — 종결된 ~~OI-15~~ 의 판정 기록과 연관) |
| ~~OI-18~~ | ~~NT 파일 `CCDTEMP` 귀속~~ | **폐기 (v1.10)** — 종결이 아니라 폐기다. `CCDTEMP` 는 **대표 센서 실측 1개**이고 pair 양쪽 동일이 5.9절로 이미 규정돼 있어(*"상이 6장을 뺀 전부"*), NT 에서 달라질 여지 자체가 없다. comment 의 chip 귀속 `M` 도 2026-08-30 에 걷혔다 — 확인할 물음이 남아 있지 않다 |
| ~~OI-19~~ | ~~guide 컨트롤러 `Cn_TEMP` 자리 순서~~ | **종결 (v1.9)** — guide 장 신설로 10.4절에 수록됐다. guide ACF `[SYSTEM]` 과 `modtm_gui_*` 스크립트 두 근거가 일치해 8자리 확정(구판 5.6.1절의 `Mod9 HVYBias` 는 `HVXBias` 오기 정정). **guide OI 는 10.6절** (OI-20~24) |
| — | subframe/ROI | **이 규격은 전면 독출 전용** — 부분 독출은 원점 카드가 없어 표현 불가. 필요 시 별도 확장 (원장 10장 제기) |

해결된 구판 OI(1·2·6·8·10·11·12)의 경위는 archive 의 v1.2 9장. **guide 의 open item(OI-20~24)은 10.6절에 따로 있다.**

## 9. Guide Raw FITS — 파일과 픽셀 배치

**이 장과 10장은 guide raw FITS 전용이다** (별도 장 신설 — 운영자 확정 2026-08-29, science 와 섞지 않는다). 1~8장·부록 A 는 science pair 전용이며, 그 규정은 이 두 장이 명시적으로 가져오는 것만 guide 에 적용된다.

대상: **STA Archon guide controller 1대**가 저장하는 guide raw FITS. 검출기는 **e2v CCD47-20**(frame-transfer, 13 μm 픽셀, image 1024×1024, 출력 amp 2개) **4개** — 초점면 네 방위의 가이드 CCD 를 한 컨트롤러가 함께 독출해 **노출 1회 = 파일 1개**를 만든다. science 와 달리 **pair 가 없다.**

**frame-transfer CCD 를 셔터 관여 없이 연속 프레임으로 운용한다** (용어 확정 — 운영자 2026-08-30, 데이터시트·ACF `FrameShift(1033)` 실측과 일치). 한 번 읽고 나서 다음번에 읽을 때까지가 노출이다 — 노출 의미론은 10.1절.

| 연동 | 값 |
| --- | --- |
| 검출기 데이터시트 | `__reference/CCD47-20.pdf` (e2v A1A-CCD47-20 Issue 7, 2003-04) — 9.4절 다크 기준열·store 1033행 대응의 원전 |
| 프레임 구성 원자료 | `__reference/guide_ccd_format.xlsx` (운영자, 2026-08-30) — 9.4절 X·Y 분해의 정본 |
| 적용 ACF | `../ics_archon/acf/KMTK_GUI_162_STA0201_R2615.acf` (KASI 벤치 유닛 실물 — `Pixels=540` · `FirstFlush`/`FlushLines=2448` · `PIXELCOUNT=528` · `LINECOUNT=1033` · 실탭 8 · `BIGBUF=0`), 분석은 `../ics_archon/acf/README.md`. ⚠️ `../ics_archon/` 은 `ics-archon-v1.0-build` 브랜치에 있다 — `main` 에서는 링크가 아직 안 열린다 |
| 소비자 | [`../gmon/`](../gmon/) v2 — guide raw 를 칩별 4장(`KMTNg{n,s,e,w}.…`)으로 분할·측정한다. `gmon/gmon.conf` `[geometry]` 와 `gmon/DESIGN.md` 가 이 장의 기하를 전제한다 — **converter·MEF 경로는 없다** |
| 취득 주체 | `icg_archon` (별개 프로그램 — `../ics_archon/icg_archon/`, ⚠️ `ics-archon-v1.0-build` 브랜치). **시뮬 단계로 가동 중**이고 이 장·10장의 카드 구성을 시험으로 물고 있다 (`icg_archon/tests/test_icg_cards.py`) — 이 장이 바뀌면 그 시험이 깨지는 것이 정상이다 |

### 9.1 science 와 같은 점 · 다른 점

**같은 것은 철학과 헤더 골격이다** — 파일명 문법·관측일·충돌 처리(2장), single HDU 16-bit 구조(3장), "검출기 공간 순서로 완전 정렬" 포장 규범(4.3절), 헤더 카드 **골격**(블록 순서·COMMENT 8장)과 형·sentinel·폭 규칙(5장). **다른 것은 검출기·기하·노출 의미론**이고 아래 표와 9.2~10.4절이 전부다.

| 항목 | science (1~8장) | guide (9~10장) |
| --- | --- | --- |
| 검출기 | e2v CCD290-99 × 4 (M·K·N·T) | e2v **CCD47-20** × 4 (frame-transfer, 13 μm) |
| 컨트롤러 | 2대 (`<SITE>-SCI-101`/`-102`) | **1대** (`<SITE>-GUI-161`, KASI 벤치 `-162`) |
| 노출 1회 산출 | 파일 2개 (pair `MK`·`NT`) | **파일 1개** (`G`) — pair 없음 |
| 셔터 | FSA 셔터가 노출을 연다/닫는다 | **셔터가 노출을 정의하지 않는다** — 프레임 주기가 노출이다 (10.1절) |
| 프레임 | 19200 × 9400 | **4224 × 1033** |
| amp | 파일당 32 (chip 당 16) | 파일당 **8** (chip 당 **2**) |
| X overscan | tile 당 48 | **물리 overscan 없음** — 채널당 **다크 기준열 16** 을 헤더는 `OVRSCNX` 로 귀속 (9.4절 · 10.3절) |
| 헤더 | 5장, 값 카드 136장 | **골격 동일, 값 카드 128장** — `CTRL2*`·`C2_*` 6장 미수록 · `CHMAP_*` 4장 → `CHMAP` 1장 · `IMGROT` 신설 (10.2절) |
| 컨트롤러 카드 | `CTRL1*`/`CTRL2*` 두 벌 실값 | **`CTRL1*` 한 벌만 — `CTRL2*`·`C2_*` 는 싣지 않는다** (10.2절) |
| `Cn_TEMP` | 10자리 (5.6.1절) | **8자리** (10.4절) |
| `Cn_VOLT` `Cn_CURR` | 7자리 (전원 레일) | **8자리** — 뒤에 `HEATER`(+28 V) 추가 (10.4절) |
| 하류 | converter → L0 MEF → pipeline | **gmon** 칩 분할·측정 (MEF 경로 없음) |
| 취득 버퍼 | `BIGBUF=1` (768 MB × 2) | `BIGBUF=0` (512 MB × 3) — 취득 SW 소관, 파일에는 무관 |

### 9.2 파일명과 정체성

형식은 2.2절 문법 그대로이고 **`<DETID>` 필드 값만 `G`** 다:

```text
<SITE>.<YYYYMMDD>.<NNNNNN>.G.fits

  예:  KMTA.20260821.123456.G.fits
```

- `<SITE>`(D-017) · `<YYYYMMDD>` 관측일(D-014) · `<NNNNNN>` 6자리 zero-padding(D-018) 규칙은 2.2절과 같다.
- **충돌 처리는 2.3절(D-016)을 단일 경로로 적용한다** — 후보 N 의 `…G.fits` 경로 **하나만** 선검사하고, `FILENAME`·`EXPID` 두 카드를 항상 기록하며, 충돌 신호 = `FILENAME` 의 `DETID` 필드를 뗀 값 ≠ `EXPID`. `EXPID` 는 pair 를 잇는 역할은 없지만 충돌 신호·재저장 필터 역할은 그대로다.
- ⏳ **노출 번호 카운터는 science 와 독립**이다(제안 — 취득 주체가 `icg_archon` 으로 다르다, **OI-23** 에서 함께 확정). 파일명은 `DETID` 필드로 갈려 science 와 충돌하지 않는다.
- science pair 탐색(converter 정규식 `….MK\.fits$`)에 guide 파일은 **구조적으로 걸리지 않는다** — 하류 오염 경로가 없다.
- **gmon 궁합**: gmon 의 stem 규칙은 `KMTA.20260821.123456.G` 에서 선두 비숫자 토큰을 떼어 `20260821.123456.G` 를 뽑는다 — 이 파일명 규약은 gmon 의 요구(`gmon/DESIGN.md` 10절 5번: 파일명·저장 경로 규약)를 충족한다. **저장 경로(감시 디렉토리)는 취득 SW 설정 소관**이며, guide raw 가 감시 디렉토리 한 곳에 떨어진다는 것만 이 규격의 전제다.
- 레거시와의 단절: 레거시는 **칩별 4파일** `KMTNg{s,e,n,w}.<INITIALIZE 타임스탬프>.<시퀀스>.fits` 였다 (`../ics_legacy/icg_legacy_report.md`). 신규는 **컨트롤러 단위 1파일**이고 칩 분할은 gmon 이 한다 — 분할 산출물이 레거시 이름꼴(`KMTNg<p>.…`)을 계승한다.

### 9.3 파일 구조

| 요구 | 값 | 비고 |
| --- | --- | --- |
| HDU 구성 | **single HDU** | 3장과 동일 |
| `BITPIX` · 픽셀 표현 | **16** · big-endian signed + `BZERO=32768` | 3장과 동일 |
| `NAXIS1` / `NAXIS2` | **4224 / 1033** | 실탭 8 × `PIXELCOUNT` 528 / `LINECOUNT` 1033 (ACF 실측) |
| 패딩 · 압축 | 2880 B 블록 · 내부 압축 금지 | 3장과 동일 |
| Binning | **1×1 전용** | ACF `VerticalBinning=1` |

| 항목 | 값 |
| --- | ---: |
| 파일당 픽셀 | 4224 × 1033 = 4,363,392 |
| 파일당 데이터 | ≈ 8.32 MiB |

프레임이 작고 주기가 짧아 **컨트롤러 프레임 카운터 되감김이 science 보다 훨씬 빨리 온다**(16비트라면 **하한 주기 ≈ 1.25 s** 기준 약 23 시간 — 10.1-1절) — 대응은 취득 SW 소관이다 (`../ics_archon/DevNote.md` 8.3절 — ⚠️ 브랜치).

### 9.4 픽셀 배치

**X 방향 — CCD 1개 = 1056열 블록, 블록 4개** (정본: `guide_ccd_format.xlsx`)

```text
X:  4224 = 1056 × 4블록,  블록 offset 0 · 1056 · 2112 · 3168

블록 1개(CCD 1개) = [ 16 다크 기준열 | 512 active | 512 active | 16 다크 기준열 ]
                    └── 좌채널 528 ──┘└── 우채널 528 ──┘
                    (다크 기준열은 각 채널의 amp 쪽 = 블록 바깥 가장자리)
```

- 채널(탭) 1개 = **528 = 다크 기준열 16 + active 512**. active 512 는 CCD47-20 image 폭 1024 의 절반(분할 독출)이다.
- **물리 X overscan 은 없다** (저장 구간이 전부 실컬럼이다 — 헤더 카드로는 다크 기준열 16 을 `OVRSCNX` 에 귀속한다, 10.3절). 시퀀서는 채널당 레지스터 blank 8개를 건너뛰고(`PreSkipPixels=8`) **541 픽셀을 디지타이즈**(`Pixels=540` + 인자 없는 flush `PixelFirst` 1)하지만 **앞 528 만 저장**하고 13 개를 버린다 (ACF `PIXELCOUNT=528`, 타이밍 LINE43~47). ⚠️ **구 R2609 까지는 `Pixels=600` 이라 601 디지타이즈 · 73 폐기였다** — 레지스터 실소자 수를 넘겨 클록만 돌던 잉여였고, R2610(2026-09-03, 운영자)에서 540 으로 줄여 **독출을 1.3746 s → 1.2506 s 로 124 ms 앞당겼다**. 산수 전문은 `../ics_archon/acf/README.md`.
- **데이터시트 대응 — 앞 16 = 다크 기준열이다 (프리스캔이 아니다)**: CCD47-20 독출 레지스터의 한쪽 절반은 `8 BLANK | 15 DARK REFERENCE | 1 transition | 512 active` 순으로 나온다 (p.8 line output format · p.4 "16 DARK REFERENCE COLUMNS"). blank 8 은 건너뛰므로 저장 528 의 선두 16 = **차광된 실제 CCD 컬럼**(다크 기준열 15 + transition 1)이다 — CCD290-99 의 prescan 27(비감광 레지스터 소자)과 성격이 다르다. 실측 확정은 **OI-20**.
- **탭 순서** (ACF `TAPLINE` 실측): seg 0..7 = `AD5L · AD1R · AD6L · AD2R · AD7L · AD3R · AD8L · AD4R` — **칩 k = 인접 세그 쌍 (2k, 2k+1)** (gmon 실험실 실측: seg4·5 만 동시 신호). 칩↔방위 대응은 잠정 `n,s,e,w` 이고 하늘 실측 확정 대상이다 (**OI-21**, gmon 커미셔닝과 공동).
- **포장은 4.3절 조항의 정신 그대로** — 검출기 공간 순서로 완전 정렬해 저장한다. gmon 의 direct 스티칭 실측(접합부 불연속 0.5~8.5 ADU, 뒤집기 시 20~90 ADU)이 이를 뒷받침한다. 고정 대상 = `CAMVER` + `CTRL1CFG`.

**Y 방향 — store 구간 전체를 읽는다**

```text
Y:  1033 = active 1024 + 추가 9행
```

- 1033 은 CCD47-20 **store 구간의 행수**다 — 프레임 트랜스퍼(1033 사이클) 후 store 전체를 읽는다 (ACF `FrameShift(1033)` · `Lines=1033`). 데이터시트 p.4 는 store 를 1024(H)×**1033**(V) elements 로 적고 **image 상단에 dark reference rows 3행**을 둔다 — 추가 9행의 내역(다크 기준행 3 + 무명 6)을 직접 서술하지는 않고, p.1 의 "additional pixels … for dark reference and over-scanning purposes" 총칭만 있다.
- ⏳ 추가 9행의 **프레임 내 위치(상/하)와 성격은 실측 확정 전**이다 — gmon 실측은 "맨 아래 최소 1행 더미"까지이고, 잠정 트림은 아래 9행(`gmon.conf` `y_trim_bottom=9`)이다. **OI-21**.

geometry 카드(`AMPNAX*`·`IMAGEX/Y`·`PRESCN*`·`OVRSCN*`)의 guide 값 규정은 **10.3절**에 있다.

## 10. Guide Raw FITS — 노출 의미론과 헤더

### 10.1 노출 의미론 (normative)

**셔터가 노출을 정의하지 않는다.** guide CCD 는 frame-transfer 소자를 셔터 관여 없이 **연속 프레임**으로 운용하며, 노출의 경계는 프레임 독출이다 (운영자 확정 2026-08-30):

1. **`EXPTIME` = 연속한 두 프레임의 트랜스퍼(`FrameShift`) 개시 시각의 간격** [seconds]. 취득 SW 가 프레임 주기를 이 값으로 만든다 (형 규칙은 5.4절과 동일 — 정수형 기본). 주기 안의 어느 고정점을 잡아도 간격은 같지만, **첫 저장 프레임의 앞 경계가 flush 라 디지타이징 개시가 없으므로 기준점은 트랜스퍼 개시 하나다**(5번).
   ⛔ **하한이 있다 (v1.10)** — 독출 자체가 store 1033행을 훑는 시간보다 짧은 간격은 만들 수 없다. **하한 = 트랜스퍼(`FrameShift` 1033행 + 레지스터 쓸기 + clamp ≈ 6.8 ms) + 디지타이징 독출(1243.9 ms)** — 다음 트랜스퍼는 store 가 다 읽혀 빌 때까지 못 오고 트랜스퍼 자체가 6.8 ms 걸리므로 두 트랜스퍼 개시의 간격은 그 합보다 짧을 수 없다(`NoIntMS`=0 기준). 현행 ACF `R2615` 계산으로 **1.2506 s**(`Pixels=540`). ⛔ **계산값이며 판마다 다르다 — 상수로 적지 않는다**("1.25" 도 안 된다: 0.6 ms 라도 하한을 거짓으로 적는 것이고 `FlushLines` 와 같은 '파생값 상수화' 함정이다). ⭐ **하한 미만 지시는 거절하지 않고 접는다** (운영자 확정 2026-08-31: *"더 작게 설정해도 최소 노출시간으로"*). 접는 기준은 **운영 하한**이다 — 취득 SW 설정 `exptime_min`(기본 **1.3 s**, 운영자 확정 2026-09-05: 하드웨어 하한 위에 여유) — 그 아래 요청은 1.3 s 로 접히고, 운영 하한을 하드웨어 하한보다 작게 두면 하드웨어 하한이 이긴다. ⛔ 두 하한은 **다른 물건**이다: `IntMS = EXPTIME − 하한` 의 하한은 하드웨어 하한(계산값)이어야 헤더가 참이고, 운영 하한은 그 위에 얹는 정책이다. ⛔ 그러면 요청값과 실제 주기가 갈리므로 **헤더에는 요청값이 아니라 실현된 간격을 싣는다** — `EXPTIME` 의 정의가 *"연속한 두 독출 개시의 간격"* 이므로 실현값이 곧 정의값이다 (`icg_archon` `frame_floor()`·`effective_exptime()`). ⚠️ 하한 값은 **ACF 판에 매인다**(구 `R2609` 는 ≈ 1.37 s) — `CTRL1CFG` 와 함께 읽어야 한다. ⭐ **`EXPTIME` 카드의 해상도는 1 ms 다** (2026-09-05) — `IntMS` 의 분해능이자 `DATE-OBS` 의 분해능이다. 하한이 ms 경계에 없어(1.2506283 s) 정수 요청은 어느 것도 정확히 실현되지 않는데(`guideexp 2` → IntMS=749 → 1.9996283 s), 그대로 실으면 5.4 조건부 형 규칙으로 카드가 실수형 `1.9996283` 이 된다. **실현값을 ms 로 반올림해 싣고, 소수부가 0 이면 정수형**이다 — `guideexp 2` → `2`, 운영 하한 미만 요청 → `1.3` (IntMS 49 ms + 하드웨어 하한 1.2506 = 1.2996 → 1.300).
2. **노출 시퀀스는 flush 로 시작한다 — 첫 트랜스퍼분은 저장하지 않는다.**
   (a) *왜* — 유휴 중 image 에 쌓인 전하는 적분 개시가 정의되지 않고, `R2612` 부터는 유휴 중 store 도 비우지 않으므로 store 에도 전하가 있다. ⚠️ 진짜 큰 전하는 **돔 열린 유휴의 빛**이다 — image 가 포화하면 ABD 가 없어(데이터시트 p.5 note 10) store 까지 블루밍하고, 그것을 안전하게 버리는 경로가 이 flush 다(암전류는 −100 ℃ 에서 1 h 유휴에 픽셀당 수 k e⁻ 로 무시할 양).
   (b) *어떻게* (운영자 확정 2026-09-04 · **ACF 반영 `R2613`, 2026-09-05**) — **디지타이즈하지 않는다.** 타이밍 스크립트의 `FlushFrame` 이 `IntUnit` 없이 곧바로 `FrameShift` 로 image→store 를 옮기고(**이 개시 순간 image 의 적분이 새로 시작한다 = 첫 저장 프레임의 `DATE-OBS`**, 4번), `SkipLine` × `FlushLines` 로 store 를 행 단위로 버린다(`R2615`: `SkipLine` 의 `HorizontalShift(600)` 이 **DG=HIGH** 로 돌아 전하를 덤프 게이트로 버린다 — 종전엔 `IMAGE6` 가 내린 DG=LOW 로 출력 노드를 지났다, 운영자 지적 2026-09-05). **프레임 버퍼에 아무것도 남지 않는다** — 컨트롤러 프레임 카운터도 늘지 않고 호스트가 볼 자료가 없다. 호스트는 `GO` 에 `Exposures=n` + `FirstFlush=1` 을 **한 `LOADPARAMS`** 로 걸고, 코어가 플래그를 소비한다(⛔ 플래그 슬롯은 `Exposures` 보다 **앞**이어야 한다 — `LOADPARAMS` 는 슬롯 순서로 적용한다). ⏳ "flush 가 프레임 카운터를 올리지 않는다" 는 ACF 논리에서 온 추론이고 FW 실측이 아니다 — 첫 구동에서 `go 1` 뒤 카운터 증가가 정확히 1 인지 확인한다(OI-26).
   (c) *`FlushLines` 는 왜 2448 인가* — flush 가 본 독출(1.2439 s)보다 빨리 끝나면 첫 저장 프레임의 실적분이 `EXPTIME` 보다 짧아지므로 소요를 맞춘다: `SkipLine` 2448 × 508.11 µs = 1.2439 s(오차 −2.7 µs). 첫 저장 프레임의 실적분 = flush `FrameShift` 개시 → 자기 `FrameShift` 개시 = 정상 주기와 같다(−2.7 µs).
   ⛔ **`FlushLines` 는 파생값이다** — `Pixels` · `Lines` · `AT`(병렬 클록 위상 폭) · `ST`(직렬 클록 위상 폭) 중 **하나라도 바꾸면 반드시 다시 계산**해야 한다. 넷이 같은 ACF 안에 있고 자동으로 따라가지 않으므로, 고치지 않으면 **오류 없이 첫 저장 프레임의 실적분만 틀린다.** 민감도는 균등하지 않다 — `Lines` 는 정비례, `Pixels` 600 이면 2692, **`ST` 를 2배로 하면 1433 로 41 % 움직인다**(`AT` 는 1 % 남짓). 산수와 검산은 `../ics_archon/acf/README.md` · `icg_archon/acftiming.py`.
3. **`go n` = flush 1회 + 독출 `n`회 · `n`장 저장.** `go` = `go 1` — flush 1회 뒤 독출 1회, 1장 저장. 트랜스퍼 개시 간격 = `EXPTIME`. ⚠️ **v1.10 발행 문면 "프레임 `n`+1개 독출 · 첫째 폐기 · `n`장 저장"(운영자 확정 2026-08-30)을 개정했다** (2026-09-05, ⏳ **운영자 재확인 요망**) — 저장 장수 `n` · 파일 배정 · `DATE-OBS` 배정은 그대로이고, 2026-09-04 의 flush 확정이 `R2613` 으로 ACF 에 들어가면서 '첫 프레임' 이 독출(디지타이즈)이 아니라 flush 가 되어 **컨트롤러 프레임 카운터가 `n` 만 는다**(구판은 `n`+1). 종전 문면은 12장 ⑬에 남긴다.
4. **`DATE-OBS` = 직전 프레임 트랜스퍼(`FrameShift`)의 개시 시각** — 저장 프레임의 적분이 시작된 순간이다. **첫 저장 프레임의 `DATE-OBS` 는 flush 를 위한 `FrameShift` 의 개시 시각**(운영자 확정 2026-09-04: '개시' 이지 종료가 아니다) — 취득 SW 는 이를 arm 의 `LOADPARAMS` 왕복 중점으로 근사한다(코어가 적용 즉시 `FlushFrame` 으로 들어가므로 ≤ 1 µs + RTT/2). 밀리초 필수, sentinel 금지 (5.4절과 동일). `go n` 다중 저장에서도 같은 규칙이다 — 각 저장 프레임의 `DATE-OBS` = 그 직전 프레임의 트랜스퍼 개시 (프레임마다 파일이 갈린다, 아래 6). ⚠️ **v1.10 발행 시점의 구현은 트랜스퍼 *종료*(+6.8 ms ≈ 디지타이징 개시)를 찍었다** — `R2613` 반영(2026-09-05)부터 개시다. 취득 SW 가 그 뒤 프레임의 개시를 **완료 관측 − (트랜스퍼 + 독출)** 로 되짚으므로 완료 관측의 폴링 지연만큼 늦는 편향이 있다(⏳ 예측 폴링으로 줄이는 것은 후속).
5. **독출 중에도 image 구간은 계속 노출된다** — 그래서 경계가 "독출 개시"다. 실체로는 프레임 트랜스퍼(1033 사이클, ms 오더)가 노출을 끊고 store 독출이 뒤따르므로, **이 규격의 "독출 개시" := 트랜스퍼(`FrameShift`) 개시**다 — 디지타이징 개시는 그보다 ≈ 6.8 ms 뒤이고 ACF 판에 매인다. 물리적으로 1033 행 트랜스퍼가 6.8 ms 에 걸쳐 각 행의 노출을 끊으니 그 폭 안은 본질적 모호 구간이지만, 규격은 점 하나를 못박는다. ⚠️ 셔터 없는 frame-transfer 운용의 구조적 특성으로 **수직 스미어**가 상존한다 — gmon 설계가 이를 감안한다 (`gmon/DESIGN.md`).
6. **저장 프레임마다 파일 1개, 노출 번호 증가** — `go n` 이면 FITS `n`개가 저장된다 (운영자 확정 2026-08-30).
7. ⛔ **`GUIEXPCTRL` 이 끊으면 거기서 끝이다 — 이어가지 않는다 (v1.10, 운영자 확정 2026-09-04).** ICS 는 science **독출 구간**을 지키려고 guide 에 `GUIEXPCTRL`(`EXPENABLE=FALSE`)을 보낸다 — science **노출 중에는 guide 가 노출·독출을 계속해도 무방하고**, 막는 것은 독출 구간뿐이다. `EXPENABLE=FALSE` 가 들어오면 그 시점이 시퀀스의 어디든 **guide 노출 시퀀스는 완전히 종료**되고, **그때 노출 중이던 프레임은 저장하지 않는다.** ⛔ `EXPENABLE=TRUE` 로 풀려도 **다음 노출을 이어가지 않는다** — 재개가 아니라 **새 `GO`** 가 있어야 다시 돈다. ⚠️ 그러면 새 블록도 2번대로 **flush 로 시작한다**. ⚠️ `DONE: EXPENABLE` 은 *"시퀀스를 세웠다"* 이지 *"guide 가 조용하다"* 가 아니다 — 취득 SW 는 `RESETTIMING` 으로 진행 중 사이클을 **그 자리에서 끊고**(적분·독출 어디든, 적분을 마저 하지 않는다) 곧바로 `FlushFrame` 한 바퀴로 CCD 를 비운다(운영자 확정 2026-09-05 — 디지타이징 없이 `SkipLine` 으로, 프레임은 만들지 않는다). 그 flush 가 **≈ 1.25 s 클록**하므로 조용해지는 것은 그 뒤다 — 한 주기와 같은 길이지만 이제 IntMS 와 무관하게 일정하다. `ABORT` 도 같은 길이다; `STOP` 은 현재 프레임을 저장까지 마친다. ⭐ 그 뒤는 **정말 조용하다** — guide ACF `R2612`(2026-09-05) 부터 유휴 루프가 CCD 를 클록하지 않는다(구판은 유휴 중에도 ~0.5 ms 마다 store 를 밀고 ADC 를 clamp 했다). **목적은 science 독출 시 guide 클록의 crosstalk 제거**다(운영자 확정 2026-09-05 — science 영상이 주이고 guide 는 노이즈를 좀 허용한다). ⛔ science 쪽 유휴 flush 는 그대로다 — science 는 피해자 쪽이라 같은 논리가 걸리지 않는다.

검증 불변식: **`DATE-OBS` + `EXPTIME` ≈ 자기 프레임의 독출 개시 시각** (10.5절 6번). ⚠️ **연속으로 돈 한 블록 안에서만 성립한다** — 7번대로 시퀀스가 끊겼다 새 `GO` 로 다시 시작하면 블록 경계를 사이에 둔 두 파일 사이에는 성립하지 않는다. **노출 번호가 이어져도** 경계는 생기므로 파일 이름만으로는 못 가린다.

**TC 질의 시점**: 셔터 재질의 규칙(5.7.1절 (c) 표의 셔터 노출 두 행)은 guide 에 **해당 없다** — `SHOPEN` 이 없다. `QDATE`/`UDATE` 순서 규약(5.7.1절 (a)·(b))은 그대로 적용된다. 질의 시점 규약은 `icg_archon` 설계와 함께 확정하며(**OI-23**), 초안은 레거시 계승이다 — 프레임 사이클 개시 전 1회 스냅샷 (`../ics_legacy/icg_legacy_report.md`: 레거시 ICG 는 GO 접수 직후 노출 전에 질의·중계했다).

### 10.2 헤더 원칙

- **카드 골격은 science 5장을 따르되 값 카드는 128장이다** (운영자 확정 견본 v0.0, 2026-08-30 · v1.10 에서 HK 5장 신설): 136장에서 **`CTRL2ID` `CTRL2SN` `CTRL2CFG` · `C2_TEMP` `C2_VOLT` `C2_CURR` 6장을 뺀다**(컨트롤러가 하나다 — 검토 중의 "`NC` 로 채우기" 안은 채택되지 않았다), **`CHMAP_LT/LB/RT/RB` 4장을 `CHMAP` 1장으로** 갈음하고, **`IMGROT` 1장을 신설**한다 — 128 = 136 − 6 − 3 + 1. 블록 순서·COMMENT 8장 골격과 형·sentinel·카드 폭 규칙(5.0절)은 그대로다.
- **5장과 값·의미가 다른 카드만 10.3절 표가 규정한다 — 표에 없는 카드는 5장 그대로다.**
- 정본 견본은 **v0.0 확정 초안**(머리말 연동 표)이다 — 이 장과의 대사에서 나온 정정·확인 목록은 [`SMC_CLAUDE.md`](SMC_CLAUDE.md) 에 있고, 해소되면 science 견본과 함께 **v1.1 로 승격**된다. 그때까지 견본과 이 장이 어긋나면 **이 장이 이긴다.**

### 10.3 science 와 값·의미가 다른 카드

| Keyword | guide 값 | 상태 · 근거 |
| --- | --- | --- |
| `NAXIS1` `NAXIS2` | `4224` · `1033` | ✅ 9.3절 |
| `INSTRUME` | ⏳ `'<SITE코드> Guide CCD'` 안 — 어휘 확정 대기 | OI-24 |
| `DETECTOR` | `'e2v CCD47-20'` | ✅ 데이터시트 |
| `DETID` | `'G'` — 파일명 `<DETID>` 필드와 동일. comment 는 **`'Detector ID in this raw FITS file'`** — science 의 "Detector pair …" 를 대체한다(guide 는 pair 가 없다) | ✅ 운영자 확정 2026-08-30 |
| `PIXSIZE` | `13.0` | ✅ 데이터시트 |
| `PIXSCALE` | ⏳ **실측 대기** — 초안 `0.49` · gmon 잠정 `0.52` · 13 μm 비례 환산 ≈`0.51` | **OI-22** |
| `NAMPDET` | `2` — CCD47-20 출력 amp 2 | ✅ |
| `NAMPRAW` | `8` — 4칩 × 2 | ✅ |
| `AMPNAX1` `AMPNAX2` | `528` · `1033` — 채널 tile 크기 | ✅ 9.4절 |
| `IMAGEX` `IMAGEY` | `512` · `1024` | ✅ 9.4절 |
| `PRESCNX` `PRESCNY` `OVRSCNX` `OVRSCNY` | `0` · `0` · **`16`** · **`9`** — 16·9 를 **overscan 귀속**으로 정리 (운영자 확정 견본 v0.0 — 종전 잠정안 `PRESCNX=16` 대체). ⚠️ 16 의 물리 성격은 **다크 기준열**(9.4절, 차광 실컬럼)이라 comment 에 성격 병기를 권고한다. 축 합 불변식: `AMPNAX1 = 0+512+16 = 528` · `AMPNAX2 = 0+1024+9 = 1033` | ✅ 값 확정 · 실측은 **OI-20 · OI-21** |
| **`CHMAP`** (1장 — science `CHMAP_*` 4장을 갈음) | `'NRL,ERL,SRL,WRL'` **[TBC]** — 칩당 1토큰, 자리 = raw X 블록 순서. 토큰은 `<칩 방위><채널 배열>`(예 `NRL` = N 칩, R·L 순)로 읽히나 **토큰 문법·값은 실측 확정 전**이다 | ✅ 형식 (견본 v0.0) · ⏳ 값 **OI-21** |
| **`IMGROT`** (신설) | `'270,180,90,0'` — **칩별 영상 회전 상태** [deg, CW], 자리 = `CHMAP` 과 같은 칩 순서(N·E·S·W). guide 4칩은 동서남북으로 정렬 장착되어 있지 않아 칩별 orientation 을 헤더가 선언한다 (운영자 확정 2026-08-30). 값의 실측 검증은 커미셔닝 | ✅ 카드 (견본 v0.0) · ⏳ 값 **OI-21** |
| `FPAID` | ⏳ guide 조립체가 5.3.1절 `FPA#n` 에 포함되는지, 별도 식별인지 확인 대기 | OI-24 |
| `IMAGETYP` `OBSTYPE` `OBJECT` | ⏳ guide 프레임 유형 어휘(기본 `'OBJECT'` 안) 확정 대기 | OI-24 |
| `EXPTIME` `DATE-OBS` | **의미 재정의 — 10.1절** (프레임 주기 · 직전 독출 개시) | ✅ 운영자 확정 2026-08-30 |
| `DATASRC` | `'ARCHON_GUIDE'` | ✅ 5.5절 어휘 |
| `CTRL1ID` `CTRL1SN` | `'<SITE>-GUI-161'` · 관측소 SN `STA-0290`(CTIO)/`0291`(SAAO)/`0292`(SSO), KASI 벤치 `'KMTK-GUI-162'`·`'STA-0201'` — 관측소 원자료 `__reference/Archon_Unit_Info.txt`(ID 숫자 = IP) — **벤치 유닛 근거는 guide ACF 파일명**(그 파일에는 KASI 항목이 없다) | ✅ |
| `CTRL1CFG` | guide ACF 이름 `<SITE>_GUI_<유닛>_<시리얼>_<ACF판>` — **검출기조 접미사가 없다** (science 와의 차이). 현행 실물은 `'KMTK_GUI_162_STA0201_R2615'` | ✅ `acf/README.md` 이름 규칙 |
| `CTRL2ID` `CTRL2SN` `CTRL2CFG` | **싣지 않는다** | ✅ 운영자 확정 2026-08-30 (견본 v0.0 — "NC 채움" 안 대체) |
| `ICSBUILD` → **`ICGBUILD`** (개명) | `icg_archon` 의 `v<버전>:<빌드일시(UTC)Z>` — 형식은 5.5절 그대로, 식별은 `DATASRC`. guide 는 **카드명부터 `ICGBUILD`** 이고, `TIMESYS`/`EXPID` comment 의 "ICS" 도 "ICG" 로 쓴다 | ✅ 견본 v0.0 |
| `RDMODE` | 취급은 5.5절과 동일. ⚠️ 현행 guide ACF 이름에는 속도 토큰이 없어 유도가 실패한다 — 결측값 `UNKNOWN` 등재(판올림 이월 대기 4건 중 하나 — README 현재 기준선)와 연동 | ⏳ |
| `C1_TEMP` | **8자리 — 10.4절** | ✅ OI-19 종결 |
| `C1_VOLT` `C1_CURR` | **8자리** — 7레일 + `HEATER`, `VOLT` 는 소수 2자리 (10.4절) | ✅ 운영자 확정 2026-08-30 |
| `C2_TEMP` `C2_VOLT` `C2_CURR` | **싣지 않는다** | ✅ 운영자 확정 2026-08-30 (견본 v0.0) |

### 10.4 HK — guide 컨트롤러가 `ICG RTD` 계통의 원천이다

science 5.6절 HK 의 `ICG RTD` 계통 7장(`CCDTEMP` `DMPTEMP` `PT30N1` `PT30N2` `CHARCOAL` `WALLBRD` `DEWPRES`)을 실측하는 주체가 **바로 이 guide 컨트롤러**다 — 듀어 RTD 는 HeaterX 모듈 둘이 읽고(MOD7: `RTD1_PT30-1` · `RTD3_PT30-2_TBC` · `RTD4_Charcoal_TBC` / MOD10: `RTD9_DMP` · `RTD8_CCD` · `RTD5_WB` — MOD7 의 `_TBC` 두 채널은 벤치 실측에서 미연결이었다, 관측소 장착 시 연결 확인 대상), 진공 게이지(MKS 356)는 MOD10 의 VCPU 가 시리얼로 읽는다 (guide ACF 실측). 따라서 **guide FITS 의 HK 7장은 자기 실측**이고, science FITS 의 같은 카드는 `icg_archon` → `ics_archon` 전달(작업 D1)로 실린다. `HEBOX` 와 5.8절 `FSATEMP`/`FSAHUM`(`Radionode`)의 출처는 science 와 같다.

**`C1_TEMP` — guide 8자리** (n = 1 뿐 — 컨트롤러가 하나다)

| 자리 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 항목 | `Backplane` | `Mod3:Driver` | `Mod4:Driver` | `Mod5:AD` | `Mod6:AD` | `Mod7:HeaterX` | `Mod9:HVXBias` | `Mod10:HeaterX` |

- 근거 둘 일치 — guide ACF `[SYSTEM]`(`MOD_PRESENT=0x37C`, 장착 슬롯 3·4·5·6·7·9·10)과 `modtm_gui_*` 스크립트가 훑는 슬롯. **OI-19 종결 (v1.9)** — 첫 guide 구동 때 STATUS 응답으로 재확인만 남는다.
- ⚠️ **구판 5.6.1절은 Mod9 를 `HVYBias` 로 적고 있었다** — ACF 실측 `MOD9_TYPE=8` = **`HVXBias`** 의 오기라 이 판에서 정정했다 (HVYBias 는 science 유닛의 모듈 형이다).
- 구분자·결측 자리 규칙(파이프 `|` · `NC`)은 5.6.1절 그대로다.

**`C1_VOLT` · `C1_CURR` — guide 8자리** (운영자 확정 2026-08-30, 견본 v0.0): science 의 7자리 뒤에 guide 전용 **`HEATER`** 가 붙는다 — HeaterX 가 요구하는 공급 레일(매뉴얼 p.39 *"HeaterX requires P17V, N6V and HEATER"*)이고, guide 장착 모듈(Driver×2·AD×2·HVXBias·HeaterX×2)이 쓰는 레일의 합집합이 정확히 이 8개다(`N35V`·`P100V`·`N100V`·`USER` 는 어느 장착 모듈도 안 쓴다). `STATUS` 필드는 `HEATER_V`/`HEATER_I`(p.47 · FW 1.0.1252). 공칭 +28 V(표준 PSU, p.43), power-good +18~+36 V(p.41).

| 자리 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 레일 | P2V5 | P5V | P6V | N6V | P17V | N17V | P35V | **HEATER** |

- 표기: **`C1_VOLT` 는 소수 셋째 자리에서 반올림해 소수 2자리**(`'2.51|5.02|…|28.09'` — science 의 소수 3자리와 다르다, 운영자 확정 2026-08-30). `C1_CURR` 는 소수 3자리 그대로다.
- 참고: guide 바이어스는 18채널 셈이나 셈법이 갈리고(물리 채널 15 / 유효 net 18 / ABG 포함 19), 라벨 넷(`VRDSR/L` 등)에 `/` 가 있어 5.6.1절 슬래시 금지와 충돌한다 — 바이어스 측정값 카드 배치(작업 D3) 설계 시 라벨을 값·comment 로 옮기지 않는 쪽이 안전하다.

### 10.5 검증 체크리스트 (guide)

| # | 검사 | 기준 |
| --- | --- | --- |
| 1 | 파일 구조 | single HDU · `BITPIX=16` · `BZERO=32768` · **4224×1033** · 2880 패딩 (9.3절) |
| 2 | 파일명 | `^(KMTC\|KMTS\|KMTA\|KMTK)\.\d{8}\.\d{6}\.G\.fits$` · `<SITE>`↔`OBSERVAT` 일치 |
| 3 | 카드 전량 | 견본 v1.10 구성 — **값 카드 128장**(10.2절) · 카드 형 일치 · **144 레코드 = 값 128 + COMMENT 8 + END 1 + 공백 7**, 정확히 4×2880 = 11,520 B |
| 4 | 정체성 | `FILENAME` = 실명 · `EXPID` 존재 · 평시 `FILENAME` 의 `DETID` 필드 뗀 값 = `EXPID` |
| 5 | 미수록·자리 규칙 | `CTRL2*` · `C2_*` 카드 **부재** · `C1_TEMP` 8자리 · `C1_VOLT`/`C1_CURR` 8자리 (10.4절) |
| 6 | 노출 | 저장 파일 `n`장 · **컨트롤러 프레임 카운터 증가분 = `n`**(flush 는 프레임을 만들지 않는다 — v1.10 발행 시점까지는 `n`+1) · `DATE-OBS` + `EXPTIME` ≈ 자기 프레임의 트랜스퍼 개시 시각 — **취득 SW 가 독립적으로 관측한 프레임 완료 시각과 대조한다**(`DATE-OBS` 를 `t0 + (k−1)·EXPTIME` 으로 만들면 이 검사는 정의상 성립해 검증이 아니다) — 연속 블록 안에서만(10.1-7) · `EXPTIME` ≥ 운영 하한(기본 1.3 s), ms 해상도(10.1-1) |
| 7 | 포장 | 검출기 공간 순서 — gmon 분할 결과가 칩 4장(1024×1024)으로 이어 붙는다 |

### 10.6 Open Items (guide)

| ID | 항목 | 내용 · 조치 |
| --- | --- | --- |
| ~~OI-19~~ | ~~guide `Cn_TEMP` 자리 순서~~ | **종결 (v1.9)** — ACF `[SYSTEM]` · `modtm_gui_*` 두 근거 일치로 8자리 확정, 10.4절 수록. 첫 guide 구동 때 STATUS 재확인 |
| OI-20 | 저장 528 의 X 구간 성격 | 데이터시트 대응은 **다크 기준열 15+1**(9.4절) — **트림은 이미 갔다** — `R2610`(2026-09-03)이 `Pixels` 600→**540** 으로 줄여 폐기가 73→13 이 됐다(9.4절). ⛔ 그러나 그것은 레지스터 실소자 수를 넘던 잉여를 걷은 것이지 **저장 528 의 성격을 판정한 것이 아니다** — 이 항목은 그대로 열려 있다. 확정 경로: 528→512 추가 트림의 무손실 여부를 실측해 **`OVRSCNX=16` 귀속(10.3절)을 뒷받침** |
| OI-21 | 추가 9행 · 칩 방위·순서 | 9행의 위치(상/하)·성격 · 칩↔방위와 프레임 내 순서(⚠️ 견본 `CHMAP`/`IMGROT` 는 **N·E·S·W**, gmon 잠정은 **n,s,e,w** — 어긋난다, 한쪽 확정 필요) · 스티칭 방향 · `CHMAP` 토큰 값 [TBC] · `IMGROT` 값 검증 — 하늘/커미셔닝 실측 (gmon DESIGN 10절과 공동) |
| OI-26 | `FlushLines` 실측 · flush 의 프레임 카운터 | flush 프레임의 `SkipLine` 횟수 **2448**(`R2613` LINE118)은 `acftiming` **계산값**이지 실측이 아니다 (10.1-2절). flush 는 프레임을 만들지 않으므로 컨트롤러 시각으로는 못 잰다 — ① 첫 저장 프레임 완료 − `LOADPARAMS` 시각 ≈ flush + 주기 인지, ② 첫 저장 프레임의 bias/dark 레벨이 2장째 이후와 통계적으로 같은지(짧으면 어둡다), ③ `go 1` 뒤 프레임 카운터 증가가 정확히 1 인지(0 이면 추론이 맞고, 2 면 flush 가 프레임을 만든 것). ⛔ `Pixels`·`Lines`·`AT`·`ST` 중 하나라도 바뀌면 **반드시 다시 계산**한다 — 안 고치면 오류 없이 첫 저장 프레임의 실적분만 틀린다 |
| OI-27 | `GUIEXPCTRL` 이후 재개 주체 | 10.1-7 대로 `EXPENABLE=FALSE` 는 guide 시퀀스를 **완전히 종료**시키고 `TRUE` 로 풀려도 재개하지 않는다 — 그러면 **누가 새 `GO` 를 내는가**가 정해져 있지 않다. 현재 ICS 는 `EXPENABLE 0/1` 만 보내고 `GO` 를 다시 내지 않으므로 **science 노출 한 번마다 guide 가 멈춘 채로 남는다.** ICS 가 `GO` 를 함께 내는 안 / guide 가 자체 재무장하는 안 / 운영자 수동 — 운영 설계로 확정 |
| OI-22 | `PIXSCALE` | `0.49`(초안) / `0.51`(13 μm 비례 환산) / `0.52`(gmon 잠정) — 하늘 실측으로 확정 |
| OI-23 | 노출 규약 잔여 | ~~장수 대응~~·~~`DATE-OBS` 배정~~·~~파일 배정~~ **종결 (2026-08-30)** — `n`+1 독출 `n` 저장(**문면은 `R2613` 반영으로 flush 1 + 독출 `n` 으로 개정**, 10.1-3 · ⏳ 운영자 재확인) · 프레임당 파일 1개 (운영자 확정). **잔여: TC 질의 시점 · 노출 번호 카운터 독립(9.2절 제안)** — 레거시 계승안(프레임 사이클 개시 전 1회 스냅샷)과 함께 `icg_archon` 설계 때 확정 |
| OI-24 | guide 헤더 카드 설계 잔여 | **해결(견본 v0.0, 2026-08-30)**: ~~`CHMAP` 재정의~~(1장 확정 — 값은 [TBC], OI-21) · ~~`C2_*` 표기~~(카드 미수록으로 소멸) · ~~`HEATER` 레일~~(`C1_VOLT`/`C1_CURR` 8자리 확정). ~~`DETID` comment~~("pair"→"ID" 확정 2026-08-30). ~~`CCDTEMP` comment~~("M" 제거 2026-08-30 — 견본 3장). **잔여**: `INSTRUME` 어휘(견본이 science 값 'KMTA 18k CCD' 잔존) · `FPAID`(견본 'FPA#1' — guide 조립체 귀속 확인) · `IMAGETYP` 어휘 · `CAMVER`(guide 계통이 science 와 같은 값을 쓰는지) — **견본 v1.1 승격 때, 상세 대사 목록은 [`SMC_CLAUDE.md`](SMC_CLAUDE.md)** (10.3절 ⏳) |

## 11. 관련 문서

| 문서 | 위치 |
| --- | --- |
| 카드 판정 원장 | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.16.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.16.md) |
| MEF 파급 · 정체성 | [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.8.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.8.md) |
| L0 MEF ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` |
| MEF keyword 정의서 | `../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` |
| Converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) |
| 결정 기록 | `../project_management/governance/DECISION_LOG.md` |
| 신규 ICS 구현·개발 노트 | `../ics_sim/` · `../ics_sim/DevNote.md` |
| 구판 | `archive/KMT_CEU_Raw_FITS_Specification_v1.2.md` (구명 Pair_Spec) · 헤더 초안 이력은 운영자 외부 백업 |
| guide 검출기 데이터시트 | `__reference/CCD47-20.pdf` (9장 원전) |
| guide 프레임 구성 원자료 | `__reference/guide_ccd_format.xlsx` (9.4절 정본) |
| guide 적용 ACF · 분석 | `../ics_archon/acf/KMTK_GUI_162_STA0201_R2615.acf` · `../ics_archon/acf/README.md` (⚠️ `ics-archon-v1.0-build` 브랜치) |
| guide 소비자 | `../gmon/DESIGN.md` · `../gmon/gmon.conf` |
| 레거시 가이드 계통 분석 | `../ics_legacy/icg_legacy_report.md` |

## 12. Revision History

| Version | Date | Change |
| --- | --- | --- |
| **v1.10** | **2026-09-04** | **HK 카드 5장 신설 + 부호 규약 + 게이지 Off 조항** (운영자 확정 2026-09-04). ① **HK 카드 5장 신설** — 시각 `HKUDATE`(이 블록 값들의 취득 시각, 초 단위 19자) 와 듀어 히터 넷 `HTREN`·`HTRSET`·`HTROUT`·`HTRFORCE`. 자리는 운영자 지정: `HKUDATE` 를 블록 **맨 앞**(`DEWPRES` 앞), 히터 넷을 **`HEBOX` 뒤**. 5.6절이 **14장 → 19장**, 값 카드가 science **131 → 136** · guide **123 → 128** 이 됐다. ⛔ **science 견본이 4블록 → 5블록(11,520 → 14,400 B)이 됐다** — 값 136 + COMMENT 8 + END 1 = 145 레코드로 144 를 넘겼다. guide 는 패딩 여유가 있어 4블록 그대로(공백 12 → 7). ⭐ 이제 science 의 공백 레코드가 **35장**이라 다음 판에 여유가 있다. 출처 어휘에 **`ICG heater`** 를 신설했고(셋째 계통), 되읽기 층(`RCONFIG` = `HTREN`·`HTRSET`·`HTRFORCE` / `STATUS` 실측 = `HTROUT`)·클램프된 값·명령 이름과 카드 이름의 불일치·`HTROUT`(0~25 V) ↔ guide `HEATER` 레일(+28 V) 구분을 **5.6.2절**로 신설했다. ⛔ `HTRPID`·`HTRRAMP`·`FORCELEVEL` 은 **안 싣는다**(운영자 확정). ⏳ `HTROUT` 의 원천은 `ics_archon` 브랜치에 **아직 0줄**이다 — 구현 전에는 sentinel 로 실린다. ⏳ `HKQDATE`(명령 수신 시각)는 이번 판에 넣지 않았다. ② **온도 부호 규약 신설** (5.0절) — 온도 카드는 양수에도 `+` 를 적는다. `FSATEMP` 를 그 규약에 **편입**(`'23.4'` → `'+23.4'`, 견본 3장 반영). ⛔ 전압·압력·습도는 대상이 아니고, **`ENS1`–`ENS7` 은 예외**다(5.8절이 *"중계 그대로"* 로 규정 — 우리가 표기를 만들지 않는다). ⛔ **`Cn_TEMP` 는 영구 예외로 확정**(운영자 2026-09-05) — science 는 부호를 주면 49→**59자**라 인용 필드 51 을 8자 넘겨 comment 가 잘리고, guide(8자리 47자, 폭 49)는 들어가지만 **한쪽만 주면 규약이 컨트롤러별로 갈린다.** 게다가 이 카드는 자리로 해석하는 **기계 판독 나열**이라 부호가 읽는 쪽에 주는 것이 없다. ⚠️ 구판이 적었던 *"8장 미결"* 은 **실제로 등재된 적이 없는 허수 참조**였다 — 이 확정으로 함께 걷힌다. ③ **sentinel 어휘 확장** — HK **전압**(`HTROUT`) 과 HK **상태 낱말**(`HTREN`·`HTRFORCE`) 은 `'NC'` 다. ⛔ 모르는 것을 `'OFF'` 로 적지 않는다. 7장 체크리스트 8번에 반영. ④ **게이지 Off 조항 신설** (5.6절) — 진공 이온게이지 필라멘트가 science 영상에 영향을 주므로 **science 노출 중에는 게이지를 끄고**(ICS 가 노출 앞에 `VACGAUGE OFF`, 독출 완료 10분 뒤 `ON`), 그동안 `DEWPRES` 는 `'9.99e-9'` 다 — **결측이 아니라 의도된 상태**임을 명문화했다. ⛔ **Conductron 함정** 병기: 이온게이지를 꺼도 같은 모듈의 열손실 센서가 값을 계속 내보내는데 그 값이 인정 범위 `[1e-8, 1e+3]` 를 **경고 없이 통과한다** — 끈 동안 오는 값을 실으면 *"정상으로 보이는 틀린 값"* 이 아카이브에 남는다. ⚠️ guide FITS 도 같은 게이지라 그 구간에는 양쪽이 동시에 sentinel 이다. 히터·게이지 명령의 `APPLYMOD`/`APPLYDIO` 가 MOD10 VCPU 를 재시작해 그 프레임의 `DEWPRES` 가 결측일 수 있다는 안내도 함께. ⑤ **견본 6장을 `header_samples/` 로 모으고 이름을 통일했다** (운영자 지시) — 판 번호를 규격과 같은 **`v1.10`** 으로(science 구 `v1.0` · guide 구 `v0.0`), 메모장 사본의 꼬리를 `_REFTEXT` 에서 **`+LF`** 로. ⚠️ **브랜치의 바이트 대사 시험이 견본 경로·이름을 리터럴로 박고 있다**(`test_raw_draft.py`·`test_fitswrite.py` 는 `v1.0` 을, guide 쪽은 `v*.txt` 를) — 고치지 않으면 대사가 **조용히 skip** 된다(2026-08-22 개명 때 실제로 났던 사고). 규격이 먼저 서고 코드가 뒤따르되 **같은 묶음**으로 처리할 것. ⑥ 머리말의 REFTEXT 동일성 문장을 정정했다 — *"LF 를 걷어내면"* 은 4바이트 어긋났다(꼬리 `#EOF` 를 함께 걷어내야 한다). ⑦ **반쪽 pair 조항 신설** (2.1절 · 5.9절 전제 · 7장 체크리스트 2번) — 두 컨트롤러가 나란히 받고 각자 저장하며 **한쪽 실패에도 성공한 쪽은 저장한다.** 그래서 한쪽만 있는 노출 번호가 실재하고, *"pair 양쪽 존재"* 는 **하드 실패에서 경고로 내려갔다** — 한쪽 실패로 성한 쪽까지 버리면 되돌릴 수 없는 손실이기 때문이다. ⑧ **guide 노출 의미론 보강** (10장) — **하한**(10.1-1: 독출 자체가 ≈ 1.25 s 라 그보다 짧은 `EXPTIME` 은 만들 수 없다, ACF 판에 매인다) · **flush 프레임**(10.1-2: 폐기 프레임은 디지타이즈하지 않고 `EXPTIME` 없이 `SkipLine` 으로 비우되 **본 독출 소요와 같아지도록** `FlushLines`=2448 로 맞춘다(⏳ ACF 반영은 `R2611`), 실적분 기준은 flush `FrameShift` **개시** 시각) · **`GUIEXPCTRL` 조항**(10.1-7: `EXPENABLE=FALSE` 는 시퀀스를 **완전히 종료**하고 그때 노출 중이던 프레임은 저장하지 않으며 `TRUE` 로 풀려도 **이어가지 않는다** — 새 `GO` 가 있어야 한다. 막는 것은 science **독출 구간**이지 노출 구간이 아니다). 이에 따라 검증 불변식이 **연속 블록 안에서만** 성립함을 명시했다(10.5절 6번). ⑨ **사실 정정 7건** — guide ACF 를 **`R2610`** 으로(세 곳. ⛔ 5.5절 `CTRL1CFG` 예시는 **science** ACF 라 `R2608` 이 맞다) · 픽셀 산수 **541 디지타이즈 · 13 폐기**(`Pixels=540`, 구 `R2609` 의 601·73 은 레지스터 실소자를 넘던 잉여였고 R2610 이 독출을 124 ms 앞당겼다) · **폴백은 시각을 지어내지 않는다**(5.7.1절 — `canned` 조차 직전 실응답을 두거나 아예 안 싣는다. 우리 시계로 채우면 5.7.2절 비교가 언제나 0 을 내 *"시계가 맞다"* 로 오독된다) · `icg_archon` **가동 중**(9장 — 시험이 이 장을 물고 있다) · 되감김 예시를 하한 주기 기준으로 · 10.5절 3번의 guide 세기(값 123→**128** · 공백 12→**7**) — v1.10 세기 훑기에서 빠져 있었다. ⑩ **미결 정리** — ~~OI-18~~(NT `CCDTEMP` 귀속) **폐기**(5.9절이 이미 규정해 물음이 없다) · **OI-25**(`HTROUT` 원천 미구현) · **OI-26**(`FlushLines` 실측) · **OI-27**(`GUIEXPCTRL` 이후 누가 새 `GO` 를 내는가 — 지금은 아무도 안 낸다) 신설. OI-20 은 R2610 의 트림으로 닫히지 않는다 — 그것은 잉여를 걷은 것이지 저장 528 의 성격을 판정한 것이 아니다. ⑪ **동반 문서**: 원장 **v1.17**(7장 5행 추가, 카드 63→68장 · 표 55→60행 · HK 공급 계통 둘→셋) · 통합 **v0.9**(C-항목 3건 신설 — 히터 넷·게이지 Off·반쪽 pair). ⑫ **`HTROUT` 원천 확정 (2026-09-05)** — `STATUS` `MOD10/HEATERAOUTPUT`. 백플레인 FW 1.0.1252(guide 실기와 같은 판) 이미지 분석으로 HeaterX(type 11) STATUS 경로가 이 키를 출력함을 확인 — 매뉴얼 p.48 의 "Heater only" 는 FW 와 어긋난 오기(같은 표의 PID 6줄 "Heater only" 와 `TEMPA/B` "in K" 도 오기 — 실측은 ℃). guide `HEATER` 레일의 STATUS 필드도 `HEATER_V`/`HEATER_I` 로 확정(p.47 · FW 문자열), 8번째 자리 논거(장착 모듈 요구 레일의 합집합)를 10.4절에 적었다. ⏳ 값이 측정값인지 명령값인지는 **OI-28** 신설. ⚠️ 종전 문면의 "`STATUS` 실측" 은 `recovered_session:1663` 의 매뉴얼 목록 확인 한 줄로 소급되는 단언이었다 — 근거 없이 "실측" 이라고 적었던 것을 바로잡는다. ⑬ **flush 를 ACF 에 넣었다 — `R2613`/`R2614` (2026-09-05, 운영자 지시)** · **⭐ 운영자 확정 문면 개정 1건, 재확인 요망**: 10.1-3 *"go n = 프레임 n+1개 독출 · 첫째 폐기 · n장 저장"*(2026-08-30) → *"flush 1회 + 독출 n회 · n장 저장"* — 첫 프레임이 디지타이즈되지 않으므로 컨트롤러 프레임 카운터가 `n` 만 는다(저장 장수·`DATE-OBS` 배정은 그대로). 함께: 10.1-1 기준점을 **트랜스퍼 개시**로 못박고 하한을 계산값(1.2506 s)으로만 적으며 **`EXPTIME` 카드 해상도 1 ms** 와 **운영 하한 `exptime_min`=1.3 s**(하드웨어 하한 위 여유 — 운영자 확정 2026-09-05; IntMS 셈은 하드웨어 하한으로)를 규정 · 10.1-2 를 왜/어떻게/`FlushLines` 로 재구성(flush 의 진짜 대상은 돔 열린 유휴의 포화 전하) · 10.1-4 `DATE-OBS` = 트랜스퍼 **개시**(v1.10 발행 시점 구현은 종료 +6.8 ms 였다) · 10.1-5 "독출 개시 := `FrameShift` 개시" · 10.5 #6 을 프레임 카운터 = `n` 과 독립 관측 대조로 · OI-26 측정법 · 현행 ACF `R2614`. 설계는 네 관점(스크립트 문법 · CCD 물리 · 호스트 통합 · 규격) 반증 검토를 거쳤다 — blocker 1(플래그 슬롯이 `Exposures` 뒤면 `LOADPARAMS` 슬롯 순서 적용 때문에 flush 없이 첫 장이 나간다 → 슬롯 0), must_fix 다수(설정 메모리 잔존 → 유령 flush · 낯선 꼬리가 첫 *저장* 프레임이 됨 → 시간 가드 · 조기 ABORT 배수 상한 · 완료 간격 감시). `R2614` 는 `DGLOW` 상태에 RG_HIGH 를 더해 `HorizontalShift(600)` 이 출력 노드 리셋을 켠 채 돌게 한 것(운영자 물음의 답 — 정상 경로 `LINE12` 가 RG=LOW 로 돌던 구멍). `FRAME6` 이 DG 를 0 V 로 내려 프레임 시프트 중 덤프가 안 되는 STA 원본의 결함은 실측 뒤 후속 판 후보. ⑭ **abort 의 뜻이 바뀌었다 (2026-09-05, 운영자)** — guide `ABORT`/`EXPENABLE=FALSE` 는 진행 중 적분을 마저 하지 않고 `RESETTIMING` 으로 끊은 뒤 `FlushFrame` 으로 CCD 를 비운다(10.1-7). `R2615`: `SkipLine` 의 수평 시프트가 DG=HIGH 로 돌아 덤프 게이트로 버린다(운영자 지적 — 종전엔 `IMAGE6` 가 내린 DG=LOW 로 출력 노드를 지났다). science ACF **`R2609`**(6장): `FirstFlush`(슬롯 0) → `FlushFrame`(Prep + Flush) 진입 신설 — 시험용 `CCDFLUSH` 명령의 대상, science `GO` 에는 flush 를 걸지 않는다. 5.5절 `CTRL1CFG` 예시도 `R2609`. |
| **v1.9** | **2026-08-30** | **guide raw FITS 장 신설(9·10장) + 환경 센서 장치명 개명** (운영자 지시 2026-08-30). ① **9장(파일·픽셀 배치)·10장(노출 의미론·헤더) 신설** — 별도 장 방침(운영자 확정 2026-08-29)대로 science 와 섞지 않고, 9.1절이 같은 점·다른 점을 서술한다. 원전: CCD47-20 데이터시트 · `guide_ccd_format.xlsx`(운영자) · guide ACF `KMTK_GUI_162_STA0201_R2608` 실측 · gmon v2 실측. 파일명 `<SITE>.<YYYYMMDD>.<NNNNNN>.G.fits`(pair 없음, 충돌 처리 단일 경로) · 프레임 **4224×1033**(채널 528 = 다크 기준열 16 + active 512 · Y = 1024 + 9) · **노출 의미론**(셔터 무관 — `EXPTIME` = 독출 개시 간격, 첫 프레임 폐기, `DATE-OBS` = 직전 독출 개시) · 헤더는 science 골격을 따르되 카드 구성은 ④의 견본 확정으로 **값 카드 123장**(`CTRL2*`/`C2_*` 미수록 — 발행 시점의 "NC 채움" 안은 ④가 대체) · `C1_TEMP` 8자리 수록으로 **OI-19 종결**(Mod9 는 구판 `HVYBias` 표기를 `HVXBias` 로 정정). guide OI 는 10.6절 신설 — OI-20(X 528 구간)·OI-21(9행·칩 방위)·OI-22(`PIXSCALE`)·OI-23(노출 규약 잔여)·OI-24(카드 설계 잔여). 이에 따라 1장 범위 밖에서 guide 를 빼고, 5.5절 "`CTRL1xx` 한 벌만" 문구를 대체하고, 5.6.1절 guide 단락을 10.4절로 위임하고, 구 9·10장은 **11·12장**이 됐다. guide 헤더 견본 v0.0 초안은 운영자 작성 중 — 확정 후 10장과 대사해 science 견본과 함께 v1.1 로 승격 예정. ② **`Tapaculo` → `Radionode` 개명** (운영자 지시 2026-08-30) — 환경 센서 장치명 교체: 5.0절 출처 어휘 · 5.6절(구칭 병기 앵커) · 5.8절 · OI-16. 장치는 같고 이름만 바뀌므로 카드 값·판정에는 변화가 없다. 원장 v1.16 · 통합 문서 v0.8 동반 개정. ③ v1.8 머리말의 "제자리 정정(2026-08-29, D-015→D-020 사이트 판별 문장)" 블록은 본문 반영이 끝나 이 행으로 흡수했다. ④ **guide 견본 v0.0 확정 반영** (운영자, 2026-08-30 — 발행 당일 제자리 보강): `CTRL2*`·`C2_*` 6장 **미수록**("NC 채움" 검토안 대체) · `CHMAP_*` 4장 → **`CHMAP` 1장**(값 [TBC]) · **`IMGROT` 신설**(칩별 회전 상태 [deg, CW], N·E·S·W) · **`ICGBUILD`**(`ICSBUILD` 의 guide 판 개명) · `C1_VOLT`/`C1_CURR` **8자리**(`HEATER` +28 V 추가 · `VOLT` 소수 2자리) · `OVRSCNX=16`/`OVRSCNY=9` 귀속 확정 → **값 카드 123장**. **frame-transfer CCD 용어 확정** · **`go n` = `n`+1 독출 `n` 저장 · 프레임당 파일 1개 확정** (운영자). 견본 패딩(144 레코드 = 4×2880 = 11,520 B) · REFTEXT 사본 신설. OI-23 은 TC 질의 시점 하나만 남았다. ⑤ **견본 정정 (운영자 지시, 2026-08-30)**: G 견본 `NAXIS1`/`NAXIS2` `19200`/`9400`→`4224`/`1033` · `AMPNAX1`/`AMPNAX2` `1033`/`4224`→`528`/`1033` · `CHMAP` comment 오타 · `DETID` comment `pair`→`ID`, 그리고 **`CCDTEMP` comment 의 chip 귀속 `M` 제거 — G·MK·NT 3장 전부** (구 "이월 대기" 1번의 조기 실행 — science 견본은 판 안 올림 제자리 수정 기확정, 2026-08-29). REFTEXT 3장 동반 재생성. ⚠️ 브랜치의 기계 사본 3곳(`rawcards.py`·`_vendor`·labtest 내장)과 바이트 대사 시험은 이제 견본과 어긋난다 — 머지 때 동반 수정. |
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

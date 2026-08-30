# KMTNet-CEU Raw FITS Specification

최종 갱신일: 2026-08-30

> ⚠️ **`../ics_archon/` 은 `main` 에 아직 없다.**  실기 ICS 는
> **`ics-archon-v1.0-build` 브랜치에서 진행 중**이고 **추후 `main` 합류 예정**
> 이다.  이 문서가 `../ics_archon/…` 을 가리키는 링크는 `main` 에서 열리지
> 않지만 **그 브랜치에서는 열린다** — 끊긴 것이 아니라 아직 안 온 것이다.

## 목적

이 디렉토리는 KMT-CEU 신규 전자부 카메라의 **STA Archon controller가 직접 저장하는 raw FITS pair** 규격을 관리한다. 노출 1회당 controller 2대가 raw FITS 2개(`MK`, `NT`)를 만들고, 이 둘이 합쳐져 L0 64-amplifier MEF의 입력이 된다.

`mef_fits_spec/`이 **출력**(L0 MEF product) 규격이라면, 이 디렉토리는 **입력**(Archon raw) 규격이다.

```text
Archon controller x2  ──►  raw FITS pair  ──►  L0 64-amp MEF  ──►  L1 calibrated CCD
                          [raw_fits_spec]      [mef_fits_spec]     [mef_pipeline]
                                               [mef_converter]
```

규격의 판정 기준은 한 문장이다 — **raw pair가 이 규격을 만족하면 converter는 placeholder 없이 L0 MEF를 채울 수 있어야 한다.** 현행 MEF에 남아 있는 `UNKNOWN` · `-999.0` · `PLACEHOLDER`는 대부분 raw 헤더에 그 정보가 없기 때문이며, 이 규격은 그 구멍을 메우는 것을 목표로 한다.

## 현재 기준선

> ✅ **현행 규격: [`KMT_CEU_Raw_FITS_Specification_v1.9.md`](KMT_CEU_Raw_FITS_Specification_v1.9.md) — "raw spec"** (2026-08-30). 2026-08-18~22 전면 재검토(확인 요망 11건 전량 종결 · D-016 등재)의 재작성판(v1.3) → 운영자 1~4장 검토 반영(v1.4) → 5장(헤더 keyword) 검토 개시분(v1.5) → 노출 정체성 카드 개정(v1.6 — `ORIGNAME` → **`EXPID`** · `FILENAME` comment) → 파일명 넷째 필드 명명(v1.7 — `<DETID>`) → `OI-9` 폐기·`CTRLnCFG` 정합(v1.8) → **v1.9 가 guide raw FITS 를 9·10장으로 신설하고 환경 센서 장치명을 `Tapaculo` → `Radionode` 로 바꾼다** (운영자 지시 2026-08-30). 구 "Raw FITS Pair 규격" v1.2 를 개명·대체한다(구판은 `archive/`).

> ⏭️ **판올림 이월 대기 4건** (구 "v1.9 대기 5건" — ~~`CCDTEMP` comment 의 chip 귀속(`M`) 제거~~ 는 **2026-08-30 운영자 지시로 조기 실행**, 견본 3장 제자리 반영): `OI-18` 폐기 · `CAMVER` 범프 규범 명시(듀어 RTD 배치 변경 포함) · 바이어스 측정값의 헤더 카드 배치(D3) · **`RDMODE` 결측값 `UNKNOWN` 등재**(5.5절 + 5.0절 문자열 sentinel 어휘 — 코드는 이미 반영됐다). **헤더 견본 v1.0 → v1.1 승격 라운드**(guide 견본 v0.0 확정 대사와 함께)에서 처리 예정. 상세는 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "규격 쪽 후속".
>
> ⚠️ **절 구성이 구판과 다르다** — 구판 절 번호(`규격 5.7절` 등)를 인용한 문서·코드 주석은 현행 기준으로 재확인할 것. v1.4 에서 **2.5절(Wrote 통보)이 삭제**돼 2장은 2.1~2.4 다. ICD v4.1 §12 와 `ics_sim`/`ics_archon` 주석의 버전 참조 갱신은 각 소관의 일감이다.

| 구분 | 문서 | 버전 | 상태 |
| --- | --- | --- | --- |
| **Raw spec (현행)** | [`KMT_CEU_Raw_FITS_Specification_v1.9.md`](KMT_CEU_Raw_FITS_Specification_v1.9.md) | **v1.9** | ✅ 현행 (guide raw FITS 9·10장 신설 + `Radionode` 개명) |
| 카드 판정 원장 | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.16.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.16.md) | **v1.16** | ✅ 현행 (raw spec v1.9 동반 — `Radionode` 개명, 판정 불변) |
| MEF·파이프라인 파급 (통합 문서) | [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.8.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.8.md) | **v0.8** | ✅ 현행 (raw spec v1.9 동반 — `Radionode` 개명, C-항목 불변) |

연동 기준:

| 항목 | 값 |
| --- | --- |
| Raw 규격/구성 버전 파악 | 별도 버전 카드 없음(`RAWVER` 미도입 — v1.13 확인 요망 11) — **`CAMVER`(HW) · `CTRLxCFG`(FW/설정) · `DETID` · `CHMAP_*` 조합**으로 파악 |
| 파일 구성 | 노출 1회 = raw FITS 2개 (`MK` = M,K / `NT` = N,T) |
| 파일명 | `<SITE>.<YYYYMMDD>.<NNNNNN>.<DETID>.fits` (넷째 필드 이름은 v1.7 에서 명명 — 값은 `MK`/`NT`), `<SITE>` ∈ {`KMTC`=CTIO, `KMTS`=SAAO, `KMTA`=SSO, `KMTK`=KASI} (D-011 · **D-017** 개정) |
| 파일 구조 | single HDU, `BITPIX=16` + `BZERO=32768`, `19200 x 9400` |
| 파일당 amplifier | 32 (chip 2 × amp 16) |
| **Guide raw** (v1.9 신설, 규격 9·10장) | guide controller 1대 → 노출 1회 = **파일 1개** `<SITE>.<YYYYMMDD>.<NNNNNN>.G.fits`, **4224 × 1033** (CCD47-20 × 4, 채널 8), 셔터 무관 노출(`EXPTIME` = 독출 개시 간격, 첫 프레임 폐기), 헤더는 science 골격에 **값 카드 123장**(`CTRL2*`·`C2_*` 미수록 · `CHMAP` 1장 · `IMGROT` 신설). 소비자는 [`../gmon/`](../gmon/) (MEF 경로 없음) |
| 기준 ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` (v4.1, docx 동본) |
| 기준 converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) |

## 디렉토리 구조

| 경로 | 내용 |
| --- | --- |
| `KMT_CEU_Raw_FITS_Specification_v1.9.md` | ✅ **현행 raw spec (2026-08-30)** — 파일 구조 · 파일명(D-011/D-014) · 충돌·정체성(D-016) · geometry(포장 규범 조항 + amp 전수 표 64행 + X overscan `RRRRLLLL` 확정) · 헤더 keyword **131장**(초안 v1.0 pair 기준 — v1.5 에서 HK 4장 폐지 · v1.6 에서 `ORIGNAME`→`EXPID` 대체) · MEF/파이프라인 연동 요점 · 검증 체크리스트 · OI · **guide raw FITS 9·10장(v1.9 신설 — 파일·기하 / 노출 의미론·헤더, science 와 분리)** · e2v 데이터시트 부록. 배경·경위는 원장(Header_and_Refs)과 통합 문서로 링크. **v1.9 = guide 장 신설 + `Tapaculo`→`Radionode` 개명** (구 9·10장은 11·12장이 됐다) |
| `archive/` | **최근 구판만 유지** — 운영자가 주기적으로 살펴보고 없어도 될 파일은 지운다(2026-08-30 기준: Header_and_Refs v1.8~**v1.15** · Specification v1.2~**v1.8** · Impacts_and_Identity v0.5~**v0.7** 이 잔류). 지워진 구판·전신 문서(MEF_Impacts·Numbering_and_Identity·raw↔MEF 키워드 대응표 등)는 **git 이력과 운영자 외부 백업(`__backup_raw_fits_spec_oldver`)에 보존** — 대응표의 살아있는 내용은 전부 흡수됐다: **판정 준거는 Header_and_Refs 0장**, 카드 대응은 같은 문서 각 장의 `Use in MEF` 열, MEF/converter 쪽 미결 4건은 통합 문서 v0.8 §6 (ACT-011) |
| `KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.16.md` | ✅ **현행 원장. v1.16 (2026-08-30) — 환경 센서 장치명 `Tapaculo` → `Radionode` 개명**(raw spec v1.9 동반, 판정 불변). v1.15 (2026-08-29) — `OI-9` 폐기 + `CTRLnCFG` 예시 정합. v1.14 (2026-08-23) — **판정 준거를 본문 0장으로 편입**(구 검토 문서 폐기에 따른 근거 보전: 준거 순위 · converter 3상태 × ICD 규정/침묵 교차표 · 준거 공백 210 중 36/174 · 추출 함정). v1.13 (2026-08-22) — 운영자 3~5차 개정과 확인 요망 종결분을 반영한 수기 개정판** (v1.6 까지는 기계 추출 생성물, 구판은 `archive/`). **raw 카드 기준은 레거시 raw 실측 헤더**이고 **레거시 123개를 전량 귀속**시킨다 — converter 가 읽는 것 · 읽지 않는 것 · 도입 후보·확정(7장) · 폐지(8장·8.1·8.2). v1.10 에서 **도입/계획 판정 완결 — 미정 0**, v1.11 에서 **돔 Source 를 TCS relay or REDIS 로 변경** + **확인 요망 1~5 종결**(`EXPTIME`/`LEDFLASH` 정수형 · `ICSBUILD` 프로그램명 제거), v1.12 에서 **확인 요망 9 종결**(HK 온도·습도 문자열 계승), v1.13 에서 **잔여 전량 종결**(sentinel `'-999.99'` 단일값 · CTRL1ID 포맷+ICS INI 편집성 · "– 철회" 라벨 · 버전 문자열 귀속/caldb 계층 규칙 · PRESCN 키워드 변경 계승 · 규격 버전 카드 미도입 — 버전 파악은 `CAMVER`·`CTRLxCFG`·`DETID`·`CHMAP_*` 조합) — **D-016 등재까지 완료(2026-08-22), V1 재작성 착수 조건 완성**. 10~12장은 subframe 제기 · converter 자기 상수 카드 · raw 직접 사용자 안내 |
| `KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.8.md` | ✅ **현행 통합 문서. v0.8 (2026-08-30 — raw spec v1.9 동반, `Radionode` 개명 · C-항목 불변). Draft v0.6 (2026-08-22) 이래의 표제: "Raw FITS 헤더 개정에 따른 MEF ICD · MEF Converter 개정 및 검토 사항".** **Part 1** = LEECU 전달용 개정 요청 목록 — C-항목 신설·개정, raw↔MEF 이름 대응, ICD·정의서 개정 후보, MEF/converter 쪽 미결 4건(§6). **Part 2** = 번호·충돌·정체성의 **파급 요약** — 정본은 raw spec 2.3절 + D-016 으로 이동(내용 이중화 방지 축약). 전신 v0.5 는 `archive/`, v0.4·v0.2 는 git 이력·외부 백업 |
| `KMTA.20260821.123456.G.fits.header.v0.0.txt`<br>`…v0.0_REFTEXT.txt` | **guide 헤더 견본 v0.0 확정 초안** (운영자 2026-08-30) — 값 카드 **123장** + COMMENT 8 + END 1 + 공백 12 = **144 레코드**, 4×2880 = **11,520 바이트**(패딩 2026-08-30). REFTEXT 는 메모장용 사본(11,669 B — LF 걷어내면 정본과 동일). 규격 10장과의 **대사 정정·확인 목록은 `SMC_CLAUDE.md`** — 해소 후 science 견본과 함께 **v1.1 승격** 예정, 그때까지 견본과 10장이 어긋나면 10장이 이긴다 |
| `KMTA.20260821.123456.MK.fits.header.v1.0.txt`<br>`KMTA.20260821.123456.NT.fits.header.v1.0.txt` | **확정 초안 헤더 v1.0 pair** — MK 는 검토 왕복(v0.0~v0.4.4)을 마친 견본(운영자 승격 2026-08-22), NT 는 MK 에서 파생(2026-08-22): pair 상이 카드 **6장**만 다르다 (v1.6 개정 — 종전 7장) — `DETID`='NT' · `CHMAP_LT/LB/RT/RB`(`__reference/Detector_and_Amp_Info_cards_v1.0.txt` NT 블록 그대로) · `FILENAME`(`.NT` `DETID` 필드). **`EXPID` 는 `DETID` 필드가 없어 양쪽 동일**이다, 나머지 125장은 MK 동일(**`CCDTEMP` comment 의 "M" 은 2026-08-30 제거됐다** — 구 이월 대기 1번 조기 실행). 각 **144 레코드 = 값 카드 131 + COMMENT 8 + END 1 + 공백 4**, 4×2880 = 11,520 바이트. 구 `__review/` 왕복함은 폐지 — docx 왕복본·초안 이력은 운영자 외부 백업(`__backup_raw_fits_spec_oldver`)에 |
| `Detector_Ch_to_AmpID_Map_v1.1.txt` | ✅ **검출기 출력 채널 ↔ MEF AmpID 64행 맵 (현행, 이 폴더 루트)** — CtrUnit–Port–CCD/CH–IMGSEC–MEF_AmpID. `CHMAP_*` 카드와 raw spec 4.5절 amp 전수 표의 **기계 가독 정본**. **v1.1 (2026-08-25)**: 채널 토큰 3자→4자 `<chip><A\|D><nn>` · `IMGSEC` `B-BOT`→`D-BOT` 16행 (`__` 읽기 전용 규칙상 `__reference/` 의 v1.0 을 고치지 않고 사본을 루트로 올렸다). ⚠️ **구 v1.0 은 v1.7 에서 삭제됐다** — 구 표기·`B-BOT` 오기가 혼동만 주기 때문이고, 원본은 git 이력(`44ab878`~)에 있다 |
| `tools/` | `md_to_docx.py` — 개정판 md 를 검토 전달용 docx 로 변환(개정마다 필수, `SMC_CLAUDE.md` 개정 워크플로) |
| `__reference/` | 규격 작성 시 대조한 참고 문서 사본 (아래) |

`__reference/` 내용:

| 파일 | 원본 위치 | 비고 |
| --- | --- | --- |
| `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` | `../mef_fits_spec/` | L0 MEF ICD **현행 v4.1**. 바이트 동일 사본 |
| `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1_KO.md` | — | v4.1 ICD의 **국문본. 이 디렉토리가 유일본** |
| `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` | `../mef_fits_spec/` | 규격 6.5절 대조표의 원본. 바이트 동일 사본 |
| `KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` | `../mef_converter/` | Archon raw 검증 결과. 바이트 동일 사본 |
| `CCD290-99 datasheet (V2 - Aug 2016).pdf` | e2v A1A-778871 V2 | **검출기 데이터시트** (운영자 확보 2026-08-22) — raw spec **부록 A** 의 원전: image section A/D · 레지스터 1152+prescan 27(레거시 `PRESCANX=27` 출처) · OS1–16 · split-frame 독출 |
| `CCD47-20.pdf` | e2v A1A-CCD47-20 Issue 7 (2003-04) | **guide 검출기 데이터시트** (운영자 확보 2026-08-30) — raw spec **9장** 원전: frame-transfer · image 1024×1024 (13 μm) · store 1024×**1033** · 다크 기준열 16/측 · 출력 amp 2 |
| `guide_ccd_format.xlsx` | — | **guide 프레임 구성 원자료** (운영자 작성 2026-08-30) — raw spec **9.4절** 정본: 4224 = [16\|512\|512\|16]×4블록, 1033 = 1024+9 |
| `Detector_and_Amp_Info_cards_v1.0.txt` | — | **확정 Detector/Amplifier 카드 블록** MK·NT 정본 (구 AMPCARD.txt, v1.0 승격 2026-08-21) |
| `Archon_Unit_Info.txt` | — | **사이트별 Archon 유닛 정체** — SCI×2 + GUI×1 의 유닛 ID(`<SITE>-SCI-101` 등, ID 숫자 = IP)와 STA 시리얼. `CTRL1ID`/`CTRL1SN`/`CTRL2ID`/`CTRL2SN` 실값의 원자료 |
| `Tel pos & limit (20230519).txt` | — | 망원경 지향·리밋 기록 (2023-05-19) — TCS 절 검토용 |
| `Legacy raw fits header samples/` | — | **레거시 시스템의 FITS 헤더 실측본** (2026-08-12 추가). `KMTNk.20170209.044131.Rawheader.txt` 가 이 규격에 대응하는 **레거시 raw 헤더**이고, `xkmta.20170209.044131.MEF.*.txt` 는 레거시가 MEF 로 변환한 산출물의 헤더다(primary 1 + 확장 35). raw 헤더는 2017→2021 사실상 불변이어서 정착된 설계로 읽을 수 있다 — 규격 5장 식별 keyword 재정의의 근거 |

> ⚠️ `KMTNc.20210503.030331.header.txt` 는 **raw pair 가 아니다.** `DETID='C'` · 1616×1616 인데, raw 영상의 ROI 조각들을 모자이크로 재구성한 **combination 산출물**이다(운영자 확인 2026-08-12). 검출기 이름이 아니므로 이 규격 범위 밖이고, `M,K,N,T` 4개 전제에 영향을 주지 않는다.

**국문 ICD를 뺀 나머지는 사본이며 기준본은 원본 위치의 것이다.** 원본이 개정되면 이 사본도 함께 갱신하거나 삭제한다.

**전량 md 로 이관했다 (2026-08-11).** 이전에는 docx 4개였고, 그중 셋은 원본 위치에 이미 md 기준본이 있어 사본만 형식을 맞췄다. 국문 ICD 는 유일본이면서 v4.0 에 머물러 있었으므로 **md 변환과 함께 v4.1 로 갱신**했다 (파일명 사이트 코드 D-011 · NT 헤더 완전성 OI-8 · converter v2.2.0). 원 docx 4개는 git 이력에 남아 있다.

> **사본 3개는 바이트 동일하므로 동기 확인이 한 줄이다.** 출력이 없으면 원본과 같은 것이다.
>
> ```bash
> diff -q __reference/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md    ../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md
> diff -q __reference/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md ../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md
> diff -q __reference/KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md        ../mef_converter/KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md
> ```
>
> 국문본은 대응 원본이 없으므로 이 검사 대상이 아니다 — 영문 v4.1 이 개정되면 **사람이 대조해 옮겨야 한다.** 절 구조가 1:1(15절, 표·목록 개수 동일)로 유지되고 있으니 절 단위로 비교하면 된다.

## 규격이 다루는 것 / 다루지 않는 것

| 다룬다 | 다루지 않는다 |
| --- | --- |
| 파일 구조 (HDU · BITPIX · 크기 · 패딩) | amp별 `GAIN` / `RDNOISE` / `SATLEVEL` / `LINMAX` → calibration DB |
| 픽셀 배치 (amp tile · overscan · 상하 분할 · 행 순서) | crosstalk coefficient → calibration DB |
| 헤더 keyword (필수/권장, 출처, MEF 목적지) | WCS 해 → L1 |
| amp ↔ module/channel 배선 맵 | MEF 구조 keyword (`EXTNAME` · section 좌표 등) → converter 파생 |
| MK/NT pair 일관성 규칙 | ~~guide CCD 자료~~ → **v1.9 부터 규격 9·10장이 다룬다** |
| Converter가 읽는 값과 누락 시 영향 | L0 MEF 내부 구조 → `mef_fits_spec/` |

raw spec **5.10절**이 "raw 에 넣지 않는 keyword"의 경계를, **6장**이 MEF·파이프라인이 알아야 할 연동 요점을 담는다. MEF keyword 전량 대조표와 L1 `CARRY_KEYS` 추적은 원장(Header_and_Refs)과 archive 의 구판 6.5·6.6절이 원자료다.

## 규격을 구현하는 곳

| 주체 | 파일 | 상태 |
| --- | --- | --- |
| **신규 ICS (시뮬)** | [`../ics_sim/ics_sim/rawpair.py`](../ics_sim/ics_sim/rawpair.py)(이름) + [`rawhdr.py`](../ics_sim/ics_sim/rawhdr.py)(카드) + [`config.py`](../ics_sim/ics_sim/config.py)(사이트 — `[node] observatory` 한 줄, D-017. 구 `siteid.py` 는 IP 판정 폐지와 함께 삭제됐다) + `sequencer._store()` + `hardware/sim.py`의 `write_frame()` | **동작 중** — 헤더 5장을 **템플릿 주도**로 재편해 견본 pair 를 **바이트 단위로 재현**한다(`rawcards.py` = 견본의 기계 사본, 대사 시험 `tests/test_raw_draft.py`). v1.3 정렬 잔여(D-016 충돌 처리 · 정체성 카드 재편 · 컨트롤러 블록 · 신설 HK/돔 카드 · 절 번호 참조)는 **전량 완료**(DevNote 11.19~11.21), 이후 v1.4~**v1.8** 개정분도 반영했다. 테스트 **330** |
| **신규 ICS (실기)** | [`../ics_archon/`](../ics_archon/README.md) — `archon/backend.py` + `archon/fitswrite.py`(raw pair 바이트 기록) | **구현 완료 · 실기 미검증.** `ics_sim` 을 사본 없이 그대로 쓰고 `DetectorBackend` 자리만 채운다(D-012). ⚠️ `ics_sim/hardware/archon.py` 는 **시뮬 패키지에 남은 스텁**이고 실기 경로가 아니다 |
| 실험실 취득 | [`../cam_char/archon/archon_kmtnet_labtest_v2.py`](../cam_char/archon/archon_kmtnet_labtest_v2.py)의 `write_fits()` | 동작 중 — geometry/telemetry 카드 보강 필요 |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) | 동작 중 — MK 헤더만 읽음, NT 헤더 반영 필요 |

## 결정된 사항 · 남은 open item

v1.0에서 제기한 OBSAgent 규약 충돌 2건은 **v1.1에서 해결되었고** (DECISION_LOG D-009 / D-010), 파일명은 **v1.2에서 사이트 코드 prefix로 재개정되었다** (D-011, D-009 대체).

| ID | 결정 |
| --- | --- |
| ~~OI-1~~ | 파일명은 `<SITE>.<YYYYMMDD>.<NNNNNN>.<DETID>.fits`, `<SITE>` ∈ {`KMTC`, `KMTS`, `KMTA`, `KMTK`} (D-011, 2026-08-10 · 넷째 코드는 **D-017**, 2026-08-25 개정). `<NNNNNN>`는 **6자리 zero-padding 필수**. converter v2.2.0에서 정규식 개정 + `OBSERVAT` 교차 검증 |
| ~~OI-2~~ | **저장 단위와 통보 단위를 분리.** 파일은 컨트롤러당 1개(2개), `STATUS: Wrote`는 CCD당 1회(4회)를 레거시 형태 논리 이름(`KMTN<c>.…`, 불변)으로 발신. OBSAgent 변경 없음 |
| ~~OI-8~~ | NT 헤더 완전성 요구가 **ICD v4.1에 반영되었다** (2026-08-10) |
| ~~OI-10~~ | 파일명 `<YYYYMMDD>`는 **그 사이트의 관측일**이다 — UT 에 사이트별 보정을 더한 뒤 날짜만 취한다. 경계는 세 사이트 모두 현지 12:30 (D-014, 2026-08-13). 종전 잠정안(UT 날짜)은 한 밤의 자료를 두 디렉토리로 갈랐다 |
| ~~OI-11~~ | CTIO · SAAO · SSO 측지값을 운영자가 확정해 `ics_sim.ini` 의 사이트별 절에 넣었다 (2026-08-13) |
| ~~OI-12~~ | 파일명 날짜부가 `DATE-OBS` 날짜와 **어긋나는 것이 정상**이다 — OI-10 이 관측일 기준으로 확정되면서 해소됐다 (2026-08-13) |

부작용 하나가 따라온다 — **`LASTFILE`이 더 이상 실재하는 경로가 아니다.** 아카이브·DTS 도구는 `LASTFILE` 대신 raw 헤더의 **`FILENAME`(+`EXPID`)** 을 근거로 삼아야 한다 (**D-016**, 2026-08-22 등재 · **v1.6 에서 `ORIGNAME`→`EXPID` 개정**). **아카이브 유일 키는 `FILENAME`** 이다 — 충돌 시 격리 대신 **노출 번호를 증가**시켜 저장하므로 유일성이 구조로 보장되고, `EXPID`(카운터가 처음 배정한 이름)과의 **값 불일치가 충돌 신호**다. `UNIQNAME` · `NAMECLSH` · `clash/` 격리는 폐지됐다 — 상세는 [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.8.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.8.md) Part 2 · raw spec 2.3절.

남은 open item 은 **raw spec 8장(science)과 10.6절(guide)** 에 있다 — 포장 조항 준수 검증(OI-3) · 중앙 overscan 분배(OI-4) · binning(OI-5) · checksum(OI-7) · 셔터 반영 지연(OI-13) · **Radionode 원값 포맷(OI-16 — 구칭 Tapaculo, v1.9 개명)** · e2v 데이터시트 대응 잔여 ③(OI-17) · NT `CCDTEMP` 귀속(OI-18 — **폐기 예정**, 물음의 전제가 사라졌다) · **guide OI-20~24**(X 528 구간 · 9행/칩 방위 · `PIXSCALE` · 노출 규약 잔여 · 카드 설계 잔여). **전부 실기 실측·자료 확보·협의가 있어야 닫힌다.** ~~OI-15~~(X overscan 4:4)는 **v1.5 에서 종결**, ~~OI-9~~(배선 실측)는 **v1.8 에서 폐기**, ~~OI-19~~(guide `Cn_TEMP` 자리)는 **v1.9 에서 종결**(10.4절 수록)됐다.

## 버전 / 관리 정책

- Raw geometry/포장이 바뀌면 **`CAMVER`(HW) 또는 `CTRLxCFG`(설정)** 가 바뀐 것이어야 하며(raw spec 4.3절 — 별도 `RAWVER` 카드는 없다), L0 의 `GEOMVER` 도 같은 변경으로 갱신한다.
- 이 규격 · L0 ICD · converter는 같은 geometry를 가리켜야 한다. 셋 중 하나만 바꾸지 않는다.
- 새 버전을 현행으로 올릴 때 이 README의 "현재 기준선"을 함께 갱신하고, 구버전은 `archive/`로 옮겨 이력을 보존한다.
- 대용량 raw FITS는 Git에 넣지 않는다 (`.gitignore`). 로컬 `raw/`에서 다루고 파일명 · SHA256 · 생성 command를 문서에 기록한다.

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| **작업 이어갈 때의 컨텍스트** | [`SMC_CLAUDE.md`](SMC_CLAUDE.md) — 진행 상태 · 검토 중인 카드 · 남은 판단 |
| L0 MEF 규격 (keyword/ICD) | [`../mef_fits_spec/README.md`](../mef_fits_spec/README.md) |
| Converter | [`../mef_converter/README.md`](../mef_converter/README.md) |
| L0→L1 전처리 파이프라인 | [`../mef_pipeline/README.md`](../mef_pipeline/README.md) |
| 신규 ICS 개발 노트 | [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) |
| Archon 실험실 취득 | [`../cam_char/archon/ARCHON_LABTEST_V2.md`](../cam_char/archon/ARCHON_LABTEST_V2.md) |
| 기술 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |
| 프로젝트 관리 보드 | [`../project_management/README.md`](../project_management/README.md) |

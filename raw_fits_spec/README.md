# KMTNet-CEU Raw FITS Specification

최종 갱신일: 2026-09-24

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

> ✅ **현행 규격: [`KMT_CEU_Raw_FITS_Specification_v1.16.md`](KMT_CEU_Raw_FITS_Specification_v1.16.md) — "raw spec"** (**v1.16** · 2026-09-24 · 태그 **`raw-spec-v1.16`**).  구 "Raw FITS Pair 규격" v1.2 를 개명·대체한 문서다.
> ⭐ **v1.16 은 `OBSTYPE` 을 사용자 입력 카드로 두고 `EXPTIME` 을 실수형으로 정했으며 견본 comment 문안을 정정했다**(운영자 확정 2026-09-24).  `OBSTYPE` 은 `PROJID` 와 같은 부류로, 기본값은 science `'SCIENCE'` · guide `'GUIDE'` 이고 빈 값이 와도 `IMAGETYP` 을 복사하지 않는다 — 계통 식별은 `DATASRC` · `DETID` 가 맡는다.  `EXPTIME` 은 science·guide 모두 실수형이다 — 소수점 아래 최소 한 자리(`0.0` · `2.0`, 소수부가 있으면 그대로 `0.25`).  comment 는 `OBSTYPE` 을 *"User-defined observation type"* 으로 바꾸고, geometry 네 장(`PRESCNX`/`PRESCNY`/`OVRSCNX`/`OVRSCNY`)의 괄호 · 채널 맵 `COMMENT` 의 *"within each card"* 를 걷고, science `ICSBUILD` 의 *"ICS/ICG"* 를 *"ICS"* 로 줄이고, `DSTELALT`/`DSTELAZ` 에 단위(*"in degrees"*)를 달았다.  guide 견본은 기동 기본값(`IMAGETYP` `'OBJECT'` · `OBJECT` `'guide'` · `EXPTIME` `2.0`)으로 바꿨다.  동반 판올림은 원장 **v1.22**(3.1절 `OBSTYPE` · `EXPTIME` 행 등 — 판정 불변) · 통합 **v1.2**(§1 기록 행 신설 — MEF 쪽 계통 판별은 `DATASRC`)이고, 견본 6장은 `v1.16` 으로 이름과 내용을 함께 바꿨다(레코드 수·크기 불변).
> 판별 변경은 규격 **12장**과 원장·통합 문서의 **머리 changelog** 가 든다 — 각 판의 발행본은 `archive/` 에 있다.

> ⏭️ **판올림 이월 대기 1건** — **바이어스 측정값의 헤더 카드 배치(D3)**.  견본 카드 변경을 동반하므로 **guide 견본 ↔ 규격 10장 대사 확인 목록을 해소하는 라운드**에서 함께 처리한다.  상세는 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "규격 쪽 후속".
>
> ⚠️ **구판 절 번호를 인용한 문서·코드 주석은 현행 기준으로 재확인할 것** — v1.4 에서 2.5절(Wrote 통보)이 삭제돼 2장은 2.1~2.4 다.  v1.15 는 기존 절 번호를 그대로 두고 소절(5.2.1 · 5.6.3 · 5.6.4 · 8.1 · 10.3.1 · 10.6.1)을 보탰고, 10.1-7 은 (a)~(g) 소항목으로 나눴다(항목 번호는 그대로) — 옮겨 간 규범(예: HK 원천·신선도 → 5.6.3절)은 새 소절에서 찾는다.  v1.16 은 절 번호를 바꾸지 않았다.  ICD 와 `ics_sim`/`ics_archon` 주석의 판 참조 갱신은 각 소관의 일감이다 — ICD **v4.3** 은 `KMT_CEU_Raw_FITS_Specification_v1.13.md` 를 인용하는데(백틱 경로라 링크는 아니다) 그 파일이 `archive/` 로 갔으므로, 현행 경로로의 갱신 요청이 LEECU 소관으로 남아 있다(통합 문서 §3).

| 구분 | 문서 | 버전 | 상태 |
| --- | --- | --- | --- |
| **Raw spec (현행)** | [`KMT_CEU_Raw_FITS_Specification_v1.16.md`](KMT_CEU_Raw_FITS_Specification_v1.16.md) | **v1.16** | ✅ 현행 |
| 카드 판정 원장 | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.22.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.22.md) | **v1.22** | ✅ 현행 |
| MEF·파이프라인 파급 (통합 문서) | [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.2.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.2.md) | **v1.2** | ✅ 현행 |

연동 기준:

| 항목 | 값 |
| --- | --- |
| Raw 규격/구성 버전 파악 | 별도 버전 카드 없음(`RAWVER` 미도입 — 원장 v1.13 확인 요망 11) — **`CAMVER`(HW) · `CTRLxCFG`(FW/설정) · `DETID` · `CHMAP_*` 조합**으로 파악.  취득 SW 쪽 헤더 규칙의 세대는 `ICSBUILD`(guide 는 `ICGBUILD`)로 가린다(raw spec 5.10절) |
| 파일 구성 | 노출 1회 = raw FITS 2개 (`MK` = M,K / `NT` = N,T) |
| 파일명 | `<SITE>.<YYYYMMDD>.<NNNNNN>.<DETID>.fits` (넷째 필드 이름은 v1.7 에서 명명 — 값은 `MK`/`NT`), `<SITE>` ∈ {`KMTC`=CTIO, `KMTS`=SAAO, `KMTA`=SSO, `KMTK`=KASI} (D-011 · **D-017** 개정) |
| 파일 구조 | single HDU, `BITPIX=16` + `BZERO=32768`, `19200 x 9400` |
| 파일당 amplifier | 32 (chip 2 × amp 16) |
| **Guide raw** (v1.9 신설, 규격 9·10장) | guide controller 1대 → 노출 1회 = **파일 1개** `<SITE>.<YYYYMMDD>.<NNNNNN>.G.fits`, **4224 × 1033** (CCD47-20 × 4, 채널 8), 셔터 무관 노출(`EXPTIME` = 트랜스퍼 개시 간격 · `go n` = 디지타이즈 없는 flush 1회 + 독출 `n`회 · `n`장 저장, 10.1절), 헤더는 science 골격에 **값 카드 128장**(`CTRL2*`·`C2_*` 미수록 · `CHMAP` 1장 · `IMGROT` 신설 · `LEDFLASH` → **`TRIGOUT`** 교체). 소비자는 [`../gmon/`](../gmon/) (MEF 경로 없음) |
| 기준 ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md` (v4.3, 2026-09-23 — L0 sky WCS 를 L1 Gaia 측성의 **seed** 로 규정(D-023) · `AMPINFO` 배선 열(C-11) · `VOLTINFO` 실측 레일(C-18) · converter v2.5.0 기준. 구 v4.2·v4.1 은 `../mef_fits_spec/archive/`) |
| 기준 MEF keyword 정의서 | `../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md` (v1.1, 2026-09-23 — converter v2.5.0 기준. 구 v1.0 은 `../mef_fits_spec/archive/`) |
| 기준 converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (**v2.5.0** — 파일명 접미사 `_v2_1` 은 그대로이고 판은 `SOFTWARE_VERSION` 이 말한다) |

## 디렉토리 구조

| 경로 | 내용 |
| --- | --- |
| `KMT_CEU_Raw_FITS_Specification_v1.16.md` | ✅ **현행 raw spec** — 파일 구조 · 파일명(D-011/D-014) · 충돌·정체성(D-016) · geometry(포장 규범 조항 + amp 전수 표 64행 + X overscan `RRRRLLLL`) · 헤더 keyword **136장**(science 견본 pair 기준) · MEF/파이프라인 연동 요점 · 검증 체크리스트 · OI · **guide raw FITS 9·10장**(파일·기하 / 노출 의미론·헤더 — science 와 분리) · e2v 데이터시트 부록.  배경·경위는 원장과 통합 문서가, 판별 변경은 12장이 든다 |
| `archive/` | **최근 구판만 유지** — 운영자가 주기적으로 살펴보고 없어도 될 파일은 지운다(2026-09-24 기준: Header_and_Refs v1.8~**v1.21** · Specification v1.2~**v1.15** · Impacts_and_Identity v0.5~**v1.1** 이 잔류). 지워진 구판·전신 문서(MEF_Impacts·Numbering_and_Identity·raw↔MEF 키워드 대응표 등)는 **git 이력과 운영자 외부 백업(`__backup_raw_fits_spec_oldver`)에 보존** — 대응표의 살아있는 내용은 전부 흡수됐다: **판정 준거는 Header_and_Refs 0장**, 카드 대응은 같은 문서 각 장의 `Use in MEF` 열, MEF/converter 쪽 이관 안건 4건은 통합 문서 §6 이다 — 넷째(`DATASRC`·`CTRL1CFG`/`CTRL2CFG` 의 MEF 목적지)는 converter v2.5.0 이 PRIMARY 중계로 닫았고, 미결 셋(`NCTRL` 정의 · `CTRLID` 개칭 · `SATURAT`↔`SATLEVEL` 통일)의 본문은 같은 문서 §7-7~7-9(LEECU 판단 항목)에 있다 |
| `KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.22.md` | ✅ **현행 원장 — 카드 판정 원장.**  **0장이 판정 준거다**(준거 순위 · converter 3상태 × ICD 규정/침묵 교차표 · 준거 공백 · 추출 함정).  raw 카드 기준은 **레거시 raw 실측 헤더**이고 **레거시 123개를 전량 귀속**시킨다 — converter 가 읽는 것 · 읽지 않는 것(1~6장) · 도입 후보·확정(7장) · 폐지(8장·8.1·8.2) · 전량 귀속(9장), 10~12장은 subframe 제기 · converter 자기 상수 카드 · raw 직접 사용자 안내, 13장은 종합이다.  판별 변경은 머리 changelog 가 든다 |
| `KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.2.md` | ✅ **현행 통합 문서** — 표제 "Raw FITS 헤더 개정에 따른 MEF ICD · MEF Converter 개정 및 검토 사항".  **Part 1** = LEECU 전달용 개정 요청 목록 — C-항목 신설·개정, raw↔MEF 이름 대응, ICD·정의서 개정 후보, MEF/converter 쪽 이관 안건 4건(§6 — 넷째는 converter v2.5.0 이 닫았다), 그리고 **§7 MEF converter 및 PIPELINE 판단 필요 항목**(7-1~7-10) — raw 규격이 정하지 않고 MEF 쪽(converter · `mef_pipeline` · 아카이브)이 골라야 하는 것만 모은 절이다: 반쪽 pair 의 성한 절반 보관(DECISION_LOG D-001 과 맞물린다) · raw 가 공급하지 않는 MEF 카드의 처분 · 멈춤 기준 · §6 미결 셋 · MEF 에 raw 내용 해시 등.  **Part 2** = 번호·충돌·정체성의 **파급 요약** — 정본은 raw spec 2.3절 + D-016(내용 이중화 방지 축약).  판별 변경은 머리 changelog 가 들고, 구판 v0.5~v1.1 은 `archive/`, 전신 문서 v0.4·v0.2 는 git 이력·외부 백업이다 |
| `header_samples/KMTA.20260821.123456.G.…v1.16.txt`<br>`…v1.16+LF.txt` | **guide 헤더 견본 (정본)** — 규격 10장 표가 *견본 v0.0* 으로 부르는 것이다.  값 카드 **128장** + COMMENT 8 + END 1 + 공백 7 = **144 레코드**, 4×2880 = **11,520 바이트**.  `+LF` 는 메모장용 사본(11,669 B — LF 와 꼬리 `#EOF` 를 걷어내면 정본과 동일).  ⏳ 규격 10장과의 **대사 확인 목록은 `SMC_CLAUDE.md`** — 견본과 10장이 어긋나면 10장이 이긴다 |
| `header_samples/KMTA.20260821.123456.MK.fits.header.v1.16.txt`<br>`…NT.fits.header.v1.16.txt`<br>(각 `…v1.16+LF.txt` 메모장용 사본) | **science 헤더 견본 pair — 정본** (구 `확정 초안 헤더 v1.0 pair`).  NT 는 MK 와 **pair 상이 카드 6장**만 다르다 — `DETID`='NT' · `CHMAP_LT/LB/RT/RB`(raw spec 4.5절 표 = `Detector_Ch_to_AmpID_Map_v1.1.txt` 의 NT 행 — 4자 토큰) · `FILENAME`(`.NT` `DETID` 필드).  **`EXPID` 는 `DETID` 필드가 없어 양쪽 동일**이고 나머지 130장도 같다.  각 **180 레코드 = 값 카드 136 + COMMENT 8 + END 1 + 공백 35**, 5×2880 = 14,400 바이트.  메모장용 사본 `…v1.16+LF.txt`(14,585 B)는 **LF 와 꼬리 `#EOF` 를 함께 걷어내면 정본과 바이트 동일**하다.  검토 왕복 이력(docx 왕복본 · 초안 v0.0~v0.4.4)은 운영자 외부 백업(`__backup_raw_fits_spec_oldver`)에 있다 |
| `Detector_Ch_to_AmpID_Map_v1.1.txt` | ✅ **검출기 출력 채널 ↔ MEF AmpID 64행 맵 (현행, 이 폴더 루트)** — CtrUnit–Port–CCD/CH–IMGSEC–MEF_AmpID.  `CHMAP_*` 카드와 raw spec 4.5절 amp 전수 표의 **기계 가독 정본**이고, 채널 토큰은 4자 `<chip><A\|D><nn>` 이다.  `__` 읽기 전용 규칙상 `__reference/` 의 구 v1.0 을 고치지 않고 사본을 루트로 올려 고친 판이며, 구 v1.0 은 지웠다(경위는 규격 12장 v1.7 — 원본은 git 이력 `44ab878`~) |
| `tools/` | `md_to_docx.py` — 개정판 md 를 검토 전달용 docx 로 변환한다.  **검토 사이클이 열릴 때만** 쓴다 — 판올림마다 만드는 것이 아니다(`SMC_CLAUDE.md` 개정 워크플로, 운영자 확정 2026-08-22) |
| `__reference/` | 규격 작성 시 대조한 참고 문서 사본 (아래) |

`__reference/` 내용:

| 파일 | 원본 위치 | 비고 |
| --- | --- | --- |
| `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` | `../mef_fits_spec/archive/` | ⏳ **L0 MEF ICD 구판 v4.1 의 사본.** `archive/` 원본과는 바이트 동일이지만 **현행 준거는 `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md`** 다 (2026-09-23, D-023 — 그 앞 v4.2 는 2026-09-04, D-017). 아래 사본 규칙대로 현행판으로 갱신하거나 지워야 하는데, 국문본이 v4.1 에 묶여 있어 **운영자 판단 대기**다 |
| `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1_KO.md` | — | v4.1 ICD의 **국문본. 이 디렉토리가 유일본.** ⏳ 영문이 v4.2(2026-09-04) · v4.3(2026-09-23)으로 두 번 개정됐으므로 **v4.2 분(머리말 판 표기 · 기준 표 원시 파일명 행 · §2.1 제목 · 사이트 코드 넷째 `KMTK`/`KASI` 행 + "Changed in v4.2" 단락 · converter 참조 · §11 converter v2.4.0 · v2.3.0 `--ampchar` · §12 · §13)과 v4.3 분(머리말 판 표기 · 기준 표 3행 `PRODVER`/`GEOMVER`/Reference converter · §2 OI-8 단락의 raw spec 경로 · §2.1 D-020 단락 · converter 판 · raw spec 경로 · §5 HDU 불변 주 · `VOLTINFO`/`TELEMETRY` 행 · §6 방향 주(D-023 4항) · §7 `AMPSEQ` 주 · `TRIMSEC`/`PRESEC`/`DETSEC` 열 · §7.1·7.2 seed WCS 신설(D-023) · §8 `AMPINFO`(C-11 · seed WCS 열) · §9 `VOLTINFO`·`TELEMETRY`(C-18) · §10 · §11 converter v2.5.0 · §12 · §13)이 미반영**이다 — 두 목록은 영문 v4.1↔v4.2↔v4.3 을 절 단위로 대조해 뽑았다 |
| `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` | `../mef_fits_spec/archive/` | ⏳ **MEF keyword 정의서 구판 v1.0 의 사본** — 구판 규격 6.5절 대조표의 원본이다. `archive/` 원본과 바이트 동일하지만 **현행은 `../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md`**(2026-09-23)다.  아래 사본 규칙대로 갱신하거나 지울 대상이고, `__` 폴더라 운영자 몫이다 |
| `KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` | `../mef_converter/` | Archon raw 검증 결과. 바이트 동일 사본 |
| `CCD290-99 datasheet (V2 - Aug 2016).pdf` | e2v A1A-778871 V2 | **검출기 데이터시트** (운영자 확보 2026-08-22) — raw spec **부록 A** 의 원전: image section A/D · 레지스터 1152+prescan 27(레거시 `PRESCANX=27` 출처) · OS1–16 · split-frame 독출 |
| `CCD47-20.pdf` | e2v A1A-CCD47-20 Issue 7 (2003-04) | **guide 검출기 데이터시트** (운영자 확보 2026-08-30) — raw spec **9장** 원전: frame-transfer · image 1024×1024 (13 μm) · store 1024×**1033** · 다크 기준열 16/측 · 출력 amp 2 |
| `guide_ccd_format.xlsx` | — | **guide 프레임 구성 원자료** (운영자 작성 2026-08-30) — raw spec **9.4절** 정본: 4224 = [16\|512\|512\|16]×4블록, 1033 = 1024+9 |
| `Detector_and_Amp_Info_cards_v1.0.txt` | — | **Detector/Amplifier 카드 블록의 확정 당시(2026-08-21) 원자료** MK·NT (구 AMPCARD.txt, v1.0 승격 2026-08-21).  ⚠️ **현행 정본이 아니다** — 채널 토큰이 3자(`N08` 등)이고 `CHMAP_*` comment(`CCD output ch`)·카드 구성(`CAMVER` 없음 · MK 블록의 `DETECTOR`→`FPAID` 순서 — NT 블록은 현행 견본과 같은 `FPAID`→`DETECTOR`)도 현행 견본과 다르다.  현행 정본은 루트의 `Detector_Ch_to_AmpID_Map_v1.1.txt` 와 `header_samples/` 견본이다 |
| `Archon_Unit_Info.txt` | — | **사이트별 Archon 유닛 정체** — SCI×2 + GUI×1 의 유닛 ID(`<SITE>-SCI-101` 등, ID 숫자 = IP)와 STA 시리얼. `CTRL1ID`/`CTRL1SN`/`CTRL2ID`/`CTRL2SN` 실값의 원자료 |
| `Tel pos & limit (20230519).txt` | — | 망원경 지향·리밋 기록 (2023-05-19) — TCS 절 검토용 |
| `Legacy raw fits header samples/` | — | **레거시 시스템의 FITS 헤더 실측본** (2026-08-12 추가). `KMTNk.20170209.044131.Rawheader.txt` 가 이 규격에 대응하는 **레거시 raw 헤더**이고, `xkmta.20170209.044131.MEF.*.txt` 는 레거시가 MEF 로 변환한 산출물의 헤더다(primary 1 + amp 확장 32 = 33장). raw 헤더는 2017→2021 사실상 불변이어서 정착된 설계로 읽을 수 있다 — 규격 5장 식별 keyword 재정의의 근거 |
| `KMTNk.20170209.044131.Rawheader.txt` | `Legacy raw fits header samples/` | 원본 위치 칸의 폴더(`__reference/` 의 하위 폴더)에 있는 같은 이름 파일과 **바이트 동일한 중복 사본**(2026-08-22 `e728e02` 부터).  짝이 `__reference/` 안에 있으므로 아래 「사본 3개」 동기 확인(바깥 원본의 사본)에는 들지 않는다.  지울지는 운영자 판단이다(`__` 폴더) |

> ⚠️ `KMTNc.20210503.030331.header.txt` 는 **raw pair 가 아니다.** `DETID='C'` · 1616×1616 인데, raw 영상의 ROI 조각들을 모자이크로 재구성한 **combination 산출물**이다(운영자 확인 2026-08-12). 검출기 이름이 아니므로 이 규격 범위 밖이고, `M,K,N,T` 4개 전제에 영향을 주지 않는다.

**국문 ICD를 뺀 나머지는 사본이며 기준본은 원본 위치의 것이다.** 원본이 개정되면 이 사본도 함께 갱신하거나 삭제한다.

**전량 md 로 이관했다 (2026-08-11).** 이전에는 docx 4개였고, 그중 셋은 원본 위치에 이미 md 기준본이 있어 사본만 형식을 맞췄다. 국문 ICD 는 유일본이면서 v4.0 에 머물러 있었으므로 **md 변환과 함께 v4.1 로 갱신**했다 (파일명 사이트 코드 D-011 · NT 헤더 완전성 OI-8 · converter v2.2.0). 원 docx 4개는 git 이력에 남아 있다.

> **사본 3개는 짝과 바이트 동일하므로 동기 확인이 한 줄씩이다.** 출력이 없으면 짝과 같은 것이다.  ⏳ **현행 원본과 짝이 서 있는 것은 Work_Summary 하나뿐이다** — ICD 사본(v4.1)은 원본이 v4.2 → v4.3 으로, Keywords 사본(v1.0)은 원본이 v1.1 로 판올림되면서 짝이 `../mef_fits_spec/archive/` 로 옮겨갔기 때문이다(2026-09-23 확인 — 두 사본 모두 `archive/` 의 구판과 바이트 동일).
>
> ```bash
> # ⏳ ICD·Keywords 사본은 구판(v4.1 · v1.0)이라 현행 원본과 짝이 없다. 구판 동기만 확인된다:
> diff -q __reference/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md    ../mef_fits_spec/archive/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md
> diff -q __reference/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md ../mef_fits_spec/archive/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md
> diff -q __reference/KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md        ../mef_converter/KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md
> ```
>
> 국문본은 대응 원본이 없으므로 이 검사 대상이 아니다 — 영문이 개정되면 **사람이 대조해 옮겨야 한다.** 절 구조는 v4.2 까지 1:1(15절, 표·목록 개수 동일)이었으니 절 단위로 비교하면 된다 — ⚠️ **v4.3 은 §7 밑에 7.1·7.2 소절을 새로 두어** 그 두 소절은 국문본에 대응 자리가 없다.  ⏳ **그 조건이 이미 걸렸다** — 영문은 **v4.2**(2026-09-04) · **v4.3**(2026-09-23)으로 두 번 개정됐고 국문본은 v4.1 에 머물러 있다. 옮길 곳은 위 표의 국문본 행이 v4.2 분과 v4.3 분으로 나눠 적었다.  ⚠️ ICD 13장 개정 이력만 따라가면 빠지는 곳이 있다 — v4.3 행은 §2.1 D-020 단락 · §5 · §7 의 변경을 적지 않았고, §6 에 든 방향 주를 *"Section 4"* 라 불렀다(§4 는 v4.2 와 같다.  정정 요청은 통합 문서 Part 1 §3).

## 규격이 다루는 것 / 다루지 않는 것

| 다룬다 | 다루지 않는다 |
| --- | --- |
| 파일 구조 (HDU · BITPIX · 크기 · 패딩) | amp별 `GAIN` / `RDNOISE` / `SATLEVEL` / `LINMAX` → calibration DB |
| 픽셀 배치 (amp tile · overscan · 상하 분할 · 행 순서) | crosstalk coefficient → calibration DB |
| 헤더 keyword (필수/권장, 출처, MEF 목적지) | WCS 해 → L1 |
| amp ↔ module/channel 배선 맵 | MEF 구조 keyword (`EXTNAME` · section 좌표 등) → converter 파생 |
| MK/NT pair 일관성 규칙 | ~~guide CCD 자료~~ → **v1.9 부터 규격 9·10장이 다룬다** |
| Converter가 읽는 값과 누락 시 영향 | L0 MEF 내부 구조 → `mef_fits_spec/` |

raw spec **5.10절**이 "raw 에 넣지 않는 keyword"의 경계를, **6장**이 MEF·파이프라인이 알아야 할 연동 요점을 담는다. MEF keyword 전량 대조표는 원장(Header_and_Refs)과 `archive/` 구판 v1.2 의 6.5절이 원자료다.  구 L1 `CARRY_KEYS`(`mef_pipeline` v1.7 까지의 25키 승계 목록) 추적은 같은 구판 6.6절이고, `mef_pipeline` v1.8(2026-09-04)부터 L1 primary 는 L0 primary 를 전량 승계한다(`io_l1.CARRY_EXCLUDE` 에 든 카드만 뺀다 — raw spec 6장).

## 규격을 구현하는 곳

| 주체 | 파일 | 상태 |
| --- | --- | --- |
| **신규 ICS (시뮬)** | [`../ics_sim/ics_sim/rawpair.py`](../ics_sim/ics_sim/rawpair.py)(이름) + [`rawhdr.py`](../ics_sim/ics_sim/rawhdr.py)(카드) + [`config.py`](../ics_sim/ics_sim/config.py)(사이트 — `[node] observatory` 한 줄이 정본이다: 값 어휘는 D-017, 판별 방식은 **D-020**. ⚠️ 구 `siteid.py`(호스트 IP 판정, D-015)는 **브랜치 `ics-archon-v1.0-build` 에서 삭제**됐고 `main` 의 `ics_sim` 은 합류 대기라 파일이 아직 남아 있다) + `sequencer._store()` + `hardware/sim.py`의 `write_frame()` | **동작 중** — 헤더 5장을 **템플릿 주도**로 재편해 견본 pair 를 **바이트 단위로 재현**한다(`rawcards.py` = 견본의 기계 사본, 대사 시험 `tests/test_raw_draft.py`). v1.3 정렬 잔여(D-016 충돌 처리 · 정체성 카드 재편 · 컨트롤러 블록 · 신설 HK/돔 카드 · 절 번호 참조)는 **전량 완료**(DevNote 11.19~11.21)이고 이후 개정분도 따라간다.  ⏳ v1.16 견본의 comment 정정과 `EXPTIME` 실수형이 템플릿에 따라오기 전까지 v1.16 견본과의 바이트 대사가 어긋나고, `OBSTYPE` 빈 값 폴백 폐지도 아직 남아 있다(`SMC_CLAUDE.md` 「브랜치 후속」). ⚠️ **이 칸이 적는 것은 브랜치 `ics-archon-v1.0-build` 의 구현 상태다** — 왼쪽 링크가 가리키는 `main` 의 `ics_sim` 은 합류 대기라 `rawcards.py` 와 `tests/test_raw_draft.py` 가 아직 없고, 폐지된 `siteid.py` · `tests/test_site_id.py` 가 아직 남아 있다. ⛔ 시험 수는 여기 박지 않는다 — `python -m pytest --collect-only -q` 의 꼬리가 정본이다 |
| **신규 ICS (실기)** | [`../ics_archon/`](../ics_archon/README.md) — `ics_archon/archon/backend.py` + `ics_archon/archon/fitswrite.py`(raw pair 바이트 기록) | **구현 완료 · KASI 벤치에서 실기 가동을 시작했다**(2026-09-15 — 브랜치 `ics_archon/DevNote.md` 11.93·11.94). `ics_sim` 을 사본 없이 그대로 쓰고 `DetectorBackend` 자리만 채운다(D-012). ⚠️ `ics_sim/hardware/archon.py` 는 **시뮬 패키지에 남은 스텁**이고 실기 경로가 아니다 |
| 실험실 취득 | [`../cam_char/archon/archon_kmtnet_labtest_v2.py`](../cam_char/archon/archon_kmtnet_labtest_v2.py)의 `write_fits()` | 동작 중 — geometry/telemetry 카드 보강 필요 |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) | 동작 중 (**v2.5.0**) — amp 카드는 **그 chip 이 든 파일의 헤더**(MK·NT)에서 읽는다(C-17 반영).  PRIMARY 의 포인팅·HK 는 여전히 MK 헤더에서 읽는다.  pair 동일 카드는 두 파일 사이에서, raw geometry 선언은 MK·NT 각각 converter 상수와 대조해(선언이 없는 카드는 대조 없이 지나간다) 어긋나면 경고와 `HISTORY` 를 남기고 변환을 계속한다.  ⛔ 카드 값으로 멈추는 것은 둘이다 — pair 양쪽 `EXPID` 가 둘 다 있고 서로 다를 때(pair 동일 카드 가운데 이것만 멈춘다)와, 기본 출력 이름을 지을 때 파일명 사이트 코드가 `OBSERVAT` 와 어긋날 때다(raw spec 6장).  반영 현황은 통합 문서 Part 1 |

## 결정된 사항 · 남은 open item

v1.0에서 제기한 OBSAgent 규약 충돌 2건은 **v1.1에서 해결되었고** (DECISION_LOG D-009 / D-010), 파일명은 **v1.2에서 사이트 코드 prefix로 재개정되었다** (D-011, D-009 대체).

| ID | 결정 |
| --- | --- |
| ~~OI-1~~ | 파일명은 `<SITE>.<YYYYMMDD>.<NNNNNN>.<DETID>.fits`, `<SITE>` ∈ {`KMTC`, `KMTS`, `KMTA`, `KMTK`} (D-011, 2026-08-10 · 넷째 코드는 **D-017**, 2026-08-25 개정). `<NNNNNN>`는 **6자리 zero-padding 필수**. converter v2.2.0에서 정규식 개정 + `OBSERVAT` 교차 검증 |
| ~~OI-2~~ | **저장 단위와 통보 단위를 분리.** 파일은 컨트롤러당 1개(2개), `STATUS: Wrote`는 CCD당 1회(4회)를 레거시 형태 논리 이름(`KMTN<c>.…`, 불변)으로 발신. OBSAgent 변경 없음 |
| ~~OI-8~~ | NT 헤더 완전성 요구가 **ICD v4.1에 반영되었다** (2026-08-10) |
| ~~OI-10~~ | 파일명 `<YYYYMMDD>`는 **그 사이트의 관측일**이다 — UT 에 사이트별 보정을 더한 뒤 날짜만 취한다. 경계는 **UT 로 CTIO 16:30 · SAAO 10:30 · SSO 01:30** 이다 (D-014, 2026-08-13 — 검산 불변식 *"세 경계가 모두 현지 12:30"* 은 CTIO UTC−4 · SAAO UTC+2 · SSO UTC+11 로 센 숫자 검산이고, 민간 시각으로는 계절에 따라 CTIO 13:30 또는 SSO 11:30 이 된다.  확인은 UT 값으로 한다).  ⭐ KASI(`KMTK`)는 보정 **+9 h** — 경계 UT 15:00 = KST 00:00 이라 관측일은 KST 날짜다(운영자 확정 2026-09-12 · D-017 4항 개정).  ⚠️ 이 규칙을 구현하지 않은 취득 SW 로 찍은 KASI 파일은 보정 0 이라 UT 날짜다 — 브랜치 `982ebe5`(2026-09-13) 이전의 코드와 합류 전 `main` 의 `ics_sim`(`rawpair.py` 보정표가 아직 `'KMTK': 0`)이 그렇고, 그 가운데 KST 09:00 이전에 찍은 파일은 하루 앞선 이름을 갖는다.  종전 잠정안(UT 날짜)은 한 밤의 자료를 두 디렉토리로 갈랐다 |
| ~~OI-11~~ | CTIO · SAAO · SSO 측지값을 운영자가 확정해 `ics_sim.ini` 의 사이트별 절에 넣었다 (2026-08-13) |
| ~~OI-12~~ | 파일명 날짜부가 `DATE-OBS` 날짜와 **어긋나는 것이 정상**이다 — OI-10 이 관측일 기준으로 확정되면서 해소됐다 (2026-08-13) |

부작용 하나가 따라온다 — **`LASTFILE`이 더 이상 실재하는 경로가 아니다.** 아카이브·DTS 도구는 `LASTFILE` 대신 raw 헤더의 **`FILENAME`(+`EXPID`)** 을 근거로 삼아야 한다 (**D-016**, 2026-08-22 등재 · **v1.6 에서 `ORIGNAME`→`EXPID` 개정**). **아카이브 유일 키는 `FILENAME`** 이다 — 충돌 시 격리 대신 **노출 번호를 증가**시켜 저장하므로 유일성이 구조로 보장되고, `EXPID`(카운터가 처음 배정한 이름)과의 **값 불일치가 충돌 신호**다. `UNIQNAME` · `NAMECLSH` · `clash/` 격리는 폐지됐다 — 상세는 [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.2.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.2.md) Part 2 · raw spec 2.3절. ⭐ **저장되지 않은 프레임은 번호를 소비하지 않는다** (2.3절 8항 · **D-022**, 운영자 확정 2026-09-07) — `ABORT` 나 취득 실패로 파일이 안 생기면 번호를 되감으므로 아카이브 번호는 **연속이 원칙**이고, 남는 구멍은 예외 넷(내부 오류 · 번호 공간 고갈 · 번호 기록 파일 읽기 실패 · 종료 저장 상한 초과)뿐이다.

남은 open item 은 **raw spec 8장(science)과 10.6절(guide)** 이 정본이고, 닫힌 것은 **8.1절 · 10.6.1절**에 있다(폐기된 ~~OI-9~~ 는 12장 v1.8 행, 해결된 구판 OI(1·2·6·8·10·11·12)의 경위는 `archive/` 의 v1.2 9장).  대부분 실기 실측·자료 확보·협의가 있어야 닫히고, OI-29(`CAMVER` 값↔구성 대장) · OI-32(`PROJID` 기본값 귀속)는 운영자 판단으로 닫힌다.

## 버전 / 관리 정책

- Raw geometry/포장이 바뀌면 **`CAMVER`(HW) 또는 `CTRLxCFG`(설정)** 가 바뀐 것이어야 하며(raw spec 4.3절 — 별도 `RAWVER` 카드는 없다), L0 의 `GEOMVER` 도 같은 변경으로 갱신한다.
- 이 규격 · L0 ICD · converter는 같은 geometry를 가리켜야 한다. 셋 중 하나만 바꾸지 않는다.
- 새 버전을 현행으로 올릴 때 이 README의 "현재 기준선"(판 · 날짜 · **현행 태그 이름**)을 함께 갱신하고, 구버전은 `archive/`로 옮겨 이력을 보존한다.
- ⭐ **견본 판 번호는 규격 판 번호를 따라간다** (v1.10 이후).  판올림 때 `header_samples/` **6장**(MK·NT·G × 정본·`+LF`)의 파일명을 바꾸면, 그것을 가리키는 자리를 **한 번에** 치환한다 — 규격 머리말 연동 표(**링크 텍스트와 href 둘 다**) · 이 README 의 디렉토리 구조 표 · `SMC_CLAUDE.md`.  ⚠️ v1.12 에서 NT 견본의 **링크 텍스트만** 구판(`…v1.11.txt`)으로 남은 적이 있다 — href 가 맞으면 링크는 열리므로 눈에 띄지 않는다.
- ⭐ **규격 본문은 머리말 「작성 규칙」대로 쓴다** (v1.15) — 규범은 규칙과 출처 괄호(`D-n` · 운영자 확정 날짜)로, 경위는 12장 해당 판 행과 원장 · 통합 문서로, 읽는 쪽 안내는 `> 참고 —` 인용 블록으로, 구현 위치는 11장으로 보낸다.  이미 찍힌 파일을 읽는 데 필요한 호환 안내만 카드 행이나 6장에 한 구절로 남긴다.
- 대용량 raw FITS는 Git에 넣지 않는다 (`.gitignore`). 로컬 `raw/`에서 다루고 파일명 · SHA256 · 생성 command를 문서에 기록한다.

### 태그 — 현행 판 하나만 둔다

raw spec 태그(`raw-spec-v<판>`)는 **현행 판 하나만** 둔다 — 판을 올릴 때 옛 태그를 원격에서 지운다.  현행 태그 이름은 위 「현재 기준선」에, 판 ↔ 커밋 대장과 태그 규칙은 [`SMC_CLAUDE.md`](SMC_CLAUDE.md) 「태그 규칙」 절에 있다.

**인자 없는(또는 원격 이름만 적은) `git pull`·`git fetch`** 는 새 태그를 받아 온다 — 원격에서 지운 옛 태그는 로컬에 남는다.  저장소마다 아래 두 줄을 **한 번** 해 두면, 그 뒤로는 같은 명령이 옛 태그도 지운다.

```bash
git config fetch.prune true
git config fetch.pruneTags true
```

- ⚠️ **브랜치까지 적으면(`git pull origin main` · `git fetch origin main` 등) 설정과 상관없이 새 태그가 오지 않고 옛 태그도 지워지지 않는다** — 원격 이름만 적은 `git fetch origin`·`git pull origin` 은 인자 없는 것과 같다.  브랜치까지 적어 받았으면 인자 없는 `git fetch` 를 한 번 더 한다.
- ⚠️ **`fetch.pruneTags` 는 원격에 없는 로컬 태그를 전부 지운다** — raw-spec 태그만이 아니고, 아직 push 하지 않은 자기 태그도 지운다.  태그를 만들면 곧바로 push 하고 그 사이에 pull·fetch 하지 않는다.  이 설정은 저장소의 `.git/config` 에 들어가므로 **같은 저장소의 워크트리 전체**가 함께 쓴다.  pull·fetch 마다 지워지는 것이 싫으면 상시 설정 대신 필요할 때만 `git fetch --prune --prune-tags` 를 한다 — 이 명령도 그 순간 원격에 없는 로컬 태그를 똑같이 지우므로, push 하지 않은 태그가 없을 때 한다.
- ⚠️ **원격에서 같은 이름의 태그가 다른 커밋으로 옮겨지면**, 이 설정을 한 저장소의 `git pull` 은 `would clobber existing tag` 로 실패하고 `main` 도 따라오지 않는다(`git fetch --prune --prune-tags` 도 같다).  설정하지 않은 저장소는 실패하지 않지만 태그가 옛 커밋에 남는다.  어느 쪽이든 `git fetch --tags --force` 로 맞춘다.
- ⛔ 옛 태그가 남은 채로 `git push --tags` 나 `git push --follow-tags`(또는 `push.followTags=true` 설정)를 하지 말 것 — 지운 태그가 원격에 되살아난다.
- 설정하지 않아도 규격을 쓰는 데 문제는 없다.  남은 옛 태그는 대개 제 판의 마지막 커밋을 가리키지만 예외가 있다(`raw-spec-v1.11` = 판 첫 커밋 `a55447f` · 옮기기 전에 받은 `raw-spec-v1.5`) — 판 ↔ 커밋은 `SMC_CLAUDE.md` 태그 표로 확인한다.

위 거동은 git 2.55 로 확인했다(2026-09-24, 임시 저장소 실험).

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
| 변경 관리 (site baseline) | [`../project_management/governance/CHANGE_CONTROL.md`](../project_management/governance/CHANGE_CONTROL.md) — raw 헤더에 걸리는 것은 **CR-003**(돔 방위 셋 redis, D-021).  ⚠️ **CR-003 은 `ics-archon-v1.0-build` 의 CHANGE_CONTROL 에만 있다** — `main` 의 이 파일에는 CR-001·CR-002 뿐이고, CR-003 은 `ics_archon` 합류 때 baseline 변경으로 다시 걸린다(D-021 은 `main` DECISION_LOG 에 있다) |
| 프로젝트 관리 보드 | [`../project_management/README.md`](../project_management/README.md) |

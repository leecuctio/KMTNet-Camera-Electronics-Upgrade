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

> ✅ **현행 규격: [`KMT_CEU_Raw_FITS_Specification_v1.14.md`](KMT_CEU_Raw_FITS_Specification_v1.14.md) — "raw spec"** (2026-09-23, v1.14).
> v1.10 이 **HK 카드 5장 신설 · 온도 부호 규약 · 게이지 Off 조항 · 견본을 `header_samples/` 로 통일**했고,
> v1.11 은 그 v1.10 이 발행 뒤 제자리 개정으로 발행본과 갈려 **판을 끊은 것**이고(내용 변경 없음),
> **v1.12 는 v1.11 발행 뒤 쌓인 정합 수정을 담는다** — ⭐ **5.7.2절 신설**(ICS ↔ TC 시각 비교) · `CTRL1CFG` 를 science·guide **한 규칙**으로 · **`RDMODE` 등재**(INI 전용 · 결측 `'UNKNOWN'`) · 5.0절 출처 어휘 정정.
> v1.13 은 **실기 라운드 반영판**(돔 방위 redis(D-021) · `OBSTYPE` 계통 식별 · guide `TRIGOUT` · FSA 2자리 · guide `PRESCNX=16` · 노출 번호 규범(D-022))이고,
> **v1.14 는 `EQUINOX` 를 실수형으로 바꾼다** — `2000.0`, 결측 `-999.0` (5.7절, 운영자 확정 2026-09-23).  같은 판에 **2026-09-23 전반 재검토 결과**를 담았다 — science HK 원천을 **`GO` 마다 `HKDATA NOW`** 로(5.6절) · `KMTK` 관측일 보정 **+9 h**(경계 KST 자정, 2.2절 · D-017 4항 개정) · guide `BIAS` = 최소 노출 · 기동 `EXPTIME` 2 s(~~OI-24~~ 종결) · converter **v2.5.0** · ICD **v4.3** · Keywords **v1.1** 재대조(6장 — 카드 값 하드 실패는 둘) · 운영자 결정 일곱(**`DATE-OBS` = 모든 영상(`DARK`·`BIAS` 포함)의 적분 개시**(5.4절) · guide `TRIGOUT` 판정 창 = **그 프레임의 노출 창 ± 여유 `g`**(`[icg] trigout_guard`, 기본 0.15 s — 2026-09-23 의 *"창 `[DATE-OBS, 독출 완료]` 의 겹침은 의도"* 를 2026-09-24 에 고쳤다, 10.3절) · `CTRLnID`/`CTRLnSN` 은 INI 가 비면 `'NC'`(5.5절 · 10.3절) · `CHECKSUM`/`DATASUM` 미도입 확정(~~OI-7~~ 종결, 5.10절) · `RDMODE` 결측도 `'NC'` 로 통일(5.0절) · 돔 방위 셋 `DSAZ`·`DSTELAZ`·`DAZERR` 소수 3자리(5.7.3절) · `HKDATA NOW` 는 Radionode 를 치지 않는다(5.6절)) · 사실 정정 · 표 렌더 결함 · 끊긴 링크와 낡은 판 표기 정정.
> 아래는 그 이전 경위다 — 2026-08-18~22 전면 재검토(확인 요망 11건 전량 종결 · D-016 등재)의 재작성판(v1.3) → 운영자 1~4장 검토 반영(v1.4) → 5장(헤더 keyword) 검토 개시분(v1.5) → 노출 정체성 카드 개정(v1.6 — `ORIGNAME` → **`EXPID`** · `FILENAME` comment) → 파일명 넷째 필드 명명(v1.7 — `<DETID>`) → `OI-9` 폐기·`CTRLnCFG` 정합(v1.8) → **v1.9 가 guide raw FITS 를 9·10장으로 신설하고 환경 센서 장치명을 `Tapaculo` → `Radionode` 로 바꾼다** (운영자 지시 2026-08-30). 구 "Raw FITS Pair 규격" v1.2 를 개명·대체한다(구판은 `archive/`).

> ⏭️ **판올림 이월 대기 1건** (구 "v1.9 대기 5건" — ~~`CCDTEMP` comment 의 chip 귀속(`M`) 제거~~ 는 **2026-08-30 운영자 지시로 조기 실행**, 견본 3장 제자리 반영): **바이어스 측정값의 헤더 카드 배치(D3)** 하나다.  ⭐ ~~`OI-18` 폐기~~ 는 **v1.10 에서 이행**됐고, ~~`RDMODE` 결측값 등재~~ 는 **v1.12 에서 닫혔다**(INI 전용 · 결측 `'UNKNOWN'` · ACF 유도 제거, 5.5절), ~~`CAMVER` 범프 규범 명시(듀어 RTD 배치 변경 포함)~~ 는 **v1.13 에서 닫혔다**(5.2절 `CAMVER` 행에 범프 사유 셋 — 포장 4.3절 · `Cn_*` 자리 5.6.1절 · 듀어 RTD 배치 10.4절.  값↔구성 대장은 `OI-29`).  남은 D3 는 **guide 견본 ↔ 규격 10장 대사 확인 목록을 해소하는 라운드**에서 함께 처리 예정이다 (⭐ 견본은 v1.10 부터 규격과 같은 판 번호를 달아, 따로 '견본 승격' 판올림은 없다). 상세는 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "규격 쪽 후속".
>
> ⚠️ **절 구성이 구판과 다르다** — 구판 절 번호(`규격 5.7절` 등)를 인용한 문서·코드 주석은 현행 기준으로 재확인할 것. v1.4 에서 **2.5절(Wrote 통보)이 삭제**돼 2장은 2.1~2.4 다. ICD 와 `ics_sim`/`ics_archon` 주석의 버전 참조 갱신은 각 소관의 일감이다 — ✅ ICD 는 **v4.3(2026-09-23)에서 구명 `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 참조를 걷고** `KMT_CEU_Raw_FITS_Specification_v1.13.md` 를 인용한다(백틱 경로라 링크는 아니다).  ⏳ v1.14 발행으로 그 v1.13 파일이 `archive/` 로 갔으니 ICD 쪽 판 표기 갱신이 다시 LEECU 소관으로 남는다.

| 구분 | 문서 | 버전 | 상태 |
| --- | --- | --- | --- |
| **Raw spec (현행)** | [`KMT_CEU_Raw_FITS_Specification_v1.14.md`](KMT_CEU_Raw_FITS_Specification_v1.14.md) | **v1.14** | ✅ 현행 (**`EQUINOX` 실수형**(`2000.0` · 결측 `-999.0`, 5.7절) + **2026-09-23 전반 재검토 반영** — science HK 원천 `HKDATA NOW` · `KMTK` 관측일 +9 h · guide `BIAS` 최소 노출 · converter v2.5.0 재대조 · `DATE-OBS` = 모든 영상의 적분 개시 · guide `TRIGOUT` 판정 창 = 노출 창 ± `g`(기본 0.15 s) · `CTRLnID`/`CTRLnSN` 미설정 `'NC'` · `CHECKSUM`/`DATASUM` 미도입 · `RDMODE` 미설정 `'NC'` · 돔 방위 소수 3자리 · `HKDATA NOW` 는 Radionode 를 안 친다) |
| 카드 판정 원장 | [`KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.20.md`](KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.20.md) | **v1.20** | ✅ 현행 (**converter v2.5.0 재대조** — raw 에서 읽는 카드 · geometry 선언 대조 · 카드 값 하드 실패.  raw spec v1.14 동반) |
| MEF·파이프라인 파급 (통합 문서) | [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.0.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.0.md) | **v1.0** | ✅ 현행 (**v1.0 — Draft 표기를 뗐다**(운영자 2026-09-23) · **converter v2.5.0 반영 현황** — 닫힌 C-항목과 남은 요청 · MEF converter 및 PIPELINE 판단 필요 항목(§7) · `EQUINOX` 파급.  raw spec v1.14 동반) |

연동 기준:

| 항목 | 값 |
| --- | --- |
| Raw 규격/구성 버전 파악 | 별도 버전 카드 없음(`RAWVER` 미도입 — 원장 v1.13 확인 요망 11) — **`CAMVER`(HW) · `CTRLxCFG`(FW/설정) · `DETID` · `CHMAP_*` 조합**으로 파악 |
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
| `KMT_CEU_Raw_FITS_Specification_v1.14.md` | ✅ **현행 raw spec (2026-09-23)** — 파일 구조 · 파일명(D-011/D-014) · 충돌·정체성(D-016) · geometry(포장 규범 조항 + amp 전수 표 64행 + X overscan `RRRRLLLL` 확정) · 헤더 keyword **136장**(현행 science 견본 pair 기준 — v1.5 에서 HK 4장 폐지 · v1.6 에서 `ORIGNAME`→`EXPID` 대체 · **v1.10 에서 HK 5장 신설**) · MEF/파이프라인 연동 요점 · 검증 체크리스트 · OI · **guide raw FITS 9·10장(v1.9 신설 — 파일·기하 / 노출 의미론·헤더, science 와 분리)** · e2v 데이터시트 부록. 배경·경위는 원장(Header_and_Refs)과 통합 문서로 링크. **v1.10 = HK 카드 5장(`HKUDATE` + 히터 넷) 신설 · 온도 부호 규약 · 게이지 Off 조항 · 견본을 `header_samples/` 로 통일** · **v1.12 = 정합 수정(5.7.2절 신설 · `CTRL1CFG` 한 규칙 · `RDMODE` 등재)** · **v1.13 = 실기 라운드 반영(돔 방위 redis · `OBSTYPE` 계통 식별 · guide `TRIGOUT` · FSA 2자리 · guide `PRESCNX=16` · 노출 번호 규범 · `HKUDATE` 셈 · HK 신선도 창)** · **v1.14 = `EQUINOX` 실수형 + 전반 재검토 반영(science HK 원천 `HKDATA NOW` · `KMTK` 관측일 +9 h · guide `BIAS` 최소 노출 · converter v2.5.0 재대조 · `DATE-OBS` = 모든 영상의 적분 개시 · guide `TRIGOUT` 판정 창 = 노출 창 ± `g`(기본 0.15 s) · `CTRLnID`/`CTRLnSN` 미설정 `'NC'` · `CHECKSUM`/`DATASUM` 미도입 · `RDMODE` 미설정 `'NC'` · 돔 방위 소수 3자리 · `HKDATA NOW` 는 Radionode 를 안 친다)** |
| `archive/` | **최근 구판만 유지** — 운영자가 주기적으로 살펴보고 없어도 될 파일은 지운다(2026-09-23 기준: Header_and_Refs v1.8~**v1.19** · Specification v1.2~**v1.13** · Impacts_and_Identity v0.5~**v0.10** 이 잔류). 지워진 구판·전신 문서(MEF_Impacts·Numbering_and_Identity·raw↔MEF 키워드 대응표 등)는 **git 이력과 운영자 외부 백업(`__backup_raw_fits_spec_oldver`)에 보존** — 대응표의 살아있는 내용은 전부 흡수됐다: **판정 준거는 Header_and_Refs 0장**, 카드 대응은 같은 문서 각 장의 `Use in MEF` 열, MEF/converter 쪽 이관 안건 4건은 통합 문서 v1.0 §6 이다 — 넷째(`DATASRC`·`CTRL1CFG`/`CTRL2CFG` 의 MEF 목적지)는 converter v2.5.0 이 PRIMARY 중계로 닫았고, 미결 셋(`NCTRL` 정의 · `CTRLID` 개칭 · `SATURAT`↔`SATLEVEL` 통일)의 본문은 같은 문서 §7-7~7-9(LEECU 판단 항목)에 있다 |
| `KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.20.md` | ✅ **현행 원장. v1.20 (2026-09-23) — converter v2.5.0 재대조**(raw 에서 읽는 카드 · geometry 선언 대조 · 카드 값 하드 실패 · ICD v4.3 · Keywords v1.1 표기, raw spec v1.14 동반). v1.19 (2026-09-12) — 돔 방위 셋 Source 를 `REDIS (dome control)` 로 확정(D-021) + 완료형 정정(raw spec v1.13 동반). v1.18 (2026-09-06) — 출처 어휘 정정(`ICG heater` 등재 · 폐지 계통 `standalone RTD` 제거)(raw spec v1.12 동반, 판정 불변). v1.15 (2026-08-29) — `OI-9` 폐기 + `CTRLnCFG` 예시 정합. v1.14 (2026-08-23) — **판정 준거를 본문 0장으로 편입**(구 검토 문서 폐기에 따른 근거 보전: 준거 순위 · converter 3상태 × ICD 규정/침묵 교차표 · 준거 공백 210 중 36/174 · 추출 함정). v1.13 (2026-08-22) — 운영자 3~5차 개정과 확인 요망 종결분을 반영한 수기 개정판 (v1.6 까지는 기계 추출 생성물, 구판은 `archive/`). **raw 카드 기준은 레거시 raw 실측 헤더**이고 **레거시 123개를 전량 귀속**시킨다 — converter 가 읽는 것 · 읽지 않는 것 · 도입 후보·확정(7장) · 폐지(8장·8.1·8.2). v1.10 에서 **도입/계획 판정 완결 — 미정 0**, v1.11 에서 **돔 Source 를 TCS relay or REDIS 로 변경** + **확인 요망 1~5 종결**(`EXPTIME`/`LEDFLASH` 정수형 · `ICSBUILD` 프로그램명 제거), v1.12 에서 **확인 요망 9 종결**(HK 온도·습도 문자열 계승), v1.13 에서 **잔여 전량 종결**(sentinel `'-999.99'` 단일값 · CTRL1ID 포맷+ICS INI 편집성 · "– 철회" 라벨 · 버전 문자열 귀속/caldb 계층 규칙 · PRESCN 키워드 변경 계승 · 규격 버전 카드 미도입 — 버전 파악은 `CAMVER`·`CTRLxCFG`·`DETID`·`CHMAP_*` 조합) — **D-016 등재까지 완료(2026-08-22), V1 재작성 착수 조건 완성**. 10~12장은 subframe 제기 · converter 자기 상수 카드 · raw 직접 사용자 안내, 13장은 종합 |
| `KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.0.md` | ✅ **현행 통합 문서. v1.0 (2026-09-23 — 판 번호를 v0.11 대신 v1.0 으로 올리고 Draft 표기를 뗐다(운영자 2026-09-23).  raw spec v1.14 동반, converter v2.5.0 이 닫은 C-항목 표시 · §7 MEF converter 및 PIPELINE 판단 필요 항목 신설 · `EQUINOX` 파급 기록 · LEECU 요청 갱신). v0.10 (2026-09-12 — raw spec v1.13 동반, 돔 방위 셋 출처 · `OBSTYPE` 어휘 · HK 완료형 정정). v0.9 (2026-09-04 — raw spec v1.10 동반, HK 카드 5장 신설 + 게이지 Off + 반쪽 pair, C-항목 3건 신설). Draft v0.6 (2026-08-22) 이래의 표제: "Raw FITS 헤더 개정에 따른 MEF ICD · MEF Converter 개정 및 검토 사항".** **Part 1** = LEECU 전달용 개정 요청 목록 — C-항목 신설·개정, raw↔MEF 이름 대응, ICD·정의서 개정 후보, MEF/converter 쪽 이관 안건 4건(§6 — 넷째는 converter v2.5.0 이 닫았다), 그리고 **§7 MEF converter 및 PIPELINE 판단 필요 항목** — raw 규격이 정하지 않고 MEF 쪽(converter · `mef_pipeline` · 아카이브)이 골라야 하는 것만 모은 절이다: 반쪽 pair 의 성한 절반 보관(DECISION_LOG D-001 과 맞물린다) · raw 가 공급하지 않는 MEF 카드의 처분 · 멈춤 기준 · §6 미결 셋 등 7-1~7-9. **Part 2** = 번호·충돌·정체성의 **파급 요약** — 정본은 raw spec 2.3절 + D-016 으로 이동(내용 이중화 방지 축약). 구판 v0.5~v0.10 은 `archive/`, 전신 문서 v0.4·v0.2 는 git 이력·외부 백업 |
| `header_samples/KMTA.20260821.123456.G.…v1.14.txt`<br>`…v1.14+LF.txt` | **guide 헤더 견본 (정본)** — 구 `v0.0 확정 초안`(운영자 2026-08-30), **v1.10 에서 판 번호를 규격과 통일했다**. 값 카드 **128장** + COMMENT 8 + END 1 + 공백 7 = **144 레코드**, 4×2880 = **11,520 바이트**. `+LF` 는 메모장용 사본(11,669 B — LF 와 꼬리 `#EOF` 를 걷어내면 정본과 동일). ⏳ 규격 10장과의 **대사 확인 목록은 `SMC_CLAUDE.md`** — 견본과 10장이 어긋나면 10장이 이긴다 |
| `header_samples/KMTA.20260821.123456.MK.fits.header.v1.14.txt`<br>`…NT.fits.header.v1.14.txt`<br>(각 `…v1.14+LF.txt` 메모장용 사본) | **science 헤더 견본 pair — 정본** (구 `확정 초안 헤더 v1.0 pair`.  ⭐ **v1.10 에서 `header_samples/` 로 옮기고 판 번호를 규격과 통일했다** — 따로 '견본 승격' 판올림은 없다).  MK 는 검토 왕복(v0.0~v0.4.4)을 마친 견본(운영자 승격 2026-08-22), NT 는 MK 에서 파생(2026-08-22): pair 상이 카드 **6장**만 다르다 (v1.6 개정 — 종전 7장) — `DETID`='NT' · `CHMAP_LT/LB/RT/RB`(raw spec 4.5절 표 = `Detector_Ch_to_AmpID_Map_v1.1.txt` 의 NT 행 — 4자 토큰) · `FILENAME`(`.NT` `DETID` 필드). **`EXPID` 는 `DETID` 필드가 없어 양쪽 동일**이다, 나머지 130장은 MK 동일(**`CCDTEMP` comment 의 "M" 은 2026-08-30 제거됐다** — 구 이월 대기 1번 조기 실행). 각 **180 레코드 = 값 카드 136 + COMMENT 8 + END 1 + 공백 35**, 5×2880 = 14,400 바이트 (v1.10 에서 HK 5장 신설로 4블록 → 5블록). 메모장용 사본 `…v1.14+LF.txt`(14,585 B)는 **LF 와 꼬리 `#EOF` 를 함께 걷어내면 정본과 바이트 동일**하다. 구 `__review/` 왕복함은 폐지 — docx 왕복본·초안 이력은 운영자 외부 백업(`__backup_raw_fits_spec_oldver`)에 |
| `Detector_Ch_to_AmpID_Map_v1.1.txt` | ✅ **검출기 출력 채널 ↔ MEF AmpID 64행 맵 (현행, 이 폴더 루트)** — CtrUnit–Port–CCD/CH–IMGSEC–MEF_AmpID. `CHMAP_*` 카드와 raw spec 4.5절 amp 전수 표의 **기계 가독 정본**. **v1.1 (2026-08-25)**: 채널 토큰 3자→4자 `<chip><A\|D><nn>` · `IMGSEC` `B-BOT`→`D-BOT` 16행 (`__` 읽기 전용 규칙상 `__reference/` 의 v1.0 을 고치지 않고 사본을 루트로 올렸다). ⚠️ **구 v1.0 은 v1.7 에서 삭제됐다** — 구 표기·`B-BOT` 오기가 혼동만 주기 때문이고, 원본은 git 이력(`44ab878`~)에 있다 |
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

raw spec **5.10절**이 "raw 에 넣지 않는 keyword"의 경계를, **6장**이 MEF·파이프라인이 알아야 할 연동 요점을 담는다. MEF keyword 전량 대조표와 L1 `CARRY_KEYS` 추적은 원장(Header_and_Refs)과 archive 의 구판 6.5·6.6절이 원자료다.

## 규격을 구현하는 곳

| 주체 | 파일 | 상태 |
| --- | --- | --- |
| **신규 ICS (시뮬)** | [`../ics_sim/ics_sim/rawpair.py`](../ics_sim/ics_sim/rawpair.py)(이름) + [`rawhdr.py`](../ics_sim/ics_sim/rawhdr.py)(카드) + [`config.py`](../ics_sim/ics_sim/config.py)(사이트 — `[node] observatory` 한 줄이 정본이다: 값 어휘는 D-017, 판별 방식은 **D-020**. ⚠️ 구 `siteid.py`(호스트 IP 판정, D-015)는 **브랜치 `ics-archon-v1.0-build` 에서 삭제**됐고 `main` 의 `ics_sim` 은 합류 대기라 파일이 아직 남아 있다) + `sequencer._store()` + `hardware/sim.py`의 `write_frame()` | **동작 중** — 헤더 5장을 **템플릿 주도**로 재편해 견본 pair 를 **바이트 단위로 재현**한다(`rawcards.py` = 견본의 기계 사본, 대사 시험 `tests/test_raw_draft.py`). v1.3 정렬 잔여(D-016 충돌 처리 · 정체성 카드 재편 · 컨트롤러 블록 · 신설 HK/돔 카드 · 절 번호 참조)는 **전량 완료**(DevNote 11.19~11.21)이고 이후 개정분도 따라간다. ⚠️ **이 칸이 적는 것은 브랜치 `ics-archon-v1.0-build` 의 구현 상태다** — 왼쪽 링크가 가리키는 `main` 의 `ics_sim` 은 합류 대기라 `rawcards.py` 와 `tests/test_raw_draft.py` 가 아직 없고, 폐지된 `siteid.py` · `tests/test_site_id.py` 가 아직 남아 있다. ⛔ 시험 수는 여기 박지 않는다 — `python -m pytest --collect-only -q` 의 꼬리가 정본이다 |
| **신규 ICS (실기)** | [`../ics_archon/`](../ics_archon/README.md) — `archon/backend.py` + `archon/fitswrite.py`(raw pair 바이트 기록) | **구현 완료 · 실기 미검증.** `ics_sim` 을 사본 없이 그대로 쓰고 `DetectorBackend` 자리만 채운다(D-012). ⚠️ `ics_sim/hardware/archon.py` 는 **시뮬 패키지에 남은 스텁**이고 실기 경로가 아니다 |
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

부작용 하나가 따라온다 — **`LASTFILE`이 더 이상 실재하는 경로가 아니다.** 아카이브·DTS 도구는 `LASTFILE` 대신 raw 헤더의 **`FILENAME`(+`EXPID`)** 을 근거로 삼아야 한다 (**D-016**, 2026-08-22 등재 · **v1.6 에서 `ORIGNAME`→`EXPID` 개정**). **아카이브 유일 키는 `FILENAME`** 이다 — 충돌 시 격리 대신 **노출 번호를 증가**시켜 저장하므로 유일성이 구조로 보장되고, `EXPID`(카운터가 처음 배정한 이름)과의 **값 불일치가 충돌 신호**다. `UNIQNAME` · `NAMECLSH` · `clash/` 격리는 폐지됐다 — 상세는 [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.0.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.0.md) Part 2 · raw spec 2.3절. ⭐ **저장되지 않은 프레임은 번호를 소비하지 않는다** (2.3절 8항 · **D-022**, 운영자 확정 2026-09-07) — `ABORT` 나 취득 실패로 파일이 안 생기면 번호를 되감으므로 아카이브 번호는 **연속이 원칙**이고, 남는 구멍은 예외 넷(내부 오류 · 번호 공간 고갈 · 번호 기록 파일 읽기 실패 · 종료 저장 상한 초과)뿐이다.

남은 open item 은 **raw spec 8장(science)과 10.6절(guide)** 에 있다 — **science**: 포장 조항 준수 검증(OI-3) · 중앙 overscan 분배(OI-4) · binning(OI-5) · 셔터 반영 지연(OI-13) · e2v 데이터시트 대응 잔여 ③(OI-17) · **`HTROUT` 값의 의미(OI-28** — 측정값인지 명령값인지, FORCE 실험으로 닫는다**)** · `CAMVER` 값↔구성 대장(OI-29) · 돔 방위의 기준 `S to E`(OI-30) · 돔 방위 셋의 redis 실기 확인(OI-31) · **`PROJID` 기본값 귀속(OI-32** — 규격을 고칠지 값을 고칠지**)**.  **guide(10.6절)**: **OI-20·21·22·26 · OI-31**(X 528 구간 실측 · 9행/칩 방위 · `PIXSCALE` · `FlushLines` 실측 · 돔 방위 실기 확인).  **대부분 실기 실측·자료 확보·협의가 있어야 닫히고, OI-29(대장 위치·범프 주체) · OI-32 는 운영자 판단으로 닫힌다.**  ~~OI-15~~(X overscan 4:4)는 **v1.5 에서 종결**, ~~OI-9~~(배선 실측)는 **v1.8 에서 폐기**, ~~OI-19~~(guide `Cn_TEMP` 자리)는 **v1.9 에서 종결**(10.4절 수록), ~~OI-18~~(NT `CCDTEMP` 귀속)은 **v1.10 에서 폐기**(5.9절이 pair 양쪽 동일을 이미 규정해 물음의 전제가 없다), 그리고 **v1.13 에서 넷이 닫혔다** — ~~OI-16~~(Radionode 원값 포맷, 구칭 Tapaculo: 2026-09-09 실측으로 소수 2자리 확정) · ~~OI-23~~(guide 노출 규약 잔여: TC 질의 = `GO` 당 1회 → 10.1절 · 카운터 독립 → 9.2절) · ~~OI-25~~(HK 신설 5장의 원천 배선: 다섯 다 실기 원천에 닿았다) · ~~OI-27~~(`GUIEXPCTRL` 이후 새 `GO` 의 주체: ICS 가 아니라 셔터 실측을 감시하는 별도 주체).  **v1.14 에서는 둘이 닫혔다** — ~~OI-7~~(raw 무결성: `CHECKSUM`·`DATASUM` 은 raw 에 도입하지 않는다 — 운영자 확정 2026-09-23, 5.10절 폐지·미도입 목록.  원장 7장의 `X` 판정과 같고, MEF 의 같은 이름 카드는 converter 가 HDU 마다 쓰는 별개의 것이다) · ~~OI-24~~(guide 헤더 카드 설계 잔여: `CAMVER` 는 science 와 같고, `IMAGETYP` 은 같은 어휘이되 `BIAS` 면 `EXPTIME` 에 설정 가능한 최소 노출(기본 1.3 s)의 실현값을 싣는다 · 기동 기본은 `OBJECT` · `EXPTIME` 2 s — 운영자 확정 2026-09-15, 10.3절).

## 버전 / 관리 정책

- Raw geometry/포장이 바뀌면 **`CAMVER`(HW) 또는 `CTRLxCFG`(설정)** 가 바뀐 것이어야 하며(raw spec 4.3절 — 별도 `RAWVER` 카드는 없다), L0 의 `GEOMVER` 도 같은 변경으로 갱신한다.
- 이 규격 · L0 ICD · converter는 같은 geometry를 가리켜야 한다. 셋 중 하나만 바꾸지 않는다.
- 새 버전을 현행으로 올릴 때 이 README의 "현재 기준선"을 함께 갱신하고, 구버전은 `archive/`로 옮겨 이력을 보존한다.
- ⭐ **견본 판 번호는 규격 판 번호를 따라간다** (v1.10 이후).  판올림 때 `header_samples/` **6장**(MK·NT·G × 정본·`+LF`)의 파일명을 바꾸면, 그것을 가리키는 자리를 **한 번에** 치환한다 — 규격 머리말 연동 표(**링크 텍스트와 href 둘 다**) · 이 README 의 디렉토리 구조 표 · `SMC_CLAUDE.md`.  ⚠️ v1.12 에서 NT 견본의 **링크 텍스트만** 구판(`…v1.11.txt`)으로 남은 적이 있다 — href 가 맞으면 링크는 열리므로 눈에 띄지 않는다.
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
| 변경 관리 (site baseline) | [`../project_management/governance/CHANGE_CONTROL.md`](../project_management/governance/CHANGE_CONTROL.md) — raw 헤더에 걸리는 것은 **CR-003**(돔 방위 셋 redis, D-021).  ⚠️ **CR-003 은 `ics-archon-v1.0-build` 의 CHANGE_CONTROL 에만 있다** — `main` 의 이 파일에는 CR-001·CR-002 뿐이고, CR-003 은 `ics_archon` 합류 때 baseline 변경으로 다시 걸린다(D-021 은 `main` DECISION_LOG 에 있다) |
| 프로젝트 관리 보드 | [`../project_management/README.md`](../project_management/README.md) |

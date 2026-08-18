# KMTNet-CEU Raw FITS Specification

최종 갱신일: 2026-08-13

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

> ⛔ **현행 raw pair 규격이 없다 (2026-08-18).** `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 는 파일로는 남아 있지만 **((재작성중)) 표시가 붙었고 근거가 아니다.** 전면 재검토 중이며, 어느 절이 살아남을지 정해지지 않았다.
>
> **재작성판이 나올 때까지 이 규격을 인용하거나 근거로 구현하지 않는다.** 절 번호(5.x · 7장 · 9장)도 바뀔 수 있다.
>
> 다른 문서·코드에 남은 참조는 **경로로는 유효하지만 근거로는 무효**다. 특히 ICD v4.1 §12 와 `ics_sim` 의 `rawhdr.py` · `rawpair.py` · `hardware/archon.py` 가 5장에 의존하므로 재작성 시 함께 정리한다.

| 구분 | 문서 | 버전 | 상태 |
| --- | --- | --- | --- |
| Raw pair 규격 | [`KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`](KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md) | v1.2 | ⛔ **((재작성중)) — 현행 아님** |

연동 기준:

| 항목 | 값 |
| --- | --- |
| Raw 규격 버전 (`RAWVER`) | `CEU-RAW-v1.0` |
| 파일 구성 | 노출 1회 = raw FITS 2개 (`MK` = M,K / `NT` = N,T) |
| 파일명 | `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK\|NT>.fits`, `<SITE>` ∈ {`KMTC`=CTIO, `KMTS`=SAAO, `KMTA`=SSO, `KMTT`=테스트베드} (D-011) |
| 파일 구조 | single HDU, `BITPIX=16` + `BZERO=32768`, `19200 x 9400` |
| 파일당 amplifier | 32 (chip 2 × amp 16) |
| 기준 ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` (v4.1, docx 동본) |
| 기준 converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) |

## 디렉토리 구조

| 경로 | 내용 |
| --- | --- |
| `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` | ⛔ **((재작성중)).** 옛 raw pair 규격이며 **현행이 아니다.** 재검토 결과로 다시 쓴다 |
| `KMT_CEU_Raw_to_MEF_Keyword_Map_v0.7_REVIEW.md` | **검토용 — 규격이 아니다.** raw ↔ L0 MEF 키워드 전수 대응표 289행. 0장이 **준수 우선순위**(1 ICD v4.1 → 2 converter 코드 → 3 keyword 정의서, 레거시 MEF 는 배경지식)를, 1.2절이 **raw 쪽 기준선**(레거시 raw 실측 헤더 123개 — `ics_sim` 출력이 아니다)을 세우고, 2장이 준거 대비 현재 상태를, 5장이 결정이 필요한 10항목을 담는다 (ACT-011) |
| `__reference/` | 규격 작성 시 대조한 참고 문서 사본 (아래) |

`__reference/` 내용:

| 파일 | 원본 위치 | 비고 |
| --- | --- | --- |
| `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` | `../mef_fits_spec/` | L0 MEF ICD **현행 v4.1**. 바이트 동일 사본 |
| `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1_KO.md` | — | v4.1 ICD의 **국문본. 이 디렉토리가 유일본** |
| `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` | `../mef_fits_spec/` | 규격 6.5절 대조표의 원본. 바이트 동일 사본 |
| `KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` | `../mef_converter/` | Archon raw 검증 결과. 바이트 동일 사본 |
| `KMT_CEU_Converter_Raw_Reads_v1.0.md` | — | **사본이 아니라 생성물이다** (2026-08-18 추가). converter 소스에서 기계 추출한 **raw 헤더 읽기 목록 104개** — 각 keyword 의 MEF 목적지 · 없을 때 채워지는 기본값 · 레거시 raw 유무. converter 가 개정되면 다시 생성한다 |
| `Legacy raw fits header samples/` | — | **레거시 시스템의 FITS 헤더 실측본** (2026-08-12 추가). `KMTNk.20170209.044131.Rawheader.txt` 가 이 규격에 대응하는 **레거시 raw 헤더**이고, `xkmta.20170209.044131.MEF.*.txt` 는 레거시가 MEF 로 변환한 산출물의 헤더다(primary 1 + 확장 35). raw 헤더는 2017→2021 사실상 불변이어서 정착된 설계로 읽을 수 있다 — 규격 5장 식별 keyword 재정의의 근거 |

> ⚠️ `KMTNc.20210503.030331.header.txt` 는 **raw pair 가 아니다.** `DETID='C'` · 1616×1616 인데, raw 영상의 ROI 조각들을 모자이크로 재구성한 **combination 산출물**이다(운영자 확인 2026-08-12). 검출기 이름이 아니므로 이 규격 범위 밖이고, `M,K,N,T` 4개 전제에 영향을 주지 않는다.

**국문 ICD와 `KMT_CEU_Converter_Raw_Reads_v1.0.md` 를 뺀 나머지는 사본이며 기준본은 원본 위치의 것이다.** 원본이 개정되면 이 사본도 함께 갱신하거나 삭제한다. 국문 ICD 는 유일본이고, `KMT_CEU_Converter_Raw_Reads_v1.0.md` 는 converter 소스에서 뽑은 **생성물**이라 둘 다 대조 원본이 없다.

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
| MK/NT pair 일관성 규칙 | guide/focus CCD 자료 |
| Converter가 읽는 값과 누락 시 영향 | L0 MEF 내부 구조 → `mef_fits_spec/` |

규격 5.12절이 "raw에 넣지 않는 keyword"의 경계를, 6.5절이 **MEF keyword 정의서 전 항목의 출처 대조표**를, 6.6절이 **L1 `CARRY_KEYS` 추적**을 담는다. MEF/L1이 요구하는 값 중 raw에서 와야 하는 것이 빠지지 않았는지는 이 세 절로 확인한다.

## 규격을 구현하는 곳

| 주체 | 파일 | 상태 |
| --- | --- | --- |
| **신규 ICS (시뮬)** | [`../ics_sim/ics_sim/rawpair.py`](../ics_sim/ics_sim/rawpair.py)(이름) + [`rawhdr.py`](../ics_sim/ics_sim/rawhdr.py)(카드) + [`siteid.py`](../ics_sim/ics_sim/siteid.py)(사이트) + `sequencer._store()` + `hardware/sim.py`의 `write_frame()` | **동작 중 (2026-08-13)** — 2.3 파일명(사이트별 관측일, D-014) · 2.5 저장/통보 분리 · 5.0 sentinel · **5.1~5.10 헤더 카드 전체**를 구현했다. 픽셀은 더미이고 크기도 실물(19200×9400)이 아니지만 **구조와 규약은 규격 그대로**라, 하드웨어 없이 실물 OBSAgent 로 D-010/D-011을 검증할 수 있다 |
| 신규 ICS (실기) | [`../ics_sim/ics_sim/hardware/archon.py`](../ics_sim/ics_sim/hardware/archon.py)의 `write_frame()` | 스텁 — 실기 단계에서 구현. **계약은 개정 완료 (D-012)**, 시뮬 백엔드가 참고 구현 |
| 실험실 취득 | [`../cam_char/archon/archon_kmtnet_labtest_v2.py`](../cam_char/archon/archon_kmtnet_labtest_v2.py)의 `write_fits()` | 동작 중 — geometry/telemetry 카드 보강 필요 |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) | 동작 중 — MK 헤더만 읽음, NT 헤더 반영 필요 |

## 결정된 사항 · 남은 open item

v1.0에서 제기한 OBSAgent 규약 충돌 2건은 **v1.1에서 해결되었고** (DECISION_LOG D-009 / D-010), 파일명은 **v1.2에서 사이트 코드 prefix로 재개정되었다** (D-011, D-009 대체).

| ID | 결정 |
| --- | --- |
| ~~OI-1~~ | 파일명은 `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK\|NT>.fits`, `<SITE>` ∈ {`KMTC`, `KMTS`, `KMTA`, `KMTT`} (D-011, 2026-08-10). `<NNNNNN>`는 **6자리 zero-padding 필수**. converter v2.2.0에서 정규식 개정 + `OBSERVAT` 교차 검증 |
| ~~OI-2~~ | **저장 단위와 통보 단위를 분리.** 파일은 컨트롤러당 1개(2개), `STATUS: Wrote`는 CCD당 1회(4회)를 레거시 형태 논리 이름(`KMTN<c>.…`, 불변)으로 발신. OBSAgent 변경 없음 |
| ~~OI-8~~ | NT 헤더 완전성 요구가 **ICD v4.1에 반영되었다** (2026-08-10) |
| ~~OI-10~~ | 파일명 `<YYYYMMDD>`는 **그 사이트의 관측일**이다 — UT 에 사이트별 보정을 더한 뒤 날짜만 취한다. 경계는 세 사이트 모두 현지 12:30 (D-014, 2026-08-13). 종전 잠정안(UT 날짜)은 한 밤의 자료를 두 디렉토리로 갈랐다 |
| ~~OI-11~~ | CTIO · SAAO · SSO 측지값을 운영자가 확정해 `ics_sim.ini` 의 사이트별 절에 넣었다 (2026-08-13) |
| ~~OI-12~~ | 파일명 날짜부가 `DATE-OBS` 날짜와 **어긋나는 것이 정상**이다 — OI-10 이 관측일 기준으로 확정되면서 해소됐다 (2026-08-13) |

부작용 하나가 따라온다 — **`LASTFILE`이 더 이상 실재하는 경로가 아니다.** 아카이브·DTS 도구는 `LASTFILE` 대신 raw 헤더의 `UNIQNAME`/`FILENAME`/`CTRLTAG`를 근거로 삼아야 한다 (규격 2.5절). **색인 키는 `UNIQNAME`** 이다 — 이름이 겹쳐 격리된 경우에도 그 값만 불변이다 (2.3.1절).

남은 open item은 규격 문서 9장에 있다 — `ROWORDR`/`RDDIRT`/`RDDIRB` 확정(OI-3), 중앙 overscan 분배 실측(OI-4), binning(OI-5), raw 단계 checksum(OI-7), amp↔배선 맵 실측(OI-9, `XTALKCAL=True` 전제조건), **AUX 셔터 상태가 `SHOPEN`+3초에 반영되는가(OI-13)**. **전부 실기 실측이나 협의·정책 결정이 있어야 닫힌다** — 문서만으로 닫을 수 있었던 sentinel 규약(OI-6)은 2026-08-11에, 협의로 닫힌 **파일명 날짜 기준(OI-10)·사이트 측지값(OI-11)·날짜부와 `DATE-OBS` 의 어긋남(OI-12)** 은 2026-08-13에 해결됐다.

## 버전 / 관리 정책

- Raw geometry가 바뀌면 `RAWVER`를 올리고, 필요하면 L0의 `GEOMVER`도 같은 변경으로 갱신한다.
- 이 규격 · L0 ICD · converter는 같은 geometry를 가리켜야 한다. 셋 중 하나만 바꾸지 않는다.
- 새 버전을 현행으로 올릴 때 이 README의 "현재 기준선"을 함께 갱신하고, 구버전은 `archive/`로 옮겨 이력을 보존한다.
- 대용량 raw FITS는 Git에 넣지 않는다 (`.gitignore`). 로컬 `raw/`에서 다루고 파일명 · SHA256 · 생성 command를 문서에 기록한다.

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| L0 MEF 규격 (keyword/ICD) | [`../mef_fits_spec/README.md`](../mef_fits_spec/README.md) |
| Converter | [`../mef_converter/README.md`](../mef_converter/README.md) |
| L0→L1 전처리 파이프라인 | [`../mef_pipeline/README.md`](../mef_pipeline/README.md) |
| 신규 ICS 개발 노트 | [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) |
| Archon 실험실 취득 | [`../cam_char/archon/ARCHON_LABTEST_V2.md`](../cam_char/archon/ARCHON_LABTEST_V2.md) |
| 기술 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |
| 프로젝트 관리 보드 | [`../project_management/README.md`](../project_management/README.md) |

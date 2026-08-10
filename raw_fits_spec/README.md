# KMTNet-CEU Raw FITS Specification

최종 갱신일: 2026-08-10

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

| 구분 | 문서 | 버전 | 상태 |
| --- | --- | --- | --- |
| Raw pair 규격 | [`KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`](KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md) | v1.2 | Current |

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
| `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` | 현행 raw pair 규격 (md가 diff 가능한 기준본) |
| `__reference/` | 규격 작성 시 대조한 참고 문서 사본 (아래) |

`__reference/` 내용:

| 파일 | 원본 위치 | 비고 |
| --- | --- | --- |
| `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx` | `../mef_fits_spec/archive/` | L0 MEF ICD v4.0 (규격 작성 시점 사본; 현행은 v4.1) |
| `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4_0_KO.docx` | — | v4.0 ICD의 국문본. **이 디렉토리가 유일본** (v4.1 국문본은 미작성) |
| `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.docx` | `../mef_fits_spec/` | 규격 6.5절 대조표의 원본 |
| `KMT_CEU_L0AmpRaw_Work_Summary_v1.0.docx` | `../mef_converter/` | Archon raw 검증 결과 |

**국문 ICD를 뺀 나머지는 사본이며 기준본은 원본 위치의 것이다.** 원본이 개정되면 이 사본도 함께 갱신하거나 삭제한다.

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
| 신규 ICS | [`../ics_sim/ics_sim/hardware/archon.py`](../ics_sim/ics_sim/hardware/archon.py)의 `write_fits()` | 스텁 — 실기 단계에서 구현 |
| 실험실 취득 | [`../cam_char/archon/archon_kmtnet_labtest_v2.py`](../cam_char/archon/archon_kmtnet_labtest_v2.py)의 `write_fits()` | 동작 중 — geometry/telemetry 카드 보강 필요 |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) | 동작 중 — MK 헤더만 읽음, NT 헤더 반영 필요 |

## 결정된 사항 · 남은 open item

v1.0에서 제기한 OBSAgent 규약 충돌 2건은 **v1.1에서 해결되었고** (DECISION_LOG D-009 / D-010), 파일명은 **v1.2에서 사이트 코드 prefix로 재개정되었다** (D-011, D-009 대체).

| ID | 결정 |
| --- | --- |
| ~~OI-1~~ | 파일명은 `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK\|NT>.fits`, `<SITE>` ∈ {`KMTC`, `KMTS`, `KMTA`, `KMTT`} (D-011, 2026-08-10). `<NNNNNN>`는 **6자리 zero-padding 필수**. converter v2.2.0에서 정규식 개정 + `OBSERVAT` 교차 검증 |
| ~~OI-2~~ | **저장 단위와 통보 단위를 분리.** 파일은 컨트롤러당 1개(2개), `STATUS: Wrote`는 CCD당 1회(4회)를 레거시 형태 논리 이름(`KMTN<c>.…`, 불변)으로 발신. OBSAgent 변경 없음 |
| ~~OI-8~~ | NT 헤더 완전성 요구가 **ICD v4.1에 반영되었다** (2026-08-10) |

부작용 하나가 따라온다 — **`LASTFILE`이 더 이상 실재하는 경로가 아니다.** 아카이브·DTS 도구는 `LASTFILE` 대신 raw 헤더의 `FILENAME`/`EXPID`/`CTRLTAG`를 근거로 삼아야 한다 (규격 2.5절).

남은 open item은 규격 문서 9장에 있다 — `ROWORDR`/`READDIR` 확정, 중앙 overscan 분배 실측, amp↔배선 맵 실측(OI-9, `XTALKCAL=True` 전제조건), binning, sentinel 규약, checksum.

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

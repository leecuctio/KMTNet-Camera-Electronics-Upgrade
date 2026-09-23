# KMTNet-CEU MEF FITS Specification

최종 갱신일: 2026-09-23

## 목적

이 디렉토리는 KMT-CEU 신규 전자부 카메라의 science output을 저장하는 **MEF FITS 데이터 산출물 규격**을 한곳에서 관리한다. 두 가지 규격 문서를 담는다.

- **Keyword 정의서**: 운영 MEF FITS에 들어가야 할 FITS keyword와 binary table column의 최종 기준.
- **ICD (Interface Control Document)**: MEF product의 구조, geometry, HDU layout, 데이터 흐름을 정의하는 인터페이스 통제 문서.

두 문서는 동일한 product를 다른 관점에서 기술하므로 항상 함께 일관성을 유지해야 한다. Geometry나 HDU layout이 바뀌면 ICD와 keyword 정의서를 같은 변경으로 갱신한다.

## 현재 기준선

| 구분 | 문서 | 버전 | 상태 |
| --- | --- | --- | --- |
| Keyword 정의 | [`KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md`](KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md) | v1.1 | Current |
| Keyword 정의 (배포본) | `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.docx` | v1.1 | ⏳ **미생성** — 아래 "배포본(.docx) 미생성" 참조 |
| ICD | [`KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md`](KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md) | v4.3 | Current |
| ICD (배포본) | `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.docx` | v4.3 | ⏳ **미생성** |

연동 기준:

| 항목 | 값 |
| --- | --- |
| Product | KMT-CEU L0 64-amplifier raw MEF |
| Geometry version (`GEOMVER`) | `CEU-L0AMP-v2.1` |
| Raw 입력 파일명 | `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK\|NT>.fits`, `<SITE>` ∈ {KMTC, KMTS, KMTA, KMTK} (ICD v4.2 §2.1, D-011 · 넷째 코드 **D-017**, 2026-08-25 — ICD 본문·converter 정규식 반영 완료 2026-09-04) |
| 기준 converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.5.0) |
| Product format version (`PRODVER`) | `v2.2.0` (D-023) |
| HDU count | 69 = PRIMARY + 64 amp IMAGE + 4 BINTABLE |
| Binary tables | `AMPINFO`, `XTALKINFO`, `VOLTINFO`, `TELEMETRY` |

## 디렉토리 구조

| 경로 | 내용 |
| --- | --- |
| `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md` | 현행 keyword 정의서 (md가 diff 가능한 기준본) |
| `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md` | 현행 ICD (md가 diff 가능한 기준본, v4.1부터 md 병행) |
| `archive/` | superseded된 구버전 ICD. 이력 보존용이며 운영 기준이 아님 |

## ICD Revision History

| 버전 | 파일 | 위치 | 핵심 변화 |
| --- | --- | --- | --- |
| v1.1 | `KMT_CEU_Science_MEF_ICD_Final_v1.1.docx` | `archive/` | 초기 science MEF ICD 초안 |
| v2.0 | `KMT_CEU_Science_MEF_ICD_ArchonRawVerified_v2.0.docx` | `archive/` | 검증된 Archon MK/NT raw geometry 반영 |
| v3.0 | `KMT_CEU_Science_MEF_ICD_ArchonRawVerified_v3.0.docx` | `archive/` | Archon raw 구조 정밀화 |
| v4.0 | `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md` | `archive/` | Primary raw product를 CCD-level image가 아니라 L0 64-amplifier MEF로 재정의 |
| v4.1 | `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` / `.docx` | `archive/` | Raw 파일명 prefix를 사이트 코드(KMTC/KMTS/KMTA/KMTT)로 개정(D-011) + NT 헤더 완전성 요구(raw_fits_spec OI-8). md 기준본 도입 |
| v4.2 | `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md` / `.docx` | `archive/` | 넷째 사이트 코드 개정(D-017): `KMTT`/`TESTBED` → `KMTK`/`KASI`, L0 prefix `kmtt`→`kmtk`. converter 기준 v2.4.0(+v2.3.0 `--ampchar` 실측 GAIN/RDNOISE 스탬핑). geometry 불변 |
| **v4.3** | `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md` | (현행) | **L0 sky WCS 를 L1 Gaia 측성의 seed 로 규정(D-023) — §7.1·§7.2 신설 · §4 에 `CD` 무반전 주석 · `AMPINFO` 40→52 · `CHANNEL` 1–16(C-11) · `VOLTINFO` 9→37(C-18) · converter 기준 v2.5.0 · `PRODVER` v2.2.0. geometry 불변** |

Keyword 정의서 개정 이력은 그 문서의 §13에 있다 (v1.0 2026-06-22 → **v1.1 2026-09-23**, D-023).

v3.0 → v4.0의 product 재정의 근거는 `../project_management/governance/DECISION_LOG.md`의 **D-001**에, v4.0 → v4.1의 파일명/NT 헤더 개정 근거는 **D-011**과 `../raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`(2.1절·2.3절)에, v4.1 → v4.2의 넷째 사이트 코드 개정 근거는 **D-017**에, v4.2 → v4.3 및 keyword 정의서 v1.0 → v1.1의 seed WCS 규정 근거는 **D-023**에 기록되어 있다.

### ⏳ 배포본(.docx) 미생성

v4.3 · v1.1 은 **md 기준본만 갱신했다.** 이 환경에 `python-docx` 가 없어
`../raw_fits_spec/tools/md_to_docx.py` 를 돌릴 수 없었다. 구 `.docx`(v4.2 · v1.0)는
규칙대로 `archive/` 로 옮겼으므로 **현행 배포본이 없는 상태**다. `python-docx` 가
있는 환경에서 다음을 돌려 채운다:

```bash
python3 ../raw_fits_spec/tools/md_to_docx.py \
  KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.docx
python3 ../raw_fits_spec/tools/md_to_docx.py \
  KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.docx
```

### ⏳ raw_fits_spec 쪽 사본 (이 저장소에서 닫을 수 없음)

`../raw_fits_spec/__reference/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md` 는 구
v1.0 과 **바이트 동일 사본**이고 그쪽 README 에 `diff -q` 대조가 걸려 있다. v1.1
판올림으로 그 대조는 더 이상 성립하지 않는다. ⛔ `__` 접두 폴더는 **읽기 전용**
(운영자 확정 2026-08-22)이라 이 저장소에서 갱신할 수 없다 — ICS 쪽에서 사본을
v1.1 로 올리거나 지워야 한다. ICD 국문본(`__reference/…_v4.1_KO.md`, 그쪽 유일본)도
이미 v4.1 에 묶여 있어 v4.3 기준으로 두 판 뒤처진다.

## 버전 / 관리 정책

- Software/product version과 geometry version은 분리해서 관리한다 (DECISION_LOG **D-004**). FITS card formatting, parser, atomic write 같은 patch는 geometry 변경이 아니다.
- **Geometry change** (amp ordering, section, chip orientation, HDU layout)이 발생하면 `GEOMVER`를 갱신하고 ICD와 keyword 정의서를 같은 변경으로 올린다.
- Keyword 정의서, ICD, converter의 `AMPINFO` table은 동일한 geometry/electronics 값을 가져야 한다. 세 곳 중 하나만 바꾸지 않는다.
- 구버전 문서는 삭제하지 않고 `archive/`에 남겨 이력을 보존한다. 새 버전을 현행으로 올릴 때 이 README의 "현재 기준선"과 "ICD Revision History"를 함께 갱신한다.
- docx와 md가 함께 있으면 md를 diff 가능한 기준본으로 삼고 docx는 배포/공유본으로 둔다.

## 운영 전환 시 확정 필요 값

현재 keyword 정의서의 일부 값은 commissioning 전 placeholder이다. 실측/운영값 확정은 `../project_management/science/CALIBRATION_TRACKER.md`에서 추적한다.

- Calibration: `GAIN`, `RDNOISE`, `SATURAT`, `LINMAX`, `XTALKINFO`
- Telemetry: `VOLTINFO`, `TELEMETRY`, controller identity/firmware
- Orientation: `READDIR` (flat/star sequence test로 확정)
- `XTALKCAL=True`는 실측 crosstalk coefficient가 들어간 경우에만 허용한다.

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| Converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` |
| Converter README | `../mef_converter/README_KMT_CEU_L0AmpRaw_Converter_v2.1.1.md` |
| 작업 정리 | `../mef_converter/KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` |
| 기술 결정 기록 | `../project_management/governance/DECISION_LOG.md` |
| Calibration 추적 | `../project_management/science/CALIBRATION_TRACKER.md` |
| Release 점검 | `../project_management/release/RELEASE_CHECKLIST.md` |
| 프로젝트 관리 보드 | `../project_management/README.md` |

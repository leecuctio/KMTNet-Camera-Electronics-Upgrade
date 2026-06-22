# KMTNet-CEU MEF FITS Specification

최종 갱신일: 2026-06-22

## 목적

이 디렉토리는 KMT-CEU 신규 전자부 카메라의 science output을 저장하는 **MEF FITS 데이터 산출물 규격**을 한곳에서 관리한다. 두 가지 규격 문서를 담는다.

- **Keyword 정의서**: 운영 MEF FITS에 들어가야 할 FITS keyword와 binary table column의 최종 기준.
- **ICD (Interface Control Document)**: MEF product의 구조, geometry, HDU layout, 데이터 흐름을 정의하는 인터페이스 통제 문서.

두 문서는 동일한 product를 다른 관점에서 기술하므로 항상 함께 일관성을 유지해야 한다. Geometry나 HDU layout이 바뀌면 ICD와 keyword 정의서를 같은 변경으로 갱신한다.

## 현재 기준선

| 구분 | 문서 | 버전 | 상태 |
| --- | --- | --- | --- |
| Keyword 정의 | [`KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`](KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md) | v1.0 | Current |
| Keyword 정의 (배포본) | `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.docx` | v1.0 | Current |
| ICD | `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx` | v4.0 | Current |

연동 기준:

| 항목 | 값 |
| --- | --- |
| Product | KMT-CEU L0 64-amplifier raw MEF |
| Geometry version (`GEOMVER`) | `CEU-L0AMP-v2.1` |
| 기준 converter | `../kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.1.1) |
| HDU count | 69 = PRIMARY + 64 amp IMAGE + 4 BINTABLE |
| Binary tables | `AMPINFO`, `XTALKINFO`, `VOLTINFO`, `TELEMETRY` |

## 디렉토리 구조

| 경로 | 내용 |
| --- | --- |
| `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` / `.docx` | 현행 keyword 정의서 (md가 diff 가능한 기준본) |
| `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx` | 현행 ICD |
| `archive/` | superseded된 구버전 ICD. 이력 보존용이며 운영 기준이 아님 |

## ICD Revision History

| 버전 | 파일 | 위치 | 핵심 변화 |
| --- | --- | --- | --- |
| v1.1 | `KMT_CEU_Science_MEF_ICD_Final_v1.1.docx` | `archive/` | 초기 science MEF ICD 초안 |
| v2.0 | `KMT_CEU_Science_MEF_ICD_ArchonRawVerified_v2.0.docx` | `archive/` | 검증된 Archon MK/NT raw geometry 반영 |
| v3.0 | `KMT_CEU_Science_MEF_ICD_ArchonRawVerified_v3.0.docx` | `archive/` | Archon raw 구조 정밀화 |
| **v4.0** | `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx` | (현행) | **Primary raw product를 CCD-level image가 아니라 L0 64-amplifier MEF로 재정의** |

v3.0 → v4.0의 product 재정의 근거는 `../project_management/governance/DECISION_LOG.md`의 **D-001**에 기록되어 있다.

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
| Converter | `../kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` |
| Converter README | `../README_KMT_CEU_L0AmpRaw_Converter_v2.1.1.md` |
| 작업 정리 | `../KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` |
| 기술 결정 기록 | `../project_management/governance/DECISION_LOG.md` |
| Calibration 추적 | `../project_management/science/CALIBRATION_TRACKER.md` |
| Release 점검 | `../project_management/release/RELEASE_CHECKLIST.md` |
| 프로젝트 관리 보드 | `../project_management/README.md` |

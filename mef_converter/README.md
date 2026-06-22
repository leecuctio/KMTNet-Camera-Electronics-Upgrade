# KMTNet-CEU MEF Converter

최종 갱신일: 2026-06-22

## 목적

이 디렉토리는 KMT-CEU Archon MK/NT raw FITS를 **L0 64-amplifier raw MEF**로 변환하는 converter와 그 참고 문서를 모은 곳이다. 생성되는 MEF의 데이터 산출물 규격(keyword/ICD)은 [`../mef_fits_spec/`](../mef_fits_spec/README.md)에서 관리한다.

`mef_fits_spec/`(규격)과 `mef_converter/`(구현)을 분리해, 규격 변경과 코드 변경을 독립적으로 추적한다.

## 현재 기준선

| 구분 | 파일 | 버전 |
| --- | --- | --- |
| Converter (최종 실행 파일) | [`kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) | v2.1.1 |
| Geometry version (`GEOMVER`) | — | `CEU-L0AMP-v2.1` |
| 기준 ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx` | v4.0 |

## 디렉토리 구조

| 경로 | 내용 |
| --- | --- |
| `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` | 현행 converter (순수 Python + NumPy, 독립형 FITS writer) |
| `run_kmt_ceu_l0amp_example.sh` | 실행 예제 (실행 위치와 무관하게 동작) |
| `README_KMT_CEU_L0AmpRaw_Converter_v2.1.1.md` | 상세 사용법/검증 결과 |
| `KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` / `.docx` | 작업 정리 (md가 diff 기준본, docx는 배포본) |
| `archive/` | 구버전/개발 스크립트 보관. 운영 기준이 아님 |

## 실행

repo 루트에서:

```bash
python3 mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  KMTN.20260116.000001.MK.fits \
  -o kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits \
  -f --gzip
```

또는 예제 스크립트 (입력/출력 기본값은 repo 루트 기준, `$1`/`$2`로 변경 가능):

```bash
bash mef_converter/run_kmt_ceu_l0amp_example.sh
```

MK 또는 NT 중 하나만 지정하면 짝 파일을 자동으로 찾는다. 옵션(`-o`, `-d`, `-f`, `--gzip`)은 상세 README 참조. 대용량 raw/generated FITS는 `.gitignore`로 제외되어 있어 별도 보관 위치에서 다룬다.

## archive

| 파일 | 비고 |
| --- | --- |
| `archive/kmt_ceu_archon_mknt_to_l0_amp_mef_v2.py` | 현행 `v2_1`로 대체된 구버전 |
| `archive/kmtn2mef_dev_v0.4_debug7_yoverscanfix_midoverscan.py` | 개발/디버그 스크립트 |

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| 데이터 규격 (keyword/ICD) | `../mef_fits_spec/README.md` |
| 기술 결정 기록 | `../project_management/governance/DECISION_LOG.md` |
| Release 점검 | `../project_management/release/RELEASE_CHECKLIST.md` |
| Calibration 추적 | `../project_management/science/CALIBRATION_TRACKER.md` |
| 프로젝트 관리 보드 | `../project_management/README.md` |

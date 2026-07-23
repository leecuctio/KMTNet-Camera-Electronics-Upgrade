# KMTNet-CEU 카메라 특성 측정 (cam_char)

최종 갱신일: 2026-07-23

## 목적

이 디렉토리는 신규 전자부(2× STA Archon, 64-amplifier) 카메라의 **실험실/사이트
특성 측정**에 관련된 계획 문서, 분석 코드, Archon 제어 스크립트, 산출물 테이블을
모으는 곳이다. 측정 결과는 L0 헤더/`AMPINFO`/`XTALKINFO`의 placeholder와
전처리 파이프라인의 no-op 단계(linearity, crosstalk)를 실측값으로 전환하는 데
쓰인다 — 추적은 [CALIBRATION_TRACKER](../project_management/science/CALIBRATION_TRACKER.md).

## 구조

| 경로 | 내용 |
| --- | --- |
| `KMTNet_CCD_Lab_Characterization_Plan_v1.0.md` | 실험실 특성 측정 계획 (v1.0; 검토 의견 반영 개정은 v1.1로) |
| `kmt_cam_char/` | 분석 코드 패키지 (PTC/read noise/linearity/crosstalk/EPER/안정성 — 캠페인과 함께 작성) |
| `archon/` | Archon 실험실 제어 스크립트 (`archon_kmtnet_labtest_v1.0.*.py`, repo 루트에서 이동) |
| `results/` | 산출물 테이블 (기계가독; 스키마는 [results/README.md](results/README.md)) — 소용량만 git |
| (측정 FITS) | git 밖 — 기존 정책대로 `raw/labtest/<날짜>/` 등 로컬 보관 |

## 코드 작성 원칙

- **`mef_pipeline/kmt_ceu_preproc`를 import해서 재사용한다** — L0 리더(`io_l0`),
  geometry(`geometry`, AMPINFO 기반), overscan 보정(`steps/overscan`)을 다시
  구현하지 않는다. 실험실 분석과 운영 파이프라인이 같은 코드로 같은 기하를
  읽는 것 자체가 교차 검증이다.
- 스택 동일: 순수 Python + NumPy + astropy, stdlib unittest.
- keyword/ICD 정의의 원본은 [`mef_fits_spec/`](../mef_fits_spec/README.md) —
  여기서는 링크만 하고 중복 정의하지 않는다. 이 디렉토리가 새로 정의하는 것은
  **측정 산출물의 스키마**(results/README.md)다.

## 산출물 → 반영 경로

| 산출물 | 반영 위치 | 파이프라인 효과 |
| --- | --- | --- |
| 앰프별 GAIN/RDNOISE/SATURAT/LINMAX/READDIR 테이블 | L0 converter 헤더/AMPINFO | `GAINAPPL=T`, 실측 saturation/linearity 플래그 |
| 64×64 crosstalk 계수 (ADU 비, 게인 전, readout-order 좌표) | `XTALKINFO` + `XTALKCAL=T` | crosstalk 보정 활성화 (코드 수정 없음) |
| 선형성 보정계수 (형식: results/README.md) | caldb | `steps/linearity.py` 보정식 활성화 |
| bad/hot pixel 맵 | caldb (MASK bit 1=BAD 규약) | BPM 보강 |

## 관련 자료

- 전처리 파이프라인: [`../mef_pipeline/README.md`](../mef_pipeline/README.md)
- 데이터 규격 (keyword/ICD): [`../mef_fits_spec/README.md`](../mef_fits_spec/README.md)
- 구형 전자부(ICS/ISIS) 참고: [`../ics_legacy/`](../ics_legacy/)
- 실측 전환 계획: 설계 문서 §8, [CALIBRATION_TRACKER](../project_management/science/CALIBRATION_TRACKER.md)

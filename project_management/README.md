# KMTNet-CEU Project Management

최종 갱신일: 2026-06-22

## 목적

이 폴더는 KMT-CEU 신규 전자부 카메라의 L0 64-amplifier raw MEF converter 및 관련 문서, 검증 산출물을 관리하기 위한 작업 보드이다.

현재 관리 기준은 로컬 작업 폴더에 정리된 다음 산출물이다.

- `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx`
- `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`
- `README_KMT_CEU_L0AmpRaw_Converter_v2.1.1.md`
- `KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md`
- `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`
- `KMT_CEU_L0AmpRaw_Converter_v2.1.1_release.zip`

## 현재 기준선

| 항목 | 기준 |
| --- | --- |
| Product | KMT-CEU L0 64-amplifier raw MEF |
| Primary raw archive | 64 amp IMAGE extensions + binary tables |
| Converter | `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` |
| Software/Product version | `v2.1.1` |
| Geometry version | `CEU-L0AMP-v2.1` |
| ICD 기준 | `KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.0.docx` |
| Keyword 기준 | `KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` |
| 검증 raw | `KMTN.20260116.000001.MK.fits`, `KMTN.20260116.000001.NT.fits` |
| 검증 output | `kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz` |
| gzip SHA256 | `7a55e7573eac899cd4b3c50b5dc747efe362a49bef505c1f0f90f53f68760289` |

## 관리 원칙

- L0 raw archive는 CCD-level image가 아니라 64 amplifier MEF이다.
- 각 amp extension은 active pixels와 local overscan pixels를 함께 보존한다.
- CCD-level `SCI_M`, `SCI_K`, `SCI_N`, `SCI_T`는 L1 calibrated product에서 생성한다.
- CEU Archon L0 packing 단계에서는 legacy OSU식 chip-dependent flip을 적용하지 않는다.
- `GAIN`, `RDNOISE`, `SATURAT`, `LINMAX`, `XTALKINFO`, `VOLTINFO`, `TELEMETRY`의 placeholder 값은 운영 calibration 값으로 오인하지 않는다.
- `XTALKCAL=True`는 실측 crosstalk coefficient가 들어간 경우에만 허용한다.

## 현재 상태

| 구분 | 상태 |
| --- | --- |
| L0 product 방향 | 확정 |
| MK/NT raw geometry | 검증 완료 |
| Converter v2.1.1 | 샘플 raw 기준 동작 검증 |
| FITS verification | 통과 |
| Release ZIP | 생성 완료 |
| Calibration values | 실측값 대기 |
| READDIR | flat/star sequence test로 최종 확인 필요 |
| 운영 telemetry | Archon/TCS/auxiliary 실데이터 연동 필요 |

## 관리 파일

| 파일 | 용도 |
| --- | --- |
| `BACKLOG.md` | 남은 일, 우선순위, 완료 조건 |
| `DECISION_LOG.md` | 확정된 기술 결정과 근거 |
| `RELEASE_CHECKLIST.md` | 버전 릴리스 전 점검 절차 |
| `SITE_UPGRADE_MILESTONES.md` | SSO, CTIO, SAAO 사이트별 업그레이드 마일스톤 |

## Git 관리 기준

- Git에는 소스 코드, 문서, 프로젝트 관리 문서를 담는다.
- Raw FITS, generated MEF FITS, gzip FITS, conversion summary, checksum sidecar, release ZIP은 `.gitignore`로 제외한다.
- 대용량 데이터 산출물은 파일명, SHA256, 생성 command를 문서에 기록하고 실제 파일은 별도 저장소 또는 데이터 보관 위치에서 관리한다.
- release ZIP은 Git에 직접 넣기보다 release checklist를 통해 재생성 가능한 산출물로 관리한다.

## 작업 흐름

1. 변경 전 `BACKLOG.md`에서 작업 ID를 확인한다.
2. 코드, ICD, keyword, sample output 중 영향을 받는 산출물을 함께 확인한다.
3. 변경 후 converter 실행, FITS 검증, HDU/keyword/summary/checksum을 확인한다.
4. geometry 또는 product 정책이 바뀌면 `DECISION_LOG.md`에 결정 기록을 남긴다.
5. 배포 전 `RELEASE_CHECKLIST.md`를 기준으로 release 폴더와 ZIP을 다시 만든다.

## 버전 규칙

| 변경 유형 | 예시 | 권장 처리 |
| --- | --- | --- |
| Patch | FITS card formatting, parser bug, README correction | `v2.1.x` |
| Product/software minor | keyword 추가, CLI 옵션 추가, table column 추가 | `v2.x.0` |
| Geometry change | amp ordering, section, chip orientation, HDU layout 변경 | `GEOMVER` 갱신 및 ICD major/minor 갱신 |
| Calibration update | 실측 gain/read-noise/crosstalk/telemetry 반영 | calibration version keyword 갱신 |

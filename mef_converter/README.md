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
| `kmt_ceu_legacy32_to_l0amp_mef_v2.py` | 구형 32-amp MEF → 신형 64-amp L0 MEF **목업** 변환기 v2.0 (독립 실행형, 파이프라인 개발용) |
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

## Mockup 생성 (구형 32-amp MEF → 신형 64-amp L0 MEF)

신규 전자부 실제 관측 자료가 없는 동안, 전처리/자료처리 파이프라인 개발·검증에 쓸 신형 64-amp MEF 목업을 **구형 카메라 32-amp MEF**에서 만든다. 각 CCD를 8개 amp가 strip 전체(9232행)로 읽던 구형 자료를, strip을 CCD 좌표(`CCDSEC`) 기준으로 TOP/BOT 절반(4616행)씩 나눠 신형 16-amp/CCD 구조로 재배치한다. K·N 칩은 구형 라벨 번호가 strip 위치와 반대이므로 **이름이 아닌 기하로 매칭**한다.

- 픽셀은 구형 실측 값을 그대로 보존(활성 1152열 + 실측 오버스캔). 신형 오버스캔 48열은 구형 32열 오버스캔에서 결정론적으로 구성한다.
- **균일 패킹**: 64개 amp 모두 `DATASEC=[1:1152,1:4616]`, `BIASSEC=[1153:1200,1:4616]` (data-left). 같은 별이 모든 amp 영상에서 동일한 in-amp (x,y)에 놓인다. ICD는 amp 5–8/13–16의 오버스캔을 왼쪽에 두므로 이 목업은 의도적 편차이며 `AMPPACK='DATA_LEFT'`, `GEOMVER='CEU-L0AMP-v2.1-mockU1'`로 기록한다.
- **WCS/좌표 이식**: 구형 strip별 WCS를 CRPIX 이동(x−27 프리스캔, TOP은 y−4616)으로 합성해 ds9 sky 좌표가 구형 표시와 일치(v2.0은 최단왕복 부동소수점 기록으로 오차 ≈0, 기계 정밀도). `LTV1/LTV2/LTM`(IRAF physical) 기록으로 ds9 physical 좌표가 구형 파일과 동일: x=strip 열 1–1152, y=CCD 행 1–9232 (TOP amp는 `LTV2=-4616`). `DTV/DTM`은 ds9/IRAF 규약(detector = DTM×physical + DTV)에 맞춰 `DETSEC`과 자기일관: `DTV2=CHIP_Y0-1` (양 끝 공통).
- 채울 수 있는 관측/사이트/노출 키워드는 구형 primary header에서 채운다. 이 변환에서 채울 수 없는 값은 **문자열 키워드는 `na`**, **정수형 키워드/컬럼은 `-1`**(예: `NUMFILES`, `RAWNAX1/2`, `MIDOVSCY`, AMPINFO `RAWX0..RAWY1`)로 표시해 downstream의 `int()` 파싱을 보존한다. 구형의 valueless 카드(TSHSHUT, DSUP 등)는 감지해 `na` 처리. `MOCKDATA=T`(primary+각 amp), `ORIGFILE`/`ORIGEXT`/`CONVPROG` 등 목업 provenance를 기록한다.
- 출력 구조는 실제 64-amp L0 제품과 HDU·키워드가 동일(HDU 69개, amp `1200×4616`, `AMPINFO/XTALKINFO/VOLTINFO/TELEMETRY`). `JD`/`MJD-OBS`는 완전 정밀도로 기록되어 상호 일치.

```bash
# 단일 파일
python3 mef_converter/kmt_ceu_legacy32_to_l0amp_mef_v2.py kmtc.20260630.011092.fits -d . -f

# 여러 장 일괄 (구형 원본만 정확히 지정 — 목업 산출물 재입력 방지)
ls -1 | grep -E '^kmtc\.[0-9]{8}\.[0-9]{6}\.fits$' \
  | xargs python3 mef_converter/kmt_ceu_legacy32_to_l0amp_mef_v2.py -d . -f
```

출력 파일명: `<prefix>.<YYYYMMDD>.<NNNNNN>.ceu.l0amp.mock64.mef.fits`.

## archive

| 파일 | 비고 |
| --- | --- |
| `archive/kmt_ceu_archon_mknt_to_l0_amp_mef_v2.py` | 현행 `v2_1`로 대체된 구버전 |
| `archive/kmt_ceu_legacy32_to_l0amp_mef_v1.py` | 목업 변환기 구버전 (v2.0으로 대체: DTV2/JD 정밀도/valueless 카드/정수 na 수정) |
| `archive/kmtn2mef_dev_v0.4_debug7_yoverscanfix_midoverscan.py` | 개발/디버그 스크립트 |

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| 데이터 규격 (keyword/ICD) | `../mef_fits_spec/README.md` |
| 기술 결정 기록 | `../project_management/governance/DECISION_LOG.md` |
| Release 점검 | `../project_management/release/RELEASE_CHECKLIST.md` |
| Calibration 추적 | `../project_management/science/CALIBRATION_TRACKER.md` |
| 프로젝트 관리 보드 | `../project_management/README.md` |

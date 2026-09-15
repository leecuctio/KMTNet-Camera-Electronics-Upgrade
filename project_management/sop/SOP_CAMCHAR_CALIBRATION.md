# SOP: cam_char 카메라 특성 측정(캘리브레이션) 캠페인

최종 갱신일: 2026-09-15

## 목적 / 적용 범위

돔플랫·바이어스 프레임으로 amp별 GAIN/RDNOISE/SATURAT/LINMAX/READDIR을 측정해
L0 헤더·`AMPINFO`의 placeholder를 실측값으로 전환하는 절차를 정의한다.
대상 코드: [`cam_char/kmt_cam_char/`](../../cam_char/kmt_cam_char/), 산출물 스키마: [`cam_char/results/README.md`](../../cam_char/results/README.md).

이 SOP는 **현재 검증된 절차**, 즉 **LEGACY 캠페인(구형 32-amp 전자부, 2026-06/07 취득) 재현**을 다룬다.

- `runner.py`의 campaign 이름은 `LEGACY-{site}-{night}` 형식으로 고정되어 있고, `report.py`는 `amp_characterization_LEGACY-*.csv` 패턴만 집계한다 — 신규(실제 CEU Archon) 캠페인에 그대로 재사용하려면 이 명명 규칙을 먼저 확인/조정해야 한다.
- 실측 Archon으로 신규 자료를 **취득**하는 스크립트(`archon/archon_kmtnet_labtest_v2.py`)는 2026-09-15 기준 **시뮬레이터 검증까지만 완료, 실 하드웨어 미검증**이다 ([ARCHON_LABTEST_V2.md](../../cam_char/archon/ARCHON_LABTEST_V2.md) §5 확인 사항 필독). 실 하드웨어 투입 전 해당 문서 §5의 5개 항목을 먼저 점검한다.
- 아래 절차는 이미 취득되어 로컬 `raw/preproc/<site>/<night>/`에 있는 레거시 원본(git 비추적)을 입력으로 가정한다.

## 사전 확인

- [ ] repo 루트 기준으로 실행한다.
- [ ] Python3 + NumPy + astropy 사용 가능.
- [ ] 대상 야간의 레거시 32-amp raw가 `raw/preproc/<site>/<night>/*.fits`에 있다 (git 비추적 — 로컬에서 확보).
- [ ] `mef_converter/kmt_ceu_legacy32_to_l0amp_mef_v2.py`(32→64-amp mock 변환기)가 사용 가능하다.
- [ ] 결과를 실제 반영할 계획이면 [`project_management/science/CALIBRATION_TRACKER.md`](../science/CALIBRATION_TRACKER.md)에서 대상 항목(GAIN/RDNOISE/SATURAT/LINMAX/READDIR)의 현재 상태를 확인한다.

## 절차 (LEGACY 캠페인 재현)

### 1. QC 스크리닝 + 비정상 동작 집계

```bash
python3 cam_char/kmt_cam_char/qc.py raw/preproc/<site>/<night> \
        cam_char/results/qc_legacy_<site>_<night>.json
```

야간별 프레임 수, bias/flat 신호 레벨, 포화 도달 여부, dead/flooding amp 목록을 JSON으로 낸다. 출력 마지막 줄에 요약이 한 줄 찍힌다(예: `74 frames, bias 20, levels {...}, sat_reached=False, dead=[], flooding=[...]`). `astropy.io.fits.card`의 `WARNING: ... invalid or follows an unrecognized non-standard convention` 경고는 레거시 헤더의 비표준 키워드(`GAINDL`, `TSHSHUT`, `DSUP` 등)에 대한 것으로 **무해하며 무시**한다.

### 2. Mock64 변환 (32-amp legacy → 64-amp mock L0)

```bash
ls raw/preproc/<site>/<night>/*.fits | xargs -P 4 -n 8 \
  python3 mef_converter/kmt_ceu_legacy32_to_l0amp_mef_v2.py \
  -d raw/preproc/<site>/<night>/mock64 -f
```

측정 코드는 mock64 파일만 읽는다(`kmt_cam_char/core.py`가 L0 reader/geometry를 `mef_pipeline/kmt_ceu_preproc`에서 그대로 가져와 쓰기 때문에, legacy raw를 직접 읽지 않는다). 이미 변환된 mock64가 있으면 건너뛰어도 되고, `-f`로 재실행해도 안전하다(결정론적 변환).

### 3. 측정 — amp 특성 CSV 생성

```bash
python3 cam_char/kmt_cam_char/runner.py \
  cam_char/results/qc_legacy_<site>_<night>.json \
  raw/preproc/<site>/<night>/mock64 \
  cam_char/results/amp_characterization_LEGACY-<SITE>-<night>.csv
```

QC selection을 bias/flats(PTC)/repeat/satprobe로 나눠 amp별(64개, 물리 32-amp를 TOP/BOT으로 분리) read noise, PTC gain+곡률, linearity, saturation, serial EPER CTE, PRNU, 야간 내 gain 안정성을 측정한다. **사이트-야간당 약 13분** 소요. 출력 CSV는 헤더 1행 + amp 64행 = 65행이어야 한다 ([스키마](../../cam_char/results/README.md) 1절).

- [ ] 실행 시작 시 콘솔에 `[LEGACY-<SITE>-<night>] bias N, flats N, repeat N, satprobe N` 한 줄이 찍히는지 확인 (QC selection이 제대로 읽혔다는 신호). 이후 `16/64 amps`, `32/64`, `48/64`, `64/64` 진행률과 `wrote <출력 CSV 경로>` 완료 줄이 이어진다.
- [ ] 완료 후 CSV 행 수 = 65 확인 (헤더 1 + amp 64).
- [ ] `STATUS` 컬럼에 QC census(DEAD/FLOOD)와 측정 상태가 반영되어 있는지 확인 — QC 단계(1단계)의 flooding/dead 목록과 교차 확인.

### 4. 결과값 스케일 확인 (중요)

`kmt_cam_char.core`의 픽셀 판독은 헤더 `BZERO/BSCALE`을 적용한 **물리 unsigned ADU**를 쓴다(2026-09-05 정정). 단, **기존 LEGACY-\* 캠페인 CSV의 절대 ADU 값**(`BIAS_ADU`, `SATURAT`, `LINMAX`, `LIN_RANGE_LO/HI` 등)은 구 스케일(물리값+32768, mod 65536)로 남아 있다. `GAIN`/`RDNOISE`/`PRNU_PCT`/`CTE_SERIAL` 등 **차분 통계는 두 스케일에서 동일**하므로 영향 없음. 레거시-신규 절대 레벨을 비교할 때만 레거시 값에서 32768을 뺀다. 상세는 [results/README.md](../../cam_char/results/README.md) 각주 참조.

검증 예 (M01T, SSO 20260610): 기존 커밋 CSV `BIAS_ADU=34472` vs 이 SOP 재현 실행 결과 `BIAS_ADU=1704` — 차이가 정확히 32768. 같은 amp의 `GAIN=1.6116`/`RDNOISE=6.758`은 기존값(1.6076/6.741)과 소수 셋째 자리 수준까지 일치(측정 알고리즘 재현성 확인, 완전 동일하지 않은 것은 정상 — QC selection의 신호 레벨 그룹핑에 미세한 순서 의존성이 있을 수 있음).

### 5. 보고서 갱신

```bash
python3 cam_char/kmt_cam_char/report.py cam_char/results \
  cam_char/KMT_CamChar_Legacy_Baseline_Report_v1.0.md
```

`RESULTS_DIR`(`cam_char/results`)에 있는 **모든** `amp_characterization_LEGACY-*.csv`와 `qc_legacy_*.json`을 다시 모아 보고서를 재생성한다 — 이번에 새로 추가한 캠페인 하나만 반영되는 게 아니라 기존 캠페인 전체가 다시 집계되므로, 다른 사이트/야간 CSV를 실수로 지우거나 이름을 바꾸지 않았는지 먼저 확인한다.

### 6. (선택) 측정값을 L0 MEF 헤더에 스탬프

```bash
python3 mef_converter/kmt_ceu_legacy32_to_l0amp_mef_v2.py <legacy.fits> \
  --ampchar cam_char/results/amp_characterization_LEGACY-<SITE>-<night>.csv -d out -f
```

신규(64-amp 실물) converter에 스탬프하는 절차는 [SOP_MEF_CONVERTER_RUN.md](SOP_MEF_CONVERTER_RUN.md) 2단계와 동일한 메커니즘이다(amp extension header + `AMPINFO` 테이블 양쪽 반영, primary `AMPCHAR` 카드에 테이블명 기록).

### 7. (선택, 사전 준비 필요) 확장 진단 5계열

`diagnostics.py`(PTC 5패널+CMRR) / `biasdiag.py`(행렬/PSD/FPN/상관) / `adccheck.py`(ADC 코드 결함) / `linearity.py`(확장, linearizer 계수) / `satshut.py`(포화 원인·persistence·셔터·shading)는 `--bias/--flats/-o OUTDIR --campaign NAME` 규약의 독립 CLI다. 정식 입력은 [ARCHON_LABTEST_V2.md §5b](../../cam_char/archon/ARCHON_LABTEST_V2.md)의 취득 타입 6–9(기준노출 인터리브, 포화 램프, 셔터 시퀀스, 포화 직후 bias)이며, 돔플랫/바이어스만으로 소급 적용한 예시와 한계는 [KMT_CamChar_SSO_Diagnostics_Report_v1.0.md](../../cam_char/KMT_CamChar_SSO_Diagnostics_Report_v1.0.md) §2/§5/부록 A를 따른다.

⚠️ 돔플랫/바이어스만으로 돌린 결과는 사용 제한이 있다 — 같은 보고서 §5/§6 기준:
- `linearity.py` 확장의 linearizer 계수는 **caldb 반영 금지** (모듈 동작 기록 용도로만 보존)
- `satshut.py`의 포화 원인 분류·persistence·셔터값은 **인용 금지** (full well 하한만 참고 가능)
- 정식 타입 6–9 취득 전에는 이 5계열을 1차 캘리브레이션 산출물로 쓰지 않는다.

### 8. Calibration Tracker 갱신

새 실측값이 채택되면 [`project_management/science/CALIBRATION_TRACKER.md`](../science/CALIBRATION_TRACKER.md)의 해당 행(GAIN/RDNOISE/SATURAT/LINMAX/READDIR)에 상태와 완료 조건 충족 여부를 반영한다.

## 문제 해결

| 증상 | 확인 사항 |
| --- | --- |
| `astropy.io.fits.card` invalid keyword 경고 다수 출력 | 레거시 헤더의 비표준 키워드(GAINDL, TSHSHUT, DSUP 등)로 무해함 — 무시 |
| `runner.py`가 특정 프레임을 못 찾음 | 2단계 mock64 변환이 해당 야간 전체에 대해 끝났는지 확인 (`mock_path()`는 legacy 파일명 stem으로 mock64 쌍을 찾는다) |
| CSV 행 수가 65가 아님 | QC json의 selection이 비정상(프레임 수 불일치)이거나 mock64 변환이 일부 누락된 경우 — 1·2단계부터 재확인 |
| `report.py` 실행 후 다른 사이트/야간 결과가 사라짐 | `results/` 디렉토리에서 해당 CSV/JSON 파일이 삭제/이름 변경되지 않았는지 확인 — report는 디렉토리 전체를 재집계한다 |
| 절대 ADU 값이 기존 캠페인과 어긋나 보임 | 4단계의 +32768 스케일 차이(레거시 vs 신규 스캔) 확인 — 차분 통계는 영향 없음 |

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| cam_char 개요/코드 구조 | `../../cam_char/README.md` |
| 산출물 스키마 (CSV/FITS 컬럼) | `../../cam_char/results/README.md` |
| 실험실 특성 측정 계획 | `../../cam_char/KMTNet_CCD_Lab_Characterization_Plan_v1.0.md` |
| LEGACY 기준선 보고서 | `../../cam_char/KMT_CamChar_Legacy_Baseline_Report_v1.0.md` |
| SSO 진단 5계열 적용 보고서 (한계·재현 명령) | `../../cam_char/KMT_CamChar_SSO_Diagnostics_Report_v1.0.md` |
| Archon 취득 스크립트 설계/하드웨어 투입 전 확인 사항 | `../../cam_char/archon/ARCHON_LABTEST_V2.md` |
| MEF Converter 실행 SOP (`--ampchar` 스탬프 메커니즘) | `SOP_MEF_CONVERTER_RUN.md` |
| Calibration Tracker | `../science/CALIBRATION_TRACKER.md` |

## 개정 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-09-15 | 최초 작성. LEGACY 캠페인(SSO 20260610) QC→mock64→측정 파이프라인을 실행해 명령/소요시간/출력 형식을 확인 |

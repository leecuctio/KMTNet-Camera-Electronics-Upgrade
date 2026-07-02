# KMTNet-CEU L0→L1 전처리 파이프라인

최종 갱신일: 2026-07-02

## 목적

이 디렉토리는 **L0 64-amplifier raw MEF**(`../mef_converter/` 산출물)를 amp 단위 교정 후
CCD 단위로 조립한 **L1 CCD-level calibrated MEF**로 변환하는 전처리 파이프라인이다.
처리 순서는 keyword 규격 §12(`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`)를 따른다.

설계 문서: [`KMT_CEU_L1_Preproc_Pipeline_Design_v1.2.md`](KMT_CEU_L1_Preproc_Pipeline_Design_v1.2.md)

## 현재 기준선

| 구분 | 값 |
| --- | --- |
| 파이프라인 | `kmt_ceu_preproc` v1.2 (순수 Python + NumPy + astropy) |
| L1 제품 | `PRODVER=v1.1`, 단일 MEF: PRIMARY + (SCI/MASK)×4 CCD + CALHIST (~1.7 GB/노출) |
| VAR plane | 기본 제외 (`VARINCL=F`; 재구성식 header 기록, `run --with-var`로 생성 가능) |
| L1 픽셀 단위 | electrons (`BUNIT='electron'`, amp별 GAIN 적용, placeholder면 1.0 + `GAINAPPL=F`) |
| 종점 | CCD 조립 + 근사 WCS (`WCSAPPRX=T`; 정밀 astrometry는 후단) |
| L1 파일명 | `<prefix>.<YYYYMMDD>.<NNNNNN>.ceu.l1ccd.mef.fits` |

## 처리 단계 (트랙 A: 과학 프레임)

| # | 단계 | 내용 | 상태 |
| --- | --- | --- | --- |
| 1 | 검증/Ingest | 규격 §11 구조 검사, AMPINFO/헤더 geometry 로드 (하드코딩 없음) | 동작 |
| 2 | Saturation/LINMAX 플래그 | raw ADU 기준 MASK bit 기록 | 동작 |
| 3 | Overscan | `BIASSEC` 행별 clipped mean + 이동 median 평활, mock은 앞 32열만. **오염 가드**: overscan 레벨이 master bias의 `OVSCLVL`에서 >100 ADU 벗어나면(하늘 신호 유입) 기준 상수 감산으로 대체하고 amp를 `NO_OVERSCAN_FIT` 플래그 | 동작 |
| 4 | Bias | master bias 감산 (amp 단위, ADU) | 동작 |
| 5 | Dark | 구조만, 기본 off (Rehearsal 후 결정) | no-op |
| 6 | Linearity | 계수 미측정 → LINMAX 플래그만 | no-op |
| 7 | Crosstalk | `XTALKINFO` 64×64, controller group 내 적용. `XTALKCAL=F`면 no-op | no-op |
| 8 | Gain | ADU→electrons (`--with-var` 시 variance RN²+Poisson 초기화·전파) | 동작 |
| 9 | Flat | 필터별 master flat 나눗셈 + variance 전파 | 동작 |
| 10 | BPM | bad pixel MASK 병합 (픽셀값 보존) | 동작 |
| 11 | AMPMATCH | amp 경계 조화 — 경계 양쪽 zone 중앙값으로 amp별 잔차 gain/bias 보정 (CCD 평균 보존) | 동작 |
| 12 | 조립 | `CCDSEC` 배치(flip 없음), seam 지표, 근사 WCS, `CALHIST`/provenance | 동작 |

MASK bits: 1=BAD, 2=SATURATED, 4=NONLINEAR, 8=XTALK, 16=AMP_SEAM, 32=NO_OVERSCAN_FIT

VAR 재구성 (D-007 개정): `VAR = (RDNOISE² + SCI×flat) / flat²` [electron²] —
flat은 primary header `CALFLAT`이 가리키는 master flat plane, RDNOISE는 L0 amp
header/AMPINFO. SATURATED/NONLINEAR는 raw 기준 판정이라 재구성 불가 → MASK는 항상 포함.

**AMPMATCH (amp 경계 조화)**: flat/gain/bias 후에도 남는 amp 경계 단차(twilight
flat과 밤하늘 조명 불일치, gain drift, bias 잔차)를 각 내부 경계 양쪽의 좁은
zone(기본 32px, BAD/SAT 제외) 중앙값으로 측정해, CCD당 16-amp 보정치를 정규화
최소제곱으로 풀어 적용한다. 하늘이 충분하면(≥100 e-) 곱셈(gain성, 상한 10%),
어두우면 덧셈(bias성) — `auto`가 기본. overscan 오염 fallback이 발생한 칩은
잔차가 덧셈성 baseline 오차이므로 **덧셈 모드로 강제**하고(상한 2,000 e-),
정상 amp들을 anchor로 평균을 고정해 오염 amp만 이동시킨다. CCD 평균을 고정해
광도 중립이며, 죽은 amp는 제약에서 제외되어 보정 없이 유지된다. 적용
배율/오프셋은 SCI 헤더 `AMMODE`/`AMC<amp>` 카드와 QA JSON에 기록되어 감사·역적용이
가능하다. `run --ampmatch off|mult|add|auto`로 제어.

QA seam 지표는 경계 바로 옆 1픽셀(고정 패턴 edge-column, `MASK_SEAM` 플래그됨)을
건너뛰고 그 다음 4픽셀 밴드끼리 비교해, 검출기 화장품이 아닌 amp 수준 교정 오차를
측정한다.

## 실행

repo 루트에서 (mock 야간 전체: master bias/flat/BPM → OBJECT 28장 → QA summary):

```bash
bash mef_pipeline/run_mock_night.sh . ./l1_mock
```

개별 명령:

```bash
PP="python3 mef_pipeline/kmt_preproc.py"
$PP calib-bias  bias1.fits bias2.fits ...   -d l1_out          # master bias
$PP calib-flat  flatV1.fits flatV2.fits ... -d l1_out          # master flat (필터 자동)
$PP bpm         --flat l1_out/caldb/master_flat_I.fits -d l1_out
$PP run         object*.fits -d l1_out -f                      # L0 -> L1
$PP qa-summary  -d l1_out                                      # QA markdown
```

교정자료는 `l1_out/caldb/`(JSON index로 site+필터+최근접 날짜 선택), QA JSON은
`l1_out/qa/`에 쌓인다. 대용량 산출물은 `.gitignore` 대상이며 별도 보관 정책을 따른다.

## 단위 테스트

```bash
python3 -m unittest discover -s mef_pipeline/tests
```

합성 소형 L0(4-amp)로 geometry/overscan/조립/variance와 마스터 생성→L1까지의
end-to-end 산술(gain 2.0 e-/ADU 검증 가능)을 시험한다. pytest 불필요(stdlib unittest).

## 검증 결과 (mock 2026-06-30 야간, 40노출)

- 단위 테스트 23개 통과
- **geometry 정밀검증**: 교정 없이 DATASEC trim+조립한 mosaic이 구형 32-amp 원본의
  trim mosaic과 4개 CCD 모두 **픽셀 단위 완전 일치** (K/N 역순 strip 매핑 포함)
- master bias(BIAS 5장)·master flat V/I(각 3장)·BPM 생성, OBJECT 28장 → L1 28개
  모두 구조(HDU 10개, BUNIT, provenance, JD/MJD 일관성)와 astropy
  `verify('exception')` 통과 — 상세는 `l1_mock/qa/qa_summary.md`
- **amp seam 제거 (AMPMATCH)**: 무보정 조립(gain만 적용) 대비 100배 이상 감소
  (예: 011103 CCD별 470–6,178 e- → **2.2–4.2 e-**; 28노출 max|seam| 중앙값
  **23 e-** ≈ sky 4,750 e-의 0.5%). overscan 오염 3개 칩도 additive 복구로
  76–249 e- 수준(해당 amp는 `NO_OVERSCAN_FIT` 플래그)
- **QA가 실제 검출기 이상 검출 (1)**: 구형 N칩의 죽은 비디오 채널(legacy N02,
  mock N07T/B strip)이 flat response 기반으로 1,063만 픽셀 BAD 플래그됨
- **QA가 실제 검출기 이상 검출 (2)**: 일부 legacy 프레임에서 특정 칩의 serial
  overscan이 bias(~2,030 ADU)가 아닌 **하늘 수준**(예: 011108·011112의 M칩,
  011107의 T칩)으로 오염됨을 확인 — overscan 오염 가드가 `OVSCLVL` 기준 상수
  감산으로 대체해 과학 신호를 보존하고 해당 amp를 플래그
- 처리 속도: 노출당 ~5초 (검증·SHA256·1.7 GB L1 쓰기 포함, Apple SSD 기준)

## 실측값 전환 (Rehearsal/Site)

gain/RN/linearity/crosstalk가 실측되면 **코드 수정 없이** L0 헤더/`XTALKINFO`와
caldb의 교정자료 교체만으로 반영된다 (`GAINAPPL`/`XTALKAPL`로 상태 추적).
placeholder 정책은 DECISION_LOG D-005를 따른다.

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| 설계 문서 | `KMT_CEU_L1_Preproc_Pipeline_Design_v1.2.md` |
| L0 데이터 규격 (keyword/ICD) | `../mef_fits_spec/README.md` |
| L0 변환기 | `../mef_converter/README.md` |
| 기술 결정 기록 (D-006~D-008: L1 단위/구조/종점) | `../project_management/governance/DECISION_LOG.md` |
| Calibration 추적 | `../project_management/science/CALIBRATION_TRACKER.md` |

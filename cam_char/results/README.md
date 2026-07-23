# cam_char 산출물 스키마

최종 갱신일: 2026-07-23

측정 캠페인의 최종 산출물은 아래 **기계가독 테이블**로 낸다. L0 헤더/AMPINFO
반영은 이 파일들에서 기계적으로 수행한다(수기 전사 금지). 모든 값의 ADU는
**raw ADU**(bias 포함) 기준임을 명시한다 — 파이프라인의 saturation/linearity
플래그가 raw ADU에서 동작하기 때문이다.

## 1. amp_characterization_<CAMPAIGN>.csv (64행)

| 컬럼 | 단위 | 내용 |
| --- | --- | --- |
| AMPID | — | 전역 amp ID 1–64 |
| EXTNAME | — | M01T … T08B |
| GAIN, GAIN_ERR | e-/ADU | PTC(곡률 모델) 게인 |
| RDNOISE, RDNOISE_ERR | e- | bias 쌍차분 (MAD 기반) |
| SATURAT | raw ADU | min(ADC, analog, full-well) × 0.98 |
| LINMAX | raw ADU | 비선형 ≤1% 최대 신호 |
| READDIR | — | 마스크 기하+blooming+EPER tail로 확정 (+X/-X, +Y/-Y) |
| STATUS | — | OK / DEAD / NOISY / … |
| CAMPAIGN, DATE, CONFIG | — | 측정 캠페인 ID, 일자, Archon config 버전 |

## 2. xtalk_matrix_<CAMPAIGN>.csv (4096행, XTALKINFO 스키마)

SOURCE_AMP, TARGET_AMP, XTALK_COEF, XTALK_ERROR, XTALK_VERSION, STATUS.
규약: **coef = ΔADU_victim/ADU_aggressor, 둘 다 overscan 차감, 게인 변환 전,
readout-order 좌표**(파이프라인 적용 규약과 동일). 20–80% 신호 구간 기울기로
단일 계수화; 비선형/포화 거동은 STATUS(NONLINEAR 등)에 기록. 컨트롤러 간
블록(Archon1↔2)은 0 일치 확인 결과를 STATUS로 기록.

## 3. linearity_coeff_<CAMPAIGN>.csv (64행)

AMPID, 보정 함수형(문서화된 다항식), a1..an, 유효 raw ADU 범위, 잔차 RMS,
CAMPAIGN/DATE/CONFIG. 적용 도메인(raw ADU vs bias 차감 후)을 헤더 주석으로
명시 — `steps/linearity.py` 활성화 입력.

## 4. bad_pixel_mask_<CAMPAIGN>.fits

CCD별 uint8, 파이프라인 MASK 규약 bit 1(BAD). 기준: hot(dark>기준),
dead/low(<50% 응답), unstable(RTS) — 기준값은 계획서 §10/§11 개정판을 따름.

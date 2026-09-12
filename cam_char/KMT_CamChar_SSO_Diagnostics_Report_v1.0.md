# KMTNet 카메라 특성 — SSO 진단 5계열 적용 보고서 (LEGACY-SSO 캠페인)

**v1.0 | 2026-09-05** | 대상: `LEGACY-SSO-20260610` · `LEGACY-SSO-20260710` (구형 32-amp 전자부, mock64 변환본)

## 1. 목적과 지위

2026-09-05 구현된 진단 분석 5계열(`diagnostics`/`biasdiag`/`adccheck`/`linearity` 확장/`satshut`)을
SSO 사이트의 기존 LEGACY 캠페인 2야간에 소급 적용한 결과 보고서다. 목적은 둘이다.

1. **신규 모듈의 실자료 검증** — 합성자료 단위시험(결함 주입 → 정량 회수)을 통과한 코드가
   실측 자료에서 기존 측정(`runner.py` → [기준선 보고서](KMT_CamChar_Legacy_Baseline_Report_v1.0.md))과
   정합하는지 교차 확인한다.
2. **SSO 구형 전자부의 심화 진단** — 기준선 보고서가 집계 수준으로 남긴 비정상 동작
   (overscan 침수, T칩 잡음)을 앰프 단위로 정량화한다.

이 자료는 진단 5계열의 설계 취득([타입 6~9](archon/ARCHON_LABTEST_V2.md) — 기준노출 인터리브,
포화 램프, 0.1~2 s 셔터 시퀀스, 포화 직후 연속 bias)을 **충족하지 않는** 돔플랫/바이어스
캠페인이므로, §5의 커버리지 한계와 사용 금지 항목을 함께 읽어야 한다. 모든 ADU는
**물리 unsigned 스케일**(BZERO 적용, 2026-09-05 정정 이후)이다 — 구 LEGACY CSV 절대값과
비교할 때는 [results/README.md](results/README.md) 각주의 +32768 환산을 적용한다.

## 2. 자료와 실행

QC selection(`qc_legacy_sso_<야간>.json`) 기준 야간별 구성은 동일하다:

| 구분 | 프레임 | 내용 |
| --- | ---: | --- |
| bias | 20 | 시퀀스 앞 10 + 꼬리 10 |
| flats (ptc) | 54 | 2.5~20 s 8단계 돔플랫 (물리 ~7.0k → 46.6k ADU, 포화 미도달) |
| repeat (refs) | 19 | 10 s 반복 |
| persist | 10 | 마지막 플랫 이후 꼬리 bias |
| short / long | 15 / 5 | 2.5·5·7.5 s / 12.5 s (셔터·shading 입력) |

실행 매트릭스는 2야간 × 5모듈 전 조합이며 전부 정상 종료했다(총 98분, 2026-09-05).
산출물은 `results/LEGACY-SSO-<야간>/<모듈>/`에 앰프별 진단 페이지(`amps/`, 64장) +
카메라 요약 PNG + 수치 CSV로 남는다. gain/RDNOISE가 필요한 모듈(`linearity`, `satshut`)에는
해당 야간의 `amp_characterization_LEGACY-SSO-<야간>.csv`를 `--ampchar`로 공급했다.
재현 명령은 부록 A.

## 3. 신규 모듈 실자료 검증 — 기준선과의 교차

| 항목 | 20260610 | 20260710 | 판정 |
| --- | --- | --- | --- |
| gain 중앙값 (`diagnostics`) | 1.6595 | 1.6633 | 기준선(runner PTC) 1.667/1.666과 0.2~0.5% 내 일치 |
| gain 앰프별 교차 (vs runner) | med \|Δ\| 0.45% (max 2.6%) | med \|Δ\| 0.48% (max 1.8%) | 독립 구현 간 정합 |
| gain 야간 간 재현 (610↔710) | med 0.21%, max 1.27% (n=60) | — | 기준선 보고서(0.27/1.13%)와 동급 |
| RDNOISE 중앙값 | 7.02 e⁻ | 7.04 e⁻ | 기준선 7.00/7.06 e⁻ 일치 |
| bias 준위 중앙값 | 1673 ADU | 1673 ADU | biasdiag RN_ADU 4.193 × gain = 6.97 e⁻로 자기일관 |
| PTC curvature a 중앙값 | 2.41e-6 /ADU | 2.39e-6 /ADU | 전 앰프 균일 |

단위시험(합성 결함 주입: gain 0.35%·LINMAX ±0.3%·셔터 Δt ±0.6 ms·τ +3.3% 회수)도
이 환경(framework Python 3.10)에서 전부 통과했다. **신규 5계열의 수치 신뢰성은 확립**로 판정한다.

## 4. SSO 심화 소견

### 4.1 Overscan 침수(공통모드/CMRR) 정량화 — 가장 큰 소견

`diagnostics`의 overscan-vs-signal 기울기 진단이 기준선 QC census(침수 16/22앰프)보다
민감하게 비정상 동작을 잡는다:

| 야간 | `OSCAN_SLOPE` 플래그 | 최악 앰프 (기울기 → @50k ADU 환산) |
| --- | --- | --- |
| 20260610 | **43/64** (QC flood strip과 26 중첩 + 추가 검출) | N06T −8.7e-4 (≈ −44 ADU) · N06B · N04T · M03B/T |
| 20260710 | **53/64** (39 중첩) | **T06B −1.33e-2 (≈ −665 ADU)** · T06T · T02B/T · T01B |

710의 T칩 기울기 크기는 QC census의 "+797 ADU@50k" 침수와 정합한다(부호 규약은 상이 —
앰프별 페이지 참조). 구형 전자부의 신호 의존 공통모드가 광범위하다는 뜻이며, **신규 CEU
인수 시험에서 CMRR(overscan slope ≈ 0)을 acceptance 항목으로 확인해야 하는 근거**다.

### 4.2 M07/M08 비정상 동작 클러스터 (AMPID 7·8·15·16)

네 진단이 같은 앰프 무리를 독립적으로 지목한다 — 610 QC 침수 최상위(M07 −17, M08 −20 ADU@50k)와 동일 무리:

- `diagnostics`: 쌍 드리프트 가드에 걸려 **gain 측정 탈락**(TOO_FEW_PAIRS, 양야간 동일 4앰프)
- `satshut`: p99.9가 65.2k ADU 부근 plateau → ANALOG 분류 (침수 왜곡의 반영, 실포화 아님)
- `adccheck`: **missing code 65527이 M07T/M07B에서 양야간 재현** (그 외 스택은 결손 없음)
- `biasdiag`: 저주파(0.0011 cpp) 성분 최대 355 ADU — bias 램프 구조 이상

**M07/M08 스트립의 video chain 이상**으로 종합 판정한다. CEU 전환 후 같은 위치에서
재발하는지가 CCD 귀속/전자부 귀속을 가르는 시험이 된다.

### 4.3 T칩 계열 (컨트롤러 2)

- RDNOISE 상승 클러스터: AMPID 51+ 에서 ~9 e⁻ (중앙값 7.0 e⁻ 대비 +2 e⁻; MAD 이상치 플래그)
- `biasdiag` 채널 상관행렬: T칩 블록에서 쌍차분 상관 0.3~0.4 — 같은 컨트롤러 공통모드 잡음
- 710에서 T칩 대규모 침수 → 이 야간 T칩의 `satshut` FULLWELL 10건(s_sat med 26.4k,
  fullwell −1.1k e⁻ 등 비물리)은 **오염 무효**로 처리한다

### 4.4 Bias 구조 (`biasdiag`) — 대체로 깨끗

| 항목 | 610 | 710 |
| --- | --- | --- |
| image − overscan | 0.08 ADU | 1.10 ADU |
| 시퀀스 내 drift | 3.0 ADU | 11.0 ADU |
| 고정패턴(FPN) | 0.22 ADU | 0.33 ADU |
| PSD 고정주파수 피크 | 14앰프 (0.443 cpp ×5, 0.388 cpp ×5, 진폭 0.4~2 ADU) | 15앰프 (0.388 cpp ×7 등) |

0.39/0.44 cycles/pixel의 소진폭 피크는 고정주파수 pickup 후보다 — Hz 환산은 픽셀 클록
확정 후(`f_Hz = f_cpp × f_pixclk`), CEU에서 재측정할 항목.

### 4.5 ADC 무결성 (`adccheck`) — 건강

stuck bit 0, DNL rms 중앙값 0.022(최대 0.055), missing code는 §4.2의 M07 65527 외에
710에서 T03B/T05B 각 1코드(bias 대역, 단일 야간)뿐. 구형 ADC 자체는 코드 레벨에서 문제 없음.

### 4.6 Full well 하한 (`satshut`)

램프가 포화에 못 미치므로(NOT_REACHED 60/50앰프) `fullwell_e`는 **하한**이다:
정상 앰프에서 **full well ≥ ~80 ke⁻** (610 med 80.1k, 710 med 80.4k; 램프 상단 46.6k ADU × gain 1.66).
e2v CCD290-99 기대치와 정합하며, 실측 확정은 타입 8(satPersist)로 한다.

## 5. 이 자료로 측정할 수 없었던 것 — 커버리지 한계와 사용 금지

| 항목 | 결과값 | 판정과 근거 |
| --- | --- | --- |
| **linearizer 계수** (`linearity_coeff_*.csv`) | LINMAX(1%) med 9.1k(610)/3.4k(710) ADU, NL_MAX 최대 195%(710) | **caldb 반영 금지.** REF-드리프트 정규화는 타입 6(매 스텝 기준노출 인터리브) 전제 — 이 캠페인은 레벨당 5장 블록 + 10 s repeat뿐이라 돔램프 드리프트가 비선형성으로 위장(aliasing)된다. 선형성 기준값은 기준선 CSV의 LIN_* 유지 |
| 셔터 Δt | med −93 ms(610)/−141 ms(710) | 비물리(음수 수십 ms) — 노출 블록 간 램프 준위 차이의 위장. 타입 9(0.1~2 s 인터리브) 필요. shading map(p-p ~7 ms)은 참고용 |
| persistence | τ med 0, A0 med 0 | 포화가 없어 무정보(모듈 정상 동작 확인만). 610의 N05B/N06B τ=478 s는 A0~1.9e30의 **퇴화 적합**(비물리) — 모듈에 A0 상한 가드 추가 권고 |
| 포화 원인 분류 | NOT_REACHED 60/50 | 램프 상단(물리 46.6k ADU)이 포화 미달. 타입 8 필요 |

## 6. 산출물과 활용 지침

| 산출물 | 위치 | 활용 |
| --- | --- | --- |
| PTC 진단 CSV/페이지 | `results/LEGACY-SSO-<야간>/diagnostics/` | gain/RN 교차검증 ✓, OSCAN_SLOPE 플래그 → CEU acceptance 목록 |
| bias 진단 + 채널 상관 | `.../biasdiag/` (`corr_matrix_*.csv` 포함) | CEU 비교 기준선(FPN·PSD·상관 블록) |
| ADC 점검 | `.../adccheck/` | M07 missing code 추적, CEU ADC 비교 기준선 |
| linearity 계수 | `.../linearity/linearity_coeff_*.csv` | ⛔ caldb 반영 금지 (§5) — 모듈 동작 기록으로만 보존 |
| 포화/셔터 | `.../satshut/` | full well 하한(§4.6)만 인용, 셔터/포화 분류값 인용 금지 |

야간당 49 MB(앰프별 PNG 64장×5모듈 포함). 저장소 반영 시 CSV+요약 PNG만 커밋하고
`amps/`는 제외하는 선택지가 있다 — 결정 대기.

## 7. 다음 단계

1. **타입 6~9 취득 캠페인 실행** (CEU 실기): §5의 네 항목이 모두 열린다 — 실행 순서는
   ptcRamp → ptcRepeat → shutSeq → **satPersist 마지막** ([ARCHON_LABTEST_V2 §5b](archon/ARCHON_LABTEST_V2.md))
2. CEU 인수 기준에 **CMRR(overscan slope)** 항목 추가 — §4.1의 구형 비정상 동작이 사라졌는지가 1차 판정
3. M07/M08·T칩 비정상 동작의 CEU 재발 여부 확인 (§4.2, §4.3 — CCD vs 전자부 귀속 분리)
4. `satshut` persistence 적합에 A0 상한/퇴화 가드 추가 (§5)

## 부록 A. 재현

```
# 카테고리 구성: QC selection(json) → bias/flats/refs/persist/short/long 심링크
# (persist = 마지막 플랫 이후 bias, short = 2.5/5/7.5 s, long = 12.5 s)
for <야간> in 20260610 20260710:
  OUT=cam_char/results/LEGACY-SSO-<야간>; CAMP=LEGACY-SSO-<야간>
  AC=cam_char/results/amp_characterization_$CAMP.csv
  python3 cam_char/kmt_cam_char/diagnostics.py --bias 'bias/*' --flats 'flats/*' -o $OUT --campaign $CAMP
  python3 cam_char/kmt_cam_char/biasdiag.py    --bias 'bias/*' --flats 'flats/*' -o $OUT --campaign $CAMP
  python3 cam_char/kmt_cam_char/adccheck.py    --bias 'bias/*' --flats 'flats/*' -o $OUT --campaign $CAMP
  python3 cam_char/kmt_cam_char/linearity.py   --flats 'flats/*' --refs 'refs/*' --bias 'bias/*' \
                                               -o $OUT --campaign $CAMP --ampchar $AC
  python3 cam_char/kmt_cam_char/satshut.py     --ramp 'flats/*' --persist 'persist/*' --short 'short/*' \
                                               --long 'long/*' -o $OUT --campaign $CAMP --ampchar $AC
```

## 개정 이력

| 버전 | 일자 | 내용 |
| --- | --- | --- |
| v1.0 | 2026-09-05 | 최초 발행 — 진단 5계열의 LEGACY-SSO 2야간 소급 적용, 모듈 실자료 검증 + SSO 심화 소견 |

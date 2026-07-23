# KMTNet CCD 카메라 전자부 교체 후 실험실 특성 측정 계획

## 1. 목적

본 문서는 KMTNet CCD 카메라의 전자부를 기존 시스템에서 Archon 컨트롤러 및 신규 월보드 기반 시스템으로 교체한 후, 실험실에서 수행해야 할 카메라 특성 측정 항목과 시험 방법을 정리한 것이다.

본 시험의 주요 목적은 다음과 같다.

- 64개 amplifier의 gain, read noise, bias 특성 측정
- 선형성, 포화 수준, dynamic range 확인
- dark current, DSNU, PRNU 측정
- cross-talk 및 long-tail artifact 검증
- serial/parallel charge transfer 성능 확인
- shutter timing 및 노출시간 정확도 검증
- 전자파 간섭 및 장시간 안정성 평가
- 기존 전자부와 신규 전자부의 성능 비교
- 최종 운용 clock, bias, CDS 및 readout 설정 결정

전자부 교체 전후 비교가 가능하도록, 가능한 경우 기존 전자부에서도 동일한 조건으로 시험 영상을 확보한다.

---

## 2. 시험 환경 및 기록 항목

모든 시험 영상에 대해 다음 조건을 기록한다.

- CCD 설정온도
- CCD 실제온도
- Archon 보드 온도
- 월보드 온도
- CCD bias voltage
- CCD clock voltage
- pixel readout rate
- CDS 및 sampling 설정
- 아날로그 gain 설정
- 디지털 gain 또는 scaling 설정
- ADC 입력 범위
- overscan 크기
- 노출시간
- 냉각 안정화 이후 경과시간
- 전원 재기동 이후 경과시간
- amplifier 번호
- amplifier readout 방향
- 사용 광원과 광원 설정값
- 시험 일시
- 시험 담당자
- 소프트웨어 및 configuration version

가능하면 각 설정 파일과 FITS 영상을 동일한 시험 디렉토리에 보관한다.

---

## 3. 시험 장비

권장 시험 장비는 다음과 같다.

- 안정화된 LED 광원
- integrating sphere
- 균일 flat-field 광원
- 광섬유 또는 pinhole 광원
- 특정 영역을 차단하거나 조사할 수 있는 mask
- calibrated photodiode
- 광원 모니터링용 photodiode
- oscilloscope
- multimeter
- 온도 센서
- 암실 또는 완전 차광 구조
- vacuum 및 cooling monitoring 장비

광원의 시간적 안정성은 PTC와 linearity 측정 정확도에 직접 영향을 주므로, 시험 중 별도의 photodiode로 광량을 모니터링하는 것이 좋다.

---

# 4. 영상 구조 및 amplifier mapping 확인

전자부 특성 측정에 앞서 FITS 영상 구조가 올바르게 생성되는지 확인한다.

## 4.1 촬영 방법

비대칭 문자, 숫자 또는 특정 모양이 포함된 mask를 CCD 앞에 설치하고 영상을 촬영한다.

## 4.2 확인 항목

- 64개 extension의 존재 여부
- extension 순서
- extension 크기
- amplifier 번호
- overscan 위치
- prescan 위치
- x 방향 flip
- y 방향 flip
- readout 방향
- CCD mosaic상의 물리적 위치
- extension 조립 후 전체 영상 방향
- saturated spot의 amplifier 위치
- FITS keyword
- `BITPIX`
- `BZERO`
- unsigned integer 처리
- `GAIN`
- `RDNOISE`
- `EXPTIME`
- `DATE-OBS`
- UTC 기록 정확성

---

# 5. Bias level과 read noise

## 5.1 목적

- amplifier별 bias level 측정
- amplifier별 read noise 측정
- fixed-pattern noise 확인
- row/column pattern 확인
- 시간에 따른 bias drift 확인
- 채널 간 correlated noise 확인

## 5.2 촬영 조건

빛을 완전히 차단하고 최소 노출시간으로 bias 영상을 촬영한다.

권장 촬영량:

- 냉각 안정 직후: 50장
- 정상 안정 상태: 100~200장
- 1~2시간 후: 50장
- 장시간 연속운용 후: 50장
- 전원 재기동 후: 50장

## 5.3 분석 방법

각 amplifier별로 다음 값을 측정한다.

- mean bias
- median bias
- bias RMS
- frame-to-frame bias variation
- overscan mean
- image area와 overscan의 차이
- row profile
- column profile
- 2D FFT
- amplifier 간 covariance

두 bias 영상의 차이를 이용한 read noise는 다음과 같다.

\[
RN_{\mathrm{ADU}}
=
\frac{\mathrm{std}(B_1-B_2)}{\sqrt{2}}
\]

전자 단위 read noise는 다음과 같다.

\[
RN_{e^-}
=
RN_{\mathrm{ADU}} \times g
\]

여기서 \(g\)는 \(e^-/\mathrm{ADU}\) 단위의 gain이다.

## 5.4 결과물

- 64개 amplifier별 bias level 표
- 64개 amplifier별 read noise 표
- bias histogram
- bias difference image
- row/column profile
- 2D FFT 또는 power spectrum
- 장시간 bias drift plot

---

# 6. Gain 측정: Photon Transfer Curve

## 6.1 목적

- amplifier별 system gain 측정
- gain 균일도 확인
- photon-noise 지배 영역 확인
- 신호 수준에 따른 gain 변화 확인
- read noise와 photon noise의 전환점 확인

## 6.2 촬영 조건

균일하고 안정적인 광원을 사용한다.

포화 수준의 약 1~90% 범위에서 15~25단계를 설정한다.

예시 신호 수준:

- 1%
- 2%
- 5%
- 10%
- 15%
- 20%
- 30%
- 40%
- 50%
- 60%
- 70%
- 80%
- 90%

각 단계에서 다음을 촬영한다.

- 동일 조건 flat 2장 이상
- 권장: 단계별 3~5쌍
- 중간중간 bias frame 촬영
- 광량 모니터링값 기록

광원 밝기를 직접 변경하기보다, 가능한 경우 광량을 고정하고 노출시간을 변경한다.

## 6.3 계산 방법

두 flat의 평균 신호는 다음과 같다.

\[
S
=
\frac{\langle F_1\rangle+\langle F_2\rangle}{2}
-
\langle B\rangle
\]

한 장의 flat에 해당하는 분산은 다음과 같다.

\[
V
=
\frac{
\mathrm{Var}(F_1-F_2)
-
\mathrm{Var}(B_1-B_2)
}{2}
\]

Photon-noise가 지배하는 선형 영역에서는 다음 관계가 성립한다.

\[
V=\frac{S}{g}
\]

분산 대 평균 그래프의 기울기를 \(m\)이라 하면,

\[
g=\frac{1}{m}
\]

이다.

## 6.4 주의사항

- 각 amplifier를 독립적으로 분석한다.
- amplifier 경계를 포함하지 않는 ROI를 사용한다.
- bad pixel과 cosmic ray를 제거한다.
- flat 한 장의 공간 분산만 사용하지 않는다.
- 저신호 영역은 read noise 영향 때문에 fitting에서 제외한다.
- 고신호 영역은 비선형성과 brighter-fatter effect 때문에 제외할 수 있다.
- 평균 신호와 분산의 관계가 직선인지 확인한다.
- fitted gain이 신호 수준에 따라 달라지는지 확인한다.

## 6.5 결과물

- amplifier별 PTC
- amplifier별 gain
- gain 평균과 표준편차
- amplifier 간 gain 차이
- fitting range
- fitting residual
- gain의 신호 의존성

---

# 7. Linearity 측정

## 7.1 목적

- CCD와 전자부의 선형 응답 범위 확인
- ADC saturation 여부 확인
- amplifier별 비선형성 측정
- 포화 직전 응답 변화 확인

## 7.2 촬영 조건

광원 밝기를 고정하고 노출시간만 변경한다.

예시 노출시간:

```text
1, 2, 3, 5, 10, 20, 30, 40, 60, 80, 100, 120초
```

각 노출시간에서 3~5장 촬영한다.

광원의 시간 변화를 확인하기 위해 동일한 기준 노출을 중간중간 반복한다.

예:

```text
10, 20, 10, 30, 10, 40, 10, 60초
```

## 7.3 분석 방법

저신호 및 중간신호 영역을 직선으로 fitting한다.

비선형성은 다음과 같이 계산한다.

\[
\mathrm{Nonlinearity}(\%)
=
100
\frac{S_{\mathrm{measured}}-S_{\mathrm{fit}}}
{S_{\mathrm{fit}}}
\]

## 7.4 결과물

- amplifier별 signal versus exposure time plot
- amplifier별 nonlinearity plot
- 0.5% 이내 선형 범위
- 1% 이내 선형 범위
- 포화 직전 최대 선형 신호
- amplifier 간 선형성 편차

---

# 8. 포화 수준과 full well

## 8.1 목적

- ADC saturation 확인
- 아날로그 회로 saturation 확인
- CCD full well 또는 유효 charge-handling limit 확인
- 포화 이후 blooming과 residual 확인

## 8.2 촬영 조건

다음과 같은 신호 수준으로 flat 또는 spot 영상을 촬영한다.

- 포화의 50%
- 70%
- 80%
- 90%
- 95%
- 100%
- 105%
- 110%

포화 영상을 촬영한 직후 bias 또는 dark 영상을 연속으로 촬영한다.

## 8.3 분석 항목

다음 세 가지를 구분해야 한다.

1. ADC saturation
2. analog front-end saturation
3. CCD full well

유효 full well은 다음과 같이 추정할 수 있다.

\[
Q_{\mathrm{FW}}
\simeq
S_{\mathrm{sat,ADU}} \times g
\]

단, ADC나 아날로그 회로가 먼저 포화되면 CCD 자체의 full well은 직접 측정되지 않는다.

## 8.4 결과물

- saturation ADU
- 최대 선형 ADU
- 최대 선형 전자 수
- 포화 전자 수
- blooming profile
- 포화 후 residual image
- recovery frame sequence

---

# 9. Dynamic range

Dynamic range는 최대 선형 신호와 read noise를 이용해 계산한다.

\[
DR
=
\frac{Q_{\mathrm{linear,max}}}{RN}
\]

비트 단위로 표현하면 다음과 같다.

\[
DR_{\mathrm{bit}}
=
\log_2
\left(
\frac{Q_{\mathrm{linear,max}}}{RN}
\right)
\]

ADC bit 수와 실제 dynamic range는 동일하지 않다.

## 결과물

- amplifier별 dynamic range
- amplifier별 effective bit depth
- 평균 dynamic range
- 기존 전자부 대비 변화

---

# 10. Dark current와 DSNU

## 10.1 목적

- 평균 dark current 측정
- DSNU 측정
- hot pixel과 hot column 확인
- amplifier glow 확인
- 온도에 따른 dark current 변화 확인

## 10.2 촬영 조건

완전 암조건에서 다음 영상을 촬영한다.

```text
Bias       20장
60초 dark  10장
300초 dark 10장
600초 dark 10장
```

가능하면 CCD 온도를 2~3단계로 변경하여 반복한다.

예:

```text
-100°C
-95°C
-90°C
```

## 10.3 계산 방법

노출시간이 \(t_1\), \(t_2\)인 dark 영상의 평균 차이를 이용한다.

\[
I_{\mathrm{dark}}
=
g
\frac{\langle D_2\rangle-\langle D_1\rangle}
{t_2-t_1}
\]

단위는 다음과 같다.

\[
e^-\,\mathrm{pixel}^{-1}\,\mathrm{s}^{-1}
\]

DSNU는 dark current의 픽셀별 공간 불균일성으로 계산한다.

## 10.4 결과물

- 평균 dark current
- dark current histogram
- DSNU
- hot pixel map
- hot column map
- amplifier glow image
- dark current versus temperature plot

---

# 11. PRNU와 flat-field 균일성

## 11.1 목적

- 픽셀별 감도 불균일성 측정
- amplifier 경계의 불연속 확인
- row/column fixed pattern 확인
- 채널별 상대 gain 차이 확인

## 11.2 촬영 조건

포화의 약 30~60% 수준에서 동일 조건 flat을 20장 이상 촬영한다.

## 11.3 분석 방법

- bias 제거
- flat normalization
- 여러 장을 median 또는 average combine
- 대규모 illumination gradient 제거
- bad pixel masking
- pixel-to-pixel RMS 계산

전자부만 교체한 경우 CCD 자체 PRNU는 크게 달라지지 않아야 한다. 차이가 크다면 gain normalization, signal processing 또는 영상 조립 문제를 의심한다.

## 11.4 결과물

- normalized master flat
- PRNU map
- amplifier별 median response
- amplifier 경계 profile
- row/column response pattern

---

# 12. Cross-talk 측정

## 12.1 목적

- amplifier 간 cross-talk 측정
- ADC 보드 내 channel coupling 확인
- 차동회로와 케이블 간 coupling 확인
- 포화 신호에서 발생하는 비선형 cross-talk 확인

## 12.2 시험 방법

작은 영역만 강하게 조사할 수 있는 광원을 사용한다.

예:

- LED와 pinhole
- 광섬유 spot
- 일부 영역만 개방한 mask
- 특정 amplifier에만 위치한 강한 spot

한 amplifier에 강한 신호를 인가하고 나머지 amplifier의 동일 좌표에서 ghost를 측정한다.

## 12.3 권장 신호 수준

- 포화의 20%
- 50%
- 80%
- 포화 직전
- 포화 상태

## 12.4 계산 방법

신호를 인가한 채널을 \(i\), 영향을 받는 채널을 \(j\)라 하면 다음과 같이 계산한다.

\[
C_{ij}
=
\frac{\Delta S_j}{S_i}
\]

64채널 시스템에서는 가능한 경우 64×64 cross-talk matrix를 생성한다.

## 12.5 확인 항목

- positive ghost
- negative ghost
- saturated cross-talk
- nonlinear cross-talk
- 동일 보드 내 cross-talk
- 보드 간 cross-talk
- 케이블 간 coupling
- 동일 pixel 좌표 ghost
- serial 방향 tail

## 12.6 결과물

- 64×64 cross-talk matrix
- aggressor-victim channel table
- cross-talk versus signal plot
- 포화 전후 ghost image
- 기존 전자부와 신규 전자부 비교

---

# 13. Long-tail 및 포화 후 artifact

## 13.1 목적

- 기존 전자부에서 나타난 long-tail 개선 여부 검증
- serial 및 parallel 방향 charge artifact 측정
- 포화 후 persistence 확인

## 13.2 촬영 순서

1. bias 또는 정상 flat
2. 강한 포화 spot
3. 포화 직후 bias
4. 포화 직후 dark
5. 추가 bias 또는 dark 여러 장

## 13.3 분석 항목

- serial 방향 tail
- parallel 방향 bleeding
- tail 길이
- tail 총전하
- 포화 신호 대비 tail 비율
- 포화 후 residual
- 다음 프레임까지 남는 persistence
- 기존 전자부 대비 변화

## 13.4 결과물

- 포화 spot image
- serial profile
- parallel profile
- tail ratio
- recovery sequence
- 교체 전후 비교 plot

---

# 14. Charge Transfer Efficiency

## 14.1 목적

- serial CTE 측정
- parallel CTE 측정
- clock voltage 및 clock timing 최적화
- 신호 수준에 따른 deferred charge 확인

## 14.2 EPER 촬영 조건

높은 신호의 flat을 촬영하고 overscan을 충분히 확보한다.

권장 신호 수준:

- 포화의 30%
- 포화의 60%
- 포화의 90%

권장 overscan:

- serial overscan 수십 pixel 이상
- 가능한 경우 parallel overscan 확보

## 14.3 계산 방법

Serial CTI는 개략적으로 다음과 같이 계산한다.

\[
CTI_{\mathrm{serial}}
\simeq
\frac{Q_{\mathrm{overscan}}}
{Q_{\mathrm{image}}N_{\mathrm{transfer}}}
\]

\[
CTE=1-CTI
\]

## 14.4 결과물

- serial CTE
- parallel CTE
- deferred charge profile
- 신호 수준에 따른 CTE
- clock 설정에 따른 CTE
- 기존 전자부 대비 변화

---

# 15. Shutter 및 노출시간 정확도

## 15.1 목적

- shutter open/close timing 확인
- 명령 노출시간과 실제 적분시간 비교
- 짧은 노출에서의 illumination pattern 확인
- FITS `EXPTIME` 정확도 확인

## 15.2 촬영 조건

균일한 광원에서 다음 노출시간으로 flat을 촬영한다.

```text
0.1, 0.2, 0.5, 1, 2, 5, 10, 30초
```

각 노출시간에서 5장 이상 촬영한다.

## 15.3 분석 방법

신호를 노출시간에 대해 fitting한다.

\[
S=R(t+\Delta t)
\]

여기서 \(R\)은 광원의 count rate이고, \(\Delta t\)는 shutter 및 trigger timing offset이다.

긴 기준 노출 flat으로 짧은 노출 flat을 정규화하여 위치별 shutter pattern을 측정한다.

## 15.4 결과물

- 실제 노출시간 offset
- shutter pattern map
- 위치별 유효 노출시간 차이
- 짧은 노출에서의 비선형성
- FITS 시간 keyword 검증 결과

---

# 16. 전자파 간섭 및 주변 장치 영향

## 16.1 목적

주변 장치와 전원계통이 bias 및 read noise에 미치는 영향을 확인한다.

## 16.2 시험 조건

Bias 또는 dark를 연속 촬영하면서 다음 장치를 하나씩 켜고 끈다.

- chiller
- vacuum pump
- shutter motor
- cooling fan
- telescope motor 또는 유사 부하
- network switch
- camera control PC
- switching power supply
- 실험실 LED 조명
- 주변 고전력 장치

각 조건에서 bias를 20장 이상 촬영한다.

## 16.3 분석 항목

- bias level 변화
- read noise 변화
- row/column periodic pattern
- 2D FFT
- 특정 주파수 pickup
- common-mode noise
- amplifier 간 correlated noise

## 16.4 결과물

- 장치별 bias/read noise 비교표
- noise spectrum
- on/off difference image
- pickup frequency
- 권장 grounding 및 shielding 조건

---

# 17. 온도 및 장시간 안정성

## 17.1 목적

- 밤 전체 운용 중 bias drift 확인
- gain drift 확인
- read noise drift 확인
- 온도 변화와 전자부 특성의 상관관계 확인
- 전원 재기동 후 재현성 확인

## 17.2 촬영 조건

정상 운용 조건에서 6~12시간 동안 다음 sequence를 반복한다.

```text
Bias 10장
중간 밝기 flat 2장
Dark 1장
```

20~30분 간격으로 반복한다.

## 17.3 기록 항목

- CCD 온도
- Archon 온도
- 월보드 온도
- 전원 전압
- bias level
- gain
- read noise
- dark level
- cooling duty cycle

## 17.4 결과물

- bias versus time
- gain versus time
- read noise versus time
- temperature versus time
- gain versus temperature
- bias versus temperature
- 재기동 전후 비교

---

# 18. Readout speed 및 CDS 설정 최적화

## 18.1 목적

- readout speed와 read noise의 균형 결정
- CDS 및 sampling 설정 최적화
- readout time 단축 효과 확인
- 설정에 따른 cross-talk 및 linearity 변화 확인

## 18.2 시험 방법

가능한 readout rate와 CDS 설정별로 다음 영상을 촬영한다.

- bias 20장 이상
- 중간 밝기 flat 10장 이상
- PTC 일부 신호 수준
- 포화 spot
- cross-talk spot

## 18.3 비교 항목

- total readout time
- gain
- read noise
- linearity
- saturation
- cross-talk
- long-tail
- board temperature
- power consumption
- 데이터 손상 여부

## 18.4 결과물

- 설정별 성능 비교표
- 최종 권장 readout 설정
- 최종 권장 CDS 설정
- 최종 clock/bias configuration

---

# 19. 실험실에서 직접 측정하기 어려운 항목

## 19.1 Photometric zero point

천문학적 photometric zero point는 다음을 모두 포함한다.

- 망원경 집광면적
- 광학계 투과율
- 필터 투과율
- CCD QE
- 대기 투과율
- 관측 및 측광 방법

따라서 일반적인 실험실 flat만으로 직접 측정할 수 없다.

실험실에서는 다음 값을 측정할 수 있다.

- system gain
- read noise
- electron 기준 responsivity
- 상대 wavelength response
- QE
- 광학 throughput

전자부 교체 전후 감도를 비교할 때는 ADU가 아니라 gain을 적용한 electron 단위 신호를 사용한다.

\[
N_e=N_{\mathrm{ADU}}\times g
\]

절대 QE 또는 responsivity 측정에는 다음 장비가 필요하다.

- calibrated photodiode
- monochromator
- integrating sphere
- 절대 광출력 calibration
- 동일 입사광 조건

---

# 20. 권장 최소 촬영 세트

| 시험 | 최소 권장 촬영량 |
|---|---:|
| 영상 구조 및 mapping | mask 영상 5장 이상 |
| Bias/read noise | 100~200장 |
| 장시간 bias 안정성 | 6시간 이상 |
| PTC flat | 15~25단계, 단계별 3쌍 |
| Linearity | 15단계 이상, 단계별 3장 |
| Saturation/full well | 8~10단계 |
| Dark current | 60/300/600초 각 10장 |
| PRNU | 동일 신호 flat 20장 이상 |
| Cross-talk | 64개 aggressor 채널 또는 대표 채널 전체 |
| Long-tail | 포화 spot 및 recovery sequence |
| CTE | 3개 신호 수준, 각 5장 |
| Shutter | 0.1~30초, 단계별 5장 |
| EMI 시험 | 장치 on/off 조건별 bias 20장 |
| 온도 안정성 | 6~12시간 |
| Readout 설정 비교 | 설정별 bias/flat 20장 이상 |

---

# 21. 권장 수행 순서

1. 영상 구조 및 amplifier mapping 확인
2. bias level 및 read noise 측정
3. PTC gain 측정
4. linearity 측정
5. saturation 및 full well 측정
6. dynamic range 계산
7. dark current 및 DSNU 측정
8. PRNU 및 flat-field 균일성 측정
9. cross-talk 측정
10. long-tail 및 포화 artifact 측정
11. CTE 측정
12. shutter 및 exposure timing 측정
13. EMI 및 주변 장치 영향 시험
14. 장시간 온도 및 성능 안정성 시험
15. readout speed 및 CDS 설정 최적화
16. 최종 설정에서 전체 핵심 시험 반복

---

# 22. 최종 산출물

최종적으로 다음 자료를 작성한다.

- 64개 amplifier별 gain 표
- 64개 amplifier별 read noise 표
- bias level 및 stability 표
- PTC plot
- linearity plot
- saturation 및 dynamic range 표
- dark current 및 DSNU map
- PRNU map
- bad pixel 및 hot pixel map
- 64×64 cross-talk matrix
- long-tail profile
- CTE 측정 결과
- shutter timing 결과
- EMI 시험 결과
- 장시간 안정성 plot
- readout/CDS 설정 비교표
- 기존 전자부와 신규 전자부 비교표
- 최종 권장 Archon configuration
- 최종 FITS header keyword 정의
- 최종 acceptance test report

---

# 23. 주요 성능 판단 항목

KMTNet CCD 카메라 전자부 교체의 핵심 판단 항목은 다음과 같다.

1. 64개 amplifier의 gain과 read noise가 목표 범위 안에 있는가?
2. amplifier 간 gain 편차를 안정적으로 보정할 수 있는가?
3. 기존 대비 cross-talk가 감소했는가?
4. 기존 long-tail artifact가 제거되거나 감소했는가?
5. 선형성과 dynamic range가 기존 시스템 이상인가?
6. 포화 신호 이후 residual 또는 persistence가 발생하지 않는가?
7. bias와 gain이 장시간 안정적으로 유지되는가?
8. 주변 장치에 의한 periodic noise나 pickup이 없는가?
9. 영상 extension 순서와 방향이 올바른가?
10. 실제 관측에 사용할 최종 readout 설정이 재현 가능한가?

---

# 24. 결론

실험실 시험에서 가장 중요한 결과는 다음 네 가지이다.

- 64개 amplifier별 gain, read noise 및 linearity
- 64×64 cross-talk matrix
- saturation 및 long-tail artifact 비교
- 장시간 bias 및 gain 안정성

이 시험 결과를 바탕으로 최종 Archon clock, bias, gain, CDS 및 readout 설정을 결정하고, 이후 실제 망원경에 설치한 뒤 twilight flat, stellar field, bright-star 및 장시간 관측 시험을 추가로 수행한다.

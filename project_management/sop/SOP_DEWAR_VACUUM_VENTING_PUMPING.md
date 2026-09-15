# KMTNet Dewar 진공 해제 및 펌핑 작업 정리

최종 갱신일: 2026-09-15

**기준 문서:** `Wall Board 현장 교체 절차 (Rev.7.1)`
**목적:** Wallboard 교체 과정에서 필요한 듀어 진공 해제(Venting), 재펌핑(Pump-down), 진공 관련 부품 및 현장 준비사항을 한 문서로 정리

이 SOP는 [`SOP_SITE_DEPLOYMENT.md`](SOP_SITE_DEPLOYMENT.md) 3단계("Wallboard 교체 / 진공 펌핑 / 냉각 시작")의 세부 절차서다. 진공/냉각 이상 발생 시 대응은 [`operations/RECOVERY_ROLLBACK_PLAN.md`](../operations/RECOVERY_ROLLBACK_PLAN.md) Recovery Level 3, 취급 일반 원칙은 [`operations/SAFETY_HANDLING_PLAN.md`](../operations/SAFETY_HANDLING_PLAN.md)을 따른다.

---

## 1. 진공 해제 전 준비 조건

진공 해제 전에 다음 조건을 확인한다.

1. 모든 CCD 냉각기 컴프레서를 정지한다.
2. 모든 냉각부 온도가 Brooks에서 규정한 최소 분리 온도 이상인지 확인한다.
3. 듀어 내부의 모든 온도가 **주변 이슬점(Dew Point)보다 높은지 확인**한다.
4. 듀어를 클린 부스 안으로 이동한다.
5. 듀어 카트에 접지선을 연결한다.
6. 진공 관련 케이블과 배관을 점검한다.
7. 벤팅에 사용할 배관, 밸브, 필터, 진공펌프 상태를 확인한다.

> **중요:** 듀어 내부 부품이 이슬점보다 낮은 상태에서 벤팅하면 내부 표면에 수분이 응축될 가능성이 있으므로 벤팅을 시작하지 않는다.

---

## 2. 듀어 진공 해제(Venting) 절차

### 2.1 기본 순서

1. **Throttle Valve를 완전히 닫는다.**
2. Bellows와 Vacuum Pump 사이의 Isolation Valve를 연다.
3. Vacuum Pump를 가동한다.
4. Dewar Valve와 Throttle Valve 사이의 배관을 먼저 배기한다.
5. 해당 배관의 압력을 **현재 Dewar 압력보다 약 한 자릿수(1 decade) 낮은 수준**까지 낮춘다.
6. Dewar Valve를 천천히 연다.
7. Bellows와 Pump 사이의 Isolation Valve를 닫는다.
8. Vacuum Pump를 정지한다.
9. Vacuum Pump는 제조사에서 규정한 자체 vent 절차에 따라 진공을 해제한다.
10. Throttle Valve를 매우 천천히 열어 Vent Gas를 듀어 내부로 유입시킨다.
11. 듀어 내부 압력이 대기압에 도달할 때까지 천천히 벤팅한다.
12. 대기압에 도달하면:
    - Throttle Valve를 닫는다.
    - Dewar Valve를 닫는다.

---

## 3. 권장 Venting 구성

기본 구성은 다음과 같이 정리할 수 있다.

```text
                        +--> Baffle Filter
                        |        |
                        |        v
Dewar --> Dewar Valve --> KF16 Tee --> Throttle / Needle Valve
                        |                       |
                        |                       v
                        |                KF16-to-1/4" Adapter
                        |                       |
                        |                       v
                        |                  Vent Gas Line
                        |
                        +--> Bellows --> Isolation Valve --> Vacuum Pump
```

### Vent Gas 권장 구성

```text
Dry N2 Source
    |
Pressure Regulator
    |
Particle Filter
    |
Shut-off Valve
    |
1/4" Clean Tube
    |
KF16-to-1/4" Adapter
    |
Throttle / Needle Valve
    |
Baffle Filter
    |
KF16 Tee
    |
Dewar
```

---

## 4. 진공 해제 시 핵심 주의사항

### 4.1 듀어 내부 오염 방지

- 가능한 경우 일반 실내 공기보다 **Dry N2**를 사용한다.
- Vent Gas Line 내부는 깨끗하고 건조하게 유지한다.
- 사용하지 않는 KF 배관과 포트는 즉시 Blank Cap으로 막는다.
- O-ring 및 sealing surface를 맨손으로 만지지 않는다.
- Vacuum-side 부품은 lint-free wipe와 승인된 세척제를 사용하여 청소한다.

### 4.2 급격한 Vent 방지

Throttle Valve는 반드시 아주 천천히 연다.

급격한 압력 상승은 다음 문제를 일으킬 수 있다.

- 내부 부품에 대한 순간적인 압력 하중
- 미세 입자 이동
- 오염물 유입
- 내부 구조물에 대한 불필요한 기계적 충격

필요하면 Needle Valve 이외에 **Fixed Restrictor / Orifice**를 추가하여 작업자 실수에 의한 급격한 벤팅을 방지할 수 있다.

---

# 5. 재조립 후 진공 펌핑 절차

## 5.1 Pump-down 전 점검

재조립 전에 다음을 확인한다.

1. Rear Cylinder의 Vacuum Valve 내부를 청소한다.
2. Rear Cylinder 위/아래 flange의 O-ring을 제거한다.
3. O-ring groove를 점검하고 청소한다.
4. 세척된 O-ring을 준비한다.
5. 필요한 위치에 규정된 Vacuum Grease를 소량 도포한다.
6. Rear Cylinder와 Rear Cover를 재조립한다.
7. 모든 flange 및 sealing surface가 정상적으로 결합되었는지 확인한다.

---

## 5.2 사용하는 Dewar O-ring

| 위치/용도 | 규격 | 필요 수량 |
|---|---|---:|
| Wallboard / Front Cylinder 관련 | AN-280-VITON | 1 |
| Rear Cylinder 하부 | AN-280-VITON | 1 |
| Rear Cylinder 상부 / Rear Cover | AN-279-VITON | 1 |
| **작업용 기본 필요량** |  | **AN-280 × 2, AN-279 × 1** |

현장 작업에서는 각각 Spare를 추가 준비하는 것을 권장한다.

---

## 5.3 Dewar Pump-down 및 냉각 절차

1. Vacuum Pump로 Dewar 배기를 시작한다.
2. Pump-down 초기 단계에서 **Leakage 여부를 확인한다.**
3. L4 O-ring의 정상 압착 여부를 함께 점검한다.
4. 진공에 문제가 없으면 정해진 절차에 따라 Dewar를 Telescope에 장착한다.
   - SSO 작업에서는 Dewar Cart에서 관련 작업을 수행할 수 있다.
5. Cooler Line 6개를 다시 연결한다.
6. Vacuum Pump로 계속 배기한다.
7. 규정된 적정 진공도까지 Pump-down을 계속한다.
8. PT30 #1 Compressor를 기동한다.
9. 약 20초 기다린다.
10. PT30 #2 Compressor를 기동한다.
11. 다음 조건 중 하나에 도달할 때까지 기다린다.
    - PT30 온도 약 **-80 °C**
    - 또는 CCD 온도 약 **+5 °C**
12. PT13 Compressor를 기동한다.
13. Dewar Vacuum Valve를 닫는다.
14. 이후 Dewar 내부의 냉각 및 진공 상태를 계속 확인한다.

---

# 6. 진공 해제 및 펌핑 작업용 부품 목록

아래는 **Dewar 1대 작업용 Vacuum/Venting Kit 1세트** 기준이다.

## 6.1 절차서에 명시된 주요 장비

| 분류 | 품목 | 제조사 / 모델 | 수량 | 비고 |
|---|---|---|---:|---|
| Pump | Vacuum Pumping Station | Pfeiffer Vacuum / **HiCube 80 Neo**, PM Q100 011 00 | 1 | TMP: HiPace 80 Neo, Backing: MVP 030-3 |
| Pump | Pump Venting Valve | Pfeiffer Vacuum / Venting Valve 24 VDC, G1/8 | 1 | Pump 자체 vent용 |
| Vacuum fitting | KF Tee Equal | MK / KF16 90° Tee-Equal, SUS304 | 1 | Pump/Vent line 분기 |
| Filter | Vacuum Gauge Baffle Filter | Fredericks / Televac **2-2121-KF16** | 1 | Vent 시 particle 저감 |
| Flow control | Vacuum Throttling Valve | SENFIY / KF16-KF16 Flow Control Needle Valve | 1 | 304/316L Stainless Steel |
| Adapter | KF-to-Tube Fitting | Hohwon / KF16 to 1/4" Tube-end | 1 | SUS304 |

---

## 6.2 진공 배관 및 연결 부품

| 품목 | 규격 | 권장 수량 | 비고 |
|---|---|---:|---|
| Flexible Bellows | KF16 | 1 | Dewar-Manifold-Pump 연결 |
| Pump Isolation Valve | KF16 | 1 | Bellows와 Pump 사이 |
| KF16 Clamp | KF16 | 연결부 수량 + Spare 2~4 | 현장 Spare 필수 |
| KF16 Centering Ring + O-ring | KF16 | 연결부 수량 + Spare 2~4 | 손상/오염 대비 |
| KF16 Blank Flange / Cap | KF16 | 2~4 | 분리된 Vacuum Port 밀봉 |
| 1/4" Clean Gas Tube | 1/4" | 필요 길이 | Vent Gas Line |
| Tube Plug / Cap | 1/4" | 2 이상 | 보관 중 오염 방지 |

---

## 6.3 Dewar sealing 부품

| 품목 | 규격 | 기본 수량 | 권장 준비량 |
|---|---|---:|---:|
| Viton O-ring | AN-280-VITON | 2 | 3~4 |
| Viton O-ring | AN-279-VITON | 1 | 2 |
| Vacuum Grease | 기존 승인 규격 | 1 | 1 |
| Kapton Tape | Vacuum 작업용 | 1 roll | 1~2 roll |

---

# 7. 추가 권장 Vent Gas 관련 부품

> 다음 항목은 Rev.7.1 절차서에 명확하게 규정되어 있지는 않지만, 내부 오염 방지 및 반복 가능한 현장 작업을 위해 추가를 권장한다.

| 품목 | 권장도 | 용도 |
|---|---|---|
| **Dry N2 Cylinder / Supply** | 강력 권장 | 습기 및 먼지가 포함된 ambient air 유입 방지 |
| N2 Pressure Regulator | 필수 권장 | 공급 압력 제한 |
| Fine Particle Inline Filter | 권장 | Gas line particle 제거 |
| Gas Shut-off Valve | 권장 | Gas 공급 완전 차단 |
| Fixed Flow Restrictor / Orifice | 선택 권장 | Throttle Valve 오조작에 대한 fail-safe |
| Clean 1/4" Tube | 권장 | Regulator와 Dewar vent system 연결 |

---

# 8. 계측 및 점검 장비

| 품목 | 필요성 | 용도 |
|---|---|---|
| Dewar Vacuum Gauge | 필수 | Dewar pressure 확인 |
| Vacuum Gauge Controller | 필수 | Pump-down/Venting monitoring |
| Pump Pressure Gauge | 필수 | TMP/Backing pump 상태 확인 |
| Dew Point / RH Meter | 강력 권장 | Vent 시작 전 Dew Point 조건 확인 |
| Temperature Monitor | 필수 | CCD, DMP, PT30/PT13 온도 확인 |
| He Leak Detector | 가능하면 권장 | 정밀 누설 검사 |
| Portable Vacuum Gauge | 권장 | Main gauge와 독립적인 교차 확인 |

---

# 9. 청소 및 작업 소모품

- Powder-free clean gloves
- Lint-free wipes
- 승인된 세척용 IPA 또는 기존 Vacuum Cleaning Solvent
- Clean swab
- Vacuum grease
- Kapton tape
- Clean polyethylene bag
- KF16 blank cap
- 1/4" tube cap
- Clean aluminum foil
- Particle-free storage container

---

# 10. 현장 Spare 권장 목록

장거리 해외 현장 작업에서는 작은 Vacuum 부품 하나의 손실이나 손상으로 전체 작업이 중단될 수 있다.

따라서 최소 다음 Spare를 별도 보관하는 것을 권장한다.

- KF16 Clamp: **4개 이상**
- KF16 Centering Ring/O-ring: **4세트 이상**
- KF16 Blank Cap: **2개 이상**
- AN-280-VITON: 기본 필요량 외 **2개 이상**
- AN-279-VITON: 기본 필요량 외 **1개 이상**
- 1/4" Tube Fitting: **1개 Spare**
- Needle Valve: 가능하면 **1개 Spare**
- Baffle Filter: 가능하면 **1개 Spare**
- Vacuum Gauge 관련 Cable: **1개 Spare**
- Vacuum Valve용 O-ring / seal: 가능한 규격별 Spare
- Clean Gas Tube: 여유 길이 확보

---

# 11. SOP에서 추가 확정이 필요한 항목

현재 Rev.7.1에서는 아래 값이 정량적으로 명확하지 않다.

## 11.1 Vent Gas 종류

다음 중 하나로 명확히 규정할 필요가 있다.

- Dry N2
- Clean Dry Air
- 기타 승인 Gas

**권장:** Dry N2

---

## 11.2 Vent Rate

현재 절차는 "Throttle Valve를 천천히 연다"고 되어 있으나 정량 기준이 없다.

다음 중 하나의 기준을 설정하는 것이 좋다.

- Pressure rise rate
- 특정 압력 구간별 최소 시간
- Vacuum → Atmospheric Pressure까지의 최소 총 Vent 시간

---

## 11.3 TMP 허용 Inlet Pressure

현재 절차에는 대략적으로

> "허용 입구 압력 이하에서만 TMP까지 연다."

는 개념은 있으나 구체적인 압력 값이 없다.

HiCube 80 Neo / HiPace 80 Neo 제조사 기준과 실제 KMTNet 배관 구성을 확인하여 수치를 명시해야 한다.

---

## 11.4 Pump-down 완료 기준

현재 절차에서는 **"적정 진공도"**라고만 되어 있다.

다음을 수치로 정의하는 것이 좋다.

```text
Pump-down acceptance pressure = __________ mbar / Torr
```

가능하면 다음도 함께 기록한다.

```text
Pump start time       = __________
Pressure after 1 hr   = __________
Pressure after 2 hr   = __________
Final pressure        = __________
```

---

## 11.5 Leak Acceptance Criterion

누설 검사 방법과 합격 기준을 정해야 한다.

예:

```text
Method:
[ ] Pressure Rise Test
[ ] Helium Leak Test

Acceptance:
Pressure rise = __________________
He leak rate  = __________________
```

---

# 12. 현장 작업 체크리스트

## A. Venting 전

- [ ] 모든 Compressor OFF
- [ ] CCD/DMP/PT 온도 확인
- [ ] 모든 Dewar 내부 온도 > Dew Point
- [ ] Clean Booth 정상
- [ ] Dewar Cart Grounding 완료
- [ ] Vacuum Pump 준비
- [ ] Bellows 준비
- [ ] KF16 Tee 준비
- [ ] Baffle Filter 준비
- [ ] Throttle Valve 준비
- [ ] KF16 Clamp/Centering Ring 확인
- [ ] Vent Gas 준비
- [ ] Gas Regulator 확인
- [ ] Gas Line 청결 확인
- [ ] Vacuum Gauge 정상
- [ ] Spare Vacuum Parts 확인

## B. Venting

- [ ] Throttle Valve CLOSED
- [ ] Pump Isolation Valve OPEN
- [ ] Vacuum Pump ON
- [ ] Vent Manifold 선배기
- [ ] Manifold Pressure 확인
- [ ] Dewar Valve 천천히 OPEN
- [ ] Pump Isolation Valve CLOSED
- [ ] Vacuum Pump OFF
- [ ] Pump 자체 Vent 완료
- [ ] Throttle Valve 매우 천천히 OPEN
- [ ] Dewar Pressure 상승 상태 모니터링
- [ ] Atmospheric Pressure 도달 확인
- [ ] Throttle Valve CLOSED
- [ ] Dewar Valve CLOSED

## C. 재조립 후 Pump-down

- [ ] Vacuum Valve 내부 청소
- [ ] O-ring Groove 청소
- [ ] AN-280 O-ring 설치
- [ ] AN-279 O-ring 설치
- [ ] Vacuum Grease 상태 확인
- [ ] Rear Cylinder 체결 확인
- [ ] Rear Cover 체결 확인
- [ ] Vacuum Pump 연결
- [ ] Pump-down 시작
- [ ] 초기 Leakage 확인
- [ ] L4 O-ring 압착 상태 확인
- [ ] Pressure 기록
- [ ] Cooler Line 6개 연결
- [ ] 목표 진공도 도달 확인
- [ ] PT30 #1 ON
- [ ] 20초 대기
- [ ] PT30 #2 ON
- [ ] PT30 -80 °C 또는 CCD +5 °C 확인
- [ ] PT13 ON
- [ ] Dewar Vacuum Valve CLOSED
- [ ] 최종 Pressure / Temperature 기록

---

# 13. 현장용 Vacuum Kit 구성 권장

가능하면 진공 작업 부품을 일반 공구와 분리하여 하나의 전용 박스로 관리한다.

```text
KMTNet Dewar Vacuum/Venting Kit
|
+-- Vacuum Pump
+-- KF16 Bellows
+-- KF16 Tee
+-- Isolation Valve
+-- Baffle Filter
+-- Needle / Throttle Valve
+-- KF16-to-1/4" Adapter
+-- 1/4" Clean Tube
+-- KF16 Clamp Spares
+-- KF16 Centering Ring Spares
+-- KF16 Blank Caps
+-- AN-280 O-ring Spares
+-- AN-279 O-ring Spares
+-- Vacuum Grease
+-- Dry N2 Regulator
+-- Particle Filter
+-- Dew Point Meter
+-- Vacuum Gauge / Cable
+-- Cleaning Kit
+-- Clean Gloves
+-- Kapton Tape
```

SSO, CTIO, SAAO에서 동일한 구성을 사용하면 현장별 작업 방법을 표준화하고 부품 누락 가능성을 줄일 수 있다.

---

## 문서 기준과 추가 권고의 구분

### Rev.7.1 절차서에 명시된 내용

- HiCube 80 Neo Pumping Station
- Pfeiffer 24 VDC Pump Venting Valve
- KF16 Tee
- Televac 2-2121-KF16 Baffle Filter
- KF16-KF16 Flow Control Needle Valve
- KF16-to-1/4" Tube Fitting
- Dewar Venting 순서
- AN-280 / AN-279 Viton O-ring
- Pump-down 및 냉각 순서
- Leakage 확인
- PT30/PT13 냉각 순서

### 본 정리에서 추가 권고한 사항

- Dry N2 사용
- N2 Pressure Regulator
- Particle Filter
- Fixed Restrictor/Orifice
- KF16 Clamp 및 Centering Ring Spare
- Dew Point Meter
- Leak Acceptance Criterion
- Pump-down Acceptance Pressure
- 정량적 Vent Rate
- 전용 Vacuum/Venting Kit 구성

이 추가 항목들은 Rev.7.1 원문에 확정된 사양으로 제시된 내용이 아니라, 현장 작업의 안전성·청정도·재현성 확보를 위한 권고사항이다.

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| 현장 배포 절차 (3단계: Wallboard 교체/진공펌핑/냉각) | `SOP_SITE_DEPLOYMENT.md` |
| Recovery/Rollback (Level 3: 진공/냉각 문제) | `../operations/RECOVERY_ROLLBACK_PLAN.md` |
| 안전/취급 일반 원칙 | `../operations/SAFETY_HANDLING_PLAN.md` |
| 물류(Vacuum Kit 부품 추적) | `../logistics/EQUIPMENT_TRACKER.md`, `../logistics/LOGISTICS_PLAN.md` |

## 개정 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-09-15 | Wall Board 현장 교체 절차 Rev.7.1 기준 정리본을 SOP로 편입 (원문 그대로, 관련 문서 링크만 추가) |

# Tom O'Brien 전문가 자문 질문 목록 (SSO Wallboard 교체)

최종 갱신일: 2026-08-31  
연계: `SITE_PLAN.md`(SSO 일정) · `../../planning/ACTION_REGISTER.md` ACT-007 · 저장소 전수 조사 기반(48건 후보 → 26건 병합)

## 0. 규모 산정 (자문 패키지 ≈ USD 20,000 기준)

| 항목 | 값 |
| --- | --- |
| 실자문 시간 | 3~4 h/day × 7일 = **21~28시간** |
| 질문 구성 | **사전 서면 5건(WQ) + 현장 21건(TQ)** — 현장 세션당 45~60분 심층 토의 |
| 시간당 자문 가치 | ≈ $700~950 → 모든 질문은 "팀이 스스로 답할 수 없는 것"만: 원 설계 의도, as-built 값, 고장 이력, 안전 한계 |
| 답변 형식 | 구두 토의 + **서면 값/문서**(전압표·토크값·이력 기록)를 기본으로 요청. 각 항목에 "기대 산출물" 명시 |

우선순위: **P0** = 교체작업 차단·하드웨어 손상 위험 / **P1** = 품질·일정 / **P2** = 이력·참고.

> ⚠️ **일정 플래그 (팀 내부 조치 2건)** — 조사 중 발견:
> 1. **SSO 일정에 냉각기 off 단계가 없음.** CTIO(11-13)·SAAO(12-08)는 도착 전 냉각기 off를 명시했지만 SSO는 10-22 제거 전 off/warm-up 행이 없다 → WQ-1 답변(warm-up 소요시간) 확인 후 `SITE_PLAN.md`에 반영 필요.
> 2. **WQ-2(스페어 목록)는 9월 초 항공 출고 전 마감** — 톰 도착(10-18)을 기다리면 늦는다. 서면 질의를 즉시 발송할 것.

---

## Part A — 사전 서면 질의 (WQ: 출장 전 이메일, 5건)

### WQ-1. [P0] 냉각기 정지·warm-up 기준 (제거 전 필수값)
> The SSO plan removes the camera on Oct 22. How many hours/days before removal must the PCC cooler be shut down, and what internal (cold-plate / CCD) temperature must be reached before the dewar can be safely moved or vented? Should we ask the site staff to switch the cooler off before the team arrives on Oct 20?

- 근거: SSO `SITE_PLAN.md`에 냉각기 off 단계 부재 (CTIO/SAAO엔 있음)
- 기대 산출물: warm-up 소요시간, 안전 취급 온도 기준 → SITE_PLAN 반영

### WQ-2. [P1·시급] 고장 이력 기반 필수 스페어·공구 목록 (9월 항공출고 전 마감)
> Based on the original build and 12+ years of failure history, which spares must be in the air freight for the wallboard swap: exact O-ring part numbers/sizes for the wallboard flange and feedthroughs, hermetic connector spares, temperature sensors/heaters, and any special tools or jigs the team is likely to be missing?

- 근거: `EQUIPMENT_TRACKER.md` EQ-006/007 항공분 잔여, 9/1 종합검토 "항공 출고 목록 반영 마감"
- 기대 산출물: 품번 수준 must-carry 목록 → 항공 출고분 반영

### WQ-3. [P0] As-built CCD 전압표·절대한계·전원 시퀀스 (Archon 첫 POWERON 전)
> Can you provide the as-built OSU voltage table at the CCD pins — OD, RD, OG, substrate, parallel/serial clock rails per science chip M/K/N/T and for the guide CCD47-20s — the absolute do-not-exceed limits, any per-chip/per-amp trims, and the required power-on/off sequencing, so the Archon configuration can be cross-checked before first power-up of the flight CCDs? (Our lab campaign swept OD 29/30/31 V and the final set is still open; STA reviews the Archon config only on paper.)

- 근거: `DECISION_LOG.md` D-005 (VOLTINFO placeholder), cam_char 실험 셋업 코드(OD 스윕 미확정)
- 기대 산출물: 서면 전압표 + 한계값 + 시퀀스 → ACF 교차검증, `VOLTINFO` 기준

### WQ-4. [P0/P1] 칩별 수락시험 기록·결함 이력 (미사용 8출력 포함)
> Do your original acceptance-test records survive for the SSO focal plane (e2v CCD290-99 chips M/K/N/T): per-amplifier gain, read noise, full well, linearity — including the 8 outputs per chip the legacy 32-amp electronics never used — and the known cosmetic defects, hot columns, traps, or anomalous bias/dark patterns? Can you bring or reconstruct these reports so we can separate pre-existing artifacts from swap-induced damage before the Oct 29 GO/NOGO? Also: what full-well value should we design the Archon analog gain around (legacy saturation 62–64k ADU at 1.67–1.88 e-/ADU)?

- 근거: `SCIENCE_VERIFICATION_PLAN.md` 합격기준이 "기존 대비"인데 신뢰할 per-amp 기준값 부재; legacy 헤더 gain은 낡음(`cam_char` baseline 보고서); 64-amp 전환으로 미검증 8출력/칩 활성화
- 기대 산출물: OSU/e2v 시험 보고서 (지참 요청) → GO/NOGO 판정 기준선

### WQ-5. [P1] 탈거·재조립·진공 SOP 서면 사전검토
> We will send you the draft removal / reassembly / vacuum SOPs 2–3 weeks before your arrival. Please review them in writing against the original assembly order, torque values, and protection steps, and flag anything that contradicts the as-built design — we will then walk them through with you on Oct 20–21 before the removal starts.

- 근거: 리허설 수정사항 SOP 반영 진행 중(9/1 회의), punch list §4.2 SOP open
- 기대 산출물: 서면 검토의견 → SOP 확정판

---

## Part B — 현장 자문 (TQ: 작업 연동, 10-20~26)

### 준비·워크스루 (10-20~21)

**TQ-1. [P0] 카메라 리깅: 인양점·중량·CG·자세 제약·분리 순서**
> For the Oct 22 removal: what are the approved lifting points and fixtures for the camera, its as-built weight and CG, any orientation constraints, and the required disconnect order (cryo lines, signal cables, purge lines)? What went wrong or nearly wrong during the original installations?

- 기대 산출물: 리깅 도해·순서 확정 → 탈거 SOP 최종화

**TQ-2. [P1] 더미 HE박스 질량·CG 허용오차, 장착 특이사항**
> What are the as-built mass and CG of the original HE box relative to its telescope mounting interface, and within what tolerance must the dummy match them? Any mounting quirks (shim stack, strain reliefs, torque values) to replicate on Oct 22 (dummy) and Oct 30 (real box)?

**TQ-3. [P2] 클린부스 요구조건: 청정도·습도·개방 허용시간**
> What cleanliness class and humidity did the original dewar assembly require, what is the maximum time the dewar can stay open during the swap, and are extra precautions needed (dry-N2 purge into the open dewar, focal-plane covers)?

### 제거일 (10-22)

**TQ-4. [P0] CCD 보호: 월보드 분리 시 shorting plug·접지 스트랩·커넥터 취급**
> Once the OSU wallboard is disconnected, do the CCD signal/bias lines at the dewar feedthroughs need shorting plugs or grounding straps? Which hermetic connectors or internal flex cables are fragile or have a failure history, and is there a mandatory connect/disconnect order?

**TQ-5. [P0] 셔터 TTL 라인 전기 규격·인터록**
> The HE box drives the focal-plane shutter with a TTL line (HIGH = start open, LOW = start close; no software shutter command, no open-confirmation path). After the HE-box modification: which connector/pin carries this line, what are its exact electrical characteristics (polarity, voltage/current, edge-vs-level semantics, isolation), and what interlocks must the new driver respect — in particular, is asserting HIGH during the blade RELOADING state dangerous for the dual-blade mechanism (cycle ≈ open 5 s + close 5 s + reload ~5.7 s)?

- 근거: `ics_sim/DevNote.md` §9.2, `TCSAgent/tcsagent_report.md` — 저장소 어디에도 전기 규격 없음
- 기대 산출물: 핀아웃·전기규격·금지조건 서면 → 신규 셔터 드라이버 설계 입력

### 교체·진공·냉각일 (10-23) — 핵심 집중 구간

**TQ-6. [P0] O-ring/씰: 교체 대상·규격·토크·리크 판정 기준**
> Which O-rings/seals must be replaced versus safely reusable when the wallboard comes off, what material/size/grease spec applies, what bolt torque and tightening pattern does the wallboard flange need, and what leak-test acceptance criterion (rate-of-rise or He leak rate) must be met before starting cooldown?

- 근거: RISK_REGISTER R5(진공 형성 실패) Open — 기대 산출물: 수치 기준 → R5 완화

**TQ-7. [P0] 진공 문턱값·냉각 속도 한계**
> What chamber pressure and minimum pumping time are required before switching on the PCC, what maximum cooldown rate protects the CCD mosaic and internal bonds, and where should cryopumping (charcoal/getter) take over from the external pump? Is same-day pump-down + cooldown (our Oct 23 plan) consistent with original practice?

**TQ-8. [P0] 접지 토폴로지 + 원 월보드 채널별 보호/필터 회로**
> What is the original grounding topology between dewar, wallboard, HE box, and telescope (single-point ground location, shield terminations, intentional chassis bonds)? And per video/clock/bias channel, what filtering, series resistance, and protection networks did the original wallboard contain that the new Production Wallboard must reproduce to keep the legacy noise floor and protect the CCDs?

- 기대 산출물: 접지 다이어그램 스케치 + 채널 회로 요약 → 설치 시 그대로 재현

**TQ-9. [P0] 온도제어 루프: RTD·히터 위치, 저항/최대전력, 설정점·램프**
> Which physical sensor did the legacy CCDTEMP come from, where exactly are the RTDs and heater elements on the cold plate, what are the heater resistances and maximum safe drive power, and what setpoint, gains, and ramp limits did the original loop use for −100 °C operation that the new heater controller must reproduce during the first cooldown?

### 셋업·첫 영상 (10-24~26)

**TQ-10. [P1] 3× Archon 개조 HE박스 열·EMI 마진 검토**
> Please review the modified HE box against your original design: what heat load was the enclosure designed to reject vs 3× Archon dissipation, is the original cooling path still adequate, and does the modification break the EMI shielding or grounding continuity?

**TQ-11. [P1] 칩 장착 방향 확정 (READDIR/K·N 180° 회전/채널 맵)**
> In the as-built focal plane, are the K and N dies mounted rotated 180° relative to M and T? Per chip, toward which physical edge do the TOP-half outputs clock charge, and does CCD output OS n map one-to-one to our channel n at each hermetic connector with no swaps in the internal flex? Why did the legacy software treat M/T and K/N as different flip groups — die mounting, wiring, or software convention?

- 근거: `raw_fits_spec` v1.9 OI-17 잔여·OI-9 폐기, READDIR placeholder (BACKLOG KMT-002 P0)
- 기대 산출물: 칩별 방향 확정 → 온스카이 없이 READDIR/CHMAP 확정, mask 시험은 검증으로 전환

**TQ-12. [P1] ERASE 사이클(7.24 s)의 실체와 Archon ACF 재현 필요성**
> Every legacy exposure ran a 7.24-second ERASE before shutter open. What did it do electrically (number of full-frame flushes, any erase-gate/substrate manipulation, why 7.24 s), do these CCDs show persistence that requires it, and is an equivalent pre-exposure sequence needed in the Archon ACF beyond continuous idle flushing?

**TQ-13. [P1] 레거시 영상 병리 계보 ①: overscan 침수·long-tail의 발생단**
> Legacy data show signal-dependent overscan shifts (up to +1655 ADU at 50k signal on some SAAO amps) and a long-tail artifact after saturated sources — both are our headline new-vs-old GO/NOGO criteria. Which stage of your video chain causes each (baseline restore / AC-coupling droop / CDS recovery vs CCD serial register), and should we expect them to disappear completely with the Archon chain?

- 기대 산출물: "사라져야 정상 / 남는 게 정상" 판정 기준 → GO/NOGO 오판 방지

**TQ-14. [P2] 레거시 영상 병리 계보 ②: amp 경계 edge-column·하늘수준 overscan 칩**
> Is the fixed-pattern edge column at the 1152-column amplifier boundaries intrinsic to the CCD or an OSU-electronics artifact? And in legacy CTIO data some frames show an entire chip's X overscan at sky level instead of bias (chip M on some exposures, T on others) — was this a known artifact, and will it persist with Archon?

**TQ-15. [P1] Crosstalk 커플링 경로와 보정 보류 판단 검증**
> Inside the dewar, how are the four science chips' video/clock/bias lines routed and shielded relative to each other, which amplifier pairs did you observe or design against for crosstalk, and at what level (1e-4? 1e-5)? We have deferred a 64×64 crosstalk matrix as insignificant — is that consistent with your data, given detector-internal coupling survives the electronics swap? Also: the legacy guide loop gated guide readout to avoid science-readout crosstalk (>15 s remaining rule) — what was the physical coupling path, and does it survive the swap?

- 근거: BACKLOG KMT-003 보류 결정(2026-08-29), `gmon/DESIGN.md` §10-7
- 기대 산출물: 보류 결정 확정 or 재검토 + 신규 ICS 게이팅 규칙 필요 여부

**TQ-16. [P1] 가이드 CCD47-20 기하·운용 모드**
> For the four guide CCD47-20s: which physical chip sits at sky N/S/E/W, what is each chip's mounting rotation (our header draft says IMGROT='270,180,90,0' for N,E,S,W [TBC]; gmon provisionally uses n,s,e,w), where are the two output amps per chip, and did the original system run them frame-transfer with no shutter (is the storage region physically masked — is a vertical smear ramp expected)?

- 근거: raw_fits_spec v1.9 OI-21 (스펙↔gmon 불일치), gmon DESIGN §10 — 온스카이(2027-02) 전 확정 기회

### 시험·판정 지원 (10-27~29)

**TQ-17. [P1] 셔터 타이밍 의미론 (EXPTIME 연속성)**
> What is the delay from the TTL edge to blades fully open, what blade travel profile produces the position-dependent exposure across the 340 mm focal plane, did the legacy IC firmware apply any shutter-latency correction to EXPTIME, and what minimum interval does the reload require? (We fit Δt from a 0.1–30 s lab ladder and must compare like-for-like with 10+ years of archive EXPTIME.)

**TQ-18. [P1] 롤백 실행 가능성 실사**
> If the new wallboard fails acceptance, is reinstalling the original OSU wallboard genuinely feasible within the remaining site days? Which removal steps are one-way, what must be preserved untouched during the swap to keep rollback open, and what is a realistic revert timeline?

- 근거: RECOVERY_ROLLBACK_PLAN Level 4 — 기대 산출물: 롤백 성립 조건 목록 (10-22 제거 전에 합의)

**TQ-19. [P1] PCC 교체 판단 기준·냉매라인 취급 규칙**
> What criteria decide swapping to the new PCC versus keeping the old one as fallback? What cryoline handling rules apply (bend radius, purge/evacuation on reconnect, decontamination cycle), and what failure modes have the site PCCs shown that we should watch during cooldown?

### 마무리·보관 (10-29~30)

**TQ-20. [P0→보관] 3개월 보관 구성 (10-30 → 2027-02 온스카이까지)**
> For the ~3-month storage with the cooler off: what warm-up and vent procedure avoids condensation on the CCDs, should the dewar be left under vacuum / backfilled with dry N2 / periodically re-pumped, how long does it hold vacuum unpumped, and what monitoring should site staff perform while the team is away?

**TQ-21. [P2] 이력 기반 잡동사니 (한 세션에 일괄)**
> (a) EMI history: which site devices (chiller, pumps, shutter motor, telescope drives) coupled into the video chain originally, at what frequencies, and what grounding/shield fixes worked? (b) LEDFLASH inspection LED: where is it mounted, does its wiring pass through the wallboard being replaced, what drive is safe, and what was the 2018 SAAO OSU-code fault? (c) Guide-fiber 'GO DMA WAIT TIMEOUT' aborts: was the marginal element in the removed electronics or in dewar-side connectors we should inspect/reseat while open?

---

## Part C — 계약 산출물 연계 (10-30)

- **Lessons-learned + CTIO/SAAO 권고사항 서면 보고서** (계약 deliverable): 위 TQ 답변 중 절차·수치 확정분을 반영해 CTIO(11-12~)·SAAO(12-06~) SOP 갱신의 입력으로 사용.
- 답변 기록 담당을 지정하고(권장: 작업 리더와 분리), 각 세션 종료 시 값·수치를 당일 site work log에 기록한다.

## 진행 관리

| 단계 | 시점 | 액션 |
| --- | --- | --- |
| WQ 발송 | 즉시 (수락 회신 후) | WQ-1~5 이메일 — 특히 WQ-2는 항공출고 전 회신 필수 |
| SOP 사전검토 | 10월 초 | WQ-5: SOP 초안 송부 |
| 현장 세션 | 10-20 ~ 10-29 | TQ-1~21, 일자·작업 연동 |
| 산출물 | 10-30 | lessons-learned 보고서 + 서면 값 일체 회수 |

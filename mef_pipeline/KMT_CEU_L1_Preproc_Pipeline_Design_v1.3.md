# KMT-CEU L0→L1 전처리 파이프라인 설계 (v1.3)

최종 갱신일: 2026-07-02

관련 항목: BACKLOG `KMT-010` (L1 pipeline), `KMT-011` (Operations), `KMT-012` (Provenance),
keyword 규격 §12 "L1 Product 생성 시 주의" (`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`),
결정 기록 D-006~D-008 (`../project_management/governance/DECISION_LOG.md`)

## 1. 목적과 범위

새 전자부(2× STA Archon, 64-amplifier readout)가 생성하는 **L0 64-amp raw MEF**
(`kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` v2.1.2 산출물)를 입력으로 받아,
amp 단위 교정을 모두 마친 **L1 CCD-level calibrated 제품**을 만드는
전처리 파이프라인을 정의한다. 실제 Archon 자료가 나오기 전까지는 mock 변환기
(`kmt_ceu_legacy32_to_l0amp_mef_v2.py`, `MOCKDATA=T`) 산출물로 개발·검증한다.

파이프라인은 세 갈래로 구성한다.

| 트랙 | 입력 | 출력 | 실행 빈도 | 구현 상태 (v1.0) |
| --- | --- | --- | --- | --- |
| (A) 과학 프레임 전처리 | L0 amp MEF (object) | L1 CCD MEF (+MASK; VAR 옵션) | 노출마다 | 구현 완료 |
| (B) 마스터 교정자료 생성 | L0 amp MEF (bias/dark/flat 시퀀스) | master bias/flat, BPM | 관측일/주기별 | 구현 완료 (dark 제외) |
| (C) 검출기 특성 측정 | 전용 시퀀스 (PTC, linearity ramp, crosstalk) | gain/RN table, LINMAX/SATURAT, 64×64 crosstalk matrix, READDIR 확정 | Rehearsal/Site 1회+ | 별도 작업 (KMT-001~003) |

(C)의 산출물은 L0 헤더/`XTALKINFO`와 calibration DB에 버전으로 반영되어 (A)·(B)가
소비한다. 파이프라인은 **코드 수정 없이 계수 교체만으로** 실측값 전환이 되도록 구현되어 있다.

## 2. 확정된 설계 결정 (2026-07-02)

| 항목 | 결정 | 기록 |
| --- | --- | --- |
| L1 픽셀 단위 | **electrons** (`BUNIT='electron'`; GAIN placeholder면 1.0 적용 + `GAINAPPL=F`) | D-006 |
| L1 파일 구성 | **단일 MEF**: PRIMARY + SCI×CHIPLIST + CALHIST. **VAR 기본 제외**(재구성 가능; `--with-var`), **MASK는 별도 `.mask.mef.fits`**(`--mask-file` 옵션, 기본 미생성; `MASKFILE` 기록) | D-007 (2차 개정) |
| 전처리 종점 | **CCD 조립 + astrometry**: 기준성표(`--refcat`)가 있으면 TAN 해(`WCSSOLVE=T`, `WCSRMS`), 실패/성표 없음이면 근사 WCS 유지 + `WCSSOLVE=F`/`WCSFAIL` 플래그. photometric ZP는 후단 | D-008 (개정) |
| 구현 범위 | Full chain + QA (트랙 A·B 전부, mock 야간 검증 포함) | 본 문서 |

## 3. 데이터 레벨 정의

| 레벨 | 내용 | 저장 |
| --- | --- | --- |
| L0 | 64-amp raw MEF (amp별 1200×4616, 로컬 overscan 포함, HDU 69) | 영구 (기존) |
| L1 | CCD 단위(9216×9232) 조립 완료 calibrated image + variance + mask | 영구 |
| CALIB | master bias/flat, BPM (+향후 dark, linearity/crosstalk 계수) | 영구, caldb 버전 관리 |

L1 제품 구조: `PRIMARY` + CCD별 `SCI_x`(float32, electron) — x는 `CHIPLIST`
순서(M,K,N,T) — + `CALHIST` binary table(단계별 적용 여부·교정자료 파일/버전·
파라미터·시각). 노출당 약 1.36 GB. 주요 보정 방법과 수식은 primary header의
COMMENT 카드("processing methods")로 제품 안에 기록된다. 파일명:
`<prefix>.<YYYYMMDD>.<NNNNNN>.ceu.l1ccd.mef.fits` (prefix = kmtc/kmts/kmta).

**MASK (D-007 2차 개정)**: MASK plane은 본 MEF에서 제외하고 `--mask-file` 옵션 시
별도 `*.l1ccd.mask.mef.fits`(PRIMARY+MASK×4, uint8)로 생성한다 — 기본은 미생성.
주의: raw 기준 SATURATED/NONLINEAR 비트는 L1에서 재구성 불가하므로, 마스크가
필요한 처리(측광 등)를 계획하면 `--mask-file`을 켜야 한다. `MASKFILE` 키워드가
연결을 기록한다.

**VAR plane (D-007 개정)**: `VAR = (RDNOISE² + SCI×flat) / flat²` 로 SCI와 교정
참조에서 완전 재구성 가능하므로 기본 제외한다 (`VARINCL=F`, 재구성식을 primary
header COMMENT로 기록; `run --with-var`로 포함 생성 가능, +1.36 GB). MASK는 raw
ADU 기준 SATURATED/NONLINEAR 비트가 재구성 불가하므로 항상 포함한다.

MASK bits: 1=BAD, 2=SATURATED, 4=NONLINEAR, 8=XTALK, 16=AMP_SEAM, 32=NO_OVERSCAN_FIT.

## 4. 과학 프레임 처리 단계 (트랙 A)

keyword 규격 §12의 순서를 따른다. 모든 geometry는 **헤더/AMPINFO에서 읽는다**
(`DATASEC`/`BIASSEC`/`CCDSEC`/`DETSEC`; mock의 `AMPPACK='DATA_LEFT'` 균일 패킹과
실제 ICD 패킹이 코드 수정 없이 모두 처리됨). amp 64개는 controller group(2×32,
crosstalk 결합 영역) 단위로 처리해 메모리를 한 그룹 + 한 CCD 수준으로 제한한다.

| # | 단계 | 내용 | 필요 교정자료 | 현재 동작 |
| --- | --- | --- | --- | --- |
| 0 | Ingest/검증 | 규격 §11 구조 검사(테이블 존재, HDU 수, section 정합), `MOCKDATA` 분기 | — | 동작 |
| 1 | Sat/Linearity 플래그 | raw ADU 기준 `SATURAT`/`LINMAX` 초과 → MASK bit | — | 동작 |
| 2 | Overscan 보정 | amp별 `BIASSEC` 행별 clipped mean + 이동 median 평활 후 감산. mock은 앞 32열만(뒤 16열은 미러 복제). **오염 가드**: 레벨이 master bias `OVSCLVL` 대비 >100 ADU 벗어나면(overscan에 하늘 유입 — legacy 실측 사례) 기준 상수 감산으로 대체 + `NO_OVERSCAN_FIT` 플래그. `OVSC*` QA 기록 | master bias(`OVSCLVL`) | 동작 |
| 3 | Bias 보정 | master bias(amp별 2D 잔차, ADU) 감산 | master bias | 동작 |
| 4 | Dark 보정 | 노출시간 스케일 감산 — 기본 off | master dark | 구조만 |
| 5 | Linearity 보정 | 계수 미측정 → no-op 기록 | linearity 계수 | 구조만 |
| 6 | Crosstalk 보정 | `XTALKINFO` 64×64, group 내 pre-correction 복사본 기준 감산. `XTALKCAL=F`면 no-op | crosstalk matrix | 구조만 |
| 7 | Gain 변환 | ADU→electrons(amp별). `--with-var` 시 variance 초기화 var=RN²+max(sci,0); RN은 `RDNOISE`>0이면 헤더값, 아니면 overscan RMS×gain | gain (L0 헤더) | 동작 |
| 8 | Flat fielding | 필터별 master flat 나눗셈 (`--with-var` 시 var/=flat²). 저응답(<0.1)은 BAD 플래그 | master flat | 동작 |
| 9 | BPM 적용 | MASK에 OR (픽셀값 보존) | BPM | 동작 |
| 10 | AMPMATCH | amp 경계 조화: 내부 경계 양쪽 zone(기본 32px, 마스크 제외) 중앙값으로 CCD당 16-amp 최소제곱 chain 해(평균 고정→CCD 평균 보존). sky≥100 e-면 곱셈(gain성, 상한 10%), 미만이면 덧셈(bias성). overscan fallback 칩은 덧셈 강제(상한 2,000 e-, 정상 amp anchor). 보정치는 `AMMODE`/`AMC*` 카드와 QA에 기록, `--ampmatch off`로 비활성 | — | 동작 |
| 11 | CCD 조립 | `CCDSEC` 배치(`CHIPFLP='None'`, flip 없음), 경계 seam 지표(인접 열/행 차 중앙값), 경계 픽셀 MASK_SEAM | — | 동작 |
| 12 | Astrometry | 5σ 별 검출(마스크 제외, 최대 200개/CCD) → 전역 오프셋 사전 추정(±600px 히스토그램) → 기준성표 매칭(15→5→3px 반복) → TAN 6-parameter fit (ξ,η)=CD·(pix−CRPIX), CRVAL 고정. 성공: WCS 카드 갱신 + `WCSSOLVE=T`/`WCSRMS`/`WCSNMAT`; 실패: 근사 WCS 유지 + `WCSSOLVE=F`/`WCSFAIL`(NO_REFCAT/FEW_STARS/FEW_MATCHES/HIGH_RMS 등) | refcat (`make-refcat` 생성 또는 외부 Gaia 추출) | 동작 |
| 13 | 헤더/출력 | provenance(L0 파일+SHA256, calib 버전, `GAINAPPL`/`XTALKAPL`/`VARINCL`/`MASKFILE`/`WCSNSOLV`), 보정 수식 COMMENT, CALHIST, 임시파일→원자적 교체 | — | 동작 |

## 5. 마스터 교정자료 생성 (트랙 B)

| 산출물 | 입력 | 방법 | 구현 |
| --- | --- | --- | --- |
| master bias | bias N장 | amp별 overscan 보정 후 MAD 기반 sigma-clip mean stack (ADU) | `calib/masters.py` |
| master flat | 필터별 flat N장 | overscan+bias+gain 후 프레임별 chip 조도로 정규화 → clip stack → chip median response=1.0 재정규화. amp 간 감도차는 response에 보존 | `calib/masters.py` |
| BPM | master flat | response < 0.5 또는 > 2.0 → BAD | `calib/bpm.py` |
| master dark | dark 시퀀스 | 필요성 평가 후 (open question #2) | 미구현 |

caldb: 디렉토리 + JSON index. `CALTYPE`(+site, +filter) 매칭 후 관측일 최근접 버전 선택.
모든 마스터는 `CALVER`, `NCOMBINE`, 입력 파일 목록을 헤더에 기록한다.

## 6. 소프트웨어 구조

Python 3.9+, numpy + astropy (converter와 동일 스택), stdlib unittest (pytest 불필요).

```
mef_pipeline/
  kmt_preproc.py           # 실행 래퍼 (설치 불필요)
  run_mock_night.sh        # mock 야간 전체 실행 예제
  kmt_ceu_preproc/
    geometry.py            # FITS section 파서, AmpGeom, CCD shape/DETSEC 유도
    io_l0.py               # L0 reader (AMPINFO/헤더 기반, validate, xtalk matrix)
    io_l1.py               # L1 writer (점진적 append + 원자적 교체), CALHIST
    variance.py            # variance 초기화/RN 선택
    pipeline.py            # 트랙 A orchestrator (controller group 단위)
    steps/                 # saturation, overscan, bias, dark, linearity,
                           # xtalk, gain, flat, bpm, assemble
    calib/                 # masters, bpm, caldb
    qa/                    # 노출별 QA JSON, batch summary markdown
    cli.py                 # calib-bias | calib-flat | bpm | run | qa-summary
  tests/                   # 합성 소형 L0 fixture + 단위/E2E 테스트
```

## 7. QA와 검증

- **QA 지표**: amp별 overscan level/RMS·fallback 여부·saturation/nonlinear 수, CCD별 sky
  median/MAD, seam 지표(수직 7×2 + 수평 1 경계별; 경계 인접 1px 제외 후 4px 밴드 비교로
  edge-column 고정 패턴과 분리), ampmatch 보정치, bad/sat 픽셀 수, 처리 시간 →
  노출별 JSON + `qa_summary.md`.
- **단위 테스트 22개**: section 파싱, overscan(행별 제거·outlier·mirror 열 제외),
  조립/seam/WCS 이동, 합성 야간 E2E(전자 단위 산술, L1 구조, CALHIST, variance).
- **geometry 정밀검증 (2026-07-02 통과)**: mock64를 교정 없이 DATASEC trim+조립한
  mosaic이 구형 32-amp 원본 trim mosaic과 4개 CCD 모두 픽셀 단위 완전 일치.
- **mock 야간 (2026-06-30 세트, 40노출, 2026-07-02 통과)**: BIAS 5 → master bias,
  FLAT V/I 각 3 → master flat, BPM, OBJECT 28 → L1 28개 전부 구조·표준 검증 통과.
  amp seam은 무보정 조립 대비 5–75배 감소(28노출 max|seam| 중앙값 201 e- ≈ sky의 4%).
  QA가 구형 N칩의 죽은 비디오 채널(legacy N02)을 검출해 해당 strip 1,063만 픽셀을
  BAD 플래그 — placeholder/이상 검출 경로가 실데이터로 확인됨. 결과: `l1_mock/qa/`.


## 7.1 검증에서 확인된 데이터 특성 (교훈 기록)

mock 야간 처리에서 확인된 사항 — 실기기(CEU) 커미셔닝 시 점검 목록에 반영할 것:

| # | 확인 사항 | 대응 |
| --- | --- | --- |
| 1 | 구형 N칩 **N02 비디오 채널 사망**(BIAS 208/FLAT 55/OBJECT 196 ADU, 무신호) | flat response 기반 BPM이 strip 전체(1,063만 px)를 BAD 플래그. AMPMATCH는 해당 amp를 제약에서 제외 |
| 2 | 일부 프레임에서 칩 단위 **serial overscan이 하늘 수준으로 오염**(011107 T, 011108·011112 M 등 — overscan이 bias가 아닌 sky+bias를 따름) | overscan 오염 가드: master bias `OVSCLVL` 대비 >100 ADU면 상수 감산 대체 + `NO_OVERSCAN_FIT`. 해당 칩은 AMPMATCH 덧셈 강제(정상 amp anchor, 상한 2,000 e-) |
| 3 | M칩 특정 경계(x3457, x8065)에 **하늘 비례 고정 edge-column 패턴**(~±70–130 e-) | 경계 ±1px는 `MASK_SEAM` 플래그. QA seam 지표는 1px 건너뛴 4px 밴드 비교로 교정 오차와 분리 |
| 4 | amp 경계 잔차는 **하늘에 비례**(gain성) — flat(twilight)과 밤하늘 조명 불일치 | AMPMATCH 곱셈 모드가 기본 (auto) |
| 5 | 구형 amp별 실측 gain 1.6–1.7 e-/ADU가 mock 헤더로 승계 | electrons 변환·AMPMATCH 실검증 가능 |
| 6 | mock overscan 48열 중 **뒤 16열은 미러 복제** | overscan fit은 앞 32열만 사용(`MOCKDATA` 자동) |
| 7 | 구형 K/N칩 amp 라벨이 strip 위치와 역순 | geometry는 전부 `CCDSEC` 기반 → 라벨 무관(픽셀 완전 일치 검증) |
| 8 | **방문 간 TCS 지향 반복오차가 정밀 매칭 반경(15px≈6″)을 초과** — 같은 필드 재방문도 즉시 매칭 불가 | 전역 오프셋 사전 추정(검출−기준 오프셋 2D 히스토그램 최빈값, 탐색 ±600px) 후 정밀 매칭 |
| 9 | mock 야간은 **여러 필드**(RA 164°/162°/266° 등)를 방문 — 단일 프레임 성표로는 다른 필드가 `FEW_REF_IN_FIELD`로 실패 플래그됨(설계 의도대로) | `make-refcat`이 여러 L1을 병합(2″ 중복 제거)해 야간 전체 커버; 운영에서는 필드별/전천 외부 성표(Gaia) 권장 |
| 10 | 밝은 별 포화(blooming)로 인해 **성표와 대상의 별 검출이 같은 마스크 정책을 써야 매칭 가능** — 마스크 없는 성표(포화 피크 포함) vs 마스크 적용 대상(포화 제외)은 상위 200 별 집합이 크게 어긋나 FEW_MATCHES 발생 | pass 1을 `--mask-file`로 돌려 `make-refcat`이 sibling mask로 동일한 검출을 수행 |

## 8. 실측값 전환 계획 (Rehearsal/Site)

| 실측 항목 | 반영 경로 | 파이프라인 변경 |
| --- | --- | --- |
| gain/RN (KMT-001) | L0 헤더/AMPINFO 갱신 | 없음 (`GAINAPPL=T` 자동) |
| linearity (KMT-001) | 계수 테이블 caldb 등록 | `steps/linearity.py` 보정식 활성화 |
| crosstalk (KMT-003) | `XTALKINFO` 실측 + `XTALKCAL=T` | 없음 (자동 적용) |
| READDIR (KMT-002) | L0 geometry/ICD 반영 | 없음 (geometry는 헤더 기반) |
| dark 정책 | master dark 생성 + config on | `calib`에 builder 추가 |

## 9. 남은 결정/후속 항목 (Open)

| # | 항목 | 상태 |
| --- | --- | --- |
| 1 | dark 보정 활성화 여부 | Rehearsal dark 특성 후 결정 (기본 off) |
| 2 | CR rejection 위치 | 후단 파이프라인 (필요 시 옵션 추가) |
| 3 | 파이프라인의 site 설치/freeze 대상 여부 | freeze(2026-09-15) 전 결정 필요 |
| 4 | L1 보관/배포 정책 (노출당 ~1.7 GB; 추가 절감은 fpack 압축 검토) | KMT-009 데이터 정책과 함께 |
| 5 | master dark builder | open #1 결정 후 |

## 10. Revision History

| 버전 | 일자 | 내용 |
| --- | --- | --- |
| v0.1 | 2026-07-02 | 최초 설계 초안 |
| v1.0 | 2026-07-02 | 설계 결정 확정(D-006~D-008), Full chain + QA 구현 및 검증 반영 |
| v1.1 | 2026-07-02 | D-007 개정: VAR plane 기본 제외(재구성식 header 기록, `--with-var` 옵션), L1 PRODVER v1.1, 노출당 3.1→1.7 GB |
| v1.2 | 2026-07-02 | AMPMATCH 단계 추가: amp 경계 gain/bias 잔차 조화(자동 곱셈/덧셈, CCD 평균 보존, 죽은 amp 제외), 보정치 header/QA 기록. overscan 오염 가드 추가(master bias `OVSCLVL` 기준, 하늘 유입 시 상수 감산 대체) |
| v1.3 | 2026-07-02 | D-007 2차 개정: MASK를 별도 파일 옵션(`--mask-file`, 기본 미생성)으로 분리. D-008 개정: astrometry를 전처리에 포함(TAN fit, 실패 시 `WCSSOLVE=F`/`WCSFAIL` 플래그, `make-refcat` 부트스트랩). 보정 방법/수식을 L1 primary COMMENT로 기록 |

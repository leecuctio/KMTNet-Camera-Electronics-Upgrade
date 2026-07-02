# KMT-CEU L0→L1 전처리 파이프라인 설계 (v1.0)

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
| (A) 과학 프레임 전처리 | L0 amp MEF (object) | L1 CCD MEF (+VAR, +MASK) | 노출마다 | 구현 완료 |
| (B) 마스터 교정자료 생성 | L0 amp MEF (bias/dark/flat 시퀀스) | master bias/flat, BPM | 관측일/주기별 | 구현 완료 (dark 제외) |
| (C) 검출기 특성 측정 | 전용 시퀀스 (PTC, linearity ramp, crosstalk) | gain/RN table, LINMAX/SATURAT, 64×64 crosstalk matrix, READDIR 확정 | Rehearsal/Site 1회+ | 별도 작업 (KMT-001~003) |

(C)의 산출물은 L0 헤더/`XTALKINFO`와 calibration DB에 버전으로 반영되어 (A)·(B)가
소비한다. 파이프라인은 **코드 수정 없이 계수 교체만으로** 실측값 전환이 되도록 구현되어 있다.

## 2. 확정된 설계 결정 (2026-07-02)

| 항목 | 결정 | 기록 |
| --- | --- | --- |
| L1 픽셀 단위 | **electrons** (`BUNIT='electron'`; GAIN placeholder면 1.0 적용 + `GAINAPPL=F`) | D-006 |
| L1 파일 구성 | **단일 MEF**: PRIMARY + (SCI/VAR/MASK)×CHIPLIST + CALHIST | D-007 |
| 전처리 종점 | **CCD 조립 + 근사 WCS** (`WCSAPPRX=T`; 정밀 astrometry/ZP는 후단) | D-008 |
| 구현 범위 | Full chain + QA (트랙 A·B 전부, mock 야간 검증 포함) | 본 문서 |

## 3. 데이터 레벨 정의

| 레벨 | 내용 | 저장 |
| --- | --- | --- |
| L0 | 64-amp raw MEF (amp별 1200×4616, 로컬 overscan 포함, HDU 69) | 영구 (기존) |
| L1 | CCD 단위(9216×9232) 조립 완료 calibrated image + variance + mask | 영구 |
| CALIB | master bias/flat, BPM (+향후 dark, linearity/crosstalk 계수) | 영구, caldb 버전 관리 |

L1 제품 구조: `PRIMARY` + CCD별 `SCI_x`(float32, electron), `VAR_x`(float32, electron²),
`MASK_x`(uint8) — x는 `CHIPLIST` 순서(M,K,N,T) — + `CALHIST` binary table
(단계별 적용 여부·교정자료 파일/버전·파라미터·시각). 파일명:
`<prefix>.<YYYYMMDD>.<NNNNNN>.ceu.l1ccd.mef.fits` (prefix = kmtc/kmts/kmta).

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
| 2 | Overscan 보정 | amp별 `BIASSEC` 행별 clipped mean + 이동 median 평활 후 감산. mock은 앞 32열만(뒤 16열은 미러 복제). `OVSC*` QA 기록 | — | 동작 |
| 3 | Bias 보정 | master bias(amp별 2D 잔차, ADU) 감산 | master bias | 동작 |
| 4 | Dark 보정 | 노출시간 스케일 감산 — 기본 off | master dark | 구조만 |
| 5 | Linearity 보정 | 계수 미측정 → no-op 기록 | linearity 계수 | 구조만 |
| 6 | Crosstalk 보정 | `XTALKINFO` 64×64, group 내 pre-correction 복사본 기준 감산. `XTALKCAL=F`면 no-op | crosstalk matrix | 구조만 |
| 7 | Gain 변환 | ADU→electrons(amp별), variance 초기화 var=RN²+max(sci,0). RN은 `RDNOISE`>0이면 헤더값, 아니면 overscan RMS×gain | gain (L0 헤더) | 동작 |
| 8 | Flat fielding | 필터별 master flat 나눗셈, var/=flat². 저응답(<0.1)은 BAD 플래그 | master flat | 동작 |
| 9 | BPM 적용 | MASK에 OR (픽셀값 보존) | BPM | 동작 |
| 10 | CCD 조립 | `CCDSEC` 배치(`CHIPFLP='None'`, flip 없음), 경계 seam 지표(인접 열/행 차 중앙값), 경계 픽셀 MASK_SEAM | — | 동작 |
| 11 | 헤더/WCS/출력 | 기준 amp WCS의 CRPIX 이동으로 근사 CCD WCS, provenance(L0 파일+SHA256, calib 버전, `GAINAPPL`/`XTALKAPL`), CALHIST, 임시파일→원자적 교체 | — | 동작 |

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

- **QA 지표**: amp별 overscan level/RMS·saturation/nonlinear 수, CCD별 sky
  median/MAD, seam 지표(수직 7×2 + 수평 1 경계별), bad/sat 픽셀 수, 처리 시간 →
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
| 4 | L1 보관/배포 정책 (노출당 ~3 GB) | KMT-009 데이터 정책과 함께 |
| 5 | master dark builder | open #1 결정 후 |

## 10. Revision History

| 버전 | 일자 | 내용 |
| --- | --- | --- |
| v0.1 | 2026-07-02 | 최초 설계 초안 |
| v1.0 | 2026-07-02 | 설계 결정 확정(D-006~D-008), Full chain + QA 구현 및 검증 반영 |

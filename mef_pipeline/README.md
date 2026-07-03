# KMTNet-CEU L0→L1 전처리 파이프라인

최종 갱신일: 2026-07-03

## 목적

이 디렉토리는 **L0 64-amplifier raw MEF**(`../mef_converter/` 산출물)를 amp 단위 교정 후
CCD 단위로 조립한 **L1 CCD-level calibrated MEF**로 변환하는 전처리 파이프라인이다.
처리 순서는 keyword 규격 §12(`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`)를 따른다.

설계 문서: [`KMT_CEU_L1_Preproc_Pipeline_Design_v1.5.md`](KMT_CEU_L1_Preproc_Pipeline_Design_v1.5.md)

## 현재 기준선

| 구분 | 값 |
| --- | --- |
| 파이프라인 | `kmt_ceu_preproc` v1.5 (순수 Python + NumPy + astropy) |
| L1 제품 | `PRODVER=v1.2`, 단일 MEF: PRIMARY + SCI×4 CCD + CALHIST (~1.36 GB/노출). 보정 수식은 primary COMMENT 기록 |
| VAR plane | 기본 제외 (`VARINCL=F`; 재구성식 header 기록, `run --with-var`로 생성 가능) |
| MASK plane | 기본 미생성; `run --mask-file` 시 별도 `*.l1ccd.mask.mef.fits` 생성 (`MASKFILE` 기록) |
| Astrometry | Gaia 기준 **TAN–SIP(3)** 해 (칩별 대표 템플릿 초기값, scale 0.3952″/px); 성공 `WCSSOLVE=T`+`WCSRMS`(~0.25″), 실패 `WCSSOLVE=F`+`WCSFAIL` |
| L1 픽셀 단위 | electrons (`BUNIT='electron'`, amp별 GAIN 적용, placeholder면 1.0 + `GAINAPPL=F`) |
| 종점 | CCD 조립 + astrometry (기준성표 기반; photometric ZP는 후단) |
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
| 12 | 조립 | `CCDSEC` 배치(flip 없음), seam 지표, 근사 WCS | 동작 |
| 13 | Astrometry | 별 검출(≤800) → 칩별 템플릿 초기값 → 구역 seed + annulus 확장 → **TAN–SIP(3) fit**, WCS 키워드 갱신. 실패 시 `WCSSOLVE=F`+`WCSFAIL` 플래그 | 동작 |
| 14 | 출력 | provenance(`CALHIST`, 수식 COMMENT), 임시파일→원자적 교체 | 동작 |

MASK bits: 1=BAD, 2=SATURATED, 4=NONLINEAR, 8=XTALK, 16=AMP_SEAM, 32=NO_OVERSCAN_FIT

VAR 재구성 (D-007 개정): `VAR = (RDNOISE² + SCI×flat) / flat²` [electron²] —
flat은 primary header `CALFLAT`이 가리키는 master flat plane, RDNOISE는 L0 amp
header/AMPINFO. **주의**: MASK의 SATURATED/NONLINEAR 비트는 raw 기준 판정이라 L1에서
재구성 불가 — 마스크가 필요한 후속 처리(정밀 측광 등)는 `--mask-file`로 생성해 둘 것.
위 수식들을 포함한 전체 보정 방법은 모든 L1 primary header의 COMMENT
"processing methods" 블록에 그대로 기록된다.

**Astrometry (v1.4, Gaia 실증 절차)**: KMTNet 주초점 광학 왜곡이 칩 모서리에서
17–54″에 달해 선형 TAN으로는 불가 — **TAN–SIP(3)** 로 푼다. 초기값은 칩별 대표
템플릿(`kmt_ceu_preproc/data/astrom_template.json`: scale **0.3952″/px**, 칩 회전각
M +0.072°/K −0.358°/N −0.777°/T +0.239°, 칩 중심 오프셋 ±0.533°/±0.562°, 평균 SIP —
011103–06 프레임 16개 Gaia 해의 평균, 프레임 간 scale 산포 0.01 mas/px)에 지향
keyword(RA/DEC)를 결합해 만들고, 템플릿이 없으면 L0 근사 WCS를 0.395로 재척도해
쓴다. 이후 최다득표 구역 seed(±700px, TCS 반복오차·칩 내 ~100px 오차 기울기 대응) →
annulus 확장(1,500px 스텝, 12px 매칭, 2.5px 클립, 차수 2→3) → 최종 5px 매칭으로
수렴한다. 매칭·평가는 반드시 SIP 인지 `all_world2pix` 사용. 결과: 검증 프레임들에서
칩당 400–760개 매칭, median ~0.13″, rms 0.23–0.38″. 실패 시 `WCSSOLVE=F` +
`WCSFAIL`(NO_REFCAT/FEW_STARS/NO_SEED_ZONE/FEW_MATCHES/HIGH_RMS/NO_FIT).

기준성표(우선순위): ① **로컬 Gaia 스토어**(`run --gaia-local DIR`) — 지향
keyword에서 노출마다 자동으로 콘을 추출(<0.5초, 네트워크 불필요)하고 `MJD-OBS`
기준으로 고유운동을 관측 시점에 전파한다. 스토어는 dec 1°×RA 15° 구획의 npy
파일(행당 28 B: ra/dec/G/pmRA/pmDE — 전천 G<19 ≈ 20 GB, 관측 필드만이면 수십 MB)로,
`gaia-ingest`가 `fetch-gaia` 산출 FITS나 **ESA gaia_source bulk csv(.gz)** 에서
만든다(중복 자동 제거 — 겹치는 콘 안전). 야간 배치의 병목이던 VizieR 조회
(~65분/야간)가 사라지고 사이트 오프라인 운영이 가능하다. ② `--refcat FITS`
(`fetch-gaia` 개별 콘, 네트워크). ③ `make-refcat`(L1 추출·병합, 상대 정렬).
성표와 대상의 별 검출은 같은 마스크 정책이어야 한다(`--mask-file` pass 권장).

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
bash mef_pipeline/run_mock_night.sh raw ./mef_pipeline_out
```

개별 명령:

```bash
PP="python3 mef_pipeline/kmt_preproc.py"
$PP calib-bias  bias1.fits bias2.fits ...   -d l1_out          # master bias
$PP calib-flat  flatV1.fits flatV2.fits ... -d l1_out          # master flat (필터 자동)
$PP bpm         --flat l1_out/caldb/master_flat_I.fits -d l1_out
$PP run         object*.fits -d l1_out -f                      # L0 -> L1
$PP gaia-ingest cones/*.fits --store l1_out/caldb/gaia_local -d l1_out  # 로컬 스토어 구축
$PP run         object*.fits -d l1_out -f \
                --gaia-local l1_out/caldb/gaia_local           # 오프라인 astrometry(권장)
$PP fetch-gaia  --like KMTN...MK.fits -d l1_out                # Gaia DR3 개별 콘(네트워크)
$PP make-refcat l1_out/*.ceu.l1ccd.mef.fits -d l1_out          # 오프라인 부트스트랩(대안)
$PP run         object*.fits -d l1_out -f \
                --refcat l1_out/caldb/refcat.fits              # astrometry 포함 처리
$PP qa-summary  -d l1_out                                      # QA markdown
```

`run` 주요 옵션: `--with-var`(VAR 포함), `--mask-file`(별도 MASK 파일 생성),
`--refcat PATH`(astrometry 기준성표; FITS RA/DEC 테이블 — `make-refcat` 산출물
또는 외부 Gaia 추출), `--ampmatch off|mult|add|auto`.

교정자료는 `l1_out/caldb/`(JSON index로 site+필터+최근접 날짜 선택), QA JSON은
`l1_out/qa/`에 쌓인다. 대용량 산출물은 `.gitignore` 대상이며 별도 보관 정책을 따른다.

## 단위 테스트

```bash
python3 -m unittest discover -s mef_pipeline/tests
```

합성 소형 L0(4-amp)로 geometry/overscan/조립/variance와 마스터 생성→L1까지의
end-to-end 산술(gain 2.0 e-/ADU 검증 가능)을 시험한다. pytest 불필요(stdlib unittest).

## 검증 결과 (mock 2026-06-30 야간, 40노출)

- 단위 테스트 40개 통과 (astrometry solver의 교란 WCS 복원 포함)
- **geometry 정밀검증**: 교정 없이 DATASEC trim+조립한 mosaic이 구형 32-amp 원본의
  trim mosaic과 4개 CCD 모두 **픽셀 단위 완전 일치** (K/N 역순 strip 매핑 포함)
- master bias(BIAS 5장)·master flat V/I(각 3장)·BPM 생성, OBJECT 28장 → L1 28개
  모두 구조(HDU 10개, BUNIT, provenance, JD/MJD 일관성)와 astropy
  `verify('exception')` 통과 — 상세는 `mef_pipeline_out/qa/qa_summary.md`
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
- **Astrometry (Gaia DR3 절대, 야간 전체)**: 필드별 Gaia 성표(21개 필드,
  팽대부는 G<16/15 적응 제한)로 28노출 × 4 CCD 중 **105개 해**(`WCSSOLVE=T`,
  rms 중앙값 0.31″·최대 0.85″, 매칭 중앙값 746개/칩). 실패 7개는 전부 정당:
  초점 스윕 프레임 011109(4칩, NO_SEED_ZONE/FIT_ERROR)와 readout 기하 손상 칩
  011107 T·011108 M·011112 M — 모두 `WCSFAIL`로 플래그
- 처리 속도: 노출당 ~10초 (검증·SHA256·astrometry·1.36 GB L1 쓰기 포함, Apple SSD 기준)

## 실측값 전환 (Rehearsal/Site)

gain/RN/linearity/crosstalk가 실측되면 **코드 수정 없이** L0 헤더/`XTALKINFO`와
caldb의 교정자료 교체만으로 반영된다 (`GAINAPPL`/`XTALKAPL`로 상태 추적).
placeholder 정책은 DECISION_LOG D-005를 따른다.

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| 설계 문서 | `KMT_CEU_L1_Preproc_Pipeline_Design_v1.5.md` |
| L0 데이터 규격 (keyword/ICD) | `../mef_fits_spec/README.md` |
| L0 변환기 | `../mef_converter/README.md` |
| 기술 결정 기록 (D-006~D-008 및 개정: L1 단위/구조/종점/astrometry) | `../project_management/governance/DECISION_LOG.md` |
| Calibration 추적 | `../project_management/science/CALIBRATION_TRACKER.md` |

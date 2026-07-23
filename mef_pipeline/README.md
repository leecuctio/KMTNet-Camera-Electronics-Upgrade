# KMTNet-CEU L0→L1 전처리 파이프라인

최종 갱신일: 2026-07-03 (v1.6)

## 목적

이 디렉토리는 **L0 64-amplifier raw MEF**(`../mef_converter/` 산출물)를 amp 단위 교정 후
CCD 단위로 조립한 **L1 CCD-level calibrated MEF**로 변환하는 전처리 파이프라인이다.
처리 순서는 keyword 규격 §12(`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`)를 따르고,
v1.6에서 대형 서베이(Rubin/DES/HSC/ZTF/PS1) 표준 전처리 단계(fringe, illumination,
CR 플래그, sky 모델, 근사 photometric ZP)를 추가했다.

설계 문서: [`KMT_CEU_L1_Preproc_Pipeline_Design_v1.6.md`](KMT_CEU_L1_Preproc_Pipeline_Design_v1.6.md)

## 현재 기준선

| 구분 | 값 |
| --- | --- |
| 파이프라인 | `kmt_ceu_preproc` **v1.6** (순수 Python + NumPy + astropy) |
| L1 제품 | `PRODVER=v1.3`, 단일 MEF: PRIMARY + SCI×4 CCD + CALHIST (~1.36 GB/노출). 보정 수식은 primary COMMENT 기록 |
| VAR plane | 기본 제외 (`VARINCL=F`; 재구성식 header 기록, `run --with-var`로 생성 가능) |
| MASK plane | 기본 미생성; `run --mask-file` 시 별도 `*.l1ccd.mask.mef.fits` 생성 (`MASKFILE` 기록) |
| Astrometry | Gaia 기준 **TAN–SIP(3)** 해 (칩별 대표 템플릿 초기값, scale 0.3952″/px); 성공 `WCSSOLVE=T`+`WCSRMS`(~0.25″), 실패 `WCSSOLVE=F`+`WCSFAIL` |
| Photometric ZP | astrometry 성공 칩에서 **Gaia G 기준 근사 zero point** (`ZPMAG`/`ZPRMS`/`ZPNSTAR`; 색항 없음 — 상대/QA용) |
| L1 픽셀 단위 | electrons (`BUNIT='electron'`, amp별 GAIN 적용, placeholder면 1.0 + `GAINAPPL=F`) |
| 종점 | CCD 조립 + astrometry + 근사 ZP (절대 측광 보정은 후단) |
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
| 10 | **Fringe** (v1.6) | 필터별 master fringe(하늘 대비 비율 패턴)를 amp별 **clipped LSQ 스케일 fit** 후 감산. 템플릿 진폭이 무시 수준인 amp는 기록만 하고 건너뜀 (`FRNGSCL`) | 동작 |
| 11 | **Illumination** (v1.6) | 필터별 dark-sky 조명 보정(대규모 평활 response, 칩 중앙값=1) 나눗셈 — twilight flat과 밤하늘 조명 차이 보정 (`ILLUMDEV`) | 동작 |
| 12 | BPM | bad pixel MASK 병합 (픽셀값 보존) | 동작 |
| 13 | AMPMATCH | amp 경계 조화 — 경계 양쪽 zone 중앙값으로 amp별 잔차 gain/bias 보정 (CCD 평균 보존) | 동작 |
| 14 | 조립 | `CCDSEC` 배치(flip 없음), seam 지표, 근사 WCS | 동작 |
| 15 | **CR 플래그** (v1.6) | 단일 프레임 우주선 검출(3×3 median Laplacian 유의도 + 8-이웃 ring + van Dokkum fine-structure 판정, 타일 처리) → **MASK bit 64 기록만** (픽셀값 불변, `CRCOUNT`). `--cr off`로 비활성 | 동작 |
| 16 | **Sky 모델** (v1.6) | 256px clipped-median mesh + bilinear 배경 모델 — 기본은 **측정만**(`SKYLVL`/`SKYRMS`/`SKYGRADX`/`SKYGRADY`), `--sky sub` 시 감산(`SKYSUB=T`). DIA를 위해 기본은 하늘 보존 | 동작 |
| 17 | Astrometry | 별 검출(≤800, CR 제외) → 칩별 템플릿 초기값 → 구역 seed + annulus 확장 → **TAN–SIP(3) fit**, WCS 키워드 갱신. 실패 시 `WCSSOLVE=F`+`WCSFAIL` 플래그 | 동작 |
| 18 | **Photometric ZP** (v1.6) | WCS 성공 칩에서 aperture 측광(r=4px, annulus 8–12px) ↔ Gaia G 매칭 → clipped median `ZPMAG`(+`ZPRMS`/`ZPNSTAR`). **근사값**(Gaia G 기준, 색항 없음) — 투명도/칩간 상대 추적·QA용 | 동작 |
| 19 | 출력 | provenance(`CALHIST` 17행, 수식 COMMENT), 임시파일→원자적 교체 | 동작 |

MASK bits: 1=BAD, 2=SATURATED, 4=NONLINEAR, 8=XTALK, 16=AMP_SEAM, 32=NO_OVERSCAN_FIT, **64=COSMIC_RAY**

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

## v1.6 신규 단계 사용 시 주의

- **calib-fringe / calib-illum 입력 선정**: flat 보정된 **과학 프레임**에서 만들며,
  **필드당 1장**(중복 지향 프레임은 같은 픽셀에 별이 반복돼 clipped stack을 살아남음)과
  초점 스윕 제외가 원칙이다. 빌더가 중복 필드·필드 다양성 부족·flat 부재를 경고한다.
  팽대부처럼 혼잡한 필드만으로 만든 illumination은 항성 밀도 기울기가 스며들 수 있어
  가능하면 여러 방향의 필드를 섞는다.
- **Fringe**: mock(=실측 legacy CTIO I밴드 픽셀)에서 하늘의 ~0.7% 진폭 소규모 패턴이
  실제로 검출·제거된다. 템플릿 진폭이 무시 수준(<0.01%)인 amp는 자동 no-op.
- **CR 플래그는 픽셀을 바꾸지 않는다** — BPM과 같은 flag-only 정책. 언더샘플 PSF(FWHM
  ~2.5px)에서 별 어깨 오검출을 막는 fine-structure 판정이 들어 있다(단위테스트로 검증).
- **ZPMAG는 근사값**: Gaia G 기준·색항 없음. 밤사이 투명도, 칩간·노출간 상대 변화 추적과
  QA용이며, 절대 등급 보정(필터 변환식)은 후단 측광 보정에서 확정한다.
- **Sky는 기본 보존**: 차감영상(DIA)측 처리에 하늘 통계가 필요하므로 기본은 측정만.

## 실행

repo 루트에서 (mock 야간 전체: master bias/flat/BPM/fringe/illum → OBJECT 28장 → QA summary):

```bash
bash mef_pipeline/run_mock_night.sh raw ./mef_pipeline_out
```

개별 명령:

```bash
PP="python3 mef_pipeline/kmt_preproc.py"
$PP calib-bias  bias1.fits bias2.fits ...   -d mef_pipeline_out          # master bias
$PP calib-flat  flatV1.fits flatV2.fits ... -d mef_pipeline_out          # master flat (필터 자동)
$PP calib-fringe obj_field1.fits obj_field2.fits ... -d mef_pipeline_out # master fringe (필드당 1장)
$PP calib-illum  obj_field1.fits obj_field2.fits ... -d mef_pipeline_out # illumination (필드당 1장)
$PP bpm         --flat mef_pipeline_out/caldb/master_flat_I.fits -d mef_pipeline_out
$PP run         object*.fits -d mef_pipeline_out -f                      # L0 -> L1
$PP gaia-ingest cones/*.fits --store mef_pipeline_out/caldb/gaia_local -d mef_pipeline_out  # 로컬 스토어 구축
$PP run         object*.fits -d mef_pipeline_out -f \
                --gaia-local mef_pipeline_out/caldb/gaia_local           # 오프라인 astrometry(권장)
$PP fetch-gaia  --like KMTN...MK.fits -d mef_pipeline_out                # Gaia DR3 개별 콘(네트워크)
$PP make-refcat mef_pipeline_out/*.ceu.l1ccd.mef.fits -d mef_pipeline_out          # 오프라인 부트스트랩(대안)
$PP run         object*.fits -d mef_pipeline_out -f \
                --refcat mef_pipeline_out/caldb/refcat.fits              # astrometry 포함 처리
$PP qa-summary  -d mef_pipeline_out                                      # QA markdown
```

`run` 주요 옵션: `--with-var`(VAR 포함), `--mask-file`(별도 MASK 파일 생성),
`--refcat PATH`(astrometry 기준성표; FITS RA/DEC[+GMAG] 테이블 — `make-refcat`
산출물 또는 외부 Gaia 추출), `--ampmatch off|mult|add|auto`,
`--no-fringe`/`--no-illum`(마스터 있어도 건너뜀), `--cr flag|off`(+`--cr-sigma`),
`--sky measure|sub|off`, `--no-zp`. ZP는 GMAG를 가진 성표(로컬 Gaia 스토어 또는
`fetch-gaia` 산출물)에서만 측정된다.

교정자료는 `mef_pipeline_out/caldb/`(JSON index로 site+필터+최근접 날짜 선택), QA JSON은
`mef_pipeline_out/qa/`에 쌓인다. 대용량 산출물은 `.gitignore` 대상이며 별도 보관 정책을 따른다.

## 단위 테스트

```bash
python3 -m unittest discover -s mef_pipeline/tests
```

합성 소형 L0(4-amp)로 geometry/overscan/조립/variance와 마스터 생성→L1까지의
end-to-end 산술(gain 2.0 e-/ADU 검증 가능)을 시험한다. v1.6에서 신규 단계 테스트
12개 추가(**총 64개**): fringe 스케일 fit·주입 패턴 복원, illumination 기울기 복원,
CR 플래그(언더샘플 σ=1.2px 별 미오검출 + 1·2px CR 검출 + 포화 가드), sky 모델
기울기 복원·감산, ZP 복원(합성 별 ±0.05 mag). pytest 불필요(stdlib unittest).

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
- **v1.6 신규 단계 (동일 야간 재처리, 28노출 전부 통과)**:
  - **Fringe**: unique-field 18장(I)/4장(V)에서 master fringe 생성 — mock의 실측
    legacy I밴드 픽셀에서 하늘 대비 **~0.7% 진폭**의 소규모 고정 패턴이 실제로
    검출됨(`FRNGAMP` 중앙값 7.0e-3). 프레임별 fit 스케일 중앙값 ~3,400 e-
    (하늘 4,700 e-의 ~72% — 상관 성분만 감산, 실효 패턴 진폭 ≈ 스케일×진폭 ≈ 24 e-)
  - **Illumination**: unique-field dark-sky response(I/V) 생성·적용. 정상 amp
    편차 수 % 수준, 죽은 N칩 strip은 response≈0으로 정직하게 기록(BPM이 BAD 처리)
  - **CR 플래그**: 칩당 중앙값 ~39k px(0.045%; 실 CR + BPM 미포함 hot pixel +
    혼잡 필드 잔여). >0.2% `cr_warning` 13개 칩은 전부 알려진 손상 칩(011107 T·
    011108 M·011112 M)과 늦은 시각 프레임(011126–011130 일부)으로 QA가 정확히 표적
  - **Sky 모델**: 전 칩 `SKYLVL`/`SKYRMS`/`SKYGRAD*` 기록 (하늘 중앙값 ~4,700 e-)
  - **Photometric ZP**: WCS 성공 **105개 칩 전부**에서 측정 — I 중앙값 24.69,
    V 중앙값 23.41, `ZPRMS` 중앙값 0.30 mag(Gaia G 대비 색항 없음에 따른 색 산포;
    상대 추적용으로 충분). 같은 필드 반복 방문 간 ZP 차 69–382 mmag로 야간 투명도
    변화 추적 가능
- 처리 속도: v1.5 노출당 ~10초 → **v1.6 ~24초**(4병렬 유효; 단독 ~90초 — CR·sky·
  ZP·fringe/illum 추가 비용, 검증·SHA256·astrometry·1.36 GB L1 쓰기 포함, Apple SSD 기준)

## 실측값 전환 (Rehearsal/Site)

gain/RN/linearity/crosstalk가 실측되면 **코드 수정 없이** L0 헤더/`XTALKINFO`와
caldb의 교정자료 교체만으로 반영된다 (`GAINAPPL`/`XTALKAPL`로 상태 추적).
placeholder 정책은 DECISION_LOG D-005를 따른다.

## Linux 서버 배포·운영 가이드

### 요구사항

| 항목 | 요구/권장 | 비고 |
| --- | --- | --- |
| Python | **≥3.10** (개발·검증 3.10.8; 3.11/3.12 권장 — 순수 파이썬 구간 10–20% 빠름) | 구형 배포판 기본 python3(3.6/3.8) 불가 → conda/pyenv/배포판 모듈 |
| numpy | ≥1.22 | `sliding_window_view` 사용 |
| astropy | ≥5.3 (개발 6.1.7) | `fit_wcs_from_points`(SIP), TAN–SIP WCS |
| 그 외 | 없음 | scipy·pytest 불필요(테스트는 stdlib unittest), GUI 불필요 |
| curl | `fetch-gaia`에만 필요 | `--gaia-local` 오프라인 경로는 불필요 |

UTF-8 로케일(`LANG=C.UTF-8`) 확인. `run_mock_night.sh`는 bash 전용. 패키지 설치
없이 `python3 mef_pipeline/kmt_preproc.py ...`로 바로 실행된다.

### 설치와 검증

```bash
python3 -m venv ~/venv/kmtceu && source ~/venv/kmtceu/bin/activate
pip install "numpy>=1.22" "astropy>=5.3"
git clone https://github.com/leecuctio/KMTNet-Camera-Electronics-Upgrade.git
cd KMTNet-Camera-Electronics-Upgrade
python3 -m unittest discover -s mef_pipeline/tests   # 데이터 없이 도는 설치 검증
```

### git에 없는 것 (별도 준비)

1. **원본 FITS** — `raw/`로 전송 (MK/NT·legacy/mock64 쌍은 같은 디렉토리 유지).
2. **마스터 교정자료(caldb)** — 서버에서 재생성 권장(`calib-bias`/`calib-flat`/`bpm`,
   수 분). 기존 caldb를 rsync로 옮길 경우 **`caldb/index.json`이 절대경로**이므로
   새 경로로 수정해야 한다.
3. **로컬 Gaia 스토어** — `gaia-ingest`로 구축: ESA `gaia_source` bulk csv.gz →
   전천 G<19 약 20 GB, 관측(서베이) 필드만이면 수십 MB. 칩별 astrometry 템플릿은
   repo에 포함(`data/astrom_template.json`)되어 clone만으로 따라온다.
4. 오프라인 동작은 소켓 차단 테스트로 실증됨 — astropy의 숨은 다운로드(IERS 등) 없음.

### 성능 (노출당 실측: I/O 지배, 20–30초/노출 = 0.7 GB 읽기 + 연산 + 1.36 GB 쓰기)

1. **로컬 NVMe/SSD 스크래치에서 처리** — memmap 임의접근이 많아 **NFS 위에서는
   크게 느려진다**. 원본·caldb·산출물을 로컬에 두고 완료 후 아카이브로 이동.
2. **노출 단위 병렬화**(노출 간 완전 독립; L1/QA 파일명이 노출별이라 동시 실행 안전,
   caldb·Gaia 스토어는 처리 중 읽기 전용):

   ```bash
   export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
   ls raw/*.mock64.mef.fits | xargs -P 8 -n 1 -I{} \
     python3 mef_pipeline/kmt_preproc.py run {} -d mef_pipeline_out -f \
       --gaia-local mef_pipeline_out/caldb/gaia_local
   ```

   워커당 메모리 ~3–4 GB 기준으로 병렬수를 정한다(예: 16 병렬 ≈ 64 GB RAM).
   8–16 병렬이면 야간 300노출도 10–20분 수준이며 그 이상은 디스크 대역폭이 한계.
   **단, 마스터 생성(`calib-*`)은 병렬 실행 전에 단독으로** 먼저 끝낼 것
   (`index.json` 쓰기 경합 방지).
3. 마스터(~5 GB)·Gaia 셀은 페이지 캐시에 올라가므로 RAM 여유가 곧 성능.
4. 처리량 최우선이면 `--no-sha256`(노출당 ~2초 절약; provenance 약화 트레이드오프).
5. 보관 용량이 부담이면 fpack 타일 압축을 후속 검토(D-007 후속 항목).

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| 설계 문서 | `KMT_CEU_L1_Preproc_Pipeline_Design_v1.6.md` (구판 v1.5 병존) |
| L0 데이터 규격 (keyword/ICD) | `../mef_fits_spec/README.md` |
| L0 변환기 | `../mef_converter/README.md` |
| 기술 결정 기록 (D-006~D-008 및 개정: L1 단위/구조/종점/astrometry) | `../project_management/governance/DECISION_LOG.md` |
| Calibration 추적 | `../project_management/science/CALIBRATION_TRACKER.md` |

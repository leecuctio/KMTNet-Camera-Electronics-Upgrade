# SOP: MEF Converter 실행 (Archon MK/NT → L0 64-amp MEF)

최종 갱신일: 2026-09-15

## 목적

KMT-CEU Archon MK/NT raw FITS 쌍을 L0 64-amplifier raw MEF로 변환하는 표준 실행 절차를 정의한다.
대상 스크립트: [`mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py)

| 항목 | 값 |
| --- | --- |
| Software version | v2.4.0 |
| Product version (`PRODVER`) | v2.1.1 |
| Geometry version (`GEOMVER`) | `CEU-L0AMP-v2.1` |
| 출력 HDU 구성 | PRIMARY + 64 amp image + `AMPINFO`/`XTALKINFO`/`VOLTINFO`/`TELEMETRY` = 69 |

세부 옵션/배경은 [`mef_converter/README.md`](../../mef_converter/README.md)와 [`README_KMT_CEU_L0AmpRaw_Converter_v2.1.1.md`](../../mef_converter/README_KMT_CEU_L0AmpRaw_Converter_v2.1.1.md) 참조. 이 SOP는 "무엇을 어떤 순서로 실행/점검하는가"만 다룬다.

## 사전 확인

- [ ] repo 루트 기준으로 실행한다 (상대경로 예제는 모두 repo 루트 기준).
- [ ] Python3 + NumPy 사용 가능 (converter는 순수 Python + NumPy, 독립형 FITS writer).
- [ ] 입력 MK/NT 쌍이 존재한다: `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits` (`SITE` ∈ `KMTC`/`KMTS`/`KMTA`/`KMTK`). MK 또는 NT 중 하나만 있어도 짝 파일을 파일명으로 자동 탐색하므로, 최소한 한쪽은 있어야 한다.
- [ ] 대용량 raw/생성 FITS는 git 추적 대상이 아니다(`.gitignore`) — 로컬 `raw/` 아래에서 다룬다 (검증용 샘플: `raw/science/KMTN.20260116.000001.{MK,NT}.fits`, D-011 이전 명명).
- [ ] 출력 파일을 덮어써야 하면 `-f/--force`가 필요함을 인지한다.

## 절차

### 1. 기본 변환 실행

```bash
python3 mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  <입력 MK 또는 NT 파일> \
  -o <출력 경로>.ceu.l0amp.mef.fits \
  -f --gzip
```

예: 저장소에 있는 검증 샘플로 실행

```bash
python3 mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  raw/science/KMTN.20260116.000001.MK.fits \
  -o kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits \
  -f --gzip
```

또는 예제 스크립트(입력/출력 기본값은 repo 루트 기준, 인자로 override 가능):

```bash
bash mef_converter/run_kmt_ceu_l0amp_example.sh [입력파일] [출력파일]
```

옵션 요약:

| 옵션 | 의미 |
| --- | --- |
| `-o`, `--output` | 출력 L0 MEF FITS 경로 |
| `-d`, `--outdir` | `--output` 생략 시 출력 디렉토리 |
| `-f`, `--force` | 기존 출력 파일 덮어쓰기 |
| `--gzip` | `.fits.gz` 압축본 + SHA256 파일도 생성 |
| `--ampchar` | amp별 실측 GAIN/RDNOISE/SATURAT/LINMAX 주입 (2단계 참조) |

### 2. (해당 시) amp별 실측 GAIN/RDNOISE 주입 — `--ampchar`

cam_char 캠페인 결과 CSV가 있으면(`cam_char/results/amp_characterization_*.csv` 스키마), 취득 SW가 아니라 **이 변환 단계**에서 실측값을 스탬핑한다 (2026-08-22 운영자 확정: gain/noise는 raw 미기재 · L0 재량 · L1 필수).

```bash
python3 mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py \
  <입력 MK 또는 NT 파일> -f \
  --ampchar cam_char/results/amp_characterization_<사이트-일자>.csv
```

amp extension header와 `AMPINFO` 테이블 양쪽에 반영되고, 값이 없거나 ≤0인 amp는 placeholder를 유지한다. primary `AMPCHAR` 카드에 사용한 테이블명이 기록되므로, 산출물 점검 시 이 카드로 실측값 적용 여부를 확인할 수 있다.

### 3. 산출물 확인

정상 실행 시 아래 파일들이 생성된다 (출력 경로가 `OUT`일 때):

| 파일 | 내용 |
| --- | --- |
| `OUT` | 변환된 L0 MEF FITS |
| `OUT.summary.txt` | HDU 레이아웃, 기하 파라미터, 파일 크기, SHA256 요약 (converter가 자동 생성) |
| `OUT.gz` (`--gzip` 지정 시) | gzip 압축본 |
| `OUT.gz.sha256.txt` (`--gzip` 지정 시) | 압축본 SHA256 |

`OUT.summary.txt`를 열어 다음을 확인한다:
- [ ] Output layout이 `PRIMARY, M01T..M08T, K01T..K08T, N01T..N08T, T01T..T08T, AMPINFO, XTALKINFO, VOLTINFO, TELEMETRY` 순서와 일치
- [ ] `RAWNAX1/RAWNAX2`, `RAWXTILE` 등 기하 파라미터가 기대값과 일치
- [ ] 파일 크기가 비정상적으로 작지 않음 (0 또는 수십 KB면 변환 실패 의심)

### 4. 무결성/구조 검증

```bash
python3 - <<'PY'
from astropy.io import fits

path = "kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits"
with fits.open(path, memmap=False) as hdul:
    hdul.verify("exception")
    print("verify ok")
    print("HDU count =", len(hdul))
    print("first HDUs =", [h.name for h in hdul[:6]])
    print("last HDUs =", [h.name for h in hdul[-4:]])
    print("M01T shape =", hdul["M01T"].data.shape)
    print("AMPINFO rows =", len(hdul["AMPINFO"].data))
    print("XTALKINFO rows =", len(hdul["XTALKINFO"].data))
    print("VOLTINFO rows =", len(hdul["VOLTINFO"].data))
    print("TELEMETRY rows =", len(hdul["TELEMETRY"].data))
PY
```

기대값: `verify ok`, `HDU count = 69`, `M01T shape = (4616, 1200)`, `AMPINFO rows = 64`, `XTALKINFO rows = 4096`, `VOLTINFO rows = 9`, `TELEMETRY rows = 2`.

스케일 키워드(`BZERO`/`BSCALE`) 때문에 image data를 다시 읽을 때는 항상 `memmap=False` 또는 `do_not_scale_image_data=True`를 사용한다.

`--gzip`을 지정했다면 압축본도 점검한다:

```bash
gzip -t kmta.20260116.000001.ceu.l0amp.v2_1_1.mef.fits.gz && echo "gzip -t = ok"
```

### 5. 산출물 정리

- [ ] 위 검증 4단계를 모두 통과하면 산출물을 의도한 위치(`raw/science/` 등)에 보관하고, 배포/공유가 필요하면 `.gz` + `.sha256.txt`를 함께 전달한다.
- [ ] 검증 실패 시 원본 raw 쌍과 실행 로그를 보존한 채로 문제 해결 절차(아래)로 넘어간다. 실패한 산출물을 그대로 downstream(전처리 파이프라인 등)에 넘기지 않는다.

## 문제 해결

| 증상 | 확인 사항 |
| --- | --- |
| 짝 파일(MK/NT)을 못 찾음 | 파일명이 `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK\|NT>.fits` 규칙과 정확히 일치하는지, 같은 디렉토리에 있는지 확인 |
| 출력 파일이 이미 존재해서 실패 | `-f/--force` 지정 여부 확인 (의도치 않은 덮어쓰기가 아닌지 먼저 확인) |
| `hdul.verify("exception")`에서 예외 발생 | 입력 raw 쌍 자체의 손상 여부, converter 버전(`SOFTWARE_VERSION`)이 이 SOP 기준과 같은지 확인 |
| `--ampchar` 적용 후 값이 placeholder로 남음 | CSV의 해당 amp 행 값이 비어있거나 ≤0인지 확인 (의도된 동작) |
| gzip -t 실패 | 디스크 공간/중단된 실행 여부 확인 후 재실행 |

## 관련 문서

| 문서 | 위치 |
| --- | --- |
| Converter 개요/디렉토리 구조 | `../../mef_converter/README.md` |
| Converter 상세 옵션/검증 이력 | `../../mef_converter/README_KMT_CEU_L0AmpRaw_Converter_v2.1.1.md` |
| MEF 데이터 규격 (keyword/ICD) | `../../mef_fits_spec/README.md` |
| L0→L1 전처리 파이프라인 | `../../mef_pipeline/README.md` |
| Calibration 추적 (`--ampchar` 입력 CSV 출처) | `../science/CALIBRATION_TRACKER.md` |
| Release 점검 | `../release/RELEASE_CHECKLIST.md` |
| 기술 결정 기록 | `../governance/DECISION_LOG.md` |

## 개정 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-09-15 | 최초 작성 (v2.4.0 / PRODVER v2.1.1 기준) |

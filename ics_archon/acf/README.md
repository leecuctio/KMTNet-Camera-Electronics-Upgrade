# Archon 설정 파일 (`.acf`)

컨트롤러에 올리는 **설정·타이밍 정본**이다. 취득 스크립트가
`CLEARCONFIG` → `WCONFIG`(전 줄) → `APPLYALL` 순으로 그대로 밀어 넣는다
(`../scr_labtest/README_labtest.md`).

벤치에서는 `~/AIC/Config/acf/` 에 두고, 스크립트의 `UNIT_ACF_SCI_NORMAL` 이
`../Config/acf/…` 로 가리킨다.

## 목록

| 파일 | 유닛 | `TAPLINES` | `BIGBUF` | **저장** 픽셀/탭 × 줄 | IP |
|---|---|---:|---:|---|---|
| `KMTC_SCI_101_STA0284_R2608_MK.acf` | CTIO science 1 (MK) | 33 | 1 | **1200** × 4700 | `.101` |
| `KMTC_SCI_102_STA0285_R2608_NT.acf` | CTIO science 2 (NT) | 33 | 1 | **1200** × 4700 | `.102` |
| `KMTS_SCI_101_STA0286_R2608_MK.acf` | SAAO science 1 (MK) | 33 | 1 | **1200** × 4700 | `.101` |
| `KMTS_SCI_102_STA0287_R2608_NT.acf` | SAAO science 2 (NT) ⭐ **2026-09-03 반입** | 33 | 1 | **1200** × 4700 | `.102` |
| `KMTK_SCI_113_STA0200_R2608_MK.acf` | KASI 시험 유닛 (MK) | **32** | 1 | **1200** × 4700 | `.113` |
| `KMTK_SCI_113_STA0200_R2608_NT.acf` | KASI 시험 유닛 (NT) | 33 | 1 | **1200** × 4700 | `.113` |
| `KMTK_GUI_162_STA0201_R2614.acf` | KASI guide ⭐ **현행 유일본** | 9 | **0** | **528** × 1033 | `.162` |

⚠️ **이 열은 `PIXELCOUNT` × `LINECOUNT` 다 -- 타이밍 파라미터가 아니다.**
바로 아래 절이 그 둘을 가른다.  ⚠️ **v1.7 까지 이 열은 타이밍 쪽 값
(`Pixels=1201`/`600`)을 싣고 있었다** (2026-08-29 정정).

⚠️ **구 `KMTT_SCI_113…` 2장은 폐기했다** (2026-08-27, 운영자) — `KMTT` 는
**D-017 에서 폐지된 사이트 코드**이고, `KMTK_…` 가 그 개명본이다(내용 동일함을
대조로 확인). 되살릴 일이 있으면 git 이력에 있다.

## ⚠️ 읽는 픽셀 수와 **저장되는** 픽셀 수가 다르다 (2026-08-29 확인)

**타이밍 파라미터 `Pixels` 는 시퀀서가 몇 개를 디지타이즈하나이고, 프레임에 실제로
담기는 것은 `PIXELCOUNT` 다.**  Archon GUI 에서는 **CDS/Deint 탭의 "Pixels per
Tap"** 이 그 값이다 (운영자 확인 2026-08-29).

| | 시퀀서가 디지타이즈 | **프레임에 저장** | 버려짐 |
|---|---:|---:|---:|
| guide (현행 **R2610**) | `Pixels=540` + 1 = **541** | `PIXELCOUNT=`**528** | **13** |
| guide (구 R2609) | `Pixels=600` + 1 = 601 | `PIXELCOUNT=`528 | 73 |
| science | `Pixels=1201` + 1 = **1202** | `PIXELCOUNT=`**1200** | 2 |

⚠️ **아래 `LINE<n>` 은 전부 guide 기준이다** -- science 는 같은 번호에 다른 줄이
있다(guide `LINE43`↔science `LINE57`, `44`↔`58`, `47`↔`61`).  판을 안 밝히면
조용히 틀린 독해가 된다.

    LINE43  LCLK;   CALL SkipPixelFirst(PreSkipPixels)    8   버리며 지나감(디지타이즈 안 함)
    LINE44  RGHIGH; CALL PixelFirst(Pixels)             540   디지타이즈  (구 R2609: 600)
    LINE45  RGHIGH; CALL SkipPixelFirst(PostSkipPixels)   0
    LINE46  RGHIGH; CALL PixelFirst(OverscanPixels)       0
    LINE47  RGHIGH; CALL PixelFirst                       1   ← 인자 없는 호출 = 1개 더

**그래서 저장 영상은 채널(탭)당 528 컬럼**이고, guide 프레임 전체는
**8탭 × 528 = `NAXIS1=4224`**, `NAXIS2=1033` 이다.  science 는 16탭 × 1200 =
`NAXIS1=19200`, 2 × 4700 = `NAXIS2=9400` (`../ics_archon.ini` 의 `naxis1`/`naxis2`).

**근거가 셋 일치한다** -- ① ACF 의 `PIXELCOUNT` ② Archon GUI 의 "Pixels per Tap"
③ **`gmon` v2 의 실측 7장**(`main` 브랜치, `gmon/DESIGN.md` 2절: "`NAXIS1=4224 =
8 세그먼트 × 528컬럼`").

⚠️ **구 R2609 의 73 은 science 의 여유 2 와 성격이 달랐다** -- science 쪽은
파이프라인 flush 여유인데 guide 는 73개를 클록해 놓고 버렸다(픽셀 클록 구간의 약
12%).  보관본까지 대조하면 **여섯 판이 전부 600/528 로 같아서** 최근에 잘못 건드린
것이 아니라 STA 초안부터 그랬다.  ⭐ **R2610 에서 13 으로 줄였다** (2026-09-03,
아래 "왜 600 인가" · "`Pixels` 여분은 몇이어야 하나" 절).

### 73개가 어디에 있는 전하인가 -- 데이터시트가 계산을 닫는다 (2026-09-01)

규격 9.4절(v1.9)이 CCD47-20 독출 레지스터 **절반**의 구성을 적어 두었다
(데이터시트 p.8 line output format · p.4):

    8 BLANK | 15 DARK REFERENCE | 1 transition | 512 active   =  536 소자

ACF 와 자리마다 맞는다 -- **여유가 0 이다**:

| 데이터시트 | ACF | |
|---|---|---|
| `8 BLANK` (비감광 레지스터 소자) | `PreSkipPixels=8` | 건너뜀 |
| `15 DARK REF + 1 transition + 512 active` = **528** | `PIXELCOUNT=528` | **저장** |
| (레지스터 끝) | 구 R2609 `Pixels=600`+1 → 클록 609 | 73 초과 |
| 〃 | **현행 R2610 `Pixels=540`+1 → 클록 549** | **13 초과** |

⭐ **그래서 그 초과분은 레지스터의 물리적 끝을 지난 자리다** -- CCD 전하가 있을 수
없는 구간을 디지타이즈해서 버린다.  P-k 항목(2026-08-29)과 이 데이터시트 대응
(v1.9, 2026-08-30)은 **따로 적혀 있었는데**, 붙여 보면 무손실 트림이 거의
확정이다.  바이트 비교는 확인 절차이지 미지수를 푸는 실험이 아니다.

⚠️ 이 대응은 **저장 창이 앞 528 임을 함의한다** -- 뒤 528 이었다면 다크 기준열이
프레임 선두에 안 오고, 그것은 `gmon` v2 실측·규격 9.4절 배치와 어긋난다.

### 시간으로 얼마인가 (2026-09-01, `acftiming` 계산)

| `Pixels` | 독출 | 최소 프레임 주기(하한) | 절약 |
|---:|---:|---:|---:|
| 600 (구 R2609) | 1367.8 ms | 1.3746 s | -- |
| **540** (현행 R2610) | **1243.9 ms** | **1.2506 s** | **124.0 ms** |
| 529 | 1221.1 ms | 1.2279 s | 146.7 ms |
| 528 | 1219.1 ms | 1.2258 s | 148.8 ms |

픽셀당 199틱(1.99 µs).  600→528 **전 구간**을 트림하면 프레임당 148.8 ms(독출의
10.9%)이고, 채택한 600→**540** 은 그중 **124.0 ms(9.1%)** 다.

⚠️ **평상시에는 시간이 절약되지 않는다.**  시퀀서 pacing 이라(DevNote 9.12)
`EXPTIME` 을 고정하면 독출이 줄어든 만큼 `IntMS` 가 늘어 **주기도 신호도 그대로**
다.  움직이는 것은 **하한 하나**다 -- 실익은 "1.251 초보다 빠른 가이딩이 필요한가"
에만 걸린다.  레거시 실측은 `guideexp 10`(10초)이었다.

⏳ **`Pixels` 트림은 실기 시험 항목이다** (P-k, 운영자 2026-08-29).
판정법은 **같은 조건에서 두 값으로 프레임을 찍어 바이트 비교** -- 같으면 저장 창이
앞 528 이고 무손실이다.  ⚠️ **줄이더라도 `LINE47` 의 인자 없는
`CALL PixelFirst`(+1)는 남길 것** -- 그것이 flush 여유다.

⚠️ **종전 권고 `Pixels=529`(여유 2, science 관례)는 2026-09-03 문헌 조사로
대체됐다** -- 정본은 아래 "`Pixels` 여분은 몇이어야 하나" 절이고 **채택값은
540(여분 13)** 이다.  트림은 ACF 개정이라 판 번호가 오르고 규격 4.3절의
`CTRLnCFG` 범프 사유가 된다.

### 왜 600 인가 -- overscan 을 얻던 값의 잔재다 (2026-09-03, 운영자 기록)

⭐ **STA 초안은 `Pixels=600` 과 함께 `PIXELCOUNT=600` 이었고, 600 은 serial
overscan 72 를 담기 위한 값이었다.**  overscan 을 폐지할 때 `PIXELCOUNT` 만
528 로 내렸고 `Pixels` 는 남았다 -- 그래서 지금 73 을 헛돈다 (운영자 기록).

| | `Pixels` | 디지타이즈 | `PIXELCOUNT` | 저장 내역 | 미기록 = 레지스터 초과 |
|---|---:|---:|---:|---|---:|
| STA 초안 | 600 | 601 | **600** | 16 + 512 + **OS 72** | 1 (초과는 73) |
| 구 R2609 | 600 | 601 | 528 | 16 + 512 | **73** |
| **현행 R2610** | **540** | 541 | 528 | 16 + 512 | **13** |
| 트림 | ? | ?+1 | 528 | 16 + 512 | **?+1-528** |

⭐ **overscan 을 저장하지 않으면 "미기록" 과 "레지스터 초과" 가 한 수로 합쳐진다**
-- 노브가 하나다.  하한은 `Pixels >= 527`(레지스터 536 을 다 쓸고, 저장 528 을
채우는 두 제약이 같은 수로 떨어진다).  ⭐ **여유를 얼마로 둘지는 문헌 조사로
닫았다**(아래 절) -- 여유를 1 에서 13 으로 늘리는 값이 **24.8 ms** 뿐이라 넉넉히
잡는 비용이 싸다.

⚠️ **`HorizontalShift(600)` 은 이 트림과 무관하다.**  스크립트는 **트랜스퍼
경로에 리터럴을, 독출 경로에 파라미터를** 쓰고 값이 우연히 같을 뿐이다:

| 스크립트 | 성격 | 닮은 파라미터 | 바닥 |
|---|---|---|---:|
| `LINE11 FrameShift(1033)` | 리터럴 | `Lines=1033` | store 구간 행수 1033 |
| `LINE12`·`LINE53 HorizontalShift(600)` | 리터럴 | `Pixels=600` | 레지스터 536 |
| `LINE15 Line(Lines)` · `LINE44 PixelFirst(Pixels)` | 파라미터 | -- | -- |

`HorizontalShift` 를 바닥(536)까지 깎아도 프레임당 **42.9 µs**(하한의 0.003%)라
ACF 개정 비용을 못 갚는다.  ⚠️ `Pixels` 트림과 **묶어서 개정하지 말 것** --
P-k 판정법이 "같은 조건에서 두 값으로 찍어 바이트 비교" 라 두 값을 함께 바꾸면
차이의 원인을 못 가른다.

⚠️ **`Pixels` 트림은 P-k(실기 시험 항목)이고 규격 OI-20 과 물려 있다** -- 트림
전후 바이트가 같으면 저장 창이 앞 528 임이 확정되고, 규격 10.3절의 `OVRSCNX=16`
귀속이 실측으로 뒷받침된다.  ⚠️ 규격 v1.9 의 OI-20 은 아직 `600->528` 로 적혀 있다 -- **확정값은 540**
이므로 raw spec 다음 판올림 때 갱신해야 한다(규격 판올림 주기가 따로 있어
여기서는 고치지 않는다).

⚠️ **Y축 9행도 같은 부류의 미결이다 (OI-21).**  운영자 관측(2026-09-03)은
"맨 앞 1행 blank · 뒤쪽 ~7행이 bias/dark" 인데, 규격 10.3절은 `PRESCNY=0`/
`OVRSCNY=9`(전부 뒤쪽) 이고 `gmon.conf` 는 `y_trim_bottom=9`/`y_trim_top=0`
(배열 앞에서 9행 절단)이라 **양쪽 다 어긋난다.**  gmon·규격 소관이라 여기서는
기록만 남긴다.

### `Pixels` 여분은 몇이어야 하나 (2026-09-03 문헌 조사)

**벤더는 여분 직렬 클록 수를 규정하지 않는다** -- 요구는 시간뿐이다(직렬 정지 ->
병렬 시작 `t_dri` min 1 µs, 데이터시트 p.8).  레지스터를 비우는 벤더 수단은 여분
클록이 아니라 **DG 덤프 게이트**다(FEATURES "Gated Dump Drain on Output
Register" · pin 26).

여분이 필요한 진짜 이유는 **CTI 지연전하**다.  직렬 트랩은 빠르게 방출된다 --
첫 이송에서 **50~60%**(HST ACS/WFC, arXiv:2602.02844), 시정수 **τ = 0.5~1.5 µs**
(LSST ITL, arXiv:2001.03223 §3) = 우리 픽셀주기 1.99 µs 로 **0.25~0.75 픽셀**.
CCD47-20 직렬 CTI 는 **7×10⁻⁶/전송**(데이터시트 p.2 note 5).
⚠️ 레지스터를 안 비운 채 병렬 이송하면 **잔류 전하가 다음 행과 더해진다** --
그것이 곧 수직 비닝의 구현 방식이다(onsemi AND9187/D).

| N (536 초과 클록) | 근거 |
|---:|---|
| 0 | 산술 하한 -- 512번째 active 가 클록 536 에 출력단 도달 |
| 1 | Archon/STA 템플릿 관례 (인자 없는 `CALL PixelFirst` 하나) |
| **8~16** | ⭐ **문헌 권고** -- τ 의 12~36배라 클록 정지 시점 트랩 잔여 ≈ 0 |
| **13** | ⭐⭐ **채택 (운영자 확정 2026-09-03)** -- 권고 구간 안.  `Pixels=540` |
| 16~32 | 여분을 **저장**해 EPER 로 CTI 를 감시할 때 (실무 오버스캔 밴드 20~64) |
| 73 | 현행.  근거 없음 (overscan 잔재) |

⭐⭐ **`Pixels=540` (N=13) 으로 확정** (운영자 2026-09-03).  `PIXELCOUNT` 은
**528 그대로**이고, 저장되는 528 픽셀은 소자도 순서도 그대로라 **FITS 폭·픽셀
매핑·다운스트림에 영향이 없다.**

| `Pixels` | 클록/행 | N | 디지타이즈 | 저장 | 버림 | 독출 | 프레임 하한 | 절약 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 600 (구 R2609) | 609 | 73 | 601 | 528 | 73 | 1367.8 ms | 1.3746 s | -- |
| **540 (현행 R2610)** ⭐ | **549** | **13** | 541 | 528 | 13 | **1243.9 ms** | **1.2506 s** | **124.0 ms** |
| 528 (최소 관례) | 537 | 1 | 529 | 528 | 1 | 1219.1 ms | 1.2258 s | 148.8 ms |

⚠️ **트림하면 ACF 개정이다** -- 판 번호가 오르고 규격 4.3절의 `CTRLnCFG` 범프
사유가 된다.  N 을 13 에서 1 로 더 깎아도 **25 ms** 뿐이라 여유를 사는 값이 싸다.

⚠️ **바꾸는 것은 `Pixels` 하나뿐이다** -- `PIXELCOUNT`(528) · `PreSkipPixels`(8) ·
`HorizontalShift(600)` 은 그대로다.  ⚠️ **클록 파형(DG 등)을 같이 손대지 말 것**
-- P-k 판정법이 "같은 조건에서 두 값으로 찍어 바이트 비교" 라 두 가지를 함께
바꾸면 차이의 원인을 못 가른다.  같은 루틴의 `CLAMP; X(10000)` 이
라인당 100 µs = **프레임당 103 ms** 를 쓰므로 속도를 더 원하면 그쪽이 굵은
표적이다 -- ⚠️ 다만 프리앰프 정착 시간이라 실측 없이 건드리지 말 것.

⚠️ **`HorizontalShift(600)` 의 600 은 건드리지 말 것.**  그것은 레지스터 **전체
플러시**라 `>=536` 이어야 한다 (프레임 전송 중 저장부에서 밀려든 전하를 여기서
쓸어낸다).  `Pixels` 를 고칠 때 `600` 을 grep 으로 싸잡아 바꾸면 사고가 난다.

⏳ **문헌으로 확정 못 하는 것 -- CCD47-20 자신의 직렬 τ** (공개 실측 0건.  위
τ 는 LSST ITL 값, 50~60% 는 HST ACS/WFC 값이다).  ⭐ **실측법**: 타이밍을 전혀
안 건드리고 `PIXELCOUNT` 만 601 로 올리면 디지타이즈 601 이 전부 파일에 남는다
(1~15 다크기준 · 16 전이 · 17~528 active · **529~601 = 레지스터를 지난 꼬리**).
지수 적합으로 τ 가 나오고 N 이 계산으로 확정된다.  ⚠️ 값 변경 뒤에는 바이어스·
다크 **재취득 필수** -- 라인 끝 클록 이력이 바뀌면 준위가 미세하게 움직일 수 있다.

⭐ **⏳ 로 남겨 두었던 "STA 에 물어볼 항목" 은 위 운영자 기록으로 닫혔다.**
종전에 여기 적었던 두 가설(회로 안정화 / `HorizontalShift(600)` 를 옮겨 적은
흔적)은 둘 다 아니었다.

⭐ **blank 8 은 저장에 못 들어간다 -- `SkipPixel` 에 `PCLK` 가 없다.**
`SkipPixel`/`SkipPixelFirst` 는 `Pixel`/`PixelFirst` 와 **두 줄만 다르고**
(`PCLK`·`NOPCLK` 자리가 `X`·`X`), `PCLK` 는 guide 스크립트 전체에서 그 두 줄뿐이다.
즉 `PreSkipPixels=8` 은 전하를 레지스터에서 밀어내기만 하고 프레임 버퍼에는
넣지 않는다.  science 도 같은 구조다(`PreSkipPixels=27` = prescan 27, 규격
`PRESCNX=0`).

⭐ **앞 16 은 overscan 이 아니라 다크 기준열이다** -- 차광된 실제 CCD 컬럼
(다크 기준열 15 + transition 1)이고, science 의 prescan 27(비감광 레지스터
소자)과 성격이 다르다.  헤더는 그 16 을 `OVRSCNX` 에 귀속한다(규격 10.3절,
운영자 확정 -- 성격이 다크 기준열이라 comment 에 병기).  독출 순서로는 항상
앞이고, 이미지 컬럼으로는 좌/우 채널이 거울이다.  ⚠️ 그래서 `Pixels`/
`OverscanPixels` 로 16 을 가르는 것은 안 된다 -- 시퀀서 관점에선 순서가
거꾸로고, 이미지 관점에선 채널마다 위치가 갈려 파라미터 하나로 표현이 안 된다.

원전: [`../../raw_fits_spec/__reference/CCD47-20.pdf`](../../raw_fits_spec/__reference/CCD47-20.pdf)
(e2v A1A-CCD47-20 Issue 7, 2003-04 -- p.8 line output format · p.4).

⚠️ **"600 중 어느 528 인가" 는 `gmon` 과 공유하는 물음이다.**  `gmon/DESIGN.md`
10절이 "채널당 16컬럼(528−512)의 성격(프리스캔/다크 기준열)"을 커미셔닝 확인
항목으로 올려 두었다 -- 같은 답을 두 문서가 기다린다.

⭐ **`gmon` 은 이미 가정을 선언해 두었다** (`main` 브랜치 `gmon/gmon.conf`
`[geometry]`).  소비자 쪽의 현행 전제이므로 guide raw 규격을 세울 때 **이것과
어긋나면 분할이 깨진다**:

    raw_nx = 4224 · raw_ny = 1033 · nseg = 8 · seg_width = 528
    left_active  = 16,528     왼쪽 채널: 앞 16 컬럼이 비활성
    right_active = 0,512      오른쪽 채널: 뒤 16 컬럼이 비활성
    y_trim_bottom = 9         추가 9행은 아래쪽으로 가정

즉 **16 컬럼이 채널 쌍의 바깥쪽에 붙는다**는 가정이다.  ⭐ 그것이 **규격 4.1절의
science X overscan 패턴(`RRRRLLLL`, side varies)과 같은 부류**다 -- science 는
`AMPNAX1 = 1200 = PRESCNX(0) + IMAGEX(1152) + OVRSCNX(48)` 이고 prescan 을 아예
기록하지 않는다(`rawhdr.py`).  guide 528 = 16 + 512 도 같은 모양으로 읽힌다.
**두 계통이 같은 규범을 따르는 것이 자연스럽고, 그러면 guide 규격은 science 의
자리 잡는 방식을 그대로 물려받으면 된다** -- 다만 아직 실측 확정은 아니다.

⭐ 그리고 **`AMPNAX1`/`AMPNAX2` 가 곧 `PIXELCOUNT`/`LINECOUNT` 다** (1200 / 4700).
규격이 이미 프레임 버퍼 값을 쓰고 있었다 -- 틀렸던 것은 이 표뿐이다.

## R2614 -- `DGLOW` 가 RG 도 올린다 (2026-09-05, 운영자 물음에서)

    KMTK_GUI_162_STA0201_R2613.acf  ->  ..._R2614.acf   (구판은 archive/)
    STATE13\MOD4 ch4(RGR/RGL):  ,1,1 (keep)  ->  RG_HIGH,1,0 (set)   **차이는 이 필드 하나뿐**

운영자 물음(2026-09-05): *"HorizontalShift 만으로는 output node 가 비워지지 않아서(RG
설정 부재) 글루/블루밍이 생길 수 있다는 거지?  HorizontalShift 중 output node 가
계속 비워지게 할 수 있을 것 같은데."*  -- **맞다, 정상 경로 `LINE12` 에서.**

`SmallIntUnit`(IntUnit/NoIntUnit 의 몸체)이 `RGHIGH;X(11) / RGLOW;X(11)` 로 시작해
S 상으로 끝나므로 적분을 거치면 **RG=LOW** 로 나온다.  그 뒤 `DGHIGH`·`FRAME1~6`·
`DGLOW`·`S1~S3` 상태가 모두 RG 를 keep 이라 `LINE11~13`(FrameShift 6.2 ms +
HorizontalShift(600) 360 µs + CLAMP 100 µs) 내내 RG=LOW 다 -- 600 회 시프트가
**리셋 없는 출력 노드**에 쌓인다.  (IntMS=0·NoIntMS=0 이면 RESET 의 RG_HIGH 가 남아
반대로 도니 **IntMS 에 따라 달라지는 숨은 비일관성**까지 있었다.)

R2614 는 `DGLOW` 상태가 "DG 내림 + **RG 올림**" 이 되게 한다.  그러면 `LINE12` 와
R2613 의 `LINE116`(flush 경로)의 HorizontalShift(600) 이 노드 리셋을 켠 채 돌고 IntMS
의존도 사라진다.  부작용은 못 찾았다 -- 몇백 µs 뒤 `SkipLine`/`Line` 이 어차피
`RGHIGH` 를 걸고, RESET 이 유휴 내내 RG=12 V 를 유지하고 있어 DC HIGH 는 이미 상시
상태다.  DG 는 그대로 내리므로 "Line 독출 전 DG LOW" 조건은 유지된다.

⚠️ **왜 R2613 과 분리했나** -- 이것은 정상 프레임의 **클록 파형 변경**이다.  이 README
의 규칙(클록 파형은 다른 변경과 함께 손대지 말 것)대로 flush 로직(R2613)과 갈라,
벤치에서 R2614 에 문제가 보이면 R2613 으로 물러 어느 쪽인지 가를 수 있게 했다.

### 함께 확인된 것 -- `FRAME6`/`IMAGE6` 가 DG 를 0 V 로 내린다 (⏳ R2615 후보)

`DGHIGH; CALL FrameShift(1033)` 은 DG 를 12 V 로 올려 프레임 시프트 중 레지스터를
덤프 드레인으로 비우려는 뜻인데, **`STATE31\MOD4`(FRAME6) 의 ch6(DG) 필드가 keep 이
아니라 `A_LOW,1,0`(0 V 로 set)** 이다.  그래서 DG=12 V 인 구간은 **첫 행의 FRAME1~5
(~4 µs)** 뿐이고 2~1033 행은 DG=0 V 로 밀려 **레지스터에 store 1033 행분이 그대로
쌓인다.**  `IMAGE6` 도 같다.  STA 원본 R2601 부터 모든 판이 이렇다 -- 상태표 편집
때 S3 열의 `A_LOW` 가 DG 열에 같이 들어간 STA 쪽 실수로 보인다(DG 용 상수 `DG_LOW`
가 따로 있다).

양은 실기 조건에서 무시할 수준이다: CCDTEMP 실측 −100.6 ℃(172.5 K)에서 데이터시트
p.2 note 2 공식으로 5.4e-4~1.1e-3 e/px/s, 보수적 바닥값 0.01 을 두어도 1033 행 합이
유휴 1 h 에 2k~4k(공식) / 37k(바닥값) e⁻ -- full well 80k~120k 아래.  넘치려면 바닥값으로
3 h, 공식으론 20 h 이상 유휴가 필요하다.  진짜 큰 전하는 **돔 열린 유휴의 빛**(image
포화 → ABD 없음(p.5 note 10) → store 까지 블루밍)인데, 그 프레임은 통째로 flush 로
버리므로 자료 피해도 소자 손상 기제도 아니다.

⏳ 고치려면 `STATE31\MOD4` ch6 을 `,1,1`(keep) 로 -- FrameShift 내내 DG 12 V 유지.
**그러나 데이터시트 본문만으로는 DG 가 정적 레지스터를 통째로 덤프하는지(가로 인접
덤프 게이트) R 클록 동반이 필요한지 못 가린다.**  실측 뒤 R2615 로: 암실·저온·유휴
30 min 뒤 시험 ACF 에서 LINE12 를 `DGLOW; X(1)` 로 바꿔(HorizontalShift 생략) 레지스터
잔량이 1 행에 더해져 나오게 하고 FRAME6 ch6 을 A_LOW/keep 두 판으로 찍어 비교.

## R2613 -- flush 프레임이 스크립트 안에 들어갔다 (2026-09-05, 운영자)

    KMTK_GUI_162_STA0201_R2612.acf  ->  ..._R2613.acf   (구판은 archive/)
    LINE1="RESET; IF ContinuousExposures GOTO Continuous"  ->  "RESET; IF FirstFlush GOTO FlushFrame"
    LINE2="X; IF Exposures GOTO Exposure"                  ->  "X; IF ContinuousExposures GOTO Continuous"
    LINE3="X; X(100)"                                     ->  "X; IF Exposures GOTO Exposure"
    LINE4="X; GOTO Start"                                 ->  "X; X(100)"
    LINE5=(빈 줄)                                          ->  "X; GOTO Start"
    LINE113=FlushFrame:                                   (신설)
    LINE114="X; FirstFlush--"
    LINE115="DGHIGH; CALL FrameShift(1033)"               ; t0 -- 첫 저장 프레임의 적분 개시 = DATE-OBS
    LINE116="DGLOW; CALL HorizontalShift(600)"
    LINE117="CLAMP; X(10000)"
    LINE118="NOCLAMP; CALL SkipLine(FlushLines)"          ; store 를 행 단위로 버린다, 2448 회 ≈ Line(1033)
    LINE119="X; GOTO Start"
    LINES=113 -> 120
    PARAMETER0="ContinuousExposures=0"  ->  "FirstFlush=0"      ⛔ 반드시 슬롯 0
    PARAMETER16="ContinuousExposures=0" (신설) · PARAMETERS=16 -> 17

빈 LINE5 를 써서 **LINE6 이하 번호는 밀리지 않았다** -- `acftiming` 형태 검사(`LINE11`·
`12`·`47`·`48`)와 `skipline_ticks` 가 보는 `LINE52~55` 가 그대로다.  `_SHAPE` 에는
`LINE1`·`LINE118` 이 추가돼 **R2612 이하 판을 R2613+ 호스트가 만나면 걸러낸다.**

### 무엇을 하나 (규격 10.1-2 · 10.1-3)

호스트가 GO 에 `Exposures=n` + `FirstFlush=1` (+ `IntMS`) 을 **한 LOADPARAMS** 로 건다.
코어는 유휴 루프 첫 줄에서 `FirstFlush` 를 보고 `FlushFrame` 으로 뛴다: 플래그를 깎고,
**`IntUnit` 없이 곧바로 `FrameShift`** (이 개시 순간이 첫 저장 프레임의 적분 개시 =
`DATE-OBS`), 레지스터를 쓸고, `SkipLine` × `FlushLines` 로 store 를 행 단위로 버린 뒤
`Start` 로 돌아간다.  이제 플래그는 0 이라 `Exposures` 로 정상 사이클이 `n` 번 돈다.

    go n  =  flush 1회 + 독출 n회 · n장 저장     (v1.10 까지: 독출 n+1 · 첫째 폐기)
    첫 저장 프레임 적분 = FS(flush)+HS+CLAMP+SkipLine(2448)+루프+IntMS+noint
                       ≈ 정상 주기 = FS+HS+CLAMP+Line(1033)+루프+IntMS+noint   (차 −2.71 µs)

⭐ **flush 는 프레임을 만들지 않는다** -- 버퍼에 아무것도 안 남고 컨트롤러 프레임
카운터도 안 는다(SkipLine 에 ADC 샘플 상태가 없다).  호스트가 볼 자료가 없다.
⏳ 이것은 ACF 논리에서 온 추론이고 FW 실측이 아니다 -- 첫 구동에서 `go 1` 뒤 FRAME
증가가 정확히 1 인지 확인한다.

### ⛔ 슬롯 순서 -- 설계 검토가 잡은 blocker

`LOADPARAMS` 는 파라미터를 **첫 슬롯부터 순서대로 하나씩** 적용한다(매뉴얼 p.52).
유휴 루프 한 바퀴가 105 틱(1.05 µs)이라, 플래그를 뒤 슬롯에 두면 `Exposures`(슬롯 1)가
먼저 앉는 순간 코어가 `IF Exposures GOTO Exposure` 로 **flush 없이** 뛰고, flush 는 1·2
번 프레임 **사이**에 끼어 2번 프레임의 실적분이 주기 + 1.25 s 가 된다.  그래서
`FirstFlush` 가 슬롯 0 이고 `ContinuousExposures`(호스트가 어디서도 안 쓴다)가 16 으로
갔다.  잔여 창은 두 LOAD 가 20 ns 안에 잇따르는 경우뿐 -- 실질 0.

### ⛔ 플래그가 설정 메모리에 남는다

`LOADPARAMS`/`LOADTIMING`/`APPLYALL` 은 설정 메모리의 파라미터를 **전부** 다시 태운다.
코어는 `FirstFlush--` 로 자기 값을 깎지만 **설정 메모리는 1 그대로**라, 그 뒤 어떤
LOADPARAMS 든(STOP 의 `Exposures=0` …) 1 을 되살려 **유령 flush**(1.25 s 클록, 프레임
없음)가 돈다.  규칙: **arm 의 LOADPARAMS 한 번에만 실리고, 호스트가 곧바로 설정 메모리를
`FirstFlush=0` 으로 되쓴다**(LOADPARAMS 없이 -- 코어 값은 그대로).  `set_exposures(0)`
도 함께 0 을 쓴다.  가짜 컨트롤러가 이 재점화를 모사해 시험이 잡는다.

### `FlushFrame` 은 서브루틴이 아니다

GOTO 로 들어가 GOTO 로 나가는 코드 블록이다.  **RETURN 을 쓰면 스택이 어긋난다.**  이름이
`…Frame:` 이라 나중에 누가 CALL 로 바꾸기 쉬워 여기 적어 둔다.

### 무엇이 바뀌었나 -- R2611·R2612 의 "굽지 말 것" 이 닫혔다

R2611 은 `FlushLines` 파라미터만, R2612 는 유휴 정지만 있어 flush 스크립트 줄이 없었다.
R2613 이 그 줄이다.  ⏳ **실기에는 R2614 를 굽는다** (R2613 + DGLOW RG).

## R2612 -- 유휴 루프가 클록하지 않는다 (2026-09-05, 운영자)

    KMTK_GUI_162_STA0201_R2611.acf  ->  ..._R2612.acf   (구판은 archive/)
    LINE3="X; CALL SkipLine"        ->  "X; X(100)"     **차이는 이 한 줄뿐**

번호를 밀지 않았으므로 `LINES=113` 도, `acftiming` 의 형태 검사(`LINE11`·`12`·
`47`·`48`)도 그대로다.

### 무엇이 바뀌나

구판의 유휴 루프는 `Exposures` 를 폴링하는 사이사이 **`SkipLine` 을 계속 불렀다**
-- store 1행을 옮기고 직렬 레지스터를 600 번 밀고 ADC 를 clamp/unclamp 하는
일을 ~508 µs 마다 반복했다.  운영자 지시(*"아이들 상태에서는 가만히 있게"*)로
그 자리를 **`X; X(100)`** 으로 바꿨다.

`X` 상태는 **모든 채널이 `keep`** 이다(`STATE1`) -- 클록 드라이버(MOD3·4·11)도
ADM clamp(MOD5·6·8)도 건드리지 않는다.  즉 유휴는 이제 **전기적으로 조용한
상태**다.  1 µs 마다 `Exposures` 만 본다.

⭐ **매뉴얼 자체 예시가 이 꼴이다** (p.79 Basic Examples):

    Start:
    Idle; X(100)
    Clamp; X(2000)
    Idle; X(100)
    Idle; IF !Count GOTO Start

벤더 참조 스크립트도 유휴 중에 CCD 를 클록하지 않는다.  STA 템플릿의 `CALL
SkipLine` 은 선택이었지 요구가 아니었다.

⭐ **목적은 science 독출 시 crosstalk 제거다** (운영자 확정 2026-09-05).  science
영상이 주(主)이고 guide 영상은 노이즈가 좀 있어도 된다 -- guide 클록이 science
독출 구간에 간섭하지 않게 하는 것이 이 변경의 이유다.  ⛔ **science 템플릿의 유휴
`SkipLine` 은 그대로 둔다** -- science 는 유휴 중에도 계속 비워 주는 것이 필요하다
(운영자 확정 2026-09-05).  science 가 피해자 쪽이라 같은 논리가 걸리지 않는다.

### 왜 중요한가 -- `GUIEXPCTRL` 의 약속

ICS 는 science 독출 구간에 guide 클록을 치우려고 `GUIEXPCTRL`(`EXPENABLE=0`)을
보낸다.  ⛔ **그런데 구판에서는 시퀀스를 세워도 유휴 루프가 계속 클록했다** --
`EXPENABLE=0` 뒤 guide 는 "노출은 안 하지만 508 µs 마다 store 를 밀고 ADC 를
clamp 하는" 상태였다.  R2612 에서 그 약속이 처음으로 온전해진다: 진행 중이던
프레임 하나가 끝나면(≤ 한 주기) **그 뒤는 정말 조용하다.**

### 유휴 clamp 는 걱정 없다

매뉴얼 예시는 유휴 중 ADC 를 clamp 한다.  우리는 `X`(keep) 라 유휴 중 clamp
상태를 바꾸지 않는데, 노출 경로가 **독출 전에 스스로 clamp 한다**
(`LINE13 CLAMP; X(10000)` -> `LINE14 NOCLAMP`).  유휴 중 clamp 상태는 자료에
닿지 않는다.

### ⚠️ 트레이드오프 -- store 가 유휴 중 쌓인다

구판의 유휴 `SkipLine` 은 store 를 계속 비워 두는 효과가 있었다.  이제 유휴가
길면 **store 도 image 처럼 전하가 쌓인다.**  노출 개시 때 `FrameShift(1033)` 이
store 의 1033 행을 직렬 레지스터로 밀어 넣고 `HorizontalShift(600)` 이 그것을
버리므로, 자료로는 **첫 프레임(폐기)** 에 들어갈 뿐이다 -- 규격 10.1-2 가 첫
프레임을 버리는 이유가 하나 더 생긴 셈이다.

⏳ **첫 실기에서 볼 것**: 긴 유휴(수십 분) 뒤 첫 노출의 **폐기 프레임**에
블루밍 흔적이 있는지.  1033 행분 전하가 한 레지스터에 몰리면 레지스터 용량을
넘겨 store 컬럼 위로 되밀릴 수 있다 -- 냉각된 CCD 에 돔이 닫혀 있으면 무시할
양이지만, 실측으로 닫아야 한다.

## R2611 -- `FlushLines=2448` 신설 (2026-09-05, 운영자)

    KMTK_GUI_162_STA0201_R2610.acf  ->  ..._R2611.acf   (구판은 archive/)
    PARAMETER15=                    ->  "FlushLines=2448"  **차이는 이 한 줄뿐**

`PARAMETERS=16` 이 이미 빈 15번을 세고 있어서 **개수 선언은 안 건드렸다.**

### 무엇에 쓰나

노출 시퀀스의 **첫 프레임은 버린다** (규격 10.1-2) -- 대기 중 쌓인 전하라
노출 개시 시점이 정의되지 않는다.  버릴 것을 디지타이즈할 이유가 없으므로
`EXPTIME` 을 주지 않고 `SkipLine` 반복으로 비운다.

⛔ **그런데 그냥 빨리 비우면 안 된다.**  flush 가 본 독출보다 빨리 끝나면
**첫 저장 프레임의 실적분이 `EXPTIME` 보다 짧아진다** -- 첫 장만 조용히 어두운
자료가 된다.  그래서 `SkipLine` 횟수를 **본 독출 소요와 같아지도록** 맞춘다.

    본 독출 (Pixels=540, Lines=1033)   1243.9 ms
    SkipLine 1회                        508.11 us   (= 50,811 틱)
    FlushLines = 1243.9 ms / 508.11 us = 2447.6  ->  **2448**   (오차 -2.7 us)

### ⛔ 파생값이다 -- 넷 중 하나만 바뀌어도 다시 계산해야 한다

`FlushLines` 는 **`Pixels`·`Lines`·`AT`·`ST` 에서 나온 값**인데 넷과 같은
파일에 있고 **자동으로 따라가지 않는다.**  고치지 않으면 **오류 없이 첫 저장
프레임의 실적분만 틀린다** -- 가장 나쁜 부류다.

| 무엇이 | 어떻게 | `FlushLines` | 변화 |
| --- | --- | ---: | --- |
| (현행) | `Pixels=540 Lines=1033 AT=100 ST=10` | **2448** | -- |
| `Lines` | 1033 -> n | **정비례** | 1:1 |
| `Pixels` | 540 -> 600 | 2692 | +10 % |
| `AT` | 100 -> 200 | 2419 | -1.2 % |
| **`ST`** | 10 -> 20 | **1433** | **-41 %** |

`AT`(병렬 클록 위상 폭, `IMAGE1..6`/`FRAME1..6` 의 `X(AT)`)와 **`ST`**(직렬
레지스터 클록 위상 폭, `S1LOW`~`S2HIGH` 의 `X(ST)`)가 **같은 방향으로 안
움직이는 이유**: flush 쪽 `SkipLine` 은 `VerticalShift`(AT) + `Horizontal
Shift(600)`(ST) 라 **AT·ST 로만** 결정되는데, 맞출 대상인 본 독출은 디지타이징
`Pixel` 루틴이 대부분이라 `AT`·`ST` 비중이 작다.  그래서 `ST` 를 건드리면
**flush 쪽만 크게** 움직인다.

⭐ **호스트가 검산한다** -- `icg_archon` 이 기동 때 ACF 를 파싱해
`acftiming.check_flush_lines()` 로 대사하고, 어긋나면 **`log.error` 로
소리를 낸다**(`icg_archon/backend.py`).  상수로 두되 조용히 틀리지는 않게
한 것이다.  산수 자체는 `acftiming.flush_lines()` 가 정본이다.

~~⏳ 타이밍 스크립트 쪽은 아직이다~~ → ✅ **R2613 에서 `LINE118 NOCLAMP; CALL SkipLine(FlushLines)` 로 들어갔다.**

⏳ **실측 확인**: 2448 은 `acftiming` **계산값**이지 실측이 아니다 (규격
OI-26).  첫 guide 구동에서 flush 소요와 본 독출 소요를 재어 어긋나면 고친다.

## R2610 -- `Pixels` 를 540 으로 (2026-09-03, 운영자)

    KMTK_GUI_162_STA0201_R2609.acf  ->  ..._R2610.acf   (구판은 archive/)
    PARAMETER5="Pixels=600"         ->  "Pixels=540"    **차이는 이 한 줄뿐**

`Pixels=600` 은 **serial overscan 72 를 담던 값의 잔재**였다 (STA 초안은
`PIXELCOUNT=600`.  overscan 폐지 때 `PIXELCOUNT` 만 528 로 내렸다 -- 운영자
기록).  그래서 레지스터(536)를 **73 개나 지나** 클록하고 있었다.

여분을 **13**(= 549 클록 - 536)으로 줄였다 -- 문헌 권고 8~16 안이다(위
"`Pixels` 여분은 몇이어야 하나" 절).  **최소 프레임 주기 1.3746 -> 1.2506 s**
(-124.0 ms), 독출 1367.8 -> 1243.9 ms.

⚠️ **저장은 한 픽셀도 안 바뀐다** -- `PIXELCOUNT`(528)·`PreSkipPixels`(8)이
그대로라 담기는 528 은 같은 소자·같은 순서다.  FITS 폭·픽셀 매핑·다운스트림
무영향.  ⚠️ `HorizontalShift(600)` 도 그대로다 (레지스터 전체 flush 라
`>=536` 이어야 한다 -- 위 표 참조).

⏳ **실기 확인**: 트림 전후 프레임 바이트 비교(P-k).  같으면 저장 창이 앞
528 임이 확정되고 규격 OI-20 이 함께 닫힌다.  ⚠️ 값 변경 뒤 **바이어스·다크
재취득**.

## R2609 -- `NoIntMS` 를 0 으로 (2026-08-31, 운영자)

    KMTK_GUI_162_STA0201_R2608.acf  ->  ..._R2609.acf   (구판은 archive/)
    PARAMETER3="NoIntMS=500"        ->  "NoIntMS=0"     **차이는 이 한 줄뿐**

`NoIntMS` 는 적분(`IntUnit`) 뒤 **프레임 트랜스퍼 전**에 시퀀서가 무조건
도는 대기다 (타이밍 스크립트 `NOINT; CALL NoIntUnit(NoIntMS)`).  guide 는
셔터가 없어 그 대기가 할 일이 없고, 그만큼이 **최소 프레임 주기에 그대로
얹힌다** -- 1.875 s 에서 **1.375 s** 로 줄었다 (계산: `icg_archon/
acftiming.py`, 경위는 DevNote 9.10·9.12).  `DATE-OBS` 의 트랜스퍼 보정도
507 ms -> **6.8 ms** 가 된다.

⭐ **이름을 함께 올린 이유**: `CTRL1CFG` 카드가 이 파일 이름을 싣는다.
같은 이름으로 타이밍이 다른 두 판이 돌면 **헤더만 보고 못 가린다** --
raw spec 4.3 의 "구성 변경은 `CAMVER`/`CTRLnCFG` 범프로 드러나야 한다" 와
같은 자리다.

⚠️ **STA 확인 대기**: `NoIntMS=500` 이 왜 있었는지 (클록 정착? 의도적
dead time?) 는 저장소에 근거가 없다.  첫 구동에서 이상이 보이면 이 값을
먼저 되돌려 볼 것.

## guide 정본을 하나로 줄였다 (2026-08-28, 운영자)

**넷을 두던 자리에 최종본 하나만 둔다.**  이름도 science 와 같은 규칙으로
맞췄다:

    kmtnet_guide_STA0201_162_R0827_for1259_rtd9cal.acf
      -> KMTK_GUI_162_STA0201_R2608.acf          **내용은 바이트가 같다** (대조 확인)

빠진 셋 — `R0827_for1110_rtd9cal` 하나와 스왑 **전** `_TBC` 판 둘(`R2601_
for1110` · `R2601_for1259`) — 은 지운 것이 아니라
[`../__ref_archon_control/acf/`](../__ref_archon_control/acf/) 로 옮겼다.  그
폴더가 **벤더·실기에서 받은 원본 보관용**이다(운영자 2026-08-28) — 개명 전
`R0827_for1259_rtd9cal` 원본과 현행 science 여섯의 원본, 그리고 다른 guide
유닛(`STA0291`)의 ACF 둘도 함께 있다.

⭐ **ACF 말고 하나가 더 산다 -- 타이밍 스크립트 freeze 사본 둘**(2026-09-03).
그 둘은 **받은 원본이 아니라 ACF 에서 뽑은 파생물**이고, 파일명의 `R<YYMMDD>`
가 그것을 가른다.  아래 "타이밍 스크립트 freeze 사본" 절이 성격을 적는다 --
⚠️ **받은 원본 표에 넣지 말 것**(받은 줄 끝·받은 바이트가 없는 파일이다).

### 보관함 목록과 줄 끝 (2026-09-02 실측 -- 작업 트리 기준)

⚠️ **종전 서술 "그 사본들은 줄 끝이 CRLF(원본 그대로)" 는 뭉뚱그린 것이었다** --
실제로는 **판마다 갈렸다**(`R2601` 계열 = CRLF, GUI 내보내기 / `R0827` 계열 = LF).
⭐ **운영자 지시(2026-09-02)로 보관함도 전부 LF 로 정규화했고**
`.gitattributes` 의 `-text` 예외를 걷었다 -- 그래서 **작업 트리에는 받은 그대로의
줄 끝이 이제 바이트에 없다.**  아래 "받은 줄 끝" 열이 그 기록이다.

⭐ **받은 바이트는 이 저장소 이력에 그대로 있다** -- 정규화 직전 커밋
`e7653cc`(=`febedd2^`)에서 일곱 개 전부 복구된다.  아래 표는 **작업 트리** 기준의
기록이다.

    git show e7653cc:ics_archon/__ref_archon_control/acf/<이름>.acf > /tmp/orig.acf

| 보관함 파일 (`__ref_archon_control/acf/`) | 받은 줄 끝 | 받은 바이트 | 지금(LF) |
|---|---|---:|---:|
| `KMTC_SCI_101_STA0284_R2608_MK.acf` | CRLF | 29,541 | 28,525 |
| `KMTK_SCI_113_STA0200_R2608_MK.acf` | CRLF | 29,528 | 28,513 |
| `KMTK_SCI_113_STA0200_R2608_NT.acf` | CRLF | 29,540 | 28,524 |
| `kmtnet_guide_STA0201_162_R2601_for1110.acf` | CRLF | 29,500 | 28,436 |
| `kmtnet_guide_STA0201_162_R2601_for1259.acf` | CRLF | 29,549 | 28,482 |
| `kmtnet_guide_STA0291_103_R2601_for1259.acf` | CRLF | 29,551 | 28,484 |
| `kmtnet_guide_STA0291_103_goff_R2601_for1259.acf` | CRLF | 29,551 | 28,484 |
| `KMTC_SCI_102_STA0285_R2608_NT.acf` | LF | 28,525 | 28,525 |
| `KMTS_SCI_101_STA0286_R2608_MK.acf` | LF | 28,525 | 28,525 |
| `kmtnet_guide_STA0201_162_R0827_for1110_rtd9cal.acf` | LF | 28,427 | 28,427 |
| `kmtnet_guide_STA0201_162_R0827_for1259_rtd9cal.acf` | LF | 28,475 | 28,475 |
| `KMTK_GUI_162_STA0201_R2608.acf` (2026-09-02 반입) | LF | 28,475 | 28,475 |
| `KMTS_SCI_102_STA0287_R2608_NT.acf` (2026-09-03 반입) | **LF** | 28,525 | 28,525 |

⚠️ **정규화 뒤에는 science 원본 여섯이 전부 정본 `acf/` 사본과 바이트가 같다** --
보관본의 값이 "받은 이름" 하나로 줄었다는 뜻이다(내용으로는 아무것도 안 남긴다).
guide 쪽 넷(`R2601` 계열 둘 · `STA0291` 둘)은 정본에 없는 판이라 그대로 값이 있다.

### 타이밍 스크립트 freeze 사본 둘 (2026-09-03) -- ⚠️ **받은 원본이 아니다**

위 표와 성격이 다르다.  이 둘은 벤더가 준 파일이 아니라 **ACF 의 `LINE<n>=` 키를
풀어 쓴 파생물**이고, 정본 `acf/` 사본이 갱신돼도 이 시점을 얼려 두려고 둔다 --
그래서 "받은 줄 끝"·"받은 바이트" 가 **없다**.

| 보관함 파일 | 판 | 줄 | 지금(LF) | 정본 쪽 짝 |
|---|---|---:|---:|---|
| `acf_timing_script_guide_R210930.txt` | guide | 113 | 1,765 | `acf/acf_timing_script_guide.txt` |
| `acf_timing_script_science_R250826.txt` | science | 137 | 2,137 | `acf/acf_timing_script_science.txt` |

⭐ **파일명의 `R<YYMMDD>` 는 타이밍 스크립트 자체의 최종 수정일**이다(운영자 기록)
-- `R210930` = 2021-09-30 · `R250826` = 2025-08-26.  ⚠️ **ACF 판 번호(`R<YYMM>`)와
다른 계열이다** ("판 표기" 절).  ACF 에는 날짜 필드가 없어 출처는 이 기록 하나다.

**뽑는 절차의 정본은 [`../tools/extract_timing_script.py`](../tools/extract_timing_script.py) 다.**

    python tools/extract_timing_script.py acf/*.acf --check acf/    # 대조
    python tools/extract_timing_script.py acf/*.acf --out acf/      # 다시 뽑기

`tests/test_timing_script_extract.py` 가 정본 `acf/*.acf` 일곱에 대해 같은 대조를
건다 (`archive/`·보관함은 역사적 판이라 범위 밖이다).  ⚠️ 함정 셋은 그 도구의
주석에 있다 -- `^LINE\d+=` 앵커(guide ACF 에 `MOD10\VCPU_LINE*` 109개가 따로 있다) ·
바깥 큰따옴표 한 쌍만 벗김 · **끝 개행 없음**(그래서 `wc -l` 은 112/136 을 내놓고
실제 줄 수는 `LINES=` 와 같은 113/137 이다).

### ⭐ 2026-09-02 반입분 -- **이미 있는 바이트의 사본**이다

운영자가 보관함에 하나를 더 넣었다.  **새 내용은 없고**, 새로 남는 것은 *이름의
대응*이다 -- 지우기 전에 아래를 볼 것.  (⚠️ **종전에 "반입분 둘" 로 적고
`acf_timing_script.txt` 를 여기 넣었던 것은 틀렸다** -- 그 파일도 받은 것이
아니라 ACF 추출본이었다.  2026-09-03 정정, 위 freeze 절로 옮겼다.)

    KMTK_GUI_162_STA0201_R2608.acf   = kmtnet_guide_STA0201_162_R0827_for1259_rtd9cal.acf  (같은 폴더)
                                     = ../../acf/archive/KMTK_GUI_162_STA0201_R2608.acf
                                       sha256 d710ffae26e6...  28,475 B  LF

⭐ **개명 대응이 보관함 안에서 자립한다** -- 종전에는 "원본은 `R0827_for1259...`,
정본은 `KMTK_GUI_162...`" 라는 대응이 **이 README 에만** 있었고 보관함만 보면 알 수
없었다.  이제 같은 바이트가 두 이름으로 나란히 있어 폴더 자체가 그 대응을 증언한다.

⚠️ **바이트가 같은 묶음** (한쪽을 "중복" 으로 지우면 대응이 끊긴다):

| 같은 바이트를 가진 자리 |
|---|
| `acf/archive/KMTK_GUI_162_STA0201_R2608.acf` · 보관함 `KMTK_GUI_162_STA0201_R2608.acf` · 보관함 `kmtnet_guide_STA0201_162_R0827_for1259_rtd9cal.acf` (sha256 `d710ffae26e6`) |
| `acf/<이름>.acf` ↔ 보관함 `<같은 이름>.acf` -- **science 여섯 전부** (정규화 뒤) |
| `acf/acf_timing_script_guide.txt` ↔ 보관함 `acf_timing_script_guide_R210930.txt` (1,765 B) |
| `acf/acf_timing_script_science.txt` ↔ 보관함 `acf_timing_script_science_R250826.txt` (2,137 B) |

⚠️ **`archive/` 는 여전히 필요하다** — 거기 있는 `R2601_…_rtd9cal` 둘은
**limit 정정 전** 판이고, 그 내용은 `__ref_archon_control/acf/` 에 없다.  둘을
같은 것으로 보고 지우지 말 것.

⭐ **판 번호가 이제 규칙에 맞는다.**  `R0827` 은 `MMDD` 라 `YYMM` 규칙의
예외였고 **숫자로 정렬하면 구판보다 앞에 왔는데**(0827 < 2601), `R2608` 로
바뀌면서 그 예외가 없어졌다.  아래 절의 정정 내용은 그대로 유효하다 — 판
번호만 바뀌었고 바이트는 같다.

## `R2608` (구 `R0827`) — MOD10 센서 B/C limit 정정 (2026-08-27)

**MOD10 의 센서 B/C 위치를 맞바꿨을 때(`_rtd9cal` 판) 라벨만 옮기고 limit 설정을
안 옮겼다.**  그래서 CCD 채널이 벽면보드용 범위를, 벽면보드가 CCD 용 범위를 쓰고
있었다.  운영자 확정(2026-08-27)으로 바로잡고 판을 `R2601` → `R0827` 로 올렸다
(2026-08-28 에 규칙에 맞춰 `R2608` 로 다시 표기했다 — 내용은 그대로다).

    MOD10\SENSORBLABEL      = RTD8_CCD1  ->  RTD8_CCD     (칩 번호 표기 제거)
    MOD10\SENSORBLOWERLIMIT = -30        ->  -120         (B = RTD8_CCD)
    MOD10\SENSORBUPPERLIMIT = 60 / 70.0  ->  50.0
    MOD10\SENSORCLOWERLIMIT = -120       ->  -30          (C = RTD5_WB)
    MOD10\SENSORCUPPERLIMIT = 50.0       ->  70.0

**왜 중요한가** — `SENSORx{LOWER,UPPER}LIMIT` 는 RTD 변환의 유효 범위다.  CCD
채널 하한이 −30 이면 **−30 아래를 읽을 수 없다**(운용 온도가 −100 대다).  그리고
그 채널이 raw spec `CCDTEMP` 의 **유일한 원천**이므로 대체 센서도 없다.
결측 판정을 값이 아니라 **이 한계로** 하는 것이 규범이다 -- 미연결 채널이
`-273.2` 만 내는 것이 아니라 `-196.9`~`-206.1` 처럼 **그럴듯한 값도 흘리기**
때문이다 (실측 확인, `../SMC_CLAUDE.md` "실측 로그 판정").

⚠️ **`_TBC` 판 둘(`R2601`, 스왑 전)은 손대지 않았다** -- 그 판에서는 limit 이
이미 라벨과 맞다.  고치면 옛 배치의 이력이 사라진다.  지금은
`../__ref_archon_control/acf/` 에 있다.

⚠️ **저장소 사본을 고친 것이 실기에 반영되는 것은 아니다** -- 유닛에 올려
`APPLYALL` 을 해야 적용된다.  그리고 `__ref_archon_control/` 의 실험실
스크립트들(`archon_kmtnet_guide_tvm_v0.9….py` · `modtm_*.py` · `tvm_gui_goff_
v0.7….py`)의 `UNIT_ACF` 가 **구 파일명을 가리키므로 작업본에서 함께 고쳐야
한다** (그 폴더는 참고 원본 보관용이라 여기서 고치지 않는다).

정정 **전** 판은 `archive/` 에 있다.

## 읽을 때 알아둘 것

**모듈 구성이 science 와 guide 에서 다르다** (`[SYSTEM]` 의 `MODn_TYPE`,
`0` = 빈 슬롯).  `Cn_TEMP` 자리 표(규격 5.6.1절)가 여기서 갈린다:

| | 장착 슬롯 | 자리 수 (백플레인 포함) |
|---|---|---:|
| science 여섯 | 1·2·3·4·5·8·9·10·11 | **10** |
| guide | 3·4·5·6·7·9·10 | **8** |

science 쪽은 `rawhdr.TEMP_MODS` 와 정확히 같고, `__ref_archon_control/
modtm_sci_*.py`(실사용본)가 `STATUS` 에서 읽는 자리와도 같다 — 규격과 무관하게
쓰인 스크립트가 같은 표에 닿았다는 것이 **자리 표의 독립 확인**이다.
guide 8자리는 **raw spec 10.4절이 정본**이다 — v1.9 에서 `OI-19` 종결, 이 ACF
`[SYSTEM]` 과 `modtm_gui_*` 두 근거 일치 (첫 guide 구동 때 STATUS 재확인만 남는다).
형 번호는 science 가 `17`(ADM)·`18`(HVYBias), guide 가 `2`(AD)·`11`(HeaterX)·
`8`(HVXBias) 다.

**`BIGBUF` 가 science/guide 를 가른다.** science 는 `1`(768 MB × 2), guide 는
`0`(512 MB × 3). `../scr_labtest/` 에 smallbuf 사본을 남겨 둔 근거가 이것이다
— guide 취득 스크립트를 만들 때 버퍼 주소 지정이 참고가 된다. 다만 bigbuf 판은
`FETCH` 주소를 프레임 상태의 `BUFnBASE` 에서 읽어 **설계상 구성 무관**이므로
그쪽을 출발점으로 삼아도 된다(실기 검증은 첫 guide 구동 때).

**MK/NT ACF 는 구조적으로 동등하다.** 2026-08-27 에 `KMTC_SCI_101`↔`102` 를
전수 대조한 결과, `[CONFIG]` 항목 959개의 **집합이 같고** 다른 값은 33개뿐이며
그 전부가 `IP` 와 **amp 배정**(`TAPLINEn`)이다 — 검출기 조가 다르니 당연하다.
※ 섹션 순서만 다르다(MK 는 `[SYSTEM]` 먼저, NT 는 `[CONFIG]` 먼저). `configparser`
가 읽으므로 동작에는 영향이 없다.

**`TAPLINES` 가 33 과 32 로 갈리는 것은 기능 차이가 아니다.** 실제 tap 은
어느 판이든 **science 32개 · guide 8개**로 같고, 끝에 **빈 `TAPLINEn` 이 하나
붙었느냐**가 값을 1 올린 것뿐이다 (GUI 저장 시 생기는 꼬리로 보인다):

| | `TAPLINES` | 실제 tap | 마지막 항목 |
|---|---:|---:|---|
| science 대부분 · guide | 33 · 9 | 32 · 8 | `TAPLINE32`·`TAPLINE8` = 빈값 |
| `KMTK_SCI_113…MK.acf` | 32 | 32 | 빈 항목 없음 |

※ 2026-08-27 에 "amp 하나가 빠진 것 아니냐" 로 의심했다가 전수 대조로 해소했다.
`TAPLINES` 값만 보고 판단하지 말고 **빈 항목을 뺀 실제 tap 수**를 셀 것.

⚠️ **줄 끝은 LF 로 정규화된다** (`.gitattributes` 의 `*.acf`/`*.txt text eol=lf`
-- 이 폴더의 타이밍 스크립트 txt 둘도 같은 규칙이다).
전 계통 리눅스 구동이고, CRLF 로 체크아웃되면 값 뒤에 `\r` 이 붙는 파서를
만나 조용히 틀리기 때문이다. Archon GUI 가 내보낸 원본(CRLF)과는 바이트가
다르니, GUI 로 되불러 편집할 일이 있으면 변환이 필요할 수 있다.

## 판 표기

`R2608` · `R2601` 은 ACF 개정 번호이고 **`YYMM`** 으로 읽는다.  파일명 규칙:

```
<SITE>_<역할>_<유닛번호>_<시리얼>_<ACF판>[_<검출기조>].acf
```

역할은 `SCI`(science) · `GUI`(guide) 다.  **검출기조(`_MK`/`_NT`)는 science
에만 붙는다** -- guide 는 유닛당 검출기가 하나라 가를 것이 없다.

유닛 ↔ 시리얼 대응의 정본은 `../../raw_fits_spec/__reference/Archon_Unit_Info.txt`
다 (`KMTC-SCI-101` ↔ `STA0284` 등).

⚠️ **`YYMM` 은 같은 달의 두 번째 판을 표현하지 못한다** (2026-09-03 에 드러났다).
`R2610` 은 **2026-09-03 에 만들어졌다** -- `YYMM` 대로면 `R2609` 인데 그 이름은
이미 쓰였다(커밋 2026-09-01).  ⭐ **번호는 단조 증가하고 `YYMM` 은 하한으로
읽는다** 로 규칙을 넓힌다 -- 같은 달의 두 번째 판은 다음 번호로 넘어간다.
⚠️ 그러면 번호가 만들어진 달보다 앞설 수 있다.  `R2610` 이 그 첫 사례다.

⚠️ **타이밍 스크립트 txt 의 `R<YYMMDD>` 는 이것과 다른 계열이다** (2026-09-03).
보관함의 `acf_timing_script_{guide,science}_R<YYMMDD>.txt` 에 붙는 여섯 자리는
**ACF 개정 번호가 아니라 타이밍 스크립트 자체의 최종 수정일**이다 (운영자 기록).
`R210930` 을 `YYMM` 으로 읽어 "2021-09" 로 오해하지 말 것 -- `YYMMDD` 다.
같은 스크립트가 여러 ACF 판에 그대로 실리므로(guide 열두 장이 전부 동일) 스크립트
날짜와 ACF 판 번호는 애초에 따로 움직인다.

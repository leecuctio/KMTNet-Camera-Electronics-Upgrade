# SMC_CLAUDE.md

`raw_fits_spec/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md), 이 폴더의 구성은 [README.md](README.md) 참고.

## 이 폴더가 뭔가

**Archon controller 가 직접 저장하는 raw FITS pair 의 규격을 관리한다.** `mef_fits_spec/` 이 출력(L0 MEF) 규격이라면 여기는 입력(Archon raw) 규격이다.

## ⚠️ 지금은 현행 규격이 없다 (2026-08-18 부터)

`KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 는 파일로는 남아 있지만 **⛔ ((재작성중)) 표시가 붙었고 근거가 아니다.** 제목 · 첫 화면 · 버전 줄 세 곳에 표시가 있다.

- **재작성판이 나올 때까지 이 규격을 인용하거나 근거로 구현하지 않는다.** 절 번호(5.x · 7장 · 9장)도 바뀔 수 있다.
- 다른 문서·코드에 남은 참조 16곳은 **경로로는 유효하지만 근거로는 무효**다.
- 특히 **ICD v4.1 §12 가 이 문서의 5장에 필요한 raw 텔레메트리 집합을 위임**하고 있고, `ics_sim` 의 `rawhdr.py` · `rawpair.py` · `hardware/archon.py` 가 5장을 구현한다. 재작성 시 이 의존을 함께 정리해야 한다.

## 먼저 읽을 것

| 문서 | 지위 |
|---|---|
| `KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.7.md` | **이 폴더에서 지금 가장 쓸모 있는 문서.** converter 가 읽는 것 · 읽지 않는 것 · 도입 후보·확정 · 폐지된 것을 13장으로 정리했다. v1.7 은 수기 개정(3장 6열 신형식 · 확정 초안 반영 · 8.2 신설) — 구판은 `archive/` |
| `KMT_CEU_Raw_to_MEF_Keyword_Map_v0.7_REVIEW.md` | 검토용. 팀 검토 대기 중인 **5장 10항목**이 여기 있다 (ACT-011) |
| `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` | ⛔ ((재작성중)). 참고만 |
| `__reference/Legacy raw fits header samples/` | **raw 쪽 기준선.** `KMTNk.20170209.044131.Rawheader.txt` keyword 123개 |

## 준수 우선순위 (v0.7 검토 문서 0장에서 확립)

```
1  mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md    준거
2  mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py   L0 MEF 산출 주체
3  mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md 참고 (converter 미러)
```

- **raw 쪽 기준선은 레거시 raw 실측 헤더**다. `ics_sim` 의 현재 출력은 미완성 구현이라 판정 근거로 쓰지 않는다.
- 레거시 **MEF** 헤더 33건은 배경지식이지 판정 근거가 아니다. 레거시 **raw** 헤더 1건만 근거다.
- **ICD 는 PRIMARY keyword 를 열거하지 않는다.** converter 가 만드는 카드 이름 210개 중 ICD 에 나오는 것은 36개뿐이고 174개(83%)가 없다. 그 침묵 구간이 곧 이 검토가 결정할 몫이다.
- 확정된 근거는 `../project_management/governance/DECISION_LOG.md` 의 **D-번호**다. 이 폴더가 기대는 것은 **D-011**(사이트 코드 파일명) · **D-013**(레거시 keyword 판정).

## ▶ 이어서 시작하는 자리 (2026-08-21 기준)

### 2026-08-21 확정분 (직전 세션과 목의 검토로 닫힘)

- **Detector/Amplifier 블록 확정** — `DETID`(레거시 계승, 값 'MK'/'NT' 재정의, comment "Detector pair in this raw FITS file") · `DETECTOR` · `PIXSIZE`/`PIXSCALE`(0.395, 근거 표기 없이) · `CCDXBIN`/`CCDYBIN`(이름 유지) · `NAMPDET`/`NAMPRAW` · **타일 해부 대칭형** `AMPNAX1`=1200/`AMPNAX2`=4700 + `IMAGEX`=1152/`IMAGEY`=4616 + `PRESCNX`/`PRESCNY`=0 + `OVRSCNX`=48/`OVRSCNY`=84(개명으로 레거시 동명 충돌 전부 해소) · **`CHMAP_LT/LB/RT/RB` 4장**(값=CCD 출력 채널, raw X 오름차순; AMPCHA/AMPCHB 안 대체). 값은 REVIEW/AMPID.txt 와 전수 대조 완료. 파생 카드(`AMPDATA`·`NXTILE`·`RAWXTILE` 등)는 싣지 않는다.
- **충돌 처리 · 정체성 재설계 확정** — 번호 공간 000000–099999, 충돌 시 pair 선검사 + 번호 증가(상한 100000회 초과 시 ERROR·저장 안 함), 카운터 동기화. `UNIQNAME`·`NAMECLSH`·`clash/` 폐지, `FILENAME`(유일 키)+`ORIGNAME`(항상 기록, 불일치=충돌 신호). 정리본: [`KMT_CEU_Raw_Numbering_and_Identity_v0.1.md`](KMT_CEU_Raw_Numbering_and_Identity_v0.1.md) (D-등재 대기, 결정문 초안 8장).
- **MEF 쪽 개정 요청 목록**: [`KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.2.md`](KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.2.md) (LEECU 전달용 — MEF `UNIQNAME` 공급원, C-11 CHMAP 개정 등).
- 미세 미결: `ORIGNAME` 이름 최종 확정(ORIGNAME 유지 권고, 차선 INITNAME), `READMODE` 값 충돌(FAST vs 64AMP — 이름 분리 필요), Instrument 절(FPAID 카드안 · INSTRUME 어휘) 미착수.

### 2026-08-20 세션 기록 (아래는 그 시점 기준)

**2026-08-20 세션은 키워드 설계를 검토만 했고 아무것도 확정하지 않았다.** 그래서 v1.6 · v0.7 · 규격 v1.2 는 손대지 않았다. 아래는 그 논의에서 **모양이 잡힌 것**과 **아직 못 정한 것**이다. 다시 처음부터 헤매지 않도록 근거까지 적어 둔다.

작업 대상 초안은 저장소 밖에 있다 — `../../REVIEW/KMTA.20260818.012345.MK.fits.header.txt` (운영자가 만드는 신규 raw 헤더 초안).

### 모양이 잡힌 것 (아직 결정 아님)

| 카드 | 형태 | 근거 |
|---|---|---|
| `NAMPDET` / `NAMPRAW` | `16` / `32` | `NAMPS`(레거시 8 → 신규 64, **세는 범위가 바뀜**)와 `AMPPCD`(`AMPCCD` 오타로 읽힘)를 폐지하고 통일. v1.6 8.1절에 기록됨 |
| `AMPNAX1` / `AMPNAX2` | `1200` / `4700` | `RAWNAX1`/`RAWNAX2` 계열. `*SIZE` 는 이 헤더에서 **구간 문자열**이라(`DETSIZE`) 피했다. comment 는 `X pixels per amplifier (image+pre/overscan)` |
| `AMPCHA` / `AMPCHB` | `'1615141312111009 0102030405060708'` | AMPID ↔ CCD 출력 채널. 자리=amp, 값=channel. **8개마다 공백**이 TOP/BOT 경계와 맞는다. port 글자가 이름에 들어가야 해서 `AMPCHMAP`(8자)은 못 쓴다 |
| `IMGSEC` 계열 값 | `'D-Top'` / `'A-Bot'` | 구분자는 **하이픈** — 콜론은 구간·육십진으로 이미 두 뜻, 쉼표는 목록. `Bot` 은 `ENDID`/`EXTNAME` 이 쓰는 축약 |

**`AMPNAX*` 로 파생되는 값은 카드로 싣지 않는다** — `AMPDATA`·`NXTILE`·`RAWXTILE` 이 전부 `NAXIS` 와의 나눗셈·뺄셈으로 나온다.

```text
tile 수  = NAXIS1 / AMPNAX1 = 19200 / 1200 = 16
active X = AMPNAX1 - OVERSCNX - PRESCANX = 1200 - 48 - 0 = 1152
active Y = AMPNAX2 - OVERSCNY - PRESCANY = 4700 - 84 - 0 = 4616
```

### 아직 못 정한 것

| 무엇 | 왜 막혔나 |
|---|---|
| **`AMPDIRST`/`AMPDIRSB` 의 `L`/`R` 뜻** | *"독출 방향"* 인지 *"amp 위치"* 인지 안 갈린다. 초안 값 `'LLLLRRRRLLLLRRRR'` 는 현행 `OSCNPATT='RRRRLLLL'`·converter `is_bias_right()` 와 **좌우가 반대**다. 방향으로 읽으면 어긋나고 amp 위치로 읽으면 맞는다. **comment 한 줄로 끝나고 측정과 무관하므로 지금 정할 수 있다** |
| **`OVSCN` 계열의 X/Y 분리** | v1.6 8.1절이 `OVERSCNX` 폐지 → `OVSCN` 으로 적었는데, 이후 초안은 `OVERSCNX`+`OVERSCNY` 를 유지한다. **둘 중 하나를 철회해야 한다** |
| **`OVERSCNY=84` 의 가장자리** | amp 기준으로는 안쪽 가장자리(TOP 은 아래, BOT 은 위)인데 헤더에 안 적혀 있다. 게다가 `84` 는 168 의 균등 분배 **가정**이고 OI-4 가 미측정이다 |
| **상하 독출 방향** | `AMPDIRS*` 는 좌우만 담는다. `RDDIRT`/`RDDIRB` 가 하던 일이 초안에서 사라졌다 |
| **v1.6 7장 `도입 여부` 36칸** | 후보 37장 중 `NAMPRAW` 하나만 `O` 다 |
| **v1.6 2장 `Raw Archon` 열** | 123개 중 9개만 채워져 있다 |

> **이 결정이 왜 자꾸 안 끝나는가** — 아는 것(좌우 X)과 모르는 것(상하 Y · 중앙 overscan 분배)을 **한 카드에 함께 담으려 해서**다. 측정 안 된 사실의 최종 표기는 설계할 수 없다. 그리고 **converter 가 raw geometry 를 하나도 읽지 않아** 어떤 형식을 골라도 틀렸는지 알 방법이 없다(되먹임 없음).
>
> **여유는 있다.** `AMPDIRST`·`AORG`·`OVERSCNY` 같은 신규 카드는 아직 아무 자료도 쌓지 않았다. ACT-011 의 *"이름을 바꾸면 아카이브가 영구히 안 읽힌다"* 는 first light 부터의 얘기다.
>
> **권고**: ⓐ `L`/`R` 뜻만 지금 확정 ⓑ 미측정은 값 대신 **sentinel** 로(규격 5.0 절의 규약) ⓒ 형식은 OI-3 측정이 내놓는 모양을 보고 정한다.

### 검토했으나 접은 안

| 안 | 접은 이유 |
|---|---|
| raw 에 amp 별 구간형(`DATASEC` 32벌 등) | 단일 HDU 라 128장이 되고, 8자 제한 때문에 `DSEC01` 같은 비표준 어근이 필요하다. **raw 는 파라미터, MEF 는 구간**으로 가르기로 방향을 잡았다 |
| `AORG<nn>` 32장 (amp 별 원점+방향) | **이름이 지어낸 것**이고(`ORG` 가 FITS `ORIGIN` 과 겹친다), Y 방향이 OI-3 미측정이라 placeholder 32장이 된다. 실기 배치가 가정과 다르다고 밝혀지면 그때 다시 본다 |
| amp 별 `OVERSCNX`/`OVERSCNY`/… 32벌 | 128장인데 **값이 전부 같다.** amp 32개가 기하학적으로 동일하므로 스칼라 한 벌로 충분하다 |

## 되풀이 나타나는 함정 세 가지

**1. 이름은 같은데 뜻이 달라진 카드.** 값이 유효해 보여 오류가 안 난다.

| 카드 | 레거시 | 신규 |
|---|---|---|
| `OVERSCNY` | `0`, **가장자리** | `84`, **영상 중앙** ← D-013 이 폐지한 이유 |
| `NAMPS` | `8` (CCD 하나) | `64` (카메라 전체) ← v1.6 이 폐지 |
| `OVERSCNX` | `32` | converter 상수 `48` |
| `PRESCANX` | `27` | `0` |

**2. 기본값이 진짜 값처럼 보인다.** converter 는 카드가 없어도 오류를 내지 않는다.

- `DATE-OBS` 없으면 **변환 시각(now)** 으로 대체 — 이 문서 전체에서 가장 위험하다
- `RA`/`DEC` 없으면 `"00:00:00.00"` — 형식이 유효해 하류에서 안 걸린다
- 버전 문자열 9종은 `"ARCHON-v1.0"` 처럼 **그럴듯한 provenance** 가 박힌다
- **오류로 걸리는 것은 `OBSERVAT` 하나**(파일명 사이트 코드 교차 검증, D-011)

**3. converter 는 raw geometry 를 하나도 읽지 않는다.** `OSCNPATT`·`ROWORDR`·`RDDIRT`/`RDDIRB`·`AMPMAP`·`AMOD`/`ACHN`·`NXTILE`·`CHIPS`/`CHIP1`/`CHIP2` 는 **소스에 이름조차 없다.** 나머지는 자기 상수로 만들어 내보낸다. `OVERSCAN_X=48` 은 표기용이 아니라 **실제 픽셀 절단 좌표 계산에 쓰인다.** → 변경점 C-5 · C-11 · C-12 · C-13

## 조사로 확정된 사실 (문서에 아직 안 들어감)

**레거시 `READOUT = 'ARLBRL'` 의 정체** — OSU IC 펌웨어(`../../__localonly_osu_legacy/IC2_*/IC2.img`)에 FreeBASIC 원본이 통째로 들어 있고, `SUB SetReadout()` 이 이렇게 하드코딩한다:

```basic
'-- Four amp readout only
Amps = "ARLBRL" : XAmp = 2 : YAmp = 2
TopDelaceCode = 8 : BotDelaceCode = 10  '-- swap to register quadrants correctly
```

`XAmp=2, YAmp=2` 사분면 전제 + de-interlace 순서가 얽힌 부호이고, 레거시 표본 3건 — 2017 raw(SSO) · 2021 raw(CTIO) · MEF primary — 이 **전부 같은 값**이다(불변 상수). **D-013 의 폐지 판정이 옳았음을 뒷받침한다.**

**레거시 IC 에 ROI 가 있었다** — 같은 펌웨어의 `READOUTSETVAR` 에 `OSCANX`/`OSCANY` 와 경고문이 있다: *"Region-of-interest has been modified to maintain symmetry around CCD centerline."* ICS 명령 테이블에는 없어 운영에서 쓰이지 않았다. v1.6 10장(subframe)의 근거가 된다.

**레거시 `AMPSEC` 이 독출 방향을 담고 있었다** — 레거시 MEF 실측 32장을 보면 `AMPSEC` 이 `CCDSEC` 과 같은 범위인데 **순서가 뒤집힌 것이 있다**(`K01`: `CCDSEC='[8065:9216,...]'` vs `AMPSEC='[9216:8065,...]'`). IRAF 관례대로 **구간의 오름/내림차순이 곧 독출 방향**이다. 전량 패턴은 `M/T = 5:3`, `K/N = 3:5` 인데 **우리 신규는 4:4 를 전제**한다 — 같은 e2v CCD290-99 인데 분할이 다르므로 한쪽이 틀렸다. flat 이나 STA 문서로 확인이 필요하다.

## 미결 항목

규격이 재작성중이라 OI 번호는 v1.2 9장 기준이다.

| ID | 무엇 | 상태 |
|---|---|---|
| **OI-3** | `ROWORDR`/`RDDIRT`/`RDDIRB` 확정 | 실기 flat/star 필요. ICD §12 도 `READDIR` 을 placeholder 라 밝힌다 |
| **OI-4** | 중앙 overscan 의 TOP/BOT 분배 | 실측 필요. `OVERSCNY=84` 는 균등 가정 |
| **OI-5** | binning | 1×1 전용. binned 관측 계획이 서야 |
| **OI-9** | amp ↔ 배선 맵 실측 | `XTALKCAL=True` 의 전제조건. `AMPCHA`/`AMPCHB` 가 **CCD 출력단**을 담고, **Archon module/channel 은 그 다음 단**이라 아직 미확정 |
| — | **부분 독출(subframe·ROI·window)** | **규격에도 미결 목록에도 없다.** v1.6 10장이 제기만 해 둔 상태. 쓸 계획이 있는지부터 정하고 OI 로 세워야 한다 |
| — | Archon AD 모듈당 채널 수 · TAPLINE 표기 | 저장소 증거는 `MOD5`~`MOD8`(AD 4장)뿐. STA 문서나 Tom O'Brien 협의 필요 |

## 브랜치 상태

작업은 **`raw-fits-spec-v1-review`** 브랜치에 쌓고 있고, **`main` 위에 얹힌 채 아직 원격에 올리지 않았다.** 몇 개가 쌓였는지는 여기 적지 않는다 — 커밋할 때마다 이 문장이 낡기 때문이다. 직접 본다:

```bash
git log --oneline --decorate main..raw-fits-spec-v1-review
```

`main` 은 `origin/main` 과 같은 자리라 **fast-forward 로 들어간다** — `git merge --ff-only raw-fits-spec-v1-review`.

이 브랜치가 갈라져 나온 자리는 **`6b19ad6`** 이다(v0.7 검토판 + 규격에 ((재작성중)) 표시를 붙인 커밋). 이 해시는 뒤에 뭘 더 쌓아도 안 바뀐다.

## ⚠️ v1.6 문서 재생성 수단이 남아 있지 않다

v1.6 은 converter 소스·v0.7 4.H 절·D-013 표에서 **기계 추출한 생성물**이고, 문서 스스로 *"원천이 바뀌면 다시 생성한다"* 고 적고 있다. 그런데 **생성기 스크립트는 세션 scratchpad 에 있었으므로 이미 사라졌다.**

다음에 v1.7 을 만들 때는 둘 중 하나다.

- 생성기를 다시 쓴다 — 추출 규칙은 v1.6 머리말에 적혀 있다(`card("<MEF>", v("<raw>", <기본값>))` 를 정규식으로 파싱, 4.H 절과 5.13 폐지 표를 표 블록으로 읽기)
- 또는 **생성기를 저장소에 넣는다** — 그래야 이 문제가 되풀이되지 않는다

`Raw Archon` 열과 `도입 여부` 열은 기계 추출이 아니라 **사람이 채우는 계획 열**이라, 생성기 안에 표로 들고 있어야 재생성해도 살아남는다.

## 관련 문서

| 문서 | 위치 |
|---|---|
| L0 MEF ICD (1위 준거) | [`../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md`](../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md) |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) |
| 취득 SW 구현 | [`../ics_sim/SMC_CLAUDE.md`](../ics_sim/SMC_CLAUDE.md) · `../ics_sim/DevNote.md` 11.14 |
| 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |
| 등재 | [`../project_management/planning/ACTION_REGISTER.md`](../project_management/planning/ACTION_REGISTER.md) **ACT-011** |

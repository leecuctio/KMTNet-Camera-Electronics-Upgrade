# KMT-CEU Raw FITS Pair 규격

버전: v1.2
작성일: 2026-08-06
최종 갱신일: 2026-08-10
Raw 규격 버전 (`RAWVER`): `CEU-RAW-v1.0` (문서 v1.1/v1.2의 변경은 geometry가 아니므로 유지)
연동 ICD: `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` (v4.1, docx 동본)
연동 converter: `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0)

## 1. 문서 목적과 범위

이 문서는 KMT-CEU 신규 전자부에서 **STA Archon controller 2대가 노출 1회당 만들어내는 raw FITS 2개** — 이하 **raw FITS pair** — 의 파일 구조, 픽셀 배치, 그리고 **헤더에 반드시 들어가야 할 keyword**를 정의한다.

| 구분 | 대상 | 규격 문서 |
| --- | --- | --- |
| **입력 (이 문서)** | Archon raw FITS pair (MK, NT) | `raw_fits_spec/` |
| 출력 | L0 64-amplifier MEF | `../mef_fits_spec/` |
| 변환 | raw pair → L0 MEF | `../mef_converter/` |
| 후처리 | L0 → L1 calibrated CCD | `../mef_pipeline/` |

작성 기준은 다음 한 문장이다.

> **raw pair가 이 규격을 만족하면, converter는 placeholder 없이 L0 MEF의 PRIMARY / amp extension / `AMPINFO` / `XTALKINFO` / `VOLTINFO` / `TELEMETRY`를 전부 실제 값으로 채울 수 있어야 한다.**

현행 converter가 `UNKNOWN` · `-999.0` · `PLACEHOLDER`로 채우고 있는 값들은 대부분 **raw 헤더에 그 정보가 없기 때문**이다. 이 문서의 5장은 그 구멍을 메우는 것이 주 목적이다.

이 규격의 구현 주체:

| 주체 | 파일 | 역할 |
| --- | --- | --- |
| 신규 ICS | `../ics_sim/ics_sim/hardware/archon.py`의 `write_fits()` | 운영 시 raw pair를 이 규격대로 저장 |
| 실험실 취득 | `../cam_char/archon/archon_kmtnet_labtest_v2.py`의 `write_fits()` | 특성 측정용 raw를 같은 구조로 저장 |
| Converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` | raw pair를 읽어 L0 MEF 생성 |

범위 밖:

- amp별 `GAIN` / `RDNOISE` / `SATLEVEL` / `LINMAX` / crosstalk coefficient는 **raw 헤더에 넣지 않는다.** calibration database 소관이며 converter가 `AMPINFO` / `XTALKINFO`에 주입한다 (`../project_management/science/CALIBRATION_TRACKER.md`).
- WCS 해는 raw에 넣지 않는다. L0 amp extension의 WCS는 placeholder이고, 확정 astrometry는 L1에서 만든다.
- Guide CCD, focus CCD 자료.

## 2. Raw FITS Pair 정의

### 2.1 노출 1회 = 파일 2개

신규 전자부는 science Archon controller 2대를 쓰고, **컨트롤러 1대가 science CCD 2개를 읽어 raw FITS 1개로 저장**한다.

| Raw file | 담는 chip | Controller | 역할 |
| --- | --- | ---: | --- |
| `...MK.fits` | M, K | 1 | pixel + **master metadata** |
| `...NT.fits` | N, T | 2 | pixel + metadata |

공식 chip order는 `M,K,N,T`이고 raw grouping convention은 `MKNT`이다 (DECISION_LOG **D-002**).

> **v1.0에서 상향된 요구**: ICD v4.0은 검증 시점의 실측을 근거로 "NT 헤더는 최소한만 있을 수 있다"고 기술했다. 이 규격은 그것을 **허용하지 않는다.** NT 파일도 5장의 필수 keyword를 모두 채워야 한다. 근거는 (1) NT 파일 단독으로도 해석 가능해야 archive 자산으로서 온전하고, (2) controller 2의 identity/telemetry는 NT에만 있으며, (3) pair 일관성 검사를 하려면 양쪽에 같은 키가 있어야 하기 때문이다. **ICD v4.1(2026-08-10)에 반영 완료** (OI-8 해결).

### 2.2 레거시 대비

| 항목 | 레거시 OSU 카메라 | KMT-CEU |
| --- | --- | --- |
| 노출당 raw 파일 수 | 4 (CCD당 1개, IC 4대) | 2 (controller당 1개) |
| 파일명 | `KMTN<c>.<YYYYMMDD>.<NNNNNN>.fits` | `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK\|NT>.fits` |
| 1 파일당 chip 수 | 1 | 2 |
| Amp 수 (전체) | 32 | 64 |

파일 수와 파일명이 둘 다 바뀌지만 **OBSAgent 규약은 그대로 유지된다.** 파일은 컨트롤러 단위로 2개를 쓰고, 저장 완료 통보만 CCD 단위로 4번 내보내는 방식으로 분리했다 (2.5절, DECISION_LOG **D-011** / **D-010**).

### 2.3 파일명

**확정 (D-011, 2026-08-10 — D-009를 대체).** Archon 컨트롤러 구성이 저장하는 파일명은 ICD v4.0 형식의 필드 구조를 유지하되, prefix를 고정 문자열 `KMTN`에서 **4자 대문자 사이트 코드**로 바꾼다 (ICD v4.1에 반영).

```text
<SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits
<SITE>.<YYYYMMDD>.<NNNNNN>.NT.fits
```

- `<SITE>`: 4자 대문자 사이트 코드. **TC 텔레메트리 `TELID` 규약과 동일**하며, 새 식별자가 아니라 기존 식별자의 파일명 확장이다.

  | `<SITE>` | 사이트 | `OBSERVAT` 헤더 | L0 MEF prefix |
  | --- | --- | --- | --- |
  | `KMTC` | CTIO | `CTIO` | `kmtc` |
  | `KMTS` | SAAO | `SAAO` | `kmts` |
  | `KMTA` | SSO | `SSO` | `kmta` |
  | `KMTT` | 테스트베드 (실험실·데모·Full Rehearsal) | `TESTBED` | `kmtt` |

- `<YYYYMMDD>`: 8자리. **UTC 날짜** — 그 노출의 `DATE-OBS` 가 속한 UTC 일자다. **잠정 확정이며 재정의 대상이다 (OI-10)** — 종전 서술 "관측 야간 기준 날짜" 는 레거시 실측과 현행 구현 어느 쪽과도 맞지 않아 정정했다.
- `<NNNNNN>`: **6자리 고정폭, 0으로 좌측 패딩**한 노출 일련번호. pair 양쪽이 같은 값이어야 한다.
- 접미 `.MK.fits` / `.NT.fits`는 **대소문자까지 정확히** 일치해야 한다. converter는 이 문자열로 짝을 찾는다.
- 예: `KMTC.20260807.012345.MK.fits`, `KMTC.20260807.012345.NT.fits`

사이트 코드를 넣는 이유 (D-011 근거 요약): 3사이트 데이터를 한 분석 풀에 모을 때의 동명 충돌 제거. ICS는 `<SITE>`를 설정(`[node] site`/`telid`)에서 얻으며, 설정 오배포 방어로 TC 텔레메트리 `TELID`와의 교차 검증을 둔다. `KMTC`/`KMTS`/`KMTA`/`KMTT`는 `KMTN` 부분 문자열을 포함하지 않으므로 물리 경로가 메시지에 섞여도 OBSAgent `FitsNum` 파서가 오반응하지 않는다.

> **6자리 zero-padding은 선택이 아니다.** converter(v2.2.0)의 정규식은 `^(KMTC|KMTS|KMTA|KMTT)\.(\d{8})\.(\d{6})\.MK\.fits$`이고, `find_pair()`는 MK 파일명에서 `.MK.fits`를 `.NT.fits`로 치환해 짝을 찾는다. 한쪽만 `12345`(5자리)로 쓰면 (1) 짝 파일을 못 찾아 `FileNotFoundError`, (2) 정규식 불일치로 출력 MEF 이름이 fallback 경로로 빠진다. (3) raw 파일명 자체는 OBSAgent에 가지 않지만(D-010), 같은 일련번호에서 만들어지는 `Wrote` 논리 이름의 `<NNNNNN>`이 함께 자릿수를 어기면 OBSAgent의 `FitsNum` 15자 슬라이스가 한 칸 밀린다.

> **파일명 `<SITE>`와 헤더 `OBSERVAT`는 일치해야 한다.** converter(v2.2.0)는 출력 MEF prefix를 파일명 `<SITE>`에서 유도하고 `OBSERVAT`와 교차 검증한다 — 불일치는 오류다 (6.1절). 파일명이 헤더와 다르게 유통되는 사고(설정 오배포, 수동 개명)를 조기에 잡기 위한 안전장치다.

파일명은 **pair 식별의 유일한 근거가 되어서는 안 된다.** 5.2절의 `UNIQNAME` / `CTRLTAG` / `PAIRFILE`로 헤더 안에서도 짝이 확인되어야 한다.

#### 2.3.1 이름이 겹쳤을 때 — 격리 · 접미 · 카드 (2026-08-12 확정)

ICS 계열은 1999년 Prospero 시절부터 **계산된 파일명이 이미 존재하면 조용히 덮어쓰지 않는** fail-safe를 갖고 있다 (`ics_legacy_report.md` 5.5절, DevNote 6.4). 레거시는 `<yymmdd>.<nnn>`으로 **개명**했고 그 후보 이름을 헤더 `UNIQNAME`에 실었다 — 실측 헤더가 `FILENAME = 'KMTNk.20170209.044131'` / `UNIQNAME = '170209.000'`이다 (`__reference/Legacy raw fits header samples/`).

**신규는 개명 대신 격리를 먼저 쓴다.** 개명하는 목적은 "덮어쓰지 않기" 하나뿐인데, 디렉토리를 옮기면 그 목적이 달성되면서 이름을 훼손하지 않는다. 세 겹이 각각 다른 질문에 답한다:

| 층 | 무엇을 말하나 | 값 |
| --- | --- | --- |
| **격리 디렉토리** | **어디에 있나** | `<data_dir>/clash/` |
| **파일 이름 접미** | **어느 것인가** | `<정본이름>.clash<YYYYMMDD>T<hhmmss>Z` |
| **헤더 카드** | **일어났는가** | `NAMECLSH = T` — **충돌했을 때만 넣는다** |

`clash`라는 낱말을 쓰는 이유: 겹친 것은 **이름**이고 자료는 멀쩡한 새 프레임이다. `dup`(duplicate)은 자료가 중복이라는 오해를 부른다. 세 층이 같은 낱말을 쓰므로 하나만 봐도 나머지가 짚인다.

접미를 번호가 아니라 **시각**으로 하는 이유: 소진될 일이 없고, 같은 프레임이 두 번 격리되어도 충돌하지 않으며, **언제 생긴 중복인지가 이름에 남는다.**

##### 왜 `FILENAME` · `UNIQNAME` 인가 — 새 keyword 를 만들지 않은 이유

**한때 `EXPID`(`'20260116.000001'`)와 `EXPNUM`(정수 연번)을 raw 헤더에 새로 넣는 것을 검토했다.** 파일명이 pair 식별의 유일한 근거가 되면 안 된다는 요구(2.3절 말미)를 헤더 안에서 충족시키려는 것이었고, 규격 v1.0~v1.2 는 그 형태로 기술돼 있었다.

**그런데 레거시 raw 헤더를 확인한 결과 이미 그 역할을 하는 keyword 가 있었다** (`__reference/Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt`):

```text
FILENAME = 'KMTNk.20170209.044131'  / Filename assigned by the data-taking system
UNIQNAME = '170209.000'             / Unique filename; if filename is invalid
```

- **`FILENAME` 이 날짜와 연번을 통째로 담고 있었다.** `EXPID` 는 그 부분집합이고, `EXPNUM` 은 그 안의 연번일 뿐이다.
- **`UNIQNAME` 은 이름을 쓸 수 없을 때를 위한 두 번째 이름이었다.** 즉 이름 충돌 문제를 레거시가 이미 헤더로 다루고 있었다.

그래서 **새 keyword 를 만들지 않고 이 둘을 이어받기로 했다** (2026-08-12 확정). 판단 근거 셋:

| | |
| --- | --- |
| **중복 제거** | 같은 정보를 담은 카드가 넷(`FILENAME`·`UNIQNAME`·`EXPID`·`EXPNUM`)이면 **서로 어긋날 수 있다.** 어긋났을 때 무엇이 정본인지 규격이 답해야 하는데, 그 답을 만들 이유가 없다 |
| **레거시 연속성** | 20년 가까이 쓰인 이름을 그대로 쓰면 기존 아카이브·도구·운영자의 지식이 이어진다. `EXPID` 는 이 저장소가 새로 만든 낱말이고 MEF 규격·converter·레거시 어디에도 없었다 |
| **MEF 목적지가 이미 있다** | MEF keyword 정의서는 `UNIQNAME` 을 *"unique filename or exposure ID"* 로 받는다. `EXPID` 를 만들면 그 자리에 전달할 값이 둘이 된다 |

**다만 `UNIQNAME` 은 보완해서 쓴다.** 레거시의 `<yymmdd>.<nnn>` 형식과 "대체 이름" 이라는 역할을 그대로 가져가지는 않는다 — 아래 역할 분담과 그 뒤 문단 참고.

##### `UNIQNAME`과 `FILENAME`의 역할 분담

| Keyword | 역할 |
| --- | --- |
| **`UNIQNAME`** | **정본 식별자.** 항상 정규 형태(`<SITE>.<YYYYMMDD>.<NNNNNN>.<MK\|NT>`)이고 **어떤 경우에도 바뀌지 않는다.** 파싱·짝 탐색·아카이브 색인은 이 값을 쓴다 |
| **`FILENAME`** | **디스크에 실제로 쓴 이름.** 평소엔 `UNIQNAME`과 같고, 충돌 시에만 `.clash…` 접미가 붙는다 |
| **`NAMECLSH`** | 충돌했을 때만 존재. `F`를 넣지 않는다 — 그러면 "충돌 안 함"과 "이 규격을 모르는 취득 SW"가 구분되지 않는다 |

**이 분담이 식별 손실 문제를 없앤다.** `UNIQNAME`이 불변이므로 격리된 파일도 어느 노출의 어느 컨트롤러인지 헤더만으로 알 수 있다. 레거시가 `UNIQNAME`을 "대체 이름"으로 쓴 것과 방향이 반대인데, **정본을 불변으로 두는 쪽이 파싱 규칙을 하나로 만든다** — 레거시 방식에서는 상황에 따라 `FILENAME`이나 `UNIQNAME`을 골라 읽어야 했다.

레거시의 `<yymmdd>.<nnn>` 형식은 채택하지 않는다: 하루 1000개 한계, **사이트 코드 소실**(3사이트 통합 시 동명 충돌이 되돌아온다 — D-011이 없애려던 문제), **컨트롤러 태그 소실**(짝을 못 찾는다).

##### converter 쪽 동작

converter(v2.2.0)의 정규식은 `clash/` 안의 이름을 받지 않고, 그 디렉토리를 훑지도 않는다. **즉 격리된 파일은 사람이 확인·개명해야 변환된다.** 이것이 의도한 동작이다 — 이름 충돌은 카운터 역행·시계 역행·파일 수동 복사 같은 **실제 이상**의 징후이므로(DevNote 11.12) 조용히 변환되어서는 안 된다.

> **왜 이 절이 필요한가.** 지속 카운터를 쓰면(DevNote 11.12) 정상 운용에서 충돌은 발생하지 않는다. 그런데 벤치에서 실제로 발생했고, 그때 헤더에 검출기 식별이 **하나도** 없어(`DETECTOR`/`INSTRUME`/`FILENAME`/`CTRLTAG` 전무, 4개 CCD가 동일 헤더) 어느 파일이 어느 검출기인지 알 수 없었다. 구현은 DevNote 11.13.

### 2.4 크기

| 항목 | 값 |
| --- | ---: |
| 파일당 픽셀 | 19200 × 9400 = 180,480,000 |
| 파일당 데이터 | 360,960,000 B ≈ 344.2 MiB |
| Pair 1쌍 | ≈ 688.5 MiB |
| 파생 L0 MEF | ≈ 676.2 MiB |

L0 MEF의 amp 픽셀 총수(64 × 1200 × 4616 = 354,508,800)와 raw pair 픽셀 총수(360,960,000)의 차이는 정확히 **middle Y overscan 블록**(2 × 19200 × 168 = 6,451,200)이다. 이 등식이 깨지면 4장의 geometry 해석이 어긋난 것이다.

### 2.5 저장 완료 통보 — ICS `Wrote` 규약

**확정 (D-010, 2026-08-07).** 파일은 컨트롤러 단위 2개지만, ICS가 OBSAgent로 내보내는 저장 완료 통보는 **레거시와 똑같이 CCD 단위 4회**다. 저장 단위와 통보 단위를 분리해 OBSAgent를 건드리지 않는다.

| raw 파일 | 발신 메시지 |
| --- | --- |
| `KMTC.20260807.012345.MK.fits` | `STATUS: Wrote LASTFILE=/data/KMTNm.20260807.012345.fits`<br>`STATUS: Wrote LASTFILE=/data/KMTNk.20260807.012345.fits` |
| `KMTC.20260807.012345.NT.fits` | `STATUS: Wrote LASTFILE=/data/KMTNn.20260807.012345.fits`<br>`STATUS: Wrote LASTFILE=/data/KMTNt.20260807.012345.fits` |

논리 이름은 `KMTN<chip 소문자>.<YYYYMMDD>.<NNNNNN>.fits`이며 chip 문자는 `CHIP1`/`CHIP2`에서 결정론적으로 나온다 (MK → `m`,`k` / NT → `n`,`t`). 파일 1개를 다 쓴 시점에 그 파일이 담은 두 chip의 메시지를 함께 낸다. **논리 이름의 `KMTN` prefix는 물리 파일명의 사이트 코드(D-011)와 무관하게 불변이다** — OBSAgent 파서가 `"KMTN"` 문자열 위치를 기준으로 자르기 때문이다.

이 규약이 OBSAgent에서 성립하는 근거:

| 검사 | 결과 |
| --- | --- |
| 메시지 타입 | `ICS>OBS`는 원래 `STATUS: Wrote`다 (DevNote 6.1 실측 로그). `DONE:`은 `CB>ICS` 구간이고, SSO의 `STATUS:` 결함은 그 앞 hop이라 무관하다 |
| `count_wrote` | 4회 → `FitsSaved=1` ✓ |
| `FitsNum` 파싱 | `"KMTN"` 위치 +6부터 15자 → `'20260807.012345'` ✓ (`obsagent_model.py:112-114`) |
| 4개 메시지 간 일관성 | 네 논리 이름의 날짜·번호가 같으므로 도착 순서와 무관하게 같은 `FitsNum` |
| 타이밍 | 프레임 N의 `Wrote` 4개는 프레임 N+1의 `EXPSTATUS=READOUT`(및 그 뒤 `PCTREAD=`)가 `count_wrote`를 리셋하기 전에 다 도착해야 한다 (DevNote 6.1, OBSAgent `commands.c` 797~816행). 파일 2개 × 2회를 저장 직후 함께 내므로 레거시(IC 4대 개별 발신)보다 여유가 있다 |

**발신 순서 규칙 — 프레임 N의 `Wrote` 4회는 프레임 N+1의 `EXPSTATUS=READOUT` 발신 이전에 반드시 내보낸다.**

OBSAgent는 `PCTREAD=` 수신 시뿐 아니라 **`EXPSTATUS=READOUT` 수신 시에도** `count_wrote`와 `FitsSaved`를 리셋하며(`commands.c` 812~816행), READOUT은 첫 `PCTREAD=`보다 약 2.7초 먼저 온다 (DevNote 4.1 실측: t+38.69 `EXPSTATUS=READOUT` vs t+41.4 첫 `PCTREAD=`). 이 READOUT ~ 첫 PCTREAD 사이 약 2.7초는 **함정 창**이다 — 여기에 낀 `Wrote`는 READOUT 리셋 뒤에 세어졌다가 첫 `PCTREAD=` 리셋(`count_wrote=0`, `FitsSaved=0`)에 지워지므로, 그 프레임의 `FitsSaved`는 영영 서지 않고 매 프레임 `force_fitssaved` 25초 타임아웃 + `ExpStatus=ERROR` 경로로 빠진다.

**이름이 겹친 경우의 통보** — 격리했을 때 나가는 `WARNING: FITS file '<정본경로>' already exists, writing as '<격리경로>' instead`는 **파일 단위 사건이므로 파일당 1회**이고, **발신자는 `ICS`**, 수신자는 노출 개시자 하나다. 레거시는 `*.CB>{ICS, OBS}`로 양쪽에 보냈지만 그건 CB가 별도 프로세스였기 때문이고, 통합 구조에서는 ICS가 파일을 쓴 당사자라 자기 앞 발신이 낭비다(XIS 경유 모드에서는 에코로 되돌아온다). 발신자를 CCD 단위 `*.CB`로 하지 않는 이유: 물리 파일 1개에 chip이 2개라 `M.CB`/`K.CB` 중 무엇으로 보낼지 정할 근거가 없고, 둘 다 보내면 파일 2개가 겹친 것처럼 보인다. OBSAgent 쪽 안전성은 소스로 확인했다 — `case WARNING:`(`commands.c:1045-1048`)은 발신자를 보지 않고 본문을 출력만 하며 `already exists`를 파싱하지 않고, 발신 노드 필터(`:757`)는 `case STATUS:` 안에만 있다. `Wrote` 통보 4회는 격리와 무관하게 그대로 나간다(논리 이름을 쓰므로).

**주의 — `LASTFILE`은 이제 실재하는 경로가 아니다.**

`/data/KMTNm.20260807.012345.fits`라는 파일은 디스크에 없다. 실제 파일은 `/data/KMTC.20260807.012345.MK.fits` 하나이고, 논리 이름은 OBSAgent 규약을 만족시키기 위한 **CCD 단위 식별자**일 뿐이다. 따라서:

- `LASTFILE` 값을 경로로 열려는 도구는 실패한다. 아카이브·DTS·QL 도구는 `LASTFILE`이 아니라 raw 헤더의 `UNIQNAME` / `FILENAME` / `CTRLTAG`를 근거로 삼아야 한다 (5.2절). **색인 키는 `UNIQNAME`** 이다 — 이름이 겹쳐 격리된 경우에도 그 값만 불변이다 (2.3.1절).
- 논리 이름 ↔ 실제 파일 대응은 `CHIP1`/`CHIP2`로 역추적 가능하므로 raw 헤더에 별도 keyword를 두지 않는다.
- `RATE=` 필드를 붙이는 경우, 한 파일에서 나온 두 메시지는 **그 파일의 측정 전송률을 동일하게** 싣는다 (CCD별로 나누지 않는다).

## 3. 파일 구조 요구사항

| 요구 | 값 | 근거 |
| --- | --- | --- |
| HDU 구성 | **single HDU** (PRIMARY에 이미지) | converter `read_primary_header()`가 첫 END 카드 직후부터 픽셀을 memmap한다. extension이 있으면 오독한다 |
| `BITPIX` | **16** | `memmap_raw()`가 16이 아니면 즉시 실패 |
| 픽셀 표현 | big-endian signed 16-bit + `BZERO=32768` (FITS unsigned 관례) | converter가 `>i2`로 읽어 **그대로** MEF에 기록. `BZERO`가 다르면 L0 픽셀 해석이 통째로 틀림 |
| `NAXIS1` / `NAXIS2` | **19200 / 9400** | 다르면 converter가 즉시 실패 |
| 패딩 | 헤더·데이터 모두 2880 byte 블록 | FITS 표준 |
| 압축 | **파일 내부 압축(tile compression) 금지** | 전송용 `.gz`는 파일 단위로 별도 생성 |
| Binning | v1.0은 **1×1 전용** | 9장 OI-5 |

## 4. 픽셀 배치 (Raw Geometry)

### 4.1 X 방향 — 16개 amp tile

```text
X:  1 ....................... 9600 | 9601 ..................... 19200
    첫 번째 chip (M 또는 N)          두 번째 chip (K 또는 T)
    strip 1..8 × 1200 col            strip 1..8 × 1200 col
```

tile 1개 = **1200 col = active 1152 + X overscan 48**, prescan 없음.

overscan이 tile의 왼쪽인지 오른쪽인지는 strip 번호로 정해진다 (`OSCNPATT='RRRRLLLL'`).

| Strip | tile 내 active | tile 내 overscan |
| ---: | --- | --- |
| 1–4 | 앞 1152 col | 뒤 48 col (**오른쪽**) |
| 5–8 | 뒤 1152 col | 앞 48 col (**왼쪽**) |

chip 시작 offset을 `X0` (첫 chip 0, 두 번째 chip 9600)라 할 때 strip `s`의 tile은 `X0 + (s-1)*1200 + 1 .. X0 + s*1200`이다.

### 4.2 Y 방향 — 상·하 분할 독출과 중앙 overscan

```text
Y:  1 ..... 4616 | 4617 ..... 4784 | 4785 ..... 9400
    BOT active     middle Y overscan   TOP active
    (4616 rows)    (168 rows)          (4616 rows)
```

- CCD 1개는 9232행이고 8개 strip을 **상·하 양 끝에서 동시에** 읽는다. strip 1개가 amp 2개(TOP/BOT)를 갖는다.
- 따라서 **X tile 1개는 amp 2개를 담는다**. raw 파일 1개에 chip 2개 × amp 16개 = **amp 32개**.
- 중앙의 168행은 양 half의 active row를 다 읽은 뒤 추가로 clocking된 Y overscan이며, 프레임 중앙에 나타난다.

**행 순서 규약 (`ROWORDR`)** — 이 규격에서 가장 오해하기 쉬운 지점이다.

| 값 | 의미 |
| --- | --- |
| `CCD` (**v1.0 규정값**) | TOP half가 **독출 순서가 아니라 CCD 좌표 순서**로 기록된다. raw row 4785 ↔ CCD row 4617, raw row 9400 ↔ CCD row 9232 |
| `READ` | TOP half가 독출 순서대로 기록된다 (raw row 4785 ↔ CCD row 9232) |

현행 converter는 `ROWORDR='CCD'`를 전제로 raw row를 **뒤집지 않고** 복사하며, `CCDSEC=[...,4617:9232]`로 기록한다. 실기 raw가 `READ`로 나오면 **TOP half 영상 전체가 Y 반전**되고 L0의 CCD 좌표계가 통째로 틀어진다. 그래서 이 값을 헤더에 **명시적으로 선언**하도록 요구한다. 최종 확인은 flat/star sequence test이며 amp header의 `READDIR`와 함께 확정한다 (9장 OI-3).

**중앙 overscan 분배 (`MIDOSCB` / `MIDOSCT`)** — 168행 중 몇 행이 BOT half에서, 몇 행이 TOP half에서 나온 것인지는 timing script가 정한다. 대칭 clocking이면 84/84이지만 **가정하지 말고 헤더에 기록**한다. 현행 converter는 이 블록을 **전부 버린다** (9장 OI-4).

### 4.3 amp 1개의 raw 좌표

| Amp 범위 | `ENDID` | raw Y 구간 | CCD Y 구간 |
| --- | --- | --- | --- |
| 1–8 | `TOP` | 4785 : 9400 | 4617 : 9232 |
| 9–16 | `BOT` | 1 : 4616 | 1 : 4616 |

amp 번호 → strip 번호는 `strip = ((amp-1) mod 8) + 1`이다.

## 5. 헤더 Keyword 규격

### 5.0 작성 정책

| 상태 | 의미 |
| --- | --- |
| **필수** | 없으면 L0 MEF가 틀린 값을 갖거나 변환이 실패한다 |
| **권장** | 없어도 변환은 되지만 provenance·진단 능력이 떨어진다 |
| 선택 | 사이트 사정에 따라 |

| 출처 | 의미 |
| --- | --- |
| ARCHON | Archon controller STATUS/FRAME/CONFIG 응답 |
| ICS | ICS가 TC에 질의해 중계하는 AUX/TCS telemetry (`../ics_sim/ics_sim/telemetry.py`) |
| ACQ | 취득 소프트웨어가 스스로 아는 값 (파일명, 시각, 노출 계획) |
| SITE | 사이트 설정 DB (고정값) |

공통 규칙:

- FITS 표준 keyword는 **8자 이내**. `HIERARCH`는 쓰지 않는다 (converter의 카드 파서가 `key[:8]`만 본다).
- 시각은 모두 **UTC**. `TIMESYS='UTC'`를 명시한다.
- 문자열 값에 홑따옴표가 들어가면 FITS 규칙대로 두 번 쓴다.
- **식별자 keyword는 FITS 문자열 카드로 쓴다 — 숫자 카드로 쓰면 안 된다.**

  대상: `UNIQNAME` · `FILENAME` · `PAIRFILE` · `CTRLTAG` · `CHIPS` · `CHIP1` · `CHIP2` · `CHIPLIST` · `RAWPROD` · `RAWVER` · `RAWGROUP` · `OBSERVAT` · `ORIGIN` · `CREATOR` · `DATE`. (개수인 `NUMFILES` · `VOLTN` 등은 정수 카드가 맞다.)

  이유는 연번을 담은 이름 하나로 충분하다. `UNIQNAME`의 값이 `'KMTA.20260811.000010.MK'`처럼 문자를 포함하면 애초에 숫자로 해석되지 않지만, **연번만 담는 값을 새로 도입하면 곧바로 이 함정에 걸린다.** 예를 들어 `'20260811.000010'`을 실수 카드로 쓰면 **2.3절이 필수로 정한 6자리 zero-padding이 파괴된다**:

  | 값 | 실수 카드로 쓰면 | 결과 |
  | --- | --- | --- |
  | `'20260811.000001'` | `20260811.000001` | 우연히 살아남는다 |
  | `'20260811.000010'` | `20260811.00001` | **`000010` → `00001`** |
  | `'20260811.000100'` | `20260811.0001` | **`000100` → `0001`** |
  | `'20260811.010000'` | `20260811.01` | **`010000` → `01`** |

연번은 파일명 `<NNNNNN>`과 같은 값이고 pair 일관성 검사(5.11절)와 `Wrote` 논리 이름(2.5절)의 근거이므로, 자릿수가 소실되면 파일명과 헤더가 어긋나 6.2절 "조용히 틀린 값" 부류가 된다. **끝자리가 0이 아닌 노출에서는 왕복이 우연히 성립하므로, 시험 데이터를 `000001`로만 잡으면 이 결함이 통과한다** — 검사는 값이 아니라 **카드의 형**을 봐야 한다 (8장 체크리스트).

- **sentinel 금지 항목은 "없을 수 있는 값"이 아니다 — 취득 SW가 구조적으로 아는 값이다.**

  `DATE-OBS` · `EXPTIME` · `DARKTIME` · geometry keyword는 전부 ICS 또는 ACQ가 자기 동작으로부터 아는 값이므로 **항상 존재해야 한다.** 특히 `DATE-OBS`는 **ICS가 셔터를 여는 그 시점의 OS 시각(UTC)을 그대로 물어 넣는다** — 외부에서 받아오는 값이 아니라 ICS가 스스로 찍는 값이다(5.7절: 셔터가 실제로 열린 시각, BIAS/DARK는 ERASE 완료 시각). 따라서 "값이 없어서 못 넣는" 상황은 정상 운용에 존재하지 않는다.

  그럼에도 카드를 못 채우는 일이 생겼다면 그것은 취득 SW의 **결함**이다. 그 경우 `'NC'`나 `0`으로 채워 값이 있는 것처럼 만들지 않는다 — 카드를 비우고 그 노출을 결함으로 보고한다. 6.1절의 실패 경로(변경점 C-6: `DATE-OBS` 누락 시 변환 중단)가 그때 정상적으로 발동해야 하기 때문이다.
- **값이 없을 때의 표기 (sentinel)**

  | 형 | Sentinel | 비고 |
  | --- | --- | --- |
  | 문자열 | `'NC'` | 레거시 ICS 관례 (`DSSTAT=NC`) |
  | 정수 | `-1` | |
  | 실수 telemetry | `-999.0` | converter의 `BOARDTEMP` placeholder와 동일 |

  **`EXPTIME` · `DARKTIME` · `DATE-OBS` · geometry keyword에는 sentinel을 쓰지 않는다.** 값이 없으면 그 노출은 불완전한 것으로 표시해야 한다. 숫자 `0`을 "값 없음"으로 쓰면 안 된다 — `EXPTIME=0`은 BIAS라는 뜻이고 `SECZ=0`은 물리적으로 불가능한 값이라 조용한 오염이 된다 (9장 OI-6).

### 5.1 FITS 표준 · 파일 정체성

| Keyword | 상태 | 값/예시 | 출처 | 설명 |
| --- | --- | --- | --- | --- |
| `SIMPLE` | 필수 | `T` | ACQ | FITS standard |
| `BITPIX` | 필수 | `16` | ACQ | 3장 참조 |
| `NAXIS` | 필수 | `2` | ACQ | |
| `NAXIS1` | 필수 | `19200` | ACQ | |
| `NAXIS2` | 필수 | `9400` | ACQ | |
| `BZERO` | 필수 | `32768` | ACQ | unsigned 16-bit zero point |
| `BSCALE` | 필수 | `1` | ACQ | |
| `BUNIT` | 필수 | `'ADU'` | ACQ | |
| `EXTEND` | 권장 | `F` | ACQ | extension 없음을 명시 |
| `ORIGIN` | 필수 | `'KASI'` | SITE | file originator |
| `DATE` | 필수 | UTC ISO | ACQ | 파일 생성 시각 |
| `CREATOR` | 필수 | `'ics_archon_v1.0'` | ACQ | 취득 소프트웨어와 버전 |
| `FILENAME` | 필수 | `'KMTC.20260116.000001.MK'` | ACQ | 자기 파일 이름 — **확장자를 뺀 형태** (`<SITE>` prefix, 2.3절). 레거시 실측 헤더가 `FILENAME = 'KMTNk.20170209.044131'` 로 `.fits` 없이 기록했다 (`__reference/Legacy raw fits header samples/`) |
| `CHECKSUM` | 권장 | FITS 표준 checksum | ACQ | 9장 OI-7 |
| `DATASUM` | 권장 | FITS 표준 datasum | ACQ | |

### 5.2 Pair 식별 · Provenance

**이 절이 raw pair 규격의 핵심이다.** 파일명에만 의존하지 않고 헤더만으로 짝을 확인할 수 있어야 한다.

| Keyword | 상태 | MK 값 | NT 값 | 출처 | 설명 |
| --- | --- | --- | --- | --- | --- |
| `RAWPROD` | 필수 | `'L0_RAW_ARCHON'` | 동일 | ACQ | 이 파일이 CEU Archon science raw임을 선언 |
| `RAWVER` | 필수 | `'CEU-RAW-v1.0'` | 동일 | ACQ | **raw 규격/geometry 버전.** 4장이 바뀌면 올린다 |
| `RAWGROUP` | 필수 | `'MKNT'` | 동일 | ACQ | raw grouping convention |
| `CHIPLIST` | 필수 | `'M,K,N,T'` | 동일 | ACQ | 카메라 전체 공식 chip order |
| `CTRLTAG` | 필수 | `'MK'` | `'NT'` | ACQ | **이 파일이 pair의 어느 쪽인가** |
| `CHIPS` | 필수 | `'M,K'` | `'N,T'` | ACQ | 이 파일에 담긴 chip (X 낮은 쪽부터) |
| `CHIP1` | 필수 | `'M'` | `'N'` | ACQ | X 1–9600 절반의 chip |
| `CHIP2` | 필수 | `'K'` | `'T'` | ACQ | X 9601–19200 절반의 chip |
| `PAIRFILE` | 필수 | NT 파일 이름 | MK 파일 이름 | ACQ | 짝의 이름. **`FILENAME` 과 같은 형태(확장자 없음)** |
| `NUMFILES` | 필수 | `2` | `2` | ACQ | 이 노출의 raw 파일 수 |
| `UNIQNAME` | 필수 | `'KMTC.20260116.000001.MK'` | `'…NT'` | ACQ | **정본 식별자.** 항상 정규 형태이고 **어떤 경우에도 바뀌지 않는다** — 이름이 겹쳐 격리된 파일도 이 값은 그대로다 (2.3.1절). 파싱·짝 탐색·아카이브 색인의 기준이고 MEF `UNIQNAME`으로 전달된다 |
| `NAMECLSH` | 조건부 | (없음) | (없음) | ACQ | 이름이 겹쳐 `clash/`로 격리된 경우에**만** `T`. 카드의 존재가 곧 신호이므로 `F`를 넣지 않는다 (2.3.1절) |

> **`EXPID`·`EXPNUM` 은 이 규격에 없다.** 규격 v1.0~v1.2 초기 기술에는 있었으나, 레거시 실측 헤더가 `FILENAME` 하나로 날짜+연번을 이미 담고 있음을 확인하고 **그 keyword 를 이어받는 쪽으로 정리했다**(2026-08-12 확정). 노출 식별은 `UNIQNAME`(정본)·`FILENAME`(실제 이름)·`CTRLTAG`(짝의 어느 쪽) 셋으로 완결된다. 판단 근거는 2.3.1절 「왜 `FILENAME`·`UNIQNAME` 인가」 참고.

### 5.3 Raw Geometry 선언

4장의 배치를 **하드코딩 없이 읽을 수 있도록** 헤더가 스스로 기술한다. converter는 이 값과 자기 상수를 대조해 불일치를 잡아야 한다.

| Keyword | 상태 | 값 | 설명 |
| --- | --- | ---: | --- |
| `RAWNAX1` | 필수 | `19200` | raw 폭. `NAXIS1`과 같아야 한다 |
| `RAWNAX2` | 필수 | `9400` | raw 높이. `NAXIS2`와 같아야 한다 |
| `NXTILE` | 필수 | `16` | X 방향 amp tile 수 (chip 2 × strip 8) |
| `NAMPRAW` | 필수 | `32` | **이 파일에 담긴 amplifier 수** (chip 2 × amp 16) |
| `RAWXTILE` | 필수 | `1200` | amp tile 폭 |
| `AMPDATA` | 필수 | `1152` | tile당 active column |
| `OVERSCNX` | 필수 | `48` | tile당 local X overscan column |
| `PRESCANX` | 필수 | `0` | X prescan column |
| `OSCNPATT` | 필수 | `'RRRRLLLL'` | strip 1–8의 overscan 위치 (R=오른쪽, L=왼쪽) |
| `NSTRIP` | 필수 | `8` | chip당 strip 수 |
| `NEND` | 필수 | `2` | strip당 독출단 수 (TOP/BOT) |
| `AMPPCD` | 필수 | `16` | **chip당 amplifier 수** (`NSTRIP × NEND`) |
| `STRIPDIR` | 필수 | `'+X'` | strip 번호 증가 방향 |
| `TOPROWS` | 필수 | `4616` | TOP half active row |
| `BOTROWS` | 필수 | `4616` | BOT half active row |
| `MIDOVSCY` | 필수 | `168` | 중앙 Y overscan row 총수 |
| `MIDOSCB` | 필수 | `84` | 그중 BOT half에서 나온 row 수 (**실측 확인 필요**) |
| `MIDOSCT` | 필수 | `84` | 그중 TOP half에서 나온 row 수 (**실측 확인 필요**) |
| `ROWORDR` | 필수 | `'CCD'` | **4.2절 행 순서 규약. 잘못 쓰면 TOP half가 Y 반전된다** |
| `RDDIRT` | 필수 | `'-Y'` | **TOP amp의 물리적 독출 진행 방향.** MEF amp header `READDIR`로 전달 |
| `RDDIRB` | 필수 | `'+Y'` | **BOT amp의 물리적 독출 진행 방향** |
| `CHIPFLP` | 필수 | `'None'` | chip별 OSU식 flip 없음 (DECISION_LOG D-003) |
| `READMODE` | 필수 | `'64AMP'` | 카메라 전체 독출 모드 |
| `READARCH` | 필수 | `'8STRIPx2END'` | 독출 구조 |
| `CCDXBIN` | 필수 | `1` | X binning. v1.0은 1만 허용 |
| `CCDYBIN` | 필수 | `1` | Y binning. v1.0은 1만 허용 |
| `CCDSUM` | 권장 | `'1 1'` | IRAF 관례 binning 표기 |

불변식(파일 자기검사에 쓸 것):

```text
RAWNAX1 = NXTILE * RAWXTILE                       19200 = 16 * 1200
RAWXTILE = AMPDATA + OVERSCNX + PRESCANX          1200 = 1152 + 48 + 0
RAWNAX2 = BOTROWS + MIDOVSCY + TOPROWS            9400 = 4616 + 168 + 4616
MIDOVSCY = MIDOSCB + MIDOSCT                      168 = 84 + 84
AMPPCD = NSTRIP * NEND                            16 = 8 * 2
NAMPRAW = NXTILE * NEND                           32 = 16 * 2
NAMPS = NCCD * AMPPCD                             64 = 4 * 16
```

### 5.4 Detector · Camera 구성

| Keyword | 상태 | 예시 | 출처 | 설명 |
| --- | --- | --- | --- | --- |
| `DETECTOR` | 필수 | `'e2v CCD290-99'` | SITE | detector model |
| `CAMNAME` | 필수 | `'KMT-CEU'` | SITE | 카메라 시스템 |
| `CAMVER` | 필수 | `'CEU-v2.1'` | SITE | 카메라/전자부 버전 |
| `DETTYPE` | 필수 | `'SCIENCE'` | SITE | |
| `INSTRUME` | 필수 | `'KMTS'` | SITE | instrument name |
| `NCCD` | 필수 | `4` | SITE | 카메라 전체 science CCD 수 |
| `NAMPS` | 필수 | `64` | SITE | 카메라 전체 amplifier 수 |
| `PIXSIZE` | 권장 | `10.0` | SITE | micron |
| `PIXSCALE` | 권장 | `0.395` | SITE | arcsec/pixel (Gaia DR3 실측, CR-002) |
| `CCDSN1` | 권장 | chip1 시리얼 | SITE | CCD 개체 추적 |
| `CCDSN2` | 권장 | chip2 시리얼 | SITE | |

**Mosaic geometry** — raw 파일 1개는 chip 2개만 담지만, converter가 `DETSEC`(mosaic 좌표)을 계산하려면 **4-chip 배치 상수**가 필요하다. 현재 converter는 이 값들을 소스에 하드코딩하고 있으므로, raw가 실어 주면 사이트별 검증이 가능해진다.

| Keyword | 상태 | 값 | 출처 | 설명 |
| --- | --- | --- | --- | --- |
| `DETSIZE` | 필수 | `'[1:18892,1:19397]'` | SITE | mosaic 전체 크기 |
| `CCDCOLS` | 필수 | `9216` | SITE | chip 1개의 active column (`NSTRIP × AMPDATA`) |
| `CCDROWS` | 필수 | `9232` | SITE | chip 1개의 active row (`TOPROWS + BOTROWS`) |
| `COLGAP` | 필수 | `460` | SITE | chip 간 X 간격 [pixel] |
| `ROWGAP` | 필수 | `933` | SITE | chip 간 Y 간격 [pixel] |

```text
CCDCOLS = NSTRIP * AMPDATA                        9216 = 8 * 1152
CCDROWS = TOPROWS + BOTROWS                       9232 = 4616 + 4616
DETSIZE X = 2*CCDCOLS + COLGAP                    18892 = 2*9216 + 460
DETSIZE Y = 2*CCDROWS + ROWGAP                    19397 = 2*9232 + 933
```

chip의 mosaic 원점은 `M`,`K`가 위쪽 행, `N`,`T`가 아래쪽 행이고 `M`,`N`이 왼쪽 열이다 (converter `CHIP_X0` / `CHIP_Y0`).

### 5.5 Controller 정체성 · Telemetry → MEF `TELEMETRY`

**파일마다 다른 값이다.** MK 파일은 controller 1을, NT 파일은 controller 2를 기술한다. converter는 이 값들로 `TELEMETRY` table의 2개 row와 PRIMARY의 `CTRL1*` / `CTRL2*` 카드를 채운다.

| Keyword | 상태 | 예시 | 출처 | MEF 목적지 |
| --- | --- | --- | --- | --- |
| `CONTROLL` | 필수 | `'STA ARCHON'` | SITE | PRIMARY `CONTROLL` |
| `NCTRL` | 필수 | `2` | SITE | PRIMARY `NCTRL`, `TELEMETRY` 헤더 |
| `CTRLID` | 필수 | `1` (MK) / `2` (NT) | ACQ | `TELEMETRY.CTRLID`, amp `CTRLID` |
| `CTRLNAME` | 필수 | `'ARCHON-SSO-1'` | SITE | PRIMARY `CTRL1ID` / `CTRL2ID` |
| `CTRLSN` | 필수 | 컨트롤러 시리얼 | ARCHON | PRIMARY `CTRL1SN` / `CTRL2SN` |
| `CTRLFW` | 필수 | firmware 버전 | ARCHON | PRIMARY `CTRL1FW` / `CTRL2FW`, `TELEMETRY.FWVERSION` |
| `CTRLVER` | 필수 | `'ARCHON-v1.0'` | SITE | PRIMARY `CTRLVER` |
| `CTRLSTAT` | 필수 | `'OK'` / `'WARN'` / `'ERROR'` | ARCHON | `TELEMETRY.STATUS` |
| `CTRLERR` | 필수 | `0` (정상) | ARCHON | `TELEMETRY.ERRORFLAG` |
| `BCKTEMP` | 필수 | `28.4` | ARCHON | `TELEMETRY.BOARDTEMP` [degC] |
| `READTIME` | 필수 | `14.2` | ACQ | `TELEMETRY.READTIME` [s] |
| `FRAMENO` | 권장 | `1274` | ARCHON | controller frame counter |
| `BUFNO` | 권장 | `1` | ARCHON | 사용한 Archon frame buffer |
| `ACFFILE` | 필수 | `'kmtnet_ceu_v1.acf'` | ACQ | 적용된 Archon 설정 파일 |
| `TIMCONF` | 필수 | `'CEU_TIM_v1.0'` | SITE | PRIMARY `TIMCONF` |
| `TIMVER` | 필수 | `'TIM-v1.0'` | SITE | PRIMARY `TIMVER` |
| `BIASVER` | 필수 | `'BIAS-v1.0'` | SITE | PRIMARY/`VOLTINFO` `BIASVER` |
| `CLKVER` | 필수 | `'CLK-v1.0'` | SITE | PRIMARY/`VOLTINFO` `CLKVER` |
| `WBTYPE` | 권장 | `'STA Differential Board'` | SITE | PRIMARY `WBTYPE` |
| `ELECSYS` | 권장 | `'KMT-CEU'` | SITE | PRIMARY `ELECSYS` |
| `SIGELEC` | 권장 | `'STA_DIFF_VIDEO'` | SITE | PRIMARY `SIGELEC` |

`CTRLNAME` / `CTRLSN` / `CTRLFW`는 카메라 완성 후에야 확정되는 값이다. 현행 `../project_management/science/CALIBRATION_TRACKER.md`에는 아직 이 항목이 없으므로 추적 항목으로 추가할 예정이다 (OI-9의 tracker 항목 추가와 함께 처리). **raw가 이 값을 실어 주지 않으면 MEF는 영원히 `UNKNOWN`이다.**

#### 5.5.1 amp ↔ 전자계통 매핑 → MEF `MODULE` / `CHANNEL` / `XTALKGROUP`

MEF는 amp extension마다 `MODULE`(컨트롤러 모듈)과 `CHANNEL`(비디오 채널)을 갖고, `AMPINFO.XTALKGROUP`이 여기서 파생된다. **이건 설치 시의 실제 배선이라 컨트롤러만 아는 사실인데, 현행 converter는 amp 번호에서 규칙적으로 추정하고 있다.**

```python
# kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py:520-521 — "placeholder"로 명시돼 있다
card("MODULE",  1 + ((amp - 1) // 8), "controller module placeholder"),
card("CHANNEL", 1 + ((amp - 1) % 8),  "controller channel placeholder"),
```

배선이 이 가정과 다르면 **crosstalk 보정이 엉뚱한 amp 묶음에 적용된다.** crosstalk은 같은 비디오 보드를 공유하는 채널 사이에서 생기므로 `XTALKGROUP`이 틀리면 계수 측정 자체가 무의미해진다. 따라서 raw가 실제 매핑을 실어야 한다.

| Keyword | 상태 | 예시 | 설명 |
| --- | --- | --- | --- |
| `AMPMAP` | 필수 | `'EXPLICIT'` | `EXPLICIT`이면 아래 표가 유효. `DEFAULT`면 converter의 추정식을 쓴다는 선언 |
| `AMOD<nn>` | 필수 | `1` | raw-local amp `nn`의 controller module |
| `ACHN<nn>` | 필수 | `3` | raw-local amp `nn`의 video channel |

`<nn>`은 **raw-local amp 번호 01–32**이며 다음과 같이 정의한다.

```text
nn = (chip 순번 - 1) * AMPPCD + a          chip 순번: CHIP1=1, CHIP2=2
a  = 1..8   -> TOP  end, strip a
a  = 9..16  -> BOT  end, strip a-8
```

converter는 `AMPID(global) = AMP_BASE[chip] + a`로 MEF amp에 연결한다 (`AMP_BASE`: M=0, K=16, N=32, T=48). 예를 들어 NT 파일의 `nn=17`은 `CHIP2=T`의 `a=1`이므로 `T01T`, global `AMPID=49`이다.

`XTALKGROUP`은 raw에 넣지 않는다. converter가 `C<CTRLID>M<MODULE>` 규칙으로 파생한다.

### 5.6 전압 Telemetry → MEF `VOLTINFO`

Archon의 bias/clock 전압을 **인덱스 keyword 묶음**으로 기록한다. 8자 제한 안에서 항목 수를 늘릴 수 있고 `VOLTINFO` table 컬럼과 1:1로 대응한다.

| Keyword | 상태 | 예시 | `VOLTINFO` 컬럼 |
| --- | --- | --- | --- |
| `VOLTN` | 필수 | `9` | (row 수) |
| `VOLT<n>` | 필수 | `'VOD'` | `VOLTNAME` |
| `VSET<n>` | 필수 | `26.0` | `SETPOINT` |
| `VMEA<n>` | 필수 | `25.98` | `MEASURED` |
| `VUNI<n>` | 권장 | `'V'` | `UNIT` |
| `VSTA<n>` | 권장 | `'OK'` | `STATUS` |
| `VOLTSTAT` | 필수 | `'OK'` / `'PARTIAL'` / `'UNKNOWN'` | `VOLTINFO` 헤더 `VOLTSTAT` |

`<n>`은 `1`부터 `VOLTN`까지. 최소 기록 항목 (MEF `VOLTINFO`의 초기 9종과 동일):

```text
VOD, VRD, VOG, VSS, VDD, PCLKH, PCLKL, SCLKH, SCLKL
```

예:

```text
VOLTN   =                    9 / number of voltage telemetry entries
VOLT1   = 'VOD     '           / voltage name
VSET1   =                 26.0 / commanded setpoint [V]
VMEA1   =                25.98 / measured value [V]
VUNI1   = 'V       '
VSTA1   = 'OK      '
```

컨트롤러가 더 많은 채널을 보고하면 `VOLTN`을 늘려 그대로 싣는다. 측정값이 없으면 `VMEA<n> = -999.0`, `VSTA<n> = 'NC'`, `VOLTSTAT = 'PARTIAL'`.

### 5.7 시각 · 노출

| Keyword | 상태 | 예시 | 출처 | 설명 |
| --- | --- | --- | --- | --- |
| `TIMESYS` | 필수 | `'UTC'` | ICS | time system |
| `DATE-OBS` | 필수 | `'2026-01-16T14:23:25.467'` | ICS | **ICS가 `SHOPEN`(셔터 개방)을 지시한 UTC 시각.** BIAS/DARK는 ERASE 완료 시각. 최소 초 단위, **밀리초 권장**. 정의 근거는 아래 |
| `MJD-OBS` | 권장 | `61056.599...` | ACQ | `DATE-OBS`와 같은 순간. 배정밀도로 기록 |
| `UT` | 권장 | `'2026-01-16T14:23:25'` | ICS | UTC timestamp |
| `TSHOPEN` | 필수 | `'14:23:25.467'` | ICS | 셔터 열림 시각 |
| `TSHSHUT` | 필수 | `'14:24:25.470'` | ICS | 셔터 닫힘 시각 |
| `EXPTIME` | 필수 | `60.0` | ACQ | 요청 노출 시간 [s]. **sentinel 금지** |
| `EXPMEAS` | 권장 | `60.003` | ARCHON | 컨트롤러 트리거 타임스탬프로 측정한 실제 노출 [s] |
| `DARKTIME` | 필수 | `74.2` | ACQ | 누적 dark time [s] |
| `SHUTTER` | 필수 | `'OPEN'` / `'CLOSED'` | ICS | 노출 중 셔터 사용 여부 |
| `SHUTOP` | 권장 | `'STANDBY'` | ICS | 셔터 운용 상태 |

`DATE-OBS`는 **pair 양쪽이 같아야 한다.** 셔터는 하나이고 노출도 하나다. 값이 다르면 두 컨트롤러의 트리거 동기가 깨진 것이므로 그 노출은 의심 대상이다.

> **`DATE-OBS`를 "셔터 개방 지시 시각"으로 정의하는 이유 (2026-08-12 확정).**
>
> **실기에서 "셔터가 실제로 열린 시각"은 알 수 없는 값이다.** 카메라 셔터는 HE 박스에서 나오는 TTL 신호가 구동하고, AUX 제어 SW는 블레이드 리밋 스위치를 **읽기만** 한다 (`TCSAgent/__reference/KMTNet AUX control remote commands` 4-2절, DevNote 9.2.2). 개방 완료를 ICS에게 알려 주는 경로가 없다. 그러므로 ICS가 헤더에 넣을 수 있는 시각은 **자기가 개방을 지시한 순간의 OS 시각**뿐이다.
>
> 레거시는 `K.IC>OBS STATUS: SHOPEN Shutter=Open` 응답을 받은 뒤(개방 지시 +0.15초)의 시각을 썼다. 그러나 그 값도 "블레이드가 열렸다"가 아니라 "IC가 지시를 접수했다"였고, **실기의 블레이드 주행은 약 5초**다 — 60초 노출에서 8%에 해당하므로 알 수 없는 값을 모사하는 것보다 **정의를 지시 시점으로 옮기는 편**이 정확하다.
>
> 셔터 개폐 지연에 의한 실효 노출시간 보정은 헤더의 `DATE-OBS`/`EXPTIME`이 아니라 **shutter correction(별도 calibration)의 몫**이다. `EXPMEAS`(컨트롤러 트리거 타임스탬프 실측)가 있으면 그것과 대조할 수 있다.

### 5.8 관측 식별

| Keyword | 상태 | 예시 | 출처 | 설명 |
| --- | --- | --- | --- | --- |
| `IMAGETYP` | 필수 | `'OBJECT'` | ICS | 아래 통제 어휘 |
| `OBSTYPE` | 필수 | `'OBJECT'` | ICS | `IMAGETYP`과 같은 값 |
| `OBJECT` | 필수 | `'BLG11'` | ICS | 관측 대상/필드명 |
| `FIELDID` | 권장 | `'BLG11'` | ICS | KMTNet field ID. 없으면 `OBJECT` |
| `PROJID` | 권장 | 프로그램 ID | ICS | |
| `OBSERVER` | 권장 | 관측자 | ICS | |
| `FILTER` | 필수 | `'V'` | ICS | 광로에 있는 필터명 |
| `FILNUM` | 권장 | `3` | ICS | 필터 선택기 위치 |

`IMAGETYP` 통제 어휘 — ICS가 받는 명령어 집합(`../ics_sim/ics_sim/state.py`의 `IMAGE_TYPES`)과 일치시킨다. **대문자**로 기록한다. L1 파이프라인의 master frame 생성기가 `BIAS` / `FLAT` / `OBJECT`를 문자열 비교로 검사한다.

```text
BIAS, DARK, OBJECT, FLAT, DOMEFLAT, SKY, STANDARD
```

특성 측정용 프레임은 `../cam_char/`의 dataset 규약을 따르되 위 어휘를 벗어나면 `IMAGETYP='TEST'`로 두고 `DATASET` / `FILENUM`으로 구분한다.

### 5.9 관측소 · TCS Pointing

전부 **ICS가 TC에 질의해 중계**하는 값이다. pair 양쪽에 같은 값이 들어간다.

| Keyword | 상태 | 설명 |
| --- | --- | --- |
| `OBSERVAT` | 필수 | 관측소. **`CTIO` / `SAAO` / `SSO` / `TESTBED` 중 하나.** converter(v2.2.0)는 MEF 파일명 prefix를 파일명 `<SITE>`에서 유도하고 이 값과 교차 검증한다 — 불일치는 오류 (2.3절, D-011) |
| `SITEID` | 필수 | site identifier (`OBSERVAT`와 동일값 허용) |
| `TELESCOP` | 필수 | `'KMTNet 1.6m'` |
| `TELID` | 권장 | ICS relay의 telescope ID |
| `LATITUDE` | 필수 | 사이트 위도 |
| `LONGITUD` | 필수 | 사이트 경도 |
| `ELEVATIO` | 필수 | 사이트 고도 [m] |
| `RADECSYS` | 필수 | `'ICRS'` |
| `RA` | 필수 | 망원경 적경 |
| `DEC` | 필수 | 망원경 적위 |
| `EQUINOX` | 필수 | `2000.0` |
| `HA` | 필수 | hour angle |
| `ST` | 필수 | local sidereal time |
| `SECZ` | 필수 | airmass |
| `ALT` | 필수 | 망원경 고도 [deg] |
| `AZ` | 필수 | 망원경 방위 [deg] |
| `TCSLINK` | 필수 | TCS 통신 상태 |
| `TCSARC` | 권장 | TCS auto recovery 상태 |
| `TCSQDATE` | 필수 | 마지막 TCS 질의 UTC |
| `TCSUDATE` | 필수 | 마지막 TCS 갱신 UTC |
| `TCSDRIVE` | 필수 | 망원경 구동 상태. **converter는 `TCSDRIVE`를 먼저 찾고 없으면 `TCSDRIV`를 본다. `TCSDRIVE`(8자)로 쓸 것** |
| `TELMOVE` | 필수 | 망원경 이동 상태 |
| `TCSLIMIT` | 권장 | limit 상태 |
| `EXECODE` | 선택 | ICS relay 필드 |

> TC 질의가 실패하면 레거시는 노출을 멈추지 않고 **TCS 필드가 빈 채로** 저장했다. 신규도 같은 방침이되, 5.0절 sentinel로 "값이 없었다"는 사실이 헤더에 남아야 한다. 좌표가 sentinel인 프레임은 astrometry 단계에서 걸러진다.

### 5.10 AUX · 필터/셔터 · 초점 · 돔 · 열 환경

`AUXSTATUS` 중계 값이다. **ICS가 TC로부터 받은 key=value는 전부 기록한다** (pass-through). 아래는 그중 converter가 MEF PRIMARY로 옮기는 항목이므로 반드시 있어야 한다.

| 그룹 | Keywords |
| --- | --- |
| AUX link | `AUXLINK`, `AUXARC`, `AUXQDATE`, `AUXUDATE` |
| 필터/셔터 | `FSSTAT`, `FILTOP`, `FILNUM`, `FILTER`, `SHUTOP`, `SHUTTER` |
| FSA 환경 | `FSATEMP`, `FSAHUM`, `FSADEW`, `FSAALRM` |
| 초점 액추에이터 | `FASTAT`, `FAFOCUS`, `FATILTNS`, `FATILTEW`, `FAPOSS`, `FALIMS`, `FAPOSE`, `FALIME`, `FAPOSW`, `FALIMW` |
| 돔 | `DSSTAT`, `DSUP`, `DSLW`, `DSSAF`, `DSAUTO`, `DSALT`, `DSAZ`, `DSTELALT`, `DSTELAZ`, `DALTERR`, `DAZERR` |
| 미러/칠러/환경 | `MCSTAT`, `MCPOS`, `CHSTAT`, `ENSTAT`, `ENFAN` |
| 열/듀어 | `CCDTEMP`, `DEWPRES`, `PT30N1`, `PT30N2`, `CHARCOAL`, `AIR_IN`, `AIR_OUT`, `GLYC_IN`, `GLYC_OUT` |
| 영상 점검 | `CHKIMG`, `CHKIMG_C` |
| 환경 센서(추가) | `ENS1`..`ENS7`, `CHOP`, `CHSET`, `CHPROC` |

**칩별 온도** — 레거시는 파일 1개가 CCD 1개였으므로 `CCDTEMP` 하나로 충분했다. 신규 raw는 파일 1개에 chip이 2개이므로 다음을 **추가로** 요구한다.

| Keyword | 상태 | 설명 |
| --- | --- | --- |
| `CCDTMP1` | 필수 | `CHIP1` 온도 [degC] |
| `CCDTMP2` | 필수 | `CHIP2` 온도 [degC] |
| `CCDTEMP` | **필수** | 대표값 (두 칩 평균 또는 듀어 대표 센서). **L1 파이프라인이 `CCDTEMP`를 이름으로 지정해 L1 primary로 전달하므로**(`mef_pipeline/kmt_ceu_preproc/io_l1.py`의 `CARRY_KEYS`) 반드시 있어야 한다 |

### 5.11 Pair 일관성 규칙

| 구분 | Keywords |
| --- | --- |
| **반드시 동일** | `DATE-OBS`, `MJD-OBS`, `EXPTIME`, `DARKTIME`, `TSHOPEN`, `TSHSHUT`, `IMAGETYP`, `OBSTYPE`, `OBJECT`, `FIELDID`, `PROJID`, `FILTER`, `OBSERVAT`, `SITEID`, `TELESCOP`, `RA`, `DEC`, `EQUINOX`, `HA`, `ST`, `SECZ`, `ALT`, `AZ`, 모든 TCS/AUX relay 필드, 5.3절 geometry 전체, `RAWVER`, `RAWGROUP`, `CHIPLIST`, `NUMFILES` |
| **반드시 상이** | `UNIQNAME`, `FILENAME`, `PAIRFILE`, `CTRLTAG`, `CHIPS`, `CHIP1`, `CHIP2`, `CTRLID`, `CTRLNAME`, `CTRLSN`, `CTRLFW` |
| **다를 수 있음** | `NAMECLSH`(한쪽만 겹칠 수 있다), `DATE`, `CTRLSTAT`, `CTRLERR`, `BCKTEMP`, `READTIME`, `FRAMENO`, `BUFNO`, `VOLT*`/`VSET*`/`VMEA*`, `CCDTMP1`, `CCDTMP2`, `CHECKSUM`, `DATASUM` |

### 5.12 raw에 넣지 **않는** keyword

MEF keyword 정의서(`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`)의 항목 중 아래는 **raw 헤더에 넣지 않는다.** raw 단계에 그 정보가 존재하지 않거나, raw가 실어봐야 converter가 덮어쓰는 값들이다.

| 분류 | Keyword | 이유 |
| --- | --- | --- |
| MEF 구조 | `XTENSION`, `PCOUNT`, `GCOUNT`, `EXTNAME`, `EXTTYPE`, `NAXIS`/`NAXIS1`/`NAXIS2`(amp), HDU 배치 | MEF 파일 구조 자체. raw는 single HDU라 대응물이 없다 |
| 제품 정체성 | `DATAPROD`, `PRODVER`, `PIPEVER`, `GEOMVER`, `CREATOR`(MEF), `FILENAME`(MEF), `DATE`(MEF) | converter가 자기 버전과 출력 파일명으로 생성. raw는 `RAWPROD`/`RAWVER`/자기 `FILENAME`을 따로 갖는다 |
| Section 좌표 | `CCDSEC`, `AMPSEC`, `DETSEC`, `DATASEC`, `BIASSEC`, `PRESEC`, `TRIMSEC`, `RAWDATA`, `RAWBIAS`, `AMPINFO`의 `*X0/*X1/*Y0/*Y1` | 전부 5.3·5.4절 geometry에서 **계산되는 값**. raw가 중복해서 실으면 불일치 원천이 된다 |
| Amp 식별 | `AMPID`, `AMPSEQ`, `AMPNAME`, `STRIPID`, `ENDID`, `CHIPID`, `CCDNAME`, `RAWFILE`, `REALDATA` | 같은 이유로 파생값. raw는 `CHIP1`/`CHIP2`와 5.5.1절 amp 번호 규칙만 준다 |
| Amp calibration | `GAIN`, `RDNOISE`, `SATURAT`, `SATLEVEL`, `LINMAX` | calibration DB 소관. 노출 시점에 컨트롤러가 아는 값이 아니다 |
| Crosstalk | `XTALKINFO` 전체 (4096행), `XTALKGROUP` | calibration DB 소관. `XTALKGROUP`은 `CTRLID`+`MODULE`에서 파생 |
| WCS | `CTYPE1/2`, `CRVAL1/2`, `CRPIX1/2`, `CD1_1`..`CD2_2`, `WCSDIM` | L0에서는 placeholder이고 확정 해는 L1에서 만든다 |
| 파생 시각 | `JD` | converter가 `DATE-OBS`에서 계산. raw는 `DATE-OBS`(+`MJD-OBS`)만 |
| 목업 전용 | `MOCKDATA`, `ORIGFILE`, `ORIGFMT`, `CONVPROG`, `AMPPACK` | 구형 32-amp MEF 목업 변환기 전용 |

**경계선상의 4개** — 현행 converter는 이 값들을 **MK 헤더에서 읽고 있지만**(`v("XTALKVER","UNMEASURED")` 등) 실제로는 calibration DB 소관이다.

| Keyword | 현행 동작 | 권고 |
| --- | --- | --- |
| `XTALKVER` | raw에서 읽고 없으면 `'UNMEASURED'` | caldb에서 주입 (C-11) |
| `XTALKCAL` | converter가 `False`로 고정 | caldb 연동 시 해제 |
| `REFVER` | raw에서 읽고 없으면 `'N/A'` | caldb에서 주입 (C-11) |
| `CATVER` | raw에서 읽고 없으면 `'N/A'` | caldb에서 주입 (C-11) |

정리하면 — **MEF 전용 헤더는 raw에 넣을 필요도 없고 넣을 정보도 없다.** 다만 아래 3종은 이름만 보면 MEF 쪽 같지만 **컨트롤러/사이트만 아는 사실**이라 raw가 반드시 실어야 한다.

1. `MODULE` / `CHANNEL` — 실제 배선 (5.5.1절)
2. `READDIR` — 물리적 독출 방향 (`RDDIRT`/`RDDIRB`, 5.3절)
3. `DETSIZE` / `COLGAP` / `ROWGAP` / `AMPPCD` — mosaic 배치 상수 (5.3·5.4절)

## 6. Converter가 실제로 읽는 값과 누락 시 영향

현행 `kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) 기준이다. **converter는 MK 헤더만 읽는다** — NT 헤더는 `BITPIX`/`NAXIS`만 확인하고 메타데이터는 쓰지 않는다 (`convert()`가 두 chip 모두에 `mk_hdr`를 넘긴다).

### 6.1 없으면 변환이 실패하는 값

| Keyword | 조건 | 동작 |
| --- | --- | --- |
| `BITPIX` | `!= 16` | `ValueError: Only BITPIX=16 is supported` |
| `NAXIS1` × `NAXIS2` | `!= 19200 × 9400` | `ValueError: MK/NT has unexpected shape` |
| END 카드 | 없음 | `ValueError: No END card in FITS header` |
| 파일명 `<SITE>` ↔ `OBSERVAT` | 불일치 | `ValueError: Filename site code ... conflicts with OBSERVAT=...` (2.3절, D-011) |

### 6.2 없으면 **조용히 틀린 값**이 들어가는 것 — 가장 위험

| Keyword | 누락 시 fallback | 결과 |
| --- | --- | --- |
| `DATE-OBS` | **변환을 실행한 시각(now)** | MEF의 `DATE-OBS` / `MJD-OBS` / `JD`가 전부 관측과 무관한 값이 된다. 오류 없이 통과한다 |
| `BZERO` | `32768` 가정 | raw가 signed(`BZERO=0`)면 전 픽셀이 32768만큼 어긋난다 |
| `OBSERVAT` | 파일명 `<SITE>`에서 prefix 유도 (규격 파일명이면 정확), 파일명도 비규격이면 prefix `kmt` | 교차 검증이 불가능해져 설정 오배포를 잡지 못한다. 파일명까지 비규격이면 출력 MEF 이름이 사이트 규약(`kmtc`/`kmts`/`kmta`/`kmtt`)을 벗어난다 |
| `EXPTIME`, `DARKTIME` | `0.0` | BIAS와 구분되지 않는다 |
| `TSHOPEN` | `''` | MEF `UT`가 `DATE-OBS`로 대체된다 |
| `EQUINOX` | `2000.0` | |
| `RA`, `DEC` | `'00:00:00.00'`, `'+00:00:00.0'` | 겉보기엔 유효한 좌표로 보인다 |

### 6.3 없으면 placeholder가 되는 것 — 5.5·5.6절이 메우려는 구멍

| Raw에 필요한 값 | 없을 때 MEF 값 |
| --- | --- |
| controller identity | `CTRL1ID` / `CTRL1SN` / `CTRL1FW` / `CTRL2ID` / `CTRL2SN` / `CTRL2FW` = `'UNKNOWN'` |
| controller telemetry | `TELEMETRY`: `FWVERSION='UNKNOWN'`, `BOARDTEMP=-999.0`, `READTIME=-1.0`, `STATUS='UNKNOWN'`, `ERRORFLAG=-1` |
| 전압 telemetry | `VOLTINFO`: 9행 전부 `SETPOINT=0.0`, `MEASURED=0.0`, `STATUS='UNKNOWN'` |
| 설정 버전 | `CTRLVER` / `TIMVER` / `BIASVER` / `CLKVER` = 기본 문자열 |

`XTALKINFO`(4096행)와 amp별 `GAIN`/`RDNOISE`/`SATURAT`/`LINMAX`는 **raw로 채우지 않는다.** calibration DB 소관이다.

### 6.4 그 밖에 MK 헤더에서 그대로 복사되는 값

`ORIGIN`, `BUNIT`, `DETECTOR`, `CCDXBIN`, `CCDYBIN`, `TELESCOP`, `LATITUDE`, `LONGITUD`, `ELEVATIO`, `OBSERVER`, `OBJECT`, `FIELDID`, `PROJID`, `IMAGETYP`, `OBSTYPE`, `TSHSHUT`, `UNIQNAME`, `INSTRUME`, `XTALKVER`, `REFVER`, `CATVER`, `TIMESYS`, `RADECSYS`, `HA`, `ST`, `SECZ`, `ALT`, `AZ`, `TCSLINK`, `TCSARC`, `TCSQDATE`, `TCSUDATE`, `TCSDRIVE`, `TELMOVE`, 5.10절 AUX/초점/돔/열 keyword 전체.

이 중 `FILTER` · `PROJID` · `IMAGETYP` · `OBJECT` · `OBSTYPE` · `RA` · `DEC` · `HA` · `ST` · `SECZ` · `ALT` · `AZ` · `UT`는 **64개 amp extension header에도 반복 기록**된다.

### 6.5 MEF keyword 전량 대조표

`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`의 모든 항목을 출처별로 분류한 결과다. 출처가 **raw**인 항목은 전부 5장에 대응 keyword가 있어야 한다.

| MEF 문서 절 | 항목 | 출처 | Raw 규격 위치 |
| --- | --- | --- | --- |
| 4.1 Product identity | `SIMPLE` `BITPIX` `NAXIS` `EXTEND` `ORIGIN` `BUNIT` | raw | 5.1 |
| | `DATE` `CREATOR` `DATAPROD` `PRODVER` `PIPEVER` | converter | 5.12 |
| 4.2 Raw provenance | `RAWGROUP` `CHIPLIST` `NUMFILES` | raw | 5.2 |
| | `RAWNAX1` `RAWNAX2` `RAWXTILE` `AMPDATA` `OVERSCNX` `PRESCANX` `MIDOVSCY` `TOPROWS` `BOTROWS` `CHIPFLP` | raw | 5.3 |
| | `MKFILE` `NTFILE` | converter (raw `FILENAME`/`PAIRFILE`에서) | 5.2 |
| 4.3 Detector/camera | `DETECTOR` `CAMNAME` `CAMVER` `DETTYPE` `NCCD` `NAMPS` `PIXSCALE` `PIXSIZE` | raw | 5.4 |
| | **`AMPPCD`** `NSTRIP` `NEND` `CCDXBIN` `CCDYBIN` `READMODE` `READARCH` | raw | 5.3 |
| | **`DETSIZE`** **`COLGAP`** **`ROWGAP`** | raw | 5.4 |
| 4.4 Observatory/exposure | `OBSERVAT` `SITEID` `TELESCOP` `LATITUDE` `LONGITUD` `ELEVATIO` | raw | 5.9 |
| | `OBSERVER` `OBJECT` `FIELDID` `PROJID` `IMAGETYP` `OBSTYPE` `FILTER` | raw | 5.8 |
| | `EXPTIME` `DARKTIME` `TSHOPEN` `TSHSHUT` | raw | 5.7 |
| | `UNIQNAME` | raw | 5.2 |
| | `FILENAME` | converter | 5.12 |
| 4.5 Electronics | `INSTRUME` | raw | 5.4 |
| | `CONTROLL` `NCTRL` `CTRL1ID` `CTRL1SN` `CTRL1FW` `CTRL2ID` `CTRL2SN` `CTRL2FW` `WBTYPE` `ELECSYS` `SIGELEC` `TIMCONF` `CTRLVER` `TIMVER` `BIASVER` `CLKVER` | raw | 5.5 |
| | `XTALKVER` `XTALKCAL` `REFVER` `CATVER` | caldb (현행은 raw 조회) | 5.12 |
| 4.6 Time/TCS | `TIMESYS` `DATE-OBS` `UT` | raw | 5.7 |
| | `MJD-OBS` | raw (권장) / converter | 5.7 |
| | `JD` | converter | 5.12 |
| | `RADECSYS` `RA` `DEC` `EQUINOX` `HA` `ST` `SECZ` `ALT` `AZ` `TCSLINK` `TCSARC` `TCSQDATE` `TCSUDATE` `TCSDRIV` `TELMOVE` | raw | 5.9 |
| 4.7 AUX/focus/dome/thermal | 전 그룹 (`AUXLINK`…`CHKIMG_C`) | raw | 5.10 |
| 5.1 Amp 표준 | `XTENSION` `PCOUNT` `GCOUNT` `NAXIS1` `NAXIS2` | converter | 5.12 |
| | `BZERO` `BSCALE` `BUNIT` | raw | 5.1 |
| 5.2 Amp identity | `EXTNAME` `EXTTYPE` `REALDATA` `DATAPROD` `CHIPID` `CCDNAME` `AMPID` `AMPSEQ` `STRIPID` `ENDID` `AMPNAME` `RAWFILE` | converter | 5.12 |
| | `CTRLID` | raw | 5.5 |
| | **`MODULE`** **`CHANNEL`** | raw | **5.5.1** |
| 5.3 Amp geometry | `CHIPFLP` `STRIPDIR` `CCDSUM` | raw | 5.3 |
| | **`READDIR`** | raw (`RDDIRT`/`RDDIRB`) | **5.3** |
| | `CCDSEC` `AMPSEC` `DETSEC` `RAWDATA` `RAWBIAS` `DATASEC` `PRESEC` `BIASSEC` `TRIMSEC` | converter (파생) | 5.12 |
| 5.4 Amp calibration | `GAIN` `RDNOISE` `SATURAT` `LINMAX` | caldb | 5.12 |
| 5.5 Amp obs/WCS | `FILTER` `PROJID` `IMAGETYP` `OBJECT` `OBSTYPE` `RA` `DEC` `HA` `ST` `SECZ` `ALT` `AZ` `UT` | raw (PRIMARY와 동일값 복제) | 5.7–5.9 |
| | `CTYPE*` `CRVAL*` `CRPIX*` `CD*` `WCSDIM` | converter (placeholder) | 5.12 |
| 6 `AMPINFO` | `NAMP` `GEOMVER` | converter | 5.12 |
| | `RAWGROUP` | raw | 5.2 |
| | 나머지 컬럼 | 위 amp keyword와 동일 출처 | — |
| | `XTALKGROUP` | converter (`CTRLID`+`MODULE` 파생) | 5.5.1 |
| 7 `XTALKINFO` | 전체 | caldb | 5.12 |
| 8 `VOLTINFO` | `VOLTNAME` `SETPOINT` `MEASURED` `UNIT` `STATUS` `VOLTSTAT` `BIASVER` `CLKVER` | raw | 5.6 |
| 9 `TELEMETRY` | `CTRLID` `FWVERSION` `BOARDTEMP` `READTIME` `STATUS` `ERRORFLAG` `NCTRL` | raw | 5.5 |
| | `TELSTAT` | converter (양쪽 `CTRLSTAT`에서 파생: 둘 다 `OK`면 `OK`, 아니면 `PARTIAL`) | 5.5 |

굵게 표시한 6개(`AMPPCD`, `DETSIZE`/`COLGAP`/`ROWGAP`, `MODULE`/`CHANNEL`, `READDIR`)는 **MEF 문서에는 있는데 raw 규격 초안에서 빠졌다가 이 대조 과정에서 보강한 항목**이다.

### 6.6 L1 product가 요구하는 것

L1 전처리기는 L0 primary에서 아래를 이름으로 지정해 L1 primary로 옮긴다 (`../mef_pipeline/kmt_ceu_preproc/io_l1.py`의 `CARRY_KEYS`).

```text
ORIGIN OBSERVAT SITEID TELESCOP INSTRUME CAMNAME OBJECT FIELDID PROJID
IMAGETYP OBSTYPE EXPTIME DARKTIME FILTER DATE-OBS JD MJD-OBS TIMESYS
RA DEC EQUINOX RADECSYS CCDTEMP CHIPLIST MOCKDATA
```

`JD`(converter 생성)와 `MOCKDATA`(목업 전용)를 뺀 **23개가 전부 raw에서 와야 하며**, 위 대조표에서 모두 확인된다. 이 중 `CCDTEMP`는 초안에서 권장이었으나 L1이 이름으로 요구하므로 **필수로 올렸다**(5.10절).

파이프라인이 별도로 읽는 값: `BSCALE` `BZERO` `CHIPLIST` `DATE-OBS` `EXPTIME` `FILTER` `IMAGETYP` `OBJECT` `OBSERVAT` `XTALKCAL` — 전부 위에 포함된다. master frame 생성기는 `IMAGETYP`을 `BIAS`/`FLAT`/`OBJECT`와 **대문자 문자열 비교**하므로 5.8절 통제 어휘를 반드시 지켜야 한다.

## 7. 이 규격을 받아들이기 위한 변경점

| # | 대상 | 변경 내용 |
| --- | --- | --- |
| C-1 | `mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` | **NT 헤더도 읽어야 한다.** 현재 `convert()`는 `mk_hdr` 하나만 쓴다. `CTRL2*`와 `TELEMETRY` 2행을 채우려면 `nt_hdr`가 필요하다 |
| C-2 | 〃 | `TELEMETRY` 2행을 각 파일의 `CTRLID`/`CTRLFW`/`BCKTEMP`/`READTIME`/`CTRLSTAT`/`CTRLERR`로 채운다 |
| C-3 | 〃 | `VOLTINFO`를 `VOLTN` + `VOLT<n>`/`VSET<n>`/`VMEA<n>`/`VUNI<n>`/`VSTA<n>`에서 채운다. 행 수는 `VOLTN` |
| C-4 | 〃 | **pair 일관성 검사 추가**: `DATE-OBS`·`EXPTIME`·`RAWVER`가 다르면, 그리고 두 `UNIQNAME`의 `<YYYYMMDD>`·`<NNNNNN>` 필드가 다르면 변환 중단. (`UNIQNAME` 자체는 컨트롤러 태그가 달라 **같지 않은 것이 정상**이다 — 5.11절) |
| C-5 | 〃 | 5.3절 geometry keyword를 자기 상수와 대조. 불일치 시 중단 |
| C-6 | 〃 | `DATE-OBS` 누락 시 "현재 시각"으로 조용히 대체하지 말고 **실패**시킨다 (6.2절) |
| ~~C-7~~ | 〃 | ~~파일명 정규식 수정~~ → **완료 (D-011, converter v2.2.0).** `default_output_name()` 정규식을 사이트 코드 형식 `^(KMTC\|KMTS\|KMTA\|KMTT)\.(\d{8})\.(\d{6})\.MK\.fits$`로 개정하고, 출력 prefix를 파일명 `<SITE>`에서 유도 + `OBSERVAT` 교차 검증(불일치=오류)을 추가했다. `find_pair()`는 prefix 무관이라 변경 없음 |
| **C-11** | 〃 | `MODULE` / `CHANNEL`을 raw의 `AMOD<nn>` / `ACHN<nn>`에서 채운다. 현재 amp 번호로 추정하는 placeholder 식(`v2_1.py:520-521`)을 대체하고, `XTALKGROUP`도 그 값으로 파생 (5.5.1절) |
| **C-12** | 〃 | amp `READDIR`를 raw의 `RDDIRT` / `RDDIRB`에서 채운다. 현재 `amp<=8`이면 `-Y`로 하드코딩 |
| **C-13** | 〃 | `DETSIZE` / `COLGAP` / `ROWGAP` / `AMPPCD`를 raw 선언값과 대조. 하드코딩 상수와 다르면 중단 (C-5의 확장) |
| **C-14** | 〃 | `XTALKVER` / `REFVER` / `CATVER`를 raw가 아니라 calibration DB에서 주입 (5.12절) |
| **C-15** | 〃 | `TELEMETRY` 확장 헤더의 `TELSTAT`을 양쪽 `CTRLSTAT`에서 파생 |
| **C-8** | `ics_sim/ics_sim/hardware/archon.py` | 이 규격대로 저장하도록 구현 (현재 스텁). **계약은 이미 개정됐다 (D-012)** — `write_frame(controller, chips, path, header)` 를 채우면 되고, 저장 단위가 컨트롤러 1개(chip 2개)인 것이 시그니처에 드러나 있다. 시뮬 백엔드가 같은 계약으로 돌고 있어 참고 구현이 된다 (`hardware/sim.py`) |
| ~~**C-16**~~ | `ics_sim/ics_sim/sequencer.py` `_store()` · `ics_sim/ics_sim/rawpair.py` | **해결 (2026-08-11, D-012).** 2.5절 `Wrote` 규약 구현 완료 — 저장은 컨트롤러 단위 1파일, 통보는 그 파일이 담은 chip 2개분 논리 이름. 물리/논리 이름 생성은 신설 `rawpair.py` 로 모았고 `state.ChannelState.filename()` 은 논리 이름 생성기로 남았다. 검증은 `tests/test_raw_pair.py`(16개). 종전 서술: **2.5절 `Wrote` 규약 구현.** 현재는 CCD 1개당 파일 1개를 쓰고 `Wrote` 1회를 낸다. 신규는 컨트롤러 1개당 파일 1개를 쓰고 **그 파일이 담은 chip 2개분 `Wrote`를 논리 이름으로** 낸다. `ChannelState.filename()`의 `KMTN<ccd>.<suffix>.fits`는 **논리 이름 생성기로 남기고**, 실제 저장 경로는 `<SITE>.<suffix>.<CTRLTAG>.fits`로 분리한다 (`<SITE>`는 설정 `[node] site`에서 유도, D-011) |
| ~~C-9~~ | `ics_sim/ics_sim/telemetry.py` | **해결 (2026-08-11).** FITS 헤더용 `fits_header_dict()` 를 분리해 5.0절 규약(정수 `-1` / 실수 `-999.0` / 문자열 `'NC'`)을 따르게 했다. 레거시 메시지 계층의 `'0'` 채움은 `header_dict()` 에 그대로 남긴다 — 중계 본문은 레거시 재현이 필요하기 때문이다 (DevNote 11.2) |
| C-10 | `cam_char/archon/archon_kmtnet_labtest_v2.py` | 실험실 raw도 5.3절 geometry 선언과 5.5절 controller telemetry를 싣도록 카드 추가 |

## 8. 검증 체크리스트

Raw pair 1쌍을 archive에 넣거나 converter에 넘기기 전에 확인한다.

**구조**

- [ ] 두 파일 모두 astropy `verify('exception')` 통과
- [ ] HDU 수가 1 (extension 없음)
- [ ] `BITPIX=16`, `BZERO=32768`, `BSCALE=1`
- [ ] `NAXIS1=19200`, `NAXIS2=9400`
- [ ] 파일 크기가 헤더 블록 + 360,960,000 B

**Geometry 선언**

- [ ] 5.3절 불변식 7개가 모두 성립
- [ ] 5.4절 mosaic 불변식 4개가 모두 성립 (`DETSIZE` ↔ `CCDCOLS`/`CCDROWS`/`COLGAP`/`ROWGAP`)
- [ ] `ROWORDR` 값이 있고 converter의 전제와 일치
- [ ] `RDDIRT` / `RDDIRB`가 선언되어 있다
- [ ] `MIDOSCB + MIDOSCT = MIDOVSCY`
- [ ] `AMPMAP='EXPLICIT'`이면 `AMOD01..AMOD32` / `ACHN01..ACHN32`가 빠짐없이 있다
- [ ] `(AMOD, ACHN)` 조합에 중복이 없다

**Pair 식별**

- [ ] 파일명이 `<SITE>.<8자리>.<6자리 zero-pad>.<MK|NT>.fits` 형식, `<SITE>` ∈ {`KMTC`, `KMTS`, `KMTA`, `KMTT`} (2.3절, D-011)
- [ ] 파일명 `<SITE>`가 헤더 `OBSERVAT`와 일치 (2.3절)
- [ ] `CTRLTAG`가 `MK` / `NT`로 서로 다르다
- [ ] `PAIRFILE`이 상대 파일을 정확히 가리킨다
- [ ] 두 `UNIQNAME`의 날짜·연번 필드가 동일 (태그는 달라야 한다 — 5.11절)
- [ ] **`UNIQNAME`이 FITS *문자열* 카드이고 연번이 6자리 zero-padding을 유지한다** (5.0절)
- [ ] **`UNIQNAME`이 정규 형태다** — `<SITE>.<8자리>.<6자리>.<MK|NT>`, 접미 없음
- [ ] **`FILENAME`이 그 파일의 실제 이름과 같다** (확장자 없음. 격리된 경우 `.clash…` 접미 포함 — 2.3.1절)
- [ ] `clash/` 디렉토리가 비어 있다. 비어 있지 않으면 그 파일들은 `NAMECLSH=T`를 갖고 있고, **변환 전에 사람이 확인해야 한다**
- [ ] `CHIPS`가 `M,K` / `N,T`
- [ ] `CHIP1`+`CHIP2` 4개가 `CHIPLIST`를 빠짐없이 덮는다

**메타데이터**

- [ ] 5.11절 "반드시 동일" 항목이 전부 일치
- [ ] 5.11절 "반드시 상이" 항목이 전부 다름
- [ ] `DATE-OBS`가 실제 셔터 열림 시각 (변환/저장 시각이 아님)
- [ ] `EXPTIME` / `DARKTIME`이 sentinel이 아님
- [ ] `IMAGETYP`이 통제 어휘에 속하고 대문자
- [ ] `OBSERVAT` ∈ {`CTIO`, `SAAO`, `SSO`, `TESTBED`}
- [ ] `CTRLNAME` / `CTRLSN` / `CTRLFW`가 `UNKNOWN`이 아님
- [ ] `VOLTN ≥ 9`이고 필수 9종이 모두 포함
- [ ] `BCKTEMP` / `READTIME`이 sentinel이 아님
- [ ] `CCDTEMP` · `CCDTMP1` · `CCDTMP2`가 모두 있고 sentinel이 아님 (L1 `CARRY_KEYS`)
- [ ] 6.6절 L1 `CARRY_KEYS` 23개가 raw에 전부 존재

> **이 체크리스트 중 일부는 이미 자동 검증된다.** `ics_sim`이 규격대로 저장하게 되면서(2026-08-11, D-012) 파일 구성·이름·pair 식별·sentinel 항목은 `ics_sim/tests/test_raw_pair.py`(16개)가 매 실행 확인한다. 실기(`ics_archon`)에서 추가로 확인해야 하는 것은 **구조**(`BITPIX`/`NAXIS`/파일 크기) · **geometry 선언** · **메타데이터**(controller telemetry·전압·온도) 쪽이다 — 시뮬은 픽셀이 더미이고 실물 크기가 아니므로 그 항목들을 검증하지 못한다.

**변환 왕복**

- [ ] converter가 오류 없이 L0 MEF를 만든다
- [ ] MEF HDU 수가 69
- [ ] MEF의 `TELEMETRY` / `VOLTINFO`에 placeholder가 남아 있지 않다
- [ ] MEF amp 픽셀 총수 + raw 중앙 overscan = raw pair 픽셀 총수 (2.4절)

검증 예:

```bash
python3 -c "
from astropy.io import fits
mk = fits.open('KMTC.20260116.000001.MK.fits'); mk.verify('exception')
nt = fits.open('KMTC.20260116.000001.NT.fits'); nt.verify('exception')
a, b = mk[0].header, nt[0].header
assert len(mk) == 1 and len(nt) == 1
assert (a['NAXIS1'], a['NAXIS2']) == (19200, 9400)
assert a['BZERO'] == 32768 and a['BSCALE'] == 1
assert a['RAWNAX1'] == a['NXTILE'] * a['RAWXTILE']
assert a['RAWXTILE'] == a['AMPDATA'] + a['OVERSCNX'] + a['PRESCANX']
assert a['RAWNAX2'] == a['BOTROWS'] + a['MIDOVSCY'] + a['TOPROWS']
assert a['MIDOVSCY'] == a['MIDOSCB'] + a['MIDOSCT']
assert a['AMPPCD'] == a['NSTRIP'] * a['NEND']
assert a['NAMPRAW'] == a['NXTILE'] * a['NEND']
assert a['NAMPS'] == a['NCCD'] * a['AMPPCD']
assert a['CCDCOLS'] == a['NSTRIP'] * a['AMPDATA']
assert a['CCDROWS'] == a['TOPROWS'] + a['BOTROWS']
assert a['DETSIZE'] == '[1:%d,1:%d]' % (2*a['CCDCOLS'] + a['COLGAP'],
                                        2*a['CCDROWS'] + a['ROWGAP'])
assert (a['CTRLTAG'], b['CTRLTAG']) == ('MK', 'NT')
for h in (a, b):                                   # amp -> 전자계통 배선 맵
    if h['AMPMAP'] == 'EXPLICIT':
        wiring = [(h['AMOD%02d' % n], h['ACHN%02d' % n]) for n in range(1, 33)]
        assert len(set(wiring)) == 32, 'duplicate (MODULE, CHANNEL)'
for k in ('DATE-OBS','EXPTIME','RAWVER','OBSERVAT','FILTER'):
    assert a[k] == b[k], (k, a[k], b[k])
carry = ('ORIGIN OBSERVAT SITEID TELESCOP INSTRUME CAMNAME OBJECT FIELDID '
         'PROJID IMAGETYP OBSTYPE EXPTIME DARKTIME FILTER DATE-OBS MJD-OBS '
         'TIMESYS RA DEC EQUINOX RADECSYS CCDTEMP CHIPLIST').split()
missing = [k for k in carry if k not in a]         # L1 CARRY_KEYS (6.6절)
assert not missing, 'L1 carry keys missing: %s' % missing
assert a['UNIQNAME'].split('.')[1:3] == b['UNIQNAME'].split('.')[1:3]
print('raw pair OK:', a['UNIQNAME'])
"
```

## 9. Open Items

| ID | 항목 | 내용 | 조치 |
| --- | --- | --- | --- |
| ~~OI-1~~ | **파일명 규약** | **해결 (2026-08-07, D-009) → 재개정 (2026-08-10, D-011).** D-009는 ICD v4.0 형식 `KMTN.…`을 유지했으나, D-011이 prefix를 사이트 코드 `<SITE>` ∈ {`KMTC`,`KMTS`,`KMTA`,`KMTT`}로 개정했다 (3사이트 데이터 통합 시 동명 충돌 제거). 파일명 자체는 OBSAgent의 `FitsNum` 슬라이스와 맞지 않지만, OI-2 해결책이 `Wrote` 메시지에 레거시 형태의 논리 이름을 싣는 방식이라 문제가 성립하지 않는다 | 규격 2.3절 반영 완료. converter v2.2.0에서 정규식 개정 + `OBSERVAT` 교차 검증 추가. `<NNNNNN>` 6자리 zero-padding 필수 유지 |
| ~~OI-2~~ | **`Wrote` 4회 규약** | **해결 (2026-08-07, D-010).** 저장 단위(컨트롤러 2파일)와 통보 단위(CCD 4회)를 분리한다. ICS는 파일 1개를 쓸 때마다 그 파일이 담은 chip 2개분 `STATUS: Wrote`를 논리 이름으로 낸다. `count_wrote=4` · `FitsNum='20260807.012345'` 모두 성립 | 규격 2.5절 반영 완료. OBSAgent·`RAWNAX1` 변경 없음. `LASTFILE`이 실재 경로가 아니게 되는 부작용을 2.5절에 명시 |
| **OI-3** | `ROWORDR` / `RDDIRT` / `RDDIRB` 확정 | TOP half가 CCD 좌표 순서로 기록되는지 독출 순서인지 실기 확인 필요. MEF amp header `READDIR`의 placeholder(TOP=`-Y`, BOT=`+Y`)를 확정하는 사안이며, 규격은 값을 raw가 **선언**하도록 자리를 만들어 뒀다 | flat/star sequence test. 확정 시 `RAWVER`와 `GEOMVER` 동시 갱신 |
| **OI-9** | amp ↔ 배선 맵 실측 | `AMOD<nn>` / `ACHN<nn>`의 실제 값은 컨트롤러 결선 후에야 확정된다. 확정 전에는 `AMPMAP='DEFAULT'`로 두고 converter의 추정식을 쓰되, **`XTALKCAL=True`로 올리기 전에 반드시 `EXPLICIT`으로 교체**해야 한다 (5.5.1절) | 통합 시 배선표 작성 + Archon 채널 응답과 대조. `CALIBRATION_TRACKER.md`에 항목 추가 |
| **OI-10** | `<YYYYMMDD>` 의 기준 확정 | **잠정: UTC 날짜.** 규격 v1.0~v1.2 는 "관측 야간 기준 날짜" 로 적었으나 **레거시도 구현도 UTC 날짜를 쓴다** — CTIO `isis.20240102.log`(UTC−4) 안에 `KMTNm.20240103.023885.fits` 가 있고, `ics_sim` 은 `utcnow().strftime('%Y%m%d')` 다. **차이가 실재하는 곳은 SAAO** (UTC+2): 현지 20:00~05:00 이 UTC 18:00~03:00 이라 **한 야간이 UTC 자정을 넘어 날짜가 둘로 갈린다**. CTIO·SSO 는 야간 안에서 UTC 날짜가 상수라 문제가 드러나지 않는다. 야간 기준으로 가면 야간 경계(정오 UTC 등)를 정의해야 하고 사이트별로 달라진다 | **이충욱(LEECU)과 협의해 확정.** 결정 시 (1) 이 절과 2.3절, (2) `ics_sim` 의 `state.stamp_compact()`, (3) 야간 기준으로 갈 경우 야간 경계 정의와 사이트별 적용을 함께 갱신한다. 그때까지는 UTC 기준이 정본이다 |
| **OI-4** | `MIDOSCB` / `MIDOSCT` 분배 | 중앙 168행의 half별 분배가 84/84인지 미확인. 현행 converter는 이 블록을 전부 버린다 | timing script 확인 + bias frame 통계. 확정되면 Y overscan으로 활용할지 별도 검토 |
| **OI-5** | Binning 지원 | v1.0은 1×1 전용. binning 시 `NAXIS`가 바뀌어 converter가 즉시 실패한다 | binned 관측 계획이 서면 geometry 규격 확장 |
| ~~OI-6~~ | Sentinel 규약 통일 | **해결 (2026-08-11, 변경점 C-9).** 중계 본문과 FITS 헤더 값을 분리했다 — `header_dict()`(메시지 계층, `'0'` 유지) / `fits_header_dict()`(FITS, 정수 `-1` · 실수 `-999.0` · 문자열 `'NC'`). `DATE-OBS`는 값이 없으면 키를 넣지 않아 불완전한 노출이 드러난다 | 완료. 검증 `tests/test_raw_pair.py::test_fits_sentinels_follow_the_spec_not_the_message_layer` |
| **OI-7** | `CHECKSUM` / `DATASUM` | 현재 무결성은 MEF 산출물의 SHA256 사이드카로만 관리된다. raw 단계 무결성 검증 수단이 없다 | FITS 표준 checksum 도입 여부 결정 |
| ~~OI-8~~ | NT 헤더 완전성 | **해결 (2026-08-10, ICD v4.1).** ICD v4.0의 "NT 메타데이터는 최소한일 수 있다" 기술이 v4.1에서 이 규격과 같은 완전성 요구로 개정됐다 (2.1절) | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` §4 |

## 10. 관련 문서

| 문서 | 위치 |
| --- | --- |
| L0 MEF ICD | `../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` (docx 동본) |
| L0 MEF keyword 정의 | `../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md` |
| Converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` |
| Converter 작업 정리 | `../mef_converter/KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` |
| 신규 ICS 개발 노트 | `../ics_sim/DevNote.md` |
| Archon 실험실 취득 | `../cam_char/archon/ARCHON_LABTEST_V2.md` |
| 기술 결정 기록 | `../project_management/governance/DECISION_LOG.md` |
| Calibration 추적 | `../project_management/science/CALIBRATION_TRACKER.md` |
| Release 점검 | `../project_management/release/RELEASE_CHECKLIST.md` |

## 11. Revision History

| Version | Date | Change |
| --- | --- | --- |
| v1.0 | 2026-08-06 | Archon raw FITS pair(MK/NT) 규격 초판. 파일 구조·픽셀 배치·헤더 keyword 정의, converter 영향 분석, OBSAgent 파일명/`Wrote` 규약 충돌 제기 |
| v1.0 | 2026-08-06 | MEF keyword 정의서 v1.0 및 L1 `CARRY_KEYS` 전량 대조(6.5·6.6절) 후 누락 보강: `AMPPCD`, `DETSIZE`/`CCDCOLS`/`CCDROWS`/`COLGAP`/`ROWGAP`, `MODULE`/`CHANNEL` 배선 맵(5.5.1), `READDIR`(`RDDIRT`/`RDDIRB`), `CCDTEMP` 필수 격상. raw 제외 keyword 경계 명시(5.12) |
| v1.1 | 2026-08-07 | **OI-1 · OI-2 해결.** 파일명은 ICD v4.0 형식 유지 + `<NNNNNN>` 6자리 zero-padding 필수화(2.3절, D-009). 저장 단위(컨트롤러 2파일)와 통보 단위(CCD 4회 `Wrote`)를 분리하는 ICS 규약 추가(2.5절, D-010). `LASTFILE`이 실재 경로가 아니게 되는 부작용 명시. C-7 불필요 처리, C-16 추가 |
| v1.1 | 2026-08-08 | 정정(geometry 아님, `RAWVER` 유지): 2.5절 타이밍 조건을 `EXPSTATUS=READOUT`(및 그 뒤 `PCTREAD=`) 리셋 기준으로 수정하고(`commands.c` 812~816행 근거) `Wrote` 발신 순서 규칙 + READOUT~첫 PCTREAD 함정 창(~2.7초) 경고 추가. 2.3절 zero-padding 위반 결과 (3)을 `Wrote` 논리 이름 기준으로 정정. 5.5절 `CTRLNAME`/`CTRLSN`/`CTRLFW`의 CALIBRATION_TRACKER 추적 서술을 현재형에서 추가 예정으로 완화 |
| v1.2 | 2026-08-10 | **파일명 prefix를 사이트 코드로 개정 (D-011, D-009 대체).** `<SITE>` ∈ {`KMTC`=CTIO, `KMTS`=SAAO, `KMTA`=SSO, `KMTT`=테스트베드} — TC 텔레메트리 `TELID` 규약과 동일. `RAWVER`는 `CEU-RAW-v1.0` 유지(픽셀 배치 불변). converter v2.2.0: 정규식 개정 + 출력 prefix를 파일명에서 유도 + `OBSERVAT` 교차 검증(불일치=오류, 6.1절). `Wrote` 논리 이름(D-010)은 불변. C-7 완료 처리, OI-1 재개정, OI-8 해결(ICD v4.1). 연동 ICD를 v4.1(md+docx)로 갱신 |
| v1.2 | 2026-08-11 | 제자리 개정(요구사항 변경 아님, `RAWVER`·문서 버전 유지): **5.0절에 식별자 keyword 의 카드 형 규칙 추가** — `EXPID` 등을 실수 카드로 쓰면 2.3절이 필수로 정한 6자리 zero-padding 이 파괴된다(`000010`→`00001`). 구현에서 실제로 발생했고 시험값이 `000001` 이라 우연히 통과했다. 같은 절에 **결측 시 카드 자체를 넣지 않는다**(C-6 실패 경로와 연결)를 명시. **2.5절에 fail-safe 발동 시의 `WARNING` 발신 규약**(파일당 1회, 발신자는 `CHIP1` 의 `*.CB` — 레거시 대응 사례 없어 정한 것). **8장 체크리스트에 `EXPID` 카드 형·`FILENAME` 일치 항목 추가**와 자동 검증 범위 안내. **2.3.1절 신설** — 파일명 fail-safe 가 발동했을 때 `FILENAME`은 실제 파일명을 따라가고 `EXPID`/`CTRLTAG`/`CHIP1`/`CHIP2`가 개명 후 유일한 식별 근거이며 `PAIRFILE`은 명목 이름으로 열화될 수 있다는 것을 명시(5.1·5.2절 필수 항목의 함의). **OI-6·C-9·C-16 해결 처리**, C-8은 계약 개정(D-012) 반영. 구현은 `ics_sim` — DevNote 11.13 |
| v1.2 | 2026-08-12 | 제자리 개정: **5.7절 `DATE-OBS` 정의를 "셔터가 실제로 열린 시각"에서 "ICS가 `SHOPEN`을 지시한 UTC 시각"으로 변경** — 실기에는 셔터 개방 완료를 알려 주는 경로가 없어 전자는 알 수 없는 값이다(운영자 확정). 근거 블록을 같은 절에 추가. **2.5절 fail-safe `WARNING` 발신자를 `CHIP1`의 `*.CB`에서 `ICS`로 변경** — 파일을 쓴 당사자가 보고하는 것이 맞고, OBSAgent `case WARNING:`이 발신자를 보지 않음을 소스로 확인했다(`commands.c:1045`). **2.3절 `<YYYYMMDD>`를 UTC 날짜로 정정하고 OI-10으로 등재** — 종전 "관측 야간 기준 날짜"는 레거시·구현 어느 쪽과도 맞지 않았다. 야간 기준 여부는 이충욱과 협의해 확정한다 |
| v1.2 | 2026-08-12 | **레거시 raw 헤더 실측본을 근거로 식별 keyword 재정의** (`__reference/Legacy raw fits header samples/` 신설 — 2017·2021 raw 2건, MEF 35건. raw 헤더는 4년간 사실상 불변이었다). **`EXPID`·`EXPNUM` 삭제** — 레거시가 `FILENAME` 하나로 날짜+연번을 담고 있었고 `UNIQNAME`을 그 옆에 두었다. 둘을 함께 두면 서로 어긋날 수 있는 중복이다(운영자 확정). **`UNIQNAME`을 정본 식별자로 승격**(필수, 불변, `<SITE>.<8자리>.<6자리>.<MK\|NT>`)하고 `FILENAME`은 **실제로 쓴 이름**으로 정의. 둘 다 **확장자를 빼고** 기록한다(레거시 관례). **`NAMECLSH` 신설**(조건부). **2.3.1절에 「왜 `FILENAME`·`UNIQNAME` 인가」 신설** — `EXPID`·`EXPNUM` 을 검토했다가 레거시 keyword 를 이어받기로 한 경위와 근거 셋(중복 제거·레거시 연속성·MEF 목적지)을 실측 인용과 함께 남겼다. 5.2절에도 두 keyword 가 없는 이유를 안내한다. **2.3.1절 전면 재작성** — 이름이 겹치면 개명 대신 `clash/` 격리 + 시각 접미 + 카드의 세 겹. 레거시의 `<yymmdd>.<nnn>` 형식은 사이트 코드·컨트롤러 태그를 잃어 채택하지 않았다. 5.0·5.2·5.11·C-4·8장 정합 갱신. 구현은 `ics_sim` — DevNote 11.13 |

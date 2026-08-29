# archon_kmtnet_labtest — 실험실 취득 스크립트

**이 폴더의 실험실 취득 스크립트에 관한 모든 것**을 담는다 — 돌리기 전에 손볼
자리, 첫 실행 점검, 경고의 뜻, raw spec 적용으로 바뀐 것, 검토·감사에서 고친
것, 판 이력.

| 다른 곳 | 무엇이 |
|---|---|
| [README.md](../README.md) | 폴더 개요와 `ics_archon` 본편 계획 (여기 내용의 요약 포인터만) |
| [`../ics_sim/DevNote.md`](../../ics_sim/DevNote.md) 11.19~11.22 | **왜 그렇게 정했나** — 경위·판단·시사점 |
| [SMC_CLAUDE.md](../SMC_CLAUDE.md) | 인수인계 — 상태·브랜치·절대 깨뜨리면 안 되는 것 |
| [`../raw_fits_spec/`](../../raw_fits_spec/README.md) | 산출 규격(raw FITS pair). 헤더 5장의 바이트 정본은 견본 pair |

## 스크립트 두 벌

| 파일 | 정체 |
|---|---|
| [`archon_kmtnet_labtest_v1.3.bigbuf.py`](archon_kmtnet_labtest_v1.3.bigbuf.py) | ✅ **현행** (`SCRIPT_VERSION='1.3.0'`). **science 유닛용** — BIGBUF=1, 768 MB 버퍼 2개 구성. v1.0.bigbuf 에 raw spec 을 적용한 판 |
| [`archon_kmtnet_labtest_v1.3.smallbuf.py`](archon_kmtnet_labtest_v1.3.smallbuf.py) | **구버전 science 유닛을 구동하던 코드** — smallbuf로 구성되는 **guide 유닛 제어용 코드 작성 시 참고**한다(운영자 2026-08-26). bigbuf 와 **버퍼 주소 지정 다섯 자리만** 다르다 |
| [`archon_kmtnet_labtest_v1.3.bigbuf.KMTC-102.py`](archon_kmtnet_labtest_v1.3.bigbuf.KMTC-102.py) · [`…KMTC-113.py`](archon_kmtnet_labtest_v1.3.bigbuf.KMTC-113.py) · [`…KMTS-101.py`](archon_kmtnet_labtest_v1.3.bigbuf.KMTS-101.py) | **유닛별 사본** — 기준 판에서 `<---- Set this` 항목만 바꾼 것. **기준 판 자체가 `KMTC-101`(MK) 설정**이라 그 사본은 따로 두지 않는다 |
| [`tests/verify_labtest_v13.py`](../tests/verify_labtest_v13.py) | **실기 없이 돌리는 검증** (32항목) — 가짜 Archon + astropy 실파일 |
| [`tests/test_labtest_spec_copy.py`](../tests/test_labtest_spec_copy.py) | **규격 사본 표류 감시** (4항목, 2026-08-26 신설) — 내장 `RAWCARDS`·`CHMAP`·`SITE_INFO`·번호 공간이 `ics_sim` 과 갈라지면 실패한다 |
| `__ref_archon_control/archon_kmtnet_labtest_v1.0.{bigbuf,smallbuf}.py` | **v1.0 원본** (읽기 전용). 되돌려 비교할 때 쓴다 |

## 이 판이 무엇인가

`v1.0.bigbuf` 는 **실제로 돌려서 쓰던 검증된 코드**다. v1.1 은 거기에 raw spec
적용 개정을 얹은 것이므로, 판단해야 할 것은 하나다:

> **내 개정이 그 검증된 취득 경로를 건드렸나?**

컨트롤러와의 왕복 기준으로 v1.1 이 **추가한 프로토콜 명령은 `STATUS` 하나뿐**
이다(나머지 변경은 파일명·헤더·패딩 등 호스트 쪽 일이라 컨트롤러와 무관).
그래서 **`TELEMETRY_ENABLE = False` 로 두면 왕복이 v1.0 과 완전히 같아진다** —
문제가 보일 때 원인을 가르는 가장 빠른 수단이다.

## 검증 상태 (v1.3.0, 2026-08-26)

| 항목 | 상태 |
|---|---|
| 헤더 144카드가 견본 v1.0 pair 와 **바이트 단위 일치** | ✅ 확인 (불일치 0) |
| 헤더 2880B × 4블록 정렬 · 데이터부 패딩 | ✅ 확인 |
| 문법·컴파일 (`SyntaxWarning` 포함) | ✅ 확인 |
| STATUS 상한 · 실패 후 **연결 재수립** · 다음 두 명령 생존 | ✅ 가짜 컨트롤러로 실측 |
| 비ASCII 손편집 값을 기동에서 거부 · 헤더 바이트 정렬 유지 | ✅ 실측 |
| 기하·표본 불일치를 fetch 전에 거부 | ✅ 실측 |
| 없는 ACF 를 접속·전원 전에 거부 | ✅ 실측 |
| **저장 자리**(없음·읽기전용·용량 부족·안 펼친 `~`)를 접속·전원 전에 거부 | ✅ 실측 |
| **실기 왕복** (POWERON → LOADPARAMS → FRAME 폴링 → FETCH) | ❌ **미검증** |
| 실제 픽셀이 담긴 FITS 를 converter 에 투입 | ❌ 미검증 |

즉 **하드웨어로는 한 번도 돌리지 않았다.** 첫 실행은 그 전제로 볼 것.

실기 없이 돌리는 검증은 언제든 다시 할 수 있다:

```bash
python ics_archon/tests/verify_labtest_v13.py
```

31개 항목 전부 통과해야 한다(실패 0).  읽기전용 자리 검사 1건은 POSIX 에서만
돌고 윈도우에서는 `SKIP` 으로 넘어간다. 스크립트를 손봤으면 돌려 보고 나가라.

## ✅ 종결 — 프레임이 한 장도 안 나오던 증상 (2026-08-27)

**원인: `Sync In` 이 물려 있었고, 상대 컨트롤러가 클록을 잡고 있었다** (운영자).
101(STA-0284)의 **전원부 고장**으로 클록이 나오지 않아, 102(STA-0285)의 타이밍
코어가 외부 동기를 영원히 기다렸다. 101 쪽을 정리한 뒤 102 는 정상 취득했다.

**증상.** `POWERON` 까지 정상인데 프레임 카운터가 오르지 않는다:

```
>> CCD Flush / Exposure / Readout progress: 
   [   5s] RBUF=0  FRAME=0/0/0  COMPLETE=0/0/0  POWER=4  POWERGOOD=1
>> Failed to readout complete!
```

**⚠️ 이 증상을 만나면 `Sync In` 부터 본다.** 관측된 것이 전부 이 원인과 맞는다:

| 관측 | 이 원인이면 |
|---|---|
| `POWER=4` · `POWERGOOD=1` | 자기 전원은 정상 — **`POWERGOOD` 은 외부 클록 의존을 보지 않는다** |
| `FRAME=0/0/0` 영구 | 코어가 동기를 기다리느라 프레임을 만들지 않는다 |
| 명령 응답은 정상 | 통신 경로는 타이밍과 독립이다 |
| 전원 리셋 무효 | 리셋해도 상대가 클록을 주지 않는다 |
| ACF·파라미터 정상 | 설정 문제가 아니다 |

**`POWERGOOD=1` 은 하드웨어 정상을 보장하지 않는다** — 컨트롤러 자기 전원만
보고한다. 전원이 정상 보고인데 프레임이 0장이면 **외부 클록(Sync In)과 상대
유닛**을 의심하라.

**이번에 아니라고 가려낸 것** — 같은 증상이 또 나오면 여기부터 다시 뒤지지 말 것:

| 짚었던 것 | 결과 |
|---|---|
| ACF 파라미터 슬롯 불일치 | `PARAMETER1=Exposures` · `PARAMETER2=IntMS` 로 정확 |
| 셔터 트리거 (`TRIGOUTFORCE`) | `ShutOpen=True` 로도 전에 성공 |
| 전원 이상 | `POWER=4` · `POWERGOOD=1` |
| 컨트롤러 상태 꼬임 | 전원 리셋으로 안 바뀜 |
| MK↔NT ACF 차이 | 구조 동등 — 다른 값 33개는 `IP` 와 amp 배정뿐 (`../acf/README.md`) |

**남은 계측.** 시한 초과 시에는 `FRAME_DUMP_ENABLE` 과 **무관하게** 진단 한 장이
항상 남는다. 재발하면 **가동 경과 시간** · 그 스냅샷 줄 · 한 유닛인지 둘 다인지 ·
`Sync In` 결선 상태를 함께 남길 것.

## 유닛별 사본

기준 판(`…v1.3.bigbuf.py`)이 **`KMTC-101`(MK) 설정 그대로**이고, 나머지 유닛은
`<---- Set this` 항목만 바꾼 사본을 둔다. 벤치에서는 각 사본을 `~/AIC/scr/` 에
놓고 쓴다.

| 사본 | `CTRLTAG` | `CTRL_ID` | `CTRL_SN` | IP | ACF |
|---|---|---|---|---|---|
| (기준 판) | MK | `KMTC-SCI-101` | `STA-0284` | `.101` | `KMTC_SCI_101_…MK` |
| `KMTC-102` | NT | `KMTC-SCI-102` | `STA-0285` | `.102` | `KMTC_SCI_102_…NT` |
| `KMTC-113` | MK | `KMTC-SCI-113` | `STA-0200` | `.113` | `KMTK_SCI_113_…MK` |
| `KMTS-101` | MK | `KMTS-SCI-101` | `STA-0286` | `.101` | `KMTS_SCI_101_…MK` |

유닛 ↔ 시리얼 정본은 `../../raw_fits_spec/__reference/Archon_Unit_Info.txt` 다
(113 은 시험 유닛이라 그 표에 없다).

⚠️ **113 의 사이트 코드가 섞여 있다** — 스크립트는 `KMTC-SCI-113`, ACF 는
`KMTK_SCI_113_…` 다. 113 이 **CTIO 설치 후보**가 되면서 생긴 혼용이고, **설치
위치가 정해지면 일괄 통일할 예정**이다 (운영자 2026-08-27). **오류로 보고 고치지
말 것.**

⚠️ `SITE_CODE` 는 어느 사본이든 `KMTK` 다 — **자료를 딴 곳**(KASI 실험실)이지
유닛 정체가 아니다. 두 축을 섞지 말 것.

**사본이 갈라지지 않게 시험이 지킨다** (`../tests/test_labtest_spec_copy.py`):
손편집 항목 밖의 차이 · 정체와 시리얼의 1:1 · **가리키는 ACF 의 실재**.

## 돌리기 전에 손볼 자리

행 번호는 **`v1.3.0`(2026-08-26) 실측**이다. ⚠️ 판이 오르면 밀리므로 **어긋나면 아래 `grep` 으로 찾는다** — 종전 표는 28행쯤 어긋난 채 남아 있었다:

```bash
grep -n "Set this\|^TELEMETRY_\|^SITE_CODE\|^TestRunNum\|^GetDataset" archon_kmtnet_labtest_v1.3.bigbuf.py
```

| 행 | 항목 | 지금 값 | 비고 |
|---:|---|---|---|
| 69 | `DATA_PREFIX` | `'AC13A'` | 로그·SMS 표시용 라벨. **파일명에는 안 들어간다** |
| 71 | `UNIT_ID` | `7` | |
| 72 | `UNIT_IP` | `'13'` | 주소는 `10.0.0.<UNIT_IP>` |
| **89** | `DATA_STORAGE` | `'~/AIC/data'` | **v1.1.3 에서 한 곳으로 합쳤다** (구판은 `_C`/`_A`/`_B` 세 갈래). `~` 는 `GetDataset` 이 펼친다 — 다른 디스크로 보내려면 이 값 대신 **`~/AIC/data` 를 심볼릭 링크로** 둔다 (INSTALL.md) |
| **98** | `SITE_CODE` | `'KMTK'` | KASI(실험실). 관측소 반입 시 `KMTC`/`KMTS`/`KMTA` — **`OBSERVAT`/`ORIGIN`/`TELESCOP`/`FPAID` 가 여기서 유도된다** (5.3.1절). ⚠️ D-017 로 구 `KMTT` 폐지 |
| **100** | `UNIT_CTRLTAG` | `'MK'` | **신설.** 이 유닛이 담당하는 detector pair. `MK`/`NT` 가 아니면 기동 시 거부 |
| **102** | `UNIT_CTRL_ID` | `'KMTK-SCI-101'` | **신설.** FITS `CTRL<n>ID` |
| **103** | `UNIT_CTRL_SN` | `'STA-0287'` | **신설.** 백플레인 시리얼 |
| 104 | `OBSERVER_NAME` | `'HELab'` | FITS `OBSERVER` |
| 112 | `TELEMETRY_ENABLE` | `True` | 문제가 보이면 `False` (아래 "이상할 때") |
| 113 | `TELEMETRY_TIMEOUT` | `3.0` | STATUS 응답 대기 상한 [s] |
| **115** | `FRAME_WAIT_MAX` | `20` | 노출시간 위에 더 기다릴 상한 [s]. 넘으면 예외 → `finally` 의 `POWEROFF`. **무인 실행에서 전원을 켠 채 매달리는 것을 막는다** |
| **123** | `FRAME_DUMP_ENABLE` | `True` | 프레임 대기 중 상태를 주기적으로 찍나. **취득이 정상으로 돌기 시작하면 `False`** — 진행 막대만 남는다 |
| **125** | `FRAME_DUMP_EVERY` | `8` | 몇 회전마다 (8 ≈ 5초) |
| **126** | `FRAME_DUMP_STATUS` | `True` | `POWER`/`POWERGOOD`/`TIMER` 도 함께. 끄면 `FRAME` 질의 하나만 (왕복 3 → 1) |
| **130~131** | `SCRIPT_VERSION`/`SCRIPT_BUILD` | `'1.3.0'` / `'2026-08-26T18:05Z'` | FITS `ICSBUILD`. **소스를 고치면 같이 올린다.** 카드에 들어갈 자리가 26자라 `v<버전>:<빌드>` 가 그 길이를 넘으면 잘리고 경고가 난다 — 지금은 24자이므로 **초 단위를 넣으면(27자) 잘린다** |
| 235~236 | `TEST_FRAMENUM_xTalk` / `TEST_EXPTIMES_xTalk` | `3` / 7개 | 연막시험 때 줄이는 자리 (아래 "첫 실행은 작게") |
| 1891~1912 | 실행부 | — | 구 캠페인 3블록은 `'''` 로 묶여 있고 **1912 한 줄이 활성**(`UNIT_ACF_SCI_NORMAL`, DatasetId 2844)(`3211`/`3511`/`3811`, 2025-04-13 자). 아래 ⚠️ 참조 |

> 🔴 **활성 블록의 유닛 번호를 확인하라.** `DatasetId` 는
> `[UnitID(1)][TestSetup(2)][DatasetType(1)]` 이고, 활성 블록의 `3211`/`3511`/
> `3811` 은 첫 자리 3 = **유닛 23A** 다. 그런데 위 설정은 `UNIT_ID = 7`
> (= 13A, AC13A) 다. 주석 처리된 두 블록은 `7211`/`7511`/`7811` 로 유닛 7 과
> 맞아떨어진다 — **활성 블록은 다른 유닛의 것이다.**
>
> 이게 중요한 이유: **`UNIT_ID` 는 36행에 정의만 있고 코드 어디서도 쓰이지
> 않는 죽은 변수**이고, `DATA_PREFIX` 도 v1.1 부터 파일명에서 빠졌으며 SMS 는
> 함수 본문이 주석 처리돼 죽어 있다. 그래서 **유닛이 기록되는 자리는 DS 번호
> 첫 자리와 `UNIT_CTRL_ID`/`UNIT_CTRL_SN` 뿐**이다. 셋을 함께 맞춰야 한다.

> ⚠️ **손편집 문자열은 ASCII 만 된다.** `SITE_CODE`·`UNIT_CTRLTAG`·`UNIT_CTRL_ID`·
> `UNIT_CTRL_SN`·`OBSERVER_NAME`·`SCRIPT_*`·`DATA_PREFIX` 에 한글이나 기호가
> 한 자라도 있으면 **기동에서 멈춘다.** FITS 헤더는 규격상 ASCII 전용이고,
> 한글 한 자(utf-8 3바이트)가 2880B 정렬을 깨서 **파일 전체를 못 읽게** 만든다.

그 밖에 확인할 것:

- `acf/KMTNet_Sci_{fast,comp,slow}_med_U<IP>.acf` (118~120행) — **v1.1.1 부터는
  스크립트가 데이터셋 시작에 직접 확인하고, 없으면 접속·전원 전에 멈춘다.**
  경로가 상대경로이므로 **작업 디렉터리**가 그 상위 폴더여야 한다
- `DATA_STORAGE` 자리가 **이미 있는지** (54행). **v1.1.3 부터 스크립트가 데이터셋 시작에 직접 확인하고, 없거나 못 쓰거나 좁으면 접속·전원 전에 멈춘다** — 그리고 **만들어 주지 않는다**(마운트가 안 붙은 것을 폴더 생성으로 덮으면 자료가 엉뚱한 곳에 쌓인다). 자리는 운영자가 먼저 만든다 — `mkdir -p ~/AIC/data`, 다른 디스크로 보낼 거면 심볼릭 링크 (INSTALL.md "2. 자리 만들기"). — 그리고 **여유
  용량**(아래 "첫 실행은 작게" 의 표)
- `TEMP_MODS` (598행) — 지금은 `BACKPLANE_TEMP` + AD 모듈 4장(MOD5~8).
  카드 폭(51자)을 넘으면 잘리고 경고가 난다. **모듈 나열 순서의 정본 명세는
  규격 수록 예정**이라 확정되면 교체한다
- ~~**`twilio` 가 깔려 있는지.**~~ **v1.1.2 에서 고쳤다.** SMS 함수 본문은 전부
  `'''` 로 막혀 `return` 만 하는데 `from twilio.rest import Client` 는 모듈
  최상단에서 **실제로 import 돼서**, 없는 기계로 옮기면 아무것도 못 하고
  `ModuleNotFoundError` 로 죽었다 (v1.0 부터 그랬다). 이제 `try/except
  ImportError` 로 감싸 없어도 넘어간다 — SMS 를 되살릴 때는 twilio 를 설치한다
- **`DatasetId` 끝자리가 1/2/3/5 가 아니면 직전 데이터셋 설정을 그대로
  재사용한다.** `SetDatasetConfig` 의 `else` 분기가 `TEST_DATASET` 만 바꾸고
  `TEST_FRAMENUM`/`TEST_EXPTIMES` 는 건드리지 않는다 (0=Check, 1=xTalk, 2=Dark,
  3=iFlat, 5=GxT). v1.0 부터 그대로이므로 새 문제는 아니지만, 끝자리 0 으로
  돌릴 생각이면 알고 있어야 한다

## 첫 실행은 작게 시작한다

활성 실행 블록을 그대로 돌리면 이만큼이다 (xTalk 타입 = `DatasetId % 10 == 1`,
`TEST_EXPTIMES_xTalk` 7개 × `TEST_FRAMENUM_xTalk` 3, REF·DARK 없음):

| | |
|---|---|
| 데이터셋당 프레임 | **21** |
| 파일 하나 | **344.25 MiB** (헤더 11,520 + 데이터 360,960,000 + 패딩 1,920 B) |
| 데이터셋 하나 | **7.06 GiB** / 노출 시간 합계 159 초 (+ 독출 × 21) |
| 활성 블록 3개 | **63 프레임 / 21.18 GiB** |
| — 전부 `DATA_STORAGE` 한 곳 | **21.18 GiB** — v1.1.3 에서 갈래를 합쳤으므로 `~/AIC/data` 하나가 이만큼을 감당해야 한다 |

**실기로 한 번도 돌리지 않은 판이므로 이걸 첫 실행으로 삼지 않는다.** 뭔가
틀렸으면 21 GiB 를 쓴 뒤에 알게 된다. 1프레임으로 먼저 확인한다:

```python
TEST_FRAMENUM_xTalk = 1        # 184행 (원래 3)
TEST_EXPTIMES_xTalk = (0,)     # 185행 (원래 7개)
```

→ 1프레임 / 344 MiB / 노출 0 초. 활성 블록에서 `GetDataset` 한 줄만 남기고
돌린 뒤, 아래 "첫 프레임이 나오면" 확인을 통과하면 두 값을 원복한다.

> **연막시험에서는 `TELEMETRY_ENABLE` 을 `True` 로 두는 게 낫다.** v1.1 이 추가한
> 유일한 왕복이므로 문제가 있으면 이때 드러나야 한다. 본판에서 이상하면 그때
> 끈다.

## 첫 실행에서 볼 것

**기동 즉시** — 컨트롤러에 붙기 **전에** 정체성을 검사하고 배너를 찍는다.
틀리면 여기서 멈춘다(오타가 노출 도중에 터지지 않게 하려는 것):

```
Identity: SITE=KMTK  DETID=MK  CTRL1=KMTK-SCI-101 (STA-0287)
          OBSERVAT=KASI  ORIGIN=KASI  TELESCOP=KMTNet 1.6m #0
```

**노출마다** — 파일명 형식이 바뀌었다:

```
v1.0:  AC13A.<YYYYMMDD>.<NNNNNN>.fits
v1.1:  KMTK.<YYYYMMDD>.<NNNNNN>.MK.fits      <SITE>.<날짜>.<번호>.<MK|NT>
```

**경고가 뜨면** 뜻은 이렇다:

| 메시지 | 뜻 · 대처 |
|---|---|
| `WARNING: STATUS query failed (...) -- telemetry cards go NC for the rest of this run` | 텔레메트리만 포기하고 **취득은 계속된다.** 설계된 동작이다 — `Cn_*` 카드가 `'NC'` 로 실린다 |
| `WARNING: resyncing the Archon link (STATUS reply abandoned)` | STATUS 가 시한 안에 안 와서 **연결을 새로 열었다.** 취득은 계속된다 |
| `WARNING: FITS card C1_TEMP value too long (N > M) -- truncated` | `TEMP_MODS` 를 줄인다. 카드는 유효한 상태로 유지된다 |
| `WARNING: FITS card ... has non-ASCII characters ... replaced with ?` | 헤더에 들어온 비ASCII 를 `?` 로 바꿨다. 값은 잃지만 파일은 온전하다 |
| `WARNING: filename clash -- number bumped NNNNNN -> MMMMMM (D-016)` | 같은 이름이 있어 번호를 올려 저장했다. 헤더에 **`FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값 ≠ `EXPID`** 로 남는다 (v1.6/D-019 — 구 `ORIGNAME`). **프레임마다 뜬다면 아래 '재실행' 항목을 볼 것** |
| `WARNING: <dir> 에 오늘(UT ...) 자 파일이 이미 N 개 있다 -- ...` | 데이터셋 시작에 한 번. **같은 UT 날짜의 재실행은 멱등하지 않다** — 아래 참조 |
| `WARNING: POWEROFF 를 못 보냈다 (...)` | 예외로 빠져나가는 중에 전원 끄기까지 실패했다. **유닛 전원 상태를 직접 확인하라** |
| `ERROR: data storage not found -- '...'` (데이터셋 시작에서 멈춤) | 저장 자리가 없다. **스크립트는 만들지 않는다** — `~` 가 안 펼쳐졌거나(cwd 아래 `~` 폴더), 마운트가 안 붙었거나, 경로 오타다. `mkdir -p` 로 먼저 만들어라 |
| `ERROR: data storage not writable -- '...'` | 읽기전용으로 붙었거나 권한이 없다. `mount \| grep` 으로 확인 |
| `ERROR: data storage too small -- '...'` | 이 데이터셋이 쓸 바이트보다 여유가 적다. 비우거나 다른 디스크로 |
| `WARNING: '<dir>' 는 마운트 지점이 아니다 -- OS 디스크에 쌓인다` | 알리기만 하고 **계속 간다.** `~/AIC/data` 를 OS 디스크에 두는 것도 정상 배치다 (INSTALL.md) — 외장을 쓸 작정이었으면 마운트를 확인하라 |
| `ERROR: ACF not found -- '...'` (데이터셋 시작에서 멈춤) | ACF 파일이 없다. 함께 찍히는 `resolved to` 절대경로와 `cwd` 를 보라 — **작업 디렉터리가 다른 것**이 가장 흔하다 |
| `ERROR: <이름> = ... 에 비ASCII 문자가 있다` (기동에서 멈춤) | 손편집 값에 한글/기호가 있다. ASCII 로 바꿔라 — 그대로면 FITS 가 통째로 안 읽힌다 |
| `RuntimeError: frame data N B (...) != header NAXIS ...` | 실제 프레임 크기가 헤더 선언과 다르다. ACF 기하나 `samplemode` 를 확인하라. **fetch 전에 멈추므로 첫 프레임에서 드러난다** |

### 재실행은 덮어쓰기가 아니다

v1.0 은 같은 파일명을 `'wb'` 로 열어 **덮어썼다**. v1.1 은 D-016 선검사가
점유된 번호를 피해 올라간다. 그래서 **같은 UT 날짜에** 파일이 남아 있는 DS
폴더를 `StartNum=0` 으로 처음부터 다시 돌리면 재실행분이 다음 DS 의 번호
영역으로 넘어가고, `filenum - DatasetId*100 == nframe` 이라는 v1.0 의 불변식이
깨진다 — '07번 프레임' 식으로 번호를 믿는 분석이 어긋난다. 실측(iFlat
116프레임): 1회차 321100~321215 → 2회차 **321216~321331** → 3회차
**321332~321447**.

> **날짜가 다르면 충돌이 아니다.** 선검사 경로에 날짜가 들어 있으므로(D-011)
> **다음 날 같은 DS 를 다시 찍는 것은 아무 영향이 없다** — 그게 실험실의 평상
> 재실행이다. 걸리는 것은 **같은 UT 날짜 안에서의 재실행**뿐이다.

같은 날 다시 돌려야 하면 셋 중 하나를 하면 된다:

- 이전 폴더를 비우거나 옮긴다 (권장)
- 끊긴 자리부터 `StartNum` 으로 이어받는다 — 이 경로는 충돌이 안 난다
- 그대로 두고 `FILENAME` 의 `DETID` 필드를 뗀 값 ≠ `EXPID` 로 사후에 가른다 (D-019)

선검사 비용은 문제되지 않는다 — 프레임당 `os.path.exists` 2회(앞에 k개가
점유돼 있으면 최대 2(k+1)회)이고, 116프레임을 3회차까지 밀어 올려도 누적
0.9초다. 프레임 하나가 344 MiB 를 내려받는 것에 비하면 무시할 수준이다.

**첫 프레임이 나오면** 확인:

```bash
python -c "from astropy.io import fits; h=fits.open('KMTK.20260822.321100.MK.fits'); print(h[0].data.shape, repr(h[0].header['DETID']), repr(h[0].header['C1_TEMP']), repr(h[0].header['DATE-OBS']))"
```

기대: `(9400, 19200)` · `'MK'` · 온도 나열(또는 `'NC'`) · UTC 밀리초.

## 이상할 때 — 원인을 가르는 순서

1. **`TELEMETRY_ENABLE = False`** (76행). 이러면 컨트롤러와의 왕복이 v1.0 과
   동일해진다. 그래도 문제가 남으면 **원인은 내 개정 밖**이다(헤더·파일명은
   호스트 쪽이라 취득에 관여하지 않는다).
2. 그래도 재현되면 `__ref_archon_control/archon_kmtnet_labtest_v1.0.bigbuf.py`
   로 되돌려 같은 조건을 돌려 본다. v1.0 에서도 나면 v1.1 과 무관하다.
3. 헤더만 이상하면 취득은 이미 끝난 뒤의 일이다 — 프레임은 살아 있다.

## v1.1 에서 바뀐 것 (raw spec 적용, 2026-08-22)

정본: [`../raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.8.md`](../../raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.8.md)

1. **파일명** — `AC13A.<날짜>.<번호>.fits` → **`<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits`**
   (D-011). 실험실은 `SITE_CODE='KMTK'`(KASI), 날짜는 UT(KMTK 보정 0,
   D-014), 번호는 기존 DS 체계(6자리 `[Unit][Setup][Type][SN]`) 유지 —
   converter 정규식(`\d{6}`)에 그대로 걸린다.
2. **이름 충돌 = 번호 증가** (D-016) — 쓰기 전에 후보 번호의 MK·NT 두 경로를
   선검사하고 점유 시 +1. 카운터(DS 체계) 최초 배정분은 **`EXPID`** 카드로
   남는다 — 충돌 신호 = `FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값 ≠ `EXPID`.
   ⚠️ v1.6(D-019)에서 구 `ORIGNAME` 을 대체했다. `EXPID` 는 컨트롤러 태그가
   없어 **pair 양쪽이 같은 값**이다.
3. **헤더 전면 교체** — 구 12카드 → **견본 초안 v1.0 pair 의 144 레코드**
   (값 131 + COMMENT 8 + END 1 + 공백 4 = 정확히 2880B×4블록). 카드 순서·comment·문자열
   패딩까지 견본과 **바이트 단위 동일** (검증: 견본 값을 넣으면 견본이 그대로
   재현된다 — 불일치 0). 실험실에서 모르는 값(TCS/AUX/듀어 HK)은 규격 5.0절
   sentinel (`'NC'`/`-1`/`'-999.99'`/`'9.99e-9'`).
4. **Archon STATUS 텔레메트리** — `Cn_TEMP`(science 10자리: Backplane +
   Mod1·2·3·4·5·8·9·10·11 — 규격 5.6.1절 자리 표),
   `Cn_VOLT`/`Cn_CURR`(전원 레일 7자리 P2V5 P5V P6V N6V P17V N17V P35V) — 매뉴얼
   p.47–49. **색인 `n` 은 `UNIT_CTRLTAG` 가 정한다**(MK→1 / NT→2, 5.9절) —
   `C1_*` 는 "내 컨트롤러"가 아니라 컨트롤러 1 고정이다. 실험실은 한 대만
   돌리므로 나머지 한 벌은 **자리 수만큼 채운** `'NC|NC|…'` 이고(규격
   5.6.1절 "자리는 비우지 않는다" — 자리 수 자체가 모듈 구성 판별에
   쓰이므로 `'NC'` 한 토큰으로 내지 않는다), 두 대분 합치기는 본편 몫이다.
   **구분자는 파이프(`|`)** 이고 결측 자리 sentinel 은 `NC` 다 (v1.6) —
   단일 HK 카드의 `'-999.99'` 와 다르다.
5. **`IMAGETYP` 유도** — 0초=`BIAS` / 트리거 없음=`DARK` / 트리거(LED) 노출=`FLAT`.
   `LEDFLASH` 는 트리거 노출이면 노출시간[ms] (실험실 광원이 트리거 라인으로
   노출 내내 켜지므로). `OBJECT`=`DS<번호>` 로 데이터셋 정체를 남긴다.
6. **`DATE-OBS`** — 노출 지시(LOADPARAMS) 시점의 **UTC, 밀리초까지**
   (구판은 Local 날짜/시각 2카드). `TIME-OBS` 폐지.
7. **데이터부 2880B 패딩** (규격 3장) — v1.0 은 마지막 블록이 잘려 있었다.
8. `CTRL1CFG` = 적용한 ACF 파일명, `RDMODE` = ACF 속도 토큰(FAST/COMP/SLOW),
   `ICSBUILD` = `v<버전>:<빌드일시>Z`, `DATASRC='ARCHON_SCIENCE'`.

> **⚠️ 기존 분석 스크립트는 그대로 못 쓴다.** 파일명이 `AC13A.*` 에서
> `KMTK.*.MK` 로 바뀌었고(glob 패턴 갱신 필요), 날짜부가 Local → **UTC** 라
> KST 00:00~09:00 취득분은 파일명에 **전날 날짜**가 박힌다(D-014 대로다).
> `SHUTOPEN`(정수 0/1)과 `TIME-OBS`(Local)는 폐지 — 대체는
> `IMAGETYP`/`OBSTYPE` + `LEDFLASH`[ms] + `DATE-OBS` 한 장이다.
> 반대로 `EXPTIME` 은 정밀해졌다: v1.0 의 `%20.2f` 는 Dark 데이터셋 노출시간
> **16종에서 반올림 손실**이 있었다(2395 ms → `2.40`). 이제 `2.395` 다.

> **규격 판 참조**: v1.1 은 raw spec **v1.3** 기준으로 작성했고, 같은 날 발행된
> **v1.4** 는 1~4장의 표현만 바뀌어 이 스크립트의 동작에 영향이 없다 — 2.5절
> 삭제(`Wrote` 통보는 취득 SW 소관이라 규격에서 빠졌다), 4.1 `RRRRLLLL` 확정
> (OI-15 종결), 4.2/4.4 표기 정합. **5장 이후(헤더 카드)는 아직 검토 전**이므로
> 견본 144카드 기준은 그대로다.

## v1.1 이 취득 경로에서 유일하게 손댄 곳

`STATUS` 질의 하나이고, **놓는 위치를 두 번 고쳤다.** 처음엔 프레임 fetch
직후·파일 쓰기 직전에 두었는데, `archoncmd` 에 타임아웃이 없어서 컨트롤러가
답하지 않으면 그 자리에서 무한히 돌고 **이미 다 읽어낸 노출을 잃었다**
(`try/except` 로는 안 잡힌다 — 무한 루프는 예외가 아니다). 지금은:

- **노출 개시 전**에 스냅샷을 뜬다 → 실패해도 잃을 프레임이 없다
- `archoncmd(cmd, timeout=)` 로 상한을 준다 — **기본값 `None` 이라 기존
  호출(`APPLYALL` 등 오래 걸리는 것)의 동작은 바뀌지 않는다.** STATUS 만 3초
- 한 번 실패하면 `TELEMETRY_ENABLE` 을 끈다 — 어긋난 뒤에도 노출마다 계속
  물어보는 것은 같은 위험을 되풀이하는 일이다
- **그리고 연결을 새로 연다.** 끄기만 해서는 *이미* 어긋난 것이 안 풀린다:
  `archoncmd` 는 응답을 검증한 뒤에야 `msgref` 를 올리므로, 시한 초과로
  빠져나가면 명령은 나갔는데 `msgref` 는 그대로다. 늦게 도착한 STATUS 응답의
  헤더가 그 `msgref` 와 맞아떨어져 **다음 명령이 남의 응답을 먹고, 그 다음
  명령이 `Invalid command packet header` 로 죽는다.** `msgref` 만 올리는
  것으로는 부족하다 — 응답이 부분만 도착했으면 소켓에 꼬리 바이트가 남고,
  늦은 응답이 몇 분 뒤 다른 데이터셋에서 튀어나올 수도 있다. 그래서 소켓을
  버리고 새로 연다(설정·전원은 컨트롤러가 들고 있어 잃는 상태가 없다)
- 노출 루프를 `try/finally` 로 감쌌다 — **무슨 예외가 나도 `POWEROFF` 는
  보낸다.** v1.0 은 감싸지 않아 예외 하나로 전원을 켠 채 traceback 으로
  끝났다

## v1.1 적대적 검토 반영 (2026-08-22, 같은 날)

v1.1 을 만든 뒤 스크립트를 원본과 대조 검토해 **6건을 고쳤다** (전부 v1.1 에서
새로 들어온 결함이다 — v1.0 의 `SetHeader` 는 순수 문자열 포맷이라 실패 경로가
없었다). 경위는 `../ics_sim/DevNote.md` **11.20**.

| 무엇이 문제였나 | 어떻게 고쳤나 |
|---|---|
| `fits_card` 가 폭 초과 문자열을 클램프하지 않아 80바이트에서 통째로 절단 — **닫는 인용부호·comment 가 사라져** astropy·converter 가 파싱 불가 (온도 13슬롯이면 실제로 그렇게 된다). `build_header` 의 `% 2880` 단언은 원리상 이걸 못 잡는다 | 들어갈 자리를 계산해 잘라내고 **경고**한다 |
| 텔레메트리 나열이 결측 항목을 **건너뛰어** "자리 = 항목"(5.6절)을 조용히 깼다 — MOD3 결측이면 MOD4 값이 MOD3 자리에 앉고, volt/curr 항목 수가 서로 달라질 수 있었다 | 자리마다 sentinel. 슬롯 목록을 `TEMP_MODS` 상수로 (BACKPLANE + AD 모듈 4장 — **모듈 순서 정본은 규격 수록 예정**이라 그때 교체) |
| 프레임 fetch 후·쓰기 전 미처리 예외 2종 — STATUS 의 비수치 토큰 하나, `UNIT_CTRLTAG` 오타(KeyError). **이미 읽어낸 노출이 통째로 버려졌다** | `status_number()` 가 sentinel + 경고로 흡수 · `_check_identity_setup()` 이 기동 시점 1회 검증 |
| `CTRL1*`/`C1_*` 에 자기 유닛 값을 넣어 5.9절 위반 — `C1_*` 는 "내 컨트롤러"가 아니라 **컨트롤러 1 고정**이다 | `UNIT_CTRLTAG` 가 색인 자리를 정한다 (NT 유닛이면 `CTRL2*`/`C2_*`) |
| `SITE_CODE` 를 주석 지시대로 관측소 코드로 바꾸면 `OBSERVAT` 가 옛 사이트로 남아 **규격의 유일한 하드 실패** | `SITE_INFO` 표에서 `OBSERVAT`/`ORIGIN`/`TELESCOP`/`FPAID` 유도 |
| `OBJECT` 가 `filenum // 100` 역산을 써서 iFlat(116 프레임)의 `nframe >= 100` 구간에서 `DS<번호+1>` | 죽은 `prefix` 인자를 `datasetid` 로 교체 — 호출측이 넘긴다 |

수정 후에도 **견본 바이트 재현(144카드, 불일치 0)** 은 그대로다.

## v1.1.1 — 투입 전 감사 회귀 4건 수정 (2026-08-23)

실기에 걸기 직전 **"v1.0 에서는 되던 것이 v1.1 에서 깨졌나"** 만 묻는 감사를
돌렸다(에이전트 21, blocker 0). **확정 회귀 4건이 전부 v1.1 이 넣은 자리에서**
나왔고, 넷 다 **취득 중에는 아무 경고도 안 떴다.** 경위는
`../ics_sim/DevNote.md` **11.22**.

| 무엇이 문제였나 | 어떻게 고쳤나 |
|---|---|
| `STATUS` 시한 초과가 `msgref`·수신 스트림을 어긋냈다 — 명령은 나갔는데 `msgref` 는 그대로여서 **다음 명령이 남의 응답을 먹고 그 다음이 `Invalid command packet header` 로 죽는다.** 루프백 재현: `archon_status()` → `SetConfig` 가 STATUS 본문을 삼킴 → `APPLYSYSTEM` 예외 | `_resync_archon_link()` 로 **연결을 새로 연다.** `msgref` 만 올리면 부족하다 — 부분 수신분이 소켓에 남고, 늦은 응답이 다음 데이터셋에서 튀어나올 수 있다 |
| 손편집 문자열의 **비ASCII 한 자**가 FITS 를 통째로 못 읽게 만들었다. `assert len(head) % 2880` 은 **문자 수**라 통과한다 (`'HELab 차상목'`: 문자 11520 통과 / 바이트 11526 → `Empty or corrupt FITS file`). v1.1 이 운영자 편집 문자열을 헤더에 넣은 첫 판이다 | 3중 방어 — `_check_identity_setup()` 기동 거부 · `build_header` 단정을 **바이트 수**로 · `fits_card` 가 새어 든 값을 `?` 로 치환 |
| 데이터부 2880 패딩(v1.1 신설) + NAXIS 하드코딩 → 실제 프레임이 선언보다 길면 꼬리가 블록 경계에 맞아 `Header missing END card`. **v1.0 은 경고만 내고 열렸다** (진단 가능성을 없앤 셈). 걸리는 경로: `samplemode`(정확히 2배) · ACF 기하 변경 | fetch **앞에서** `framesize` 를 선언 바이트와 대조해 거부. **픽셀 수로 비교하면 samplemode 를 못 잡는다** — 그 경우 기하는 같고 바이트가 2배다 |
| 예외가 나면 `POWEROFF` 를 건너뛴 채 traceback 으로 끝났다 (v1.0 도 같지만 v1.1 이 예외 원인을 늘렸다) | 노출 루프 `try/finally` — 무슨 예외가 나도 CCD 바이어스·클록은 끈다 |

함께 넣은 것:

- **재실행 경고** — 같은 UT 날짜에 파일이 남은 DS 폴더를 다시 돌리면 D-016 이
  번호를 밀어 올린다(v1.0 은 덮어썼다). 데이터셋 시작에 한 번 알린다. 운용
  조치는 위 "재실행은 덮어쓰기가 아니다".
  - ⚠️ 처음 넣은 경고는 **날짜를 안 보고** 폴더의 모든 파일을 세서, 실험실의
    평상 재실행(다른 날 같은 DS)마다 헛경고를 냈다. 오늘 자만 세도록 고쳤다.
- **ACF 선검사** — `configparser.read()` 는 없는 파일에 조용히 성공하고 그
  다음 `items('CONFIG')` 가 `NoSectionError` 로 터져서, "설정 파일이 없다"
  라는 원인이 화면에 안 나왔다. 데이터셋 시작에 `os.path.isfile` 로 확인하고
  절대경로·`cwd` 와 함께 멈춘다. POWERON 앞이라 멈춰도 안전하다.

## smallbuf 사본 — guide 스크립트를 만들 때의 참고 코드

> **smallbuf.py 스크립트는 구버전의 science 유닛을 구동하던 코드로서, smallbuf로
> 구성되는 guide 유닛 제어용 코드 작성 시 참고할 코드이다. 다만, bigbuf 스크립트의
> 코드로도 smallbuf 구성 유닛의 동작이 가능할 수도 있으니, 참조 바람.**
> (운영자 2026-08-26)

**왜 그럴 수 있나** — bigbuf 는 FETCH 주소를 프레임 상태의 `BUFnBASE` 에서 읽고,
그 값은 컨트롤러가 **어떤 버퍼 구성이든 자기 배치대로** 돌려준다. 설계상 구성에
무관하다는 뜻이다.

> ※ 설계상 그렇다는 것이고 **small buffer 유닛에서 실기 검증은 아직 없다.**
> 첫 guide 구동 때 확인할 항목이다.

**bigbuf v1.3 과 다른 자리 — 다섯 곳뿐** (2026-08-26 에 v1.3 으로 맞췄다):

- `newest()` 가 `BUFnBASE` 를 돌려주지 않는다 (5-튜플)
- 그것을 받던 네 자리가 5-튜플 언패킹
- `FETCH` 주소가 small buffer 배치식 `((buf+1)|4)<<29`

헤더·규격 정합·데이터셋 구성·검사는 **글자까지 같다** — 견본 대조 139장 불일치 0.
`test_labtest_spec_copy.py` 의 두 시험이 그 밖의 자리에서 갈라지는 것을 막는다.

⚠️ **이것은 guide 유닛용 스크립트가 아니다.** 기하가 science(19200×9400)이고
`DATASRC`·`CTRL1xx` 규약도 science 그대로다.

**guide 스크립트 착수 때 필요한 것** (raw spec 기준):

- `DATASRC='ARCHON_GUIDE'` + `CTRL1xx` **한 벌** 규약 (raw spec 5.5절)
- **기하를 guide 크기로** — 지금 두 사본 다 science 를 하드코딩한다.
  v1.1.1 의 기하 대조가 어긋난 경우를 fetch 전에 거부하므로 안전 장치는 있다
- `Cn_TEMP` **8자리** (Backplane · Mod3 · Mod4 · Mod5 · Mod6 · Mod7 · Mod9 ·
  Mod10) — 원장 7장 기재분이고 **실기 대조 전이다** (규격 8장 **OI-19**)

## 첫 실행 결과 (기록용 — 돌린 뒤 채운다)

```
날짜 :
유닛 :
데이터셋 :
결과 :
```

## 판 이력

| 판 | 무엇 |
|---|---|
| v1.0 | 실험실에서 실제로 돌려 쓰던 원본 (`__ref_archon_control/` 에 보존) |
| v1.1.0 | raw spec v1.3 적용 (파일명·헤더 144카드·데이터부 패딩·STATUS 텔레메트리) + 적대적 검토 6건 수정 |
| v1.1.1 | 감사에서 잡힌 회귀 4건 수정 — STATUS 시한 초과 후 연결 재수립 / 비ASCII 손편집 값 기동 거부 / 기하·표본 불일치 fetch 전 거부 / 예외에도 `POWEROFF` 보장. 함께: 재실행 시 번호 밀림 경고(같은 UT 날짜), ACF 선검사 |
| v1.1.2 | **리눅스 포팅** (운영자 확정 2026-08-23: 전 계통 리눅스 구동) — 저장소 경로를 윈도우 드라이브 문자(`C:/DATA`·`H:/DATA`·`L:/DATA`)에서 POSIX 경로로, 그리고 **쓰지도 않는 `twilio` import** 를 `try/except` 로 감쌌다(그 패키지가 없는 기계에서 스크립트가 아예 시작하지 못했다). 컨트롤러와의 왕복은 한 줄도 바뀌지 않았다 |
| v1.1.3 | **저장 자리 한 곳으로** (운영자 확정 2026-08-24) — 세 갈래(`_C`/`_A`/`_B`)를 `DATA_STORAGE = ~/AIC/data` 하나로 합치고, `~` 를 `GetDataset` 이 펼치게 했다(안 펼치면 **cwd 아래 `~` 폴더**가 생기고 오류도 안 난다 — `ics_sim config.py` 의 2026-08-23 실측과 같은 함정). 함께 **저장소 선검사**를 ACF 와 같은 자리(POWERON 앞)에 넣었다 — `createFolder` 가 OSError 를 삼켜서, 경로가 틀리면 POWERON 뒤 `os.listdir` 에서 터지고 그 자리가 노출 루프 `try/finally` 의 **바깥**이라 전원을 켠 채 끝났다. 용량을 세려고 `SetDatasetConfig` 호출을 POWERON 앞으로 올렸다(전역 대입과 `print` 뿐이라 컨트롤러와 무관) |
| **v1.3.0** | **Target 데이터셋 신설** (2026-08-26, 운영자): `DS_TARGET = 4`(비어 있던 자리) · `TEST_DARK_NUMBER` 도입으로 dark 를 여러 장 찍는다(다섯 데이터셋 전부 + `_expected_dataset_bytes()` 동반) · 실기 유닛 정보(`STA-0284`, IP `.101`, ACF `KMTC_SCI_101_STA0284_R2608_MK.acf`, 관측자 `SMC`) · `DATA_STORAGE` 한 곳에 저장(DS 폴더 분리 해제).  **`CTRL1ID` = `KMTC-SCI-101`** — CTIO 로 갈 유닛을 실험실에서 시험하므로 **유닛 정체는 시리얼과 1:1**(원자료 `Archon_Unit_Info.txt`)로 두고, 자료를 딴 곳은 `SITE_CODE='KMTK'` 가 따로 말한다 |
| **v1.2.0** | **raw spec v1.5/v1.6 반영 — 헤더 내용 변경** (2026-08-26): 값 카드 135 → **131**(HK 4장 폐지) · `CHMAP_*` **4자 토큰** · `ORIGNAME` → **`EXPID`** · `Cn_*` 구분자 공백 → **`\|`** · 결측 자리 sentinel **`NC`** · 카드 폭 초과 규범(comment 를 뒤에서 자른다) · D-017 사이트 코드 · D-018 번호 공간.  **판을 올린 이유**: `SCRIPT_VERSION`/`SCRIPT_BUILD` 가 그대로 `ICSBUILD` 카드에 실리므로, 1.1.3 에 머물면 헤더가 다른 두 종류 프레임이 같은 값으로 찍힌다.  파일명도 `…v1.2.bigbuf.py` 로 옮겼다 |

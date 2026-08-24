# SMC_CLAUDE.md

`ics_archon/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는
[../README.md](../README.md), 이 폴더의 구성·실행법은 [README.md](README.md).

## 이 폴더가 뭔가

**실기 ICS(`ics_archon`) 다.** `ics_sim`(시퀀서·명령 처리부·메시지 규약·헤더
층)을 **사본 없이 그대로** 쓰고, 그 아래 `DetectorBackend` 자리에 실제 Archon
컨트롤러 제어를 넣은 프로그램이다. 최종적으로 `ics` 로 개명해 운영 배포한다.

제어 코드의 원형은 같은 폴더의 실험실 취득 스크립트
(`archon_kmtnet_labtest_v1.1.bigbuf.py`, 1년 실사용으로 검증된 v1.0 계보)다.
그 스크립트는 **계속 남는다** — 실험실 단독 취득에 쓰는 별개 도구다.

## 먼저 읽을 것

| 문서 | 언제 |
|---|---|
| 이 문서 **"▶ 다음 세션 작업 지시"** | ⭐⭐ **새 세션이면 여기부터.** 목이 정한 다음 일감 둘 + 착수 전 승인이 필요한 것 |
| 이 문서 **"미해결 목록"** | F1~F12 · P1. 작업 2 의 일감이고, **앞 세션 워크플로 결과를 근거로 쓰지 말라는 경고**가 붙어 있다 |
| [README.md](README.md) | 폴더 구성 · 실행법 · 모듈 표 · 계약 어긋남 3건 · v0.0 에 없는 것 |
| `ics_archon/archon/controller.py` 머리말 | **"노출을 누가 재나"** — 이 층의 가장 중요한 판단 |
| `ics_archon/archon/backend.py` 머리말 | 계약과 실기의 어긋남 3건 · 동기 접근자가 스냅샷을 읽는 이유 |
| [README.md](README.md) "실기 첫 실행 절차" | ⭐ **실기를 붙이기 전에 이것부터.** `tools/probe_archon.py` 1~3단계 · 실험실 1유닛 설정 |
| [README_labtest.md](README_labtest.md) | ⭐ **실험실 취득 스크립트에 관한 모든 것** (별개 도구) |
| [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 11.19~11.25 | 왜 그렇게 정했나 (11.25 = 커밋 + 병렬 독출 계획 검토). 9장은 하드웨어 확장점, 3장은 OBSAgent 규약 |
| [`../ics_sim/SMC_CLAUDE.md`](../ics_sim/SMC_CLAUDE.md) | 물려받은 층의 상태·규약 |
| [`../raw_fits_spec/`](../raw_fits_spec/README.md) | 산출 규격(raw FITS pair). 헤더 5장의 바이트 정본은 견본 pair |

## 절대 깨뜨리면 안 되는 것

1. **`ics_sim` 사본은 `_vendor/` 하나뿐이고, 그것을 손으로 고치지 않는다.**
   `_vendor/ics_sim/` 는 `tools/sync_vendor.py` 가 만드는 **생성물**이다(독립
   배포를 위한 것 — 목 2026-08-23 지시). 원천은 형제 `ics_sim/` 이고
   `_simpath.py` 가 그것을 먼저 찾는다 — 저장소에서는 형제가 이긴다.
   raw spec 5장이 개정되면 견본 pair 와 `rawcards.py` 가 함께 바뀌는데 그 기계
   사본이 이미 **셋**이다(`ics_sim/rawcards.py` · `_vendor` · labtest 내장
   `RAWCARDS`) — **네 번째를 만들지 말고**, 형제를 고친 뒤
   `python tools/sync_vendor.py` 를 돌린다. 안 돌리면 `tests/test_vendor.py` 가
   실패한다(`--check` 로 미리 본다).
2. **`ics_sim` 의 규약을 고치지 않는다.** 시퀀서·명령 처리부·OBSAgent 규약은
   시험 318개가 묶어 두고 있다. 합본은 **백엔드 층을 채우는 일**이고, 규약을
   건드려야 할 것 같으면 그것 자체가 재검토 신호다. v0.0 이 `ics_sim` 에 넣은
   변경은 **확장점 3개**(`register_backend()` · `DetectorBackend.writes_files` ·
   `begin_exposure()`)와 **결함 4건**(D-016 게이트 · `~` 확장 · `\#` 탈출 ·
   expnum fsync)이고, **규약 자체는 한 줄도 안 고쳤다**(커밋 `ecf3487`).
   ⚠️ **2026-08-24 에 처음으로 그 규약을 열었다** (목 지시, 작업 1) — 확장점
   `readout_events()` 와 `[readout] acq_per_frame`/`acq_skew_warn`, 그리고
   `Sequencer.drain_writers()`.  **기본값이 꺼짐이라 거동은 종전과 같다**:
   `acq_per_frame=false` 면 `Acquisition Complete.` 4개가 여전히 같은 틱에
   나간다.  **켜면 그 4개의 산포가 두 컨트롤러의 실제 시차가 되어 1.8초 창
   (DevNote 3.3)의 구조적 보장이 없어진다** — 실기 시차 실측 전에는 켜지 말 것.
   여는 것과 어기는 것은 다르다: 커밋에 **연 것임**을 명시한다.
3. **`ArchonLink.command(cmd, timeout=None)` 의 기본값을 바꾸지 말 것.**
   `APPLYALL` 처럼 오래 걸리는 명령이 있어 무한 대기가 기본이어야 한다. 상한은
   부르는 쪽(`controller.py`)이 명령마다 준다 — 프로토콜은 **인식 못 한 명령에
   무응답**이므로(매뉴얼 p.45) 오타 하나로 영구히 멈춘다.
4. **`telemetry = false` 로 두면 왕복이 labtest v1.0 계보와 같아진다.** 그
   성질을 없애지 말 것 — 실기에서 원인을 가르는 첫 수단이다.
5. **동기 접근자 셋(`controller_info`/`controller_telemetry`/`sensors`)은 소켓을
   만지지 않는다.** 시퀀서가 `_backend_fact` 로 **동기 호출**하므로 이벤트 루프
   안이다. `initialize()` 에서 떠 둔 스냅샷을 읽는다 — fetch 뒤에 물어보면
   컨트롤러가 답하지 않을 때 다 읽어낸 노출을 잃는다(labtest 가 v1.1 에서 옮긴
   자리).
6. **긴 블로킹은 반드시 `asyncio.to_thread`.** FETCH(수십 초)와 344 MiB
   쓰기가 그렇다. OBSAgent 시간 창(획득 1.8초 · IDLE 0.9초 · Wrote 25초,
   DevNote 3.3)이 루프 정지를 허용하지 않는다.
7. **헤더에 들어가는 값은 ASCII 전용이다.** 헤더는 문자 단위로 80자씩 조립하고
   파일에는 utf-8 바이트로 쓰므로, 한글 한 자(3바이트)가 2880B 정렬을 깨고
   **파일 전체를 못 읽게** 만든다. `fits_card`(→ `fitswrite.card_image`)의 `?`
   치환과 `header_bytes` 의 **바이트 수** 단정을 둘 다 없애지 말 것.
7-1. **와이어로 나가는 문구는 ASCII 여야 한다.** 전송 계층이
   `decode('ascii', 'replace')` 를 하므로(레거시 IMPv2 는 ASCII 프로토콜이다)
   한글은 `?` 로 바뀌어 관측자가 읽을 수 없다 — **사실은 로그에, 통보는
   ASCII 로** 나눈다. OS 오류 문구도 한국어 Windows 에서 한글로 온다.
8. **기하 대조는 픽셀이 아니라 바이트로, fetch 앞에서.** `samplemode`(32bit
   표본)는 기하가 선언과 같은데 정확히 2배가 된다 — 픽셀 비교로는 안 잡힌다.
9. **저장은 "최신 프레임" 이 아니라 `내 번호`를 담은 버퍼를 찾는다**
   (`parse.find_frame`). 저장은 `write_delay` 뒤 백그라운드라 그 사이 프레임이
   더 나와 있다 — 최신 것을 집으면 그 파일이 **남의 노출 픽셀**을 담고 헤더는
   이 프레임의 것이어서 아무 경고도 없다. 못 찾으면 **저장하지 않는다** (파일
   한 장을 잃는 편이 틀린 파일을 남기는 것보다 낫다). 프레임 상태는
   `FrameTicket` 이 들고 가고 저장 대기열은 FIFO 다.
10. **`__` 접두 폴더는 읽기 전용이다** (운영자 규칙). 편집이 필요하면 사본을 떠서
    작업한다.
9-1. **이미 있는 파일을 덮지 않는다.** `fitswrite.write_frame` 이 `os.replace`
   앞에서 존재를 확인하고 거부한다 (목 승인 2026-08-23). 선검사 하나만으로는
   그 사이의 틈을 못 막는다 — 이번 검토의 1번 결함이 "방어가 한 겹뿐이라
   조용히 지나갔다" 는 사례 자체였다. 실패하면 `.part` 도 지운다.
11-0. **D-016 충돌 선검사의 게이트는 백엔드 속성 `writes_files` 다.**
    `[paths] write_fits` 로 되돌리지 말 것 — 그 플래그는 시뮬 전용이고, 그것에
    묶어 두면 `write_fits=false` 로 실기를 돌릴 때 같은 이름을 조용히 덮어쓴다.
11-1. **실기는 `[timing] time_scale = 1.0` 이어야 한다.** 적분은 컨트롤러가
    재므로 축척을 따라오지 않는다 — 카운트다운이 먼저 끝나면 셔터가 강제로
    닫혀 **노출이 잘린 채 `EXPTIME` 은 요청값으로** 실린다.
11. **전원을 켠 채로 끝내지 않는다.** `IcsArchon.stop()` 이 `backend.shutdown()`
    을 부른다 — 검출기 쪽 위험이다. 전원 차단 여부는 확인된 상태(`powered`)가
    아니라 **`power_attempted`** 로 판단한다: `POWERON` 응답을 잃으면 컨트롤러는
    켜졌는데 `powered` 는 `False` 로 남는다 (F4).
11-2. **종료는 저장 중인 프레임을 먼저 기다린다** (`[archon] shutdown_drain`,
    기본 30초). 전원 차단보다 **앞**이다 — 전원은 몇 초 더 켜져 있어도 되지만
    독출을 마친 프레임은 다시 못 찍는다 (F3).

## 상태 (2026-08-24 — 작업 1·2 반영, **커밋 전**)

### 완료 — `ics_archon` v0.0.0 + 작업 1·2

**1단계(`ics_sim` + labtest 합본)가 커밋 2건으로 올라갔고**, 그 위에 목이
지시한 **작업 1(병렬 독출)·작업 2(F1~F12)** 를 반영했다.  실기 왕복만
미검증이다.

    6a94e57  ics_archon v0.0 -- ics_sim + labtest 합본으로 실기 백엔드 신설
    ecf3487  ics_sim: 바깥 백엔드용 확장점 + 경로·영속성 결함 4건
    (미커밋)  작업 1-A/1-C + 미해결 F1~F12  ← DevNote 11.26

브랜치 `ics-archon-v1.0-build`, **`main` 미합류.**  검증 상태:
`ics_archon` **110 통과 / 실패 0** (98 -> 110) · 벤더 표류 **없음**.
`ics_sim` **330 통과 / 실패 0** (325 -> 330, `tests/test_acq_per_frame.py` 5항목).

**작업 1·2 에서 바뀐 자리** (경위는 DevNote 11.26)

| 어디 | 무엇 |
|---|---|
| `ics_sim/hardware/base.py` | 선택 훅 `readout_events()` 계약 |
| `ics_sim/config.py` | `[readout] acq_per_frame`(기본 false) · `acq_skew_warn`(1.0) |
| `ics_sim/sequencer.py` | `_readout(..., on_frame)` · 획득 완료 발신 재구성 · `drain_writers()` |
| `ics_sim/hardware/sim.py` | **얕은** `readout_events()` (시차 0 — 실구현은 archon) |
| `archon/backend.py` | `_readout_stream()` 신설 (1-A 두 컨트롤러 동시 대기 · 1-C 컨트롤러별 완료 사건) · `shutdown()` F4 · `erase()` F6 근거 주석 |
| `archon/controller.py` | F8 낡은 스냅샷 폐기 · F4 `power_attempted` · F2 `_check_health()` · F5 `fetch_timeout` |
| `archon/parse.py` | F9 `MODULE_TYPES` 전량 + `AD_TYPES` · F2 `POWER_STATES`/`power_state`/`overheating`/`health_problems` |
| `archon/fitswrite.py` | F7 홑따옴표 겹치기 + 절단 안전 |
| `config.py` · `ics_archon.ini` | `shutdown_drain` · `fetch_timeout` + FETCH/frame 상한 교차검사 |
| `app.py` | F3 종료 전 저장 대기 |
| `tools/sync_vendor.py` | F12 파생물만 제외 |
| `tools/probe_archon.py` | F2 `POWER`/`OVERHEAT` 확인 · F9 `AD_TYPES` |
| `tests/` | `repo_only` 표식(F11) + 회귀 시험 12항목 |

- 신설 `ics_archon/ics_archon/` — `_simpath` · `__init__`(버전·`build_id`) ·
  `config`(`[archon]`) · `app`(`IcsArchon(IcsSim)`) · `__main__` +
  `archon/`(protocol · parse · controller · fitswrite · backend).
- 신설 `ics_archon.ini` — `[archon]` 절이 컨트롤러 배선. 나머지 절은
  `ics_sim.ini` 와 같은 것을 읽는다(실기에서 달라지는 값만 주석으로 풀었다).
- 신설 `tests/` — `fake_archon.py`(가짜 컨트롤러, 버퍼 2~3개 순환 + `LOCKn`
  존중 + 프레임별 픽셀) + 9개 파일 **98항목, 실패 0**.
  `python -m pytest tests` — **코드를 손봤으면 돌리고 나가라.**
- 신설 `tests/test_ini_cards.py`(ini -> FITS 카드 전수) ·
  `tests/test_failures.py`(오류 시나리오 21개) — 아래 "설정·오류 전수 검토".
- 신설 `tools/probe_archon.py` — **실기 첫 실행 도구.** 1단계 읽기 전용
  (전원 안 켬) → 2단계 ACF 대조(`RCONFIG` 확인만) → 3단계 프레임 1장(전원 ON,
  `--expose` 필요, 끝나면 무조건 `POWEROFF`). 미검증 3자리를 컨트롤러에 직접
  물어보고 **독출 시간·FETCH 속도를 실측**한다. 절차는 README.
- `ics_sim` 변경은 **확장점 3개 + 결함 4건**이고 시뮬 거동은 무변경이다
  (커밋 `ecf3487`, 시험 318 -> **325 통과**). 규약은 안 건드렸다 — 위 규약 2번.
- **독립 배포**: `_vendor/ics_sim/`(24모듈) + `MANIFEST.sha256`.
  `ics_sim` 을 설치하지 않고 `ics_archon` 만 두어도 돈다 (목 2026-08-23 지시).

**검증된 것**
- 견본 v1.0 pair 144카드 **바이트 단위 재현**(MK·NT, 불일치 0) · 2880B 정렬 ·
  `BITPIX=16`+`BZERO=32768` 저장형 · astropy 왕복.
- 가짜 컨트롤러 2대로 **전 경로**: DARK·OBJECT 두 갈래 모두 `Acquisition
  Complete.` 4회 · `Wrote` 4회 · `EXPSTATUS=IDLE` 1회 → pair 2파일 · 픽셀 값
  일치 · `CTRLnSN`(BACKPLANE_ID) · `Cn_TEMP` 5자리 · `Cn_VOLT/CURR` 7자리 ·
  5.9절 "양쪽 동일" · `CCDTEMP` sentinel.
- 제어 시퀀스 순서(CLEARCONFIG→APPLYALL→POWERON→LOADPARAMS→FETCH→POWEROFF) ·
  `APPLYALL` 은 프레임마다가 아니라 한 번 · ERASE 는 두 대 다 · STATUS 시한
  초과가 프레임을 잃지 않음 · samplemode 기하 불일치는 fetch **앞에서** 거부.
- 진행률이 ini 의 시뮬 모델이 아니라 컨트롤러 `BUFnLINES` 에서 온다.
- **파이프라인 겹침** — 저장이 다음 프레임 개시보다 늦어도 각 파일이 자기
  프레임 자료를 담는다(가짜 픽셀에 프레임 번호를 섞어 값으로 확인). 그리고
  **버퍼가 재활용된 경우에는 저장을 거부**한다 — 틀린 픽셀을 쓰지 않는다.

**첫 실행에서 바로 터질 결함 하나를 잡았다 (2026-08-23, 목 질문 중 발견)**
- **완료된 프레임이 하나도 없는 컨트롤러**(첫 전원 투입)에서 `newest()` 가
  `-1` 을 주는데, 저장이 `prev + 1 = 0` 을 기다렸다. 컨트롤러가 첫 프레임에 1 을
  붙이는 순간 "0 을 지나쳤다" 가 되어 **첫 노출이 통째로 버려졌다.**
  → `parse.next_frame()` 이 "prev 이후 **가장 이른** 완료 프레임" 을 찾고,
  `prev < 0` 이면 번호를 못박지 않는다. 회귀 시험
  `test_stage3_survives_a_controller_with_no_frames_yet`(가짜 `fresh=True`).

**❌ 미검증 (실기)**
- **실물 왕복 전체.** 가짜 상대역은 우리가 읽은 규격대로 답한다.
- 표시는 코드에 `PROVISIONAL` 로 남겼다 — 아래 "검토사항" B 항목.
- **먼저 `tools/probe_archon.py` 1~3단계를 돌린다** (README "실기 첫 실행 절차").

### 설정·오류 전수 검토 (2026-08-23, 목 지시) — 결함 9건

**ini -> FITS 대조.** `ics_archon.ini` 의 **키 125개 전부**가 어느 한쪽
로더(`ics_sim.config` · `ics_archon.config`)에 읽힌다. `[archon]` 은 키 24 ↔
필드 22 가 **양방향으로 완전 대응**한다(ini 로 못 바꾸는 필드 0 · 대응 없는 키
0). 판정 원장 v1.14 의 `Source = ICS INI` **17장**은 기본값과 겹치지 않는 값을
넣어 **파일에서 되읽어** 확인했다 — `tests/test_ini_cards.py`.

    ORIGIN OBSERVAT TELESCOP LATITUDE LONGITUD ELEVATIO   [site]/[node]
    DETECTOR CAMVER INSTRUME FPAID                        [camera]
    CTRL1ID/SN/CFG CTRL2ID/SN/CFG RDMODE                  [controllers]

함께 못박은 것 — ini 가 **백엔드 보고값(`BACKPLANE_ID`)을 이긴다**, 비우면
컨트롤러 값이 실린다, `[node] site` 한 줄이 파일명 `<SITE>`·`OBSERVAT`·좌표·
`ORIGIN` 을 **함께** 끌고 간다(한쪽만 따라오면 converter 의 유일한 하드 실패),
테스트베드는 좌표가 sentinel.

**고친 결함 9건.** 전부 회귀 시험을 붙였다 (`test_ini_cards.py` ·
`test_failures.py`, 시험 57 -> **85개** — 그 뒤 독립 배포·병렬 검토를 넣어
최종 **98개**).

| # | 결함 | 왜 위험한가 |
|---|---|---|
| 1 | **D-016 충돌 선검사가 `[paths] write_fits` 에 묶여 있었다** | 그 플래그의 뜻은 "시뮬이 더미 FITS 를 만드는가" 다. archon 은 무관하게 실파일을 쓰므로, 저장소 기본값(`false`)으로 실기를 돌리면 같은 이름을 **조용히 덮어썼다** — 실측 재현. 게이트를 백엔드 속성 `writes_files` 로 옮겼다 |
| 2 | **첫 전원 투입에서 첫 노출을 버렸다** | 완료 프레임이 없으면 `newest()` 가 -1 을 주는데 저장이 `prev+1=0` 을 기다려 "0 을 지나쳤다" 로 떨어졌다 -> `parse.next_frame()` |
| 3 | **프레임이 안 나오면 영구 대기** | `EXPSTATUS=READOUT` 에 갇혀 OBSAgent 가 `opause` — 조용한 정지다. `[archon] frame_timeout` 신설, 넘기면 레거시 `DMA WAIT TIMEOUT` 경로 |
| 4 | **와이어는 ASCII 인데 오류 문구가 한글이었다** | 전송 계층이 `decode('ascii','replace')` 를 하므로 관측자는 `?` 만 본다. 통보는 ASCII, 진단은 로그로 갈랐다 (OS 오류 문구도 한국어 Windows 에서 한글로 온다) |
| 5 | **`numpy` 부재가 저장 태스크를 조용히 죽였다** | `to_fits_data()` 가 안에서 import 하는데 `ImportError` 가 `BackendError` 밖으로 새서 `Wrote` 0회·오류 0회 (11.20 critical 과 같은 부류). 잡고, 기동에서 numpy 확인 |
| 6 | **`?xx` 거부에 재접속·재시도를 되풀이했다** | 같은 설정을 다시 밀면 같은 거부가 온다. 원인이 "망이 불안하다" 로 오인된다 -> `reply_error` 는 즉시 실패 |
| 7 | **`initialize` 실패가 컨트롤러당 2번 일어났다** | chip 이 둘이라 `APPLYALL` 이 두 번 나갔다 -> 실패도 프레임 단위로 기억 |
| 8 | **`time_scale != 1.0` + archon = 노출이 조용히 잘린다** | 적분은 컨트롤러가 재므로 축척을 안 따라온다. 카운트다운이 먼저 끝나 `close_shutter()` 가 셔터를 강제로 닫고, `EXPTIME` 은 요청값 그대로 실린다. 교차 검사 경고 신설 + `close_shutter` 에 여유 폭(정상 경로에서는 `APPLYSYSTEM` 을 안 보낸다) |
| 9 | **`_head()` 가 `\#` 를 안 벗겼다** | `FPAID = FPA\#1` 이 `'FPA\#1'` 로 실렸다 (`_text_or` 만 벗기고 있었다) |

**교차 검사 신설** (`config._cross_checks`) — 한쪽만 보면 둘 다 정상인 조합을
기동에서 알린다: `time_scale != 1.0` · `[auxcontrol] enabled=true` ·
`[behavior] inject` 가 켜짐 · **archon 이 보지 않는 설정**(`write_fits` ·
`fits_shape`)이 바뀌어 있음.

### 이 세션에서 확정한 매뉴얼 사실 (새로 찾은 것)

- **`FRAME` 에 진행 카운터가 있다** — `BUFnLINES`(라인 진행) ·
  `BUFnPIXELS`(픽셀 진행), 쓰기 중 버퍼는 `WBUF` (p.49-50). 그래서 독출
  진행률을 **추정이 아니라 보고값으로** 낼 수 있다. labtest 는 쓰지 않았다.
- **오류 응답은 `?xx`**, **인식 못 한 명령은 무응답**, 이진 응답은 `<xx:` +
  1024B **개행 없음** (p.45). labtest 는 `<xx` 만 대조해 `?xx` 를 프레이밍
  오류로 뭉갰다.
- `STATUS` 필드 이름 확인 — `POWERGOOD` · `BACKPLANE_TEMP` · `MODm/TEMP` ·
  레일 `P2V5_V/I`…`P35V_V/I` (그 밖에 `N35V`/`P100V`/`N100V`/`USER`/`HEATER`
  도 있다 — 규격 `Cn_VOLT` 는 7개만 쓴다). `FANTACH` 은 Rev F 만.
- `FASTLOADPARAM p d` 가 "즉시 로드" 다 (p.52) — STOP 으로 적분을 자를 수 있는지
  실기 확인 항목의 근거.
- **`LOCKn` (p.50)** — 버퍼 n 을 읽기용으로 잠근다(`n=0` 은 전체 해제).
  labtest 는 2026-05-28 에 이 명령을 뺐다("remove to fetch debug"). **v0.0 은
  되돌렸다** (`[archon] lock_buffer`) — 아래 검토사항 A5 가 그 이유다.

## ▶ 이어서 시작하는 자리

| 순서 | 할 일 |
|---|---|
| **1** | ~~`ics_archon` v0.0 작성~~ **완료 (2026-08-23)**, ~~커밋~~ **완료 (2026-08-24, `ecf3487`+`6a94e57`)** |
| **1.5** | ~~작업 1(병렬 독출) · 작업 2(F1~F12)~~ **완료 (2026-08-24)** — 아래 "작업 1·2" 절. ⚠️ **아직 커밋 안 했다** |
| **2** | **다듬기** — 아래 "결정사항"을 목이 확인하고 "검토사항 A"(실기 없이 되는 것)를 처리한다 → `v0.1`. **P1(ABORT 와 노출 번호)도 목 판단 대기** |
| **3** | **시험 결과 반영** — labtest 실기 구동 결과 + `ics_sim` 시험 결과로 디버깅·업데이트. "검토사항 B" 가 그 목록이다. **1·2 와 병행이며 이것을 기다리지 않는다** |
| **4** | **main 합류** — **v0 완성 또는 v1 즈음, 진행하면서 판단**(목 2026-08-23). 미리 정해진 시점은 없다. 방식은 `--no-ff` 거품 머지 |
| **5** | **guide 계통** — guide raw 규격이 정해진 뒤 smallbuf 판에 적용 |

## ▶ 작업 1·2 — **완료 (2026-08-24)**

목이 11.25 의 계획을 보고 **범위를 좁혀 결정**했다.

> ics_sim에서는 병렬독출 구현하지 말고, 간단히 모사만 하고 ics_archon에서만
> 구현하자. 작업1, 2, 둘다 진행해줘.

그래서 11.25 견적(~300줄)의 가장 큰 덩어리 -- `ics_sim/hardware/sim.py` 를 두
컨트롤러로 모사하고 시차 주입까지 붙이는 것 -- 이 빠졌다.  **계약 훅 자체는
줄이지 못했다**: `Acquisition Complete.` 를 내보내는 것은 시퀀서이므로 "어느
컨트롤러가 끝났나" 가 계약을 건너야 한다.  경위는 DevNote **11.26**.

### 작업 1 — 두 컨트롤러 병렬 독출

| | 지시 | 결과 |
|---|---|---|
| **1-A** | FRAME 검사를 둘 다 동시에 | ✅ **고쳤다** (결함, F1).  두 프레임을 함께 기다리고 완료 통보는 **둘 다 끝난 뒤**.  `Acquisition Complete.` 4개는 여전히 같은 틱이라 1.8초 창 산포는 0 |
| **1-B** | fetch 를 병렬로 | ✅ **이미 되어 있었다.**  이번에 시험으로 못박음(느린 NT 로 겹침 확인) |
| **1-C** | 프레임별 `Acquisition Complete.` | ✅ **스위치 뒤에 넣었다** -- `[readout] acq_per_frame`(기본 `false` = 종전 거동) |

- 계약: `DetectorBackend.readout_events()` **선택 훅** (`('progress', pct)` ·
  `('frame', ctrltag)`).  없으면 `readout()` 로 떨어진다 -- 구판 백엔드는
  아무것도 안 바뀐다.
- `[readout] acq_skew_warn`(기본 1.0초) -- **스위치와 무관하게 시차를 잰다.**
  `acq_per_frame` 기본값을 정할 근거가 그 실측이기 때문이다.
- `ics_sim` 쪽은 **얕은 모사**다 (시차 0).  목적은 그 분기를 `ics_sim` 시험도
  밟게 하는 것 -- 시뮬이 훅을 안 내놓으면 **새 분기가 실기에서 처음 돈다.**

⚠️ **이것이 `ics_sim` 규약(3.3)을 처음 연 건이다.**  목 지시로 연 것이므로
위반이 아니고, 기본값이 꺼짐이라 **거동은 종전과 같다.**  커밋 메시지에 "어긴
것이 아니라 연 것" 이라고 적을 것.

### 작업 2 — v0 세부 검토·수정

**F1~F12 를 코드로 다시 읽어 판정했다.**  11.25 의 경고("앞 세션 워크플로
결과를 근거로 쓰지 말라")대로 항목마다 재확인했고, **F6 은 결함이 아니었다.**

## 미해결 목록 — 처리 결과 (2026-08-24)

| # | 판정 | 무엇을 했나 | 자리 |
|---|---|---|---|
| **F1** | 결함 | 작업 1-A | `backend._readout_stream()` |
| **F2** | 결함 | 취득 경로가 전원·과열을 한 번도 안 봤다.  매뉴얼에서 **`POWER=n`(0~5)** 을 새로 찾았다 -- `POWERON` 이 성공해도 `POWER=3`(일부 모듈만 올라옴)일 수 있다 | `parse.health_problems()` · `controller._check_health()` |
| **F3** | 결함 | 종료가 **저장 중인 프레임을 버렸다** | `Sequencer.drain_writers()` + `[archon] shutdown_drain` |
| **F4** | 결함 | `POWERON` 응답을 잃으면 `POWEROFF` 를 건너뛰었다 (규약 11 위반) | `controller.power_attempted` |
| **F5** | **미확정 — 실측 대기** | FETCH 상한을 `[archon] fetch_timeout` 으로 뺐고, `frame_timeout` 과 어긋나면 기동에서 알린다.  **값은 probe 3단계 실측 뒤에** | `config._cross_checks` |
| **F6** | **결함 아님** | 아래 | -- |
| **F7** | 결함 | 값 안의 `'` 를 안 겹쳤다 (FITS 표준 4.2.1).  절단이 겹친 따옴표를 반 자르는 것도 함께 막음 | `fitswrite.card_image` |
| **F8** | 결함 | `STATUS` 실패 뒤 **낡은 스냅샷을 실측값처럼** 다시 실었다 | `controller.refresh_status` |
| **F9** | 결함 | 13/14/15 결측 + **AD 판정이 `t == 2` 하나**였다 | `parse.MODULE_TYPES` · `parse.AD_TYPES` |
| **F10** | 이미 닫힘 | -- | -- |
| **F11** | 결함 | `repo_only` 표식으로 저장소/배치본을 가름 | `tests/conftest.py` · README |
| **F12** | 결함 | `.py` 만 추적하던 것을 **파생물만 빼고 전부**로 | `tools/sync_vendor.py` |

**F6 은 국면 불일치가 아니라 어휘의 한계였다.**  ERASE 실패가 `Failed to
initialize one or more ICs` 로 나가는 것을 결함으로 적어 뒀는데, **OBSAgent 가
알아듣는 ICS 오류 문구는 둘뿐이다**(DevNote 3장).  그 둘 중에서는 ERASE 가
취득 개시 *전*의 준비 국면이므로 이쪽이 맞고, 새 문구를 지어내면 OBSAgent 가
못 알아듣는다 -- **고치면 규약을 깨는 자리**다.  코드는 그대로 두고 근거를
주석으로 남겼다.

**F2 는 막지 않는다.**  전원·과열 이상을 발견해도 노출을 중단하지 않는다 --
이 필드들은 실기 미검증(PROVISIONAL)이고, 오독 하나로 관측을 통째로 세우는
쪽이 더 나쁘다.  **보고하지 않는 필드는 이상으로 세지 않는다**(없는 필드를
이상으로 세면 첫 실행이 통째로 경보가 된다).  대신 크게 남기고
`probe_archon` 1단계가 같은 값을 눈으로 확인한다.

### 정책 미정 — **목 판단이 남아 있다**

**P1 — ABORT 와 노출 번호.** 실측된 비대칭: 같은 프로세스에서 ABORT 하면 번호를
**재사용**하는데, 프로그램을 재시작하면 그 번호를 **건너뛴다**(영구 구멍). 중단
국면에서 파일은 항상 0개였고, `GO n` 의 1번 프레임 파일은 남았다. **어느 쪽이
규범인지 정해진 바 없다** — 정하고 나서 시험으로 못박아야 한다.  이번 작업에서는
**건드리지 않았다** (정책이 정해지기 전에 코드를 바꾸면 그 자체가 결정이 된다).


## 결정사항 — v0.0 에서 내가 정한 것 (목 확인 요망)

되돌리기 쉬운 순서로 적었다. **1~3 이 구조적 판단**이고 나머지는 국소적이다.

| # | 정한 것 | 왜 | 되돌릴 때 |
|---|---|---|---|
| 1 | `ics_sim` 을 **가져다 쓴다** (사본 없음). `_simpath` + `register_backend` | 기계 사본이 이미 둘이라 세 번째를 만들면 raw spec 5장 개정 때 어긋난 하나를 놓친다 | 사본을 뜨면 `_simpath` 를 지우고 import 를 상대경로로 |
| 2 | 저장을 **원시 바이트**로 쓴다 (astropy 아님) | ① 취득 경로에 astropy 의존을 넣지 않는다 ② 344 MiB 사본을 안 만든다(제자리 byteswap) ③ 데이터부 2880B 패딩을 명시 | `ics_sim.fitsout.write_dummy_fits` 로 갈면 된다 (계약은 같다) |
| 3 | **적분은 컨트롤러가 잰다.** 시퀀서 카운트다운은 알림 | `IntMS`+`LOADPARAMS` 가 적분·셔터·독출을 다 몬다. 호스트가 재려면 트리거를 직접 흔들어야 하고 그건 검증된 경로가 아니다 | — (하드웨어 사실) |
| 4 | DARK/BIAS 노출을 **`readout()` 첫머리**에서 건다 | 계약에 노출 개시 훅이 없다. 시퀀서가 `_integrate_dark` 에서 백엔드를 안 부른다 | `base.py` 에 `begin_exposure()` 를 넣으면 깔끔하다 (D-012 선례가 있다) |
| 5 | `erase(ccd)` 를 **두 대 다** flush | NT 를 안 비우면 잔상이 남는다. master 만 flushing 은 레거시 IC 구조의 관례다 | `full_flush_on_erase=false` 로 끌 수 있다 |
| 6 | `close_shutter()` 는 **적분 중일 때만** `TRIGOUTFORCE=1` | 정상 경로에서는 이미 닫혀 있다. 독출 중에 `APPLYSYSTEM` 을 보내지 않으려는 것 | — |
| 7 | 참조번호를 **보내기 전에** 올린다 | 시한 초과 뒤 늦은 응답이 다음 명령 번호와 맞아떨어지는 일이 원리상 없어진다 (labtest 회귀 1번의 근본 처방) | **labtest 에 역이식할 후보** |
| 8 | `?xx` 오류 응답을 구분하고, 읽기 버퍼를 **하나로** 둔다 | labtest 는 `<xx` 만 대조해 컨트롤러의 거부를 프레이밍 오류로 뭉갰다. 그리고 `archoncmd` 가 `msgbuf` 를 안 봐서 이진 꼬리를 놓칠 구멍이 있었다 | **labtest 에 역이식할 후보** |
| 9 | `progress_step = 0` 은 "**값이 바뀔 때마다**" | 폴링이 라인 진행보다 빠르면 같은 값을 되풀이 보낸다 | — |
| 10 | `.part` 로 쓰고 `os.replace` | 중간에 죽은 반쪽 파일이 최종 이름을 차지하면 D-016 선검사가 그 번호를 점유된 것으로 본다 | — |
| 11 | `flash_led` 는 **하드웨어를 만지지 않는다** | 실기 LED 배선이 미확정이다. 트리거를 임의로 흔들면 셔터가 열린다 | 배선 확정 후 구현 |
| 12 | `RDMODE` 를 ACF 이름에서 유도 (ini 가 이긴다) | 컨트롤러는 적용 ACF 이름을 보고하지 않는다 (p.54) | ini 에 적으면 그쪽이 이긴다 |
| 13 | 기본 백엔드 = `archon` (ini 가 **안 적었을 때만**) | `python -m ics_archon` 이 조용히 시뮬로 도는 것을 막는다 | `[hardware] backend = sim` 을 적으면 존중한다 |
| 14 | 프레임 상태를 **`FrameTicket`** 으로 프레임이 들고 간다 (저장 대기열 FIFO) | 저장은 `write_delay` 뒤 백그라운드다 — 컨트롤러 필드에 두면 뒤 프레임이 앞 프레임의 값을 덮는다(엉뚱한 프레임 대기 · 이중 노출). `ics_sim` 이 같은 부류를 두 번 겪었다(12.10 · 11.20 critical) | — |
| 14-1 | **이미 있는 파일은 덮지 않는다** (`fitswrite.write_frame`) — **목 승인 2026-08-23** | D-016 선검사와 쓰기 사이에 `write_delay`+저장시간만큼 틈이 있고, 그 틈에 누가 그 경로에 파일을 두면 `os.replace` 가 말없이 지운다. 둘 중 하나를 잃어야 하면 **새 프레임을 버리는 쪽**이 맞다 — 옛 프레임은 이미 아카이브에 들어갔을 수 있고 되돌릴 수 없는데, 새 프레임은 다시 찍을 수 있고 오류가 크게 뜬다. **이름은 여전히 시퀀서가 정한다** (백엔드는 "덮지 않겠다" 고만 한다) | — |
| 15 | fetch 중 **`LOCKn` 으로 버퍼를 잠근다**(`lock_buffer=true`) + fetch 앞 프레임 번호 대조 | 검토사항 A5 참조. labtest 가 뺐던 명령을 되돌린 것이라 **실기 확인 항목** | `lock_buffer=false` 로 끄면 labtest 와 같아진다(대조는 남는다) |

## 검토사항

### A. 실기 없이 처리할 수 있는 것 (2단계)

1. **메모리** — 344 MiB 프레임 2개를 동시에 들고 있다(컨트롤러당 fetch 버퍼
   하나). 제자리 변환으로 사본은 없앴지만, **FETCH 를 받는 대로 디스크에
   흘려 쓰면** 상주가 블록 하나로 줄어든다. 25초 창에 여유가 없으면 이쪽이
   답이다.
2. **`[readout]` 의 시뮬 파라미터가 archon 에서 무의미하다** —
   `pctread_start/step/tick` 을 안 쓴다. `config.validate()` 에 "쓰이지 않는
   설정" 경고를 넣을지.
3. **`base.py` 에 `begin_exposure()` 를 넣을지** (결정사항 4). 넣으면 DARK 와
   셔터 노출이 같은 자리에서 시작하고, `readout()` 이 "읽기만" 하게 된다.
4. **labtest 역이식 3건** (결정사항 7·8 + `BUFnLINES` 진행률). labtest 는 실기
   투입 직전이라 지금 손대는 것이 맞는지 목 판단이 필요하다.
5. ⚠️ **버퍼 수 대 저장 여유 — v0.0 에서 발견한 실제 제약.**
   BIGBUF=1 은 **버퍼가 2개**인데 노출 1회가 프레임 **2개**(flush + 취득)를
   만든다. 즉 **다음 노출이 이 프레임의 버퍼를 정확히 덮는다** — 저장이
   `write_delay` 뒤 백그라운드라 그 경합이 구조적으로 존재한다. 실기 값
   (프레임 ~40초 · `write_delay` 3.4초)이면 여유가 크지만 **독출 시간 실측이
   나오기 전에는 알 수 없다.** v0.0 이 넣은 것은 둘 — `LOCKn` 잠금과 fetch 앞
   프레임 번호 대조(어긋나면 저장 거부). 남은 판단: ① `full_flush_on_erase` 를
   끄면 프레임 소비가 절반이 된다 ② `LOCKn` 을 실기에서 켜도 되는지(labtest 가
   왜 뺐는지 근거가 "fetch debug" 한 줄뿐이다) ③ 스트리밍 저장(위 1번)이면
   잠금 시간이 짧아진다.
6. **`ics_sim` 쪽 `hardware/archon.py` 스텁의 처지** — 이제 실기 구현이 여기
   있으므로 그 스텁은 "등록이 안 됐을 때의 안내" 역할만 한다. 문구를
   `ics_archon` 을 가리키게 고칠지.

### B. 실기 왕복으로만 확정되는 것 (3단계)

| 미검증 자리 | 실기에서 확정될 값 | 코드 표시 |
|---|---|---|
| STATUS 필드·모듈 나열 순서 | `TEMP_SLOTS`(BACKPLANE + MOD5~8)가 실물과 맞는지. **정본 명세는 규격 수록 예정** | `parse.TEMP_SLOTS` |
| 독출 시간·진행률 거동 | `BUFnLINES` 가 선형인지, 독출 개시 전 0 구간이 있는지. **FETCH+저장이 `Wrote` 25초 창에 들어가는지** | `controller.wait_frame` · `backend.readout` |
| 픽셀 좌우 배치 | Archon 이 주는 X 순서가 raw spec 4.1절(`chips[0]` = X 낮은 쪽)과 같은지 | `backend.write_frame` |
| 산출물 실물 | 기하(19200×9400) · `DETID` · `DATE-OBS` · converter 투입 | `fitswrite.write_frame` |
| STOP 이 적분을 자를 수 있나 | `FASTLOADPARAM IntMS 0`(p.52)이 즉시 반영되는지 | `backend.close_shutter` |
| 적분 중 `APPLYSYSTEM` 이 안전한가 | 강제 셔터 폐쇄가 독출을 흔들지 않는지 | 〃 |
| 셔터 트리거 배선 | `shutter_ctrl` 을 `both` 에서 한쪽으로 좁힐지 | `[archon] shutter_ctrl` |
| ERASE 운용 | 매 노출마다 전체 독출 flush 가 맞는지(독출 1회분이 걸린다) | `[archon] full_flush_on_erase` |
| 노출 파라미터 슬롯 | `PARAMETER1/2` 와 `IntMS`/`Exposures` 가 현행 ACF 와 맞는지 | `[archon] param_*` |
| `DATE-OBS` 정밀도 | `TIMER` ↔ 호스트 UT 상관 + `BUFnREATIMESTAMP` 로 개선할지 | 지금은 호스트 시각 |

### C. 원천이 아예 없는 것

- **듀어·환경 HK** (`sensors()`) — 공급 3계통(ICG RTD · standalone RTD readout
  unit · Tapaculo). labtest 도 안 읽으므로 옮겨올 원형이 없다. 붙일 때의 계약은
  `ics_sim/hardware/base.py` 의 `sensors()` docstring 에 다 있다(키 이름 · 대표
  센서 `ccdtemp1` · 못 읽은 항목은 넣지 않기).
- **guide 계통** — guide raw 규격 미정.
- **binning** (`BIN`) — `ics_sim` 쪽도 스텁이다.

## 리눅스 구동 (운영자 확정 2026-08-23)

**`ics_sim` · `ics_archon` · labtest 전부 리눅스에서 돌린다.**  전수 감사 결과
포팅이 필요한 것은 셋뿐이었고 다 고쳤다 — 그 밖의 코드는 이미 이식성이 있다
(`sys.platform`/`os.name` 분기 0 · 윈도우 전용 모듈 0 · 텍스트 `open()` 은 전부
`encoding=` 명시 · `siteid` 는 `getaddrinfo` + UDP 탐침이라 리눅스에서 더 정확).

| 고친 것 | 무엇이 문제였나 |
|---|---|
| labtest 저장소 경로 | `C:/DATA` · `H:/DATA` · `L:/DATA` (윈도우 드라이브 문자). 리눅스에서는 경로로 성립하지 않아 **cwd 아래 `C:` 라는 이름의 폴더를 만들고 오류도 안 난다** -> `/data` · `/mnt/ssda/DATA` · `/mnt/ssdb/DATA` (`<---- Set this`) |
| labtest 의 `twilio` import | 함수 본문이 통째로 주석 처리돼 **쓰지도 않는데** 모듈 최상단에서 import 했다 -> twilio 없는 기계에서 **스크립트가 아예 시작 못 했다.** `try/except ImportError` 로 감쌌다 |
| `.gitattributes` | `*.ini`·`*.acf` 가 정규화 목록에 없어 CRLF 로 체크아웃됐다 -> `text eol=lf` 추가 |

⚠️ **labtest 판올림**: 위 둘을 고쳐 `v1.1.1` -> **`v1.1.2`** (`SCRIPT_BUILD`
2026-08-23T12:00Z). 컨트롤러와의 왕복은 한 줄도 안 건드렸다. `smallbuf` 판도
같이 고쳤다(원본은 `__ref_archon_control/` 에 그대로 있다).

### 경로 설정 — `~` 확장 (2026-08-23, 목 지시로 발견)

**`[paths] data_dir` 이 `~` 를 펼치지 않았다.**  `os.makedirs('~/AICS/data')` 는
오류를 내지 않는다 — `~` 를 정상적인 상대 경로 조각으로 보고 **작업 디렉터리
아래에 `~` 라는 이름의 폴더**를 만든다.  즉 설정에 `~/AICS/data` 를 적어 놓고
자료가 거기 있다고 믿는 동안 `<cwd>/~/AICS/data` 에 쌓인다.  `expnum_file` 만
펼치고 있었던 것이 오히려 함정이었다("경로 설정은 `~` 를 받는다" 고 믿게 한다).

`data_dir` · `[logging] file` · `[archon] acf_*` 를 다 펼치게 고쳤다
(`config._path_or`).  시험 `ics_sim/tests/test_path_settings.py` (5항목).

**`[paths] data_dir = ~/AICS/data`** 로 확정했다 (목 2026-08-23).

- 그 자리는 **실제 디렉터리든 심볼릭 링크든 된다.**  프로그램이 매번 경로를
  다시 해석하고, 임시 파일(`.part`)과 최종 파일이 같은 디렉터리라 파일계통을
  넘는 rename 이 없다.  `expnum_file` 은 `~/AICS/Config/` 에 따로 있어 저장
  경로를 옮기거나 비워도 번호가 되돌아가지 않는다(그 분리의 목적이다).
  ⚠️ 링크 **대상이 먼저 있어야** 한다 — 끊긴 링크면 `makedirs(exist_ok=True)`
  가 `FileExistsError` 로 거부한다(`exist_ok` 는 `isdir` 을 본다).
- ⚠️ **상대경로(`../data`)는 권하지 않는다.**  ini 위치도 프로그램 위치도 아니라
  **실행한 디렉터리** 기준으로 풀리므로, 띄우는 방법(systemd `WorkingDirectory` ·
  cron · 손으로 띄운 셸)이 바뀌면 **같은 설정이 다른 곳에 자료를 쌓는다.**
  오류가 없어 드러나지도 않는다(labtest 의 ACF 상대경로가 같은 부류로 가장 많이
  넘어졌다).  `backend=archon` + 상대경로면 교차 검사가 경고한다.
- **기동 배너가 풀어낸 절대경로를 찍는다** — 링크든 `~` 든 상대경로든 자료가
  실제로 어디에 쌓이는지 t=0 에 보인다.

**남은 운용 확인** — USB SSD 마운트 지점은 기계마다 다르다
(`lsblk -o NAME,LABEL,MOUNTPOINT`).  labtest 의 `/mnt/ssda`·`/mnt/ssdb` 는
**추측값**이므로 실제 마운트에 맞출 것.

## 6자리 노출 번호 카운터

**이름은 `EXPNUM` 이다.**  코드에서는 `state.IcsState.expnum`, 와이어에서는
`EXPNUM` 명령/질의(OBSAgent 가 readout 중 스스로 묻는다 — DevNote 3장 4항),
파일명에서는 `<SITE>.<YYYYMMDD>.<NNNNNN>` 의 뒤 6자리다.

- **번호 공간**: `rawpair.NUM_SPACE = 100000` -> 관측 운용은 `000000`~`099999`
  이고 넘으면 되감는다. 6자리 형식은 유지된다(실험실 DS 체계가 6자리 전체를
  쓰기 때문 — raw spec 2.3절).
- **저장 위치**: `[paths] expnum_file` (`~` 확장됨). 비우면 **설정 파일 옆**으로 자동 결정
  (`config.resolve_expnum_file`) — `~/AICS/Config/ics_archon.ini` 면
  `~/AICS/Config/ics_archon.expnum`. `data_dir` 와 **일부러 분리**했다: 저장
  파일을 지우거나 옮겨도 번호가 되돌아가지 않아야 한다(운영자 확정
  2026-08-11, DevNote 11.12). `-c` 로 여러 구성을 나란히 돌려도 카운터가 섞이지
  않는다.
- **언제 기록하나**: 프레임이 번호를 **집는 순간**(`next_suffix()`)이다. 노출
  중에 죽어도 그 번호는 소비된 것으로 남아 재사용되지 않는다.
- **재기동**: `load_expnum()` 이 기록값 +1 부터 시작한다.
- **재부팅·전원 손실**: 내용 `fsync` -> `os.replace` -> **디렉터리 `fsync`**
  (2026-08-23 보강). 종전에는 `os.replace` 만 해서 *원자적*이기만 하고
  *영속*이 아니었다 — 전원이 끊기면 이름 바꾸기는 반영됐는데 내용 블록이 없어
  파일이 비고 **번호가 1 로 되돌아갈** 수 있었다.
- **기록 실패는 노출을 막지 않는다** — 경고만 남긴다(번호가 되돌아갈 수 있다는
  사실을 알린다).

## 브랜치 (장수 브랜치)

작업은 **`ics-archon-v1.0-build`** 에 쌓는다(origin 에 푸시됨).
**main 합류는 `ics_archon` v0 완성 또는 v1 즈음 — 진행하면서 판단한다**
(목 2026-08-23). 브랜치 이름의 `v1.0` 은 최종 목표를 가리키는 것이고 합류
기준이 아니다 — 이름은 그대로 둔다. **아직은 합류하지 않는다.**

⚠️ **그래서 main 을 주기적으로 들여와야 한다.** 그냥 두면 완성 시점에 큰 충돌
하나를 맞는다. 특히 **raw spec 5장 검토**가 위험하다 — v1.4 는 1~4장만
반영했고 5장 이후는 팀 협의 후 다음 판이므로, 그 개정이 오면 견본 pair 와
`rawcards.py`(그리고 labtest 스크립트의 내장 `RAWCARDS`)를 **직접** 건드린다.
바이트 대사 시험이 그때 알람 역할을 한다 — `ics_archon/tests/test_fitswrite.py`
가 견본을 **패턴으로** 찾고 없으면 실패한다(skip 이 아니다). 합류 방식은
`--no-ff` 거품 머지.

## Archon 매뉴얼에서 확정한 사실 (`__ref_archon_control/`)

본편에서 다시 찾지 않도록 적어 둔다. 근거는 매뉴얼(2021-02-23)·ZTF Readout
Notes(2014-10-30), 쪽수는 매뉴얼 기준.

- **프로토콜** (p.45): `>xxCMD\n` → `<xxRESPONSE\n` / `?xx\n`(오류) /
  `<xx:`+1024B(이진, **개행 없음**). **인식 못 한 명령은 무응답**이고,
  참조번호는 호스트가 정하는 꼬리표라 값을 건너뛰어도 어긋나지 않는다.
- **STATUS** (p.47-49): `POWERGOOD` · `BACKPLANE_TEMP` · 모듈별 `MODm/TEMP` ·
  전원 레일 `P2V5_V/I` … `P35V_V/I`(그 위로 `N35V`/`P100V`/`N100V`/`USER`/
  `HEATER` 도 있다). **raw spec `Cn_VOLT` 의 자리 순서가 이 레일 순서**다
  (`P2V5 P5V P6V N6V P17V N17V P35V` — 7개만 쓴다).
- **SYSTEM** (p.46): `BACKPLANE_ID`(16진 16자리 고유 ID = 시리얼 대용) ·
  `BACKPLANE_TYPE`(1=X12, 2=X16) · `BACKPLANE_REV` · `BACKPLANE_VERSION` ·
  `MOD_PRESENT` · `MODn_TYPE`(2 = AD). **모델명 문자열 필드는 없다.**
- **FRAME** (p.49-50): `RBUF`/`WBUF` · `BUFnCOMPLETE`/`BASE`/`FRAME`/`WIDTH`/
  `HEIGHT`/`SAMPLE` · **`BUFnLINES`(라인 진행)** · `BUFnPIXELS`(픽셀 진행) ·
  `BUFnTIMESTAMP`. 진행률은 `BUF<WBUF>LINES / BUF<WBUF>HEIGHT` 다.
- **AD(비디오) 모듈은 중앙 4슬롯(5-8)에만** 꽂힌다 (p.20) — 모듈당 4채널(tap).
  그래서 `TEMP_SLOTS` 기본값이 `BACKPLANE_TEMP + MOD5~8/TEMP` 다.
  `ArchonController._log_module_map()` 이 기동에서 이 가정을 실물과 대조한다.
- **컨트롤러는 적용된 ACF 이름을 보고하지 않는다** (p.54) — `CTRLnCFG` 는
  호스트가 관리한다.
- **파라미터 갱신** (p.52): `LOADPARAMS`(전부) · `LOADPARAM p`(하나) ·
  `FASTLOADPARAM p d`(**즉시**, 설정 메모리는 그대로) · `PREPPARAM`/
  `FASTPREPPARAM`(EXTLOAD 에서 반영 — 다중 시스템 동기화용).
- **TIMER / BUFnTIMESTAMP 는 10 ns tick** (p.49-50). ⚠️ **`BUFnTIMESTAMP` 는
  프레임 기록(readout) 개시 시점**이라 `DATE-OBS`(노출 개시)로 **그대로 쓸 수
  없다.** 정밀 시각이 필요하면 `TIMER` ↔ 호스트 UT 상관 + 트리거 에지
  타임스탬프(`BUFnREATIMESTAMP` 등)를 봐야 한다.
- **BIGBUF=1 → 768 MB 버퍼 2개** (기본은 512 MB × 3). science 가 이 구성이고
  베이스 주소는 `BUFnBASE` 로 보고된다 — 그 값을 그대로 FETCH 에 쓴다.
- 셔터는 **Trigger Out** 이 INT 클럭을 따르게 해서 구동한다 (p.15) —
  `TRIGOUTFORCE=0` 이 그 모드, `1` 이면 `TRIGOUTLEVEL` 로 고정된다.
- **FETCH** (p.51): `FETCHxxxxxxxxyyyyyyyy` — 주소(16진 8자리)에서 1024B 블록
  `yyyyyyyy` 개. 요청 블록당 이진 응답 하나.

## 관련 문서

| 문서 | 위치 |
|---|---|
| 산출 규격 (raw FITS pair) | [`../raw_fits_spec/`](../raw_fits_spec/README.md) |
| 헤더 카드 템플릿 (공유 원천) | `../ics_sim/ics_sim/rawcards.py` |
| 백엔드 계약 | `../ics_sim/ics_sim/hardware/base.py` (D-012) |
| L0 MEF ICD · converter | `../mef_fits_spec/` · `../mef_converter/` |
| 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |

# SMC_CLAUDE.md

`ics_archon/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는
[../README.md](../README.md), 이 폴더의 구성·실행법은 [README.md](README.md).

## 이 폴더가 뭔가

**실기 ICS(`ics_archon`) 다.** `ics_sim`(시퀀서·명령 처리부·메시지 규약·헤더
층)을 **사본 없이 그대로** 쓰고, 그 아래 `DetectorBackend` 자리에 실제 Archon
컨트롤러 제어를 넣은 프로그램이다. 최종적으로 `ics` 로 개명해 운영 배포한다.

**실기 ICG(`icg_archon/`)도 이 폴더에 산다** (2026-08-31 v0 신설, 작업 D).
guide 유닛 취득(raw spec v1.9 9·10장 — 견본 바이트 재현 검증) + HK 취득·
로깅(1분 — Ctrl·진공·RTD·Radionode·AUX)이고, `ics_archon` 은 그 HK 스냅샷
(`[archon] hk_latest`)을 읽어 5.6절 HK 카드를 실값으로 채운다.  구조·판단·
PROVISIONAL 목록은 **[DevNote 9장](DevNote.md)**, 시험은
`tests/test_icg_*.py` 19개.  ⚠️ **실기 왕복 미검증** — `HEATER` 레일 필드명·
노출 pacing·Radionode Open API endpoint 가 첫 구동/콘솔 확인 대기다.

**노출 주기는 시퀀서가 만든다** (DevNote 9.12) — `Exposures=n+1` 을 한 번
걸고 `IntMS = EXPTIME − 하한` 으로 환산한다.  하한의 정본은 ini 가 아니라
**ACF 계산값**이다 (`icg_archon/acftiming.py`) — 현행 R2609(`NoIntMS=0`)에서
**1.375 s** 이고, 더 짧게 요청하면 거부가 아니라 하한으로 클램프한다.
⭐ **독출과 노출은 별개로 흐른다** — frame-transfer 라 image 는 독출 중에도
적분하고, 저장 프레임의 노출 개시는 *직전* 트랜스퍼다(규격 10.1-4·5).
독출 1.368 s 가 하한에 드는 것은 노출을 막아서가 아니라 **다음 트랜스퍼가
store 가 빌 때까지 못 와서**다 (DevNote 9.13).
**잠금은 주기보다 짧아야 한다** — `[icg] fetch_timeout = 1.0`(하한 1.375 s 아래, 8.3 MiB
≈ 0.08 s), 기동 검사가 어긋나면 알린다 (DevNote 10.6 · 9.15).  FETCH 가 독출을 멈춘다는
8.9 전제는 2026-09-02 실측으로 폐기 — **실효 하한 = 하한**.

제어 코드의 원형은 같은 폴더의 실험실 취득 스크립트
(`scr_labtest/archon_kmtnet_labtest_v1.3.bigbuf.py`, 1년 실사용으로 검증된 v1.0 계보)다.
그 스크립트는 **계속 남는다** — 실험실 단독 취득에 쓰는 별개 도구다.

## 먼저 읽을 것

| 문서 | 언제 |
|---|---|
| 이 문서 **"▶ 인수인계"** | ⭐⭐ **새 세션이면 여기부터.** 이 세션이 한 것 · 어디까지 됐나 · **밟기 쉬운 함정 넷** · 밟을 순서 |
| 이 문서 **"▶ 다음 세션 작업 지시"** | 그 바로 아래 — 일감 목록(작업 B~D) + 운영자 몫 + 착수 전 승인이 필요한 것 |
| 이 문서 **"참고 자료 재검토"** | ⭐ `__ref_archon_control/` 을 열기 전에. **옮기지 않은 것 셋의 근거**가 거기 있다 — 없으면 같은 것을 "빠졌다" 로 읽는다 |
| 이 문서 **"미해결 목록"** | F1~F12 · P1. 작업 2 의 일감이고, **앞 세션 워크플로 결과를 근거로 쓰지 말라는 경고**가 붙어 있다 |
| [README.md](README.md) | 폴더 구성 · 실행법 · 모듈 표 · 계약 어긋남 3건 · v0.0 에 없는 것 |
| ⭐ [`archon_lock_fetch_report.md`](archon_lock_fetch_report.md) | **실기 시험 보고서** — `LOCK`/`FETCH`/버퍼 운영 결론과 실측값, 재현 명령 (2026-09-01~02) |
| [INSTALL.md](INSTALL.md) | ⭐ **벤치에 설치할 때** — `~/AIC` 한 벌 세우기 · 기존 설치 이전 · 이상할 때 |
| `ics_archon/archon/controller.py` 머리말 | **"노출을 누가 재나"** — 이 층의 가장 중요한 판단 |
| `ics_archon/archon/backend.py` 머리말 | 계약과 실기의 어긋남 3건 · 동기 접근자가 스냅샷을 읽는 이유 |
| [README.md](README.md) "실기 첫 실행 절차" | ⭐ **실기를 붙이기 전에 이것부터.** `tools/probe_archon.py` 1~3단계 · 실험실 1유닛 설정 |
| [README_labtest.md](scr_labtest/README_labtest.md) | ⭐ **실험실 취득 스크립트에 관한 모든 것** (별개 도구) |
| ⭐ [`DevNote.md`](DevNote.md) | **이 폴더의 개발 노트** — 왜 그렇게 정했나(과정·판단·시사점). 2026-08-29 작업분부터 여기다.  ⭐ **10장 = 실기 시험 결론**(`LOCK`/`FETCH`/버퍼, 2026-09-01~02) |
| [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 11.22~11.30 | 그 이전의 `ics_archon` 이력 · `ics_sim` 층의 경위. 11.19~11.25 는 합본 판단 (11.25 = 커밋 + 병렬 독출 계획 검토). 9장은 하드웨어 확장점, 3장은 OBSAgent 규약 |
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
10-1. **사이트는 `[node] observatory` 한 줄이 정한다** (2026-08-24).
    `CTIO`/`SSO`/`SAAO`/`KASI` 넷뿐이고 **적은 값이 그대로 `OBSERVAT`
    카드**가 된다. 거기서 `telid`(사이트 코드)·`site`(`[site.*]` 절)가
    **유도**되어 파일명 `<SITE>` · 좌표 · `ORIGIN` · `INSTRUME` · **`TELESCOP`
    · `FPAID`**(raw spec 5.3.1절)가 함께 따라온다. **모르는 값은 기동을
    거부한다.**
    ⚠️ **D-017 (2026-08-25)**: 넷째 값이 `TESTBED`/`KMTT` 에서 **`KASI`/`KMTK`**
    로 바뀌었다. 벤치에 `observatory = TESTBED` 로 설치된 사본은 **기동이
    멈춘다** — `KASI` 로 고칠 것. `[site.testbed]` 절도 `[site.kasi]` 다.
    ⚠️ **망원경 번호와 `FPAID` 번호는 관측소 셋 모두 어긋난다**(CTIO 망원경
    `#1`·`FPA#2` 등). 오타로 보고 맞추면 검출기 귀속이 틀어진다.
    ⚠️ 종전의 **호스트 IP 판정(D-015)은 폐지**했다 — `siteid.py` 를 지웠으니
    되살리지 말 것. 두 위험(틀린 설정 vs 틀린 판정) 중 설정 쪽을 택한
    결과이고 경위는 DevNote 11.27 이다.
10-2. **컨트롤러 대수는 `[archon] n_controllers` 다** (1 또는 2, 그 밖은 기동
    거부). 1대일 때 어느 쪽인지는 `[controllers] ctrl1_id`(→MK)/`ctrl2_id`
    (→NT) **선언 여부**가 정하고 둘 다 진짜로 선언하면 거부한다. "없음" 은
    빈 값 · `NC` 가 같은 뜻이라 **한쪽만 적어도, 둘 다 적고 한쪽을
    `NC` 로 둬도 된다**(2대 ini 를 그대로 가져와 한 줄만 고치는 쓰임).
    **빠진 컨트롤러의 `CTRLnID/SN/CFG` 카드는 빼지 않고 값에 규격 5.0절
    sentinel `NC` 가 실린다** — 카드를 빼면 pair 두 파일의 카드 수가 달라져
    converter 와 견본 대사가 구조 변경으로 읽는다.
10-3. ⚠️ **색인이 태그를 정한다 — 이름 문자열은 절대 읽지 않는다**
    (운영자 확정 2026-08-25). 색인 1 = `ctrl1_*` 로 정의한 컨트롤러 =
    **무조건 `MK`**, 색인 2 = `ctrl2_*` = **무조건 `NT`** 다
    (`rawpair.CONTROLLERS` 순서).
    - **이름 끝 번호(`101`/`102`/`103`/`104`…)는 유닛마다 다르고 색인과 아무
      관계가 없다.** `KMTA-SCI-104` 가 색인 1 에 올 수 있다.
    - `ctrl1_id = NT` 라고 적어도 색인 1 이므로 `MK` 다.
    - **정본은 배선**(`[archon] ctrl_mk_host`/`ctrl_nt_host`)이지 이름이
      아니다. 실험실에서 유닛을 바꿔 꽂는 일이 실제로 있다.
    - 이름으로 유추하는 코드를 넣지 말 것 — 그러면 **운영이 이름 한 번 바꾸는
      것이 자료의 정체를 바꾼다.** `tests/test_controllers.py` 의
      `test_the_index_alone_decides_the_tag_never_the_string` 이 지킨다.
11. **전원을 켠 채로 끝내지 않는다.** `IcsArchon.stop()` 이 `backend.shutdown()`
    을 부른다 — 검출기 쪽 위험이다. 전원 차단 여부는 확인된 상태(`powered`)가
    아니라 **`power_attempted`** 로 판단한다: `POWERON` 응답을 잃으면 컨트롤러는
    켜졌는데 `powered` 는 `False` 로 남는다 (F4).
11-2. **종료는 저장 중인 프레임을 먼저 기다린다** (`[archon] shutdown_drain`,
    기본 30초). 전원 차단보다 **앞**이다 — 전원은 몇 초 더 켜져 있어도 되지만
    독출을 마친 프레임은 다시 못 찍는다 (F3).
12. **헤더용 스냅샷과 살아 있는 스냅샷을 섞지 않는다** (2026-08-28, 층 1·2).
    `ctrl.status` 는 **노출 개시에 언 것**이고 `controller_telemetry()` → 헤더
    전용이다. 감시가 갱신하는 것은 `ctrl.status_live` 다.
    - 감시가 `ctrl.status` 를 덮으면 헤더 스냅샷이 굳는 순간에 잡히는 것이
      **마지막 폴링 값**이 된다 — 독출이 모듈을 데우므로 값이 다르고, **폴링
      간격·락 경합에 따라 노출마다 달라져 비결정적**이 된다. `Cn_TEMP/VOLT/CURR`
      의 뜻("노출 개시 시점 값")이 조용히 바뀌는 부류다.
    - **감시는 `telemetry_enabled` 래치도 만지지 않는다** — 그것은 취득 경로의
      판단이다(F8). 감시는 `status_live_fails` 로 따로 센다.
    - **락을 새로 만들지 않는다** — `ArchonController._lock` 을 그대로 탄다.
      FETCH 가 락을 오래 쥐어 주기가 밀리는 것은 **오류가 아니라 `lag_ms` 에
      적을 사실**이고, **밀린 만큼 몰아서 뜨지 않는다.**
    - `tests/test_monitor.py` 의
      `test_monitor_never_touches_the_header_snapshot` 이 지킨다.

## 상태 (2026-08-28 — **층 1·2 구현 완료 + 참고 자료 재검토**, 벤치 연동 시험 대기)

### ✅ 참고 자료 재검토 — `__ref_archon_control/` 전수 (2026-08-28, 목 지시)

운영자가 실험실 실사용 스크립트 일곱과 ACF 원본 열하나를
`__ref_archon_control/` 에 반입했고, **본편에 옮길 것이 있나**를 전수로 봤다.

**계보가 셋이라는 것이 이 폴더의 핵심이다** — 셋이 같은 프로토콜 코드에서
갈라져 나왔고, 갈린 자리가 곧 판단이 있었던 자리다:

| 계보 | 파일 | 하는 일 | 본편과의 관계 |
|---|---|---|---|
| **labtest** | `archon_kmtnet_labtest_v1.0.{big,small}buf.py` | 실험실 취득 (1년 실사용) | ⭐ **본편 제어 층의 원형** |
| **modtm** | `modtm_{sci,gui}_{imgacq,powon}_v0.3….py` × 6 | 모듈 온도 감시 + 전원 관리 + 주기 취득 | 감시 층의 선례 |
| **tvm** | `archon_kmtnet_guide_tvm_v0.{8,9}….py` · `tvm_gui_goff_v0.7….py` | 진공·RTD·모듈 온도 감시 (guide) | **층 3 = `icg_archon` 소관** |

⚠️ `modtm_*` 여섯은 **유닛 설정만 다른 사본**이다 (101/102, sci/gui,
imgacq/powon).  `powon` 판은 `imgacq` 판에서 `Exposure()` 호출만 주석 처리한
것이고, 실질은 **두 갈래(sci·gui)뿐**이다 — 여섯을 다 읽을 필요는 없다.

#### ⭐ 옮긴 것 하나 — `POWERON` 뒤 `POWER=4` 확인

**계보가 여기서 갈린다.**  labtest v1.0/v1.3 은 `POWERON` 응답만 보고 12초를
세는데, `modtm_*` 는 `STATUS` 를 되물어 `POWER==4` 를 확인한 뒤에야 진행한다
(0.2초 × 40).  본편은 labtest 를 원형으로 삼았으므로 **확인이 없었다** —
그런데 `parse.POWER_STATES` 의 주석이 이미 *"`POWERON` 이 성공 응답을 줬다는
것과 전원이 실제로 올라왔다는 것은 다르다"* 고 적어 두고 있었다.  아는 것을
안 쓰고 있었던 셈이고, 확인이 없으면 전원이 안 올라온 채로 노출이 걸려 밖에서는
**"취득 실패" 로만** 보인다 (F2 가 막으려던 바로 그 모양).

`controller._await_power()` 로 넣었고 **판단 셋이 붙어 있다**:

1. **`poweron_wait` 를 줄이지 않는다.**  그 12초는 전원 램프가 아니라 **CCD
   flush** 를 기다리는 것이라(labtest 24 × 0.5), `POWER=4` 를 봤다고 일찍
   빠져나오면 첫 프레임이 flush 가 덜 된 상태로 나간다.  **확인은 그 대기
   안에서** 하고, 4 를 보면 되묻기만 멈춘다 (왕복 1~3회).
2. **`telemetry=false` 면 안 건다** — 규약 4 가 "왕복을 labtest v1.0 계보와
   똑같이 둔다" 이고 확인 질의도 왕복이다.
3. **`_check_health()` 를 부르지 않는다** — 램프 도중의 `POWER=3`(Intermediate,
   일부 모듈만 올라왔다)은 **정상 경과**인데 건강 판정에 넣으면 켤 때마다
   "컨트롤러 상태 이상" 이 뜬다.  스냅샷(`status`/`status_live`)도 안 덮는다 —
   저 둘은 헤더와 감시의 것이고 여기 값은 지나가는 상태다.
4. **막지는 않는다** — `POWER` 는 아직 실기 미검증(PROVISIONAL)이라 오독 하나로
   관측을 세우는 쪽이 더 나쁘다.  ERROR 한 줄로 크게 남긴다.
   ⚠️ modtm 은 여기서 **스크립트를 종료**한다(`return -6`).  실험실 도구라
   그래도 되지만 본편은 다르다 — 이 차이는 의도한 것이다.

#### 옮기지 않은 것 셋 (근거를 남긴다 — 다시 검토하지 말 것)

| 무엇 | 왜 안 옮겼나 |
|---|---|
| **`POWER!=4` 를 보면 유닛을 재초기화** (modtm 주 루프: ACF 재업로드 → `APPLYALL` → `POWERON`) | 감시 태스크가 관측 도중에 `APPLYALL` 을 내면 **진행 중인 노출·독출을 통째로 날린다.**  감시는 기록기이고 취득 경로의 판단을 뒤집지 않는다(규칙 2).  실험실 무인 방치용 회복 동작이다 |
| **주기 취득 루프** (`INTERVAL_EXP` 로 60초마다 한 장) | soak 시험 도구의 성질이다.  본편의 취득 계기는 OBSAgent 명령이고, 그 자리에 자체 트리거를 두면 규약 3(OBSAgent 규약)과 겹친다 |
| **변화 문턱 + SMS 통보** (`TH_TM` 0.5℃ · `TH_VC` 0.002 · `TH_TR` 0.2, Twilio) | 통보 계통을 본편이 갖지 않는다(운영자 미지시).  기록에 전 표본이 남으므로 문턱은 **읽는 쪽에서** 걸면 된다 |

그 밖에 **명령 집합은 이미 전량 덮고 있다** — 참고 스크립트가 쓰는 것
(`CLEARCONFIG`·`WCONFIG`·`APPLYALL`·`APPLYSYSTEM`·`LOADPARAMS`·`LOCKn`·
`FRAME`·`STATUS`·`POWERON`·`FETCH`)에 본편이 `SYSTEM`·`RCONFIG`·`TIMER`·
`POWEROFF` 를 더 쓴다.  재접속 사다리(`SWSET_ACFRETRY`/`CONNECTRETRY`)도
`acf_retry`·`connect_retry` 로 이미 있다.

#### 새로 확정한 사실 셋 (ACF `[SYSTEM]` 전수 대조)

1. ⭐ **guide 자리 표 = `BACKPLANE_TEMP` + MOD3·4·5·6·7·9·10 = 8자리.**
   미해결 **`OI-19`("guide 8자리 자리 표")의 답이 실물로 나왔다** —
   `acf/KMTK_GUI_162_STA0201_R2609.acf` 의 `MODn_TYPE` 과
   `modtm_gui_imgacq_v0.3….py` 가 훑는 슬롯이 **정확히 같다.**
   형 번호는 3·4 = `1`(Driver), 5·6 = `2`(AD), 7·10 = `11`(HeaterX),
   9 = `8`(HVXBias).  ✅ **규격 수록 완료** — raw spec **v1.9 가 10.4절에
   수록하며 OI-19 를 종결**했다 (2026-08-30, 첫 guide 구동 때 STATUS
   재확인만 남는다).
2. ⭐ **science 자리 표가 독립으로 확인됐다.**  `rawhdr.TEMP_MODS`(백플레인 +
   MOD1·2·3·4·5·8·9·10·11)와 실기 science ACF 다섯의 장착 슬롯, 그리고
   `modtm_sci_*.py`(2026-05, 규격과 무관하게 쓰인 실사용본)가 `STATUS` 에서
   읽는 자리가 **셋 다 같다.**  규격 5.6.1절 자리 표의 근거가 하나 늘었다.
3. **`MOD9` 형이 유닛마다 다르다** — KMTC/KMTS 는 `18`(HVYBias), KASI 벤치기
   `KMTK_SCI_113` 은 `8`(HVXBias).  둘 다 `MODULE_TYPES` 에 있어 배너는
   정상이고, 자리 표 판정(`field_order_problems()`)은 형이 아니라 **장착
   여부**만 보므로 영향이 없다.

셋 다 시험으로 못박았다 — `tests/test_monitor.py` 의
`test_the_science_slot_table_matches_the_real_acfs` ·
`test_the_guide_unit_has_a_different_slot_table_which_is_still_open`.

#### 층 3 자료는 `icg_archon` 몫 그대로다

`tvm_*` 셋(진공 `DEWPRES` · `HeaterX` RTD 계통)은 **`ics_archon` 소관이 아니다**
(운영자 2026-08-27).  해독 규칙은 아래 "층 3" 세 절에 이미 다 있고, 이번에 들어온
`tvm_gui_goff_v0.7….py`(STA0291, `_goff_` ACF)는 **진공 게이지를 끄고 기동하는
판**이라는 것 하나가 새롭다 — `icg_archon` 이 게이지 전원 대기(12초)를 건너뛰는
경로를 가질 수 있다는 뜻이다.  ⚠️ **다시 조사하지 말 것.**

### ✅ 층 1·2 감시·기록 구현 (2026-08-28) — 작업 A 완료

설계(2026-08-27)를 그대로 코드로 옮겼다.  **설계에서 바뀐 것은 없고**, 설계가
요구했지만 목록에 없던 것 둘을 더했다(아래 "설계에서 더한 것 둘").

| 자리 | 무엇 |
|---|---|
| `archon/monitor.py` (신설) | `TelemetryLog`(날짜별 CSV·고정 열) · `TelemetryMonitor`(주기 태스크) |
| `archon/controller.py` | `status_live` + `status_live_at` + `status_live_fails` · `refresh_status_live()` · `timer()` · `diagnostic_snapshot()` |
| `archon/parse.py` | `status_valid`/`status_count`/`log_count` · `RAIL_LIMITS`·`rail_problems()` · `bias_channels()`/`bias_readings()` · `telemetry_of(honour_valid=)` |
| `archon/backend.py` | D5 -- `synched` 가 `status_live` -> `status` -> 링크 상태 순으로 답한다 |
| `app.py` | `_start_monitors()`/`_stop_monitors()` -- `IcsSim.spawn()` 을 쓴다(**`ics_sim` 무수정**) |
| `config.py` | `monitor` · `monitor_interval` · `monitor_log` · `frame_dump` · `[archon.rails]` |
| `tools/probe_archon.py` | 1단계에 `VALID`/`COUNT`/`LOG` · 레일 범위 · **바이어스 채널 표** |
| `tests/test_monitor.py` (신설) | 30항목 -- 규칙 넷 · D4 · D5 · 파일 가르기 · **`app.py` 배선 왕복** · **실기 ACF 정합** |
| `tests/fake_archon.py` | **`FULL_STATUS`** 신설 -- 매뉴얼 p.47 건강 필드를 다 내는 응답 (+`count_step`) |
| `tests/test_probe.py` | +1 -- P-g·P-h·P-i 의 **확인 쪽 경로** |
| `tests/test_controllers.py` | +5 -- **저장 자리 선검사**(labtest v1.1.3) · **비ASCII ini 값** |

**규칙 넷은 시험이 지킨다** — `test_monitor_never_touches_the_header_snapshot`
(헤더용 `status` 와 `telemetry_enabled` 불가침) ·
`test_live_refresh_does_not_flip_the_acquisition_latch`(F8) ·
`test_log_splits_when_the_column_set_changes`(열 구성 변경) ·
`test_monitor_writes_fixed_columns_with_units`(`expstatus` 열 · 단위).

#### 설계에서 더한 것 둘 (판단 근거를 남긴다)

1. **`event` 열** — 설계가 "시작·종료·재연결을 한 줄씩 남긴다" 를 요구하는데,
   그 줄을 값 없는 행으로 적으면 **`valid=0` 표본과 구별되지 않는다.**  값은
   `start`/`stop`/`offline`/`poll_failed`/`resumed` 다.
2. **`lag_ms` 열** — 규칙 1 이 "밀린 시간을 로그에 적고 넘어간다" 를 요구한다.
   `age_ms`(값의 나이)와 **다른 것**이다: 폴링이 성공하면 `age_ms` 는 왕복
   시간이지만 `lag_ms` 는 FETCH 락에 밀린 정도다.

#### ⭐ 거동이 하나 바뀌었다 — **기동에서 접속하고, 그 뒤에 감시를 시작한다**

**접속자는 컨트롤러당 하나다** (운영자 확정 2026-08-28) — science 는
`ics_archon`, guide 는 `icg_archon` 이 맡고 **한 컨트롤러에 여러 노드가 붙는
구성은 두지 않는다.**  그래서 접속을 여는 자리를 `IcsArchon.start()` 의
`_connect_controllers()` 로 못박았다.

⚠️ **처음 구현했을 때는 감시 태스크가 첫 폴링에서 자기가 접속을 열었다** —
D5("링크가 올라온 순간부터 답한다")를 만족시키려다 **접속이 감시의 부수효과**가
된 것이다.  운영자가 순서를 바로잡았다: **접속이 먼저, 감시가 그 뒤.**  종전
(첫 노출의 `prepare()`)도, 감시 부수효과도 둘 다 "접속이 언제 열리나" 를 코드
흐름에서 읽기 어렵게 만든다.

| | |
|---|---|
| 접속 시점 | `IcsArchon.start()` — **`monitor` 설정과 무관** |
| 실패하면 | 기동을 막지 않는다.  감시가 주기마다 재시도(감시를 껐으면 `prepare()`) |
| 감시의 접속 코드 | 남아 있지만 **재수립**이다 — 처음 여는 자리가 아니다 |
| D5 | 그대로 성립한다 — 기동 직후부터 `status_live` 가 찬다 |

⚠️ **본편이 떠 있는 동안에는 STA GUI 도 `tools/probe_archon.py` 도 붙이지
않는다** — 설정으로 피하는 것이 아니라 **본편을 내리고 쓴다.**  Rev F
백플레인(KASI 벤치기 `KMTK_SCI_113` · guide)은 동시 접속이 하나뿐이고(p.15),
Rev H(4접속)에서도 규칙은 같다: **소유자가 하나면 "누가 이 값을 읽었나" 를
물을 일이 없다.**

#### ✅ D4 — `VALID=0` 이면 헤더가 `NC` 로 떨어진다

`telemetry_of()` 에 `honour_valid` 를 뒀다.  **헤더는 `True`(기본), 기록은
`False`** — 같은 응답이 헤더에서는 `NC`, 기록에서는 값으로 남는다("언제부터
이상했는지가 자료다").  `VALID` **필드가 없는 경우**는 `None` 으로 갈라
종전대로 값을 싣는다(F2).

⭐ **여기서 딸린 결함 하나를 더 잡았다** — `parse.health_problems()` 가
`VALID=0` 인 응답의 `POWER`/`POWERGOOD`/`OVERHEAT` 를 그대로 판정하고 있었다.
매뉴얼 p.47 이 "n = 1 if **remaining status fields** are valid" 라고 못박으므로
그 셋도 "나머지" 에 든다 — 무효 블록을 읽어 `POWER=0 Unknown` 같은 **가짜
경보**를 내면, 진짜 전원 이상이 왔을 때 사람이 이미 그것을 무시하도록 학습돼
있다.  이제 `VALID=0` 이면 그 한 줄만 내고 나머지 판정을 보류한다.

#### ✅ D5 — 첫 노출 전의 `-SYNCH` (G5)

`backend.status()` 의 `synched` 가 **살아 있는 스냅샷**을 본다.  아무것도 못
읽었으면 **링크 상태**로 답한다 — 거기서 `False` 를 내면 **모르는 것을 고장이라고
말하는 것**이 된다(`commands.py` 가 `ChannelState.synched` 기본값 `True` 를
덮으므로 침묵할 수도 없다).

⚠️ **`POWERGOOD` 은 이 물음에 정확히 답하지 못한다** — labtest 가 2026-08-27 에
종결한 증상이 그 증거다(아래 "labtest 에서 가져온 것").  Archon `STATUS` 에
동기 여부를 직접 말하는 필드는 **없다.**  그래서 이 플래그는 "전원 계통에
이상이 없다" 까지만 뜻하고, 진짜 동기 정지는 **프레임이 안 나오는 것**으로
드러난다.

### ✅ labtest 에서 가져온 것 (2026-08-28)

`scr_labtest` 가 v1.2 → **v1.3.4** 로 오면서 얻은 것을 본편에 옮겼다.  옮긴
것은 코드만이 아니라 **판정 지식**이다.

| labtest | ics_archon |
|---|---|
| `_frame_snapshot()` (v1.3.4) | `ArchonController.diagnostic_snapshot()` |
| `TIMER` 를 별도 명령으로 (`e5d72b5`) | `ArchonController.timer()` -- 값이 안 변하면 **타이밍 코어 정지** |
| `FRAME_WAIT_MAX` = `exptime + 20초` | ⭐ **`frame_timeout` 을 적분이 끝난 뒤부터 센다** (아래) |
| `FRAME_DUMP_ENABLE` 스위치 | `[archon] frame_dump` (초, 0 = 끔) |
| 시한 초과 시 진단은 **스위치와 무관하게 항상** | 같다 -- 그 증상은 간헐이라 평소 꺼 두면 정작 재발했을 때 증거가 없다 |
| **`Sync In` 종결** (2026-08-27) | 시한 초과 문구에 그 단서를 박았다 · D5 docstring · README 한 절 |

#### ⭐ 결함 -- 긴 DARK 이 헛 시한을 맞고 있었다

`wait_frame()` 의 상한이 `now + frame_timeout` 이었다.  셔터 노출은 시퀀서가
카운트다운을 다 하고 `readout()` 을 부르므로 들어올 때 적분이 이미 끝나 있지만,
**DARK/BIAS 는 `_readout_stream()` 이 `IntMS=<적분시간>` 으로 걸고 곧바로 여기로
들어온다** -- 기본 300초 상한에 **600초 dark 를 걸면 프레임이 정상으로 나오는
중에 `DMA WAIT TIMEOUT. EXPOSURES ABORTED.`** 가 났다.  labtest 는 처음부터
`exptime/1000 + FRAME_WAIT_MAX` 로 세고 있었다.

이제 `max(now, ticket.int_until) + frame_timeout` 이다.  회귀는
`test_frame_wait_deadline_starts_after_integration` -- **고치기 전 판에서 실패
하는 것을 확인하고 넣었다**(2026-08-24 교훈).

### ✅ 검토사항 A 에서 둘을 닫았다 (2026-08-28)

- **A2 — 안 쓰이는 `[readout]` 설정 경고.**  archon 은 진행률을 컨트롤러의
  `FRAME`(`BUFnLINES`/`BUFnHEIGHT`)에서 얻으므로 `pctread_start`/`step`/`tick`
  이 아예 안 쓰인다(`pctread_final` 만 쓴다).  **기본값과 다를 때만** 알린다 —
  "안 쓰인다" 를 늘 외치면 그것이 배경 소음이 되고 **사람이 실제로 고쳐 놓은
  것**을 알리려던 목적이 사라진다.
- **A6 — `ics_sim` 쪽 `hardware/archon.py` 스텁 문구.**  이미 `ics_archon` 을
  가리키고 있었지만 **없는 파일을 가리키는 경로가 하나 있었다**
  (`…labtest_v1.0.smallbuf.py`).  현행 이름으로 고치고 `sync_vendor.py` 를
  다시 돌렸다.  같은 부류로 `ics_archon/__init__.py` · `archon/__init__.py` 의
  "원형은 …v1.1.bigbuf.py" 도 고쳤다 — **v1.1 은 이제 없는 판이다.**

### ⭐ 저장 자리를 기동에서 본다 (labtest v1.1.3 역이식, 2026-08-28)

`config.validate()` 가 `[paths] data_dir` 을 기동에서 검사한다 — **자리가 있나 ·
쓸 수 있나 · pair 10장분 여유가 있나.**

**왜 기동인가** — 종전에는 저장 경로가 틀렸다는 것이 `write_frame()` 에서
드러났고, 그 시점에는 **이미 fetch 를 마친 뒤**라 다 읽어낸 노출을 잃는다.
labtest 는 v1.1.3 에서 같은 이유로 이 검사를 `POWERON` 앞으로 올려 뒀는데,
본편으로 옮길 때 그 교훈이 따라오지 않았다.

⚠️ **없다고 만들지 않는다.**  가장 흔한 원인이 "마운트가 안 붙었다" 인데, 그때
만들어 버리면 **마운트 지점을 가려** OS 디스크에 쌓이기 시작하고 나중에 마운트가
붙으면 그 자료가 통째로 안 보인다.  **막지도 않는다** — 관측소에서 마운트가 늦게
붙는 배치가 실재한다.  경고만 내고 기동 배너 옆에 크게 남긴다.

문턱을 절대값(GB)이 아니라 **pair 장수**(`STORAGE_MIN_PAIRS = 10`)로 둔 것은
기하가 바뀌면 뜻이 함께 따라가야 해서다 — 실물이면 pair 한 장이 688 MiB 라
10장은 약 6.7 GiB 다.

### 🔍 2차 검토에서 더 나온 것 (2026-08-28, 목 지시로 한 바퀴 더)

| # | 무엇 | 자리 |
|---|---|---|
| R1 | **접속 순서를 운영자가 바로잡았다** — 감시의 부수효과가 아니라 기동의 명시적 단계로 | `app._connect_controllers()` (위 절) |
| R2 | **종료가 감시를 곱게 안 세우고 있었다** — 표시만 하고 `sleep(0)` 이라, 폴링 중이던 감시가 `POWEROFF`·`close()` 와 겹쳐 **헛 `poll_failed`** 를 남겼다.  이제 상한(`status_timeout`+1초)을 두고 **기다린다**; 넘기면 취소하지만 `finally` 가 `stop` 행은 적는다 | `app._stop_monitors()` |
| R3 | **비ASCII ini 값 검사가 없었다** — labtest 3중 방어 중 **첫째**(기동 검사)만 안 따라왔다.  `fitswrite` 가 `?` 로 바꾸고 바이트 정렬도 지키지만, 그 경고는 카드마다·프레임마다 떠서 **밤새 돌리고 나서야** 헤더가 `????` 인 것을 본다 | `config._ascii_checks()` |
| R4 | `probe --acf` 를 줘도 **1단계의 바이어스 표가 그 ACF 를 못 봤다** — ini 만 봤다 | `tools/probe_archon.py` |
| R5 | **science ACF 다섯이 같은 16채널**임을 전수 확인 (종전에는 `KMTK_SCI_113` 하나만 근거였다).  ⚠️ **guide 는 18채널이고 라벨 넷에 `/` 가 있다** | 위 [층 2](#층-2--바이어스-측정값의-헤더-수록-계획-규격-개정-사안) 절 |
| R6 | **가짜 컨트롤러가 실기보다 빈약했다** — `VALID`/`COUNT`/`LOG`/`POWER`/`OVERHEAT` 를 아예 안 내서 기록의 그 열들이 **시험에서 늘 `NC`** 였다.  매뉴얼 p.47 은 실기가 다 보고한다고 한다 | `tests/fake_archon.FULL_STATUS` |

⚠️ **R6 에서 `DEFAULT_STATUS` 를 바꾸지 않았다.**  그 응답도 실재하는 경우
(그 필드를 보고하지 않는 펌웨어)이고 **F2 원칙이 지켜야 하는 쪽**이다 — 기본을
`FULL_STATUS` 로 바꾸면 "보고 없는 필드를 이상으로 세지 않는다" 를 검사하는
시험들이 통째로 무의미해진다.  둘을 나란히 두고 **양쪽 경로를 다 밟는다.**
`count_step` 은 `COUNT` 가 오르는/얼어붙는 두 경우를 만들어 기록의 `fresh` 열을
검사하게 한다.

⚠️ **R3 은 막지 않고 알리기만 한다.**  labtest 는 기동을 거부하지만 그쪽은
사람이 붙어 있는 실험실 스크립트이고, 여기는 OBSAgent 가 상대인 상주
프로그램이다 — **카드 한 장 때문에 관측을 통째로 못 하게 만드는 쪽이 더 나쁘다.**
검사 목록(`_HEADER_INI_FIELDS`)이 실제 필드와 어긋나면 시험이 잡는다.

### ⚠️ 벤더 매니페스트가 **어긋난 채로 커밋돼 있었다** (2026-08-28 발견)

`ics_archon/_vendor/MANIFEST.sha256` 가 `94c09ab`("sensors() 계약 -- ccdtemp
하나로 통합")부터 어긋나 있었다 — 어긋난 항목 넷(`hardware/archon.py` ·
`base.py` · `sim.py` · `rawhdr.py`)이 **그 커밋이 고친 파일 그대로**다.  내장본과
형제 원천은 서로 **바이트 동일**이었고 매니페스트만 낡았다 — `sync_vendor.py` 를
돌린 뒤에 그 파일들을 한 번 더 고친 것으로 보인다.

⚠️ **그래서 인수인계의 "`ics_archon` 171 통과" 는 사실이 아니었다** —
`test_vendor.py` 의 두 시험이 그때부터 실패하고 있었다(`repo_only` 도 아니다).
`python tools/sync_vendor.py` 로 매니페스트만 갱신해 닫았다.

**교훈**: 마지막에 고친 파일이 생성물의 입력이면 **생성기를 다시 돌린 뒤에**
시험을 돌려야 한다.  시험 결과를 인수인계에 적을 때는 **그 순간 실제로 돌린
출력**을 적을 것.

### ⚠️ 매뉴얼 p.41 표에 한 줄이 빠져 있었다 (2026-08-28 정정)

아래 "Archon 매뉴얼에서 확정한 사실" 의 전원 정상 범위 표에서 **`P17V`
(+16.4 … +17.5)** 가 빠져 있었다 — 옮겨 적을 때 8칸 표에 7개만 들어갔다.
`parse.RAIL_LIMITS` 는 매뉴얼 원문(p.41)에서 다시 확인해 **7레일 전부**를
담았고, `test_rail_limits_are_asymmetric` 이 `VOLT_RAILS` 와 집합이 같은지
검사한다.  표도 고쳤다.

### ⚠️ 시험이 헐거워서 깨진 것 하나 (2026-08-28)

저장 자리 검사를 넣자마자 `test_time_scale_other_than_one_is_flagged_for_archon`
이 깨졌다 — **제품 결함이 아니었다.**  그 시험이 `any('time_scale' in n …)` 로
찾는데 새 경고가 **경로를 그대로 싣고**, pytest 의 `tmp_path` 는 **시험 이름에서
만들어진다**(`…/test_time_scale_other_than_one0/rawdata`).  걸린 것은 경고 문구가
아니라 **폴더 이름**이었다.

⚠️ 같은 코드를 다른 이름의 시험으로 복제했더니 **재현되지 않았다** — "재현이 안
된다" 가 곧 "결함이 없다" 가 아니고, **시험 이름 자체가 입력**인 경우가 있다.

고친 것은 시험 쪽이다(`'[timing] time_scale'` 접두사째 찾는다).  경로는 진단에
꼭 필요하므로 무는 쪽이 시험이다.

### 시험

`ics_archon` **221 통과** · 배치본 `-m "not repo_only"` **185**.
(작업 A 에서 36 신설, 참고 자료 재검토에서 7 더 신설 — `POWERON` 확인 5 ·
자리 표 2 — 작업 E 에서 3 더 — `CTRLnCFG` 파생.)
⚠️ **`ics_sim` 스위트와 동시에 돌리지 말 것** — 부하로
`test_shutdown_waits_for_frames…` 가 간헐 실패한다(그 시험 자신의 주석에 이력이
있다).  직렬로 돌린다.

⚠️ **`test_backend.py` · `test_failures.py` 에서 감시를 꺼 뒀다** (`acfg.monitor
= False`).  ini 기본값이 켬이라 그대로 두면 그 시험들이 **사용자 홈의
`~/AIC/log/` 에 진짜 CSV 를 쌓고**, 기동 시점에 링크를 잡아 가짜 컨트롤러와
왕복을 다툰다.  감시 자체는 `test_monitor.py` 가 자기 임시 폴더에서 본다.


### ✅ raw spec v1.6 반영 (2026-08-26) — 정체성 카드가 바뀌었다

**`ORIGNAME` 을 폐지하고 `EXPID` 를 세웠다** (D-019, 운영자 확정).  규격·견본은
`main`(커밋 `6d9c137`), 코드는 이 브랜치 — D-017 때 세운 방침 그대로다.

    ORIGNAME= 'KMTA.20260821.123450.MK' / Original filename assigned by ICS counter
        ↓
    EXPID   = 'KMTA.20260821.123450'    / Exposure identifier assigned by ICS counter

**값에서 컨트롤러 태그가 빠진 것이 핵심**이다 — pair 양쪽이 같은 값을 싣고,
5.9절 "반드시 상이" 가 **7장 → 6장**이 되며 **짝을 잇는 단일 키**가 카드 추가
없이 생겼다(폐지된 `PAIRFILE` 의 역할).

| 무엇 | 전 → 후 | 어디 |
|---|---|---|
| **정체성 카드** | `ORIGNAME` → **`EXPID`** | `rawcards.CARDS`·`PAIR_DIFF`(7→6) · `rawhdr.exposure_header(expid=)` · 신설 `rawpair.exposure_id()` · `sequencer`(`name_stem()` 호출이 빠졌다) · **`archon/backend._frame_key()`** · labtest · 시험 |
| **`FILENAME` comment** | → `FITS file name as written to storage` | 종전 문구가 `ORIGNAME` 과 똑같이 "ICS 가 배정" 계열이라 둘의 차이가 안 드러났다 |
| **`Cn_*` 구분자** | 공백 → **`\|`** | `rawhdr._join_readings()` · labtest.  ⚠️ **슬래시는 배제했다** — FITS comment 구분자와 같은 글자라 인용부호를 먼저 찾지 않는 파서에서 값이 첫 슬래시에서 잘린다 |
| **`Cn_*` comment** | `Ctr-n` → **`Ctrl-n`** | `rawcards.CARDS` 6장 · labtest |
| **나열 결측 sentinel** | `-999.99` → **`NC`** | 정본은 `rawhdr.FIELD_NC`, `archon/parse.FIELD_NC` 가 그것을 받아 쓴다 · labtest `FIELD_NC`.  ⚠️ **단일 HK 카드(`CCDTEMP` 등)는 `-999.99` 그대로다.**  **전 자리 결측은 `NC` 한 토큰이 아니라 자리 수만큼** `NC|NC|…` 다 (아래 전수 검사) |
| **카드 폭 초과** | 값을 잘랐다 → **comment 를 먼저 자른다** | 규격 5.0절 신설.  **구현 자리가 셋이다** — `archon/fitswrite.card_image()` · astropy 경로(`fitsout._fit_to_card()`) · labtest `fits_card()`.  ⚠️ 1차 반영에서 첫째만 고쳐졌다 (아래 전수 검사) |
| **견본 노출 번호** | `012345`/`012340` → **`123456`/`123450`** | 견본 파일 이름도 함께 옮겨졌다 |

⚠️ **충돌 판별이 한 단계 늘었다** — `FILENAME != ORIGNAME`(직접 비교)에서
**`FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값 != `EXPID`** 로.

**코드에서 걸린 것 — 저장 경로가 끊겼다**

`archon/backend.py` 의 `_frame_key()` 가 **`ORIGNAME` 카드로 프레임 표를 집고
있었다**(blocker B).  카드가 사라지자 표를 못 찾아 **두 번째 노출이 저장되지
않았고**, `test_d016_collision_check_is_on_even_when_write_fits_is_false` 가
그것을 잡았다.  `EXPID` 로 바꾸니 파싱 규칙(`parts[1].parts[2]`)은 그대로
먹혔다 — `DETID` 필드가 없어져 오히려 pair 양쪽이 같은 키를 준다.

> **카드 하나를 갈면 그 카드를 읽는 코드가 어디인지부터 세야 한다.**
> 헤더 카드는 산출물이면서 동시에 **내부 배선**이기도 하다.

**시험이 더 잡은 것 둘**

- `test_raw_header.py` 의 **폐지 카드 목록에 `EXPID` 가 있었다** — D-013 이
  폐지했던 이름이라 당연히 거기 있었고, 되살렸으니 뺐다.  `EXPNUM` 은 여전히
  미도입이라 남긴다.
- **신설한 `test_labtest_spec_copy` 가 labtest 사본의 표류를 잡았다** — 브랜치를
  `reset --hard` 로 되돌리는 과정에서 `FILENAME` comment 한 줄이 딸려 돌아갔다.
  사람 눈으로는 못 봤을 자리다 (11.28 에서 신설한 지 하루 만에 값을 했다).

⚠️ **`EXPID` 는 2026-08-12 에 삭제됐던 이름을 되살린 것이다** (D-013).  되살린
근거와 당시 삭제 근거의 대조는 규격 2.3절 폐지 목록 아래 경고와 D-019 에 있다.
당시 실제 사고(실수 카드로 저장돼 zero-padding 파괴, DevNote 11.13.2)는 값이
`<SITE>` 접두로 시작해 숫자로 읽힐 여지가 없어 구조적으로 막힌다.

경위·판단은 **DevNote 11.29**.

### ✅ raw spec v1.6 **전수 검사** (2026-08-26) — 반영이 안 닿았던 자리 넷

위 반영을 끝낸 **뒤에** 영향 범위를 처음부터 다시 셌다.  시험 471개가 전부
초록인 상태였는데 **넷이 남아 있었다** — 넷 다 시험이 없는 자리였다.

| # | 무엇이 규격과 갈렸나 | 어디 |
|---|---|---|
| 1 | **5.0절 폭 초과 규범이 labtest 사본에만 안 갔다** — 값을 먼저 잘랐다.  실험실 자료만 `Cn_*` 의 **뒤 항목이 조용히 사라진다**(자리=항목이라 읽는 쪽은 모른다).  옆에서: 홑따옴표 겹쳐쓰기 방어도 labtest 에만 없었다 | `archon_kmtnet_labtest_v1.3.bigbuf.py::fits_card()` |
| 2 | **"자리는 비우지 않는다" 를 카드 전체가 빌 때 안 지켰다** — 전 자리 결측을 `'NC'` **한 토큰**으로 냈다.  5.6.1절이 **자리 수 자체를 모듈 구성 판별에 쓰라**고 하므로 읽는 쪽엔 "모듈 한 장짜리 컨트롤러" 로 보인다.  ⚠️ **`tools/probe_archon.py` 는 이미 그것을 빨강으로 짚고 있었다** — 산출부와 검사부가 다른 규격을 따랐다.  옆에서: 목록 안 `None` 이 `'None'` 으로 실렸다 | `rawhdr._join_readings()` · labtest `ctrl_telemetry_cards()` |
| 3 | **5.0절 둘째 문단이 `ics_sim` 쪽에 없었다** — 값만 68자를 넘으면 astropy 가 자르지 않고 `CONTINUE` 로 **카드를 늘린다**.  견본이 못박은 144 레코드·11,520B 가 깨지는데 경고가 없다.  `OBJECT`/`OBSERVER`/`PROJID` 는 **관측자가 치는 값**이라 길이가 바깥에서 온다 (실측: 100자 → 카드 3장) | `fitsout.apply_cards()` — 신설 `_fit_to_card()` |
| 4 | **동기화 도구가 초록이라 말한 뒤 시험이 빨갰다** — 동기화 경로가 매니페스트의 **존재 여부**만 봤다.  원천·내장본을 둘 다 손으로 같게 고치면(개정 반영에서 흔하다) 옮길 파일이 없어 그 경로를 타고, 매니페스트만 낡는다 | `tools/sync_vendor.py` |

> **규범 하나를 세우면 그 규범을 구현하는 자리를 세라.**  11.29 의 교훈("카드
> 하나를 갈면 그 카드를 **읽는** 코드를 세라")과 짝이다.  이 저장소에서 카드
> 이미지를 만드는 곳은 **셋**이다.

신설 시험 — labtest 동작 대조 3(`test_labtest_spec_copy`: 폭 규범 · 홑따옴표 ·
자리 채움) · 매니페스트 회귀 1(`test_vendor`) · 5.0절 4 + 5.6.1절 2(`ics_sim`).
문서·주석 표류(상이 7장 · 견본 이름 `012345` · 값 카드 135 · 판 표기 · "공백
구분" · 시험 개수)도 함께 걷었다 — 목록은 **DevNote 11.30**.

### ✅ raw spec v1.5 반영 (2026-08-26) — `main` 머지 + 전 계층 정합

**5장 검토 라운드가 내려왔다.**  `main` 이 raw spec v1.5 를 발행하고 구판(IP
판별) `ics_sim` 에 먼저 반영했으며(`13e02b2`), 이 브랜치가 `main` 을 **머지해서**
`observatory` 판별 구조 위에서 완결했다.  `13e02b2` 커밋 메시지가 "머지 충돌
해소는 **`main` 값을 정본으로**" 라고 지시했고 그대로 했다 — 다만 **값만**
정본이고 구조는 이 브랜치 것을 지켰다 (아래 "머지에서 내린 판단" 참조).

⚠️ **벤치에 이미 설치된 사본은 `ics_archon.ini` 를 고쳐야 기동한다** —
`[node] observatory = TESTBED` 는 이제 **모르는 값이라 기동을 거부**한다.
`KASI` 로 바꾸고 `[site.testbed]` 절도 `[site.kasi]` 로 고칠 것.

| 무엇 | 전 → 후 | 어디 |
|---|---|---|
| **D-017 사이트 코드** | `KMTT`/`TESTBED` → **`KMTK`/`KASI`** | `rawpair`(`OBSERVAT`·`SITE_OF_OBSERVATORY`·`SITE_SECTION`·`ORIGIN_OF`·관측일 보정) · `config`(`_SITE_TELID`·`NodeCfg` 기본값) · `state.site_code` · `app` 경고 · 두 ini · labtest `SITE_CODE` · `probe_archon` |
| **상수 개명** | `rawpair.TESTBED_SITE` → **`KASI_SITE`** | 옛 이름은 없다 — `AttributeError` 로 드러난다 |
| **D-017 항목 6 (5.3.1절)** | `TELESCOP`·`FPAID` 를 **사이트가 정한다** | `rawhdr.VERIFIED_SITES` 에 네 사이트 `telescop`+`fpaid`, 신설 `rawhdr.fpaid_of()`.  **모듈 상수 `FPAID='FPA#1'` 은 없앴다** — `[camera] fpaid` 가 있으면 그쪽이 이긴다 |
| **D-018 번호 공간** | `099999` 상한 → **`000000`–`999999`** | `rawpair.NUM_SPACE = 1_000_000` 하나.  `EXPNUM <n>` 입구 검사·되감음·충돌 루프 상한이 전부 그 상수를 본다 |
| **HK 4장 폐지** | `AIR_IN`·`AIR_OUT`·`GLYC_IN`·`GLYC_OUT` | `rawhdr.DEWAR_CARDS` 10 → **6** · `rawcards.CARDS` · labtest 템플릿+값.  견본 값 카드 **135 → 131** |
| **`CHMAP_*` 토큰** | 3자 `M16` → **4자 `MD16`** | `rawhdr.CHMAP` · `check_geometry()` 불변식(4자·가운데 글자 규칙) · 신설 `rawhdr.chmap_section()` · `rawcards` 폭 31→39 · comment `CCD output ch,`→`CCD out ch,` · labtest |
| **견본 comment 오타 2건** | `Telesope`→`Telescope` · `Acutator`→`Actuator` | `rawcards.CARDS` · labtest 템플릿 |
| **5.6.1절 신설 (`Cn_*` 자리 순서)** | `Cn_TEMP` science **5자리 → 10자리** | `rawhdr.TEMP_MODS`(정본 신설) + `TEMP_MOD_LABELS` · `parse.TEMP_MODS` 가 그것을 참조 · labtest 사본 · `fake_archon` · probe.  **아래 "재검토에서 나온 것" 참조** |

### 🔍 재검토에서 나온 것 (2026-08-26, 목 지시로 한 바퀴 더)

1차 반영을 마친 뒤 v1.5 변경 이력 12항목을 코드와 하나씩 대조했다.  **셋이
더 나왔다.**

**① `Cn_TEMP` 가 자리 수부터 틀렸다 (5.6.1절).**  코드는 `BACKPLANE_TEMP` +
`MOD5`~`MOD8` **5자리**였는데 규격 5.6.1절은 science **10자리**를 확정했고,
**견본 pair 의 `C1_TEMP` 도 처음부터 10개**였다 — 잠정안이 견본과 갈려
있었던 것이다.  `parse.TEMP_MODS` 의 주석이 "모듈 나열 순서의 정본 명세는
규격 수록 예정 … 확정되면 이 목록을 그것으로 교체한다" 고 남겨 둔 자리이고,
v1.5 가 바로 그 수록이다.

- 정본을 `rawhdr.TEMP_MODS` 에 세우고(`VOLT_RAILS` 와 같은 자리) `parse` 는
  그것을 참조한다 — **사본을 늘리지 않는다.**
- **자리 = 항목**이라 순서가 하나만 밀려도 소비자는 다른 모듈의 온도를 그
  모듈 값으로 읽는다.  값이 그럴듯해서 아무 경고도 안 뜬다.
- `Mod6`·`Mod7`·`Mod12` 는 **자리를 차지하지 않는다.**  가짜 컨트롤러가
  일부러 Mod6·Mod7 을 보고하게 두고 **카드에서 배제되는 것**을 시험이 밟는다
  (`test_cn_temp_slot_order_follows_spec_5_6_1`).
- ⚠️ AD 모듈이 슬롯 5~8 이라는 **매뉴얼 근거와 자리 표는 다른 것**이다 --
  자리 표에 실리는 AD 는 `Mod5`·`Mod8` 둘뿐이다.  섞으면 자리 수가 조용히
  달라진다.  probe 1단계 문구도 그렇게 고쳤다.

**② 5.7.1절의 재질의 문턱을 밟는 시험이 하나도 없었다.**  `aux_requery_after_
shopen` 은 지연이자 **재질의가 걸리는 노출 문턱**인데(그 두 번째 뜻이 v1.5 에서
처음 명시됐다), 3.0→1.0 으로 내려도 아무 시험도 반응하지 않았다.
`ics_sim/tests/test_qdate_order.py`(8항목)를 세웠다 — 문턱 경계(`<=` 포함) ·
`0` 이하 끄기 · 기본값 1.0 · **TC 무응답 폴백의 `UDATE` ≤ `QDATE`**(ICS 가 두
시각을 직접 찍는 유일한 자리).  3.0 으로 되돌려 실제로 실패하는 것을 확인했다.

**③ `INSTALL.md` 와 코드가 서로 다른 값을 말하고 있었다.**  설치 문서는
`[node] observatory` 를 **`KASI`** 로 두라고 적혀 있었는데 코드는 `TESTBED` 만
받았다 — **문서대로 설치하면 기동이 거부되는** 상태였다.  D-017 이 문서 쪽으로
정리되면서 저절로 닫혔다.  (거꾸로 말하면, 벤치에 이미 선 사본은 `TESTBED` 로
적혀 있을 것이므로 **고쳐야 한다.**)

**④ `ics_archon.ini` 만 재질의 지연이 `3.0` 으로 남아 있었다.**  `ics_sim.ini`
는 1.0 으로 고쳤는데 **실기가 읽는 ini** 를 빠뜨렸다 — 코드 기본값만 맞고
운영값은 틀린, 가장 조용한 부류다.  고치고 **배포 ini 두 벌을 규격값에 묶는
시험**을 양쪽에 붙였다(`test_qdate_order.py` · `test_labtest_spec_copy.py`).

> 이 넷을 찾은 방법은 같다 — **v1.5 변경 이력 12항목을 코드와 한 줄씩 대조**했다.
> "시험이 초록" 은 "그 자리가 시험됐다" 가 아니라는 이 폴더의 반복 교훈이
> 그대로 또 나왔다 (DevNote 11.20 · 11.25 · 11.26 계열).

**probe 1단계가 이제 자리 표를 눈으로 대조하게 해 준다.**  `Cn_TEMP` 는 값에
이름표가 없어서(자리 = 항목) 실기에서 "이 자리가 정말 그 모듈인가" 를 확인할
길이 없었다.  `tools/probe_archon.py` 가 `rawhdr.TEMP_MOD_LABELS` 로 자리별
이름표를 찍고, 자리 수가 규격과 다르면 **문제로 낸다**:

    자리 표 (규격 5.6.1절) -- 값이 그 모듈의 것인지 대조할 것:
       1  Backplane      31.5
       2  Mod1:LVDS      30.1
       ...
      10  Mod11:Driver   34.3

함께 처리한 것 — `ICS_DEPLOYMENT_CHECKLIST.md` 가 **폐지된 D-015 와 지워진
`siteid.py`** 를 안내하고 있었다(브랜치가 3bf2d73 에서 판별을 바꾸며 놓친
자리다).  현행 판별로 고치고 `FPAID` 확인 항목을 넣었다.  `ACT-009` 도 같은
파일을 가리키고 있어 "ICS 결합은 없어졌고 망 문서 필요는 남는다" 로 정정했다.
기동 배너에는 **`FPAID` 를 세웠다** — 사이트를 바꾸면 조용히 따라오는 값이라
배너의 목적("자료 한 장 찍기 전에 사람 눈에 띄게") 그대로다.
| **셔터 재질의** | `3.0` → **`1.0`** 초 | `config.TimingCfg` · `ics_sim.ini`.  ⚠️ **재질의가 걸리는 노출 문턱이기도 하다** — 이제 **1초 이하** 노출이 개시 직전 값을 그대로 쓴다 (5.7.1절 (c) 표) |
| **기계 정본 판올림** | 채널맵 v1.0 → **v1.1** | `IMGSEC` 의 `B-BOT`→`D-BOT` 정정 포함.  자리도 `__reference/` 에서 sub레포 루트로 옮겨졌다 |

**직접 고친 결함 하나 — labtest 헤더 조립이 통째로 거부됐다.**  값 카드가 4장
줄자 헤더가 140 레코드 = 11,200B 가 되는데 **2880 의 배수가 아니다.**
`archon/fitswrite.py::header_bytes` 는 `END` 뒤를 공백으로 채우고 있었지만
(주석이 "카드 수가 바뀌는 개정이 오면 여기서 조용히 흡수돼야 한다" 고 예고해
두었다) **labtest 의 `build_header` 는 패딩 없이 정렬 단정만 두고 있었다.**
같은 패딩을 넣어 견본과 같은 144 레코드 · 11,520B 가 되게 했다.

**신설 시험 — 규격 사본 셋 중 하나가 무방비였다.**
`tests/test_labtest_spec_copy.py`(4항목).  `ics_sim/rawcards.py` 와 `_vendor`
는 `sync_vendor`+`test_vendor` 가 지키는데 **labtest 내장 `RAWCARDS` 만 아무도
안 봤다** — 갈라져도 `ics_archon` 시험은 전부 초록이고, 실험실에서 찍은 파일만
카드 구성이 달라져 converter 가 구조 변경으로 읽는다.  이제 `RAWCARDS`·`CHMAP`
·`SITE_INFO`·번호 공간 넷을 원천과 대조한다 (표류를 주입해 실제로 잡히는 것을
확인했다).

**머지에서 내린 판단 (값은 `main`, 구조는 브랜치)**

| 자리 | 무엇을 택했나 | 왜 |
|---|---|---|
| `ics_sim/siteid.py` · `tests/test_site_id.py` | **삭제 유지** (`main` 은 고쳤다) | D-015 IP 판정은 이 브랜치가 폐지했다 (목 확정 2026-08-24, DevNote 11.27).  되살리면 그 결정이 뒤집힌다 |
| 노출 번호 공간 상수 | `rawpair.NUM_SPACE` **하나만** (`main` 의 `state.EXPNUM_SPACE` 는 채택 안 함) | 같은 뜻의 상수를 둘로 두면 다음 개정에서 한쪽만 바뀐다.  값(1000000)은 `main` 정본 그대로 |
| 절 참조 | 브랜치 쪽 (`raw spec 5.5절` 등) | `main` 주석의 `규격 5.1절` 은 구판(v1.2) 번호다 |
| `FPAID` | **브랜치에서 새로 구현** | `main` 은 5.3.1절을 문서에만 반영하고 `FPAID='FPA#1'` 상수를 그대로 뒀다 — 사이트를 바꿔도 FPA 번호가 안 따라오는 상태였다 |

**검증** — `ics_sim` **323 통과** · `ics_archon` **148 통과** · 벤더 표류
**없음** · labtest 하네스 **32항목 0실패**.
(1차 반영 시점 313/143 → 재검토 라운드에서 9+3 항목이 늘었다.)  그리고 **견본 v1.5 pair 를 바이트
단위로 재현**한다(MK·NT, 불일치 0) — 헤더 층이 규격과 같다는 가장 강한 신호다.
⚠️ 종전 인수인계의 "`pytest` 가 없어 시험을 못 돌렸다"(`main` 쪽 기록)는 이제
해소됐다 — 이 환경에 `pytest` 를 넣고 전부 돌렸다.

### ⏳ 지금 진행 중인 것 — 관측 스크립트 첫 구동

목이 벤치(`kmtnet-sso`)에서 `aic_integration_test_v0.0.osc` 를 **한 번에**
돌리고 있다 (`+opause` 를 로컬에서 주석 처리했다 — 그래서 **목의 사본은
`ostart` 줄번호가 저장소 판과 다르다**).

**결과가 오면 할 일**: `obs.event.*.log` · `isis.*.log` · `ls -l ~/AIC/data` 를
받아 아래를 판정한다.

  * 노출마다 `Acquisition Complete.` 4회 · `Wrote` 4회 · `EXPSTATUS=IDLE` 1회
  * 시간 창 3종(1.8 / 0.9 / 25초) — `ics_sim/obsagent_model.py` 의
    `CamStatusReplay` 에 발신 스트림을 먹여 `check_windows()` 로 잰다
  * CamStatus 전이 — DARK/BIAS 가 `INT_2` 를 건너뛰는지, 역행 0인지
  * **P2 겹침 구간**에서 파일 일련번호가 밀리지 않았는지
  * 헤더 — `EXPTIME`·`IMAGETYP`·`FILTER`·`OBJECT`·`RA/DEC` 가 줄마다 맞는지

⚠️ **아직 확인 안 된 것**: `FILTER` 값(`n`/`i`/`r`/`v`)이 벤치의 필터 설정과
맞는지.  파서가 `sys.filterlabel[]` 과 대조해서 안 맞으면 **그 줄만** "unrecognized
filter name" 경고와 함께 skip 된다 (`loadconfig.c:1377`).

### 완료 — `ics_archon` v0.0.0 + 작업 1·2 + 사이트/대수 개정

브랜치 `ics-archon-v1.0-build`, **`main` 미합류.**  origin 동기.

    c205571  osc 관측줄에 PROJID 열 추가 -- 26줄이 통째로 버려지고 있었다
    0c77058  labtest v1.1.3 -- 취득 전에 저장 자리를 검사한다   (작성=목)
    3bf2d73  사이트 판별을 OBSERVATORY 로 · 컨트롤러 대수를 ini 로
    b9132b1  관측 시험 스크립트 신설 -- 하룻밤을 압축한 연동 시험
    7d80a68  벤치 설치 문서 + build-local.sh 를 bin/ 설치까지
    bed73e7  설치 루트 AICS -> AIC 개명 + 경로가 재빌드에 묶여 있던 것 해소
    6cfc3c0  ics_archon: 두 컨트롤러 병렬 독출 + v0 미해결 F1~F12

별도 브랜치 **`archongui-analysis`**(`2239583`, `main` 기반) — `ArchonGUI/
QT_INSTALL.md` 뿐이다.  STA 가 준 GUI 의 Qt5 빌드 절차이고 `ics_archon` 과
무관해 따로 관리한다 (작성=목).

검증: `ics_sim` **323 통과** · `ics_archon` **148 통과** · 벤더 표류 **없음**
· labtest 하네스 **32항목**(읽기전용 1건은 POSIX 전용, 윈도우는 SKIP).
(2026-08-26 v1.5 반영 뒤 수치다 — 종전 306/139/31.)

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
- **독립 배포**: `_vendor/ics_sim/`(**23모듈** — `siteid.py` 폐지로 24 에서 줄었다)
  + `MANIFEST.sha256`.
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
컨트롤러 값이 실린다, `[node] observatory` 한 줄이 파일명 `<SITE>`·`OBSERVAT`·좌표·
`ORIGIN` 을 **함께** 끌고 간다(한쪽만 따라오면 converter 의 유일한 하드 실패),
KASI(실험실)는 좌표가 sentinel.

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
  되돌렸다** (`[archon] lock_buffer`) — 아래 검토사항 A5 가 그 이유였고, ✅ **2026-09-01
  실기 종결** — 15/15 반영·대가 0·지킬 구간 실재, `true` 확정 (DevNote 10.6).

## 관측 스크립트 (`.osc`) — 알고 시작할 것

`aic_integration_test_v0.0.osc` 를 다룰 때 **소스로 확인한 사실**이다
(`OBSAgent/OBSAgent.latest/KMTObs/`).  추측하지 말고 여기를 볼 것.

| | |
|---|---|
| **관측줄 형식** | `PROJID LABEL RA DEC COPT IMGTYP OBJECT FILTER EXPTIME UTOBS UTTOL [VelRA VelDEC]` — **맨 앞이 `PROJID`** (`loadconfig.c:1148`) |
| ⚠️ **저장소 견본이 낡았다** | `bak.sample.osc`(2017)·`functest.osc`(2020)는 `ProjID` 열이 생기기 전(v0.6.4) 판이라 **10열**이다.  그대로 베끼면 `0 of N exposures imported` 가 난다 (2026-08-25 실측).  **정본은 `osc/osc.dflat/` 의 최신 판** |
| 줄이 버려지는 조건 | ①열 부족(`rtn<9`) ②필터 이름을 `sys.filterlabel[]` 에서 못 찾음 ③`ExpTime` 이 `[0.05, 18000]` 밖 (BIAS 는 값을 안 본다) — 셋 다 **파싱 오류가 아니라 skip** 이라 "import 실패" 로만 보인다 |
| 콘솔 명령 | `osc`/`oscript`/`oscr` 로드 · **`ostart <줄번호>`(번호 필수)** · `oresume`/`or`/`resume` 재개 · `ostat`/`os` · `ostop` · `oabort` |
| 줄번호 세는 법 | **주석·빈줄을 뺀 순번**.  `+` 지시어와 관측줄을 함께 센다 (운영자 확인) |
| 경로 | `'/'`·`'.'`·`'~'` 로 시작하지 않으면 `DEFAULT_OSCDIR`(`/home/dts/osc/`, 컴파일 상수)이 앞에 붙는다 → **절대경로로 줄 것** |
| 두는 자리 | **`~/AIC/osc/`** (`Config/`·`Logs/`·`data/` 와 같은 층).  저장소에서 복사해 쓴다 |
| `tstow` vs `stow` | **같은 명령**이다 (`commands.h` cmdtab, 도움말 `commands.c:1550`) |

**저장소에 사본이 두 벌이다** — `ics_sim/osc/` 와 `ics_archon/osc/`.  같은
스크립트로 시뮬과 실기를 나란히 시험하려는 것이고, `ics_archon/tests/
test_osc_script.py`(9항목)가 **바이트 동일성 · `ostart` 표 정합 · 11열 ·
`ExpTime` 범위 · `+msgout` ASCII** 를 지킨다.  **한쪽만 고치면 실패한다.**

## 텔레메트리 감시 · 기록 (설계 2026-08-27 · **층 1·2 구현 완료 2026-08-28**)

> ✅ **아래 설계는 그대로 구현됐다** — 코드는 `archon/monitor.py` ·
> `controller.status_live` · `parse` 의 감시 절, 시험은 `tests/test_monitor.py`
> 다.  반영 내역과 설계에서 더한 것 둘은 위 [층 1·2 감시·기록 구현](#-층-12-감시기록-구현-2026-08-28--작업-a-완료) 절.
> **이 절은 그 근거(왜 그렇게 정했나)를 담은 원문이므로 그대로 둔다.**
> 층 3 은 여전히 `icg_archon` 소관이다.


원형은 `__ref_archon_control/archon_kmtnet_guide_tvm_v0.9.kasi.STA0201_IP162.py`
(가이드 유닛 TVM 감시 스크립트)와 그 실측 로그
`__ref_archon_control/tvm.gui.log.sample.txt`(658행, 2026-08-19~22)다.

⚠️ **그 스크립트를 "science 판으로 복제" 하는 것이 아니다.** 참고만 하고
science 컨트롤러 값을 읽어 **들고 있는** 것이 일이다 (운영자 2026-08-27).
복제가 성립하지 않는 이유는 아래 "왜 science 에는 RTD·진공이 없나".

### 층 나누기 — 같은 `STATUS` 응답이지만 성격이 다르다

| 층 | 무엇 | 규격 접촉 |
|---|---|---|
| **1** | science 컨트롤러 **주기 감시·기록** — 온도 10 + 레일 7×2 = **24개 값** | 없음 (`parse.telemetry_of()` 를 그대로 쓴다) |
| **2** | 같은 응답에서 **바이어스 16채널 V/I** · `VALID`/`COUNT`/`LOG` 도 기록 | 지금은 **로그만**. 헤더 수록은 **계획됨** — 규격 개정 필요 (운영자 2026-08-27) |
| **3** | `sensors()` 의 `ICG RTD` 계통 — ⚠️ **`ics_archon` 소관이 아니다.** `icg_archon` 이 읽어 넘긴다 (운영자 2026-08-27) | 규격 5.6절 HK 카드 |

**층 1·2 가 `ics_archon` 의 일감이고 층 3 은 `icg_archon` 을 기다린다.**  그때까지
`backend.sensors()` 는 **빈 dict 를 그대로 유지**하고 HK 카드 7장은 sentinel 로
실린다.  아래 "층 3" 절은 **`icg_archon` 을 만들 때 쓸 해독 규칙**이다 — 이 세션에
실측으로 확정해 뒀으니 그때 다시 조사하지 말 것.

⚠️ **가이드 TVM 스크립트는 실험실 Test Dewar 감시용이고 ICS 와 함께 쓰이지
않는다** (운영자 2026-08-27).  그래서 "ics_archon 이 그 로그 파일을 임시로
읽는다" 안(③)은 **채택되지 않았다** — 파일 계층의 낡은 값 함정을 피할 수 있게
됐고, 대신 `icg_archon` 이 나오기까지 HK 는 sentinel 로 남는다.
⚠️ 같은 이유로 **지금 실측값은 시험 듀어의 것**이다 — 운용 듀어 값이 아니다.

**층 1 은 새 판독기가 아니라 기록기다.** `parse.telemetry_of()` 가 이미 정확히
그 24개를 `{'temp':[10], 'volt':[7], 'curr':[7]}` 로 돌려준다 — 파싱 코드도,
규격 협의도, converter 영향도 없다. 그리고 감시와 FITS 헤더가 **같은 함수**를
읽으므로 둘이 어긋날 수 없다(기계 사본을 넷째로 만들지 않는다).

원장 v1.14:466 이 `CCDTEMP` 대표 센서를 두고 **"센서 이상은 취득 SW 로그가
담는다"** 고 약속해 뒀는데 **그 로그가 지금 없다.** 층 1 이 그 약속의 이행물이다.

### ⚠️ 반드시 지킬 것 넷 (운영자 승인 2026-08-27)

1. **락을 새로 만들지 않는다** — `ArchonController._lock` 을 그대로 탄다
   (`refresh_status()` 를 부르면 자동으로 직렬화된다). 단 **FETCH 가 락을
   344 MiB 동안 쥔다**(`fetch_timeout=0` 이면 크기에서 유도, 최대 344초 — ⚠️ 그러면
   잠금이 주기를 넘어 기동 검사가 알린다, DevNote 10.6) —
   감시 주기가 그만큼 밀린다. **"간격을 못 맞췄다" 를 오류로 보지 말고 밀린
   시간을 로그에 적고 넘어간다. 밀린 만큼 몰아서 뜨는 것은 절대 금지.**
2. **`telemetry_enabled` 래치를 감시가 되돌리지 않는다** — 그 플래그는 "한 번
   실패하면 이 실행 동안 안 묻는다" 다(F8). 감시가 재시도하며 그것을 다시 켜면
   **취득 경로의 판단이 감시 쪽 사정으로 뒤집힌다.** 감시는 자기 실패 카운터를
   따로 들고 백오프로 재시도하며, 성공해도 헤더용 래치는 만지지 않는다.
3. **파일은 컨트롤러당 하나 + 날짜별로 가른다** (`telemetry.<태그>.<YYYYMMDD>.csv`).
   **위치는 `~/AIC/log/`** 다 (운영자 확정 2026-08-27) — `[paths] data_dir` 밑에
   두면 자료와 함께 굴러가 아카이브 정책에 걸린다.
   **기록 간격은 수십 초 ~ 수 분**이다 (운영자 2026-08-27) — 기본값 20초로 두고
   ini 로 늘릴 수 있게 한다.  이 간격이라 FETCH 락(science ≤ 10초 · guide ≤ 1초 --
   `fetch_timeout`, DevNote 10.6)에 밀려 표본
   한두 개를 건너뛰는 것은 **문제로 보지 않는다** (위 규칙 1).
   한 파일에 무한 append 하면 밤새 돌린 것이 하나로 뭉친다. 그리고 **헤더 줄을
   반드시 넣는다** — 원형 `tvm.gui.log` 는 열 이름이 없어 스크립트 소스를 봐야
   몇 번째가 무엇인지 알 수 있고, **자리 수가 바뀌면 과거 파일이 조용히
   오독된다**. 열 이름은 `rawhdr.TEMP_MOD_LABELS` 를 쓴다(규격 5.6.1 표 그 자체).
4. **`EXPSTATUS` 를 한 열로 같이 적는다** — 나중에 "이 온도가 독출 중 값인지
   대기 중 값인지" 를 반드시 묻게 되고, **사후에 시각으로 맞출 수는 없다.**

### ⚠️ 함정: 헤더용 스냅샷과 살아 있는 스냅샷을 갈라야 한다

지금 `Cn_TEMP/VOLT/CURR` 의 뜻은 **"노출 개시 시점 값"** 이다 — `initialize()`
에서 `refresh_status()` 로 뜨고, 헤더 스냅샷은 `ics_sim/sequencer.py` 의 `snap`
에서 **독출이 끝난 뒤** 굳히는데 그 사이 아무도 갱신하지 않으므로 결과적으로 개시
시점 값이 실린다 (`backend.py` 머리말 근거: labtest 도 노출 앞에서 떴다).

배경 감시가 `ctrl.status` 를 계속 덮으면 굳히는 순간에 잡히는 것은 **마지막 폴링
값**이다. 독출 자체가 모듈을 데우므로 값이 다르고, 게다가 **폴링 간격·락 경합에
따라 노출마다 달라져 비결정적이 된다.** 카드의 뜻이 조용히 바뀌는 부류다.

| 자리 | 갱신 | 소비자 |
|---|---|---|
| `ctrl.status` | 노출 개시에 **언 것** (지금 그대로) | `controller_telemetry()` → **헤더 전용** |
| `ctrl.status_live` + `status_live_at` | 감시가 계속 갱신 | 기록 · 콘솔 · ICS `STATUS` 응답 · 건강검사 |

`controller_telemetry()` 는 계속 언 쪽을 읽어야 한다 — 여기 손대면 규격의 뜻이
바뀐다.

### 기록 형태

```
telemetry.<태그>.<YYYYMMDD>.csv        # 주기 스냅샷, 고정 열
  utc, age_ms, expstatus,
  valid, count, fresh, log_n,          # fresh = count 가 직전 행과 달라졌나
  power, powergood, overheat,
  T1..T10                              # 규격 5.6.1 자리, [deg C]
  V1..V7 [V], I1..I7 [A]               # P2V5..P35V  (단위 A)
  rail_flag                            # p.41 power good 범위 이탈
  B_<label>_V [V], B_<label>_I [mA] x 16   # 바이어스 (단위 mA — 섞지 말 것)

ctrllog.<태그>.<YYYYMMDD>.log          # FETCHLOG 로 빼낸 항목 + 빼낸 시각
```

경로는 `~/AIC/log/` 다.

**✅ 7레일이 맞다는 것이 실측으로 확정됐다** (운영자 2026-08-27) — science
컨트롤러에서 `N35V` · `P100V` · `N100V` · `USER` 가 **전부 0 V / 0 A** 로 나온다.
안 쓰이는 레일이고, 매뉴얼 p.42-43 과 정합한다(표준 전원이 만들지 않는다).
`HEATER` 도 science 에서는 무의미하다.

- **`USER` 를 나중에 쓰게 되더라도 `Cn_VOLT` 에 넣지 않는다** — 그때는 우리가
  다른 의도로 전압 출력이 필요해서 쓰는 것이므로 **별도로 관리한다**
  (운영자 2026-08-27).
- ⚠️ **`HEATER`(+28 V)는 guide 에서 실재하고 기록할 계획이다** (HeaterX 두 장).
  guide 감시 열에는 `HEATER_V/I` 를 넣는다 — science 열과 **다른 표**가 된다.

- **시작·종료·재연결을 한 줄씩 남긴다.** 원형 로그에 60초 넘는 공백이 셋
  (178초 · 6.2시간 · 3.0일) 있는데 **스크립트가 죽은 것인지 사람이 껐다 켠
  것인지 로그만으로는 알 수 없다.** `age_ms`/`fresh` 도 같은 목적이다.
- `valid=0` 행도 **버리지 않고 기록**한다 — 언제부터 이상했는지가 자료다.
- `ctrllog` 에는 **우리가 빼낸 시각도 함께** 적는다 (컨트롤러 항목에 자체 시각이
  붙는지 미확인 — 아래 P-d).

### `FETCHLOG` 는 **쓰지 않는다** (운영자 확정 2026-08-27) — `LOG=n` 만 기록

**결정**: 드레인은 감시에 넣지 않는다.  `STATUS` 의 **`LOG=n` 한 열만** 남긴다.

**근거** — `FETCHLOG` 를 밀었던 가장 강한 논거가 "`POWER=3`(Intermediate)은
**주어가 없는 증상**이다(어느 모듈·채널인지 STATUS 에 필드가 없다)" 였는데,
**바이어스 16채널 V/I 를 기록하기로 정해지면서 그 자리가 메워졌다** -- 어느
채널이 안 올라왔는지 로그가 직접 말한다.  남은 것은 "눈 감은 창"(APPLYALL ·
POWERON 대기 · FETCH 락)이었는데, **기록 간격이 수십 초 ~ 수 분**이므로
(운영자 2026-08-27) 그 창은 표본 한두 개를 건너뛰는 것에 그친다.

**`LOG=n` 은 남긴다** -- 이미 파싱하는 응답 안에 있어 왕복이 0 이고, 드레인을
안 해도 신호가 된다: **값이 오르면 컨트롤러가 무언가 기록하고 있다**는 뜻이고,
우리 로그와 나란히 놓으면 "우리가 못 본 사건이 있었나" 를 알 수 있다.

**승격 기준** (probe 1단계에서 사람이 한 번 찍어 보고 판단) --
① 항목이 **모듈·채널 수준의 정체**를 담으면(예 `MOD9 HVHC4 failed to reach
setpoint`) 드레인을 넣을 값이 있다 ② `config applied` · `frame complete` 수준
이면 **쓰지 않는다** (우리 로그가 이미 더 잘 담는다).

안 쓰기로 한 이유가 된 위험 셋 -- 매뉴얼이 한 줄뿐이고 깊이·넘침 정책·응답
형식이 전부 미기재다:

1. **파괴적 읽기 가능성** — "oldest 를 fetch" 는 큐에서 빼는 것으로 읽힌다.
   그러면 STA GUI 를 같이 붙여둔 사람은 그 항목을 못 본다. 벤치(Rev F)는 접속이
   하나라 무의미하고 **관측소(Rev H, 4접속)에서는 실질 문제**다.
2. **인식 못 한 명령은 무응답**(p.45) — 펌웨어 판에 없으면 **영구 정지**다.
   반드시 상한 + 첫 실패에 이 실행 동안 끄는 래치.
3. **드레인 상한** — `while LOG>0: FETCHLOG` 는 락을 오래 쥔다. 한 주기에
   **최대 20개**만 빼고 남으면 다음 주기로. 그리고 `LOG` 값 자체를 열로 남긴다
   — **상한 근처에 계속 붙어 있으면 그것이 "놓치고 있다" 는 신호**다(깊이를
   모르는 채로도 읽을 수 있다).

### 층 2 — 바이어스 측정값의 헤더 수록 (계획, 규격 개정 사안)

운영자가 **헤더에도 적절히 넣을 계획**이라고 확정했다(2026-08-27).  단
**일단은 로그부터** 만든다.  넣을 때 미리 알아야 할 것:

- **카드 하나에 안 들어간다.**  16채널 × (V, I) = 32개 값이고 `.3f`(예
  `-17.067`, 7자)로 `|` 구분하면 `32×7 + 31 = 255자` 다.  견본의 `C1_TEMP` 는
  값 폭 **51자**이고 FITS 문자열 값의 물리 상한은 68자다(comment 자리를 빼면
  실질 ~60자).  **8채널이 한 카드의 한계**다 (`8×7 + 7 = 63자`).
- 그래서 갈래가 둘이다:
  - **8개씩 균등 분할** — `Cn_BV1`/`Cn_BV2`/`Cn_BI1`/`Cn_BI2` → 컨트롤러당 4장,
    **pair 8장**.  자리 표가 단순하지만 모듈 경계를 넘어 섞인다.
  - **모듈·계열별 분할** — `MOD4/LVHC` 6 · `MOD9/HVHC` 6 · `MOD9/HVLC` 4 세
    묶음 × (V, I) → 컨트롤러당 6장, **pair 12장**.  자리가 하드웨어를 따라가
    읽는 쪽이 해석하기 쉽다.
- ⚠️ **자리 = 항목 규범을 따르면 채널 구성이 규격에 박힌다** (5.6.1절).  ACF 를
  바꿔 라벨 붙은 채널이 늘거나 줄면 자리 수가 달라지고, 그것은 `CAMVER`(HW) ·
  `CTRLnCFG`(설정) 범프로 드러나야 한다(4.3절 포장 규범).
- ✅ **science ACF 다섯이 같은 16채널·같은 라벨을 선언한다** (2026-08-28 실측 --
  CTIO 2 · SAAO 1 · KASI 2).  종전에 "16채널은 `KMTK_SCI_113` 기준" 이라고만
  적어 뒀던 것을 전수로 확인했다 — **유닛마다 열이 갈리지 않는다.**
  `tests/test_monitor.py::test_every_science_acf_declares_the_same_16_bias_channels`
  가 지킨다.
- ⚠️ **guide 는 18채널이고 라벨 넷에 `/` 가 있다** (`VRDSR/L`·`VRDNR/L`·
  `VRDER/L`·`VRDWR/L`, 2026-08-28 실측).  CSV 열 이름으로는 무해하지만 **D3
  에서 반드시 걸리는 자리**다 — 5.6.1절이 "슬래시를 쓰지 말 것" 을 못박는다
  (FITS comment 구분자와 같은 글자라 값이 첫 슬래시에서 잘린다).  값이 아니라
  라벨이라 지금은 안 걸리지만, **라벨을 카드 이름·comment 로 옮기는 설계를
  고르면 그때 걸린다.**
- ⚠️ **`POWER=4` 가 아닐 때의 값은 ~0 V 다**(p.77).  헤더에 실을 때 그 상태를
  구분할 수단이 없으면 `BIAS`/전원 꺼진 프레임의 카드가 "전 채널 0 V" 로 남아
  고장처럼 보인다 — 로그의 `power` 열에 해당하는 것이 헤더에도 필요하다.

### 왜 science 에는 RTD·진공이 없나 (ACF 로 확정)

|  | MOD1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **science** | 10 LVDS | 1 Drv | 1 Drv | 9 LVXBias | **17 ADM** | 0 | 0 | **17 ADM** | 8 또는 **18** | 1 Drv | 1 Drv |
| **guide** | 0 | 0 | 1 Drv | 1 Drv | 2 AD | 2 AD | **11 HeaterX** | 0 | 8 HVXBias | **11 HeaterX** | 0 |

science ACF 5종에는 `SENSORxTYPE`/`SENSORxLABEL` 키가 **하나도 없고**
`VCPU_LINES=1`(빈 프로그램)이다. HeaterX 가 없으므로 `MODm/TEMPA/B/C` 도
`VCPU_OUTREGn` 도 나오지 않는다(p.48 "Heater(X) only" · "Modules with DIO").

**덤으로 자리 수가 규격과 맞는 것이 확인됐다** — science 장착 모듈은
1·2·3·4·5·8·9·10·11 = **10자리**(`rawhdr.TEMP_MODS` 와 일치), guide 는
3·4·5·6·7·9·10 = **8자리**(규격 **10.4절** — v1.9 에서 **OI-19 종결**). 실기
STATUS 대조는 여전히 남아 있지만 근거가 하나 늘었다.

### 층 3 (`icg_archon` 소관) — 가이드 유닛 HeaterX 가 `ICG RTD` 계통이다

가이드 ACF 의 센서 이름표가 규격 5.6절 HK 카드와 **일대일**이다. 즉
"C. 원천이 아예 없는 것" 에 적어둔 `ICG RTD` 계통의 원형이 이 스크립트다.

| STATUS 필드 | ACF 이름표 | raw 카드 | 지금 상태 |
|---|---|---|---|
| `MOD7/TEMPA` | `RTD4_Charcoal_TBC` | `CHARCOAL` | ⚠️ **미연결** |
| `MOD7/TEMPB` | `RTD1_PT30-1` | `PT30N1` | 정상 |
| `MOD7/TEMPC` | `RTD3_PT30-2_TBC` | `PT30N2` | ⚠️ **미연결** |
| `MOD10/TEMPA` | `RTD9_DMP` | `DMPTEMP` | 정상 |
| `MOD10/TEMPB` | `RTD8_CCD` | **`CCDTEMP`** | 정상 (⚠️ 하한 문제) |
| `MOD10/TEMPC` | `RTD5_WB` | `WALLBRD` | 정상 |
| `MOD10/VCPU_OUTREG0~9` | (MKS 356 게이지) | **`DEWPRES`** | 정상 |
| — | — | `HEBOX` | Radionode (별개 계통) |

**`sensors()` 가 채울 키는 7개로 확정됐다** (`ccdtemp` `dmptemp` `pt30n1`
`pt30n2` `charcoal` `wallbrd` `dewpres`). `air_*`/`glyc_*` 4장은 v1.5 에서
폐지, `hebox`/`fsatemp`/`fsahum` 은 Radionode. 즉 **가이드 HeaterX 6채널 + 진공이
규격이 요구하는 `ICG RTD` 전량**이고, 층 3 은 부분 구현이 아니라 **완결**이다.
(단 미연결 2채널 때문에 실값은 5장으로 시작한다.)

#### ✅ `ccdtemp1`/`ccdtemp2` 를 `ccdtemp` 하나로 합쳤다 (2026-08-27, 반영 완료)

운영자 확정: **CCD1/CCD2 를 구분하지 않고 CCD 대표 온도 하나만 읽는다.  `ccdtemp2`
관련 유산은 전부 없앤다.**  chip 귀속은 **정보가 없으므로 규정하지 않는다.**

⚠️ **이름 충돌이 하나 있었다** — 종전 계약이 `ccdtemp` 를 **"백엔드가 따로 줘도
무시하는" 키**로 명시했고(`base.py`), `test_raw_header.py` 가 `'ccdtemp': 0.0` 을
일부러 넘겨 무시되는지 검사했다.  그 규칙의 존재 이유가 "센서가 둘이니 두 번째
사실을 만들지 않기" 였으므로, **센서가 하나로 확정되면서 규칙 자체가 사라졌다** --
그래서 `ccdtemp` 를 대표 이름으로 승격하고 무시 규칙을 지웠다.

**"대체 금지" 원칙은 남겼다** (운영자 지시) -- 예시만 갱신했다.  없는
`ccdtemp2` 대신 **실제로 유혹이 되는 것**(`DMPTEMP` · `Cn_TEMP` 의 모듈 온도)을
경고 대상으로 적었다.

고친 자리 (`ccdtemp1` → `ccdtemp`, `ccdtemp2` 제거):

| 파일 | 무엇 |
|---|---|
| `ics_sim/ics_sim/hardware/base.py` | 계약 키 목록 + 대표 센서 문단 (무시 규칙 삭제) |
| `ics_sim/ics_sim/rawhdr.py` | `thermal_header` docstring + `s.get('ccdtemp')` (별칭 `ccdtmp1` 도 제거) |
| `ics_sim/ics_sim/hardware/sim.py` | 시뮬이 내는 키 둘 → 하나 |
| `ics_sim/ics_sim/hardware/archon.py` | 스텁 TODO 주석 |
| `ics_sim/tests/test_raw_draft.py` | 견본 재현 입력 키 |
| `ics_sim/tests/test_raw_header.py` | 두 시험 개작 — **옛 키를 아직 읽으면 실패**하는 회귀 추가 |
| `ics_archon/ics_archon/archon/backend.py` | `sensors()` docstring 인용 |
| `ics_archon/_vendor/ics_sim/` 4파일 | `tools/sync_vendor.py` 재실행 (생성물) |

**손대지 않은 것**: `ics_sim/DevNote.md` 의 `ccdtemp1` 언급은 **이력**이라 그대로
둔다.  `raw_fits_spec` 의 `CCDTEMP1`/`CCDTEMP2` **카드** 언급은 다른 것이다 --
그 둘은 애초에 도입 후보에서 제외 확정된 **FITS 카드 이름**이고, 여기서 없앤
것은 **백엔드 계약 키**다.

✅ **`air_*`/`glyc_*` 죽은 키도 없앴다** (운영자 지시 2026-08-27).  계약 키
목록에 넷이 남아 있고 `sim.py` 도 그것을 냈는데, **해당 카드 4장이 v1.5 에서
폐지**돼(`DEWAR_CARDS` 에 없다) 호출측이 값을 버리고 있었다 -- 계약에 남겨 두면
백엔드가 **아무도 읽지 않는 값을 읽으러 간다.**  이제 계약 키는 **아홉**이다
(`ccdtemp` `dewpres` `dmptemp` `pt30n1` `pt30n2` `charcoal` `wallbrd` /
`hebox` `fsatemp` `fsahum`).  고친 자리: `base.py` 계약 · `sim.py` 반환 ·
`archon.py` 스텁 주석 + `_vendor` 재생성.

⚠️ **대문자 카드 이름 언급은 그대로 뒀다** -- `rawhdr.py`(폐지 근거 주석) ·
labtest 5사본(개정 이력) · `test_raw_header.py`(**나오면 안 되는 카드** 목록)는
전부 "폐지됐다" 를 기록하는 자리다.  `mef_converter` 두 곳은 MEF 쪽이라 범위
밖이다(LEECU 소관, raw 가 공급을 끊었다는 것은 이미 C-항목으로 등재).

### 층 3 (`icg_archon` 소관) — 진공(`DEWPRES`) 해독 규칙

가이드 ACF `MOD10` 의 VCPU 프로그램이 정본이다 (p.90 포트 주소표와 대조):

```
LOAD r0, 0x0800 / OUTPUT r0, 11    ; UART 분주기 11 -> 115200/12 = 9600 baud
'#','0','5','R','D',13             ; MKS 356 에 "#05RD<CR>"
LOAD Port, RegPort (0x0200)        ; OUTREG0 부터
LOAD Count, 9   / SkipLoop         ; 앞 9글자 버림
LOAD Count, 10  / StoreLoop        ; <- 10글자를 OUTREG0..OUTREG9 에 한 칸당 한 글자
    IF C GOTO MainLoop             ;    글자가 모자라면 중도 포기
LOAD Port, 0x020F / ADD Alive,1    ; <- OUTREG15 = 성공 폴링 횟수
    OUTPUT Port, Alive
```

- `OUTREG0~9` = 응답 **10글자**의 ASCII 코드, `OUTREG10~14` 미사용,
  **`OUTREG15` = Alive 카운터**.
- ⚠️ **`Alive` 를 봐야 신선도를 안다.** 게이지 응답이 짧으면 StoreLoop 중간에서
  `IF C GOTO MainLoop` 로 빠져나가는데 그때 **`OUTREG0~9` 는 직전 값이 그대로
  남고 `Alive` 도 안 올라간다** — 옛 값이 새 값처럼 보인다(F8 과 같은 부류).
- **정상 판정은 "직전보다 증가" 하나뿐이다.** `Alive` 가 0 이거나 감소했으면
  **VCPU 재시작**(`APPLYALL`)이고, 두 번 연속 안 변했으면 게이지 이상 →
  둘 다 `DEWPRES` 는 sentinel `9.99e-9`.
- 원형 스크립트는 `OUTREG9` 를 종결 표시로 써서 **10번째 글자를 버린다**(9글자만
  이어붙인다). 실측에서는 응답이 항상 `x.xxe-04`(8자)라 **무해했다** — 658행
  전부 정상 파싱, sentinel 0건. 자릿수가 바뀌는 경우까지 무해한지는 STATUS 원문
  덤프로 확인할 일이고 **우선순위는 낮다.**
- `DEWPRES` 재포맷은 **하지 않는다.** `rawhdr.format_dewpres` 가 이미
  `6.93e-04` → `6.93e-4` 로 만들고(지수 앞 0 제거) 인정 범위
  `[1e-8, 1e+3]` 도 검사한다. `sensors()` 는 **원값을 넘기면 된다.**

### 층 3 (`icg_archon` 소관) — 실측 로그 판정 (`tvm.gui.log.sample.txt`, 658행)

**✅ 단위는 섭씨다. 매뉴얼 p.48 "in K" 는 오기.** 273.15 변환을 하면 안 된다.

```
260819 113602 … PT30-1 +20.8  DMP +20.3  CCD1 +21.1  WB +18.8  BP +33.8
260822 223514 … PT30-1 -29.5  DMP -31.8  CCD1 -27.7  WB  +7.8  BP +34.4
```

음수가 나오므로 켈빈일 수 없다. 보강 증거 — **미연결 채널이 정확히 `-273.2`**
를 낸다(= 0 K 를 섭씨로 옮긴 값). 펌웨어가 내부적으로 켈빈을 다루고 보고할 때
273.15 를 빼는 구조로 보이고, 매뉴얼은 그 내부 표현을 적은 듯하다.

**⚠️ 결측 판정은 값이 아니라 ACF 한계로 한다.** 미연결 채널이 `-273.2` 만
내는 것이 아니다 — `RTD3_PT30-2_TBC` 는 639행이 `-273.2` 인데 **19행이
`-196.9`~`-206.1`** 로 튄다. 그 값은 PT-30 cold-end 로서 **완전히 그럴듯해서**
값만으로는 가릴 수 없다. ACF 의 `SENSORx{LOWER,UPPER}LIMIT` 로 판정하면 노이즈
까지 잡힌다:

| 채널 | ACF 한계 | 실측 범위 | 판정 |
|---|---|---|---|
| MOD7A `RTD4_Charcoal_TBC` | −230 … 50 | −273.2 고정 (distinct 1) | 밖 → **미측정** |
| MOD7B `RTD1_PT30-1` | −180 … 50 | −29.5 … +20.8 | 안 (정상) |
| MOD7C `RTD3_PT30-2_TBC` | −180 … 50 | −273.2 / −196.9…−206.1 | **둘 다 밖** → 미측정 |
| MOD10A `RTD9_DMP` | −150 … 50 | −31.8 … +20.3 | 안 |
| MOD10B `RTD8_CCD` | **−30 … 60** | −27.7 … +21.1 | 안, **아슬아슬** |
| MOD10C `RTD5_WB` | −120 … 50 | +7.8 … +18.8 | 안 |

라벨의 `_TBC` 접미사가 실제로 "미연결" 을 뜻했다.

#### ✅ 원인 규명 + 수정 완료 — MOD10 센서 B/C 스왑에서 limit 이 안 따라갔다

**경위** (운영자 2026-08-27): MOD10 의 **센서 B/C 위치를 맞바꿨는데**(B←RTD8_CCD,
C←RTD5_WB) **그때 limit 설정을 안 옮겼다.**  그래서 CCD 채널이 벽면보드용
범위(−30 … +60/70)를, 벽면보드가 CCD 용 범위(−120 … +50)를 쓰고 있었다.

저장소 ACF 넷을 대조해 그 사건을 특정했다 — **스왑은 `_rtd9cal` 판을 만들 때
일어났다**:

| ACF | 센서 B | B limit | 센서 C | C limit |
|---|---|---|---|---|
| `for1110` (스왑 전) | `RTD5_WB_TBC` | −30.0 / 70.0 | `RTD8_CCD1_TBC` | −120 / 50.0 |
| `for1259` (스왑 전) | `RTD5_WB_TBC` | −30 / 60 | `RTD8_CCD1_TBC` | −120 / 50.0 |
| `for1110_rtd9cal` (스왑 후) | `RTD8_CCD1` | −30.0 / 70.0 ← 안 옮겨짐 | `RTD5_WB` | −120 / 50.0 |
| `for1259_rtd9cal` (스왑 후) | `RTD8_CCD1` | −30 / 60 ← 안 옮겨짐 | `RTD5_WB` | −120 / 50.0 |

**스왑 전 판에서는 limit 이 라벨과 맞아 있었다** — 즉 원래 값이 옳았고 스왑에서
라벨만 옮겨진 것이다.  같은 사건이 TVM 스크립트 **v0.8 → v0.9**(2026-08-14 →
08-15)의 라벨 뒤바뀜으로도 남아 있다.

**고친 것** (`_rtd9cal` 판 둘, 2026-08-27):

    MOD10\SENSORBLABEL      = RTD8_CCD1  ->  RTD8_CCD
    MOD10\SENSORBLOWERLIMIT = -30        ->  -120        (CCD)
    MOD10\SENSORBUPPERLIMIT = 60 / 70.0  ->  50.0
    MOD10\SENSORCLOWERLIMIT = -120       ->  -30         (WB)
    MOD10\SENSORCUPPERLIMIT = 50.0       ->  70.0

⚠️ **`for1259_rtd9cal` 의 WB 상한은 60 → 70.0 으로 올라갔다** — 순수 스왑이면
60 인데 운영자가 70 을 정본으로 확정했다(`for1110` 계열의 값).  실측 WB 범위가
**+7.8 … +18.8** 이라 어느 쪽이든 여유는 크다.

⚠️ **`_TBC` 판 둘(스왑 전)은 손대지 않았다** — 그 판에서는 limit 이 이미 라벨과
맞고, 고치면 옛 배치의 이력이 사라진다.  라벨의 `_TBC` 접미사도 그 판의 사실이다.

**판을 올렸다** — `R2601` → `R0827` (운영자 지시 2026-08-27), 그리고
**2026-08-28 에 guide 정본을 하나로 줄이며 `R2608` 로 다시 표기했다**:

    acf/KMTK_GUI_162_STA0201_R2609.acf                       ⭐ 현행 유일본
      = 구 kmtnet_guide_STA0201_162_R0827_for1259_rtd9cal.acf (바이트 동일)
    __ref_archon_control/acf/…                               (원본 보관 — 넷 다)
    acf/archive/…_R2601_…_rtd9cal.acf  × 2                   (정정 **전** 판)

⭐ **`R0827` 예외 조항이 없어졌다** — `MMDD` 라 `YYMM` 규칙에 어긋났고 숫자로
정렬하면 구판보다 앞에 왔는데(0827 < 2601), `R2608` 이 되면서 해소됐다.
파일명 규칙은 `acf/README.md` "판 표기" 절에 있다 (역할 토큰 `SCI`/`GUI`,
검출기조 `_MK`/`_NT` 는 science 에만).

⚠️ **저장소 사본을 고친 것이 실기에 반영되는 것은 아니다** — 운영자가 그 ACF 를
유닛에 올려야(`APPLYALL`) 적용된다.  **다음 감시 로그로 확인할 항목**이다:
CCD 채널이 −30 아래로 내려가도 값이 유지되는지(종전 설정이면 한계 밖).

⚠️ **`__ref_archon_control/` 실험실 스크립트의 `UNIT_ACF` 가 구 파일명을
가리킨다** — 그 폴더는 참고 원본 보관용이라 여기서 고치지 않는다.  운영자가
작업본을 새 이름으로 고쳐야 한다 (`archon_kmtnet_guide_tvm_v0.9….py` ·
`modtm_*.py` · `tvm_gui_goff_v0.7….py`).

⚠️ **개명이 시험을 하나 깼다** — `tests/test_monitor.py` 가 guide ACF 를
`kmtnet_guide_*.acf` 로 글롭해서 빈 목록이 됐다.  **내용으로 가르도록 고쳤다**
(`_repo_acfs()` 가 `BIGBUF` 로 science/guide 를 나눈다) — 이름은 규칙이
정비되면 또 바뀐다.

**폴링 간격**은 중앙값 22초(`INTERVAL_LOG` 20 + 취득 ~2초)다.

### 규격 쪽 후속 (다음 판올림 때)

#### ✅ `CCDTEMP` 에서 chip 귀속을 없앤다 (운영자 확정 2026-08-27) — **완료 (2026-08-30 조기 실행)**

**결정**: `CCDTEMP` 를 **특정 chip 으로 규정하지 않고 "CCD 대표 온도"** 로 한다.
카드 comment 의 `M` 도 없앤다.  **대표 센서가 어느 chip 근처인지는 정보가 지금
없다** — 그래서 있는 척하지 않는다.

**이행**: 운영자 지시(2026-08-30)로 **판올림을 기다리지 않고 조기 실행**됐다 —
견본 3장(G·MK·NT) 제자리 개정 + 규격 5.6절·원장·통합 문구, 그리고 머지
`bed2f20` 에서 브랜치 기계 사본 3곳(`rawcards.py`·`_vendor`·labtest 5본,
labtest 는 v1.3.5 판올림 동반)까지 반영 완료.  채택 문안은 아래 후보 중
**셋째**(`CCD temperature [deg C]` — mef_converter 와 같은 문안)였다.

**따라오는 것**: `OI-18`("대표 센서 M 이 NT 파일에서도 그대로인지 확인")은
**종결이 아니라 폐기**다 — 물음의 전제(chip 귀속이 있다)가 사라진다.  pair 두
파일에 같은 값이 실리는 것은 5.9절 "반드시 동일" 로 자동 충족되고, 견본도 이미
두 파일이 `'-101.23'` 으로 같다.

**comment 문안 후보** — 카드 여유는 **47자**다
(`CCDTEMP ` 8 + `= ` 2 + `'...18자...'` 20 + ` / ` 3 = 33, 80−33):

    Representative CCD temperature [deg C]     37자   (당시 클루디 추천)
    CCD representative temperature [deg C]     37자
    CCD temperature [deg C]                    23자   <- ✅ 채택 (2026-08-30)

당시 추천은 첫째였으나(이웃 카드가 전부 `<대상> temperature [deg C]` 꼴),
운영자는 **셋째**를 골랐다 — mef_converter 문안과의 일치를 우선한 것.

**⚠️ 영향 전수** (2026-08-27 실측).  `CARRY_KEYS` 는 **이름만** 요구하므로
소비자 계약은 안 깨지고, `mef_converter` 두 곳은 이미 `M` 이 없다.

| 갈래 | 자리 |
|---|---|
| **문자열 정본** | `ics_sim/ics_sim/rawcards.py` |
| **문서 인용** | `ics_sim/ics_sim/rawhdr.py`(docstring) |
| **생성물** (`tools/sync_vendor.py` 재실행) | `ics_archon/_vendor/ics_sim/rawcards.py` · `rawhdr.py` |
| **labtest 내장 사본 5** | `ics_archon/scr_labtest/…v1.3.{bigbuf,smallbuf}.py` (+ KMTC-102 · KMTC-113 · KMTS-101) |
| ⭐ **견본 pair 바이트 정본 4** | `raw_fits_spec/KMTA.20260821.123456.{MK,NT}.fits.header.v1.0{,_REFTEXT}.txt` |
| **규격·원장 문서 4** | 규격 v1.8(5.6절 표 + 8장 OI 표) · 원장 v1.15(2곳) · `Raw_Rev_MEF_Impacts_and_Identity_v0.7.md` · `raw_fits_spec/SMC_CLAUDE.md` |
| **OI-18 언급 (문자열과 별개)** | `ics_sim/ics_sim/hardware/base.py:181` · `rawhdr.py:568` · `sequencer.py:480` (+ `_vendor` 3, 생성물) · `raw_fits_spec/README.md:121` · `raw_fits_spec/SMC_CLAUDE.md:216` |
| **기계 검증** | `ics_sim/tests/test_raw_draft.py`(견본 바이트) · `ics_archon/tests/test_fitswrite.py`(카드 이미지) · `ics_archon/tests/test_labtest_spec_copy.py`(사본 표류) |

**손대지 않을 것**: `ics_sim/DevNote.md` 의 `CCD temperature M` 언급은 **이력**
이므로 그대로 둔다 (v1.6 전수 검사에서 세운 방침 — 라운드별 기록은 현재값으로
덮지 않는다).

✅ **결정됨 -- 견본 판은 올리지 않는다** (운영자 확정 2026-08-29):
*"변경사항이 마이너한 부분이므로 승격 안함"*.  `…header.v1.0.txt` 이름을 그대로
두고 **제자리에서 고친다**.  ⭐ 부수 이득 -- 파일명이 그대로라
`ics_sim/tests/test_raw_draft.py` 의 글롭(`*.fits.header.v1.0.txt`)이 계속 맞는다
(2026-08-22 에 견본을 개명했다가 **바이트 대사 6개가 통째로 skip 된 사고**가 있었다).
⚠️ 대신 판 번호가 이력을 말해 주지 않으므로 **견본을 고치는 커밋에 무슨 카드가 왜
바뀌었는지 반드시 적을 것.**
#### ⭐ `RDMODE` 결측값을 `UNKNOWN` 으로 등재 (운영자 확정 2026-08-29) — **판올림 이월 대기** (v1.9 는 guide 장 신설만 싣고 나왔다 — 견본 v1.1 승격 라운드에서)

**결정**: 독출 모드를 못 알아냈을 때 헤더에 싣는 값은 **`UNKNOWN`** 이다.
종전 코드 기본값 `'NORMAL'` 은 **실제로 쓰이는 값**이라 "정말 NORMAL" 과 "못
알아봐서 NORMAL" 이 구별되지 않았다 — 5.0절이 금지한 *"결측을 sentinel 로
가리는"* 형태다.

⚠️ **코드는 이미 갔다** (`ics_sim/rawhdr.py` `RDMODE = 'UNKNOWN'` + 기계 사본 셋).
"규격이 먼저 서고 코드가 뒤따른다" 의 **예외**이고, 이유는 규격 판올림까지
기다리면 그 사이 자료가 `NORMAL` 이라는 거짓말을 달고 아카이브에 들어가기
때문이다.  **규격이 뒤따라야 할 자리:**

| 자리 | 무엇 |
|---|---|
| 5.5절 `RDMODE` 행 | 지금 `독출 모드 (`'NORMAL'` 등)` — 결측값 `UNKNOWN` 을 명시 |
| 5.0절 sentinel 절 | 문자열 sentinel 이 `NC` 하나였다.  `UNKNOWN` 의 자리와 **`NC` 와의 뜻 차이**("없다" vs "모른다")를 적을 것 |
| 7장 검증 체크리스트 8번 | `HK sentinel '-999.99'/'9.99e-9' 만 사용` 문장에 걸린다 |

⭐ **하류 파급은 없다** — converter 는 `RDMODE` 를 읽지 않는다(MEF `READMODE` 는
converter 가 스스로 박는 별개 카드).  `UNKNOWN` 은 새 낱말도 아니다 — `SHUTTER`
값 어휘와 converter 기본값에 이미 있다.  견본 pair 는 **안 바뀐다**(`NORMAL` 은
실제 관측값이다).

#### ⭐ `ICG` RTD 구성 변경은 `CAMVER` 로 흡수한다 (운영자 확정 2026-08-27) — **판올림 이월 대기** (견본 v1.1 승격 라운드에서)

**결정**: HK 7장의 출처(`ICG RTD`)를 가리키는 **새 카드는 두지 않는다.**  RTD 의
배치·귀속이 바뀌면 **HW 변경으로 보고 `CAMVER` 를 올린다.**  (후보였던 `ICGCFG`
카드 신설은 채택되지 않았다.)

**왜 문제가 되나** — `CTRLnCFG` 는 **science 컨트롤러 둘의 ACF** 다.  그런데
RTD 채널 대응(`MOD10\SENSORBLABEL=RTD8_CCD` 등)을 정하는 것은 **가이드 ACF** 이고
그 이름은 science 헤더에 실리지 않는다.  그래서 4.3절이 "구성이 바뀌면
`CAMVER`(HW)·`CTRLnCFG`(설정) 범프로 드러난다" 고 한 장치가 **HK 7장에는 안
걸렸다.**  `CAMVER` 로 흡수하면 4.3절의 기존 구조를 그대로 쓰면서 그 구멍이
닫힌다 — 새 카드가 없으므로 converter·L1 에 영향이 없다.

⚠️ **다만 조건이 둘 있다.  이것 없이는 범프가 범례 없는 깃발이 된다.**

1. **규범을 규격에 명시해야 한다** (4.3절) — "**듀어 RTD 의 배치·귀속 변경도
   `CAMVER` 범프 사유다**".  안 적으면 다음 사람이 "가이드 ACF 는 science HW 가
   아니다" 로 읽고 안 올린다.  지금 4.3절은 고정 대상만 정하고 **무엇이 범프
   사유인지는 열거하지 않는다.**
2. **`CAMVER` 값 ↔ 구성 대장이 있어야 한다.**  `CAMVER` 는 문자열 하나라 범프는
   "무언가 바뀌었다" 만 말하고 **"무엇이" 는 말하지 않는다.**  `CEU-v2.1` →
   어느 RTD 배치인지를 찾을 표가 없으면 과거 자료를 해석할 수 없다.  위치는
   `project_management` 또는 `raw_fits_spec` 원장 중 하나로 정할 것.

⚠️ **부작용 하나** — `CAMVER` 는 "전자부 세대 판별의 참조점"(규격 5.4절)이라
캘리브레이션 게이팅에 쓰일 값이다.  RTD 라벨 재배치로 그것이 움직이면, 신호
계통이 안 바뀌었는데도 소비자에게는 세대가 바뀐 것으로 보인다.  **대장(조건 2)이
그 구분을 대신해야 한다.**

**운영 절차도 정해야 한다** — 지금 `ics_archon.ini` 의 `[camera] camver` 는 비어
있고 코드 기본값 `'CEU-v2.1'` 이 실린다.  범프는 ini 에 값을 적는 방식이 되므로
**벤치와 관측소가 각자 다른 값을 들 수 있다.**  누가 언제 올리는지를 규범에 함께
적을 것.

✅ **지금은 이력이 깨끗하다** — science raw 자료가 아직 한 장도 없다.  이미
일어난 MOD10 센서 B/C 뒤바뀜(2026-08-14/15, `_rtd9cal` 판)은 이 규범 하에서는
범프 사유였지만 **오염된 자료가 없다.**  규범을 **첫 science 프레임 전에** 세우면
이력에 구멍이 안 생긴다 — 그것이 이 항목의 시한이다.

- **`Cn_VOLT` 7레일은 그대로 둔다** — 표준 전원이 만드는 전량임이 확인됐다
  (위 매뉴얼 사실). 종전에 "12레일이므로 늘려야 한다" 고 적었던 검토는 **철회**
  한다.

## ▶ 인수인계 (2026-09-02 마감 — ⭐ 새 세션이면 **여기부터**)

### ✅ 2026-09-01~02 — **실기 시험 완료.  `LOCK`/`FETCH`/버퍼 운영 종결** (⭐ 최신)

벤치 두 대(**KMTC-101** 1261/REV 7 · **KMTK-113** 1252/REV 5)에서 `tools/ics_archon_buftest.py`
2x2 + `probe_archon` 3단계 + 운영자 `ArchonGUI` 재관측·`WARMBOOT`·`REBOOT`.  경위·판단은
**[DevNote 10장](DevNote.md)**, 결과·실행법은 **[`archon_lock_fetch_report.md`](archon_lock_fetch_report.md)**.

| 물음 | 답 |
|---|---|
| FETCH 중 readout 이 멈추나 (DevNote 8.9) | ❌ **안 멈춘다** — 두 유닛 넷 다 **368.0 행/초**.  8.9 는 **GUI 표시 착시**였다 (폴이 버려져 화면만 얼었다; 재개 시 10→1500 점프) |
| `LOCK` 이 반영되나 · 대가가 있나 | ✅ **15/15 반영, 대가 0** |
| `LOCK` 이 지킬 구간이 있나 | ✅ **있다** — `nolock` 으로 fetch 하다 경계를 넘은 2회 모두 엔진이 **읽는 중인 버퍼로** 옮겨왔다 |
| **`lock_buffer`** (A-5 판단 ②) | ✅ **`true` 유지.  종결** |
| 버퍼 둘에서 하나 잠그면 (H3) | 엔진이 잠긴 것을 피하고 **쓰던 버퍼를 재사용**, 감속 0 (`--hold 20`) |
| 독출·주기·FETCH 실측 | **368 행/초 · 4700행 12.77초 · 주기 13.27초(`NoIntMS` 0.5 포함) · FETCH 3.2~3.5초 / 99~107 MiB/s** |
| `BUFnFRAME` 리셋 | **`REBOOT` 만** (첫 프레임 = 1).  CCD 전원·`WARMBOOT` 는 이어진다 |
| `POWERON` 전제 | **`APPLYALL` 필수** (매뉴얼 p.51) — 그 세션에서 안 했으면 `?xx` 거부 |

**⏳ 남은 것 — 전부 코드·문서다, 실기 아님** (DevNote 10.9):

| 자리 | 무엇 |
|---|---|
| ✅ `parse.progress` | **`PCTREAD` 가 50% 를 못 넘었다** — `FRAMEMODE=2`(split) 라 `BUFnHEIGHT = 2 x LINECOUNT`.  → `progress_of(lines_total)` + `ArchonController.lines_total`(ACF `LINECOUNT`) (2026-09-02, DevNote 9.15) |
| ✅ `config.MIN_FRAME_PERIOD` | 12.0 → **13.27** (실측) — 2026-09-02 |
| ✅ `[archon] fetch_timeout` | 30 → **10**.  **잠금 > 주기면 다음 장이 덮인다** → 기동 검사 신설 (`lock_buffer=true` · FETCH 상한 >= 주기면 경고).  guide 는 **1.0**(하한 1.375 아래) — 2026-09-02 |
| ✅ `controller.py` | `LOCK%d` 를 `try` 안으로 — 잠금 명령이 죽어도 `LOCK0` 을 탄다 (2026-09-02) |
| `buftest` · `probe` | `RCONFIG` 선검사를 `POWERON` 앞 · 1단계 `STATUS` · `Exposures=N` · "ACF 적용 전" 문구 |

⚠️ **아래 "🔬 `LOCKn` A/B 실험 절차" 절은 종결됐다** — 계측값(덮였나)이 죽고 도구가 바뀌었다.
역사로 남겨 두되 **따르지 말 것.**

### (2026-08-30 시점) 한 줄 요약 — **실기 없이 이 브랜치에서 할 코드 작업은 없다**

브랜치 `ics-archon-v1.0-build` = `7e63db1`, **origin 동기**, 워킹트리 깨끗.
시험 `ics_archon` **235** · `ics_sim` **330**.  `main` = `41845da`, PM 문서 넷과
`raw_fits_spec` 문서 넷이 **브랜치와 바이트 단위로 같다**(확인 완료).

**남은 것은 셋뿐이고 전부 이 브랜치 밖이다:**

| 남은 것 | 누가 | 어디 |
|---|---|---|
| ⭐ **실기 시험** — 아래 "▶ 다음은 실기다" | 운영자 + 벤치 | 작업 B · A/B 실험 |
| ⏳ **판단 하나** — `connect()` 에 `drop_tickets` 배선 (`icg_archon` 착수는 운영자 지시로 **2026-08-31 착수** — 작업 D) | **운영자** | — |
| ⏳ **`main` 소관 둘** — 규격 차기 판 등재(이월 4건 — v1.9 는 2026-08-30 발행·머지됨) · 충욱 브랜치 머지 | `main` | `raw_fits_spec/` · PM |

### ✅ 2026-08-30 에 한 것 — 결함 셋을 고치고 매뉴얼의 지위를 정정했다

커밋 셋 (`9bc8bd2` → `d26ea41` → `7e63db1`).  경위는 [DevNote 8장](DevNote.md).

| 무엇 | 성격 |
|---|---|
| ⭐ **프레임 번호 되감김에서 노출을 잃던 것** — `next_frame()` 이 `frame > prev` 로만 찾아 카운터가 한 바퀴 돌면 `frame_timeout`(300초)까지 기다리다 실패한다.  **guide 는 16비트면 하룻밤**(1초 주기 18시간) | **기능 결함** |
| ⭐ **fetch 중(약 5초) 덮이는 창을 아무도 안 봤다** → `[archon] recheck_after_fetch`(기본 `true`) | **기능 결함** |
| **`drop_tickets()` 가 죽어 있었다** → `power_on()` 에 배선 | 잠재 결함 |
| ⭐ **`LOCKn` 이 먹는지를 `RBUF`/`WBUF` 로 관측** — 왕복 0(덮임 대조가 이미 읽는 `FRAME` 에서 뽑는다) | 계측 신설 |
| ⚠️⚠️ **매뉴얼은 판정 근거가 아니다** — 문서·주석 전반 정정 | **판단 규범** |

#### ⚠️⚠️ 가장 중요한 것 — **매뉴얼(2021-02-23)을 판정 근거로 쓰지 않는다**

운영자 지적: *"매뉴얼 개정판이 오래되었고 현행 FW 가 다 반영되지 않은 부분도,
**반대로 매뉴얼에 묘사된 기능이 FW 에 반영되지 않은 경우도** 있었다.  따라서
**실측이 가장 신뢰할 수 있는 판단 근거**다."*

⚠️ **표류가 양방향이라 어느 쪽으로도 보증하지 않는다.**  ⭐ 이 저장소 안에 이미
반례가 둘 있었다 — `MODn_TYPE` 16+(실기 ACF 는 17·18) · AD 모듈 슬롯(p.20 은
5-8, 실기는 5·8 둘뿐).  **둘 다 "매뉴얼이 낡았다" 로 넘어가며 원칙으로 올리지
않아** 사흘 뒤 같은 실수를 했다(내가 p.71 한 문단으로 `LOCK` 결론을 밀어 올렸다).

**근거 등급**: 우리 실기 실측 > labtest 1년 운용 > labtest 코드의 흔적 한 줄 >
**매뉴얼(가설의 출처)** > 우리 추론.  ⭐ 매뉴얼의 역할은 **무엇을 재야 하는지
알려 주는 가설 생성기**다.  등급표와 사례는 [DevNote 8.7](DevNote.md).

⚠️ **`tests/fake_archon.py` 도 판정 근거가 아니다** — 우리가 매뉴얼을 읽고 만든
것이라, 시험 235개가 다 통과해도 실기 물음은 안 닫힌다.

### ▶ 다음은 **실기다** — 값싼 것부터

⭐ **1~2 는 벤치에서 5분이고 망원경 시간이 안 든다.**

| # | 무엇 | 비용 | 무엇이 결정되나 |
|---|---|---|---|
| 1 | `FRAME` 한 번 읽어 **`BUFnFRAME` 이 65535 를 넘었나** | **0** | ⏳ **미결** — 두 유닛 다 `REBOOT` 직후라 카운터가 작다 (2026-09-02).  ⭐ 10.7 로 카운터가 CCD 전원·`WARMBOOT` 를 넘어 이어지므로 **`REBOOT` 없이 도는 guide 유닛이 자연 표본이다** — 16비트라면 1.375 s 주기로 하루 남짓(65535 장)에 한 바퀴.  첫 guide 구동부터 `BUFnFRAME` 을 적어 두고, 되감김 ERROR(`프레임 번호가 뒤로 갔다`)가 뜨는 값이 곧 폭이다.  코드는 폭에 안 기댄다(8.3) |
| 2 | ~~`probe_archon --lock` / `--no-lock` 단발 비교~~ | — | ✅ **닫힘 (2026-09-01)** — `LOCK1` 뒤 `RBUF=1`, 두 FW 다 15/15 반영.  DevNote 10.4 |
| 3 | ~~전원 재투입 직후 `BUFnFRAME` 이 0 인가~~ | — | ✅ **닫힘 (2026-09-02)** — CCD 전원·`WARMBOOT` 는 **이어지고**, `REBOOT` 만 **1 부터**.  DevNote 10.7 |
| 4 | ~~BIAS 연속 10장 × 2~~ | — | ✅ **닫힘 (2026-09-01)** — `buftest` 2x2 로 대체.  넷이 같다.  DevNote 10.4 |
| 5 | 작업 B 나머지 | 실기 일정 | 아래 "작업 B" 목록 |

~~절차와 판정 기준은 아래 "🔬 `LOCKn` A/B 실험 절차" 에 있다~~ — ✅ **종결 (2026-09-01~02,
DevNote 10장)**.  회귀 확인 절차는 [`archon_lock_fetch_report.md`](archon_lock_fetch_report.md)
4절(`tools/ics_archon_buftest.py` 2x2)이다.  (판정을 실험 전에 못박아 둔 것은 그대로
옳았다 — 10.10-2.)

### ⏳ 운영자 판단 대기 둘

1. **`icg_archon` 착수**(작업 D) — 아래 작업 지시 참조
2. **`connect()` 에도 `drop_tickets()` 를 걸까** — `power_on()` 에는 걸었다.
   ⚠️ 재접속은 *"확실히 못 받는다"* 가 아니다(링크만 끊겼으면 버퍼가 살아 있을
   수 있다).  걸면 그 프레임을 확실히 잃고, 안 걸면 낡은 표가 남는다.

### ⏳ `main` 소관 둘

1. **규격 차기 판 등재** — `RDMODE = UNKNOWN`(5.5절이 아직 `'NORMAL' 등` 이다) 포함
   **이월 4건** (v1.9 는 2026-08-30 guide 장 신설·`Radionode` 개명만 싣고 발행됐고
   브랜치에 머지됐다 — 4건은 견본 v1.1 승격 라운드로 이월).
   ⚠️ **`raw_fits_spec` 은 `main` 소관**이다
2. **충욱 브랜치**(`claude/team-progress-report-email-igu94r`) **머지** — 09-01
   아젠다에 김승리·본부장 문봉곤 참석과 코드 완성 안건 한 줄을 더한다.
   ⭐ `main` `41845da` 기준으로 **충돌 없이 합쳐지는 것을 확인했다**(2026-08-30
   모의 병합) — **우리가 08-29~30 에 옮긴 변경도 안 지워진다.**  브랜치가 더하는
   것은 그 두 줄뿐이다.  ⚠️ **회의가 2026-09-01 이라 시간이 걸린다** — 목의 판단

### ✅ 머지와 작업 E 는 **끝났다** (2026-08-29)

`main` 합류(16커밋, `b45fb31`)와 **작업 E(`CTRLnCFG` 파생, `3dabe21`)** 가 다
들어갔다.  다음 일감은 **작업 B~D** 다 — 그중 B 는 전부 실기가 있어야 한다.

머지로 들어온 것:

- **raw spec v1.8** (태그 `raw-spec-v1.8`) — `OI-9` 폐기 · `CTRLnCFG` 를 실제
  ACF 이름으로 · **견본 pair 4장의 `CTRLnCFG` 값이 바뀌었다**
- 세 문서 판올림으로 **파일명이 바뀌었다** — 규격 `_v1.8.md` · 원장 `_v1.15.md` ·
  통합문서 `_v0.7.md` (구판 `archive/`).  이 브랜치의 구 파일명 인용은 다 고쳤다
- 충욱 작업 15커밋 (PM 문서 · gmon 그래프 창·합성 별 주입 등)

⚠️ **머지 충돌 2건의 해소가 남긴 것** — `ACTION_REGISTER.md` 를 `main` 쪽으로
받으면서 **ACT-009 가 "ICS 가 IP 대역으로 사이트를 자동 판정한다" 로 되돌아갔다**
(D-015 는 폐지됐고 `siteid.py` 는 이 브랜치에서 지웠다).  같은 커밋의
`ICS_DEPLOYMENT_CHECKLIST.md` 는 "되살리지 말 것" 이라고 적고 있어 **두 PM 문서가
서로 어긋나 있다** — 전수 검토에서 고쳤다(아래 "전수 검토" 절).

### ✅ 작업 E — `CTRLnCFG` 파생 **완료 (2026-08-29)**

`[archon] acf_mk`/`acf_nt` 경로에서 **폴더와 확장자(`.acf`/`.cfg`)를 떼어**
`CTRL1CFG`/`CTRL2CFG` 를 채운다.  **비어 있을 때만** 채우고, 손으로 적어 둔 값이
파생값과 다르면 **기동에서 경고**한다.  판단 근거는 [DevNote 5장](DevNote.md).

| 자리 | 무엇 |
|---|---|
| `ics_archon/config.py` `cfg_name_from_acf()` | 자르기 규칙 **한 곳** (`.acf`/`.cfg` 만, 대소문자 무관) |
| `ics_archon/app.py` `fill_controller_cfg_names()` | 파생해 `cfg.controllers` 에 채운다 (`IcsArchon.__init__`) |
| `ics_archon/config.py` `_cross_checks()` | 손편집 값 ↔ 파생값 **어긋남 경고** |
| `archon/backend.py` `controller_info()` | ⚠️ **여기에도 파생이 있었다** — `splitext` 를 쓰고 있어 같은 함수로 바꿨다 |

⚠️ **`splitext` 를 쓰지 말 것** — ACF 판 번호에 점이 들어간다(`…_R2609.1`).
확장자 없이 적힌 경로에서 `.1` 을 먹어 **판 번호가 조용히 깨진다.**

### ✅ 전수 검토 — 세 저장소 (2026-08-29, 목 지시)

작업 E 뒤에 `raw_fits_spec` · `ics_sim` · `ics_archon` (+ 걸린 PM 문서)를 훑었다.
경위·교훈은 [DevNote 6장](DevNote.md).  고친 것:

| # | 무엇 | 성격 |
|---|---|---|
| 1 | ⭐ **`RDMODE` 유도가 현행 ACF 이름에서 늘 실패한다** — 이름에 `fast`/`comp`/`slow` 토큰이 없다.  값을 만들지 않고 **기동 경고**를 붙였다 | **기능 결함** |
| 2 | **labtest 사본 다섯의 `splitext`** — 작업 E 가 본편에서 고친 것과 같은 함정 | **잠재 결함** |
| 3 | `raw_fits_spec/README.md` — 버전 열이 `v1.7`, 견본 카드 수 143(실측 144), 종결된 `OI-15` 가 열린 항목, 삭제된 배선표 v1.0 안내, 실기 구현이 "스텁" 등 | 문서 |
| 4 | **대기 4건이 "v1.8 작업" 으로** 적혀 있었다 (이 문서 · `raw_fits_spec/SMC_CLAUDE.md`) → **v1.9 대기** | 문서 |
| 5 | ⚠️ **머지가 되살린 사실 오류** — `ACTION_REGISTER` ACT-009 · `DECISION_LOG` D-015(아직 `Accepted` 였다) · **09-01 종합검토 아젠다** | **PM 정합** |
| 6 | 시험 수·ACF 예시 파일명·문서 판 인용 (`rawcards.py` · `test_raw_draft.py` · labtest 다섯) | 문서 |

⚠️ **`raw_fits_spec/` 문서 둘(`README.md`·`SMC_CLAUDE.md`)을 이 브랜치에서
고쳤다.**  규격·원장·통합문서 본문과 **견본 pair 4장은 손대지 않았다** — 그쪽은
판올림과 함께 움직이는 `main` 소관이다.  `main` 이 같은 두 파일을 동시에 고치면
충돌하므로, 합류 때 **이쪽이 사실 갱신분**임을 기억할 것.

✅ **`RDMODE` 는 확정됐다 (운영자 2026-08-29) — 현행 전부 `NORMAL`.**
`ics_archon.ini` 에 **직접 적었다**(`rdmode = NORMAL`).  ⚠️ **속도가 다른 ACF 를
올리면 이 줄도 함께 고칠 것** — 안 고치면 헤더가 거짓말한다.  ACF 이름에 토큰이
있으면 기동에서 잡아 준다(양방향 경고).

✅ **못 알아냈을 때의 기본값은 `UNKNOWN` 이다 (운영자 확정 2026-08-29).**  종전
`'NORMAL'` 은 **실제로 쓰이는 값**이라 "정말 NORMAL" 과 "못 알아본 NORMAL" 이
헤더에서 갈리지 않았다.  ⚠️ 문자열 sentinel `'NC'` 와 **뜻이 다르다** — `NC` 는
"그 자리가 없다", `UNKNOWN` 은 "있는데 모른다" 다.  ⏳ **규격 등재는 차기 판올림
이월** (v1.9 에 안 실렸다 — 5.5절이 아직 `'NORMAL' 등` 이라 적는다).  경위는
[DevNote 6장](DevNote.md).

### ✅ ▶ **`main` 으로 넘어가서 할 일** — **완료 (2026-08-30)**

⭐ **PM 문서 넷 · `raw_fits_spec` 문서 넷을 다 옮겼고**(`main` = `41845da`), 여덟
파일 전부 브랜치와 **바이트 단위로 같은 것**을 확인했다.  아래는 그때 세운 계획을
근거로 남겨 둔다.  ⏳ **남은 것은 충욱 브랜치 머지뿐**(위 "`main` 소관 둘").

<details><summary>당시 계획 (펼치기)</summary>


**순서**: `ics_archon` 작업을 끝낸 뒤 `main` 으로 전환해서 한다 (목 지시).
⚠️ **시간 제약이 하나 있다** — 아래 1번은 **9/1 종합검토 회의(2026-09-01)** 에
걸린다.  그런데 이 브랜치에 남은 것은 **작업 B(전부 실기 필요)** 라 "작업 완료"
시점이 실기 일정에 매여 있다.  ⭐ **회의 전에 main 이 갱신되지 않으면 참석자는
폐지된 IP 판정 절차서와 틀린 아젠다를 본다.**  1번만 먼저 옮기는 것은 5분이면
되고 코드와 무관하다 — 목의 판단을 받을 것.

#### 1. PM 문서 넷을 브랜치에서 가져온다 (`main` 이 아직 못 받았다)

```bash
git checkout main
git checkout ics-archon-v1.0-build --   project_management/governance/DECISION_LOG.md   project_management/operations/ICS_DEPLOYMENT_CHECKLIST.md   project_management/planning/ACTION_REGISTER.md   project_management/meetings/AGENDA_2026-09-01_COMPREHENSIVE_REVIEW.md
```

⭐ **새로 고치는 게 아니라 브랜치 파일을 그대로 꺼내오는 것**이라, 그 파일들은
양쪽 내용이 같아져 **나중 합류에서 충돌이 안 난다.**

| 파일 | `main` 이 못 받은 것 |
|---|---|
| `DECISION_LOG.md` | **D-020 신설** · D-015 → `Superseded by D-020` |
| `ICS_DEPLOYMENT_CHECKLIST.md` | ⚠️ **문서 전체가 아직 IP 판정 판**이다 (`3bf2d73` 이래 브랜치에만 있다) |
| `ACTION_REGISTER.md` | ACT-009 — `main` 은 아직 *"IP 대역을 보고 자동 판단한다"* |
| `AGENDA_2026-09-01_…md` | 없어진 리스크를 의제로, 없는 코드(`SITE_SUBNETS`) 갱신을 체크 항목으로 |

#### 2. `DECISION_LOG` 의 **구현 상태가 낡았다** — 넷

`raw spec v1.8` 기준으로 맞출 때 함께 볼 것.  넷 다 **`Accepted` 인데 상태 문구가
"구현 예정/대기"** 이고, 실제로는 이 브랜치에 **구현이 끝나 있다**:

| 결정 | 현재 문구 | 실제 |
|---|---|---|
| D-016 | `ics_sim` 구현 **예정** | ✅ 충돌 선검사·번호 증가 구현 (`test_d016_…`) |
| D-017 | `ics_sim` 구현 **대기** | ✅ `rawpair.KASI_SITE` · `site_of_observatory()` |
| D-018 | `ics_sim` 구현 **대기** | ✅ `rawpair.NUM_SPACE = 1_000_000` (⚠️ `main` 이 넣은 `state.EXPNUM_SPACE` 가 아니다 — 브랜치는 구조를 안 겹치게 했다) |
| D-019 | `ics_sim`/`ics_archon` 구현 **대기** | ✅ `EXPID` 카드 · 견본 pair 반영 |

⚠️ **어디에 구현됐는지를 함께 적을 것** — `main` 의 `ics_sim` 과 브랜치의
`ics_sim` 이 구조가 다르다(D-018 이 그 예다).  *"구현 완료
(`ics-archon-v1.0-build`; `main` 은 합류 대기)"* 처럼 갈라 적어야 한다.

#### 3. 깨진 링크 둘 — `DECISION_LOG`

`raw_fits_spec/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md` 를 가리키는데
**그 파일은 `archive/` 로 갔다.**  D-016 절의 `상태:` 줄(613)과 `영향:` 줄(636)
둘이다.  경로에 `archive/` 를 넣거나 현행 판(지금은 `_v0.8.md` — 판 갈이마다
낡으니 "현행 통합문서" 로 적는 것도 방법)으로 옮길 것 — ⚠️ **다만
Part 2 의 내용이 v0.5 기준이라 판을 바꾸면 절 번호가 달라질 수 있다.**

⚠️ **그 밖의 `raw spec v1.5 반영 완료` 류는 고치지 말 것** — 그 결정이 **어느
판에 반영됐는지의 이력**이라, 현행 판으로 바꾸면 오히려 사실이 틀린다.

#### 4. 보관본 변경 되돌리기 (목 지시 2026-08-29)

`raw_fits_spec/archive/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.6.md` 의 한 줄
(+1 −1, 구판 목록)이 브랜치에 있다.  **보관본은 손대지 않는 것이 규칙**이므로 뺀다.

⚠️ **`main` 에서 "빼는" 것으로는 안 끝난다** — 브랜치에 남아 있으면 **나중 합류에
다시 들어온다.**  영구히 빼려면 **브랜치에서 되돌려야** 한다.

#### 5. `raw_fits_spec` 문서 넷도 같이 갈지 (목 판단)

`main` 소관인데 이 브랜치가 고쳤다 — 규격 `v1.8`(2.2절 제자리 정정 · 머리말
결정 기록 표) · `README.md` · `SMC_CLAUDE.md` · 통합문서 `v0.7`.  1번과 같은
방법으로 옮길 수 있다.  ⚠️ 안 옮기면 **`main` 의 규격이 계속 "호스트 IP 로
판정한다" 고 말한다.**

</details>

### 2026-08-29 세션이 한 것 — 넷

| # | 무엇 | 어디 |
|---|---|---|
| 1 | **작업 A** — 층 1·2 감시·기록 구현 + labtest v1.3.4 이식 | 커밋 `007fd65` (앞 세션분) |
| 2 | **운영자 ACF 정리 반영** — guide 정본을 하나로 줄이고 개명, 영향 전수 | `298d9d2` |
| 3 | **참고 자료 재검토** — `__ref_archon_control/` 전수, 옮긴 것 1 · 안 옮긴 것 3 · 새 사실 3 | `298d9d2` |
| 4 | **`main` 합류 + 작업 E(`CTRLnCFG` 파생)** | `b45fb31` · `3dabe21` |

### 상태 — 어디까지 됐나

| 층·항목 | 상태 |
|---|---|
| 층 1 (온도 10 + 레일 7×2) 기록 | ✅ 구현 완료.  **실기 미검증** |
| 층 2 (바이어스 16채널 V/I) 기록 | ✅ 구현 완료.  **헤더 수록은 규격 개정 사안**(작업 C 의 D3) |
| 층 3 (`ICG RTD` · 진공) | ⛔ **`ics_archon` 소관 아님** — `icg_archon` 대기.  해독 규칙은 이미 다 있다 |
| `POWERON` 확인 | ✅ 구현 완료.  **실기에서 램프 시간(P-j)을 재는 것이 남았다** |
| **fetch 경로 방어** (덮임·되감김) | ✅ 구현 완료 (2026-08-30) — fetch 앞 대조 · `LOCKn` · **fetch 뒤 재대조** · 되감김/재시작 재동기.  ✅ **`LOCKn` 실기 확인 (2026-09-01)** — 두 FW 15/15 반영·대가 0·지킬 구간 실재 (DevNote 10.4·10.6) |
| **`BUFnFRAME` 폭** | ⚠️ **미상** — 매뉴얼에 없다(전수 검색).  코드는 폭에 안 기댄다.  ⭐ 실기 관측 하나로 16비트 배제 가능 |
| guide 자리 표 (`OI-19`) | ✅ **종결** — raw spec v1.9 **10.4절 수록** (첫 guide 구동 때 STATUS 재확인만 남는다) |
| 실기 왕복 전체 | ⏳ **아무것도 안 해봤다** — 작업 B 가 그 목록 |

### 새 세션이 밟을 순서

1. ⭐ **실기 없이 할 코드 작업은 없다** (2026-08-30 기준, 위 "한 줄 요약").
   남은 것은 **실기(작업 B·A/B 실험)** · **운영자 판단 둘** · **`main` 소관 둘**.
2. 위 [참고 자료 재검토](#-참고-자료-재검토--__ref_archon_control-전수-2026-08-28-목-지시)
   절의 **"옮기지 않은 것 셋"** 표를 반드시 볼 것 — `__ref_archon_control/` 을
   다시 열면 같은 것이 "빠졌다" 로 보인다.  **근거가 그 표에 있다.**
3. "미해결 목록"(F1~F12 · P1) — **앞 세션 워크플로 결과를 근거로 쓰지 말라는
   경고**가 붙어 있다.

### ⚠️ 새 세션이 밟기 쉬운 함정 일곱

1. **`__ref_archon_control/` 은 읽기 전용이다.**  참고 원본 보관용이라 여기
   파일을 고치지 않는다 — `UNIT_ACF` 가 구 파일명을 가리켜도 **운영자가 자기
   작업본에서** 고친다.  고쳐야 할 것 같으면 사본을 밖으로 뜬다.
   ⚠️ **예외가 하나 있다 — `.py` 의 Twilio 자격증명은 지웠다** (**빈 문자열**,
   운영자 확정 2026-08-28).  `ics_archon/` 안의 해당 파일 **열여섯 전부**가 같은
   표시다 — SID·토큰·전화번호 둘.  **빈 문자열을 고른 이유**는 `'0000'` 같은
   자리표시가 **값처럼 보여서** 나중에 진짜 설정값으로 오해될 수 있어서다.  **GitHub 비밀 스캐닝이 푸시를 거부한다** — 실제 값은
   운영자 작업본에만 있다.  ⚠️ **되돌려 넣지 말 것**: 넣으면 그 커밋은 영영
   푸시가 안 되고, 우회 URL 로 밀면 **살아 있는 자격증명이 원격에 박힌다.**
   그래서 **보관함의 `.py` 는 "받은 바이트 그대로" 가 아니다** — 그 규칙
   (`.gitattributes` 의 `-text`)은 **`.acf` 에만** 걸린다.
2. **`__` 접두어는 "참고용" 표지이지 "로컬 전용" 표지가 아니다.**  로컬 전용은
   **저장소 바깥**(`CEU/` 직속)이라는 위치가 정한다 -- `__isislogs/` ·
   `__osu_legacy/` · `__tcs_simulator/`.  ⚠️ 구 `__localonly_` 접두어는
   **2026-08-29 에 폐지**됐고 문서 정리도 끝났다(main `c81c1f8`, 이 브랜치는
   `2f039fc` 합류분에 포함).  옛 경로를 다시 쓰지 말 것.
3. **`.gitattributes` 에 `**/__ref_archon_control/**/*.acf -text` 가 걸려
   있다** (2026-08-28 신설).  그 폴더의 ACF 는 **받은 바이트 그대로**(CRLF 인
   것은 CRLF 로) 보관한다 — 정본 `acf/` 는 여전히 LF 다.  ⚠️ **둘을 같은
   규칙으로 되돌리지 말 것**: 정본이 CRLF 가 되면 파서에 `\r` 이 섞여 들어가고,
   보관본이 LF 가 되면 원본을 남긴 뜻이 사라진다.
4. **ACF 를 파일명으로 고르지 말 것.**  개명이 시험을 한 번 깼다
   (`kmtnet_guide_*.acf` 글롭이 빈 목록).  `tests/test_monitor.py` 의
   `_repo_acfs()` 가 **내용(`BIGBUF`)으로** 가른다 — 새 시험도 그것을 쓴다.
5. **`test_shutdown_waits_for_frames_that_are_still_being_saved` 는 부하에서
   간헐 실패한다.**  저장 창을 잡는 시험이라 그렇고, 그 시험 자신의 주석에
   이력이 있다.  단독으로 다시 돌려 보고 통과하면 그것이 답이다 —
   ⚠️ `ics_sim` 스위트와 **동시에 돌리지 말 것.**
6. ⚠️⚠️ **매뉴얼을 판정 근거로 쓰지 말 것** (2026-08-30, 운영자 지적).
   `__ref_archon_control/` 의 매뉴얼은 **2021-02-23** 판이고 현행 FW 와
   **양방향으로** 어긋난다 — 문서에 있는데 FW 에 없거나, FW 에 있는데 문서에
   없거나.  ⭐ **판단 근거는 실측**이고 매뉴얼은 *무엇을 재야 하는지* 알려 주는
   **가설 생성기**다.  ⚠️ `tests/fake_archon.py` 도 같다 — 우리가 매뉴얼을 읽고
   만든 것이라 시험이 다 통과해도 실기 물음은 안 닫힌다.  등급표는
   [DevNote 8.7](DevNote.md), 확인 상태는 아래 "매뉴얼이 말하는 것" 절.
7. **`CTRLnCFG` 를 만드는 자리가 둘이다** (2026-08-29, 작업 E).
   `app.fill_controller_cfg_names()`(ini 를 미리 채운다)와
   `backend.controller_info()`(백엔드 보고값)가 **같은 ACF 경로를 각자 읽는다.**
   자르기 규칙은 `config.cfg_name_from_acf()` **한 곳뿐**이니 규칙을 고칠 때
   거기만 보면 되지만, ⚠️ **한쪽만 고치면 "ini 를 비웠을 때만 이름이 다른"**
   형태로 나타나 재현이 어렵다.

### 실기 없이 더 할 수 있는 것이 남았나

**거의 없다.**  층 1·2 는 구현이 끝났고 층 3 은 소관 밖이며, 작업 C(규격 v1.8)는
`main` 에서 끝났고 **작업 E 도 끝났다**.  ⚠️ **작업 B 는 전부 실기가 있어야 하는
것**이라, 실기 없이 새 세션을 열면 할 일은 **규격 차기 판 준비**(이월 4건 —
`OI-18` 폐기 · `CAMVER` 규범 · D3 카드 배치 · `RDMODE UNKNOWN` 등재.
~~`CCDTEMP` chip 귀속 제거~~ 는 2026-08-30 조기 실행 완료)나
**`icg_archon`**(작업 D — 운영자 지시로 **2026-08-31 착수**)뿐이다.

## ▶ 다음 세션 작업 지시 (2026-08-28 마감 — 일감 목록)

이 세션은 **작업 A(층 1·2 감시·기록)를 구현**하고, labtest v1.3.4 가 얻은 것을
본편에 옮겼다.  반영 내역·판단 근거는 위
[층 1·2 감시·기록 구현](#-층-12-감시기록-구현-2026-08-28--작업-a-완료) 절과
[`DevNote.md`](DevNote.md) **3장**.

그 뒤 **참고 자료(`__ref_archon_control/`) 전수 재검토**를 했다 (목 지시
2026-08-28) — 옮긴 것 하나(`POWERON` 뒤 `POWER=4` 확인) · 안 옮긴 것 셋 ·
새로 확정한 사실 셋.  위
[참고 자료 재검토](#-참고-자료-재검토--__ref_archon_control-전수-2026-08-28-목-지시) 절과
[DevNote 4장](DevNote.md).  **guide ACF 정본도 하나로 줄고 개명됐다**
(`KMTK_GUI_162_STA0201_R2608.acf`, 운영자 2026-08-28.  ⭐ **현행은 `…_R2609.acf`** -- 2026-08-31 에 `NoIntMS` 를 0 으로 내리며 판을 올렸다, `acf/README.md`).

### ✅ 작업 A — 층 1·2 구현 **완료 (2026-08-28)**

| 무엇 | 어디 | 상태 |
|---|---|---|
| `ctrl.status_live` + `status_live_at`, **헤더용 `ctrl.status` 와 분리** | `archon/controller.py` | ✅ |
| 주기 감시 태스크 -- `IcsSim.spawn()` (`ics_sim` 무수정) | `app.py` | ✅ |
| **기동 접속** -- `_connect_controllers()`, 감시는 그 뒤 | `app.py` | ✅ (운영자 지시 2026-08-28) |
| CSV 기록 (컨트롤러당·날짜당 1파일, `~/AIC/log/`) | `archon/monitor.py` (신설) | ✅ |
| ini 키 -- `monitor` · `monitor_interval` · `monitor_log` | `config.py` `[archon]` | ✅ (+ `frame_dump` · `[archon.rails]`) |
| 바이어스 16채널 V/I (이름은 **ACF LABEL 에서**) | `archon/parse.py` | ✅ |
| D4 -- `VALID=0` -> 헤더 `NC` | `parse.telemetry_of(honour_valid=)` | ✅ (+ `health_problems` 가짜 경보도 함께 닫았다) |
| D5 -- 첫 노출 전 `-SYNCH` (G5) | `backend._synched()` | ✅ |

⚠️ **거동이 하나 바뀌었다** — **기동에서 접속하고 그 뒤에 감시를 시작한다**
(운영자 확정 2026-08-28).  **접속자는 컨트롤러당 하나**이므로 본편이 떠 있는
동안에는 STA GUI·`probe_archon` 을 붙이지 않는다 — 설정으로 피하는 것이 아니라
**본편을 내리고 쓴다.**  접속은 `monitor` 설정과 무관하다.

**남은 것은 실기 확인뿐이다** — 아래 작업 B 가 그 목록이고, **층 2 의 헤더 수록**
(D3)은 작업 C 로 넘어간다.

### 작업 B — probe 1단계 확인 항목 (실기 붙일 때, `tools/probe_archon.py`)

⭐ **P-e ~ P-g 는 이제 probe 1단계가 자동으로 찍는다** (2026-08-28) — 사람은
결과만 읽으면 된다.  P-a ~ P-d 는 여전히 **사람이 보고 판단**한다.

| # | 확인 | 왜 | 상태 |
|---|---|---|---|
| P-a | `LOG` 값의 상한 (드레인 안 하고 관찰) | 버퍼 깊이 = 매뉴얼 미기재 | 값은 찍힌다.  **상한은 사람이 관찰** |
| P-b | `FETCHLOG` 뒤 `LOG` 감소 여부 | 파괴적 읽기인지 | 손으로 (드레인은 안 넣었다) |
| P-c | `LOG=0` 일 때 `FETCHLOG` 응답 | **무응답이면 영구 정지**(p.45) | 손으로 |
| P-d | 로그 한 줄 생김새 (자체 시각·심각도) | `FETCHLOG` **승격 기준** 판정 | 손으로 |
| P-e | 형 17(ADM)·18(HVYBias) 실물 보고 | ACF 로만 확인했다 | ✅ 모듈 표가 찍는다 |
| P-f | 자리 표 대조 (`field_order_problems()` 가 조용한지) | 규격 5.6.1 실물 정합 | ✅ 판정을 찍는다 |
| P-g | `VALID`/`COUNT`/`POWER`/`OVERHEAT`/`LOG` 실제 보고 여부 | D4 · F2 의 PROVISIONAL | ✅ 한 줄씩 찍는다 |
| **P-h** | **바이어스 16채널이 STATUS 에 다 오나** (신설) | 층 2 의 열이 통째로 `NC` 가 되는지 | ✅ 채널 표가 찍는다 |
| **P-i** | **레일이 p.41 정상 범위 안인가** (신설) | `rail_flag` 열의 기준.  유닛이 다르면 `[archon.rails]` | ✅ 판정을 찍는다 |
| **P-j** | **`POWERON` 뒤 `POWER` 가 몇 초에 4 가 되나** (신설 2026-08-28) | `poweron_wait` 12초가 램프에 충분한지.  램프 중 `3` 을 실제로 보고하는지도 함께 | ✅ 기동 로그에 `POWER=4 (On) 확인 -- N초` 로 찍힌다 |
| **P-k** | **guide `Pixels` 를 줄여도 영상이 같은가** (신설 2026-08-29 · 갱신 2026-09-01, 운영자 예정) | 지금은 탭당 601 을 디지타이즈해 **528 만 저장**한다 -- 73개가 버려지고 픽셀 클록의 약 12%, **148.8 ms/프레임**이다.  ⭐ 데이터시트 대응(규격 9.4절: `8 BLANK\|15 DARK\|1 trans\|512 active` = 536)을 맞춰 보면 **73개는 레지스터 물리적 끝을 지난 자리**라 무손실이 거의 확정 -- 바이트 비교는 확인 절차다 | 손으로 -- 같은 조건 두 값으로 프레임 찍어 **바이트 비교**.  ⭐ **권고값은 528 이 아니라 `Pixels=529`**(디지타이즈 530 · 저장 528 = science 와 같은 여유 2; 528 이면 여유 1).  ⚠️ `LINE47` 의 인자 없는 `CALL PixelFirst`(+1)는 남길 것.  ⚠️ 실익은 **하한 1.375→1.228 s** 하나 -- 시퀀서 pacing 이라 `EXPTIME` 고정이면 주기는 그대로다 |

**그리고 첫 감시 로그로 볼 것** (운영자 몫과 겹친다):

1. `age_ms`·`lag_ms` 가 어떤 값인가 — **FETCH 중에 얼마나 밀리나**가
   `monitor_interval` 기본값(20초)이 맞는지의 근거다.
2. `fresh` 열이 0 으로 오래 머무는가 — `COUNT` 가 실제로 오르는지.
3. `CCD` 채널이 −30 아래를 읽는가 (`KMTK_GUI_162_STA0201_R2609.acf` 를 올린 뒤 -- limit 정정은 구 `R0827`=`R2608` 판과 같고, R2609 는 `NoIntMS=0` 만 다르다).

### 작업 C — raw spec **v1.8** (`main` 에서, 판올림)

⚠️ **이 브랜치에서 규격·견본을 손대지 말 것** -- 견본 pair 바이트가 정본이라
규격과 함께 움직인다.  상세와 **영향 전수 목록**은 위
[규격 쪽 후속](#규격-쪽-후속-다음-판올림-때) 절.

✅ **v1.8 은 이미 발행됐다 (2026-08-29, `main` `0c821ea`, 태그 `raw-spec-v1.8`)** --
다만 **아래 5건이 아니라 다른 둘**이 들어갔다.  세 문서를 함께 판올림했다:
**규격 v1.7→v1.8 · 원장 v1.14→v1.15 · 통합문서 v0.6→v0.7** (구판 `archive/`).

- **`OI-9`(배선 실측) 폐기** -- 종결이 아니라 폐기.  배선은 raw spec 4.5절 amp
  전수 표·`CHMAP_*` 와 MEF `AMPINFO` 가 통제한다(운영자 확정).  원장의 경고
  문구 셋은 **"세부 내용, 앰프별 배치 및 방향은 raw spec 4.5절(Amp 전수 표)을
  참조한다"** 로 바뀌었다.
- **`CTRLnCFG` 예시를 실제 ACF 이름 규칙으로** + 규격 5장에 **"폴더 경로와
  확장자(`.acf`/`.cfg`)를 뗀 이름"** 명시.  ✅ **그 파생은 코드로 들어갔다**
  (작업 E, `3dabe21` — [DevNote 5장](DevNote.md)).

⚠️ **아래 1~5 는 여전히 v1.9 이후 대기다** (4·5 는 실측·설계가 더 필요하다).

1. **`CCDTEMP` 에서 chip 귀속 제거** -- comment 의 `M` 을 없앤다.  추천 문안
   `Representative CCD temperature [deg C]`(37자, 여유 47자).  **영향 18곳 +
   견본 pair 바이트** -- 목록이 그 절에 있다.
2. **`OI-18` 폐기** -- 물음의 전제(chip 귀속)가 사라졌다.  종결이 아니라 폐기다.
3. **`CAMVER` 규범 명시** (4.3절) -- "듀어 RTD 의 배치·귀속 변경도 `CAMVER` 범프
   사유다".  ⚠️ **`CAMVER` 값 ↔ 구성 대장**과 **누가 언제 올리나**를 함께 정해야
   범프가 범례 없는 깃발이 되지 않는다.
4. **D3 -- 바이어스 측정값의 헤더 카드 배치.**  32개 값이 카드 하나에 안 들어간다
   (8개가 한 카드 한계).  두 갈래와 계산이 위 [층 2](#층-2--바이어스-측정값의-헤더-수록-계획-규격-개정-사안) 절에.
   ⭐ **이제 근거가 둘 늘었다** (2026-08-28) — ① 감시 기록이 `B_<라벨>_V/I`
   열로 **실제 채널 구성과 값 범위**를 남기므로 카드 폭·자리 수를 실측으로 정할
   수 있다(**첫 감시 로그를 보고 나서 정할 것**) ② **science 다섯이 같은
   16채널**임을 전수로 확인했다 — 자리 표가 유닛마다 갈리지 않는다.
   ⚠️ 그리고 **guide 는 18채널이고 라벨 넷에 `/` 가 있다** — 라벨을 카드
   이름이나 comment 로 옮기는 설계를 고르면 5.6.1절의 "슬래시 금지" 에 걸린다.
5. ⭐ **`Cn_*` 카드에 전원 상태를 함께 실을지** (신설 검토).  층 2 를 헤더에
   넣으면 **`POWER=4` 가 아닐 때의 값이 전 채널 ~0 V**(p.77)라 `BIAS`·전원 꺼진
   프레임의 카드가 "전 채널 고장" 으로 남는다 — 로그의 `power` 열에 해당하는
   것이 헤더에도 필요하다.  **D3 과 함께 정할 것.**

### ✅ 작업 E — `CTRLnCFG` 를 ACF 경로에서 파생 **완료 (2026-08-29)**

**규격이 먼저 섰고(v1.8) 코드가 뒤따랐다.**  구현 자리와 판단은 위
[작업 E 완료](#-작업-e--ctrlncfg-파생-완료-2026-08-29) 절과 [DevNote 5장](DevNote.md) 이다.
아래는 착수 시점의 지시이고, **딸림 넷은 다 처리했다** — ① 문서 파일명 인용
(줄바꿈에 걸려 grep 이 놓친 `test_ini_cards.py` 한 자리 포함) ② `ics_sim.ini`
예시 주석 ③ `test_raw_header.py` 픽스처 — ⚠️ **깨지지 않았다**: 이 브랜치의
픽스처는 이미 확장자 없는 값이었고(`main` 쪽 사본이 낡아 있었을 뿐이다),
파생은 `ics_archon` 에만 있어 `ics_sim` 시험을 지나간다 ④ 견본 바이트 대사
(`test_raw_draft.py`) 통과.

**할 일** -- `[archon] acf_mk`/`acf_nt`(경로 전체)에서 **폴더와 확장자를 떼어**
`CTRL1CFG`/`CTRL2CFG` 를 채운다.

    [archon] acf_mk = ~/AIC/Config/acf/KMTC_SCI_101_STA0284_R2608_MK.acf
                   -> CTRL1CFG = 'KMTC_SCI_101_STA0284_R2608_MK'

⭐ **`.acf` 와 `.cfg` 일 때만 뗀다** (운영자 확정).  범용 `splitext` 금지 --
**판 번호에 점이 들어간다**(`…_R2609.1.acf`).  확장자 없는 경로를 받으면
`splitext` 가 `.1` 을 먹어 판 번호가 깨진다:

    stem = (name[:-4] if name.lower().endswith(('.acf', '.cfg')) else name)

⚠️ **`ics_sim` 은 한 줄도 고치지 않는다** (규약 2).  값은
`ini` -> `ics_sim/config.py:835` -> `ControllersCfg.ctrl1_cfg` ->
`overrides()`(227) -> `sequencer.py:896` -> `rawhdr.controller_header()` ->
`rawcards.py:97` 로 흐른다 -- **그 사슬은 읽기만 하고**, `ics_archon` 이
`cfg.controllers.ctrl1_cfg` 를 **미리 채워** 넣는다.  자리 후보 둘:
`ics_archon/app.py:66`(`super().__init__(cfg)` 앞) 또는
`ics_archon/__main__.py:72·82`(두 설정을 나란히 로드하는 곳).

⚠️ **함께 볼 것** -- `ics_archon/config.py:557` 의 `_HEADER_INI_FIELDS` 가
`ctrl1_cfg` 를 **손편집 ini 값**으로 등재해 기동 ASCII 검사를 건다.  파생으로
바꾸면 그 목록도 손봐야 하고, **ini 에 값이 이미 있으면 덮을지**를 정해야 한다.

**딸림 -- 이 브랜치에만 있어서 `main` 에서 못 고친 자리:**

1. ⚠️ **문서 경로 인용 18곳** -- v1.8 판올림으로 파일명이 바뀌었다.  전수는:

       git grep -n "Specification_v1\.7\|Converter_v1\.14\|Identity_v0\.6"

   `_vendor/` 는 **생성물**이므로 원천(`ics_sim/`)을 고치고
   `python tools/sync_vendor.py` 를 돌린다 -- 손으로 고치면 `test_vendor.py` 실패.
2. `ics_sim/ics_sim.ini` 의 `ctrl1_cfg`/`ctrl2_cfg` 예시 주석(`.acf` 붙어 있다).
3. ⚠️ **`ics_sim/tests/test_raw_header.py` 픽스처가 깨진다** -- 지금
   `== 'KMTA_SCI_101_R2609.1'` 를 단정하는데, 파생을 넣으면 입력이 경로가 된다.
4. **검증** -- `ics_sim/tests/test_raw_draft.py`(견본 바이트 대사)는 **이 브랜치에만
   있다**.  견본 pair 가 `main` 에서 바뀌었으므로 **머지 뒤 반드시 돌릴 것.**

### 작업 D — `icg_archon` (별개 프로그램, 착수 미정)

층 3(`sensors()` 의 `ICG RTD` 계통)이 **`ics_archon` 소관이 아니다**(운영자
2026-08-27).  그때까지 `backend.sensors()` 는 빈 dict 이고 HK 카드 7장은
sentinel 이다.  **해독 규칙은 실측으로 다 확정해 뒀다** -- 위 "층 3" 세 절
(대응 표 · 진공 `Alive` 규칙 · 실측 로그 판정).  다시 조사하지 말 것.

착수할 때 정할 것: **D1 -- `icg_archon` → `ics_archon` HK 전달 경로.**  후보 셋
(IMPv2 메시지 / 파일 / 공유 상태)이고 각각 걸림돌이 있다.  어느 쪽이든 **"이 값이
몇 초 전 것인가" 를 함께 실어야** 한다 -- 없으면 `Alive` 로 잡은 신선도가 전달
계층에서 다시 사라진다.

⭐ **`ics_archon` 쪽에 본보기가 생겼다** (2026-08-28) — `monitor.py` 의
`age_ms`/`fresh`/`event` 열이 정확히 그 문제(값의 나이와 신선도를 함께 싣기)를
푼 것이다.  `icg_archon` 도 같은 형태로 만들면 두 기록을 나란히 놓을 수 있다.

### 운영자 몫 (실기)

1. **`KMTK_GUI_162_STA0201_R2609.acf` 를 guide 유닛에 올린다** (`APPLYALL`)
   -- 저장소만 고친 상태다.  ⚠️ 구 `R0827_for1259_rtd9cal` 과 **내용은 같다**
   (이름만 규칙에 맞췄다) -- 이미 올렸다면 다시 올릴 필요 없다.
2. 실험실 스크립트들의 `UNIT_ACF` 를 **새 파일명으로** 고친다 --
   `archon_kmtnet_guide_tvm_v0.9….py` · `modtm_*.py` · `tvm_gui_goff_v0.7….py`.
   (`__ref_archon_control/` 은 참고 원본 보관용이라 여기서 고치지 않았다.)
3. 다음 감시 로그로 **CCD 채널이 −30 아래를 읽는지** 확인 -- 종전 설정이면
   한계 밖이라 못 읽는다.
4. ⭐ **벤치 설치본 ini 에 감시 키를 넣는다** -- `~/AIC/Config/ics_archon.ini`
   는 저장소 사본이 아니다.  `monitor`/`monitor_interval`/`monitor_log` 가
   없으면 **코드 기본값(켬 · 20초 · `~/AIC/log`)** 으로 돈다 -- 그 자체는
   맞지만, **`mkdir -p ~/AIC/log` 는 해 두는 편이 낫다**(못 만들면 감시를 아예
   안 건다).
5. ⭐ **`[node] observatory = TESTBED` 는 여전히 기동을 거부한다** (D-017) --
   벤치 ini 를 `KASI` 로, `[site.testbed]` -> `[site.kasi]` 로.  **이걸 안 하면
   벤치에서 아무것도 안 돈다.**

### 낮은 우선순위

- `__version__` 을 언제 `0.1.0` 으로 올릴지 — 로드맵이 "검토사항 A 처리 완료"
  를 v0.1 로 잡아 뒀는데 이번 작업은 그것이 아니라 **그대로 `0.0.0` 에 두고
  `__build_date__` 만 올렸다**(`ICSBUILD` 는 일시로 갈린다).  목 판단 사항.
- 진공 응답 **10번째 글자**가 무해한지 STATUS 원문으로 확인 (실측 658행에서는
  무해했다 -- 응답이 항상 `x.xxe-04` 8자).
- ~~guide 8자리 자리 표(**OI-19**)~~ -- ✅ **종결 (2026-08-30)**: raw spec
  **v1.9 가 guide 장(9·10장)을 신설**하며 자리 표를 **10.4절**에 수록했다
  (운영자 확정 2026-08-29 방침대로 science 와 분리).  자리 표의 근거는
  `BACKPLANE_TEMP` + MOD3·4·5·6·7·9·10 — 근거 둘(guide ACF `[SYSTEM]` ·
  `modtm_gui_*.py`)이 일치하고 시험이 못박고 있다.  첫 guide 구동 때 STATUS
  재확인만 남는다.  ⏳ **X overscan 쪽은 따로 남았다** — 저장되는 528 이
  시퀀서가 읽는 601 중 **어느 구간인가**(P-k)는 이제 **guide OI-20**(규격
  10.6절)로 등재돼 실측 대기다 (⚠️ 2026-09-01 정정 -- 종전 이 줄이 적은
  `OI-21` 은 "추가 9행·칩 방위" 항목이라 다른 물음이다).  ⭐ 데이터시트
  대응으로 **앞 528** 이 거의 확정됐다 -- `acf/README.md`.
- `field_order_problems()` 는 science 10자리 기준이라 **guide 유닛에 probe 를
  돌리면 어긋남으로 보고된다** -- guide 규격이 나오면 자리 표를 유닛 종류로 가를 것.
  같은 이유로 **감시 열 이름(`T1..T10`)도 guide 에서는 달라야 한다** --
  `rawhdr.TEMP_MOD_LABELS` 가 science 표이기 때문이다.

## ▶ 다음 세션이 먼저 알아야 할 것 (2026-08-26 마감 시점)

**전부 커밋·푸시됐고 태그(`raw-spec-v1.6`)도 붙었다.**

| 어디 | 상태 |
|---|---|
| `main` | `6d9c137` raw spec **v1.6** 발행 (규격·견본·원장·통합문서·D-019). origin 동기 |
| `ics-archon-v1.0-build` | main 머지 + v1.5·v1.6 코드 반영 완료 **+ v1.6 전수 검사 반영**(미반영 4건·표류 다수). ⚠️ **전수 검사분은 아직 커밋·푸시 전이다** |

⚠️ **남은 것 둘** (1·2 는 이 세션에서 닫았다)

1. ~~**`origin` 푸시**~~ — **완료 (2026-08-26).** `main`·브랜치·태그 전부 올렸다.
2. ~~**`raw-spec-v1.6` 태그**~~ — **완료 (2026-08-26).** `6d9c137`(main 의 v1.6 발행 커밋)에 붙였고 구판 `raw-spec-v1.5` 는 보존 방침대로 지웠다(origin 포함). v1.5 태그가 `13e02b2` 에 붙었던 선례대로 **규격 문서가 완성된 main 커밋**을 판의 마지막으로 본다 — 그것을 머지한 브랜치 커밋이 아니다. 판↔커밋 연결은 `raw_fits_spec/SMC_CLAUDE.md` 표에 남겼다.
3. **벤치 설치본 ini** — `[node] observatory = TESTBED` 는 이제 **기동을 거부**한다(D-017). `KASI` 로 고치고 `[site.testbed]` → `[site.kasi]`. **이걸 안 하면 벤치에서 아무것도 안 돈다.**
4. **converter (LEECU 소관)** — `KMTT`→`KMTK` 정규식 · `ORIGNAME`→`EXPID` · `CHMAP` 4자 토큰 · HK 4장 폐지 · `Cn_*` 구분자 `|`. 전부 C-항목으로 등재돼 있다(통합 문서 v0.6). **안 고치면 KASI 자료가 짝 탐색에 안 걸리고 재저장 필터가 죽는다.**

**규격 v1.6 이 코드에 다 내려왔는지 다시 보고 싶으면** — 아래 "raw spec v1.6 반영" 절의 표가 자리별 대조표이고, 바로 뒤의 **"전수 검사"** 절이 1차 반영에서 빠졌던 넷이다. 기계 검증은 `ics_sim/tests/test_raw_draft.py`(견본 바이트 재현) · `ics_archon/tests/test_fitswrite.py`(카드 이미지) · `ics_archon/tests/test_labtest_spec_copy.py`(사본 셋 표류 — **상수만이 아니라 동작도**)가 한다.

## ▶ 이어서 시작하는 자리

| 순서 | 할 일 |
|---|---|
| **1** | ~~`ics_archon` v0.0 작성~~ **완료 (2026-08-23)**, ~~커밋~~ **완료 (2026-08-24, `ecf3487`+`6a94e57`)** |
| **1.5** | ~~작업 1(병렬 독출) · 작업 2(F1~F12)~~ **완료·커밋 (2026-08-24, `6cfc3c0`)** — 아래 "작업 1·2" 절 |
| **1.6** | ~~raw spec v1.5 반영~~ **완료 (2026-08-26)** — `main` 머지 + 전 계층 정합.  위 "raw spec v1.5 반영" 절 |
| **1.65** | ~~raw spec **v1.6** 반영~~ **완료 (2026-08-26)** — `ORIGNAME`→`EXPID` · `Cn_*` 구분자·sentinel · 카드 폭 규범.  위 "raw spec v1.6 반영" 절 |
| **1.66** | ~~v1.6 **전수 검사**~~ **완료 (2026-08-26)** — 반영이 안 닿았던 넷(labtest 폭 규범 · 전 자리 결측 자리 수 · astropy `CONTINUE` · 매니페스트)과 문서 표류.  위 "전수 검사" 절 · DevNote 11.30.  ⚠️ **커밋·푸시 전** |
| **1.68** | ~~`origin` 푸시 + `raw-spec-v1.6` 태그~~ **완료 (2026-08-26)** — `main` `6d9c137` · 브랜치 `98fd91c` · 태그 `raw-spec-v1.6` 전부 origin 반영 |
| **1.8** | ~~**층 1·2 텔레메트리 감시·기록**~~ **완료 (2026-08-28)** — `archon/monitor.py` 신설 · D4 · D5 · labtest v1.3.4 이식(프레임 시한·진단 덤프·`TIMER`).  위 "층 1·2 감시·기록 구현" 절 |
| **1.7** | ⏳ **관측 스크립트 첫 구동 결과 판정** — 위 "지금 진행 중인 것".  로그가 오면 그것부터.  ⚠️ **벤치 ini 의 `observatory` 를 `KASI` 로 먼저 고쳐야 기동한다** |
| **2** | **다듬기** — "검토사항 A"(실기 없이 되는 것)를 처리한다 → `v0.1`. ⚠️ **결정사항·P1·P2 는 승인 대기가 아니다** — 아래 "남은 판단은 실기 시험에서 하나씩" (목 확정 2026-08-24) |
| **3** | **시험 결과 반영** — labtest 실기 구동 결과 + `ics_sim` 시험 결과로 디버깅·업데이트. "검토사항 B" 가 그 목록이다. **1·2 와 병행이며 이것을 기다리지 않는다** |
| **4** | **main 합류** — **v0 완성 또는 v1 즈음, 진행하면서 판단**(목 2026-08-23). 미리 정해진 시점은 없다. 방식은 `--no-ff` 거품 머지. ⚠️ **합류할 때 저장소 루트 `README.md` 에 [`ics_archon/INSTALL.md`](INSTALL.md) 링크를 넣는다** (목 2026-08-24 — 루트는 Leecu 영역이라 그때 함께) |
| **5** | **guide 계통** — guide raw 규격이 정해진 뒤 착수.  `scr_labtest/…v1.3.smallbuf.py` 가 small buffer 주소 지정 참고 코드다(그 자체는 science 스크립트다) |

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
| **F5** | ✅ **종결 (2026-08-29, 실측)** | FETCH 상한을 `[archon] fetch_timeout` 으로 뺐고, `frame_timeout` 과 어긋나면 기동에서 알린다.  ⭐ 값을 `30` 으로 확정했다가(실측 약 5초, 6배 여유) **2026-09-02 → `10`** — 잠금 > 주기(13.27초)면 다음 장이 덮인다(DevNote 10.6), 벤치 실측 3.2~3.5초라 2.9배 여유.  종전 유도값 344초는 실측의 **100배**여서, 링크가 죽어도 25초 창이 터진 한참 뒤까지 매달렸다 — 이제 기동 검사가 그 조합을 알린다 | `config._cross_checks` · `validate` |
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

### 정책 미정 — 실기 시험에서 판단한다

**P2 — STOP 을 걸었을 때의 `EXPTIME`. 실기 확인 뒤에 정한다 (목 2026-08-24).**
적분은 컨트롤러가 재므로(결정사항 3) `STOP` 은 적분을 자르지 못하고 셔터만
강제로 닫는다.  그런데 헤더는 `state.effective_exptime` = **요청값**을 싣는다
(`BIAS` 만 0) — 즉 **실제 개방 시간은 그보다 짧은데 파일만 봐서는 알 수 없다.**
셋 중 하나여야 한다: ① 그대로 둔다 ② 표시를 남긴다(헤더 카드 추가 = **raw spec
개정 필요**) ③ `FASTLOADPARAM IntMS 0`(매뉴얼 p.52)이 즉시 반영되면 **진짜로
자를 수 있어** 문제가 사라진다.  **③ 이 되는지가 먼저이므로 실기 확인 항목으로
넘겼다** (`tools/probe_archon.py` 3단계 이후).

**P1 — ABORT 와 노출 번호.** 실측된 비대칭: 같은 프로세스에서 ABORT 하면 번호를
**재사용**하는데, 프로그램을 재시작하면 그 번호를 **건너뛴다**(영구 구멍). 중단
국면에서 파일은 항상 0개였고, `GO n` 의 1번 프레임 파일은 남았다. **어느 쪽이
규범인지 정해진 바 없다** — 정하고 나서 시험으로 못박아야 한다.  이번 작업에서는
**건드리지 않았다** (정책이 정해지기 전에 코드를 바꾸면 그 자체가 결정이 된다).


## ▶ 남은 판단은 **실기 시험에서 하나씩** (목 확정 2026-08-24)

> 실제 시험 진행하면서 하나씩 판단하여 업데이트 해나가자.

**그래서 아래 "결정사항"·"검토사항"·"정책 미정" 은 착수를 막는 승인 대기가
아니다.**  다음 세션은 이것들을 기다리지 말고 진행하고, **시험 결과가 나오는
대로 해당 항목을 닫아 이 문서를 갱신한다.**

어느 시험이 무엇을 닫는지 미리 짝지어 둔다 — 결과가 왔을 때 무엇을 적어야
하는지 찾아 헤매지 않도록.

| 시험 | 그때 닫히는 것 |
|---|---|
| **probe 1단계** (읽기 전용) | **규격 5.6.1절 자리 표의 실물 정합** (10자리 · 자리별 이름표를 찍어 눈으로 대조한다) · AD 슬롯 5~8 가정 · `POWER`/`OVERHEAT`/`POWERGOOD` 실제 보고 여부(F2 의 PROVISIONAL) |
| **probe 2단계** (ACF 대조) | `param_intms_slot`/`param_exposures_slot` · 결정 12(`RDMODE` 유도) |
| **probe 3단계** (프레임 1장) | ✅ **독출 시간·FETCH 는 벤치 실측으로 확정됐다** (2026-08-29 운영자 자료 → **2026-09-01 두 유닛 실측**: 368 행/초 · readout 12.77초 · 주기 13.27초 · FETCH 3.2~3.5초 · `fetch_timeout=10`).  남은 것: **두 컨트롤러 시차** -> `acq_per_frame`/`acq_skew_warn` 기본값 · 픽셀 좌우 배치 · ⚠️ **2대 동시 FETCH 의 실제 속도**(GbE 를 나눠 쓰면 느려진다 — 7.5초를 넘으면 `fetch_buffers` 를 3으로.  ⚠️ 2026-09-02 정정: 7.5 는 주기 12초·저장 1초 기준이었다; 주기 13.27·저장 1.2 로는 ~8.6초이고, 무엇보다 `fetch_timeout=10` 이 잠금 상한이라 그 위로는 어차피 못 간다 — DevNote 10.6) |
| **4단계** (본편, 1유닛) | 결정 5(`erase` 두 대) · 6(`close_shutter`) · ~~15(`LOCKn`)~~ ✅ · ~~검토 A5~~ ✅ (2026-09-01 실기 종결 — DevNote 10장) |
| **5단계** (2대 + OBSAgent) | `acq_per_frame` **최종 판단** · 1.8초/0.9초/25초 창 3종 |
| **STOP 시험** | **P2** — `FASTLOADPARAM IntMS 0`(p.52)이 즉시 반영되면 `EXPTIME` 문제 자체가 사라진다.  안 되면 ①그대로/②헤더 카드(= raw spec 개정) 중 선택 |
| **ABORT 시험** | **P1** — 같은 프로세스 재사용 vs 재시작 건너뜀, 어느 쪽이 규범인지 |
| **labtest 실기 실행** (목 몫) | 결정 7·8 **역이식 여부** — labtest 가 실기에서 문제없이 돌면 급하지 않고, 걸리면 그 자리가 근거가 된다 |

**갱신할 때**: 닫힌 항목은 표에서 지우지 말고 **결과를 적어 남긴다**(왜 그렇게
정했는지가 다음 판의 근거다).  경위가 길면 DevNote 11.x 로, 결과·실행법은
README 로 나눈다.

## 결정사항 — v0.0 에서 내가 정한 것

되돌리기 쉬운 순서로 적었다. **1~3 이 구조적 판단**이고 나머지는 국소적이다.

| # | 정한 것 | 왜 | 되돌릴 때 |
|---|---|---|---|
| 1 | `ics_sim` 을 **가져다 쓴다** — **손으로 관리하는 사본은 없다.** `_simpath` + `register_backend` | 기계 사본이 이미 둘이라 세 번째를 만들면 raw spec 5장 개정 때 어긋난 하나를 놓친다 | 사본을 뜨면 `_simpath` 를 지우고 import 를 상대경로로 |
| 1-1 | 배포용 **내장본 `_vendor/ics_sim/`** 은 둔다 — **`sync_vendor.py` 가 만드는 생성물** (목 지시 2026-08-23) | `ics_archon/` 하나만 두고 돌릴 수 있어야 한다.  손으로 안 고치므로 1번의 "사본을 만들지 않는다" 와 어긋나지 않는다 — 표류는 `test_vendor.py` 가 잡는다 | 위 규약 1번 참조 |
| 2 | 저장을 **원시 바이트**로 쓴다 (astropy 아님) | ① 취득 경로에 astropy 의존을 넣지 않는다 ② 344 MiB 사본을 안 만든다(제자리 byteswap) ③ 데이터부 2880B 패딩을 명시 | `ics_sim.fitsout.write_dummy_fits` 로 갈면 된다 (계약은 같다) |
| 3 | **적분은 컨트롤러가 잰다.** 시퀀서 카운트다운은 알림 | `IntMS`+`LOADPARAMS` 가 적분·셔터·독출을 다 몬다. 호스트가 재려면 트리거를 직접 흔들어야 하고 그건 검증된 경로가 아니다 | — (하드웨어 사실) |
| 4 | DARK/BIAS 노출을 **`readout()` 첫머리**에서 건다 | 시퀀서가 `_integrate_dark` 에서 백엔드를 **부르지 않는다** — 트리거를 걸 자리가 거기뿐이다. ✅ **적분 시간은 `begin_exposure()` 훅으로 미리 받는다** (계약에 신설, `ecf3487`) — 그래서 `IntMS` 를 컨트롤러에 실을 수 있다(결정 3) | 트리거 자리는 하드웨어 사실이라 그대로다. ⚠️ **`_dark_seconds` 의 `None`(못 받음)과 `0.0`(BIAS, 정상)을 겹치지 말 것** — 겹쳤다가 BIAS 마다 거짓 경고가 났다(2026-08-29 정정) |
| 5 | `erase(ccd)` 를 **두 대 다** flush — ⛔ **다만 기본값은 `false`(안 한다)** (운영자 확정 2026-08-29) | *"이제는 clock 을 개선해서 별도 erase 를 하지 않고 바로 노출을 시작한다"*. 종전 기본값 `true` 는 **clock 개선 전 전제**였다. labtest 도 1년 실사용을 `bFullFlush=False` 로 했다. ⚠️ 켜면 노출마다 **독출 1회분(11.3초)** 이 더 붙어 주기가 12.4 → 23.7초 (2026-09-01 실측으로 갱신: 프레임 하나 = 13.27초(독출 12.77 + 사강 0.5, DevNote 10.4)라 13.27 → 약 26.5초, 추정) | `full_flush_on_erase=true` 로 켜면 두 대 다 비운다 (그 규칙은 유효하다) |
| 6 | `close_shutter()` 는 **적분 중일 때만** `TRIGOUTFORCE=1` | 정상 경로에서는 이미 닫혀 있다. 독출 중에 `APPLYSYSTEM` 을 보내지 않으려는 것 | — |
| 7 | 참조번호를 **보내기 전에** 올린다 | 시한 초과 뒤 늦은 응답이 다음 명령 번호와 맞아떨어지는 일이 원리상 없어진다 (labtest 회귀 1번의 근본 처방) | ⛔ **labtest 역이식은 안 한다** (운영자 확정 2026-08-29) — 본편 전용 |
| 8 | `?xx` 오류 응답을 구분하고, 읽기 버퍼를 **하나로** 둔다 | labtest 는 `<xx` 만 대조해 컨트롤러의 거부를 프레이밍 오류로 뭉갰다. 그리고 `archoncmd` 가 `msgbuf` 를 안 봐서 이진 꼬리를 놓칠 구멍이 있었다 | ⛔ **labtest 역이식은 안 한다** (운영자 확정 2026-08-29) — 본편 전용 |
| 9 | `progress_step = 0` 은 "**값이 바뀔 때마다**" | 폴링이 라인 진행보다 빠르면 같은 값을 되풀이 보낸다 | — |
| 10 | `.part` 로 쓰고 `os.replace` | 중간에 죽은 반쪽 파일이 최종 이름을 차지하면 D-016 선검사가 그 번호를 점유된 것으로 본다 | — |
| 11 | `flash_led` 는 **하드웨어를 만지지 않는다** | 실기 LED 배선이 미확정이다. 트리거를 임의로 흔들면 셔터가 열린다 | 배선 확정 후 구현 |
| 12 | `RDMODE` 를 ACF 이름에서 유도 (ini 가 이긴다) | 컨트롤러는 적용 ACF 이름을 보고하지 않는다 (p.54) | ini 에 적으면 그쪽이 이긴다 |
| 13 | 기본 백엔드 = `archon` (ini 가 **안 적었을 때만**) | `python -m ics_archon` 이 조용히 시뮬로 도는 것을 막는다 | `[hardware] backend = sim` 을 적으면 존중한다 |
| 14 | 프레임 상태를 **`FrameTicket`** 으로 프레임이 들고 간다 (저장 대기열 FIFO) | 저장은 `write_delay` 뒤 백그라운드다 — 컨트롤러 필드에 두면 뒤 프레임이 앞 프레임의 값을 덮는다(엉뚱한 프레임 대기 · 이중 노출). `ics_sim` 이 같은 부류를 두 번 겪었다(12.10 · 11.20 critical) | — |
| 14-1 | **이미 있는 파일은 덮지 않는다** (`fitswrite.write_frame`) — **목 승인 2026-08-23** | D-016 선검사와 쓰기 사이에 `write_delay`+저장시간만큼 틈이 있고, 그 틈에 누가 그 경로에 파일을 두면 `os.replace` 가 말없이 지운다. 둘 중 하나를 잃어야 하면 **새 프레임을 버리는 쪽**이 맞다 — 옛 프레임은 이미 아카이브에 들어갔을 수 있고 되돌릴 수 없는데, 새 프레임은 다시 찍을 수 있고 오류가 크게 뜬다. **이름은 여전히 시퀀서가 정한다** (백엔드는 "덮지 않겠다" 고만 한다) | — |
| 15 | fetch 중 **`LOCKn` 으로 버퍼를 잠근다**(`lock_buffer=true`) + fetch 앞 프레임 번호 대조 | ⭐ **실측 여유가 ~6초다** (2026-08-29) — FETCH 는 `IDLE`+3.4~8.4초에 끝나고 그 버퍼 재사용은 ~14.7초다 (2026-09-01 숫자 갱신: FETCH 3.2~3.5초라 `IDLE`+~6.9초에 끝나고, 재사용은 빨라도 프레임 주기 13.27초 뒤 — DevNote 10.4). `BIAS` 연속이 가장 얇다. **매뉴얼 p.71 이 `LOCK` 을 통상 경로로 적어 두었다** (2026-08-30) — *"새 프레임이 있으면 호스트는 LOCK 을 내려 그 버퍼가 덮이는 것을 막고 FETCH 한다"*. ⚠️ **다만 판정이 아니라 가설의 강도다** — 매뉴얼은 2021-02-23 판이고 **현행 FW 와 양방향으로 어긋날 수 있다**(운영자 2026-08-30, DevNote 8.7). 종전에 기본을 `true` 로 둔 이유로 적었던 "더 안전한 쪽" 은 실기 전 판단이었다 — 지금은 **값이 있어서**다(대가 0·지킬 구간 실재, 10.6). ⚠️ 다만 엔진은 *"다음 **잠기지 않은** 버퍼"* 를 잡으므로 **science(BIGBUF, 2개)에서는 하나를 잠그면 엔진에 하나만 남는다** — labtest 가 뺀 이유일 수 있다(가설 H3). ✅ **2026-09-01 실기 종결** — 두 FW 15/15 반영·대가 0·`nolock` 덮임 2/2·H3 는 엔진이 쓰던 버퍼를 재사용(감속 0). **`true` 확정**, DevNote 10.6 | `lock_buffer=false` 로 끄면 labtest 와 같아진다(대조는 남고, `recheck_after_fetch` 가 fetch 중 창까지 본다) |
| 18 | ⭐ **`LOCKn` 이 먹었는지를 `RBUF`/`WBUF` 로 관측한다** (왕복 0) | 매뉴얼은 판정 근거가 아니므로(DevNote 8.7) **실기가 답하게** 한다. fetch 앞 덮임 대조가 **이미 읽는 `FRAME`** 안에 `RBUF`(*"locked for reading"*, p.50)가 있었는데 버리고 있었다. 관측값은 **이미 있는 `FETCH` 로그 줄에 얹어** 정상 취득에 새 줄을 안 늘린다. ⚠️ 한 방향으로만 결정적(안 맞아도 `RBUF` 미구현일 수 있다) — ⭐ 그래서 **거동**인 `WBUF` 이동을 함께 잰다. ✅ **실기 (2026-09-01)**: 두 FW 15/15 반영, `WBUF` 가 잠긴 버퍼를 피하는 것도 관측 (DevNote 10.4) | 관측일 뿐이라 되돌릴 것이 없다. 경고가 거슬리면 `lock_buffer=false` |
| 17 | **fetch 뒤 재대조**(`[archon] recheck_after_fetch`, 기본 **`true`**) + **`POWERON` 에서 저장 표 폐기** | fetch 앞 대조는 **직전 한 순간**만 본다 — fetch 자체가 3.2~3.5초라 그 사이에 덮이면 **앞뒤가 다른 누더기**가 길이·헤더 정상으로 나와 로그에 안 남는다. ⭐ **`lock_buffer=false` 인 경우 필요할 수 있다** — `LOCKn` 을 끄면 그 창을 막는 것이 없다. 잠겨 있으면 **절대 안 걸리고** 왕복 하나(ms)만 는다. ⭐ A/B 실험(2026-08-30 설계, 09-01 종결)의 계측값이었다(누더기를 조용히 쓰는 대신 크게 운다) — 지금은 `lock_buffer=false` 로 돌릴 때의 유일한 방어라는 값만 남는다 (DevNote 10.6). ⚠️ **둘 다 끄면 기동 교차검사가 알린다** | `recheck_after_fetch = false`. ⚠️ `lock_buffer` 와 **함께 끄지 말 것** |
| 16 | **호스트 수신·저장 버퍼를 링으로** (`[archon] fetch_buffers`, 기본 **2**) + `wrote_window` 선언과 **기동 교차검사** | 종전에는 프레임마다 344 MiB 를 새로 잡고 `_store` 태스크 수에 제한이 없어 **저장이 밀리면 메모리가 조용히 늘었다.** 링은 ① 상한 `N×344 MiB` ② 재사용(할당 0.81초 절약) ③ **역압** — 다 차면 기다리고 그 횟수를 센다(`buf_waits`). ⭐ **`N = ceil((창 − write_delay) / 주기)`** 라 창과 짝이다: 25초 창엔 2개, **30초면 3개** | `fetch_buffers` 를 올리면 된다. 벤치 RAM 32 GB 이므로 3개(2.2 GB)도 여유가 크다 |

## 아직 없는 것 (v0.0) — README 에서 옮겨 왔다 (2026-08-30)

- ~~**듀어·환경 HK** (`sensors()`)~~ — ✅ **경로가 생겼다 (2026-08-31)**:
  `icg_archon` 이 guide 유닛 RTD·진공과 Radionode 를 읽어 1분 주기 스냅샷
  (`hk_latest.G.json`)을 남기고, `sensors()` 가 그것을 신선도 판정과 함께
  읽는다 (`[archon] hk_latest`).  icg 가 안 돌면 종전대로 sentinel.
- **LED 프로젝터** (`flash_led`) — 실기 배선이 미확정이라 값만 기억하고
  하드웨어를 만지지 않는다.
- **guide 계통** — guide raw 규격이 **v1.9 에서 생겼다** (9·10장 신설,
  2026-08-30).  착수 시 `DATASRC='ARCHON_GUIDE'` + `CTRL1xx` 한 벌 규약
  (raw spec 5.5절) + 기하를 guide 크기(4224×1033)로 + `C1_TEMP`/`C1_VOLT`/
  `C1_CURR` 8자리(10.4절).  **참고 코드**: `scr_labtest/…v1.3.smallbuf.py` 는 구버전
  science 유닛을 구동하던 코드로, smallbuf로 구성되는 guide 유닛 제어용 코드
  작성 시 참고한다.  다만 **bigbuf 스크립트의 코드로도 smallbuf 구성 유닛의
  동작이 가능할 수도 있으니** 그쪽도 참조할 것 — FETCH 주소를 `BUFnBASE` 에서
  읽어 설계상 구성 무관이다(실기 검증은 첫 guide 구동 때).
- **binning** (`BIN` 명령) — `ics_sim` 쪽도 스텁이다.
- **바이어스 측정값의 헤더 수록** (층 2) — 지금은 **로그만**이다.  헤더에 넣는
  것은 규격 개정 사안이고(32개 값이 카드 하나에 안 들어간다 — 8채널이 한 카드의
  한계), 갈래 둘과 계산이 `SMC_CLAUDE.md` "층 2" 절에 있다.
- **`FETCHLOG` 드레인** — 안 쓰기로 확정했다.  `LOG=n` 한 열만 남긴다.  승격
  기준(항목이 모듈·채널 수준의 정체를 담는가)은 `probe_archon` 1단계로 한 번
  보고 판단한다.

## 검토사항

### A. 실기 없이 처리할 수 있는 것 (2단계) — ✅ **전량 종결 (2026-08-30)**

일곱 중 넷 완료(A-2·3·6·7) · 둘 닫힘(A-1 불필요 · A-4 폐기) · A-5 는 판단
①③ 확정되고 남은 ②는 **분류가 틀려 B 로 옮겼다**.  ⚠️ **실기 없이 더 할 수 있는
것이 이 목록에 남아 있지 않다.**

1. ~~**메모리 — 스트리밍 저장**~~ — ⛔ **닫혔다 (2026-08-29, 실측).**
   *"25초 창에 여유가 없으면"* 이 조건이었는데 **여유가 있다**:
   창 예산이 `write_delay 3.4 + FETCH 5 + byteswap 0.1 + 저장 1 = 9.5초`,
   **남는 여유 15.5초** (2026-09-01 실측으로는 `3.4 + 3.5 + 0.1 + 1.2 = 8.2초`, 여유
   16.8초 — 결론 강화, DevNote 10.4).  복잡도만 늘리는 일이 된다.
   ⚠️ 대신 **호스트 버퍼 링**이 들어갔다 (결정사항 16) — 스트리밍과 목적이
   다르다: 겹치기가 아니라 **상한과 역압**이다.
   ⚠️ 이 항목을 닫으며 든 "걸림돌 셋" 중 *"블록 단위 byteswap 이 비싸다"* 는
   **틀렸다** — 1 KiB × 35만 번이 0.47초, 8 MiB 청크는 전체 한 번과 같은
   0.10초다.  재보지 않고 단정한 것이다.
2. ~~**`[readout]` 의 시뮬 파라미터가 archon 에서 무의미하다**~~ — ✅ **완료
   (2026-08-28).** `config.validate()` 가 `pctread_start/step/tick` 이
   **기본값과 다를 때만** 알린다 (늘 외치면 배경 소음이 된다).
3. ~~**`base.py` 에 `begin_exposure()` 를 넣을지**~~ — ✅ **완료 (2026-08-24,
   `ecf3487`).**  계약(`base.py:46`) · 시퀀서 두 자리(`sequencer.py:531`·`673`) ·
   실기 구현(`backend.begin_exposure`) · 시험(`test_backend.py`)이 다 있다.
   **이 목록에서만 안 지워져 있었다** (2026-08-29 발견).
   ⚠️ 그 자리에서 결함 하나가 나왔다 — `_dark_seconds` 의 `0.0` 이 **"훅을 못
   받았다"** 와 **"BIAS 라 0초다"** 를 겸해서 **정상 BIAS 마다 거짓 경고**가 떴고,
   문구까지 *"시퀀서에 훅이 없다"*(사실이 아니다)였다.  `None` 으로 갈랐다.
4. ~~**labtest 역이식 3건**~~ — ⛔ **하지 않는다 (운영자 확정 2026-08-29).**
   *"labtest 로 역이식은 하지 않을거야.  ics_archon 에만 적용해줘"*.
   결정사항 7(참조번호 선증가) · 8(`?xx` 구분·읽기 버퍼 하나) · `BUFnLINES`
   진행률은 **`ics_archon` 에 이미 다 들어가 있고**(`protocol.py:181` ·
   `ArchonError.reply_error` · `parse.py:176`), labtest 는 **구판 방식 그대로
   둔다.**
   ⚠️ **그래서 labtest 와 본편의 프로토콜 층은 앞으로 갈린다** — 그것이 결함이
   아니라 **결정**이다.  labtest 는 1년 실사용으로 검증된 별개 도구이고,
   실기 투입 직전에 손대는 위험이 얻는 것보다 크다.  ⚠️ 갈리지 **않아야** 하는
   것은 규격 사본(`RAWCARDS`)뿐이고 그것은 `test_labtest_spec_copy.py` 가 지킨다.
5. ✅ **버퍼 수 대 저장 여유 — 실측으로 판단 완료 (2026-08-29).**
   여유는 **~6초**다: FETCH 가 `IDLE`+3.4~8.4초에 끝나는데 그 버퍼를 다시
   쓰는 것은 ~14.7초다 (2026-09-01 실측 갱신: FETCH 3.2~3.5초라 `IDLE`+~6.9초에
   끝나고, 재사용은 빨라도 프레임 주기 13.27초 뒤 — 여유 ~6.4초, DevNote 10.4).
   ⚠️ **아래 본문의 "프레임 ~40초" 는 가정이었고 실제 주기는 13.27초**(노출 0 +
   독출 12.77 + 사강 0.5; 2026-08-29 자료로는 12초)라 여유가 가정의 3분의 1이다 — 그래서
   `LOCKn`(결정 15)이 값을 한다.  판단 ①(`full_flush_on_erase`)은 **끄는 것으로
   확정**됐고(아래 결정 5), ③(스트리밍)은 위 1번에서 닫혔다.
   ⚠️ **남은 ②(`LOCKn` 을 실기에서 켜도 되는지)는 이 항목(A)이 아니라 B 다** --
   labtest 가 왜 뺐는지의 근거가 *"fetch debug"* 한 줄뿐이라 **실기에 걸어
   봐야** 답이 나온다.  **아래 B 로 옮겼다** (2026-08-30 분류 정정).

   *(아래는 v0.0 당시 기록 — 가정값이 섞여 있으니 위 실측을 먼저 볼 것)*

   ⚠️ **버퍼 수 대 저장 여유 — v0.0 에서 발견한 실제 제약.**
   BIGBUF=1 은 **버퍼가 2개**인데 노출 1회가 프레임 **2개**(flush + 취득)를
   만든다. 즉 **다음 노출이 이 프레임의 버퍼를 정확히 덮는다** — 저장이
   `write_delay` 뒤 백그라운드라 그 경합이 구조적으로 존재한다. 실기 값
   (프레임 ~40초 · `write_delay` 3.4초)이면 여유가 크지만 **독출 시간 실측이
   나오기 전에는 알 수 없다.** v0.0 이 넣은 것은 둘 — `LOCKn` 잠금과 fetch 앞
   프레임 번호 대조(어긋나면 저장 거부). 남은 판단: ① `full_flush_on_erase` 를
   끄면 프레임 소비가 절반이 된다 ② `LOCKn` 을 실기에서 켜도 되는지(labtest 가
   왜 뺐는지 근거가 "fetch debug" 한 줄뿐이다) ③ 스트리밍 저장(위 1번)이면
   잠금 시간이 짧아진다.
6. ~~**`ics_sim` 쪽 `hardware/archon.py` 스텁의 처지**~~ — ✅ **완료
   (2026-08-28).** 이미 `ics_archon` 을 가리키고 있었는데 **없는 파일을 가리키는
   경로**가 하나 있었다(`…labtest_v1.0.smallbuf.py`).  현행 이름으로 고치고
   `sync_vendor.py` 재실행.  같은 부류로 `ics_archon` 두 `__init__.py` 의
   "원형은 …v1.1.bigbuf.py" 도 고쳤다.
7. ⭐ **저장 자리 선검사** — ✅ **완료 (2026-08-28).** labtest v1.1.3 이 이미
   푼 문제였다. 위 "저장 자리를 기동에서 본다" 절.

### ✅ 프레임 번호 **되감김** — 발견하고 고쳤다 (2026-08-30)

운영자 지적: *"되감김도 실제로 많이 일어날 수 있는 경우이네, 특히 작은 센서
또는 고속 센서에서 짧은 노출 많이 줄 때는."*  맞다 — **guide 유닛이 정확히 그
경우**다(프레임 8.7 MB, 초점·시상 감시는 짧은 노출을 연달아 찍는다).

**두 자리가 번호의 단조 증가를 전제한다:**

    parse.py:200        if frame > prev and BUF{n}COMPLETE == 1:   # prev 보다 큰 것만
    controller.py:901   if prev >= 0 and mine.frame != prev + 1:   # 정확히 prev+1

**되감김 순간**(`prev` 가 최대값, 다음이 0)에 일어나는 일:

1. `next_frame()` 이 `frame > prev` 로 걸러 **새 프레임을 못 찾는다** → `None`
2. `wait_frame()` 이 계속 기다리다 **`frame_timeout`(300초)** 에 걸린다
3. `DMA WAIT TIMEOUT` 경로 → **그 노출이 실패**

⭐ **fail-closed 다** — 틀린 파일이 아니라 한 노출을 잃고 크게 운다.  조용한
오염은 아니다.  ⚠️ 다만 **"한 번 실패하고 끝" 이 아닐 수 있다** — `prev` 가
어떻게 갱신되느냐에 따라 되감김 이후로 계속 못 찾을 수 있고, 그러면 **재기동
전까지 취득이 멈춘다.**

**얼마나 자주인가** (⚠️ `BUFnFRAME` 폭 — **매뉴얼 전수 검색 결과 미상 확정**):

| 폭 | science (주기 12초 — 실측 13.27초로는 약 1.1배) | **guide** (짧은 노출 연속) |
|---|---|---|
| 16비트 (65,536) | 약 **9일** 연속 (13.27초면 약 10일) | 1초 주기 **18시간** · 0.5초 **9시간** (⚠️ 가정법 — guide 하한은 1.375초다, DevNote 9.13) |
| 32비트 | 사실상 무한 | 사실상 무한 |

science 도 9일이면 **한 관측 기간 안에 들어온다.**  재기동하면 리셋되겠지만
**재기동에 기대는 것은 설계가 아니다.**

**✅ 매뉴얼 확인 결과 (2026-08-30, 103쪽 전문 검색)**

| 찾은 것 | 결과 |
|---|---|
| `BUFnFRAME` 정의 (p.50) | `BUFnFRAME=d ; Buffer n frame number` — **폭 없음** |
| `wrap`·`rollover`·`overflow` | 문서 전체에 **한 번도 안 나온다** |
| 폭을 아는 자리 | `TIMER=x ; **64-bit**` · `BUFnTIMESTAMP=x ; **64-bit**` · `VCPU_OUTREGn ; **unsigned 16-bit**` · *"Counts and parameters are **20-bit**"*(p.64) · *"CDS counters are **16 bit**"*(p.69) · *"accumulators are **32 bits**"*(p.69) |

⭐ **매뉴얼은 폭을 아는 자리에 폭을 적어 두었다** — `BUFnFRAME` 에 안 적은 것은
"안 찾아본 것" 이 아니라 **문서가 정하지 않은 것**이다.  정황(백플레인이 32비트
soft processor / Rev H 는 64비트 ARM, p.15)은 32비트를 가리키고 그러면 12초 주기로
1,600년(13.27초면 약 1,800년)이라 사실상 닫히지만, ⚠️ **추론이지 문서가 아니다.**

**✅ 그래서 폭에 기대지 않는 방법으로 고쳤다**

크기 휴리스틱(*"`prev` 보다 훨씬 작으면 되감김"*)은 **쓰지 않았다** — 평소에도 옛
프레임을 담은 버퍼가 `prev` 보다 작아서 **매 프레임 오탐**이 난다.  대신 **변화**를
본다: 노출 직전에 세 버퍼 번호를 한 벌 찍어 두고(`FrameTicket.prev_frames`),
**새로 바뀌었는데 `prev` 보다 크지 않은** 완료 버퍼를 되감김으로 본다
(`parse.restarted_frame()`).  잡히면 크게 울고 기준을 재동기해 **그 프레임을
받는다** — 노출을 잃지 않는다.

⭐ **컨트롤러 재시작도 같은 코드로 잡힌다** (`REBOOT`·백플레인 전원 재투입 — ⚠️ `WARMBOOT`
와 CCD `POWERON` 은 카운터를 안 지운다, 2026-09-02 실측 DevNote 10.7.  되돌아가는 첫 값은
0 이 아니라 **1**).  자세한 것은 `DevNote.md` 8.3.

### ✅ `drop_tickets()` 가 죽어 있었다 — 배선했다 (2026-08-30)

    $ git grep -n "drop_tickets"
    controller.py:802:    def drop_tickets(self, why: str) -> int:     <- 정의뿐

**아무도 부르지 않는다** -- `power_on`·`power_off`·`connect` 어디서도.  즉
**전원을 껐다 켜도 저장 대기열이 안 비워진다.**  그 함수는 *"프레임이 끊겨
저장이 없을 것이 확실할 때 부른다"* 고 스스로 적어 두었는데 배선이 빠졌다.

⭐ **치명적이지는 않다** -- 표를 이름(`EXPID`)으로 집으므로 낡은 표는 안 집히고,
못 찾으면 저장을 안 한다(fail-closed).  낡은 표가 쌓여 진단 로그에 섞일 뿐이다.

**✅ 둘 다 넣었다** (운영자 지시 2026-08-30):

1. ✅ `drop_tickets()` 를 **`power_on()` 에 배선**했다 -- 전원이 내려간 사이의 프레임은
   다시 못 받는다.  ⚠️ **정정 (2026-09-02)**: 종전에 이유로 적은 "`POWERON` 은 새 프레임
   번호 세션의 시작" 은 틀렸다 — CCD `POWERON` 은 `BUFnFRAME` 을 리셋하지 않는다
   (DevNote 10.7).  버리는 이유는 번호가 아니라 자료가 아니라는 것이고, 배선은 그대로 옳다.
   ⏳ **재접속(`connect()`)은 안 걸었다** -- 링크만 잠깐 끊긴 경우에는 버퍼가 살아
   있어 아직 받을 수 있을지도 모른다.  *"확실히 못 받는다"* 가 아니어서 남겨 둔다.
2. ✅ **fetch 뒤 재대조**를 `[archon] recheck_after_fetch` **(기본 `true`)** 로
   넣었다.  ⭐ **`lock_buffer = false` 인 경우 필요할 수 있다** -- `LOCKn` 을 끄면
   fetch 5초 동안의 창을 막는 것이 아무것도 없다.  잠긴 버퍼는 안 바뀌므로
   `lock_buffer=true` 에서는 **절대 안 걸리고**, 왕복 하나(ms)만 는다.
   ⭐ **A/B 실험을 뜻있게 만든다** -- `--no-lock` 쪽이 누더기를 조용히 쓰는 대신
   **덮였다고 크게 운다.**
   ⚠️ **둘 다 끄면 기동 교차검사가 알린다** -- 그 조합은 그 창을 보는 것이 없다.

### 🔬 `LOCKn` A/B 실험 절차 (구 A-5 판단 ②, 2026-08-30 설계) — ⚠️ **종결 (2026-09-01~02)**

> ⚠️⚠️ **이 절차는 실기로 종결됐다 — 따르지 말 것.**  계측값(*"덮였나"*)이 죽고
> `tools/ics_archon_buftest.py` 2x2 로 바뀌었으며, 그 결과 **`lock_buffer = true` 종결**이다.
> 판정과 경위는 [DevNote 10장](DevNote.md), 결과는 [`archon_lock_fetch_report.md`](archon_lock_fetch_report.md).
> 아래는 **설계 이력**으로만 남긴다 — 미리 못박은 판정 기준이 어떻게 값을 했는지(10.10)의 근거다.


**가르려는 것은 둘이다** (운영자 2026-08-30): *"뭐가 잘 안 돼서 뺀 건가, 넣으나
빼나 영향이 없어서 뺀 건가."*

| | 가설 | 실기에서 보이는 것 |
|---|---|---|
| **H1** | `LOCK` 이 fetch 를 **방해했다** | FETCH 가 실패·거부(`?xx`)·타임아웃, 또는 눈에 띄게 느려짐 |
| **H2** | **영향이 없었고** 디버깅 중 변수를 줄이려 뺐다 | FETCH 시간·성공률이 양쪽 같음 → **켜는 쪽이 이득**(덮임 방지) |

⭐ **정황은 H2 쪽이다** — 주석이 *"remove to **fetch debug** on 2026-05-28"* 다.
`LOCK` 이 원인이었다면 "LOCK breaks fetch" 라고 썼을 것이다.  다만 정황일 뿐이다.

#### 1단계 — 단발 비교 (안전, `probe_archon` 3단계)

```bash
cd ~/AIC/ics_archon
python tools/probe_archon.py --host 10.0.0.13 --acf acf/<유닛>.acf --expose 0 --no-lock
python tools/probe_archon.py --host 10.0.0.13 --acf acf/<유닛>.acf --expose 0 --lock
```

⚠️ **두 실행의 차이가 그 플래그 하나뿐이어야 한다.**  같은 ACF·같은 노출·같은
유닛.  로그에 `lock_buffer = …` 와 `FETCH … [lock=…]` 이 찍히므로 나중에 어느
것이 어느 쪽인지 헷갈리지 않는다.

⭐ **`recheck_after_fetch` 는 켠 채로 둔다** (기본 `true`, 로그 둘째 줄에 찍힌다).
`--no-lock` 쪽에서 **덮였다** 가 몇 번 나오는지가 이 실험의 주된 계측값인데,
꺼져 있으면 그 오류가 **아예 안 나온다** -- 로그만 보고 *"안 덮였다"* 로 잘못
읽게 된다.

**판정** (미리 정해 둔다 — 나중에 정하면 눈이 원하는 답을 고른다):

| 관측 | 판정 |
|---|---|
| `--lock` 에서 FETCH 가 **실패**(거부·타임아웃) | **H1 확정.** 켜지 않는다.  labtest 가 옳았다 |
| FETCH 시간이 **1.5배 이상** 느림 | **H1 쪽.** 원인을 더 본 뒤 판단 |
| 시간 차이 **±20% 이내**, 둘 다 성공 | **H2.** 2단계로 간다 |

#### ⭐⭐ 그리고 1단계가 **공짜로 더 큰 것**을 답한다 — `RBUF` (2026-08-30 신설)

매뉴얼 p.50: `RBUF=d ; **Current buffer number locked for reading**`.  fetch 는
덮임 대조를 하려고 `LOCKn` 직후 `FRAME` 을 **이미 읽는다** — 그 응답 안에 있는
값을 그동안 버리고 있었다.  **왕복이 안 는다.**

    LOCK1 뒤 RBUF=1 (기대 1) -- 이 FW 는 LOCKn 을 반영한다          <- probe 3단계
    WBUF 0 -> 0  (fetch 동안 엔진이 버퍼를 옮겼다면 여기서 보인다)

| 관측 | 뜻 |
|---|---|
| `LOCK1` 뒤 **`RBUF == 1`** | ⭐ **이 FW 가 잠금을 반영한다** — A-5 판단 ②의 절반이 여기서 닫힌다 |
| `LOCK1` 뒤 **`RBUF == 0`** | ⚠️ 반영 안 됨 **또는** `RBUF` 미구현.  어느 쪽이든 **`LOCK` 에 기대면 안 된다** → `recheck_after_fetch` 가 유일한 방어 |

⚠️ **한 방향으로만 결정적이다** — 맞으면 반영된 것이지만, 안 맞는다고 *"`LOCK`
무효"* 는 아니다(`RBUF` 쪽 미구현일 수 있다).  ⭐ **`WBUF` 의 이동이 더 강한
증거다** — 상태 플래그가 아니라 **엔진이 실제로 다른 버퍼를 썼다**는 거동이라,
2단계(연속 부하)에서 `WBUF a -> b` 로 바뀌는 것이 보이면 매뉴얼 p.71 의 *"다음
잠기지 않은 버퍼"* 가 실기에서 참임이 확인된다.

⚠️ **가짜 컨트롤러도 판정 근거가 아니다** — `tests/fake_archon.py` 는 잠금 중
`RBUF` 가 잠긴 버퍼를 가리키도록 **매뉴얼대로 모사**할 뿐이다.  시험이 재는 것은
*우리 코드가 관측값을 제대로 담아 오는가*이지 실기가 그렇게 답하는가가 아니다.

#### 2단계 — 연속 부하 (본편, **최악 조건**)

⚠️ **`BIAS` 연속이 가장 얇다** — 주기 12초로 가장 짧고 버퍼 여유가 6.3초뿐이다.
3초 노출로는 여유가 커서 차이가 안 드러난다.

```bash
# ini 에서 lock_buffer 만 바꿔 가며 두 번.  각 10장 이상
python -m ics_archon        # OBS>ICS bias begin / exp 0 / go 10
```

**로그에서 셀 것 넷:**

```
grep -c 'FETCH .* MiB'                     → 프레임이 다 왔나 (10장이어야 한다)
grep    '버퍼 .* 로 덮였다'                 → fetch **앞** 대조에 걸림 (파일 손실)
grep    'fetch 하는 동안 버퍼 .* 덮였다'    → ⭐ fetch **중**에 덮임 (재대조가 잡은 것)
grep    '프레임 번호가 뒤로 갔다'            → 되감김·컨트롤러 재시작 (재동기했다)
grep    'RBUF=.* (기대 '                    → ⚠️ LOCK 을 보냈는데 RBUF 가 안 따라왔다
grep -o 'RBUF=[0-9]* WBUF=[0-9-]*'          → ⭐ 매 프레임의 잠금 관측값 (FETCH 줄에 실린다)
grep    'LOCK0(잠금 해제)에 실패'           → 해제 실패 (다음 프레임이 막힌다)
grep    '수신 버퍼가 없어 .* 기다렸다'       → 호스트 쪽 병목 (fetch_buffers 부족)
```

**판정:**

| 관측 | 뜻 |
|---|---|
| `--lock` 에서 **프레임이 덜 나온다** | ⚠️ **잠긴 버퍼를 건너뛰지 않는다는 뜻** — 우리 전제가 틀린 것이다(아래 참조).  켜지 않는다 |
| `--no-lock` 에서 **"덮였다" 가 나온다** | `LOCK` 이 실제로 막아 주는 것이 있다 → **켜는 쪽이 맞다** |
| **양쪽 다 깨끗** | 둘 다 안전.  ⭐ **켜 두는 쪽을 고른다** — 실측 여유가 6.3초로 얇아 보험이 값싸다 |
| `LOCK0` 실패가 보임 | 해제 경로 문제.  `lock_buffer=false` 로 두고 원인을 따로 본다 |

⚠️ **`--no-lock` 에서 "덮였다" 가 안 나온다고 `LOCK` 이 불필요한 것은 아니다** --
labtest 는 1년을 껐지만 그때는 **저장이 순차**여서 다음 노출이 겹치지 않았다.
본편은 저장을 겹치므로 조건이 다르다 (`ics_archon/DevNote.md` **7장**).

#### 매뉴얼이 말하는 것 (2026-08-30) — ⚠️ **가설의 강도이지 판정이 아니다**

p.71 이 호스트 절차를 통째로 적어 두었다 -- *"이미 받아 간 것보다 프레임 번호가
**큰** 완료 버퍼가 있으면, 호스트는 **`LOCK` 을 내려 그 버퍼가 덮이는 것을 막고**
`FETCH` 한다."*

- **매뉴얼 안에서 `LOCK` 은 예외 조치가 아니라 통상 경로에 있다** -> H2 의 사전
  확률이 올라간다.
- ⭐ **우리 알고리즘이 벤더 절차 그대로다** (번호가 큰 완료 버퍼 → `LOCK` → `FETCH`).
- ⚠️ **벤더도 `greater than` 이라고 적었다** -- 벤더 절차 자체가 되감김을 안 다룬다.

⚠️⚠️ **처음에 이걸로 *"labtest 가 뺀 것이 이탈"* 이라고 적었는데 되돌린다** (운영자
지적 2026-08-30):

> 매뉴얼 개정판이 오래되었고(2021-02-23) **현행 FW 가 다 반영되지 않은 부분도, 반대로
> 매뉴얼에 묘사된 기능이 FW 에 반영되지 않은 경우도 있었다.  따라서 실측이 가장
> 신뢰할 수 있는 판단 근거다.**

⭐ **그 규칙을 적용하면 labtest 쪽이 오히려 유리하다** -- `"remove to fetch debug"` 는
한 줄이어도 **실기에서 나온 기록**이고 5년 된 문서 문단보다 앞선다.  ⚠️ 다만 그 한
줄은 **무엇을 관측했는지 안 적었다**(실측이 아니라 *실측의 흔적*)이라 그것만으로
`false` 가 옳다고도 못 한다.

**-> 양쪽이 대등한 가설이고, 이 실험이 판정한다.**  근거 등급표는 `DevNote.md` **8.7**.

#### ⚠️ ⭐ 새 가설 H3 -- **버퍼가 둘이라서 뺐을 수 있다** (2026-08-30)

운영자가 알려 준 사실: **science 는 `BIGBUF` 로 2개, guide 는 small buffer 로 3개.**
매뉴얼 p.71 은 엔진이 *"다음 **잠기지 않은** 프레임 버퍼"* 를 잡는다고 적었다.

| 유닛 | 버퍼 | 호스트가 하나 잠그면 엔진에 남는 것 |
|---|---|---|
| **science (BIGBUF)** | 2 | **1개** |
| guide (small) | 3 | 2개 |

**labtest 는 science 다.**  버퍼 둘 중 하나를 잠그면 엔진에 하나만 남고, **남는
버퍼가 없을 때 어떻게 되는지는 매뉴얼에 없다.**  2단계에서 이것을 가른다 --
`--no-lock` 과 `--lock` 의 차이가 *"누더기"* 가 아니라 *"주기가 늘어남/멈춤"* 으로
나타나면 H3 다.

#### ⚠️ 결과를 볼 때 함께 볼 것 -- 이제 **재대조가 잡아 준다**

카운터 대조는 fetch **직전 한 순간**만 본다.  **FETCH 자체가 5초**라 그 5초에
덮이면 **앞부분은 내 프레임 · 뒷부분은 남의 프레임인 누더기 파일**이 나온다.

✅ **그 구멍은 `recheck_after_fetch`(기본 `true`)가 메웠다** -- 이제 누더기는 조용히
저장되지 않고 **`덮였다` 오류로 크게 운다.**  ⭐ 그래서 `--no-lock` 쪽에서 그 오류가
몇 번 나오는지가 **실험의 주된 계측값**이다.

→ 그래도 2단계에서 **영상도 볼 것.**  재대조는 fetch 전후 두 순간을 볼 뿐이라,
번호가 두 번 바뀌어 원래 값으로 돌아오는 경우(버퍼가 셋인 guide 에서 이론상 가능)는
못 잡는다.  누더기는 **가로로 끊긴 자국**으로 나타난다.

#### 실험 없이 알 수 있는 것 (미리 계산해 둔 것)

- 잠금 구간은 **FETCH 뿐**이다(`IDLE`+3.4~8.4초).  저장은 잠금 밖이다.
- 그 버퍼를 컨트롤러가 다시 쓰는 것은 **~14.7초** → **여유 6.3초**.
- ⭐ **`LOCK` 은 이중보호의 한 겹이다** (운영자 해석 2026-08-30) — 컨트롤러가
  버퍼 번호를 바꿔 가며 쓰는 구조에서 *"읽는 동안 잠근다"* 는 보편적 관례다.
  우리 구조는 실제로 두 겹이다: **`LOCK`(예방) + fetch 앞 프레임 번호 대조
  (사후 감지)**.  ⚠️ 그 해석이 맞다면 **H1 의 가능성이 낮아진다** — 표준 관례를
  뺄 이유는 디버깅밖에 없다.
- ⭐ **"컨트롤러가 멈춘다" 는 구조적으로 안 일어날 가능성이 크다** — 우리는
  **한 번에 버퍼 하나만** 잠그고 BIGBUF=1 은 버퍼가 **둘**이라 항상 하나가
  남는다.  잃는 것은 **이중 버퍼링의 여유**이지 동작 자체가 아니다.
  ⚠️ **다만 이것은 우리 가정이다** — `tests/fake_archon.py` 가 *"잠긴 버퍼는
  건너뛴다"* 로 모사할 뿐이고, 매뉴얼에서 확인한 것은 *"버퍼 n 을 읽기용으로
  잠근다"*(p.50) 한 줄뿐이다.  **실물이 잠긴 버퍼를 건너뛰는지**가 2단계의
  진짜 물음이다.

⚠️ **labtest 가 1년간 `LOCK` 없이 무사한 것은 "필요 없다" 의 증거가 아니다** --
labtest 는 저장이 **순차**라 다음 노출이 겹칠 일이 없었다.  **보호가 필요한
상황이 안 온 것**이지 보호가 불필요했던 것이 아니다.  본편은 저장을 겹친다.

### B. 실기 왕복으로만 확정되는 것 (3단계)

| 미검증 자리 | 실기에서 확정될 값 | 코드 표시 |
|---|---|---|
| ~~**`LOCKn` 을 켜도 되나**~~ (구 A-5 판단 ②) | ✅ **종결 (2026-09-01)** — 두 FW 에서 15/15 반영, 대가 0, 지킬 구간 실재(`nolock` 덮임 2/2). **`true` 유지.**  DevNote 10.6 | `[archon] lock_buffer` · 결정 15 |
| ⭐ **`BUFnFRAME` 폭** (2026-08-30 신설) | ① 65535 초과 여부 — ⏳ **미결**(카운터가 작다) · ② ~~전원 재투입 직후 0 인가~~ ✅ **닫힘 (2026-09-02)**: 리셋은 **`REBOOT` 만**(첫 프레임 1), CCD 전원·`WARMBOOT` 는 이어진다 · ③ 밤새 되감김 — 미결 | `parse.restarted_frame` · DevNote 8.1 갱신 · 10.7 |
| ~~**엔진이 잠긴 버퍼를 실제로 건너뛰나**~~ (가설 H3) | ✅ **닫힘 (2026-09-01)** — 건너뛴다.  남는 버퍼가 없으면 **쓰던 버퍼를 재사용**하며 만속 유지 (`--hold 20`, 잠금 > 주기).  ⚠️ 대가: 잠금이 주기(13.27초)를 넘으면 **다음 장이 덮인다** → `fetch_timeout` 을 주기 아래로.  DevNote 10.4·10.6 | `[archon] lock_buffer` |
| STATUS 필드·모듈 나열 순서 | `TEMP_MODS`(BACKPLANE + MOD5~8)가 실물과 맞는지. **정본 명세는 규격 수록 예정** | `parse.TEMP_MODS` |
| ~~독출 시간·진행률 거동~~ | ✅ **실측 (2026-09-01)** — **368 행/초**, 4700행 12.77초, 선형.  FETCH 3.2~3.5초 + 저장 1.2초 → 25초 창에 넉넉히 든다.  ⚠️ **`PCTREAD` 가 49% 에서 완료로 넘어갔다** — `FRAMEMODE=2` 라 `BUFnHEIGHT=9400`, `BUFnLINES` 는 4700 에서 멈춘다.  ✅ **고쳤다 (2026-09-02)**: `parse.progress_of(lines_total)` + `ArchonController.lines_total`(ACF `LINECOUNT`), DevNote 9.15 | `controller.wait_frame` · `backend.readout` · `parse.progress_of` |
| 픽셀 좌우 배치 | Archon 이 주는 X 순서가 raw spec 4.1절(`chips[0]` = X 낮은 쪽)과 같은지 | `backend.write_frame` |
| 산출물 실물 | 기하(19200×9400) · `DETID` · `DATE-OBS` · converter 투입 | `fitswrite.write_frame` |
| STOP 이 적분을 자를 수 있나 | `FASTLOADPARAM IntMS 0`(p.52)이 즉시 반영되는지 | `backend.close_shutter` |
| 적분 중 `APPLYSYSTEM` 이 안전한가 | 강제 셔터 폐쇄가 독출을 흔들지 않는지 | 〃 |
| 셔터 트리거 배선 | `shutter_ctrl` 을 `both` 에서 한쪽으로 좁힐지 | `[archon] shutter_ctrl` |
| ~~ERASE 운용~~ | ✅ **확정 (2026-08-29)** — **하지 않는다.**  clock 개선으로 별도 erase 없이 바로 노출을 시작한다(운영자).  기본값 `false` | `[archon] full_flush_on_erase` |
| **호스트 버퍼가 모자란 적이 있나** | ⭐ `ctrl.buf_waits`/`buf_wait_s` 가 0 이면 `fetch_buffers=2` 로 충분한 것이다.  쌓이면 3으로 올린다 (RAM 32 GB 라 여유가 크다) | `[archon] fetch_buffers` |
| 노출 파라미터 슬롯 | `PARAMETER1/2` 와 `IntMS`/`Exposures` 가 현행 ACF 와 맞는지 | `[archon] param_*` |
| `DATE-OBS` 정밀도 | `TIMER` ↔ 호스트 UT 상관 + `BUFnREATIMESTAMP` 로 개선할지 | 지금은 호스트 시각 |

### C. 원천이 아예 없는 것

- ~~**듀어·환경 HK** (`sensors()`)~~ — ✅ 원천이 생겼다: `icg_archon` HK
  스냅샷 (2026-08-31, 위 "아직 없는 것" 항목 참조).
- ~~**guide 계통**~~ — ✅ **`icg_archon/` v0 로 착수됐다** (2026-08-31,
  DevNote 9장).  실기 왕복은 미검증.
- **binning** (`BIN`) — `ics_sim` 쪽도 스텁이다.

## 설치 루트 = `~/AIC` (운영자 확정 2026-08-24)

벤치 기계 이름이 **AIC** 이므로 설치 루트를 거기 맞췄다 (`~/AICS` -> `~/AIC`).
`ics_sim`·`ics_archon` 뿐 아니라 **XIS·OBSAgent·TCSAgent 가 같은 루트를 쓴다**
— 저장소 전수 20파일 101곳을 함께 고쳤다.

### 이미 `~/AICS` 로 돌고 있는 기계를 옮길 때 (1회)

```bash
pkill -f obstool; pkill -f pctcs; pkill -f ics_sim; pkill -f isis
mv ~/AICS ~/AIC
grep -rl 'AICS' ~/AIC/Config/ | xargs sed -i 's|AICS|AIC|g'
grep -rn 'AICS' ~/AIC/Config/          # 비어야 정상
```

⚠️ **폴더 이름만 바꾸면 안 된다.**  `build-local.sh` 가 만든 ini 들이 로그·
카탈로그 경로를 **절대경로로 펼쳐서** 써 놓으므로, 부모 폴더를 옮겨도 파일
안의 문자열은 그대로 옛 루트를 가리킨다 (`isis.ini` `ServerLog` · `pctcs.ini`
`LOGFILE`/`CATFILE` · `obstool.ini` `LOGFILE`).  위 `sed` 가 그 몫이다.

⚠️ **`~/AIC/bin/` 의 바이너리도 갈아야 한다** (2026-08-24 실측에서 빠뜨렸던 것).
`build-local.sh` 는 `build/` 아래에만 만들고 `bin/` 에 설치하지 않는다 — `bin/`
사본은 사람이 손으로 복사해 둔 것이라 **개명해도 옛 판 그대로 남는다.**  그
안에는 `TEMP_*LOGFILE`(옛 루트)이 박혀 있고 **그 자리는 ini 로 못 고치므로**,
띄우면 로그 파일을 못 열고 시작한다.

```bash
pkill -f 'bin/isis'; pkill -f obstool; pkill -f pctcs   # 먼저 내린다
bash ./OBSAgent/build-local.sh          # bin/ 까지 설치한다
bash ./TCSAgent/build-local.sh
bash ./ics_sim/xis/build-local.sh --build-dir ~/AIC/build/xis --prefix ~/AIC
for f in ~/AIC/bin/*; do printf '%-12s %s
' "$(basename $f)"   "$(strings $f | grep -c AICS)"; done      # 전부 0 이어야 한다
```

돌고 있는 실행 파일에 `install` 하면 `Text file busy` 로 실패한다 — 그래서
`pkill` 이 먼저다.  XIS 는 `--prefix` 를 **컴파일 상수로 박으므로**(`CONFIG`/
`LOGS` 정의) 재빌드가 필요하다.  `isis.ini` 는 이미 있으면 안 건드린다.

⚠️ **`~/AIC/Config/*.expnum` 이 노출 번호 카운터다.**  `mv` 로 옮기면 따라오지만,
`Config/` 를 지우고 새로 만들면 **번호가 1 로 되돌아간다** — 2026-08-11 에
`FitsNum=00000000.000000` 로 실제로 겪었고 OBSAgent 파싱까지 깨졌다.  옮긴 뒤
`cat ~/AIC/Config/ics_sim.expnum` 으로 확인할 것.

**이 판을 처음 적용할 때만 `pctcs`·`obstool` 을 한 번 다시 빌드한다** (아래
"재빌드가 필요 없어진 것" 이 그때 들어간다).  그 뒤로는 루트를 또 옮겨도
재빌드가 필요 없다.

### 재빌드가 필요 없어진 것 (2026-08-24)

로그 경로 일부가 컴파일 상수라 루트를 바꿀 때마다 재빌드가 필요했다.  성질을
갈라 풀었다 — 근거는 [`../OBSAgent/SMC_CLAUDE.md`](../OBSAgent/SMC_CLAUDE.md) ·
[`../TCSAgent/SMC_CLAUDE.md`](../TCSAgent/SMC_CLAUDE.md) 의 같은 제목 절.

| 상수 | 처방 |
|---|---|
| `pctcs` `TEMP_LOGFILE` · `obstool` `TEMP_{EVENT,DEBUG,SCROBS}LOGFILE` | **`/tmp` 고정** — ini 를 읽기 전에 열려 ini 로는 원리상 못 고친다.  수 초 뒤 ini 의 `LOGFILE` 자리로 `mv` 되므로 최종 위치는 여전히 ini 소관 |
| `obstool` `DEFAULT_OBSSTAT` | **ini 키 `OBSSTATFILE` 신설** — 키가 없으면 종전 상수를 쓴다(기존 설치 무변경) |
| 양쪽 `DEFAULT_LOGFILE` | 그대로 — ini 의 `LOGFILE` 이 덮어쓰는 기본값이다 |

⚠️ 새 설치는 `--prefix`/`--root` 기본값이 이미 `~/AIC` 다.  **XIS 만 예외**로
기본값이 `$HOME/xis` 이므로 `./ics_sim/xis/build-local.sh --prefix ~/AIC` 처럼
명시해야 한다 (개명 전에도 그랬다).

## 리눅스 구동 (운영자 확정 2026-08-23)

**`ics_sim` · `ics_archon` · labtest 전부 리눅스에서 돌린다.**  전수 감사 결과
포팅이 필요한 것은 셋뿐이었고 다 고쳤다 — 그 밖의 코드는 이미 이식성이 있다
(`sys.platform`/`os.name` 분기 0 · 윈도우 전용 모듈 0 · 텍스트 `open()` 은 전부
`encoding=` 명시).  ⚠️ 당시 근거로 들었던 `siteid` 의 `getaddrinfo`·UDP 탐침은 **그 파일이 2026-08-24 에 삭제되어 더 이상 없다**(D-015 폐기).

| 고친 것 | 무엇이 문제였나 |
|---|---|
| labtest 저장소 경로 | `C:/DATA` · `H:/DATA` · `L:/DATA` (윈도우 드라이브 문자). 리눅스에서는 경로로 성립하지 않아 **cwd 아래 `C:` 라는 이름의 폴더를 만들고 오류도 안 난다** -> `/data` · `/mnt/ssda/DATA` · `/mnt/ssdb/DATA` (`<---- Set this`) |
| labtest 의 `twilio` import | 함수 본문이 통째로 주석 처리돼 **쓰지도 않는데** 모듈 최상단에서 import 했다 -> twilio 없는 기계에서 **스크립트가 아예 시작 못 했다.** `try/except ImportError` 로 감쌌다 |
| `.gitattributes` | `*.ini`·`*.acf` 가 정규화 목록에 없어 CRLF 로 체크아웃됐다 -> `text eol=lf` 추가 |

⚠️ **labtest 판올림**: 위 둘을 고쳐 `v1.1.1` -> **`v1.1.2`** (`SCRIPT_BUILD`
2026-08-23T12:00Z). 컨트롤러와의 왕복은 한 줄도 안 건드렸다. `smallbuf` 판도
같이 고쳤다(원본은 `__ref_archon_control/` 에 그대로 있다).

### 경로 설정 — `~` 확장 (2026-08-23, 목 지시로 발견)

**`[paths] data_dir` 이 `~` 를 펼치지 않았다.**  `os.makedirs('~/AIC/data')` 는
오류를 내지 않는다 — `~` 를 정상적인 상대 경로 조각으로 보고 **작업 디렉터리
아래에 `~` 라는 이름의 폴더**를 만든다.  즉 설정에 `~/AIC/data` 를 적어 놓고
자료가 거기 있다고 믿는 동안 `<cwd>/~/AIC/data` 에 쌓인다.  `expnum_file` 만
펼치고 있었던 것이 오히려 함정이었다("경로 설정은 `~` 를 받는다" 고 믿게 한다).

`data_dir` · `[logging] file` · `[archon] acf_*` 를 다 펼치게 고쳤다
(`config._path_or`).  시험 `ics_sim/tests/test_path_settings.py` (5항목).

**`[paths] data_dir = ~/AIC/data`** 로 확정했다 (목 2026-08-23).

- 그 자리는 **실제 디렉터리든 심볼릭 링크든 된다.**  프로그램이 매번 경로를
  다시 해석하고, 임시 파일(`.part`)과 최종 파일이 같은 디렉터리라 파일계통을
  넘는 rename 이 없다.  `expnum_file` 은 `~/AIC/Config/` 에 따로 있어 저장
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

- **번호 공간**: `rawpair.NUM_SPACE = 1_000_000` -> `000000`~**`999999`** 이고
  1000000 에서 `000000` 으로 되감는다 (**D-018**, 2026-08-25 — 구 `099999`
  상한을 대체했다). 6자리 형식 전체를 쓴다 (raw spec 2.3절).
- **저장 위치**: `[paths] expnum_file` (`~` 확장됨). 비우면 **설정 파일 옆**으로 자동 결정
  (`config.resolve_expnum_file`) — `~/AIC/Config/ics_archon.ini` 면
  `~/AIC/Config/ics_archon.expnum`. `data_dir` 와 **일부러 분리**했다: 저장
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
하나를 맞는다.

✅ **그 예고가 그대로 일어났고, 2026-08-26 에 들여왔다** — raw spec **v1.5** 의
5장 검토분(HK 4장 폐지 · `CHMAP_*` 4자 토큰 · comment 오타 2건 · D-017 사이트
코드 · D-018 번호 공간)이 견본 pair 와 `rawcards.py` 와 labtest 내장
`RAWCARDS` 를 **셋 다** 건드렸다. 예고대로 **바이트 대사 시험이 알람 역할을
했다** (`tests/test_fitswrite.py` · `ics_sim/tests/test_raw_draft.py`).
자세한 것은 위 "raw spec v1.5 반영" 절. 합류 방식은 `--no-ff` 거품 머지.

## Archon 매뉴얼이 말하는 것 — ✅실측 확인 / ⚠️미확인 (`__ref_archon_control/`)

본편에서 다시 찾지 않도록 적어 둔다. 근거는 매뉴얼(**2021-02-23**)·ZTF Readout
Notes(2014-10-30), 쪽수는 매뉴얼 기준.

> ⚠️⚠️ **매뉴얼은 판정 근거가 아니다** (운영자 2026-08-30).  개정판이 오래되어
> **현행 FW 가 매뉴얼을 다 반영하지 않은 부분도 있고, 반대로 매뉴얼에 묘사된 기능이
> FW 에 없는 경우도 있었다.**  ⚠️ **표류가 양방향이라 어느 쪽으로도 보증하지
> 않는다.**  ⭐ **판단 근거는 실측**이고, 매뉴얼의 역할은 **무엇을 재야 하는지 알려
> 주는 가설 생성기**다.  근거 등급표와 사례는 `DevNote.md` **8.7**.
>
> ⚠️ 이 절의 종전 제목이 *"매뉴얼에서 **확정한 사실**"* 이었다 — **제목 자체가
> 매뉴얼을 판정으로 읽게 부추기고 있었다.**  그래서 항목마다 **✅실측 확인 /
> ⚠️미확인** 을 붙인다.

### ⭐⭐ 이 절 안에 **매뉴얼이 이미 틀린 것으로 드러난 사례가 둘** 있었다

운영자의 지적이 추상적인 경고가 아니다 — **우리 저장소가 이미 반례를 들고
있었는데 그 함의를 안 뽑아냈다** (2026-08-30에야 알아봤다).

| 매뉴얼 | 실기 | 어긋난 방향 |
|---|---|---|
| `MODn_TYPE` 을 **15까지만** 정의, *"16+: Unknown"* (p.46) | science ACF 가 `MOD5/MOD8_TYPE=**17**`, KMTC/KMTS 가 `MOD9_TYPE=**18**` | **FW·하드웨어가 문서보다 새롭다** |
| AD(비디오) 모듈은 **중앙 4슬롯(5-8)** (p.20) | 실기 science 는 AD 계열이 **슬롯 5·8 둘뿐** (2026-08-27 확인) | 문서의 배치 전제가 현행 구성과 다르다 |

⭐ **둘 다 우리가 실기 ACF 를 읽다가 걸린 것**이고, 둘 다 *"매뉴얼이 낡았다"* 로
정리하고 넘어갔다.  ⚠️ **그때 원칙으로 승격했어야 했다** — 그랬으면 `LOCK` 을
매뉴얼 한 문단으로 판정하지 않았을 것이다.  이번에는 원칙으로 적는다
(`DevNote.md` **8.7**).

### 확인 상태 요약

| 상태 | 항목 |
|---|---|
| ✅ **실기 동작으로 확인** | 프로토콜 프레이밍(p.45) · `FETCH` 블록 규약(p.51) · `FRAME`/`SYSTEM`/`STATUS` 필드 이름 · `LOADPARAMS` · 셔터 `TRIGOUTFORCE` · 기하(`PIXELCOUNT`/`LINECOUNT`) · ⭐ **2026-09-01 추가**: `LOCKn` 효과(`RBUF` 15/15, 두 FW) · 엔진의 *"다음 잠기지 않은 버퍼"* 정책(H3) · **`POWERON` 은 `APPLYALL` 뒤**(p.51) · 버퍼 정보는 **첫 프레임에** 채워진다(p.70) · `FRAMEMODE=2` split(p.56·70) · `REBOOT`/`WARMBOOT` 의 차이(p.51) |
| ⚠️ **미확인 — 매뉴얼뿐** | `BUFnTIMESTAMP` 의 시점 의미 · 바이어스 자가검사(p.29·31) · Rev F 단일 접속(p.15) · power good 범위(p.41, **전원 보드 저항으로 정해진다니 판마다 다를 수 있다**) · 쓰는 중인 버퍼의 **부분 fetch**(p.70) |
| ⚠️ **매뉴얼에 없음** | `BUFnFRAME` 폭 (⏳ 미결) · ~~남는 버퍼 없을 때 거동~~ → ✅ **실측**: 쓰던 버퍼를 재사용, 감속 0 (DevNote 10.4) · `LOCKT`·`AUTOFETCH` 의 뜻 |
| ❌ **매뉴얼이 현행과 다름(실증)** | `MODn_TYPE` 16+ · AD 모듈 슬롯 배치 |

- ✅ **실측 확인** (근거 셋 일치 -- ACF · GUI · `gmon` v2 실측 7장).
  ⭐ **프레임 기하는 `PIXELCOUNT`/`LINECOUNT` 가 정한다 -- 타이밍 파라미터가
  아니다** (2026-08-29 확인).  타이밍의 `Pixels`/`Lines`(`PARAMETERn`)는 시퀀서가
  **몇 개를 디지타이즈하나**이고, 프레임에 담기는 것은 `PIXELCOUNT` x `LINECOUNT`
  다.  Archon GUI 에서는 **CDS/Deint 탭의 "Pixels per Tap"** 이 `PIXELCOUNT` 다
  (운영자 확인).
  - **guide**: 디지타이즈 601(`Pixels=600` + 인자 없는 `CALL PixelFirst` 1) ->
    **저장 528**.  8탭 x 528 = `NAXIS1=4224`, `NAXIS2=1033`
  - **science**: 디지타이즈 1202 -> **저장 1200**.  16탭 x 1200 = `NAXIS1=19200`,
    2 x 4700 = `NAXIS2=9400`
  - ⚠️ **guide 는 73개를 클록해 놓고 버린다**(science 는 2개 -- flush 여유).
    보관본 여섯 판이 전부 600/528 이라 최근 실수가 아니다.  **트림 가능 여부는
    실기 시험 항목**이고 판정법·주의는 [`acf/README.md`](acf/README.md) 의
    "읽는 픽셀 수와 저장되는 픽셀 수가 다르다" 절에 있다.
  - 근거 셋 일치: ACF `PIXELCOUNT` · GUI "Pixels per Tap" · **`gmon` v2 실측
    7장**(`main` 브랜치 `gmon/DESIGN.md` 2절).
- ✅ **실측 확인** (labtest 1년 운용 + 우리 실기 왕복).
  **프로토콜** (p.45): `>xxCMD\n` → `<xxRESPONSE\n` / `?xx\n`(오류) /
  `<xx:`+1024B(이진, **개행 없음**). **인식 못 한 명령은 무응답**이고,
  참조번호는 호스트가 정하는 꼬리표라 값을 건너뛰어도 어긋나지 않는다.
- ✅ **실기 확인 (2026-09-01)** -- `LOCK` 의 효과는 매뉴얼대로다: 두 FW 15/15 반영, 엔진이
  잠긴 버퍼를 피한다 (DevNote 10.4).  아래 p.71 인용은 가설의 출처로 남긴다.
  **호스트 취득 절차가 p.71 에 통째로 적혀 있다** (2026-08-30 확인).
  *"`FRAME` 을 내고, **이미 받아 간 것보다 프레임 번호가 큰** 완료 버퍼가 있는지
  본다.  새 프레임이 있으면 **`LOCK` 을 내려 그 버퍼가 덮이는 것을 막고**, 그 다음
  `FETCH` 로 픽셀을 받는다."*  -> **우리 알고리즘이 벤더 절차 그대로**이고,
  **매뉴얼 안에서 `LOCK` 은 예외 조치가 아니라 통상 경로에 있다**(결정 15).
  ⚠️ **그러나 이것은 판정이 아니라 가설의 강도다** -- 이 문서가 실기 FW 를
  기술한다는 보장이 없다(위 반례 둘).  ⚠️ 벤더도 `greater than` 이라 **되감김은
  벤더 절차에도 없다.**
- ✅ **실기 확인 (2026-09-01)** (가설 H3 의 출처였다).
  **엔진은 새 프레임을 시작할 때 "다음 잠기지 않은 버퍼" 를 잡고**, 그 버퍼의
  정보(시각·번호)를 갱신한 뒤 채운다 (p.71).  -> **번호가 가만히 있으면 옛 프레임,
  바뀌면 새 프레임**이라는 판별의 근거다(되감김 처리).  ⭐ **남는 버퍼가 없으면 엔진은
  쓰던 버퍼를 재사용**해 다음 장을 덮는다 -- 매뉴얼에는 없고 `--hold 20` 실측이다
  (DevNote 10.4); 그래서 잠금은 주기 안에 풀어야 한다 (10.6).
- ⚠️ **매뉴얼에 없다 -- 실측으로만 좁힐 수 있다.**
  **`BUFnFRAME` 의 폭** (2026-08-30, 103쪽 전수 검색).
  `BUFnFRAME=d ; Buffer n frame number` 뿐이고 `wrap`/`rollover`/`overflow` 라는
  낱말이 문서에 **한 번도 안 나온다.**  ⭐ 매뉴얼은 **폭을 아는 자리에는 적어
  두었다**(`TIMER`·`BUFnTIMESTAMP` 64-bit · `VCPU_OUTREG` unsigned 16-bit ·
  counts/parameters 20-bit p.64 · CDS counters 16 bit p.69 · accumulators 32 bits
  p.69) -- 즉 **문서가 정하지 않은 것**이다.  정황(백플레인 32비트 soft processor /
  Rev H 64비트 ARM, p.15)은 32비트를 가리키나 **추론이다.**  코드는 폭에 기대지
  않는 방법으로 되감김을 다룬다(`parse.restarted_frame`).
  ⭐ **값싼 실측 셋** (2026-08-30) -- ① `FRAME` 을 한 번 읽어 `BUFnFRAME` 이
  **65535 를 넘은 적이 있으면 16비트가 아니다**(`probe_archon` 1단계가 이미 원문을
  찍는다, 비용 0.  ⚠️ 한 방향으로만 결정적 -- 안 넘었다고 16비트인 건 아니다)
  ② ~~전원 재투입 직후 `BUFnFRAME` 이 0 인가~~ ✅ **닫힘 (2026-09-02)** -- CCD 전원·`WARMBOOT`
     는 이어지고 `REBOOT` 만 **1 부터** 다시 (0 은 "없다").  재시작 경로가 걸리는 사건은
     `REBOOT`·백플레인 전원 재투입뿐 (DevNote 10.7)
  ③ guide 로 짧은 노출을 밤새(0.5초 주기면 16비트는 약 9시간) 돌려 **되감김을 직접
  본다**.
- ⚠️ **부분 확인** -- 개수(science 2 · guide 3)는 운영자가 확인, **주소·용량은 매뉴얼뿐**.
  **버퍼 크기** (p.71): 기본은 **512 MB 짜리 3개**, `BIGBUF=1` 이면 **768 MB
  짜리 2개**(주소 `0xA0000000`·`0xD0000000`, 3번 미사용).  ⭐ **우리 운용은
  science = BIGBUF 2개 · guide = 3개**다 (운영자 2026-08-30).
- ✅ **실측 확인** (실기 `STATUS` 응답 · 층 1·2 감시).
  **STATUS** (p.47-49): `VALID` · `COUNT` · `LOG` · `POWER`(0~5) ·
  `POWERGOOD` · `OVERHEAT` · `BACKPLANE_TEMP` · 모듈별 `MODm/TEMP` · 전원 레일
  `P2V5_V/I` … `P35V_V/I`. **raw spec `Cn_VOLT` 의 자리 순서가 이 레일 순서**다
  (`P2V5 P5V P6V N6V P17V N17V P35V`).
  - **`VALID=n`** — "n=1 이면 나머지 필드가 유효" (p.47). ⚠️ **필드가 없는
    경우와 `VALID=0` 을 갈라야 한다** — 없다고 전 자리를 결측으로 만들면 구
    펌웨어에서 첫 실행이 통째로 `NC` 가 된다 (F2 원칙 "보고하지 않는 필드는
    이상으로 세지 않는다").
  - **`COUNT=n`** — 컨트롤러가 **내부 상태 레지스터를 갱신한 횟수** (p.47,
    p.79 GUI 설명이 같은 말을 한다). 두 질의 사이에 안 변하면 **새로 잰 것이
    아니라 같은 블록**이다. **감소하면 래핑 또는 컨트롤러 재기동**이다 — 폭
    (16/32bit)은 미기재.
  - **`LOG=n`** + **`FETCHLOG`**(p.50, "Fetches the oldest log entry") —
    컨트롤러가 자기 로그를 들고 있다. ⚠️ **깊이·넘침 정책·응답 형식·비었을 때
    응답이 전부 미기재**다 (매뉴얼 전체에서 로그 언급이 이 둘 + p.73 GUI
    설명, 셋뿐).
- ⭐ **`Cn_VOLT` 의 7레일이 "7개만 골라 쓴 것" 이 아니라 표준 구성의 전량이다**
  (p.43): "The standard Archon power supply … generate **+2.5V, +5V, +6V, -6V,
  +17V, -17V, and +35V** … along with +12V fan and +28V heater voltages."
  `P100V`/`N100V` 는 **XV 섀시 전용 핀아웃**이고(표준의 `-35V`·`User` 자리를
  대체, p.41-42) 우리 유닛은 `BACKPLANE_TYPE=1`(X12) + XVBias(형 12) 미장착이라
  해당 없다. `N35V` 는 커넥터에 핀만 있고 표준 전원이 만들지 않는다.
  그리고 p.42: "Only the voltages used by the installed modules need be
  supplied … Switches must be set on P1 and P7 to indicate which supply
  voltages are being used" — **안 쓰는 레일은 배선도 감시도 안 된다.**
  ⚠️ **`HEATER`(+28 V)는 guide 유닛에서 실재하는 레일**이다 (HeaterX 두 장) —
  guide raw 규격을 세울 때 8자리 온도와 함께 챙길 것.
- **전원 정상(power good) 범위** (p.41) — 감시가 수치만 적지 않고 **이탈을
  표시**할 근거다. ⚠️ **비대칭이라 ±% 규칙을 쓰면 틀린다**(N6V 하한 5.3 vs
  P6V 5.5). 그리고 이 값은 **전원 보드의 저항으로 정해지는 기본값**이므로
  ini 로 덮을 수 있게 둘 것.

  | 레일 | 범위 | 레일 | 범위 |
  |---|---|---|---|
  | P2V5 | +2.1 … +2.9 | **P17V** | **+16.4 … +17.5** |
  | P5V | +4.4 … +5.6 | N17V | −16.6 … −17.7 |
  | P6V | +5.5 … +6.6 | P35V | +34.3 … +36.0 |
  | N6V | −5.3 … −6.6 | (N35V) | −33.8 … −35.9 |
  | | | Heater/User | +18.0 … +36.0 |

  ⚠️ **`P17V` 줄은 2026-08-28 에 채운 것이다** — 처음 옮겨 적을 때 빠졌고, 그
  누락은 "우리가 쓰는 7레일 중 하나를 감시에서 통째로 뺀다" 를 뜻했다.  정본은
  `parse.RAIL_LIMITS` 이고 `[archon.rails]` 로 유닛별로 덮을 수 있다.

  레일 V/I 의 출처는 백플레인 ADC 가 아니라 **전원 보드**다 (p.43: "monitored
  and digitized … retrieved by the backplane over a cable connected to **P9**").
  그래서 P9 가 헐거우면 **레일 V/I 만 이상해지고 나머지 STATUS 는 정상**이다.
- **모듈별 실측 V/I 가 따로 있다** (p.48) — 모듈 형에 따라 키가 다르고
  **전류 단위가 mA 다** (시스템 레일은 A — 섞으면 1000배 틀린다).

  | 필드 | 조건 | 채널 |
  |---|---|---|
  | `MODm/LVLC_Vn` `_In` | LV(X)Bias | n=1~24 → LV1~LV24 (10 mA max) |
  | `MODm/LVHC_Vn` `_In` | LV(X)Bias | n=1~6 → LV25~LV30 (500 mA max) |
  | `MODm/HVLC_Vn` `_In` | HV(X)Bias | n=1~24 → HV1~HV24 (10 mA max) |
  | `MODm/HVHC_Vn` `_In` | HV(X)Bias | n=1~6 → HV25~HV30 (250 mA max) |
  | `MODm/MAG_*` `OFS_*` | HS only | 우리 구성에 HS 모듈은 없다 |

  science ACF 에 채널 이름표가 붙어 있다 — `MOD9\HVHC_LABEL1..6` =
  `DD-B ODD-B ODA-B DD-A ODD-A ODA-A`, `MOD9\HVLC_LABEL{11,12,23,24}` =
  `RDA-B RDD-B RDA-A RDD-A`, `MOD4\LVHC_LABEL1..6` =
  `OG-A CLAMP_N-A CLAMP_P-A CLAMP_P-B CLAMP_N-B OG-B`. **16채널이 CCD 바이어스**다.
  ⚠️ **`POWER=4` 가 아니면 전 채널이 ~0 V 다** (p.77 "When power to the CCD is
  off, all channels should be at about zero volts") — 전원 꺼진 동안의 값을
  고장으로 오독하지 말 것.
- ⚠️ **ACF 설정 키와 STATUS 키의 문자열이 같다.** `MODm/HVHC_Vi` 는 ACF 에서
  **지령값**("Set the power on voltage", p.60)이고 STATUS 에서 **실측값**
  ("voltage reading", p.48)이다. `parse_acf()` 가 `\` → `/` 로 정규화하므로
  `self.config` 와 `self.status` 의 키가 **글자 하나까지 같아진다.** 값도
  15 vs 15.02 로 비슷해서 잘못된 dict 를 뒤져도 그럴듯해 보인다 — **두 dict 를
  절대 합치지 말 것.**
- **컨트롤러가 전원 투입 때 바이어스를 스스로 검사한다** (p.29 · p.31):
  "all biases are set to 0 V. The biases are **checked** … each bias is set to
  its operating level in a user programmable sequence. **At each step, the bias
  levels are checked before proceeding**." → 지령대로 안 올라온 바이어스는
  시퀀스가 안 끝나 `POWER=3`(Intermediate)으로 나오고, 그것은
  `parse.health_problems()`(F2)가 이미 잡는다. **검사는 투입 시점만이므로
  밤중 표류는 안 잡힌다** — 그것이 감시 기록의 몫이다.
- **Rev F 이하는 동시 접속이 하나뿐이다** (p.15): "Rev F and older backplanes
  can only support a **single connection at a time**. … Rev H backplanes
  currently support up to four simultaneous connections." `BACKPLANE_REV` 는
  0=A, 1=B… 이므로 **5=Rev F, 7=Rev H**. 우리 ACF 실측:

  | 유닛 | REV | 동시 접속 |
  |---|---|---|
  | KMTK_SCI_113 (KASI 벤치) · guide STA0201 | 5 = **Rev F** | **1개** |
  | KMTC/KMTS (관측소, STA0284/0285/0286) | 7 = Rev H | 4개 |

  → **벤치에서는 별개 감시 프로세스가 `ics_archon` 과 공존할 수 없다.**
  감시를 `ics_archon` 안에 두는 것은 취향이 아니라 하드웨어가 정한 결론이다.
- **VCPU / `VCPU_OUTREGn`** (p.86-90) — DIO 가 있는 모듈마다 **100 MHz 16비트
  CPU** 가 들어 있고, ACF 에 어셈블리를 텍스트로 써 넣으면 컨트롤러가 컴파일해
  태운다(512줄, 명령 하나 10 ns). 매뉴얼이 **우리 용례를 예시로 든다** —
  "useful for … **reading an RS-232 vacuum gauge**".
  - VCPU ↔ 호스트는 **16비트 레지스터 16칸씩** 두 방향. 호스트→VCPU 는
    `VCPU_INREGn`(ACF), VCPU→호스트는 **`VCPU_OUTREGn`(STATUS 보고)**.
  - **OUTREG 자체에는 정해진 뜻이 없다** — "그 모듈의 VCPU 프로그램이 무엇을
    넣기로 했는가" 가 전부다. **정본은 ACF 안의 그 프로그램**이고 매뉴얼로는
    알 수 없다.
  - 출력 포트 주소 `0x020b` = OUTREG `b` 에 쓰기 (p.90). 그래서 guide ACF 의
    `RegPort = 0x0200` 이 OUTREG0 이고 `0x020F` 가 OUTREG15 다.
  - ⚠️ **`APPLYALL`/`APPLYMOD`/`APPLYDIO` 가 VCPU 를 재시작한다** — "held in
    reset while it's being configured, and then begins running from address 0".
    그래서 `prepare()` 의 `APPLYALL` 직후에는 OUTREG 가 잔재이고, 첫 성공
    폴링까지 **최소 0.15초 + 게이지 응답시간**의 창이 있다.
- **SYSTEM** (p.46): `BACKPLANE_ID`(16진 16자리 고유 ID = 시리얼 대용) ·
  `BACKPLANE_TYPE`(1=X12, 2=X16) · `BACKPLANE_REV` · `BACKPLANE_VERSION` ·
  `MOD_PRESENT` · `MODn_TYPE`(2 = AD). **모델명 문자열 필드는 없다.**
- **FRAME** (p.49-50): `RBUF`/`WBUF` · `BUFnCOMPLETE`/`BASE`/`FRAME`/`WIDTH`/
  `HEIGHT`/`SAMPLE` · **`BUFnLINES`(라인 진행)** · `BUFnPIXELS`(픽셀 진행) ·
  `BUFnTIMESTAMP`. 진행률은 `BUF<WBUF>LINES / LINECOUNT`(ACF) 다 -- ⚠️ `BUF<WBUF>HEIGHT`
  가 아니다: `FRAMEMODE=2`(split)면 HEIGHT = 2 x LINECOUNT 라 그 셈은 50% 에 묶인다
  (2026-09-01 실측, DevNote 10.3).
- **AD(비디오) 모듈은 중앙 4슬롯(5-8)에만** 꽂힌다 (p.20) — 모듈당 4채널(tap).
  ⚠️ **이 잠정안은 실기 ACF 와 어긋난다** (2026-08-27 확인, 아래 G1~G3).
  실기 science 는 AD 계열이 **슬롯 5·8 둘뿐**이고 6·7 은 빈 슬롯(형 0)이며,
  형 번호가 매뉴얼에 없는 **17(ADM)** 이다. `TEMP_MODS` 는 이미 규격 5.6.1 의
  10자리(1·2·3·4·5·8·9·10·11)로 교체됐는데 `_log_module_map()` 의 경고 조건만
  `[5,6,7,8]` 로 남아 있다.
- **`MODn_TYPE` 은 매뉴얼이 15까지만 정의하고 "16+: Unknown" 이다** (p.46).
  실기 science ACF 는 `MOD5/MOD8_TYPE=17`, KMTC/KMTS 는 `MOD9_TYPE=18` —
  **매뉴얼보다 새로운 형**이다. 이름은 규격 5.6.1 라벨표가 이미 갖고 있다
  (**17 = ADM**, **18 = HVYBias**), 그리고 매뉴얼 p.25 에 ADM 모듈 설명이
  따로 있다(18채널 18bit 12.5 MHz).
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

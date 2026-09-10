# ics_archon — 실기 ICS (STA Archon 제어)

`ics_sim/`(시퀀서·명령 처리부·메시지 규약·헤더 층)과 이 폴더의 Archon 제어
코드를 합친 **실기 취득 프로그램**이다.  최종적으로 `ics` 로 개명해 운영
배포한다.

```bash
cd ics_archon
python -m ics_archon                 # ics_archon.ini 를 읽는다
python -m ics_archon --backend sim   # 컨트롤러를 만지지 않고 메시지 층만
```

> **현재 판 `v0.0.0` — 실기 왕복은 한 번도 돌리지 않았다.**  가짜 컨트롤러
> (`tests/fake_archon.py`)로 전 경로가 돌고 견본 헤더와 바이트 단위로 일치하지만,
> 실물 Archon 과의 왕복·독출 시간·픽셀 배치는 미검증이다.  잠정인 자리는
> 코드에 `PROVISIONAL` 로 표시했고 목록은 [SMC_CLAUDE.md](SMC_CLAUDE.md) 에 있다.

## 파일 구성

| 파일 | 정체 |
|---|---|
| [`ics_archon/`](ics_archon/) | ✅ **실기 취득 프로그램** (`v0.0.0`) — `ics_sim` 을 가져다 쓰고 그 아래 Archon 층을 채운다 |
| [`ics_archon.ini`](ics_archon.ini) | 설정 — `[archon]` 절이 컨트롤러 배선이다.  **`hk_latest`** 가 icg 의 HK 스냅샷 경로(5.6절 HK 카드의 원천)다 |
| [`icg_archon/`](icg_archon/) | ✅ **실기 ICG** (`v0.0.0`, 2026-08-31 신설) — guide 유닛 취득(raw spec v1.9 **9·10장**: `<SITE>.<날짜>.<번호>.G.fits`, frame-transfer 의미론) + **HK 취득·로깅**(1분 — Ctrl·진공·RTD·Radionode·AUX).  `python -m icg_archon` / `--backend sim`.  경위·판단은 [DevNote 9장](DevNote.md) |
| [`icg_archon.ini`](icg_archon.ini) | icg 설정 — `[icg]` 가 guide 컨트롤러 배선, `[hk]` 가 로깅, `[radionode]` 가 Tapaculo365 Open API 접속(콘솔의 "OPENAPI 매뉴얼" 값을 옮겨 적는다) |
| [`tools/gen_guidecards.py`](tools/gen_guidecards.py) | guide 견본 헤더 → `icg_archon/guidecards.py` 생성기 — 견본이 개정되면(v1.1 승격) 다시 돌린다.  `--diff` 는 science 폭 대조만 |
| [`INSTALL.md`](INSTALL.md) | ⭐ **벤치 설치 문서** — `~/AIC` 한 벌 세우기(XIS·OBSAgent·TCSAgent·ICS) · 기존 설치 이전 · 이상할 때 |
| [`tests/`](tests/) | **실기 없이 돌리는 검증** — `python -m pytest tests` (약 5분). 배치본은 `-m "not repo_only"`.  ⛔ **항목 수를 여기 적지 않는다** -- `python -m pytest --collect-only -q` 꼬리가 정본이고, 적어 두면 커밋마다 밀린다 (2026-09-09 에 300/244 가 실제 656/598 과 어긋난 것을 걷어냈다).  ⚠️ `ics_sim` 스위트와 **동시에 돌리지 말 것** — 부하로 `test_shutdown_waits_for_frames…` 가 간헐 실패한다 |
| [`tools/probe_archon.py`](tools/probe_archon.py) | ⭐ **실기 첫 실행 도구** — 미검증 3자리를 컨트롤러에 직접 물어본다 (1단계는 전원을 켜지 않는다) |
| [`tools/ics_archon_buftest.py`](tools/ics_archon_buftest.py) | **`LOCK`/`FETCH` 2x2 회귀 시험** — 엔진 라인 속도를 `idle`·`lock`·`fetch`·`nolock` 넷으로 견준다 (본편 무수정). 2026-09-01 실기 결론은 [`archon_lock_fetch_report.md`](archon_lock_fetch_report.md) |
| [`tools/extract_timing_script.py`](tools/extract_timing_script.py) | **ACF 의 타이밍 스크립트를 뽑는다** — `acf/acf_timing_script_{guide,science}.txt` 의 절차 정본. `--check` 로 대조, `--out` 으로 재추출.  ACF 를 고쳤으면 반드시 다시 뽑는다 (`tests/test_timing_script_extract.py` 가 지킨다) |
| [`tools/sync_vendor.py`](tools/sync_vendor.py) | **`ics_sim` 내장본 동기화** — `ics_archon` 만으로 돌게 만드는 자리. `--check` 로 확인만 |
| `ics_archon/_vendor/ics_sim/` | **내장본** (원천의 사본 + `MANIFEST.sha256`). 손으로 고치지 말고 `sync_vendor.py` 로 갱신한다 |
| [`acf/`](acf/) | **Archon 설정 파일 정본** (현행 7개 = science 6 + guide 1, `archive/` 구판 4개, 타이밍 스크립트 발췌 txt 2장) — 컨트롤러에 그대로 밀어 넣는 설정·타이밍. `BIGBUF` 가 science(1)/guide(0)를 가른다.  목록·주의는 [`acf/README.md`](acf/README.md) |
| [`scr_labtest/README_labtest.md`](scr_labtest/README_labtest.md) | ⭐ **실험실 취득 스크립트에 관한 모든 것** — 돌리기 전에 손볼 자리 · 첫 실행 점검 · 경고의 뜻 · 변경 내역 · 판 이력 |
| [`scr_labtest/archon_kmtnet_labtest_v1.3.bigbuf.py`](scr_labtest/archon_kmtnet_labtest_v1.3.bigbuf.py) | ✅ **현행 실험실 취득 스크립트** (`v1.3.4`, science 유닛).  유닛별 사본 셋(`KMTC-102`·`KMTC-113`·`KMTS-101`)이 나란히 있고 `tests/test_labtest_spec_copy.py` 가 표류를 막는다 |
| [`scr_labtest/archon_kmtnet_labtest_v1.3.smallbuf.py`](scr_labtest/archon_kmtnet_labtest_v1.3.smallbuf.py) | **small buffer 주소 지정 참고 코드** (`v1.3.4`) — 그 자체는 science 스크립트다.  guide 를 세울 때 본다 |
| [`tests/verify_labtest_v13.py`](tests/verify_labtest_v13.py) | **labtest 전용 검증** (32항목, 실패 0이어야 한다) — `python tests/verify_labtest_v13.py`.  읽기전용 자리 1건은 POSIX 에서만 돌고 윈도우에서는 `SKIP` |
| ⭐ [`icg_first_run.md`](icg_first_run.md) | ⭐ **guide 첫 구동 체크리스트** — 0~6단계 · 무엇을 적나 · 무엇이 나오면 멈추나. science 의 "실기 첫 실행 절차" 짝이고, `icg_archon` 을 실기에 붙일 때 여기부터 |
| ⭐ [`DevNote.md`](DevNote.md) | **개발 노트** — 과정·판단 근거·시사점. "왜 이렇게 됐나" 는 여기 |
| [`SMC_CLAUDE.md`](SMC_CLAUDE.md) | **인수인계** — 상태 · 브랜치 · 절대 깨뜨리면 안 되는 것 · Archon 매뉴얼이 말하는 것(**확인 상태 표시**) |
| `__ref_archon_control/` | **읽기 전용 참조** — v1.0 원본 2부 + STA Archon 매뉴얼(2021-02-23) + ZTF Readout Notes(2014-10-30).  ⚠️ **매뉴얼은 판정 근거가 아니다** — 현행 FW 와 양방향으로 어긋날 수 있다(DevNote 8.7) |

`__` 접두 폴더는 읽기 전용이다 — 편집이 필요하면 이 루트로 사본을 떠서
작업한다(운영자 규칙 2026-08-22). `scr_labtest/` 의 **v1.1~v1.3.4 계보가 바로 그
사본**이고, v1.0 원본은 `__ref_archon_control/` 에 남아 있어 이력이 보존된다.

> **용량 메모** (2026-08-22 실측): `__ref_archon_control/` 의 PDF 2부(4.1 MB)는
> 저장소에 **각각 한 부뿐이다** — `cam_char/archon/` 을 포함해 다른 사본이 없다.
> 중복인 것은 v1.0 스크립트 2개(루트 사본)뿐이고 합쳐 100 KB 다.  저장소 전체
> 중복은 **21.3 MiB / 608 그룹**이고 그중 **20.5 MiB 가 `ics_legacy/`**(3사이트
> DTS 백업이 같은 파일을 3~9벌 보유) 다 — 나중에 용량을 확보할 때 볼 곳은
> 거기다.  `raw_fits_spec/__reference/` 가 PDF 포함 46개를 추적하는 선례가
> 있어 참조 자료를 저장소에 두는 것 자체는 이 저장소의 관례다.

## 실험실 취득 스크립트 — 핵심 참고사항

세부는 전부 **[README_labtest.md](scr_labtest/README_labtest.md)** 에 있다. 여기서는
폴더를 처음 보는 사람이 알아야 할 것만 적는다.

- **현행은 `v1.1.2`** (science 유닛, BIGBUF=1). v1.0 원본은 **실제로 돌려서 쓰던
  검증된 코드**이고, v1.1 은 그 위에 raw spec 을 얹은 개정판이다.
- **컨트롤러와의 왕복에서 v1.1 이 추가한 명령은 `STATUS` 하나뿐**이다. 그래서
  `TELEMETRY_ENABLE = False` 로 두면 왕복이 v1.0 과 완전히 같아진다 — 실기에서
  문제가 보일 때 원인을 가르는 첫 수단이다.
- **실기로는 한 번도 돌리지 않았다.** 헤더·파일명·검증 하네스는 통과했지만
  POWERON → FETCH 왕복은 미검증이다.
- **산출물 규격이 통째로 바뀌었다** — 파일명 `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits`,
  헤더 **180 레코드**(값 카드 136 + COMMENT 8 + `END` 1 + 공백 35 = 5x2880 =
  14,400B, 견본 바이트 재현), 날짜는 UTC.  ⚠️ **144 레코드·11,520B 는 이제
  guide 쪽 수다** -- science 는 v1.10 의 HK 5장까지 실어 180 으로 늘었다
  (견본 `raw_fits_spec/header_samples/` 실측 2026-09-09). **기존 분석 스크립트는 glob 패턴과
  카드명을 갱신해야 한다.** ⚠️ raw spec v1.5(2026-08-26 반영)로 `<SITE>` 넷째
  코드가 `KMTT`→**`KMTK`**, HK 4장 폐지, `CHMAP_*` 토큰 3자→**4자** 가 됐고,
  **v1.6 으로 `ORIGNAME` → `EXPID`**(값에 `DETID` 필드(`.MK`/`.NT`)가 없어 pair 양쪽이
  같다 — 짝을 잇는 단일 키다) · `Cn_*` 나열 구분자가 공백 → **`|`** 가 됐다.
- **같은 UT 날짜의 재실행은 멱등하지 않다** (D-016 이 번호를 밀어 올린다 —
  v1.0 은 덮어썼다). 날짜가 다르면 영향 없다.
- **첫 실기 실행은 1프레임 연막시험으로.** 활성 실행 블록 그대로면 63프레임 /
  21.18 GiB 다.
- **헤더에 들어가는 손편집 문자열은 ASCII 전용**이다. 한글 한 자로 FITS 가
  통째로 깨지므로 기동에서 거부한다.
- **guide 유닛은 미개정** — guide raw 규격이 아직 없어서다.

## 본편 `ics_archon/` — 구성

`ics_sim` 의 시퀀서·명령 처리부·메시지 규약·헤더 층을 그대로 쓴다.  **독립
배포를 위해 내장본을 함께 들고 다니고**(`_vendor/ics_sim`), 저장소에서는 형제
원천이 이긴다 — 탐색 순서와 갈라짐 방지는 위 "설치 · 배치" 참조.

| 모듈 | 하는 일 |
|---|---|
| `archon/protocol.py` | 저수준 왕복 — 텍스트/이진 프레이밍, 참조번호, 시한 초과 후 재동기 |
| `archon/parse.py` | `SYSTEM`/`STATUS`/`FRAME` 해석. **왕복이 없어** 실기 응답 한 줄로 재현할 수 있다 |
| `archon/controller.py` | 컨트롤러 한 대의 제어 시퀀스 — ACF · 전원 · 노출 · 독출 · FETCH (asyncio) |
| `archon/monitor.py` | 텔레메트리 주기 감시·기록 (층 1·2) — CSV, `~/AIC/Logs/` |
| `archon/fitswrite.py` | raw pair 바이트 기록 — 견본 v1.0 이 정본, 데이터부 2880B 패딩 |
| `archon/backend.py` | `ics_sim` `DetectorBackend` 구현 (D-012) |
| `app.py` · `__main__.py` | `ics_sim.IcsSim` 에 백엔드를 끼우고 `ICSBUILD`/`RDMODE`/`CTRLnCFG`/종료를 갈아낀다 |
| `config.py` | `[archon]` 절 |

### 계약과 실기의 어긋남 — 백엔드가 흡수하는 셋

| 계약 | 실기 | 흡수 방식 |
|---|---|---|
| `initialize(ccd, …)` CCD 4회 | 컨트롤러 2대 | suffix 로 중복 제거 — `APPLYALL` 은 프레임마다 되풀이할 수 없다 |
| `erase(ccd)` master 한 번 | 두 대 다 비워야 한다 | 살아 있는 컨트롤러 전부에 퍼뜨린다 |
| 노출을 걸 자리가 없다 | `IntMS` + `LOADPARAMS` | 셔터 노출은 `open_shutter()`, DARK/BIAS 는 `readout()` 첫머리 |

**적분은 컨트롤러가 잰다.**  시퀀서의 카운트다운은 관측자 알림이고 하드웨어를
몰지 않는다.  그래서 `STOP` 은 적분을 자르지 못하고 셔터만 강제로 닫는다 —
근거와 한계는 `archon/controller.py` 머리말에 있다.

## 텔레메트리 감시·기록 (층 1·2)

컨트롤러 온도 10 + 전원 레일 7×2 + **바이어스 16채널 V/I** 를 주기적으로 떠서
CSV 로 남긴다.  원장 v1.14 가 `CCDTEMP` 대표 센서를 두고 **"센서 이상은 취득 SW
로그가 담는다"** 고 약속해 뒀는데 그 로그가 없었다 — 이것이 그 이행물이다.

```
~/AIC/Logs/telemetry.MK.20260828.csv       # 컨트롤러당 · 날짜당 하나
~/AIC/Logs/telemetry.NT.20260828.csv
```

| 열 | 무엇 |
|---|---|
| `utc` `age_ms` `lag_ms` | 시각 · 값의 나이 · **주기가 밀린 정도** |
| `expstatus` | ⚠️ 이 온도가 **독출 중 값인지 대기 중 값인지** — 사후에 시각으로 맞출 수 없다 |
| `valid` `count` `fresh` `log_n` | 응답 자체의 건강 (`fresh` = `COUNT` 가 직전 행과 달라졌나) |
| `power` `powergood` `overheat` | 전원·과열 |
| `T1..T10 [C]` | 규격 5.6.1절 **자리 = 항목** (열 이름이 `rawhdr.TEMP_MOD_LABELS`) |
| `V1..V7 [V]` `I1..I7 [A]` | 시스템 레일 — ⚠️ 전류 단위 **A** |
| `rail_flag` | 매뉴얼 p.41 정상 범위 이탈 (막지는 않는다) |
| `B_<라벨>_V [V]` `_I [mA]` | 바이어스 — ⚠️ 전류 단위 **mA**.  이름표는 **ACF** 에서 온다 |
| `event` | `start` `stop` `offline` `poll_failed` `resumed` |

**설정** (`[archon]`):

```ini
monitor          = true      # telemetry=false 면 이 값과 무관하게 안 돈다
monitor_interval = 20.0      # 수십 초 ~ 수 분 (운영자 확정)
monitor_log      = ~/AIC/Logs
```

### 접속자는 컨트롤러당 하나다 (운영자 확정 2026-08-28)

**본편이 기동에서 컨트롤러에 접속하고, 그 뒤에 감시를 시작한다.**  science
컨트롤러는 `ics_archon` 이, guide 는 `icg_archon` 이 맡고 **한 컨트롤러에 여러
노드가 붙는 구성은 두지 않는다.**  감시는 별개 프로세스가 아니라 이 프로세스
안의 태스크이고 **같은 소켓·같은 락**을 탄다.

- 접속은 `monitor` 설정과 **무관하다** — `monitor = false` 로 둬도 기동에서
  붙는다(그 스위치는 CSV 기록과 주기 폴링만 끈다).
- 기동 접속이 실패해도 **기동을 막지 않는다** — 컨트롤러 전원이 나중에 들어오는
  배치가 실재한다.  감시가 `monitor_interval` 마다 다시 시도하고, 감시를 껐으면
  첫 노출의 `prepare()` 가 시도한다.
- ⚠️ 그래서 **본편이 떠 있는 동안에는 STA GUI 도 `probe_archon` 도 붙이지
  않는다** — 설정으로 피하는 것이 아니라 **본편을 내리고 쓴다.**  Rev F
  백플레인(KASI 벤치기 `KMTK_SCI_113` · guide 유닛)은 동시 접속이 하나뿐이고
  (매뉴얼 p.15), Rev H(4접속)에서도 규칙은 같다.

**알아 둘 것 넷:**

1. **헤더용 값과 다른 자리에 든다.**  `Cn_TEMP/VOLT/CURR` 의 뜻은 여전히 "노출
   개시 시점 값" 이고, 감시는 `ctrl.status_live` 만 갱신한다.  섞으면 카드의
   뜻이 **폴링 간격·락 경합에 따라 노출마다 달라지는 값**으로 조용히 바뀐다.
2. **FETCH 가 락을 344 MiB 동안 쥔다** — 그동안 주기가 밀린다.  그것은 오류가
   아니라 `lag_ms` 에 적을 사실이고, **밀린 만큼 몰아서 뜨지 않는다.**
3. **`valid=0` 행도 버리지 않는다** — 언제부터 이상했는지가 자료다.  같은 응답이
   **헤더에서는 `NC`** 로 떨어진다(D4).
4. **`FETCHLOG` 는 쓰지 않는다** — `LOG=n` 한 열만 남긴다 (왕복 0).  드레인
   승격은 `probe_archon` 1단계로 한 번 보고 판단한다.

## Radionode 는 **폴링값으로 답한다** (운영자 확정 2026-09-09)

`HKDATA`/`HK` 응답도 FITS 헤더도 **폴러가 60초 주기로 받아 둔 값**을 쓴다 —
명령이 올 때 클라우드를 다시 치지 않는다.

| | 원천 | 왕복 |
|---|---|---|
| **guide 유닛** 측정값(RTD·진공·`HTROUT`) | 폴러의 최근 값(60초) | 왕복 없음 |
| **guide 유닛** 설정값(`HTREN`·`HTRSET`·`HTRFORCE`) | ⏳ **검토 중** — 지금은 명령마다 `RCONFIG` | ⭐ 3회가 **6 ms** (한가할 때 실측) |
| **Radionode**(`HEBOX`·`FSATEMP`·`FSAHUM`) | 폴러의 최근 값 | 왕복 없음 |

⭐ **즉시 조회해도 더 신선해지지 않는 것**이 핵심 이유다 — 장치가 60초마다
클라우드로 올리므로 언제 물어도 같은 값이다. 그 밖에 인터넷 왕복(수백 ms~초),
**쿼터 분당 10회**, 블로킹 HTTP(스레드로 도는 이유)가 겹친다.

⚠️ 낡음은 숨기지 않는다 — `stale_after`(= 전송주기 ×3 = 180초)를 넘으면
sentinel 이고, `HKUDATE` 는 **guide 유닛 측정값만** 기준으로 한다.

### ✅ guide 유닛 **설정값**도 명령마다 되읽는다 (실측으로 정함 2026-09-09)

⭐ **갈리는 것은 왕복 시간이 아니라 "어떤 값이냐" 였다** (운영자: *"히터나 trigger
출력의 실시간 반영이 문제로구나"*).

| | 60초에 얼마나 변하나 | 폴링값으로 되나 |
|---|---|---|
| 측정값 (RTD 4·진공·`HTROUT`·Radionode 3) | 서서히 | ✅ 된다 — 낡음은 `HKUDATE`·`HKSTALE` 이 알린다 |
| 설정값 (`HTREN`·`HTRSET`·`HTRFORCE`) | ⚠️ **운영자가 방금 바꾼다** | ⛔ 안 된다 — `htrset 1 -95` 바로 뒤 `hkdata` 가 옛 값을 낸다 |

⭐ **결론: 지금대로 명령마다 `RCONFIG` 3회 를 유지한다.**  근거는 실측이다 —
**취득 중에도 `HKDATA` 전체가 중앙 7.7 ms · 최악 108 ms** 라 왕복 셋을 없애 벌 것이
없다 (아래 결과표).

⚠️ 남는 것 하나: **헤더와 `HKDATA` 의 원천이 갈려 있다** — 헤더는 HK 폴링값(`_sample`,
60초), `HKDATA` 는 명령마다 `RCONFIG`.  ⭐ 값은 같고 신선도만 다르며 **둘 다 맞다** —
헤더는 그 프레임 시각의 값이 맞고 `HKDATA` 는 지금 값이 맞다.

⭐ 그리고 확인하는 길이 따로 있다 — `HTRSET`·`HTRFORCE`·`TRIGOUTFORCE`·`TRIGOUTLEVEL`
은 **인자 없이 치면 조회**고 그 갈래는 `RCONFIG` 즉시 되읽기다.

## `HKDATA` 는 두 갈래다 (운영자 확정 2026-09-09)

```
HKDATA          ← 폴링값 (60초 주기).  왕복 없음
HKDATA NOW      ← 히터 설정 셋만 RCONFIG 즉시 되읽기
HK / HK NOW     ← 같은 본문
```

⭐ **`NOW` 는 HK 한 바퀴를 지금 돌린다** — RTD·진공·`HTROUT`·히터 설정·Radionode 가
다 갱신되고, **폴링 값(그리고 다음 FITS 헤더)도 그 값이 된다**.
⚠️ **Radionode 만 제동이 있다** — 표본이 **`[radionode] now_min_age`(기본 60초)** 보다
낡았을 때만 클라우드를 다시 친다.  ⛔ 쿼터가 **api_key 당 분당 10회**라 태우면 **주기
폴링까지 실패**하고, ⭐ 즉시 조회해도 더 신선해지지 않는다(장치가 60초마다 올린다).
⛔ 이 눈금을 `poll_period` 나 장치의 `device_interval` 에서 **파생시키면 안 된다** —
전자는 늘리면 재조회까지 막히고, 후자는 배우기 전 값이 1333초다.

⭐ **`HKDATA NOW` 뒤에는 주기 기준이 60초 뒤로 밀린다** — 방금 돌린 바퀴 몇 초 뒤에
주기 바퀴가 또 도는 낭비를 막는다.

⭐ 기본이 폴링값인 것의 가장 큰 이득은 **FITS 헤더와 `HKDATA` 가 같은 원천을 보는 것**
이다 — 같은 순간에 둘이 다른 값을 낼 수 없다.

⭐ **주기 바퀴(60초)는 왕복이 도는 중이면 비켜 준다** — 최대 1초.  ⛔ 상한이 있는 것이
요점이다: guide 는 연속 취득이라 *"안 바쁠 때까지"* 를 곧이곧대로 쓰면 HK 가 영영 안
돌고, **히터 과열 차단까지 멈춘다**.
⚠️ 낡음은 `HKUDATE`(가장 낡은 표본시각)·`HKSTALE` 이 그대로 알린다.
⭐ 방금 바꾼 값을 확인하려면 `HKDATA NOW` 이거나, `HTRSET`/`HTRFORCE` 를 **인자 없이**
치는 조회(늘 `RCONFIG` 즉시)다.
⚠️ `NOW` 가 실패하면 **폴링값으로 물러난다**(빼지 않는다).  ⛔ 모르는 인자는 거절한다.

## 로그 파일 — 날마다 갈아탄다 (운영자 지시 2026-09-09)

```ini
[logging]
file        = ~/AIC/Logs        ; 폴더 → icg.<YYYYMMDD>.log
```

⭐ **`.log` 로 끝나면 그 파일 하나, 아니면 폴더**다 (옛 설정은 그대로 돈다).
재실행해도 지우지 않고 **덧붙인다**.  날짜는 **UTC** — `HKQDATE`·`DATE-OBS`·FITS
파일명과 같은 경계를 쓴다.
⚠️ 로그 시각도 UTC 로 고정했다 — 종전에는 지역시라 한국시 기계에서 +9 시간 어긋났다
(벤치가 UTC 라 안 드러났던 자리).

### 화면을 조용하게 — `verbose` (운영자 지시 2026-09-11)

```ini
[logging]
verbose     = on        ; off 면 화면만 간결.  on|true|yes|1|enable|high 와 그 반대편
```

⭐ **화면만 간결해지고 로그 파일은 언제나 전부다.**  화면에서 안 보인 줄이 파일에는
있으므로, 벤치에서 *"그 줄 못 봤는데"* 로 판정하면 안 된다.

`verbose = off` 에서 화면에 남는 줄을 **함축 메시지(essential message)** 라 한다.
빠지는 것은 **프로그램이 스스로 주고받는** 줄들뿐이다:

| 빠진다 | 남는다 |
|---|---|
| `AUXSTATUS`/`TCSSTATUS` 자동 왕복 | 명령과 그 응답 (`EXEC:` · `DONE:` · `ERROR:`) |
| `PING`/`PONG` 핸드셰이킹 | `EXPSTATUS=…` · `PCTREAD=…` · `Wrote …` |
| 매번 같은 값인 `LOADPARAMS` 왕복 경고 | 경고·오류 전부 (딸린 한글 설명만 떨어진다) |

⚠️ **`wire = off` 와 다른 물건이다** — 그쪽은 와이어 줄을 **아예 안 남긴다**(파일에도
없다).  자취를 지우는 눈금이라 운영에서는 켜 둔다.

⭐ 문구는 **영문 한 줄 + 딸린 세부**다.  세부(한글 설명 · 버퍼·주소 같은 값)는
`verbose = off` 화면에서만 떨어진다:

```
verbose off :  fetch frame 12: 8.3 MiB in 0.1s
verbose on  :  fetch frame 12: 8.3 MiB in 0.1s  --  buf 3, base 0xE0000000, lock=True …
```

### 노출 국면 — `EXPSTATUS`

| 낱말 | 언제 | 비고 |
|---|---|---|
| `INITIALIZING` | 사이클 개시 | |
| `ERASE` | **flush 창** (guide 실측 1.25초) | ⭐ 2026-09-11 신설 자리 — 종전엔 이 창이 `INTEGRATING` 이라 거짓이었다 |
| `INTEGRATING` | 적분 | guide 는 **사이클마다 한 번**, science 는 노출마다 |
| `READOUT` | CCD → 컨트롤러 버퍼 | 진행률이 `PCTREAD=` 로 함께 나간다 |
| `FETCH` | 컨트롤러 버퍼 → 호스트 | ⭐ **신설** — guide 0.1초 · science ≈4초(추정, 344 MiB) |
| `WRITING` | 호스트 → FITS 파일 | guide 0.06초 · science ≈1.7초(추정) |
| `IDLE` / `ERROR` | 종료 | |

⛔ **`FETCH`/`WRITING` 은 알림일 뿐 국면 변수를 안 바꾼다** — 저장은 다음 노출과
겹쳐 도는데(정상 운영), 변수를 여기서 바꾸면 진행 중인 프레임의 국면을 덮어쓰고
그 변수를 보고 판단하는 자리(`GO` 거절 · `STOP` 응답)가 틀린 국면을 본다.

## ✅ 연속 노출 중 명령 지연 — **실측 결과** (2026-09-09 벤치)

운영자 물음: *"guide 유닛 timing script 가 돌고 연속 촬영 중일 때 `trigout <초>`
명령 실행 지연 여부"*.

⭐ **막히지 않는다** — 거부도 대기도 없고, `cmd_trigout` 은 즉시 `Reply.noop()` 을 내고
실제 왕복은 따로 돈다.  취득 중이라고 막는 문이 이 명령에는 없다.

### 결과 (`icg_archon.20260909.002.log`, `go 100`+`go 20`, 재동기 **0회**)

| | n | 중앙 | 최대 | 95% |
|---|---|---|---|---|
| `HKDATA` **한가** | 9 | **7.0 ms** | 10.5 | 8.7 |
| `HKDATA` **취득중** | 51 | **7.7 ms** | **107.8 ms** | 96.5 |
| `TRIGOUT` 올림 **한가** | 13 | **232.5 ms** | 236.4 | 234.1 |
| `TRIGOUT` 올림 **취득중** | 26 | **233.8 ms** | 337.4 | 259.6 |

⭐ **`HKDATA` 는 취득 중에도 중앙 7.7 ms** — 한가할 때와 사실상 같다.  50 ms 를 넘은
것은 **51회 중 7회(14 %)** 이고 최악이 108 ms 다.  ⚠️ 그 14 %가 곧 *"FETCH 가 락을 쥐고
있을 확률"* 이다 — 기하로 셈한 6 %(0.08 s ÷ 1.251 s)보다 큰데, FETCH 뒤에 저장·재대조
왕복이 붙어 실제 점유가 더 길기 때문이다.

⛔⛔ **`TRIGOUT` 은 한가할 때도 233 ms 다.**  ⭐ **락 경합이 아니라 `APPLYSYSTEM` 자체가
그만큼 걸린다** — `WCONFIG` 둘이 ~4 ms 이니 **`APPLYSYSTEM` ≈ 229 ms**.  취득 중
추가분은 중앙 **+1.3 ms**(최악 +104 ms)뿐이라, **늦추는 것은 취득이 아니라 컨트롤러
자신**이다.  ⚠️ 앞서 잰 `LOADPARAMS 240 ms`·`RESETTIMING 246 ms` 와 같은 자릿수다 —
**APPLY 계열은 다 200 ms 대**로 본다.

### ⛔ 펄스 폭이 **+235 ms 계통 초과**였다 — 고쳤다

```
폭오차: n=17  중앙 +235.1 ms  범위 +233.6 ~ +251.3   (요청 2 s)
```

17회 내내 일정했다 — 잡음이 아니라 계통 편향이다.  종전 코드는 `sleep(<초>)` **뒤에**
내림 왕복을 보냈으므로 핀이 `<초> + 내림 적용시간(≈233 ms)` 동안 HIGH 였다.
⚠️ 2 s 요청에 11.8 % 초과이고, **0.5 s 면 +47 %** 다.

✅ **고친 뒤 확인 실측**: `go 20` 중 `trigout` 11회(2·3·5 s)에서 폭오차 **중앙 +1.7 ms ·
범위 −2.7 ~ +7.9 ms** — 종전 +235 ms 에서 **99 % 가 사라졌다**.  ⭐ 요청 폭을 키워도
오차가 안 커진다(더해지는 상수였다는 진단이 맞았다).

⭐ **고침: 잠들 시간에서 방금 잰 올림 비용을 뺀다.**  적용 하나에 `C` 가 걸리고 핀이 그
안 비율 `f` 에서 뒤집힌다면 HIGH 는 `t+fC`, LOW 는 `t+C+잠+fC` 이므로 **폭 = 잠 + C**
이고 `f` 가 지워진다 — **핀이 적용 중 언제 뒤집히는지 몰라도 옳은 보정**이다.
⚠️ **실현 최소 폭 ≈ 235 ms** — 그보다 짧으면 0 으로 눌러 담고 경고한다.  더 짧은 펄스가
필요하면 타이밍 스크립트(ACF)로 몰아야 한다.

#### ⛔ *"올림·내림 적용시간이 같으면 상쇄되지 않나?"* — 안 된다

⭐ 두 에지의 간격은 **두 명령을 보낸 간격**과 같다 (핀이 적용 중 어디서 뒤집히든 그
지연이 양쪽에 똑같이 붙어 지워진다).  ⛔ 그런데 **보낸 간격이 `<초>` 가 아니라
`<초> + C`** 였다 — **잠들기를 올림 왕복이 *끝난 뒤에* 시작**했기 때문이다.  올림의
적용시간은 시계가 돌기 **전**에, 내림의 것은 시계가 멈춘 **뒤**에 들어가므로 둘이
마주 보지 않고 **더해진다**.

⭐ 실측이 그대로다 — 상쇄된다면 폭오차가 0 이었을 텐데 **17회 내내 +235 ms** 였다.
고침은 **보낸 간격을 `<초>` 로 만드는 것**이다: `잠 = <초> − C`.

### ⭐ 취득은 해치지 않는다

`go 20` 이 **20장을 다 찍었다**(`000076`~`000095`).  그 사이 `trigout 2` 를 4회 쳤다(당시 인자는 **초**다 — 지금 눈금은 ms 라 같은 펄스가 `trigout 2000` 이다) —
걱정하던 *"`APPLYSYSTEM` 이 `Exposures` 를 되돌린다"* 는 일어나지 않았다.

⚠️ `독출 완료 간격이 밀렸다` 가 8건 났지만 **명령과 상관이 없다** — 가장 가까운 명령까지
−0.40 ~ +1.40 s 로 흩어지고 **넷은 명령보다 먼저** 났다.  크기도 1.466~1.468 s 로 거의
일정하다.  ⏳ 종전부터 열려 있던 *"원인 미상 — 첫 구동 실측 항목"* 그대로다.

### 다시 재려면

`~/AIC/Config/icg_archon.ini` 에서 임계를 0 으로 두면 전부 남는다.
⭐ **실측용 설정이다** — 끝나면 운용값으로 되돌린다.

```ini
[icg]
latency_warn_ms = 0
```

⛔ `TRIGOUT` 은 **이 눈금을 안 탄다**(늘 남긴다).  임계를 타는 것은 `HKDATA`/`HK` 뿐이고,
그 이유는 **바깥 감시 계통이 자주 물어 올 수 있어서**다 — 우리 프로그램에는 주기
발신자가 없다.  ⭐ 운용값 **150 ms 는 실측 최악(108 ms) 위**로 잡은 것이다.

```
guiexp 1.3
expenable on
go 60
trigout 2000   ← 연속 노출 중에 여러 번 (⚠️ 단위는 **ms** 다)
hkdata         ← 연속 노출 중에 20회 이상 (락 경합이 14 % 라 적게 치면 최악값을 못 잡는다)
```

로그(`icg_archon.cmd`)에 이런 줄이 남는다:

```
HKDATA 지연 -- 수신→완료 96.5 ms (취득중)
TRIGOUT 올림 지연 -- 수신→완료 233.8 ms (취득중) Sec=2
TRIGOUT 내림 지연 -- 수신→완료 2236.1 ms (취득중) 폭오차 +1.2 ms (요청 2s, 보정 -234 ms)
```

⭐ **가장 중요한 값은 폭오차다** — 시작이 밀려도 폭이 맞으면 광원 노출량은 맞는다.
보정이 들어갔으므로 **0 근처여야 한다**; +235 ms 가 그대로면 보정이 안 먹은 것이다.
⛔ 이 지연은 **락 대기 + 왕복 처리**를 합친 값이라 둘을 가르지 않는다.

## Radionode 자격증명 — Tapaculo365 Open API (운영자 지시 2026-09-03)

`HEBOX`·`FSATEMP`·`FSAHUM` 세 카드의 원천이다.  ⚠️ **장치(RN320-BTH)는
LoRaWAN 이라 LAN 폴링이 안 된다** — IP 스택이 없어 LoRa 게이트웨이를 거쳐
클라우드로만 간다.  그래서 접근은 **Tapaculo365 Open API 폴링** 하나뿐이고,
endpoint 상세가 콘솔 로그인 뒤의 문서에만 있어 **URL·경로·인증 헤더 이름까지
ini 소관**이다 (코드에 박으면 계정이 바뀔 때 코드를 고쳐야 한다).

### 옮겨 적을 값 **둘** (+ 장치 MAC 둘)

| ini 키 | 무엇 | 콘솔에서 어디 |
|---|---|---|
| `api_key` | API KEY | `s2.radionode365.com` → **고객사 정보변경** → API Key/Secret |
| `api_secret` | API SECRET | 같은 자리 |

⭐ **나머지는 코드가 안다** (2026-09-08, DevNote 11.44).  `base_url` 은 ini 에 실값
(`https://oa.radionode365.com`)이 있고 `api_path` 는 기본 `/tp365/v1` 이다.
⛔ **`latest_path`·`key_header`·`secret_header` 는 폐기됐다** — 이 API 는 인증을
**POST 본문 파라미터**로 받고(헤더 인증 자리가 없다) 값은 `channel/get_lst` 한 번으로 온다.
ini 에 남아 있으면 **기동이 경고한다.**

장치 둘의 `device_mac`·별칭·계약 키는 `[radionode.hebox]` · `[radionode.fsa]` 에 있다
(HE box 는 온도만, FSA 는 온도+습도).  ⭐ `keys` 는 **채널 번호 순서로 짝짓는다**
(CH1=온도 ℃ · CH2=습도 %) -- 단위가 이름과 어긋나면 그 채널은 **안 싣는다**.

주기는 `poll_period`(기본 60 s -- ⛔ 쿼터가 **api_key 당 분당 10회**인데 우리는 한 바퀴에
**한 번**만 친다).  신선도 문턱 `stale_after` 는 **4000 s 초기값**이고, 한 번 읽으면 그
장치의 **`device_interval` x3** 으로 바뀐다 (API 가 전송주기를 알려 준다).

### ⛔ 실제 값을 저장소에 담지 않는다

`icg_archon.ini` 는 **저장소에 있는 배포본**이다.  KEY/SECRET 은 벤치의
설치본(`~/AIC/Config/icg_archon.ini`)에만 적고, 저장소 쪽은 **주석인 채로 둔다.**
⚠️ 한 번 커밋되면 이력 재작성 없이는 못 뺀다.

### 확인 절차

```
RADIONODE STATUS      # Backend=off Polling=no Credentials=... missing
RADIONODE CONNECT     # ⭐ 런타임에 폴링을 켠다 (자격증명이 모자라면 이름을 댄다)
RADIONODE STATUS      # Backend=openapi Polling=yes hebox=ok 3s ago ...
RADIONODE RECONNECT   # 주기를 안 기다리고 즉시 한 바퀴
HK                    # HEBOX/FSATEMP/FSAHUM 이 실려 나오는지
```

⚠️ **`CONNECT` 는 ini 를 고치지 않는다** — 재기동하면 ini 값으로 돌아간다.
상시로 쓰려면 `[radionode] backend = openapi` 를 적어야 하고, 그때는 기동에서
바로 폴링이 돈다.  ⭐ `CONNECT` 는 *"값을 넣고 지금 되는지 보는"* 자리다.

⚠️ **`sim` 은 배선 확인용**이라 그 값은 **헤더 경로로 안 나간다** (고정 상수가
실측처럼 아카이브에 남으면 파일만 보고 못 가른다).  `sim` 에서는 `CONNECT` 를
거부한다.

### ⛔ 인터넷이 안 되는 사이트 — `local_lns` (⏳ 자리만 있다)

`openapi` 는 **클라우드 경로라 인터넷이 있어야 한다.**  끊기면 세 카드가 그동안
sentinel 이고, ⛔ **운영자는 그 결측을 받아들이지 않는다** (2026-09-04 확정).

⚠️ 그런데 **코드로는 못 막는다** — 자료가 들어오는 길이 클라우드 하나뿐이라
끊기면 값이 물리적으로 안 온다.  `stale_after` 를 늘려 옛 값을 계속 싣는 것은
결측을 없애는 것이 아니라 **틀릴 수 있는 값으로 덮는 것**이라 규격 5.0절
sentinel 의 정신에 어긋난다.

⭐ **실제로 막는 유일한 길**은 LoRa 게이트웨이를 **안쪽 LNS**(ChirpStack)로
돌려 클라우드 없이 받는 것이다.  센서 자체는 LoRaWAN(KR920)이라 IP 스택이 없어
LAN 으로 직접 못 받지만, **게이트웨이 아래로는 로컬로 받을 수 있다.**

| 선행 조건 | 왜 |
|---|---|
| ① LoRa 게이트웨이 **기종과 관리 접근** | LNS 주소를 바꿀 수 있어야 한다 (지금은 Tapaculo365 를 본다) |
| ② 장치 **가입 키** (DevEUI · JoinEUI · AppKey) | ⛔ 없으면 장치가 우리 서버에 **안 붙는다**.  Tapaculo365 에 프로비저닝돼 있으면 콘솔에서 꺼내거나 재등록해야 한다 |
| ③ 페이로드 코덱 | ✅ 공식 `rn320bth.js` 가 공개돼 있다 |

`[radionode] backend = local_lns` 를 적어 두면 *"이 사이트는 클라우드를 안
쓴다"* 는 뜻이 ini 에 남고, 기동이 **무엇이 먼저인지** 크게 알린다.  ⏳ 수집
구현은 위 ①②가 채워진 뒤다 (DevNote 11.22).

## 프레임이 안 나올 때 — `Sync In` 부터 본다

실기에서 **프레임이 한 장도 안 나오던 증상**의 원인은 `Sync In` 이 물려 상대
컨트롤러가 클록을 잡고 있던 것이었다 (labtest 2026-08-27 종결).  그때 관측된
조합이 이것이다:

⭐ **배선까지 좁혀졌다 (운영자 실기 확인 2026-09-04)** -- **master 의 `Sync Out`
이 이 유닛의 `Sync In` 에 연결되어 있으면 노출이 진행되지 않는다.**  발견해서
해결했다.  ⚠️ 그러니 유닛을 **한 대만** 돌릴 때(실험실 1유닛 · guide 첫 구동)는
**`Sync In` 을 비워 둘 것** -- 2대 구성의 배선을 그대로 남겨 두면 이 증상이 난다.

```
POWER=4  POWERGOOD=1  FRAME=0/0/0  (영구)
```

**`POWERGOOD=1` 은 하드웨어 정상을 보장하지 않는다** — 컨트롤러 **자기 전원만**
보고하고 외부 클록 의존을 보지 않는다.  그래서 `ics_archon` 은 프레임 대기에
시한을 두고, **시한을 넘기면 진단 한 장을 항상 남긴다**(`frame_dump` 설정과
무관):

```
ERROR ... 프레임 대기 시한 초과 -- RBUF=0 WBUF=0  FRAME=0/0/0  COMPLETE=0/0/0
          LINES=0/0/0  POWER=4  POWERGOOD=1  OVERHEAT=0  TIMER=...
```

| 보이는 것 | 뜻 |
|---|---|
| `FRAME` 이 안 오름 | 노출 미개시 — `LOADPARAMS`·타이밍·**Sync In** |
| `FRAME` 은 오르는데 `COMPLETE=0` | 독출이 버퍼를 못 채운다 — 기하·tap |
| `TIMER` 가 안 변함 | 타이밍 코어 정지 |

평상시에 계속 보고 싶으면 `[archon] frame_dump = 5` (초).  ⚠️ **정상 취득이
도는 동안은 꺼 둔다** — 한 번에 왕복이 셋 는다.

⚠️ **시한은 적분이 끝난 뒤부터 센다** (`frame_timeout`).  DARK/BIAS 는 컨트롤러가
적분을 재므로 `IntMS` 를 걸고 곧바로 기다리는데, 시한을 지시 시점부터 세면
600초 dark 가 300초 상한에 걸려 **정상 프레임 중에 `DMA WAIT TIMEOUT`** 이 난다.

## 설치 · 배치 (리눅스)

**`ics_archon/` 하나만 두면 돌아간다.** `ics_sim` 을 설치하지 않아도 된다 —
그 층을 `ics_archon/ics_archon/_vendor/ics_sim/` 로 **내장해서 함께 들고 다닌다**
(운영자 확정 2026-08-23). 파이썬이라 빌드·설치 단계도 없다.

```
/home/<사용자>/
├── CEU/                          개발용 클론 — 여기서 고치고 커밋한다
└── AIC/                         운영 자리 (레거시 dts 처럼 역할 기준)
    ├── src/ics_archon/           ★ 배포본 — 이 폴더 하나면 된다
    │   ├── ics_archon/           패키지 (_vendor/ics_sim 포함)
    │   ├── tools/  tests/
    │   └── ics_archon.ini        (참조용 원본. 실제 설정은 Config/ 로)
    ├── bin/
    │   ├── xis…                  컴파일 산출물 (관례상 여기)
    │   └── ics_archon            얇은 실행 래퍼 (6절)
    ├── Config/
    │   ├── ics_archon.ini        ← 배포본 사본을 고쳐 쓴다
    │   ├── ics_archon.expnum     ← 노출 번호 (ini 옆으로 자동 결정)
    │   └── acf/                  ← Archon 설정 파일
    ├── Logs/ics_archon.log
    └── data/                     ← raw pair. 실제 디렉터리든 심볼릭 링크든 된다
```

### 왜 내장본인가 — 그리고 갈라지지 않는 근거

`ics_archon` 은 `ics_sim` 의 시퀀서·명령 처리부·메시지 규약·헤더 층을 그대로
쓴다. 종전에는 형제 폴더를 `sys.path` 에 넣었는데, 그러면 **두 폴더를 항상 함께
옮겨야 했다.**

사본을 두면 갈라진다 — 그것이 종전에 사본을 안 만든 이유였다. **그 걱정의 실체는
"사본" 이 아니라 "몰래 갈라짐" 이다.** 갈라짐을 기계가 잡으면 사본을 두어도 된다:

| 겹 | 무엇을 잡나 | 원천이 없어도 되나 |
|---|---|---|
| `_vendor/MANIFEST.sha256` | 내장본 손상·손편집 | ✅ 배포된 트리의 자가 진단 |
| `tests/test_vendor.py` ② | **원천과 갈라짐** (개정 누락) | ❌ 저장소에서만 |
| `tests/test_vendor.py` ③ | 배선이 틀려 독립 실행이 안 되는 것 | ✅ |

③은 **`ics_archon/` 만 떼어 놓은 임시 트리에서 실제로 노출을 돌려** 확인한다.

`ics_sim` 을 고쳤으면 동기화한다 — 안 하면 저장소 시험이 **실패**한다:

```bash
python3 tools/sync_vendor.py            # 동기화
python3 tools/sync_vendor.py --check    # 확인만 (CI)
```

### 탐색 순서

| 순서 | 어디 | 언제 |
|---|---|---|
| 1 | `ICS_SIM_PATH` 환경변수 | 명시적 지정 (탈출구) |
| 2 | 형제 폴더 `../ics_sim` | **저장소에서 개발할 때** — 살아 있는 원천 |
| 3 | 내장본 `_vendor/ics_sim` | **독립 배포** |

기동 배너의 `ics_sim` 줄이 **어느 것을 골랐는지** 찍는다. 셋 다 없으면 찾아본
경로를 다 찍고 멈춘다 — 조용히 실패하지 않는다.

### 1. 준비

| | |
|---|---|
| Python | **3.10 이상** |
| 필수 | **`numpy`** — FITS 저장형 변환. 없으면 백엔드가 **기동에서 거부**한다 |
| 선택 | `astropy` — `probe_archon` 되읽기 확인과 시험에만. **취득에는 필요 없다** |
| 시험 | `pytest` |

### 2. 자리 만들기

```bash
mkdir -p ~/AIC/{src,bin,Config/acf,Logs,data}
```

`~/AIC/data` 를 다른 디스크로 보내려면 실제 디렉터리 대신 링크를 둔다
(대상이 **먼저** 있어야 한다 — 끊긴 링크면 거부된다):

```bash
mkdir -p /mnt/bigdisk/data && ln -s /mnt/bigdisk/data ~/AIC/data
```

### 3. 배포본 놓기

**방법 A — 폴더만 복사** (가장 단순. `ics_sim` 이 필요 없다):

```bash
cd ~/CEU && git checkout ics_archon-v0.1.0
python3 ics_archon/tools/sync_vendor.py --check     # 내장본이 최신인지
rsync -a --delete --exclude='__pycache__' --exclude='__ref_archon_control' \
      ics_archon/  ~/AIC/src/ics_archon/
```

**방법 B — 배포용 클론** (되짚기가 쉽다. `git describe` 로 "무엇이 돌고 있나"):

```bash
git clone <저장소> ~/AIC/src/CEU
cd ~/AIC/src/CEU && git checkout ics_archon-v0.1.0
git describe --tags
```
→ 이 경우 실행 경로는 `~/AIC/src/CEU/ics_archon` 이고, 형제 `ics_sim` 이 함께
있으므로 **탐색 순서 2번**(원천)이 쓰인다.

> **개발 클론(`~/CEU`)에서 직접 돌리지 않는다.** 야간에 `git pull` 이나 브랜치
> 전환이 일어나면 돌고 있는 코드가 바뀐다.

### 4. 설정

```bash
cp ~/AIC/src/ics_archon/ics_archon.ini ~/AIC/Config/ics_archon.ini
cp <어딘가>/KMTNet_Sci_*.acf            ~/AIC/Config/acf/
```

고칠 것 — **`[archon]` 이 컨트롤러 배선이다**:

```ini
[node]
observatory  = KASI                 # **사이트를 정하는 단 하나의 값**
                                    #   CTIO | SSO | SAAO | KASI
                                    #   적은 값이 그대로 OBSERVAT 카드가 되고,
                                    #   사이트 코드 KMTC/KMTA/KMTS/KMTK 가 유도돼
                                    #   파일명·좌표·ORIGIN·INSTRUME·TELESCOP·
                                    #   FPAID 를 함께 끌고 간다.  모르는 값은
                                    #   기동 거부.  ⚠️ D-017: 구 TESTBED/KMTT
                                    #   는 폐지됐다 -- 남아 있으면 기동이 멈춘다
ic_ids       = M.IC, K.IC           # 유닛 한 대만 돌릴 때 (2대면 4개)
cb_ids       = M.CB, K.CB

[paths]
data_dir     = ~/AIC/data
expnum_file  =                      # 비우면 ini 옆 ics_archon.expnum

[archon]
n_controllers = 1                   # 유닛 한 대만 돌릴 때.  2대면 2
ctrl_mk_host = 10.0.0.13
acf_mk       = ~/AIC/Config/acf/KMTC_SCI_101_STA0284_R2611_MK.acf
monitor      = true                 # 텔레메트리 주기 감시·기록 (위 절)
                                    #   ⚠️ 접속은 이 값과 무관하다 -- 본편이
                                    #   기동에서 붙는다.  이 스위치는 CSV 기록과
                                    #   주기 폴링만 끈다
monitor_log  = ~/AIC/Logs           # ⚠️ data_dir 밑에 두지 말 것
fetch_buffers = 2                   # 호스트 수신·저장 버퍼 (컨트롤러당)
wrote_window  = 25.0                # OBSAgent force_fitssaved 창 [s] -- 선언값
full_flush_on_erase = false         # clock 개선으로 별도 erase 를 하지 않는다
lock_buffer   = true                # fetch 중 프레임 버퍼를 LOCKn 으로 잠근다
fetch_timeout = 10                  # FETCH 상한 = 잠금 상한 -- 주기(13.27초) 아래 (DevNote 10.6)
recheck_after_fetch = true          # fetch 뒤에 덮이지 않았는지 한 번 더 대조

[controllers]
ctrl1_id     = KMTA-SCI-101         # 비우면 컨트롤러 보고값(BACKPLANE_ID)
ctrl1_sn     = STA-0288
ctrl1_cfg    =                      # 비우면 [archon] acf_mk 에서 파생 (아래)

[logging]
file         = ~/AIC/Logs/ics_archon.log
```

> ⭐ **호스트 수신 버퍼는 링이다** (2026-08-29). `[archon] fetch_buffers`(기본 **2**)
> 만큼만 잡아 **재사용**하고, 다 차면 FETCH 가 **기다리며 그 횟수를 센다**
> (`buf_waits`). 종전에는 프레임마다 344 MiB 를 새로 잡아 저장이 밀리면 메모리가
> 조용히 늘었다. ⚠️ **`wrote_window` 와 짝이다** — `N = ceil((창 − write_delay) /
> 주기)`. 25초 창엔 2개, **30초로 넓히면 3개**가 필요하고 기동에서 검사한다.
> 2개 = 1.4 GB · 3개 = 2.2 GB (벤치 RAM 32 GB).

> ⚠️ **매뉴얼은 판정 근거가 아니다** (운영자 2026-08-30). 개정판이 2021-02-23 이라
> **현행 FW 가 매뉴얼을 다 반영하지 않은 부분도, 반대로 매뉴얼에 있는데 FW 에 없는
> 경우도 있었다.** ⭐ **판단 근거는 실측**이고, 매뉴얼은 *무엇을 재야 하는지* 알려
> 주는 가설 생성기다. `lock_buffer` 기본값이 `true` 인 것도 *"매뉴얼이 그렇다"* 가
> 아니라 **실측으로 값이 확인됐기 때문**이다 (2026-09-01, 두 유닛) — 대가 0(`lock` =
> `idle` = 368 행/초), 지킬 구간 실재(`nolock` 에서 경계가 걸리면 엔진이 읽는 중인 버퍼로
> 옮겨온다, 2/2). 자세한 것은 `DevNote.md` 8.7 · 10.6.

> ⭐ **`FETCH` 로그 줄이 잠금 관측값을 싣는다** — `[lock=True RBUF=1 WBUF=0->2]`.
> `LOCK1` 을 보냈는데 `RBUF` 가 1 이 아니면 경고가 뜬다(그때는 `recheck_after_fetch` 가
> 유일한 방어다). ✅ 두 FW(1252·1261)에서 **15/15 반영**을 확인했으므로(2026-09-01,
> DevNote 10.4) 이 경고는 **FW 회귀 신호**다 — 종전의 "`RBUF` 미구현일 수 있다" 는 닫혔다.
> 왕복은 안 늘었다(덮임 대조가 이미 읽는 `FRAME` 에서 뽑는다).

> ⭐ **fetch 중에 버퍼가 덮이는 것을 두 겹으로 막는다** (2026-08-30).
> `lock_buffer`(기본 `true`)가 `LOCKn` 으로 **막고**, `recheck_after_fetch`
> (기본 `true`)가 fetch 뒤에 한 번 더 대조해 **덮였으면 그 자료를 버린다**.
> fetch 앞의 대조는 직전 한 순간만 보는데 fetch 자체가 3.2~3.5초라(2026-09-01 실측), 그 사이에 덮이면
> **앞뒤가 다른 누더기 파일**이 길이·헤더 정상으로 나온다 — 로그에도 안 남는다.
> ⭐ **`lock_buffer = false` 로 둘 때 `recheck_after_fetch` 가 필요하다.**
> ⚠️ **둘 다 끄지 말 것** — 그러면 그 창을 보는 것이 아무것도 없고, 기동
> 교차검사가 그 조합을 알린다. 잠겨 있으면 재대조는 절대 안 걸리므로 켜 두는
> 값이 사실상 없다(왕복 하나).

> ⛔ **`full_flush_on_erase` 기본값은 `false` 다** (운영자 확정 2026-08-29) —
> *"clock 을 개선해서 별도 erase 를 하지 않고 바로 노출을 시작한다"*. ⚠️ 켜면
> 노출마다 **독출 1회분(실측 12.77초 — 사강 `NoIntMS` 0.5 가 붙으면 13.27초, DevNote 10.4)**
> 이 더 붙어 주기가 13.27 → 약 26초가 된다 (추정).

> **`CTRL1CFG`/`CTRL2CFG` 는 ACF 경로에서 나온다** (2026-08-29 v1.8 확정, 현행 규격 v1.9 5.5절).
> `[controllers] ctrlN_cfg` 를 **비워 두면** `[archon] acf_mk`/`acf_nt` 에서
> **폴더와 확장자(`.acf`/`.cfg`)를 뗀 이름**이 실린다 —
> `~/AIC/Config/acf/KMTC_SCI_101_STA0284_R2611_MK.acf` →
> `'KMTC_SCI_101_STA0284_R2611_MK'`.  적어 두면 **그 값이 이기고**, 파생값과
> 다르면 기동에서 경고한다(헤더가 주장하는 설정 파일과 실제로 올리는 파일이
> 갈린 자료는 나중에 봐도 드러나지 않는다).  `RDMODE` 와 같은 규칙이다.

> **`~` 는 펼쳐진다** (`data_dir` · `expnum_file` · `logging file` · `acf_*`).
> **상대경로는 권하지 않는다** — ini 위치가 아니라 **실행한 디렉터리** 기준으로
> 풀려서, 띄우는 방법이 바뀌면 자료가 조용히 다른 곳에 쌓인다.
>
> **로그는 반드시 파일로 받는다.** 터미널 스크롤백은 페인 폭 경계에서 한 글자씩
> 먹혀 와이어 손상과 구분이 안 된다 (DevNote 3.7.2 실측).

### 5. 돌리기

```bash
cd ~/AIC/src/ics_archon
python3 -m ics_archon -c ~/AIC/Config/ics_archon.ini
```

**첫 실행은 본편이 아니라 `probe_archon` 1단계부터** — 아래 "실기 첫 실행 절차".

```bash
python3 tools/probe_archon.py -c ~/AIC/Config/ics_archon.ini --host 10.0.0.13
```

### 6. 실행 래퍼 (`~/AIC/bin/ics_archon`)

`cd` 를 사람이 기억하지 않게 한다. **작업 디렉터리를 못박는 것이 요점**이다 —
상대경로 설정과 `_simpath` 탐색이 둘 다 여기에 걸린다.

```sh
#!/bin/sh
# ~/AIC/bin/ics_archon -- 실기 ICS 실행 래퍼
set -eu
AIC="$HOME/AIC"
cd "$AIC/src/ics_archon"
exec python3 -m ics_archon -c "$AIC/Config/ics_archon.ini" "$@"
```

```bash
chmod +x ~/AIC/bin/ics_archon
~/AIC/bin/ics_archon --backend sim      # 컨트롤러를 안 만지고 메시지 층만
```

### 7. 서비스로 돌릴 때

콘솔(stdin)을 쓰지 않으므로 `[behavior] console = false` 로 둔다.

```ini
[Service]
WorkingDirectory=/home/<사용자>/AIC/src/ics_archon
ExecStart=/home/<사용자>/AIC/bin/ics_archon
Restart=on-failure
```

### 8. 여러 구성을 나란히

**ini 를 나누면 노출 번호도 자동으로 나뉜다** (`expnum` 이 ini 이름을 따른다):

```
~/AIC/Config/ics_archon.ini      →  ics_archon.expnum
~/AIC/Config/ics_archon_lab.ini  →  ics_archon_lab.expnum
```

### 갱신 · 되돌리기

```bash
cd ~/AIC/src/ics_archon
python3 -m pytest tests -q -m "not repo_only"      # 배치본 -- 실패 0
```

⚠️ **배치본에서는 `-m "not repo_only"` 를 붙인다.**  붙이지 않으면 그 표식이
붙은 것들이 실패하는데 설치가 깨진 것이 아니다 — 그것들은 **저장소에만 있는
원천**을 대조하는 시험이라 배치본에는 대조할 상대가 없다.

⛔ **개수를 적지 않는다** -- `python -m pytest --collect-only -q -m repo_only` 가 정본이다 (2026-09-09 에 이 표가 *세 파일 17건*에 멈춰 있는 것을 고쳤다 — 실제는 **아홉 파일**이었다).

| 없는 원천 | 표식이 붙은 파일 |
|---|---|
| 형제 `ics_sim/` 원천 | `test_vendor.py`(벤더 표류) · `test_labtest_spec_copy.py`(labtest 규격 사본 — 같은 파일의 배포 ini 대조는 표식이 없다.  **상수 대조만이 아니라 카드 절단 규범·나열 자리 채움 같은 동작도 본다**, v1.6) |
| `raw_fits_spec/` 견본·규격 | `test_fitswrite.py`(견본 pair 바이트 재현) · `test_icg_cards.py`(guide 견본) · `test_ch10_reflection.py`(규격 10장 문면) |
| 저장소 `acf/` 실물 | `test_icg_timing.py` · `test_timing_script_extract.py` · `test_monitor.py` · `test_icg_app.py` |

**배치본의 기대값은 `-m "not repo_only"` 가 수집한 수 전량 통과 · 실패 0** 이다.  그 밖의 실패는 정상이 아니다.  ⛔ 기대 수를 여기 박아 두지 않는다 — 2026-08-31 실측이라던 *223* 이 그 뒤로 두 배 넘게 벌어져 있었다.

⚠️ **저장소에서는 `-m "not repo_only"` 를 쓰지 말 것.**  표식의 뜻은 "안 돌려도
되는 시험" 이 아니라 "배치본에는 대조할 원천이 없다" 다.  저장소에서 빼면
**벤더 표류와 견본 어긋남을 놓친다** — 그 둘이 raw spec 5장 개정이 왔을 때
울리는 알람이다.  **2026-08-26 의 v1.5 반영이 그 알람으로 시작됐다.**
저장소에서는 표식 없이 전부 돌린다.

- **야간에는 갱신하지 않는다.** 돌고 있는 코드가 바뀐다.
- `~/AIC/Config/` 의 ini 는 배포본 밖이라 **덮이지 않는다.** 새 키가 생겼는지는
  `diff ~/AIC/Config/ics_archon.ini ~/AIC/src/ics_archon/ics_archon.ini`.
- 되돌리기: 방법 A 는 이전 태그에서 다시 `rsync`, 방법 B 는 `git checkout <태그>`.
- FITS `ICSBUILD` 가 `v<버전>:<빌드일시>` 를 싣는다. **손으로 적는 값**이므로
  (`ics_archon/__init__.py`) 소스를 고쳤으면 같이 올려야 하고, 그래서 헤더에서
  "이 자료를 만든 코드" 를 되짚을 수 있다.

## 실기 첫 실행 절차

> ⚠️ **이 절은 science pair 다.** guide 유닛(`icg_archon`)은
> **[`icg_first_run.md`](icg_first_run.md)** 를 따른다 — 자리 표·카드 표·
> 설정 파일이 다르고, probe 도 **`--unit guide`** 로 불러야 한다 (안 주면
> 자리 표 어긋남을 거짓으로 보고한다).

**본편을 그냥 돌리지 말 것.** 미검증 3자리가 한꺼번에 걸리면 원인을 가릴 수
없다. `tools/probe_archon.py` 가 위험이 낮은 것부터 하나씩 확인한다 — 본편과
**같은 모듈**을 쓰므로 여기서 통과한 것은 본편에서도 통과한다.

⚠️ **본편을 내리고 돌린다.**  `ics_archon` 은 기동에서 컨트롤러에 접속하고
**접속자는 컨트롤러당 하나**다(운영자 확정 2026-08-28).  Rev F 백플레인은 동시
접속이 하나뿐이라(매뉴얼 p.15) 물리적으로도 못 붙고, Rev H 라도 같은 규칙이다.

### 1단계 — 읽기 전용 (전원을 켜지 않는다)

```bash
python tools/probe_archon.py --host 10.0.0.13
```

`SYSTEM`·`STATUS`·`FRAME` 원문을 다 찍고, 가정을 대조한다 — 장착 모듈이 규격
5.6.1절 자리 표와 맞는지 · 온도 슬롯·전원 레일 결측 · 기하 vs 선언 ·
`BUFnLINES` 존재 · `Cn_*` 카드의 폭(견본 51자를 넘으면 규격 5.0절대로
**comment 가 먼저 줄고**, 66자를 넘어야 값이 잘린다) · **`Cn_TEMP` 자리 수가
규격 5.6.1절 표와 같은지**.
**여기서 `문제` 가 하나라도 나오면 그것부터 고친다.**

여기에 **감시가 기다리는 확인 항목**도 함께 나온다 (2026-08-28 추가):

| 보이는 것 | 무엇을 판정하나 |
|---|---|
| `VALID` / `COUNT` / `LOG` 보고 여부 | D4(무효 응답 → 헤더 `NC`) · 기록의 `fresh`/`log_n` 열이 살아 있나 |
| 전원 레일 정상 범위 (p.41) | `rail_flag` 열의 기준.  유닛이 다르면 `[archon.rails]` 로 덮는다 |
| **바이어스 채널 표** | 층 2 — 이름표는 **ACF**, 값은 **STATUS** 다.  ⚠️ 두 dict 의 키 문자열이 같으니 섞어 읽지 말 것 |

⚠️ **`LOG` 은 여기서 사람이 한 번 보고 판단할 것이 있다** — 값의 상한, 로그 한
줄의 생김새(자체 시각·심각도가 붙나).  항목이 **모듈·채널 수준의 정체**를 담으면
(`MOD9 HVHC4 failed to reach setpoint` 같은) `FETCHLOG` 드레인을 넣을 값이 있고,
`config applied` 수준이면 **안 쓴다**(우리 로그가 이미 더 잘 담는다).

### 2단계 — ACF 대조 (여전히 읽기 전용)

```bash
python tools/probe_archon.py --host 10.0.0.13 --acf acf/KMTC_SCI_101_STA0284_R2611_MK.acf
```

`[archon] param_intms_slot`/`param_exposures_slot` 이 그 ACF 에 있는지, 컨트롤러
메모리의 같은 줄 번호가 그 키인지 `RCONFIG` 로 확인만 한다. **어긋난 채로
돌리면 노출 시간이 조용히 안 바뀐다.**

### 3단계 — 프레임 1장 ⚠️ 전원 ON

```bash
python tools/probe_archon.py --host 10.0.0.13 --acf acf/... --expose 0 --write
```

`--expose` 를 준 경우에만 돈다. 셔터는 열지 않는다(`TRIGOUTFORCE=1`). 끝나면
무슨 일이 있어도 `POWEROFF`. **여기서 나오는 값이 3단계의 산출물이다** —
독출 실측 시간 · 진행률 보고 횟수 · FETCH MiB/s · FITS 1장(`probe.*.fits`,
관측 번호 공간을 건드리지 않는다).

⭐ **`POWERON` 로그도 여기서 처음 본다** (2026-08-28 추가) — flush 대기
(`poweron_wait`, 기본 12초) **안에서** `STATUS` 를 되물어 `POWER=4` 를
확인하고 `POWER=4 (On) 확인 -- N초` 를 남긴다.  **`N` 이 실측 램프 시간**이라
12초가 충분한지의 근거가 된다.  4 에 못 닿으면 `ERROR` 한 줄이 나가지만
**막지는 않는다** — 값이 아직 실기 미검증이라 오독으로 관측을 세우는 쪽이 더
나쁘다.  ⚠️ 대기 시간 자체는 램프가 아니라 **CCD flush** 를 기다리는 것이라
`POWER=4` 를 봤다고 줄이지 말 것.

> 실측한 독출 시간을 `[timing]` 에 넣고, `write_delay + FETCH + 저장`이
> **25초 창**(`[obsagent] force_fitssaved`)에 들어가는지 확인한다.

#### ✅ `LOADTIMING` 이 노출을 시작한다 — 스크립트로 확정 (2026-09-04)

⛔ **`ccdflush` 를 토글하면 프레임 한 장이 유령으로 돌 수 있다.**  근거가 셋이고
서로 맞물린다:

1. **매뉴얼 p.51** -- `LOADTIMING` 은 *"Parses and compiles the timing script
   **and parameters** … and applies them to the system.  **This resets the
   timing cores.**"*
2. **매뉴얼 p.52** -- 코어 리셋은 *"starting all timing cores from the first
   line of the timing script"* 이다 (`RESETTIMING` 항).
3. ⭐ **실물 타이밍 스크립트의 `Start:` 블록이 그 관문이다**
   (`acf/KMTC_SCI_101_STA0284_R2611_MK.acf`.  ⛔ 줄 번호로 적지 않는다 -- 판마다
   밀린다, DevNote 11.35):

   ```
   Start:
     RESET; IF FirstFlush GOTO FlushFrame
     X; IF ContinuousExposures GOTO Continuous
     X; IF Exposures GOTO Exposure          <- 관문
     X; CALL SkipLine
     X; GOTO Start                          <- Exposures=0 이면 유휴 루프

   Exposure:
     X; Exposures--
   Continuous:                              <- 여기 오면 적분·독출 시작
   ```

   즉 코어 리셋 뒤 `Exposures != 0` 이면 **그 자리에서 노출이 돈다.**
   운영자가 ArchonGUI 로 실측한 거동(`Exposures=1` + "Load Timing" -> 독출)이
   이 경로이고, GUI 의 `CLEARCONFIG`+전량 재작성과는 **무관하다** -- 우리처럼
   줄 하나만 `WCONFIG` 해도 같다.

⚠️ **ACF 출하값은 `Exposures=0`·`ContinuousExposures=0`** 이라 **첫 노출 전
한 번은 안전하다.**  ⛔ 그런데 `trigger()` 가 프레임마다 설정 메모리에
`Exposures=1` 을 쓰고, `LINE7` 의 `Exposures--` 는 **타이밍 코어의 파라미터
RAM** 에서만 줄어든다 -- **설정 메모리 텍스트는 `1` 로 남는다.**  그래서 **첫
노출 뒤로는 계속 위험 구간**이다.

⭐ **처방 (R2610, 2026-09-05)**: `ccdflush` 는 이제 **`LOADTIMING` 을 내지 않는다** --
`set_first_flush()` 가 설정 메모리의 `FirstFlush` 한 줄만 쓰고(되읽어 확인), 다음 노출의
`LOADPARAMS`(코어 리셋 없음)가 그것을 실어 간다.  그래서 이 유령 독출 경로는 **운영 중에
열리지 않는다**.  남는 위험은 벤더 GUI 의 "Load Timing" 같은 수동 `LOADTIMING` 뿐이다 --
그때는 먼저 `Exposures=0` 을 써 둘 것.  (종전 처방 -- `set_ccdflush()` 가 `LOADTIMING` 앞에
`Exposures=0` 을 눌러 두고 되읽던 것 -- 은 기제와 함께 걷혔다, DevNote 11.33.)

⏳ **첫 구동에서 확인만 하면 되는 것 하나** -- `ccdflush=true` 로 찍은 프레임 수가 요청 수와
같아야 한다(flush 는 프레임을 만들지 않는다).  `probe` 3단계 로그의 프레임 수로 본다.

> 참고 — 매뉴얼이 가르는 셋 (p.51-52):
> `WCONFIG` 는 **설정 메모리에 글자만 적는다**(파싱·컴파일 없음) ·
> `LOADTIMING` 은 **컴파일해서 코어에 심고 리셋한다** ·
> `RESETTIMING` 은 **컴파일 없이 첫 줄부터 다시 돌린다** ·
> `LOADPARAMS` 는 **파라미터만 적용하고 코어를 리셋하지 않는다**.

### 4단계 — 본편, 실험실 1유닛

실험실은 유닛이 한 대이므로 `MK` pair 만 돌린다. `ics_archon.ini` 세 곳:

```ini
[node]
ic_ids = M.IC, K.IC        # NT 를 빼면 그 파일은 생기지 않는다
cb_ids = M.CB, K.CB
master = K

[controllers]
ctrl1_id = KMTA-SCI-101    # **선언한 쪽이 그 한 대다** (색인 1 = MK)

[archon]
n_controllers = 1          # 1 또는 2.  그 밖은 기동 거부
ctrl_mk_host = 10.0.0.13
acf_mk       = acf/KMTC_SCI_101_STA0284_R2611_MK.acf
```

> `n_controllers = 1` 이면 `[controllers] ctrl1_id`(→`MK`) / `ctrl2_id`(→`NT`)
> 의 **선언 여부**가 어느 컨트롤러인지 정한다.  둘 다 선언하면 기동을 거부한다.
> ⚠️ **색인이 태그를 정하고 이름 문자열은 읽지 않는다** — 이름 끝 번호
> (`101`/`103`/`104`…)는 유닛마다 다르고 색인과 관계없다.  정본은 배선
> (`ctrl_mk_host`/`ctrl_nt_host`)이다.
> "없음" 은 빈 값 · `NC` 가 같은 뜻이라 **한쪽만 적어도, 둘 다 적고
> 한쪽을 `NC` 로 둬도 된다.**  빠진 쪽의 `CTRLnID/SN/CFG` 카드는 **빼지 않고**
> 값에 규격 5.0절 sentinel `NC` 가 실린다.

```bash
python -m ics_archon
```

콘솔에서 `projid ENG` → `dark begin` → `exp 1` → `go`. OBSAgent 없이
전 경로가 돈다.

> ⚠️ **배포 ini 는 허브를 본다** (2026-09-07 운영자 지시) — `xis_host = 127.0.0.1`
> `xis_port = 6660` 이고 `[archon] require_xis = true` 라 **허브가 없으면 기동에서
> 멈춘다**. 허브 없이 돌리려면 `require_xis = false` 로 내리고 `xis_host` 를
> 비운다(direct-reply). ⛔ **ICG 쪽 `xis_host` 도 함께** — 한쪽만 바꾸면
> `ICS→ICG` 의 `VACGAUGE`·`HKDATA` 가 조용히 사라진다.

> ⚠️ **이 구성은 OBSAgent 규약을 만족하지 못한다** — `Acquisition Complete.` 와
> `Wrote` 가 4회가 아니라 2회다(CCD 가 둘이니까). 관측 시퀀스 시험은 유닛 2대가
> 붙은 뒤에 한다. 4단계의 목적은 **취득·저장 경로**를 실기로 확인하는 것이다.

### 5단계 — 유닛 2대 + OBSAgent

`ic_ids` 를 4개로 돌리고 `ctrl_nt_host`/`acf_nt` 를 채운다. 여기서 비로소
`Acquisition Complete.` 4회 · `Wrote` 4회 · 시간 창 3종이 검증된다.

## 아직 없는 것 (v0.0)

**요약** — LED 프로젝터 배선 · binning · 바이어스 측정값의 헤더 수록(로그만
있다).  ~~듀어·환경 HK~~ 와 ~~guide 계통~~ 은 **2026-08-31 `icg_archon` 신설**로
경로가 생겼다 — HK 는 `[archon] hk_latest` 로 icg 스냅샷을 읽고(icg 가 꺼져
있으면 종전대로 sentinel), guide 취득은 `icg_archon/` 이 맡는다 (실기 미검증).

⚠️ **각 항목의 근거와 착수 조건은 [SMC_CLAUDE.md](SMC_CLAUDE.md) 에 있다** —
여기 두면 "쓰는 법" 과 "남은 일" 이 섞인다.


## CCD 조작 명령 넷 (운영자 지시 2026-09-05)

ICS(`ics_archon`)·ICG(`icg_archon`) 둘 다 받는다.  ICS 는 컨트롤러가 둘이라 대상을 고른다:

| ICS 명령 | 하는 일 | 응답 |
|---|---|---|
| `CCDFLUSH [MK\|NT\|ALL]` | 유휴 CCD 를 FlushFrame 한 바퀴로 비운다 (science ACF R2610+, Prep+Flush). 프레임은 안 만든다. ⚠️ **첫 `GO` 뒤에만** 된다(ACF 줄 번호는 `prepare()` 가 파싱한다) — 그 전엔 `Failed: ACF not loaded … run GO once first` | `DONE: CCDFLUSH Flushed=MK,NT` |
| `CCDPOWON [MK\|NT\|ALL]` | `POWERON` + flush 대기(`poweron_wait`, 기본 12 s) | `DONE: CCDPOWON Power=ON Controllers=MK,NT` |
| `CCDPOWOFF [MK\|NT\|ALL]` | `POWEROFF`. 다음 `GO` 가 다시 켠다. 안 앉았으면 `Failed: POWEROFF not confirmed` | `DONE: CCDPOWOFF Power=OFF Controllers=MK,NT` |
| `ARCHON <MK\|NT> <원문…>` | 바이패스 — 원문을 그대로 보내고 응답 원문을 돌려준다. ⛔ 위생 검사 없음(`RESETTIMING`·`WCONFIG` 도 나간다). 1800자 넘으면 잘리고 전문은 로그에 | `DONE: ARCHON MK <응답>` / 거부 `ERROR: ARCHON MK rejected: <원문>` / 빈 ack `<empty reply>` |

ICS 에서도 운영자 명령이 도는 중의 `GO` 는 `ERROR: GO Operator command in progress (CCDPOWON) -- retry when it is DONE` 으로 거부된다.  `--backend sim` 이면 넷 다 `Controller is not available (no hardware backend)`.

ICG 는 컨트롤러가 하나라 인자가 없다:

```
CCDFLUSH              # 유휴 CCD 를 FlushFrame 한 바퀴로 비운다 -> DONE: CCDFLUSH Flushed=1 (프레임 없음)
CCDPOWON / CCDPOWOFF  # POWERON/POWEROFF -> Power=ON|OFF  (ON 은 poweron_wait 초 뒤에 DONE)
ARCHON <command>      # 컨트롤러 바이패스 -> DONE: ARCHON <응답 원문>  (거부는 ERROR: ARCHON rejected: <원문>)
```

* ⛔ 앞의 셋(`CCDFLUSH`·`CCDPOWON`·`CCDPOWOFF`)은 **취득 중이면 거부**한다 (`Exposure in progress -- ABORT
  first`) — 진행 중 노출 위의 `LOADPARAMS`/`POWEROFF` 는 그 프레임을 망친다.  셋은 서로도, `GO` 도 막는다
  (`Busy with <CMD>`) — `POWERON` ack 뒤 `poweron_wait`(12 s) 동안 들어온 `GO` 가 flush 안 끝난 CCD 를
  arm 하는 구멍 때문이다.  `EXPENABLE OFF` 는 막지 않고 응답에 `(ExpEnable=OFF)` 를 붙인다.
* ⭐ `ARCHON` 은 **제한이 없다** (운영자 2026-09-05 *"제한 없이 모두 풀어줘"*) — 취득 중이든 다른 조작이 도는
  중이든 받고, `GO` 도 막지 않는다.  진행 중 노출 위의 `RESETTIMING` 이 프레임을 망치는 것은 운영자 몫이다
  (로그에는 남는다).
* ⚠️ `ARCHON` 은 원문을 **그대로**(대소문자 유지) 보낸다 — 컨트롤러는 모르는 명령에 무응답이라 소문자
  이름은 시한 초과로 끝난다.  위생 검사가 없는 운영자 도구다.  긴 응답(`STATUS`)은 1800 B 에서 잘리고
  전문은 `*.cmd` 로그에 남는다.  빈 ack(`WCONFIG`·`LOADPARAMS`·`APPLY*`)는 `(accepted, empty reply)`.
* guide 의 flush 는 `FlushFrame`(R2613+: FrameShift + SkipLine×FlushLines, 프레임 없음), science 의 flush 는
  `Prep`+`Flush`(R2609+) 다.  ACF 가 구판이면 `Failed: … ACF has no FirstFlush …` 로 거부된다.
  ⭐ **R2616(guide)/R2610(science) 부터 flush 는 ACF 설정 메모리의 `FirstFlush` 가 싣는다** — guide 는 상수 1(모든
  `LOADPARAMS` 가 flush 한 번을 싣고, `STOP` 뒤에도 꼬리 flush 한 번), science 는 `[archon] ccdflush` 옵션이 기동
  때 1/0 을 쓴다(1 이면 **매 노출 전** Prep+Flush).  호스트가 프레임마다 쓰는 플래그는 없다 (DevNote 11.33).
* `sim` 백엔드에서는 `ARCHON` 이 `SIM (no controller): <원문>` 을 돌려준다 — 배선 확인용.

## 콘솔 (운영자 지시 2026-09-07)

`[behavior] console = true` 면 stdin 을 읽는다. 타이핑한 명령은 스펙 2.2절 관례대로
**자기 자신에게 보내는 `EXEC:`** 다. `help` 또는 `?` 로 도움말이 나온다.

⭐ **도움말은 앱마다 다르고 명령표에서 자동으로 검증된다.** `IcsArchon.console_help()`
· `IcgArchon.console_help()` 가 절 목록을 주고, `tests/test_console.py` 가 그것과
`Dispatcher` 의 `cmd_*` 를 **양방향**으로 대조한다 — 명령을 새로 넣고 도움말을 안
고치면 시험이 빨개진다. ⛔ **표의 명령 이름을 손으로 유지하지 말 것.**

### `>NODE 메시지` — 다른 노드로 보내기

```
>XIS HOSTS              # ICS>XIS HOSTS  -- 허브에 등록된 노드 목록
>XIS HOST ICG           # 그 노드의 IdleTime 까지
>TC status              # ICS>TC status
>K.IC status            # 우리가 받는 노드 -- 프로세스 안에서 처리 (종전 거동)
```

* **목적지가 우리 노드면**(`ICS`·`K.IC`·`K.CB` …) 종전대로 프로세스 안에서 돈다.
  **남의 노드면 와이어로 나간다** — `xis_host` 가 있으면 허브가 받아 전달한다.
  ⛔ 2026-09-07 전에는 남의 노드도 프로세스 안으로 흘려서 *"담당하는 노드가
  아닙니다"* 로 막혔고, `icg_first_run` 3단계가 시키는 `ICG>XIS HOSTS` 를 **보낼
  수단이 아예 없었다**.
* ⭐ **친 문면을 그대로 싣는다** — `EXEC:` 를 우리가 붙이지 않는다. 남의 노드의
  어휘를 감싸면 뜻이 달라진다(`>XIS HOSTS` 는 타입 토큰 없는 암묵 REQ 이고, 같은
  허브 명령표의 `REMOVE` 는 `EXEC:` 가드가 있다). `ARCHON <원문>` 과 같은 성격의
  바이패스다.
* ⛔ **ASCII 전용** — 한글은 `?` 로 바뀌어 상대가 못 읽으므로 보내기 전에 거절한다
  (규약 7-1).
* ⚠️ **답은 프롬프트가 아니라 로그로 온다** (`보고 수신 (조치 없음) -- …`).
  `python -u -m ics_archon 2>&1 | tee` 처럼 stderr 를 함께 잡을 것.
* 길이 없으면(`xis_host` 가 비었고 그 노드에게서 아직 아무것도 못 받았다)
  **버려지기 전에 알린다** — 종전 transport 는 조용히 버렸다.

## 셔터 · Trigger Out (운영자 확정 2026-09-09)

⛔ **Trigger Out 이 무엇을 모는지가 계통마다 다르다.**

| 유닛 | 그 선이 모는 것 | 쉬는 상태 | 명령 |
|---|---|---|---|
| **science** (`ics_archon`) | **실제 셔터** | `TRIGOUTFORCE=0` — 타이밍 스크립트가 몬다 | `SHOPEN <초>` · `SHCLOSE` |
| **guide** (`icg_archon`) | **LED** (셔터가 없다 — frame-transfer) | `TRIGOUTFORCE=1` — 선을 우리가 붙든다 | `TRIGOUT <ms>` · `TRIGOUT 0` |

### 무엇을 쓰나 — 어느 쪽도 `APPLYSYSTEM` **한 번**

| | science | guide |
|---|---|---|
| `SHOPEN <초>` / `TRIGOUT <초>` | `TRIGOUTLEVEL=1` + `TRIGOUTFORCE=1` | 같음 |

⚠️ **`TRIGOUT <초>` 의 실현 최소 폭은 ≈235 ms 다** (2026-09-09 실측).  선을 세우고
내리는 수단이 `WCONFIG`+`APPLYSYSTEM` 인데 **적용 하나가 ≈233 ms** 걸리기 때문이다.
⭐ 그 시간이 폭에 더해지지 않도록 **잠들 시간에서 미리 뺀다** — 그래서 요청한 `<초>` 가
실제 폭이 된다.  ⛔ `<초>` 가 235 ms 보다 짧으면 만들 수 없어 0 으로 눌러 담고 경고를
남긴다.  그보다 짧은 펄스가 필요하면 **타이밍 스크립트(ACF)로 몰아야** 한다.
⏳ 자세한 실측은 「연속 노출 중 명령 지연」 절.
| `<초>` 만료 · `SHCLOSE` / `TRIGOUT 0` | `TRIGOUTLEVEL=0` + **`TRIGOUTFORCE=0`** | `TRIGOUTLEVEL=0` + **`TRIGOUTFORCE=1`** |

* 올림은 두 계통이 **완전히 같고**, 내림은 돌아갈 `TRIGOUTFORCE` 만 다르다.
* **시한 만료와 명시적 내림이 같은 동작**이다. 새 `SHOPEN`/`TRIGOUT` 은 앞 타이머를 끊는다.
* `TRIGOUTFORCE`/`TRIGOUTLEVEL` 은 조회·설정 명령으로 **따로 남아 있다**.
* ⭐ **science 는 노출을 걸 때마다 `TRIGOUTFORCE` 를 되돌린다** —
  `ArchonBackend.open_shutter()` 가 `set_trigger_forced(not drives_shutter(tag))`
  를 쓴다. 그래서 `SHOPEN` 이나 즉시 차단이 선을 붙든 채 끝나도 **다음 `GO` 가
  쉬는 상태(`FORCE=0`)로 되돌린다**.

### ⛔ `SHCLOSE` 는 "닫는다" 가 아니라 "내 강제를 놓는다"

`TRIGOUTFORCE=0` 으로 선을 **타이밍 스크립트에 돌려준다**.  그래서 노출 중에 쓰면
셔터가 닫히는 시각은 **둘 중 늦은 쪽**이다:

    셔터 닫힘 = max( SHOPEN <초> 만료,  노출의 NoIntMS )

| `<초>` vs 남은 노출 | 닫는 주체 |
|---|---|
| `<초>` 가 **길다** | ⭐ **`<초>`** — 그동안 `FORCE=1` 이라 스크립트가 `NOINT` 로 내려도 핀은 HIGH 로 붙들려 있고, 만료 때 넘겨주면 스크립트는 이미 INT 밖이라 그때 닫힌다 |
| `<초>` 가 **짧다** | **노출**(`NoIntMS`) — 넘겨줄 때 스크립트가 아직 `IntUnit` 안이라 계속 열려 있다 |

`SHCLOSE` 는 시한 없이 곧바로 넘겨주므로 **항상 뒤쪽**이다 — 적분 중이면 노출이
끝날 때 닫힌다.

⛔ **`<초>` 가 남은 노출보다 길면 자료가 오염된다** — 노출이 끝난 뒤에도 셔터가
열려 있는 동안 **프레임 트랜스퍼와 독출**이 돌기 때문이다(스미어).  교정·점검이
아니라면 `<초>` 를 남은 노출보다 짧게 두거나 취득 밖에서 쓸 것.

### `STOP` · `ABORT` 와의 관계

⛔ **`STOP` 은 셔터를 안 건드린다.** 정의가 *"현재 노출을 끝까지 마치고 **다음을
안 건다**"* 이므로(`Sequencer.stop_integration`), `GO`(1장)에는 사실상 영향이
없고 **`GO n` 에서만** 뜻이 있다. ICS·ICG 가 같은 정의다.

`ABORT` 는 현재 노출을 종료하고 **영상을 저장하지 않는다**. 뒤처리가 계통마다
다르다:

| | ABORT 뒤 | 유휴(idle) 상태 |
|---|---|---|
| **science** | readout **없이** 곧바로 유휴 (flush 는 `ccdflush` 가 정한다 — 아래) | `SkipLine` 을 계속 돌려 **CCD 를 계속 비운다** |
| **guide** | **flush 한 번**(`abort_flush()` — `RESETTIMING` + flush) | `SkipLine` 을 안 돌린다 — **CCD clocking 을 멈춘다** |

#### science 의 CCD flush 는 **기본이 꺼짐**이고 ini 가 정한다

`ics_archon.ini` 의 `[archon] ccdflush` 가 기본 **`false`** 다. 켜면(`true`) 설정
메모리의 `FirstFlush` 가 `1` 이 되고, 코어는 `Start:` 첫 줄에서 `FlushFrame`
(Prep + Flush)으로 뛴다 — 그래서 **`true` 면 flush 가 두 자리에서 한 번씩 돈다**:

| 언제 | 왜 도나 |
|---|---|
| **매 노출 전** | science 는 노출마다 `LOADPARAMS` 를 내고, 그때 코어가 `Start:` 를 지난다 |
| **`ABORT` 뒤 한 번** | `abort_now()` 의 `RESETTIMING` 이 코어를 `Start:` 로 되돌린다 |

⚠️ `false`(기본)면 두 자리 모두 flush 가 없다 — 유휴의 `SkipLine` 이 CCD 를 계속
비우기 때문이다. ⛔ guide 는 다르다: ACF 상수가 `FirstFlush=1` 이라 **항상** 돈다.

⚠️ **셔터를 즉시 끊는 경로는 `ArchonBackend.close_shutter()`** 이고
(`TRIGOUTFORCE=1` + `TRIGOUTLEVEL=0` 으로 선을 **붙든다**), 적분 자체는 남은
시간을 다 센다. ⏳ 다만 **현재 `ABORT` 는 이 함수를 안 지난다** — 시퀀서가
태스크만 취소하므로 science 는 컨트롤러의 적분이 물리적으로 끝까지 가고 셔터는
`NoIntMS` 에 닫힌다(프레임만 안 쓴다). 미결 항목이다 (DevNote 11.50).

| | 강제 | 적분 중 셔터 |
|---|---|---|
| `SHCLOSE` | **놓는다** (`FORCE=0`) | 노출 끝(`NoIntMS`)에 닫힘 |
| `STOP` | 안 건드린다 | 노출 끝에 닫힘 (정상 종료) |
| `ABORT` | 펄스 중이면 **쉬는 상태로 되돌린다** | 적분을 끊고(`RESETTIMING`) **닫힘** |
| `close_shutter()` (즉시 차단 경로) | **붙든다** (`FORCE=1`, `LEVEL=0`) | **즉시** 닫힘 |

⭐ **진행 중인 `SHOPEN`/`TRIGOUT` 펄스를 끊는 자리가 셋이다** — `ABORT` ·
`EXPENABLE OFF`(ICG) · **종료(`quit`)**. `RESETTIMING` 은 타이밍 코어만
되돌리는데 펄스 중에는 `TRIGOUTFORCE=1` 이라 핀이 코어를 안 따라가기 때문이다 —
안 끊으면 **셔터가(guide 는 LED 가) 열린 채 남는다**.
⛔ **종료가 특히 그렇다**: 펄스는 백그라운드 태스크로 도는데 종료가 그것을
취소하므로 내림이 **영영 안 돈다**. ⚠️ 펄스가 없었으면 아무것도 안 쓴다.
⛔ **`STOP` 은 안 끊는다** — *"다음을 안 건다"* 라 펄스와 무관하다.

### guide 는 선을 놓지 않는다

`TRIGOUT 0` 도 시한 만료도 `TRIGOUTFORCE=1` 을 유지한다. guide 에서 `0` 은
*"타이밍 스크립트가 몬다"* 이고, guide 는 `IntMS = EXPTIME − 기본 노출시간` 으로
넣어 `INT` 가 실제로 서므로 **노출마다 LED 선이 흔들린다**. 그래서 ACF 출고값도
`TRIGOUTFORCE=1` 로 올렸고(**R2618**), `GuideBackend.prepare()` 가 띄울 때마다
되읽어 확인한다.

⚠️ 이 명령들은 모두 `WCONFIG` + `APPLYSYSTEM` 이다. **적분 중·독출 중
`APPLYSYSTEM` 의 안전성은 아직 실측 전**이라(DevNote 11.50) 취득 중에 치면 한 번
경고가 나온다.

### 없앤 명령

| 명령 | 어디서 | 왜 |
|---|---|---|
| `FLASHNOW` · `LEDFLASH` | ICS · ICG | 점검용 LED 프로젝터 — 실기에서 구현된 적이 없다. 그 자리는 `SHOPEN`/`TRIGOUT` 이 대신한다 |
| `DMAWAIT` | ICG | 광케이블 IC 의 통신 지연 — guide 는 Archon 한 대다 |
| `SHOPEN` · `SHCLOSE` | ICG | guide 엔 셔터가 없다 → `TRIGOUT` 으로 갈렸다 |

⛔ **감추지 않고 거절한다** — `ERROR: <명령> Not supported on this node`.
⚠️ 시뮬(`ics_sim`)에는 그대로 남는다(레거시 흐름을 흉내내는 것이 시뮬의 몫이다).

## 관련 문서

| 문서 | 위치 |
|---|---|
| **경위·판단 (왜 그렇게 정했나)** | ⭐ [`DevNote.md`](DevNote.md) — **이 폴더의 개발 노트** |
| 〃 (`ics_sim` 층 · 2026-08-26 이전 실기분) | [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 11.22~11.30 |
| 산출 규격 (raw FITS pair) | [`../raw_fits_spec/`](../raw_fits_spec/README.md) |
| 헤더 카드 템플릿 (공유 원천) | `../ics_sim/ics_sim/rawcards.py` |
| 백엔드 계약 | `../ics_sim/ics_sim/hardware/base.py` (D-012) |
| L0 MEF ICD · converter | `../mef_fits_spec/` · `../mef_converter/` |

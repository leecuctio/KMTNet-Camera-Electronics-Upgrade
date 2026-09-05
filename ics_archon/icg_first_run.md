# icg 첫 구동 체크리스트 — guide 유닛 (`KMTK-GUI-162`)

`icg_archon` 을 **처음 실기에 붙일 때** 무엇을 어떤 순서로 돌리고 · 무엇을
적고 · 무엇이 나오면 통과인지 한 장으로. science 쪽 짝은
[README.md "실기 첫 실행 절차"](README.md) 다.

- 경위·판단은 [DevNote 9장](DevNote.md), 잠정 목록은 **9.8 PROVISIONAL 총목록**.
- science 실기 시험의 결과·재현법은 [`archon_lock_fetch_report.md`](archon_lock_fetch_report.md).
- 이 문서를 다 밟으면 **PROVISIONAL 6건이 닫힌다**:

| # | 잠정인 것 | 어느 단계가 닫나 |
|---|---|---|
| 1 | `HEATER` 레일의 STATUS 필드 이름 (후보 셋) | 1단계 |
| 2 | `C1_TEMP` 8자리 자리 표 (규격 10.4절) | 1단계 |
| 3 | `EXPTIME` 하한 **1.251 s** (ACF 계산값, R2610) | 4단계 |
| 4 | `DATE-OBS` 트랜스퍼 보정 **6.8 ms** | 4단계 |
| 5 | guide **3버퍼** 잠금 거동 (science 실측은 2버퍼다) | 4단계 |
| 6 | `Exposures=0` 뒤 꼬리가 **한 장인지 두 장인지** | 5단계 |

## 지킬 것 셋

1. ⚠️ **접속자는 컨트롤러당 하나다.** guide 유닛은 `BACKPLANE_REV=5` = **Rev F**
   라 동시 접속이 **하나뿐**이다 (매뉴얼 p.15). `ArchonGUI` · `probe` · 본편
   중 **하나만** 붙는다 — 나머지는 내린다.
2. **한 번에 한 변수.** 특히 6단계(P-k)와 P-l 을 같이 돌리지 않는다. 펌웨어도
   이 캠페인 중에는 건드리지 않는다 — 10장 실측이 현행 판(1252)에 묶여 있다.
3. **판정은 실측이다.** 매뉴얼(2021-02-23)은 무엇을 재야 하는지 알려 주는
   가설의 출처일 뿐이고, `tests/fake_archon.py` 는 우리가 매뉴얼을 읽고 만든
   것이라 시험이 다 통과해도 여기의 물음은 안 닫힌다 (DevNote 8.7).

로그는 전부 `python3 -u … | tee <파일>` 로 남긴다. 실행 자리는 `ics_archon/` 다.

## 0단계 — 준비 (사람이 확인, 왕복 없음)

| 확인 | 어디 | 통과 |
|---|---|---|
| **링크가 서나** | `ping 10.0.0.162` | ✅ **해결법이 확정돼 있다** -- 광 스위치허브의 **포트별 auto-negotiation 을 해제하고 고정 1 G** 로 둔다 (운영자 2026-09-04).  Archon 은 1 Gbps 전용(매뉴얼 p.9)이고 SFP+ 는 자동협상을 하지 않는다.  ⚠️ **스위치를 교체·포트를 옮기면 그 설정이 안 따라온다** -- 링크가 안 서면 모듈·케이블보다 **포트 설정을 먼저** 본다.  자세히는 [INSTALL.md](INSTALL.md) "벤치 네트워크" |
| ⭐ **`Sync In` 이 비었나** | 컨트롤러 뒤판 배선 | ⛔ **master 의 `Sync Out` 이 이 유닛 `Sync In` 에 물려 있으면 노출이 진행되지 않는다** (운영자 실기 확인 2026-09-04).  `POWER=4`·`POWERGOOD=1` 인데 `FRAME` 이 영구히 0 이면 이것부터 -- `POWERGOOD` 은 **자기 전원만** 보고하고 외부 클록 의존을 보지 않는다.  README "프레임이 안 나올 때" |
| guide 컨트롤러 IP | `[icg] ctrl_host` | **`10.0.0.162`** — 정본은 ACF 안의 `IP=` 키다 (`APPLYALL` 이 심는 값).  호스트는 `10.0.0.201`(np0)/`10.0.0.202`(np1) |
| ACF 경로 | `[icg] acf` | `acf/KMTK_GUI_162_STA0201_R2612.acf` (현행 유일본) |
| 사이트 | `[node] observatory` | **`KASI`** — `TESTBED` 면 기동을 거부한다 (D-017) |
| HK 스냅샷 짝 | `[hk] log_dir`+`latest_name` ↔ science `[archon] hk_latest` | **같은 파일**을 가리켜야 한다. 한쪽만 바꾸면 science 5.6절 HK 카드가 조용히 전부 sentinel 이 된다 |
| 포트 | `[transport] bind_port` | **`6601`**(ICG 몫, 2026-09-03 배정).  ICS 는 6600 이고 `ics_sim` 기본값도 6600 이라 **비워 두면 같은 값으로 떨어져** 한 호스트에서 둘 다 못 뜬다 — 기동 검사가 알린다.  배정표는 [INSTALL.md](INSTALL.md).  ⭐ 레거시는 ICG 가 **Guide server**(`.108`, `TC`·`ABC` 와 같은 호스트)에서 돌고 ICS·XIS 는 **Science server**(`.109`)라 포트가 같아도 호스트가 달랐다 (icg_legacy_report 3절) |
| **XIS 허브에 붙나** | `[transport] xis_host` | ⭐ **icg 도 XIS 와 통신한다** — `IcsSim` 의 전송 계층을 그대로 물려받아, 값을 적으면 **모든 발신이 허브로** 가고 비우면 direct-reply(허브 없이 콘솔로 도는 모드)다.  **첫 구동은 비운 채로** 한다 — 취득 경로만 먼저 가른다.  기동에서 `register()` 가 수신하려는 ID **전부**(`ICG`·`G.IC`·`G.CB`)로 PING 을 보내 등록한다 |
| 허브에 붙일 때 | `[transport] bind_host` | 기본 `127.0.0.1` 이라 붙지 않는다 — 허브·`TC`·`ABC` 가 다른 호스트이므로 **`0.0.0.0`** 으로 |
| ⭐ **`guide_ic_id` 를 비웠나** | `[node] guide_ic_id` | **빈 값이어야 한다.**  기본값 `G.IC` 를 안 지우면 라우터가 **자기 IC 를 "범위 밖 guide" 로 무시한다**(`nodes.Role.GUIDE`).  설정 검사가 수신 노드 ID 와의 겹침을 잡는다 |
| ICS 쪽 한 줄 | `ics_archon.ini` `[behavior] send_guide_init` | **`false` 유지.**  켜면 science 노출마다 ICG 안으로 `INITIALIZE` 가 들어가 남의 상태를 건드린다 — 그 노드를 이제 `icg_archon` 이 진짜로 수신 등록한다 (2026-08-31) |
| 환경센서 | `[radionode] backend` | **`off`** 로 둔다 — 값이 없으면 `HEBOX`/`FSATEMP`/`FSAHUM` 이 sentinel 로 정직하게 남는다. `sim` 은 헤더로 안 나가지만 조합 경고가 붙는다 |
| 텔레메트리 | `[icg] telemetry` | `true` 유지 — 실기에서 원인을 가르는 첫 수단이다 |
| **Apply All** | `ArchonGUI` (또는 `probe --expose`) | 이 세션에 `APPLYALL` 이 없으면 **`POWERON` 이 `?xx` 로 거부된다** (매뉴얼 p.51, DevNote 10.2). `REBOOT`·설정 재업로드 뒤에는 반드시 다시 |

## 1단계 — probe 읽기 전용 ⭐ **`STATUS` 원문을 확보하는 단계** (전원 안 켬)

```bash
python3 -u tools/probe_archon.py --unit guide --host 10.0.0.162 --acf acf/KMTK_GUI_162_STA0201_R2612.acf | tee probe1_guide.log
```

⚠️ **`--unit guide` 를 빠뜨리지 말 것.** science 10자리 자리 표로 재면
`extra [6, 7]` + `missing [1, 2, 8, 11]` 이 **거짓으로** 뜬다 — 첫 화면의
오경보가 진짜 문제를 덮는다.

적을 것:

| 항목 | 기대 | 실측 |
|---|---|---|
| 자리 표 판정 | `장착 모듈이 규격 10.4절 자리 표와 정합한다 (8자리: [3, 4, 5, 6, 7, 9, 10])` | |
| `C1_TEMP` 8자리 ↔ 이름표 | `Backplane · Mod3:Driver · Mod4:Driver · Mod5:AD · Mod6:AD · Mod7:HeaterX · Mod9:HVXBias · Mod10:HeaterX` | |
| `HEATER` 레일 | `HEATER_V`/`HEATER_I` 가 있고(매뉴얼 p.47 · FW 1.0.1252) 값이 **27~36 V** 인가 (공칭 28 · power-good 18~36 · ACF `HEATERALIMIT=25` + "출력 최대치보다 2 V 이상" 규칙) | |
| ⭐ **`MOD10/HEATERAOUTPUT`** | 토큰이 **있고**(FW 1.0.1252 확인 — 매뉴얼 p.48 'Heater only' 는 오기) 현 ACF(`HEATERAENABLE=0`·`FORCE=0`)에서 `0.000` 인가. `MOD10/HEATERBOUTPUT`·`MOD7/HEATERAOUTPUT` 도 함께. ⭐ **STATUS 원문 전체를 파일로 남긴다** — guide `.162` 의 STATUS 실물이 저장소에 한 번도 없다 | |
| `MOD10/HEATERAP` 자릿수 | HeaterX 는 FW 에서 `%lld`(64-bit) — 파서가 int32 면 넘칠 수 있다(현재 PID 0 이라 무해). 자릿수를 적어 둔다 | |
| 바이어스 **18채널** V/I | 전부 읽힌다 (science 는 16이다) | |
| `VALID`/`COUNT`/`LOG`/`POWER`/`OVERHEAT` | 보고 여부 (안 보고해도 이상이 아니다 — F2) | |
| 진공 `VCPU_OUTREG*` 원문 | MOD10 VCPU 가 MKS 356 을 시리얼로 읽는다. **10번째 글자가 무해한지** 확인 (실측 658행에서는 응답이 항상 `x.xxe-04` 8자였다) | |
| `FRAME` — 버퍼 **셋** | `BUF1~BUF3` 이 다 나오고 `BUFnBASE`·`BUFnLINES` 가 있다 | |
| ⭐ **`BUFnFRAME` 값** | 되감김 폭(16비트?) 자연 표본의 **시작점**이다 — 반드시 적어 둔다 | |

**통과 기준**: 요약에 `문제 0건`.

## 2단계 — 파라미터 슬롯 대조 (여전히 읽기 전용)

1단계 명령에 `--acf` 를 이미 줬으므로 같은 로그에 함께 찍힌다. `PARAMETER1`
(`Exposures`) · `PARAMETER2`(`IntMS`) 가 그 ACF 에 있고 컨트롤러 메모리의
같은 줄 번호가 그 키인지 `RCONFIG` 로 확인만 한다.

**통과**: 두 슬롯 다 `OK`, 또는 `컨트롤러의 설정 줄 …가 비어 있다`(아직 안
올린 상태 — 정상). ⛔ `설정 줄 …가 … 가 아니다` 가 나오면 **여기서 멈춘다** —
그대로 돌리면 `set_config` 가 엉뚱한 줄을 고쳐 **노출 시간이 조용히 안
바뀐다**.

## 3단계 — 본편 기동 (아직 전원은 안 켠다 — 첫 `go` 에서 켜진다)

```bash
python3 -u -m icg_archon | tee icg_boot.log
```

| 항목 | 기대 | 실측 |
|---|---|---|
| 기동 검사 | `[icg] FETCH 상한 … 가 프레임 하한 … 이상이다` 경고가 **없어야** 한다 (`fetch_timeout=1.0` < 하한 1.251 s) | |
| ⭐ ACF 하한 | `acftiming` 이 타이밍 스크립트에서 읽은 하한 = **1.251 s**. 못 읽으면 ini 대체값 2.0 으로 내려가며 경고가 붙는다 — 그러면 4단계 수치의 뜻이 달라진다 | |
| HK 루프 | 1분마다 `~/AIC/log/hk.G.<YYYYMMDD>.csv` 에 한 행 + `hk_latest.G.json` 갱신 | |
| 콘솔 `hk` | 값 한 줄. `HEBOX`/`FSATEMP`/`FSAHUM` 은 안 실린다(=sentinel, Radionode off) | |
| 콘솔 `radionode status` | `off` | |
| `age_ms`/`lag_ms` | 첫 감시 로그에서 어떤 값인가 — `monitor_interval` 기본값의 근거 | |
| 포트 | `bind_port=6601` 로 떴나 (`ICS 몫` 경고가 없어야 한다) | |
| 노드 등록 | `xis_host` 를 비웠으면 direct-reply 라 허브 왕복이 **없는 것이 정상**이다.  허브에 붙였다면 `ICG`·`G.IC`·`G.CB` 세 이름의 등록 PING 이 나가고, 허브가 `G.IC` 를 모르면 `ERROR: No Route to Destination Host G.IC` 가 온다 (레거시에도 있던 실패 사례) | |
| ⭐ 허브가 아는 노드 | 허브에 붙였을 때만.  **`ICG>XIS HOSTS`** 를 보내면 `DONE: HOST numHosts=… host0=… ` 로 등록된 노드가 다 온다 — 거기 **`ICG`·`G.IC`·`G.CB` 셋이 보이는지**가 등록이 됐다는 직접 확인이다 (허브의 노드 표는 **순전히 동적**이라 노드가 뭘 보내기 전엔 모른다).  `HOST ICG` 는 `IdleTime` 까지 준다 — HK 보고가 끊겼을 때 *ICG 가 죽었나 / 링크가 죽었나* 를 가르는 값이다.  ⚠️ 읽기 전용이지만 같은 명령표의 **`REMOVE <ID>` 는 `EXEC:` 가드가 없다** — 실수로 보내면 그 노드가 허브 표에서 빠진다 | |

## 4단계 — 첫 취득, 주기 실측 ⚠️ **전원 ON**

콘솔에서:

```
projid ENG
dark ICGTEST
guideexp 2
go 20
```

> `dark` 의 인자는 `OBJECT` 카드가 된다. guide 는 `bias`/`dark` 에서도
> **주기를 0 으로 만들지 않는다** — `EXPTIME` 이 셔터 노출이 아니라 **독출
> 개시 간격**이라 0 이 실현 불가능한 값이기 때문이다. `go n` 은 n장이고,
> 앞의 폐기 1장은 별도다 (`Exposures=n+1`).

| `EXPTIME` 지시 | 실현 주기 (중앙값) | `간격이 밀렸다` 경고 | FETCH 초 | 저장 파일 수 |
|---|---|---|---|---|
| 2 s | | | | 20 |
| 5 s | | | | |
| 10 s | | | | |

그리고:

| 항목 | 기대 | 실측 |
|---|---|---|
| ⭐ **하한 클램프** | `guideexp 1` (하한 미만) → **거부가 아니라 하한으로 눌러 담는다.** 헤더 `EXPTIME` 은 요청값이 아니라 **실현값** | |
| ⭐ **`DATE-OBS`** | 직전 트랜스퍼 시각 + **6.8 ms**. 연속 두 파일의 `DATE-OBS` 차 ≈ 실현 주기여야 한다 (규격 10.5절 6번 불변식) | |
| ⭐ **3버퍼 잠금** | 로그의 `RBUF`/`WBUF` — `LOCK` 이 반영되나, 엔진이 잠긴 버퍼를 피하나. ⚠️ science `--hold 20` 실측은 **2버퍼** 결과다, 옮겨 적지 말 것 | |
| guide FETCH | 8.3 MiB. science 실측 99~107 MiB/s 를 옮기면 ≈0.08 s — `fetch_timeout=1.0` 이 12배 여유인지 확인 | |
| 파일 | `~/AIC/data/guide/KMTK.<YYYYMMDD>.<NNNNNN>.G.fits`, **4224 x 1033** | |
| 헤더 | `C1_TEMP`/`C1_VOLT`/`C1_CURR` 8자리 · `ICGBUILD`(개명) · `CTRL2*` 없음 · `DATASRC=ARCHON_GUIDE` · `RDMODE=UNKNOWN` | |
| ⭐ **`BUFnFRAME` 다시** | 증가분 = 찍은 장수 + 폐기 1 이어야 한다 | |

## 5단계 — `STOP` / `ABORT` 뒤 꼬리 (⏳ 미결 하나를 닫는다)

`go 50` 을 걸고 중간에 `stop`, 다시 `go 50` 을 걸고 중간에 `abort`.

| 항목 | 기대 | 실측 |
|---|---|---|
| ⭐ 해제 직후 `FRAME` 증가 수 | **꼬리 한 장인가 두 장인가** = `Exposures=0` 이 읽히는 시점. 시퀀서는 최대 2홉까지 소화한다 | |
| `busy` | 꼬리를 소화하는 동안 True — **그것이 의도다** | |
| 다음 `go` | 꼬리를 자기 첫(폐기) 프레임으로 오인하지 않는다 (기준선 오염) | |
| `abort` 두 번 | 두 번째가 뒷정리를 끊지 않는다. IDLE 통보는 **마지막 요청자**에게 (`df4d4fc` 확인 항목) | |

**통과**: `DONE: ABORT` 뒤 `EXPSTATUS=IDLE` 하나, 그리고 다음 `go` 가 정상.

## 6단계 — P-k, `Pixels` 600 vs 540 ⚠️ **단일 변수**

절차·판정은 [SMC_CLAUDE.md](SMC_CLAUDE.md) 의 **"P-k 실행 절차"** 를 그대로
따른다. 요지: 두 ACF(`acf/archive/…_R2609.acf` = 600 · `acf/…_R2610.acf` =
540)는 **`PARAMETER5` 한 줄만 다르다.** 조명·온도·`IntMS` 를 고정하고 판마다
여러 장 찍어 **통계로** 비교한다(평균·표준편차·컬럼 프로파일 — 구조적 이동은
한 컬럼만 밀려도 바로 보인다). 부수로 주기가 1.375 → **1.251 s** 로 내려가는지
확인하고, 라인 끝 클록 이력이 바뀌었으니 **바이어스·다크를 재취득**한다.

⚠️ **P-l(`PIXELCOUNT`=601 로 꼬리 측정)은 따로 돌린다.**

## 부록 -- 진공게이지 On/Off 실험 (`VACGAUGE` 명령의 근거)

⭐ **명령은 이미 있다** (`VACGAUGE ON|OFF`, 2026-09-04 구현) -- 이 실험이 정하는 것은
**어느 갈래를 쓰느냐**다.  "무엇을 내리면 이온게이지가 꺼지는가" 가 아직 **추론**이고,
후보가 둘인데 성격이 전혀 다르다.  ⭐ 판정이 나면 고칠 것은 코드가 아니라 ini 한 줄
(`[icg] gauge_off_method = ionen | diopower`)이다.

| 후보 | 무엇을 건드리나 | 매뉴얼 근거 |
|---|---|---|
| **A** `MOD10\DIO_SOURCE3` 1→0 | `IONEN` **한 라인**만 정적 HIGH→LOW | p.62 -- `DIO_SOURCEi`: 0=low · 1=high · 2=timing core · 3=VCPU |
| **B** `MOD10\DIO_POWER` 1→0 | **8라인 전부의 버퍼 전원** (내부 +3.3 V → 외부 전압 기대) | p.62 -- *"…or 1 to the internal +3.3V supply.  The +3.3V supply is routed to the DPWR pin"* |

⚠️ **B 는 "게이지 off" 가 아니다** -- 외부 전압을 안 물려놨으면 8라인 구동이 사라져
출력 1~4(`DIO_DIR12=1`·`DIO_DIR34=1`)가 **부정 상태**가 되고, `ION_DE`·`ION_DI`·
`ION_RO`(`SOURCE=3`=VCPU, 게이지와 주고받는 시리얼)까지 죽어 **읽기 경로가 함께
끊긴다.**  값이 안 오는 것을 "껐다" 로 오인할 수 있으니 A 와 **따로** 재야 한다.
⭐ 다만 게이지의 ION enable 입력이 **DPWR 을 공급·풀업으로 쓰고 있으면** B 가 실제로
de-assert 가 된다 -- 그것은 배선 문제라 ACF·매뉴얼로는 못 가른다.

### 도구와 전제

- ✅ **`APPLYDIO` 가 이제 우리 코드에도 있다** (`ArchonController.apply_module(10, dio=True)`,
  2026-09-04 신설 -- 종전에는 `WCONFIG`(`set_config`)뿐이라 `ArchonGUI` 를 빌려야 했다).
  ⭐ **그래서 실험 A/B 를 손으로 `WCONFIG` 하지 말고 `icg_archon` 을 띄운 채
  `VACGAUGE OFF`/`ON` 으로 돌리는 편이 낫다** -- 복구 경로가 같은 코드라 되돌리기가
  확실하고, 갈래는 ini `gauge_off_method` 로 고른다(A=`ionen` · B=`diopower`).
  손으로 돌릴 때의 명령은 GUI 의 `applyModuleDIO(10)` 과 같은 **`APPLYDIO09`** 다 (⚠️ **슬롯 인자는 0기점 2자리 16진** -- MOD10 → `09`),
  시한 10 초, **DIO + VCPU 를 함께** 적용한다 (p.53).
- ⚠️ **접속자는 컨트롤러당 하나** (Rev F) -- 이 실험 동안 `ics_archon`·`icg_archon`·
  `probe` 를 **다 내린다.**
- ⭐ **복구 경로를 바꾸기 전에 확정한다** -- `RCONFIG` 로 `MOD10\DIO_POWER` ·
  `DIO_SOURCE3` 의 **컨트롤러 메모리 값**을 읽어 파일값(`1`·`1`)과 같은지 먼저 본다.
  다르면 실험을 시작하지 않는다 (되돌릴 목표를 모르는 채로 바꾸는 것이다).

### 기준선 (바꾸기 전에 적는다)

| 항목 | 값 |
|---|---|
| `#05RD` 응답 (진공 원문) | |
| `VCPU_OUTREG0~9` (10글자) | |
| `alive` = `VCPU_OUTREG15` | |
| **DPWR 실측 전압** (멀티미터) | |
| 게이지 앞면 표시 (이온게이지 점등 여부) | |

### 실험 A -- `IONEN` 만 내린다  ⭐ **이것을 먼저**

1. `WCONFIG`: `MOD10\DIO_SOURCE3` = **0**
2. `APPLYDIO09`
3. 적는다 → 아래 판정표
4. **복구**: `DIO_SOURCE3` = **1** → `APPLYDIO09` → ⏳ **값이 정상으로 돌아오는 데
   걸린 시간**(warm-up)을 잰다.  ⚠️ 규격이 매뉴얼에 없어 이것이 실측 항목이다.
5. ⭐ **완전 복구를 확인한 뒤에** B 로 넘어간다 (한 번에 한 변수).

### 실험 B -- `DIO_POWER` 를 내린다  ⚠️ 8라인 전부에 걸린다

1. `WCONFIG`: `MOD10\DIO_POWER` = **0**
2. `APPLYDIO09`
3. 적는다 → 판정표.  ⭐ 특히 **DPWR 전압**과 **`ION_*` 시리얼이 죽는지**
4. **복구**: `DIO_POWER` = **1** → `APPLYDIO09` → warm-up 시간

### 판정표

| 보는 것 | 기준선 | A (`IONEN`=0) | B (`DIO_POWER`=0) |
|---|---|---|---|
| 게이지 이온 점등 | | | |
| **`#05RD` 가 답하나** | | | |
| 그 값 (원문 10글자) | | | |
| `alive`(OUTREG15) | | | |
| DPWR 전압 | | | |
| 복구 후 warm-up [s] | -- | | |

⭐ **판정의 핵심 둘**

- **`#05RD` 가 계속 답하면** → 이온게이지만 꺼지고 **Conductron 이 살아** 1e-3~
  대기압 숫자를 계속 준다.  그러면 *"껐다고 믿는데 그럴싸한 압력이 헤더에 실린다"*
  가 실재하므로, 명령이 **우리 층 플래그로 값을 막는 것**이 필수가 된다.
- **`alive` 가 0 으로 되감기면** → `APPLYDIO` 가 VCPU 를 재시작한 것이고, 그것은
  **명령이 스스로 만드는 결측 창**이다.  응답에 그 사실을 적는다
  (`DONE: VACGAUGE Gauge=OFF (… (VCPU restarted -- DEWPRES has a gap))`).

### 멈출 조건

- 게이지에서 이상 소리·발열 → **즉시 복구**
- 복구했는데 값이 안 돌아온다 → 그 자리에서 멈추고 **기다린 시간**을 적는다
  (warm-up 인지 고장인지는 시간이 가른다)
- `RCONFIG` 값이 파일값과 다르다 → **시작하지 않는다**

## 무엇이 나오면 멈추나

- 1단계 요약에 `문제` 가 하나라도 (자리 표·결측·기하)
- 기하가 4224 x 1033 이 아니면 — 본편이 fetch 앞에서 거부한다 (바이트로 대조한다)
- `POWER` 가 4 에 못 닿는데 바이어스 값이 그럴싸하면 — `POWER≠4` 에서는 전 채널 ~0 V 여야 한다 (p.77)
- 실현 주기가 하한의 2배를 넘으면 — 원인(pacing / FETCH / 링크)을 가르기 전에 계속 찍지 않는다
- `프레임 번호가 뒤로 갔다` ERROR — 되감김이다. **그 값이 곧 `BUFnFRAME` 의 폭**이므로 적어 두고 멈춘다

## 끝나고 할 것

1. DevNote **9.8 PROVISIONAL 표**에서 닫힌 줄을 표시하고, `guidehdr.
   HEATER_FIELD_CANDIDATES` 를 확정된 한 줄로 줄인다.
2. 실측값·경위는 DevNote 9장에, **결과와 실행법은 이 문서와 보고서**에
   (문서 층을 섞지 않는다).
3. `[icg] exptime_min` 은 그대로 둔다 — **정본은 ACF 계산값**이고 ini 는
   ACF 를 못 읽을 때의 대체값이다.
4. 실현 주기가 확정되면 `[icg] fetch_timeout` 이 여전히 하한 아래인지 다시 본다.

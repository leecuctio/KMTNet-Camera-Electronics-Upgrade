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
| 4 | ~~`DATE-OBS` 트랜스퍼 보정 **6.8 ms**~~ ⛔ **폐기된 모델** (2026-09-06) -- 코드에 보정이 없다.  `DATE-OBS` = **직전 `FrameShift` 개시 시각** 그대로다 (`sequencer.py:738-741`, 규격 10.1-4) | -- |
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

⛔ **로그는 `python3 -u … 2>&1 | tee <파일>` 로 남긴다** (2026-09-06 정정).
⚠️ 종전 문구는 `| tee` 였는데 **로그 핸들러가 `sys.stderr`**(`ics_sim/__main__.py`)
라 파이프가 stdout 만 넘긴다 — 경고·오류가 **기록에 하나도 안 남았다.**  실행
자리는 `ics_archon/` 다.

## 0단계 — 준비 (사람이 확인, 왕복 없음)

| 확인 | 어디 | 통과 |
|---|---|---|
| **링크가 서나** | `ping 10.0.0.162` | ✅ **해결법이 확정돼 있다** -- 광 스위치허브의 **포트별 auto-negotiation 을 해제하고 고정 1 G** 로 둔다 (운영자 2026-09-04).  Archon 은 1 Gbps 전용(매뉴얼 p.9)이고 SFP+ 는 자동협상을 하지 않는다.  ⚠️ **스위치를 교체·포트를 옮기면 그 설정이 안 따라온다** -- 링크가 안 서면 모듈·케이블보다 **포트 설정을 먼저** 본다.  자세히는 [INSTALL.md](INSTALL.md) "벤치 네트워크" |
| ⭐ **`Sync In` 이 비었나** | 컨트롤러 뒤판 배선 | ⛔ **master 의 `Sync Out` 이 이 유닛 `Sync In` 에 물려 있으면 노출이 진행되지 않는다** (운영자 실기 확인 2026-09-04).  `POWER=4`·`POWERGOOD=1` 인데 `FRAME` 이 영구히 0 이면 이것부터 -- `POWERGOOD` 은 **자기 전원만** 보고하고 외부 클록 의존을 보지 않는다.  README "프레임이 안 나올 때" |
| guide 컨트롤러 IP | `[icg] ctrl_host` | **`10.0.0.162`** — 정본은 ACF 안의 `IP=` 키다 (`APPLYALL` 이 심는 값).  호스트는 `10.0.0.201`(np0)/`10.0.0.202`(np1) |
| ACF 경로 | `[icg] acf` | `acf/KMTK_GUI_162_STA0201_R2619.acf` (현행 유일본) |
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
python3 -u tools/probe_archon.py --unit guide --host 10.0.0.162 --acf acf/KMTK_GUI_162_STA0201_R2619.acf 2>&1 | tee probe1_guide.log
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
| ⭐ **`go 1` 뒤 FRAME 증가분** | **정확히 1** (R2613+: flush 는 프레임을 만들지 않는다 — v1.10 발행 시점까지는 +2). 0 이면 flush 가 프레임을 만든 것(추론 틀림, 규격 OI-26 ③), flush 중 `WBUF=0` 인지도 | |
| ⭐ **첫 저장 프레임 완료 − LOADPARAMS 시각** | ≈ flush(1.2506) + 주기 (OI-26 ①). `FirstFlush` 슬롯 적용→`FlushFrame` 진입 지연도 여기서 실측 | |
| **첫 저장 프레임 bias/dark 레벨** | 2장째 이후와 통계적으로 같은가 (짧으면 어둡다 — `FlushLines` 검증, OI-26 ②) | |

**통과 기준**: 요약에 `문제 0건`.

## 2단계 — 파라미터의 Config 슬롯 번호 대조 (여전히 읽기 전용)

1단계 명령에 `--acf` 를 이미 줬으므로 같은 로그에 함께 찍힌다. `PARAMETER1`
(`Exposures`) · `PARAMETER2`(`IntMS`) 가 그 ACF 에 있고 컨트롤러 메모리의
같은 줄 번호가 그 키인지 `RCONFIG` 로 확인만 한다.

**통과**: 두 슬롯 다 `OK`, 또는 `컨트롤러의 설정 줄 …가 비어 있다`(아직 안
올린 상태 — 정상). ⛔ `설정 줄 …가 … 가 아니다` 가 나오면 **여기서 멈춘다** —
그대로 돌리면 `set_config` 가 엉뚱한 줄을 고쳐 **노출 시간이 조용히 안
바뀐다**.

## 3단계 — 본편 기동 ⚠️ **여기서 전원이 켜진다** (2026-09-06 정정)

```bash
python3 -u -m icg_archon 2>&1 | tee icg_boot.log
```

⛔ **종전 제목의 *"아직 전원은 안 켠다 — 첫 `go` 에서 켜진다"* 는 거짓이었다.**
`ArchonController.prepare()` 끝이 `if not self.powered: await self.power_on()` 이고
기동의 `_connect_controller()` 가 그것을 부른다.  `apply_acf = true` 이므로 기동
한 번에 **`CLEARCONFIG` → `WCONFIG` 전량 → `APPLYALL` → `POWERON`** 이 돈다.
⚠️ 그러므로 **0·1·2단계(배선 · probe · Config 슬롯 대조)를 반드시 먼저 마칠 것** —
슬롯 대조 전에 전원이 올라가면 되돌릴 수 없는 것은 없지만, 어긋난 줄로 `set_config`
가 돌면 `EXPTIME` 이 조용히 안 바뀐 파일이 남는다.
⭐ 전원 없이 기동만 보려면 `--backend sim` 을 쓴다.

| 항목 | 기대 | 실측 |
|---|---|---|
| 기동 검사 | `[icg] FETCH 상한 … 가 프레임 하한 … 이상이다` 경고가 **없어야** 한다 (`fetch_timeout=1.0` < 하한 1.251 s) | |
| ⭐ ACF 하한 | `acftiming` 이 타이밍 스크립트에서 읽은 하한 = **1.251 s**. 못 읽으면 ini 대체값 2.0 으로 내려가며 경고가 붙는다 — 그러면 4단계 수치의 뜻이 달라진다 | |
| HK 루프 | 1분마다 `~/AIC/Logs/hk.G.<YYYYMMDD>.csv` 에 한 행 + `hk_latest.G.json` 갱신 | |
| 콘솔 `hk` | 값 한 줄. `HEBOX`/`FSATEMP`/`FSAHUM` 은 안 실린다(=sentinel, Radionode off) | |
| 콘솔 `radionode status` | `off` | |
| `age_ms`/`lag_ms` | 첫 감시 로그에서 어떤 값인가 — `monitor_interval` 기본값의 근거 | |
| 포트 | `bind_port=6601` 로 떴나 (`ICS 몫` 경고가 없어야 한다) | |
| 노드 등록 | 배포 ini 는 이제 **`xis_host = 127.0.0.1` · `xis_port = 6660`** 이다 (운영자 2026-09-07).  `ICG`·`G.IC`·`G.CB` 세 이름의 등록 PING 이 나가고, 허브가 `G.IC` 를 모르면 `ERROR: No Route to Destination Host G.IC` 가 온다 (레거시에도 있던 실패 사례).  ⚠️ 허브가 다른 호스트면 그 IP 로 바꾼다.  비우면 direct-reply 라 허브 왕복이 **없는 것이 정상**이고, 그때는 아래 `>XIS HOSTS` 도 *"가는 길이 없습니다"* 로 거절된다 | |
| ⭐ 허브가 아는 노드 | 콘솔에 **`>XIS HOSTS`** 를 친다 — 그것이 `ICG>XIS HOSTS` 로 나간다 (2026-09-07 신설.  ⛔ 종전에는 `>NODE` 가 와이어로 안 나가서 **보낼 수단이 없었다**).  답 `DONE: HOST numHosts=… host0=… ` 에 **`ICG`·`G.IC`·`G.CB` 셋이 보이는지**가 등록됐다는 직접 확인이다 (허브의 노드 표는 **순전히 동적**이라 노드가 뭘 보내기 전엔 모른다).  `>XIS HOST ICG` 는 `IdleTime` 까지 준다 — HK 보고가 끊겼을 때 *ICG 가 죽었나 / 링크가 죽었나* 를 가르는 값이다.  ⚠️ 답은 콘솔 프롬프트가 아니라 **로그로** 온다(`보고 수신 (조치 없음) -- XIS>ICG DONE: HOST …`) — 위 실행법의 `2>&1 | tee` 가 그것을 잡는다.  ⚠️ 읽기 전용이지만 같은 명령표의 **`REMOVE <ID>` 는 `EXEC:` 가드가 없다** — 실수로 보내면 그 노드가 허브 표에서 빠진다 | |

## 3.5단계 — 운영자 명령 넷 (전원 · flush · 바이패스) — 2026-09-05 신설

콘솔에서 `ccdpowon` → `ccdflush` → `archon STATUS` → `ccdpowoff` 순서로 (문법·응답은 README "CCD 조작 명령 넷").

| 항목 | 기대 | 실측 |
|---|---|---|
| `CCDPOWON` | `DONE: CCDPOWON Power=ON` 이 **`poweron_wait`(12 s) 뒤**에 온다. 그 사이 `go` 는 `ERROR: GO Busy with CCDPOWON -- wait for its DONE` | |
| `CCDFLUSH` | `DONE: CCDFLUSH Flushed=1`. `FRAME` 의 `BUFnFRAME` 이 **안 는다**(flush 는 프레임을 안 만든다, R2613+). `RCONFIG` 로 `FirstFlush=1` 이 **그대로**인가 (R2616 상수 — 호스트가 안 쓴다) | |
| ⭐ flush 소요 | `DONE` 까지 ≈ 기본 노출시간 1.2506 s — 4단계 주기 실측의 예고편 (규격 OI-26 ①) | |
| `ARCHON STATUS` | `DONE: ARCHON POWERGOOD=1 …` 원문. 1800 B 넘으면 `...(+N bytes truncated, see log)` 가 붙고 전문은 `icg_archon.cmd` 로그에. ⭐ **이 응답 원문을 파일로 남긴다** — guide `.162` 의 STATUS 실물이 저장소에 한 번도 없다(11.30) | |
| `ARCHON` 거부 | 틀린 명령(예 `ARCHON WCONFIGZZZZ`)은 `ERROR: ARCHON rejected: …`. ⚠️ **컨트롤러는 모르는 이름에 무응답**이라 소문자 `archon status` 는 시한 초과 → 링크 재수립 → `Failed`. 명령 이름은 대문자로 | |
| 취득 중 거부 | `go 5` 도는 동안 `ccdflush` → `ERROR: CCDFLUSH Exposure in progress -- ABORT first` (히터 명령과 달리 **거부**다). ⭐ `archon STATUS` 는 취득 중에도 `DONE: ARCHON …` — 제한 없음(2026-09-05) | |
| `CCDPOWOFF` | `DONE: CCDPOWOFF Power=OFF`. 다음 `go` 가 `prepare()` 로 다시 켠다 | |
| 잠금과의 관계 | `expenable off` 뒤 `ccdflush` 는 되고 응답에 `(ExpEnable=OFF)` 가 붙는다 — flush 는 노출이 아니다 | |

## 4단계 — 첫 취득, 주기 실측 ⚠️ **전원 ON**

콘솔에서:

```
projid ENG
dark ICGTEST
guiexp 2
go 20
```

> `dark` 의 인자는 `OBJECT` 카드가 된다. guide 는 `bias`/`dark` 에서도
> **주기를 0 으로 만들지 않는다** — `EXPTIME` 이 셔터 노출이 아니라 **독출
> 개시 간격**이라 0 이 실현 불가능한 값이기 때문이다. `go n` 은 n장이고,
> R2613+: 앞에 **flush 1회**가 붙는다 -- 프레임을 만들지 않는다 (`Exposures=n` 을 한 LOADPARAMS 로 — flush 는 ACF 상수 `FirstFlush=1` 이 싣는다, R2616).

| `EXPTIME` 지시 | 실현 주기 (중앙값) | `간격이 밀렸다` 경고 | FETCH 초 | 저장 파일 수 |
|---|---|---|---|---|
| 2 s | | | | 20 |
| 5 s | | | | |
| 10 s | | | | |

그리고:

| 항목 | 기대 | 실측 |
|---|---|---|
| ⭐ **최소 노출시간 클램프** | `guiexp 1` (설정 가능한 최소 노출시간 1.3 s 미만) → **거부가 아니라 1.3 s 로 눌러 담는다** (`IntMS` 는 기본 노출시간 1.2506 기준 49 ms). 헤더 `EXPTIME` 은 요청값이 아니라 **실현값** | |
| ⭐ **`DATE-OBS`** | ⛔ **+6.8 ms 는 폐기된 모델이다** (2026-09-06 정정) -- 코드는 **직전 `FrameShift` 개시 시각을 그대로** 싣는다 (`sequencer.py:738-741`).  볼 것은 **연속 두 파일의 `DATE-OBS` 차 ≈ 실현 주기** 하나다 (규격 10.5절 6번 불변식).  ⚠️ 폴링 편향으로 늦는 쪽 쏠림이 있다(`sequencer.py:274`) -- 그 크기를 적어 둘 것 | |
| ⭐ **3버퍼 잠금** | 로그의 `RBUF`/`WBUF` — `LOCK` 이 반영되나, 엔진이 잠긴 버퍼를 피하나. ⚠️ science `--hold 20` 실측은 **2버퍼** 결과다, 옮겨 적지 말 것 | |
| guide FETCH | 8.3 MiB. science 실측 99~107 MiB/s 를 옮기면 ≈0.08 s — `fetch_timeout=1.0` 이 12배 여유인지 확인 | |
| 파일 | `~/AIC/data/guide/KMTK.<YYYYMMDD>.<NNNNNN>.G.fits`, **4224 x 1033** | |
| 헤더 | `C1_TEMP`/`C1_VOLT`/`C1_CURR` 8자리 · `ICGBUILD`(개명) · `CTRL2*` 없음 · `DATASRC=ARCHON_GUIDE` · `RDMODE=UNKNOWN` | |
| ⭐ **최근 고친 카드 셋** (2026-09-06 추가) | ① **`FPAID` 가 공백 18자가 아니라 `NC`** (`1e650ce`) ② **`HKUDATE` 가 19자로 실린다** -- 종전엔 늘 `NC` 였다 (`64894f2`) ③ **`CTRL1CFG`** -- ini 값이 있으면 그 값, 비면 ACF 파일명 파생 (규격 v1.12 5.5절, `46aad59`) | |
| ⭐ **`BUFnFRAME` 다시** | ⛔ **증가분 = 찍은 장수** 다 (2026-09-06 정정).  종전의 *"+ 폐기 1"* 은 v1.10 시절 모델이고 **R2613+ 사이클에는 폐기분이 없다** (`sequencer.py:627`).  flush 도 프레임을 안 만든다 | |

## 4-b단계 — ⏳ **연속 노출 중 명령 지연** (2026-09-09 운영자 물음) ⚠️ **전원 ON**

운영자 물음 둘을 한 번에 닫는다: *"연속 촬영 중 `trigout <초>` 명령 실행 지연 여부"* 와
*"`HKDATA` 를 60초 폴링값으로 쓸지 즉시 되읽을지"*.

⛔ **막히지는 않는다** — 취득 중이라고 거부하는 문이 두 명령에 없다.  밀리는 원인은
하나뿐이다: `_locked_thread` 가 모든 링크 왕복을 한 줄로 세워 **진행 중인 FETCH 뒤에
선다** (guide 8.3 MiB ≈ 0.08 s, 잠금 상한 `fetch_timeout = 1.0 s`).  주기가 1.251 s 라
**락이 잡혀 있을 확률은 대략 6 %** — 그래서 **여러 번 쳐야** 최악값이 잡힌다.

### 준비

```ini
[icg]
latency_warn_ms = 0          ; ⭐ 실측용 -- 전부 남긴다 (끝나면 운용값으로)

[logging]
file = ~/AIC/Logs/icg_archon.log     ; 주석을 푼다 -- 나중에 grep 하려면 필요
```

⚠️ `TRIGOUT` 은 이 눈금을 **안 탄다**(늘 남는다) — `0` 으로 두는 것은 `HKDATA` 때문이다.

### 재기

```
python -m icg_archon
```

콘솔에서:

```
projid ENG
dark ICGTEST
guiexp 1.3
expenable on
go 30
```

`go 30` 이 도는 **약 40초 동안** 아래를 섞어 친다.  ⭐ **↑ 화살표로 직전 명령을 불러
Enter** 를 되풀이하면 빠르다.

| 칠 것 | 몇 번 | 무엇을 보나 |
|---|---|---|
| `hkdata` | **20회 이상** | 락 경합 확률이 6 % 라 적게 치면 최악값을 못 잡는다 |
| `trigout 2000` | 5~10회 | 올림 지연 · 내림 지연 · **폭오차** (⚠️ 눈금이 **ms** 다) |
| `trigout 0` | 2~3회 | 즉시 내림의 지연 |

⚠️ **한가할 때 기준선을 먼저 잡는다** — `go` 전에 같은 명령을 5회씩 쳐 둔다.  그것이
비교 대상이다 (종전 실측: `RCONFIG` 3회 = **6 ms**).

### 읽기

```bash
grep -E '지연 --' ~/AIC/Logs/icg_archon.log
```

이런 줄이 나온다:

```
[2026-09-09T..] HKDATA 지연 -- 수신→완료 88.1 ms (취득중)
[2026-09-09T..] TRIGOUT 올림 지연 -- 수신→완료 92.4 ms (취득중) Sec=2
[2026-09-09T..] TRIGOUT 내림 지연 -- 수신→완료 2095.1 ms (취득중) 폭오차 +2.7 ms (요청 2s)
```

`(한가)`/`(취득중)` 이 붙으므로 **두 무리를 갈라서** 최댓값·중앙값을 적으면 된다.

| 항목 | 기대 | ✅ 실측 (2026-09-09) |
|---|---|---|
| `HKDATA` 지연 — 한가 | ≈6 ms (`RCONFIG` 3회) | **중앙 7.0 ms** (최대 10.5, n=9) |
| ⭐ `HKDATA` 지연 — 취득중 **최댓값** | FETCH 0.08 s 뒤에 서면 ≈90 ms | **최악 107.8 ms** (중앙 7.7, 95 % 96.5, n=51).  50 ms 초과 **14 %** |
| `TRIGOUT 올림` — 한가 | ⏳ 미지였다 | ⛔ **232.5 ms** — 락이 아니라 **`APPLYSYSTEM` 자체가 ≈229 ms** |
| ⭐ `TRIGOUT 올림` — 취득중 **최댓값** | ⏳ 미지였다 | 337.4 ms (중앙 233.8 — 취득 추가분은 중앙 **+1.3 ms** 뿐) |
| ⭐⭐ **폭오차** | *"밀림을 안 물려받는다"* 로 봤다 | ⛔ **틀렸다 — +235.1 ms 가 17회 내내 일정**.  내림 자신의 `APPLYSYSTEM` 이 폭에 들어갔다.  ⭐ 보정을 넣어 고쳤다 (실현 최소 폭 ≈235 ms) |
| ⛔ **취득을 해쳤나** | `Exposures` 가 되돌려지면 장수가 끊긴다 | ✅ **안 해친다** — `go 20` 이 20장 완주 (그 사이 `trigout 2` 4회) |
| 프레임 주기 | `trigout` 친 프레임이 튀지 않나 | ✅ `간격이 밀렸다` 8건은 **명령과 무관** (넷은 명령보다 **먼저** 났다) |
| 링크 | 재동기 0회 | ✅ **0회** (11.54 고침 뒤) |

⏳ **남은 확인 하나**: 보정을 넣은 뒤 `trigout 2000` 을 쳐서 **폭오차가 0 근처로 떨어지는지**
로그로 본다 (`폭오차 +x.x ms (요청 2000 ms, 보정 -234 ms)`).  ⚠️ **눈금이 ms 로 바뀌었다** (2026-09-09 저녁).

| 상황 | 기대 | ✅ 실측 (2026-09-09, `…003.log`) |
|---|---|---|
| **취득중** — `go 20` 중 `trigout` 11회 (2·3·5 s) | 폭오차 ≈ 0, 음수도 정상 | **중앙 +1.7 ms · 범위 −2.7 ~ +7.9** (n=11).  ⭐ 종전 +235 ms 에서 **99 % 사라졌다** |
| 요청 폭을 키우면 | 오차가 안 커져야 한다 (더해지는 상수였으니) | ✅ 2 s 와 5 s 의 오차가 같은 크기 |
| `trigout 0` (즉시 내림) | 대기 중 펄스를 끊는다 | ✅ `Sec=10`·`Sec=30` 펄스를 각각 끊었다 (⚠️ 그때 응답 낱말이 `Sec=` 였다 — 지금은 `MS=`) |
| 새 `trigout` 이 앞 것을 끊나 | 타이머는 하나만 산다 | ✅ 3 s 펄스 중 새 3 s 를 쳤더니 앞 것이 사라졌다 |
| ⚠️ 짧은 펄스 — `trigout 100` | 만들 수 없다는 경고 + 폭 ≈235 ms | ⏳ 아직 안 쳐봤다.  ⭐ 눈금이 ms 라 하한(≈235)과 **같은 단위로** 읽힌다 |

⏳ ⚠️ **음수 폭오차가 왜 정상인가**: 보정값 `C` 는 *"올림을 시작해서 끝날 때까지"* 라
**FETCH 를 기다린 락 대기**가 섞인다.  내림이 그만큼 안 기다리면 너무 많이 빼서 폭이
짧아진다.  ⭐ 종전의 **늘 +235 ms** 와 달리 이제는 두 왕복의 락 대기 **차**만 남으므로
평균 0 근처여야 한다.  ⛔ **한쪽으로 치우쳐 크게 나오면** `ctrl.last_cmd_timing` 으로
락 대기를 뺀 순수 적용시간을 쓰도록 다듬는다 (DevNote 11.55).

### 이 실측으로 정할 것

1. ⭐ **`HKDATA` 의 히터 셋**을 (갑) 지금대로 `RCONFIG` 3회 · (을) 폴링값 ·
   (병) `config_value()`(캐시 + `config_dirty` 때만 되읽기) 중 무엇으로 둘지.
   ⚠️ 운영자 판단은 *"히터를 빈번히 켜고 끌 일이 없고 trigout 도 모니터링할 필요
   없으면 폴링값"* 이고, ⭐ `HTRSET`·`HTRFORCE`·`TRIGOUT*` 은 **인자 없이 치면 즉시
   되읽기 조회**라 확인 경로가 따로 있다는 것이 그 판단의 근거다.
2. ⏳ **운용 임계 `latency_warn_ms`** — 기본 50 은 한가할 때 기준선의 8배로 잡은
   임시값이다.  ⛔ 취득 중 정상 지연이 늘 50 을 넘으면 그 값은 *"이상"* 이 아니라
   **소음**이 된다.  **실측 최악값 위**로 다시 잡는다.

## 5단계 — `STOP` / `ABORT` 뒤 꼬리 (⏳ 미결 하나를 닫는다)

`go 50` 을 걸고 중간에 `stop`, 다시 `go 50` 을 걸고 중간에 `abort`.

| 항목 | 기대 | 실측 |
|---|---|---|
| ⭐ 해제 직후 `FRAME` 증가 수 | **꼬리 한 장인가 두 장인가** = `Exposures=0` 이 읽히는 시점. 시퀀서는 최대 2홉까지 소화한다 | |
| `busy` | 꼬리를 소화하는 동안 True — **그것이 의도다** | |
| 다음 `go` | 꼬리를 자기 **첫 저장** 프레임으로 오인하지 않는다 (기준선 오염) | |
| `abort` 두 번 | 두 번째가 뒷정리를 끊지 않는다. IDLE 통보는 **마지막 요청자**에게 (`df4d4fc` 확인 항목) | |
| ⭐ `stop` 뒤 꼬리 flush (R2616+) | 마지막 저장 프레임 뒤 `FRAME` 은 **안 늘고** ≈ 1.25 s 클록이 한 번 더 돈다(`Exposures=0` 의 LOADPARAMS 가 ACF 상수 `FirstFlush=1` 을 다시 싣는다). 그 뒤 조용 | |

**통과**: `DONE: ABORT` 뒤 `EXPSTATUS=IDLE` 하나, 그리고 다음 `go` 가 정상.

## 6단계 — P-k, `Pixels` 600 vs 540 ⚠️ **단일 변수**

절차·판정은 [SMC_CLAUDE.md](SMC_CLAUDE.md) 의 **"P-k 실행 절차"** 를 그대로
⛔ **판 차이를 먼저 읽을 것** (2026-09-06) -- 그 두 판은 현행 **R2617 과 7판 차이**이고
그 사이에 유휴 flush·`DG`/`RG` 파형이 여러 번 바뀌었다.  **옛 판으로 받은 바이어스·다크를
R2617 프레임과 섞으면 단일 변수가 깨진다** -- 옛 두 판은 **서로만** 견주고, 오늘 파형으로
제대로 재려면 R2617 사본에 `Pixels=600` + `FlushLines=2692` 를 넣은 시험 ACF 를 만들어
R2617 원본과 짝지어라.  ⚠️ `acf/…_R2610.acf` 는 이제 **`acf/archive/`** 에 있다.

따른다. 요지: 두 ACF(`acf/archive/…_R2609.acf` = 600 · `acf/archive/…_R2610.acf` =
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

## 부록 -- DG 정적 덤프 실측 (`FRAME6`/`IMAGE6` DG=0 V 를 고칠지의 근거) — 2026-09-05 신설

물음(운영자): *"DG 로 register 가 통째로 비워지는지 실측 시험이 필요하면 시험 프로시저 준비해줘."*
현행 R2617 의 flush 는 `SkipLine` 에서 DG=HIGH 로 600 번 시프트하므로(R2615) 답이 무엇이든 **flush 는 안전**하다.
이 실측이 정하는 것은 **FrameShift(1033 사이클) 동안 DG 를 올려 두면 레지스터에 도착하는 전하가 R 클록 없이도
덤프되는가** — 그렇다면 `FRAME6`/`IMAGE6` 의 DG=A_LOW(0 V, STA 템플릿 슬립 — `acf/README.md` R2614 절)를 DG_HIGH
로 고치는 후속 판(**R2620** — R2617 은 빈 줄, R2618 은 `TRIGOUTFORCE`, R2619 는 `DIO_POWER` 가 썼다)이 정당하다.

### 원리

정상 프레임에서 레지스터 잔량은 `LINE13="DGLOW; CALL HorizontalShift(600)"`(R2617 번호) 이 독출 전에 쓸어 낸다.  그 줄을
**시프트 없는 한 줄**로 바꾸면 잔량이 **첫 독출 행에 더해져** 나온다 — 그것이 측정량이다.  잔량의 주 원천은
FrameShift 가 store 를 1033 행 밀어 레지스터로 떨어뜨리는 전하(store 는 직전 독출 ≈1.25 s 동안 쌓인다)이므로,
**약한 균일광**(돔 플랫 램프 최저 — 정상 프레임 수준 수십 e⁻/픽셀) 아래에서 재면 신호가 뚜렷하다: 잔량 ≈ 1033 ×
(행당 store 전하) → 첫 행이 나머지 행의 수백~천 배.  ⚠️ 어둠에서 30 분 유휴로 재는 방법은 `go 1` 의 첫 flush 가
image/store 를 비워 버려 신호가 남지 않는다 — 균일광이 맞다.

### 전제
* CCD 저온 안정 · 전원 ON · 균일광 세기는 **단계 B 의 첫 행이 포화하지 않도록** 먼저 맞춘다(정상 프레임 수준 ≤ 50 e⁻).
* 시험 ACF 는 R2617 사본에서 표의 줄/상태만 바꾼다.  `Pixels`·`Lines`·`FlushLines` 는 손대지 않는다.  판 사이에는
  `APPLYALL` 뒤 `POWERON` 이 다시 필요하다(매뉴얼 p.51).
* `go 3` 으로 찍고 **2·3 번째 파일**을 쓴다(1 번째의 직전은 flush 라 store 축적 시간이 다르다).  `guiexp 1.3`.

### 절차
| 단계 | 시험 ACF | 보는 것 |
|---|---|---|
| A 기준선 | R2617 그대로 | 첫 행 중앙값 − 2~10 행 중앙값 = Δ₀ (≈ 0 이어야 한다: 600 번 시프트가 레지스터를 비운다) |
| B 시프트 생략 · DG 낮음 | `LINE13="DGLOW; X(1)"` | Δ_B — 잔량이 첫 행에 더해진다(양수, "잔량이 있다" 의 증거이자 척도) |
| C 시프트 생략 · DG 높음(정적) | `LINE13="DGHIGH; X(10000)"` (100 µs, R 클록 없음) | Δ_C — **Δ_C ≈ Δ₀ 면 정적 DG 가 이미 찬 레지스터를 비운다**, Δ_C ≈ Δ_B 면 못 비운다 |
| D FrameShift 중 DG 높음 (본 물음) | `FRAME6`/`IMAGE6` 의 DG 항을 `DG_HIGH,1,0` 으로 + `LINE13="DGLOW; X(1)"` | Δ_D — **Δ_D ≈ Δ₀ 면 도착하는 전하가 시프트 없이 덤프된다** → FRAME6 수정 정당 |
| E (선택) 부작용 | D 의 상태표 + `LINE13` 원상 | 배경·첫 행·노이즈가 A 와 같은가 |

각 단계 **3 회**, 첫 행/다음 9 행의 중앙값 차를 `GAIN` 으로 e⁻ 환산해 표에 적는다.

### 판정
* Δ_D ≈ Δ₀ (Δ_B 의 10 % 이하): FrameShift 중 DG=HIGH 가 레지스터를 비운다 → `FRAME6`/`IMAGE6` DG_HIGH 후속 판(**R2618**) 정당.
* Δ_D ≈ Δ_B: DG 는 시프트(R 클록) 중에만 덤프한다 → FRAME6 은 그대로, flush 는 현행(R2615 SkipLine DGHIGH)으로 충분하고 그것이 유일한 길.
* Δ_C 와 Δ_D 가 갈리면(C 만 ≈ Δ₀): 정적 DG 는 비우지만 도착 중 전하는 못 잡는다 → FrameShift 뒤 `DGHIGH; X(n)` 한 줄을 넣는 R2617 대안.
* Δ_B ≈ Δ₀ (잔량 자체가 없다): 광량이 너무 약하다 → 세기를 올려 다시.

### 멈출 조건
* 첫 행 포화/블루밍 — 결과 폐기, 광량을 낮춰 재시작.
* 단계 B~D 에서 `ERROR`/`간격이 밀렸다` — 시험 ACF 가 주기를 바꿨다는 뜻이니 표의 줄 외에 바뀐 것이 없는지 대조.

## 무엇이 나오면 멈추나

- 1단계 요약에 `문제` 가 하나라도 (자리 표·결측·기하)
- 기하가 4224 x 1033 이 아니면 — 본편이 fetch 앞에서 거부한다 (바이트로 대조한다)
- `POWER` 가 4 에 못 닿는데 바이어스 값이 그럴싸하면 — `POWER≠4` 에서는 전 채널 ~0 V 여야 한다 (p.77)
- 실현 주기가 기본 노출시간의 2배를 넘으면 — 원인(pacing / FETCH / 링크)을 가르기 전에 계속 찍지 않는다
- `frame number went backwards` ERROR — 되감김이다. **그 값이 곧 `BUFnFRAME` 의 폭**이므로 적어 두고 멈춘다

## 끝나고 할 것

1. DevNote **9.8 PROVISIONAL 표**에서 닫힌 줄을 표시하고, `guidehdr.
   HEATER_FIELD_CANDIDATES` 를 확정된 한 줄로 줄인다.
2. 실측값·경위는 DevNote 9장에, **결과와 실행법은 이 문서와 보고서**에
   (문서 층을 섞지 않는다).
3. `[icg] exptime_min`(설정 가능한 최소 노출시간, 1.3) 은 그대로 둔다 — 기본 노출시간의
   **정본은 ACF 계산값**이고 ini 값은 그 위의 정책이다(ACF 를 못 읽을 때는 대체값 노릇도 한다).
4. 실현 주기가 확정되면 `[icg] fetch_timeout` 이 여전히 기본 노출시간 아래인지 다시 본다.

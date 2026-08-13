# SMC_CLAUDE.md

`ics_sim/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md) 참고.

## 이 폴더가 뭔가

**신규 Python ICS 의 첫 실행 산출물.** 레거시 조사(3부작 보고서)가 끝난 뒤 실제로 만든 첫 코드다.

- 지금은 **시뮬레이터** — 카메라 하드웨어 없이 레거시와 호환되는 메시지를 낸다.
- 다음 단계는 **실기 구동** — `ics_sim/hardware/archon.py` 에 실제 CCD 제어 코드를 넣으면, 시퀀서·명령 처리부·메시지 규약은 **무개정**으로 그대로 쓴다. `[hardware] backend = archon` 한 줄로 전환.
- 최종적으로 `ics` 로 개명해 운영 배포.

## 먼저 읽을 것

> **[DevNote.md](DevNote.md) 가 이 폴더의 중심 문서다.** 사양·판단 근거·조사 이력·정정 이력·백로그가 전부 들어 있다. 코드를 고치기 전에 해당 절을 먼저 본다.

| 문서 | 언제 |
|---|---|
| [DevNote.md](DevNote.md) | 설계를 이해하거나 바꿀 때. 15개 장 |
| [README.md](README.md) | 그냥 돌려보고 싶을 때 |
| [xis/xis.md](xis/xis.md) | 붙을 상대(레거시 허브)의 소스·설정·기동 방식이 궁금할 때 |
| [../ics_legacy/ics_legacy_report.md](../ics_legacy/ics_legacy_report.md) | 레거시 원본 동작이 궁금할 때 |
| [../OBSAgent/obsagent_report.md](../OBSAgent/obsagent_report.md) | OBSAgent 쪽 사정이 궁금할 때 |

## 절대 깨뜨리면 안 되는 것 (DevNote 3장)

OBSAgent 는 **개정하지 않기로 확정**돼 있다. 그래서 아래는 규약이지 취향이 아니다.

1. **수신은 9개 노드 ID 전부** — `ICS` + `{K,M,T,N}.IC` + `{K,M,T,N}.CB`. `kstatus`/`dmawait`/`datasource` 가 개별 노드 주소로 온다. (발신 이름은 자유 — 비대칭이다)
2. **`Acquisition Complete.`(마침표 포함) 4회, `Wrote` 4회** — 개수가 곧 규약이다. `Wrote` 는 CB 직송이 아니라 **ICS 가 OBS 로 중계한 것**을 센다.
3. **파일명 `KMTN<x>.<8자리>.<6자리>.fits` 고정** — OBSAgent 가 `"KMTN"`+6 부터 15자를 잘라 쓴다.
4. **`ExpNum` 질의에 응답** — OBSAgent 가 readout 중 스스로 보낸다. 없으면 관측자 화면의 ExpNum 이 안 바뀐다.
5. **시간 창 3종** — 획득 완료 4개는 1.8초 안에, `EXPSTATUS=IDLE` 은 그 뒤 0.9초 안에, `Wrote` 4개는 25초 안에.
6. **`EXPSTATUS=` 는 전이 시 1회, `OBS` 로만** — 과다 발신하면 CamStatus 가 역행한다.

전부 `tests/test_obsagent_contract.py` 가 검증한다. **테스트가 깨지면 그건 규약을 어긴 것이다.**

## 메시지 오염 버그 (DevNote 5장)

레거시 ICS 는 커맨드워드 슬롯을 비우지 않아 비동기 메시지가 엉뚱한 커맨드워드를 달고 나갔다(CTIO 634일에 173,635건 등). **이 프로그램은 그걸 고친 것이 존재 이유 중 하나다.**

- `emitter.py` 의 모든 메서드가 `cmdword` 를 **명시적 인자**로 받는다. 상태에서 물려받는 경로를 만들지 마라.
- 송신 전 `validate()` 가 6가지 오염 패턴을 검사한다.
- `--bug-compat` 로 레거시 오염을 재현할 수 있다(골든 대조용, 기본 꺼짐).

## 상태 (2026-08-11)

- **구현 완료**: 전체 노출 사이클(DARK/BIAS/OBJECT), `GO n` 다중 노출, 전 명령 디스패치, 텔레메트리 중계, 옵션 FITS, 콘솔, 결함 주입 6종, **`STOP`/`ABORT`**(9.2.1), **AUX control TCP 연동**(9.2.2), **자기 발신 에코 필터·브로드캐스트 중복 억제·노드 ID 검증**(3.1.2 — 실물 XIS 연동의 전제)
- **테스트 197개 전부 통과**
- **실물 연동 시험 완료 (2026-08-11)** — 재빌드한 XIS(v2.9.1) 허브에 **실물 TCSAgent·OBSAgent 와 함께** 물려 돌렸다. 9개 노드 ID 등록·에코 필터·재등록·개별 IC 라우팅·노출 사이클 전 구간 통과, 타임아웃 창 3종 모두 큰 여유. **`ExpNum` 응답 값이 한 칸 밀리는 결함 하나를 잡아 고쳤다**(DevNote 3.4·12.14). 전체 결과는 DevNote **3.7**
- **아직 안 만든 것**: `BIN` 하나. `strict_legacy` 면 무응답이고, 구현 지침은 `commands.py` docstring 에 있다.
- **일부러 안 만든 것**: `ROI`/`DISPL`/`MOVIE` — **레거시 ICS 명령 테이블에 아예 없어서** 핸들러를 두지 않았다. 레거시와 똑같이 `Didn't understand` 로 거부된다(DevNote 6.8).
- **2026-08-08 전 문서 정합성 일제 점검 완료** — 레거시 보고서 3부작·Agent 보고서 2종·raw_fits_spec·xis 문서의 낡은 서술/모순 30여 건 정정. 내역은 DevNote 14장 말미.
- **2차 연동 시험 완료 (2026-08-11)** — **`ExpNum` 값 규약이 실물에서 확정됐다**(DevNote 3.7.2). 노출 2회로 readout 중 `ExpNum`==파일 번호 · 종료 후 `ExpNum`==`FitsNum` · `EXPNUM` 응답 N+1 을 모두 확인. 12.14 의 교정이 시뮬 테스트를 넘어 관측자 화면에서 검증된 것은 이번이 처음이다. **로그는 터미널 스크롤백 대신 `[logging] file` 로 받을 것** — 스크롤백은 페인 폭 경계에서 한 글자씩 먹혀 5.3 의 와이어 손상과 구분이 안 된다(3.7.2 말미)
- **EXPNUM 지속 (2026-08-11)** — 위 시험의 전제였다. 첫 시도에서 `FitsNum=00000000.000000` 이 나왔다. 번호가 매 실행 1 로 되돌아가 기존 파일과 겹치고, 파일명 fail-safe 가 `KMTN` 없는 이름을 쓰자 OBSAgent 파싱이 실패한 것이었다. **마지막으로 쓴 번호를 `[paths] expnum_file`(기본: 설정파일 옆 = `~/AICS/Config/ics_sim.expnum`)에 기록하고 기동 시 +1 부터 쓴다.** `data_dir` 를 비워도 되돌아가지 않는다 — 근거와 버린 대안은 DevNote **11.12**
- **raw pair 규격 적용 (2026-08-11)** — **저장 단위와 통보 단위를 분리했다.** 물리 파일은 컨트롤러당 1개(`<SITE>.<날짜>.<번호>.<MK|NT>.fits` ×2), `Wrote` 통보는 CCD당 1회씩 4회를 레거시 논리 이름(`KMTN<c>.…`, 불변)으로 낸다. 하드웨어 계약도 컨트롤러 단위로 개정했다(`write_frame`, **D-012**). 헤더에 규격 5.1·5.2 정체성 카드, sentinel 은 5.0절대로(C-9/OI-6). **기존 규약 테스트 177개가 한 줄도 안 고치고 통과** — 통보가 논리 이름 그대로라 OBSAgent 는 무변경이다. 근거·경위는 DevNote **11.13**, 규격은 [`../raw_fits_spec/`](../raw_fits_spec/README.md) 2.3·2.5·5장
- **다음 단계**: ① 연동 시험 계속(아래 "이어서 시작하는 자리") ② `ics_archon` — **Archon 3 unit**(과학 2 + **가이드 1**, DevNote 9.1) 제어. **파일 구성·이름·헤더 규약은 이미 시뮬이 지키고 있으므로**(위 항목) 남은 것은 실제 픽셀·실물 크기(19200×9400)·`BITPIX=16`+`BZERO=32768`·픽셀 배치·Archon 텔레메트리 카드다 (C-8, DevNote 9.1)

## ▶ 이어서 시작하는 자리 (2026-08-11 기준)

**벤치가 SSO AIC 리눅스(`kmtnet-sso`)에 그대로 살아 있다.** 창 네 개 — 0=XIS · 1=`ics_sim` · 2=`obstool` · 3=`pctcs`. 기동 명령은 [README](README.md) "실물 연동 시험", 설치·빌드는 [`../TCSAgent/tcsagent_report.md`](../TCSAgent/tcsagent_report.md) · [`../OBSAgent/obsagent_report.md`](../OBSAgent/obsagent_report.md) 각 12절(`build-local.sh` 한 줄이면 재현된다).

| 순서 | 할 일 |
|---|---|
| ~~**1**~~ | ~~**`ExpNum` 교정의 실물 재확인**~~ — **완료 (2026-08-11 2차, DevNote 3.7.2).** 노출 2회로 판정: readout 중 `ExpNum` == 그 프레임의 파일 번호, 종료 후 `ExpNum`==`FitsNum`, `EXPNUM` 응답 N+1, `FitsOsc` `CHECK`→`NO`. 타임아웃 창 3종도 두 프레임에서 밀리초까지 동일. **전제였던 EXPNUM 카운터 결함을 먼저 고쳐야 했다**(11.12) — fail-safe 가 침묵해야 이 판정이 성립한다<br>※ **1회만 돌리면 판정이 안 된다.** OBSAgent 가 받은 값을 `strNextNum` 에 담아 두고 **다음 노출 시작 시** `strCurNum` 으로 승격해 표시하므로(`commands.c:835,848`), 1회 세션에서는 `ExpNum=00000000.000000` 이 정상이다 |
| **2** | **Telcom/AUX 시뮬레이터 설치** — KASI 제작본이 `../../__localonly_tcs_simulator/TCS_simulation.zip` 에 있다. **빌드가 없다**(stdlib 전용, Python 3.12+ 필요 — Ubuntu 24.04 기본이 3.12 라 그대로 된다). `pctcs.ini` 의 `TCS_Host`/`AUX_Host` 가 이미 `127.0.0.1` 이라 그대로 맞물린다. 절차와 함정은 아래 블록. 판정: 두 링크 `DOWN`→`UP`, `tstat`/`astat` 실값, 그리고 **`ics_sim` 의 텔레메트리 중계가 `passthrough`(빈 필드)에서 실값으로 바뀌는 것** — FITS 헤더의 AUX/TCS 키워드가 처음 실값을 받는 자리 |
| **3** | **세부 연동 시험** — `STOP`/`ABORT`(9.2.1 의 `DONE:` 본문은 실측 근거 없이 정한 것) · `GO n`(6.1) · `.osc` 스크립트 관측(3.5) · 결함 주입 6종(**실물 OBSAgent 의 경보·`opause` 경로를 확인하는 유일한 수단**) |

판정 기준과 지난 결과는 [DevNote 3.7](DevNote.md). 시험 도구는 `tools/xis_probe.py`(노드 하나를 흉내 내는 프로브 — 포트 6650 이라 `obstool` 과 겹친다).

### TCS 시뮬레이터 — 설치 절차와 함정 (2026-08-11 사전 점검)

자료는 `../../__localonly_tcs_simulator/` 에 있다 — `TCS_simulation.zip`(시뮬 본체) + 계통도 PDF 2종(레거시 R2 · 신규 CEU R2.0). **빌드가 없다.** 옮기고 `python3 -m sim.monitor` 로 끝이다.

```bash
export LANG=C.UTF-8                       # 아래 함정 ⑤
mkdir -p ~/tcs-sim && tar -xzf tcs-sim.tgz -C ~/tcs-sim --strip-components=1
cd ~/tcs-sim && python3 -V                # 3.12 이상 (display 계열이 PEP 701 f-string 사용)
python3 -m sim.selfcheck && python3 -m sim.aux_selfcheck \
  && python3 -m sim.display_selfcheck && python3 -m sim.fieldlog_probe   # 넷 다 RESULT: ALL PASS
python3 -m sim.monitor                    # 벤치 창 4 — 5750(Telcom) + 5752(AUX) + 상태 패널
python3 -m sim.live_probe                 # 창 5 — 실소켓 33항목. 반드시 '갓 기동' 상태에서
```

**개발 PC(Windows, Python 3.12)에서 위 다섯 줄을 미리 돌려 전부 통과시켰다.** 포트도 안 겹친다 — 5750/5752(시뮬) · 6600(`ics_sim`) · 6606(`TC`) · 6650(`OBS`) · 6660(XIS).

| # | 함정 | 대처 |
|---|---|---|
| **①** | **`.osc` 스크립트가 첫 노출 라인에서 멈춘다.** TCSAgent `tmradec` 는 `NEXTRA`+`NEXTDEC`+`MOVNEXT` 만 보내고 `TRACK ON` 을 보내지 않는데(`commands.c:2194,2216`), 시뮬은 추적 OFF 의 `MOVNEXT` 를 `BAD` 로 거부한다(`sim/simulator.py:272-295` — 레거시는 `OK` 를 주고 조용히 무동작하는 쪽이라, 시뮬이 일부러 엄하게 만든 것). 응답 판정 실패 → 재시도 → **`opause`** | 시뮬 기동 후 `tcmd TRACK ON` 을 **1회** 치거나, 시험용 `.osc` 머리에 `+tcmd TRACK ON` 을 넣는다. `osc/` 실사용 자산에는 이 줄이 하나도 없다(실운영에서는 관측자가 초저녁에 손으로 켜므로) |
| **②** | **`osc/` 원본 스크립트는 대부분 라인 skip 된다.** 실제 날짜·좌표라서 시험 시각에는 고도 30° 아래다 | 좌표를 **LST 기준으로 찍는다.** `sim/obsagent_probe.py:113-120` 이 이미 그렇게 한다 — 첫 `tcsstatus` 에서 `ST=` 를 뽑아 `HA=-1h` 목표를 만든다. 그 로직을 그대로 쓰면 된다 |
| **③** | **프로브가 AUX 상태를 실제로 움직인다** (필터·셔터·포커서). `ics_sim` 노출과 동시에 돌리면 카메라 셔터를 서로 뺏는다 | 직렬화한다. `live_probe` 는 초기상태 단언이 많아 **갓 기동 직후**가 아니면 오탐 |
| **④** | **`[auxcontrol] enabled = true` 인 시험은 `time_scale = 1.0` 이어야 한다.** 셔터 사이클이 와이어 기준 14초인데 시뮬 시간은 우리 축척을 따라오지 않는다 | `exp >= 5` · 노출 간격 >= 15초. 근거와 실측표는 [DevNote 9.2.3](DevNote.md) |
| **⑤** | `display_selfcheck`·`fieldlog_probe` 가 파일을 **기본 로케일 인코딩**으로 읽는다 (Windows cp949 에서 둘 다 죽었다) | 리눅스 UTF-8 이면 그냥 된다. `export LANG=C.UTF-8` 로 확실히 |
| **⑥** | `acmd simul cshut/staterr/clearerr` 가 **시뮬에 없다** (AUX 43 verb 중 31개 구현, `SIMUL` 은 규격 밖이라 미포함) | AUX 서브시스템 에러 주입은 불가. 대신 `ALL DISCONNECT` → 6상태어 `NC` 경로로 `AUXLINK` 유지·복구를 본다. `ics_sim --inject` 6종은 ICS 자체 결함이라 무관 |

**pctcs 기반 프로브 4종**(`shut_probe`·`limit_probe`·`nc_probe`·`obsagent_probe`)은 `$PCTCS_DIR/ini/pctcs.localhost.sta.ini` 를 상대경로로 요구한다(이름이 하네스에 하드코딩). `build-local.sh` 가 만드는 것은 `~/AICS/Config/pctcs.ini`(ISISclient 모드, `TC`/6606) 하나뿐이지만, 빌드 시 `cp -R` 로 `ini/` 가 통째로 복사되므로 `~/AICS/build/TCSAgent/ini/pctcs.kmtna.sta.ini` 는 **이미 거기 있다.** 호스트 두 줄과 `LOGFILE`(`tc.sta` 로 갈라야 6606 벤치와 안 겹친다)·`CATFILE` 만 sed 로 고쳐 이름을 맞추면 된다. **STA 모드는 `TC.STA`/5755 라 본 벤치를 내리지 않고 돌릴 수 있다.** 우리에게 쓸모 있는 것은 `shut_probe`(`SET_SH` → `SHUTOP` 6전이가 실 pctcs 에서 어떻게 읽히는지)와 `nc_probe`(⑥의 대체 수단) 둘이다 — 선택 항목이므로 손으로 한 번 돌려 보고 쓸만하면 그때 스크립트에 굳힌다.

## 조사 자료

레거시 로그는 저장소에 없다.

| 자료 | 위치 | 커밋 |
|---|---|---|
| 샘플 로그 (9개월×3사이트) | `../ics_legacy/__sample_isislog/` | `*.log` 비커밋 |
| 오염 버그 샘플 | `../ics_legacy/__sample_isislog/samples_for_bug.txt` | **커밋** |
| 전량 아카이브 (48GB, 1,113일) | `../../__localonly_isislogs/` | 비커밋 |
| 골든 픽스처 (발췌) | `tests/fixtures/golden_*.txt` | **커밋** |
| 오염 패턴 (파생) | `tests/fixtures/bug_patterns.txt` | **커밋** |

원본이 있는 컴퓨터에서는 `tools/scan_legacy_logs.py` 로 언제든 재검증할 수 있다. 원본이 없어도 **커밋된 픽스처만으로 테스트는 전부 돈다**.

## XIS 노드 등록 — 해결됨 (2026-08-04)

**통합 `ics` 는 9개 노드 ID로 메시지를 받아야 해서, 그 9개가 전부 같은 (IP,port) 를 가리키도록 등록한다.** 이 구성이 XIS 에서 되는지가 한동안 최대 미해결 항목이었는데, **XIS 서버 소스로 안전함이 확정됐다.**

<details>
<summary>확정 전의 상태 (판단 근거를 되짚을 때만 보면 된다)</summary>

- 확인됐던 것: XIS는 **노드ID → 주소** 방향 테이블을 갖는다 (`ABC`/`GMON` 이 ephemeral 포트로 매번 바꿔 보내는데도 응답을 받는다).
- 확인 안 됐던 것: 같은 (IP,port)에 여러 ID를 올려도 되는지. 48GB 로그 전체에 그런 사례가 없었다.
- 그때의 대비책: 문제가 확인되면 **2안(노드별 소켓/포트 9개)** 으로 전환. → **불필요해졌다.**

</details>

**진단 수단**: 등록 안 된 노드로 보내면 XIS가 발신자에게 `ERROR: No Route to Destination Host K.IC - host is unknown/unlisted` 를 돌려준다. 실물 시험의 판정 기준이다.

**근거 — XIS 서버 소스** (운영본 `ISIS/server/`, stock ISIS v2.9.1 — 트리 판정은 [xis/xis.md 3절](xis/xis.md)):

- **클라이언트 테이블은 노드 ID로만 키잉된다** — `strcmp(testStr, clientTab[i].ID)==0`, 주소는 비교에 안 쓰이고 **확인 없이 갱신**된다. 주소 충돌 검사 로직 자체가 없다. **→ 1안(단일 소켓 + 9개 ID PING) 안전. 2안 불필요.**
- `MAXCLIENTS 64`(운용 13개 안팎) · `MAXPRESET 32`(사용 13~14) — **`isis.ini` 한 줄 추가에 제약 없다.** → [xis/xis.md 6.2](xis/xis.md)
- XIS 재시작 시 `handShake()` 가 **`XIS>AL PING` 을 시리얼 포트 + preset UDP 목록에 개별 전송**한다. IP 브로드캐스트가 아니다.
- 브로드캐스트 relay 는 송신 슬롯 하나만 제외한다 — 9개 ID 로 등록한 우리에겐 같은 데이터그램이 **최대 9부 중복 배달**되고, 우리가 자기 노드 앞으로 보낸 유니캐스트도 **그대로 되돌아온다**. (한때 인용했던 *"clients that share the same port …"* 주석은 코드와 다른 문구였다 — [xis/xis.md 6.3](xis/xis.md))

**구현 완료**: 기동 시 9개 ID 로 PING, `XIS>AL PING` 브로드캐스트에 9개 전부 PONG(XIS 재시작 후 재등록의 유일한 경로), 그리고 **자기 발신 에코 필터 + 브로드캐스트 중복 억제 + 노드 ID 검증**(DevNote 3.1.2, `test_xis_echo.py` 15개). 에코를 안 거르면 XIS 경유 모드에서 ERASE/SHOPEN 이 이중 실행된다 — 점검(2026-08-08)에서 잡은 실물 연동의 마지막 전제 조건이었다.

**남은 것 — 운영 측 작업**: 신규 `ics` 의 주소를 XIS `isis.ini` 의 `UDPPort` 목록에 한 줄 추가해야 XIS 재시작 시 PING 을 받는다. 넣기 전에 XIS 콘솔 `UDPPING <ip> <port>` 로 선시험 가능.

> ⚠️ **운영 허브에 그냥 붙이지 말 것** — XIS 는 같은 ID 의 주소를 무조건 덮어쓰므로, 레거시 ICS/IC 가 살아 있는 허브에 시뮬을 등록하면 그 라우팅을 즉시 가로챈다. **레거시 계통을 정지하거나 시험용 XIS 인스턴스를 쓴다** ([xis/xis.md 7절](xis/xis.md) 경고 블록).

자세한 내용은 [DevNote 3.1.1·3.1.2](DevNote.md), 논의 전 과정은 [xis/xis.md 부록 A](xis/xis.md).

## XIS 원본 보관 — `xis/` (2026-08-05 신설)

레거시 허브의 소스·운영 설정·기동 스크립트·실행파일을 `__dts_legacy` 3사이트 백업에서 뽑아 [`xis/`](xis/) 에 모았다(162 파일). **운영본 소스와 빌드 정의는 온전하나 운영 바이너리(`isis` v2.9.1)는 백업에 없다** — 재빌드가 전제다. 중심 문서는 [xis/xis.md](xis/xis.md), 파일 출처는 [xis/MANIFEST.md](xis/MANIFEST.md).

## 레거시 실제 구조 (2026-08-04, `__dts_legacy` 로 확인)

신규 설계를 이해하려면 알아야 할 배경이다. 상세는 [`../ics_legacy/ics_legacy_report.md`](../ics_legacy/ics_legacy_report.md) 1.3.1절.

- **IC/ICS 는 VDOS(DOS) 머신**이고 리눅스 `isisrelay` 가 UDP 6600 ↔ 시리얼 9600 으로 중계한다. 신규 `ics` 는 이 3계층을 **한 프로그램으로 대체**한다.
- **`ICS` 는 IC 와 같은 소프트웨어**(`INSTRUMENT=ICS`, 디렉토리만 `\KMTX`). → 메시지 오염 버그가 ICS·IC 양쪽에 똑같이 나타나는 이유.
- BUILD 접두어 = 프로그램 디렉토리: `KX`=\KMTX, `KS`=\KMTS, `KG`=\KMTG.
- `SP` 노드(`KMTNsp`) = 과학 계열 예비 IC, XIS preset 의 `.107` 자리로 보인다.
- **IC(VDOS) 본체 소스를 `IC2.img` 에서 확보했다 (2026-08-04).** `__localonly_osu_legacy/IC2_KX20160323.1381_ICSci_{CTIO,SAAO}/IC2.img` (각 8 GB, 비커밋). **C 가 아니라 FreeBASIC** 이고 실행파일과 소스가 함께 들어 있어 역어셈블이 필요 없었다. 꺼내는 절차는 [DevNote 2.2](DevNote.md) — 7-Zip 으로 0.3초면 된다.

논의 전 과정(문제 발견 → 내 근거 없는 단언 → 사용자 지적 → 로그 실측 → 결정)은 [xis/xis.md 부록 A](xis/xis.md) 와 DevNote 12.7 에 남겨 뒀다.

## ICS 소스로 확정된 것 (2026-08-04)

로그 추론으로 세웠던 5·6장이 소스 검증을 거쳤다. 판정표는 [DevNote 12.11](DevNote.md).

- **오염 버그의 원인 코드** — `SHARE\PAP7COM.INC:797-802` 의 `SUB Prt`. 첫 낱말이 콜론으로 끝나기만 하면 `COMS(OutPort).CommandEcho` 를 **무조건** 끼워 넣는다. 슬롯은 포트별로 살아남고 정상 운용 중 비워지지 않는다. → DevNote 5.5
- **`EXPSTATUS=` 는 상태 통보가 아니라 접미사다** — 같은 `SUB Prt` 가 노출 중 모든 콜론 메시지에 붙인다. 노출 시퀀스 쪽은 본문이 빈 `STATUS: ` 껍데기이고 `EXPSTATUS=` 는 주석 처리돼 있다. **"전이 시 1회" 규칙은 레거시 모방이 아니라 레거시보다 엄격한 선택**이다.
- **`STOP`/`ABORT`/`BIN` 은 레거시에 구현되어 있다** — "미구현"은 틀린 서술이었다. 반대로 `ROI`/`DISPL`/`MOVIE` 는 ICS 명령 테이블에 아예 없다(ICS 는 공용 `PAP7.CMD` 를 포함하지 않는다). **`commands.py` 를 이에 맞게 고쳤다.** → DevNote 6.8
- **SSO 는 `Wrote` 중계가 끊겨 있다** — SSO Caliban 만 `STATUS: Wrote` 로 보내는데 ICS 중계 분기는 `DONE:` 을 요구한다. 결과적으로 SSO 는 **매 노출 `FitsSaved` 를 25초 타임아웃으로만** 세운다(OBSAgent 에 SSO 전용 우회가 이미 있어 경고는 안 뜬다). → DevNote 6.9

## IC·ICG 계통 확정 (2026-08-05)

VM 이미지가 **5개**로 늘었다(`ICSci` CTIO/SAAO · `ICGui` · `K.IC` · `G.IC`). 계통 전체의 구성이 드러났다.

- **역할은 `0ICCFG\IC.INI` 한 파일이 정한다.** 모든 이미지가 세 프로그램을 다 담고 있고, `ICHOST`/`INSTRUMENT` 와 `CD \KMTx` 로 갈린다.
- **`ICG` 는 `ICS` 와 같은 바이너리다** — 둘 다 `\KMTX\PAP7KX.EXE`. 런타임 `ICHost` 로 다섯 군데만 분기하고, 그중 `AcquisitionCompleteCounter > 3`(과학, CCD 4개) vs `> 0`(가이드, 1개)이 **"4회 누적" 규약이 과학에만 있는 구조적 이유**다. → DevNote 6.11
- **`Acquisition Complete.` 마침표 비대칭은 의도된 것** — IC 가 OBS 에는 마침표 있는 문자열, ICS 에는 없는 문자열을 **각각 따로** 보낸다. OBSAgent 가 마침표로 세므로 이걸 빠뜨리면 `opause` 로 간다. → `ics_legacy_report.md` 4.6
- **`USESTATUS` 는 셔터 닫힘 알림 타입을 `DONE:`→`STATUS:` 로 바꾸는 스위치**였다. 관측자 UI 가 `DONE:` 을 명령 완료로 오해하는 걸 피하려던 조치.
- **오염 버그는 최소 2017-06-19 까지 안 고쳐졌다** — G.IC 이미지의 더 나중 소스에도 같은 코드가 있다.
- **`STOP`/`ABORT` 를 구현했다** — 레거시 분기 그대로. 단 수락 시 `DONE:` 본문은 실측 근거가 없어 우리가 정한 것이다. → DevNote 9.2.1

## AUX control 연동 (2026-08-05 신규)

셔터 개폐 때 KMTNet AUX control software 에 TCP 로 알린다. **레거시에는 없던 경로다.**

- 규격: `TCSAgent/__reference/KMTNet AUX control remote commands(v20140908).pdf`
- 설정 키는 TCSAgent 의 `pctcs.kmtn*.ini` 와 같게 뒀다(같은 서버를 가리킨다). 값 뒤 `(KMTNC)` 같은 괄호 설명도 그대로 받는다.
- 보내는 것: `KMTNET AUX <pid> FILTERS SET_SH OPEN|CLOSE`. **DARK/BIAS 는 보내지 않는다**(셔터를 안 연다).
- 응답: `OK` 통과 / `BAD` 빨강 / `WAIT` 청록 / **무응답도 빨강**. 규격 2-4 상 ID 오타면 서버가 침묵하므로 조용한 실패를 눈에 띄게 했다.
- **어떤 경우에도 노출은 완주한다.** 서버가 없어도 마찬가지.

> ⚠️ **이 경로는 HW 트리거의 시뮬레이션용 대체물이다.** 실기에는 셔터 SW 명령이 없고 HE 박스 TTL 이 그 역할을 한다. `backend = archon` 으로 갈 때 `[auxcontrol] enabled = false` 로 꺼야 구동원이 겹치지 않는다 — `config.validate()` 가 그 조합을 경고한다. → DevNote 9.2.2

## 다음에 이어서 할 만한 일

1. ~~**실제 OBSAgent·XIS 연동 시험**~~ — **1차 완료 (2026-08-11).** 9노드 등록·라우팅·노출 사이클 전 구간 통과, `ExpNum` 결함 하나 수정. **남은 항목은 위 "이어서 시작하는 자리"** 로 옮겼다. 결과는 DevNote 3.7.
2. **`ics_archon` 구현** — Archon 컨트롤러 2기 제어 + raw FITS pair 저장. 제어 시퀀스는 `cam_char/archon/` 이식(DevNote 9장), **저장 규격은 [`../raw_fits_spec/`](../raw_fits_spec/README.md)** — 저장/통보 단위가 갈라지는 지점(D-009/D-010)은 DevNote 9.1 의 상기 블록에 정리돼 있다.
3. ~~`STOP`/`ABORT` 구현~~ · ~~`\KMTS`·`\KMTG` 소스 정독~~ — **둘 다 2026-08-05 완료.** 아래 "IC·ICG 계통 확정" 참조. ~~자기 발신 에코 처리~~ — **2026-08-08 완료**(위 "XIS 노드 등록" 참조).
4. **`icg` 착수** — 가이드 계통. OBSAgent 가 가이드 발신을 무시하므로 하위호환 부담이 없어 자유롭다. 공통 로직(IMPv2 노드, 텔레메트리 중계, 파일명 fail-safe)은 이 폴더에서 뽑아 쓸 수 있다.
5. **DevNote 13장 백로그** — 구조화 로깅, 상태 조회 API 등.

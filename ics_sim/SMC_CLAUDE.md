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

## 상태 (2026-08-03)

- **구현 완료**: 전체 노출 사이클(DARK/BIAS/OBJECT), `GO n` 다중 노출, 전 명령 디스패치, 텔레메트리 중계, 옵션 FITS, 콘솔, 결함 주입 6종
- **테스트 113개 전부 통과**
- **미구현(의도적)**: `BIN`/`ROI`/`DISPL`/`STOP`/`ABORT`/`MOVIE` — 레거시도 미구현이고 48GB 로그 전량에서 0건. **스텁과 구현 지침은 `commands.py` 에 있다**
- **다음 단계**: `hardware/archon.py` (DevNote 9장에 계약과 참고 자산 정리)

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

**근거 — XIS 서버 소스.** `ics_legacy/__dts_legacy/`(ICS 컴퓨터 `dts` 폴더 백업, 3개 사이트)의 `EXEC_ISIS/server/` 에 XIS 서버 소스 전체가 있다. 확인 결과:

- **클라이언트 테이블은 노드 ID로만 키잉된다** — `strcmp(testStr, clientTab[i].ID)==0`, 주소는 비교에 안 쓰이고 갱신만 된다. 주소 충돌 검사 로직 자체가 없다.
- 브로드캐스트 코드가 *"clients that share the same port as the sending host"* 를 명시적으로 다룬다 — **한 포트를 여러 클라이언트가 쓰는 건 설계상 예상된 상황**이다.
- **→ 1안(단일 소켓 + 9개 ID PING) 안전. 2안 불필요.**
- `MAXCLIENTS 64`, 현재 운용 13개 안팎이라 여유 충분.
- XIS 재시작 시 `handShake()` 가 **`XIS>AL PING` 을 시리얼 포트 + `isis.ini` 의 preset UDP 목록에 개별 전송**한다. IP 브로드캐스트가 아니다.

**구현 완료**: 기동 시 9개 ID 로 PING, **`XIS>AL PING` 브로드캐스트에도 9개 전부 PONG**(XIS 재시작 후 재등록의 유일한 경로).

**남은 것 — 운영 측 작업**: 신규 `ics` 의 주소를 XIS `isis.ini` 의 `UDPPort` 목록에 한 줄 추가해야 XIS 재시작 시 PING 을 받는다. 단 `MAXPRESET` 여유를 먼저 확인할 것 — 백업 헤더는 `8` 인데 CTIO 설정엔 13줄이라 배포 바이너리가 다를 수 있다. **XIS 콘솔에서 `info` 를 치면 `NumPreset/MaxPreset` 이 나온다.**

자세한 내용은 [DevNote 3.1.1 (12)](DevNote.md).

## 레거시 실제 구조 (2026-08-04, `__dts_legacy` 로 확인)

신규 설계를 이해하려면 알아야 할 배경이다. 상세는 [`../ics_legacy/ics_legacy_report.md`](../ics_legacy/ics_legacy_report.md) 1.3.1절.

- **IC/ICS 는 VDOS(DOS) 머신**이고 리눅스 `isisrelay` 가 UDP 6600 ↔ 시리얼 9600 으로 중계한다. 신규 `ics` 는 이 3계층을 **한 프로그램으로 대체**한다.
- **`ICS` 는 IC 와 같은 소프트웨어**(`INSTRUMENT=ICS`, 디렉토리만 `\KMTX`). → 메시지 오염 버그가 ICS·IC 양쪽에 똑같이 나타나는 이유.
- BUILD 접두어 = 프로그램 디렉토리: `KX`=\KMTX, `KS`=\KMTS, `KG`=\KMTG.
- `SP` 노드(`KMTNsp`) = 과학 계열 예비 IC, XIS preset 의 `.107` 자리로 보인다.
- **IC(VDOS) 본체 소스를 `IC2.img` 에서 확보했다 (2026-08-04).** `__localonly_osc_legacy/IC2_KX20160323.1381_ICSci_{CTIO,SAAO}/IC2.img` (각 8 GB, 비커밋). **C 가 아니라 FreeBASIC** 이고 실행파일과 소스가 함께 들어 있어 역어셈블이 필요 없었다. 꺼내는 절차는 [DevNote 2.2](DevNote.md) — 7-Zip 으로 0.3초면 된다.

논의 전 과정(문제 발견 → 내 근거 없는 단언 → 사용자 지적 → 로그 실측 → 결정)은 [DevNote 3.1.1](DevNote.md) 과 12.7절에 남겨 뒀다.

## ICS 소스로 확정된 것 (2026-08-04)

로그 추론으로 세웠던 5·6장이 소스 검증을 거쳤다. 판정표는 [DevNote 12.11](DevNote.md).

- **오염 버그의 원인 코드** — `SHARE\PAP7COM.INC:797-802` 의 `SUB Prt`. 첫 낱말이 콜론으로 끝나기만 하면 `COMS(OutPort).CommandEcho` 를 **무조건** 끼워 넣는다. 슬롯은 포트별로 살아남고 정상 운용 중 비워지지 않는다. → DevNote 5.5
- **`EXPSTATUS=` 는 상태 통보가 아니라 접미사다** — 같은 `SUB Prt` 가 노출 중 모든 콜론 메시지에 붙인다. 노출 시퀀스 쪽은 본문이 빈 `STATUS: ` 껍데기이고 `EXPSTATUS=` 는 주석 처리돼 있다. **"전이 시 1회" 규칙은 레거시 모방이 아니라 레거시보다 엄격한 선택**이다.
- **`STOP`/`ABORT`/`BIN` 은 레거시에 구현되어 있다** — "미구현"은 틀린 서술이었다. 반대로 `ROI`/`DISPL`/`MOVIE` 는 ICS 명령 테이블에 아예 없다(ICS 는 공용 `PAP7.CMD` 를 포함하지 않는다). **`commands.py` 를 이에 맞게 고쳤다.** → DevNote 6.8
- **SSO 는 `Wrote` 중계가 끊겨 있다** — SSO Caliban 만 `STATUS: Wrote` 로 보내는데 ICS 중계 분기는 `DONE:` 을 요구한다. 결과적으로 SSO 는 **매 노출 `FitsSaved` 를 25초 타임아웃으로만** 세운다. → DevNote 6.9

## 다음에 이어서 할 만한 일

1. **실제 OBSAgent·XIS 연동 시험** — XIS 허브를 띄우고 `--xis-host` 로 붙여 `kstatus` 를 쳐 본다. **소스 정독으로 세운 규약 전체가 실물에서 처음 검증되는 자리**이고, `transport.feed()` 로는 확인할 수 없는 라우팅 경로도 여기서만 실증된다. 선행 조건은 XIS `isis.ini` 에 시뮬 주소 한 줄 추가(위 "남은 것" 참조). 이어서 `.osc` 스크립트를 돌리면 규약 검증이 완결된다.
2. **`hardware/archon.py` 구현** — DevNote 9장. `cam_char/archon/` 의 기존 스크립트를 옮겨오면 된다.
3. **`STOP`/`ABORT` 구현** — **레거시에 있는 기능을 아직 안 옮긴 것**이다(새 기능이 아니다). 레거시 분기 로직과 거부 문자열이 `commands.py` docstring 에 그대로 적혀 있으니 옮기기만 하면 된다.
3b. **`\KMTS`·`\KMTG` 소스 정독** — ICS(`\KMTX`)만 읽었다. IC 쪽 고유 동작(`SHOPEN` 카운트다운 주기, `TRANSFER`/`REQ SWAP` 핸드셰이크)을 확정하려면 필요하다. 꺼내는 절차는 DevNote 2.2.
4. **`icg` 착수** — 가이드 계통. OBSAgent 가 가이드 발신을 무시하므로 하위호환 부담이 없어 자유롭다. 공통 로직(IMPv2 노드, 텔레메트리 중계, 파일명 fail-safe)은 이 폴더에서 뽑아 쓸 수 있다.
5. **DevNote 13장 백로그** — 구조화 로깅, 상태 조회 API 등.

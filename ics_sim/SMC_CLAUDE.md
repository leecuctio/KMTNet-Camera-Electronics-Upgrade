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
- **테스트 111개 전부 통과**
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

## 미해결 — XIS 노드 등록 (최우선)

**통합 `ics` 는 9개 노드 ID로 메시지를 받아야 하는데, 지금은 그 9개가 전부 같은 (IP,port) 를 가리키도록 등록한다.** 이 구성이 XIS에서 되는지 **아직 확인되지 않았다.**

- 확인된 것: XIS는 **노드ID → 주소** 방향 테이블을 갖는다 (`ABC`/`GMON` 이 ephemeral 포트로 매번 바꿔 보내는데도 응답을 받는다).
- 확인 안 된 것: 같은 (IP,port)에 여러 ID를 올려도 되는지. **48GB 로그 전체에 그런 사례가 없고, XIS 서버 소스도 저장소에 없다.**
- 현재: **1안(단일 소켓 + 9개 ID PING)** 으로 구현. `[transport] register_all_nodes` 로 끌 수 있다.
- 문제가 확인되면 **2안(노드별 소켓/포트 9개)** 으로 전환.

**사용자가 ISIS/XIS 소스를 찾아 공유하기로 했다.** 받으면 [DevNote 3.1.1 (7)](DevNote.md) 의 확인 항목부터 볼 것 — 클라이언트 테이블의 인덱스 키, 같은 주소 재등록 시 처리, 테이블 크기, `AL` 브로드캐스트의 중복 수신 여부.

논의 전 과정(문제 발견 → 내 근거 없는 단언 → 사용자 지적 → 로그 실측 → 결정)은 [DevNote 3.1.1](DevNote.md) 과 12.7절에 남겨 뒀다.

## 다음에 이어서 할 만한 일

1. **실제 OBSAgent·XIS 연동 시험** — XIS 허브를 띄우고 `--xis-host` 로 붙여 `kstatus` 를 쳐 본다. **위 미해결 항목의 가장 빠른 확인법**이자, `transport.feed()` 로는 검증할 수 없는 라우팅 경로 전체를 처음 실증하는 일이다. 이어서 `.osc` 스크립트를 돌리면 규약 검증이 실물로 완결된다.
2. **`hardware/archon.py` 구현** — DevNote 9장. `cam_char/archon/` 의 기존 스크립트를 옮겨오면 된다.
3. **`STOP`/`ABORT` 구현** — 운영 편의상 가치가 높다. 스텁에 구현 방향이 적혀 있다.
4. **`icg` 착수** — 가이드 계통. OBSAgent 가 가이드 발신을 무시하므로 하위호환 부담이 없어 자유롭다. 공통 로직(IMPv2 노드, 텔레메트리 중계, 파일명 fail-safe)은 이 폴더에서 뽑아 쓸 수 있다.
5. **DevNote 13장 백로그** — 구조화 로깅, 상태 조회 API 등.

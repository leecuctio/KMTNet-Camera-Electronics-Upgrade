# SMC_CLAUDE.md

`ics_archon/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는
[../README.md](../README.md), 이 폴더의 구성·변경 내역은 [README.md](README.md).

## 이 폴더가 뭔가

**실기 ICS(`ics_archon`)를 만드는 자리다.** 최종 형태는
**`ics_sim` + Archon 컨트롤러 제어**이고, 시퀀서·명령 처리부·메시지 규약·헤더
층은 `ics_sim` 이 이미 갖고 있으므로 **가져다 쓰고 개정하지 않는다.**

지금은 그 전 단계 — **실험실 취득 스크립트에 raw spec 을 먼저 적용해 둔 상태**다.
본편 코드는 아직 없다.

## 먼저 읽을 것

| 문서 | 언제 |
|---|---|
| [README.md](README.md) | 폴더 구성 · 본편 계획 · 실험실 스크립트 **핵심 참고사항** |
| [README_labtest.md](README_labtest.md) | ⭐ **실험실 취득 스크립트에 관한 모든 것.** 손볼 자리(행 번호)·첫 실행 점검·경고의 뜻·변경 내역·판 이력 |
| [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 11.19~11.21 | 왜 그렇게 정했나(경위·판단). 9장은 하드웨어 확장점 |
| [`../ics_sim/SMC_CLAUDE.md`](../ics_sim/SMC_CLAUDE.md) | 흡수할 상대의 상태·규약 |
| [`../raw_fits_spec/`](../raw_fits_spec/README.md) | 산출 규격(raw FITS pair). 헤더 5장의 바이트 정본은 견본 pair |

## 절대 깨뜨리면 안 되는 것

1. **`v1.0.bigbuf` 는 실제로 돌려서 쓰던 검증된 코드다** (사용자 확인
   2026-08-22). v1.1 은 그 위의 개정이므로, 판단 기준은 늘 하나다 — **그
   검증된 취득 경로를 건드렸나.** 컨트롤러와의 왕복 기준으로 v1.1 이 추가한
   프로토콜 명령은 **`STATUS` 하나뿐**이고, `TELEMETRY_ENABLE = False` 로 두면
   왕복이 v1.0 과 완전히 같아진다. 그 성질을 없애지 말 것 — 실기에서 원인을
   가르는 유일한 수단이다.
2. **`archoncmd(cmd, timeout=None)` 의 기본값을 바꾸지 말 것.** `APPLYALL` 처럼
   오래 걸리는 명령이 있어 무한 대기가 기본이어야 한다. 상한은 v1.1 이 새로
   넣은 `STATUS` 에만 준다.
3. **`__` 접두 폴더는 읽기 전용이다** (운영자 규칙). 편집이 필요하면 그 파일을
   이 루트로 사본을 떠서 작업한다 — v1.1 이 바로 그 방식으로 만들어졌고 v1.0
   원본은 `__ref_archon_control/` 에 남아 있다.
4. **헤더 틀은 `ics_sim/ics_sim/rawcards.py` 와 같은 원천**(견본 초안 v1.0
   pair)이다. 카드를 늘리거나 바꾸려면 **견본이 먼저 개정돼야 한다** —
   `ics_sim/tests/test_raw_draft.py` 가 바이트 대사로 어긋남을 잡는다.
5. **헤더에 들어가는 값은 ASCII 전용이다.** 헤더는 문자 단위로 80자씩 조립하고
   파일에는 utf-8 바이트로 쓰므로, 한글 한 자(3바이트)가 2880B 정렬을 깨고
   **파일 전체를 못 읽게** 만든다 — 취득 중에는 경고가 한 줄도 안 뜬다.
   `_check_identity_setup()` 이 기동에서 거부하고 `fits_card` 가 `?` 로
   치환한다. 둘 다 없애지 말 것.
6. **`archoncmd` 가 시한 초과로 빠져나가면 연결을 새로 열어야 한다.** 응답을
   검증한 뒤에야 `msgref` 를 올리는 구조라, 시한 초과 시 명령은 나갔는데
   `msgref` 는 그대로다 → 늦은 응답을 다음 명령이 먹고 그 다음이 죽는다.
   `msgref` 만 올리는 것으로는 부족하다(부분 수신분이 소켓에 남는다).
   `_resync_archon_link()` 가 그 일을 한다.

## 상태 (2026-08-22)

- **현행 = `archon_kmtnet_labtest_v1.1.bigbuf.py`, `SCRIPT_VERSION='1.1.1'`**
  (science 유닛, BIGBUF=1). raw spec 적용 + 적대적 검토 6건 + 투입 전 감사
  회귀 4건 수정.
- **투입 전 감사 (에이전트 21, blocker 0)** 에서 잡혀 v1.1.1 에서 고친 것 —
  **네 건 모두 내가 v1.1 에서 넣은 자리이고, 넷 다 취득 중에 조용했다**:
  1. STATUS 시한 초과가 `msgref`·수신 스트림을 어긋내 **두 명령 뒤에 취득이
     죽었다** → 실패 시 연결 재수립(`_resync_archon_link`).
  2. 손편집 문자열의 비ASCII 한 자가 **FITS 를 통째로 못 읽게** 만들었다
     (`assert len(head) % 2880` 은 문자 수라 못 잡는다) → 기동 검사 + 바이트
     단정 + `fits_card` 치환.
  3. 데이터부 2880 패딩(v1.1 신설) + NAXIS 하드코딩이 겹쳐, 실제 프레임이
     선언보다 길면 **v1.0 에서는 경고만 나고 읽혔던 파일이 아예 안 열렸다**
     (samplemode = 정확히 2배) → fetch 전에 바이트 수 대조.
  4. 예외가 나면 `POWEROFF` 를 건너뛴 채 끝났다 → 노출 루프 `try/finally`.
  - 함께: 재실행이 멱등하지 않다는 점(D-016 이 번호를 밀어 올린다)을 데이터셋
    시작에 경고로 알린다. **v1.0 은 덮어썼다** — 분석이 프레임 번호를 믿으면
    어긋난다.
- **검증된 것**: 헤더 144카드가 견본과 **바이트 단위 일치**(불일치 0) ·
  2880B×4 정렬 · 컴파일(`SyntaxWarning` 포함) · 위 1~3 을 가짜 컨트롤러·
  astropy 로 실측. `python tests/verify_labtest_v11.py` (19항목, 실패 0) —
  **스크립트를 손봤으면 돌리고 나가라.**
- ❌ **미검증**: **실기 왕복**(POWERON → LOADPARAMS → FRAME 폴링 → FETCH)을
  한 번도 돌리지 않았다. 실제 픽셀이 담긴 FITS 의 converter 투입도 미검증.
- **guide 유닛**은 `archon_kmtnet_labtest_v1.0.smallbuf.py`(원본 사본, 미개정).
  **guide raw 규격이 아직 없어** spec 적용 대상이 아니다 — 착수 시
  `DATASRC='ARCHON_GUIDE'` + `CTRL1xx` 한 벌 규약(raw spec 5.5절).
  ⚠️ 헤더가 science 크기(19200×9400)를 하드코딩하고 있으므로 그대로 쓰면 안 된다.

## 브랜치 (장수 브랜치)

작업은 **`ics-archon-v1.0-build`** 에 쌓는다(origin 에 푸시됨).
**main 합류는 `ics_archon` v1.0 완성 후** — 운영자 확정, "한참 뒤"다.

⚠️ **그래서 main 을 주기적으로 들여와야 한다.** 그냥 두면 완성 시점에 큰 충돌
하나를 맞는다. 특히 **raw spec 5장 검토**가 위험하다 — v1.4 는 1~4장만
반영했고 5장 이후는 팀 협의 후 다음 판이므로, 그 개정이 오면 견본 pair 와
`rawcards.py`(그리고 이 폴더 스크립트의 내장 `RAWCARDS`)를 **직접** 건드린다.
바이트 대사 시험이 그때 알람 역할을 한다. 합류 방식은 `--no-ff` 거품 머지.

## ▶ 이어서 시작하는 자리

| 순서 | 할 일 |
|---|---|
| **1** | **실기로 v1.1 돌려 보기** — 사용자가 코드를 손봐서 직접 돌릴 예정(2026-08-22). 손볼 자리와 점검 항목은 [README_labtest.md](README_labtest.md). 결과를 그 문서의 "첫 실행 결과" 에 채운다 |
| **2** | **본편 착수** — `ics_sim/ics_sim/hardware/archon.py` 스텁에 제어 시퀀스(CLEARCONFIG→WCONFIG→APPLYALL, POWERON, LOADPARAMS, FRAME 폴링, FETCH)를 옮기고 **백엔드 3계약**을 채운다: `controller_info()`(SYSTEM) · `controller_telemetry()`(STATUS) · `sensors()`(HK 3계통). 원형은 이 폴더의 `archon_status()`/`ctrl_telemetry_cards()` |
| **3** | **guide 계통** — guide raw 규격이 정해진 뒤 smallbuf 판에 적용 |

## Archon 매뉴얼에서 확정한 사실 (`__ref_archon_control/`)

본편에서 다시 찾지 않도록 적어 둔다. 근거는 매뉴얼(2021-02-23)·ZTF Readout
Notes(2014-10-30), 쪽수는 매뉴얼 기준.

- **STATUS** (p.47-49): `BACKPLANE_TEMP` · 모듈별 `MODm/TEMP` · 전원 레일
  `P2V5_V/I` … `P35V_V/I`. **raw spec `Cn_VOLT` 의 자리 순서가 이 레일 순서**다
  (`P2V5 P5V P6V N6V P17V N17V P35V`).
- **SYSTEM** (p.46): `BACKPLANE_ID`(16진 고유 ID = 시리얼 대용) ·
  `BACKPLANE_VERSION` · `MODn_TYPE/REV/VERSION/ID`. **모델명 문자열 필드는 없다.**
- **AD(비디오) 모듈은 중앙 4슬롯(5-8)에만** 꽂힌다 (p.20) — 모듈당 4채널(tap).
  그래서 `TEMP_SLOTS` 기본값이 `BACKPLANE_TEMP + MOD5~8/TEMP` 다.
- **컨트롤러는 적용된 ACF 이름을 보고하지 않는다** (p.54) — `CTRLnCFG` 는
  호스트가 관리한다(그래서 `ics_sim` 은 `[controllers] ctrl<n>_cfg` ini 로 받는다).
- **TIMER / BUFnTIMESTAMP 는 10 ns tick** (p.49-50). ⚠️ **`BUFnTIMESTAMP` 는
  프레임 기록(readout) 개시 시점**이라 `DATE-OBS`(노출 개시)로 **그대로 쓸 수
  없다.** 정밀 시각이 필요하면 `TIMER` ↔ 호스트 UT 상관 + 트리거 에지
  타임스탬프(`BUFnREATIMESTAMP` 등)를 봐야 한다.
- **BIGBUF=1 → 768 MB 버퍼 2개** (기본은 512 MB × 3). science 가 이 구성이고
  베이스 주소는 `BUFnBASE` 로 보고된다 — 스크립트가 그 값을 그대로 FETCH 에 쓴다.
- 셔터는 **Trigger Out** 이 INT 클럭을 따르게 해서 구동한다 (p.15) — 스크립트는
  `TRIGOUTFORCE` 0/1 + `APPLYSYSTEM` 으로 여닫는다.

## 관련 문서

| 문서 | 위치 |
|---|---|
| 산출 규격 (raw FITS pair) | [`../raw_fits_spec/`](../raw_fits_spec/README.md) |
| 헤더 카드 템플릿 (공유 원천) | `../ics_sim/ics_sim/rawcards.py` |
| 백엔드 계약 | `../ics_sim/ics_sim/hardware/base.py` (D-012) |
| L0 MEF ICD · converter | `../mef_fits_spec/` · `../mef_converter/` |
| 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |

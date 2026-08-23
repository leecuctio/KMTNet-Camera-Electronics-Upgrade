# ics_archon — Archon 컨트롤러 제어 (준비 단계)

**최종 목표**: `ics_sim/`(시퀀서·메시지 규약·헤더 층)과 이 폴더의 Archon 제어
코드를 합쳐 실기 ICS(`ics_archon`)를 만든다.  지금은 그 전 단계 — 실험실
취득 스크립트에 **raw spec**(현행 v1.4) 을 먼저 적용해 두는 자리다.

## 파일 구성

| 파일 | 정체 |
|---|---|
| [`README_labtest.md`](README_labtest.md) | ⭐ **실험실 취득 스크립트에 관한 모든 것** — 돌리기 전에 손볼 자리 · 첫 실행 점검 · 경고의 뜻 · 변경 내역 · 판 이력 |
| [`archon_kmtnet_labtest_v1.1.bigbuf.py`](archon_kmtnet_labtest_v1.1.bigbuf.py) | ✅ **현행 실험실 취득 스크립트** (`v1.1.1`, science 유닛) |
| [`archon_kmtnet_labtest_v1.0.smallbuf.py`](archon_kmtnet_labtest_v1.0.smallbuf.py) | **guide 유닛용 참고 사본** — 원본 그대로, 미개정 |
| [`tests/verify_labtest_v11.py`](tests/verify_labtest_v11.py) | **실기 없이 돌리는 검증** (19항목) — `python tests/verify_labtest_v11.py` |
| [`SMC_CLAUDE.md`](SMC_CLAUDE.md) | **인수인계** — 상태 · 브랜치 · 절대 깨뜨리면 안 되는 것 · Archon 매뉴얼 확정 사실 |
| `__ref_archon_control/` | **읽기 전용 참조** — v1.0 원본 2부 + STA Archon 매뉴얼(2021-02-23) + ZTF Readout Notes(2014-10-30) |

`__` 접두 폴더는 읽기 전용이다 — 편집이 필요하면 이 루트로 사본을 떠서
작업한다(운영자 규칙 2026-08-22). v1.1 이 바로 그 사본이고, v1.0 원본은
`__ref_archon_control/` 에 남아 있어 이력이 보존된다.

> **용량 메모** (2026-08-22 실측): `__ref_archon_control/` 의 PDF 2부(4.1 MB)는
> 저장소에 **각각 한 부뿐이다** — `cam_char/archon/` 을 포함해 다른 사본이 없다.
> 중복인 것은 v1.0 스크립트 2개(루트 사본)뿐이고 합쳐 100 KB 다.  저장소 전체
> 중복은 **21.3 MiB / 608 그룹**이고 그중 **20.5 MiB 가 `ics_legacy/`**(3사이트
> DTS 백업이 같은 파일을 3~9벌 보유) 다 — 나중에 용량을 확보할 때 볼 곳은
> 거기다.  `raw_fits_spec/__reference/` 가 PDF 포함 46개를 추적하는 선례가
> 있어 참조 자료를 저장소에 두는 것 자체는 이 저장소의 관례다.

## 실험실 취득 스크립트 — 핵심 참고사항

세부는 전부 **[README_labtest.md](README_labtest.md)** 에 있다. 여기서는
폴더를 처음 보는 사람이 알아야 할 것만 적는다.

- **현행은 `v1.1.1`** (science 유닛, BIGBUF=1). v1.0 원본은 **실제로 돌려서 쓰던
  검증된 코드**이고, v1.1 은 그 위에 raw spec 을 얹은 개정판이다.
- **컨트롤러와의 왕복에서 v1.1 이 추가한 명령은 `STATUS` 하나뿐**이다. 그래서
  `TELEMETRY_ENABLE = False` 로 두면 왕복이 v1.0 과 완전히 같아진다 — 실기에서
  문제가 보일 때 원인을 가르는 첫 수단이다.
- **실기로는 한 번도 돌리지 않았다.** 헤더·파일명·검증 하네스는 통과했지만
  POWERON → FETCH 왕복은 미검증이다.
- **산출물 규격이 통째로 바뀌었다** — 파일명 `<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits`,
  헤더 144카드(견본 바이트 재현), 날짜는 UTC. **기존 분석 스크립트는 glob
  패턴과 카드명을 갱신해야 한다.**
- **같은 UT 날짜의 재실행은 멱등하지 않다** (D-016 이 번호를 밀어 올린다 —
  v1.0 은 덮어썼다). 날짜가 다르면 영향 없다.
- **첫 실기 실행은 1프레임 연막시험으로.** 활성 실행 블록 그대로면 63프레임 /
  21.18 GiB 다.
- **헤더에 들어가는 손편집 문자열은 ASCII 전용**이다. 한글 한 자로 FITS 가
  통째로 깨지므로 기동에서 거부한다.
- **guide 유닛은 미개정** — guide raw 규격이 아직 없어서다.

## ics_archon 본편으로 갈 때

- 시퀀서·명령 처리·메시지 규약·헤더 값 층은 `ics_sim/` 이 이미 갖고 있다 —
  `ics_sim/ics_sim/hardware/archon.py` 스텁에 이 스크립트의 제어 시퀀스
  (CLEARCONFIG→WCONFIG→APPLYALL, POWERON, LOADPARAMS, FRAME 폴링, FETCH)를
  옮기면 된다. 헤더 틀은 `ics_sim/ics_sim/rawcards.py`(기계 사본)를 그대로 쓴다.
- 백엔드 계약(D-012): `controller_info()`/`controller_telemetry()`/`sensors()`
  — 이 스크립트의 `archon_status()`/`ctrl_telemetry_cards()` 가 그 원형이다.
- guide 유닛은 smallbuf 구성 + `DATASRC='ARCHON_GUIDE'`, `CTRL1xx` 한 벌 규약
  (raw spec 5.5절) — guide raw 규격 확정 후 착수.
- **두 대분 텔레메트리 합치기**가 본편 몫이다. 실험실은 한 대만 돌리므로
  `Cn_*` 한 벌이 `'NC'` 로 남아 있다 (5.9절은 양쪽 파일에 같은 값을 요구한다).

## 관련 문서

| 문서 | 위치 |
|---|---|
| 경위·판단 (왜 그렇게 정했나) | [`../ics_sim/DevNote.md`](../ics_sim/DevNote.md) 11.19~11.22 |
| 산출 규격 (raw FITS pair) | [`../raw_fits_spec/`](../raw_fits_spec/README.md) |
| 헤더 카드 템플릿 (공유 원천) | `../ics_sim/ics_sim/rawcards.py` |
| 백엔드 계약 | `../ics_sim/ics_sim/hardware/base.py` (D-012) |
| L0 MEF ICD · converter | `../mef_fits_spec/` · `../mef_converter/` |

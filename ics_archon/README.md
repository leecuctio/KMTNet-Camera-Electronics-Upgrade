# ics_archon — Archon 컨트롤러 제어 (준비 단계)

**최종 목표**: `ics_sim/`(시퀀서·메시지 규약·헤더 층)과 이 폴더의 Archon 제어
코드를 합쳐 실기 ICS(`ics_archon`)를 만든다.  지금은 그 전 단계 — 실험실
취득 스크립트에 **raw spec**(현행 v1.4) 을 먼저 적용해 두는 자리다.

## 파일 구성

| 파일 | 정체 |
|---|---|
| [`archon_kmtnet_labtest_v1.1.bigbuf.py`](archon_kmtnet_labtest_v1.1.bigbuf.py) | ✅ **현행 실험실 취득 스크립트** — v1.0.bigbuf 에 raw spec 을 적용한 판. **science 유닛용** (BIGBUF=1, 768MB 버퍼 2개 구성) |
| [`archon_kmtnet_labtest_v1.0.smallbuf.py`](archon_kmtnet_labtest_v1.0.smallbuf.py) | **guide 유닛용 참고 사본** (512MB 버퍼 3개 구성) — 원본 그대로, 미개정. guide raw 규격이 아직 없어 spec 적용 대상이 아니다 |
| `__ref_archon_control/` | **읽기 전용 참조** — v1.0 원본 2부 + STA Archon 매뉴얼(2021-02-23) + ZTF Readout Notes(2014-10-30) |

> **용량 메모** (2026-08-22 실측): `__ref_archon_control/` 의 PDF 2부(4.1 MB)는
> 저장소에 **각각 한 부뿐이다** — `cam_char/archon/` 을 포함해 다른 사본이 없다.
> 중복인 것은 v1.0 스크립트 2개(루트 사본)뿐이고 합쳐 100 KB 다.  저장소 전체
> 중복은 **21.3 MiB / 608 그룹**이고 그중 **20.5 MiB 가 `ics_legacy/`**(3사이트
> DTS 백업이 같은 파일을 3~9벌 보유) 다 — 나중에 용량을 확보할 때 볼 곳은
> 거기다.  `raw_fits_spec/__reference/` 가 PDF 포함 46개를 추적하는 선례가
> 있어 참조 자료를 저장소에 두는 것 자체는 이 저장소의 관례다.

`__` 접두 폴더는 읽기 전용이다 — 편집이 필요하면 이 루트로 사본을 떠서
작업한다(운영자 규칙 2026-08-22). v1.1 이 바로 그 사본이고, v1.0 원본은
`__ref_archon_control/` 에 남아 있어 이력이 보존된다.

## v1.1 에서 바뀐 것 (raw spec 적용, 2026-08-22)

정본: [`../raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.4.md`](../raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.4.md)

1. **파일명** — `AC13A.<날짜>.<번호>.fits` → **`<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits`**
   (D-011). 실험실은 `SITE_CODE='KMTT'`(테스트베드), 날짜는 UT(KMTT 보정 0,
   D-014), 번호는 기존 DS 체계(6자리 `[Unit][Setup][Type][SN]`) 유지 —
   converter 정규식(`\d{6}`)에 그대로 걸린다.
2. **이름 충돌 = 번호 증가** (D-016) — 쓰기 전에 후보 번호의 MK·NT 두 경로를
   선검사하고 점유 시 +1. 카운터(DS 체계) 최초 배정명은 `ORIGNAME` 카드로
   남는다 — 충돌 신호 = `FILENAME ≠ ORIGNAME`.
3. **헤더 전면 교체** — 구 12카드 → **견본 초안 v1.0 pair 의 144카드**
   (값 135 + COMMENT 8 + END = 정확히 2880B×4블록). 카드 순서·comment·문자열
   패딩까지 견본과 **바이트 단위 동일** (검증: 견본 값을 넣으면 견본이 그대로
   재현된다 — 불일치 0). 실험실에서 모르는 값(TCS/AUX/듀어 HK)은 규격 5.0절
   sentinel (`'NC'`/`-1`/`'-999.99'`/`'9.99e-9'`).
4. **Archon STATUS 텔레메트리** — `Cn_TEMP`(BACKPLANE_TEMP + AD 모듈 온도),
   `Cn_VOLT`/`Cn_CURR`(전원 레일 P2V5 P5V P6V N6V P17V N17V P35V) — 매뉴얼
   p.47–49. **색인 `n` 은 `UNIT_CTRLTAG` 가 정한다**(MK→1 / NT→2, 5.9절) —
   `C1_*` 는 "내 컨트롤러"가 아니라 컨트롤러 1 고정이다. 실험실은 한 대만
   돌리므로 나머지 한 벌은 `'NC'` 이고, 두 대분 합치기는 본편 몫이다.
5. **`IMAGETYP` 유도** — 0초=`BIAS` / 트리거 없음=`DARK` / 트리거(LED) 노출=`FLAT`.
   `LEDFLASH` 는 트리거 노출이면 노출시간[ms] (실험실 광원이 트리거 라인으로
   노출 내내 켜지므로). `OBJECT`=`DS<번호>` 로 데이터셋 정체를 남긴다.
6. **`DATE-OBS`** — 노출 지시(LOADPARAMS) 시점의 **UTC, 밀리초까지**
   (구판은 Local 날짜/시각 2카드). `TIME-OBS` 폐지.
7. **데이터부 2880B 패딩** (규격 3장) — v1.0 은 마지막 블록이 잘려 있었다.
8. `CTRL1CFG` = 적용한 ACF 파일명, `RDMODE` = ACF 속도 토큰(FAST/COMP/SLOW),
   `ICSBUILD` = `v<버전>:<빌드일시>Z`, `DATASRC='ARCHON_SCIENCE'`.

유닛별로 손대는 자리는 스크립트 머리의 `<---- Set this` 표시 —
`UNIT_*`(주소·라벨)와 **`UNIT_CTRLTAG`(MK/NT)·`UNIT_CTRL_ID`·`UNIT_CTRL_SN`**
(raw spec identity, `__reference/Archon_Unit_Info.txt` 참조).

## ics_archon 본편으로 갈 때

- 시퀀서·명령 처리·메시지 규약·헤더 값 층은 `ics_sim/` 이 이미 갖고 있다 —
  `ics_sim/ics_sim/hardware/archon.py` 스텁에 이 스크립트의 제어 시퀀스
  (CLEARCONFIG→WCONFIG→APPLYALL, POWERON, LOADPARAMS, FRAME 폴링, FETCH)를
  옮기면 된다. 헤더 틀은 `ics_sim/ics_sim/rawcards.py`(기계 사본)를 그대로 쓴다.
- 백엔드 계약(D-012): `controller_info()`/`controller_telemetry()`/`sensors()`
  — 이 스크립트의 `archon_status()`/`ctrl_telemetry_cards()` 가 그 원형이다.
- guide 유닛은 smallbuf 구성(v1.0.smallbuf 참조) + `DATASRC='ARCHON_GUIDE'`,
  `CTRL1xx` 한 벌 규약 (raw spec 5.5절) — guide raw 규격 확정 후 착수.

## v1.1 적대적 검토 반영 (2026-08-22, 같은 날)

v1.1 을 만든 뒤 스크립트를 원본과 대조 검토해 **6건을 고쳤다** (전부 v1.1 에서
새로 들어온 결함이다 — v1.0 의 `SetHeader` 는 순수 문자열 포맷이라 실패 경로가
없었다). 경위는 `../ics_sim/DevNote.md` **11.20**.

| 무엇이 문제였나 | 어떻게 고쳤나 |
|---|---|
| `fits_card` 가 폭 초과 문자열을 클램프하지 않아 80바이트에서 통째로 절단 — **닫는 인용부호·comment 가 사라져** astropy·converter 가 파싱 불가 (온도 13슬롯이면 실제로 그렇게 된다). `build_header` 의 `% 2880` 단언은 원리상 이걸 못 잡는다 | 들어갈 자리를 계산해 잘라내고 **경고**한다 |
| 텔레메트리 나열이 결측 항목을 **건너뛰어** "자리 = 항목"(5.6절)을 조용히 깼다 — MOD3 결측이면 MOD4 값이 MOD3 자리에 앉고, volt/curr 항목 수가 서로 달라질 수 있었다 | 자리마다 sentinel. 슬롯 목록을 `TEMP_SLOTS` 상수로 (BACKPLANE + AD 모듈 4장 — **모듈 순서 정본은 규격 수록 예정**이라 그때 교체) |
| 프레임 fetch 후·쓰기 전 미처리 예외 2종 — STATUS 의 비수치 토큰 하나, `UNIT_CTRLTAG` 오타(KeyError). **이미 읽어낸 노출이 통째로 버려졌다** | `status_number()` 가 sentinel + 경고로 흡수 · `_check_identity_setup()` 이 기동 시점 1회 검증 |
| `CTRL1*`/`C1_*` 에 자기 유닛 값을 넣어 5.9절 위반 — `C1_*` 는 "내 컨트롤러"가 아니라 **컨트롤러 1 고정**이다 | `UNIT_CTRLTAG` 가 색인 자리를 정한다 (NT 유닛이면 `CTRL2*`/`C2_*`) |
| `SITE_CODE` 를 주석 지시대로 관측소 코드로 바꾸면 `OBSERVAT` 가 `TESTBED` 로 남아 **규격의 유일한 하드 실패** | `SITE_INFO` 표에서 `OBSERVAT`/`ORIGIN`/`TELESCOP` 유도 |
| `OBJECT` 가 `filenum // 100` 역산을 써서 iFlat(116 프레임)의 `nframe >= 100` 구간에서 `DS<번호+1>` | 죽은 `prefix` 인자를 `datasetid` 로 교체 — 호출측이 넘긴다 |

수정 후에도 **견본 바이트 재현(144카드, 불일치 0)** 은 그대로다.

> **규격 판 참조**: v1.1 은 raw spec **v1.3** 기준으로 작성했고, 같은 날 발행된
> **v1.4** 는 1~4장의 표현만 바뀌어 이 스크립트의 동작에 영향이 없다 — 2.5절
> 삭제(`Wrote` 통보는 취득 SW 소관이라 규격에서 빠졌다), 4.1 `RRRRLLLL` 확정
> (OI-15 종결), 4.2/4.4 표기 정합. **5장 이후(헤더 카드)는 아직 검토 전**이므로
> 견본 144카드 기준은 그대로다.

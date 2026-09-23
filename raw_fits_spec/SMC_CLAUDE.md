# SMC_CLAUDE.md

`raw_fits_spec/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md), 이 폴더의 구성은 [README.md](README.md) 참고.

> ⚠️ **`../ics_archon/` 은 `main` 에 아직 없다.**  실기 ICS 는
> **`ics-archon-v1.0-build` 브랜치에서 진행 중**이고 **추후 `main` 합류 예정**
> 이다.  이 문서가 `../ics_archon/…` 을 가리키는 링크는 `main` 에서 열리지
> 않지만 **그 브랜치에서는 열린다** — 끊긴 것이 아니라 아직 안 온 것이다.

## 이 폴더가 뭔가

**Archon controller 가 직접 저장하는 raw FITS pair 의 규격을 관리한다.** `mef_fits_spec/` 이 출력(L0 MEF) 규격이라면 여기는 입력(Archon raw) 규격이다.

## ✅ 현행 규격 — raw spec **v1.14** (2026-09-23 판올림)

> ▶ **이어서 시작하는 자리는 이 절이다.**
> ⭐ **v1.14 는 `EQUINOX` 를 실수형으로 바꾸고**(운영자 확정 2026-09-23 — `EQUINOX = 2000.0`, 결측·비수치는 실수 sentinel `-999.0`, 5.7절 · 견본 6장은 이 카드 하나만 바뀌었고 크기·레코드 수는 그대로다), **같은 판에서 2026-09-23 전반 재검토의 발견 133건(반증을 통과한 것)을 다뤘다** — 대부분 반영했고, 규범을 그대로 두기로 한 것과 범위 밖으로 둔 제안 9건은 아래 「운영자 판단 대기」 표에 남는다(운영자 확정 2026-09-23).
>
> **문서별 한 줄**:
>
> - **규격 v1.14** — science HK 원천을 `GO` 마다 `HKDATA NOW` 로(5.6절) · KASI 관측일을 KST 날짜로(2.2절) · guide ~~OI-24~~ 종결(`BIAS` = 최소 노출 · 기동 `EXPTIME` 2 s) · converter v2.5.0 재대조(6장 — 카드 값 하드 실패 둘 · 경고 층 · D-023 WCS 행) · 운영자 결정 일곱(아래 4 ~ 10 — guide `TRIGOUT` 판정 창은 2026-09-24 에 노출 창 ± g(`[icg] trigout_guard`, 기본 0.15 s)로 좁혔다, 결정 5 개정 · 10.3절) · 표 렌더 결함 둘과 사실 정정.  전량은 12장 v1.14 행 ①~⑦.
> - **원장 v1.20** (구판 `archive/…v1.19.md`) — converter v2.5.0 이 raw 에서 읽는 카드(새로 47장 · 더는 안 읽는 둘) · geometry 선언 대조 · 카드 값 하드 실패 둘을 여러 장에 반영하고, 운영자 결정 셋(4장 `DATE-OBS` · 3.3절 `CTRLnID`/`CTRLnSN` · 7장 `CHECKSUM`/`DATASUM`)을 옮겼다.  `Raw Archon`·도입 여부 판정은 그대로다.
> - **통합 v1.0** (구판 `archive/…v0.10.md`) — 판 번호를 v0.11 대신 **v1.0** 으로 올리고 *(Draft)* 를 뗐다(운영자 2026-09-23).  §1 을 v2.5.0 과 다시 맞췄고(✅ C-11 · C-17 · C-18 · C-5/C-13 — 단 멈추지 않고 경고만 · ⚠️ C-12 는 커밋 제목에 올랐지만 코드가 그대로) §1.2(기존 C-항목 현황)와 기록 행 다섯을 새로 두었다.  ⭐ **§7 「MEF converter 및 PIPELINE 판단 필요 항목」** 이 MEF 쪽이 골라야 할 아홉(LEECU 여덟 · PIPELINE 하나 7-5 — 반쪽 pair 의 성한 절반 보관 — D-001 과 맞물린다 · raw 가 공급하지 않는 MEF 카드의 처분 · 멈춤 기준 · §6 미결 셋 등)을 모은다.  **LEECU 전달분 = 통합 Part 1** — 판단은 §7, 나머지 절은 수정 요청이다.
> - **README** — 판 표 · 연동 기준 · 열린 항목(~~OI-7~~ · ~~OI-24~~ 종결) · 국문 ICD 미반영 절 목록을 현행으로.  **DECISION_LOG** — D-017 4항 개정(결정 1) · D-013 · D-014(결정 4 의 `DATE-OBS` 시점 포함) · D-017 개정 표시.
>
> ⭐ **LEECU 판올림 반영** — ICD **v4.3** · Keywords **v1.1** · converter **v2.5.0**(파일명 접미사 `_v2_1` 은 그대로이고 판은 `SOFTWARE_VERSION` 이 말한다) · **D-023**(L0 sky WCS = L1 Gaia 측성의 seed).  구 ICD v4.2 · Keywords v1.0 은 `../mef_fits_spec/archive/` 로 갔다.
>
> ⭐ **운영자 결정** (이 라운드):
>
> 1. **KASI(`KMTK`) 관측일 보정 +9 h** — 경계 UT 15:00 = KST 00:00, 관측일은 KST 날짜다(운영자 2026-09-12 · **D-017 4항 개정**).  이 규칙이 없는 코드(브랜치 `982ebe5`(2026-09-13) 이전 · 합류 전 `main` 의 `ics_sim`)로 찍은 KASI 파일은 보정 0(UT 날짜)이다.
> 2. **5.0절 금지 열 장은 근거 문장만 고쳤다** — converter v2.5.0 은 거부하지 않는다(`EXPTIME`·`DATE-OBS` 는 기본값 0·변환 시각으로 채우고, geometry 여덟은 선언이 있을 때만 대조해 어긋나면 경고·`HISTORY`).  비운 결함은 7장 체크리스트 3·8번이 드러낸다.  C-항목은 올리지 않았다.
> 3. **통합 문서 v1.0** — *(Draft)* 를 떼고 §7 을 두었다(위).
> 4. **`DATE-OBS` = 모든 영상(`DARK`·`BIAS` 포함)의 적분 개시 시각** — 셔터 노출은 ICS 가 셔터 개방을 지시한 시각, 셔터 없는 노출은 컨트롤러에 적분을 건 시각, guide 는 10.1절이다(5.4절 · 5.7.1절 (c)).
> 5. **guide `TRIGOUT` 판정 창 = `[DATE-OBS − g, t_next + g]`** (운영자 2026-09-24 — 2026-09-23 의 *"창 `[DATE-OBS, 독출 완료]` 의 겹침은 의도다"* 를 고친다 · 10.3절).  `t_next` 는 이 프레임의 트랜스퍼(FrameShift) 개시 = 다음 저장 장의 `DATE-OBS`(≈ `DATE-OBS + EXPTIME`)이고, 호스트는 `t_next` 를 이 프레임의 완료 관측에서 셈한다 — 다음 프레임을 기다리지 않는다.  즉 창의 뼈대는 **그 프레임의 노출 창**이다.  **g 는 호스트 시각 불확도 여유 — ICG INI `[icg] trigout_guard`, 기본 0.15 s**(권장 0.10 ~ 0.15 s)다.  호스트는 펄스 에지를 `APPLYSYSTEM` 응답 뒤에 적어 실제보다 0 ~ ≈0.24 s 늦게, 프레임 경계는 완료 폴링 지연으로 0 ~ ≈0.21 s 늦게 안다(브랜치 `ics_archon/DevNote.md` 11.55) — 최소 펄스 폭(≈235 ms — 코드 유도, 벤치 미확인)과 같은 크기라 여유 없이 좁히면 경계 근처 `0` 이 단언이 못 된다.  이웃 창은 **2g 만큼만** 겹친다 — 경계 ±g 안의 펄스는 이웃한 두 장에 `1` 로 찍힐 수 있다(의도, 이웃 장 거짓 `1` ≈ 2g/`EXPTIME`).  종전 창의 자기 독출 1.25 s 겹침(이웃 장 거짓 `1` ≈ 1.25 s/`EXPTIME`, 최소 노출 근처에서는 세 장까지)은 없어졌다.  창이 넓었던 출처는 v1.13 의 사실 오류(*"적분은 이 독출로 끝난다"* — 10.1-5 와 모순)였고 09-09 원래 뜻은 *"노출 창"* 이다 — 그래서 G 견본 comment `Trigger Out asserted during exposure (1=yes)` 는 **그대로 맞다**(견본·템플릿 불변).  ⚠️ 남는 한계 넷: ① 에지·경계 지연 차이가 g 를 넘는 드문 경우 경계 근처 거짓 `0` ② LED 가 image 를 포화시켜 독출 중 store 로 번진 빛은 그 프레임에 `1` 로 안 잡힌다(ABD 없음, 10.1-2(a)) ③ 마지막 저장 장의 `t_next + g` 뒤에 친 펄스는 어느 파일에도 안 남는다(저장 안 된 장을 비췄으므로 물리적으로 맞다) ④ 이진 플래그라 얼마나 비췄는지는 말하지 않는다.  `trigout_guard` 키는 아직 코드에 없다 — 규격이 먼저 섰고 코드가 따라온다(아래 「브랜치 후속」 — g 축소 조건도 거기).  science 에는 TRIG 계열 카드가 없다.
> 6. **`CTRLnID`·`CTRLnSN` 은 INI 에 값이 없으면 `'NC'`** — Archon `SYSTEM` 값(펌웨어 문자열 · 16진 `BACKPLANE_ID`)으로 대신 채우지 않는다(5.5절 · 10.3절).
> 7. **`CHECKSUM`·`DATASUM` 은 raw 미도입 확정** — ~~OI-7~~ 종결, 5.10절 폐지·미도입 목록 등재(원장 7장 `X` 와 같다).  MEF 의 같은 이름 카드는 converter 가 HDU 마다 쓰는 별개의 것이고 변환 뒤의 바이트만 보증한다.
> 8. **`RDMODE` 결측도 `'NC'` 로 통일** (운영자 2026-09-24) — 2026-08-29 의 `'UNKNOWN'` 을 뒤집는다.  같은 처지(INI 전용 값이 비었다)인 결정 6 과 표기를 맞췄고, *"`NORMAL` 로 가리지 않는다"* 는 원래 목적은 `'NC'` 로도 지켜진다.  `'UNKNOWN'` 은 중계값 `SHUTTER` 에만 남는다(5.0절 표 · 5.5절 · 7장 8번 · 10.3절).  ⚠️ 2026-09-06 에도 같은 기억(*"NC 로 통일하기로 했었다"*)이 나왔는데 그때는 기록이 `UNKNOWN` 뿐이라 `UNKNOWN` 으로 등재됐다 — 이번이 **처음으로 `NC` 를 고른 결정**이다.
> 9. **돔 방위 셋 `DSAZ`·`DSTELAZ`·`DAZERR` 은 소수 3자리** (운영자 2026-09-24 — redis 도 `%.3f`, `DAZERR` 는 부호 포함) — 5.7.3절 (g).  브랜치 11.94-h 의 소수 2자리를 대체한다.  견본 6장의 세 카드도 `'12.300'`·`'12.100'`·`'+0.200'` 으로 맞췄다(값·폭 불변).
> 10. **`HKDATA NOW` 는 Radionode 를 치지 않는다** (운영자 2026-09-24) — 폴러의 표본을 싣고 클라우드는 INI 주기 폴링만 친다(5.6절).  2026-09-09 브랜치 DevNote 11.56 의 *"`now_min_age`(60 s)보다 낡았으면 `NOW` 가 한 번 친다"* 를 뒤집는다 — 11.52 (3) 의 *"즉시 조회해도 더 신선해지지 않는다"* 가 `NOW` 에도 맞기 때문이다.  시한은 **둘 다 그대로** — ICS `[archon] hk_query_timeout` **2 s** · ICG `[radionode] timeout` **5 s**(운영자 2026-09-24).  NOW 가 클라우드를 안 치면 Radionode 시한은 백그라운드 폴러와 종료 지연(≤5 s)에만 걸리고, 줄이면 느린 날 주기 조회 실패만 는다.  ⚠️ 이번에도 운영자 기억(*"NOW 에서는 안 치기로 했었다"*)과 기록(11.56)이 어긋났다 — 이 결정이 **처음으로** NOW 에서 Radionode 를 뺐다.
>
> ✅ 태그 — `raw-spec-v1.13`(`ae3fbfe`)을 로컬·원격에서 지우고 **`raw-spec-v1.14`** 를 이 판의 마지막 커밋에 붙였다(2026-09-24 — 운영자가 *"최신 판에만"* 규칙 유지를 확정).  팀은 `main` 을 pull 하면 새 태그를 받는다.  지운 옛 태그까지 pull 로 정리되게 하려면 각자 **한 번만** `git config fetch.prune true` · `git config fetch.pruneTags true` 를 해 둔다(아래 태그 규칙 절 팀 알림 2026-09-24).

### ⏳ 브랜치 후속 (`ics-archon-v1.0-build`)

- ✅ **(구) v1.13 후속은 끝났다** — `bfc4ea6` · `cbffe40`(2026-09-12)이 아래 (구) v1.13 절의 일감을 처리했고, 합류(`5543234`) 뒤 전수가 통과했다(`ics_archon` 716 · `ics_sim` 425).
- ⛔ **선결 — `EQUINOX` 실수형 구현이 아직 미커밋이다.**  `telemetry._as_real` · `rawcards`/`guidecards` 의 `'R'` · DevNote **11.95** 는 작업본에만 있고 HEAD `32b002d` 에는 없다.  규격 5.7절 표 아래 구현 요약과 12장 v1.14 행 ① 이 그것을 인용하므로 **`main` 에 v1.14 를 커밋하기 전에 브랜치 커밋이 먼저**다.
- **`EQUINOX` 후속** — 규격이 따라잡은 뒤 할 것(DevNote 11.95 *"규격이 따라잡을 때 할 것"*, 작업본 기준): 두 `SPEC_PENDING` 비우기 · `ics_sim/tests/test_raw_draft.py` 의 `_ahead_of_sample()` 에서 **`EQUINOX` 만** 지우기(`DAZERR` 는 돔 방위 2자리가 규격 미반영이라 남는다 — 아래) · `test_icg_cards.test_only_equinox_runs_ahead_of_the_sample` 을 `== ()` 로 · `tools/gen_guidecards.py` 의 `SAMPLE` 을 `…G.fits.header.v1.14.txt` 로 올리고 재실행(지금은 `v1.13` 을 박아 두었다 — ⚠️ 합류 전 v1.13 견본으로 돌리면 guide `EQUINOX` 가 `'S'` 로 돌아간다) · labtest 다섯 사본의 `RAWCARDS` 와 TCS 결측값(`'NC'` → `-999.0`).
  ⚠️ **합류하면 빨개지는 시험이 둘이다** — `test_icg_cards.test_template_matches_the_sample_generator`(`gen_guidecards.SAMPLE` 이 박아 둔 v1.13 견본이 v1.14 로 개명돼 없어서 도구가 `SystemExit` 로 멈춘다) · `test_raw_draft.test_the_sample_has_not_caught_up_yet`(MK·NT — 견본이 따라잡았다고 알리는 **의도된 신호**).  위 일감을 처리하면 둘 다 걷힌다.  나머지 바이트 대사는 초록일 것이다(`_ahead_of_sample()` 이 견본 값으로 현행 이미지를 만든다) — 합류 뒤 전수로 확인한다(`main` 에는 견본 대사 시험이 없다).
- ⭐ **별도 세션 몫 — 코드 검토·보완** (운영자 2026-09-23 — 규격 규범은 그대로다):
  - **science `DARK` 의 적분 트리거를 `DATE-OBS` 시점으로** (결정 4) — 지금 `archon/backend.py` `begin_exposure()` 는 적분 초만 받아 두고, 트리거(`IntMS=0` · `NoIntMS`=적분시간)는 READOUT 국면의 `_readout_stream()` 이 건다.  그래서 `DATE-OBS` 가 실적분 개시보다 약 `EXPTIME` 앞선다.  트리거를 `begin_exposure()` 로 옮기고 호스트 카운트다운은 통보만 하게 하되, `_readout_stream()` 의 `pending` 판정과 컨트롤러 쪽 `dwell_until` 시한을 함께 본다.
  - **guide `STOP` 거동** — 규격 5.4.1-1 · 10.1-7 은 *"노출 중이던 프레임을 저장한 뒤 멈춘다 · 최악 한 주기"* 인데, 코드는 지금 장을 저장한 뒤에야 `Exposures=0` 을 보내 꼬리 한 장을 독출·폐기하고 조용함을 한 주기 더 확인한다(최악 약 3주기).
  - **돔 방위 셋 소수 3자리** (결정 9) — `ics_sim/ics_sim/domeaz.py` `_read_once` 의 `DSAZ`/`DSTELAZ` `%.2f` → `%.3f` · `DAZERR` `%+.2f` → `%+.3f` · 계산 갈래 `telemetry._sync_error_az` `%+.2f` → `%+.3f` · 그 값을 단언하는 시험(`test_raw_draft` 의 `test_dalterr_…` · `test_dome_wiring`) · `test_raw_draft._AHEAD_OF_SAMPLE` 의 `DAZERR` 항목은 **지운다**(견본이 `'+0.200'` 으로 따라왔다 — `DSAZ`·`DSTELAZ` 는 `dome source = off` 로 견본 값 `'12.300'`·`'12.100'` 을 그대로 되먹인다) · `_sync_error_az` docstring 의 *"소수 1자리"*.
  - **`RDMODE` INI 부재 = `'NC'`** (결정 8) — `ics_sim/ics_sim/rawhdr.py` `RDMODE = 'UNKNOWN'` → `'NC'` · 그것을 단언하는 시험 둘(`ics_sim/tests/test_raw_header.py` · `ics_archon/tests/test_ini_cards.py`) · `icg_archon/backend.py` 의 `rdmode` 두 자리 docstring · `ics_archon/ics_archon/app.py`·`config.py`·`ics_sim/ics_sim/config.py` 주석 · 배포 ini 두 벌의 `rdmode` 주석 · labtest 다섯의 `rdmode = 'UNKNOWN'` · `tools/sync_vendor.py` 재동기.
  - **`CTRLnID`·`CTRLnSN` INI 부재 = `'NC'`** (결정 6) — INI 가 비면 science `archon/backend.py` `controller_info()` 는 `parse.unit_identity()` 의 `SYSTEM` 값으로, guide `icg_archon/backend.py` `controller_info()` 는 같은 값으로(`SYSTEM` 을 못 읽었으면 빈 문자열로) 채운다.  `ics_archon.ini` 주석 *"비우면 … 파생한다 (규격 5.5절)"* 은 `CTRLnCFG` 에만 맞다.  (와이어 `CnHKDATA` 답의 `CTRLnID=<BACKPLANE_ID>` — `app.py` · `commands.py` → `hkwire.py` — 는 헤더 경로가 아니다.)
- **이 라운드 편집자들이 넘긴 것** (겹친 것은 하나로):
  - guide `HKUDATE` 셈에 카드가 아닌 `'gauge'` 표본이 낀다 — `icg_archon/hk.py` `sensors()` 가 Radionode 키만 빼고 셈해서, 카드가 전부 sentinel 이어도 `HKUDATE` 가 *"방금"* 으로 실린다(`HKDATA` 를 거쳐 science 헤더에도 간다).  같은 파일 `_read_heater_settings` docstring 도 코드·규격과 반대다.
  - science `OBSERVER` 기본값이 `'none'` 이다(`ics_sim/ics_sim/state.py`) — 규격 5.3절의 `'KMTNetOp'` · 자리채움 낱말 금지와 어긋난다.
  - 낡은 코드 문면 — `telemetry.py` 의 `DATE-OBS` 빈 값 로그 detail *"converter 가 이 노출을 거부하게 한다"*(결정 2 와 반대 — converter 는 변환 시각으로 채운다) · 같은 파일의 *"`TCS relay or REDIS`"*(v1.13 에서 걷힌 어휘)와 *"규격 5.7절이 원래 정한 `ICS calculation`"*(지금 자리는 5.7.3절 (d)) · `rawhdr.py` 의 *"규격 5.4절의 … 는 낡았다 -- 갱신은 `main` 소관"*(`OBSTYPE` 어휘 — v1.13 이 이미 고쳤다) · `tcsclock.py` 의 폴백 `TCSQDATE` 이유 문장(폴백은 직전 실응답의 보존본이다) · 머리말 판 표기(아래 「판올림 규약」 절).
  - **guide `TRIGOUT` 판정 창을 `[DATE-OBS − g, t_next + g]` 로** (결정 5 개정, 운영자 2026-09-24 — 종전 항목 *"창의 끝이 규격의 독출 완료와 같은 순간인지 확인"* 을 이것으로 대체한다).  ⛔ 순서: 다른 세션의 미커밋 편집(`sequencer.py` · `controller.py` · `test_icg_cards.py`)이 커밋된 뒤.  줄 번호는 작업본 기준이다.
    - `icg_archon/sequencer.py` — `t_next = done_utc − fs_to_done` 을 `_dispatch_store` 호출(414) 앞에서 셈해 넘기고, 그것을 창 끝으로 써서 `[DATE-OBS − g, t_next + g]` 로 판정한다(지금은 `now = time.time()`(909) 으로 닫아 창이 자기 독출 ≈1.25 s 를 품는다).  418 의 `t_prev` 갱신은 같은 `t_next` 값을 다시 쓴다 — k 의 창 끝과 k+1 의 창 시작(`DATE-OBS`)이 한 변수라 이웃 창의 뼈대가 틈 없이 이어진다.  주석 *"창은 `[DATE-OBS, 지금]` 이다"* · *"이 독출로 끝난다"*(894-896 — 10.1-5 와 모순) 정정.  타지 않는 `t_prev is None` 갈래(910-911 — `t_prev` 는 arm 에서 늘 선다, 331-336)는 정리하거나 `t_next − exptime` 으로 바꾸고, 그 주석(897-898 *"`t_prev` 가 없으면(첫 프레임) 노출시간만큼 되짚는다"*)도 정정 — 남겨 두면 시작은 `now`, 끝은 `t_next` 기준이 되어 어긋난다.
    - `icg_archon/config.py` `IcgCfg.trigout_guard`(초, 기본 0.15 s) + 로더 + `icg_archon.ini` `[icg]` 절에 한 줄.  ⚠️ 설정 객체가 **둘**(`cfg`/`icfg`)인 함정.
    - `tests/test_icg_cards.py:394-395` — 시퀀서 원문을 리터럴 `trigger_was_high_between(start, now)` 로 잘라 보므로 변수 이름을 바꾸면 `ValueError` 로 빨개진다 — 같은 커밋에서 대조를 고친다.
    - 창 위치 시험 3~4건 신설 — `fs_to_done≠0` 대역에 `_trig_spans` 를 epoch 로 심어: 독출 중 펄스는 k 에 `0` · k+1 에 `1` / 경계 ±g 에 걸친 펄스는 둘 다 `1` / 마지막 장 `t_next + g` 뒤 펄스는 어느 파일도 `1` 아님 / 타이밍 모델이 없을 때(`fs_to_done=0`)의 동작(기대값은 아래 「운영자 판단 대기」 표의 `fs_to_done=0` 행 판단 뒤).
    - 낡은 문면 — `ics_archon/archon/controller.py:1741` 주석 *"선이 실제로 바뀌는 시점이 여기다"*(11.55-(6) 과 어긋난다 — 핀은 `APPLYSYSTEM` 처리 안의 모르는 지점에서 뒤집힌다) · guide ACF 출고값이 0(`TRIGOUTFORCE=0` — 타이밍 스크립트가 몬다)이라는 투의 문장, grep `출고값`(R2618 부터 `TRIGOUTFORCE=1` — `ics_archon/archon/controller.py:1829` · `icg_archon/commands.py:1060`·`1169` · `icg_archon/backend.py:424` · `tests/test_icg_backend.py:90`).
    - `ics_archon/DevNote.md` 새 절(09-24 결정) + 11.58 에 빠진 카드 신설 결정 한 줄 보충.
    - 후속 — 경계 추정 개선(`BUFnLINES` 외삽 · `frame_poll` 축소)과 `APPLYSYSTEM` 안 핀 반전 지점 실측이 되면 g 를 줄인다.
  - **`HKDATA NOW` 에서 Radionode 제외** (결정 10) — `icg_archon/hk.py` `refresh_now()` 의 `radionode.poll_now()` 호출과 `_radionode_is_old()` 제거 · `[radionode] now_min_age` 설정(config·ini)과 그 시험(`test_the_threshold_comes_from_the_ini_not_the_poll_period` 등) 정리 · `hkdata.py` 표·docstring 의 *"(+ Radionode)"* · DevNote 에 11.56 을 뒤집는 절 · 배포 ini 는 **안 바꾼다**(ICS `hk_query_timeout = 2.0` · ICG `[radionode] timeout = 5.0` 그대로).  ✅ 그러면 종전의 *"ICG `[radionode] timeout` 5.0 s 가 ICS 시한 2.0 s 보다 길어 느린 날 HK 블록이 통째로 sentinel"* 위험은 사라진다(`GO` 경로에 인터넷 왕복이 없다).
  - KASI +9 h — DevNote(`ics_sim` · `ics_archon`)에 결정 항목이 없다(근거는 `rawpair.py` 보정표 주석과 `982ebe5` 뿐).  항목을 만들면 DECISION_LOG D-017 배너의 *"DevNote … 에는 이 결정의 항목이 없고"* 도 함께 고친다.  브랜치 `ics_sim/DevNote.md` 의 *"보정 `0` 과 세 관측소 경계는 그대로다"* 현재형 문장 아래에는 개정 한 줄이 필요하다.  `main` 의 `ics_sim/ics_sim/rawpair.py` 는 합류 전까지 `'KMTK': 0` 이다.
  - DevNote 11.90-(1) *"타이머 해제만은 수락 전에 한다"* 를 작업본의 *"거절된 GO"* 변경이 뒤집었는데 DevNote 는 그대로다.
  - 폐지 카드 대사 — `ics_sim` RETIRED 목록에 5.10절 v1.10 미도입 넷(`HKQDATE` · `HTRPID` · `HTRRAMP` · `FORCELEVEL`)을 보태고, guide 헤더용 폐지 카드 대사 시험을 새로 둔다.
  - 합류 때 — 브랜치의 `DECISION_LOG.md` 사본은 `main` 판(D-013 · D-014 · D-017 개정 표시 · D-023)을 정본으로 병합한다 · CR-003 은 브랜치 `CHANGE_CONTROL.md` 에만 있으니 `main` 으로 옮긴다.
- ⏳ **`main` 쪽 문면 하나** (다른 문서 — 이 라운드에서 안 고쳤다): `project_management/operations/ICS_DEPLOYMENT_CHECKLIST.md` 관측일 경계 항목의 *"KASI 는 보정 0"*(결정 1 과 반대 — 배정자 없음).  ✅ 함께 적혀 있던 둘은 고쳤다 — DECISION_LOG D-014 결정 셋째 항목(*"`DATE-OBS` 는 `SHOPEN` 지시 시점"*)에 결정 4 개정 표시(머리 배너 · 항목 인라인 · 상태줄) · 통합 §1.1 대비표 `TRIGOUT` 행 *"노출 창"* → *"판정 창"*.

### ✅ 규격 미반영 — 없다 (돔 방위 자릿수는 결정 9 로 닫혔다)

- ✅ ~~**돔 방위 카드 소수 2자리**~~ — **해소 (결정 9, 운영자 2026-09-24)**: 방위 셋은 **소수 3자리**(`%.3f` — redis 도 같다, `DAZERR` 는 `%+.3f`)로 규격 5.7.3절 (g) 와 견본 6장에 실었다.  브랜치 11.94-h 의 `%.2f` 는 코드 쪽이 따라올 일이다(아래 「브랜치 후속」).

### ⏳ 운영자 판단 대기 — 규범을 바꾸지 않은 것 (운영자 확정 2026-09-23)

> 번호는 2026-09-23 전반 재검토의 발견 번호다 — `C-n` 도 그 목록의 번호라 통합 문서의 C-항목과는 다른 번호 공간이다.  목록 원본은 세션 임시 폴더에 있어 저장소에 없으므로 행마다 내용을 적는다.

| 번호 | 무엇 | 물을 것 |
|---|---|---|
| D4-8 | 독출 뒤 저장(FETCH·쓰기)이 실패한 노출은 번호가 이미 넘어가 결번이 남는데, 2.3절 8항 *"결번이 남는 자리 넷"* 에 없다(science `_store()` · guide `_store_locked()` 는 오류만 낸다) | ⑤ 로 등재할지 · 되감기 조건(뒤 프레임이 번호를 안 집었을 때만)을 코드에 둘지 |
| D4-10 | `ICSBUILD`/`ICGBUILD` 의 빌드일시가 8월 말에 멈춰 있다(`ics_archon` 08-28 · `icg_archon` 08-31 · `ics_sim` 08-22) | 배포 전에 올릴지 · 5.5절에 갱신 규범 한 줄(선택) |
| D4-19 | 5.7.2절 ICS↔TC 시계 비교가 guide 에 걸리는지 규격이 말하지 않고, ICG 에는 그 감시가 없다 | 10.1절에 적용 여부 한 줄 |
| D2-3 · D7-9 | 견본의 `OBSTYPE` comment 가 `IMAGETYP` 과 같은 레거시 *"Type of observation"* 이다(뜻은 v1.13 에서 계통 식별로 바뀌었다) | 카드를 지목하면 견본 6장 · 템플릿 · 대사 시험을 한 커밋에 · 6장에 뜻 변경 행(선택) |
| D7-13 | `DSTELALT`/`DSTELAZ` comment 에 단위가 없고, science `ICSBUILD` comment 에 *"ICS/ICG"* 가 있다 | 카드를 지목할 때만 고친다 |
| C-4 | `EXPID`·노출 번호는 계통 안에서만 유일하다 — science 와 guide 의 값이 겹칠 수 있다(견본 셋도 같은 `EXPID`) | 5.9·9.2절에 *"두 계통이 섞인 곳에서는 `DETID`/`DATASRC` 로 먼저 거른다"* 안내 한 줄 |
| C-5 | `[node] observatory` 키가 없으면 조용히 KASI 로 기동한다(2.2절 · D-020 은 *"넷 밖의 값"* 만 거부한다) | 누락도 거부 / KASI 기본값 + 경고 가운데 하나를 규범으로 |
| D6-8 | 아래 「브랜치 상태」 절의 `raw-fits-spec-v1-review` 가 로컬·원격 어디에도 없다(합류 커밋 `e1cb82f` 는 남아 있다) | 되살릴지(`e1cb82f^2`) · 그 절을 *"지워졌다"* 로 고칠지 |
| D6-14 | `main` 의 다른 폴더가 `archive/` 로 간 파일을 가리킨다 — `ICS_DEPLOYMENT_CHECKLIST` 관련 문서 절(→ Specification v1.9) · `ACTION_REGISTER` ACT-011(→ 원장 v1.16) · DECISION_LOG D-009~D-012 네 자리(→ 구명 `Pair_Spec_v1.2`) · `mef_fits_spec/README` | 판 무관 지시로 바꿀지 · DECISION_LOG 는 결정 당시 기록이니 경로만 고칠지 둘지 |
| — (결정 5 개정 분석, 2026-09-24) | guide ACF 타이밍 모델이 없으면(형태 불일치·읽기 실패 → `timing=None` → `icg_archon/backend.py` `frameshift_to_done()` 이 `0`) `t_next` 가 곧 완료 관측이라 판정 창이 좁혀지지 않고, `DATE-OBS` 자체도 ≈1.25 s 늦어 창이 통째로 밀린다 | `fs_to_done=0`(ACF 타이밍 모델 없음)일 때 `TRIGOUT` 은 `-1`(판정 못 함)인가, 밀린 창 그대로인가 — 정해지면 위 「브랜치 후속」 창 위치 시험의 기대값이 된다 |
| ~~—~~ ✅ **결정 9 로 해소** | ~~돔 방위 카드 소수 2자리~~ → **소수 3자리**(2026-09-24) | — |
| ~~— (이 라운드 검증)~~ ✅ **결정 8 로 해소** (`RDMODE` 도 `'NC'`) | ~~결정 6 은 INI 에 없으면 `'NC'` 인데, 같은 INI 전용 값 `RDMODE` 는 *"독출 모드는 언제나 존재한다"*(5.0절 표)는 이유로 `'UNKNOWN'` 이다 — 시리얼도 물리적으로 늘 있어 5.0절 `NC`/`UNKNOWN` 구별과 부딪힌다~~ | ~~① 결정 6 을 유지하고 *"UNKNOWN 이 아닌 이유"* 한 줄을 넣을지(이유는 운영자가 준다) ② `CTRLnSN` 만 `'UNKNOWN'` 으로 할지 — 어느 쪽이든 5.0절 표 · 5.5절 · 10.3절을 같은 문면으로~~ |
| ~~— (이 라운드 검증)~~ ✅ **종결 — 결정 5 개정** (2026-09-24, comment 가 그대로 맞다) | ~~G 견본 `TRIGOUT` comment `Trigger Out asserted during exposure (1=yes)` 가 10.3절 판정 창(노출 + 자기 독출, 이웃 창과 겹침 — 결정 5)보다 좁다~~ → 판정 창이 노출 창 ± g 로 좁혀져 *"during exposure"* 가 맞다(G 견본 · `guidecards` 템플릿 불변) | — |
| — | 결정 4~10 에 D-번호를 줄지 | 규격은 운영자 확정 날짜(*"2026-09-23"* · 결정 5 개정과 8 · 9 · 10 은 *"2026-09-24"*)로만 인용한다 |

**범위 밖으로 둔 제안 9건** (규범 보강 제안 — 다음 판 후보):

| 번호 | 제안 |
|---|---|
| D2-11 | 정본 견본이 충돌 사례(`FILENAME` 에서 `DETID` 필드를 뗀 값 ≠ `EXPID` — 번호가 6 밀렸다)라는 안내를 2.3절이나 연동 표에 |
| D3-12 | 10.5절 guide 체크리스트에 geometry 합 불변식 행과 `TRIGOUT` 값역(`1`/`0`/`-1`) 행 |
| D3-14 | 10.3절 KASI 벤치 예시에 guide 둘째 상자 `STA-0230` 과 *"`CTRL1SN` 은 `CTRL1CFG` 안의 시리얼과 같은 상자를 가리킨다"* 안내 |
| D3-16 | G 견본 `PRESCNY` comment `(frame-edge side)` 도 science 문구 그대로다 — 아래 대사 목록의 `OVRSCNY` 항목과 함께 정리 |
| D4-12 | 5.4절 `EXPTIME` 에 셔터 노출의 경계(열리기 시작 ~ 닫히기 시작, 브랜치 DevNote 11.83) |
| D4-17 | 5.0절 `DEWPRES` 표기를 `x.xxe±n` 으로(양의 지수 `e+N` 도 실린다) |
| D4-18 | 5.0절에 헤더 값 ASCII 제한(비ASCII 사용자 입력은 `?` 로 바뀐다) — 또는 코드 detail 의 근거를 FITS 표준으로 |
| C-10 | 2.2절에 관측일을 정하는 순간(프레임 개시 — `DATE-OBS` 로 다시 센 날짜와 경계 근처에서 갈릴 수 있다) |
| C-11 | 5.5절에 KASI 벤치 science 상자(`KMTK-SCI-112`/`-113` · `STA-0212`/`STA-0200`, 상자 하나가 MK·NT 어느 역할이든 한다) |

### (구) v1.13 (2026-09-12 판올림)

> ⭐ **v1.13 은 실기 라운드(브랜치 `ics-archon-v1.0-build`, 2026-09-06~11)에서 확정된 것을 한꺼번에 싣는다** — 12장 v1.13 행이 전량 목록이다.  헤더에 실제로 닿는 것은 여섯이다:
>
> 1. **돔 방위 셋** `DSAZ`·`DSTELAZ`·`DAZERR` 의 출처가 **돔 제어 프로그램 redis** 로 확정(**D-021**).  5.7절 돔 행을 넷으로 가르고 **5.7.3절**(규약·표기)을 신설했다.  ⛔ TC 는 이 셋을 안 보낸다 — 5.0절 출처 어휘의 `TCS relay or REDIS` 를 폐지하고 **`REDIS (dome control)`** 를 세웠다.
> 2. **`OBSTYPE`** 이 `IMAGETYP` 사본에서 **계통 식별**(`SCIENCE`/`GUIDE`)로.  견본 3장의 값도 고쳤다.
> 3. **guide `LEDFLASH` → `TRIGOUT`** (같은 자리, 1:1 교체라 128장 불변).
> 4. **`FSATEMP`/`FSAHUM` 소수 2자리** 확정 (~~OI-16~~ 종결).
> 5. **guide X 16 = `PRESCNX`** — CCD 의 **dark reference columns** 를 읽은 값이다(CU 협의 완료).  `OVRSCNX=0`.
> 6. **COMMENT 두 장에 밑줄** (`Exposure Information` · `Camera System House Keeping Data`).
>
> 그 밖에 규범 신설이 다섯이다 — **2.3절 8항**(저장 안 된 프레임은 노출 번호를 안 먹는다, **D-022**) · **5.4.1절**(`STOP`·`ABORT`) · **5.6절 갱신 주기·신선도 창**과 **실측 보존 조항** · **`HKUDATE` 셈**(Radionode 제외) · **`CAMVER` 범프 사유 셋**.  OI 는 **넷 종결**(16·23·25·27) **넷 신설**(29~32).
>
> ✅ ~~⛔ 브랜치 후속 일감이 있다 — 합류하면 바이트 대사가 빨개진다.~~ **끝났다** — 브랜치 `bfc4ea6` · `cbffe40`(2026-09-12)이 아래 일감을 처리했고, 합류(`5543234`) 뒤 전수가 통과했다(`ics_archon` 716 · `ics_sim` 425).  `HKUDATE` 셈만은 뒤에 구조로 풀렸다 — science 가 `HKDATA` 와이어(`a0b2773`, 2026-09-15)로 ICG 가 센 값을 그대로 받고, Radionode 제외는 `icg_archon/hk.py` `sensors()` 한 곳이 한다.  아래는 그때의 목록이다.  main 의 새 견본과 브랜치 템플릿을 실제로 대조해 본 결과(2026-09-12) 갈린 곳은 **science 2 · guide 5** 다:
>
> - science `rawcards.CARDS` — `COMMENT` 두 장의 본문(`Exposure Information` · `Camera System House Keeping Data`)에 **밑줄**을 더해야 한다.
> - guide `guidecards.CARDS` — 같은 `COMMENT` 두 장 + `PRESCNX` comment(→ `Dark reference columns per amplifier`) · `OVRSCNX` comment(→ `Overscan columns per amplifier (none)`) · `CHMAP` comment 의 `[TBC]` 제거.  `LEDFLASH`→`TRIGOUT` 은 `SPEC_PENDING` 이 이미 덮고 있어 대조에 안 걸린다.
>
> 그 밖에 코드가 따라와야 하는 자리: `guidecards.SPEC_PENDING` 비우고 `tools/gen_guidecards.py` 재실행 · `rawhdr.format_ens()` 를 **소수 2자리**로 · science `backend.sensors()` 의 `HKUDATE` 셈에서 **Radionode 제외** · guide geometry `PRESCNX=16`/`OVRSCNX=0` 이 견본과 맞는지 바이트 대사 · `TRIGOUT` 결측은 **sentinel `-1`**(카드를 비우지 않는다) · `OBSTYPE`/`INSTRUME` 견본 대사 · 브랜치 `DECISION_LOG` 의 D-021 상태 줄.

> ⭐ **v1.12 는 v1.11 발행 뒤 쌓인 정합 수정을 담는다** (5.7.2절 신설 · `CTRL1CFG` 한 규칙 · `RDMODE` 등재 · 출처 어휘 — 12장).  ⚠️ 아래는 v1.11 을 끊은 경위다.  v1.10 이 발행(2026-09-04) 뒤 이틀 동안 제자리 개정을 많이 받아 **발행본과 갈렸기 때문에** 판을 끊었다(12장 v1.11 행).
> ⚠️ 태그는 **최신 판에만** 둔다 — v1.13 발행과 함께 `raw-spec-v1.12`(구 발행 커밋 `8e3bdbf`)를 지우고 **`raw-spec-v1.13`** 을 이 판의 마지막 커밋에 붙였다(로컬·원격 반영 완료).  팀은
> `git fetch --tags --prune --prune-tags` 가 필요하다.

### ⭐ 판올림 규약이 바뀌었다 (운영자 확정 2026-09-06)

⛔ **안 바뀐 문서는 안 올린다.**  종전에는 규격·원장·통합 **셋을 늘 함께** 올렸는데(v1.8·v1.9 라운드),
운영자 확정: *"버전번호 별도로 가고 있었기 때문에, 안 바뀌었으면 안 올리도록 해줘."*

* v1.11 라운드가 그 첫 적용이었다 — **규격만 v1.10 → v1.11**, 원장 `v1.17` · 통합 `v0.9` 는 **내용이
  안 바뀌어 그대로** 뒀다.  규격 연동 표의 링크만 현행을 가리키게 고쳤다.  ⭐ **v1.12 라운드에서는 원장 본문이 실제로 바뀌어 원장도 `v1.18` 로 올렸다** — 같은 규약의 뒤집힌 쪽이다 (통합 `v0.9` 는 그대로)
  (⚠️ v1.10 내내 구판 `v1.16` · `v0.8` 을 가리키고 있었다).
* 각 문서의 머리말이 *"raw spec v1.x 동반"* 이라 적은 것은 **그 판이 언제 함께 나왔나의 이력**이다 —
  규격 판이 올라갔다고 고치지 않는다.
* 태그는 규격에만, 그리고 **최신 판 하나만** 둔다(위).

⭐ v1.10 = **HK 카드 5장 신설**(`HKUDATE` + 히터 넷) · **온도 부호 규약** · **게이지 Off 조항** · 견본 6장을 `header_samples/` 로 모으고 이름을 `v1.10`/`+LF` 로 통일.
⛔ **science 견본이 4블록 → 5블록(14,400 B)** 이 됐다.  ✅ **바이트 대사 시험의 글롭은 그 뒤 판 무관으로 고쳐졌다** — `ics_sim/tests/test_raw_draft.py` · `ics_archon/tests/test_fitswrite.py` · `ics_archon/tests/test_icg_cards.py` 가 모두 `…fits.header.v*[0-9].txt` 라, 견본 이름의 판만 올리는 것으로는 대사가 조용히 skip 되지 않는다(구 경고 *"경로·이름을 리터럴로 박고 있다"* 는 실측으로 해소됐다).  ⚠️ **대신 밀리는 것은 머리말의 판 표기다** — 2026-09-24 에 훑은 브랜치 자리: `icg_archon/guidecards.py`(*"정본은 …G.fits.header.v1.13.txt"*) · `ics_archon/tests/test_icg_cards.py`(*"…Specification_v1.9.md"* · *"견본 헤더 v1.10"*) · `ics_sim/ics_sim/rawhdr.py` · `rawpair.py` · `hardware/archon.py`(*"…Specification_v1.9.md"*) — 판올림마다 낡는데 **글롭이 판 무관이라 시험이 못 잡는다**.  ⛔ **`tools/gen_guidecards.py` 의 `SAMPLE` 만은 머리말이 아니다** — 견본 판을 일부러 박아 둔 실행 경로라(지금 `v1.13`), 견본 이름이 바뀌면 도구가 `SystemExit` 로 멈추고 그 도구를 부르는 `test_icg_cards.test_template_matches_the_sample_generator` 도 빨개진다.  판올림 라운드마다 이 자리를 훑되, 고치는 것은 **브랜치 소관**이다(`_vendor` 사본은 `tools/sync_vendor.py` 가 따라온다).

### (구) v1.9 (2026-08-30 발행 · 푸시 · 태그 `raw-spec-v1.9` 완료)

**[`KMT_CEU_Raw_FITS_Specification_v1.9.md`](archive/KMT_CEU_Raw_FITS_Specification_v1.9.md)** ("raw spec" / "로우 스펙") 이 **그때의 현행이었다**(지금 현행은 맨 위 「✅ 현행 규격」 절) — v1.3 재작성판(구 "Raw FITS Pair 규격" v1.2 개명·대체) → v1.4 운영자 1~4장 검토 반영 → v1.5·v1.6 = 5장 검토분 → v1.7 = 파일명 넷째 필드 `<DETID>` 명명 → v1.8 = `OI-9` 폐기 + `CTRLnCFG` 예시 정합 → **v1.9 = guide raw FITS 9·10장 신설 + `Tapaculo`→`Radionode` 개명**. 구판은 `archive/`(v1.2 구명 Pair_Spec · v1.3 ~ v1.8).

- ⭐ **v1.9 발행분 (2026-08-30, 커밋 `7ea3d63` — origin 푸시 완료)** — 세 문서를 함께 판올림했다: **규격 v1.8 → v1.9** · **원장 v1.15 → v1.16** · **통합문서 v0.7 → v0.8** (구판 `archive/`). 발행·후속 정정을 **커밋 하나로 합쳐** 올렸다(운영자 지시 — main 커밋 수 최소화). 태그 `raw-spec-v1.9` 는 운영자 지시(2026-08-30)로 이 판의 마지막 커밋(인수인계 갱신 커밋)에 붙었다.
  1. **guide raw FITS 장 신설 (9·10장)** — 운영자 확정(2026-08-29) 방침대로 science 와 분리. 9장 = 파일명(`<DETID>`=`G`, pair 없음)·구조(4224×1033)·픽셀 배치([16 다크 기준열|512|512|16]×4블록, Y=1024+9), 10장 = 노출 의미론(셔터 무관 — `EXPTIME` = 독출 개시 간격 · 첫 프레임 폐기 · `DATE-OBS` = 직전 독출 개시 · **`go n` = `n`+1 독출 `n` 저장, 프레임당 파일 1개** — 운영자 확정 2026-08-30)·헤더(science 골격, **값 카드 123장** — `CTRL2*`·`C2_*` 미수록 · `CHMAP` 1장 · `IMGROT` 신설 · `ICGBUILD` · `C1_VOLT`/`CURR` 8자리+`HEATER`)·`C1_TEMP` 8자리(**OI-19 종결** — 구판 5.6.1절 `Mod9 HVYBias` 는 `HVXBias` 오기 정정)·guide 검증 체크리스트·**OI-20~24 신설**(10.6절). 구 9·10장(관련 문서·Revision History)은 **11·12장**이 됐다. 원전: `__reference/CCD47-20.pdf` · `__reference/guide_ccd_format.xlsx`(운영자 2026-08-30) · guide ACF `KMTK_GUI_162_STA0201_R2608` 실측 · gmon v2.
  2. **`Tapaculo` → `Radionode` 개명** (운영자 지시 2026-08-30) — 세 문서 살아있는 표기 전량(17곳) 교체, 5.6절에 구칭 앵커. `archive/`·레거시 실측 헤더는 그대로(사실 기록). ⚠️ 코드·문서 쪽 잔여 (**브랜치 충돌을 피해 여기서 안 고쳤다** — 브랜치 쪽 일감): ① `Radionode` 개명 — `ics_sim/ics_sim/hardware/archon.py:142` 주석 · `ics_sim/DevNote.md:1892` · 브랜치의 사본들 ② `ics_sim/ics_sim/fitsout.py:65` 주석이 구판(v1.2) 절 번호(`규격 5.1절 권장, 9장 OI-7`)를 인용 — 현행은 8장 OI-7 이고 9장은 guide 라 딴 곳을 가리킨다 ③ 브랜치 `ics_archon/acf/README.md` 의 "guide 8자리는 미해결 OI-19, 아직 규격에 안 실렸다" 문장 — v1.9 종결·10.4절 수록로 낡았다(머지 때 정정).
- ✅ **guide 헤더 견본 v0.0 확정 + 전수 대사 완료** (2026-08-30) — 운영자 확정 결정 다섯이 규격 10장에 반영됐다: `CTRL2*`·`C2_*` **미수록** · `CHMAP` 1장(`'NRL,ERL,SRL,WRL'` [TBC]) · **`IMGROT` 신설**(`'270,180,90,0'` [deg, CW], N·E·S·W) · **`ICGBUILD`** 개명(+ `TIMESYS`/`EXPID` comment 의 ICS→ICG) · `C1_VOLT`/`C1_CURR` **8자리**(`HEATER` +28 V, VOLT 소수 2자리). 견본은 클루디가 **11,520 B 로 패딩**(운영자 지시 — 144 레코드)했고 REFTEXT 사본(11,669 B)을 만들었다. **frame-transfer CCD 용어 확정**(운영자).
- 📋 **guide 견본 ↔ 10장 대사 목록** (오기·오타는 운영자 지시로 정정 완료 — 잔여는 이 목록을 해소하는 라운드에서.  ⭐ 견본은 v1.10 부터 규격과 같은 판 번호라 따로 '승격'은 없다):
  1. ✅ **명백 오기 둘 — 정정 완료** (2026-08-30, 운영자 지시로 클루디 수정 + REFTEXT 재생성): ① `NAXIS1`/`NAXIS2` `19200`/`9400`(science 잔재) → **`4224`/`1033`** ② `AMPNAX1`/`AMPNAX2` `1033`/`4224`(축 뒤바뀜 + 4224 는 amp 값이 아니라 프레임 폭) → **`528`/`1033`** (합 불변식: 0+512+16 = 528 · 0+1024+9 = 1033).
  2. ✅ **`CHMAP` comment 정정 완료** — ① 오타 `outout` → `output` (2026-08-30, 운영자 지시) ② **검토 표식 `[TBC]` 제거** (v1.13 라운드, 운영자 메모 (5)). ⭐ ②의 근거는 *값이 확정됐다* 가 아니라 **검토 표식을 아카이브 파일에 박아 두지 않는다**이다(5.0절 공통 규칙 신설) — 값의 잠정성은 아래 4번과 **OI-21** 이 그대로 든다. science 견본(MK/NT)의 `CHMAP_*` comment 에는 `[TBC]` 가 없어 고칠 자리가 없다.
  3. ✅ ~~`INSTRUME`~~ — **`'KMTA Guide CCDs'` 로 정정 완료** (운영자 확정 2026-09-07 *"instrume 는 비웠을 때 `<SITE코드> Guide CCDs` 로"*, DevNote 11.43-(1) — 견본 2장 + 10.3절 수록). ✅ ~~`FPAID`~~ — **고칠 것이 없다**: `'FPA#1'` 은 5.3.1절 SSO 유도값과 같고, 같은 확정이 *"guide CCD 도 FPA 조립체에 들어가 있어"* 로 귀속을 닫았다. ✅ ~~목 판단 (OI-24 잔여) — `CAMVER`(아래 5번) · `IMAGETYP` 어휘~~ — **~~OI-24~~ 종결로 닫혔다**(운영자 2026-09-15, 브랜치 DevNote 11.92 — 둘 다 science 와 같다 · 규격 v1.14 10.3·10.6절).  ⏳ 남은 것은 `FILENAME` 값 꼬리 공백 1자(`'…G '` 23자 맞춤 — 사소) 하나다. ✅ ~~`CCDTEMP` comment~~ — **"M" 제거 완료** (2026-08-30, 견본 3장 — science 포함). ✅ ~~`DETID` comment~~ — **`'Detector ID in this raw FITS file'` 로 정정 완료** (운영자 확정 2026-08-30, 클루디 수정 + REFTEXT 재생성).
  4. ⏳ 실측 (OI-21·22) — `CHMAP` 값 [TBC] · `IMGROT` 값 검증 · `PIXSCALE` 0.49/0.51/0.52 · ⚠️ 칩 순서 견본 N·E·S·W vs gmon 잠정 n,s,e,w 어긋남(한쪽 확정 필요). **운영자 지시(2026-08-30): 다음 판에서 실측 확인 후 갱신** — 이번 라운드에서는 더 건드리지 않는다.
  5. ⏳ **최종 검토(2026-08-30, 커밋 후 전수 재검)에서 추가된 확인 항목** — 목록 해소 라운드에서 함께:
     - ✅ ~~`C1_VOLT` 절사/반올림~~ — **해소 (2026-08-30, 운영자 확정)**: **규칙은 반올림**("소수 셋째 자리에서 반올림", 10.4절 명시)이고, **견본 샘플값은 절사 그대로 둔다** — 임의 샘플이라 수정 대상이 아니다(운영자: "견본을 수정할 필요는 없었는데. 반올림이란 것만 문서에 명시해두면 되"). 규칙-샘플값 표면 불일치는 결함이 아니다.
     - `OVRSCNY` comment `(frame-center side)` — science 문구가 그대로 왔는데 guide 의 추가 9행은 **중앙이 아니고 위치도 미정**(OI-21)이다 — 목록 해소 때 문구 정정.
     - ✅ ~~`OVRSCNX` comment `(side varies)`~~ — **해소 (v1.13)**: guide 의 X 16 은 `OVRSCNX` 가 아니라 **`PRESCNX`** 로 귀속이 바뀌었다(운영자 확정 2026-09-08, CU 협의 완료 — CCD 의 **dark reference columns** 를 읽은 값).  G 견본의 두 카드 값을 `PRESCNX=16` · `OVRSCNX=0` 으로 고치고 comment 를 `Dark reference columns per amplifier`(`PRESCNX`) · `Overscan columns per amplifier (none)`(`OVRSCNX`)로 바꿨다.
     - ✅ **규범은 v1.14 가 정했다** — guide `BIAS` 는 최소 노출이라 `EXPTIME` 이 0 이 아니다(10.3절 · ~~OI-24~~).  견본의 `EXPTIME=0` 은 임의 샘플값이라 운영자가 카드를 지목할 때만 고친다.  종전 기록: `EXPTIME=0` · `IMAGETYP='BIAS'` 시나리오 — guide 의미론상 `EXPTIME=0`(독출 간격 0)은 실현 불가한 견본값 — 목록 해소 때 현실 시나리오(예: 1초) 검토.
     - ✅ **닫혔다** — science 와 같은 `'CEU-v2.1'` 이고, 바꿀 일이 있으면 ICG INI `[camera] camver` 로 덮는다(~~OI-24~~, 운영자 2026-09-15 · 규격 v1.14 10.6절).  종전 기록: `CAMVER='CEU-v2.1'` 이 science 와 동일 — guide 계통이 같은 카메라 전자부 버전 문자열을 공유하는지 확인 (OI-24 잔여 ①). ⚠️ **10.2절 규칙상 현행 규범이 이미 science 와 같다** — 10.3절 표에 `CAMVER` 행이 없으므로 5.2절 값이 그대로 적용되고, 취득 SW 도 그 값을 싣는다(`icg_archon/guidehdr.py` `cam.get('camver', 'CEU-v2.1')`). 남은 물음은 *다른 값을 써야 하는가* 하나다.
     - COMMENT 2번("Map of CCD output channels, raw X ascending within each card")이 science 문구 그대로 — 골격 규칙(10.2)상 유지 가능하나 guide 는 카드가 하나라 "each card" 가 안 맞음, 문구 조정 선택.
     - ⏳ **공유 카드 8장의 문자열 인용 필드 폭이 science 와 다르다** — 컨트롤러 블록 `DATASRC`·`CTRL1ID`·`CTRL1SN`·`CTRL1CFG`·`RDMODE` 24/29 → **26**, `C1_TEMP`·`C1_VOLT`·`C1_CURR` 51 → **49**.  ✅ 8장 중 4장은 **설명이 끝났다** — `C1_*` 셋은 자리 수 차이(guide 8 vs science 10/7)에서 오는 구조적 차이이고(폭 = 최장 자연 길이 + 2), `CTRL1CFG` 는 패딩이 아니라 guide ACF 이름에 `_MK`/`_NT` 꼬리가 없어 값이 3자 짧은 것이다.  **남은 물음은 컨트롤러 블록 네 장을 26 으로 둔 것이 의도인지 하나**다.  ⭐ **견본은 고치지 않는다** — 폭 조항을 규격 5.0절(인용 필드 폭의 정본은 견본 · 최소 패딩)과 10.2절(8장 열거)에 실었다.  (v1.14 — 판정할 때 이름이 달라 셈에 들지 않는 `ICGBUILD`(자연 길이 24)도 26 으로 채워져 있다는 것을 함께 본다: guide 컨트롤러 블록 여섯 장이 전부 `CTRL1CFG` 의 자연 길이 26 에 맞춰져 있다 — 10.2절 열린 물음에 더했다.)
- ✅ **guide 견본 `LEDFLASH` → `TRIGOUT` 교체 완료** (v1.13 — 운영자 확정 2026-09-09, 브랜치 코드가 먼저 갔다): G 견본 2장(정본·`+LF`)의 **레코드 46** 을 `TRIGOUT =                    0 / Trigger Out asserted during exposure (1=yes)` 로 바꿨다.  **폭·패딩 동일 — 값 128장 · 144 레코드 · 11,520 B(+LF 11,669 B) 불변**이고 MK·NT 견본은 손대지 않았다(science 는 `LEDFLASH` 유지).  ✅ ~~⛔ 브랜치 동반 일감~~ **끝났다** — `bfc4ea6`(`TRIGOUT` 결측 `-1`) · `cbffe40`(`SPEC_PENDING` 비움 · 템플릿 재생성, 2026-09-12).  그때의 목록(머지·후속 커밋에서): `icg_archon/guidecards.py` 의 `SPEC_PENDING` 을 **비우고** `tools/gen_guidecards.py` 로 템플릿을 재생성 · `tests/test_icg_cards.py` 의 `len(SPEC_PENDING) == 1` 단언을 0 으로 고침.  ⛔ **결측 규칙은 규격이 정했다** — 모르면 **sentinel `-1`** 이고 카드는 남긴다(5.0절 정수 sentinel · 값 카드 128장 불변).  `guidehdr.py` 주석의 *"카드를 비운다"* 는 규격과 어긋나므로 브랜치에서 고칠 것.
- ⏭️ **판올림 이월 대기 1건** (구 "v1.9 대기 5건" — ~~`CCDTEMP` comment `M` 제거~~ 는 **2026-08-30 운영자 지시로 조기 실행**: G·MK·NT 견본 3장 + REFTEXT 제자리 반영, 5.6절·원장·통합 문구 갱신. ⚠️ 브랜치 기계 사본 3곳·바이트 대사 시험이 어긋남 — 머지 때 동반 수정): **바이어스 측정값의 헤더 카드 배치**(D3) 하나다.  ⭐ 닫힌 셋 — ~~`OI-18` 폐기~~ **v1.10** · ~~`RDMODE` 결측값 `UNKNOWN` 등재~~ **v1.12**(5.5·10.3절 등재) + **v1.13**(5.0절 `NC`↔`UNKNOWN` 구별 · 7장 체크리스트 8번) · ~~`CAMVER` 범프 규범 명시~~ **v1.13**(5.2절 `CAMVER` 행에 범프 사유 셋: 포장 4.3절 · `Cn_*` 자리 5.6.1절 · 듀어 RTD 배치 10.4절.  `ICGCFG` 신설 안은 기각, 값↔구성 대장은 `OI-29`.  **견본은 안 바뀌었다**).  남은 D3 는 **guide 견본 대사 목록 해소 라운드에서 함께 처리**가 자연스럽다(견본 카드 변경을 동반한다). 상세는 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "규격 쪽 후속".
- ✅ 5장 검토 라운드는 닫혔다 (v1.5~v1.7, 2026-08-25~26) — `Cn_*` 자리 순서 명세(5.6.1절) · 노출 정체성 카드 개정(v1.6) · `<DETID>` 명명(v1.7).
- ✅ **v1.8 발행분 (2026-08-29)** — 세 문서를 함께 판올림했다:
  **규격 v1.7 → v1.8** · **원장 v1.14 → v1.15** · **통합문서 v0.6 → v0.7** (구판 `archive/`).
  - **`OI-9` 폐기** — *"실측하여 raw spec 과 mef spec 에 다 정리해놓았고, 이들 문서를
    통해 통제하므로"* (운영자 2026-08-29).  종결이 아니라 **폐기**다: 배선은 이제
    4.5절 amp 전수 표·`CHMAP_*` 와 MEF `AMPINFO` 가 통제한다.  자리 여섯 전부 정리
    (규격 OI 표·본문 · 원장 셋 · 통합문서 · README open item 열거).
    원장의 경고 문구 셋은 **참조 안내로 바꿨다**(운영자 2026-08-29) — *"세부 내용,
    앰프별 배치 및 방향은 raw spec 4.5절(Amp 전수 표)을 참조한다"*.  경고로 둘 일이
    아니라 **그 문서가 관리하는 값**이라는 뜻이다.  기계 정본은
    `Detector_Ch_to_AmpID_Map_v1.1.txt` 다.  ⚠️ `C-11`(converter 가 `CHMAP_*` 를
    읽도록 개정) 자체는 **converter 쪽 개정 항목으로 남아 있다** — 그건 LEECU 몫이다.
    ✅ **converter v2.5.0 이 닫았다** — `CHMAP_*` 4자 토큰으로 amp 정체를 유도한다(통합 v1.0 §1.2).
  - **`CTRLxCFG` 예시 값** — 규격 5장·원장 세 곳을 실제 ACF 이름 규칙으로 옮기고,
    **폴더 경로와 확장자(`.acf`/`.cfg`)를 뗀 이름**임을 규격에 명시했다.
  ✅ **코드 쪽도 끝났다** (2026-08-29, `ics-archon-v1.0-build` `3dabe21`) — `ics_archon` 이
  `[archon] acf_mk`/`acf_nt` 경로에서 폴더·확장자를 떼어 `CTRL1CFG`/`CTRL2CFG` 를 채운다.
  문서 경로 인용도 전수 정합했다.  경위·판단은 [`../ics_archon/DevNote.md`](../ics_archon/DevNote.md) **5장**.

### ✅ `CTRLnCFG` 를 **실제 ACF 파일명**으로 맞췄다 (운영자 지시 2026-08-29, 완료)

**값 = 적용된 ACF 파일명, 단 폴더 경로와 확장자(`.acf`/`.cfg`)는 뺀다.**  종전 견본
값(`'KMTA_SCI_101_R2609.1'`)은 실제 ACF 이름 규칙과 모양이 달랐다 -- **시리얼과
검출기조가 빠져 있었다**.  규칙은 [`../ics_archon/acf/README.md`](../ics_archon/acf/README.md)
"판 표기" 절: `<SITE>_<역할>_<유닛번호>_<시리얼>_<ACF판>[_<검출기조>]`.

    CTRL1CFG= 'KMTA_SCI_101_STA0288_R2608_MK' / Controller 1 Configuration
    CTRL2CFG= 'KMTA_SCI_102_STA0289_R2608_NT' / Controller 2 Configuration

**전파 결과** -- 자리 전부 닫혔다:

| 갈래 | 자리 | 상태 |
|---|---|---|
| 견본 pair 4 | `…{MK,NT}….v1.0{,_REFTEXT}.txt` | ✅ 운영자 (판은 안 올렸다) |
| 규격 본문 | 5장 `CTRL1CFG` 행 + "경로·확장자를 뗀 이름" 명시 | ✅ **v1.8** |
| 원장 3곳 | 3.3절 표 · 대응표 두 행 | ✅ **v1.15** |
| 기계 사본 3 | `ics_sim/rawcards.py` · `_vendor`(sync) · labtest 내장 5 | ✅ `ics-archon-v1.0-build` `b45fb31` |
| 코드 (파생) | `ics_archon` 이 ACF 경로에서 유도 | ✅ `3dabe21` (`ics_archon/DevNote.md` 5장) |

**확인해 둔 것** (2026-08-29):

- ✅ **카드 폭은 문제없다.**  값이 29자라 카드가 `8+2 + 31 + 3 = 44` 를 쓰고
  **comment 여유가 36자**다.  실제로 실린 문안은 `Controller 1 Configuration`(26자)
  이고 -- 종전 `… Configuration file`(30자)에서 `file` 을 뗐다: 값이 이제 **파일명이
  아니라 확장자를 뗀 이름**이라 `file` 이 남으면 값의 형태와 어긋난다.  전 줄 80자를
  지킨다.
- ⚠️ **`CTRLnCFG` 는 pair 두 파일에 같은 값이어야 한다** -- 규격 5장이 "두 대분을
  양쪽 파일에 모두 싣는다(converter 가 MK 만 읽으므로)" 이므로, `NT` 파일의
  `CTRL1CFG` 도 `…_101_STA0288_R2608_MK` 여야 한다.  **MK/NT 로 갈리는 것은
  `DETID` 뿐**이다(2.2절 v1.7).
- ⚠️ **`main` 에는 견본 바이트 대사 시험이 없다.**  `ics_sim/tests/test_raw_draft.py`
  는 **`ics-archon-v1.0-build` 에만** 있다 -- 견본을 고치면 **그 브랜치에서** 돌려
  확인할 것.  이번 판은 그렇게 확인했다(330 통과).

(⚠️ **v1.10 에서 뒤집혔다** — 현행은 README 의 *"견본 판 번호는 규격 판 번호를 따라간다"* 이고 시험 글롭은 `v*[0-9]` 다.  아래 이 절 끝까지는 2026-08-29 결정의 경위다.)

✅ **견본 판은 올리지 않는다 -- `v1.0` 제자리 수정** (운영자 확정 2026-08-29).
*"변경사항이 마이너한 부분이므로 승격 안함"*.  `CTRLnCFG` 도 `CCDTEMP` 의 `M`
제거도 카드 하나씩의 값·comment 변경이라 판을 가를 만한 구조 변경이 아니다.
✅ [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "규격 쪽 후속" 도 이
확정으로 고쳐져 있다 (2026-08-29 확인).

⭐ **부수 이득 하나** -- 파일명이 그대로라 `ics_sim/tests/test_raw_draft.py` 의
글롭(`*.fits.header.v1.0.txt`)이 계속 맞는다.  2026-08-22 에 견본을 개명했다가
**바이트 대사 6개가 통째로 skip 된 사고**가 있었고(초록으로 지나가 아무도 몰랐다),
그 시험이 지금은 "못 찾으면 skip 이 아니라 실패" 로 고쳐져 있지만 **개명 자체를
안 하는 것이 더 안전하다.**

⚠️ 다만 **판을 안 올리므로 "언제 무엇이 바뀌었나" 를 파일명이 말해 주지 않는다**
-- 그 이력은 규격 12장 Revision History 와 git 이력이 맡는다(구 10장 — v1.9 에서 guide 9·10장 신설로 밀렸다).  견본을 고치는
커밋에 **무슨 카드가 왜 바뀌었는지**를 반드시 적을 것.

### ✅ guide raw FITS — **9·10장으로 신설 완료** (v1.9, 2026-08-30)

방침(운영자 확정 2026-08-29 — 같은 문서 안 별도 장, science 와 섞지 않기, 같은 점·다른 점 절)대로 **v1.9 에서 신설했다.** `OI-19` 는 10.4절 수록으로 **종결**, guide 고유 미결은 **OI-20~24**(10.6절)로 등재됐다. 남은 것은 **목 검토 → guide 견본 ↔ 10장 대사 목록 해소**다 (⭐ 견본 판 번호는 v1.10 부터 규격을 따라가므로 별도 '승격' 라운드는 없다).

**아래 재료 표는 집필 근거 기록이다** (2026-08-28~29 실측·전수, 다시 캐지 말 것 — 근거는 [`../ics_archon/acf/README.md`](../ics_archon/acf/README.md) 와 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md)). 추가 원전(2026-08-30 확보): `__reference/CCD47-20.pdf`(다크 기준열 16/측 · store 1033행 — 528=16+512 와 1033=1024+9 의 데이터시트 대응) · `__reference/guide_ccd_format.xlsx`(X·Y 분해 정본).

| 항목 | guide | science | 비고 |
|---|---|---|---|
| `Cn_TEMP` 자리 | 백플레인 + MOD3·4·5·6·7·9·10 = **8자리** | 백플레인 + MOD1·2·3·4·5·8·9·10·11 = **10자리** | 근거 둘 일치(ACF `[SYSTEM]` · `modtm_gui_*.py`) |
| 프레임 | **4224 × 1033** (8탭 × `PIXELCOUNT` 528) | 19200 × 9400 (16탭 × 1200, 2줄) | ⚠️ 타이밍 `Pixels` 가 아니라 `PIXELCOUNT` 가 정본 |
| 모듈 형 | 2(AD) · 11(HeaterX) · 8(HVXBias) · 1(Driver) | 17(ADM) · 18/8(HVYBias/HVXBias) · 9·10·1 | |
| 바이어스 채널 | **18** | 16 | ⚠️ **guide 라벨 넷에 `/` 가 있다** — 5.6.1절 "슬래시 금지" 에 걸린다 |
| `BIGBUF` | 0 (512 MB × 3) | 1 (768 MB × 2) | |
| 검출기조 접미사 | 없음 (유닛당 1개) | `_MK`/`_NT` | 파일명 규칙 |

⚠️ **소비자가 이미 있다** — `main` 의 [`../gmon/`](../gmon/) v2 가 guide raw 를 읽어 칩별로 쪼갠다.  `gmon/gmon.conf` `[geometry]` 가 전제를 선언해 두었고(`seg_width 528` · `left_active 16,528` · `right_active 0,512` · `y_trim_bottom 9`), **규격이 그것과 어긋나면 `gsplit` 이 깨진다.**  `gmon/DESIGN.md` 10절 5번은 반대로 **우리에게 파일명·저장 경로 규약을 요구**하고 있다 — 두 문서가 서로를 기다린다.

⏳ **실측 확정 전인 것 — OI-20 으로 등재됐다** (v1.9 10.6절): 저장되는 528 이 시퀀서가 읽는 600(+1) 중 어느 구간인가. **데이터시트 대응은 나왔다** — CCD47-20 레지스터 반쪽은 `8 BLANK | 15 DARK REF | 1 transition | 512 active` 이고 blank 8 은 `PreSkipPixels=8` 로 건너뛰므로 **저장 528 의 선두 16 = 다크 기준열 15+1(차광 실컬럼, 프리스캔 아님)** 로 지목된다. ✅ **귀속은 v1.13 에서 닫혔다** — 운영자 확정 2026-09-08(CU 협의 완료): 선두 16 은 CCD 의 **dark reference columns** 를 읽은 값이므로 **`PRESCNX=16` · `OVRSCNX=0`** 이다(10.3절 · 9.1·9.4절 · G 견본 2장).  ⏳ 남은 것은 **실측 하나** — 528→512 추가 트림이 무손실인지(그 16 이 영상 정보를 담지 않는지)를 flat/bias 로 확인한다.  `gmon` 커미셔닝 §10-1 과 공동.

- **절 구성이 구판과 다르다** — 구판 절 번호를 인용한 문서·코드 주석(`규격 5.7절` 등)은 현행 기준으로 재확인. ⚠️ **v1.4 에서 2.5절(Wrote 통보)이 삭제돼 절 번호가 또 바뀌었다**(2장은 2.1~2.4). `ics_sim` 쪽 참조 정리는 **완료**(2026-08-22, v1.3 정렬과 함께 — 아래 "다음 사람이 할 일" 3). ICD **v4.2** §12 의 위임 대상 갱신은 LEECU 몫으로 남아 있었다 — v4.2(2026-09-04)에서도 §2·§7·§12 가 구명 `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 를 가리켰다(세 곳).  ✅ **ICD v4.3(2026-09-23)이 그 참조를 걷고** `KMT_CEU_Raw_FITS_Specification_v1.13.md` 를 인용한다 — ⏳ v1.14 발행으로 그 파일이 `archive/` 로 가서 v1.14 로 다시 갱신할 것을 요청했다(통합 v1.0 §3).
- 헤더 5장의 바이트 단위 정본은 **science 헤더 견본 pair**(`header_samples/KMTA.20260821.123456.{MK,NT}.fits.header.v1.14.txt`)다 — 구 "초안 헤더 v1.0 pair".  ⭐ **판 번호는 규격을 따라간다**(v1.10 에서 `header_samples/` 로 모으고 규격과 맞췄다) — 따로 '견본 승격' 판올림은 없다.

## 먼저 읽을 것

| 문서 | 지위 |
|---|---|
| `KMT_CEU_Raw_FITS_Specification_v1.14.md` | ✅ **현행 raw spec** — 최종 정의·규격 (science 1~8장 + guide 9·10장). 배경은 아래 원장·통합 문서로 링크 |
| `KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.20.md` | **카드 판정 원장** (v1.20 = converter v2.5.0 재대조 — raw 에서 읽는 카드 · geometry 선언 대조 · 카드 값 하드 실패 둘 · 운영자 결정 셋, 판정 불변). **0장이 판정 준거다**(준거 순위 · converter 3상태 × ICD 규정/침묵 · 준거 공백 크기). converter 가 읽는 것 · 읽지 않는 것 · 도입 후보·확정 · 폐지된 것을 13장으로 정리했다 — 최근 구판은 `archive/` |
| `KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.0.md` | **통합 문서** (v1.0 = converter v2.5.0 재대조 · *(Draft)* 를 뗐다) — Part 1: LEECU 전달용 — C-항목 · 이름 대응 · ICD/정의서 개정 후보 · **§7 「MEF converter 및 PIPELINE 판단 필요 항목」**(판단은 여기, 나머지 절은 수정 요청) / Part 2: 번호·충돌·정체성 **파급 요약**(정본 = raw spec 2.3절 + D-016). 전신 v0.5~v0.10 은 `archive/`, v0.4·v0.2 는 git 이력·외부 백업 |
| `__reference/Legacy raw fits header samples/` | **raw 쪽 기준선.** `KMTNk.20170209.044131.Rawheader.txt` keyword 123개 |

## 개정 워크플로 — `__review/` 는 임시 왕복함 (운영자 확정 2026-08-22)

**검토 사이클이 열릴 때만 `__review/` 를 만들어 쓰고, 끝나면 결과물을 이 폴더 루트에 저장한 뒤 `__review/` 는 지운다.** 상시 폴더가 아니다 — 2026-08-22 에 첫 적용: 초안 헤더가 **`KMTA.20260821.012345.MK.fits.header.v1.0.txt`** 로 승격되어 루트로 왔고, docx 왕복본·초안 이력(v0.0~v0.4.4)은 운영자 외부 백업(`__backup_raw_fits_spec_oldver`)으로 나갔다. 전달용 docx 는 검토 사이클이 있을 때만 `tools/md_to_docx.py` 로 만들어 `__review/` 에 둔다(변환기는 저장소 유지 — pandoc 없는 환경 전제, python-docx 만 사용). `__` 접두 폴더 읽기 전용 규칙은 그대로다 — 안의 파일은 읽기만 하고 **편집하지 않는다. 편집이 필요하면 그 파일을 sub레포 루트로 옮겨서(사본) 작업한다**(운영자 확정 규칙 2026-08-22). 클루디 산출물(docx) 신규 생성은 허용. 왕복 중 결정의 근거는 항상 md 판 changelog 에 반영하므로 docx 중간산물이 이력에서 빠져도 근거는 남는다.

## 태그 규칙 — `raw-spec-vX.Y` 는 **그 판의 마지막 커밋**에 붙인다 (운영자 확정 2026-08-25)

**판 하나에 태그 하나이고, 자리는 그 판의 마지막 커밋이다.** 라운드가 열려 있는 동안에는 태그를 붙이지 않는다 — 개시분에 붙여 두면 뒤에 쌓이는 결정마다 태그가 가리키는 내용과 판 이름이 갈린다(원장 v1.12 판 분리의 교훈).

- 라운드 중에 이미 붙어 버렸으면 **마지막 커밋으로 옮긴다.** 원격에 올라간 뒤라면 강제 갱신이 필요하다:

  ```bash
  git tag -f -a raw-spec-v1.6 -m '<메시지>' <마지막 커밋>
  git push --force origin refs/tags/raw-spec-v1.6
  ```

- **태그를 옮기면 이미 그 태그로 체크아웃해 둔 사람은 자동으로 따라오지 않는다** — `git fetch --tags --force` 가 필요하다. 옮겼다는 사실을 팀에 알릴 것.
- 판이 끝났다는 판단이 서기 전에는 태그 대신 **커밋 해시로 인용**한다.
- **보존 방침: 현행 판 태그만 남긴다** (운영자 확정 2026-08-25). 새 판을 태그할 때 **직전 판 태그는 지운다** — 2026-08-25 에 `raw-spec-v1.4` 를 로컬·원격에서 삭제했다.
  - 지워도 안전한 근거: 판 본문은 `archive/` 에 남고(`…_v1.4.md` 등), 그 커밋은 `main` 의 조상이라 이력에서 사라지지 않는다. 저장소 문서가 태그 이름을 인용하는 곳도 없다.
  - 잃는 것: **판 ↔ 커밋 연결**이다. 지우기 전에 그 판이 어느 커밋이었는지 여기 적어 둘 것.
- ⛔ **발행 전 예고 문면을 발행된 문서에 남기지 않는다.** 12장 행에 *"이 판을 발행할 때 … 붙인다"* 같은 예고를 적어 두면 발행 뒤에도 그대로 남아 **발행본이 자기 상태를 거짓으로 말한다**(v1.12 행에서 실제로 났다). 발행 커밋에서 과거형(*"… 에 붙였다"*)으로 바꾸고 **발행 커밋 해시를 그 자리에 적는다.**

  | 판 | 마지막 커밋 | 태그 |
  | --- | --- | --- |
  | v1.4 | `e1cb82f` (`Merge branch 'raw-fits-spec-v1-review'`) | 삭제됨 (2026-08-25) |
  | v1.5 | `13e02b2` | 삭제됨 (2026-08-26, v1.6 발행) |
  | v1.6 | `6d9c137` | 삭제됨 (v1.7 발행 즈음 — 2026-08-30 실측에서 부재 확인) |
  | v1.7 | `182b7f3` | **삭제됨 (2026-08-30, v1.9 태그와 함께 정리)** — ⚠️ v1.8 발행 때 방침대로 지워졌어야 했는데 로컬·원격에 남아 있었다 |
  | v1.8 | `8ed6385` (`raw spec v1.8 발행`) | **삭제됨 (2026-08-30, v1.9 발행)** — ⚠️ 메모리·기록의 "태그 → `0c821ea`" 표기는 오기였다, 실측 8ed6385 |
  | v1.9 | 인수인계 갱신 커밋 (2026-08-30 — `7ea3d63` 발행 커밋 직후) | **삭제됨 (2026-09-06, v1.11 발행)** |
  | v1.10 | `3a603da` (`Raw FITS Spec v1.10 -- 2026-09-05~06 제자리 개정 일괄`) | **붙은 적이 없다** — 운영자 판단으로 태그 없이 v1.11 로 넘어갔다 |
  | v1.11 | `ec9b3ec` (`Raw FITS Spec v1.11 -- 판올림 규약 명시 + 전수 검토 확인분 반영`) | **삭제됨 (2026-09-06, v1.12 발행)** — ⚠️ 태그가 판의 **첫** 커밋 `a55447f` 에 붙은 채 마지막 커밋으로 옮겨지지 않았다(위 규칙 위반) |
  | v1.12 | `8e3bdbf` (`Raw FITS Spec v1.12 -- 정합 수정 판올림`) | **삭제됨 (2026-09-12, v1.13 발행)** |
  | v1.13 | `ae3fbfe` (`Raw FITS Spec v1.13 -- 실기 라운드 반영`) | **삭제됨 (2026-09-24, v1.14 발행)** |
  | **v1.14** | `Raw FITS Spec v1.14 -- EQUINOX 실수형 + 전반 재검토 반영` (이 판의 마지막 커밋) | **`raw-spec-v1.14` (현행)** |

  ⚠️ **팀 알림 (2026-08-30)**: `raw-spec-v1.7`·`raw-spec-v1.8` 이 원격에서 삭제되고 `raw-spec-v1.9` 가 신설됐다 — 이미 받아 둔 쪽은 `git fetch --tags --prune --prune-tags` 로 정리해야 한다.

  ⚠️ **팀 알림 (2026-09-06)**: 같은 날 태그가 두 번 갈렸다 — `raw-spec-v1.9` 삭제 → `raw-spec-v1.11` 신설 → 그것도 삭제하고 **`raw-spec-v1.12` 신설**(v1.10 은 태그를 안 붙였다). 정리 명령은 위와 같다.

  ⚠️ **팀 알림 (2026-09-24)**: `raw-spec-v1.13` 삭제 → **`raw-spec-v1.14` 신설**.  ⭐ **매번 정리 명령을 칠 필요가 없게 — 저장소마다 한 번만**:

  ```bash
  git config fetch.prune true
  git config fetch.pruneTags true
  ```

  그 뒤로는 `git pull` 이 원격에서 지운 태그를 로컬에서도 지운다.  설정하지 않아도 **새 태그는 pull 로 따라온다**(받아 오는 커밋을 가리키는 태그는 git 이 함께 받는다) — 지운 옛 태그가 로컬에 남을 뿐이고, 그 태그도 제 판의 발행 커밋을 가리키므로 틀린 정보는 아니다.  ⛔ 다만 그 상태로 `git push --tags` 를 하면 지운 태그가 원격에 **되살아나니** 하지 말 것.  ⚠️ 같은 이름의 태그를 다른 커밋으로 **옮기는** 경우(위 `git fetch --tags --force` 절)는 이 설정으로 해결되지 않는다 — 판마다 새 이름을 쓰는 지금 규칙에서는 생기지 않는다.


## 준수 우선순위 (v0.7 검토 문서 0장에서 확립)

```
1  mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md    준거
2  mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py   L0 MEF 산출 주체 (v2.5.0)
3  mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md 참고 (converter 미러)
```

- **raw 쪽 기준선은 레거시 raw 실측 헤더**다. `ics_sim` 의 현재 출력은 미완성 구현이라 판정 근거로 쓰지 않는다.
- 레거시 **MEF** 헤더 33건은 배경지식이지 판정 근거가 아니다. 레거시 **raw** 헤더 1건만 근거다.
- **ICD 는 PRIMARY keyword 를 대부분 열거하지 않는다**(v4.3 은 §7.1 에 seed WCS 상태 카드만 표로 둔다). converter v2.2.0 이 만드는 카드 이름 210개 중 ICD v4.2 에 나오는 것은 36개뿐이고 174개(83%)가 없었다(원장 0.3절 — v2.5.0 은 286개로 늘었고 ICD v4.3 대조는 다시 뜨지 않았다). 그 침묵 구간이 곧 이 검토가 결정할 몫이다.
- 확정된 근거는 `../project_management/governance/DECISION_LOG.md` 의 **D-번호**이고, **이 폴더가 기대는 D-번호 전량은 규격 머리말 "결정 기록" 행이 정본으로 나열한다** — 여기에 다시 적지 않는다(같은 목록이 두 자리에 있으면 갈라진다).  ⚠️ 구 문장은 **D-011 · D-013 · D-016** 셋만 적어 D-014(관측일)·D-017(사이트 코드 넷)·D-018(노출 번호 공간)·D-019(`EXPID`)·D-020(사이트 판별)·D-021(돔 방위 셋 = redis)·D-022(저장 안 된 프레임은 번호를 안 먹는다)가 빠져 있었고, 폐지된 `ORIGNAME` 을 정체성 카드로 부르고 있었다.

## 🗄️ 지난 라운드 기록 — raw spec v1.4~v1.8 (2026-08-22~29)

> ⚠️ **여기부터는 경위 보존용이다** — 이어서 시작하는 자리는 위의 「✅ 현행 규격」 절이고, 이월 목록은 [README.md](README.md) 의 "판올림 이월 대기" 다.

### ✅ v1.7 발행 — 파일명 넷째 필드에 이름을 준다 `<DETID>` (2026-08-26)

**대기 안건이던 "꼬리 → `DETID` 필드" 를 이 판에서 처리했다** (운영자 지시).

2.2절 문법이 앞 세 자리만 이름을 갖고 넷째는 리터럴 `MK`/`NT` 였다. 이름이 없으니 D-019 를 쓰는 문서들이 그 필드를 **"꼬리"·"태그" 라고 제각각** 불렀는데, 값은 정확히 `DETID` 카드의 값이다.

```text
<SITE>.<YYYYMMDD>.<NNNNNN>.<DETID>.fits
```

- **본체** — 2.2절 문법 개정 + `<DETID>` 필드 설명 신설(값 = `DETID` 카드, 파일명에서 이 필드만 pair 상이)
- **딸림 17곳** — 2.3절 충돌 판별·5항 짝 이름 유도 · 5.9절 pair 규칙 · **DECISION_LOG D-019 항목 4·"잃는 것"** · **통합 문서**(LEECU 전달분) · README · 원장 v1.14. **규칙은 그대로고 부르는 이름만 정해졌다.**
- **`__reference/Detector_Ch_to_AmpID_Map_v1.0.txt` 삭제**(운영자) — 4자 채널 표기 이전 판 + `B-BOT` 오기라 혼동만 준다. v1.6 ⑪ 의 "v1.0 은 원본 기록으로 남는다" 를 **같은 판에서 철회**했다(없는 파일을 가리키는 문장이 남지 않게). 원본은 git 이력 `44ab878`~ 에 있다.
- ✅ **코드 따라가기 완료** — `ics-archon-v1.0-build` 의 `34cb177`("코드의 '꼬리' 를 DETID 필드로") · `dd57bbb`("'태그' 표기도 DETID 필드로") 두 커밋이 약 25곳을 옮겼다(`rawhdr`·`rawpair`·`emitter`·`rawcards`·시험 6·labtest·양쪽 SMC_CLAUDE). 2026-08-29 전수 확인 — 남은 `꼬리` 는 전부 **다른 뜻**이다(소켓 꼬리 바이트 · FITS 블록 꼬리 · GUI 가 남기는 빈 `TAPLINE`). **규격이 먼저 서고 코드가 뒤따르는 순서다.**

### ✅ v1.6 발행 — 노출 정체성 카드 개정 (2026-08-26)

**`ORIGNAME` 을 폐지하고 `EXPID` 를 세웠다** (운영자 확정).  값이
`<SITE>.<YYYYMMDD>.<NNNNNN>` 으로 **`DETID` 필드가 없어 pair 양쪽에서 같다.**

| 무엇 | 전 → 후 |
|---|---|
| 정체성 카드 | `ORIGNAME= 'KMTA.….123450.MK'` (pair 상이) → `EXPID   = 'KMTA.20260821.123450'` (**pair 동일**) |
| `FILENAME` comment | `'Filename assigned by ICS'` → `'FITS file name as written to storage'` |
| 5.9절 pair 상이 | **7장 → 6장** — 짝을 잇는 **단일 키**가 카드 추가 없이 생겼다(폐지된 `PAIRFILE` 의 역할) |
| 충돌 판별 | `FILENAME ≠ ORIGNAME`(직접 비교) → **`FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값 ≠ `EXPID`** |
| 견본 노출 번호 | `012345`/`012340` → **`123456`/`123450`** (D-018 로 6자리 전부를 쓰므로 맨 앞이 `0` 이 아닌 값). **견본 파일 이름도 함께 옮겼다** |

⚠️ **`EXPID` 는 2026-08-12 에 삭제됐던 이름을 되살린 것이다** (구판 v1.2
2.3.1절).  되살린 근거와 당시 삭제 근거의 대조는 규격 2.3절 폐지 목록 아래
경고에 적었다.  당시 실제 사고(`EXPID` 가 실수 카드로 저장돼 zero-padding
파괴, DevNote 11.13.2)는 **값이 `<SITE>` 접두로 시작해 숫자로 읽힐 여지가
없어** 구조적으로 막힌다.

⚠️ **`ics_sim`/`ics_archon` 코드 반영은 `ics-archon-v1.0-build` 몫이다** —
`rawcards.CARDS`·`PAIR_DIFF`(7→6) · `rawhdr.exposure_header` · `sequencer`
(`name_stem()` 호출이 빠지고 `orig_suffix` 를 그대로 싣게 된다) · `emitter` ·
labtest 내장본 · 시험 3종 · `_vendor`.  **여기서 고치면 그 브랜치와 충돌한다**
(D-017 때 겪은 그대로).

⚠️ **converter 파급 (LEECU 소관)** — `ORIGNAME` 을 읽던 코드는 `EXPID` 로
옮겨야 하고, 충돌 판별이 "두 값 직접 비교" 에서 "`DETID` 필드를 뗀 뒤 비교" 로 한 단계
늘어난다.  대신 **짝 탐색을 파일명 파싱 없이 `EXPID` 하나로** 할 수 있게 됐다.

### ⏳ 열려 있는 라운드 — raw spec **v1.5~v1.6** (5장 검토, 2026-08-25~)

**작업 자리가 `KMTNet-CEU-main` 워크트리(브랜치 `main`)로 옮겨졌다**(운영자). `ics-archon-v1.0-build` 쪽 `raw_fits_spec/` 은 손대지 않는다 — 두 곳에서 같은 파일을 고치면 머지가 지저분해진다.

**들어온 것**

1. **견본 헤더 comment 오타 2건 정정 (운영자 직접 수정)** — `Telesope`→`Telescope`(`ALT`) · `Acutator`→`Actuator`(`FASTAT`). 꼬리 `#EOF` 4바이트도 떨어져 **견본이 정확히 4×2880 = 11,520 바이트**가 됐다(종전 11,524 는 2880 의 배수가 아니었다). 구조 전수 검증 통과 — 144 레코드 · 값 135 + COMMENT 8 + END · 중복 keyword 0 · 바이트-9 위반 0 · 제어문자 0 · **MK↔NT 상이 정확히 7장**(5.9절 pair 규칙).
2. **메모장용 사본 신설** — `…MK/NT.fits.header.v1.0_REFTEXT.txt`: 카드마다 **LF**(CRLF 아님) + 끝에 `#EOF`, 11,669 바이트 = 144×81 + 5. **LF 를 걷어내면 정본과 바이트 동일**이다. 정본(연속 80칼럼)은 그대로 두고 보기용만 분리했다 — 정본 자체를 개명·변환했던 `…fits__header.…` 안은 폐기(되살리려면 `git checkout`).
3. **`Cn_*` 자리 순서 명세 — 5.6.1절 신설**(운영자 제시). 원장 7장이 "이 순서를 raw FITS spec 에 명세로 수록"으로 남겨 둔 지시를 닫았다(원장은 제자리 보강으로 그리 가리키게 했다). guide 8자리는 실기 대조 전이라 **OI-19** 신설.
4. 머리말 견본 카드 수 정정 — "143카드 = 값 135 + COMMENT 7 + END" → **144 레코드 = 값 135 + COMMENT 8 + END 1**(COMMENT 실측 8장).
5. **`QDATE`/`UDATE` 순서 규약 — 5.7.1절 신설 + 견본 시각 카드 4장 정정.** 08-22 판이 소스 정의와 **반대**로 되어 있었다. TC 원전(`TCSAgent/.../commands.c:1553`·`:2902`)이 `*QDATE` = TC 가 응답을 조립하는 순간, `*UDATE` = 텔레메트리 패킷을 마지막으로 받은 시각으로 정의하므로 **`UDATE` ≤ `QDATE` 가 구조적으로 필연**인데, 08-22 에 "`UDATE` 가 `QDATE` 보다 앞선다"를 결함으로 보고 뒤집었다. 레거시 실측(`KMTNk.20170209`: AUX −98 ms · TCS −703 ms)과 시뮬 구현도 같은 편이었다 — 그때 진짜 문제였던 것은 순서가 아니라 **`DATE-OBS` 와 4시간 어긋난 시각**이다. 간격 크기(300·523·753·797 ms)는 08-22 결정 그대로 두고 **부호만 뒤집었다**. 기준은 **`QDATE`**(운영자 확정) — 자리는 `DATE-OBS`(=`SHOPEN` 지시 시각) 전후이고 경로별로 갈린다. 출처 열도 `ICS code` → **`TCS relay`/`AUX relay`** 로 정정(원장 v1.14 348~351·374~377 과 정합 — 규격 쪽이 틀렸다). 셔터 재질의 **3초 → 1초**(운영자, OI-13).
6. **`Cn_*` 자리 표기 개정 (운영자 확정)** — `S<n>`(Slot) → **`Mod<n>`(Module)**. 2번 자리의 `M1` 은 **`Mod1` 의 오타**였다(운영자 확인). `Backplane` 을 뺀 아홉 자리가 한 체계로 통일됐고 원장 7장의 "Slot1 LVDS" 와도 정합한다. 종전 "표기 확인 대기 ①" 종결.
7. **`CHMAP_*` 토큰 3자 → 4자 (운영자 확정)** — `<chip><A|D><nn>`, 채널 **01–08 = `A` · 09–16 = `D`**. 견본 8장 · 4.5절 표 · 5.2절 행 반영. 80칼럼 예산이 8자 늘어 **견본 comment 를 `CCD output ch,…` → `CCD out ch,…` 로 줄였다**(값이 41자가 되어 종전 comment 가 2자 넘쳤다). chip 별로 A/D 가 깨끗하게 갈린다 — **M·T 는 TOP=D, K·N 은 TOP=A** 로, 부록 A 의 "K·N 조 180° 회전 장착" 추정과 같은 짝이다.
10. **`IMGSEC` 의 `B` 종결 — OI-17 잔여 ①·② 동시 해소 (운영자 확정).** 운영자가 **채널 번호 = OS 번호**를 확정해 잔여 ②가 닫혔고, 그로써 `채널 09–16 = OS9–16 = 위 half = 섹션 D` 가 데이터시트까지 이어진다. 데이터시트에 `B` 섹션이 없으므로 배선표의 `B-BOT` 16행(K·N 조 채널 09–16)은 **원전 없는 오기**로 판정돼 `D-BOT` 으로 정정했다. **OI-17 잔여는 ③(K·N 180° 회전 장착 확인) 하나만 남았다.**
11. **기계 정본 판 올림 — `Detector_Ch_to_AmpID_Map_v1.1.txt` (sub레포 루트).** 7번의 4자 채널 표기 + 10번의 `D-BOT` 반영. `__` 읽기 전용 규칙대로 `__reference/` 의 v1.0 은 **손대지 않고** 사본을 루트로 올려 고쳤다 — v1.0 은 원본 기록으로 남는다. 검산: 64행 · IMGSEC 네 값 16개씩 · `B` 0건 · AmpID 01–64 전량. 규격 머리말·4.5절 참조를 v1.1 로 옮겼다. **이로써 기계 정본과 규격 표의 갈림이 해소됐다.**
9. **사이트별 상수표 — 5.3.1절 신설 (운영자 확정, D-017 항목 6 으로 편입).** `TELESCOP` = CTIO `'KMTNet 1.6m #1'` · SSO `'#3'` · SAAO `'#2'` / `FPAID` = CTIO `'FPA#2'` · SSO `'FPA#1'` · SAAO `'FPA#3'` · KASI `'FPA#0'`. **견본은 손대지 않았다** — SSO 값 `TELESCOP='KMTNet 1.6m #3'`·`FPAID='FPA#1'` 이 표와 맞는다. 5.2절 `FPAID` 행과 5.3절 `TELESCOP` 행은 값을 빼고 5.3.1 로 위임했다.
   ⚠️ **망원경 번호와 FPA 번호는 세 사이트 모두 어긋난다** — CTIO 망원경 #1·FPA #2 / SSO 망원경 #3·FPA #1 / SAAO 망원경 #2·FPA #3. 오타로 보고 맞추면 검출기 귀속이 통째로 틀어져서 규격 5.3.1 과 D-017 양쪽에 경고를 박아 뒀다.
   **KASI `TELESCOP` = `'KMTNet 1.6m #0'`** (운영자 확정, 구 `'Sim'` 대체). KASI 만 망원경·FPA 가 둘 다 `#0` 인데 **우연이다** — 관측소 셋은 전부 어긋난다.
   ✅ **SSO 값은 레거시 실측이 뒷받침한다** — `KMTNk.20170209.044131.Rawheader.txt` 가 `OBSERVAT='SSO'` + `TELESCOP='KMTNet 1.6m #3'`. `rawhdr.py:514` 주석도 `#1`/`#2`/`#3` = CTIO/SAAO/SSO 로 적고 있었다. 첫 지시(SSO `#2`)가 이 둘과 어긋났던 것이고, 정정본이 저장소 증거와 맞는다.
   📌 **경위**: 첫 지시가 SSO `#2` · SAAO `#3` 이었고 그대로 넣었다가 **견본이 틀렸다고 판단해 `#3`→`#2` 로 고쳤는데, 운영자가 곧 정정**(SSO `#3` · SAAO `#2`)해서 되돌렸다. **견본이 처음부터 옳았다.** 견본은 이 대응의 유일한 바이트 기준물이므로, 표와 견본이 어긋나 보이면 **견본을 의심하기 전에 표를 먼저 확인할 것.**
12. **HK 카드 4장 폐지 (운영자 확정)** — `AIR_IN`·`AIR_OUT`·`GLYC_IN`·`GLYC_OUT`(standalone RTD 계통). 5.6절 **18장→14장**, 견본 값 카드 **135→131**. 견본은 **`END` 뒤 공백 레코드 4장**으로 채워 144 레코드·4×2880 = 11,520 바이트를 유지한다(FITS 표준 패딩). 5.10절 폐지 목록 등재. ⚠️ 이로써 **`standalone RTD readout unit` 공급 계통이 raw 헤더에서 완전히 비었다** — 원장 4.x 절에 기록했고, MEF 쪽은 아직 넷을 싣고 있어 **C-항목으로 올렸다**(통합 문서 Part 1).
8. **사이트 코드 (D-017) · 노출 번호 공간 (D-018) 개정 — 결정 원장 등재 완료.** `OBSERVAT` = `CTIO`/`SSO`/`SAAO`/**`KASI`**(`TESTBED` 폐지) · 접두어 = `KMTC`/`KMTA`/`KMTS`/**`KMTK`**(`KMTT` 폐지) · 번호 공간 `000000`–**`999999`**(되감음 1000000→0, 충돌 루프 상한 1000000회).

**✅ `main` 쪽 반영 완료 (2026-08-25) — `ics_archon` 만 브랜치로 남는다**

운영자 지시로 **`ics_sim` 을 포함한 `main` 전체에 이 라운드를 반영했다.** 종전에 "머지 때 함께"로 미뤄 두었던 것을 앞당긴 것이다.

| 반영처 | 내용 |
|---|---|
| `ics_sim/ics_sim/rawpair.py` | `OBSERVAT`·`ORIGIN_OF` 넷째 자리 → `KMTK:KASI` · `TESTBED_SITE` → **`KASI_SITE`** 개명 · `normalize_site()` · `OBSDATE_SHIFT_MIN` |
| `config.py` | `_SITE_TELID` `testbed`→`kasi` · `aux_requery_after_shopen` **3.0 → 1.0** |
| `state.py` | `site_code` 기본값 `KMTK` · **`EXPNUM_SPACE = 1_000_000` 신설**, `advance()` 가 되감는다 (D-018) |
| ~~`siteid.py`~~ | `BENCH_SITE = 'KMTK'` — ⚠️ **그 파일은 2026-08-24 에 브랜치 `ics-archon-v1.0-build` 에서 삭제됐다**(D-015 폐기, D-020 대체). **`main` 트리에는 아직 남아 있다** — 합류 대기이고, 이 행은 그때 `main` 쪽에 넣은 값의 기록이다 |
| `app.py` | `KASI_SITE` 참조 · 경고 문구 |
| `rawhdr.py` | `DEWAR_CARDS` 에서 **폐지 4장 제거** · `VERIFIED_SITES` 에 **`KMTK: TELESCOP='KMTNet 1.6m #0'`** 추가 · TELESCOP 대응 주석 |
| `hardware/base.py` | 폐지 카드를 예시로 쓰던 주석 |
| `ics_sim.ini` | `[site.testbed]`→**`[site.kasi]`**(+`telescop`) · telid 주석 · IP 판정 주석 · 재질의 1.0 |
| 시험 3종 | `test_raw_header.py`·`test_site_id.py`·`test_config_site.py` — `KMTT`→`KMTK`, KASI 좌표 시험이 `TELESCOP` 은 값이 있음을 확인하도록 개정 |
| 문서 | `raw_fits_spec/README.md`(배선표 v1.1) · 원장 v1.14(`OBSERVAT` 행 · 폐지 4장 취소선 · CHMAP 4자) · 통합 문서 v0.6(C-항목 3건) · `DECISION_LOG`(D-011·D-014·D-015·D-016 에 개정 포인터) · `ICS_DEPLOYMENT_CHECKLIST` · `project_management/README` · `mef_fits_spec/README` · `ics_sim/DevNote`(11.15·11.16 절 머리에 갱신 포인터) · `ics_sim/SMC_CLAUDE` |

⚠️ **검증 한계** — 이 환경에 `pytest` 가 없어 **시험 모음을 돌리지 못했다.** 대신 모듈을 직접 import 해 상수·`site_header()` 4사이트·`DEWAR_CARDS`·`advance()` 되감음(999999→000000)·기본값을 확인했고 전 파일 문법 검사를 통과했다. **`pytest` 가 있는 자리에서 한 번 돌릴 것.**

⚠️ **`ics-archon-v1.0-build` 머지 때 충돌한다** — 그 브랜치가 같은 파일들을 이미 고쳤다(`3bf2d73` 사이트 판별을 `OBSERVATORY` 로 · `9545f64` ics_sim v0.2.0). 특히 `rawpair.py`·`config.py`·`state.py`·`siteid.py`(브랜치에선 삭제)·시험 3종이 겹친다. **머지는 `main` 쪽 값(`KMTK`/`KASI`/1.0/`EXPNUM_SPACE`)을 정본으로 삼아 해소한다.**

**✅ 후속 넷 — `ics_archon` 브랜치에서 완료 (2026-08-26)**

이 라운드가 **`main` 에 없는 코드**에 걸리는 일감을 넷 만들었고, `ics-archon-v1.0-build` 가 `main` 을 머지로 받으면서 전부 처리했다 (그 브랜치 커밋 — DevNote **11.28**).

| # | 일감 | 결과 |
|---|---|---|
| 1 | 견본 오타 2건 + **시각 카드 4장** + **`CHMAP` 8장** + **폐지 4장 제거·공백 패딩** 을 기계 사본에 반영 | ✅ 사본 3곳 전부. `#EOF` 제거로 견본이 4x2880 = 11,520B 가 되면서 **labtest 의 `build_header` 가 헤더 조립을 거부**했다 — 정렬 단정만 있고 패딩이 없었다. 같은 패딩을 넣었다 |
| 2 | **D-017** 사이트 코드 · **D-018** 번호 공간 · 재질의 1초 · `FPAID` 사이트 유도 | ✅ ⚠️ **"`main` 의 `ics_sim` 을 그대로 가져오면 된다" 는 이 브랜치에 맞지 않았다** — `main` 쪽은 IP 판별 구판이라 `siteid.py` 를 되살리게 되고, `state.EXPNUM_SPACE` 도 같은 뜻의 두 번째 상수가 된다. **값만** 가져오고 구조는 브랜치 것을 지켰다. `FPAID` 사이트 유도는 `main` 에 없어서 브랜치에서 새로 구현했다(`rawhdr.fpaid_of()`) |
| 3 | 폐지 4장 · `CHMAP` 4자 · `TELESCOP`/`FPAID` 표 | ✅ + **labtest 사본 표류 감시 시험 신설** (`ics_archon/tests/test_labtest_spec_copy.py`, 5항목) — 사본 셋 중 이것만 아무도 안 보고 있었다 |
| 4 | 규격 참조 판올림 | ✅ `README.md`·`README_labtest.md`·`SMC_CLAUDE.md`·labtest 머리말 |

**표에 없었는데 나온 것 — `Cn_TEMP` 자리 수 (5.6.1절).** 구현이 잠정 **5자리**(`BACKPLANE_TEMP`+`MOD5`~`MOD8`)였는데 5.6.1절이 science **10자리**를 확정했고, **견본 pair 의 `C1_TEMP` 는 처음부터 10개**였다 — 잠정안이 견본과 갈려 있었다. 바이트 대사가 못 잡은 이유는 그 시험이 **견본 값을 그대로 되먹여서** 실기 파서(`parse.telemetry_of`)를 지나지 않기 때문이다. 정본을 `rawhdr.TEMP_SLOTS` 에 세우고 두 경로를 잇는 시험을 새로 붙였다.

검증: `ics_sim` **321 통과** · `ics_archon` **145 통과** · **견본 v1.5 pair 바이트 단위 재현**(MK·NT, 불일치 0).

✅ **배선표 갈림 해소 (2026-08-25)** — `__reference/` 읽기 전용 규칙대로 v1.0 은 손대지 않고 사본을 sub레포 루트로 올려 **`Detector_Ch_to_AmpID_Map_v1.1.txt`** 로 고쳤다(4자 채널 토큰 + `IMGSEC` `D-BOT`). 규격 머리말·4.5절·`raw_fits_spec/README.md` 의 참조를 v1.1 로 옮겼다. 구 v1.0 은 원본 기록으로 `__reference/` 에 남겼다 — **그것을 읽는 외부 도구가 있으면 v1.1 로 옮겨야 한다.** ⚠️ **그 v1.0 은 v1.7 에서 삭제됐다**(구 표기·`B-BOT` 오기가 혼동만 준다 — 아래 v1.7 절). 원본은 git 이력 `44ab878`~ 에 있다.

✅ **converter 정규식 반영 완료 (2026-09-04)** — `^(KMTC|KMTS|KMTA|KMTK)\.` (converter v2.4.0) · `SITE_PREFIX`/`OBS_PREFIX` `KMTK`/`KASI` · ICD v4.2 §2.1 갱신. 번호 공간(D-018)은 정규식이 `\d{6}` 이라 영향 없다.

**견본 오타 정정이 걸린 코드 사본 3곳** (종전 기재)

견본은 **바이트 정본**이고 이를 그대로 베낀 기계 사본이 셋 있다. 오타 정정을 따라가지 않으면 대사 시험이 깨진다 (실측: `ics_sim/tests/test_raw_draft.py` **3 failed**).

| 파일 | 줄 |
|---|---|
| `ics_sim/ics_sim/rawcards.py` | 130–131 · 158–159 (오타 + "고치면 바이트 대사가 어긋난다" 주석 2줄도 함께) |
| `ics_archon/ics_archon/_vendor/ics_sim/rawcards.py` | 위와 바이트 동일 사본 |
| `ics_archon/archon_kmtnet_labtest_v1.1.bigbuf.py` | 504 · 531 (`# 견본 원문` 주석 포함) |

**셋 다 `main` 에 없다** — `rawcards.py` 를 들여온 커밋 `9545f64`(ics_sim v0.2.0, 템플릿 주도 재편)가 `ics-archon-v1.0-build` 전용이고 `main` 에는 `ics_archon/` 폴더 자체가 없다. 그래서 **이 라운드를 main 에 올린 뒤, 그 브랜치가 main 을 머지로 받는 시점에 함께 고쳤다** (2026-08-26 완료). ✅ 이제 그 세 사본은 **시험이 지킨다** — `_vendor` 는 `test_vendor.py`, labtest 내장본은 신설 `test_labtest_spec_copy.py` 다.

`#EOF` 제거는 안전하다 — `ics_sim/tests/test_raw_draft.py:67` · `ics_archon/tests/test_fitswrite.py:46` 둘 다 조건부로 뗀다. `__reference/` 의 레거시 실측 헤더 20여 장은 **사실 기록이므로 오타를 그대로 둔다**.

**확인 대기 없음 — 이 라운드는 닫혔다**

① ~~`Cn_TEMP` 2번 자리 표기~~ → **닫힘** (위 6번) — `M1` 은 `Mod1` 오타였다. 잔여 없음.

② ~~태그~~ → **완료 (2026-08-25).** 규칙(그 판의 마지막 커밋)·보존 방침(현행 판만) 확정 후 실행까지 마쳤다 — `raw-spec-v1.5` 를 `13e02b2` 로 옮겨 원격에 강제 갱신하고 `raw-spec-v1.4` 는 로컬·원격에서 삭제했다. 위 「태그 규칙」 절 참조. ⚠️ **태그가 옮겨졌으니 팀은 `git fetch --tags --force` 가 필요하다.**

③ ~~`IMGSEC` 의 `B` → `D`~~ · ~~배선표 사본 처리~~ → **둘 다 닫힘** (위 10·11번). 권고했던 ⓑ 방식(사본을 루트로 올려 두 건 동시 처리)으로 진행했다.


### 🏁 최종 2 — raw spec **v1.4** (운영자 1~4장 검토 반영, 2026-08-22)

- **반영 4건**: ① **2.5절 삭제**(ICS `Wrote` 통보 규약 — 취득 SW 소관, 정본은 `../ics_sim/DevNote.md` 3.2. raw 사용자용 "`LASTFILE` 은 실재 경로 아님"만 2.3절 5항으로 흡수) ② **4.1 X overscan `RRRRLLLL` 확정** — 실제 획득 자료 육안 확인(운영자), 경고 문구 삭제 → **OI-15 종결**(통합 문서 §3·§5 도 종결 표시) ③ **4.2 다이어그램에 BOT/TOP Y overscan 84/84 분리** (타일 규약 층 — 물리 clocking 분배는 OI-4 로 유지) ④ **4.4 `Amp 범위` → `AmpID 범위`** + 값을 MEF AmpID(01–64) 기준으로 정합(구 `1–8`/`9–16` 은 chip 로컬 번호였다) + half 판정식.
- **견본 헤더 시각 카드 정정 (2026-08-22, 운영자 지시)** — `TCSQDATE`/`AUXQDATE` 를 `DATE-OBS` 직후 수백 ms(+300 · +523 ms), 각 `UDATE` 를 해당 `QDATE` +0.5~1 s(+0.753 · +0.797 s)로 잡았다. **운영 개념: 셔터가 열리는 시점 전후에 TCS/AUX 를 질의해 정보를 얻는다.** 종전 값은 레거시 실측을 베껴 `16:34`(DATE-OBS 와 4시간 어긋남)였고 **`UDATE` 가 `QDATE` 보다 앞서** 있었다. MK·NT 동일(5.9절). ⚠️ **이 순서 규약은 아직 규격 본문에 없다** — 5장 검토 때 5.7/5.8 절에 명문화할 것(견본만으로는 근거가 아니다).
- ⚠️ **5장 이후는 아직 검토 전** — 팀 협의 후 다음 판에서. 그때 함께 볼 것: **QDATE/UDATE 순서 규약 명문화(위 항목)** · 4.5 amp 표의 `IMGSEC` `B` 표기(OI-17 잔여) · 견본 헤더 날짜 불일치(아래 5번) · DevNote 11.19 의 목 확인 2건.
- ✅ **버전 참조 갱신 완료 (2026-08-22, 그 세션이 처리)** — `ics_sim`·`ics_archon` 의 규격 파일명 참조 6곳을 `_v1.4.md` 로, **삭제된 2.5절** 인용 9곳을 `DevNote 3.2`(통보 규약 정본)로, **OI-15 종결** 반영(`XOSC_PATTERN`·`test_geometry_vs_converter.py` 의 "상충 증거" 경고 제거). ⚠️ **견본 개명이 `test_raw_draft.py` 의 바이트 대사 6개를 조용히 skip 시키고 있었다** — 경로 하드코딩 → **glob 탐색**으로 바꾸고 못 찾으면 skip 이 아니라 **실패**하게 했다(다음 개명에는 안 깨진다). 경위는 `../ics_sim/DevNote.md` **11.21**.
- (원문) **남은 버전 참조 갱신 (다른 세션 소관)**: `ics_sim/{rawhdr,rawpair,hardware/archon}.py` · `ics_sim/tests/{test_raw_header,test_raw_pair}.py` · `ics_archon/{README.md,archon_kmtnet_labtest_v1.1.bigbuf.py}` 의 머리말이 아직 `…_v1.3.md` 를 가리킨다 — 그 세션이 편집 중인 파일이라 건드리지 않았다. **규격 내용 변경은 없다**(1~4장 수정은 구현에 영향 없음: 2.5절은 애초에 DevNote 소관, 4.1/4.2/4.4 는 문서 표현). 커밋할 때 `v1.4` 로 바꿔 주면 된다. ⚠️ **다만 견본 헤더 파일명이 `KMTA.20260821.…` 로 바뀌었으므로**(아래 5번) `test_raw_draft.py` 의 `DRAFTS` 경로는 **갱신하지 않으면 시험이 파일을 못 찾는다** — 이건 문구가 아니라 동작에 영향이 있다.

### 🏁 최종 (raw spec v1.3 발행 — 이 검토 사이클의 종점)

- **raw spec v1.3 발행 (2026-08-22)** — 구 Pair_Spec v1.2 를 `KMT_CEU_Raw_FITS_Specification` 으로 개명하고 전면 재작성(운영자 지시). 구성: 1 목적 · 2 pair(파일명 D-011/D-014 · **충돌·정체성 D-016** · Wrote D-010) · 3 파일 구조 · 4 geometry(**4.3 포장 규범 조항** — 고정 `CAMVER`+`CTRLxCFG` · **4.5 amp 전수 표 64행** — 기계 사본 = `__reference/Detector_Ch_to_AmpID_Map_v1.0.txt`) · 5 헤더 keyword(초안 v1.0 pair 의 값 카드 135장 전량, 블록별 표 + 5.0 정책/sentinel/문자열 형/ICS INI 규칙 + 5.9 pair 규칙 + 5.10 미기재 경계) · 6 MEF·파이프라인 연동 요점 · 7 검증 체크리스트 · 8 OI(신설 15~18 포함) · 10 이력. 배경·경위는 전부 원장 v1.13·통합 문서 링크로 처리(간결 원칙 — 운영자 지시).
- **통합 문서 v0.6** — raw spec 발행 정합: Part 2 를 파급 요약으로 축약(정본 이동 완료), 구 규격 참조 전부 현행판으로 교체. v0.5 는 `archive/`.
- **다음 사람이 할 일 (우선순위 순)**:
  1. **목 검토**: raw spec v1.3 전문 — 특히 4.5 amp 표(IMGSEC A/B/D 열), 5장 카드 표의 값·출처, 8장 OI 번호 부여(15~18 신설).
  2. **LEECU 전달**: 통합 문서 v0.6 Part 1 (C-항목·미결 4건) + raw spec 6장.
  3. ~~**ics_sim 구현 일감** — v1.3 정렬~~ — **✅ 완료 (2026-08-22, ①~⑤ 전량 + 대사 테스트).** 헤더 층이 **템플릿 주도**로 재편됐다: `ics_sim/ics_sim/rawcards.py` 가 초안 v1.0 pair 의 기계 사본이고, `tests/test_raw_draft.py` 가 견본 값 역산 → **바이트 단위 재현**(MK·NT 불일치 0)을 대사한다. D-016(선검사·되감음·상한·카운터 동기화), 신설·폐지 카드 전량, `fits_shape = spec` 실물 기하 이미지 생성 + **converter end-to-end L0 MEF 생성 검증**까지. 같은 날 `ics_archon/archon_kmtnet_labtest_v1.1.bigbuf.py` (실험실 취득 스크립트)에도 v1.3 을 적용했다(내장 템플릿 동일 원천). 경위·판단은 `../ics_sim/DevNote.md` **11.19** — **목 확인 대상 2건**(RADECSYS 결측 기본 `'ICRS'` · ENS1~7 결측 sentinel `'NC'`)이 거기 있다.  ✅ **①(`RADECSYS`)은 이 라운드에서 닫혔다** — TC 가 그 필드를 아예 안 보낸다는 것이 원전으로 확인돼(TCSAgent 트리 0건) 5.7절 출처를 `TCS relay` → **`ICS code`** 로 정정하고 `'ICRS'` 고정을 명문화했다(원장 v1.18 3.4절과 정합).  ②(ENS1~7)는 아직 열려 있다.
  4. **실측·확인 항목**: OI-15(4:4 vs 5:3 — 검증 표본으로 즉시 가능) · OI-16(Radionode 포맷 — 구칭 Tapaculo) · OI-17(**부분 종결** — 데이터시트 확보·부록 A 신설, 잔여 = IMGSEC `B` 표기 해명·채널↔OS 대응·K/N 회전 장착 확인) · OI-18(NT CCDTEMP).
  5. ✅ **견본 헤더의 날짜 불일치 — 해결 (2026-08-22, 운영자 지시)** ⚠️ *번호는 v1.6 에서 `123456` 으로 옮겨졌다 — 파일명·카드 정합 규칙 자체는 그대로다*: 견본 파일명을 **`KMTA.20260821.012345.{MK,NT}.fits.header.v1.0.txt`** 로 바꾸고 raw spec 2.3절 예시도 맞췄다(카드가 규격상 옳았다). 이제 파일명 == `FILENAME` 카드다. ✅ `ics_sim`/`ics_archon` 쪽 대응은 **그 세션이 처리 완료** — `test_raw_draft.py` 는 경로 하드코딩을 **glob 탐색**으로 바꿔 다음 개명에도 안 깨지게 했다(위 항목 참조). `archive/` 에 있던 옛 이름 백업 사본 2장은 **삭제된 상태로 커밋에 포함**됐다(운영자 archive 정리 — 루트에 현행 견본이 있어 중복이었고, 옛 이름 판은 git 이력에 남는다). 아래는 발견 당시 기록:
  ~~⚠️ **견본 헤더의 날짜 불일치 (2026-08-22 발견, 목 판단 필요)**~~ — 견본 두 장의 `FILENAME`/`ORIGNAME` 이 `KMTA.**20260821**.012345.{MK,NT}` 인데, **견본 파일 이름과 raw spec 2.3절 4항의 예시 블록은 `20260818`** 이다. 같은 값이 세 곳에서 두 날짜로 갈렸다. 규격으로 판정하면 **카드가 맞다** — 견본 `DATE-OBS='2026-08-21T12:34:56.789'` 에 SSO 보정 −1:30(2.2절)을 적용하면 관측일이 `20260821` 이므로, 틀린 것은 **견본 파일 이름과 2.3절 예시**다. 2.3절 4항이 `FILENAME` 을 "실제 저장명"이자 "아카이브·DTS·색인의 유일 키"로 규정한 만큼 그 규칙의 유일한 바이트 기준물이 스스로 규칙을 깨고 있는 셈이고, 받아 구현하는 쪽(LEECU)이 "파일명과 `FILENAME` 이 달라도 된다"로 읽거나 반대로 불일치를 충돌 신호로 오독할 여지가 있다(실제 충돌 신호는 `FILENAME ≠ ORIGNAME` 이고 `012345` vs `012340` 으로 정상 표현돼 있다). **어느 쪽으로 맞출지는 정본 소관이라 손대지 않았다** — 견본 파일명을 `20260821` 로 바꾸고 2.3절 예시를 맞추거나, 카드·`DATE-OBS` 를 `20260818` 기준으로 되돌리거나 **셋이 같아야 한다**. `ics_sim/tests/test_raw_draft.py` 는 견본 값을 되먹여 바이트 대조하므로 이 불일치를 구조적으로 못 잡는다.
- **데이터시트 확보 (2026-08-22, 운영자)** — `__reference/CCD290-99 datasheet (V2 - Aug 2016).pdf`. raw spec **부록 A** 로 대응 정리: `IMGSEC` 의 `A`/`D` = e2v image section(아래/위 half) 확인, **레거시 `PRESCANX=27` 의 원전**(레지스터 1152 active + 27 prescan) 확인, 독출 방향은 ACF 소관(OI-3 유지). **시사점**: K·N 조의 `A-TOP` 은 die 180° 회전 장착을 시사한다.  ⚠️ 종전에는 이것을 레거시 `AMPSEC` 의 M/T vs K/N 패턴과 "같은 짝" 으로 묶어 함께 확인하려 했는데, **그 패턴은 레거시 계통의 것이라 신규에 적용되지 않는다**(`OI-15` 종결 2026-08-22).  짝을 풀고 나면 남는 것은 **`OI-17` 잔여 ③**(K·N 조가 M·T 조와 `IMGSEC` 체계가 다른 이유) 하나이고, 그것은 데이터시트·장착 도면으로 볼 일이지 레거시 자료로 볼 일이 아니다.

### 2026-08-22 확정분 · 최신 (확인 요망 6~11 전량 종결 + D-016 등재 = v1.13)

- **재가 3건 종결(2026-08-22, v1.13 반영)** — ⑥ `CTRL1ID`='KMTA-SCI-101' 포맷 + **ICS INI 카드 전부 ini 편집 가능(운영자 지시)**: ics_sim 에 `[camera]`(DETECTOR/CAMVER/INSTRUME) · `[controllers]`(CTRL1*/CTRL2* + CTRLnCFG 신설 카드) · `[site] origin` 추가, INI > 백엔드 우선. **ORIGIN 유도 수정**(고정 'KASI' → 관측소 raw=관측소명·테스트베드=KASI, v1.7 확정 정렬) · **INSTRUME 기본 '<SITE> 18k CCD'**. ⑦ "– 철회" = 구 이름 계승의 철회(라벨 문구 교체). ⑧ TIMVER/BIASVER/CLKVER = CTRLxCFG 귀속 + **CAMVER = HW·성능 세대 참조점** / XTALKVER·REFVER·CATVER = **Pipeline calibration DB 소관**(값 칸 표기 교체) — **계층 규칙: raw 미기재 · L0 수록은 pipeline 팀 판단 · L1 필수**(통합 문서 §4 등재).
- **NT 초안 헤더 생성** — `KMTA.20260821.012345.NT.fits.header.v1.0.txt`: pair 상이 7장(DETID·CHMAP 4장·FILENAME/ORIGNAME)만 상이, 미확인분은 MK 동일(CCDTEMP comment "M" 포함).
- **확인 요망 10 종결(2026-08-22, v1.13)** — PRESCN 은 **키워드 변경 계승**: 레거시 `PRESCANX` → `PRESCNX`/`PRESCNY`(값 0), `OVRSCNX`/`OVRSCNY` 확정 후 자리수를 맞춘 개칭(운영자). 6장 = 개칭 계승 표기(DSTEL 선례) · 7장 `PRESCNX` `X`→`O` 정정 — 초안 v1.0 과 3자 정합.
- **확인 요망 11 종결(2026-08-22, v1.13) — 전량 종결 달성**: 규격 버전 카드(`RAWVER`/`RAWPROD`)는 **미도입 확정** — 규격/구성 버전은 **`CAMVER`(HW)·`CTRLxCFG`(FW/설정)·`DETID`·`CHMAP_*` 조합**으로 전부 파악(운영자). 귀결: V1 포장 규범 조항의 고정 대상 = `RAWVER` → **`CAMVER`+`CTRLxCFG`**(7장 ROWORDR 행), MEF `GEOMVER` 동반 범프 문구도 갱신(통합 문서 §3).
- **D-016 등재 완료(운영자 승인 2026-08-22)** — 충돌 번호 증가·`FILENAME`/`ORIGNAME` 정체성·`UNIQNAME` 폐지가 `DECISION_LOG.md` 에 Accepted 로 등재. D-010/D-012 삼총사 문구 개정 표시, README 구 문단 교체, 통합 문서 Part 2 상태 승격. **✅ V1 재작성 착수 조건 완성** — 다음 작업 = Pair Spec V1 재작성([[project-pair-spec-rewrite]] 페이로드: 포장 규범 조항(CAMVER+CTRLxCFG 고정) · amp 전수 표(검증상태 열) · 데이터시트 부록 · 기계 사본 · 충돌 처리 절 · 5장 확정분).

### 2026-08-22 확정분 (확인 요망 9 확정 = v1.12 · 초안 v1.0 승격)

- **확인 요망 9 종결 — HK 온도·습도 카드는 문자열 계승** (레거시도 문자열 `'-103.16'` · converter pass-through — 아카이브 형 통일). 표기: HK ±소수 2자리(`'+16.78'`), FSA 2장은 ENS식 잠정(소수 1자리, Radionode(구칭 Tapaculo) 원값 포맷 확인 후 최종 — 실기 확인 항목). **측정불가 sentinel = 온도·습도 전 카드 `'-999.99'` 단일값** (기각: `-99.99` 는 CCDTEMP 냉각 램프 통과값, 습도 `0.00` 은 유효 측정값). ics_sim 반영: `format_temp()` 신설 + thermal_header 문자열 전환 + 테스트 교체.
- **초안 헤더 v1.0 승격** (운영자) — `KMTA.20260821.012345.MK.fits.header.v1.0.txt` 를 폴더 루트로, 내용은 마지막 커밋본과 동일(143카드, diff 0). `__review/` 폐지, archive 는 v1.8~v1.11 만 유지(그 이전 판·docx·초안 이력은 외부 백업).

### 2026-08-22 확정분 (운영자 5차 개정 + 확인 요망 4·5 확정 = v1.11 로 닫힘)

- **돔 Source 전면 변경** — 계승 6장 + `DSAZ`/`DSTELALT`/`DSTELAZ` 가 `AUX relay` → **`TCS relay or REDIS*`**, `DALTERR`/`DAZERR` 는 **`ICS calculation`**. newTCS 전환으로 dome shutter control 이 TCS 에 편입 — 초안 DS 블록도 TCS 절로 이동(3.6절, 절명에서 "AUX" 제거).
- **확인 요망 1~5 종결** — ① chiller 재삭제 ② `FSATEMP`/`FSAHUM` 반영 ③ 돔 4장 반영(모두 초안 v0.3.7 전수 대사 검증) ④ **`EXPTIME`/`LEDFLASH` 정수형** — `EXPTIME` 은 소수점 있으면 실수형, **`LEDFLASH` 는 [ms] 로 단위 변경**(D-013 "초 유지" 번복 — comment 에 단위 명시, `ics_sim` ms÷1000 제거) ⑤ **`ICSBUILD` = `v<버전>:<빌드일시>Z`**(프로그램명 제거 — 식별은 `DATASRC`, `ics_sim` `build_id()` 개정 + `PROGRAM` 상수 삭제 + 테스트 교체, 전체 325 통과). **ics_sim 변경분은 v1.11 문서 배치와 함께 커밋(운영자 지시)**.
- **문서 통합 (운영자 지시)** — MEF_Impacts v0.4 + Numbering v0.2 → **`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md`** (Part 1 = MEF 개정 요청 / Part 2 = 번호·정체성). 구 raw↔MEF 키워드 대응표의 잔여 미결 4건(`NCTRL`·`CTRLID` 개칭·`SATURAT`/`SATLEVEL`·`DATASRC`/`CTRLnCFG` MEF 목적지)을 Part 1 §6 으로 이관 — **그 문서는 흡수 완료로 폐기됐다(운영자 재가 2026-08-22)**. ⚠️ 처음엔 archive 로 옮긴 것으로 기록했으나 실제로는 삭제됐고, 판정 준거는 2026-08-23 에 Header_and_Refs **0장**으로 편입했다(원문은 git 이력 `4782c78^`).

### 2026-08-22 확정분 · 추가 (운영자 4차 개정 = v1.10 으로 닫힘)

- **`CHKIMG` · `CHKIMG_C` → `X`** ("Pipeline 에서 판별하는 대상") — **도입/계획 판정 미정 0 달성** (구 대응표의 검토 항목 9 = 도입 판정 미정분, 전량 종결).
- **6장 `DSTEL` → `O` (`DSTELALT` 로 변경 적용)** — 6장 마지막 빈칸 소멸.
- **`OVERSCNY` 개명(`OVRSCNY`) 후속 지시** — 위험 사유와 개명을 V1 규격·MEF Impacts(ICD 개정 후보)에 수록. ※ 운영자 원문 "OVRSCANY" 는 `OVRSCNY` 오탈자로 교정 반영(확인 대기).
- 남은 것: **확인 요망 11건 일괄 판정 + D-등재** → 이 둘이 닫히면 V1 재작성 착수.

### 2026-08-22 확정분 (운영자 3차 개정 = v1.9 로 닫힘)

- **7장 도입 여부 전면 판정 완결** — 도입 `O` 20+ 장 · 미도입 `X` 28+ 장, **미정은 `CHKIMG` · `CHKIMG_C` 2장뿐**.
- **`RDMODE` 개명 도입** — raw 독출 속도 모드 선언. MEF `READMODE`(`'64AMP'`, 구조 선언)와 이름이 갈라져 **값 충돌 미결이 종결**됐다 (MEF Impacts v0.4 3장에 해소 표시).
- **`BCKTEMP` → `Cn_TEMP`/`Cn_VOLT`/`Cn_CURR` 확장** — 컨트롤러별 텔레메트리 3종(모듈 순서 명세는 spec 수록 예정). MEF `VOLTINFO`/`TELEMETRY` 공급원 **C-후보**로 연결 (MEF Impacts v0.4 1장).
- **`CAMVER` 신설** — 카메라 시스템 버전 선언.
- **미도입 `X` 확정** — `CTRLTAG` · `PAIRFILE`(pair 식별은 `FILENAME` `DETID` 필드 `.MK`/`.NT` 로 충분) · `OSCNPATT` · `RDDIRT`/`RDDIRB` · `MIDOSC*` · 전압 색인 계열 · `RAWVER`/`RAWPROD` · `FSADEW`/`FSAALRM`. → Numbering v0.2 · MEF Impacts v0.4 에 반영 완료.
- **확정 초안 v0.3.6** — 돔 블록이 TCS 절로 이동, 카드 8장 추가.
- **미결 갱신** — ⚠️ 확인 요망 **11건**(신규: 10번 `PRESCN` 모순 · 11번 `RAWVER` 공백 포함, v1.9 머리말) · `CHKIMG` 2장 판정 · 충돌 처리/정체성의 D-등재.

### 2026-08-21 v1.8 확정분 (운영자 v1.7_revision 반영으로 닫힘)

- **3장 `Raw Archon` 열 전면 판정** — 3.2~3.7 전 행 O/X. `X`: `DARKTIME`(=`EXPTIME` 파생) · `TSHOPEN` · `TSHSHUT` · `CHSTAT` · `HEMODE` · `NPHLINES`. ⚠️ `TSHOPEN` 폐지 → **MEF `UT` 조립 원천 교체** C-항목, `DARKTIME` → `EXPTIME` 파생 C-항목 (MEF Impacts v0.3).
- **컨트롤러 블록 재편** — `CTRL1CFG`/`CTRL2CFG` 신설(ICS INI, 예 `KMTA_SCI_101_R2609.1.acf`), `CTRLxID`/`CTRLxSN` 도입 확정 + 실값(`KMTA-SCI-101/-102` · `STA-0288/-0289`, `__reference/Archon_Unit_Info.txt`), 펌웨어·버전 문자열 6장은 `CTRLxCFG` 귀속 `X`. 양쪽 raw 에 2대분, guide 는 `CTRL1xx` 한 벌, `CTRLnxx` 확장 규약.
- **HK 재구성** — `CCDTEMP` 실측 대표 전환("CCD temperature M", ICG RTD) · `CCDTEMP1/2` 후보 제외 · `DEWPRES` 문자열 `x.xxe-x` + sentinel `9.99e-9` · 신설 `DMPTEMP`/`WALLBRD`/`HEBOX` · `AIR_*`/`GLYC_*` = standalone RTD readout unit · `TCSTIME` 신설(시각계 분리). **`ics_sim` `rawhdr.py` 의 HK 부분은 동기화 완료** — 노출·컨트롤러 블록 재편은 백로그(`../ics_sim/SMC_CLAUDE.md`).
- **⚠️ 확인 요망 9건 중 1번(CHSTAT)은 해소** — 운영자가 초안에서 chiller 4장(`CHSTAT` `CHOP` `CHSET` `CHPROC`) 삭제(2026-08-21), 블록 전체 미도입 확정. **남은 8건**(v1.8 머리말) — FSA 4장/돔 4장(O vs 초안 부재) · EXPTIME 형(Integer vs `0.0`) · ICSBUILD 형식(프로그램명 유무) · CTRLxID 값(`-01` vs `-101`, 후자 채택) · `– 철회` 라벨 해석 · XTALKVER 3장 귀속 표기(caldb 유지) · HK 온도 형(문자열 vs 실수).
- 미세 미결 갱신: `READMODE` 는 초안이 카드를 뺐다 — **→ v1.9 에서 `RDMODE` 개명 도입으로 종결** · `ORIGNAME` 은 v1.7_revision 에서 이의 없음 — 확정 수순(D-등재 대기).

### 2026-08-21 확정분 (직전 세션과 목의 검토로 닫힘)

- **Detector/Amplifier 블록 확정** — `DETID`(레거시 계승, 값 'MK'/'NT' 재정의, comment "Detector pair in this raw FITS file") · `DETECTOR` · `PIXSIZE`/`PIXSCALE`(0.395, 근거 표기 없이) · `CCDXBIN`/`CCDYBIN`(이름 유지) · `NAMPDET`/`NAMPRAW` · **타일 해부 대칭형** `AMPNAX1`=1200/`AMPNAX2`=4700 + `IMAGEX`=1152/`IMAGEY`=4616 + `PRESCNX`/`PRESCNY`=0 + `OVRSCNX`=48/`OVRSCNY`=84(개명으로 레거시 동명 충돌 전부 해소) · **`CHMAP_LT/LB/RT/RB` 4장**(값=CCD 출력 채널, raw X 오름차순; AMPCHA/AMPCHB 안 대체). 값은 채널맵 원자료와 전수 대조 완료 — 검토 종료 후 `__reference/Detector_Ch_to_AmpID_Map_v1.0.txt`(구 AMPID.txt) · `__reference/Detector_and_Amp_Info_cards_v1.0.txt`(구 AMPCARD.txt)로 v1.0 승격(2026-08-21). 파생 카드(`AMPDATA`·`NXTILE`·`RAWXTILE` 등)는 싣지 않는다. `__reference/Archon_Unit_Info.txt`가 CTRL1/2 ID·SN 실값의 원자료다.
- **충돌 처리 · 정체성 재설계 확정** — 번호 공간 000000–099999, 충돌 시 pair 선검사 + 번호 증가(상한 100000회 초과 시 ERROR·저장 안 함), 카운터 동기화. `UNIQNAME`·`NAMECLSH`·`clash/` 폐지, `FILENAME`(유일 키)+`ORIGNAME`(항상 기록, 불일치=충돌 신호). 정리본: [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md`](archive/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md) **Part 2** (D-등재 대기, 결정문 초안 §8 — 구 Numbering v0.2 는 `archive/`).
- **MEF 쪽 개정 요청 목록**: 같은 문서 **Part 1** (LEECU 전달용 — MEF `UNIQNAME` 공급원, C-11 CHMAP 개정, 이관 미결 4건 등 — 구 MEF_Impacts v0.4 는 `archive/`).
- 미세 미결: `ORIGNAME` 이름 최종 확정(ORIGNAME 유지 권고, 차선 INITNAME), `READMODE` 값 충돌(FAST vs 64AMP — → v1.9 `RDMODE` 개명으로 종결), Instrument 절(FPAID 카드안 · INSTRUME 어휘) 미착수.

### 2026-08-20 세션 기록 (아래는 그 시점 기준)

**2026-08-20 세션은 키워드 설계를 검토만 했고 아무것도 확정하지 않았다.** 그래서 v1.6 · v0.7 · 규격 v1.2 는 손대지 않았다. 아래는 그 논의에서 **모양이 잡힌 것**과 **아직 못 정한 것**이다. 다시 처음부터 헤매지 않도록 근거까지 적어 둔다.

작업 대상 초안은 `__review/KMTA.20260818.012345.MK.fits.header.txt` 로 들어왔다(현재 v0.3.5 — 이전판들은 git 이력과 운영자 외부 백업 `__backup_raw_fits_spec_oldver/` 에 있고, `.bak` 은 운영자 지시로 무시한다).

### 모양이 잡힌 것 (아직 결정 아님)

| 카드 | 형태 | 근거 |
|---|---|---|
| `NAMPDET` / `NAMPRAW` | `16` / `32` | `NAMPS`(레거시 8 → 신규 64, **세는 범위가 바뀜**)와 `AMPPCD`(`AMPCCD` 오타로 읽힘)를 폐지하고 통일. v1.6 8.1절에 기록됨 |
| `AMPNAX1` / `AMPNAX2` | `1200` / `4700` | `RAWNAX1`/`RAWNAX2` 계열. `*SIZE` 는 이 헤더에서 **구간 문자열**이라(`DETSIZE`) 피했다. comment 는 `X pixels per amplifier (image+pre/overscan)` |
| `AMPCHA` / `AMPCHB` | `'1615141312111009 0102030405060708'` | AMPID ↔ CCD 출력 채널. 자리=amp, 값=channel. **8개마다 공백**이 TOP/BOT 경계와 맞는다. port 글자가 이름에 들어가야 해서 `AMPCHMAP`(8자)은 못 쓴다 |
| `IMGSEC` 계열 값 | `'D-Top'` / `'A-Bot'` | 구분자는 **하이픈** — 콜론은 구간·육십진으로 이미 두 뜻, 쉼표는 목록. `Bot` 은 `ENDID`/`EXTNAME` 이 쓰는 축약 |

**`AMPNAX*` 로 파생되는 값은 카드로 싣지 않는다** — `AMPDATA`·`NXTILE`·`RAWXTILE` 이 전부 `NAXIS` 와의 나눗셈·뺄셈으로 나온다.

```text
tile 수  = NAXIS1 / AMPNAX1 = 19200 / 1200 = 16
active X = AMPNAX1 - OVERSCNX - PRESCANX = 1200 - 48 - 0 = 1152
active Y = AMPNAX2 - OVERSCNY - PRESCANY = 4700 - 84 - 0 = 4616
```

### 아직 못 정한 것

| 무엇 | 왜 막혔나 |
|---|---|
| **`AMPDIRST`/`AMPDIRSB` 의 `L`/`R` 뜻** | *"독출 방향"* 인지 *"amp 위치"* 인지 안 갈린다. 초안 값 `'LLLLRRRRLLLLRRRR'` 는 현행 `OSCNPATT='RRRRLLLL'`·converter `is_bias_right()` 와 **좌우가 반대**다. 방향으로 읽으면 어긋나고 amp 위치로 읽으면 맞는다. **comment 한 줄로 끝나고 측정과 무관하므로 지금 정할 수 있다** |
| **`OVSCN` 계열의 X/Y 분리** | v1.6 8.1절이 `OVERSCNX` 폐지 → `OVSCN` 으로 적었는데, 이후 초안은 `OVERSCNX`+`OVERSCNY` 를 유지한다. **둘 중 하나를 철회해야 한다** |
| **`OVERSCNY=84` 의 가장자리** | amp 기준으로는 안쪽 가장자리(TOP 은 아래, BOT 은 위)인데 헤더에 안 적혀 있다. 게다가 `84` 는 168 의 균등 분배 **가정**이고 OI-4 가 미측정이다 |
| **상하 독출 방향** | `AMPDIRS*` 는 좌우만 담는다. `RDDIRT`/`RDDIRB` 가 하던 일이 초안에서 사라졌다 |
| **v1.6 7장 `도입 여부` 36칸** | 후보 37장 중 `NAMPRAW` 하나만 `O` 다 |
| **v1.6 2장 `Raw Archon` 열** | 123개 중 9개만 채워져 있다 |

> **이 결정이 왜 자꾸 안 끝나는가** — 아는 것(좌우 X)과 모르는 것(상하 Y · 중앙 overscan 분배)을 **한 카드에 함께 담으려 해서**다. 측정 안 된 사실의 최종 표기는 설계할 수 없다. 그리고 **converter 가 raw geometry 를 하나도 읽지 않아** 어떤 형식을 골라도 틀렸는지 알 방법이 없다(되먹임 없음).
>
> **여유는 있다.** `AMPDIRST`·`AORG`·`OVERSCNY` 같은 신규 카드는 아직 아무 자료도 쌓지 않았다. ACT-011 의 *"이름을 바꾸면 아카이브가 영구히 안 읽힌다"* 는 first light 부터의 얘기다.
>
> **권고**: ⓐ `L`/`R` 뜻만 지금 확정 ⓑ 미측정은 값 대신 **sentinel** 로(규격 5.0 절의 규약) ⓒ 형식은 OI-3 측정이 내놓는 모양을 보고 정한다.

### 검토했으나 접은 안

| 안 | 접은 이유 |
|---|---|
| raw 에 amp 별 구간형(`DATASEC` 32벌 등) | 단일 HDU 라 128장이 되고, 8자 제한 때문에 `DSEC01` 같은 비표준 어근이 필요하다. **raw 는 파라미터, MEF 는 구간**으로 가르기로 방향을 잡았다 |
| `AORG<nn>` 32장 (amp 별 원점+방향) | **이름이 지어낸 것**이고(`ORG` 가 FITS `ORIGIN` 과 겹친다), Y 방향이 OI-3 미측정이라 placeholder 32장이 된다. 실기 배치가 가정과 다르다고 밝혀지면 그때 다시 본다 |
| amp 별 `OVERSCNX`/`OVERSCNY`/… 32벌 | 128장인데 **값이 전부 같다.** amp 32개가 기하학적으로 동일하므로 스칼라 한 벌로 충분하다 |

## 되풀이 나타나는 함정 세 가지

**1. 이름은 같은데 뜻이 달라진 카드.** 값이 유효해 보여 오류가 안 난다.

| 카드 | 레거시 | 신규 |
|---|---|---|
| `OVERSCNY` | `0`, **가장자리** | `84`, **영상 중앙** ← D-013 이 폐지한 이유 |
| `NAMPS` | `8` (CCD 하나) | `64` (카메라 전체) ← v1.6 이 폐지 |
| `OVERSCNX` | `32` | converter 상수 `48` |
| `PRESCANX` | `27` | `0` |

**2. 기본값이 진짜 값처럼 보인다.** converter 는 카드가 없어도 오류를 내지 않는다(v2.5.0 — 멈추지 않는 이상은 `ConverterWarning` 으로 알리고 일부는 `HISTORY` 에 남긴다).

- `DATE-OBS` 없으면 **변환 시각(now)** 으로 대체 — 이 문서 전체에서 가장 위험하다
- ✅ ~~`RA`/`DEC` 없으면 `"00:00:00.00"` — 형식이 유효해 하류에서 안 걸린다~~ — **v2.5.0 이 걷었다**: 비면 카드를 빼고, 파싱되지 않으면 WCS 를 통째로 빼고 `WCSOMIT=T` 를 남긴다(D-023)
- 버전 문자열 9종은 `"ARCHON-v1.0"` 처럼 **그럴듯한 provenance** 가 박힌다
- **카드 값으로 멈추는 것은 둘이다**(v2.5.0) — `OBSERVAT` ↔ 파일명 사이트 코드(D-011 — 기본 출력 이름 경로에서만: `-o` 없음 · 파일명이 정규식에 맞음 · `OBSERVAT` 가 네 값 안) · pair 양쪽 `EXPID` 가 둘 다 있고 서로 다를 때.  (구 문장: *"오류로 걸리는 것은 `OBSERVAT` 하나"*)

**3. converter 는 raw geometry 로 자르지 않는다 — 선언은 대조에만 읽는다.** (구 제목 *"하나도 읽지 않는다"* — v2.5.0 부터 `check_raw_geometry()` 가 MK·NT 각각의 geometry 선언을 converter 상수와 대조해, 어긋나면 경고·`HISTORY` 를 남기고 카드가 없으면 대조 없이 지나간다.)  `OSCNPATT`·`ROWORDR`·`RDDIRT`/`RDDIRB`·`AMPMAP`·`AMOD`/`ACHN`·`NXTILE`·`CHIPS`/`CHIP1`/`CHIP2` 는 **소스에 이름조차 없다.** 나머지는 자기 상수로 만들어 내보낸다. `OVERSCAN_X=48` 은 표기용이 아니라 **실제 픽셀 절단 좌표 계산에 쓰인다.** → 변경점 C-5 · C-11 · C-12 · C-13 (✅ C-11 반영 · C-5/C-13 은 대조로 반영하되 멈추지 않고 경고만 · ⚠️ C-12 는 코드가 그대로 — 통합 v1.0 §1.2)

## 조사로 확정된 사실 (문서에 아직 안 들어감)

**레거시 `READOUT = 'ARLBRL'` 의 정체** — OSU IC 펌웨어(`../../__osu_legacy/IC2_*/IC2.img`)에 FreeBASIC 원본이 통째로 들어 있고, `SUB SetReadout()` 이 이렇게 하드코딩한다:

```basic
'-- Four amp readout only
Amps = "ARLBRL" : XAmp = 2 : YAmp = 2
TopDelaceCode = 8 : BotDelaceCode = 10  '-- swap to register quadrants correctly
```

`XAmp=2, YAmp=2` 사분면 전제 + de-interlace 순서가 얽힌 부호이고, 레거시 표본 3건 — 2017 raw(SSO) · 2021 raw(CTIO) · MEF primary — 이 **전부 같은 값**이다(불변 상수). **D-013 의 폐지 판정이 옳았음을 뒷받침한다.**

**레거시 IC 에 ROI 가 있었다** — 같은 펌웨어의 `READOUTSETVAR` 에 `OSCANX`/`OSCANY` 와 경고문이 있다: *"Region-of-interest has been modified to maintain symmetry around CCD centerline."* ICS 명령 테이블에는 없어 **운영에서 쓰이지 않았다.**

⚠️ 종전에는 이것을 **원장 10장(subframe)의 근거**로 세워 두었는데, **부분 독출이 불채택되면서**(운영자 2026-08-29) 규격 쪽 용처가 없어졌다.  레거시가 기능을 갖고도 안 썼다는 **사실 기록으로만** 남긴다 — 원장 10장 자체는 검토 기록이므로 그대로 두는 것이 기본이고, 덜어내려면 v1.8 에서 판단할 일이다.

**레거시 `AMPSEC` 이 독출 방향을 담고 있었다** — 레거시 MEF 실측 32장을 보면 `AMPSEC` 이 `CCDSEC` 과 같은 범위인데 **순서가 뒤집힌 것이 있다**(`K01`: `CCDSEC='[8065:9216,...]'` vs `AMPSEC='[9216:8065,...]'`). IRAF 관례대로 **구간의 오름/내림차순이 곧 독출 방향**이다. 전량 패턴은 `M/T = 5:3`, `K/N = 3:5` 인데 **우리 신규는 4:4 다.**

⚠️ **이 상충은 이미 닫혔다 — 틀린 쪽은 레거시다** (운영자 확정 2026-08-22, 재확인 2026-08-29).  `OI-15` 가 그때 **종결**됐고 규격 v1.4~v1.8 8장 OI 표와 `archive/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.7.md` 82행이 같은 판정을 싣고 있다: 실제 획득 자료 육안 확인으로 **`RRRRLLLL`(4:4) 확정**이고, 레거시 `AMPSEC` 의 5:3 / 3:5 는 **레거시 계통의 관찰이라 신규에 적용하지 않는다.**  ~~flat 이나 STA 문서로 확인이 필요하다~~ 는 **철회**한다.

남는 일은 확인이 아니라 **전파**다 — `Raw_Rev_MEF_Impacts` 가 적어 둔 대로 "ICD·정의서가 레거시 패턴을 전제하고 있으면 갱신 대상" 이다(LEECU 몫).

## 미결 항목

⚠️ **이 절은 2026-08-20 재작성 전 기록이다** — 당시 OI 번호는 구판 v1.2 9장 기준이고, **현행 OI 정본은 현행 raw spec 의 8장(science) + 10.6절(guide)** 이다. 서술도 구식이다(예: OI-3 의 `ROWORDR`/`RDDIRT`/`RDDIRB` 는 폐지되고 4.3절 포장 조항 준수 검증으로 바뀌었다). 아래는 경위 참고용으로만 남긴다.

| ID | 무엇 | 상태 |
|---|---|---|
| **OI-3** | `ROWORDR`/`RDDIRT`/`RDDIRB` 확정 | 실기 flat/star 필요. ICD §12 도 `READDIR` 을 placeholder 라 밝힌다 |
| **OI-4** | 중앙 overscan 의 TOP/BOT 분배 | 실측 필요. `OVERSCNY=84` 는 균등 가정 |
| **OI-5** | binning | 1×1 전용. binned 관측 계획이 서야 |
| ~~—~~ | ~~**부분 독출(subframe·ROI·window)**~~ | **불채택 (운영자 확정 2026-08-29)** — *"현재는 쓸 계획 없으므로 관련내용 없어도 되"*.  **OI 로 세우지 않고 규격에도 넣지 않는다.**  ⚠️ 되살아나면 필요한 것은 크기가 아니라 **원점**(`DETSEC`)이고, `CCDSUM`(OI-5 binning)이 거의 항상 함께 온다 — 검토는 **원장 10장**에 남아 있다 |

## 브랜치 상태

✅ **`raw-fits-spec-v1-review` 는 `e1cb82f` 로 `main` 에 합류했다** (거품 머지, `--no-ff`).  `origin/main` 의 조상이므로 남은 커밋은 없다 — 확인은 이렇게 한다:

```bash
git log --oneline --decorate origin/main..raw-fits-spec-v1-review   # 비어 있어야 한다
```

⚠️ **브랜치는 로컬 전용이고 원격에 안 올렸다.  합류 뒤에도 지우지 않는다**(목 선호) — 다음 라운드도 같은 브랜치에서 이어간다.

⚠️ **(2026-09-24 확인) 이 브랜치는 지금 로컬·원격 어디에도 없다** — `git rev-parse --verify raw-fits-spec-v1-review` 가 실패하고 `git branch -a` 에도 없어서 위 확인 명령이 돌지 않는다.  합류 커밋 `e1cb82f`(부모 `6b19ad6` · `67b4cfa`)는 남아 있어 이력은 보존된다.  되살릴지(`e1cb82f^2`) 이 절을 고칠지는 운영자 판단 대기다(맨 위 「운영자 판단 대기」 표 D6-8).  작업 자리는 이미 `main` 워크트리다.

이 브랜치가 갈라져 나온 자리는 **`6b19ad6`** 이다(v0.7 검토판 + 규격에 ((재작성중)) 표시를 붙인 커밋). 이 해시는 뒤에 뭘 더 쌓아도 안 바뀐다.

## 문서 생성 수단의 현재 상태

- **md → docx 변환기는 저장소에 있다** — `tools/md_to_docx.py` (71a1989 에서 도입). **검토 사이클이 열릴 때만** 이것으로 `__review/` 에 전달본 docx 를 만든다 — 판올림마다 만드는 것이 아니다(위 「개정 워크플로」, 운영자 확정 2026-08-22).
- **원천 추출 생성기(converter 소스 → md)는 여전히 없다** — v1.6 까지의 기계 추출 스크립트는 세션 scratchpad 와 함께 사라졌고, **v1.7 부터는 수기 개정 체제**라 당장 필요하지 않다. converter 가 크게 바뀌어 3~6장을 다시 기계 추출해야 할 때만 재작성한다(추출 규칙은 v1.6 머리말: `card("<MEF>", v("<raw>", <기본값>))` 정규식 파싱, 4.H 절·5.13 폐지 표를 표 블록으로 읽기). `Raw Archon` 열과 `도입 여부` 열은 사람이 채우는 계획 열이므로 그때도 보존해야 한다.

## 관련 문서

| 문서 | 위치 |
|---|---|
| L0 MEF ICD (1위 준거) | [`../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md`](../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md) (v4.3 — 구 v4.2·v4.1 은 `../mef_fits_spec/archive/`) |
| MEF keyword 정의서 (3위 참고) | [`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md`](../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md) (v1.1 — 구 v1.0 은 `../mef_fits_spec/archive/`) |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) (**v2.5.0** — 파일명 접미사 `_v2_1` 은 그대로이고 판은 `SOFTWARE_VERSION` 이 말한다) |
| 취득 SW 구현 | [`../ics_sim/SMC_CLAUDE.md`](../ics_sim/SMC_CLAUDE.md) · `../ics_sim/DevNote.md` 11.14 |
| 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |
| 등재 | [`../project_management/planning/ACTION_REGISTER.md`](../project_management/planning/ACTION_REGISTER.md) **ACT-011** |

# SMC_CLAUDE.md

`ics_sim/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md) 참고.

## 이 폴더가 뭔가

**신규 Python ICS 의 첫 실행 산출물.** 레거시 조사(3부작 보고서)가 끝난 뒤 실제로 만든 첫 코드다.

- 지금은 **시뮬레이터** — 카메라 하드웨어 없이 레거시와 호환되는 메시지를 낸다.
- **`ics_archon` v0.0 이 나왔다 (2026-08-23, DevNote 11.23).** 실기 프로그램은 [`../ics_archon/`](../ics_archon/README.md) 에 있고 **이 폴더를 사본 없이 그대로 가져다 쓴다** — 시퀀서·명령 처리부·메시지 규약은 **무개정**이다. 이 폴더에 늘어난 것은 `hardware/__init__.py` 의 `register_backend()` **6줄뿐**이고, 그것이 원래 확장점이다. 시험 318개는 한 줄도 안 고치고 통과한다.
  - **그래서 이 폴더를 고칠 때 상대가 하나 늘었다.** 헤더 층(`rawcards`/`rawhdr`/`rawpair`)·백엔드 계약(`hardware/base.py`)·시퀀서의 백엔드 호출 자리를 바꾸면 `ics_archon` 이 곧바로 깨진다. 바꿀 일이 있으면 `ics_archon/tests` (46항목)도 함께 돌린다.
  - **규약을 건드려야 할 것 같으면 그것 자체가 재검토 신호다.** 결정·검토사항 목록은 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md).
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

⚠️ **2026-08-24 — 사이트 판별이 바뀌었다** (운영자 지시, DevNote 11.27).
`[node] observatory`(`CTIO`/`SSO`/`SAAO`/**`KASI`** — 넷째 값은 **D-017**
(2026-08-25)로 구 `TESTBED` 를 대체했다) 한 줄이 정본이고 거기서
`telid`/`site` 가 유도된다. **적은 값이 그대로 `OBSERVAT` 카드**라 규격 2.2절·
converter 와 어긋나는 자리가 없다. **호스트 IP 판정(D-015)은 폐지** —
`siteid.py` 를 지웠다. 모르는 값은 **기동 거부**.

전부 `tests/test_obsagent_contract.py` 가 검증한다. **테스트가 깨지면 그건 규약을 어긴 것이다.**

⚠️ **2026-08-24 — 위 5번(1.8초 창)에 스위치가 생겼다** (목 지시, DevNote 11.26).
`[readout] acq_per_frame` 을 켜면 `Acquisition Complete.` 를 컨트롤러 프레임별로
내보내고, 그러면 4개의 산포가 **0 에서 두 컨트롤러의 실제 시차로** 바뀐다 —
5번의 구조적 보장이 없어진다는 뜻이다.

- **기본은 `false` 이고 그때 거동은 종전과 완전히 같다** (4개가 같은 틱).
- **켜는 것은 실기 시차 실측 뒤에 정한다** (`tools/probe_archon.py` 3단계).
  스위치가 꺼져 있어도 시차는 잰다 — `[readout] acq_skew_warn`(기본 1.0초)이
  넘으면 경고를 남긴다. 그 실측이 기본값을 정할 근거다.
- 시뮬에서는 `obsagent_model.check_windows` 가 `spread = acq[3] - acq[0]` 로
  잡는다. 시험은 `tests/test_acq_per_frame.py`.

**규약을 어긴 것이 아니라 목 지시로 연 것이다** — 커밋에 그 사실을 명시한다.

## 메시지 오염 버그 (DevNote 5장)

레거시 ICS 는 커맨드워드 슬롯을 비우지 않아 비동기 메시지가 엉뚱한 커맨드워드를 달고 나갔다(CTIO 634일에 173,635건 등). **이 프로그램은 그걸 고친 것이 존재 이유 중 하나다.**

- `emitter.py` 의 모든 메서드가 `cmdword` 를 **명시적 인자**로 받는다. 상태에서 물려받는 경로를 만들지 마라.
- 송신 전 `validate()` 가 6가지 오염 패턴을 검사한다.
- `--bug-compat` 로 레거시 오염을 재현할 수 있다(골든 대조용, 기본 꺼짐).

## ⚠️ 백엔드 계약 `sensors()` 가 바뀌었다 (2026-08-27) -- 키 아홉

**`ics_archon` 세션에서 이 폴더의 계약을 고쳤다.**  경위는 [DevNote 11.32](DevNote.md), 일감 지시는 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "▶ 다음 세션 작업 지시".

- **`ccdtemp1`/`ccdtemp2` → `ccdtemp` 하나.**  운영자 확정(2026-08-27) -- CCD1/CCD2 를 구분하지 않고 **듀어의 CCD 대표 온도 하나**만 읽는다.  chip 귀속은 **정보가 없으므로 규정하지 않는다.**
  - ⚠️ **종전 계약이 `ccdtemp` 를 "백엔드가 따로 줘도 무시하는" 키로 명시**했고 `tests/test_raw_header.py` 가 그것을 못박고 있었다.  규칙의 존재 이유("센서가 둘이니 두 번째 사실을 만들지 않기")가 사라져 **규칙을 지웠다.**  `ccdtemp1`/`ccdtemp2` 를 **아직 읽으면 실패**하는 회귀가 들어 있다.
  - **"대체 금지" 원칙은 남아 있다** -- 예시만 갱신했다(없는 `ccdtemp2` → 실제로 유혹이 되는 `DMPTEMP`·`Cn_TEMP` 모듈 온도).
- **`air_in`/`air_out`/`glyc_in`/`glyc_out` 넷을 없앴다.**  해당 카드 4장이 v1.5 에서 폐지돼(`rawhdr.DEWAR_CARDS` 에 없다) 호출측이 값을 버리고 있었다 -- 계약에 남겨 두면 백엔드가 **아무도 읽지 않는 값을 읽으러 간다.**
- 고친 파일: `hardware/base.py`(계약) · `rawhdr.py`(`thermal_header`) · `hardware/sim.py` · `hardware/archon.py`(스텁 주석) · `tests/test_raw_header.py` · `tests/test_raw_draft.py`.  `ics_archon/_vendor` 는 `tools/sync_vendor.py` 로 재생성했다.
- ⚠️ **`CCDTEMP` 카드 comment 의 `M` 제거는 이것과 별개**이고 **raw spec v1.8 작업**이다 (견본 pair 바이트가 정본이라 규격과 함께 `main` 에서 움직인다).
- **시험**: `ics_sim` **330 통과** · `ics_archon` **214 통과** (2026-08-28 세션 2 기준).  ⚠️ 두 스위트를 **동시에 돌리지 말 것** -- `ics_archon` 의 `test_shutdown_waits_for_frames…` 가 부하로 간헐 실패한다.
  - ⚠️ **여기 적혀 있던 "`ics_archon` 171 통과" 는 사실이 아니었다** (2026-08-28 정정) -- 그때 `_vendor/MANIFEST.sha256` 이 어긋난 채 커밋돼 `test_vendor.py` 두 시험이 실패하고 있었다(**169 통과 · 2 실패**).  원인은 `sync_vendor.py` 를 돌린 **뒤에** 원천을 한 번 더 고친 것이다.  경위·교훈은 [DevNote 11.33](DevNote.md).

## ✅ 참고 자료 재검토도 **이 폴더는 무개정** (2026-08-28 세션 2)

운영자가 `ics_archon/__ref_archon_control/` 에 실험실 실사용 스크립트 일곱과 ACF
원본 열하나를 반입했고, 본편에 옮길 것을 전수로 봤다.  **`ics_sim` 은 한 줄도 안
고쳤다** -- 그래서 `tools/sync_vendor.py` 를 돌릴 일도 없었고
`_vendor/MANIFEST.sha256` 도 그대로다.

옮긴 것은 하나뿐이고 전부 `ics_archon` 쪽이다: **`POWERON` 뒤 `POWER=4` 확인**
(`archon/controller.py`).  경위·미채택 근거·부산물(guide 자리 표 = `OI-19` 의 답)은
[DevNote 11.34](DevNote.md)와
[`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "참고 자료 재검토".

⚠️ **이 폴더에 걸리는 것 하나** -- guide 자리 표가 **8자리**(백플레인 +
MOD3·4·5·6·7·9·10)로 확정됐는데 `rawhdr.TEMP_MODS`/`TEMP_MOD_LABELS` 는
**science 10자리 하나뿐**이다.  guide raw 규격을 세울 때 **유닛 종류로 자리
표를 가르는 것**이 이 폴더의 일감이 된다.  지금 손대지 말 것 -- 규격이 먼저다.

## ✅ `ics_archon` 층 1·2 감시가 붙었다 (2026-08-28) -- **이 폴더는 무개정**

`ics_archon` 이 컨트롤러 텔레메트리를 주기적으로 떠서 CSV 로 남기기 시작했다
(`archon/monitor.py`).  **`ics_sim` 은 한 줄도 안 고쳤다** -- `IcsSim.spawn()`
이라는 기존 확장점만 썼다.

`ics_sim` 쪽에서 알아 둘 것은 하나다: **`DetectorBackend` 의 텔레메트리 접근자
(`controller_telemetry()`)가 읽는 값의 뜻은 그대로 "노출 개시 시점 값"** 이다.
`ics_archon` 이 감시용 스냅샷을 **다른 자리**(`ctrl.status_live`)에 들기 때문이고,
섞였으면 `Cn_TEMP/VOLT/CURR` 이 **폴링 간격에 따라 노출마다 달라지는 값**이
됐을 것이다.  계약에 이 구분을 적을 필요는 없다 -- 백엔드 안의 일이다.

## ⚠️ raw spec v1.6 반영 (2026-08-26) -- 정체성 카드가 바뀌었다

**`ORIGNAME` 이 폐지되고 `EXPID` 가 대신한다** (D-019).  값은
`<SITE>.<YYYYMMDD>.<NNNNNN>` 이고 **`DETID` 필드가 없어 pair 양쪽이 같다** --
그래서 `rawcards.PAIR_DIFF` 가 **7장 -> 6장**이 됐다.

| 무엇 | 전 → 후 | 자리 |
|---|---|---|
| 정체성 카드 | `ORIGNAME`(`DETID` 필드 있음) → **`EXPID`**(없음, pair 동일) | `rawcards.CARDS`·`PAIR_DIFF` · `rawhdr.exposure_header(expid=)` · 신설 `rawpair.exposure_id()` · `sequencer`(`name_stem()` 호출이 빠졌다) |
| `FILENAME` comment | → `FITS file name as written to storage` | `rawcards.CARDS` |
| `Cn_*` 구분자 | 공백 → **`|`** | `rawhdr._join_readings()`.  ⚠️ 슬래시는 FITS comment 구분자와 겹쳐 배제했다 |
| `Cn_*` comment | `Ctr-n` → **`Ctrl-n`** | `rawcards.CARDS` 6장 |
| 나열 결측 sentinel | `-999.99` → **`NC`** | 정본은 **`rawhdr.FIELD_NC`**(`archon/parse.FIELD_NC` 가 받아 쓴다).  ⚠️ **단일 HK 카드는 `-999.99` 그대로다** |
| 카드 폭 초과 | 값을 잘랐다 → **comment 를 먼저 자른다** | 규격 5.0절 신설.  이 저장소에서 카드 이미지를 만드는 곳은 **셋** — `archon/fitswrite.card_image()` · **astropy 경로 `fitsout._fit_to_card()`** · labtest `fits_card()` |

⚠️ **충돌 판별이 한 단계 늘었다** -- 종전 `FILENAME != ORIGNAME`(직접 비교)에서
**`FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값 != `EXPID`** 로.  `DETID` 필드 제거는 이미
규격 2.3절 5항이 정의한 연산이다.

**⚠️ 전수 검사에서 더 나온 둘 (2026-08-26)** — `ics_sim` 쪽만 적는다.

- **전 자리 결측은 `NC` 한 토큰이 아니라 자리 수만큼** `NC|NC|…` 다.
  `rawhdr._join_readings(values, fmt, slots)` 에 자리 수 인자가 생겼다 —
  규격 5.6.1절 "자리는 비우지 않는다" 이고, 같은 절이 **자리 수 자체를 모듈
  구성 판별에 쓰라**고 하므로 한 토큰짜리는 "모듈 한 장짜리 컨트롤러" 로
  읽힌다.  목록 안의 `None`/빈 값도 `NC` 로 간다.
- **astropy 는 값이 68자를 넘으면 자르지 않고 `CONTINUE` 로 카드를 늘린다** —
  그 순간 견본이 못박은 144 레코드·11,520B 가 깨지는데 경고가 없다.
  `fitsout._fit_to_card()` 가 규격 5.0절대로 잘라 막는다.  값의 출처가
  `OBJECT`/`OBSERVER`/`PROJID`(관측자 입력)라 길이는 바깥에서 온다.

경위·판단은 **DevNote 11.29**, 전수 검사는 **DevNote 11.30**.  `ics_archon` 쪽 반영분과 **다음 세션 착수점**(origin 푸시 · `raw-spec-v1.6` 태그 · 벤치 ini · converter)은
[`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "다음 세션이 먼저 알아야 할 것".

## ⚠️ raw spec v1.5 반영 (2026-08-26, 이 브랜치에서 마무리)

**v1.5 의 5장 검토 라운드가 `ics_sim` 까지 내려왔다.**  `main` 이 구판(IP 판별)
`ics_sim` 에 먼저 반영했고(`13e02b2`), 이 브랜치가 그것을 머지해 **`observatory`
판별 구조 위에서 완결**했다.  값이 바뀐 자리 — 여기를 모르고 옛 상수를 기대하면
시험이 깨진다.

| 무엇 | 전 → 후 | 자리 |
| --- | --- | --- |
| **사이트 코드 (D-017)** | `KMTT`/`TESTBED` → **`KMTK`/`KASI`** | `rawpair.OBSERVAT`·`SITE_OF_OBSERVATORY`·`SITE_SECTION`·`ORIGIN_OF`·`OBSDATE_SHIFT_MIN` · `config._SITE_TELID`(`testbed`→`kasi`)·`NodeCfg` 기본값 · `state.site_code` · `ics_sim.ini` `[node] observatory` + `[site.kasi]` |
| **상수 개명** | `rawpair.TESTBED_SITE` → **`rawpair.KASI_SITE`** | 참조는 `app.py` 두 곳.  **옛 이름은 없다** — `AttributeError` 로 드러난다 |
| **노출 번호 공간 (D-018)** | `099999` 상한 → **`000000`–`999999`** | `rawpair.NUM_SPACE = 1_000_000`.  ⚠️ `main` 은 `state.EXPNUM_SPACE` 를 따로 신설했는데 **이 브랜치는 채택하지 않았다** — 같은 뜻의 상수를 둘로 두지 않는다.  `state` 는 종전대로 `rawpair.NUM_SPACE` 하나를 쓴다 |
| **셔터 재질의** | `3.0` → **`1.0`** 초 | `config.TimingCfg.aux_requery_after_shopen` · `ics_sim.ini`.  ⚠️ **이 값은 재질의가 걸리는 노출 문턱이기도 하다** — `_integrate_shutter()` 가 `exptime <= delay` 면 재질의하지 않으므로 **1초 이하 노출**이 개시 직전 값을 그대로 쓰는 구간이 됐다 (종전엔 3초 이하) |
| **HK 카드 4장 폐지** | `AIR_IN`·`AIR_OUT`·`GLYC_IN`·`GLYC_OUT` 제거 | `rawhdr.DEWAR_CARDS` 10장 → **6장** · `rawcards.CARDS` 에서 제거.  `standalone RTD` 공급 계통이 통째로 비었다.  견본 값 카드 **135 → 131** |
| **`CHMAP_*` 토큰** | 3자 `M16` → **4자 `MD16`** | `rawhdr.CHMAP` · `check_geometry()` 불변식 · `rawcards` 폭 31→39 · comment `CCD output ch,`→`CCD out ch,` |
| **사이트별 상수 (5.3.1)** | `TELESCOP`+`FPAID` 를 사이트가 정한다 | `rawhdr.VERIFIED_SITES` 에 네 사이트 `telescop`+`fpaid`.  KASI = `'KMTNet 1.6m #0'`/`'FPA#0'`.  **좌표는 여전히 비운다** |
| **견본 comment 오타 2건** | `Telesope`→`Telescope` · `Acutator`→`Actuator` | `rawcards.CARDS` |

⚠️ **망원경 번호와 `FPAID` 번호는 관측소 셋 모두 어긋난다** (CTIO 망원경 `#1`·`FPA#2` /
SSO `#3`·`FPA#1` / SAAO `#2`·`FPA#3`).  오타로 보고 맞추면 검출기 귀속이 틀어진다.

경위·판단은 **DevNote 11.28**.  `ics_archon` 쪽 반영분(벤더 재생성 · labtest 내장
사본 · 신설 표류 감시 시험)은 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md)
"raw spec v1.5 반영" 절.

⚠️ **벤치 설치본은 ini 를 고쳐야 기동한다** -- `[node] observatory = TESTBED` 는
이제 모르는 값이라 **기동을 거부**한다.  `KASI` 로 바꾸고 `[site.testbed]` 절도
`[site.kasi]` 로 고칠 것.

## 상태 (2026-08-26 — raw spec v1.5·v1.6 반영 완료)

**검증(2026-08-26 실측)** — `ics_sim` **330 통과** · 형제 `ics_archon` **152 통과**(배치본 135 + `repo_only` 17) · 벤더 표류 없음 · 견본 v1.6 pair 바이트 단위 재현.

### ⏳ 지금 진행 중 — 관측 스크립트로 첫 연동 시험

목이 벤치에서 **`osc/aic_integration_test_v0.0.osc`** 를 한 번에 돌리고 있다
(`+opause` 를 로컬 사본에서 주석 처리했다 — 그래서 **목의 사본은 `ostart`
줄번호가 저장소 판과 다르다**).  하룻밤을 압축한 6블록이고, `ics_sim` 이
받는 쪽이다.

**로그가 오면 판정할 것** (`obs.event.*.log` · `isis.*.log` · `ls -l ~/AIC/data`):

- 노출마다 `Acquisition Complete.` 4회 · `Wrote` 4회 · `EXPSTATUS=IDLE` 1회
- 시간 창 3종 — **`ics_sim/obsagent_model.py` 의 `CamStatusReplay` 에 발신
  스트림을 먹이고 `check_windows()`** 로 잰다.  이미 있는 도구다
- CamStatus 전이 — DARK/BIAS 가 `INT_2` 를 건너뛰는지, 역행 0인지
- **P2 겹침 구간**(1초 노출 ×5)에서 파일 일련번호가 밀리지 않았는지 —
  DevNote 12.10 이 겪은 부류다
- 헤더 — `EXPTIME`·`IMAGETYP`·`FILTER`·`OBJECT`·`RA/DEC` 가 줄마다 맞는지

⚠️ **아직 확인 안 된 것**: `FILTER` 값(`n`/`i`/`r`/`v`)이 벤치 필터 설정과
맞는지.  obstool 이 `sys.filterlabel[]` 과 대조해 못 찾으면 **그 줄만**
"unrecognized filter name" 경고와 함께 skip 된다.  로그에 그 경고가 있는지가
첫 확인 항목이다.

스크립트 형식·명령·함정은 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md)
"관측 스크립트 (`.osc`) — 알고 시작할 것" 에 정리해 두었다 (⚠️ **저장소의 옛
견본은 `ProjID` 열이 없는 판이라 그대로 베끼면 안 된다** — 2026-08-25 에
`0 of 26 exposures imported` 로 실측했다).

### 종전 상태

- **구현 완료**: 전체 노출 사이클(DARK/BIAS/OBJECT), `GO n` 다중 노출, 전 명령 디스패치, 텔레메트리 중계, 옵션 FITS, 콘솔, 결함 주입 6종, **`STOP`/`ABORT`**(9.2.1), **AUX control TCP 연동**(9.2.2), **자기 발신 에코 필터·브로드캐스트 중복 억제·노드 ID 검증**(3.1.2 — 실물 XIS 연동의 전제)
- **테스트 330개 전부 통과** (2026-08-26 기준 실측. 2026-08-22 v1.3 정렬로 헤더 시험 재편 + 적대적 검토 회귀 시험 추가 — 구 324개 → 318개, 그 뒤 `ics_archon` 확장점·경로 결함 회귀로 +7, 병렬 독출 스위치로 +5, **사이트 판별 개정으로 IP 판정 전용 시험 28개 삭제·사이트 시험 11개 신설**)
- **실물 연동 시험 완료 (2026-08-11)** — 재빌드한 XIS(v2.9.1) 허브에 **실물 TCSAgent·OBSAgent 와 함께** 물려 돌렸다. 9개 노드 ID 등록·에코 필터·재등록·개별 IC 라우팅·노출 사이클 전 구간 통과, 타임아웃 창 3종 모두 큰 여유. **`ExpNum` 응답 값이 한 칸 밀리는 결함 하나를 잡아 고쳤다**(DevNote 3.4·12.14). 전체 결과는 DevNote **3.7**
- **아직 안 만든 것**: `BIN` 하나. `strict_legacy` 면 무응답이고, 구현 지침은 `commands.py` docstring 에 있다.
- **일부러 안 만든 것**: `ROI`/`DISPL`/`MOVIE` — **레거시 ICS 명령 테이블에 아예 없어서** 핸들러를 두지 않았다. 레거시와 똑같이 `Didn't understand` 로 거부된다(DevNote 6.8).
- **2026-08-08 전 문서 정합성 일제 점검 완료** — 레거시 보고서 3부작·Agent 보고서 2종·raw_fits_spec·xis 문서의 낡은 서술/모순 30여 건 정정. 내역은 DevNote 14장 말미.
- **2차 연동 시험 완료 (2026-08-11)** — **`ExpNum` 값 규약이 실물에서 확정됐다**(DevNote 3.7.2). 노출 2회로 readout 중 `ExpNum`==파일 번호 · 종료 후 `ExpNum`==`FitsNum` · `EXPNUM` 응답 N+1 을 모두 확인. 12.14 의 교정이 시뮬 테스트를 넘어 관측자 화면에서 검증된 것은 이번이 처음이다. **로그는 터미널 스크롤백 대신 `[logging] file` 로 받을 것** — 스크롤백은 페인 폭 경계에서 한 글자씩 먹혀 5.3 의 와이어 손상과 구분이 안 된다(3.7.2 말미)
- **EXPNUM 지속 (2026-08-11)** — 위 시험의 전제였다. 첫 시도에서 `FitsNum=00000000.000000` 이 나왔다. 번호가 매 실행 1 로 되돌아가 기존 파일과 겹치고, 파일명 fail-safe 가 `KMTN` 없는 이름을 쓰자 OBSAgent 파싱이 실패한 것이었다. **마지막으로 쓴 번호를 `[paths] expnum_file`(기본: 설정파일 옆 = `~/AIC/Config/ics_sim.expnum`)에 기록하고 기동 시 +1 부터 쓴다.** `data_dir` 를 비워도 되돌아가지 않는다 — 근거와 버린 대안은 DevNote **11.12**
- **raw pair 규격 적용 (2026-08-11)** — **저장 단위와 통보 단위를 분리했다.** 물리 파일은 컨트롤러당 1개(`<SITE>.<날짜>.<번호>.<MK|NT>.fits` ×2), `Wrote` 통보는 CCD당 1회씩 4회를 레거시 논리 이름(`KMTN<c>.…`, 불변)으로 낸다. 하드웨어 계약도 컨트롤러 단위로 개정했다(`write_frame`, **D-012**). 헤더에 규격 5.1·5.2 정체성 카드, sentinel 은 5.0절대로(C-9/OI-6). **기존 규약 테스트 177개가 한 줄도 안 고치고 통과** — 통보가 논리 이름 그대로라 OBSAgent 는 무변경이다. 근거·경위는 DevNote **11.13**, 규격은 [`../raw_fits_spec/`](../raw_fits_spec/README.md) 2.3·2.5·5장
- **식별 keyword 재정의 (2026-08-12)** — 레거시 실측 헤더를 근거로 `EXPID`/`EXPNUM` 을 없애고 `UNIQNAME` 을 **정본**(불변)·`FILENAME` 을 **실제로 쓴 이름**으로 갈랐다. 이름이 겹치면 개명 대신 `clash/` 격리 + 시각 접미 + `NAMECLSH` 카드 세 겹. 경위는 DevNote **11.13.2**
- **헤더 전면 재검토 (2026-08-13)** — 레거시 raw 123개 카드를 하나씩 맞대어 **계승 5 · 개칭 1 · 폐지 16** 으로 판정했다(규격 5.13절, **D-013**). 그리고 규격 5.3~5.10 을 실제로 구현했다 — 헤더가 **68장 → 221장**. **규격 안의 불일치 하나를 잡았다**: converter 는 `CTRL1ID`/`CTRL2ID` 색인형을 MK 헤더에서 직접 읽는데 종전 규격은 단수형을 싣게 해서, 그대로 두면 MEF 의 컨트롤러 정체가 **오류 없이 전부 `UNKNOWN`** 이 됐다. 신설 `rawhdr.py`, 백엔드 계약 4개 확장, 시험 59개 추가. 경위는 DevNote **11.14**
- **파일명 날짜부 = 사이트별 관측일 (2026-08-13)** — UT 에 사이트별 보정을 더한 뒤 날짜만 취한다. 경계는 CTIO UT 16:30 · SAAO UT 10:30 · SSO UT 01:30 이고 **셋 다 현지 12:30** 이다. 종전 잠정안(UT 날짜)은 CTIO·SAAO 에서 **한 밤의 자료를 두 디렉토리로 갈랐다** — 아무 오류 없이. `DATE-OBS` 는 `SHOPEN` 지시 시각의 UT(밀리초까지)이고 중복이던 `UT` 카드는 없앴다. **OI-10 종결 · OI-12 해소**, **D-014**, 경위는 DevNote **11.15**
- ~~**사이트는 호스트 IP 로 판정한다 (2026-08-13)**~~ — **폐지 (2026-08-24, DevNote 11.27).** 이제 **`[node] observatory`**(`CTIO`/`SSO`/`SAAO`/`KASI`) 한 줄이 정본이고 거기서 `telid`·`site`·좌표·`ORIGIN`·`INSTRUME` 가 함께 유도된다. `siteid.py` 와 `site_from_ip` 는 지웠다. D-015 가 막으려던 것(틀린 설정)과 이번에 막는 것(틀린 판정)은 **다른 위험**이고, 운영자가 설정 쪽을 택했다 — NIC 이 내려가면 진짜 관측 자료가 `KMTK.…` 로 저장되던 것이 그 이유다. 모르는 값은 **기동 거부**. ini 어휘를 `CTIO`/`SSO`/`SAAO`/`KASI` 로 둔 것이 요점이다 — **적은 값이 그대로 `OBSERVAT` 카드**라 규격·converter 를 고칠 일이 없다
- **raw ↔ MEF 키워드 대응표 (2026-08-13, 검토 대기)** — 289행 전수. MEF 쪽은 문서가 아니라 **converter 코드에서 기계 추출**했다(코드가 최종본이므로). **Archon setup·구성·유닛 텔레메트리 카드의 이름과 구성**이 핵심이다 — 실기가 이 이름으로 자료를 쌓은 뒤 이름이 바뀌면 그때까지의 아카이브가 영구히 안 읽힌다. 정본은 판정 원장 [`../raw_fits_spec/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.14.md`](../raw_fits_spec/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.14.md) (대응 관계 = `Use in MEF` 열, 판정 준거 = 0장), 미결 4건은 [`../raw_fits_spec/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.6.md`](../raw_fits_spec/KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.6.md) §6, **ACT-011**. ⚠️ **`ics_sim` 의 현재 출력은 raw 쪽 사실의 근거가 아니다**(순환) — 원장 0장 참조. 경위는 DevNote **11.17**
- **raw spec v1.3 전면 정렬 (2026-08-22)** — 헤더 층을 **템플릿 주도**로 재편했다: 신설 [`ics_sim/rawcards.py`](ics_sim/rawcards.py) 가 초안 헤더 v1.0 pair 의 **기계 사본**(값 135 + COMMENT 8, 카드 순서·comment·패딩)이고, `rawhdr` 는 값 풀만 공급한다. 견본 값을 넣으면 견본이 **바이트 단위로 재현**된다(`tests/test_raw_draft.py` 대사 — 불일치 0). D-016 충돌 처리(선검사·번호 증가·되감음·상한, `UNIQNAME`/`NAMECLSH`/`clash/` 폐지, `ORIGNAME` 상시), 백엔드 계약 개정(`voltages`/`amp_map` 폐지 → `controller_telemetry` 신설), TC 중계 카드 전부 문자열화(`TCSTIME` 이관 · `DALTERR`/`DAZERR` 계산), **`fits_shape = spec`** 이면 실물 19200×9400 을 4장 기하 구조(암프별 offset·X/중앙 overscan) 그대로 생성 — **converter end-to-end 로 69-HDU L0 MEF 생성 검증 완료**. 테스트 **317개** 전부 통과(OBSAgent 규약 시험은 무수정). v0.2.0. 경위·판단은 DevNote **11.19**
- **적대적 검토 + 12건 수정 (2026-08-22)** — v1.3 정렬분을 관점 4개(규격 준수·동시성·archon 스크립트·OBSAgent 규약)로 재검토하고 반박 검증을 붙여 **확정 14건 중 12건**을 고쳤다. 큰 것: ⚠️ **critical** — D-016 선검사가 외부 `INITIALIZE` 로 오염된 채널 suffix 를 파싱해 **노출 태스크를 죽였다**(IDLE·Wrote·advance 전부 유실 → `opause`); **pair 동일성(5.9절)이 구조적으로 없었다**(백엔드 사실을 컨트롤러별로 따로 질의 — 시뮬 고정값 때문에 시험이 통과하던 부류); 노출 메타데이터 경합; 구판부터 있던 **사이트 갈림**(파일명·헤더가 IP 판정 대신 ini 원값, D-015 위반)·STOP 이벤트 잔류·ABORT 의 앞 프레임 저장 파괴. archon v1.1 도 6건 전량 수정(카드 폭 클램프·자리 sentinel·예외 방어·컨트롤러 색인·SITE 유도·OBJECT 역산). **남겼던 2건은 둘 다 닫혔다** — `IMAGETYP='STANDARD'` 폐지(운영자 확정) · 견본 헤더 날짜 불일치(정본 개명으로 해결). 전부 DevNote **11.20**
- **`IMAGETYP` 어휘 정리 + raw spec v1.4 정합 (2026-08-22)** — `STANDARD` 폐지(운영자 확정 "이제 안 쓴다"): `state.IMAGE_TYPES`·`cmd_standard`·`emitter.KNOWN_COMMANDS`·콘솔 도움말에서 걷어내 **규격 5.4절 어휘와 집합이 같아졌고**, 그 일치를 시험이 지킨다(`test_command_vocabulary_equals_the_spec_vocabulary` — 한쪽만 늘면 걸린다. 값 추가는 규격과 코드를 **함께** 고치라는 운영자 지시의 강제 장치다). 레거시에 있던 명령이라 갈라지는 지점이지만 `.osc` 22개·레거시 로그에 용례 0건. 규격 v1.4 정합도 함께 — 파일명 참조 6곳, **삭제된 2.5절** 인용 9곳을 DevNote 3.2 로(IMPv2 스펙 2.5절은 무관하니 제외), **OI-15 종결**(4.1 `RRRRLLLL` 확정) 경고 제거. ⚠️ **견본 개명이 바이트 대사 6개를 조용히 skip 시켰던 것을 발견해 고쳤다** — 경로 하드코딩 → glob, 없으면 skip 이 아니라 **실패**. DevNote **11.21**
- **바깥 백엔드용 확장점 + 결함 4건 (2026-08-24, 커밋 `ecf3487`)** — `ics_archon` 이 규약을 안 고치고 실기 백엔드를 끼울 수 있도록 **확장점 3개**를 열었다: `hardware.register_backend()` · `DetectorBackend.writes_files` · `DetectorBackend.begin_exposure(seconds, opens_shutter)`. 함께 고친 결함 4건 — ⓐ **D-016 충돌 선검사가 `[paths] write_fits` 에 묶여 있었다**(그 플래그는 시뮬 전용이라, 항상 파일을 쓰는 백엔드를 `write_fits=false` 로 돌리면 검사가 꺼진 채 **같은 이름을 조용히 덮어썼다**) ⓑ `data_dir`·`logging.file` 의 `~` 미확장(`os.makedirs` 가 `./~/AIC/data` 를 아무 불평 없이 만든다) ⓒ `_head()` 가 `\#` 를 안 벗겨 `FPAID='FPA\#1'` ⓓ **expnum 기록이 `os.replace` 뿐이어서 원자적이기만 하고 영속이 아니었다** — 전원 손실에 번호가 되돌아간다. 내용·디렉터리 둘 다 fsync. **시뮬 거동 무변경 · 규약 무변경.** 경위는 DevNote **11.24**
- **다음 단계**: ⓪ ⭐ **두 컨트롤러 병렬 독출 개정 (목 2026-08-24 지시, 착수 전 승인 필요)** — FRAME 검사를 두 대 동시에 · fetch 병렬(이미 됨) · 프레임별 `Acquisition Complete.`. **이 폴더의 규약을 고치는 첫 건**이고 위 ⚠️ 경고와 같은 자리다. 계획·비용·의견은 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "다음 세션 작업 지시" ① TCS 시뮬레이터 설치 + 연동 시험(아래 "이어서 시작하는 자리") ② **`ics_archon` v0.0 이 나왔다 (2026-08-23, DevNote 11.23)** — 과학 2 unit 제어·raw pair 저장·헤더까지 가짜 컨트롤러로 전 경로가 돌고 견본과 바이트 단위로 일치한다. 남은 것은 **실기 왕복**(미검증)과 **듀어·환경 HK**(`sensors()` — 원형이 없다), 그리고 **가이드 unit**(guide raw 규격 미정)이다. 결정·검토사항 목록은 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md)

## ▶ 이어서 시작하는 자리 (2026-08-26 기준)

**벤치가 SSO AIC 리눅스(`kmtnet-sso`)에 그대로 살아 있다.** 창 네 개 — 0=XIS · 1=`ics_sim` · 2=`obstool` · 3=`pctcs`. 기동 명령은 [README](README.md) "실물 연동 시험", 설치·빌드는 [`../TCSAgent/tcsagent_report.md`](../TCSAgent/tcsagent_report.md) · [`../OBSAgent/obsagent_report.md`](../OBSAgent/obsagent_report.md) 각 12절(`build-local.sh` 한 줄이면 재현된다).

| 순서 | 할 일 |
|---|---|
| **0** | ⏳ **관측 스크립트 첫 구동 결과 판정** — 위 "지금 진행 중" .  로그가 오면 그것부터 |
| ~~**1**~~ | ~~**`ExpNum` 교정의 실물 재확인**~~ — **완료 (2026-08-11 2차, DevNote 3.7.2).** 노출 2회로 판정: readout 중 `ExpNum` == 그 프레임의 파일 번호, 종료 후 `ExpNum`==`FitsNum`, `EXPNUM` 응답 N+1, `FitsOsc` `CHECK`→`NO`. 타임아웃 창 3종도 두 프레임에서 밀리초까지 동일. **전제였던 EXPNUM 카운터 결함을 먼저 고쳐야 했다**(11.12) — fail-safe 가 침묵해야 이 판정이 성립한다<br>※ **1회만 돌리면 판정이 안 된다.** OBSAgent 가 받은 값을 `strNextNum` 에 담아 두고 **다음 노출 시작 시** `strCurNum` 으로 승격해 표시하므로(`commands.c:835,848`), 1회 세션에서는 `ExpNum=00000000.000000` 이 정상이다 |
| **2** | **Telcom/AUX 시뮬레이터 설치** — KASI 제작본이 `../../__localonly_tcs_simulator/TCS_simulation.zip` 에 있다. **빌드가 없다**(stdlib 전용, Python 3.12+ 필요 — Ubuntu 24.04 기본이 3.12 라 그대로 된다). `pctcs.ini` 의 `TCS_Host`/`AUX_Host` 가 이미 `127.0.0.1` 이라 그대로 맞물린다. 절차와 함정은 아래 블록. 판정: 두 링크 `DOWN`→`UP`, `tstat`/`astat` 실값, 그리고 **`ics_sim` 의 텔레메트리 중계가 `passthrough`(빈 필드)에서 실값으로 바뀌는 것** — FITS 헤더의 AUX/TCS 키워드가 처음 실값을 받는 자리 |
| **3** | **세부 연동 시험** — `STOP`/`ABORT`(9.2.1 의 `DONE:` 본문은 실측 근거 없이 정한 것) · `GO n`(6.1) · `.osc` 스크립트 관측(3.5) · 결함 주입 6종(**실물 OBSAgent 의 경보·`opause` 경로를 확인하는 유일한 수단**) |
| **4** | **벤치에서 확인할 것 (2026-08-13, ⓐⓑ 는 2026-08-24 폐지)** — ~~ⓐ `siteid.detect()` 판정~~ · ~~ⓑ `[node] site = testbed`~~ → **사이트는 이제 `[node] observatory = KASI` 한 줄이다**(IP 판정 폐지, DevNote 11.27) ⓒ **`SHOPEN`+`aux_requery_after_shopen`(현행 **1초** — 2026-08-25 에 3초에서 내렸다)에 AUX 상태가 실제로 갱신돼 있나**(**OI-13**) — `SHUTOP` 가 그 시점에 `OPENING`/`OPENED` 중 무엇인지 실측해야 헤더의 `SHUTTER` 가 노출 중 값이라고 말할 수 있다 |

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

**pctcs 기반 프로브 4종**(`shut_probe`·`limit_probe`·`nc_probe`·`obsagent_probe`)은 `$PCTCS_DIR/ini/pctcs.localhost.sta.ini` 를 상대경로로 요구한다(이름이 하네스에 하드코딩). `build-local.sh` 가 만드는 것은 `~/AIC/Config/pctcs.ini`(ISISclient 모드, `TC`/6606) 하나뿐이지만, 빌드 시 `cp -R` 로 `ini/` 가 통째로 복사되므로 `~/AIC/build/TCSAgent/ini/pctcs.kmtna.sta.ini` 는 **이미 거기 있다.** 호스트 두 줄과 `LOGFILE`(`tc.sta` 로 갈라야 6606 벤치와 안 겹친다)·`CATFILE` 만 sed 로 고쳐 이름을 맞추면 된다. **STA 모드는 `TC.STA`/5755 라 본 벤치를 내리지 않고 돌릴 수 있다.** 우리에게 쓸모 있는 것은 `shut_probe`(`SET_SH` → `SHUTOP` 6전이가 실 pctcs 에서 어떻게 읽히는지)와 `nc_probe`(⑥의 대체 수단) 둘이다 — 선택 항목이므로 손으로 한 번 돌려 보고 쓸만하면 그때 스크립트에 굳힌다.

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
2. ~~**`ics_archon` 구현**~~ — **v0.0 완료 (2026-08-23, DevNote 11.23).** 실기 프로그램은 [`../ics_archon/`](../ics_archon/README.md) 에 있고 이 폴더를 사본 없이 가져다 쓴다. 남은 일(실기 왕복 검증 · HK 3계통 · 가이드 계통)은 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) 의 검토사항 표.
3. ~~`STOP`/`ABORT` 구현~~ · ~~`\KMTS`·`\KMTG` 소스 정독~~ — **둘 다 2026-08-05 완료.** 아래 "IC·ICG 계통 확정" 참조. ~~자기 발신 에코 처리~~ — **2026-08-08 완료**(위 "XIS 노드 등록" 참조).
4. **`icg` 착수** — 가이드 계통. OBSAgent 가 가이드 발신을 무시하므로 하위호환 부담이 없어 자유롭다. 공통 로직(IMPv2 노드, 텔레메트리 중계, 파일명 fail-safe)은 이 폴더에서 뽑아 쓸 수 있다.
5. ~~⭐ **두 컨트롤러 병렬 독출 개정**~~ — **완료 (2026-08-24, DevNote 11.26).**
   목이 범위를 좁혀 결정했다: *"ics_sim에서는 병렬독출 구현하지 말고, 간단히
   모사만 하고 ics_archon에서만 구현하자."* 그래서 이 폴더에 들어온 것은
   **계약 훅 + 스위치 + 얕은 모사**뿐이다.
   - 선택 훅 `DetectorBackend.readout_events()` — `('progress', pct)` ·
     `('frame', ctrltag)`. 없으면 `readout()` 로 떨어져 **구판 백엔드는 무변경**.
   - `[readout] acq_per_frame`(기본 `false`) · `acq_skew_warn`(1.0초).
   - `hardware/sim.py` 는 **시차 0 의 얕은 모사** — 목적은 이 분기를 `ics_sim`
     시험도 밟게 하는 것이다(시뮬이 훅을 안 내놓으면 새 분기가 실기에서 처음
     돈다). **병렬 독출 실구현은 `ics_archon`.**
   - `Sequencer.drain_writers()` — 종료가 저장 중인 프레임을 버리던 것(F3).
   - 시험 `tests/test_acq_per_frame.py` (5항목).

   ⚠️ **이것이 3.3 규약을 처음 연 건이다.** 기본값이 꺼짐이라 거동은 종전과
   같고, **켜면 `Acquisition Complete.` 4개의 산포가 두 컨트롤러의 실제 시차가
   되어 1.8초 창의 구조적 보장이 없어진다** — 실기 시차 실측 전에는 켜지 말 것.
6. **DevNote 13장 백로그** — 구조화 로깅, 상태 조회 API 등.
7. ~~**raw 헤더를 확정 초안에 동기화**~~ — **완료 (2026-08-22, DevNote 11.19).** raw spec v1.3 발행분 전량: 템플릿 주도 조립(`rawcards.py`) + 견본 v1.0 pair 바이트 대사 + D-016 + 카드 comment 지원. 잔여는 목 확인 2건(RADECSYS 기본 `'ICRS'` · ENS sentinel `'NC'` — 11.19)과 규격 OI 실측분(OI-15~18)뿐이다.

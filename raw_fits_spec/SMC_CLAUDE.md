# SMC_CLAUDE.md

`raw_fits_spec/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md), 이 폴더의 구성은 [README.md](README.md) 참고.

> ⚠️ **`../ics_archon/` 은 `main` 에 아직 없다.**  실기 ICS 는
> **`ics-archon-v1.0-build` 브랜치에서 진행 중**이고 **추후 `main` 합류 예정**
> 이다.  이 문서가 `../ics_archon/…` 을 가리키는 링크는 `main` 에서 열리지
> 않지만 **그 브랜치에서는 열린다** — 끊긴 것이 아니라 아직 안 온 것이다.

## 이 폴더가 뭔가

**Archon controller 가 직접 저장하는 raw FITS pair 의 규격을 관리한다.** `mef_fits_spec/` 이 출력(L0 MEF) 규격이라면 여기는 입력(Archon raw) 규격이다.

## ✅ 현행 규격 — raw spec v1.9 (2026-08-30 발행 · 푸시 · 태그 `raw-spec-v1.9` 완료)

**[`KMT_CEU_Raw_FITS_Specification_v1.9.md`](KMT_CEU_Raw_FITS_Specification_v1.9.md)** ("raw spec" / "로우 스펙") 이 현행이다 — v1.3 재작성판(구 "Raw FITS Pair 규격" v1.2 개명·대체) → v1.4 운영자 1~4장 검토 반영 → v1.5·v1.6 = 5장 검토분 → v1.7 = 파일명 넷째 필드 `<DETID>` 명명 → v1.8 = `OI-9` 폐기 + `CTRLnCFG` 예시 정합 → **v1.9 = guide raw FITS 9·10장 신설 + `Tapaculo`→`Radionode` 개명**. 구판은 `archive/`(v1.2 구명 Pair_Spec · v1.3 ~ v1.8).

- ⭐ **v1.9 발행분 (2026-08-30, 커밋 `7ea3d63` — origin 푸시 완료)** — 세 문서를 함께 판올림했다: **규격 v1.8 → v1.9** · **원장 v1.15 → v1.16** · **통합문서 v0.7 → v0.8** (구판 `archive/`). 발행·후속 정정을 **커밋 하나로 합쳐** 올렸다(운영자 지시 — main 커밋 수 최소화). 태그 `raw-spec-v1.9` 는 운영자 지시(2026-08-30)로 이 판의 마지막 커밋(인수인계 갱신 커밋)에 붙었다.
  1. **guide raw FITS 장 신설 (9·10장)** — 운영자 확정(2026-08-29) 방침대로 science 와 분리. 9장 = 파일명(`<DETID>`=`G`, pair 없음)·구조(4224×1033)·픽셀 배치([16 다크 기준열|512|512|16]×4블록, Y=1024+9), 10장 = 노출 의미론(셔터 무관 — `EXPTIME` = 독출 개시 간격 · 첫 프레임 폐기 · `DATE-OBS` = 직전 독출 개시 · **`go n` = `n`+1 독출 `n` 저장, 프레임당 파일 1개** — 운영자 확정 2026-08-30)·헤더(science 골격, **값 카드 123장** — `CTRL2*`·`C2_*` 미수록 · `CHMAP` 1장 · `IMGROT` 신설 · `ICGBUILD` · `C1_VOLT`/`CURR` 8자리+`HEATER`)·`C1_TEMP` 8자리(**OI-19 종결** — 구판 5.6.1절 `Mod9 HVYBias` 는 `HVXBias` 오기 정정)·guide 검증 체크리스트·**OI-20~24 신설**(10.6절). 구 9·10장(관련 문서·Revision History)은 **11·12장**이 됐다. 원전: `__reference/CCD47-20.pdf` · `__reference/guide_ccd_format.xlsx`(운영자 2026-08-30) · guide ACF `KMTK_GUI_162_STA0201_R2608` 실측 · gmon v2.
  2. **`Tapaculo` → `Radionode` 개명** (운영자 지시 2026-08-30) — 세 문서 살아있는 표기 전량(17곳) 교체, 5.6절에 구칭 앵커. `archive/`·레거시 실측 헤더는 그대로(사실 기록). ⚠️ 코드·문서 쪽 잔여 (**브랜치 충돌을 피해 여기서 안 고쳤다** — 브랜치 쪽 일감): ① `Radionode` 개명 — `ics_sim/ics_sim/hardware/archon.py:142` 주석 · `ics_sim/DevNote.md:1892` · 브랜치의 사본들 ② `ics_sim/ics_sim/fitsout.py:65` 주석이 구판(v1.2) 절 번호(`규격 5.1절 권장, 9장 OI-7`)를 인용 — 현행은 8장 OI-7 이고 9장은 guide 라 딴 곳을 가리킨다 ③ 브랜치 `ics_archon/acf/README.md` 의 "guide 8자리는 미해결 OI-19, 아직 규격에 안 실렸다" 문장 — v1.9 종결·10.4절 수록로 낡았다(머지 때 정정).
- ✅ **guide 헤더 견본 v0.0 확정 + 전수 대사 완료** (2026-08-30) — 운영자 확정 결정 다섯이 규격 10장에 반영됐다: `CTRL2*`·`C2_*` **미수록** · `CHMAP` 1장(`'NRL,ERL,SRL,WRL'` [TBC]) · **`IMGROT` 신설**(`'270,180,90,0'` [deg, CW], N·E·S·W) · **`ICGBUILD`** 개명(+ `TIMESYS`/`EXPID` comment 의 ICS→ICG) · `C1_VOLT`/`C1_CURR` **8자리**(`HEATER` +28 V, VOLT 소수 2자리). 견본은 클루디가 **11,520 B 로 패딩**(운영자 지시 — 144 레코드)했고 REFTEXT 사본(11,669 B)을 만들었다. **frame-transfer CCD 용어 확정**(운영자).
- 📋 **견본 v0.0 ↔ 10장 대사 목록** (오기·오타는 운영자 지시로 정정 완료 — 잔여는 v1.1 승격 때):
  1. ✅ **명백 오기 둘 — 정정 완료** (2026-08-30, 운영자 지시로 클루디 수정 + REFTEXT 재생성): ① `NAXIS1`/`NAXIS2` `19200`/`9400`(science 잔재) → **`4224`/`1033`** ② `AMPNAX1`/`AMPNAX2` `1033`/`4224`(축 뒤바뀜 + 4224 는 amp 값이 아니라 프레임 폭) → **`528`/`1033`** (합 불변식: 0+512+16 = 528 · 0+1024+9 = 1033).
  2. ✅ **오타 정정 완료** (2026-08-30, 운영자 지시) — `CHMAP` comment `outout` → `output`.
  3. ⏳ 목 판단 (OI-24 잔여) — `INSTRUME`(science 값 `'KMTA 18k CCD'` 잔존) · `FPAID`(`'FPA#1'` — guide 조립체 귀속) · `IMAGETYP` 어휘 · `FILENAME` 값 꼬리 공백 1자(`'…G '` 23자 맞춤 — 사소). ✅ ~~`CCDTEMP` comment~~ — **"M" 제거 완료** (2026-08-30, 견본 3장 — science 포함). ✅ ~~`DETID` comment~~ — **`'Detector ID in this raw FITS file'` 로 정정 완료** (운영자 확정 2026-08-30, 클루디 수정 + REFTEXT 재생성).
  4. ⏳ 실측 (OI-21·22) — `CHMAP` 값 [TBC] · `IMGROT` 값 검증 · `PIXSCALE` 0.49/0.51/0.52 · ⚠️ 칩 순서 견본 N·E·S·W vs gmon 잠정 n,s,e,w 어긋남(한쪽 확정 필요). **운영자 지시(2026-08-30): 다음 판에서 실측 확인 후 갱신** — 이번 라운드에서는 더 건드리지 않는다.
  5. ⏳ **최종 검토(2026-08-30, 커밋 후 전수 재검)에서 추가된 확인 항목** — v1.1 승격 때 함께:
     - ✅ ~~`C1_VOLT` 절사/반올림~~ — **해소 (2026-08-30, 운영자 확정)**: **규칙은 반올림**("소수 셋째 자리에서 반올림", 10.4절 명시)이고, **견본 샘플값은 절사 그대로 둔다** — 임의 샘플이라 수정 대상이 아니다(운영자: "견본을 수정할 필요는 없었는데. 반올림이란 것만 문서에 명시해두면 되"). 규칙-샘플값 표면 불일치는 결함이 아니다.
     - `OVRSCNY` comment `(frame-center side)` — science 문구가 그대로 왔는데 guide 의 추가 9행은 **중앙이 아니고 위치도 미정**(OI-21)이다 — v1.1 때 문구 정정.
     - `OVRSCNX` comment `(side varies)` — 10.3절 권고대로 다크 기준열 성격 병기 검토 (80바이트 예산 확인).
     - `EXPTIME=0` · `IMAGETYP='BIAS'` 시나리오 — guide 의미론상 `EXPTIME=0`(독출 간격 0)은 실현 불가한 견본값 — v1.1 때 현실 시나리오(예: 1초) 검토.
     - `CAMVER='CEU-v2.1'` 이 science 와 동일 — guide 계통이 같은 카메라 전자부 버전 문자열을 공유하는지 확인 (OI-24 등재).
     - COMMENT 2번("Map of CCD output channels, raw X ascending within each card")이 science 문구 그대로 — 골격 규칙(10.2)상 유지 가능하나 guide 는 카드가 하나라 "each card" 가 안 맞음, 문구 조정 선택.
- ⏭️ **판올림 이월 대기 4건** (구 "v1.9 대기 5건" — ~~`CCDTEMP` comment `M` 제거~~ 는 **2026-08-30 운영자 지시로 조기 실행**: G·MK·NT 견본 3장 + REFTEXT 제자리 반영, 5.6절·원장·통합 문구 갱신. ⚠️ 브랜치 기계 사본 3곳·바이트 대사 시험이 어긋남 — 머지 때 동반 수정): `OI-18` 폐기 · `CAMVER` 범프 규범 명시 · **바이어스 측정값의 헤더 카드 배치**(D3) · ⭐ **`RDMODE` 결측값 `UNKNOWN` 등재**(5.5절 + 5.0절 sentinel 어휘 — **코드는 이미 갔다**, 운영자 확정 2026-08-29). **견본 v1.1 승격 라운드에서 함께 처리**가 자연스럽다(넷은 견본 카드 변경을 동반한다). 상세는 [`../ics_archon/SMC_CLAUDE.md`](../ics_archon/SMC_CLAUDE.md) "규격 쪽 후속".
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

방침(운영자 확정 2026-08-29 — 같은 문서 안 별도 장, science 와 섞지 않기, 같은 점·다른 점 절)대로 **v1.9 에서 신설했다.** `OI-19` 는 10.4절 수록으로 **종결**, guide 고유 미결은 **OI-20~24**(10.6절)로 등재됐다. 남은 것은 **목 검토 → 견본 v0.0 확정 대사 → v1.1 승격**이다.

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

⏳ **실측 확정 전인 것 — OI-20 으로 등재됐다** (v1.9 10.6절): 저장되는 528 이 시퀀서가 읽는 600(+1) 중 어느 구간인가. **데이터시트 대응은 나왔다** — CCD47-20 레지스터 반쪽은 `8 BLANK | 15 DARK REF | 1 transition | 512 active` 이고 blank 8 은 `PreSkipPixels=8` 로 건너뛰므로 **저장 528 의 선두 16 = 다크 기준열 15+1(차광 실컬럼, 프리스캔 아님)** 로 지목된다. 확정은 P-k 실측(`Pixels` 600→528 트림 무손실 검증) 몫이고, 그때 `PRESCNX`/`OVRSCNX` 귀속(10.3절 잠정값)이 닫힌다. `gmon` 커미셔닝 §10-1 과 공동.

- **절 구성이 구판과 다르다** — 구판 절 번호를 인용한 문서·코드 주석(`규격 5.7절` 등)은 현행 기준으로 재확인. ⚠️ **v1.4 에서 2.5절(Wrote 통보)이 삭제돼 절 번호가 또 바뀌었다**(2장은 2.1~2.4). `ics_sim` 쪽 참조 정리는 **완료**(2026-08-22, v1.3 정렬과 함께 — 아래 "다음 사람이 할 일" 3). ICD v4.1 §12 의 위임 대상 갱신은 LEECU 몫으로 남아 있다.
- 헤더 5장의 바이트 단위 정본은 **초안 헤더 v1.0 pair**(`KMTA...MK/NT.fits.header.v1.0.txt`)다.

## 먼저 읽을 것

| 문서 | 지위 |
|---|---|
| `KMT_CEU_Raw_FITS_Specification_v1.9.md` | ✅ **현행 raw spec** — 최종 정의·규격 (science 1~8장 + guide 9·10장). 배경은 아래 원장·통합 문서로 링크 |
| `KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.16.md` | **이 폴더에서 지금 가장 쓸모 있는 문서** (v1.16 = `Radionode` 개명, 판정 불변). **0장이 판정 준거다**(준거 순위 · converter 3상태 × ICD 규정/침묵 · 준거 공백 크기) — v1.14 에서 구 검토 문서 폐기분을 본문으로 편입했다. converter 가 읽는 것 · 읽지 않는 것 · 도입 후보·확정 · 폐지된 것을 13장으로 정리했다. v1.10 판정 완결(미정 0) → v1.11 돔 Source TCS 전환 + 확인 요망 1~5 종결 → v1.12 확인 요망 9 종결(HK 문자열·sentinel `'-999.99'`) → **v1.13 잔여 전량 종결(6·7·8·10·11) + D-016 등재 — V1 착수 조건 완성** — 최근 구판은 `archive/` |
| `KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.8.md` | **통합 문서** (v0.8 = `Radionode` 개명, C-항목 불변) — Part 1: LEECU 전달용 C-항목·이름 대응·MEF/converter 쪽 미결 4건 / Part 2: 번호·충돌·정체성 **파급 요약**(정본 = raw spec 2.3절 + D-016). 전신 v0.5 는 `archive/`, v0.4·v0.2 는 git 이력·외부 백업 |
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

  | 판 | 마지막 커밋 | 태그 |
  | --- | --- | --- |
  | v1.4 | `e1cb82f` (`Merge branch 'raw-fits-spec-v1-review'`) | 삭제됨 (2026-08-25) |
  | v1.5 | `13e02b2` | 삭제됨 (2026-08-26, v1.6 발행) |
  | v1.6 | `6d9c137` | 삭제됨 (v1.7 발행 즈음 — 2026-08-30 실측에서 부재 확인) |
  | v1.7 | `182b7f3` | **삭제됨 (2026-08-30, v1.9 태그와 함께 정리)** — ⚠️ v1.8 발행 때 방침대로 지워졌어야 했는데 로컬·원격에 남아 있었다 |
  | v1.8 | `8ed6385` (`raw spec v1.8 발행`) | **삭제됨 (2026-08-30, v1.9 발행)** — ⚠️ 메모리·기록의 "태그 → `0c821ea`" 표기는 오기였다, 실측 8ed6385 |
  | **v1.9** | 인수인계 갱신 커밋 (2026-08-30 — `7ea3d63` 발행 커밋 직후) | **`raw-spec-v1.9` (현행)** |

  ⚠️ **팀 알림 (2026-08-30)**: `raw-spec-v1.7`·`raw-spec-v1.8` 이 원격에서 삭제되고 `raw-spec-v1.9` 가 신설됐다 — 이미 받아 둔 쪽은 `git fetch --tags --prune --prune-tags` 로 정리해야 한다.


## 준수 우선순위 (v0.7 검토 문서 0장에서 확립)

```
1  mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md    준거
2  mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py   L0 MEF 산출 주체
3  mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md 참고 (converter 미러)
```

- **raw 쪽 기준선은 레거시 raw 실측 헤더**다. `ics_sim` 의 현재 출력은 미완성 구현이라 판정 근거로 쓰지 않는다.
- 레거시 **MEF** 헤더 33건은 배경지식이지 판정 근거가 아니다. 레거시 **raw** 헤더 1건만 근거다.
- **ICD 는 PRIMARY keyword 를 열거하지 않는다.** converter 가 만드는 카드 이름 210개 중 ICD 에 나오는 것은 36개뿐이고 174개(83%)가 없다. 그 침묵 구간이 곧 이 검토가 결정할 몫이다.
- 확정된 근거는 `../project_management/governance/DECISION_LOG.md` 의 **D-번호**다. 이 폴더가 기대는 것은 **D-011**(사이트 코드 파일명) · **D-013**(레거시 keyword 판정) · **D-016**(충돌 번호 증가 · `FILENAME`/`ORIGNAME` 정체성, 2026-08-22 등재).

## ▶ 이어서 시작하는 자리 (2026-08-25 기준)

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
| ~~`siteid.py`~~ | `BENCH_SITE = 'KMTK'` — ⚠️ **그 파일은 2026-08-24 에 삭제됐다**(D-015 폐기). 이 행은 당시 `main` 기준 기록이다 |
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
  3. ~~**ics_sim 구현 일감** — v1.3 정렬~~ — **✅ 완료 (2026-08-22, ①~⑤ 전량 + 대사 테스트).** 헤더 층이 **템플릿 주도**로 재편됐다: `ics_sim/ics_sim/rawcards.py` 가 초안 v1.0 pair 의 기계 사본이고, `tests/test_raw_draft.py` 가 견본 값 역산 → **바이트 단위 재현**(MK·NT 불일치 0)을 대사한다. D-016(선검사·되감음·상한·카운터 동기화), 신설·폐지 카드 전량, `fits_shape = spec` 실물 기하 이미지 생성 + **converter end-to-end L0 MEF 생성 검증**까지. 같은 날 `ics_archon/archon_kmtnet_labtest_v1.1.bigbuf.py` (실험실 취득 스크립트)에도 v1.3 을 적용했다(내장 템플릿 동일 원천). 경위·판단은 `../ics_sim/DevNote.md` **11.19** — **목 확인 대상 2건**(RADECSYS 결측 기본 `'ICRS'` · ENS1~7 결측 sentinel `'NC'`)이 거기 있다.
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

**2. 기본값이 진짜 값처럼 보인다.** converter 는 카드가 없어도 오류를 내지 않는다.

- `DATE-OBS` 없으면 **변환 시각(now)** 으로 대체 — 이 문서 전체에서 가장 위험하다
- `RA`/`DEC` 없으면 `"00:00:00.00"` — 형식이 유효해 하류에서 안 걸린다
- 버전 문자열 9종은 `"ARCHON-v1.0"` 처럼 **그럴듯한 provenance** 가 박힌다
- **오류로 걸리는 것은 `OBSERVAT` 하나**(파일명 사이트 코드 교차 검증, D-011)

**3. converter 는 raw geometry 를 하나도 읽지 않는다.** `OSCNPATT`·`ROWORDR`·`RDDIRT`/`RDDIRB`·`AMPMAP`·`AMOD`/`ACHN`·`NXTILE`·`CHIPS`/`CHIP1`/`CHIP2` 는 **소스에 이름조차 없다.** 나머지는 자기 상수로 만들어 내보낸다. `OVERSCAN_X=48` 은 표기용이 아니라 **실제 픽셀 절단 좌표 계산에 쓰인다.** → 변경점 C-5 · C-11 · C-12 · C-13

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

⚠️ **이 절은 2026-08-20 재작성 전 기록이다** — 당시 OI 번호는 구판 v1.2 9장 기준이고, **현행 OI 정본은 규격 v1.9 의 8장(science) + 10.6절(guide)** 이다. 서술도 구식이다(예: OI-3 의 `ROWORDR`/`RDDIRT`/`RDDIRB` 는 폐지되고 4.3절 포장 조항 준수 검증으로 바뀌었다). 아래는 경위 참고용으로만 남긴다.

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

이 브랜치가 갈라져 나온 자리는 **`6b19ad6`** 이다(v0.7 검토판 + 규격에 ((재작성중)) 표시를 붙인 커밋). 이 해시는 뒤에 뭘 더 쌓아도 안 바뀐다.

## 문서 생성 수단의 현재 상태

- **md → docx 변환기는 저장소에 있다** — `tools/md_to_docx.py` (71a1989 에서 도입). 개정판을 만들면 이것으로 `__review/` 에 전달본 docx 를 생성한다(상시 규칙).
- **원천 추출 생성기(converter 소스 → md)는 여전히 없다** — v1.6 까지의 기계 추출 스크립트는 세션 scratchpad 와 함께 사라졌고, **v1.7 부터는 수기 개정 체제**라 당장 필요하지 않다. converter 가 크게 바뀌어 3~6장을 다시 기계 추출해야 할 때만 재작성한다(추출 규칙은 v1.6 머리말: `card("<MEF>", v("<raw>", <기본값>))` 정규식 파싱, 4.H 절·5.13 폐지 표를 표 블록으로 읽기). `Raw Archon` 열과 `도입 여부` 열은 사람이 채우는 계획 열이므로 그때도 보존해야 한다.

## 관련 문서

| 문서 | 위치 |
|---|---|
| L0 MEF ICD (1위 준거) | [`../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md`](../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md) |
| Converter | [`../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py`](../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py) |
| 취득 SW 구현 | [`../ics_sim/SMC_CLAUDE.md`](../ics_sim/SMC_CLAUDE.md) · `../ics_sim/DevNote.md` 11.14 |
| 결정 기록 | [`../project_management/governance/DECISION_LOG.md`](../project_management/governance/DECISION_LOG.md) |
| 등재 | [`../project_management/planning/ACTION_REGISTER.md`](../project_management/planning/ACTION_REGISTER.md) **ACT-011** |

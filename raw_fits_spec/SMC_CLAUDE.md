# SMC_CLAUDE.md

`raw_fits_spec/` 폴더에서 작업을 이어갈 때 참고할 컨텍스트. 저장소 전체 개요는 [../README.md](../README.md), 이 폴더의 구성은 [README.md](README.md) 참고.

## 이 폴더가 뭔가

**Archon controller 가 직접 저장하는 raw FITS pair 의 규격을 관리한다.** `mef_fits_spec/` 이 출력(L0 MEF) 규격이라면 여기는 입력(Archon raw) 규격이다.

## ⚠️ 지금은 현행 규격이 없다 (2026-08-18 부터)

`KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 는 파일로는 남아 있지만 **⛔ ((재작성중)) 표시가 붙었고 근거가 아니다.** 제목 · 첫 화면 · 버전 줄 세 곳에 표시가 있다.

- **재작성판이 나올 때까지 이 규격을 인용하거나 근거로 구현하지 않는다.** 절 번호(5.x · 7장 · 9장)도 바뀔 수 있다.
- 다른 문서·코드에 남은 참조 16곳은 **경로로는 유효하지만 근거로는 무효**다.
- 특히 **ICD v4.1 §12 가 이 문서의 5장에 필요한 raw 텔레메트리 집합을 위임**하고 있고, `ics_sim` 의 `rawhdr.py` · `rawpair.py` · `hardware/archon.py` 가 5장을 구현한다. 재작성 시 이 의존을 함께 정리해야 한다.

## 먼저 읽을 것

| 문서 | 지위 |
|---|---|
| `KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.12.md` | **이 폴더에서 지금 가장 쓸모 있는 문서.** converter 가 읽는 것 · 읽지 않는 것 · 도입 후보·확정 · 폐지된 것을 13장으로 정리했다. v1.10 판정 완결(미정 0) → v1.11 돔 Source TCS 전환 + 확인 요망 1~5 종결 → **v1.12 확인 요망 9 종결(HK 문자열·sentinel `'-999.99'`) — 잔여 5건(결정 10·11 / 재가 6·7·8)** — 최근 구판은 `archive/` |
| `KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md` | **통합 문서 (2026-08-22)** — Part 1: LEECU 전달용 MEF ICD·정의서·converter 개정 요청(C-항목 · 이름 대응 · 키워드맵 이관 미결 4건) / Part 2: 번호·정체성·충돌 처리(D-016 결정문 초안 §8). 전신 MEF_Impacts v0.4 · Numbering v0.2 는 `archive/` |
| `archive/KMT_CEU_Raw_to_MEF_Keyword_Map_v0.7_REVIEW.md` | 검토용 — **흡수 완료 후 archive 이동(운영자 재가 2026-08-22)**: 판정은 Header_and_Refs, 미결 4건은 통합 문서 Part 1 §6. 배경 자료(전수 대응표·인벤토리)로만 유효 (ACT-011) |
| `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` | ⛔ ((재작성중)). 참고만 |
| `__reference/Legacy raw fits header samples/` | **raw 쪽 기준선.** `KMTNk.20170209.044131.Rawheader.txt` keyword 123개 |

## 개정 워크플로 — `__review/` 는 임시 왕복함 (운영자 확정 2026-08-22)

**검토 사이클이 열릴 때만 `__review/` 를 만들어 쓰고, 끝나면 결과물을 이 폴더 루트에 저장한 뒤 `__review/` 는 지운다.** 상시 폴더가 아니다 — 2026-08-22 에 첫 적용: 초안 헤더가 **`KMTA.20260818.012345.MK.fits.header.v1.0.txt`** 로 승격되어 루트로 왔고, docx 왕복본·초안 이력(v0.0~v0.4.4)은 운영자 외부 백업(`__backup_raw_fits_spec_oldver`)으로 나갔다. 전달용 docx 는 검토 사이클이 있을 때만 `tools/md_to_docx.py` 로 만들어 `__review/` 에 둔다(변환기는 저장소 유지 — pandoc 없는 환경 전제, python-docx 만 사용). `__` 접두 폴더 읽기 전용 규칙은 그대로다 — 안의 파일은 읽기만 하고 **편집하지 않는다. 편집이 필요하면 그 파일을 sub레포 루트로 옮겨서(사본) 작업한다**(운영자 확정 규칙 2026-08-22). 클루디 산출물(docx) 신규 생성은 허용. 왕복 중 결정의 근거는 항상 md 판 changelog 에 반영하므로 docx 중간산물이 이력에서 빠져도 근거는 남는다.

## 준수 우선순위 (v0.7 검토 문서 0장에서 확립)

```
1  mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md    준거
2  mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py   L0 MEF 산출 주체
3  mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md 참고 (converter 미러)
```

- **raw 쪽 기준선은 레거시 raw 실측 헤더**다. `ics_sim` 의 현재 출력은 미완성 구현이라 판정 근거로 쓰지 않는다.
- 레거시 **MEF** 헤더 33건은 배경지식이지 판정 근거가 아니다. 레거시 **raw** 헤더 1건만 근거다.
- **ICD 는 PRIMARY keyword 를 열거하지 않는다.** converter 가 만드는 카드 이름 210개 중 ICD 에 나오는 것은 36개뿐이고 174개(83%)가 없다. 그 침묵 구간이 곧 이 검토가 결정할 몫이다.
- 확정된 근거는 `../project_management/governance/DECISION_LOG.md` 의 **D-번호**다. 이 폴더가 기대는 것은 **D-011**(사이트 코드 파일명) · **D-013**(레거시 keyword 판정).

## ▶ 이어서 시작하는 자리 (2026-08-22 기준)

### 2026-08-22 확정분 · 최신 2 (확인 요망 9 확정 = v1.12 · 초안 v1.0 승격)

- **확인 요망 9 종결 — HK 온도·습도 카드는 문자열 계승** (레거시도 문자열 `'-103.16'` · converter pass-through — 아카이브 형 통일). 표기: HK ±소수 2자리(`'+16.78'`), FSA 2장은 ENS식 잠정(소수 1자리, Tapaculo 원값 포맷 확인 후 최종 — 실기 확인 항목). **측정불가 sentinel = 온도·습도 전 카드 `'-999.99'` 단일값** (기각: `-99.99` 는 CCDTEMP 냉각 램프 통과값, 습도 `0.00` 은 유효 측정값). ics_sim 반영: `format_temp()` 신설 + thermal_header 문자열 전환 + 테스트 교체.
- **초안 헤더 v1.0 승격** (운영자) — `KMTA.20260818.012345.MK.fits.header.v1.0.txt` 를 폴더 루트로, 내용은 마지막 커밋본과 동일(143카드, diff 0). `__review/` 폐지, archive 는 v1.8~v1.11 만 유지(그 이전 판·docx·초안 이력은 외부 백업).

### 2026-08-22 확정분 (운영자 5차 개정 + 확인 요망 4·5 확정 = v1.11 로 닫힘)

- **돔 Source 전면 변경** — 계승 6장 + `DSAZ`/`DSTELALT`/`DSTELAZ` 가 `AUX relay` → **`TCS relay or REDIS*`**, `DALTERR`/`DAZERR` 는 **`ICS calculation`**. newTCS 전환으로 dome shutter control 이 TCS 에 편입 — 초안 DS 블록도 TCS 절로 이동(3.6절, 절명에서 "AUX" 제거).
- **확인 요망 1~5 종결** — ① chiller 재삭제 ② `FSATEMP`/`FSAHUM` 반영 ③ 돔 4장 반영(모두 초안 v0.3.7 전수 대사 검증) ④ **`EXPTIME`/`LEDFLASH` 정수형** — `EXPTIME` 은 소수점 있으면 실수형, **`LEDFLASH` 는 [ms] 로 단위 변경**(D-013 "초 유지" 번복 — comment 에 단위 명시, `ics_sim` ms÷1000 제거) ⑤ **`ICSBUILD` = `v<버전>:<빌드일시>Z`**(프로그램명 제거 — 식별은 `DATASRC`, `ics_sim` `build_id()` 개정 + `PROGRAM` 상수 삭제 + 테스트 교체, 전체 325 통과). **ics_sim 변경분은 v1.11 문서 배치와 함께 커밋(운영자 지시)**.
- **문서 통합 (운영자 지시)** — MEF_Impacts v0.4 + Numbering v0.2 → **`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md`** (Part 1 = MEF 개정 요청 / Part 2 = 번호·정체성). 키워드맵 v0.7 잔여 미결 4건(`NCTRL`·`CTRLID` 개칭·`SATURAT`/`SATLEVEL`·`DATASRC`/`CTRLnCFG` MEF 목적지)을 Part 1 §6 으로 이관 — **키워드맵은 archive 로 이동 완료(운영자 재가 2026-08-22)**.
- 남은 것: **확인 요망 6건**(결정 9 HK 온도 형 · 10 PRESCN 삼자 모순 · 11 규격 버전 선언 / 재가 6 CTRL1ID 값 · 7 "– 철회" 라벨 · 8 XTALKVER 귀속 표기) **+ D-등재(D-016, 통합 문서 Part 2 §8 초안)** → 닫히면 V1 재작성 착수.

### 2026-08-22 확정분 · 추가 (운영자 4차 개정 = v1.10 으로 닫힘)

- **`CHKIMG` · `CHKIMG_C` → `X`** ("Pipeline 에서 판별하는 대상") — **도입/계획 판정 미정 0 달성**, 키워드맵 검토 항목 9 전량 종결.
- **6장 `DSTEL` → `O` (`DSTELALT` 로 변경 적용)** — 6장 마지막 빈칸 소멸.
- **`OVERSCNY` 개명(`OVRSCNY`) 후속 지시** — 위험 사유와 개명을 V1 규격·MEF Impacts(ICD 개정 후보)에 수록. ※ 운영자 원문 "OVRSCANY" 는 `OVRSCNY` 오탈자로 교정 반영(확인 대기).
- 남은 것: **확인 요망 11건 일괄 판정 + D-등재** → 이 둘이 닫히면 V1 재작성 착수.

### 2026-08-22 확정분 (운영자 3차 개정 = v1.9 로 닫힘)

- **7장 도입 여부 전면 판정 완결** — 도입 `O` 20+ 장 · 미도입 `X` 28+ 장, **미정은 `CHKIMG` · `CHKIMG_C` 2장뿐**.
- **`RDMODE` 개명 도입** — raw 독출 속도 모드 선언. MEF `READMODE`(`'64AMP'`, 구조 선언)와 이름이 갈라져 **값 충돌 미결이 종결**됐다 (MEF Impacts v0.4 3장에 해소 표시).
- **`BCKTEMP` → `Cn_TEMP`/`Cn_VOLT`/`Cn_CURR` 확장** — 컨트롤러별 텔레메트리 3종(모듈 순서 명세는 spec 수록 예정). MEF `VOLTINFO`/`TELEMETRY` 공급원 **C-후보**로 연결 (MEF Impacts v0.4 1장).
- **`CAMVER` 신설** — 카메라 시스템 버전 선언.
- **미도입 `X` 확정** — `CTRLTAG` · `PAIRFILE`(pair 식별은 `FILENAME` 꼬리 `.MK`/`.NT` 로 충분) · `OSCNPATT` · `RDDIRT`/`RDDIRB` · `MIDOSC*` · 전압 색인 계열 · `RAWVER`/`RAWPROD` · `FSADEW`/`FSAALRM`. → Numbering v0.2 · MEF Impacts v0.4 에 반영 완료.
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
- **충돌 처리 · 정체성 재설계 확정** — 번호 공간 000000–099999, 충돌 시 pair 선검사 + 번호 증가(상한 100000회 초과 시 ERROR·저장 안 함), 카운터 동기화. `UNIQNAME`·`NAMECLSH`·`clash/` 폐지, `FILENAME`(유일 키)+`ORIGNAME`(항상 기록, 불일치=충돌 신호). 정리본: [`KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md`](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md) **Part 2** (D-등재 대기, 결정문 초안 §8 — 구 Numbering v0.2 는 `archive/`).
- **MEF 쪽 개정 요청 목록**: 같은 문서 **Part 1** (LEECU 전달용 — MEF `UNIQNAME` 공급원, C-11 CHMAP 개정, 키워드맵 이관 미결 4건 등 — 구 MEF_Impacts v0.4 는 `archive/`).
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

**레거시 `READOUT = 'ARLBRL'` 의 정체** — OSU IC 펌웨어(`../../__localonly_osu_legacy/IC2_*/IC2.img`)에 FreeBASIC 원본이 통째로 들어 있고, `SUB SetReadout()` 이 이렇게 하드코딩한다:

```basic
'-- Four amp readout only
Amps = "ARLBRL" : XAmp = 2 : YAmp = 2
TopDelaceCode = 8 : BotDelaceCode = 10  '-- swap to register quadrants correctly
```

`XAmp=2, YAmp=2` 사분면 전제 + de-interlace 순서가 얽힌 부호이고, 레거시 표본 3건 — 2017 raw(SSO) · 2021 raw(CTIO) · MEF primary — 이 **전부 같은 값**이다(불변 상수). **D-013 의 폐지 판정이 옳았음을 뒷받침한다.**

**레거시 IC 에 ROI 가 있었다** — 같은 펌웨어의 `READOUTSETVAR` 에 `OSCANX`/`OSCANY` 와 경고문이 있다: *"Region-of-interest has been modified to maintain symmetry around CCD centerline."* ICS 명령 테이블에는 없어 운영에서 쓰이지 않았다. v1.6 10장(subframe)의 근거가 된다.

**레거시 `AMPSEC` 이 독출 방향을 담고 있었다** — 레거시 MEF 실측 32장을 보면 `AMPSEC` 이 `CCDSEC` 과 같은 범위인데 **순서가 뒤집힌 것이 있다**(`K01`: `CCDSEC='[8065:9216,...]'` vs `AMPSEC='[9216:8065,...]'`). IRAF 관례대로 **구간의 오름/내림차순이 곧 독출 방향**이다. 전량 패턴은 `M/T = 5:3`, `K/N = 3:5` 인데 **우리 신규는 4:4 를 전제**한다 — 같은 e2v CCD290-99 인데 분할이 다르므로 한쪽이 틀렸다. flat 이나 STA 문서로 확인이 필요하다.

## 미결 항목

규격이 재작성중이라 OI 번호는 v1.2 9장 기준이다.

| ID | 무엇 | 상태 |
|---|---|---|
| **OI-3** | `ROWORDR`/`RDDIRT`/`RDDIRB` 확정 | 실기 flat/star 필요. ICD §12 도 `READDIR` 을 placeholder 라 밝힌다 |
| **OI-4** | 중앙 overscan 의 TOP/BOT 분배 | 실측 필요. `OVERSCNY=84` 는 균등 가정 |
| **OI-5** | binning | 1×1 전용. binned 관측 계획이 서야 |
| **OI-9** | amp ↔ 배선 맵 실측 | `XTALKCAL=True` 의 전제조건. `AMPCHA`/`AMPCHB` 가 **CCD 출력단**을 담고, **Archon module/channel 은 그 다음 단**이라 아직 미확정 |
| — | **부분 독출(subframe·ROI·window)** | **규격에도 미결 목록에도 없다.** v1.6 10장이 제기만 해 둔 상태. 쓸 계획이 있는지부터 정하고 OI 로 세워야 한다 |
| — | Archon AD 모듈당 채널 수 · TAPLINE 표기 | 저장소 증거는 `MOD5`~`MOD8`(AD 4장)뿐. STA 문서나 Tom O'Brien 협의 필요 |

## 브랜치 상태

작업은 **`raw-fits-spec-v1-review`** 브랜치에 쌓고 있고, **`main` 위에 얹힌 채 아직 원격에 올리지 않았다.** 몇 개가 쌓였는지는 여기 적지 않는다 — 커밋할 때마다 이 문장이 낡기 때문이다. 직접 본다:

```bash
git log --oneline --decorate main..raw-fits-spec-v1-review
```

`main` 은 `origin/main` 과 같은 자리라 **fast-forward 로 들어간다** — `git merge --ff-only raw-fits-spec-v1-review`.

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

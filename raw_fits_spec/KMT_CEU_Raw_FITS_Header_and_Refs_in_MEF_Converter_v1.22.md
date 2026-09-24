# raw FITS 헤더 카드 — converter 가 읽는 것 · 읽지 않는 것 · 도입 후보 · 폐지된 것

**v1.22** · 개정 2026-09-24 · **`OBSTYPE` 사용자 입력 카드 · `EXPTIME` 실수형 · comment 문안 정정** (raw spec v1.16 동반) — 운영자 결정(2026-09-24)을 옮겼다.  ⭐ 3.1절 `OBSTYPE` 행을 **사용자 입력으로만 바뀌는 카드**(`PROJID` 와 같은 부류)로 고쳤다 — 기본값은 science `'SCIENCE'` · guide `'GUIDE'` 이고, 빈 값이 와도 기본값이며 `IMAGETYP` 을 복사하지 않는다(raw spec v1.13 ~ v1.15 의 빈 값 폴백 폐지).  raw spec v1.13 이 적은 뜻 *"어느 계통이 찍었나"* 는 기본값의 성질로 내려갔다 — 사람이 바꿀 수 있으므로 계통 식별은 `DATASRC` · `DETID` 가 맡는다.  13장 *"개칭 없이 뜻이 바뀐 카드"* 의 `OBSTYPE` 도 같이 고쳤다.  ⭐ 3.1절 `EXPTIME` 행의 형을 **Integer → Real** 로 고쳤다 — 소수점 아래 최소 한 자리(`0.0` · `2.0`, raw spec v1.16 5.4절 — 확인 요망 4 종결의 *"정수형 기본"* 을 운영자가 2026-09-24 에 고쳤다).  함께: 7장 `PRESCNX`/`PRESCNY`/`OVRSCNX`/`OVRSCNY` 행 설명에 comment 괄호를 옮겨 적었던 자리 표기(*"side varies"* · *"frame-edge side"* · *"frame-center side"*)를 걷고 `OVRSCNX`/`OVRSCNY` 의 자리는 규격 4.1절 · 4.2절을 가리키게 했다(네 카드 comment 의 괄호가 걷혔다 — 규격 5.2절) · 8장 `OVERSCNY` 행과 8.1절 `OVERSCNX` 행의 *"대신 보는 것"* 칸도 같은 표기 정리(*"frame-center side"* → 영상 중앙 · 규격 4.2절) · 3.7절 `CCDTEMP` 행과 그 아래 단락의 comment 인용 `CCD temperature` → **`CCD temperature [deg C]`**(견본 · 규격 5.6절과 맞춤 — v1.21 까지 단위를 뺀 채 comment 전체처럼 적었다) · 11.1절 `RAILREF` 행에 raw spec v1.16 · 통합 문서 링크 표기 v1.1 → **v1.2** · 규격 참조 v1.16.  `Raw Archon` · 도입 여부 · `Use in MEF` 판정에는 변화가 없다 — converter v2.5.0 은 `OBSTYPE` 을 raw 값 그대로 옮기고(`v("OBSTYPE","")`) raw comment 는 읽지 않으며, `EXPTIME` 은 `fnum()` 으로 읽어 늘 실수로 쓴다.
> 구판 **v1.21** · 개정 2026-09-24 · **발행본 재검토 정정** (raw spec v1.15 동반) — raw spec v1.14 발행본 재검토(2026-09-24)에서 반증을 통과한 발견 가운데 원장 몫을 실었다.  ⭐ 7장 `RDMODE` 행의 결측 낱말을 **`'NC'`** 로 고쳤다 — 운영자 결정(2026-09-24, 규격 5.0절 · 5.5절 — 종전 `'UNKNOWN'`)이 v1.20 에 옮겨지지 않아 원장만 자기가 인용한 절과 반대 값을 적고 있었다.  같은 행에 converter 쪽 사실(raw `'NC'` 는 MEF 로 그대로 가고 기본값 `'UNKNOWN'` 은 카드가 없을 때만 들어간다)과 v1.13 까지의 규칙으로 찍힌 raw 의 `'UNKNOWN'` 을 적었다.  함께: 3.7절 `CCDTEMP` 단락의 *"MEF/L1 쪽 정의 문구("평균 파생")의 갱신은 C-항목이다"* 를 **해당 없음**으로(하류 어디에도 그 문구가 없다 — 통합 문서 v1.1 §1) · 8.2절 끝에 `EXPID` 이름 재사용 경고 한 줄(구판 v1.2 의 `EXPID` 와 섞지 않는다 — 되살린 근거는 규격 12장 v1.6 행) · 3.7절 미연결 RTD 예시 `'-273.20'` → 실측 **`'-273.15'`**(규격 5.0절 · 10.4절 정정과 맞춤) · 3.7절 sentinel 사유 셋 → **넷**(`HKDATA NOW` 답 없음 — 규격 5.0절 정정과 맞춤) · 통합 문서 링크 표기 v1.0 → **v1.1** · 11.1절 `RAILREF` 행에 raw spec v1.15 · 규격 참조 v1.15.  `Raw Archon` · 도입 여부 · `Use in MEF` 판정에는 변화가 없다.
> 구판 **v1.20** · 개정 2026-09-24 · **converter v2.5.0 재대조 + 현재형 서술 정정** (raw spec v1.14 동반) — LEECU 의 converter **v2.5.0** 이 raw 읽기 목록을 바꿨다: 새로 읽는 raw 키 **47장**(레거시 13 · 7장 32 · `CTRL1CFG`/`CTRL2CFG` 2), 더는 읽지 않는 둘(`ORIGIN` 은 MEF 상수화 · `UNIQNAME` 은 MEF 카드 폐지).  1장·9장에 **v2.5.0 기준 귀속**(읽는다 89 · `hval()` 5 · 읽지 않는다 11 · 폐지 18)을 v2.2.0 추출 기준 표 곁에 두고, 3.1절·3.3절·6장·7장·11장의 *"converter 가 읽지 않는다"* 류 문장을 사실대로 고쳤다 — raw geometry 선언은 **대조에만** 읽고(어긋나면 경고·HISTORY, 카드가 없으면 대조 없이 지나감), 카드 값으로 변환이 멈추는 곳은 **둘**(`OBSERVAT`↔파일명 — 기본 출력 이름 경로에서만 · pair 양쪽 `EXPID` 불일치)이다.  ⭐ 함께: 3.4절 `EQUINOX` 행을 **실수형 · 결측 `-999.0` · `TCS relay`** 로 · 3.2절과 8장 `UT` 행의 *"`TSHOPEN` 이 없으면 MEF `UT` 시각부가 빈다"* 를 사실로(구 조립식도 `TSHOPEN` 이 없으면 `DATE-OBS` 전체로 채웠다) · 3.4절 `RA`/`DEC` 기본 좌표 경고를 v2.5.0 사실로(기본 좌표를 걷고 WCS 를 통째로 뺀다, D-023) · 11.4절을 **같은 이름 표 · 이름만 갈린 표** 둘로 · 8장 *"대신 보는 것"* 열을 현행 후계로 · 레거시 귀속의 *"폐지 18"* 내역(8장 16 + 8.1절 2) · "규격" 정의를 현행 raw spec 으로(구판 v1.2 절 번호는 드러내 적는다) · `TELESCOP` `#0` · 13장 동명이의 넷 · 3.6절 출처 네 갈래 · 8.1절 comment 구 경고 본문 · 8.2절 RETIRED 시험 범위 · ICD **v4.3** · Keywords **v1.1** · converter **v2.5.0** 표기.  운영자 결정(2026-09-23) 셋도 옮겼다 — 4장 `DATE-OBS` 출처를 **적분 개시 시각**(모든 영상)으로 · 3.3절 `CTRLnID`/`CTRLnSN` 결측 **`'NC'`**(Archon `SYSTEM` 값으로 대신 채우지 않는다) · 7장 `CHECKSUM`/`DATASUM` **미도입 확정**(규격 OI-7 종결).  `Raw Archon`·도입 여부 판정에는 변화가 없고, `Use in MEF` 와 converter 독취 서술만 v2.5.0 을 따라간다.
> 구판 **v1.19** · 개정 2026-09-12 · **돔 방위 셋 Source 확정 + 완료형 정정** (raw spec v1.13 동반) — 3.6절에서 `DSAZ` · `DSTELAZ` · `DAZERR` 를 **`REDIS (dome control)`**(돔 제어 프로그램 redis, **D-021** · CR-003)로, 나머지 돔 카드 일곱 장을 **`TCS relay*`**(구 `TCS relay or REDIS*`)로 고쳤다.  `DAZERR` 는 `ICS calculation` → **중계값**이고 계산은 예비 경로다.  ⭐ 함께: 3.5절 FSA 형·포맷을 **소수 2자리 확정**으로(raw spec ~~OI-16~~ 종결) · 3.7절과 13장의 *"`ics_sim` 이 고칠 대상"* · 7장 `HTROUT` 의 *"읽는 코드가 아직 없다"* · 8.1절 comment 경고 · 8.2절 RETIRED · 3.6절 계승 6장 *"아직 안 쓴다"* 를 **완료형**으로 · 7장 `Cn_*` 행의 구분자(공백 → **파이프**)와 guide 모듈 표기(`HVYBias` → **`HVXBias`**, OI-19 종결) · `HKUDATE` 행에 **Radionode 제외** 규칙 · 카드 수 셈 `63` → **`68`** 세 곳 · ICD **v4.2** · converter **v2.4.0** 표기.  판정(`Use in MEF` · converter 독취)에는 변화가 없다 — **값 공급 계통과 사실 서술만 바뀐다.**
> 구판 **v1.18** · 개정 2026-09-06 · **출처 어휘 정정** (raw spec v1.12 동반) — Source 어휘에 **`ICG heater`** 를 등재하고(⚠️ v1.17 이 *"신설했다"* 고 적었는데 **실제로는 규격·원장 어느 쪽에도 안 들어가 있었다**) 폐지 계통 **`standalone RTD readout unit`** 을 걷었다.  3.7절 HK 계통 서술의 자기모순도 정리했다 — 한 문단이 앞 문장에서 옛 셋(`standalone RTD` 포함)을 세고 뒤 문장에서 새 셋(`ICG heater` 포함)을 세고 있었다.  판정 내용에는 변화가 없다.
> 구판 **v1.17** · 2026-09-04 · **HK 카드 5장 신설 반영** (raw spec v1.10 동반) — 7장 카드 표에 `HKUDATE`·`HTREN`·`HTRSET`·`HTROUT`·`HTRFORCE` **5행 추가**(카드 63→68장 · 표 55→60행), 3.7절 HK 공급 계통을 **둘 → 셋**으로(`ICG heater` 신설, 되읽기/실측 두 층).
> 구판 **v1.16** · 2026-08-30 · 환경 센서 장치명 `Tapaculo` → `Radionode` 개명 (raw spec v1.9 동반)
> **v1.14** · 2026-08-23 · 판정 준거를 본문에 편입(0장 신설) — 폐기 문서 의존 제거
>
> **v1.16 개정 (2026-08-30)** — **환경 센서 장치명을 `Tapaculo` 에서 `Radionode` 로 바꿨다** (운영자 지시 2026-08-30, raw spec v1.9 동반). 출처 어휘 `Tapaculo sensor` → **`Radionode sensor`**, 본문·changelog 표기 전량 교체 — 장치는 같고 이름만 바뀌었으므로 **판정 내용에는 변화가 없다.** 구판(`archive/`)의 `Tapaculo` 표기는 같은 장치다. Radionode 원값 포맷 확인 항목(OI-16)은 이름만 바뀐 채 그대로 열려 있다. ⚠️ guide raw FITS 장 신설(raw spec v1.9 의 9·10장)은 **이 원장의 범위 밖**이다 — 이 문서는 science pair 카드 판정 원장이다.
>
> **v1.15 개정 (2026-08-29)** — ① **`OI-9`(배선 실측) 폐기**: 실측이 끝나 raw spec 4.5절 amp 전수 표·`CHMAP_*` 와 MEF `AMPINFO` 가 통제한다(운영자 확정).  본문 세 곳(`CHMAP_*` 행 · `MODULE`/`CHANNEL` 항 · "배선" 항)의 `OI-9` 참조와 경고 문구를 **참조 안내로 바꿨다** — **세부 내용, 앰프별 배치 및 방향은 raw spec 4.5절(Amp 전수 표)을 참조한다.**  더 이상 열린 물음이 아니라 그 문서가 관리하는 값이다.  ② **`CTRLnCFG` 예시** — `'KMTA_SCI_101_R2609.1.acf'` 가 **확장자까지 달고** 있었는데, 헤더 값은 **폴더 경로와 확장자를 뗀 이름**이다(raw spec v1.8 5장).  실제 ACF 이름 규칙에 맞춘 값으로 옮겼다.
> **제자리 보강 (2026-08-25)** — 7장 `Cn_*` 행의 지시 "이 순서를 raw FITS spec 에 명세로 수록"이 이행됐다. 정본은 **raw spec 5.6.1절**(v1.5)이고, 이 행은 이제 그리로 가리킨다. 판정 내용에는 변화가 없다.
>
> **제자리 보강 (2026-08-26) — raw spec v1.6 반영.** ⑬ **`ORIGNAME` 폐지 · `EXPID` 신설** — 값이 `<SITE>.<YYYYMMDD>.<NNNNNN>` 으로 **`DETID` 필드가 없어 pair 양쪽에서 같다.** 5.9절 "반드시 상이" 가 **7장 → 6장**이 되고, 짝을 잇는 **단일 키**가 카드 추가 없이 생긴다(폐지된 `PAIRFILE` 의 역할). 충돌 판별은 `FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값과 비교하는 것으로 바뀐다. ⚠️ **converter 에서 `ORIGNAME` 을 읽던 자리는 `EXPID` 로 옮겨야 한다** (C-항목). ⑭ **`FILENAME` comment** `'Filename assigned by ICS'` → `'FITS file name as written to storage'` — 종전 문구가 `ORIGNAME` 과 똑같이 "ICS 가 배정" 계열이라 둘의 차이가 드러나지 않았다. ⑮ 견본 노출 번호 `012345`/`012340` → `123456`/`123450` 이고 **견본 파일 이름도 함께 옮겼다**.

> **제자리 보강 (2026-08-26) — raw spec v1.7 반영.** ⑭ 충돌 판별을 서술하는 낱말이 정해졌다 — 파일명 넷째 필드가 `<DETID>` 로 명명되면서(규격 2.2절) 이 문서의 "꼬리" 5곳을 **`DETID` 필드**로 옮겼다. "컨트롤러 태그가 없어"(`EXPID` 설명) 2곳도 같은 이유로 **"`DETID` 필드가 없어"** 로 옮겼다 — 필드에 이름이 생겼으므로 없는 것을 옛 관용어로 부를 이유가 없다. 판정 내용에는 변화가 없다.
>
> **v1.14 에서 바뀐 것 — 판정 근거가 문서 안으로 들어왔다.**
>
> 1. **0장 신설 — 준거 순위와 판정 구간.** 이 문서가 카드를 `O`/`X` 로 놓을 때 쓴 판정 기준이 그동안 별도 검토 문서(키워드맵 v0.7)에만 있었다. 그 문서는 흡수 완료로 삭제됐는데(운영자 재가 2026-08-22) **판정 기준까지 같이 사라져** 근거 없이 결론만 남은 상태였다. 순위표 · converter 3상태 × ICD 규정/침묵 교차표 · 준거 공백의 크기(210개 중 ICD 36 / 없는 것 174) · 추출 함정을 본문으로 들여왔다.
> 2. **키워드맵 v0.7 참조 전량 제거.** 6장·7장의 출처 서술을 자립 문장으로 바꿨다 — 판정 기준이 무엇이었는지가 이제 0장과 각 장 안에 있으므로 외부 문서를 가리킬 이유가 없다.
> 3. 흡수하지 않은 것과 그 근거: **MEF 표 HDU 컬럼 77장**(`AMPINFO` 40 · `TELEMETRY` 6 · `VOLTINFO` 5 · `XTALKINFO` 7 · 표 HDU 헤더 19)은 raw 에서 오는 값이 없어 **MEF 규격(ICD v4.2 §8 · Main_Keywords) 소관**이다. **MEF 인벤토리 236장 분석**은 converter 코드에서 기계 추출한 파생 수치이므로 규모만 0.3 에 남겼다. 구 `C-15`(`TELSTAT` 을 raw `CTRLSTAT` 에서 파생)는 **전제가 소멸**했다 — `CTRLSTAT` 이 v1.9 에서 `X` 확정이라 raw 가 싣지 않는다.

> **v1.13 에서 바뀐 것 — 잔여 확인 요망(6 · 7 · 8 · 10 · 11)이 전량 종결됐고, 충돌·정체성 결정이 D-016 으로 등재됐다** (운영자 확정 2026-08-22).
>
> 1. **재가 3건 종결(확인 요망 6 · 7 · 8)** — ⑥ `CTRL1ID` = `'KMTA-SCI-101'` 포맷 확정 + **Source 가 `ICS INI` 인 카드 전부를 ini 에서 수정 가능하게(운영자 지시, `ics_sim` 구현 반영)** · ⑦ `OVERSCNX`/`OVERSCNY` 의 "– 철회" = **구 이름 계승의 철회(폐지 확정 재확인)** — 8장·8.1 라벨을 대상이 드러나는 문구로 교체 · ⑧ `TIMVER`/`BIASVER`/`CLKVER` 는 `CTRLxCFG` 귀속(+ **`CAMVER` = HW·성능 세대 참조점** 명시), `XTALKVER`/`REFVER`/`CATVER` 는 caldb 소관 유지 — **pipeline setup 에서 HW 변화 없이 바뀔 수 있는 값이라 raw 미기재가 맞다**(운영자).
> 2. **확인 요망 10 종결 — PRESCN 은 키워드 변경 계승 (운영자 확정 2026-08-22)** — 레거시 `PRESCANX` 를 **`PRESCNX`/`PRESCNY` 로 개칭해 계승**한다(값 `0` — 신규 구조에 prescan 없음). `OVRSCNX`/`OVRSCNY` 를 정하고 나서 **자리수를 맞춰** 바꾼 것 — "그대로 계승"이 아니다. 6장 표기를 개칭 계승(DSTEL→DSTELALT 선례)으로, 7장 `PRESCNX` 를 `X`→`O` 로 정정 — 초안 v1.0·Detector 블록 정본과 3자 정합 회복.
> 3. **확인 요망 11 종결 — 규격 버전 카드는 미도입 (운영자 확정 2026-08-22)** — `RAWVER`/`RAWPROD` 부활 없이, 규격/구성 버전은 **`CAMVER`(HW) · `CTRLxCFG`(FW/설정) · `DETID` · `CHMAP_*`** 조합으로 전부 파악된다. 포장 규범 조항(V1)의 고정 대상도 `RAWVER` → **`CAMVER` + `CTRLxCFG`** 로 교체(7장 `ROWORDR` 행) — MEF 쪽 `GEOMVER` 동반 범프 문구도 같은 기준으로 갱신(통합 문서 §3).
> 4. **D-016 등재 (운영자 승인 2026-08-22)** — 충돌 처리(번호 증가·선검사·상한 100000회)와 정체성(`FILENAME` 유일 키 + `ORIGNAME` 충돌 신호, `UNIQNAME`·`NAMECLSH`·`clash/` 폐지)이 `DECISION_LOG.md` 에 **D-016 (Accepted)** 으로 등재됐다. D-010·D-012 의 "아카이브 근거 삼총사" 문구에 개정 표시, README 의 "색인 키는 UNIQNAME" 구 문단 교체. **이로써 V1 재작성 착수 조건(확인 요망 전량 + D-등재)이 완성됐다.**
> 5. **NT 초안 헤더 v1.0 파생 생성** — `KMTA.20260821.012345.NT.fits.header.v1.0.txt`: pair 상이 7장(`DETID` · `CHMAP_*` 4장 · `FILENAME`/`ORIGNAME` — `__reference` 정본 기준)만 다르고 나머지 136카드는 MK 동일(미확인분은 MK 값 유지).

> **v1.12 에서 바뀐 것 — HK 온도 카드의 형이 문자열로 확정됐다 (확인 요망 9 종결, 운영자 확정 2026-08-22).**
>
> 1. **온도·습도 카드는 레거시처럼 문자열 계승** — 레거시 실측이 이미 부호 포함 고정 포맷 문자열이었고(`CCDTEMP = '-103.16 '` · `AIR_IN = '+34.98  '`), converter 는 pass-through(`v("CCDTEMP","")`)라 raw 가 문자열이면 MEF 도 레거시 MEF 와 동일 형이다. 신규만 실수형이면 **아카이브에 같은 이름·다른 형이 섞여** 하류 파서가 두 갈래가 된다 — 초안 쪽이 맞았고, 고칠 대상은 `ics_sim`(실수형 → 문자열)이었다 — ✅ **그 전환은 완료됐다**(`rawhdr.format_temp()`, 3.7절).
> 2. **측정불가 sentinel — 온도·습도 전 카드 `'-999.99'` 단일값 통일 (운영자 확정 2026-08-22)**. 온도로는 어떤 냉각 램프도 닿지 않는 값이고 습도로는 음수라 물리 불가 — `'N/A'` 같은 글자 대신 수 모양의 불가능값을 쓰는 것은 `DEWPRES` `9.99e-9` 와 같은 설계 논리다(파싱 경로 단일화, 비교 대상이 정확히 한 문자열). 검토 중 기각된 안 둘의 사유를 남긴다 — `-99.99` 는 **CCDTEMP 냉각/워밍업 램프가 실제로 지나가는 값**(정상 운영값 -101~-103 바로 위)이라 실측과 구별 불가, 습도 `0.00` 은 **0% RH 가 유효 측정값**이라 "측정불가"와 "정말 건조함"이 섞인다. `DEWPRES` 는 기존 확정(`9.99e-9`) 그대로다. 규격 5.0 sentinel 표에 등재할 것.
> 3. **FSA 2장 포맷 = ENS식 잠정 채택** — 부호 생략(음수면 자연히 `-`)·소수 1자리, 레거시 `ENS1 = '23.0'` 선례와 일치. 단 **Radionode 원값 포맷이 워크스페이스에 근거가 없어** 실기/장치 문서 확인 항목으로 남긴다 — 확인되면 "원값 그대로 싣기"로 최종 확정(게이지 원문을 존중한 `DEWPRES` 와 같은 정신).
> 4. **초안 헤더 v1.0 승격 · `__review/` 폐지 (운영자, 2026-08-22)** — 검토 왕복이 사실상 끝나, 확정 초안이 **`KMTA.20260821.012345.MK.fits.header.v1.0.txt`** 로 이 폴더 루트에 승격됐다(내용은 v0.3.7 커밋본과 동일 — 143카드 diff 0). docx 왕복본과 초안 이력(v0.0~v0.4.4)은 운영자 외부 백업에 있다. 이 문서의 과거 changelog 가 가리키는 `__review/` 경로들은 **이력 기록**이다.

> **v1.11 에서 바뀐 것 — 돔 출처가 TCS 로 넘어갔고, 확인 요망 다섯이 닫혔다.**
>
> 1. **3.6 돔 Source 전면 변경 (운영자 5차 개정)** — 계승 6장(`DSSTAT`~`DSALT`)과 `DSAZ` · `DSTELALT` · `DSTELAZ` 의 출처가 `AUX relay` → **`TCS relay or REDIS*`**, `DALTERR` · `DAZERR` 는 중계값이 아니라 **`ICS calculation`** 이다. 근거: 돔 azimuth 는 원래 TCS 관장이고, **newTCS 전환으로 dome shutter control 이 TCS 에 편입**되어 돔 정보 전체를 AUX 가 아닌 TCS 에서 가져온다. 초안 헤더의 DS 카드 블록도 TCS Information and Status 절로 이동했다.
> 2. **확인 요망 1~3 종결 (초안 2026-08-22 최신판 — 이 문서에서 v0.3.7)** — chiller 4장 재삭제 · `FSATEMP`/`FSAHUM` 반영 · 돔 4장(`DSAZ` `DSTELAZ` `DALTERR` `DAZERR`) 반영을 **값 카드 135장 전수 대사**로 검증했다 (4×2880 정합 · 위반 0 · 중복 0).
> 3. **확인 요망 4 종결 — `EXPTIME` · `LEDFLASH` 정수형 (운영자 확정 2026-08-22)** — `EXPTIME` 은 **정수형 기본, 소수점 아래 값이 있을 때만 실수형**. `LEDFLASH` 는 **단위를 [seconds] → [milliseconds] 로 변경**해 정수형을 유지한다 — D-013 계승 조건("초 유지")의 번복이자 레거시와 같은 이름·1000배 다른 단위가 되므로 **카드 comment 가 단위를 명시**한다 (이 카드는 실험실 flat 식별용이라 계산 소비자가 없다 — converter 미독, 6장).
> 4. **확인 요망 5 종결 — `ICSBUILD` 형식에서 프로그램명 제거 (운영자 확정 2026-08-22)** — `v<버전>:<빌드일시(UTC)Z>` 채택 (예 `'v1.2.3:2026-08-21T18:09Z'`). 작성 프로그램 식별은 `DATASRC` 가 담당한다. `ics_sim` 반영 완료 — `build_id()` 개정 + `PROGRAM` 상수 삭제 + 테스트 교체, 전체 325 통과.
> 5. 잔여 확인 요망 6건 — **결정 대기 9(HK 온도 형) · 10(PRESCN 삼자 모순) · 11(규격 버전 선언 공백)**, 재가 대기 6 · 7 · 8.

> **v1.10 에서 바뀐 것 — 도입 판정의 마지막 미정이 사라졌다.**
>
> 1. **`CHKIMG` · `CHKIMG_C` → `X`** — "Pipeline 에서 판별하는 대상"(운영자). 영상 점검은 취득 시점에 존재할 수 없는 값이라 raw 카드가 아니다. **이로써 3장·6장·7장의 도입/계획 판정에 빈칸이 하나도 없다** — 검토 항목 9(도입 판정 미정) 전량 종결.
> 2. **6장 `DSTEL` → `O` (`DSTELALT` 로 변경하여 적용)** — 6장의 마지막 빈칸 소멸. D-013 개칭 판정의 계획 열 반영.
> 3. **8장 `OVERSCNY` 경고문에 후속 지시 추가** — `OVRSCNY` 개명으로 잘림 방지를 명기하고, raw FITS spec(V1)·MEF ICD·converter 검토 문서(MEF Impacts)에 수록하도록 했다. ※ 운영자 원문의 "OVRSCANY" 표기는 확정 카드명 `OVRSCNY` 의 오탈자로 보고 교정 반영 — 확인 요망. · v1.6 까지는 원천에서 기계 추출했다 — **v1.7 부터는 검토 확정분을 손으로 반영한 개정판이다** (생성기 부재 상태의 수기 개정 — 생성기를 재작성할 때 이 판의 손질을 승계해야 한다).

> **v1.9 에서 바뀐 것 — 운영자 3차 개정(`__review/…_v1.8_revision.docx`)과 확정 초안 v0.3.6(2026-08-22 판)을 반영했다.** 골자는 **7장 도입 여부 전면 판정 완결**이다.
>
> 1. **7장의 빈칸 26행을 전부 `O`/`X` 로 판정했다** — 이제 3.7 의 `CHKIMG` · `CHKIMG_C` 2장만 **문서 전체의 마지막 미정**으로 남는다.
> 2. **`READMODE` → `RDMODE` 개명 도입**(`O`, 값 예 `'NORMAL'` — 초안 v0.3.6) — raw `RDMODE`(독출 모드) / MEF `READMODE`(`'64AMP'`, converter 상수)로 **이름을 분리해 값 충돌을 종결**했다.
> 3. **`BCKTEMP` → `Cn_TEMP` `Cn_VOLT` `Cn_CURR` 확장 도입**(Sci n=1,2 · Gui n=1 — 구분 나열, 자리=항목.  ⚠️ 이 줄이 적었던 *"공백 구분"* 은 오기다 — 구분자는 **파이프(`\|`)** 이고 raw spec 5.6.1절이 정본이다, 운영자 확정 2026-08-26) + **`CAMVER` 신설**(`'CEU-v2.1'`, ICS INI).
> 4. **`X` 확정** — `CTRLTAG`(`DETID` 와 값 중복) · `PAIRFILE`(규약으로 예측 가능) · `OSCNPATT`/`RDDIRT`/`RDDIRB`(헤더 생략 — 세부는 raw FITS spec 수록) · `MIDOSCB`/`MIDOSCT`(`OVRSCNY` 로 충분) · `CHECKSUM`/`DATASUM`/`BUFNO`/`CTRLERR`/`CTRLSTAT`/`EXECODE`/`FRAMENO`/`TCSLIMIT`/`TELID` · 전압 6계열(`VMEA<n>` 등 — `Cn_VOLT`/`Cn_CURR` 나열형으로 대체) · `RAWPROD`/`RAWVER` · `CHIP1`/`CHIP2`/`CHIPS` · `PRESCNX`.
> 5. **3.5 `FSADEW` · `FSAALRM` `X` 전환**(계산·감지 파생은 raw FITS header 범주 밖 — 운영자 판정) · **4장 `DATE-OBS` `O` · `TCSDRIV` `X`** · **6장 `PRESCANX` · `PIXSCALE` · `PIXSIZE` `O`**.
> 6. **초안 v0.3.6 반영** — `CAMVER` · `RDMODE` · `C1_`/`C2_` `TEMP`·`VOLT`·`CURR` 8장 추가, 돔 블록(`DSSTAT`~`DSTELALT`)이 AUX 절에서 TCS 절로 이동.
>
> ⚠️ 새로 드러난 것 셋 — **PRESCN 삼자 모순**(6장 `PRESCANX` `O` vs 7장 `PRESCNX` `X` vs 초안은 `PRESCNX` 카드를 실음 — 신규 확인 요망 10) · **chiller 4장 초안 재잔존**(확인 요망 1 재개) · **`RAWVER` 부재로 raw 가 규격 버전을 자기 선언할 수단이 없어짐**(신규 확인 요망 11).

> **v1.8 에서 바뀐 것 — 운영자 2차 개정(`__review/…_v1.7_revision.docx`)과 확정 초안 v0.3.5 를 반영했다.** 골자는 셋이다: 3장 `Raw Archon` 열 전면 판정 · 컨트롤러 블록 재편 · HK(열·듀어) 블록 재구성.
>
> 1. **3.2~3.7 의 `Raw Archon` 열을 판정했다 — `CHKIMG` · `CHKIMG_C` 2장(3.7)만 미정 빈칸으로 남는다** (v1.7 까지는 3.1 만 채워져 있었다). `X` 판정 = `DARKTIME`(`EXPTIME` 에서 파생 — 카드 불요) · `TSHOPEN` · `TSHSHUT` · `CHSTAT`. ⚠️ **`TSHOPEN` 폐지는 MEF `UT` 조립 원천을 끊는다** — C-항목으로 등재했다(3.2절, MEF Impacts v0.3).
> 2. **3.3 컨트롤러 표 재편** — `CTRL1CFG`/`CTRL2CFG` 신설(`O`, ICS INI, 예 `KMTA_SCI_101_STA0288_R2608_MK` — **경로·확장자를 뗀 이름**), `CTRLxID`/`CTRLxSN` 도입 확정 + 실값(`KMTA-SCI-101`/`-102` · `STA-0288`/`-0289`), 펌웨어·버전 문자열(`CTRLxFW` `TIMVER` `BIASVER` `CLKVER`)은 **`CTRLxCFG` 로 귀속** `X`. 컨트롤러 2대분을 양쪽 raw 에 모두 싣고, guide FITS 는 `CTRL1xx` 한 벌, `CTRLnxx` 확장 규약(각주).
> 3. **HK 블록 재구성 확정** — `CCDTEMP` 는 평균 파생을 폐기하고 **실측 대표 센서 1개**("CCD temperature M", `ICG RTD measurement`), `CCDTEMP1`/`CCDTEMP2` 후보 제외(`X`), `DEWPRES` 는 문자열 `x.xxe-x` [torr] + 측정불가 sentinel **`9.99e-9`**, 신설 `DMPTEMP` · `WALLBRD` · `HEBOX`(7장 `O`). 출처 어휘 세 갈래 신설 — `ICG RTD measurement` · `standalone RTD readout unit` · `Radionode sensor`(2장).
> 4. **6장 판정** — `NPHLINES` · `HEMODE` `X`(`HEMODE` 는 `DATASRC`·`CTRLxID` 와 중복이라 삭제), `DATASRC` `O` + 값 체계 확장(`ARCHON_SCIENCE` / `ARCHON_GUIDE` / `SIM`), `LEDFLASH` · `FILENAME` · `ICSBUILD` `O`, `ENS1`~`ENS7` `O`(AUX 중계값 그대로 수록).
> 5. **`TCSTIME` 신설**(7장 `O`) — 시각계 선언을 `TIMESYS`(ICS)와 `TCSTIME`(TCS)으로 분리(초안 v0.3.5). `TCSLINK` 값 어휘 `Up`/`Idle`/`Down` · `AUXLINK` `Up`/`Down` 명시.

> ✅ **확인 요망 (운영자, v1.12~v1.13 갱신) — 열한 곳 전량 종결.** 아래 목록은 각 항목의 결정과 근거의 기록이다.
>
> 1. ~~`CHSTAT` 는 개정본이 `X` 인데 초안에 카드가 남아 있다~~ → 해소 (2026-08-21) → 재개 (v1.9): 초안 v0.3.6 재잔존 → **종결 (v1.11)**: 운영자가 초안에서 chiller 4장(`CHSTAT` `CHOP` `CHSET` `CHPROC`)을 재삭제, 검증 완료.
> 2. ~~`FSATEMP` · `FSAHUM` 2장이 `O` 인데 초안에 카드가 없다~~ → **종결 (v1.11)**: 운영자가 초안에 2장 반영, 검증 완료. (`FSADEW` · `FSAALRM` 은 v1.9 에서 `X` 확정 — 3.5절.)
> 3. ~~돔 신설 4장(`DSAZ` `DSTELAZ` `DALTERR` `DAZERR`)이 `O` 인데 초안에 없다~~ → **종결 (v1.11)**: 운영자가 초안 TCS 절에 4장 반영(오류 카드명 `DSALTERR`/`DSAZERR` 는 converter 독취명 `DALTERR`/`DAZERR` 로 교정), 검증 완료. `DSTELAZ` 의 "TCS `AZ` 와 중복 재검토" 단서는 유지(3.6절).
> 4. ~~`EXPTIME` 값이 개정본은 `Integer`, 초안은 `0.0` 이다 — `LEDFLASH` 도 같다~~ → **종결 (v1.11, 운영자 확정)**: 둘 다 **정수형**. `EXPTIME` 은 소수점 아래 값이 있을 때만 실수형으로 기록. `LEDFLASH` 는 단위를 **[milliseconds]** 로 변경해 정수형 유지 (6장 — D-013 계승 조건 번복 기록).
> 5. ~~`ICSBUILD` 형식 — 개정본은 `<프로그램>-v<버전>:<빌드일시>`, 초안은 프로그램명이 없다~~ → **종결 (v1.11, 운영자 확정)**: 초안 쪽 채택 — **`v<버전>:<빌드일시(UTC)Z>`**. 작성 프로그램 식별은 `DATASRC` 담당. `ics_sim` 코드·테스트 반영 완료.
> 6. ~~`CTRL1ID` 값 — 개정본 `'KMTA-SCI-01'` vs 초안·`__reference/Archon_Unit_Info.txt` `'KMTA-SCI-101'`~~ → **종결 (v1.13, 운영자 재가)**: `'KMTA-SCI-101'` 포맷 확정(ID 숫자 = IP). 함께 지시: **Source 가 `ICS INI` 인 카드는 전부 `ics_sim`/`ics_archon` 의 ini 파일에서 수정 가능해야 한다** — 구현 반영.
> 7. ~~8장·8.1절의 `OVERSCNY`/`OVERSCNX` 에 붙은 `– 철회` 낱말의 방향~~ → **종결 (v1.13, 운영자 재가)**: "구 이름 계승을 철회(폐지 확정 재확인)"가 맞다 — 라벨을 대상이 드러나는 문구로 교체했다. `DETID` 쪽 "철회"는 반대 방향(폐지의 철회 = 부활)이므로 표기를 "철회, 3.1 로 계승"으로 유지.
> 8. ~~`XTALKVER` · `REFVER` · `CATVER` 의 값 칸에 개정본이 `CTRLxCFG 로 귀속됨` 을 적었다~~ → **종결 (v1.13, 운영자 재가)**: 귀속 표기는 `TIMVER`/`BIASVER`/`CLKVER` 에만(세 값의 정본 = ACF 설정 파일 = `CTRLxCFG`), 이 셋은 **calibration DB 소관 유지**(C-14 — 정본이 ACF 가 아니다). 함께 명시: **`CAMVER` 는 HW·성능상 변경 시에만 올리는 전자부 세대 참조점**이다(3.3 주석·7장).
> 9. ~~HK 온도 카드의 형 — 초안은 문자열(`'-101.23'`, 부호 포함)인데 `ics_sim` 은 실수형으로 싣는 중이다~~ → **종결 (v1.12, 운영자 확정)**: **문자열 계승** — 레거시 실측도 부호 포함 문자열(`'-103.16 '`)이었고 converter 는 pass-through 라 아카이브 전체의 형이 통일된다. 측정불가 sentinel 은 온도·습도 전 카드 **`'-999.99'`** 단일값. 고칠 대상은 `ics_sim`(실수형 → 문자열) — ✅ **완료**(`rawhdr.format_temp()`).
> 10. ~~**PRESCN 삼자 모순 (v1.9 신규)** — 6장 `PRESCANX` `O` vs 7장 `PRESCNX` `X` vs 초안은 `PRESCNX` 를 실음~~ → **종결 (v1.13, 운영자 확정)**: **`PRESCNX`/`PRESCNY` 로 키워드 변경하여 계승, 값 `0`** — `OVRSCNX`/`OVRSCNY` 를 정하고 나서 자리수를 맞춰 개칭한 것이다. 6장은 "그대로 계승(O)"이 아니라 **개칭 계승** 표기로(DSTEL→DSTELALT 선례), 7장 `PRESCNX` 는 `X`→`O` 정정. 초안 v1.0·Detector 블록 정본과 정합.
> 11. ~~**규격 버전 자기 선언 공백 (v1.9 신규)** — `RAWVER` · `RAWPROD` 가 `X` 로 확정되면서 raw 가 자기 규격 버전을 선언할 카드가 없어졌다~~ → **종결 (v1.13, 운영자 확정): 미도입 유지.** 규격/구성 버전은 별도 카드 없이 **`CAMVER`(HW 부분) · `CTRLxCFG`(FW/설정 부분) · `DETID` · `CHMAP_*`** 조합으로 전부 파악된다. 귀결: 포장 규범 조항(V1)의 고정 대상은 `RAWVER` 대신 **`CAMVER` + `CTRLxCFG`** — geometry/포장 변경은 HW·설정 변경에서만 오므로 그 둘의 범프가 곧 판별 신호다.

> **v1.7 에서 바뀐 것 — 3장 표를 6열 신형식으로 바꾸고, 검토 확정분을 반영했다.** 근거는 `__review/…_v1.6_revision.docx`(운영자 개정, 3.1 표가 신형식의 견본)와 `__review/KMTA.20260818.012345.MK.fits.header.txt`(확정 초안), 2026-08-20~21 검토 세션이다.
>
> 1. **3장 표: `MEF 목적지` → `Use in MEF`**, `없을 때` 열 폐지 — converter 기본값은 각 표 아래 주석으로 흡수. **`Value (* default)` · `Source (* default)` 열 신설** — 값·통제 어휘와 그 출처를 적고, `*` 는 기본값/기본 출처다. 3.1 은 운영자가 채웠고 3.2~3.7 은 이번 개정에서 채웠다(빈칸 = 아직 정하지 않음).
> 2. **4장 표 동형식** — `쓰임새` → **`MEF Usage`**.
> 3. **초안 확정 반영**: Detector/Amplifier 블록(`AMPNAX1/2` · `IMAGEX/Y` · `PRESCNX/Y` · `OVRSCNX/Y` · `CHMAP_LT/LB/RT/RB` · `DETID` 재정의) · `FILENAME`/`ORIGNAME` 도입과 **`UNIQNAME` 폐지**(8.2절 신설) · `FPAID` 신설 · `INSTRUME` 값 형식(`'<SITE> 18k CCD'`).
> 4. **`OBSERVAT` · `ORIGIN` 확정** (운영자 확정 2026-08-21) — `OBSERVAT` 는 사이트 코드 재정의안을 철회하고 **현행 체계 그대로** `TESTBED`/`CTIO`/`SAAO`/`SSO` 다: converter 교차검증·ICD 2.1·`rawpair.py` 와 완전 정합, 개정 항목 없음. `ORIGIN` 은 레거시 계승 — **"이 파일이 생성된 곳"**: 관측소 raw 는 관측소 이름(OBSERVAT 와 중복 감수), 테스트베드 raw 는 `KASI`, KASI 서버 파이프라인 산출물(MEF·L1)은 `KASI`. 이 개념에 따라 **MEF `ORIGIN` 은 raw 복사가 아니라 상수 `'KASI'` 가 맞다** — 경미한 C-항목으로 등재(MEF Impacts v0.2).
> 5. 7장 `도입 여부` 판정 반영 + 확정 신규 카드 14장 추가(37→51장), **8.1 의 `OVSCN` 미정 해소**(`OVRSCNX`/`OVRSCNY` 두 장 + `PRESCANX`→`PRESCNX` 개칭), 12장 카드 이름 갱신.

> **v1.6 에서 바뀐 것 — `OVERSCNX` 를 폐지하고, 7장에 `도입 여부` 열을 넣었다.** `OVERSCNX` 는 `NAMPS` 와 같은 부류다 — 레거시 `32` 와 converter 상수 `48` 이 **같은 이름으로 다른 값**을 말하고, `X` 만 있어 **중앙 Y overscan 을 담을 자리가 없다.** 후속 이름은 **`OVSCN`** 계열로 정했고, X/Y 를 한 장으로 둘지 두 장으로 가를지는 아직 미정이다(8.1절).
>
> `도입 여부` 열은 7장 후보 37장을 하나씩 **도입/보류**로 판정하는 자리다. 지금은 `NAMPRAW` 하나가 `O` 다.

> **v1.5 에서 바뀐 것 — 11장(converter 가 만들어 쓰는 카드)과 12장(raw 를 직접 쓰는 사람을 위한 안내)을 나눠 넣었다.** 지금까지 이 문서는 *converter 가 raw 에서 무엇을 읽나* 만 다뤘다. 그런데 **converter 가 raw 를 읽지 않고 자기 상수로 만들어 내보내는 카드가 그보다 많고**, raw FITS 를 converter 없이 직접 쓰는 사람에게는 **그 카드들이 아예 없다.** 두 사정을 장으로 갈랐다 — 11장은 MEF 쪽 사실, 12장은 raw 쪽 사용자를 위한 것이다.

> **v1.4 에서 바뀐 것 — amplifier 수 카드를 `NAMPDET`/`NAMPRAW` 로 통일하고 `NAMPS`·`AMPPCD` 를 폐지했다.** 세 카드가 서로 다른 범위를 세면서 이름이 그것을 드러내지 않았다 — `NAMPS` 는 레거시 `8`(CCD 하나)에서 신규 `64`(카메라 전체)로 **범위가 바뀌었는데 이름이 그대로**였고, `AMPPCD` 는 값 `16` 이 `NAMPDET` 과 같은 것을 세면서 이름만 달랐다. 8.1절이 판정과 근거다.
>
> **ICD v4.2 에 `NAMPS` · `AMPPCD` 가 하나도 없다** — 0.3절이 말한 **침묵 구간**이라 우리가 정할 수 있고, converter 는 raw 를 읽지 않고 자기 상수를 쓰므로 **raw 에서 빼도 MEF 출력은 바뀌지 않는다.**

> **v1.3 에서 바뀐 것 — `Raw Archon` 열이 생겼고, subframe 절(10장)이 붙었다.** 지금까지 표는 *레거시가 그 카드를 실었나* 만 말했다. 신규 Archon raw 가 **그 카드를 실을 계획인가** 는 별개 사실인데 적을 자리가 없었다. `Raw Archon` 열이 그 자리다 — **기계 추출이 아니라 운영자가 채우는 계획 열**이고, 재생성해도 유지되도록 생성기 안에 표로 들고 있다.
>
> 함께 반영한 손질: **`DETID` 를 3.1 로 되살렸다**(값을 `MK`/`NT` 로 재정의, MEF 목적지는 `((TBD))`) · `ORIGIN` 의 기본값을 사이트별로 폈다 · 7장 `ACFFILE` 에 `CTR_CFG` 를 병기하고 `READMODE` 를 넣었다 · `CHIP1`/`CHIP2`/`CHIPS` 에 **`DETID` 로 변경** 을 달았다.

> **v1.2 에서 바뀐 것 — raw 카드의 기준을 레거시 실측 헤더로 명확히 했다.** v1.1 은 6장을 검토 문서 v0.7 의 4.H 절 그대로 실어 **레거시가 이미 싣던 카드와 아직 제안 단계인 신규 카드가 한 표에 섞여 있었다.** 지위가 다른 둘을 같은 표에 두면 *"이 카드는 확정된 것인가"* 를 표에서 읽어낼 수 없다.
>
> v1.2 는 그 53장을 **레거시 16 + 신규 37** 로 가르고, 앞엣것은 6장(레거시 24장)에 흡수하고 뒤엣것을 **7장 "Archon ICS 도입 후보"** 로 분리했다. 6장에는 **converter 가 왜 그 카드를 읽지 않는지**를 카드마다 적었다 — 자기 상수를 쓰는가, 다른 이름으로 나뉘었는가, 기록으로만 남기는가. 폐지 표는 7장에서 **8장**으로 밀렸다.

| 항목 | 값 |
| --- | --- |
| **raw 카드 기준** | `__reference/Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt` — **레거시 raw 실측 헤더 123개** |
| 대상 converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (**v2.5.0**) — ⚠️ **3~5장·6장·11장의 카드 대조는 v2.2.0 본으로 떴다.** v2.3.0(`--ampchar`, PRIMARY 자기 카드 `AMPCHAR` 신설 — 11.1)·v2.4.0(D-017 사이트 코드)은 raw 읽기 목록을 바꾸지 않았고, ⭐ **v2.5.0 은 바꿨다** — 새로 읽는 raw 키 47장 · 더는 읽지 않는 둘(`ORIGIN` · `UNIQNAME`).  장 배치는 v2.2.0 추출 그대로 두고 바뀐 행마다 **v2.5.0** 을 적었다(귀속 수는 1장 둘째 표) |
| **v1.22 개정 근거** | 운영자 결정 2026-09-24(`OBSTYPE` 사용자 입력 카드 · 빈 값 폴백 폐지 · `EXPTIME` 실수형 · 견본 comment 문안 정정 — raw spec v1.16 12장 v1.16 행) · converter v2.5.0 `primary_cards()` · `amp_header()` 의 `OBSTYPE` 중계(`v("OBSTYPE","")`) · `EXPTIME` 의 `fnum()` 실수 변환 · `read_primary_header()` 의 raw comment 미독 재확인 |
| **v1.21 개정 근거** | raw spec v1.14 발행본 재검토(2026-09-24)에서 반증을 통과한 발견 가운데 원장 몫(7장 `RDMODE` 결측 · 3.7절 `CCDTEMP` 평균 파생 문구 · 8.2절 `EXPID` 이름 재사용 경고) · 운영자 결정 2026-09-24(`RDMODE` 결측 `'NC'` — v1.20 에 옮겨지지 않았다) · converter v2.5.0 `primary_cards()` 의 `RDMODE` 기본값 재확인 |
| **v1.20 개정 근거** | converter v2.5.0(커밋 `3e82467` 과 뒤이은 정정) 전문 대조 — v2.4.0(`f4c7e5e`) 대비 raw 읽기 목록 차분을 스크립트로 떴다 · raw spec v1.14 전반 재검토(2026-09-23)의 원장 몫 · 운영자 결정 2026-09-23(`DATE-OBS` 적분 개시 · `CTRLnID`/`CTRLnSN` 결측 `'NC'` · `CHECKSUM`/`DATASUM` 미도입 확정) |
| **v1.14 개정 근거** | 키워드맵 v0.7 삭제(운영자 재가 2026-08-22)에 따른 판정 근거 편입 — 원문은 git 이력에 있다(`4782c78^`) |
| **v1.13 개정 근거** | 운영자 확정 2026-08-22(확인 요망 6 · 7 · 8 재가, 10 PRESCN 키워드 변경 계승, 11 규격 버전 카드 미도입) · DECISION_LOG **D-016 등재** · `__reference/Archon_Unit_Info.txt`(CTRL 실값) · NT 초안 헤더 v1.0 파생 |
| **v1.12 개정 근거** | 운영자 확정 2026-08-22(확인 요망 9 — HK 온·습도 문자열 계승 · sentinel `'-999.99'` 단일값 · FSA ENS식 잠정) · 레거시 실측 헤더의 HK 문자열 포맷 재확인 |
| **v1.11 개정 근거** | `__review/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.10_revision.docx`(운영자 5차 개정 — 돔 Source 변경) · `__review/KMTA.20260818.012345.MK.fits.header.txt`(확정 초안 2026-08-22 최신판 — 이 문서에서 v0.3.7: chiller 재삭제 · FSA 2장 · 돔 4장 · `EXPTIME`/`LEDFLASH` 정수형 · `RDMODE` · `CAMVER` 반영) · 운영자 확정 2026-08-22(확인 요망 4 · 5) |
| **v1.9 개정 근거** | `__review/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.8_revision.docx`(운영자 3차 개정) · `__review/KMTA.20260818.012345.MK.fits.header.txt`(확정 초안 2026-08-22 판 — 이 문서에서 v0.3.6 으로 부른다) |
| **v1.8 개정 근거** | `__review/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.7_revision.docx`(운영자 2차 개정) · `__review/KMTA.20260818.012345.MK.fits.header.txt`(확정 초안 v0.3.5 — 직전판 v0.3.4 는 git 이력(44ab878)과 운영자 외부 백업에 보존) · `__reference/Archon_Unit_Info.txt`(CTRL 실값) |
| **v1.7 개정 근거** | `__review/KMT_CEU_Raw_FITS_Header_and_Refs_in_MEF_Converter_v1.6_revision.docx`(운영자 개정) · `__review/KMTA.20260818.012345.MK.fits.header.txt`(확정 초안) · `__reference/Detector_and_Amp_Info_cards_v1.0.txt`(구 AMPCARD.txt) |
| 3~5장 추출 | `card("<MEF>", v("<raw>", <기본값>), …)` 호출을 정규식으로 파싱 |
| 6장 | 레거시 123개에서 3~5장·8장을 뺀 나머지. 설명은 converter 소스 대조 |
| 7장 출처 | **레거시 실측 123개에 없는 카드** 중 규격·`ics_sim`·운영자 개정이 제안한 것 (0.1 의 raw 기준선 기준) |
| 8장 출처 | DECISION_LOG **D-013** (`Accepted (Amended)`) — 표 본문은 구판 규격 v1.2 5.13절([`archive/KMT_CEU_Raw_FITS_Specification_v1.2.md`](archive/KMT_CEU_Raw_FITS_Specification_v1.2.md))에서 옮겨 왔다 |

> **raw 카드의 기준은 레거시 raw 실측 헤더다.** 규격 v1.2 나 `ics_sim` 이 새로 들인 카드는 **레거시 기준선 밖의 제안에서 출발했으므로** 7장에 따로 모았다 — 도입 여부는 v1.9 에 완결됐지만(7장) 출신이 레거시 계승 카드와 다르다.

> **이 문서에서 "규격" 은 현행 raw spec — [`KMT_CEU_Raw_FITS_Specification_v1.16.md`](KMT_CEU_Raw_FITS_Specification_v1.16.md) — 을 가리킨다** (판이 오르면 README 의 현행 문서 표를 따른다).  구판 규격 v1.2(구명 `Pair_Spec`, 현 [`archive/KMT_CEU_Raw_FITS_Specification_v1.2.md`](archive/KMT_CEU_Raw_FITS_Specification_v1.2.md))의 절 번호로 적힌 포인터는 **"구판 v1.2 N절"** 로 드러내고 현행 절을 곁에 적는다.
>
> ⚠️ 절 번호는 판마다 바뀔 수 있다. 아래에서 `규격 5.10` 처럼 절을 적은 곳은 **지금 그 내용이 어디 있는지 알려주는 포인터일 뿐 근거가 아니다.** 확정된 근거는 `../project_management/governance/DECISION_LOG.md` 의 **D-번호**다 — 이 문서 본문이 인용하는 것은 D-003(chip 반전 안 씀) · D-011(사이트 코드 파일명) · D-012(백엔드 계약 — 아카이브 근거 문구) · **D-013**(레거시 keyword 판정) · D-014(관측일 — 이 문서는 `DATE-OBS` 밀리초 조항을 인용) · **D-016**(충돌 번호 증가 · 정체성, 2026-08-22 등재) · **D-017**(사이트 코드 넷) · **D-019**(`ORIGNAME` 폐지 · `EXPID` 신설) · **D-021**(돔 방위 셋 = 돔 제어 프로그램 redis) · **D-023**(L0 sky WCS 는 seed) 열이고 전부 Accepted 다(D-013 · D-014 · D-017 은 Amended — D-017 은 항목 3(→ D-020) · 4(`KMTK` 보정 `+9:00`) · 6 이 개정됐다). ⚠️ 이 폴더가 기대는 D-번호 **전량 목록의 정본은 규격 머리말 "결정 기록" 행**이다 — 같은 목록을 두 자리에 두면 갈라지므로 여기에는 이 문서 본문이 인용하는 것만 적는다.

## 0. 준거 순위와 판정 구간

**이 장은 "무엇을 근거로 판정했나" 를 정한다.** v1.14 신설 — 폐기된 검토 문서
(키워드맵 v0.7)에만 있던 판정 기준을 본문으로 들여왔다. 카드 하나를 `O`/`X` 로
놓을 때마다 되돌아오는 질문이라 문서 안에 있어야 한다.

### 0.1 무엇을 따르는가 — 순위

**대상은 `mef_converter/` 가 만드는 L0 MEF 다.** 그 헤더가 무엇을 담아야 하는지
정할 때 아래 순위를 따른다.

| 순위 | 무엇 | 지위 |
| --- | --- | --- |
| **1** | [`../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md`](../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.3.md) | **준거.** 어긋나면 아래가 틀린 것이다 |
| **2** | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.5.0) | **산출 주체.** 단 둘로 갈라 읽는다 — 0.2 |
| **3** | [`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md`](../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.1.md) | 참고. **PRIMARY keyword 층의 유일한 문서 근거**이지만 converter 파생물이다 |
| — | `KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` | **판정 근거로 쓰지 않는다** |
| — | `../ics_sim/` 의 현재 헤더 출력 | **판정 근거로 쓰지 않는다 — 근거가 순환한다** |
| **raw 기준선** | `__reference/Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt` — **레거시 raw 실측 123개** | **raw 쪽이 실제로 무엇을 싣는지의 기준선.** 계승 판정(D-013)의 근거이자 6장·9장의 출처 |

3위가 3위인 이유는 그 문서가 스스로 밝힌다 — 머리말이 *"기준 converter:
…v2_1.py v2.5.0"* 이다(v1.1, 2026-09-23 — v1.0 은 *"v2.2.0"* 이었다). **converter 를
따라 적은 파생물이므로 원본보다 위일 수 없다.**

> ⚠️ **3위·제외 문서를 근거로 쓰면 틀린다.** 둘 다 저장소에 있어서
> 겉보기로는 권위가 있으므로, 실측해 둔 상태를 남긴다(3위 문서는 구판 상태도 함께).
>
> | 문서 | 확인된 상태 |
> | --- | --- |
> | `Main_Keywords v1.1` (현행, 2026-09-23) | converter v2.5.0 과 함께 개정됐다(D-023 — seed WCS 상태 §4.7 · amp 채널 정체 · `AMPINFO` 52열 · `VOLTINFO` 37행 · `PIXSCALE` `0.395`). ⚠️ **그래도 converter 를 다 따라가지 못했다** — v2.5.0 이 PRIMARY 에 싣는 HK pass-through(`HKUDATE` · 히터 넷 · `DMPTEMP` `WALLBRD` `HEBOX` · `ENS1`–`ENS7` · `C1_`/`C2_` `TEMP`·`VOLT`·`CURR`)가 §4.8 에 없고, raw 가 v1.5 에 폐지한 `AIR_IN` `AIR_OUT` `GLYC_IN` `GLYC_OUT` 은 §4.8 에 남아 있다(converter 도 빈 값으로 싣는다). `EQUINOX` 행(§4.6)의 *"raw 는 문자열 `'2000.000'`"* 은 raw spec v1.14 부터 틀린 말이다. 정정 요청은 통합 문서 §4 |
> | (구) `Main_Keywords v1.0` (현 `archive/`) | ICD v4.1 개정 커밋에서 **8줄만 바뀌었다** — 머리말 기준 버전 2줄 + `MKFILE`/`NTFILE` 예시 파일명 2줄. 본문 대조 흔적이 없고 버전·작성일이 `v1.0`/`2026-06-22` 그대로라 **겉보기로는 미개정으로 읽힌다.** 본문에 `CREATOR`=`…_v2.1.1` · `PIPEVER`=`…-v2.1.1` 잔재가 남아 있다(당시 converter v2.4.0 의 실제 값은 **`v2.4.0`** — `CREATOR`·`PIPEVER` 가 소스의 `SOFTWARE_VERSION` 을 그대로 박는다. `PRODVER`=`v2.1.1` 은 그 판까지 코드가 의도적으로 고정한 값이라 맞았다 — v2.4.0 까지의 소스 주석 *"L0 MEF format unchanged by v2.1.2+ fixes"*.  v2.5.0 은 `CREATOR`·`PIPEVER` `v2.5.0` · `PRODVER` `v2.2.0` 이다 — Keywords v1.1 머리말과 같다) |
> | `Work_Summary v1.0` | **2026-06-22 이후 갱신되지 않았다.** 기준 ICD 가 `v4.0`, 파일명이 `KMTN.*`(D-011 이전), converter 가 `v2.1.1` 이다. 특히 **NT 헤더를 *"Header metadata may be minimal"* 이라 적고 있는데 이는 ICD v4.1 §2 가 OI-8 로 뒤집어 금지한 서술이다** |

### 0.2 순위 2위(converter)는 둘로 갈라 읽는다

converter 는 **준거이면서 동시에 수정 대상**이다. 한 낱말로 부르면 C-항목을
무엇이라 불러야 할지 정해지지 않는다.

| converter 의 무엇 | 지위 |
| --- | --- |
| **산출물 구조** — HDU 구성, 카드 이름, 표 컬럼 | **준거 2위** |
| **값을 채우는 동작** — 읽음 / 하드코딩 / placeholder | **미완 구현.** 준거가 아니다 |

그 "값을 채우는 동작" 은 세 가지다.

| 표기 | 뜻 | 함의 |
| --- | --- | --- |
| **읽음** | converter 가 raw 헤더에서 값을 꺼낸다 | **raw 가 정본.** 이름이 틀리면 L0 MEF 가 `UNKNOWN` 을 받는다 |
| **하드코딩** | converter 가 같은 값을 소스에 문자열로 갖고 있다 | raw 카드가 지금은 중복이다. 사이트별로 값이 갈리는 순간 필요해진다 |
| **placeholder** | converter 가 고정값으로 채운다 (raw 를 볼 통로가 없다) | raw 는 **아카이브 기록으로만** 남는다. 연결이 변경점 대상 |

여기에 **ICD 가 그 자리를 규정했는가**를 겹쳐 읽으면 무게가 정해진다.

| | ICD 가 규정한 자리 | ICD 가 침묵하는 자리 |
| --- | --- | --- |
| **placeholder** | **ICD 미준수다.** §12 가 *"placeholder 는 raw 헤더가 실측 텔레메트리를 주지 않을 때"* 로 한정하고 **필요한 raw 텔레메트리 집합은 우리 규격 5장이 정의한다**고 역참조한다 → **C-12 · C-17 · C-18 의 근거** (C-17 · C-18 은 converter v2.5.0 이 반영했다 — C-12 `READDIR` 은 코드가 그대로다) | 아카이브 기록으로만 남는다. MEF 목적지를 만들지 말지가 결정 사항 |
| **하드코딩** | 대조 대상이 있으므로 raw 선언과 맞추면 된다 | **근거가 순환한다** — 버전 문자열 계열이 이 칸이었고, 확인 요망 8 에서 `CTRLxCFG` 귀속 / caldb 소관으로 갈라 종결했다 |

### 0.3 ICD 가 침묵하는 구간이 판정의 과녁이다

**ICD 에는 PRIMARY keyword 목록이 대부분 없다.** 규정하는 것은 구조(§5) ·
amp section(§7) · `AMPINFO` 컬럼군(§8) · 표 역할(§9)이다 — v4.3 이 §7.1 에 PRIMARY
의 seed WCS 상태 카드(`WCSSKY` `WCSOMIT` `WCSSOLVE` 등, D-023)를 들였을 뿐 관측 ·
provenance · 환경 카드는 여전히 규정하지 않는다. 그래서 두 구간을 갈라 읽어야 한다.

| 구간 | 판정 방법 |
| --- | --- |
| **ICD 가 규정한 구간** | converter 는 구현체다. 어긋나면 **converter 가 틀린 것**이고 판정이 자동으로 나온다 |
| **ICD 가 침묵하는 구간** | converter 는 정본이 아니라 **"현재 구현"** 이다. **이 구간이 곧 결정해야 할 곳**이다 |

**구간의 크기를 세어 두었다** (converter v2.2.0 · ICD v4.2 기준 분석 — 원장 v1.14 가 센 수를
다시 세지 않았다). converter 가 `card()` 로 만드는 헤더 카드 이름은
**210개**(표 컬럼까지 포함하면 236개)이고, 그중 —

| ICD v4.2 에 | 개수 | 성격 |
| --- | ---: | --- |
| 등장한다 | **36** | **전량이 §7 amp section · §8 `AMPINFO` 컬럼 · geometry 계열**이다 — `DATASEC` `BIASSEC` `CCDSEC` `DETSEC` `AMPSEC` `TRIMSEC` `AMPID` `CHIPID` `STRIPID` `ENDID` `MODULE` `CHANNEL` `CTRLID` `READDIR` `CHIPFLP` `STRIPDIR` `GAIN` `RDNOISE` `LINMAX` `RAWFILE` `RAWDATA` `RAWBIAS` 등 |
| 없다 | **174** (83%) | **PRIMARY 의 관측 · provenance · 환경 keyword 전량** |

그러니 대립은 이름 충돌이 아니라 **준거의 공백**이다 — 3위 정의서(당시 v1.0)에 정의가 없는
카드 이름은 `COMMENT`·`END`·`TFIELDS` **3개**(전부 FITS 구조 카드)뿐이고 반대
방향(문서에만 있고 코드가 안 만드는 것)도 없었다. **그 시점에는 converter 가 문서 밖 이름을
발명한 사례가 없었다.**

> ⭐ **v2.5.0 에서 규모가 바뀌었다** — converter 가 만드는 카드 이름은 v2.4.0 211(v2.2.0 의 210 + `AMPCHAR`) → v2.5.0 286 이다(`card("NAME"` 호출과 `ENS`n · `C`n`_*` 루프로 셈, f-string 카드명은 뺐다). ICD v4.3 대조는 다시 뜨지 않았다. 위의 *"문서 밖 이름 없음"* 은 v2.5.0 에서 깨졌다 — 0.1 의 ⚠️ 표대로 HK pass-through 카드가 Keywords v1.1 에 없다.

### 0.4 카드를 어디서 뽑았나 — 그리고 놓쳤던 것

| 무엇 | 어디서 |
| --- | --- |
| **MEF 키워드** | converter **코드**. 검토 대상 L0 MEF 를 실제로 만드는 것이 이 코드다 — **"코드가 정본"이라는 뜻은 아니다**(0.1 · 0.2) |
| **raw 키워드** | 레거시 raw 실측 헤더 123개. **정착된 설계다** — 신규 raw 가 무엇을 계승하고 무엇을 새로 만드는지가 여기서 갈린다 |
| 참고 (근거 아님) | `ics_sim` 의 `rawhdr` · `rawpair` · `telemetry` 출력. **미완성 구현이다** |

> ⚠️ **추출 함정.** `card(...)` 호출은 **괄호 균형으로** 파싱해야 한다. 처음에
> 함수별로 잘라 파싱했다가 `extra_cards=[…]` 안의 5장(`GEOMVER` `TELSTAT`
> `NAMP` `NXTALK` `EXTTYPE`)을 놓쳤다 — 표 HDU 의 카드가 함수 밖에 있다.

> **용어**: **`L0 MEF`** 는 converter 가 만드는 산출물이고, **`레거시 MEF`** 는
> `xkmta.20170209.*` 실측 헤더다. 둘을 그냥 "MEF" 로 부르지 않는다 — 섞으면
> 버전 문자열 판정에서 실제로 오류가 났다.

## 1. 요약

**레거시 raw 실측 123개**가 어디로 갔는지 (장 배치 = converter **v2.2.0 추출** 기준):

| | 개수 | 어느 장 |
| --- | ---: | --- |
| converter 가 읽는다 | **78** | 3장 · 4장 |
| 구조 카드 — `hval()` 로 읽는다 | **5** | 5장 |
| **converter 가 읽지 않는다** | **22** | **6장** |
| 폐지됐다 | **18** | 8장 16(D-013 폐지 16 — `DETID` 포함) + 8.1절 2(`NAMPS` · `OVERSCNX`) |
| **합계** | **123** | |

> **폐지 18 의 셈** — 8장 표 17행 가운데 `UT` 는 레거시 밖의 규격 카드라 이 셈에 들지 않고, 8.1절 표 3행 가운데 `AMPPCD` 도 레거시 밖이다. ⚠️ `DETID` 는 폐지가 철회돼 3.1 로 계승됐지만(8장) converter v2.2.0 이 읽지 않아 **converter 축에서는** 여기 남는다 — Raw Archon 축과 섞지 말 것(9장).

⭐ **converter v2.5.0 기준으로 다시 세면** 이렇다 (v2.4.0 대비 raw 읽기 목록 차분을 스크립트로 떴다 — v2.3.0·v2.4.0 은 v2.2.0 과 목록이 같다):

| | 개수 | 무엇이 옮겼나 |
| --- | ---: | --- |
| converter 가 읽는다 | **89** | 78 − `ORIGIN`(MEF 상수 `'KASI'`) − `UNIQNAME`(MEF 카드 폐지) + 6장 12장(`PIXSCALE`·`PIXSIZE` 는 대조만 · `DATASRC`·`LEDFLASH`·`ICSBUILD`·`ENS1`–`ENS7` 은 MEF 로 옮긴다) + `DETID`(교차검증만) |
| 구조 카드 — `hval()` 로 읽는다 | **5** | 그대로 |
| converter 가 읽지 않는다 | **11** | 6장의 나머지 10(`SIMPLE` `NAXIS` `PRESCANX` `NPHLINES` `HEMODE` `FILENAME` `DSTEL` `CHOP` `CHSET` `CHPROC`) + `ORIGIN` |
| 폐지됐다 | **18** | 8장 15(`DETID` 가 빠진다) + 8.1절 2 + 8.2절 `UNIQNAME` |
| **합계** | **123** | |

여기에 **레거시에 없던 카드**가 두 갈래로 붙는다:

| | 개수 | 어느 장 |
| --- | ---: | --- |
| converter 가 읽는데 레거시에 없다 | **26** | 3장 (`X` 표시). ⭐ v2.5.0 은 여기에 `CTRL1CFG`/`CTRL2CFG`(3.3절)와 7장 32장을 더해 **60** 을 읽는다 |
| **Archon ICS 도입 후보·확정** — 규격 v1.2 / `ics_sim` / 확정 초안이 새로 들였고 converter v2.2.0 은 읽지 않았다(⭐ v2.5.0 은 그중 32장을 읽는다 — 7장 머리) | **68** (후보 39 + v1.7 신규 14 + v1.8 신설 4 + v1.9 확장·신설 6 + v1.17 HK 신설 5 — `Cn_*` 6장이 `BCKTEMP` 1장을 대체(+5), `CAMVER` +1, HK 는 `HKUDATE` 와 듀어 히터 넷). 구 원장 "37" 은 v1.3 `READMODE` · v1.4 `NAMPDET` 추가분을 재산정하지 않은 값이라 v1.8 에서 실측 재산정했다 | **7장** |

> **PRIMARY 카드는 전부 MK 헤더에서 읽는다** — v2.5.0 도 같다. pair 동일 규칙(규격 5.9절)이 그것을 허용하고, v2.5.0 은 그 규칙이 지켜졌는지 `EXPID` · `DATE-OBS` · `EXPTIME` · 포인팅 · 컨트롤러 정체 · `Cn_*` · `HKUDATE` · `CCDTEMP` 등 22장을 두 파일 사이에서 대조한다(어긋나면 경고·HISTORY — `EXPID` 만 멈춘다, 13장). ⭐ **amp 헤더는 v2.5.0 부터 그 chip 을 담은 파일의 헤더를 읽는다**(변경점 C-17 반영) — NT 헤더가 amp 에 반영되지 않던 것은 v2.4.0 까지다.

## 2. 표 보는 법

| 열 | 뜻 |
| --- | --- |
| **Raw Legacy** | `O` = 레거시 raw 실측본에 있다(계승) · **`X`** = 없다(신규 결정 대상) |
| **Raw Archon** | `O` = Archon raw 에 구현 예정 · **`X`** = 없다(폐지 또는 keyword 정의 변경) · 빈칸 = **아직 안 정했다** |
| **Use in MEF** | 그 값이 들어가는 MEF 카드. `+amp` 는 amp extension 에도 반복 기록된다는 표시. (구 `MEF 목적지`) |
| **Value (`*` default)** | 카드가 가질 값·통제 어휘. `*` 는 기본값 |
| **Source (`*` default)** | 값의 출처 — `ICS INI`(설정) · `ICS code`(취득 SW 산출) · `ICS generating`(취득 SW 생성) · `user input/selection` · `TCS relay` / `AUX relay`(TC 중계) · `REDIS`(돔 제어 프로그램의 redis — 돔 방위 전용, D-021) · `Archon`(컨트롤러) · `ICG RTD measurement`(Archon 쪽 RTD·게이지 실측, v1.8) · `ICG heater`(듀어 히터 제어·실측, v1.10) · `Radionode sensor`(환경 센서, v1.8) · `ICS calculation`/`ICS detection`(ICS 파생·감지, v1.8). `*` 는 기본 출처 |

> 구 `없을 때` 열(raw 에 카드가 없을 때 converter 가 대신 넣는 값 — **오류는 나지 않는다**)은 폐지하고 각 표 아래 주석으로 옮겼다. 기본값 경고(그럴듯한 값이 조용히 박히는 부류)는 각 절의 ⚠️ 문단이 계속 담는다.

표기: `ᴬ` = AUX/TCS 중계(pass-through) · `ᶠ` = FITS 표준 카드

> **`X` 가 전부 결함인 것은 아니다.** raw 가 실을 필요가 없다고 이미 정리된 것도 `X` 로 나온다 — 3.3절의 `XTALKVER` · `REFVER` · `CATVER` 가 그렇다. 각 표 아래 주석이 그 구분을 적어 둔다.

## 3.1 관측소 · 검출기 · 관측 식별

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `ORIGIN` | O | O | — (⭐ v2.5.0: MEF `ORIGIN` 은 converter 상수 `'KASI'` — raw 를 읽지 않는다) | `KASI`* / `SSO` / `CTIO` / `SAAO` | ICS INI |
| `BUNIT` | O | O | `BUNIT` `+amp` | `ADU` | ICS code |
| `DETID` | O | O | — (⭐ v2.5.0: **교차검증에만** 읽는다 — 파일명 접미사 `.MK`/`.NT` 와 대조 · pair 양쪽이 같으면 경고. MEF `DETID` 는 converter 상수 `'MKNT'`) | `MK` / `NT` | ICS code |
| `DETECTOR` | O | O | `DETECTOR` | `'e2v CCD290-99'` | ICS INI |
| `CCDXBIN` | O | O | `CCDXBIN` | `1` (2 & 3 reserved) | ICS code* / user selection |
| `CCDYBIN` | O | O | `CCDYBIN` | `1` (2 & 3 reserved) | ICS code* / user selection |
| `OBSERVAT` | O | O | `OBSERVAT` · `SITEID` | `CTIO` / `SSO` / `SAAO` / `KASI` (**D-017** — 구 `TESTBED` 대체) | ICS INI |
| `TELESCOP` | O | O | `TELESCOP` | `'KMTNet 1.6m #0/#1/#2/#3'` (사이트별 — 규격 5.3.1절 표. `#0` = KASI, 구 `Sim` 대체) | ICS INI |
| `LATITUDE` | O | O | `LATITUDE` | `'+dd:mm:ss.ss'` | ICS INI (=Legacy) |
| `LONGITUD` | O | O | `LONGITUD` | `'dd:mm:ss.ss'` (West) | ICS INI (=Legacy) |
| `ELEVATIO` | O | O | `ELEVATIO` | Integer | ICS INI (=Legacy) |
| `OBSERVER` | O | O | `OBSERVER` | `KMTNetOp`* / user input | ICS code* / user input |
| `OBJECT` | O | O | `OBJECT` `+amp` | `bias`* / user input | ICS code* / user input |
| `FIELDID` | **X** | **X** | `FIELDID` | MEF converter generating — `v("OBJECT", "")` ← fallback | `OBJECT` |
| `PROJID` | O | O | `PROJID` `+amp` | `OBS`* / user input | ICS code* / user input |
| `IMAGETYP` | O | O | `IMAGETYP` `+amp` | `BIAS`* / `DARK` / `OBJECT` / `FLAT` / `SKY` / `DOMEFLAT` | ICS code* / user selection |
| `OBSTYPE` | O | O | `OBSTYPE` `+amp` | **사용자 정의 관측 유형** (어휘 2026-09-09 · 뜻 2026-09-24) — `SCIENCE`*(science) / `GUIDE`*(guide) / user input(대문자로 접음).  `PROJID` 처럼 **사용자 입력으로만 바뀌고**, 빈 값이 와도 기본값 `*` 이다.  ⛔ `IMAGETYP` 을 복사하지 않는다 — 레거시·구판의 사본 규칙도, 빈 값이면 복사하던 폴백(raw spec v1.13 ~ v1.15)도 폐지됐다.  기본값이 계통마다 다를 뿐 **계통 식별자가 아니다** — 계통은 `DATASRC` · `DETID` 가 가린다 (raw spec 5.4절) | ICS code* / user input |
| `INSTRUME` | O | O | `INSTRUME` | `'KMTK/KMTA/KMTC/KMTS 18k CCD'` (넷째 코드 **D-017** 개정) | ICS INI |
| `UNIQNAME` | O | **X** | — (⭐ v2.5.0 이 MEF `UNIQNAME` 카드를 폐지했다 — 정체는 `FILENAME` + `EXPID`) | replaced with `EXPID` card (v1.6 — 구 `ORIGNAME`) | ICS code |

**신규는 `FIELDID` 하나뿐이다.** 없으면 `OBJECT` 값이 그대로 들어간다 — 레거시가 필드명을 `OBJECT` 에 넣던 관행을 코드가 흡수한 형태다.

> 구 `없을 때`(converter v2.5.0 기본값): `BUNIT "ADU"` · `DETECTOR "e2v CCD290-99"` · `CCDXBIN/CCDYBIN 1` · `TELESCOP "KMTNet 1.6m"` · `INSTRUME "KMTS"` · `ELEVATIO -1`(v2.5.0 — 없음과 sentinel 이 같은 값이 됐다) · `FIELDID ← OBJECT` · 나머지 전부 `""`.  `ORIGIN` 은 기본값이 아니라 **상수 `'KASI'`** 다(v2.5.0 — v2.4.0 까지는 raw 를 복사하고 없으면 `"KASI"`).  `DETID` 에는 기본값이 있던 적이 없다 — v2.4.0 까지는 읽지 않았고 v2.5.0 은 대조에만 읽는다(구판의 `DETID "MK"/"NT"` 표기는 오기였다).

**`OBSERVAT` 는 converter 가 파일명의 사이트 코드와 교차 검증하는 카드다** — 불일치는 오류다 (v2.2.0 에서 도입, D-011 · 넷째 코드는 v2.4.0 에서 `KMTK`/`KASI` 로 개정, D-017). `SITEID` 로도 복제된다. ⚠️ **이 검사는 기본 출력 이름 경로에서만 돈다** — `-o` 를 주지 않았고 · 파일명이 `<SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits` 정규식에 맞고 · `OBSERVAT` 가 네 값(`CTIO` `SSO` `SAAO` `KASI`) 안일 때다(`default_output_name()`).  `OBSERVAT` 가 **없으면** 대조용 기본값 `'KMT'` 가 네 값 밖이라 멈추지 않는다(MEF `OBSERVAT` 는 빈 문자열).  파일명이 정규식에 안 맞으면 v2.5.0 은 경고만 내고 출력 이름을 대체 규칙으로 짓는다.  카드 값으로 변환이 멈추는 곳은 이것과 **pair 양쪽 `EXPID` 불일치**(v2.5.0 — 둘 다 있고 서로 다를 때) 둘이다.  나머지 카드는 없으면 조용히 기본값으로 지나가고, 선언이 converter 상수와 어긋나면 v2.5.0 은 경고와 HISTORY 를 남긴다(13장).

> **`OBSERVAT` · `ORIGIN` 확정 경위 (v1.7).** `OBSERVAT` 를 사이트 코드(`KMTA` 등)로 재정의하는 안이 검토됐으나 converter v2.2.0 의 교차검증(`OBS_PREFIX` 맵)과 정면 상충해 철회 — **현행 체계 그대로 `TESTBED`/`CTIO`/`SAAO`/`SSO` 로 확정**했고 개정 항목이 없다. `ORIGIN` 은 레거시 계승(관측소 raw 에서 OBSERVAT 와 중복)이되 개념을 **"이 파일이 생성된 곳"** 으로 정의한다: 관측소 raw = 관측소 이름 · 테스트베드 raw = `KASI` · KASI 파이프라인 산출물 = `KASI`. 이 개념의 귀결 하나 — converter 는 현재 raw `ORIGIN` 을 MEF 로 **복사**하는데(`v("ORIGIN","KASI")`), MEF 는 파이프라인 산출물이므로 **상수 `'KASI'` 로 쓰는 것이 맞다** (MEF Impacts v0.2 의 경미 C-항목).  → ⭐ **그 뒤**: `TESTBED` 는 **D-017** 로 폐지되고 `KASI` 가 넷째 값이 됐다(3.1 표 · converter v2.4.0). MEF `ORIGIN` 상수화는 **converter v2.5.0 이 반영했다**(`card("ORIGIN", "KASI")` — raw 를 읽지 않는다).

> ⚠️ **기본값이 진짜 값처럼 보이는 셋**: `DETECTOR="e2v CCD290-99"` · `TELESCOP="KMTNet 1.6m"` · `INSTRUME="KMTS"`. raw 가 안 실으면 이 값들이 사이트·망원경과 무관하게 박힌다.  (구판의 넷째 `ORIGIN="KASI"` 는 v2.5.0 에서 기본값이 아니라 상수가 됐다 — MEF 가 파이프라인 산출물이라 어느 사이트든 맞는 값이다.)
>
> 레거시 실측본과 대면 어긋남이 보였던 `INSTRUME`(레거시 `OBSERVAT='SSO'` 인데 `INSTRUME='KMTS'`)는 **v1.7 에서 형식이 확정됐다** — `'<SITE> 18k CCD'`(예: `'KMTA 18k CCD'`), 사이트와 함께 움직인다. `TELESCOP` 도 사이트별 번호(`#0/#1/#2/#3` — 규격 5.3.1절 표, KASI = `#0`)를 싣는다.

## 3.2 노출 · 시각

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `EXPTIME` | O | O | `EXPTIME` | **Real** [seconds] — 소수점 아래 최소 한 자리(`0.0` · `2.0` · 소수부가 있으면 그대로) (운영자 확정 2026-09-24, raw spec v1.16 5.4절 — 확인 요망 4 종결의 *"정수형 기본, 소수점 아래 값이 있을 때만 실수형"* 을 고친다) | ICS code* / user input |
| `DARKTIME` | O | **X** | `DARKTIME` | `EXPTIME` 과 동일 — 파생으로 충분, 카드 불요 (v1.8) | `EXPTIME` |
| `TSHOPEN` | O | **X** | `TSHOPEN` | `'HH:MM:SS.mmm'` — v1.8 판정: 싣지 않음 | ICS code |
| `TSHSHUT` | O | **X** | `TSHSHUT` | `'HH:MM:SS.mmm'` — v1.8 판정: 싣지 않음 | ICS code |
| `TIMESYS` | O | O | `TIMESYS` | `UTC`* — comment 는 `ICS Time System`, TCS 쪽은 신설 `TCSTIME`(7장) | ICS code |

> 구 `없을 때`(converter v2.5.0 기본값): `EXPTIME` `0.0` · `DARKTIME` = `EXPTIME` 값(v2.5.0 — 둘 다 없으면 `0.0`) · `TSHOPEN`·`TSHSHUT` `""` · `TIMESYS` `"UTC"`.

**이 그룹에서 가장 중요한 `DATE-OBS` 는 이 표에 없다** — `card()` 밖에서 쓰이므로 4장에 있다.

**`DARKTIME` · `TSHOPEN` · `TSHSHUT` 는 v1.8 판정으로 신규 raw 가 싣지 않는다.** `DARKTIME` 은 `EXPTIME` 과 같은 값이라 파생으로 충분하다 — ✅ converter v2.5.0 은 raw 에 `DARKTIME` 이 없으면 `EXPTIME` 값으로 채운다(`fnum(mk_hdr, "DARKTIME", exptime)`, `primary_cards()`).  **MEF `UT` 는 v2.5.0 부터 `TSHOPEN` 과 무관하게 `DATE-OBS` 를 그대로 싣는다** — PRIMARY 는 `DATE-OBS`(없으면 변환 시각), amp 헤더는 그 chip 파일의 `DATE-OBS`(없으면 빈 문자열)다.  ⚠️ **종전 문면의 *"raw 가 `TSHOPEN` 을 싣지 않으면 MEF `UT` 의 시각부가 빈다"* 는 사실이 아니었다** — v2.4.0 이하의 조립식은 `(DATE-OBS 날짜부 + "T" + TSHOPEN) if TSHOPEN else DATE-OBS` 라서, `TSHOPEN` 이 없으면 밀리초까지 든 `DATE-OBS` 전체가 `UT` 에 들어갔다(저장소의 가장 이른 판 v2.1.1 부터 같은 식).  그래서 `TSHOPEN` 폐지의 MEF `UT` 파급은 처음부터 없었고, 등재했던 C-항목(MEF Impacts v0.3)은 v2.5.0 이 `UT`·`DARKTIME` 을 정리하면서 닫혔다.  ⚠️ 이 거짓 전제가 LEECU 산출물로 옮겨 갔다 — converter v2.5.0 의 docstring·주석과 Keywords v1.1 `UT` 행이 *"시각부가 비어 있었다"* 고 적는다(정정 요청은 통합 문서).

> ⚠️ `EXPTIME` 의 기본값이 `0.0` 이고 `DARKTIME` 은 그것을 따른다 — 카드가 없으면 두 카드 다 **"노출 0초"** 라는 유효해 보이는 값이 된다.

## 3.3 Archon 정체 · 버전

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `CTRL1ID` | **X** | O | `CTRL1ID` | `'KMTA-SCI-101'` — ID 숫자 = IP (`__reference/Archon_Unit_Info.txt`, 확인 요망 6 종결 — 운영자 재가 2026-08-22) | ICS INI |
| `CTRL1SN` | **X** | O | `CTRL1SN` | `'STA-0288'` | ICS INI |
| `CTRL1FW` | **X** | **X** | `CTRL1FW` | `CTRLxCFG` 로 귀속 (v1.8) | Archon telemetry |
| `CTRL1CFG` | **X** | O | `CTRL1CFG` (⭐ v2.5.0 pass-through — 없으면 `'UNKNOWN'`. v2.4.0 까지 converter 미독) | `'KMTA_SCI_101_STA0288_R2608_MK'` | ICS INI |
| `CTRL2ID` | **X** | O | `CTRL2ID` | `'KMTA-SCI-102'` | ICS INI |
| `CTRL2SN` | **X** | O | `CTRL2SN` | `'STA-0289'` | ICS INI |
| `CTRL2FW` | **X** | **X** | `CTRL2FW` | `CTRLxCFG` 로 귀속 (v1.8) | Archon telemetry |
| `CTRL2CFG` | **X** | O | `CTRL2CFG` (⭐ v2.5.0 pass-through — 없으면 `'UNKNOWN'`. v2.4.0 까지 converter 미독) | `'KMTA_SCI_102_STA0289_R2608_NT'` | ICS INI |
| `CTRLVER` | **X** | **X** | `CTRLVER` | `CTRLxCFG` 로 귀속 (운영자 개정은 행 삭제 — converter 가 읽는 사실 기록을 위해 유지) |  |
| `TIMVER` | **X** | **X** | `TIMVER` | `CTRLxCFG` 로 귀속 (v1.8) |  |
| `BIASVER` | **X** | **X** | `BIASVER` | `CTRLxCFG` 로 귀속 (v1.8) |  |
| `CLKVER` | **X** | **X** | `CLKVER` | `CTRLxCFG` 로 귀속 (v1.8) |  |
| `XTALKVER` | **X** | **X** | `XTALKVER` | **Pipeline calibration DB 소관** — raw 미기재 (확인 요망 8 종결, 운영자 재가 2026-08-22) | Pipeline caldb (C-14) |
| `REFVER` | **X** | **X** | `REFVER` | **Pipeline calibration DB 소관** — raw 미기재 | Pipeline caldb (C-14) |
| `CATVER` | **X** | **X** | `CATVER` | **Pipeline calibration DB 소관** — raw 미기재 | Pipeline caldb (C-14) |

> 구 `없을 때`(converter 기본값): `CTRL1*`·`CTRL2*` `"UNKNOWN"` · `CTRLVER "ARCHON-v1.0"` · `TIMVER "TIM-v1.0"` · `BIASVER "BIAS-v1.0"` · `CLKVER "CLK-v1.0"` · `XTALKVER "UNMEASURED"` · `REFVER`/`CATVER` `"N/A"`. 버전 문자열의 근거 순환(0.2 의 "하드코딩 × ICD 침묵" 칸)은 **v1.8 에서 `CTRLxCFG` 귀속으로 정리됐고 v1.13 에서 재가로 확정됐다(확인 요망 6·8 종결)** — 추적 대상이 적용 설정 파일 하나로 모이고, raw 는 그 파일명(`CTRL1CFG`/`CTRL2CFG`)만 실으면 된다. **`CAMVER` 도 판단 참조점이다 (운영자, 2026-08-22)**: HW·성능상 변경사항이 있을 때만 올리는 카드라, 설정 상세는 `CTRLxCFG` 로 · **전자부 HW/성능 세대는 `CAMVER` 로** 판단할 수 있다. 반면 `XTALKVER` · `REFVER` · `CATVER` 의 정본은 ACF 파일이 아니라 **calibration DB** 다(C-14) — 귀속 표기를 셋에 붙이면 없는 곳을 가리키는 포인터가 된다.

> **raw 쪽 결측 규칙 — `CTRLnID` · `CTRLnSN`** (운영자 확정 2026-09-23, 규격 5.5절) — 값의 원천은 INI 하나다. INI 에 값이 없으면 **`'NC'`** 를 싣고, Archon `SYSTEM` 응답의 값(펌웨어 문자열 · 16진 `BACKPLANE_ID`)으로 대신 채우지 않는다. converter 는 그 `'NC'` 를 문자열 그대로 MEF 로 옮긴다(기본값 `"UNKNOWN"` 은 카드가 **없을** 때만 들어간다 — `hval()` 은 키가 없을 때만 기본값을 준다).

**표의 15장 전부 레거시 raw 에 없다** — 7장의 도입 후보와 같은 부류다(`CTRL1CFG`/`CTRL2CFG` 는 converter v2.2.0 이 읽지 않던 신설이라 1장 v2.2.0 집계 어디에도 안 들고, 가족 묶음으로 이 표에 둔다 — ⭐ v2.5.0 은 둘 다 MEF 로 옮긴다). 성격이 둘로 갈린다.

**`XTALKVER` · `REFVER` · `CATVER` 셋은 raw 가 실을 필요가 없다.** converter 가 읽기는 하지만 raw 에 그 카드가 없으므로 **기본값(`"UNMEASURED"` · `"N/A"`)으로 채워지고, 지금은 그것이 맞는 상태다.** 구판 규격 v1.2 5.12절이 *"현행 converter 는 이 값들을 MK 헤더에서 읽고 있지만 실제로는 calibration DB 소관"* 이라고 정리했고(현행은 규격 5.10절 Calibration 행 — raw 미기재 · L0 재량 · L1 필수), converter v2.5.0 도 여전히 MK 헤더에서 읽는다. caldb 주입으로 바꾸는 것이 **변경점 C-14** 다. 즉 이 셋의 `X` 는 결함이 아니라 **의도된 상태**다. **미기재 근거 확정(운영자, 2026-08-22, 확인 요망 8 종결)**: 이 값들은 **HW·성능 변화 없이도 pipeline setup 에서 바뀔 수 있어** 취득 시점의 raw 에 실으면 곧 낡은 값이 된다 — raw 는 취득 시점에 고정되는 사실만 싣는다. **계층 규칙(운영자, 2026-08-22)**: raw = 미기재 · **전처리 전 MEF(L0) = 수록 여부는 pipeline 팀 판단** · **전처리 후 MEF(L1) = 필수 수록**(보정에 실제 적용한 버전이므로). 이 규칙은 통합 문서(LEECU 전달용)에도 등재했다.

나머지는 신규 전자부에 필연적으로 따라오는 것들이다. v1.8 판정으로 **정체 4장(`CTRLxID`/`CTRLxSN`)과 설정 포인터 2장(`CTRLxCFG`)이 도입 `O`**, 펌웨어·버전 문자열(`CTRLxFW` `TIMVER` `BIASVER` `CLKVER`)은 **`CTRLxCFG` 로 귀속돼 `X`** 다.

**`CTRL1*` · `CTRL2*` 가 색인형인 이유**: converter 가 PRIMARY 의 컨트롤러 정체를 **MK 헤더에서만** 읽으면서 컨트롤러 두 대분 정체를 요구한다(v2.5.0 도 같다 — amp 헤더만 v2.5.0 부터 그 chip 파일의 헤더를 받는다, C-17). 단수형으로 두면 MEF 가 전부 `UNKNOWN` 을 받는다. 레거시도 raw 파일마다 `KBUILD`/`MBUILD`/`TBUILD`/`NBUILD` 를 다 실어 같은 구조였다 — 그 넷은 8장에서 폐지되고 `CTRL1FW`/`CTRL2FW` 가 자리를 물려받았다 — 그리고 그 둘도 v1.8 에서 `CTRLxCFG` 귀속으로 정리됐다.

> **컨트롤러 2대분을 양쪽 raw 에 모두 싣는다** (운영자 확정, v1.7_revision) — 파일을 만든 컨트롤러 것만 싣는 안도 검토됐으나 기각했다. guide FITS 는 컨트롤러가 1대라 `CTRL1xx` 한 벌만 싣고, 컨트롤러 수가 늘면 `CTRLnxx` 벌이 늘어나는 **확장 규약**이다.

> ⚠️ **버전 문자열의 기본값이 진짜 provenance 처럼 보인다** — `"ARCHON-v1.0"` · `"TIM-v1.0"` · `"BIAS-v1.0"` · `"CLK-v1.0"`. raw 가 안 실어도 MEF 에 그럴듯한 버전이 박히고 오류는 나지 않는다. 이 값들의 **근거가 순환하는 문제**는 0.2 의 "하드코딩 × ICD 침묵" 칸이다.  ⚠️ converter v2.5.0 에서는 **한 MEF 안에 `BIASVER`·`CLKVER` 값이 둘**이다 — PRIMARY 는 이 기본값(`"BIAS-v1.0"`·`"CLK-v1.0"`)이고 `VOLTINFO` 표 헤더는 상수 `'UNKNOWN'` 이다(LEECU 판단 항목 — 통합 문서 §7-2).

## 3.4 TCS 링크 · 포인팅

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `TCSLINK` | O | O | `TCSLINK` | `Up` / `Idle` / `Down` | TCS relay |
| `TCSARC` | O | O | `TCSARC` |  | TCS relay |
| `TCSQDATE` | O | O | `TCSQDATE` |  | TCS relay |
| `TCSUDATE` | O | O | `TCSUDATE` |  | TCS relay |
| `RADECSYS` | O | O | `RADECSYS` · `RADESYS` (⭐ v2.5.0 — seed WCS 를 쓸 때 `+amp`) | `ICRS`* | ICS code |
| `RA` | O | O | `RA` `+amp` · ⭐ v2.5.0: `RA_DEG` · amp seed WCS `CRVAL1` (파싱될 때만) | `'hh:mm:ss.ss'` | TCS relay |
| `DEC` | O | O | `DEC` `+amp` · ⭐ v2.5.0: `DEC_DEG` · amp seed WCS `CRVAL2` (파싱될 때만) | `'±dd:mm:ss.s'` | TCS relay |
| `EQUINOX` | O | O | `EQUINOX` · ⭐ v2.5.0: `+amp`(seed WCS 를 쓸 때) — MEF 는 실수 | **실수** — 견본 `2000.0`, 결측은 실수 sentinel **`-999.0`** (raw spec v1.14, 운영자 확정 2026-09-23 — TC 가 보낸 문자열 `'2000.000'` 을 ICS 가 수치로 바꿔 싣는다. 레거시·v1.13 까지는 문자열, 규격 5.7절) | TCS relay |
| `HA` | O | O | `HA` `+amp` | `'±hh:mm:ss'` | TCS relay |
| `ST` | O | O | `ST` `+amp` | `'hh:mm:ss'` | TCS relay |
| `SECZ` | O | O | `SECZ` `+amp` |  | TCS relay |
| `ALT` | O | O | `ALT` `+amp` |  | TCS relay |
| `AZ` | O | O | `AZ` `+amp` |  | TCS relay |
| `TCSDRIVE` | O | O | `TCSDRIV` — `v("TCSDRIV", "")` ← fallback |  | TCS relay |
| `TELMOVE` | O | O | `TELMOVE` |  | TCS relay |

> 구 `없을 때`(converter v2.5.0 기본값): `RADECSYS "ICRS"`(`RADESYS` 도) · `EQUINOX 2000.0` — 카드가 없거나 값이 결측 낱말(`NC` `N/A` `UNKNOWN` 등)·비수치일 때다. raw 의 `-999.0` 은 유한수라 **그대로 간다** · `RA`/`DEC` 는 **기본값이 없다** — 비면 카드를 싣지 않는다(v2.4.0 까지는 `"00:00:00.00"` · `"+00:00:00.0"`) · 나머지 전부 `""`.

**전부 레거시 계승이고 v1.8 에서 전 행 `O` 로 판정됐다.** 시각계 선언은 초안 v0.3.5 에서 둘로 갈라졌다 — `TIMESYS`(ICS 시각계, 3.2절) · **`TCSTIME`**(TCS 시각계, 7장 신설 `O`). 4장의 `TCSDRIV` 만 레거시에 없는데 그것도 구멍이 아니다 — converter 가 **`TCSDRIVE`(8자)를 먼저 보고** 없을 때만 `TCSDRIV` 를 본다. 레거시가 쓰는 이름이 `TCSDRIVE` 이므로 **raw 는 `TCSDRIVE` 로 쓰면 된다.**

> ✅ **`RA` · `DEC` 의 기본 좌표는 converter v2.5.0 이 걷었다** (D-023). v2.4.0 까지는 기본값이 `"00:00:00.00"` · `"+00:00:00.0"` 이라, 카드가 없으면 **형식이 유효한 그럴듯한 좌표**가 들어가 하류에서 걸러지지 않았다.  v2.5.0 은 값이 비면 `RA`/`DEC` 카드를 싣지 않고, 파싱되지 않으면(비었거나 `'NC'` 등 — 비지 않은 값은 문자열 그대로 `RA`/`DEC` 카드로 간다) amp 의 seed WCS 카드를 통째로 빼고 `WCSOMIT=T` 를 싣는다.  `IMAGETYP` 이 `BIAS`/`DARK`/`DOMEFLAT` 이면 좌표와 무관하게 `WCSSKY=F` · `WCSOMIT=T` 다(3.1 `IMAGETYP` 어휘가 여기서 쓰인다 — 없거나 모르는 값은 하늘을 본 프레임으로 다룬다).
>
> ⚠️ **남은 것은 `EQUINOX` 다.** raw 결측 `-999.0` 은 PRIMARY 와 (seed WCS 가 써질 때) amp 헤더에 그대로 실리고, `mef_pipeline` 이 amp 의 WCS 카드를 L1 CCD WCS 로 복사하므로(`steps/assemble.py` `WCS_COPY_KEYS`) L1 까지 간다.  카드가 없거나 `'NC'`·비수치면 그럴듯한 `2000.0` 이 된다 — v1.13 이전 raw 의 결측 `'NC'` 가 여기 든다.  좌표 해는 틀어지지 않는다 — `RADESYS` 가 `ICRS` 라 FITS WCS 가 `EQUINOX` 를 해석에 쓰지 않고 `CRVAL` 은 `RA`/`DEC` 만으로 정해진다.  수치로 세차 보정을 하는 하류만 깨진다(정정 요청은 통합 문서).

## 3.5 AUX — 링크 · 필터/셔터 · 초점

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `AUXLINK` | O | O | `AUXLINK` | `Up` / `Down` | AUX relay |
| `AUXARC` | O | O | `AUXARC` |  | AUX relay |
| `AUXQDATE` | O | O | `AUXQDATE` |  | AUX relay |
| `AUXUDATE` | O | O | `AUXUDATE` |  | AUX relay |
| `FSSTAT` | O | O | `FSSTAT` |  | AUX relay |
| `FILTOP` | O | O | `FILTOP` |  | AUX relay |
| `FILNUM` | O | O | `FILNUM` |  | AUX relay |
| `FILTER` | O | O | `FILTER` `+amp` |  | AUX relay |
| `SHUTOP` | O | O | `SHUTOP` | `NC` / `STANDBY` / `OPENING` / `OPENED` / `CLOSING` / `RELOADING` / `ERROR` | AUX relay |
| `SHUTTER` | O | O | `SHUTTER` | `OPEN` / `CLOSED` / `UNKNOWN` | AUX relay |
| `FSATEMP` | **X** | O | `FSATEMP` |  | Radionode sensor |
| `FSAHUM` | **X** | O | `FSAHUM` |  | Radionode sensor |
| `FSADEW` | **X** | **X** | `FSADEW` | 듀어 윈도우 온도 기준 판단이 어려우며, 공기 온도로 구한 dewpoint 는 큰 의미가 없어 삭제 — 계산·정보제공은 raw FITS header 범주 밖 (운영자 판정) | Calculation with FSATEMP·FSAHUM |
| `FSAALRM` | **X** | **X** | `FSAALRM` | 상동 | Detection with FSADEW·FSATEMP |
| `FASTAT` | O | O | `FASTAT` |  | AUX relay |
| `FAFOCUS` | O | O | `FAFOCUS` |  | AUX relay |
| `FATILTNS` | O | O | `FATILTNS` |  | AUX relay |
| `FATILTEW` | O | O | `FATILTEW` |  | AUX relay |
| `FAPOSS` | O | O | `FAPOSS` |  | AUX relay |
| `FALIMS` | O | O | `FALIMS` |  | AUX relay |
| `FAPOSE` | O | O | `FAPOSE` |  | AUX relay |
| `FALIME` | O | O | `FALIME` |  | AUX relay |
| `FAPOSW` | O | O | `FAPOSW` |  | AUX relay |
| `FALIMW` | O | O | `FALIMW` |  | AUX relay |

> 구 `없을 때`(converter 기본값): 전부 `""`.

**24개 중 신규는 FSA 환경 4개(`FSATEMP` `FSAHUM` `FSADEW` `FSAALRM`)뿐**이고 나머지 20개는 레거시 계승이다.

FSA 4개는 레거시 raw 어디에도 없다 — 검토 항목 9의 물음("없는 장치를 sentinel 로 적으면 정보가 흐려진다")의 판정은 **v1.9 에서 둘로 갈렸다**: 실측 2장 `FSATEMP` · `FSAHUM` 만 `O`(`Radionode sensor` — 초안 v0.3.7 반영 확인, 확인 요망 2 종결)이고, 파생 2장 `FSADEW` · `FSAALRM` 은 **`X`** 다 — 듀어 윈도우 온도 기준 판단이 어렵고 공기 온도로 구한 dewpoint 는 큰 의미가 없어, **계산·감지 파생은 raw FITS header 범주 밖**으로 정리했다(운영자, v1.8_revision).

`SHUTTER` 는 `SHUTOP` 의 **순수 함수**이고 "완전 개방" 을 뜻하지 않는다 — `OPEN` 이 개방중·개방·폐쇄중을 모두 덮는다 (구판 규격 v1.2 5.10절의 통제 어휘 — 현행 규격 5.8절 `SHUTTER` 행).

> **`FSATEMP` · `FSAHUM` 의 형·포맷 (v1.12 잠정 → 2026-09-09 확정)** — 문자열(3.7 의 HK 온·습도 확정과 동일). ✅ **확인 항목이 닫혔다** — Radionode Open API `channel/get_lst` 원문이 `ch_value` 를 **소수 2자리 문자열**(`"22.35"` · `"47.67"`, `ch_unit` `℃`/`%`)로 주는 것을 운영자가 실측해, *"원값 그대로 싣기"* 로 최종 확정했다(게이지 원문을 존중한 `DEWPRES` 와 같은 정신. HK CSV 원값 열도 `22.19`·`53.14` 로 같다). 표기는 **소수 2자리**이고, `FSATEMP` 는 온도 부호 규약(raw spec 5.0절, v1.10 편입)을 따라 `'+22.35'`, `FSAHUM` 은 습도라 부호 없이 `'47.67'` 이다. 측정불가 sentinel 은 HK 와 같은 **`'-999.99'`**. ⛔ **v1.12 의 *"ENS식 잠정 채택"*(부호 생략 · 소수 1자리)은 두 대목 다 폐기한다** — *부호 생략* 은 raw spec v1.10 이 `FSATEMP` 를 온도 부호 규약에 편입한 시점에 이미 무효였고(구판 문면이 그때 따라오지 못한 것이다), *소수 1자리* 의 근거였던 *"레거시 `ENS1 = '23.0'` 선례"* 는 성립하지 않는 유추였다 — `ENS1`–`ENS7` 은 raw spec 5.8절이 *"중계 그대로"* 로 규정해 **TCSSTATUS 가 준 자릿수**가 그대로 갈 뿐이고 FSA 는 출처가 다르다. 같은 Radionode 의 `HEBOX` 와 한 규약이 된다. raw spec ~~OI-16~~ **종결**.

## 3.6 돔 · 미러커버 (돔 상태·고도 = TCS 관장 v1.11 · 돔 **방위** 셋 = 돔 제어 프로그램 redis, D-021)

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `DSSTAT` | O | O | `DSSTAT` |  | TCS relay* |
| `DSUP` | O | O | `DSUP` |  | TCS relay* |
| `DSLW` | O | O | `DSLW` |  | TCS relay* |
| `DSSAF` | O | O | `DSSAF` |  | TCS relay* |
| `DSAUTO` | O | O | `DSAUTO` |  | TCS relay* |
| `DSALT` | O | O | `DSALT` |  | TCS relay* |
| `DSAZ` | **X** | O | `DSAZ` |  | **REDIS (dome control)** (D-021) |
| `DSTELALT` | **X** | O | `DSTELALT` (`DSTEL` → `DSTELALT`) |  | TCS relay* |
| `DSTELAZ` | **X** | O | `DSTELAZ` |  | **REDIS (dome control)** (D-021) |
| `DALTERR` | **X** | O | `DALTERR` |  | ICS calculation (고도차 — 접기 없음) |
| `DAZERR` | **X** | O | `DAZERR` |  | **REDIS (dome control) or ICS calculation** (D-021) |
| `MCSTAT` | O | O | `MCSTAT` |  | AUX relay |
| `MCPOS` | O | O | `MCPOS` |  | AUX relay |

> 구 `없을 때`(converter 기본값): 전부 `""`.

**돔 필드는 셋으로 갈린다** — 계승 6(`DSSTAT` `DSUP` `DSLW` `DSSAF` `DSAUTO` `DSALT`) · 신규 4(`DSAZ` `DSTELAZ` `DALTERR` `DAZERR`) · 개칭 1(`DSTELALT`). **출처로는 넷으로 갈린다** — 방위 셋(`DSAZ` `DSTELAZ` `DAZERR`)은 `REDIS (dome control)` 이고(`DAZERR` 는 `dome_del_az` 키가 없을 때만 ICS 가 계산한다, D-021) · 고도차 `DALTERR` 는 `ICS calculation` · 나머지 7장(계승 6 + `DSTELALT`)은 `TCS relay` · 미러커버 2장은 `AUX relay` 다.

> **돔 출처 변경 (운영자, v1.10_revision)** — dome shutter 정보의 source 가 기존 `AUX relay` 에서 **`TCS relay or REDIS`** 로 변경됐다. 돔 azimuth 는 원래 TCS 에서 관장하고, **newTCS 로 전환되면서 dome shutter control 이 TCS 에 편입**되었으므로 돔 정보는 AUX 가 아닌 TCS 에서 가져와야 한다. 이에 따라 초안 헤더의 DS 카드 블록 위치도 **TCS Information and Status 절**로 옮겨졌다. 미러커버 2장(`MCSTAT` `MCPOS`)은 그대로 AUX 소관이라 절 이름에서 "AUX" 를 뗐다. (`DSAZ` 행의 구 표기 `TCS relay or REDIS (v1.8)` 는 `*` 기본 표기로 정규화. `DALTERR` 는 망원경–돔 **고도**의 차이값이라 중계가 아니라 `ICS calculation` 이다. ⭐ **`DAZERR` 는 D-021 로 중계가 됐다** — 아래 상자.)

> **돔 방위 셋의 출처 확정 (D-021 · CR-003, 2026-09-11)** — `DSAZ` · `DSTELAZ` · `DAZERR` 의 Source 가 `TCS relay or REDIS*` / `ICS calculation` 에서 **`REDIS (dome control)`** 로 확정됐다. 돔 제어 프로그램이 `dome_az` · `dome_tel_az` · `dome_del_az` 에 TTL 수백 ms 로 실어 두는 값을 ICS·ICG 가 직접 읽는다(키가 없으면 `NC`, 옛 값을 이어 싣지 않는다). ⭐ **TC 는 이 셋을 보내지 않는다** — 레거시 TCSAgent 트리에 `DSAZ`/`DSTELAZ` 가 0건이라 종전 `TCS relay` 갈래는 실현될 수 없는 갈래였고, 그래서 나머지 돔 카드의 `or REDIS` 도 걷어 `TCS relay*` 로 좁혔다. `DAZERR` 는 **중계값**이 되고 `ICS calculation`(`DSAZ` − `DSTELAZ` 를 −180~+180 으로 접은 값)은 `dome_del_az` 만 없을 때의 예비 경로로 남는다. `DALTERR` 는 이 결정 밖이다 — **고도**차라서 `AUXSTATUS` 실값으로 계산한다. ⚠️ 판정(`Use in MEF` · converter 독취 O/X)에는 변화가 없다 — **값 공급 계통만 바뀐다.** ⏳ 계승 여섯 장 + `DSTELALT` 가 실제로 오는 곳은 벤치에서 여전히 `AUXSTATUS` 블록이다(2026-09-08 · 레거시 `commands.c` 의 `cmd_auxstatus` 도 AUX 응답에 실었다) — `TCS relay` 표기는 newTCS 편입을 전제한 것이고, 전환 실태는 별도 확인 항목이다.

> `DSTELAZ` 는 TCS `AZ` 와 중복일 수 있어 **돔 쪽 TelAz 가 별도 관리되는지 확인 후 도입을 한 번 더 검토**한다 — 일단은 정보 확인 편의를 위해 싣는 방향이다(운영자, v1.7_revision). 돔 신설 4장은 초안 v0.3.7 에 반영 확인됐다(확인 요망 3 종결).  → **D-021 로 원천이 확정됐다** — 돔 제어 프로그램이 따로 관리하는 `dome_tel_az` 가 `DSTELAZ` 다(위 상자). 남은 물음은 방위 기준(규격 OI-30)과 redis 실기 확인(규격 OI-31)이다.

`DSTELALT` 는 레거시 `DSTEL` 의 개칭이다 (D-013). **공급 계통이 TCS 로 바뀌어도 converter 가 `DSTELALT` 만 읽는 사실(fallback 없음)은 그대로다** — 중계 필드명이 무엇이든 ICS 가 `DSTELALT` 카드로 실어야 한다. 레거시 이름 `DSTEL` 은 6장에 있다.

> ✅ **계승 6개는 구현에 반영됐다** — 취득 SW 가 `AUXSTATUS` 응답에서 여섯 필드를 받아 카드로 싣는다(중계 필드 목록 · 헤더 템플릿 자리). 레거시 설계에 이미 있던 카드라 검토 안건이 아니었고, **구현 일감으로도 닫혔다.**

## 3.7 AUX — 열 환경 · 영상 점검

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `CHSTAT` | O | **X** | `CHSTAT` | v1.8 판정: 싣지 않음 — v1.9 재잔존 → **v1.11 재삭제 검증 완료(확인 요망 1 종결)** | AUX relay |
| `ENSTAT` | O | O | `ENSTAT` |  | AUX relay |
| `ENFAN` | O | O | `ENFAN` |  | AUX relay |
| `CCDTEMP` | O | O | `CCDTEMP` | [degC] — **실측 대표 센서** (comment `CCD temperature [deg C]` — chip 귀속 `M` 은 2026-08-30 제거) | ICG RTD measurement |
| `DEWPRES` | O | O | `DEWPRES` | `x.xxe-x` [torr] 문자열 · 측정불가 `9.99e-9`* (0·음수·비수치·범위 밖 — 게이지의 `0.00e-0` 포함). ⚠️ **게이지 Off·예열·켜짐대기 구간도 같은 sentinel 이고 그것은 결측이 아니라 의도된 상태다** (규격 5.6절) | ICG RTD measurement |
| `PT30N1` | O | O | `PT30N1` | PT-30 #1 cold-end [degC] | ICG RTD measurement |
| `PT30N2` | O | O | `PT30N2` | PT-30 #2 cold-end [degC] | ICG RTD measurement |
| `CHARCOAL` | O | O | `CHARCOAL` | charcoal canister [degC] | ICG RTD measurement |
| ~~`AIR_IN`~~ | **폐지** | — | — (⚠️ converter v2.5.0 은 여전히 raw 를 읽어 빈 MEF `AIR_IN` 을 싣는다 — 통합 문서 §7-2 판단 항목) | ~~열교환기 흡기 [degC]~~ — **raw spec v1.5 에서 폐지 (운영자 확정 2026-08-25)**, 5.10절 목록 | ~~standalone RTD readout unit~~ |
| ~~`AIR_OUT`~~ | **폐지** | — | — (〃) | ~~열교환기 배기 [degC]~~ — v1.5 폐지 | ~~standalone RTD readout unit~~ |
| ~~`GLYC_IN`~~ | **폐지** | — | — (〃) | ~~HE box 유입 glycol [degC]~~ — v1.5 폐지 | ~~standalone RTD readout unit~~ |
| ~~`GLYC_OUT`~~ | **폐지** | — | — (〃) | ~~HE box 배출 glycol [degC]~~ — v1.5 폐지 | ~~standalone RTD readout unit~~ |
| `CHKIMG` | **X** | **X** | `CHKIMG` |  | Pipeline 에서 판별하는 대상 — raw 카드 아님 (v1.10) |
| `CHKIMG_C` | **X** | **X** | `CHKIMG_C` |  | Pipeline 에서 판별하는 대상 — raw 카드 아님 (v1.10) |

> 구 `없을 때`(converter 기본값): 전부 `""`.

**14개 중 신규는 `CHKIMG` · `CHKIMG_C` 둘뿐**이고, 이 둘도 레거시 raw 에 없어 FSA 4개와 같은 물음에 걸렸었다 (검토 문서 5.4절 9번). FSA 쪽은 v1.8 에서, 이 둘은 **v1.10 에서 `X` 로 판정됐다** — 영상 점검은 취득 시점에 존재할 수 없는 값이고 **pipeline 이 판별하는 대상**이라 raw 카드가 아니다. 이로써 검토 항목 9 는 전량 종결이다.

**`CCDTEMP` 의 평균 파생(D-013)은 v1.8 에서 폐기됐다.** 온도센서 구성이 바뀌어 **실측 대표 센서 1개** 값을 싣는다(comment `CCD temperature [deg C]` — chip 귀속 `M` 은 2026-08-30 제거) — 출처는 `ICG RTD measurement`, `CCDTEMP1`/`CCDTEMP2` 후보는 **제외 확정**이다(7장 `X`). ⚠️ 대표값을 파일만으로 검산할 근거는 사라졌다 — 센서 이상은 취득 SW 로그가 담는다. MEF/L1 쪽에는 고칠 정의 문구("평균 파생")가 없다 — `mef_fits_spec` · `mef_converter` · `mef_pipeline` 어디에도 그 정의가 없어(2026-09-24 확인 — 정의서 v1.1 §4.8 은 이름만 나열한다) 그 C-항목은 **해당 없음**으로 닫혔다([통합 문서 v1.2](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.2.md) Part 1 §1 「C-신설: HK 온도 카드 재구성」 ② — 처음 등재는 MEF Impacts v0.3).

**HK 온도·습도 카드는 전부 문자열이다 (확인 요망 9 종결 — 운영자 확정 2026-08-22).** 레거시 실측이 이미 부호 포함 문자열(`'-103.16 '` · `'+34.98  '`)이었고 converter 는 pass-through 라 문자열 계승이 아카이브 전체의 형을 통일한다 — 신규만 실수형이면 같은 이름에 두 형이 섞인다. 표기는 초안대로 **부호 포함 소수 2자리**(`'-101.23'` · `'+16.78'`)다. **측정불가 sentinel 은 온도·습도 전 카드 `'-999.99'` 단일값** — 온도로는 불가능한 값이고 습도로는 음수라 불가능하다 (기각안: `-99.99` 는 CCDTEMP 냉각 램프가 실제로 지나가는 값, 습도 `0.00` 은 유효 측정값). ✅ **`ics_sim` 의 문자열 전환은 끝났다** — `rawhdr.format_temp()` 가 `f'{t:+.2f}'` 문자열을 내고 측정불가는 전부 `'-999.99'` 로 접으며 `rawcards.CARDS` 의 HK 온·습도 카드가 전부 `'S'` 다.  종전 문면의 *"고칠 대상"* 은 걷는다.  ⭐ **"측정불가" 의 범위는 raw spec 5.0·5.6절이 정한다** (운영자 확정 2026-09-06) — 센서 한계 밖이거나 채널이 미연결(`'-273.15'` — 0 K 를 ℃ 로 옮긴 값)인 값은 측정불가가 **아니라 실측**이므로 그대로 실린다.  sentinel 은 규격 5.0절이 든 사유 넷 — 장치가 값을 주지 않았거나 · 수치로 안 읽히거나 · 표본이 낡았거나 · science 가 그 `GO` 의 `HKDATA NOW` 답을 받지 못한 자리 — 에만 쓴다.  ⚠️ 한계로 값을 버리던 종전 구현은 **히터 과열을 센서 결측으로 위장**시켰다.

**`DEWPRES` 는 문자열 카드다** — 지수 표기 `x.xxe-x` 를 고정하려면 실수 카드로는 안 되고(astropy 가 표기를 정한다), 측정불가는 전부 **`9.99e-9`** 로 접는다. 레거시의 "AUX relay" 출처는 HK 에서 전부 물러났다. ⭐ **raw spec v1.10(2026-09-04)에서 `ICG heater` 계통이 신설되어 공급 계통은 셋이다** — `ICG RTD`(온도·압력) · `Radionode`(`FSATEMP`·`FSAHUM`·`HEBOX`) · **`ICG heater`**(`HTREN`·`HTRSET`·`HTROUT`·`HTRFORCE`). 히터 넷은 값의 **층이 둘로 갈린다** — `RCONFIG` 되읽기(설정값 셋)와 `STATUS` `MOD10/HEATERAOUTPUT`(`HTROUT` — FW 1.0.1252 로 키 확인, 측정/명령값 여부 OI-28)이고, 되읽기 값은 **명령이 아니라 컨트롤러가 받아들인 값**이다 (raw spec 5.6.2절).

## 4. `card()` 밖에서 쓰이는 둘

| Raw Keywords | Raw Legacy | Raw Archon | MEF Usage | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `DATE-OBS` | O | O | PRIMARY `DATE-OBS` · `MJD-OBS` · `JD` · `UT` 와 amp `UT` 를 여기서 파생시킨다(v2.5.0 — `UT` = `DATE-OBS` 그대로). ⚠️ **없으면 PRIMARY 네 카드가 변환 시각(now)으로 대체**되어 관측과 무관해지고(amp `UT` 는 빈 문자열) **그래도 오류가 나지 않는다** (규격 6장 "조용한 오염" 행 — 구판 v1.2 6.2절. C-6 은 v2.5.0 에도 미반영) | `'YYYY-MM-DDThh:mm:ss.mmm'` — **밀리초 필수** (D-014) | ICS code (**적분 개시 시각** — `BIAS`·`DARK` 를 포함한 모든 영상. 셔터 노출은 ICS 가 `SHOPEN` 을 지시한 시각, 셔터를 열지 않는 노출은 컨트롤러 적분을 건 시각 — 규격 5.4절, 운영자 확정 2026-09-23) |
| `TCSDRIV` | **X** | **X** | `TCSDRIVE` 가 없을 때만 보는 fallback 이다. 레거시가 쓰는 이름은 8자 `TCSDRIVE` 이므로 **구멍이 아니다** |  |  |

**이 문서 전체에서 가장 위험한 카드가 `DATE-OBS` 다.** 다른 카드는 없으면 빈 문자열이 들어가 나중에라도 눈에 띄지만, `DATE-OBS` 는 **그럴듯한 시각**으로 채워져 티가 나지 않는다.

## 5. `hval()` 로 직접 읽는 것

`v()` 를 거치지 않고 변환 로직이 직접 읽는 카드다. MEF 카드로 옮기는 것이 아니라 **픽셀 해석과 검증에 쓴다.**

| raw 키워드 | 쓰임새 |
| --- | --- |
| `BITPIX` · `BSCALE` · `BZERO` | 픽셀 값 복원 (`BITPIX=16` + `BZERO=32768` 부호없는 저장) |
| `NAXIS1` · `NAXIS2` | raw 영상 크기 확인 (`19200 x 9400`) |
| `OBSERVAT` | 파일명 사이트 코드와 **교차 검증** — 불일치는 오류 (v2.2.0, D-011). ⚠️ 기본 출력 이름 경로에서만 돈다(`-o` 없음 · 파일명 정규식 · `OBSERVAT` 네 값 안 — 3.1절) |

> ⭐ **v2.5.0 이 더한 검증 읽기** (1장 집계에서는 각 카드의 장에 센다) — ① pair 양쪽 **`EXPID`** 가 둘 다 있고 서로 다르면 **오류로 멈춘다**(`convert()`). ② geometry 선언 12장(`NAXIS1`/`NAXIS2` · `AMPNAX1`/`AMPNAX2` · `IMAGEX`/`IMAGEY` · `PRESCNX`/`PRESCNY` · `OVRSCNX`/`OVRSCNY` · `NAMPDET` · `NAMPRAW`)과 실수 넷(`PIXSCALE` · `PIXSIZE` · `CCDXBIN` · `CCDYBIN`)을 자기 상수와 대조하고(`check_raw_geometry()`), `DETID` 를 파일명 접미사와 대조한다 — 어긋나면 **경고와 HISTORY** 만 남기고 변환은 계속한다. 카드가 없으면 대조 없이 지나간다. ③ pair 동일이어야 할 22장을 두 파일 사이에서 대조한다(`check_raw_pair()`, 경고·HISTORY). ④ `CHMAP_*` 를 AmpID Map v1.1 과 대조해 `CHMAPOK` 에 남긴다(11.2).  파일 구조 쪽 하드 실패(`BITPIX` ≠ 16 · `NAXIS1`/`NAXIS2` ≠ 19200/9400 · `END` 없음)는 종전 그대로다.

## 6. 레거시에 있으나 converter 가 읽지 않던 카드 (v2.2.0 기준 22장)

**레거시 raw 가 싣던 카드인데 converter(v2.2.0 ~ v2.4.0)가 값을 꺼내지 않았다.** 폐지된 것도 아니다(그건 8장). 이유는 대체로 셋이다 — **converter 가 자기 상수를 쓰거나**, **신규 규격이 더 정확한 다른 이름으로 나눴거나**, **raw 쪽 기록으로만 남기기로 한 것**이다.

> ⭐ **converter v2.5.0 은 이 표의 12장을 읽는다** — `PIXSCALE`·`PIXSIZE` 는 **대조에만**(MEF 값은 여전히 자기 상수, 어긋나면 경고·HISTORY) · `DATASRC`·`LEDFLASH`·`ICSBUILD`·`ENS1`–`ENS7` 은 **MEF PRIMARY 로 옮긴다**.  남은 10장(`SIMPLE` `NAXIS` `PRESCANX` `NPHLINES` `HEMODE` `FILENAME` `DSTEL` `CHOP` `CHSET` `CHPROC`)은 여전히 읽지 않고, 3.1 의 `ORIGIN` 이 v2.5.0 에서 이 부류에 든다(MEF 상수 `'KASI'`) — v2.5.0 기준 11장(1장 둘째 표).  행마다 ⭐ 로 적었다.

| raw 키워드 | Raw Legacy | Raw Archon | 용도 / 레거시 실측값 / Archon 계획 | converter 는 어떻게 하나 |
| --- | :---: | :---: | --- | --- |
| `SIMPLE` | O | O | FITS 표준 필수 카드 | converter 가 **자기가 새로 만든다** (`card("SIMPLE", True)`). raw 값을 볼 이유가 없다 |
| `NAXIS` | O | O | 축 수 | 〃. MEF PRIMARY 는 영상이 없어 `0`, amp extension 은 `2` 다 |
| `PRESCANX` → **`PRESCNX` 로 변경** | O | O (`PRESCNX`/`PRESCNY` 로 변경하여 계승 — v1.13, 확인 요망 10 종결) | amp 당 수평 prescan 열 수 — 레거시 실측 `27`, 신규 `0`(prescan 없음). **`OVRSCNX`/`OVRSCNY` 를 정하고 나서 자리수를 맞춰 개칭했다**(운영자, 2026-08-22) — 그대로 계승이 아니라 **키워드 변경 계승**이다: 레거시 27 과 신규 0 의 동명이값도 이름 분리로 해소된다 | converter 가 자기 상수 **`0`** 을 쓴다(`PRESCAN_X`). 신규 구조에는 prescan 이 없다. ⭐ v2.5.0 은 raw 의 새 이름 `PRESCNX`·`PRESCNY` 를 `0` 과 대조한다 — 레거시 이름 `PRESCANX` 는 여전히 읽지 않는다 |
| `PIXSCALE` | O | O | 픽셀 스케일 [arcsec/px] — 레거시 실측 `0.400` | converter 가 자기 상수 **`0.395`** 를 쓴다 — 소스 주석이 *"measured vs Gaia DR3 (was 0.400 nominal)"* 라고 밝힌 **실측 갱신값**이다. ⭐ v2.5.0 은 raw `PIXSCALE` 을 이 상수와 **대조한다**(허용 1e-6 — 어긋나면 경고·HISTORY). MEF 값은 여전히 상수다 |
| `PIXSIZE` | O | O | 픽셀 크기 [micron] — 레거시 실측 `10.0` | converter 가 자기 상수 `10.0` 을 쓴다. 값은 같다. ⭐ v2.5.0 은 `PIXSCALE` 과 같이 대조한다 |
| `NPHLINES` | O | **X** | preheat line 수 — 레거시 계승(구판 v1.2 5.13절). ADC/비디오단을<br>안정시키려 독출 전에 버리는 dummy line. 값의 정본은<br>`ACFFILE`이 가리키는 timing script 다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `DATASRC` | O | O | **`ARCHON_SCIENCE` / `ARCHON_GUIDE` / `SIM`** — 레거시 계승(구판 v1.2 5.13절)<br>+ 값 체계 확장(v1.8, 추후 확장 대비). 레거시는 ADC/CTC 보정 경로<br>구분이었고 Archon 에서는 **컨트롤러·HW 셋업 요약**으로 쓴다.<br>**시뮬 프레임이 실측으로 오인되는 것을 막는 유일한 카드**라는<br>성격은 그대로다 | ⭐ **v2.5.0 이 MEF PRIMARY `DATASRC` 로 옮긴다**(없으면 `'UNKNOWN'`). v2.4.0 까지는 읽지 않아 raw 아카이브 기록으로만 남았다 |
| `HEMODE` | O | **X** | **`SCIENCE` / `GUIDE`** — 레거시 계승(구판 v1.2 5.13절)이었으나<br>**v1.8 에서 삭제 판정**: `DATASRC`(`ARCHON_GUIDE`) 및<br>`CTRLxID` 와 중복이다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `LEDFLASH` | O | O | 점검용 LED 프로젝터 점등 시간 — **정수형 [milliseconds]**<br>(운영자 확정 2026-08-22, 확인 요망 4 종결). `0`이면 점등 안 함.<br>**레거시 계승(구판 v1.2 5.13절)** — 램프로 만든 실험실 flat 을 하늘<br>자료로 오인하지 않게 하는 카드다. ⚠️ **단위 변경**: D-013 계승<br>조건은 "레거시와 같은 초 유지"였으나, 정수형을 유지하면서<br>250 ms 같은 sub-second 값의 잘림을 막으려 **ms 로 변경**했다.<br>같은 이름에 1000배 다른 단위이므로 **카드 comment 가<br>`[milliseconds]` 를 명시**한다 — 계산 소비자는 없다.<br>`ics_sim` 반영 완료(ms÷1000 제거) | ⭐ **v2.5.0 이 MEF PRIMARY `LEDFLASH` 로 옮긴다** — 실수로 바꿔 싣고(comment `[ms]`, Keywords v1.1 도 [ms]) 없으면 **`0.0`** 이다. ⚠️ `0.0` 은 *"점등 안 함"* 으로 읽히는 그럴듯한 값이다. v2.4.0 까지는 읽지 않았다 |
| `FILENAME` | O | O | 자료 취득 시스템이 붙인 파일명 | converter 가 **MEF 출력 파일명으로 새로 만든다**(`out_path.name`). raw 의 `FILENAME` 은 raw 쪽 식별자로 남는다 |
| `ICSBUILD` | O | O | **취득 프로그램의 빌드 식별자** — 레거시 계승(구판 v1.2 5.13절).<br>형식은 **`v<버전>:<빌드일시(UTC)Z>`**,<br>예 `'v1.2.3:2026-08-21T18:09Z'` — 프로그램명 제거<br>(운영자 확정 2026-08-22, 확인 요망 5 종결). 작성 프로그램<br>식별은 `DATASRC` 가 담당한다. 끝의 `Z` 는 의도적(시각 카드가<br>아니라 떼어 읽는 식별자). `ics_sim` 반영 완료 | ⭐ **v2.5.0 이 MEF PRIMARY `ICSBUILD` 로 옮긴다**(없으면 `'UNKNOWN'`). v2.4.0 까지는 읽지 않았다 |
| `DSTEL` → **`DSTELALT` 로 변경** | O | O (`DSTELALT` 로 변경하여 적용 — v1.10) | 돔이 쓰는 망원경 고도 [deg] | **`DSTELALT` 로 개칭됐다** (D-013). converter 는 `DSTELALT` 만 읽고 fallback 이 없어 **AUX 가 보내는 `DSTEL` 을 ICS 가 옮겨 실어야 한다** |
| `CHOP` | O | **X** | chiller 블록 미도입 — 초안에서 삭제 (2026-08-21) | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `CHSET` | O | **X** | chiller 블록 미도입 — 초안에서 삭제 (2026-08-21) | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `CHPROC` | O | **X** | chiller 블록 미도입 — 초안에서 삭제 (2026-08-21) | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `ENS1` | O | O | AUX 중계값을 그대로 싣는다 | ⭐ **v2.5.0 이 MEF PRIMARY 로 옮긴다**(문자열 그대로, 없으면 `""`). v2.4.0 까지는 읽지 않았다 |
| `ENS2` | O | O | AUX 중계값을 그대로 싣는다 | 〃 |
| `ENS3` | O | O | AUX 중계값을 그대로 싣는다 | 〃 |
| `ENS4` | O | O | AUX 중계값을 그대로 싣는다 | 〃 |
| `ENS5` | O | O | AUX 중계값을 그대로 싣는다 | 〃 |
| `ENS6` | O | O | AUX 중계값을 그대로 싣는다 | 〃 |
| `ENS7` | O | O | AUX 중계값을 그대로 싣는다 | 〃 |

> ⚠️ **`NAMPS` · `OVERSCNX` · `PRESCANX` 는 이름이 같고 값이 다르다.** 레거시는 `8` · `32` · `27` 이었고 converter 는 `64` · `48` · `0` 을 쓴다. 같은 이름을 물려주면 **어느 쪽 값인지 읽는 쪽이 알 수 없다** — 8장 `OVERSCNY` 와 같은 부류의 위험이다.

> `PIXSCALE` 은 값이 갱신된 사례다. 레거시 `0.400`(공칭) → converter `0.395`, 소스 주석이 *"measured vs Gaia DR3"* 라고 근거를 남겼다.

> v1.9: Chiller 는 시스템에서 제거되어 CH* 카드 전체 미도입이 재확인됐다(운영자) — 초안 v0.3.6 재잔존은 **v1.11 에서 재삭제 검증 완료**(확인 요망 1 종결. 재잔존 원인은 백업 재편 중 구판 파일 교체로 확인).

## 7. Archon ICS 도입 후보·확정 카드 (카드 68장 · 표 60행)

**레거시 raw 에는 없고 규격 v1.2 · `ics_sim` · 확정 초안이 새로 들인 카드다.** converter v2.2.0 ~ v2.4.0 은 이 카드들을 읽지 않아 **MEF 로 가지 않았다.** 용도는 (1) converter 교차검증 선언, (2) pair 식별, (3) 아카이브 기록 세 가지다.

> ⭐ **converter v2.5.0 은 도입(`O`) 33장 가운데 `CAMVER` 를 뺀 32장을 읽는다** — **MEF 로 옮기는 것** 18장(`RDMODE` · `EXPID` · `FPAID` · `TCSTIME` · `HKUDATE` · 히터 넷 · `DMPTEMP` `WALLBRD` `HEBOX` · `Cn_*` 6장 — `Cn_*` 는 문자열 그대로 두면서 `VOLTINFO`/`TELEMETRY` 로도 해석한다) · **대조에만 쓰는 것** 10장(geometry 여덟 · `NAMPDET` · `NAMPRAW` — 5장 ⭐ 상자) · **amp 정체를 유도하는 것** `CHMAP_*` 4장(C-11 — `CHMAP_*` 행).  `CAMVER` 는 MEF 에서 converter 상수 `'CEU-v2.1'` 이라 raw 를 읽지 않는다.  `X` 카드는 raw 에 없으니 읽을 것이 없다.

> **`도입 여부` 열은 운영자가 채운다** — `O` = 도입 확정 · `X` = 도입 안 함 · 빈칸 = **아직 안 정함**. `Raw Archon` 열(2장)과 같은 성격이라 생성기 안에 표로 들고 있다.
>
> **v1.7 에서 바뀐 것**: 확정 초안(`__reference/Detector_and_Amp_Info_cards_v1.0.txt` · 헤더 초안)이 들인 **신규 14장을 추가**하고(`AMPNAX1/2` `IMAGEX/Y` `PRESCNX/Y` `OVRSCNX/Y` `CHMAP_*` `FPAID` `ORIGNAME` — 전부 `O`), 기존 후보의 도입 여부를 검토 결과대로 판정했다. 파생 가능해진 카드(`NXTILE` `CCDCOLS` `CCDROWS`)와 대체된 카드(`AMPMAP`), 규격 조항으로 이관하는 카드(`ROWORDR`)는 `X` 다.
>
> **v1.8 에서 바뀐 것**: HK 재구성 신설 3장(`DMPTEMP` `WALLBRD` `HEBOX`)과 `TCSTIME` 을 추가하고(전부 `O`), `CCDTEMP1`/`CCDTEMP2` 를 **제외 확정**(`X` — 평균 파생 폐기, 3.7절), `ACFFILE`·`CTR_CFG` 항목을 **`CTRL1CFG`/`CTRL2CFG` 확정**(3.3절)으로 종결했다.
>
> **v1.17 에서 바뀐 것**: raw spec v1.10 의 **HK 카드 5장 신설**을 반영했다 — `HKUDATE`(시각) 와 듀어 히터 넷 `HTREN`·`HTRSET`·`HTROUT`·`HTRFORCE`, 전부 `O`. **카드 63→68장, 표 55→60행.** 출처 어휘에 **`ICG heater`** 를 신설해 HK 공급 계통이 **둘 → 셋**이 됐다.
>
> **v1.9 에서 바뀐 것**: 빈칸 26행을 전부 `O`/`X` 로 판정해 **`도입 여부` 열이 완결됐다** — 문서 전체의 잔여 미정은 3.7 의 `CHKIMG` · `CHKIMG_C` 뿐이다. `READMODE`→`RDMODE` 개명 도입, `BCKTEMP`→`Cn_TEMP`/`Cn_VOLT`/`Cn_CURR` 변경·확장(+5), `CAMVER` 신설(+1) — 카드 57→63장, 표 54→55행.

> **"후보" 라고 부르는 이유**: 레거시 카드는 **2017 raw 실측**(`KMTNk.20170209.044131` — 같은 틀을 쓴 2021 combination 산출물 `KMTNc.20210503.030331` 이 곁에 있다)으로 확인된 설계지만, 이 표의 카드는 판정 전까지 **제안**이었다(이름·구성 검토 ACT-011).  도입 여부는 v1.9 에 완결됐고 카드 규범은 현행 raw spec 이 정한다 — 장 이름의 "후보" 는 그 출신을 남긴 낱말이다.

| 도입 후보 카드 | 도입 여부 | 용도 / 설명 | 유의사항 |
| --- | :---: | --- | --- |
| `ACFFILE` · `CTR_CFG` | **X** | 적용된 Archon 설정 파일 | **v1.8: `CTRL1CFG`/`CTRL2CFG`(3.3절)로 확정** — 컨트롤러별<br>색인형으로 가면서 이름 단일화 미결도 함께 종결됐다 |
| `READMODE` → **`RDMODE` 로 변경** | **O** | 컨트롤러 ACF/Setting 에 따른 readout mode 를<br>user-friendly 하게 제공 (값 예: `'NORMAL'` — 초안 v0.3.6) | 값 충돌(`'FAST'` vs `'64AMP'`)은 **이름 분리로 종결** (v1.9) —<br>raw `RDMODE`(독출 모드) / MEF `READMODE`(`'64AMP'`, converter 상수).<br>⭐ **값은 INI(`[controllers] rdmode`) 전용 · 정의가 없으면 `'NC'` ·<br>ACF 파일명에서 유도하지 않는다**(규격 5.0절 · 5.5절 — 결측 `'NC'` 는 운영자 확정 2026-09-24,<br>종전 `'UNKNOWN'`(2026-08-29 확정 · 규격 v1.12~v1.13)을 5.0절 결측 낱말로 통일했다).<br>converter v2.5.0 은 raw 값을 MEF `RDMODE` 로 그대로 옮긴다 — raw `'NC'` 는 `'NC'` 로 가고,<br>기본값 `'UNKNOWN'` 은 카드가 **없을** 때만 들어간다(`primary_cards()`).<br>⚠️ v1.13 까지의 규칙으로 찍은 raw(와 아직 그 규칙인 현행 브랜치 코드의 raw)는 결측이 `'UNKNOWN'` 이다 |
| `NAMPDET` | **O** | **chip(검출기) 하나당 amplifier 수** = `16`.<br>`AMPPCD` 를 대신한다 | comment 는 레거시 `NAMPS` 문구를 잇는다 —<br>*Number of amplifiers in the detector*. 확정 초안 반영.<br>⭐ v2.5.0 이 `16` 과 대조한다(MEF 는 여전히 `AMPPCD` `16` · `NAMPS` `64`) |
| `AMPMAP` | **X** | `EXPLICIT`이면 아래 표가 유효. `DEFAULT`면 converter의<br>추정식을 쓴다는 선언 | **v1.7: `CHMAP_*` 4장으로 대체** — 선언 카드 자체가 불필요해졌다 |
| `AMPNAX1` | **O** | **amp 타일의 X 크기** = `1200` (prescan+image+overscan) | `NAXIS1/AMPNAX1 = 16` 으로 타일 수 파생. MEF `RAWXTILE` 과 값 동일, 이름 상이 — ⭐ v2.5.0 이 `1200` 과 대조 |
| `AMPNAX2` | **O** | **amp 타일의 Y 크기** = `4700` = `NAXIS2/NEND` (타일 규약) | `AMPNAX2−IMAGEY = 84` 가 중앙 overscan 의 amp 몫 — **물리 분배는 OI-4**. ⭐ v2.5.0 이 `NAXIS2/2 = 4700` 과 대조 |
| ~~`BCKTEMP`~~ → **`Cn_TEMP` `Cn_VOLT` `Cn_CURR`**<br>로 변경·확장 | **O** (변경·확장) | Archon unit monitoring (Archon telemetry). Sci: n=1,2 · Gui: n=1.<br>Temp 는 Backplane 이후 모듈 번호 순서, Volt/Curr 는<br>P2V5·P5V·P6V·N6V·P17V·N17V·P35V 순서 —<br>**파이프(`\|`)로 구분한 나열**(자리=항목, 결측 자리는 `NC`) —<br>raw spec **v1.6**(2026-08-26) 에서 공백 하나를 파이프로 바꿨다 | Sci 모듈 순서(10자리): Backplane, `Mod1:LVDS`, `Mod2:Driver`,<br>`Mod3:Driver`, `Mod4:LVXBias`, `Mod5:ADM`, `Mod8:ADM`, `Mod9:HVYBias`,<br>`Mod10:Driver`, `Mod11:Driver` / Gui 모듈 순서(8자리): Backplane,<br>`Mod3:Driver`, `Mod4:Driver`, `Mod5:AD`, `Mod6:AD`, `Mod7:HeaterX`,<br>`Mod9:HVXBias`, `Mod10:HeaterX` —<br>✅ **raw spec 5.6.1절에 명세로 수록 완료**(v1.5, 2026-08-25). 표기는 v1.5 에서 구 `Slot<n>` 을 **`Mod<n>`**(Module) 로 바꿨고 자리 순서 자체는 그대로다.<br>✅ **Gui 는 OI-19 종결 (raw spec v1.9)** — 자리 표의 정본은 **raw spec 10.4절**이다(guide ACF `MOD_PRESENT=0x37C` 와 `modtm_gui_*` 두 근거 일치). 구 기재 `Slot9 HVY Bias` 는 ACF 실측 `MOD9_TYPE=8` = **`HVXBias`** 의 오기였다(`HVYBias` 는 science 유닛의 모듈 형). 첫 guide 구동 때 `STATUS` 응답으로 재확인만 남는다.<br>⚠️ **Gui 는 전원 레일도 8자리**다 — 7레일 뒤에 guide 전용 `HEATER`(+28 V)가 붙고 `C1_VOLT` 는 소수 2자리다(raw spec 10.4절, 운영자 확정 2026-08-30) |
| `BUFNO` | **X** | 사용한 Archon frame buffer | 모니터링 불필요(버퍼를 번갈아 사용) |
| `CAMVER` | **O** | Camera electronics version — INI 설정, 값 `CEU-v2.1`. **HW·성능상 변경사항이 있을 때만 올린다** — 전자부 세대 판단의 참조점(운영자, 2026-08-22). 설정 상세 추적은 `CTRLxCFG` 몫. ⭐ **듀어 RTD 의 배치·귀속 변경도 범프 사유다**(운영자 확정 2026-08-27 — `ICG RTD` 계통 HK 카드의 채널 대응이 헤더에 안 실리고 `CTRLxCFG` 는 science ACF 만 가리켜서다. 후보였던 `ICGCFG` 카드 신설은 기각 — converter 에 새 카드가 생기지 않는다). 범프 사유 전량은 raw spec **5.2절 `CAMVER` 행**(4.3절은 포장 쪽 판별 신호) | v1.9 신설 (초안 v0.3.6). MEF `CAMVER` 는 converter 상수 `'CEU-v2.1'` — raw 값을 읽지 않는다(v2.5.0 도 같다) |
| `CCDCOLS` | **X** | chip 1개의 active column | **`IMAGEX × 8` 로 파생 — 카드 불요** (v1.7) |
| `CCDROWS` | **X** | chip 1개의 active row | **`IMAGEY × 2` 로 파생 — 카드 불요** (v1.7) |
| `CCDTEMP1` | **X** | `CHIP1` 온도 [degC] | **v1.8 제외 확정** — HK 재구성으로 평균 파생 폐기(3.7절) |
| `CCDTEMP2` | **X** | `CHIP2` 온도 [degC] | 〃 |
| `CHECKSUM` | **X** | FITS 표준 checksum | raw 카드로서 **미도입 확정**(운영자 2026-09-23 — 규격 OI-7 종결, 5.10절 폐지·미도입 목록) — MEF 에는 converter v2.5.0 이 모든 HDU 에 쓴다 |
| `CHIP1` | **X** | X 1–9600 절반의 chip | `DETID` 유지 확정(3.1)과 함께 **관련 키워드 검토 때 재론** |
| `CHIP2` | **X** | X 9601–19200 절반의 chip | 〃 |
| `CHIPS` | **X** | 이 파일에 담긴 chip (X 낮은 쪽부터) | 〃 |
| `CHMAP_LT` `CHMAP_LB`<br>`CHMAP_RT` `CHMAP_RB` | **O** | **CCD 출력 채널 맵 4장** — 사분면(좌/우 절반 × TOP/BOT 행)별<br>8토큰, raw X 오름차순. **토큰은 4자 `<chip><A\|D><nn>`**<br>(01–08=`A` · 09–16=`D`, raw spec v1.5 개정 — 구 3자 `M16` 대체).<br>예: `'MD16,MD15,…,MD09'` | `AMOD<nn>`/`ACHN<nn>` 색인형 65장을 대체.<br>✅ **converter v2.5.0 이 이 카드에서 amp 정체를 유도한다**(C-11 반영) —<br>`CTRUNIT` · `CCDPORT` · `CHANNAME` · `CHANNUM` · `IMGSEC` · `CHMAPSRC`,<br>`MODULE` = 포트(A→1 · B→2) · `CHANNEL` = 1–16, AmpID Map v1.1 과 대조해 `CHMAPOK`. 값 = **CCD 출력단**(Archon module/channel 은 다음 단).<br>**세부 내용, 앰프별 배치 및 방향은 raw spec 4.5절<br>(Amp 전수 표)을 참조한다.** |
| `CTRLERR` | **X** | `TELEMETRY.ERRORFLAG` | 별도 모니터링 하므로 미적용 |
| `CTRLSTAT` | **X** | `TELEMETRY.STATUS` | `Cn_TEMP`/`Cn_VOLT`/`Cn_CURR` 와 중복 |
| `CTRLTAG` | **X** | **이 파일이 pair의 어느 쪽인가** (`MK`/`NT`) | 아카이브 근거 — `FILENAME`(+`EXPID`)/`CTRLTAG` (D-012 문구 개정).<br>**v1.9 미도입 확정 — `DETID` 와 값 중복.** pair 식별은<br>`FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)로 충분 |
| `DATASUM` | **X** | FITS 표준 datasum | 미사용(raw 카드로서) — `CHECKSUM` 과 함께 **미도입 확정**(OI-7 종결). MEF 에는 converter v2.5.0 이 모든 HDU 에 쓴다 |
| `DMPTEMP` | **O** | DMP 온도 [degC] — HK 재구성 신설 (v1.8) | `ICG RTD measurement`. ⭐ v2.5.0 MEF pass-through |
| `EXECODE` | **X** | ICS relay 필드 |  |
| `FPAID` | **O** | **Focal Plane Assembly ID** (예: `'FPA#1'`) | 검출기 조립 정체는 FPA 단위 — FPA↔CCD 시리얼 대응표는 규격 부록 몫. ⭐ v2.5.0 MEF pass-through(없으면 `'UNKNOWN'`) |
| `FRAMENO` | **X** | controller frame counter | 진단용, MEF 목적지 없음 — `FILENAME`/`EXPID` 와 중복이므로 미적용 |
| `HEBOX` | **O** | HE box 내부 온도 [degC] — HK 재구성 신설 (v1.8) | `Radionode sensor`. ⭐ v2.5.0 MEF pass-through |
| `HKUDATE` | **O** | **guide 유닛 실측 HK 값들 중 가장 오래된 표본시각** — 초 단위 19자 `'2026-09-04T09:10:33'`(`Z` 없음, 시간계는 `TIMESYS`). 셈에 드는 것은 `ICG RTD` 7장 + `ICG heater` 넷이고 ⛔ **`Radionode` 3장(`HEBOX`·`FSATEMP`·`FSAHUM`)은 넣지 않는다**(raw spec 5.6절 · 운영자 확정 2026-09-08) — **이 카드는 그 세 장의 나이를 말하지 않는다.** sentinel `'NC'`. 자리는 블록 **맨 앞**(`DEWPRES` 앞) | 규격 v1.10 신설 (운영자 확정 2026-09-04). ⏳ `HKQDATE`(명령 수신 시각)는 **안 싣는다**. ⭐ 셈 규칙의 정본은 raw spec 5.6절. ⭐ v2.5.0 MEF pass-through |
| `HTREN` | **O** | 듀어 히터 사용 여부 — **`'ON'`/`'OFF'`** 낱말. sentinel `'NC'` | `ICG heater`(계통 신설). `RCONFIG` 되읽기 층. ⛔ 모르는 것을 `'OFF'` 로 적지 않는다. ⭐ v2.5.0 MEF pass-through(히터 넷 모두) |
| `HTRFORCE` | **O** | 강제 출력 모드 — **`'ON'`/`'OFF'`** 낱말. sentinel `'NC'` | `ICG heater`. `RCONFIG` 되읽기 층 |
| `HTROUT` | **O** | 히터 **출력 전압** `'3.512'` [V] — 부호 없음. sentinel `'NC'` | `ICG heater`. **`STATUS` 층**(`MOD10/HEATERAOUTPUT`, 되읽기가 아니다 — FW 1.0.1252 확인, 측정/명령값 여부 OI-28). ⚠️ guide `HEATER` 레일(`HEATER_V`, 공칭 +28 V)과 **다른 것**이다. ✅ **원천 배선 완료 (2026-09-05)** — ICG 의 HK 표본기가 주기마다 `STATUS` 스냅샷에서 `MOD10/HEATERAOUTPUT` 을 담는다 (설정 셋 `HTREN`·`HTRSET`·`HTRFORCE` 는 2026-09-09 에 같은 바퀴의 `RCONFIG` 되읽기로 배선됐다 — raw spec ~~OI-25~~ 종결). `'NC'` 는 `STATUS` 는 왔는데 그 키가 없을 때만이고 그때는 한 번 경고한다. 미구현은 이제 없고 남은 물음은 값의 뜻(raw spec OI-28)뿐이다 |
| `HTRSET` | **O** | 히터 **목표온도** `'-100.10'` [degC] — **부호 필수**. sentinel `'-999.99'` | `ICG heater`. `RCONFIG` 되읽기 층 |
| `IMAGEX` | **O** | amp 당 image(active) 열 수 = `1152` | MEF `AMPDATA` 와 값 동일, 이름 상이(11.4 ②) — ⭐ v2.5.0 이 `1152` 와 대조 |
| `IMAGEY` | **O** | amp 당 image(active) 행 수 = `4616` | MEF 에 같은 이름이 없다 — converter 상수 `ACTIVE_HALF_ROWS`(MEF `TOPROWS`/`BOTROWS` `4616`)가 대응(11.4 ②). ⭐ v2.5.0 이 `4616` 과 대조 |
| `MIDOSCB` | **X** | 중앙 overscan 중 BOT half에서 나온 row 수 | v1.9: 오류 사례 없음 — `OVRSCNY` 로 충분 (구 "OI-4 실측 후 도입") |
| `MIDOSCT` | **X** | 중앙 overscan 중 TOP half에서 나온 row 수 | 〃 |
| `NAMPRAW` | O | **이 파일에 담긴 amplifier 수** (chip 2 × amp 16) | ⭐ v2.5.0 이 `32` 와 대조(MEF 카드는 없다) |
| `NXTILE` | **X** | X 방향 amp tile 수 (chip 2 × strip 8) | **`NAXIS1 / AMPNAX1` 로 파생 — 카드 불요** (v1.7) |
| ~~`ORIGNAME`~~ → **`EXPID`** | **O** | **카운터가 이 노출에 처음 배정한 식별자** `<SITE>.<YYYYMMDD>.<NNNNNN>` — 모든 파일에 항상 기록.<br>**`DETID` 필드가 없어 pair 양쪽 동일** → 짝을 잇는 단일 키.<br>충돌 신호 = `FILENAME` 의 `DETID` 필드를 뗀 값 ≠ `EXPID` | `UNIQNAME`·`NAMECLSH`·`clash/` 격리를 대체(8.2절, **D-016 등재**).<br>**v1.6 에서 `ORIGNAME` → `EXPID` 개명·재정의** (운영자 확정 2026-08-26).<br>상세: 규격 2.3절 · D-016 · D-019.<br>⭐ converter v2.5.0 은 MEF PRIMARY `EXPID` 로 옮기고, pair 양쪽 값이 둘 다 있는데 다르면 **변환을 멈춘다** |
| `OSCNPATT` | **X** | strip 1–8의 overscan 위치 (R=오른쪽, L=왼쪽).<br>**근거는 converter의 `is_bias_right()`** —<br>`strip_id(amp)=((amp-1)%8)+1`,<br>`is_bias_right(amp)= 1≤amp≤4 or 9≤amp≤12` | converter 가 이 카드를 읽지 않아 **선언과 하드코딩이<br>갈라져도 변환 쪽에서 못 잡는다**(C-5/C-13 — v2.5.0 의 선언 대조도 카드가 없는 이 패턴은 대상 밖이다). 취득 SW 쪽 방어는<br>`test_geometry_vs_converter.py`. **v1.9 미도입 — 헤더가<br>복잡해지므로 세부내용은 raw FITS spec 에 수록**(포장 규범 조항 이관 전제) |
| `OVRSCNX` | **O** | amp 당 X overscan 열 수 = `48` — 좌우는 strip 에 따라 갈린다(규격 4.1절 `RRRRLLLL`) | 폐지된 `OVERSCNX`(레거시 32)와 **이름 분리** — 8.1절의 미정 해소. ⭐ v2.5.0 이 `48` 과 대조 |
| `OVRSCNY` | **O** | amp 당 Y overscan 행 수 = `84` — 자리는 **영상 중앙**이다(규격 4.2절) | 폐지된 `OVERSCNY` 와 **이름 분리**. 84/84 분배는 OI-4. ⭐ v2.5.0 이 `84`(= MEF `MIDOVSCY` 168 / 2)와 대조 |
| `PAIRFILE` | **X** | 짝의 이름. **`FILENAME` 과 같은 형태(확장자 없음)** | converter 는 CLI 로 두 경로를 받으므로 읽지 않는다 —<br>**아카이브 도구용**. pair 가 충돌 시 함께 증가하므로 **항상 실명**이다.<br>**v1.9 미도입 — 규약으로 예측 가능하므로 생략(운영자)** |
| `PRESCNX` | **O** | amp 당 X prescan 열 수 = `0` | 레거시 `PRESCANX` 의 **키워드 변경 계승**(운영자 확정 2026-08-22, 확인 요망 10 종결) —<br>`OVRSCNX`/`OVRSCNY` 확정 후 자리수를 맞춰 개칭. 동명이값(레거시 27 · 신규 0) 해소 겸.<br>합 불변식의 항: `AMPNAX1 = PRESCNX + IMAGEX + OVRSCNX`. 초안 v1.0 과 정합. ⭐ v2.5.0 이 `0` 과 대조 |
| `PRESCNY` | **O** | amp 당 Y prescan 행 수 = `0` | ⭐ v2.5.0 이 `0` 과 대조 |
| `RAWPROD` | **X** | 이 파일이 CEU Archon science raw임을 선언 | MEF 는 `DATAPROD` 를 따로 만든다. `CAMVER` 등 instrument<br>카드가 정보 제공 — 중복 배제 (v1.9) |
| `RAWVER` | **X** | **raw 규격/geometry 버전.** 4장이 바뀌면 올린다 | **미도입 확정 (v1.13, 확인 요망 11 종결)** — 규격/구성 버전은<br>**`CAMVER`(HW) · `CTRLxCFG`(FW/설정) · `DETID` · `CHMAP_*`** 조합으로<br>전부 파악되므로 별도 카드가 중복이다(운영자, 2026-08-22) |
| `RDDIRB` | **X** | **BOT amp의 물리적 독출 진행 방향** | **v1.9: 헤더 생략 — 세부는 raw FITS spec 에 수록** (구 OI-3 보류) |
| `RDDIRT` | **X** | **TOP amp의 물리적 독출 진행 방향.** MEF amp header<br>`READDIR`로 전달 | MEF amp `READDIR` 로 가야 하는데 converter<br>가 하드코딩(C-12). **v1.9: 헤더 생략 — 세부는 raw FITS spec 에<br>수록** (구 OI-3 보류) |
| `ROWORDR` | **X** | **4.2절 행 순서 규약. 잘못 쓰면 TOP half가 Y 반전된다** | **v1.7: 카드 대신 규격의 포장 규범 조항으로 이관** — "raw 는<br>검출기 공간 순서로 완전 정렬 저장"을 요구사항으로 선언한다.<br>flat/star 시험(OI-3)은 준수 검증이 된다. 고정 대상은 `RAWVER` 미도입<br>확정(확인 요망 11)에 따라 **`CAMVER` + `CTRLxCFG`** — 포장 변경은<br>HW·설정 변경에서만 오므로 그 둘의 범프가 판별 신호다 (v1.13) |
| `TCSLIMIT` &nbsp;&nbsp; | **X** | — | TCS 설정값 — raw 헤더 삽입 대상 아님 |
| `TCSTIME` | **O** | TCS 시각계 선언 (`'UTC'`) — `TIMESYS`(ICS)와 분리, 초안 v0.3.5 | 직전 초안(v0.3.4)의 `TCSTSYS` 에서 개명. ⭐ v2.5.0 MEF pass-through |
| `TELID` | **X** | ICS relay의 telescope ID | 전 시스템 고정값 — TCS/AUX relay 통신 규격에서만 필요 |
| `VMEA<n>` | **X** | `MEASURED` | 전압 텔레메트리는 `Cn_VOLT`/`Cn_CURR` 나열형으로 대체 (v1.9) |
| `VOLT<n>` | **X** | `VOLTNAME` | 〃 |
| `VOLTN` | **X** | — | 〃 |
| `VSET<n>` | **X** | `SETPOINT` | 〃 |
| `VSTA<n>` | **X** | — | 〃 |
| `VUNI<n>` | **X** | — | 〃 |
| `WALLBRD` | **O** | wallboard 온도 [degC] — HK 재구성 신설 (v1.8) | `ICG RTD measurement`. 초안 v0.3.4 의<br>`WALLBOAR`(단순 8자 절단형)에서 개명. ⭐ v2.5.0 MEF pass-through |

> **이름을 틀리면 무엇이 드러나나** (converter v2.5.0) — MEF 로 옮기는 18장은 3장 카드처럼 MEF 에 기본값(`'UNKNOWN'` · `""`)이 남는다.  대조에만 쓰는 10장은 **카드가 없으면 대조 없이 지나가므로** 이름을 틀려도 조용하다 — 값이 어긋날 때만 경고가 난다.  `CHMAP_*` 는 이름을 틀리면 amp 정체가 `UNKNOWN` 이 되고 `CHMAPOK=F` 로 드러난다.  나머지 36장(`CAMVER` 와 `X` 카드)은 converter 가 읽지 않아 흔적이 없다.  `OSCNPATT` · `ROWORDR` · `RDDIRT` · `RDDIRB` 처럼 **converter 하드코딩과 대조하라고 만든 선언**은 v1.7~v1.9 에 카드가 아니라 규격 조항으로 갔으므로 v2.5.0 의 대조(C-5 · C-13 반영) 대상 밖이다.

## 8. 폐지된 레거시 카드 (17장)

**신규 raw 는 이 카드들을 싣지 않는다.** D-013 이 레거시 123개를 하나씩 판정해 101개는 이미 대응물이 있었고, 대응물이 없던 22개를 **계승 5 · 개칭 1 · 폐지 16** 으로 갈랐다. 여기에 규격 카드 `UT` 하나가 함께 폐지됐다.

> `KBUILD` 처럼 **레거시 헤더에는 있는데 3장에도 6장에도 없는 카드**를 찾았다면 여기에 있다. 빠뜨린 것이 아니라 **폐지된 것**이다. (`DETID` 는 예외 — 폐지가 철회돼 3.1 에 있다.)
>
> **"대신 보는 것" 열은 현행 후계를 가리킨다** (v1.20 정정) — 구판이 적었던 `CTRLTAG` · `CHIPS` · `MIDOSCB`/`MIDOSCT` · `OSCNPATT` · `ACFFILE` · `TIMVER` · `BUFNO` · `CTRL1FW`/`CTRL2FW` 는 7장·3.3 에서 `X` 가 됐고, `TIMCONF` · `READTIME` 은 구판 규격 v1.2 5.5절의 raw 카드였으나 v1.3 재작성판에서 빠졌다 — 지금은 MEF 쪽에만 있다(PRIMARY `TIMCONF` 는 converter 상수 `'CEU_TIM_v1.0'`, `TELEMETRY.READTIME` 은 sentinel `-1.0`).

| 폐지 카드 | 폐지 근거 | 대신 보는 것 |
| --- | --- | --- |
| `DETID` — **철회, 3.1 로 계승** | 파일 1개 = CCD 1개 전제의 카드. 신규는 파일 1개에 chip 2개다 | (폐지 철회 — 3.1 계승, 값 `MK`/`NT` 로 재정의) |
| `OVERSCNY` — **구 이름 계승을 철회 (폐지 확정 재확인, 확인 요망 7 종결)** | ⚠️ **이름을 물려주면 자료가 깎인다.** 레거시는 Y overscan 이 `0`(없음)이었고 있었다면 **가장자리**를 뜻했다. 신규는 Y overscan 이 **영상 중앙**에 있다(4.2절). `OVERSCNY=168`을 본 도구가 "위쪽 168행 자르기"를 하면 active 픽셀을 지운다 | raw **`OVRSCNY`**(amp 당 `84`, 자리는 영상 중앙 — 규격 4.2절) · MEF **`MIDOVSCY`**(`168`, 위치가 이름에 들어 있다) |
| `READOUT` (`'ARLBRL'`) | 8-amp CCD 의 amp 조합 부호. 64-amp 구조를 표현할 수 없다 | raw `RDMODE` · `CHMAP_*` · raw spec 4.1절 overscan 좌우 패턴 `RRRRLLLL` / MEF `READMODE`(`'64AMP'`) · `READARCH`(`'8STRIPx2END'`) |
| `GAINDL` | **레거시 4년치에서 값이 비어 있던 카드다**(`GAINDL / comment` 형태). 계승할 관례가 없다 | `CTRL1CFG`/`CTRL2CFG`(적용 ACF — timing script 는 그 안에 있다) |
| `PIXITIME` | 〃 (같은 이유, 같은 자리) | 〃 |
| `DMAWAIT` | master IC 가 slave 의 DMA 설정을 기다리는 시간. Archon 에는 master/slave DMA 가 없다 | (해당 없음) |
| `ICROLE` | `'MASTER'`/`'SLAVE'`. Archon 과학 컨트롤러 2대는 대등하고, 셔터는 ICS 가 AUX 로 직접 구동한다 | `CTRLID` · `CTRL<n>ID` |
| `CTCSOURC` | CTC(전하전송 보정) 계수의 출처. Archon 은 컨트롤러에서 CTC 를 하지 않는다 | (해당 없음) |
| `CTCFILE` | 〃 | `CTRL1CFG`/`CTRL2CFG`(적용 ACF)가 설정 파일 자리다 |
| `KBUILD` | CCD 별 IC 의 소프트웨어 빌드. CCD 별 IC 가 없어졌다. **다만 "모든 파일이 전체 전자부 상태를 안다"는 취지는 계승했다** — 구판 v1.2 5.5.0절 `CTRL<n>*`(현행 규격 5.5절) | `CTRL1CFG`/`CTRL2CFG`(3.3절 — 구 `CTRL1FW`/`CTRL2FW` 가 여기로 귀속됐다). 호스트 취득 SW 빌드는 `ICSBUILD`(뜻이 다르다) |
| `MBUILD` | 〃 | 〃 |
| `TBUILD` | 〃 | 〃 |
| `NBUILD` | 〃 | 〃 |
| `GBUILD` | 〃. guide 파일은 `DATASRC` = `ARCHON_GUIDE` 로 구분한다(`HEMODE` 는 v1.8 삭제) — guide raw 는 규격 9·10장 소관이고 이 원장(science pair · converter)의 범위 밖이다 | guide raw 의 `ICGBUILD`(규격 10.3절) · 컨트롤러 설정은 guide 의 `CTRL1CFG` |
| `RTD12` | **값도 주석도 없는 빈 카드**가 4년치 아카이브에 남아 있었다. RTD 채널 12 자리로 보이나 채워진 적이 없다 | (없음). 규격 5.0절 sentinel 규칙이 이 사례를 막는다 — 값이 없는 카드는 sentinel 을 싣고, 카드를 비우는 것은 **sentinel 을 금지한 열 장**(`EXPTIME` · `DATE-OBS` · geometry 여덟 — 규격 5.0절)뿐이다 |
| `INPUTFMT` | *"Format of file from which image was read"*. 프레임이 컨트롤러에서 TCP 로 직접 오므로 "읽어 들인 파일" 이 없다 | (해당 없음) |
| `UT` | **`DATE-OBS` 와 완전한 중복.** 레거시가 둘 다 실은 것은 `UT` 에 `TSHOPEN`(백분초)을 붙여 정밀도를 보태려던 것인데, `DATE-OBS` 를 밀리초까지 쓰기로 하면서 이유가 없어졌다 (2026-08-13 확정) | `DATE-OBS` (밀리초 포함). MEF `UT` 는 converter v2.5.0 이 `DATE-OBS` 를 그대로 싣는다 — 구 조립식(`DATE-OBS` 날짜부 + `TSHOPEN`)도 `TSHOPEN` 이 없으면 `DATE-OBS` 전체로 채웠으므로, v1.8 의 `TSHOPEN` 폐지는 MEF `UT` 를 비운 적이 없다 (3.2절) |

> ⚠️ **`OVERSCNY` 가 이 목록에서 가장 위험한 축이다.** 이름을 그대로 물려주면 **자료가 깎인다** — 레거시는 Y overscan 이 가장자리였고 신규는 영상 중앙이라(규격 4.2절), `OVERSCNY=168` 을 본 도구가 "위쪽 168행 자르기" 를 하면 active 픽셀을 지운다. 이름이 같아서 조용히 틀리는 부류다. **`OVRSCNY` 로 개명해 잘림을 방지했다(운영자 확정, v1.10)** — 이 개명과 위험 사유를 **raw FITS spec(V1) 에 명시하고, MEF ICD·converter 검토 문서(MEF Impacts)에도 수록한다.**

> ⚠️ **`DETID` 는 폐지가 철회됐다.** 파일 1개 = CCD 1개 전제가 무너진 것은 그대로지만, **값을 `MK`/`NT`(어느 컨트롤러의 파일인가)로 재정의**해 3.1 로 되살렸다. 폐지 근거는 옛 정의에 대한 것이므로 기록으로 남겨 둔다 — 같은 이름을 다른 뜻으로 쓰는 셈이라 **`NAMPS` · `OVERSCNX` 와 같은 부류의 위험**을 안는다(6장). ⭐ converter v2.5.0 은 raw `DETID` 를 **교차검증에만** 읽고(파일명 접미사 · pair 상이), MEF `DETID` 는 상수 `'MKNT'` 를 새로 쓴다 — raw(`MK`/`NT`)와 MEF(`MKNT`)가 같은 이름에 다른 값이다(13장).

계승 5 · 개칭 1 은 D-013 폐지 대상이 아니어서 6장에 있다 — `DATASRC` `HEMODE` `LEDFLASH` `ICSBUILD` `NPHLINES` 와 `DSTEL`(→ **`DSTELALT`**). 그중 `HEMODE` · `NPHLINES` 는 v1.8 판정으로 신규 raw 가 싣지 않는다(6장 `X`).

### 8.1 이 검토에서 새로 폐지한 카드 (3장)

위 표는 **D-013 이 내린 판정**이고, 아래는 **이 검토에서 새로 내린 것**이다. 둘 다 근거가 같다 — *이름이 범위를 드러내지 않으면 조용히 틀린다.*

| 폐지 카드 | 폐지 근거 | 대신 보는 것 |
| --- | --- | --- |
| `NAMPS` | 레거시는 `8`(그 CCD 하나), 신규는 `64`(카메라 전체) — **이름은 같은데 세는 범위가 달라졌다.** 레거시를 아는 도구가 amp 수로 쓰면 조용히 8배 틀린다. `OVERSCNY` 를 폐지한 것과 같은 부류다 | **`NAMPDET`** (`16`, chip 당). 카메라 전체는 `NAMPDET × NCCD` 로 파생되므로 카드가 필요 없다 |
| `OVERSCNX` — **구 이름 계승을 철회 (폐지 확정 재확인, 확인 요망 7 종결)** | 레거시 실측 `32`, converter 상수 `48` — **이름은 같은데 값이 다르다.** 게다가 `X` 만 있고 중앙 Y overscan 을 담을 자리가 없어, 양방향 overscan 을 한 이름으로 표현하지 못한다(11.3 · 12.3) | **`OVRSCNX`/`OVRSCNY` 두 장 — v1.7 에서 확정** (X = amp 당 48 · Y = amp 당 84 — Y 자리는 영상 중앙, 규격 4.2절). 같은 이유로 `PRESCANX`(레거시 27 ↔ 신규 0)도 **`PRESCNX`** 로 개칭하고 `PRESCNY` 를 짝으로 신설했다(7장) |
| `AMPPCD` | *amplifiers per CCD* 의 축약인데 `AMPCCD` 오타로 읽힌다. 값 `16` 은 `NAMPDET` 과 **같은 것을 센다** | **`NAMPDET`** — `NAMPRAW` 와 이름 형태가 같아(`N`+`AMP`+범위) 한 계열로 읽힌다 |

**남는 것은 두 카드다.**

```text
NAMPDET =                   16 / Number of amplifiers in the detector
NAMPRAW =                   32 / Number of amplifiers in the raw FITS file
```

- **범위가 전치사구로 갈린다** — `in the detector` · `in the raw FITS file`. 레거시 `NAMPS` 의 comment 가 *Number of amplifiers in the detector* 였으므로 `NAMPDET` 은 **뜻을 그대로 잇고 이름만 바꾼 것**이다. 값이 `8`→`16` 인 것은 검출기가 바뀐 결과이지 뜻이 바뀐 것이 아니다.
- **이름 형태가 같아** (`N` + `AMP` + 범위) 헤더를 훑을 때 한 계열로 읽힌다. `AMPPCD` 는 이 규칙 밖이었다.
- `NAMPRAW = NAMPDET × 2` (파일당 chip 2개) — 구판 규격 v1.2 의 불변식 `NAMPRAW = NXTILE × NEND` 와 같은 값을 다른 길로 확인한다(`NXTILE` 은 v1.7 에 `NAXIS1 / AMPNAX1` 파생으로 돌려 미도입 — 7장. 현행 규격에는 이 식이 없다).
- **카메라 전체(`64`)는 카드로 싣지 않는다** — `NAMPDET × NCCD` 로 파생되고, converter 는 이미 자기 상수 `64` 를 쓴다.

> ✅ **comment 는 취득 SW 가 싣는다.**  헤더 조립이 **카드 템플릿**(keyword · 형 · 패딩 폭 · comment)을 순서 그대로 얹는 경로로 재편됐고, 폭이 모자라는 카드는 raw spec 5.0절대로 comment 를 먼저 줄인다.  위 두 줄은 목표 형태가 아니라 **견본 정본의 실제 레코드**다.  ⚠️ `main` 에 합류 대기 중인 구 `ics_sim` 사본은 아직 dict 경로라 main 트리에서 돌린 출력에는 comment 가 없다.  (구 경고 — *"comment 를 넣으려면 취득 SW 를 먼저 고쳐야 한다 … 위 두 줄은 목표 형태"* — 는 템플릿 경로로 해소돼 걷었다. 원문은 `archive/` 의 구판(v1.19 까지)에 있다.)

> **딸려오는 변경**: 규격 5.4(카드 정의) · 5.13(폐지 목록) · 불변식(`NAMPS = NCCD × AMPPCD` → `NAMPRAW = NAMPDET × 2`) · `ics_sim/ics_sim/rawhdr.py` 의 상수와 `tests/test_raw_header.py` 의 단언 두 줄. **converter 와 MEF 는 손대지 않는다** — raw 를 읽지 않기 때문이다.  (v1.4 당시 기록 — 절 번호는 구판 v1.2 것이다. ⭐ converter v2.5.0 은 `NAMPDET`·`NAMPRAW` 를 대조에 읽지만 MEF 카드 `NAMPS`·`AMPPCD` 는 그대로 상수다.)

### 8.2 v1.7 에서 새로 폐지한 카드 (2장)

파일명 충돌 처리를 `clash/` 격리에서 **번호 증가**로 바꾸면서 정체성 카드가 재편됐다 — **D-016 으로 등재 완료(2026-08-22)**, 상세는 규격 2.3절 · D-016 · D-019(구 상세였던 통합 문서 v0.5 Part 2 는 `archive/` 로 갔고 v0.6 에서 요약으로 줄었다 — 현행 요약은 [통합 문서 v1.2](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.2.md) Part 2).

| 폐지 카드 | 폐지 근거 | 대신 보는 것 |
| --- | --- | --- |
| `UNIQNAME` (레거시 계승분) | "불변 정본 키"라는 뜻이 이탈했다 — 번호 증가 방식이 `FILENAME` 의 유일성을 구조로 보장하므로 잉여가 되고, 뜻이 두 번 흐른 이름에 세 번째 뜻을 얹지 않는다(D-013 원칙). ✅ converter v2.4.0 까지는 이 카드를 읽어 MEF `UNIQNAME` 으로 옮겼으나(폐지 후 빈 문자열이 될 자리 — C-항목), **v2.5.0 이 MEF `UNIQNAME` 카드를 폐지해 닫았다** | **`FILENAME`**(실명 · 아카이브 유일 키) + **`EXPID`**(v1.6 — 구 `ORIGNAME`. 카운터가 처음 배정한 노출 식별자, 항상 기록 · pair 동일) |
| `NAMECLSH` (규격 v1.2 신설분) | 충돌 신호가 카드 존재에서 **값 비교**로 이동했다 | `FILENAME` 의 `DETID` 필드를 뗀 값 ≠ `EXPID` 가 곧 충돌 신호 (v1.6 — 구 `ORIGNAME`). `EXPID` 결측은 헤더 결함으로 분류 |

`clash/` 격리 디렉토리와 `.clash<UTC>` 접미사, "PAIRFILE 은 명목 이름으로 열화될 수 있다" 조항도 함께 폐지된다. ✅ 브랜치 `ics_sim` 의 RETIRED(부활 금지) 목록(`UNIQNAME`·`NAMECLSH` 포함)이 **science 산출 헤더(MK·NT)** 에서 되살아나지 않는지 시험이 지킨다.  견본 MK/NT 는 바이트 대사 시험(`test_raw_draft`)으로 템플릿과 묶여 간접으로 지켜진다.  ⚠️ **guide(G)에는 폐지 카드 대사가 없다** — 템플릿 폐쇄는 산출 = 견본만 보장하므로 견본과 템플릿에 함께 되살린 카드는 걸리지 않는다.  `main` 의 구 `ics_sim` 사본(RETIRED 에 `UNIQNAME`·`NAMECLSH` 가 없다)은 합류 전이다.

> ⚠️ **`EXPID` 는 구판 규격 v1.2 에서 폐지됐다가(2026-08-12) v1.6(2026-08-26)에서 `ORIGNAME` 을 대체하며 형식을 바꿔(`<SITE>` 접두) 되살아난 이름이다** — 구판 문서의 `EXPID` 와 섞어 읽지 않는다(현행 정의는 7장 `EXPID` 행).  되살린 근거와 당시 삭제 근거의 대조는 규격 12장 v1.6 행에 있다.

## 9. 레거시 123개 전량 귀속

레거시 raw 실측본의 keyword 가 **하나도 빠짐없이** 어딘가에 귀속되는지 확인한 표다. 이 문서를 읽다가 *"이 카드는 어디 갔지"* 가 나오면 여기서 찾는다.

| 어디로 갔나 | 개수 (v2.2.0 추출 · 장 배치) | 개수 (⭐ v2.5.0) | 어느 장 |
| --- | ---: | ---: | --- |
| converter 가 읽는다 | **78** | **89** | 3장 · 4장 (v2.5.0: `ORIGIN` · `UNIQNAME` 이 빠지고 6장 12장 · `DETID` 가 든다) |
| 구조 카드 — `hval()` 로 읽는다 | **5** | **5** | 5장 |
| converter 가 읽지 않는다 | **22** | **11** | 6장 (v2.5.0: 6장 나머지 10 + `ORIGIN`) |
| 폐지됐다 | **18** | **18** | 8장 16(D-013 폐지 16) + 8.1절 2(`NAMPS` · `OVERSCNX`) — v2.5.0: 8장 15(`DETID` 빠짐) + 8.1절 2 + 8.2절 `UNIQNAME` |
| **합계** | **123** | **123** | |

폐지 18 의 셈은 1장 첫 표 아래 상자와 같다 — 8장 표의 `UT` 와 8.1절 표의 `AMPPCD` 는 레거시 밖이라 들지 않는다.

레거시에 없던 카드는 이 표 밖이다 — converter 가 읽는 26개는 3장에 `X` 로, 도입 후보·확정 **68장**은 7장에 있다 (7장 머리말과 같은 수 — 표 60행 가운데 `Cn_TEMP`/`Cn_VOLT`/`Cn_CURR` 행이 6장, `CHMAP_*` 행이 4장이라 58 + 6 + 4 = 68). ⭐ v2.5.0 은 레거시 밖 카드를 60장 읽는다 — 3장 `X` 26 + `CTRL1CFG`/`CTRL2CFG` + 7장 32.

> 이 귀속은 **converter 동작 기준**이다 — Raw Archon 축(무엇을 싣나)과 섞지 말 것. 그래서 converter 가 바뀌면 수가 바뀐다: v2.4.0 까지는 Raw Archon 축에서 폐지된 `UNIQNAME`(8.2절)이 converter 가 읽으므로 "읽는다 78" 에 있었고 되살아난 `DETID` 가 converter 가 안 읽으므로 "폐지 18" 에 있었는데, v2.5.0 에서는 둘이 자리를 바꿨다.  장 배치(3~8장)는 v2.2.0 추출 그대로 두었다.

## 10. subframe · ROI · window 독출 — 지금 규격에 자리가 없다

**전면 독출만 전제하고 있다.** 규격은 8장 미결 표에 번호 없는 행 하나로 *"이 규격은 전면 독출 전용"* 이라 선언해 두었을 뿐(이 장을 제기로 인용한다) 부분 독출을 다루는 OI 도 원점 카드도 없다 — binning 이 OI-5 로 열려 있을 뿐이다. 레거시도 사정이 비슷했다: 카메라 IC 에는 `ROI` 명령이 실제로 구현돼 있었지만 **ICS 명령 테이블에는 아예 없어** 운영에서 쓰이지 않았고, ROI 산출물은 조각을 모자이크로 재구성한 **별도 combination 파일**로 만들었다(`KMTNc.20210503.030331`, `1616 x 1616`).

### 10.1 부분 독출에 필요한 것 — 크기가 아니라 원점이다

`NAXIS1`/`NAXIS2` 는 **몇 픽셀인지**만 말한다. 부분 독출에서 정작 필요한 것은 **그 창이 검출기의 어디였나** 이고, 그것이 없으면 자료의 위치를 복원할 수 없다. 광학 CCD 천문학이 쓰는 관례는 FITS 표준 자체가 아니라 **IRAF/NOAO mosaic 관례**인데, 사실상 표준으로 굳었다.

| 카드 | 뜻 | 부분 독출에서 |
| --- | --- | --- |
| **`DETSEC`** | 이 픽셀들이 **검출기(모자이크) 좌표**의 어디인가 | **가장 중요.** 창의 원점과 범위가 여기 들어간다 |
| **`CCDSEC`** | **CCD 좌표**의 어디인가 | CCD 가 여럿이면 필요하다 |
| **`DATASEC`** | 파일 안에서 **실제 자료 영역** | 창 안에서 overscan 을 뺀 부분 |
| `BIASSEC` · `TRIMSEC` | overscan · 잘라낼 영역 | 창을 잡으면 overscan 의 유무와 위치가 달라진다 |
| `AMPSEC` | amp 좌표계 | |
| **`CCDSUM`** | binning, `'1 1'` 형식 | 부분 독출과 거의 항상 함께 온다 (OI-5) |
| `DETSIZE` · `CCDSIZE` | 창이 아니라 **원래 전체 크기** | 창의 분모 |
| `LTV1` `LTV2` · `LTM1_1` `LTM2_2` | 논리→물리 좌표 변환 | IRAF 계열 파이프라인이 trim·window·binning 이력을 이것으로 추적한다 |

표기는 1-기반 포함 구간이다 — `DETSEC = '[2049:3072,1025:2048]'`. **최소 조합은 `DETSEC` + `DATASEC` + `CCDSUM`** 이고, 이 셋이면 창의 위치·자료 범위·binning 이 복원된다.

> ⚠️ **가장 흔한 사고는 `CRPIX` 다.** 창을 잡으면 `CRPIX1`/`CRPIX2` 가 그만큼 옮겨가야 하는데, 이것을 빠뜨리면 WCS 가 창 오프셋만큼 통째로 어긋난다. **헤더는 멀쩡해 보이고 값도 유효해서 오류가 나지 않는다** — 이 문서가 내내 경계한 *조용히 틀리는* 부류의 대표다. `CRVAL` 과 `CD` 행렬은 순수 평행이동이면 바뀌지 않는다.

계열별로 이름이 갈리기도 한다 — ESO 는 `HIERARCH ESO DET WIN1 STRX/STRY/NX/NY`, SBIG·ASCOM 계열은 `XORGSUBF`/`YORGSUBF` 를 쓴다. **Archon 은 정해진 관례가 없다** — 창은 timing script(ACF)의 line/pixel 파라미터로 정해지고 헤더 카드는 각 관측소가 붙인다. 그래서 **이름을 우리가 정해야 한다.**

### 10.2 우리 구조에서 걸리는 것

**MEF 쪽 기계는 이미 있다.** ICD 의 `AMPINFO` 가 `DETSEC` · `CCDSEC` · `DATASEC` · `BIASSEC` · `TRIMSEC` · `AMPSEC` 을 모두 갖고 converter 가 실제로 만든다. 창을 지원한다는 것은 **그 값들이 노출마다 달라진다**는 뜻이다. 막히는 곳은 두 군데다.

| 무엇 | 왜 막히나 |
| --- | --- |
| **raw 가 창을 말할 방법이 없다** | 레거시 raw 는 section 계열을 하나도 쓰지 않고 `OVERSCNX` · `PRESCANX` · `NAMPS` · `READOUT` 같은 **파라미터 방식**이었다(6장). 전면 독출만 하면 그것으로 충분했다. 창을 넣으려면 **원점을 실을 카드가 새로 필요하다** |
| **converter 가 geometry 를 상수로 갖고 있다** | `OVERSCAN_X=48` · `PRESCAN_X=0` · amp `1200 x 4616` 이 전부 소스 상수다(6장). **창을 읽어도 무시하고 상수로 계산하므로 `DETSEC` 이 조용히 틀린다.** OI-5 는 binning 에 대해 *"`NAXIS` 가 바뀌면 converter 가 즉시 실패한다"* 고 적었는데, **부분 독출은 그보다 나쁘다 — 실패하지 않고 틀린 좌표를 만들 수 있다**.  ⭐ converter v2.5.0: 프레임 크기가 `19200 x 9400` 이 아니면 shape 검사로 멈추고(v2.4.0 도 같다), raw 가 창을 geometry 카드로 선언하면 대조 경고와 HISTORY 가 남는다 — 그래도 **창을 계산에 쓰는 경로는 없다** |

### 10.3 raw 에 필요한 최소 카드 (제안)

| 카드 | 값 | 왜 |
| --- | --- | --- |
| `ROIMODE` 같은 선언 | `FULL` / `WINDOW` | **창 모드인지가 먼저 드러나야 한다.** 없으면 소비자가 전면 독출로 가정한다 — 5.0절 sentinel 규약과 같은 취지다 |
| `DETSEC` | `[x1:x2,y1:y2]` | 검출기 상의 창 위치. 관례 그대로 쓴다 |
| `CCDSUM` | `'1 1'` | binning. OI-5 와 묶인다 |
| amp 별 분해 | 창이 amp 경계를 가로지를 때 | **파일 1개에 chip 2 · amp 32** 이므로 창 하나가 여러 amp 에 걸치면 amp 마다 `DETSEC` 이 달라지고 아예 읽히지 않는 amp 도 생긴다 |

마지막 줄이 가장 까다롭다. 레거시가 ROI 산출물을 **모자이크로 재구성한 별도 파일**로 만든 것도 아마 이 복잡함 때문일 것이다 — 64-amp 구조에서는 그 부담이 더 크다.

> **이 절은 규격이 아니라 제기다.** 부분 독출을 쓸 계획이 있는지부터 정해야 하고, 쓴다면 **미결 항목(OI-*)으로 세워** binning(OI-5) 과 함께 다루는 것이 맞다. 지금은 규격이 *"전면 독출 전용"* 한 줄만 두고 OI 번호를 세우지 않아서, **쓸지 말지는 아무도 결정하지 않은 채로 남아 있다.**

## 11. converter 가 만들어 쓰는 카드

**converter 는 geometry 를 raw 선언이 아니라 소스 상수와 amp 번호에서 계산해** L0 MEF 에 내보낸다. 이 장은 그 값들이다 — raw 가 다른 값을 실어도 converter 는 아래를 쓴다.  ⭐ v2.2.0 ~ v2.4.0 은 raw 의 geometry 선언을 하나도 읽지 않았고, **v2.5.0 은 읽되 대조에만 쓴다**(`check_raw_geometry()` — 어긋나면 경고와 HISTORY, 카드가 없으면 대조 없이 지나감, 5장 ⭐ 상자).

### 11.1 전역 상수와 대조 결과로 만드는 카드 (PRIMARY)

| 카드 | 값 | 뜻 |
| --- | --- | --- |
| `RAWXTILE` | `1200` | amp tile 폭 (X) |
| `AMPDATA` | `1152` | 그중 active 열 |
| `OVERSCNX` | `48` | amp 당 X overscan |
| `PRESCANX` | `0` | X prescan (없음) |
| `MIDOVSCY` | `168` | **중앙** Y overscan 행 수 |
| `NSTRIP` · `NEND` | `8` · `2` | chip 당 strip · strip 당 독출단 |
| `CHIPLIST` | `M,K,N,T` | 공식 chip 순서 |
| `RAWGROUP` | `MKNT` | pair 묶음 규약 |
| `DETSIZE` | `[1:18892,1:19397]` | 모자이크 전체 크기 |
| `COLGAP` · `ROWGAP` | `460` · `933` | chip 간 간격 |
| `CHIPFLP` | `None` | OSU 식 chip 반전 **안 씀** (D-003) |
| `STRIPDIR` | `+X` | strip 번호 증가 방향 |
| `TOPROWS` · `BOTROWS` | `4616` · `4616` | 반쪽별 active 행 수 (`ACTIVE_HALF_ROWS` — amp `NAXIS2` 도 이 값) |
| `PIXSCALE` · `PIXSIZE` | `0.395` · `10.0` | 픽셀 스케일 [arcsec/px] · 크기 [micron] — raw 에도 같은 이름이 있다(11.4 ①). ⭐ v2.5.0 은 raw 선언과 대조한다 |
| `CAMVER` | `'CEU-v2.1'` | 전자부 세대 — raw 에도 같은 이름이 있으나 읽지 않는다(11.4 ①) |
| `DETID` | `'MKNT'` | ⭐ **v2.5.0 신설** — 이 MEF 가 묶은 raw 쌍. raw `DETID`(`MK`/`NT`)와 **같은 이름에 다른 값**이다(11.4 ①) |
| `ORIGIN` | `'KASI'` | ⭐ **v2.5.0 부터 상수** — 파이프라인 산출물의 생성처(3.1) |
| `CHMAPOK` · `AMPIDMAP` | `T`/`F` · `'Detector_Ch_to_AmpID_Map_v1.1'` | ⭐ **v2.5.0 신설** — raw `CHMAP_*` 를 내장 AmpID Map 과 대조한 결과와 그 판 |
| `RAILREF` | `'RAWSPEC-v1.13-5.6.1'` | ⭐ **v2.5.0 신설** — `Cn_*` 자리 순서를 풀 때 쓴 규격 판(`VOLTINFO` 헤더에도). raw spec v1.14 · v1.15 · v1.16 의 5.6.1절 자리 순서(`Cn_TEMP` 모듈 10자리 · `Cn_VOLT`/`Cn_CURR` 레일 7자리 표)는 v1.13 과 같다 — 그래서 v1.13 을 가리키는 값이 v1.14 이후 raw 에도 맞다 |
| `WCSSKY` · `WCSOMIT` · `WCSSOLVE` (seed 가 있을 때 `WCSNAME` · `WCSAPPRX` · `BOREPIXX` · `BOREPIXY`) | `T`/`F` · … · `'TCS-SEED'` · `9418.0` · `9699.0` | ⭐ **v2.5.0 신설** — seed WCS 상태(D-023). 좌표 자체는 amp 에 있다(11.2 ⭐) |
| `AMPCHAR` | amp 특성표 파일명(40자로 자른다) | ⭐ **converter v2.3.0 신설 · 조건부** — `--ampchar` 로 amp 특성 CSV 를 준 실행에서만 나간다(`primary_cards()` 끝). 그 CSV 의 실측 `GAIN`/`RDNOISE`/`SATURAT`/`LINMAX` 를 amp 확장 헤더와 `AMPINFO` 에 박고, 어느 표를 썼는지를 이 카드가 남긴다. **raw 와 무관하다** — raw 는 gain·noise 를 싣지 않는다(카드 계층 규칙, 규격 5장) |

카드로 나가지 않는 내부 상수: `CCD_COLS=9216` · `CCD_ROWS=9232`(chip 원점 계산에만 쓴다).  ⚠️ 구판이 여기 함께 적었던 `ACTIVE_HALF_ROWS=4616` · `PIX_SIZE=10.0` · `PIX_SCALE=0.395` 는 **카드로 나간다**(`TOPROWS`/`BOTROWS` · `PIXSIZE` · `PIXSCALE` — 저장소의 가장 이른 판 v2.1.1 부터 카드였다. `PIXSCALE` 값은 v2.1.3 에 `0.400` → `0.395`. 구판이 v2.2.0 추출 때 놓친 것이다) — 위 표에 더했다.

> raw 에서 옮기거나 유도하는 PRIMARY 카드(3~7장 · `RA_DEG`/`DEC_DEG` · `AIRMASS` · `RADESYS` 등)와 `HISTORY`(geometry·pair·CHMAP 불일치 기록)는 이 표 밖이다.

### 11.2 amp 번호에서 계산하는 카드

`amp` 는 **chip 안 1~16**, `chip` ∈ `M` `K` `N` `T` 다.

| 카드 | 계산식 | M chip amp 1 / amp 13 |
| --- | --- | --- |
| `STRIPID` | `((amp-1) % 8) + 1` | `1` / `5` |
| `ENDID` | `amp<=8` 이면 `TOP`, 아니면 `BOT` | `TOP` / `BOT` |
| `EXTNAME` · `AMPNAME` | `{chip}{strip:02d}{T\|B}` | `M01T` / `M05B` |
| `AMPID` | `AMP_BASE[chip] + amp` (M0 K16 N32 T48) | `1` / `13` |
| `AMPSEQ` | `amp` (chip 안 번호) | `1` / `13` |
| `CHIPID` | `chip` | `M` / `M` |
| `CTRLID` | `M,K → 1` · `N,T → 2` | `1` / `1` |
| **`READDIR`** | `amp<=8` 이면 `-Y`, 아니면 `+Y` | `-Y` / `+Y` ⚠️ |
| `MODULE` | ⭐ v2.5.0: **`CHMAP_*` 에서** — 컨트롤러 포트 `CCDPORT`(파일 안 X 낮은 쪽 chip `M`·`N` = `A` → 1, 높은 쪽 `K`·`T` = `B` → 2), 토큰을 못 읽으면 `-1` (구 `1 + (amp-1)//8`) | `1` / `1` |
| `CHANNEL` | ⭐ v2.5.0: **`CHMAP_*` 토큰의 `nn`**(CCD 출력 채널 1–16), 못 읽으면 `-1` (구 `1 + (amp-1)%8`) | `16` / `5` (정상 `CHMAP` 기준) |
| `XTALKGROUP` (`AMPINFO` 열) | ⭐ v2.5.0: `'<CTRUNIT>-<CCDPORT>'` — 실제 컨트롤러 포트 묶음 (구 `C{1 if chip in MK else 2}M{1+(amp-1)//8}`) | `MK-A` / `MK-A` |

> ⚠️ 표시는 **소스가 스스로 잠정이라 밝힌 값**이다 — `READDIR` 은 comment 가 `placeholder` 다(OI-3 · C-12 — v2.5.0 도 식과 comment 가 그대로다).  구판이 `MODULE`·`CHANNEL` 에 달았던 ⚠️ 는 v2.5.0 이 두 값을 `CHMAP_*` 에서 유도하면서(C-11 반영) 걷었다.  **세부 내용, 앰프별 배치 및 방향은 raw spec 4.5절(Amp 전수 표)을 참조한다** — 그 표와 기계 정본 `Detector_Ch_to_AmpID_Map_v1.1.txt`(이 폴더 루트 — converter v2.5.0 이 내장 사본으로 대조해 `CHMAPOK` 에 남긴다)가 대응을 관리한다.
>
> ⭐ **v2.5.0 이 amp 헤더에 더한 것** — 채널 정체 `CTRUNIT`(`MK`/`NT`) · `CCDPORT` · `CHANNAME`(`CHMAP` 토큰) · `CHANNUM` · `IMGSEC`(e2v `A`/`D` + TOP/BOT) · `CHMAPSRC`(출처 카드) · IRAF 변환 `LTV`/`LTM`/`ATV`/`ATM`/`DTV`/`DTM` · `AIRMASS`(`SECZ` 가 수치일 때) · seed WCS(`CTYPE` `CUNIT` `CRVAL` `CRPIX` `CD` `RADECSYS`/`RADESYS` `EQUINOX` `WCSNAME` `WCSAPPRX` `WCSDIM` — 포인팅이 파싱되고 하늘을 본 프레임일 때만, 아니면 전부 빼고 `WCSOMIT=T`) · `WCSSOLVE` · `WCSSKY`.  채널 정체와 `CRPIX`·`LTV`·`DTV` 는 `AMPINFO` 끝에 덧붙은 12열에도 실린다.

### 11.3 구간 카드 — 좌우 overscan 이 갈린다

converter 는 `is_bias_right(amp) = (1<=amp<=4) or (9<=amp<=12)` 로 좌우를 가른다. **규격 4.1절의 overscan 좌우 패턴 `RRRRLLLL`(카드 후보였던 `OSCNPATT` 는 v1.9 미도입 — 7장)을 코드로 재현한 것이고 raw 에서 읽지는 않는다.**

| | overscan 오른쪽 (strip 1–4) | overscan 왼쪽 (strip 5–8) |
| --- | --- | --- |
| `DATASEC` | `[1:1152,1:4616]` | `[49:1200,1:4616]` |
| `BIASSEC` | `[1153:1200,1:4616]` | `[1:48,1:4616]` |
| `PRESEC` | `[1:0,1:4616]` (없음) | 〃 |
| `TRIMSEC` | `DATASEC` 과 같다 | 〃 |

raw 파일 안 위치(`RAWDATA`/`RAWBIAS`) — `tile0 = chipbase + (strip-1)×1200`, chipbase 는 `M`·`N`=0, `K`·`T`=9600:

| | 값 |
| --- | --- |
| X (overscan 오른쪽) | data `tile0+1 : tile0+1152` · bias `tile0+1153 : tile0+1200` |
| X (overscan 왼쪽) | bias `tile0+1 : tile0+48` · data `tile0+49 : tile0+1200` |
| **Y** | TOP(amp 1–8) `4785:9400` · BOT(amp 9–16) `1:4616` |

`CCDSEC` = X `(strip-1)×1152+1 : strip×1152`, Y 는 TOP `4617:9232` · BOT `1:4616`. `DETSEC` 은 여기에 chip 원점을 더한다 — `M (1, 10166)` · `K (9677, 10166)` · `N (1, 1)` · `T (9677, 1)`.

> **Y 사이 `4617:4784` 168행이 중앙 overscan 이고 어느 amp 구간에도 들어가지 않는다** — L0 MEF 에서 버려진다. amp extension 의 `MIDOVSCY` comment 가 *middle Y overscan rows ignored* 라고 밝힌다.

### 11.4 raw 와 이름이 겹치는 카드 · 이름만 갈린 대응

구판은 여기에 *"raw 도 싣고 converter 도 만드는 11개"* 로 `RAWXTILE` · `AMPDATA` · `PRESCANX` · `MIDOVSCY` · `NSTRIP` · `NEND` · `DETSIZE` · `COLGAP` · `ROWGAP` · `CHIPFLP` · `STRIPDIR` · `CTRLID`(실제로는 12개)를 적었는데, **이 이름들은 현행 raw 에 하나도 없다** — 넷(`RAWXTILE` · `AMPDATA` · `PRESCANX` · `MIDOVSCY`)은 현행 raw 에 다른 이름으로만 있고(② — `MIDOVSCY` 는 raw `OVRSCNY` 의 두 배), 나머지 여덟(`NSTRIP` · `NEND` · `DETSIZE` · `COLGAP` · `ROWGAP` · `CHIPFLP` · `STRIPDIR` · `CTRLID`)은 현행 raw 에 없는 MEF 쪽 이름이다.  구판 규격 v1.2 는 열두 장 모두를 raw 필수 카드(5.3~5.5절)로 두었으나 v1.3 재작성판부터 raw 밖이다(현행 규격 5.10절 — MEF 구조와 section·amp 식별은 raw 에 넣지 않는다).  실제 겹침은 아래 두 표다.

**① 같은 이름 — raw 도 싣고 MEF 에는 converter 가 스스로 만든다**

| 카드 | raw | MEF (converter v2.5.0) | 대조 |
| --- | --- | --- | --- |
| `CAMVER` | `'CEU-v2.1'` (ICS INI) | 상수 `'CEU-v2.1'` | **없다** — raw 를 읽지 않는다. raw 쪽만 범프되면 MEF 는 옛 값을 싣는다 |
| `PIXSCALE` · `PIXSIZE` | 선언 (ICS INI) | 상수 `0.395` · `10.0` | ⭐ v2.5.0 이 대조한다(허용 1e-6 — 어긋나면 경고·HISTORY) |
| `DETID` | `MK` / `NT` | ⭐ v2.5.0 상수 `'MKNT'`(이 MEF 가 묶은 쌍) | raw 값은 파일명 접미사 · pair 상이 여부만 대조한다. **같은 이름에 다른 값이 정상**이다 |
| `ORIGIN` | 생성 사이트 (`SSO`/`CTIO`/`SAAO`/`KASI`) | ⭐ v2.5.0 상수 `'KASI'`(파이프라인 산출물) | 없다 — 같은 이름에 다른 값이 정상이다(3.1) |
| `FILENAME` | raw 저장명 (확장자 없음) | MEF 출력 파일명 | **뜻이 다르다** — 대조 대상이 아니다 |

`SIMPLE` · `NAXIS` 같은 FITS 구조 카드는 어느 FITS 에나 있어 대조 대상으로 뜻이 없으므로 넣지 않았다.  `CCDXBIN`/`CCDYBIN` 은 같은 이름의 pass-through 인데, v2.5.0 은 `1` 과도 대조한다(binning 이 section 계산의 전제라서).

**② 이름만 갈린 대응 — ⭐ converter v2.5.0 이 이 대응으로 대조한다** (불일치 = 경고·HISTORY · 카드가 없으면 대조 없음)

| raw 선언 | converter 상수 (MEF 카드) | 값 |
| --- | --- | ---: |
| `AMPNAX1` | `RAW_XTILE` (MEF `RAWXTILE`) | `1200` |
| `AMPNAX2` | `RAW_NAXIS2 // 2` (MEF 카드 없음) | `4700` |
| `IMAGEX` | `AMP_DATA_COLS` (MEF `AMPDATA`) | `1152` |
| `IMAGEY` | `ACTIVE_HALF_ROWS` (MEF `TOPROWS` · `BOTROWS`) | `4616` |
| `PRESCNX` · `PRESCNY` | `PRESCAN_X` (MEF `PRESCANX`) · `0` (MEF 카드 없음) | `0` · `0` |
| `OVRSCNX` | `OVERSCAN_X` (MEF `OVERSCNX`) | `48` |
| `OVRSCNY` | `MIDDLE_OVERSCAN_Y // 2` (MEF `MIDOVSCY` = `168`) | `84` |
| `NAMPDET` · `NAMPRAW` | `16` · `32` (MEF 는 `AMPPCD` `16` · `NAMPS` `64` — 8.1절) | `16` · `32` |

> **`OVERSCNX` 는 raw 쪽 이름이 바뀌었다** — 8.1 절이 raw 이름을 **`OVRSCNX`** 로 바꿨고(v1.7 확정) converter 는 여전히 MEF 에 `OVERSCNX` 를 내보내므로 **raw 와 MEF 의 이름이 갈린다.** 위 ② 표 전체가 같은 부류다.  변경점 **C-5 · C-13** 은 이 대조를 붙이는 일이었고 **v2.5.0 이 반영했다** — 다만 **멈추지 않고 경고만 남긴다**(`-W error` 로 돌릴 때만 실패로 올라간다, 13장).  대응표 원자료: [통합 문서 v1.2](KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v1.2.md) §2.

## 12. raw FITS 를 직접 쓰는 사람에게

converter 를 거치지 않고 **raw pair 를 그대로 다루는 경우**를 위한 장이다. 11장이 *MEF 에 무엇이 들어가나* 라면, 여기는 *raw 만 가진 사람이 무엇을 알 수 있고 무엇을 직접 해야 하나* 다.

### 12.1 raw 헤더가 주는 것

geometry 를 재구성할 재료는 **raw 헤더 안에 다 있다** — 11.1 의 값 가운데 타일·구간 값은 raw 에 **다른 이름으로** 실리고(11.4 ② — 예: MEF `RAWXTILE` = raw `AMPNAX1`), `NSTRIP` · `NEND` · `DETSIZE` · `COLGAP` · `ROWGAP` · `CHIPFLP` · `STRIPDIR` 같은 모자이크 배치 상수는 raw 에 없다(MEF 쪽 상수 — 규격은 raw 파일 안 배치만 4장에서 정한다). 여기에 raw 에만 있는 배치 선언이 더해진다:

| 카드 | 무엇 |
| --- | --- |
| `AMPNAX1` · `AMPNAX2` | amp 타일 크기 (1200 × 4700). 타일 수는 `NAXIS1/AMPNAX1 = 16` 으로 파생 |
| `IMAGEX/Y` · `PRESCNX/Y` · `OVRSCNX/Y` | 타일 해부 — image 1152 × 4616 · prescan 0 · overscan 48(좌우 가변) / 84(중앙 쪽) |
| `OSCNPATT` | strip 별 overscan 좌우 (`RRRRLLLL`) (v1.9 미도입 — 세부는 규격 조항) |
| `NAMPDET` · `NAMPRAW` | chip 당 amp 수 (16) · 이 파일의 amp 수 (32) |
| `CHMAP_LT/LB/RT/RB` | CCD 출력 채널 맵 — 사분면별 8토큰(**4자 `<chip><A\|D><nn>`**, v1.5), raw X 오름차순 |
| `DETID` | 이 파일에 담긴 chip 쌍 (`MK`/`NT`). `CHIPS`·`CHIP1`·`CHIP2` 는 v1.9 미도입(7장) |
| `MIDOSCB` · `MIDOSCT` | 중앙 overscan 의 BOT/TOP 몫 (v1.9 미도입 — `OVRSCNY` 로 충분) |
| `RDDIRT` · `RDDIRB` | 독출 방향 (v1.9 미도입 — 세부는 raw FITS spec 수록). 행 순서(구 `ROWORDR`)는 규격 포장 규범 조항으로 이관 |
| `FILENAME` · `EXPID` | 실명(아카이브 유일 키) · 카운터 최초 배정 노출 식별자(**pair 동일**, v1.6 — 구 `ORIGNAME`). **pair 식별은 `FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)** — `CTRLTAG` · `PAIRFILE` 은 v1.9 미도입(`DETID` 와 값 중복 · 규약으로 예측 가능) |
| `RDMODE` · `CAMVER` · `Cn_TEMP`/`Cn_VOLT`/`Cn_CURR` | readout mode(값 예 `'NORMAL'`) · 카메라 전자부 버전(`'CEU-v2.1'`) · Archon unit 텔레메트리 나열(v1.9, 7장) |

### 12.2 raw 헤더에 **없는** 것 — 직접 계산해야 한다

11장의 카드 중 **23개는 MEF 전용**이라 raw 에 없다(v2.2.0 기준 — v2.5.0 이 더한 채널 정체 · IRAF 변환 · seed WCS 카드는 11.2 ⭐ 상자):

`STRIPID` `ENDID` `EXTNAME` `AMPNAME` `AMPID` `AMPSEQ` `CHIPID` `READDIR` `MODULE` `CHANNEL` `XTALKGROUP` `CHIPLIST` `RAWGROUP` `DATASEC` `BIASSEC` `PRESEC` `TRIMSEC` `CCDSEC` `DETSEC` `AMPSEC` `RAWFILE` `RAWDATA` `RAWBIAS`

**amp 하나를 raw 에서 꺼내는 절차**는 이렇다 (chip 안 amp 번호 `a` = 1~16). ⚠️ v1.9 부터 `OSCNPATT` 는 **카드가 아니다**(7장 `X`) — 아래 `OSCNPATT[strip-1]` 은 규격 4.1절이 조항으로 정한 strip 별 overscan 좌우 패턴(`RRRRLLLL`)을 뜻하는 기호다:

```text
strip  = ((a-1) % 8) + 1
end    = TOP if a <= 8 else BOT
chipbase = 0 (X 낮은 쪽 chip) 또는 9600 (높은 쪽)      <- DETID 의 첫/둘째 글자
tile0  = chipbase + (strip-1) * AMPNAX1

overscan 이 오른쪽인가?  OSCNPATT[strip-1] == 'R'   <- 규격 조항의 패턴(카드 아님)
  오른쪽:  data = tile0+1 .. tile0+IMAGEX
           bias = tile0+IMAGEX+1 .. tile0+AMPNAX1
  왼쪽:    bias = tile0+1 .. tile0+OVRSCNX
           data = tile0+OVRSCNX+1 .. tile0+AMPNAX1

Y:  TOP -> NAXIS2-IMAGEY+1 .. NAXIS2      (예: 4785:9400)
    BOT -> 1 .. IMAGEY
```

**중앙 `MIDOVSCY` 행은 이 두 구간 사이에 있고 어느 amp 것도 아니다.**

### 12.3 조심할 것

| | |
| --- | --- |
| **독출 방향을 믿지 말 것** | `RDDIRT`/`RDDIRB` 는 **미확정**(OI-3)이고 MEF `READDIR` 도 `placeholder` 다. 방향이 필요하면 flat/star 로 직접 확인해야 한다 |
| **배선** | raw 의 **`CHMAP_LT/LB/RT/RB`**(구 `AMOD`/`ACHN` 대체)가 실제 CCD 출력 채널을 싣는다 — ✅ converter v2.5.0 이 MEF `MODULE`/`CHANNEL`(과 `CHANNAME` 등)을 이 카드에서 채운다(C-11 반영, 11.2). v2.4.0 이하 L0 의 `MODULE`/`CHANNEL` 은 amp 번호 추정식이라 실배선과 다르다. **세부 내용, 앰프별 배치 및 방향은 raw spec 4.5절(Amp 전수 표)을 참조한다.** Archon module/channel 은 그 다음 단이다 |
| **중앙 overscan** | raw 에는 있고 **L0 MEF 에는 없다.** bias jump·전하 잔류 진단에 쓰려면 **raw 를 보관해야 한다** |
| **overscan 좌우 패턴(구 `OSCNPATT`)이 바뀌면 MEF 가 틀린다** | 패턴은 카드가 아니라 규격 조항(4.1절 `RRRRLLLL`)이고 converter 는 `is_bias_right()` 하드코딩을 쓰므로, 실제 배치가 바뀌면 **오류 없이 어긋난다** — v2.5.0 의 선언 대조에도 패턴은 없다 |
| **부분 독출** | 10장 참조. 규격은 *"전면 독출 전용"* 한 줄뿐이다 |

## 13. 종합

- **기본값이 거의 전부 `""` 나 `"UNKNOWN"` 이다.** 카드가 없어도 변환은 성공하고, **L0 MEF 에 빈 문자열이 조용히 들어간다.**
- **카드 값으로 변환이 멈추는 것은 둘이다** — `OBSERVAT`↔파일명 사이트 코드 불일치(**기본 출력 이름 경로에서만** — `-o` 없음 · 파일명 정규식 · `OBSERVAT` 네 값 안, 3.1절)와 **pair 양쪽 `EXPID` 불일치**(v2.5.0 — 둘 다 있고 다를 때). 파일 구조 쪽(`BITPIX` · 프레임 크기 · `END`)은 따로 멈춘다(5장).  ⭐ v2.5.0 은 멈추지 않는 이상에 **경고 층**을 두었다 — geometry 선언 불일치 · pair 동일 카드 불일치 · `CHMAP` 불일치(`CHMAPOK=F`) · 파일명 대체 규칙 · 포인팅 파싱 실패 · `Cn_*` 자리 수 불일치 · 카드 절단을 매 노출 `ConverterWarning` 으로 알리고, 그중 geometry · pair · `CHMAP` 불일치와 WCS 생략 사유는 PRIMARY `HISTORY` 와 곁 파일(`.hdu_verify.txt` · `.summary.txt`)에도 남긴다. `-W error` 로 돌리면 이 경고가 실패로 올라간다.  **카드가 없는 것은 여전히 전부 조용히 지나간다.**
- 조용히 **틀린 값**이 들어가는 쪽이 더 위험하다 — `DATE-OBS`(변환 시각) · `EXPTIME`/`DARKTIME`(0초) · 버전 문자열(그럴듯한 provenance) · `EQUINOX`(카드가 없거나 `'NC'`·비수치면 `2000.0` — raw 결측 `-999.0` 은 그대로 L1 까지 간다, 3.4절) · `LEDFLASH`(없으면 `0.0` = *"점등 안 함"*, 6장).  `RA`/`DEC`(그럴듯한 기본 좌표)는 v2.4.0 까지의 위험이다 — ✅ v2.5.0 은 기본 좌표를 걷고 WCS 를 통째로 뺀다(`WCSOMIT=T`, D-023).
- **HK 블록은 v1.8 에서 재구성됐다** — `CCDTEMP` 실측 대표 전환 · `DEWPRES` 문자열 `x.xxe-x` + sentinel `9.99e-9` · 신설 `DMPTEMP`/`WALLBRD`/`HEBOX` · 출처 3계통(3.7절). `DARKTIME` · `TSHOPEN` · `TSHSHUT` · `HEMODE` · `NPHLINES` · `CHSTAT` 는 신규 raw 가 싣지 않는다 — `TSHOPEN` 폐지는 MEF `UT` 를 비운 적이 없고(구 조립식도 `TSHOPEN` 이 없으면 `DATE-OBS` 전체로 채웠다), converter v2.5.0 은 `UT` = `DATE-OBS` · `DARKTIME` = `EXPTIME` 으로 정리했다(3.2절).
- **v1.10 으로 도입 판정이 완결됐고, v1.11~v1.13 으로 확인 요망 11건이 전량 종결됐으며, 충돌·정체성 결정이 D-016 으로 등재됐다** — 3장·6장 계획 열과 7장 도입 여부에 빈칸이 없고, 어긋남 목록도 비었다. **V1 재작성 착수 조건이 완성됐다.**
- **HK 블록의 형 논쟁은 v1.12 로 닫혔다** — 온도·습도 전 카드 문자열(레거시 계승), sentinel `'-999.99'` 단일값, `DEWPRES` 만 `9.99e-9`. ✅ `ics_sim` 의 실수형→문자열 전환은 **구현이 끝났다**(`rawhdr.format_temp()` · `rawcards.CARDS` 의 온도·습도 카드가 전부 `'S'`). ✅ **Radionode 원값 포맷도 2026-09-09 실측으로 닫혔다** — `get_lst` 가 소수 2자리를 주어 `FSATEMP`/`FSAHUM` 을 원값 그대로 2자리로 확정했다(3.5절 · raw spec ~~OI-16~~). **이 항목에 남은 일감은 없다.**
- **이름은 같은데 뜻이 달라진 카드 문제는 v1.7 개칭으로 닫혔다** — `OVERSCNX`→`OVRSCNX` · `PRESCANX`→`PRESCNX` · `OVERSCNY`→`OVRSCNY`(뜻 재정의 겸 개명) · `NAMPS` 폐지(8.1절). **`READMODE`** 의 값 충돌(`FAST` vs `64AMP`)은 v1.9 에서 raw `RDMODE` / MEF `READMODE` 로 **이름을 분리해 종결**했다(7장) — 그러나 **개칭 없이 뜻이 바뀐 카드가 남는다**: **`DETID`**(값 재정의 `MK`/`NT` — 3.1 comment 가 새 뜻을 명시. ⭐ MEF 에서는 converter v2.5.0 상수 `'MKNT'` 라 raw↔MEF 사이에서도 값이 갈린다) · **`OBSTYPE`**(프레임 종류 → 사용자 정의 관측 유형, 기본값 `SCIENCE`/`GUIDE` — raw spec v1.13 · v1.16.  v1.13 이 적은 *"계통 식별"* 은 v1.16 에서 기본값의 성질로 내려갔다 — 계통은 `DATASRC` · `DETID` 가 가린다) · **`DATASRC`**(레거시의 ADC/CTC 보정 경로 구분 → Archon 셋업 요약 `ARCHON_SCIENCE`/`ARCHON_GUIDE`/`SIM`, 원장 v1.8 판정) · **`LEDFLASH`**(단위 [s] → [ms], 운영자 확정 2026-08-22).  하류가 이 넷을 레거시 뜻으로 읽으면 틀린다.
- **`UNIQNAME` 은 폐지됐다**(8.2절) — 정체성은 `FILENAME`(유일 키) + `EXPID`(항상 기록, 불일치 = 충돌 신호. v1.6 — 구 `ORIGNAME`)가 담당한다. ✅ MEF `UNIQNAME` 은 converter v2.5.0 이 카드째 폐지해 C-항목이 닫혔다(v2.4.0 까지는 raw 를 옮겨 빈 문자열이 될 자리였다).
- **`OBSERVAT` 는 `CTIO`/`SSO`/`SAAO`/`KASI` 다**(**D-017** — 구 `TESTBED` 대체, converter v2.4.0 반영 · 3.1절). `ORIGIN` 은 "파일이 생성된 곳"(raw = 생성 사이트 — 관측소 raw 는 관측소 이름, KASI 실험실 raw 는 `KASI` · 파이프라인 산출물 = `KASI`) — MEF `ORIGIN` 상수화(경미 C-항목)는 ✅ converter v2.5.0 이 반영했다.
- `X` 중 **`XTALKVER` · `REFVER` · `CATVER` 셋은 결함이 아니다** — 규격 5.10절(구판 v1.2 5.12절)이 calibration DB 소관으로 정리했고 변경점 C-14 가 caldb 주입으로 바꾼다(v2.5.0 에도 미반영 — 여전히 MK 헤더에서 읽는다).
- **7장 68장 가운데 converter v2.5.0 이 읽는 것은 32장이다**(7장 머리) — MEF 로 옮기는 18장은 이름을 틀리면 MEF 에 기본값이 남고, `CHMAP_*` 는 `CHMAPOK=F` 로 드러나지만, 대조에만 쓰는 geometry 10장은 **카드가 없으면 대조 없이 지나간다**.  나머지 36장(`CAMVER` 와 `X` 카드)은 converter 가 읽지 않아 MEF 에 흔적이 없다.  (v2.4.0 까지는 68장 전부가 이 처지였다 — C-5/C-11/C-13 은 v2.5.0 이 반영했다.)
- **부분 독출(subframe · ROI · window)은 규격이 *"전면 독출 전용"* 한 줄로만 적고 OI 번호가 없다** — 10장. 지원한다면 `DETSEC` · `DATASEC` · `CCDSUM` 이 최소다.  converter 는 geometry 를 상수로 계산하므로 창을 반영하지 못한다 — 프레임 크기가 바뀌면 shape 검사에서 멈추고, 선언만 바뀌면 v2.5.0 이 경고를 낸다.
- **converter 는 geometry 를 자기 상수로 계산한다**(11장) — ⭐ v2.5.0 부터 raw 의 geometry 선언을 **대조에만** 읽는다(11.4 ② 의 이름 대응 · C-5·C-13 반영). 어긋나면 경고·HISTORY 만 남기고 변환은 계속하며, 카드가 없으면 대조 없이 지나간다.  같은 이름으로 겹치는 카드는 `CAMVER` · `PIXSCALE` · `PIXSIZE` · `DETID` · `ORIGIN` · `FILENAME` 이다(11.4 ①) — 값이 같아야 하는데 대조가 없는 것은 `CAMVER` 하나다(`ORIGIN` · `FILENAME` · `DETID` 는 raw 와 MEF 값이 다른 것이 정상이다).
- **raw 만 쓰는 사람에게는 amp 이름·번호·구간 23개가 없다** — 12.2 의 절차로 직접 계산해야 한다.
- 그룹별 주의사항은 **각 표 아래**에 붙였다.

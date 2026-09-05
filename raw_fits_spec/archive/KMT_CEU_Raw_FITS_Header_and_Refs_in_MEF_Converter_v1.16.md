# raw FITS 헤더 카드 — converter 가 읽는 것 · 읽지 않는 것 · 도입 후보 · 폐지된 것

**v1.16** · 개정 2026-08-30 · **환경 센서 장치명 `Tapaculo` → `Radionode` 개명** (raw spec v1.9 동반)
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
> 3. 흡수하지 않은 것과 그 근거: **MEF 표 HDU 컬럼 77장**(`AMPINFO` 40 · `TELEMETRY` 6 · `VOLTINFO` 5 · `XTALKINFO` 7 · 표 HDU 헤더 19)은 raw 에서 오는 값이 없어 **MEF 규격(ICD v4.1 §8 · Main_Keywords) 소관**이다. **MEF 인벤토리 236장 분석**은 converter 코드에서 기계 추출한 파생 수치이므로 규모만 0.3 에 남겼다. 구 `C-15`(`TELSTAT` 을 raw `CTRLSTAT` 에서 파생)는 **전제가 소멸**했다 — `CTRLSTAT` 이 v1.9 에서 `X` 확정이라 raw 가 싣지 않는다.

> **v1.13 에서 바뀐 것 — 잔여 확인 요망(6 · 7 · 8 · 10 · 11)이 전량 종결됐고, 충돌·정체성 결정이 D-016 으로 등재됐다** (운영자 확정 2026-08-22).
>
> 1. **재가 3건 종결(확인 요망 6 · 7 · 8)** — ⑥ `CTRL1ID` = `'KMTA-SCI-101'` 포맷 확정 + **Source 가 `ICS INI` 인 카드 전부를 ini 에서 수정 가능하게(운영자 지시, `ics_sim` 구현 반영)** · ⑦ `OVERSCNX`/`OVERSCNY` 의 "– 철회" = **구 이름 계승의 철회(폐지 확정 재확인)** — 8장·8.1 라벨을 대상이 드러나는 문구로 교체 · ⑧ `TIMVER`/`BIASVER`/`CLKVER` 는 `CTRLxCFG` 귀속(+ **`CAMVER` = HW·성능 세대 참조점** 명시), `XTALKVER`/`REFVER`/`CATVER` 는 caldb 소관 유지 — **pipeline setup 에서 HW 변화 없이 바뀔 수 있는 값이라 raw 미기재가 맞다**(운영자).
> 2. **확인 요망 10 종결 — PRESCN 은 키워드 변경 계승 (운영자 확정 2026-08-22)** — 레거시 `PRESCANX` 를 **`PRESCNX`/`PRESCNY` 로 개칭해 계승**한다(값 `0` — 신규 구조에 prescan 없음). `OVRSCNX`/`OVRSCNY` 를 정하고 나서 **자리수를 맞춰** 바꾼 것 — "그대로 계승"이 아니다. 6장 표기를 개칭 계승(DSTEL→DSTELALT 선례)으로, 7장 `PRESCNX` 를 `X`→`O` 로 정정 — 초안 v1.0·Detector 블록 정본과 3자 정합 회복.
> 3. **확인 요망 11 종결 — 규격 버전 카드는 미도입 (운영자 확정 2026-08-22)** — `RAWVER`/`RAWPROD` 부활 없이, 규격/구성 버전은 **`CAMVER`(HW) · `CTRLxCFG`(FW/설정) · `DETID` · `CHMAP_*`** 조합으로 전부 파악된다. 포장 규범 조항(V1)의 고정 대상도 `RAWVER` → **`CAMVER` + `CTRLxCFG`** 로 교체(7장 `ROWORDR` 행) — MEF 쪽 `GEOMVER` 동반 범프 문구도 같은 기준으로 갱신(통합 문서 §3).
> 4. **D-016 등재 (운영자 승인 2026-08-22)** — 충돌 처리(번호 증가·선검사·상한 100000회)와 정체성(`FILENAME` 유일 키 + `ORIGNAME` 충돌 신호, `UNIQNAME`·`NAMECLSH`·`clash/` 폐지)이 `DECISION_LOG.md` 에 **D-016 (Accepted)** 으로 등재됐다. D-010·D-012 의 "아카이브 근거 삼총사" 문구에 개정 표시, README 의 "색인 키는 UNIQNAME" 구 문단 교체. **이로써 V1 재작성 착수 조건(확인 요망 전량 + D-등재)이 완성됐다.**
> 5. **NT 초안 헤더 v1.0 파생 생성** — `KMTA.20260821.012345.NT.fits.header.v1.0.txt`: pair 상이 7장(`DETID` · `CHMAP_*` 4장 · `FILENAME`/`ORIGNAME` — `__reference` 정본 기준)만 다르고 나머지 136카드는 MK 동일(미확인분은 MK 값 유지).

> **v1.12 에서 바뀐 것 — HK 온도 카드의 형이 문자열로 확정됐다 (확인 요망 9 종결, 운영자 확정 2026-08-22).**
>
> 1. **온도·습도 카드는 레거시처럼 문자열 계승** — 레거시 실측이 이미 부호 포함 고정 포맷 문자열이었고(`CCDTEMP = '-103.16 '` · `AIR_IN = '+34.98  '`), converter 는 pass-through(`v("CCDTEMP","")`)라 raw 가 문자열이면 MEF 도 레거시 MEF 와 동일 형이다. 신규만 실수형이면 **아카이브에 같은 이름·다른 형이 섞여** 하류 파서가 두 갈래가 된다 — 초안 쪽이 맞았고, 고칠 대상은 `ics_sim`(실수형 → 문자열)이다.
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
> 3. **`BCKTEMP` → `Cn_TEMP` `Cn_VOLT` `Cn_CURR` 확장 도입**(Sci n=1,2 · Gui n=1 — 공백 구분 나열, 자리=항목) + **`CAMVER` 신설**(`'CEU-v2.1'`, ICS INI).
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
> 9. ~~HK 온도 카드의 형 — 초안은 문자열(`'-101.23'`, 부호 포함)인데 `ics_sim` 은 실수형으로 싣는 중이다~~ → **종결 (v1.12, 운영자 확정)**: **문자열 계승** — 레거시 실측도 부호 포함 문자열(`'-103.16 '`)이었고 converter 는 pass-through 라 아카이브 전체의 형이 통일된다. 측정불가 sentinel 은 온도·습도 전 카드 **`'-999.99'`** 단일값. 고칠 대상은 `ics_sim`(실수형 → 문자열).
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
> **ICD v4.1 에 `NAMPS` · `AMPPCD` 가 하나도 없다** — 0.3절이 말한 **침묵 구간**이라 우리가 정할 수 있고, converter 는 raw 를 읽지 않고 자기 상수를 쓰므로 **raw 에서 빼도 MEF 출력은 바뀌지 않는다.**

> **v1.3 에서 바뀐 것 — `Raw Archon` 열이 생겼고, subframe 절(10장)이 붙었다.** 지금까지 표는 *레거시가 그 카드를 실었나* 만 말했다. 신규 Archon raw 가 **그 카드를 실을 계획인가** 는 별개 사실인데 적을 자리가 없었다. `Raw Archon` 열이 그 자리다 — **기계 추출이 아니라 운영자가 채우는 계획 열**이고, 재생성해도 유지되도록 생성기 안에 표로 들고 있다.
>
> 함께 반영한 손질: **`DETID` 를 3.1 로 되살렸다**(값을 `MK`/`NT` 로 재정의, MEF 목적지는 `((TBD))`) · `ORIGIN` 의 기본값을 사이트별로 폈다 · 7장 `ACFFILE` 에 `CTR_CFG` 를 병기하고 `READMODE` 를 넣었다 · `CHIP1`/`CHIP2`/`CHIPS` 에 **`DETID` 로 변경** 을 달았다.

> **v1.2 에서 바뀐 것 — raw 카드의 기준을 레거시 실측 헤더로 명확히 했다.** v1.1 은 6장을 검토 문서 v0.7 의 4.H 절 그대로 실어 **레거시가 이미 싣던 카드와 아직 제안 단계인 신규 카드가 한 표에 섞여 있었다.** 지위가 다른 둘을 같은 표에 두면 *"이 카드는 확정된 것인가"* 를 표에서 읽어낼 수 없다.
>
> v1.2 는 그 53장을 **레거시 16 + 신규 37** 로 가르고, 앞엣것은 6장(레거시 24장)에 흡수하고 뒤엣것을 **7장 "Archon ICS 도입 후보"** 로 분리했다. 6장에는 **converter 가 왜 그 카드를 읽지 않는지**를 카드마다 적었다 — 자기 상수를 쓰는가, 다른 이름으로 나뉘었는가, 기록으로만 남기는가. 폐지 표는 7장에서 **8장**으로 밀렸다.

| 항목 | 값 |
| --- | --- |
| **raw 카드 기준** | `__reference/Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt` — **레거시 raw 실측 헤더 123개** |
| 대상 converter | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) |
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
| 8장 출처 | DECISION_LOG **D-013** (Accepted) — 표 본문은 raw pair 규격 5.13절 |

> **raw 카드의 기준은 레거시 raw 실측 헤더다.** 규격 v1.2 나 `ics_sim` 이 새로 들인 카드는 **아직 확정된 raw 가 아니라 제안**이므로 7장에 따로 모았다 — 레거시가 정착된 설계인 것과 지위가 다르다.

> **이 문서에서 "규격" 은 `KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`(raw pair 규격) 를 가리킨다.**
>
> ⚠️ 그 문서는 **((재작성중))** 이라 절 번호가 바뀔 수 있다. 아래에서 `규격 5.12` 처럼 절을 적은 곳은 **지금 그 내용이 어디 있는지 알려주는 포인터일 뿐 근거가 아니다.** 확정된 근거는 `../project_management/governance/DECISION_LOG.md` 의 **D-번호**다 — 이 문서가 기대는 것은 D-011(사이트 코드 파일명) · **D-013**(레거시 keyword 판정) · **D-016**(충돌 번호 증가 · `FILENAME`/`ORIGNAME` 정체성, 2026-08-22 등재) 이고 전부 Accepted 다.

## 0. 준거 순위와 판정 구간

**이 장은 "무엇을 근거로 판정했나" 를 정한다.** v1.14 신설 — 폐기된 검토 문서
(키워드맵 v0.7)에만 있던 판정 기준을 본문으로 들여왔다. 카드 하나를 `O`/`X` 로
놓을 때마다 되돌아오는 질문이라 문서 안에 있어야 한다.

### 0.1 무엇을 따르는가 — 순위

**대상은 `mef_converter/` 가 만드는 L0 MEF 다.** 그 헤더가 무엇을 담아야 하는지
정할 때 아래 순위를 따른다.

| 순위 | 무엇 | 지위 |
| --- | --- | --- |
| **1** | [`../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md`](../mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md) | **준거.** 어긋나면 아래가 틀린 것이다 |
| **2** | `../mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py` (v2.2.0) | **산출 주체.** 단 둘로 갈라 읽는다 — 0.2 |
| **3** | [`../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md`](../mef_fits_spec/KMT_CEU_MEF_FITS_Main_Keywords_Final_v1.0.md) | 참고. **PRIMARY keyword 층의 유일한 문서 근거**이지만 converter 파생물이다 |
| — | `KMT_CEU_L0AmpRaw_Work_Summary_v1.0.md` | **판정 근거로 쓰지 않는다** |
| — | `../ics_sim/` 의 현재 헤더 출력 | **판정 근거로 쓰지 않는다 — 근거가 순환한다** |
| **raw 기준선** | `__reference/Legacy raw fits header samples/KMTNk.20170209.044131.Rawheader.txt` — **레거시 raw 실측 123개** | **raw 쪽이 실제로 무엇을 싣는지의 기준선.** 계승 판정(D-013)의 근거이자 6장·9장의 출처 |

3위가 3위인 이유는 그 문서가 스스로 밝힌다 — 머리말이 *"기준 converter:
…v2_1.py v2.2.0"* 이다. **converter 를 따라 적은 파생물이므로 원본보다 위일 수
없다.**

> ⚠️ **3위·제외 문서를 근거로 쓰면 틀린다.** 둘 다 저장소에 그대로 있어서
> 겉보기로는 권위가 있으므로, 실측해 둔 상태를 남긴다.
>
> | 문서 | 확인된 상태 |
> | --- | --- |
> | `Main_Keywords v1.0` | ICD v4.1 개정 커밋에서 **8줄만 바뀌었다** — 머리말 기준 버전 2줄 + `MKFILE`/`NTFILE` 예시 파일명 2줄. 본문 대조 흔적이 없고 버전·작성일이 `v1.0`/`2026-06-22` 그대로라 **겉보기로는 미개정으로 읽힌다.** 본문에 `CREATOR`=`…_v2.1.1` · `PIPEVER`=`…-v2.1.1` 잔재가 남아 있다(converter 실제 값은 `v2.2.0`. `PRODVER`=`v2.1.1` 은 코드가 의도적으로 고정한 것이라 맞다) |
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
| **placeholder** | **ICD 미준수다.** §12 가 *"placeholder 는 raw 헤더가 실측 텔레메트리를 주지 않을 때"* 로 한정하고 **필요한 raw 텔레메트리 집합은 우리 규격 5장이 정의한다**고 역참조한다 → **C-12 · C-17 · C-18 의 근거** | 아카이브 기록으로만 남는다. MEF 목적지를 만들지 말지가 결정 사항 |
| **하드코딩** | 대조 대상이 있으므로 raw 선언과 맞추면 된다 | **근거가 순환한다** — 버전 문자열 계열이 이 칸이었고, 확인 요망 8 에서 `CTRLxCFG` 귀속 / caldb 소관으로 갈라 종결했다 |

### 0.3 ICD 가 침묵하는 구간이 판정의 과녁이다

**ICD v4.1 에는 PRIMARY keyword 목록이 없다.** 규정하는 것은 구조(§5) ·
amp section(§7) · `AMPINFO` 컬럼군(§8) · 표 역할(§9)이다. 그래서 두 구간을 갈라
읽어야 한다.

| 구간 | 판정 방법 |
| --- | --- |
| **ICD 가 규정한 구간** | converter 는 구현체다. 어긋나면 **converter 가 틀린 것**이고 판정이 자동으로 나온다 |
| **ICD 가 침묵하는 구간** | converter 는 정본이 아니라 **"현재 구현"** 이다. **이 구간이 곧 결정해야 할 곳**이다 |

**구간의 크기를 세어 두었다.** converter 가 `card()` 로 만드는 헤더 카드 이름은
**210개**(표 컬럼까지 포함하면 236개)이고, 그중 —

| ICD v4.1 에 | 개수 | 성격 |
| --- | ---: | --- |
| 등장한다 | **36** | **전량이 §7 amp section · §8 `AMPINFO` 컬럼 · geometry 계열**이다 — `DATASEC` `BIASSEC` `CCDSEC` `DETSEC` `AMPSEC` `TRIMSEC` `AMPID` `CHIPID` `STRIPID` `ENDID` `MODULE` `CHANNEL` `CTRLID` `READDIR` `CHIPFLP` `STRIPDIR` `GAIN` `RDNOISE` `LINMAX` `RAWFILE` `RAWDATA` `RAWBIAS` 등 |
| 없다 | **174** (83%) | **PRIMARY 의 관측 · provenance · 환경 keyword 전량** |

그러니 대립은 이름 충돌이 아니라 **준거의 공백**이다 — 3위 정의서에 정의가 없는
카드 이름은 `COMMENT`·`END`·`TFIELDS` **3개**(전부 FITS 구조 카드)뿐이고 반대
방향(문서에만 있고 코드가 안 만드는 것)도 없다. **converter 가 문서 밖 이름을
발명한 사례는 없다.**

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

**레거시 raw 실측 123개**가 어디로 갔는지:

| | 개수 | 어느 장 |
| --- | ---: | --- |
| converter 가 읽는다 | **78** | 3장 · 4장 |
| 구조 카드 — `hval()` 로 읽는다 | **5** | 5장 |
| **converter 가 읽지 않는다** | **22** | **6장** |
| 폐지됐다 | **18** | 8장 — D-013 이 17, 8.1절이 `NAMPS` |
| **합계** | **123** | |

여기에 **레거시에 없던 카드**가 두 갈래로 붙는다:

| | 개수 | 어느 장 |
| --- | ---: | --- |
| converter 가 읽는데 레거시에 없다 | **26** | 3장 (`X` 표시) |
| **Archon ICS 도입 후보·확정** — 규격 v1.2 / `ics_sim` / 확정 초안이 새로 들였고 converter 는 읽지 않는다 | **63** (후보 39 + v1.7 신규 14 + v1.8 신설 4 + v1.9 확장·신설 6 — `Cn_*` 6장이 `BCKTEMP` 1장을 대체(+5), `CAMVER` +1). 구 원장 "37" 은 v1.3 `READMODE` · v1.4 `NAMPDET` 추가분을 재산정하지 않은 값이라 v1.8 에서 실측 재산정했다 | **7장** |

> **전부 MK 헤더에서만 읽는다.** `convert()` 가 두 chip 에 `mk_hdr` 하나만 넘기므로 NT 헤더는 현재 반영되지 않는다 (변경점 C-17).

## 2. 표 보는 법

| 열 | 뜻 |
| --- | --- |
| **Raw Legacy** | `O` = 레거시 raw 실측본에 있다(계승) · **`X`** = 없다(신규 결정 대상) |
| **Raw Archon** | `O` = Archon raw 에 구현 예정 · **`X`** = 없다(폐지 또는 keyword 정의 변경) · 빈칸 = **아직 안 정했다** |
| **Use in MEF** | 그 값이 들어가는 MEF 카드. `+amp` 는 amp extension 에도 반복 기록된다는 표시. (구 `MEF 목적지`) |
| **Value (`*` default)** | 카드가 가질 값·통제 어휘. `*` 는 기본값 |
| **Source (`*` default)** | 값의 출처 — `ICS INI`(설정) · `ICS code`(취득 SW 산출) · `ICS generating`(취득 SW 생성) · `user input/selection` · `TCS relay` / `AUX relay`(TC 중계) · `Archon`(컨트롤러) · `ICG RTD measurement`(Archon 쪽 RTD·게이지 실측, v1.8) · `standalone RTD readout unit`(별도 RTD 판독 장치, v1.8) · `Radionode sensor`(환경 센서, v1.8) · `ICS calculation`/`ICS detection`(ICS 파생·감지, v1.8). `*` 는 기본 출처 |

> 구 `없을 때` 열(raw 에 카드가 없을 때 converter 가 대신 넣는 값 — **오류는 나지 않는다**)은 폐지하고 각 표 아래 주석으로 옮겼다. 기본값 경고(그럴듯한 값이 조용히 박히는 부류)는 각 절의 ⚠️ 문단이 계속 담는다.

표기: `ᴬ` = AUX/TCS 중계(pass-through) · `ᶠ` = FITS 표준 카드

> **`X` 가 전부 결함인 것은 아니다.** raw 가 실을 필요가 없다고 이미 정리된 것도 `X` 로 나온다 — 3.3절의 `XTALKVER` · `REFVER` · `CATVER` 가 그렇다. 각 표 아래 주석이 그 구분을 적어 둔다.

## 3.1 관측소 · 검출기 · 관측 식별

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `ORIGIN` | O | O | `ORIGIN` | `KASI`* / `SSO` / `CTIO` / `SAAO` | ICS INI |
| `BUNIT` | O | O | `BUNIT` `+amp` | `ADU` | ICS code |
| `DETID` | O | O | ((TBD)) | `MK` / `NT` | ICS code |
| `DETECTOR` | O | O | `DETECTOR` | `'e2v CCD290-99'` | ICS INI |
| `CCDXBIN` | O | O | `CCDXBIN` | `1` (2 & 3 reserved) | ICS code* / user selection |
| `CCDYBIN` | O | O | `CCDYBIN` | `1` (2 & 3 reserved) | ICS code* / user selection |
| `OBSERVAT` | O | O | `OBSERVAT` · `SITEID` | `CTIO` / `SSO` / `SAAO` / `KASI` (**D-017** — 구 `TESTBED` 대체) | ICS INI |
| `TELESCOP` | O | O | `TELESCOP` | `'KMTNet 1.6m Sim/#1/#2/#3'` | ICS INI |
| `LATITUDE` | O | O | `LATITUDE` | `'+dd:mm:ss.ss'` | ICS INI (=Legacy) |
| `LONGITUD` | O | O | `LONGITUD` | `'dd:mm:ss.ss'` (West) | ICS INI (=Legacy) |
| `ELEVATIO` | O | O | `ELEVATIO` | Integer | ICS INI (=Legacy) |
| `OBSERVER` | O | O | `OBSERVER` | `KMTNetOp`* / user input | ICS code* / user input |
| `OBJECT` | O | O | `OBJECT` `+amp` | `bias`* / user input | ICS code* / user input |
| `FIELDID` | **X** | **X** | `FIELDID` | MEF converter generating — `v("OBJECT", "")` ← fallback | `OBJECT` |
| `PROJID` | O | O | `PROJID` `+amp` | `OBS`* / user input | ICS code* / user input |
| `IMAGETYP` | O | O | `IMAGETYP` `+amp` | `BIAS`* / `DARK` / `OBJECT` / `FLAT` / `SKY` / `DOMEFLAT` | ICS code* / user selection |
| `OBSTYPE` | O | O | `OBSTYPE` `+amp` | `BIAS`* / `DARK` / `OBJECT` / `FLAT` / `SKY` / `DOMEFLAT` / user input | `IMAGETYP`* / user input |
| `INSTRUME` | O | O | `INSTRUME` | `'KMTK/KMTA/KMTC/KMTS 18k CCD'` (넷째 코드 **D-017** 개정) | ICS INI |
| `UNIQNAME` | O | **X** | `UNIQNAME` | replaced with `EXPID` card (v1.6 — 구 `ORIGNAME`) | ICS code |

**신규는 `FIELDID` 하나뿐이다.** 없으면 `OBJECT` 값이 그대로 들어간다 — 레거시가 필드명을 `OBJECT` 에 넣던 관행을 코드가 흡수한 형태다.

> 구 `없을 때`(converter 기본값): `ORIGIN "KASI"` · `BUNIT "ADU"` · `DETID "MK"/"NT"` · `DETECTOR "e2v CCD290-99"` · `CCDXBIN/CCDYBIN 1` · `TELESCOP "KMTNet 1.6m"` · `INSTRUME "KMTS"` · `FIELDID ← OBJECT` · 나머지 전부 `""`.

**`OBSERVAT` 는 이 문서에서 유일하게 "없거나 어긋나면 변환이 멈추는" 카드다.** `SITEID` 로도 복제되고, converter v2.2.0 이 **파일명의 사이트 코드와 교차 검증**한다 — 불일치는 오류다 (D-011). 나머지 카드는 전부 조용히 기본값으로 지나간다.

> **`OBSERVAT` · `ORIGIN` 확정 경위 (v1.7).** `OBSERVAT` 를 사이트 코드(`KMTA` 등)로 재정의하는 안이 검토됐으나 converter v2.2.0 의 교차검증(`OBS_PREFIX` 맵)과 정면 상충해 철회 — **현행 체계 그대로 `TESTBED`/`CTIO`/`SAAO`/`SSO` 로 확정**했고 개정 항목이 없다. `ORIGIN` 은 레거시 계승(관측소 raw 에서 OBSERVAT 와 중복)이되 개념을 **"이 파일이 생성된 곳"** 으로 정의한다: 관측소 raw = 관측소 이름 · 테스트베드 raw = `KASI` · KASI 파이프라인 산출물 = `KASI`. 이 개념의 귀결 하나 — converter 는 현재 raw `ORIGIN` 을 MEF 로 **복사**하는데(`v("ORIGIN","KASI")`), MEF 는 파이프라인 산출물이므로 **상수 `'KASI'` 로 쓰는 것이 맞다** (MEF Impacts v0.2 의 경미 C-항목).

> ⚠️ **기본값이 진짜 값처럼 보이는 넷**: `ORIGIN="KASI"` · `DETECTOR="e2v CCD290-99"` · `TELESCOP="KMTNet 1.6m"` · `INSTRUME="KMTS"`. raw 가 안 실으면 이 값들이 사이트·망원경과 무관하게 박힌다.
>
> 레거시 실측본과 대면 어긋남이 보였던 `INSTRUME`(레거시 `OBSERVAT='SSO'` 인데 `INSTRUME='KMTS'`)는 **v1.7 에서 형식이 확정됐다** — `'<SITE> 18k CCD'`(예: `'KMTA 18k CCD'`), 사이트와 함께 움직인다. `TELESCOP` 도 사이트별 번호(`Sim/#1/#2/#3`)를 싣는다.

## 3.2 노출 · 시각

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `EXPTIME` | O | O | `EXPTIME` | Integer [seconds] — 소수점 아래 값이 있으면 실수형으로 기록 (운영자 확정, 확인 요망 4 종결) | ICS code* / user input |
| `DARKTIME` | O | **X** | `DARKTIME` | `EXPTIME` 과 동일 — 파생으로 충분, 카드 불요 (v1.8) | `EXPTIME` |
| `TSHOPEN` | O | **X** | `TSHOPEN` | `'HH:MM:SS.mmm'` — v1.8 판정: 싣지 않음 | ICS code |
| `TSHSHUT` | O | **X** | `TSHSHUT` | `'HH:MM:SS.mmm'` — v1.8 판정: 싣지 않음 | ICS code |
| `TIMESYS` | O | O | `TIMESYS` | `UTC`* — comment 는 `ICS Time System`, TCS 쪽은 신설 `TCSTIME`(7장) | ICS code |

> 구 `없을 때`(converter 기본값): `EXPTIME`·`DARKTIME` `0.0` · `TSHOPEN`·`TSHSHUT` `""` · `TIMESYS` `"UTC"`.

**이 그룹에서 가장 중요한 `DATE-OBS` 는 이 표에 없다** — `card()` 밖에서 쓰이므로 4장에 있다.

**`DARKTIME` · `TSHOPEN` · `TSHSHUT` 는 v1.8 판정으로 신규 raw 가 싣지 않는다.** `DARKTIME` 은 `EXPTIME` 과 같은 값이라 파생으로 충분하다. ⚠️ **`TSHOPEN` 폐지는 MEF 에 파급이 있다** — converter 가 `DATE-OBS` 의 날짜부에 raw `TSHOPEN` 을 붙여 MEF `UT` 를 조립하므로(`v2_1.py:440` · `:583`), raw 가 `TSHOPEN` 을 싣지 않으면 **MEF `UT` 의 시각부가 빈다** (오류 없음). `DATE-OBS` 가 밀리초 시각을 온전히 가지므로 조립 원천을 `DATE-OBS` 시각부로 바꾸면 된다 — `DARKTIME`(converter 기본값 `0.0` 이 MEF 에 박힘)과 함께 **C-항목으로 등재했다** (MEF Impacts v0.3). "raw `UT` 카드 폐지(8장)는 MEF `UT` 에 영향이 없다"던 종전 문장은 이 C-항목 처리 전까지만 참이다.

> ⚠️ `EXPTIME` · `DARKTIME` 의 기본값이 `0.0` 이다 — 카드가 없으면 **"노출 0초"** 라는 유효해 보이는 값이 들어간다.

## 3.3 Archon 정체 · 버전

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `CTRL1ID` | **X** | O | `CTRL1ID` | `'KMTA-SCI-101'` — ID 숫자 = IP (`__reference/Archon_Unit_Info.txt`, 확인 요망 6 종결 — 운영자 재가 2026-08-22) | ICS INI |
| `CTRL1SN` | **X** | O | `CTRL1SN` | `'STA-0288'` | ICS INI |
| `CTRL1FW` | **X** | **X** | `CTRL1FW` | `CTRLxCFG` 로 귀속 (v1.8) | Archon telemetry |
| `CTRL1CFG` | **X** | O | — (converter 미독) | `'KMTA_SCI_101_STA0288_R2608_MK'` | ICS INI |
| `CTRL2ID` | **X** | O | `CTRL2ID` | `'KMTA-SCI-102'` | ICS INI |
| `CTRL2SN` | **X** | O | `CTRL2SN` | `'STA-0289'` | ICS INI |
| `CTRL2FW` | **X** | **X** | `CTRL2FW` | `CTRLxCFG` 로 귀속 (v1.8) | Archon telemetry |
| `CTRL2CFG` | **X** | O | — (converter 미독) | `'KMTA_SCI_102_STA0289_R2608_NT'` | ICS INI |
| `CTRLVER` | **X** | **X** | `CTRLVER` | `CTRLxCFG` 로 귀속 (운영자 개정은 행 삭제 — converter 가 읽는 사실 기록을 위해 유지) |  |
| `TIMVER` | **X** | **X** | `TIMVER` | `CTRLxCFG` 로 귀속 (v1.8) |  |
| `BIASVER` | **X** | **X** | `BIASVER` | `CTRLxCFG` 로 귀속 (v1.8) |  |
| `CLKVER` | **X** | **X** | `CLKVER` | `CTRLxCFG` 로 귀속 (v1.8) |  |
| `XTALKVER` | **X** | **X** | `XTALKVER` | **Pipeline calibration DB 소관** — raw 미기재 (확인 요망 8 종결, 운영자 재가 2026-08-22) | Pipeline caldb (C-14) |
| `REFVER` | **X** | **X** | `REFVER` | **Pipeline calibration DB 소관** — raw 미기재 | Pipeline caldb (C-14) |
| `CATVER` | **X** | **X** | `CATVER` | **Pipeline calibration DB 소관** — raw 미기재 | Pipeline caldb (C-14) |

> 구 `없을 때`(converter 기본값): `CTRL1*`·`CTRL2*` `"UNKNOWN"` · `CTRLVER "ARCHON-v1.0"` · `TIMVER "TIM-v1.0"` · `BIASVER "BIAS-v1.0"` · `CLKVER "CLK-v1.0"` · `XTALKVER "UNMEASURED"` · `REFVER`/`CATVER` `"N/A"`. 버전 문자열의 근거 순환(0.2 의 "하드코딩 × ICD 침묵" 칸)은 **v1.8 에서 `CTRLxCFG` 귀속으로 정리됐고 v1.13 에서 재가로 확정됐다(확인 요망 6·8 종결)** — 추적 대상이 적용 설정 파일 하나로 모이고, raw 는 그 파일명(`CTRL1CFG`/`CTRL2CFG`)만 실으면 된다. **`CAMVER` 도 판단 참조점이다 (운영자, 2026-08-22)**: HW·성능상 변경사항이 있을 때만 올리는 카드라, 설정 상세는 `CTRLxCFG` 로 · **전자부 HW/성능 세대는 `CAMVER` 로** 판단할 수 있다. 반면 `XTALKVER` · `REFVER` · `CATVER` 의 정본은 ACF 파일이 아니라 **calibration DB** 다(C-14) — 귀속 표기를 셋에 붙이면 없는 곳을 가리키는 포인터가 된다.

**표의 15장 전부 레거시 raw 에 없다** — 7장의 도입 후보와 같은 부류다(`CTRL1CFG`/`CTRL2CFG` 는 converter 미독 신설이라 1장 집계 어디에도 안 들고, 가족 묶음으로 이 표에 둔다). 성격이 둘로 갈린다.

**`XTALKVER` · `REFVER` · `CATVER` 셋은 raw 가 실을 필요가 없다.** converter 가 읽기는 하지만 raw 에 그 카드가 없으므로 **기본값(`"UNMEASURED"` · `"N/A"`)으로 채워지고, 지금은 그것이 맞는 상태다.** 규격 5.12 절이 *"현행 converter 는 이 값들을 MK 헤더에서 읽고 있지만 실제로는 calibration DB 소관"* 이라고 정리했고, caldb 주입으로 바꾸는 것이 **변경점 C-14** 다. 즉 이 셋의 `X` 는 결함이 아니라 **의도된 상태**다. **미기재 근거 확정(운영자, 2026-08-22, 확인 요망 8 종결)**: 이 값들은 **HW·성능 변화 없이도 pipeline setup 에서 바뀔 수 있어** 취득 시점의 raw 에 실으면 곧 낡은 값이 된다 — raw 는 취득 시점에 고정되는 사실만 싣는다. **계층 규칙(운영자, 2026-08-22)**: raw = 미기재 · **전처리 전 MEF(L0) = 수록 여부는 pipeline 팀 판단** · **전처리 후 MEF(L1) = 필수 수록**(보정에 실제 적용한 버전이므로). 이 규칙은 통합 문서(LEECU 전달용)에도 등재했다.

나머지는 신규 전자부에 필연적으로 따라오는 것들이다. v1.8 판정으로 **정체 4장(`CTRLxID`/`CTRLxSN`)과 설정 포인터 2장(`CTRLxCFG`)이 도입 `O`**, 펌웨어·버전 문자열(`CTRLxFW` `TIMVER` `BIASVER` `CLKVER`)은 **`CTRLxCFG` 로 귀속돼 `X`** 다.

**`CTRL1*` · `CTRL2*` 가 색인형인 이유**: converter 가 **MK 헤더만** 읽으면서(`convert()` 가 두 chip 에 `mk_hdr` 하나만 넘긴다) 컨트롤러 두 대분 정체를 요구한다. 단수형으로 두면 MEF 가 전부 `UNKNOWN` 을 받는다. 레거시도 raw 파일마다 `KBUILD`/`MBUILD`/`TBUILD`/`NBUILD` 를 다 실어 같은 구조였다 — 그 넷은 8장에서 폐지되고 `CTRL1FW`/`CTRL2FW` 가 자리를 물려받았다 — 그리고 그 둘도 v1.8 에서 `CTRLxCFG` 귀속으로 정리됐다.

> **컨트롤러 2대분을 양쪽 raw 에 모두 싣는다** (운영자 확정, v1.7_revision) — 파일을 만든 컨트롤러 것만 싣는 안도 검토됐으나 기각했다. guide FITS 는 컨트롤러가 1대라 `CTRL1xx` 한 벌만 싣고, 컨트롤러 수가 늘면 `CTRLnxx` 벌이 늘어나는 **확장 규약**이다.

> ⚠️ **버전 문자열의 기본값이 진짜 provenance 처럼 보인다** — `"ARCHON-v1.0"` · `"TIM-v1.0"` · `"BIAS-v1.0"` · `"CLK-v1.0"`. raw 가 안 실어도 MEF 에 그럴듯한 버전이 박히고 오류는 나지 않는다. 이 값들의 **근거가 순환하는 문제**는 검토 문서 2.4절에 있다.

## 3.4 TCS 링크 · 포인팅

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `TCSLINK` | O | O | `TCSLINK` | `Up` / `Idle` / `Down` | TCS relay |
| `TCSARC` | O | O | `TCSARC` |  | TCS relay |
| `TCSQDATE` | O | O | `TCSQDATE` |  | TCS relay |
| `TCSUDATE` | O | O | `TCSUDATE` |  | TCS relay |
| `RADECSYS` | O | O | `RADECSYS` | `ICRS`* | ICS code |
| `RA` | O | O | `RA` `+amp` | `'hh:mm:ss.ss'` | TCS relay |
| `DEC` | O | O | `DEC` `+amp` | `'±dd:mm:ss.s'` | TCS relay |
| `EQUINOX` | O | O | `EQUINOX` | `2000.0`* | ICS code |
| `HA` | O | O | `HA` `+amp` | `'±hh:mm:ss'` | TCS relay |
| `ST` | O | O | `ST` `+amp` | `'hh:mm:ss'` | TCS relay |
| `SECZ` | O | O | `SECZ` `+amp` |  | TCS relay |
| `ALT` | O | O | `ALT` `+amp` |  | TCS relay |
| `AZ` | O | O | `AZ` `+amp` |  | TCS relay |
| `TCSDRIVE` | O | O | `TCSDRIV` — `v("TCSDRIV", "")` ← fallback |  | TCS relay |
| `TELMOVE` | O | O | `TELMOVE` |  | TCS relay |

> 구 `없을 때`(converter 기본값): `RADECSYS "ICRS"` · `RA "00:00:00.00"` · `DEC "+00:00:00.0"` · `EQUINOX 2000.0` · 나머지 전부 `""`.

**전부 레거시 계승이고 v1.8 에서 전 행 `O` 로 판정됐다.** 시각계 선언은 초안 v0.3.5 에서 둘로 갈라졌다 — `TIMESYS`(ICS 시각계, 3.2절) · **`TCSTIME`**(TCS 시각계, 7장 신설 `O`). 4장의 `TCSDRIV` 만 레거시에 없는데 그것도 구멍이 아니다 — converter 가 **`TCSDRIVE`(8자)를 먼저 보고** 없을 때만 `TCSDRIV` 를 본다. 레거시가 쓰는 이름이 `TCSDRIVE` 이므로 **raw 는 `TCSDRIVE` 로 쓰면 된다.**

> ⚠️ **`RA` · `DEC` 의 기본값이 빈 문자열이 아니다** — `"00:00:00.00"` · `"+00:00:00.0"`. 카드가 없으면 **형식이 유효한 그럴듯한 좌표**가 들어가서 하류에서 걸러지지 않는다. `EQUINOX` 도 `2000.0` 이 들어간다.

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

`SHUTTER` 는 `SHUTOP` 의 **순수 함수**이고 "완전 개방" 을 뜻하지 않는다 — `OPEN` 이 개방중·개방·폐쇄중을 모두 덮는다 (규격 5.10 의 통제 어휘).

> **`FSATEMP` · `FSAHUM` 의 형·포맷 (v1.12)** — 문자열(3.7 의 HK 온·습도 확정과 동일), 표기는 **ENS식 잠정 채택**: 부호 생략(음수면 자연히 `-`)·소수 1자리(`'23.4'` · `'12.3'`) — 레거시 `ENS1 = '23.0'` 선례와 일치하고 초안 표기 그대로다. 측정불가 sentinel 은 HK 와 같은 **`'-999.99'`**. ⚠️ **Radionode 원값 포맷은 워크스페이스에 근거가 없다** — 실기/장치 문서로 확인 후 "원값 그대로 싣기"로 최종 확정한다(게이지 원문을 존중한 `DEWPRES` 와 같은 정신). V1 재작성 시 확인 항목으로 이관.

## 3.6 돔 · 미러커버 (돔 = TCS 관장, v1.11)

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `DSSTAT` | O | O | `DSSTAT` |  | TCS relay or REDIS* |
| `DSUP` | O | O | `DSUP` |  | TCS relay or REDIS* |
| `DSLW` | O | O | `DSLW` |  | TCS relay or REDIS* |
| `DSSAF` | O | O | `DSSAF` |  | TCS relay or REDIS* |
| `DSAUTO` | O | O | `DSAUTO` |  | TCS relay or REDIS* |
| `DSALT` | O | O | `DSALT` |  | TCS relay or REDIS* |
| `DSAZ` | **X** | O | `DSAZ` |  | TCS relay or REDIS* |
| `DSTELALT` | **X** | O | `DSTELALT` (`DSTEL` → `DSTELALT`) |  | TCS relay or REDIS* |
| `DSTELAZ` | **X** | O | `DSTELAZ` |  | TCS relay or REDIS* |
| `DALTERR` | **X** | O | `DALTERR` |  | ICS calculation |
| `DAZERR` | **X** | O | `DAZERR` |  | ICS calculation |
| `MCSTAT` | O | O | `MCSTAT` |  | AUX relay |
| `MCPOS` | O | O | `MCPOS` |  | AUX relay |

> 구 `없을 때`(converter 기본값): 전부 `""`.

**돔 필드는 셋으로 갈린다** — 계승 6(`DSSTAT` `DSUP` `DSLW` `DSSAF` `DSAUTO` `DSALT`) · 신규 4(`DSAZ` `DSTELAZ` `DALTERR` `DAZERR`) · 개칭 1(`DSTELALT`).

> **돔 출처 변경 (운영자, v1.10_revision)** — dome shutter 정보의 source 가 기존 `AUX relay` 에서 **`TCS relay or REDIS`** 로 변경됐다. 돔 azimuth 는 원래 TCS 에서 관장하고, **newTCS 로 전환되면서 dome shutter control 이 TCS 에 편입**되었으므로 돔 정보는 AUX 가 아닌 TCS 에서 가져와야 한다. 이에 따라 초안 헤더의 DS 카드 블록 위치도 **TCS Information and Status 절**로 옮겨졌다. 미러커버 2장(`MCSTAT` `MCPOS`)은 그대로 AUX 소관이라 절 이름에서 "AUX" 를 뗐다. (`DSAZ` 행의 구 표기 `TCS relay or REDIS (v1.8)` 는 `*` 기본 표기로 정규화. `DALTERR` · `DAZERR` 는 망원경–돔 지향의 **차이값**이라 중계가 아니라 `ICS calculation` 이다.)

> `DSTELAZ` 는 TCS `AZ` 와 중복일 수 있어 **돔 쪽 TelAz 가 별도 관리되는지 확인 후 도입을 한 번 더 검토**한다 — 일단은 정보 확인 편의를 위해 싣는 방향이다(운영자, v1.7_revision). 돔 신설 4장은 초안 v0.3.7 에 반영 확인됐다(확인 요망 3 종결).

`DSTELALT` 는 레거시 `DSTEL` 의 개칭이다 (D-013). **공급 계통이 TCS 로 바뀌어도 converter 가 `DSTELALT` 만 읽는 사실(fallback 없음)은 그대로다** — 중계 필드명이 무엇이든 ICS 가 `DSTELALT` 카드로 실어야 한다. 레거시 이름 `DSTEL` 은 6장에 있다.

> 계승 6개는 `ics_sim` 이 아직 쓰지 않는다. **레거시 설계에 이미 있으므로 검토 안건이 아니라 구현 일감이다.**

## 3.7 AUX — 열 환경 · 영상 점검

| Raw Keywords | Raw Legacy | Raw Archon | Use in MEF | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `CHSTAT` | O | **X** | `CHSTAT` | v1.8 판정: 싣지 않음 — v1.9 재잔존 → **v1.11 재삭제 검증 완료(확인 요망 1 종결)** | AUX relay |
| `ENSTAT` | O | O | `ENSTAT` |  | AUX relay |
| `ENFAN` | O | O | `ENFAN` |  | AUX relay |
| `CCDTEMP` | O | O | `CCDTEMP` | [degC] — **실측 대표 센서** (comment `CCD temperature` — chip 귀속 `M` 은 2026-08-30 제거) | ICG RTD measurement |
| `DEWPRES` | O | O | `DEWPRES` | `x.xxe-x` [torr] 문자열 · 측정불가 `9.99e-9`* (0·음수·비수치·범위 밖 — 게이지의 `0.00e-0` 포함) | ICG RTD measurement |
| `PT30N1` | O | O | `PT30N1` | PT-30 #1 cold-end [degC] | ICG RTD measurement |
| `PT30N2` | O | O | `PT30N2` | PT-30 #2 cold-end [degC] | ICG RTD measurement |
| `CHARCOAL` | O | O | `CHARCOAL` | charcoal canister [degC] | ICG RTD measurement |
| ~~`AIR_IN`~~ | **폐지** | — | — | ~~열교환기 흡기 [degC]~~ — **raw spec v1.5 에서 폐지 (운영자 확정 2026-08-25)**, 5.10절 목록 | ~~standalone RTD readout unit~~ |
| ~~`AIR_OUT`~~ | **폐지** | — | — | ~~열교환기 배기 [degC]~~ — v1.5 폐지 | ~~standalone RTD readout unit~~ |
| ~~`GLYC_IN`~~ | **폐지** | — | — | ~~HE box 유입 glycol [degC]~~ — v1.5 폐지 | ~~standalone RTD readout unit~~ |
| ~~`GLYC_OUT`~~ | **폐지** | — | — | ~~HE box 배출 glycol [degC]~~ — v1.5 폐지 | ~~standalone RTD readout unit~~ |
| `CHKIMG` | **X** | **X** | `CHKIMG` |  | Pipeline 에서 판별하는 대상 — raw 카드 아님 (v1.10) |
| `CHKIMG_C` | **X** | **X** | `CHKIMG_C` |  | Pipeline 에서 판별하는 대상 — raw 카드 아님 (v1.10) |

> 구 `없을 때`(converter 기본값): 전부 `""`.

**14개 중 신규는 `CHKIMG` · `CHKIMG_C` 둘뿐**이고, 이 둘도 레거시 raw 에 없어 FSA 4개와 같은 물음에 걸렸었다 (검토 문서 5.4절 9번). FSA 쪽은 v1.8 에서, 이 둘은 **v1.10 에서 `X` 로 판정됐다** — 영상 점검은 취득 시점에 존재할 수 없는 값이고 **pipeline 이 판별하는 대상**이라 raw 카드가 아니다. 이로써 검토 항목 9 는 전량 종결이다.

**`CCDTEMP` 의 평균 파생(D-013)은 v1.8 에서 폐기됐다.** 온도센서 구성이 바뀌어 **실측 대표 센서 1개** 값을 싣는다(comment `CCD temperature` — chip 귀속 `M` 은 2026-08-30 제거) — 출처는 `ICG RTD measurement`, `CCDTEMP1`/`CCDTEMP2` 후보는 **제외 확정**이다(7장 `X`). ⚠️ 대표값을 파일만으로 검산할 근거는 사라졌다 — 센서 이상은 취득 SW 로그가 담는다. MEF/L1 쪽 정의 문구("평균 파생")의 갱신은 C-항목이다(MEF Impacts v0.3 ②).

**HK 온도·습도 카드는 전부 문자열이다 (확인 요망 9 종결 — 운영자 확정 2026-08-22).** 레거시 실측이 이미 부호 포함 문자열(`'-103.16 '` · `'+34.98  '`)이었고 converter 는 pass-through 라 문자열 계승이 아카이브 전체의 형을 통일한다 — 신규만 실수형이면 같은 이름에 두 형이 섞인다. 표기는 초안대로 **부호 포함 소수 2자리**(`'-101.23'` · `'+16.78'`)다. **측정불가 sentinel 은 온도·습도 전 카드 `'-999.99'` 단일값** — 온도로는 불가능한 값이고 습도로는 음수라 불가능하다 (기각안: `-99.99` 는 CCDTEMP 냉각 램프가 실제로 지나가는 값, 습도 `0.00` 은 유효 측정값). `ics_sim` 의 실수형 구현이 고칠 대상이다.

**`DEWPRES` 는 문자열 카드다** — 지수 표기 `x.xxe-x` 를 고정하려면 실수 카드로는 안 되고(astropy 가 표기를 정한다), 측정불가는 전부 **`9.99e-9`** 로 접는다. HK 카드의 공급 계통은 셋으로 갈린다 — Archon 쪽 `ICG RTD measurement` · 별도 장치 `standalone RTD readout unit`(AIR/GLYC) · `Radionode sensor`(`HEBOX`, 7장). 레거시의 "AUX relay" 출처는 HK 에서 전부 물러났다. ⚠️ **raw spec v1.5(2026-08-25)에서 `AIR_IN`/`AIR_OUT`/`GLYC_IN`/`GLYC_OUT` 4장이 폐지되어 `standalone RTD readout unit` 계통은 raw 헤더에서 비었다** — 공급 계통은 이제 `ICG RTD` 와 `Radionode` 둘이다.

## 4. `card()` 밖에서 쓰이는 둘

| Raw Keywords | Raw Legacy | Raw Archon | MEF Usage | Value (`*` default) | Source (`*` default) |
| --- | :---: | :---: | --- | --- | --- |
| `DATE-OBS` | O | O | `DATE-OBS` · `MJD-OBS` · `JD` · `UT` 를 여기서 파생시킨다. ⚠️ **없으면 변환 시각(now)으로 대체**되어 네 카드가 전부 관측과 무관해지고 **그래도 오류가 나지 않는다** (규격 6.2, C-6) | `'YYYY-MM-DDThh:mm:ss.mmm'` — **밀리초 필수** (D-014) | ICS code (SHOPEN 시각) |
| `TCSDRIV` | **X** | **X** | `TCSDRIVE` 가 없을 때만 보는 fallback 이다. 레거시가 쓰는 이름은 8자 `TCSDRIVE` 이므로 **구멍이 아니다** |  |  |

**이 문서 전체에서 가장 위험한 카드가 `DATE-OBS` 다.** 다른 카드는 없으면 빈 문자열이 들어가 나중에라도 눈에 띄지만, `DATE-OBS` 는 **그럴듯한 시각**으로 채워져 티가 나지 않는다.

## 5. `hval()` 로 직접 읽는 것

`v()` 를 거치지 않고 변환 로직이 직접 읽는 카드다. MEF 카드로 옮기는 것이 아니라 **픽셀 해석과 검증에 쓴다.**

| raw 키워드 | 쓰임새 |
| --- | --- |
| `BITPIX` · `BSCALE` · `BZERO` | 픽셀 값 복원 (`BITPIX=16` + `BZERO=32768` 부호없는 저장) |
| `NAXIS1` · `NAXIS2` | raw 영상 크기 확인 (`19200 x 9400`) |
| `OBSERVAT` | 파일명 사이트 코드와 **교차 검증** — 불일치는 오류 (v2.2.0, D-011) |

## 6. 레거시에 있으나 converter 가 읽지 않는 카드 (22장)

**레거시 raw 가 싣던 카드인데 converter 가 값을 꺼내지 않는다.** 폐지된 것도 아니다(그건 8장). 이유는 대체로 셋이다 — **converter 가 자기 상수를 쓰거나**, **신규 규격이 더 정확한 다른 이름으로 나눴거나**, **raw 쪽 기록으로만 남기기로 한 것**이다.

| raw 키워드 | Raw Legacy | Raw Archon | 용도 / 레거시 실측값 / Archon 계획 | converter 는 어떻게 하나 |
| --- | :---: | :---: | --- | --- |
| `SIMPLE` | O | O | FITS 표준 필수 카드 | converter 가 **자기가 새로 만든다** (`card("SIMPLE", True)`). raw 값을 볼 이유가 없다 |
| `NAXIS` | O | O | 축 수 | 〃. MEF PRIMARY 는 영상이 없어 `0`, amp extension 은 `2` 다 |
| `PRESCANX` → **`PRESCNX` 로 변경** | O | O (`PRESCNX`/`PRESCNY` 로 변경하여 계승 — v1.13, 확인 요망 10 종결) | amp 당 수평 prescan 열 수 — 레거시 실측 `27`, 신규 `0`(prescan 없음). **`OVRSCNX`/`OVRSCNY` 를 정하고 나서 자리수를 맞춰 개칭했다**(운영자, 2026-08-22) — 그대로 계승이 아니라 **키워드 변경 계승**이다: 레거시 27 과 신규 0 의 동명이값도 이름 분리로 해소된다 | converter 가 자기 상수 **`0`** 을 쓴다(`PRESCAN_X`). 신규 구조에는 prescan 이 없다 |
| `PIXSCALE` | O | O | 픽셀 스케일 [arcsec/px] — 레거시 실측 `0.400` | converter 가 자기 상수 **`0.395`** 를 쓴다 — 소스 주석이 *"measured vs Gaia DR3 (was 0.400 nominal)"* 라고 밝힌 **실측 갱신값**이다 |
| `PIXSIZE` | O | O | 픽셀 크기 [micron] — 레거시 실측 `10.0` | converter 가 자기 상수 `10.0` 을 쓴다. 값은 같다 |
| `NPHLINES` | O | **X** | preheat line 수 — 레거시 계승(5.13절). ADC/비디오단을<br>안정시키려 독출 전에 버리는 dummy line. 값의 정본은<br>`ACFFILE`이 가리키는 timing script 다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `DATASRC` | O | O | **`ARCHON_SCIENCE` / `ARCHON_GUIDE` / `SIM`** — 레거시 계승(5.13절)<br>+ 값 체계 확장(v1.8, 추후 확장 대비). 레거시는 ADC/CTC 보정 경로<br>구분이었고 Archon 에서는 **컨트롤러·HW 셋업 요약**으로 쓴다.<br>**시뮬 프레임이 실측으로 오인되는 것을 막는 유일한 카드**라는<br>성격은 그대로다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `HEMODE` | O | **X** | **`SCIENCE` / `GUIDE`** — 레거시 계승(5.13절)이었으나<br>**v1.8 에서 삭제 판정**: `DATASRC`(`ARCHON_GUIDE`) 및<br>`CTRLxID` 와 중복이다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `LEDFLASH` | O | O | 점검용 LED 프로젝터 점등 시간 — **정수형 [milliseconds]**<br>(운영자 확정 2026-08-22, 확인 요망 4 종결). `0`이면 점등 안 함.<br>**레거시 계승(5.13절)** — 램프로 만든 실험실 flat 을 하늘<br>자료로 오인하지 않게 하는 카드다. ⚠️ **단위 변경**: D-013 계승<br>조건은 "레거시와 같은 초 유지"였으나, 정수형을 유지하면서<br>250 ms 같은 sub-second 값의 잘림을 막으려 **ms 로 변경**했다.<br>같은 이름에 1000배 다른 단위이므로 **카드 comment 가<br>`[milliseconds]` 를 명시**한다 — 계산 소비자는 없다(converter 미독).<br>`ics_sim` 반영 완료(ms÷1000 제거) | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `FILENAME` | O | O | 자료 취득 시스템이 붙인 파일명 | converter 가 **MEF 출력 파일명으로 새로 만든다**(`out_path.name`). raw 의 `FILENAME` 은 raw 쪽 식별자로 남는다 |
| `ICSBUILD` | O | O | **취득 프로그램의 빌드 식별자** — 레거시 계승(5.13절).<br>형식은 **`v<버전>:<빌드일시(UTC)Z>`**,<br>예 `'v1.2.3:2026-08-21T18:09Z'` — 프로그램명 제거<br>(운영자 확정 2026-08-22, 확인 요망 5 종결). 작성 프로그램<br>식별은 `DATASRC` 가 담당한다. 끝의 `Z` 는 의도적(시각 카드가<br>아니라 떼어 읽는 식별자). `ics_sim` 반영 완료 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `DSTEL` → **`DSTELALT` 로 변경** | O | O (`DSTELALT` 로 변경하여 적용 — v1.10) | 돔이 쓰는 망원경 고도 [deg] | **`DSTELALT` 로 개칭됐다** (D-013). converter 는 `DSTELALT` 만 읽고 fallback 이 없어 **AUX 가 보내는 `DSTEL` 을 ICS 가 옮겨 실어야 한다** |
| `CHOP` | O | **X** | chiller 블록 미도입 — 초안에서 삭제 (2026-08-21) | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `CHSET` | O | **X** | chiller 블록 미도입 — 초안에서 삭제 (2026-08-21) | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `CHPROC` | O | **X** | chiller 블록 미도입 — 초안에서 삭제 (2026-08-21) | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `ENS1` | O | O | AUX 중계값을 그대로 싣는다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `ENS2` | O | O | AUX 중계값을 그대로 싣는다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `ENS3` | O | O | AUX 중계값을 그대로 싣는다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `ENS4` | O | O | AUX 중계값을 그대로 싣는다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `ENS5` | O | O | AUX 중계값을 그대로 싣는다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `ENS6` | O | O | AUX 중계값을 그대로 싣는다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |
| `ENS7` | O | O | AUX 중계값을 그대로 싣는다 | 읽지 않는다. **MEF 목적지가 없고 raw 아카이브 기록으로만 남는다** |

> ⚠️ **`NAMPS` · `OVERSCNX` · `PRESCANX` 는 이름이 같고 값이 다르다.** 레거시는 `8` · `32` · `27` 이었고 converter 는 `64` · `48` · `0` 을 쓴다. 같은 이름을 물려주면 **어느 쪽 값인지 읽는 쪽이 알 수 없다** — 8장 `OVERSCNY` 와 같은 부류의 위험이다.

> `PIXSCALE` 은 값이 갱신된 사례다. 레거시 `0.400`(공칭) → converter `0.395`, 소스 주석이 *"measured vs Gaia DR3"* 라고 근거를 남겼다.

> v1.9: Chiller 는 시스템에서 제거되어 CH* 카드 전체 미도입이 재확인됐다(운영자) — 초안 v0.3.6 재잔존은 **v1.11 에서 재삭제 검증 완료**(확인 요망 1 종결. 재잔존 원인은 백업 재편 중 구판 파일 교체로 확인).

## 7. Archon ICS 도입 후보·확정 카드 (카드 63장 · 표 55행)

**레거시 raw 에는 없고 규격 v1.2 · `ics_sim` · 확정 초안이 새로 들인 카드다.** converter 는 이 카드들을 읽지 않으므로 **MEF 로 가지 않는다.** 용도는 (1) converter 교차검증 선언, (2) pair 식별, (3) 아카이브 기록 세 가지다.

> **`도입 여부` 열은 운영자가 채운다** — `O` = 도입 확정 · `X` = 도입 안 함 · 빈칸 = **아직 안 정함**. `Raw Archon` 열(2장)과 같은 성격이라 생성기 안에 표로 들고 있다.
>
> **v1.7 에서 바뀐 것**: 확정 초안(`__reference/Detector_and_Amp_Info_cards_v1.0.txt` · 헤더 초안)이 들인 **신규 14장을 추가**하고(`AMPNAX1/2` `IMAGEX/Y` `PRESCNX/Y` `OVRSCNX/Y` `CHMAP_*` `FPAID` `ORIGNAME` — 전부 `O`), 기존 후보의 도입 여부를 검토 결과대로 판정했다. 파생 가능해진 카드(`NXTILE` `CCDCOLS` `CCDROWS`)와 대체된 카드(`AMPMAP`), 규격 조항으로 이관하는 카드(`ROWORDR`)는 `X` 다.
>
> **v1.8 에서 바뀐 것**: HK 재구성 신설 3장(`DMPTEMP` `WALLBRD` `HEBOX`)과 `TCSTIME` 을 추가하고(전부 `O`), `CCDTEMP1`/`CCDTEMP2` 를 **제외 확정**(`X` — 평균 파생 폐기, 3.7절), `ACFFILE`·`CTR_CFG` 항목을 **`CTRL1CFG`/`CTRL2CFG` 확정**(3.3절)으로 종결했다.
>
> **v1.9 에서 바뀐 것**: 빈칸 26행을 전부 `O`/`X` 로 판정해 **`도입 여부` 열이 완결됐다** — 문서 전체의 잔여 미정은 3.7 의 `CHKIMG` · `CHKIMG_C` 뿐이다. `READMODE`→`RDMODE` 개명 도입, `BCKTEMP`→`Cn_TEMP`/`Cn_VOLT`/`Cn_CURR` 변경·확장(+5), `CAMVER` 신설(+1) — 카드 57→63장, 표 54→55행.

> **"후보" 라고 부르는 이유**: 레거시 카드는 2017→2021 실측으로 정착된 설계지만 이 표의 카드는 **판정 전까지는 제안**이다. 이름·구성이 검토 대상이고(ACT-011), 규격 문서 자체가 ((재작성중)) 이다.

| 도입 후보 카드 | 도입 여부 | 용도 / 설명 | 유의사항 |
| --- | :---: | --- | --- |
| `ACFFILE` · `CTR_CFG` | **X** | 적용된 Archon 설정 파일 | **v1.8: `CTRL1CFG`/`CTRL2CFG`(3.3절)로 확정** — 컨트롤러별<br>색인형으로 가면서 이름 단일화 미결도 함께 종결됐다 |
| `READMODE` → **`RDMODE` 로 변경** | **O** | 컨트롤러 ACF/Setting 에 따른 readout mode 를<br>user-friendly 하게 제공 (값 예: `'NORMAL'` — 초안 v0.3.6) | 값 충돌(`'FAST'` vs `'64AMP'`)은 **이름 분리로 종결** (v1.9) —<br>raw `RDMODE`(독출 모드) / MEF `READMODE`(`'64AMP'`, converter 상수) |
| `NAMPDET` | **O** | **chip(검출기) 하나당 amplifier 수** = `16`.<br>`AMPPCD` 를 대신한다 | comment 는 레거시 `NAMPS` 문구를 잇는다 —<br>*Number of amplifiers in the detector*. 확정 초안 반영 |
| `AMPMAP` | **X** | `EXPLICIT`이면 아래 표가 유효. `DEFAULT`면 converter의<br>추정식을 쓴다는 선언 | **v1.7: `CHMAP_*` 4장으로 대체** — 선언 카드 자체가 불필요해졌다 |
| `AMPNAX1` | **O** | **amp 타일의 X 크기** = `1200` (prescan+image+overscan) | `NAXIS1/AMPNAX1 = 16` 으로 타일 수 파생. MEF `RAWXTILE` 과 값 동일, 이름 상이 |
| `AMPNAX2` | **O** | **amp 타일의 Y 크기** = `4700` = `NAXIS2/NEND` (타일 규약) | `AMPNAX2−IMAGEY = 84` 가 중앙 overscan 의 amp 몫 — **물리 분배는 OI-4** |
| ~~`BCKTEMP`~~ → **`Cn_TEMP` `Cn_VOLT` `Cn_CURR`**<br>로 변경·확장 | **O** (변경·확장) | Archon unit monitoring (Archon telemetry). Sci: n=1,2 · Gui: n=1.<br>Temp 는 Backplane 이후 Slot 순서, Volt/Curr 는<br>P2V5·P5V·P6V·N6V·P17V·N17V·P35V 순서 —<br>**공백 구분 나열**(자리=항목) | Sci module 순서: Backplane, Slot1 LVDS, Slot2 Driver, Slot3 Driver,<br>Slot4 LVX Bias, Slot5 ADM, Slot8 ADM, Slot9 HVY Bias, Slot10 Driver,<br>Slot11 Driver / Gui: Backplane, Slot3 Driver, Slot4 Driver, Slot5 AD,<br>Slot6 AD, Slot7 HeaterX, Slot9 HVY Bias, Slot10 HeaterX —<br>✅ **raw spec 5.6.1절에 명세로 수록 완료**(v1.5, 2026-08-25). ⚠️ **표기 개정 (2026-08-25)**: 위 `Slot<n>` 은 구 표기다 — 현행은 **`Mod<n>`**(Module) 이고 첫 모듈은 **`Mod1`** 이다(`Mod1:LVDS` · `Mod2:Driver` …). 자리 순서 자체는 그대로다.<br>Gui 순서는 실기 대조 전이라 **OI-19** 로 승계 |
| `BUFNO` | **X** | 사용한 Archon frame buffer | 모니터링 불필요(버퍼를 번갈아 사용) |
| `CAMVER` | **O** | Camera electronics version — INI 설정, 값 `CEU-v2.1`. **HW·성능상 변경사항이 있을 때만 올린다** — 전자부 세대 판단의 참조점(운영자, 2026-08-22). 설정 상세 추적은 `CTRLxCFG` 몫 | v1.9 신설 (초안 v0.3.6) |
| `CCDCOLS` | **X** | chip 1개의 active column | **`IMAGEX × 8` 로 파생 — 카드 불요** (v1.7) |
| `CCDROWS` | **X** | chip 1개의 active row | **`IMAGEY × 2` 로 파생 — 카드 불요** (v1.7) |
| `CCDTEMP1` | **X** | `CHIP1` 온도 [degC] | **v1.8 제외 확정** — HK 재구성으로 평균 파생 폐기(3.7절) |
| `CCDTEMP2` | **X** | `CHIP2` 온도 [degC] | 〃 |
| `CHECKSUM` | **X** | FITS 표준 checksum |  |
| `CHIP1` | **X** | X 1–9600 절반의 chip | `DETID` 유지 확정(3.1)과 함께 **관련 키워드 검토 때 재론** |
| `CHIP2` | **X** | X 9601–19200 절반의 chip | 〃 |
| `CHIPS` | **X** | 이 파일에 담긴 chip (X 낮은 쪽부터) | 〃 |
| `CHMAP_LT` `CHMAP_LB`<br>`CHMAP_RT` `CHMAP_RB` | **O** | **CCD 출력 채널 맵 4장** — 사분면(좌/우 절반 × TOP/BOT 행)별<br>8토큰, raw X 오름차순. **토큰은 4자 `<chip><A\|D><nn>`**<br>(01–08=`A` · 09–16=`D`, raw spec v1.5 개정 — 구 3자 `M16` 대체).<br>예: `'MD16,MD15,…,MD09'` | `AMOD<nn>`/`ACHN<nn>` 색인형 65장을 대체.<br>converter C-11 이 이 카드에서 `MODULE`/`CHANNEL` 을<br>채우도록 개정 대상. 값 = **CCD 출력단**(Archon module/channel 은 다음 단).<br>**세부 내용, 앰프별 배치 및 방향은 raw spec 4.5절<br>(Amp 전수 표)을 참조한다.** |
| `CTRLERR` | **X** | `TELEMETRY.ERRORFLAG` | 별도 모니터링 하므로 미적용 |
| `CTRLSTAT` | **X** | `TELEMETRY.STATUS` | `Cn_TEMP`/`Cn_VOLT`/`Cn_CURR` 와 중복 |
| `CTRLTAG` | **X** | **이 파일이 pair의 어느 쪽인가** (`MK`/`NT`) | 아카이브 근거 — `FILENAME`(+`EXPID`)/`CTRLTAG` (D-012 문구 개정).<br>**v1.9 미도입 확정 — `DETID` 와 값 중복.** pair 식별은<br>`FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)로 충분 |
| `DATASUM` | **X** | FITS 표준 datasum | 미사용 |
| `DMPTEMP` | **O** | DMP 온도 [degC] — HK 재구성 신설 (v1.8) | `ICG RTD measurement` |
| `EXECODE` | **X** | ICS relay 필드 |  |
| `FPAID` | **O** | **Focal Plane Assembly ID** (예: `'FPA#1'`) | 검출기 조립 정체는 FPA 단위 — FPA↔CCD 시리얼 대응표는 규격 부록 몫 |
| `FRAMENO` | **X** | controller frame counter | 진단용, MEF 목적지 없음 — `FILENAME`/`EXPID` 와 중복이므로 미적용 |
| `HEBOX` | **O** | HE box 내부 온도 [degC] — HK 재구성 신설 (v1.8) | `Radionode sensor` |
| `IMAGEX` | **O** | amp 당 image(active) 열 수 = `1152` | MEF `AMPDATA` 와 값 동일, 이름 상이 — `Use in MEF` 열이 그 대응이다 |
| `IMAGEY` | **O** | amp 당 image(active) 행 수 = `4616` | `IMAGEX` 와 같음 — `Use in MEF` 열 참조 |
| `MIDOSCB` | **X** | 중앙 overscan 중 BOT half에서 나온 row 수 | v1.9: 오류 사례 없음 — `OVRSCNY` 로 충분 (구 "OI-4 실측 후 도입") |
| `MIDOSCT` | **X** | 중앙 overscan 중 TOP half에서 나온 row 수 | 〃 |
| `NAMPRAW` | O | **이 파일에 담긴 amplifier 수** (chip 2 × amp 16) |  |
| `NXTILE` | **X** | X 방향 amp tile 수 (chip 2 × strip 8) | **`NAXIS1 / AMPNAX1` 로 파생 — 카드 불요** (v1.7) |
| ~~`ORIGNAME`~~ → **`EXPID`** | **O** | **카운터가 이 노출에 처음 배정한 식별자** `<SITE>.<YYYYMMDD>.<NNNNNN>` — 모든 파일에 항상 기록.<br>**`DETID` 필드가 없어 pair 양쪽 동일** → 짝을 잇는 단일 키.<br>충돌 신호 = `FILENAME` 의 `DETID` 필드를 뗀 값 ≠ `EXPID` | `UNIQNAME`·`NAMECLSH`·`clash/` 격리를 대체(8.2절, **D-016 등재**).<br>**v1.6 에서 `ORIGNAME` → `EXPID` 개명·재정의** (운영자 확정 2026-08-26).<br>상세: 통합 문서 v0.5 Part 2 |
| `OSCNPATT` | **X** | strip 1–8의 overscan 위치 (R=오른쪽, L=왼쪽).<br>**근거는 converter의 `is_bias_right()`** —<br>`strip_id(amp)=((amp-1)%8)+1`,<br>`is_bias_right(amp)= 1≤amp≤4 or 9≤amp≤12` | converter 가 이 카드를 읽지 않아 **선언과 하드코딩이<br>갈라져도 변환 쪽에서 못 잡는다**(C-5/C-13). 취득 SW 쪽 방어는<br>`test_geometry_vs_converter.py`. **v1.9 미도입 — 헤더가<br>복잡해지므로 세부내용은 raw FITS spec 에 수록**(포장 규범 조항 이관 전제) |
| `OVRSCNX` | **O** | amp 당 X overscan 열 수 = `48` (side varies) | 폐지된 `OVERSCNX`(레거시 32)와 **이름 분리** — 8.1절의 미정 해소 |
| `OVRSCNY` | **O** | amp 당 Y overscan 행 수 = `84` (frame-center side) | 폐지된 `OVERSCNY` 와 **이름 분리**. 84/84 분배는 OI-4 |
| `PAIRFILE` | **X** | 짝의 이름. **`FILENAME` 과 같은 형태(확장자 없음)** | converter 는 CLI 로 두 경로를 받으므로 읽지 않는다 —<br>**아카이브 도구용**. pair 가 충돌 시 함께 증가하므로 **항상 실명**이다.<br>**v1.9 미도입 — 규약으로 예측 가능하므로 생략(운영자)** |
| `PRESCNX` | **O** | amp 당 X prescan 열 수 = `0` (side varies) | 레거시 `PRESCANX` 의 **키워드 변경 계승**(운영자 확정 2026-08-22, 확인 요망 10 종결) —<br>`OVRSCNX`/`OVRSCNY` 확정 후 자리수를 맞춰 개칭. 동명이값(레거시 27 · 신규 0) 해소 겸.<br>합 불변식의 항: `AMPNAX1 = PRESCNX + IMAGEX + OVRSCNX`. 초안 v1.0 과 정합 |
| `PRESCNY` | **O** | amp 당 Y prescan 행 수 = `0` (frame-edge side) |  |
| `RAWPROD` | **X** | 이 파일이 CEU Archon science raw임을 선언 | MEF 는 `DATAPROD` 를 따로 만든다. `CAMVER` 등 instrument<br>카드가 정보 제공 — 중복 배제 (v1.9) |
| `RAWVER` | **X** | **raw 규격/geometry 버전.** 4장이 바뀌면 올린다 | **미도입 확정 (v1.13, 확인 요망 11 종결)** — 규격/구성 버전은<br>**`CAMVER`(HW) · `CTRLxCFG`(FW/설정) · `DETID` · `CHMAP_*`** 조합으로<br>전부 파악되므로 별도 카드가 중복이다(운영자, 2026-08-22) |
| `RDDIRB` | **X** | **BOT amp의 물리적 독출 진행 방향** | **v1.9: 헤더 생략 — 세부는 raw FITS spec 에 수록** (구 OI-3 보류) |
| `RDDIRT` | **X** | **TOP amp의 물리적 독출 진행 방향.** MEF amp header<br>`READDIR`로 전달 | MEF amp `READDIR` 로 가야 하는데 converter<br>가 하드코딩(C-12). **v1.9: 헤더 생략 — 세부는 raw FITS spec 에<br>수록** (구 OI-3 보류) |
| `ROWORDR` | **X** | **4.2절 행 순서 규약. 잘못 쓰면 TOP half가 Y 반전된다** | **v1.7: 카드 대신 규격의 포장 규범 조항으로 이관** — "raw 는<br>검출기 공간 순서로 완전 정렬 저장"을 요구사항으로 선언한다.<br>flat/star 시험(OI-3)은 준수 검증이 된다. 고정 대상은 `RAWVER` 미도입<br>확정(확인 요망 11)에 따라 **`CAMVER` + `CTRLxCFG`** — 포장 변경은<br>HW·설정 변경에서만 오므로 그 둘의 범프가 판별 신호다 (v1.13) |
| `TCSLIMIT` &nbsp;&nbsp; | **X** | — | TCS 설정값 — raw 헤더 삽입 대상 아님 |
| `TCSTIME` | **O** | TCS 시각계 선언 (`'UTC'`) — `TIMESYS`(ICS)와 분리, 초안 v0.3.5 | 직전 초안(v0.3.4)의 `TCSTSYS` 에서 개명 |
| `TELID` | **X** | ICS relay의 telescope ID | 전 시스템 고정값 — TCS/AUX relay 통신 규격에서만 필요 |
| `VMEA<n>` | **X** | `MEASURED` | 전압 텔레메트리는 `Cn_VOLT`/`Cn_CURR` 나열형으로 대체 (v1.9) |
| `VOLT<n>` | **X** | `VOLTNAME` | 〃 |
| `VOLTN` | **X** | — | 〃 |
| `VSET<n>` | **X** | `SETPOINT` | 〃 |
| `VSTA<n>` | **X** | — | 〃 |
| `VUNI<n>` | **X** | — | 〃 |
| `WALLBRD` | **O** | wallboard 온도 [degC] — HK 재구성 신설 (v1.8) | `ICG RTD measurement`. 초안 v0.3.4 의<br>`WALLBOAR`(단순 8자 절단형)에서 개명 |

> 이 표의 카드는 **converter 가 읽지 않으므로 이름을 틀려도 변환이 조용히 지나간다.** 3장 카드와 달리 MEF 에 `UNKNOWN` 조차 남지 않는다 — 어긋남이 드러나는 곳이 없다는 뜻이다. `OSCNPATT` · `ROWORDR` · `RDDIRT` · `RDDIRB` 처럼 **converter 하드코딩과 대조하라고 만든 선언**이 특히 그렇다 (변경점 C-5 · C-13).

## 8. 폐지된 레거시 카드 (17장)

**신규 raw 는 이 카드들을 싣지 않는다.** D-013 이 레거시 123개를 하나씩 판정해 101개는 이미 대응물이 있었고, 대응물이 없던 22개를 **계승 5 · 개칭 1 · 폐지 16** 으로 갈랐다. 여기에 규격 카드 `UT` 하나가 함께 폐지됐다.

> `DETID` 처럼 **레거시 헤더에는 있는데 3장에도 6장에도 없는 카드**를 찾았다면 여기에 있다. 빠뜨린 것이 아니라 **폐지된 것**이다.

| 폐지 카드 | 폐지 근거 | 대신 보는 것 |
| --- | --- | --- |
| `DETID` — **철회, 3.1 로 계승** | 파일 1개 = CCD 1개 전제의 카드. 신규는 파일 1개에 chip 2개다 | `CTRLTAG` · `CHIPS` · `CHIP1` · `CHIP2` (더 정확하다) |
| `OVERSCNY` — **구 이름 계승을 철회 (폐지 확정 재확인, 확인 요망 7 종결)** | ⚠️ **이름을 물려주면 자료가 깎인다.** 레거시는 Y overscan 이 `0`(없음)이었고 있었다면 **가장자리**를 뜻했다. 신규는 Y overscan 이 **영상 중앙**에 있다(4.2절). `OVERSCNY=168`을 본 도구가 "위쪽 168행 자르기"를 하면 active 픽셀을 지운다 | `MIDOVSCY` · `MIDOSCB` · `MIDOSCT` (위치가 이름에 들어 있다) |
| `READOUT` (`'ARLBRL'`) | 8-amp CCD 의 amp 조합 부호. 64-amp 구조를 표현할 수 없다 | `READMODE`(`'64AMP'`) · `READARCH`(`'8STRIPx2END'`) · `OSCNPATT` |
| `GAINDL` | **레거시 4년치에서 값이 비어 있던 카드다**(`GAINDL / comment` 형태). 계승할 관례가 없다 | `ACFFILE` · `TIMCONF` · `TIMVER` 가 timing script 를 가리킨다 |
| `PIXITIME` | 〃 (같은 이유, 같은 자리) | 〃 |
| `DMAWAIT` | master IC 가 slave 의 DMA 설정을 기다리는 시간. Archon 에는 master/slave DMA 가 없다 | `READTIME` · `BUFNO` |
| `ICROLE` | `'MASTER'`/`'SLAVE'`. Archon 과학 컨트롤러 2대는 대등하고, 셔터는 ICS 가 AUX 로 직접 구동한다 | `CTRLID` · `CTRL<n>ID` |
| `CTCSOURC` | CTC(전하전송 보정) 계수의 출처. Archon 은 컨트롤러에서 CTC 를 하지 않는다 | (해당 없음) |
| `CTCFILE` | 〃 | `ACFFILE` 이 그 자리다 |
| `KBUILD` | CCD 별 IC 의 소프트웨어 빌드. CCD 별 IC 가 없어졌다. **다만 "모든 파일이 전체 전자부 상태를 안다"는 취지는 계승했다** — 5.5.0절 `CTRL<n>*` | `CTRL1FW` · `CTRL2FW` |
| `MBUILD` | 〃 | 〃 |
| `TBUILD` | 〃 | 〃 |
| `NBUILD` | 〃 | 〃 |
| `GBUILD` | 〃. guide 는 이 규격 범위 밖이고 `HEMODE` 로 구분한다 | 〃 |
| `RTD12` | **값도 주석도 없는 빈 카드**가 4년치 아카이브에 남아 있었다. RTD 채널 12 자리로 보이나 채워진 적이 없다 | (없음). 5.0절 "결측이면 카드를 넣지 않는다"가 이 사례를 막는다 |
| `INPUTFMT` | *"Format of file from which image was read"*. 프레임이 컨트롤러에서 TCP 로 직접 오므로 "읽어 들인 파일" 이 없다 | (해당 없음) |
| `UT` | **`DATE-OBS` 와 완전한 중복.** 레거시가 둘 다 실은 것은 `UT` 에 `TSHOPEN`(백분초)을 붙여 정밀도를 보태려던 것인데, `DATE-OBS` 를 밀리초까지 쓰기로 하면서 이유가 없어졌다 (2026-08-13 확정) | `DATE-OBS` (밀리초 포함). MEF `UT` 는 converter 가 `DATE-OBS` 날짜부 + `TSHOPEN` 으로 조립해 왔다 — ⚠️ **v1.8 에서 `TSHOPEN` 이 Raw Archon `X` 로 판정되어 이 조립 원천이 끊긴다** (3.2절 · MEF Impacts v0.3 C-항목) |

> ⚠️ **`OVERSCNY` 가 이 목록에서 가장 위험한 축이다.** 이름을 그대로 물려주면 **자료가 깎인다** — 레거시는 Y overscan 이 가장자리였고 신규는 영상 중앙이라(규격 4.2절), `OVERSCNY=168` 을 본 도구가 "위쪽 168행 자르기" 를 하면 active 픽셀을 지운다. 이름이 같아서 조용히 틀리는 부류다. **`OVRSCNY` 로 개명해 잘림을 방지했다(운영자 확정, v1.10)** — 이 개명과 위험 사유를 **raw FITS spec(V1) 에 명시하고, MEF ICD·converter 검토 문서(MEF Impacts)에도 수록한다.**

> ⚠️ **`DETID` 는 폐지가 철회됐다.** 파일 1개 = CCD 1개 전제가 무너진 것은 그대로지만, **값을 `MK`/`NT`(어느 컨트롤러의 파일인가)로 재정의**해 3.1 로 되살렸다. 폐지 근거는 옛 정의에 대한 것이므로 기록으로 남겨 둔다 — 같은 이름을 다른 뜻으로 쓰는 셈이라 **`NAMPS` · `OVERSCNX` 와 같은 부류의 위험**을 안는다(6장). MEF 목적지는 아직 `((TBD))` 다.

계승 5 · 개칭 1 은 D-013 폐지 대상이 아니어서 6장에 있다 — `DATASRC` `HEMODE` `LEDFLASH` `ICSBUILD` `NPHLINES` 와 `DSTEL`(→ **`DSTELALT`**). 그중 `HEMODE` · `NPHLINES` 는 v1.8 판정으로 신규 raw 가 싣지 않는다(6장 `X`).

### 8.1 이 검토에서 새로 폐지한 카드 (3장)

위 표는 **D-013 이 내린 판정**이고, 아래는 **이 검토에서 새로 내린 것**이다. 둘 다 근거가 같다 — *이름이 범위를 드러내지 않으면 조용히 틀린다.*

| 폐지 카드 | 폐지 근거 | 대신 보는 것 |
| --- | --- | --- |
| `NAMPS` | 레거시는 `8`(그 CCD 하나), 신규는 `64`(카메라 전체) — **이름은 같은데 세는 범위가 달라졌다.** 레거시를 아는 도구가 amp 수로 쓰면 조용히 8배 틀린다. `OVERSCNY` 를 폐지한 것과 같은 부류다 | **`NAMPDET`** (`16`, chip 당). 카메라 전체는 `NAMPDET × NCCD` 로 파생되므로 카드가 필요 없다 |
| `OVERSCNX` — **구 이름 계승을 철회 (폐지 확정 재확인, 확인 요망 7 종결)** | 레거시 실측 `32`, converter 상수 `48` — **이름은 같은데 값이 다르다.** 게다가 `X` 만 있고 중앙 Y overscan 을 담을 자리가 없어, 양방향 overscan 을 한 이름으로 표현하지 못한다(11.3 · 12.3) | **`OVRSCNX`/`OVRSCNY` 두 장 — v1.7 에서 확정** (X = amp 당 48 · Y = amp 당 84, frame-center side). 같은 이유로 `PRESCANX`(레거시 27 ↔ 신규 0)도 **`PRESCNX`** 로 개칭하고 `PRESCNY` 를 짝으로 신설했다(7장) |
| `AMPPCD` | *amplifiers per CCD* 의 축약인데 `AMPCCD` 오타로 읽힌다. 값 `16` 은 `NAMPDET` 과 **같은 것을 센다** | **`NAMPDET`** — `NAMPRAW` 와 이름 형태가 같아(`N`+`AMP`+범위) 한 계열로 읽힌다 |

**남는 것은 두 카드다.**

```text
NAMPDET =                   16 / Number of amplifiers in the detector
NAMPRAW =                   32 / Number of amplifiers in the raw FITS file
```

- **범위가 전치사구로 갈린다** — `in the detector` · `in the raw FITS file`. 레거시 `NAMPS` 의 comment 가 *Number of amplifiers in the detector* 였으므로 `NAMPDET` 은 **뜻을 그대로 잇고 이름만 바꾼 것**이다. 값이 `8`→`16` 인 것은 검출기가 바뀐 결과이지 뜻이 바뀐 것이 아니다.
- **이름 형태가 같아** (`N` + `AMP` + 범위) 헤더를 훑을 때 한 계열로 읽힌다. `AMPPCD` 는 이 규칙 밖이었다.
- `NAMPRAW = NAMPDET × 2` (파일당 chip 2개) — 규격의 불변식 `NAMPRAW = NXTILE × NEND` 와 같은 값을 다른 길로 확인한다.
- **카메라 전체(`64`)는 카드로 싣지 않는다** — `NAMPDET × NCCD` 로 파생되고, converter 는 이미 자기 상수 `64` 를 쓴다.

> ⚠️ **comment 를 넣으려면 취득 SW 를 먼저 고쳐야 한다.** `ics_sim` 은 헤더를 `dict` 로 넘기고 `fitsout._apply_header()` 가 `hdr[key] = val` 만 하므로 **지금은 모든 raw 카드의 comment 칸이 비어 있다.** 위 두 줄은 목표 형태이지 현재 출력이 아니다.

> **딸려오는 변경**: 규격 5.4(카드 정의) · 5.13(폐지 목록) · 불변식(`NAMPS = NCCD × AMPPCD` → `NAMPRAW = NAMPDET × 2`) · `ics_sim/ics_sim/rawhdr.py` 의 상수와 `tests/test_raw_header.py` 의 단언 두 줄. **converter 와 MEF 는 손대지 않는다** — raw 를 읽지 않기 때문이다.

### 8.2 v1.7 에서 새로 폐지한 카드 (2장)

파일명 충돌 처리를 `clash/` 격리에서 **번호 증가**로 바꾸면서 정체성 카드가 재편됐다 — **D-016 으로 등재 완료(2026-08-22)**, 상세는 통합 문서 `KMT_CEU_Raw_Rev_MEF_Impacts_and_Identity_v0.5.md` Part 2.

| 폐지 카드 | 폐지 근거 | 대신 보는 것 |
| --- | --- | --- |
| `UNIQNAME` (레거시 계승분) | "불변 정본 키"라는 뜻이 이탈했다 — 번호 증가 방식이 `FILENAME` 의 유일성을 구조로 보장하므로 잉여가 되고, 뜻이 두 번 흐른 이름에 세 번째 뜻을 얹지 않는다(D-013 원칙). ⚠️ converter 가 이 카드를 읽어 MEF `UNIQNAME` 으로 옮기므로(`v2_1.py:405`) **폐지 후 MEF 가 빈 문자열을 받는다** — C-항목으로 LEECU 이관 (MEF Impacts 문서 1장) | **`FILENAME`**(실명 · 아카이브 유일 키) + **`ORIGNAME`**(카운터가 처음 배정한 이름, 항상 기록) |
| `NAMECLSH` (규격 v1.2 신설분) | 충돌 신호가 카드 존재에서 **값 비교**로 이동했다 | `FILENAME` 의 `DETID` 필드를 뗀 값 ≠ `EXPID` 가 곧 충돌 신호 (v1.6 — 구 `ORIGNAME`). `EXPID` 결측은 헤더 결함으로 분류 |

`clash/` 격리 디렉토리와 `.clash<UTC>` 접미사, "PAIRFILE 은 명목 이름으로 열화될 수 있다" 조항도 함께 폐지된다. ics_sim 의 RETIRED(부활 금지) 목록에 `UNIQNAME`·`NAMECLSH` 를 추가해야 한다.

## 9. 레거시 123개 전량 귀속

레거시 raw 실측본의 keyword 가 **하나도 빠짐없이** 어딘가에 귀속되는지 확인한 표다. 이 문서를 읽다가 *"이 카드는 어디 갔지"* 가 나오면 여기서 찾는다.

| 어디로 갔나 | 개수 | 어느 장 |
| --- | ---: | --- |
| converter 가 읽는다 | **78** | 3장 · 4장 |
| 구조 카드 — `hval()` 로 읽는다 | **5** | 5장 |
| converter 가 읽지 않는다 | **22** | 6장 |
| 폐지됐다 | **18** | 8장 — D-013 이 17, 8.1절이 `NAMPS` |
| **합계** | **123** | |

레거시에 없던 카드는 이 표 밖이다 — converter 가 읽는 26개는 3장에 `X` 로, 도입 후보·확정 63장은 7장에 있다.

> 이 귀속은 **converter 동작 기준**이라 v1.7 이후에도 변하지 않는다. `UNIQNAME` 처럼 Raw Archon 축에서 폐지된 카드(8.2절)도 converter 가 여전히 읽으므로 "converter 가 읽는다 78" 에 남는다 — 두 축을 섞지 말 것.

## 10. subframe · ROI · window 독출 — 지금 규격에 자리가 없다

**전면 독출만 전제하고 있다.** raw pair 규격에도, 미결 목록(OI-*)에도 부분 독출 얘기가 없다 — binning 이 OI-5 로 열려 있을 뿐이다. 레거시도 사정이 비슷했다: 카메라 IC 에는 `ROI` 명령이 실제로 구현돼 있었지만 **ICS 명령 테이블에는 아예 없어** 운영에서 쓰이지 않았고, ROI 산출물은 조각을 모자이크로 재구성한 **별도 combination 파일**로 만들었다(`KMTNc.20210503.030331`, `1616 x 1616`).

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
| **converter 가 geometry 를 상수로 갖고 있다** | `OVERSCAN_X=48` · `PRESCAN_X=0` · amp `1200 x 4616` 이 전부 소스 상수다(6장). **창을 읽어도 무시하고 상수로 계산하므로 `DETSEC` 이 조용히 틀린다.** OI-5 는 binning 에 대해 *"`NAXIS` 가 바뀌면 converter 가 즉시 실패한다"* 고 적었는데, **부분 독출은 그보다 나쁘다 — 실패하지 않고 틀린 좌표를 만들 수 있다** |

### 10.3 raw 에 필요한 최소 카드 (제안)

| 카드 | 값 | 왜 |
| --- | --- | --- |
| `ROIMODE` 같은 선언 | `FULL` / `WINDOW` | **창 모드인지가 먼저 드러나야 한다.** 없으면 소비자가 전면 독출로 가정한다 — 5.0절 sentinel 규약과 같은 취지다 |
| `DETSEC` | `[x1:x2,y1:y2]` | 검출기 상의 창 위치. 관례 그대로 쓴다 |
| `CCDSUM` | `'1 1'` | binning. OI-5 와 묶인다 |
| amp 별 분해 | 창이 amp 경계를 가로지를 때 | **파일 1개에 chip 2 · amp 32** 이므로 창 하나가 여러 amp 에 걸치면 amp 마다 `DETSEC` 이 달라지고 아예 읽히지 않는 amp 도 생긴다 |

마지막 줄이 가장 까다롭다. 레거시가 ROI 산출물을 **모자이크로 재구성한 별도 파일**로 만든 것도 아마 이 복잡함 때문일 것이다 — 64-amp 구조에서는 그 부담이 더 크다.

> **이 절은 규격이 아니라 제기다.** 부분 독출을 쓸 계획이 있는지부터 정해야 하고, 쓴다면 **미결 항목(OI-*)으로 세워** binning(OI-5) 과 함께 다루는 것이 맞다. 지금은 규격에도 미결 목록에도 자리가 없어서, **아무도 결정하지 않은 채로 남아 있다.**

## 11. converter 가 만들어 쓰는 카드

**converter 는 raw 의 geometry 선언을 하나도 읽지 않는다**(3~5장에 raw 읽기 목록이 있고 geometry 는 거기에 없다). 대신 **소스 상수와 amp 번호에서 계산해** L0 MEF 에 내보낸다. 이 장은 그 값들이다 — raw 가 다른 값을 실어도 converter 는 아래를 쓴다.

### 11.1 전역 상수에서 만드는 카드 (PRIMARY)

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

카드로 나가지 않는 내부 상수: `CCD_COLS=9216` · `CCD_ROWS=9232` · `ACTIVE_HALF_ROWS=4616` · `PIX_SIZE=10.0` · `PIX_SCALE=0.395`

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
| `MODULE` | `1 + (amp-1)//8` | `1` / `2` ⚠️ |
| `CHANNEL` | `1 + (amp-1)%8` | `1` / `5` ⚠️ |
| `XTALKGROUP` | `C{1 if chip in MK else 2}M{1+(amp-1)//8}` | `C1M1` / `C1M2` |

> ⚠️ 표시 셋은 **소스가 스스로 잠정이라 밝힌 값**이다. `READDIR` 은 comment 가 `placeholder` 이고(OI-3), `MODULE`·`CHANNEL` 은 주석이 `placeholder` 라 적혀 있다. **세부 내용, 앰프별 배치 및 방향은 raw spec 4.5절(Amp 전수 표)을 참조한다** — 그 표와 기계 정본 `Detector_Ch_to_AmpID_Map_v1.1.txt` 가 대응을 관리한다(C-11).

### 11.3 구간 카드 — 좌우 overscan 이 갈린다

converter 는 `is_bias_right(amp) = (1<=amp<=4) or (9<=amp<=12)` 로 좌우를 가른다. **raw 의 `OSCNPATT` 를 코드로 재현한 것이고 raw 를 읽지는 않는다.**

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

### 11.4 raw 와 이름이 겹치는 11개

아래는 **raw 도 싣고 converter 도 만드는** 카드다. 같은 값이어야 하지만 **아무도 대조하지 않는다** — converter 가 raw 를 읽지 않기 때문이다. 변경점 **C-5 · C-13** 이 이 대조를 붙이는 일이다.

`RAWXTILE` · `AMPDATA` · `PRESCANX` · `MIDOVSCY` · `NSTRIP` · `NEND` · `DETSIZE` · `COLGAP` · `ROWGAP` · `CHIPFLP` · `STRIPDIR` · `CTRLID`

> **`OVERSCNX` 는 이 목록에서 빠졌다** — 8.1 절이 raw 쪽 이름을 **`OVRSCNX`** 로 바꿨기 때문이다(v1.7 확정). converter 는 여전히 MEF 에 `OVERSCNX` 를 내보내므로 **raw 와 MEF 의 이름이 갈린다.** 같은 부류의 갈림이 v1.7 에서 늘었다 — raw `AMPNAX1` ↔ MEF `RAWXTILE`, raw `IMAGEX` ↔ MEF `AMPDATA`, raw `PRESCNX` ↔ MEF `PRESCANX`. converter 가 raw 를 읽지 않으니 당장 깨지는 것은 없으나, C-5 의 대조를 붙일 때 **이름 대응을 명시해야 한다** (대응표: MEF Impacts 문서 2장).

## 12. raw FITS 를 직접 쓰는 사람에게

converter 를 거치지 않고 **raw pair 를 그대로 다루는 경우**를 위한 장이다. 11장이 *MEF 에 무엇이 들어가나* 라면, 여기는 *raw 만 가진 사람이 무엇을 알 수 있고 무엇을 직접 해야 하나* 다.

### 12.1 raw 헤더가 주는 것

geometry 를 재구성할 재료는 **raw 헤더 안에 다 있다** — 11.1 의 값들이 raw 에도 실리되, v1.7 부터 **일부 이름이 갈린다**(11.4 · MEF Impacts 문서 2장의 대응표). 여기에 raw 에만 있는 배치 선언이 더해진다:

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

11장의 카드 중 **23개는 MEF 전용**이라 raw 에 없다:

`STRIPID` `ENDID` `EXTNAME` `AMPNAME` `AMPID` `AMPSEQ` `CHIPID` `READDIR` `MODULE` `CHANNEL` `XTALKGROUP` `CHIPLIST` `RAWGROUP` `DATASEC` `BIASSEC` `PRESEC` `TRIMSEC` `CCDSEC` `DETSEC` `AMPSEC` `RAWFILE` `RAWDATA` `RAWBIAS`

**amp 하나를 raw 에서 꺼내는 절차**는 이렇다 (chip 안 amp 번호 `a` = 1~16). ⚠️ v1.9 부터 `OSCNPATT` 는 **카드가 아니다**(7장 `X`) — 아래 `OSCNPATT[strip-1]` 은 규격이 조항·전수 표로 정의할 strip 별 overscan 좌우 패턴(`RRRRLLLL`)을 뜻하는 기호다:

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
| **배선** | `MODULE`/`CHANNEL` 은 converter 의 추정식이고, raw 의 **`CHMAP_LT/LB/RT/RB`**(구 `AMOD`/`ACHN` 대체)가 실제 CCD 출력 채널을 싣는다 — **converter 가 이 카드에서 채우도록 개정 대상**(C-11). **세부 내용, 앰프별 배치 및 방향은 raw spec 4.5절(Amp 전수 표)을 참조한다.** Archon module/channel 은 그 다음 단이다 |
| **중앙 overscan** | raw 에는 있고 **L0 MEF 에는 없다.** bias jump·전하 잔류 진단에 쓰려면 **raw 를 보관해야 한다** |
| **`OSCNPATT` 를 바꾸면 MEF 가 틀린다** | converter 가 이 카드를 읽지 않고 `is_bias_right()` 하드코딩을 쓰므로, raw 선언만 바꾸면 **오류 없이 어긋난다** |
| **부분 독출** | 10장 참조. 규격에 자리가 없다 |

## 13. 종합

- **기본값이 거의 전부 `""` 나 `"UNKNOWN"` 이다.** 카드가 없어도 변환은 성공하고, **L0 MEF 에 빈 문자열이 조용히 들어간다.**
- **오류로 걸리는 것은 `OBSERVAT` 하나**(파일명 교차 검증)다. 나머지는 전부 조용히 지나간다.
- 조용히 **틀린 값**이 들어가는 쪽이 더 위험하다 — `DATE-OBS`(변환 시각) · `RA`/`DEC`(그럴듯한 좌표) · `EXPTIME`/`DARKTIME`(0초) · 버전 문자열(그럴듯한 provenance).
- **HK 블록은 v1.8 에서 재구성됐다** — `CCDTEMP` 실측 대표 전환 · `DEWPRES` 문자열 `x.xxe-x` + sentinel `9.99e-9` · 신설 `DMPTEMP`/`WALLBRD`/`HEBOX` · 출처 3계통(3.7절). `DARKTIME` · `TSHOPEN` · `TSHSHUT` · `HEMODE` · `NPHLINES` · `CHSTAT` 는 신규 raw 가 싣지 않는다 — `TSHOPEN` 폐지의 MEF `UT` 파급은 C-항목이다(3.2절).
- **v1.10 으로 도입 판정이 완결됐고, v1.11~v1.13 으로 확인 요망 11건이 전량 종결됐으며, 충돌·정체성 결정이 D-016 으로 등재됐다** — 3장·6장 계획 열과 7장 도입 여부에 빈칸이 없고, 어긋남 목록도 비었다. **V1 재작성 착수 조건이 완성됐다.**
- **HK 블록의 형 논쟁은 v1.12 로 닫혔다** — 온도·습도 전 카드 문자열(레거시 계승), sentinel `'-999.99'` 단일값, `DEWPRES` 만 `9.99e-9`. 남은 것은 `ics_sim` 의 실수형→문자열 전환(구현 일감)과 Radionode 원값 포맷 확인이다.
- **이름은 같은데 뜻이 달라진 카드 문제는 v1.7 개칭으로 닫혔다** — `OVERSCNX`→`OVRSCNX` · `PRESCANX`→`PRESCNX` · `OVERSCNY`→`OVRSCNY`(뜻 재정의 겸 개명) · `NAMPS` 폐지(8.1절). **`READMODE`** 의 값 충돌(`FAST` vs `64AMP`)은 v1.9 에서 raw `RDMODE` / MEF `READMODE` 로 **이름을 분리해 종결**했다(7장) — 남은 동명이의는 **`DETID`** 하나다(뜻 재정의 유지 — 3.1 comment 가 새 뜻을 명시).
- **`UNIQNAME` 은 폐지됐다**(8.2절) — 정체성은 `FILENAME`(유일 키) + `EXPID`(항상 기록, 불일치 = 충돌 신호. v1.6 — 구 `ORIGNAME`)가 담당한다. ⚠️ converter 가 `UNIQNAME` 을 읽어 MEF 로 옮기므로 C-항목 처리 전까지 MEF `UNIQNAME` 이 빈 문자열이 된다.
- **`OBSERVAT` 는 현행 체계 그대로 확정됐다**(`TESTBED`/`CTIO`/`SAAO`/`SSO` — 3.1절) — converter 교차검증과 완전 정합, 개정 불요. `ORIGIN` 은 "파일이 생성된 곳"(raw=관측소·테스트베드는 KASI, 파이프라인 산출물=KASI) — MEF `ORIGIN` 을 복사에서 상수 `'KASI'` 로 바꾸는 경미 C-항목만 남는다.
- `X` 중 **`XTALKVER` · `REFVER` · `CATVER` 셋은 결함이 아니다** — 규격 5.12 가 calibration DB 소관으로 정리했고 변경점 C-14 가 caldb 주입으로 바꾼다.
- **7장 63장은 어긋나도 드러나지 않는다** — converter 가 읽지 않으므로 MEF 에 흔적이 남지 않는다. 확정(`O`) 카드도 converter 쪽 대조(C-5/C-11/C-13)가 붙기 전까지는 같은 처지다.
- **부분 독출(subframe · ROI · window)은 규격에도 미결 목록에도 없다** — 10장. 지원한다면 `DETSEC` · `DATASEC` · `CCDSUM` 이 최소이고, converter 가 geometry 를 상수로 갖고 있어 **틀려도 드러나지 않는다.**
- **converter 는 raw 의 geometry 를 하나도 읽지 않는다**(11장). 겹치는 11개는 같은 값이어야 하지만 **대조하는 코드가 없다**(C-5·C-13).
- **raw 만 쓰는 사람에게는 amp 이름·번호·구간 23개가 없다** — 12.2 의 절차로 직접 계산해야 한다.
- 그룹별 주의사항은 **각 표 아래**에 붙였다.

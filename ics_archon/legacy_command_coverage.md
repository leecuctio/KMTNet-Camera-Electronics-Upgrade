# 레거시 명령 전수 대조 — ICS / ICG

> **무엇인가.** 레거시 ICIMACS 의 ICS·ICG(+IC·CB) 명령을 전수로 뽑아, 현행
> `ics_archon`/`icg_archon` 구현과 하나씩 맞춘 표다.  운영자 물음이 출발점이다 —
> *"원래 Legacy ICG에 있던 명령어(예를 들면 go)들도 다 구현해야되.  ICS_archon은
> legacy ICS의 명령어 거의 구현되어 있지?  몇개는 일부러 뺐고 나머지는 거의 구현되어
> 있어야 해."*
>
> **작성 2026-09-06** (`ics-archon-v1.0-build`).  경위·판단은 [`DevNote.md`](DevNote.md),
> 시험 절차는 [`bench_test_plan.md`](bench_test_plan.md).

## 어떻게 만들었나

세 표를 따로 뽑아 맞춘 뒤 **반증**을 한 번 더 거쳤다.

| 단계 | 원천 |
|---|---|
| 레거시 ICS | [`../ics_legacy/ics_legacy_report.md`](../ics_legacy/ics_legacy_report.md) 3·4·5절 + `__dts_legacy/` 원본 C 소스 + `IC_commands_R20220302.pdf` |
| 레거시 ICG | [`../ics_legacy/icg_legacy_report.md`](../ics_legacy/icg_legacy_report.md) 7·9절 + `__sample_isislog/` 실측 (⚠️ ICG 는 **자체 문서·소스가 없어 XIS 로그가 유일한 근거**다) |
| 현행 구현 | `ics_sim/ics_sim/commands.py`(기반) + `ics_archon/ics_archon/app.py` + `ics_archon/icg_archon/commands.py` |

⭐ **판정선은 핸들러 유무다** — 디스패처가 `getattr(self, 'cmd_<낱말>')` 로 찾고
(`ics_sim/ics_sim/commands.py:103`) 없으면 `Didn't understand … ?` 로 거절한다.
그래서 *"어휘에 등록됐다"* 와 *"핸들러가 있다"* 를 갈라 봤고, **어긋난 자리는 0건**이었다.

⭐ **remote 와 console 을 나누지 않는다** — `Console.feed()` 가 입력을
`<ICS>><ICS> EXEC: <입력>` 으로 만들어 remote 와 **같은 디스패처**로 넘기므로
(`ics_sim/ics_sim/console.py:77-93`), 판정 기준은 *"어느 쪽에서 되나"* 가 아니라
**"명령표에 등록됐나"** 다.  ⚠️ 예외는 `feed()` 가 디스패치 **전에** 채가는 넷뿐이다
(`quit`·`exit`·`help`·`?`) — 아래 "console 전용" 절.

## 판정 어휘

| 낱말 | 뜻 |
|---|---|
| **구현됨** | 현행에 같은 뜻의 핸들러가 있다 (이름이 달라도 된다) |
| **신설** | 레거시에 없던 것을 새로 만들었다 |
| **일부러 뺐다** | 없는데 **폐지 근거가 문서에 있다** (근거를 노트에 인용) |
| **미구현** | 없고 폐지 근거도 못 찾았다.  ⚠️ *"일부러 뺐겠지"* 로 추측하지 않았다 |
| **레거시도 미구현** | 레거시에서도 이름만 있고 안 돌던 것 |

## 집계

| 판정 | 수 |
|---|---:|
| 구현됨 | **42** |
| 신설 | **8** |
| 일부러 뺐다 | **17** |
| 미구현 | **64** |
| 기타 | **3** |
| **합계** | **134** |

추출 원표: 레거시 ICS **143** · 레거시 ICG **47** · 현행 구현 **66**.

⭐ **미구현 64 의 대부분은 되살릴 것이 아니다** — `+LOG`/`-LOG`·`BIOSDISKREAD`·
`COMTEST`·`FINDHOST`·`SETBUFFER` 처럼 **VDOS 시절 진단 명령**이거나,
`EXPO`/`GEXPO`/`EXPTIME`/`STD` 처럼 **이미 있는 명령의 별칭**이다.  실제로 검토할 만한
것은 FITS 헤더 항목 계열(`PROPID`·`PI_NAME`·`PI-COI`·`TELOPS`·`COMMENT`)과
`RECOVER`·`SAVECONFIG` 정도다.

## console 전용 — 운영자 지시에 대한 답

> *"legacy에서 console 전용으로 되어 있던 것은 ics_archon/icg_archon에서도 console
> 전용으로 해줘."*

**이미 그렇게 돼 있다.**

| 명령 | 레거시 | 현행 |
|---|---|---|
| `QUIT` · `EXIT` | console 전용 | ✅ console 전용 — `console.py:66-71` 이 디스패치 전에 채간다 |
| `HELP` · `?` | console 전용 | ✅ console 전용 — 〃 |

레거시의 나머지 console 전용 일가(`HISTORY`·`INFO`·`CBSTATUS`·`+ARCHIVE`·`+AUTOLOG`
…)는 **Caliban(CB) 프로세스의 것**인데, 신규는 CB 를 `ICS` 안으로 흡수해(9노드 통합)
그 프로세스 자체가 없다.  **그래서 추가로 console 전용으로 만들 것이 없다.**

⚠️ **다만 그 축소를 결정한 기록이 문서에 없었다** (`grep` 0건) — 이 문서가 그 기록이다.

---

## 구현됨 (42)

| 명령 | 노드 | 인자 | 용도 | 노트 (이유·근거) |
|---|---|---|---|---|
| **(판정 기준)** | 공통 | - | 핸들러 유무가 판정선 — 이름으로 getattr 해서 cmd_* 가 있으면 되고 없으면 거절 | 구현됨 — 원안 그대로 맞아. [검증: `grep -rn "def cmd_" --include=*.py` 워크트리 전수 재실행. 기반 29(ics_sim/ics_sim/commands.py) + ics_archon 7(app.py) + icg_archon 16(commands.py) = 원안과 한 개도 안 어긋나. impv2.py:107 `def cmd_is` 는 Message 메서드라 디스패처 표가 아니고, tools/scan_legacy_logs.py:97 `cmd_slot` 은 접두가 달라. 상속도 확인 — ics_archon/ics_archon/app.py:163 `class IcsDispatcher(Dispatcher)` · icg_archon/commands.py:131 `class IcgDispatcher(sim_commands.Dispatcher)`. 벤더본은 `diff -rq ics_sim/ics_sim/ ics_archon/ics_archon/_vendor/ics_sim/` 결과 __pycache__/.pytest_cache 말고 차이 0건이라 판정 무영향] |
| **>NODE <명령>** | console 전용 문법 | `>K.IC status` | 콘솔에서 **우리 프로그램이 담당하는** 내부 노드를 골라 넘기는 문법 | 구현됨 — 판정은 맞는데 ⛔ **purpose 설명이 틀렸어. '특정 노드로 보내기' 가 아니야.** [검증: console.py:77-93 전문 열람. 조립한 줄은 **와이어로 안 나가** — `dispatch.handle()` 을 프로세스 안에서 직접 부를 뿐이야. 게다가 :90-92 가 목적지를 `router.resolve()` 로 풀어 `is_ours` 가 아니면 **거절하고 끝내**. `Target.is_ours`(nodes.py:49-51)는 ICS·IC·CB 뿐이라 `>XIS HOSTS`·`>TC AUXSTATUS`·`>ICG VACGAUGE OFF` 는 전부 *"담당하는 노드가 아닙니다"* 로 막혀. ⭐ 그러니 원안의 *"remote 로 임의 발신을 시킬 수 없다"* 는 **약한 서술이고, 사실은 console 로도 임의 발신을 못 해** — 레거시 CB 의 `>{host} {msg}` 능력은 재현되지 않았어. 이게 위 `HOSTS`·`TIME` 항목이 막히는 이유이기도 해] |
| **ABORT** | ICS·ICG | 없음 | 취득 전체 중지 (독출·저장 안 함) | 구현됨 — 원안 맞아. [검증: 531-550 본문·docstring 직접 열람. 레거시 PAP7KX.CMD:291-302 분기 인용과 거부 문구 일치, 저장 태스크 정리·시퀀서의 `DONE: EXPSTATUS=IDLE` 설명도 docstring 그대로]. ⚠️ 원안에 없던 것 하나 — 이 명령은 **콘솔 도움말에 안 나와**(아래 `help / ?` 항목) |
| **ACQSTATUS** | ICS·ICG | 없음 | IC 들의 연결·초기화 상태를 한 줄로 집계 | 구현됨 — 원안 맞아, ICS/ICG 분기 재현 주장까지 확인했어. [검증: ics_archon/ics_archon.ini:36 `ic_ids = K.IC, M.IC, T.IC, N.IC`(4대) · ics_archon/icg_archon.ini:12 `ic_ids = G.IC`(1대) 둘 다 열어 대조]. ⚠️ 값이 늘 `READY` 고정이라 실제 상태를 안 묻는 것도 :187 그대로 맞아 |
| **AUXSTATUS** | ICS·ICG (발신 전용) | - | 보조 장비(필터·초점·환경) 텔레메트리 질의 → IC 중계 | 구현됨(발신) — 원안 맞아, 줄번호도 정확해. [검증: sequencer.py:292-332 열람 — :297 aux_query 를 국면 1 에서 먼저 띄우고 `await asyncio.sleep(0)` 로 실제 발신 순서를 맞춰. ICG 는 icg_archon/sequencer.py:248-249 에서 aux·tcs 를 `backend.prepare()` **앞에** 나란히 띄워 원안 서술대로야]. ⚠️ 위 TCSSTATUS 와 같은 정정 — TC 의 답은 `DONE:` 이고 app.py:311-314 가 가로채, `STATUS:` 는 우리가 IC 들에게 뿌리는 중계 방향이야 |
| **BIAS** | ICS·ICG | `BIAS [<objname>]` | IMAGETYP=BIAS 설정 | 구현됨 — 원안 맞아. [검증: icg_archon/commands.py:140-161 열어 확인. `keep = st.exptime` → `super()._image_type(...)` → `if st.exptime != keep: st.exptime = keep`(:154-160). docstring 이 이유도 적어 뒀어 — guide 의 EXPTIME 은 독출 개시 간격이라 0 이면 `go` 가 거부되고 `EXP` 로 되돌릴 수도 없어 가이딩이 잠긴다] |
| **DARK** | ICS·ICG | `DARK [<objname>]` | IMAGETYP=DARK 설정 | 구현됨 — 원안 맞아. [검증: :314-315] |
| **DATASOURCE** | ICS·ICG·IC | `DATASOURCE [ADC\|CTC\|SIM]` | onboard crosstalk 보정 경로 선택 | 구현됨 — 원안 맞아. [검증: 363-384 본문 열람. 세 값 매핑과 거부 문구 `Invalid selection for DataSource. ADC, CTC, and SIM are valid.` 확인]. ICG 가 sim 스텁 위에서 돈다는 단서도 맞아 — ics_archon/icg_archon/app.py:52 `cfg.hardware.backend = 'sim'` · :57-60 `self.guide = GuideBackend(...)` 직접 확인 |
| **DMAWAIT** | IC (ICS·ICG 주소로도 받음) | `DMAWAIT [<정수>]` | 광케이블 통신 지연 조회·설정 | 구현됨 — 원안 맞아. [검증: :351-361]. 덤: ics_legacy/IC_commands_R20220302.pdf 본문에 `DMAWAIT` 8회 나와 IC 전용 낱말이라는 분류가 문서로도 뒷받침돼 |
| **DOMEFLAT** | ICS·ICG | `DOMEFLAT [<objname>]` | IMAGETYP=DOMEFLAT 설정 | 구현됨 — 원안 맞아. [검증: :326-327] |
| **DONE:** | 공통 | `<본문>` | IMPv2 완료 응답 수신 처리 (메시지 타입) | 구현됨 — 원안 맞아. [검증: impv2.py:40 · app.py:326-352 전 구간 열람. 보고 갈래는 :349-352 `log.info('보고 수신 (조치 없음) -- …')` 로 끝나 어떤 경우에도 답을 안 보내]. ⭐ 원안에 없던 사실: **실제로 등록된 조치는 딱 둘** — ics_archon/ics_archon/app.py:572-573 `for word in ('HK','HKDATA'): self.register_report('DONE', word, self._on_hkdata)`. 워크트리 전체에서 `register_report` 호출은 이 한 자리뿐이라, ICG 쪽은 등록된 조치가 0개야 |
| **ERASE** | ICS·ICG·IC | 없음 | CCD flushing (master 채널에서만) | 구현됨 — 원안 맞아. [검증: 400-409 전문 열람. ICG 의 sim 스텁 경고도 icg_archon/app.py:52 로 확인] |
| **ERROR:** | 공통 | `<본문>` | IMPv2 에러 알림 수신 처리 (메시지 타입) | 구현됨 — 원안 맞아. [검증: 위 DONE: 과 같은 구간]. ⭐ 덧붙일 것: ics_archon 은 ICG 의 `ERROR:` 를 **_on_message 에서 따로 엿들어** 게이지·노출잠금 데드맨을 푼다(ics_archon/ics_archon/app.py:653-667 `for ctl, word in ((self.gauge, GAUGE_CMD), (self.guideexp, GUIEXP_CMD)) … ctl.note_reply(msg.raw)`) — 명령 처리부가 아니라 수신 훅이야 |
| **EXEC:** | 공통 | `<명령문>` | 콘솔 입력을 명령으로 넘기는 메시지 타입 | 구현됨 — 원안 맞아. remote·console 을 같은 표로 모으는 이음매가 이거라는 것도 확인했어. [검증: console.py:77-93 전문 + app.py:326-328]. ⚠️ 다만 콘솔 입력은 `app._on_message` 를 **안 지나고** `dispatch.handle` 을 직접 불러(console.py:93) — 자기 에코 걸러내기·브로드캐스트 중복 제거가 안 걸리는 경로야 |
| **EXP** | ICS·ICG | `EXP [<초>]` | 노출시간(EXPTIME) 조회·설정 | 구현됨 — 원안 맞고 ICS·ICG 갈림도 확인했어. [검증: icg_archon/commands.py:163-171 전문 열람 — BIAS 가드가 정말 없고 `if arg: st.exptime = float(arg)` 뒤 곧장 `Reply.done('EXP', 'ExpTime=%g seconds.' % st.exptime)`. docstring 이 `_image_type` 과 같은 이유라고 명시] |
| **EXPNUM** | ICS·ICG | `EXPNUM [<n>]` | 파일 일련번호 조회·설정 | 구현됨 — 원안 맞아. [검증: 215-249 전문 열람. docstring 이 OBSAgent 가 `Filename=` 뒤 **정확히 15자**를 잘라 쓴다는 것과 D-018 이 D-016 상한 `099999` 를 대체했다는 것까지 적어 뒀어. 6자리 통일 서술도 그대로] |
| **FATAL:** | 공통 | `<본문>` | IMPv2 치명 오류 알림 수신 처리 (메시지 타입) | 구현됨(수신) — 원안 맞아. [검증: MSG_TYPES 에 `'FATAL:'` 있음 확인]. 발신 대응물 없다는 것도 grep 으로 확인 — UDP 전환으로 UART 버퍼 폭주 상황 자체가 사라졌어 |
| **FILENAME** | ICS·ICG·IC | 없음 | 현재 설정된 저장 파일이름 반환 | 구현됨 — 원안 맞아. [검증: 207-214 전문 열람] |
| **FLASHNOW** | IC (ICS·ICG 주소로도 받음) | `FLASHNOW [<ms>]` | 점검용 LED 를 n ms 즉시 점등 | 구현됨 — 원안 맞아. [검증: 443-459 전문. 문서 쪽에도 `FLASHNOW` 7회] |
| **FLAT** | ICS·ICG | `FLAT [<objname>]` | IMAGETYP=FLAT 설정 | 구현됨 — 원안 맞아. [검증: :320-321] |
| **GO** | ICS·ICG | `GO [<장수>]` | 노출 개시 | 구현됨 — 원안의 3층 구조 서술 전부 확인했어. [검증: 층1 commands.py:462-482 전문(`count = max(1, int(arg))`, 인자 없으면 1장, `self.app.seq.start(count, msg.src)`). 층2 ics_archon/app.py:207-215 — `bad = self._inflight_reply('GO')` 를 **게이지보다 먼저** 두고 그 뒤 `gauge.before_exposure()`, 그다음 `super().cmd_go(...)`. 층3 icg_archon/commands.py:311-331 — `flag.allowed` 검사(:325-326) → `_op_in_flight` 검사(:327-329) → `super()`]. ⭐ 원안이 안 적은 층2 세부: GO 가 거절됐는데 취득 중이 아니면 게이지 되켜기 타이머를 자가 치유로 건다(app.py:219-231) |
| **GO (ICG 수신)** | ICG | `GO [<장수>]` | 가이드 노출 사이클 개시 | 구현됨 — 원안 맞아. [검증: icg_archon/commands.py:308-331 전문 + 기반 commands.py:462-482 전문 열람. 인자 없으면 `count = 1` 이 맞아서 *"레거시 ABC 가 보내던 `abc>icg go` 그대로 동작한다"* 는 서술이 성립해. 검사를 `super()` 앞에 둔 이유도 docstring(:314-316)에 원안 그대로 적혀 있어] |
| **GUIDEEXP** | ICG (ICS 테이블에도 CASE) | `GUIDEEXP [<초>]` | 가이드 노출시간(독출 개시 간격) 조회·설정 | 구현됨(ICG) / 미구현(ICS) — 원안 맞아. [검증: 174-194 전문 열람. 음수 거부(:191-192)까지 있고 응답 문구 `GuideExp=<n> seconds.` 를 조회·설정 양쪽에서 똑같이 내. ICS 쪽은 핸들러 목록에 `cmd_guideexp` 가 없어 `Didn't understand` 가 맞아. 어휘도 확인 — `GUIDEEXP` 는 icg_archon/commands.py:95 ICG_COMMANDS 에만 있고 기반 KNOWN_COMMANDS 에는 없어] |
| **INITIALIZE** | ICS·ICG·IC | `INITIALIZE <suffix>` | 파일명 suffix 를 통째로 지정 | 구현됨(수신·발신) — 원안 맞아, 결합 지점이 의도적으로 남았다는 것까지 확인했어. [검증: commands.py:385-398 전문 + sequencer.py:304-307 `if cfg.behavior.send_guide_init and cfg.node.guide_ic_id: … self.emit.emit_req(cfg.node.guide_ic_id, 'INITIALIZE', st.guide_suffix)` + 두 ini 를 나란히 열람. ics_archon.ini:38 은 `guide_ic_id = G.IC`(주석에 *"INITIALIZE 만 보낸다"*), icg_archon.ini:15-17 은 `guide_ic_id =` 를 **비우고** 주석에 *"비워 둔다 -- 기본값 G.IC 를 지우지 않으면 라우터가 자기 IC 를 범위 밖 guide 로 무시한다"* 라고 적어 뒀어. nodes.py:63-65 가 `if cfg.guide_ic_id:` 일 때만 Role.GUIDE 를 등록하니 정확히 맞물려] |
| **LEDFLASH** | ICS·ICG·IC | `LEDFLASH [<ms>]` | 점검용 LED 점등시간 조회·설정 | 구현됨 — 원안 맞아. [검증: :283 핸들러 + :443-452 `cmd_flashnow` 가 인자 없으면 `self.state.ledflash_ms` 를 쓰는 것(:450)까지 확인해서 '값만 정하고 점등은 FLASHNOW' 해석이 맞아] |
| **OBJECT** | ICS·ICG | `OBJECT [<objname>]` | IMAGETYP=OBJECT 설정 + 대상 이름 | 구현됨 — 원안 맞아. [검증: :317-318] |
| **OBSERVER** | ICS·ICG | `OBSERVER [<이름 …>]` | 관측자 이름 조회·설정 (띄어쓰기 허용) | 구현됨 — 원안 맞아. [검증: :260-266] |
| **PING** | 공통 | 없음 | 생존 확인 — PONG 응답 | 구현됨 — 원안 맞아. [검증: 135-157 전문 + docstring 열람. *"대표로 하나만 답하면 ICS 만 재등록되고 나머지 8개는 영영 죽는다"* 가 그대로 적혀 있어. 등록 ID 는 nodes.py:89-92 `registered_ids` → `cfg.all_node_ids`] |
| **PING (ICG→XIS 능동 등록)** | ICG | 없음 | 허브에 자기 노드를 등록 | 구현됨 — 원안 맞아. [검증: app.py:229-251 전문 + docstring 열람(*"9개 ID 가 같은 (IP,port) 를 가리켜도 안전하다 -- 2026-08-04 에 XIS 서버 소스로 확인"*). `IcgArchon(IcsSim)` 상속이라 ICG 도 이 경로를 그대로 받아. icg_legacy_report.md:300 원문도 확인]. ⚠️ 다만 같은 :300 줄이 XIS 필수 인터페이스로 `TIME` **질의**도 함께 적어 뒀는데 그쪽은 발신 코드가 없어(위 TIME 항목) |
| **PONG** | 공통 | 없음 | PING 에 대한 응답 수신 | 구현됨 — 원안 맞아. [검증: :159-160] |
| **PROJID** | ICS·ICG | `PROJID [<id>]` | 관측 프로젝트 ID 조회·설정 | 구현됨 — 원안 맞아. [검증: :253-258] |
| **SHCLOSE** | ICS·ICG·IC | 없음 | 셔터 즉시 닫기 (강제 중단용) | 구현됨 — 원안 맞아. [검증: 434-441 전문 열람] |
| **SHOPEN** | ICS·ICG·IC | `SHOPEN <초> [<sourceID> USESTATUS]` | 셔터를 지정 시간만큼 개방 | 구현됨 — 원안 맞고 `USESTATUS` 지적도 정확해. [검증: 412-433 전문 열람. `parts = msg.body.split()` 뒤 `parts[0]`(초)와 `parts[1]`(sourceID)만 읽고 **`parts[2]` 는 어디서도 안 봐**. 늦은 응답 경로 `_do_shopen`(:427-433)이 `emit.ic_shutter_open` → sleep → `emit.ic_shutter_closed` 를 부르는데, 그 타입은 emitter 가 스스로 정해서 `USESTATUS` 스위치가 닿을 자리가 없어. 레거시와 어긋나는지 확인이 필요하다는 원안의 유보 그대로 남겨] |
| **SKY** | ICS·ICG | `SKY [<objname>]` | IMAGETYP=SKY 설정 | 구현됨 — 원안 맞아. [검증: :323-324] |
| **STATUS** | 공통 | 없음 \| `<n>` | 설정·상태 덤프 반환 | 구현됨 — 원안 맞고 두 ⚠️ 도 다 사실이야. [검증: 164-183 전문 열람. ① 인자는 `msg.body` 를 **한 번도 안 읽어** — `1` 이 와도 갈래가 안 갈려. ② ICS 본문에 `Build=` 가 없어(위 BUILD 항목). OBSAgent 가 `" STATUS"` 앞 공백을 본다는 docstring 도 :166-168 에 그대로 있어] |
| **STATUS:** | 공통 | `<본문>` | IMPv2 진행상황 알림 수신·발신 (메시지 타입) | 구현됨 — 원안 맞아. [검증: sequencer.py:821-833 `_relay_aux`/`_relay_tcs` 두 메서드 전문 열람, 인용 줄번호 825·832 정확. ⭐ 중요한 방향 구분 — 이 `STATUS:` 는 **우리가 우리 IC 노드들에게 헤더 재료를 뿌리는 중계**야(`ic_of(ccd)` 가 목적지). TC 에서 **오는** 답이 아니야 (아래 TCSSTATUS 항목에서 원안을 고침)] |
| **STATUS: GO / DONE: EXPSTATUS=IDLE (ICG→ABC 보고)** | ICG | `EXPSTATUS=<상태>` | 노출 진행 상태를 요청자에게 보고 | 구현됨 + 개선 — 원안 맞아, 줄번호도 정확해. [검증: icg_archon/sequencer.py:240-266 전문 열람 — :247 사이클 개시 보고, :252-259 `backend.prepare()` 실패 갈래가 `emit.error(source,'GO',...)` 뒤 `st.expstatus = ExpStatus.IDLE` · `self.emit.idle_done(source)` 로 **반드시 IDLE 을 내보내**, :264-265 INTEGRATING 전이 뒤 재발신. 레거시가 CB 에 미루느라 안 보내던 자리를 신규가 스스로 채운다는 서술 그대로야] |
| **STOP** | ICS·ICG | 없음 | integration 중지 후 readout/저장까지는 진행 | 구현됨 — 원안 맞아. [검증: 514-530 전문·docstring 열람, PAP7KX.CMD:279-290 분기 인용 확인]. ⚠️ 원안에 없던 미결 하나 — ics_sim/DevNote.md:2872 미해결 표에 *"`STOP`/`ABORT` 실물 재확인"* 이 **우선순위 중간으로 아직 열려 있어**: `DONE:` 본문은 실측 근거 없이 우리가 정한 문구라 실물 OBSAgent 로 확인해야 해. 그리고 이 명령도 콘솔 도움말에 없어 |
| **TIME** | 공통 | 없음 | OS/FITS 시각과 TIMESYS 반환 | 구현됨(수신) — 원안 맞아. [검증: :192-195]. ⚠️ 원안에 없던 반쪽 — **보내는 쪽은 없어.** icg_legacy_report.md:300 은 XIS 허브에 대한 필수 인터페이스로 *"노드 등록(PING), `TIME` 질의, PONG 응답"* 셋을 적었는데, `grep -rn "'TIME'"` 결과 발신 자리는 0건이고 emitter 에도 대응 메서드가 없어. `HOSTS` 와 같은 부류(우리가 물어봐야 하는데 물어볼 코드가 없음)야 |
| **WARNING:** | 공통 | `<본문>` | IMPv2 경고 알림 수신 (메시지 타입) | 구현됨 — 원안 맞아. 레거시 99개에 없던 것을 신규가 채운 자리라는 서술도 표와 대조해 확인했어(레거시 표에 `WARNING:` 없음). [검증: impv2.py:40 · 레거시 표 파싱 결과 낱말 집합] |
| **help / ?** | console 전용 | 없음 | 콘솔 도움말 출력 | 구현됨(console) / ⛔ 내용 낡음 — 판정은 원안대로인데 **숫자가 틀렸고 누락 범위가 더 넓어.** [검증: ① **16개가 아니라 14개**야. 층2 ICS 가 더한 새 낱말은 6(HK·HKDATA·CCDFLUSH·CCDPOWON·CCDPOWOFF·ARCHON — `cmd_go` 는 재정의라 새 낱말 아님), 층3 ICG 는 14(그 6 + GUIDEEXP·RADIONODE·EXPENABLE·HTRSET·HTRFORCE·HTRRAMP·HTRPID·VACGAUGE — `cmd_go`·`cmd_exp` 는 재정의). ICS 의 6 이 ICG 의 14 에 포함되니 합집합은 **14**야 — 원안이 괄호 안에 손으로 적은 목록도 정확히 14개였어. ② ⭐ **더 나쁜 건 기반 명령도 빠졌다는 것**: `_HELP`(:23-38)를 세어 보니 기반 29개 중 `stop`·`abort`·`datasource`·`initialize`·`erase`·`shopen`·`shclose`·`dmawait`·`bin`·`ping`·`pong` **열한 개가 없어**. 특히 `stop`/`abort` 는 노출을 세우는 비상 수단인데 도움말에 없어. ③ 세 프로그램이 같은 `Console` 을 쓰는 것 맞아 — `_HELP` 는 grep 결과 console.py 한 곳에만 정의되고 ics_archon/icg_archon 어디에도 재정의가 없어] |
| **quit / exit** | console 전용 | 없음 | 콘솔 종료 | 구현됨(console) — 원안 맞아. [검증: :66-71] |

## 신설 — 레거시에 없던 것 (8)

| 명령 | 노드 | 인자 | 용도 | 노트 (이유·근거) |
|---|---|---|---|---|
| **ARCHON** | ICS·ICG | ICS `ARCHON <MK\|NT> <원문…>` / ICG `ARCHON <원문…>` | 컨트롤러 바이패스 — 명령 원문을 보내고 응답 원문을 그대로 돌려준다 | 신설 — 원안 맞아, 제한 없음도 확인했어. [검증: ics_archon/app.py:180-186 docstring 원문 *"⭐ `ARCHON` 은 **제한이 없다** (운영자 2026-09-05 \"제한 없이 모두 풀어줘\") -- 취득 중이든 다른 조작 중이든 받고, `_op_inflight` 도 잡지 않는다(`GO` 를 막지 않는다)"* 를 직접 열람. ICG 쪽도 commands.py:60-63 에 같은 취지가 적혀 있어. ⭐ 원안의 지적(레거시 CB `XMIT` 은 위험 통로로 지목돼 안 옮겼는데 이쪽은 의식적으로 열었다 — 같은 모양의 두 결정이 반대로 났다)은 문서에 그렇게 적어 둘 값어치가 있어] |
| **CCDFLUSH** | ICS·ICG | ICS `CCDFLUSH [MK\|NT\|ALL]` / ICG 인자 없음 | 유휴 CCD 를 FlushFrame 한 바퀴로 비운다 (프레임은 안 만든다) | 신설 — 원안 맞아. [검증: 두 핸들러 다 sweep 에 있고 어휘도 양쪽 다 등록돼(ics_archon/app.py:63 ICS_OPS_COMMANDS · icg_archon/commands.py:95 ICG_COMMANDS). app.py:71-72 의 `BUSY_TEXT` 상수 확인] |
| **CCDPOWON / CCDPOWOFF** | ICS·ICG | ICS `[MK\|NT\|ALL]` / ICG 없음 | CCD 전원 켜기·끄기 | 신설 — 원안 맞아. [검증: 네 핸들러 다 sweep 에 있고 어휘 등록도 양쪽 확인] |
| **EXPENABLE** | ICG (ICS 는 발신) | `EXPENABLE [ON\|TRUE\|1\|OFF\|FALSE\|0]` | 가이드 노출 잠금 조회·설정 (지속) | 신설 — 원안 맞아. [검증: guideexp.py:40 상수 + icg_archon/commands.py:332 핸들러 + :95 어휘 셋 다 확인. ini 옵션 이름과 와이어 낱말이 다르다는 경고도 유효 — ics_archon/config.py:210 주석이 `EXPENABLE` 은 *"ICS 노출 전/후가 아니라 독출 앞뒤"* 라고 정정해 뒀어]. ⚠️ 위 '(어휘 전수)' 항목의 아슬아슬한 자리가 여기야 — **ICS 는 `EXPENABLE` 을 보내면서 자기 어휘(ICS_OPS_COMMANDS)에는 안 넣었어.** `emit_req` 가 validate() 를 건너뛰어서 지금은 안 울 뿐이야 |
| **HK / HKDATA** | ICS·ICG | 없음 | HK(하우스키핑) 스냅샷 — ICG 가 만들고 ICS 는 물어본다 | 신설 — 원안 맞아, ⚠️ 도 사실이야. [검증: ics_archon/app.py:314-339 전문 열람 — `_ask_icg` 가 `self.emit.emit_req(dest, cmdword)` 로 묻고 곧바로 `Reply.done(cmdword, 'Queried %s -- the reply arrives as a separate DONE: %s report')` 를 돌려줘(안 기다려). 답은 :572-573 `register_report('DONE', word, self._on_hkdata)` 로 받고, :549-568 `_on_hkdata` 는 `self.hk_wire` 에 담고 `log.info` + `print` 만 해. 그 docstring 이 직접 *"⚠️ 값을 헤더로 흘리지는 **아직** 않는다"* 라고 적어 뒀어 — 원안의 '콘솔에 찍기만 한다' 가 정확해] |
| **HTRSET / HTRFORCE / HTRRAMP / HTRPID** | ICG | `HTRSET [<0\|1> <섭씨>]` · `HTRFORCE [<0\|1> <V>]` · `HTRRAMP [<0\|1> <mK/update>]` · `HTRPID [<P> <I> <D>]` | guide 듀어 히터 제어 넷 | 신설 — 원안 맞아. [검증: 네 핸들러 다 sweep 에 있고 :95-99 ICG_COMMANDS 에 네 낱말 다 등록돼(위험 ② 통과). commands.py:26-30 머리말이 `HTR` 접두 통일(운영자 2026-09-04)과 인자 없으면 조회라는 규약을 적어 뒀고, :34-36 이 `HTRFORCE` 의 PID 우회 위험을 못박아. `HTREN` 이 별도 명령이 아니라는 것도 sweep 으로 확인 — `cmd_htren` 없어] |
| **RADIONODE** | ICG | `RADIONODE [STATUS\|CONNECT\|DISCONNECT\|RECONNECT\|ENABLE <별칭>\|DISABLE <별칭>]` | Radionode 폴러 상태 조회 / 폴링 켜고 끄기 / 장치별 켜고 끄기 | 신설 — 원안 맞아. [검증: :237-296 구간 + 어휘 등록 확인. 하위 낱말을 갖는 유일한 2단 구조라는 것도 sweep 상 다른 핸들러엔 없어] |
| **VACGAUGE** | ICG (ICS 는 발신) | `VACGAUGE [ON\|OFF]` | 이온게이지 켜기·끄기·조회 | 신설 — 원안 맞아. [검증: gaugectl.py:57 + icg_archon/commands.py:473 + 어휘 :95 확인. ⭐ 원안이 안 적은 배선 하나 — ICS 는 이 응답을 **명령 처리부가 아니라 `_on_message` 훅에서 엿들어** 데드맨을 풀어(app.py:653-667 `if (ctl is not None and ctl.enabled and msg.src.upper() == ctl.node.upper() and word in raw): ctl.note_reply(msg.raw)`). gaugectl.py:43 주석도 *"답이 안 와도 우리는 모른다"* 라고 그 이유를 적어 뒀어. `EXPENABLE` 어휘 미등록 주의는 이 낱말도 똑같아] |

## 일부러 뺐다 — 폐지 근거가 문서에 있는 것 (17)

| 명령 | 노드 | 인자 | 용도 | 노트 (이유·근거) |
|---|---|---|---|---|
| **ACK** | IC→CB | `DISK` \| `SWAP` | 디스크 동기화·교대 확인 응답 | 일부러 뺐다 — 원안 유지. [검증: icg_legacy_report.md:322 원문 열람 — 폐지 근거 두 가지(1998년 SCSI 최적화 무의미 · 단일 PC 통합으로 NFS 시간 확보 불필요)가 그대로 적혀 있어] |
| **DISPL** | IC 전용 | - | TV 표시 범위(MinTV/MaxTV) 설정 | 일부러 뺐다 — 원안 유지. [검증: 위 ROI 와 같음. 문서에는 `((reserved` 로 적혀 있어] |
| **DONE (콜론 없음)** | CB→IC | `<alias> <이미지수>` | CB 의 전송 완료 통보 | 일부러 뺐다 — 원안 맞고 ⚠️ 경고도 사실이야. [검증: impv2.py:162-171 추적 — `DONE`(콜론 없음)은 MSG_TYPES 의 `'DONE:'` 과 안 맞아 타입으로 안 잡히고 `mtype='REQ'` · `cmdword='DONE'` 이 돼 `Didn't understand` 로 되쏘여. `USAGE:` 와 같은 부류의 오작동이야] |
| **FOUND** | IC↔CB (ICS 테이블에도 CASE) | `<디스크ID>` \| `MOUNT <경로>` | CB 가 찾은 전송 디스크·마운트 지점 통보 수신 | 일부러 뺐다 — 원안 맞아, 폐지 근거 세 곳 다 원문 확인했어. [검증: DevNote.md:838 한 줄, :1409-1413 '11.1 디스크 다중화 폐지' 의 배경→대안→선택→이유 네 줄, :47 `**안으로는** 확정된 신규 구조(ICS + K/M/T/N.IC + K/M/T/N.CB = 9노드 통합)로 짠다` 를 각각 직접 열람. 이유가 '1998년 SCSI 성능 최적화 + NFS 전송시간 확보' 두 전제의 소멸이라고 적혀 있어] |
| **GO / GUIDEEXP / INITIALIZE / STATUS 1 (ICG→G.IC 발신)** | ICG | - | 레거시 ICG 가 하위 G.IC 에 내리던 발신 계열 | 일부러 뺐다 — 원안 맞아. [검증: icg_legacy_report.md:286-289 전문 열람. *"§5.4의 '키를 역순으로 재조립해 중계'하는 기묘한 가공이 통째로 불필요해진다"* 도 :289 원문에 있어. 신규가 백엔드를 직접 부르는 것도 app.py:57-60 으로 확인] |
| **HELP / ? / HISTORY / INFO / CBSTATUS / +ARCHIVE / +AUTOLOG / +DISPLAY / +ADDFITS / +SWAP / RESTORE / RESYNCH / DBGREAD / XMIT / >{host} / TIMEOUT / +ACKSWAP / LASTFILE / PATH / LOG / OFFLINE / DEBUG** | CB | 각각 다름 | Caliban(CB) 프로세스의 콘솔·플래그·엔지니어링 명령 일가 | 일부러 뺐다 — 원안 유지. CB 라는 별도 프로세스가 없어진 결과라는 구조 논거가 맞아. [검증: DevNote:47 원문 확인. `LOG`·`LASTFILE`·`PATH`·`INFO` 처럼 진단에 쓸모 있던 것도 함께 사라졌으니 필요하면 '되살리기가 아니라 신설' 이라는 원안 결론 유지 — 실제로 핸들러 52개 어디에도 대응물이 없어] |
| **INIT** | IC→CB | `DISK <헤더블록> <데이터블록>` | CB 에 디스크 동기화 시작 지시 | 일부러 뺐다 — 원안 유지. `INITIALIZE`(구현됨)와 이름이 닮았으니 문서에서 구분해 적으라는 경고도 유효해. [검증: 원문 두 곳] |
| **MOVIE** | IC 전용 | - | 연속 촬영 모드 | 일부러 뺐다 — 원안 유지. [검증: 위와 같음] |
| **REQ** | IC↔CB (ICS 테이블에도 CASE) | `MOUNT` \| `SWAP` \| `INITDISK` | 하위 계층의 요청 수신 | 일부러 뺐다 — 원안 맞아. [검증: icg_legacy_report.md:288 원문 확인 — `G.IC → G.CB`: `TRANSFER DISK<n> 4 ABC`, `ACK SWAP` / `G.CB → G.IC`: `DONE DISK<n> 4`, `REQ SWAP`, 초기화 핸드셰이크 전체 → 내부 큐/상태 전이. 이름 겹침 경고도 맞아 — impv2.py:40 의 `'REQ:'` 와 app.py:327 의 `msg.mtype in ('REQ','EXEC')` 는 그대로 살아 있어] |
| **RESTART / FLUSH / REMOVE / HOST / UDPPING** | XIS 허브 | 각각 다름 | ISIS 허브 운영 명령 | 일부러 뺐다 — 원안 유지. 4단계에서 허브를 흡수하면 보관본이 명세가 된다는 단서도 그대로. [검증: DevNote 15장 표 확인] |
| **ROI** | IC 전용 (ICS·ICG 에는 없음) | - | Region of interest 설정 | 일부러 뺐다 — 원안 맞아. [검증: commands.py:499-502 주석 전문 + :62-78 위쪽 정정 주석(2026-08-04) 열람 — *"공용 SHARE\PAP7.CMD 에만 있다. ICS 는 그 파일을 포함하지 않으므로 … 레거시 ICS 는 이들을 ERROR 로 거부한다"*. ⭐ 이게 위험 ②의 역방향 사례이기도 해: `ROI`/`DISPL`/`MOVIE` 는 **emitter.py:63 KNOWN_COMMANDS 에는 들어 있는데 핸들러가 없어** — 의도된 비대칭이야(`BIN` 과 달리 NOT_YET_IMPLEMENTED 에도 없어서 `Didn't understand` 로 떨어져). 덤: IC_commands_R20220302.pdf 는 `ROI ((reserved` · `DISPL ((reserved` 로 적어 레거시 IC 에서도 예약 상태였음을 보여 줘] |
| **SNAP** | IC 전용 | - | (공용 세트 명령 — 레거시 ICS 99개에도, 보고서 본문에도 설명 없음) | 일부러 뺐다(근거 등급 낮음) — 원안의 유보가 맞았고 ⭐ **음성 확인을 하나 더 붙일 수 있어**. [검증: `grep -rn "SNAP"` 워크트리 전체에서 이 낱말이 나오는 자리는 commands.py:80 · DevNote.md:913 **둘뿐**이야(gmon/ 의 SNAP 버튼은 무관한 GUI). 게다가 이 워크트리의 IC 명령 정본인 `ics_legacy/IC_commands_R20220302.pdf` 를 풀어 보니 `ROI`·`DISPL`·`MOVIE`·`DMAWAIT`·`FLASHNOW` 다섯은 다 실려 있는데 **`SNAP` 만 0회**야. 즉 `IC_ONLY` 여섯 중 다섯은 문서로 뒷받침되고 `SNAP` 만 출처 불명 — 원안이 등급을 낮춰 적은 게 옳았어. 원천 `SHARE\PAP7.CMD`(202개) 도 이 워크트리에 없어] |
| **STANDARD** | ICS·ICG | `<objname>` | IMAGETYP=STANDARD 설정 (표준별) | 일부러 뺐다 — 판정은 맞는데 ⚠️ **'시험이 함께 고치기를 강제한다' 는 절반만 맞아**. [검증: test_raw_header.py:801-820 전문 열람 — 그 시험이 실제로 하는 단언은 `assert set(IMAGE_TYPES) == spec_vocab` **하나뿐**이야. 즉 규격 어휘 ↔ `state.IMAGE_TYPES` 는 묶어 두지만, **핸들러는 손으로 쓴 `cmd_bias`…`cmd_domeflat` 여섯**이라 IMAGE_TYPES 에 값을 늘려도 핸들러는 안 생기고 어떤 시험도 안 깨져. 세 곳(코드 주석·DevNote·state.py 주석)에 근거가 남아 있다는 것과 :822 의 거부 시험이 따로 있다는 것은 확인했어. ⭐ 덤: commands.py:555-558 `KNOWN` 상수가 IMAGE_TYPES 를 합쳐 만들어지는데 **아무 데서도 임포트 안 해**(grep 0건) — 죽은 코드야] |
| **TRANSFER** | IC→CB | `DISK<n> <개수> <보고대상>` | CB 에 디스크의 이미지를 읽어 저장하라고 지시 | 일부러 뺐다 — 원안 맞아. [검증: icg_archon/sequencer.py:792-794 열람 — 주석 *"소비자(gmon·ABC)를 위한 저장 통보 -- 규약 자유 구역이지만 레거시 형태(`Wrote LASTFILE=… RATE=…`)를 유지한다"* 뒤 `self.emit.wrote_relay(source, path, rate, self.st.expstatus)`. 완료 보고 문구를 살렸다는 서술 확인] |
| **UNMOUNT** | CB→IC | `<마운트경로>` | 마운트 해제 요청 | 일부러 뺐다(근거 등급 낮음) — 원안의 유보가 맞아. [검증: DevNote:1409-1413 원문에 `TRANSFER`/`REQ SWAP`/`ACK SWAP` 만 이름이 나오고 `UNMOUNT` 는 **없어**. 디스크 링 전체를 지목한 폐지문에 딸려 들어간 것이라는 원안 서술 그대로야] |
| **USE** | IC→CB (ICS 테이블에도 CASE) | `DISK<n> <서명>` \| `MOUNT <경로>` | CB 에 쓸 디스크·마운트 지점 지정 | 일부러 뺐다 — 원안 유지. [검증: DevNote 원문 두 곳 열람] |
| **USING** | CB→IC (ICS 테이블에도 CASE) | `<alias>` | CB 의 디스크 확정 통보 수신 | 일부러 뺐다 — 원안 유지. [검증: 원문 두 곳 열람] |

## 미구현 — 없고 폐지 근거도 못 찾은 것 (64)

| 명령 | 노드 | 인자 | 용도 | 노트 (이유·근거) |
|---|---|---|---|---|
| **+LOG** | ICS·ICG | 없음 | 통신 로그 기록 켜기 | 미구현 — 원안 유지. [검증: 핸들러 52개 목록에 없음] |
| **-LOG** | ICS·ICG | 없음 | 통신 로그 기록 끄기 | 미구현 — 원안 유지. [검증: 위와 같음] |
| **BIN** | ICS·ICG | `BIN <n>` | CCD 비닝 설정 | 미구현(스텁) — 원안 맞아. [검증: 488-512 열람. strict_legacy=true 면 `Reply.ignore()`, 끄면 `Reply.error(msg.cmdword.upper(), 'not implemented yet')`]. ⭐ **원안에 없던 두 번째 출처**: `ics_legacy/IC_commands_R20220302.pdf` 를 풀어 보니 `BIN <n> ((not implemented` 로 적혀 있어. 다만 그건 IC 명령 문서이고 매뉴얼은 판정 근거가 아니니(현행 FW 와 어긋난 전례), '일부러 뺐다' 로 올리지 않는다는 원안 결론은 그대로야 |
| **BIOSDISKREAD** | ICS·ICG | 미상 | 용도 미상 (VDOS BIOS 경유 디스크 읽기 진단으로 짐작) | 미구현 — 원안 유지. [검증: 핸들러 목록 부재 + 문서 4종 grep 0건 재확인] |
| **BUFFER** | ICS·ICG | 미상 | 통신 버퍼 조회로 짐작 | 미구현 — 원안 유지. `SETBUFFER` 와 짝. [검증: 위와 같음] |
| **BUILD** | ICS·ICG | 미상 | 자신의 빌드 버전 반환 | 미구현 — 원안 맞고, ICS 본문에 `Build=` 없다는 지적도 사실이야. [검증: commands.py:180-182 ICS 본문은 `Inst=ICS ExpTime=… GuideExp=0 ImageType=… ObjectName=… Mode=… ComTest=F` 로 끝나 `Build=` 가 정말 없어. 반면 emitter.py:406-409 `ic_status` 에는 있어. 값은 state.py:212 `ics_build: str = field(default_factory=build_id)` 로 살아 있고 sequencer.py:818 `out['ICSBUILD'] = st.ics_build` 로 헤더에 실려] |
| **BUILDS** | ICS·ICG | 미상 | IC 들의 빌드 버전 모음 반환으로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재]. 참고로 값 자체는 sequencer.py:816-819 `_builds()` 가 `{c}BUILD`/`GBUILD`/`ICSBUILD` 로 모아 AUXSTATUS 중계 꼬리에 실어 |
| **CCDBIN** | ICS·ICG | 미상 | BIN 계열 (별개 CASE 인 이유는 레거시도 미확인) | 미구현 — 원안 맞아. [검증: :76 `NOT_YET_IMPLEMENTED = ('BIN',)` 한 낱말뿐이라 CCDBIN 은 :105-108 을 타고 `Didn't understand` 로 떨어져] |
| **COMMENT** | ICS·ICG | `<문자열>`(추정) | FITS 헤더 COMMENT 카드용으로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **COMP** | ICS·ICG | `<objname>`(추정) | 비교광원 IMAGETYP 으로 짐작 | 미구현 — 원안 유지. [검증: state.py:55-65 주석·상수 직접 열람. 어휘 여섯 확인, `COMP` 는 폐지 기록에 이름이 없어 `STANDARD` 와 판정이 갈린다는 원안 논리 그대로 성립] |
| **COMTEST** | ICS·ICG | 미상 | 통신 회선 시험으로 짐작 | 미구현 — 원안 맞아. [검증: :180-182 본문 조립식 직접 확인 — `ComTest=F` 는 STATUS 응답의 고정 문자열이고 명령 핸들러는 없어] |
| **CONCISE** | ICS·ICG | 없음 | 상세 출력 끄기 (VERBOSE 반대) | 미구현 — 원안 유지. VERBOSE·QUIET 와 셋 다 없어. [검증: 핸들러 부재] |
| **CONFIG** | ICS·ICG | 없음(추정) | 현재 설정 덤프 | 미구현 — 원안 유지. [검증: :164-183, :197-205 둘 다 열람] |
| **ECHO** | ICS·ICG | `<문자열>`(추정) | 용도 미상 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **END** | ICS·ICG | 미상 | 종료 계열로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **ESTATUS** | ICS·ICG | 미상 | exposure status 축약으로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **EXIT** | ICS·ICG | 없음 | 프로그램 종료 | 미구현(remote) / 구현됨(console) — 원안 맞아. [검증: console.py:66-76 `feed()` 머리 열람. `low = line.lower()` 뒤 문자열 비교로 먼저 채가서 :83 의 wire 조립까지 못 가]. 문서에 이 축소를 결정한 기록이 없다는 것도 grep 으로 재확인 |
| **EXPO** | ICS·ICG | 미상 | EXP 별칭으로 짐작 (GEXPO 의 과학판) | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **EXPSTATUS** | ICS·ICG | 미상 | 노출 상태 질의로 짐작 | 미구현 — 원안 맞아. [검증: emitter.py:79 `_BODY_CMDWORD` 표에서 `EXPSTATUS=` 본문은 커맨드워드가 **빈 문자열이어야** 정상이라고 못박아 뒀어 — 명령 낱말이 아니라 비동기 알림 본문이라는 뜻이라 원안의 '헷갈리기 쉬운 자리' 경고가 맞아] |
| **EXPTIME** | ICS·ICG | `<초>` | 노출시간 설정 (EXP 별칭) | 미구현 — 원안 유지. [검증: 핸들러 부재 + :281 응답 필드 확인] |
| **FINDHOST** | ICS·ICG | `<호스트명>`(추정) | ISIS 허브에 호스트 조회로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재]. 짝인 `HOSTS` 항목의 방향 구분 지적도 맞아 |
| **FOCUS** | ICS·ICG | 미상 | 용도 미상 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **GEXPO** | ICS·ICG | 미상 | 가이드 노출 (EXPO 의 G판) | 미구현 — 원안 유지. [검증: 핸들러 부재. 덧붙여 ics_legacy/IC_commands_R20220302.pdf 본문을 풀어 훑었는데 `GEXPO` **0회**라 그쪽에도 설명이 없어] |
| **GEXPTIME** | ICS·ICG | `<초>`(추정) | 가이드 노출시간 | 미구현 — 원안 유지. 실기능은 `GUIDEEXP` 가 대신해. [검증: 핸들러 부재] |
| **GOQUIET** | ICS·ICG | 없음 \| `<n>`(추정) | 진행 보고 없는 GO 로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **GUIDEENABLE** | ICS·ICG | 미상 | 가이드 계통 활성화로 짐작 | 미구현 — 원안 맞아, 신중한 판단이 옳았어. [검증: ics_legacy/IC_commands_R20220302.pdf 본문에서 `GUIDEENABLE` **0회** — 문서 쪽에도 설명이 없어 무엇을 했는지 여전히 모르는 상태 그대로야. 신설 `EXPENABLE` 은 icg_archon/commands.py:20 주석이 *"추가 (운영자 확정 2026-09-03)"* 라고 못박아 레거시 계승이 아님을 명시하고 있어. 둘을 같은 것으로 볼지는 운영자 몫이라는 원안 결론 유지] |
| **HOSTS** | ICS·ICG | 없음 | 알고 있는 호스트 목록 반환 | 미구현 — 원안 맞고, ⭐ **한 겹 더 나빠**. [검증: `grep -rn "HOSTS" --include=*.py` 워크트리 전체 **0건** — 받는 핸들러가 없는 건 물론이고 **보내는 코드도 없어**. 게다가 콘솔로도 못 보내 (아래 `>NODE` 항목 참고 — console.py:90-92 가 `target.is_ours` 아닌 목적지를 거절해서 `>XIS HOSTS` 가 안 나가). 즉 DevNote:3625 *"첫 구동 확인에 쓴다"* 는 계획에 **구현 경로가 하나도 없어**. 지금 이 워크트리에서 실제로 보낼 수 있는 유일한 수단은 별도 도구 `ics_sim/tools/xis_probe.py`(:59 `sock.sendto((line + '\r').encode('latin-1'), dest)`) 야] |
| **ICSTATUS** | ICS·ICG | 미상 | IC 상태 질의로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **LEDOFF** | ICS·ICG | 없음 | LED 끄기 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **LEDON** | ICS·ICG | 없음(추정) | LED 켜기 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **LEDPULSEDUTYCYCLE** | ICS·ICG | `<값>`(추정) | LED 펄스 듀티비 설정 | 미구현 — 원안 유지. [검증: 핸들러 부재. 낱말 길이 상한이 없다는 원안 참고도 맞아 — commands.py:103 은 길이를 안 봐] |
| **NUMPHLINES** | ICS·ICG·IC | `<n>` | readout 앞쪽 preheat 라인 수 설정 | 미구현 — 원안 유지. [검증: 핸들러 부재. ⭐ 원안이 안 짚은 것 — DevNote.md:2872 미해결 표에 `NUMPHLINES=32` preheat 처리가 `PCTREAD` 4블록 간격 미해결 항목의 조사 대상으로 아직 걸려 있어(우선순위 낮음, *"시뮬은 실측값을 쓰므로 동작에는 영향 없음"*)] |
| **PARTNER** | ICS·ICG | 미상 | 용도 미상 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **PI-COI** | ICS·ICG | `<이름>`(추정) | FITS 헤더 공동연구자 | 미구현 — 원안 맞고, 하이픈 지적도 정확해. [검증: :103 의 치환이 `.`→`_` 하나뿐이라 `PI-COI` 는 `cmd_pi-coi` 를 찾게 되고 그건 파이썬 식별자로 정의할 수 없어. 되살리려면 디스패처 규칙부터 손봐야 한다는 원안 서술 그대로야] |
| **PI_NAME** | ICS·ICG | `<이름>`(추정) | FITS 헤더 PI 이름 | 미구현 — 원안 유지. PROPID·PI-COI·RECID·TELOPS·SUPPORT 와 제안서 메타데이터 다섯이 통째로 없어. [검증: 핸들러 부재] |
| **POLLFSASTAT** | ICS·ICG | 미상 | FSA(필터/셔터 조립체) 상태 폴링으로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재. FSA 값이 AUXSTATUS 로 들어온다는 대응 서술도 telemetry.py:324-331 `aux_body` 로 확인] |
| **PORTS** | ICS·ICG | 없음 | 통신 포트 목록·상태 반환 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **PROPID** | ICS·ICG | `<id>`(추정) | proposal ID | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **QUIET** | ICS·ICG | 없음 | 출력 억제 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **QUIT** | ICS·ICG | 없음 | 프로그램 종료 | 미구현(remote) / 구현됨(console) — 원안 맞아. [검증: console.py:69-71] |
| **READMAP** | ICS·ICG | 미상 | readout 맵으로 짐작 | 미구현 — 원안 유지. READSEQ·ZEROMAP·ZEROSEQ 와 4종 세트가 통째로 없어. [검증: 핸들러 부재] |
| **READSEQ** | ICS·ICG | 미상 | readout 시퀀스 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **RECID** | ICS·ICG | 미상 | 용도 미상 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **RECOVER** | ICS·ICG (CB 에는 동명 실동작) | 미상 (CB 판은 `<n> <디스크ID>`) | 전송 실패 복구 | 미구현 — 원안 유지(ICS 판의 정체가 불명이라 '일부러 뺐다' 로 못 올린다는 판단이 맞아). [검증: DevNote:1409-1413 원문에 `RECOVER` 라는 낱말은 없고 `TRANSFER`/`REQ SWAP`/`ACK SWAP` 만 이름이 나와] |
| **RESETCHECKSUM** | ICS·ICG | 없음(추정) | 통신 체크섬 카운터 초기화로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **SAVECONFIG** | ICS·ICG | 없음(추정) | 현재 설정을 설정파일에 저장 | 미구현 — 원안 맞아. [검증: icg_archon/app.py:62-64 직접 확인 — 주석이 *"노출 잠금 -- 지속 플래그 … ⚠️ 경로가 비면 지속되지 않는다"* 라고 적어 뒀어. 설정 전체를 저장하는 명령은 없다는 결론 그대로] |
| **SETBUFFER** | ICS·ICG | `<n>`(추정) | 통신 버퍼 크기 설정 | 미구현 — 원안 맞아. [검증: impv2.py:30-31 `#: 스펙상 최대 길이. 초과분은 malformed 로 버린다. / MAX_LEN = 2048` — 상수라는 원안 서술 확인] |
| **STD** | ICS·ICG | `<objname>`(추정) | STANDARD 별칭으로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재 + state.py:59-64 폐지 주석에 `STANDARD` 만 이름이 있고 `STD` 는 없음을 원문에서 재확인. 규칙대로 근거를 못 찾았으니 미구현이 맞고, 폐지가 맞다면 주석에 `STD` 도 적어 두자는 권고도 그대로 유효] |
| **SUPPORT** | ICS·ICG | `<이름>`(추정) | 지원 관측자 이름으로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **TCSTATUS** | ICS·ICG | 미상 | 용도 미상 (TCSSTATUS 와 별개 CASE) | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **TELOPS** | ICS·ICG | `<이름>`(추정) | telescope operator | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **TEMPBIAS** | ICS·ICG | 미상 | 용도 미상 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **TEMPDARK** | ICS·ICG | 미상 | 용도 미상 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **TEMPOBJ** | ICS·ICG | 미상 | 용도 미상 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **TIMELOOP** | ICS·ICG | 미상 | 타이밍 반복시험으로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **UARTFLUSH** | ICS·ICG | 없음(추정) | UART(광케이블 시리얼) 버퍼 비우기 | 미구현 — 원안 유지(간접 근거뿐이라 '일부러 뺐다' 로 안 올린 판단이 맞아). [검증: 핸들러 부재] |
| **UPTIME** | ICS·ICG | 없음 | 프로그램 가동 시간 반환 | 미구현 — 원안 유지. 첫 구동 점검용 후보로 적어 두자는 제안도 그대로 유효해. [검증: 핸들러 부재] |
| **USAGE:** | 공통 | `<본문>` | IMPv2 사용법 안내 수신 (메시지 타입) | 미구현 — 원안 맞고 ⭐ **원안보다 한 겹 더 나빠.** [검증: impv2.py:150-176 `parse_line` 전문 추적 — `USAGE:` 는 MSG_TYPES 에 없어서 타입으로 안 잡히고 `mtype='REQ'` · `cmdword='USAGE:'` 가 돼. app.py:327 이 REQ 를 디스패처로 넘기고, commands.py:103 의 치환은 `.`→`_` 뿐이라 콜론이 남아 `cmd_usage:` 를 찾다 실패, :107-108 이 상대에게 ERROR 를 되쏴. ⭐ **추가 피해**: 그 ERROR 의 커맨드워드가 `USAGE:` 라 emitter.py:170 `if cmdword is not None and cmd and cmd.upper().rstrip(':') not in KNOWN_COMMANDS` 에도 걸려(`USAGE` 는 KNOWN_COMMANDS 밖) 발신할 때마다 `unknown_cmdword` 위생 위반이 함께 쌓여. IMPv2.5 7종 중 이것만 빠진 것은 손볼 자리라는 원안 결론 그대로] |
| **VERBOSE** | 공통 | 없음 | 상세 출력 켜기 | 미구현 — 원안 유지. 원격에서 로그 상세도를 못 올린다는 지적도 맞아. [검증: 핸들러 부재] |
| **VERSION** | 공통 | 없음 | 버전·컴파일 정보 반환 | 미구현 — 원안 맞아. [검증: icg_archon/app.py:56 `self.state.ics_build = build_id() # 배너·STATUS 응답용` 직접 확인 + state.py:212 필드 + sequencer.py:818 `ICSBUILD` 카드. 값은 있는데 물어볼 낱말이 없다는 서술 그대로야] |
| **VERT** | ICS·ICG | 미상 | 수직 클럭/전송으로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **ZERO** | ICS·ICG | `<objname>`(추정) | BIAS 의 다른 이름으로 짐작 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **ZEROMAP** | ICS·ICG | 미상 | 용도 미상 | 미구현 — 원안 유지. [검증: 핸들러 부재] |
| **ZEROSEQ** | ICS·ICG | 미상 | 용도 미상 | 미구현 — 판정은 맞는데 ⛔ **'99개 전량' 이라는 마무리 문장은 그대로 쓰면 안 돼.** [검증: :407-419 코드블록을 스크립트로 파싱해 세 보니 **낱말 99개, 중복 0개** 였고 원안 표의 이름 집합과 **양방향 차집합이 공집합**이야 — 즉 원안은 적혀 있는 것을 하나도 안 빠뜨렸어. 그런데 **그 블록의 머리글(:406)이 스스로 "100개" 라고 말해**, 그리고 같은 주장이 다섯 군데 더 있어: ics_legacy_report.md:986 · :1125 · icg_legacy_report.md:74 · :239 · ics_sim/ics_sim/commands.py:500 `KMTX\PAP7KX.CMD, CASE 100개`. 원천 `PAP7KX.CMD` 는 이 워크트리에 **없어**(ics_legacy/__ICIMACS/original codes 에는 ISISclient.zip·pctcs.zip 뿐, `find -iname '*.CMD'` 0건 — 그건 예전 세션에서 IC2.img 로 읽은 것). 그러니 **레거시 CASE 하나가 대조표에서 통째로 빠졌을 수 있고 여기서는 어느 쪽이 맞는지 못 가려**. '99개 전량' 대신 '보고서에 옮겨 적힌 99개 전량 — 다만 보고서 머리글은 100개라 한 개가 미상' 으로 적어야 해] |

## 판정 기준·어휘 점검 (명령이 아님) (3)

| 명령 | 노드 | 인자 | 용도 | 노트 (이유·근거) |
|---|---|---|---|---|
| **(어휘 전수 — 위험 ②)** | 공통 | - | 핸들러가 있는데 커맨드워드 어휘에 없어 위생 검사가 우는 경우가 있나 | ⭐ **원안에 없던 항목이라 새로 넣어.** 결론은 **어긋난 자리 0건** — 기반 29개 커맨드워드가 전부 KNOWN_COMMANDS 안에 있고, ICS 신설 6낱말(HK·HKDATA·CCDFLUSH·CCDPOWON·CCDPOWOFF·ARCHON)은 ICS_OPS_COMMANDS 가, ICG 신설 14낱말은 ICG_COMMANDS 가 덮어. 역방향(어휘만 있고 핸들러 없음)은 ROI·DISPL·MOVIE·AUXSTATUS·TCSSTATUS 다섯인데 전부 의도된 것. ⚠️ **아슬아슬한 자리 하나**: ICS 가 ICG 로 보내는 `EXPENABLE`·`VACGAUGE` 는 ICS_OPS_COMMANDS 에 **없어**. 지금 안 우는 이유는 `emit_req`(emitter.py:260-266)가 발신 경로 중 **유일하게 validate() 를 안 부르기** 때문이야 — 누가 이 둘을 `emit()`/`done()` 으로 옮기면 그 순간부터 `unknown_cmdword` 가 나. [검증: emitter.py:241-266 두 메서드 본문 대조, grep 으로 등록 호출부 전수] |
| **SYNCHRONIZE** | 공통 | 없음 | IMGTYPE/OBJNAME/EXP/OBSERVER/PROJID 스냅샷 반환 | ⛔ **판정 고침 — 구현됨(조회 전용)은 맞지만 '의도적으로 끊었고 docstring 이 근거' 는 과장이야.** [검증: ① docstring 원문(:199-204)을 열어 보니 *"레거시의 위험한 성질을 끊었다"* 같은 말은 **없고**, 실제 문장은 *"통합 노드에는 동기화할 상대가 없지만, 외부 노드(ICG 등)가 물어보면 그대로 답한다"* 야 — 축소 사유가 아니라 현황 서술이야. ② 그 전제가 **이미 깨졌어**: ICS·ICG 를 두 프로그램으로 가르면서 '동기화할 상대' 가 실제로 생겼어. ③ 결정 자체가 두 곳에서 **미결로 열려 있어** — DevNote.md:2882 은 13장 미해결 표(우선순위 중간)이고, icg_legacy_report.md:301 은 ICS↔ICG 의 SYNCHRONIZE 를 *"유지/폐지 결정 필요"* 로 적어 뒀어. 그러니 '일부러 뺐다' 쪽 근거로 쓰면 안 되고, **미결 항목으로 대조표에 남겨야 해**] |
| **TCSSTATUS** | ICS·ICG (발신 전용) | - | 망원경 지향 텔레메트리 질의 → IC 중계 | ⛔ **판정은 구현됨(발신)/미구현(명령 수신)으로 유지하지만, 기전 설명이 두 군데 틀렸어.** 원안은 *"TC 의 답은 `STATUS:` 타입이라 보고 경로로 빠진다"* 고 했는데 [검증: telemetry.py:186-213 `query()` 와 :302-319 `on_tc_reply()` 전문, app.py:290-330 수신 순서 열람] ① **TC 의 답은 `DONE:` 이야** — `on_tc_reply` docstring 이 `TC>ICS DONE: AUXSTATUS ...` 라고 못박고 `msg.cmdword` 로 걸러. ② **보고 경로로 안 가** — app.py:311-314 가 `router.resolve()` **앞에서** 먼저 채가서 대기 중인 future 를 깨워(:317-319). `STATUS:` 는 반대 방향, 즉 우리가 우리 IC 들에게 뿌리는 중계(sequencer.py:832)야. 원안이 나가는 중계와 들어오는 답을 뒤섞었어. 나머지(우리가 질의자다, 누가 `REQ TCSSTATUS` 를 보내면 레거시와 달리 `Didn't understand` 로 거절된다)는 맞아 |

---

## ⏳ 다음 세션으로 이월 — 이 대조에서 나온 결함 셋

운영자 확정 2026-09-06: *"⛔ 내일 시험에 걸리는 결함 셋에 대해서는 다음 세션에서
검토하여 반영할게."*

| # | 무엇 | 근거 | 무게 |
|---|---|---|---|
| 1 | ⛔ **`ICG>XIS HOSTS` 를 보낼 수단이 없다** | `grep -rn "HOSTS" --include=*.py` **0건** — 받는 핸들러도 **보내는 코드도** 없다.  콘솔 `>XIS HOSTS` 도 아래 2번에 막힌다.  실제로 보낼 수 있는 것은 별도 도구 `../ics_sim/tools/xis_probe.py` 뿐 | [`icg_first_run.md`](icg_first_run.md) **3단계**가 이 명령으로 *"허브가 아는 노드"* 를 확인하라고 적어 두었다 — **구현 경로가 하나도 없다** |
| 2 | ⛔ **`>NODE <명령>` 이 설명과 다르다** | `console.py:77-93` — 조립한 줄이 **와이어로 안 나간다**.  프로세스 안에서 `dispatch.handle()` 을 부를 뿐이고, `:90-92` 가 `router.resolve()` 로 풀어 `is_ours` 가 아니면 거절한다.  `Target.is_ours`(`nodes.py:49-51`)는 ICS·IC·CB 뿐 | `>XIS …` · `>TC …` · `>ICG …` 가 전부 *"담당하는 노드가 아닙니다"* 로 막힌다.  **"`>NODE` 를 진짜 remote 발신으로 만들 것인가"** 는 설계 결정이다 |
| 3 | ⛔ **콘솔 도움말이 낡았다** | `console.py:22-38` `_HELP` — 신설 **14 낱말**(`HK`·`HKDATA`·`VACGAUGE`·`HTRSET`·`HTRFORCE`·`HTRRAMP`·`HTRPID`·`EXPENABLE`·`RADIONODE`·`GUIDEEXP`·`CCDFLUSH`·`CCDPOWON`·`CCDPOWOFF`·`ARCHON`)이 하나도 없고, **기반 명령 `ABORT`·`STOP` 도 빠져 있다** | 명령이 되는데 **찾을 수가 없다.**  명령표에서 도움말을 **생성**하게 고치면 다시는 어긋나지 않는다 |

### 곁들여 — 지금 안 울지만 언젠가 우는 자리

⚠️ ICS 가 ICG 로 보내는 **`EXPENABLE`·`VACGAUGE` 가 `ICS_OPS_COMMANDS` 에 없다.**
지금 위생 검사가 조용한 이유는 `emitter.emit_req()`(`:260-266`)가 발신 경로 중
**유일하게 `validate()` 를 안 부르기** 때문이다 — 누가 이 둘을 `emit()`/`done()` 으로
옮기면 그 순간부터 `unknown_cmdword` 가 난다.
(2026-09-06 에 신설한 `HK`·`HKDATA` 는 등록해 두었다.)

⚠️ **콘솔 입력은 `app._on_message` 를 지나지 않는다** (`console.py:93` 이
`dispatch.handle()` 을 직접 부른다) — 자기 에코 걸러내기·브로드캐스트 중복 제거가
그 경로에는 안 걸린다.

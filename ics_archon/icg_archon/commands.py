#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""icg 명령 -- science 명령 처리부 상속 + 텔레메트리 명령 추가.

레거시 계승: ICG 는 ICS 와 **같은 명령 테이블**을 썼으므로(`PAP7KX.CMD`,
icg_legacy_report 8.1절) `OBJECT`/`DARK`/`EXP`/`GO`/`STOP`/`ABORT` 등은
`ics_sim.commands.Dispatcher` 를 상속해서 그대로 받는다.  실측 관측된
전용 명령은 `GUIDEEXP` 하나다 (5.2절 -- 응답 문구까지 계승).

추가 (운영자 요구 2026-08-31):

* `HK`                     -- 최신 HK 스냅샷 한 줄
* `RADIONODE STATUS`       -- 백엔드·루프·자격증명·장치별 상태
* `RADIONODE CONNECT` / `DISCONNECT` -- ⭐ **폴링 자체를 런타임에 켜고 끈다**
* `RADIONODE RECONNECT`    -- 즉시 재폴링 (주기를 안 기다린다)
* `RADIONODE ENABLE <별칭>` / `DISABLE <별칭>` -- **그 장치만** 켜기/끄기
  (`CONNECT <별칭>`/`DISCONNECT <별칭>` 도 같은 뜻이다)

추가 (운영자 확정 2026-09-03):

* `EXPENABLE ON|TRUE|OFF|FALSE`  -- **노출 잠금** (지속.  인자 없이 조회)

추가 (운영자 확정 2026-09-04):

* `HTRSET <0|1> <섭씨>`    -- 히터 Enable + 목표온도  (`…AENABLE`/`…ATARGET`)
* `HTRFORCE <0|1> <V>`     -- ⛔ 강제 출력 (PID 우회)  (`…AFORCE`/`…AFORCELEVEL`)
* `HTRRAMP <0|1> <mK>`     -- 목표온도 램프            (`…ARAMP`/`…ARAMPRATE`)
* `HTRPID <P> <I> <D>`     -- PID 게인 셋              (`…AP`/`…AI`/`…AD`)
* `VACGAUGE ON|OFF`        -- ⭐ **이온게이지 켜기/끄기** (`MOD10\\DIO_SOURCE3`)

⭐ 셋은 **응답이 나중에 온다** (`Reply.noop()` → 왕복 후 `emit.done/error`).
컨트롤러 왕복이 필요한데 핸들러는 동기 함수이기 때문이고, `ics_sim` 의
`ERASE`/`SHOPEN` 이 쓰는 것과 **같은 선례**다 -- 규약을 새로 열지 않는다.

⭐ 히터 다섯은 **`HTR` 접두로 통일**했다 (운영자 2026-09-04: *"HEATERSET 으로
했었는데 줄여서 HTRSET 같이 바꾸려고 해"*) -- 채널 구분자 `A` 는 없다(채널 B 는
안 쓴다).  ⭐ 다섯 다 **인자 없이 보내면 조회**이고, 답은 캐시가 아니라 `RCONFIG`
되읽기다 (`ctrl.config` 는 왕복 실패에도 먼저 갈아 끼워져 못 믿는다).

⛔ 셋 다 `APPLYMOD09`/`APPLYDIO09` 를 부르므로 **진공 게이지를 읽는 MOD10 의
VCPU 가 재시작되고 `DEWPRES` 에 결측 창이 생긴다** (매뉴얼 p.86).  ⭐ 운영자
확정(2026-09-04): **취득 중이어도 거부하지 않는다** -- 결측은 받아들이고
경고와 응답 표시로만 알린다 (DevNote 11.18-(3)).

추가 (운영자 지시 2026-09-05) -- **CCD 조작 넷**:

* `CCDFLUSH`               -- 유휴 CCD 를 `FlushFrame` 한 바퀴로 비운다 (프레임 없음)
* `CCDPOWON` / `CCDPOWOFF` -- CCD 전원 (`POWERON`/`POWEROFF`; ON 은 `poweron_wait` 초)
* `ARCHON <명령 원문…>`     -- 컨트롤러 바이패스 (응답 원문을 `DONE` 으로 되돌린다)

⛔ 넷 다 **취득 중이면 거부**한다 (`ERROR: … Exposure in progress -- ABORT
first`) -- 히터·게이지와 반대다.  그쪽은 결측 창 하나가 대가지만, 이쪽은
진행 중 노출 위에 `LOADPARAMS`/`RESETTIMING`/`POWEROFF` 가 들어가 **자료를
망친다**.  ⭐ 그리고 **넷이 서로도, `GO` 도 막는다** (`_op_in_flight`) --
`POWERON` 의 `poweron_wait` 동안 들어온 `GO` 는 `prepare()` 가 이미 `powered`
라 그대로 arm 해 flush 가 안 끝난 CCD 를 찍는다.  ⚠️ `EXPENABLE` 잠금과는
**무관하게 허용**한다 (flush·전원·바이패스는 노출이 아니다) -- 잠겨 있으면
응답에 `ExpEnable=OFF` 를 덧붙여 알리기만 한다.

⭐ 히터·게이지의 `_ctrl()` 이 아니라 **백엔드 표면**(`flush_ccd`/`power_ccd`/
`raw_command`)을 부른다 -- 그래서 컨트롤러 없는 Sim 에서도 돈다 (Sim 의
`raw_command` 는 `SIM (no controller): …` 를 돌려준다).
"""

from __future__ import annotations

import logging

from ics_archon import _simpath

_simpath.ensure()

from ics_archon.archon.protocol import ArchonError  # noqa: E402
from ics_sim import commands as sim_commands  # noqa: E402
from ics_sim import emitter  # noqa: E402
from ics_sim.commands import Reply  # noqa: E402
from ics_sim.impv2 import MAX_LEN, Message  # noqa: E402
from ics_sim.nodes import Target  # noqa: E402

from . import expenable as expen  # noqa: E402
from . import heater  # noqa: E402
from .radionode import RadionodeError  # noqa: E402

log = logging.getLogger('icg_archon.cmd')

#: emitter 의 커맨드워드 어휘에 icg 몫을 더한다 -- `validate()` 가 이 표로
#: 발신을 검사하므로, 등록 없이 새 커맨드워드를 쓰면 위생 검사가 운다
#: (`unknown_cmdword` -- `emit.violations` 에 쌓이고 경고 로그가 난다).
ICG_COMMANDS = frozenset({'GUIDEEXP', 'HK', 'RADIONODE', 'EXPENABLE',
                          'HTRSET', 'HTRFORCE', 'HTRRAMP',
                          'HTRPID', 'VACGAUGE',
                          'CCDFLUSH', 'CCDPOWON', 'CCDPOWOFF', 'ARCHON'})

#: `ARCHON` 응답 본문의 상한 [bytes].  한 메시지 상한은 `MAX_LEN`(2048) 이고
#: 헤더(`ICG>abc DONE: ARCHON ` -- 노드 이름 8자씩이면 31)와 잘림 표시
#: (` ...(+NNNNN bytes truncated, see log)` ≈ 40) · 잠금 주석(` (ExpEnable=OFF)`
#: 16) 을 뺀 여유다.  `STATUS` 응답이 1~2 KB 라 실제로 걸리는 자리다 --
#: 넘치면 여기서 자르고 **전문은 로그**에 남긴다.
ARCHON_REPLY_MAX = 1800
assert ARCHON_REPLY_MAX + 31 + 40 + 16 < MAX_LEN

#: 넷의 공통 거부 문구 -- 취득 중.
BUSY_REFUSAL = 'Exposure in progress -- ABORT first'

#: `ON|OFF` 를 받는 명령들의 어휘.  ⭐ `EXPENABLE` 과 **같은 낱말**을 쓴다 --
#: 명령마다 다른 어휘를 두면 운영자가 어느 명령이 `TRUE` 를 받는지 외워야
#: 한다.  ⛔ 어휘 밖은 기본값으로 떨어뜨리지 않고 **거부**한다.
ONOFF = {'ON': True, 'TRUE': True, '1': True,
         'OFF': False, 'FALSE': False, '0': False}

#: 어휘 밖 값에 붙이는 문구.  ⭐ **"모르는 값"이라고 말하고 받는 낱말을 댄다**
#: (운영자 2026-09-04) -- "Invalid" 만으로는 무엇이 허용인지 알 수 없다.
def _unknown(word: str) -> str:
    return ('Unrecognized value: %s -- use %s'
            % (word, '|'.join(sorted(ONOFF, key=str.lower))))


def extend_vocabulary() -> None:
    """모듈 상수(frozenset)를 합집합으로 갈아 끼운다 -- 한 번이면 된다."""
    if not ICG_COMMANDS <= emitter.KNOWN_COMMANDS:
        emitter.KNOWN_COMMANDS = frozenset(emitter.KNOWN_COMMANDS
                                           | ICG_COMMANDS)


class IcgDispatcher(sim_commands.Dispatcher):
    """science 디스패처 + icg 전용 핸들러."""

    def __init__(self, app) -> None:  # noqa: ANN001
        super().__init__(app)
        #: 지금 왕복 중인 CCD 조작 명령의 커맨드워드 (`CCDFLUSH`/`CCDPOWON`/
        #: `CCDPOWOFF`/`ARCHON`), 없으면 빈 문자열.  `cmd_go` 와 넷이 서로를
        #: 이것으로 막는다 -- 시퀀서 `busy` 는 취득만 알고 이 왕복은 모른다.
        self._op_in_flight = ''

    def _image_type(self, msg: Message, imgtype: str) -> Reply:
        """`BIAS`/`DARK`/… -- **guide 는 노출시간을 0 으로 만들지 않는다.**

        부모는 `BIAS` 에서 `exptime = 0` 으로 두고 `EXP` 도 거부한다(레거시
        실측 규약).  그런데 guide 에서 `EXPTIME` 은 셔터 노출이 아니라
        **독출 개시 간격**이라(raw spec 10.1절) 0 이 실현 불가능한 값이고,
        그 상태가 되면 `go` 가 거부되는데 `EXP` 로 되돌릴 수도 없어
        **가이딩이 명령 하나로 잠긴다** (2026-08-31 교차검토).

        그래서 국면 이름만 바꾸고 주기는 건드리지 않는다.  ⏳ guide 의
        `IMAGETYP` 어휘 자체는 아직 미확정이다 (guide OI-24).
        """
        st = self.state
        keep = st.exptime
        reply = super()._image_type(msg, imgtype)
        if st.exptime != keep:
            log.info('guide 는 %s 에서도 주기를 유지한다 -- EXPTIME 은 독출 '
                     '개시 간격이라 0 이 될 수 없다 (%g s 유지)',
                     imgtype, keep)
            st.exptime = keep
        return reply

    def cmd_exp(self, msg: Message, target: Target) -> Reply:
        """EXP -- guide 는 `BIAS` 에서도 받는다 (위 `_image_type` 과 같은 이유)."""
        st = self.state
        arg = msg.body.strip()
        if arg:
            try:
                st.exptime = float(arg)
            except ValueError:
                return Reply.error('EXP', 'Invalid exposure time: %s' % arg)
        return Reply.done('EXP', 'ExpTime=%g seconds.' % st.exptime)

    def cmd_guideexp(self, msg: Message, target: Target) -> Reply:
        """GUIDEEXP <초> -- 가이드 노출시간(독출 개시 간격) 설정.

        레거시 응답 문구를 계승한다 -- `DONE: GUIDEEXP GuideExp=<n> seconds.`
        (icg_legacy_report 5.2절 실측).  값 의미는 신규 규격으로 넘어와
        `EXPTIME` = 독출 개시 간격이다 (raw spec 10.1절) -- `EXP` 와 같은
        상태 필드를 채우므로 어느 쪽으로 설정해도 같다 (guide 는 `EXP` 의
        `BIAS` 가드도 풀어 뒀다 -- `cmd_exp`).
        """
        arg = msg.body.strip()
        if not arg:
            return Reply.done('GUIDEEXP',
                              'GuideExp=%g seconds.' % self.state.exptime)
        try:
            seconds = float(arg)
        except ValueError:
            return Reply.error('GUIDEEXP', 'Invalid exposure time: %s' % arg)
        if seconds < 0:
            return Reply.error('GUIDEEXP', 'Invalid exposure time: %s' % arg)
        self.state.exptime = seconds
        return Reply.done('GUIDEEXP', 'GuideExp=%g seconds.' % seconds)

    def cmd_hk(self, msg: Message, target: Target) -> Reply:
        """HK -- 최신 HK 표본 한 줄 (키=값, 결측은 안 싣는다)."""
        hk = getattr(self.app, 'hk', None)
        if hk is None:
            return Reply.error('HK', 'HK monitor is not running')
        vals = hk.sensors()
        unit = hk.ctrl_telemetry()
        parts = ['%s=%s' % (k.upper(), v) for k, v in sorted(vals.items())]
        if unit.get('temp'):
            parts.append('C1_TEMP=%s' % '|'.join(
                '%.1f' % t if t is not None else 'NC'
                for t in unit['temp']))
        body = ' '.join(parts) if parts else 'no fresh HK sample yet'
        return Reply.done('HK', body)

    def cmd_radionode(self, msg: Message, target: Target) -> Reply:
        """RADIONODE [STATUS | CONNECT | DISCONNECT | RECONNECT | EN/DISABLE].

        ⭐ **`CONNECT`/`DISCONNECT` 는 인자 유무로 뜻이 갈린다** -- 인자가
        없으면 **폴링 자체**를, 있으면 **그 장치 하나**를 켜고 끈다.  운영자
        지시가 *"디바이스 2개 접속상태를 알려주고 connect/disconnect 명령"*
        이라 둘 다 필요한데, 한 낱말이 두 뜻이라 **응답에 어느 뜻으로 했는지**
        를 적는다 (`Polling=on …` 대 `hebox connected`).
        """
        rn = getattr(self.app, 'radionode', None)
        if rn is None:
            return Reply.error('RADIONODE', 'Radionode poller is not running')
        args = msg.body.split()
        sub = args[0].upper() if args else 'STATUS'
        if sub == 'STATUS':
            return Reply.done('RADIONODE', rn.status_text())
        if sub in ('CONNECT', 'DISCONNECT') and len(args) < 2:
            # ⭐ 인자 없는 갈래 -- 폴링 자체를 켜고 끈다.
            if sub == 'CONNECT':
                try:
                    note = rn.connect()
                except RadionodeError as exc:
                    # ⛔ 켜지 못한 이유를 **그대로** 돌려준다 -- "무엇이
                    # 없어서 못 켜는지" 가 이 명령의 값어치다.
                    return Reply.error('RADIONODE', str(exc))
                return Reply.done('RADIONODE', note)
            self.app.spawn(self._do_rn_disconnect(msg.src, rn))
            return Reply.noop()
        if sub == 'RECONNECT':
            if rn.cfg.backend != 'openapi':
                return Reply.error('RADIONODE',
                                   'Backend is %s -- nothing to poll (use '
                                   'RADIONODE CONNECT first)'
                                   % rn.cfg.backend)
            # 즉시 한 바퀴 -- 결과는 다음 STATUS 로 본다 (질의는 블로킹이라
            # 백그라운드로 던진다).
            self.app.spawn(rn.poll_now())
            return Reply.done('RADIONODE', 'Polling now')
        if sub in ('ENABLE', 'DISABLE', 'DISCONNECT', 'CONNECT'):
            if len(args) < 2:
                return Reply.error('RADIONODE', 'Usage: RADIONODE %s <alias>'
                                   % sub)
            if rn.cfg.backend != 'openapi':
                # 폴러가 없는데 "껐다/켰다" 고 답하면 운영자가 상태를 잘못
                # 믿는다 -- 실제로 바뀌는 것이 없다.
                return Reply.error('RADIONODE',
                                   'Backend is %s -- nothing to enable or '
                                   'disable (use RADIONODE CONNECT first)'
                                   % rn.cfg.backend)
            alias = args[1]
            on = sub in ('ENABLE', 'CONNECT')
            if not rn.set_enabled(alias, on):
                return Reply.error('RADIONODE', 'Unknown device: %s' % alias)
            # ⭐ **장치 하나**를 만졌다는 것이 문구에서 보여야 한다 -- 인자
            # 없는 CONNECT(폴링 전체)와 헷갈리지 않게.
            return Reply.done('RADIONODE', 'Device=%s %s' % (
                alias, 'enabled' if on else 'disabled'))
        return Reply.error('RADIONODE', "Didn't understand %s ?" % sub)

    async def _do_rn_disconnect(self, dest: str, rn) -> None:  # noqa: ANN001
        """폴링 정지는 루프 태스크를 취소하므로 코루틴이다 -- 늦은 `DONE`."""
        try:
            note = await rn.disconnect()
        except Exception as exc:  # noqa: BLE001
            self.emit.error(dest, 'RADIONODE', 'Failed: %s' % exc)
            return
        self.emit.done(dest, 'RADIONODE', note)

    # -- 노출 잠금 (운영자 확정 2026-09-03) -------------------------------

    def _expenable(self):  # noqa: ANN202
        """앱이 들고 있는 플래그.  없으면 `None` (시뮬 하네스 등)."""
        return getattr(self.app, 'expenable', None)

    def cmd_go(self, msg: Message, target: Target) -> Reply:
        """GO -- ⛔ **잠겨 있으면 시작하지 않는다.**

        ⚠️ 검사를 `super()` **앞에** 둔다.  뒤에 두면 시퀀서가 이미 국면을
        `INITIALIZING` 으로 옮기고 취득 태스크를 띄운 뒤라 되돌려야 한다.

        ⭐ CCD 조작 넷(`CCDFLUSH`/`CCDPOWON`/`CCDPOWOFF`/`ARCHON`)이 왕복 중이면
        **그것도 거부**한다 (2026-09-05).  `POWERON` 은 ack 직후 `powered=True`
        가 되고 그 뒤 `poweron_wait` 를 CCD flush 로 보내는데, 그 사이의 `GO` 는
        `prepare()` 가 전원을 건너뛰어 **flush 가 안 끝난 CCD 를 arm 한다**
        (`controller.power_on` 주석).  시퀀서 `busy` 는 이 왕복을 모른다.
        """
        flag = self._expenable()
        if flag is not None and not flag.allowed:
            # 문구는 레거시 ERROR 꼴을 따른다 (두 칸 띄고 한 문장).
            return Reply.error('GO', 'Exposure is disabled (EXPENABLE OFF)!')
        if self._op_in_flight:
            return Reply.error('GO', 'Busy with %s -- wait for its DONE'
                               % self._op_in_flight)
        return super().cmd_go(msg, target)

    def cmd_expenable(self, msg: Message, target: Target) -> Reply:
        """EXPENABLE [ON|TRUE|OFF|FALSE] -- 노출 잠금.  인자 없으면 조회.

        ⭐ **`OFF` 는 진행 중인 노출도 세운다** (운영자 확정) -- 그리고
        **순서가 중요하다**:

            1. 플래그를 **먼저** 올린다
            2. `seq.busy` 면 **ABORT 경로**로 세운다

        ⚠️ 뒤바꾸면 창이 열린다 -- abort 가 끝나 `EXPSTATUS=IDLE` 이 나가면
        그것을 기다린 `go` 가 곧바로 들어올 수 있고, 플래그가 아직 안 올라가
        있으면 **막 세운 노출이 즉시 다시 시작된다.**

        ⭐ `STOP` 이 아니라 `ABORT` 인 이유: `STOP` 은 적분만 끊고 독출·저장을
        정상 수행하므로 *"지금 멈춤"* 이 아니다.  guide `ABORT` 는 `_settle()`
        이 붙어 **컨트롤러를 실제로 세운다**(`df4d4fc` 로 검증된 경로)고,
        **이미 fetch 를 마친 저장은 끝내 준다** -- 완료된 프레임을 잃지 않는다.

        ⚠️ `busy` 가 아니면 abort 를 부르지 않는다 -- `cmd_abort` 가
        `ERROR: No acquisition in progress` 를 내서 *"플래그는 올렸는데 에러
        응답"* 이 되어 헷갈린다.
        """
        flag = self._expenable()
        if flag is None:
            return Reply.error('EXPENABLE', 'Exposure lock is not available')
        arg = msg.body.strip()
        if not arg:
            return Reply.done('EXPENABLE', 'ExpEnable=%s' % flag.word)
        want = expen.parse(arg)
        if want is None:
            # ⛔ 기본값으로 떨어뜨리지 않는다 -- 상태를 그대로 둔다.
            return Reply.error('EXPENABLE', _unknown(arg))

        flag.set(want)                            # ① 플래그를 먼저
        aborted = 0
        if not want and self.app.seq.busy:        # ② 그 다음 세운다
            if self.app.seq.cancel(save=False, requester=msg.src):
                aborted = 1
                log.info('EXPENABLE OFF -- 진행 중이던 취득을 세웠다 (%s)',
                         msg.src)
        body = 'ExpEnable=%s' % flag.word
        if aborted:
            body += ' Aborted=1'
        return Reply.done('EXPENABLE', body)

    # -- 히터·이온게이지 (운영자 확정 2026-09-04) --------------------------

    def _ctrl(self, cmdword: str):  # noqa: ANN202
        """guide 컨트롤러와 **거부 Reply** 를 짝으로 돌려준다.

        시뮬 백엔드·단위 시험 하네스에는 컨트롤러가 없다 -- 그때 조용히
        성공을 돌려주면 *"명령은 먹었는데 아무것도 안 바뀜"* 이 된다.
        """
        ctrl = getattr(getattr(self.app, 'guide', None), 'ctrl', None)
        if ctrl is None:
            return None, Reply.error(cmdword,
                                     'Controller is not available (no '
                                     'hardware backend)')
        return ctrl, None

    def _busy_note(self, cmdword: str) -> str:
        """취득 중이면 **경고를 남기고 응답에 붙일 문구**를 돌려준다.

        ⭐ **거부하지 않는다** (운영자 확정 2026-09-04) -- *"받되 경고+응답에
        표시 하면 되"*.  `APPLYMOD09`/`APPLYDIO09` 가 진공 게이지를 읽는
        MOD10 VCPU 를 재시작하므로 지금 도는 프레임의 `DEWPRES` 는 결측이
        되는데, 그 결측은 받아들이기로 했다.
        """
        seq = getattr(self.app, 'seq', None)
        if seq is None or not seq.busy:
            return ''
        log.warning('%s 를 **취득 중에** 받았다 -- APPLYMOD/APPLYDIO 가 진공 '
                    '게이지를 읽는 MOD10 VCPU 를 재시작하므로 지금 도는 '
                    '프레임의 DEWPRES 가 결측이 된다.  ⭐ 거부하지 않는다 '
                    '(운영자 확정).  결측까지 피하려면 HK 기록 주기(기본 '
                    '60초)를 비켜 보낼 것', cmdword)
        return 'DuringAcquisition=1'

    def _finish(self, dest: str, cmdword: str, body: str, note: str) -> None:
        """왕복이 끝난 뒤 보내는 늦은 `DONE` -- 주석 문구를 괄호로 붙인다."""
        if note:
            body = '%s (%s)' % (body, note)
        self.emit.done(dest, cmdword, body)

    def cmd_htrset(self, msg: Message, target: Target) -> Reply:
        """HTRSET <0|1> <섭씨> -- 히터 Enable + 목표온도.  인자 없으면 조회.

        ⭐ **인자 둘이다** (운영자 확정 2026-09-04 -- 원안으로 되돌렸다).
        `HTREN` 이라는 별도 명령은 **없다**.  ⚠️ 다만 **헤더 카드는 `HTREN` 과
        `HTRSET` 으로 나뉘어** 실린다 -- 명령의 모양과 카드의 모양이 다른 것이
        의도다 (카드는 각 값을 따로 읽을 수 있어야 한다).

        한계는 상수가 아니라 **ACF 를 두 걸음 타서** 얻고, 넘으면 거부가
        아니라 **한계로 접고 응답에 적는다** (`heater.clamp`).
        """
        ctrl, bad = self._ctrl('HTRSET')
        if bad is not None:
            return bad
        arg = msg.body.strip()
        if not arg:
            self.app.spawn(self._do_heater_query(msg.src, ctrl, 'HTRSET'))
            return Reply.noop()
        parts, bad = self._split('HTRSET', arg, 2, 'HTRSET <0|1> <celsius>')
        if bad is not None:
            return bad
        on = ONOFF.get(parts[0].upper())
        if on is None:
            return Reply.error('HTRSET', _unknown(parts[0]))
        celsius, bad = self._number('HTRSET', parts[1], 'temperature')
        if bad is not None:
            return bad
        busy = self._busy_note('HTRSET')
        self.app.spawn(self._do_htrset(msg.src, ctrl, on, celsius, busy))
        return Reply.noop()

    async def _do_htrset(self, dest: str, ctrl, on: bool,  # noqa: ANN001
                         celsius: float, busy: str) -> None:
        try:
            value, note = await heater.set_target(ctrl, on, celsius)
        except Exception as exc:  # noqa: BLE001
            self.emit.error(dest, 'HTRSET', 'Failed: %s' % exc)
            return
        self._finish(dest, 'HTRSET', 'Enable=%d Target=%.2f' % (int(on), value),
                     ' '.join(x for x in (busy, note) if x))

    async def _do_heater_query(self, dest: str, ctrl,  # noqa: ANN001
                              cmdword: str) -> None:
        """히터 다섯의 조회 -- **컨트롤러에서 되읽어** 답한다.

        ⭐ 어느 키를 읽고 어떤 이름표로 답할지는 `heater.GROUPS` 한 표가
        정한다 -- 설정 응답과 조회 응답이 **같은 낱말**을 쓰게 하려는 것이다.
        ⚠️ 하나라도 못 읽으면 부분 답을 내지 않고 통째로 `ERROR` 다 -- 일부만
        답하면 나머지가 **옛 값인지 못 읽은 것인지** 구별되지 않는다.
        """
        try:
            body = await heater.read_group(ctrl, cmdword)
        except Exception as exc:  # noqa: BLE001
            self.emit.error(dest, cmdword, 'Readback failed: %s' % exc)
            return
        self.emit.done(dest, cmdword, body)

    def cmd_vacgauge(self, msg: Message, target: Target) -> Reply:
        """VACGAUGE [ON|OFF] -- ⭐ **이온게이지 켜기/끄기**.  없으면 조회.

        ⛔ **끄는 것이 목적이다** -- 게이지 필라멘트가 science 영상을
        오염시키므로(운영자) science 노출 전에 **ICS 가 이 명령을 보낸다.**
        끈 동안 `DEWPRES` 는 sentinel 로 내려간다 -- 모듈이 Conductron 값을
        계속 내보내는데 그것이 정상값처럼 보이기 때문이다 (`gauge.py` 머리말).
        """
        state = getattr(self.app, 'gauge', None)
        if state is None:
            return Reply.error('VACGAUGE', 'Gauge control is not available')
        arg = msg.body.strip()
        if not arg:
            # ⚠️ **게이지에 물어본 값이 아니다** -- 우리가 아는 설정값이다.
            #   출처를 함께 적어 운영자가 그 차이를 알게 한다.
            return Reply.done('VACGAUGE', 'Gauge=%s Origin=%s Method=%s'
                              % (state.word, state.origin, state.method))
        ctrl, bad = self._ctrl('VACGAUGE')
        if bad is not None:
            return bad
        want = ONOFF.get(arg.upper())
        if want is None:
            return Reply.error('VACGAUGE', _unknown(arg))
        busy = self._busy_note('VACGAUGE')
        self.app.spawn(self._do_vacgauge(msg.src, ctrl, state, want, busy))
        return Reply.noop()

    async def _do_vacgauge(self, dest: str, ctrl, state,  # noqa: ANN001
                           on: bool, busy: str) -> None:
        try:
            note = await state.set(ctrl, on)
        except Exception as exc:  # noqa: BLE001
            self.emit.error(dest, 'VACGAUGE', 'Failed: %s' % exc)
            return
        self._finish(dest, 'VACGAUGE', 'Gauge=%s' % state.word,
                     ' '.join(x for x in (busy, note) if x))

    # -- 히터 나머지 셋 (운영자 확정 2026-09-04) ---------------------------

    def _split(self, cmdword: str, body: str, n: int, usage: str):  # noqa: ANN202
        """인자를 **정확히 n개**로 가른다.  어긋나면 `(None, Reply)`.

        ⚠️ 모자란 것과 남는 것을 **둘 다** 거부한다.  ⭐ 남는 것을 조용히
        버리면 옛 문법(`HEATERSET <enable> <target>`)으로 보낸 사람이
        *"DONE 인데 아무것도 안 바뀐"* 상태를 만난다 -- `HTRSET` 이 이미 그
        자리에서 같은 이유로 2인자를 거부한다.
        """
        parts = body.split()
        if len(parts) != n:
            return None, Reply.error(cmdword, 'Usage: %s' % usage)
        return parts, None

    def _number(self, cmdword: str, word: str, what: str, cast=float):  # noqa: ANN202,ANN001
        """숫자 인자 하나.  못 읽으면 `(None, Reply)`."""
        try:
            return cast(word), None
        except ValueError:
            return None, Reply.error(cmdword, 'Invalid %s: %s' % (what, word))

    def cmd_htrforce(self, msg: Message, target: Target) -> Reply:
        """HTRFORCE <0|1> <레벨 V> -- 강제 출력.  인자 없으면 조회.

        ⛔ **PID 를 우회한다** -- 켜면 센서 온도와 무관하게 레벨이 그대로
        나가고 `HEATERALIMIT`(PID 모드 전용 상한)은 **안 걸린다**.  ⭐ 별도
        운영 상한은 두지 않는다 (운영자 확정 2026-09-04: *"FORCELEVEL 로
        출력전압을 조절하니 운영하는 쪽에서 알아서 한다"*) -- 대신 모듈
        범위(0~25 V) 밖은 거부하고 `Force=1` 인 동안은 응답·로그에 그
        사실을 상시 표시한다 (DevNote 11.13 F3).
        """
        ctrl, bad = self._ctrl('HTRFORCE')
        if bad is not None:
            return bad
        arg = msg.body.strip()
        if not arg:
            self.app.spawn(self._do_heater_query(msg.src, ctrl, 'HTRFORCE'))
            return Reply.noop()
        parts, bad = self._split('HTRFORCE', arg, 2,
                                 'HTRFORCE <0|1> <level V>')
        if bad is not None:
            return bad
        on = ONOFF.get(parts[0].upper())
        if on is None:
            return Reply.error('HTRFORCE', _unknown(parts[0]))
        level, bad = self._number('HTRFORCE', parts[1], 'level')
        if bad is not None:
            return bad
        busy = self._busy_note('HTRFORCE')
        self.app.spawn(self._do_htrforce(msg.src, ctrl, on, level, busy))
        return Reply.noop()

    async def _do_htrforce(self, dest: str, ctrl, on: bool,  # noqa: ANN001
                           level: float, busy: str) -> None:
        try:
            note = await heater.set_force(ctrl, on, level)
        except Exception as exc:  # noqa: BLE001
            self.emit.error(dest, 'HTRFORCE', 'Failed: %s' % exc)
            return
        self._finish(dest, 'HTRFORCE', 'Force=%d Level=%g' % (int(on), level),
                     ' '.join(x for x in (busy, note) if x))

    def cmd_htrramp(self, msg: Message, target: Target) -> Reply:
        """HTRRAMP <0|1> <mK/update> -- 목표온도 램프.  인자 없으면 조회.

        ⚠️ `RAMPRATE` 는 초당이 아니라 **update time 당**이라, ACF 의
        `HEATERUPDATETIME` 이 바뀌면 같은 값의 뜻이 바뀐다 -- 그래서 응답에
        **ACF 에서 읽은 환산값**을 함께 싣는다 (`1 mK/s = 3.6 K/h`).
        """
        ctrl, bad = self._ctrl('HTRRAMP')
        if bad is not None:
            return bad
        arg = msg.body.strip()
        if not arg:
            self.app.spawn(self._do_heater_query(msg.src, ctrl, 'HTRRAMP'))
            return Reply.noop()
        parts, bad = self._split('HTRRAMP', arg, 2,
                                 'HTRRAMP <0|1> <rate mK/update>')
        if bad is not None:
            return bad
        on = ONOFF.get(parts[0].upper())
        if on is None:
            return Reply.error('HTRRAMP', _unknown(parts[0]))
        rate, bad = self._number('HTRRAMP', parts[1], 'rate', int)
        if bad is not None:
            return bad
        busy = self._busy_note('HTRRAMP')
        self.app.spawn(self._do_htrramp(msg.src, ctrl, on, rate, busy))
        return Reply.noop()

    async def _do_htrramp(self, dest: str, ctrl, on: bool,  # noqa: ANN001
                          rate: int, busy: str) -> None:
        try:
            note = await heater.set_ramp(ctrl, on, rate)
        except Exception as exc:  # noqa: BLE001
            self.emit.error(dest, 'HTRRAMP', 'Failed: %s' % exc)
            return
        self._finish(dest, 'HTRRAMP', 'Ramp=%d RampRate=%d' % (int(on), rate),
                     ' '.join(x for x in (busy, note) if x))

    def cmd_htrpid(self, msg: Message, target: Target) -> Reply:
        """HTRPID <P> <I> <D> -- PID 게인 셋.  인자 없으면 조회.

        ⭐ **이 명령이 있어야 히터가 실제로 데워진다** -- 현행 guide ACF 는
        게인이 전부 0이라 목표를 아무리 줘도 출력 0 V 다 (DevNote 11.13 F1).
        ⚠️ `IL`(적분항 상한)·`UPDATETIME` 은 **ACF 소관**이라 안 만진다.
        """
        ctrl, bad = self._ctrl('HTRPID')
        if bad is not None:
            return bad
        arg = msg.body.strip()
        if not arg:
            self.app.spawn(self._do_heater_query(msg.src, ctrl, 'HTRPID'))
            return Reply.noop()
        parts, bad = self._split('HTRPID', arg, 3, 'HTRPID <P> <I> <D>')
        if bad is not None:
            return bad
        gains = []
        for word, what in zip(parts, ('P', 'I', 'D')):
            val, bad = self._number('HTRPID', word, what)
            if bad is not None:
                return bad
            gains.append(val)
        busy = self._busy_note('HTRPID')
        self.app.spawn(self._do_htrpid(msg.src, ctrl, gains, busy))
        return Reply.noop()

    async def _do_htrpid(self, dest: str, ctrl, gains,  # noqa: ANN001
                         busy: str) -> None:
        try:
            note = await heater.set_pid(ctrl, *gains)
        except Exception as exc:  # noqa: BLE001
            self.emit.error(dest, 'HTRPID', 'Failed: %s' % exc)
            return
        self._finish(dest, 'HTRPID', 'P=%g I=%g D=%g' % tuple(gains),
                     ' '.join(x for x in (busy, note) if x))

    # -- CCD flush · 전원 · 바이패스 (운영자 지시 2026-09-05) ------------------
    #
    # 넷은 히터·게이지와 **같은 늦은-DONE 규약**(`Reply.noop()` → 왕복 → `_finish`/
    # `emit.error`)을 쓰되 두 가지가 다르다: ① 취득 중이면 **거부**한다 (결측
    # 창이 아니라 자료 손상이 대가다) ② `_ctrl()` 이 아니라 **백엔드 표면**을
    # 부른다 (Sim 에서도 돌아야 한다 -- 원시 함수는 실기·Sim 둘 다 있다).

    def _guide(self, cmdword: str):  # noqa: ANN202
        """guide 백엔드와 **거부 Reply** 를 짝으로 -- `_ctrl()` 의 백엔드 판.

        `IcgArchon` 은 늘 `guide` 를 갖지만(`GuideBackend`/`SimGuideBackend`)
        단위 하네스가 빼 둘 수 있다 -- 그때 조용히 `DONE` 을 내면 *"먹었는데
        아무것도 안 바뀜"* 이다 (`_ctrl` 과 같은 이유).
        """
        be = getattr(self.app, 'guide', None)
        if be is None:
            return None, Reply.error(cmdword, 'Guide backend is not available')
        return be, None

    def _refuse_if_busy(self, cmdword: str):  # noqa: ANN202
        """취득 중이거나 다른 CCD 조작이 왕복 중이면 거부 Reply, 아니면 `None`.

        ⭐ `_busy_note()` 와 반대 방향이다 -- 그쪽은 받되 표시하고, 이쪽은
        거부한다.  이유는 머리말: 진행 중 노출 위의 `LOADPARAMS`(flush) ·
        `POWEROFF` · 원문 `RESETTIMING` 은 그 프레임을 망친다.
        """
        seq = getattr(self.app, 'seq', None)
        if seq is not None and seq.busy:
            return Reply.error(cmdword, BUSY_REFUSAL)
        if self._op_in_flight:
            return Reply.error(cmdword, 'Busy with %s -- wait for its DONE'
                               % self._op_in_flight)
        return None

    def _lock_note(self) -> str:
        """`EXPENABLE OFF` 면 응답에 붙일 주석 -- 막지는 않는다 (노출이 아니다)."""
        flag = self._expenable()
        if flag is not None and not flag.allowed:
            return 'ExpEnable=OFF'
        return ''

    def _no_args(self, cmdword: str, msg: Message):  # noqa: ANN202
        """인자를 받지 않는 명령 -- 남는 것을 조용히 버리지 않는다 (`_split` 규칙)."""
        if msg.body.strip():
            return Reply.error(cmdword, 'Usage: %s (no arguments)' % cmdword)
        return None

    def _begin_op(self, cmdword: str) -> None:
        self._op_in_flight = cmdword

    def _end_op(self, cmdword: str) -> None:
        if self._op_in_flight == cmdword:
            self._op_in_flight = ''

    def cmd_ccdflush(self, msg: Message, target: Target) -> Reply:
        """CCDFLUSH -- 유휴 CCD 를 `FlushFrame` 한 바퀴로 비운다 (프레임 없음).

        백엔드 `flush_ccd()` = `FirstFlush=1`·`Exposures=0` 을 `LOADPARAMS` 로
        걸고 설정 메모리의 `FirstFlush` 를 0 으로 되쓴다 (`controller.flush_now`,
        guide ACF R2613+ -- 슬롯이 없으면 `GuideBackendError` 로 `ERROR`).
        ⭐ `EXPENABLE OFF` 여도 허용한다 -- flush 는 노출이 아니다.  대신 응답에
        `ExpEnable=OFF` 를 덧붙여 잠긴 상태에서 한 일임을 남긴다.
        """
        be, bad = self._guide('CCDFLUSH')
        if bad is not None:
            return bad
        bad = self._no_args('CCDFLUSH', msg)
        if bad is not None:
            return bad
        bad = self._refuse_if_busy('CCDFLUSH')
        if bad is not None:
            return bad
        note = self._lock_note()
        log.info('CCDFLUSH by %s -- 유휴 CCD 를 FlushFrame 한 바퀴로 비운다%s',
                 msg.src, ' (EXPENABLE OFF 상태 -- flush 는 노출이 아니라 허용)'
                 if note else '')
        self._begin_op('CCDFLUSH')
        self.app.spawn(self._do_ccdflush(msg.src, be, note))
        return Reply.noop()

    async def _do_ccdflush(self, dest: str, be, note: str) -> None:  # noqa: ANN001
        try:
            try:
                await be.flush_ccd()
            except Exception as exc:  # noqa: BLE001
                log.error('CCDFLUSH 실패 -- %s', exc)
                self.emit.error(dest, 'CCDFLUSH', 'Failed: %s' % exc)
                return
            self._finish(dest, 'CCDFLUSH', 'Flushed=1', note)
        finally:
            self._end_op('CCDFLUSH')

    def cmd_ccdpowon(self, msg: Message, target: Target) -> Reply:
        """CCDPOWON -- CCD 전원 ON (`POWERON` + `poweron_wait` 초의 flush 대기).

        ⚠️ **`DONE` 이 수 초 뒤에 온다** (`[icg] poweron_wait`, 기본 12 s) -- 그
        시간은 전원 램프가 아니라 CCD flush 대기라 줄이지 않는다
        (`controller.power_on`).  그동안 `GO` 는 거부된다 (`cmd_go`).
        ⭐ 접속·ACF 는 하지 않는다 -- 기동 접속(`_connect_controller`)이나 첫
        `GO` 의 `prepare()` 가 그 몫이고, 접속 전이면 `ERROR … Failed` 다.
        """
        return self._ccdpower(msg, 'CCDPOWON', True)

    def cmd_ccdpowoff(self, msg: Message, target: Target) -> Reply:
        """CCDPOWOFF -- CCD 전원 OFF (`POWEROFF`).  다음 `GO` 가 다시 켠다.

        ⚠️ `controller.power_off()` 는 **실패를 올리지 않는다** (`finally` 자리용
        설계 -- 로그만 남긴다).  그래서 여기서는 왕복 뒤 `ctrl.powered` 가 아직
        참이면 `ERROR` 로 옮긴다 -- 안 그러면 링크가 죽어 있어도 `Power=OFF`
        라고 답해 운영자가 바이어스가 내려갔다고 믿는다.
        """
        return self._ccdpower(msg, 'CCDPOWOFF', False)

    def _ccdpower(self, msg: Message, cmdword: str, on: bool) -> Reply:
        be, bad = self._guide(cmdword)
        if bad is not None:
            return bad
        bad = self._no_args(cmdword, msg)
        if bad is not None:
            return bad
        bad = self._refuse_if_busy(cmdword)
        if bad is not None:
            return bad
        note = self._lock_note()
        log.info('%s by %s -- CCD 전원 %s%s', cmdword, msg.src,
                 'ON (POWERON, poweron_wait 뒤 DONE)' if on else 'OFF (POWEROFF)',
                 ' (EXPENABLE OFF 상태)' if note else '')
        self._begin_op(cmdword)
        self.app.spawn(self._do_ccdpower(msg.src, be, cmdword, on, note))
        return Reply.noop()

    async def _do_ccdpower(self, dest: str, be, cmdword: str,  # noqa: ANN001
                           on: bool, note: str) -> None:
        try:
            try:
                await be.power_ccd(on)
            except Exception as exc:  # noqa: BLE001
                log.error('%s 실패 -- %s', cmdword, exc)
                self.emit.error(dest, cmdword, 'Failed: %s' % exc)
                return
            ctrl = getattr(be, 'ctrl', None)
            if not on and ctrl is not None and getattr(ctrl, 'powered', False):
                # `power_off()` 가 삼킨 실패 -- 확인된 상태(`powered`)가 안 바뀌었다.
                log.error('%s -- POWEROFF 가 확인되지 않았다 (powered 가 그대로 참). '
                          '유닛 전원 상태를 직접 확인할 것', cmdword)
                self.emit.error(dest, cmdword,
                                'Failed: POWEROFF was not acknowledged -- check '
                                'the unit power (see log)')
                return
            self._finish(dest, cmdword, 'Power=%s' % ('ON' if on else 'OFF'), note)
        finally:
            self._end_op(cmdword)

    def cmd_archon(self, msg: Message, target: Target) -> Reply:
        """ARCHON <명령 원문…> -- 컨트롤러 바이패스.  guide 는 한 대라 태그가 없다.

        원문을 **그대로** 보낸다 (공백만 접는다 -- `controller.raw_command`).
        대소문자도 안 바꾼다: `WCONFIG` 본문(타이밍 스크립트 줄)은 대소문자가
        뜻이다.  ⚠️ 그래서 **명령 이름은 대문자로 칠 것** -- 컨트롤러는 모르는
        명령에 **무응답**이라(매뉴얼 p.45) 소문자 `status` 는 시한 초과 →
        링크 재수립 → `ERROR … Failed` 가 된다.

        응답 원문을 `DONE: ARCHON <원문>` 으로 되돌린다.  `ARCHON_REPLY_MAX`
        를 넘으면 잘라 표시하고 **전문은 `log.info`** 로 남긴다.  `?xx` 거부는
        `ERROR: ARCHON rejected: <보낸 원문>`.  ⚠️ 위생 검사 없음 -- 운영자
        도구다.  ⛔ 취득 중이면 거부한다 -- 진행 중 노출 위의 `RESETTIMING`
        같은 원문은 그 프레임을 망친다.
        """
        be, bad = self._guide('ARCHON')
        if bad is not None:
            return bad
        text = ' '.join(msg.body.split())
        if not text:
            return Reply.error('ARCHON', 'Usage: ARCHON <command>')
        bad = self._refuse_if_busy('ARCHON')
        if bad is not None:
            return bad
        note = self._lock_note()
        log.info('ARCHON by %s -- 원문 바이패스: %r%s', msg.src, text,
                 ' (EXPENABLE OFF 상태)' if note else '')
        self._begin_op('ARCHON')
        self.app.spawn(self._do_archon(msg.src, be, text, note))
        return Reply.noop()

    async def _do_archon(self, dest: str, be, text: str,  # noqa: ANN001
                         note: str) -> None:
        try:
            try:
                reply = await be.raw_command(text)
            except ArchonError as exc:
                if exc.reply_error:
                    # 컨트롤러가 `?xx` 로 거부했다 -- 내 명령이 틀린 것이고
                    # 링크는 멀쩡하다 (`controller.cmd` 주석).
                    log.warning('ARCHON %r -- 컨트롤러가 거부했다 (%s)', text, exc)
                    self.emit.error(dest, 'ARCHON', 'rejected: %s' % text)
                    return
                log.error('ARCHON %r 실패 -- %s', text, exc)
                self.emit.error(dest, 'ARCHON', 'Failed: %s' % exc)
                return
            except Exception as exc:  # noqa: BLE001
                log.error('ARCHON %r 실패 -- %s', text, exc)
                self.emit.error(dest, 'ARCHON', 'Failed: %s' % exc)
                return
            # ⭐ 전문은 로그에 -- 응답이 잘려도 여기서 다 볼 수 있다.
            log.info('ARCHON %r -> %d bytes: %s', text, len(reply), reply)
            self._finish(dest, 'ARCHON', self._clip_reply(reply), note)
        finally:
            self._end_op('ARCHON')

    @staticmethod
    def _clip_reply(reply: str) -> str:
        """응답 원문 -> 메시지 본문.  ASCII 로 접고 상한을 넘으면 잘라 표시한다.

        빈 응답(`WCONFIG`/`LOADPARAMS`/`APPLY*` 의 성공 ack)은 `DONE: ARCHON`
        만 나가 *됐는지* 가 안 보이므로 그 사실을 적는다.
        """
        text = reply.encode('ascii', 'replace').decode('ascii')
        # 한 줄 프로토콜이다 -- 종료문자·널이 섞이면 수신측이 malformed 로 버린다.
        text = text.replace('\r', ' ').replace('\n', ' ').replace('\0', ' ').strip()
        if not text:
            return '(accepted, empty reply)'
        if len(text) <= ARCHON_REPLY_MAX:
            return text
        return '%s ...(+%d bytes truncated, see log)' % (
            text[:ARCHON_REPLY_MAX], len(text) - ARCHON_REPLY_MAX)

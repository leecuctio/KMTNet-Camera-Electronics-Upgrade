#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""icg 명령 -- science 명령 처리부 상속 + 텔레메트리 명령 추가.

레거시 계승: ICG 는 ICS 와 **같은 명령 테이블**을 썼으므로(`PAP7KX.CMD`,
icg_legacy_report 8.1절) `OBJECT`/`DARK`/`EXP`/`GO`/`STOP`/`ABORT` 등은
`ics_sim.commands.Dispatcher` 를 상속해서 그대로 받는다.  실측 관측된
전용 명령은 `GUIEXP` 하나다 (레거시 실측은 `GUIDEEXP` -- 2026-09-08 에 줄였다).

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

⛔ 앞의 셋은 **취득 중이면 거부**한다 (`ERROR: … Exposure in progress -- ABORT
first`) -- 히터·게이지와 반대다.  그쪽은 결측 창 하나가 대가지만, 이쪽은
진행 중 노출 위에 `LOADPARAMS`/`POWEROFF` 가 들어가 **자료를 망친다**.  ⭐ 그리고
**셋이 서로도, `GO` 도 막는다** (`_op_in_flight`) --
`POWERON` 의 `poweron_wait` 동안 들어온 `GO` 는 `prepare()` 가 이미 `powered`
라 그대로 arm 해 flush 가 안 끝난 CCD 를 찍는다.  ⚠️ `EXPENABLE` 잠금과는
**무관하게 허용**한다 (flush·전원·바이패스는 노출이 아니다) -- 잠겨 있으면
응답에 `ExpEnable=OFF` 를 덧붙여 알리기만 한다.

⭐ `ARCHON` 은 **제한이 없다** (운영자 2026-09-05 *"제한 없이 모두 풀어줘"*) -- 취득
중이든 다른 조작이 왕복 중이든 받고, 자기도 `GO` 를 막지 않는다(`_op_in_flight` 를
잡지 않는다).  진행 중 노출 위의 `RESETTIMING` 같은 원문이 그 프레임을 망치는 것은
운영자의 몫이다 -- 로그에는 남는다.

⭐ 히터·게이지의 `_ctrl()` 이 아니라 **백엔드 표면**(`flush_ccd`/`power_ccd`/
`raw_command`)을 부른다 -- 그래서 컨트롤러 없는 Sim 에서도 돈다 (Sim 의
`raw_command` 는 `SIM (no controller): …` 를 돌려준다).
"""

from __future__ import annotations

import logging

from ics_archon import _simpath

_simpath.ensure()

from ics_archon.archon import trigout as trigout_core  # noqa: E402
from ics_archon.archon.protocol import ArchonError  # noqa: E402
from ics_sim import commands as sim_commands  # noqa: E402
from ics_sim import emitter  # noqa: E402
from ics_sim.commands import Reply  # noqa: E402
from ics_sim.impv2 import MAX_LEN, Message  # noqa: E402
from ics_sim.nodes import Target  # noqa: E402

from . import expenable as expen  # noqa: E402
from . import heater  # noqa: E402
from . import hkdata  # noqa: E402
from .radionode import RadionodeError  # noqa: E402

log = logging.getLogger('icg_archon.cmd')

#: emitter 의 커맨드워드 어휘에 icg 몫을 더한다 -- `validate()` 가 이 표로
#: 발신을 검사하므로, 등록 없이 새 커맨드워드를 쓰면 위생 검사가 운다
#: (`unknown_cmdword` -- `emit.violations` 에 쌓이고 경고 로그가 난다).
ICG_COMMANDS = frozenset({'GUIEXP', 'HK', 'HKDATA', 'RADIONODE', 'EXPENABLE',
                          'TRIGOUT', 'TRIGOUTFORCE', 'TRIGOUTLEVEL',
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

    def cmd_guiexp(self, msg: Message, target: Target) -> Reply:
        """GUIEXP <초> -- 가이드 노출시간(독출 개시 간격) 설정.

        ⭐ **낱말을 `GUIDEEXP` 에서 줄였다** (운영자 2026-09-08).  값 의미는
        `EXPTIME` = 독출 개시 간격이다 (raw spec 10.1절) -- `EXP` 와 **같은
        상태 필드**를 채우므로 어느 쪽으로 설정해도 같다 (guide 는 `EXP` 의
        `BIAS` 가드도 풀어 뒀다 -- `cmd_exp`).
        ⚠️ `EXP` 를 남겨 두는 것은 **초점조절 유틸리티(gmon)가 그것을 쓰기**
        때문이다 (운영자) -- 아니었으면 `GUIEXP` 하나만 뒀다.
        ⛔ 레거시 실측 낱말은 `GUIDEEXP` 였다(icg_legacy_report 5.2절) --
        옛 낱말로 보내는 발신자가 있으면 `Didn't understand` 가 된다.
        """
        arg = msg.body.strip()
        if not arg:
            return Reply.done('GUIEXP',
                              'GuiExp=%g seconds.' % self.state.exptime)
        try:
            seconds = float(arg)
        except ValueError:
            return Reply.error('GUIEXP', 'Invalid exposure time: %s' % arg)
        if seconds < 0:
            return Reply.error('GUIEXP', 'Invalid exposure time: %s' % arg)
        self.state.exptime = seconds
        return Reply.done('GUIEXP', 'GuiExp=%g seconds.' % seconds)

    def cmd_hk(self, msg: Message, target: Target) -> Reply:
        """HK [NOW] -- `HKDATA` 와 **같은 본문**을 낸다 (운영자 지시 2026-09-06).

        ⭐ 커맨드워드만 다르다 -- 조립은 `hkdata.body()` **한 곳뿐**이다.  두
        명령이 다른 본문을 내면 어느 쪽이 정본인지 다투게 된다.

        ⚠️ **종전 `HK` 가 내던 `C1_TEMP=40.1|41.2|…` 는 빠진다** -- 확정 문면
        (DevNote 11.14-(1))에 그 필드가 없고, *"둘이 같은 본문"* 지시가 그보다
        뒤다.  그 값은 `ARCHON STATUS` 응답과 HK CSV 에 그대로 남는다.
        """
        return self._hk_reply(msg, 'HK')

    def cmd_hkdata(self, msg: Message, target: Target) -> Reply:
        """HKDATA [NOW] -- ICS 가 **자기 헤더를 채우려고** 묻는 것.

        ⭐ **인자가 없으면 폴링값** (60초 주기, 왕복 없음), **`NOW` 면 즉시
        되읽기** (운영자 확정 2026-09-09).  ⛔ 갈리는 것은 **히터 설정 셋**
        (`HTREN`·`HTRSET`·`HTRFORCE`) 하나뿐이다 -- 나머지는 원래부터 폴링값이다.
        ⚠️ 낡음은 `HKUDATE`·`HKSTALE` 이 그대로 알린다.

        문면은 DevNote 11.14-(1) 운영자 확정이고 조립은 `hkdata.py` 다.
        게이지·히터는 **ICG 만** 만지므로 이 응답에 없는 값은 ICS 가 만들 길이
        없다 -- 그래서 빠진 자리는 ICS 가 규격 5.0절 sentinel 로 채운다.
        """
        return self._hk_reply(msg, 'HKDATA')

    def _log_latency(self, what: str, t0: float, extra: str = '',
                     always: bool = False) -> float:
        r"""⏳ **수신 -> 완료 지연을 남긴다** (2026-09-09 실측용).  ms 를 돌려준다.

        ⭐ **왜 로그로 남기나**: 종전에는 `HKQDATE`(명령 수신 시각)와 응답
        로그 줄의 시각을 **눈으로 빼야** 했다 -- 연속 노출 중에 여러 번 치며
        재려면 그 뺄셈이 실측을 가로막는다.  한 줄에 이미 뺀 값을 적는다.

        ## 늘 남기는 것과 임계를 타는 것이 갈린다

        * `always=True` -- **`TRIGOUT` 계열**.  운영자가 칠 때만 나가는 드문
          명령이라 로그를 덮을 수가 없고, ⭐ 그 지연 자체가 진단 값이다.
        * `always=False` -- **`HKDATA`/`HK`**.  ⚠️ 이쪽만 임계를 탄다
          (`[icg] latency_warn_ms`, 기본 50 ms): 우리 프로그램은 이 명령을
          **스스로 보내지 않지만**, 바깥 감시 계통이 초 단위로 물어 올 수는
          있어서다.  임계 아래는 `DEBUG` 로 내린다.

        ⛔ **종전에 적어 둔 근거 *"`HKDATA` 는 프레임마다 온다"* 는 틀렸다**
        (2026-09-09 정정).  `ics_archon/app.py` 의 `_ask_icg('HKDATA')` 를
        부르는 곳은 **명령 처리기 둘뿐**이고 주기 발신자가 없다 -- 빈도를
        정하는 것은 바깥이다.

        ⏳ **실측 뒤에 임계를 다시 정한다** -- 취득 중 정상 지연이 50 ms 를
        늘 넘으면 그 기본값은 *"이상"* 이 아니라 **소음**이 된다.
        ⭐ **벤치에서는 `latency_warn_ms = 0` 으로 두어 전부 남긴다** -- 그것이
        이 눈금의 시험용 자리다.

        ⛔ 이 값은 **락 대기 + 왕복 처리**를 합친 것이다 -- 둘을 가르지
        않는다.  가르려면 `_locked_thread` 안팎에 각각 시각을 찍어야 하는데,
        그것은 `controller.last_cmd_timing`(스레드 안 RTT)과 이 값의 차로
        나중에 얻을 수 있다.
        """
        import time
        ms = (time.monotonic() - t0) * 1000.0
        seq = getattr(self.app, 'seq', None)
        busy = '취득중' if (seq is not None and seq.busy) else '한가'
        # ⛔ **`self.cfg` 가 아니라 `app.icfg` 다** -- 앞은 ics_sim 설정이라
        # 이 눈금이 없고, 그러면 벤치에서 `0` 으로 낮춰도 기본값 50 이 살아
        # **재려던 줄이 `DEBUG` 로 숨는다** (2026-09-09 시험이 잡았다).
        icfg = getattr(self.app, 'icfg', None)
        cap = float(getattr(icfg, 'latency_warn_ms', 50.0) or 0.0)
        line = '%s 지연 -- 수신→완료 %.1f ms (%s)%s'
        args = (what, ms, busy, (' %s' % extra) if extra else '')
        if always or ms >= cap:
            log.info(line, *args)
        else:
            log.debug(line, *args)
        return ms

    def _hk_reply(self, msg: Message, cmdword: str) -> Reply:
        """`HK`/`HKDATA` 공통 진입 -- 인자는 `NOW` 하나뿐이다.

        ⚠️ **늦은 `DONE`** 이다.  ⭐ 기본 갈래는 왕복이 없어 동기로도 답할 수
        있지만 **한 경로로 둔다** -- 갈래마다 응답 방식이 다르면 받는 쪽이 두
        가지를 다뤄야 한다.  `NOW` 는 `RCONFIG` 셋이라 어차피 늦은 `DONE` 이다.
        ⛔ **모르는 인자는 거절한다** -- `HKDATA NOWW` 를 조용히 폴링값으로
        답하면 운영자가 *"즉시 읽었는데 옛 값이 온다"* 로 읽는다.
        """
        if getattr(self.app, 'hk', None) is None:
            return Reply.error(cmdword, 'HK monitor is not running')
        arg = msg.body.split()
        if len(arg) > 1 or (arg and arg[0].upper() != 'NOW'):
            return Reply.error(cmdword,
                               "Usage: %s [NOW] -- got '%s'"
                               % (cmdword, msg.body.strip()))
        import time
        self.app.spawn(self._do_hkdata(msg.src, cmdword, time.monotonic(),
                                       now=bool(arg)))
        return Reply.noop()

    async def _do_hkdata(self, dest: str, cmdword: str,
                         t0: float | None = None, now: bool = False) -> None:
        """본문을 만들어 늦은 `DONE` 으로 답한다.

        ⏳ `t0`(수신 monotonic)가 있으면 **지연을 로그로 남긴다** -- 연속
        노출 중 `RCONFIG` 셋이 FETCH 락 뒤에 얼마나 밀리는지가 관측 대상이다
        (`_log_latency`, DevNote 11.53).
        """
        try:
            body = await hkdata.body(self.app, now=now)
        except Exception as exc:  # noqa: BLE001
            self.emit.error(dest, cmdword, 'Failed: %s' % exc)
            return
        if t0 is not None:
            self._log_latency(cmdword + (' NOW' if now else ''), t0)
        self.emit.done(dest, cmdword, body or 'no fresh HK sample yet')

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
        # ⭐ **뒷정리 중이면 그 사실을 말한다** (운영자 2026-09-09).  기반은
        # `Data acquisition already in progress!` 하나로 답하는데, `STOP` 뒤
        # 꼬리 소화 구간에서는 **틀린 그림**이다 -- 저장은 이미 끝났고 컨트롤러
        # 꼬리를 기다리는 중이다 (벤치 2026-09-08: `guiexp 15` 에서 32초).
        # ⚠️ **거절은 그대로 한다** -- 그 꼬리를 다음 시퀀스가 제 첫 프레임으로
        # 알면 남의 픽셀이 정상 헤더로 저장된다 (9.15-(9)).
        seq = getattr(self.app, 'seq', None)
        if seq is not None and getattr(seq, 'settling', False):
            return Reply.error(
                'GO', 'Finishing previous sequence (draining controller '
                      'tail frame) -- retry shortly')
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
        if not want:
            # ⭐ **펄스도 끊는다** (운영자 2026-09-09) -- `EXPENABLE OFF` 도
            # 사이클을 세우는 경로이므로 `ABORT` 와 같은 자리다.  ⚠️ `busy` 와
            # 무관하다: 취득 중이 아니어도 펄스는 돌 수 있다.
            self.app.spawn(self.release_pulse('EXPENABLE OFF'))
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

        백엔드 `flush_ccd()` = `Exposures=0` 을 `LOADPARAMS` 로 걸어 코어가 `FlushFrame`
        을 한 번 돌게 한다 -- flush 는 ACF 의 `FirstFlush=1` 상수가 싣는다 (`controller.flush_now`,
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

    # -- Trigger Out (셔터 자리의 실기 명령) --------------------------------
    #
    # ⛔ **guide 에는 셔터가 없다** (frame-transfer, 규격 10.1 "셔터 무관").
    # 기반의 `SHOPEN`/`SHCLOSE` 는 상속으로 살아 있는데, guide 에서는 셔터
    # 대신 **Archon 의 Trigger Out 선**을 세우는 뜻으로 쓴다 (운영자 2026-09-08).
    #
    # ⭐ **둘은 다른 물건이다**: `TRIGOUTFORCE` 는 *강제할지*, `TRIGOUTLEVEL` 은
    # *강제했을 때 나갈 레벨*.  핀을 실제로 HIGH 로 세우려면 **둘 다** 필요하다.
    # guide ACF 출고값은 둘 다 0 이지만(`TRIGOUTFORCE=0` = 타이밍 스크립트가
    # 몬다), **guide 의 쉬는 상태는 `FORCE=1` + `LEVEL=0`** 이다 (운영자 확정
    # 2026-09-08) -- 선을 우리가 붙들어 LOW 로 고정한다.  띄울 때마다
    # `GuideBackend.ensure_trigger_resting()` 이 그 상태로 되돌린다.
    # ⛔ 그래서 **`SHCLOSE` 는 강제를 풀지 않는다** -- 레벨만 내린다.

    #: ⛔ **guide 에 없는 기반 명령** (운영자 2026-09-08).
    #:
    #: `DMAWAIT` 는 레거시 IC 의 **광케이블 통신 지연**이다 -- guide 는 IC 가
    #: 아니라 **Archon 한 대**를 TCP 로 몰므로 그 값을 둘 자리가 없다.  종전에는
    #: 상속으로 살아 있어 `DONE: DMAWAIT DMAWaitTime=…` 을 **성공으로** 답했고,
    #: 그 값은 아무 데도 안 쓰였다 -- 거짓 성공이다.
    #: ⚠️ **레거시 ICG 는 이것을 받았다** (`legacy_command_coverage.md`:
    #: *"IC (ICS·ICG 주소로도 받음)"*).  OBSAgent 가 guide 로도 보낸다면 응답이
    #: `DONE` 에서 `ERROR` 로 바뀐다 -- 운영자 확인 사항으로 남긴다.
    #:
    #: ⛔ **`FLASHNOW`/`LEDFLASH` 는 거짓 성공이었다** (운영자 2026-09-09).
    #: `cmd_flashnow` 는 `app.backend.flash_led()` 를 부르는데 ICG 의 그 자리는
    #: **눌러 둔 science sim 스텁**이라 아무 하드웨어도 안 건드리고 `DONE: FLASHNOW
    #: LED Flash Done.` 이 나갔다.  ⚠️ science 실기는 `BackendError(_NOT_YET)` 로
    #: **정직하게 거절**한다 -- 거짓말은 ICG 쪽만이었다.
    #: ⚠️ `LEDFLASH` 를 없애면 **노출과 자동 동기되는 점등**이 사라진다
    #: (`TRIGOUT <ms>` 는 우리가 임의 시각에 내는 것이라 프레임과 비동기다).
    #:
    #: ⛔ **`SHOPEN`/`SHCLOSE` 는 `TRIGOUT` 으로 갈렸다** (운영자 2026-09-09) --
    #: guide 에는 셔터가 없으니 셔터 낱말을 빌려 쓰지 않는다.  ⚠️ 11.45 에서는
    #: *"낱말은 남기고 뜻만 바꾼다"* 였는데 그 결정이 뒤집혔다: OBSAgent 나 IC 가
    #: guide 로 `SHOPEN` 을 보내면 이제 `ERROR` 다.
    UNSUPPORTED = frozenset({'DMAWAIT', 'FLASHNOW', 'LEDFLASH',
                             'SHOPEN', 'SHCLOSE'})

    #: guide 의 **쉬는 상태** -- `(TRIGOUTLEVEL, TRIGOUTFORCE)` 의 설정 문면.
    #: `ctrl.trigger_state()` 가 돌려주는 것과 같은 꼴이다.
    _TRIGOUT_REST = trigout_core.REST_GUIDE

    @staticmethod
    def _trigout_words(high=None, forced=None) -> str:  # noqa: ANN001
        """응답 본문 -- 쓴 것만, **쓴 차례대로**(레벨이 먼저)."""
        out = []
        if high is not None:
            out.append('TRIGOUTLEVEL=%d' % (1 if high else 0))
        if forced is not None:
            out.append('TRIGOUTFORCE=%d' % (1 if forced else 0))
        return ' '.join(out)

    def _trigout(self, msg: Message, word: str, key: str):  # noqa: ANN001, ANN202
        """`TRIGOUTFORCE`/`TRIGOUTLEVEL` 공통 -- 인자 없으면 조회."""
        ctrl = getattr(getattr(self.app, 'guide', None), 'ctrl', None)
        if ctrl is None:
            return Reply.error(word, 'Controller is not available')
        arg = msg.body.strip()
        if not arg:
            # ⭐ **캐시가 아니라 `RCONFIG` 되읽기다** -- 히터 다섯과 같은 규약
            # (이 모듈 머리말).  ⛔ `ctrl.config` 는 `set_config` 가 **왕복
            # 실패에도 먼저** 갈아 끼우므로 못 믿는다 (11.13 F5) -- 캐시를
            # 답하면 *"1 이라고 답하는데 실제 핀은 0"* 이 된다.
            self.app.spawn(self._read_trigout(msg.src, word, key))
            return Reply.noop()
        want = expen.parse(arg)
        if want is None:
            return Reply.error(word, _unknown(arg))
        one = {'high' if key == 'TRIGOUTLEVEL' else 'forced': want}
        self.app.spawn(self._do_trigout(msg.src, word, **one))
        return Reply.noop()

    async def _read_trigout(self, dest: str, word: str, key: str) -> None:
        """`RCONFIG` 로 되읽어 답한다 -- 실패는 숨기지 않는다."""
        try:
            held = (await self.app.guide.ctrl.read_config(key)).strip()
        except Exception as exc:  # noqa: BLE001 -- 한 명령이 노드를 못 죽인다
            self.emit.error(dest, word, 'Failed: %s' % exc)
            return
        self.emit.done(dest, word, '%s=%s' % (key, held))

    async def _write_trigout(self, ctrl, *, high=None,  # noqa: ANN001
                             forced=None) -> None:
        """한 번의 `APPLYSYSTEM` 으로 쓴다 (`ctrl.set_trigger`)."""
        if forced is False:
            # ⚠️ **쉬는 상태를 벗어난다** -- 선이 타이밍 스크립트 손에 넘어가
            # 노출마다 흔들린다.  거절하지는 않는다(운영자가 일부러 쓰는
            # 자리다) -- 대신 그 사실을 남긴다.
            log.warning('TRIGOUTFORCE=0 -- 트리거 선을 타이밍 스크립트에 '
                        '넘긴다.  guide 의 쉬는 상태는 FORCE=1 이고, '
                        '다음 GO 의 prepare() 가 되돌린다')
        await ctrl.set_trigger(high=high, forced=forced)

    async def _do_trigout(self, dest: str, word: str, *,  # noqa: ANN001
                          high=None, forced=None, t0=None) -> None:
        """쓰고 늦은 `DONE` 을 낸다 -- 실패는 숨기지 않는다.

        ⏳ `t0`(수신 monotonic)가 있으면 **지연을 남긴다** -- `TRIGOUT 0`
        (즉시 내림)이 연속 노출 중에 얼마나 밀리는지가 관측 대상이다.
        """
        ctrl = self.app.guide.ctrl
        try:
            await self._write_trigout(ctrl, high=high, forced=forced)
        except Exception as exc:  # noqa: BLE001 -- 한 명령이 노드를 못 죽인다
            self.emit.error(dest, word, 'Failed: %s' % exc)
            return
        if t0 is not None:
            self._log_latency('%s 쓰기' % word, t0, always=True)
        self.emit.done(dest, word, self._trigout_words(high=high, forced=forced))

    def cmd_trigoutforce(self, msg: Message, target: Target) -> Reply:
        """TRIGOUTFORCE [ON|OFF] -- Trigger Out 을 **강제할지**.  없으면 조회.

        `0` 이면 타이밍 스크립트가 몬다(ACF 출고값), `1` 이면 `TRIGOUTLEVEL` 로
        고정.  ⚠️ science 는 이 값으로 셔터를 여닫는다(`0`=열림) -- guide 는
        셔터가 없어 **바깥 트리거 선**을 세우는 뜻이다.
        ⭐ **guide 의 쉬는 상태는 `1` 이다** (운영자 확정 2026-09-08).  `0` 으로
        내려놓는 것은 되지만 그 사실을 경고로 남기고, **다음 `GO` 의
        `prepare()` 가 `1` 로 되돌린다** (`ensure_trigger_resting`).
        """
        return self._trigout(msg, 'TRIGOUTFORCE', 'TRIGOUTFORCE')

    def cmd_trigoutlevel(self, msg: Message, target: Target) -> Reply:
        """TRIGOUTLEVEL [HIGH|LOW] -- 강제했을 때 Trigger Out 이 나갈 레벨.

        ⛔ 이것만 세우면 핀은 안 바뀐다 -- `TRIGOUTFORCE` 가 `1` 이라야 나간다.
        """
        return self._trigout(msg, 'TRIGOUTLEVEL', 'TRIGOUTLEVEL')

    #: `TRIGOUT <ms>` 가 띄운 자동 내림 타이머.  ⭐ 하나만 산다 -- 새 `TRIGOUT`
    #: 이 오면 앞의 것을 끊는다 (안 끊으면 옛 타이머가 나중에 깨어나 **방금
    #: 세운 선을 내린다**).
    _trigout_timer = None

    #: 취득 중 `APPLYSYSTEM` 경고를 한 번만 낸다 (아래 `_do_trigout_pulse`).
    _warned_busy_apply = False

    def cmd_trigout(self, msg: Message, target: Target) -> Reply:
        """TRIGOUT <ms> -- **Trigger Out 을 <ms> 동안 HIGH 로**.  `0` 이면 즉시 LOW.

        운영자 확정 2026-09-09.  종전 `SHOPEN <초>`/`SHCLOSE` 를 이 한 낱말로
        모았다 -- ⛔ guide 에는 셔터가 없으니 **셔터 낱말을 빌려 쓰지 않는다**.

        ⛔ **단위가 초에서 ms 로 바뀌었다** (운영자 2026-09-09 저녁).  ⚠️ 옛
        버릇이 위험하다 -- `trigout 2` 는 종전 **2 초**였는데 이제 **2 ms** 라
        실현 최소 폭(≈235 ms)으로 눌린다.  2 초를 원하면 `trigout 2000`.
        ⭐ 눈금을 ms 로 옮긴 이유는 **실현 최소 폭 자체가 ms 단위**라서다
        (적용 한 번 ≈235 ms) -- 초로 적으면 쓸 수 있는 값이 소수점 아래로
        몰린다 (`0.25`·`0.5`).

        | 인자 | 하는 것 | 적용 |
        |---|---|---|
        | `<ms>` > 0 | 무장(`LEVEL=0`+`FORCE=1`) -> `LEVEL=1`, `<ms>` 뒤 자동 내림 | 1~2회 |
        | `0` | 즉시 `LEVEL=0` + `FORCE=1` (대기 중 타이머도 끊는다) | 1회 |

        ⭐ **둘을 한 적용에 같이 세운다** (`archon.trigout.raise_line`) -- 무장을
        앞세우면 그 한 적용 동안 핀이 강제 LOW 라 science 에서 노출 중 셔터가
        잠깐 닫힌다.  두 계통이 같은 알맹이를 쓰므로 여기도 같은 규범이다.
        ⚠️ 시한은 `cfg.scaled()` 를 탄다 (시험 축척) -- 실기 `time_scale` 은 1 이다.

        ✅ **취득 중에 쳐도 된다 -- 실측했다** (2026-09-09, DevNote 11.55).  핀 자체는 CCD 로
        되먹임이 없어 자료에 관여하지 않는다.  ⚠️ 그런데 실현 수단이
        `WCONFIG`+`APPLYSYSTEM` 이고, **독출 중 `APPLYSYSTEM`** 의 안전성은
        science 쪽(`archon/backend.py` `close_shutter`)이 이미 *"실기 확인 항목"*
        으로 열어 둔 자리다.  guide 는 연속 취득이라 거의 항상 그 상황이다.
        ⭐ **막지는 않는다** -- 막으면 이 명령을 쓸 수가 없다.  대신 취득 중이면
        **한 번 경고**해 나중에 프레임 이상과 이을 단서를 남긴다.
        """
        arg = msg.body.split()
        if not arg:
            return Reply.error('TRIGOUT', 'Missing duration (milliseconds)')
        try:
            ms = float(arg[0])
        except ValueError:
            return Reply.error('TRIGOUT', 'Invalid duration: %s' % arg[0])
        if ms < 0:
            return Reply.error('TRIGOUT', 'Invalid duration: %s' % arg[0])
        ctrl = getattr(getattr(self.app, 'guide', None), 'ctrl', None)
        if ctrl is None:
            return Reply.error('TRIGOUT', 'Controller is not available')
        import time
        t0 = time.monotonic()
        self._cancel_trigout_timer()
        if ms == 0:
            # ⭐ 종전 `SHCLOSE` -- 둘을 한 적용에 같이 세운다 (되읽기 없음).
            self.app.spawn(self._do_trigout(msg.src, 'TRIGOUT',
                                            high=False, forced=True, t0=t0))
            return Reply.noop()
        self.app.spawn(self._do_trigout_pulse(msg.src, ms, t0))
        return Reply.noop()

    def _cancel_trigout_timer(self) -> bool:
        """대기 중 펄스를 끊는다.  **끊었으면 `True`** (선이 아직 HIGH 다)."""
        timer, self._trigout_timer = self._trigout_timer, None
        if timer is None or timer.done():
            return False
        timer.cancel()
        return True

    async def release_pulse(self, why: str) -> bool:
        """진행 중 `TRIGOUT` 펄스를 **끊고 선을 쉬는 상태로**.  끊었으면 `True`.

        ⛔ **끊는 자리가 셋이다** (운영자 2026-09-09): `ABORT` · `EXPENABLE OFF` ·
        **종료**.  안 내리면 **LED 가 켜진 채 남는다** -- `RESETTIMING` 은 타이밍
        코어만 되돌리는데 펄스 중에는 `TRIGOUTFORCE=1` 이라 핀이 코어를 아예 안
        따라가기 때문이다.  ⛔ **종료가 특히 나쁘다**: `spawn` 한 펄스 태스크가
        종료에 취소되므로 내림이 **영영 안 돌고** 사람 없는 채로 광원이 남는다.
        ⚠️ 펄스가 없었으면 **아무것도 안 쓴다** (군더더기 왕복을 안 만든다).
        ⚠️ **실패를 삼킨다** -- 종료 경로에서 부르므로 여기서 던지면 종료가 막힌다.
        """
        if not self._cancel_trigout_timer():
            return False
        ctrl = getattr(getattr(self.app, 'guide', None), 'ctrl', None)
        if ctrl is None:
            return False
        log.warning('%s -- 진행 중이던 TRIGOUT 펄스를 끊고 선을 쉬는 상태로 '
                    '되돌린다', why)
        try:
            await trigout_core.rest_line(ctrl, self._TRIGOUT_REST)
        except Exception as exc:  # noqa: BLE001 -- 종료를 막지 않는다
            log.error('%s -- TRIGOUT 을 못 내렸다: %s.  **선이 HIGH 로 남을 수 '
                      '있다**', why, exc)
        return True

    def cmd_abort(self, msg: Message, target: Target) -> Reply:
        """ABORT -- 기반 동작 + **진행 중 `TRIGOUT` 펄스를 끊는다** (`release_pulse`)."""
        self.app.spawn(self.release_pulse('ABORT'))
        return super().cmd_abort(msg, target)

    def _warn_if_acquiring(self) -> None:
        """취득 중 `APPLYSYSTEM` -- **한 번만** 남긴다 (자취용).

        ⭐ **경고에서 알림(`INFO`)으로 낮췄다** (2026-09-09) -- 해롭지 않다는
        것을 실측했기 때문이다 (11.55).  ⚠️ 그래도 **남기기는 한다**: 나중에
        프레임 이상을 쫓을 때 *"그때 적용을 보냈나"* 가 첫 갈래이고, 그 자취가
        없으면 되짚을 수가 없다.
        """
        seq = getattr(self.app, 'seq', None)
        if seq is None or not seq.busy or self._warned_busy_apply:
            return
        self._warned_busy_apply = True
        log.info('취득 중에 TRIGOUT 을 쳤다 -- WCONFIG + APPLYSYSTEM 이 프레임 '
                 '도중에 나간다.  ⭐ **해롭지 않다는 것은 실측했다** '
                 '(2026-09-09, DevNote 11.55): go 20 이 완주했고 프레임 주기 '
                 '밀림은 명령과 무관했으며 모듈 VCPU 도 안 재시작됐다.  '
                 '이 뒤 프레임에 이상이 보이면 이 줄을 함께 볼 것')

    async def _do_trigout_pulse(self, dest: str, ms: float,
                                t0: float | None = None) -> None:
        r"""세우고 -> 기다리고 -> 내린다.  ⛔ 내림은 **취소돼도 안 흘린다**.

        ⏳ **여기가 지연 실측 자리다** (운영자 2026-09-09).  연속 노출 중에는
        `_locked_thread` 가 모든 왕복을 한 줄로 세우므로 이 명령의 `WCONFIG`
        둘 + `APPLYSYSTEM` 은 **진행 중인 FETCH 뒤에 선다** (guide 8.3 MiB
        ≈ 0.08 s, 잠금 상한 `fetch_timeout = 1.0 s`).  세 값을 남긴다:

        * **수신 -> HIGH** -- 락 대기 + 적용.  운영자가 물은 *"명령 실행 지연"*.
        * **수신 -> LOW** -- 내림도 같은 락을 탄다.
        * ⭐ **펄스 폭 오차** -- 실제 HIGH 지속과 요청 `<ms>` 의 차.  ⚠️ 이것이
          가장 중요한 값이다: 시작이 밀려도 **폭이 맞으면** 광원 노출량은 맞는다.

        ⛔ **실측이 내 예측을 뒤집었다** (2026-09-09): *"밀림은 폭에 안 섞이고
        남는 오차는 내림 쪽 락 대기뿐"* 이라고 봤는데, 폭오차가 **+235 ms 로
        17회 내내 일정**했다.  락 대기가 아니라 **내림 자신의 `APPLYSYSTEM`
        처리시간**(≈233 ms)이 통째로 폭에 들어간 것이다.  ⭐ 그래서 이제
        **잠들 시간에서 그만큼을 뺀다** (아래 `apply_cost`).
        """
        import asyncio
        import time
        # ⭐ **바깥 눈금은 ms, 안쪽 셈은 초다** -- `cfg.scaled()` 도
        # `asyncio.sleep()` 도 초를 받는다.  경계에서 한 번만 나눈다.
        seconds = ms / 1000.0
        ctrl = self.app.guide.ctrl
        self._warn_if_acquiring()
        raise_at = time.monotonic()
        try:
            await trigout_core.raise_line(ctrl)
        except Exception as exc:  # noqa: BLE001 -- 한 명령이 노드를 못 죽인다
            self.emit.error(dest, 'TRIGOUT', 'Failed: %s' % exc)
            return
        high_at = time.monotonic()
        apply_cost = high_at - raise_at
        if t0 is not None:
            self._log_latency('TRIGOUT 올림', t0, 'MS=%g' % ms,
                              always=True)
        self.emit.done(dest, 'TRIGOUT',
                       'TRIGOUTLEVEL=1 TRIGOUTFORCE=1 MS=%g' % ms)
        self._trigout_timer = asyncio.current_task()
        # ⭐ **내림에 걸릴 시간을 미리 뺀다** (2026-09-09 실측).
        #
        # ⛔ 종전에는 `sleep(<초>)` 만 하고 그 뒤에 내림 왕복을 보냈다 -- 그래서
        # 핀이 실제로 HIGH 인 시간이 **`<초>` + 내림 적용시간**이었다.  벤치
        # 실측: 요청 2000 ms 에 폭오차 **+235 ms 가 17회 내내 일정** (2235 ms).
        # 짧은 펄스일수록 비율이 커진다 -- 500 ms 면 +47 % 다.
        #
        # ⭐ **핀이 적용 처리의 어느 지점에서 뒤집히든 이 보정은 옳다.**  적용
        # 하나에 `C` 가 걸리고 핀이 그 안 비율 `f` 에서 뒤집힌다고 하면
        # HIGH 는 `t올림 + fC`, LOW 는 `t올림 + C + 잠 + fC` 이므로
        # **폭 = 잠 + C** 이고 `f` 가 지워진다.  그래서 `잠 = <초> - C` 다.
        # ⭐ `C` 는 **방금 잰 올림 비용**을 쓴다 -- 올림과 내림이 같은 왕복
        # (`WCONFIG` 둘 + `APPLYSYSTEM`)이고 실측도 232 ms 대 236 ms 였다.
        # ⛔ 상수로 박지 않는다 -- 링크·펌웨어가 바뀌면 따라와야 한다.
        #
        # ⚠️ **`<ms>` 가 적용 하나보다 짧으면 못 만든다** -- 0 으로 눌러 담고
        # 그 사실을 알린다 (실현 최소 폭 ≈ 235 ms).  ⭐ 눈금이 ms 라 운영자가
        # 그 하한을 **같은 단위로** 읽고 쓴다.
        #
        # ⏳ ⚠️ **남은 빈틈: `apply_cost` 에는 락 대기가 섞인다.**  이 값은
        # *"올림을 시작해서 끝날 때까지"* 라 **진행 중인 FETCH 를 기다린
        # 시간**도 들어 있다 (취득 중 최악 +104 ms 실측).  내림이 그만큼
        # 안 기다리면 **너무 많이 빼서 폭이 짧아진다.**
        # ⭐ 그래도 종전보다 낫다: 종전은 **늘 +235 ms** 였고 지금은 두 왕복의
        # 락 대기 **차**만 남는다 (평균 0 근처, 한가할 때는 정확히 0).
        # ⏳ 이 잔차가 실측에서 크게 보이면 `ctrl.last_cmd_timing`(스레드 안
        # 왕복 시각)으로 **락 대기를 뺀 순수 적용시간**을 쓰도록 다듬는다.
        want = self.cfg.scaled(seconds)
        nap = want - apply_cost
        if nap < 0:
            log.warning('TRIGOUT %g ms 는 적용 한 번(%.0f ms)보다 짧다 -- '
                        '실현 폭은 약 %.0f ms 가 된다 (그보다 짧은 펄스는 이 '
                        '방식으로 못 만든다)', ms, apply_cost * 1000,
                        apply_cost * 1000)
            nap = 0.0
        try:
            await asyncio.sleep(nap)
        except asyncio.CancelledError:
            # ⭐ 새 `TRIGOUT` 이 끊었다 -- 그쪽이 선을 책임진다.
            raise
        self._trigout_timer = None
        try:
            # ⭐ **시한 내림은 강제를 유지한다** -- guide 는 쉬는 상태가 곧
            # 그것이라 `TRIGOUT 0` 과 같은 값이지만, 뜻이 다른 자리라 함수를
            # 나눠 부른다 (science 에서는 실제로 갈린다).
            await trigout_core.rest_line(ctrl, self._TRIGOUT_REST)
        except Exception as exc:  # noqa: BLE001
            self.emit.error(dest, 'TRIGOUT', 'Failed: %s' % exc)
            return
        # ⭐ **폭 오차** -- 실제 HIGH 지속 - 요청.  ⚠️ 이제 보정이 들어갔으므로
        # **0 근처여야 한다** -- 종전의 +235 ms 가 그대로면 보정이 안 먹은 것이다.
        wide_ms = (time.monotonic() - high_at - want) * 1000.0
        if t0 is not None:
            self._log_latency('TRIGOUT 내림', t0,
                              '폭오차 %+.1f ms (요청 %g ms, 보정 -%.0f ms)'
                              % (wide_ms, ms, apply_cost * 1000),
                              always=True)
        # ⚠️ 부르지 않은 `DONE` 이다 -- 시한이 다 됐다는 통보다.
        self.emit.done(dest, 'TRIGOUT', '%s (auto after %g ms)'
                       % (self._trigout_words(high=False, forced=True), ms))

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
        도구다.  ⭐ **제한 없음** (운영자 2026-09-05) -- 취득 중·다른 조작 중에도
        받고 `GO` 도 막지 않는다; 진행 중 노출 위의 `RESETTIMING` 이 프레임을
        망치는 것은 운영자의 몫이다.
        """
        be, bad = self._guide('ARCHON')
        if bad is not None:
            return bad
        text = ' '.join(msg.body.split())
        if not text:
            return Reply.error('ARCHON', 'Usage: ARCHON <command>')
        note = self._lock_note()
        log.info('ARCHON by %s -- 원문 바이패스: %r%s', msg.src, text,
                 ' (EXPENABLE OFF 상태)' if note else '')
        self.app.spawn(self._do_archon(msg.src, be, text, note))
        return Reply.noop()

    async def _do_archon(self, dest: str, be, text: str,  # noqa: ANN001
                         note: str) -> None:
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

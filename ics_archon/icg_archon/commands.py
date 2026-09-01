#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""icg 명령 -- science 명령 처리부 상속 + 텔레메트리 명령 추가.

레거시 계승: ICG 는 ICS 와 **같은 명령 테이블**을 썼으므로(`PAP7KX.CMD`,
icg_legacy_report 8.1절) `OBJECT`/`DARK`/`EXP`/`GO`/`STOP`/`ABORT` 등은
`ics_sim.commands.Dispatcher` 를 상속해서 그대로 받는다.  실측 관측된
전용 명령은 `GUIDEEXP` 하나다 (5.2절 -- 응답 문구까지 계승).

추가 (운영자 요구 2026-08-31):

* `HK`                     -- 최신 HK 스냅샷 한 줄
* `RADIONODE STATUS`       -- 장치별 연결 상태
* `RADIONODE RECONNECT`    -- 즉시 재폴링
* `RADIONODE ENABLE <별칭>` / `DISABLE <별칭>` -- 장치 폴링 켜기/끄기
"""

from __future__ import annotations

import logging

from ics_archon import _simpath

_simpath.ensure()

from ics_sim import commands as sim_commands  # noqa: E402
from ics_sim import emitter  # noqa: E402
from ics_sim.commands import Reply  # noqa: E402
from ics_sim.impv2 import Message  # noqa: E402
from ics_sim.nodes import Target  # noqa: E402

log = logging.getLogger('icg_archon.cmd')

#: emitter 의 커맨드워드 어휘에 icg 몫을 더한다 -- `validate()` 가 이 표로
#: 발신을 검사하므로, 등록 없이 새 커맨드워드를 쓰면 위생 검사가 운다.
ICG_COMMANDS = frozenset({'GUIDEEXP', 'HK', 'RADIONODE'})


def extend_vocabulary() -> None:
    """모듈 상수(frozenset)를 합집합으로 갈아 끼운다 -- 한 번이면 된다."""
    if not ICG_COMMANDS <= emitter.KNOWN_COMMANDS:
        emitter.KNOWN_COMMANDS = frozenset(emitter.KNOWN_COMMANDS
                                           | ICG_COMMANDS)


class IcgDispatcher(sim_commands.Dispatcher):
    """science 디스패처 + icg 전용 핸들러."""

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
        """RADIONODE STATUS | RECONNECT | ENABLE <별칭> | DISABLE <별칭>."""
        rn = getattr(self.app, 'radionode', None)
        if rn is None:
            return Reply.error('RADIONODE', 'Radionode poller is not running')
        args = msg.body.split()
        sub = args[0].upper() if args else 'STATUS'
        if sub == 'STATUS':
            return Reply.done('RADIONODE', rn.status_text())
        if sub == 'RECONNECT':
            if rn.cfg.backend != 'openapi':
                return Reply.error('RADIONODE',
                                   'Backend is %s -- nothing to poll'
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
                                   'disable' % rn.cfg.backend)
            alias = args[1]
            on = sub in ('ENABLE', 'CONNECT')
            if not rn.set_enabled(alias, on):
                return Reply.error('RADIONODE', 'Unknown device: %s' % alias)
            return Reply.done('RADIONODE', '%s %s' % (
                alias, 'enabled' if on else 'disabled'))
        return Reply.error('RADIONODE', "Didn't understand %s ?" % sub)

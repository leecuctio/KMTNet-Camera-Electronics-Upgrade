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

    def cmd_guideexp(self, msg: Message, target: Target) -> Reply:
        """GUIDEEXP <초> -- 가이드 노출시간(독출 개시 간격) 설정.

        레거시 응답 문구를 계승한다 -- `DONE: GUIDEEXP GuideExp=<n> seconds.`
        (icg_legacy_report 5.2절 실측).  값 의미는 신규 규격으로 넘어와
        `EXPTIME` = 독출 개시 간격이다 (raw spec 10.1절) -- `EXP` 와 같은
        상태 필드를 채우므로 어느 쪽으로 설정해도 같다.
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
            # 즉시 한 바퀴 -- 결과는 다음 STATUS 로 본다 (질의는 블로킹이라
            # 백그라운드로 던진다).
            self.app.spawn(rn.poll_now())
            return Reply.done('RADIONODE', 'Polling now')
        if sub in ('ENABLE', 'DISABLE', 'DISCONNECT', 'CONNECT'):
            if len(args) < 2:
                return Reply.error('RADIONODE', 'Usage: RADIONODE %s <alias>'
                                   % sub)
            alias = args[1]
            on = sub in ('ENABLE', 'CONNECT')
            if not rn.set_enabled(alias, on):
                return Reply.error('RADIONODE', 'Unknown device: %s' % alias)
            return Reply.done('RADIONODE', '%s %s' % (
                alias, 'enabled' if on else 'disabled'))
        return Reply.error('RADIONODE', "Didn't understand %s ?" % sub)

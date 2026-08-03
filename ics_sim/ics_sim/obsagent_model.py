#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A faithful model of OBSAgent's CamStatus state machine.

`OBSAgent/OBSAgent.latest/KMTObs/commands.c` 757~864행의 if/else-if 체인과
`main.c` 650~708행의 주기 타이머를 파이썬으로 옮긴 것이다.  두 곳에서 쓴다:

  * `tools/scan_legacy_logs.py camstatus` -- 실측 로그를 재생해 전이를 집계
  * `tests/test_obsagent_contract.py`     -- 시뮬 발신이 규약을 지키는지 검증

**같은 코드를 쓴다는 점이 중요하다.**  실측에서 나온 전이 패턴과 시뮬이 만드는
전이 패턴을 같은 자로 재야 비교가 성립한다.

두 가지 함정을 여기 못박아 둔다:

1. **dest 필터.**  OBSAgent 는 자기 앞으로 온 메시지만 본다.  XIS 로그를 재생할
   때 이 필터를 빠뜨리면 `ICS>N.IC STATUS: TCSSTATUS .. EXPSTATUS=INTEGRATING`
   같은 IC 행 중계까지 먹여서 있지도 않은 `INT_3 -> INT_1` 역행이 수만 건 잡힌다
   (실제로 조사 중에 그랬다 -- DevNote 12장 정정 이력).
2. **발신 노드 필터.**  ICS / {K,M,T,N}.IC / {K,M,T,N}.CB 만 CamStatus 에
   영향을 준다.  ICG/G.IC/G.CB 는 v0.3.2 부터 명시적으로 무시된다.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

#: CamStatus 값 (obstool.h 의 enum 과 같은 이름).
NC = 'NC'
PREP_I, PREP_E = 'PREP_I', 'PREP_E'
INT_1, INT_2, INT_3 = 'INT_1', 'INT_2', 'INT_3'
CLOSING = 'CLOSING'
READ_1, READ_2, READ_3 = 'READ_1', 'READ_2', 'READ_3'
IDLE_1, IDLE_2, IDLE_3 = 'IDLE_1', 'IDLE_2', 'IDLE_3'
READY = 'READY'

#: CamStatus 에 영향을 주는 발신 노드 (commands.c 757-759).
SCI_NODES = frozenset({'ICS', 'K.IC', 'M.IC', 'T.IC', 'N.IC',
                       'K.CB', 'M.CB', 'T.CB', 'N.CB'})

#: OBSAgent 가 받는 주소.
OBS_DESTS = frozenset({'OBS', 'AL', 'ALL'})

_HEAD = re.compile(r'^\S+ (?:\[[^\]]*\] )?')
_MSG = re.compile(r'^(?P<src>[A-Za-z0-9._]+)>(?P<dst>[A-Za-z0-9._]+) '
                  r'(?P<type>DONE:|STATUS:)(?P<rest>.*)$')


@dataclass
class CamStatusReplay:
    """메시지 스트림을 먹여 CamStatus 전이를 추적한다."""

    state: str = NC
    count_acqcomp: int = 0
    count_wrote: int = 0
    fits_saved: int = 0
    fits_num: str = ''
    exp_num_next: str = ''

    transitions: Counter = field(default_factory=Counter)
    history: list[tuple[str, str, str]] = field(default_factory=list)
    #: 규약 위반 기록 (사유, 메시지)
    faults: list[tuple[str, str]] = field(default_factory=list)
    #: 각 이벤트가 도착한 시각 (초).  타임아웃 창 검사에 쓴다.
    events: list[tuple[float, str, str]] = field(default_factory=list)

    def feed(self, line: str, when: float = 0.0) -> str | None:
        """XIS 로그 한 줄 또는 와이어 한 줄을 먹인다.

        두 형식을 모두 받는다::

            2024-03-03T22:23:16.570276 [/dev/ttyS0] ICS>OBS STATUS: ...
            ICS>OBS STATUS: ...

        먼저 원문 그대로 시도하고, 안 맞으면 앞머리(타임스탬프 + [iface])를
        떼고 다시 본다.  순서를 반대로 하면 `ICS>OBS ` 자체가 앞머리로 잘려
        나가 아무것도 매칭되지 않는다.

        Returns:
            상태가 바뀌었으면 새 상태, 아니면 None.
        """
        body = line.rstrip('\r\n')
        m = _MSG.match(body)
        if not m:
            body = _HEAD.sub('', body)
            m = _MSG.match(body)
        if not m:
            return None
        if m.group('src').upper() not in SCI_NODES:
            return None
        if m.group('dst').upper() not in OBS_DESTS:
            return None
        return self._apply(body, when)

    def _apply(self, buf: str, when: float) -> str | None:
        old = self.state
        trigger = ''

        # commands.c 764: EXPSTATUS=IDLE 은 **독립 if** 다.
        if 'EXPSTATUS=IDLE' in buf:
            self.state = IDLE_3
            trigger = 'EXPSTATUS=IDLE'
            self.events.append((when, 'idle', buf))

        # 771 이후는 하나의 else-if 체인.  순서가 곧 우선순위다.
        if 'Wrote' in buf:
            self.count_wrote += 1
            self.events.append((when, 'wrote', buf))
            if self.count_wrote >= 4:
                self.fits_saved = 1
                pos = buf.find('KMTN')
                self.fits_num = (buf[pos + 6:pos + 21] if pos >= 0
                                 else '00000000.000000')
        elif 'Acquisition Complete.' in buf:
            self.count_acqcomp += 1
            self.state = IDLE_1
            self.events.append((when, 'acq', buf))
            if self.count_acqcomp >= 4:
                self.state = IDLE_2
            trigger = 'Acquisition Complete.'
        elif 'PCTREAD=' in buf:
            if self.state == READ_1:
                self.state = READ_2
            elif self.state == READ_2:
                self.state = READ_3
            elif self.state != READ_3:
                self.state = READ_1
            self.count_acqcomp = 0
            self.count_wrote = 0
            self.fits_saved = 0
            self.events.append((when, 'pctread', buf))
            trigger = 'PCTREAD='
        elif 'EXPSTATUS=READOUT' in buf:
            self.state = READ_1
            self.count_wrote = 0
            self.fits_saved = 0
            trigger = 'EXPSTATUS=READOUT'
        elif 'Shutter=Closed' in buf:
            self.state = CLOSING
            trigger = 'Shutter=Closed'
        elif 'Remaining=' in buf:
            self.state = INT_3
            trigger = 'Remaining='
        elif 'Shutter=Open' in buf:
            self.state = INT_2
            trigger = 'Shutter=Open'
        elif 'EXPSTATUS=INTEGRATING' in buf:
            self.state = INT_1
            trigger = 'EXPSTATUS=INTEGRATING'
        elif 'EXPSTATUS=ERASE' in buf:
            self.state = PREP_E
            trigger = 'EXPSTATUS=ERASE'
        elif 'EXPSTATUS=INITIALIZING' in buf:
            self.state = PREP_I
            trigger = 'EXPSTATUS=INITIALIZING'

        if self.state == old:
            return None
        self.transitions[(old, self.state)] += 1
        self.history.append((old, self.state, trigger))
        return self.state

    # -- 검사 -------------------------------------------------------------

    def visited(self) -> list[str]:
        """거쳐 간 상태 순서."""
        return [b for _a, b, _t in self.history]

    def check_windows(self, force_idle_sec: float = 1.8,
                      idle_sec: float = 0.9,
                      fits_sec: float = 25.0) -> list[str]:
        """OBSAgent 의 하드 타임아웃 창을 침범했는지 검사한다.

        (main.c 650~708, 1카운트 = 0.045초 -- DevNote 3.3)

        Returns:
            위반 설명 목록.  비어 있으면 통과.
        """
        bad: list[str] = []
        acq = [t for t, kind, _ in self.events if kind == 'acq']
        idle = [t for t, kind, _ in self.events if kind == 'idle']
        wrote = [t for t, kind, _ in self.events if kind == 'wrote']

        if len(acq) >= 4:
            spread = acq[3] - acq[0]
            if spread > force_idle_sec:
                bad.append(
                    f'1번째~4번째 Acquisition Complete. 산포 {spread:.2f}s > '
                    f'{force_idle_sec:.2f}s -> opause + ERROR')
        elif acq:
            bad.append(f'Acquisition Complete. 가 {len(acq)}회뿐 (4회 필요)')

        if len(acq) >= 4 and idle:
            gap = idle[-1] - acq[3]
            if gap > idle_sec:
                bad.append(
                    f'4번째 Acquisition Complete. -> EXPSTATUS=IDLE {gap:.2f}s > '
                    f'{idle_sec:.2f}s -> WARNING')

        if idle and len(wrote) >= 4:
            gap = wrote[3] - idle[-1]
            if gap > fits_sec:
                bad.append(
                    f'IDLE_3 -> 4번째 Wrote {gap:.2f}s > {fits_sec:.2f}s -> '
                    'WARNING + ExpStatus=ERROR')
        elif idle and len(wrote) < 4:
            bad.append(f'Wrote 가 {len(wrote)}회뿐 (4회 필요)')

        return bad

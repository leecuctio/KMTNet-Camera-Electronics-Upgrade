#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local keyboard interface.

프로토콜 스펙 2.2절의 관례를 그대로 따른다: **콘솔에서 타이핑한 명령은 "자기
자신에게 보내는 EXEC:" 로 취급한다.**  `>NODE cmd` 축약형으로 특정 노드에 보낼
수도 있다.

OBS 드라이버를 만들지 않기로 했으므로 이것이 손으로 시뮬을 돌려볼 유일한
수단이고, 동시에 ICS 자체의 정당한 기능이기도 하다.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from .impv2 import parse_line

log = logging.getLogger('ics_sim.console')

_HELP = """\
사용법 -- 레거시 ICS 콘솔과 같다.

  projid <id>            프로젝트 ID
  observer <name>        관측자 (띄어쓰기 허용)
  object|dark|bias|flat|sky|domeflat <objname>
  exp <sec>              노출시간
  expnum [<n>]           파일 일련번호 조회/설정
  go [n]                 노출 n 장 (기본 1)
  status | acqstatus | filename | synchronize | time
  ledflash <ms> | flashnow <ms>
  >K.IC status           특정 노드로 보내기 (축약형)

  help / ?               이 도움말
  quit / exit            종료
"""


class Console:
    """stdin 을 읽어 자기 자신에게 EXEC 로 넘긴다."""

    def __init__(self, app) -> None:  # noqa: ANN001
        self.app = app
        self._stop = asyncio.Event()

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        print(_HELP, end='')
        while not self._stop.is_set():
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
            except (RuntimeError, ValueError):
                break
            if not line:
                break
            self.feed(line.strip())

    def stop(self) -> None:
        self._stop.set()

    # -- 입력 처리 --------------------------------------------------------

    def feed(self, line: str) -> None:
        """한 줄을 처리한다.  테스트에서도 직접 부를 수 있다."""
        if not line:
            return
        low = line.lower()
        if low in ('quit', 'exit'):
            self.stop()
            return
        if low in ('help', '?'):
            print(_HELP, end='')
            return

        ics = self.app.cfg.node.ics_id
        if line.startswith('>'):
            dest, _, rest = line[1:].partition(' ')
            wire = f'{ics}>{dest.strip()} EXEC: {rest.strip()}'
        else:
            # "자기 자신에게 보내는 EXEC" -- 스펙 2.2절의 키보드 인터페이스 관례
            wire = f'{ics}>{ics} EXEC: {line}'

        msg = parse_line(wire)
        if msg is None:
            print(f'  ?? 해석할 수 없는 입력: {line}')
            return
        target = self.app.router.resolve(msg)
        if not target.is_ours:
            print(f'  ?? {msg.dst} 는 이 프로그램이 담당하는 노드가 아닙니다')
            return
        self.app.dispatch.handle(msg, target)

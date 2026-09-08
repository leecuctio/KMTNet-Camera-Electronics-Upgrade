#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local keyboard interface.

프로토콜 스펙 2.2절의 관례를 그대로 따른다: **콘솔에서 타이핑한 명령은 "자기
자신에게 보내는 EXEC:" 로 취급한다.**  `>NODE 메시지` 축약형으로 특정 노드에
보낼 수도 있다.

OBS 드라이버를 만들지 않기로 했으므로 이것이 손으로 시뮬을 돌려볼 유일한
수단이고, 동시에 ICS 자체의 정당한 기능이기도 하다.

⭐ **`>NODE` 는 두 갈래다** (운영자 지시 2026-09-07).  목적지가 **우리가 받는
노드**(`router.owns`)면 종전대로 프로세스 안에서 처리하고, 남의 노드면 **와이어로
내보낸다** -- `xis_host` 가 설정돼 있으면 허브가 받아 그 노드에 전달한다
(`ICS>TC …` · `ICG>XIS HOSTS`).  ⛔ 종전에는 남의 노드도 `dispatch.handle()` 로
흘려서 `is_ours` 가 아니면 *"담당하는 노드가 아닙니다"* 로 막혔고, 그래서
`>XIS HOSTS` 를 **보낼 수단이 아예 없었다** (`icg_first_run` 3단계가 그것을 시켰다).

⭐ **도움말은 앱이 준다** (2026-09-07).  `app.console_help()` 가 절 목록을 돌려주면
그것을 쓰고, 없으면 `BASE_HELP`(이 파일) 다.  ⛔ **표를 손으로 유지하지 않는다** --
`tests/test_console.py` 가 절 목록과 `Dispatcher` 의 `cmd_*` 를 **양방향으로**
대조하므로, 명령을 넣고 도움말을 안 고치면 시험이 빨개진다 (종전 도움말은 신설
14개가 하나도 없고 `stop`·`abort` 도 빠져 있었다).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import unicodedata

from . import impv2
from .impv2 import parse_line

log = logging.getLogger('ics_sim.console')

#: 도움말 한 줄 -- (문법, 설명).  문법의 첫 토큰이 명령 이름이고 `|` 로 여럿을
#: 묶을 수 있다 (`object|dark|bias`).  `>` 로 시작하면 명령이 아니라 축약형이다.
Entry = tuple[str, str]
#: 도움말 한 절 -- (제목, 줄들).  제목이 빈 문자열이면 제목 없이 붙는다.
Section = tuple[str, tuple[Entry, ...]]

#: out-of-band 핸드셰이킹 -- 사람이 치는 명령이 아니라서 도움말에 안 싣는다.
#: `test_console.py` 의 양방향 대조도 이 둘만 면제한다.
NOT_IN_HELP = frozenset({'ping', 'pong'})

#: 축약형 절 -- 명령표에 짝이 없다(`>` 로 시작해 `command_names()` 가 뺀다).
#: ⭐ 앱 절 **뒤**에 온다 -- 앱 명령이 기반 명령 바로 다음에 붙는 것이 읽기 좋다.
REMOTE_TAIL: tuple[Section, ...] = (
    ('다른 노드로 보내기', (
        ('>NODE 메시지',
         '와이어로 내보낸다 -- xis_host 가 있으면 허브 경유'),
        ('>XIS HOSTS', '(예) 허브에 등록된 노드 목록'),
        ('>TC status', '(예) TCS 에 질의'),
    )),
)

#: 콘솔 자체의 낱말 -- 명령이 아니라서 `Dispatcher` 에 짝이 없다.  ⭐ 늘 **맨
#: 끝**에 붙는다 (`extend_help()` 가 앱 절을 이 앞에 끼운다).
CONSOLE_TAIL: tuple[Section, ...] = (
    ('', (
        ('help | ?', '이 도움말'),
        ('quit | exit', '종료'),
    )),
)

BASE_HELP_BODY: tuple[Section, ...] = (
    ('노출 설정', (
        ('projid <id>', '프로젝트 ID'),
        ('observer <name>', '관측자 (띄어쓰기 허용)'),
        ('object|dark|bias|flat|sky|domeflat <objname>',
         '이미지 종류 + 대상 이름'),
        ('exp <sec>', '노출시간 [s]'),
        ('expnum [<n>]', '파일 일련번호 조회/설정'),
        ('ledflash <ms>', '노출 중 LED 점등 시간'),
    )),
    ('취득', (
        ('go [n]', '노출 n 장 (기본 1)'),
        ('stop', '진행 중 노출은 저장까지 마치고 다음을 안 건다'),
        ('abort', '노출 전체 중지 -- readout 도 저장도 안 한다'),
    )),
    ('조회', (
        ('status', '통합 설정 (IC 앞이면 그 CCD 상태)'),
        ('acqstatus', '4개 IC 의 연결·초기화 상태'),
        ('filename', '다음 파일 이름'),
        ('synchronize', '현재 설정 스냅샷'),
        ('time', 'UTC 시각'),
    )),
    ('IC 레벨 (보통 OBSAgent 가 보낸다)', (
        ('initialize <suffix>', '파일명 suffix 를 통째로 설정'),
        ('erase', 'CCD flushing'),
        ('shopen <sec>', '셔터 개방 (master 전용)'),
        ('shclose', '셔터 즉시 닫기 (master 전용)'),
        ('flashnow <n>', '점검용 LED 를 n 만큼 점등'),
        ('dmawait <ms>', 'optical fiber 통신 지연'),
        ('datasource <n>', 'onboard crosstalk 보정 선택'),
        ('bin <n>', 'CCD binning (미구현 스텁)'),
    )),
)

#: 기반 명령만 쓰는 앱(`ics_sim`)의 도움말.
BASE_HELP: tuple[Section, ...] = BASE_HELP_BODY + REMOTE_TAIL + CONSOLE_TAIL


def extend_help(*extra: Section, swap: dict | None = None) -> tuple[Section, ...]:
    """기반 명령 **뒤**, 축약형·콘솔 낱말 절 **앞**에 앱의 절을 끼운다.

    ⭐ 인덱스로 자르지 않는다 -- 기반 절이 늘어도 앱 쪽이 안 깨진다.

    `swap` 은 `{명령: 새 대사}` 또는 `{명령: (새 표기, 새 대사)}` --
    **기반 명령의 뜻이 앱에서 다를 때** 갈아 끼운다.  ⭐ 표기까지 바꿀 수 있는
    것은 **인자가 달라지는 경우**가 있기 때문이다 (ICG 의 `shopen` 은 초를
    안 받는다 -- `shopen <sec>` 를 그대로 두면 표가 거짓말한다).
    ⛔ 명령을 감추거나 빼지는 않는다: 응답하는 것을 안 보이게 하면 그것대로
    거짓말이고, 도움말 ↔ 명령표 대조도 깨진다.
    ⚠️ 이것이 필요한 실제 자리: ICG 의 `shopen`/`shclose` 는 셔터가 아니라
    **Trigger Out 선**을 세운다 (guide 는 frame-transfer 라 셔터가 없다).
    """
    body = BASE_HELP_BODY
    if swap:
        want = {k.lower(): v for k, v in swap.items()}
        seen = set()
        out = []
        for title, entries in body:
            rows = []
            for word, said in entries:
                key = word.split()[0].lower()
                if key in want:
                    repl = want[key]
                    if isinstance(repl, tuple):
                        word, said = repl
                    else:
                        said = repl
                    seen.add(key)
                rows.append((word, said))
            out.append((title, tuple(rows)))
        missed = set(want) - seen
        # ⛔ 갈아 끼울 자리를 못 찾으면 **조용히 넘어가지 않는다** -- 기반
        # 도움말이 바뀌었는데 앱이 옛 이름을 들고 있는 상태다.
        assert not missed, 'swap 대상이 기반 도움말에 없다: %s' % sorted(missed)
        body = tuple(out)
    return body + tuple(extra) + REMOTE_TAIL + CONSOLE_TAIL


# -- 도움말 조립 ----------------------------------------------------------

def command_names(sections) -> set[str]:  # noqa: ANN001
    """절 목록에 실린 **명령 이름** (소문자).

    `>` 로 시작하는 축약형과 `help`/`quit` 같은 콘솔 자체 낱말은 명령이
    아니지만, 그것을 여기서 거르지 않는다 -- 거르는 것은 대조하는 쪽 몫이다
    (콘솔 낱말 목록이 두 곳에 생기는 것을 막는다).
    """
    out: set[str] = set()
    for _title, entries in sections:
        for syntax, _desc in entries:
            head = syntax.split()[0]
            if head.startswith('>'):
                continue
            out.update(t.lower() for t in head.split('|') if t)
    return out


def dispatcher_commands(cls) -> set[str]:  # noqa: ANN001
    """`Dispatcher` 상속 체인 전체가 아는 명령 이름 (소문자).

    핸들러 규칙이 `cmd_<이름>` 이라 클래스만 보면 어휘가 나온다 (`cmd_k_ic`
    처럼 `_` 가 든 이름은 `.` 으로 되돌린다).  ⚠️ `ping`/`pong` 은
    out-of-band 핸드셰이킹이라 뺀다 (`NOT_IN_HELP`).

    ⭐ 도움말 <-> 명령표 대조가 이것을 쓴다 (`tests/test_console.py`).
    """
    out: set[str] = set()
    for klass in cls.__mro__:
        for name in vars(klass):
            if name.startswith('cmd_'):
                out.add(name[4:].replace('_', '.'))
    return out - NOT_IN_HELP


def _cells(text: str) -> int:
    """터미널에서 차지하는 **칸 수**.

    ⛔ `len()` 이 아니다 -- 한글·전각은 한 글자가 두 칸이라 `ljust()` 로
    맞추면 설명 열이 밀린다 (`>NODE 메시지` 가 실제로 그랬다).
    """
    return sum(2 if unicodedata.east_asian_width(ch) in 'WF' else 1
               for ch in text)


def render_help(sections) -> str:  # noqa: ANN001
    """절 목록 -> 콘솔에 찍을 문자열."""
    widths = [_cells(s) for _t, entries in sections for s, _d in entries]
    # 상한을 두는 것은 **긴 한 줄이 전체를 밀지 않게** 하려는 것이다 -- 넘는
    # 줄은 자기만 밀린다 (`radionode …` 가 그렇다).
    width = min(max(max(widths, default=0), 20), 40)
    lines = ['사용법 -- 레거시 ICS 콘솔과 같다.', '']
    for title, entries in sections:
        if title:
            lines.append('  [%s]' % title)
        for syntax, desc in entries:
            if not desc:
                lines.append('    %s' % syntax)
                continue
            pad = ' ' * max(width - _cells(syntax), 1)
            lines.append('    %s%s  %s' % (syntax, pad, desc))
        lines.append('')
    return '\n'.join(lines)


class Console:
    """stdin 을 읽어 자기 자신에게 EXEC 로 넘긴다."""

    def __init__(self, app) -> None:  # noqa: ANN001
        self.app = app
        self._stop = asyncio.Event()

    # -- 도움말 -----------------------------------------------------------

    @property
    def sections(self):  # noqa: ANN201
        """이 앱의 도움말 절 목록 -- 앱이 주면 그것, 아니면 기반 명령."""
        fn = getattr(self.app, 'console_help', None)
        return tuple(fn()) if callable(fn) else BASE_HELP

    def help_text(self) -> str:
        return render_help(self.sections)

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        print(self.help_text())
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
            print(self.help_text())
            return

        ics = self.app.cfg.node.ics_id
        if line.startswith('>'):
            dest, _, rest = line[1:].partition(' ')
            dest, rest = dest.strip(), rest.strip()
            if not dest:
                print('  ?? 목적지 노드가 없습니다 -- 사용법: >NODE 메시지')
                return
            # ⭐ 우리가 받는 노드면 프로세스 안에서 (종전 거동), 남의 노드면
            # 와이어로 내보낸다 (운영자 지시 2026-09-07).
            if not self.app.router.owns(dest):
                self.send_remote(dest, rest)
                return
            wire = f'{ics}>{dest} EXEC: {rest}'
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

    # -- 원격 발신 --------------------------------------------------------

    def send_remote(self, dest: str, rest: str) -> str:
        """`ICS>TC …` 를 **와이어로** 내보낸다.  조립된 줄을 돌려준다(못 보내면 '').

        ⭐ **친 문면을 그대로 싣는다.**  `EXEC:` 를 붙일지는 운영자가 정한다 --
        남의 노드의 어휘를 우리가 감싸면 뜻이 달라진다 (`ICG>XIS HOSTS` 는
        타입 토큰 없는 암묵 REQ 이고, 같은 허브 명령표의 `REMOVE` 는 `EXEC:`
        가드가 있다).  `ARCHON <원문>` 바이패스와 같은 성격이다.

        ⛔ **와이어는 ASCII 다** (규약 7-1).  한글은 `?` 로 바뀌어 상대가 못
        읽으므로 보내기 전에 거른다.
        """
        if not rest:
            print('  ?? 보낼 것이 없습니다 -- 사용법: >NODE 메시지')
            return ''
        src = self.app.cfg.node.ics_id
        msg = parse_line(f'{src}>{dest} {rest}')
        if msg is None:
            print(f'  ?? 노드 이름이 IMPv2 규격에 안 맞습니다: {dest}')
            return ''
        if not rest.isascii():
            print('  ?? 와이어는 ASCII 전용입니다 -- 한글은 ? 로 바뀝니다')
            return ''
        payload = impv2.format(src, dest, msg.mtype, msg.cmdword, msg.body)
        line = payload.rstrip(b'\r').decode('ascii', errors='replace')
        # ⛔ 라우트가 없으면 transport 가 **조용히 버린다** -- 콘솔에서는 그것을
        # 알려야 한다.  ⚠️ `xis_addr` 이 있으면 길은 늘 있다(허브가 살아 있는지는
        # 여기서 모른다) -- 이 분기가 도는 것은 direct-reply 로 아직 그 노드에게서
        # 아무것도 못 받았을 때다.
        if self.app.transport.route_for(dest) is None:
            print('  ?? %s 로 가는 길이 없습니다 -- [transport] xis_host 가 '
                  '비어 있고(direct-reply) 그 노드의 주소를 아직 못 배웠습니다'
                  % dest)
            return ''
        self.app.transport.send(payload, dest)
        print('  >>> %s' % line)
        return line

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IMPv2.5 message parsing and assembly.

    src>dest [TYPE:] [command_word] [message_body]\r

스펙: ics_legacy/__ICIMACS/IMPv2.5Protocol1.pdf, 요약은 ics_legacy_report.md 2절.

레거시 대비 의도적으로 다르게 한 곳:
  * command_word 와 message_body 의 분리를 여기서 끝낸다.  레거시 C 라이브러리는
    이 분리를 애플리케이션에 떠넘겼고(ics_legacy_report 7.2절), 그 결과 커맨드워드
    슬롯이 관리되지 않아 메시지 오염 버그가 생겼다(DevNote 5장).
  * 인용부호/괄호로 묶인 다중 단어 값을 parse_kv() 가 실제로 처리한다.
    레거시 GetArg() 는 공백 토큰화만 해서 Observer=(a, b, c) 같은 값을 깨뜨렸다.

공백에 관하여: 수신측은 공백을 토큰 구분자로만 쓰고 개수는 무시한다.  따라서
format() 은 정규 형태(구분자 1칸)를 만들고, 레거시 로그의 들쭉날쭉한 공백을
그대로 재현할 필요가 있을 때만 emitter 가 raw 문자열을 넘긴다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

#: 메시지 종료 문자.  '\n' 이나 '\0' 은 malformed 로 취급한다.
TERMINATOR = '\r'

#: 스펙상 최대 길이.  초과분은 malformed 로 버린다.
MAX_LEN = 2048

#: 노드 이름: 2~8자, [A-Z0-9._], 대소문자 무관.
_NODE_RE = re.compile(r'^[A-Za-z0-9._]{2,8}$')

#: 브로드캐스트 예약 주소.
BROADCAST = frozenset({'AL', 'ALL'})

#: 메시지 타입 7종.  REQ 는 암묵 기본값이라 리터럴로 보내지 않는다.
MSG_TYPES = ('DONE:', 'STATUS:', 'ERROR:', 'WARNING:', 'FATAL:', 'EXEC:', 'REQ:')

#: 본문 안에 다시 나타나면 오염을 의심해야 하는 토큰 (emitter.validate 가 쓴다).
TYPE_TOKENS = frozenset(t.rstrip(':') for t in MSG_TYPES)

_HEADER_RE = re.compile(
    r'^(?P<src>[A-Za-z0-9._]{2,8})>(?P<dst>[A-Za-z0-9._]{2,8})(?:\s+(?P<rest>.*))?$',
    re.DOTALL,
)

# key=value 토큰화: 'quoted' 와 (parenthesised) 값을 하나로 묶는다.
_KV_RE = re.compile(
    r"""(?P<key>[A-Za-z][A-Za-z0-9_.\-]*)=          # KEY=
        (?P<val>'[^']*'                              #   'single quoted'
              |\([^)]*\)                             #   (parenthesised)
              |[^\s]*)                               #   bare token (may be empty)
    """,
    re.VERBOSE,
)


def is_valid_node(name: str) -> bool:
    """노드 이름이 스펙에 맞는지."""
    return bool(_NODE_RE.match(name))


@dataclass(frozen=True)
class Message:
    """파싱된 IMPv2 메시지 하나.

    Attributes:
        src:      발신 노드 (원문 대소문자 유지)
        dst:      수신 노드 (원문 대소문자 유지)
        mtype:    'REQ' | 'EXEC' | 'DONE' | 'STATUS' | 'ERROR' | 'WARNING' | 'FATAL'
                  타입 토큰이 없으면 'REQ' (스펙상 암묵 기본값)
        explicit_type: 타입 토큰이 실제로 실려 있었는지.  heartbeat 판별에 쓴다.
        cmdword:  커맨드워드.  없으면 빈 문자열
        body:     커맨드워드를 제외한 나머지 본문
        raw:      종료문자를 뺀 원문 전체
    """

    src: str
    dst: str
    mtype: str
    cmdword: str
    body: str
    raw: str
    explicit_type: bool = False

    # -- 편의 프로퍼티 ----------------------------------------------------

    @property
    def is_broadcast(self) -> bool:
        return self.dst.upper() in BROADCAST

    @property
    def is_heartbeat(self) -> bool:
        """헤더만 있는 빈 메시지 (노드 생존 신호)."""
        return not self.cmdword and not self.body and not self.explicit_type

    @property
    def payload(self) -> str:
        """커맨드워드 + 본문 (타입 토큰 제외)."""
        if self.cmdword and self.body:
            return f'{self.cmdword} {self.body}'
        return self.cmdword or self.body

    def cmd_is(self, name: str) -> bool:
        """커맨드워드 비교 (대소문자 무관).

        레거시 라이브러리도 strcasecmp 를 쓴다 (ics_legacy_report 7.2절).
        """
        return self.cmdword.casefold() == name.casefold()

    def addressed_to(self, node: str) -> bool:
        """이 메시지가 node 앞으로 온 것인가 (브로드캐스트 포함)."""
        return self.is_broadcast or self.dst.casefold() == node.casefold()

    def kv(self) -> dict[str, str]:
        return parse_kv(self.body)


def parse(data: bytes | str) -> Message | None:
    """와이어 바이트 -> Message.  malformed 면 None.

    스펙 2.5절: malformed 메시지에는 **절대 ERROR 로 응답하지 않는다**.  조용히
    버리고 로그만 남긴다.  그래서 예외 대신 None 을 돌려준다.
    """
    if isinstance(data, bytes):
        try:
            text = data.decode('ascii', errors='strict')
        except UnicodeDecodeError:
            return None
    else:
        text = data

    # 종료문자: '\r' 로 끝나야 한다.  실무상 '\r\n' 도 받아준다.
    text = text.rstrip('\n')
    if not text.endswith(TERMINATOR):
        return None
    text = text[:-1]

    if len(text) > MAX_LEN:
        return None
    if '\r' in text or '\n' in text or '\0' in text:
        return None

    return parse_line(text)


def parse_line(text: str) -> Message | None:
    """종료문자를 뺀 한 줄 -> Message.  로그 재생·테스트에서도 쓴다."""
    text = text.strip()
    if not text:
        return None

    m = _HEADER_RE.match(text)
    if not m:
        return None

    src, dst = m.group('src'), m.group('dst')
    rest = (m.group('rest') or '').strip()

    mtype = 'REQ'
    explicit = False
    if rest:
        head, _, tail = rest.partition(' ')
        if head.upper() in MSG_TYPES:
            mtype = head.upper().rstrip(':')
            explicit = True
            rest = tail.strip()

    cmdword, _, body = rest.partition(' ')
    return Message(
        src=src,
        dst=dst,
        mtype=mtype,
        cmdword=cmdword,
        body=body.strip(),
        raw=text,
        explicit_type=explicit,
    )


def format(src: str, dst: str, mtype: str = '', cmdword: str = '',
           body: str = '') -> bytes:
    """Message 를 와이어 바이트로.

    Args:
        mtype:   'DONE' | 'STATUS' | ... 또는 빈 문자열(=암묵 REQ).
                 'REQ' 는 관례상 리터럴로 보내지 않으므로 빈 문자열로 취급한다.
        cmdword: 커맨드워드.  **비동기 알림이면 명시적으로 빈 문자열을 넘긴다.**
                 어떤 상태에서도 물려받지 않는 것이 이 함수의 계약이다(DevNote 5.4).

    구분자는 1칸으로 정규화한다.  수신측이 공백 개수를 무시하기 때문이다.
    """
    parts = [f'{src}>{dst}']
    t = mtype.upper().rstrip(':')
    if t and t != 'REQ':
        parts.append(f'{t}:')
    if cmdword:
        parts.append(cmdword)
    if body:
        parts.append(body)
    line = ' '.join(parts)
    return (line + TERMINATOR).encode('ascii', errors='replace')


def format_raw(line: str) -> bytes:
    """이미 완성된 한 줄을 그대로 와이어에 실는다.

    레거시의 불규칙한 공백을 바이트 단위로 재현해야 하는 bug_compat 경로 전용.
    일반 경로는 format() 을 쓴다.
    """
    return (line + TERMINATOR).encode('ascii', errors='replace')


def parse_kv(body: str) -> dict[str, str]:
    """본문의 key=value 쌍을 뽑는다.

    'quoted' / (parenthesised) 다중 단어 값을 하나로 묶는다.  레거시 GetArg() 는
    이걸 못 해서 각 애플리케이션이 알아서 처리해야 했다(ics_legacy_report 7.2절).
    감싼 기호는 벗겨서 돌려준다.
    """
    out: dict[str, str] = {}
    for m in _KV_RE.finditer(body):
        val = m.group('val')
        if len(val) >= 2 and val[0] in "'(" and val[-1] in "')":
            val = val[1:-1]
        out[m.group('key')] = val
    return out


def iter_kv(body: str) -> Iterator[tuple[str, str]]:
    """parse_kv 와 같지만 **원문 순서를 보존**한다.

    AUXSTATUS/TCSSTATUS 중계는 필드 순서를 뒤집어야 하므로 순서가 중요하다
    (DevNote 4.3).
    """
    for m in _KV_RE.finditer(body):
        val = m.group('val')
        if len(val) >= 2 and val[0] in "'(" and val[-1] in "')":
            val = val[1:-1]
        yield m.group('key'), val


def quote(value: str) -> str:
    """여러 단어면 작은따옴표로 감싼다 (스펙 2.3절)."""
    if value == '' or ' ' in value or '\t' in value:
        return f"'{value}'"
    return value


def quote_always(value: str) -> str:
    """항상 작은따옴표로 감싼다.

    스펙은 단어 하나면 그대로 두어도 된다고 하지만, 실제 ICS 는 ObjectName 을
    한 단어일 때도 늘 감쌌다 (실측: ObjectName='begin', ObjectName='BLG11').
    OBSAgent 가 값 자체를 파싱하진 않지만 형태를 맞춰 둔다.
    """
    return f"'{value}'"


def paren(value: str) -> str:
    """OBSERVER 값처럼 괄호로 감싸는 관례 (실측: Observer=(jeonghyun))."""
    return f'({value})'

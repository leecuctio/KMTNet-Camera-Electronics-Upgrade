#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Outbound message construction -- the single place where wire strings are made.

이 모듈이 존재하는 이유가 곧 이 프로젝트의 핵심 발견이다.

레거시 ICS/IC 는 IMPv2 메시지의 커맨드워드 슬롯을 "가장 최근에 처리한 메시지"의
것으로 채운 채 비우지 않았다.  그 결과 비동기 상태 메시지가 엉뚱한 커맨드워드를
달고 나갔다 (CTIO 634일 실측, DevNote 5.1):

    ICS>OBS  STATUS:  STATUS: EXPSTATUS=INTEGRATING          173,635회
    K.IC>OBS STATUS: REQ  Integration Remaining=54 sec.      148,430회
    K.IC>OBS STATUS: DATASOURCE  Integration Remaining=5 sec.  39,614회
    K.IC>ICS DONE:   REQ  Erase Cycle Complete.               31,604회

REQ/DONE/PONG/FOUND 같은 **프로토콜 키워드**까지 그 자리에 나타난다 -- 검증된
명령 테이블이 아니라 직전 파싱 토큰에서 슬롯이 채워졌다는 뜻이다.  심하면 잔재가
겹쳐 쌓여 본문을 밀어내고 소실시킨다 (DevNote 5.2):

    ICS>OBS STATUS: SYNCHRONIZE STATUS:                      본문 완전 소실
    K.IC>ICS DONE: EXP  FLAT  ImageType=FLAT ...             커맨드워드 2개 적층
    ICS>OBS DONE: PROJID  ProjID=ALL BIAS BIAS               꼬리에 잔재 2회

그래서 이 모듈의 계약은 이렇다:

1. **모든 메서드가 cmdword 를 명시적으로 정한다.**  비동기 알림은 빈 문자열을
   명시적으로 넘긴다.  어떤 인스턴스 상태에서도 물려받지 않는다.
2. **조립은 매번 새 bytes 를 만든다.**  재사용 버퍼도, bytearray 누적도 없다.
3. **송신 직전에 validate() 로 자가검증한다.**  위반이면 로그 경고를 남기고,
   테스트에서는 실패로 잡는다.
4. **EXPSTATUS= 알림은 상태가 실제로 전이한 시점에 1회씩만, OBS 로만** 보낸다
   (DevNote 3.2.1/3.2.2).  레거시처럼 셔터가 닫힌 뒤에도 INTEGRATING 을 계속
   내보내지 않는다.

bug_compat=true 로 두면 1번 규칙을 일부러 어겨 레거시 오염을 재현한다.  골든
대조 테스트에서 레거시 로그와 바이트 단위로 맞추기 위한 것이고, **기본은
꺼짐**이다.  두 모드 모두 OBSAgent 규약 테스트를 통과해야 한다 -- 즉 "이 버그는
OBSAgent 동작에 영향이 없다"가 검증 대상이다.
"""

from __future__ import annotations

import logging
import re

from . import impv2
from .config import SimConfig
from .nodes import NodeRouter, Role

log = logging.getLogger('ics_sim.emitter')

#: 커맨드워드 슬롯에 올 수 있는 정당한 값.  validate() 가 이걸로 검사한다.
KNOWN_COMMANDS = frozenset({
    # ICS 레벨
    'STATUS', 'ACQSTATUS', 'FILENAME', 'SYNCHRONIZE', 'EXPNUM', 'TIME',
    'LEDFLASH', 'PROJID', 'OBSERVER', 'EXP', 'GO',
    'BIAS', 'DARK', 'OBJECT', 'FLAT', 'SKY', 'DOMEFLAT',
    # IC 레벨
    'DMAWAIT', 'DATASOURCE', 'INITIALIZE', 'ERASE', 'SHOPEN', 'SHCLOSE',
    'FLASHNOW', 'AUXSTATUS', 'TCSSTATUS',
    # 미구현(스텁)이지만 명령 테이블에는 있는 것들
    'BIN', 'ROI', 'DISPL', 'STOP', 'ABORT', 'MOVIE',
    # out-of-band
    'PING', 'PONG',
})

_HEADER_OK = re.compile(r'^[A-Za-z0-9._]{2,8}>[A-Za-z0-9._]{2,8} '
                        r'(?:DONE|STATUS|ERROR|WARNING|FATAL):')

#: "Didn't understand <cmd> <args> ?" 처럼 받은 명령을 되읊는 정당한 본문.
_ECHO_PREFIXES = ("Didn't understand",)

#: 커맨드워드 슬롯으로 볼 토큰의 모양.  대문자 영숫자(끝에 콜론 허용).
#: 레거시 오염에서 실제로 나타난 형태 -- REQ, DONE, STATUS:, DATASOURCE, PING 등.
_CMDWORD_SHAPE = re.compile(r'^[A-Z][A-Z0-9]*:?$')

#: 비동기 알림 본문별로 허용되는 커맨드워드.
#:
#: 이 표가 레거시 오염을 잡아내는 핵심이다.  같은 본문이 REQ / DATASOURCE /
#: SHOPEN / FLASHNOW / PING / 빈 값 등 제각각인 커맨드워드를 달고 나갔다는 것이
#: 슬롯이 관리되지 않았다는 증거였다(DevNote 5.1).  신규는 본문마다 커맨드워드가
#: 하나로 정해져 있어야 한다.
_BODY_CMDWORD: tuple[tuple[str, frozenset[str]], ...] = (
    ('EXPSTATUS=', frozenset({''})),
    ('Remaining=', frozenset({''})),
    ('Integration Remaining=', frozenset({''})),
    ('Shutter=Closed', frozenset({'', 'SHCLOSE'})),
    ('Shutter=Open', frozenset({'', 'SHOPEN'})),
    ('Wrote ', frozenset({''})),
    ('Erase Cycle Complete', frozenset({''})),
    ('Initialization Complete', frozenset({'', 'INITIALIZE'})),
    ('PCTREAD=', frozenset({'', 'GO'})),
    ('Acquisition Complete', frozenset({'', 'GO'})),
    ('Disk Write Complete', frozenset({'', 'GO'})),
    ('Image ', frozenset({''})),
    ('LED Flash Done', frozenset({'', 'FLASHNOW'})),
)


def split_cmdword(rest: str) -> tuple[str, str]:
    """타입 토큰 뒤의 나머지를 (커맨드워드, 본문)으로 가른다.

    레거시 C 라이브러리는 이 분리를 애플리케이션에 떠넘겼고(ics_legacy_report
    7.2절) 그래서 슬롯이 관리되지 않았다.  여기서는 한 가지 규칙으로 못박는다:
    **첫 토큰이 대문자 커맨드워드 모양이면 커맨드워드, 아니면 전부 본문.**

    이 규칙 덕에 `STATUS: EXPSTATUS=INITIALIZING` 의 `EXPSTATUS=INITIALIZING` 이나
    `DONE: Erase Cycle Complete.` 의 `Erase` 가 커맨드워드로 오인되지 않는다.
    """
    head, _, tail = rest.strip().partition(' ')
    if head and '=' not in head and _CMDWORD_SHAPE.match(head):
        return head, tail.strip()
    return '', rest.strip()


class HygieneError(Exception):
    """조립된 메시지가 오염 검사에 걸렸을 때 (테스트에서 쓴다)."""


def validate(line: str, cmdword: str | None = None) -> list[str]:
    """조립된 한 줄이 오염 패턴에 걸리는지 검사한다.

    검사 항목 (DevNote 5.4-4):
      * header           -- src>dest TYPE: 형태인가
      * type_in_body     -- 본문/커맨드워드에 메시지 타입 키워드가 재등장하는가
                            (레거시: "STATUS:  STATUS: EXPSTATUS=..")
      * unknown_cmdword  -- 커맨드워드가 KNOWN_COMMANDS 밖인가
                            (레거시: REQ / DONE / FOUND / PONG 이 슬롯에 등장)
      * stale_cmdword    -- 본문에 맞지 않는 커맨드워드인가
                            (레거시: "DATASOURCE  Integration Remaining=5 sec.")
      * stacked_cmdword  -- 본문 첫 토큰이 또 다른 커맨드워드인가
                            (레거시: "EXP  FLAT  ImageType=FLAT ..")
      * repeated_tail    -- 끝에 같은 bare 토큰이 반복되는가
                            (레거시: "ProjID=ALL BIAS BIAS")

    Args:
        cmdword: 발신측이 **의도한** 커맨드워드.  Emitter 는 이걸 넘긴다.
            생 로그 한 줄을 검사할 때(테스트의 역방향 검증)는 None 을 넘기고,
            그러면 split_cmdword() 로 추정한다.

    Returns:
        위반 항목 이름 목록.  비어 있으면 깨끗하다.

    Note:
        "커맨드워드는 있는데 본문이 빈" 경우(레거시의 `STATUS: EXPNUM`)는
        검사하지 않는다.  `K.IC>ICS STATUS: GO` 처럼 본문 없는 정상 메시지가
        레거시에 실재하기 때문이다.
    """
    problems: list[str] = []
    if not _HEADER_OK.match(line):
        return ['header']

    header, _, after = line.partition(' ')
    mtype, _, rest = after.partition(' ')
    guess_cmd, guess_body = split_cmdword(rest)
    cmd = guess_cmd if cmdword is None else cmdword
    body = guess_body if cmdword is None else rest[len(cmdword):].strip()

    # 1) 메시지 타입 키워드 재등장
    for tok in (cmd, *body.split()):
        if tok.endswith(':') and tok.rstrip(':').upper() in impv2.TYPE_TOKENS:
            problems.append('type_in_body')
            break

    # 2) 커맨드워드가 허용 집합 밖 (빈 문자열은 정상 -- 비동기 알림)
    #    발신측이 의도를 알려줬을 때만 검사한다.  생 로그에서 추정한 값은
    #    믿을 수 없다 -- "WARNING: FITS file '..' already exists" 의 'FITS' 처럼
    #    산문 첫 단어가 커맨드워드로 오인되기 때문이다.  추정 경로에서는 아래
    #    stale_cmdword 검사가 실질적인 그물 역할을 한다.
    if cmdword is not None and cmd and cmd.upper().rstrip(':') not in KNOWN_COMMANDS:
        problems.append('unknown_cmdword')

    # 3) 본문과 커맨드워드의 정합
    for prefix, allowed in _BODY_CMDWORD:
        if body.startswith(prefix):
            if cmd.upper() not in allowed:
                problems.append('stale_cmdword')
            break

    tokens = body.split()
    echoing = any(body.startswith(p) for p in _ECHO_PREFIXES)

    # 4) 커맨드워드 적층
    #    토큰이 **커맨드워드 모양**(대문자)일 때만 센다.  'Erase Cycle Complete.'
    #    의 'Erase' 처럼 문장 첫 단어가 우연히 명령어와 같은 경우를 오탐하지
    #    않기 위해서다.  레거시 오염("EXP  FLAT  ImageType=..")은 전부 대문자라
    #    이 조건으로 잡힌다.
    if tokens and not echoing and _CMDWORD_SHAPE.match(tokens[0]) \
            and tokens[0].upper() in KNOWN_COMMANDS:
        problems.append('stacked_cmdword')

    # 5) 꼬리 반복 ("ProjID=ALL BIAS BIAS")
    if len(tokens) >= 2 and not echoing:
        a, b = tokens[-2], tokens[-1]
        if a == b and _CMDWORD_SHAPE.match(a) and a.upper() in KNOWN_COMMANDS:
            problems.append('repeated_tail')

    return problems


class Emitter:
    """모든 발신 문자열을 만든다.  다른 모듈은 여기 메서드만 부른다."""

    def __init__(self, cfg: SimConfig, router: NodeRouter, send) -> None:  # noqa: ANN001
        """
        Args:
            send: ``send(payload: bytes, dest_node: str)`` 콜백.
        """
        self.cfg = cfg
        self.router = router
        self._send = send
        #: bug_compat 전용.  마지막으로 파싱한 커맨드워드를 기억했다가 비동기
        #: 메시지에 흘려넣어 레거시 오염을 재현한다.  기본 경로는 절대 읽지
        #: 않는다 -- 그게 이 프로그램이 고치려는 버그 그 자체이므로.
        self._stale_cmdword = ''
        #: validate() 위반 누적 (테스트가 확인)
        self.violations: list[tuple[str, list[str]]] = []

    # -- 저수준 -----------------------------------------------------------

    def note_inbound(self, cmdword: str) -> None:
        """bug_compat 재현용으로 직전 커맨드워드를 기록한다.

        레거시의 버그 경로를 흉내내는 것이 유일한 목적이다.
        """
        if cmdword:
            self._stale_cmdword = cmdword.upper()

    def _cmd(self, cmdword: str) -> str:
        """실제로 실을 커맨드워드.

        정상 경로에서는 인자를 그대로 쓴다.  bug_compat 일 때만, 비동기 알림
        (cmdword='')에 직전 커맨드워드를 흘려넣어 레거시 오염을 재현한다.
        """
        if cmdword:
            return cmdword
        if self.cfg.behavior.bug_compat and self._stale_cmdword:
            return self._stale_cmdword
        return ''

    def emit(self, dest: str, mtype: str, cmdword: str = '', body: str = '',
             role: Role = Role.ICS, ccd: str = '') -> str:
        """메시지 하나를 조립해 발신 큐에 넣는다.  조립된 줄을 돌려준다."""
        src = self.router.emit_id(role, ccd)
        actual = self._cmd(cmdword)
        payload = impv2.format(src, dest, mtype, actual, body)
        line = payload.rstrip(b'\r').decode('ascii', errors='replace')

        # 발신측이 의도한 커맨드워드를 그대로 넘겨 검사한다 -- 줄에서 다시
        # 추정하지 않는다.  추정은 생 로그를 검사할 때만 쓴다.
        problems = validate(line, actual)
        if problems and not self.cfg.behavior.bug_compat:
            log.warning('message hygiene violation %s: %s', problems, line)
        if problems:
            self.violations.append((line, problems))

        self._send(payload, dest)
        return line

    def emit_req(self, dest: str, cmdword: str, body: str = '',
                 role: Role = Role.ICS, ccd: str = '') -> str:
        """타입 토큰 없는 요청 (암묵 REQ).  REQ: 는 리터럴로 보내지 않는다."""
        src = self.router.emit_id(role, ccd)
        payload = impv2.format(src, dest, '', cmdword, body)
        line = payload.rstrip(b'\r').decode('ascii', errors='replace')
        self._send(payload, dest)
        return line

    # -- 명령 응답 (ICS 레벨) ---------------------------------------------

    def _suffix(self, expstatus: str) -> str:
        """노출 진행 중이면 응답 끝에 붙는 ' EXPSTATUS=<상태>'.

        레거시는 노출 중에도 설정 변경을 잠그지 않고 현재 국면을 덧붙였다.
        OBSAgent v0.2.7 이 Wrote 카운트 버그를 고친 원인이 바로 이 접미사다.
        """
        from .state import ExpStatus
        return '' if expstatus == ExpStatus.IDLE else f' EXPSTATUS={expstatus}'

    def done(self, dest: str, cmdword: str, body: str, expstatus: str = 'IDLE',
             role: Role = Role.ICS, ccd: str = '') -> str:
        return self.emit(dest, 'DONE', cmdword,
                         body + self._suffix(expstatus), role, ccd)

    def error(self, dest: str, cmdword: str, body: str, expstatus: str = 'IDLE',
              role: Role = Role.ICS, ccd: str = '') -> str:
        return self.emit(dest, 'ERROR', cmdword,
                         body + self._suffix(expstatus), role, ccd)

    def warning(self, dest: str, body: str, role: Role = Role.ICS,
                ccd: str = '') -> str:
        return self.emit(dest, 'WARNING', '', body, role, ccd)

    def status(self, dest: str, body: str, cmdword: str = '',
               role: Role = Role.ICS, ccd: str = '') -> str:
        return self.emit(dest, 'STATUS', cmdword, body, role, ccd)

    # -- 노출 국면 알림 (ICS -> OBS) --------------------------------------
    #
    # 상태가 실제로 전이하는 시점에 1회씩만 부른다.  과다 발신하면 OBSAgent 의
    # CamStatus 가 역행해 스크립트 관측이 깨진다 (DevNote 3.2.1).

    def exp_status(self, dest: str, expstatus: str) -> str:
        """STATUS: EXPSTATUS=<상태>.  커맨드워드 없음."""
        return self.status(dest, f'EXPSTATUS={expstatus}')

    def idle_done(self, dest: str) -> str:
        """노출 종료.  마지막 프레임은 DONE: 으로 낸다."""
        return self.emit(dest, 'DONE', '', 'EXPSTATUS=IDLE')

    def image_complete(self, dest: str, index: int, total: int) -> str:
        """GO n 의 중간 프레임 완료 (DevNote 6.1).

        마지막 프레임이 아닌 경우 DONE: 대신 STATUS: 로 나간다.  OBSAgent 가
        v0.3.0 에서 `STATUS:` 에도 EXPSTATUS=IDLE 핸들러를 넣은 이유다.
        """
        return self.status(dest, f'Image {index} of {total} complete. EXPSTATUS=IDLE')

    def countdown_ics(self, dest: str, remaining: int, total: int,
                      expstatus: str) -> str:
        """DARK/BIAS 경로의 카운트다운.  ICS 가 직접 보낸다."""
        return self.status(
            dest,
            f'Remaining={remaining} sec. of {total} sec. EXPSTATUS={expstatus}')

    def shutter_closed_ics(self, dest: str, expstatus: str) -> str:
        """DARK/BIAS 의 논리적 노출 종료 알림.

        셔터를 연 적이 없어도 `Shutter=Closed` 로 보낸다.  레거시 관례를 그대로
        유지하는 이유는 OBSAgent 가 이걸로 CLOSING 을 밟고 곧바로
        EXPSTATUS=READOUT/PCTREAD= 로 READ_1 이 되기 때문이다 (DevNote 3.2.1).
        """
        return self.status(
            dest,
            f'Shutter=Closed Integration Remaining=0 sec. EXPSTATUS={expstatus}')

    def wrote_relay(self, dest: str, path: str, rate: int,
                    expstatus: str) -> str:
        """CB 의 Wrote 를 OBS 로 중계한다.

        **OBSAgent 가 세는 것은 이 중계 메시지다** (CB->ICS 직송이 아니라).
        4회 누적돼야 FitsSaved=1 이 된다 (DevNote 3.2, 4.1).
        """
        body = f'Wrote LASTFILE={path} RATE={rate} KB/sec'
        return self.status(dest, body + self._suffix(expstatus))

    # -- IC 발신 ----------------------------------------------------------

    def ic_initialize_done(self, dest: str, ccd: str) -> str:
        return self.emit(dest, 'DONE', 'INITIALIZE', 'Initialization Complete.',
                         Role.IC, ccd)

    def ic_erase_done(self, dest: str, ccd: str) -> str:
        return self.emit(dest, 'DONE', '', 'Erase Cycle Complete.', Role.IC, ccd)

    def ic_shutter_open(self, dest: str, ccd: str) -> str:
        return self.emit(dest, 'STATUS', 'SHOPEN', 'Shutter=Open', Role.IC, ccd)

    def ic_countdown(self, dest: str, ccd: str, remaining: int,
                     cmdword: str = '') -> str:
        """SHOPEN 경로의 카운트다운.

        레거시는 첫 메시지에만 SHOPEN 커맨드워드를 달고 이후엔 비웠다가, 그
        사이 다른 명령이 오면 그 커맨드워드를 흘려보냈다.  신규는 시종일관
        일관되게 낸다 -- 기본은 빈 커맨드워드.
        """
        return self.emit(dest, 'STATUS', cmdword,
                         f'Integration Remaining={remaining} sec.', Role.IC, ccd)

    def ic_shutter_closed(self, dest: str, ccd: str) -> str:
        return self.emit(dest, 'STATUS', '',
                         'Shutter=Closed Integration Remaining=0 sec.',
                         Role.IC, ccd)

    def ic_go_ack(self, dest: str, ccd: str) -> str:
        """GO 접수 확인.  본문 없는 정상 메시지."""
        return self.emit(dest, 'STATUS', 'GO', '', Role.IC, ccd)

    def ic_pctread(self, dest: str, ccd: str, pct: int) -> str:
        return self.emit(dest, 'STATUS', 'GO', f'PCTREAD={pct}', Role.IC, ccd)

    def ic_acq_complete_obs(self, dest: str, ccd: str, pct: int) -> str:
        """sourceID 에게 보내는 획득 완료.

        `Acquisition Complete.` 는 **마침표를 포함해야** OBSAgent 가 센다.
        4회 누적돼야 IDLE_2 로 간다 (DevNote 3.2).
        """
        return self.emit(dest, 'STATUS', 'GO',
                         f'PCTREAD={pct} Acquisition Complete. '
                         f'Disk Transfer Starting.', Role.IC, ccd)

    def ic_acq_complete_ics(self, dest: str, ccd: str) -> str:
        """ICS 방향 획득 완료.  실측상 마침표가 없다."""
        return self.emit(dest, 'STATUS', 'GO', 'Acquisition Complete',
                         Role.IC, ccd)

    def ic_disk_write_complete(self, dest: str, ccd: str) -> str:
        """레거시는 XIS PING/PONG 왕복을 타이밍 신호로 쓴 뒤 이걸 보냈다.

        OBSAgent 는 이 문자열을 파싱하지 않는다 (핸들러가 없다).  보내도
        무해하지만 저장 완료 판단에는 쓰이지 않는다 -- 그 판단은 Wrote 4회다.
        """
        return self.emit(dest, 'STATUS', 'GO', 'Disk Write Complete',
                         Role.IC, ccd)

    def ic_status(self, dest: str, ccd: str, ch, expstatus: str) -> str:  # noqa: ANN001
        body = (f'Inst=KMTN{ccd.lower()}  DetectorID={ccd} '
                f'Driving={ch.driving} {ch.flags} Build={ch.build}')
        return self.done(dest, 'STATUS', body, expstatus, Role.IC, ccd)

    def ic_flashnow_done(self, dest: str, ccd: str) -> str:
        return self.emit(dest, 'DONE', 'FLASHNOW', 'LED Flash Done.',
                         Role.IC, ccd)

    # -- CB 발신 ----------------------------------------------------------

    def cb_wrote(self, dest: str, ccd: str, path: str, rate: int) -> str:
        return self.emit(dest, 'DONE', '',
                         f'Wrote LASTFILE={path} RATE={rate} KB/sec',
                         Role.CB, ccd)

    # 구판의 `name_clash()`(파일명 fail-safe WARNING 발신)는 없앴다 --
    # D-016 이 격리·개명을 폐지하고 **충돌 시 번호 증가 + WARNING 로그**로
    # 바꿨다 (raw spec 2.3절, D-016).  충돌 사실은 헤더에서 `FILENAME` 의
    # `DETID` 필드(`.MK`/`.NT`)를 뗀 값과 `EXPID` 의 **값 비교**로 남고(D-019),
    # 하류 필터가 그것을 근거로 돈다.

    # -- out-of-band ------------------------------------------------------

    def ping(self, dest: str) -> str:
        return self.emit_req(dest, 'PING')

    def register_ping(self, node_id: str, dest: str = 'AL',
                      cmdword: str = 'PING') -> str:
        """노드 등록용 PING/PONG.  **src 를 그대로 지정한다** (emit_node_mode 무시).

        IMPv2 에는 등록 API 가 없다.  노드가 자기 이름으로 아무 메시지나 보내면
        XIS 가 "노드ID -> 그 데이터그램의 (IP,port)" 를 기억하는 것이 전부다
        (XIS 소스 `clients.c` updateHosts(), DevNote 3.1.1).  따라서
        **수신하려는 이름 전부로 한 번씩 보내야** 그 이름 앞으로 오는 메시지가
        도착한다.

        emit_node_mode 를 따르지 않는 이유: merged 모드는 **발신 이름**만
        ICS 로 통일하는 옵션이고, 수신은 언제나 9개 ID 전부여야 한다
        (DevNote 3.1).  등록까지 merged 로 하면 K.IC 앞으로 오는
        kstatus/dmawait/datasource 가 영영 도달하지 않는다.

        Args:
            cmdword: 기동 시 자발적으로 등록하는 것이면 `PING`,
                XIS 의 `XIS>AL PING` 에 답하는 것이면 `PONG`.
        """
        payload = impv2.format(node_id, dest, '', cmdword, '')
        self._send(payload, dest)
        return payload.rstrip(b'\r').decode('ascii', errors='replace')

    def pong(self, dest: str, role: Role = Role.ICS, ccd: str = '') -> str:
        """PONG 은 타입 토큰 없이 커맨드워드만 보낸다 (스펙 2.4절)."""
        return self.emit_req(dest, 'PONG', role=role, ccd=ccd)

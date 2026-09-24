#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""배선 -- `ics_sim.IcsSim` 에 Archon 백엔드를 끼운다.

**`ics_sim` 의 배선을 그대로 물려받는다.**  9개 노드 수신 · 명령 처리 · 시퀀서 ·
텔레메트리 중계 · 콘솔은 전부 그쪽 것이고, 여기서 갈라지는 줄기는 다섯이다:

1. **백엔드** -- `ics_sim.hardware.register_backend()` 로 실기 구현을 넣는다.
   그 자리가 원래 확장점이고(`[hardware] backend = archon` 한 줄), 구현만
   이 패키지에 있다.
2. **`ICSBUILD`** -- `ics_archon` 자신의 버전·빌드일시로 바꾼다.  안 바꾸면
   `ics_sim` 의 값이 실려 **거짓 provenance** 가 된다 (`ics_sim/__init__.py`
   의 `build_id()` 경고).
3. **`CTRLnCFG`** -- `[controllers] ctrlN_cfg` 가 비어 있으면 적용 ACF 경로에서
   채운다 (`fill_controller_cfg_names`).  컨트롤러는 ACF 이름을 보고하지 않으므로
   (매뉴얼 p.54) 호스트가 아는 유일한 근거가 그 파일명이다.
   ⛔ `RDMODE` 는 유도하지 않는다 -- ini 전용이고 비면 `UNKNOWN` 이다 (규격 5.5절).
4. **종료** -- 전원을 끄고 연결을 닫는다.  전원을 켠 채로 끝나는 것은 검출기
   쪽 위험이다.
5. **접속과 텔레메트리 감시** -- 기동에서 컨트롤러에 접속하고, 그 뒤에 컨트롤러
   마다 주기 감시 태스크를 띄운다 (층 1·2, `archon/monitor.py`).
   `IcsSim.spawn()` 을 쓰므로 `ics_sim` 은 무수정이다.  **한 컨트롤러의 접속자는
   이 프로세스 하나다** -- guide 는 `icg_archon` 이 같은 방식으로 맡는다.

그 위에 얹은 운영 기능(진공게이지 · guide 노출 잠금 · HK 질의 · XIS 확인 · 운영자
명령)은 `IcsDispatcher`·`IcsArchon` docstring 과 각 모듈(`gaugectl` · `expenablectl` ·
`hkwire` · `xischeck` · `tcsclock`) 머리말에 있다.
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import replace
import os

from datetime import timedelta

from . import _simpath, build_id, config as acfg_mod

_simpath.ensure()

from ics_sim.app import IcsSim                            # noqa: E402
from ics_sim.hardware import register_backend             # noqa: E402

from .archon.backend import ArchonBackend                 # noqa: E402
from .archon import parse                                  # noqa: E402
from .config import CTRLTAGS                                # noqa: E402
from .archon.monitor import TelemetryMonitor              # noqa: E402
from .archon import trigout as trigout_core               # noqa: E402
from .archon.protocol import ArchonError                  # noqa: E402
from .gaugectl import CMD as GAUGE_CMD, GaugeControl      # noqa: E402
from . import hkwire                                     # noqa: E402
from .expenablectl import CMD as EXPENABLE_CMD, ExpEnableControl  # noqa: E402
from .tcsclock import ClockWatch, watch_tc_queries
from .xischeck import XIS_ID, XisGate         # noqa: E402
from ics_sim import console, emitter                       # noqa: E402
from ics_sim import rawhdr                                  # noqa: E402
from ics_sim.commands import Dispatcher, Reply, ReplyKind  # noqa: E402
from ics_sim.hardware.base import BackendError             # noqa: E402
from ics_sim.impv2 import Message                          # noqa: E402
from ics_sim.nodes import Target                           # noqa: E402
from ics_sim.state import utcnow                           # noqa: E402

log = logging.getLogger('ics_archon.app')

# ---------------------------------------------------------------------------
# 운영자 명령 넷 -- `CCDFLUSH` · `CCDPOWON` · `CCDPOWOFF` · `ARCHON` (운영자 지시 2026-09-05)
# ---------------------------------------------------------------------------

#: emitter 의 커맨드워드 어휘에 더하는 ICS 운영자 명령.  `icg_archon/commands.py` 의
#: `ICG_COMMANDS` 와 같은 패턴이다 -- `emitter.validate()` 가 이 표로 발신을 검사하므로
#: 등록 없이 쓰면 응답마다 `unknown_cmdword` 위생 경고가 난다 (`emitter.py:170`).
ICS_OPS_COMMANDS = frozenset({'CCDFLUSH', 'CCDPOWON', 'CCDPOWOFF', 'ARCHON',
                              'HK', 'HKDATA', 'HKNOW', 'C1HKDATA', 'C2HKDATA',
                              'C1HK', 'C2HK', 'C1HKNOW', 'C2HKNOW',
                              'C1TRIGOUT', 'C2TRIGOUT'})

#: `ARCHON` 바이패스 응답 본문의 상한 [문자].  한 메시지 상한 `impv2.MAX_LEN`(2048) 안에
#: 머리(`src>dest DONE: ARCHON MK ` -- 노드 이름 8자씩이면 ~30) 와 잘림 꼬리(~40) 를
#: 더해도 들어가게 잡았다.  `STATUS` 응답이 ~2 KB 라 이 자리가 실제로 쓰인다.
ARCHON_REPLY_MAX = 1800

#: 취득 중 거부 문구 -- 넷이 같은 낱말을 쓴다 (운영자 지시 2026-09-05).
BUSY_TEXT = 'Exposure in progress -- ABORT first'


def extend_vocabulary() -> None:
    """모듈 상수(frozenset)를 합집합으로 갈아 끼운다 -- 한 번이면 된다."""
    if not ICS_OPS_COMMANDS <= emitter.KNOWN_COMMANDS:
        emitter.KNOWN_COMMANDS = frozenset(emitter.KNOWN_COMMANDS
                                           | ICS_OPS_COMMANDS)


def wire_text(text) -> str:  # noqa: ANN001
    """와이어에 실을 수 있는 ASCII 한 줄로.

    전송 계층이 `encode('ascii', errors='replace')` 를 하므로(`impv2.format`) 비ASCII
    는 어차피 `?` 가 된다 -- 여기서 미리 바꿔 **길이를 셀 때 바이트 수와 문자 수가
    같게** 한다 (잘림 판정이 그 길이로 한다).  개행·제어문자는 메시지를 깨므로
    (`impv2.parse` 가 `\\r`/`\\n`/`\\0` 을 malformed 로 버린다) 공백으로 접는다.
    """
    out = []
    for ch in str(text):
        o = ord(ch)
        if o < 32 or o == 127:
            out.append(' ')
        elif o > 126:
            out.append('?')
        else:
            out.append(ch)
    return ' '.join(''.join(out).split())


def _fail_text(exc: BaseException) -> str:
    """예외를 `Failed:` 뒤에 붙일 문구로.  ⚠️ 컨트롤러 층의 문구는 대개 한글이라
    `?` 로 뭉개진다 -- 그때는 `(see log)` 를 붙여 원문이 로그에 있음을 알린다."""
    raw = str(exc) or type(exc).__name__
    text = wire_text(raw)
    if any(ord(ch) > 126 for ch in raw):
        text += ' (see log)'
    return text


class _OpError(Exception):
    """운영자 명령이 **정해진 문구로** 실패했다 -- 본문은 이미 와이어용이다."""

#: ACF 경로에서 헤더 값을 뽑는 규칙은 **하나다** -- `config.cfg_name_from_acf()`
#: (`CTRLnCFG`).  ⛔ `RDMODE` 는 ini 전용이다 (규격 5.5절, 비면 `UNKNOWN`) -- 유도하지
#: 않는다 (유도 규칙과 그 대조는 2026-09-06 에 걷었다 -- `config.py` 머리 주석).
#: `config._cross_checks()` 는 손으로 적은 `ctrlN_cfg` 와 ACF 경로에서 나오는 이름의
#: 어긋남을 기동에서 본다.
#: ⚠️ 자르기는 `config.CFG_SUFFIXES`(`.acf`/`.cfg`) 둘만 뗀다 -- `CTRLnCFG` 는 값 자체가
#: 되므로 범용 `splitext` 처럼 판 번호의 점(`…_R2609.1`)을 먹으면 안 된다.


def fill_controller_cfg_names(cfg, acfg) -> None:  # noqa: ANN001
    """`[controllers] ctrlN_cfg` 가 비었으면 **적용 ACF 경로에서** 채운다.

    raw spec v1.8 5.5절이 `CTRLnCFG` 를 *"폴더 경로와 확장자(`.acf`/`.cfg`)를
    뗀 이름"* 으로 못박았고, 그 이름의 유일한 근거가 `[archon] acf_mk`/`acf_nt`
    다 -- 컨트롤러는 적용 ACF 이름을 보고하지 않는다 (매뉴얼 p.54).

    **왜 파생인가** -- 종전에는 `[controllers] ctrlN_cfg` 와 `[archon]
    acf_mk`/`acf_nt` 가 같은 파일을 가리키는 **별개의 ini 키**여서 둘을 맞추는
    것이 사람 몫이었다.  벤치와 관측소가 각자 ini 를 적으므로(`CAMVER` 와 같은
    부류) 한쪽만 어긋나면 **그 사이트 자료만 영구히 다른 설정 이름**을 단다.

    **왜 덮지 않나** -- 원장이 `Source = ICS INI` 로 못박은 카드는 전부 ini 에서
    고칠 수 있어야 하고(운영자 지시 2026-08-22, `tests/test_ini_cards.py`),
    `[controllers]` 의 원칙도 "채워져 있으면 INI 가 이긴다" 다 (같은 블록의
    `RDMODE` 는 파생 없이 ini 값만 쓴다).  대가로 남는
    "둘이 어긋난 채 배포" 는 **기동 경고**로 드러낸다
    (`config._cross_checks()`).  배포되는 `ics_archon.ini` 는 이 칸이 비어
    있으므로 실기에서는 늘 파생이 채운다.

    ⚠️ **`NC` 는 빈 값이 아니다** -- 운영자가 "그 컨트롤러는 없다" 고 적어 둔
    것이므로(규격 5.0절 sentinel) 파생이 덮지 않는다.

    ⚠️ **`ics_sim` 은 한 줄도 고치지 않는다** -- 이 함수가 `ics_sim` 의
    `ControllersCfg` 를 **미리 채워** 넣을 뿐이고, 그 아래 사슬
    (`overrides()` -> `sequencer` -> `rawhdr.controller_header()`)은 읽기만
    한다.
    """
    for tag in acfg_mod.CTRLTAGS:
        n = acfg.index_of(tag)
        field = 'ctrl%d_cfg' % n
        if str(getattr(cfg.controllers, field, '') or '').strip():
            continue                       # 손편집 값(`NC` 포함)이 이긴다
        derived = acfg_mod.cfg_name_from_acf(acfg.acf.get(tag, ''))
        if derived:
            setattr(cfg.controllers, field, derived)
            log.info('CTRL%dCFG derived from the acf path -- %s (%s)',
                     n, derived, acfg.acf.get(tag, ''))


class IcsDispatcher(Dispatcher):
    """ICS 명령 처리부 -- `GO` 앞에서 진공게이지를 끈다 (운영자 2026-09-04).

    ⭐ **스크립트 관측이든 콘솔에서 직접 친 `GO` 든 여기를 지난다** -- 그래서
    한 곳에서 끈다.  `ics_sim` 은 한 줄도 안 고친다.

    추가 (운영자 지시 2026-09-05) -- 컨트롤러를 **직접** 만지는 운영자 명령 넷:

    * `CCDFLUSH [MK|NT|ALL]`   -- 유휴 CCD 를 FlushFrame 한 바퀴로 비운다
    * `CCDPOWON [MK|NT|ALL]`   -- `POWERON` + `POWER=4` 확인 (+ `poweron_wait` 추가 대기, ICS 기본 0)
    * `CCDPOWOFF [MK|NT|ALL]`  -- `POWEROFF`
    * `ARCHON <MK|NT> <원문…>` -- 바이패스: 명령 원문을 한 컨트롤러에, 응답 원문을 그대로

    ⭐ 넷 다 **응답이 나중에 온다** (`Reply.noop()` -> 왕복 뒤 `emit.done/error`) --
    핸들러는 동기 함수인데 왕복(특히 `POWERON` 의 `POWER=4` 확인, 실측 ~1초)이 필요하기
    때문이고, `ics_sim` 의 `ERASE`/`SHOPEN` · icg 의 `HTRSET` 이 쓰는 **같은 선례**다.

    ⛔ **취득 중(`seq.busy`)이면 앞의 셋은 거부한다** (`BUSY_TEXT`).  진행 중 노출 위에
    `LOADPARAMS`(flush) · `POWEROFF` 가 들어가면 자료를 망친다.  ⭐ 반대 방향도 막는다 --
    셋 중 하나가 **돌고 있는 동안 `GO`** 는 거부한다 (`_op_inflight`).  `CCDPOWOFF` 의
    `POWEROFF` 가 아직 안 나갔는데 `GO` 가 `prepare()` 를 지나면(`powered` 가 아직 True)
    노출 도중에 전원이 내려간다.  같은 이유로 운영자 명령끼리도 한 번에 하나다.
    ⭐ `ARCHON` 은 **제한이 없다** (운영자 2026-09-05 *"제한 없이 모두 풀어줘"*) -- 취득
    중이든 다른 조작 중이든 받고, `_op_inflight` 도 잡지 않는다(`GO` 를 막지 않는다).
    원문이 자료를 망치는 것은 운영자의 몫이다 -- 로그에는 남는다.
    """

    def __init__(self, app) -> None:  # noqa: ANN001
        super().__init__(app)
        #: 돌고 있는 운영자 명령의 커맨드워드 (없으면 '').  `GO` 와 서로 배타.
        self._op_inflight = ''

    def _inflight_reply(self, cmdword: str):  # noqa: ANN202
        """다른 운영자 명령이 도는 중이면 거부 Reply, 아니면 None.

        ⚠️ 커맨드워드를 **괄호 안에** 둔다 -- 본문 첫 토큰이 등록된 커맨드워드면
        `emitter.validate()` 가 `stacked_cmdword` 로 운다 (`ERROR: GO CCDPOWON in
        progress …` 는 안 된다).
        """
        if self._op_inflight:
            return Reply.error(cmdword, 'Operator command in progress (%s) -- retry '
                                        'when it is DONE' % self._op_inflight)
        return None

    def cmd_go(self, msg, target):  # noqa: ANN001, ANN201
        bad = self._inflight_reply('GO')
        if bad is not None:
            # ⛔ 게이지·되켜기 타이머를 만지기 **전에** 거절한다.
            return bad
        reply = super().cmd_go(msg, target)
        if reply is not None and reply.kind is ReplyKind.ERROR:
            # ⛔ **GO 가 거절됐다** -- 취득이 시작되지 않았으므로 게이지도 되켜기
            # 타이머도 안 건드린다.  켜짐대기였으면 그 10분이 **그대로 흐른다**.
            # ⛔ 종전(2026-09-15 판)에는 타이머를 이 판정 **앞에서** 풀어서, 거절된
            # `GO` 하나가 켜짐대기 타이머를 지우고 아무도 다시 안 걸었다 -- 다음 `GO`
            # 가 성공해 끝날 때까지 게이지가 꺼진 채 남았다 (DevNote 11.96).
            # ⚠️ 취득 중 거절도 여기로 온다 -- 그때는 타이머가 원래 없고, 돌고 있는
            # 취득의 타이머는 `_watch_acquisition` 이 독출 완료 때 건다.
            return reply
        gauge = getattr(self.app, 'gauge', None)
        if gauge is not None:
            # ⭐ **수락된 뒤, `begin_go()` 앞에서** 되켜기 타이머를 푼다 -- 아래
            # 태스크가 `HKDATA` 답을 기다리는 사이에 만료되면 노출 도중에 켜진다.
            # 끌지 말지는 태스크가 정한다.  ⚠️ `cmd_go` 는 동기라 `super().cmd_go`
            # 와 여기 사이에 `await` 가 없다 -- 순서를 뒤로 옮겨도 만료될 틈은 없다.
            gauge.cancel_reenable('exposure starting')
        # ⭐ **HKDATA 를 묻고, 그 답으로 게이지를 끈다** (운영자 2026-09-15).
        # 시퀀서 태스크는 `super().cmd_go` 가 만들었지만 이 동기 흐름이 끝나야
        # 돈다 -- 그래서 여기서 띄운 태스크가 첫 프레임의 `initialize()` 보다
        # 먼저 백엔드에 걸린다 (`backend.hk_task`).
        self.app.begin_go()
        return reply

    # -- 운영자 명령 넷 (2026-09-05) -- 공통 -----------------------------------

    def _archon_backend(self, cmdword: str):  # noqa: ANN202
        """archon 백엔드와 **거부 Reply** 를 짝으로 돌려준다.

        `--backend sim` 에는 원시 함수(`flush_ccd`/`power_ccd`/`raw_command`)가 없다 --
        그때 조용히 `DONE` 을 내면 *"명령은 먹었는데 아무것도 안 바뀜"* 이 된다
        (icg `_ctrl()` 과 같은 이유).
        """
        be = getattr(self.app, 'backend', None)
        if be is None or not all(hasattr(be, n) for n in
                                 ('flush_ccd', 'power_ccd', 'raw_command', 'tags')):
            return None, Reply.error(cmdword, 'Controller is not available (no '
                                              'hardware backend)')
        return be, None

    def _refuse_if_busy(self, cmdword: str):  # noqa: ANN202
        """취득 중이거나 다른 운영자 명령이 도는 중이면 거부 Reply, 아니면 None."""
        seq = getattr(self.app, 'seq', None)
        if seq is not None and seq.busy:
            return Reply.error(cmdword, BUSY_TEXT)
        return self._inflight_reply(cmdword)

    def _tags_arg(self, cmdword: str, body: str, be):  # noqa: ANN001, ANN202
        """`[MK|NT|ALL]` 인자 -> (`'ALL'` 또는 태그, None) / (None, 거부 Reply).

        ⭐ usage 의 태그 나열은 **이 배치에 살아 있는 컨트롤러**(`backend.tags`)다 --
        벤치 1대 구성에서는 `[MK|ALL]` 로 읽힌다.
        """
        parts = body.split()
        usage = 'usage: %s [%s|ALL]' % (cmdword, '|'.join(be.tags))
        if len(parts) > 1:
            return None, Reply.error(cmdword, usage)
        if not parts:
            return 'ALL', None
        word = parts[0].upper()
        if word == 'ALL' or word in be.tags:
            return word, None
        return None, Reply.error(cmdword, usage)

    def _start_op(self, dest: str, cmdword: str, work) -> Reply:  # noqa: ANN001
        """왕복을 백그라운드로 띄우고 `noop` -- 답은 `_finish_op` 이 낸다."""
        self._op_inflight = cmdword
        self.app.spawn(self._finish_op(dest, cmdword, work))
        return Reply.noop()

    async def _finish_op(self, dest: str, cmdword: str, work, *,  # noqa: ANN001
                         track: bool = True) -> None:
        """`work` 가 돌려준 본문을 `DONE` 으로, 예외는 `ERROR: <cmd> Failed: …` 로.

        `track=False`(`ARCHON`)면 `_op_inflight` 를 건드리지 않는다 -- 잡지도 않았으니
        내리지도 않는다 (다른 명령의 표시를 지우면 안 된다).

        ⚠️ `except Exception` 은 `CancelledError` 를 잡지 않는다(3.8+ BaseException) --
        종료가 태스크를 취소하면 응답 없이 끝나고 `finally` 만 표시를 내린다.
        """
        try:
            body = await work
        except _OpError as exc:
            self.emit.error(dest, cmdword, str(exc))
            return
        except (BackendError, ArchonError, TimeoutError, OSError) as exc:
            log.error('%s failed -- %s', cmdword, exc,
                      extra={'detail': '컨트롤러 왕복이 실패했다 -- 와이어에는 ASCII 로 '
                                       '접은 문구가 나간다, 원문은 이 줄'})
            self.emit.error(dest, cmdword, 'Failed: %s' % _fail_text(exc))
            return
        except Exception as exc:  # noqa: BLE001  하나의 명령이 프로세스를 죽이지 않는다
            log.exception('%s failed -- unexpected exception', cmdword,
                          extra={'detail': '예상 밖 예외다 -- 한 명령이 프로세스를 못 '
                                           '죽이게 여기서 받는다.  추적은 이 줄에'})
            self.emit.error(dest, cmdword, 'Failed: %s: %s'
                            % (type(exc).__name__, _fail_text(exc)))
            return
        finally:
            if track:
                self._op_inflight = ''
        self.emit.done(dest, cmdword, body)

    def _emit_failed(self, dest: str, word: str, what: str,
                     exc: BaseException, detail: str = '') -> None:
        """늦은 `ERROR: <word> Failed: …` 한 줄 -- **원문은 로그에 먼저** 남긴다.

        ⛔ `'Failed: %s' % exc` 를 그대로 싣지 않는다 (DevNote 11.96) -- 컨트롤러 층의
        문구는 대개 한글이라 와이어에서 `?` 로 뭉개진다 (`impv2.format`).  `_fail_text` 가
        ASCII 로 접고 `(see log)` 를 붙이므로, 그 말이 참이 되게 **같은 자리에서** 원문을
        로그에 남긴다.  `what` 은 영문 짧은 구 (`'raising the trigger line'`) -- 영문 로그
        줄에 그대로 박힌다.
        """
        log.error('%s: %s failed -- %s', word, what, exc,
                  extra={'detail': detail or '와이어에는 ASCII 로 접은 문구가 나간다 '
                                             '-- 원문은 이 줄'})
        self.emit.error(dest, word, 'Failed: %s' % _fail_text(exc))

    # -- CCDFLUSH ----------------------------------------------------------------

    def cmd_hk(self, msg: Message, target: Target) -> Reply:
        """HK [NOW] -- `HKDATA` 와 같다 (운영자 확정 2026-09-06).  ICG 에 묻는다."""
        return self._ask_icg('HK', msg.body)

    def cmd_hknow(self, msg: Message, target: Target) -> Reply:
        """HKNOW -- `HK NOW` 의 별칭 (운영자 지시 2026-09-15).  ICG 에는 `HK NOW` 로
        나간다 -- 답이 `DONE: HK …` 로 와야 `register_report` 가 받아 적는다."""
        if msg.body.strip():
            return Reply.error('HKNOW', "Takes no argument -- got '%s'"
                               % msg.body.strip())
        return self._ask_icg('HK', 'NOW', reply_as='HKNOW')

    def cmd_hkdata(self, msg: Message, target: Target) -> Reply:
        """HKDATA [NOW] -- ⭐ **ICS 는 이 값을 만들지 않는다.  ICG 에 묻는다.**

        게이지·히터·듀어 RTD 는 **ICG 만** 만지므로(규격 10.4절) ICS 가
        자기 헤더의 5.6절 HK 카드를 채우려면 물어보는 수밖에 없다.

        ⚠️ **답은 이 응답이 아니라 뒤따르는 보고로 온다** -- `ICG>ICS DONE:
        HKDATA …` 가 도착하면 `register_report` 로 걸어 둔 조치(`_on_hkdata`)가
        받아 적는다.  화면에는 전송층이 찍는 **그 와이어 줄**로 보인다 -- 조치는
        따로 출력하지 않는다 (맨 `print` 는 걷었다, 2026-09-15 벤치).  여기서
        기다리지 않는 것이 의도다: 기다리면 ICG 가 조용할 때 ICS 명령 처리부가
        함께 멈춘다.

        ⭐ **`NOW` 는 그대로 넘긴다** (2026-09-15 벤치: 콘솔 `hkdata now` 가
        `HKDATA` 로 나가 ICG 가 폴링값을 답했다 -- `HKUDATE` 가 안 움직였다).
        ICG 쪽 규약과 같이 `NOW` 만 받고 다른 인자는 거절한다.
        """
        return self._ask_icg('HKDATA', msg.body)

    def cmd_c1hkdata(self, msg: Message, target: Target) -> Reply:
        """C1HKDATA [NOW] -- 컨트롤러 1(MK) 의 텔레메트리 한 줄 (5.6절 `C1_*` 의 와이어 판)."""
        return self._cx_hkdata(msg, 1)

    def cmd_c2hkdata(self, msg: Message, target: Target) -> Reply:
        """C2HKDATA [NOW] -- 컨트롤러 2(NT).  `C1HKDATA` 와 같은 규약."""
        return self._cx_hkdata(msg, 2)

    # ⭐ 별칭 `C1HK`/`C2HK` (운영자 지시 2026-09-15) -- `HK`/`HKDATA` 짝과 같은 규약:
    # **같은 본문, 커맨드워드만 다르다** (답은 `DONE: C1HK …`).
    def cmd_c1hk(self, msg: Message, target: Target) -> Reply:
        """C1HK [NOW] -- `C1HKDATA` 와 같다."""
        return self._cx_hkdata(msg, 1)

    def cmd_c2hk(self, msg: Message, target: Target) -> Reply:
        """C2HK [NOW] -- `C2HKDATA` 와 같다."""
        return self._cx_hkdata(msg, 2)

    def cmd_c1hknow(self, msg: Message, target: Target) -> Reply:
        """C1HKNOW -- `C1HK NOW` (= `C1HKDATA NOW`) 의 별칭.  인자는 안 받는다."""
        return self._cx_hknow(msg, 1)

    def cmd_c2hknow(self, msg: Message, target: Target) -> Reply:
        """C2HKNOW -- `C2HK NOW` 의 별칭."""
        return self._cx_hknow(msg, 2)

    def _cx_hknow(self, msg: Message, n: int) -> Reply:
        word = (msg.cmdword or '').upper() or 'C%dHKNOW' % n
        if msg.body.strip():
            return Reply.error(word, "Takes no argument -- got '%s'"
                               % msg.body.strip())
        return self._cx_hkdata(replace(msg, body='NOW'), n)

    def _cx_hkdata(self, msg: Message, n: int) -> Reply:
        """`CnHKDATA [NOW]` -- science 컨트롤러 n 의 `STATUS` 텔레메트리를 와이어로 낸다
        (운영자 확정 2026-09-04 · 구현 2026-09-15, DevNote 11.91).  포맷은 `hkwire.ctrl_body`.

        * 인자 없음 -> **감시 스냅샷**(`status_live`, `[archon] monitor_interval` 주기, 왕복 없음).
          `monitor = false` 면 표본이 없어 전 자리 결측이다 -- 그때는 `NOW`.
        * `NOW` -> `refresh_status_live()` 로 **지금** 한 번 읽는다 (왕복 하나, 락 대기 포함).
        * ⭐ 헤더의 `Cn_*` 와 같은 자리 표(`rawhdr.TEMP_MOD_LABELS` 10 · `VOLT_RAILS` 7)와 같은
          D4 규칙(`VALID=0` 이면 전 자리 결측)이다 -- `parse.telemetry_of`.
        * ⚠️ **늦은 `DONE`** 이다 (`HKDATA` 와 같다).  컨트롤러 자리가 없으면 곧바로 `ERROR`.
        """
        # 답의 커맨드워드는 **받은 그대로** (`C1HKDATA` 또는 별칭 `C1HK`).
        word = (msg.cmdword or '').upper() or 'C%dHKDATA' % n
        be, bad = self._archon_backend(word)
        if bad is not None:
            return bad
        tag = CTRLTAGS[n - 1]
        ctrl = getattr(be, 'ctrls', {}).get(tag)
        if ctrl is None:
            return Reply.error(word, 'Controller %d (%s) is not configured' % (n, tag))
        arg = msg.body.split()
        if len(arg) > 1 or (arg and arg[0].upper() != 'NOW'):
            return Reply.error(word, "Usage: %s [NOW] -- got '%s'" % (word, msg.body.strip()))
        self.app.spawn(self._do_cx_hkdata(msg.src, word, n, ctrl, now=bool(arg)))
        return Reply.noop()

    async def _do_cx_hkdata(self, dest: str, word: str, n: int, ctrl,  # noqa: ANN001
                            now: bool) -> None:
        try:
            if now:
                try:
                    await ctrl.refresh_status_live()
                except (ArchonError, TimeoutError, OSError) as exc:
                    # ⚠️ 실패해도 답은 낸다 -- 감시 스냅샷이 그대로 나가고 `CnUDATE` 가 그 나이를 말한다.
                    log.warning('%s NOW: STATUS read failed -- %s.  answering with '
                                'the monitor snapshot', word, exc)
            status = dict(getattr(ctrl, 'status_live', None) or {})
            unit = parse.telemetry_of(status)
            ident = parse.unit_identity(getattr(ctrl, 'system', None) or {}).get('sn')
            body = hkwire.ctrl_hkdata_body(
                n=n, labels=rawhdr.TEMP_MOD_LABELS, rails=rawhdr.VOLT_RAILS,
                unit=unit, status=status, ident=ident,
                sampled_at=float(getattr(ctrl, 'status_live_at', 0.0) or 0.0))
        except Exception as exc:  # noqa: BLE001
            # ⚠️ `(see log)` 가 참이 되게 원문을 로그에 먼저 (`_emit_failed`).
            self._emit_failed(dest, word, 'building the telemetry reply', exc)
            return
        self.emit.done(dest, word, body)

    def _ask_icg(self, cmdword: str, body: str = '',
                 reply_as: str | None = None) -> Reply:
        """ICG 에 질의 한 줄.  ⚠️ 답은 **보고 경로**로 온다.

        `body` 는 `NOW` 하나만 받는다 (대소문자 무관) -- ICG 의 `HKDATA`/`HK` 규약과
        같다.  ⛔ 응답 본문에 `DONE:` 을 적지 않는다 -- 타입 낱말이 본문에 들면
        `emitter.validate()` 의 `type_in_body` 가 경고를 낸다 (2026-09-15 벤치).
        `reply_as` 는 우리 즉답의 커맨드워드(별칭 `HKNOW` 가 쓴다) -- 와이어로는
        `cmdword` 가 나간다.
        """
        dest = self.app.acfg.icg_node
        mine = reply_as or cmdword
        if not dest:
            # ⛔ 와이어 응답은 ASCII 영문 -- 한글은 `impv2.format` 에서 `?` 로 뭉개진다.
            return Reply.error(mine, '[archon] icg_node is empty -- no ICG to ask')
        arg = (body or '').strip()
        if arg and arg.upper() != 'NOW':
            return Reply.error(mine, 'Unknown argument %r -- use %s [NOW]'
                               % (arg, cmdword))
        arg = 'NOW' if arg else ''
        self.emit.emit_req(dest, cmdword, arg)
        return Reply.done(mine,
                          'Queried %s%s -- its %s report follows separately'
                          % (dest, ' now' if arg else '', cmdword))

    #: ⛔ **science 에 없는 기반 명령** (운영자 2026-09-09).
    #:
    #: `FLASHNOW`/`LEDFLASH` 는 점검용 LED 프로젝터다.  실기 백엔드의
    #: `flash_led()` 는 `BackendError(_NOT_YET)` 라 **늘 실패**했고, 그 자리는
    #: `SHOPEN <초>`(Trigger Out 강제)가 대신한다.
    #: ⭐ 감추는 것이 아니라 **거절한다** -- 도움말에서 빼려면 응답도 멈춰야
    #: 한다 (`console.extend_help` 의 `drop=` 과 짝).
    #: ⚠️ **시뮬(`ics_sim`)에는 그대로 남는다** -- 레거시 흐름을 흉내내는 것이
    #: 시뮬의 몫이고 OBSAgent 시험이 그것을 본다.
    UNSUPPORTED = frozenset({'FLASHNOW', 'LEDFLASH'})

    # -- 셔터 (Trigger Out) ------------------------------------------------
    #
    # ⭐ **`SHOPEN <초>`/`SHCLOSE` 를 Trigger Out 강제로 구현한다** (운영자
    # 2026-09-09).  ICG 의 `TRIGOUT <ms>`/`TRIGOUT 0` 과 **같은 알맹이**
    # (`archon.trigout`)를 쓰고 **쉬는 상태만 다르다** (눈금도 다르다 -- `SHOPEN` 은 초).
    #
    # ⛔ **배선이 계통마다 다르다** (운영자 2026-09-09): science 의 Trigger Out
    # 은 **실제 셔터**를 몰고, guide 의 것은 **LED** 를 켠다.  그래서 science 의
    # 쉬는 상태는 `FORCE=0`(타이밍 스크립트가 셔터를 몬다)이고 guide 는 `1` 이다.
    #
    # ⛔ **정상 취득 경로는 안 지난다** -- 시퀀서는 `backend.open_shutter()` 를
    # 직접 부른다.  여기서 바뀌는 것은 **손으로 여는 경우**뿐이다.
    # ⚠️ 종전 판은 `backend.open_shutter()` 를 불러 **실제 노출을 걸었다**
    # (`LOADPARAMS` + 트리거).  지금은 **선만 세운다** -- 프레임을 안 만든다.
    # ⭐ 응답 흐름(`IC Shutter Open`/`Closed`)은 **그대로 둔다**: OBSAgent 가 그
    # 문면을 보므로 낱말까지 바꾸면 바깥이 깨진다.
    # ⛔ **시뮬 백엔드면 기반 판 그대로**다.

    #: science 의 쉬는 상태 -- `FORCE=0`(타이밍 스크립트가 몬다).  guide 와 반대.
    _TRIGOUT_REST = trigout_core.REST_SCIENCE

    #: `SHOPEN <초>` 가 띄운 펄스 태스크 (하나만 산다).
    #: ⭐ **`spawn` 하는 자리에서 곧바로 적고, 내림이 끝난 뒤에 지운다** (DevNote 11.96)
    #: -- 올림(`raise_line` = `WCONFIG` 둘 + `APPLYSYSTEM`, ICG 실측 ~235 ms) · 대기 ·
    #: 내림 **세 창 모두**에서 `ABORT`·종료·`SHCLOSE`·`CnTRIGOUT` 이 이 펄스를 본다.
    #: 태스크 안에서 올림 뒤에 적던 판은 올림 창을, 내림 앞에서 지우던 판은 내림 창을
    #: 놓쳤다 -- 그 창에 온 종료가 태스크를 취소하면 선이 HIGH 로 남는다.
    _shutter_timer = None

    #: 취득 중 `APPLYSYSTEM` 경고를 한 번만 낸다.
    _warned_busy_apply = False

    def _shutter_ctrls(self, be):  # noqa: ANN001, ANN202
        """셔터를 모는 컨트롤러들 -- ACF 배선이 정한다 (`drives_shutter`)."""
        return [c for tag, c in getattr(be, 'ctrls', {}).items()
                if be.acfg.drives_shutter(tag)]

    def _refuse_if_stopping(self, word: str):  # noqa: ANN202
        """종료가 시작됐으면 거부 Reply, 아니면 None -- **선을 올리는 명령만** 부른다.

        ⛔ `release_pulse('shutdown')` 뒤, 전송이 닫히기 전에 온 `SHOPEN <초>`·
        `CnTRIGOUT <ms>` 가 새 펄스를 띄우면 `super().stop()` 이 그 태스크를 **내림 없이**
        취소한다 (링크도 이미 닫혔다) -- 선이 HIGH(셔터를 모는 쪽이면 열린 채)로 남는다
        (DevNote 11.96).  깃발(`IcsArchon.stopping`)은 `stop()` 의 첫 줄이 세운다.
        ⚠️ 내리는 명령(`SHCLOSE`·`SHOPEN 0`·`CnTRIGOUT 0`)은 막지 않는다 -- 선을 올리지 않는다.
        """
        if not getattr(self.app, 'stopping', False):
            return None
        log.warning('%s refused -- the ICS is shutting down', word,
                    extra={'detail': '종료가 펄스를 이미 내렸다 -- 새로 올리면 내릴 이가 '
                                     '없어 선이 HIGH 로 남는다'})
        return Reply.error(word, 'Shutting down -- not raised')

    def _cancel_shutter_timer(self) -> bool:
        """진행 중 `SHOPEN` 을 끊는다.  **끊었으면 `True`** (셔터가 열려 있거나 여닫는 중이다).

        ⚠️ 끊은 쪽이 선을 책임진다 -- 끊긴 태스크는 내림을 안 돌린다.
        """
        timer, self._shutter_timer = self._shutter_timer, None
        if timer is None or timer.done():
            return False
        timer.cancel()
        return True

    async def release_pulse(self, why: str) -> bool:
        """진행 중 `SHOPEN`·`CnTRIGOUT` 펄스를 **끊고 선을 쉬는 상태로 내린다**.  끊었으면 `True`.

        ⛔ **끊는 자리가 둘이다** (운영자 2026-09-09): `ABORT` · **종료**.
        안 닫으면 **셔터가 강제로 열린 채 남는다** -- `abort_now()` 의
        `RESETTIMING` 은 타이밍 코어만 되돌리는데 `SHOPEN` 중에는
        `TRIGOUTFORCE=1` 이라 핀이 코어를 아예 안 따라가기 때문이다.
        ⛔ **종료가 특히 나쁘다**: `spawn` 한 펄스 태스크가 종료에 취소되므로
        내림이 **영영 안 돌고** 사람 없는 채로 셔터가 열린 채 끝난다.
        ⭐ **`C1TRIGOUT`/`C2TRIGOUT` 펄스도 끊는다** (DevNote 11.96) -- 종전에는
        `_shutter_timer` 만 봐서 `CnTRIGOUT` 중에 종료하면 `TRIGOUTLEVEL=1`·`FORCE=1`
        이 설정 메모리와 핀에 남았다 (MK 면 셔터가 열린 채).  각 컨트롤러는 **자기
        쉬는 상태**로 내린다 (`_trigout_rest` -- 셔터를 모는 쪽 `FORCE=0`, 안 모는 쪽 `1`).
        ⚠️ `ABORT` 도 같은 함수라 `CnTRIGOUT` 을 끊는다 -- ICG `TRIGOUT` 과 같은 규약이다.
        ⭐ 펄스 태스크는 **올림 · 대기 · 내림** 내내 핸들을 쥐고 있으므로(DevNote 11.96)
        어느 창에서 와도 여기서 끊고 다시 내린다.  `CnTRIGOUT` 이 끊은 `SHOPEN` 의 다른
        컨트롤러 내림(`_rest_left_by_shopen`)도 `_trigout_timers` 에 있어 같이 잡힌다.
        ⚠️ **핸들 없는 한 적용 내림은 못 본다** -- `SHCLOSE`·`SHOPEN 0`·`CnTRIGOUT 0` 의
        내림(`_do_shutter_close`·`_do_trigout_rest`)은 핸들을 안 적는다.  그 한 적용(~235 ms)
        도중에 종료가 오면 뒤의 `backend.shutdown()`(링크 닫기)이나 `super().stop()` 의
        취소가 그 내림을 끊을 수 있다 -- 선이 HIGH 로 남을 수 있는 **남은 창**이다.
        ⭐ **종료가 이 함수를 지난 뒤의 올림은 막는다** (DevNote 11.96) -- `IcsArchon.stop()`
        이 첫 줄에서 `stopping` 을 세우므로, 전송이 닫히기 전에 온 `SHOPEN <초>`·
        `CnTRIGOUT <ms>` 는 `Shutting down -- not raised` 로 거절된다 (`_refuse_if_stopping`).
        종전에는 새 펄스가 떠서 `super().stop()` 이 내림 없이 취소했다 (링크도 이미 닫혔다).
        그래서 종료의 남은 창은 위의 **핸들 없는 내림 하나**다.
        ⚠️ 펄스가 없었으면 아무것도 안 쓴다.  ⚠️ **실패를 삼킨다** (종료 경로).
        ⚠️ `why` 는 영문 짧은 낱말 (`'ABORT'`·`'shutdown'`) -- 영문 로그 줄에 그대로 박힌다.
        """
        cut_shutter = self._cancel_shutter_timer()
        # ⚠️ 복사본을 돈다 -- `_cancel_trigout_timer` 가 표에서 꺼낸다(pop).
        cut_tags = [t for t in list(self._trigout_timers or {})
                    if self._cancel_trigout_timer(t)]
        if not cut_shutter and not cut_tags:
            return False
        be, bad = self._archon_backend('SHCLOSE')
        if bad is not None:
            return False
        ctrls = getattr(be, 'ctrls', {})
        #: 태그 -> (컨트롤러, 쉬는 상태).  한 컨트롤러는 한 번만 내린다.
        jobs: dict = {}
        if cut_shutter:
            for tag, c in ctrls.items():
                if be.acfg.drives_shutter(tag):
                    jobs[tag] = (c, self._TRIGOUT_REST)
        for tag in cut_tags:
            c = ctrls.get(tag)
            if c is not None:
                jobs.setdefault(tag, (c, self._trigout_rest(be, tag)))
        if not jobs:
            return False
        log.warning('%s -- cutting the running pulse on %s and resting the line',
                    why, ','.join(jobs),
                    extra={'detail': 'SHOPEN %s · CnTRIGOUT %s'
                                     % ('끊음' if cut_shutter else '없음',
                                        ','.join(cut_tags) or '없음')})
        for tag, (c, rest) in jobs.items():
            try:
                await trigout_core.rest_line(c, rest)
            except Exception as exc:  # noqa: BLE001 -- 종료를 막지 않는다
                log.error('%s -- could not rest the %s trigger line: %s',
                          why, tag, exc,
                          extra={'detail': '⚠️ HIGH(셔터를 모는 쪽이면 열린 채)로 '
                                           '남을 수 있다'})
        return True

    def cmd_abort(self, msg: Message, target: Target) -> Reply:
        """ABORT -- 기반 동작 + **진행 중 `SHOPEN`·`CnTRIGOUT` 펄스를 끊는다** (`release_pulse`)."""
        self.app.spawn(self.release_pulse('ABORT'))
        return super().cmd_abort(msg, target)

    # -- Trigger Out 을 컨트롤러별로 (운영자 2026-09-12) -------------------
    #
    # ⭐ **`SHOPEN`/`SHCLOSE` 와 갈라 둔 까닭**: 그 둘은 *"셔터를 연다"* 는 뜻이라
    # `[archon] shutter_ctrl` 이 지정한 컨트롤러만 움직인다.  `CnTRIGOUT` 은
    # *"이 컨트롤러의 핀을 움직인다"* 라서 **지정 여부와 무관**하다 -- 배선 점검과
    # 예비 유닛 시험에 그 길이 필요하다.
    # ⭐ ICG 의 `TRIGOUT <ms>` 와 **같은 규약**이다 (ms · `0` 이면 즉시 내림).
    # ⚠️ `SHOPEN` 은 **초**, `CnTRIGOUT` 은 **밀리초**다 -- 눈금이 다르다.

    #: 태그 -> `CnTRIGOUT` 펄스 태스크 -- **컨트롤러마다 따로**다.
    #: ⛔ `SHOPEN` 의 `_shutter_timer` 와 다른 물건이다 (그쪽은 셔터를 모는
    #: 것들을 한 태스크가 함께 몬다).
    #: ⭐ `_shutter_timer` 와 같이 **`spawn` 하는 자리에서 적고 내림이 끝난 뒤에 지운다**
    #: (DevNote 11.96) -- 올림 · 대기 · 내림 세 창 모두에서 끊는 쪽이 본다.
    #: 끊는 쪽이 선을 책임진다 -- 다음 명령 · `SHOPEN`/`SHCLOSE` · `release_pulse`(ABORT·종료).
    #: ⚠️ `CnTRIGOUT` 이 끊은 `SHOPEN` 의 **다른 컨트롤러 내림**(`_rest_left_by_shopen`)도
    #: 여기 적는다 -- 같은 규약(끊는 쪽이 선을 책임진다)으로 종료가 그 내림을 본다.
    _trigout_timers = None

    def cmd_c1trigout(self, msg: Message, target: Target) -> Reply:
        """C1TRIGOUT <ms> -- **컨트롤러 1(MK)** 의 Trigger Out 을 <ms> 동안 HIGH.

        `0` 이면 대기 중 펄스를 끊고 **즉시** 쉬는 상태로 내린다.
        ⭐ `[archon] shutter_ctrl` 이 무엇이든 **이 컨트롤러를 움직인다.**
        ⚠️ 단위는 **밀리초**다 (`SHOPEN` 은 초).
        """
        return self._trigout_cmd('C1TRIGOUT', acfg_mod.CTRLTAGS[0], msg)

    def cmd_c2trigout(self, msg: Message, target: Target) -> Reply:
        """C2TRIGOUT <ms> -- **컨트롤러 2(NT)** 의 Trigger Out.  위와 같은 규약."""
        return self._trigout_cmd('C2TRIGOUT', acfg_mod.CTRLTAGS[1], msg)

    def _trigout_rest(self, be, tag: str) -> tuple:  # noqa: ANN001
        """이 컨트롤러가 내려갈 **쉬는 상태** -- 셔터를 모느냐로 갈린다.

        | | `TRIGOUTLEVEL` | `TRIGOUTFORCE` | 뜻 |
        |---|---|---|---|
        | 셔터를 **몬다** | `0` | `0` | 선을 타이밍 스크립트에 **돌려준다** |
        | **안 몬다** | `0` | `1` | 우리가 **붙들어** LOW 로 고정 |

        ⭐ 운영자 규범 그대로다 (2026-09-12) -- *"지정되지 않은 유닛은 계속
        `trigoutforce=true`/`trigoutlevel=0` 을 유지"*.
        ⛔ 안 모는 쪽을 `FORCE=0` 으로 돌려주면 그 핀이 **자기 타이밍 스크립트를
        따라가** 노출마다 흔들린다.
        """
        if be.acfg.drives_shutter(tag):
            return trigout_core.REST_SCIENCE       # ('0', '0') -- 스크립트에 반환
        return trigout_core.REST_GUIDE             # ('0', '1') -- 붙든다

    def _cancel_trigout_timer(self, tag: str) -> bool:
        """그 컨트롤러의 진행 중 펄스를 끊는다.  **끊었으면 `True`** (선이 HIGH 거나 올리고
        내리는 중).  ⚠️ 끊은 쪽이 선을 책임진다 -- 끊긴 태스크는 내림을 안 돌린다."""
        timers = self._trigout_timers or {}
        timer = timers.pop(tag, None)
        if timer is None or timer.done():
            return False
        timer.cancel()
        return True

    def _trigout_cmd(self, word: str, tag: str, msg: Message) -> Reply:
        """`CnTRIGOUT` 의 알맹이 -- 둘이 태그만 다르다."""
        be, bad = self._archon_backend(word)
        if bad is not None:
            return bad
        ctrl = getattr(be, 'ctrls', {}).get(tag)
        if ctrl is None:
            return Reply.error(word, 'Controller %s is not available' % tag)
        arg = msg.body.split()
        if not arg:
            return Reply.error(word, 'Missing duration (milliseconds)')
        try:
            ms = float(arg[0])
        except ValueError:
            return Reply.error(word, 'Invalid duration: %s' % arg[0])
        # ⛔ `nan`·`inf` 도 거절한다 -- `float()` 은 받아 주지만 `nan` 은 아래 비교를
        # 전부 빠져나가 선을 올리고, `asyncio.sleep(nan)` 이 안 깨어 **선이 HIGH 로
        # 남는다** (DevNote 11.96).
        if not math.isfinite(ms) or ms < 0:
            return Reply.error(word, 'Invalid duration: %s' % arg[0])
        if ms > 0:
            # ⛔ 종료 중이면 올리지 않는다 -- 타이머를 만지기 **전에** 거절한다.
            refused = self._refuse_if_stopping(word)
            if refused is not None:
                return refused
        if self._trigout_timers is None:
            self._trigout_timers = {}
        self._cancel_trigout_timer(tag)
        # ⛔ **같은 컨트롤러를 `SHOPEN` 이 몰고 있으면 그 타이머도 끊는다** --
        # 안 끊으면 옛 타이머가 나중에 깨어나 지금 세운 선을 내린다.
        if be.acfg.drives_shutter(tag) and self._cancel_shutter_timer():
            # ⛔ **`SHOPEN` 이 함께 몰던 다른 컨트롤러도 내린다** (DevNote 11.96) --
            # `shutter_ctrl = both` 면 `SHOPEN` 은 두 대를 올리는데, 끊긴 `SHOPEN` 은
            # 내림을 안 돌리고 이 명령은 자기 컨트롤러만 만진다.  안 내리면 다른 쪽이
            # `TRIGOUTLEVEL=1`·`FORCE=1` 인 채 **핸들 없이** 남아 `ABORT`·종료도 못
            # 찾는다 (셔터가 열린 채).  쉬는 상태는 `SHOPEN` 의 것(`_TRIGOUT_REST`)이다.
            others = [t for t in getattr(be, 'ctrls', {})
                      if t != tag and be.acfg.drives_shutter(t)]
            log.warning('%s took the line from a pending SHOPEN (%s)',
                        word, tag,
                        extra={'detail': '셔터를 모는 컨트롤러다 -- SHOPEN 의 남은 '
                                         '시간은 버려진다%s'
                                         % (' · 함께 몰던 %s 는 쉬는 상태로 내린다'
                                            % ','.join(others) if others else '')})
            for t in others:
                self._rest_left_by_shopen(word, be, t)
        rest = self._trigout_rest(be, tag)
        if ms == 0:
            self.app.spawn(self._do_trigout_rest(msg.src, word, ctrl, rest))
            return Reply.noop()
        # ⭐ **핸들은 여기서 적는다** -- 올림 앞이다.  태스크 안에서 올림 뒤에 적으면
        # 그 창(올림 한 번, ICG 실측 ~235 ms)에 온 `ABORT`·종료·다음 명령이 이 펄스를
        # 못 본다 (DevNote 11.96).  지우는 것은 태스크가 내림을 마친 뒤다.
        # ⚠️ 시작 전에 끊긴 태스크는 한 줄도 안 돈다 -- 끊은 쪽이 선을 내린다.
        self._trigout_timers[tag] = self.app.spawn(
            self._do_trigout_pulse(msg.src, word, tag, ctrl, ms, rest))
        return Reply.noop()

    def _rest_left_by_shopen(self, word: str, be, tag: str) -> None:  # noqa: ANN001
        """`CnTRIGOUT` 이 끊은 `SHOPEN` 이 올려 둔 **다른** 컨트롤러를 내린다 (핸들을 적는다).

        ⭐ 핸들을 `_trigout_timers[tag]` 에 적는다 -- 끊는 쪽이 선을 책임지는 규약을
        그대로 탄다: `release_pulse`(ABORT·종료)는 이 내림을 끊고 **스스로** 내리고, 그
        컨트롤러의 다음 `CnTRIGOUT` · `SHOPEN`/`SHCLOSE` 는 끊고 자기 값을 쓴다.
        ⚠️ 이미 산 핸들이 있으면 그 주인이 선을 책임지므로 건드리지 않는다 (지금 흐름에서는
        안 생긴다 -- `SHOPEN` 이 셔터를 모는 쪽의 `CnTRIGOUT` 을 다 끊고 시작한다).
        """
        c = getattr(be, 'ctrls', {}).get(tag)
        timers = self._trigout_timers
        if c is None or timers is None:
            return
        live = timers.get(tag)
        if live is not None and not live.done():
            return
        timers[tag] = self.app.spawn(self._do_rest_left(word, tag, c))

    async def _do_rest_left(self, word: str, tag: str, ctrl) -> None:  # noqa: ANN001
        """`_rest_left_by_shopen` 의 태스크 -- 적용 한 번.  ⚠️ 와이어 답은 없다 (명령의 답은
        그 명령의 컨트롤러 몫이다) -- 실패는 로그 오류 한 줄이다."""
        try:
            await trigout_core.rest_line(ctrl, self._TRIGOUT_REST)
        except Exception as exc:  # noqa: BLE001 -- 한 명령이 노드를 못 죽인다
            log.error('%s: could not rest the %s trigger line left by SHOPEN -- %s',
                      word, tag, exc,
                      extra={'detail': '⚠️ HIGH(셔터가 열린 채)로 남을 수 있다 -- '
                                       'SHCLOSE 로 다시 내릴 것'})
        finally:
            # ⛔ **자기 핸들일 때만 지운다** (`_do_trigout_pulse` 와 같은 규칙).
            timers = self._trigout_timers or {}
            if timers.get(tag) is asyncio.current_task():
                timers.pop(tag, None)

    async def _do_trigout_rest(self, dest: str, word: str,  # noqa: ANN001
                               ctrl, rest: tuple) -> None:
        """선을 쉬는 상태로 -- 적용 한 번.  ⚠️ 핸들을 안 적는다 -- 종료가 이 한 적용을
        못 본다 (`release_pulse` 의 *"남은 창"*)."""
        self._warn_if_acquiring(word)
        try:
            await trigout_core.rest_line(ctrl, rest)
        except Exception as exc:  # noqa: BLE001 -- 한 명령이 노드를 못 죽인다
            self._emit_failed(dest, word, 'resting the trigger line', exc,
                              '⚠️ 선이 HIGH 로 남았을 수 있다 -- %s 0 을 다시 칠 것'
                              % word)
            return
        self.emit.done(dest, word, 'TrigOut=Low Ctrl=%s' % ctrl.tag)

    async def _do_trigout_pulse(self, dest: str, word: str,  # noqa: ANN001
                                tag: str, ctrl, ms: float,
                                rest: tuple) -> None:
        """`<ms>` 동안 HIGH -- 올림 한 적용, 시한 뒤 내림 한 적용.

        ⭐ 핸들은 `_trigout_cmd` 가 `spawn` 하며 적었고(올림 앞) **내림이 끝난 뒤
        `finally` 에서** 지운다 -- 올림 · 대기 · 내림 어느 창에 온 `ABORT`·종료·다음
        명령도 이 펄스를 끊고 선을 책임진다.  ⛔ 종전에는 올림 **뒤에** 적고 내림
        **앞에서** 지워, 그 두 창(각 ~235 ms)에 온 종료가 핸들을 못 보고 태스크 취소로
        선을 HIGH 로 남겼다.  시한은 올림이 끝난 뒤부터 잰다.
        """
        try:
            self._warn_if_acquiring(word)
            try:
                await trigout_core.raise_line(ctrl)
            except Exception as exc:  # noqa: BLE001
                # ⛔ **실패해도 내려 본다** (DevNote 11.96) -- `APPLYSYSTEM` 이 나간 뒤의
                # 시한 초과면 선은 이미 HIGH 인데, 핸들은 아래 `finally` 가 지워
                # `ABORT`·종료도 못 찾는다.  내림 실패는 로그 오류 한 줄 -- 답은 올림 실패다.
                await self._rest_each(word, [(ctrl, rest)],
                                      '올림이 실패한 뒤의 내림도 실패했다 -- ⚠️ 선이 HIGH '
                                      '로 남았을 수 있다.  %s 0 을 다시 칠 것' % word)
                self._emit_failed(dest, word, 'raising the trigger line', exc)
                return
            try:
                await asyncio.sleep(self.cfg.scaled(ms / 1000.0))
            except asyncio.CancelledError:
                # ⭐ 끊은 쪽이 선을 책임진다 -- 다음 명령 · `SHOPEN`/`SHCLOSE` ·
                # `release_pulse`(ABORT·종료).
                raise
            try:
                await trigout_core.rest_line(ctrl, rest)
            except Exception as exc:  # noqa: BLE001
                self._emit_failed(dest, word, 'resting the trigger line', exc,
                                  '⚠️ 선이 HIGH 로 남았을 수 있다 -- %s 0 을 다시 '
                                  '칠 것' % word)
                return
            self.emit.done(dest, word,
                           'TrigOut=Low Ctrl=%s Width=%gms' % (ctrl.tag, ms))
        finally:
            # ⛔ **자기 핸들일 때만 지운다** -- 그 사이 새 펄스가 적은 핸들을 지우면 그
            # 펄스를 `ABORT`·종료가 못 찾는다.  끊겼으면 끊은 쪽이 이미 꺼냈다(pop).
            timers = self._trigout_timers or {}
            if timers.get(tag) is asyncio.current_task():
                timers.pop(tag, None)

    async def _rest_each(self, word: str, jobs, detail: str):  # noqa: ANN001, ANN202
        """`(컨트롤러, 쉬는 상태)` 마다 내림 한 적용 -- **하나가 실패해도 나머지를 다 내린다**.

        ⛔ 고리 전체를 한 `try` 로 감싸면 첫 실패에서 멈춰 **뒤 컨트롤러가 HIGH 로 남는다**
        (`shutter_ctrl = both` 에서 MK 가 실패하면 NT 가 열린 채 -- DevNote 11.96).  그래서
        컨트롤러마다 제 `try` 로 내리고, 실패마다 `log.error` 한 줄(`detail` 을 싣는다)을
        남긴 뒤 **다 돌고 나서 첫 실패를 돌려준다** (없으면 `None`).
        ⭐ 답은 부른 쪽이 낸다 -- 올림 실패 뒤의 내림이면 **올림 실패**를(내림 실패가 그것을
        가리지 않는다), 내림 고리면 이 첫 실패를 `_emit_failed` 로.
        ⚠️ `CancelledError` 는 안 잡는다 -- 끊은 쪽이 선을 책임진다.
        """
        first = None
        for ctrl, rest in jobs:
            try:
                await trigout_core.rest_line(ctrl, rest)
            except Exception as exc:  # noqa: BLE001 -- 나머지 컨트롤러도 내린다
                log.error('%s: could not rest the %s trigger line -- %s',
                          word, ctrl.tag, exc, extra={'detail': detail})
                if first is None:
                    first = exc
        return first

    def _warn_if_acquiring(self, word: str) -> None:
        """⏳ **적분 중·독출 중 `APPLYSYSTEM`** 은 아직 실측 전이다 (11.50)."""
        seq = getattr(self.app, 'seq', None)
        if seq is None or not seq.busy or self._warned_busy_apply:
            return
        self._warned_busy_apply = True
        log.warning('%s during an acquisition -- taking shutter control away '
                    'from that frame', word,
                    extra={'detail': 'SHOPEN 은 강제로 열어 두고, SHCLOSE 는 '
                                     '스크립트에 돌려줄 뿐이라 적분 중이면 안 '
                                     '닫힌다.  ⚠️ 적분 중·독출 중 APPLYSYSTEM '
                                     '의 안전성은 아직 실측 전이다 (DevNote '
                                     '11.50)'})

    def cmd_shopen(self, msg: Message, target: Target) -> Reply:
        """SHOPEN <초> [<sourceID> …] -- **셔터를 <초> 동안 연다**.

        ⭐ ICG 의 `TRIGOUT <ms>` 와 **같은 알맹이**(`archon.trigout`)다 -- 올림은
        `LEVEL=1`+`FORCE=1` **한 적용**(`raise_line`), `<초>` 뒤 쉬는 상태로 한 적용
        (`rest_line`).  ⚠️ 눈금이 다르다 -- `SHOPEN` 은 **초**, ICG `TRIGOUT` 은 **밀리초**.
        ⚠️ **에지를 보장하지 않는다** (운영자 확정 2026-09-09) -- 무장(`LEVEL=0`+
        `FORCE=1`)을 앞세우면 그 한 적용 동안 핀이 강제 LOW 라 **노출 중 셔터가 잠깐
        닫힌다**.  그래서 둘을 같이 세운다 -- 스크립트가 이미 셔터를 열어 둔 채였다면
        에지 없이 **그대로** 열린 채다.
        ⚠️ 끝은 `FORCE=0` -- 선을 **타이밍 스크립트에 돌려준다**.
        ⛔ 취득 중에 치면 그 프레임의 셔터를 뺏는다 (경고를 낸다, 막지는 않는다).
        ⛔ **종료 중이면 거절한다** (`Shutting down -- not raised`, `_refuse_if_stopping`)
        -- 종료가 펄스를 내린 뒤라 새로 올리면 내릴 이가 없다 (DevNote 11.96).

        ⭐ **`SHOPEN 0` 은 `SHCLOSE` 와 같다** (운영자 2026-09-12) -- 대기 중인
        타이머를 끊고 **즉시** 닫는다.  ⛔ 펄스 경로로 보내면 닫으라는 명령이
        선을 한 번 올렸다 내려 셔터가 깜빡인다.
        ⭐ **어느 노드로 와도 받는다** -- `>ICS` 든 `>K.IC` 든 `target.ccd` 가
        비면 master 로 떨어진다 (운영자 확인 2026-09-12).
        """
        be, bad = self._archon_backend('SHOPEN')
        if bad is not None:
            return super().cmd_shopen(msg, target)      # 시뮬 -- 기반 판 그대로
        parts = msg.body.split()
        if not parts:
            return Reply.error('SHOPEN', 'Missing exposure time')
        try:
            seconds = float(parts[0])
        except ValueError:
            return Reply.error('SHOPEN', 'Invalid exposure time: %s' % parts[0])
        # ⛔ `nan`·`inf` 도 거절한다 -- 셔터가 강제로 열린 채 안 닫힌다 (위 `CnTRIGOUT` 과 같다).
        if not math.isfinite(seconds) or seconds < 0:
            return Reply.error('SHOPEN', 'Invalid exposure time: %s' % parts[0])
        if seconds > 0:
            # ⛔ 종료 중이면 올리지 않는다 -- 타이머를 만지기 **전에** 거절한다.
            refused = self._refuse_if_stopping('SHOPEN')
            if refused is not None:
                return refused
        ctrls = self._shutter_ctrls(be)
        if not ctrls:
            return Reply.error('SHOPEN', 'No shutter-driving controller')
        source = parts[1] if len(parts) > 1 else msg.src
        ccd = target.ccd or self.cfg.node.master
        self._cancel_shutter_timer()
        self._take_from_trigout('SHOPEN', be)
        if seconds == 0:
            # ⭐ **`SHOPEN 0` 은 `SHCLOSE` 와 같다** (운영자 2026-09-12) --
            # *"시간이 남았어도 즉시 닫는다"*.  ICG `TRIGOUT 0` 과 같은 자리다.
            # ⛔ 펄스 경로로 보내면 `raise_line` 이 선을 한 번 **올렸다가**
            # 곧 내려서 셔터가 깜빡인다 -- 닫으라는 명령이 여는 에지를 만든다.
            self.app.spawn(self._do_shutter_close(source, ccd, ctrls))
            return Reply.noop()
        # ⭐ **핸들은 여기서 적는다** -- 올림 앞이다 (DevNote 11.96).  태스크 안에서
        # 올림 뒤에 적으면 그 창에 온 `ABORT`·종료·`SHCLOSE` 가 이 펄스를 못 봐서 선이
        # HIGH(셔터가 열린 채)로 남는다.  지우는 것은 태스크가 내림을 마친 뒤다.
        # ⚠️ 시작 전에 끊긴 태스크는 한 줄도 안 돈다.
        self._shutter_timer = self.app.spawn(
            self._do_shutter_pulse(source, ccd, seconds, ctrls))
        return Reply.noop()

    def _take_from_trigout(self, word: str, be) -> None:  # noqa: ANN001
        """셔터를 모는 컨트롤러의 **대기 중 `CnTRIGOUT` 펄스를 끊는다** (DevNote 11.96).

        ⛔ 안 끊으면 `CnTRIGOUT` 의 옛 타이머가 나중에 깨어나 `SHOPEN`/`SHCLOSE` 가
        세운 선을 내린다 -- 예: `C1TRIGOUT 5000` 뒤 `SHOPEN 20` 이면 5초 뒤 MK 선이
        `FORCE=0` 으로 돌아가 20초 열겠다던 셔터가 도중에 스크립트로 넘어간다.
        `_trigout_cmd` 가 `SHOPEN` 타이머를 끊는 것과 짝이다.  선은 부른 명령이 책임진다.
        """
        for tag in list(self._trigout_timers or {}):
            if be.acfg.drives_shutter(tag) and self._cancel_trigout_timer(tag):
                log.warning('%s took the line from a pending CnTRIGOUT pulse (%s)',
                            word, tag,
                            extra={'detail': '셔터를 모는 컨트롤러다 -- '
                                             'CnTRIGOUT 의 남은 시간은 버려진다'})

    async def _do_shutter_pulse(self, dest: str, ccd: str,  # noqa: ANN001
                                seconds: float, ctrls) -> None:
        """`<초>` 동안 연다.

        ⭐ 핸들은 `cmd_shopen` 이 `spawn` 하며 적었고(올림 앞) **내림이 끝난 뒤 `finally`
        에서** 지운다 -- 올림 · 대기 · 내림 어느 창에 온 `ABORT`·종료·`SHCLOSE`·
        `CnTRIGOUT` 도 이 펄스를 끊고 선을 책임진다 (`_do_trigout_pulse` 와 같은 규칙).
        """
        try:
            self._warn_if_acquiring('SHOPEN')
            #: 올렸거나 **올리려 한** 컨트롤러 -- 올림이 실패하면 이것들을 내린다.
            tried = []
            try:
                for c in ctrls:
                    tried.append(c)
                    await trigout_core.raise_line(c)
            except Exception as exc:  # noqa: BLE001 -- 한 명령이 노드를 못 죽인다
                # ⛔ **올린 것과 올리려 한 것을 다 내린다** (DevNote 11.96) -- `shutter_ctrl
                # = both` 에서 MK 는 올랐는데 NT 가 실패하거나, `APPLYSYSTEM` 이 나간 뒤
                # 시한을 넘기면 선이 HIGH 인데 핸들은 아래 `finally` 가 지워 `ABORT`·종료도
                # 못 찾는다 (셔터가 강제로 열린 채).  내림 실패는 로그 오류 줄 -- 답은 올림 실패다.
                await self._rest_each('SHOPEN',
                                      [(c, self._TRIGOUT_REST) for c in tried],
                                      '올림이 실패한 뒤의 내림도 실패했다 -- ⚠️ 셔터가 '
                                      '열린 채 남았을 수 있다.  SHCLOSE 를 다시 칠 것')
                self._emit_failed(dest, 'SHOPEN', 'raising the shutter line', exc)
                return
            self.emit.ic_shutter_open(dest, ccd)
            try:
                await asyncio.sleep(self.cfg.scaled(seconds))
            except asyncio.CancelledError:
                # ⭐ 끊은 쪽이 선을 책임진다 -- `SHCLOSE` · 다음 `SHOPEN` · `CnTRIGOUT` ·
                # `release_pulse`(ABORT·종료).
                raise
            # ⭐ **넘겨준다** -- `FORCE=0` 으로 선을 스크립트에 돌려준다 (운영자 확정
            # 2026-09-09).  적분 중이면 `<초>` 가 지나도 안 닫히고 노출이 `NoIntMS` 에
            # 닫는다 (`trigout.rest_line`).  ⛔ 컨트롤러마다 따로 내린다 -- 하나가 실패해도
            # 나머지는 닫고, 다 돈 뒤에 첫 실패를 답한다 (`_rest_each`).
            failed = await self._rest_each('SHCLOSE',
                                           [(c, self._TRIGOUT_REST) for c in ctrls],
                                           '⚠️ 이 컨트롤러는 셔터가 열린 채 남았을 수 있다 '
                                           '-- 나머지는 내려 본 뒤 첫 실패를 답한다')
            if failed is not None:
                self._emit_failed(dest, 'SHCLOSE', 'closing the shutter line', failed,
                                  '⚠️ 셔터가 열린 채 남았을 수 있다 -- SHCLOSE 를 다시 '
                                  '칠 것')
                return
            self.emit.ic_shutter_closed(dest, ccd)
        finally:
            # ⛔ **자기 핸들일 때만 지운다** -- 새 `SHOPEN` 이 적은 핸들을 지우면 그 펄스를
            # `ABORT`·종료가 못 찾는다.  끊겼으면 끊은 쪽이 이미 비웠다.
            if self._shutter_timer is asyncio.current_task():
                self._shutter_timer = None

    def cmd_shclose(self, msg: Message, target: Target) -> Reply:
        """SHCLOSE -- 셔터를 닫고 **타이밍 스크립트에 돌려준다** (적용 한 번).

        `LEVEL=0` + `FORCE=0` 을 한 `APPLYSYSTEM` 으로 쓴다 -- ICG 의
        `TRIGOUT 0` 과 같은 자리이고 끝값만 다르다 (운영자 2026-09-09).
        ⛔ **`SHOPEN` 의 타이머도 끊는다** -- 안 끊으면 옛 타이머가 나중에
        깨어나 그때 세워져 있던 선을 내린다.  셔터를 모는 컨트롤러의 `CnTRIGOUT`
        펄스도 같은 이유로 끊는다 (`_take_from_trigout`).
        ⚠️ **적분 중이면 셔터가 닫힌 채로 남지 않는다** -- 선을 스크립트에
        돌려주므로 그 노출의 셔터 제어가 이어진다 (노출 종료 `NoIntMS` 에 닫힌다).
        ⛔ **적분을 끊는 것은 `ABORT` 다** -- `ArchonBackend.abort_now()`(`Exposures=0`
        -> `RESETTIMING`)로 코어를 되돌리면 `RESET` 상태가 6비트를 0 으로 몰아 셔터가
        닫힌다.  `STOP` 은 적분을 안 끊는다(현재 프레임을 마친다).
        `ArchonBackend.close_shutter()` 의 `FORCE=1`+`LEVEL=0` 은 호스트 카운트다운이
        적분보다 먼저 끝났을 때 **빛만** 끊는 자리다.
        """
        be, bad = self._archon_backend('SHCLOSE')
        if bad is not None:
            return super().cmd_shclose(msg, target)     # 시뮬 -- 기반 판 그대로
        ctrls = self._shutter_ctrls(be)
        if not ctrls:
            return Reply.error('SHCLOSE', 'No shutter-driving controller')
        self._cancel_shutter_timer()
        self._take_from_trigout('SHCLOSE', be)
        ccd = target.ccd or self.cfg.node.master
        self.app.spawn(self._do_shutter_close(msg.src, ccd, ctrls))
        return Reply.noop()

    async def _do_shutter_close(self, dest: str, ccd: str, ctrls) -> None:  # noqa: ANN001
        """`SHCLOSE`·`SHOPEN 0` 의 내림 -- 적용 한 번씩.  ⚠️ 핸들을 안 적는다 -- 종료가
        이 내림을 못 본다 (`release_pulse` 의 *"남은 창"*)."""
        self._warn_if_acquiring('SHCLOSE')
        # ⭐ **넘겨준다** -- 적분 중이면 `NoIntMS` 에서 닫힌다.  ⛔ 컨트롤러마다 따로
        # 내린다 -- 하나가 실패해도 나머지는 닫고, 다 돈 뒤에 첫 실패를 답한다.
        failed = await self._rest_each('SHCLOSE',
                                       [(c, self._TRIGOUT_REST) for c in ctrls],
                                       '⚠️ 이 컨트롤러는 셔터가 열린 채 남았을 수 있다 '
                                       '-- 나머지는 내려 본 뒤 첫 실패를 답한다')
        if failed is not None:
            self._emit_failed(dest, 'SHCLOSE', 'closing the shutter line', failed,
                              '⚠️ 셔터가 열린 채 남았을 수 있다 -- SHCLOSE 를 다시 칠 것')
            return
        self.emit.ic_shutter_closed(dest, ccd)
        self.emit.done(dest, 'SHCLOSE',
                       'Shutter=Closed Integration Remaining=0 sec.')

    def cmd_ccdflush(self, msg: Message, target: Target) -> Reply:
        """CCDFLUSH [MK|NT|ALL] -- 유휴 CCD 를 FlushFrame 한 바퀴로 비운다.

        `backend.flush_ccd()` -> `controller.flush_now(reset=False)`: `Exposures=0` 을
        `LOADPARAMS` 로 걸어 코어가 `FlushFrame`(science ACF R2610+: Prep + Flush)을 한
        번 돌게 한다 -- 설정 메모리의 `FirstFlush` 가 1 이 아니면(ACF 초기값 0 이거나
        `[archon] ccdflush_first` 가 0·2 이상) 잠시 1 로 올렸다가 **읽어 둔 값 그대로**
        되돌린다 -- 오류·취소에도 (`finally`, DevNote 11.33).  `EveryFlush`
        (`ccdflush_every`)는 유휴 경로가 안 닿아 건드리지 않는다.  프레임은 안 만든다.

        ⚠️ **ACF 줄 번호를 알아야 한다** -- `WCONFIG` 는 줄 번호로 쓰는데 그 번호는
        `prepare()`(첫 `GO`)의 ACF 파싱에서 온다.  아직 파싱 전이면 `flush_now()` 가
        *"ACF has no FirstFlush parameter"* 라고 하는데 그것은 **원인이 아니라 증상**
        이다 -- 여기서 먼저 걸러 바른 문구를 낸다.
        """
        be, bad = self._archon_backend('CCDFLUSH')
        if bad is not None:
            return bad
        tags, bad = self._tags_arg('CCDFLUSH', msg.body, be)
        if bad is not None:
            return bad
        bad = self._refuse_if_busy('CCDFLUSH')
        if bad is not None:
            return bad
        ctrls = getattr(be, 'ctrls', {})
        picked = list(be.tags) if tags == 'ALL' else [tags]
        cold = [t for t in picked if not getattr(ctrls.get(t), 'config', None)]
        if cold:
            return Reply.error('CCDFLUSH', 'Failed: ACF not loaded on %s in this '
                               'session -- run GO once first' % ','.join(cold))
        log.info('CCDFLUSH %s -- requested by %s', tags, msg.src)
        return self._start_op(msg.src, 'CCDFLUSH', self._flush_work(be, tags))

    async def _flush_work(self, be, tags) -> str:  # noqa: ANN001
        done = await be.flush_ccd(tags)
        return 'Flushed=%s' % ','.join(done)

    # -- CCDPOWON / CCDPOWOFF ----------------------------------------------------

    def cmd_ccdpowon(self, msg: Message, target: Target) -> Reply:
        """CCDPOWON [MK|NT|ALL] -- `POWERON`.  ⚠️ 응답은 `POWER=4` 확인(실측 ~1초) 뒤에
        온다 -- 확인은 `[archon] poweron_wait` 와 무관하게 한다 (`controller.power_on`;
        `telemetry = false` 면 확인 왕복도 안 건다).  `poweron_wait` 는 그 위의 **추가**
        대기이고 ICS 기본은 `0` 이다 (운영자 확정 2026-09-10) -- 값을 적으면 응답이 그만큼
        더 늦다.

        ⚠️ 실기는 **이 세션에서 `APPLYALL` 이 없었으면** `?xx` 로 거부한다 (매뉴얼
        p.51, DevNote 10.2) -- 기동 뒤 아직 `GO` 가 없었다면 `GO` 한 번(첫 `prepare()` 의
        `APPLYALL`)이 먼저다.  ⛔ ICS 가 떠 있는 동안의 REBOOT·전원 재투입 뒤에는 `GO`
        로도 안 된다 -- `prepare()` 는 ACF 를 **세션에 한 번만** 민다(`acf_applied`).
        그때는 ICS 를 다시 띄운다.  그 진단 문구는 `controller.power_on()` 이 낸다.
        """
        return self._power(msg, True, 'CCDPOWON')

    def cmd_ccdpowoff(self, msg: Message, target: Target) -> Reply:
        """CCDPOWOFF [MK|NT|ALL] -- `POWEROFF`.  다음 `GO` 의 `prepare()` 가 다시 켠다."""
        return self._power(msg, False, 'CCDPOWOFF')

    def _power(self, msg: Message, on: bool, cmdword: str) -> Reply:
        be, bad = self._archon_backend(cmdword)
        if bad is not None:
            return bad
        tags, bad = self._tags_arg(cmdword, msg.body, be)
        if bad is not None:
            return bad
        bad = self._refuse_if_busy(cmdword)
        if bad is not None:
            return bad
        log.info('%s %s -- requested by %s', cmdword, tags, msg.src)
        return self._start_op(msg.src, cmdword, self._power_work(be, on, tags))

    async def _power_work(self, be, on: bool, tags) -> str:  # noqa: ANN001
        """`power_ccd()` 뒤 **상태로 판정한다** -- `controller.power_off()` 는 실패를
        올리지 않고 로그만 남기므로(`finally` 자리용), 그대로 `DONE` 을 내면 전원이
        살아 있는데 *"OFF"* 라고 답하게 된다."""
        done = await be.power_ccd(on, tags)
        ctrls = getattr(be, 'ctrls', {})
        wrong = [t for t in done
                 if bool(getattr(ctrls.get(t), 'powered', on)) != on]
        word = 'ON' if on else 'OFF'
        if wrong:
            raise _OpError('Failed: POWER%s not confirmed on %s (see log)'
                           % (word, ','.join(wrong)))
        return 'Power=%s Controllers=%s' % (word, ','.join(done))

    # -- ARCHON 바이패스 ---------------------------------------------------------

    def cmd_archon(self, msg: Message, target: Target) -> Reply:
        """ARCHON <MK|NT> <명령 원문…> -- 한 컨트롤러에 원문을 보내고 응답 원문을 답한다.

        ⚠️ **위생 검사 없음** -- 운영자 도구다 (2026-09-05 지시).  `RESETTIMING` ·
        `WCONFIG…` 같은 원문도 그대로 나간다.  ⭐ **제한 없음** (운영자 2026-09-05) --
        취득 중·다른 조작 중에도 받고 `GO` 도 막지 않는다 (`_op_inflight` 를 잡지 않는다).

        응답이 길면(`STATUS` ~2 KB) `ARCHON_REPLY_MAX` 에서 잘라 꼬리를 붙이고 **전문은
        `log.info` 로** 남긴다 -- 한 메시지 상한 `MAX_LEN`(2048) 을 넘기면 받는 쪽이
        통째로 버린다 (`impv2.parse`).
        """
        be, bad = self._archon_backend('ARCHON')
        if bad is not None:
            return bad
        usage = 'usage: ARCHON <%s> <command>' % '|'.join(be.tags)
        head, _, text = msg.body.strip().partition(' ')
        tag, text = head.upper(), text.strip()
        if tag not in be.tags or not text:
            return Reply.error('ARCHON', usage)
        log.info('ARCHON %s %r -- requested by %s', tag, text, msg.src,
                 extra={'detail': '바이패스 -- 위생 검사도 제한도 없다'})
        self.app.spawn(self._finish_op(msg.src, 'ARCHON',
                                       self._archon_work(be, tag, text), track=False))
        return Reply.noop()

    async def _archon_work(self, be, tag: str, text: str) -> str:  # noqa: ANN001
        try:
            reply = await be.raw_command(tag, text)
        except ArchonError as exc:
            if exc.reply_error:
                # 컨트롤러가 `?xx` 로 거부했다 -- 내 명령이 틀린 것이라 `DONE` 이 아니다.
                log.warning('ARCHON %s: the controller rejected it -- %r (%s)',
                            tag, text, exc)
                raise _OpError('%s rejected: %s' % (tag, wire_text(text))) from exc
            log.error('ARCHON %s %r failed -- %s', tag, text, exc)
            raise _OpError('%s Failed: %s' % (tag, _fail_text(exc))) from exc
        except (BackendError, TimeoutError, OSError) as exc:
            log.error('ARCHON %s %r failed -- %s', tag, text, exc)
            raise _OpError('%s Failed: %s' % (tag, _fail_text(exc))) from exc
        body = wire_text(reply)
        # ⭐ **전문은 여기에** -- 와이어는 잘려도 로그는 안 잘린다.
        log.info('ARCHON %s %r -> %d bytes: %s', tag, text, len(body),
                 body or '(empty reply)')
        if len(body) > ARCHON_REPLY_MAX:
            kept = body[:ARCHON_REPLY_MAX].rstrip()
            body = '%s ...(+%d bytes truncated, see log)' % (kept, len(body) - len(kept))
        return '%s %s' % (tag, body or '<empty reply>')


def _is_reply_to(msg, word: str) -> bool:  # noqa: ANN001
    """`msg` 가 `word` 명령에 대한 **답**(`DONE:`/`ERROR:`/`FATAL:`)인가.

    ⛔ **원문 부분 문자열로 보지 않는다** (2026-09-15 벤치): `HKDATA` 답 본문에
    `VACGAUGE=ON` 이 실리므로 *"`VACGAUGE` 가 원문에 있나"* 로 보면 **HK 답마다
    게이지 데드맨이 풀리고** `vacuum gauge reply` 가 찍힌다 -- 진짜 `VACGAUGE` 가
    답을 못 받았을 때 그 사실이 묻힌다.  커맨드워드와 타입으로 가른다.
    `EXEC:`(진행 중)는 답이 아니다.
    """
    return (msg.mtype in ('DONE', 'ERROR', 'FATAL')
            and (msg.cmdword or '').upper() == word.upper())


class IcsArchon(IcsSim):
    """실기 ICS -- `ics_sim` 본체 + Archon 백엔드."""

    def __init__(self, cfg, acfg) -> None:  # noqa: ANN001
        # 운영자 명령 넷의 커맨드워드를 emitter 어휘에 -- 첫 응답 전이면 어디든
        # 되지만, icg 와 같은 자리(생성자 첫 줄)에 둔다.
        extend_vocabulary()
        # **`super().__init__()` 앞에 등록한다** -- 그 안에서 `make_backend()`
        # 가 불리므로, 늦으면 이 폴더의 스텁이 만들어진다.
        register_backend('archon', lambda c: ArchonBackend(c, acfg))
        if cfg.hardware.backend != 'archon':
            log.warning('ics_archon started with [hardware] backend=%r -- it '
                        'will not touch the Archon controllers',
                        cfg.hardware.backend,
                        extra={'detail': '실기로 돌리려면 archon 으로 두거나 '
                                         '--backend archon 을 주라'})
        self.acfg = acfg
        #: ⛔ **종료가 시작됐다** -- `stop()` 의 첫 줄이 세운다 (되내리지 않는다).  명령
        #: 처리부가 이것을 보고 선을 올리는 `SHOPEN <초>`·`CnTRIGOUT <ms>` 를 거절한다
        #: (`IcsDispatcher._refuse_if_stopping`, DevNote 11.96).
        self.stopping = False
        #: `fetch_icg_hk()` 가 기다리는 Future -- `_on_hkdata`(답) · `_on_hk_refused`
        #: (`HKDATA` 거절)가 푼다.
        self._hk_future: asyncio.Future | None = None
        #: 마지막으로 받은 `HK`/`HKDATA` 답의 원문 (진단용 -- 화면에는 전송층의 와이어
        #: 줄로 보이고, 이 값을 따로 찍는 곳은 없다).
        self.hk_wire: dict | None = None
        super().__init__(cfg)

        # `ICSBUILD` -- 이 프로그램의 것으로.
        self.state.ics_build = build_id()

        # -- 진공게이지 (운영자 지시 2026-09-04) -------------------------
        #: 노출 앞뒤로 ICG 에 `VACGAUGE` 를 보낸다.
        self.gauge = GaugeControl(
            acfg.icg_node, acfg.gauge_reenable_after, self.spawn,
            self.emit.emit_req, acfg.gauge_reply_timeout,
            enabled=acfg.gauge_off_on_exposure,
            # ⚠️ **`time_scale` 로 접는다** -- 이 대기는 저장소의 다른 타이밍
            # 값(`write_delay` 등)과 같은 성격이라 시뮬·시험에서 함께 줄어야
            # 한다.  안 접으면 `time_scale = 0.02` 짜리 시험에서 5초가 그대로
            # 흘러 **프레임보다 대기가 길어진다** (실제로 시험 하나가 그것으로
            # 깨졌다).  실기는 `time_scale = 1.0` 이라 값 그대로다.
            settle_after=cfg.scaled(acfg.gauge_settle_after),
            # ⛔ **취득 중이면 무조건 안 켠다** (운영자 지시 2026-09-04) --
            # 만료 시점에 이것을 다시 본다.  상태 확인만으로는 못 막는 길이
            # 있었다 (취득 중 `GO` 거절이 타이머를 걸던 자리).
            is_busy=lambda: bool(getattr(self.seq, 'busy', False)))
        # ⭐ **백엔드가 그 안정화 대기를 볼 수 있게 건네준다** -- 프레임의 첫
        # 백엔드 호출(`initialize()`)에서 기다려야 노출 전 flush(`ccdflush_first`/
        # `ccdflush_every` 의 `Prep`+`Flush`, 게이지를 끈 GO 의 첫 장 flush)가 게이지가
        # 꺼진 뒤에 돈다 (운영자 지시 2026-09-04 · 2026-09-15).  ⚠️ 명령 처리부
        # 에서는 못 기다린다 -- `cmd_go` 는 `Reply` 를 돌려주는 동기 메서드다.
        backend = getattr(self, 'backend', None)
        if backend is not None:
            backend.gauge = self.gauge
        #: science 독출 앞뒤로 guide 노출을 막고 푼다 (`GUIEXPCTRL`).
        self.expenable = ExpEnableControl(
            acfg.icg_node, acfg.guiexp_lead, self.spawn,
            self.emit.emit_req, acfg.gauge_reply_timeout,
            enabled=acfg.guiexpctrl)
        #: `GO` 를 가로채는 명령 처리부로 갈아 끼운다.
        self.dispatch = IcsDispatcher(self)
        #: 취득 종료를 지켜보는 태스크 (`start()` 가 띄운다).
        self._gauge_task = None

        # -- TCS 시각 비교 (운영자 지시 2026-09-04) ----------------------
        #: TC 시계와 우리 시계의 어긋남.  `TCSQDATE` 하나로 잰다.
        #: ⭐ `ics_sim` 은 **0줄**이다 -- relay 인스턴스의 `query()` 만 감싼다.
        self.tcs_clock = ClockWatch('TCS', acfg.tcs_clock_warn)
        if acfg.tcs_clock_warn > 0:
            watch_tc_queries(self.telem, self.tcs_clock)

        # -- XIS 허브 확인 (운영자 지시 2026-09-04) --------------------
        #: ⭐ **허브가 없으면 기동을 멈춘다** -- ICG 와 주고받는 명령이
        #: 조용히 사라지는 것을 자료 찍기 전에 막는다 (`xischeck.py`).
        self.xis_gate = XisGate(
            cfg.node.ics_id, timeout=acfg.xis_ping_timeout,
            tries=acfg.xis_ping_tries, required=acfg.require_xis,
            xis_host=cfg.transport.xis_host)

        #: 돌고 있는 텔레메트리 감시 (`start()` 가 띄우고 `stop()` 이 세운다).
        self._monitors: list[TelemetryMonitor] = []
        #: 그 태스크 -- 종료에서 **실제로 기다리려면** 참조가 필요하다.
        #: (`IcsSim` 도 참조를 들고 있지만 그쪽은 `super().stop()` 에서
        #: 취소할 뿐이라, 우리가 원하는 "먼저 곱게 세운다" 를 못 한다.)
        self._monitor_tasks: list = []

        # `CTRL1CFG`/`CTRL2CFG` -- ini 가 비었으면 적용 ACF 경로에서.
        fill_controller_cfg_names(cfg, acfg)


    def _on_hkdata(self, msg: Message, target: Target) -> None:  # noqa: ANN001
        """`ICG>ICS DONE: HKDATA …` 를 받는다 (DevNote 11.12 F1 이 없다던 경로).

        ⭐ **받아 적기만 한다 -- 답하지 않는다** (출력도 따로 안 한다 -- 아래 주석).
        보고에 답하면 두 노드가 서로 보고를 주고받는 고리가 생긴다 (`register_report`
        주석).

        ⭐ **`GO` 의 질의가 기다리고 있으면 그 Future 를 푼다** (`fetch_icg_hk`,
        2026-09-15) -- 그것이 헤더 5.6절 카드의 원천이다.  기다리는 이가 없으면
        (운영자가 콘솔에서 친 `hkdata`) 마지막 응답만 남긴다.
        ⚠️ 응답이 아닌 본문(*"no fresh HK sample yet"*)은 `parse_hkdata` 가 `None`
        으로 접는다 -- 그때는 Future 를 **안 푼다** (F9: 값 없음으로 굳히지 않고
        시한까지 기다린다.  ICG 가 곧 다시 답할 수 있다).
        ⚠️ `ERROR:`/`FATAL:` 답은 여기로 안 온다 -- `_on_hk_refused` 가 받는다.
        """
        body = (msg.payload or '').strip()
        self.hk_wire = {'when': utcnow(), 'src': msg.src, 'body': body}
        # ⛔ **`print()` 로 내지 않는다** (벤치 2026-09-15: `hk` 뒤 프롬프트가 사라졌다).
        # 맨 `print` 는 `PromptSafeStream` 을 안 지나 입력 줄을 지우고 프롬프트를
        # 다시 안 그린다.  그리고 같은 본문이 이미 와이어 줄(`ICG>ICS DONE: HKDATA …`,
        # 전송층이 찍는다)로 화면에 있으므로 여기서는 **DEBUG 한 줄**만 남긴다 --
        # 종전엔 셋(와이어 · `ICG HK received` · `HKDATA <-`)이 같은 줄이었다.
        log.debug('ICG HK received -- %s', body)
        parsed = hkwire.parse_hkdata(body)
        fut = self._hk_future
        if parsed is not None and fut is not None and not fut.done():
            fut.set_result(parsed)

    def _on_hk_refused(self, msg: Message, target: Target) -> None:  # noqa: ANN001
        """`ICG>ICS ERROR:`/`FATAL: HKDATA …`(또는 `HK`)를 받는다.  `HKDATA` 거절이면
        `GO` 의 기다리는 질의를 **곧바로** 끝낸다.

        ⛔ 종전에는 `DONE` 에만 조치를 걸어 두어서(DevNote 11.96), ICG 가 거절하면
        `GO` 마다 `hk_query_timeout` 을 헛기다렸고, 그 뒤 *"ICG 가 떠 있는지 · XIS …"*
        라는 **틀린 진단**을 냈다 -- ICG 는 떠 있고 답도 했다.  ICG 가 이렇게 답하는
        경우는 셋이다: 본문 조립 예외(`Failed: …`) · `HK monitor is not running` ·
        `HKDATA` 를 모르는 구판 ICG 의 `Didn't understand`.
        ⭐ 이 조치가 걸리면 기반의 *"보고 수신 (조치 없음)"* 줄이 더는 안 나온다 -- 그래서
        **원인 본문은 여기 경고에** 싣는다.
        ⚠️ **답하지 않는다** (`register_report` 규약).  F9(비응답 본문이면 시한까지
        기다림)는 `DONE` 의 규칙이라 여기와 무관하다.

        ⭐ **Future 를 푸는 것은 `HKDATA` 거절뿐이다** (DevNote 11.96) -- `GO` 의 질의
        (`fetch_icg_hk`)는 `HKDATA NOW` 를 보내므로 그 거절도 `HKDATA` 로 온다.  `HK`
        거절은 콘솔 `hk`/`hknow` 의 답이라 **경고만** 한다.
        ⚠️ 콘솔 `hkdata` 의 거절은 `GO` 의 질의와 **못 가른다** -- 답에 짝 번호가 없고
        커맨드워드도 같다.  그때 `GO` 가 기다리고 있으면 함께 `None` 으로 끝나 그 취득의
        5.6절 카드가 sentinel 이 된다 (뒤에 `GO` 몫의 `DONE` 이 와도 못 싣는다).  콘솔
        `hkdata` 가 `GO` 의 짧은 대기 창(ICG 답 실측 중앙 7.7 ms)에 겹칠 때만이라 받아들인다.
        ⚠️ **발신자로 거르지 않으므로**(`start()` 주석) 진단은 `icg_node` 가 아니라 실제로
        보낸 이(`msg.src`)를 댄다.
        """
        word = (msg.cmdword or '').upper()
        body = (msg.body or '').strip()
        fut = self._hk_future
        ends_wait = word == 'HKDATA' and fut is not None and not fut.done()
        if ends_wait:
            detail = ('%s 가 거절로 답했다 -- GO 의 HKDATA 질의를 시한 전에 끝낸다.  '
                      '5.6절 카드는 sentinel, 게이지는 추적 상태로 판단하고 노출은 간다'
                      % msg.src)
        else:
            detail = ('%s 가 거절로 답했다 -- 기다리는 GO 의 HKDATA 질의에는 안 닿는다 '
                      '(콘솔 질의의 답이거나 시한이 지난 답)' % msg.src)
        log.warning('%s refused %s (%s) -- %s', msg.src, msg.cmdword, msg.mtype,
                    body or '(no text)', extra={'detail': detail})
        if ends_wait:
            fut.set_result(None)

    async def fetch_icg_hk(self) -> dict | None:
        """`ICS>ICG HKDATA NOW` 를 보내고 답(소문자 키 dict)을 기다린다.

        ⭐ **왜 `NOW` 인가** -- 답의 `VACGAUGE` 로 게이지를 끌지 정하는데, 주기값의
        낱말은 방금 바뀐 것을(≤ `[hk] interval`) 모른다.  `NOW` 는 ICG 가 바퀴를 지금
        돌려 답하므로 낱말도 값도 **지금** 것이다 (실측 중앙 7.7 ms, DevNote 11.55).
        ⚠️ 시한(`[archon] hk_query_timeout`, `time_scale` 로 접는다) 안에 답이 없으면
        `None` -- 카드는 sentinel, 게이지는 추적 상태로 판단, **노출은 간다**.  관측을
        HK 하나 때문에 막지 않는다 (F3: 데드맨은 여기 한 곳).  ICG 가 `ERROR`/`FATAL:
        HKDATA` 로 답하면 시한을 안 기다리고 **곧바로** `None` 이다 (`_on_hk_refused` --
        `HK` 거절은 이 대기에 안 닿는다).
        ⛔ 한 번에 하나만 기다린다 -- 겹치면 앞 것을 `None` 으로 끝낸다.
        """
        dest = self.acfg.icg_node
        if not dest:
            return None
        loop = asyncio.get_running_loop()
        prev = self._hk_future
        if prev is not None and not prev.done():
            prev.set_result(None)
        fut: asyncio.Future = loop.create_future()
        self._hk_future = fut
        timeout = self.cfg.scaled(self.acfg.hk_query_timeout)
        try:
            self.emit.emit_req(dest, 'HKDATA', 'NOW')
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            log.warning('no HKDATA reply from %s within %.2fs', dest, timeout,
                        extra={'detail': 'ICG 가 떠 있는지 · 허브(XIS)가 붙어 '
                                         '있는지 · [archon] icg_node 를 볼 것.  '
                                         '5.6절 카드는 sentinel, 게이지는 추적 '
                                         '상태로 판단하고 노출은 간다'})
            return None
        finally:
            if self._hk_future is fut:
                self._hk_future = None

    async def _hk_before_exposure(self) -> dict | None:
        """`GO` 마다 한 번 -- HKDATA 를 받고 그 낱말로 게이지를 끈다 (운영자 2026-09-15)."""
        hk = await self.fetch_icg_hk()
        word = (hk or {}).get('vacgauge')
        gauge = getattr(self, 'gauge', None)
        if gauge is not None:
            gauge.before_exposure(word)
        backend = getattr(self, 'backend', None)
        if backend is not None and hasattr(backend, 'set_hk'):
            backend.set_hk(hk)
        return hk

    def begin_go(self) -> None:
        """`GO` 가 받아들여진 직후 -- HK 질의 + 게이지 판단 태스크를 띄우고 백엔드에 건다.

        `--backend sim` 에도 뜬다(게이지 배선은 백엔드와 무관하다) -- 그때는 기다리는
        `initialize()` 가 없어 답이 오는 대로 끄기만 한다.
        """
        task = self.spawn(self._hk_before_exposure())
        backend = getattr(self, 'backend', None)
        if backend is not None and hasattr(backend, 'hk_task'):
            backend.hk_task = task

    # -- 콘솔 도움말 ------------------------------------------------------

    def console_help(self):  # noqa: ANN201
        """기반 명령 + **실기 ICS 의 CCD 조작 명령**  (운영자 지시 2026-09-07).

        ⛔ 표를 손으로 맞추지 않는다 -- `tests/test_console.py` 가 이 목록과
        `IcsDispatcher` 의 `cmd_*` 를 양방향으로 대조한다.
        """
        return console.extend_help(
            ('CCD 조작 (실기 -- 운영자 명령 넷)', (
                ('ccdflush [MK|NT|ALL]',
                 '유휴 CCD 를 FlushFrame 한 바퀴로 비운다 (프레임 없음)'),
                ('ccdpowon [MK|NT|ALL]',
                 'CCD 전원 ON -- POWER=4 확인(~1초) 뒤에 DONE 이 온다 '
                 '(+ poweron_wait, 기본 0)'),
                ('ccdpowoff [MK|NT|ALL]',
                 'CCD 전원 OFF -- 다음 go 가 다시 켠다'),
                ('c1trigout <ms>',
                 '컨트롤러 1(MK) 의 Trigger Out 을 <ms> 동안 HIGH. 0 이면 '
                 '즉시 내림.  ⚠️ shutter_ctrl 과 무관하게 움직인다'),
                ('c2trigout <ms>',
                 '컨트롤러 2(NT) 의 Trigger Out.  위와 같은 규약'),
                ('archon <MK|NT> <원문>',
                 '컨트롤러 바이패스 -- 응답 원문을 그대로 답한다'),
            )),
            ('House Keeping (ICG 에 묻는다)', (
                ('hk [now]', 'HK 한 줄 -- HKDATA 와 같은 본문'),
                ('hkdata [now]', '헤더용 HK -- 답은 ICG 가 준다.  now 면 ICG 가 한 바퀴 지금'),
                ('hknow', '`hk now` 의 별칭'),
            )),
            ('컨트롤러 텔레메트리 (5.6절 Cn_* 의 와이어 판)', (
                ('c1hkdata [now]',
                 '컨트롤러 1(MK) 온도 10·전압/전류 7 -- now 면 STATUS 를 지금 읽는다'),
                ('c2hkdata [now]', '컨트롤러 2(NT).  같은 규약'),
                ('c1hk|c2hk [now]', '위 둘의 별칭 -- 같은 본문'),
                ('c1hknow|c2hknow', '`c1hk now` · `c2hk now` 의 별칭'),
            )),
            # ⛔ **science 에 없는 기반 명령** (운영자 2026-09-09) -- 점검용 LED
            # 프로젝터 명령 둘.  실기 백엔드의 `flash_led()` 는 `_NOT_YET` 이라
            # 늘 실패했고, 그 자리는 `SHOPEN <초>`(Trigger Out)가 대신한다.
            # ⭐ 감추는 게 아니라 **거절한다** (`IcsDispatcher.UNSUPPORTED`).
            drop=('flashnow', 'ledflash'),
        )

    async def start(self) -> None:
        # ⭐ ICG 의 답을 받는 조치를 건다 (DevNote 11.12 F1).  ⚠️ **발신자로
        # 거르지 않는다** -- ICG 가 내는 답의 `src` 는 `G.IC` 가 아니라 `ICG`
        # 이고(11.15 ①), 어차피 `(mtype, cmdword)` 로만 걸면 충분하다.
        # ⭐ `DONE` 은 받아 적고, `ERROR`/`FATAL` 은 경고한다 -- `HKDATA` 거절이면 `GO`
        # 의 기다리는 질의를 곧바로 끝낸다 (DevNote 11.96 -- 종전엔 `DONE` 만 걸어
        # 거절에도 시한까지 기다렸다).
        for word in ('HK', 'HKDATA'):
            self.register_report('DONE', word, self._on_hkdata)
            self.register_report('ERROR', word, self._on_hk_refused)
            self.register_report('FATAL', word, self._on_hk_refused)
        # ⭐ 게이지 감시는 **백엔드와 무관하게** 띄운다 -- 상대는 ICG 이고
        #    우리 컨트롤러가 아니다.  `--backend sim` 에서도 배선을 볼 수 있다.
        if self.acfg.gauge_off_on_exposure or self.acfg.guiexpctrl:
            self._gauge_task = self.spawn(self._watch_acquisition())
        # **archon 백엔드가 아니면 컨트롤러 배선을 검사하지도, 배너를 찍지도
        # 않는다.**  `--backend sim` 은 메시지 층만 돌려 보는 모드이므로 그
        # 경고가 다 무의미하고, 무의미한 경고는 사람이 경고를 무시하도록
        # 학습시킨다.
        if self.cfg.hardware.backend != 'archon':
            await super().start()
            await self._require_xis()
            return
        for note in acfg_mod.validate(self.acfg, tuple(self.cfg.node.ccds),
                                      self.cfg):
            log.warning('[archon]: %s', note)
        await super().start()
        # ⭐ **허브를 확인하고, 안 되면 여기서 멈춘다** (운영자 지시
        # 2026-09-04).  ⚠️ `super().start()` **뒤**여야 한다 -- 전송이 열려야
        # PING 을 보내고 PONG 을 받는다.  컨트롤러 접속보다는 **앞**이다:
        # 허브가 없으면 어차피 못 돌 구성이라, 전원을 켜기 전에 멈추는 것이 싸다.
        await self._require_xis()
        self._log_archon_banner()
        # **접속을 먼저 연다 -- 감시는 그 뒤에 시작한다** (운영자 2026-08-28).
        # 한 컨트롤러의 접속자는 이 프로세스 하나다.
        await self._connect_controllers()
        self._start_monitors()

    async def _require_xis(self) -> None:
        """XIS 허브가 `PING` 에 답하는지 보고, 아니면 기동을 멈춘다.

        ⛔ **자동 우회는 없다** -- 허브가 없으면 직결로 넘어가지 않고 멈춘다
        (DevNote 11.15 확정).  ICS 와 ICG 는 허브를 통해서만 통신하기로
        확정됐으므로(운영자 2026-09-04), 허브 없이 뜨면 `VACGAUGE`·
        `EXPENABLE`·`HKDATA` 가 조용히 사라진 채로 자료가 쌓인다.
        """
        gate = getattr(self, 'xis_gate', None)
        if gate is None:
            return
        await gate.check(lambda: self.emit.ping(XIS_ID))

    async def _watch_acquisition(self) -> None:
        """취득이 끝나는 순간을 지켜본다 -- 그때 되켜기 타이머를 건다.

        ⭐ **`busy` 를 1초마다 본다.**  시퀀서에 완료 훅이 없고 `ics_sim` 을
        고치지 않기로 했으므로 이것이 가장 얕은 길이다 -- 10분 타이머 앞에서
        1초 해상도는 넉넉하다.

        ⚠️ 셔터 닫힘이 아니라 **취득 종료**를 쓴다: `GO n` 은 셔터가 n 번
        닫히므로 첫 닫힘에 타이머를 걸면 **다음 프레임 도중에 켜진다**
        (`gaugectl` 머리말).
        """
        was = False
        while True:
            await asyncio.sleep(max(0.05, self.acfg.phase_poll))
            # ⭐ guide 노출 잠금은 **국면**을 본다 (독출 앞뒤), 게이지는
            #    **취득 전체**를 본다 (끝나면 되켜기 타이머).  한 틱에서 둘 다.
            self.expenable.on_phase(self.state.expstatus,
                                    self._seconds_to_readout())
            now = bool(self.seq.busy)
            if was and not now:
                self.gauge.after_acquisition()
            was = now

    def _seconds_to_readout(self) -> float:
        """독출 시작까지 남은 초.  모르면 `inf`, 이미 독출 중이면 `0`.

        ⚠️ **적분 국면에서만 앞을 내다본다** -- `exp_start` 와 실효 노출시간이
        있어야 계산이 되고, BIAS/DARK 처럼 적분 국면이 없거나 짧은 갈래는
        `READOUT` 국면 자체가 신호다 (`expenable.on_phase`).
        """
        st = self.state
        phase = (st.expstatus or '').upper()
        if phase == 'READOUT':
            return 0.0
        if phase != 'INTEGRATING' or st.exp_start is None:
            return float('inf')
        end = st.exp_start + timedelta(seconds=st.effective_exptime)
        return (end - utcnow()).total_seconds()

    def _on_message(self, msg, addr) -> None:  # noqa: ANN001
        """⚠️ `VACGAUGE` 응답을 **엿듣는다** -- 명령 처리부는 그것을 안 쓴다.

        ICG 의 `DONE:`/`ERROR:`/`FATAL:` 는 우리 앞으로 오지만 처리기가 없어 조용히
        버려진다.  데드맨이 *"보냈는데 답이 없다"* 를 알려면 여기서 봐야 한다.
        ⭐ **`Message` 째로 넘긴다** -- 거절 판정은 받는 쪽이 `msg.mtype` 으로 한다
        (`note_reply`, DevNote 11.96).  ⛔ 원문(`msg.raw`)을 넘기면 받는 쪽이 부분
        문자열로 가를 수밖에 없다.
        """
        gate = getattr(self, 'xis_gate', None)
        if gate is not None:
            gate.note_message(msg)
        for ctl, word in ((getattr(self, 'gauge', None), GAUGE_CMD),
                          (getattr(self, 'expenable', None), EXPENABLE_CMD)):
            if (ctl is not None and ctl.enabled
                    and msg.src.upper() == ctl.node.upper()
                    and _is_reply_to(msg, word)):
                ctl.note_reply(msg)
        super()._on_message(msg, addr)

    async def stop(self) -> None:
        """종료 -- **백엔드를 먼저 내린다.**

        `super().stop()` 은 태스크를 취소하고 전송을 닫는다.  그 전에 전원을
        끄지 않으면 컨트롤러가 바이어스를 걸고 있는 채로 프로세스가 끝난다
        (labtest 가 노출 루프를 `try/finally` 로 감싼 것과 같은 이유 --
        DevNote 11.22 (4)).
        """
        # ⛔ **깃발을 가장 먼저 세운다** (DevNote 11.96) -- 아래 `release_pulse` 가 펄스를
        # 내린 뒤, 전송이 닫히기 전에 온 `SHOPEN <초>`·`CnTRIGOUT <ms>` 가 새 펄스를 띄우면
        # `super().stop()` 이 그것을 내림 없이 취소한다 (링크도 이미 닫혔다).  깃발이 서
        # 있으면 명령 처리부가 `Shutting down -- not raised` 로 거절한다.
        self.stopping = True
        # ⛔ **펄스를 먼저 내린다** (운영자 2026-09-09).  `spawn` 한 `SHOPEN`·
        # `CnTRIGOUT` 태스크는 `super().stop()` 이 취소하므로 내림이 **영영 안
        # 돈다** -- 그러면 사람 없는 채로 **셔터가 열린 채**(또는 `TRIGOUTLEVEL=1`
        # 인 채) 프로세스가 끝난다.
        # ⚠️ `spawn` 이 아니라 **여기서 기다린다** (같은 이유로).
        await self.dispatch.release_pulse('shutdown')
        # **감시를 가장 먼저 세운다** -- 아래 `_stop_monitors()` 참조.
        await self._stop_monitors()
        # 게이지 타이머·데드맨 -- ⚠️ 게이지를 켜지는 않는다 (gaugectl.close).
        await self.gauge.close()
        # guide 노출 잠금 -- ⚠️ **풀지 않는다** (독출 중에 죽었을 수 있다).
        await self.expenable.close()
        # **저장 중인 프레임을 먼저 지킨다.**  `super().stop()` 이 태스크를
        # 취소하고 `backend.shutdown()` 이 링크를 닫으므로, 그 전에 기다리지
        # 않으면 독출을 마친 프레임이 파일 없이 사라진다 -- 전원을 끄는 것보다
        # 앞이다 (전원은 몇 초 더 켜져 있어도 되지만 프레임은 다시 못 찍는다).
        drain = getattr(self.seq, 'drain_writers', None)
        if drain is not None:
            try:
                # ⭐ **반환값을 버리지 않는다** -- 상한 초과는 프레임을 잃은
                # 것이므로 종료 기록에 남아야 한다 (2026-09-06).
                late = await drain(self.acfg.shutdown_drain)
                if late:
                    log.error('%d frame(s) did not finish writing within the '
                              'shutdown limit (%.0fs) -- read out but no file',
                              late, self.acfg.shutdown_drain,
                              extra={'detail': '[archon] shutdown_drain 을 '
                                               '늘리거나 저장 경로를 확인하라'})
            except Exception:                       # noqa: BLE001
                log.exception('exception while draining writes -- frames may '
                              'have been lost')
        shutdown = getattr(self.backend, 'shutdown', None)
        if shutdown is not None:
            try:
                await shutdown()
            except Exception:                       # noqa: BLE001
                log.exception('exception during backend shutdown',
                              extra={'detail': '유닛 전원 상태를 직접 확인하라'})
        await super().stop()

    async def _connect_controllers(self) -> None:
        """**기동에서 각 컨트롤러에 접속한다** (운영자 확정 2026-08-28).

        `ics_archon` 이 그 컨트롤러의 **유일한 접속자**다.  `icg_archon` 이
        guide 를 맡고, 한 컨트롤러에 여러 노드가 붙는 구성은 두지 않는다 --
        Rev F 백플레인은 동시 접속이 하나뿐이고(매뉴얼 p.15), Rev H(4접속)에서도
        같은 규칙을 쓴다.  **소유자가 하나면 "누가 이 값을 읽었나" 를 물을 일이
        없다.**

        그래서 접속을 여는 자리를 여기로 못박았다 -- 종전에는 첫 노출의
        `prepare()` 였고, 감시를 넣으면서 잠깐 **감시 태스크의 부수효과**가 됐다.
        둘 다 "접속이 언제 열리나" 를 코드 흐름에서 읽기 어렵게 만든다.

        **실패해도 기동을 막지 않는다.**  컨트롤러 전원이 나중에 들어오는 배치가
        실재하고, 여기서 죽으면 그 배치가 통째로 못 돈다.  감시가
        `monitor_interval` 마다 다시 시도하고(`monitor = false` 면 첫 노출의
        `prepare()` 가 시도한다), 못 붙은 사실은 아래 배너와 로그에 남는다.
        """
        for ctrl in self.backend._active():
            if ctrl.link.connected:
                continue
            try:
                await ctrl.connect()
            except (ArchonError, TimeoutError, OSError) as exc:
                log.warning('%s: connect failed at startup (%s) -- startup '
                            'continues', ctrl.tag, exc,
                            extra={'detail': '컨트롤러 전원과 [archon] '
                                             'ctrl_%s_host 를 확인하라'
                                             % ctrl.tag.lower()})
                continue
            log.info('%s: connected %s:%d',
                     ctrl.tag, ctrl.link.host, ctrl.link.port)

    def _start_monitors(self) -> None:
        """컨트롤러마다 텔레메트리 감시 태스크를 띄운다 (층 1·2).

        **`IcsSim.spawn()` 을 그대로 쓴다** -- `ics_sim` 은 한 줄도 안 고친다.
        그쪽이 태스크 참조를 들고 있다가 `stop()` 에서 취소하므로, 우리는 그보다
        **먼저** 멈춰 세우기만 하면 된다 (아래 `stop()`).

        ⚠️ **감시는 `ctrl.status_live` 만 갱신한다** -- 헤더용 `ctrl.status` 는
        노출 개시에 언 채로 남는다.  그 둘을 섞으면 `Cn_TEMP/VOLT/CURR` 의 뜻이
        "노출 개시 시점 값" 에서 "마지막 폴링 값" 으로 조용히 바뀐다.
        """
        if not self.acfg.monitor:
            log.info('[archon] monitor=false -- no telemetry monitor')
            return
        ctrls = getattr(self.backend, 'ctrls', None)
        if not ctrls:
            return
        for tag in self.backend.tags:
            # ⭐ 사이트 코드를 넘긴다 -- 감시 CSV 파일명의 `<YYYYMMDD>` 가
            # 로그·FITS 와 같은 **관측일**이 되게 (운영자 2026-09-12).
            mon = TelemetryMonitor(ctrls[tag], self.acfg,
                                   expstatus=lambda: self.state.expstatus,
                                   site_code=self.state.site_code)
            self._monitors.append(mon)
            self._monitor_tasks.append(self.spawn(mon.run()))

    async def _stop_monitors(self) -> None:
        """감시를 **가장 먼저** 세운다 -- 종료 순서가 중요하다.

        `backend.shutdown()` 이 `POWEROFF` 를 내고 링크를 닫는데, 그 사이에
        감시가 `STATUS` 를 물면 종료 때마다 `poll_failed` 행이 남아 **진짜
        고장과 구별되지 않는다.**  그래서 전원을 끄기 전에 세운다.

        **끝날 때까지 기다린다** -- 세우라고 표시만 하고 넘어가면(`sleep(0)`)
        폴링 중이던 감시가 `POWEROFF`·`close()` 와 겹쳐 바로 그 헛 `poll_failed`
        를 남긴다.

        ⚠️ **다만 무한정 기다리지는 않는다.**  FETCH 가 락을 수 분 쥐고 있으면
        감시는 그 뒤에나 깨어난다 -- 그때까지 종료를 붙잡아 두면 전원 차단이
        늦어진다(검출기 쪽 위험).  상한을 넘기면 취소하는데, 그래도 마지막
        `stop` 행은 남는다 -- 감시의 `finally` 가 취소 경로에서도 그것을 적는다.
        """
        if not self._monitors:
            return
        for mon in self._monitors:
            mon.stop()
        tasks = [t for t in self._monitor_tasks if not t.done()]
        if tasks:
            _done, pending = await asyncio.wait(
                tasks, timeout=max(self.acfg.status_timeout, 1.0) + 1.0)
            for task in pending:
                log.warning('the monitor did not stop in time -- cancelling',
                            extra={'detail': 'FETCH 락에 걸려 있을 수 있다'})
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        self._monitors.clear()
        self._monitor_tasks.clear()

    def _log_archon_banner(self) -> None:
        """컨트롤러 배선과 **미검증 자리**를 기동에 한 번 보여 준다.

        사이트 배너(`ics_sim`)와 같은 취지다 -- 자료 한 장 찍기 전에 사람 눈에
        띄게 한다.  v0.0 은 실기 왕복이 미검증이므로 그 사실 자체가 배너
        항목이다.
        """
        a = self.acfg
        tags = a.active_tags(tuple(self.cfg.node.ccds))
        rows = [
            ('컨트롤러', ', '.join('%s=%s:%d' % (t, a.hosts.get(t, '?'), a.port)
                                   for t in tags) or '없음'),
            ('ACF', ', '.join('%s=%s' % (t, os.path.basename(a.acf.get(t, '-')))
                              for t in tags) or '없음'),
            # ⚠️ 기동 자체는 접속만 한다 -- ACF 는 **첫 GO 의 `prepare()`** 가 민다.
            ('ACF 적용', '첫 GO 에서 세션당 한 번 APPLYALL (건너뛰는 눈금 없음)'),
            ('선언 기하', '%d x %d  (%.1f MiB/파일)'
                          % (a.naxis1, a.naxis2, a.frame_bytes / (1 << 20))),
            ('텔레메트리', 'STATUS 질의 켜짐' if a.telemetry
                            else '꺼짐 -- Cn_* 는 NC'),
            ('감시·기록', ('%.0f초 간격 -> %s' % (a.monitor_interval,
                                                 a.monitor_log))
                          if (a.monitor and a.telemetry) else '꺼짐'),
            ('셔터 트리거', a.shutter_ctrl),
            ('ERASE', '전체 독출 flush' if a.full_flush_on_erase else '건너뜀'),
            # **어느 `ics_sim` 사본이 돌고 있나.**  저장소 배치에는 형제 원천과
            # 내장본이 둘 다 있을 수 있어서, 어느 것을 골랐는지가 진단의 출발점
            # 이다 (독립 배포에서는 내장본이 나온다).
            ('ics_sim', _simpath.describe()),
        ]
        width = 74
        lines = ['=' * width,
                 ' Archon 배선 -- v0.0 은 실기 왕복이 미검증이다',
                 '-' * width]
        lines += [' %-14s%s' % (label, value) for label, value in rows]
        lines += [
            '-' * width,
            ' 미검증(잠정) 3자리 -- ics_archon/SMC_CLAUDE.md',
            '   1. STATUS 필드 이름·모듈 나열 순서 (Cn_TEMP 의 자리)',
            '   2. 두 컨트롤러 시차·픽셀 좌우 배치 (독출 368 행/초·12.77초 · '
            'FETCH 3.2~3.5초는 2026-09-01 실측 완료)',
            '   3. 산출물 실물 (기하·픽셀 좌우 배치·DETID·DATE-OBS)',
            # ⚠️ 종전 줄 *"원천 없음 -- 듀어·환경 HK 는 sentinel"* 은 와이어 HK(2026-09-15)
            # 뒤로 틀린 말이었다 (DevNote 11.96).
            ' 듀어·환경 HK(5.6절) -- GO 마다 ICG 에 HKDATA NOW 로 묻는다 (답이 없으면 '
            'sentinel)',
            '=' * width,
        ]
        log.info('\n%s', '\n'.join(lines))

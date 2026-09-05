#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""배선 -- `ics_sim.IcsSim` 에 Archon 백엔드를 끼운다.

**`ics_sim` 의 배선을 그대로 물려받는다.**  9개 노드 수신 · 명령 처리 · 시퀀서 ·
텔레메트리 중계 · 콘솔은 전부 그쪽 것이고, 여기서 갈라지는 것은 넷뿐이다:

1. **백엔드** -- `ics_sim.hardware.register_backend()` 로 실기 구현을 넣는다.
   그 자리가 원래 확장점이고(`[hardware] backend = archon` 한 줄), 구현만
   이 패키지에 있다.
2. **`ICSBUILD`** -- `ics_archon` 자신의 버전·빌드일시로 바꾼다.  안 바꾸면
   `ics_sim` 의 값이 실려 **거짓 provenance** 가 된다 (`ics_sim/__init__.py`
   의 `build_id()` 경고).
3. **`RDMODE`** -- ini 가 비어 있으면 적용 ACF 이름에서 유도한다 (labtest 가
   하던 일).  컨트롤러는 ACF 이름을 보고하지 않으므로(매뉴얼 p.54) 호스트가
   아는 유일한 근거가 그 파일명이다.
4. **종료** -- 전원을 끄고 연결을 닫는다.  전원을 켠 채로 끝나는 것은 검출기
   쪽 위험이다.
5. **접속과 텔레메트리 감시** -- 기동에서 컨트롤러에 접속하고, 그 뒤에 컨트롤러
   마다 주기 감시 태스크를 띄운다 (층 1·2, `archon/monitor.py`).
   `IcsSim.spawn()` 을 쓰므로 `ics_sim` 은 무수정이다.  **한 컨트롤러의 접속자는
   이 프로세스 하나다** -- guide 는 `icg_archon` 이 같은 방식으로 맡는다.
"""

from __future__ import annotations

import asyncio
import logging
import os

from datetime import timedelta

from . import _simpath, build_id, config as acfg_mod

_simpath.ensure()

from ics_sim.app import IcsSim                            # noqa: E402
from ics_sim.hardware import register_backend             # noqa: E402

from .archon.backend import ArchonBackend                 # noqa: E402
from .archon.monitor import TelemetryMonitor              # noqa: E402
from .archon.protocol import ArchonError                  # noqa: E402
from .gaugectl import CMD as GAUGE_CMD, GaugeControl      # noqa: E402
from .guideexp import CMD as GUIEXP_CMD, GuideExpControl  # noqa: E402
from .tcsclock import ClockWatch, watch_tc_queries
from .xischeck import XIS_ID, XisGate         # noqa: E402
from ics_sim import emitter                                # noqa: E402
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
ICS_OPS_COMMANDS = frozenset({'CCDFLUSH', 'CCDPOWON', 'CCDPOWOFF', 'ARCHON'})

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

#: ACF 경로에서 헤더 값을 뽑는 규칙 둘은 **`config.py` 에 함께 있다** --
#: `rdmode_from_acf()`(`RDMODE`) · `cfg_name_from_acf()`(`CTRLnCFG`).
#: 같은 입력에서 나오는 값들이라 한 곳에 두었고, `config._cross_checks()` 가
#: 둘의 어긋남을 기동에서 본다.
#: **둘의 자르기 규칙이 다르다**: `RDMODE` 는 토큰을 찾을 뿐이라 `splitext`
#: 로 충분하지만, `CTRLnCFG` 는 값 자체가 되므로 판 번호의 점을 먹으면 안 된다.
rdmode_from_acf = acfg_mod.rdmode_from_acf


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
    `[controllers]` 의 원칙도 "채워져 있으면 INI 가 이긴다" 다.  아래 `RDMODE`
    도 같은 규칙이라 한 블록 안의 우선순위가 하나로 유지된다.  대가로 남는
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
            log.info('CTRL%dCFG 를 ACF 경로에서 파생했다 -- %s (%s)',
                     n, derived, acfg.acf.get(tag, ''))


class IcsDispatcher(Dispatcher):
    """ICS 명령 처리부 -- `GO` 앞에서 진공게이지를 끈다 (운영자 2026-09-04).

    ⭐ **스크립트 관측이든 콘솔에서 직접 친 `GO` 든 여기를 지난다** -- 그래서
    한 곳에서 끈다.  `ics_sim` 은 한 줄도 안 고친다.

    추가 (운영자 지시 2026-09-05) -- 컨트롤러를 **직접** 만지는 운영자 명령 넷:

    * `CCDFLUSH [MK|NT|ALL]`   -- 유휴 CCD 를 FlushFrame 한 바퀴로 비운다
    * `CCDPOWON [MK|NT|ALL]`   -- `POWERON` (+ `poweron_wait` 의 flush 대기)
    * `CCDPOWOFF [MK|NT|ALL]`  -- `POWEROFF`
    * `ARCHON <MK|NT> <원문…>` -- 바이패스: 명령 원문을 한 컨트롤러에, 응답 원문을 그대로

    ⭐ 넷 다 **응답이 나중에 온다** (`Reply.noop()` -> 왕복 뒤 `emit.done/error`) --
    핸들러는 동기 함수인데 왕복(특히 `POWERON` 의 flush 대기 수 초)이 필요하기
    때문이고, `ics_sim` 의 `ERASE`/`SHOPEN` · icg 의 `HTRSET` 이 쓰는 **같은 선례**다.

    ⛔ **취득 중(`seq.busy`)이면 넷 다 거부한다** (`BUSY_TEXT`).  진행 중 노출 위에
    `LOADPARAMS`(flush) · `POWEROFF` · `RESETTIMING`(바이패스 원문) 이 들어가면
    자료를 망친다.  ⭐ 반대 방향도 막는다 -- 넷 중 하나가 **돌고 있는 동안 `GO`** 는
    거부한다 (`_op_inflight`).  `CCDPOWOFF` 의 `POWEROFF` 가 아직 안 나갔는데 `GO`
    가 `prepare()` 를 지나면(`powered` 가 아직 True) 노출 도중에 전원이 내려간다.
    같은 이유로 운영자 명령끼리도 한 번에 하나다.
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
            # ⛔ 게이지를 만지기 **전에** 거절한다 -- 아래 `before_exposure()` 를
            # 지나면 되켜기 타이머까지 걸어야 한다.
            return bad
        gauge = getattr(self.app, 'gauge', None)
        if gauge is not None:
            # ⭐ **super() 앞에서** 끈다 -- 뒤에 두면 첫 프레임의 앞부분을
            # 필라멘트가 켜진 채로 찍는다.
            gauge.before_exposure()
        reply = super().cmd_go(msg, target)
        busy = bool(getattr(getattr(self.app, 'seq', None), 'busy', False))
        if (gauge is not None and reply is not None
                and reply.kind is ReplyKind.ERROR and not busy):
            # ⛔ **GO 가 거절됐다** -- 취득이 시작되지 않았으므로 "끝났다" 도
            # 안 온다.  자가 치유로 되켜기 타이머를 건다.  안 그러면 게이지가
            # 다음 취득이 끝날 때까지(또는 영영) 꺼진 채로 남는다.
            #
            # ⛔⛔ **취득 중의 거절은 예외다** (운영자 지시 2026-09-04).
            # 취득 중에 들어온 `GO` 는 *"Data acquisition already in
            # progress!"* 로 거절되는데 그것도 `ERROR` 라, 여기서 타이머를
            # 걸면 **돌고 있는 취득 중에** 10분이 시작된다 -- 남은 노출이
            # 10분을 넘으면 **노출 도중에 게이지가 켜진다**.  ⭐ `seq.busy` 로
            # 그 갈래를 가른다: 취득 중이면 아무것도 안 하고, 타이머는 진짜
            # 독출이 끝날 때 `_watch_acquisition` 이 건다 (10분의 기준은
            # **독출 완료**다).
            gauge.after_acquisition()
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

    async def _finish_op(self, dest: str, cmdword: str, work) -> None:  # noqa: ANN001
        """`work` 가 돌려준 본문을 `DONE` 으로, 예외는 `ERROR: <cmd> Failed: …` 로.

        ⚠️ `except Exception` 은 `CancelledError` 를 잡지 않는다(3.8+ BaseException) --
        종료가 태스크를 취소하면 응답 없이 끝나고 `finally` 만 표시를 내린다.
        """
        try:
            body = await work
        except _OpError as exc:
            self.emit.error(dest, cmdword, str(exc))
            return
        except (BackendError, ArchonError, TimeoutError, OSError) as exc:
            log.error('%s 실패 -- %s', cmdword, exc)
            self.emit.error(dest, cmdword, 'Failed: %s' % _fail_text(exc))
            return
        except Exception as exc:  # noqa: BLE001  하나의 명령이 프로세스를 죽이지 않는다
            log.exception('%s 실패 -- 예상 밖 예외', cmdword)
            self.emit.error(dest, cmdword, 'Failed: %s: %s'
                            % (type(exc).__name__, _fail_text(exc)))
            return
        finally:
            self._op_inflight = ''
        self.emit.done(dest, cmdword, body)

    # -- CCDFLUSH ----------------------------------------------------------------

    def cmd_ccdflush(self, msg: Message, target: Target) -> Reply:
        """CCDFLUSH [MK|NT|ALL] -- 유휴 CCD 를 FlushFrame 한 바퀴로 비운다.

        `backend.flush_ccd()` -> `controller.flush_now(reset=False)`: `FirstFlush=1` ·
        `Exposures=0` 을 `LOADPARAMS` 로 걸고(science ACF R2609+ 의 `FlushFrame` =
        Prep + Flush) 설정 메모리의 `FirstFlush` 를 0 으로 되쓴다.  프레임은 안 만든다.

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
        log.info('CCDFLUSH %s -- %s 가 시켰다', tags, msg.src)
        return self._start_op(msg.src, 'CCDFLUSH', self._flush_work(be, tags))

    async def _flush_work(self, be, tags) -> str:  # noqa: ANN001
        done = await be.flush_ccd(tags)
        return 'Flushed=%s' % ','.join(done)

    # -- CCDPOWON / CCDPOWOFF ----------------------------------------------------

    def cmd_ccdpowon(self, msg: Message, target: Target) -> Reply:
        """CCDPOWON [MK|NT|ALL] -- `POWERON`.  ⚠️ `poweron_wait`(CCD flush 대기, 기본
        12 s) 를 포함하므로 응답이 그만큼 늦다.

        ⚠️ 실기는 **이 세션에서 `APPLYALL` 이 없었으면** `?xx` 로 거부한다 (매뉴얼
        p.51, DevNote 10.2) -- REBOOT·전원 재투입 뒤라면 `GO` 한 번(`prepare()` 의
        `APPLYALL`)이 먼저다.  그 진단 문구는 `controller.power_on()` 이 낸다.
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
        log.info('%s %s -- %s 가 시켰다', cmdword, tags, msg.src)
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
        `WCONFIG…` 같은 원문도 그대로 나간다.  그래서 취득 중에는 거부한다 (`BUSY_TEXT`).

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
        bad = self._refuse_if_busy('ARCHON')
        if bad is not None:
            return bad
        log.info('ARCHON %s %r -- %s 가 시켰다 (바이패스, 위생 검사 없음)',
                 tag, text, msg.src)
        return self._start_op(msg.src, 'ARCHON', self._archon_work(be, tag, text))

    async def _archon_work(self, be, tag: str, text: str) -> str:  # noqa: ANN001
        try:
            reply = await be.raw_command(tag, text)
        except ArchonError as exc:
            if exc.reply_error:
                # 컨트롤러가 `?xx` 로 거부했다 -- 내 명령이 틀린 것이라 `DONE` 이 아니다.
                log.warning('ARCHON %s: 컨트롤러가 거부했다 -- %r (%s)', tag, text, exc)
                raise _OpError('%s rejected: %s' % (tag, wire_text(text))) from exc
            log.error('ARCHON %s %r 실패 -- %s', tag, text, exc)
            raise _OpError('%s Failed: %s' % (tag, _fail_text(exc))) from exc
        except (BackendError, TimeoutError, OSError) as exc:
            log.error('ARCHON %s %r 실패 -- %s', tag, text, exc)
            raise _OpError('%s Failed: %s' % (tag, _fail_text(exc))) from exc
        body = wire_text(reply)
        # ⭐ **전문은 여기에** -- 와이어는 잘려도 로그는 안 잘린다.
        log.info('ARCHON %s %r -> %d bytes: %s', tag, text, len(body),
                 body or '(empty reply)')
        if len(body) > ARCHON_REPLY_MAX:
            kept = body[:ARCHON_REPLY_MAX].rstrip()
            body = '%s ...(+%d bytes truncated, see log)' % (kept, len(body) - len(kept))
        return '%s %s' % (tag, body or '<empty reply>')


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
            log.warning('[hardware] backend=%r 로 ics_archon 을 띄웠다 -- '
                        'Archon 컨트롤러를 만지지 않는다.  실기로 돌리려면 '
                        'archon 으로 두거나 --backend archon 을 주라',
                        cfg.hardware.backend)
        self.acfg = acfg
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
        # 백엔드 호출(`initialize()`)에서 기다려야 `ccdflush` 의 `Prep`+`Flush`
        # 가 게이지가 꺼진 뒤에 돈다 (운영자 지시 2026-09-04).  ⚠️ 명령 처리부
        # 에서는 못 기다린다 -- `cmd_go` 는 `Reply` 를 돌려주는 동기 메서드다.
        backend = getattr(self, 'backend', None)
        if backend is not None:
            backend.gauge = self.gauge
        #: science 독출 앞뒤로 guide 노출을 막고 푼다 (`GUIEXPCTRL`).
        self.guideexp = GuideExpControl(
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

        # `RDMODE` -- ini 가 비었으면 ACF 이름에서.
        if not cfg.controllers.rdmode:
            for tag in ('MK', 'NT'):
                derived = rdmode_from_acf(acfg.acf.get(tag, ''))
                if derived:
                    cfg.controllers.rdmode = derived
                    log.info('RDMODE 를 ACF 이름에서 유도했다 -- %s (%s)',
                             derived, acfg.acf.get(tag, ''))
                    break

    async def start(self) -> None:
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
            self.guideexp.on_phase(self.state.expstatus,
                                   self._seconds_to_readout())
            now = bool(self.seq.busy)
            if was and not now:
                self.gauge.after_acquisition()
            was = now

    def _seconds_to_readout(self) -> float:
        """독출 시작까지 남은 초.  모르면 `inf`, 이미 독출 중이면 `0`.

        ⚠️ **적분 국면에서만 앞을 내다본다** -- `exp_start` 와 실효 노출시간이
        있어야 계산이 되고, BIAS/DARK 처럼 적분 국면이 없거나 짧은 갈래는
        `READOUT` 국면 자체가 신호다 (`guideexp.on_phase`).
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

        ICG 의 `DONE:`/`ERROR:` 는 우리 앞으로 오지만 처리기가 없어 조용히
        버려진다.  데드맨이 *"보냈는데 답이 없다"* 를 알려면 여기서 봐야 한다.
        """
        gate = getattr(self, 'xis_gate', None)
        if gate is not None:
            gate.note_message(msg)
        raw = (msg.raw or '').upper()
        for ctl, word in ((getattr(self, 'gauge', None), GAUGE_CMD),
                          (getattr(self, 'guideexp', None), GUIEXP_CMD)):
            if (ctl is not None and ctl.enabled
                    and msg.src.upper() == ctl.node.upper() and word in raw):
                ctl.note_reply(msg.raw)
        super()._on_message(msg, addr)

    async def stop(self) -> None:
        """종료 -- **백엔드를 먼저 내린다.**

        `super().stop()` 은 태스크를 취소하고 전송을 닫는다.  그 전에 전원을
        끄지 않으면 컨트롤러가 바이어스를 걸고 있는 채로 프로세스가 끝난다
        (labtest 가 노출 루프를 `try/finally` 로 감싼 것과 같은 이유 --
        DevNote 11.22 (4)).
        """
        # **감시를 가장 먼저 세운다** -- 아래 `_stop_monitors()` 참조.
        await self._stop_monitors()
        # 게이지 타이머·데드맨 -- ⚠️ 게이지를 켜지는 않는다 (gaugectl.close).
        await self.gauge.close()
        # guide 노출 잠금 -- ⚠️ **풀지 않는다** (독출 중에 죽었을 수 있다).
        await self.guideexp.close()
        # **저장 중인 프레임을 먼저 지킨다.**  `super().stop()` 이 태스크를
        # 취소하고 `backend.shutdown()` 이 링크를 닫으므로, 그 전에 기다리지
        # 않으면 독출을 마친 프레임이 파일 없이 사라진다 -- 전원을 끄는 것보다
        # 앞이다 (전원은 몇 초 더 켜져 있어도 되지만 프레임은 다시 못 찍는다).
        drain = getattr(self.seq, 'drain_writers', None)
        if drain is not None:
            try:
                await drain(self.acfg.shutdown_drain)
            except Exception:                       # noqa: BLE001
                log.exception('저장 대기 중 예외 -- 프레임을 잃었을 수 있다')
        shutdown = getattr(self.backend, 'shutdown', None)
        if shutdown is not None:
            try:
                await shutdown()
            except Exception:                       # noqa: BLE001
                log.exception('백엔드 종료 중 예외 -- 유닛 전원 상태를 직접 '
                              '확인하라')
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
                log.warning('%s: 기동 접속 실패 (%s) -- 기동은 계속한다.  '
                            '컨트롤러 전원과 [archon] ctrl_%s_host 를 확인하라',
                            ctrl.tag, exc, ctrl.tag.lower())
                continue
            log.info('%s: 접속 %s:%d', ctrl.tag, ctrl.link.host, ctrl.link.port)

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
            log.info('[archon] monitor=false -- 텔레메트리 감시를 걸지 않는다')
            return
        ctrls = getattr(self.backend, 'ctrls', None)
        if not ctrls:
            return
        for tag in self.backend.tags:
            mon = TelemetryMonitor(ctrls[tag], self.acfg,
                                   expstatus=lambda: self.state.expstatus)
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
                log.warning('감시가 제때 멈추지 않았다 -- 취소한다 (FETCH 락에 '
                            '걸려 있을 수 있다)')
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
            ('ACF 적용', 'APPLYALL 수행' if a.apply_acf
                          else '건너뜀 (줄 번호만 파싱해 대조)'),
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
            ' 원천 없음 -- 듀어·환경 HK(sensors) 는 sentinel 로 실린다',
            '=' * width,
        ]
        log.info('\n%s', '\n'.join(lines))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command dispatch.

매칭은 대소문자 무관이다 -- 레거시 라이브러리도 strcasecmp 를 쓰고, 실측 로그에
`OBS>ICS go` / `OBS>ICS Go` / `OBS>ICS GO` 가 모두 나온다.

**모든 명령이 핸들러 함수를 갖는다.**  지금 동작하지 않는 것(BIN/ROI/DISPL/
STOP/ABORT/MOVIE)도 docstring 과 레거시 근거 주석을 갖춘 스텁으로 존재한다.
다음 단계에서 본문만 채우면 되도록 하기 위해서다 (DevNote 9.2).  strict_legacy
가 켜져 있으면 레거시와 똑같이 무응답이고, 끄면 ERROR 를 돌려주는 현대화
모드가 된다.

발신 노드 화이트리스트는 두지 않는다.  IMPv2 에 노드 인증 개념이 없고, 실제
로그에도 문서화되지 않은 클라이언트(CHA, C1 -- DevNote 6.3)가 명령을 보낸다.
프로토콜에 맞으면 누가 보냈든 처리하고 요청자에게 응답한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from .impv2 import Message, paren, quote_always
from .nodes import Role, Target
from .state import IMAGE_TYPES, ExpStatus, stamp_iso_ms, utcnow

log = logging.getLogger('ics_sim.cmd')


class ReplyKind(Enum):
    DONE = 'done'
    ERROR = 'error'
    NOOP = 'noop'      # 핸들러가 직접 발신을 끝냈다
    IGNORE = 'ignore'  # 아무 응답도 하지 않는다 (레거시 미구현 명령)


@dataclass(frozen=True)
class Reply:
    kind: ReplyKind
    cmdword: str = ''
    body: str = ''

    @staticmethod
    def done(cmdword: str, body: str = '') -> 'Reply':
        return Reply(ReplyKind.DONE, cmdword, body)

    @staticmethod
    def error(cmdword: str, body: str) -> 'Reply':
        return Reply(ReplyKind.ERROR, cmdword, body)

    @staticmethod
    def noop() -> 'Reply':
        return Reply(ReplyKind.NOOP)

    @staticmethod
    def ignore() -> 'Reply':
        return Reply(ReplyKind.IGNORE)


#: 레거시 명령 테이블에는 있으나 구현되지 않은 명령들.
#: 48GB 로그 전량에서 송수신 0건 -- 운용에서 한 번도 쓰이지 않았다(DevNote 6.7).
UNIMPLEMENTED = ('BIN', 'ROI', 'DISPL', 'STOP', 'ABORT', 'MOVIE')


class Dispatcher:
    """수신 메시지를 명령 핸들러로 보낸다."""

    def __init__(self, app) -> None:  # noqa: ANN001
        self.app = app
        self.cfg = app.cfg
        self.state = app.state
        self.emit = app.emit

    # -- 진입점 -----------------------------------------------------------

    def handle(self, msg: Message, target: Target) -> None:
        """우리 앞으로 온 REQ/EXEC 메시지를 처리한다."""
        cmd = msg.cmdword.upper()
        if not cmd:
            return  # heartbeat -- 응답하지 않는다

        # bug_compat 재현용 기록.  정상 경로는 이 값을 읽지 않는다.
        self.emit.note_inbound(cmd)

        handler = getattr(self, f'cmd_{cmd.lower().replace(".", "_")}', None)
        if handler is None:
            if cmd in UNIMPLEMENTED:
                handler = self._unimplemented
            else:
                self._reply(msg, target, Reply.error(
                    cmd, f"Didn't understand {msg.payload} ?"))
                return

        try:
            reply = handler(msg, target)
        except Exception as exc:  # noqa: BLE001  하나의 잘못된 명령이 전체를 죽이지 않는다
            log.exception('command %s failed', cmd)
            reply = Reply.error(cmd, f'internal error: {exc}')
        if reply is not None:
            self._reply(msg, target, reply)

    def _reply(self, msg: Message, target: Target, reply: Reply) -> None:
        if reply.kind is ReplyKind.IGNORE or reply.kind is ReplyKind.NOOP:
            return
        role = target.role if target.role in (Role.IC, Role.CB) else Role.ICS
        ccd = target.ccd
        st = self.state
        if reply.kind is ReplyKind.DONE:
            self.emit.done(msg.src, reply.cmdword, reply.body,
                           st.expstatus, role, ccd)
        else:
            self.emit.error(msg.src, reply.cmdword, reply.body,
                            st.expstatus, role, ccd)

    # -- out-of-band ------------------------------------------------------

    def cmd_ping(self, msg: Message, target: Target) -> Reply:
        """PING -> PONG.  프로토콜 스펙 2.4절의 소프트웨어 핸드셰이킹.

        **브로드캐스트 PING에는 9개 노드 ID 전부로 PONG을 보낸다.**

        XIS 는 기동/재시작할 때 `handShake()` 에서 `XIS>AL PING` 을 시리얼
        포트와 preset UDP 목록에 뿌리고, 돌아오는 PONG 으로 클라이언트 테이블을
        다시 채운다(XIS 소스 `interfaces.c`, DevNote 3.1.1 (12)④).  **이것이
        XIS 재시작 후 재등록되는 유일한 경로다.**

        레거시는 노드마다 프로세스가 따로라 각자 PONG 을 보냈고, 그래서 12개
        노드가 전부 살아났다.  통합 프로그램인 우리가 대표로 하나만 답하면
        `ICS` 만 재등록되고 나머지 8개는 영영 죽는다 -- kstatus/dmawait/
        datasource 가 도달하지 않게 된다.

        직접 지목된 PING(`OBS>K.IC PING`)에는 그 노드로만 답한다.
        """
        if msg.is_broadcast and self.cfg.transport.register_all_nodes:
            for node_id in self.app.router.registered_ids:
                self.emit.register_ping(node_id, msg.src, cmdword='PONG')
            return Reply.noop()
        self.emit.pong(msg.src, target.role, target.ccd)
        return Reply.noop()

    def cmd_pong(self, msg: Message, target: Target) -> Reply:
        return Reply.ignore()

    # -- 상태 조회 --------------------------------------------------------

    def cmd_status(self, msg: Message, target: Target) -> Reply:
        """STATUS.  ICS 앞이면 통합 설정, IC 앞이면 그 CCD 상태.

        OBSAgent 의 스크립트 응답 체크는 본문에 `" STATUS"`(앞 공백 포함)가
        있는지 본다 (DevNote 3.5).  `DONE: STATUS ...` 형태면 자동으로 만족한다.
        """
        st = self.state
        if target.role is Role.IC:
            ch = st.channel(target.ccd)
            hw = self.app.backend.status(target.ccd)
            ch.driving = hw.get('driving', ch.driving)
            ch.fibers = hw.get('fibers', ch.fibers)
            ch.synched = hw.get('synched', ch.synched)
            self.emit.ic_status(msg.src, target.ccd, ch, st.expstatus)
            return Reply.noop()

        body = (f'Inst=ICS ExpTime={st.exptime:g} GuideExp=0 '
                f'ImageType={st.imgtype} ObjectName={quote_always(st.objname)} '
                f'Mode={"Acquiring" if st.exposing else "Idle"} ComTest=F')
        return Reply.done('STATUS', body)

    def cmd_acqstatus(self, msg: Message, target: Target) -> Reply:
        """ACQSTATUS -- 4개 IC 의 연결/초기화 상태."""
        parts = [f'{self.cfg.node.ic_of(c)}=READY' for c in self.cfg.node.ccds]
        body = ('ACQSTATUS=READY ' + ' '.join(parts) +
                f' MASTER={self.cfg.node.ic_of(self.cfg.node.master)}')
        return Reply.done('ACQSTATUS', body)

    def cmd_time(self, msg: Message, target: Target) -> Reply:
        now = utcnow()
        return Reply.done('TIME', f'OS={stamp_iso_ms(now)} '
                                  f'FITS={stamp_iso_ms(now)} TIMESYS=UTC')

    def cmd_synchronize(self, msg: Message, target: Target) -> Reply:
        """SYNCHRONIZE -- 현재 설정 스냅샷.

        레거시는 이 형태의 메시지가 오면 보낸 주체와 무관하게 그대로 반영하는
        수동 리스너였다.  통합 노드에는 동기화할 상대가 없지만, 외부 노드(ICG
        등)가 물어보면 그대로 답한다.  실측상 DONE: 과 STATUS: 두 타입 모두
        쓰였다 (DevNote 3.6).
        """
        return Reply.done('SYNCHRONIZE', self.state.synchronize_body())

    def cmd_filename(self, msg: Message, target: Target) -> Reply:
        st = self.state
        if target.role is Role.IC:
            ch = st.channel(target.ccd)
            name = f'KMTN{target.ccd.lower()}.{ch.suffix or st.peek_suffix()}'
            return Reply.done('FILENAME', f'Filename={name}')
        return Reply.done('FILENAME', f'Filename={st.ics_filename()}')

    def cmd_expnum(self, msg: Message, target: Target) -> Reply:
        """EXPNUM -- 파일 일련번호 조회/설정.

        **OBSAgent 가 자동으로 보내는 질의다.**  readout 중 첫 PCTREAD= 를 받은
        시점에 `OBS>ICS ExpNum` 을 스스로 발행하고, 응답의 `Filename=` 뒤
        **정확히 15자**를 잘라 expinfo.strNextNum 으로 쓴다.  그 값이 다음
        노출의 Shutter=Open 시점에 strCurNum 으로 승격돼 관측자 화면과
        /data/Logs/ObsStatus.txt 의 ExpNum 필드를 채운다.
        OBSAgent v1.0.1(2024-07-01)에 추가된 기능이며, 응답하지 않으면 카메라
        동작은 정상이지만 ExpNum 표시가 갱신되지 않는다 (DevNote 3.4).

        레거시는 ICS 6자리 / IC 4자리로 자릿수가 달라 INITIALIZE 로 우회했지만,
        신규는 6자리로 통일했다 (ics_legacy_report 3.4절).
        """
        st = self.state
        arg = msg.body.strip()
        if arg:
            try:
                st.expnum = int(arg)
            except ValueError:
                return Reply.error('EXPNUM', f'Invalid exposure number: {arg}')
        return Reply.done('EXPNUM', f'Filename={st.peek_suffix()}')

    # -- 설정 -------------------------------------------------------------

    def cmd_projid(self, msg: Message, target: Target) -> Reply:
        arg = msg.body.strip()
        if arg:
            self.state.projid = arg.upper()
            self._propagate(msg)
        return Reply.done('PROJID', f'ProjID={self.state.projid}')

    def cmd_observer(self, msg: Message, target: Target) -> Reply:
        """OBSERVER -- 띄어쓰기가 허용된다.  응답은 괄호로 감싼다."""
        arg = msg.body.strip()
        if arg:
            self.state.observer = arg
            self._propagate(msg)
        return Reply.done('OBSERVER', f'Observer={paren(self.state.observer)}')

    def cmd_exp(self, msg: Message, target: Target) -> Reply:
        """EXP -- 노출시간.  BIAS 상태에서는 거부한다 (레거시 실측)."""
        st = self.state
        arg = msg.body.strip()
        if arg:
            if st.imgtype.upper() == 'BIAS':
                return Reply.error(
                    'EXP', f'Cannot change EXPTIME for ImgType={st.imgtype}')
            try:
                st.exptime = float(arg)
            except ValueError:
                return Reply.error('EXP', f'Invalid exposure time: {arg}')
            self._propagate(msg)
        return Reply.done('EXP', f'ExpTime={st.exptime:g} seconds.')

    def cmd_ledflash(self, msg: Message, target: Target) -> Reply:
        arg = msg.body.strip()
        if arg:
            try:
                self.state.ledflash_ms = int(arg)
            except ValueError:
                return Reply.error('LEDFLASH', f'Invalid flash time: {arg}')
        return Reply.done('LEDFLASH',
                          f'LEDFlashTime={self.state.ledflash_ms}')

    def _image_type(self, msg: Message, imgtype: str) -> Reply:
        """BIAS/DARK/OBJECT/FLAT/SKY/DOMEFLAT/STANDARD 공통.

        응답의 EXP= 는 **변경 전 현재 노출시간**이다 (실측).  BIAS 는 정의상
        0초로 보고한다.
        """
        st = self.state
        arg = msg.body.strip()
        st.imgtype = imgtype
        if arg:
            st.objname = arg
        if imgtype == 'BIAS':
            st.exptime = 0.0
        self._propagate(msg)
        return Reply.done(imgtype,
                          f'ImageType={imgtype} ObjectName={quote_always(st.objname)} '
                          f'EXP={st.effective_exptime:g}')

    def cmd_bias(self, msg, target):  # noqa: ANN001, ANN201, D102
        return self._image_type(msg, 'BIAS')

    def cmd_dark(self, msg, target):  # noqa: ANN001, ANN201, D102
        return self._image_type(msg, 'DARK')

    def cmd_object(self, msg, target):  # noqa: ANN001, ANN201, D102
        return self._image_type(msg, 'OBJECT')

    def cmd_flat(self, msg, target):  # noqa: ANN001, ANN201, D102
        return self._image_type(msg, 'FLAT')

    def cmd_sky(self, msg, target):  # noqa: ANN001, ANN201, D102
        return self._image_type(msg, 'SKY')

    def cmd_domeflat(self, msg, target):  # noqa: ANN001, ANN201, D102
        return self._image_type(msg, 'DOMEFLAT')

    def cmd_standard(self, msg, target):  # noqa: ANN001, ANN201, D102
        return self._image_type(msg, 'STANDARD')

    def _propagate(self, msg: Message) -> None:
        """설정 변경을 각 IC 로 전파한다.

        레거시는 ICS 가 받은 명령을 원문 그대로 4개 IC 에 다시 보내고 각 IC 가
        DONE 으로 답했다.  통합 구조에서는 그 왕복이 사라지므로 내부적으로는
        아무것도 하지 않는다 -- IcsState 하나가 진실의 원천이다.
        emit_node_mode=legacy 로 골든 대조를 할 때만 그 전파 메시지를 재현한다.
        """
        if self.cfg.node.emit_node_mode != 'legacy':
            return
        for ccd in self.cfg.node.ccds:
            self.emit.emit_req(self.cfg.node.ic_of(ccd),
                               msg.cmdword, msg.body)

    # -- IC 전용 설정 -----------------------------------------------------

    def cmd_dmawait(self, msg: Message, target: Target) -> Reply:
        """DMAWAIT -- optical fiber 통신 지연.  OBSAgent 는 K.IC 에만 보낸다."""
        ccd = target.ccd or self.cfg.node.master
        ch = self.state.channel(ccd)
        arg = msg.body.strip()
        if arg:
            try:
                ch.dmawait = int(arg)
            except ValueError:
                return Reply.error('DMAWAIT', f'Invalid DMA wait time: {arg}')
        return Reply.done('DMAWAIT', f'DMAWaitTime={ch.dmawait}')

    def cmd_datasource(self, msg: Message, target: Target) -> Reply:
        """DATASOURCE -- onboard crosstalk 보정 선택.

        레거시가 받아들이는 값은 ADC / CTC / **SIM** 세 가지다.  SIM 은 문서에
        없었고 에러 메시지에서만 드러났다 (DevNote 6.4).  시뮬 백엔드가 자신을
        SIM 으로 보고하므로 프로토콜상 자연스럽게 맞물린다.
        """
        ccd = target.ccd or self.cfg.node.master
        ch = self.state.channel(ccd)
        arg = msg.body.strip().upper()
        mapping = {'ADC': 'ADC', 'CTC': 'CT_CORRECTION', 'SIM': 'SIM'}
        if arg:
            if arg not in mapping:
                return Reply.error(
                    'DATASOURCE',
                    'Invalid selection for DataSource. ADC, CTC, and SIM are '
                    f'valid. DataSource={ch.datasource}')
            ch.datasource = mapping[arg]
        return Reply.done('DATASOURCE',
                          f'DataSource={ch.datasource} '
                          f'CTCSource={ch.ctc_source}')

    def cmd_initialize(self, msg: Message, target: Target) -> Reply:
        """INITIALIZE <suffix> -- 파일명 suffix 를 통째로 설정.

        레거시는 ICS 6자리 / IC 4자리 EXPNUM 불일치를 이 명령으로 우회했다.
        신규는 자릿수를 통일했지만, 외부에서 임의 suffix 를 지정하는 용도는
        그대로 남긴다 (실측상 CHA 노드가 이 명령을 쓴다 -- DevNote 6.3).
        """
        suffix = msg.body.strip()
        if not suffix:
            return Reply.error('INITIALIZE', 'Missing filename suffix')
        ccds = [target.ccd] if target.ccd else list(self.cfg.node.ccds)
        for ccd in ccds:
            self.state.channel(ccd).suffix = suffix
        return Reply.done('INITIALIZE', 'Initialization Complete.')

    def cmd_erase(self, msg: Message, target: Target) -> Reply:
        """ERASE -- CCD flushing.  레거시는 master 에서만 동작했다."""
        ccd = target.ccd or self.cfg.node.master
        if ccd != self.cfg.node.master:
            return Reply.ignore()
        self.app.spawn(self._do_erase(msg.src, ccd))
        return Reply.noop()

    async def _do_erase(self, dest: str, ccd: str) -> None:
        await self.app.backend.erase(ccd)
        self.emit.ic_erase_done(dest, ccd)

    def cmd_shopen(self, msg: Message, target: Target) -> Reply:
        """SHOPEN <sec> [<sourceID> USESTATUS] -- 셔터 개방.  master 전용."""
        parts = msg.body.split()
        if not parts:
            return Reply.error('SHOPEN', 'Missing exposure time')
        try:
            seconds = float(parts[0])
        except ValueError:
            return Reply.error('SHOPEN', f'Invalid exposure time: {parts[0]}')
        source = parts[1] if len(parts) > 1 else msg.src
        ccd = target.ccd or self.cfg.node.master
        self.app.spawn(self._do_shopen(source, ccd, seconds))
        return Reply.noop()

    async def _do_shopen(self, dest: str, ccd: str, seconds: float) -> None:
        import asyncio
        await self.app.backend.open_shutter(seconds)
        self.emit.ic_shutter_open(dest, ccd)
        await asyncio.sleep(self.cfg.scaled(seconds))
        await self.app.backend.close_shutter()
        self.emit.ic_shutter_closed(dest, ccd)

    def cmd_shclose(self, msg: Message, target: Target) -> Reply:
        """SHCLOSE -- 셔터 즉시 닫기 (강제 중단용).  master 전용."""
        ccd = target.ccd or self.cfg.node.master
        was_open = self.app.backend.status(ccd).get('shutter_open', False)
        self.app.spawn(self.app.backend.close_shutter())
        tail = '' if was_open else ' Shutter was not open'
        return Reply.done('SHCLOSE',
                          f'Shutter=Closed Integration Remaining=0 sec.{tail}')

    def cmd_flashnow(self, msg: Message, target: Target) -> Reply:
        """FLASHNOW <n> -- 점검용 LED 를 n 만큼 점등.

        실측상 운용에서 정기적으로 쓰인다 (CTIO 4,700+회 -- DevNote 6.6).
        """
        ccd = target.ccd or self.cfg.node.master
        try:
            ms = int(msg.body.strip() or self.state.ledflash_ms)
        except ValueError:
            return Reply.error('FLASHNOW', f'Invalid flash time: {msg.body}')
        self.app.spawn(self._do_flash(msg.src, ccd, ms))
        return Reply.noop()

    async def _do_flash(self, dest: str, ccd: str, ms: int) -> None:
        await self.app.backend.flash_led(ms)
        self.emit.ic_flashnow_done(dest, ccd)

    # -- 노출 -------------------------------------------------------------

    def cmd_go(self, msg: Message, target: Target) -> Reply:
        """GO [n] -- 노출 n 장.

        진행 중이면 거부한다.  OBSAgent 도 CamStatus 가 IDLE_3/READY 가 아니면
        GO 를 막지만, ICS 자체 방어선이 따로 있다 (실측 ERROR 메시지).
        """
        st = self.state
        if self.app.seq.busy:
            return Reply.error('GO', 'Data acquisition already in progress!')
        arg = msg.body.strip()
        count = 1
        if arg:
            try:
                count = max(1, int(arg))
            except ValueError:
                return Reply.error('GO', f'Invalid frame count: {arg}')
        if self.cfg.behavior.injecting('init_fail'):
            return Reply.error('', 'Failed to initialize one or more ICs')
        st.expstatus = ExpStatus.INITIALIZING
        self.app.seq.start(count, msg.src)
        return Reply.noop()

    # -- 미구현 (구현 자리를 남겨 둔다) ------------------------------------

    def _unimplemented(self, msg: Message, target: Target) -> Reply:
        """레거시 명령 테이블에는 있으나 동작하지 않는 명령들.

        strict_legacy=true 면 레거시와 똑같이 **무응답**이다.  "명령이 정의돼
        있다고 곧 동작한다는 뜻은 아니다"라는 레거시의 성질을 그대로 재현하기
        위해서다 (ics_legacy_report 3.4절).  끄면 ERROR 를 돌려준다.
        """
        if self.cfg.behavior.strict_legacy:
            log.debug('unimplemented command ignored: %s', msg.cmdword)
            return Reply.ignore()
        return Reply.error(msg.cmdword.upper(), 'not implemented yet')

    def cmd_bin(self, msg: Message, target: Target) -> Reply:
        """BIN <n> -- CCD binning.

        레거시 상태: 명령 목록에만 존재, 미구현.  48GB 로그 전량 0건.
        구현 시: backend 에 set_binning(ccd, n) 을 추가하고 FITS 헤더의
        CCDSUM/BINNING 키워드를 함께 갱신할 것.
        """
        return self._unimplemented(msg, target)

    def cmd_roi(self, msg: Message, target: Target) -> Reply:
        """ROI <x1> <x2> <y1> <y2> -- region of interest.

        레거시 상태: 예약만 되고 미동작.  48GB 로그 전량 0건.
        구현 시: backend.set_roi() + FITS 의 DATASEC/DETSEC 갱신.
        """
        return self._unimplemented(msg, target)

    def cmd_displ(self, msg: Message, target: Target) -> Reply:
        """DISPL -- 표시용 축소 영상 전송.  레거시 예약, 미동작."""
        return self._unimplemented(msg, target)

    def cmd_stop(self, msg: Message, target: Target) -> Reply:
        """STOP -- integration 중지 후 readout/저장은 수행.

        레거시 상태: 미구현.  48GB 로그 전량 0건.
        구현 시: 셔터를 닫고 카운트다운을 끊은 뒤 정상 readout 경로로 합류한다.
                 sequencer 에 stop_integration() 을 추가하면 된다.
                 운영 편의상 실제 구현 가치가 높다 (DevNote 13장 백로그).
        """
        return self._unimplemented(msg, target)

    def cmd_abort(self, msg: Message, target: Target) -> Reply:
        """ABORT -- 전체 중지, readout/저장 안 함.

        레거시 상태: 미구현.  48GB 로그 전량 0건.
        구현 시: self.app.seq.cancel(save=False) 후 EXPSTATUS=IDLE 을 발신한다.
                 진행 중이던 저장 태스크도 정리해야 한다.
        """
        return self._unimplemented(msg, target)

    def cmd_movie(self, msg: Message, target: Target) -> Reply:
        """MOVIE -- 연속 촬영 모드.  레거시 예약, 미동작."""
        return self._unimplemented(msg, target)


#: 참고용 -- 이 디스패처가 아는 명령 전부.
KNOWN = tuple(sorted(
    {n[4:].upper() for n in dir(Dispatcher) if n.startswith('cmd_')}
    | set(UNIMPLEMENTED) | set(IMAGE_TYPES)))

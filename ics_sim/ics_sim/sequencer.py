#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exposure state machine.

레거시에서 ICS 와 4개 IC/CB 사이를 오가던 프로토콜이 여기서는 **프로그램 내부의
병렬 처리 문제**로 바뀐다.  4개 CCD 는 asyncio.Task 로 병렬 진행하고 ICS 는
gather 로 모은다.  바깥으로 나가는 메시지는 레거시와 같게 유지한다.

전체 흐름 (DevNote 4.1/4.2, XIS 로그 실측):

    go 접수
      -> TC AUXSTATUS 질의
      -> EXPSTATUS=INITIALIZING          [OBS]
      -> G.IC / K,M,T,N.IC 로 INITIALIZE
      -> EXPSTATUS=ERASE                 [OBS]
      -> K.IC 에만 ERASE, AUXSTATUS 를 4 IC 로 중계, TC TCSSTATUS 질의
      -> (erase_sec) Erase Cycle Complete.
      -> EXPSTATUS=INTEGRATING           [OBS]   ← 노출 개시 시각 확정
      -> TCSSTATUS 를 4 IC 로 중계 (DATE-OBS = 이 시각)
      -> 셔터 경로면 SHOPEN + Shutter=Open + 카운트다운 (K.IC 발신)
         DARK/BIAS 면 ICS 가 "Remaining=N sec. of M sec." 로 카운트다운
      -> Shutter=Closed Integration Remaining=0 sec.
      -> EXPSTATUS=READOUT               [OBS]
      -> M/T/N.IC 에 GO, 마지막에 K.IC 에 GO
      -> master 가 PCTREAD= 를 sourceID 에게만 보고
      -> 100% 에서 4개 IC 가 "Acquisition Complete." (마침표 포함) 발신
      -> EXPSTATUS=IDLE                  [OBS]  (마지막 프레임만 DONE:)
      -> 백그라운드로 CCD 별 저장 -> CB Wrote -> ICS 가 OBS 로 중계

지켜야 하는 시간 창 (OBSAgent, DevNote 3.3):
  * 4개 "Acquisition Complete." 가 **1.8초** 안에 모여야 한다.  넘으면
    OBSAgent 가 스크립트 관측을 멈춘다(opause).
  * 4번째 이후 **0.9초** 안에 EXPSTATUS=IDLE 이 가야 한다.
  * IDLE_3 진입 후 **25초** 안에 4개 Wrote 가 들어와야 한다.
  * READY 는 IDLE_3 후 12.2초 타이머다 -- 메시지로 앞당길 수 없다.
config.validate() 가 기동 시 이 창을 침범하는지 검사한다.

EXPSTATUS= 알림은 **상태가 실제로 전이한 시점에 1회씩만, OBS 로만** 보낸다.
레거시는 셔터가 닫힌 뒤에도 INTEGRATING 을 계속 내보냈고(DevNote 3.2.2), 또
IC 앞으로 가는 텔레메트리 중계에도 EXPSTATUS= 를 실었다.  후자가 OBS 로도 가면
OBSAgent 의 CamStatus 가 INT_1 으로 역행한다(DevNote 3.2.1).
"""

from __future__ import annotations

import asyncio
import logging

from .config import SimConfig
from .emitter import Emitter
from .hardware import BackendError
from .nodes import NodeRouter, Role
from .state import (ExpStatus, IcsState, stamp_guide, stamp_iso, unique_path,
                    utcnow)
from .telemetry import TelemetryRelay

log = logging.getLogger('ics_sim.seq')


class Sequencer:
    """노출 사이클 하나를 끝까지 몰고 간다."""

    def __init__(self, cfg: SimConfig, state: IcsState, emit: Emitter,
                 router: NodeRouter, telem: TelemetryRelay, backend) -> None:  # noqa: ANN001
        self.cfg = cfg
        self.state = state
        self.emit = emit
        self.router = router
        self.telem = telem
        self.backend = backend
        self._task: asyncio.Task | None = None
        self._writers: list[asyncio.Task] = []
        #: 저장이 끝날 때까지 재사용을 막기 위한 CCD 별 락
        self._write_lock: dict[str, asyncio.Lock] = {}
        #: STOP 신호.  세워지면 카운트다운이 즉시 끝나고 readout 으로 넘어간다.
        self._stop_evt = asyncio.Event()
        #: ABORT 로 취소됐는지.  _run 의 CancelledError 처리가 이것을 본다.
        self._aborted_by: str | None = None

    # -- 외부 인터페이스 --------------------------------------------------

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def integrating(self) -> bool:
        """적분 중인가 -- STOP 의 선행 조건.

        레거시의 `ExpLoopFlag = 1` 에 해당한다 (PAP7KX.CMD:282).
        """
        return self.busy and self.state.expstatus == ExpStatus.INTEGRATING

    def start(self, count: int, source: str) -> None:
        """GO 접수.  실제 진행은 백그라운드 태스크."""
        self._stop_evt.clear()
        self._aborted_by = None
        self._task = asyncio.create_task(
            self._run(count, source), name='ics_sim.exposure')

    async def wait(self) -> None:
        """노출과 후속 저장까지 전부 끝날 때까지 (테스트/콘솔 편의)."""
        if self._task is not None:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._writers:
            await asyncio.gather(*self._writers, return_exceptions=True)
            self._writers.clear()

    def stop_integration(self, requester: str) -> bool:
        """STOP -- 적분만 조기 종료한다.  readout 과 저장은 정상 진행.

        레거시(PAP7KX.CMD:279-290)는 `SoftStop = 1` 을 세우고 `AbortHost` 에
        요청자를 기록할 뿐, 노출 사이클 자체는 그대로 흘려보낸다.  여기서도
        카운트다운만 끊는다 -- 셔터 닫힘 알림부터 `Wrote` 까지 전부 정상
        경로를 탄다.  OBSAgent 입장에서는 그냥 짧은 노출로 보인다.

        Returns:
            받아들였으면 True.  적분 중이 아니면 False (호출측이 레거시와
            같은 거부 문자열을 돌려준다).
        """
        if not self.integrating:
            return False
        log.info('STOP from %s -- ending integration early', requester)
        self._stop_evt.set()
        return True

    def cancel(self, save: bool = False, requester: str = '') -> bool:
        """ABORT -- 노출 전체를 중지한다.  readout 도 저장도 하지 않는다.

        레거시(PAP7KX.CMD:291-302)는 `GoFlag = 0` 으로 되돌리고 `AbortHost` 를
        기록한다.  통합 구조에서는 진행 중인 태스크를 취소해야 하고, **이미
        떠 있는 저장 태스크도 함께 정리**해야 한다 -- 레거시는 CB 가 별도
        프로세스라 이 문제가 없었다(12.10 과 같은 부류).

        Args:
            save: True 면 진행 중이던 저장은 끝까지 두고 노출만 중단한다.
            requester: 레거시의 `AbortHost`.  종료 알림을 여기로 보낸다.

        Returns:
            받아들였으면 True.  노출 중이 아니면 False.
        """
        if not self.busy:
            return False
        log.warning('ABORT from %s -- cancelling exposure (save=%s)',
                    requester, save)
        self._aborted_by = requester or self.cfg.node.ics_id
        if not save:
            for w in self._writers:
                w.cancel()
            self._writers.clear()
        self._task.cancel()
        return True

    # -- 본체 -------------------------------------------------------------

    async def _run(self, count: int, source: str) -> None:
        st = self.state
        st.exposing = True
        try:
            for index in range(1, count + 1):
                await self._frame(index, count, source)
        except BackendError as exc:
            log.error('exposure aborted: %s', exc)
            self.emit.error(source, '', str(exc), st.expstatus)
            st.expstatus = ExpStatus.IDLE
        except asyncio.CancelledError:
            # ABORT 로 끊긴 경우에는 OBSAgent 가 IDLE 로 돌아올 수 있도록
            # 종료를 알려야 한다.  알리지 않으면 CamStatus 가 READOUT 에
            # 머문 채 force_idle 타임아웃을 타고 opause 로 간다(3.3).
            log.warning('exposure cancelled')
            st.expstatus = ExpStatus.IDLE
            if self._aborted_by is not None:
                self.emit.idle_done(self._aborted_by)
            raise
        finally:
            st.exposing = False

    async def _frame(self, index: int, count: int, source: str) -> None:
        cfg, st = self.cfg, self.state
        ccds = cfg.node.ccds
        master = cfg.node.master
        ics = cfg.node.ics_id

        await asyncio.sleep(cfg.scaled(cfg.timing.go_to_initializing))

        # --- 1) INITIALIZING ---------------------------------------------
        # AUXSTATUS 는 ERASE 국면에 중계하지만 질의는 여기서 먼저 시작한다.
        # sleep(0) 으로 태스크를 한 번 돌려 ICS>TC AUXSTATUS 가 실제로 먼저
        # 나가게 한다 -- 레거시 로그의 순서와 맞추기 위해서다.
        aux_query = asyncio.create_task(self.telem.query('AUXSTATUS'))
        await asyncio.sleep(0)

        st.expstatus = ExpStatus.INITIALIZING
        self.emit.exp_status(source, ExpStatus.INITIALIZING)

        suffix = st.next_suffix()
        st.guide_suffix = stamp_guide()
        if cfg.behavior.send_guide_init and cfg.node.guide_ic_id:
            # 가이드 채널에도 INITIALIZE 를 보낸다.  ICG 자체는 범위 밖이지만
            # 레거시가 보내던 메시지라 형태를 유지한다.
            self.emit.emit_req(cfg.node.guide_ic_id, 'INITIALIZE', st.guide_suffix)

        for ccd in ccds:
            st.channel(ccd).suffix = suffix
            self.emit.emit_req(cfg.node.ic_of(ccd), 'INITIALIZE', suffix)

        await asyncio.gather(*(self.backend.initialize(c, suffix) for c in ccds))
        for ccd in ccds:
            self.emit.ic_initialize_done(ics, ccd)

        await aux_query

        # --- 2) ERASE ----------------------------------------------------
        st.expstatus = ExpStatus.ERASE
        self.emit.exp_status(source, ExpStatus.ERASE)
        self.emit.emit_req(cfg.node.ic_of(master), 'ERASE')

        await self._relay_aux(ExpStatus.ERASE)
        tcs_query = asyncio.create_task(self.telem.query('TCSSTATUS'))

        await self.backend.erase(master)
        self.emit.ic_erase_done(ics, master)
        await tcs_query

        # --- 3) INTEGRATING ----------------------------------------------
        # 노출 개시 시각을 여기서 확정한다.  TCSSTATUS 의 DATE-OBS 가 이 값이다.
        st.exp_start = utcnow()
        st.expstatus = ExpStatus.INTEGRATING
        self.emit.exp_status(source, ExpStatus.INTEGRATING)

        exptime = st.effective_exptime
        if st.opens_shutter and exptime > 0:
            await self._integrate_shutter(source, master, exptime)
        else:
            await self._relay_tcs(stamp_iso(st.exp_start), ExpStatus.INTEGRATING)
            await self._integrate_dark(source, exptime)

        # --- 4) READOUT --------------------------------------------------
        if st.opens_shutter and exptime > 0:
            await asyncio.sleep(cfg.scaled(cfg.timing.shutter_to_readout))

        # M/T/N 먼저, master(K)는 마지막.  레거시 순서 그대로.
        others = [c for c in ccds if c != master]
        for ccd in others:
            self.emit.emit_req(cfg.node.ic_of(ccd), 'GO', source)
        for ccd in others:
            self.emit.ic_go_ack(ics, ccd)

        st.expstatus = ExpStatus.READOUT
        self.emit.exp_status(source, ExpStatus.READOUT)

        self.emit.emit_req(cfg.node.ic_of(master), 'GO', source)
        self.emit.ic_go_ack(ics, master)

        await self._readout(source, master)

        # --- 5) 획득 완료 -------------------------------------------------
        # 4개가 1.8초 안에 모여야 한다.  같은 이벤트 루프 틱에서 내보내므로
        # 산포는 사실상 0 이다.
        final = cfg.readout.pctread_final
        reporting = ccds
        if cfg.behavior.injecting('acq_short'):
            # 4개에 못 미치면 OBSAgent 가 1.8초 뒤 opause + ERROR 를 낸다.
            reporting = ccds[:-1]
            log.warning('inject: Acquisition Complete. 를 %d회만 보냅니다',
                        len(reporting))
        for ccd in reporting:
            self.emit.ic_acq_complete_obs(source, ccd, final)
        for ccd in reporting:
            self.emit.ic_acq_complete_ics(ics, ccd)

        # 저장은 백그라운드로 넘긴다.  GO n 에서 프레임 N 의 Wrote 가 프레임
        # N+1 의 준비 중에 도착하는 레거시 파이프라인을 그대로 재현한다.
        #
        # 파일명은 **여기서 확정해 넘긴다.**  저장 태스크가 나중에
        # ChannelState.suffix 를 읽으면 그때는 이미 다음 프레임이 덮어쓴 뒤라
        # 프레임 1 의 영상이 프레임 2 의 번호로 저장된다 (실제로 그 버그를
        # 겪었다 -- GO 5 에서 일련번호가 4개만 나왔다).
        header = self.telem.header_dict(stamp_iso(st.exp_start))
        for ccd in ccds:
            path = st.channel(ccd).filename(cfg.paths.data_dir)
            self._writers.append(asyncio.create_task(
                self._store(ccd, source, dict(header), path),
                name=f'ics_sim.store.{ccd}'))
        self._writers = [t for t in self._writers if not t.done()]

        await asyncio.sleep(cfg.scaled(cfg.timing.acq_to_idle))
        st.expstatus = ExpStatus.IDLE
        if index < count:
            self.emit.image_complete(source, index, count)
        else:
            self.emit.idle_done(source)
        st.advance()

    # -- 노출 국면 --------------------------------------------------------

    async def _integrate_shutter(self, source: str, master: str,
                                 exptime: float) -> None:
        """셔터를 여는 경로 (OBJECT/FLAT/SKY/DOMEFLAT/STANDARD)."""
        cfg, st = self.cfg, self.state
        self.emit.emit_req(cfg.node.ic_of(master), 'SHOPEN',
                           f'{exptime:g} {source} USESTATUS')
        await self.backend.open_shutter(exptime)

        # 셔터가 실제로 열린 시각으로 노출 개시를 갱신하고, 그 값을 DATE-OBS 로
        # 확정한 뒤에야 TCSSTATUS 를 중계한다 (ics_legacy_report 5.3절).
        st.exp_start = utcnow()
        self.emit.ic_shutter_open(source, master)
        await self._relay_tcs(stamp_iso(st.exp_start), ExpStatus.INTEGRATING)

        tick = cfg.timing.countdown_tick_shop
        async for remaining in self._countdown(exptime, tick):
            self.emit.ic_countdown(source, master, remaining)

        await self.backend.close_shutter()
        self.emit.ic_shutter_closed(source, master)

    async def _integrate_dark(self, source: str, exptime: float) -> None:
        """셔터를 열지 않는 경로 (DARK/BIAS).

        ICS 가 직접 카운트다운하고, 종료도 ICS 가 알린다.  셔터를 연 적이
        없는데도 `Shutter=Closed` 로 보내는 것은 레거시 관례이며 그대로
        유지한다 -- OBSAgent 가 이걸로 CLOSING 을 밟기 때문이다(DevNote 3.2.1).
        """
        tick = self.cfg.timing.countdown_tick_dark
        total = int(round(exptime))
        async for remaining in self._countdown(exptime, tick):
            self.emit.countdown_ics(source, remaining, total,
                                    ExpStatus.INTEGRATING)
        self.emit.shutter_closed_ics(source, ExpStatus.INTEGRATING)

    async def _nap(self, seconds: float) -> bool:
        """seconds 만큼 재우되 STOP 이 오면 즉시 깬다.

        Returns:
            STOP 때문에 깼으면 True, 정상적으로 다 잤으면 False.
        """
        if seconds <= 0:
            return self._stop_evt.is_set()
        try:
            await asyncio.wait_for(self._stop_evt.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return False
        return True

    async def _countdown(self, exptime: float, tick: float):
        """노출 시간을 tick 간격으로 세며 남은 초를 yield 한다.

        마지막 조각은 따로 재우고 yield 하지 않는다 -- 종료 알림
        (`Shutter=Closed .. Remaining=0 sec.`)이 그 역할을 하기 때문이다.

        STOP 이 들어오면 남은 시간을 건너뛰고 조용히 끝난다.  호출측이 곧바로
        셔터를 닫고 readout 으로 넘어가므로, 바깥에서 보면 짧은 노출과 같다.
        """
        scaled_tick = self.cfg.scaled(tick)
        elapsed = 0.0
        while True:
            remaining = exptime - elapsed - tick
            if remaining < 1.0:
                break
            if await self._nap(scaled_tick):
                return
            elapsed += tick
            yield int(exptime - elapsed)
        rest = max(exptime - elapsed, 0.0)
        if rest > 0:
            await self._nap(self.cfg.scaled(rest))

    async def _readout(self, source: str, master: str) -> None:
        """master 의 진행률을 sourceID 에게만 보고한다.

        진행률은 백엔드가 yield 한다.  시뮬은 [readout] 설정대로, 실기는
        컨트롤러가 보고하는 값을 그대로 흘려보낸다 -- 이 코드는 안 바뀐다.
        """
        final = self.cfg.readout.pctread_final
        async for pct in self.backend.readout(master):
            if pct >= final:
                break
            self.state.channel(master).pctread = pct
            self.emit.ic_pctread(source, master, pct)

    # -- 텔레메트리 중계 --------------------------------------------------

    def _builds(self) -> dict[str, str]:
        st = self.state
        out = {f'{c}BUILD': st.channel(c).build for c in self.cfg.node.ccds}
        out['GBUILD'] = st.guide_build
        out['ICSBUILD'] = st.ics_build
        return out

    async def _relay_aux(self, expstatus: str) -> None:
        body = self.telem.aux_body(expstatus, self._builds())
        gap = self.cfg.scaled(self.cfg.timing.aux_relay_gap)
        for ccd in self._relay_order():
            self.emit.emit(self.cfg.node.ic_of(ccd), 'STATUS', 'AUXSTATUS', body)
            await asyncio.sleep(gap)

    async def _relay_tcs(self, date_obs: str, expstatus: str) -> None:
        body = self.telem.tcs_body(date_obs, expstatus)
        gap = self.cfg.scaled(self.cfg.timing.tcs_relay_gap)
        for ccd in self._relay_order():
            self.emit.emit(self.cfg.node.ic_of(ccd), 'STATUS', 'TCSSTATUS', body)
            await asyncio.sleep(gap)

    def _relay_order(self) -> tuple[str, ...]:
        """중계 순서.  실측은 N -> T -> M -> K (master 가 마지막)."""
        known = [c for c in self.cfg.timing.ccd_skew_order
                 if c in self.cfg.node.ccds]
        rest = [c for c in self.cfg.node.ccds if c not in known]
        return tuple(known + rest)

    # -- 저장 -------------------------------------------------------------

    async def _store(self, ccd: str, source: str, header: dict,
                     wanted: str) -> None:
        """CCD 하나의 FITS 저장 + Wrote 발신.

        레거시는 IC -> CB TRANSFER DISK<n> / REQ SWAP / ACK SWAP 핸드셰이크로
        디스크 링을 돌렸지만, 신규는 단일 저장 경로다(DevNote 6.2) -- 취합
        서버와 기기제어를 한 PC 에 통합해 NFS 전송시간을 감당할 필요가 없어졌기
        때문이다.  바깥으로 나가는 Wrote 규약만 유지한다.

        Args:
            wanted: 프레임 시작 시점에 확정된 경로.  여기서 다시 계산하면
                파이프라인된 다음 프레임의 번호를 집어 온다.
        """
        cfg, st = self.cfg, self.state
        lock = self._write_lock.setdefault(ccd, asyncio.Lock())
        async with lock:
            skew = cfg.timing.skew_of(ccd)
            await asyncio.sleep(cfg.scaled(cfg.timing.write_delay + skew))

            if cfg.behavior.injecting('wrote_drop') and ccd == cfg.node.master:
                log.warning('inject: %s.CB Wrote 를 일부러 누락시킵니다', ccd)
                return

            ch = st.channel(ccd)
            path, clashed = (unique_path(wanted) if cfg.paths.write_fits
                             else (wanted, False))
            try:
                rate = await self.backend.write_fits(ccd, path, header)
            except BackendError as exc:
                self.emit.error(source, '', str(exc), st.expstatus)
                return
            ch.last_file = path

            if clashed:
                # fail-safe 경고는 ICS 와 OBS 양쪽으로 나간다 (DevNote 6.4).
                self.emit.cb_name_clash(cfg.node.ics_id, ccd, wanted, path)
                self.emit.cb_name_clash(source, ccd, wanted, path)

            # 레거시는 XIS PING/PONG 왕복을 저장 완료 타이밍 신호로 재활용했다.
            # 신규는 내부 콜백이므로 그 편법이 필요 없지만, IC 계층이 내던
            # 'Disk Write Complete' 는 형태를 유지한다 (OBSAgent 는 무시한다).
            self.emit.ic_disk_write_complete(cfg.node.ics_id, ccd)
            self.emit.cb_wrote(cfg.node.ics_id, ccd, path, rate)
            # OBSAgent 가 실제로 세는 것은 이 중계다.
            self.emit.wrote_relay(source, path, rate, st.expstatus)

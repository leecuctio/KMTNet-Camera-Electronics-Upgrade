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
import time

from . import rawhdr, rawpair
from .config import SimConfig
from .emitter import Emitter
from .hardware import BackendError
from .nodes import NodeRouter, Role
from .state import ExpStatus, IcsState, stamp_guide, stamp_iso_ms, utcnow
from .telemetry import TelemetryRelay

log = logging.getLogger('ics_sim.seq')


class Sequencer:
    """노출 사이클 하나를 끝까지 몰고 간다."""

    def __init__(self, cfg: SimConfig, state: IcsState, emit: Emitter,
                 router: NodeRouter, telem: TelemetryRelay, backend,  # noqa: ANN001
                 aux=None) -> None:  # noqa: ANN001  -- AuxControlClient
        self.cfg = cfg
        self.state = state
        self.emit = emit
        self.router = router
        self.telem = telem
        self.backend = backend
        #: AUX control 연동 (auxcontrol.py).  None 이면 이벤트를 건너뛴다.
        self.aux = aux
        self._task: asyncio.Task | None = None
        self._writers: list[asyncio.Task] = []
        #: 저장이 끝날 때까지 재사용을 막기 위한 CCD 별 락
        self._write_lock: dict[str, asyncio.Lock] = {}
        #: **진행 중 프레임이 띄운** 저장 태스크.  ABORT 의 취소 대상을
        #: 이것으로 좁힌다 -- `_writers` 전체를 취소하면 이미 완결된 앞
        #: 프레임의 파일까지 사라진다 (`cancel()` 참고).
        self._frame_writers: list[asyncio.Task] = []
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

    async def drain_writers(self, timeout: float) -> int:
        """**저장 태스크만** 끝날 때까지 기다린다 (종료 경로용).

        `wait()` 는 노출 사이클(`_task`)까지 기다리므로 `GO 100` 중이면 끝나지
        않는다.  종료에서 필요한 것은 그것이 아니라 **이미 독출을 마친
        프레임을 잃지 않는 것**이다 -- 저장은 `write_delay` 뒤에 백그라운드로
        도는데, 그 사이 종료가 태스크를 취소하면 컨트롤러에서 다 읽어낸
        프레임이 파일 없이 사라진다.

        Args:
            timeout: 상한 [s].  0 이하면 기다리지 않는다.

        Returns:
            상한 안에 못 끝낸 태스크 수 (0 이면 전부 저장됐다).
        """
        pending = [t for t in self._writers if not t.done()]
        if not pending or timeout <= 0:
            return len(pending)
        log.info('종료 대기 -- 저장 중인 프레임 %d개 (상한 %.0f초)',
                 len(pending), timeout)
        done, late = await asyncio.wait(pending, timeout=timeout)
        del done
        if late:
            log.error('저장이 %.0f초 안에 안 끝났다 -- 프레임 %d개를 잃는다. '
                      '독출은 끝났는데 파일이 없는 상태다', timeout, len(late))
        return len(late)

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
            # **진행 중 프레임이 띄운 저장만 취소한다.**  구판은 `_writers`
            # 전체를 취소해서, `GO n` 파이프라인에서 프레임 k 초반에 ABORT 가
            # 오면 이미 `Acquisition Complete.` 까지 발신한 **프레임 k-1 의
            # 파일이 기록 전에 사라졌다** (저장 태스크는 `write_delay+skew`
            # 동안 잠들어 있다).  GO 종료 직후 새 GO 를 ABORT 하는 경우에는
            # 직전 GO 의 완결 노출이 지워졌다 -- 그 프레임의 `Wrote` 는 영영
            # 안 나가고(OBSAgent 25초 창) 번호는 이미 소비돼 디스크에 구멍만
            # 남았다.  레거시는 CB 가 별도 프로세스라 앞 프레임을 끝까지 썼다.
            for w in self._frame_writers:
                w.cancel()
            self._writers = [t for t in self._writers
                             if t not in self._frame_writers]
            self._frame_writers = []
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

        # **STOP 은 그 프레임의 적분에만 적용된다** (`stop_integration()` 의
        # 계약: "적분만 조기 종료").  구판은 `start()` 에서만 이벤트를 지워서
        # `GO n` 도중 STOP 이 오면 이벤트가 세워진 채 다음 프레임으로 넘어갔고,
        # 각 프레임의 첫 `_nap()` 이 즉시 깨어나 **남은 프레임 전부가 ~0초
        # 노출**이 됐다 -- 그런데 헤더 `EXPTIME` 은 요청값을 그대로 실으므로
        # (raw spec 5.4절) 정상 노출로 보이는 오염 프레임이 생산됐다.
        self._stop_evt.clear()
        # 이 프레임이 띄운 저장 태스크만 담는다 -- ABORT 가 이전 프레임의
        # 저장을 취소하지 않게 하는 근거다 (`cancel()` 참고).
        self._frame_writers = []

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
        # 헤더의 AUX 스냅샷을 **노출과 같은 시각**으로 맞춘다 (운영자 확정
        # 2026-08-13).  프레임 개시의 AUXSTATUS 는 여기보다 8초 이상 앞서
        # 질의됐으므로(`initialize_ack` + `erase_sec`) 셔터 상태가 노출과
        # 무관하다 -- 레거시 실측이 `IMAGETYP='OBJECT'`·`EXPTIME=30` 프레임에
        # `SHUTTER='CLOSED'` 를 남긴 것이 그 증거다.
        #
        # **셔터를 여는 노출과 그렇지 않은 노출의 시점이 다르다:**
        #   * DARK/BIAS -- 여기서 **즉시**.  셔터를 열지 않으니 기다릴 것이 없고
        #     `SHUTTER='CLOSED'` 가 곧 정답이다.
        #   * 셔터 노출 -- `SHOPEN` 후 `aux_requery_after_shopen` 만큼 뒤에
        #     (`_integrate_shutter`).  블레이드가 움직일 시간을 준다.
        if not (st.opens_shutter and st.effective_exptime > 0):
            await self.telem.query('AUXSTATUS')
            await self._relay_aux(ExpStatus.INTEGRATING)

        # 노출 개시 시각을 여기서 확정한다.  TCSSTATUS 의 DATE-OBS 가 이 값이다.
        st.exp_start = utcnow()
        st.expstatus = ExpStatus.INTEGRATING
        self.emit.exp_status(source, ExpStatus.INTEGRATING)

        exptime = st.effective_exptime
        if st.opens_shutter and exptime > 0:
            await self._integrate_shutter(source, master, exptime)
        else:
            await self._relay_tcs(stamp_iso_ms(st.exp_start), ExpStatus.INTEGRATING)
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

        # --- 5) 획득 완료 -------------------------------------------------
        # 4개가 1.8초 안에 모여야 한다.  **기본은 같은 이벤트 루프 틱**에서
        # 내보내므로 산포가 사실상 0 이고, 그 창이 구조적으로 보장된다.
        final = cfg.readout.pctread_final
        reporting = ccds
        if cfg.behavior.injecting('acq_short'):
            # 4개에 못 미치면 OBSAgent 가 1.8초 뒤 opause + ERROR 를 낸다.
            reporting = ccds[:-1]
            log.warning('inject: Acquisition Complete. 를 %d회만 보냅니다',
                        len(reporting))

        chips_of = dict(rawpair.CONTROLLERS)
        sent: list[str] = []
        first_at: list[float] = []
        per_frame = cfg.readout.acq_per_frame

        async def _frame_done(ctrltag: str) -> None:
            """컨트롤러 하나의 프레임이 완료됐다.

            **발신 여부와 무관하게 시차부터 잰다** -- 실기의 두 컨트롤러 시차는
            아직 실측이 없고(`acq_per_frame` 기본값을 정할 근거가 그것이다),
            창을 깨기 전에 알아야 한다.
            """
            now = time.monotonic()
            if not first_at:
                first_at.append(now)
            else:
                skew = now - first_at[0]
                if skew > cfg.readout.acq_skew_warn:
                    log.warning('컨트롤러 완료 시차가 %.2f초다 (%s) -- '
                                '[readout] acq_skew_warn=%.1f 초과.  4개가 '
                                '1.8초 안에 모여야 OBSAgent 가 opause 로 '
                                '가지 않는다', skew, ctrltag,
                                cfg.readout.acq_skew_warn)
            if not per_frame:
                return
            group = [c for c in reporting
                     if c in chips_of.get(ctrltag, ()) and c not in sent]
            for ccd in group:
                self.emit.ic_acq_complete_obs(source, ccd, final)
            for ccd in group:
                self.emit.ic_acq_complete_ics(ics, ccd)
            sent.extend(group)

        await self._readout(source, master, _frame_done)

        # 프레임별로 이미 나간 것을 빼고 나머지를 낸다.  `acq_per_frame` 이
        # 꺼져 있으면 여기서 4개가 한꺼번에 나가고, 그것이 종전 거동이다.
        rest = [c for c in reporting if c not in sent]
        for ccd in rest:
            self.emit.ic_acq_complete_obs(source, ccd, final)
        for ccd in rest:
            self.emit.ic_acq_complete_ics(ics, ccd)

        # 저장은 백그라운드로 넘긴다.  GO n 에서 프레임 N 의 Wrote 가 프레임
        # N+1 의 준비 중에 도착하는 레거시 파이프라인을 그대로 재현한다.
        #
        # 파일명은 **여기서 확정해 넘긴다.**  저장 태스크가 나중에
        # ChannelState.suffix 를 읽으면 그때는 이미 다음 프레임이 덮어쓴 뒤라
        # 프레임 1 의 영상이 프레임 2 의 번호로 저장된다 (실제로 그 버그를
        # 겪었다 -- GO 5 에서 일련번호가 4개만 나왔다).
        # 저장은 **컨트롤러 단위**, 통보는 **CCD 단위** 다 (D-010/D-011).
        # DATE-OBS 는 노출 개시 시점에 우리가 찍은 OS 시각이다 (raw spec 5.4절).
        # `stamp_iso(None)` 은 **조용히 현재 시각**을 돌려주므로 그대로 넘기면
        # exp_start 가 비었을 때 저장 시각이 DATE-OBS 로 들어간다 -- C-6 이
        # 금지한 "누락을 현재 시각으로 조용히 대체" 그 자체다.  그래서 None 을
        # 빈 문자열로 바꿔 헤더 카드를 비우고, converter 가 거부하게 한다.
        if st.exp_start is None:
            log.error('exp_start 가 없다 -- DATE-OBS 를 채울 근거가 없으므로 '
                      '카드를 비운다 (raw spec 5.0절, C-6)')
        # **밀리초까지 넣는다** (raw spec 5.4절).
        date_obs = stamp_iso_ms(st.exp_start) if st.exp_start is not None else ''
        # 노출 중 AUXSTATUS 재질의가 아직 돌고 있으면 기다린다 -- 스냅샷을
        # 먼저 뜨면 갱신이 헤더에 반영되지 않는다.  readout 뒤이므로 실제로는
        # 이미 끝나 있고, 이 await 는 결정성을 위한 것이다.
        requery = getattr(self, '_aux_requery', None)
        if requery is not None:
            await asyncio.gather(requery, return_exceptions=True)
            self._aux_requery = None
        telem = self.telem.fits_header_dict(date_obs)
        self._check_shutter_agrees_with_imagetyp(telem)
        # **`suffix` 는 이 프레임 개시 때 확정한 지역 변수를 그대로 쓴다**
        # (`next_suffix()`, INITIALIZING 국면).  구판은 여기서
        # `st.channel(ccds[0]).suffix` 를 다시 읽었는데, 그 필드는 **외부 노드가
        # 임의 문자열을 넣을 수 있는 자리**다 -- `INITIALIZE <suffix>` 는 레거시
        # 관례상 형식 검증이 없고(`cmd_initialize`, 실측상 CHA 노드가 쓴다),
        # 레거시 IC 는 점 없는 4자리를 실었다.  그 값이 프레임 중간에 들어오면
        # 파일명·번호가 그쪽으로 갈렸고, D-016 선검사의 번호 파싱까지 그 값을
        # 받게 되어 **노출 태스크가 죽는다** -- EXPSTATUS=IDLE 도 `Wrote` 도
        # 나가지 않아 OBSAgent 가 창 초과로 `opause` 에 빠진다 (규약 3장).
        # 프레임의 이름은 프레임이 정한다.

        # 이름 충돌 처리 (D-016, raw spec 2.3절) -- 쓰기 전에 후보 번호의
        # MK·NT 두 경로를 **pair 동시**로 선검사한다.  번호가 오르면 카운터를
        # 확정 번호로 동기화하고 WARNING 로그를 남긴다 (격리·개명 통보는
        # 폐지 -- 구판 `clash/`·`NAMECLSH`·fail-safe 메시지가 이 자리에 있었다).
        # 카운터가 처음 배정한 것은 `EXPID` 로 모든 파일에 남는다 (D-019).
        orig_suffix = suffix
        date_part, _, num_str = suffix.partition('.')
        # `isdigit()` 로 먼저 걸러 **선검사가 프레임을 죽이지 못하게** 한다.
        # `next_suffix()` 가 늘 `<8자리>.<6자리>` 를 주므로 평시에는 항상
        # 참이고, 어긋나면 선검사만 건너뛰고 프레임은 정상 종료 경로를 탄다
        # -- 이름이 이상한 것과 노출 통보가 사라지는 것은 피해가 다른 급이다.
        if num_str.isdigit():
            try:
                final = rawpair.resolve_pair_number(
                    cfg.paths.data_dir, st.site_code, date_part,
                    int(num_str), check=self._backend_writes_files())
            except rawpair.NumberSpaceExhausted as exc:
                # 이 규격의 **유일한 저장 실패 조건** (D-016 2항).
                log.error('%s', exc)
                self.emit.error(source, '', str(exc), st.expstatus)
                await asyncio.sleep(cfg.scaled(cfg.timing.acq_to_idle))
                st.expstatus = ExpStatus.IDLE
                if index < count:
                    self.emit.image_complete(source, index, count)
                else:
                    self.emit.idle_done(source)
                st.advance()
                return
            if final != int(num_str):
                suffix = f'{date_part}.{final:06d}'
                log.warning(
                    '파일명 충돌 -- 노출 번호를 %s -> %06d 로 올려 저장한다 '
                    '(D-016). 카운터를 확정 번호로 동기화한다', num_str, final)
                st.sync_expnum(final)
                # 채널 suffix 도 확정 번호로 맞춘다 -- 안 맞추면 `FILENAME`
                # 질의(`cmd_filename` 이 `ch.suffix` 를 읽는다)가 **충돌
                # 상대(옛 파일)의 이름**을 답한다.  `Wrote` 논리 이름은
                # 확정 suffix 를 인자로 받으므로 이미 맞다 -- 둘이 갈리면
                # 관측자 화면과 디스크가 어긋난다.
                for ccd in ccds:
                    st.channel(ccd).suffix = suffix

        # **pair 양쪽에 같은 값이 실려야 하는 것은 노출당 한 번만 뜬다**
        # (raw spec 5.9절 "반드시 동일").  컨트롤러별 저장 태스크가 각자
        # 질의하면 두 파일의 스냅샷 시각이 `write_delay + skew` 만큼 벌어져
        # 실기 백엔드에서 값이 갈린다 -- 시뮬은 고정값을 돌려주므로 **시험이
        # 통과하는 채로 실기에서만 깨지는** 부류다.  노출 메타데이터도 같은
        # 이유로 여기서 굳힌다: `_store` 는 `write_delay` 뒤에 도는데 그 사이
        # 다음 관측의 `object`/`exp` 명령이 들어오면 프레임 N 의 헤더에 프레임
        # N+1 의 값이 실린다 (`suffix` 를 넘겨 주는 것과 같은 이유, 12.10).
        snap = {
            'ctrl_info': self._backend_fact(
                'controller_info', rawpair.CONTROLLERS[0][0],
                default={'units': ()}),
            'ctrl_telem': self._backend_fact('controller_telemetry',
                                             default=None),
            # HK 는 카메라 계통 단위이고 `CCDTEMP` 도 pair 양쪽이 같은 대표
            # 센서다(견본 v1.0 에서 상이 6장에 없다) -- 그래서 대표 pair 의
            # chip 으로 한 번 읽어 양쪽에 싣는다.  대표 센서의 귀속 자체는
            # 실기 확인 항목이다 (OI-18) -- 그때 바뀌는 것은 "어느 센서인가"
            # 이고 "양쪽이 같다" 는 5.9절 규칙은 그대로다.
            'sensors': self._backend_fact(
                'sensors', rawpair.CONTROLLERS[0][0],
                rawpair.CONTROLLERS[0][1], default={}),
            'imgtype': st.imgtype,
            'objname': st.objname,
            'projid': st.projid,
            'observer': st.observer,
            'exptime': st.effective_exptime,
            'ledflash_ms': st.ledflash_ms,
        }

        for ctrltag, chips in rawpair.CONTROLLERS:
            mine = tuple(c for c in chips if c in ccds)
            if not mine:
                continue
            task = asyncio.create_task(
                self._store(ctrltag, chips, mine, source, dict(telem),
                            suffix, orig_suffix, snap),
                name=f'ics_sim.store.{ctrltag}')
            self._writers.append(task)
            self._frame_writers.append(task)
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
        """셔터를 여는 경로 (OBJECT/FLAT/SKY/DOMEFLAT)."""
        cfg, st = self.cfg, self.state
        # **DATE-OBS 는 SHOPEN 을 내는 이 시점의 OS 시각이다** (운영자 확정
        # 2026-08-12, raw spec 5.4절).  개방 지시 **직전**에 찍는다.
        #
        # 종전에는 `open_shutter()` 가 돌아온 뒤에 찍어 "셔터가 실제로 열린
        # 시각" 을 모사했는데, **실기에서는 알 수 없는 값이다** -- 셔터는 HE
        # 박스 TTL 이 구동하고 개방 완료를 알려 주는 경로가 없다(AUX 는 블레이드
        # 리밋을 읽기만 한다, DevNote 9.2.2).  ICS 가 아는 것은 자기가 지시를
        # 낸 순간뿐이므로, 그 값을 정의로 삼는다.
        #
        # 레거시와의 차이: 레거시는 `Shutter=Open` 응답을 받은 뒤(+0.15초)
        # 확정했다.  실기의 블레이드 주행은 ~5초라 이 차이가 60초 노출에서 8%가
        # 되므로, "알 수 없는 값을 모사" 하는 쪽을 버렸다.
        begin = getattr(self.backend, 'begin_exposure', None)
        if begin is not None:
            await begin(exptime, True)

        st.exp_start = utcnow()
        self.emit.emit_req(cfg.node.ic_of(master), 'SHOPEN',
                           f'{exptime:g} {source} USESTATUS')
        await self.backend.open_shutter(exptime)

        self.emit.ic_shutter_open(source, master)
        await self._aux_event('open')
        await self._relay_tcs(stamp_iso_ms(st.exp_start), ExpStatus.INTEGRATING)

        # 헤더의 셔터 상태를 **노출 중 값**으로 갱신한다 (운영자 확정 2026-08-13).
        # 프레임 개시의 AUXSTATUS 는 여기보다 8초 이상 앞서 질의되므로
        # (`initialize_ack` + `erase_sec`) 그 값은 노출과 무관하다 -- 레거시
        # 실측이 `IMAGETYP='OBJECT'`·`EXPTIME=30` 프레임에 `SHUTTER='CLOSED'` 를
        # 남긴 것이 그 증거다.
        self._aux_requery = self._spawn_aux_requery(exptime)

        tick = cfg.timing.countdown_tick_shop
        async for remaining in self._countdown(exptime, tick):
            self.emit.ic_countdown(source, master, remaining)

        await self.backend.close_shutter()
        # 셔터 닫힘 **지시** 시각 -- 로그·진단용.  `exp_start` 와 대칭으로 지시
        # 시점을 찍는다 (블레이드가 닫힌 시각은 여기서도 알 수 없다).  구판의
        # `TSHSHUT` 카드는 v1.3 미기재라 헤더에는 안 실린다 (raw spec 5.10절).
        st.exp_end = utcnow()
        self.emit.ic_shutter_closed(source, master)
        await self._aux_event('close')

    def _spawn_aux_requery(self, exptime: float):  # noqa: ANN201
        """`SHOPEN` 후 설정 시간에 `AUXSTATUS` 를 다시 질의하는 태스크.

        **백그라운드로 돌린다.**  적분 중에 기다리면 그만큼 노출이 길어진다 --
        TC 질의는 최대 `tc_query_timeout`(0.5초)까지 걸릴 수 있다.  헤더를
        만드는 `_store()` 는 readout(~30초) 뒤이므로 그때까지는 넉넉히 끝난다.

        **노출이 갱신 시점보다 짧으면 띄우지 않는다** -- 셔터가 이미 닫힌 뒤의
        값을 노출 중 값이라고 싣게 되기 때문이다.  그 경우 개시 값이 그대로
        남고, 그것도 사실이다(짧은 노출은 블레이드가 다 열리지도 않는다 --
        "이동 슬릿", `TCSAgent/tcsagent_report.md:240`).

        DARK/BIAS 는 이 경로를 지나지 않는다 -- `EXPSTATUS=INTEGRATING` 직전에
        **즉시** 갱신한다(`_run_frame`).  셔터를 열지 않으니 기다릴 것이 없다.
        """
        delay = self.cfg.timing.aux_requery_after_shopen
        if delay <= 0 or exptime <= delay:
            return None

        async def _run() -> None:
            await asyncio.sleep(self.cfg.scaled(delay))
            await self.telem.query('AUXSTATUS')
            await self._relay_aux(ExpStatus.INTEGRATING)

        # `Sequencer` 는 app 을 참조하지 않으므로 태스크를 직접 만든다.
        # 참조를 남기지 않으면 GC 가 가져갈 수 있다 -- 호출측이 보관한다.
        return asyncio.create_task(_run(), name='ics_sim.aux_requery')

    def _check_shutter_agrees_with_imagetyp(self, telem: dict) -> None:
        """AUX 가 보고한 셔터 상태가 노출 종류와 어긋나는지 (**양방향**).

        **양방향이 안전한 근거**: `SHUTTER` 는 리밋 스위치를 직접 읽은 값이 아니고
        `SHUTOP` 의 순수 함수다 (`TCSAgent/.../commands.c:4470-4620` 의 대입 쌍
        전량):

            OPENING · OPENED · CLOSING  ->  OPEN
            RELOADING · STANDBY         ->  CLOSED
            ERROR                       ->  UNKNOWN
            NC (초기값)                 ->  UNKNOWN   (comsoft.c:907-908)

        그래서 갱신 시점(`SHOPEN`+`aux_requery_after_shopen`, 현행 **1초** --
        2026-08-25 에 3초에서 내렸다)이 블레이드 주행(5초) 중간이어도
        `SHUTOP='OPENING'` -> `SHUTTER='OPEN'` 이 된다.  한때 "주행 중이라 `CLOSED`
        가 나올 수 있으니 이 방향은 검사하면 오탐" 이라고 판단했는데 **틀렸다**
        (운영자 지적, 2026-08-13).  파생표를 확인하고 양방향으로 되돌렸다.

        ⚠️ **`OPEN` 은 "완전 개방" 이 아니라 "열림 국면"** 이다 -- 개방중·개방·
        폐쇄중이 모두 `OPEN` 이다.  노출 중 어느 시점에 질의해도 셔터가 제 일을
        하고 있으면 `OPEN` 이 나온다는 뜻이고, 그래서 이 검사가 성립한다.

        `UNKNOWN` 은 AUX 가 판단 실패한 것이다 -- `OPENING`/`CLOSING`/`RELOADING`
        이 `FS_ShutOpTime + SOP_TIMEOUT` 을 넘기면 `ERROR`->`UNKNOWN` 이 되므로
        (`commands.c:4574,4590,4606`) **셔터가 걸린 신호**이고 경고 대상이다.
        `NC` 는 FS 서브시스템이 연결되지 않은 것이라 정보 없음 -- 조용히 넘긴다.
        """
        st = self.state
        got = str(telem.get('SHUTTER', '')).strip().upper()
        if not got or got == 'NC':
            return                              # 정보 없음 != 불일치
        if got == 'UNKNOWN':
            log.warning(
                'AUX 가 SHUTTER=UNKNOWN 을 보고했다 -- 셔터 동작이 '
                'FS_ShutOpTime+SOP_TIMEOUT 을 넘겨 ERROR 로 떨어졌다는 뜻이다'
                '(commands.c:4574). 이 프레임의 노출이 온전한지 확인할 것')
            return
        want = 'OPEN' if st.opens_shutter else 'CLOSED'
        if got == want:
            return
        if st.opens_shutter:
            log.warning(
                'IMAGETYP=%s 는 셔터를 여는 노출인데 AUX 가 SHUTTER=%s 를 '
                '보고했다 -- 셔터가 열리지 않았을 수 있다. 이 프레임에 빛이 '
                '들어왔는지 확인할 것 (raw spec 5.8절)', st.imgtype, got)
        else:
            log.warning(
                'IMAGETYP=%s 는 셔터를 열지 않는데 AUX 가 SHUTTER=%s 를 '
                '보고했다 -- 광 누출이거나 셔터 고장이다. 이 프레임의 '
                'dark/bias 값은 믿을 수 없다 (raw spec 5.8절)', st.imgtype, got)

    async def _aux_event(self, which: str) -> None:
        """셔터 개폐를 AUX control 서버에 알린다.

        **DARK/BIAS 는 셔터를 열지 않으므로 여기를 지나지 않는다.**  레거시의
        `SHOPEN`/`SHCLOSE` 도 셔터 경로에만 있으므로 같은 범위다.

        실패해도 노출은 계속한다 -- AUX 는 부가 경로이고, 접속이 없으면
        auxcontrol 이 경고만 남긴다.
        """
        if self.aux is None:
            return
        try:
            if which == 'open':
                await self.aux.on_shutter_open()
            else:
                await self.aux.on_shutter_close()
        except Exception as exc:  # noqa: BLE001  노출을 죽이지 않는다
            log.warning('AUX %s event failed: %s', which, exc)

    async def _integrate_dark(self, source: str, exptime: float) -> None:
        """셔터를 열지 않는 경로 (DARK/BIAS).

        ICS 가 직접 카운트다운하고, 종료도 ICS 가 알린다.  셔터를 연 적이
        없는데도 `Shutter=Closed` 로 보내는 것은 레거시 관례이며 그대로
        유지한다 -- OBSAgent 가 이걸로 CLOSING 을 밟기 때문이다(DevNote 3.2.1).
        """
        # **노출 개시를 백엔드에 알린다** (선택 훅).  셔터 노출은
        # `open_shutter(seconds)` 가 그 역할을 하지만 이 경로는 백엔드를 아예
        # 부르지 않아서, 실기 백엔드가 **적분 시간을 알 방법이 없었다** --
        # 컨트롤러가 적분을 재는 구조(labtest 가 검증한 방식)를 쓸 수 없었다.
        # 속성이 없는 백엔드(시뮬)는 종전대로 돈다.
        begin = getattr(self.backend, 'begin_exposure', None)
        if begin is not None:
            await begin(exptime, False)

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

    async def _readout(self, source: str, master: str,
                       on_frame=None) -> None:  # noqa: ANN001
        """master 의 진행률을 sourceID 에게만 보고한다.

        진행률은 백엔드가 yield 한다.  시뮬은 [readout] 설정대로, 실기는
        컨트롤러가 보고하는 값을 그대로 흘려보낸다 -- 이 코드는 안 바뀐다.

        Args:
            on_frame: 컨트롤러 하나의 프레임이 완료될 때 부를 코루틴
                (`await on_frame(ctrltag)`).  주면 백엔드의 선택 훅
                `readout_events()` 를 쓰고, 훅이 없는 백엔드에서는 종전
                경로로 떨어진다 (`readout()`).
        """
        final = self.cfg.readout.pctread_final

        def report(pct: int) -> None:
            self.state.channel(master).pctread = pct
            self.emit.ic_pctread(source, master, pct)

        events = None
        if on_frame is not None:
            hook = getattr(self.backend, 'readout_events', None)
            if hook is not None:
                events = hook(master)
        if events is None:
            async for pct in self.backend.readout(master):
                if pct >= final:
                    break
                report(pct)
            return
        async for kind, value in events:
            if kind == 'progress':
                if int(value) < final:
                    report(int(value))
            elif kind == 'frame':
                await on_frame(str(value))

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
    #
    # 구판의 `_darktime()` 은 없앴다 -- `DARKTIME` 은 v1.3 미기재 카드다
    # (raw spec 5.10절, `EXPTIME` 파생은 하류 몫).  `st.exp_end`(셔터 닫힘
    # 지시 시각)는 로그·진단용으로 계속 찍는다.

    def _backend_writes_files(self) -> bool:
        """D-016 선검사를 할 것인가 -- **백엔드가 실제로 파일을 쓰나.**

        종전에는 `[paths] write_fits` 를 그대로 게이트로 썼는데, 그 플래그의 뜻은
        **"시뮬이 더미 FITS 를 만드는가"** 다.  실기 백엔드는 그 값과 무관하게
        항상 실파일을 쓰므로, `write_fits=false` 로 실기를 돌리면 **선검사가 꺼진
        채 실파일이 나가** 같은 이름을 조용히 덮어쓴다 -- D-016 이 막으려던 바로
        그 일이다 (`ics_archon` v0.0 검토에서 실측, 2026-08-23).

        그래서 백엔드에게 묻는다.  속성이 없는 백엔드(시험용 더미)는 종전대로
        `write_fits` 를 따른다 -- 시뮬의 거동은 한 줄도 바뀌지 않는다.
        """
        return bool(getattr(self.backend, 'writes_files',
                            self.cfg.paths.write_fits))

    def _backend_fact(self, method: str, *args, default):
        """백엔드에서 헤더용 사실을 받아 온다.  **없거나 실패하면 기본값.**

        헤더 생성은 저장 경로이지 노출 경로가 아니다.  센서 한 채널을 못 읽은
        것 때문에 프레임을 버리면 손해가 훨씬 크므로, 실패는 sentinel 로 남기고
        (규격 5.0절) 저장은 계속한다 -- "값이 없었다" 는 사실이 헤더에 남으므로
        조용한 오염이 되지 않는다.

        메서드가 아예 없는 백엔드도 허용한다 -- 시험용 더미 백엔드가 규격 5장
        전체를 구현할 이유는 없다.
        """
        fn = getattr(self.backend, method, None)
        if fn is None:
            return default
        try:
            return fn(*args)
        except Exception:                       # noqa: BLE001
            log.exception('백엔드 %s() 실패 -- 헤더는 sentinel 로 채우고 저장은 '
                          '계속한다 (규격 5.0절)', method)
            return default

    async def _store(self, ctrltag: str, chips: tuple[str, str],
                     reporting: tuple[str, ...], source: str,
                     telem: dict, suffix: str, orig_suffix: str,
                     snap: dict) -> None:
        """컨트롤러 하나의 FITS 저장(**파일 1개**) + CCD 단위 `Wrote` 발신.

        **저장 단위와 통보 단위가 갈라진다** (D-010/D-011, DevNote 3.2).
        파일은 `<SITE>.<날짜>.<번호>.<MK|NT>.fits` 하나이고, `Wrote` 는 그
        파일이 담은 chip 마다 하나씩 **레거시 형식의 논리 이름**(`KMTN<c>.…`)
        으로 낸다.  OBSAgent 는 논리 이름만 보므로 무개정이다.

        레거시는 IC -> CB TRANSFER DISK<n> / REQ SWAP / ACK SWAP 핸드셰이크로
        디스크 링을 돌렸지만, 신규는 단일 저장 경로다(DevNote 6.2) -- 취합
        서버와 기기제어를 한 PC 에 통합해 NFS 전송시간을 감당할 필요가 없어졌기
        때문이다.  바깥으로 나가는 `Wrote` 규약만 유지한다.

        Args:
            ctrltag: `MK` 또는 `NT`.
            chips: 이 파일이 담는 chip, X 낮은 쪽부터.
            reporting: 그중 실제로 통보할 chip (설정에서 빠진 CCD 제외).
            telem: 노출 하나분 TC 중계 카드 (`telemetry.fits_header_dict()`).
            suffix: **확정된** `<YYYYMMDD>.<NNNNNN>` -- D-016 선검사를 거친
                값이다.  이름 결정은 `_frame` 몫이고 여기서는 수령만 한다
                (통합 문서 Part 2 §3).  다시 계산하면 파이프라인된 다음
                프레임의 번호를 집어 온다 (12.10 에서 실제로 겪은 경합).
            orig_suffix: 카운터가 처음 배정한 suffix -- `EXPID` 의 근거
                (D-019.  구 `ORIGNAME` 을 대체한다).
                충돌이 없었으면 `suffix` 와 같다.
            snap: **노출당 한 번 굳힌** pair 공통 사실 -- 백엔드 3계약 결과와
                노출 메타데이터.  여기서 다시 질의·조회하지 않는 것이 5.9절
                "반드시 동일" 의 구조적 보장이다 (`_frame` 의 주석 참고).
        """
        cfg, st = self.cfg, self.state
        lock = self._write_lock.setdefault(ctrltag, asyncio.Lock())
        async with lock:
            # 파일 시차는 그 파일이 담은 chip 중 가장 늦은 쪽을 따른다 --
            # 레거시의 CCD별 저장 시차(N->T->M->K)를 컨트롤러 단위로 접은 것.
            skew = max(cfg.timing.skew_of(c) for c in chips)
            await asyncio.sleep(cfg.scaled(cfg.timing.write_delay + skew))

            # **실효 사이트는 `state.site_code` 다** -- IP 판정이 ini 를 이긴다
            # (D-015, raw spec 2.2절).  구판은 여기서 `cfg.node.telid`(ini
            # 원값)를 읽었는데, 그러면 판정이 ini 와 다를 때 관측일 경계는
            # 판정값(`st.obs_date()`)을 쓰면서 파일명 `<SITE>` 와 `OBSERVAT` 는
            # ini 값이 되어 **한 파일 안에서 사이트가 갈렸다** -- 기동 배너가
            # 찍는 파일명 예시(`st.site_code` 기준)와도 어긋났다.
            site = st.site_code
            path = rawpair.physical_path(cfg.paths.data_dir, site, suffix,
                                         ctrltag)

            # 헤더 = TC 중계 카드(telem)를 바닥에 깔고 rawhdr 블록을 얹은
            # 값 풀 -> `rawcards.render()` 템플릿 조립.  구판의 "겹침 런타임
            # 검사"는 템플릿이 대체한다 -- 템플릿에 없는 와이어 키는 카드로
            # 새지 못하고, 카드 순서·comment 는 견본 v1.0 과 바이트 단위로
            # 같다 (raw spec 5장 머리말).
            cards = rawhdr.spec_cards(
                ctrltag=ctrltag, site_code=site,
                backend_name=getattr(self.backend, 'name', ''),
                ics_build=st.ics_build,
                # pair 공통 사실은 `_frame` 이 굳힌 스냅샷에서 온다 (5.9절)
                ctrl_info=snap['ctrl_info'],
                ctrl_telem=snap['ctrl_telem'],
                sensors=snap['sensors'],
                cfg_site=cfg.site_for(site),
                # ICS INI 출처 카드의 ini 오버라이드 (운영자 지시 2026-08-22)
                cfg_camera=cfg.camera.as_dict(),
                cfg_ctrl=cfg.controllers.overrides(),
                rdmode=cfg.controllers.rdmode,
                telem_cards=telem,
                date_obs=str(telem.get('DATE-OBS', '')),
                # 노출 메타데이터도 스냅샷에서 -- live state 를 읽으면 다음
                # 관측의 object/exp 명령이 이 프레임 헤더에 실린다
                exptime=snap['exptime'],
                ledflash_ms=snap['ledflash_ms'],
                imgtype=snap['imgtype'], objname=snap['objname'],
                projid=snap['projid'], observer=snap['observer'],
                # FILENAME = 실제 저장명 · EXPID = 카운터 최초 배정 식별자.
                # 충돌 신호 = 두 값의 불일치 (D-016).
                filename=rawpair.name_stem(site, suffix, ctrltag),
                # `EXPID` 는 **컨트롤러 태그를 붙이지 않는다** -- pair 양쪽이
                # 같은 값을 싣고 그것이 짝을 잇는 키가 된다 (D-019, 5.9절).
                expid=rawpair.exposure_id(site, orig_suffix))

            try:
                rate = await self.backend.write_frame(ctrltag, chips, path,
                                                      cards)
            except BackendError as exc:
                self.emit.error(source, '', str(exc), st.expstatus)
                return

            for ccd in reporting:
                if (cfg.behavior.injecting('wrote_drop')
                        and ccd == cfg.node.master):
                    log.warning('inject: %s 의 Wrote 를 일부러 누락시킵니다', ccd)
                    continue
                logical = rawpair.logical_path(cfg.paths.data_dir, ccd, suffix)
                st.channel(ccd).last_file = logical
                # 레거시는 XIS PING/PONG 왕복을 저장 완료 타이밍 신호로
                # 재활용했다.  신규는 내부 콜백이라 그 편법이 필요 없지만,
                # IC 계층이 내던 'Disk Write Complete' 는 형태를 유지한다
                # (OBSAgent 는 무시한다).
                self.emit.ic_disk_write_complete(cfg.node.ics_id, ccd)
                # RATE 는 그 파일의 측정값을 두 통보에 **동일하게** 싣는다 --
                # CCD 별로 나누지 않는다 (DevNote 3.2).
                self.emit.cb_wrote(cfg.node.ics_id, ccd, logical, rate)
                # OBSAgent 가 실제로 세는 것은 이 중계다.
                self.emit.wrote_relay(source, logical, rate, st.expstatus)

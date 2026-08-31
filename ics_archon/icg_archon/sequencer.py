#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide 노출 상태기 -- frame-transfer 연속 독출 (raw spec v1.9 10.1절).

science `ics_sim.sequencer.Sequencer` 를 상속하지 않는다 -- 그쪽은
INITIALIZING→ERASE→INTEGRATING(셔터/암)→READOUT→저장(pair) 상태기이고,
guide 의 노출 의미론은 그 틀에 없다:

* 셔터가 없다 -- 노출 경계는 **독출 개시**다.
* `go n` = **n+1 독출 · 첫 독출 폐기 · n장 저장** (10.1-2·3).
* `EXPTIME` = 연속 두 독출 개시의 간격 -- **호스트가 절대 시각으로 주기를
  만든다** (`IntMS=0` 트리거, 근거는 `backend.py` 머리말).
* `DATE-OBS` = **직전 독출 개시 시각** (10.1-4) -- 폐기 프레임의 트리거
  시각이 첫 저장 프레임의 `DATE-OBS` 가 된다.
* 프레임마다 파일 1개 + 노출 번호 증가 (10.1-6).

메시지 규약은 자유 재설계 영역이다 (OBSAgent 가 guide 발신을 무시한다 --
icg_legacy_report 7.3절).  그래도 `ics_sim.emitter` 의 위생 규칙(커맨드워드
슬롯·본문 검증)은 그대로 쓴다 -- 오염을 재발명하지 않는 것이 요점이다.

TC 질의는 **사이클 개시 전 1회 스냅샷**이다 (guide OI-23 의 초안 = 레거시
계승 -- ICG 는 GO 접수 직후 질의해 곧바로 썼다, icg_legacy_report 5.3절).
`go n` 의 n장이 같은 TCS/AUX 값을 공유한다 -- 확정은 OI-23 몫.
"""

from __future__ import annotations

import asyncio
import logging
import time

from ics_archon import _simpath

_simpath.ensure()

from ics_sim.state import ExpStatus, stamp_iso_ms, utcnow  # noqa: E402

from . import guidecards, guidehdr, guidepair  # noqa: E402
from .backend import GuideBackendError  # noqa: E402
from .config import IcgCfg  # noqa: E402

log = logging.getLogger('icg_archon.seq')


def _ascii(text: object) -> str:
    """와이어로 나가는 문구는 ASCII 다 (science 백엔드와 같은 이유)."""
    return str(text).encode('ascii', 'replace').decode('ascii')


class GuideSequencer:
    """`go [n]` 한 사이클의 오케스트레이션.

    `ics_sim.commands.Dispatcher` 가 기대하는 표면(`busy`/`start`/
    `stop_integration`/`cancel`)을 그대로 내서 명령 처리부를 무개정으로
    재사용한다.
    """

    def __init__(self, cfg, icfg: IcgCfg, state, emit, telem,  # noqa: ANN001
                 backend, hk) -> None:  # noqa: ANN001
        self.cfg = cfg
        self.icfg = icfg
        self.st = state
        self.emit = emit
        self.telem = telem
        self.backend = backend
        self.hk = hk
        self._task: asyncio.Task | None = None
        self._writers: list[asyncio.Task] = []
        self._stop_evt = asyncio.Event()
        self._aborted_by = ''

    # -- Dispatcher 표면 ------------------------------------------------------

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def integrating(self) -> bool:
        """guide 는 사이클 내내 '적분 중' 이다 (독출 사이가 곧 노출)."""
        return self.busy

    def start(self, count: int, source: str) -> None:
        self._stop_evt.clear()
        self._aborted_by = ''
        self._task = asyncio.get_running_loop().create_task(
            self._run(max(int(count), 1), source))

    def stop_integration(self, requester: str) -> bool:
        """STOP -- 진행 중 프레임까지 저장하고 나머지를 포기한다."""
        if not self.busy:
            return False
        log.info('STOP by %s -- 현재 프레임까지 저장하고 멈춘다', requester)
        self._stop_evt.set()
        return True

    def cancel(self, *, save: bool, requester: str) -> bool:
        """ABORT -- 사이클을 끊는다.  **이미 fetch 를 마친 저장은 끝낸다**
        (되돌릴 수 없는 프레임을 버리는 쪽보다 낫다 -- 대기 표만 버린다)."""
        if not self.busy:
            return False
        self._aborted_by = requester
        self.backend.drop_pending('ABORT by %s' % requester)
        self._task.cancel()
        return True

    async def wait(self) -> None:
        """시험 하네스용 -- 사이클과 저장이 다 끝날 때까지."""
        if self._task is not None:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.drain_writers(None)

    async def drain_writers(self, timeout: float | None) -> None:
        """저장 태스크를 곱게 기다린다 (종료 경로 -- `app.stop`)."""
        pending = [w for w in self._writers if not w.done()]
        self._writers = [w for w in self._writers if not w.done()]
        if not pending:
            return
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True), timeout)
        except asyncio.TimeoutError:
            log.error('저장 태스크 %d개가 %s초 안에 안 끝났다 -- 취소한다',
                      len(pending), timeout)
            for w in pending:
                w.cancel()

    # -- 사이클 ---------------------------------------------------------------

    async def _run(self, count: int, source: str) -> None:
        st = self.st
        try:
            exptime = float(st.exptime)
            if exptime < self.icfg.exptime_min:
                # guide 에서 `EXPTIME=0` 은 실현 불가다 (독출 간격이 0 일 수
                # 없다 -- raw_fits_spec/SMC_CLAUDE 대사 5항).  하한은
                # PROVISIONAL (독출 실측 전).
                self.emit.error(
                    source, 'GO',
                    'Invalid guide EXPTIME=%g -- minimum %g sec '
                    '(readout-start interval, raw spec 10.1)' %
                    (exptime, self.icfg.exptime_min), st.expstatus)
                st.expstatus = ExpStatus.IDLE
                self.emit.idle_done(source)
                return

            # TC 스냅샷 -- 사이클 개시 전 1회 (OI-23 초안).  실패해도 노출은
            # 계속한다 (telemetry 가 sentinel 을 만든다).
            self.emit.exp_status(source, st.expstatus)
            aux_q = asyncio.ensure_future(self.telem.query('AUXSTATUS'))
            tcs_q = asyncio.ensure_future(self.telem.query('TCSSTATUS'))
            try:
                await self.backend.prepare()
            except Exception as exc:  # noqa: BLE001 -- 접속·ACF·전원 실패
                log.error('guide 준비 실패 -- %s', exc)
                aux_q.cancel()
                tcs_q.cancel()
                self.emit.error(source, 'GO',
                                'Failed to initialize guide controller',
                                st.expstatus)
                st.expstatus = ExpStatus.IDLE
                self.emit.idle_done(source)
                return
            await asyncio.gather(aux_q, tcs_q, return_exceptions=True)

            interval = self.cfg.scaled(exptime)
            st.expstatus = ExpStatus.INTEGRATING
            self.emit.exp_status(source, st.expstatus)

            base = time.monotonic()
            t_prev = None            # 직전 독출 개시 (UTC) -- DATE-OBS 원천
            saved = 0
            for k in range(count + 1):
                target = base + k * interval
                while True:
                    left = target - time.monotonic()
                    if left <= 0 or self._stop_evt.is_set():
                        break
                    await asyncio.sleep(min(left, 0.2))
                if self._stop_evt.is_set():
                    log.info('STOP -- %d/%d 장 저장 후 멈춘다', saved, count)
                    break

                orig_suffix = '' if k == 0 else st.next_suffix()
                trig_utc = utcnow()
                ticket = await self.backend.trigger_frame(
                    queue=k > 0, suffix=orig_suffix)

                st.expstatus = ExpStatus.READOUT
                async for pct in self.backend.wait_frame(ticket):
                    self.emit.status(source, 'PCTREAD=%d' % pct,
                                     cmdword='GO')

                if k == 0:
                    # 첫 프레임 폐기 (10.1-2) -- fetch 없이 완료만 확인.
                    await self.backend.discard_frame(ticket)
                else:
                    self._dispatch_store(source, orig_suffix,
                                         t_prev, exptime, k, count)
                    saved += 1
                    st.advance()
                t_prev = trig_utc
                if k < count:
                    st.expstatus = ExpStatus.INTEGRATING

            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(source)
        except GuideBackendError as exc:
            log.error('guide 사이클 실패 -- %s', exc)
            st.expstatus = ExpStatus.ERROR
            self.emit.error(source, 'GO', _ascii(exc), st.expstatus)
            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(source)
        except asyncio.CancelledError:
            # ABORT -- 요청자에게 IDLE 종결을 알린다 (science 와 같은 규칙).
            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(self._aborted_by or source)

    # -- 저장 ----------------------------------------------------------------

    def _dispatch_store(self, source: str, orig_suffix: str,  # noqa: ANN001
                        t_prev, exptime: float, index: int,  # noqa: ANN001
                        total: int) -> None:
        """이름 확정 + 헤더 조립 + 저장 태스크 발사.

        헤더 스냅샷은 **여기서**(독출 완료 직후) 굳힌다 -- 저장은 백그라운드
        라, 나중에 뜨면 다음 프레임의 값이 섞인다 (science `snap` 과 같은
        이유).
        """
        st, cfg = self.st, self.cfg
        site = st.site_code
        data_dir = cfg.paths.data_dir

        # D-016 선검사 (guide 판 -- 경로 하나).  점유로 밀리면 카운터 동기화.
        date_part, num = orig_suffix.split('.')
        final = guidepair.resolve_guide_number(
            data_dir, site, date_part, int(num))
        suffix = orig_suffix
        if final != int(num):
            log.warning('guide 이름 충돌 -- %s.%s 가 점유돼 %06d 로 민다 '
                        '(EXPID 는 최초 배정분을 유지, D-016/D-019)',
                        date_part, num, final)
            st.sync_expnum(final)
            suffix = f'{date_part}.{final:06d}'

        path = guidepair.guide_path(data_dir, site, suffix)
        # DATE-OBS = 직전 독출 개시 (10.1-4).  첫 저장 프레임은 폐기분의
        # 트리거 시각이다 -- t_prev 가 그 값이다.
        date_obs = stamp_iso_ms(t_prev) if t_prev is not None else None

        pool = guidehdr.build_pool(
            site_code=site,
            ctrl_info=self.backend.controller_info(),
            ctrl_telem=self.hk.ctrl_telemetry() if self.hk else None,
            sensors=self.hk.sensors() if self.hk else None,
            cfg_site=cfg.site_for(site),
            cfg_camera=cfg.camera.as_dict(),
            cfg_ctrl=cfg.controllers.overrides(),
            rdmode=self.backend.rdmode(),
            telem_cards=self.telem.fits_header_dict(date_obs or ''),
            date_obs=date_obs,
            exptime=exptime,
            ledflash_ms=st.ledflash_ms,
            imgtype=st.imgtype, objname=st.objname,
            projid=st.projid, observer=st.observer,
            filename=guidepair.guide_stem(site, suffix),
            expid=guidepair.exposure_id(site, orig_suffix))
        cards = guidecards.render(pool)

        self._writers.append(asyncio.get_running_loop().create_task(
            self._store(source, orig_suffix, path, cards, index, total)))

    async def _store(self, source: str, suffix: str, path: str,  # noqa: ANN001
                     cards, index: int, total: int) -> None:  # noqa: ANN001
        try:
            rate = await self.backend.write_frame(suffix, path, cards)
        except GuideBackendError as exc:
            self.emit.error(source, 'GO', _ascii(exc), self.st.expstatus)
            return
        # 소비자(gmon·ABC)를 위한 저장 통보 -- 규약 자유 구역이지만
        # 레거시 형태(`Wrote LASTFILE=… RATE=…`)를 유지한다.
        self.emit.wrote_relay(source, path, rate, self.st.expstatus)
        if total > 1:
            self.emit.status(source,
                             'Image %d of %d complete.' % (index, total))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide 노출 상태기 -- frame-transfer 연속 독출 (raw spec v1.9 10.1절).

science `ics_sim.sequencer.Sequencer` 를 상속하지 않는다 -- 그쪽은
INITIALIZING→ERASE→INTEGRATING(셔터/암)→READOUT→저장(pair) 상태기이고,
guide 의 노출 의미론은 그 틀에 없다:

* 셔터가 없다 -- 노출 경계는 **독출 개시**다.
* `go n` = **n+1 독출 · 첫 독출 폐기 · n장 저장** (10.1-2·3).
* `EXPTIME` = 연속 두 독출 개시의 간격 -- **시퀀서가 주기를 만든다**
  (`Exposures=n+1` 을 한 번 걸고 `IntMS = EXPTIME - 하한`, 운영자 확정
  2026-08-31.  근거·계산은 `backend.py` 머리말과 `acftiming`).
  하한보다 짧게 요청하면 **하한으로 눌러 담고** 헤더에는 실현값을 싣는다.
* `DATE-OBS` = **직전 독출 개시 시각** (10.1-4) -- 폐기 프레임의 트랜스퍼
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
import os
import time
from datetime import timedelta

from ics_archon import _simpath

_simpath.ensure()

from ics_sim.state import ExpStatus, stamp_iso_ms, utcnow  # noqa: E402

from . import guidecards, guidehdr, guidepair  # noqa: E402
from .backend import GuideBackendError  # noqa: E402
from .config import IcgCfg  # noqa: E402
from .guidepair import NumberSpaceExhausted  # noqa: E402

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
        #: **저장을 한 줄로 세운다** (2026-08-31 교차검토).  guide 는
        #: 컨트롤러가 **한 대**라 저장 둘이 겹치면 같은 링크에서 `LOCKn` 이
        #: 교차한다 -- 앞 프레임의 `LOCK0`(전체 해제)이 뒤 프레임의 잠금을
        #: 풀어, 덮임 방어와 재대조가 둘 다 무의미해지고 **두 노출이 섞인
        #: 픽셀**이 정상 길이·정상 헤더로 나온다.  science 는 저장이 태그별
        #: 다른 컨트롤러라 이 자리가 없다.
        #: ⚠️ 대기가 생기면 그것이 곧 "주기가 저장보다 짧다" 는 신호다 --
        #: 경고로 남겨 `exptime_min` 실측(DevNote 9.2)의 자료로 쓴다.
        self._store_gate = asyncio.Semaphore(1)

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
        st.exposing = True     # STATUS `Mode=Acquiring` · EXPNUM 창의 근거
        try:
            requested = float(st.exptime)
            # **하한 아래는 눌러 담는다 -- 거부하지 않는다** (운영자 확정
            # 2026-08-31).  하한은 하드웨어가 만들 수 있는 가장 짧은 독출
            # 개시 간격이고(`acftiming`: NoIntMS + 트랜스퍼 + 독출), 그보다
            # 짧게 요청하면 그냥 그 값이 된다.
            #
            # ⚠️ 그때 헤더 `EXPTIME` 은 **요청값이 아니라 실현값**이다 --
            # 10.1-1 이 이 카드를 "연속 두 독출 개시의 간격" 으로 정의하므로
            # 못 만든 주기를 적으면 카드가 거짓말이 된다.
            floor = self.backend.frame_floor()
            intms = self.backend.intms_for(requested)
            exptime = self.backend.effective_exptime(requested)
            if exptime > requested + 1e-6:
                log.info('EXPTIME %g s 는 하한 %.3f s 보다 짧다 -- 하한으로 '
                         '담는다 (헤더에는 실현값 %.3f s 를 싣는다)',
                         requested, floor, exptime)
                st.exptime = exptime

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

            st.expstatus = ExpStatus.INTEGRATING
            self.emit.exp_status(source, st.expstatus)

            t_prev = None            # 직전 트랜스퍼(=독출 개시) -- DATE-OBS
            prev_mono = None         # 실현 간격 계측용 (단조 시계)
            saved = 0
            armed = False
            ticket = None
            # **트리거 시각 != 트랜스퍼 시각이다.**  시퀀서는 프레임마다
            # `IntUnit(IntMS)` + `NoIntUnit(NoIntMS)` 를 돌린 **뒤에**
            # 트랜스퍼하고, 그 트랜스퍼가 곧 독출 개시다 (10.1-4·5).  그
            # 지연을 안 더하면 `DATE-OBS` 가 그만큼 이르고 10.5절 6번
            # 불변식이 계통적으로 어긋난다.
            # ⚠️ 독출과 노출은 별개로 흐른다 -- frame-transfer 라 독출
            # 중에도 image 는 적분하고, 저장 프레임의 노출 개시는 *직전*
            # 트랜스퍼다.  그래서 아래가 t_prev 를 `DATE-OBS` 로 쓴다.
            # ⚠️ PROVISIONAL -- ACF 계산값이다, 첫 구동에서 실측과 대조할 것.
            xfer_lag = timedelta(
                seconds=self.backend.trigger_to_transfer(intms))

            for k in range(count + 1):
                if self._stop_evt.is_set():
                    log.info('STOP -- %d/%d 장 저장 후 멈춘다', saved, count)
                    break

                orig_suffix = '' if k == 0 else st.next_suffix()
                if not armed:
                    # ⭐ **한 번만 건다** -- `Exposures = n+1` 이면 시퀀서가
                    # 유휴 없이 연달아 찍는다 (타이밍 스크립트 `GOTO Start`
                    # 뒤 `Exposures` 가 남아 있으면 곧바로 `Exposure:`).
                    # 첫 프레임은 폐기분이라 저장 대기열에 넣지 않는다.
                    ticket = await self.backend.arm_sequence(
                        count + 1, intms, suffix=orig_suffix, queue=False)
                    armed = True
                else:
                    # 이후 프레임은 **표만** 잇는다 (`LOADPARAMS` 없음).
                    ticket = await self.backend.next_ticket(
                        ticket, intms, suffix=orig_suffix, queue=True)

                # 이 프레임의 트랜스퍼 시각 = 지금(적분 개시) + 지연.
                xfer_utc = utcnow() + xfer_lag
                now_mono = time.monotonic()
                # **실현 간격 감시** (10.5절 6번 불변식의 취득 시점 판).
                # 시퀀서가 주기를 만들지만 호스트가 그것을 **재서 확인**한다 --
                # 원인을 가정하지 않는 안전망이고, 첫 구동의 실현 주기 실측
                # 자료다 (경위는 DevNote 9.12 갱신 · 9.15).  허용 편차는 PROVISIONAL.
                if prev_mono is not None:
                    achieved = now_mono - prev_mono
                    if achieved > exptime * 1.05 + 0.1:
                        log.warning(
                            '독출 개시 간격이 밀렸다 -- 실현 %.3fs, 지시 '
                            '%.3fs (프레임 %d/%d).  원인 미상 -- 첫 구동 실측 '
                            '항목.  헤더 EXPTIME 은 지시값이므로 이 프레임의 '
                            '10.5절 6번 불변식이 깨진다',
                            achieved, exptime, k, count)
                prev_mono = now_mono

                st.expstatus = ExpStatus.READOUT
                async for pct in self.backend.wait_frame(ticket):
                    self.emit.status(source, 'PCTREAD=%d' % pct,
                                     cmdword='GO')

                if k == 0:
                    # 첫 프레임 폐기 (10.1-2) -- fetch 없이 완료만 확인.
                    # ⚠️ **표는 그대로 들고 간다** -- 다음 표의 기준선이다.
                    await self.backend.discard_frame(ticket, release=False)
                else:
                    self._dispatch_store(source, orig_suffix,
                                         t_prev, exptime, k, count)
                    saved += 1
                    st.advance()
                t_prev = xfer_utc
                if k < count:
                    st.expstatus = ExpStatus.INTEGRATING

            if self._stop_evt.is_set() and armed:
                # 남은 연속 노출을 끊는다 -- 안 끊으면 시퀀서가 계속 찍고
                # 그 프레임들을 아무도 안 가져간다 (버퍼만 돈다).
                await self.backend.stop_sequence()

            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(source)
        except GuideBackendError as exc:
            log.error('guide 사이클 실패 -- %s', exc)
            st.expstatus = ExpStatus.ERROR
            self.emit.error(source, 'GO', _ascii(exc), st.expstatus)
            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(source)
        except NumberSpaceExhausted as exc:
            # D-016 의 유일한 저장 실패 조건 -- 규격이 ERROR 를 명한다
            # (2.3절 2항, 9.2절 준용).  문구는 ASCII 고정(원문은 한글).
            log.error('%s', exc)
            st.expstatus = ExpStatus.ERROR
            self.emit.error(source, 'GO',
                            'Exposure number space exhausted -- not saving '
                            '(D-016)', st.expstatus)
            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(source)
        except asyncio.CancelledError:
            # ABORT -- 요청자에게 IDLE 종결을 알린다 (science 와 같은 규칙).
            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(self._aborted_by or source)
        except Exception:  # noqa: BLE001 -- 최후 안전망
            # 여기 오면 우리 결함이다 -- 그래도 **조용히 죽지 않는다**:
            # 통보 없이 태스크만 죽으면 expstatus 가 그 국면에 고착되고
            # 가이딩 클라이언트가 영원히 기다린다.
            log.exception('guide 사이클이 예상 밖 예외로 죽었다')
            st.expstatus = ExpStatus.ERROR
            self.emit.error(source, 'GO', 'Internal error in guide sequencer',
                            st.expstatus)
            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(source)
        finally:
            st.exposing = False

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
            backend_name=getattr(self.backend, 'name', ''),
            telem_cards=self.telem.fits_header_dict(date_obs or ''),
            date_obs=date_obs,
            exptime=exptime,
            ledflash_ms=st.ledflash_ms,
            imgtype=st.imgtype, objname=st.objname,
            projid=st.projid, observer=st.observer,
            filename=guidepair.guide_stem(site, suffix),
            expid=guidepair.exposure_id(site, orig_suffix))
        cards = guidecards.render(pool)

        # 완료분을 걸러낸다 -- 밤새 연속 가이딩(수만 프레임)에서 Task 참조가
        # 무한히 쌓이는 것을 막는다 (science `_writers` 정리와 같은 자리).
        self._writers = [w for w in self._writers if not w.done()]
        self._writers.append(asyncio.get_running_loop().create_task(
            self._store(source, orig_suffix, path, cards, index, total)))

    async def _store(self, source: str, suffix: str, path: str,  # noqa: ANN001
                     cards, index: int, total: int) -> None:  # noqa: ANN001
        # 컨트롤러 한 대에 fetch 하나만 -- `_store_gate` 주석 참조.
        if self._store_gate.locked():
            log.warning('저장이 겹친다 -- 앞 프레임의 fetch·기록이 트리거 '
                        '주기를 넘겼다 (%s 대기).  EXPTIME 을 늘리거나 저장 '
                        '경로를 봐야 한다', os.path.basename(path))
        async with self._store_gate:
            await self._store_locked(source, suffix, path, cards, index, total)

    async def _store_locked(self, source: str, suffix: str, path: str,  # noqa: ANN001
                            cards, index: int, total: int) -> None:  # noqa: ANN001
        try:
            rate = await self.backend.write_frame(suffix, path, cards)
        except GuideBackendError as exc:
            if self._aborted_by:
                # ABORT 의 `drop_pending` 과 이 태스크의 `take_ticket` 이
                # 경합하면 'No pending' 이 나온다 -- 의도된 폐기이지 결함이
                # 아니므로 IDLE 통보 뒤에 낙오 ERROR 를 흘리지 않는다.
                log.info('ABORT 뒤 저장 포기 -- %s (%s)', path, exc)
                return
            self.emit.error(source, 'GO', _ascii(exc), self.st.expstatus)
            return
        # 소비자(gmon·ABC)를 위한 저장 통보 -- 규약 자유 구역이지만
        # 레거시 형태(`Wrote LASTFILE=… RATE=…`)를 유지한다.
        self.emit.wrote_relay(source, path, rate, self.st.expstatus)
        if total > 1:
            self.emit.status(source,
                             'Image %d of %d complete.' % (index, total))

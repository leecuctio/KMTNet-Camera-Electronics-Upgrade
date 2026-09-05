#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide 노출 상태기 -- frame-transfer 연속 독출 (raw spec v1.9 10.1절).

science `ics_sim.sequencer.Sequencer` 를 상속하지 않는다 -- 그쪽은
INITIALIZING→ERASE→INTEGRATING(셔터/암)→READOUT→저장(pair) 상태기이고,
guide 의 노출 의미론은 그 틀에 없다:

* 셔터가 없다 -- 노출 경계는 **독출 개시**다.
* `go n` = **flush 1회 + 독출 n회 · n장 저장** (10.1-2·3, R2613+).
* `EXPTIME` = 연속 두 독출 개시의 간격 -- **시퀀서가 주기를 만든다**
  (`Exposures=n` 을 한 번 걸고 `IntMS = EXPTIME - 하한`, 운영자 확정
  2026-08-31.  근거·계산은 `backend.py` 머리말과 `acftiming`).
  하한보다 짧게 요청하면 **하한으로 눌러 담고** 헤더에는 실현값을 싣는다.
* `DATE-OBS` = **직전 `FrameShift` 개시 시각** (10.1-4) -- 첫 저장 프레임은 flush
  `FrameShift` 개시(≈ arm 의 LOADPARAMS 시각, 표의 `armed_utc`)다.
* 프레임마다 파일 1개 + 노출 번호 증가 (10.1-6).
* **ABORT / `EXPENABLE OFF` 는 사이클을 그 자리에서 끊고 CCD 를 비운다** (운영자
  2026-09-05): `backend.abort_flush()` = `Exposures=0`·`FirstFlush=1` LOADPARAMS →
  **`RESETTIMING`** → 코어가 `Start:` 에서 `FlushFrame` 으로.  적분을 마저 하지 않고
  디지타이징도 하지 않으며 **프레임이 나오지 않는다** -- 꼬리 배수 대신 flush 한
  바퀴(`flush_duration()` + 여유)를 기다린 뒤 IDLE 이다 (`_settle`).  **STOP 은
  종전대로** 현재 프레임을 저장하고 `Exposures=0` + 꼬리 배수다 (`_drain_tail`).

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

#: 꼬리 소화의 홉 상한.  ⭐ 종전 2 는 **모자랐다** -- 해제가 늦게 닿으면
#: "해제 전 완료분" 이 두 번 나올 수 있고, 그때 둘째 홉에서 무조건 돌아가
#: IDLE 뒤에 프레임이 한 장 더 나왔다 (격리 8회 중 1~2회 재현).  상한은
#: 폭주 방지용이고, 실제 종료 판정은 `_tail_is_quiet()` 가 한다.
_MAX_TAIL_HOPS = 3

#: 로그 문구용 -- "꼬리가 둘/셋/넷".  ⚠️ 시험이 이 문구로 두 홉 경로를 확인한다
#: (`test_two_frame_tail_is_drained_when_disarm_lands_late`) -- 지우지 말 것.
_HOP_WORD = ('둘', '셋', '넷')

#: abort flush 뒤 IDLE 까지의 여유 [s] -- `backend.flush_duration()`(ACF 계산값, 실기
#: ≈1.25 s) 위에 더한다.  RESETTIMING 응답 → 코어 `Start:` → `FlushFrame` → `IF
#: Exposures`(0) 로 유휴까지의 셈 오차를 덮는 값이고, 프레임이 안 나오므로 관측으로
#: 닫을 수 없어 시간으로 잰다 (`_await_flush`).  ⚠️ `cfg.scaled` 를 **안 탄다** --
#: 시뮬 축이 아니라 실기 허용 오차다 (가짜의 flush 도 실시간으로 돈다).
_FLUSH_SETTLE_MARGIN = 0.5


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
        #: `_disarm()` 이 띄운 해제 왕복 -- abort flush(`RESETTIMING`) 또는
        #: `Exposures=0`.  두 번째 취소(ABORT 위에 종료)가 겹치면 `wait()` 가
        #: 이것을 기다려야 POWEROFF·링크 종료가 그 앞을 지나가지 않는다 (9.15-(9)).
        self._disarm_fut: asyncio.Future | None = None
        #: 꼬리 소화 태스크(STOP · abort flush 실패 대체 경로) -- `wait()` 가
        #: 기다린다 (고아 방지).
        self._drain_fut: asyncio.Future | None = None
        #: 뒷정리(해제·flush 대기·꼬리 소화) 중 -- 이때의 두 번째 ABORT 는 무시한다
        #: (종료의 `cancel()` 만 통과).  같은 사이클을 두 번 끊을 일은 없다.
        self._settling = False
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
        self._disarm_fut = None
        self._drain_fut = None
        self._settling = False
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
        """ABORT(와 `EXPENABLE OFF`, 종료) -- 사이클을 **그 자리에서** 끊는다.

        진행 중 프레임은 `RESETTIMING` 으로 끊기고 CCD 는 `FlushFrame` 으로 비워진다
        (`_settle` -- 운영자 2026-09-05).  그 프레임은 나오지 않는다.  **이미
        fetch 를 마친 저장은 끝낸다** (되돌릴 수 없는 프레임을 버리는 쪽보다 낫다
        -- 대기 표만 버린다).
        """
        if not self.busy:
            return False
        if self._settling and requester != 'shutdown':
            # ⭐ 이미 세우는 중이다 -- 두 번째 ABORT 로 뒷정리(해제·꼬리 소화)를
            # 끊으면 꼬리가 고아로 남아 다음 GO 의 기준선을 오염시킨다 (2차
            # 반증).  받아 준 것으로 답하고 그대로 둔다.  종료(shutdown)만 통과.
            # 다만 IDLE 통보는 **마지막 요청자**에게 간다 -- 그래야 `DONE: ABORT`
            # 가 약속한 `EXPSTATUS=IDLE` 을 그 클라이언트가 받는다 (3차 반증).
            log.info('ABORT by %s -- 이미 세우는 중이라 그대로 둔다', requester)
            self._aborted_by = requester
            return True
        self._aborted_by = requester
        self.backend.drop_pending('ABORT by %s' % requester)
        self._task.cancel()
        return True

    async def wait(self, *, drain: bool = True) -> None:
        """사이클 · 해제 왕복(· 저장)이 다 끝날 때까지 (`app.stop()` · 시험 하네스).

        `drain=False` 면 저장 태스크는 기다리지 않는다 -- `app.stop()` 이 그렇게
        불러 **상한 있는** `drain_writers(shutdown_drain)` 을 따로 밟는다 (3차
        반증: 무조건 `wait()` 가 무한 `drain_writers(None)` 을 타면 `[icg]
        shutdown_drain` 이 아무것도 묶지 못했다).

        ⚠️ `_task` 자체의 대기에는 상한이 없다 -- 종료가 `prepare()` 의 ACF 적용
        중에 오면 `_locked_thread` 가 스레드를 끝까지 기다리므로 최악 `T_APPLY`
        (60 s)까지 걸릴 수 있다.  취소-안전 락의 대가이고, 링크 시한이 상한이다.
        """
        if self._task is not None:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        for fut in (self._disarm_fut, self._drain_fut):
            if fut is not None and not fut.done():
                # ABORT 위에 종료(두 번째 취소)가 겹쳤을 때 -- `Exposures=0`
                # 왕복(과 소화 태스크)이 끝나기를 여기서 기다려야 `app.stop()`
                # 의 POWEROFF·링크 종료가 그 앞을 지나가지 않는다.
                await asyncio.wait({fut}, timeout=10.0)
        if drain:
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
        # ⭐ 컨트롤러에 `Exposures=n` 이 걸렸나 / 사이클이 곱게 끝났나.
        # `try` **밖**에서 만든다 -- `prepare()` 중 ABORT 가 와도 `finally` 가
        # 이름을 찾아야 한다.  `clean` 이 아니면서 `armed` 면 컨트롤러가 아직
        # 돌고 있다는 뜻이라 `finally` 가 `Exposures=0` 을 건다 (9.15-(9)).
        armed = False
        clean = False
        ticket = None          # 마지막으로 기다린 표 -- 꼬리 프레임 소화의 기준선
        intms = 0
        try:
            requested = float(st.exptime)
            # **하한 아래는 눌러 담는다 -- 거부하지 않는다** (운영자 확정
            # 2026-08-31).  접는 기준은 **운영 하한** `exptime_min`(기본 1.3 s,
            # 운영자 확정 2026-09-05 -- 하드웨어 하한 위 여유)이고, IntMS 의 뺄셈은
            # 그대로 **하드웨어 하한**(`acftiming`: NoIntMS + 트랜스퍼 + 독출)이다
            # -- `backend.intms_for/effective_exptime` 이 둘을 가른다.
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

            # ── R2613+: go n = flush 1회 + 독출 n회 · n장 저장 (규격 10.1-2·3).
            # 코어가 `FirstFlush=1` 을 보고 IntUnit 없이 곧바로 FrameShift 하므로
            # **그 개시 순간이 첫 저장 프레임의 적분 개시 = DATE-OBS** 다 (10.1-4).
            # 호스트가 아는 가장 가까운 시각은 arm 의 LOADPARAMS 왕복 **중점**
            # (표의 `armed_utc`, 링크 스레드 안에서 찍힘 -- 11.31).
            # 이후 프레임의 DATE-OBS = 직전 프레임의 FrameShift 개시 = 직전 프레임의
            # **완료 관측** − (transfer + 독출).  ⚠️ 완료 관측은 폴링 지연(frame_poll)
            # 만큼 늦다 -- 그만큼 DATE-OBS 가 늦는 편향이 있다 (예측 폴링은 후속).
            t_prev = None            # 직전 FrameShift **개시** -- 다음 프레임의 DATE-OBS
            t_arm_mono = None
            prev_done_mono = None    # 완료 관측 간격 (실현 주기 감시)
            saved = 0
            fs_to_done = self.backend.frameshift_to_done()
            flush_dur = self.backend.flush_duration()
            floor = self.backend.frame_floor()

            stopped = False
            for k in range(count):
                if self._stop_evt.is_set():
                    log.info('STOP -- %d/%d 장 저장 후 멈춘다', saved, count)
                    stopped = True
                    break

                orig_suffix = st.next_suffix()
                if not armed:
                    # ⭐ **한 번만 건다** -- `Exposures=n` + `FirstFlush=1` 을 한 LOADPARAMS 로.
                    # 시퀀서가 flush 뒤 유휴 없이 n 장을 연달아 찍는다.  ⚠️ 걸기 **전에**
                    # 표시한다 -- LOADPARAMS 직후 ABORT 가 들어오면 컨트롤러는 이미 돌고
                    # 있는데 표시가 없으면 아무도 안 세운다.
                    armed = True
                    ticket = await self.backend.arm_sequence(
                        count, intms, flush=True, suffix=orig_suffix, queue=True)
                    t_arm_mono = getattr(ticket, 'armed_mono', None)
                    if t_arm_mono is None:
                        t_arm_mono = time.monotonic()
                    armed_utc = getattr(ticket, 'armed_utc', None)
                    if armed_utc is not None:
                        # epoch -> 우리 시계 (datetime import 없이): 지금에서 경과분을 뺀다.
                        t_prev = utcnow() - timedelta(seconds=max(time.time() - armed_utc, 0.0))
                    else:
                        t_prev = utcnow()
                else:
                    # 이후 프레임은 **표만** 잇는다 (`LOADPARAMS` 없음).
                    ticket = await self.backend.next_ticket(
                        ticket, intms, suffix=orig_suffix, queue=True)

                st.expstatus = ExpStatus.READOUT
                async for pct in self.backend.wait_frame(ticket):
                    self.emit.status(source, 'PCTREAD=%d' % pct, cmdword='GO')
                done_mono = time.monotonic()
                done_utc = utcnow()

                # 가드는 **하드웨어 타이밍 모델이 있을 때만** 건다 -- 실기(R2615)는 늘
                # 있고, 스크립트 없는 시험 ACF 나 대역은 모델이 없어 기준이 없다
                # (ini 하한 2.0 s 를 그대로 쓰면 ms 로 도는 가짜의 첫 장을 다 버린다).
                if k == 0 and getattr(self.backend, 'timing', None) is not None:
                    # ⛔ 낯선 꼬리 프레임 가드 (11.31): 엔진은 arm 뒤 flush + IntMS + 하한
                    # 전에는 첫 프레임을 **못** 만든다.  그보다 일찍 온 것은 직전 블록의
                    # 꼬리다 -- Exposures=n 이 된 뒤로는 그것이 폐기분이 아니라 **첫 저장
                    # 프레임**이 되어 남의 픽셀이 정상 헤더로 저장되므로 여기서 버린다.
                    earliest = flush_dur + intms / 1000.0 + floor - 0.2
                    hops = 0
                    while done_mono - t_arm_mono < earliest and hops < 2:
                        log.error('첫 프레임이 arm 뒤 %.2fs 에 왔다 (최소 %.2fs) -- 직전 '
                                  '블록의 꼬리로 보고 버린다', done_mono - t_arm_mono,
                                  earliest)
                        await self.backend.discard_frame(ticket, release=False)
                        ticket = await self.backend.next_ticket(
                            ticket, intms, suffix=orig_suffix, queue=True)
                        async for pct in self.backend.wait_frame(ticket):
                            self.emit.status(source, 'PCTREAD=%d' % pct, cmdword='GO')
                        done_mono = time.monotonic()
                        done_utc = utcnow()
                        hops += 1

                # **실현 주기 감시** -- 완료 관측 **간격**으로 (표 잇는 시각이 아니다,
                # 11.31: 그러면 첫 간격이 flush 만큼 늘어 매 GO 거짓 경고가 났다).  첫
                # 완료는 기준만 세운다.  원인을 가정하지 않는 안전망이고 첫 구동의 실현
                # 주기 실측 자료다 (DevNote 9.12 · 9.15).  허용 편차는 PROVISIONAL.
                if prev_done_mono is not None:
                    achieved = done_mono - prev_done_mono
                    if achieved > exptime * 1.05 + 0.1:
                        log.warning(
                            '독출 완료 간격이 밀렸다 -- 실현 %.3fs, 지시 %.3fs (프레임 '
                            '%d/%d).  원인 미상 -- 첫 구동 실측 항목.  DATE-OBS 는 완료 '
                            '관측에서 되짚으므로 이 프레임의 10.5절 6번은 그대로 성립',
                            achieved, exptime, k + 1, count)
                prev_done_mono = done_mono

                self._dispatch_store(source, orig_suffix, t_prev, exptime, k + 1, count)
                saved += 1
                st.advance()
                # 이 프레임의 FrameShift 개시 = 완료 관측 − (transfer + 독출) -> 다음 DATE-OBS.
                t_prev = done_utc - timedelta(seconds=fs_to_done)
                if k < count - 1:
                    st.expstatus = ExpStatus.INTEGRATING

            if stopped and armed:
                # 남은 연속 노출을 끊는다 -- 안 끊으면 시퀀서가 계속 찍고
                # 그 프레임들을 아무도 안 가져간다 (버퍼만 돈다).  ⚠️ 이벤트가
                # 아니라 `stopped` 로 가른다 -- 마지막 프레임 중에 STOP 이 와서
                # 루프가 자연히 끝났으면 컨트롤러는 이미 멈췄고 꼬리도 없다
                # (2차 반증: 그때 소화를 기다리면 IDLE 이 3초 넘게 늦었다).
                self._settling = True
                await self.backend.stop_sequence()
                # `Exposures=0` 은 **현재 프레임까지** 찍는다 -- 그 꼬리가 끝날
                # 때까지 busy 를 유지한다 (안 그러면 다음 GO 가 그 꼬리를 제
                # 첫 프레임으로 안다, 9.15-(9)).
                await self._drain_tail(ticket, intms)
            clean = True          # 자연 종료(Exposures 소진) 또는 STOP 해제 완료

            st.expstatus = ExpStatus.IDLE
            # STOP 뒷정리 중에 ABORT 가 왔으면 IDLE 은 그 요청자에게 (3차 반증).
            self.emit.idle_done(self._aborted_by or source)
        except GuideBackendError as exc:
            log.error('guide 사이클 실패 -- %s', exc)
            clean = await self._settle(armed, clean, ticket, intms,
                                       '사이클 실패', drain=True)
            st.expstatus = ExpStatus.ERROR
            self.emit.error(source, 'GO', _ascii(exc), st.expstatus)
            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(source)
        except NumberSpaceExhausted as exc:
            # D-016 의 유일한 저장 실패 조건 -- 규격이 ERROR 를 명한다
            # (2.3절 2항, 9.2절 준용).  문구는 ASCII 고정(원문은 한글).
            log.error('%s', exc)
            clean = await self._settle(armed, clean, ticket, intms,
                                       '번호 고갈', drain=True)
            st.expstatus = ExpStatus.ERROR
            self.emit.error(source, 'GO',
                            'Exposure number space exhausted -- not saving '
                            '(D-016)', st.expstatus)
            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(source)
        except asyncio.CancelledError:
            # ABORT -- **먼저 컨트롤러를 세우고**(RESETTIMING + flush, 그 flush 가
            # 끝나기를 기다림), 그 다음 IDLE 을 알린다.  순서를 바꾸면 IDLE 을 들은
            # GO 가 busy 에 막히거나 아직 도는 flush 위에 LOADPARAMS 를 얹는다
            # (9.15-(9) · 10.1-7).  종료(shutdown)면 flush 는 안 기다린다 --
            # POWEROFF 가 뒤따른다.
            clean = await self._settle(armed, clean, ticket, intms,
                                       'ABORT by %s' % (self._aborted_by or source),
                                       drain=(self._aborted_by != 'shutdown'))
            # 뒷정리 **뒤에** 정한다 -- 그 사이 다른 클라이언트의 ABORT 가 요청자를
            # 바꿨을 수 있다 (3차 반증).
            who = self._aborted_by or source
            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(who)
        except Exception:  # noqa: BLE001 -- 최후 안전망
            # 여기 오면 우리 결함이다 -- 그래도 **조용히 죽지 않는다**:
            # 통보 없이 태스크만 죽으면 expstatus 가 그 국면에 고착되고
            # 가이딩 클라이언트가 영원히 기다린다.
            log.exception('guide 사이클이 예상 밖 예외로 죽었다')
            clean = await self._settle(armed, clean, ticket, intms,
                                       '내부 오류', drain=True)
            st.expstatus = ExpStatus.ERROR
            self.emit.error(source, 'GO', 'Internal error in guide sequencer',
                            st.expstatus)
            st.expstatus = ExpStatus.IDLE
            self.emit.idle_done(source)
        finally:
            if armed and not clean:
                # ⭐ 안전망 -- 핸들러 안에서 또 예외가 났을 때만 여기 온다.
                # 어느 길로 나가든 컨트롤러에 걸린 `Exposures=n` 은 **그대로
                # 돈다** (2026-09-02 확인, DevNote 9.15-(9)).  안 세우면 아무도 안
                # 받는 프레임이 버퍼를 돌고, 다음 `go` 의 `LOADPARAMS` 가 도는
                # 시퀀스 위에 덧써진다.  `app.stop()` 도 같은 `cancel()` 을 타므로
                # 종료 뒤 컨트롤러가 계속 찍는 것도 이 줄이 막는다.  여기서는
                # flush 를 기다리지 않는다 -- 안전망이고, 실패한 핸들러가 무엇을
                # 이미 보냈는지 모른다 (RESETTIMING 은 겹쳐 보내도 해가 없다).
                await self._disarm(self._aborted_by or source,
                                   flush=self._cycle_started(ticket))
            st.exposing = False

    async def _settle(self, armed: bool, clean: bool, ticket, intms: int,  # noqa: ANN001
                      why: str, *, drain: bool) -> bool:
        """비정상 종료(ABORT · `EXPENABLE OFF` · 사이클 실패 · 번호 고갈 · 내부
        오류)의 공통 뒷정리 -- **사이클을 끊고 CCD 를 비운 뒤** 조용해지길 기다린다.

        운영자 2026-09-05: *"노출 중 EXPENABLE=False 나 abort 시에 리드아웃은
        진행해서 CCD 를 비우는 것이 좋아 … 디지타이징 필요 없이 비우기만 하는
        skipline"*.  그래서 `backend.abort_flush()` 다 -- `Exposures=0`·`FirstFlush=1`
        LOADPARAMS → **`RESETTIMING`** → 설정 메모리 `FirstFlush=0` 되쓰기.  진행 중
        적분·독출은 그 자리에서 끊기고(버퍼 미완료, 프레임 번호 불변) 코어는 `Start:`
        에서 `FlushFrame` 으로 뛰어 CCD 를 비운 뒤 `IF Exposures`(0) 로 유휴가 된다.
        **프레임이 나오지 않으므로 꼬리 배수가 없다** -- 대신 flush 한 바퀴를
        시간으로 기다린다 (`_await_flush`).  그 뒤가 IDLE 이라야 10.1-7 의 "그 뒤는
        조용하다" 가 선다.

        `abort_flush` 를 못 보내면(링크·거부) 경고하고 종전 `Exposures=0`
        (`stop_sequence`) 으로 물러난다 -- 그때는 진행 중 프레임이 끝까지 클록되므로
        종전대로 꼬리를 배수한다 (`_drain_tail`).

        **예외 경로도 같은 길이다** (판단 2026-09-05).  `GuideBackendError`(프레임
        시한·건너뜀) · 번호 고갈 · 내부 오류 뒤에도 남은 사이클과 진행 중 프레임은
        어차피 저장하지 않으므로, 컨트롤러가 살아 있으면 RESETTIMING 으로 끊고
        비우는 것이 맞다 -- 특히 프레임 시한은 호스트가 프레임 추적을 잃은 것이라
        `Exposures=0`(현재 장까지 찍고 멈춤)보다 코어를 첫 줄로 되돌리는 쪽이
        확실하다.  링크가 죽어서 난 예외면 `abort_flush` 도 `stop_sequence` 도 못
        보내고 경고만 남는다 -- 같은 실패, 같은 결과라 갈라 볼 이유가 없다.
        반대 논거: 사이클 실패의 원인이 컨트롤러 쪽 이상이면 RESETTIMING 뒤 flush 가
        실제로 돌았는지 호스트는 확인할 길이 없다(프레임이 없으니 관측이 없다).
        그래도 안 보내는 것보다 나쁘지 않고, 다음 GO 의 `FirstFlush=1` 이 한 번 더
        비운다.

        **종료(shutdown)가 겹치면** 해제 왕복(RESETTIMING)은 shield 로 끝까지
        보내되 flush 는 기다리지 않는다 -- POWEROFF 가 뒤따르고, 그 전에 진행 중
        프레임을 끊어 둔 것으로 충분하다 (종전 "꼬리는 안 기다린다" 와 같은 규칙).
        판정은 **여기서** 다시 한다 -- 해제 도중 `_aborted_by` 가 shutdown 으로
        바뀌었을 수 있다 (핸들러 진입 때의 값은 낡았다).

        arm 의 `LOADPARAMS` 가 나가기 **전에** 취소됐으면 컨트롤러는 유휴다 -- 끊을
        사이클이 없으므로 flush 도 걸지 않고 `Exposures=0` 으로 설정 메모리만
        되돌린다 (다음 GO 가 `FirstFlush=1` 로 어차피 비운다).  기다리면 flush 한
        바퀴를 헛되이 쓴다 (3차 반증의 "꼬리 없음" 과 같은 자리).

        `clean` 을 돌려준다 -- `finally` 의 안전망이 두 번 해제하지 않도록.
        """
        if not armed or clean:
            return clean
        self._settling = True
        started = self._cycle_started(ticket)
        flushed = await self._disarm(why, flush=started)
        if not drain or self._aborted_by == 'shutdown':
            return True
        if flushed:
            await self._await_flush()
        elif started:
            # abort flush 를 못 보내 `Exposures=0` 으로 물러났다 -- 진행 중 프레임이
            # 끝까지 클록되므로 종전대로 꼬리를 배수한다.
            await self._drain_tail(ticket, intms)
        else:
            log.info('LOADPARAMS 가 나가기 전에 취소됐다 -- 컨트롤러는 유휴, 끊을 '
                     '사이클도 꼬리도 없다')
        return True

    def _cycle_started(self, ticket) -> bool:  # noqa: ANN001
        """arm 의 `LOADPARAMS` 가 컨트롤러에 닿았나 -- 끊을 사이클이 있는지의 근거.

        표가 있으면 `trigger()` 가 돌아온 것이고, 표 없이 취소됐어도 `loadparams_sent`
        가 참이면 ack 를 (곧) 받은 것이다 (`_locked_thread` 가 스레드를 끝까지
        기다리므로).
        """
        return ticket is not None or bool(self.backend.loadparams_sent())

    async def _abort_flush_or_stop(self) -> bool:
        """`abort_flush()` -- 실패하면 경고 후 종전 `stop_sequence()` 로.  `True` 면
        RESETTIMING 이 나갔다(프레임이 안 나온다), `False` 면 `Exposures=0` 경로다
        (진행 중 프레임은 끝까지 클록된다)."""
        try:
            await self.backend.abort_flush()
            return True
        except GuideBackendError as exc:
            log.warning('abort flush 를 못 보냈다 -- %s.  종전 Exposures=0 으로 '
                        '물러난다 (진행 중 프레임은 끝까지 클록되고 꼬리를 배수한다)',
                        exc)
            await self.backend.stop_sequence()
            return False

    async def _disarm(self, why: str, *, flush: bool) -> bool:
        """컨트롤러를 세운다 -- 취소·예외 경로용.  `True` 면 abort flush 가 나갔다.

        `flush=True`: `backend.abort_flush()` -- 진행 중 사이클을 `RESETTIMING` 으로
        끊고 `FlushFrame` 으로 CCD 를 비운다 (프레임 없음).  못 보내면 경고 후 종전
        `Exposures=0`(`stop_sequence`) 으로 물러나고 `False` 다.
        `flush=False`: `Exposures=0` 만 -- arm 의 `LOADPARAMS` 가 안 나간 경우다
        (끊을 사이클이 없고, `trigger()` 가 WCONFIG 만 써 둔 `Exposures=n`·
        `FirstFlush=1` 을 설정 메모리에서 되돌린다).

        `asyncio.shield` 로 감싼다: ABORT 로 취소된 태스크 안에서 부르므로
        종료(`stop()`)가 겹쳐 **두 번째 취소**가 와도 왕복은 끊기지 않는다 --
        그 미래를 `_disarm_fut` 에 두고 `wait()` 가 기다린다 (안 그러면 고아가
        되어 POWEROFF·링크 종료가 앞질러 갈 수 있다).  abort flush 는 왕복이
        다섯(WCONFIG×2 · LOADPARAMS · RESETTIMING · WCONFIG)이라 더더욱 -- 중간에
        끊기면 `FirstFlush=1` 이 설정 메모리에 남아 다음 LOADPARAMS 가 유령 flush
        를 되살린다 (11.31).  실패는 경고로 남긴다 (링크가 죽었으면 어차피
        컨트롤러도 못 세운다).  ⚠️ 왕복 자체가 취소에 안전한 것은
        `ArchonController._locked_thread` 덕이다 -- 취소된 명령의 스레드가
        소켓을 놓기 전에 이 왕복이 끼어들면 응답 번호가 어긋난다.
        """
        if flush:
            log.info('사이클을 끊고 CCD 를 비운다 (%s) -- RESETTIMING + FlushFrame', why)
            fut = asyncio.ensure_future(self._abort_flush_or_stop())
        else:
            log.info('연속 노출을 끊는다 (%s) -- Exposures=0', why)
            fut = asyncio.ensure_future(self.backend.stop_sequence())
        self._disarm_fut = fut
        # 고아가 돼도(아무도 안 기다려도) 실패를 삼키지 않는다.
        fut.add_done_callback(
            lambda f: None if f.cancelled() or f.exception() is None else
            log.warning('해제 왕복이 뒤늦게 실패했다 -- %s', f.exception()))
        try:
            return bool(await asyncio.shield(fut))
        except asyncio.CancelledError:
            # 두 번째 취소(종료) -- 왕복은 계속 간다; `wait()` 가 미래를 기다린다.
            # 결과를 모르니 `False` -- 종료가 뒤따르므로 flush 대기는 어차피 없다.
            return False
        except Exception as exc:  # noqa: BLE001
            log.warning('컨트롤러를 세우지 못했다 -- %s (남은 프레임이 더 나올 '
                        '수 있다)', exc)
            return False

    async def _await_flush(self) -> None:
        """abort flush 가 끝나기를 기다린다 -- 프레임이 안 나오므로 **시간으로** 잰다.

        RESETTIMING 뒤 코어는 `Start:` → `FlushFrame`(≈ `flush_duration()`, ACF
        계산값 실기 ≈1.25 s) → `IF Exposures`(0) 유휴다.  관측할 프레임이 없어
        `_drain_tail` 의 번호 관찰을 쓸 수 없고, 호스트가 코어 위치를 물을 길도
        없다 -- 계산값에 여유(`_FLUSH_SETTLE_MARGIN`)를 더해 잔다.  그 뒤가 IDLE
        이라야 10.1-7 의 "그 뒤는 조용하다" 가 선다 (IDLE 을 들은 GO 의 LOADPARAMS
        가 도는 flush 위에 얹히지 않는다).

        종료(두 번째 취소)가 겹치면 대기를 접는다 -- POWEROFF 가 뒤따른다.
        대기 표는 여기서 한 번 더 버린다 -- RESETTIMING 이 끊은 프레임을 기다리는
        표가 있어도 그 프레임은 오지 않는다 (`cancel()` 과 `reset_timing()` 이 이미
        버렸으니 보통은 0 이다).
        """
        hold = self.cfg.scaled(self.backend.flush_duration()) + _FLUSH_SETTLE_MARGIN
        self.backend.drop_pending('abort flush -- 끊긴 프레임은 오지 않는다')
        log.info('flush 가 끝나기를 %.2fs 기다린다 -- 그 뒤 IDLE', hold)
        try:
            await asyncio.sleep(hold)
        except asyncio.CancelledError:
            log.info('종료가 겹쳤다 -- flush 대기를 접는다 (POWEROFF 가 뒤따른다)')

    async def _tail_is_quiet(self, done: int, period: float) -> bool:
        """프레임 번호가 **한 주기 동안 안 늘면** 엔진이 멈춘 것이다.

        ⭐ `Exposures=0` 은 *"지금 물고 있는 장까지"* 찍고 멈추는데, **그 장이
        완료되기 전에는 번호가 안 늘어** 밖에서 "멈췄다" 와 구별되지 않는다.
        그래서 마지막 완료 뒤 한 주기를 **관찰**한다 -- 늘면 아직 도는 것이고,
        안 늘면 꼬리가 끝난 것이다.

        ⚠️ 값을 못 읽으면 **"조용하다" 로 본다** -- 링크가 이미 죽었으면 더
        기다려도 얻을 것이 없고, 여기서 막히면 IDLE 이 영영 안 온다.
        """
        deadline = time.monotonic() + period * 1.2
        while time.monotonic() < deadline:
            await asyncio.sleep(min(period / 4.0, 0.25))
            try:
                now = await self.backend.newest_frame()
            except Exception as exc:  # noqa: BLE001
                log.info('꼬리 확인 중 FRAME 을 못 읽었다 -- %s (조용한 것으로 '
                         '본다)', exc)
                return True
            if now is not None and now > done:
                log.info('꼬리가 더 있다 -- 프레임 %d 가 더 나왔다', now)
                return False
        return True

    async def _drain_tail(self, ticket, intms: int) -> None:  # noqa: ANN001
        """`Exposures=0` 은 **현재 프레임까지** 찍고 멈춘다 -- 그 꼬리가 끝날
        때까지 `busy` 를 유지한다 (9.15-(9), 반증자 지적).

        ⭐ 이 길을 타는 것은 **STOP** 과 abort flush 를 못 보낸 대체 경로뿐이다
        (2026-09-05) -- ABORT/`EXPENABLE OFF` 는 `RESETTIMING` 으로 끊어 프레임이
        안 나오므로 `_await_flush` 가 대신한다.

        안 기다리면 IDLE 직후 들어온 GO 가 그 꼬리를 제 **첫 저장** 프레임으로
        알아 **남의 픽셀이 정상 헤더로 저장된다** (R2613+: 폐기분이 없다 --
        `_run` 의 '너무 이른 첫 프레임' 시간 가드가 이중 안전장치다, 11.31).

        **꼬리는 관측으로 정한다** (2차 반증): 해제 직후 `FRAME` 의 최신 완료
        번호를 읽어 두고, 기다린 꼬리가 그 번호 이하면 -- 즉 해제가 닿기 전에
        이미 끝난 프레임이면 -- 엔진은 그 다음 프레임을 시작한 것이라 **한 장
        더** 기다린다.  표가 없으면(`arm_sequence` 도중 취소) 지금 `FRAME` 을
        기준선으로 표를 만든다.  대기는 **한 주기 + 2 s** 로 묶는다 -- 첫 홉이
        기다렸으면 그것이 꼬리고(≤ 한 주기), 첫 홉이 즉시 끝났으면(해제 전
        완료분) 둘째 홉이 ≤ 한 주기다.  그 이상은 꼬리가 없는 경우라 상한까지
        기다리는 헛수고다 (3차 반증 -- 종전 2주기는 그 헛수고를 두 배로 했다).
        대역(sim)은 꼬리가 없어 건너뛴다.
        """
        period = self.backend.frame_floor() + intms / 1000.0
        # ⚠️ 조용함 확인이 홉마다 한 주기를 더 쓸 수 있으므로 상한도 함께 넓힌다.
        limit = period * (_MAX_TAIL_HOPS + 1) + 2.0
        armed_mono = getattr(ticket, 'armed_mono', None)
        if ticket is not None and getattr(ticket, 'ready', None) is None \
                and armed_mono is not None:
            # R2613+: arm 표가 아직 안 익었다 = 첫 프레임이 안 나왔다.  flush 중에
            # Exposures=0 이 앉으면 flush 뒤 `IF Exposures` 가 0 이라 **프레임이 한
            # 장도 안 나온다** -- 종전 상한(≈7 s)을 헛기다리면 10.1-7 의 '최악 한
            # 주기' 가 깨진다.  엔진이 첫 프레임을 낼 수 있는 가장 늦은 시각까지만.
            flush_total = self.backend.flush_duration() + intms / 1000.0
            limit = max(0.0, armed_mono + flush_total - time.monotonic()) + period + 0.5

        async def _wait() -> None:
            newest = await self.backend.newest_frame()
            if getattr(ticket, 'ready', None) is not None:
                tail = await self.backend.next_ticket(ticket, intms, suffix='',
                                                      queue=False)
            elif ticket is not None:
                tail = ticket                        # 기다리던 그 표가 곧 꼬리
            else:
                tail = await self.backend.tail_ticket()
                if tail is None:                     # 대역 -- 꼬리 없음
                    return
            for hop in range(_MAX_TAIL_HOPS):
                async for _pct in self.backend.wait_frame(tail):
                    pass
                await self.backend.discard_frame(tail, release=True)
                done = getattr(getattr(tail, 'ready', None), 'frame', None)
                if done is None:
                    return                           # 표가 안 익었다 -- 더 볼 것이 없다
                if newest is None or done > newest:
                    # 해제 뒤에 끝난 장이다 -- **꼬리로 보인다.**
                    # ⛔ 그런데 "보인다" 로 끝내면 안 된다: 엔진이 이미 다음
                    # 장을 물고 있으면 그 장은 아직 **완료가 아니라** 번호가
                    # 안 늘어 있고, 여기서 돌아가면 IDLE **뒤에** 한 장이 더
                    # 나온다 (실측 flake -- 8회 중 1~2회).
                    # ⭐ 확실한 신호는 하나뿐이다: **한 주기 동안 번호가 안 는다.**
                    # `WBUF`·`BUFnLINES` 는 못 쓴다 -- 적분 중에도 0/None 이라
                    # "멈췄다" 와 "다음 장 적분 중" 을 못 가른다.
                    if await self._tail_is_quiet(done, period):
                        return
                    newest = done                    # 아직 돌고 있다 -- 한 장 더
                else:
                    # 해제 전에 이미 끝나 있던 장이었다 -- 엔진은 다음 장을 시작했다.
                    log.info('꼬리가 %s -- 프레임 %d 는 해제 전 완료분, 한 장 더 '
                             '기다린다', _HOP_WORD[min(hop, len(_HOP_WORD) - 1)],
                             done)
                if hop == _MAX_TAIL_HOPS - 1:
                    log.warning('꼬리를 %d홉 안에 못 닫았다 (마지막 완료 %s) -- '
                                '다음 시퀀스의 기준선이 어긋날 수 있다',
                                _MAX_TAIL_HOPS, done)
                    return
                tail = await self.backend.next_ticket(tail, intms, suffix='',
                                                      queue=False)

        task = asyncio.ensure_future(asyncio.wait_for(_wait(), limit))
        self._drain_fut = task
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            # 종료의 두 번째 취소 -- 소화를 **포기**한다 (고아로 두지 않는다).
            task.cancel()
            task.add_done_callback(lambda f: f.cancelled() or f.exception())
        except asyncio.TimeoutError:
            log.info('꼬리 프레임이 %.1fs 안에 안 끝났다 -- 이미 멈춰 있었을 것이다',
                     limit)
        except Exception as exc:  # noqa: BLE001
            log.info('꼬리 프레임 소화 생략 -- %s', exc)

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
        # DATE-OBS = 직전 FrameShift 개시 (10.1-4).  첫 저장 프레임은 flush FrameShift 개시
        # (arm 의 LOADPARAMS 시각, R2613+)이고 그 뒤는 직전 프레임 완료에서 되짚은 값 --
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

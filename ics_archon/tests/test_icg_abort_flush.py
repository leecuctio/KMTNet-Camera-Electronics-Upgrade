#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABORT / `EXPENABLE OFF` 가 사이클을 `RESETTIMING` 으로 끊고 flush 로 CCD 를 비운다.

운영자 2026-09-05: *"guide CCD 는 금방 읽기 때문에 노출 중 EXPENABLE=False 나 abort
시에 리드아웃은 진행해서 CCD 를 비우는 것이 좋아 … 디지타이징 필요 없이 비우기만
하는 skipline"*.  시퀀서 `_settle` 이 `backend.abort_flush()` 를 부른다 --
`Exposures=0`·`FirstFlush=1` LOADPARAMS → RESETTIMING → `FirstFlush=0` 되쓰기.
프레임이 안 나오므로 꼬리 배수 대신 flush 한 바퀴를 기다린 뒤 IDLE 이다.

`test_icg_backend.py` 의 하네스(가짜 컨트롤러 + `IcgArchon`) 그대로.  가짜는
`RESETTIMING` 을 안다 -- 진행 중 프레임을 그 자리에서 끊고(버퍼 미완료 · `frame_no`
불변) 마지막 LOADPARAMS 의 RAM 값(`FirstFlush=1` · `Exposures=0`)으로 flush 한
바퀴를 돈다.  `fake.resets` 가 RESETTIMING 횟수, `fake.flushes` 가 flush 횟수다.

⚠️ 가짜의 시간은 **실시간**이다 (`readout_ticks * tick`) -- 시퀀서의 flush 대기는
`cfg.scaled(flush_duration)`(0.04 s) + 여유 0.5 s 라 가짜 flush(≤0.4 s)가 그 안에
끝난다.  그래서 "IDLE 뒤가 조용하다" 를 가짜로도 볼 수 있다.
"""

from __future__ import annotations

import asyncio
import glob
import os
import time

import pytest

import ics_archon  # noqa: F401

from icg_archon.app import IcgArchon  # noqa: E402

from fake_archon import FakeArchon  # noqa: E402
import test_icg_backend as tb  # noqa: E402  -- 모듈로 들여온다 (시험 함수 재수집 방지)


def _app(tmp_path, fake, monkeypatch):  # noqa: ANN001, ANN202
    """`test_icg_backend._go_app` 과 같은 조립 + EXPENABLE 기록 경로."""
    cfg, icfg = tb.make_cfgs(tmp_path, fake)
    cfg.transport.bind_port = 0
    cfg.transport.send_gap_ms = 0
    cfg.paths.write_fits = True
    cfg.paths.expnum_file = str(tmp_path / 'icg.expnum')
    icfg.expenable_file = str(tmp_path / 'icg.expenable')
    icfg.hk.interval = 3600.0
    icfg.hk.query_aux = False
    # ⭐ 하한을 **명시**한다 -- 시험 ACF 는 타이밍 스크립트가 없어 `frame_floor()` 가
    # `exptime_min` 으로 물러나는데, `make_cfgs` 는 `IcgCfg()` 기본값을 쓴다(ini 아님).
    # 기본값이 바뀌면 `GUIDEEXP 2` 의 IntMS 가 0 이 아니게 되어 "독출 중/적분 중" 전제가
    # 조용히 어긋난다 (실제로 기본 1.3 으로 IntMS=700 이 나와 (b) 의 전제가 깨졌다).
    icfg.exptime_min = 2.0          # GUIDEEXP 2 -> IntMS 0 · GUIDEEXP 3 -> IntMS 1000
    import icg_archon.app as app_mod
    monkeypatch.setattr(app_mod, 'validate', lambda cfg, backend: [])
    return IcgArchon(cfg, icfg, backend='icg_archon')


def _files(app) -> int:  # noqa: ANN001
    return len(glob.glob(os.path.join(app.cfg.paths.data_dir, '*.G.fits')))


def _flush_budget(app) -> float:  # noqa: ANN001
    """ABORT -> IDLE 의 허용 시간: flush(scaled) + 1 s."""
    return app.cfg.scaled(app.guide.flush_duration()) + 1.0


def _loads(fake) -> list[str]:  # noqa: ANN001
    return [c for c in fake.seen if c.upper().startswith('LOADPARAMS')]


def _flush_slot(fake) -> str:  # noqa: ANN001
    return next((v for v in fake.config.values() if 'FirstFlush=' in str(v)), '')


class _Snap:
    """ABORT 직전/직후의 가짜 상태."""

    def __init__(self, fake, app) -> None:  # noqa: ANN001
        self.frame_no = fake.frame_no
        self.files = _files(app)
        self.flushes = getattr(fake, 'flushes', 0)
        self.resets = getattr(fake, 'resets', 0)
        self.wbuf = fake.wbuf


# ---------------------------------------------------------------------------
# (a) 적분 중 ABORT
# ---------------------------------------------------------------------------

def test_abort_during_integration_resets_and_flushes_without_a_frame(tmp_path, monkeypatch):  # noqa: ANN001
    """적분 중 ABORT -- RESETTIMING 1회 · flush 1회 더 · 프레임 없음 · 파일 불변 · IDLE 은
    flush(scaled) + 1 s 안."""
    fake = FakeArchon(width=tb.NX, height=tb.NY, readout_ticks=4, tick=0.05,
                      system=tb.GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        app = _app(tmp_path, fake, monkeypatch)

        async def run():  # noqa: ANN202
            await app.start()
            try:
                app.transport.feed('abc>ICG GUIDEEXP 3')     # 하한 2.0 + IntMS 1000 -- 가짜 적분 1 s
                await asyncio.sleep(0.02)
                app.transport.feed('abc>ICG go 20')
                await tb._first_wrote(app)                   # 첫 장 저장 -- 둘째 장은 적분 중
                await asyncio.sleep(0.3)
                before = _Snap(fake, app)
                assert before.wbuf == 0, '독출 중이다 -- 시험 전제(적분 중)가 깨졌다'
                t0 = time.monotonic()
                assert app.seq.cancel(save=False, requester='abc'), 'busy 가 아니다'
                await app.seq.wait()
                to_idle = time.monotonic() - t0
                after = _Snap(fake, app)
                await asyncio.sleep(0.3)                     # 그 뒤가 조용한가
                return before, after, to_idle, fake.frame_no
            finally:
                await app.stop()

        before, after, to_idle, later = asyncio.run(run())
        assert after.resets == 1, 'RESETTIMING 이 %d회' % after.resets
        assert after.flushes == before.flushes + 1, (before.flushes, after.flushes)
        assert after.frame_no == before.frame_no, '끊은 프레임이 나왔다 (%d -> %d)' % (
            before.frame_no, after.frame_no)
        assert later == before.frame_no, 'IDLE 뒤에 프레임이 더 나왔다'
        assert after.files == before.files, '끊은 프레임이 저장됐다'
        assert to_idle <= _flush_budget(app), 'IDLE 이 %.2fs -- 상한 %.2fs' % (
            to_idle, _flush_budget(app))
        # LOADPARAMS 는 arm 1 + abort_flush 1 -- 그 뒤에 RESETTIMING, 설정 메모리는 되돌려졌다.
        seen = [c.upper() for c in fake.seen]
        assert len(_loads(fake)) == 2, _loads(fake)
        last_load = max(i for i, c in enumerate(seen) if c.startswith('LOADPARAMS'))
        assert 'RESETTIMING' in seen[last_load:], seen[last_load:]
        assert fake._exposures() == 0                   # noqa: SLF001
        assert 'FirstFlush=0' in _flush_slot(fake), _flush_slot(fake)
        sent = [str(m) for m in app.transport.sent_log]
        assert any('abc' in m and 'IDLE' in m for m in sent), sent[-5:]
        assert not any('ERROR' in m for m in sent), sent[-5:]
    finally:
        fake.shutdown()


# ---------------------------------------------------------------------------
# (b) 독출 중 ABORT
# ---------------------------------------------------------------------------

def test_abort_during_readout_leaves_the_buffer_incomplete(tmp_path, monkeypatch):  # noqa: ANN001
    """독출 중 ABORT -- 같은 결과 + 쓰던 버퍼가 `complete=0` 으로 남는다 (디지타이징 안 함)."""
    fake = FakeArchon(width=tb.NX, height=tb.NY, readout_ticks=8, tick=0.05,
                      system=tb.GUIDE_SYSTEM, nbuf=3)                # 독출 0.4 s
    fake.start()
    try:
        app = _app(tmp_path, fake, monkeypatch)

        async def run():  # noqa: ANN202
            await app.start()
            try:
                app.transport.feed('abc>ICG GUIDEEXP 2')     # IntMS=0 -- 프레임이 연달아
                await asyncio.sleep(0.02)
                app.transport.feed('abc>ICG go 20')
                t_go = time.monotonic()
                await tb._first_wrote(app)
                t_wrote = time.monotonic() - t_go
                await asyncio.sleep(0.15)                    # 둘째 장 독출의 한중간
                before = _Snap(fake, app)
                assert before.wbuf != 0, (
                    '독출 중이 아니다 -- 시험 전제가 깨졌다 (첫 Wrote %.2fs, frame_no %d, '
                    'exposing %s, remaining %d, seen[-8:] %r, sent[-4:] %r)' % (
                        t_wrote, fake.frame_no, fake._exposing, fake._remaining,   # noqa: SLF001
                        fake.seen[-8:], [str(m) for m in app.transport.sent_log][-4:]))
                t0 = time.monotonic()
                assert app.seq.cancel(save=False, requester='abc')
                await app.seq.wait()
                to_idle = time.monotonic() - t0
                after = _Snap(fake, app)
                await asyncio.sleep(0.3)
                buf = dict(fake.bufs[before.wbuf - 1])
                return before, after, to_idle, fake.frame_no, buf
            finally:
                await app.stop()

        before, after, to_idle, later, buf = asyncio.run(run())
        assert after.resets == 1
        assert after.flushes == before.flushes + 1
        assert after.frame_no == before.frame_no == later
        assert after.files == before.files
        assert to_idle <= _flush_budget(app), to_idle
        assert buf['complete'] == 0, buf
        assert fake.wbuf == 0, '독출이 아직 돌고 있다'
    finally:
        fake.shutdown()


# ---------------------------------------------------------------------------
# (c) EXPENABLE OFF 가 같은 길을 탄다
# ---------------------------------------------------------------------------

def test_expenable_off_takes_the_abort_flush_path(tmp_path, monkeypatch):  # noqa: ANN001
    """`EXPENABLE OFF` = 플래그 + `cancel(save=False)` (`commands.py`) -- RESETTIMING + flush."""
    fake = FakeArchon(width=tb.NX, height=tb.NY, readout_ticks=4, tick=0.05,
                      system=tb.GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        app = _app(tmp_path, fake, monkeypatch)

        async def run():  # noqa: ANN202
            await app.start()
            try:
                app.transport.feed('abc>ICG GUIDEEXP 3')
                await asyncio.sleep(0.02)
                app.transport.feed('abc>ICG go 20')
                await tb._first_wrote(app)
                await asyncio.sleep(0.3)
                before = _Snap(fake, app)
                t0 = time.monotonic()
                app.transport.feed('abc>ICG EXPENABLE OFF')
                await asyncio.sleep(0.05)
                await app.seq.wait()
                to_idle = time.monotonic() - t0
                after = _Snap(fake, app)
                await asyncio.sleep(0.3)
                return before, after, to_idle, fake.frame_no
            finally:
                await app.stop()

        before, after, to_idle, later = asyncio.run(run())
        sent = [str(m) for m in app.transport.sent_log]
        assert any('Aborted=1' in m for m in sent), sent[-6:]
        assert not app.expenable.allowed
        assert after.resets == 1
        assert after.flushes == before.flushes + 1
        assert after.frame_no == before.frame_no == later
        assert after.files == before.files
        assert to_idle <= _flush_budget(app), to_idle
        assert any('abc' in m and 'IDLE' in m for m in sent), sent[-5:]
    finally:
        fake.shutdown()


# ---------------------------------------------------------------------------
# (d) STOP 은 종전대로
# ---------------------------------------------------------------------------

def test_stop_still_saves_the_current_frame_without_resettiming(tmp_path, monkeypatch):  # noqa: ANN001
    """STOP -- 현재 프레임 저장 · `Exposures=0` · 꼬리 배수.  RESETTIMING 은 없다."""
    fake = FakeArchon(width=tb.NX, height=tb.NY, readout_ticks=2, tick=0.05,
                      system=tb.GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        app = _app(tmp_path, fake, monkeypatch)

        async def run():  # noqa: ANN202
            await app.start()
            try:
                app.transport.feed('abc>ICG GUIDEEXP 2')
                await asyncio.sleep(0.02)
                app.transport.feed('abc>ICG go 20')
                await tb._first_wrote(app)
                before = _Snap(fake, app)
                assert app.seq.stop_integration('abc')
                await app.seq.wait()
                after = _Snap(fake, app)
                await asyncio.sleep(0.3)
                return before, after, fake.frame_no
            finally:
                await app.stop()

        before, after, later = asyncio.run(run())
        assert after.resets == 0, 'STOP 이 RESETTIMING 을 보냈다'
        assert 'RESETTIMING' not in [c.upper() for c in fake.seen]
        # 현재 프레임(들)이 저장됐다 -- 적어도 한 장은 늘어야 한다.
        assert after.files > before.files, (before.files, after.files)
        assert after.frame_no > before.frame_no, 'STOP 인데 진행 중 프레임이 끊겼다'
        assert later == after.frame_no, 'IDLE 뒤에 더 찍었다 -- 꼬리를 안 소화했다'
        assert len(_loads(fake)) == 2, _loads(fake)
        assert fake._exposures() == 0                   # noqa: SLF001
        assert after.flushes == before.flushes, 'STOP 이 flush 를 걸었다'
        sent = [str(m) for m in app.transport.sent_log]
        assert any('IDLE' in m for m in sent) and not any('ERROR' in m for m in sent), sent[-6:]
    finally:
        fake.shutdown()


# ---------------------------------------------------------------------------
# (e) ABORT 뒤 곧바로 go 2 -- 기준선 오염 없음
# ---------------------------------------------------------------------------

def test_go_right_after_abort_flush_makes_exactly_two_frames(tmp_path, monkeypatch):  # noqa: ANN001
    """IDLE 을 들은 GO 가 flush 뒤 깨끗한 기준선에서 시작한다 -- 2장 저장 · 프레임 정확히 2."""
    fake = FakeArchon(width=tb.NX, height=tb.NY, readout_ticks=4, tick=0.05,
                      system=tb.GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        app = _app(tmp_path, fake, monkeypatch)

        async def run():  # noqa: ANN202
            await app.start()
            try:
                app.transport.feed('abc>ICG GUIDEEXP 2')
                await asyncio.sleep(0.02)
                app.transport.feed('abc>ICG go 20')
                await tb._first_wrote(app)
                await asyncio.sleep(0.05)
                assert app.seq.cancel(save=False, requester='abc')
                await app.seq.wait()
                mid = _Snap(fake, app)
                app.transport.feed('abc>ICG go 2')           # 곧바로
                await asyncio.sleep(0.05)
                await app.seq.wait()
                await asyncio.sleep(0.1)
                return mid, _Snap(fake, app)
            finally:
                await app.stop()

        mid, end = asyncio.run(run())
        assert mid.resets == 1
        assert end.files - mid.files == 2, 'go 2 가 %d 장을 저장했다' % (end.files - mid.files)
        assert end.frame_no - mid.frame_no == 2, 'go 2 가 프레임을 %d 장 만들었다' % (
            end.frame_no - mid.frame_no)
        assert end.flushes == mid.flushes + 1, 'go 2 의 flush 는 정확히 한 번이다'
        assert end.resets == 1, 'go 2 가 RESETTIMING 을 보냈다'
        sent = [str(m) for m in app.transport.sent_log]
        assert not any('ERROR' in m for m in sent), sent[-6:]
    finally:
        fake.shutdown()


# ---------------------------------------------------------------------------
# (f) abort_flush 를 못 보내면 종전 Exposures=0 + 꼬리 배수로 물러난다
# ---------------------------------------------------------------------------

def test_abort_falls_back_to_exposures_zero_when_the_flush_is_refused(tmp_path, monkeypatch, caplog):  # noqa: ANN001
    """`abort_flush` 가 `GuideBackendError` 면 경고 후 `stop_sequence` + `_drain_tail`."""
    import logging

    from icg_archon import backend as be_mod
    from icg_archon.backend import GuideBackendError

    fake = FakeArchon(width=tb.NX, height=tb.NY, readout_ticks=2, tick=0.05,
                      system=tb.GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        app = _app(tmp_path, fake, monkeypatch)

        async def refused(self):  # noqa: ANN001, ANN202
            raise GuideBackendError('abort flush failed: refused (test)')

        monkeypatch.setattr(be_mod.GuideBackend, 'abort_flush', refused)

        async def run():  # noqa: ANN202
            await app.start()
            try:
                app.transport.feed('abc>ICG GUIDEEXP 2')
                await asyncio.sleep(0.02)
                app.transport.feed('abc>ICG go 20')
                await tb._first_wrote(app)
                before = _Snap(fake, app)
                with caplog.at_level(logging.WARNING, logger='icg_archon.seq'):
                    assert app.seq.cancel(save=False, requester='abc')
                    await app.seq.wait()
                after = _Snap(fake, app)
                await asyncio.sleep(0.4)
                return before, after, fake.frame_no
            finally:
                await app.stop()

        before, after, later = asyncio.run(run())
        assert any('abort flush 를 못 보냈다' in r.getMessage() for r in caplog.records)
        assert after.resets == 0
        assert 'RESETTIMING' not in [c.upper() for c in fake.seen]
        assert fake._exposures() == 0                   # noqa: SLF001
        # 종전 의미론 -- 현재 프레임은 끝까지 클록되고(≤ 한두 장) 그 뒤로는 조용하다.
        assert before.frame_no <= after.frame_no <= before.frame_no + 2
        assert later == after.frame_no, 'IDLE 뒤에 더 찍었다 -- 꼬리를 안 배수했다'
        sent = [str(m) for m in app.transport.sent_log]
        assert any('abc' in m and 'IDLE' in m for m in sent), sent[-5:]
    finally:
        fake.shutdown()


# ---------------------------------------------------------------------------
# (g) ABORT 위에 종료 -- RESETTIMING 은 POWEROFF 앞에, flush 는 기다리지 않는다
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('gap', [0.0, 0.1], ids=['at_once', 'during_flush_wait'])
def test_abort_then_shutdown_sends_resettiming_before_poweroff(tmp_path, monkeypatch, gap):  # noqa: ANN001
    """shield 덕에 abort flush 왕복은 끝까지 가고, flush 대기는 종료가 접는다.

    `gap=0` 은 두 취소가 한 CancelledError 로 합쳐지는 경우(`_disarm` 뒤 판정),
    `gap=0.1` 은 RESETTIMING 이 끝나고 `_await_flush` 가 자는 중에 종료가 오는 경우다.
    """
    fake = FakeArchon(width=tb.NX, height=tb.NY, readout_ticks=4, tick=0.05,
                      system=tb.GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        app = _app(tmp_path, fake, monkeypatch)

        async def run():  # noqa: ANN202
            await app.start()
            app.transport.feed('abc>ICG GUIDEEXP 3')
            await asyncio.sleep(0.02)
            app.transport.feed('abc>ICG go 20')
            await tb._first_wrote(app)
            await asyncio.sleep(0.2)
            assert app.seq.cancel(save=False, requester='abc')
            if gap:
                await asyncio.sleep(gap)
                assert app.seq.busy, 'flush 대기 중이어야 한다 -- 시험 전제가 깨졌다'
            t0 = time.monotonic()
            await app.stop()                             # 종료 -- 두 번째 취소
            return time.monotonic() - t0

        stop_took = asyncio.run(run())
        seen = [c.upper() for c in fake.seen]
        resets = [i for i, c in enumerate(seen) if c.startswith('RESETTIMING')]
        offs = [i for i, c in enumerate(seen) if c.startswith('POWEROFF')]
        assert len(resets) == 1, seen
        assert offs and resets[0] < offs[0], 'RESETTIMING 이 POWEROFF 뒤다: %r' % seen
        assert 'FirstFlush=0' in _flush_slot(fake), _flush_slot(fake)
        # 종료는 flush 대기(0.54 s)를 접는다 -- 그보다 훨씬 짧게 끝나야 한다.
        assert stop_took < 0.45, 'app.stop() 이 flush 대기를 기다렸다 (%.2fs)' % stop_took
    finally:
        fake.shutdown()

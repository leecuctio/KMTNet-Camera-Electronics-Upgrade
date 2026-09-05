#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GuideBackend <-> 가짜 컨트롤러 -- 실기 취득 경로의 회귀.

`test_backend.py` 의 축소 기하 수법 그대로 -- 다른 것은 **한 대**라는 점과
guide 저장(`guidecards.WIDTHS`)이다.  폐기 프레임(queue=False)이 저장 표를
남기지 않는 것, 티켓 경로(fetch·저장·버퍼 반환)가 이 시험의 몫이다.
"""

from __future__ import annotations

import asyncio
import glob
import os

import ics_archon  # noqa: F401

from ics_sim import config as simcfg  # noqa: E402

from ics_archon.archon.controller import ArchonController  # noqa: E402

from icg_archon import guidecards  # noqa: E402
from icg_archon.app import IcgArchon  # noqa: E402
from icg_archon.backend import GuideBackend  # noqa: E402
from icg_archon.config import IcgCfg  # noqa: E402

from fake_archon import FakeArchon  # noqa: E402

NX, NY = 8, 4

ACF_TEXT = """[CONFIG]
TRIGOUTFORCE=0
TRIGOUTLEVEL=1
PARAMETER0="FirstFlush=0"
PARAMETER1="Exposures=1"
PARAMETER2="IntMS=0"
"""

INI = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    os.pardir, 'icg_archon.ini'))

#: guide 구성의 가짜 SYSTEM (`MOD_PRESENT=0x37C` -- 3·4·5·6·7·9·10 장착).
GUIDE_SYSTEM = {
    'BACKPLANE_TYPE': '1', 'BACKPLANE_REV': '5',
    'BACKPLANE_VERSION': '1.0.408', 'BACKPLANE_ID': '0000000000000201',
    'MOD_PRESENT': '037C',
    'MOD1_TYPE': '0', 'MOD2_TYPE': '0', 'MOD3_TYPE': '1', 'MOD4_TYPE': '1',
    'MOD5_TYPE': '2', 'MOD6_TYPE': '2', 'MOD7_TYPE': '11', 'MOD8_TYPE': '0',
    'MOD9_TYPE': '8', 'MOD10_TYPE': '11', 'MOD11_TYPE': '0', 'MOD12_TYPE': '0',
}


def make_cfgs(tmp_path, fake: FakeArchon):  # noqa: ANN001, ANN201
    acf = tmp_path / 'guide_test.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')
    cfg = simcfg.load(INI)
    cfg.timing.time_scale = 0.02
    cfg.behavior.console = False
    cfg.paths.data_dir = str(tmp_path / 'data')

    icfg = IcgCfg()
    icfg.hosts = {'G': '127.0.0.1'}
    icfg.port = fake.port
    icfg.acf = {'G': str(acf)}
    icfg.poweron_wait = 0.0
    icfg.frame_poll = 0.01
    # 이 파일의 시간 전제(GUIDEEXP 2 = IntMS 0 · 두 홉 창 …)는 운영 하한 2.0 으로 쓰였다 --
    # 기본값이 1.3 으로 바뀐 뒤(2026-09-05)에도 그 전제를 유지한다.
    icfg.exptime_min = 2.0
    icfg.progress_step = 0
    icfg.frame_timeout = 5.0
    # 시험 기하 -- validate() 의 고정 기하 검사는 실기 배선 전용이라 여기서는
    # 부르지 않는다 (test_backend 의 축소 기하와 같은 수법).
    icfg.naxis1, icfg.naxis2 = NX, NY
    icfg.hk.log_dir = str(tmp_path / 'log')
    return cfg, icfg


def test_acquire_discard_then_save(tmp_path):
    fake = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.01,
                      system=GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        cfg, icfg = make_cfgs(tmp_path, fake)
        be = GuideBackend(cfg, icfg)

        async def run():  # noqa: ANN202
            await be.prepare()
            # 폐기 프레임 -- 저장 표를 남기지 않는다 (queue=False).
            t0 = await be.trigger_frame(queue=False)
            async for _pct in be.wait_frame(t0):
                pass
            await be.discard_frame(t0)
            # 저장 프레임.
            t1 = await be.trigger_frame(queue=True, suffix='20260831.000001')
            pcts = []
            async for pct in be.wait_frame(t1):
                pcts.append(pct)
            path = os.path.join(cfg.paths.data_dir,
                                'KMTK.20260831.000001.G.fits')
            cards = guidecards.render({})       # 값은 sentinel -- 틀만 본다
            rate = await be.write_frame('20260831.000001', path, cards)
            await be.shutdown()
            return pcts, path, rate

        pcts, path, rate = asyncio.run(run())
        assert rate >= 0 and os.path.exists(path)
        size = os.path.getsize(path)
        # 헤더 144 레코드(4x2880) + 데이터 8x4x2=64B -> 2880 패딩.
        assert size == 4 * 2880 + 2880
        blob = open(path, 'rb').read(4 * 2880)
        assert blob[:6] == b'SIMPLE'
        text = blob.decode('ascii')
        assert 'ICGBUILD' in text and 'ICSBUILD' not in text
        # 폐기분이 저장 대기열에 남아 있으면 여기 두 번째 표가 잡힌다.
        assert be.ctrl.take_ticket('') is None
        assert glob.glob(os.path.join(cfg.paths.data_dir, '*.fits')) == [path]
    finally:
        fake.shutdown()


def test_sequencer_pacing_arms_once_and_chains_tickets(tmp_path):
    """⭐ `go n` 은 `LOADPARAMS` 를 **한 번만** 낸다 (시퀀서 pacing).

    프레임마다 다시 걸면 시퀀서가 매번 유휴 루프로 돌아갔다 오므로 주기가
    호스트 지터를 탄다 -- 이 방식의 요점이 그것을 없애는 것이다.
    표는 `expect_next()` 가 왕복 하나(`FRAME`)로 이어 간다.
    """
    fake = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.01,
                      system=GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        cfg, icfg = make_cfgs(tmp_path, fake)
        be = GuideBackend(cfg, icfg)

        async def run():  # noqa: ANN202
            await be.prepare()
            seen = []
            t = await be.arm_sequence(3, 250, suffix='', queue=False)
            async for _p in be.wait_frame(t):
                pass
            await be.discard_frame(t, release=False)
            seen.append(t.ready.frame)
            for i in (1, 2):
                t = await be.next_ticket(t, 250,
                                         suffix='20260831.00000%d' % i)
                async for _p in be.wait_frame(t):
                    pass
                seen.append(t.ready.frame)
            await be.stop_sequence()
            return seen

        frames = asyncio.run(run())
        # 프레임 번호가 끊김 없이 이어져야 한다 (건너뛰면 wait_frame 이 던진다).
        assert frames == [frames[0], frames[0] + 1, frames[0] + 2]

        # `LOADPARAMS` 는 arm 1회 + stop_sequence 1회뿐이다.
        loads = [c for c in fake.seen if c.upper().startswith('LOADPARAMS')]
        assert len(loads) == 2, 'LOADPARAMS 가 %d회 -- 프레임마다 걸고 있다' % len(loads)

        # 저장 대기열에는 이름 붙은 표 둘만 (폐기분은 queue=False).
        assert be.ctrl.take_ticket('20260831.000001') is not None
        assert be.ctrl.take_ticket('20260831.000002') is not None
        assert be.ctrl.take_ticket('') is None
    finally:
        fake.shutdown()


# ---------------------------------------------------------------------------
# ABORT 가 연속 시퀀스를 세운다 (DevNote 9.15-(9), 2026-09-02)
# ---------------------------------------------------------------------------

def test_fake_exposures_is_a_live_counter_that_loadparams_rewrites():
    """가짜 충실도 -- `Exposures=0` 은 0장, 도는 중의 `Exposures=0` 은 현재 프레임까지.

    실기 시퀀서는 `LOADPARAMS` 로 파라미터가 즉시 바뀐다 (`Start:` 의 `IF Exposures`).
    종전 가짜는 루프 시작 때 한 번 읽고 0 도 한 장을 찍어 아래 시퀀서 시험이 결함을
    못 봤을 것이다.
    """
    import socket
    import time as _time

    fk = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.05,
                    system=GUIDE_SYSTEM, nbuf=3)
    fk.start()
    try:
        def cmd(c):  # noqa: ANN001, ANN202
            with socket.create_connection(('127.0.0.1', fk.port), timeout=2) as s:
                s.sendall(('>01%s\n' % c).encode('ascii'))
                return s.recv(64)

        # Exposures=0 -> LOADPARAMS 는 한 장도 안 찍는다.
        assert cmd('WCONFIG0001Exposures=0').startswith(b'<01')
        assert cmd('LOADPARAMS').startswith(b'<01')
        _time.sleep(0.3)
        assert fk.frame_no == 0, '실기는 Exposures=0 에 한 장도 안 찍는다'

        # Exposures=8 로 돌리다 Exposures=0 -- 현재 프레임까지만.
        cmd('WCONFIG0001Exposures=8')
        cmd('LOADPARAMS')
        _time.sleep(0.15)                        # 한두 장 뒤
        cmd('WCONFIG0001Exposures=0')
        cmd('LOADPARAMS')
        _time.sleep(0.3)
        n = fk.frame_no
        assert 0 < n < 8, '멈추지 않았다 (%d)' % n
        _time.sleep(0.3)
        assert fk.frame_no == n, '멈춘 뒤에 더 찍었다'
    finally:
        fk.shutdown()


def test_abort_disarms_the_running_sequence(tmp_path, monkeypatch):  # noqa: ANN001
    """⭐ ABORT 가 `Exposures=0` 을 건다 -- 컨트롤러가 `n+1` 장을 계속 찍지 않는다.

    종전에는 `cancel()` 이 대기 표만 버리고 태스크를 취소해, 컨트롤러는 걸린
    `n+1` 을 끝까지 찍었다(아무도 안 받는 프레임이 버퍼를 돈다).  다음 `go` 의
    `LOADPARAMS` 는 그 위에 덧써졌고, `app.stop()` 도 같은 길이라 **종료 뒤에도
    컨트롤러가 찍었다.**  이제 `_run()` 의 `finally` 가 `armed and not clean` 이면
    `_disarm()` 을 부른다 (DevNote 9.15-(9)).
    """
    import time as _time

    fake = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.05,
                      system=GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        cfg, icfg = make_cfgs(tmp_path, fake)
        cfg.transport.bind_port = 0
        cfg.transport.send_gap_ms = 0
        cfg.paths.write_fits = True
        cfg.paths.expnum_file = str(tmp_path / 'icg.expnum')
        icfg.hk.interval = 3600.0
        icfg.hk.query_aux = False
        # 축소 기하(8x4) 시험 -- validate() 의 고정 기하 불변식(4224x1033)은 실기
        # 배선 전용이라 여기서는 건너뛴다 (이 파일의 다른 시험이 validate 를 안
        # 부르는 것과 같은 이유).  app.py 는 이름으로 들여온다.
        import icg_archon.app as app_mod
        monkeypatch.setattr(app_mod, 'validate', lambda cfg, backend: [])
        app = IcgArchon(cfg, icfg, backend='icg_archon')

        async def run():  # noqa: ANN202
            await app.start()
            try:
                app.transport.feed('abc>ICG GUIDEEXP 2')      # IcgCfg 기본 exptime_min 은 1.3(운영 하한) -- 2.0 요청은 IntMS=700 이다 (2026-09-05)
                await asyncio.sleep(0.02)
                app.transport.feed('abc>ICG go 20')           # 21 독출 · 20 저장
                for _ in range(400):
                    if any('Wrote' in str(m) for m in app.transport.sent_log):
                        break
                    await asyncio.sleep(0.02)
                else:                                          # pragma: no cover
                    raise AssertionError('첫 저장이 안 나왔다 -- %r / %r'
                                         % ([str(m) for m in app.transport.sent_log][-6:],
                                            fake.seen[-12:]))
                assert app.seq.cancel(save=False, requester='abc'), 'busy 가 아니다'
                await app.seq.wait()
                await asyncio.sleep(0.05)
                return fake.frame_no
            finally:
                await app.stop()

        at_abort = asyncio.run(run())
        # ① 컨트롤러에 Exposures=0 이 걸렸다 -- LOADPARAMS 는 arm 1 + disarm 1.
        loads = [c for c in fake.seen if c.upper().startswith('LOADPARAMS')]
        assert len(loads) == 2, loads
        assert fake._exposures() == 0                # 슬롯 글자
        with fake._lock:
            remaining = fake._remaining
        assert remaining == 0, '슬롯은 0 인데 LOADPARAMS 가 안 먹었다 (%d)' % remaining
        # ② 실제로 멈췄다 -- 21 장을 다 찍지 않았다.  `Exposures=0` 은 **현재
        #    프레임까지** 찍고 멈추는 것이라(실기 `Start:` 의 `IF Exposures`,
        #    가짜도 같다) 취소 시점 뒤 **최대 한 장**은 더 나올 수 있다 -- 그
        #    뒤로는 늘지 않아야 한다.
        assert at_abort < 21, '취소했는데 n+1 을 다 찍었다'
        # ⭐ `seq.wait()` 가 돌아온 시점(=IDLE)에는 꼬리까지 소화돼 있다 -- 그 뒤로
        #    한 장도 늘지 않아야 한다 (안 그러면 다음 GO 의 기준선이 오염된다).
        _time.sleep(0.4)
        assert fake.frame_no == at_abort, ('IDLE 뒤에 컨트롤러가 더 찍었다 -- 꼬리를 안 '
                                           '소화했다 (%d -> %d)' % (at_abort, fake.frame_no))
        # ③ IDLE 종결은 통보됐다 (ABORT 요청자 abc 에게).
        sent = [str(m) for m in app.transport.sent_log]
        assert any('abc' in m and 'IDLE' in m for m in sent), sent[-5:]
    finally:
        fake.shutdown()


def test_cancelled_command_keeps_the_link_lock_until_the_thread_finishes(tmp_path):
    """⭐ 취소된 `cmd()` 가 락을 **스레드가 끝날 때까지** 쥔다 (2026-09-02, 반증자 재현).

    종전에는 `CancelledError` 에 `async with self._lock` 을 빠져나오며 락이 풀렸는데
    스레드는 소켓 왕복 중이었다 -- 다음 명령이 끼어들어 응답 번호가 어긋나고 링크가
    다시 세워졌다(`STATUS` 0.2초 지연으로 20회 중 14회).  ABORT 뒤 `Exposures=0`
    이 바로 그 "다음 명령" 이라 고침이 실기에서 안 먹을 수 있었다.
    """
    import time as _time

    fake = FakeArchon(width=NX, height=NY, system=GUIDE_SYSTEM, nbuf=3,
                      status_delay=0.3)
    fake.start()
    try:
        cfg, icfg = make_cfgs(tmp_path, fake)
        ctrl = ArchonController('G', icfg)

        async def run():  # noqa: ANN202
            await ctrl.connect()
            ctrl.parse_acf(icfg.acf['G'])       # set_config 의 줄 번호표 (왕복 없음)
            t0 = _time.monotonic()
            task = asyncio.ensure_future(ctrl.cmd('STATUS'))
            await asyncio.sleep(0.05)             # 스레드가 소켓 왕복에 들어간 뒤
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            waited = _time.monotonic() - t0
            # 취소가 돌아왔을 때는 이미 스레드가 끝나 락이 풀려 있다 -- 즉 0.3초
            # 지연을 **기다렸다**.
            assert waited >= 0.25, '취소가 스레드를 안 기다렸다 (%.2fs)' % waited
            assert not ctrl._lock.locked()      # noqa: SLF001
            # 곧바로 다음 명령 -- 끼어들지 않았으므로 재접속 없이 통과한다.
            await ctrl.set_exposures(0)
            await ctrl.close()

        asyncio.run(run())
        assert fake.accepts == 1, '링크가 다시 세워졌다 -- 왕복이 끼어들었다 (%d회 접속)' % fake.accepts
        assert any(c.upper().startswith('LOADPARAMS') for c in fake.seen), fake.seen
    finally:
        fake.shutdown()


def test_abort_then_shutdown_loads_exposures_zero_before_poweroff(tmp_path, monkeypatch):  # noqa: ANN001
    """ABORT 위에 종료가 겹쳐도 `Exposures=0` 이 **POWEROFF 앞에** 들어간다.

    `_disarm()` 의 shield 미래를 `wait()` 가 기다리므로 `app.stop()` 의 POWEROFF·링크
    종료가 그 왕복을 앞지르지 않는다 (9.15-(9), 반증자 지적).
    """
    fake = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.05,
                      system=GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        cfg, icfg = make_cfgs(tmp_path, fake)
        cfg.transport.bind_port = 0
        cfg.transport.send_gap_ms = 0
        cfg.paths.write_fits = True
        cfg.paths.expnum_file = str(tmp_path / 'icg.expnum')
        icfg.hk.interval = 3600.0
        icfg.hk.query_aux = False
        import icg_archon.app as app_mod
        monkeypatch.setattr(app_mod, 'validate', lambda cfg, backend: [])
        app = IcgArchon(cfg, icfg, backend='icg_archon')

        async def run():  # noqa: ANN202
            await app.start()
            app.transport.feed('abc>ICG GUIDEEXP 2')
            await asyncio.sleep(0.02)
            app.transport.feed('abc>ICG go 20')
            for _ in range(400):
                if any('Wrote' in str(m) for m in app.transport.sent_log):
                    break
                await asyncio.sleep(0.02)
            assert app.seq.cancel(save=False, requester='abc')
            # 곧바로 종료 -- 두 번째 취소(shutdown)가 ABORT 처리 위에 겹친다.
            await app.stop()

        asyncio.run(run())
        seen = [c.upper() for c in fake.seen]
        loads = [i for i, c in enumerate(seen) if c.startswith('LOADPARAMS')]
        offs = [i for i, c in enumerate(seen) if c.startswith('POWEROFF')]
        assert len(loads) == 2, seen
        assert offs and loads[-1] < offs[0], '해제 LOADPARAMS 가 POWEROFF 뒤다: %r' % seen
        with fake._lock:
            assert fake._remaining == 0
    finally:
        fake.shutdown()


def test_second_cancel_during_the_lock_wait_is_absorbed(tmp_path):
    """⭐ 두 번째 취소(ABORT 위에 종료)가 락 대기를 끊지 못한다 (2차 반증, 6회 중 3회 재현).

    `_locked_thread` 가 첫 취소를 받고 스레드를 기다리는 동안 두 번째 취소가 오면,
    종전엔 `asyncio.wait` 가 끊겨 락이 풀리고 다음 명령이 소켓에 끼어들었다.  이제
    스레드가 끝날 때까지 취소를 흡수한다.
    """
    import time as _time

    fake = FakeArchon(width=NX, height=NY, system=GUIDE_SYSTEM, nbuf=3,
                      status_delay=0.3)
    fake.start()
    try:
        cfg, icfg = make_cfgs(tmp_path, fake)
        ctrl = ArchonController('G', icfg)

        async def run():  # noqa: ANN202
            await ctrl.connect()
            ctrl.parse_acf(icfg.acf['G'])
            t0 = _time.monotonic()
            task = asyncio.ensure_future(ctrl.cmd('STATUS'))
            await asyncio.sleep(0.05)
            task.cancel()
            await asyncio.sleep(0.05)
            task.cancel()                          # 두 번째 -- 대기 중에
            try:
                await task
            except asyncio.CancelledError:
                pass
            assert _time.monotonic() - t0 >= 0.25, '두 번째 취소가 대기를 끊었다'
            assert not ctrl._lock.locked()      # noqa: SLF001
            await ctrl.set_exposures(0)
            await ctrl.close()

        asyncio.run(run())
        assert fake.accepts == 1, '링크가 다시 세워졌다 (%d회 접속)' % fake.accepts
        assert any(c.upper().startswith('LOADPARAMS') for c in fake.seen), fake.seen
    finally:
        fake.shutdown()


def _go_app(tmp_path, fake, monkeypatch):  # noqa: ANN001, ANN202
    cfg, icfg = make_cfgs(tmp_path, fake)
    cfg.transport.bind_port = 0
    cfg.transport.send_gap_ms = 0
    cfg.paths.write_fits = True
    cfg.paths.expnum_file = str(tmp_path / 'icg.expnum')
    icfg.hk.interval = 3600.0
    icfg.hk.query_aux = False
    import icg_archon.app as app_mod
    monkeypatch.setattr(app_mod, 'validate', lambda cfg, backend: [])
    return IcgArchon(cfg, icfg, backend='icg_archon')


async def _first_wrote(app) -> None:  # noqa: ANN001
    for _ in range(400):
        if any('Wrote' in str(m) for m in app.transport.sent_log):
            return
        await asyncio.sleep(0.02)
    raise AssertionError('첫 저장이 안 나왔다')  # pragma: no cover


def test_go_right_after_abort_starts_on_a_clean_baseline(tmp_path, monkeypatch):  # noqa: ANN001
    """⭐ ABORT 직후의 GO 가 꼬리 프레임을 제 것으로 알지 않는다 (9.15-(9)).

    꼬리를 소화하지 않으면 새 GO 의 폐기(k=0) 표가 이미 끝난 꼬리에 만족돼 진짜
    첫 프레임이 저장 프레임으로 올라간다 -- 그러면 `go 2` 가 프레임을 **2장**만
    더 만들고도 파일 2장을 쓴다.  깨끗한 기준선이면 3장(폐기 1 + 저장 2)이다.
    """
    fake = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.05,
                      system=GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        app = _go_app(tmp_path, fake, monkeypatch)

        async def run():  # noqa: ANN202
            await app.start()
            try:
                app.transport.feed('abc>ICG GUIDEEXP 2')
                await asyncio.sleep(0.02)
                app.transport.feed('abc>ICG go 20')
                await _first_wrote(app)
                assert app.seq.cancel(save=False, requester='abc')
                await app.seq.wait()
                files0 = len(glob.glob(os.path.join(app.cfg.paths.data_dir, '*.G.fits')))
                frames0 = fake.frame_no
                app.transport.feed('abc>ICG go 2')          # 곧바로 -- 꼬리가 남았다면 여기서 오염
                await asyncio.sleep(0.05)
                await app.seq.wait()
                await asyncio.sleep(0.1)
                files1 = len(glob.glob(os.path.join(app.cfg.paths.data_dir, '*.G.fits')))
                return files1 - files0, fake.frame_no - frames0
            finally:
                await app.stop()

        saved, produced = asyncio.run(run())
        assert saved == 2, 'go 2 가 %d 장을 저장했다' % saved
        # R2613+: flush 는 프레임을 만들지 않는다 -- go 2 = 프레임 정확히 2 (구판 3).
        assert produced == 2, 'go 2 가 프레임을 %d 장 만들었다 -- 2 이어야(flush 는 프레임을 안 만든다)' % produced
    finally:
        fake.shutdown()


def test_stop_disarms_and_drains_before_idle(tmp_path, monkeypatch):  # noqa: ANN001
    """STOP 경로 -- `Exposures=0` 한 번, 꼬리 소화 뒤 IDLE, 그 뒤로는 안 찍는다."""
    import time as _time

    fake = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.05,
                      system=GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        app = _go_app(tmp_path, fake, monkeypatch)

        async def run():  # noqa: ANN202
            await app.start()
            try:
                app.transport.feed('abc>ICG GUIDEEXP 2')
                await asyncio.sleep(0.02)
                app.transport.feed('abc>ICG go 20')
                await _first_wrote(app)
                assert app.seq.stop_integration('abc')
                await app.seq.wait()
                return fake.frame_no
            finally:
                await app.stop()

        at_idle = asyncio.run(run())
        loads = [c for c in fake.seen if c.upper().startswith('LOADPARAMS')]
        assert len(loads) == 2, loads
        assert at_idle < 21
        _time.sleep(0.4)
        assert fake.frame_no == at_idle, 'STOP 의 IDLE 뒤에 컨트롤러가 더 찍었다'
        sent = [str(m) for m in app.transport.sent_log]
        assert any('IDLE' in m for m in sent) and not any('ERROR' in m for m in sent), sent[-6:]
    finally:
        fake.shutdown()


def test_two_frame_tail_is_drained_when_disarm_lands_late(tmp_path, monkeypatch, caplog):  # noqa: ANN001
    """⭐ 해제가 닿기 전에 프레임 k 가 끝나 있었으면 k+1 이 꼬리다 -- 두 홉 (3차 반증 시험 공백).

    `stop_sequence()` 를 한 주기 넘게 늦춰 그 상황을 결정적으로 만든다.  소화가
    끝난 뒤(IDLE)에는 프레임이 더 늘지 않고, 곧 이어진 `go 2` 는 깨끗한 기준선에서
    프레임 3장을 만든다.
    """
    import logging
    import time as _time

    from icg_archon import backend as be_mod

    fake = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.05,
                      system=GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        app = _go_app(tmp_path, fake, monkeypatch)
        orig = be_mod.GuideBackend.stop_sequence

        async def late_stop(self):  # noqa: ANN001, ANN202
            await asyncio.sleep(0.15)                 # 한 주기(0.1 s) 넘게 -- k 가 끝난다
            return await orig(self)

        monkeypatch.setattr(be_mod.GuideBackend, 'stop_sequence', late_stop)

        async def run():  # noqa: ANN202
            await app.start()
            try:
                app.transport.feed('abc>ICG GUIDEEXP 2')
                await asyncio.sleep(0.02)
                app.transport.feed('abc>ICG go 20')
                await _first_wrote(app)
                # R2613+ (2026-09-05): ABORT 는 RESETTIMING + flush 라 꼬리가 없다.  '늦은 해제 뒤
                # 두 홉 소화' 는 이제 **STOP** 경로의 성질이다 -- 그래서 STOP 으로 건다.
                assert app.seq.stop_integration('abc')
                with caplog.at_level(logging.INFO, logger='icg_archon.seq'):   # 로거 이름은 seq 다
                    await app.seq.wait()
                at_idle = fake.frame_no
                await asyncio.sleep(0.4)
                assert fake.frame_no == at_idle, 'IDLE 뒤에 더 찍었다 -- 꼬리를 덜 소화했다'
                frames0 = fake.frame_no
                files0 = len(glob.glob(os.path.join(app.cfg.paths.data_dir, '*.G.fits')))
                app.transport.feed('abc>ICG go 2')
                await asyncio.sleep(0.05)
                await app.seq.wait()
                await asyncio.sleep(0.1)
                files1 = len(glob.glob(os.path.join(app.cfg.paths.data_dir, '*.G.fits')))
                return fake.frame_no - frames0, files1 - files0
            finally:
                await app.stop()

        produced, saved = asyncio.run(run())
        assert any('꼬리가 둘' in r.getMessage() for r in caplog.records), \
            '두 홉 경로를 안 탔다 -- 시험 전제(늦은 해제)가 안 성립'
        assert (produced, saved) == (2, 2), (produced, saved)   # R2613+: flush 는 프레임을 안 만든다
        del _time
    finally:
        fake.shutdown()


# ---------------------------------------------------------------------------
# R2613+ flush 프레임 -- 설계 검토 must_fix 를 못박는 시험 (DevNote 11.31)
# ---------------------------------------------------------------------------

def test_go_is_refused_when_the_acf_has_no_firstflush(tmp_path):
    """R2612 이하(FirstFlush 슬롯 없음)에 R2613+ 호스트가 GO 를 걸면 **거부**한다.

    그 판에 `Exposures=n` 을 걸면 첫 장이 flush 없이(적분 개시 미정의) 정상 헤더로
    저장된다 -- 조용히 틀리는 가장 나쁜 부류라 경고가 아니라 거부다.
    """
    from icg_archon.backend import GuideBackendError

    fake = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.01,
                      system=GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        cfg, icfg = make_cfgs(tmp_path, fake)
        old = tmp_path / 'old_r2612.acf'
        old.write_text(ACF_TEXT.replace('PARAMETER0="FirstFlush=0"' + chr(10), ''),
                       encoding='utf-8')
        assert 'FirstFlush' not in old.read_text(encoding='utf-8')
        icfg.acf = {'G': str(old)}
        be = GuideBackend(cfg, icfg)
        assert not getattr(be, '_flush_capable', True)

        async def run():  # noqa: ANN202
            await be.prepare()
            try:
                await be.arm_sequence(2, 0, flush=True, suffix='20260905.000001')
            finally:
                await be.shutdown()

        try:
            asyncio.run(run())
        except GuideBackendError as exc:
            assert 'FirstFlush' in str(exc)
        else:
            raise AssertionError('R2612 ACF 에 GO 가 거부되지 않았다')
    finally:
        fake.shutdown()


def test_arm_sets_firstflush_once_and_the_flush_makes_no_frame(tmp_path):
    """arm 은 `FirstFlush=1` 을 LOADPARAMS 한 번에 실고 **곧바로 설정 메모리를 0 으로**
    되쓴다; 가짜의 flush 는 독출 소요만큼 걸리고 **프레임을 만들지 않는다**.

    설정 메모리에 1 이 남으면 뒤따르는 어떤 LOADPARAMS(STOP 의 Exposures=0 …)도
    유령 flush 를 되살린다 -- 가짜가 LOADPARAMS 마다 설정 메모리를 재독하므로 이
    시험이 그 재점화를 본다.
    """
    fake = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.01,
                      system=GUIDE_SYSTEM, nbuf=3)
    fake.start()
    try:
        cfg, icfg = make_cfgs(tmp_path, fake)
        be = GuideBackend(cfg, icfg)

        def flush_slot_text():  # noqa: ANN202
            return next((v for v in fake.config.values() if 'FirstFlush=' in str(v)), '')

        async def run():  # noqa: ANN202
            await be.prepare()
            t1 = await be.arm_sequence(2, 0, flush=True, suffix='20260905.000001')
            # ① 호스트가 LOADPARAMS 뒤 설정 메모리를 되썼다.
            assert 'FirstFlush=0' in flush_slot_text(), flush_slot_text()
            assert t1.armed_utc is not None and t1.armed_mono is not None
            async for _pct in be.wait_frame(t1):
                pass
            t2 = await be.next_ticket(t1, 0, suffix='20260905.000002')
            async for _pct in be.wait_frame(t2):
                pass
            # ② flush 1회 · 프레임 정확히 2 (구판은 3).
            assert getattr(fake, 'flushes', 0) == 1, fake.__dict__.get('flushes')
            assert fake.frame_no == 2, fake.frame_no
            # ③ STOP 경로도 FirstFlush=0 을 함께 쓴다 -- 유령 flush 가 없다.
            flushes0 = fake.flushes
            await be.stop_sequence()
            await asyncio.sleep(0.15)
            assert fake.flushes == flushes0, 'STOP 의 LOADPARAMS 가 flush 를 되살렸다'
            assert 'FirstFlush=0' in flush_slot_text()
            await be.shutdown()

        asyncio.run(run())
    finally:
        fake.shutdown()

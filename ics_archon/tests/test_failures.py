#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""오류 시나리오 -- **실기에서 실제로 일어나는 실패를 밖에서 어떻게 보나.**

시뮬은 거의 안 실패한다.  실기는 컨트롤러 전원이 꺼져 있고, 망이 끊기고, ACF
경로가 틀리고, 디스크가 차고, 독출이 시작되지 않는다.  그때 물어야 할 것은
셋이다:

    1. **프로그램이 살아 있나** (다음 명령을 받나)
    2. **오류가 와이어로 나가나** (관측자가 아나)
    3. **반쪽 산출물이 남지 않나** (아카이브 오염)

⚠️ **가장 나쁜 실패는 "조용한 정지"다.**  예외가 fire-and-forget 태스크에서
죽으면 `Wrote` 0회 · 오류 0회가 되고, OBSAgent 는 창이 넘칠 때까지 기다렸다가
`opause` 로 스크립트 관측을 멈춘다 (DevNote 3.3 · 11.20 critical).  그래서 이
파일의 단정은 대부분 "**무엇이 나갔나**" 다.
"""

from __future__ import annotations

import asyncio
import glob
import os

import pytest
from fake_archon import FakeArchon

from ics_archon import config as acfg_mod
from ics_archon.app import IcsArchon
from ics_archon.archon.protocol import ArchonError

from ics_sim import config as simcfg

NX, NY = 12, 4
INI = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    os.pardir, 'ics_archon.ini'))
ACF_TEXT = '[CONFIG]\nTRIGOUTFORCE=0\nPARAMETER1="Exposures=1"\nPARAMETER2="IntMS=0"\n'
GO = ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go']


def cfgs(tmp_path, **over):  # noqa: ANN001
    acf = tmp_path / 'test.acf'
    if not acf.exists():
        acf.write_text(ACF_TEXT, encoding='ascii')
    cfg = simcfg.load(INI)
    cfg.timing.time_scale = 0.02
    cfg.transport.bind_host = '127.0.0.1'
    cfg.transport.bind_port = 0
    cfg.transport.send_gap_ms = 0.0
    cfg.behavior.console = False
    cfg.logging.wire = False
    cfg.paths.data_dir = str(tmp_path / 'rawdata')
    cfg.paths.expnum_file = str(tmp_path / 'expnum')
    cfg.hardware.backend = 'archon'

    acfg = acfg_mod.load(INI)
    acfg.hosts = {'MK': '127.0.0.1', 'NT': '127.0.0.1'}
    acfg.acf = {'MK': str(acf), 'NT': str(acf)}
    acfg.naxis1, acfg.naxis2 = NX, NY
    acfg.poweron_wait = 0.0
    acfg.frame_poll = 0.01
    acfg.connect_retry = 1
    # 감시는 끈다 -- `test_backend.make_cfgs` 와 같은 이유(홈에 진짜 CSV 를
    # 쌓고 기동 시점에 링크를 잡는다).  `over` 로 켤 수는 있다.
    acfg.monitor = False
    for k, v in over.items():
        setattr(acfg, k, v)
    return cfg, acfg


async def _drive(cfg, acfg, ports, script=None, settle=0.8):  # noqa: ANN001
    app = IcsArchon(cfg, acfg)
    for tag, port in ports.items():
        if tag in app.backend.ctrls:
            app.backend.ctrls[tag].link.port = port
    await app.start()
    try:
        for line in script or GO:
            app.transport.feed(line)
            await asyncio.sleep(0.02)
        await app.seq.wait()
        await asyncio.sleep(settle)
        # **프로그램이 살아 있나** -- 다음 명령이 응답을 받아야 한다.
        before = len(app.transport.sent_log)
        app.transport.feed('OBS>ICS status')
        await asyncio.sleep(0.15)
        alive = len(app.transport.sent_log) > before
        return list(app.transport.sent_log), alive
    finally:
        await app.stop()


def files(tmp_path):  # noqa: ANN201
    return sorted(glob.glob(str(tmp_path / 'rawdata' / '*')))


def errors(sent):  # noqa: ANN201
    return [m for m in sent if '>OBS ERROR' in m or ' ERROR:' in m]


# ---------------------------------------------------------------------------
# 접속 · 설정 실패
# ---------------------------------------------------------------------------

def test_controller_not_answering_is_reported_and_survivable(tmp_path):  # noqa: ANN001
    """**컨트롤러 전원이 꺼져 있다** (가장 흔한 첫 실패).

    레거시와 같은 문구가 나가야 하고, 프로그램은 살아 있어야 한다 -- 전원을
    켜고 다시 `go` 하면 되어야 한다.
    """
    cfg, acfg = cfgs(tmp_path)
    # 아무도 듣지 않는 포트
    sent, alive = asyncio.run(_drive(cfg, acfg, {'MK': 1, 'NT': 1}))
    errs = errors(sent)
    assert errs, '오류가 와이어로 안 나갔다 -- 조용한 정지다'
    assert any('Failed to initialize one or more ICs' in m for m in errs), errs
    assert alive, '프로그램이 죽었다'
    assert not files(tmp_path), '실패했는데 파일이 남았다'


def test_missing_acf_says_where_it_looked(tmp_path):  # noqa: ANN001
    """ACF 경로가 틀렸다 -- **상대경로가 가장 흔한 원인**이라 cwd 를 함께 알린다.

    `configparser.read()` 는 없는 파일에 조용히 성공하므로 그대로 두면
    `NoSectionError` 로 터져 원인이 화면에 안 나온다.
    """
    cfg, acfg = cfgs(tmp_path)
    acfg.acf = {'MK': 'acf/nosuch.acf', 'NT': 'acf/nosuch.acf'}
    mk, nt = FakeArchon(width=NX, height=NY), FakeArchon(width=NX, height=NY)
    mk.start(); nt.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg,
                                        {'MK': mk.port, 'NT': nt.port}))
    finally:
        mk.shutdown(); nt.shutdown()
    assert any('Failed to initialize' in m for m in errors(sent)), errors(sent)
    assert alive
    assert not files(tmp_path)
    # 전원을 올리기 **전에** 멈춘다 -- 설정 없이 바이어스를 걸지 않는다
    assert 'POWERON' not in mk.seen


def test_acf_without_config_section_is_named_not_a_traceback(tmp_path):  # noqa: ANN001
    """ACF 가 Archon 설정 파일이 아니다 -- 무엇이 잘못인지 말한다."""
    bad = tmp_path / 'test.acf'
    bad.write_text('[SOMETHINGELSE]\nx=1\n', encoding='ascii')
    cfg, acfg = cfgs(tmp_path)
    mk, nt = FakeArchon(width=NX, height=NY), FakeArchon(width=NX, height=NY)
    mk.start(); nt.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg,
                                        {'MK': mk.port, 'NT': nt.port}))
    finally:
        mk.shutdown(); nt.shutdown()
    assert any('Failed to initialize' in m for m in errors(sent))
    assert alive


@pytest.mark.parametrize('section, key, value, needle', [
    ('archon', 'shutter_ctrl', 'MIDDLE', 'shutter_ctrl'),
    ('archon', 'port', 'fourtytwo', 'port'),
    ('archon', 'telemetry', 'maybe', 'telemetry'),
])
def test_bad_ini_value_fails_at_startup_with_the_key_name(tmp_path, section,  # noqa: ANN001
                                                          key, value, needle):
    """**ini 오타는 기동에서 죽어야 한다** -- 노출 중에 알면 늦다.

    그리고 메시지에 **키 이름**이 있어야 한다.  어느 줄이 문제인지 모르면
    운영자가 파일 전체를 다시 훑는다.
    """
    import configparser
    cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    cp.read(INI, encoding='utf-8')
    cp[section][key] = value
    path = str(tmp_path / 'bad.ini')
    with open(path, 'w', encoding='utf-8') as f:
        cp.write(f)
    with pytest.raises(acfg_mod.ArchonConfigError, match=needle):
        acfg_mod.load(path)


def test_missing_ics_sim_is_reported_not_guessed():
    """형제 원천도 내장본도 없을 때 -- **찾아본 경로를 다 찍어야** 한다.

    탐색 순서(환경변수 -> 형제 원천 -> 내장본)와 고치는 방법 셋을 다 말한다.
    자세한 단정은 `test_vendor.py::test_missing_everything_names_all_three_fixes`
    가 한다 -- 여기서는 "오류가 조용하지 않다" 만 본다.
    """
    from ics_archon import _simpath
    assert _simpath.CHOSEN, 'ensure() 가 아직 안 불렸다'
    assert _simpath.CHOSEN_WHY, '어느 사본을 골랐는지 기록하지 않았다'
    # 배너가 찍는 한 줄에 경로와 근거가 함께 있어야 한다
    line = _simpath.describe()
    assert _simpath.CHOSEN in line and _simpath.CHOSEN_WHY in line, line


# ---------------------------------------------------------------------------
# 노출 중 실패
# ---------------------------------------------------------------------------

def test_link_dropped_during_readout_reports_the_legacy_message(tmp_path):  # noqa: ANN001
    """**독출 중에 망이 끊긴다.**  레거시가 이 상황에 낸 문구를 그대로 쓴다.

        G.IC>ABC ERROR: GO  DMA WAIT TIMEOUT. EXPOSURES ABORTED.
    """
    cfg, acfg = cfgs(tmp_path)
    mk, nt = FakeArchon(width=NX, height=NY), FakeArchon(width=NX, height=NY)
    mk.start(); nt.start()

    async def run():  # noqa: ANN202
        app = IcsArchon(cfg, acfg)
        app.backend.ctrls['NT'].link.port = nt.port
        await app.start()
        try:
            for line in GO:
                app.transport.feed(line)
                await asyncio.sleep(0.02)
            # 독출이 시작될 무렵 서버를 내린다
            await asyncio.sleep(0.05)
            mk.shutdown(); nt.shutdown()
            for c in app.backend.ctrls.values():
                await c.close()
            await app.seq.wait()
            await asyncio.sleep(0.5)
            return list(app.transport.sent_log)
        finally:
            await app.stop()

    try:
        sent = asyncio.run(run())
    finally:
        mk.shutdown(); nt.shutdown()
    errs = errors(sent)
    assert errs, '독출 실패가 조용히 지나갔다'
    assert any('DMA WAIT TIMEOUT' in m or 'Failed to' in m or '프레임' in m
               for m in errs), errs
    assert not glob.glob(str(tmp_path / 'rawdata' / '*.fits'))


def test_a_frame_that_never_completes_times_out_instead_of_hanging(tmp_path):  # noqa: ANN001
    """**독출이 시작되지 않는다** (ACF 가 틀림 · 클록이 안 감).

    상한이 없으면 `EXPSTATUS=READOUT` 에 갇혀 관측자 화면이 멈추고 OBSAgent 가
    `force_idle` 타임아웃으로 `opause` 에 빠진다 -- **조용한 정지가 가장 나쁜
    실패다.**  `[archon] frame_timeout` 이 그것을 레거시 오류 경로로 바꾼다.
    """
    # `full_flush_on_erase` 를 끈다 -- 켜 두면 ERASE 국면의 flush 에서 먼저
    # 걸려(그것도 정상 동작이고 더 이른 발견이다) 독출 경로를 못 본다.
    cfg, acfg = cfgs(tmp_path, frame_timeout=0.3, full_flush_on_erase=False)
    # `LOADPARAMS` 에 답만 하고 프레임을 만들지 않는 컨트롤러
    mk, nt = FakeArchon(width=NX, height=NY), FakeArchon(width=NX, height=NY)
    for srv in (mk, nt):
        srv._expose = lambda: None        # noqa: SLF001 -- 프레임이 안 나온다
        srv.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg,
                                        {'MK': mk.port, 'NT': nt.port},
                                        settle=1.5))
    finally:
        mk.shutdown(); nt.shutdown()
    errs = errors(sent)
    assert errs, '영구히 기다렸다 -- frame_timeout 이 동작하지 않았다'
    assert any('DMA WAIT TIMEOUT' in m for m in errs), errs
    assert alive
    assert not glob.glob(str(tmp_path / 'rawdata' / '*.fits'))


def test_acquisition_does_not_go_out_before_the_other_controller_finishes(tmp_path):  # noqa: ANN001
    """**NT 만 죽는다 -- 획득 완료가 먼저 나가면 안 된다** (F1, 목 지시 1-A).

    종전에는 `readout()` 이 master(MK) 티켓만 폴링하고 곧바로 `pctread_final`
    을 냈다.  그러면 시퀀서가 `Acquisition Complete.` 4개를 내보낸 **뒤에야**
    NT 의 프레임을 확인하므로, NT 가 죽어도 관측자와 OBSAgent 는 "다 잘
    끝났다" 를 먼저 본다 -- 그 다음에 파일이 2개만 나온다.

    시뮬에서는 CCD 4개가 다 소프트웨어라 "master 가 끝났으면 나머지도 끝났다"
    가 참이었고, 그래서 시험 325개가 전부 초록이었다 (DevNote 11.25).  실기는
    컨트롤러가 물리적으로 둘이라 그 전제가 깨진다.
    """
    # ⚠️ **적분 시간을 0 으로 둔다.**  `exp 1` 이면 IntMS=1000 이라 프레임이
    # 1초 뒤에나 나오고, 그러면 `frame_timeout` 이 MK 에서 먼저 터져 **둘 다
    # 죽은 채로 시험이 통과한다** -- 이 시험이 무엇을 잡는지 모르게 된다.
    cfg, acfg = cfgs(tmp_path, frame_timeout=0.5, full_flush_on_erase=False)
    mk = FakeArchon(width=NX, height=NY)
    nt = FakeArchon(width=NX, height=NY)
    nt._expose = lambda: None             # noqa: SLF001 -- NT 만 프레임이 없다
    mk.start(); nt.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg,
                                         {'MK': mk.port, 'NT': nt.port},
                                         script=['OBS>ICS dark begin',
                                                 'OBS>ICS exp 0',
                                                 'OBS>ICS go'],
                                         settle=1.5))
    finally:
        mk.shutdown(); nt.shutdown()
    acq = [m for m in sent if 'Acquisition Complete.' in m]
    assert not acq, ('NT 가 프레임을 못 냈는데 획득 완료가 나갔다 -- '
                     'master 만 기다린 것이다: %r' % acq)
    errs = errors(sent)
    assert any('DMA WAIT TIMEOUT' in m for m in errs), errs
    assert alive


def test_a_failed_status_drops_the_stale_snapshot_instead_of_reusing_it(tmp_path):  # noqa: ANN001
    """**STATUS 가 실패하면 낡은 값을 버린다** (F8).

    종전에는 `telemetry_enabled` 만 내리고 `self.status` 를 그대로 뒀다.  그
    뒤의 모든 프레임이 **앞 프레임의 온도·전압**을 `Cn_TEMP/VOLT/CURR` 에
    싣고, 텔레메트리는 이 실행 동안 다시 갱신되지 않으므로 파일만 봐서는
    언제 잰 값인지 알 길이 없다.  "물어봤는데 실패" 는 `NC` 여야 한다.
    """
    from ics_archon.archon import parse
    from ics_archon.archon.controller import ArchonController

    cfg, acfg = cfgs(tmp_path, status_timeout=0.2)
    del cfg
    srv = FakeArchon(width=NX, height=NY)
    srv.start()
    try:
        async def run():  # noqa: ANN202
            ctrl = ArchonController('MK', acfg)
            ctrl.link.port = srv.port
            await ctrl.connect()
            try:
                await ctrl.refresh_status()
                first = dict(ctrl.status)
                assert first, '첫 STATUS 가 비었다 -- 시험이 헛돈다'
                assert parse.telemetry_of(first)['temp']
                # 다음 질의부터 답이 늦는다 -- 시한 초과 경로.
                srv.status_delay = 2.0
                ctrl.telemetry_enabled = True
                await ctrl.refresh_status()
                return dict(ctrl.status)
            finally:
                await ctrl.close()

        after = asyncio.run(run())
    finally:
        srv.shutdown()
    assert after == {}, ('STATUS 실패 뒤에도 낡은 스냅샷이 남았다 -- 그 값이 '
                        '실측값처럼 헤더에 실린다: %r' % after)
    # 빈 스냅샷은 `NC` 가 된다 (자리마다 sentinel 을 채우지 않는다).
    assert parse.telemetry_of(after) == {}


def test_shutdown_waits_for_frames_that_are_still_being_saved(tmp_path):  # noqa: ANN001
    """**종료가 독출을 마친 프레임을 버리면 안 된다** (F3).

    저장은 `write_delay` 뒤에 백그라운드로 도는 일이라, 그 창에 종료가 들어오면
    `super().stop()` 이 저장 태스크를 취소하고 `backend.shutdown()` 이 링크를
    닫는다 -- **컨트롤러에서 다 읽어낸 프레임이 파일 없이 사라진다.**  취득
    한 장은 다시 못 찍으므로 전원 차단보다 이쪽이 먼저다.
    """
    cfg, acfg = cfgs(tmp_path, full_flush_on_erase=False)
    # 저장을 늦춰 "독출은 끝났는데 파일은 아직" 창을 넓힌다.
    # 저장을 늦춰 "독출은 끝났는데 파일은 아직" 창을 넓힌다.  전체 스위트를
    # 돌릴 때는 부하로 폴링이 밀리므로 넉넉히 둔다 (0.2초면 간헐 실패했다).
    cfg.timing.write_delay = 50.0            # scaled(0.02) = 1.0초
    mk = FakeArchon(width=NX, height=NY)
    nt = FakeArchon(width=NX, height=NY)
    mk.start(); nt.start()

    async def run():  # noqa: ANN202
        app = IcsArchon(cfg, acfg)
        app.backend.ctrls['MK'].link.port = mk.port
        app.backend.ctrls['NT'].link.port = nt.port
        await app.start()
        try:
            for line in ['OBS>ICS dark begin', 'OBS>ICS exp 0', 'OBS>ICS go']:
                app.transport.feed(line)
                await asyncio.sleep(0.02)
            # 획득 완료가 나오는 즉시 종료한다 -- 저장이 아직 안 끝난 자리다.
            for _ in range(400):
                if any('Acquisition Complete.' in m
                       for m in app.transport.sent_log):
                    break
                await asyncio.sleep(0.01)
            else:                                    # pragma: no cover
                raise AssertionError('획득 완료가 안 나왔다')
            assert not glob.glob(str(tmp_path / 'rawdata' / '*.fits')),                 '저장이 벌써 끝났다 -- 이 시험이 창을 못 잡았다'
        finally:
            await app.stop()

    try:
        asyncio.run(run())
    finally:
        mk.shutdown(); nt.shutdown()
    got = glob.glob(str(tmp_path / 'rawdata' / '*.fits'))
    assert len(got) == 2, ('종료가 저장 중인 프레임을 버렸다 -- 독출은 끝났는데 '
                           '파일이 없다: %r' % got)


def test_a_slower_controller_delays_completion_but_keeps_the_four_in_one_tick(tmp_path):  # noqa: ANN001
    """**NT 가 느려도 4개는 같은 틱에 나간다** (1-A 는 창을 안 건드린다).

    두 프레임을 함께 기다리게 만든 뒤에도 `Acquisition Complete.` 는 **둘 다
    끝난 뒤 한꺼번에** 나가야 한다.  프레임별로 흩어 보내는 것은 별개 판단
    (1-C)이고, 그것을 켜면 4개의 산포가 두 컨트롤러의 실제 시차가 되어 1.8초
    창(DevNote 3.3)이 구조적 보장을 잃는다.
    """
    cfg, acfg = cfgs(tmp_path, full_flush_on_erase=False)
    mk = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.02)
    # NT 를 6배 느리게 -- 실기의 컨트롤러 시차를 흉내낸다.
    nt = FakeArchon(width=NX, height=NY, readout_ticks=6, tick=0.04)
    mk.start(); nt.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg,
                                         {'MK': mk.port, 'NT': nt.port},
                                         settle=1.5))
    finally:
        mk.shutdown(); nt.shutdown()
    assert sum('Acquisition Complete.' in m for m in sent) == 4
    assert sum('Wrote' in m for m in sent) == 8       # CB 4 + ICS 중계 4
    assert sum('EXPSTATUS=IDLE' in m for m in sent) == 1
    assert len(glob.glob(str(tmp_path / 'rawdata' / '*.fits'))) == 2
    assert alive


def test_undeclared_geometry_leaves_no_partial_file(tmp_path):  # noqa: ANN001
    """저장을 거부할 때 **`.part` 임시 파일도 남기지 않는다.**

    반쪽 파일이 최종 이름을 차지하면 D-016 선검사가 그 번호를 점유된 것으로
    보고 다음 번호로 밀어 버린다 -- 그리고 반쪽이 아카이브에 남는다.
    """
    cfg, acfg = cfgs(tmp_path)
    mk = FakeArchon(width=NX * 2, height=NY)      # 선언과 다르다
    nt = FakeArchon(width=NX * 2, height=NY)
    mk.start(); nt.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg,
                                        {'MK': mk.port, 'NT': nt.port}))
    finally:
        mk.shutdown(); nt.shutdown()
    assert errors(sent), '기하 불일치가 통보되지 않았다'
    assert not files(tmp_path), files(tmp_path)
    assert alive
    # 획득 자체는 성공했으니 규약은 지켜져야 한다
    assert sum('Acquisition Complete.' in m for m in sent) == 4


def test_write_failure_is_wrapped_not_leaked(tmp_path):  # noqa: ANN001
    """저장 실패는 **`BackendError` 로 감싸져야** 한다.

    `_store` 는 `BackendError` 만 잡는다.  다른 예외가 새면 fire-and-forget
    태스크가 조용히 죽어 `Wrote` 0회 · 오류 0회가 된다 (DevNote 11.20 critical
    과 같은 부류).  `to_fits_data()` 가 numpy 를 안에서 import 하므로
    `ImportError` 도 그 경로였다.
    """
    from ics_archon.archon import backend as bmod
    cfg, acfg = cfgs(tmp_path)
    mk, nt = FakeArchon(width=NX, height=NY), FakeArchon(width=NX, height=NY)
    mk.start(); nt.start()
    real = bmod.fitswrite.write_frame

    def boom(*a, **k):  # noqa: ANN001, ANN202
        raise ImportError('numpy 가 없다')

    bmod.fitswrite.write_frame = boom
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg,
                                        {'MK': mk.port, 'NT': nt.port}))
    finally:
        bmod.fitswrite.write_frame = real
        mk.shutdown(); nt.shutdown()
    # **와이어 문구는 ASCII 다** -- 전송 계층이 `decode('ascii','replace')`
    # 를 하므로 한글은 `?` 로 바뀌어 관측자가 읽을 수 없다.  한글 진단은
    # 로그로 가고 통보는 ASCII 로 나간다.
    assert any('Failed to write FITS' in m for m in errors(sent)), errors(sent)
    assert all(m.isascii() for m in errors(sent)), errors(sent)
    assert alive


def test_unwritable_data_dir_is_reported(tmp_path):  # noqa: ANN001
    """저장 경로를 만들 수 없다 (권한 · 잘못된 경로)."""
    cfg, acfg = cfgs(tmp_path)
    blocker = tmp_path / 'blocked'
    blocker.write_text('나는 파일이다', encoding='utf-8')
    cfg.paths.data_dir = str(blocker / 'rawdata')   # 파일 아래에는 못 만든다
    mk, nt = FakeArchon(width=NX, height=NY), FakeArchon(width=NX, height=NY)
    mk.start(); nt.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg,
                                        {'MK': mk.port, 'NT': nt.port}))
    finally:
        mk.shutdown(); nt.shutdown()
    # OS 오류 문구가 한국어 Windows 에서 한글로 오므로 그대로 실으면 와이어가
    # `?` 범벅이 된다 -- 통보는 ASCII, 상세는 로그다.
    assert any('Failed to write FITS' in m for m in errors(sent)), errors(sent)
    assert all(m.isascii() for m in errors(sent)), errors(sent)
    assert alive


# ---------------------------------------------------------------------------
# 부분 실패 · 종료
# ---------------------------------------------------------------------------

def test_one_controller_down_does_not_silently_produce_half_a_pair(tmp_path):  # noqa: ANN001
    """**NT 만 죽었다.**  pair 한 짝만 나가면 converter 가 못 읽는다.

    지금 판정: `initialize` 가 `_all`/gather 로 묶여 있어 **한 대가 실패하면
    프레임 전체가 실패**한다 -- 반쪽 pair 를 만들지 않는다는 뜻이고, 그것이
    안전한 쪽이다.  이 시험은 그 선택을 못박는다 (바꾸려면 여기가 걸린다).
    """
    cfg, acfg = cfgs(tmp_path)
    mk = FakeArchon(width=NX, height=NY)
    mk.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg, {'MK': mk.port, 'NT': 1}))
    finally:
        mk.shutdown()
    assert errors(sent), '한쪽이 죽은 것이 통보되지 않았다'
    got = glob.glob(str(tmp_path / 'rawdata' / '*.fits'))
    assert not got, '반쪽 pair 가 나갔다: %r' % got
    assert alive


def test_single_controller_configuration_is_supported(tmp_path):  # noqa: ANN001
    """**실험실은 유닛이 한 대다** -- `[node] ic_ids` 를 둘로 줄이면 돌아야 한다.

    그때 `Acquisition Complete.`/`Wrote` 는 4회가 아니라 2회다(CCD 가 둘) --
    OBSAgent 규약은 만족하지 못하고, 그것이 이 구성의 알려진 한계다
    (README "실기 첫 실행 절차" 4단계).
    """
    cfg, acfg = cfgs(tmp_path)
    cfg.node.ic_ids = ('M.IC', 'K.IC')
    cfg.node.cb_ids = ('M.CB', 'K.CB')
    cfg.node.master = 'K'
    mk = FakeArchon(width=NX, height=NY)
    mk.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg, {'MK': mk.port}))
    finally:
        mk.shutdown()
    assert not errors(sent), errors(sent)
    assert sum('Acquisition Complete.' in m for m in sent) == 2
    got = sorted(os.path.basename(p)
                 for p in glob.glob(str(tmp_path / 'rawdata' / '*.fits')))
    assert len(got) == 1 and got[0].endswith('.MK.fits'), got
    assert alive


def test_shutdown_powers_off_even_after_a_failed_exposure(tmp_path):  # noqa: ANN001
    """**전원을 켠 채로 끝나지 않는다** -- 노출이 실패했더라도."""
    cfg, acfg = cfgs(tmp_path)
    mk = FakeArchon(width=NX * 2, height=NY)      # 기하 불일치로 저장 실패
    nt = FakeArchon(width=NX * 2, height=NY)
    mk.start(); nt.start()
    try:
        asyncio.run(_drive(cfg, acfg, {'MK': mk.port, 'NT': nt.port}))
    finally:
        mk.shutdown(); nt.shutdown()
    assert 'POWEROFF' in mk.seen and 'POWEROFF' in nt.seen
    assert not mk.powered and not nt.powered


def test_reply_error_from_the_controller_is_not_a_framing_error(tmp_path):  # noqa: ANN001
    """컨트롤러가 `?xx` 로 명령을 거부했다 -- **내 명령이 틀린 것**이다.

    프레이밍 오류와 갈라야 대응이 갈린다(명령·ACF 를 보는 것 vs 연결을 다시
    세우는 것).  거부는 연결을 버릴 이유가 아니다.
    """
    cfg, acfg = cfgs(tmp_path)
    mk = FakeArchon(width=NX, height=NY, reject=('APPLYALL',))
    nt = FakeArchon(width=NX, height=NY, reject=('APPLYALL',))
    mk.start(); nt.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg,
                                        {'MK': mk.port, 'NT': nt.port},
                                        settle=1.2))
    finally:
        mk.shutdown(); nt.shutdown()
    assert any('Failed to initialize' in m for m in errors(sent)), errors(sent)
    assert alive
    # **거부는 재연결 사유가 아니다.**  같은 설정을 다시 밀면 같은 거부가
    # 돌아오고, 그 사이 재접속을 되풀이하면 원인이 "망이 불안하다" 로 오인된다.
    assert mk.accepts == 1, '거부 응답에 연결을 다시 열었다 (%d회)' % mk.accepts
    assert mk.seen.count('APPLYALL') == 1, (
        '거부된 APPLYALL 을 재시도했다 (%d회)' % mk.seen.count('APPLYALL'))


def test_unknown_command_does_not_hang_forever(tmp_path):  # noqa: ANN001
    """프로토콜은 **인식 못 한 명령에 무응답**이다 (매뉴얼 p.45).

    `ArchonLink.command` 의 기본값은 무한 대기(규약)이므로, 부르는 쪽이 상한을
    주지 않으면 오타 하나로 영구히 멈춘다.  `controller.py` 가 명령마다 상한을
    주는지 확인한다 -- `APPLYSYSTEM` 을 삼키게 만든다.
    """
    cfg, acfg = cfgs(tmp_path)
    mk = FakeArchon(width=NX, height=NY, unknown=('APPLYSYSTEM',))
    nt = FakeArchon(width=NX, height=NY, unknown=('APPLYSYSTEM',))
    mk.start(); nt.start()
    try:
        sent, alive = asyncio.run(asyncio.wait_for(
            _drive(cfg, acfg, {'MK': mk.port, 'NT': nt.port}, settle=1.0),
            timeout=180))
    finally:
        mk.shutdown(); nt.shutdown()
    assert errors(sent), '무응답에 영구히 매달렸다'
    assert alive


def test_a_stuck_flush_also_errors_instead_of_hanging(tmp_path):  # noqa: ANN001
    """`ERASE` 의 flush 도 프레임을 기다린다 -- 거기서 멈춰도 오류로 나가야 한다.

    `full_flush_on_erase=true`(기본값)면 독출보다 **먼저** 여기서 걸린다 --
    노출 시간을 버리기 전에 알게 되므로 오히려 이른 발견이다.  통보의 국면은
    `EXPSTATUS=ERASE` 로 드러난다.
    """
    cfg, acfg = cfgs(tmp_path, frame_timeout=0.3)
    mk, nt = FakeArchon(width=NX, height=NY), FakeArchon(width=NX, height=NY)
    for srv in (mk, nt):
        srv._expose = lambda: None        # noqa: SLF001
        srv.start()
    try:
        sent, alive = asyncio.run(_drive(cfg, acfg,
                                        {'MK': mk.port, 'NT': nt.port},
                                        settle=1.5))
    finally:
        mk.shutdown(); nt.shutdown()
    errs = errors(sent)
    assert errs, '영구히 기다렸다'
    assert any('EXPSTATUS=ERASE' in m for m in errs), errs
    assert alive


def test_time_scale_other_than_one_is_flagged_for_archon(tmp_path):  # noqa: ANN001
    """⚠️ **`time_scale != 1.0` 은 실기에서 노출을 잘라낸다.**

    적분 길이를 재는 것은 컨트롤러(`IntMS`)이고 시퀀서의 카운트다운은 알림이다.
    축척을 낮추면 카운트다운이 먼저 끝나 `close_shutter()` 가 적분 중에 불리고,
    그것이 셔터를 강제로 닫는다 -- 그런데 헤더 `EXPTIME` 은 요청값 그대로라
    **정상으로 보이는 오염 프레임**이 된다.  DevNote 9.2.3 이 AUX 시뮬을 물릴
    때 같은 이유로 1.0 을 요구했다.

    한쪽만 보면 둘 다 정상인 값이라 각자의 `validate()` 로는 안 걸린다 --
    교차 검사가 필요한 자리다.
    """
    cfg, acfg = cfgs(tmp_path)
    cfg.timing.time_scale = 0.02
    notes = acfg_mod.validate(acfg, tuple(cfg.node.ccds), cfg)
    assert any('[timing] time_scale' in n and 'EXPTIME' in n
               for n in notes), notes

    cfg.timing.time_scale = 1.0
    again = acfg_mod.validate(acfg, tuple(cfg.node.ccds), cfg)
    # ⚠️ **`'[timing] time_scale'` 로 찾는다 -- 낱말만 보면 안 된다.**  pytest 의
    # `tmp_path` 는 **시험 이름에서 만들어지고**(`…test_time_scale_other_than_one0`),
    # 경로를 그대로 싣는 경고가 하나라도 있으면 그 이름이 걸린다.  실제로
    # 저장 자리 선검사(2026-08-28)를 넣자마자 이 시험이 그렇게 깨졌다 --
    # 제품 결함이 아니라 **시험이 너무 헐거웠던 것**이다.
    assert not any('[timing] time_scale' in n for n in again), again


def test_aux_and_inject_are_flagged_for_archon(tmp_path):  # noqa: ANN001
    """실기에서 켜 두면 안 되는 두 가지 -- 셔터 구동원 이중화와 결함 주입."""
    cfg, acfg = cfgs(tmp_path)
    cfg.timing.time_scale = 1.0
    cfg.auxcontrol.enabled = True
    cfg.behavior.inject = frozenset({'wrote_drop'})
    notes = acfg_mod.validate(acfg, tuple(cfg.node.ccds), cfg)
    assert any('auxcontrol' in n for n in notes), notes
    assert any('inject' in n for n in notes), notes


def test_normal_countdown_end_does_not_force_the_shutter(tmp_path):  # noqa: ANN001
    """정상 경로에서는 셔터를 **만지지 않는다.**

    `int_until` 은 `trigger()` 시점 + `IntMS` 이고 그 trigger 는 카운트다운
    시작보다 조금 뒤에 걸리므로, 여유 폭이 없으면 **매 노출마다** 독출 시작
    무렵에 `APPLYSYSTEM` 이 한 번 더 나간다 -- 그것이 안전한지는 실기 확인
    항목이라 정상 경로에서는 보내지 않는 편이 맞다.
    """
    cfg, acfg = cfgs(tmp_path)
    cfg.timing.time_scale = 1.0          # 실기 조건
    mk, nt = FakeArchon(width=NX, height=NY), FakeArchon(width=NX, height=NY)
    mk.start(); nt.start()
    try:
        sent, alive = asyncio.run(_drive(
            cfg, acfg, {'MK': mk.port, 'NT': nt.port},
            script=['OBS>ICS object M31', 'OBS>ICS exp 1', 'OBS>ICS go'],
            settle=2.0))
    finally:
        mk.shutdown(); nt.shutdown()
    assert not errors(sent), errors(sent)
    # 셔터 모드 설정(open_shutter)에서 1회.  강제 폐쇄가 있으면 2회가 된다.
    assert mk.seen.count('APPLYSYSTEM') == 1, mk.seen
    assert alive


def test_relative_data_dir_is_flagged_for_archon(tmp_path):  # noqa: ANN001
    """⚠️ **상대경로 `data_dir` 은 실행한 디렉터리 기준으로 풀린다.**

    ini 위치도 프로그램 위치도 아니다 -- systemd 의 `WorkingDirectory`, cron,
    손으로 띄운 셸이 각각 다른 곳을 가리키므로 **같은 설정이 실행마다 다른 곳에
    자료를 쌓는다.**  오류가 없으니 드러나지도 않는다(labtest 의 ACF 상대경로가
    같은 부류로 가장 많이 넘어졌다).
    """
    cfg, acfg = cfgs(tmp_path)
    cfg.timing.time_scale = 1.0
    cfg.paths.data_dir = '../data'
    notes = acfg_mod.validate(acfg, tuple(cfg.node.ccds), cfg)
    assert any('data_dir' in n and '상대경로' in n for n in notes), notes

    cfg.paths.data_dir = os.path.expanduser('~/AIC/data')
    assert not any('상대경로' in n
                   for n in acfg_mod.validate(acfg, tuple(cfg.node.ccds), cfg))


# ---------------------------------------------------------------------------
# POWERON -- "응답은 왔는데 전원이 안 올라왔다"
# ---------------------------------------------------------------------------
#
# 실험실 계보 둘이 여기서 갈린다 (2026-08-28 참고자료 재검토):
# labtest v1.0/v1.3 은 `POWERON` 응답만 보고 12초를 세고,
# `__ref_archon_control/modtm_*.py` 는 `STATUS` 를 되물어 `POWER==4` 를
# 확인한다.  본편은 modtm 쪽을 따른다 -- 확인이 없으면 전원이 안 올라온 채로
# 노출이 걸리고 밖에서는 "취득 실패" 로만 보인다 (F2 가 막으려던 모양).


def _power_run(tmp_path, srv, **over):  # noqa: ANN001, ANN202
    """`power_on()` 한 번 -- 컨트롤러만 세우고 부른다."""
    from ics_archon.archon.controller import ArchonController

    _cfg, acfg = cfgs(tmp_path, **over)
    del _cfg

    async def run():  # noqa: ANN202
        ctrl = ArchonController('MK', acfg)
        ctrl.link.port = srv.port
        await ctrl.connect()
        try:
            await ctrl.power_on()
        finally:
            await ctrl.close()

    asyncio.run(run())


def test_poweron_is_verified_against_the_power_field(tmp_path, caplog):  # noqa: ANN001
    """**램프 도중의 `POWER=3` 은 정상 경과이고 경보가 아니다.**

    바이어스는 단계로 올라온다(p.47 의 `3` = Intermediate, 일부 모듈만).  그
    값을 `_check_health()` 에 넣으면 **켤 때마다** "컨트롤러 상태 이상" 이 뜨고,
    반복되는 경고는 사람이 경고를 무시하도록 학습시킨다.  확인 경로는 건강
    판정과 갈라 두고, `4` 에 닿았다는 것만 알린다.
    """
    from fake_archon import FULL_STATUS

    srv = FakeArchon(width=NX, height=NY, status=dict(FULL_STATUS),
                     power_ramp=2)
    srv.start()
    try:
        with caplog.at_level('INFO', logger='ics_archon.ctrl'):
            _power_run(tmp_path, srv, poweron_wait=1.5)
    finally:
        srv.shutdown()
    text = caplog.text
    assert 'POWER=4' in text, text
    assert '컨트롤러 상태 이상' not in text, ('램프 도중의 POWER=3 이 건강 '
                                             '판정으로 샜다: %s' % text)


def test_poweron_that_never_reaches_four_is_reported_but_does_not_block(tmp_path,  # noqa: ANN001
                                                                       caplog):
    """**막지는 않는다** -- `_check_health()` 와 같은 자리다.

    이 필드는 아직 실기 미검증(PROVISIONAL)이라 오독 하나로 관측을 통째로
    세우는 쪽이 더 나쁘다.  대신 원인이 보이도록 크게 남긴다 -- 종전에는 전원이
    안 올라온 것이 밖에서 "취득 실패" 로만 보였다.
    """
    from fake_archon import FULL_STATUS

    # 램프가 끝나지 않는다 -- 대기 시간 안에 `4` 에 못 닿는다.
    srv = FakeArchon(width=NX, height=NY, status=dict(FULL_STATUS),
                     power_ramp=50)
    srv.start()
    try:
        with caplog.at_level('INFO', logger='ics_archon.ctrl'):
            _power_run(tmp_path, srv, poweron_wait=1.2)
    finally:
        srv.shutdown()
    errs = [r.getMessage() for r in caplog.records if r.levelname == 'ERROR']
    assert any('POWER=3' in m for m in errs), caplog.text


def test_poweron_is_not_verified_when_telemetry_is_off(tmp_path):  # noqa: ANN001
    """**규약 4 -- `telemetry=false` 는 왕복을 labtest v1.0 계보와 같게 둔다.**

    확인 질의도 왕복이다.  그 설정에서 `STATUS` 가 하나라도 늘면 "실기에서
    원인을 가르는 첫 수단" 이라는 그 설정의 존재 이유가 없어진다.
    """
    from fake_archon import FULL_STATUS

    srv = FakeArchon(width=NX, height=NY, status=dict(FULL_STATUS))
    srv.start()
    try:
        _power_run(tmp_path, srv, poweron_wait=0.3, telemetry=False)
    finally:
        srv.shutdown()
    assert 'STATUS' not in srv.seen, srv.seen
    assert 'POWERON' in srv.seen, srv.seen


def test_a_firmware_without_the_power_field_is_not_an_error(tmp_path, caplog):  # noqa: ANN001
    """**보고가 없는 필드를 이상으로 세지 않는다** (F2 원칙).

    `DEFAULT_STATUS` 는 `POWER` 를 아예 안 내는 응답이다(구 펌웨어).  그때는
    확인 수단이 없는 것이지 전원이 안 올라온 것이 아니다 -- 여기서 오류를 내면
    첫 실행이 통째로 경보가 된다.
    """
    srv = FakeArchon(width=NX, height=NY)       # DEFAULT_STATUS -- POWER 없음
    srv.start()
    try:
        with caplog.at_level('INFO', logger='ics_archon.ctrl'):
            _power_run(tmp_path, srv, poweron_wait=0.6)
    finally:
        srv.shutdown()
    assert not [r for r in caplog.records if r.levelname == 'ERROR'], caplog.text
    assert 'POWER 필드가 없다' in caplog.text, caplog.text


def test_the_startup_path_runs_the_check_without_deadlocking(tmp_path, caplog):  # noqa: ANN001
    """**`prepare()` 를 통째로 밟는다** -- 확인이 락 안에서 도는지.

    `_await_power()` 는 `query()` 를 부르고 그것이 `ArchonController._lock` 을
    잡는다.  `power_on()` 이 그 락을 쥔 채로 부르면 **재진입 없는
    `asyncio.Lock` 이라 그대로 멈춘다** -- 위 시험 넷은 `power_on()` 을 바로
    부르므로 그 경로를 못 밟는다.  여기서 ACF 적용 → 전원 → `SYSTEM` 까지
    실제 순서로 지나간다.
    """
    from fake_archon import FULL_STATUS
    from ics_archon.archon.controller import ArchonController

    srv = FakeArchon(width=NX, height=NY, status=dict(FULL_STATUS),
                     power_ramp=1)
    srv.start()
    try:
        _cfg, acfg = cfgs(tmp_path, poweron_wait=1.0)
        del _cfg

        async def run():  # noqa: ANN202
            ctrl = ArchonController('MK', acfg)
            ctrl.link.port = srv.port
            try:
                await asyncio.wait_for(ctrl.prepare(), timeout=20)
            finally:
                await ctrl.close()

        with caplog.at_level('INFO', logger='ics_archon.ctrl'):
            asyncio.run(run())
    finally:
        srv.shutdown()
    assert 'POWER=4' in caplog.text, caplog.text
    assert srv.seen.count('APPLYALL') == 1, srv.seen

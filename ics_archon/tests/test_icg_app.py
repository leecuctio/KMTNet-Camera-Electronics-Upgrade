#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""icg 전 경로 -- `go n` 이 guide 의미론(10.1절)대로 도는가.

`ics_sim` 하네스와 같은 수법 -- 소켓 없이 `transport.feed()` 로 명령을
주입하고 발신 로그를 대조한다.  백엔드는 `SimGuideBackend`(컨트롤러 없음),
저장은 실제 파일(zero 프레임, 8.3 MiB)이다.
"""

from __future__ import annotations

import asyncio
import glob
import os

import pytest

import ics_archon  # noqa: F401

from ics_sim import config as simcfg  # noqa: E402

from icg_archon import config as icfg_mod  # noqa: E402
from icg_archon.app import IcgArchon  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INI = os.path.join(ROOT, 'icg_archon.ini')


def make_cfgs(tmp_path):  # noqa: ANN001, ANN201
    """배포 ini 를 실제로 읽고 시험용으로 덮는다 (make_config 과 같은 정신)."""
    cfg = simcfg.load(INI)
    cfg.timing.time_scale = 0.02
    cfg.transport.bind_port = 0
    cfg.transport.send_gap_ms = 0
    cfg.behavior.console = False
    cfg.paths.data_dir = str(tmp_path / 'data')
    cfg.paths.write_fits = True
    cfg.paths.expnum_file = str(tmp_path / 'icg.expnum')
    icfg = icfg_mod.load(INI)
    icfg.hk.log_dir = str(tmp_path / 'log')
    icfg.hk.interval = 3600.0        # 시험 중 재바퀴 금지 (첫 바퀴는 돈다)
    icfg.hk.query_aux = False        # TC 없는 시험 -- 시한 대기 소음 제거
    icfg.exptime_min = 0.5
    return cfg, icfg


async def _drive(tmp_path, script):  # noqa: ANN001, ANN201
    cfg, icfg = make_cfgs(tmp_path)
    app = IcgArchon(cfg, icfg, backend='sim')
    await app.start()
    try:
        for line in script:
            app.transport.feed(line)
            await asyncio.sleep(0.02)
        await app.seq.wait()
        await asyncio.sleep(0.05)    # 마지막 발신 flush
    finally:
        await app.stop()
    return app, [str(s) for s in app.transport.sent_log]


@pytest.fixture()
def run_go3(tmp_path):  # noqa: ANN201
    return asyncio.run(_drive(tmp_path, [
        'abc>ICG GUIDEEXP 2',
        'abc>ICG go 3',
    ]))


def test_go_n_saves_n_files_discarding_the_first(run_go3, tmp_path):
    """10.1-2·3 -- `go 3` = 독출 4회 · 저장 3장 · 파일명 `.G.fits` 연번."""
    app, _sent = run_go3
    files = sorted(glob.glob(os.path.join(
        app.cfg.paths.data_dir, '*.G.fits')))
    assert len(files) == 3
    names = [os.path.basename(p) for p in files]
    site = app.state.site_code
    assert all(n.startswith(site + '.') for n in names)
    nums = [int(n.split('.')[2]) for n in names]
    assert nums == [nums[0], nums[0] + 1, nums[0] + 2]


def _cards(path: str) -> dict[str, str]:
    """FITS 헤더 80자 레코드 -> {key: 원문 값·comment}."""
    out = {}
    with open(path, 'rb') as fh:
        blob = fh.read(2880 * 4)
    text = blob.decode('ascii')
    for i in range(0, len(text), 80):
        rec = text[i:i + 80]
        if rec.startswith('END'):
            break
        key = rec[:8].rstrip()
        if key and key != 'COMMENT':
            out[key] = rec[10:]
    return out


def test_guide_header_semantics(run_go3):
    """DATE-OBS(직전 독출 개시)·EXPTIME(정수 2)·EXPID/FILENAME 정체성."""
    app, _sent = run_go3
    files = sorted(glob.glob(os.path.join(
        app.cfg.paths.data_dir, '*.G.fits')))
    dates = []
    for path in files:
        cards = _cards(path)
        stem = os.path.basename(path)[:-5]
        assert cards['FILENAME'].startswith("'" + stem)
        # EXPID = FILENAME 에서 DETID 필드를 뗀 값 (평시 -- 충돌 없음).
        expid = stem.rsplit('.', 1)[0]
        assert cards['EXPID'].startswith("'" + expid)
        # ⭐ **대역으로 찍은 프레임은 `SIM` 이다** -- 규격 5.5절이 이 카드를
        # "시뮬 프레임 오인을 막는" 자리로 규정한다.  종전에는 상수로 박아
        # 둬서 0-프레임이 실측 자료로 표시됐고 이 시험이 그것을 못박고
        # 있었다 (2026-08-31 교차검토).  실기 값은 아래 별도 시험.
        assert cards['DATASRC'].startswith("'SIM")
        assert 'ICGBUILD' in cards and 'ICSBUILD' not in cards
        assert cards['EXPTIME'].split('/')[0].strip() == '2'
        assert cards['NAXIS1'].split('/')[0].strip() == '4224'
        date_obs = cards['DATE-OBS'].split('/')[0].strip().strip("'").strip()
        assert len(date_obs) == 23        # 밀리초 필수 (10.1-4)
        dates.append(date_obs)
    # 프레임마다 DATE-OBS 가 전진한다 (= 직전 독출 개시가 서로 다르다).
    assert dates == sorted(dates) and len(set(dates)) == 3


def test_messages_follow_the_wrote_and_idle_forms(run_go3):
    """저장 통보 3회 + 마지막 DONE: EXPSTATUS=IDLE (메시지 위생 위반 0)."""
    app, sent = run_go3
    text = '\n'.join(sent)
    assert text.count('Wrote LASTFILE=') == 3
    assert 'DONE: EXPSTATUS=IDLE' in text
    assert 'DONE: GUIDEEXP GuideExp=2 seconds.' in text
    assert app.emit.violations == [] if hasattr(app.emit, 'violations') else True


def test_readout_failure_reports_error_and_returns_to_idle(tmp_path):
    """독출 실패가 시퀀서를 조용히 죽이면 안 된다 -- ERROR + IDLE 통보.

    교차검토(2026-08-31)에서 잡힌 고착 경로의 회귀: wait_frame 예외가
    무처리로 새면 expstatus 가 READOUT 에 고정되고 통보가 0이 된다.
    """
    from icg_archon.backend import GuideBackendError, SimGuideBackend

    class FailingBackend(SimGuideBackend):
        async def wait_frame(self, ticket):  # noqa: ANN001, ANN202
            yield 50
            raise GuideBackendError('DMA WAIT TIMEOUT. EXPOSURES ABORTED.')

    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        app = IcgArchon(cfg, icfg, backend='sim')
        app.guide = FailingBackend(cfg, icfg)
        app.seq.backend = app.guide
        await app.start()
        try:
            app.transport.feed('abc>ICG GUIDEEXP 1')
            await asyncio.sleep(0.02)
            app.transport.feed('abc>ICG go')
            await asyncio.sleep(0.02)
            await app.seq.wait()
            await asyncio.sleep(0.05)
        finally:
            await app.stop()
        return app, [str(s) for s in app.transport.sent_log]

    app, sent = asyncio.run(run())
    text = '\n'.join(sent)
    assert 'ERROR: GO DMA WAIT TIMEOUT' in text
    assert 'DONE: EXPSTATUS=IDLE' in text
    assert app.state.expstatus == 'IDLE'
    assert not app.state.exposing


def test_collision_bumps_number_but_keeps_expid(tmp_path):
    """D-016 guide 판 -- 점유 시 번호가 밀리고 EXPID 는 최초 배정분."""
    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        try:
            os.makedirs(cfg.paths.data_dir, exist_ok=True)
            site = app.state.site_code
            date = app.state.obs_date()
            nxt = app.state.expnum
            taken = os.path.join(
                cfg.paths.data_dir,
                '%s.%s.%06d.G.fits' % (site, date, nxt))
            open(taken, 'wb').close()
            app.transport.feed('abc>ICG GUIDEEXP 1')
            await asyncio.sleep(0.02)
            app.transport.feed('abc>ICG go')
            await asyncio.sleep(0.02)
            await app.seq.wait()
        finally:
            await app.stop()
        return app, site, date, nxt

    app, site, date, nxt = asyncio.run(run())
    files = glob.glob(os.path.join(app.cfg.paths.data_dir, '*.G.fits'))
    saved = [p for p in files if os.path.getsize(p) > 0]
    assert len(saved) == 1
    cards = _cards(saved[0])
    stem = os.path.basename(saved[0])[:-5]
    assert stem == '%s.%s.%06d.G' % (site, date, nxt + 1)
    # EXPID 는 최초 배정분 -- FILENAME 과의 불일치가 충돌 신호 (D-019).
    assert cards['EXPID'].startswith("'%s.%s.%06d" % (site, date, nxt))


# ---------------------------------------------------------------------------
# 포트 배정 (2026-09-03)
# ---------------------------------------------------------------------------

@pytest.mark.repo_only
def test_the_two_programs_do_not_share_a_port():
    """⭐ **ICS 6600 · ICG 6601** -- 배포 ini 둘이 같은 포트를 쓰지 않는다.

    ⚠️ `ics_sim` 기본값이 6600 이라 icg ini 에서 `bind_port` 를 **빼면 같은
    값으로 떨어진다** -- 한 호스트에 둘을 올리는 배치에서 뒤에 뜨는 쪽이 bind
    에 실패하고, 그 오류는 "왜 안 뜨나" 로만 보인다.  주석으로 막을 수 없는
    자리라 시험으로 못박는다 (배정표는 `INSTALL.md`).
    """
    ics_ini = os.path.join(ROOT, 'ics_archon.ini')
    ics = simcfg.load(ics_ini)
    icg = simcfg.load(INI)
    assert ics.transport.bind_port == 6600, ics.transport.bind_port
    assert icg.transport.bind_port == 6601, icg.transport.bind_port
    assert ics.transport.bind_port != icg.transport.bind_port
    # 레거시가 쓰던 나머지 자리와도 안 겹친다 (TC 6606 · OBS 6650 · XIS 6660).
    assert icg.transport.bind_port not in (6606, 6650, 6660)
    # 허브를 가리키는 값은 둘이 **같아야** 한다 -- 같은 허브에 붙는다.
    assert ics.transport.xis_port == icg.transport.xis_port == 6660


def test_icg_warns_when_it_is_given_the_ics_port(tmp_path, caplog):  # noqa: ANN001
    """ICS 몫 포트를 받으면 기동에서 알린다 -- 오타 방어.

    ⚠️ 막지는 않는다 -- 호스트를 갈라 둔 배치에서는 6600 이 정당하다.
    """
    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        cfg.transport.bind_port = IcgArchon.ICS_BIND_PORT
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        await app.stop()

    caplog.set_level('WARNING')
    asyncio.run(run())
    said = [r.getMessage() for r in caplog.records]
    assert any('ICS 몫' in m for m in said), said


# ---------------------------------------------------------------------------
# EXPENABLE -- 노출 잠금 (운영자 확정 2026-09-03)
# ---------------------------------------------------------------------------

def _drive_lines(tmp_path, script, before=None):  # noqa: ANN001
    """대본을 먹이고 (app, 발신로그) 를 돌려준다.  `before(app)` 로 상태 주입."""
    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        if before:
            before(app)
        try:
            for line in script:
                app.transport.feed(line)
                await asyncio.sleep(0.02)
            await app.seq.wait()
            await asyncio.sleep(0.05)
        finally:
            await app.stop()
        return app, [str(s) for s in app.transport.sent_log]
    return asyncio.run(run())


def test_expenable_accepts_four_words_and_answers_in_normal_form(tmp_path):  # noqa: ANN001
    """`ON`/`TRUE`/`OFF`/`FALSE` 를 받고 응답은 **정규형**으로 되돌린다.

    ⭐ `true` 를 쳐도 `ExpEnable=ON` 이 나가야 로그가 한 형태로만 남아 grep 이
    된다 (저장소 관례 -- `DONE: EXP ExpTime=...`).
    """
    _app, sent = _drive_lines(tmp_path, [
        'abc>ICG EXPENABLE',            # 조회 -- 기본은 허용
        'abc>ICG EXPENABLE false',      # 소문자 · 별칭
        'abc>ICG EXPENABLE',
        'abc>ICG EXPENABLE TRUE',
        'abc>ICG EXPENABLE',
    ])
    said = [s for s in sent if 'EXPENABLE' in s]
    assert any('ExpEnable=ON' in s for s in said), said
    assert any('ExpEnable=OFF' in s for s in said), said
    # 소문자·별칭을 그대로 되돌리지 않는다 (정규형만 나간다)
    assert not any('false' in s or 'TRUE' in s.split('ExpEnable=')[-1]
                   for s in said if 'ExpEnable=' in s), said


def test_expenable_refuses_an_unknown_value_and_keeps_the_state(tmp_path):  # noqa: ANN001
    """⛔ **모르는 값은 기본값으로 떨어뜨리지 않는다** -- 거부하고 상태 유지.

    ⭐ 이 규칙이 **잘림 손상까지 막는다** -- 시리얼 구간에서 `OFF` 가 `O` 로
    잘려 와도 거부되므로 잠금이 조용히 풀리지 않는다.
    """
    app, sent = _drive_lines(tmp_path, [
        'abc>ICG EXPENABLE OFF',
        'abc>ICG EXPENABLE FLASE',      # 오타
        'abc>ICG EXPENABLE O',          # 잘림
        'abc>ICG EXPENABLE',
    ])
    said = [s for s in sent if 'EXPENABLE' in s]
    assert sum('Invalid value' in s for s in said) == 2, said
    # 오타 둘을 겪고도 여전히 잠겨 있다
    assert not app.expenable.allowed
    assert said[-1].endswith('ExpEnable=OFF')


def test_go_is_refused_while_locked(tmp_path):  # noqa: ANN001
    """⛔ 잠겨 있으면 `GO` 가 시작하지 않는다 -- 파일도 안 생긴다."""
    app, sent = _drive_lines(tmp_path, [
        'abc>ICG EXPENABLE OFF',
        'abc>ICG GUIDEEXP 2',
        'abc>ICG go 3',
    ])
    assert any('Exposure is disabled (EXPENABLE OFF)' in s for s in sent), sent
    assert not app.seq.busy
    assert not glob.glob(str(tmp_path / 'data' / '*.fits'))


def test_expenable_off_stops_a_running_acquisition(tmp_path):  # noqa: ANN001
    """⭐ `OFF` 는 진행 중인 취득도 세운다 -- 그리고 **플래그가 먼저**다.

    ⚠️ 순서를 뒤바꾸면 창이 열린다: abort 뒤 `EXPSTATUS=IDLE` 을 기다린 `go`
    가 곧바로 들어오면 **막 세운 노출이 즉시 다시 시작된다.**  그래서 세우는
    도중에 들어온 `go` 도 거절되는지 함께 본다.
    """
    async def run():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        icfg.expenable_file = str(tmp_path / 'icg.expenable')
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        try:
            app.transport.feed('abc>ICG GUIDEEXP 2')
            await asyncio.sleep(0.02)
            app.transport.feed('abc>ICG go 5')
            await asyncio.sleep(0.05)
            assert app.seq.busy, '취득이 안 돌고 있다 -- 시험 전제가 깨졌다'
            app.transport.feed('abc>ICG EXPENABLE OFF')
            await asyncio.sleep(0.05)
            app.transport.feed('abc>ICG go 5')      # 세우는 도중에 들어온 GO
            await asyncio.sleep(0.05)
            await app.seq.wait()
            await asyncio.sleep(0.05)
        finally:
            await app.stop()
        return app, [str(s) for s in app.transport.sent_log]

    app, sent = asyncio.run(run())
    assert any('Aborted=1' in s for s in sent), sent
    assert any('Exposure is disabled' in s for s in sent), sent
    assert not app.expenable.allowed


def test_the_lock_survives_a_restart(tmp_path):  # noqa: ANN001
    """지속된다 -- 재기동해도 잠김이 유지된다 (`expnum` 과 같은 영속 규약)."""
    path = str(tmp_path / 'icg.expenable')

    async def once(script):  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        icfg.expenable_file = path
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        for line in script:
            app.transport.feed(line)
            await asyncio.sleep(0.02)
        allowed, origin = app.expenable.allowed, app.expenable.origin
        await app.stop()
        return allowed, origin

    assert asyncio.run(once(['abc>ICG EXPENABLE OFF']))[0] is False
    allowed, origin = asyncio.run(once([]))       # 새 프로세스처럼 다시 뜬다
    assert allowed is False, '재기동에서 잠금이 풀렸다'
    assert origin == 'file'


def test_a_garbled_lock_file_starts_locked(tmp_path):  # noqa: ANN001
    """⚠️ **폴라리티가 expnum 과 반대다** -- 값을 못 믿으면 **잠근다.**

    ⭐ 다만 "없음"(첫 구동)과 "못 읽음"(손상)은 가른다 -- 없으면 허용이다.
    파일이 없을 때마다 잠기면 첫 구동 체크리스트가 한 걸음도 못 간다.
    """
    path = tmp_path / 'icg.expenable'

    async def boot():  # noqa: ANN202
        cfg, icfg = make_cfgs(tmp_path)
        icfg.expenable_file = str(path)
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        out = (app.expenable.allowed, app.expenable.origin)
        await app.stop()
        return out

    assert asyncio.run(boot()) == (True, 'absent')        # 없음 -> 허용
    path.write_text('YES PLEASE\n', encoding='utf-8')     # 어휘 밖
    assert asyncio.run(boot()) == (False, 'garbled')      # 손상 -> 금지


# -- 히터·이온게이지 명령 (운영자 확정 2026-09-04) -------------------------
#
# 여기는 **명령 층**만 본다 -- 키 조립·한계·클램프는 `test_icg_heater_gauge.py`
# 가 실물 ACF 로 본다.


def _with_ctrl(tmp_path, script):  # noqa: ANN001, ANN202
    """`sim` 백엔드에 **가짜 컨트롤러를 꽂고** 대본을 먹인다.

    `SimGuideBackend.ctrl` 은 `None` 이라 히터·게이지 명령이 정상적으로
    거부된다 -- 그 거부까지 시험하려면 꽂아 줘야 한다.
    """
    from test_icg_heater_gauge import RecordingCtrl

    ctrl = RecordingCtrl()

    def before(app):  # noqa: ANN001, ANN202
        app.guide.ctrl = ctrl
        app.hk.ctrl = None            # HK 는 이 가짜로 STATUS 를 안 본다

    app, sent = _drive_lines(tmp_path, script, before=before)
    return app, sent, ctrl


def test_the_heater_and_gauge_commands_refuse_without_a_controller(tmp_path):  # noqa: ANN001
    """⛔ 컨트롤러가 없으면 **성공을 흉내내지 않는다.**

    조용히 DONE 을 내면 *"명령은 먹었는데 아무것도 안 바뀜"* 이 된다.
    """
    _app, sent = _drive_lines(tmp_path, [
        'abc>ICG HTREN ON', 'abc>ICG HTRSET -100', 'abc>ICG VACGAUGE OFF',
    ])
    said = [s for s in sent if 'ERROR' in s]
    for word in ('HTREN', 'HTRSET', 'VACGAUGE'):
        assert any(word in s for s in said), (word, said)


def test_htrset_takes_one_argument_only(tmp_path):  # noqa: ANN001
    """⭐ **인자 하나**다 (운영자 확정) -- 옛 2인자 문법은 조용히 버리지 않는다.

    두 번째 값을 말없이 무시하면 *"Enable 도 같이 넣었다고 믿는"* 자리가 된다.
    """
    _app, sent, ctrl = _with_ctrl(tmp_path, [
        'abc>ICG HTRSET -100 1',       # 옛 문법
        'abc>ICG HTRSET nope',         # 수치가 아니다
    ])
    said = [s for s in sent if 'HTRSET' in s]
    assert sum('ERROR' in s for s in said) == 2, said
    assert ctrl.writes() == [], '거부했는데 컨트롤러에 썼다'


def test_the_onoff_words_are_the_same_as_expenable(tmp_path):  # noqa: ANN001
    """`ON|TRUE|1` · `OFF|FALSE|0` -- ⛔ 어휘 밖은 거부한다."""
    _app, sent, ctrl = _with_ctrl(tmp_path, [
        'abc>ICG HTREN true',
        'abc>ICG VACGAUGE 0',
        'abc>ICG HTREN maybe',         # 어휘 밖
    ])
    assert any('HTREN' in s and 'Enable=1' in s for s in sent), sent
    assert any('VACGAUGE' in s and 'Gauge=OFF' in s for s in sent), sent
    assert any('HTREN' in s and 'Invalid value: maybe' in s for s in sent), sent


def test_a_heater_command_during_acquisition_is_accepted_with_a_warning(  # noqa: ANN001
        tmp_path, caplog):
    """⭐ **거부하지 않는다** (운영자 확정 2026-09-04).

    `APPLYMOD09` 가 진공 VCPU 를 재시작해 그 프레임의 `DEWPRES` 가 결측이
    되지만, 그 결측은 받아들인다 -- 대신 경고를 남기고 **응답에 표시**한다.
    ⚠️ 이 시험이 뒤집히면(거부로 바뀌면) 운영자 확정과 어긋난다.
    """
    import logging

    caplog.set_level(logging.WARNING)
    # ⚠️ **노출을 길게 잡는 것이 의도다.**  `time_scale=0.02` 라 `EXP 1` 은
    # 프레임당 0.02초이고, 대본 사이 간격도 0.02초여서 **부하가 걸리면 취득이
    # 먼저 끝나** `busy` 가 False 로 읽힌다 (전체 스위트에서만 빨개졌다).
    # `EXP 30` = 프레임당 0.6초라 도착 순서가 확실해진다 -- 줄이지 말 것.
    _app, sent, ctrl = _with_ctrl(tmp_path, [
        'abc>ICG EXP 30', 'abc>ICG GO 2',
        'abc>ICG HTRSET -100',         # 취득 중에 들어온다
    ])
    said = [s for s in sent if 'HTRSET' in s]
    assert any('DONE' in s for s in said), said
    assert not any('ERROR' in s for s in said), said
    assert any('DuringAcquisition=1' in s for s in said), said
    assert any('취득 중에' in r.message for r in caplog.records), \
        '경고가 없다 -- 결측이 조용히 생긴다'


def test_the_gauge_query_says_where_the_answer_came_from(tmp_path):  # noqa: ANN001
    """⚠️ 조회 답은 **게이지에 물어본 값이 아니다** -- 출처를 함께 적는다.

    MKS 는 `IGS`(ON/OFF 상태)를 갖고 있지만 우리 VCPU 프로그램은 압력(`RD`)만
    보낸다.  그래서 우리가 아는 것은 되읽은 **설정값**뿐이다.
    """
    _app, sent, _ctrl = _with_ctrl(tmp_path, ['abc>ICG VACGAUGE'])
    said = [s for s in sent if 'VACGAUGE' in s]
    assert any('Origin=' in s and 'Method=ionen' in s for s in said), said


def test_the_new_heater_commands_check_their_argument_count(tmp_path):  # noqa: ANN001
    """⛔ 모자란 것도 남는 것도 **거부한다** -- 조용히 버리지 않는다.

    ⭐ 원 지시가 *"3개의 명령어를 만들고 arg 를 2개씩"* 이었다가 `HTRSET` 만
    1인자로 갈라졌다.  그래서 **명령마다 인자 수가 다르고**, 옛 문법으로
    보낸 값이 말없이 버려지면 *"넣었다고 믿는"* 자리가 생긴다.
    """
    _app, sent, ctrl = _with_ctrl(tmp_path, [
        'abc>ICG HTRFORCE 1',            # 2인자인데 하나
        'abc>ICG HTRRAMP 1 2 3',         # 2인자인데 셋
        'abc>ICG HTRPID 1 2',            # 3인자인데 둘
        'abc>ICG HTRPID 1 2 nope',       # 수치가 아니다
    ])
    said = [s for s in sent if 'ERROR' in s]
    assert sum('Usage:' in s for s in said) == 3, said
    assert any('Invalid D: nope' in s for s in said), said
    assert ctrl.writes() == [], '거부했는데 컨트롤러에 썼다'


def test_htrforce_says_that_the_pid_limit_does_not_apply(tmp_path):  # noqa: ANN001
    """⛔ `FORCE=1` 은 **다른 등급**이다 -- 응답이 그 사실을 늘 말한다.

    `HEATERALIMIT`(25.0)은 매뉴얼이 *"in PID mode"* 로 못박은 상한이라 force
    중에는 안 걸린다.  ⭐ 별도 운영 상한을 두지 않기로 했으므로(운영자 확정)
    **표시가 유일한 안전장치**다 -- 이 시험이 그것을 지킨다.
    """
    _app, sent, ctrl = _with_ctrl(tmp_path, ['abc>ICG HTRFORCE 1 3.5'])
    said = [s for s in sent if 'HTRFORCE' in s]
    assert any('DONE' in s and 'Force=1 Level=3.5' in s for s in said), said
    assert any('HEATERALIMIT does not apply' in s for s in said), said
    assert any('MOD10/HEATERAFORCELEVEL=3.5' in c for c in ctrl.writes())


def test_the_ramp_response_carries_the_converted_rate(tmp_path):  # noqa: ANN001
    """⭐ *"1 이 얼마나 느린가"* 를 그 자리에서 알게 한다 (1 mK/s = 3.6 K/h)."""
    _app, sent, _ctrl = _with_ctrl(tmp_path, ['abc>ICG HTRRAMP 1 1'])
    said = [s for s in sent if 'HTRRAMP' in s]
    assert any('RampRate=1' in s and '3.6 K/h' in s for s in said), said


def test_a_heater_query_answers_from_the_controller(tmp_path):  # noqa: ANN001
    """인자 없이 보내면 조회 -- 답은 캐시가 아니라 `RCONFIG` 되읽기다."""
    _app, sent, ctrl = _with_ctrl(tmp_path, [
        'abc>ICG HTRPID', 'abc>ICG HTRFORCE',
    ])
    assert any('HTRPID' in s and 'P=0 I=0 D=0' in s for s in sent), sent
    assert any('HTRFORCE' in s and 'Force=0 Level=0' in s for s in sent), sent
    assert ctrl.writes() == [], '조회인데 컨트롤러에 썼다'


# ---------------------------------------------------------------------------
# RADIONODE -- 런타임 CONNECT (운영자 지시 ④, 2026-09-04 구현)
# ---------------------------------------------------------------------------

def test_radionode_connect_names_what_is_missing(tmp_path):  # noqa: ANN001
    """⛔ **자격증명이 없으면 켜지 않는다** -- 무엇이 없는지 이름을 댄다.

    조용히 켜면 주기마다 실패 로그만 쌓이고 헤더는 sentinel 인데, 운영자는
    *"연결했다"* 고 믿는다.  ⭐ 배포 ini 는 자격증명 넷이 다 주석이라 이것이
    **첫 구동에서 실제로 만나는 갈래**다.
    """
    _app, sent = _drive_lines(tmp_path, ['abc>ICG RADIONODE CONNECT'])
    said = [s for s in sent if 'RADIONODE' in s]
    assert any('ERROR' in s for s in said), said
    for key in ('base_url', 'api_key', 'api_secret'):
        assert any(key in s for s in said), (key, said)


def test_radionode_connect_with_an_alias_is_the_device_branch(tmp_path):  # noqa: ANN001
    """⭐ **인자 유무로 뜻이 갈린다** -- 있으면 그 장치 하나다.

    ⚠️ 한 낱말이 두 뜻이라 응답이 어느 쪽인지 말해야 한다.  ini 기본이
    `backend=off` 라 장치 갈래는 *"먼저 CONNECT 하라"* 로 거절된다.
    """
    _app, sent = _drive_lines(tmp_path, ['abc>ICG RADIONODE CONNECT hebox'])
    said = [s for s in sent if 'RADIONODE' in s]
    assert any('ERROR' in s and 'CONNECT first' in s for s in said), said


def test_radionode_status_says_why_nothing_is_coming_in(tmp_path):  # noqa: ANN001
    """운영자가 묻는 것은 *"왜 자료가 안 들어오나"* 하나다."""
    _app, sent = _drive_lines(tmp_path, ['abc>ICG RADIONODE'])
    said = [s for s in sent if 'RADIONODE' in s]
    assert any('Backend=off' in s and 'Polling=no' in s for s in said), said
    assert any('missing' in s for s in said), said


def test_radionode_reconnect_points_at_connect(tmp_path):  # noqa: ANN001
    """`RECONNECT` 는 **주기를 안 기다리는 것**이지 켜는 것이 아니다."""
    _app, sent = _drive_lines(tmp_path, ['abc>ICG RADIONODE RECONNECT'])
    said = [s for s in sent if 'RADIONODE' in s]
    assert any('ERROR' in s and 'RADIONODE CONNECT' in s for s in said), said

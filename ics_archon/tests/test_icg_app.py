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
        assert cards['DATASRC'].startswith("'ARCHON_GUIDE")
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

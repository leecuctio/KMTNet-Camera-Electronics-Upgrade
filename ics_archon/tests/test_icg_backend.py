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

from icg_archon import guidecards  # noqa: E402
from icg_archon.backend import GuideBackend  # noqa: E402
from icg_archon.config import IcgCfg  # noqa: E402

from fake_archon import FakeArchon  # noqa: E402

NX, NY = 8, 4

ACF_TEXT = """[CONFIG]
TRIGOUTFORCE=0
TRIGOUTLEVEL=1
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DevNote 10장(실기 시험 2026-09-01~02) 반영 -- 죽은 전제가 코드에 되살아나지 않게.

10.10-3 의 교훈: **잘못된 전제는 전수로**.  이 파일은 그 전제 하나하나에 시험을
하나씩 세운다 -- 다시 박히면 여기서 걸린다.
"""

from __future__ import annotations

import asyncio
import logging
import os

import pytest

import ics_archon  # noqa: F401

from ics_archon import config as acfg_mod  # noqa: E402
from ics_archon.archon import parse  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE_ACF = os.path.join(ROOT, 'acf', 'KMTK_GUI_162_STA0201_R2615.acf')
SCI_ACF = os.path.join(ROOT, 'acf', 'KMTC_SCI_101_STA0284_R2609_MK.acf')


# ---------------------------------------------------------------------------
# 10.3  BUFnHEIGHT 는 라인 수가 아니다 (split) -- PCTREAD 50% 상한
# ---------------------------------------------------------------------------

def test_progress_of_uses_linecount_not_buffer_height():
    """⭐ `FRAMEMODE=2` 에서 `BUFnHEIGHT = 2 x LINECOUNT` -- HEIGHT 분모면 50% 상한.

    2026-09-01 실측(DevNote 10.3): probe 3단계가 49% 에서 완료로 넘어갔다.
    """
    fields = {'RBUF': '1', 'WBUF': '1',
              'BUF1FRAME': '3', 'BUF1COMPLETE': '0',
              'BUF1WIDTH': '19200', 'BUF1HEIGHT': '9400',
              'BUF1SAMPLE': '0', 'BUF1BASE': '0', 'BUF1LINES': '4700'}
    fs = parse.newest(fields)
    assert fs.progress == 50                    # 구식 셈 -- 라인이 다 찼는데 50
    assert fs.progress_of(4700) == 99           # LINECOUNT 분모 (100 은 완료 뒤)
    fields['BUF1LINES'] = '2350'
    fs = parse.newest(fields)
    assert fs.progress_of(4700) == 50 and fs.progress == 25
    assert fs.progress_of(0) == fs.progress     # 0 이면 HEIGHT 로 물러난다


@pytest.mark.repo_only
def test_controller_learns_linecount_from_the_acf():
    """컨트롤러가 ACF 의 `LINECOUNT` 를 진행률 분모로 들고 있는가."""
    from ics_archon.archon.controller import ArchonController
    from icg_archon.config import IcgCfg

    for path, expect in ((GUIDE_ACF, 1033), (SCI_ACF, 4700)):
        icfg = IcgCfg()
        icfg.acf = {'G': path}
        ctrl = ArchonController('G', icfg)
        assert ctrl.lines_total == 0
        ctrl.parse_acf(path)
        assert ctrl.lines_total == expect, path


# ---------------------------------------------------------------------------
# 10.4  주기 13.27 s · 10.6  잠금은 주기보다 짧아야 한다
# ---------------------------------------------------------------------------

def test_min_frame_period_is_the_measured_one():
    """12.0(labtest 11.3 초 유래) -> **13.27** (두 유닛 실측, IntMS=0·NoIntMS=500)."""
    assert acfg_mod.MIN_FRAME_PERIOD == 13.27


def test_fetch_timeout_above_the_period_is_flagged_when_locking(tmp_path):
    """⭐ `lock_buffer=true` 인데 FETCH 상한 >= 주기면 기동에서 알린다 (10.6).

    잠금을 쥔 채 경계를 넘으면 엔진이 쓰던 버퍼를 재사용해 다음 장이 덮인다.
    `fetch_timeout=0`(크기 유도, 344 MiB -> 344초)이 그 전형이다.
    """
    from test_ini_cards import ACF_TEXT, INI_OVERRIDES, write_ini
    from ics_sim import config as simcfg

    acf = tmp_path / 'KMTC_SCI_101_STA0284_R2608_MK.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')

    def notes(fetch_timeout, lock):  # noqa: ANN001
        over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
        ini = write_ini(tmp_path, over, str(acf))
        cfg, acfg = simcfg.load(ini), acfg_mod.load(ini)
        acfg.fetch_timeout, acfg.lock_buffer = fetch_timeout, lock
        return [n for n in acfg_mod.validate(acfg, tuple(cfg.node.ccds), cfg)
                if '다음 장이 덮인다' in n]

    assert notes(0.0, True), '344초 유도 상한이 주기를 넘는데 조용하다'
    assert notes(30.0, True), '종전 값 30초도 주기 13.27초를 넘는다'
    assert not notes(10.0, True)
    # 잠그지 않으면 이 위험은 없다 (대신 recheck_after_fetch 가 짝이다)
    assert not notes(0.0, False)


@pytest.mark.repo_only
def test_the_shipped_ini_keeps_fetch_timeout_under_the_period():
    acfg = acfg_mod.load(os.path.join(ROOT, 'ics_archon.ini'))
    assert 0 < acfg.fetch_timeout < acfg_mod.MIN_FRAME_PERIOD


# ---------------------------------------------------------------------------
# 10.9  fetch() -- LOCK%d 가 try 안: 잠금 명령이 죽어도 LOCK0 을 탄다
# ---------------------------------------------------------------------------

def test_lock0_is_sent_even_when_the_lock_command_itself_fails():
    """`LOCK%d` 응답이 타임아웃으로 죽어도 컨트롤러는 이미 잠겼을 수 있다 --
    `finally` 의 `LOCK0` 을 타야 한다 (DevNote 8.14 -> 10.9)."""
    from test_backend import _fs, _stub_fetch
    from ics_archon.archon.controller import ArchonController, ArchonError

    acfg = acfg_mod.ArchonCfg()
    acfg.lock_buffer = True
    acfg.recheck_after_fetch = False
    ctrl = ArchonController('MK', acfg)
    seen = _stub_fetch(ctrl, before_frame=7, after_frame=7, nbytes=32)

    orig = ctrl.cmd

    async def cmd(c, *a, **k):  # noqa: ANN001, ANN202
        if c.startswith('LOCK') and c != 'LOCK0':
            seen['cmds'].append(c)
            raise ArchonError('응답 없음 (모사)', cmd=c)
        return await orig(c, *a, **k)

    ctrl.cmd = cmd
    with pytest.raises(ArchonError):
        asyncio.run(ctrl.fetch(_fs(7), 32))
    assert seen['cmds'] == ['LOCK1', 'LOCK0'], seen['cmds']


# ---------------------------------------------------------------------------
# icg -- 형태 가드 · fetch_timeout 검사
# ---------------------------------------------------------------------------

@pytest.mark.repo_only
def test_acftiming_recognises_the_guide_script_and_rejects_science():
    """`acftiming` 은 guide 스크립트 형태 전용이다 -- science 를 대면 셈하지 않는다.

    science ACF 에 억지로 씌우면 13.65 s 가 나오는데 그건 검증도 계산도 아니다
    (DevNote 9.15).
    """
    from ics_archon.archon.controller import ArchonController
    from icg_archon import acftiming
    from icg_archon.config import IcgCfg

    def cfg_of(path):  # noqa: ANN001, ANN202
        icfg = IcgCfg()
        icfg.acf = {'G': path}
        ctrl = ArchonController('G', icfg)
        ctrl.parse_acf(path)
        return ctrl.config

    assert acftiming.script_matches(cfg_of(GUIDE_ACF)) == []
    bad = acftiming.script_matches(cfg_of(SCI_ACF))
    assert bad and any(b.startswith('LINE11=') for b in bad), bad


@pytest.mark.repo_only
def test_guide_backend_refuses_timing_from_a_science_acf():
    from ics_sim import config as simcfg

    from icg_archon.backend import GuideBackend
    from icg_archon.config import load

    ini = os.path.join(ROOT, 'icg_archon.ini')
    icfg = load(ini)
    icfg.acf = {'G': SCI_ACF}
    icfg.exptime_min = 4.2
    be = GuideBackend(simcfg.load(ini), icfg)
    assert be.timing is None
    assert be.frame_floor() == 4.2


@pytest.mark.repo_only
def test_guide_fetch_timeout_must_sit_under_the_frame_floor(caplog):
    """⭐ guide 도 같은 제약이다 (10.6) -- 잠금 상한 = FETCH 상한 < 프레임 하한.

    ⚠️ 하한을 리터럴로 적지 않는다 -- ACF 판이 오르면 값이 바뀐다
    (R2609 1.375 s -> R2610 1.251 s).  `frame_floor()` 가 ACF 에서 셈한
    값과 대본다.
    """
    from ics_sim import config as simcfg

    from icg_archon.backend import GuideBackend
    from icg_archon.config import load

    ini = os.path.join(ROOT, 'icg_archon.ini')

    icfg = load(ini)
    icfg.acf = {'G': GUIDE_ACF}
    with caplog.at_level(logging.WARNING, logger='icg_archon.backend'):
        be = GuideBackend(simcfg.load(ini), icfg)
    floor = be.frame_floor()
    assert icfg.fetch_timeout < floor,         'ini 의 fetch_timeout(%s) 이 하한(%.4f s) 위다' % (icfg.fetch_timeout, floor)
    assert not [r for r in caplog.records if 'fetch_timeout' in r.getMessage()]

    for bad in (30.0, 0.0):                  # 종전 기본값 · 크기 유도(60 s)
        caplog.clear()
        icfg = load(ini)
        icfg.acf = {'G': GUIDE_ACF}
        icfg.fetch_timeout = bad
        with caplog.at_level(logging.WARNING, logger='icg_archon.backend'):
            GuideBackend(simcfg.load(ini), icfg)
        hits = [r for r in caplog.records if 'fetch_timeout' in r.getMessage()]
        assert hits and '덮인다' in hits[0].getMessage(), bad


# ---------------------------------------------------------------------------
# 10.5  8.9 문구가 코드에 남아 있지 않다
# ---------------------------------------------------------------------------

@pytest.mark.repo_only
def test_no_live_code_blames_fetch_for_stalling_readout():
    """"FETCH 가 다음 독출을 멈춘다(8.9)" 를 원인으로 지목하는 살아 있는 코드 문구가
    없어야 한다 -- 주석·경고문 포함 (DevNote 10.9 의 icg 항목)."""
    import glob

    import re

    offenders = []
    for pat in ('icg_archon/*.py', 'ics_archon/*.py', 'ics_archon/archon/*.py', '*.ini'):
        for path in glob.glob(os.path.join(ROOT, pat)):
            with open(path, encoding='utf-8', errors='replace') as fh:
                text = fh.read()
            # 주석이 줄바꿈으로 갈라져 있어도 잡는다 -- 줄 끝 + 다음 줄의 들여쓰기·`#`
            # 를 공백 하나로 접는다 (첫 판은 줄 단위라 두 줄에 걸친 문구를 놓쳤다).
            flat = re.sub(r'\s*\n\s*#?\s*', ' ', text)
            for phrase in ('FETCH 가 다음 독출', '실효 하한은 `하한 + FETCH`'):
                if phrase in flat:
                    offenders.append('%s: %r' % (os.path.relpath(path, ROOT), phrase))
    assert not offenders, offenders


# ---------------------------------------------------------------------------
# 가짜 컨트롤러가 실기의 두 거동을 안다 -- split 의 LINES 상한 · POWERON 의 APPLYALL 전제
# ---------------------------------------------------------------------------

def test_fake_split_mode_caps_lines_at_linecount_not_height():
    """10.3 -- 가짜가 FRAMEMODE=0 만 모사해서 `parse.progress` 의 50% 결함이 시험을
    다 통과했다.  split 판 가짜는 HEIGHT 를 그대로 내고 LINES 는 절반에서 멈춰야 한다."""
    from fake_archon import FakeArchon

    fk = FakeArchon(width=8, height=8, framemode=2, readout_ticks=4, tick=0.0)
    try:
        assert fk.linecount == 4 and fk.height == 8
        fk._one_frame()                              # 서버 없이 프레임 하나를 돌린다
        f = fk._frame_fields()
        wb = int(f['WBUF']) or 1
        done = [n for n in (1, 2, 3) if f['BUF%dCOMPLETE' % n] == '1'][0]
        assert f['BUF%dHEIGHT' % done] == '8'
        assert f['BUF%dLINES' % done] == '4', f      # HEIGHT 의 절반에서 멈춘다
        # parse 로 넣어 보면 -- 구식 셈은 50, LINECOUNT 분모는 99
        fields = dict(f)
        fields['WBUF'] = str(done)                   # 쓰는 중인 것처럼
        fields['BUF%dCOMPLETE' % done] = '0'
        fs = parse.newest(fields)
        assert fs.progress == 50 and fs.progress_of(4) == 99
    finally:
        fk.shutdown()
    del wb


def test_fake_refuses_poweron_without_applyall_this_session():
    """10.2 -- 매뉴얼 p.51: APPLYALL 없이 POWERON 은 `?xx`.  가짜도 그렇게 답해야
    `controller.power_on()` 의 진단 문구 경로가 시험에 닿는다."""
    import socket

    from fake_archon import FakeArchon

    fk = FakeArchon(width=8, height=4, applied=False)
    fk.start()
    try:
        def ask(cmd):  # noqa: ANN001, ANN202
            with socket.create_connection(('127.0.0.1', fk.port), timeout=2) as c:
                c.sendall(('>01%s\n' % cmd).encode('ascii'))
                return c.recv(64)

        assert ask('POWERON').startswith(b'?'), 'APPLYALL 없이 POWERON 을 받아 줬다'
        assert ask('APPLYALL').startswith(b'<01')
        assert ask('POWERON').startswith(b'<01'), 'APPLYALL 뒤인데 거부했다'
        assert ask('REBOOT').startswith(b'<01')
        assert ask('POWERON').startswith(b'?'), 'REBOOT 뒤인데 APPLYALL 없이 받아 줬다'
    finally:
        fk.shutdown()


def test_power_on_names_the_missing_applyall_when_the_controller_refuses():
    """10.2·10.10-6 -- 첫 관문에서 한 시간을 먹은 것이 `?02` 한 줄이었다.

    `POWERON` 이 `?xx` 로 거부되면 `power_on()` 이 p.51 의 전제(이 세션의 APPLYALL)
    를 진단 문구로 붙여 올린다.  프레이밍 오류(reply_error=False)는 그대로 올린다.
    """
    from ics_archon.archon.controller import ArchonController, ArchonError

    acfg = acfg_mod.ArchonCfg()
    ctrl = ArchonController('MK', acfg)

    async def refuse(cmd, *a, **k):  # noqa: ANN001, ANN202
        raise ArchonError('컨트롤러가 명령을 거부했다 (?02): %s' % cmd,
                          cmd=cmd, reply_error=True)

    ctrl.cmd = refuse
    with pytest.raises(ArchonError) as ei:
        asyncio.run(ctrl.power_on(wait=0))
    assert 'APPLYALL' in str(ei.value) and 'p.51' in str(ei.value), str(ei.value)
    assert ei.value.reply_error
    assert ctrl.power_attempted and not ctrl.powered

    async def framing(cmd, *a, **k):  # noqa: ANN001, ANN202
        raise ArchonError('응답 없음', cmd=cmd)

    ctrl.cmd = framing
    with pytest.raises(ArchonError) as ei:
        asyncio.run(ctrl.power_on(wait=0))
    assert 'APPLYALL' not in str(ei.value), '프레이밍 오류에 APPLYALL 진단을 붙였다'


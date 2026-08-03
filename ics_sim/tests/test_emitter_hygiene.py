#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""메시지 오염 방지 검증 (DevNote 5장).

레거시 ICS 는 커맨드워드 슬롯을 비우지 않아 비동기 상태 메시지가 엉뚱한
커맨드워드를 달고 나갔다.  여기서는 두 방향으로 확인한다:

  정방향 -- 시뮬이 내는 **모든** 메시지가 깨끗한가
  역방향 -- 레거시의 실제 오염 샘플을 검증기가 **빠짐없이 잡아내는가**

역방향이 없으면 검증기가 아무것도 안 하는 껍데기여도 정방향은 통과한다.
"""

from __future__ import annotations

import os

import pytest

from conftest import (DARK_SCRIPT, GON5_SCRIPT, OBJECT_SCRIPT, FIXTURES,
                      drive, make_config)
from ics_sim.emitter import split_cmdword, validate

BUG_PATTERNS = os.path.join(FIXTURES, 'bug_patterns.txt')


def load_bug_patterns() -> list[tuple[int, str]]:
    if not os.path.exists(BUG_PATTERNS):
        return []
    out: list[tuple[int, str]] = []
    with open(BUG_PATTERNS, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            count, _, msg = line.partition('\t')
            out.append((int(count), msg))
    return out


# -- 정방향: 시뮬 출력은 깨끗해야 한다 -----------------------------------

@pytest.mark.parametrize('script, name', [
    (DARK_SCRIPT, 'dark'),
    (OBJECT_SCRIPT, 'object'),
    (GON5_SCRIPT, 'go5'),
])
def test_no_violations_in_full_cycle(script, name):
    run = drive(script, settle=1.0)
    assert run.violations == [], \
        f'{name} 사이클에서 오염 발생: {run.violations[:3]}'


@pytest.mark.parametrize('mode', ['legacy', 'merged'])
def test_clean_in_both_node_modes(mode):
    cfg = make_config(node__emit_node_mode=mode)
    run = drive(DARK_SCRIPT, cfg)
    assert run.violations == []


def test_expstatus_not_repeated_after_shutter_closes():
    """셔터가 닫힌 뒤에는 EXPSTATUS=INTEGRATING 을 보내지 않는다.

    레거시는 노출마다 아래를 반복했다 (DevNote 3.2.2):
        ICS>OBS STATUS:  STATUS: EXPSTATUS=INTEGRATING
        ICS>OBS STATUS:   Shutter=Closed .. EXPSTATUS=INTEGRATING
    """
    run = drive(OBJECT_SCRIPT, settle=1.0)
    to_obs = run.to('OBS')
    closed = next(i for i, m in enumerate(to_obs) if 'Shutter=Closed' in m)
    after = to_obs[closed + 1:]
    assert not [m for m in after if 'EXPSTATUS=INTEGRATING' in m], \
        f'셔터 닫힘 이후 INTEGRATING 재발신: {after[:3]}'


def test_expstatus_transitions_emitted_once_each():
    """각 노출 국면 알림은 프레임당 정확히 1회."""
    run = drive(DARK_SCRIPT)
    to_obs = run.to('OBS')
    for status in ('INITIALIZING', 'ERASE', 'READOUT'):
        hits = [m for m in to_obs if m.endswith(f'EXPSTATUS={status}')]
        assert len(hits) == 1, f'{status} 알림이 {len(hits)}회'


def test_expstatus_only_goes_to_obs():
    """EXPSTATUS= 만 실린 알림이 IC 앞으로 새어 나가면 안 된다.

    레거시가 IC 로 보내던 텔레메트리 중계에는 EXPSTATUS= 가 실려 있었는데,
    그건 OBS 앞이 아니라서 안전했다.  신규가 편의상 브로드캐스트하거나 OBS 로도
    보내면 CamStatus 가 INT_1 으로 역행한다 (DevNote 3.2.1).
    """
    run = drive(DARK_SCRIPT)
    for msg in run.sent:
        dest = msg.split('>', 1)[1].split(' ', 1)[0].upper()
        if dest in ('OBS', 'AL', 'ALL'):
            continue
        # IC 앞 메시지에 EXPSTATUS= 가 있어도 되지만, 텔레메트리 중계에
        # 딸린 것이어야 한다 (AUXSTATUS/TCSSTATUS).
        if 'EXPSTATUS=' in msg:
            assert 'AUXSTATUS' in msg or 'TCSSTATUS' in msg, \
                f'IC 앞으로 순수 EXPSTATUS 알림이 나갔다: {msg}'


# -- 역방향: 레거시 오염을 실제로 잡아내는가 -----------------------------

@pytest.mark.skipif(not load_bug_patterns(), reason='bug_patterns.txt 없음')
@pytest.mark.parametrize('count, message', load_bug_patterns())
def test_legacy_contamination_is_detected(count, message):
    """`tests/fixtures/bug_patterns.txt` 의 모든 샘플이 위반으로 잡혀야 한다.

    이 픽스처는 `tools/scan_legacy_logs.py patterns` 가 실측 로그에서 뽑은
    것이다.  검증기가 느슨해지면 여기서 먼저 깨진다.
    """
    problems = validate(message)
    assert problems, f'놓친 오염 ({count}회 관측): {message}'


def test_validator_accepts_legitimate_messages():
    """정상 메시지를 오탐하지 않는지 -- 실측 로그에서 가져온 표본."""
    good = [
        'ICS>OBS DONE: PROJID  ProjID=OBS',
        "ICS>OBS DONE: DARK  ImageType=DARK ObjectName='begin' EXP=30",
        'ICS>OBS DONE: EXP  ExpTime=30 seconds.',
        'ICS>OBS DONE: EXPNUM  Filename=20250902.057288 EXPSTATUS=READOUT',
        'ICS>OBS STATUS:    EXPSTATUS=INITIALIZING',
        'ICS>OBS STATUS:   Remaining=24 sec. of 30 sec.  EXPSTATUS=INTEGRATING',
        'ICS>OBS STATUS:   Image 1 of 5 complete. EXPSTATUS=IDLE',
        'ICS>OBS DONE:   EXPSTATUS=IDLE',
        'K.IC>ICS DONE: INITIALIZE  Initialization Complete.',
        'K.IC>ICS DONE:   Erase Cycle Complete.',
        'K.IC>OBS STATUS: SHOPEN  Shutter=Open',
        'K.IC>OBS STATUS:   Integration Remaining=49 sec.',
        'K.IC>OBS STATUS:   Shutter=Closed Integration Remaining=0 sec.',
        'K.IC>OBS STATUS: GO  PCTREAD=6',
        'K.IC>OBS STATUS: GO  PCTREAD=100 Acquisition Complete. '
        'Disk Transfer Starting.',
        'K.IC>ICS STATUS: GO  Acquisition Complete',
        'K.IC>ICS STATUS: GO  Disk Write Complete',
        'K.CB>ICS DONE: Wrote LASTFILE=/mnt/ICSData/KMTNk.20240303.039400.fits '
        'RATE=8656 KB/sec',
        'ICS>OBS ERROR: EXP  Cannot change EXPTIME for ImgType=BIAS',
        'ICS>OBS ERROR:   Failed to initialize one or more ICs',
        "K.IC>ICS ERROR: OBCT  Didn't understand OBCT BLG37 ?",
        "K.CB>OBS WARNING: FITS file '/mnt/ICSData/KMTNk.20250902.050666.fits' "
        "already exists, writing as '/mnt/ICSData/250902.000.fits' instead",
        'K.IC>ICS DONE: STATUS  Inst=KMTNk  DetectorID=K Driving=1 '
        '+FIBERS +SYNCH Build=KS2016-01-13:1370',
    ]
    for line in good:
        assert validate(line) == [], f'오탐: {line} -> {validate(line)}'


# -- bug_compat: 레거시 재현 모드 ----------------------------------------

def test_bug_compat_reproduces_contamination():
    """bug_compat 을 켜면 레거시 오염이 실제로 나타난다.

    이 모드는 골든 대조 전용이며 기본은 꺼짐이다.  꺼진 상태에서 깨끗하다는
    것만으로는 "검증기가 켜져 있다"는 증거가 되지 못하므로, 켰을 때 실제로
    더러워지는지도 확인한다.
    """
    cfg = make_config(behavior__bug_compat=True)
    run = drive(DARK_SCRIPT, cfg)
    assert run.violations, 'bug_compat 모드인데 오염이 재현되지 않았다'
    stale = [line for line, probs in run.violations if 'stale_cmdword' in probs]
    assert stale, f'스테일 커맨드워드가 나타나지 않았다: {run.violations[:3]}'


def test_bug_compat_still_satisfies_obsagent():
    """오염이 있어도 OBSAgent 규약은 만족한다.

    "이 버그는 OBSAgent 동작에 영향이 없다"가 검증 대상이다 -- 그래서 레거시가
    수년간 이 상태로 운용될 수 있었다.
    """
    from ics_sim.obsagent_model import CamStatusReplay
    cfg = make_config(behavior__bug_compat=True)
    run = drive(DARK_SCRIPT, cfg, settle=1.0)
    replay = CamStatusReplay()
    for when, msg in run.timed:
        replay.feed(msg, when)
    assert replay.state == 'IDLE_3'
    assert replay.fits_saved == 1


# -- split_cmdword 규칙 ---------------------------------------------------

@pytest.mark.parametrize('rest, cmd, body', [
    ('PROJID  ProjID=OBS', 'PROJID', 'ProjID=OBS'),
    ('  EXPSTATUS=INITIALIZING', '', 'EXPSTATUS=INITIALIZING'),
    ('  Erase Cycle Complete.', '', 'Erase Cycle Complete.'),
    ('GO  PCTREAD=6', 'GO', 'PCTREAD=6'),
    ('  Shutter=Closed Integration Remaining=0 sec.', '',
     'Shutter=Closed Integration Remaining=0 sec.'),
    ('  Wrote LASTFILE=/x RATE=1 KB/sec', '', 'Wrote LASTFILE=/x RATE=1 KB/sec'),
])
def test_split_cmdword(rest, cmd, body):
    assert split_cmdword(rest) == (cmd, body)

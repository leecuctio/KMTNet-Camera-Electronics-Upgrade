#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`Acquisition Complete.` 를 컨트롤러 프레임별로 낼지 -- 스위치와 그 기본값.

**목 지시 2026-08-24.**  `readout()` 계약은 진행률 정수만 흘려보내므로 "어느
컨트롤러가 끝났나" 를 표현할 자리가 없었다.  선택 훅
`DetectorBackend.readout_events()` 가 그 경계를 만든다.

⚠️ **`ics_sim` 쪽은 간단한 모사다** (목 지시).  시뮬은 CCD 4개가 다
소프트웨어라 독출 경로에 컨트롤러라는 경계가 없고, 두 대를 진짜로 모사하려면
`[readout]` 모델 자체를 나눠야 한다 -- 비용이 이득보다 크다는 판단이다.
**병렬 독출의 실구현은 `ics_archon` 에 있다.**  여기서 지키는 것은 둘이다:

1. 스위치가 꺼진 **기본값에서 거동이 종전과 같다** (4개를 같은 틱에).
2. 켰을 때도 **개수가 4개**다 -- 개수가 곧 규약이다 (DevNote 3장 2항).
"""

from __future__ import annotations

import pytest

from conftest import DARK_SCRIPT, drive, make_config

from ics_sim import rawpair


def acq_messages(run) -> list[str]:  # noqa: ANN001
    return [m for m in run.sent if 'Acquisition Complete.' in m]


def senders(msgs: list[str]) -> list[str]:
    """`M.IC>OBS ...` -> `M`."""
    return [m.split('.IC>')[0] for m in msgs]


def test_default_is_off_and_keeps_todays_behaviour():
    """**기본은 꺼짐이다.**  4개가 같은 틱에 나가 산포가 사실상 0 이다.

    그 산포 0 이 DevNote 3.3 의 1.8초 창을 **구조적으로** 보장한다 -- 켜면
    그 보장이 두 컨트롤러의 실제 시차에 좌우된다.  실기 시차 실측 전에는
    이득 크기를 알 수 없으므로 기본값을 바꾸지 않는다.
    """
    cfg = make_config()
    assert cfg.readout.acq_per_frame is False
    run = drive(DARK_SCRIPT, cfg)
    msgs = acq_messages(run)
    assert len(msgs) == 4, msgs
    # 같은 틱이므로 첫 것과 마지막 것의 간격이 사실상 0 이다.
    when = [t for t, m in run.timed if 'Acquisition Complete.' in m]
    assert len(when) == 4
    assert when[-1] - when[0] < 0.5, when


@pytest.mark.parametrize('per_frame', [False, True])
def test_the_count_is_four_either_way(per_frame):
    """**개수가 곧 규약이다.**  스위치는 "언제" 만 바꾼다."""
    cfg = make_config()
    cfg.readout.acq_per_frame = per_frame
    run = drive(DARK_SCRIPT, cfg)
    assert len(acq_messages(run)) == 4
    assert sum('Wrote' in m for m in run.sent) == 8      # CB 4 + ICS 중계 4
    assert sum('EXPSTATUS=IDLE' in m for m in run.sent) == 1


def test_per_frame_groups_the_messages_by_controller():
    """켜면 컨트롤러 묶음으로 나간다 -- MK(M/K) 다음 NT(N/T)."""
    cfg = make_config()
    cfg.readout.acq_per_frame = True
    run = drive(DARK_SCRIPT, cfg)
    who = senders(acq_messages(run))
    groups = dict(rawpair.CONTROLLERS)
    assert set(who[:2]) == set(groups['MK']), who
    assert set(who[2:]) == set(groups['NT']), who


def test_the_sim_backend_offers_the_hook_so_the_path_is_exercised():
    """시뮬이 훅을 내놓아야 `ics_sim` 시험도 새 분기를 밟는다.

    훅이 없으면 시퀀서가 종전 경로로 떨어지고, 그러면 **새 분기가 실기에서
    처음 도는** 상황이 된다 -- DevNote 11.25 가 경고한 부류의 반대편이다.
    """
    from ics_sim.hardware.sim import SimBackend

    backend = SimBackend(make_config())
    events = backend.readout_events('K')
    assert events is not None
    assert hasattr(events, '__aiter__')

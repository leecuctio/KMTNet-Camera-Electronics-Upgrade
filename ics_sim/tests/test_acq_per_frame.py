#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`Acquisition Complete.` 는 **컨트롤러 프레임별로** 나간다 (스위치 없음).

**목 지시 2026-08-24 · 스위치 제거 2026-09-04.**  `readout()` 계약은 진행률
정수만 흘려보내므로 "어느 컨트롤러가 끝났나" 를 표현할 자리가 없었다.  선택 훅
`DetectorBackend.readout_events()` 가 그 경계를 만든다.

⚠️ **`[readout] acq_per_frame` 스위치는 없어졌다** (운영자 확정 2026-09-04) --
*"스위치 없애고 무조건 켜짐과 같이 구동해줘."*  ⛔ 그래서 4개의 산포가 이제
**두 컨트롤러의 실제 시차**이고, 종전에 스위치를 꺼 둠으로써 얻던 *"같은 틱 =
산포 0"* 이라는 1.8초 창의 **구조적 보장은 사라졌다** (DevNote 3.3).
⏳ 남은 안전장치는 `acq_skew_warn` 하나이고, **첫 실기에서 시차를 재서 그 값을
맞추는 것**이 남은 일이다.

⚠️ **`ics_sim` 쪽은 간단한 모사다** (목 지시).  시뮬은 CCD 4개가 다
소프트웨어라 독출 경로에 컨트롤러라는 경계가 없고, 두 대를 진짜로 모사하려면
`[readout]` 모델 자체를 나눠야 한다 -- 비용이 이득보다 크다는 판단이다.
**병렬 독출의 실구현은 `ics_archon` 에 있다.**  여기서 지키는 것은 둘이다:

1. **개수가 4개**다 -- 개수가 곧 규약이다 (DevNote 3장 2항).
2. **컨트롤러 묶음으로** 나간다 (MK 몫 다음 NT 몫).
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


def test_there_is_no_switch_any_more():
    """⛔ **`acq_per_frame` 설정은 없다** (운영자 확정 2026-09-04).

    ⚠️ 남겨 두면 *"꺼면 종전 거동"* 이라는 죽은 전제가 문서·시험에 계속 살아
    있게 된다 -- 이 저장소가 여러 번 겪은 부류다.  키를 ini 에 적어도 조용히
    무시되는 것이 아니라 **필드 자체가 없어야** 그 오해가 안 생긴다.
    """
    cfg = make_config()
    assert not hasattr(cfg.readout, 'acq_per_frame')


def test_the_count_is_still_four():
    """**개수가 곧 규약이다** -- 프레임별로 갈라 내보내도 4개다."""
    run = drive(DARK_SCRIPT, make_config())
    assert len(acq_messages(run)) == 4
    assert sum('Wrote' in m for m in run.sent) == 8      # CB 4 + ICS 중계 4
    assert sum('EXPSTATUS=IDLE' in m for m in run.sent) == 1


def test_the_messages_are_grouped_by_controller():
    """컨트롤러 묶음으로 나간다 -- MK(M/K) 다음 NT(N/T).  **조건 없이.**"""
    run = drive(DARK_SCRIPT, make_config())
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

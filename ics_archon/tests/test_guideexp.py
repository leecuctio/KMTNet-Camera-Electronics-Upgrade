#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`GUIEXPCTRL` -- science 독출 앞뒤로 guide 노출을 막고 푼다 (운영자 2026-09-04).

운영자 문면: *"`EXPENABLE` 은 ICS 노출 전/후에 보내는 게 아니고, ICS(science
CCD) **독출 2초 전**과 **독출완료 직후**에 보내는 거야.  독출 전에 0, 독출 후에
1."*

지키려는 것 다섯:

* ⭐ **독출 시작 `lead` 초 전**에 막는다 -- guide 가 이미 시작한 프레임을 마칠
  시간을 준다.
* ⭐ **국면이 `READOUT` 이면 즉시** 막는다 -- BIAS/DARK 처럼 적분 국면이 없어
  앞을 못 내다보는 갈래의 안전망이다.
* ⭐ **`READOUT` 을 벗어나면** 푼다 (`WRITING`/`IDLE`) -- `FETCH` 가 독출 안이라
  그 다음이어야 한다 (운영자 단서: *"혹시 Fetch 에 방해가 된다면 fetch 후에"*).
* ⛔ **같은 상태를 되풀이해 보내지 않는다** -- 틱마다 보내면 하룻밤에 수만 줄이다.
* ⚠️ **종료할 때 잠금을 풀지 않는다** -- 독출 중에 죽었으면 guide 가 그 구간에
  노출한다.
"""

from __future__ import annotations

import asyncio
import logging

import pytest

import ics_archon  # noqa: F401

from ics_archon import guideexp as ge  # noqa: E402
from ics_archon.guideexp import GuideExpControl  # noqa: E402

INF = float('inf')


class Harness:
    def __init__(self, **over) -> None:  # noqa: ANN003
        self.sent: list[tuple[str, str, str]] = []
        self.tasks: list = []
        opts = dict(node='ICG', lead=2.0, reply_timeout=5.0, enabled=True)
        opts.update(over)
        self.ctl = GuideExpControl(
            opts['node'], opts['lead'], self._spawn, self._emit,
            opts['reply_timeout'], enabled=opts['enabled'])

    def _spawn(self, coro):  # noqa: ANN001, ANN202
        task = asyncio.ensure_future(coro)
        self.tasks.append(task)
        return task

    def _emit(self, dest: str, cmdword: str, body: str = '') -> str:
        self.sent.append((dest, cmdword, body))
        return body

    @property
    def words(self) -> list[str]:
        return [b for _d, _c, b in self.sent]


def _run(fn):  # noqa: ANN001, ANN202
    async def wrap():  # noqa: ANN202
        h = Harness()
        fn(h)
        await h.ctl.close()
        return h
    return asyncio.run(wrap())


# -- 막기 -------------------------------------------------------------------


def test_it_blocks_two_seconds_before_readout():
    """⭐ 독출 시작 `lead` 초 전에 `EXPENABLE 0`."""
    h = _run(lambda h: h.ctl.on_phase('INTEGRATING', 1.5))
    assert h.sent == [('ICG', 'EXPENABLE', '0')], h.sent
    assert h.ctl.state == ge.BLOCKED


def test_it_stays_quiet_while_the_readout_is_still_far_away():
    """⚠️ 노출이 30초 남았는데 막으면 guide 가 그만큼 논다."""
    h = _run(lambda h: h.ctl.on_phase('INTEGRATING', 30.0))
    assert h.sent == [], h.sent
    assert h.ctl.state == ge.UNKNOWN


def test_the_readout_phase_blocks_even_without_a_lead():
    """⭐ BIAS/DARK 는 적분 국면이 없다 -- `READOUT` 자체가 신호다."""
    h = _run(lambda h: h.ctl.on_phase('READOUT', INF))
    assert h.words == ['0'], h.sent


@pytest.mark.parametrize('phase', ['WRITING', 'IDLE'])
def test_it_unblocks_after_the_readout(phase):  # noqa: ANN001
    """⭐ `FETCH` 는 독출 안이므로 **`READOUT` 을 벗어난 뒤**에 푼다."""
    def script(h):  # noqa: ANN001, ANN202
        h.ctl.on_phase('READOUT', 0.0)
        h.ctl.on_phase(phase, INF)
    h = _run(script)
    assert h.words == ['0', '1'], h.sent
    assert h.ctl.state == ge.ALLOWED


def test_the_same_state_is_not_resent():
    """⛔ 틱마다 보내면 하룻밤에 수만 줄이다."""
    def script(h):  # noqa: ANN001, ANN202
        for _ in range(20):
            h.ctl.on_phase('READOUT', 0.0)
        for _ in range(20):
            h.ctl.on_phase('IDLE', INF)
    h = _run(script)
    assert h.words == ['0', '1'], h.sent


def test_each_frame_of_a_multi_frame_go_toggles():
    """⚠️ `GO n` 은 독출이 n 번이다 -- 프레임마다 여닫는 것이 의도다."""
    def script(h):  # noqa: ANN001, ANN202
        for _ in range(3):
            h.ctl.on_phase('INTEGRATING', 30.0)     # 조용
            h.ctl.on_phase('INTEGRATING', 1.0)      # 막는다
            h.ctl.on_phase('READOUT', 0.0)
            h.ctl.on_phase('WRITING', INF)          # 푼다
    h = _run(script)
    assert h.words == ['0', '1', '0', '1', '0', '1'], h.sent


def test_it_does_nothing_when_disabled():
    """`GUIEXPCTRL = false` 면 ICS 는 안 보낸다 -- 콘솔 경로는 그대로다."""
    async def run():  # noqa: ANN202
        h = Harness(enabled=False)
        h.ctl.on_phase('READOUT', 0.0)
        h.ctl.on_phase('IDLE', INF)
        await h.ctl.close()
        return h
    h = asyncio.run(run())
    assert h.sent == []


# -- 응답 · 종료 ------------------------------------------------------------


def test_a_missing_reply_makes_the_state_unknown(caplog):  # noqa: ANN001
    """⚠️ 조용한 실패는 *"막았다고 믿는"* 상태다."""
    caplog.set_level(logging.WARNING)

    async def run():  # noqa: ANN202
        h = Harness(reply_timeout=0.03)
        h.ctl.on_phase('READOUT', 0.0)
        await asyncio.sleep(0.10)
        await h.ctl.close()
        return h
    h = asyncio.run(run())
    assert h.ctl.state == ge.UNKNOWN
    assert any('답하지 않았다' in r.message for r in caplog.records)


def test_an_error_reply_makes_the_state_unknown(caplog):  # noqa: ANN001
    caplog.set_level(logging.WARNING)

    def script(h):  # noqa: ANN001, ANN202
        h.ctl.on_phase('READOUT', 0.0)
        h.ctl.note_reply('ICG>ICS ERROR: EXPENABLE Exposure lock is not available')
    h = _run(script)
    assert h.ctl.state == ge.UNKNOWN
    assert any('거절됐다' in r.message for r in caplog.records)


def test_closing_does_not_release_the_lock():
    """⚠️ 독출 중에 죽었으면 guide 가 그 구간에 노출한다 -- 풀지 않는다."""
    def script(h):  # noqa: ANN001, ANN202
        h.ctl.on_phase('READOUT', 0.0)
    h = _run(script)
    assert h.words == ['0'], h.sent
    assert h.ctl.state == ge.BLOCKED


def test_the_summary_reads_back_the_state():
    h = _run(lambda h: h.ctl.on_phase('READOUT', 0.0))
    said = h.ctl.summary()
    assert 'state=BLOCKED' in said and 'node=ICG' in said, said

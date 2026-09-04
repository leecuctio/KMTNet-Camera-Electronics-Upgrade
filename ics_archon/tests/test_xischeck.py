#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XIS 허브 확인 -- **못 닿으면 기동을 멈춘다** (운영자 지시 2026-09-04).

⭐ **왜 시험이 필요한가.**  이 검사가 막으려는 실패는 **조용하다** -- 허브가
없으면 `VACGAUGE`·`EXPENABLE`·`HKDATA` 가 전송 계층의 `log.debug` 한 줄로
버려지고 `sendto` 는 성공한다.  즉 *"검사가 동작하지 않는다"* 는 것도 조용히
지나가므로, 그 자리를 시험으로 못박아야 한다.
"""

from __future__ import annotations

import asyncio
import types

import pytest

import ics_archon  # noqa: F401

from ics_archon.xischeck import XIS_ID, XisGate, XisUnreachable  # noqa: E402


def _msg(src: str, raw: str):  # noqa: ANN202
    return types.SimpleNamespace(src=src, raw=raw)


def _gate(**over):  # noqa: ANN003, ANN202
    opts = dict(node_id='ICS', timeout=0.05, tries=2, required=True,
                xis_host='127.0.0.1')
    opts.update(over)
    return XisGate(opts.pop('node_id'), **opts)


def test_a_pong_from_the_hub_lets_the_startup_through():
    """정상 경로 -- `ICS>XIS PING` 에 `XIS>ICS PONG` 이 오면 통과."""
    async def run():  # noqa: ANN202
        gate = _gate()
        sent = []

        def ping():  # noqa: ANN202
            sent.append(XIS_ID)
            gate.note_message(_msg('XIS', 'XIS>ICS PONG'))

        await gate.check(ping)
        return sent, gate.answered_on

    sent, answered = asyncio.run(run())
    assert sent == [XIS_ID] and answered == 1


def test_no_answer_stops_the_startup_after_the_retries():
    """⛔ 답이 없으면 **멈춘다** -- 조용히 지나가지 않는다."""
    async def run():  # noqa: ANN202
        gate = _gate(tries=3)
        tries = []
        with pytest.raises(XisUnreachable, match='PING'):
            await gate.check(lambda: tries.append(1))
        return tries

    assert len(asyncio.run(run())) == 3, 'tries 만큼 다시 묻지 않았다'


def test_a_pong_from_another_node_does_not_count():
    """⛔⛔ **허브가 아닌 노드의 `PONG` 은 안 센다.**

    `commands.cmd_ping` 이 브로드캐스트 `PING` 에 답하므로 다른 노드도 `PONG`
    을 낸다.  그것을 세면 *"허브는 죽었는데 옆 노드가 살아 있어서 통과"* 가
    되고, 이 검사가 막으려던 상태가 그대로 지나간다.
    """
    async def run():  # noqa: ANN202
        gate = _gate(tries=1)

        def ping():  # noqa: ANN202
            gate.note_message(_msg('ICG', 'ICG>ICS PONG'))
            gate.note_message(_msg('TC', 'TC>ICS PONG'))

        with pytest.raises(XisUnreachable):
            await gate.check(ping)

    asyncio.run(run())


def test_an_empty_xis_host_is_refused_with_the_key_name():
    """⛔ 허브 주소가 비어 있으면 **그 키 이름을 대고** 거절한다.

    ⚠️ 종전에는 그 상태로 뜨고 명령이 조용히 사라졌다 -- 그것이 이 검사가
    생긴 이유다 (운영자 확정: ICS·ICG 는 허브를 통해서만 통신한다).
    """
    async def run():  # noqa: ANN202
        gate = _gate(xis_host='')
        with pytest.raises(XisUnreachable, match='xis_host'):
            await gate.check(lambda: None)

    asyncio.run(run())


def test_the_check_is_skippable_for_harnesses():
    """`required=False` 면 **PING 도 안 보낸다** (시험·허브 없는 자리)."""
    async def run():  # noqa: ANN202
        gate = _gate(required=False, xis_host='')
        sent = []
        await gate.check(lambda: sent.append(1))
        return sent

    assert asyncio.run(run()) == []


def test_the_shipped_ini_requires_the_hub():
    """⭐ 배포 설정은 **켜 둔 것이 정본**이다 (운영자 지시 2026-09-04)."""
    import os

    from ics_archon import config as acfg_mod

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert acfg_mod.load(os.path.join(root, 'ics_archon.ini')).require_xis

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Radionode 를 **런타임에 붙였다 뗐다** 한다 -- 운영자 지시 ④ (2026-09-03).

지시 원문: *"Radionode 디바이스 2개 접속상태를 알려주고, connect/disconnect
명령이 필요해. … connect 하면 자동으로 자료를 주기적으로 받아오도록 하고,
주기와 디바이스 정보는 icg_archon.ini에서"*

⭐ 종전에 없던 것은 **폴링을 런타임에 켜는 길**이다 -- `start()` 가 기동에서
`backend` 를 한 번 보고 루프를 안 띄우면 끝이라, ini 기본값 `off` 로 뜬
프로세스는 다시 띄우지 않고는 자료를 받을 수 없었다 (DevNote 11.15-(6)).

지키려는 것 넷:

* ⛔ **자격증명이 모자라면 켜지 않는다** -- 켜 놓고 실패를 반복하면 헤더는
  sentinel 인데 운영자는 "연결했다" 고 믿는다.  무엇이 없는지 **이름을 댄다**.
* ⛔ **`sim` 에서는 못 켠다** -- sim 값은 헤더로 안 나가는 배선 확인용이다.
* ⭐ **끊으면 곧바로 sentinel** -- `off` 의 뜻이 그것이다.  *"끊었는데 10분간
  옛 값이 나가는"* 상태보다 정직하다.
* ⭐ **되켜도 옛 표본이 갓 잰 값으로 둔갑하지 않는다** -- 표본시각이 값과
  함께 나간다.
"""

from __future__ import annotations

import asyncio

import pytest

import ics_archon  # noqa: F401

from icg_archon.config import RadionodeCfg, RadionodeDevice  # noqa: E402
from icg_archon.radionode import (RadionodeClient,  # noqa: E402
                                  RadionodeError)

DEVICES = (RadionodeDevice(alias='hebox', mac='AA', keys=('hebox',)),
           RadionodeDevice(alias='fsa', mac='BB', keys=('fsatemp', 'fsahum')))

CREDS = dict(base_url='https://example.invalid', latest_path='/x/{mac}',
             api_key='k', api_secret='s')


def _client(**over):  # noqa: ANN201
    cfg = RadionodeCfg(devices=DEVICES, poll_period=3600.0, **over)
    rn = RadionodeClient(cfg)
    # ⚠️ **실제 HTTP 를 치지 않는다** -- 폴링 한 바퀴가 바로 도는데 그것이
    # 바깥으로 나가면 시험이 네트워크에 매달린다.
    # ⚠️ 응답 모양은 **실기 API 를 흉내낸다** (`_store` 가 temperature/
    # humidity 를 판다) -- 우리 계약 키 이름을 그대로 주면 시험만 통과하고
    # 실기에서는 "응답에서 온도/습도를 못 찾았다" 가 된다.
    rn._fetch_latest = lambda mac: {'temperature': 21.5,   # noqa: SLF001
                                    'humidity': 44.0}
    return rn


def _spawn_in(loop_tasks):  # noqa: ANN001, ANN202
    def spawn(coro):  # noqa: ANN001, ANN202
        task = asyncio.ensure_future(coro)
        loop_tasks.append(task)
        return task
    return spawn


# -- 켜기 -------------------------------------------------------------------


def test_connect_is_refused_when_the_credentials_are_missing():
    """⛔ **무엇이 없는지 이름을 댄다** -- 조용히 켜면 헤더가 밤새 sentinel 이다."""
    rn = _client()                          # backend=off, 자격증명 없음
    rn.start(lambda coro: None)
    with pytest.raises(RadionodeError) as exc:
        rn.connect()
    for key in ('base_url', 'latest_path', 'api_key', 'api_secret'):
        assert key in str(exc.value), str(exc.value)
    assert rn.cfg.backend == 'off' and not rn.polling


def test_connect_is_refused_on_the_sim_backend():
    """⛔ sim 값은 **헤더로 안 나간다** -- 런타임에 올리면 ini 와 실제가 갈린다."""
    rn = _client(backend='sim', **CREDS)
    rn.start(lambda coro: None)
    with pytest.raises(RadionodeError):
        rn.connect()
    assert rn.cfg.backend == 'sim'


def test_connect_starts_the_polling_loop_at_runtime():
    """⭐ 지시의 *"connect 하면 자동으로 주기적으로 받아온다"* 가 이것이다."""
    async def run():  # noqa: ANN202
        tasks = []
        rn = _client(**CREDS)               # backend=off 인 채로 뜬다
        rn.start(_spawn_in(tasks))
        assert not rn.polling, '기동에서는 안 돈다 (backend=off)'
        note = rn.connect()
        assert rn.cfg.backend == 'openapi' and rn.polling
        # ⚠️ ini 를 안 고쳤다는 사실이 응답에 있어야 한다.
        assert 'runtime only' in note and 'backend=off' in note
        await asyncio.sleep(0.05)           # 첫 바퀴가 돌 틈
        assert rn.values(), '켰는데 값이 안 들어온다'
        await rn.stop()
    asyncio.run(run())


def test_connecting_twice_is_harmless():
    """두 번 쳐도 루프가 둘이 되면 안 된다 (API 쿼터가 분 단위다)."""
    async def run():  # noqa: ANN202
        tasks = []
        rn = _client(**CREDS)
        rn.start(_spawn_in(tasks))
        rn.connect()
        first = rn._task                    # noqa: SLF001
        assert rn.connect() == 'Already polling'
        assert rn._task is first            # noqa: SLF001
        await rn.stop()
    asyncio.run(run())


# -- 끄기 -------------------------------------------------------------------


def test_disconnect_stops_the_loop_and_the_values_go_to_sentinel():
    """⭐ **끊으면 곧바로 결측**이다 -- `off` 의 뜻이 그것이다.

    ⚠️ 표본을 지우는 것이 아니라 `values()` 가 백엔드로 먼저 거른다 -- 그래서
    되켜면 옛 표본이 곧바로 다시 보인다 (아래 시험).
    """
    async def run():  # noqa: ANN202
        tasks = []
        rn = _client(**CREDS)
        rn.start(_spawn_in(tasks))
        rn.connect()
        await asyncio.sleep(0.05)
        assert rn.values()
        note = await rn.disconnect()
        assert not rn.polling and rn.cfg.backend == 'off'
        assert rn.values() == {}, '끊었는데 헤더로 값이 나간다'
        assert 'sentinel' in note
        return rn
    asyncio.run(run())


def test_a_stale_sample_does_not_become_fresh_when_we_reconnect():
    """⭐ 되켜도 **표본시각은 그대로** -- 갓 잰 값으로 둔갑하지 않는다.

    `values_with_time()` 이 값과 시각을 함께 내므로 하류(`HKSTALE`·헤더 나이)
    가 낡은 것을 낡은 것으로 판정한다.
    """
    async def run():  # noqa: ANN202
        import time
        tasks = []
        rn = _client(**CREDS)
        rn.start(_spawn_in(tasks))
        rn.connect()
        await asyncio.sleep(0.05)
        when = rn.values_with_time()['hebox'][1]
        await rn.disconnect()
        # 폴링 없이 되켠다 -- 새 표본이 들어오기 전에 읽는다.
        rn.cfg.backend = 'openapi'
        again = rn.values_with_time()['hebox'][1]
        assert abs(again - when) < 0.5, (when, again)
        assert again <= time.time()
    asyncio.run(run())


# -- 상태 -------------------------------------------------------------------


def test_status_says_why_it_cannot_connect():
    """⭐ 종전에는 `off` 이면 `Backend=off` 한 마디로 끝났다.

    운영자가 묻는 것은 *"왜 자료가 안 들어오나"* 인데 그 답이 안 보였다.
    """
    rn = _client()
    text = rn.status_text()
    assert 'Backend=off' in text and 'Polling=no' in text
    assert 'missing' in text
    for key in ('base_url', 'api_secret'):
        assert key in text, text


def test_status_marks_a_cached_sample_as_not_published():
    """⚠️ `STATUS` 에 값이 보이는데 헤더는 sentinel 인 상태를 설명한다."""
    async def run():  # noqa: ANN202
        tasks = []
        rn = _client(**CREDS)
        rn.start(_spawn_in(tasks))
        rn.connect()
        await asyncio.sleep(0.05)
        await rn.disconnect()
        return rn.status_text()
    text = asyncio.run(run())
    assert 'not published' in text, text
    assert 'Polling=no' in text


def test_status_separates_the_backend_from_the_loop():
    """⚠️ `backend=openapi` 인데 루프가 죽어 있을 수 있다 -- 둘을 따로 보인다."""
    rn = _client(backend='openapi', **CREDS)
    assert 'Backend=openapi' in rn.status_text()
    assert 'Polling=no' in rn.status_text(), '루프는 아직 안 떴다'

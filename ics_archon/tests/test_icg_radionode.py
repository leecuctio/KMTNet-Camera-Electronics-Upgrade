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
import base64
import json

import pytest

import ics_archon  # noqa: F401

from icg_archon.config import (RadionodeCfg,  # noqa: E402
                                RadionodeDevice)
from icg_archon.radionode import (RadionodeClient,  # noqa: E402
                                  RadionodeError)

DEVICES = (RadionodeDevice(alias='hebox', mac='AA', keys=('hebox',)),
           RadionodeDevice(alias='fsa', mac='BB', keys=('fsatemp', 'fsahum')))

CREDS = dict(base_url='https://example.invalid', latest_path='/x/{mac}',
             api_key='k', api_secret='s')


#: ⭐ `local_lns` 갈래는 DevEUI 로 붙는다 (게이트웨이 GWEUI 와 같은 계열의
#: 값을 시험에도 쓴다 -- 실물 모양을 흉내내야 정규화가 실제로 걸린다).
DEVICES_EUI = (
    RadionodeDevice(alias='hebox', mac='AA', keys=('hebox',),
                    deveui='AC-1F-09-FF-FE-1F-50-01'),      # 구분자 섞인 모양
    RadionodeDevice(alias='fsa', mac='BB', keys=('fsatemp', 'fsahum'),
                    deveui='ac1f09fffe1f5002'))


def _client(**over):  # noqa: ANN201
    over.setdefault('devices', DEVICES)
    cfg = RadionodeCfg(poll_period=3600.0, **over)
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


# -- ⏳ local_lns -- 자리만 있다 (2026-09-04) --------------------------------
#
# ⛔ **인터넷이 끊기면 세 카드가 결측이고, 운영자는 그것을 받아들이지 않는다**
# (2026-09-04 확정).  그런데 자료가 들어오는 길이 클라우드 하나뿐이라 코드로는
# 못 막는다 -- 실제로 막는 길은 게이트웨이를 안쪽 LNS 로 돌리는 것이고, 그것은
# 운영자 액션 둘(게이트웨이 관리 접근 · 장치 가입 키)이 선행이다.
# ⭐ 그래서 **자리만 정식으로** 열어 둔다: ini 에 그 뜻을 적을 수 있고, 기동이
# 무엇이 모자란지 크게 알린다.


def test_the_local_lns_config_warns_about_what_would_silently_drop():
    """⭐ 막는 것은 **조용히 아무것도 안 받는 상태**다.

    주소가 없으면 임의 포트에 떠서 게이트웨이가 못 찾고, DevEUI 가 없으면
    uplink 가 와도 어느 장치인지 못 붙여 전부 버려진다 -- ⛔ 둘 다 로그만
    보면 *"잘 떠 있는"* 것처럼 보인다.  ⚠️ 기동은 **안 세운다**: 나머지
    HK(RTD·진공·AUX)는 돌아야 한다.
    """
    from icg_archon.config import IcgCfg, validate

    cfg = IcgCfg()
    cfg.radionode = RadionodeCfg(backend='local_lns', devices=DEVICES)
    warn = validate(cfg, 'sim')
    said = '\n'.join(warn)
    assert 'lns_bind' in said, said
    assert 'deveui' in said and 'hebox' in said and 'fsa' in said, said


def test_an_unknown_backend_still_refuses_to_start():
    """⛔ 자리를 하나 열었다고 아무 낱말이나 받으면 안 된다."""
    from icg_archon.config import IcgCfg, IcgConfigError, validate

    cfg = IcgCfg()
    cfg.radionode = RadionodeCfg(backend='cloudy', devices=DEVICES)
    with pytest.raises(IcgConfigError):
        validate(cfg, 'sim')


def test_connect_does_not_quietly_fall_back_to_the_cloud():
    """⛔ `local_lns` 에서 `CONNECT` 가 openapi 로 올리면 **안 된다.**

    *"이 사이트는 클라우드를 안 쓴다"* 고 적어 둔 ini 인데 명령 하나로 조용히
    바깥을 치게 되는 자리다.  ⚠️ 자격증명이 다 있어도(`CREDS`) 그렇다.
    """
    rn = _client(backend='local_lns', **CREDS)   # ⚠️ DevEUI 는 없다
    rn.start(lambda coro: None)
    with pytest.raises(RadionodeError) as exc:
        rn.connect()
    assert 'deveui' in str(exc.value).lower(), str(exc.value)
    assert rn.cfg.backend == 'local_lns', '백엔드가 조용히 바뀌었다'
    assert not rn.polling, '클라우드 폴러가 떴다'


def test_a_listener_is_not_started_when_no_device_has_a_deveui():
    """⛔ 떠 있는데 **전부 버려지는** 상태를 만들지 않는다.

    소켓만 열려 있으면 `STATUS` 는 멀쩡해 보이는데 값은 영영 안 들어온다.
    """
    rn = _client(backend='local_lns', lns_bind='127.0.0.1:0')
    rn.start(lambda coro: None)             # ⚠️ 기동은 안 세운다
    assert not rn.listening
    assert not rn.publishing


# -- 실제 수신 (localhost 소켓) ---------------------------------------------


def _post(addr: str, path: str, payload, token: str = ''):  # noqa: ANN001, ANN202
    """수신기에 uplink 하나를 넣는다 -- **진짜 HTTP** 다 (localhost)."""
    import urllib.request

    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request('http://%s%s' % (addr, path), data=body,
                                 headers={'Content-Type': 'application/json'})
    if token:
        req.add_header('X-Auth-Token', token)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _listening(**over):  # noqa: ANN201
    """DevEUI 를 붙인 장치 둘 + 127.0.0.1 임의 포트로 뜬 수신기."""
    over.setdefault('lns_bind', '127.0.0.1:0')
    rn = _client(backend='local_lns', devices=DEVICES_EUI, **over)
    rn.start(lambda coro: None)
    assert rn.listening, '수신기가 안 떴다'
    return rn


def test_an_uplink_becomes_a_sample():
    """⭐ 게이트웨이 NS 가 밀어 준 uplink 하나가 그대로 HK 값이 된다."""
    rn = _listening()
    try:
        code = _post(rn._listener.address, '/uplink',        # noqa: SLF001
                     {'deviceInfo': {'devEui': 'AC1F09FFFE1F5001'},
                      'object': {'temperature': 21.5, 'humidity': 44.0}})
        assert code == 200
        vals = rn.values()
        assert vals.get('hebox') == 21.5, vals
    finally:
        rn._listener.stop()                                 # noqa: SLF001


def test_the_deveui_matches_even_when_the_shapes_differ():
    """⚠️ 같은 DevEUI 가 **세 모양**으로 온다 -- 구분자·대소문자·base64.

    ⛔ 모양이 다르면 대응이 조용히 빗나가 *"uplink 는 오는데 아무 장치에도 안
    붙는"* 상태가 된다.
    """
    rn = _listening()
    try:
        b64 = base64.b64encode(bytes.fromhex('ac1f09fffe1f5002')).decode()
        code = _post(rn._listener.address, '/uplink',        # noqa: SLF001
                     {'devEUI': b64,
                      'object': {'temperature': 19.0, 'humidity': 51.0}})
        assert code == 200
        vals = rn.values()
        assert vals.get('fsatemp') == 19.0 and vals.get('fsahum') == 51.0, vals
    finally:
        rn._listener.stop()                                 # noqa: SLF001


def test_an_unknown_deveui_is_dropped_but_counted():
    """⛔ 버리되 **센다** -- 센서를 더 달고 ini 에 안 적은 것이 가장 흔하다."""
    rn = _listening()
    try:
        _post(rn._listener.address, '/uplink',               # noqa: SLF001
              {'deviceInfo': {'devEui': 'AC1F09FFFE1F9999'},
               'object': {'temperature': 1.0}})
        assert rn.values() == {}
        assert 'UnknownEUI=' in rn.status_text(), rn.status_text()
        assert 'ac1f09fffe1f9999' in rn.status_text().lower()
    finally:
        rn._listener.stop()                                 # noqa: SLF001


def test_an_uplink_without_a_decoded_object_is_missing_with_a_reason():
    """⛔ 코덱이 없으면 base64 원문만 온다 -- **짐작으로 자르지 않는다.**

    결측으로 두되 `STATUS` 가 이유를 말해야 게이지 고장과 구별된다.
    """
    rn = _listening()
    try:
        _post(rn._listener.address, '/uplink',               # noqa: SLF001
              {'deviceInfo': {'devEui': 'AC1F09FFFE1F5001'},
               'data': 'AQIDBA=='})
        assert rn.values() == {}
        assert 'codec' in rn.status_text(), rn.status_text()
    finally:
        rn._listener.stop()                                 # noqa: SLF001


def test_the_token_and_path_are_checked():
    """⚠️ LAN 안이라도 **누가 보냈는지**는 가른다 -- 틀린 값이 헤더로 가는 길이다."""
    rn = _listening(lns_token='s3cret')
    try:
        addr = rn._listener.address                          # noqa: SLF001
        good = {'deviceInfo': {'devEui': 'AC1F09FFFE1F5001'},
                'object': {'temperature': 5.0}}
        assert _post(addr, '/uplink', good) == 401           # 토큰 없음
        assert _post(addr, '/nope', good, 's3cret') == 404   # 경로 다름
        assert rn.values() == {}
        assert _post(addr, '/uplink', good, 's3cret') == 200
        assert rn.values().get('hebox') == 5.0
    finally:
        rn._listener.stop()                                 # noqa: SLF001


def test_disconnecting_the_listener_sends_the_values_to_sentinel():
    """⭐ 끄면 곧바로 결측이고, **백엔드는 local_lns 그대로**다.

    ⛔ `off` 로 되돌리면 다음 `CONNECT` 가 **클라우드로 간다** -- 인터넷을 안
    쓰기로 한 사이트에서 그것은 사고다.
    """
    async def run():  # noqa: ANN202
        rn = _listening()
        _post(rn._listener.address, '/uplink',               # noqa: SLF001
              {'deviceInfo': {'devEui': 'AC1F09FFFE1F5001'},
               'object': {'temperature': 7.5}})
        assert rn.values().get('hebox') == 7.5
        note = await rn.disconnect()
        assert not rn.listening and rn.values() == {}
        assert rn.cfg.backend == 'local_lns', '백엔드가 off 로 돌아갔다'
        assert 'sentinel' in note
        # 되켜면 옛 표본이 다시 보인다 (표본시각은 그대로다).
        rn.connect()
        assert rn.values().get('hebox') == 7.5
        rn._listener.stop()                                 # noqa: SLF001
    asyncio.run(run())

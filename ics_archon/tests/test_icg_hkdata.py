#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`HKDATA` 응답 본문 -- DevNote 11.14-(1) 운영자 확정 문면의 시험판.

지키려는 것:

* ⭐ **`HKQDATE` 23자 · `HKUDATE` 19자** -- 길이가 다른 것이 의도다 (뒤바뀌면 보인다)
* **`HKSTALE` = 낡아서 뺀 계약 키 수**, `실린 계약키 + HKSTALE = 10`
* ⛔ **따옴표를 안 붙인다** · 공백이 든 값은 **거부**한다
* ⭐ 불린은 **낱말** (`ON`/`OFF`), 매핑은 ICG 한 곳에서만
* ⛔ **못 읽으면 아예 안 싣는다** -- 모르는 것을 `OFF` 로 적으면 거짓말이다
* ⭐ **`HK` 와 `HKDATA` 가 같은 본문**을 낸다 (운영자 지시 2026-09-06)
"""

from __future__ import annotations

import asyncio
import time

import ics_archon  # noqa: F401

from icg_archon import hkdata  # noqa: E402


class _Hk:
    """`hk.sensors()` 만 흉내낸다 -- 조립기가 보는 것이 그것뿐이다."""

    def __init__(self, vals) -> None:  # noqa: ANN001
        self._vals = vals
        self.ctrl = None
        self.gauge = None

    def sensors(self) -> dict:
        return dict(self._vals)


class _App:
    def __init__(self, vals) -> None:  # noqa: ANN001
        self.hk = _Hk(vals)
        self.gauge = None


FULL = {
    'hkudate': '2026-09-04T09:10:33',
    'dewpres': '6.93e-04', 'ccdtemp': -100.64, 'dmptemp': -122.34,
    'pt30n1': -153.45, 'pt30n2': -154.56, 'charcoal': -205.67,
    'wallbrd': 16.78, 'hebox': 37.89, 'fsatemp': 16.7, 'fsahum': 17.8,
}


def _body(vals) -> str:  # noqa: ANN001
    return asyncio.run(hkdata.body(_App(vals)))


def _kv(body: str) -> dict:
    return dict(p.split('=', 1) for p in body.split() if '=' in p)


def test_the_two_timestamps_have_different_lengths():
    """⭐ **23자 대 19자** -- 뒤바뀌면 눈에 보이라고 그렇게 정했다."""
    kv = _kv(_body(FULL))
    assert len(kv['HKQDATE']) == 23, kv['HKQDATE']
    assert len(kv['HKUDATE']) == 19, kv['HKUDATE']


def test_every_contract_key_present_means_no_stale():
    """`실린 계약키 + HKSTALE = 10` -- 완전성 검사가 이 셈에 걸려 있다."""
    kv = _kv(_body(FULL))
    carried = [k for k in ('DEWPRES', 'CCDTEMP', 'DMPTEMP', 'PT30N1', 'PT30N2',
                           'CHARCOAL', 'WALLBRD', 'HEBOX', 'FSATEMP', 'FSAHUM')
               if k in kv]
    assert len(carried) == 10
    assert kv['HKSTALE'] == '0'


def test_stale_keys_are_omitted_and_counted():
    """⛔ **낡은 키는 싣지 않는다** -- sentinel 로 채우면 셈이 깨진다."""
    vals = dict(FULL)
    for k in ('charcoal', 'pt30n2', 'hebox'):
        del vals[k]
    kv = _kv(_body(vals))
    assert 'CHARCOAL' not in kv and 'PT30N2' not in kv and 'HEBOX' not in kv
    assert kv['HKSTALE'] == '3'


def test_temperatures_carry_a_sign_and_humidity_does_not():
    """규격 5.0절 부호 규약이 **와이어에도** 걸린다 (DevNote 11.14)."""
    kv = _kv(_body(FULL))
    assert kv['WALLBRD'] == '+16.78'
    assert kv['CCDTEMP'] == '-100.64'
    # ⭐ **2자리** (운영자 확정 2026-09-09) -- Radionode 원문이 `"22.35"` 로
    # 2자리를 준다.  종전 1자리는 `ENS1` 선례를 유추한 것이었는데, `ENS` 는
    # 규격 5.8절이 *"중계 그대로"* 라 TCSSTATUS 의 자릿수일 뿐이었다.
    assert kv['FSATEMP'] == '+16.70'         # 소수 2자리 + 부호
    assert kv['FSAHUM'] == '17.80'           # ⛔ 습도는 부호 대상이 아니다


def test_nothing_is_quoted():
    """⛔ 따옴표를 전부 뺐다 (11.14-(1-c)) -- 같은 프로그램의 `HK` 와 맞춘 것."""
    body = _body(FULL)
    assert "'" not in body and '"' not in body


def test_a_value_with_a_space_is_refused():
    """⛔ 공백이 든 값은 **뺀다** -- 따옴표가 없으므로 파서가 조용히 자른다.

    `DEWPRES=6.93 e-04` 가 `'6.93'` 이 되면 sentinel 이 아니라 **그럴듯한 틀린
    값**으로 카드에 실린다.
    """
    vals = dict(FULL)
    vals['dewpres'] = '6.93 e-04'
    kv = _kv(_body(vals))
    assert 'DEWPRES' not in kv


def test_unreadable_heater_fields_are_omitted_not_guessed():
    """⛔ **모르는 것을 `OFF` 로 적지 않는다** -- 그러면 "껐다" 고 거짓말한다.

    컨트롤러가 없으면 `HTREN`·`HTRSET`·`HTRFORCE` 가 통째로 빠지고, ICS 가 그
    카드를 규격 5.0절 sentinel 로 채운다.
    """
    kv = _kv(_body(FULL))
    for k in ('HTREN', 'HTRSET', 'HTRFORCE'):
        assert k not in kv, k


def test_the_gauge_word_is_carried_when_known():
    """⭐ 불린은 낱말이다 -- `VACGAUGE` 는 `ON`/`OFF`/`UNKNOWN`."""
    app = _App(FULL)

    class _G:
        word = 'ON'
    app.gauge = _G()
    kv = _kv(asyncio.run(hkdata.body(app)))
    assert kv['VACGAUGE'] == 'ON'
    # ⭐ 운영자 지시 -- 압력은 상태 낱말 **바로 뒤**다.
    body = asyncio.run(hkdata.body(app))
    assert body.index('VACGAUGE=') < body.index('DEWPRES=')


def test_htrout_is_unsigned_with_three_decimals():
    """`HTROUT` 은 전압이라 부호가 없고 소수 3자리다 (규격 5.6.2절)."""
    vals = dict(FULL)
    vals['htrout'] = 3.5123
    kv = _kv(_body(vals))
    assert kv['HTROUT'] == '3.512'


# -- 폴링값 대 즉시 되읽기 (운영자 확정 2026-09-09) -------------------------
#
# ⭐ **`NOW` 는 조립기가 컨트롤러를 직접 치지 않는다** -- `hk.refresh_now()` 로
# **한 바퀴를 돌리고** 그 결과(`sensors()`)를 읽는다.  ⛔ 여기서 또 읽으면
# 왕복이 두 배가 되고, 두 값이 갈리면 어느 쪽이 정본인지 다투게 된다
# (11.52 가 그 부류였다).  그래서 대역도 *"한 바퀴를 돌면 값이 바뀐다"* 로 만든다.


class _HkNow(_Hk):
    """`refresh_now()` 가 표본을 갈아 끼우는 HK 대역 -- 호출 횟수를 센다."""

    def __init__(self, vals, after=None, fail=False) -> None:  # noqa: ANN001
        super().__init__(vals)
        self._after = after
        self._fail = fail
        self.refreshed = 0

    async def refresh_now(self) -> None:  # noqa: ANN202
        self.refreshed += 1
        if self._fail:
            raise RuntimeError('링크가 죽었다')
        if self._after is not None:
            self._vals.update(self._after)


def _body_now(vals, after=None, fail=False):  # noqa: ANN001, ANN202
    """(본문, 갱신횟수) -- `after` 는 한 바퀴 뒤에 바뀔 값."""
    app = _App({})
    app.hk = _HkNow(dict(vals), after, fail)
    body = asyncio.run(hkdata.body(app, now=True))
    return body, app.hk.refreshed


POLLED = {'htren': '1', 'htrset': -95.25, 'htrforce': '0'}
AFTER = {'htren': '0', 'htrset': -80.50, 'htrforce': '1',
         'ccdtemp': -101.11}


def test_hkdata_without_now_uses_the_polled_values_and_does_not_refresh():
    """⭐ **인자가 없으면 폴링값** -- 한 바퀴를 돌리지 **않는다**.

    ⭐ 요점은 속도가 아니라 **원천이 하나**가 되는 것이다: FITS 헤더도 같은
    `_sample` 을 보므로, 같은 순간에 헤더와 `HKDATA` 가 다른 값을 낼 수 없다
    (11.52 가 만들었던 갈림이 여기서 닫힌다).
    ⚠️ 낡음은 `HKUDATE`·`HKSTALE` 이 그대로 알린다 -- 숨기지 않는다.
    """
    vals = dict(FULL)
    vals.update(POLLED)
    app = _App({})
    app.hk = _HkNow(vals, AFTER)
    got = _kv(asyncio.run(hkdata.body(app)))
    assert app.hk.refreshed == 0, '폴링 갈래가 한 바퀴를 돌렸다'
    assert got['HTREN'] == 'ON' and got['HTRFORCE'] == 'OFF', got
    assert got['HTRSET'] == '-95.25', got


def test_hkdata_now_turns_one_full_cycle_and_uses_its_result():
    """⭐ `HKDATA NOW` 는 **한 바퀴를 돌려** 그 값을 싣는다.

    운영자 지시 2026-09-09: *"`hkdata now` 면 RTD, 진공, Radionode, 히터설정
    모두 되읽기해서 값을 넣어주고, **폴링 값들도 갱신**하도록."*
    ⭐ 그래서 히터 셋만이 아니라 **RTD 도 갱신되는지** 함께 본다 -- 히터만
    보면 *"한 바퀴"* 가 아니라 *"셋만 읽기"* 로 되돌아가도 안 잡힌다.
    ⚠️ 폴링값과 **다른 값**을 먹여야 어느 쪽이 실렸는지 갈린다.
    """
    vals = dict(FULL)
    vals.update(POLLED)
    body, turns = _body_now(vals, AFTER)
    got = _kv(body)
    assert turns == 1, turns
    assert got['HTREN'] == 'OFF' and got['HTRFORCE'] == 'ON', got
    assert got['HTRSET'] == '-80.50', got
    assert got['CCDTEMP'] == '-101.11', got      # ⭐ RTD 도 갱신됐다


def test_now_still_answers_when_the_refresh_fails():
    """⚠️ 갱신이 실패해도 **폴링값으로 답한다** -- 무응답보다 낫다.

    ⛔ 여기서 예외를 올리면 링크가 잠깐 흔들린 것만으로 `HKDATA` 가 통째로
    `ERROR` 가 된다 -- 나머지 열몇 카드는 멀쩡한데도.
    """
    vals = dict(FULL)
    vals.update(POLLED)
    body, turns = _body_now(vals, AFTER, fail=True)
    got = _kv(body)
    assert turns == 1
    assert got['HTREN'] == 'ON' and got['HTRSET'] == '-95.25', got


def test_the_heater_three_are_omitted_when_the_poll_has_nothing():
    """⛔ 폴링값도 없으면 **아예 안 싣는다** -- ICS 가 sentinel 로 채운다.

    ⚠️ HK 가 아직 한 바퀴도 안 돌았거나 ACF 파싱 전이면 이 자리다.
    """
    got = _kv(_body(dict(FULL)))
    for k in ('HTREN', 'HTRSET', 'HTRFORCE'):
        assert k not in got, (k, got)

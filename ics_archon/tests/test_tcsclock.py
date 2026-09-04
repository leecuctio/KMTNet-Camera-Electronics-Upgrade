#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TCS 시각 비교 -- `TCSQDATE` 로 TC 시계와 우리 시계를 견준다 (운영자 2026-09-04).

⛔ **왜 재나.**  `DATE-OBS` 는 우리 시계, `TCSQDATE`·포인팅은 TC 시계다.  두
시계가 어긋나면 한 헤더 안에서 **시각과 위치가 다른 순간**을 가리키는데 파일만
봐서는 안 보인다 -- 카드 값은 둘 다 그럴싸하다.

지키려는 것 넷:

* ⭐ **왕복의 가운데**를 TC 의 그 순간에 대응시킨다 (한쪽 방향 차가 아니다).
* ⚠️ **불확실도보다 작은 오프셋은 어긋남이 아니다** -- 문턱은
  `max(설정값, 왕복/2)` 다.  안 그러면 TC 가 느린 밤에 경고가 쏟아진다.
* ⭐ **넘을 때 한 번 · 돌아올 때 한 번**만 말한다 (경고를 무시하도록
  학습시키지 않는다).
* ⛔ **폴백(canned) 응답은 견주지 않는다** -- 그 `TCSQDATE` 는 우리가 찍은
  값이라 언제나 0 이 나와 *"맞았다"* 로 읽힌다.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import logging

import pytest

import ics_archon  # noqa: F401

from ics_archon.tcsclock import (ClockWatch, field_value,  # noqa: E402
                                 parse_stamp, watch_tc_queries)

#: `2026-08-21T12:34:56.266` 의 epoch.  ⭐ **손으로 적지 않는다** -- 처음에
#: 한 해를 틀리게 적어 시험 여섯이 빨개졌다.  `datetime` 으로 짓되 **UTC 로
#: 명시**하는 것이 이 상수의 요점이다 (파싱이 지역시로 읽으면 여기서 갈린다).
BASE = _dt.datetime(2026, 8, 21, 12, 34, 56, 266000,
                    tzinfo=_dt.timezone.utc).timestamp()


# -- 시각 문자열 ------------------------------------------------------------


def test_the_stamp_is_read_as_utc():
    """⚠️ `Z` 가 없다 -- `TIMESYS` 카드가 시간계를 선언한다.  UTC 로 읽는다."""
    assert parse_stamp('2026-08-21T12:34:56.266') == pytest.approx(BASE, abs=1e-3)
    # 따옴표째 온 카드 값도 받는다.
    assert parse_stamp("'2026-08-21T12:34:56.266'") == pytest.approx(BASE, abs=1e-3)


def test_a_second_resolution_stamp_is_also_accepted():
    """밀리초를 뺀 판이 와도 견줄 수 있어야 한다."""
    assert parse_stamp('2026-08-21T12:34:56') == pytest.approx(BASE - 0.266,
                                                               abs=1e-3)


@pytest.mark.parametrize('bad', ['', '   ', 'NC', '2026-08-21 12:34:56',
                                 '2026-08-21T12:34:56.266Z'])
def test_an_unreadable_stamp_is_none_not_zero(bad):  # noqa: ANN001
    """⚠️ 못 읽는 것과 어긋난 것은 다르다 -- 0 을 돌려주면 "맞았다" 가 된다."""
    assert parse_stamp(bad) is None


# -- 오프셋 산수 ------------------------------------------------------------


def test_the_offset_is_measured_against_the_middle_of_the_round_trip():
    """⭐ 한쪽 방향 차가 아니라 **왕복의 가운데**다."""
    watch = ClockWatch('TCS', warn_after=1.0)
    # 우리가 t0 에 보내고 t1 에 받았고, TC 는 그 한가운데를 찍었다 -> 0.
    off = watch.observe('2026-08-21T12:34:56.266', BASE - 0.2, BASE + 0.2)
    assert off == pytest.approx(0.0, abs=1e-3)
    assert watch.uncertainty == pytest.approx(0.2, abs=1e-3)


def test_our_clock_running_ahead_reads_positive():
    """⭐ **양수 = 우리가 앞선다** (운영자 확정 2026-09-04 -- 부호를 뒤집었다).

    ⚠️ 종전 규약은 반대였다(`TCSQDATE - 가운데`, 양수 = TC 가 앞선다).
    기준을 **우리**로 두는 것이 이 기능의 목적(*"ICS 또는 TCS 의 OS 시각이
    잘못된 경우를 발견"*)과 읽는 방향이 같다.
    """
    watch = ClockWatch('TCS', warn_after=1.0)
    # 우리 시계가 TC 가 찍은 순간보다 5초 뒤를 가리킨다 = 우리가 앞선다.
    off = watch.observe('2026-08-21T12:34:56.266', BASE + 5.0, BASE + 5.0)
    assert off == pytest.approx(5.0, abs=1e-3)


def test_a_fast_tc_clock_reads_negative():
    """짝 -- TC 가 앞서면 음수다."""
    watch = ClockWatch('TCS', warn_after=1.0)
    off = watch.observe('2026-08-21T12:34:56.266', BASE - 5.0, BASE - 5.0)
    assert off == pytest.approx(-5.0, abs=1e-3)


def test_a_slow_round_trip_does_not_move_the_threshold():
    """⛔ **왕복이 느려도 문턱은 안 움직인다** (운영자 확정 2026-09-04).

    종전에는 `max(warn_after, 불확실도)` 라 느린 왕복이 문턱을 밀어 올렸다.
    ⛔ 그런데 **그 가지는 한 번도 안 뽑혔다**: 성공한 질의의 왕복은
    `[timing] tc_query_timeout`(0.5 초)을 못 넘고, 더 느리면
    `telemetry.query()` 가 `False` 를 돌려 `watch_tc_queries` 가 표본을 통째로
    버린다.  ⭐ **없는 안전장치를 있는 것처럼 두면** 읽는 사람이 "느린 왕복은
    이미 다뤄진다" 고 믿으므로 걷어냈다.

    ⭐ 불확실도는 **버리지 않는다** -- 경고 문구에 함께 찍혀 사람이 보고
    판단한다.  그래서 값은 계속 재고, 문턱에만 안 섞는다.
    """
    watch = ClockWatch('TCS', warn_after=1.0)
    # 왕복 10초 -> 불확실도 5초.  ⭐ 그래도 문턱은 1.0 그대로다.
    off = watch.observe('2026-08-21T12:34:56.266', BASE - 8.0, BASE + 2.0)
    assert watch.uncertainty == pytest.approx(5.0, abs=1e-3), '불확실도를 안 쟀다'
    assert watch.threshold == pytest.approx(1.0, abs=1e-3), '문턱이 움직였다'
    # 가운데는 BASE-3.0 이고 TC 는 BASE 를 찍었으니 우리가 3초 뒤진다.
    assert off == pytest.approx(-3.0, abs=1e-3)
    assert watch.breaches == 1, '문턱을 넘었는데 안 셌다'


def test_in_the_reachable_range_the_threshold_is_just_the_setting():
    """⭐ **실제로 도달 가능한 왕복에서는 문턱이 설정값 그대로다** (2026-09-04).

    `tc_query_timeout = 0.5` 이므로 성공한 표본의 왕복은 0~0.5 초, 곧
    불확실도는 0~0.25 초다.  기본 문턱 0.5 초는 그보다 언제나 크므로
    `max()` 는 설정값을 고른다 -- **거동을 정하는 것은 이 값 하나**다.
    """
    watch = ClockWatch('TCS', warn_after=0.5)
    # 왕복 0.4초 (시한 0.5초 안) -> 불확실도 0.2초.
    watch.observe('2026-08-21T12:34:56.266', BASE - 0.2, BASE + 0.2)
    assert watch.uncertainty == pytest.approx(0.2, abs=1e-3)
    assert watch.threshold == pytest.approx(0.5, abs=1e-3), (
        '도달 가능한 왕복에서 불확실도가 문턱을 밀어 올렸다')


def test_the_default_threshold_is_half_a_second():
    """운영자 확정 기본값 (2026-09-04) -- OS 시계 어긋남은 초~분 단위다."""
    from ics_archon import config as acfg_mod

    assert acfg_mod.ArchonCfg().tcs_clock_warn == pytest.approx(0.5)


def test_a_backward_clock_step_skips_the_sample():
    """우리 시계가 왕복 중에 뒤로 밟히면 그 표본은 못 쓴다."""
    watch = ClockWatch('TCS')
    assert watch.observe('2026-08-21T12:34:56.266', BASE + 1.0, BASE) is None
    assert watch.samples == 0


# -- 로그 -------------------------------------------------------------------


def test_it_warns_once_and_says_recovery(caplog):  # noqa: ANN001
    """⭐ 넘을 때 한 번 · 돌아올 때 한 번."""
    caplog.set_level(logging.INFO)
    watch = ClockWatch('TCS', warn_after=1.0)
    for _ in range(5):                          # 계속 어긋나 있다
        watch.observe('2026-08-21T12:34:56.266', BASE - 30.0, BASE - 30.0)
    warned = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warned) == 1, [r.message for r in warned]
    assert watch.breaches == 5, '넘은 횟수는 세어 둔다'
    caplog.clear()
    watch.observe('2026-08-21T12:34:56.266', BASE, BASE)   # 돌아왔다
    assert any('돌아왔다' in r.message for r in caplog.records), caplog.records


def test_the_summary_says_it_has_no_sample_before_the_first_query():
    watch = ClockWatch('TCS')
    assert 'no sample' in watch.summary()


# -- relay 감싸기 -----------------------------------------------------------


class _Relay:
    """`TelemetryRelay` 의 최소 대역 -- 감싸기만 본다."""

    def __init__(self, ok: bool = True, stamp: str = '') -> None:
        self.ok = ok
        self.tcs_fields = [('TCSQDATE', stamp), ('TIMESYS', 'UTC')]
        self.aux_fields = []
        self.calls = []

    async def query(self, what: str) -> bool:
        self.calls.append(what)
        return self.ok


def test_wrapping_keeps_the_original_behaviour():
    """⚠️ 감싼 뒤에도 `query()` 의 반환·부작용이 그대로여야 한다."""
    relay = _Relay(stamp='2026-08-21T12:34:56.266')
    watch = ClockWatch('TCS')
    watch_tc_queries(relay, watch)
    assert asyncio.run(relay.query('TCSSTATUS')) is True
    assert relay.calls == ['TCSSTATUS']
    assert watch.samples == 1


def test_a_failed_query_is_not_measured():
    """⛔ 폴백이 채운 `TCSQDATE` 는 **우리가 찍은 값**이다 -- 견주면 0 이 나온다."""
    relay = _Relay(ok=False, stamp='2026-08-21T12:34:56.266')
    watch = ClockWatch('TCS')
    watch_tc_queries(relay, watch)
    assert asyncio.run(relay.query('TCSSTATUS')) is False
    assert watch.samples == 0, '시한 초과 응답을 시계 비교에 썼다'


def test_only_the_tcs_query_is_measured():
    """AUX 질의는 TC 의 다른 스탬프다 -- 같은 감시로 세지 않는다."""
    relay = _Relay(stamp='2026-08-21T12:34:56.266')
    watch = ClockWatch('TCS')
    watch_tc_queries(relay, watch)
    asyncio.run(relay.query('AUXSTATUS'))
    assert watch.samples == 0


def test_field_value_takes_the_first_occurrence():
    """⚠️ `dict()` 로 접으면 뒤엣것이 이긴다 -- 응답의 그 필드는 **먼저 온 것**."""
    fields = [('TCSQDATE', 'first'), ('TCSQDATE', 'second')]
    assert field_value(fields, 'TCSQDATE') == 'first'
    assert field_value(fields, 'NOPE') == ''
    assert field_value(None, 'TCSQDATE') == ''


# -- ini 왕복 (감사가 짚은 공백, 2026-09-04) --------------------------------


def test_the_ini_value_reaches_the_config_and_zero_turns_it_off(tmp_path):  # noqa: ANN001
    """⭐ **배포 ini 의 값이 실제로 `ArchonCfg` 에 꽂히는지**를 못박는다.

    ⚠️ 이 시험이 없어서 *"키는 있는데 배선이 끊겨도 통과"* 하는 상태였다
    (감사 2026-09-04).  형제 기능 `ccdflush` 는 같은 시험을 갖고 있다.
    `0` 은 **끈다**는 뜻이고 그것도 함께 본다.
    """
    import configparser
    import os as _os

    from ics_archon import config as acfg_mod

    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    for word, want in (('0.25', 0.25), ('0', 0.0)):
        cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        cp.read(_os.path.join(root, 'ics_archon.ini'), encoding='utf-8')
        cp['archon']['tcs_clock_warn'] = word
        path = tmp_path / ('ics_%s.ini' % want)
        with open(path, 'w', encoding='utf-8') as fh:
            cp.write(fh)
        assert acfg_mod.load(str(path)).tcs_clock_warn == pytest.approx(want)


def test_the_shipped_ini_carries_the_confirmed_default():
    """배포 ini 가 운영자 확정값(0.5)을 담고 있나 -- 코드 기본값과 짝이다."""
    import os as _os

    from ics_archon import config as acfg_mod

    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    ini = acfg_mod.load(_os.path.join(root, 'ics_archon.ini'))
    assert ini.tcs_clock_warn == pytest.approx(0.5)

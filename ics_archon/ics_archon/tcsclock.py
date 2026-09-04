#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TCS 시계와 우리 시계를 견준다 -- `TCSQDATE` 하나로 (운영자 지시 2026-09-04).

**왜 필요한가.**  `DATE-OBS` 는 **우리**(ICS) 시계로 찍고, `TCSQDATE`·`RA`/`DEC`
같은 포인팅 값은 **TC** 가 자기 시계로 찍어 보낸다.  두 시계가 어긋나면 헤더
안에서 **시각과 위치가 서로 다른 순간**을 가리키는데, ⛔ 그 어긋남은 파일만
봐서는 안 보인다 -- 카드 값은 둘 다 그럴싸하다.

**어떻게 재는가.**  `TCSQDATE` 는 *"TC 가 응답을 조립하는 순간"* 의 TC 시계다
(규격 5.7.1절).  우리는 질의를 **보낸 시각**(`t0`)과 응답을 **받은 시각**(`t1`)
을 알므로, 시계가 맞다면

    t0  <=  TCSQDATE  <=  t1

가 성립해야 한다.  ⭐ 그래서 왕복의 **가운데**를 TC 의 그 순간에 대응시킨다:

    오프셋 = (t0 + t1) / 2 - TCSQDATE        (⭐ 양수 = **우리가** 앞선다)
    불확실도 = (t1 - t0) / 2                 (한쪽 방향 전파 시간, 참고값)

⭐ **무엇을 잡으려는 것인가** -- *"ICS 또는 TCS 의 OS 시각이 잘못된 경우"*
(운영자 2026-09-04).  NTP 가 죽으면 어긋남은 보통 **초~분** 단위라 기본 문턱
0.5 초면 넉넉히 걸리고, 위 왕복 오차(±0.25 초 이하)에 묻히지 않는다.

⭐ **문턱은 설정값 하나다** (운영자 확정 2026-09-04, 기본 0.5 초).  ⛔ 종전에는
`max(warn_after, 불확실도)` 였는데 **두 번째 항이 한 번도 안 뽑혔다**: 성공한
질의의 왕복은 `[timing] tc_query_timeout`(0.5 초)을 넘을 수 없고 -- 더 느리면
`telemetry.query()` 가 `False` 를 돌려 `watch_tc_queries` 가 **표본을 통째로
버린다** -- 그러면 불확실도는 언제나 0.25 초 이하다.  없는 안전장치를 있는 것처럼
두면 읽는 사람이 *"느린 왕복은 이미 다뤄진다"* 고 믿으므로 걷어냈다.  불확실도는
**경고 문구에 함께 찍어** 사람이 보고 판단하게 둔다.  ⚠️ 종전 이 자리의
*"TC 가 느린 밤에 경고가 쏟아진다"* 는 **사실이 아니었다** -- 느린 TC 는 경고를
내는 것이 아니라 표본에서 빠진다.

⛔ **고치지는 않는다.**  시계를 맞추는 것은 NTP 의 몫이고, 우리는 **알리기만**
한다 -- 값을 보정해 실으면 어느 것이 실측인지 나중에 못 가른다.
"""

from __future__ import annotations

import datetime as _dt
import logging

log = logging.getLogger('ics_archon.tcsclock')

#: `2026-08-21T12:34:56.266` -- `state.stamp_iso_ms()` 형식.  ⚠️ `Z` 가 없다
#: (`TIMESYS`/`TCSTIME` 카드가 시간계를 선언한다) -- **UTC 로 읽는다**.
_FMT = '%Y-%m-%dT%H:%M:%S.%f'


def parse_stamp(text: str) -> float | None:
    """`TCSQDATE` 문자열 -> epoch 초.  못 읽으면 `None`.

    ⚠️ 초 단위(19자)로 오는 판도 받는다 -- `HKUDATE` 가 그 길이이고, TC 가
    밀리초를 뺀 판을 보낼 가능성을 배제할 근거가 없다.
    """
    raw = (text or '').strip().strip("'").strip()
    if not raw:
        return None
    for fmt in (_FMT, '%Y-%m-%dT%H:%M:%S'):
        try:
            naive = _dt.datetime.strptime(raw, fmt)
        except ValueError:
            continue
        return naive.replace(tzinfo=_dt.timezone.utc).timestamp()
    return None


class ClockWatch:
    """한 상대(TC 등)의 시계 어긋남을 지켜본다.

    ⭐ **상태를 하나 들고 있는 이유는 로그를 줄이기 위해서다** -- 어긋난 동안
    매 질의마다 울면 하룻밤에 수천 줄이 되고, 그러면 경고가 무시된다.  넘을
    때 한 번 · 돌아올 때 한 번만 말한다.
    """

    def __init__(self, name: str, warn_after: float = 0.5) -> None:
        self.name = name
        #: 이보다 크면 알린다 [s].  ⭐ **문턱은 이 값 하나다** (운영자 확정
        #: 2026-09-04) -- 왕복 불확실도를 섞지 않는다.
        self.warn_after = float(warn_after)
        #: 마지막 추정 오프셋 [s].  ⭐ **양수 = 우리가 앞선다**
        #: (운영자 확정 2026-09-04).  못 쟀으면 `None`.
        self.offset: float | None = None
        #: 마지막 왕복의 한쪽 방향 불확실도 [s].
        self.uncertainty: float = 0.0
        #: 표본 수 · 넘은 횟수 -- 진단용.
        self.samples = 0
        self.breaches = 0
        self._warned = False

    @property
    def threshold(self) -> float:
        """실제로 적용되는 문턱 -- **설정값 그대로**다 (운영자 확정 2026-09-04).

        ⛔ 종전에는 `max(warn_after, 불확실도)` 였는데, **그 두 번째 항은 한
        번도 안 뽑혔다**: 성공한 질의의 왕복은 `[timing] tc_query_timeout`
        (0.5 초)을 못 넘고 -- 더 느리면 `telemetry.query()` 가 시한 초과로
        `False` 를 돌려 표본이 통째로 버려진다 (`watch_tc_queries` 가 `ok` 를
        보고 거른다) -- 그러면 불확실도는 0.25 초 이하라 기본 문턱 0.5 초를
        절대 못 넘는다.  ⭐ **없는 안전장치를 있는 것처럼 두는 것이 더 나쁘다**
        -- 읽는 사람이 "느린 왕복은 이미 다뤄진다" 고 믿는다.

        ⭐ 불확실도는 **버리지 않고 경고 문구에 함께 찍는다** -- 오프셋이 그
        오차보다 작으면 사람이 그 사실을 보고 판단하면 된다.
        """
        return self.warn_after

    def observe(self, stamp: str, t0: float, t1: float) -> float | None:
        """질의 하나를 반영한다.  추정 오프셋을 돌려준다 (못 재면 `None`).

        `t0`/`t1` 은 **우리 시계**의 발신·수신 시각(epoch)이다.
        """
        when = parse_stamp(stamp)
        if when is None:
            # ⚠️ 못 읽는 것과 어긋난 것은 다르다 -- 여기서 0 을 돌려주면
            # "맞았다" 로 읽힌다.
            log.debug('%s 시각 비교 건너뜀 -- %s 를 못 읽었다', self.name, stamp)
            return None
        if t1 < t0:
            # 우리 시계가 왕복 중에 뒤로 밟혔다 (NTP step).  이 표본은 못 쓴다.
            log.warning('%s 시각 비교 건너뜀 -- 우리 시계가 왕복 중에 뒤로 '
                        '갔다 (t0=%.3f > t1=%.3f)', self.name, t0, t1)
            return None
        self.samples += 1
        self.uncertainty = (t1 - t0) / 2.0
        # ⭐ **우리 시계 - TC 시계** (운영자 확정 2026-09-04) -- 양수면 우리가
        # 앞선다.  ⚠️ 종전은 부호가 반대였다(`when - 가운데`).  기준을 "우리"
        # 로 두는 것이 이 기능의 목적(*"ICS 또는 TCS 의 OS 시각이 잘못된 경우를
        # 발견"*)과 읽는 방향이 같다.
        self.offset = (t0 + t1) / 2.0 - when
        self._speak()
        return self.offset

    def _speak(self) -> None:
        off, lim = self.offset or 0.0, self.threshold
        if abs(off) > lim:
            self.breaches += 1
            if not self._warned:
                self._warned = True
                log.warning(
                    '⚠️ 우리 시계가 %s 보다 %+.3f 초 앞선다 (문턱 %.3f 초, 왕복 '
                    '불확실도 %.3f 초).  ⛔ 헤더 안에서 DATE-OBS(우리 시계)와 '
                    'TCSQDATE·포인팅(%s 시계)이 다른 순간을 가리킨다 -- 값은 '
                    '보정하지 않는다(어느 것이 실측인지 못 가르게 된다).  '
                    'NTP 를 확인할 것', self.name, off, lim, self.uncertainty,
                    self.name)
        elif self._warned:
            self._warned = False
            log.info('%s 시계가 문턱 안으로 돌아왔다 (%+.3f 초, 문턱 %.3f 초)',
                     self.name, off, lim)

    def summary(self) -> str:
        """배너·진단 한 줄."""
        if self.offset is None:
            return '%s clock: no sample' % self.name
        return ('%s clock: %+.3f s (±%.3f, threshold %.3f, %d samples, '
                '%d over)' % (self.name, self.offset, self.uncertainty,
                              self.threshold, self.samples, self.breaches))


def field_value(fields, key: str) -> str:  # noqa: ANN001
    """TC 응답 필드 목록(원문 순서 보존)에서 값 하나.

    ⚠️ `dict(fields)` 로 접으면 같은 키가 두 번 온 경우 뒤엣것이 이기는데,
    여기서는 **먼저 온 것**이 응답의 그 필드다.
    """
    for name, value in fields or ():
        if name.upper() == key:
            return value
    return ''


def watch_tc_queries(relay, watch, key: str = 'TCSSTATUS',  # noqa: ANN001
                     field: str = 'TCSQDATE') -> None:
    """`TelemetryRelay.query()` 를 감싸 응답마다 시계를 견준다.

    ⭐⭐ **`ics_sim` 은 0줄로 둔다** -- 이 **인스턴스의 메서드 하나**만 감싼다.
    ⚠️ 객체를 갈아 끼우지 않는 것이 의도다: 시퀀서가 같은 relay 를 들고
    있으므로 교체하면 한쪽만 바뀌어 **조용히 반쯤 적용된다**.

    ⚠️ 시한 초과·주입 실패는 `query()` 가 `False` 를 돌려주고, 그때는 견주지
    않는다 -- 폴백(canned)이 채운 `TCSQDATE` 는 **우리 시계로 찍은 값**이라
    견주면 언제나 0 이 나와 *"맞았다"* 로 읽힌다.
    """
    import time as _time

    inner = relay.query

    async def query(what: str) -> bool:  # noqa: ANN202
        t0 = _time.time()
        ok = await inner(what)
        if ok and what.upper() == key:
            fields = (relay.tcs_fields if key == 'TCSSTATUS'
                      else relay.aux_fields)
            watch.observe(field_value(fields, field), t0, _time.time())
        return ok

    relay.query = query

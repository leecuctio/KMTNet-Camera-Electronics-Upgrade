#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`HKDATA` 응답 본문 -- ICS 가 자기 헤더를 채우려고 ICG 에 묻는 것.

운영자 확정 문면은 **DevNote 11.14-(1)** 이고 이 모듈이 그것을 그대로 만든다:

    ICS>ICG HKDATA
    ICG>ICS DONE: HKDATA HKQDATE=… HKUDATE=… HKSTALE=n VACGAUGE=… DEWPRES=…
                  HTREN=… HTRSET=… HTROUT=… HTRFORCE=… <계약키…>

⭐ **`HK` 와 `HKDATA` 가 같은 본문을 낸다** (운영자 지시) -- 커맨드워드만 다르다.
그래서 조립은 여기 한 곳뿐이고, 두 명령이 같은 함수를 부른다.

## 지키는 규약 (전부 DevNote 11.14)

* ⭐ **`HKQDATE` 23자 · `HKUDATE` 19자** -- 길이가 다른 것이 의도다.  둘이 뒤바뀌면
  눈에 보인다.  `HKQDATE` 는 **명령을 받은 시각**(ICG 시계), `HKUDATE` 는 **자료를
  획득한 시각**(가장 낡은 표본).
* ⭐ **`HKUDATE` 는 HK 루프의 생존 신호다** -- 응답은 오는데 두 바퀴 넘게 그 값이
  그대로면 루프가 멈춘 것이고, 그것은 링크 장애와 구별된다.
* **`HKSTALE` = 낡아서 뺀 계약 키 수.**  완전성 검사가 `실린 계약키 + HKSTALE = 10`
  이므로 **낡은 키는 싣지 않는다** -- 값을 sentinel 로 채우면 그 셈이 깨진다.
* ⛔ **따옴표를 안 붙인다** (11.14-(1-c) -- `quote_always()` 를 뒤집은 결정).  같은
  프로그램의 `HK` 가 이미 안 붙이고, 값에 공백이 생길 구조가 없다.  대신 조립 때
  `hkwire.wire_safe()` 가 공백·따옴표를 **거부**한다: *"공백이 없다"* 를 가정이
  아니라 지켜지는 성질로 만든다.
* ⭐ **불린은 낱말** -- `HTREN`/`HTRFORCE` 는 `ON`/`OFF`, `VACGAUGE` 는
  `ON`/`OFF`/`UNKNOWN`.  ⛔ **`0`/`1` → 낱말 매핑은 여기 한 곳에서만** 한다.
* ⛔ **못 읽으면 아예 안 싣는다.**  ICS 가 그 카드를 규격 5.0절 sentinel(`NC`)로
  채운다 -- 모르는 것을 `OFF` 로 적으면 *"껐다"* 고 거짓말한다.
* ⛔ **`FORCELEVEL` 은 안 싣는다** (운영자 확정 -- 카드가 아니다).

## 되읽기는 세 층이다 (11.14-(1), 신뢰도 순)

| 층 | 믿을 수 있나 |
|---|---|
| 우리 캐시 `ctrl.config` | ⛔ 못 믿는다 -- `set_config()` 가 **왕복 실패에도 먼저** 갈아 끼운다 (11.13 F5) |
| **`RCONFIG`** | ✅ `WCONFIG` 가 실제로 앉은 값.  `HTREN`·`HTRSET`·`HTRFORCE` 가 여기서 온다 |
| `STATUS` | ✅ 가장 강하다.  `HTROUT` 이 여기서 온다 (HK 루프가 읽어 둔 것) |
"""

from __future__ import annotations

import logging

from ics_archon import _simpath

_simpath.ensure()

from ics_sim.state import stamp_iso, stamp_iso_ms, utcnow  # noqa: E402

from ics_archon import hkwire  # noqa: E402

from . import heater  # noqa: E402

log = logging.getLogger('icg_archon.hkdata')

#: 계약 키 **10개** -- `HKSTALE` 완전성 셈이 이 수에 걸려 있다
#: (`실린 계약키 + HKSTALE = 10`).  ⚠️ 늘리거나 줄이면 받는 쪽 검사도 함께 고칠 것.
CONTRACT_KEYS = ('dewpres', 'ccdtemp', 'dmptemp', 'pt30n1', 'pt30n2',
                 'charcoal', 'wallbrd', 'hebox', 'fsatemp', 'fsahum')

#: 계약 키의 와이어 이름과 표기 -- `(키, 와이어이름, 소수자리, 부호)`.
#:
#: ⭐ **온도는 부호를 붙인다** (규격 5.0절 · DevNote 11.14 *"HKDATA 답변과 FITS
#: header 의 모든 온도정보에 +/- 부호"*).  ⛔ `FSAHUM` 은 습도라 대상이 아니고,
#: `DEWPRES` 는 지수 표기 원문이라 여기 없다(따로 싣는다).
_FIELDS = (
    ('ccdtemp', 'CCDTEMP', 2, True),
    ('dmptemp', 'DMPTEMP', 2, True),
    ('pt30n1', 'PT30N1', 2, True),
    ('pt30n2', 'PT30N2', 2, True),
    ('charcoal', 'CHARCOAL', 2, True),
    ('wallbrd', 'WALLBRD', 2, True),
    ('hebox', 'HEBOX', 2, True),
    # ⭐ **2자리다** (운영자 확정 2026-09-09, 실측 근거).  Radionode 원문이
    # `"ch_value":"22.35"` · `"47.67"` 로 **소수 2자리**를 준다 -- 1자리로 적으면
    # 받은 자리를 버린다.
    # ⛔ 종전 1자리의 근거는 *"레거시 `ENS1='23.0'` 선례"* 였는데 **성립하지 않는
    # 유추**였다: `ENS1~7` 은 규격 5.8절이 *"중계 그대로 -- 우리가 표기를 만들지
    # 않는다"* 로 규정해 **TCSSTATUS 가 준 자릿수**가 그대로 갈 뿐이고, FSA 는
    # 출처가 달라 2자리를 준다 (운영자).
    # ⏳ 규격 문면(5.0절 · v1.18 확인 항목 · 견본 3장)은 `main` 라운드 이월.
    ('fsatemp', 'FSATEMP', 2, True),
    ('fsahum', 'FSAHUM', 2, False),
)


def _word(raw) -> str | None:  # noqa: ANN001
    """`RCONFIG` 원값 `0`/`1` -> `OFF`/`ON`.  못 읽으면 `None` (= 안 싣는다).

    ⛔ **매핑은 여기 한 곳뿐이다** -- 두 곳에서 하면 갈린다 (11.14-(1-a)).
    """
    if raw is None:
        return None
    try:
        return 'ON' if int(float(str(raw).strip())) else 'OFF'
    except (TypeError, ValueError):
        log.warning('불린으로 못 읽는 되읽기 값이라 뺀다 -- %r', raw)
        return None


def _signed_or_none(raw) -> str | None:  # noqa: ANN001
    """수치면 `+00.00` 표기, 아니면 `None` (= 안 싣는다).  `HTRSET` 전용."""
    try:
        return hkwire.fmt_signed(float(raw), 2)
    except (TypeError, ValueError):
        return None


def _unsigned(value, digits: int) -> str | None:  # noqa: ANN001
    """부호 없는 소수 표기 (`FSAHUM`·`HTROUT`).  수치가 아니면 `None`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return '%.*f' % (digits, value)


async def body(app, *, ctrl=None, now: bool = False) -> str:  # noqa: ANN001
    r"""`HKDATA`/`HK` 응답 본문 한 줄.

    ## ⭐ 갈래가 둘이다 (운영자 확정 2026-09-09)

    | | 히터 설정 셋 (`HTREN`·`HTRSET`·`HTRFORCE`) | 왕복 |
    |---|---|---|
    | `now=False` (**기본**) | HK 폴러가 60초마다 받아 둔 값 (`sensors()`) | **없다** |
    | `now=True` (`HKDATA NOW`) | `RCONFIG` **즉시 되읽기** | 셋 |

    ⭐ **기본이 폴링값인 것이 요점이다** -- 리모트 명령에 **왕복 없이 곧바로**
    답한다.  ⛔ 나머지 값(RTD·진공·`HTROUT`·Radionode)은 **원래부터** 폴링값이라
    갈래와 무관하다 -- `STATUS` 를 이 자리에서 다시 읽은 적이 없다.

    ⚠️ **낡음을 숨기지 않는다** -- `HKUDATE`(가장 낡은 표본시각)와 `HKSTALE` 이
    그대로 나가므로, 방금 바꾼 설정이 아직 안 실렸으면 **시각으로 드러난다.**
    ⭐ 그리고 확인 창구가 따로 있다: `HTRSET`/`HTRFORCE` 를 **인자 없이** 치면
    `RCONFIG` 즉시 조회다.

    ⚠️ `now=True` 여도 **취득을 방해하지 않는다** -- 왕복은 `_locked_thread` 가
    한 줄로 세우므로 진행 중인 FETCH 뒤에 설 뿐이다 (실측 최악 108 ms,
    DevNote 11.55).  ⛔ 그러니 따로 기다리는 장치를 두지 않는다.

    ⚠️ `now=True` 인데 컨트롤러가 없거나 왕복이 실패하면 **폴링값으로 물러난다**
    -- 그 셋만 빼 버리면 `now` 가 오히려 정보를 줄인다.
    """
    hk = getattr(app, 'hk', None)
    if hk is None:
        raise RuntimeError('HK monitor is not running')
    # ⚠️ `now` 는 바로 아래에서 **시각**으로 다시 쓰인다 -- 갈래 표시를 먼저 뜬다.
    now_read = bool(now)

    now = utcnow()
    if now_read:
        # ⭐ **한 바퀴를 지금 돌린다** -- RTD·진공·`HTROUT`·히터 설정·Radionode
        # 가 다 갱신되고, `_sample` 에 담기므로 **다음 헤더도 이 값을 본다**
        # (운영자 2026-09-09).  ⚠️ Radionode 는 충분히 낡았을 때만 다시 친다.
        # ⚠️ **실패해도 답은 낸다** -- 폴링값이 그대로 나가는 것이 무응답보다 낫다.
        try:
            await hk.refresh_now()
        except Exception as exc:           # noqa: BLE001
            log.warning('HKDATA NOW: 갱신 실패 -- %s.  폴링값으로 답한다', exc)
    vals = hk.sensors()                    # 신선한 계약 키 + hkudate
    pairs: list[tuple[str, object]] = [
        ('HKQDATE', stamp_iso_ms(now)),    # 23자 -- 명령을 받은 시각
    ]

    # ⭐ `HKUDATE` -- 자료를 획득한 시각(가장 낡은 표본), **19자**.
    # `hk.sensors()` 가 이미 가장 낡은 것으로 만들어 둔다.
    udate = vals.get('hkudate')
    if udate:
        # `sensors()` 는 `stamp_iso`(19자)로 만든다 -- 그대로 쓴다.
        pairs.append(('HKUDATE', udate))

    # ⭐ **낡은 키는 싣지 않고 세어서 알린다** -- sentinel 로 채우면 완전성 셈이 깨진다.
    carried = [k for k in CONTRACT_KEYS if vals.get(k) is not None]
    pairs.append(('HKSTALE', len(CONTRACT_KEYS) - len(carried)))

    # 진공 -- 상태 낱말 바로 뒤에 압력 (운영자 지시).
    gauge = getattr(app, 'gauge', None) or getattr(hk, 'gauge', None)
    pairs.append(('VACGAUGE', getattr(gauge, 'word', None) if gauge else None))
    dew = vals.get('dewpres')
    pairs.append(('DEWPRES', dew if dew is not None else None))

    # 히터 넷 -- ⛔ `FORCELEVEL` 은 안 싣는다.
    #
    # ⭐ **기본은 폴링값이다** -- HK 가 한 바퀴마다 `RCONFIG` 로 받아 `_sample`
    # 에 담아 두므로(11.52-(2)) 여기서 왕복이 없다.  ⭐ 그래서 **헤더와
    # `HKDATA` 가 같은 원천**을 본다 -- 11.52 가 만들었던 갈림이 여기서 닫힌다.
    ctrl = ctrl if ctrl is not None else getattr(hk, 'ctrl', None)
    htren = _word(vals.get('htren'))
    htrset = _signed_or_none(vals.get('htrset'))
    htrforce = _word(vals.get('htrforce'))
    # ⛔ **여기서 따로 되읽지 않는다** -- `NOW` 는 위에서 `hk.refresh_now()` 로
    # 한 바퀴를 돌렸고 그 바퀴가 히터 설정 셋도 `RCONFIG` 로 읽어 `_sample` 에
    # 담았다.  ⚠️ 여기서 또 읽으면 **왕복이 두 배**가 되고, 두 값이 갈리면
    # 어느 쪽이 정본인지 다투게 된다 (11.52 가 그 부류였다).
    pairs.append(('HTREN', htren))
    pairs.append(('HTRSET', htrset))
    # `HTROUT` 은 `STATUS` 에서 온다 -- HK 루프가 이미 읽어 뒀다 (11.30).
    pairs.append(('HTROUT', _unsigned(vals.get('htrout'), 3)))
    pairs.append(('HTRFORCE', htrforce))

    # 계약 키 나머지 아홉 (`dewpres` 는 위에서 이미 실었다).
    for key, wire, digits, signed in _FIELDS:
        raw = vals.get(key)
        if raw is None:
            continue
        try:
            num = float(raw)
        except (TypeError, ValueError):
            log.warning('HKDATA: %s 값이 수치가 아니라 뺀다 -- %r', wire, raw)
            continue
        pairs.append((wire,
                      hkwire.fmt_signed(num, digits) if signed
                      else _unsigned(num, digits)))

    return hkwire.pairs_to_body(pairs)

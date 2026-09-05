#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HK 와이어 포맷 -- `HKDATA` · `C1HKDATA`/`C2HKDATA` 의 **한 곳뿐인 정본**
(운영자 확정 2026-09-04, DevNote 11.26).

⭐ **왜 여기 있나.**  같은 문면을 ICS(science 컨트롤러 둘)와 ICG(guide
컨트롤러 하나·듀어 HK)가 **둘 다** 조립한다.  포맷 규약이 두 곳에 있으면
반드시 갈린다 -- 이 저장소가 `rawcards` 기계 사본 셋으로 이미 겪은 부류다.
그래서 **키 이름표·표기·안전 검사**를 여기 모으고, 두 프로그램은 값만 준다.

**확정된 규약** (운영자 2026-09-04):

* ⛔ **따옴표를 붙이지 않는다** -- 기존 `HK` 응답과 같은 규칙 (DevNote
  11.14-(1-c)).  대신 조립할 때 **공백·따옴표가 든 값을 거부**한다.
  그러면 *"값에 공백이 없다"* 가 가정이 아니라 **지켜지는 성질**이 된다.
* ⭐ **온도에는 언제나 부호** (`+40.1`) · ⭐ **전압·전류에도 부호**
  (`+5.023` · `-17.067`) -- 운영자 2026-09-04.  ⚠️ 이것은 DevNote
  11.14-(1-d) 의 *"`*_V`/`*_I` 는 부호 대상 아님"* 을 **뒤집은 결정**이다.
* ⭐ **낡거나 못 읽은 값은 싣지 않고 `<접두>STALE` 로 센다** -- FITS 카드
  (`C1_TEMP` 파이프 나열)와 **일부러 다르다**: 카드는 자리가 곧 항목이라
  결측도 `NC` 로 자리를 채워야 하지만(5.6.1절), 와이어는 이름이 붙어 있어
  빠져도 자리가 안 밀린다.

**자리 이름** -- 규격 5.6.1/10.4절 라벨(`Mod9:HVYBias`)에서 기계로 만든다:

    Backplane    -> BP_TEMP
    Mod1:LVDS    -> M1_LVDS_TEMP
    Mod2:Driver  -> M2_DRV_TEMP
    Mod9:HVYBias -> M9_HVYB_TEMP

⭐⭐ **`M9` 는 형이 갈려도 이름을 고정한다** (운영자 확정 2026-09-04):
관측소 science `MOD9` 는 형 18(HVYBias)인데 **KMTK 벤치기는 형 8(HVXBias)**
이고 **guide 도 HVXBias** 다 (`parse.MODULE_TYPES` 주석 · 규격 10.4절).
⛔ 형을 그대로 이름에 넣으면 **같은 명령이 기기마다 다른 키를 뱉어** 받는
쪽이 파서를 미리 못 짠다 -- 그래서 셋 다 **`M9_HVYB_TEMP`** 로 통일한다.
⚠️ 대가: guide 에서는 **이름표(HVXBias)와 키(HVYB)가 어긋난다.**  그 어긋남이
조용히 묻히지 않도록 `type_mismatches()` 가 기동 검사용으로 짚어 준다 --
와이어에는 안 싣는다(통일이 목적이므로).

**guide 전용 `HEATER` 레일** -- 와이어 키는 **`HTR_V`/`HTR_I`** 다 (운영자
확정 2026-09-04).  STATUS 필드는 **`HEATER_V`/`HEATER_I`** 다(매뉴얼 p.47 ·
FW 1.0.1252 확인, 2026-09-05).  이 개명은 **출력 이름만** 정한 것이다 -- 값이
실기에서 채워지는지는 첫 구동 대기.
"""

from __future__ import annotations

import logging

from ics_archon import _simpath                       # noqa: F401

from ics_sim.state import stamp_iso, stamp_iso_ms      # noqa: E402,F401

log = logging.getLogger('ics_archon.hkwire')


# ---------------------------------------------------------------------------
# 시각 -- 두 개를 **다른 길이로** 낸다
# ---------------------------------------------------------------------------
#
# ⭐ **길이가 다른 것이 의도다** -- 질의 시각은 밀리초 **23자**
# (`stamp_iso_ms`), 표본 시각은 초 **19자**(`stamp_iso`)라, 둘이 뒤바뀌면
# **눈에 보인다** (DevNote 11.14-(1)).
#
# ⛔ **새 헬퍼를 만들지 않는다** -- DevNote 11.14-(1) 이 *"초 단위 스탬프
# 함수가 프로젝트에 없으므로 icg 쪽에 헬퍼 하나를 둔다"* 고 적었는데 그것이
# **사실이 아니었다**: `ics_sim.state.stamp_iso()` 가 정확히 그 함수다
# (`'%Y-%m-%dT%H:%M:%S'` = 19자).  ⭐ 그 문면을 믿고 사본을 만들면 이 저장소가
# `rawcards` 로 이미 겪은 **기계 사본 넷** 부류가 하나 더 생긴다 (DevNote
# 11.26 에서 정정).
#
# ⚠️ 둘 다 **인자 없이 부르지 말 것** -- `stamp_iso_ms()` 는 초와 밀리초가
# 서로 다른 `utcnow()` 호출에서 나와 초 경계에서 시각이 최대 1초 튄다
# (DevNote 11.12-(5)).  한 번 뜬 시각을 넘겨야 두 시각이 같은 순간이 된다.


# ---------------------------------------------------------------------------
# 자리 이름표 -- 규격 라벨에서 기계로 만든다
# ---------------------------------------------------------------------------

#: 모듈 형 이름 -> 와이어 약칭.  ⭐ **정본은 규격 라벨**(`TEMP_MOD_LABELS`)
#: 이고 이 표는 줄이기만 한다 -- 여기 없는 형이 오면 그대로 대문자로 쓴다
#: (조용히 자리를 잃는 것보다 낫다).
#:
#: ⛔ **`HVXBias` 가 `HVYB` 로 접히는 것은 오타가 아니다** -- 위 머리말의
#: "형이 갈려도 이름을 고정한다" 가 여기 한 줄로 구현돼 있다.
TYPE_ABBR: dict[str, str] = {
    'LVDS': 'LVDS',
    'Driver': 'DRV',
    'DriverX': 'DRVX',
    'LVXBias': 'LVXB',
    'LVYBias': 'LVYB',
    'HVXBias': 'HVYB',          # ⭐ 통일 (운영자 2026-09-04) -- 위 머리말
    'HVYBias': 'HVYB',
    'ADM': 'ADM',
    'AD': 'AD',
    'HeaterX': 'HTRX',
    'Heater': 'HTR',
    'Atlas': 'ATLAS',
}

#: `HEATER` 레일의 와이어 키 접두 (운영자 확정 2026-09-04).
HEATER_RAIL_KEY = 'HTR'


def temp_key(label: str) -> str:
    """규격 라벨 -> 와이어 키.  `'Mod9:HVYBias'` -> `'M9_HVYB_TEMP'`.

    `'Backplane'` 처럼 모듈 번호가 없는 자리는 `'BP_TEMP'` 다.
    """
    if ':' not in label:
        head = label.strip()
        if head.lower() == 'backplane':
            return 'BP_TEMP'
        return '%s_TEMP' % head.upper()
    slot, kind = (part.strip() for part in label.split(':', 1))
    number = slot[3:] if slot.lower().startswith('mod') else slot
    return 'M%s_%s_TEMP' % (number, TYPE_ABBR.get(kind, kind.upper()))


def temp_keys(labels) -> tuple[str, ...]:              # noqa: ANN001
    """라벨 표 -> 키 표.  ⚠️ **자리 수는 그대로다** (자리 = 항목).

    ⛔ 키가 겹치면 값 하나가 조용히 덮인다 -- 그러면 받는 쪽은 자리 하나가
    빠진 것으로 읽는데 `STALE` 은 0 이라 어긋남이 안 보인다.  그래서 여기서
    **겹침을 막는다** (형 통일로 `M9` 둘이 생기는 구성이 실제로 가능하다).
    """
    keys = tuple(temp_key(x) for x in labels)
    if len(set(keys)) != len(keys):
        dup = sorted({k for k in keys if keys.count(k) > 1})
        raise ValueError('온도 자리 이름이 겹친다: %s -- 라벨 표를 보라 (%s)'
                         % (', '.join(dup), ', '.join(labels)))
    return keys


def rail_keys(rail: str) -> tuple[str, str]:
    """레일 이름 -> `(전압 키, 전류 키)`.

    ⭐ 이름을 **발명하지 않는다** -- `P2V5_V`/`P2V5_I` 는 Archon `STATUS`
    필드명 그대로다.  ⚠️ 예외는 guide 전용 `HEATER` 하나이고, 그것은 출력
    이름을 **`HTR_V`/`HTR_I`** 로 못박았다 (위 머리말).
    """
    head = HEATER_RAIL_KEY if rail == 'HEATER' else rail
    return '%s_V' % head, '%s_I' % head


# ---------------------------------------------------------------------------
# 값 표기 -- 부호를 붙이고, 와이어에 못 나갈 값을 막는다
# ---------------------------------------------------------------------------

#: 온도 소수 자리 -- 컨트롤러 모듈 온도는 **1자리** (`C1_TEMP` 카드와 같다).
#: ⚠️ 듀어 HK 온도(`CCDTEMP` 등)는 **2자리**이고 그쪽은 `rawhdr.format_temp`
#: 가 맡는다 -- 두 층의 자리수가 다른 것은 규격이 그렇게 정한 것이다.
TEMP_DIGITS = 1

#: 전압·전류 소수 자리 -- **3자리**.  ⭐ 카드는 guide 만 2자리로 반올림하는데
#: (10.4절) 와이어는 **덜 접는 쪽**이다: 접는 것은 카드를 만드는 쪽에서 늦게
#: 해도 되지만, 와이어에서 접으면 그 정보는 되찾을 수 없다.
VOLT_DIGITS = 3


def fmt_signed(value, digits: int) -> str | None:      # noqa: ANN001
    """수치를 **부호를 붙여** 표기.  수치가 아니면 `None` (= 싣지 않는다).

    ⚠️ `bool` 을 막는다 -- 파이썬에서 `True` 는 수치라 `+1.0` 으로 조용히
    실린다.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return '%+.*f' % (digits, value)


def wire_safe(key: str, value: str) -> bool:
    """와이어에 낼 수 있는 값인가 -- **공백·따옴표가 있으면 아니다**.

    ⛔ 따옴표를 안 붙이기로 했으므로(11.14-(1-c)) 공백이 든 값은 `parse_kv`
    에서 **조용히 잘린다** -- `DEWPRES=6.93 e-04` 가 `'6.93'` 이 되어
    sentinel 이 아니라 **그럴듯한 틀린 값**으로 카드에 실린다.  값에
    따옴표가 있으면 어디서 끊을지 모른다.
    """
    if any(ch.isspace() for ch in value) or "'" in value or '"' in value:
        log.warning('와이어에 못 낼 값이라 뺀다 -- %s=%r (공백이나 따옴표가 '
                    '들어 있다).  ⭐ 값이 빠지면 STALE 로 세어져 받는 쪽이 '
                    '결측을 안다', key, value)
        return False
    return True


def pairs_to_body(pairs) -> str:                       # noqa: ANN001
    """`(키, 값)` 나열 -> 본문 한 줄.  값이 `None` 인 자리는 **빠진다**."""
    out = []
    for key, value in pairs:
        if value is None:
            continue
        text = str(value)
        if wire_safe(key, text):
            out.append('%s=%s' % (key, text))
    return ' '.join(out)


# ---------------------------------------------------------------------------
# `CxHKDATA` 본문
# ---------------------------------------------------------------------------

def type_mismatches(status, labels) -> list[str]:      # noqa: ANN001
    """STATUS 실측 형과 규격 라벨이 어긋난 자리 (기동 검사용, 와이어 아님).

    ⭐ 이름을 통일한 대가를 **드러내는 자리**다 -- `M9_HVYB_TEMP` 라는 키는
    어디서나 같지만, 그 상자가 실제로 HVXBias 면 그 사실이 어디에도 안
    남는다.  기동에서 한 번 짚어 주면 *"이름이 실물과 다르다"* 를 사람이 알
    수 있다 (DevNote 11.26).
    """
    from ics_archon.archon import parse as _parse      # 순환 수입 회피
    bad: list[str] = []
    if not status:
        return bad
    for label in labels:
        if ':' not in label:
            continue
        slot, kind = (part.strip() for part in label.split(':', 1))
        if not slot.lower().startswith('mod'):
            continue
        raw = status.get('%s_TYPE' % slot.upper())
        if raw is None:
            continue                                   # 보고가 없으면 안 센다
        try:
            seen = _parse.MODULE_TYPES.get(int(str(raw).strip()))
        except (TypeError, ValueError):
            continue
        if seen and seen != kind:
            bad.append('%s: 규격 라벨 %s / 실측 %s' % (slot, kind, seen))
    return bad


def ctrl_body(*, prefix: str, labels, rails, unit,     # noqa: ANN001
              status=None, ident_key=None, ident=None,
              qdate=None, udate=None) -> tuple[str, int]:
    """`CxHKDATA` 본문과 **거른 자리 수**를 돌려준다.

    Args:
        prefix: `'C1'` · `'C2'` -- 시각·`STALE` 키의 접두.
        labels: 규격 온도 라벨 표 (`rawhdr.TEMP_MOD_LABELS` 또는 guide 판).
        rails: 전원 레일 표 (`rawhdr.VOLT_RAILS` 또는 guide 판 8자리).
        unit: `parse.telemetry_of()` 꼴 -- `{'temp': [...], 'volt': [...],
            'curr': [...]}`.  빈 dict 이면 **전 자리가 결측**이다.
        status: 원본 `STATUS` -- `VALID`/`POWER`/`POWERGOOD` 를 여기서 읽는다.
        ident_key/ident: `CTRL1ID=…` -- ⭐ **장식이 아니다.**  guide 도
            `C1HKDATA` 를 쓰기로 했으므로(운영자 2026-09-04) **같은 이름이
            노드에 따라 다른 상자**를 가리킨다.  받은 쪽이 *"어느 상자가
            답했나"* 를 아는 수단이 이 필드뿐이다.

    ⭐ **`STALE` 은 텔레메트리 자리만 센다** -- `VALID`/`POWER`/`POWERGOOD`·
    정체·시각은 계약 자리가 아니다.  `HKDATA` 에서 `VACGAUGE`/`HTR*` 가
    `HKSTALE` 셈에 안 들어가는 것과 같은 규칙이다.
    """
    tkeys = temp_keys(labels)
    temps = list(unit.get('temp') or [None] * len(tkeys))
    volts = list(unit.get('volt') or [None] * len(rails))
    currs = list(unit.get('curr') or [None] * len(rails))
    if len(temps) != len(tkeys) or len(volts) != len(rails) \
            or len(currs) != len(rails):
        raise ValueError('%sHKDATA 자리 수가 표와 다르다 -- 온도 %d/%d · '
                         '레일 %d·%d/%d' % (prefix, len(temps), len(tkeys),
                                            len(volts), len(currs),
                                            len(rails)))

    head = [('%sQDATE' % prefix, qdate), ('%sUDATE' % prefix, udate)]
    slots: list[tuple[str, str | None]] = []
    for key, value in zip(tkeys, temps):
        slots.append((key, fmt_signed(value, TEMP_DIGITS)))
    for rail, volt, curr in zip(rails, volts, currs):
        vkey, ikey = rail_keys(rail)
        slots.append((vkey, fmt_signed(volt, VOLT_DIGITS)))
        slots.append((ikey, fmt_signed(curr, VOLT_DIGITS)))
    stale = sum(1 for _, value in slots if value is None)

    state: list[tuple[str, str | None]] = [('%sSTALE' % prefix, stale)]
    if ident_key and ident:
        state.append((ident_key, ident))
    if status:
        for field in ('VALID', 'POWER', 'POWERGOOD'):
            raw = status.get(field)
            if raw is not None:
                state.append((field, str(raw).strip()))
    return pairs_to_body(head + state + slots), stale

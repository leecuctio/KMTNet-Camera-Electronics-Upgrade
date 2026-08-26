#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional FITS output — raw spec 5장 헤더의 물리 기록.

지금은 더미 배열을 쓰지만 **헤더 생성 경로는 처음부터 실제와 같게** 만든다.
다음 단계에서 백엔드의 fetch_image() 가 실제 픽셀을 돌려주면 그대로 저장된다.

헤더는 `rawcards.render()` 가 만든 **순서 있는 카드 목록**(`(keyword, value,
comment)`, `COMMENT` 구분 카드 포함)으로 온다 -- 견본 v1.0 pair 가 카드 순서·
comment·패딩까지 바이트 단위 기준이기 때문이다 (raw spec 5장 머리말).
`SIMPLE`~`BZERO` 구조 카드는 astropy 가 데이터에서 만들고, 여기서 comment 만
견본대로 맞춘다.
"""

from __future__ import annotations

import logging
import os
import time

log = logging.getLogger('ics_sim.fits')

#: FITS 헤더 키워드는 8자 이하여야 한다 (raw spec 5.0절 -- `HIERARCH` 금지).
_MAX_KEY = 8

#: 값 하나가 카드 **한 장**에 들어갈 수 있는 최대 길이 (raw spec **5.0절**).
#: `KEY     = '`(11) + 값 + `'`(1) = 80 이 되는 지점이고, 규격이 "값만으로
#: 68자 초과" 라고 적은 그 수다.
#:
#: ⚠️ **이보다 길면 astropy 가 `CONTINUE` 규약으로 카드를 여러 장으로 늘린다.**
#: 그러면 견본이 못박은 **144 레코드 · 11,520 바이트**가 깨지고, 경고는 한 줄도
#: 안 뜬다.  5.0절이 "값을 자르되 경고를 남긴다" 고 한 자리다.
_VALUE_MAX = 68


def _fit_to_card(key: str, text: str, comment: str) -> tuple[str, str]:
    """raw spec **5.0절** 카드 폭 규범 -- **comment 를 먼저 자르고, 값은 마지막.**

    값이 자료이고 comment 는 설명이기 때문이다 -- 특히 `Cn_*` 나열 카드는
    **자리가 곧 항목**이라(5.6.1절) 값이 잘리면 뒤 항목이 통째로 사라지는데
    읽는 쪽은 그 사실을 알 방법이 없다.  자리 뜻의 정본은 5.6.1절 표다.

    astropy 도 값이 길면 comment 를 먼저 줄이므로 첫 단계는 맡겨도 되지만,
    **둘째 단계는 맡길 수 없다** -- 값만으로 68자를 넘으면 astropy 는 자르지
    않고 `CONTINUE` 로 **카드 수를 늘린다**(`_VALUE_MAX` 주석).  그래서 여기서
    미리 잘라 규격대로 경고를 남긴다.  `ics_archon/archon/fitswrite.card_image()`
    가 같은 규칙을 자기 카드 조립기에 갖고 있다 -- 이쪽은 astropy 경로 몫이다.

    Returns:
        `(값, comment)` -- 그대로일 수도, 한쪽이 짧아졌을 수도 있다.
    """
    # astropy 는 값 안의 홑따옴표를 겹쳐 쓴다 (FITS 표준 4.2.1) -- 폭은 겹친
    # 뒤 길이로 따져야 한다.
    def _wide(s: str) -> int:
        return len(s.replace("'", "''"))

    room = _VALUE_MAX - (3 + len(comment) if comment else 0)
    if _wide(text) <= room:
        return text, comment
    if _wide(text) <= _VALUE_MAX:
        keep = max(_VALUE_MAX - _wide(text) - 3, 0)
        log.warning('FITS 카드 %s 의 값이 길어 comment 를 줄였다 (값 %d자) -- '
                    '값은 그대로다 (raw spec 5.0절)', key, _wide(text))
        return text, comment[:keep].rstrip()
    # comment 를 다 지워도 안 들어간다 -- 값을 자르고 **경고를 남긴다**.
    cut = text
    while cut and _wide(cut) > _VALUE_MAX:
        cut = cut[:-1]
    log.warning('FITS 카드 %s 의 값이 너무 길다 (%d > %d) -- comment 를 다 '
                '지워도 안 들어가 값을 잘라낸다.  자리 나열 카드면 뒤 항목이 '
                '사라진다 (raw spec 5.0절 · 5.6.1절)',
                key, _wide(text), _VALUE_MAX)
    return cut, ''


class FitsStr(str):
    """**문자열로 강제**할 헤더값.  숫자처럼 보여도 숫자로 바꾸지 않는다.

    `_apply_header`(딕셔너리 경로)는 텔레메트리를 와이어에서 받은 `key=value`
    문자열로 다루기 때문에 숫자로 보이는 값을 숫자로 바꾼다.  **식별자에는
    그게 재앙이다**: 숫자 카드는 zero-padding 을 파괴한다 (raw spec 5.0절 --
    `'…000010'` -> `…00001`).  그래서 정체성 카드는 이 타입으로 싣는다.

    템플릿 경로(`apply_cards`)에서는 형이 템플릿에 있으므로 필요 없다.
    """

    __slots__ = ()


def write_dummy_fits(path: str, data, header) -> int:  # noqa: ANN001
    """FITS 파일 하나를 쓰고 전송률(KB/sec)을 돌려준다.

    `header` 는 `rawcards.render()` 의 카드 목록 또는 (하위 호환) 딕셔너리.
    astropy 가 없거나 data 가 None 이면 0 을 돌려준다 (호출측이 대체 전송률을
    쓴다).  astropy 는 여기서만 import 한다 -- 메시지만 내는 기본 모드에서는
    의존성이 없어야 하기 때문이다.

    **`CHECKSUM`/`DATASUM` 은 쓰지 않는다** -- raw spec OI-7 이 미도입으로
    두었다 (도입 여부 결정 대기).  견본 v1.0 에도 없다.
    """
    if data is None:
        return 0
    try:
        from astropy.io import fits
    except ImportError:
        log.warning('astropy 없음 -- FITS 저장을 건너뜁니다 (%s)', path)
        return 0

    hdu = fits.PrimaryHDU(data=_as_unsigned16(data))
    # 견본 v1.0 에 없는 `EXTEND` 를 뗀다 -- astropy 가 기본으로 넣지만
    # single HDU 라 선언할 확장이 없다 (raw spec 3장).
    if 'EXTEND' in hdu.header:
        del hdu.header['EXTEND']
    # 구조 카드의 comment 를 견본 v1.0 에 맞춘다.  BZERO/BSCALE 은 astropy 가
    # uint16 데이터에서 값을 만들지만, 카드가 미리 있으면 comment 는 보존된다.
    hdu.header['BSCALE'] = (1, 'PHYSICAL=INTEGER*BSCALE+BZERO')
    hdu.header['BZERO'] = (32768, '')
    if isinstance(header, dict):
        _apply_header(hdu.header, header)
    else:
        apply_cards(hdu.header, header)

    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    started = time.monotonic()
    hdu.writeto(path, overwrite=True)
    elapsed = max(time.monotonic() - started, 1e-6)

    size_kb = os.path.getsize(path) / 1024.0
    return int(size_kb / elapsed)


def _as_unsigned16(data):  # noqa: ANN001, ANN201
    """더미 픽셀을 규격 3장의 저장형(`BITPIX=16` + `BZERO=32768`)으로.

    **왜 형까지 맞추나.** converter 는 `BITPIX != 16` 이면 그 자리에서
    `ValueError: Only BITPIX=16 is supported` 로 멈춘다(raw spec 3장). 시뮬이
    float32 로 쓰면 산출물이 **converter 에 한 번도 들어가 볼 수 없어서**,
    크기 말고는 아무것도 시험할 수 없다.  픽셀값이 더미라도 저장형을 맞춰
    두면 변환 경로를 끝까지 돌려 볼 수 있다.

    astropy 는 `uint16` 배열에 `BZERO=32768` · `BSCALE=1` 을 자동으로 붙인다.

    ⚠️ 크기는 `fits_shape` 설정값이다 -- 실물(19200×9400)은 `spec` 으로 켠다.
    """
    try:
        import numpy as np
    except ImportError:                      # pragma: no cover
        return data
    if getattr(data, 'dtype', None) is not None and data.dtype.kind == 'u':
        return data
    # bias level 1000 근처의 더미이므로 클리핑으로 잃는 값이 없다.
    return np.clip(data, 0, 65535).astype(np.uint16)


def apply_cards(hdr, cards) -> None:  # noqa: ANN001
    """`rawcards.render()` 카드 목록을 **순서 그대로** FITS 헤더에 얹는다.

    문자열 값은 템플릿 폭까지 패딩된 채로 온다 -- astropy 는 넘겨준 문자열의
    꼬리 공백을 보존하므로 카드 이미지가 견본과 바이트 단위로 같아진다.
    `COMMENT` 는 블록 구분 카드로 그 자리에 삽입한다.

    폭이 모자라는 카드는 `_fit_to_card()` 가 규격 5.0절대로 다듬는다 --
    comment 를 먼저 자르고, 값은 마지막에 자르며 경고를 남긴다.
    """
    from astropy.io import fits
    for key, value, comment in cards:
        try:
            if key == 'COMMENT':
                hdr.append(fits.Card('COMMENT', value), end=True)
            else:
                if isinstance(value, str):
                    value, comment = _fit_to_card(key, value, comment)
                hdr.append(fits.Card(key, value, comment), end=True)
        except Exception as exc:  # 헤더 하나 때문에 노출을 망치지 않는다
            log.error('header %s=%r rejected: %s', key, value, exc)


def _apply_header(hdr, values: dict) -> None:  # noqa: ANN001
    """딕셔너리 헤더 (하위 호환 -- 템플릿을 거치지 않는 시험·도구용).

    숫자로 보이면 숫자로, 아니면 문자열로 넣는다.  8자 넘는 키는 HIERARCH.
    """
    for key, raw in values.items():
        val: object = raw
        if isinstance(raw, FitsStr):
            val = str(raw)          # 문자열 강제 -- 숫자 변환을 건너뛴다
        elif isinstance(raw, str):
            token = raw.strip()
            try:
                val = int(token)
            except ValueError:
                try:
                    val = float(token)
                except ValueError:
                    val = token
        try:
            if len(key) > _MAX_KEY:
                hdr[f'HIERARCH {key}'] = val
            else:
                hdr[key] = val
        except Exception as exc:  # 헤더 하나 때문에 노출을 망치지 않는다
            log.debug('header %s=%r rejected: %s', key, raw, exc)

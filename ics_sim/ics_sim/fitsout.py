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
    """
    from astropy.io import fits
    for key, value, comment in cards:
        try:
            if key == 'COMMENT':
                hdr.append(fits.Card('COMMENT', value), end=True)
            else:
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional FITS output.

지금은 더미 배열을 쓰지만 **헤더 생성 경로는 처음부터 실제와 같게** 만든다.
다음 단계에서 백엔드의 fetch_image() 가 실제 픽셀을 돌려주면 그대로 저장된다.

레거시 헤더의 출처는 AUX/TCS 텔레메트리다 -- ICS 가 TC 에 질의해 각 IC 에
중계하고, IC 가 저장 시 헤더에 박는다(ics_legacy_report 5.3절).  telemetry.py 의
header_dict() 가 그 딕셔너리를 만든다.  없는 필드는 sentinel(0 / NC)로 채워
"값이 없다"는 사실이 헤더에 남게 한다.

mef_fits_spec/ 의 KMT-CEU 키워드 규격과의 정합은 실기 단계에서 붙인다.  지금은
레거시 헤더 재현까지가 목표다.
"""

from __future__ import annotations

import logging
import os
import time

log = logging.getLogger('ics_sim.fits')

#: FITS 헤더 키워드는 8자 이하여야 한다.  긴 이름은 HIERARCH 로 넘긴다.
_MAX_KEY = 8


class FitsStr(str):
    """**문자열로 강제**할 헤더값.  숫자처럼 보여도 숫자로 바꾸지 않는다.

    `_apply_header` 는 텔레메트리를 와이어에서 받은 `key=value` 문자열로 다루기
    때문에 숫자로 보이는 값을 숫자로 바꾼다 -- `EQUINOX='2000.000'` 이 실수로
    들어가야 하므로 그 동작이 맞다.  그런데 **식별자에는 그게 재앙이다**:
    `EXPID='20260811.000001'` 은 규격 5.2절이 문자열로 정의한 값인데 그대로
    두면 float 카드가 되어 자릿수·형이 다 무너진다 (실제로 그렇게 저장됐다).

    그래서 정체성 카드는 이 타입으로 싣는다 -- 호출측 시그니처를 늘리지 않고
    값 자체가 "나는 문자열이다" 를 들고 다니게 하는 방식이다.
    """

    __slots__ = ()


def write_dummy_fits(path: str, data, header: dict) -> int:
    """FITS 파일 하나를 쓰고 전송률(KB/sec)을 돌려준다.

    astropy 가 없거나 data 가 None 이면 0 을 돌려준다 (호출측이 대체 전송률을
    쓴다).  astropy 는 여기서만 import 한다 -- 메시지만 내는 기본 모드에서는
    의존성이 없어야 하기 때문이다.
    """
    if data is None:
        return 0
    try:
        from astropy.io import fits
    except ImportError:
        log.warning('astropy 없음 -- FITS 저장을 건너뜁니다 (%s)', path)
        return 0

    hdu = fits.PrimaryHDU(data=_as_unsigned16(data))
    _apply_header(hdu.header, header)

    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    started = time.monotonic()
    # `CHECKSUM`/`DATASUM` (규격 5.1절 권장, 9장 OI-7).  astropy 가 계산해
    # 넣어 주므로 우리가 만들 이유가 없다.
    hdu.writeto(path, overwrite=True, checksum=True)
    elapsed = max(time.monotonic() - started, 1e-6)

    size_kb = os.path.getsize(path) / 1024.0
    return int(size_kb / elapsed)


def _as_unsigned16(data):  # noqa: ANN001, ANN201
    """더미 픽셀을 규격 3장의 저장형(`BITPIX=16` + `BZERO=32768`)으로.

    **왜 형까지 맞추나.** converter 는 `BITPIX != 16` 이면 그 자리에서
    `ValueError: Only BITPIX=16 is supported` 로 멈춘다(규격 6.1절). 시뮬이
    float32 로 쓰면 산출물이 **converter 에 한 번도 들어가 볼 수 없어서**,
    크기 말고는 아무것도 시험할 수 없다.  픽셀값이 더미라도 저장형을 맞춰
    두면 변환 경로를 끝까지 돌려 볼 수 있다.

    astropy 는 `uint16` 배열에 `BZERO=32768` · `BSCALE=1` 을 자동으로 붙인다 --
    우리가 카드를 만들지 않아도 규격 5.1절 필수 항목이 채워진다.

    ⚠️ 크기는 아직 실물(19200×9400)이 아니다 -- `fits_shape` 설정값이다.
    """
    try:
        import numpy as np
    except ImportError:                      # pragma: no cover
        return data
    # bias level 1000 근처의 더미이므로 클리핑으로 잃는 값이 없다.
    return np.clip(data, 0, 65535).astype(np.uint16)


def _apply_header(hdr, values: dict) -> None:  # noqa: ANN001
    """텔레메트리 딕셔너리를 FITS 헤더로.

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

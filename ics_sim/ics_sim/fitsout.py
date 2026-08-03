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

    hdu = fits.PrimaryHDU(data=data)
    _apply_header(hdu.header, header)

    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    started = time.monotonic()
    hdu.writeto(path, overwrite=True)
    elapsed = max(time.monotonic() - started, 1e-6)

    size_kb = os.path.getsize(path) / 1024.0
    return int(size_kb / elapsed)


def _apply_header(hdr, values: dict) -> None:  # noqa: ANN001
    """텔레메트리 딕셔너리를 FITS 헤더로.

    숫자로 보이면 숫자로, 아니면 문자열로 넣는다.  8자 넘는 키는 HIERARCH.
    """
    for key, raw in values.items():
        val: object = raw
        if isinstance(raw, str):
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

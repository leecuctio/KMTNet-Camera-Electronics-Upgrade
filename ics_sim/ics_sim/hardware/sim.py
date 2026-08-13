#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simulated detector backend.

실제 하드웨어 없이 레거시와 같은 타이밍으로 노출 사이클을 흉내낸다.  모든
소요시간은 [timing]/[readout] 설정값이며 XIS 로그 실측 중앙값에서 왔다.

레거시 프로토콜에 이미 `DataSource=SIM` 이 정의돼 있으므로(DevNote 6.4) 이
백엔드는 자신을 SIM 으로 보고한다.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import AsyncIterator

from .base import BackendError

log = logging.getLogger('ics_sim.hw.sim')


class SimBackend:
    """타이밍만 재현하는 백엔드."""

    name = 'sim'

    def __init__(self, cfg) -> None:  # noqa: ANN001
        self.cfg = cfg
        self._shutter_open = False
        self._led_ms = 0

    # -- 준비 -------------------------------------------------------------

    async def initialize(self, ccd: str, suffix: str) -> None:
        if self.cfg.behavior.injecting('init_fail') and ccd == self.cfg.node.master:
            raise BackendError('Failed to initialize one or more ICs', ccd=ccd)
        await asyncio.sleep(self.cfg.scaled(self.cfg.timing.initialize_ack))

    async def erase(self, ccd: str) -> None:
        await asyncio.sleep(self.cfg.scaled(self.cfg.timing.erase_sec))

    # -- 셔터 / LED -------------------------------------------------------

    async def open_shutter(self, seconds: float) -> None:
        if self.cfg.behavior.injecting('shopen_corrupt'):
            # 레거시 실측: SHOPEN 60 OBS USESTATUS 가 "N 60 .." 로 깨져
            # K.IC 가 거부 -> 셔터가 열리지 않은 노출이 됐다 (DevNote 5.3).
            raise BackendError("Didn't understand N 60 OBS USESTATUS ?")
        await asyncio.sleep(self.cfg.scaled(self.cfg.timing.shutter_open_delay))
        self._shutter_open = True

    async def close_shutter(self) -> None:
        self._shutter_open = False

    async def flash_led(self, milliseconds: int) -> None:
        self._led_ms = milliseconds

    # -- readout ----------------------------------------------------------

    async def readout(self, ccd: str) -> AsyncIterator[int]:
        """[readout] 설정대로 진행률을 흘려보낸다.

        실측: 6 -> 17 -> 28 -> ... -> 94 를 3.37초 간격으로, 그 다음 100.
        """
        if self.cfg.behavior.injecting('dma_timeout') and ccd == self.cfg.node.master:
            raise BackendError('DMA WAIT TIMEOUT. EXPOSURES ABORTED.', ccd=ccd)
        r = self.cfg.readout
        tick = self.cfg.scaled(r.pctread_tick)
        for pct in r.steps():
            await asyncio.sleep(tick)
            yield pct
        await asyncio.sleep(tick / 2)
        yield r.pctread_final

    async def fetch_image(self, ccd: str):  # noqa: ANN201
        """더미 이미지.  numpy 가 없으면 None (메시지만 내는 모드)."""
        if not self.cfg.paths.write_fits:
            return None
        try:
            import numpy as np
        except ImportError:
            log.warning('numpy 없음 -- FITS 생성을 건너뜁니다')
            return None
        rows, cols = self.cfg.paths.fits_shape
        rng = np.random.default_rng(abs(hash(ccd)) % (2 ** 32))
        # bias level + read noise + 약한 배경
        img = rng.normal(1000.0, 8.0, size=(rows, cols))
        return img.astype('float32')

    async def write_frame(self, controller: str, chips: tuple[str, ...],
                          path: str, header: dict) -> int:
        """컨트롤러 1대분을 파일 하나로 저장.  전송률(KB/sec)을 돌려준다.

        **chip 2개를 X 방향으로 이어 붙인다** -- 실기 raw 가 그렇다(MK 파일의
        X 1–9600 이 M, 9601–19200 이 K).  시뮬은 `fits_shape` 크기의 더미를
        chip 마다 만들어 가로로 붙이므로 폭이 2배가 된다.  실물 크기
        (19200×9400, 파일당 344 MiB)는 쓰지 않는다 -- 구조만 맞춘다.

        `write_fits=false` 면 실제로 쓰지 않고 그럴듯한 전송률만 돌려준다 --
        레거시 로그의 RATE= 값 범위(수십만~백만 KB/sec)에 맞춘다.
        """
        if self.cfg.paths.write_fits:
            from ..fitsout import write_dummy_fits
            halves = [await self.fetch_image(c) for c in chips]
            data = _join_x(halves)
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            written = write_dummy_fits(path, data, header)
            if written:
                return written
        # 실측 RATE 범위에서 컨트롤러마다 조금씩 다른 값
        return 1_030_000 + (abs(hash(controller)) % 60_000)

    # -- 상태 -------------------------------------------------------------

    def status(self, ccd: str) -> dict:
        return {
            'driving': 1,
            'fibers': True,
            'synched': True,
            'datasource': 'SIM',
            'shutter_open': self._shutter_open,
            'led_ms': self._led_ms,
        }


def _join_x(halves: list) -> object | None:
    """chip 절반들을 X 방향으로 이어 붙인다 (실기 raw 의 배치).

    하나라도 None 이면(numpy 없음 · write_fits=false) None 을 돌려 호출측이
    "쓰지 않음" 으로 처리하게 한다.
    """
    if not halves or any(h is None for h in halves):
        return None
    if len(halves) == 1:
        return halves[0]
    import numpy as np
    return np.concatenate(halves, axis=1)

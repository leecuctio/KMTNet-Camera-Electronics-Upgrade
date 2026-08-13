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

    # -- FITS 헤더용 컨트롤러 사실 (규격 5.5·5.6·5.10절) ------------------
    #
    # **시뮬 값임이 헤더에 남는다.**  `DATASRC='SIM'` 이 그 표시이고
    # (`rawhdr.datasrc_of`), 여기서 돌려주는 값들은 그 카드가 있는 한 실측으로
    # 오인될 수 없다.  값은 레거시 실측 헤더의 범위에서 가져와 형식만 맞춘다.

    def controller_info(self, controller: str) -> dict:
        tag = controller.upper()
        idx = 1 if tag == 'MK' else 2
        return {
            # 색인형 -- 양쪽 파일에서 같은 값이어야 한다 (규격 5.11절).
            # 그래서 `controller` 에 의존하지 않고 고정 목록을 돌려준다.
            'units': (
                {'id': 'ARCHON-SIM-1', 'sn': 'SIM0001', 'fw': 'SIM-fw-0.0'},
                {'id': 'ARCHON-SIM-2', 'sn': 'SIM0002', 'fw': 'SIM-fw-0.0'},
            ),
            'status': 'OK',
            'errorflag': 0,
            'boardtemp': 28.0 + idx * 0.4,
            'readtime': round(self.cfg.readout.pctread_tick
                              * len(tuple(self.cfg.readout.steps())), 2),
            'acffile': 'kmtnet_ceu_sim.acf',
            'nphlines': 32,          # 레거시 실측값과 같다
            'frameno': 0,
            'bufno': idx,
        }

    def sensors(self, controller: str, chips: tuple[str, ...]) -> dict:
        # 레거시 실측 헤더(SSO 2017)의 값 범위를 쓴다.  chip 마다 조금 다르게
        # 만들어 CCDTEMP1 != CCDTEMP2 인 경우를 시험할 수 있게 한다.
        base = -103.16
        return {
            'ccdtemp1': round(base - 0.05, 2),
            'ccdtemp2': round(base + 0.05, 2),
            'pt30n1': -151.68, 'pt30n2': -147.39, 'charcoal': -197.79,
            'air_in': 34.98, 'air_out': 31.26,
            'glyc_in': 27.97, 'glyc_out': 29.01,
            # `dewpres` 는 넣지 않는다 -- 레거시도 `'N/A'` 였다.  호출측이
            # sentinel 을 채우는 경로를 실제로 밟게 하려는 것이다.
        }

    def voltages(self, controller: str) -> list[dict]:
        from ..rawhdr import VOLT_NAMES
        setpoints = {'VOD': 26.0, 'VRD': 13.0, 'VOG': -4.0, 'VSS': 0.0,
                     'VDD': 5.0, 'PCLKH': 3.0, 'PCLKL': -8.0,
                     'SCLKH': 5.0, 'SCLKL': -5.0}
        return [{'name': n, 'setpoint': setpoints[n],
                 'measured': round(setpoints[n] + 0.02, 2),
                 'unit': 'V', 'status': 'OK'} for n in VOLT_NAMES]

    def amp_map(self, controller: str) -> dict | None:
        # **배선을 모른다고 말하는 것이 맞다.**  시뮬이 그럴듯한 매핑을
        # 만들어 `AMPMAP='EXPLICIT'` 로 싣으면, 실기에서 실제 배선을 넣는 일이
        # 이미 끝난 것처럼 보인다 (규격 5.5.1절, 변경점 C-11).
        return None

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

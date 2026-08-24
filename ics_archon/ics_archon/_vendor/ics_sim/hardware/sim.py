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

    @property
    def writes_files(self) -> bool:
        """시뮬은 `[paths] write_fits` 를 따른다 (종전과 같다)."""
        return bool(self.cfg.paths.write_fits)

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

    def readout_events(self, ccd: str):  # noqa: ANN201
        """독출을 사건으로 흘려보낸다 (`base.py` 의 선택 훅).

        ⚠️ **간단한 모사다 -- 두 컨트롤러를 실제로 모사하지 않는다** (목 지시
        2026-08-24).  시뮬은 CCD 4개가 다 소프트웨어라 독출 경로에 컨트롤러
        라는 경계가 없고, 그것을 진짜로 만들려면 `[readout]` 모델 자체를
        컨트롤러별로 나눠야 한다 -- 비용이 이득보다 크다는 판단이다.
        **병렬 독출의 실구현은 `ics_archon` 에 있다.**

        그래서 여기서는 진행률을 종전대로 흘려보낸 뒤 **완료 사건만**
        컨트롤러 수만큼 낸다(시차 0).  그것으로 충분한 이유는 이 훅이 있는
        경로를 `ics_sim` 시험도 밟게 하는 것이 목적이기 때문이다 -- 새 분기가
        실기에서 처음 도는 상황을 만들지 않는다.
        """
        from .. import rawpair

        r = self.cfg.readout
        tick = self.cfg.scaled(r.pctread_tick)
        ccds = tuple(self.cfg.node.ccds)

        async def _events():  # noqa: ANN202
            if (self.cfg.behavior.injecting('dma_timeout')
                    and ccd == self.cfg.node.master):
                raise BackendError('DMA WAIT TIMEOUT. EXPOSURES ABORTED.',
                                   ccd=ccd)
            for pct in r.steps():
                await asyncio.sleep(tick)
                yield 'progress', pct
            await asyncio.sleep(tick / 2)
            for tag, chips in rawpair.CONTROLLERS:
                if any(c in ccds for c in chips):
                    yield 'frame', tag

        return _events()

    async def fetch_image(self, ccd: str):  # noqa: ANN201
        """chip 1개분 더미 이미지.  numpy 가 없으면 None (메시지만 내는 모드).

        `fits_shape` 가 **spec 기하**(chip 당 9400×9600, `fits_shape = spec`)면
        raw spec 4장의 배치를 실제로 담은 프레임을 만든다 -- amp tile 별 bias
        offset, X overscan(strip 1–4 오른쪽 · 5–8 왼쪽, `XOSC_PATTERN`), 중앙
        Y overscan 168행.  converter 의 `DATASEC`/`BIASSEC` 절단과 overscan
        통계가 **값으로** 검증 가능해진다.  그 밖의 크기는 구조 없는 노이즈다.
        """
        return self._chip_image(ccd, signal=150.0)

    def _chip_image(self, ccd: str, signal: float):  # noqa: ANN202
        if not self.cfg.paths.write_fits:
            return None
        try:
            import numpy as np
        except ImportError:
            log.warning('numpy 없음 -- FITS 생성을 건너뜁니다')
            return None
        from .. import rawhdr
        rows, cols = self.cfg.paths.fits_shape
        rng = np.random.default_rng(abs(hash(ccd)) % (2 ** 32))
        spec_chip = (rows, cols) == (rawhdr.RAW_NAXIS2,
                                     rawhdr.RAW_NAXIS1 // 2)
        if not spec_chip:
            # bias level + read noise (+ 약한 신호) -- 구조 없는 더미
            img = rng.normal(1000.0 + signal, 8.0, size=(rows, cols))
            return img.astype('float32')

        # raw spec 기하 -- strip 8개 × (TOP/BOT) amp 16개의 타일 구조.
        # active 영역에만 `signal` 을 얹어 overscan 과 통계로 갈라지게 한다.
        # 중앙 168행은 BOT/TOP 몫 84/84 로 나눈다 (OI-4 의 균등 가정 그대로).
        img = np.empty((rows, cols), dtype=np.uint16)
        bot_rows = rawhdr.IMAGEY                       # 1..4616
        top_rows = rows - rawhdr.IMAGEY                # 4785..9400 의 시작
        mid_split = bot_rows + rawhdr.OVRSCNY          # BOT 몫 중앙 84행 끝
        chip_base = 1000.0 + (abs(hash(ccd)) % 8) * 4.0
        for s in range(8):                             # strip 1..8
            x0 = s * rawhdr.AMPNAX1
            tile = rng.normal(0.0, 8.0,
                              size=(rows, rawhdr.AMPNAX1)).astype('float32')
            # amp 별 bias offset -- TOP 과 BOT 이 다르게 (경계 진단용)
            tile[:mid_split] += chip_base + s * 2.0            # BOT amp 몫
            tile[mid_split:] += chip_base + s * 2.0 + 1.0      # TOP amp 몫
            # active 픽셀에만 신호 -- X overscan 열과 중앙 Y overscan 행 제외.
            # XOSC_PATTERN 'RRRRLLLL': strip 1–4 오른쪽 48열, 5–8 왼쪽 48열.
            if rawhdr.XOSC_PATTERN[s] == 'R':
                ax0, ax1 = 0, rawhdr.IMAGEX
            else:
                ax0, ax1 = rawhdr.OVRSCNX, rawhdr.AMPNAX1
            tile[:bot_rows, ax0:ax1] += signal
            tile[top_rows:, ax0:ax1] += signal
            img[:, x0:x0 + rawhdr.AMPNAX1] = np.clip(
                tile, 0, 65535).astype(np.uint16)
        return img

    async def write_frame(self, controller: str, chips: tuple[str, ...],
                          path: str, header) -> int:  # noqa: ANN001
        """컨트롤러 1대분을 파일 하나로 저장.  전송률(KB/sec)을 돌려준다.

        **chip 2개를 X 방향으로 이어 붙인다** -- 실기 raw 가 그렇다(MK 파일의
        X 1–9600 이 M, 9601–19200 이 K).  `fits_shape = spec` 이면 실물 크기
        (19200×9400, 파일당 344 MiB)의 기하 구조 프레임이 되고, 그 밖에는
        `fits_shape` 크기의 더미를 chip 마다 만들어 붙인다 (폭 2배).

        active 신호 크기는 `IMAGETYP` 을 따른다 -- BIAS 는 0 (bias 프레임의
        overscan/active 가 통계적으로 같아야 하므로), 나머지는 고정 신호.

        `write_fits=false` 면 실제로 쓰지 않고 그럴듯한 전송률만 돌려준다 --
        레거시 로그의 RATE= 값 범위(수십만~백만 KB/sec)에 맞춘다.
        """
        if self.cfg.paths.write_fits:
            from ..fitsout import write_dummy_fits
            from ..rawcards import value_of
            imgtype = ''
            if isinstance(header, dict):
                imgtype = str(header.get('IMAGETYP', ''))
            else:
                imgtype = str(value_of(header, 'IMAGETYP') or '')
            signal = 0.0 if imgtype.strip().upper() == 'BIAS' else 150.0
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)

            # **스레드로 내보낸다.**  `fits_shape = spec` 이면 프레임 하나가
            # 19200x9400(344 MiB)이고, 그 생성(numpy)과 쓰기(astropy)는 둘 다
            # 블로킹이다 -- 이벤트 루프 안에서 돌리면 그 몇 초 동안 UDP 수신과
            # 다른 CCD 의 발신이 전부 멈춘다.  DevNote 3.3 의 시간 창(획득
            # 1.8초 · IDLE 0.9초 · Wrote 25초)은 그런 정지를 허용하지 않고,
            # 실기 백엔드의 FETCH 도 같은 성질이라 이 구조가 그쪽 선례가 된다.
            def _make_and_write():
                halves = [self._chip_image(c, signal) for c in chips]
                return write_dummy_fits(path, _join_x(halves), header)

            written = await asyncio.to_thread(_make_and_write)
            if written:
                return written
        # 실측 RATE 범위에서 컨트롤러마다 조금씩 다른 값
        return 1_030_000 + (abs(hash(controller)) % 60_000)

    # -- FITS 헤더용 컨트롤러 사실 (raw spec 5.5·5.6절) --------------------
    #
    # **시뮬 값임이 헤더에 남는다.**  `DATASRC='SIM'` 이 그 표시이고
    # (`rawhdr.datasrc_of`), 여기서 돌려주는 값들은 그 카드가 있는 한 실측으로
    # 오인될 수 없다.  값은 견본 헤더 v1.0 의 범위에서 가져와 형식만 맞춘다.

    def controller_info(self, controller: str) -> dict:
        return {
            # 색인형 -- 양쪽 파일에서 같은 값이어야 한다 (raw spec 5.9절).
            # 그래서 `controller` 에 의존하지 않고 고정 목록을 돌려준다.
            # 실기 값은 `[controllers]` ini 가 이 목록을 덮는다 (ICS INI 카드).
            'units': (
                {'id': 'ARCHON-SIM-1', 'sn': 'SIM0001',
                 'cfg': 'KMT_SIM_101_R0000.0'},
                {'id': 'ARCHON-SIM-2', 'sn': 'SIM0002',
                 'cfg': 'KMT_SIM_102_R0000.0'},
            ),
        }

    def controller_telemetry(self) -> list[dict]:
        # 견본 헤더 v1.0 의 표본값 그대로 -- 전압/전류 자리는
        # `rawhdr.VOLT_RAILS`(P2V5 P5V P6V N6V P17V N17V P35V) 순서다.
        return [
            {'temp': [40.1, 41.2, 42.3, 43.4, 44.5, 45.6, 46.7, 47.8,
                      48.9, 49.0],
             'volt': [2.512, 5.023, 5.834, -5.945, 16.956, -17.067, 35.089],
             'curr': [4.698, 4.487, 2.176, 0.465, 0.454, 0.443, 0.032]},
            {'temp': [40.9, 49.8, 48.7, 47.6, 46.5, 45.4, 44.3, 43.2,
                      42.1, 41.0],
             'volt': [2.498, 5.087, 5.876, -5.965, 16.954, -17.043, 35.032],
             'curr': [4.712, 4.423, 2.134, 0.445, 0.456, 0.467, 0.078]},
        ]

    def sensors(self, controller: str, chips: tuple[str, ...]) -> dict:
        # 레거시 실측 헤더(SSO 2017)와 견본 v1.0 의 값 범위를 쓴다.
        # chip 마다 조금 다르게 만들어 대표 센서(ccdtemp1 -> CCDTEMP)와 이웃
        # 센서(ccdtemp2, 진단용)가 구분되는지 시험할 수 있게 한다.
        base = -103.16
        return {
            'ccdtemp1': round(base - 0.05, 2),
            'ccdtemp2': round(base + 0.05, 2),
            'dmptemp': -122.34,
            'pt30n1': -151.68, 'pt30n2': -147.39, 'charcoal': -197.79,
            'wallbrd': 16.78, 'hebox': 33.21,
            'air_in': 34.98, 'air_out': 31.26,
            'glyc_in': 27.97, 'glyc_out': 29.01,
            'fsatemp': 23.4, 'fsahum': 12.3,       # Tapaculo (raw spec 5.8절)
            # `dewpres` 는 넣지 않는다 -- 레거시도 `'N/A'` 였다.  호출측이
            # sentinel 을 채우는 경로를 실제로 밟게 하려는 것이다.
        }

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

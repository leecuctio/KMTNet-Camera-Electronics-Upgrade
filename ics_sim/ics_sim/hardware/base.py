#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detector backend contract.

**이 계약이 다음 단계로 가는 통로다.**  지금은 시뮬이지만 곧 실제 CCD 를 구동해
영상을 얻고 FITS 로 저장한다.  시퀀서(sequencer.py)는 하드웨어를 직접 만지지
않고 오직 이 인터페이스만 호출하므로, 실기로 넘어갈 때 시퀀서 코드는 한 줄도
고치지 않는다.  `[hardware] backend = sim | archon` 한 줄로 전환한다.

특히 readout() 이 진행률을 yield 하도록 만든 것이 중요하다.  시뮬에서는
[readout] 설정대로 6 -> 17 -> ... -> 100 을 만들어내고, 실기에서는 컨트롤러가
보고하는 실제 진행률을 그대로 흘려보내면 된다.  PCTREAD 메시지를 만드는 쪽은
어느 쪽이 오는지 알 필요가 없다.

레거시에 이미 `DataSource=SIM` 이라는 값이 정의돼 있다는 점도 참고할 만하다
(*.IC>OBS ERROR: Invalid selection for DataSource. ADC, CTC, and SIM are valid.
-- DevNote 6.4).  시뮬 백엔드를 DATASOURCE SIM 으로 노출하면 프로토콜상으로도
자연스럽다.
"""

from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class DetectorBackend(Protocol):
    """CCD 4대 + 셔터 + LED 를 다루는 최소 계약."""

    name: str

    async def initialize(self, ccd: str, suffix: str) -> None:
        """다음 노출의 파일명 suffix 를 설정하고 컨트롤러를 준비한다."""

    async def erase(self, ccd: str) -> None:
        """CCD flushing.  레거시는 master(K)에서만 수행했다."""

    async def open_shutter(self, seconds: float) -> None:
        """셔터를 seconds 동안 연다.  반환은 즉시 -- 대기는 시퀀서가 한다."""

    async def close_shutter(self) -> None:
        """셔터를 즉시 닫는다 (강제 중단 포함)."""

    async def flash_led(self, milliseconds: int) -> None:
        """점검용 LED 프로젝터를 점등한다 (FLASHNOW)."""

    def readout(self, ccd: str) -> AsyncIterator[int]:
        """readout 을 시작하고 진행률(0~100)을 yield 한다.

        마지막으로 100 을 내보내야 한다.  시퀀서는 이 값으로 PCTREAD 메시지를
        만든다.
        """
        ...

    async def fetch_image(self, ccd: str):
        """읽어낸 픽셀 배열.  FITS 를 쓰지 않을 때는 None 을 돌려도 된다."""

    async def write_fits(self, ccd: str, path: str, header: dict) -> int:
        """FITS 로 저장하고 전송률(KB/sec)을 돌려준다."""

    def status(self, ccd: str) -> dict:
        """STATUS 명령 응답에 쓸 값들 (Driving, fibers, build 등)."""


class BackendError(Exception):
    """하드웨어 계층에서 올라오는 오류.

    시퀀서는 이걸 잡아 레거시와 같은 ERROR 메시지로 바꾼다:
        ICS>OBS ERROR: Failed to initialize one or more ICs
        ICS>OBS ERROR: Failed to Start acquisition on one or more ICs
        G.IC>ABC ERROR: GO  DMA WAIT TIMEOUT. EXPOSURES ABORTED.
    """

    def __init__(self, message: str, *, ccd: str = '') -> None:
        super().__init__(message)
        self.ccd = ccd

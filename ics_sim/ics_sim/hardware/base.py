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

    async def write_frame(self, controller: str, chips: tuple[str, ...],
                          path: str, header: dict) -> int:
        """컨트롤러 1대분 프레임을 FITS 파일 **하나**로 저장, 전송률(KB/sec) 반환.

        **개정됨 (D-012, 2026-08-11).** 종전 시그니처는 `write_fits(ccd, …)` 로
        CCD 단위였다 -- 그 형태로는 실기의 저장 단위를 표현할 수 없다.  노출
        1회가 만드는 물리 파일은 **컨트롤러당 1개, 즉 MK/NT 2개**이고 각 파일이
        chip 2개분 픽셀을 담는다 (raw_fits_spec 2.3·2.5절, ICD v4.1 2.1·3절).

        통보(`Wrote`)는 여전히 **CCD 단위 4회**다 -- 그 분리는 시퀀서가 하고
        백엔드는 관여하지 않는다 (D-010).

        Args:
            controller: `MK` 또는 `NT` (규격 5.2 `CTRLTAG`).
            chips: 이 파일이 담는 chip, **X 낮은 쪽부터** (`CHIP1`, `CHIP2`).
            path: 실제로 쓸 경로.  파일명 fail-safe 가 이미 적용된 값이므로
                백엔드는 다시 바꾸지 않는다.
            header: 규격 5장 헤더.  `FILENAME` 은 `path` 의 basename 과 같다.
        """

    def status(self, ccd: str) -> dict:
        """STATUS 명령 응답에 쓸 값들 (Driving, fibers, build 등)."""

    # -- FITS 헤더용 컨트롤러 사실 (규격 5.5·5.6·5.10절) ------------------
    #
    # **왜 텔레메트리 중계가 아니라 백엔드인가.**  레거시 raw 헤더에서 듀어
    # 온도(`CCDTEMP` `PT30N1` `CHARCOAL` `GLYC_IN` …)는 `ENS7` **뒤에** 있고
    # AUX 텔레메트리 필드 집합에는 없다 -- 각 IC 가 자기 듀어 RTD 를 직접
    # 읽었다는 뜻이다.  신규는 Archon 이 그 센서를 읽으므로 값의 출처가
    # TC 중계(`telemetry.py`)가 아니라 이쪽이다 (D-013).

    def controller_info(self, controller: str) -> dict:
        """컨트롤러 정체 + 런타임 상태 (규격 5.5·5.5.0절).

        Returns:
            `units`: 색인 순서(`1`=MK, `2`=NT)의 `{'id','sn','fw'}` 목록.
                **양쪽 파일에 같은 값이 실린다** -- converter 가 MK 헤더만
                읽으면서 두 대분 정체를 요구하기 때문이다(`v2_1.py:411-416`).
            나머지 키(`status` `errorflag` `boardtemp` `readtime` `acffile`
                `nphlines` `frameno` `bufno`): **이 컨트롤러의** 런타임 상태.
                노출마다 두 대가 실제로 다르므로 색인형으로 복제하지 않는다.
        """

    def sensors(self, controller: str, chips: tuple[str, ...]) -> dict:
        """chip 온도 + 듀어 센서 (규격 5.10절).

        키는 소문자: `ccdtemp1` `ccdtemp2` `dewpres` `dmptemp` `pt30n1`
        `pt30n2` `charcoal` `wallbrd` `hebox` `air_in` `air_out` `glyc_in`
        `glyc_out`.  읽지 못한 항목은 **넣지 않는다** -- 호출측이 sentinel 로
        채운다.  `dewpres` 만 sentinel 이 다르다: 실수 `-999.0` 이 아니라
        문자열 `'9.99e-9'` 이고, 읽혔더라도 `0`·음수·범위 밖이면 같은 값으로
        떨어진다 (`rawhdr.format_dewpres`).  단위는 [torr].

        **`ccdtemp1` 이 FITS `CCDTEMP` 의 실측 원천이다** (운영자 확정
        2026-08-21 -- 평균 파생 폐기).  `ccdtemp2` 는 진단·로그용으로만 남고
        raw 카드가 아니다.  백엔드가 `ccdtemp` 를 따로 줘도 호출측이 무시한다
        -- 대표 센서와 어긋날 수 있는 두 번째 사실을 만들지 않는다.
        """

    def voltages(self, controller: str) -> list[dict]:
        """bias/clock 전압 telemetry (규격 5.6절).

        각 항목은 `{'name','setpoint','measured','unit','status'}`.
        `measured` 를 넣지 않으면 `VMEA<n>=-999.0` · `VOLTSTAT=PARTIAL` 이 된다.
        """

    def amp_map(self, controller: str) -> dict | None:
        """raw-local amp 번호 -> `(module, channel)` 실제 배선 (규격 5.5.1절).

        `None` 이면 `AMPMAP='DEFAULT'` 로 **converter 의 추정식을 쓰겠다고
        선언한다.**  배선이 추정과 다르면 crosstalk 보정이 엉뚱한 amp 묶음에
        적용되므로, 아는 순간 실제 값을 돌려줘야 한다.
        """


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

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

    #: **이 백엔드가 실제로 파일을 쓰는가.**  D-016 이름 충돌 선검사를 할지
    #: 여기서 정한다 -- 종전에는 `[paths] write_fits` 를 게이트로 썼는데 그
    #: 플래그의 뜻은 "시뮬이 더미 FITS 를 만드는가" 다.  실기 백엔드는 그 값과
    #: 무관하게 항상 쓰므로, 게이트가 그쪽에 묶여 있으면 `write_fits=false` 로
    #: 실기를 돌릴 때 **선검사가 꺼진 채 실파일이 나간다** (2026-08-23 실측).
    #: 속성이 없으면 시퀀서가 종전대로 `write_fits` 를 본다.
    writes_files: bool

    async def initialize(self, ccd: str, suffix: str) -> None:
        """다음 노출의 파일명 suffix 를 설정하고 컨트롤러를 준비한다."""

    async def erase(self, ccd: str) -> None:
        """CCD flushing.  레거시는 master(K)에서만 수행했다."""

    async def begin_exposure(self, seconds: float,
                             opens_shutter: bool) -> None:
        """노출 개시 통보 (**선택** -- 없으면 시퀀서가 건너뛴다).

        `open_shutter()` 는 셔터를 여는 노출에만 불린다.  DARK/BIAS 는 시퀀서가
        직접 카운트다운하고 백엔드를 부르지 않으므로, **적분 시간을 백엔드에
        알려 줄 자리가 없었다** -- 컨트롤러가 적분을 재는 하드웨어(Archon 의
        `IntMS`)에서는 그것이 곧 "적분을 호스트가 잰다" 가 되고, 헤더
        `EXPTIME` 은 요청값이라 실제와 조용히 어긋난다 (2026-08-24 확정).

        시뮬은 이 메서드를 두지 않는다 -- 타이밍만 흉내내므로 알 필요가 없다.
        """

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

    def readout_events(self, ccd: str):
        """독출을 **사건으로** 흘려보낸다 (**선택** -- 없으면 `readout()`).

        `('progress', pct)` 와 `('frame', ctrltag)` 를 yield 하는 비동기
        이터레이터를 돌려준다.  `None` 을 돌려주면 시퀀서가 종전 경로
        (`readout()`)로 떨어지므로, 이 훅이 없는 백엔드는 아무것도 바뀌지
        않는다.

        **왜 훅인가.**  `readout()` 은 진행률 정수만 흘려보내므로 "어느
        컨트롤러가 끝났나" 를 표현할 자리가 없다.  시뮬은 CCD 4개가 다
        소프트웨어라 그 구분이 없었지만 실기는 컨트롤러가 **물리적으로 둘**
        이고, 그래서 `Acquisition Complete.` 를 프레임별로 내려면 이 경계가
        계약에 있어야 한다 (목 지시 2026-08-24, DevNote 11.25/11.26).

        ⚠️ **`('frame', …)` 이 곧 발신은 아니다.**  프레임별로 내보낼지는
        `[readout] acq_per_frame` 이 정하고 기본은 꺼짐이다 -- 켜면 4개의
        산포가 두 컨트롤러의 실제 시차가 되어 1.8초 창(DevNote 3.3)의 구조적
        보장이 없어진다.  꺼져 있어도 시퀀서는 이 훅을 써서 **모든 컨트롤러의
        완료를 기다린다** (master 만 기다리던 것이 F1 이었다).
        """

    async def fetch_image(self, ccd: str):
        """읽어낸 픽셀 배열.  FITS 를 쓰지 않을 때는 None 을 돌려도 된다."""

    async def write_frame(self, controller: str, chips: tuple[str, ...],
                          path: str, header: dict) -> int:
        """컨트롤러 1대분 프레임을 FITS 파일 **하나**로 저장, 전송률(KB/sec) 반환.

        **개정됨 (D-012, 2026-08-11).** 종전 시그니처는 `write_fits(ccd, …)` 로
        CCD 단위였다 -- 그 형태로는 실기의 저장 단위를 표현할 수 없다.  노출
        1회가 만드는 물리 파일은 **컨트롤러당 1개, 즉 MK/NT 2개**이고 각 파일이
        chip 2개분 픽셀을 담는다 (raw spec 2.1절, D-010, ICD v4.1 2.1·3절).

        통보(`Wrote`)는 여전히 **CCD 단위 4회**다 -- 그 분리는 시퀀서가 하고
        백엔드는 관여하지 않는다 (D-010).

        Args:
            controller: `MK` 또는 `NT`.
            chips: 이 파일이 담는 chip, **X 낮은 쪽부터** (raw spec 4.1절).
            path: 실제로 쓸 경로.  충돌 번호 증가(D-016)가 이미 적용된
                값이므로 백엔드는 다시 바꾸지 않는다.
            header: raw spec 5장 헤더 -- `rawcards.render()` 의 순서 있는
                카드 목록.  `FILENAME` 은 `path` 의 basename 과 같다.
        """

    def status(self, ccd: str) -> dict:
        """STATUS 명령 응답에 쓸 값들 (Driving, fibers, build 등)."""

    # -- FITS 헤더용 컨트롤러 사실 (raw spec 5.5·5.6절) --------------------
    #
    # **왜 텔레메트리 중계가 아니라 백엔드인가.**  레거시 raw 헤더에서 듀어
    # 온도(`CCDTEMP` `PT30N1` `CHARCOAL` `GLYC_IN` …)는 `ENS7` **뒤에** 있고
    # AUX 텔레메트리 필드 집합에는 없다 -- 각 IC 가 자기 듀어 RTD 를 직접
    # 읽었다는 뜻이다.  신규는 Archon 계통이 그 센서를 읽으므로 값의 출처가
    # TC 중계(`telemetry.py`)가 아니라 이쪽이다 (D-013).
    #
    # 구판 계약의 `voltages()`(전압 색인 카드) · `amp_map()`(`AMPMAP`/`AMOD*`)
    # 은 **폐지됐다** -- 해당 카드가 v1.3 미기재다 (raw spec 5.10절).  전압·
    # 전류·온도 텔레메트리는 `controller_telemetry()` 의 `Cn_*` 나열 카드로
    # 재편됐고, 배선은 `CHMAP_*`(rawhdr 상수) + 4.5절 amp 전수 표가 담당한다.

    def controller_info(self, controller: str) -> dict:
        """컨트롤러 정체 (raw spec 5.5절).

        Returns:
            `units`: 색인 순서(`1`=MK, `2`=NT)의 `{'id','sn','cfg'}` 목록.
                `cfg` 는 적용된 Archon 설정 파일명(`CTRLnCFG`) -- 타이밍·
                바이어스·클럭 버전 문자열은 전부 이 파일로 귀속된다.
                **양쪽 파일에 같은 값이 실린다** -- converter 가 MK 헤더만
                읽으면서 두 대분 정체를 요구하기 때문이다.  `[controllers]`
                ini 가 채워져 있으면 이 값을 **덮는다** (ICS INI 카드).
                실기 원천: 시리얼은 SYSTEM 의 `BACKPLANE_ID`, 설정 파일명은
                호스트가 관리한다 (컨트롤러는 ACF 이름을 보고하지 않는다 --
                Archon 매뉴얼 p.54).
        """

    def controller_telemetry(self) -> list[dict]:
        """컨트롤러별 온도/전압/전류 나열 -- FITS `Cn_TEMP`/`Cn_VOLT`/`Cn_CURR`
        (raw spec 5.6절).

        색인 순서(`1`=MK, `2`=NT)의 `{'temp': [...], 'volt': [...],
        'curr': [...]}` 목록.  **양쪽 파일에 두 대분을 같은 값으로 싣는다**
        (5.9절 "반드시 동일") -- 그래서 컨트롤러 인자가 없다.

        실기 원천은 Archon STATUS 다 (매뉴얼 p.47-49): `temp` 는
        `BACKPLANE_TEMP` + `MODm/TEMP`, `volt`/`curr` 는 전원 레일
        `P2V5`/`P5V`/`P6V`/`N6V`/`P17V`/`N17V`/`P35V` 의 `_V`/`_I` 쌍 --
        자리 순서는 `rawhdr.VOLT_RAILS`.  모듈 나열 순서 명세는 규격 수록
        예정이다 (통합 문서 §1).
        """

    def sensors(self, controller: str, chips: tuple[str, ...]) -> dict:
        """chip 온도 + 듀어·환경 센서 (raw spec 5.6절 + 5.8절 Tapaculo 2장).

        키는 소문자: `ccdtemp1` `ccdtemp2` `dewpres` `dmptemp` `pt30n1`
        `pt30n2` `charcoal` `wallbrd` `hebox` `air_in` `air_out` `glyc_in`
        `glyc_out` `fsatemp` `fsahum`.  공급 3계통(ICG RTD / standalone RTD /
        Tapaculo)은 raw spec 5.6절 표 참조 -- `hebox`/`fsatemp`/`fsahum` 이
        Tapaculo 다.  읽지 못한 항목은 **넣지 않는다** -- 호출측이 sentinel
        (`'-999.99'`, `dewpres` 만 `'9.99e-9'`)로 채운다.

        **`ccdtemp1` 이 FITS `CCDTEMP` 의 실측 원천이다** (운영자 확정
        2026-08-21 -- 평균 파생 폐기).  `ccdtemp2` 는 진단·로그용으로만 남고
        raw 카드가 아니다.  백엔드가 `ccdtemp` 를 따로 줘도 호출측이 무시한다
        -- 대표 센서와 어긋날 수 있는 두 번째 사실을 만들지 않는다.
        NT 파일의 대표 센서 귀속은 확인 항목이다 (OI-18).
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STA Archon detector backend -- 실제 CCD 구동이 들어갈 자리.

**현재는 스텁이다.**  다음 단계에서 여기에 실제 컨트롤러 제어 코드를 넣으면
시퀀서·명령 처리부·메시지 규약은 한 줄도 고치지 않고 실기로 넘어간다.
`[hardware] backend = archon` 으로 전환한다.

이미 저장소에 있는 자산:
  * `cam_char/archon/archon_kmtnet_labtest_v2.py`
        Archon 텍스트/바이너리 프로토콜로 노출·FETCH 까지 하는 실동작 스크립트.
        여기 있는 명령 시퀀스(POWERON, LOADPARAM, FASTPREPPARAM/RELEASETIMING,
        STATUS/FRAME 폴링, 1 KiB 블록 FETCH)를 그대로 옮겨오면 된다.
  * `cam_char/archon/archon_simulator.py`
        하드웨어 없이 위 스크립트를 시험하는 프로토콜 시뮬레이터.
        이 백엔드를 개발할 때 상대역으로 쓸 수 있다.
  * `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`
        **write_fits() 가 맞춰야 할 1차 산출 규격** -- Archon raw FITS pair.
        2.3 파일명(<SITE> 사이트 코드 prefix, D-011), 2.5 저장/통보 분리,
        5장 헤더 키워드, 변경점 C-8.
  * `mef_converter/` 와 `mef_fits_spec/`
        raw pair -> L0 64-amp MEF 변환기와 그 출력물 규격.  write_fits() 의
        산출물이 아니라 다음 단계의 입력<->출력 관계다.

구현 시 유의할 점:
  * readout() 은 **진행률을 yield** 해야 한다.  Archon 은 FRAME 의 픽셀/라인
    카운터를 폴링해 진행률을 낼 수 있다.  레거시가 6/17/28/... 처럼 듬성듬성
    보고한 것은 IC 구현 사정이고, 신규는 더 촘촘히 보내도 OBSAgent 는 문제없다
    (PCTREAD= 는 2회 이상이면 READ_3 에 도달한다 -- DevNote 3.2).
  * 4개 CCD 를 병렬로 읽되, **4개의 획득 완료가 1.8초 안에** 모여야 한다.
    넘으면 OBSAgent 가 스크립트 관측을 멈춘다 (DevNote 3.3).
  * **저장 단위와 통보 단위가 갈라진다 (D-010/D-011).**  파일은 컨트롤러당
    1개(노출당 MK/NT 2개)를 쓰고, Wrote 통보만 CCD 단위 4회를 레거시 형식의
    논리 이름으로 낸다.  **계약은 이미 개정됐다 (D-012, 2026-08-11)** --
    write_frame(controller, chips, path, header) 를 구현하면 되고, 통보 분리와
    파일명 fail-safe 는 시퀀서가 처리하므로 백엔드는 관여하지 않는다.
    시뮬 백엔드가 같은 계약으로 이미 돌고 있어 참고 구현이 된다 (sim.py).
  * Wrote 4회의 마감은 다음 프레임의 EXPSTATUS=READOUT 발신 전이다
    (~25초 창, raw_fits_spec 2.5 / DevNote 6.1).
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from .base import BackendError

log = logging.getLogger('ics_sim.hw.archon')

_NOT_YET = ('archon 백엔드는 아직 구현 전입니다. '
            'ics_sim/DevNote.md 9장과 cam_char/archon/ 참고.')


class ArchonBackend:
    """실기 백엔드 스텁.  각 메서드에 구현 지침을 주석으로 남겨 둔다."""

    name = 'archon'

    def __init__(self, cfg) -> None:  # noqa: ANN001
        self.cfg = cfg
        log.warning('%s', _NOT_YET)

    async def initialize(self, ccd: str, suffix: str) -> None:
        # TODO: 컨트롤러 연결 확인 + 다음 파일명 suffix 등록.
        #       실패 시 BackendError('Failed to initialize one or more ICs').
        raise BackendError(_NOT_YET, ccd=ccd)

    async def erase(self, ccd: str) -> None:
        # TODO: flushing 파라미터 적용 후 완료까지 대기.
        #       레거시는 master(K) 에서만 수행했고 ~7.24초 걸렸다.
        raise BackendError(_NOT_YET, ccd=ccd)

    async def open_shutter(self, seconds: float) -> None:
        # TODO: AUX 셔터 제어.  KMTNet 은 Full/Half TTL 두 선을 쓴다
        #       (TCSAgent 문서의 AUX remote commands 참고).
        raise BackendError(_NOT_YET)

    async def close_shutter(self) -> None:
        # TODO: 즉시 닫기.  SHCLOSE 강제 중단 경로에서도 불린다.
        raise BackendError(_NOT_YET)

    async def flash_led(self, milliseconds: int) -> None:
        # TODO: 점검용 LED 프로젝터 점등 (FLASHNOW).
        raise BackendError(_NOT_YET)

    async def readout(self, ccd: str) -> AsyncIterator[int]:
        # TODO: readout 시작 후 FRAME 폴링으로 진행률 yield, 마지막에 100.
        raise BackendError(_NOT_YET, ccd=ccd)
        yield 0  # pragma: no cover  (async generator 로 만들기 위한 형식)

    async def fetch_image(self, ccd: str):  # noqa: ANN201
        # TODO: FETCH 로 픽셀 블록을 받아 배열로 조립.
        raise BackendError(_NOT_YET, ccd=ccd)

    async def write_frame(self, controller: str, chips: tuple[str, ...],
                          path: str, header: dict) -> int:
        # TODO: 이 컨트롤러가 읽은 chip 2개분 픽셀을 `path` 에 FITS 파일
        #       **하나**로 저장하고 실제 전송률(KB/sec) 을 돌려준다.
        #       - 픽셀 배치: chips[0] 이 X 낮은 쪽, chips[1] 이 높은 쪽
        #         (raw_fits_spec 4.1절, 5.2 CHIP1/CHIP2).  19200x9400,
        #         BITPIX=16 + BZERO=32768 (규격 3장).
        #       - `header` 에는 규격 5장 카드가 이미 채워져 온다.  여기서
        #         Archon 이 아는 값(CTRLID/CTRLFW/BCKTEMP/READTIME/전압
        #         텔레메트리 5.5·5.6절)을 덧붙인다.
        #       - `FILENAME` 은 이미 `path` 와 맞춰져 있으므로 건드리지 않는다
        #         (파일명 fail-safe 도 시퀀서가 처리했다).
        #       참고 구현은 sim.py 의 같은 메서드, 계약은 base.py (D-012).
        raise BackendError(_NOT_YET, ccd=chips[0] if chips else '')

    # -- FITS 헤더용 컨트롤러 사실 (규격 5.5·5.6·5.10절, D-013) -----------
    #
    # **이 넷이 MEF 의 placeholder 를 없애는 자리다.**  지금 MEF 는 컨트롤러
    # 정체를 `UNKNOWN`, 보드 온도를 `-999.0`, 전압을 `0.0` 으로 채우고 있고
    # (규격 6.3절), 그 원인은 raw 에 그 정보가 없기 때문이다.
    #
    # ⚠️ 스텁이 예외를 던지지 않고 **빈 값을 돌려준다.**  헤더 생성은 노출
    # 경로가 아니라 저장 경로이므로, 여기서 던지면 다른 이유로 실기를 돌려
    # 보는 사람이 저장 단계에서 막힌다.  호출측이 sentinel 로 채우고 그 사실이
    # 헤더에 남는다 (규격 5.0절).

    def controller_info(self, controller: str) -> dict:
        # TODO: STATUS/SYSTEM 응답에서 채운다.
        #       - units: 두 과학 컨트롤러의 ID/시리얼/firmware.  **양쪽 raw
        #         파일에 같은 값을 실어야 한다** -- converter 가 MK 헤더만
        #         읽으면서 CTRL1*/CTRL2* 를 요구한다 (규격 5.5.0절).
        #         시리얼은 SYSTEM 의 BACKPLANE_ID, firmware 는 BACKPLANE_VERSION.
        #       - boardtemp: STATUS 의 BACKPLANE_TEMP.
        #       - readtime: readout 시작~완료 실측 [s].
        #       - acffile: LOADPARAM 에 쓴 설정 파일 이름.
        #       - nphlines: timing script 의 preheat line 수 (레거시 계승).
        #       - frameno/bufno: FRAME 응답의 BUFnFRAME / 사용 버퍼 번호.
        log.warning('controller_info: %s', _NOT_YET)
        return {'units': ()}

    def sensors(self, controller: str, chips: tuple[str, ...]) -> dict:
        # TODO: Archon HEATER/RTD(ICG) 모듈에서 읽는다.  chips[0] -> ccdtemp1
        #       (= FITS CCDTEMP 의 실측 대표, 운영자 확정 2026-08-21),
        #       chips[1] -> ccdtemp2 (진단·로그용 -- raw 카드가 아니다).
        #       공급 계통이 셋이다 (Header_and_Refs v1.8 3.7절) --
        #       ICG RTD: dewpres/dmptemp/pt30n1/pt30n2/charcoal/wallbrd,
        #       Tapaculo: hebox, standalone RTD readout unit: air_*/glyc_*.
        log.warning('sensors: %s', _NOT_YET)
        return {}

    def voltages(self, controller: str) -> list[dict]:
        # TODO: STATUS 의 bias/clock 채널을 규격 5.6절 9종에 대응시킨다.
        #       측정값을 못 읽은 항목은 `measured` 를 넣지 않는다 -- 그러면
        #       VOLTSTAT 이 PARTIAL 이 되어 사실이 헤더에 남는다.
        log.warning('voltages: %s', _NOT_YET)
        return []

    def amp_map(self, controller: str) -> dict | None:
        # TODO: 설치 시 실제 배선표를 돌려준다 (규격 5.5.1절, 변경점 C-11).
        #       **추정식으로 채우지 말 것** -- 배선이 다르면 crosstalk 보정이
        #       엉뚱한 amp 묶음에 적용되고, 계수 측정 자체가 무의미해진다.
        #       모르는 동안은 None 이 정직한 답이다 (AMPMAP='DEFAULT').
        return None

    def status(self, ccd: str) -> dict:
        return {'driving': 0, 'fibers': False, 'synched': False,
                'datasource': 'ADC', 'shutter_open': False, 'led_ms': 0}

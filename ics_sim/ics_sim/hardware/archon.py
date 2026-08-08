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
  * `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.1.md`
        **write_fits() 가 맞춰야 할 1차 산출 규격** -- Archon raw FITS pair.
        2.3 파일명, 2.5 저장/통보 분리, 5장 헤더 키워드, 변경점 C-8.
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
  * **저장 단위와 통보 단위가 갈라진다 (D-009/D-010).**  파일은 컨트롤러당
    1개(노출당 MK/NT 2개)를 쓰고, Wrote 통보만 CCD 단위 4회를 레거시 형식의
    논리 이름으로 낸다.  현재의 write_fits(ccd, ...) 시그니처는 CCD 단위라
    이 구조를 표현할 수 없다 -- ics_archon 착수 시 개정한다 (DevNote 9.1).
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

    async def write_fits(self, ccd: str, path: str, header: dict) -> int:
        # TODO: raw_fits_spec 규격(2.3 파일명, 5장 헤더)에 맞춰 raw pair 를
        #       저장하고 실제 전송률(KB/sec) 반환.  저장은 컨트롤러 단위
        #       2파일, 통보는 CCD 단위 4회 -- 시그니처 개정 필요 (모듈
        #       docstring 과 DevNote 9.1 의 상기 블록 참고).
        raise BackendError(_NOT_YET, ccd=ccd)

    def status(self, ccd: str) -> dict:
        return {'driving': 0, 'fibers': False, 'synched': False,
                'datasource': 'ADC', 'shutter_open': False, 'led_ms': 0}

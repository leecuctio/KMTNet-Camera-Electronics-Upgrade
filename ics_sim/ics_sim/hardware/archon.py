#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STA Archon detector backend -- **실기 구현은 `ics_archon/` 에 있다.**

> **2026-08-23 이후 이 파일의 처지.**  실제 컨트롤러 제어는
> `ics_archon/ics_archon/archon/backend.py` 가 한다 (`ics_archon` v0.0,
> DevNote 11.23).  **여기에 사본을 두지 않는다** -- raw spec 5장이 개정되면
> 견본 pair 와 `rawcards.py` 가 함께 바뀌고, 그 기계 사본이 이미 둘이라
> (`rawcards.py` · labtest 내장 `RAWCARDS`) 세 번째를 만들면 어긋난 하나를
> 놓친다.
>
> `ics_archon` 은 같은 폴더의 `register_backend('archon', …)` 로 자기 구현을
> 끼운다.  그래서 **아래 스텁은 `ics_archon` 을 거치지 않고 `ics_sim` 을 직접
> `backend = archon` 으로 띄웠을 때만** 만들어진다 -- 그 경우의 안내 역할이다.
> 실기로 돌리려면 `python -m ics_archon` 을 쓴다.

**아래는 스텁이다.**  구현 지침으로서의 가치가 있어 남겨 둔다 -- 메서드마다
값 출처·규격 절·주의사항이 적혀 있고, `ics_archon` 의 백엔드가 이 지침을
따라 쓰였다.

이미 저장소에 있는 자산:
  * `ics_archon/scr_labtest/archon_kmtnet_labtest_v1.3.bigbuf.py` (현행, v1.3.4)
        Archon 텍스트/바이너리 프로토콜로 노출·FETCH·raw spec 헤더까지 하는
        실동작 스크립트 (science = bigbuf 구성.  small buffer 주소 지정은
        같은 폴더의 `…v1.3.smallbuf.py` 가 참고 코드다 -- 그 자체는 science
        스크립트이고, v1.0 원본은 `__ref_archon_control/` 에 있다).  명령
        시퀀스(CLEARCONFIG/WCONFIG, APPLYALL, POWERON, LOADPARAMS, STATUS/FRAME
        폴링, 1 KiB 블록 FETCH)를 그대로 옮겨오면 된다 -- ⚠️ `APPLYALL` 이
        `POWERON` 앞이다 (매뉴얼 p.51, `ics_archon` DevNote 10.2).
        ⚠️ **헤더 산출물 실물은 실기 미검증이다** -- STATUS 필드 이름과 독출
        시간은 2026-09-01 실측으로 닫혔다(368 행/초 · 12.77초 · 주기 13.27초,
        `ics_archon` DevNote 10.4).  옮길 때 잠정 표시를 남긴다
        (`ics_archon/SMC_CLAUDE.md` "ics_archon v0.0").  손볼 자리·경고의
        뜻은 `ics_archon/scr_labtest/README_labtest.md`.
        v1.0 원본과 Archon 매뉴얼 2부는
        `ics_archon/__ref_archon_control/`(읽기 전용) 에 있다.
  * `raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.9.md`
        **write_frame() 이 맞춰야 할 1차 산출 규격** -- Archon raw FITS pair.
        2장 파일명(D-011)·충돌 처리(D-016), 4장 geometry, 5장 헤더 keyword
        (견본 = 초안 헤더 v1.0 pair, 틀은 `ics_sim/rawcards.py`).
  * `mef_converter/` 와 `mef_fits_spec/`
        raw pair -> L0 64-amp MEF 변환기와 그 출력물 규격.  write_frame() 의
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
    (~25초 창, DevNote 3.2·6.1 -- v1.4 에서 규격 2.5절이 삭제되고 `Wrote`
    통보 규약의 정본이 DevNote 로 옮겨졌다: 취득 SW 소관이라서다).
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from .base import BackendError

log = logging.getLogger('ics_sim.hw.archon')

_NOT_YET = ('이 archon 스텁은 실기 구현이 아닙니다 -- 실기는 '
            '`python -m ics_archon` 으로 띄웁니다 '
            '(ics_archon/README.md, DevNote 11.23).')


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
        #         (raw spec 4.1절).  19200x9400, BITPIX=16 + BZERO=32768
        #         (raw spec 3장).
        #       - `header` 에는 규격 5장 카드가 이미 채워져 온다.  여기서
        #         Archon 이 아는 값(CTRLID/CTRLFW/BCKTEMP/READTIME/전압
        #         텔레메트리 5.5·5.6절)을 덧붙인다.
        #       - `FILENAME` 은 이미 `path` 와 맞춰져 있으므로 건드리지 않는다
        #         (파일명 fail-safe 도 시퀀서가 처리했다).
        #       참고 구현은 sim.py 의 같은 메서드, 계약은 base.py (D-012).
        raise BackendError(_NOT_YET, ccd=chips[0] if chips else '')

    # -- FITS 헤더용 컨트롤러 사실 (raw spec 5.5·5.6절, D-013) ------------
    #
    # **이 셋이 MEF 의 placeholder 를 없애는 자리다.**  지금 MEF 는 컨트롤러
    # 정체를 `UNKNOWN`, 텔레메트리를 placeholder 로 채우고 있고, 그 원인은
    # raw 에 그 정보가 없기 때문이다 (MEF `VOLTINFO`/`TELEMETRY` C-후보).
    #
    # ⚠️ 스텁이 예외를 던지지 않고 **빈 값을 돌려준다.**  헤더 생성은 노출
    # 경로가 아니라 저장 경로이므로, 여기서 던지면 다른 이유로 실기를 돌려
    # 보는 사람이 저장 단계에서 막힌다.  호출측이 sentinel 로 채우고 그 사실이
    # 헤더에 남는다 (raw spec 5.0절).

    def controller_info(self, controller: str) -> dict:
        # TODO: SYSTEM 응답 + 호스트 설정에서 채운다 (Archon 매뉴얼 p.46).
        #       - units: 두 과학 컨트롤러의 {'id','sn','cfg'}.  **양쪽 raw
        #         파일에 같은 값을 실어야 한다** (raw spec 5.9절).
        #         시리얼은 SYSTEM 의 BACKPLANE_ID.  cfg(적용 ACF 이름)는
        #         컨트롤러가 보고하지 않으므로 호스트가 관리한다 -- 실운용은
        #         `[controllers]` ini 가 이 값을 덮는다 (ICS INI 카드).
        log.warning('controller_info: %s', _NOT_YET)
        return {'units': ()}

    def controller_telemetry(self) -> list[dict]:
        # TODO: 두 컨트롤러의 STATUS 에서 채운다 (Archon 매뉴얼 p.47-49).
        #       - temp: **자리 순서는 규격 5.6.1절이 정한다**(science 10자리,
        #         rawhdr.TEMP_MOD_LABELS).  그 자리에 넣을 STATUS 필드는
        #         rawhdr.TEMP_MODS -- BACKPLANE_TEMP + MODm/TEMP 대응이며
        #         **규격이 아니라 매뉴얼 p.47-49 근거의 구현 판단**이다.
        #         목록에 없는 모듈(6·7·12)은 자리를 차지하지 않는다.
        #       - volt/curr: 전원 레일 P2V5/P5V/P6V/N6V/P17V/N17V/P35V 의
        #         `_V`/`_I` 쌍, 자리 순서는 rawhdr.VOLT_RAILS (7자리).
        #       읽지 못한 자리는 건너뛰지 말고 rawhdr.FIELD_NC 로 채운다 --
        #       건너뛰면 뒤 항목이 앞으로 당겨져 소비자가 구분할 수 없다.
        #       **양쪽 파일에 두 대분을 같은 값으로** (raw spec 5.9절).
        log.warning('controller_telemetry: %s', _NOT_YET)
        return []

    def sensors(self, controller: str, chips: tuple[str, ...]) -> dict:
        # TODO: 공급 3계통에서 읽는다 (raw spec 5.6절) --
        #       ICG RTD: ccdtemp(= FITS CCDTEMP 실측 대표 -- **chip 귀속
        #         정보는 없다**, 운영자 2026-08-27)/
        #         dewpres/dmptemp/pt30n1/pt30n2/charcoal/wallbrd,
        #       Radionode: hebox/fsatemp/fsahum.
        #       (standalone RTD 계통 air_*/glyc_* 는 카드가 v1.5 에서 폐지됐다
        #        -- 계약에서도 빠졌다, 2026-08-27)
        log.warning('sensors: %s', _NOT_YET)
        return {}

    def status(self, ccd: str) -> dict:
        return {'driving': 0, 'fibers': False, 'synched': False,
                'datasource': 'ADC', 'shutter_open': False, 'led_ms': 0}

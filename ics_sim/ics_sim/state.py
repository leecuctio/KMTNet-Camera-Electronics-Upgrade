#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime state: ICS-level settings and per-CCD channel state.

레거시에서는 ICS 와 4개 IC 가 각자 상태를 들고 SYNCHRONIZE 로 맞췄다.  신규
통합 구조에서는 IcsState 하나가 진실의 원천이고 ChannelState 는 CCD 별로
달라지는 것(파일명, readout 진행률)만 갖는다.

파일명 형식은 바꿀 수 없다.  OBSAgent 가 Wrote 메시지에서 "KMTN" 위치+6 부터
15자를 잘라 FitsNum 으로 쓰기 때문이다 (commands.c 776-784, DevNote 3.2).
    KMTN<ccd 한 글자>.<yyyymmdd 8자>.<nnnnnn 6자>.fits
             ^KMTN+6 부터 15자 = "20250902.057288"

단, 고정인 것은 **Wrote 메시지에 싣는 논리 이름**이다 (D-011/D-010).  실기
(ics_archon)의 디스크 실물은 컨트롤러당 1개 <SITE>.<날짜>.<번호>.<MK|NT>.fits
2개로 저장하고 (<SITE> 는 [node] site 에서 유도한 KMTC/KMTS/KMTA/KMTT,
D-011), 이 논리 이름은 통보 전용이 된다 -- filename() 은 그때 논리 이름
생성기와 물리 경로로 분리된다 (raw_fits_spec 2.3/2.5절, DevNote 9.1/13장 C-16).
시뮬은 레거시 재현이 목적이라 논리 이름 그대로 저장까지 한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone


class ExpStatus:
    """ICS 가 EXPSTATUS= 로 알리는 노출 국면.

    OBSAgent 의 CamStatus 는 이 값들을 문자열로 찾아 전이한다(DevNote 3.2).
    """

    IDLE = 'IDLE'
    INITIALIZING = 'INITIALIZING'
    ERASE = 'ERASE'
    INTEGRATING = 'INTEGRATING'
    READOUT = 'READOUT'
    WRITING = 'WRITING'
    ERROR = 'ERROR'


#: 셔터를 열지 않는 이미지 타입.
NO_SHUTTER = frozenset({'BIAS', 'DARK'})

#: ICS 가 받아들이는 이미지 타입 명령.
IMAGE_TYPES = ('BIAS', 'DARK', 'OBJECT', 'FLAT', 'SKY', 'DOMEFLAT', 'STANDARD')


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def stamp_compact(when: datetime | None = None) -> str:
    """20240303.  파일명 날짜부."""
    return (when or utcnow()).strftime('%Y%m%d')


def stamp_iso(when: datetime | None = None) -> str:
    """2024-03-03T22:23:25.  DATE-OBS 형식 (소수점 없음)."""
    return (when or utcnow()).strftime('%Y-%m-%dT%H:%M:%S')


def stamp_iso_ms(when: datetime | None = None) -> str:
    """2024-03-03T22:23:16.467.  AUXQDATE/TCSQDATE 형식."""
    return (when or utcnow()).strftime('%Y-%m-%dT%H:%M:%S.') + \
        f'{(when or utcnow()).microsecond // 1000:03d}'


def stamp_guide(when: datetime | None = None) -> str:
    """20240303T222316.  가이드 채널 INITIALIZE suffix 형식."""
    return (when or utcnow()).strftime('%Y%m%dT%H%M%S')


@dataclass
class ChannelState:
    """CCD 하나(K/M/T/N)의 상태."""

    ccd: str
    #: 이번 노출의 파일명 suffix -- '20240303.039400'
    suffix: str = ''
    #: 마지막으로 저장한 파일의 전체 경로
    last_file: str = ''
    #: 마지막 readout 진행률
    pctread: int = 0
    #: 광케이블 연결 여부.  STATUS 응답의 +FIBERS / -FIBERS
    fibers: bool = True
    synched: bool = True
    driving: int = 1
    #: DATASOURCE 현재값.  ADC | CT_CORRECTION | SIM  (DevNote 6.4)
    datasource: str = 'CT_CORRECTION'
    ctc_source: str = 'FIRMWARE'
    dmawait: int = 500
    build: str = 'KS2016-01-13:1370'

    def filename(self, data_dir: str) -> str:
        """저장 경로.

        메시지에는 항상 '/' 구분자로 나간다.  레거시가 리눅스 경로
        (/mnt/ICSData/...)를 실었고, OBSAgent 는 "KMTN" 위치를 기준으로
        문자열을 자르므로 구분자 종류에 의존하지는 않지만 형태를 맞춰 둔다.
        """
        joined = os.path.join(data_dir, f'KMTN{self.ccd.lower()}.{self.suffix}.fits')
        return joined.replace(os.sep, '/')

    @property
    def flags(self) -> str:
        """STATUS 응답의 +FIBERS/+SYNCH 플래그 (스펙 2.3절의 상태 플래그)."""
        return ('+FIBERS' if self.fibers else '-FIBERS') + \
               (' +SYNCH' if self.synched else ' -SYNCH')


@dataclass
class IcsState:
    """ICS 레벨 설정 -- 4개 CCD 가 공유한다."""

    imgtype: str = 'OBJECT'
    objname: str = 'test'
    exptime: float = 0.0
    observer: str = 'none'
    projid: str = 'ENG'
    #: 6자리 파일 일련번호.  레거시 IC 는 4자리였고 그 불일치를 INITIALIZE 로
    #: 우회했다(ics_legacy_report 3.4절).  신규는 애초에 6자리로 통일한다.
    expnum: int = 1
    ledflash_ms: int = 0
    expstatus: str = ExpStatus.IDLE
    ics_build: str = 'KX2016-03-23:1381'
    guide_build: str = ''

    #: 현재 노출의 날짜부.  자정을 넘겨도 한 노출 안에서는 고정된다.
    date_part: str = ''
    #: 가이드 채널 INITIALIZE 에 쓴 suffix
    guide_suffix: str = ''
    #: 셔터 개방(또는 논리적 노출 개시) 시각.  TCSSTATUS 의 DATE-OBS 가 된다.
    exp_start: datetime | None = None

    channels: dict[str, ChannelState] = field(default_factory=dict)

    #: 노출 진행 중 여부.  GO 중복 거부(DevNote 6.4)에 쓴다.
    exposing: bool = False

    # -- 채널 -------------------------------------------------------------

    def init_channels(self, ccds: tuple[str, ...]) -> None:
        self.channels = {c: ChannelState(ccd=c) for c in ccds}

    def channel(self, ccd: str) -> ChannelState:
        return self.channels[ccd]

    # -- 파일명 -----------------------------------------------------------

    def next_suffix(self, when: datetime | None = None) -> str:
        """이번 노출의 과학 채널 suffix -- '<yyyymmdd>.<nnnnnn>'.

        정확히 15자여야 한다.  OBSAgent 가 EXPNUM 응답의 Filename= 뒤 15자를
        그대로 잘라 쓰고(DevNote 3.4), Wrote 의 KMTN+6 부터 15자도 이 값이다.
        """
        self.date_part = stamp_compact(when)
        return f'{self.date_part}.{self.expnum:06d}'

    def peek_suffix(self, when: datetime | None = None) -> str:
        """다음 노출의 suffix 를 만들되 상태는 바꾸지 않는다.

        OBSAgent 가 readout 중에 보내는 ExpNum 질의에 답할 때 쓴다.
        """
        return f'{stamp_compact(when)}.{self.expnum:06d}'

    def ics_filename(self, when: datetime | None = None) -> str:
        """FILENAME 명령의 ICS 레벨 응답 -- 'ICS.<iso>.<nnnnnn>'."""
        return f'ICS.{stamp_guide(when)}.{self.expnum:06d}'

    def advance(self) -> None:
        self.expnum += 1

    # -- 설정 요약 --------------------------------------------------------

    def synchronize_body(self) -> str:
        """SYNCHRONIZE 본문.

        레거시는 이 형태의 메시지가 오면 보낸 주체와 무관하게 그대로 반영하는
        수동 리스너였다(ics_legacy_report 3.2절).  신규는 통합 노드라 내부
        동기화가 필요 없지만, 외부 노드(ICG 등)가 질의하면 그대로 답한다.
        """
        return (f'IMGTYPE={self.imgtype} OBJNAME={self.objname} '
                f'EXP={self.exptime:g} OBSERVER={self.observer} '
                f'PROJID={self.projid}')

    @property
    def opens_shutter(self) -> bool:
        return self.imgtype.upper() not in NO_SHUTTER

    @property
    def effective_exptime(self) -> float:
        """BIAS 는 정의상 0초."""
        return 0.0 if self.imgtype.upper() == 'BIAS' else self.exptime


def unique_path(path: str) -> tuple[str, bool]:
    """파일명이 이미 있으면 대체 이름을 만든다.

    레거시 fail-safe (ics_legacy_report 5.5절): 계산된 이름이 존재하면 조용히
    덮어쓰지 않고 '<yymmdd>.<nnn>.fits' 로 저장한 뒤 WARNING 을 낸다.  1999년
    Prospero 시절부터 여러 세대에 걸쳐 검증된 데이터 유실 방지 장치라 신규에서도
    그대로 가져간다.

    Returns:
        (실제로 쓸 경로, 대체되었는지 여부)
    """
    if not os.path.exists(path):
        return path, False
    folder = os.path.dirname(path)
    short = utcnow().strftime('%y%m%d')
    for n in range(1000):
        alt = os.path.join(folder, f'{short}.{n:03d}.fits')
        if not os.path.exists(alt):
            return alt, True
    return path, False

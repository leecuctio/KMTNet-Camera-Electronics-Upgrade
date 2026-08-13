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

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import build_id

log = logging.getLogger('ics_sim.state')


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
    """20240303 -- **순수 UT 날짜**.

    ⚠️ **파일명 `<YYYYMMDD>` 에는 이걸 쓰지 않는다.** 파일명은 사이트별
    **관측일**이고 그건 `rawpair.observing_date()` / `IcsState.obs_date()` 다
    (운영자 확정 2026-08-13, LEECU 협의 후).

    남겨 둔 이유는 UT 날짜 자체가 필요한 자리가 따로 있기 때문이다 -- 로그
    파일명, 진단 출력 같은 것.  파일명 날짜부로 쓰면 CTIO·SAAO 에서 야간 도중에
    날짜가 갈린다.
    """
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
    #:
    #: **재실행에도 되돌아가지 않는다** -- 마지막으로 쓴 번호를 `expnum_file` 에
    #: 적어 두고 기동 시 그 다음 번호부터 시작한다(load_expnum, DevNote 7 `[paths]`).
    expnum: int = 1

    #: 마지막으로 쓴 `expnum` 을 적어 두는 파일 경로.  빈 값이면 지속시키지 않고
    #: 매 실행 1 부터 시작한다(단위 테스트의 기본 동작).
    #:
    #: **`data_dir` 와 무관해야 한다.** 저장 파일을 지우거나 옮겨도 번호는
    #: 되돌아가지 않는 것이 요구사항이다(운영자 확정 2026-08-11) -- 그래서 이
    #: 카운터는 디스크의 파일 목록을 근거로 삼지 않는다.
    expnum_file: str = ''
    ledflash_ms: int = 0
    expstatus: str = ExpStatus.IDLE
    #: 사이트 코드 (`KMTC`/`KMTS`/`KMTA`/`KMTT`).  파일명 `<YYYYMMDD>` 가
    #: **사이트별 관측일** 이므로 날짜를 만들 때마다 필요하다
    #: (`rawpair.observing_date`, 운영자 확정 2026-08-13).
    #:
    #: 상태에 둔 이유: `next_suffix()` 와 `peek_suffix()` 가 **같은 규칙**을
    #: 써야 하는데 호출측이 매번 넘기게 하면 한쪽을 빠뜨린다 -- 그러면 EXPNUM
    #: 응답과 실제 파일명의 날짜가 갈리고, 그건 야간 경계에서만 드러난다.
    site_code: str = 'KMTT'
    #: FITS `ICSBUILD` -- **이 프로그램의** 빌드 식별자 (규격 5.1절).
    #:
    #: 한때 기본값이 레거시 ICS 의 `'KX2016-03-23:1381'` 이었다.  없는 것이
    #: 아니라 **적극적으로 거짓**이었고, `ICSBUILD` 를 둔 목적(헤더 이상을 소스
    #: 상태로 되짚기)을 정면으로 무력화했다 -- 8장 체크리스트가 "비어 있지
    #: 않음" 만 보므로 통과하기까지 했다 (2026-08-13 정정).
    #:
    #: `AUXSTATUS` 중계 꼬리의 `ICSBUILD=` 도 같은 값이다 -- 레거시 ICS 가 거기에
    #: **자기** 빌드를 실었으므로, 다른 프로그램인 우리가 레거시 문자열을 흉내낼
    #: 이유가 없다.  형태만 유지한다.
    ics_build: str = field(default_factory=build_id)
    guide_build: str = ''

    #: 현재 노출의 날짜부.  자정을 넘겨도 한 노출 안에서는 고정된다.
    date_part: str = ''
    #: 가이드 채널 INITIALIZE 에 쓴 suffix
    guide_suffix: str = ''
    #: 셔터 개방(또는 논리적 노출 개시) 시각.  TCSSTATUS 의 DATE-OBS 가 된다.
    exp_start: datetime | None = None

    #: 셔터 닫힘 **지시** 시각.  FITS `TSHSHUT` 이 된다 (규격 5.7절).
    #: `exp_start` 와 대칭으로 지시 시점을 찍는다 -- 블레이드가 실제로 닫힌
    #: 시각은 알 수 없다(AUX 는 리밋을 읽기만 한다, DevNote 9.2.2).
    #: DARK/BIAS 는 셔터 경로를 지나지 않으므로 `None` 으로 남는다.
    exp_end: datetime | None = None

    channels: dict[str, ChannelState] = field(default_factory=dict)

    #: 노출 진행 중 여부.  GO 중복 거부(DevNote 6.4)에 쓴다.
    exposing: bool = False

    #: 이번 프레임이 `expnum` 을 점유했고 아직 advance() 하지 않은 상태.
    #: next_suffix() 가 세우고 advance() 가 내린다.  EXPNUM 질의가 현재 번호를
    #: 답할지 다음 번호를 답할지 가르는 유일한 근거다 (peek_suffix 참고).
    suffix_taken: bool = False

    # -- 채널 -------------------------------------------------------------

    def init_channels(self, ccds: tuple[str, ...]) -> None:
        self.channels = {c: ChannelState(ccd=c) for c in ccds}

    def channel(self, ccd: str) -> ChannelState:
        return self.channels[ccd]

    # -- 파일명 -----------------------------------------------------------

    def obs_date(self, when: datetime | None = None) -> str:
        """파일명 `<YYYYMMDD>` -- 이 사이트의 **관측일**.

        운영자 확정 (2026-08-13, LEECU 협의 후).  종전에는 UT 날짜를 그대로
        썼는데, 그 경계(UT 자정)가 CTIO(현지 20시)·SAAO(현지 22시)에서는 **관측
        시간대 안**이라 프레임이 경계를 걸치면 파일명과 `DATE-OBS` 의 날짜가
        갈렸다.  관측일 기준의 경계는 현지 12:30 이라 관측 중에는 지나가지 않는다.

        규칙 자체는 `rawpair.observing_date()` 에 있다 -- 사이트 규약이라 이름
        모듈이 갖는 것이 맞고, 여기서는 상태의 `site_code` 를 얹어 준다.
        """
        from . import rawpair
        return rawpair.observing_date(when or utcnow(), self.site_code)


    def next_suffix(self, when: datetime | None = None) -> str:
        """이번 노출의 과학 채널 suffix -- '<yyyymmdd>.<nnnnnn>'.

        정확히 15자여야 한다.  OBSAgent 가 EXPNUM 응답의 Filename= 뒤 15자를
        그대로 잘라 쓰고(DevNote 3.4), Wrote 의 KMTN+6 부터 15자도 이 값이다.
        """
        self.date_part = self.obs_date(when)
        self.suffix_taken = True
        # 번호를 **쓰는 시점에** 기록한다.  advance() 까지 미루면 노출 중
        # 죽었을 때 그 번호가 기록되지 않아 재실행이 같은 번호를 다시 쓴다
        # -- 방금 저장한 파일과 충돌해 파일명 fail-safe 를 부르는 경로다.
        self._record_expnum()
        return f'{self.date_part}.{self.expnum:06d}'

    def peek_suffix(self, when: datetime | None = None) -> str:
        """**다음** 노출이 쓸 suffix 를 만들되 상태는 바꾸지 않는다.

        OBSAgent 가 readout 중에 보내는 ExpNum 질의에 답하는 값이다.  받은 값은
        expinfo.strNextNum 에 담겼다가 **다음 노출이 시작될 때** strCurNum 으로
        승격돼 관측자 화면의 ExpNum 이 된다(DevNote 3.4).  그래서 노출 N 의
        readout 중에는 N+1 을 답해야 화면이 맞는다.

        레거시 실측(CTIO isis.20250401.log)이 그대로 그렇다 -- readout 중 응답이
        `Filename=20250401.010459` 이고 그 노출이 저장한 파일은
        `KMTNt.20250401.010458.fits` 로, 답이 한 칸 앞선다.

        `advance()` 는 `EXPSTATUS=IDLE` 직후에 돌므로(12.10 의 경합 수정) 노출
        중에는 `expnum` 이 아직 현재 프레임 번호다.  그래서 프레임이 번호를
        점유 중일 때만 하나 더한다.  `exposing` 을 함께 보는 것은 ABORT 로
        advance() 를 건너뛴 경우에 대비한 것이다 -- 그 플래그는 `_run()` 의
        finally 에서 반드시 내려간다.
        """
        nxt = self.expnum + 1 if (self.exposing and self.suffix_taken) else self.expnum
        return f'{self.obs_date(when)}.{nxt:06d}'

    def ics_filename(self, when: datetime | None = None) -> str:
        """FILENAME 명령의 ICS 레벨 응답 -- 'ICS.<iso>.<nnnnnn>'."""
        return f'ICS.{stamp_guide(when)}.{self.expnum:06d}'

    def advance(self) -> None:
        self.expnum += 1
        self.suffix_taken = False

    # -- expnum 지속 (2026-08-11 운영자 확정) -----------------------------
    #
    # 요구사항: **ics 를 재실행해도, data_dir 안의 파일 유무와 무관하게,
    # EXPNUM 은 무조건 1 씩 증가한다.**  그래서 마지막으로 쓴 번호를 파일에
    # 적어 두고 기동 시 그 다음 번호부터 시작한다.
    #
    # `data_dir` 를 훑어 최대값+1 을 쓰는 방식은 **채택하지 않았다** -- 저장
    # 파일을 지우거나 다른 곳으로 옮기면 번호가 되돌아가 요구사항을 깬다.
    # 기록 위치는 설정파일 옆(`config.resolve_expnum_file`)이다.

    def load_expnum(self) -> None:
        """기록된 '마지막으로 쓴 번호' 를 읽어 **그 다음 번호**부터 시작한다.

        기록이 없거나 읽을 수 없으면 현재 값(기본 1)을 그대로 쓴다.  기동을
        막지는 않는다 -- 번호가 겹치면 파일명 fail-safe 가 받아 주고, 그 경고가
        곧 "카운터가 안 읽혔다" 는 신호가 된다(DevNote 6.4).
        """
        path = self.expnum_file
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                last = int(fh.read().split()[0])
        except FileNotFoundError:
            log.info('expnum 기록이 없다 -- %06d 부터 시작한다 (%s)',
                     self.expnum, path)
            return
        except (OSError, ValueError, IndexError) as exc:
            log.warning('expnum 기록을 읽을 수 없다 (%s: %s) -- %06d 부터 시작한다',
                        path, exc, self.expnum)
            return
        if last < 0:
            log.warning('expnum 기록이 음수다 (%s: %d) -- %06d 부터 시작한다',
                        path, last, self.expnum)
            return
        self.expnum = last + 1
        log.info('expnum 기록을 이어받는다 -- 마지막 %06d, 이번 %06d (%s)',
                 last, self.expnum, path)

    def _record_expnum(self) -> None:
        """방금 쓴 번호를 기록한다.  **실패해도 노출은 진행한다.**

        같은 디렉토리에 임시 파일을 쓰고 `os.replace` 로 바꿔 넣는다 -- 기록
        도중에 죽어도 파일이 반쯤 쓰인 상태로 남지 않게 하려는 것이다.
        """
        path = self.expnum_file
        if not path:
            return
        tmp = f'{path}.tmp'
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(tmp, 'w', encoding='utf-8') as fh:
                fh.write(f'{self.expnum}\n')
            os.replace(tmp, path)
        except OSError as exc:
            log.warning('expnum %06d 을 기록할 수 없다 (%s: %s) '
                        '-- 재실행하면 번호가 되돌아간다', self.expnum, path, exc)

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



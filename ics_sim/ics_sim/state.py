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

단, 고정인 것은 **Wrote 메시지에 싣는 논리 이름**이다 (D-011/D-010).  디스크
실물은 컨트롤러당 1개 <SITE>.<날짜>.<번호>.<MK|NT>.fits 2개이고, 그 `<SITE>`
는 **`[node] observatory` 한 줄이 정한 사이트 코드**(아래 `site_code`)다 --
KMTC/KMTS/KMTA/KMTK 넷뿐이고 그 밖은 기동을 거부한다 (D-011 · D-017, raw spec
2.2절).  ⚠️ 종전의 호스트 IP 판정(D-015)은 폐지됐다 (목 확정 2026-08-24,
DevNote 11.27).  논리 이름은 통보 전용이다 (DevNote 3.2 -- raw spec v1.4 에서
규격 2.5절이 삭제되고 정본이 그쪽으로 옮겨졌다).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import build_id
from .rawpair import NUM_SPACE

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

#: ICS 가 받아들이는 이미지 타입 명령 = **raw spec 5.4절 `IMAGETYP` 통제
#: 어휘와 정확히 같다.**  헤더가 실을 수 없는 값을 명령으로 받으면 규격 밖
#: 값이 아카이브에 박히므로, 두 목록이 갈리면 안 된다
#: (`tests/test_raw_header.py` 가 대조한다).
#:
#: `STANDARD` 는 **폐지했다** (운영자 확정 2026-08-22 -- "이제 안 쓴다").
#: 레거시 명령 테이블에는 있었고 핸들러도 있었지만 규격 5.4절 어휘에 없어,
#: 그대로 두면 `IMAGETYP='STANDARD'` 가 규격 밖 값으로 실렸다.  실사용
#: `.osc` 관측 스크립트 22개와 레거시 로그 샘플에 용례가 0건이라 걷어내도
#: 실운용에 닿지 않는다.  **값을 다시 늘릴 일이 생기면 raw spec 5.4절과 이
#: 목록을 함께 고친다** (운영자 지시 -- 한쪽만 고치면 조용히 어긋난다).
IMAGE_TYPES = ('BIAS', 'DARK', 'OBJECT', 'FLAT', 'SKY', 'DOMEFLAT')


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


def _fsync_dir(path: str) -> None:
    """디렉터리 항목을 영속화한다 -- **이름 바꾸기 자체를 디스크에 박는다.**

    `os.replace` 는 원자적이지만 그 사실이 곧 영속은 아니다.  전원이 끊기면
    이름 바꾸기가 사라져 옛 파일(또는 없음)이 남을 수 있다.

    POSIX 는 디렉터리를 `O_RDONLY` 로 열어 `fsync` 하면 된다.  윈도우는
    디렉터리 핸들에 `fsync` 를 못 하므로(그리고 개발 기계일 뿐이므로) 조용히
    넘어간다 -- 운영은 리눅스다.
    """
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return                        # 윈도우 등 -- 디렉터리를 못 연다
    try:
        os.fsync(fd)
    except OSError:
        pass                          # 지원하지 않는 파일계통 -- 넘어간다
    finally:
        os.close(fd)


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
    #: **번호 공간은 `000000`–`999999`** 이고 1000000 에서 되감는다 (D-018)
    #: (`rawpair.NUM_SPACE`, D-016 1항 -- 레거시 관례).
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
    #: 사이트 코드 (`KMTC`/`KMTS`/`KMTA`/`KMTK`).  파일명 `<YYYYMMDD>` 가
    #: **사이트별 관측일** 이므로 날짜를 만들 때마다 필요하다
    #: (`rawpair.observing_date`, 운영자 확정 2026-08-13).
    #:
    #: 상태에 둔 이유: `next_suffix()` 와 `peek_suffix()` 가 **같은 규칙**을
    #: 써야 하는데 호출측이 매번 넘기게 하면 한쪽을 빠뜨린다 -- 그러면 EXPNUM
    #: 응답과 실제 파일명의 날짜가 갈리고, 그건 야간 경계에서만 드러난다.
    site_code: str = 'KMTK'
    #: FITS `ICSBUILD` -- **이 프로그램의** 빌드 식별자 (raw spec 5.5절).
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

    #: 셔터 닫힘 **지시** 시각 -- 로그·진단용.  `exp_start` 와 대칭으로 지시
    #: 시점을 찍는다 (블레이드가 실제로 닫힌 시각은 알 수 없다 -- AUX 는
    #: 리밋을 읽기만 한다, DevNote 9.2.2).  구판의 `TSHSHUT` 카드는 v1.3
    #: 미기재다 (raw spec 5.10절).  DARK/BIAS 는 `None` 으로 남는다.
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
        return f'{self.date_part}.{self.expnum % NUM_SPACE:06d}'

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
        return f'{self.obs_date(when)}.{nxt % NUM_SPACE:06d}'

    def ics_filename(self, when: datetime | None = None) -> str:
        """FILENAME 명령의 ICS 레벨 응답 -- 'ICS.<iso>.<nnnnnn>'."""
        return f'ICS.{stamp_guide(when)}.{self.expnum:06d}'

    def advance(self) -> None:
        # **D-018 (2026-08-25)**: 번호 공간은 `000000`-`999999` 로 6자리를 전부
        # 쓰고, 1000000 에 닿으면 `000000` 으로 되감는다.  구 규칙은 `099999`
        # 상한이라 맨 앞 자리가 늘 `0` 이었다.  되감지 않으면 `:06d` 가 7자리를
        # 내놓아 파일명 형식(6자리 고정폭)이 깨진다 (`rawpair.NUM_SPACE`).
        self.expnum = (self.expnum + 1) % NUM_SPACE
        self.suffix_taken = False

    def sync_expnum(self, number: int) -> None:
        """확정 번호로 카운터를 동기화한다 (D-016 3항).

        이름 충돌로 `rawpair.resolve_pair_number()` 가 번호를 올렸을 때
        불린다 -- 평소 영속화 경로(`_record_expnum`) 그대로 기록하고, 점프는
        호출측(`sequencer`)이 WARNING 로그를 남긴다.
        """
        self.expnum = number % NUM_SPACE
        self._record_expnum()

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
        # 마지막이 999999 였으면 000000 으로 되감는다 (D-016 1항 · D-018).
        self.expnum = (last + 1) % NUM_SPACE
        log.info('expnum 기록을 이어받는다 -- 마지막 %06d, 이번 %06d (%s)',
                 last, self.expnum, path)

    def _record_expnum(self) -> None:
        """방금 쓴 번호를 기록한다.  **실패해도 노출은 진행한다.**

        같은 디렉토리에 임시 파일을 쓰고 `os.replace` 로 바꿔 넣는다 -- 기록
        도중에 죽어도 파일이 반쯤 쓰인 상태로 남지 않게 하려는 것이다.

        **전원이 끊겨도 값이 남아야 한다** (운영자 요구 2026-08-23: 재부팅
        상황에서도 기억해야 한다).  정상 종료·재부팅은 `os.replace` 만으로도
        충분하지만 **전원 손실은 다르다** -- 이름 바꾸기는 반영됐는데 내용
        블록은 아직 디스크에 없을 수 있고, 그러면 파일이 비거나 0 바이트로
        남아 번호가 1 로 되돌아간다.  그래서 셋을 다 한다:
        내용 `fsync` -> `os.replace` -> **디렉터리 `fsync`**(이름 바꾸기 자체를
        영속화).  프레임당 한 번이고 몇 바이트라 비용이 없다.
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
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            _fsync_dir(parent or '.')
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



#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""텔레메트리 주기 감시·기록 -- 층 1·2 (설계 2026-08-27, 구현 2026-08-28).

**새 판독기가 아니라 기록기다.**  층 1(온도 10 + 레일 7x2 = 24개)은
`parse.telemetry_of()` 가 이미 정확히 그 값을 돌려준다 -- 감시와 FITS 헤더가
**같은 함수**를 읽으므로 둘이 어긋날 수 없다(기계 사본을 넷째로 만들지 않는다).
층 2 는 같은 응답에서 바이어스 16채널 V/I 와 `VALID`/`COUNT`/`LOG` 를 더 적는
것이고, **지금은 로그만**이다 (헤더 수록은 규격 개정 사안 -- 작업 C 의 D3).

원장 v1.14:466 이 `CCDTEMP` 대표 센서를 두고 **"센서 이상은 취득 SW 로그가
담는다"** 고 약속했는데 그 로그가 없었다.  이 모듈이 그 약속의 이행물이다.

## 왜 `ics_archon` 안에 두나 -- 접속자는 컨트롤러당 하나다

**한 컨트롤러에 여러 노드가 붙는 구성은 두지 않는다** (운영자 확정 2026-08-28).
science 컨트롤러는 `ics_archon` 이, guide 는 `icg_archon` 이 맡고 **각자 접속한
뒤에 자기 감시를 시작한다.**  그래서 감시는 별개 프로세스가 아니라 이 프로세스
안의 백그라운드 태스크이고, `ArchonController` 의 **같은 소켓·같은 락**을 탄다.

하드웨어도 같은 방향을 가리킨다 -- **Rev F 백플레인은 동시 접속이 하나뿐이다**
(매뉴얼 p.15.  KASI 벤치기 `KMTK_SCI_113` 과 guide 유닛이 Rev F 다).  관측소
유닛(Rev H)은 4접속이지만 규칙은 같게 둔다: **소유자가 하나면 "누가 이 값을
읽었나" 를 물을 일이 없다.**

⚠️ 그래서 본편이 떠 있는 동안에는 STA GUI 도 `tools/probe_archon.py` 도 붙이지
않는다 -- 설정으로 피하는 것이 아니라 **본편을 내리고 쓴다.**

## 지키는 규칙 넷 (운영자 승인 2026-08-27)

1. **락을 새로 만들지 않는다** -- `ArchonController._lock` 을 그대로 탄다
   (`refresh_status_live()` 가 `query()` 를 부르면 자동으로 직렬화된다).
   ⚠️ **FETCH 가 락을 344 MiB 동안 쥔다**(실측 3.2~3.5초, 상한은 `fetch_timeout`
   10초 -- DevNote 10.4·10.6) -- 그동안 감시 주기가
   밀린다.  **"간격을 못 맞췄다" 를 오류로 보지 않는다**: 밀린 시간을
   `lag_ms` 열에 적고 넘어가며, **밀린 만큼 몰아서 뜨지 않는다.**
2. **`telemetry_enabled` 래치를 되돌리지 않는다** -- 그것은 취득 경로의
   판단이다(F8).  감시는 자기 실패 카운터(`status_live_fails`)로 백오프한다.
3. **파일은 컨트롤러당 하나 + 날짜별**로 가른다.  한 파일에 무한 append 하면
   밤새 돌린 것이 하나로 뭉친다.  그리고 **헤더 줄을 반드시 넣는다** -- 원형
   `tvm.gui.log` 는 열 이름이 없어 스크립트 소스를 봐야 몇 번째가 무엇인지
   알 수 있었고, **자리 수가 바뀌면 과거 파일이 조용히 오독된다.**
4. **`EXPSTATUS` 를 한 열로 같이 적는다** -- 나중에 "이 온도가 독출 중 값인지
   대기 중 값인지" 를 반드시 묻게 되고, **사후에 시각으로 맞출 수는 없다.**

## 열 (고정)

    utc, age_ms, lag_ms, expstatus,
    valid, count, fresh, log_n, power, powergood, overheat,
    T1_<라벨>[C] x10                 규격 5.6.1절 자리 (rawhdr.TEMP_MOD_LABELS)
    V1_<레일>[V] x7, I1_<레일>[A] x7  ⚠️ 시스템 레일 전류는 **A**
    rail_flag                        p.41 power good 범위 이탈
    B_<라벨>_V[V], B_<라벨>_I[mA]     ⚠️ 모듈 바이어스 전류는 **mA** -- 섞지 말 것
    event                            start | stop | offline |
                                     poll_failed | resumed | ''

`event` 열은 설계 목록에 없던 것을 하나 더한 것이다 -- 설계가 "**시작·종료·
재연결을 한 줄씩 남긴다**" 를 요구하는데, 그 줄을 값 없는 행으로 적으면
`valid=0` 표본과 구별되지 않는다.  원형 로그에 60초 넘는 공백이 셋(178초 ·
6.2시간 · 3.0일) 있었고 **스크립트가 죽은 것인지 사람이 껐다 켠 것인지 로그
만으로는 알 수 없었다** -- 그 물음에 답하는 것이 이 열이다.

`FETCHLOG` 는 **쓰지 않는다** (운영자 확정 2026-08-27) -- `LOG=n` 한 열만
남긴다.  근거와 승격 기준은 `../../SMC_CLAUDE.md` 의 그 절에 있다.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import os
import time
from datetime import datetime, timezone

from . import parse
from .protocol import ArchonError
from .. import _simpath

_simpath.ensure()

from ics_sim import rawhdr                    # noqa: E402

log = logging.getLogger('ics_archon.monitor')

#: 값이 없는 자리에 적는 것 -- 나열 카드와 같은 sentinel 을 쓴다.
#: **자리를 비우지 않는다**: 빈 칸은 "0 이었나 결측이었나" 를 가리지 않는다.
NC = parse.FIELD_NC


def _utc_stamp(when: float) -> str:
    """`YYYY-MM-DDThh:mm:ss.sssZ` -- 밀리초까지, UTC 명시."""
    dt = datetime.fromtimestamp(when, timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.') + '%03dZ' % (dt.microsecond // 1000)


def _utc_date(when: float) -> str:
    return datetime.fromtimestamp(when, timezone.utc).strftime('%Y%m%d')


def _fmt(value, digits: int) -> str:
    """수치는 자리수 고정, 그 밖(sentinel 문자열)은 그대로."""
    if isinstance(value, float):
        return '%.*f' % (digits, value)
    return str(value)


class TelemetryLog:
    """컨트롤러 하나의 CSV 기록 -- **날짜별 파일 + 고정 열.**

    파일 이름은 `telemetry.<태그>.<YYYYMMDD>.csv` 이고 자리는 `~/AIC/log/` 다
    (운영자 확정 2026-08-27).  ⚠️ **`[paths] data_dir` 밑에 두지 않는다** --
    자료와 함께 굴러가 아카이브 정책에 걸린다.
    """

    def __init__(self, tag: str, log_dir: str, columns: list[str]) -> None:
        self.tag = tag
        self.log_dir = log_dir
        self.columns = columns
        self._date = ''
        self._fh = None
        self._writer = None
        self.path = ''

    # -- 파일 -------------------------------------------------------------

    def _open(self, date: str) -> None:
        """그 날짜의 파일을 연다.  **열이 다르면 새 파일로 가른다.**

        같은 날 안에서 열 구성이 바뀔 수 있는 경로가 실재한다 -- ACF 를 바꿔
        이름표 붙은 바이어스 채널이 늘거나 줄면 열 수가 달라진다(그리고 그것은
        `CTRLnCFG` 범프 사유다, 규격 4.3절).  그때 같은 파일에 이어 쓰면 **과거
        행이 조용히 오독된다** -- 열 이름이 한 줄뿐이라 어디서 바뀌었는지
        알 수 없다.  그래서 헤더가 다르면 `…<YYYYMMDD>.2.csv` 로 가른다.
        """
        self.close()
        base = os.path.join(self.log_dir, 'telemetry.%s.%s' % (self.tag, date))
        path = base + '.csv'
        seq = 1
        while True:
            head = self._existing_header(path)
            if head is None or head == self.columns:
                break
            seq += 1
            log.warning('%s: %s 의 열 구성이 지금과 다르다 -- 이어 쓰지 않고 '
                        '%s.%d.csv 로 가른다 (ACF 가 바뀌면 바이어스 채널 수가 '
                        '달라진다)', self.tag, os.path.basename(path),
                        os.path.basename(base), seq)
            path = '%s.%d.csv' % (base, seq)
        fresh = self._existing_header(path) is None
        # `newline=''` 은 csv 모듈의 요구다 -- 없으면 윈도우에서 빈 줄이 낀다.
        self._fh = open(path, 'a', encoding='utf-8', newline='')
        self._writer = csv.writer(self._fh)
        if fresh:
            self._writer.writerow(self.columns)
        self._date = date
        self.path = path

    @staticmethod
    def _existing_header(path: str) -> list[str] | None:
        """이미 있는 파일의 첫 줄 (없으면 `None`, 비었으면 빈 목록)."""
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding='utf-8', newline='') as fh:
                for row in csv.reader(fh):
                    return row
            return []
        except OSError as exc:                  # pragma: no cover
            log.warning('기존 기록 파일을 읽지 못했다 (%s) -- %s', exc, path)
            return []

    def write(self, row: list[str], when: float) -> None:
        """한 행.  **날짜가 바뀌면 파일을 갈아탄다.**

        ⚠️ 실패해도 예외를 올리지 않는다 -- 기록은 취득의 부산물이고, 디스크가
        가득 찼다고 관측을 세우는 것은 손해가 훨씬 크다.
        """
        date = _utc_date(when)
        try:
            if self._writer is None or date != self._date:
                self._open(date)
            self._writer.writerow(row)
            # **행마다 flush 한다** -- 밤새 돌린 기록이 프로세스와 함께 사라지면
            # 기록의 존재 이유가 없다.  fsync 까지는 하지 않는다(주기가 수십 초
            # 라 OS 버퍼로 충분하고, fsync 는 저장 경로와 디스크를 다툰다).
            self._fh.flush()
        except OSError as exc:
            log.error('%s: 텔레메트리 기록 실패 (%s) -- 취득은 계속한다',
                      self.tag, exc)
            self.close()

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except OSError:                     # pragma: no cover
                pass
        self._fh = None
        self._writer = None


class TelemetryMonitor:
    """컨트롤러 한 대의 주기 감시 태스크.

    `app.py` 가 `IcsSim.spawn()` 으로 띄운다 -- **`ics_sim` 은 무수정**이다.
    """

    def __init__(self, ctrl, acfg, expstatus=None) -> None:  # noqa: ANN001
        self.ctrl = ctrl
        self.acfg = acfg
        #: 지금 `EXPSTATUS` 를 돌려주는 콜백 (규칙 4).  없으면 `NC`.
        self._expstatus = expstatus
        self._stop = asyncio.Event()
        #: ACF 에서 찾은 바이어스 채널.  **첫 행 앞에 한 번 정한다** -- 열
        #: 이름이 그것으로 정해지므로 도중에 바뀌면 파일을 갈아타야 한다.
        self.channels: list[tuple[str, str]] = []
        self.log: TelemetryLog | None = None
        self._prev_count: int | None = None
        #: 직전 폴링이 실패했나 -- 성공으로 돌아오는 순간에 `resumed` 를 적는다.
        self._failing = False

    # -- 열 ---------------------------------------------------------------

    def columns(self) -> list[str]:
        """고정 열 이름.  **단위를 이름에 박는다.**

        ⚠️ 시스템 레일 전류는 **A**, 모듈 바이어스 전류는 **mA** 다 (매뉴얼
        p.47-48).  섞으면 1000배 틀리고, 값만 보고는 알 수 없다.
        """
        cols = ['utc', 'age_ms', 'lag_ms', 'expstatus',
                'valid', 'count', 'fresh', 'log_n',
                'power', 'powergood', 'overheat']
        cols += ['T%d_%s[C]' % (i + 1, label)
                 for i, label in enumerate(rawhdr.TEMP_MOD_LABELS)]
        cols += ['V%d_%s[V]' % (i + 1, rail)
                 for i, rail in enumerate(parse.VOLT_RAILS)]
        cols += ['I%d_%s[A]' % (i + 1, rail)
                 for i, rail in enumerate(parse.VOLT_RAILS)]
        cols.append('rail_flag')
        for _prefix, label in self.channels:
            cols += ['B_%s_V[V]' % label, 'B_%s_I[mA]' % label]
        cols.append('event')
        return cols

    # -- 행 ---------------------------------------------------------------

    def _row(self, when: float, *, event: str = '', lag: float = 0.0
             ) -> list[str]:
        """지금의 `status_live` 로 행 하나를 만든다.

        **`valid=0` 행도 버리지 않는다** -- 언제부터 이상했는지가 자료다.  그래서
        `telemetry_of(honour_valid=False)` 로 값을 그대로 싣고, 유효 여부는
        `valid` 열이 따로 말한다.  ⚠️ **헤더는 반대다** -- `VALID=0` 이면
        `Cn_*` 가 `NC` 로 떨어진다 (D4).
        """
        st = self.ctrl.status_live
        age = ((when - self.ctrl.status_live_at) * 1000.0
               if self.ctrl.status_live_at and st else None)
        valid = parse.status_valid(st)
        count = parse.status_count(st)
        fresh = NC
        if count is not None:
            fresh = ('1' if self._prev_count is None or count != self._prev_count
                     else '0')
            self._prev_count = count
        power = parse.power_state(st)
        log_n = parse.log_count(st)
        overheat = st.get('OVERHEAT', NC) if st else NC

        tel = parse.telemetry_of(st, honour_valid=False)
        temps = tel.get('temp') or [NC] * len(parse.TEMP_MODS)
        volts = tel.get('volt') or [NC] * len(parse.VOLT_RAILS)
        currs = tel.get('curr') or [NC] * len(parse.VOLT_RAILS)

        row = [_utc_stamp(when),
               '%.0f' % age if age is not None else NC,
               '%.0f' % (lag * 1000.0),
               (self._expstatus() if self._expstatus else NC) or NC,
               NC if valid is None else ('1' if valid else '0'),
               NC if count is None else str(count),
               fresh,
               NC if log_n is None else str(log_n),
               NC if power is None else str(power),
               st.get('POWERGOOD', NC) if st else NC,
               overheat]
        row += [_fmt(v, 1) for v in temps]
        row += [_fmt(v, 3) for v in volts]
        row += [_fmt(v, 3) for v in currs]
        row.append(' '.join(parse.rail_problems(st, self.acfg.rail_limits))
                   or '')
        for _label, volt, curr in parse.bias_readings(st, self.channels):
            row += [_fmt(volt, 3), _fmt(curr, 3)]
        row.append(event)
        return row

    # -- 태스크 -----------------------------------------------------------

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        """주기 감시 -- 종료 지시(`stop()`)나 태스크 취소가 올 때까지.

        **간격을 못 맞춘 것을 오류로 보지 않는다** (규칙 1).  FETCH 가 락을
        쥐고 있으면 이 주기가 통째로 밀리는데, 밀린 만큼 몰아서 뜨면 그 순간
        컨트롤러에 왕복이 폭주한다 -- 감시가 아니라 부하다.  다음 시각을
        **지금 기준으로 다시 잡고** 밀린 시간만 `lag_ms` 에 적는다.

        `stop` 행은 `finally` 에서 적는다 -- 정상 경로(`stop()` -> 루프 탈출)와
        취소 경로(`IcsSim.stop()` 이 태스크를 취소한다) **양쪽**이 그 자리를
        지나기 때문이다.  둘 중 하나에만 적으면 FETCH 락에 걸려 취소된 종료가
        기록에서 사라진다.
        """
        if not self._prepare():
            return
        interval = max(float(self.acfg.monitor_interval), 1.0)
        self._emit(time.time(), event='start')
        next_at = time.monotonic() + interval
        try:
            while True:
                try:
                    await asyncio.wait_for(
                        self._stop.wait(),
                        timeout=max(next_at - time.monotonic(), 0.0))
                    break                       # 종료 지시
                except asyncio.TimeoutError:
                    pass
                lag = max(time.monotonic() - next_at, 0.0)
                event = await self._poll(interval)
                if lag > interval:
                    log.info('%s: 감시 주기가 %.1f초 밀렸다 (FETCH 락이 원인일 '
                             '수 있다) -- 건너뛴 표본은 몰아서 뜨지 않는다',
                             self.ctrl.tag, lag)
                # ⚠️ **실패 여부와 사건 이름을 갈라 둔다.**  `resumed` 를
                # 넣은 뒤에 `_failing = bool(event)` 로 세면 그 값이 참이 되어
                # **다음 성공마다 `resumed` 가 되풀이된다** (자기 회복 표시가
                # 자기를 다시 트리거한다).
                failed = bool(event)
                if not failed and self._failing:
                    event = 'resumed'
                self._failing = failed
                self._emit(time.time(), event=event, lag=lag)
                # **다음 시각을 지금 기준으로 다시 잡는다** (몰아 뜨기 금지).
                next_at = time.monotonic() + interval
        finally:
            # 취소로 끝나도 마지막 줄은 남는다 -- 원형 로그의 긴 공백이
            # "죽은 것인가 끈 것인가" 를 못 가렸던 것이 이 줄을 두는 이유다.
            self._emit(time.time(), event='stop')
            if self.log is not None:
                self.log.close()

    async def _poll(self, interval: float) -> str:
        """한 표본.  성공하면 `''`, 아니면 사건 이름(`offline`/`poll_failed`).

        **접속을 여는 것은 감시의 일이 아니다** (운영자 2026-08-28).  기동에서
        `IcsArchon._connect_controllers()` 가 이미 열어 뒀고, 여기 있는 것은
        **끊겼거나 그때 못 붙은 경우의 재수립**이다 -- 컨트롤러 전원이 나중에
        들어오는 배치가 실재하므로 감시가 주기마다 다시 시도한다.

        접속자가 이 프로세스 하나라는 것이 전제다 -- `ics_archon` 이 science
        컨트롤러를, `icg_archon` 이 guide 를 맡고 **한 컨트롤러에 여러 노드가
        붙는 구성은 두지 않는다** (Rev F 는 동시 접속이 하나뿐이고, Rev H 라도
        같은 규칙이다).  그래서 여기서 재접속하는 것이 남의 접속을 밀어내는
        일이 되지 않는다.
        """
        if not self.ctrl.link.connected:
            try:
                await self.ctrl.connect()
            except (ArchonError, TimeoutError, OSError) as exc:
                self.ctrl.status_live = {}
                if not self._failing:
                    log.warning('%s: 감시가 접속하지 못했다 (%s) -- %.0f초마다 '
                                '다시 시도한다.  컨트롤러 전원과 [archon] '
                                'ctrl_%s_host 를 확인하라', self.ctrl.tag, exc,
                                interval, self.ctrl.tag.lower())
                return 'offline'
            log.info('%s: 감시가 링크를 다시 세웠다 -- %s:%d', self.ctrl.tag,
                     self.ctrl.link.host, self.ctrl.link.port)
        return '' if await self.ctrl.refresh_status_live() else 'poll_failed'

    # -- 내부 -------------------------------------------------------------

    def _prepare(self) -> bool:
        """기록 자리와 열을 정한다.  못 하면 `False` (감시를 걸지 않는다)."""
        if not self.acfg.telemetry:
            log.info('%s: [archon] telemetry=false -- 감시도 돌리지 않는다 '
                     '(컨트롤러와의 왕복을 labtest v1.0 계보와 같게 둔다)',
                     self.ctrl.tag)
            return False
        directory = self.acfg.monitor_log
        # ⚠️ **`~` 가 안 펼쳐졌으면 만들지 않는다.**  `os.makedirs` 는 그것을
        # 정상적인 상대 경로로 보고 **작업 디렉터리 아래에 `~` 폴더**를 아무
        # 불평 없이 만든다 -- 오류가 없으므로 기록이 엉뚱한 곳에 쌓인다
        # (`ics_sim config.py` 의 2026-08-23 실측과 같은 함정).
        if not directory or directory.startswith('~'):
            log.error('[archon] monitor_log 가 비었거나 `~` 가 안 펼쳐졌다 '
                      '(%r) -- 감시를 걸지 않는다', directory)
            return False
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as exc:
            log.error('감시 기록 자리를 만들지 못했다 (%s) -- %s.  감시를 '
                      '걸지 않는다', exc, directory)
            return False
        # **ACF 를 먼저 읽어 둔다 -- 왕복이 없다.**  `parse_acf()` 는 파일만
        # 읽고 컨트롤러를 만지지 않는다.  이것이 없으면 감시가 기동 직후에
        # 뜨는데 `ctrl.config` 는 첫 노출의 `prepare()` 전까지 비어 있어서
        # **층 2 열이 통째로 빠진 파일**이 하루치 쌓인다 -- 그리고 첫 노출에서
        # 채널이 생기면 열 구성이 바뀌어 파일이 갈린다.  기동 시점에 정해 두면
        # 그 날 파일이 처음부터 온전하다.
        #
        # `acf_applied` 는 건드리지 않으므로 `prepare()` 의 판단(적용할지 ·
        # 줄 번호를 대조할지)은 그대로다.
        if not self.ctrl.config:
            acf = self.acfg.acf.get(self.ctrl.tag, '')
            if acf:
                try:
                    self.ctrl.parse_acf(acf)
                except ArchonError as exc:
                    log.warning('%s: 감시용 ACF 읽기 실패 (%s) -- 층 2(바이어스)'
                                ' 열 없이 돈다', self.ctrl.tag, exc)
        # **바이어스 채널은 ACF 에서 찾는다** -- STATUS 가 아니다.  두 dict 의
        # 키 문자열이 같아서(지령값 vs 실측값) 헷갈리기 쉬운 자리다.
        self.channels = parse.bias_channels(self.ctrl.config)
        if not self.channels:
            log.warning('%s: ACF 에서 이름표 붙은 바이어스 채널을 못 찾았다 -- '
                        '층 2(16채널 V/I) 열이 비게 된다.  ACF 파싱이 먼저인지 '
                        '확인할 것', self.ctrl.tag)
        else:
            log.info('%s: 바이어스 %d채널 감시 -- %s', self.ctrl.tag,
                     len(self.channels),
                     ', '.join(label for _p, label in self.channels))
        self.log = TelemetryLog(self.ctrl.tag, directory, self.columns())
        log.info('%s: 텔레메트리 감시 %.0f초 간격, 기록 %s', self.ctrl.tag,
                 self.acfg.monitor_interval, directory)
        return True

    def _emit(self, when: float, *, event: str = '', lag: float = 0.0) -> None:
        if self.log is not None:
            self.log.write(self._row(when, event=event, lag=lag), when)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""컨트롤러 한 대의 제어 시퀀스 -- ACF 적용 · 전원 · 노출 · 독출 · FETCH.

원형은 실험실 취득 스크립트의 `GetDataset()`/`Exposure()` 다.  **제어 시퀀스
자체(POWERON -> WCONFIG/APPLYALL -> LOADPARAMS -> FRAME 폴링 -> FETCH)는 v1.0
계보로 1년 실사용 검증된 것**이므로 순서와 명령을 바꾸지 않았다.  바꾼 것은
바깥 껍데기다:

* **전역 상태 -> 객체.**  labtest 는 컨트롤러 한 대를 전제로 전역 변수
  (`archon`/`config`/`configline`/`CURRENT_ACF`/`STATUS_SNAPSHOT`)를 썼다.
  실기는 과학 2대(+가이드 1대)이므로 한 대를 객체 하나로 접는다.
* **블로킹 -> `asyncio.to_thread` + 락.**  시퀀서는 asyncio 이고 OBSAgent 의
  시간 창(획득 1.8초 · IDLE 0.9초 · Wrote 25초, DevNote 3.3)이 이벤트 루프
  정지를 허용하지 않는다.  왕복은 스레드로 내보내고, 한 연결에 한 번에 하나만
  나가도록 락으로 묶는다.
* **명령마다 상한을 준다.**  프로토콜은 **인식 못 한 명령에 무응답**이므로
  (매뉴얼 p.45) 오타 하나로 영구히 멈춘다.  `ArchonLink.command` 의 기본값
  (무한 대기)은 규약이라 그대로 두고, 부르는 쪽인 여기서 상한을 준다.

## 노출을 누가 재나 -- 이 층의 가장 중요한 판단

**컨트롤러가 잰다.**  `IntMS` 를 실어 `LOADPARAMS` 하면 Archon 의 타이밍
스크립트가 적분·셔터 트리거·독출을 스스로 몰고 간다.  시퀀서의 카운트다운
(`Remaining=N sec.`)은 **관측자에게 보내는 알림**이고 하드웨어를 몰지 않는다.

그래서 노출을 시작하는 자리가 두 갈래다 (`backend.py` 가 부른다):

| 노출 | 시작 자리 | 이유 |
|---|---|---|
| 셔터 노출 (OBJECT/FLAT/SKY/DOMEFLAT) | `open_shutter()` | 시퀀서가 여기서 셔터를 열라고 한다.  `IntMS` = 노출시간 |
| DARK / BIAS | `readout()` | 시퀀서가 `_integrate_dark` 에서 백엔드를 아예 부르지 않는다.  적분 시간은 `begin_exposure()` 훅으로 미리 받아 두고 여기서 `IntMS` 에 실어 건다 -- **컨트롤러가 잰다** (훅이 없으면 `IntMS=0` 으로 곧바로 읽어내고 경고를 남긴다) |

⚠️ **STOP(적분 조기 종료)은 컨트롤러의 적분을 자르지 못한다.**  타이밍
스크립트가 이미 `IntMS` 만큼 세고 있으므로, 할 수 있는 것은 `TRIGOUTFORCE=1`
로 **셔터를 강제로 닫아 빛을 끊는 것**뿐이다.  노출은 남은 시간을 다 세고
끝나므로 헤더 `EXPTIME` 은 요청값이고 실제 개방 시간은 그보다 짧다.
`FASTLOADPARAM IntMS 0`(매뉴얼 p.52)이 즉시 반영되는지는 **실기 확인
항목**이다 -- 되면 그쪽이 맞다.
"""

from __future__ import annotations

import asyncio
import configparser
import logging
import os
import time
from dataclasses import dataclass

from . import parse
from .protocol import ArchonError, ArchonLink

log = logging.getLogger('ics_archon.ctrl')


@dataclass
class FrameTicket:
    """노출 1회의 상태 -- **그 프레임이 들고 간다.**

    컨트롤러 필드에 두면 파이프라인이 겹칠 때 뒤 프레임이 앞 프레임의 값을
    덮는다.  저장은 `write_delay` 뒤에 백그라운드로 돌고 그 사이 다음 프레임이
    이미 `LOADPARAMS` 를 냈을 수 있다 -- 그러면 앞 프레임의 저장이 "직전 프레임
    번호" 를 잘못 알고(엉뚱한 프레임을 기다린다), 반대로 앞 프레임의 뒷정리가
    뒤 프레임의 "노출을 걸었다" 표시를 지운다(이중 노출).

    `ics_sim` 이 같은 부류를 두 번 겪었다 -- 파일 일련번호 경합(DevNote 12.10)과
    D-016 선검사의 채널 suffix 재읽기(11.20 critical).  결론은 매번 같았다:
    **프레임의 것은 프레임이 정하고, 나중에 다시 읽지 않는다.**
    """

    #: 이 표가 속한 프레임의 이름 (`<YYYYMMDD>.<NNNNNN>`).
    #:
    #: **이것이 없으면 취소된 프레임의 표가 대기열에 영구히 남는다.**  ABORT 나
    #: 저장 실패로 `write_frame()` 이 안 불리면 아무도 표를 꺼내지 않고, 다음
    #: 프레임의 저장이 **그 낡은 표**를 FIFO 로 집어 온다 -- 그러면 파일마다
    #: 한 노출 뒤진 픽셀이 담기고 헤더는 새 프레임의 것이라 **경고가 한 줄도
    #: 안 뜬다** (2026-08-24 검토에서 확정한 blocker).
    suffix: str
    #: 노출 지시 **직전**의 프레임 번호.  이 값이 바뀌면 내 프레임이다.
    prev_frame: int
    #: 적분 종료 예상 시각 (monotonic).  `None` 이면 즉시 독출(`IntMS=0`).
    int_until: float | None = None
    #: 완료가 확인된 프레임.  `wait_frame()` 이 채운다.
    ready: parse.FrameStatus | None = None

#: 명령별 응답 상한 [s].  근거는 "그 명령이 실제로 무엇을 하나" 다.
#:
#: * 짧은 것(WCONFIG·FRAME·SYSTEM)은 즉답이라 넉넉해도 5초면 충분하다.
#: * `APPLY*`/`LOADTIMING` 은 설정을 모듈에 밀어 넣으므로 초 단위가 걸린다.
#: * `POWERON`/`POWEROFF` 는 바이어스 램프가 있어 더 길다.
#: 상한을 넘기면 연결이 어긋난 것으로 보고 재수립한다 (부분 응답이 소켓에
#: 남을 수 있어서다 -- DevNote 11.22 (1)).
T_FAST = 5.0
#: `APPLYSYSTEM`·`LOADPARAMS` -- 시스템/파라미터만 적용한다.  `APPLYALL` 과 같은
#: 상한을 주면 **노출 안에서 60초를 매달린다**(무응답 명령이면 실제로 그랬다) --
#: 25초 `Wrote` 창을 훌쩍 넘는다.
T_SYSTEM = 15.0
#: `APPLYALL`·`LOADTIMING` -- 설정 전체를 모듈에 밀어 넣는다.  첫 프레임에서만
#: 불리고 시간 창이 없는 구간이라 넉넉히 준다.
T_APPLY = 60.0
T_POWER = 30.0


class ArchonController:
    """컨트롤러 한 대 (`MK` 또는 `NT`)."""

    def __init__(self, tag: str, cfg) -> None:  # noqa: ANN001 -- ArchonCfg
        self.tag = tag
        self.cfg = cfg
        self.link = ArchonLink(cfg.hosts.get(tag, ''), cfg.port,
                               sock_timeout=cfg.sock_timeout,
                               burst_len=cfg.burst_len, name=tag)
        #: 한 연결에 한 번에 하나.  FETCH 가 락을 오래 쥐지만 컨트롤러마다
        #: 연결이 따로라 다른 대의 왕복은 막지 않는다.
        self._lock = asyncio.Lock()

        #: ACF 설정 줄 -> 내용, 그리고 키 -> 줄 번호.  `WCONFIG` 는 줄 번호로
        #: 쓰므로 이 대응이 없으면 파라미터를 못 바꾼다.
        self.config: dict[str, str] = {}
        self.configline: dict[str, int] = {}
        #: 마지막으로 적용(또는 파싱)한 ACF 경로 -- FITS `CTRLnCFG`/`RDMODE`
        #: 의 근거다.  컨트롤러는 적용된 ACF 이름을 보고하지 않는다 (p.54).
        self.acf_path: str = ''
        self.acf_applied = False

        #: 마지막 `SYSTEM`/`STATUS` 스냅샷.  **헤더용 접근자는 동기 메서드**
        #: 라(시퀀서가 `_backend_fact` 로 그냥 부른다) 소켓을 만질 수 없다 --
        #: 노출 개시 전에 떠 둔 이 값을 읽는다.  labtest 도 같은 이유로
        #: `STATUS_SNAPSHOT` 을 노출 앞에서 떴다.
        self.system: dict[str, str] = {}
        self.status: dict[str, str] = {}
        #: STATUS 가 한 번 실패하면 이 실행 동안 다시 묻지 않는다 -- 어긋난
        #: 뒤에도 노출마다 되풀이하는 것은 위험을 반복하는 일이다.  카드
        #: 몇 장보다 취득이 우선이다.
        self.telemetry_enabled = bool(cfg.telemetry)

        self.powered = False
        #: `POWERON` 을 **보낸 적이 있나.**  응답을 잃은 경우까지 포함한다 --
        #: 종료 때 `POWEROFF` 를 낼지는 이 값으로 정한다 (`powered` 는 응답으로
        #: 확인된 상태라 "켜졌는데 모르는" 경우를 놓친다).
        self.power_attempted = False
        #: 이상을 이미 알렸나 -- 프레임마다 같은 줄을 되풀이하지 않는다.
        self._health_bad = False
        #: **진행 중** 프레임의 표 (노출·독출이 끝나면 `release_current()`).
        #: `triggered`/`integrating` 이 이것을 본다.
        self._current: FrameTicket | None = None
        #: 저장을 기다리는 프레임 표 -- FIFO.  `write_frame()` 이 가져간다.
        #: 파이프라인이 겹쳐도 앞 프레임의 저장이 자기 프레임을 기다린다.
        self._queue: list[FrameTicket] = []

    # -- 왕복 -------------------------------------------------------------

    async def cmd(self, command: str, timeout: float = T_FAST) -> bytes:
        """텍스트 명령 하나.  실패하면 `ArchonError`.

        시한 초과는 **연결 재수립**으로 이어진다 -- 참조번호를 미리 올려
        두어(`protocol.py` 3번) 늦은 응답이 다음 명령에 먹히지는 않지만,
        부분 수신분이 소켓에 남는 문제는 그대로다.
        """
        async with self._lock:
            def _run() -> bytes:
                try:
                    return self.link.command(command, timeout=timeout)
                except TimeoutError as exc:
                    self.link.resync('%s 응답 시한 초과' % command)
                    raise ArchonError(str(exc), cmd=command) from None
                except ArchonError as exc:
                    # **거부(`?xx`)는 연결 문제가 아니다** -- 내 명령이 틀린
                    # 것이므로 링크를 버리지 않는다.  그 밖의 실패(프레이밍
                    # 어긋남 · 상대가 끊음)는 스트림 위치를 잃은 것이라
                    # **반드시 재수립해야 한다** -- 안 하면 이후 모든 명령이
                    # 같은 어긋남을 되풀이하고 그 컨트롤러는 재기동까지 죽는다
                    # (2026-08-24 검토에서 확정).
                    if not exc.reply_error:
                        self.link.resync('%s 왕복이 깨졌다' % command)
                    raise
            return await asyncio.to_thread(_run)

    async def query(self, command: str, timeout: float = T_FAST
                    ) -> dict[str, str]:
        """`KEY=VALUE` 나열을 돌려주는 질의 (`SYSTEM`/`STATUS`/`FRAME`)."""
        return parse.keyvals(await self.cmd(command, timeout))

    # -- 연결 -------------------------------------------------------------

    async def connect(self) -> None:
        if not self.cfg.hosts.get(self.tag):
            raise ArchonError('%s: [archon] ctrl_%s_host 가 비어 있다'
                              % (self.tag, self.tag.lower()))
        async with self._lock:
            await asyncio.to_thread(self.link.connect, self.cfg.connect_retry)

    async def close(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self.link.close)

    # -- ACF --------------------------------------------------------------

    def parse_acf(self, path: str) -> None:
        """ACF 를 읽어 `config`/`configline` 을 만든다.  **왕복하지 않는다.**

        `configparser.read()` 는 없는 파일에 조용히 성공하고 그 다음
        `items('CONFIG')` 가 `NoSectionError` 로 터진다 -- "설정 파일이 없다"
        라는 원인이 화면에 안 나온다.  경로가 상대경로라 **작업 디렉터리가
        다른 것**이 가장 흔한 원인이어서 풀어낸 절대경로와 cwd 를 같이 알린다
        (labtest 가 여기서 가장 많이 넘어졌다).
        """
        if not os.path.isfile(path):
            raise ArchonError(
                "%s: ACF 가 없다 -- '%s'\n"
                "        절대경로 '%s'\n"
                "        cwd      '%s'\n"
                '        경로가 상대경로면 작업 디렉터리를 확인하라.'
                % (self.tag, path, os.path.abspath(path), os.getcwd()))
        cp = configparser.RawConfigParser(strict=False)
        # **파싱 예외를 전부 `ArchonError` 로 접는다.**  `configparser` 는
        # `DuplicateOptionError`·`MissingSectionHeaderError`·`ParsingError` 를
        # 낼 수 있고 그것들은 `ArchonError` 가 아니다 -- `initialize()` 의
        # `except (ArchonError, TimeoutError, OSError)` 를 통과하지 못해
        # **노출 태스크가 조용히 죽는다**(`Wrote` 0회 · 오류 0회).  실제 ACF 는
        # 수천 줄이라 중복 키가 있을 수 있다 (2026-08-24 검토에서 확정).
        #
        # `strict=False` 는 labtest 와 같은 관용도를 준다 -- 중복 키는 마지막
        # 값이 이긴다.  그래도 남는 예외는 아래에서 감싼다.
        try:
            cp.read(path)
            items = cp.items('CONFIG')
        except configparser.NoSectionError:
            raise ArchonError("%s: ACF 에 [CONFIG] 절이 없다 -- '%s' 가 Archon "
                              '설정 파일인지 확인하라' % (self.tag, path)) from None
        except (configparser.Error, UnicodeDecodeError, ValueError) as exc:
            raise ArchonError(
                "%s: ACF 를 읽을 수 없다 -- '%s'\n        %s: %s"
                % (self.tag, path, type(exc).__name__, exc)) from None

        # INI 형식의 역슬래시·인용부호를 Archon 형식으로 (labtest 그대로).
        self.config = {}
        self.configline = {}
        for i, (key, value) in enumerate(items):
            k = key.upper().replace('\\', '/')
            self.config[k] = value.replace('"', '')
            self.configline[k] = i
        self.acf_path = path
        log.info('%s: ACF 파싱 %d줄 -- %s', self.tag, len(self.config), path)

    async def apply_acf(self, path: str) -> None:
        """ACF 를 컨트롤러에 밀어 넣고 적용한다 (`CLEARCONFIG`+`WCONFIG`+`APPLYALL`).

        설정 줄이 수천 개라 왕복마다 기다리면 몇 분이 걸린다 -- labtest 처럼
        **몰아 보내고 몰아 받는다** (`ArchonLink.pipeline`).  실패하면 연결을
        다시 세우고 재시도한다.
        """
        self.parse_acf(path)
        keys = list(self.config)
        cmds = ['WCONFIG%04X%s=%s' % (self.configline[k], k, self.config[k])
                for k in keys]

        last: Exception | None = None
        for attempt in range(max(self.cfg.acf_retry, 1)):
            try:
                async with self._lock:
                    def _push() -> None:
                        self.link.command('CLEARCONFIG', timeout=T_APPLY)
                        self.link.pipeline(cmds, timeout=T_APPLY)
                    await asyncio.to_thread(_push)
                await self.cmd('APPLYALL', timeout=T_APPLY)
            except (ArchonError, TimeoutError, OSError) as exc:
                if isinstance(exc, ArchonError) and exc.reply_error:
                    # **컨트롤러가 거부한 것이다 -- 연결 문제가 아니다.**  같은
                    # 설정을 다시 밀면 같은 거부가 돌아오고, 그 사이 재접속을
                    # 되풀이하면 원인이 "망이 불안하다" 로 오인된다.
                    raise ArchonError(
                        '%s: 컨트롤러가 ACF 적용을 거부했다 (%s) -- 설정 내용을 '
                        '확인하라.  재시도·재접속하지 않는다' % (self.tag, exc),
                        cmd=exc.cmd, reply_error=True) from None
                last = exc
                log.warning('%s: ACF 적용 실패 %d/%d (%s) -- 연결을 다시 '
                            '세우고 재시도한다', self.tag, attempt + 1,
                            max(self.cfg.acf_retry, 1), exc)
                async with self._lock:
                    await asyncio.to_thread(self.link.resync, 'ACF 적용 실패')
                await asyncio.sleep(1.0)
                continue
            self.acf_applied = True
            log.info('%s: ACF 적용 완료 -- %s', self.tag, path)
            return
        raise ArchonError('%s: ACF 를 적용할 수 없다 (%s)' % (self.tag, last))

    async def set_config(self, key: str, value: str) -> None:
        """설정 줄 하나를 다시 쓴다 (labtest `SetConfig`).

        **줄 번호는 ACF 파싱에서 온다.**  파싱을 안 했으면 어느 줄을 고칠지
        모른다 -- `apply_acf=false` 로 두고 이미 적용된 설정을 쓰는 경우에도
        파일은 읽어 둔다 (`prepare()`).
        """
        k = key.upper().replace('\\', '/')
        line = self.configline.get(k)
        if line is None:
            raise ArchonError(
                "%s: 설정 줄 '%s' 을 모른다 -- ACF 를 먼저 파싱해야 한다 "
                '(현재 ACF %r)' % (self.tag, key, self.acf_path or '없음'))
        self.config[k] = value
        await self.cmd('WCONFIG%04X%s=%s' % (line, k, value), timeout=T_FAST)

    async def verify_config_lines(self, keys) -> list[str]:  # noqa: ANN001
        """`RCONFIG` 로 줄 번호 대응이 맞는지 확인한다.  어긋난 키 목록을 돌려준다.

        **`apply_acf=false` 의 안전장치다.**  파일에서 얻은 줄 번호가 컨트롤러
        메모리의 실제 배치와 다르면, `set_config('PARAMETER2', 'IntMS=…')` 가
        **엉뚱한 줄을 고친다** -- 그러면 노출 시간이 안 바뀌는데 오류도 안 난다.
        기동에서 한 번 대조해 두면 그 침묵을 없앨 수 있다.
        """
        bad = []
        for key in keys:
            k = key.upper().replace('\\', '/')
            line = self.configline.get(k)
            if line is None:
                bad.append(key)
                continue
            try:
                got = (await self.cmd('RCONFIG%04X' % line, timeout=T_FAST)
                       ).decode('ascii', 'replace')
            except ArchonError as exc:
                log.warning('%s: RCONFIG%04X 실패 (%s) -- 대조를 건너뛴다',
                            self.tag, line, exc)
                continue
            if not got.upper().startswith(k + '='):
                log.error('%s: 설정 줄 %04X 가 %s 가 아니다 -- 받은 것 %r.  '
                          'ACF 파일과 컨트롤러 메모리가 다르다 (apply_acf 를 '
                          'true 로 두거나 같은 ACF 를 쓰라)',
                          self.tag, line, k, got[:60])
                bad.append(key)
        return bad

    # -- 전원 -------------------------------------------------------------

    async def power_on(self, wait: float | None = None) -> None:
        """CCD 입력 클록·바이어스 전원 ON + flush 대기.

        **"보냈다" 를 보내기 전에 기록한다.**  응답을 잃어도(시한 초과·망 끊김)
        컨트롤러는 이미 전원을 올렸을 수 있다 -- 그때 `powered=False` 로 남으면
        `shutdown()` 이 `POWEROFF` 를 건너뛰고 **바이어스가 걸린 채로 프로그램이
        끝난다**(검출기 쪽 위험, 규약 11).  확인된 상태(`powered`)와 시도한
        사실(`power_attempted`)을 갈라 두면 종료는 안전한 쪽으로, 재준비는
        확인된 쪽으로 판단할 수 있다.
        """
        self.power_attempted = True
        await self.cmd('POWERON', timeout=T_POWER)
        self.powered = True
        delay = self.cfg.poweron_wait if wait is None else wait
        if delay > 0:
            log.info('%s: POWERON -- CCD flush %.1f초 대기', self.tag, delay)
            await asyncio.sleep(delay)

    async def power_off(self) -> None:
        """전원 OFF.  **실패해도 예외를 올리지 않는다.**

        이것을 부르는 자리는 대개 `finally` 다 -- 여기서 예외를 내면 원래
        원인이 가려진다.  전원을 켠 채로 프로그램이 죽는 것은 검출기 쪽
        위험이므로, 못 껐다는 사실만 크게 알린다.
        """
        try:
            await self.cmd('POWEROFF', timeout=T_POWER)
        except (ArchonError, TimeoutError, OSError) as exc:
            log.error('%s: POWEROFF 를 못 보냈다 (%s) -- 유닛 전원 상태를 '
                      '직접 확인하라', self.tag, exc)
            return
        self.powered = False
        self.power_attempted = False

    # -- 스냅샷 -----------------------------------------------------------

    async def refresh_system(self) -> None:
        """`SYSTEM` 스냅샷 (`CTRLnID`/`CTRLnSN` 의 원천).  실패는 경고만."""
        try:
            self.system = await self.query('SYSTEM', timeout=T_FAST)
        except (ArchonError, TimeoutError, OSError) as exc:
            log.warning('%s: SYSTEM 질의 실패 (%s) -- 컨트롤러 정체는 ini '
                        '값이나 sentinel 로 실린다', self.tag, exc)

    async def refresh_status(self) -> None:
        """`STATUS` 스냅샷 (`Cn_TEMP/VOLT/CURR` 의 원천).

        **노출 개시 전에 부른다.**  fetch 뒤에 두면 컨트롤러가 답하지 않을 때
        다 읽어낸 노출을 잃는다 (labtest 가 v1.1 에서 옮긴 자리).
        """
        if not self.telemetry_enabled:
            return
        try:
            self.status = await self.query('STATUS',
                                          timeout=self.cfg.status_timeout)
            self._check_health()
        except (ArchonError, TimeoutError, OSError) as exc:
            self.telemetry_enabled = False
            # **낡은 스냅샷을 반드시 버린다.**  안 버리면 `controller_telemetry()`
            # 가 앞 프레임의 값을 읽어 **지금 잰 값처럼** 헤더에 싣는다 --
            # 텔레메트리는 이 실행 동안 다시 갱신되지 않으므로 그 뒤의 모든
            # 프레임이 같은 온도·전압을 달고 나가고, 파일만 봐서는 언제 잰
            # 값인지 알 길이 없다.  "물어봤는데 실패" 는 `NC` 여야 한다
            # (`parse.telemetry_of` 가 빈 dict 를 그렇게 만든다).
            self.status = {}
            log.warning('%s: STATUS 질의 실패 (%s) -- 이 실행 동안 텔레메트리를 '
                        '끈다.  Cn_* 는 NC 로 실린다', self.tag, exc)

    def _check_health(self) -> None:
        """`STATUS` 응답에서 전원·과열 이상을 읽어 알린다 (F2).

        **막지는 않는다.**  이 필드들은 아직 실기 미검증(PROVISIONAL)이라,
        오독 하나로 관측을 통째로 세우는 쪽이 더 나쁘다 -- 첫 실행에서
        `tools/probe_archon.py` 1단계가 같은 값을 눈으로 확인한다.  대신 원인이
        보이도록 크게 남긴다: 종전에는 전원 이상이 밖에서 "취득 실패" 로만
        보였다.
        """
        bad = parse.health_problems(self.status)
        if not bad:
            self._health_bad = False
            return
        if not self._health_bad:
            self._health_bad = True
            log.error('%s: 컨트롤러 상태 이상 -- %s.  이 상태의 프레임은 '
                      '자료가 아니라 잔해일 수 있다 (매뉴얼 p.47)',
                      self.tag, ' / '.join(bad))

    async def frame(self) -> parse.FrameStatus:
        return parse.newest(await self.query('FRAME', timeout=T_FAST))

    # -- 셔터 트리거 ------------------------------------------------------

    async def set_trigger_forced(self, forced: bool) -> None:
        """`TRIGOUTFORCE` -- 셔터/광원 트리거 라인을 강제할지.

        Archon 은 셔터를 **Trigger Out 이 INT 클록을 따르게 해서** 구동한다
        (매뉴얼 p.15).  그래서 `TRIGOUTFORCE=0` 이 "타이밍 스크립트가 몬다"
        (= 셔터 노출), `1` 이 "`TRIGOUTLEVEL` 로 고정" (= 열지 않는다) 이다.
        labtest 의 `shopen` 분기가 정확히 이 두 값이다.
        """
        await self.set_config('TRIGOUTFORCE', '1' if forced else '0')
        await self.cmd('APPLYSYSTEM', timeout=T_SYSTEM)

    # -- 노출 -------------------------------------------------------------
    #
    # **프레임 상태는 프레임이 들고 간다 (`FrameTicket`).**  컨트롤러 필드에
    # 두면 파이프라인이 겹칠 때 뒤 프레임이 앞 프레임의 값을 덮는다 -- 저장은
    # `write_delay` 뒤에 백그라운드로 돌고 그 사이 다음 프레임이 이미
    # `LOADPARAMS` 를 냈을 수 있다.  그러면 앞 프레임의 저장이 "직전 프레임
    # 번호" 를 잘못 알고, 반대로 앞 프레임의 뒷정리가 뒤 프레임의 "노출을
    # 걸었다" 표시를 지운다(-> 이중 노출).
    #
    # `ics_sim` 이 같은 부류를 두 번 겪었다 -- 파일 일련번호 경합(12.10)과
    # D-016 선검사의 채널 suffix 재읽기(11.20 critical).  결론은 매번 같았다:
    # **프레임의 것은 프레임이 정하고, 나중에 다시 읽지 않는다.**

    async def trigger(self, exptime_ms: int, *, queue: bool = True,
                      suffix: str = '') -> FrameTicket:
        """노출 1회를 걸고 곧바로 돌아온다 (적분·독출은 컨트롤러가 몬다).

        순서는 labtest 그대로다 -- **프레임 번호를 먼저 읽고** `IntMS`,
        `Exposures=1`, `LOADPARAMS`.  번호를 먼저 읽는 이유는 그 값이 "새
        프레임이 나왔나" 의 기준이기 때문이다.

        Args:
            queue: 저장 대기열에 넣을지.  flush 는 **버리는 프레임**이라
                `False` 다 -- 넣으면 저장 쪽이 그것을 자기 프레임으로 집어 온다.
            suffix: 이 프레임의 이름 (`<YYYYMMDD>.<NNNNNN>`).  저장 쪽이 **자기
                프레임의 표를 골라 집는** 근거다.
        """
        prev = (await self.frame()).frame
        await self.set_config(self.cfg.param_intms_slot,
                              '%s=%d' % (self.cfg.param_intms_name,
                                         max(int(exptime_ms), 0)))
        await self.set_config(self.cfg.param_exposures_slot,
                              '%s=1' % self.cfg.param_exposures_name)
        await self.cmd('LOADPARAMS', timeout=T_SYSTEM)
        ticket = FrameTicket(
            suffix=suffix,
            prev_frame=prev,
            int_until=(time.monotonic() + exptime_ms / 1000.0
                       if exptime_ms > 0 else None))
        self._current = ticket
        if queue:
            self._queue.append(ticket)
        log.info('%s: 노출 지시 -- IntMS=%d (프레임 %d 다음%s)',
                 self.tag, int(exptime_ms), prev, '' if queue else ', 버림')
        return ticket

    @property
    def triggered(self) -> bool:
        """**이번 프레임**의 노출이 이미 걸렸나 (flush 는 해제한다)."""
        return self._current is not None

    @property
    def current_ticket(self) -> FrameTicket | None:
        """진행 중 프레임의 표.  `readout()` 이 이것을 기다린다."""
        return self._current

    @property
    def integrating(self) -> bool:
        """컨트롤러가 아직 적분 중이라고 볼 수 있나 (호스트 시각 기준)."""
        t = self._current
        return (t is not None and t.int_until is not None
                and time.monotonic() < t.int_until)

    @property
    def integration_left(self) -> float:
        """남은 적분 시간 [s] (호스트 시각 기준).  적분 중이 아니면 0.

        `close_shutter()` 가 "조기 종료인가" 를 이 값으로 판단한다 --
        참/거짓만 보면 정상 경로의 종료 순간과 구별할 수 없다.
        """
        t = self._current
        if t is None or t.int_until is None:
            return 0.0
        return max(t.int_until - time.monotonic(), 0.0)

    def release_current(self) -> None:
        """이번 프레임의 노출·독출이 끝났음을 표시한다.

        저장 대기열은 건드리지 않는다 -- 그쪽은 `take_ticket()` 이 FIFO 로
        가져간다.  이것을 안 해 주면 다음 프레임의 `readout()` 이 "이미
        걸렸다" 고 보고 노출을 안 건다.
        """
        self._current = None

    def take_ticket(self, suffix: str = '') -> FrameTicket | None:
        """저장 대기열에서 **내 프레임의** 표를 가져온다.

        `suffix` 를 주면 그 이름의 표를 찾고, **그보다 앞선 표는 버린다** --
        앞선 표가 아직 남아 있다는 것은 그 프레임이 취소되거나 저장에 실패해
        아무도 꺼내지 않았다는 뜻이다.  FIFO 로 그냥 집으면 이 파일이 **그
        프레임의 픽셀**을 담고 헤더는 내 것이 된다 (경고 0).

        `suffix` 가 비면 종전처럼 FIFO -- 시험용 경로다.
        """
        if not self._queue:
            return None
        if not suffix:
            return self._queue.pop(0)
        for i, t in enumerate(self._queue):
            if t.suffix == suffix:
                dropped = self._queue[:i]
                del self._queue[:i + 1]
                if dropped:
                    log.warning(
                        '%s: 저장되지 않은 프레임 표 %d개를 버린다 (%s) -- '
                        '그 프레임은 취소되거나 저장에 실패했다.  내 프레임(%s)의 '
                        '표를 집는다', self.tag, len(dropped),
                        ', '.join(d.suffix or '?' for d in dropped), suffix)
                return t
        # 내 표가 없다 -- 대기열에 남은 것은 전부 남의 것이므로 집지 않는다.
        log.error('%s: 프레임 %s 의 저장 표가 없다 (대기열: %s) -- 이 프레임은 '
                  '저장하지 않는다', self.tag, suffix,
                  ', '.join(t.suffix or '?' for t in self._queue) or '비어 있음')
        return None

    def drop_tickets(self, why: str) -> int:
        """대기열을 비운다.  버린 개수를 돌려준다 (진단용).

        프레임이 끊겨 저장이 없을 것이 확실할 때 부른다.
        """
        n = len(self._queue)
        if n:
            log.warning('%s: 저장 표 %d개를 버린다 (%s)', self.tag, n, why)
            self._queue.clear()
        return n

    async def flush(self, poll: float | None = None) -> None:
        """전체 독출 flush (labtest `bFullFlush`) -- 프레임 하나를 버린다.

        `IntMS=0` 으로 노출을 걸어 축적된 전하를 읽어내고 그 프레임을 쓰지
        않는다.  레거시 `ERASE` 의 자리이고, 걸리는 시간은 **독출 1회분**이다
        (레거시 실측 7.24초는 IC 구현 값이라 실기와 다르다 -- 실측 대상).
        """
        ticket = await self.trigger(0, queue=False)
        async for _pct in self.wait_frame(ticket, poll=poll):
            pass
        self.release_current()
        log.info('%s: flush 완료 (프레임 %d 버림)', self.tag,
                 ticket.ready.frame if ticket.ready else -1)

    async def wait_frame(self, ticket: FrameTicket,
                         poll: float | None = None):  # noqa: ANN201
        """그 프레임이 완료될 때까지 기다리며 **진행률을 yield** 한다.

        진행률은 `FRAME` 의 `BUFnLINES`/`BUFnHEIGHT` 다 (매뉴얼 p.50).  적분
        중에는 쓰기 버퍼가 없어 `None` 이 나오므로 아무것도 내지 않는다 --
        `PCTREAD=` 는 독출 진행이라야 뜻이 있다.

        마지막에 **100 을 내지 않는다** -- 완료 통보는 부르는 쪽(`readout()`)의
        몫이고, 그 쪽이 시퀀서 규약(`pctread_final`)을 안다.  완료된 프레임은
        `ticket.ready` 에 담긴다.
        """
        if ticket.ready is not None:
            return
        interval = self.cfg.frame_poll if poll is None else poll
        # **최소 1 이다.**  0 이면 폴링마다 같은 값을 되풀이해 보내게 되고
        # (폴링이 라인 진행보다 빠르다), 그건 와이어 소음일 뿐이다.  0 은
        # "값이 바뀔 때마다" 로 읽는다.
        step = max(int(self.cfg.progress_step), 1)
        reported = -1
        prev = ticket.prev_frame
        limit = float(getattr(self.cfg, 'frame_timeout', 0.0) or 0.0)
        deadline = (time.monotonic() + limit) if limit > 0 else None
        while True:
            if deadline is not None and time.monotonic() > deadline:
                # **영구 대기를 오류로 바꾼다.**  독출이 시작되지 않으면
                # `EXPSTATUS=READOUT` 에 갇혀 관측자 화면이 멈추고 OBSAgent 가
                # `force_idle` 타임아웃으로 `opause` 에 빠진다 -- 조용한 정지가
                # 가장 나쁜 실패다.
                raise ArchonError(
                    '%s: 프레임 %d 이 %.0f초 안에 나오지 않았다 -- 독출이 '
                    '시작되지 않았을 수 있다(ACF·클록·LOADPARAMS 를 보라). '
                    '[archon] frame_timeout 으로 상한을 조정한다'
                    % (self.tag, prev + 1, limit), cmd='FRAME')
            fields = await self.query('FRAME', timeout=T_FAST)
            # **"내 다음 프레임" 을 찾는다** -- "최신 프레임" 이 아니다.  저장이
            # 늦으면 그 사이 프레임이 더 나와 있고, 최신 것을 집으면 이 파일이
            # **남의 노출 픽셀**을 담는다(헤더는 이 프레임의 것이라 아무 경고도
            # 없다).
            mine = parse.next_frame(fields, prev)
            if mine is not None:
                # **첫 실행(prev < 0)에는 번호를 못박지 않는다** -- 프레임이
                # 하나도 없으면 `newest()` 가 -1 을 주고, 컨트롤러의 첫 프레임
                # 번호가 1 이면 "0 을 지나쳤다" 가 되어 첫 노출을 버린다.
                if prev >= 0 and mine.frame != prev + 1:
                    raise ArchonError(
                        '%s: 프레임 %d 을 지나쳤다 (찾은 것은 %d) -- 그 버퍼가 '
                        '이미 덮였다.  저장이 다음 노출보다 늦었다는 뜻이니 '
                        'write_delay·독출 시간과 버퍼 수(BIGBUF 는 2개)를 보라'
                        % (self.tag, prev + 1, mine.frame), cmd='FRAME')
                ticket.ready = mine
                return
            pct = parse.newest(fields).progress
            if pct is not None and pct >= reported + step:
                reported = pct
                yield pct
            await asyncio.sleep(interval)

    async def await_frame(self, ticket: FrameTicket) -> parse.FrameStatus:
        """그 프레임의 완료를 기다린다 (진행률은 버린다).

        **저장 쪽이 부른다.**  진행률을 흘려보내는 것은 master 컨트롤러 하나뿐
        이므로(시퀀서가 `readout(master)` 만 부른다) 다른 대의 프레임은 아무도
        기다려 주지 않는다 -- 그 대의 `write_frame()` 이 여기서 기다린다.
        """
        async for _pct in self.wait_frame(ticket):
            pass
        if ticket.ready is None:                     # pragma: no cover
            raise ArchonError('%s: 완료 프레임을 확인하지 못했다' % self.tag)
        return ticket.ready

    # -- FETCH ------------------------------------------------------------

    async def fetch(self, fs: parse.FrameStatus,
                    expect_bytes: int) -> bytearray:
        """프레임 데이터를 받아 온다.  **선언 기하와 다르면 받지 않는다.**

        대조를 fetch **앞**에 둔 것이 요점이다 -- fetch 는 수십 초가 걸리고,
        그 뒤에 거절하면 그 시간을 버린다.  그리고 픽셀 수가 아니라 **바이트
        수**로 대조한다: `samplemode`(32bit 표본)는 기하가 선언과 같은데도
        정확히 2배가 되므로 픽셀 비교로는 안 잡힌다 (DevNote 11.22 (3)).

        패딩까지 넣고 나면 그 어긋남이 astropy 에서 `Header missing END card`
        로 나와 **파일 전체를 못 읽게** 된다 -- 여기서 막는 것이 값싸다.
        """
        if fs.data_bytes != expect_bytes:
            raise ArchonError(
                '%s: 프레임이 %d B (%dx%d, %s) 인데 선언 기하는 %d B 다 -- '
                'fetch 하지 않는다.  ACF 기하와 samplemode 를 확인하라.'
                % (self.tag, fs.data_bytes, fs.width, fs.height,
                   'samplemode/32bit' if fs.samplemode else '16bit',
                   expect_bytes), cmd='FETCH')

        # **버퍼를 잠근다** (`LOCKn`, 매뉴얼 p.50).  BIGBUF 는 버퍼가 둘뿐이고
        # 노출 1회가 프레임 2개(flush + 취득)를 만들므로, **다음 노출이 이
        # 프레임의 버퍼를 덮는다.**  저장은 `write_delay` 뒤에 백그라운드로
        # 도는 일이라 그 경합이 실재한다 -- 덮인 뒤에 fetch 하면 raw 한 장이
        # **남의 노출 픽셀**을 담고, 헤더는 이 프레임의 것이라 아무 경고도 없다.
        #
        # ⚠️ labtest 는 2026-05-28 에 `LOCK` 을 뺐다("remove to fetch debug").
        # 되돌린 것이므로 **실기 확인 항목**이다 -- 문제가 보이면
        # `[archon] lock_buffer = false` 로 끄면 labtest 와 같아진다.  끄더라도
        # 아래 대조는 남으므로 조용히 틀린 파일이 나오지는 않는다.
        buf_n = fs.buf + 1
        lock = getattr(self.cfg, 'lock_buffer', True)
        if lock:
            await self.cmd('LOCK%d' % buf_n, timeout=T_FAST)
        try:
            # **잠근 뒤에 다시 확인한다.**  잠그기 직전에 이미 덮였을 수 있다.
            live = parse.buffer_frame(
                await self.query('FRAME', timeout=T_FAST), buf_n)
            if live != fs.frame:
                raise ArchonError(
                    '%s: 버퍼 %d 가 프레임 %d 로 덮였다 (내 프레임은 %d) -- '
                    'fetch 하지 않는다.  저장이 다음 노출보다 늦었다는 뜻이니 '
                    'write_delay·독출 시간을 보라 (lock_buffer=%s)'
                    % (self.tag, buf_n, live, fs.frame, lock), cmd='FETCH')

            # 상한은 크기에서 뽑는다 -- 1 GB/s 를 밑도는 어떤 링크라도 넉넉하고,
            # 그러면서 "영구히 멈춤" 은 막는다.  실측 MiB/s 가 나오면
            # `[archon] fetch_timeout` 으로 조인다 (F5) -- 이 유도값은
            # `frame_timeout` 과 **별개의 상한**이라 한쪽만 조여도 다른 쪽은
            # 그대로다.
            timeout = float(getattr(self.cfg, 'fetch_timeout', 0.0) or 0.0)
            if timeout <= 0:
                timeout = max(60.0, expect_bytes / (1 << 20) * 1.0)
            started = time.monotonic()
            async with self._lock:
                data = await asyncio.to_thread(
                    self.link.fetch, fs.base, expect_bytes, timeout)
        finally:
            if lock:
                try:
                    await self.cmd('LOCK0', timeout=T_FAST)
                except (ArchonError, TimeoutError, OSError) as exc:
                    # **풀지 못하면 다음 노출이 버퍼를 못 쓴다** -- 크게 알린다.
                    log.error('%s: LOCK0(잠금 해제)에 실패했다 (%s) -- 다음 '
                              '프레임이 버퍼를 못 쓸 수 있다', self.tag, exc)
        log.info('%s: FETCH %.1f MiB, %.1f초 (프레임 %d, buf %d, base 0x%08X)',
                 self.tag, expect_bytes / (1 << 20),
                 time.monotonic() - started, fs.frame, buf_n, fs.base)
        return data

    # -- 준비 -------------------------------------------------------------

    async def prepare(self) -> None:
        """첫 노출 앞에 한 번 -- 연결 · ACF · 전원 · `SYSTEM` 스냅샷.

        **멱등하다.**  시퀀서는 프레임마다 CCD 별로 `initialize()` 를 부르므로
        (컨트롤러 하나당 2회) 여기서 걸러 준다.  ACF 적용(`APPLYALL`)은 초
        단위가 걸려 프레임마다 되풀이할 수 없다.
        """
        if not self.link.connected:
            await self.connect()
        acf = self.cfg.acf.get(self.tag, '')
        if acf and not self.acf_applied:
            if self.cfg.apply_acf:
                await self.apply_acf(acf)
            else:
                # 적용은 건너뛰지만 **파싱은 한다** -- 줄 번호가 없으면
                # 파라미터를 못 바꾼다.  그리고 그 줄 번호가 컨트롤러 메모리와
                # 맞는지 대조한다(어긋나면 노출 시간이 조용히 안 바뀐다).
                self.parse_acf(acf)
                self.acf_applied = True
                bad = await self.verify_config_lines(
                    (self.cfg.param_intms_slot, self.cfg.param_exposures_slot))
                if bad:
                    raise ArchonError(
                        '%s: apply_acf=false 인데 설정 줄 대응이 어긋났다 (%s) '
                        '-- 같은 ACF 를 쓰거나 apply_acf=true 로 두라'
                        % (self.tag, ', '.join(bad)))
        if not self.powered:
            await self.power_on()
        if not self.system:
            await self.refresh_system()
            self._log_module_map()

    def _log_module_map(self) -> None:
        """슬롯별 모듈 형을 한 번 찍는다 -- `TEMP_SLOTS` 가정의 실기 확인."""
        mods = parse.module_types(self.system)
        if not mods:
            return
        shown = ', '.join(
            '%d:%s' % (s, parse.MODULE_TYPES.get(t, '?%d' % t))
            for s, t in sorted(mods.items()) if t)
        ad = [s for s, t in mods.items() if t in parse.AD_TYPES]
        log.info('%s: 모듈 %s', self.tag, shown)
        if sorted(ad) != [5, 6, 7, 8]:
            log.warning('%s: AD(비디오) 모듈이 슬롯 %s 에 있다 -- parse.'
                        'TEMP_SLOTS 는 5~8 을 전제한다.  Cn_TEMP 의 자리가 '
                        '어긋날 수 있으니 목록을 고칠 것', self.tag, sorted(ad))

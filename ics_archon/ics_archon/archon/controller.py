#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""컨트롤러 한 대의 제어 시퀀스 -- ACF 적용 · 전원 · 노출 · 독출 · FETCH.

원형은 실험실 취득 스크립트의 `GetDataset()`/`Exposure()` 다.  **제어 시퀀스
자체(CLEARCONFIG/WCONFIG -> APPLYALL -> POWERON -> LOADPARAMS -> FRAME 폴링 ->
FETCH)는 v1.0 계보로 1년 실사용 검증된 것**이므로 순서와 명령을 바꾸지 않았다
(⚠️ `APPLYALL` 이 `POWERON` 앞이다 -- 매뉴얼 p.51 *"An APPLYALL is required
before this operation"*, 실기 `?02` 거부로 확인 2026-09-01, DevNote 10.2).
바꾼 것은
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
    #: 노출 지시 **직전**의 세 버퍼 번호 -- 되감김·재시작 판별의 기준선.
    #:
    #: 번호 하나(`prev_frame`)만으로는 **카운터가 뒤로 간 경우**를 못 가른다:
    #: 평소에도 옛 프레임을 담은 버퍼가 그보다 작은 번호를 들고 있다.  "어느
    #: 자리가 **새로 바뀌었나**" 를 보려면 기준선이 있어야 한다
    #: (`parse.restarted_frame`).  ⭐ 이것도 **표가 들고 간다** -- 컨트롤러
    #: 필드에 두면 파이프라인이 겹칠 때 뒤 프레임이 앞 프레임의 기준선을
    #: 덮는다 (이 클래스가 있는 이유 그대로다).
    prev_frames: tuple[int, ...] = ()
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

#: `POWERON` 뒤 `POWER` 를 다시 물어보는 간격 [s].
#:
#: **`poweron_wait` 를 줄이지 않는다** -- 그 시간은 전원 램프가 아니라 **CCD
#: flush** 를 기다리는 것이라(labtest 24 x 0.5), `POWER=4` 를 봤다고 일찍
#: 빠져나오면 첫 프레임이 flush 가 덜 된 상태로 나간다.  여기서 하는 것은 그
#: 대기 **안에서** 전원이 실제로 올라왔는지 확인하는 것뿐이다.
T_POWER_POLL = 1.0


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

        #: **수신·저장 버퍼 링** (`[archon] fetch_buffers`, 기본 2).
        #:
        #: FETCH 가 하나를 빌려 채우고 **저장이 끝난 뒤** 돌려준다
        #: (`release_buffer`).  종전에는 프레임마다 344 MiB 를 새로 잡았고
        #: 저장 태스크 수에 제한이 없어서, 저장이 밀리면 **메모리가 조용히
        #: 늘었다.**  링으로 두면 상한이 `N x 344 MiB` 로 고정된다.
        #:
        #: 큐에는 처음에 `None` 슬롯만 넣는다 -- **실제 버퍼는 처음 쓸 때
        #: 만든다.**  상한은 슬롯 수가 보장하고, 기동은 가벼운 채로 둔다.
        self._bufpool: asyncio.Queue = asyncio.Queue()
        for _ in range(max(1, int(getattr(cfg, 'fetch_buffers', 2)))):
            self._bufpool.put_nowait(None)
        #: 버퍼가 없어 기다린 횟수·시간.  ⭐ **`fetch_buffers` 가 충분한지를
        #: 추정이 아니라 실기가 답하게 하는 자리다** -- 0 이면 충분한 것이고,
        #: 쌓이면 올려야 한다.
        self.buf_waits = 0
        self.buf_wait_s = 0.0

        #: 마지막 fetch 에서 관측한 **잠금 상태** (진단용, 1-기준.  -1 = 미관측).
        #:
        #: ⭐ `LOCKn` 이 FW 에 반영되는지의 관측값.  ✅ **2026-09-01 두 FW
        #: (1252·1261) 15/15 반영** (DevNote 10.4, A-5 판단 ② 종결) -- 이제는
        #: FW 가 바뀌었을 때의 **회귀 감시**다.  fetch 앞의 덮임 대조에서
        #: **이미 읽는 `FRAME` 응답**에서 뽑으므로 왕복이 늘지 않는다.
        #: - `lock_rbuf` -- `LOCKn` 뒤의 `RBUF`.  `buf_n` 과 같으면 반영된 것
        #: - `lock_wbuf` / `lock_wbuf_after` -- fetch **전후**의 `WBUF`.
        #:   ⭐ 옮겨 갔으면 **엔진이 실제로 다른 버퍼를 썼다**는 거동 증거다
        #:   (매뉴얼 p.71 의 *"다음 잠기지 않은 버퍼"*).
        self.lock_rbuf = -1
        self.lock_wbuf = -1
        self.lock_wbuf_after = -1

        #: ACF 설정 줄 -> 내용, 그리고 키 -> 줄 번호.  `WCONFIG` 는 줄 번호로
        #: 쓰므로 이 대응이 없으면 파라미터를 못 바꾼다.
        self.config: dict[str, str] = {}
        self.configline: dict[str, int] = {}
        #: ACF `LINECOUNT` -- 진행률(`PCTREAD`)의 분모.  `BUFnHEIGHT` 는 split
        #: 에서 두 배라 못 쓴다 (DevNote 10.3).  0 이면 HEIGHT 로 물러난다.
        self.lines_total: int = 0
        #: 이번 `trigger()` 의 `LOADPARAMS` 가 실제로 나갔나 -- 취소가 그 앞에서
        #: 왔으면 컨트롤러는 유휴라 꼬리가 없다 (guide `_settle`, DevNote 9.15-(9)).
        self.loadparams_sent: bool = False
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
        #: **살아 있는 스냅샷** -- 배경 감시가 계속 갱신한다 (층 1·2, 2026-08-28).
        #:
        #: ⚠️ **`status` 와 갈라 둔 것이 핵심이다.**  `Cn_TEMP/VOLT/CURR` 의 뜻은
        #: "노출 개시 시점 값" 이고, 그것은 `status` 가 `initialize()` 에서 언
        #: 뒤 아무도 안 건드리기 때문에 성립한다.  감시가 `status` 를 계속
        #: 덮으면 헤더 스냅샷이 굳는 순간에 잡히는 것은 **마지막 폴링 값**이 되고
        #: -- 독출이 모듈을 데우므로 값이 다르다 -- **폴링 간격·락 경합에 따라
        #: 노출마다 달라져 비결정적**이 된다.  카드의 뜻이 조용히 바뀌는 부류다.
        #:
        #: | 자리 | 갱신 | 소비자 |
        #: |---|---|---|
        #: | `status` | 노출 개시에 **언 것** | `controller_telemetry()` -> 헤더 전용 |
        #: | `status_live` | 감시가 계속 | 기록 · ICS `STATUS` 응답 · 건강검사 |
        self.status_live: dict[str, str] = {}
        #: `status_live` 를 뜬 시각 (`time.time()`, UTC epoch).  0 이면 아직 없다.
        #: 기록의 `age_ms` 열이 이것으로 계산된다 -- **"이 값이 몇 초 전 것인가"**
        #: 를 함께 싣지 않으면 신선도가 전달 계층에서 사라진다.
        self.status_live_at: float = 0.0
        #: 감시 폴링이 **연달아** 실패한 횟수.  성공하면 0 으로 돌아간다.
        #:
        #: ⚠️ **`telemetry_enabled` 와 별개다** (반드시 지킬 것 2).  그 래치는
        #: "한 번 실패하면 이 실행 동안 헤더용으로 안 묻는다" 이고(F8), 감시가
        #: 재시도하며 그것을 다시 켜면 **취득 경로의 판단이 감시 쪽 사정으로
        #: 뒤집힌다.**  감시는 자기 카운터로 백오프하고 헤더용 래치는 만지지
        #: 않는다.
        self.status_live_fails: int = 0
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

    async def _locked_thread(self, fn, *args):  # noqa: ANN001, ANN201
        """`_lock` 을 쥔 채 블로킹 링크 왕복을 스레드로 돌린다.

        ⭐ **취소돼도 스레드가 끝날 때까지 락을 놓지 않는다** (2026-09-02,
        DevNote 9.15-(9)).  종전 `async with self._lock: await
        asyncio.to_thread(...)` 는 `CancelledError` 에 `async with` 를 빠져
        나오며 락을 풀었는데, 스레드는 취소되지 않아 **소켓 왕복이 아직 진행
        중**이었다 -- 다음 명령(예: ABORT 뒤의 `Exposures=0`)이 같은 소켓에
        끼어들어 응답 번호가 어긋나고 링크가 깨졌다 (가짜에서 10회 중 1회,
        `STATUS` 지연 0.2초로는 20회 중 14회 재현).  `asyncio.to_thread` 는
        어차피 끊을 수 없으니 **끝나기를 기다리는 것**이 유일한 정답이다 --
        링크 시한(`timeout`)이 그 대기를 묶는다.
        """
        async with self._lock:
            fut = asyncio.ensure_future(asyncio.to_thread(fn, *args))
            try:
                return await asyncio.shield(fut)
            except asyncio.CancelledError as first:
                # 스레드가 소켓을 놓을 때까지 락을 쥔다.  ⭐ **두 번째 취소도
                # 흡수한다** -- ABORT 위에 종료가 겹치는 것이 정상 운용이고
                # (2차 반증: 6회 중 3회 재현), 대기는 링크 시한이 묶는다.
                while not fut.done():
                    try:
                        await asyncio.wait({fut})
                    except asyncio.CancelledError:
                        pass
                if not fut.cancelled():
                    fut.exception()          # "never retrieved" 경고 방지
                raise first

    async def cmd(self, command: str, timeout: float = T_FAST) -> bytes:
        """텍스트 명령 하나.  실패하면 `ArchonError`.

        시한 초과는 **연결 재수립**으로 이어진다 -- 참조번호를 미리 올려
        두어(`protocol.py` 3번) 늦은 응답이 다음 명령에 먹히지는 않지만,
        부분 수신분이 소켓에 남는 문제는 그대로다.
        """
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
        return await self._locked_thread(_run)

    async def query(self, command: str, timeout: float = T_FAST
                    ) -> dict[str, str]:
        """`KEY=VALUE` 나열을 돌려주는 질의 (`SYSTEM`/`STATUS`/`FRAME`)."""
        return parse.keyvals(await self.cmd(command, timeout))

    # -- 연결 -------------------------------------------------------------

    async def connect(self) -> None:
        if not self.cfg.hosts.get(self.tag):
            raise ArchonError('%s: [archon] ctrl_%s_host 가 비어 있다'
                              % (self.tag, self.tag.lower()))
        await self._locked_thread(self.link.connect, self.cfg.connect_retry)

    async def close(self) -> None:
        await self._locked_thread(self.link.close)

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
        try:
            self.lines_total = int(self.config.get('LINECOUNT', '0') or 0)
        except ValueError:
            self.lines_total = 0
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
                def _push() -> None:
                    self.link.command('CLEARCONFIG', timeout=T_APPLY)
                    self.link.pipeline(cmds, timeout=T_APPLY)
                await self._locked_thread(_push)
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
                await self._locked_thread(self.link.resync, 'ACF 적용 실패')
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

        **`apply_acf=false` 의 안전장치 가운데 하나다.**  파일에서 얻은 줄 번호가
        컨트롤러 메모리의 실제 배치와 다르면, `set_config('PARAMETER2',
        'IntMS=…')` 가 **엉뚱한 줄을 고친다** -- 그러면 노출 시간이 안 바뀌는데
        오류도 안 난다.

        ⚠️ **줄이 맞아도 그 세션의 `APPLYALL` 여부는 못 가른다** -- 설정 메모리에
        줄이 남아 있어도 이 세션에서 `APPLYALL` 이 없었으면 `POWERON` 이 `?xx`
        로 거부된다 (매뉴얼 p.51, DevNote 10.2).  그 경우는 `power_on()` 이
        진단 문구를 붙인다.
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

        flush 대기 **안에서** `POWER=4` 를 확인한다 -- `_await_power()`.
        대기 시간(`poweron_wait`)은 그대로다: 그 시간은 전원 램프가 아니라
        **CCD flush** 를 기다리는 것이라 일찍 빠져나오면 안 된다.
        """
        # **여기서 낡은 저장 표를 버린다** (2026-08-30 배선).  ⚠️ CCD `POWERON`
        # 은 `BUFnFRAME` 을 리셋하지 **않는다** (2026-09-02 실측 -- 리셋은
        # `REBOOT`·백플레인 전원만, DevNote 10.7).  그래도 버리는 것이 맞다:
        # 전원이 내려간 사이의 프레임은 어차피 자료가 아니고, 표를 남겨 두면
        # 다음 프레임의 저장이
        # **그 낡은 표**를 집어 파일마다 한 노출 뒤진 픽셀이 담기고, 헤더는 새
        # 프레임의 것이라 경고가 한 줄도 안 뜬다 (`FrameTicket` 설명의 그
        # blocker 다).  **크게 잃는 것이 조용히 틀린 것보다 낫다.**
        self.drop_tickets('POWERON -- 전원이 내려간 사이의 프레임은 못 받는다')
        self.power_attempted = True
        try:
            await self.cmd('POWERON', timeout=T_POWER)
        except ArchonError as exc:
            if exc.reply_error:
                # ⭐ 첫 관문에서 한 시간을 먹은 한 줄이다 (DevNote 10.2·10.10-6).
                # 매뉴얼 p.51: *"An APPLYALL is required before this operation."*
                # 설정 메모리에 줄이 있어도 **이 세션에서** APPLYALL 이 없었으면
                # 거부한다 -- REBOOT·백플레인 전원 뒤, 또는 apply_acf=false 로
                # 새 세션을 열었을 때가 그 경우다.
                raise ArchonError(
                    '%s: POWERON 을 컨트롤러가 거부했다 (%s) -- 이 세션에서 '
                    'APPLYALL 이 없었을 가능성이 크다 (매뉴얼 p.51).  REBOOT 나 '
                    '전원 재투입 뒤라면 apply_acf=true 로 두거나 GUI Apply All '
                    '을 먼저 할 것 (DevNote 10.2)' % (self.tag, exc),
                    cmd='POWERON', reply_error=True) from exc
            raise
        self.powered = True
        delay = self.cfg.poweron_wait if wait is None else wait
        if delay <= 0:
            return
        log.info('%s: POWERON -- CCD flush %.1f초 대기', self.tag, delay)
        if not self.cfg.telemetry:
            # 규약 4 -- `telemetry=false` 는 **왕복을 labtest v1.0 계보와 똑같이
            # 둔다**는 뜻이다.  확인 질의도 왕복이므로 여기서는 걸지 않는다.
            await asyncio.sleep(delay)
            return
        await self._await_power(delay)

    async def _await_power(self, delay: float) -> None:
        """flush 대기 **안에서** `POWER=4` 를 확인한다 (modtm 계보, 2026-08-28).

        **`POWERON` 이 성공 응답을 준 것과 전원이 실제로 올라온 것은 다르다**
        (`parse.POWER_STATES` 의 주석이 이미 그렇게 적어 두고 있었는데 아무도
        확인하지 않았다).  실험실 계보 둘이 여기서 갈린다 -- labtest v1.0/v1.3
        은 응답만 보고 12초를 세고, `__ref_archon_control/modtm_*.py` 는
        `STATUS` 를 되물어 `POWER==4` 를 확인한 뒤에야 진행한다.  modtm 쪽이
        옳다: 확인이 없으면 전원이 안 올라온 채로 노출이 걸리고, 밖에서는
        **"취득 실패" 로만** 보인다 (F2 가 막으려던 바로 그 모양).

        ⚠️ **막지는 않는다.**  `_check_health()` 와 같은 자리다 -- 이 필드는
        아직 실기 미검증(PROVISIONAL)이라 오독 하나로 관측을 세우는 쪽이 더
        나쁘다.  대신 원인이 보이도록 크게 남긴다.

        ⚠️ **`_check_health()` 를 부르지 않는다.**  램프 도중의 `POWER=3`
        (Intermediate -- 일부 모듈만 올라왔다)은 **정상 경과**인데, 그것을
        건강 판정에 넣으면 켤 때마다 "컨트롤러 상태 이상" 이 뜬다.  같은
        이유로 스냅샷(`status`/`status_live`)도 덮지 않는다 -- 저 둘은 각각
        헤더와 감시의 것이고, 여기 값은 **지나가는 상태**다.
        """
        deadline = time.monotonic() + delay
        started = time.monotonic()
        state = None
        while time.monotonic() < deadline:
            await asyncio.sleep(min(T_POWER_POLL,
                                    max(deadline - time.monotonic(), 0.0)))
            try:
                fields = await self.query('STATUS',
                                          timeout=self.cfg.status_timeout)
            except (ArchonError, TimeoutError, OSError) as exc:
                log.warning('%s: POWERON 확인 질의가 실패했다 (%s) -- 확인 없이 '
                            '남은 flush 시간만 기다린다', self.tag, exc)
                break
            state = parse.power_state(fields)
            if state is None:
                # **보고가 없는 것을 이상으로 세지 않는다** (F2 원칙).  구
                # 펌웨어는 `POWER` 를 아예 안 낸다 -- 그때는 확인 수단이 없는
                # 것이지 전원이 안 올라온 것이 아니다.
                log.info('%s: STATUS 에 POWER 필드가 없다 -- POWERON 확인을 '
                         '건너뛴다 (구 펌웨어일 수 있다)', self.tag)
                break
            if state == parse.POWER_ON:
                log.info('%s: POWER=4 (On) 확인 -- %.1f초 걸렸다.  남은 flush '
                         '시간을 마저 기다린다', self.tag,
                         time.monotonic() - started)
                break
        # ⚠️ **마지막으로 읽은 값을 버리지 않는다.**  `POWER=3` 을 보다가 시한이
        # 끝난 것과 한 번도 못 물어본 것은 다른 사실이고, 아래 판정이 그 둘을
        # 갈라야 한다 (`state is None` 이 "확인 못 했다" 다).
        elapsed = time.monotonic() - started
        remaining = deadline - time.monotonic()
        if remaining > 0:
            await asyncio.sleep(remaining)
        if state is not None and state != parse.POWER_ON:
            log.error('%s: POWERON 뒤 %.1f초가 지나도 POWER=%d %s 다 -- 이 '
                      '상태에서 건 노출은 자료가 아니라 잔해일 수 있다.  유닛 '
                      '전원과 ACF 적용을 확인하라 (매뉴얼 p.47)',
                      self.tag, elapsed, state,
                      parse.POWER_STATES.get(state, '?'))

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

    async def refresh_status_live(self) -> bool:
        """**감시용** `STATUS` 스냅샷.  성공하면 `True`.

        헤더용 `refresh_status()` 와 갈라 둔 자리다 -- 규칙 넷을 여기서 지킨다
        (`../SMC_CLAUDE.md` "반드시 지킬 것 넷", 운영자 승인 2026-08-27):

        1. **락을 새로 만들지 않는다** -- `query()` 가 `self._lock` 을 타므로
           FETCH·노출 왕복과 자동으로 직렬화된다.  ⚠️ 그래서 **FETCH 가 락을
           344 MiB 동안 쥐면 감시 주기가 그만큼 밀린다.**  그것은 오류가 아니라
           기록할 사실이다 -- 밀린 시간은 기록의 `lag_ms` 열에 남고, **밀린
           만큼 몰아서 뜨지 않는다**(그건 감시가 아니라 부하다).
        2. **`telemetry_enabled` 를 만지지 않는다** -- 그 래치는 취득 경로의
           판단이다(F8).  감시의 성공·실패는 `status_live_fails` 로만 센다.
        3. `self.status`(헤더용 언 스냅샷)를 **덮지 않는다.**
        4. 실패하면 `status_live` 를 **버린다** -- 낡은 값이 새 값처럼 보이는
           것이 가장 나쁘다(`refresh_status()` 가 헤더 쪽에서 같은 판단을 한다).
           `status_live_at` 은 지우지 않는다 -- **"마지막으로 성공한 것이
           언제인가"** 는 버릴 값이 아니라 진단이다.  그 값이 기록에 `age_ms`
           로 나가는 것은 폴링이 성공한 행에서만이다.

        `[archon] telemetry = false` 면 아무것도 하지 않는다 -- 그 설정의 뜻이
        "컨트롤러와의 왕복을 labtest v1.0 계보와 똑같이 둔다" 이므로 감시도
        예외가 아니다.
        """
        if not self.cfg.telemetry:
            return False
        try:
            fields = await self.query('STATUS',
                                      timeout=self.cfg.status_timeout)
        except (ArchonError, TimeoutError, OSError) as exc:
            self.status_live_fails += 1
            self.status_live = {}
            # **같은 줄을 주기마다 되풀이하지 않는다** -- 20초 간격이면 밤새
            # 수천 줄이 되고, 반복되는 경고는 사람이 경고를 무시하도록
            # 학습시킨다.  첫 실패와 그 뒤 10회마다만 알린다 (기록 쪽에는
            # `poll_failed` 행이 빠짐없이 남으므로 사실은 안 잃는다).
            if self.status_live_fails == 1 or self.status_live_fails % 10 == 0:
                log.warning('%s: 감시 STATUS 실패 %d회 연속 (%s) -- 취득용 '
                            '텔레메트리 래치는 건드리지 않는다', self.tag,
                            self.status_live_fails, exc)
            return False
        if self.status_live_fails:
            log.info('%s: 감시 STATUS 복구 (%d회 실패 뒤)',
                     self.tag, self.status_live_fails)
        self.status_live_fails = 0
        self.status_live = fields
        self.status_live_at = time.time()
        self._check_health(fields)
        return True

    async def timer(self) -> str:
        """`TIMER` -- 컨트롤러의 10 ns tick 카운터 (매뉴얼 p.49).  실패하면 `''`.

        **STATUS 필드가 아니라 별도 명령이다** -- labtest 가 2026-08-27 에
        따로 뽑아낸 자리다(`e5d72b5`).  값이 회전마다 변하지 않으면 **타이밍
        코어가 멈춘 것**이고, 그것이 "노출이 안 걸렸나 / 독출이 안 끝나나" 를
        가르는 마지막 계측이다.

        ⚠️ 진단용이라 **예외를 올리지 않는다** -- 이것을 부르는 자리는 이미
        무언가 잘못된 순간이고, 거기서 새 예외를 내면 원인이 가려진다.
        """
        try:
            raw = await self.cmd('TIMER', timeout=T_FAST)
        except (ArchonError, TimeoutError, OSError) as exc:
            return 'ERR(%s)' % exc
        return raw.decode('ascii', 'replace').strip()

    async def diagnostic_snapshot(self, with_status: bool = True) -> str:
        """진단 한 줄 -- `FRAME` (+ `POWER`/`POWERGOOD`/`TIMER`).

        **labtest `_frame_snapshot()` 을 그대로 옮겼다** (v1.3.4, 2026-08-27).
        실기에서 프레임이 한 장도 안 나오던 증상을 가른 것이 이 한 줄이었고,
        원인은 결국 **`Sync In` 이 물려 상대 컨트롤러가 클록을 잡고 있던 것**
        이었다 (`../scr_labtest/README_labtest.md`).  그때 관측된 조합이
        `POWER=4` · `POWERGOOD=1` · `FRAME=0/0/0` 영구였다 --
        **`POWERGOOD` 은 외부 클록 의존을 보지 않는다.**

        읽는 법:

        | 보이는 것 | 뜻 |
        |---|---|
        | `FRAME` 이 안 오름 | 노출 미개시 (`LOADPARAMS`·타이밍·**Sync In**) |
        | `FRAME` 은 오르는데 `COMPLETE=0` | 독출이 버퍼를 못 채운다 (기하·tap) |
        | `TIMER` 가 안 변함 | 타이밍 코어 정지 |

        ⚠️ **예외를 올리지 않는다.**  실패한 순간에 부르는 것이므로 링크가 이미
        깨져 있을 수 있다 -- 그때는 실패 사유를 그 자리에 적는다.
        """
        try:
            fields = await self.query('FRAME', timeout=T_FAST)
        except (ArchonError, TimeoutError, OSError) as exc:
            return 'FRAME 질의 실패: %s' % exc
        line = ('RBUF=%s WBUF=%s  FRAME=%s/%s/%s  COMPLETE=%s/%s/%s  '
                'LINES=%s/%s/%s'
                % (fields.get('RBUF', '?'), fields.get('WBUF', '?'),
                   fields.get('BUF1FRAME', '?'), fields.get('BUF2FRAME', '?'),
                   fields.get('BUF3FRAME', '?'),
                   fields.get('BUF1COMPLETE', '?'),
                   fields.get('BUF2COMPLETE', '?'),
                   fields.get('BUF3COMPLETE', '?'),
                   fields.get('BUF1LINES', '?'), fields.get('BUF2LINES', '?'),
                   fields.get('BUF3LINES', '?')))
        if not with_status:
            return line
        # **감시가 이미 떠 둔 값을 쓰지 않는다** -- 지금 이 순간의 값이라야
        # 진단이 된다.  왕복이 둘 늘지만 부르는 자리는 실패한 순간뿐이다.
        try:
            status = await self.query('STATUS',
                                      timeout=self.cfg.status_timeout)
        except (ArchonError, TimeoutError, OSError) as exc:
            status = {'POWER': 'ERR(%s)' % exc}
        return line + ('  POWER=%s  POWERGOOD=%s  OVERHEAT=%s  TIMER=%s'
                       % (status.get('POWER', '?'),
                          status.get('POWERGOOD', '?'),
                          status.get('OVERHEAT', '?'), await self.timer()))

    def _check_health(self, status: dict[str, str] | None = None) -> None:
        """`STATUS` 응답에서 전원·과열 이상을 읽어 알린다 (F2).

        인자를 안 주면 헤더용 스냅샷(`self.status`)을 본다.  감시는
        `status_live` 를 넘겨 **같은 판정**을 쓴다 -- `_health_bad` 래치를
        공유하므로 취득 경로와 감시가 같은 이상을 두 번 알리지 않는다.
        (⚠️ 이 래치는 **로그 중복 방지**일 뿐 취득 판단이 아니다 -- "감시가
        취득 경로의 판단을 뒤집지 않는다" 규칙에 걸리지 않는다.)

        **막지는 않는다.**  이 필드들은 아직 실기 미검증(PROVISIONAL)이라,
        오독 하나로 관측을 통째로 세우는 쪽이 더 나쁘다 -- 첫 실행에서
        `tools/probe_archon.py` 1단계가 같은 값을 눈으로 확인한다.  대신 원인이
        보이도록 크게 남긴다: 종전에는 전원 이상이 밖에서 "취득 실패" 로만
        보였다.
        """
        bad = parse.health_problems(self.status if status is None
                                    else status)
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
                      suffix: str = '', exposures: int = 1) -> FrameTicket:
        """노출을 걸고 곧바로 돌아온다 (적분·독출은 컨트롤러가 몬다).

        순서는 labtest 그대로다 -- **프레임 번호를 먼저 읽고** `IntMS`,
        `Exposures`, `LOADPARAMS`.  번호를 먼저 읽는 이유는 그 값이 "새
        프레임이 나왔나" 의 기준이기 때문이다.

        Args:
            queue: 저장 대기열에 넣을지.  flush 는 **버리는 프레임**이라
                `False` 다 -- 넣으면 저장 쪽이 그것을 자기 프레임으로 집어 온다.
            suffix: 이 프레임의 이름 (`<YYYYMMDD>.<NNNNNN>`).  저장 쪽이 **자기
                프레임의 표를 골라 집는** 근거다.
            exposures: `Exposures` 파라미터.  **science 는 1** (프레임마다
                다시 건다).  guide 는 **n+1 을 한 번에** 걸어 시퀀서가 유휴
                없이 연달아 찍게 한다 -- 그때 둘째 프레임부터는 `expect_next()`
                로 표만 잇는다(왕복에 `LOADPARAMS` 가 없다).  타이밍
                스크립트가 `GOTO Start` 뒤 `Exposures` 가 남아 있으면 곧바로
                `Exposure:` 로 되돌아가는 것이 근거다.
        """
        # **한 번의 `FRAME` 으로 둘을 뽑는다** -- 프레임 번호(기준값)와 세
        # 버퍼의 번호(기준선).  왕복은 종전과 같다.
        self.loadparams_sent = False
        _fields = await self.query('FRAME', timeout=T_FAST)
        prev = parse.newest(_fields).frame
        before = parse.buffer_frames(_fields)
        await self.set_config(self.cfg.param_intms_slot,
                              '%s=%d' % (self.cfg.param_intms_name,
                                         max(int(exptime_ms), 0)))
        await self.set_config(self.cfg.param_exposures_slot,
                              '%s=%d' % (self.cfg.param_exposures_name,
                                         max(int(exposures), 1)))
        # 취소가 여기서 걸리면 `_locked_thread` 가 스레드를 끝까지 기다리므로
        # 표시가 True 인 순간 ack 는 이미 (또는 곧) 받은 것이다.
        self.loadparams_sent = True
        await self.cmd('LOADPARAMS', timeout=T_SYSTEM)
        ticket = FrameTicket(
            suffix=suffix,
            prev_frame=prev,
            prev_frames=before,
            int_until=(time.monotonic() + exptime_ms / 1000.0
                       if exptime_ms > 0 else None))
        self._current = ticket
        if queue:
            self._queue.append(ticket)
        log.info('%s: 노출 지시 -- IntMS=%d Exposures=%d (프레임 %d 다음%s)',
                 self.tag, int(exptime_ms), max(int(exposures), 1), prev,
                 '' if queue else ', 버림')
        return ticket

    async def expect_next(self, after: FrameTicket, *, suffix: str = '',
                          exptime_ms: int = 0,
                          queue: bool = True) -> FrameTicket:
        """**이미 걸려 있는** 연속 노출의 다음 표를 만든다 (`LOADPARAMS` 없음).

        `trigger(exposures=n)` 로 n 장을 한 번에 걸어 두면 시퀀서가 유휴 없이
        연달아 찍는다 -- 호스트는 프레임마다 노출을 다시 걸지 않고 **표만**
        이어 두면 된다.

        ⚠️ 기준선은 **직전 표의 완료 프레임 번호**다.  지금 `FRAME` 의 최신
        번호를 쓰면 안 된다 -- 우리 루프보다 독출이 빠르면 다음 프레임이 이미
        나와 있고, 그것을 기준으로 잡으면 **그 프레임을 통째로 건너뛴다**.

        Args:
            after: 직전 프레임의 표 (`ready` 가 채워져 있어야 한다).
            exptime_ms: 이 프레임의 `IntMS` -- 시한 계산(`int_until`)에만 쓴다.
        """
        if after.ready is None:            # pragma: no cover -- 호출 규약 위반
            raise ArchonError('%s: 직전 프레임이 아직 안 끝났다 -- expect_next '
                              '는 완료된 표 뒤에만 부른다' % self.tag)
        fields = await self.query('FRAME', timeout=T_FAST)
        ticket = FrameTicket(
            suffix=suffix,
            prev_frame=after.ready.frame,
            prev_frames=parse.buffer_frames(fields),
            int_until=(time.monotonic() + exptime_ms / 1000.0
                       if exptime_ms > 0 else None))
        self._current = ticket
        if queue:
            self._queue.append(ticket)
        return ticket

    async def expect_from_now(self, *, suffix: str = '',
                              queue: bool = False) -> FrameTicket:
        """**지금**을 기준선으로 한 표 -- `LOADPARAMS` 없이, 이미 도는 프레임을
        기다리는 데 쓴다 (꼬리 소화, DevNote 9.15-(9)).

        `arm_sequence()` 의 `LOADPARAMS` 도중 ABORT 가 오면 컨트롤러는 돌기
        시작했는데 표가 없다 -- 그때 `FRAME` 한 번으로 기준선을 잡는다.
        """
        fields = await self.query('FRAME', timeout=T_FAST)
        ticket = FrameTicket(
            suffix=suffix,
            prev_frame=parse.newest(fields).frame,
            prev_frames=parse.buffer_frames(fields),
            int_until=None)
        self._current = ticket
        if queue:
            self._queue.append(ticket)
        return ticket

    async def newest_frame(self) -> int:
        """`FRAME` 한 번 -- 지금 완료돼 있는 가장 새 프레임 번호 (-1 = 없음)."""
        return parse.newest(await self.query('FRAME', timeout=T_FAST)).frame

    async def set_exposures(self, n: int) -> None:
        """남은 연속 노출 수를 바꾼다 (`0` 이면 현재 프레임까지만).

        STOP 경로가 쓴다 -- 시퀀서는 `Exposures` 가 0 이 되면 현재 프레임을
        마치고 유휴 루프로 돌아간다 (타이밍 스크립트 `Start:`).
        """
        await self.set_config(self.cfg.param_exposures_slot,
                              '%s=%d' % (self.cfg.param_exposures_name,
                                         max(int(n), 0)))
        await self.cmd('LOADPARAMS', timeout=T_SYSTEM)
        log.info('%s: Exposures=%d 로 갱신', self.tag, max(int(n), 0))

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

        진행률은 `FRAME` 의 `BUFnLINES` / ACF `LINECOUNT` 다 (p.50 · DevNote
        10.3).  ⚠️ `BUFnHEIGHT` 는 분모가 아니다 -- `FRAMEMODE=2` 면 그 2배라
        `PCTREAD` 가 50% 에 묶인다 (`parse.progress_of`).  적분
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
        started = time.monotonic()
        # **상한은 적분이 끝난 뒤부터 센다** (2026-08-28 수정).
        #
        # 종전에는 `now + frame_timeout` 이라 **DARK/BIAS 의 긴 노출에서 헛
        # 시한**이 났다: 셔터 노출은 시퀀서가 카운트다운을 다 하고 `readout()`
        # 을 부르므로 여기 들어올 때 적분이 이미 끝나 있지만, DARK/BIAS 는
        # `_readout_stream()` 이 `IntMS=<적분시간>` 으로 걸고 **곧바로** 여기로
        # 들어온다 -- 300초 상한에 600초 dark 를 걸면 프레임이 정상으로 나오는
        # 중에 `DMA WAIT TIMEOUT` 이 났다.  labtest 도 같은 계산이다
        # (`deadline = exptime/1000 + FRAME_WAIT_MAX`, v1.3.4).
        deadline = None
        if limit > 0:
            deadline = max(started, ticket.int_until or 0.0) + limit
        # 프레임 대기 중 주기 덤프 -- 취득이 안 끝날 때 "노출이 안 걸렸나 /
        # 독출이 안 끝나나" 를 가르는 계측이다 (labtest `FRAME_DUMP_ENABLE`).
        # **정상 취득이 도는 동안은 꺼 둔다**(기본 0) -- 왕복이 셋 늘어난다.
        dump_every = float(getattr(self.cfg, 'frame_dump', 0.0) or 0.0)
        next_dump = (started + dump_every) if dump_every > 0 else None
        while True:
            now = time.monotonic()
            if deadline is not None and now > deadline:
                # **영구 대기를 오류로 바꾼다.**  독출이 시작되지 않으면
                # `EXPSTATUS=READOUT` 에 갇혀 관측자 화면이 멈추고 OBSAgent 가
                # `force_idle` 타임아웃으로 `opause` 에 빠진다 -- 조용한 정지가
                # 가장 나쁜 실패다.
                #
                # **실패한 순간의 진단을 항상 남긴다** -- `frame_dump` 설정과
                # 무관하다 (labtest v1.3.4 가 세운 규칙).  이 증상은 간헐이라
                # 평소 덤프를 꺼 두면 정작 재발했을 때 증거가 남지 않는다.
                # ⚠️ 실기에서 이 조합(`POWER=4` · `POWERGOOD=1` · `FRAME` 정지)
                # 의 원인은 **`Sync In` 이 물려 상대 컨트롤러가 클록을 잡고
                # 있던 것**이었다 -- `POWERGOOD` 은 외부 클록을 보지 않는다.
                log.error('%s: 프레임 대기 시한 초과 -- %s', self.tag,
                          await self.diagnostic_snapshot())
                raise ArchonError(
                    '%s: 프레임 %d 이 %.0f초 안에 나오지 않았다 (적분 %.1f초 '
                    '뒤부터 셌다) -- 독출이 시작되지 않았을 수 있다.  ACF·'
                    'LOADPARAMS·클록, 그리고 **Sync In 결선과 상대 유닛**을 '
                    '보라.  [archon] frame_timeout 으로 상한을 조정한다'
                    % (self.tag, prev + 1, limit,
                       max((ticket.int_until or started) - started, 0.0)),
                    cmd='FRAME')
            fields = await self.query('FRAME', timeout=T_FAST)
            # **"내 다음 프레임" 을 찾는다** -- "최신 프레임" 이 아니다.  저장이
            # 늦으면 그 사이 프레임이 더 나와 있고, 최신 것을 집으면 이 파일이
            # **남의 노출 픽셀**을 담는다(헤더는 이 프레임의 것이라 아무 경고도
            # 없다).
            mine = parse.next_frame(fields, prev)
            if mine is None:
                # **카운터가 뒤로 갔나** -- 되감김(한 바퀴) 또는 컨트롤러
                # 재시작.  `next_frame()` 은 `frame > prev` 로 찾으므로 이
                # 경우 **영원히 `None`** 이고, 그대로 두면 `frame_timeout`
                # 까지 기다리다 노출을 잃는다 (2026-08-30 발견).
                #
                # ⚠️ 폭을 모르므로 크기로 판별하지 않는다 -- **기준선 대비
                # 변화**로 판별한다 (`parse.restarted_frame` 의 설명).
                mine = parse.restarted_frame(fields, prev, ticket.prev_frames)
                if mine is not None:
                    log.error(
                        '%s: 프레임 번호가 뒤로 갔다 -- %d 다음을 기다렸는데 '
                        '버퍼 %d 에 %d 이 새로 들어왔다.  카운터 되감김이거나 '
                        '컨트롤러가 재시작했다.  **이 프레임은 받는다** (기준을 '
                        '%d 로 재동기).  자주 보이면 BUFnFRAME 폭을 실측해 '
                        '두라 -- 매뉴얼 p.50 에 폭이 안 적혀 있다',
                        self.tag, prev, mine.buf + 1, mine.frame, mine.frame)
                    prev = mine.frame - 1        # 아래 연속성 검사를 통과시킨다
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
            pct = parse.newest(fields).progress_of(self.lines_total)
            if pct is not None and pct >= reported + step:
                reported = pct
                yield pct
            if next_dump is not None and time.monotonic() >= next_dump:
                next_dump = time.monotonic() + dump_every
                log.info('%s: 프레임 대기 %.0f초 -- %s', self.tag,
                         time.monotonic() - started,
                         await self.diagnostic_snapshot())
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
        # 매뉴얼 p.71 은 `LOCK` 을 **통상 경로**로 적어 두었다("새 프레임이
        # 있으면 호스트는 LOCK 을 내려 그 버퍼가 덮이는 것을 막고 FETCH 한다").
        # ⚠️ **그러나 그것은 판정이 아니라 가설의 강도다** -- 매뉴얼은
        # 2021-02-23 판이고 **현행 FW 와 양방향으로 어긋날 수 있다**(운영자
        # 2026-08-30).  이 저장소 안에 이미 반례가 둘 있다(`MODn_TYPE` 16+ ·
        # AD 모듈 슬롯).  **판단 근거는 실측**이다 -- DevNote 8.7.
        #
        # ⚠️ labtest 는 2026-05-28 에 `LOCK` 을 뺐다("remove to fetch debug").
        # 되돌렸고 ✅ **실기 확인은 종결됐다** (2026-09-01, 두 유닛 -- DevNote
        # 10.4·10.6): `LOCK` 은 매번 반영되고(RBUF 15/15) 대가가 없으며(`lock`
        # = `idle` = 368 행/초), **지킬 구간이 실재한다** -- 잠그지 않은 채
        # fetch 중 프레임 경계가 걸리면 엔진이 우리가 읽는 버퍼로 옮겨온다
        # (2/2 관측).  `[archon] lock_buffer = true` 가 정본이다.  끄더라도
        # 아래 대조는 남고, `recheck_after_fetch` 가 fetch 중의 창까지 본다.
        # ⚠️ **science 는 버퍼가 둘뿐**이라 하나를 잠그면 엔진에 하나만 남는다
        # (guide 는 셋이라 둘이 남는다).  남는 버퍼가 없으면 엔진은 **쓰던
        # 버퍼를 재사용**해 다음 프레임을 덮는다 (H3 닫힘, `--hold 20` 실측)
        # -- 그래서 잠금은 프레임 주기보다 짧아야 하고, 그 상한이
        # `fetch_timeout` 이다 (config 기동 검사가 본다).
        buf_n = fs.buf + 1
        lock = getattr(self.cfg, 'lock_buffer', True)
        # **관측값을 먼저 지운다** -- `LOCK` 이 실패하면 지난 프레임의 값이
        # 남아 실험 로그가 거짓말을 한다.
        self.lock_rbuf = self.lock_wbuf = self.lock_wbuf_after = -1
        try:
            # ⭐ 잠금도 `try` 안이다 (DevNote 10.9) -- `LOCK%d` 의 응답이
            # 타임아웃으로 죽어도 컨트롤러 쪽은 이미 잠겼을 수 있으니
            # `finally` 의 `LOCK0` 을 타야 한다.  잠기지 않은 채 `LOCK0` 을
            # 보내는 것은 무해하다.
            if lock:
                await self.cmd('LOCK%d' % buf_n, timeout=T_FAST)
            # **잠근 뒤에 다시 확인한다.**  잠그기 직전에 이미 덮였을 수 있다.
            live_fields = await self.query('FRAME', timeout=T_FAST)
            live = parse.buffer_frame(live_fields, buf_n)
            # ⭐ **같은 응답에서 잠금 상태도 뽑는다** (왕복 0, 2026-08-30).
            # `LOCKn` 이 FW 에 먹는지 -- A-5 판단 ② 는 2026-09-01 종결 (두 FW
            # 15/15, DevNote 10.4).  이 관측은 이제 FW 회귀 감시다.
            self.lock_rbuf, self.lock_wbuf = parse.lock_state(live_fields)
            if lock and self.lock_rbuf != buf_n:
                # ✅ 두 FW(1252·1261) 가 15/15 반영했고 `RBUF` 는 FW 가 낸다
                # (8.11) -- "미구현" 도피구는 닫혔다.  여기가 뜨면 **FW 회귀
                # 신호**다.  그래도 `recheck_after_fetch` 가 마지막 방어다.
                log.warning(
                    '%s: LOCK%d 을 보냈는데 RBUF=%d 다 (기대 %d) -- 2026-09-01 '
                    '두 FW 15/15 반영과 다르다.  FW 가 바뀌었나 (DevNote 10.4).  '
                    'recheck_after_fetch 를 켜 두라 (매뉴얼 p.50)',
                    self.tag, buf_n, self.lock_rbuf, buf_n)
            if live != fs.frame:
                raise ArchonError(
                    '%s: 버퍼 %d 가 프레임 %d 로 덮였다 (내 프레임은 %d) -- '
                    'fetch 하지 않는다.  저장이 다음 노출보다 늦었다는 뜻이니 '
                    'write_delay·독출 시간을 보라 (lock_buffer=%s)'
                    % (self.tag, buf_n, live, fs.frame, lock), cmd='FETCH')

            # 상한은 크기에서 뽑는다 -- 1 GB/s 를 밑도는 어떤 링크라도 넉넉하고,
            # 그러면서 "영구히 멈춤" 은 막는다.  이 유도값은 `[archon]
            # fetch_timeout` 이 0 일 때만 쓰인다 -- 실측(99~107 MiB/s, DevNote
            # 10.4)으로 ini 는 10초다.  ⚠️ 잠금 상한이기도 하다: 주기(13.27초)
            # 를 넘으면 다음 장이 덮인다(10.6) -- `config` 기동 검사가 알린다.
            # `frame_timeout` 과 **별개의 상한**이라 한쪽만 조여도 다른 쪽은
            # 그대로다.
            timeout = float(getattr(self.cfg, 'fetch_timeout', 0.0) or 0.0)
            if timeout <= 0:
                timeout = max(60.0, expect_bytes / (1 << 20) * 1.0)
            # **버퍼는 `LOCK` 을 잡은 뒤에 기다린다.**  순서가 중요하다 --
            # 잠그지 않은 채 기다리면 그동안 컨트롤러가 이 프레임을 덮어
            # **프레임을 잃는다.**  잠근 채 기다리면 컨트롤러는 다른 버퍼를
            # 쓰므로 **한 프레임만** 더 간다 -- 그 다음 경계부터는 엔진이 쓰던
            # 버퍼를 재사용해 **앞 장을 덮는다** (DevNote 10.4, `--hold 20`).
            # 우리 프레임은 지켜지지만, 이 대기가 프레임 주기(13.27초)를 넘으면
            # 다음 장을 잃는다.  ⏳ 이 대기에는 상한이 없다 -- `fetch_timeout`
            # 은 전송만 잰다.  호스트 버퍼 고갈은 `buf_waits` 경고로 드러나고,
            # 상한을 둘지는 첫 운용 실측 뒤 판단 (DevNote 9.15).
            buf = await self._take_buffer(expect_bytes)
            started = time.monotonic()
            try:
                data = await self._locked_thread(
                    self.link.fetch, fs.base, expect_bytes, timeout, None, buf)
            except BaseException:
                # 실패하면 곧바로 돌려준다 -- 안 그러면 링이 한 칸씩 줄어
                # **몇 번의 실패 뒤에 영구히 막힌다.**
                self.release_buffer(buf)
                raise

            # **fetch 뒤 재대조** (`[archon] recheck_after_fetch`, 2026-08-30).
            #
            # 앞의 대조는 fetch **직전 한 순간**만 본다.  fetch 자체가 수 초
            # 걸리므로(실측 3.2~3.5초, DevNote 10.4) **그 사이에 덮이는 창**은
            # 아무도 안 본다 -- 주기 13.27초에 경계가 걸릴 확률 ≈26% 다 (10.6) --
            # `lock_buffer=true` 면 그 창을 `LOCKn` 이 막지만, **끄면 막는 것이
            # 아무것도 없다.**  그래서 이 재대조가 `lock_buffer=false` 의 짝이다.
            #
            # 덮였으면 **받아 온 자료를 버린다.**  3~4초를 버리는 셈이지만, 그
            # 대안은 남의 노출 픽셀을 담은 raw 한 장을 **아무 경고 없이** 쓰는
            # 것이다 (헤더는 이 프레임의 것이라 나중에 봐도 못 가른다).
            if getattr(self.cfg, 'recheck_after_fetch', True):
                after_fields = await self.query('FRAME', timeout=T_FAST)
                after = parse.buffer_frame(after_fields, buf_n)
                # ⭐ **`WBUF` 의 이동이 `RBUF` 보다 강한 증거다** -- 상태 플래그가
                # 아니라 **엔진이 실제로 다른 버퍼를 썼다**는 거동이다.
                self.lock_wbuf_after = parse.lock_state(after_fields)[1]
                if after != fs.frame:
                    self.release_buffer(buf)
                    raise ArchonError(
                        '%s: fetch 하는 동안 버퍼 %d 가 프레임 %d 로 덮였다 '
                        '(내 프레임은 %d) -- 받아 온 %.1f MiB 를 버린다.  이 '
                        '자료는 두 노출이 섞여 있다.  lock_buffer=%s 이니 '
                        'true 로 두거나, write_delay·독출 시간과 버퍼 수를 '
                        '보라'
                        % (self.tag, buf_n, after, fs.frame,
                           expect_bytes / (1 << 20), lock), cmd='FETCH')
        finally:
            if lock:
                try:
                    await self.cmd('LOCK0', timeout=T_FAST)
                except (ArchonError, TimeoutError, OSError) as exc:
                    # **풀지 못하면 엔진은 버퍼 하나로 돈다** -- 다음 장이 앞 장을
                    # 덮는다 (DevNote 10.6).  크게 알린다.
                    log.error('%s: LOCK0(잠금 해제)에 실패했다 (%s) -- 잠금이 '
                              '남으면 엔진은 남은 버퍼 하나로 돌아 다음 장이 앞 '
                              '장을 덮는다 (DevNote 10.6).  다음 fetch 의 LOCKn 이 '
                              '잠금을 옮길 때까지 프레임을 잃을 수 있다',
                              self.tag, exc)
        # ⭐ 잠금 관측값을 **이미 있는 줄에 얹는다** -- 정상 취득에 새 줄을
        # 늘리지 않으면서 회귀 감시(FW 가 바뀌면 RBUF/WBUF 가 달라진다)에 필요한
        # 것이 매 프레임 남는다.  A/B 실험은 2026-09-01 종결 (DevNote 10.6).
        log.info('%s: FETCH %.1f MiB, %.1f초 (프레임 %d, buf %d, base 0x%08X) '
                 '[lock=%s RBUF=%d WBUF=%d%s]',
                 self.tag, expect_bytes / (1 << 20),
                 time.monotonic() - started, fs.frame, buf_n, fs.base,
                 lock, self.lock_rbuf, self.lock_wbuf,
                 '' if self.lock_wbuf_after < 0
                 else '->%d' % self.lock_wbuf_after)
        return data

    async def _take_buffer(self, nbytes: int) -> bytearray:
        """링에서 버퍼 하나를 빌린다.  비어 있으면 **기다린다**(역압).

        기다렸다는 사실을 세어 두는 것이 요점이다 -- `fetch_buffers` 가
        충분한지를 **실기가 답하게** 한다.  기다림이 길어지면 그동안 컨트롤러
        버퍼가 덮여 프레임을 잃으므로, 조용히 넘어가면 안 되는 신호다.
        """
        try:
            buf = self._bufpool.get_nowait()
        except asyncio.QueueEmpty:
            t0 = time.monotonic()
            buf = await self._bufpool.get()
            waited = time.monotonic() - t0
            self.buf_waits += 1
            self.buf_wait_s += waited
            log.warning('%s: 수신 버퍼가 없어 %.2f초 기다렸다 (누적 %d회 · '
                        '%.1f초) -- 저장이 밀리고 있다.  길어지면 컨트롤러 '
                        '버퍼가 덮여 프레임을 잃는다.  [archon] fetch_buffers '
                        '를 올릴 것', self.tag, waited,
                        self.buf_waits, self.buf_wait_s)
        # 크기가 다르면(기하 변경) 새로 잡는다 -- 재사용이 목적이지 강제가 아니다.
        if buf is None or len(buf) != nbytes:
            buf = bytearray(nbytes)
        return buf

    def release_buffer(self, buf) -> None:  # noqa: ANN001
        """버퍼를 링에 돌려준다.  **저장이 끝난 뒤** 부른다.

        ⚠️ fetch 성공 뒤에 이것을 안 부르면 링이 한 칸 줄고, 몇 프레임 뒤에
        **영구히 막힌다** -- `write_frame` 의 `finally` 가 그 자리다.
        """
        try:
            self._bufpool.put_nowait(buf)
        except asyncio.QueueFull:      # 있을 수 없지만 막지는 않는다
            log.debug('%s: 버퍼 링이 가득 차 하나를 버린다', self.tag)

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
                # ⚠️ 이 대조는 **줄 대응**만 본다 -- 그 세션에서 APPLYALL 이
                # 됐는지는 못 가른다 (p.51, DevNote 10.2).  REBOOT 뒤라면 줄이
                # 맞아도 아래 `power_on()` 이 `?xx` 로 거부되고, 그 진단 문구가
                # 이 갈래를 가리킨다.
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
        """슬롯별 모듈 형을 한 번 찍는다 -- 규격 5.6.1절 자리 표의 실기 확인.

        ⚠️ **종전에는 "AD 모듈이 슬롯 5~8 인가" 로 판정했고 그것이 틀렸다**
        (2026-08-27).  실기 science 는 AD 계열이 5·8 둘뿐이라 **정상 구성에서
        경고가 났다.**  판정은 `parse.field_order_problems()` 로 옮겼다 --
        자리 표가 자리를 준 모듈과 실제 장착 모듈이 같은지를 본다.
        """
        mods = parse.module_types(self.system)
        if not mods:
            return
        shown = ', '.join(
            '%d:%s' % (s, parse.MODULE_TYPES.get(t, '?%d' % t))
            for s, t in sorted(mods.items()) if t)
        log.info('%s: 모듈 %s', self.tag, shown)
        # 비디오 모듈 위치는 **참고로만** 찍는다 -- 판정 근거가 아니다.
        ad = sorted(s for s, t in mods.items() if t in parse.AD_TYPES)
        log.info('%s: 비디오(AD 계열) 모듈 슬롯 %s', self.tag, ad or '없음')
        for note in parse.field_order_problems(self.system):
            log.warning('%s: 규격 5.6.1절 자리 표와 어긋난다 -- %s.  Cn_TEMP '
                        '자리가 밀릴 수 있으니 rawhdr.TEMP_MODS 를 확인할 것',
                        self.tag, note)
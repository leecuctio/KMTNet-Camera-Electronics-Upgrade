#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KMTNet AUX control software 와의 TCP 연동.

레거시에는 없던 경로다.  IC(`\\KMTS`)·ICS(`\\KMTX`) 소스 어디에도 외부 TCP
발신이 없다 -- CEU 에서 새로 붙는 기능이다.

규격 출처: `TCSAgent/__reference/KMTNet AUX control remote commands(v20140908).pdf`
(Rev.20140908, Sang-Mok Cha, KASI).

    요청: <Telescope ID> <System> <Packet ID> <SUBSYSTEM> <COMMAND>[LF]
    응답: <Telescope ID> <System> <Packet ID> <RESPONSE>[LF]

    기본 서버   192.168.24.10:5752  (AUX GUI 제어 SW 가 서버, 우리가 클라이언트)
    Telescope ID  기본 "KMTNET" -- AUX 쪽 Server Setting 대화상자에서 바꿀 수 있다
    System        "AUX" 고정
    Packet ID     공백 없는 아무 값.  응답에 그대로 되돌아오므로 대조에 쓴다
    종결자        [LF] = 0x0A

**규격에서 가장 조심할 점**: `Telescope ID` 나 `System` 이 틀리거나 인자 수가
모자라면 **서버는 아무 응답도 주지 않는다**(문서 2-4).  오타가 나도 에러가
아니라 침묵이므로, 타임아웃을 정상적인 실패 경로로 다뤄야 한다.

응답 문자열(문서 1-0): `OK`(ACK) · `BAD`(NACK) · `WAIT` · `ERROR` ·
`SUCCESS`/`FAILURE`(CONNECT) · 그 외 조회 명령의 값들.

**지금 이 클라이언트가 하는 일은 접속 유지와 접속 인사(`hello`) 한 줄뿐이다.**
⛔ 셔터 개폐 통지(`FILTERS SET_SH OPEN|CLOSE`)는 2026-09-12 에 걷었다 -- FSA HW
가 그 명령을 못 받는다는 TCS 측 검토 결과다 (운영자).  ⭐ 셔터는 컨트롤러의
Trigger Out 이 몰고 명령은 `SHOPEN`/`SHCLOSE` 다.  AUX 는 `FILTERS LIMIT_SHUT`
으로 블레이드 리밋을 **읽기만** 한다 (규격 4-2).

→ 실기(`[hardware] backend = archon`)에서는 이 접속이 할 일이 없다.  서버가 없으면
재접속 경고만 쌓이므로 `[auxcontrol] enabled = false` 로 둔다 (설정 검증이 경고한다).

설계 방침 (사용자 결정, 2026-08-05):
  * ack 를 기다리되 `ack_timeout` 이 지나면 경고만 남기고 진행한다.
  * 접속이 없어도 **노출은 계속한다** -- AUX 는 부가 경로다.
  * 재접속은 백그라운드에서 계속 시도한다.
  * 응답 등급: `OK` 통과(INFO) / `BAD`·무응답·`WAIT` 는 경고 로그 (`_report`).
    ⚠️ 종전의 콘솔 색 표시(빨강·청록)는 `print()` 였고 로그와 겹쳐 찍혀서 걷었다
    -- 등급은 로그 수준과 detail 이 말한다.
"""

from __future__ import annotations

import asyncio
import collections
import itertools
import logging

log = logging.getLogger('ics_sim.aux')

#: 진단용 왕복 기록의 상한.  넘으면 오래된 것부터 버린다.
LOG_KEEP = 200

#: 문서 1-0 의 응답 문자열 중 "받아들여졌다"로 볼 것.
ACCEPTED = frozenset({'OK', 'SUCCESS'})
#: 명시적 거부.  재시도해도 소용없다.
REJECTED = frozenset({'BAD', 'FAILURE', 'ERROR'})
#: 아직 못 한다는 뜻.  호출측이 판단한다.
BUSY = 'WAIT'


class AuxControlClient:
    """AUX 서버에 상주 접속을 유지하고, 붙을 때마다 접속 인사(`hello`)를 보낸다.

    이 클래스는 **절대 예외를 밖으로 내보내지 않는다.**  노출 시퀀스가 AUX
    때문에 죽으면 안 되기 때문이다.  실패는 전부 반환값과 로그로 표현한다.
    """

    def __init__(self, cfg) -> None:  # noqa: ANN001  -- AuxControlCfg
        self.cfg = cfg
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._closing = False
        self._packet = itertools.count(1)
        #: 진단용 -- 보낸 것과 받은 것을 그대로 남긴다.  테스트가 이걸 본다.
        #:
        #: **상한을 둔다.**  지금은 재접속마다 `hello` 한 건이라 적게 쌓이지만,
        #: `send()` 를 부르는 자리가 늘면 하룻밤에 수천 건이 될 수 있다(셔터
        #: 통지가 있던 2026-09-12 까지는 노출당 2건이었다).  이 목록은 진단용이라
        #: 최근 것만 있으면 된다.  영구 기록은 로거가 맡는다.
        self.log: collections.deque[tuple[str, str | None]] = collections.deque(
            maxlen=LOG_KEEP)

    # -- 수명 -------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def start(self) -> None:
        """백그라운드 접속 루프를 띄운다.  서버가 없어도 즉시 반환한다."""
        if not self.cfg.enabled:
            log.info('AUX control disabled')
            return
        self._closing = False
        self._task = asyncio.create_task(self._keep_connected(),
                                         name='ics_sim.aux')

    async def stop(self) -> None:
        self._closing = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None
        await self._drop()

    async def _keep_connected(self) -> None:
        """끊기면 계속 다시 붙는다.

        **백오프는 접속에 실패했을 때만 늘린다.**  한 번 붙었다가 상대가 끊은
        경우는 기본 간격으로 되돌린다 -- 그러지 않으면 정상적으로 재접속하는
        상황에서도 대기가 계속 길어진다.
        """
        delay = self.cfg.reconnect_sec
        while not self._closing:
            try:
                await self._connect_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning('AUX connect failed (%s:%s): %s -- retry in %.0fs',
                            self.cfg.host, self.cfg.port, exc, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.cfg.reconnect_max_sec)
                continue

            delay = self.cfg.reconnect_sec      # 붙었으니 백오프를 되돌린다
            try:
                # 접속이 살아 있는 동안 여기서 대기한다.
                await self._watch()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning('AUX connection lost: %s', exc)
            if not self._closing:
                await asyncio.sleep(delay)

    async def _connect_once(self) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.cfg.host, self.cfg.port),
            timeout=self.cfg.connect_timeout)
        log.info('AUX control connected: %s:%s', self.cfg.host, self.cfg.port)
        if self.cfg.hello_subsystem and self.cfg.hello_command:
            await self.send(self.cfg.hello_subsystem, self.cfg.hello_command)

    async def _watch(self) -> None:
        """상대가 끊을 때까지 대기한다.  여기서 읽지는 않는다."""
        assert self._reader is not None
        while not self._closing and self.connected:
            await asyncio.sleep(0.5)
            if self._reader.at_eof():
                log.warning('AUX control closed by peer')
                await self._drop()
                return

    async def _drop(self) -> None:
        writer, self._writer, self._reader = self._writer, None, None
        if writer is None:
            return
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:  # noqa: BLE001  종료 중 오류는 무시한다
            pass

    # -- 발신 -------------------------------------------------------------

    def format(self, subsystem: str, command: str, packet: str) -> str:
        """규격대로 한 줄을 만든다 (종결자 제외)."""
        return (f'{self.cfg.telescope_id} {self.cfg.system} {packet} '
                f'{subsystem} {command}')

    async def send(self, subsystem: str, command: str) -> str | None:
        """커맨드 한 줄을 보내고 응답을 기다린다.

        Returns:
            응답 본문(`OK`/`BAD`/`WAIT`/값...).  접속이 없거나 타임아웃이면
            `None`.  **예외는 던지지 않는다.**
        """
        if not self.cfg.enabled:
            return None
        if not self.connected:
            log.warning('AUX not connected -- dropping %s %s',
                        subsystem, command)
            self.log.append((f'{subsystem} {command}', None))
            return None

        packet = (self.cfg.packet_id or
                  f'{self.cfg.packet_prefix}{next(self._packet)}')
        line = self.format(subsystem, command, packet)
        async with self._lock:
            try:
                self._writer.write((line + '\n').encode('ascii', 'replace'))
                await self._writer.drain()
            except Exception as exc:  # noqa: BLE001
                log.warning('AUX write failed: %s', exc)
                await self._drop()
                self.log.append((line, None))
                return None

            reply = await self._await_reply(packet)

        self.log.append((line, reply))
        self._report(line, reply)
        return reply

    def _report(self, line: str, reply: str | None) -> None:
        """응답 등급을 로그로 알린다 -- ⛔ `print()` 는 안 쓴다.

        등급은 사용자 지시(2026-08-05)를 따른다:
          * `OK`/`SUCCESS` -- 통과.  INFO 한 줄이고, 간결 화면(`[behavior]
            verbose = off`)에 낼지는 `[auxcontrol] verbose` 가 정한다
            (`essential`).  ⭐ 로그 파일에는 늘 남는다.
          * 그 밖의 값 -- 조회 명령의 값이나 `ECHO` 의 되울림(규격 1-4: 답이
            `OK` 가 아니라 보낸 문자열 그대로다).  거부가 아니므로 `OK` 와 같게
            다룬다 -- ⚠️ 2026-09-23 까지는 `essential` 표시가 없어 **간결 화면에도
            늘 나갔다**(접속 인사 `hello_cmd = ALL ECHO …` 의 답이 이 갈래다).
          * `BAD`/`FAILURE`/`ERROR` -- 경고.  명시적 거부다.
          * `WAIT` -- 경고.  거부는 아니고 "아직 못 한다"는 뜻이다.
          * 무응답 -- 경고.  규격 2-4 상 ID/System 오타여도 침묵이므로
            설정 문제일 수 있다는 점을 detail 로 함께 알린다.

        ⚠️ 종전에는 로그와 **별도로** 콘솔에 색을 입혀 한 번 더 찍었다
        (`print`).  같은 내용이 두 줄로 보였고 입력 중인 프롬프트를 덮었다.
        """
        if reply is None:
            log.warning('AUX no reply within %.1fs for %r',
                        self.cfg.ack_timeout, line,
                        extra={'detail': 'AUX_TelID/AUX_SysID 와 서버 주소를 '
                                         '확인할 것 -- 규격 2-4 상 틀리면 서버가 '
                                         '침묵한다'})
        elif reply in REJECTED:
            log.warning('AUX rejected %r -> %s', line, reply,
                        extra={'detail': '명시적 거부다 -- 다시 보내도 소용없다 '
                                         '(문서 1-0)'})
        elif reply == BUSY:
            log.warning('AUX busy for %r -> WAIT', line,
                        extra={'detail': '이전 동작이 안 끝났다 (거부 아님)'})
        elif reply in ACCEPTED:
            log.info('AUX %s -> %s', line, reply,
                     extra={'essential': bool(self.cfg.verbose)})
        else:
            # 조회 명령의 값 · `ECHO` 의 되울림.  거부가 아니므로 `OK` 와 같게
            # 정보로 남기고, 간결 화면에 낼지는 `[auxcontrol] verbose` 가 정한다.
            log.info('AUX %s -> %s', line, reply,
                     extra={'essential': bool(self.cfg.verbose)})

    async def _await_reply(self, packet: str) -> str | None:
        """우리 packet ID 가 붙은 응답 줄을 골라 본문만 돌려준다."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.cfg.ack_timeout
        while True:
            budget = deadline - loop.time()
            if budget <= 0:
                return None
            try:
                raw = await asyncio.wait_for(self._reader.readline(),
                                             timeout=budget)
            except asyncio.TimeoutError:
                return None
            except Exception as exc:  # noqa: BLE001
                log.warning('AUX read failed: %s', exc)
                await self._drop()
                return None
            if not raw:
                await self._drop()
                return None

            parts = raw.decode('ascii', 'replace').strip().split(' ', 3)
            if len(parts) < 4:
                continue                      # 형식 미달 -- 무시하고 더 읽는다
            tel, system, pid, body = parts
            if tel != self.cfg.telescope_id or system != self.cfg.system:
                continue
            if pid != packet:
                log.debug('AUX stale reply for packet %s (waiting %s)',
                          pid, packet)
                continue
            return body.strip()

    # ⛔ **셔터 개폐를 AUX 에 알리던 자리는 걷었다** (운영자 2026-09-12) --
    #    FSA HW 가 그 명령을 못 받는다는 TCS 검토 결과다.  `send()` 를 직접
    #    쓰는 `hello`(접속 인사)만 남는다.

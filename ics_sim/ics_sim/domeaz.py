#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""돔 방위 셋의 원천 -- redis 에서 `DSAZ`·`DSTELAZ`·`DAZERR` 를 읽는다.

## 왜 redis 인가

돔 방위는 **`AUXSTATUS` 에 아예 없었다** -- AUX 는 돔 *고도*만 보낸다.  그래서
벤치 헤더의 `DSAZ`·`DSTELAZ`·`DAZERR` 가 `NC` 였고, 그것은 결함이 아니라
**자료가 안 오는 것**이었다 (`ics_archon/DevNote.md` 11.52).

⭐ raw spec 은 **처음부터 이 길을 열어 두었다** -- 5.7절의 돔 카드 출처가
`TCS relay or REDIS` 이고(규격 v1.12 · 원장 v1.18 3.6절), 그 `REDIS` 가 이
모듈이다.  ⭐ **운영자 확정 2026-09-11**: 돔 제어 프로그램이 redis 에 실어
두는 셋을 ICS/ICG 가 직접 읽는다.

| redis 키 | FITS 카드 | 뜻 |
|---|---|---|
| `dome_tel_az` | `DSTELAZ` | 돔이 보고하는 **망원경** 방위 |
| `dome_az` | `DSAZ` | **돔 셔터** 방위 |
| `dome_del_az` | `DAZERR` | 돔 제어 프로그램이 낸 **방위차** |

⚠️ **`DALTERR` 는 이 셋에 없다.**  운영자 지시의 첫 문면은 `dome_del_az` 를
`DALTERR` 에 넣는 것이었으나, `DALTERR` 는 **고도** 어긋남
(`DSALT` − `DSTELALT`, `AUXSTATUS` 에서 실제로 값이 온다)이고 **방위** 어긋남
카드는 `DAZERR` 로 따로 있다.  확인 결과 `DAZERR` 가 맞는 자리였다 (운영자
확정 2026-09-11).  ⛔ `DALTERR` 는 종전 계산값 그대로다 -- 방위값으로 덮으면
실제로 오고 있는 고도 어긋남이 사라진다.

## ⭐ redis 가 **유일한 출처**다 (운영자 확정 2026-09-11)

세 카드는 redis 만 본다.  ⛔ TC 가 나중에 `TCSSTATUS` 에 `DSAZ`/`DSTELAZ` 를
실어 보내더라도 그 값을 쓰지 않는다 -- 출처가 둘이면 헤더만 보고는 어느 쪽
값인지 가릴 수 없다.

⭐ **예외 하나**: `dome_del_az` 만 없고 `dome_az`·`dome_tel_az` 는 있을 때는
`DAZERR = dome_az − dome_tel_az` 를 접어서 낸다 (`telemetry._sync_error_az`).
그것은 규격 5.7절이 원래 정한 `ICS calculation` 이고 **피연산 값도 redis 것**
이라 "redis 만 본다" 를 벗어나지 않는다.  ⛔ 둘 다 손에 들고 있는데 `NC` 를
싣는 것은 실측을 버리는 것이다.

## ⭐ 키가 없으면 `NC` 다 -- 옛 값을 이어 싣지 않는다

돔 제어 프로그램은 **키에 TTL(수백 ms)을 걸어** 둔다.  값을 못 넣으면 키가
사라지므로, **키가 없다 = 지금 자료가 없다** 다.  그때 카드는 sentinel `'NC'`
다 (규격 5.0절).

⛔ **직전 값을 캐시해서 이어 싣지 않는다.**  그러면 돔이 멈춘 뒤에도 마지막
방위가 노출마다 새 값처럼 실려 나가고, 헤더만 보는 하류(converter·아카이브)에
그것이 낡았다는 사실이 **어디에도 안 남는다**.  Radionode 의 `stale_after` ·
진공 `Alive` 카운터와 같은 정신이다 -- **신선도가 값의 일부다.**

## 의존성을 더하지 않는다

`redis-py` 를 쓰지 않는다.  `INSTALL.md` 의 런타임 의존은 `python3-numpy`
하나이고 나머지는 표준 라이브러리다 (`astropy` 도 선택).  ⭐ 우리가 쓰는 것은
**`MGET` 한 번**이라, 필요한 RESP 는 배열 하나와 벌크 문자열뿐이다 -- 아래
`_read_reply()` 가 그 전부다.  `auxcontrol.py` 가 같은 방식(표준
`asyncio.open_connection`)으로 AUX TCP 를 물고 있어 전례도 여기 있다.

## 노출을 막지 않는다

* **이벤트 루프를 막지 않는다** -- `asyncio` 스트림이라 블로킹 호출이 없다
  (Radionode 는 `urllib` 이라 `to_thread` 가 필요했다; 여기는 아니다).
* 왕복 상한이 `timeout`(기본 0.3초)이고, 이 읽기는 `TCSSTATUS` 질의와
  **나란히** 돈다 -- 질의 자체가 초 단위라 노출 시간이 늘지 않는다.
* **실패 경로가 전부 `{}` 로 끝난다** -- 접속 거부·시한·프로토콜 오류·엉뚱한
  값 모두 "자료 없음" 이고 카드는 `NC` 가 된다.  예외를 부르는 쪽으로 올리지
  않는다.

## 접속은 물고 있는다

guide 는 주기가 **1.3초**라 노출마다 접속하면 왕복이 배가 된다.  그래서 한 번
붙으면 물고 있고, 끊기면 **다음 읽기에서** 다시 붙는다 (재접속 태스크를 따로
두지 않는다 -- 읽기가 노출마다 오므로 그것이 곧 재시도다).

⚠️ **로그는 상태가 바뀔 때만** 남긴다.  노출마다 경고하면 하룻밤에 천 줄이
되고, 그러면 사람이 경고를 무시하는 것을 학습한다 (`telemetry.check_telid`
가 `TELID` 를 그렇게 다룬다).
"""

from __future__ import annotations

import asyncio
import logging

from .config import DomeCfg

log = logging.getLogger('ics_sim.domeaz')

#: redis 키 -> FITS 카드.  ⛔ **정본이다** -- 키 *이름*은 ini 로 바꿀 수 있지만
#: (`[dome] key_tel_az` …) 어느 카드로 가는지는 규격 5.7절 소관이라 코드에 둔다.
CARD_OF = {
    'tel_az': 'DSTELAZ',
    'az': 'DSAZ',
    'del_az': 'DAZERR',
}

#: `CARD_OF` 의 자리 순서.  `MGET` 응답이 요청 순서대로 오므로 이 순서가
#: 요청과 응답을 잇는 유일한 끈이다.
ORDER = ('tel_az', 'az', 'del_az')

#: 이 모듈이 채우는 카드 전체.  ⭐ 부르는 쪽이 *"내가 못 채운 것은 NC"* 를
#: 알아야 하므로 함께 내보낸다.
CARDS = tuple(CARD_OF[name] for name in ORDER)


class _Disconnect(Exception):
    """이 왕복을 포기하고 접속을 버린다는 내부 신호.  밖으로 안 나간다."""


def _encode(args: list[str]) -> bytes:
    """RESP 배열 하나로 명령을 만든다 (`*N` + `$len` 벌크들).

    redis 는 인라인 명령(`MGET a b\\r\\n`)도 받지만 배열로 보낸다 -- 키에
    공백이 섞여도 깨지지 않는다.
    """
    out = [f'*{len(args)}\r\n'.encode()]
    for arg in args:
        raw = arg.encode('utf-8')
        out.append(b'$%d\r\n' % len(raw))
        out.append(raw + b'\r\n')
    return b''.join(out)


async def _line(reader: asyncio.StreamReader) -> bytes:
    """`\\r\\n` 까지 한 줄.  끊겼으면 `_Disconnect`."""
    raw = await reader.readline()
    if not raw.endswith(b'\n'):
        # readline 이 개행 없이 돌아오는 것은 EOF 뿐이다.
        raise _Disconnect('connection closed')
    return raw[:-2] if raw.endswith(b'\r\n') else raw[:-1]


async def _read_reply(reader: asyncio.StreamReader) -> object:
    """RESP 한 덩이.  우리가 쓰는 형만 안다.

    Returns:
        `str` (단순 문자열·벌크) · `None` (널 벌크 = **키가 없다**) ·
        `int` · `list` (배열).

    Raises:
        _Disconnect: 끊김 · 오류 응답(`-ERR …`) · 모르는 형.

    ⛔ 오류 응답을 값으로 돌려주지 않는다 -- `-NOAUTH …` 를 방위값으로 헤더에
    실으면 안 된다.  ⭐ RESP3 의 `%`·`>` 같은 형은 우리가 `HELLO` 를 안 보내니
    올 수 없고, 오면 "모르는 형" 으로 접속을 버린다 (조용히 오독하는 것보다
    낫다).
    """
    head = await _line(reader)
    if not head:
        raise _Disconnect('empty reply')
    kind, body = head[:1], head[1:].decode('utf-8', 'replace')
    if kind == b'+':
        return body
    if kind == b'-':
        raise _Disconnect('server error: %s' % body)
    if kind == b':':
        try:
            return int(body)
        except ValueError as exc:
            raise _Disconnect('bad integer: %r' % body) from exc
    if kind == b'$':
        try:
            size = int(body)
        except ValueError as exc:
            raise _Disconnect('bad bulk length: %r' % body) from exc
        if size < 0:
            return None            # 널 벌크 -- 키가 없다 (TTL 만료가 이것)
        raw = await reader.readexactly(size + 2)   # 값 + CRLF
        return raw[:size].decode('utf-8', 'replace')
    if kind == b'*':
        try:
            count = int(body)
        except ValueError as exc:
            raise _Disconnect('bad array length: %r' % body) from exc
        if count < 0:
            return None
        return [await _read_reply(reader) for _ in range(count)]
    raise _Disconnect('unknown reply type %r' % head[:1])


class DomeRedis:
    """`DSTELAZ`·`DSAZ`·`DAZERR` 를 redis 에서 읽어 오는 작은 클라이언트.

    ⭐ 쓰는 법은 `read()` 하나다.  **없는 카드는 딕셔너리에 안 들어간다** --
    부르는 쪽(`telemetry.fits_header_dict`)이 `'NC'` 를 채운다.
    """

    def __init__(self, cfg: DomeCfg) -> None:
        self.cfg = cfg
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        #: 마지막으로 로그에 남긴 실패 사유.  같은 사유는 다시 안 적는다.
        self._last_fault: str | None = None
        #: 한 번이라도 값을 받았나.  첫 성공을 알리는 데만 쓴다.
        self._ever_ok = False

    @property
    def enabled(self) -> bool:
        return self.cfg.source == 'redis'

    @property
    def keys(self) -> list[str]:
        """ini 가 정한 redis 키 이름 셋, `ORDER` 자리 순서."""
        return [getattr(self.cfg, 'key_' + name) for name in ORDER]

    def describe(self) -> str:
        """기동 배너용 한 줄.  ⭐ *"꺼져 있는데 켠 줄 알았다"* 를 막는다."""
        if not self.enabled:
            return 'dome azimuth source: off (DSAZ/DSTELAZ/DAZERR stay NC)'
        return 'dome azimuth source: redis %s:%d keys %s' % (
            self.cfg.host, self.cfg.port, ','.join(self.keys))

    # -- 읽기 -------------------------------------------------------------

    async def read(self) -> dict[str, str]:
        """돔 방위 셋을 한 번 읽는다.

        Returns:
            `{카드이름: 값}`.  **없는 키·빈 값·수치가 아닌 값은 빠진다.**
            꺼져 있거나 어떤 이유로든 실패하면 `{}`.

        ⛔ **예외를 올리지 않는다.**  이 값은 노출을 막을 근거가 못 된다.
        """
        if not self.enabled:
            return {}
        async with self._lock:      # 노출과 HK 가 겹쳐 부를 수 있다
            try:
                return await asyncio.wait_for(self._read_once(),
                                              timeout=self.cfg.timeout)
            except asyncio.TimeoutError:
                await self._drop()
                self._fault('timed out after %gs' % self.cfg.timeout)
                return {}
            except _Disconnect as exc:
                await self._drop()
                self._fault(str(exc))
                return {}
            except (OSError, asyncio.IncompleteReadError) as exc:
                await self._drop()
                self._fault('%s: %s' % (type(exc).__name__, exc))
                return {}
            except Exception as exc:    # noqa: BLE001
                # ⛔ 여기 오는 것은 우리 결함이다.  그래도 노출은 막지 않는다.
                await self._drop()
                log.exception('dome redis read failed unexpectedly -- %s', exc)
                return {}

    async def _read_once(self) -> dict[str, str]:
        await self._connect()
        assert self._reader is not None and self._writer is not None
        self._writer.write(_encode(['MGET'] + self.keys))
        await self._writer.drain()
        reply = await _read_reply(self._reader)
        if not isinstance(reply, list) or len(reply) != len(ORDER):
            raise _Disconnect('MGET returned %r' % (reply,))
        out: dict[str, str] = {}
        for name, value in zip(ORDER, reply):
            card = CARD_OF[name]
            if value is None:
                continue            # 키가 없다 -- TTL 만료.  카드는 NC 가 된다
            text = str(value).strip()
            if not text:
                continue
            try:
                float(text)
            except ValueError:
                # ⛔ 수치가 아닌 것을 방위 카드에 싣지 않는다.  ⚠️ 값을
                # **고치지는 않는다** -- 버리고 원문을 로그에 남긴다.
                self._fault('%s is not a number: %r' % (name, text))
                continue
            # ⭐ **원문 그대로 싣는다** -- 자리수를 우리가 다시 맞추지 않는다.
            # 다른 중계 카드(`DSALT`·`DSTELALT`)도 보내온 문자열 그대로다.
            out[card] = text
        if out and not self._ever_ok:
            self._ever_ok = True
            log.info('dome redis connected -- %d of %d keys present',
                     len(out), len(ORDER),
                     extra={'detail': '%s:%d 에서 %s 를 받았다'
                                      % (self.cfg.host, self.cfg.port,
                                         ','.join(sorted(out)))})
        if out:
            self._last_fault = None
        return out

    # -- 접속 -------------------------------------------------------------

    async def _connect(self) -> None:
        """안 붙어 있으면 붙는다.  이미 붙어 있으면 아무것도 안 한다."""
        if self._writer is not None and not self._writer.is_closing():
            return
        await self._drop()
        self._reader, self._writer = await asyncio.open_connection(
            self.cfg.host, self.cfg.port)
        if self.cfg.password:
            await self._hello_cmd(['AUTH'] + (
                [self.cfg.username, self.cfg.password] if self.cfg.username
                else [self.cfg.password]))
        if self.cfg.db:
            await self._hello_cmd(['SELECT', str(self.cfg.db)])

    async def _hello_cmd(self, args: list[str]) -> None:
        """접속 직후 한 번 나가는 명령(`AUTH`·`SELECT`).  실패는 `_Disconnect`."""
        assert self._reader is not None and self._writer is not None
        self._writer.write(_encode(args))
        await self._writer.drain()
        await _read_reply(self._reader)     # `-ERR` 이면 여기서 튄다

    async def _drop(self) -> None:
        writer, self._writer, self._reader = self._writer, None, None
        if writer is None:
            return
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:           # noqa: BLE001 -- 닫는 중의 실패는 무의미
            pass

    async def close(self) -> None:
        """종료 경로에서 부른다.  ⭐ 두 번 불러도 된다."""
        async with self._lock:
            await self._drop()

    # -- 로그 -------------------------------------------------------------

    def _fault(self, reason: str) -> None:
        """실패를 **사유가 바뀔 때만** 남긴다.

        ⚠️ 노출마다 부르는 자리라, 같은 사유를 매번 적으면 하룻밤에 천 줄이
        된다.  ⭐ 그렇다고 통째로 조용하면 *"왜 NC 인지"* 를 알 길이 없어서,
        **처음 한 번과 사유가 바뀔 때**는 반드시 적는다.
        """
        if reason == self._last_fault:
            return
        self._last_fault = reason
        log.warning('dome redis unavailable -- %s', reason,
                    extra={'detail': 'DSAZ/DSTELAZ/DAZERR 가 NC 로 나간다 '
                                     '(%s:%d). 같은 사유는 다시 적지 않는다'
                                     % (self.cfg.host, self.cfg.port)})

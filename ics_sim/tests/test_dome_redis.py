#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""돔 방위 셋의 redis 원천 -- `DSTELAZ`·`DSAZ`·`DAZERR` (2026-09-11).

`ics_sim.domeaz` + `ics_sim.telemetry._apply_dome` 를 **가짜 redis 서버**로
시험한다.  ⭐ 모듈이 `ics_sim` 것이므로 시험도 여기 둔다 -- `ics_sim` 은 홀로
설 수 있어야 한다.  시퀀서 배선(ICS·ICG)은 `ics_archon/tests/test_dome_wiring.py` 몫이다.  ⛔ **실서버에 붙지 않는다** -- 벤치·관측소 기계에는 진짜 redis 가
돌고 있어서, 기본값(`off`)이나 실서버에 기대는 시험은 *"내 기계에서는
통과하고 실기에서만 깨지는"* 부류가 된다 (DevNote 11.20 의 교훈).

가짜 서버는 `MGET` 하나만 안다 -- 우리가 보내는 것이 그것뿐이다.
"""

from __future__ import annotations

import asyncio
import logging

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                os.pardir)))

from ics_sim import domeaz                     # noqa: E402
from ics_sim.config import SimConfig           # noqa: E402
from ics_sim.telemetry import TelemetryRelay   # noqa: E402


# ---------------------------------------------------------------------------
# 가짜 redis
# ---------------------------------------------------------------------------

class FakeRedis:
    """`MGET` 만 답하는 최소 RESP 서버.

    `store` 에 있는 키는 벌크 문자열로, 없는 키는 **널 벌크(`$-1`)** 로 답한다
    -- 그것이 TTL 만료의 실제 모양이다.
    """

    def __init__(self, store: dict[str, str] | None = None) -> None:
        self.store = dict(store or {})
        self.server: asyncio.AbstractServer | None = None
        self.port = 0
        #: 받은 명령 줄 목록 (검증용).  접속 재사용 판정에 쓴다.
        self.commands: list[list[str]] = []
        #: 접속 횟수 -- 물고 있는지 보는 자다.
        self.connections = 0
        #: 답을 이만큼 미룬다 [s] -- 시한 초과 경로를 만든다.
        self.delay = 0.0
        #: True 면 `MGET` 에 `-ERR` 로 답한다.
        self.fail = False
        #: ⚠️ **핸들러가 쥔 writer** -- 아래 `stop()` 참조.
        self._writers: list = []

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._serve, '127.0.0.1', 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        """⚠️ **서버 쪽 writer 를 먼저 닫는다.**

        ⛔ 안 닫으면 `Server.wait_closed()` 가 **영영 안 돌아온다** (py3.12 는
        핸들러의 transport 가 다 닫히기를 기다린다) -- 클라이언트가 이미 접속을
        닫았어도 마찬가지다.  ⚠️ 핸들러의 `finally` 에만 기대면 예외 경로에서
        새므로 여기서도 닫는다 (2026-09-11 에 자매 파일이 그걸로 멈췄다).
        """
        for writer in self._writers:
            try:
                writer.close()
            except Exception:       # noqa: BLE001
                pass
        self._writers.clear()
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def _serve(self, reader: asyncio.StreamReader,
                     writer: asyncio.StreamWriter) -> None:
        self.connections += 1
        self._writers.append(writer)
        try:
            while True:
                args = await self._read_command(reader)
                if args is None:
                    return
                self.commands.append(args)
                if self.delay:
                    await asyncio.sleep(self.delay)
                writer.write(self._reply(args))
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            return
        finally:
            try:
                writer.close()
            except Exception:       # noqa: BLE001
                pass

    async def _read_command(self, reader) -> list[str] | None:  # noqa: ANN001
        head = await reader.readline()
        if not head:
            return None
        if not head.startswith(b'*'):
            return None
        count = int(head[1:].strip())
        args = []
        for _ in range(count):
            size = int((await reader.readline())[1:].strip())
            raw = await reader.readexactly(size + 2)
            args.append(raw[:size].decode())
        return args

    def _reply(self, args: list[str]) -> bytes:
        word = args[0].upper()
        if word in ('AUTH', 'SELECT'):
            return b'+OK\r\n'
        if word != 'MGET':
            return b'-ERR unknown command\r\n'
        if self.fail:
            return b'-ERR NOAUTH Authentication required.\r\n'
        out = [b'*%d\r\n' % (len(args) - 1)]
        for key in args[1:]:
            if key in self.store:
                raw = self.store[key].encode()
                out.append(b'$%d\r\n' % len(raw) + raw + b'\r\n')
            else:
                out.append(b'$-1\r\n')      # 키 없음 = TTL 만료
        return b''.join(out)


def _cfg(port: int, **kw) -> SimConfig:
    """`[dome] source = redis` 인 설정.  포트는 가짜 서버 것."""
    cfg = SimConfig()
    cfg.dome.source = 'redis'
    cfg.dome.host = '127.0.0.1'
    cfg.dome.port = port
    cfg.dome.timeout = 2.0      # 시험은 로컬이라 넉넉히 -- 시한 시험만 따로 조인다
    for key, value in kw.items():
        setattr(cfg.dome, key, value)
    return cfg


def _relay(cfg: SimConfig) -> TelemetryRelay:
    return TelemetryRelay(cfg, lambda *a, **k: None)


def _run(store, body, **cfgkw):  # noqa: ANN001
    """가짜 서버를 띄우고 `body(relay, fake)` 를 돌린다."""
    async def _go():
        fake = FakeRedis(store)
        await fake.start()
        relay = _relay(_cfg(fake.port, **cfgkw))
        try:
            return await body(relay, fake)
        finally:
            await relay.dome.close()
            await fake.stop()
    return asyncio.run(_go())


#: 규격 5.7절 카드 셋.  ⭐ 이름을 여기 한 번만 적는다.
TEL, AZ, ERR = 'DSTELAZ', 'DSAZ', 'DAZERR'

FULL = {'dome_tel_az': '12.1', 'dome_az': '12.3', 'dome_del_az': '+0.2'}


# ---------------------------------------------------------------------------
# 1) 값이 다 있을 때
# ---------------------------------------------------------------------------

def test_three_keys_land_in_three_cards():
    """`dome_tel_az`/`dome_az`/`dome_del_az` -> `DSTELAZ`/`DSAZ`/`DAZERR`."""
    async def body(relay, fake):
        assert await relay.query_dome() is True
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run(FULL, body)
    assert h[TEL] == '12.1'
    assert h[AZ] == '12.3'
    assert h[ERR] == '+0.2'


def test_values_are_carried_verbatim():
    """⭐ 자리수를 우리가 다시 맞추지 않는다 -- 다른 중계 카드와 같은 규범."""
    async def body(relay, fake):
        await relay.query_dome()
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run({'dome_tel_az': '123.456', 'dome_az': '7.8',
              'dome_del_az': '-0.75'}, body)
    assert h[TEL] == '123.456' and h[AZ] == '7.8' and h[ERR] == '-0.75'


def test_the_wire_command_is_a_single_mget():
    """⭐ 왕복 하나다 -- 키마다 `GET` 을 내면 노출 개시에 세 번 왕복한다."""
    async def body(relay, fake):
        await relay.query_dome()
        return list(fake.commands)
    cmds = _run(FULL, body)
    assert cmds == [['MGET', 'dome_tel_az', 'dome_az', 'dome_del_az']]


def test_key_names_come_from_the_ini():
    """키 *이름*은 ini 소관이다 (카드 배정은 아니다 -- `domeaz.CARD_OF`)."""
    async def body(relay, fake):
        await relay.query_dome()
        return list(fake.commands), relay.fits_header_dict('2026-09-11T00:00:00.000')
    cmds, h = _run({'a': '1.0', 'b': '2.0', 'c': '3.0'}, body,
                   key_tel_az='a', key_az='b', key_del_az='c')
    assert cmds == [['MGET', 'a', 'b', 'c']]
    assert h[TEL] == '1.0' and h[AZ] == '2.0' and h[ERR] == '3.0'


# ---------------------------------------------------------------------------
# 2) 키가 사라졌을 때 (TTL 만료) -- 이 기능의 핵심 경로
# ---------------------------------------------------------------------------

def test_missing_keys_become_nc():
    """⛔ TTL 이 지나 키가 없으면 세 카드가 `NC` 다 (규격 5.0절)."""
    async def body(relay, fake):
        assert await relay.query_dome() is False
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run({}, body)
    assert h[TEL] == 'NC' and h[AZ] == 'NC' and h[ERR] == 'NC'


def test_del_az_alone_is_recomputed_from_the_other_two():
    """⭐ `dome_del_az` 만 없으면 나머지 둘로 계산한다 (규격 5.7 ICS calculation).

    ⛔ 손에 든 값 둘로 낼 수 있는 것을 `NC` 로 싣는 것은 실측을 버리는 것이다.
    """
    async def body(relay, fake):
        await relay.query_dome()
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run({'dome_tel_az': '12.1', 'dome_az': '12.3'}, body)
    assert h[TEL] == '12.1' and h[AZ] == '12.3'
    assert h[ERR] == '+0.2'


def test_recomputed_del_az_folds_to_plus_minus_180():
    """방위는 순환이다 -- `270` 은 `-90` 이다 (운영자 2026-09-09)."""
    async def body(relay, fake):
        await relay.query_dome()
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run({'dome_tel_az': '10.0', 'dome_az': '280.0'}, body)
    assert h[ERR] == '-90.0'


def test_one_missing_operand_leaves_del_az_nc():
    """⛔ 계산값을 지어내지 않는다 -- 피연산 하나가 없으면 `NC`."""
    async def body(relay, fake):
        await relay.query_dome()
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run({'dome_az': '12.3'}, body)
    assert h[AZ] == '12.3'
    assert h[TEL] == 'NC' and h[ERR] == 'NC'


def test_an_empty_value_counts_as_missing():
    """키는 있는데 값이 빈 문자열이면 자료가 없는 것이다."""
    async def body(relay, fake):
        await relay.query_dome()
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run({'dome_tel_az': '', 'dome_az': '12.3', 'dome_del_az': ''}, body)
    assert h[TEL] == 'NC' and h[AZ] == '12.3' and h[ERR] == 'NC'


def test_a_non_numeric_value_is_refused_not_relayed():
    """⛔ 수치가 아닌 것을 방위 카드에 싣지 않는다.  나머지는 살린다."""
    async def body(relay, fake):
        await relay.query_dome()
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run({'dome_tel_az': 'ERROR', 'dome_az': '12.3',
              'dome_del_az': '+0.2'}, body)
    assert h[TEL] == 'NC'
    assert h[AZ] == '12.3' and h[ERR] == '+0.2'


def test_a_stale_snapshot_is_never_carried_forward():
    """⛔⛔ **옛 방위를 새 값처럼 싣지 않는다** -- 이 기능의 제1 규범.

    첫 노출에서 받은 값이 다음 노출에 남아 있으면, 돔이 멈춘 뒤에도 마지막
    방위가 밤새 새 값처럼 나간다.
    """
    async def body(relay, fake):
        await relay.query_dome()
        first = relay.fits_header_dict('2026-09-11T00:00:00.000')
        fake.store.clear()              # TTL 만료
        await relay.query_dome()
        return first, relay.fits_header_dict('2026-09-11T00:00:01.000')
    first, second = _run(FULL, body)
    assert first[AZ] == '12.3'
    assert second[TEL] == 'NC' and second[AZ] == 'NC' and second[ERR] == 'NC'


# ---------------------------------------------------------------------------
# 3) 서버가 없거나 고장났을 때 -- 노출을 막지 않는다
# ---------------------------------------------------------------------------

def test_an_unreachable_server_yields_nc_without_raising():
    """⛔ 접속 거부는 예외가 아니라 "자료 없음" 이다."""
    async def _go():
        # 아무도 안 듣는 포트.  ⭐ 서버를 띄웠다 닫아 **확실히 빈** 포트를 얻는다.
        fake = FakeRedis({})
        await fake.start()
        port = fake.port
        await fake.stop()
        relay = _relay(_cfg(port))
        assert await relay.query_dome() is False
        h = relay.fits_header_dict('2026-09-11T00:00:00.000')
        await relay.dome.close()
        return h
    h = asyncio.run(_go())
    assert h[TEL] == 'NC' and h[AZ] == 'NC' and h[ERR] == 'NC'


def test_a_server_error_reply_never_reaches_a_card():
    """⛔ `-NOAUTH …` 를 방위값으로 실으면 안 된다."""
    async def body(relay, fake):
        fake.fail = True
        assert await relay.query_dome() is False
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run(FULL, body)
    for card in (TEL, AZ, ERR):
        assert h[card] == 'NC'


def test_a_slow_server_times_out_and_gives_nc():
    """상한을 넘으면 포기한다 -- 늦게 온 방위는 이미 낡은 값이다."""
    async def body(relay, fake):
        fake.delay = 1.0
        relay.cfg.dome.timeout = 0.05
        assert await relay.query_dome() is False
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run(FULL, body)
    assert h[TEL] == 'NC' and h[AZ] == 'NC' and h[ERR] == 'NC'


def test_the_read_recovers_after_a_failure():
    """실패 뒤 다음 읽기에서 다시 붙는다 -- 재접속 태스크를 따로 두지 않는 근거."""
    async def body(relay, fake):
        fake.fail = True
        await relay.query_dome()
        fake.fail = False
        assert await relay.query_dome() is True
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run(FULL, body)
    assert h[AZ] == '12.3'


def test_a_failure_is_logged_once_per_reason(caplog):
    """⚠️ 노출마다 같은 경고를 적으면 하룻밤에 천 줄이 된다."""
    async def body(relay, fake):
        fake.fail = True
        with caplog.at_level(logging.WARNING, logger='ics_sim.domeaz'):
            for _ in range(5):
                await relay.query_dome()
            return [r.getMessage() for r in caplog.records
                    if 'dome redis unavailable' in r.getMessage()]
    msgs = _run(FULL, body)
    assert len(msgs) == 1, msgs


# ---------------------------------------------------------------------------
# 4) 출처가 하나여야 한다
# ---------------------------------------------------------------------------

def test_redis_is_the_only_source_when_it_is_on():
    """⛔ 켜져 있으면 **와이어값을 안 본다** (운영자 확정 2026-09-11).

    출처가 둘이면 헤더만 보고 어느 쪽 값인지 가릴 수 없다.
    """
    async def body(relay, fake):
        relay.tcs_fields = [('DSAZ', '999.9'), ('DSTELAZ', '888.8'),
                            ('DAZERR', '+7.7')]
        relay.last_tcs_ok = True
        await relay.query_dome()
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run(FULL, body)
    assert h[TEL] == '12.1' and h[AZ] == '12.3' and h[ERR] == '+0.2'


def test_a_missing_key_beats_a_wire_value():
    """⛔ 켜져 있는데 키가 없으면 `NC` 다 -- 와이어값으로 메우지 않는다."""
    async def body(relay, fake):
        relay.tcs_fields = [('DSAZ', '999.9'), ('DSTELAZ', '888.8')]
        relay.last_tcs_ok = True
        await relay.query_dome()
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run({}, body)
    assert h[TEL] == 'NC' and h[AZ] == 'NC' and h[ERR] == 'NC'


def test_source_off_keeps_the_legacy_wire_path():
    """⭐ `off` 면 **종전 그대로**다 -- 견본 pair 의 바이트 대사가 그 경로다.

    (`ics_sim/tests/test_raw_draft.py` 가 세 값을 와이어에 실어 역산한다.)
    """
    cfg = SimConfig()               # 기본값 -- source = off
    assert cfg.dome.source == 'off'
    relay = _relay(cfg)
    relay.tcs_fields = [('DSAZ', '12.3'), ('DSTELAZ', '12.1')]
    relay.last_tcs_ok = True
    h = relay.fits_header_dict('2026-09-11T00:00:00.000')
    assert h[AZ] == '12.3' and h[TEL] == '12.1'
    assert h[ERR] == '+0.2'         # ICS calculation


def test_an_unknown_source_word_is_off_and_warns():
    """⛔ 오타를 조용히 삼키면 세 카드가 영구히 `NC` 다."""
    cfg = SimConfig()
    cfg.dome.source = 'REDIS_'      # 오타
    relay = _relay(cfg)
    assert relay.dome.enabled is False
    assert any('[dome] source' in w for w in cfg.validate())


# ---------------------------------------------------------------------------
# 5) `DALTERR` 를 건드리지 않는다 -- 처음 지시의 문면이 이 카드였다
# ---------------------------------------------------------------------------

def test_dalterr_is_altitude_and_never_takes_a_dome_azimuth():
    """⛔⛔ `DALTERR` = 고도 어긋남 (`DSALT` − `DSTELALT`).

    `dome_del_az` 는 **방위**차라 `DAZERR` 자리다.  ⚠️ 처음 지시의 문면이
    `DALTERR` 였고(운영자 2026-09-11), 그대로 넣으면 `AUXSTATUS` 에서 실제로
    오고 있는 고도 어긋남이 방위값으로 덮인다.  이 시험이 그 길을 막는다.
    """
    async def body(relay, fake):
        relay.aux_fields = [('DSALT', '87.7'), ('DSTEL', '88.1')]
        relay.last_aux_ok = True
        await relay.query_dome()
        return relay.fits_header_dict('2026-09-11T00:00:00.000')
    h = _run({'dome_tel_az': '12.1', 'dome_az': '12.3',
              'dome_del_az': '+0.2'}, body)
    assert h['DALTERR'] == '-0.4', '고도 어긋남이 방위값으로 덮였다'
    assert h[ERR] == '+0.2'


def test_dome_cards_are_exactly_three():
    """이 모듈이 채우는 카드는 셋뿐이다 -- 늘어나면 규격 5.7절과 함께 고칠 것."""
    assert domeaz.CARDS == ('DSTELAZ', 'DSAZ', 'DAZERR')
    assert set(domeaz.CARD_OF.values()) == set(domeaz.CARDS)
    assert 'DALTERR' not in domeaz.CARDS


# ---------------------------------------------------------------------------
# 6) 접속을 물고 있다 (guide 주기 1.3초)
# ---------------------------------------------------------------------------

def test_the_connection_is_reused_across_reads():
    """⭐ 노출마다 붙지 않는다 -- guide 는 주기가 1.3초다."""
    async def body(relay, fake):
        for _ in range(4):
            await relay.query_dome()
        return fake.connections, len(fake.commands)
    conns, cmds = _run(FULL, body)
    assert cmds == 4
    assert conns == 1, f'접속을 {conns}번 새로 맺었다'


def test_close_is_idempotent():
    """종료 경로가 두 번 불러도 된다."""
    async def body(relay, fake):
        await relay.query_dome()
        await relay.dome.close()
        await relay.dome.close()
        return True
    assert _run(FULL, body) is True


def test_auth_and_select_run_once_on_connect():
    """`password`/`db` 를 적으면 접속 직후 한 번씩 나간다."""
    async def body(relay, fake):
        await relay.query_dome()
        await relay.query_dome()
        return [c[0] for c in fake.commands]
    words = _run(FULL, body, password='pw', db=3)
    assert words == ['AUTH', 'SELECT', 'MGET', 'MGET']


def test_describe_says_which_source_is_live():
    """기동 배너 한 줄 -- *"켠 줄 알았는데 꺼져 있었다"* 를 막는다."""
    off = _relay(SimConfig())
    assert 'off' in off.dome.describe()
    on = _relay(_cfg(6379))
    assert 'redis' in on.dome.describe() and '6379' in on.dome.describe()
    assert 'dome_tel_az' in on.dome.describe()


# ---------------------------------------------------------------------------
# 7) 시험 자체의 위생 -- 실서버가 새어 들어오지 못하게
# ---------------------------------------------------------------------------

def test_the_default_config_never_touches_the_network():
    """⛔⛔ 기본값이 `off` 여야 한다.

    벤치·관측소 기계에는 **진짜 redis 가 돌고 있다.**  기본이 `redis` 면
    스위트가 그 서버의 실값을 읽어, 견본 바이트 대사처럼 `NC` 를 기대하는
    시험이 **실기에서만** 깨진다 (DevNote 11.20 의 "시뮬은 통과하는데
    실기에서 깨지는" 부류를 뒤집은 것).
    """
    cfg = SimConfig()
    assert cfg.dome.source == 'off'
    assert _relay(cfg).dome.enabled is False


@pytest.mark.parametrize('bad', [b'@3\r\n', b'*2\r\n$1\r\na\r\n$1\r\nb\r\n'])
def test_a_malformed_reply_is_refused(bad):
    """모르는 형·개수가 안 맞는 배열은 접속을 버린다 -- 조용히 오독하지 않는다."""
    async def _go():
        async def serve(reader, writer):    # noqa: ANN001
            await reader.readline()         # `*4`
            for _ in range(8):              # `$len` + 값, 넷
                await reader.readline()
            writer.write(bad)
            await writer.drain()
            writer.close()
        server = await asyncio.start_server(serve, '127.0.0.1', 0)
        port = server.sockets[0].getsockname()[1]
        relay = _relay(_cfg(port))
        try:
            assert await relay.query_dome() is False
            return relay.fits_header_dict('2026-09-11T00:00:00.000')
        finally:
            await relay.dome.close()
            server.close()
            await server.wait_closed()
    h = asyncio.run(_go())
    assert h[TEL] == 'NC' and h[AZ] == 'NC' and h[ERR] == 'NC'

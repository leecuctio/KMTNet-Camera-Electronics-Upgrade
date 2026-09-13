#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUX control 연동 -- 가짜 AUX 서버를 띄워 **실제 TCP 로** 시험한다.

규격: `TCSAgent/__reference/KMTNet AUX control remote commands(v20140908).pdf`

    요청  <TelID> <SysID> <PacketID> <SUBSYSTEM> <COMMAND>[LF]
    응답  <TelID> <SysID> <PacketID> <RESPONSE>[LF]

여기서 지키려는 것:

1. 전문이 규격대로 조립되는가 (셔터 개폐 시 `FILTERS SET_SH OPEN|CLOSE`).
2. **AUX 가 무슨 응답을 하든, 또는 아무 응답도 안 하든 노출이 끝까지 간다.**
   AUX 는 부가 경로이므로 관측을 막으면 안 된다(사용자 결정 2026-08-05).
3. 규격 2-4 의 침묵 -- TelID/SysID 가 틀리면 서버가 응답하지 않는다.  이때
   무한 대기하지 않고 타임아웃으로 빠져나오는가.
4. DARK/BIAS 는 셔터를 열지 않으므로 AUX 로 아무것도 보내지 않는가.
"""

from __future__ import annotations

import asyncio

import pytest
from conftest import DARK_SCRIPT, OBJECT_SCRIPT, drive, make_config

from ics_sim.auxcontrol import AuxControlClient


class FakeAux:
    """규격대로 대꾸하는 최소 AUX 서버.

    `reply` 를 바꿔 OK/BAD/WAIT 를 시험하고, `silent=True` 로 규격 2-4 의
    무응답을 흉내낸다.
    """

    def __init__(self, reply: str = 'OK', *, silent: bool = False,
                 tel: str = 'KMTNET', sysid: str = 'AUX') -> None:
        self.reply = reply
        self.silent = silent
        self.tel = tel
        self.sysid = sysid
        self.seen: list[str] = []
        self._server: asyncio.AbstractServer | None = None
        self.port = 0

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._serve, '127.0.0.1', 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _serve(self, reader, writer) -> None:  # noqa: ANN001
        try:
            while True:
                raw = await reader.readline()
                if not raw:
                    return
                line = raw.decode('ascii', 'replace').strip()
                self.seen.append(line)
                if self.silent:
                    continue
                parts = line.split(' ', 3)
                if len(parts) < 4:
                    continue                      # 규격 2-4: 인자 부족 -> 침묵
                tel, sysid, pid, _rest = parts
                if tel != self.tel or sysid != self.sysid:
                    continue                      # 규격 2-4: ID 불일치 -> 침묵
                writer.write(f'{tel} {sysid} {pid} {self.reply}\n'
                             .encode('ascii'))
                await writer.drain()
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            try:
                writer.close()
            except Exception:  # noqa: BLE001
                pass


def _cfg(server: FakeAux, **over):
    cfg = make_config()
    a = cfg.auxcontrol
    a.enabled = True
    a.host = '127.0.0.1'
    a.port = server.port
    a.ack_timeout = 0.5
    a.reconnect_sec = 0.1
    for key, value in over.items():
        setattr(a, key, value)
    return cfg


def run_with_aux(script, server: FakeAux, cfg=None, settle: float = 0.6):
    """가짜 서버를 띄운 채 한 사이클 돌린다."""
    async def go():
        await server.start()
        try:
            conf = cfg or _cfg(server)
            conf.auxcontrol.port = server.port
            from conftest import _drive
            return await _drive(conf, script, settle)
        finally:
            await server.stop()
    return asyncio.run(go())


# -- 전문 조립 -----------------------------------------------------------

def test_wire_format_matches_the_spec():
    client = AuxControlClient(make_config().auxcontrol)
    line = client.format('FILTERS', 'SET_SH OPEN', '00')
    assert line == 'KMTNET AUX 00 FILTERS SET_SH OPEN'


@pytest.mark.parametrize('script', ['OBJECT', 'DARK'])
def test_the_exposure_cycle_sends_nothing_to_aux(script):
    """⛔ **노출 사이클은 AUX 로 아무것도 안 보낸다** (2026-09-12).

    종전에는 셔터 개폐마다 `FILTERS SET_SH OPEN`/`CLOSE` 가 나갔다.  그 경로는
    **OBSAgent/TCSAgent 를 통해 AUX 에 FSA 셔터 제어 명령을 전달**하려던 것인데,
    TCS 측 검토로 **FSA HW 에 그 명령 구현이 어렵다**고 판정돼 걷었다.
    ⭐ 셔터를 실제로 모는 것은 컨트롤러의 Trigger Out 이고 명령은 `SHOPEN`/
    `SHCLOSE` 다 -- AUX 는 `LIMIT_SHUT` 으로 **상태를 읽기만** 한다 (규격 4-2).

    ⚠️ DARK/BIAS 는 애초에 셔터를 안 열어 종전에도 조용했다 -- 이제 **OBJECT 도**
    같다는 것이 이 시험의 요점이다.
    """
    server = FakeAux('OK')
    run_with_aux(OBJECT_SCRIPT if script == 'OBJECT' else DARK_SCRIPT, server)
    assert server.seen == [], server.seen


def test_every_line_carries_telid_and_sysid():
    """전문 접두가 `<TelID> <SysID> ` 인가 (규격 2-4).

    ⚠️ 2026-09-12 까지 셔터 이벤트를 도구로 썼다.  그 경로가 걷히면서
    **접속 인사(`hello`)** 로 갈아탔다 -- 검사하는 성질은 그대로다.
    """
    server = FakeAux('OK')
    cfg = _cfg(server, hello_subsystem='ALL', hello_command='ECHO ics_sim')
    run_with_aux(OBJECT_SCRIPT, server, cfg=cfg)
    assert server.seen
    for line in server.seen:
        assert line.startswith('KMTNET AUX '), line


# -- 노출은 AUX 응답에 좌우되지 않는다 ------------------------------------

@pytest.mark.parametrize('reply', ['OK', 'BAD', 'WAIT', 'ERROR'])
def test_exposure_completes_whatever_aux_answers(reply):
    server = FakeAux(reply)
    run = run_with_aux(OBJECT_SCRIPT, server)
    assert run.count('Acquisition Complete.', node='OBS') == 4, reply
    assert run.count('Wrote LASTFILE=', node='OBS') == 4, reply


def test_exposure_completes_when_aux_is_silent():
    """규격 2-4 -- 서버가 침묵해도 타임아웃으로 빠져나와 노출을 마쳐야 한다."""
    server = FakeAux(silent=True)
    run = run_with_aux(OBJECT_SCRIPT, server)
    assert run.count('Wrote LASTFILE=', node='OBS') == 4


def test_exposure_completes_when_aux_is_absent():
    """서버가 아예 없을 때.  접속 실패가 노출을 막으면 안 된다."""
    cfg = make_config()
    a = cfg.auxcontrol
    a.enabled = True
    a.host, a.port = '127.0.0.1', 1        # 닫힌 포트
    a.connect_timeout = 0.2
    a.ack_timeout = 0.2
    a.reconnect_sec = 0.1
    run = drive(OBJECT_SCRIPT, cfg=cfg)
    assert run.count('Wrote LASTFILE=', node='OBS') == 4


def test_wrong_telescope_id_times_out_rather_than_hanging():
    """TelID 오타 -> 서버 침묵.  규격 2-4 의 가장 헷갈리는 실패 형태다.

    ⚠️ 2026-09-12 까지 셔터 이벤트를 도구로 썼다 -- **접속 인사**로 갈아탔다.
    """
    server = FakeAux('OK', tel='KMTNET')
    cfg = _cfg(server, telescope_id='KMTN',     # 틀린 ID
               hello_subsystem='ALL', hello_command='ECHO ics_sim')
    run = run_with_aux(OBJECT_SCRIPT, server, cfg=cfg)
    assert run.count('Wrote LASTFILE=', node='OBS') == 4
    assert server.seen, '서버는 줄을 받기는 해야 한다'
    assert all(s.startswith('KMTN AUX') for s in server.seen)


# -- 응답 분류 -----------------------------------------------------------

def test_reply_is_recorded_for_each_command():
    """보낸 줄과 받은 답이 **짝으로** `log` 에 남나.

    ⚠️ 2026-09-12 까지 이 시험은 `on_shutter_open()`/`on_shutter_close()` 를
    도구로 썼다.  그 경로(AUX 셔터 제어)가 걷히면서 `send()` 를 직접 부르게
    바꿨다 -- **검사하는 성질은 그대로다** (겉을 하나 덜 거칠 뿐이다).
    """
    server = FakeAux('OK')
    async def go():
        await server.start()
        try:
            client = AuxControlClient(_cfg(server).auxcontrol)
            await client.start()
            await asyncio.sleep(0.3)
            assert client.connected
            assert await client.send('FILTERS', 'STATUS') == 'OK'
            assert await client.send('ALL', 'ECHO hi') == 'OK'
            await client.stop()
            return client.log
        finally:
            await server.stop()
    log = asyncio.run(go())
    assert [r for _, r in log] == ['OK', 'OK']
    assert log[0][0].endswith('FILTERS STATUS')
    assert log[1][0].endswith('ALL ECHO hi')


@pytest.mark.parametrize('reply', ['BAD', 'WAIT'])
def test_non_ok_replies_are_returned_not_raised(reply):
    server = FakeAux(reply)
    async def go():
        await server.start()
        try:
            client = AuxControlClient(_cfg(server).auxcontrol)
            await client.start()
            await asyncio.sleep(0.3)
            out = await client.send('FILTERS', 'STATUS')
            await client.stop()
            return out
        finally:
            await server.stop()
    assert asyncio.run(go()) == reply


def test_disabled_client_never_connects():
    cfg = make_config().auxcontrol
    cfg.enabled = False
    async def go():
        client = AuxControlClient(cfg)
        await client.start()
        out = await client.send('FILTERS', 'STATUS')
        await client.stop()
        return client.connected, out
    connected, out = asyncio.run(go())
    assert connected is False
    assert out is None


# -- 설정 ----------------------------------------------------------------

def test_pctcs_style_values_are_accepted():
    """`AUX_Host 192.168.14.60 (KMTNC)` 처럼 괄호 설명이 붙어도 읽어야 한다."""
    import textwrap

    from ics_sim import config

    ini = textwrap.dedent("""
        [auxcontrol]
        enabled   = true
        AUX_Host  = 192.168.14.60 (KMTNC)
        AUX_Port  = 5752
        AUX_TelID = KMTNET
        AUX_SysID = AUX
    """)
    cfg = config.loads(ini) if hasattr(config, 'loads') else None
    if cfg is None:                       # loads() 가 없으면 파일로 우회
        import os
        import tempfile
        fd, path = tempfile.mkstemp(suffix='.ini')
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(ini)
        try:
            cfg = config.load(path)
        finally:
            os.unlink(path)
    a = cfg.auxcontrol
    assert a.host == '192.168.14.60'
    assert a.port == 5752
    assert a.telescope_id == 'KMTNET'
    assert a.system == 'AUX'

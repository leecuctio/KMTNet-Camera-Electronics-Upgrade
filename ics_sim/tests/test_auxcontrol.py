#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUX control 연동 -- 가짜 AUX 서버를 띄워 **실제 TCP 로** 시험한다.

규격: `TCSAgent/__reference/KMTNet AUX control remote commands(v20140908).pdf`

    요청  <TelID> <SysID> <PacketID> <SUBSYSTEM> <COMMAND>[LF]
    응답  <TelID> <SysID> <PacketID> <RESPONSE>[LF]

여기서 지키려는 것:

1. 전문이 규격대로 조립되는가 (접속 인사 `hello` 로 본다 -- 셔터 개폐 통지
   `FILTERS SET_SH OPEN|CLOSE` 는 2026-09-12 에 걷었다).
2. **AUX 가 무슨 응답을 하든, 또는 아무 응답도 안 하든 노출이 끝까지 간다.**
   AUX 는 부가 경로이므로 관측을 막으면 안 된다(사용자 결정 2026-08-05).
3. 규격 2-4 의 침묵 -- TelID/SysID 가 틀리면 서버가 응답하지 않는다.  이때
   무한 대기하지 않고 타임아웃으로 빠져나오는가.
4. 노출 사이클(OBJECT 포함)은 AUX 로 아무것도 보내지 않는가.
5. 응답 등급이 **로그로만** 나가는가 -- `print()` 없이, 이유는 detail 로.
"""

from __future__ import annotations

import asyncio
import logging

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
    """규격 1-4 의 보기(`ALL ECHO`)로 조립을 본다.

    ⚠️ 2026-09-23 까지 보기가 `FILTERS SET_SH OPEN` 이었다 -- 2026-09-12 에 걷은
    셔터 개폐 통지다.  지금 실제로 나가는 것은 접속 인사(`hello_cmd`)뿐이라 그
    꼴로 바꿨다 (검사하는 성질은 그대로다).
    """
    client = AuxControlClient(make_config().auxcontrol)
    line = client.format('ALL', 'ECHO check_message', '123')
    assert line == 'KMTNET AUX 123 ALL ECHO check_message'


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


class _HangUpAux(FakeAux):
    """한 줄 받아 답하고 **바로 끊는** 서버 -- 클라이언트의 재접속을 일으킨다."""

    async def _serve(self, reader, writer) -> None:  # noqa: ANN001
        try:
            raw = await reader.readline()
            if raw:
                line = raw.decode('ascii', 'replace').strip()
                self.seen.append(line)
                tel, sysid, pid, _rest = line.split(' ', 3)
                writer.write(f'{tel} {sysid} {pid} {self.reply}\n'
                             .encode('ascii'))
                await writer.drain()
        except (ConnectionError, asyncio.CancelledError, ValueError):
            pass
        finally:
            try:
                writer.close()
            except Exception:  # noqa: BLE001
                pass


def test_hello_goes_out_on_every_reconnect():
    """⭐ `hello_cmd` 는 **(재)접속할 때마다** 붙은 직후 한 줄 나간다.

    `AuxControlClient._connect_once` 가 접속마다 보내므로 서버가 끊어 다시
    붙어도 또 나간다 -- ics_sim DevNote 7장 `[auxcontrol]` 표의 `hello_cmd`
    줄이 이 성질을 적는다.
    """
    server = _HangUpAux('OK')

    async def go():
        await server.start()
        try:
            cfg = _cfg(server, hello_subsystem='ALL',
                       hello_command='ECHO ics_sim')
            client = AuxControlClient(cfg.auxcontrol)
            await client.start()
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 5.0
            while len(server.seen) < 2 and loop.time() < deadline:
                await asyncio.sleep(0.05)
            await client.stop()
        finally:
            await server.stop()

    asyncio.run(go())
    assert len(server.seen) >= 2, server.seen
    assert all(s.endswith(' ALL ECHO ics_sim') for s in server.seen), server.seen
    # 접속마다 새 packet ID 다 -- 같은 줄을 되보낸 것이 아니다.
    assert server.seen[0].split()[2] != server.seen[1].split()[2], server.seen


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


def _one_reply(server: FakeAux, **over):  # noqa: ANN202
    """가짜 서버에 `FILTERS STATUS` 한 줄을 보내고 돌려받은 값."""
    async def go():
        await server.start()
        try:
            client = AuxControlClient(_cfg(server, **over).auxcontrol)
            await client.start()
            await asyncio.sleep(0.3)
            out = await client.send('FILTERS', 'STATUS')
            await client.stop()
            return out
        finally:
            await server.stop()
    return asyncio.run(go())


def _aux_records(caplog):  # noqa: ANN001, ANN202
    return [r for r in caplog.records if r.name == 'ics_sim.aux'
            and 'FILTERS STATUS' in r.getMessage()]


@pytest.mark.parametrize('reply, silent', [('BAD', False), ('WAIT', False),
                                           (None, True)])
def test_non_ok_is_a_warning_log_with_a_detail_not_a_print(reply, silent,  # noqa: ANN001
                                                           caplog, capsys):
    """⛔ **`print()` 를 안 쓴다** -- 종전에는 로그와 별도로 색을 입혀 콘솔에 또
    찍었다(같은 내용 두 줄 · 입력 중인 프롬프트를 덮음).  이제 등급은 로그 수준이,
    이유(점검할 곳·거부 아님)는 `extra detail` 이 말한다."""
    server = FakeAux(reply or 'OK', silent=silent)
    with caplog.at_level(logging.INFO, logger='ics_sim.aux'):
        assert _one_reply(server) == reply
    hits = _aux_records(caplog)
    assert len(hits) == 1, [r.getMessage() for r in hits]
    assert hits[0].levelno == logging.WARNING
    assert getattr(hits[0], 'detail', ''), '이유는 extra detail 로'
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('reply', ['OK', 'ics_sim'])
@pytest.mark.parametrize('verbose', [False, True])
def test_ok_is_always_logged_and_verbose_only_picks_the_concise_screen(verbose,  # noqa: ANN001
                                                                        reply,
                                                                        caplog, capsys):
    """`OK` 는 **늘 INFO 로 남는다**(로그 파일은 언제나 전부) -- `[auxcontrol]
    verbose` 는 간결 화면에 낼지만 정한다 (`essential`, `EssentialOnly` 가 본다).

    ⭐ 값 응답도 같다 -- `ECHO` 는 `OK` 가 아니라 **보낸 문자열을 되울린다**(규격
    1-4, `ALL ECHO ics_sim` -> `ics_sim`).  ⛔ 2026-09-23 까지 그 갈래에는
    `essential` 표시가 없어 간결 화면에도 늘 나갔다.
    """
    server = FakeAux(reply)
    with caplog.at_level(logging.INFO, logger='ics_sim.aux'):
        assert _one_reply(server, verbose=verbose) == reply
    hits = _aux_records(caplog)
    assert len(hits) == 1 and hits[0].levelno == logging.INFO
    assert hits[0].essential is verbose
    assert capsys.readouterr().out == ''


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

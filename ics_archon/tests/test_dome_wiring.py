#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""돔 방위 redis 의 **배선** -- ICS·ICG 시퀀서와 배포 ini (2026-09-11).

⭐ `ics_sim/tests/test_dome_redis.py` 가 `domeaz` + `telemetry` 층을 덮는다.
여기서 보는 것은 **그 층이 실제 노출 경로에 붙어 있는가**다:

* 배포 `ics_archon.ini`/`icg_archon.ini` 가 운영자가 준 서버를 가리키는가
* science 노출 하나를 돌리면 그 값이 **저장된 FITS 헤더**에 실리는가
* guide 는 **프레임마다** 읽는가 (`GO` 마다 한 번이 아니다)

⛔ **표식 `dome_redis`** -- `conftest.no_real_redis` 가드를 빠져나가므로 이
모듈은 **가짜 서버를 직접 세운다.**  실서버 포트(6379)를 쓰면 기계마다 결과가
달라진다.
"""

from __future__ import annotations

import asyncio
import configparser
import os

import pytest

from ics_archon import _simpath

_simpath.ensure()

from ics_sim.config import SimConfig           # noqa: E402
from ics_sim.telemetry import TelemetryRelay    # noqa: E402

from test_ini_cards import (ACF_TEXT, INI_OVERRIDES, NX, NY,  # noqa: E402
                            _drive, headers, write_ini)
from fake_archon import FakeArchon              # noqa: E402

pytestmark = pytest.mark.dome_redis

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# 가짜 redis -- `ics_sim/tests/test_dome_redis.py` 의 것과 같은 최소 RESP
# ---------------------------------------------------------------------------

class FakeRedis:
    """`MGET` 만 답한다.  없는 키는 널 벌크(`$-1`) = TTL 만료."""

    def __init__(self, store: dict[str, str]) -> None:
        self.store = dict(store)
        self.server = None
        self.port = 0
        #: `MGET` 을 받은 횟수 -- 프레임마다 읽는지 보는 자다.
        self.mgets = 0
        #: ⚠️ **핸들러가 쥔 writer 를 들고 있어야 한다** -- 아래 `stop()` 참조.
        self._writers: list = []

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._serve, '127.0.0.1', 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        """⚠️ **서버 쪽 writer 를 먼저 닫는다.**

        ⛔ 안 닫으면 `Server.wait_closed()` 가 **영영 안 돌아온다** (py3.12 는
        핸들러의 transport 가 다 닫히기를 기다린다).  클라이언트가 이미 접속을
        닫았어도 마찬가지다 -- 핸들러 코루틴이 끝나는 것과 그 transport 가
        닫히는 것은 별개다.  ⚠️ 이걸 빠뜨려 이 파일의 end-to-end 시험이 통째로
        멈춰 있었다 (2026-09-11).
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

    async def _serve(self, reader, writer) -> None:  # noqa: ANN001
        self._writers.append(writer)
        try:
            while True:
                head = await reader.readline()
                if not head or not head.startswith(b'*'):
                    return
                args = []
                for _ in range(int(head[1:].strip())):
                    size = int((await reader.readline())[1:].strip())
                    args.append((await reader.readexactly(size + 2))[:size]
                                .decode())
                if args[0].upper() != 'MGET':
                    writer.write(b'+OK\r\n')
                else:
                    self.mgets += 1
                    out = [b'*%d\r\n' % (len(args) - 1)]
                    for key in args[1:]:
                        if key in self.store:
                            raw = self.store[key].encode()
                            out.append(b'$%d\r\n' % len(raw) + raw + b'\r\n')
                        else:
                            out.append(b'$-1\r\n')
                    writer.write(b''.join(out))
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            return
        finally:
            try:
                writer.close()
            except Exception:       # noqa: BLE001
                pass


DOME = {'dome_tel_az': '12.1', 'dome_az': '12.3', 'dome_del_az': '+0.2'}


# ---------------------------------------------------------------------------
# 1) 배포 ini -- 실기가 읽는 것이 이것이다
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('name', ['ics_archon.ini', 'icg_archon.ini'])
def test_the_shipped_inis_point_at_the_operator_given_server(name):
    """⭐ 운영자가 준 서버는 `127.0.0.1:6379` 다 (2026-09-11).

    ⛔ **코드 기본값은 `off`** 이므로(시험이 망을 안 건드리게) ini 가 켜지 않으면
    세 카드는 영구히 `NC` 다 -- 그래서 배포 ini 를 못박는다.
    `repo_only` 를 붙이지 않는다 -- ini 는 배치본에도 함께 간다.
    """
    ini = os.path.join(ROOT, name)
    assert os.path.exists(ini), f'ini 가 없다 ({ini})'
    cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    cp.read(ini, encoding='utf-8')
    assert cp.has_section('dome'), f'{name} 에 [dome] 절이 없다'
    s = cp['dome']
    assert s.get('source').strip() == 'redis', (
        f'{name} 의 [dome] source 가 redis 가 아니다 -- 실기에서 꺼진다')
    assert s.get('host').strip() == '127.0.0.1'
    assert s.getint('port') == 6379
    # 키 이름은 돔 제어 프로그램이 정한 것이다.
    assert s.get('key_tel_az').strip() == 'dome_tel_az'
    assert s.get('key_az').strip() == 'dome_az'
    assert s.get('key_del_az').strip() == 'dome_del_az'


def test_the_two_inis_agree_with_each_other():
    """⭐ 같은 돔을 보므로 두 ini 가 같은 값이어야 한다.

    한쪽만 고치면 science 헤더와 guide 헤더의 돔 방위가 **다른 서버 것**이 된다.
    """
    got = []
    for name in ('ics_archon.ini', 'icg_archon.ini'):
        cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        cp.read(os.path.join(ROOT, name), encoding='utf-8')
        got.append({k: cp['dome'].get(k, '').strip()
                    for k in ('source', 'host', 'port', 'db',
                              'key_tel_az', 'key_az', 'key_del_az')})
    assert got[0] == got[1], f'ics {got[0]} vs icg {got[1]}'


@pytest.mark.parametrize('name', ['ics_archon.ini', 'icg_archon.ini'])
def test_the_shipped_inis_parse_through_the_real_loader(name):
    """⚠️ **`configparser` 가 아니라 `config.load()` 로 본다.**

    위 시험은 ini 를 직접 읽는데, 실기가 지나는 길은 `simcfg.load()` 다.
    ⛔ 인라인 주석(`timeout = 0.3   # 왕복 상한 [s]`)을 안 떼면
    `getfloat` 가 **터지고 기동이 멈춘다** -- 그 경로를 여기서 지난다.
    """
    from ics_sim import config as simcfg

    cfg = simcfg.load(os.path.join(ROOT, name))
    d = cfg.dome
    assert d.source == 'redis'
    assert (d.host, d.port) == ('127.0.0.1', 6379)
    assert d.timeout == 0.3 and d.db == 0
    assert (d.key_tel_az, d.key_az, d.key_del_az) == (
        'dome_tel_az', 'dome_az', 'dome_del_az')
    # ⭐ 배포 ini 는 경고를 내지 않아야 한다.
    assert not [w for w in cfg.validate() if '[dome]' in w]


def test_the_code_default_is_off_so_the_suite_stays_hermetic():
    """⛔⛔ 기본값이 `redis` 면 스위트가 기계마다 다른 답을 낸다 (conftest 참조)."""
    assert SimConfig().dome.source == 'off'


# ---------------------------------------------------------------------------
# 2) science -- 노출 하나가 헤더에 값을 싣는가 (end-to-end)
# ---------------------------------------------------------------------------

def _run_science(tmp_path, store):
    """FakeArchon + 가짜 redis 로 dark 한 장을 찍고 헤더를 돌려준다."""
    acf = tmp_path / 'test.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')
    mk, nt = FakeArchon(width=NX, height=NY), FakeArchon(width=NX, height=NY)
    mk.start()
    nt.start()
    redis = FakeRedis(store)

    async def _go():
        await redis.start()
        ini = write_ini(tmp_path, INI_OVERRIDES, str(acf), str(acf))
        cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        cp.read(ini, encoding='utf-8')
        cp['archon']['port'] = str(mk.port)
        # ⭐ **가짜 서버로 돌린다** -- 배포 ini 의 6379 를 그대로 쓰면 실기
        # 기계에서 진짜 값을 읽어 시험이 기계마다 달라진다.
        cp['dome']['port'] = str(redis.port)
        with open(ini, 'w', encoding='utf-8') as fh:
            cp.write(fh)
        try:
            await _drive(ini, tmp_path, nt.port,
                         ['OBS>ICS projid ENG', 'OBS>ICS dark begin',
                          'OBS>ICS exp 1', 'OBS>ICS go'])
        finally:
            await redis.stop()

    try:
        asyncio.run(_go())
    finally:
        mk.shutdown()
        nt.shutdown()
    return headers(tmp_path), redis


def test_a_science_exposure_writes_the_redis_dome_values(tmp_path):
    """⭐⭐ 이 시험이 배선의 정본이다 -- 노출 -> 저장된 FITS 헤더까지."""
    heads, redis = _run_science(tmp_path, DOME)
    assert set(heads) == {'MK', 'NT'}, list(heads)
    for tag, head in sorted(heads.items()):
        assert head['DSTELAZ'].strip() == '12.1', tag
        assert head['DSAZ'].strip() == '12.3', tag
        assert head['DAZERR'].strip() == '+0.2', tag
    assert redis.mgets >= 1, '노출이 redis 를 읽지 않았다'


def test_a_science_exposure_writes_nc_when_the_keys_expired(tmp_path):
    """⛔ 키가 없으면 `NC` 다 -- 그리고 **고도** 카드는 영향받지 않는다."""
    heads, _ = _run_science(tmp_path, {})
    for tag, head in sorted(heads.items()):
        assert head['DSTELAZ'].strip() == 'NC', tag
        assert head['DSAZ'].strip() == 'NC', tag
        assert head['DAZERR'].strip() == 'NC', tag
        # `DALTERR` 는 고도 계산이고 TC 가 안 붙은 하네스라 `NC` 지만,
        # **방위 때문에** NC 가 된 것이 아님을 카드가 살아 있는 것으로 본다.
        assert 'DALTERR' in head, tag


def test_the_dome_read_does_not_break_an_exposure_when_the_server_is_down(
        tmp_path):
    """⛔ 서버가 없어도 노출은 끝나고 파일이 나온다."""
    acf = tmp_path / 'test.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')
    mk, nt = FakeArchon(width=NX, height=NY), FakeArchon(width=NX, height=NY)
    mk.start()
    nt.start()

    async def _go():
        # 띄웠다 닫아 **확실히 빈** 포트를 얻는다.
        dead = FakeRedis({})
        await dead.start()
        port = dead.port
        await dead.stop()
        ini = write_ini(tmp_path, INI_OVERRIDES, str(acf), str(acf))
        cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        cp.read(ini, encoding='utf-8')
        cp['archon']['port'] = str(mk.port)
        cp['dome']['port'] = str(port)
        with open(ini, 'w', encoding='utf-8') as fh:
            cp.write(fh)
        await _drive(ini, tmp_path, nt.port,
                     ['OBS>ICS projid ENG', 'OBS>ICS dark begin',
                      'OBS>ICS exp 1', 'OBS>ICS go'])

    try:
        asyncio.run(_go())
    finally:
        mk.shutdown()
        nt.shutdown()
    heads = headers(tmp_path)
    assert set(heads) == {'MK', 'NT'}, '노출이 파일을 못 남겼다'
    assert heads['MK']['DSAZ'].strip() == 'NC'


# ---------------------------------------------------------------------------
# 3) guide -- 프레임마다 읽는가
# ---------------------------------------------------------------------------

class _CountingRelay:
    """`query_dome()` 횟수만 세는 대역.  시퀀서 배선만 본다."""

    class _Dome:
        enabled = True

    def __init__(self) -> None:
        self.dome = self._Dome()
        self.reads = 0

    async def query_dome(self) -> bool:
        self.reads += 1
        return True


def test_the_guide_sequencer_reads_the_dome_once_per_frame():
    """⭐⭐ `GO n` 이면 **n 번** 읽는다 -- 스냅샷 하나를 n 장에 쓰지 않는다.

    ⛔ guide 주기는 1.3초이고 키 TTL 은 수백 ms 다.  `GO` 앞의 `TCSSTATUS`
    스냅샷에 얹으면 2번째 장부터 **TTL 이 지난 값을 새 값처럼** 싣는다.
    그래서 `_spawn_dome_read()` 가 프레임 루프 **안**에 있어야 한다.
    """
    import inspect

    from icg_archon import sequencer as icg_seq

    body = inspect.getsource(icg_seq.GuideSequencer._run)
    assert '_spawn_dome_read()' in body, (
        'guide 프레임 루프에 돔 읽기가 없다')
    assert '_collect_dome_read()' in body, (
        '읽은 값을 `_dispatch_store` 앞에서 받지 않는다')
    # 루프(`for k in range(count)`)보다 **뒤에** 있어야 프레임마다 돈다.
    loop_at = body.index('for k in range(count)')
    assert body.index('_spawn_dome_read()') > loop_at, (
        '돔 읽기가 프레임 루프 밖에 있다 -- GO 마다 한 번이 된다')
    assert body.index('_collect_dome_read()') > loop_at


def test_a_guide_go_n_writes_the_redis_values_on_every_frame(tmp_path):
    """⭐⭐ guide 배선의 정본 -- `go 3` 이 **세 장 모두**에 실값을 싣는다.

    ⛔ 원천 검사(위)만으로는 `_collect_dome_read()` 가 실제로 값을 넘기는지 알
    수 없다.  guide 는 `_dispatch_store()` 가 헤더를 **그 자리에서** 조립하므로
    (동기) 받는 순서가 틀리면 카드가 `NC` 로 나간다.
    """
    import glob

    from icg_archon.app import IcgArchon
    from test_icg_app import _cards, make_cfgs

    redis = FakeRedis(DOME)

    async def _go():
        await redis.start()
        cfg, icfg = make_cfgs(tmp_path)
        # ⭐ **가짜 서버로 돌린다** -- 배포 ini 의 6379 를 그대로 쓰면 실기
        # 기계에서 진짜 값을 읽어 시험이 기계마다 달라진다.
        cfg.dome.source = 'redis'
        cfg.dome.port = redis.port
        cfg.dome.timeout = 2.0
        app = IcgArchon(cfg, icfg, backend='sim')
        await app.start()
        try:
            for line in ('abc>ICG GUIEXP 2', 'abc>ICG go 3'):
                app.transport.feed(line)
                await asyncio.sleep(0.02)
            await app.seq.wait()
            await asyncio.sleep(0.05)
        finally:
            await app.stop()
            await redis.stop()

    asyncio.run(_go())
    paths = sorted(glob.glob(str(tmp_path / 'data' / '**' / '*.fits'),
                             recursive=True))
    assert paths, 'guide 가 파일을 안 남겼다'
    for path in paths:
        cards = _cards(path)
        assert '12.1' in cards['DSTELAZ'], (path, cards['DSTELAZ'])
        assert '12.3' in cards['DSAZ'], (path, cards['DSAZ'])
        assert '+0.2' in cards['DAZERR'], (path, cards['DAZERR'])
    # ⭐ **프레임마다** 읽었다 -- `GO` 당 한 번이면 1 이다.
    assert redis.mgets >= len(paths), (
        f'{len(paths)} 장인데 MGET 이 {redis.mgets} 번뿐이다 -- '
        'GO 당 한 번만 읽고 있다')


def test_the_guide_helpers_skip_the_task_when_the_source_is_off():
    """`off` 면 태스크를 만들지 않는다 -- 아무 일도 안 할 코루틴을 안 띄운다."""
    from icg_archon.sequencer import GuideSequencer

    class _Off:
        class dome:
            enabled = False

    seq = GuideSequencer.__new__(GuideSequencer)
    seq.telem = _Off()
    seq._dome_read = None
    assert seq._spawn_dome_read() is None
    asyncio.run(seq._collect_dome_read())       # 아무 일도 없어야 한다


def test_the_science_helper_skips_the_task_when_the_source_is_off():
    """science 쪽도 같다 (`ics_sim.sequencer.Sequencer._spawn_dome_read`)."""
    from ics_sim.sequencer import Sequencer

    seq = Sequencer.__new__(Sequencer)
    seq.telem = TelemetryRelay(SimConfig(), lambda *a, **k: None)
    seq._dome_read = None
    assert seq._spawn_dome_read() is None

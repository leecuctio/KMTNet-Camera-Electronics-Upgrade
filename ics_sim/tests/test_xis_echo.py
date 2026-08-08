#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""실물 XIS 연동 대비 -- 자기 발신 에코와 브로드캐스트 중복 (DevNote 3.1.2).

`transport.feed()` 기반 테스트는 XIS 라우팅을 건너뛰므로, 여기서는 XIS 가
실제로 하는 일을 feed() 로 흉내 낸다:

* **유니캐스트 루프백** -- 우리가 K.IC 등 자기 노드 앞으로 보낸 명령을 XIS 가
  클라이언트 테이블(K.IC 주소 = 우리 자신)대로 되돌려준다.  걸러내지 않으면
  ERASE/SHOPEN 이 이중 실행된다.
* **브로드캐스트 슬롯별 복사** -- v2.9.1 은 `AL` 메시지를 송신 슬롯 하나만 빼고
  등록 슬롯 전부에 복사한다 (`messages.c`, `if (i != sendHost)`).  9개 ID 로
  등록한 우리에게는 같은 데이터그램이 최대 9부 도착한다.

노드 ID 검증도 여기서 다룬다 -- v2.9.1 허브에는 ServerID 사칭 방어도 주소
충돌 검사도 없어서(xis/xis.md 6.3) 잘못된 이름을 거를 책임이 우리에게 있다.
"""

from __future__ import annotations

import asyncio

import pytest

from conftest import DARK_SCRIPT, drive, make_config
from ics_sim import config
from ics_sim.app import IcsSim


# -- 유니캐스트 루프백: 자기 발신 에코는 버린다 ---------------------------

def test_external_erase_is_served():
    """대조군: 외부(OBS) 발신 ERASE 는 정상 처리된다."""
    run = drive(['OBS>K.IC ERASE'])
    assert run.find('Erase Cycle Complete.'), run.sent


def test_self_sourced_erase_is_dropped():
    """XIS 가 되돌려준 자기 발신 ERASE 는 실행하지 않는다."""
    run = drive(['ICS>K.IC ERASE'])
    assert not run.find('Erase Cycle Complete.'), run.sent
    assert not run.find('ERROR'), run.sent


def test_self_sourced_shopen_is_dropped():
    """에코된 SHOPEN 이 셔터를 재구동하거나 중복 보고를 내면 안 된다."""
    run = drive(['K.IC>K.IC SHOPEN 60 OBS USESTATUS'])
    assert not run.find('Shutter=Open'), run.sent


def test_unknown_external_sources_still_served():
    """필터는 우리 9개 ID 만 거른다 -- ICG/CHA 같은 외부 노드는 그대로 처리."""
    run = drive(['ICG>ICS STATUS', 'CHA>ICS STATUS'])
    replies = [m for m in run.find(' STATUS') if 'DONE:' in m]
    assert len(replies) == 2, run.sent


async def _echo_replay() -> tuple[int, int, list]:
    """DARK 한 사이클을 돌리고, 발신 전량을 XIS 에코처럼 되먹인다."""
    app = IcsSim(make_config())
    await app.start()
    for line in DARK_SCRIPT:
        app.transport.feed(line)
        await asyncio.sleep(0.02)
    await app.seq.wait()
    await asyncio.sleep(0.6)

    before = len(app.transport.sent_log)
    for line in list(app.transport.sent_log):
        app.transport.feed(line)
    await asyncio.sleep(0.3)
    after = len(app.transport.sent_log)
    violations = list(app.emit.violations)
    await app.stop()
    return before, after, violations


def test_echo_burst_of_full_cycle_is_inert():
    """전체 노출 사이클의 에코 폭주에도 발신이 하나도 늘지 않아야 한다.

    발신 전량의 src 는 우리 9개 ID 중 하나이므로, 무엇이 되돌아오든
    (ERASE 재실행, GO busy ERROR, PONG 증식 없이) 전부 무시가 정답이다.
    """
    before, after, violations = asyncio.run(_echo_replay())
    assert after == before, f'에코가 새 발신 {after - before}건을 유발했다'
    assert not violations, violations


# -- 브로드캐스트 슬롯별 복사: 첫 부만 처리한다 ---------------------------

def test_broadcast_ping_copies_answered_once():
    """같은 XIS>AL PING 이 여러 부 와도 PONG 은 9발 한 세트뿐이어야 한다."""
    run = drive(['XIS>AL PING'] * 3)
    pongs = [m for m in run.sent if ' PONG' in m]
    assert len(pongs) == 9, f'PONG {len(pongs)}발 (81발 폭주가 재현되면 실패)'


def test_distinct_broadcasts_each_answered():
    """원문이 다른 브로드캐스트는 각각 처리한다 -- 중복 억제는 사본만 거른다."""
    run = drive(['XIS>AL PING', 'TC>AL PING'])
    pongs = [m for m in run.sent if ' PONG' in m]
    assert len(pongs) == 18, run.sent


def test_directed_ping_single_pong():
    """직접 지목된 PING 은 그 노드로만 1발 (기존 동작 불변)."""
    run = drive(['OBS>K.IC PING'])
    pongs = [m for m in run.sent if ' PONG' in m]
    assert len(pongs) == 1, run.sent
    assert pongs[0].startswith('K.IC>OBS'), pongs


def test_dedup_can_be_disabled():
    """broadcast_dedup_sec <= 0 이면 예전처럼 부마다 응답한다 (진단용)."""
    run = drive(['XIS>AL PING'] * 2,
                cfg=make_config(transport__broadcast_dedup_sec=0.0))
    pongs = [m for m in run.sent if ' PONG' in m]
    assert len(pongs) == 18, run.sent


# -- 노드 ID 검증: 허브가 안 거르므로 우리가 거른다 -----------------------

def test_reserved_node_id_rejected():
    cfg = make_config()
    cfg.node.ics_id = 'XIS'
    with pytest.raises(config.ConfigError):
        cfg.validate()


def test_broadcast_name_rejected():
    cfg = make_config()
    cfg.node.ic_ids = ('AL', 'M.IC', 'T.IC', 'N.IC')
    with pytest.raises(config.ConfigError):
        cfg.validate()


def test_malformed_node_id_rejected():
    cfg = make_config()
    cfg.node.ics_id = 'I'  # 1자 -- IMPv2 는 2~8자
    with pytest.raises(config.ConfigError):
        cfg.validate()


def test_duplicate_node_id_rejected():
    cfg = make_config()
    cfg.node.cb_ids = ('K.CB', 'K.CB', 'T.CB', 'N.CB')
    with pytest.raises(config.ConfigError):
        cfg.validate()


def test_guide_id_collision_rejected():
    cfg = make_config()
    cfg.node.guide_ic_id = 'K.IC'
    with pytest.raises(config.ConfigError):
        cfg.validate()


def test_default_config_still_valid():
    """기본 설정은 새 검증을 전부 통과해야 한다."""
    cfg = make_config()
    cfg.validate()  # ConfigError 가 나면 실패

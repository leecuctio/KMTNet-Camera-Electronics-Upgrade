#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared test fixtures: a headless simulator runner."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ics_sim import config  # noqa: E402
from ics_sim.app import IcsSim  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')
INI = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ics_sim.ini'))


@dataclass
class Run:
    """헤드리스 실행 결과."""

    sent: list[str] = field(default_factory=list)
    #: (경과초, 메시지) -- 타임아웃 창 검사에 쓴다.  time_scale 을 되돌린 값이다.
    timed: list[tuple[float, str]] = field(default_factory=list)
    violations: list[tuple[str, list[str]]] = field(default_factory=list)

    def to(self, node: str) -> list[str]:
        node = node.upper()
        return [m for m in self.sent
                if m.split('>', 1)[1].split(' ', 1)[0].upper() == node]

    def count(self, needle: str, node: str | None = None) -> int:
        pool = self.to(node) if node else self.sent
        return sum(1 for m in pool if needle in m)

    def find(self, needle: str) -> list[str]:
        return [m for m in self.sent if needle in m]


def make_config(**over) -> config.SimConfig:
    """테스트용 설정.  기본은 ini 를 읽되 축척을 크게 줄인다."""
    cfg = config.load(INI if os.path.exists(INI) else None)
    cfg.timing.time_scale = 0.02
    cfg.transport.bind_port = 0
    cfg.transport.bind_host = '127.0.0.1'
    cfg.transport.send_gap_ms = 0.0
    cfg.behavior.console = False
    cfg.logging.wire = False
    cfg.paths.write_fits = False
    cfg.paths.data_dir = '/mnt/ICSData'
    for key, value in over.items():
        section, _, name = key.partition('__')
        setattr(getattr(cfg, section), name, value)
    return cfg


async def _drive(cfg: config.SimConfig, script: list[str],
                 settle: float = 0.6) -> Run:
    app = IcsSim(cfg)
    await app.start()
    started = time.monotonic()
    scale = cfg.timing.time_scale or 1.0
    timed: list[tuple[float, str]] = []
    seen = 0

    def snapshot() -> None:
        nonlocal seen
        now = (time.monotonic() - started) / scale
        while seen < len(app.transport.sent_log):
            timed.append((now, app.transport.sent_log[seen]))
            seen += 1

    for line in script:
        app.transport.feed(line)
        await asyncio.sleep(0.02)
        snapshot()
    await app.seq.wait()
    snapshot()
    await asyncio.sleep(settle)
    snapshot()
    await app.stop()
    return Run(sent=list(app.transport.sent_log), timed=timed,
               violations=list(app.emit.violations))


def drive(script: list[str], cfg: config.SimConfig | None = None,
          settle: float = 0.6) -> Run:
    """명령 스크립트를 먹여 한 사이클을 돌리고 발신 기록을 돌려준다."""
    return asyncio.run(_drive(cfg or make_config(), script, settle))


DARK_SCRIPT = ['OBS>ICS projid obs', 'OBS>ICS dark begin',
               'OBS>ICS exp 30', 'OBS>ICS go']
OBJECT_SCRIPT = ['OBS>ICS ProjID BLG', 'OBS>ICS OBJECT BLG11',
                 'OBS>ICS exp 60.0', 'OBS>ICS Go']
GON5_SCRIPT = ['OBS>ICS projid eng', 'OBS>ICS bias bias', 'OBS>ICS go 5']


@pytest.fixture(scope='module')
def dark_run() -> Run:
    return drive(DARK_SCRIPT)


@pytest.fixture(scope='module')
def object_run() -> Run:
    return drive(OBJECT_SCRIPT)


@pytest.fixture(scope='module')
def gon5_run() -> Run:
    return drive(GON5_SCRIPT, settle=1.0)

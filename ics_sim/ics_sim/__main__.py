#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point:  python -m ics_sim [options]

설정은 ics_sim.ini 에서 읽고, 아래 인자로 개별 항목을 덮어쓴다.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from . import __version__, config
from .app import IcsSim
from .console import Console


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='ics_sim',
        description='KMTNet ICS simulator (IMPv2.5 / UDP)')
    p.add_argument('-c', '--config', default=config.DEFAULT_INI,
                   help='설정 파일 경로 (기본: ics_sim.ini)')
    p.add_argument('--time-scale', type=float,
                   help='전체 시간 축척. 0.1 이면 10배 빠르게')
    p.add_argument('--bind-port', type=int, help='수신 UDP 포트')
    p.add_argument('--xis-host', help='XIS 허브 주소 (비우면 direct-reply)')
    p.add_argument('--xis-port', type=int, help='XIS 허브 포트')
    p.add_argument('--data-dir', help='FITS 저장 경로')
    p.add_argument('--fits', dest='write_fits', action='store_true',
                   help='더미 FITS 를 실제로 생성')
    p.add_argument('--no-fits', dest='write_fits', action='store_false',
                   help='FITS 생성 안 함 (메시지만)')
    p.add_argument('--backend', choices=('sim', 'archon'),
                   help='디텍터 백엔드')
    p.add_argument('--node-mode', choices=('legacy', 'merged'),
                   help='발신 노드 이름 방식')
    p.add_argument('--bug-compat', action='store_true',
                   help='레거시 커맨드워드 오염을 의도적으로 재현')
    p.add_argument('--inject', help='결함 주입 (쉼표 구분)')
    p.add_argument('--no-console', dest='console', action='store_false',
                   help='키보드 인터페이스 없이 실행')
    p.add_argument('--quiet-wire', dest='wire', action='store_false',
                   help='송수신 메시지를 출력하지 않음')
    p.add_argument('--log-level', choices=('debug', 'info', 'warning', 'error'))
    p.add_argument('-V', '--version', action='version',
                   version=f'ics_sim {__version__}')
    p.set_defaults(write_fits=None, console=None, wire=None)
    return p


def apply_args(cfg: config.SimConfig, args: argparse.Namespace) -> None:
    if args.time_scale is not None:
        cfg.timing.time_scale = args.time_scale
    if args.bind_port is not None:
        cfg.transport.bind_port = args.bind_port
    if args.xis_host is not None:
        cfg.transport.xis_host = args.xis_host
    if args.xis_port is not None:
        cfg.transport.xis_port = args.xis_port
    if args.data_dir is not None:
        cfg.paths.data_dir = args.data_dir
    if args.write_fits is not None:
        cfg.paths.write_fits = args.write_fits
    if args.backend is not None:
        cfg.hardware.backend = args.backend
    if args.node_mode is not None:
        cfg.node.emit_node_mode = args.node_mode
    if args.bug_compat:
        cfg.behavior.bug_compat = True
    if args.inject is not None:
        cfg.behavior.inject = frozenset(
            x.strip() for x in args.inject.split(',') if x.strip())
    if args.console is not None:
        cfg.behavior.console = args.console
    if args.wire is not None:
        cfg.logging.wire = args.wire
    if args.log_level is not None:
        cfg.logging.level = args.log_level


def setup_logging(cfg: config.SimConfig) -> None:
    level = getattr(logging, cfg.logging.level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if cfg.logging.file:
        handlers.append(logging.FileHandler(cfg.logging.file, encoding='utf-8'))
    logging.basicConfig(
        level=level,
        format='%(asctime)s.%(msecs)03d %(name)-18s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S',
        handlers=handlers,
    )


async def amain(cfg: config.SimConfig) -> int:
    app = IcsSim(cfg)
    await app.start()

    console = Console(app) if cfg.behavior.console else None
    try:
        if console is not None:
            await console.run()
        else:
            await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await app.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = config.load(args.config)
    apply_args(cfg, args)
    setup_logging(cfg)
    try:
        return asyncio.run(amain(cfg))
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())

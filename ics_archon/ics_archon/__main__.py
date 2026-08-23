#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""진입점:  `python -m ics_archon [옵션]`

`ics_sim` 의 인자 처리·로깅 설정을 **그대로 재사용**하고 셋만 다르다:

* 기본 설정 파일이 `ics_archon.ini` 다.
* 기본 백엔드가 `archon` 이다 (ini 에 `[hardware] backend` 가 없어도).
* `[archon]` 절을 함께 읽어 `IcsArchon` 에 넘긴다.

시뮬로 돌려 보고 싶으면 `--backend sim` 을 주면 된다 -- 메시지 층은 완전히
같으므로 그것이 곧 회귀 시험이다.
"""

from __future__ import annotations

import asyncio
import sys

from . import __version__, _simpath, config as acfg_mod

_simpath.ensure()

from ics_sim import config as simcfg                      # noqa: E402
from ics_sim.__main__ import (apply_args, build_parser,   # noqa: E402
                              setup_logging)
from ics_sim.console import Console                       # noqa: E402

from .app import IcsArchon                                # noqa: E402

DEFAULT_INI = 'ics_archon.ini'


def make_parser():  # noqa: ANN201
    """`ics_sim` 의 파서를 빌려 기본값만 바꾼다.

    인자를 다시 정의하지 않는 것이 요점이다 -- 두 벌이 되면 한쪽에 옵션이
    늘 때 다른 쪽이 조용히 뒤처진다.
    """
    p = build_parser()
    p.prog = 'ics_archon'
    p.description = 'KMTNet ICS -- STA Archon 실기 취득 (IMPv2.5 / UDP)'
    p.set_defaults(config=DEFAULT_INI)
    for action in p._actions:                    # noqa: SLF001
        if action.dest == 'version':
            action.version = 'ics_archon %s' % __version__
        elif action.dest == 'config':
            action.help = '설정 파일 경로 (기본: %s)' % DEFAULT_INI
    return p


async def amain(cfg, acfg) -> int:  # noqa: ANN001
    app = IcsArchon(cfg, acfg)
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
        # **전원을 끄는 자리다.**  여기서 새 예외가 나면 원인이 가려지므로
        # `IcsArchon.stop()` 이 안에서 삼킨다.
        await app.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    cfg = simcfg.load(args.config)
    # **ini 가 백엔드를 안 적었으면 실기가 기본이다.**  `ics_sim` 의 기본은
    # `sim` 이라, 그 값을 그대로 물려받으면 `python -m ics_archon` 이 조용히
    # 시뮬로 돌아 "왜 컨트롤러를 안 만지나" 가 된다.  ini 가 **적어 놓은**
    # 값은 존중한다 -- `backend = sim` 은 뜻이 있는 설정이다(메시지 층만
    # 돌려 보는 회귀).
    if not acfg_mod.backend_declared(args.config) and args.backend is None:
        cfg.hardware.backend = 'archon'
    apply_args(cfg, args)
    setup_logging(cfg)
    acfg = acfg_mod.load(args.config)
    try:
        return asyncio.run(amain(cfg, acfg))
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main())

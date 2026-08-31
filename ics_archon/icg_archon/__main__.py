#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""icg_archon 진입점.

    python -m icg_archon                  # icg_archon.ini 를 읽는다
    python -m icg_archon --backend sim    # 컨트롤러 없이 메시지 층만

파서는 `ics_sim.__main__.build_parser()` 를 **빌린다** -- 인자를 다시
정의하지 않는다 (`ics_archon.__main__` 과 같은 이유: 그쪽에 새 옵션이
생기면 여기서도 그대로 통한다).
"""

from __future__ import annotations

import asyncio

from ics_archon import _simpath

_simpath.ensure()

from ics_sim import __main__ as sim_main  # noqa: E402
from ics_sim import config as simcfg  # noqa: E402

from . import __version__, build_id  # noqa: E402
from . import config as icfg_mod  # noqa: E402
from .app import IcgArchon  # noqa: E402

DEFAULT_INI = icfg_mod.DEFAULT_INI


def make_parser():  # noqa: ANN201
    p = sim_main.build_parser()
    p.prog = 'icg_archon'
    p.description = '실기 ICG -- STA Archon guide 유닛 제어 + HK 로깅'
    p.set_defaults(config=DEFAULT_INI)
    for act in p._actions:  # noqa: SLF001 -- 도움말 문구만 바꾼다
        if act.dest == 'config':
            act.help = '설정 파일 (기본 %s)' % DEFAULT_INI
        elif act.dest == 'version' and hasattr(act, 'version'):
            act.version = 'icg_archon %s (%s)' % (__version__, build_id())
    return p


async def amain(cfg, icfg, backend: str) -> None:  # noqa: ANN001
    app = IcgArchon(cfg, icfg, backend=backend)
    await app.start()
    try:
        if cfg.behavior.console:
            from ics_sim.console import Console
            await Console(app).run()
        else:
            await asyncio.Event().wait()
    finally:
        await app.stop()


def main(argv=None) -> int:  # noqa: ANN001
    args = make_parser().parse_args(argv)
    cfg = simcfg.load(args.config)
    # guide 의 기본 백엔드는 실기다 -- `--backend sim` 만 대역으로 돈다.
    backend = 'icg_archon'
    if getattr(args, 'backend', None):
        backend = 'icg_archon' if args.backend == 'archon' else args.backend
    sim_main.apply_args(cfg, args)
    sim_main.setup_logging(cfg)
    icfg = icfg_mod.load(args.config)
    asyncio.run(amain(cfg, icfg, backend))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

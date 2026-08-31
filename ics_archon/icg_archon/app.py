#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""icg 조립 -- `ics_sim.IcsSim` 을 상속하고 guide 몫을 갈아 끼운다.

`ics_archon.app.IcsArchon` 과 같은 상속 골격이되 갈아 끼우는 폭이 넓다:

* **시퀀서** -- science 노출 상태기 대신 `GuideSequencer` (frame-transfer).
* **디스패처** -- `IcgDispatcher` (+`GUIDEEXP`/`HK`/`RADIONODE`).
* **백엔드** -- `GuideBackend`(실기) / `SimGuideBackend`(메시지 층 회귀).
  `ics_sim` 의 `DetectorBackend` 계약을 쓰지 않으므로 `make_backend()` 경로
  밖이다 -- 부모가 만든 science 시퀀서·백엔드는 버려진다 (아래 주석).
* **HK 감시** (1분) + **Radionode 폴러** -- 기동에서 띄운다.

노드 정체는 ini 가 정한다 -- `[node] ics_id=ICG · ic_ids=G.IC · cb_ids=G.CB ·
master=G · guide_ic_id=` (빈 값!  기본 `G.IC` 를 지우지 않으면 라우터가
자기 IC 를 "범위 밖 guide" 로 무시한다 -- `nodes.Role.GUIDE`).
"""

from __future__ import annotations

import logging

from ics_archon import _simpath

_simpath.ensure()

from ics_sim.app import IcsSim  # noqa: E402

from . import build_id  # noqa: E402
from . import commands as icg_commands  # noqa: E402
from .backend import GuideBackend, SimGuideBackend  # noqa: E402
from .config import TAG, IcgCfg, validate  # noqa: E402
from .hk import HkMonitor  # noqa: E402
from .radionode import RadionodeClient  # noqa: E402
from .sequencer import GuideSequencer  # noqa: E402

log = logging.getLogger('icg_archon.app')


class IcgArchon(IcsSim):
    """실기 ICG 본체."""

    def __init__(self, cfg, icfg: IcgCfg, *,  # noqa: ANN001
                 backend: str = 'icg_archon') -> None:
        icg_commands.extend_vocabulary()
        # 부모가 science 백엔드·시퀀서를 만든다 -- guide 는 그 계약 밖이라
        # 아래에서 통째로 갈아 끼우고, 부모 몫은 쓰지 않는다.  `sim` 으로
        # 고정해 두는 이유: `archon` 스텁이 만들어지며 내는 경고를 막는다.
        cfg.hardware.backend = 'sim'
        super().__init__(cfg)
        self.icfg = icfg
        self.backend_name = backend
        self.state.ics_build = build_id()      # 배너·STATUS 응답용
        if backend == 'icg_archon':
            self.guide = GuideBackend(cfg, icfg)
        else:
            self.guide = SimGuideBackend(cfg, icfg)
        self.radionode = RadionodeClient(icfg.radionode)
        self.hk = HkMonitor(self.guide.ctrl, icfg, telem=self.telem,
                            expstatus=lambda: self.state.expstatus,
                            spawn=self.spawn)
        self.hk.radionode = self.radionode
        self.seq = GuideSequencer(cfg, icfg, self.state, self.emit,
                                  self.telem, self.guide, self.hk)
        self.dispatch = icg_commands.IcgDispatcher(self)

    # -- 수명 ---------------------------------------------------------------

    async def start(self) -> None:
        for line in validate(self.icfg, self.backend_name):
            log.warning('%s', line)
        await super().start()
        self._log_icg_banner()
        if self.backend_name == 'icg_archon':
            # 기동 접속 -- 실패해도 기동은 계속한다 (ics_archon 과 같은
            # 규칙: 컨트롤러 전원이 나중에 들어오는 배치가 실재한다).
            self.spawn(self._connect_controller())
        self.hk.start()
        self.radionode.start(self.spawn)

    async def _connect_controller(self) -> None:
        try:
            await self.guide.prepare()
            log.info('guide 컨트롤러 준비 완료 (%s)', self.icfg.host)
        except Exception as exc:  # noqa: BLE001
            log.error('guide 컨트롤러 기동 접속 실패 -- %s.  HK 감시가 '
                      '주기적으로 다시 시도하고, 첫 GO 의 prepare() 가 '
                      '다시 시도한다', exc)

    async def stop(self) -> None:
        await self.hk.stop()
        await self.radionode.stop()
        await self.seq.drain_writers(self.icfg.shutdown_drain)
        try:
            await self.guide.shutdown()
        except Exception as exc:  # noqa: BLE001
            log.warning('guide 백엔드 종료 실패 -- %s', exc)
        await super().stop()

    # -- 배너 ---------------------------------------------------------------

    def _log_icg_banner(self) -> None:
        i = self.icfg
        rn = i.radionode
        lines = [
            '-- icg (guide) 배선 ' + '-' * 40,
            'build        : %s' % build_id(),
            'controller   : %s:%d (tag %s)  acf=%s' % (
                i.host or '(미설정)', i.port, TAG, i.acf_path or '(없음)'),
            'geometry     : %dx%d (%.2f MiB/frame)  exptime_min=%.1fs' % (
                i.naxis1, i.naxis2, i.frame_bytes / (1 << 20), i.exptime_min),
            'hk           : every %.0fs -> %s (latest: %s)' % (
                i.hk.interval, i.hk.log_dir, i.hk.latest_name),
            'radionode    : %s (poll %.0fs, devices: %s)' % (
                rn.backend, rn.poll_period,
                ', '.join(d.alias for d in rn.devices) or '없음'),
            'backend      : %s' % self.backend_name,
            '-' * 60,
        ]
        log.info('\n%s', '\n'.join(lines))

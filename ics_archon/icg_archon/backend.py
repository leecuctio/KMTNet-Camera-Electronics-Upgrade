#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide 백엔드 -- Archon 한 대 (`ics_archon.archon` 계층 재사용).

science 의 `ArchonBackend` 와 달리 `ics_sim` 의 `DetectorBackend` 계약을
따르지 않는다 -- 그 계약은 4-CCD/2-컨트롤러 노출 상태기의 모양이고, guide
는 frame-transfer 연속 독출이라 시퀀서 자체가 다르다 (`sequencer.py`).
대신 `GuideSequencer` 가 부르는 좁은 표면을 낸다:

* `prepare()`            -- 접속·ACF·전원 (멱등, `ArchonController.prepare`)
* `trigger_frame()`      -- 독출 1회 지시 (`IntMS=0` -- **호스트가 주기를
                            만든다**, 아래 "왜 IntMS=0 인가")
* `wait_frame()`         -- 진행률 yield (컨트롤러 위임)
* `write_frame()`        -- fetch + guide FITS 저장 (`guidecards.WIDTHS`)
* `sensors()`/`ctrl_telemetry()`/`controller_info()` -- 헤더용 사실

## 왜 `IntMS=0` 인가 (PROVISIONAL -- guide OI-23 인접)

frame-transfer 에서 노출은 "직전 트랜스퍼(=독출 개시)부터 이번 트랜스퍼
까지" 다 (raw spec 10.1절).  `IntMS=<노출>` 로 걸면 실제 독출 개시 간격은
`IntMS + 독출 시간`이 되어 헤더 `EXPTIME`(= 독출 개시 간격, 10.1-1)이
조용히 어긋난다.  그래서 **적분 대기는 호스트가 재고**(시퀀서의 절대 시각
pacing) 컨트롤러에는 `IntMS=0` 으로 "지금 읽어라" 만 시킨다.  트리거
지연·독출 시간의 실측은 첫 구동 몫이고, 그때 `ContinuousExposures`(ACF
PARAMETER0) 경로와 비교해 확정한다.
"""

from __future__ import annotations

import asyncio
import logging
import os

from ics_archon import _simpath

_simpath.ensure()

from ics_archon.archon import fitswrite, parse  # noqa: E402
from ics_archon.archon.controller import ArchonController, ArchonError  # noqa: E402
from ics_archon.config import cfg_name_from_acf, rdmode_from_acf  # noqa: E402
from ics_sim import rawhdr  # noqa: E402

from . import guidecards  # noqa: E402
from .config import TAG, IcgCfg  # noqa: E402

log = logging.getLogger('icg_archon.backend')


class GuideBackendError(Exception):
    """취득 한 사이클을 세우는 실패 -- 시퀀서가 ERROR 통보로 옮긴다."""


class GuideBackend:
    """guide Archon 한 대의 취득·사실 창구."""

    name = 'archon_guide'

    def __init__(self, cfg, icfg: IcgCfg) -> None:  # noqa: ANN001
        self.cfg = cfg            # ics_sim.config.SimConfig
        self.icfg = icfg
        self.ctrl = ArchonController(TAG, icfg)
        self._trigger_forced = False
        # numpy 는 저장형 변환의 하드 의존이다 (science 백엔드와 같은 이유).
        try:
            import numpy  # noqa: F401
        except ImportError as exc:      # pragma: no cover
            raise RuntimeError(
                'icg_archon 백엔드는 numpy 가 필요하다 (FITS 저장형 변환) -- '
                'pip install numpy 후 다시 띄울 것') from exc
        log.info('guide 백엔드 -- %s:%d, 선언 기하 %dx%d (%.2f MiB/프레임)',
                 icfg.host or '(미설정)', icfg.port, icfg.naxis1, icfg.naxis2,
                 icfg.frame_bytes / (1 << 20))

    # -- 준비 ---------------------------------------------------------------

    async def prepare(self) -> None:
        """접속·ACF·전원 -- 멱등.  실패는 그대로 올린다 (시퀀서가 통보)."""
        await self.ctrl.prepare()
        if not self._trigger_forced:
            # guide 는 셔터가 없다 -- TRIGOUT 을 노출마다 흔들 일이 없으므로
            # 한 번만 강제 상태로 둔다 (modtm_gui 원형과 같은 자리).
            await self.ctrl.set_trigger_forced(True)
            self._trigger_forced = True

    # -- 취득 ---------------------------------------------------------------

    async def trigger_frame(self, *, queue: bool, suffix: str = ''):  # noqa: ANN201
        """독출 1회 지시 -- `FrameTicket` 을 돌려준다.

        `queue=False` 는 **폐기 프레임**(첫 독출, 10.1-2)이다 -- 저장 대기열에
        넣지 않고, fetch 도 하지 않는다 (버퍼 회전만 확인).  폐기분의 트리거
        시각이 다음 저장 프레임의 `DATE-OBS` 가 되므로 메타(시각)는 시퀀서가
        든다.
        """
        try:
            return await self.ctrl.trigger(0, queue=queue, suffix=suffix)
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError(
                'DMA WAIT TIMEOUT. EXPOSURES ABORTED.') from exc

    def wait_frame(self, ticket):  # noqa: ANN001, ANN201
        """진행률 yield -- 컨트롤러 위임 (완료는 `ticket.ready`)."""
        return self.ctrl.wait_frame(ticket)

    async def write_frame(self, suffix: str, path: str, cards) -> int:  # noqa: ANN001
        """fetch + guide FITS 저장.  반환은 전송률 [KB/s].

        science `ArchonBackend.write_frame()` 과 같은 뼈대 -- **저장 표를
        `take_ticket(suffix)` 로 대기열에서 집어 온다** (안 집으면 표가
        영구히 쌓인다 -- FIFO 라 다음 사이클이 남의 표를 집는다).  다른
        것은 기하(8.3 MiB)와 **`guidecards.WIDTHS`**(공유 키 8장의 폭이
        science 와 달라 science 폭 표로 패딩하면 견본과 어긋난다).
        `suffix` 는 트리거 때 준 **최초 배정분**이다 (D-016 밀림과 무관 --
        science 의 EXPID 규칙과 같다).
        """
        ticket = self.ctrl.take_ticket(suffix)
        if ticket is None:
            raise GuideBackendError(
                'No pending guide frame for %s' % (suffix or '?'))
        try:
            fs = await self.ctrl.await_frame(ticket)
            raw = await self.ctrl.fetch(fs, self.icfg.frame_bytes)
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError(
                'Failed to fetch guide frame') from exc
        try:
            rate = await asyncio.to_thread(
                fitswrite.write_frame, path, cards, raw,
                naxis1=self.icfg.naxis1, naxis2=self.icfg.naxis2,
                widths=guidecards.WIDTHS)
        except (OSError, ValueError, ImportError) as exc:
            log.error('guide FITS 저장 실패 -- %s', exc)
            raise GuideBackendError('Failed to write guide FITS') from exc
        finally:
            self.ctrl.release_buffer(raw)
        log.info('%s 저장 (%d KB/sec)', os.path.basename(path), rate)
        return rate

    async def discard_frame(self, ticket) -> None:  # noqa: ANN001
        """폐기 프레임 -- 완료만 확인하고 fetch 하지 않는다 (10.1-2).

        완료 확인을 생략하면 다음 트리거가 독출 중에 겹칠 수 있다 --
        회전(버퍼가 실제로 돌았나)은 다음 프레임의 `wait_frame` 이 프레임
        번호 증가로 함께 확인한다.
        """
        try:
            await self.ctrl.await_frame(ticket)
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError(
                'Discard frame did not complete') from exc
        finally:
            self.ctrl.release_current()

    def drop_pending(self, why: str) -> int:
        """대기 중 저장 표를 버린다 (ABORT)."""
        return self.ctrl.drop_tickets(why)

    # -- 헤더용 사실 ----------------------------------------------------------

    def controller_info(self) -> dict:
        """`CTRL1ID`/`CTRL1SN`/`CTRL1CFG` 원자료 -- science 와 같은 유도.

        ini(`[controllers] ctrl1_*`)가 이기고, 비면 컨트롤러 보고값
        (`unit_identity`)과 ACF 이름에서 파생한다 (raw spec 5.5절).
        """
        ident = parse.unit_identity(self.ctrl.system or {})
        unit = {
            'id': ident.get('id', ''),
            'sn': ident.get('sn', ''),
            'cfg': cfg_name_from_acf(self.ctrl.acf_path
                                     or self.icfg.acf_path),
        }
        return {'units': [unit]}

    def rdmode(self) -> str:
        """`RDMODE` -- ini > ACF 이름 토큰 > `UNKNOWN` (raw spec 10.3절).

        guide ACF 이름에는 속도 토큰이 없어 파생이 비므로, 결측값
        `UNKNOWN`(운영자 확정 2026-08-29 -- 코드 선반영)이 기본이 된다.
        """
        ini = (self.cfg.controllers.rdmode or '').strip()
        if ini:
            return ini
        derived = rdmode_from_acf(self.ctrl.acf_path or self.icfg.acf_path)
        return derived or rawhdr.RDMODE

    async def shutdown(self) -> None:
        """전원을 시도했으면 끈다 -- science 백엔드와 같은 규칙."""
        try:
            if self.ctrl.powered or self.ctrl.power_attempted:
                await self.ctrl.power_off()
        except (ArchonError, TimeoutError, OSError) as exc:
            log.warning('종료 POWEROFF 실패 -- %s', exc)


class _SimTicket:
    """SimGuideBackend 의 프레임 표 -- 시각·번호만 든다."""

    def __init__(self, n: int) -> None:
        self.frame = n
        self.ready = None


class SimGuideBackend:
    """컨트롤러 없이 메시지 층·시퀀서 회귀를 돌리는 대역 (`--backend sim`).

    실기 `GuideBackend` 와 같은 표면 -- 트리거는 즉답, 독출은 진행률 두 틱,
    저장은 `[paths] write_fits` 가 참일 때만 0 프레임을 실제 기하로 쓴다
    (guide 는 8.3 MiB 라 시뮬로도 싸다).
    """

    name = 'sim_guide'

    def __init__(self, cfg, icfg: IcgCfg) -> None:  # noqa: ANN001
        self.cfg = cfg
        self.icfg = icfg
        self.ctrl = None
        self._n = 0

    async def prepare(self) -> None:
        return None

    async def trigger_frame(self, *, queue: bool, suffix: str = ''):  # noqa: ANN201, ARG002
        self._n += 1
        return _SimTicket(self._n)

    async def wait_frame(self, ticket):  # noqa: ANN001, ANN201
        for pct in (50, 100):
            await asyncio.sleep(0)
            yield pct

    async def discard_frame(self, ticket) -> None:  # noqa: ANN001
        return None

    def drop_pending(self, why: str) -> int:  # noqa: ARG002
        return 0

    async def write_frame(self, suffix: str, path: str, cards) -> int:  # noqa: ANN001, ARG002
        if not self.cfg.paths.write_fits:
            return 0
        import numpy as np
        raw = bytearray(
            np.zeros(self.icfg.naxis1 * self.icfg.naxis2,
                     dtype='<u2').tobytes())
        return await asyncio.to_thread(
            fitswrite.write_frame, path, cards, raw,
            naxis1=self.icfg.naxis1, naxis2=self.icfg.naxis2,
            widths=guidecards.WIDTHS)

    def controller_info(self) -> dict:
        return {'units': [{'id': '', 'sn': '',
                           'cfg': cfg_name_from_acf(self.icfg.acf_path)}]}

    def rdmode(self) -> str:
        return (self.cfg.controllers.rdmode or '').strip() or rawhdr.RDMODE

    async def shutdown(self) -> None:
        return None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide 백엔드 -- Archon 한 대 (`ics_archon.archon` 계층 재사용).

science 의 `ArchonBackend` 와 달리 `ics_sim` 의 `DetectorBackend` 계약을
따르지 않는다 -- 그 계약은 4-CCD/2-컨트롤러 노출 상태기의 모양이고, guide
는 frame-transfer 연속 독출이라 시퀀서 자체가 다르다 (`sequencer.py`).
대신 `GuideSequencer` 가 부르는 좁은 표면을 낸다:

* `prepare()`            -- 접속·ACF·전원 (멱등, `ArchonController.prepare`)
* `arm_sequence()`/`next_ticket()` -- **연속 노출** (시퀀서 pacing, 아래)
* `wait_frame()`         -- 진행률 yield (컨트롤러 위임)
* `write_frame()`        -- fetch + guide FITS 저장 (`guidecards.WIDTHS`)
* `sensors()`/`ctrl_telemetry()`/`controller_info()` -- 헤더용 사실

## 주기는 **시퀀서**가 만든다 (운영자 확정 2026-08-31)

`Exposures = n+1` 을 한 번만 걸면 타이밍 스크립트가 `GOTO Start` 뒤
`Exposures` 가 남아 있는 동안 **유휴 없이** 다음 프레임으로 간다.  그래서
독출 개시 간격이 Archon 타이밍 코어(100 MHz)로 정해진다:

    주기 = IntMS + NoIntMS + 트랜스퍼 + 독출
         = IntMS + 하한(`acftiming.frame_timing()['floor']`)

호스트는 `IntMS = EXPTIME - 하한` 만 계산해 넣고 프레임 완료를 따라간다
(`intms_for()`).  **하한보다 짧게 요청하면 하한으로 눌러 담는다** --
거부하지 않는다 (운영자 지시).  그때 헤더 `EXPTIME` 은 요청값이 아니라
**실현값**이다 (`effective_exptime()`).

⚠️ **주기가 하드웨어로 고정되는 것은 FETCH 가 방해하지 않을 때뿐이다** --
실기 관측(DevNote 8.9, FW 1261)에서 **FETCH 중 다음 프레임의 readout 이
멈춘다**.  그래서 `EXPTIME` 이 하한에 가까우면 FETCH(8.3 MiB ≈ 0.12 s)가
다음 독출과 겹쳐 주기가 늘어난다 -- 시퀀서는 그것을 모르고 호스트도 못
막는다.  실효 하한은 `하한 + FETCH` 로 보는 것이 안전하고, 실측은 첫
구동 몫이다 (DevNote 9.12).
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

from . import acftiming, guidecards  # noqa: E402
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
        #: ACF 타이밍 스크립트에서 계산한 프레임 주기 (`acftiming`).
        #: 왕복 없이 파일만 읽으므로 기동에서 바로 잡는다 -- 이 값이 있어야
        #: `EXPTIME` 하한과 `DATE-OBS` 트랜스퍼 보정이 근거를 갖는다.
        self.timing = self._read_timing()

    def _read_timing(self) -> dict | None:
        path = self.icfg.acf_path
        if not path or not os.path.isfile(path):
            log.warning('guide ACF 를 못 읽어 프레임 주기를 계산하지 못했다 '
                        '(%s) -- EXPTIME 하한·DATE-OBS 보정이 ini 기본값을 '
                        '쓴다', path or '(미설정)')
            return None
        if not acftiming.verify_tick_anchor():   # pragma: no cover
            log.error('acftiming 셈법 검산 실패 -- NoIntUnit 이 1 ms 가 '
                      '아니다.  타이밍 계산을 신뢰하지 않는다')
            return None
        try:
            probe = ArchonController(TAG, self.icfg)
            probe.parse_acf(path)                # 왕복 없음
            params = acftiming.parameters(probe.config)
            t = acftiming.frame_timing(
                params,
                lines=int(params.get('Lines', self.icfg.naxis2)),
                pixels=int(params.get('Pixels', 0)) or 600)
        except (ArchonError, OSError, ValueError) as exc:
            log.warning('guide ACF 타이밍 계산 실패 -- %s', exc)
            return None
        log.info('guide 프레임 타이밍 (ACF 계산, PROVISIONAL) -- %s',
                 acftiming.describe(t))
        return t

    # -- 노출 주기 (규격 10.1절) --------------------------------------------

    def frame_floor(self) -> float:
        """`EXPTIME` 의 하드웨어 하한 [s] -- 이보다 짧은 독출 개시 간격은
        만들 수 없다 (`NoIntMS` + 트랜스퍼 + 독출)."""
        if self.timing:
            return self.timing['floor']
        return self.icfg.exptime_min

    def intms_for(self, exptime_s: float) -> int:
        """요청 `EXPTIME` -> 시퀀서에 걸 `IntMS` [ms].

        주기 = `IntMS` + 하한(`NoIntMS` + 트랜스퍼 + 독출) 이므로
        `IntMS = EXPTIME - 하한` 이다.  **하한보다 짧게 요청하면 0** --
        하드웨어가 만들 수 있는 가장 짧은 주기가 된다 (운영자 확정
        2026-08-31: "더 작게 설정해도 최소 노출시간으로").
        """
        return max(0, int(round((exptime_s - self.frame_floor()) * 1000.0)))

    def effective_exptime(self, exptime_s: float) -> float:
        """**실제로 실현되는** 독출 개시 간격 [s] -- 헤더 `EXPTIME` 은 이 값.

        요청값이 아니라 실현값을 싣는다 -- 규격 10.1-1 이 `EXPTIME` 을
        "연속 두 프레임 독출 개시 시각의 간격" 으로 정의하므로, 하한에
        걸려 못 만든 주기를 그대로 적으면 카드가 거짓말이 된다.
        `IntMS` 가 ms 단위로 반올림되는 것까지 반영한다.
        """
        return self.frame_floor() + self.intms_for(exptime_s) / 1000.0

    def trigger_to_transfer(self, intms: int = 0) -> float:
        """노출 개시 -> 프레임 트랜스퍼 지연 [s].

        시퀀서는 `IntUnit(IntMS)` + `NoIntUnit(NoIntMS)` 를 돌린 **뒤에**
        트랜스퍼한다.  `DATE-OBS` 는 그 트랜스퍼(=독출 개시) 시각이므로
        (10.1-4·5) 이 값을 더해야 한다.
        """
        base = self.timing['trigger_to_transfer'] if self.timing else 0.0
        return base + max(intms, 0) / 1000.0

    # -- 연속 노출 (시퀀서 pacing) -------------------------------------------

    async def arm_sequence(self, frames: int, intms: int, *,
                           suffix: str = '', queue: bool = False):  # noqa: ANN201
        """`Exposures=frames` 를 **한 번에** 걸고 첫 표를 돌려준다.

        이후 프레임은 `next_ticket()` 이 표만 잇는다 -- 시퀀서가 유휴 없이
        연달아 찍으므로 호스트는 주기를 만들지 않는다 (DevNote 9.12).
        """
        try:
            return await self.ctrl.trigger(intms, queue=queue, suffix=suffix,
                                           exposures=frames)
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError(
                'DMA WAIT TIMEOUT. EXPOSURES ABORTED.') from exc

    async def next_ticket(self, after, intms: int, *, suffix: str = '',
                          queue: bool = True):  # noqa: ANN001, ANN201
        """이미 걸린 연속 노출의 다음 표 (`LOADPARAMS` 없음)."""
        try:
            return await self.ctrl.expect_next(after, suffix=suffix,
                                               exptime_ms=intms, queue=queue)
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError(
                'Failed to track the next guide frame') from exc

    async def stop_sequence(self) -> None:
        """남은 연속 노출을 끊는다 (현재 프레임은 끝난다)."""
        try:
            await self.ctrl.set_exposures(0)
        except (ArchonError, TimeoutError, OSError) as exc:
            log.warning('Exposures=0 을 못 걸었다 -- %s (남은 프레임이 더 '
                        '나올 수 있다)', exc)

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

    async def wait_frame(self, ticket):  # noqa: ANN001, ANN201
        """진행률 yield -- 컨트롤러 위임 (완료는 `ticket.ready`).

        컨트롤러 예외(프레임 시한·건너뜀·연결 단절)를 `GuideBackendError`
        로 감싼다 -- 이 표면만 무포장이면 독출 실패가 시퀀서 태스크를
        무처리로 죽여 `EXPSTATUS=READOUT` 고착 + 통보 0 이 된다 (science
        `_readout_stream` 의 안전망과 같은 자리다.  실기 실증 경로: Sync In
        사고의 프레임 시한).
        """
        try:
            async for pct in self.ctrl.wait_frame(ticket):
                yield pct
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError(
                'DMA WAIT TIMEOUT. EXPOSURES ABORTED.') from exc

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

    async def discard_frame(self, ticket, *, release: bool = True) -> None:  # noqa: ANN001
        """폐기 프레임 -- 완료만 확인하고 fetch 하지 않는다 (10.1-2).

        완료 확인을 생략하면 다음 프레임의 기준선을 못 잡는다 -- 회전(버퍼가
        실제로 돌았나)은 다음 프레임의 `wait_frame` 이 번호 증가로 함께
        확인한다.

        Args:
            release: 연속 노출에서는 **`False`** 다.  `release_current()` 는
                "이번 프레임이 끝났다" 표시인데, 시퀀서 pacing 에서는 다음
                프레임이 이미 시퀀서 안에서 돌고 있어 그 표시가 뜻을 잃는다.
                ⚠️ 어느 쪽이든 `ticket.ready` 는 남는다 -- 다음 표의
                기준선이라 지우면 안 된다.
        """
        try:
            await self.ctrl.await_frame(ticket)
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError(
                'Discard frame did not complete') from exc
        finally:
            if release:
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
        #: 대역은 하드웨어가 없다 -- 주기 제약도 없는 것으로 둔다(시험이
        #: 짧은 EXPTIME 으로 돌 수 있어야 한다).
        self.timing = None
        #: 마지막으로 건 `IntMS` -- 대역이 주기를 흉내내는 근거.
        self._intms = 0

    def frame_floor(self) -> float:
        return self.icfg.exptime_min

    def trigger_to_transfer(self, intms: int = 0) -> float:
        return max(intms, 0) / 1000.0

    async def prepare(self) -> None:
        return None

    async def trigger_frame(self, *, queue: bool, suffix: str = ''):  # noqa: ANN201, ARG002
        self._n += 1
        return _SimTicket(self._n)

    async def wait_frame(self, ticket):  # noqa: ANN001, ANN201
        """**주기를 흉내낸다** -- `time_scale` 로 줄인 프레임 주기만큼 쉰다.

        즉시 끝내면 프레임들이 같은 밀리초에 몰려 `DATE-OBS` 가 겹치고,
        저장이 서로 겹쳐 실기에서는 안 나는 경고가 뜬다 -- 대역이 실기와
        다른 모양으로 도는 것을 시험이 정상으로 배우면 안 된다.
        """
        period = self.cfg.scaled(
            self.frame_floor() + max(self._intms, 0) / 1000.0)
        for pct in (50, 100):
            await asyncio.sleep(max(period, 0.0) / 2.0)
            yield pct

    async def discard_frame(self, ticket, *, release: bool = True) -> None:  # noqa: ANN001, ARG002
        return None

    def drop_pending(self, why: str) -> int:  # noqa: ARG002
        return 0

    # -- 연속 노출 대역 (실기와 같은 표면) ----------------------------------

    def intms_for(self, exptime_s: float) -> int:
        return max(0, int(round((exptime_s - self.frame_floor()) * 1000.0)))

    def effective_exptime(self, exptime_s: float) -> float:
        return self.frame_floor() + self.intms_for(exptime_s) / 1000.0

    async def arm_sequence(self, frames: int, intms: int, *,  # noqa: ARG002
                           suffix: str = '', queue: bool = False):  # noqa: ANN201, ARG002
        self._intms = intms
        self._n += 1
        return _SimTicket(self._n)

    async def next_ticket(self, after, intms: int, *,  # noqa: ANN001, ARG002
                          suffix: str = '', queue: bool = True):  # noqa: ANN201, ARG002
        self._intms = intms
        self._n += 1
        return _SimTicket(self._n)

    async def stop_sequence(self) -> None:
        return None

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

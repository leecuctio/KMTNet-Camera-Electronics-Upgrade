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

`Exposures = n` (+ `FirstFlush=1`, R2613+) 을 한 번만 걸면 타이밍 스크립트가 `GOTO Start` 뒤
`Exposures` 가 남아 있는 동안 **유휴 없이** 다음 프레임으로 간다.  그래서
독출 개시 간격이 Archon 타이밍 코어(100 MHz)로 정해진다:

    주기 = IntMS + NoIntMS + 트랜스퍼 + 독출
         = IntMS + 하한(`acftiming.frame_timing()['floor']`)

호스트는 `IntMS = EXPTIME - 하한` 만 계산해 넣고 프레임 완료를 따라간다
(`intms_for()`).  **하한보다 짧게 요청하면 하한으로 눌러 담는다** --
거부하지 않는다 (운영자 지시).  그때 헤더 `EXPTIME` 은 요청값이 아니라
**실현값**이다 (`effective_exptime()`).

**FETCH 는 readout 을 멈추지 않는다** -- 종전 8.9 의 "FETCH 중 정지" 는 GUI
표시 착시였다 (2026-09-02 실측, science 두 유닛 + GUI 재관측 -- DevNote
10.5).  그러니 **실효 하한 = 하한**이고 "+FETCH" 여백은 없다.  ⚠️ 다만
science 실측을 guide 에 옮긴 것이라 첫 구동에서 실현 주기를 재는 항목은
그대로다 (`sequencer` 의 실현 간격 감시).

⚠️ **대신 잠금은 주기보다 짧아야 한다** (DevNote 10.6) -- `LOCKn` 을 쥔 채
프레임 경계를 넘으면 엔진은 잠긴 버퍼를 피해 나머지로 돌고, 남는 버퍼가
없으면 **쓰던 버퍼를 재사용**해 다음 장을 덮는다.  ⚠️ 10.6 의 `--hold 20`
은 science **2버퍼**(BIGBUF=1) 실측이다 -- guide 는 버퍼 셋(`BIGBUF=0`)이라
하나를 잠그면 둘이 남고, 3버퍼에서 못 받은 장이 언제 덮이는지는 ⏳ 첫 구동
실측 항목이다 (FETCH 뒤 `lock_rbuf`/`lock_wbuf_after` 관측).  어느 쪽이든
FETCH 상한(`[icg] fetch_timeout`)이 곧 잠금 상한이므로 **하한 미만**으로 (하한은
`acftiming` 이 ACF 에서 셈한다 -- R2610~R2614 기준 1.251 s)
두는 것이 보수적 안전선이다 -- guide 는 8.3 MiB ≈ 0.08 s 라 1 s 면 넉넉하다.
`__init__` 이 이를 검사한다 (0 이면 유도값 60 s 로 셈한다).
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
        # ⭐ 잠금은 주기보다 짧아야 한다 (DevNote 10.6, 2026-09-01 실측) -- FETCH
        # 상한이 곧 잠금 상한이다.  guide FETCH 는 8.3 MiB ≈ 0.08 s (science
        # 실측 99~107 MiB/s 기준) 라 1 s 면 12배 여유고 하한(1.251 s) 아래다.
        # ⚠️ PROVISIONAL -- guide 링크 속도는 첫 구동에서 FETCH 로그로 확인.
        # ⚠️ 0 은 "크기에서 유도" 다 (`controller.fetch`: max(60, MiB) -- guide 는
        # 60 s).  ini 원값이 아니라 **실제 상한**을 하한과 대본다 (science
        # `config` 의 `fetch_cap` 과 같은 셈).
        cap = (icfg.fetch_timeout if icfg.fetch_timeout > 0
               else max(60.0, icfg.frame_bytes / (1 << 20)))
        if icfg.lock_buffer and cap >= self.frame_floor():
            log.warning('[icg] FETCH 상한 %.1fs (fetch_timeout=%g%s) 가 프레임 하한 '
                        '%.3fs 이상이다 -- lock_buffer=true 에서 잠금이 주기를 넘으면 '
                        '못 받은 장이 덮인다 (DevNote 10.6).  하한 아래(예 1.0)로 '
                        '적을 것', cap, icfg.fetch_timeout,
                        ' -> 크기 유도' if icfg.fetch_timeout <= 0 else '',
                        self.frame_floor())

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
            # R2613+: flush 를 걸 수 있는 판인가 -- 호스트가 쓰는 `FirstFlush` 슬롯이
            # 있으면 된다.  타이밍 셈(아래 형태 검사)과 **무관하게** 여기서 정한다 --
            # 시험의 최소 ACF 는 스크립트가 없어 셈은 못 해도 flush 는 걸어야 한다.
            # 없으면 `arm_sequence` 가 GO 를 거부한다 (R2612 이하에 Exposures=n 을
            # 걸면 첫 장이 flush 없이 저장된다 -- 11.31 must_fix).
            self._flush_capable = 'FirstFlush' in acftiming.parameters(probe.config)
            if not self._flush_capable:
                log.error('guide ACF 에 FirstFlush 파라미터가 없다 (%s) -- R2612 이하다. '
                          'GO 가 거부된다.  R2613+ 를 [icg] acf 에 걸 것 (규격 10.1-2)',
                          os.path.basename(path))
            # ⚠️ 이 셈법은 **guide 타이밍 스크립트 형태** 전용이다 (FrameShift ·
            # HorizontalShift(600) · PixelFirst · CLAMP).  science ACF 는 루틴
            # 배치가 달라(`IntUnit` 이 LINE11, `HorizontalSWShift(1200)`,
            # AT=2000) 억지로 셈하면 그럴싸한 13.65 s 가 나온다 (DevNote 9.15)
            # -- 형태가 다르면 셈하지 않는다.
            bad = acftiming.script_matches(probe.config)
            if bad:
                log.warning('guide ACF 의 타이밍 스크립트가 acftiming 이 아는 '
                            '형태가 아니다 (%s) -- 프레임 주기를 계산하지 않고 '
                            'ini exptime_min 을 쓴다.  science ACF 를 가리키고 '
                            '있지 않은지 볼 것', '; '.join(bad))
                return None
            params = acftiming.parameters(probe.config)
            # ⚠️ `Lines`/`Pixels` 는 **대체값 없이** ACF 에서 읽는다.  종전에는
            # 없으면 600/naxis2 로 셈했는데, 그러면 그럴싸한 하한이 나와 틀린
            # 것이 안 보인다 -- 못 읽으면 ini 대체값 경로로 크게 물러난다.
            missing = [k for k in ('Lines', 'Pixels') if k not in params]
            if missing:
                log.warning('guide ACF 에 %s 파라미터가 없다 -- 프레임 주기를 '
                            '계산하지 않고 ini exptime_min 을 쓴다',
                            '/'.join(missing))
                return None
            t = acftiming.frame_timing(
                params, lines=params['Lines'], pixels=params['Pixels'])
            # ⛔ `FlushLines` 는 **파생값인데 상수로 실려 있다** (규격 10.1-2).
            #    낳는 넷(`Pixels`·`Lines`·`AT`·`ST`)과 같은 파일에 있고 자동
            #    으로 안 따라가므로, 누가 하나만 고치면 **오류 없이 첫 저장
            #    프레임의 실적분만 틀린다.**  기동 때 한 번 대사해 그 조용한
            #    어긋남을 소리 나게 만든다.
            drift = acftiming.check_flush_lines(
                params, lines=params['Lines'], pixels=params['Pixels'])
            if drift is not None:
                log.error('guide ACF 의 FlushLines=%d 가 계산값 %d 와 다르다 '
                          '-- Pixels/Lines/AT/ST 를 고치고 FlushLines 를 안 '
                          '고친 것으로 보인다.  그대로 두면 **첫 저장 프레임의 '
                          '실적분이 EXPTIME 과 다르다** (규격 10.1-2). ACF 를 '
                          '고칠 것 (acf/README.md 의 산수표)', *drift)
            elif 'FlushLines' not in params:
                log.info('guide ACF 에 FlushLines 가 없다 -- flush 프레임 '
                         '길이 맞추기(규격 10.1-2)는 R2611 부터다')
        except (ArchonError, OSError, ValueError) as exc:
            log.warning('guide ACF 타이밍 계산 실패 -- %s', exc)
            return None
        # R2613+: flush 를 걸 수 있는 판인가 -- 형태 검사(`_SHAPE` 의 LINE1·LINE118)를
        # 통과했고 `FirstFlush`·`FlushLines` 가 있어야 한다.  없으면 `arm_sequence` 가
        # GO 를 거부한다 -- `Exposures=n` 으로 걸면 첫 장이 flush 없이 저장되니까.
        log.info('guide 프레임 타이밍 (ACF 계산, PROVISIONAL) -- %s · flush %s',
                 acftiming.describe(t),
                 ('%.4f s' % t['flush']) if t.get('flush') else '(없음 -- R2612 이하)')
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

        ⭐ **카드 해상도는 1 ms** (규격 10.1-1, 2026-09-05) -- `IntMS` 의 분해능이자
        `DATE-OBS` 의 분해능이다.  하한이 ms 경계에 없어서(1.2506283 s) 정수 요청은
        어느 것도 정확히 실현되지 않는데, 1.9996283 을 그대로 실으면 5.4 조건부 형
        규칙으로 카드가 실수형이 된다.  ms 로 반올림하면 `guideexp 2` -> `2`,
        하한 미만 -> `1.251`.
        """
        return round(self.frame_floor() + self.intms_for(exptime_s) / 1000.0, 3)

    def trigger_to_transfer(self, intms: int = 0) -> float:
        """루프 재개(직전 독출 종료) -> 이번 트랜스퍼 지연 [s].

        ⚠️ **"노출 개시"가 아니다.**  frame-transfer 라 image 구간은 독출
        중에도 계속 적분한다 -- 이 프레임의 노출은 *직전* 트랜스펴(=직전
        독출 개시)에 이미 시작됐다 (10.1-5).  여기서 재는 것은 호스트가
        표를 잇는 시각부터 **이번** 트랜스퍼까지의 지연이다: 시퀀서가
        `IntUnit(IntMS)` + `NoIntUnit(NoIntMS)` 를 돌린 **뒤에**
        트랜스퍼하기 때문이다.  `DATE-OBS` 는 그 트랜스퍼(=독출 개시)
        시각이므로 (10.1-4) 이 값을 더해야 한다.
        """
        base = self.timing['trigger_to_transfer'] if self.timing else 0.0
        return base + max(intms, 0) / 1000.0

    def trigger_to_frameshift(self, intms: int = 0) -> float:
        """표 잇는 시각 -> 이번 `FrameShift` **개시** [s] -- 10.1-4 의 DATE-OBS 기준.

        `trigger_to_transfer` 와 다르다: 그쪽은 트랜스퍼 **종료**(+HS+clamp ≈ Line
        독출 개시)까지고, 규격은 개시를 기준으로 못박았다 (R2613 반영, 11.31).
        """
        base = self.timing['to_frameshift'] if self.timing else 0.0
        return base + max(intms, 0) / 1000.0

    def frameshift_to_done(self) -> float:
        """`FrameShift` 개시 -> 프레임 완료 [s] (transfer + 독출).

        완료 관측 시각에서 이것을 빼면 그 프레임의 FrameShift 개시 = **다음** 프레임의
        DATE-OBS 다.  ⚠️ 완료 관측은 폴링 지연(frame_poll)만큼 늦다 -- 그만큼
        DATE-OBS 가 늦는 편향이 있다 (11.31, 예측 폴링은 후속).
        """
        if self.timing:
            return self.timing['frameshift_to_done']
        # 모델이 없으면(스크립트 없는 시험 ACF) 완료 시각을 그대로 -- 독출 한 번만큼
        # 늦지만 **단조**다.  ini 하한(비스케일 2 s)을 빼면 가짜/대역에서 DATE-OBS 가
        # 뒤로 간다.
        return 0.0

    def flush_duration(self) -> float:
        """flush 프레임 소요 [s] (R2613 LINE115~118) -- 규격 10.1-2 로 본 독출과 같다."""
        f = self.timing.get('flush') if self.timing else None
        return f if f is not None else self.frame_floor()

    # -- 연속 노출 (시퀀서 pacing) -------------------------------------------

    async def arm_sequence(self, frames: int, intms: int, *,
                           flush: bool = True,
                           suffix: str = '', queue: bool = True):  # noqa: ANN201
        """`Exposures=frames` (+ `FirstFlush=1`) 를 **한 LOADPARAMS 로** 걸고 첫 표를 돌려준다.

        R2613+ (규격 10.1-2·3): `go n` = flush 1회 + 독출 n회 · n장 저장.  코어가
        `FirstFlush` 를 보고 IntUnit 없이 곧바로 FrameShift 하므로 **그 순간이 첫 저장
        프레임의 DATE-OBS** 다 -- 표의 `armed_utc` 가 그 근사값이다.  이후 프레임은
        `next_ticket()` 이 표만 잇는다 (DevNote 9.12).

        ⛔ ACF 가 R2612 이하(FirstFlush/FlushFrame 없음)면 **GO 를 거부한다** -- 그
        판에 `Exposures=n` 을 걸면 첫 장이 flush 없이 저장된다 (11.31 must_fix).
        """
        if flush and not getattr(self, '_flush_capable', False):
            raise GuideBackendError(
                'guide ACF has no FirstFlush/FlushFrame (R2612 or older) -- '
                'load R2613+ or fix [icg] acf (spec 10.1-2)')
        try:
            return await self.ctrl.trigger(intms, queue=queue, suffix=suffix,
                                           exposures=frames,
                                           flush=1 if flush else None)
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

    async def tail_ticket(self):  # noqa: ANN201
        """표 없이 도는 프레임(꼬리)의 표 -- 지금 `FRAME` 을 기준선으로 (9.15-(9))."""
        try:
            return await self.ctrl.expect_from_now(suffix='', queue=False)
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError('Failed to baseline the tail frame') from exc

    def loadparams_sent(self) -> bool:
        """이번 arm 의 `LOADPARAMS` 가 나갔나 -- 표 없이 취소됐을 때 꼬리 유무의 근거."""
        return bool(getattr(self.ctrl, 'loadparams_sent', False))

    async def newest_frame(self):  # noqa: ANN201
        """지금 완료돼 있는 가장 새 프레임 번호 (-1 = 없음) -- 꼬리가 둘인지 가른다."""
        try:
            return await self.ctrl.newest_frame()
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError('Failed to read the newest frame') from exc

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

        `queue=False` 는 **저장하지 않는 프레임**(꼬리 배수 · 시험용 단발 경로 -- R2613+ 사이클에는 폐기분이 없다)이다 -- 저장 대기열에
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
        """저장하지 않는 프레임(꼬리 배수 · 낯선 첫 프레임 가드) -- 완료만 확인하고 fetch 하지 않는다 (10.1-2).

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

    def trigger_to_frameshift(self, intms: int = 0) -> float:
        return max(intms, 0) / 1000.0

    def frameshift_to_done(self) -> float:
        # 대역은 `wait_frame` 이 scaled 로 자므로 되짚는 폭도 같은 축이어야 DATE-OBS 가
        # 단조다 (비스케일 2 s 를 빼면 뒤로 간다 -- test_guide_header_semantics).
        return self.cfg.scaled(self.frame_floor())

    def flush_duration(self) -> float:
        """대역의 flush 소요 -- 실기와 같이 본 독출(하한)과 같은 길이로 흉내낸다."""
        return self.frame_floor()

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
        if getattr(self, '_flush_pending', False):
            # R2613+: 첫 프레임 앞의 flush -- 실기처럼 한 독출만큼 더 걸린다.  안 흉내내면
            # 첫 프레임이 즉시 끝나 시퀀서의 '너무 이른 첫 프레임' 가드가 그것을 남의
            # 것으로 버려 시험이 어긋난다 (11.31).
            self._flush_pending = False
            await asyncio.sleep(self.cfg.scaled(self.flush_duration()))
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
        return round(self.frame_floor() + self.intms_for(exptime_s) / 1000.0, 3)

    async def arm_sequence(self, frames: int, intms: int, *,  # noqa: ARG002
                           flush: bool = True,
                           suffix: str = '', queue: bool = True):  # noqa: ANN201, ARG002
        self._intms = intms
        self._flush_pending = bool(flush)
        self._n += 1
        return _SimTicket(self._n)

    async def next_ticket(self, after, intms: int, *,  # noqa: ANN001, ARG002
                          suffix: str = '', queue: bool = True):  # noqa: ANN201, ARG002
        self._intms = intms
        self._n += 1
        return _SimTicket(self._n)

    async def stop_sequence(self) -> None:
        return None

    async def tail_ticket(self):  # noqa: ANN201
        return None                          # 대역은 꼬리가 없다 -- 소화 생략

    async def newest_frame(self):  # noqa: ANN201
        return None

    def loadparams_sent(self) -> bool:
        return False

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

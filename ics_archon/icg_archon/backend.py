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

`Exposures = n` 을 한 번만 걸면 타이밍 스크립트가 `GOTO Start` 뒤
`Exposures` 가 남아 있는 동안 **유휴 없이** 다음 프레임으로 간다.
(flush 는 R2616+ 의 ACF 상수 `FirstFlush=1` 이 싣는다 -- 모든 LOADPARAMS 가 RAM 에
1 을 실어 코어가 `FlushFrame` 한 번을 돌고 `FirstFlush--` 로 소비하며, **호스트는 이
슬롯을 쓰지도 되쓰지도 않는다**.  DevNote 11.33)  그래서
독출 개시 간격이 Archon 타이밍 코어(100 MHz)로 정해진다:

    주기 = IntMS + NoIntMS + 트랜스퍼 + 독출
         = IntMS + **기본 노출시간**(`acftiming.frame_timing()['floor']`)

호스트는 요청을 먼저 **설정 가능한 최소 노출시간**(`exptime_min`, 기본 1.3 s)으로
접고, `IntMS = EXPTIME - 기본 노출시간` 으로 셈해 넣는다 (`intms_for()`).
⛔ **접는 기준과 빼는 기준은 다른 물건이다** (규격 10.1-1) -- 빼는 쪽에 최소
노출시간을 넣으면 헤더가 거짓이 된다.  짧게 요청해도 거부하지 않고 눌러 담으며,
그때 헤더 `EXPTIME` 은 요청값이 아니라 **실현값**이다 (`effective_exptime()`).

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
`acftiming` 이 ACF 에서 셈한다 -- R2610~R2618 기준 1.251 s)
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
from ics_archon.config import cfg_name_from_acf  # noqa: E402
from ics_sim import rawhdr  # noqa: E402

from . import acftiming, guidecards, guidehdr  # noqa: E402
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
        # ⭐ **자리 표를 꽂아 준다** -- guide 는 규격 10.4절 8자리다.
        # 안 꽂으면 컨트롤러가 science 표(5.6.1절 10자리)로 대조해
        # 정상 구성에서 `extra [6,7]`·`missing [1,2,8,11]` 오경보가 난다.
        self.ctrl.temp_fields = guidehdr.TEMP_MODS
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
        if icfg.lock_buffer and cap >= self.base_exptime():
            log.warning('[icg] FETCH 상한 %.1fs (fetch_timeout=%g%s) 가 프레임 하한 '
                        '%.3fs 이상이다 -- lock_buffer=true 에서 잠금이 주기를 넘으면 '
                        '못 받은 장이 덮인다 (DevNote 10.6).  하한 아래(예 1.0)로 '
                        '적을 것', cap, icfg.fetch_timeout,
                        ' -> 크기 유도' if icfg.fetch_timeout <= 0 else '',
                        self.base_exptime())

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
            # R2616+: flush 는 ACF 가 싣는다 -- 설정 메모리의 `FirstFlush=1` 상수가 모든
            # LOADPARAMS 에 실려 코어가 `FlushFrame` 한 번을 돌고 `FirstFlush--` 로
            # 소비한다.  호스트는 이 슬롯을 쓰지 않는다 (DevNote 11.33).  타이밍 셈(아래
            # 형태 검사)과 **무관하게** 여기서 판정한다 -- 시험의 최소 ACF 는 스크립트가
            # 없어 셈은 못 해도 flush 는 있어야 한다.  1 이 아니면 `arm_sequence` 가 GO 를
            # 거부한다 (그 판에 Exposures=n 을 걸면 첫 장이 flush 없이 저장된다 -- 11.31).
            self._flush_capable = acftiming.parameters(probe.config).get('FirstFlush') == 1
            if not self._flush_capable:
                log.error('guide ACF 의 FirstFlush 가 1 이 아니다 (%s) -- R2615 이하다. '
                          'GO 가 거부된다.  R2616+ 를 [icg] acf 에 걸 것 (규격 10.1-2)',
                          os.path.basename(path))
            # ⚠️ 이 셈법은 **guide 타이밍 스크립트 형태** 전용이다 (FrameShift ·
            # HorizontalShift(600) · PixelFirst · CLAMP).  science ACF 는 루틴
            # 배치가 달라(guide 의 `FrameShift` 자리가 `IntUnit`, `HorizontalSWShift(1200)`,
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
            # ⭐ `config` 를 함께 넘긴다 -- 트랜스퍼의 스크립트 리터럴
            # (`FrameShift(1033)`·`HorizontalShift(600)`)을 **이름으로** 읽는다.
            # 안 넘기면 `Lines` 파라미터와 상수 600 으로 물러난다 (11.35).
            t = acftiming.frame_timing(
                params, lines=params['Lines'], pixels=params['Pixels'],
                config=probe.config)
            # ⛔ `FlushLines` 는 **파생값인데 상수로 실려 있다** (규격 10.1-2).
            #    낳는 넷(`Pixels`·`Lines`·`AT`·`ST`)과 같은 파일에 있고 자동
            #    으로 안 따라가므로, 누가 하나만 고치면 **오류 없이 첫 저장
            #    프레임의 실적분만 틀린다.**  기동 때 한 번 대사해 그 조용한
            #    어긋남을 소리 나게 만든다.
            drift = acftiming.check_flush_lines(
                params, lines=params['Lines'], pixels=params['Pixels'],
                config=probe.config)
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
        # R2613+: flush 를 걸 수 있는 판인가 -- 형태 검사(`_SHAPE` 의 `Start:` flush 분기·
        # 통과했고 `FirstFlush`·`FlushLines` 가 있어야 한다.  없으면 `arm_sequence` 가
        # GO 를 거부한다 -- `Exposures=n` 으로 걸면 첫 장이 flush 없이 저장되니까.
        log.info('guide 프레임 타이밍 (ACF 계산, PROVISIONAL) -- %s · flush %s',
                 acftiming.describe(t),
                 ('%.4f s' % t['flush']) if t.get('flush') else '(없음 -- R2612 이하)')
        return t

    # -- 노출 주기 (규격 10.1절) --------------------------------------------

    def base_exptime(self) -> float:
        """**기본 노출시간** [s] -- `IntMS=0` 일 때의 주기 (`NoIntMS` + 트랜스퍼 + 독출).

        `EXPTIME = 기본 노출시간 + IntMS` 이고, 이보다 짧은 트랜스퍼 개시 간격은 만들
        수 없다 (규격 10.1-1).  구 이름 `frame_floor`/'하드웨어 하한' (운영자 개명
        2026-09-05).  설정 가능한 최소 노출시간 `exptime_min` 과 다른 물건이다.
        """
        if self.timing:
            return self.timing['floor']
        return self.icfg.exptime_min

    def intms_for(self, exptime_s: float) -> int:
        """요청 `EXPTIME` -> 시퀀서에 걸 `IntMS` [ms].

        `EXPTIME = 기본 노출시간 + IntMS` 이므로 `IntMS = EXPTIME - 기본 노출시간`
        이다.  **기본 노출시간보다 짧게 요청하면 0** -- 하드웨어가 만들 수 있는 가장
        짧은 주기가 된다 (운영자 확정 2026-08-31: "더 작게 설정해도 최소 노출시간으로").

        ⭐ 요청을 먼저 **설정 가능한 최소 노출시간**(`exptime_min`, 기본 1.3 s)으로
        접는다 (운영자 확정 2026-09-05: 기본 노출시간 위에 여유).  뺄셈의 기준은 그대로
        **기본 노출시간**이다 -- 여기에 최소 노출시간을 넣으면 `guideexp 2` 의 실현
        주기가 1.95 s 가 되어 헤더가 거짓이 된다.  최소 노출시간이 기본 노출시간보다
        작으면 기본 노출시간이 이긴다 (`max(0, ...)`).
        """
        want = max(exptime_s, float(self.icfg.exptime_min))
        return max(0, int(round((want - self.base_exptime()) * 1000.0)))

    def effective_exptime(self, exptime_s: float) -> float:
        """**실제로 실현되는** 독출 개시 간격 [s] -- 헤더 `EXPTIME` 은 이 값.

        요청값이 아니라 실현값을 싣는다 -- 규격 10.1-1 이 `EXPTIME` 을
        "연속 두 프레임 독출 개시 시각의 간격" 으로 정의하므로, 기본 노출시간에
        걸려 못 만든 주기를 그대로 적으면 카드가 거짓말이 된다.
        `IntMS` 가 ms 단위로 반올림되는 것까지 반영한다.

        ⭐ **카드 해상도는 1 ms** (규격 10.1-1, 2026-09-05) -- `IntMS` 의 분해능이자
        `DATE-OBS` 의 분해능이다.  기본 노출시간이 ms 경계에 없어서(1.2506283 s) 정수 요청은
        어느 것도 정확히 실현되지 않는데, 1.9996283 을 그대로 실으면 5.4 조건부 형
        규칙으로 카드가 실수형이 된다.  ms 로 반올림하면 `guideexp 2` -> `2`,
        최소 노출시간 미만 -> `1.3` (IntMS 49 + 1.2506).
        """
        return round(self.base_exptime() + self.intms_for(exptime_s) / 1000.0, 3)

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
        """flush 프레임 소요 [s] (`FlushFrame:` 블록) -- 규격 10.1-2 로 본 독출과 같다."""
        f = self.timing.get('flush') if self.timing else None
        return f if f is not None else self.base_exptime()

    # -- 연속 노출 (시퀀서 pacing) -------------------------------------------

    async def arm_sequence(self, frames: int, intms: int, *,
                           suffix: str = '', queue: bool = True):  # noqa: ANN201
        """`Exposures=frames` 를 **한 LOADPARAMS 로** 걸고 첫 표를 돌려준다.

        R2613+ (규격 10.1-2·3): `go n` = flush 1회 + 독출 n회 · n장 저장.  flush 는 ACF
        가 싣는다 -- R2616+ 는 설정 메모리의 `FirstFlush=1` 상수가 LOADPARAMS 마다 RAM
        에 실려 코어가 `FlushFrame` 한 번을 돌고 `FirstFlush--` 로 소비한다 (호스트가
        쓰는 플래그가 없다, DevNote 11.33).  코어가 IntUnit 없이 곧바로 FrameShift
        하므로 **그 순간이 첫 저장 프레임의 DATE-OBS** 다 -- 표의 `armed_utc` 가 그
        근사값이다.  이후 프레임은 `next_ticket()` 이 표만 잇는다 (DevNote 9.12).

        ⛔ ACF 의 `FirstFlush` 가 1 이 아니면(R2615 이하) **GO 를 거부한다** -- 그 판에
        `Exposures=n` 을 걸면 첫 장이 flush 없이 저장된다 (11.31 must_fix).
        """
        if not getattr(self, '_flush_capable', False):
            raise GuideBackendError(
                'guide ACF does not carry FirstFlush=1 (R2615 or older) -- '
                'load R2616+ or fix [icg] acf (spec 10.1-2)')
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

    # -- flush · 전원 · 바이패스 (운영자 2026-09-05) ---------------------------

    async def flush_ccd(self) -> None:
        """`CCDFLUSH` -- 유휴 CCD 를 `FlushFrame` 한 바퀴로 비운다 (프레임 없음)."""
        try:
            await self.ctrl.flush_now(reset=False)
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError('CCD flush failed: %s' % exc) from exc

    async def abort_flush(self) -> None:
        """abort/EXPENABLE=0 경로 -- **진행 중 사이클을 RESETTIMING 으로 끊고** 곧바로
        flush 로 비운다 (운영자 2026-09-05: 적분을 마저 하지 않는다, 디지타이징도
        않는다).  프레임이 나오지 않으므로 부르는 쪽은 꼬리를 기다리지 말고
        `flush_duration()` 만큼 기다린 뒤 IDLE 로 간다."""
        try:
            await self.ctrl.flush_now(reset=True)
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError('abort flush failed: %s' % exc) from exc

    async def power_ccd(self, on: bool) -> None:
        try:
            if on:
                await self.ctrl.power_on()
            else:
                await self.ctrl.power_off()
        except (ArchonError, TimeoutError, OSError) as exc:
            raise GuideBackendError('CCD power %s failed: %s'
                                    % ('on' if on else 'off', exc)) from exc

    async def raw_command(self, text: str) -> str:
        try:
            return await self.ctrl.raw_command(text)
        except (TimeoutError, OSError) as exc:
            raise GuideBackendError('raw command failed: %s' % exc) from exc

    # -- 준비 ---------------------------------------------------------------

    #: ⭐ guide 의 **쉬는 상태** -- `(TRIGOUTLEVEL, TRIGOUTFORCE)` 의 설정 문면.
    #: guide 는 셔터가 없어(frame-transfer) 트리거 선을 노출마다 흔들 일이
    #: 없으므로 **우리가 붙들어 LOW 로 고정한다** (운영자 확정 2026-09-08).
    #: ⛔ `FORCE=0` 은 *"타이밍 스크립트가 몬다"* 라 선이 노출마다 흔들린다 --
    #: ACF 출고값이 바로 그것이라 **띄울 때마다 되돌려야** 한다.
    #: ⛔ **레벨도 함께 본다** -- `FORCE=1` 인데 `LEVEL=1` 이면 쉬는 상태에서
    #: 선이 **HIGH 로 붙들려 있다** (앞 세션이 `SHOPEN` 중에 죽은 경우).
    TRIGOUT_REST = ('0', '1')

    async def prepare(self) -> None:
        """접속·ACF·전원 -- 멱등.  실패는 그대로 올린다 (시퀀서가 통보)."""
        await self.ctrl.prepare()
        await self.ensure_trigger_resting()

    async def ensure_trigger_resting(self) -> None:
        """트리거 선을 **쉬는 상태로 되돌린다** -- 멱등.

        ⛔ 종전에는 `_trigger_forced` **래치**로 *"한 번만"* 세웠다.  그런데 그
        뒤에 누가 `TRIGOUTFORCE=0` 을 쓰면(`SHCLOSE` 가 실제로 그랬다 -- 벤치
        2026-09-08) 래치가 이미 서 있어 **재시작 전까지 안 돌아왔다.**
        ⭐ 래치 대신 **설정값을 보고** 어긋났을 때만 쓴다 -- 맞으면 왕복이 없어
        래치만큼 싸고, 어긋나면 스스로 낫는다.  ACF 를 새로 밀어 캐시가
        파일값(`0`)으로 돌아간 경우도 여기서 다시 잡힌다.
        ⚠️ 되읽기가 실패해도 **쓰기는 한다** -- 모르면 세워 두는 쪽이 안전하다.
        """
        try:
            held = await self.ctrl.trigger_state()
        except (ArchonError, TimeoutError, OSError) as exc:
            log.warning('guide: TRIGOUT 상태를 못 읽었다 (%s) -- 쉬는 상태로 '
                        '그냥 다시 쓴다', exc)
            held = ('?', '?')
        if held == self.TRIGOUT_REST:
            return
        # ⭐ **둘을 한 번에 적용한다** -- 따로 쓰면 `FORCE=1` 이 먼저 서는 찰나에
        # 옛 `LEVEL=1` 이 핀으로 나간다 (앞 세션이 SHOPEN 중에 죽은 경우).
        await self.ctrl.set_trigger(high=False, forced=True)
        log.info('guide: 트리거 선을 쉬는 상태로 둔다 -- TRIGOUTLEVEL=0 '
                 'TRIGOUTFORCE=1 (종전 LEVEL=%s FORCE=%s).  FORCE=0 이면 '
                 '타이밍 스크립트가 몰아 노출마다 흔들린다', *held)

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
            'cfg': self._cfg_name(),
        }
        return {'units': [unit]}

    def _cfg_name(self) -> str:
        """`CTRL1CFG` 값 -- **ini 가 이기고, 비면 적용 ACF 파일명**.

        규격 v1.12 5.5절(그리고 10.3절이 *"5.5절과 같은 규칙"* 이라 못박는다):
        *"INI 에 정의돼 있으면 그 값, 비어 있으면 적용 ACF 파일에서, 어느
        쪽이든 경로·폴더명과 확장자를 뗀 파일명만"*.

        ⛔ **종전에는 ini 를 안 읽고 늘 ACF 에서 파생했다** -- 그런데 이
        클래스의 docstring 과 배포 ini 주석은 이미 *"ini 가 이긴다"* 라고
        적고 있었다.  운영자가 손으로 넣은 값을 코드가 조용히 버리는
        상태였다 (2026-09-06 정정).  science 쪽 짝은
        `ics_archon/app.py:fill_controller_cfg_names()` 다.
        """
        ini = (getattr(self.cfg.controllers, 'ctrl1_cfg', '') or '').strip()
        if ini:
            return ini
        return cfg_name_from_acf(self.ctrl.acf_path or self.icfg.acf_path)

    def rdmode(self) -> str:
        """`RDMODE` -- **ini 로만** 정하고, 비면 `UNKNOWN` (규격 v1.12 5.5절).

        ⛔ **ACF 이름에서 유도하지 않는다** (운영자 확정 2026-09-06).  종전
        단계였던 `fast`/`comp`/`slow` 토큰 찾기는 현행 ACF 이름에 그 토큰이
        없어 **한 번도 성립한 적이 없는 죽은 경로**였다.
        ⚠️ `UNKNOWN` 은 문자열 sentinel `NC` 와 뜻이 다르다 -- `NC` 는 *"그
        자리가 없다"*, `UNKNOWN` 은 *"있는데 값을 모른다"* 이고 독출 모드는
        언제나 존재한다 (운영자 확정 2026-08-29, 규격 5.5절에 v1.12 등재).
        """
        return (self.cfg.controllers.rdmode or '').strip() or rawhdr.RDMODE

    async def shutdown(self) -> None:
        """전원을 시도했으면 끄고 **연결을 닫는다** -- science 와 같은 규칙.

        ⛔ **`close()` 가 빠져 있었다** (2026-09-09 벤치에서 드러났다).
        science(`ArchonBackend.shutdown`)는 `power_off()` 뒤에 `ctrl.close()`
        까지 하는데 guide 만 안 했다.  Archon 은 연결을 사실상 하나만 잡으므로,
        FIN 을 안 보내고 끝나면 **컨트롤러가 옛 연결을 계속 붙들고** 곧바로 한
        재실행이 `timed out` 으로 못 붙는다.  실제로 벤치에서 네 번 연속
        재기동이 그렇게 무너졌다 (`icg.20260909` 로그).
        ⚠️ **닫기는 `POWEROFF` 가 실패해도 한다** -- 그래서 `finally` 다.
        전원이 남는 것보다 연결이 남는 것이 다음 실행을 더 확실히 막는다.

        ⭐ **종료가 무엇을 했는지 로그에 남긴다** (같은 벤치에서 드러난 둘째
        결함).  종전에는 성공하면 아무 자취가 없어 *"`quit` 을 했는지 죽었는지"*
        를 로그로 구별할 수 없었다.
        """
        try:
            if self.ctrl.powered or self.ctrl.power_attempted:
                await self.ctrl.power_off()
                log.info('종료 -- POWEROFF 를 보냈다')
        except (ArchonError, TimeoutError, OSError) as exc:
            log.warning('종료 POWEROFF 실패 -- %s.  **전원이 남아 있을 수 '
                        '있다**', exc)
        finally:
            try:
                await self.ctrl.close()
                log.info('종료 -- 컨트롤러 연결을 닫았다')
            except (ArchonError, TimeoutError, OSError) as exc:
                log.warning('종료 -- 연결을 못 닫았다: %s.  ⚠️ 컨트롤러가 옛 '
                            '연결을 붙들면 **곧바로 한 재실행이 못 붙는다** '
                            '-- 그때는 컨트롤러를 리셋할 것', exc)


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

    def base_exptime(self) -> float:
        return self.icfg.exptime_min

    def trigger_to_transfer(self, intms: int = 0) -> float:
        return max(intms, 0) / 1000.0

    def trigger_to_frameshift(self, intms: int = 0) -> float:
        return max(intms, 0) / 1000.0

    def frameshift_to_done(self) -> float:
        # 대역은 `wait_frame` 이 scaled 로 자므로 되짚는 폭도 같은 축이어야 DATE-OBS 가
        # 단조다 (비스케일 2 s 를 빼면 뒤로 간다 -- test_guide_header_semantics).
        return self.cfg.scaled(self.base_exptime())

    def flush_duration(self) -> float:
        """대역의 flush 소요 -- 실기와 같이 본 독출(기본 노출시간)과 같은 길이로 흉내낸다."""
        return self.base_exptime()

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
            self.base_exptime() + max(self._intms, 0) / 1000.0)
        for pct in (50, 100):
            await asyncio.sleep(max(period, 0.0) / 2.0)
            yield pct

    async def discard_frame(self, ticket, *, release: bool = True) -> None:  # noqa: ANN001, ARG002
        return None

    def drop_pending(self, why: str) -> int:  # noqa: ARG002
        return 0

    # -- 연속 노출 대역 (실기와 같은 표면) ----------------------------------

    def intms_for(self, exptime_s: float) -> int:
        want = max(exptime_s, float(self.icfg.exptime_min))
        return max(0, int(round((want - self.base_exptime()) * 1000.0)))

    def effective_exptime(self, exptime_s: float) -> float:
        return round(self.base_exptime() + self.intms_for(exptime_s) / 1000.0, 3)

    async def arm_sequence(self, frames: int, intms: int, *,  # noqa: ARG002
                           suffix: str = '', queue: bool = True):  # noqa: ANN201, ARG002
        self._intms = intms
        self._flush_pending = True
        self._n += 1
        return _SimTicket(self._n)

    async def next_ticket(self, after, intms: int, *,  # noqa: ANN001, ARG002
                          suffix: str = '', queue: bool = True):  # noqa: ANN201, ARG002
        self._intms = intms
        self._n += 1
        return _SimTicket(self._n)

    async def stop_sequence(self) -> None:
        return None

    async def flush_ccd(self) -> None:
        await asyncio.sleep(self.cfg.scaled(self.flush_duration()))

    async def abort_flush(self) -> None:
        # 실기의 abort_flush 는 WCONFIG ack 직후 돌아오고 **시퀀서**가 flush_duration 을
        # 기다린다 -- 대역도 같은 모양이어야 한다 (여기서 자면 두 번 기다린다).
        self._flush_pending = False

    async def power_ccd(self, on: bool) -> None:  # noqa: ARG002
        return None

    async def raw_command(self, text: str) -> str:
        return 'SIM (no controller): %s' % ' '.join(text.split())

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
        # `CTRL1CFG` -- ini 가 이기고 비면 적용 ACF 파일명 (규격 5.5절).
        ini = (getattr(self.cfg.controllers, 'ctrl1_cfg', '') or '').strip()
        return {'units': [{'id': '', 'sn': '',
                           'cfg': ini or cfg_name_from_acf(
                               self.icfg.acf_path)}]}

    def rdmode(self) -> str:
        return (self.cfg.controllers.rdmode or '').strip() or rawhdr.RDMODE

    async def shutdown(self) -> None:
        return None

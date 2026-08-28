#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`DetectorBackend` 의 Archon 구현 -- **`ics_sim` 과 실기가 맞물리는 자리.**

계약은 `ics_sim/ics_sim/hardware/base.py` (D-012) 이고, 참고 구현은 같은
폴더의 `sim.py` 다.  시퀀서·명령 처리부·메시지 규약은 **한 줄도 고치지 않는다**
-- 이 파일이 채워지면 `[hardware] backend = archon` 으로 전환된다.

## 계약과 실기의 어긋남 셋 -- 여기서 흡수한다

계약은 CCD 단위로 말하고 Archon 은 컨트롤러 단위로 움직인다.  그 차이를 이
클래스가 접는다.

1. **`initialize(ccd, suffix)` 는 CCD 4회, 컨트롤러는 2대.**  같은 컨트롤러의
   두 번째 호출은 걸러야 한다 -- `APPLYALL` 은 초 단위가 걸려 프레임마다
   되풀이할 수 없다.  suffix 로 "이 프레임은 준비됐다" 를 기억한다.
2. **`erase(ccd)` 는 master(K) 한 번만 온다.**  레거시가 master 에서만
   flushing 했기 때문인데(계약 docstring), **실기는 두 대 다 비워야 한다** --
   NT 를 안 비우면 그쪽 chip 에 앞 프레임의 잔상이 남는다.  그래서 이 호출
   하나를 살아 있는 컨트롤러 전부에 퍼뜨린다.
3. **노출을 걸 자리가 계약에 없다.**  DARK/BIAS 는 시퀀서가 백엔드를 아예
   부르지 않고 카운트다운만 돈다 (`_integrate_dark`).  그래서 셔터 노출은
   `open_shutter()` 에서, DARK/BIAS 는 `readout()` 첫머리에서 노출을 건다 --
   근거와 한계는 `controller.py` 머리말에 적었다.

## 동기 접근자 셋 (`controller_info`/`controller_telemetry`/`sensors`)

시퀀서는 이 셋을 **동기 메서드로** 부른다 (`_backend_fact`).  소켓을 만질 수
없으므로 **`initialize()` 에서 떠 둔 스냅샷**을 읽는다.  labtest 도 같은 이유로
`STATUS` 를 노출 개시 전에 떴다 -- fetch 뒤에 물어보면 컨트롤러가 답하지 않을
때 다 읽어낸 노출을 잃는다.

계약대로 **예외를 던지지 않는다.**  헤더 생성은 저장 경로이지 노출 경로가
아니므로, 센서 한 채널을 못 읽은 것 때문에 프레임을 버리면 손해가 훨씬 크다.
못 읽은 것은 sentinel 로 헤더에 남는다 (raw spec 5.0절).

## ⚠️ 실기 미검증 (v0.0 -- 잠정)

`ics_archon/SMC_CLAUDE.md` 의 "미검증 자리" 표와 같다.  옮겨 온 제어 시퀀스는
검증된 것이지만 **아래는 이 파일에서 새로 쓴 코드**다:

* `PROVISIONAL` 로 표시한 자리 -- STATUS 필드 이름 · 독출 진행률 · 산출물 실물.
* `sensors()` 는 **원형이 아예 없다** (labtest 가 HK 를 읽지 않는다).
  빈 dict 를 돌려 sentinel 경로를 밟게 한다.
* 픽셀 배치 -- Archon 이 주는 X 순서가 raw spec 4.1절(chips[0] 이 X 낮은 쪽)과
  같다고 **가정**한다.  labtest 도 같은 가정이었고, 실물 확인이 필요하다.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time

from .. import _simpath

_simpath.ensure()

from ics_sim import rawpair                              # noqa: E402
from ics_sim.hardware.base import BackendError           # noqa: E402

from ..config import CTRLTAGS                            # noqa: E402
from . import fitswrite, parse                           # noqa: E402
from .controller import ArchonController                 # noqa: E402
from .protocol import ArchonError                        # noqa: E402

log = logging.getLogger('ics_archon.hw')

#: 셔터를 강제로 닫을지 판단하는 여유 폭 [s].  남은 적분이 이보다 길 때만
#: "조기 종료" 로 본다 -- 정상 경로의 카운트다운 종료와 컨트롤러의 적분
#: 종료가 완전히 같은 순간일 수 없기 때문이다 (`close_shutter` 주석).
SHUTTER_FORCE_MARGIN = 1.0

def _frame_key(header) -> str:  # noqa: ANN001
    """헤더의 `EXPID` 에서 `<YYYYMMDD>.<NNNNNN>` 을 뽑는다.

    `EXPID` = 카운터가 **처음 배정한** 식별자 `<SITE>.<YYYYMMDD>.<NNNNNN>` 이고,
    그것이 `initialize()` 가 받은 suffix 와 같다 (D-016 번호 밀림은 그 뒤에
    결정된다).

    ⚠️ **v1.6(D-019)에서 구 `ORIGNAME` 을 대체했다.**  값에 컨트롤러 태그가
    없어졌지만 자리 수(`<SITE>.<날짜>.<번호>`)는 같으므로 뽑는 규칙은 그대로다 --
    오히려 `DETID` 필드가 없어 pair 양쪽이 같은 키를 준다.
    """
    from ics_sim import rawcards
    try:
        stem = rawcards.value_of(header, 'EXPID')
    except Exception:                       # noqa: BLE001
        return ''
    parts = str(stem or '').strip().split('.')
    return '%s.%s' % (parts[1], parts[2]) if len(parts) >= 3 else ''


def _frame_key_from_path(path: str) -> str:
    """`EXPID` 가 없을 때의 대체 -- 경로에서 뽑는다 (시험용 헤더 등)."""
    parts = os.path.basename(path).split('.')
    return '%s.%s' % (parts[1], parts[2]) if len(parts) >= 4 else ''


#: chip -> 컨트롤러 태그 (raw spec 2.1절 · `rawpair.CONTROLLERS`).
CHIP_TAG = {chip: tag for tag, chips in rawpair.CONTROLLERS for chip in chips}


class ArchonBackend:
    """STA Archon 두 대(과학 계통)를 `DetectorBackend` 로 보이게 한다."""

    name = 'archon'

    #: **항상 실파일을 쓴다** -- `[paths] write_fits` 와 무관하다.  그 플래그는
    #: 시뮬이 더미 FITS 를 만드는가라는 뜻이고, 그것을 D-016 선검사의 게이트로
    #: 쓰면 `write_fits=false` 로 실기를 돌릴 때 같은 이름을 조용히 덮어쓴다
    #: (`base.py` 의 이 속성 주석 참조).
    writes_files = True

    def __init__(self, cfg, acfg) -> None:  # noqa: ANN001
        self.cfg = cfg          # ics_sim.config.SimConfig
        self.acfg = acfg        # ics_archon.config.ArchonCfg
        self.tags = acfg.active_tags(tuple(cfg.node.ccds))
        self.ctrls = {tag: ArchonController(tag, acfg) for tag in self.tags}
        #: 태그 -> 준비를 마친 프레임의 suffix.  `initialize()` 중복 제거용.
        self._prepared: dict[str, str] = {}
        #: 태그 -> (실패한 프레임의 suffix, 통보 문구).  **실패도 기억한다** --
        #: 안 하면 같은 컨트롤러의 두 번째 chip 이 `prepare()` 를 다시 시도해
        #: `APPLYALL` 같은 무거운 명령이 두 번 나가고 오류도 두 번 나간다.
        #: 다음 프레임은 suffix 가 달라 자동으로 다시 시도한다.
        self._prep_failed: dict[str, tuple[str, str]] = {}
        self._prep_locks = {tag: asyncio.Lock() for tag in self.tags}
        self._led_ms = 0
        self._warned_sensors = False
        #: 태그 -> 이번 프레임의 이름.  `initialize()` 가 받아 두고 `trigger()`
        #: 와 `write_frame()` 이 저장 표를 맞추는 데 쓴다 (blocker B).
        self._suffix: dict[str, str] = {}
        #: 셔터를 열지 않는 노출의 적분 시간 [s].  **시퀀서가 알려 주는 자리가
        #: 계약에 없어서** `begin_exposure()` 훅으로 받는다 -- 없으면 0 이고,
        #: 그러면 labtest 와 달리 컨트롤러가 적분을 재지 않는다 (blocker C).
        self._dark_seconds = 0.0
        # **numpy 는 이 백엔드의 하드 의존이다** (엔디언 변환).  없으면 매
        # 프레임의 저장 단계에서 터지는데, 그때는 이미 fetch 를 마친 뒤라
        # 읽어낸 노출을 버린다 -- 기동에서 알아야 한다.
        try:
            import numpy  # noqa: F401
        except ImportError as exc:      # pragma: no cover
            raise RuntimeError(
                'archon 백엔드는 numpy 가 필요하다 (FITS 저장형 변환) -- '
                'pip install numpy 후 다시 띄울 것') from exc
        log.info('archon 백엔드 -- 컨트롤러 %s, 선언 기하 %dx%d (%.1f MiB/파일)',
                 ', '.join(self.tags) or '없음', acfg.naxis1, acfg.naxis2,
                 acfg.frame_bytes / (1 << 20))

    # -- 내부 -------------------------------------------------------------

    def _tag_of(self, ccd: str) -> str:
        tag = CHIP_TAG.get(ccd.upper())
        if tag is None or tag not in self.ctrls:
            # **와이어로 나가는 문구는 ASCII 여야 한다.**  전송 계층이
            # `decode('ascii', 'replace')` 를 하므로(레거시 IMPv2 는 ASCII
            # 프로토콜이다) 한글은 `?` 로 바뀌어 관측자가 읽을 수 없다.
            # 그래서 **사실은 로그에, 통보는 ASCII 로** 나눈다.
            log.error('chip %r 를 담당하는 컨트롤러가 설정에 없다 -- [archon] '
                      'ctrl_*_host 와 [node] ccds 를 확인하라', ccd)
            raise BackendError(
                'No controller configured for chip %s' % ccd, ccd=ccd)
        return tag

    def _active(self) -> list[ArchonController]:
        return [self.ctrls[t] for t in self.tags]

    async def _all(self, coro_factory, what: str) -> None:  # noqa: ANN001
        """살아 있는 컨트롤러 전부에 같은 일을 시키고 **첫 실패를 올린다.**

        `return_exceptions=True` 로 모아 두는 것이 중요하다 -- 한 대가 실패했다고
        다른 대의 코루틴을 취소하면 그쪽 컨트롤러가 절반만 설정된 상태로 남는다.
        """
        results = await asyncio.gather(
            *(coro_factory(c) for c in self._active()), return_exceptions=True)
        for ctrl, res in zip(self._active(), results):
            if isinstance(res, BaseException):
                log.error('%s: %s 실패 -- %s', ctrl.tag, what, res)
        for res in results:
            if isinstance(res, BaseException):
                raise res

    # -- 준비 -------------------------------------------------------------

    async def initialize(self, ccd: str, suffix: str) -> None:
        """컨트롤러를 준비하고 헤더용 스냅샷을 떠 둔다.

        `suffix` 는 파일명 결정에 쓰지 않는다 -- **경로는 시퀀서가 정한다**
        (D-016 선검사를 이미 거친 값이 `write_frame(path=…)` 로 온다).  여기서는
        "이 프레임은 이미 준비했다" 는 표시로만 쓴다.
        """
        tag = self._tag_of(ccd)
        ctrl = self.ctrls[tag]
        async with self._prep_locks[tag]:
            if self._prepared.get(tag) == suffix:
                return          # 같은 프레임의 두 번째 chip -- 할 일 없다
            failed = self._prep_failed.get(tag)
            if failed is not None and failed[0] == suffix:
                raise BackendError(failed[1], ccd=ccd)
            self._suffix[tag] = suffix
            try:
                await ctrl.prepare()
                ctrl.release_current()
                # PROVISIONAL: STATUS 필드 이름(`TEMP_MODS`)은 실기 미검증이다.
                await ctrl.refresh_status()
            except (ArchonError, TimeoutError, OSError) as exc:
                log.error('%s: 준비 실패 -- %s', tag, exc)
                # 레거시와 같은 문구여야 한다 (base.py 의 BackendError docstring)
                msg = 'Failed to initialize one or more ICs'
                self._prep_failed[tag] = (suffix, msg)
                raise BackendError(msg, ccd=ccd) from exc
            self._prepared[tag] = suffix
            self._prep_failed.pop(tag, None)

    async def erase(self, ccd: str) -> None:
        """CCD flushing -- **살아 있는 컨트롤러 전부**를 비운다 (위 2번)."""
        if not self.acfg.full_flush_on_erase:
            log.info('[archon] full_flush_on_erase=false -- ERASE 를 건너뛴다')
            return
        try:
            await self._all(lambda c: c.flush(), 'flush')
        except (ArchonError, TimeoutError, OSError) as exc:
            # **국면은 ERASE 인데 문구는 "initialize" 다 -- 일부러 그렇다.**
            # OBSAgent 가 알아듣는 ICS 오류 문구는 둘뿐이고(`Failed to
            # initialize one or more ICs` · `Failed to Start acquisition on
            # one or more ICs`, DevNote 3장) 둘 다 `flag_icscheck` 를 세운다.
            # ERASE 는 취득 개시 **전**의 준비 국면이므로 둘 중에서는 이쪽이
            # 맞고, 새 문구를 지어내면 OBSAgent 가 못 알아듣는다(규약).
            # 국면은 위 `_all()` 이 컨트롤러별로 로그에 남긴다.
            raise BackendError('Failed to initialize one or more ICs',
                               ccd=ccd) from exc

    # -- 셔터 / LED -------------------------------------------------------

    async def open_shutter(self, seconds: float) -> None:
        """셔터 노출을 건다.  **여기서 노출이 시작된다** (위 3번).

        Archon 은 셔터를 Trigger Out 이 INT 클록을 따르게 해서 구동한다
        (매뉴얼 p.15) -- `TRIGOUTFORCE=0` 이 그 모드이고, 적분 길이는 `IntMS`
        가 정한다.  반환은 즉시고 대기는 시퀀서가 한다 (계약 그대로).
        """
        ms = int(round(max(seconds, 0.0) * 1000))

        async def _go(c: ArchonController) -> None:
            await c.set_trigger_forced(not self.acfg.drives_shutter(c.tag))
            await c.trigger(ms, suffix=self._suffix.get(c.tag, ''))

        try:
            await self._all(_go, '노출 지시')
        except (ArchonError, TimeoutError, OSError) as exc:
            raise BackendError(
                'Failed to Start acquisition on one or more ICs') from exc

    async def close_shutter(self) -> None:
        """셔터를 닫는다.  **정상 경로에서는 할 일이 없다.**

        적분 길이는 컨트롤러가 재므로, 카운트다운이 끝난 시점에는 이미 닫혀
        있다.  실제로 뭔가 하는 것은 **조기 종료**(STOP · SHCLOSE)뿐이고, 그때
        할 수 있는 것은 `TRIGOUTFORCE=1` 로 트리거 라인을 강제해 **빛을 끊는
        것**이다 -- 적분 자체는 남은 시간을 다 센다 (`controller.py` 머리말).

        ⚠️ `APPLYSYSTEM` 을 적분 중에 보내는 것이 안전한지는 **실기 확인
        항목**이다.  그래서 "아직 적분 중" 일 때만 보낸다 -- 정상 경로에서
        독출 중에 시스템 설정을 건드리지 않게 한다.
        """
        # **여유 폭을 둔다.**  `int_until` 은 `trigger()` 시점 + `IntMS` 이고
        # 그 trigger 는 `open_shutter()` 안에서 카운트다운 시작보다 조금 뒤에
        # 걸린다(WCONFIG 3회 + APPLYSYSTEM + LOADPARAMS).  그래서 정상 경로의
        # 카운트다운이 끝난 순간에도 `integrating` 이 몇 백 ms 동안 참이다 --
        # 여유가 없으면 **매 노출마다** 독출 시작 무렵에 `APPLYSYSTEM` 을 보내게
        # 되고, 그것이 안전한지는 실기 확인 항목이다.
        remain = [(c, c.integration_left) for c in self._active()]
        still = [c for c, left in remain if left > SHUTTER_FORCE_MARGIN]
        if not still:
            return
        log.warning('남은 적분 %s초 -- 조기 폐쇄로 본다',
                    ', '.join('%s:%.1f' % (c.tag, left)
                              for c, left in remain))
        log.warning('적분 중에 셔터 폐쇄 지시가 왔다 (STOP/SHCLOSE) -- '
                    'TRIGOUTFORCE=1 로 빛을 끊는다.  적분은 남은 시간을 다 세고 '
                    '끝나므로 EXPTIME 은 요청값이다')
        for c in still:
            try:
                await c.set_trigger_forced(True)
            except (ArchonError, TimeoutError, OSError) as exc:
                log.error('%s: 셔터 강제 폐쇄 실패 -- %s', c.tag, exc)

    async def begin_exposure(self, seconds: float,
                             opens_shutter: bool) -> None:
        """노출 개시 통보 -- **셔터를 열지 않는 노출의 적분 시간을 받는 자리.**

        계약(`base.py`)에는 노출 개시 훅이 없었다.  셔터 노출은 시퀀서가
        `open_shutter(seconds)` 로 알려 주지만 **DARK/BIAS 는 백엔드를 아예
        부르지 않는다**(`sequencer._integrate_dark`) -- 그래서 v0.0 은 독출
        시점에 `IntMS=0` 으로 찍었고, 적분을 **호스트의 카운트다운**이 재게 됐다.

        그것이 labtest 와 갈리는 자리였다: labtest 는 DARK 에도
        `SetConfig(PARAMETER2, 'IntMS=<적분시간>')` 를 넣어 **컨트롤러가** 적분을
        잰다.  호스트가 재면 `time_scale`·이벤트 루프 지연·`erase` 소요가 다
        섞여 들어가고, 헤더 `EXPTIME` 은 요청값이라 **조용히 어긋난다**
        (2026-08-24 검토에서 확정한 blocker).

        시퀀서가 이 메서드를 갖고 있으면 부른다(`getattr`) -- 없는 백엔드는
        종전대로 돈다.
        """
        self._dark_seconds = 0.0 if opens_shutter else max(seconds, 0.0)

    async def flash_led(self, milliseconds: int) -> None:
        """점검용 LED 프로젝터 (`FLASHNOW`).

        ⚠️ **아직 배선이 없다.**  실험실은 LED 를 셔터 트리거 라인에 물려
        노출 내내 켰으므로(`LEDFLASH` = 노출시간) 독립 점등 경로가 없다.
        실기 LED 프로젝터가 어느 선에 붙는지 확정되기 전에 트리거를 임의로
        흔들면 셔터가 열린다 -- 그래서 **하드웨어를 만지지 않고** 값만
        기억한다.  헤더 `LEDFLASH` 는 명령이 넣은 값이라 영향이 없다.
        """
        self._led_ms = int(milliseconds)
        log.warning('archon 백엔드에는 LED 프로젝터 배선이 아직 없다 -- '
                    'FLASHNOW %d ms 를 기록만 하고 하드웨어는 만지지 않는다',
                    self._led_ms)

    # -- readout ----------------------------------------------------------

    async def readout(self, ccd: str):  # noqa: ANN201
        """독출 진행률을 yield 한다.  마지막에 `pctread_final`.

        **계약의 기본 경로다.**  `readout_events()` 를 쓰지 않는 시퀀서(구판)
        에서도 그대로 돌아야 하므로, 사건 흐름에서 진행률만 걸러 낸다.
        """
        final = self.cfg.readout.pctread_final
        async for kind, value in self._readout_stream(ccd):
            if kind == 'progress' and int(value) < final:
                yield int(value)
        yield final

    def readout_events(self, ccd: str):  # noqa: ANN201
        """독출을 사건으로 흘려보낸다 (`base.py` 의 선택 훅).

        `('progress', pct)` 는 master 의 진행률이고, `('frame', ctrltag)` 는
        **그 컨트롤러의 프레임이 완료됐다**는 뜻이다 -- 완료 순서 그대로
        나온다.  시퀀서가 `[readout] acq_per_frame` 을 보고 프레임별로
        `Acquisition Complete.` 를 낼지 정한다 (기본은 꺼짐 = 종전대로 4개를
        같은 틱에).
        """
        return self._readout_stream(ccd)

    async def _readout_stream(self, ccd: str):  # noqa: ANN201
        """독출 한 번 -- 노출 지시 · 진행률 · 컨트롤러별 완료.

        DARK/BIAS 는 시퀀서가 노출을 걸어 달라고 하지 않으므로(위 3번) 여기서
        건다 -- 적분은 `erase` 이후의 축적이고, `IntMS=0` 으로 곧바로 읽어낸다.

        PROVISIONAL: 진행률은 `FRAME` 의 `BUFnLINES`/`BUFnHEIGHT` 다 (매뉴얼
        p.50).  필드는 매뉴얼로 확인했지만 **실기 값의 거동**(선형인지, 독출
        시작 전에 0 으로 머무는 구간이 있는지)은 미검증이다.
        """
        master = self.ctrls[self._tag_of(ccd)]
        pending = [c for c in self._active() if not c.triggered]
        if pending:
            log.info('셔터를 열지 않는 노출 -- 독출 시점에 IntMS=0 으로 건다 '
                     '(%s)', ', '.join(c.tag for c in pending))
            # **적분 시간을 컨트롤러에 넘긴다** (blocker C).  `begin_exposure`
            # 로 받아 둔 값이고, 훅이 안 불렸으면 0 이다 -- 그때는 v0.0 과 같은
            # 거동(호스트가 적분을 잼)이고 경고를 남긴다.
            ms = int(round(self._dark_seconds * 1000))
            if ms <= 0 and self._dark_seconds == 0.0:
                log.warning('셔터를 열지 않는 노출인데 적분 시간을 못 받았다 -- '
                            'IntMS=0 으로 곧바로 읽어낸다(호스트가 적분을 잰 '
                            '셈이다).  시퀀서에 begin_exposure 훅이 없다')
            try:
                for c in pending:
                    await c.set_trigger_forced(True)
                await asyncio.gather(*(
                    c.trigger(ms, suffix=self._suffix.get(c.tag, ''))
                    for c in pending))
            except (ArchonError, TimeoutError, OSError) as exc:
                raise BackendError('DMA WAIT TIMEOUT. EXPOSURES ABORTED.',
                                   ccd=ccd) from exc

        ticket = master.current_ticket
        if ticket is None:                          # pragma: no cover
            raise BackendError('No exposure was triggered on %s' % master.tag,
                               ccd=ccd)
        final = self.cfg.readout.pctread_final
        # **두 컨트롤러의 프레임을 함께 기다린다** (목 지시 2026-08-24).
        #
        # 종전에는 master 티켓만 폴링하고 곧바로 `final` 을 냈다.  그러면
        # 시퀀서가 `Acquisition Complete.` 를 내보낸 **뒤에야** 나머지 대의
        # 프레임이 확인되므로 -- NT 가 늦거나 죽어도 획득 완료가 먼저 나간다.
        # 시뮬에서는 CCD 4개가 다 소프트웨어라 "master 가 끝났으면 나머지도
        # 끝났다" 가 참이었지만, 실기는 컨트롤러가 **물리적으로 둘**이라 그
        # 전제가 깨진다 (DevNote 11.25).
        others = [c for c in self._active()
                  if c is not master and c.current_ticket is not None]
        waits = {asyncio.ensure_future(c.await_frame(c.current_ticket)): c.tag
                 for c in others}
        try:
            t0 = time.monotonic()
            async for pct in master.wait_frame(ticket):
                if pct < final:
                    yield 'progress', pct
            t_master = time.monotonic()
            yield 'frame', master.tag
            # **완료 순서 그대로 낸다.**  누가 먼저 끝나는지가 곧 시차이고,
            # 그 값이 `acq_per_frame` 기본값을 정할 근거다.
            while waits:
                done, _ = await asyncio.wait(
                    waits, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    tag = waits.pop(task)
                    exc = task.exception()
                    if exc is not None:
                        log.error('%s: 프레임을 확인하지 못했다 -- %s', tag, exc)
                        raise exc
                    log.info('%s: 프레임 완료 (master %s 뒤 %.2f초)',
                             tag, master.tag, time.monotonic() - t_master)
                    yield 'frame', tag
            log.info('독출 완료 -- master %s %.1f초', master.tag,
                     t_master - t0)
        except (ArchonError, TimeoutError, OSError) as exc:
            # 레거시가 이 상황에 낸 문구를 그대로 쓴다 (base.py docstring):
            #   G.IC>ABC ERROR: GO  DMA WAIT TIMEOUT. EXPOSURES ABORTED.
            raise BackendError('DMA WAIT TIMEOUT. EXPOSURES ABORTED.',
                               ccd=ccd) from exc
        finally:
            # master 가 실패하면 나머지 대의 폴링이 영원히 남는다 -- 다음
            # 노출의 `readout()` 이 같은 티켓을 다시 기다리면 두 태스크가 같은
            # 소켓을 두고 겹친다.
            for task in waits:
                if not task.done():
                    task.cancel()
            # **여기서 "진행 중" 표시를 내린다.**  안 내리면 다음 프레임의
            # `readout()` 이 "이미 걸렸다" 고 보고 노출을 안 건다.  저장
            # 대기열은 그대로 남아 각 컨트롤러의 `write_frame()` 이 가져간다.
            for c in self._active():
                c.release_current()

    async def fetch_image(self, ccd: str):  # noqa: ANN201
        """chip 하나분 픽셀 (진단·도구용).  시퀀서는 부르지 않는다.

        저장 경로는 `write_frame()` 이고 그쪽은 컨트롤러 1대 = 파일 1개다.
        여기서는 그 프레임에서 이 chip 의 절반만 잘라 돌려준다.
        """
        import numpy as np
        tag = self._tag_of(ccd)
        ctrl = self.ctrls[tag]
        ticket = ctrl.take_ticket(self._suffix.get(tag, ''))
        if ticket is None:
            raise BackendError('No pending frame for %s' % tag, ccd=ccd)
        fs = await ctrl.await_frame(ticket)
        raw = await ctrl.fetch(fs, self.acfg.frame_bytes)
        arr = np.frombuffer(bytes(raw), dtype='<u2').reshape(
            self.acfg.naxis2, self.acfg.naxis1)
        chips = dict(rawpair.CONTROLLERS)[tag]
        half = self.acfg.naxis1 // 2
        lo = chips.index(ccd.upper()) == 0
        return arr[:, :half] if lo else arr[:, half:]

    # -- 저장 -------------------------------------------------------------

    async def write_frame(self, controller: str, chips: tuple[str, ...],
                          path: str, header) -> int:  # noqa: ANN001
        """컨트롤러 1대분 프레임을 FITS **파일 하나**로 저장 (D-012).

        `path` 는 D-016 선검사를 거친 확정 경로이고 `header` 는 규격 5장 카드가
        이미 채워져 온다 -- **둘 다 여기서 바꾸지 않는다.**

        **픽셀 배치는 Archon 이 준 순서 그대로다.**  raw spec 4.1절은
        `chips[0]` 이 X 낮은 쪽이라고 정하고, 컨트롤러가 두 chip 의 32 tap 을
        한 프레임으로 내보내므로 그 순서가 이미 맞다고 **가정**한다.  labtest
        도 같은 가정이었다 -- 실물 확인 항목이고, 어긋나면 여기서 좌우를
        바꾸면 된다 (`CHMAP_*` 카드는 헤더 쪽이라 따로다).
        """
        if controller not in self.ctrls:
            raise BackendError('Controller %s is not configured' % controller)
        want = dict(rawpair.CONTROLLERS).get(controller)
        if want is not None and tuple(chips) != tuple(want):
            # 순서가 뒤집혀 오면 픽셀 좌우가 뒤바뀐 파일이 조용히 생긴다.
            log.error('%s 의 chip 순서가 규격과 다르다 -- 받은 %r, 규격 %r '
                      '(raw spec 4.1절: chips[0] 이 X 낮은 쪽)',
                      controller, tuple(chips), tuple(want))
            raise BackendError(
                'Chip order for %s does not match the spec' % controller)

        ctrl = self.ctrls[controller]
        # **내 프레임을 표로 집어 온다** (FIFO).  컨트롤러 상태를 다시 읽으면
        # 파이프라인된 다음 프레임의 것을 집는다 (`FrameTicket` docstring).
        # **`EXPID` 로 내 표를 집는다** (blocker B).
        #
        # ⚠️ `path`(= `FILENAME`)를 쓰면 안 된다.  D-016 이름 충돌로 번호가
        # 밀리면 `path` 는 **밀린 번호**인데 `initialize()` 가 받은 suffix 는
        # 카운터가 처음 배정한 번호다(밀림은 획득 뒤에 결정된다) -- 그러면 표를
        # 못 찾아 **그 프레임이 저장되지 않는다.**  실측으로 걸렸다.
        #
        # `EXPID` 가 바로 그 최초 배정분이므로(sequencer `orig_suffix`)
        # `initialize()` 가 받은 값과 일치한다 (D-019 -- 구 `ORIGNAME`).
        want = _frame_key(header) or _frame_key_from_path(path)
        ticket = ctrl.take_ticket(want)
        if ticket is None:
            log.error('%s: 프레임 %s 의 저장 표가 없다 -- 노출이 걸리지 '
                      '않았거나 이미 저장됐다', controller, want or '?')
            raise BackendError(
                'No pending frame for %s' % controller,
                ccd=chips[0] if chips else '')
        try:
            fs = await ctrl.await_frame(ticket)
            raw = await ctrl.fetch(fs, self.acfg.frame_bytes)
        except (ArchonError, TimeoutError, OSError) as exc:
            log.error('%s: 프레임을 받지 못했다 -- %s', controller, exc)
            raise BackendError(
                'Failed to fetch frame from %s' % controller,
                ccd=chips[0] if chips else '') from exc

        try:
            # **스레드로 내보낸다.**  344 MiB 의 엔디언 변환과 디스크 쓰기는
            # 둘 다 블로킹이고, 그 몇 초 동안 UDP 수신과 다른 컨트롤러의
            # 발신이 멈추면 DevNote 3.3 의 시간 창을 넘긴다 (시뮬이 이미 같은
            # 이유로 `to_thread` 를 쓴다 -- sim.py `write_frame`).
            rate = await asyncio.to_thread(
                fitswrite.write_frame, path, header, raw,
                naxis1=self.acfg.naxis1, naxis2=self.acfg.naxis2)
        except (OSError, ValueError, ImportError) as exc:
            # **`ImportError` 를 반드시 잡는다.**  `to_fits_data()` 가 numpy 를
            # 안에서 import 하는데, 그것이 새어 나가면 `_store` 태스크가
            # `BackendError` 가 아닌 예외로 죽고 아무도 회수하지 않는다 --
            # `Wrote` 0회 · 오류 통보 0회, 즉 **조용히 사라진다**
            # (DevNote 11.20 의 critical 과 같은 부류).
            # 통보는 ASCII 다 -- OS 오류 문구가 한국어 Windows 에서 한글로
            # 오므로(`[WinError 3] ...`) 그대로 실으면 와이어가 `?` 범벅이 된다.
            log.error('%s: FITS 저장 실패 -- %s', controller, exc)
            raise BackendError(
                'Failed to write FITS for %s' % controller,
                ccd=chips[0] if chips else '') from exc
        log.info('%s: %s 저장 (%d KB/sec)', controller, os.path.basename(path),
                 rate)
        return rate

    # -- FITS 헤더용 사실 (동기 -- 스냅샷을 읽는다) -----------------------

    def controller_info(self, controller: str) -> dict:
        """5.5절 컨트롤러 정체.  **두 대분을 색인 순서로** 돌려준다.

        `sn` 은 `SYSTEM` 의 `BACKPLANE_ID` (컨트롤러가 보고하는 유일한 개체
        식별자), `cfg` 는 **호스트가 관리하는** 적용 ACF 이름이다 -- 컨트롤러는
        ACF 이름을 보고하지 않는다 (매뉴얼 p.54).  `[controllers]` ini 가
        채워져 있으면 그쪽이 이긴다 (`rawhdr.controller_header`).

        **모르는 키는 아예 넣지 않는다** -- 빈 문자열을 넣으면 `'NC'` sentinel
        경로를 건너뛰고 빈 값이 헤더에 실린다.
        """
        units = []
        for tag in CTRLTAGS:
            ctrl = self.ctrls.get(tag)
            unit: dict[str, str] = {}
            if ctrl is not None:
                unit.update(parse.unit_identity(ctrl.system))
                if ctrl.acf_path:
                    unit['cfg'] = os.path.splitext(
                        os.path.basename(ctrl.acf_path))[0]
            units.append(unit)
        return {'units': tuple(units)}

    def controller_telemetry(self) -> list[dict]:
        """5.6절 `Cn_TEMP/VOLT/CURR` -- 색인 순서(1=MK, 2=NT) 두 대분.

        **`C1_*` 는 "내 컨트롤러" 가 아니라 컨트롤러 1 고정이다** (5.9절
        "반드시 동일") -- 그래서 자리를 태그로 정한다.  없는 컨트롤러 자리는
        빈 dict 이고, `rawhdr` 가 그것을 **자리 수만큼의** `'NC|NC|…'` 로
        만든다 (5.6.1절 "자리는 비우지 않는다" -- `'NC'` 한 토큰으로 내면
        자리 수가 1이 되어 읽는 쪽에 모듈 구성이 달라 보인다).

        PROVISIONAL -- 필드 이름·모듈 나열 순서는 실기 미검증이다
        (`parse.TEMP_MODS`).
        """
        out = []
        for tag in CTRLTAGS:
            ctrl = self.ctrls.get(tag)
            out.append(parse.telemetry_of(ctrl.status if ctrl else None))
        return out

    def sensors(self, controller: str, chips: tuple[str, ...]) -> dict:
        """5.6절 듀어·환경 HK.  **아직 원천이 없다 -- 빈 dict.**

        공급 3계통(ICG RTD · standalone RTD readout unit · Tapaculo)은 Archon
        이 아니라 별도 계통이고, labtest 는 그 어느 것도 읽지 않는다 -- 즉
        **옮겨올 원형이 없다.**  호출측이 sentinel 로 채우고 그 사실이 헤더에
        남는다 (raw spec 5.0절) -- `CCDTEMP='-999.99'` 가 그 표시다.

        붙일 때의 계약은 `base.py` 의 이 메서드 docstring 에 다 적혀 있다
        (키 이름 · 대표 센서 `ccdtemp` · 못 읽은 항목은 넣지 않기).
        """
        if not self._warned_sensors:
            self._warned_sensors = True
            log.warning('듀어·환경 HK 를 읽는 경로가 아직 없다 -- CCDTEMP 를 '
                        '비롯한 5.6절 카드가 sentinel 로 실린다.  공급 3계통 '
                        '연동이 남은 일이다 (base.py sensors() 참조)')
        return {}

    def status(self, ccd: str) -> dict:
        """`STATUS` 명령 응답에 쓸 값들.

        `datasource` 는 레거시 어휘(`ADC`/`CTC`/`SIM`)를 따른다 -- 실기 Archon
        은 AD 모듈로 읽으므로 `ADC` 다 (DevNote 6.4).

        **`synched` 는 살아 있는 스냅샷을 본다** (D5, 2026-08-28).  종전에는
        헤더용 `ctrl.status` 를 읽었는데 그것은 **첫 노출 전까지 비어 있어서**,
        관측자 화면에 4채널 전부 `-SYNCH` 로 보였다 (G5).  `commands.py` 가
        `ChannelState.synched` 기본값 `True` 를 이 반환값으로 덮으므로 침묵할
        수도 없다.  이제 순서가 셋이다:

        1. 감시가 뜬 `status_live` (기동 직후부터 있다)
        2. 없으면 노출 개시에 언 `status` (감시를 껐을 때)
        3. **둘 다 없으면 링크 상태** -- 아직 한 번도 못 물어본 것이므로
           "이상하다는 증거가 없다" 가 맞다.  여기서 `False` 를 내면 **모르는
           것을 고장이라고 말하는 것**이 된다.
        """
        try:
            ctrl = self.ctrls[self._tag_of(ccd)]
        except BackendError:
            return {'driving': 0, 'fibers': False, 'synched': False,
                    'datasource': 'ADC', 'shutter_open': False,
                    'led_ms': self._led_ms}
        return {
            'driving': 1 if ctrl.powered else 0,
            'fibers': ctrl.link.connected,
            'synched': self._synched(ctrl),
            'datasource': 'ADC',
            'shutter_open': ctrl.integrating,
            'led_ms': self._led_ms,
        }

    @staticmethod
    def _synched(ctrl: ArchonController) -> bool:
        """`+SYNCH`/`-SYNCH` 플래그의 값 (위 `status()` 의 3단계).

        ⚠️ **`POWERGOOD` 은 이 물음에 정확히 답하지 못한다.**  실기에서
        프레임이 한 장도 안 나오던 증상의 원인이 **`Sync In` 이 물려 상대
        컨트롤러가 클록을 잡고 있던 것**이었는데, 그때 `POWER=4` ·
        `POWERGOOD=1` 이었다 (labtest 2026-08-27 종결,
        `../../scr_labtest/README_labtest.md`).  `POWERGOOD` 은 **컨트롤러
        자기 전원만** 보고하고 외부 클록 의존을 보지 않는다.

        Archon `STATUS` 에 동기 여부를 직접 말하는 필드는 없다.  그래서 이
        플래그는 "전원 계통에 이상이 없다" 까지만 뜻하고, 진짜 동기 정지는
        **프레임이 안 나오는 것**으로 드러난다 -- 그 자리는
        `controller.wait_frame()` 의 시한과 진단 덤프가 맡는다.
        """
        live = ctrl.status_live or ctrl.status
        if not live:
            return ctrl.link.connected
        return parse.power_good(live)

    # -- 생명주기 (계약 밖 -- app.py 가 부른다) ---------------------------

    async def shutdown(self) -> None:
        """전원을 끄고 연결을 닫는다.

        **계약에는 없지만 실기에는 반드시 있어야 한다.**  전원을 켠 채로
        프로그램이 끝나는 것은 검출기 쪽 위험이다 (labtest 가 노출 루프를
        `try/finally` 로 감싼 것과 같은 이유 -- DevNote 11.22 (4)).
        """
        for ctrl in self._active():
            # **확인된 상태가 아니라 "시도한 적이 있나" 로 판단한다.**
            # `POWERON` 응답을 잃으면 컨트롤러는 켜졌는데 `powered` 는 False 로
            # 남는다 -- 그 조합에서 POWEROFF 를 건너뛰면 전원을 켠 채로 끝난다.
            if ctrl.powered or ctrl.power_attempted:
                await ctrl.power_off()
            await ctrl.close()

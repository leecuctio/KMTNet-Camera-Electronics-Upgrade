#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""배선 -- `ics_sim.IcsSim` 에 Archon 백엔드를 끼운다.

**`ics_sim` 의 배선을 그대로 물려받는다.**  9개 노드 수신 · 명령 처리 · 시퀀서 ·
텔레메트리 중계 · 콘솔은 전부 그쪽 것이고, 여기서 갈라지는 것은 넷뿐이다:

1. **백엔드** -- `ics_sim.hardware.register_backend()` 로 실기 구현을 넣는다.
   그 자리가 원래 확장점이고(`[hardware] backend = archon` 한 줄), 구현만
   이 패키지에 있다.
2. **`ICSBUILD`** -- `ics_archon` 자신의 버전·빌드일시로 바꾼다.  안 바꾸면
   `ics_sim` 의 값이 실려 **거짓 provenance** 가 된다 (`ics_sim/__init__.py`
   의 `build_id()` 경고).
3. **`RDMODE`** -- ini 가 비어 있으면 적용 ACF 이름에서 유도한다 (labtest 가
   하던 일).  컨트롤러는 ACF 이름을 보고하지 않으므로(매뉴얼 p.54) 호스트가
   아는 유일한 근거가 그 파일명이다.
4. **종료** -- 전원을 끄고 연결을 닫는다.  전원을 켠 채로 끝나는 것은 검출기
   쪽 위험이다.
5. **접속과 텔레메트리 감시** -- 기동에서 컨트롤러에 접속하고, 그 뒤에 컨트롤러
   마다 주기 감시 태스크를 띄운다 (층 1·2, `archon/monitor.py`).
   `IcsSim.spawn()` 을 쓰므로 `ics_sim` 은 무수정이다.  **한 컨트롤러의 접속자는
   이 프로세스 하나다** -- guide 는 `icg_archon` 이 같은 방식으로 맡는다.
"""

from __future__ import annotations

import asyncio
import logging
import os

from . import _simpath, build_id, config as acfg_mod

_simpath.ensure()

from ics_sim.app import IcsSim                            # noqa: E402
from ics_sim.hardware import register_backend             # noqa: E402

from .archon.backend import ArchonBackend                 # noqa: E402
from .archon.monitor import TelemetryMonitor              # noqa: E402
from .archon.protocol import ArchonError                  # noqa: E402

log = logging.getLogger('ics_archon.app')

#: ACF 경로에서 헤더 값을 뽑는 규칙 둘은 **`config.py` 에 함께 있다** --
#: `rdmode_from_acf()`(`RDMODE`) · `cfg_name_from_acf()`(`CTRLnCFG`).
#: 같은 입력에서 나오는 값들이라 한 곳에 두었고, `config._cross_checks()` 가
#: 둘의 어긋남을 기동에서 본다.
#: **둘의 자르기 규칙이 다르다**: `RDMODE` 는 토큰을 찾을 뿐이라 `splitext`
#: 로 충분하지만, `CTRLnCFG` 는 값 자체가 되므로 판 번호의 점을 먹으면 안 된다.
rdmode_from_acf = acfg_mod.rdmode_from_acf


def fill_controller_cfg_names(cfg, acfg) -> None:  # noqa: ANN001
    """`[controllers] ctrlN_cfg` 가 비었으면 **적용 ACF 경로에서** 채운다.

    raw spec v1.8 5.5절이 `CTRLnCFG` 를 *"폴더 경로와 확장자(`.acf`/`.cfg`)를
    뗀 이름"* 으로 못박았고, 그 이름의 유일한 근거가 `[archon] acf_mk`/`acf_nt`
    다 -- 컨트롤러는 적용 ACF 이름을 보고하지 않는다 (매뉴얼 p.54).

    **왜 파생인가** -- 종전에는 `[controllers] ctrlN_cfg` 와 `[archon]
    acf_mk`/`acf_nt` 가 같은 파일을 가리키는 **별개의 ini 키**여서 둘을 맞추는
    것이 사람 몫이었다.  벤치와 관측소가 각자 ini 를 적으므로(`CAMVER` 와 같은
    부류) 한쪽만 어긋나면 **그 사이트 자료만 영구히 다른 설정 이름**을 단다.

    **왜 덮지 않나** -- 원장이 `Source = ICS INI` 로 못박은 카드는 전부 ini 에서
    고칠 수 있어야 하고(운영자 지시 2026-08-22, `tests/test_ini_cards.py`),
    `[controllers]` 의 원칙도 "채워져 있으면 INI 가 이긴다" 다.  아래 `RDMODE`
    도 같은 규칙이라 한 블록 안의 우선순위가 하나로 유지된다.  대가로 남는
    "둘이 어긋난 채 배포" 는 **기동 경고**로 드러낸다
    (`config._cross_checks()`).  배포되는 `ics_archon.ini` 는 이 칸이 비어
    있으므로 실기에서는 늘 파생이 채운다.

    ⚠️ **`NC` 는 빈 값이 아니다** -- 운영자가 "그 컨트롤러는 없다" 고 적어 둔
    것이므로(규격 5.0절 sentinel) 파생이 덮지 않는다.

    ⚠️ **`ics_sim` 은 한 줄도 고치지 않는다** -- 이 함수가 `ics_sim` 의
    `ControllersCfg` 를 **미리 채워** 넣을 뿐이고, 그 아래 사슬
    (`overrides()` -> `sequencer` -> `rawhdr.controller_header()`)은 읽기만
    한다.
    """
    for tag in acfg_mod.CTRLTAGS:
        n = acfg.index_of(tag)
        field = 'ctrl%d_cfg' % n
        if str(getattr(cfg.controllers, field, '') or '').strip():
            continue                       # 손편집 값(`NC` 포함)이 이긴다
        derived = acfg_mod.cfg_name_from_acf(acfg.acf.get(tag, ''))
        if derived:
            setattr(cfg.controllers, field, derived)
            log.info('CTRL%dCFG 를 ACF 경로에서 파생했다 -- %s (%s)',
                     n, derived, acfg.acf.get(tag, ''))


class IcsArchon(IcsSim):
    """실기 ICS -- `ics_sim` 본체 + Archon 백엔드."""

    def __init__(self, cfg, acfg) -> None:  # noqa: ANN001
        # **`super().__init__()` 앞에 등록한다** -- 그 안에서 `make_backend()`
        # 가 불리므로, 늦으면 이 폴더의 스텁이 만들어진다.
        register_backend('archon', lambda c: ArchonBackend(c, acfg))
        if cfg.hardware.backend != 'archon':
            log.warning('[hardware] backend=%r 로 ics_archon 을 띄웠다 -- '
                        'Archon 컨트롤러를 만지지 않는다.  실기로 돌리려면 '
                        'archon 으로 두거나 --backend archon 을 주라',
                        cfg.hardware.backend)
        self.acfg = acfg
        super().__init__(cfg)

        # `ICSBUILD` -- 이 프로그램의 것으로.
        self.state.ics_build = build_id()

        #: 돌고 있는 텔레메트리 감시 (`start()` 가 띄우고 `stop()` 이 세운다).
        self._monitors: list[TelemetryMonitor] = []
        #: 그 태스크 -- 종료에서 **실제로 기다리려면** 참조가 필요하다.
        #: (`IcsSim` 도 참조를 들고 있지만 그쪽은 `super().stop()` 에서
        #: 취소할 뿐이라, 우리가 원하는 "먼저 곱게 세운다" 를 못 한다.)
        self._monitor_tasks: list = []

        # `CTRL1CFG`/`CTRL2CFG` -- ini 가 비었으면 적용 ACF 경로에서.
        fill_controller_cfg_names(cfg, acfg)

        # `RDMODE` -- ini 가 비었으면 ACF 이름에서.
        if not cfg.controllers.rdmode:
            for tag in ('MK', 'NT'):
                derived = rdmode_from_acf(acfg.acf.get(tag, ''))
                if derived:
                    cfg.controllers.rdmode = derived
                    log.info('RDMODE 를 ACF 이름에서 유도했다 -- %s (%s)',
                             derived, acfg.acf.get(tag, ''))
                    break

    async def start(self) -> None:
        # **archon 백엔드가 아니면 컨트롤러 배선을 검사하지도, 배너를 찍지도
        # 않는다.**  `--backend sim` 은 메시지 층만 돌려 보는 모드이므로 그
        # 경고가 다 무의미하고, 무의미한 경고는 사람이 경고를 무시하도록
        # 학습시킨다.
        if self.cfg.hardware.backend != 'archon':
            await super().start()
            return
        for note in acfg_mod.validate(self.acfg, tuple(self.cfg.node.ccds),
                                      self.cfg):
            log.warning('[archon]: %s', note)
        await super().start()
        self._log_archon_banner()
        # **접속을 먼저 연다 -- 감시는 그 뒤에 시작한다** (운영자 2026-08-28).
        # 한 컨트롤러의 접속자는 이 프로세스 하나다.
        await self._connect_controllers()
        self._start_monitors()

    async def stop(self) -> None:
        """종료 -- **백엔드를 먼저 내린다.**

        `super().stop()` 은 태스크를 취소하고 전송을 닫는다.  그 전에 전원을
        끄지 않으면 컨트롤러가 바이어스를 걸고 있는 채로 프로세스가 끝난다
        (labtest 가 노출 루프를 `try/finally` 로 감싼 것과 같은 이유 --
        DevNote 11.22 (4)).
        """
        # **감시를 가장 먼저 세운다** -- 아래 `_stop_monitors()` 참조.
        await self._stop_monitors()
        # **저장 중인 프레임을 먼저 지킨다.**  `super().stop()` 이 태스크를
        # 취소하고 `backend.shutdown()` 이 링크를 닫으므로, 그 전에 기다리지
        # 않으면 독출을 마친 프레임이 파일 없이 사라진다 -- 전원을 끄는 것보다
        # 앞이다 (전원은 몇 초 더 켜져 있어도 되지만 프레임은 다시 못 찍는다).
        drain = getattr(self.seq, 'drain_writers', None)
        if drain is not None:
            try:
                await drain(self.acfg.shutdown_drain)
            except Exception:                       # noqa: BLE001
                log.exception('저장 대기 중 예외 -- 프레임을 잃었을 수 있다')
        shutdown = getattr(self.backend, 'shutdown', None)
        if shutdown is not None:
            try:
                await shutdown()
            except Exception:                       # noqa: BLE001
                log.exception('백엔드 종료 중 예외 -- 유닛 전원 상태를 직접 '
                              '확인하라')
        await super().stop()

    async def _connect_controllers(self) -> None:
        """**기동에서 각 컨트롤러에 접속한다** (운영자 확정 2026-08-28).

        `ics_archon` 이 그 컨트롤러의 **유일한 접속자**다.  `icg_archon` 이
        guide 를 맡고, 한 컨트롤러에 여러 노드가 붙는 구성은 두지 않는다 --
        Rev F 백플레인은 동시 접속이 하나뿐이고(매뉴얼 p.15), Rev H(4접속)에서도
        같은 규칙을 쓴다.  **소유자가 하나면 "누가 이 값을 읽었나" 를 물을 일이
        없다.**

        그래서 접속을 여는 자리를 여기로 못박았다 -- 종전에는 첫 노출의
        `prepare()` 였고, 감시를 넣으면서 잠깐 **감시 태스크의 부수효과**가 됐다.
        둘 다 "접속이 언제 열리나" 를 코드 흐름에서 읽기 어렵게 만든다.

        **실패해도 기동을 막지 않는다.**  컨트롤러 전원이 나중에 들어오는 배치가
        실재하고, 여기서 죽으면 그 배치가 통째로 못 돈다.  감시가
        `monitor_interval` 마다 다시 시도하고(`monitor = false` 면 첫 노출의
        `prepare()` 가 시도한다), 못 붙은 사실은 아래 배너와 로그에 남는다.
        """
        for ctrl in self.backend._active():
            if ctrl.link.connected:
                continue
            try:
                await ctrl.connect()
            except (ArchonError, TimeoutError, OSError) as exc:
                log.warning('%s: 기동 접속 실패 (%s) -- 기동은 계속한다.  '
                            '컨트롤러 전원과 [archon] ctrl_%s_host 를 확인하라',
                            ctrl.tag, exc, ctrl.tag.lower())
                continue
            log.info('%s: 접속 %s:%d', ctrl.tag, ctrl.link.host, ctrl.link.port)

    def _start_monitors(self) -> None:
        """컨트롤러마다 텔레메트리 감시 태스크를 띄운다 (층 1·2).

        **`IcsSim.spawn()` 을 그대로 쓴다** -- `ics_sim` 은 한 줄도 안 고친다.
        그쪽이 태스크 참조를 들고 있다가 `stop()` 에서 취소하므로, 우리는 그보다
        **먼저** 멈춰 세우기만 하면 된다 (아래 `stop()`).

        ⚠️ **감시는 `ctrl.status_live` 만 갱신한다** -- 헤더용 `ctrl.status` 는
        노출 개시에 언 채로 남는다.  그 둘을 섞으면 `Cn_TEMP/VOLT/CURR` 의 뜻이
        "노출 개시 시점 값" 에서 "마지막 폴링 값" 으로 조용히 바뀐다.
        """
        if not self.acfg.monitor:
            log.info('[archon] monitor=false -- 텔레메트리 감시를 걸지 않는다')
            return
        ctrls = getattr(self.backend, 'ctrls', None)
        if not ctrls:
            return
        for tag in self.backend.tags:
            mon = TelemetryMonitor(ctrls[tag], self.acfg,
                                   expstatus=lambda: self.state.expstatus)
            self._monitors.append(mon)
            self._monitor_tasks.append(self.spawn(mon.run()))

    async def _stop_monitors(self) -> None:
        """감시를 **가장 먼저** 세운다 -- 종료 순서가 중요하다.

        `backend.shutdown()` 이 `POWEROFF` 를 내고 링크를 닫는데, 그 사이에
        감시가 `STATUS` 를 물면 종료 때마다 `poll_failed` 행이 남아 **진짜
        고장과 구별되지 않는다.**  그래서 전원을 끄기 전에 세운다.

        **끝날 때까지 기다린다** -- 세우라고 표시만 하고 넘어가면(`sleep(0)`)
        폴링 중이던 감시가 `POWEROFF`·`close()` 와 겹쳐 바로 그 헛 `poll_failed`
        를 남긴다.

        ⚠️ **다만 무한정 기다리지는 않는다.**  FETCH 가 락을 수 분 쥐고 있으면
        감시는 그 뒤에나 깨어난다 -- 그때까지 종료를 붙잡아 두면 전원 차단이
        늦어진다(검출기 쪽 위험).  상한을 넘기면 취소하는데, 그래도 마지막
        `stop` 행은 남는다 -- 감시의 `finally` 가 취소 경로에서도 그것을 적는다.
        """
        if not self._monitors:
            return
        for mon in self._monitors:
            mon.stop()
        tasks = [t for t in self._monitor_tasks if not t.done()]
        if tasks:
            _done, pending = await asyncio.wait(
                tasks, timeout=max(self.acfg.status_timeout, 1.0) + 1.0)
            for task in pending:
                log.warning('감시가 제때 멈추지 않았다 -- 취소한다 (FETCH 락에 '
                            '걸려 있을 수 있다)')
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        self._monitors.clear()
        self._monitor_tasks.clear()

    def _log_archon_banner(self) -> None:
        """컨트롤러 배선과 **미검증 자리**를 기동에 한 번 보여 준다.

        사이트 배너(`ics_sim`)와 같은 취지다 -- 자료 한 장 찍기 전에 사람 눈에
        띄게 한다.  v0.0 은 실기 왕복이 미검증이므로 그 사실 자체가 배너
        항목이다.
        """
        a = self.acfg
        tags = a.active_tags(tuple(self.cfg.node.ccds))
        rows = [
            ('컨트롤러', ', '.join('%s=%s:%d' % (t, a.hosts.get(t, '?'), a.port)
                                   for t in tags) or '없음'),
            ('ACF', ', '.join('%s=%s' % (t, os.path.basename(a.acf.get(t, '-')))
                              for t in tags) or '없음'),
            ('ACF 적용', 'APPLYALL 수행' if a.apply_acf
                          else '건너뜀 (줄 번호만 파싱해 대조)'),
            ('선언 기하', '%d x %d  (%.1f MiB/파일)'
                          % (a.naxis1, a.naxis2, a.frame_bytes / (1 << 20))),
            ('텔레메트리', 'STATUS 질의 켜짐' if a.telemetry
                            else '꺼짐 -- Cn_* 는 NC'),
            ('감시·기록', ('%.0f초 간격 -> %s' % (a.monitor_interval,
                                                 a.monitor_log))
                          if (a.monitor and a.telemetry) else '꺼짐'),
            ('셔터 트리거', a.shutter_ctrl),
            ('ERASE', '전체 독출 flush' if a.full_flush_on_erase else '건너뜀'),
            # **어느 `ics_sim` 사본이 돌고 있나.**  저장소 배치에는 형제 원천과
            # 내장본이 둘 다 있을 수 있어서, 어느 것을 골랐는지가 진단의 출발점
            # 이다 (독립 배포에서는 내장본이 나온다).
            ('ics_sim', _simpath.describe()),
        ]
        width = 74
        lines = ['=' * width,
                 ' Archon 배선 -- v0.0 은 실기 왕복이 미검증이다',
                 '-' * width]
        lines += [' %-14s%s' % (label, value) for label, value in rows]
        lines += [
            '-' * width,
            ' 미검증(잠정) 3자리 -- ics_archon/SMC_CLAUDE.md',
            '   1. STATUS 필드 이름·모듈 나열 순서 (Cn_TEMP 의 자리)',
            '   2. 독출 진행률·독출 시간 (BUFnLINES 의 거동, Wrote 25초 창)',
            '   3. 산출물 실물 (기하·픽셀 좌우 배치·DETID·DATE-OBS)',
            ' 원천 없음 -- 듀어·환경 HK(sensors) 는 sentinel 로 실린다',
            '=' * width,
        ]
        log.info('\n%s', '\n'.join(lines))

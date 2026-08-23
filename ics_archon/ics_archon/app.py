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
"""

from __future__ import annotations

import logging
import os

from . import _simpath, build_id, config as acfg_mod

_simpath.ensure()

from ics_sim.app import IcsSim                            # noqa: E402
from ics_sim.hardware import register_backend             # noqa: E402

from .archon.backend import ArchonBackend                 # noqa: E402

log = logging.getLogger('ics_archon.app')

#: ACF 이름에 들어 있는 독출 모드 토큰 -> FITS `RDMODE`.  labtest 의 유도
#: 규칙 그대로다 (`KMTNet_Sci_fast_med_U13.acf` -> `FAST`).
_RDMODE_TOKENS = ('fast', 'comp', 'slow')


def rdmode_from_acf(path: str) -> str:
    """ACF 파일명에서 `RDMODE` 를 유도한다.  못 알아보면 빈 문자열.

    빈 문자열을 돌려주는 것이 중요하다 -- 그러면 `rawhdr` 의 코드 기본값
    (`NORMAL`)이 실린다.  여기서 `'NORMAL'` 을 만들어 넣으면 "유도 실패" 와
    "정말 NORMAL" 이 구별되지 않는다.
    """
    name = os.path.splitext(os.path.basename(path or ''))[0].lower()
    for token in _RDMODE_TOKENS:
        if token in name:
            return token.upper()
    return ''


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

    async def stop(self) -> None:
        """종료 -- **백엔드를 먼저 내린다.**

        `super().stop()` 은 태스크를 취소하고 전송을 닫는다.  그 전에 전원을
        끄지 않으면 컨트롤러가 바이어스를 걸고 있는 채로 프로세스가 끝난다
        (labtest 가 노출 루프를 `try/finally` 로 감싼 것과 같은 이유 --
        DevNote 11.22 (4)).
        """
        shutdown = getattr(self.backend, 'shutdown', None)
        if shutdown is not None:
            try:
                await shutdown()
            except Exception:                       # noqa: BLE001
                log.exception('백엔드 종료 중 예외 -- 유닛 전원 상태를 직접 '
                              '확인하라')
        await super().stop()

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

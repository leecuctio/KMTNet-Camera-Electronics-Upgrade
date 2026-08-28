#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KMTNet ICS -- 실기(STA Archon) 취득 프로그램.

`ics_sim` 이 만든 층(시퀀서 · 명령 처리부 · OBSAgent 메시지 규약 · raw spec
헤더)을 **무개정으로** 쓰고, 그 아래 `DetectorBackend` 자리에 실제 Archon
컨트롤러 제어를 넣는다.  제어 코드의 원형은 실험실 취득 스크립트
(`../scr_labtest/archon_kmtnet_labtest_v1.3.bigbuf.py`, 1년 실사용으로 검증된
v1.0 계보)다.

    python -m ics_archon -c ics_archon.ini

설계 근거·판단 이력은 `../../ics_sim/DevNote.md` 11.23 절, 상태·미검증 자리는
`../SMC_CLAUDE.md` 다.
"""

from __future__ import annotations

from . import _simpath

_simpath.ensure()

from ics_sim import build_id as _sim_build_id     # noqa: E402

__version__ = '0.0.0'

#: **마지막 갱신 일시 (UTC).  손으로 적는다.**
#:
#: ⚠️ 소스를 고치면 이 값을 같이 고친다 -- 안 고치면 FITS `ICSBUILD` 가 옛
#: 일시를 주장하고, 헤더에서 소스 상태를 되짚는 목적이 무력해진다.  이유는
#: `ics_sim/__init__.py` 의 같은 상수 주석에 다 적혀 있다 (파일 mtime 을 쓰지
#: 않는 이유 포함).
__build_date__ = '2026-08-28T04:00Z'


def build_id() -> str:
    """FITS `ICSBUILD` 에 실을 값 -- `v<버전>:<빌드일시>`.

    `ics_sim.build_id()` 를 **두 상수를 다 넘겨** 재사용한다.  안 넘기면
    `ics_sim` 의 버전·일시가 실려 거짓 provenance 가 된다 (`ics_sim` 쪽
    docstring 의 경고).  어느 프로그램이 쓴 파일인지는 `DATASRC` 가 답하므로
    이름은 붙이지 않는다 (운영자 확정 2026-08-22).
    """
    return _sim_build_id(__version__, __build_date__)


__all__ = ['__version__', '__build_date__', 'build_id']

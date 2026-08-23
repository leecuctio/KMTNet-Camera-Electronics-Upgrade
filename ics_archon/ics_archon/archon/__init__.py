#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archon 계층 -- 프로토콜 · 응답 해석 · 제어 시퀀스 · 저장 · 백엔드.

    protocol.py   저수준 왕복 (텍스트/이진, 참조번호, 재동기)
    parse.py      SYSTEM/STATUS/FRAME 해석 (왕복 없음 -- 실기 없이 시험 가능)
    controller.py 컨트롤러 한 대의 제어 시퀀스 (asyncio 래핑)
    fitswrite.py  raw FITS pair 바이트 기록 (견본 v1.0 정본)
    backend.py    ics_sim `DetectorBackend` 구현

원형은 `ics_archon/archon_kmtnet_labtest_v1.1.bigbuf.py` 이고, 프로토콜·시퀀스의
정본 근거는 `__ref_archon_control/Archon_manual_20210223.pdf` 다.
"""

from __future__ import annotations

from .backend import ArchonBackend
from .protocol import ArchonError, ArchonLink

__all__ = ['ArchonBackend', 'ArchonError', 'ArchonLink']

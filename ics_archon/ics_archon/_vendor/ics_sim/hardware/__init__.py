#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detector backends.

`[hardware] backend` 설정으로 고른다:
    sim     -- 타이밍만 흉내내는 시뮬 (지금 쓰는 것)
    archon  -- 실제 STA Archon 컨트롤러 (다음 단계, 현재는 스텁)
"""

from __future__ import annotations

from .base import BackendError, DetectorBackend

#: 바깥 패키지가 넣은 백엔드 만들기 (`이름 -> cfg 를 받는 함수`).
#:
#: **`ics_archon` 이 이 자리를 쓴다.**  실기 구현은 `ics_archon/ics_archon/
#: archon/` 에 있고 이 폴더에 사본을 두지 않는다 -- 사본을 뜨면 raw spec 5장
#: 개정 때 어긋난 쪽을 놓친다.  그래서 여기에 등록만 받는다.
#:
#: 등록된 이름은 아래 내장 목록을 **이긴다** -- `archon` 이름으로 등록하면
#: 이 폴더의 스텁 대신 실기 구현이 쓰인다.
_REGISTERED: dict = {}


def register_backend(name, factory) -> None:  # noqa: ANN001
    """백엔드 만들기를 등록한다.  `make_backend()` 앞에 불러야 한다."""
    _REGISTERED[name] = factory


def make_backend(cfg):  # noqa: ANN001, ANN201
    """설정에 맞는 백엔드를 만든다."""
    name = cfg.hardware.backend
    if name in _REGISTERED:
        return _REGISTERED[name](cfg)
    if name == 'sim':
        from .sim import SimBackend
        return SimBackend(cfg)
    if name == 'archon':
        from .archon import ArchonBackend
        return ArchonBackend(cfg)
    raise ValueError(f'unknown backend: {name}')


__all__ = ['BackendError', 'DetectorBackend', 'make_backend',
           'register_backend']

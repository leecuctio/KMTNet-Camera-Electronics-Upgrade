#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detector backends.

`[hardware] backend` 설정으로 고른다:
    sim     -- 타이밍만 흉내내는 시뮬 (지금 쓰는 것)
    archon  -- 실제 STA Archon 컨트롤러 (다음 단계, 현재는 스텁)
"""

from __future__ import annotations

from .base import BackendError, DetectorBackend


def make_backend(cfg):  # noqa: ANN001, ANN201
    """설정에 맞는 백엔드를 만든다."""
    name = cfg.hardware.backend
    if name == 'sim':
        from .sim import SimBackend
        return SimBackend(cfg)
    if name == 'archon':
        from .archon import ArchonBackend
        return ArchonBackend(cfg)
    raise ValueError(f'unknown backend: {name}')


__all__ = ['BackendError', 'DetectorBackend', 'make_backend']

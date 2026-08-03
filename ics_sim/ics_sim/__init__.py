#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KMTNet ICS simulator.

레거시 ICS(ICIMACS/IMPv2.5)와 호환되는 메시지를 내는 카메라 통합제어 시뮬레이터.
바깥으로는 레거시와 같은 규약을, 안으로는 신규 통합 구조(ICS + K/M/T/N.IC +
K/M/T/N.CB = 9노드)를 따른다.  설계 근거와 실측 자료는 DevNote.md 참고.
"""

from __future__ import annotations

__version__ = '0.1.0'

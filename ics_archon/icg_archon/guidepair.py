#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide raw 이름·번호 -- pair 없는 단일 파일 (raw spec 9.2절).

`ics_sim.rawpair` 의 규칙을 그대로 쓰되 **경로가 하나**다:

* 파일명 문법·관측일(D-014)·번호 공간(D-018)·`FILENAME`/`EXPID`
  정체성(D-019)은 science 와 같다 -- `rawpair` 함수를 그대로 부른다.
* 충돌 선검사(D-016)만 guide 판이다 -- 후보 N 의 `…G.fits` **한 경로**만
  본다 (science 는 MK·NT 두 경로).
* 노출 번호 카운터는 science 와 **독립**이다 (9.2절 제안 -- OI-23 에서
  확정 대기).  `icg_archon.ini` 가 자기 `expnum` 파일을 가지므로
  (`resolve_expnum_file` 이 ini 이름을 따른다) 구조로 보장된다.
"""

from __future__ import annotations

import os

from ics_archon import _simpath

_simpath.ensure()

from ics_sim import rawpair  # noqa: E402

from .config import TAG      # noqa: E402

#: 재수출 -- 호출측이 rawpair 를 따로 안 열어도 되게.
NumberSpaceExhausted = rawpair.NumberSpaceExhausted
NUM_SPACE = rawpair.NUM_SPACE


def guide_stem(site_code: str, suffix: str) -> str:
    """`<SITE>.<YYYYMMDD>.<NNNNNN>.G` -- `FILENAME` 카드 값 (확장자 없음)."""
    return rawpair.name_stem(site_code, suffix, TAG)


def guide_path(data_dir: str, site_code: str, suffix: str) -> str:
    """디스크 경로 -- `<data_dir>/<SITE>.<suffix>.G.fits`."""
    return rawpair.physical_path(data_dir, site_code, suffix, TAG)


def exposure_id(site_code: str, suffix: str) -> str:
    """`EXPID` 값 -- science 와 같은 규칙 (`DETID` 필드 없음, D-019).

    guide 는 파일이 하나라 "짝을 잇는 키" 역할은 없지만 **충돌 신호·재저장
    필터** 역할은 그대로다 (9.2절 -- `FILENAME` 의 `DETID` 필드를 뗀 값과
    `EXPID` 의 불일치가 충돌 표시).
    """
    return rawpair.exposure_id(site_code, suffix)


def resolve_guide_number(data_dir: str, site_code: str, date_part: str,
                         number: int, *, check: bool = True) -> int:
    """쓸 노출 번호를 정한다 -- D-016 선검사의 guide 판 (경로 하나).

    규칙은 `rawpair.resolve_pair_number()` 와 같다: 점유 시 N+1,
    999999 -> 000000 되감음, 공간 한 바퀴 초과가 유일한 실패.
    """
    start = number % NUM_SPACE
    if not check:
        return start
    n = start
    for _ in range(NUM_SPACE):
        suffix = f'{date_part}.{n:06d}'
        if not os.path.exists(guide_path(data_dir, site_code, suffix)):
            return n
        n = (n + 1) % NUM_SPACE
    raise NumberSpaceExhausted(
        f'{site_code}.{date_part} 의 guide 번호 공간 {NUM_SPACE}개가 전부 '
        '점유됐다 -- 저장하지 않는다 (D-016)')

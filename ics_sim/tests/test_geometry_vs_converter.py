#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raw geometry 상수 ↔ converter 하드코딩 상수의 **코드-대-코드 대조**.

**왜 이 파일이 따로 있나.**  v1.3 은 geometry 선언 카드(`OSCNPATT`·`ROWORDR`
등)를 폐지하고 **4.3 포장 규범 조항**(문서)으로 이관했다 -- 배치를 헤더가
아니라 규격이 정한다.  그러면 취득 SW 와 converter 의 하드코딩이 갈라져도
헤더 대조로는 잡을 수 없다: amp 절반의 `DATASEC` 에 overscan 이, `BIASSEC` 에
하늘이 들어가고 **오류는 나지 않는다.**

우리 쪽 상시 방어가 이것이다: **converter 를 import 해서 우리 상수와 맞댄다**
(raw spec 4.3절이 이 시험을 준수 검증 수단으로 명시한다).  `mef_converter/`
는 읽기 전용이지만 import 는 된다 -- 어느 쪽이 바뀌어도 여기가 걸린다.

✅ X overscan 패턴(`RRRRLLLL`)은 **확정됐다** (raw spec v1.4, 2026-08-22 --
실제 획득 자료 육안 확인, **OI-15 종결**).  그래서 이 시험은 이제 "미확정
전제의 일관성" 이 아니라 **확정된 규격과 converter 하드코딩의 일치**를
지킨다 -- 어느 쪽이 그 확정에서 벗어나면 걸린다.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

from ics_sim import rawhdr

CONVERTER = (pathlib.Path(__file__).resolve().parents[2] / 'mef_converter'
             / 'kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py')


def _converter():
    """읽기 전용 converter 를 import 한다.  없으면 시험을 건너뛴다."""
    if not CONVERTER.exists():                      # pragma: no cover
        pytest.skip(f'converter 를 찾을 수 없다: {CONVERTER}')
    spec = importlib.util.spec_from_file_location('_ceu_converter', CONVERTER)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ImportError as exc:                      # pragma: no cover
        pytest.skip(f'converter import 실패 (의존성): {exc}')
    return module


def test_xosc_pattern_matches_the_converter_rule():
    """`XOSC_PATTERN` 이 converter 의 `is_bias_right()` 와 같아야 한다.

    `'RRRRLLLL'` 은 raw spec 4.1절이 **확정**한 값이다 (v1.4 -- 실제 획득
    자료 육안 확인, OI-15 종결).  converter 는 그 값을 카드로 읽지 않고 자기
    `is_bias_right(amp)` 로 같은 규칙을 하드코딩하므로, 둘이 어긋나도
    변환 쪽에서는 아무것도 잡히지 않는다 -- 그 대조가 이 시험이다.

        strip_id(amp)      = ((amp - 1) % 8) + 1      # amp 1..16 -> strip 1..8
        is_bias_right(amp) = 1<=amp<=4 or 9<=amp<=12
        amp 1..8 = TOP 단, 9..16 = BOT 단

    -> strip 1~4 = R, strip 5~8 = L, 두 단이 동일 -> `'RRRRLLLL'`
    """
    conv = _converter()
    top = ''.join('R' if conv.is_bias_right(a) else 'L' for a in range(1, 9))
    bot = ''.join('R' if conv.is_bias_right(a) else 'L' for a in range(9, 17))
    assert top == bot, ('TOP/BOT 단의 overscan 패턴이 갈렸다 -- 그러면 strip '
                        f'하나로 기술할 수 없다 (TOP={top} BOT={bot})')
    assert top == rawhdr.XOSC_PATTERN, (
        f'우리 전제 {rawhdr.XOSC_PATTERN!r} 가 converter 규칙 {top!r} 와 '
        '다르다 -- amp 절반의 DATASEC 에 overscan 이 들어간다')


def test_strip_numbering_increases_with_x_in_the_raw_frame():
    """포장 규범 조항의 X 오름차순 (raw spec 4.3절) -- converter 의 tile
    배치와 맞아야 한다.

    converter 는 `tile0 = base + (strip_id(amp) - 1) * RAW_XTILE` 로 놓으므로
    **raw 좌표계에서 strip 번호가 +X 로 증가**한다.  네 chip 이 같다 -- `base`
    만 다르다(M/N=0, K/T=9600).

    레거시 amp 헤더의 `CCDSEC` 는 M·T 와 K·N 이 서로 반대 방향인데, 그건
    **CCD 기준**이고 K·N 이 180° 회전 장착이라서다(부록 A 의 `A-TOP` 시사와
    같은 짝, OI-17).  raw 영상 좌표계에서는 네 chip 다 좌->우 증가가
    맞다 -- 4.3절 조항은 raw 좌표계를 기술한다.
    """
    conv = _converter()
    for chip in ('M', 'K', 'N', 'T'):
        starts = [conv.raw_x_sections(chip, a)[0][0] for a in range(1, 9)]
        assert starts == sorted(starts), (
            f'{chip}: strip 번호가 +X 로 증가하지 않는다 -- {starts}')


@pytest.mark.parametrize('name,ours', [
    ('RAW_NAXIS1', 'RAW_NAXIS1'), ('RAW_NAXIS2', 'RAW_NAXIS2'),
    ('RAW_XTILE', 'AMPNAX1'), ('AMP_DATA_COLS', 'IMAGEX'),
    ('OVERSCAN_X', 'OVRSCNX'),
])
def test_geometry_constants_agree_with_the_converter(name, ours):
    """숫자 상수도 converter 와 맞대 둔다.

    converter 는 `NAXIS1×NAXIS2` 만 검사하고 나머지는 자기 상수를 쓴다.
    어긋나면 픽셀을 엉뚱한 곳에서 잘라내면서 **오류는 나지 않는다.**
    """
    conv = _converter()
    theirs = getattr(conv, name, None)
    if theirs is None:                              # pragma: no cover
        pytest.skip(f'converter 에 {name} 이 없다 -- 이름이 바뀌었는지 확인할 것')
    assert theirs == getattr(rawhdr, ours), (
        f'{name}={theirs} 인데 우리 {ours}={getattr(rawhdr, ours)} 다')


def test_ccd_rows_agree_with_the_converter():
    """chip 1개 active row = 2 × `IMAGEY` (converter `CCD_ROWS`)."""
    conv = _converter()
    theirs = getattr(conv, 'CCD_ROWS', None)
    if theirs is None:                              # pragma: no cover
        pytest.skip('converter 에 CCD_ROWS 가 없다')
    assert theirs == 2 * rawhdr.IMAGEY


def test_size_identity_from_spec_24():
    """raw spec 2.4절 크기 등식 -- pair 픽셀 − amp 픽셀 = 중앙 overscan 블록."""
    pair_pixels = 2 * rawhdr.RAW_NAXIS1 * rawhdr.RAW_NAXIS2
    amp_pixels = 64 * rawhdr.AMPNAX1 * rawhdr.IMAGEY
    assert pair_pixels - amp_pixels == 2 * rawhdr.RAW_NAXIS1 * 168

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""규격 5.3절 geometry 선언 ↔ converter 하드코딩 상수의 대조.

**왜 이 파일이 따로 있나.** 규격 5.3절 서두가 이렇게 정한다:

> 4장의 배치를 **하드코딩 없이 읽을 수 있도록** 헤더가 스스로 기술한다.
> converter는 이 값과 자기 상수를 대조해 불일치를 잡아야 한다.

그런데 **converter 는 아직 대조하지 않는다** -- `OSCNPATT`·`STRIPDIR` 등을 읽지
않고 자기 함수(`is_bias_right()`·`strip_id()`)에 하드코딩된 규칙을 쓴다.
변경점 C-5/C-13 이 그 구멍이다.  그때까지 **선언과 하드코딩이 갈라져도 아무것도
잡지 못한다** -- 그러면 amp 절반의 `DATASEC` 에 overscan 이, `BIASSEC` 에 하늘이
들어가고 **오류는 나지 않는다.**

우리 쪽에서 할 수 있는 것이 이것이다: **converter 를 import 해서 우리 선언과
맞댄다.**  `mef_converter/` 는 읽기 전용이지만 import 는 된다.  이러면 어느
쪽이 바뀌어도 우리 시험이 걸린다.

> `check_geometry()` 는 이걸 못 잡는다 -- 그쪽은 숫자 불변식이고 `OSCNPATT` 는
> 문자열이다.
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


def test_oscnpatt_matches_the_converter_rule():
    """`OSCNPATT` 가 converter 의 `is_bias_right()` 와 같은 패턴이어야 한다.

    **이것이 `'RRRRLLLL'` 의 근거다.**  레거시 실측 헤더에는 이 정보가 없다 --
    레거시는 CCD당 amp 8개(strip당 1개, TOP/BOT 분할 없음)라 대응물 자체가 없다.
    신규 64-amp 배치에서 overscan 이 tile 의 어느 쪽인지는 converter 의
    `is_bias_right(amp)` 가 정하고, 우리 선언은 그것을 **기술**한 것이다.

        strip_id(amp)      = ((amp - 1) % 8) + 1      # amp 1..16 -> strip 1..8
        is_bias_right(amp) = 1<=amp<=4 or 9<=amp<=12
        amp 1..8 = TOP 단, 9..16 = BOT 단

    -> strip 1~4 = R, strip 5~8 = L, 두 단이 동일 -> `'RRRRLLLL'`
    """
    conv = _converter()
    top = ''.join('R' if conv.is_bias_right(a) else 'L' for a in range(1, 9))
    bot = ''.join('R' if conv.is_bias_right(a) else 'L' for a in range(9, 17))
    assert top == bot, ('TOP/BOT 단의 overscan 패턴이 갈렸다 -- 그러면 strip 하나로 '
                        f'기술할 수 없다 (TOP={top} BOT={bot})')
    assert top == rawhdr.OSCNPATT, (
        f'규격 선언 {rawhdr.OSCNPATT!r} 가 converter 규칙 {top!r} 와 다르다 -- '
        'amp 절반의 DATASEC 에 overscan 이 들어간다 (변경점 C-5/C-13)')


def test_strip_numbering_increases_with_x_in_the_raw_frame():
    """`STRIPDIR='+X'` 가 converter 의 tile 배치와 맞아야 한다.

    converter 는 `tile0 = base + (strip_id(amp) - 1) * RAW_XTILE` 로 놓으므로
    **raw 좌표계에서 strip 번호가 +X 로 증가**한다.  네 chip 이 같다 -- `base` 만
    다르다(M/N=0, K/T=9600).

    레거시 amp 헤더의 `CCDSEC` 는 M·T 와 K·N 이 서로 반대 방향인데, 그건 **CCD
    기준**이고 K·N 이 180° 회전 장착이라서다(운영자 확인).  raw 영상 좌표계에서는
    네 chip 다 좌->우 증가가 맞다 -- 규격 5.3절은 raw 좌표계를 기술한다.
    """
    conv = _converter()
    for chip in ('M', 'K', 'N', 'T'):
        starts = [conv.raw_x_sections(chip, a)[0][0] for a in range(1, 9)]
        assert starts == sorted(starts), (
            f'{chip}: strip 번호가 +X 로 증가하지 않는다 -- {starts}')


@pytest.mark.parametrize('name,ours', [
    ('RAW_NAXIS1', 'RAWNAX1'), ('RAW_NAXIS2', 'RAWNAX2'),
    ('RAW_XTILE', 'RAWXTILE'), ('AMP_DATA_COLS', 'AMPDATA'),
    ('OVERSCAN_X', 'OVERSCNX'), ('CCD_ROWS', 'CCDROWS'),
])
def test_geometry_constants_agree_with_the_converter(name, ours):
    """숫자 상수도 converter 와 맞대 둔다.

    converter 는 `NAXIS1×NAXIS2` 만 검사하고(규격 6.1절) 나머지는 자기 상수를
    쓴다.  어긋나면 픽셀을 엉뚱한 곳에서 잘라내면서 **오류는 나지 않는다.**
    """
    conv = _converter()
    theirs = getattr(conv, name, None)
    if theirs is None:                              # pragma: no cover
        pytest.skip(f'converter 에 {name} 이 없다 -- 이름이 바뀌었는지 확인할 것')
    assert theirs == getattr(rawhdr, ours), (
        f'{name}={theirs} 인데 우리 {ours}={getattr(rawhdr, ours)} 다')

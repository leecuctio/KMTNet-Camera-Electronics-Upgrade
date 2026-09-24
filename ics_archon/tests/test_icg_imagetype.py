# -*- coding: utf-8 -*-
"""guide 의 `IMAGETYP`·`EXPTIME` 규약 (운영자 확정 2026-09-15, OI-24 ② 종결).

* 어휘는 science 와 같다.  기본 `IMAGETYP` 은 **`OBJECT`**, 기동 때 `EXPTIME` 은 **2 s**
  (`[icg] exptime_default`).
* **`BIAS` = 최소 노출** -- `EXPTIME` 이 guide 의 최소(기본 노출시간 위의 `exptime_min` 실현값)로
  고정되고, `EXP`/`GUIEXP` 는 거부된다.  다른 국면으로 옮기면 다시 바꿀 수 있다.
  `IMAGETYPE` 조회도 그 값을 말한다 (기반의 `EXP=0` 이 아니다 -- 2026-09-23).
* 나머지 국면은 전부 같다 -- guide 엔 셔터 제어가 없어 `DARK`·`OBJECT`·`FLAT` 이 `EXPTIME` 을
  건드리지 않는다.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_icg_ops_commands import _drive, _about, make_cfgs   # noqa: E402


def _reply(sent, word):  # noqa: ANN001
    hits = [s for s in _about(sent, word) if 'DONE:' in s or 'ERROR:' in s]
    assert hits, (word, sent)
    return hits[-1]


def test_startup_defaults_are_object_and_two_seconds(tmp_path):  # noqa: ANN001
    app, sent = _drive(tmp_path, ['abc>ICG GUIEXP', 'abc>ICG STATUS'])
    assert app.state.imgtype == 'OBJECT'
    assert 'GuiExp=2 seconds' in _reply(sent, 'GUIEXP')
    _cfg, icfg = make_cfgs(tmp_path)
    assert icfg.exptime_default == 2.0


def test_bias_pins_exptime_to_the_minimum_and_refuses_changes(tmp_path):  # noqa: ANN001
    app, sent = _drive(tmp_path, [
        'abc>ICG GUIEXP 5',
        'abc>ICG BIAS',
        'abc>ICG EXP 3',            # 거부
        'abc>ICG GUIEXP 3',         # 거부
        'abc>ICG GUIEXP',           # 조회 -- 최소 노출
    ])
    minimum = app.guide.effective_exptime(0.0)          # 대역: exptime_min(1.3) 위 실현값
    assert app.state.imgtype == 'BIAS'
    assert app.state.exptime == minimum
    assert ('EXP=%g' % minimum) in _reply(sent, 'DONE: BIAS')
    assert 'ERROR: EXP Cannot change EXPTIME for ImgType=BIAS' in _reply(sent, 'ERROR: EXP')
    assert 'ERROR: GUIEXP Cannot change EXPTIME for ImgType=BIAS' in _reply(sent, 'ERROR: GUIEXP')
    assert ('GuiExp=%g seconds' % minimum) in [s for s in sent if 'DONE: GUIEXP GuiExp' in s][-1]


def test_the_imagetype_query_after_bias_says_the_minimum_not_zero(tmp_path):  # noqa: ANN001
    """⭐ `BIAS` 뒤 `IMAGETYPE` 조회도 **최소 노출**을 말한다 (2026-09-23).

    ⛔ 종전에는 기반(`ics_sim`)의 조회를 그대로 물려받아 `EXP=0` 이 나갔다 -- 기반은
    `effective_exptime`(BIAS 면 0)을 싣는데, guide 의 `BIAS` 는 최소 노출이라 같은 상태를
    두고 `BIAS` 응답·`GUIEXP` 조회·헤더와 말이 갈렸다.  세 별칭 모두 같고, 답의
    커맨드워드는 받은 그대로다.
    """
    app, sent = _drive(tmp_path, [
        'abc>ICG BIAS',
        'abc>ICG IMAGETYPE',
        'abc>ICG IMGTYP',
        'abc>ICG imagetype bias',   # 거부 -- 조회 전용 (상태를 안 바꾼다)
    ])
    minimum = app.guide.effective_exptime(0.0)
    assert minimum > 0
    bias = _reply(sent, 'DONE: BIAS')
    for word in ('IMAGETYPE', 'IMGTYP'):
        said = [s for s in sent if 'DONE: %s ' % word in s]
        assert said, (word, sent)
        assert said[-1].endswith('EXP=%g' % minimum), said[-1]
        # ⭐ BIAS 응답과 **같은 본문**이다 (`ImageType= ObjectName= EXP=`).
        assert said[-1].split('DONE: %s ' % word, 1)[1] == bias.split('DONE: BIAS ', 1)[1]
    assert 'ERROR: IMAGETYPE Query only' in _reply(sent, 'ERROR: IMAGETYPE')
    assert app.state.imgtype == 'BIAS' and app.state.exptime == minimum


def test_the_imagetype_query_outside_bias_is_the_parent_answer(tmp_path):  # noqa: ANN001
    """`BIAS` 가 아니면 `st.exptime` 과 `effective_exptime` 이 같다 -- 답이 부모와 같아야 한다."""
    app, sent = _drive(tmp_path, ['abc>ICG GUIEXP 4', 'abc>ICG DARK', 'abc>ICG IMAGETYP'])
    said = [s for s in sent if 'DONE: IMAGETYP ' in s]
    assert said and 'ImageType=DARK' in said[-1] and said[-1].endswith('EXP=4'), said
    assert app.state.effective_exptime == app.state.exptime == 4.0


def test_other_image_types_keep_exptime_and_release_the_bias_pin(tmp_path):  # noqa: ANN001
    app, sent = _drive(tmp_path, [
        'abc>ICG GUIEXP 4',
        'abc>ICG DARK', 'abc>ICG FLAT', 'abc>ICG OBJECT m31',
        'abc>ICG BIAS',
        'abc>ICG OBJECT',           # 핀 해제 -- 최소 노출은 그대로 남되 바꿀 수 있다
        'abc>ICG GUIEXP 3',
    ])
    dark = _reply(sent, 'DONE: DARK')
    assert 'EXP=4' in dark
    assert app.state.imgtype == 'OBJECT'
    assert app.state.exptime == 3.0
    assert 'GuiExp=3 seconds' in [s for s in sent if 'DONE: GUIEXP' in s][-1]

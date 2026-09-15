# -*- coding: utf-8 -*-
"""guide 의 `IMAGETYP`·`EXPTIME` 규약 (운영자 확정 2026-09-15, OI-24 ② 종결).

* 어휘는 science 와 같다.  기본 `IMAGETYP` 은 **`OBJECT`**, 기동 때 `EXPTIME` 은 **2 s**
  (`[icg] exptime_default`).
* **`BIAS` = 최소 노출** -- `EXPTIME` 이 guide 의 최소(기본 노출시간 위의 `exptime_min` 실현값)로
  고정되고, `EXP`/`GUIEXP` 는 거부된다.  다른 국면으로 옮기면 다시 바꿀 수 있다.
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

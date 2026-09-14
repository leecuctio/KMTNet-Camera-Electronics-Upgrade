# -*- coding: utf-8 -*-
"""`tools/trace_clock_states.py` 가 ACF 의 `STATEn\\MODm` 를 **여덟 채널 다** 읽는가.

⛔ 결함 (DevNote 11.85-(8), 2026-09-14 정정): 값이 따옴표로 싸여 있는데
(`",1,1,,1,1,…,CLAMP_HIGH,1,0"`) 정규식이 따옴표까지 먹어서 마지막 채널의 keep 이
`0"` 로 읽혔다 -- science 의 8번 채널 `D4`(MOD2/MOD10) · `CLAMP`(MOD3/MOD11) 가 어느
상태에서도 안 바뀌는 것으로 나왔고, 첫 채널 준위엔 `"` 가 붙었다.  세션 35 가 그 도구로
*"D4 는 한 번도 클록 안 된다"* 고 잘못 읽었다.

시험은 저장소 정본 science ACF 한 장(`acf/KMTC_SCI_101_STA0284_R2613_MK.acf`)으로
`load()` 만 부른다 -- 도구는 본편이 안 부르므로 이것이 유일한 그물이다.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import trace_clock_states as tcs  # noqa: E402

ACF = os.path.join(ROOT, 'acf', 'KMTC_SCI_101_STA0284_R2613_MK.acf')


@pytest.fixture(scope='module')
def loaded():
    assert os.path.exists(ACF), ACF
    return tcs.load(ACF)


def test_eighth_channel_labels_are_d4_and_clamp(loaded):
    labels = loaded[0]
    assert labels[('3', '8')] == 'CLAMP-A' and labels[('11', '8')] == 'CLAMP-B'
    assert labels[('2', '8')] == 'D4-A' and labels[('10', '8')] == 'D4-B'


def test_reset_state_sets_all_eight_channels_of_mod3(loaded):
    """`STATE0`(RESET) 은 MOD3 여덟 채널을 **전부** keep=0 으로 세운다 --
    8번(`CLAMP-A`)이 빠지면 따옴표를 또 먹은 것이다."""
    states = loaded[1]
    reset = states['RESET']
    chans = sorted(int(ch) for (mod, ch) in reset if mod == '3')
    assert chans == [1, 2, 3, 4, 5, 6, 7, 8], chans
    assert reset[('3', '8')] == 'CLAMP_HIGH'
    assert reset[('3', '1')] == 'S_HIGH', '첫 채널 준위에 따옴표가 붙으면 안 된다'


def test_clamp_state_touches_only_channel_eight(loaded):
    """`STATE8`(CLAMP) 은 MOD3 에서 8번 하나만 세운다 -- 종전엔 **아무것도 안 세우는**
    상태로 읽혔다(그래서 `CLAMP` 가 화면에서 사라졌다)."""
    states = loaded[1]
    clamp = {k: v for k, v in states['CLAMP'].items() if k[0] == '3'}
    assert clamp == {('3', '8'): 'CLAMP_HIGH'}, clamp


def test_no_level_carries_a_quote(loaded):
    states = loaded[1]
    bad = [(nm, k, v) for nm, eff in states.items() for k, v in eff.items()
           if '"' in v]
    assert not bad, bad[:5]

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`[archon]` 절의 참/거짓 낱말 -- 정본(`ics_sim.config.TRUE_WORDS`/`FALSE_WORDS`)과 같은가.

⭐ **이 파일이 있는 이유** (2026-09-23 검토): DevNote 11.74 가 참/거짓 낱말의
사본을 걷으면서 `ics_sim`·`icg_archon` 은 정본을 가리키게 했는데,
`ics_archon.config._bool` 만 리터럴 튜플(`true/yes/on/1`)을 따로 들고 있었다.
그래서 같은 `ics_archon.ini` 안에서 `enable`/`high` 를 `[behavior]` 는 받고
`[archon]` 은 **기동 거부**했다.  ⛔ 운영자 지시(2026-09-11): *"1/ON/TRUE/ENABLE/HIGH
는 모두 같은 의미로, 0/OFF/FALSE/DISABLE/LOW 는 모두 같은 의미로"*.

낱말 목록은 정본에서 끌어온다 -- 여기에 다시 적으면 그것이 또 하나의 사본이다.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ics_archon import _simpath  # noqa: E402,F401

from ics_sim import config as sim_config  # noqa: E402

from ics_archon import config as acfg_mod  # noqa: E402


def _load(tmp_path, word):  # noqa: ANN001, ANN202
    path = tmp_path / 'archon_bool.ini'
    path.write_text('[archon]\nlock_buffer = %s\n' % word, encoding='utf-8')
    return acfg_mod.load(str(path))


@pytest.mark.parametrize('word', sim_config.TRUE_WORDS)
def test_every_canonical_true_word_reads_true(tmp_path, word):  # noqa: ANN001
    assert _load(tmp_path, word).lock_buffer is True, word
    # 대소문자는 안 가린다
    assert _load(tmp_path, word.upper()).lock_buffer is True, word


@pytest.mark.parametrize('word', sim_config.FALSE_WORDS)
def test_every_canonical_false_word_reads_false(tmp_path, word):  # noqa: ANN001
    assert _load(tmp_path, word).lock_buffer is False, word
    assert _load(tmp_path, word.upper()).lock_buffer is False, word


def test_the_archon_section_points_at_the_canonical_table():
    """⛔ 사본이 아니라 **같은 객체**여야 한다 -- 넓이가 다시 갈리지 않게."""
    assert acfg_mod._TRUE_WORDS is sim_config.TRUE_WORDS    # noqa: SLF001
    assert acfg_mod._FALSE_WORDS is sim_config.FALSE_WORDS  # noqa: SLF001


def test_a_typo_still_refuses_to_start_and_names_the_vocabulary(tmp_path):  # noqa: ANN001
    """⛔ 모르는 낱말은 조용히 거짓이 아니라 기동 거부다 -- 무엇을 적을지 문면에 싣는다."""
    with pytest.raises(acfg_mod.ArchonConfigError) as err:
        _load(tmp_path, 'ture')
    text = str(err.value)
    assert '[archon] lock_buffer' in text, text
    assert 'enable' in text and 'disable' in text, text


def test_an_empty_value_keeps_the_default(tmp_path):  # noqa: ANN001
    default = acfg_mod.ArchonCfg().lock_buffer
    assert _load(tmp_path, '').lock_buffer is default

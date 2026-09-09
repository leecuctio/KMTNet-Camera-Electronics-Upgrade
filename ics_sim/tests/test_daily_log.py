#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`[logging] file` 이 폴더면 **날마다 갈아타는** 로그 파일.

운영자 지시 2026-09-09: *"icg 로그를 isis 로그처럼 `icg.yyyymmdd.log` 으로 매일
갱신하여 저장.  재실행해도 전에 파일 지우지 않고 같은 날짜 뒤에 덧붙이는 식으로."*
"""

import calendar
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ics_sim.__main__ import DailyFile, _log_handler  # noqa: E402


def _rec(msg, epoch):  # noqa: ANN001, ANN201
    r = logging.LogRecord('t', logging.INFO, __file__, 1, msg, None, None)
    r.created = epoch
    return r


def _epoch(y, m, d, hh, mm):  # noqa: ANN001, ANN201
    """**UTC** 기준 epoch -- 지역시로 만들면 시험이 기계 시간대를 탄다."""
    return calendar.timegm((y, m, d, hh, mm, 0, 0, 0, 0))


def test_a_folder_becomes_one_file_per_utc_day(tmp_path):
    """⭐ 폴더를 주면 `<이름>.<YYYYMMDD>.log` 이고 **날이 바뀌면 갈아탄다**."""
    h = DailyFile(str(tmp_path), 'icg')
    h.setFormatter(logging.Formatter('%(message)s'))
    h.emit(_rec('첫날', _epoch(2026, 9, 9, 23, 30)))
    h.emit(_rec('같은날', _epoch(2026, 9, 9, 23, 59)))
    h.emit(_rec('다음날', _epoch(2026, 9, 10, 0, 1)))
    h.close()

    a = tmp_path / 'icg.20260909.log'
    b = tmp_path / 'icg.20260910.log'
    assert a.read_text(encoding='utf-8').split() == ['첫날', '같은날']
    assert b.read_text(encoding='utf-8').split() == ['다음날']


def test_restarting_appends_instead_of_truncating(tmp_path):
    """⛔ **재실행이 앞의 것을 지우면 안 된다** (운영자 지시의 핵심).

    ⚠️ 이것이 `mode='w'` 로 열면 조용히 깨지는 자리다 -- 하루 안에 프로그램을
    두 번 돌리면 **앞 실행의 자취가 통째로 사라진다.**
    """
    t = _epoch(2026, 9, 9, 10, 0)
    for msg in ('첫실행', '두번째실행'):
        h = DailyFile(str(tmp_path), 'icg')
        h.setFormatter(logging.Formatter('%(message)s'))
        h.emit(_rec(msg, t))
        h.close()
    got = (tmp_path / 'icg.20260909.log').read_text(encoding='utf-8')
    assert got.split() == ['첫실행', '두번째실행'], got


def test_the_day_boundary_is_utc_not_local(tmp_path):
    """⭐ **경계는 UTC 다** -- `HKQDATE`·`DATE-OBS`·FITS 파일명과 같아야 한다.

    ⛔ 지역시로 끊으면 한국시 기계(+9)에서 **같은 관측일의 자취가 두 파일로
    갈린다**.  ⚠️ 벤치가 UTC 로 돌아서 안 드러났던 자리다.
    """
    h = DailyFile(str(tmp_path), 'icg')
    h.setFormatter(logging.Formatter('%(message)s'))
    # UTC 로는 9일 15:00 (한국시로는 10일 00:00) -- 9일 파일이어야 한다.
    h.emit(_rec('한국시로는 이미 10일', _epoch(2026, 9, 9, 15, 0)))
    h.close()
    assert (tmp_path / 'icg.20260909.log').exists()
    assert not (tmp_path / 'icg.20260910.log').exists()


def test_a_dot_log_path_stays_a_single_file(tmp_path):
    """⚠️ 옛 설정(`…/icg_archon.log`)은 **그대로 파일 하나**로 돈다.

    ⭐ 판정을 **이름으로** 한다 -- `os.path.isdir` 로 가르면 폴더가 아직 없을 때
    뜻이 뒤집혀, 같은 ini 가 첫 실행과 두 번째 실행에서 다르게 돈다.
    """
    one = _log_handler(str(tmp_path / 'icg_archon.log'), 'icg')
    assert isinstance(one, logging.FileHandler)
    assert not isinstance(one, DailyFile)
    one.close()

    # ⭐ **아직 없는 폴더**를 줘도 폴더로 본다 (파일계에 안 묻는다).
    many = _log_handler(str(tmp_path / 'aint_there_yet'), 'icg')
    assert isinstance(many, DailyFile)
    many.close()

    assert _log_handler('', 'icg') is None
    assert _log_handler('   ', 'icg') is None


def test_the_folder_is_created_if_missing(tmp_path):
    """⚠️ 폴더가 없으면 **만든다** -- 첫 배포에서 로그가 통째로 사라지면 안 된다."""
    d = tmp_path / 'Logs' / 'nested'
    h = DailyFile(str(d), 'icg')
    h.setFormatter(logging.Formatter('%(message)s'))
    h.emit(_rec('만들어졌나', _epoch(2026, 9, 9, 1, 0)))
    h.close()
    assert (d / 'icg.20260909.log').exists()

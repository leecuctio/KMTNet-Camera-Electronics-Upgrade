#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""경로 설정의 `~` 확장 -- **안 하면 조용히 엉뚱한 곳에 쌓인다.**

`os.makedirs('~/AICS/data')` 는 오류를 내지 않는다.  `~` 를 정상적인 상대 경로
조각으로 보고 **작업 디렉터리 아래에 `~` 라는 이름의 폴더**를 만든다.  그래서
설정에 `~/AICS/data` 를 적어 놓고 자료가 거기 있다고 믿는 동안 실제로는
`<cwd>/~/AICS/data` 에 쌓인다 -- 배포에서 실제로 겪을 수 있는 형태다
(2026-08-23 실측, `[paths] data_dir` 이 그 상태였다).

`expnum_file` 은 이미 펼치고 있었다(`resolve_expnum_file`).  그 하나만 펼치고
있었다는 것이 오히려 함정이었다 -- "경로 설정은 `~` 를 받는다" 고 믿게 만든다.
"""

from __future__ import annotations

import os

from ics_sim import config

INI = """
[paths]
data_dir    = ~/AICS/data
expnum_file = ~/AICS/Config/ics.expnum

[logging]
file        = ~/AICS/Logs/ics.log
"""


def _load(tmp_path, text=INI):  # noqa: ANN001, ANN202
    path = tmp_path / 'p.ini'
    path.write_text(text, encoding='utf-8')
    return config.load(str(path))


def test_data_dir_expands_tilde(tmp_path):  # noqa: ANN001
    """`[paths] data_dir` -- raw pair 가 실제로 쌓이는 곳이다."""
    cfg = _load(tmp_path)
    assert not cfg.paths.data_dir.startswith('~'), cfg.paths.data_dir
    assert cfg.paths.data_dir == os.path.expanduser('~/AICS/data')


def test_expnum_file_expands_tilde(tmp_path):  # noqa: ANN001
    cfg = _load(tmp_path)
    assert cfg.paths.expnum_file == os.path.expanduser('~/AICS/Config/ics.expnum')


def test_log_file_expands_tilde(tmp_path):  # noqa: ANN001
    """로그가 `~` 폴더로 가면 취득 이력을 찾을 수 없다."""
    cfg = _load(tmp_path)
    assert cfg.logging.file == os.path.expanduser('~/AICS/Logs/ics.log')


def test_relative_and_absolute_paths_are_untouched(tmp_path):  # noqa: ANN001
    """`~` 가 없는 경로는 손대지 않는다 -- 상대경로도 정당한 설정이다."""
    cfg = _load(tmp_path, """
[paths]
data_dir    = ./rawdata
expnum_file = /mnt/ICSData/ics.expnum
""")
    assert cfg.paths.data_dir == './rawdata'
    assert cfg.paths.expnum_file == '/mnt/ICSData/ics.expnum'


def test_empty_stays_empty(tmp_path):  # noqa: ANN001
    """빈 값은 빈 값이어야 한다 -- `expnum_file` 은 그때 "설정파일 옆" 으로 간다.

    `os.path.expanduser('')` 는 `''` 이지만, 그것을 경로처럼 다루기 시작하면
    "안 적었다" 와 "빈 경로" 가 섞인다.  호출측 분기(`if p.expnum_file:`)가
    그 구분에 기대고 있다.
    """
    cfg = _load(tmp_path, '[logging]\nfile =\n')
    assert cfg.logging.file == ''
    # ini 를 읽었으므로 expnum_file 은 설정파일 옆으로 정해진다
    assert cfg.paths.expnum_file.endswith('.expnum')
    assert not cfg.paths.expnum_file.startswith('~')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXPNUM 지속 -- 재실행에도 번호가 되돌아가지 않는다 (DevNote 11.12).

요구사항(운영자 확정 2026-08-11): **ics 를 재실행해도, `data_dir` 안의 파일
유무와 무관하게, EXPNUM 은 무조건 1 씩 증가한다.**

그래서 검사할 것이 셋이다.

1. 마지막으로 쓴 번호를 기록하고, 다음 실행이 그 +1 부터 쓴다.
2. `data_dir` 를 비워도 번호가 되돌아가지 않는다 -- 카운터가 저장 파일 목록을
   근거로 삼지 않는다는 뜻이고, 이것이 `data_dir` 스캔 방식을 버린 이유다.
3. 기록 위치가 설정파일 옆으로 자동 결정된다(벤치의 `~/AICS/Config/`).

기록 시점이 `advance()` 가 아니라 `next_suffix()` 인 것도 검사한다 -- 노출
도중에 죽었을 때 그 번호가 기록되지 않으면 재실행이 같은 번호를 다시 쓰고,
방금 저장한 파일과 충돌해 파일명 fail-safe 를 부른다(DevNote 6.4).  실물
벤치에서 `FitsNum=00000000.000000` 이 나온 경로가 정확히 그것이었다.
"""

from __future__ import annotations

import os

from ics_sim import config
from ics_sim.state import IcsState


def _state(path: str, **kw) -> IcsState:
    st = IcsState(expnum_file=path, **kw)
    st.load_expnum()
    return st


# -- 1. 이어받기 ----------------------------------------------------------

def test_first_run_starts_at_one(tmp_path):
    """기록이 없으면 1 부터. 파일을 미리 만들어 두지 않는다."""
    rec = str(tmp_path / 'ics_sim.expnum')
    st = _state(rec)
    assert st.expnum == 1
    assert not os.path.exists(rec)          # 읽기만 했으므로 아직 안 만든다


def test_used_number_is_recorded_at_take_time(tmp_path):
    """번호는 `next_suffix()` 시점에 기록된다 -- advance() 를 기다리지 않는다."""
    rec = str(tmp_path / 'ics_sim.expnum')
    st = _state(rec)
    suffix = st.next_suffix()
    assert suffix.endswith('.000001')
    with open(rec, encoding='utf-8') as fh:
        assert int(fh.read()) == 1          # advance() 전에 이미 기록됐다


def test_restart_continues_from_last_plus_one(tmp_path):
    """재실행은 마지막으로 쓴 번호 +1 부터."""
    rec = str(tmp_path / 'ics_sim.expnum')

    first = _state(rec)
    for _ in range(3):                       # 000001, 000002, 000003
        first.next_suffix()
        first.advance()

    second = _state(rec)                     # 재실행
    assert second.expnum == 4
    assert second.next_suffix().endswith('.000004')


def test_crash_mid_exposure_does_not_reuse_the_number(tmp_path):
    """노출 중 죽어도(advance() 미실행) 재실행은 그 번호를 다시 쓰지 않는다."""
    rec = str(tmp_path / 'ics_sim.expnum')

    crashed = _state(rec)
    assert crashed.next_suffix().endswith('.000001')
    # advance() 없이 프로세스가 사라진 상황

    restarted = _state(rec)
    assert restarted.expnum == 2             # 000001 을 다시 쓰지 않는다


# -- 2. data_dir 와 무관 --------------------------------------------------

def test_counter_survives_wiping_data_dir(tmp_path):
    """저장 파일을 다 지워도 번호는 되돌아가지 않는다.

    `data_dir` 를 훑어 최대값+1 을 쓰는 방식이었다면 이 테스트가 깨진다.
    """
    rec = str(tmp_path / 'ics_sim.expnum')
    data = tmp_path / 'data'
    data.mkdir()

    st = _state(rec)
    for _ in range(5):
        suffix = st.next_suffix()
        (data / f'KMTNk.{suffix}.fits').write_text('dummy')
        st.advance()

    for f in data.iterdir():                 # data_dir 를 통째로 비운다
        f.unlink()
    assert not list(data.iterdir())

    assert _state(rec).expnum == 6            # 기록만 보고 이어간다


# -- 3. 기록 위치 ---------------------------------------------------------

def test_expnum_file_defaults_next_to_the_config(tmp_path):
    """빈 값이면 설정파일 옆 같은 이름 `.expnum` 으로 정해진다."""
    ini = tmp_path / 'Config' / 'ics_sim.ini'
    ini.parent.mkdir(parents=True)
    ini.write_text('[paths]\ndata_dir = /tmp/x\n', encoding='utf-8')

    cfg = config.load(str(ini))
    assert cfg.paths.expnum_file == str(tmp_path / 'Config' / 'ics_sim.expnum')


def test_explicit_expnum_file_wins_and_expands_user(tmp_path):
    """명시하면 그 값을 쓰고 `~` 를 펼친다."""
    ini = tmp_path / 'ics_sim.ini'
    ini.write_text('[paths]\nexpnum_file = ~/somewhere/n.expnum\n',
                   encoding='utf-8')

    cfg = config.load(str(ini))
    assert cfg.paths.expnum_file == os.path.expanduser('~/somewhere/n.expnum')


def test_no_config_no_persistence():
    """ini 없이 만든 설정은 지속시키지 않는다 -- 단위 테스트의 기본 동작."""
    cfg = config.SimConfig()
    assert config.resolve_expnum_file(cfg) == ''


# -- 견고성 ---------------------------------------------------------------

def test_unreadable_record_falls_back_to_one(tmp_path):
    """기록이 깨져 있으면 경고만 남기고 1 부터. 기동을 막지 않는다."""
    rec = tmp_path / 'ics_sim.expnum'
    rec.write_text('쓰레기\n', encoding='utf-8')
    assert _state(str(rec)).expnum == 1


def test_empty_record_falls_back_to_one(tmp_path):
    rec = tmp_path / 'ics_sim.expnum'
    rec.write_text('', encoding='utf-8')
    assert _state(str(rec)).expnum == 1


def test_unwritable_record_does_not_raise(tmp_path):
    """기록에 실패해도 노출은 진행한다 -- 예외를 밖으로 내보내지 않는다."""
    # 디렉토리를 파일 경로로 줘서 open() 이 실패하게 만든다
    victim = tmp_path / 'as_a_dir'
    victim.mkdir()
    st = IcsState(expnum_file=str(victim))
    assert st.next_suffix().endswith('.000001')   # 예외 없이 번호는 나온다


def test_persistence_off_when_path_empty(tmp_path):
    """`expnum_file` 이 비면 아무 파일도 만들지 않는다."""
    st = IcsState()
    st.load_expnum()
    st.next_suffix()
    assert st.expnum == 1
    assert not list(tmp_path.iterdir())


def test_record_is_durable_not_just_buffered(tmp_path):
    """**전원이 끊겨도 값이 남아야 한다** (운영자 요구 2026-08-23).

    기록은 임시 파일 -> `os.replace` 인데, 그것만으로는 *원자적*이기만 하고
    *영속*은 아니다 -- 전원 손실 때 내용 블록이 아직 디스크에 없으면 파일이
    비고 번호가 1 로 되돌아간다.  그래서 내용 `fsync` -> `os.replace` ->
    디렉터리 `fsync` 를 다 한다.

    fsync 자체는 시험으로 관측할 수 없으므로, **관측 가능한 것**을 못박는다:
    ① 번호를 집는 그 순간 파일에 값이 있다(종료 시 flush 에 의존하지 않는다)
    ② 임시 파일이 남지 않는다
    ③ 프로그램이 죽어도(= 여기서는 그냥 객체를 버려도) 값이 그대로다
    """
    path = str(tmp_path / 'ics.expnum')
    st = IcsState(expnum_file=path)
    st.load_expnum()
    st.init_channels(('K',))
    st.next_suffix()

    # ① 그 순간 이미 디스크에 있다
    assert open(path, encoding='utf-8').read().strip() == '1'
    # ② 임시 파일을 남기지 않는다
    assert sorted(os.listdir(tmp_path)) == ['ics.expnum']

    # ③ 객체를 버려도(= 프로세스가 죽어도) 다음 기동이 이어받는다
    del st
    again = IcsState(expnum_file=path)
    again.load_expnum()
    assert again.expnum == 2


def test_directory_fsync_helper_never_raises(tmp_path):
    """디렉터리 `fsync` 는 **실패해도 조용히 넘어가야** 한다.

    윈도우는 디렉터리 핸들에 `fsync` 를 못 하고(개발 기계), 일부 파일계통도
    지원하지 않는다.  그 때문에 노출이 죽으면 안 된다 -- 번호 기록은
    "실패해도 노출은 진행한다" 가 규칙이다.
    """
    from ics_sim import state as st_mod
    st_mod._fsync_dir(str(tmp_path))                 # noqa: SLF001
    st_mod._fsync_dir(str(tmp_path / 'nosuchdir'))   # noqa: SLF001
    st_mod._fsync_dir('')                            # noqa: SLF001

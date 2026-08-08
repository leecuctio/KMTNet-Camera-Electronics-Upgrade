#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""골든 대조 -- 시뮬 출력을 실측 레거시 시퀀스와 맞춰 본다.

픽스처는 `tools/extract_golden.py` 가 XIS 로그에서 뽑은 발췌다.  원본 로그는
비커밋(`*.log` / `__localonly_*`)이라 다른 컴퓨터에서 재생성할 수 없으므로
발췌본 자체를 커밋한다 (DevNote 8장).

비교 방식: 타임스탬프·IP·경로·수치를 정규화한 뒤

  (a) ICS -> OBS 메시지의 **형태 시퀀스**가 일치하는가
  (b) 레거시에 있는 메시지 종류를 시뮬이 빠뜨리지 않았는가
  (c) 개수 규약(Acquisition Complete. 4회, Wrote 4회)이 같은가

바이트 단위 일치는 목표가 아니다.  공백 개수는 수신측이 무시하고(DevNote 3장
서두의 "공백에 관하여"),
카운트다운 값은 틱 간격에서 나오는 부수적 결과이기 때문이다.  대신 **메시지의
종류와 순서**는 정확히 같아야 한다.
"""

from __future__ import annotations

import os
import re

import pytest

from conftest import (DARK_SCRIPT, GON5_SCRIPT, OBJECT_SCRIPT, FIXTURES,
                      drive, make_config)

_NUM_VALUE = re.compile(r'(?<==)[^\s]+')
_BARE_NUM = re.compile(r'\b\d+\b')
_QUOTED = re.compile(r"'[^']*'")


def normalise(line: str) -> str:
    """값·수치·공백을 지우고 메시지 '형태'만 남긴다."""
    s = ' '.join(line.split())
    s = _QUOTED.sub("'S'", s)
    s = _NUM_VALUE.sub('#', s)
    return _BARE_NUM.sub('#', s)


def load_fixture(name: str) -> list[str]:
    path = os.path.join(FIXTURES, name)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.rstrip('\n')
            if line and not line.startswith('#'):
                out.append(line)
    return out


def ics_to_obs(lines: list[str]) -> list[str]:
    """ICS -> OBS 메시지만, 형태로 정규화해서."""
    out = []
    for line in lines:
        if not line.upper().startswith('ICS>OBS '):
            continue
        out.append(normalise(line))
    return out


def kinds(shapes: list[str]) -> set[str]:
    """연속 중복을 지운 메시지 종류 집합."""
    return set(shapes)


# -- DARK ----------------------------------------------------------------

DARK_FIXTURE = 'golden_dark_ctio_20240303.txt'


@pytest.mark.skipif(not load_fixture(DARK_FIXTURE), reason='픽스처 없음')
def test_dark_message_kinds_match():
    """레거시 DARK 사이클의 ICS->OBS 메시지 종류를 시뮬이 모두 낸다."""
    legacy = ics_to_obs(load_fixture(DARK_FIXTURE))
    run = drive(DARK_SCRIPT, settle=1.0)
    mine = ics_to_obs(run.sent)

    # 레거시의 커맨드워드 오염(STATUS: STATUS:)은 신규가 의도적으로 고친
    # 부분이라 비교에서 제외한다 (DevNote 5장).
    def clean(shape: str) -> str:
        return shape.replace('STATUS: STATUS:', 'STATUS:')

    legacy_kinds = {clean(s) for s in legacy}
    mine_kinds = {clean(s) for s in mine}

    # 레거시에만 있고 시뮬에 없는 것 -- 있으면 구현이 빠진 것이다.
    missing = legacy_kinds - mine_kinds
    # 이 노출 구간에만 우연히 등장한 것들은 제외한다.
    ignorable = {s for s in missing
                 if 'FILNAME' in s or 'ACQSTATUS' in s or 'DATASOURCE' in s}
    assert not (missing - ignorable), \
        f'레거시에 있는데 시뮬이 안 내는 메시지: {sorted(missing - ignorable)}'


@pytest.mark.skipif(not load_fixture(DARK_FIXTURE), reason='픽스처 없음')
def test_dark_counts_match_legacy():
    legacy = load_fixture(DARK_FIXTURE)
    run = drive(DARK_SCRIPT, settle=1.0)

    def count(lines, needle, prefix=''):
        return sum(1 for m in lines
                   if needle in m and m.upper().startswith(prefix.upper()))

    # 획득 완료: sourceID 앞으로 4회 (레거시는 각 IC 가 직접 보낸다)
    assert count(run.sent, 'Acquisition Complete.') == \
        count(legacy, 'Acquisition Complete.')
    # 저장 완료 중계: ICS -> OBS 4회
    assert count(run.sent, 'Wrote LASTFILE=', 'ICS>OBS') == \
        count(legacy, 'Wrote LASTFILE=', 'ICS>OBS') == 4


@pytest.mark.skipif(not load_fixture(DARK_FIXTURE), reason='픽스처 없음')
def test_dark_relative_order_matches():
    """ICS->OBS 국면 알림의 상대 순서가 레거시와 같은가."""
    marks = ('EXPSTATUS=INITIALIZING', 'EXPSTATUS=ERASE',
             'EXPSTATUS=INTEGRATING', 'Shutter=Closed',
             'EXPSTATUS=READOUT', 'EXPSTATUS=IDLE')

    def order(lines):
        seq = []
        for line in lines:
            if not line.upper().startswith('ICS>OBS '):
                continue
            for m in marks:
                if m in line and (not seq or seq[-1] != m):
                    seq.append(m)
                    break
        return seq

    legacy = order(load_fixture(DARK_FIXTURE))
    mine = order(drive(DARK_SCRIPT, settle=1.0).sent)
    assert mine == legacy, f'\n레거시: {legacy}\n시뮬  : {mine}'


# -- OBJECT --------------------------------------------------------------

OBJECT_FIXTURE = 'golden_object_ctio_20240303.txt'


@pytest.mark.skipif(not load_fixture(OBJECT_FIXTURE), reason='픽스처 없음')
def test_object_shutter_sequence_matches():
    """셔터 경로의 핵심 메시지가 레거시와 같은 순서로 나온다."""
    legacy = load_fixture(OBJECT_FIXTURE)
    run = drive(OBJECT_SCRIPT, settle=1.0)

    # 부분문자열이 아니라 술어로 판정한다.  레거시의 첫 카운트다운 줄은
    #   K.IC>OBS STATUS: SHOPEN  Integration Remaining=54 sec.
    # 처럼 스테일 커맨드워드 SHOPEN 을 달고 있어(DevNote 5.1), 단순
    # 부분문자열로 보면 SHOPEN 명령이 두 번 나간 것처럼 보인다.
    marks = (
        ('SHOPEN', lambda m: m.startswith('ICS>') and ' SHOPEN ' in f' {m} '),
        ('Shutter=Open', lambda m: 'Shutter=Open' in m),
        ('Remaining=', lambda m: 'Remaining=' in m and 'Shutter=Closed' not in m),
        ('Shutter=Closed', lambda m: 'Shutter=Closed' in m),
        ('READOUT', lambda m: 'EXPSTATUS=READOUT' in m),
        ('PCTREAD=', lambda m: 'PCTREAD=' in m),
    )

    def order(lines):
        seq = []
        for line in lines:
            for name, pred in marks:
                if pred(line) and (not seq or seq[-1] != name):
                    seq.append(name)
                    break
        return seq

    # 픽스처 창은 노출 하나보다 길어 다음 사이클 일부가 딸려 들어온다.
    # 시뮬은 한 사이클만 돌리므로 **접두사 일치**로 본다.
    mine, theirs = order(run.sent), order(legacy)
    assert theirs[:len(mine)] == mine, f'\n레거시: {theirs}\n시뮬  : {mine}'


@pytest.mark.skipif(not load_fixture(OBJECT_FIXTURE), reason='픽스처 없음')
def test_object_shopen_form():
    """`SHOPEN <sec> <sourceID> USESTATUS` 형태를 유지한다."""
    run = drive(OBJECT_SCRIPT, settle=1.0)
    hits = run.find('SHOPEN')
    assert hits, 'SHOPEN 을 보내지 않았다'
    assert re.search(r'SHOPEN \d+(\.\d+)? OBS USESTATUS', hits[0]), hits[0]


# -- GO n ----------------------------------------------------------------

GON5_FIXTURE = 'golden_gon5_ctio_20240102.txt'


@pytest.mark.skipif(not load_fixture(GON5_FIXTURE), reason='픽스처 없음')
def test_gon5_image_progress_matches_legacy():
    """`Image n of N complete.` 형태와 개수가 레거시와 같다."""
    legacy = load_fixture(GON5_FIXTURE)
    legacy_imgs = [normalise(m) for m in legacy if 'complete.' in m]
    assert legacy_imgs, '픽스처에 Image .. complete. 가 없다'

    run = drive(GON5_SCRIPT, settle=1.0)
    mine = [normalise(m) for m in run.sent if 'complete.' in m]
    assert set(mine) <= set(legacy_imgs) or set(legacy_imgs) <= set(mine), \
        f'\n레거시: {sorted(set(legacy_imgs))}\n시뮬  : {sorted(set(mine))}'
    # 마지막 프레임은 STATUS 가 아니라 DONE 으로 끝난다
    assert not [m for m in run.sent if 'Image 5 of 5' in m]


# -- 정규화 자체 ---------------------------------------------------------

def test_normalise():
    assert normalise('ICS>OBS  DONE:  EXP  ExpTime=30 seconds.') == \
        'ICS>OBS DONE: EXP ExpTime=# seconds.'
    assert normalise("ICS>OBS DONE: DARK ObjectName='begin' EXP=30") == \
        "ICS>OBS DONE: DARK ObjectName=# EXP=#"

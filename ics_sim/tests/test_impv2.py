#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IMPv2.5 파싱/조립 단위 테스트."""

from __future__ import annotations

import pytest

from conftest import drive, make_config
from ics_sim import impv2


# -- 파싱 왕복 -----------------------------------------------------------

def test_roundtrip():
    payload = impv2.format('ICS', 'OBS', 'DONE', 'PROJID', 'ProjID=OBS')
    assert payload.endswith(b'\r')
    msg = impv2.parse(payload)
    assert msg is not None
    assert (msg.src, msg.dst, msg.mtype) == ('ICS', 'OBS', 'DONE')
    assert msg.cmdword == 'PROJID'
    assert msg.body == 'ProjID=OBS'


def test_implicit_req_type():
    """타입 토큰이 없으면 암묵 REQ.  REQ: 는 리터럴로 보내지 않는다."""
    msg = impv2.parse(b'OBS>ICS projid obs\r')
    assert msg.mtype == 'REQ'
    assert msg.explicit_type is False
    assert impv2.format('ICS', 'TC', 'REQ', 'AUXSTATUS') == b'ICS>TC AUXSTATUS\r'


def test_heartbeat():
    msg = impv2.parse(b'tcs>isis\r')
    assert msg is not None and msg.is_heartbeat


def test_broadcast():
    msg = impv2.parse(b'TC>AL ping\r')
    assert msg.is_broadcast
    assert msg.addressed_to('ICS')


# -- malformed 는 조용히 버린다 (스펙 2.5절) -----------------------------

@pytest.mark.parametrize('raw', [
    b'ICS>OBS DONE: PROJID ProjID=OBS',      # 종료문자 없음
    b'ICS>OBS DONE: x\ny\r',                 # \n 포함
    b'ICS>OBS DONE: x\0y\r',                 # \0 포함
    b'A>OBS DONE: x\r',                      # 노드명 1자
    b'TOOLONGNODE>OBS DONE: x\r',            # 노드명 9자
    b'no separator here\r',                  # 헤더 없음
    b'\r',
])
def test_malformed_returns_none(raw):
    assert impv2.parse(raw) is None


def test_oversized_rejected():
    line = b'ICS>OBS DONE: X ' + b'a' * impv2.MAX_LEN + b'\r'
    assert impv2.parse(line) is None


# -- 대소문자 무관 -------------------------------------------------------

def test_case_insensitive_matching():
    for text in (b'OBS>ICS Go\r', b'OBS>ICS go\r', b'OBS>ICS GO\r'):
        assert impv2.parse(text).cmd_is('go')
    assert impv2.parse(b'obs>ics DONE: x\r').mtype == 'DONE'


def test_node_validation():
    assert impv2.is_valid_node('K.IC')
    assert impv2.is_valid_node('ICS')
    assert not impv2.is_valid_node('A')
    assert not impv2.is_valid_node('WAY.TOO.LONG')


# -- key=value (레거시 GetArg 가 못 하던 부분) ---------------------------

def test_kv_quoted_and_parenthesised():
    body = ("ImageType=OBJECT ObjectName='BLG 11 field' "
            'Observer=(Pogge, DePoy, and Mason) EXP=60')
    kv = impv2.parse_kv(body)
    assert kv['ImageType'] == 'OBJECT'
    assert kv['ObjectName'] == 'BLG 11 field'
    assert kv['Observer'] == 'Pogge, DePoy, and Mason'
    assert kv['EXP'] == '60'


def test_kv_preserves_order():
    body = 'AUXQDATE=1 TIMESYS=UTC TELID=KMTC'
    assert [k for k, _ in impv2.iter_kv(body)] == \
        ['AUXQDATE', 'TIMESYS', 'TELID']


def test_kv_empty_value():
    """레거시의 GBUILD= 처럼 값이 빈 필드도 살려야 한다."""
    assert impv2.parse_kv('GBUILD= ICSBUILD=KX2016')['GBUILD'] == ''


# -- 깨진 명령 수신 (DevNote 5.3) ----------------------------------------

@pytest.mark.parametrize('broken, echo', [
    ('OBS>ICS OBCT BLG37', 'OBCT BLG37'),
    ('OBS>K.IC N 60 OBS USESTATUS', 'N 60 OBS USESTATUS'),
    ('OBS>K.IC EN 60 OBS USESTATUS', 'EN 60 OBS USESTATUS'),
])
def test_corrupted_command_is_rejected_not_crashed(broken, echo):
    """전송 손상으로 깨진 명령은 레거시와 같은 형식으로 거부한다."""
    run = drive([broken], settle=0.1)
    replies = run.find("Didn't understand")
    assert replies, f'거부 응답이 없다: {broken}'
    assert echo in replies[0]


def test_unknown_node_still_served():
    """문서에 없는 노드(CHA 등)에서 온 명령도 프로토콜대로 처리한다.

    IMPv2 에 노드 인증 개념이 없고, 실측 로그에도 CHA/C1 이 명령을 보낸다
    (DevNote 6.3).  발신자 화이트리스트를 두지 않는다.
    """
    run = drive(['CHA>ICS ExpNum'], settle=0.1)
    assert run.count('DONE: EXPNUM', node='CHA') == 1
    assert run.find('Filename=')[0].startswith('ICS>CHA')


def test_guide_node_not_answered():
    """G.IC 는 범위 밖이다.  ICG 가 별도 프로그램이므로 답하면 충돌한다."""
    run = drive(['OBS>G.IC STATUS'], settle=0.1)
    assert run.to('OBS') == []


def test_quote_helpers():
    assert impv2.quote('one') == 'one'
    assert impv2.quote('two words') == "'two words'"
    assert impv2.quote_always('one') == "'one'"
    assert impv2.paren('smc') == '(smc)'

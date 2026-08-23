#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""저수준 왕복 -- 프레이밍 · 오류 응답 · 무응답 · 시한 초과 후 재동기.

**이 파일이 labtest 의 회귀 1건(DevNote 11.22 (1))을 못박는 자리다.**  시한
초과 뒤에 다음 두 명령이 살아 있는지를 실제 소켓으로 확인한다.
"""

from __future__ import annotations

import pytest
from fake_archon import FakeArchon

from ics_archon.archon.protocol import ArchonError, ArchonLink


@pytest.fixture()
def fake():  # noqa: ANN201
    srv = FakeArchon()
    srv.start()
    yield srv
    srv.shutdown()


def link_to(srv, **kw):  # noqa: ANN001, ANN201
    link = ArchonLink('127.0.0.1', srv.port, name='TEST', **kw)
    link.connect()
    return link


def test_text_command_roundtrip(fake):  # noqa: ANN001
    link = link_to(fake)
    reply = link.command('SYSTEM', timeout=5)
    assert b'BACKPLANE_ID=' in reply
    link.close()


def test_reference_number_wraps_at_256(fake):  # noqa: ANN001
    """참조번호는 2자리 16진이라 256 에서 돌아야 한다."""
    link = link_to(fake)
    for _ in range(260):
        link.command('APPLYSYSTEM', timeout=5)
    link.close()


def test_reply_error_is_distinguished(fake):  # noqa: ANN001
    """`?xx` 는 **컨트롤러가 거부한 것**이다 -- 프레이밍 오류와 갈라야 한다.

    labtest 는 `<xx` 만 대조해서 이 경우가 'Invalid command packet header' 로
    뭉개졌다 -- 원인이 "내 명령이 틀렸다" 인데 화면에는 "프로토콜이 깨졌다" 로
    나온다.
    """
    fake.reject = ('LOADPARAMS',)
    link = link_to(fake)
    with pytest.raises(ArchonError) as exc:
        link.command('LOADPARAMS', timeout=5)
    assert exc.value.reply_error is True
    # 거부된 뒤에도 왕복은 살아 있다 (연결을 버릴 이유가 없다).
    assert b'BACKPLANE_ID=' in link.command('SYSTEM', timeout=5)
    link.close()


def test_unknown_command_gets_no_reply_at_all(fake):  # noqa: ANN001
    """매뉴얼 p.45: **인식 못 한 명령은 무시된다.**

    가장 헷갈리는 실패 형태다 -- 오타 하나로 `timeout=None` 이 영구히 멈춘다.
    그래서 `controller.py` 는 명령마다 상한을 준다.
    """
    fake.unknown = ('NOSUCHCMD',)
    link = link_to(fake)
    with pytest.raises(TimeoutError):
        link.command('NOSUCHCMD', timeout=0.5)
    link.close()


def test_timeout_then_two_more_commands_survive(fake):  # noqa: ANN001
    """**회귀 1번의 못박음.**  STATUS 가 늦게 와도 다음 두 명령이 살아야 한다.

    labtest v1.1 의 결함: `msgref` 를 응답 검증 뒤에 올려서, 늦게 도착한
    STATUS 의 `<NN` 이 다음 명령의 번호와 맞아떨어졌다 -- 다음 명령이 남의
    응답을 먹고 그 다음이 죽었다.  실측 순서까지 짚였다 (`WCONFIG` 가 STATUS
    본문을 삼키고 `APPLYSYSTEM` 이 예외).

    여기서는 두 겹으로 막는다 -- 번호를 **미리** 올리고(원리상 일치 불가),
    `command_or_resync` 가 연결을 새로 연다(부분 수신분 제거).
    """
    fake.status_delay = 1.0
    link = link_to(fake)
    assert link.command_or_resync('STATUS', timeout=0.2) is None
    assert link.resyncs == 1
    # 늦은 응답이 새 연결에는 오지 않는다 -- 두 명령이 제 응답을 받아야 한다.
    assert link.command('APPLYSYSTEM', timeout=5) == b''
    assert b'BACKPLANE_ID=' in link.command('SYSTEM', timeout=5)
    link.close()


def test_pipeline_matches_each_reply_to_its_own_ref(fake):  # noqa: ANN001
    """ACF 적용 형태 -- 몰아 보내고 몰아 받는다.

    설정 줄 수천 개를 왕복마다 기다리면 몇 분이 걸리므로 labtest 도 이 형태다.
    응답이 명령 순서대로 오는지, 참조번호가 각자 것으로 대조되는지 본다.
    """
    link = link_to(fake)
    cmds = ['WCONFIG%04XKEY%d=V%d' % (i, i, i) for i in range(300)]
    replies = link.pipeline(cmds, timeout=10)
    assert len(replies) == 300
    assert fake.config[0] == 'KEY0=V0'
    assert fake.config[299] == 'KEY299=V299'
    link.close()


def test_fetch_returns_exactly_requested_bytes(fake):  # noqa: ANN001
    """`FETCH` 는 1024B 블록으로 오고 마지막 블록은 남는다 -- 잘라 써야 한다."""
    fake.width, fake.height = 700, 3          # 4200 B = 4블록 + 104 B
    link = link_to(fake)
    want = fake.width * fake.height * 2
    data = link.fetch(0xA0000000, want, timeout=10)
    assert len(data) == want
    assert data[:2] == b'\x00\x00'            # 픽셀 0
    assert data[2:4] == b'\x01\x00'            # 픽셀 1 (리틀엔디언)
    link.close()


def test_fetch_rejection_is_reported_not_hung(fake):  # noqa: ANN001
    """`?xx` 로 거부된 FETCH 를 블록 대기로 오해하지 않는다."""
    fake.reject = ('FETCH',)
    link = link_to(fake)
    with pytest.raises(ArchonError) as exc:
        link.fetch(0, 2048, timeout=2)
    assert exc.value.reply_error is True
    link.close()

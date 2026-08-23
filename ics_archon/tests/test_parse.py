#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""응답 해석 -- `FRAME` 최신 프레임 판정 · 진행률 · 텔레메트리 "자리 = 항목".

왕복이 없으므로 실기 응답 한 줄을 붙여넣어 재현할 수 있다.  실기 자료가
들어오면 그 문자열을 그대로 케이스로 추가할 것.
"""

from __future__ import annotations

from fake_archon import DEFAULT_STATUS, DEFAULT_SYSTEM, FakeArchon

from ics_archon.archon import parse


def test_keyvals_ignores_tokens_without_equals():
    got = parse.keyvals(b'A=1 junk B=2.5')
    assert got == {'A': '1', 'B': '2.5'}


def test_newest_prefers_a_higher_complete_frame_over_rbuf():
    """버퍼가 셋이라 가장 최근 프레임이 반드시 `RBUF` 는 아니다.

    labtest `newest()` 의 2단계 판정을 그대로 옮겼는지 본다.
    """
    fields = {'RBUF': '1', 'WBUF': '0'}
    for n, (frame, complete) in enumerate(((7, 1), (9, 1), (8, 1)), start=1):
        fields.update({
            'BUF%dFRAME' % n: str(frame), 'BUF%dCOMPLETE' % n: str(complete),
            'BUF%dWIDTH' % n: '19200', 'BUF%dHEIGHT' % n: '9400',
            'BUF%dSAMPLE' % n: '0', 'BUF%dBASE' % n: str(0x1000 * n),
            'BUF%dLINES' % n: '9400',
        })
    fs = parse.newest(fields)
    assert (fs.frame, fs.buf) == (9, 1)          # buf 는 0-기준
    assert fs.base == 0x2000
    assert fs.progress is None                   # 쓰는 중이 아니다


def test_newest_ignores_an_incomplete_newer_frame():
    """번호가 커도 **완료되지 않은** 버퍼는 고르지 않는다 -- 반쪽 프레임이다."""
    fields = {'RBUF': '1', 'WBUF': '2'}
    for n, (frame, complete) in enumerate(((7, 1), (9, 0), (0, 0)), start=1):
        fields.update({
            'BUF%dFRAME' % n: str(frame), 'BUF%dCOMPLETE' % n: str(complete),
            'BUF%dWIDTH' % n: '10', 'BUF%dHEIGHT' % n: '20',
            'BUF%dSAMPLE' % n: '0', 'BUF%dBASE' % n: '0',
            'BUF%dLINES' % n: '5',
        })
    fs = parse.newest(fields)
    assert fs.frame == 7
    # 진행률은 **쓰기 버퍼**(WBUF=2)에서 온다 -- 5/20 = 25%
    assert fs.progress == 25


def test_progress_never_reports_100_before_completion():
    """진행률은 99 에서 멈춘다 -- 100 은 완료가 확정된 뒤에만 낸다.

    시퀀서는 `pctread_final`(100) 을 보면 "Acquisition Complete." 로 넘어간다
    (`_readout` 이 그 값에서 루프를 끊는다).  폴링이 99.6% 를 100 으로
    반올림해 내보내면 **프레임이 아직 안 끝났는데** 획득 완료가 나간다.
    """
    fields = {'RBUF': '1', 'WBUF': '1',
              'BUF1FRAME': '3', 'BUF1COMPLETE': '0',
              'BUF1WIDTH': '10', 'BUF1HEIGHT': '1000',
              'BUF1SAMPLE': '0', 'BUF1BASE': '0', 'BUF1LINES': '1000'}
    assert parse.newest(fields).progress == 99


def test_samplemode_doubles_the_byte_count_not_the_geometry():
    """**픽셀 수 비교로는 samplemode 를 못 잡는다** (DevNote 11.22 (3)).

    32bit 표본이면 기하는 선언과 같은데 바이트 수가 정확히 2배다.  이 성질이
    데이터부 패딩과 겹쳐 파일 전체를 못 읽게 만든 회귀의 원인이었다.
    """
    base = {'RBUF': '1', 'WBUF': '0', 'BUF1FRAME': '1', 'BUF1COMPLETE': '1',
            'BUF1WIDTH': '100', 'BUF1HEIGHT': '50', 'BUF1BASE': '0',
            'BUF1LINES': '50'}
    fs16 = parse.newest({**base, 'BUF1SAMPLE': '0'})
    fs32 = parse.newest({**base, 'BUF1SAMPLE': '1'})
    assert (fs16.width, fs16.height) == (fs32.width, fs32.height)
    assert fs32.data_bytes == 2 * fs16.data_bytes == 100 * 50 * 4


def test_telemetry_keeps_one_slot_per_item_even_when_missing():
    """**자리 = 항목** (raw spec 5.6절).  결측이면 그 자리에 sentinel 이다.

    건너뛰면 뒤 항목이 앞으로 당겨져 소비자가 구분할 방법이 없다 -- MOD6 이
    없으면 MOD7 값이 MOD6 자리에 앉는다.
    """
    status = dict(DEFAULT_STATUS)
    del status['MOD6/TEMP']
    status['P5V_V'] = 'FAULT'                    # 비수치 토큰
    telem = parse.telemetry_of(status)
    assert len(telem['temp']) == len(parse.TEMP_SLOTS)
    assert len(telem['volt']) == len(telem['curr']) == len(parse.VOLT_RAILS)
    assert telem['temp'][2] == parse.SLOT_NC     # MOD6 자리
    assert telem['temp'][3] == 33.0              # MOD7 은 제자리
    assert telem['volt'][1] == parse.SLOT_NC     # P5V 자리
    assert telem['volt'][2] == 5.834             # P6V 는 제자리


def test_telemetry_of_nothing_is_empty_not_a_row_of_sentinels():
    """STATUS 를 아예 못 떴으면 `rawhdr` 가 카드를 `'NC'` 로 만들게 넘긴다.

    자리마다 sentinel 을 채워 보내면 "물어봤는데 다 결측" 과 "안 물어봤다" 가
    헤더에서 구별되지 않는다.
    """
    assert parse.telemetry_of(None) == {}
    assert parse.telemetry_of({}) == {}


def test_volt_rails_come_from_ics_sim_not_a_local_copy():
    """자리 순서의 정본은 `ics_sim.rawhdr` 다 -- 사본을 두면 개정 때 갈린다."""
    from ics_sim import rawhdr
    assert parse.VOLT_RAILS is rawhdr.VOLT_RAILS


def test_unit_identity_uses_backplane_id_as_the_serial():
    """컨트롤러가 보고하는 유일한 개체 식별자가 `BACKPLANE_ID` 다 (p.46).

    모델명 문자열 필드는 없다.  그리고 **모르는 키는 넣지 않는다** --
    빈 문자열을 넣으면 `rawhdr` 의 `'NC'` sentinel 경로를 건너뛴다.
    """
    ident = parse.unit_identity(DEFAULT_SYSTEM)
    assert ident['sn'] == '0024498A715E301C'
    assert ident['id'].startswith('ARCHON-X12')
    assert parse.unit_identity({}) == {}
    assert parse.unit_identity({'BACKPLANE_ID': 'X'}) == {'sn': 'X'}


def test_module_map_confirms_the_ad_slot_assumption():
    """`TEMP_SLOTS` 는 AD(비디오) 모듈이 슬롯 5~8 이라고 전제한다 (p.20).

    `MODn_TYPE=2` 가 AD 다 -- 실기에서 이 가정을 확인하는 수단이고,
    `ArchonController._log_module_map()` 이 어긋나면 경고한다.
    """
    mods = parse.module_types(DEFAULT_SYSTEM)
    assert [s for s, t in mods.items() if t == 2] == [5, 6, 7, 8]
    assert parse.MODULE_TYPES[2] == 'AD'
    assert all('MOD%d/TEMP' % s in parse.TEMP_SLOTS for s in (5, 6, 7, 8))


def test_fake_controller_status_uses_the_real_field_names():
    """가짜 상대역이 매뉴얼 필드 이름을 쓰는지 -- 시험이 헛돌지 않게.

    이름을 우리끼리 지어 두면 `TEMP_SLOTS`/`VOLT_RAILS` 가 무엇과도 맞물리지
    않은 채 초록이 된다.
    """
    srv = FakeArchon()
    try:
        telem = parse.telemetry_of(srv.status)
        assert all(isinstance(v, float) for v in telem['temp'])
        assert all(isinstance(v, float) for v in telem['volt'])
        assert parse.power_good(srv.status) is True
    finally:
        srv.shutdown()

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


def test_telemetry_keeps_one_field_per_item_even_when_missing():
    """**자리 = 항목** (raw spec 5.6절).  결측이면 그 자리에 sentinel 이다.

    건너뛰면 뒤 항목이 앞으로 당겨져 소비자가 구분할 방법이 없다 -- MOD6 이
    없으면 MOD7 값이 MOD6 자리에 앉는다.
    """
    status = dict(DEFAULT_STATUS)
    del status['MOD2/TEMP']                      # 자리 3 (규격 5.6.1절 표)
    status['P5V_V'] = 'FAULT'                    # 비수치 토큰
    telem = parse.telemetry_of(status)
    assert len(telem['temp']) == len(parse.TEMP_MODS) == 10
    assert len(telem['volt']) == len(telem['curr']) == len(parse.VOLT_RAILS)
    assert telem['temp'][2] == parse.FIELD_NC     # Mod2 자리
    assert telem['temp'][3] == 30.3              # Mod3 은 제자리
    assert telem['volt'][1] == parse.FIELD_NC     # P5V 자리
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


def test_module_map_matches_the_spec_field_table_not_the_old_ad_range():
    """가짜 `SYSTEM` 은 **실기 science 구성**이고 자리 표와 같아야 한다.

    ⚠️ **종전 이름은 `..._confirms_the_ad_slot_assumption` 이었고, 그 가정
    (매뉴얼 p.20 "AD 는 중앙 4슬롯 5~8")은 폐기됐다** (2026-08-27).  실기는
    AD 계열이 **5·8 둘뿐**이고 6·7 은 빈 슬롯이다 -- 규격 5.6.1절의 열 자리와
    정확히 같다.  가짜가 옛 가정을 담고 있어서 **정상 구성에서 경고가 나던
    결함을 이 시험들이 통과시켰다.**
    """
    mods = parse.module_types(DEFAULT_SYSTEM)
    assert sorted(s for s, t in mods.items() if t) == [1, 2, 3, 4, 5, 8, 9, 10, 11]
    assert sorted(s for s, t in mods.items() if t in parse.AD_TYPES) == [5, 8]
    assert parse.MODULE_TYPES[2] == 'AD'
    # 자리 표에 실리는 AD 는 5·8 뿐이고 6·7 은 자리를 차지하지 않는다.
    assert 'MOD5/TEMP' in parse.TEMP_MODS and 'MOD8/TEMP' in parse.TEMP_MODS
    assert 'MOD6/TEMP' not in parse.TEMP_MODS
    assert 'MOD7/TEMP' not in parse.TEMP_MODS


def test_cn_temp_mod_order_follows_spec_5_6_1():
    """`Cn_TEMP` 열 자리가 **규격 5.6.1절 표 그대로**여야 한다.

    자리 자체가 항목이므로(값에 이름표가 없다) 순서가 하나만 밀려도 소비자는
    **다른 모듈의 온도를 그 모듈 값으로 읽는다** -- 아무 오류도 나지 않는다.
    v1.5 반영 전에는 잠정 5자리였고 견본 pair(10개)와 갈려 있었다.
    """
    assert parse.TEMP_MODS == (
        'BACKPLANE_TEMP', 'MOD1/TEMP', 'MOD2/TEMP', 'MOD3/TEMP', 'MOD4/TEMP',
        'MOD5/TEMP', 'MOD8/TEMP', 'MOD9/TEMP', 'MOD10/TEMP', 'MOD11/TEMP')
    # 자리를 차지하지 않는 모듈이 보고돼도 카드에는 안 실린다.
    telem = parse.telemetry_of(DEFAULT_STATUS)
    assert len(telem['temp']) == 10
    assert 32.5 not in telem['temp'] and 33.0 not in telem['temp']  # Mod6·7


def test_module_types_cover_the_whole_manual_list_including_the_ad_family():
    """`MODn_TYPE` 표는 매뉴얼 p.46 전량이어야 한다 (F9).

    13/14/15(ADF/ADX/ADLN)가 빠져 있었다.  이름표가 빠지는 것보다 나쁜 것은
    **AD 판정이 `t == 2` 하나였다는 것**이다 -- 그 셋 중 하나가 꽂힌 백플레인
    에서는 `tools/probe_archon.py` 1단계가 "AD 모듈을 못 찾았다" 를 내고, 그
    화면이 실기 첫 실행에서 가장 먼저 보는 것이다.
    """
    for code, name in ((13, 'ADF'), (14, 'ADX'), (15, 'ADLN')):
        assert parse.MODULE_TYPES[code] == name
        assert code in parse.AD_TYPES
    assert 2 in parse.AD_TYPES
    # ADX 가 꽂힌 백플레인도 슬롯 5~8 을 AD 로 읽어야 한다.
    system = dict(DEFAULT_SYSTEM)
    system.update({'MOD5_TYPE': '14', 'MOD6_TYPE': '14',
                   'MOD7_TYPE': '14', 'MOD8_TYPE': '14'})
    mods = parse.module_types(system)
    assert sorted(s for s, t in mods.items() if t in parse.AD_TYPES) == [5, 6, 7, 8]




#: 실기 science ACF 의 모듈 구성.  **가짜 `DEFAULT_SYSTEM` 이 이미 그 값**이라
#: (`fake_archon.py`, 2026-08-27) 사본을 두지 않고 그것을 가리킨다 -- 사본을
#: 두면 한쪽만 고쳐진다.  KMTC/KMTS 는 `MOD9_TYPE` 이 18(HVYBias)이다.
REAL_SCIENCE_SYSTEM = DEFAULT_SYSTEM


def test_module_types_name_the_post_manual_modules_17_and_18():
    """매뉴얼(2021)은 15 까지만 정의하고 "16+: Unknown" 이다 (p.46).

    실기 science ACF 는 `MOD5/MOD8_TYPE=17`(ADM) 이고 KMTC/KMTS 는
    `MOD9_TYPE=18`(HVYBias) -- **매뉴얼보다 새로운 모듈**이다 (운영자 확정
    2026-08-27).  이름표가 없으면 기동 배너가 `5:?17 8:?17` 로 찍힌다.
    """
    assert parse.MODULE_TYPES[17] == 'ADM'
    assert parse.MODULE_TYPES[18] == 'HVYBias'
    # 16 은 아직 모른다 -- 추측해서 채우지 않았는지 못박는다.
    assert 16 not in parse.MODULE_TYPES


def test_ad_types_include_adm_so_the_real_backplane_is_not_a_false_alarm():
    """`17`(ADM) 이 빠져 있어서 실기에서 `ad` 가 **빈 목록**이 됐다.

    F9 가 13/14/15 를 넣어 막으려던 그 오경보("AD 모듈을 못 찾았다")가 형
    번호가 달라 그대로 재현됐다 -- 실기 첫 실행에서 가장 먼저 보는 화면이다.
    """
    assert 17 in parse.AD_TYPES
    mods = parse.module_types(REAL_SCIENCE_SYSTEM)
    assert sorted(s for s, t in mods.items() if t in parse.AD_TYPES) == [5, 8]


def test_real_science_layout_matches_the_spec_field_table():
    """⭐ **회귀** -- 실기 정상 구성이 경고를 내지 않아야 한다.

    종전 판정은 `sorted(ad) != [5, 6, 7, 8]` 였다 (매뉴얼 p.20 "AD 는 중앙
    4슬롯" 을 옮긴 잠정안).  실기 science 는 AD 계열이 **5·8 둘뿐**이고 6·7 은
    빈 슬롯이라 **정상 구성에서 경고가 났다.**  판정을 자리 표(규격 5.6.1절)
    대 실제 장착 모듈 비교로 바꿨다.
    """
    assert parse.temp_mod_slots() == frozenset({1, 2, 3, 4, 5, 8, 9, 10, 11})
    assert parse.field_order_problems(REAL_SCIENCE_SYSTEM) == []
    # 형 18(KMTC/KMTS)로 바뀌어도 자리 수는 같다 -- 자리 표는 형이 아니라
    # **장착 여부**를 본다.
    kmtc = dict(REAL_SCIENCE_SYSTEM, MOD9_TYPE='18')
    assert parse.field_order_problems(kmtc) == []
    # 보고가 아예 없으면 판정하지 않는다 (없는 필드를 이상으로 세지 않는다, F2).
    assert parse.field_order_problems({}) == []
    assert parse.field_order_problems(None) == []


def test_field_order_problems_names_both_directions_of_mismatch():
    """자리 표와 실물이 어긋나면 **어느 쪽으로** 어긋났는지 말해야 한다.

    자리 수 자체가 모듈 구성 판별에 쓰이므로(5.6.1절), 어긋난 채로 실으면
    소비자는 **다른 모듈의 온도를 그 모듈 값으로 읽는다** -- 아무 오류도 나지
    않는다.
    """
    # 슬롯 6·7 이 장착됐고(자리 표에 없다) 9·10·11 이 없다(자리 표에 있다).
    wrong = {k: v for k, v in REAL_SCIENCE_SYSTEM.items()
             if k not in ('MOD9_TYPE', 'MOD10_TYPE', 'MOD11_TYPE')}
    wrong.update({'MOD6_TYPE': '17', 'MOD7_TYPE': '17'})
    bad = parse.field_order_problems(wrong)
    assert len(bad) == 2
    assert '[6, 7]' in bad[0]
    assert '[9, 10, 11]' in bad[1]


def test_health_problems_names_power_and_overheat_faults():
    """전원·과열을 취득 경로가 **한 번도 안 봤다** (F2).

    `POWERGOOD`/`OVERHEAT`/`POWER` 는 노출마다 뜨는 `STATUS` 안에 이미 있다
    (매뉴얼 p.47) -- 왕복을 늘리지 않고 원인을 가를 수 있는 자리였다.
    """
    assert parse.health_problems(DEFAULT_STATUS) == []

    bad = dict(DEFAULT_STATUS, POWERGOOD='0')
    assert any('POWERGOOD' in m for m in parse.health_problems(bad))

    hot = dict(DEFAULT_STATUS, OVERHEAT='1')
    assert any('OVERHEAT' in m for m in parse.health_problems(hot))
    assert parse.overheating(hot) is True

    # `POWERON` 이 성공해도 일부 모듈만 올라온 상태가 있다 (POWER=3).
    part = dict(DEFAULT_STATUS, POWER='3')
    got = parse.health_problems(part)
    assert any('POWER=3' in m for m in got), got
    assert parse.health_problems(dict(DEFAULT_STATUS, POWER='4')) == []


def test_missing_health_fields_are_not_counted_as_faults():
    """**보고하지 않는 필드를 이상으로 세지 않는다.**

    실기 응답을 아직 못 봤다(PROVISIONAL).  없는 필드를 이상으로 세면 첫
    실행이 통째로 경보가 되고, 그러면 진짜 이상이 그 소음에 묻힌다.
    """
    lean = {k: v for k, v in DEFAULT_STATUS.items()
            if k not in ('POWERGOOD', 'OVERHEAT', 'POWER')}
    assert parse.health_problems(lean) == []
    assert parse.power_state(lean) is None


def test_fake_controller_status_uses_the_real_field_names():
    """가짜 상대역이 매뉴얼 필드 이름을 쓰는지 -- 시험이 헛돌지 않게.

    이름을 우리끼리 지어 두면 `TEMP_MODS`/`VOLT_RAILS` 가 무엇과도 맞물리지
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

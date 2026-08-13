#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""호스트 IP 로 사이트를 판정하는 규약 (D-015).

`[node] site` 한 줄이 사이트 코드 → 좌표 → 관측일 경계 → 파일명까지 전부 끌고
가므로(D-011·D-014), 그 한 줄이 틀리면 **아무 오류 없이** 전부 틀린다.  설정
묶음을 통째로 잘못 복사하면 안에 있는 어떤 값으로도 잡을 수 없어서, **설정 밖에서
오는 신호**(호스트 주소)로 판정한다.

**이 파일의 절반은 "경고가 안 떠야 한다" 를 지킨다.**  오탐이 잦은 검사는 사람이
무시하는 것을 학습시켜서 검사가 없는 것보다 나쁘다 -- 벤치·오프라인 노트북·
canned 모드가 전부 정상 상황이므로 조용해야 한다.
"""

from __future__ import annotations

import logging

import pytest

from conftest import make_config

from ics_sim import rawpair, siteid
from ics_sim.config import SimConfig
from ics_sim.telemetry import TelemetryRelay


# -- 대역 → 사이트 --------------------------------------------------------

#: 근거: `ics_legacy/icg_legacy_report.md:47` (세 사이트 로그에서 확인).
#: 신규 CEU 망도 같은 대역을 쓴다 (운영자 확정 2026-08-13).
BAND_CASES = [
    (('192.168.14.109',), 'KMTC'),            # CTIO -- Science server
    (('192.168.14.102',), 'KMTC'),            # 같은 대역, 다른 호스트
    (('192.168.13.108',), 'KMTS'),            # SAAO
    (('192.168.15.109',), 'KMTA'),            # SSO
]


@pytest.mark.parametrize('addrs,want', BAND_CASES)
def test_known_band_identifies_the_site(addrs, want):
    got, why = siteid.site_of(addrs)
    assert got == want
    assert addrs[0] in why, '근거 문구에 판정에 쓴 주소가 들어가야 한다'


def test_last_octet_is_not_part_of_the_decision():
    """**/24 대역만 본다** -- 호스트의 마지막 옥텟은 보지 않는다.

    레거시는 호스트 IP 를 통째로 박아서(`ics_legacy_report.md:763`,
    `192.168.15.109`) SSO 의 XIS 주소가 바뀌면 갑자기 매 노출 경고가 떴다
    (`:784`).  같은 함정을 밟지 않는다.
    """
    codes = {siteid.site_of((f'192.168.15.{n}',))[0] for n in (1, 42, 109, 254)}
    assert codes == {'KMTA'}


# -- 그 밖은 전부 벤치 ----------------------------------------------------

BENCH_CASES = [
    ('192.168.1.5',),        # 192.168 이지만 사이트 대역이 아니다 (운영자 확정)
    ('192.168.22.221',),     # 개발 머신에서 실제로 관측된 주소
    ('10.0.0.5',),
    ('172.16.4.9',),
    ('169.254.11.22',),      # link-local -- DHCP 실패
]


@pytest.mark.parametrize('addrs', BENCH_CASES)
def test_anything_else_is_bench(addrs):
    """`KMTC`/`KMTS`/`KMTA` 대역이 아니면 모두 벤치다 (운영자 확정 2026-08-13).

    테스트베드는 `192.168.x.x` 를 쓰지 않고, 벤치는 `[node] site` 를 무엇으로
    두더라도 파일명이 `KMTT.…` 여야 한다.
    """
    assert siteid.site_of(addrs)[0] == siteid.BENCH_SITE == 'KMTT'


def test_no_address_at_all_is_bench_not_an_error():
    """네트워크가 없는 노트북도 정상 상황이다 -- 예외를 던지지 않는다."""
    code, why = siteid.site_of(())
    assert code == 'KMTT'
    assert '네트워크' in why


def test_a_site_band_wins_over_other_interfaces():
    """다중 NIC -- 기기망 주소가 하나라도 있으면 그 사이트다.

    관측실 PC 는 보통 기기망 + 캠퍼스망을 함께 갖는다.  하나만 보고 판정하면
    어느 것이 잡히는지가 OS 의 인터페이스 순서에 좌우된다.
    """
    assert siteid.site_of(('10.0.0.5', '192.168.15.42'))[0] == 'KMTA'
    assert siteid.site_of(('192.168.15.42', '10.0.0.5'))[0] == 'KMTA'


def test_detecting_on_this_machine_does_not_raise():
    """실제 호스트에서 돌려도 예외가 없고 네 코드 중 하나가 나온다."""
    code, why = siteid.detect()
    assert code in ('KMTC', 'KMTS', 'KMTA', 'KMTT')
    assert why


def test_local_addresses_never_include_loopback():
    """루프백은 판정 근거가 못 되므로 목록에서 빠진다."""
    assert not [a for a in siteid.local_ipv4s() if a.startswith('127.')]


# -- 판정이 ini 를 이긴다 -------------------------------------------------

def test_ip_detection_overrides_the_declared_site(monkeypatch, caplog):
    """벤치에서 `site=sso` 로 둬도 파일명은 `KMTT.…` 여야 한다.

    운영자 요구사항이다 -- 벤치는 사이트 이름을 `kmtnet-sso`/`kmtnet-ctio` 등
    무엇으로 두더라도 파일명이 `KMTT` 다.  그러려면 **설정 밖에서 오는 신호가
    이겨야** 한다.
    """
    from ics_sim.app import IcsSim
    monkeypatch.setattr(siteid, 'detect', lambda: ('KMTT', '10.0.0.5 (bench)'))
    cfg = make_config(node__site='sso', node__telid='KMTA',
                      node__site_from_ip=True)
    app = IcsSim.__new__(IcsSim)
    app.cfg = cfg
    with caplog.at_level(logging.WARNING):
        site, why = app._resolve_site()
    assert site == 'KMTT', 'IP 판정이 ini 를 이겨야 한다'
    assert any('판정을 따른다' in r.message for r in caplog.records)


def test_matching_ini_and_ip_are_silent(monkeypatch, caplog):
    """둘이 같으면 경고가 없어야 한다 -- 정상 배포가 조용해야 한다."""
    from ics_sim.app import IcsSim
    monkeypatch.setattr(siteid, 'detect',
                        lambda: ('KMTC', '192.168.14.109 in 192.168.14.0/24'))
    cfg = make_config(node__site='ctio', node__telid='KMTC',
                      node__site_from_ip=True)
    app = IcsSim.__new__(IcsSim)
    app.cfg = cfg
    with caplog.at_level(logging.WARNING):
        site, _ = app._resolve_site()
    assert site == 'KMTC'
    assert not [r for r in caplog.records if '판정' in r.message]


def test_switch_off_keeps_the_declared_site(caplog):
    """`site_from_ip=false` 면 ini 를 그대로 쓴다 -- 시험이 이 경로를 쓴다."""
    from ics_sim.app import IcsSim
    cfg = make_config(node__site='ctio', node__telid='KMTC')
    assert cfg.node.site_from_ip is False, 'conftest 가 꺼 두어야 한다'
    app = IcsSim.__new__(IcsSim)
    app.cfg = cfg
    site, why = app._resolve_site()
    assert site == 'KMTC'
    assert '꺼짐' in why


# -- TC 의 TELID 대조 (세 번째 값) ---------------------------------------

def _relay(site_code: str) -> TelemetryRelay:
    relay = TelemetryRelay(SimConfig(), lambda *a, **k: None)
    relay.site_code = site_code
    return relay


def test_telid_mismatch_warns_once_per_value(caplog):
    """`TELID` 가 다르면 경고하되 **같은 값에 대해서는 한 번만**.

    AUXSTATUS 는 노출마다 오므로 매번 경고하면 하룻밤에 1000줄이 된다.  그러면
    사람이 경고를 무시하는 것을 학습하고, 그건 검사가 없는 것보다 나쁘다.
    """
    relay = _relay('KMTC')
    with caplog.at_level(logging.WARNING):
        for _ in range(5):
            relay.check_telid([('TELID', 'KMTS')])
    hits = [r for r in caplog.records if 'TELID' in r.message]
    assert len(hits) == 1, f'{len(hits)}번 경고했다 -- 1번이어야 한다'
    assert 'KMTS' in hits[0].message and 'KMTC' in hits[0].message


def test_an_oscillating_telid_does_not_warn_again(caplog):
    """**"서로 다른 값마다 한 번" 이지 "바뀔 때마다" 가 아니다.**

    `KMTS`(불일치) -> `KMTC`(일치) -> `KMTS`(다시 불일치) 로 오가도 두 번째
    `KMTS` 는 조용해야 한다.  이미 말한 사실을 다시 말할 이유가 없고, TC 를
    재기동하는 동안 값이 오가는 것은 흔하다 -- 그때마다 경고하면 사람이 경고를
    무시하는 것을 학습한다.

    이 시험이 두 해석을 가른다.  구현이 "바뀔 때마다" 로 바뀌면 여기서 걸린다.
    """
    relay = _relay('KMTC')
    with caplog.at_level(logging.WARNING):
        relay.check_telid([('TELID', 'KMTS')])     # 경고 1회
        relay.check_telid([('TELID', 'KMTC')])     # 일치 -- 조용
        relay.check_telid([('TELID', 'KMTS')])     # 되돌아옴 -- 다시 조용해야 한다
    hits = [r for r in caplog.records if 'TELID' in r.message]
    assert len(hits) == 1, (
        f'{len(hits)}번 경고했다 -- 같은 값이 되돌아왔을 때 다시 말하면 안 된다')


def test_a_second_distinct_telid_does_warn(caplog):
    """반대로 **다른 값**이 오면 새로 경고해야 한다 -- 새 사실이니까."""
    relay = _relay('KMTC')
    with caplog.at_level(logging.WARNING):
        relay.check_telid([('TELID', 'KMTS')])
        relay.check_telid([('TELID', 'KMTA')])
    hits = [r for r in caplog.records if 'TELID' in r.message]
    assert len(hits) == 2
    assert 'KMTS' in hits[0].message and 'KMTA' in hits[1].message


def test_pctcs_default_telid_gets_its_own_wording(caplog):
    """`KMTN` 은 "pctcs 설정이 안 됐다" 는 뜻이다 (`pctcs.h:115`).

    사이트 불일치로 말하면 엉뚱한 곳을 보게 된다.
    """
    relay = _relay('KMTC')
    with caplog.at_level(logging.WARNING):
        relay.check_telid([('TELID', 'KMTN')])
    msg = ' '.join(r.message for r in caplog.records)
    assert 'FITS_TELID' in msg and '기본값' in msg


@pytest.mark.parametrize('fields', [
    [('TELID', 'KMTC')],                    # 일치
    [('AUXLINK', 'Up')],                    # TELID 없음 = 정보 없음
    [('TELID', '')],                        # 빈 값
    [],                                     # TC 무응답
])
def test_telid_check_is_silent_when_nothing_is_wrong(caplog, fields):
    """**없는 것은 불일치가 아니다.**  정보가 없는 것과 틀린 것은 다르다."""
    relay = _relay('KMTC')
    with caplog.at_level(logging.WARNING):
        relay.check_telid(fields)
    assert not [r for r in caplog.records if 'TELID' in r.message]


def test_telid_check_is_skipped_when_the_site_is_unknown(caplog):
    """`site_code` 가 비면 대조를 건너뛴다 -- 단위 시험이 relay 를 홀로 만들 때."""
    relay = TelemetryRelay(SimConfig(), lambda *a, **k: None)
    with caplog.at_level(logging.WARNING):
        relay.check_telid([('TELID', 'KMTS')])
    assert not caplog.records


def test_canned_mode_never_feeds_the_telid_check(caplog):
    """canned 모드의 `TELID` 는 **우리 설정을 복사한 값**이라 C 가 될 수 없다.

    `_apply_timeout()` 이 `vals['TELID'] = self.cfg.node.telid` 를 넣는다
    (`telemetry.py:203`).  그걸 C 로 인정하면 **한 출처를 두 번 읽고 "두 출처가
    합의했다" 고 보고**하는 꼴이 된다 -- 불일치보다 거짓 일치가 더 위험하다.

    그래서 `check_telid()` 는 `on_tc_reply()` 에서만 불린다.  이 시험은 그
    배선을 지킨다 -- 종전 시험은 `CANNED_AUX_VALUES` 상수에 `TELID` 가 없는지만
    봤는데, 값이 **동적으로** 주입되므로 통과해도 아무것도 증명하지 못했다.
    """
    relay = _relay('KMTC')
    relay.cfg.node.telid = 'KMTS'          # 우리 설정과 다른 값을 흉내
    relay.cfg.timing.tc_timeout_mode = 'canned'
    with caplog.at_level(logging.WARNING):
        relay._apply_timeout('AUXSTATUS')
    assert not [r for r in caplog.records if 'TELID' in r.message], (
        'canned 경로가 TELID 대조를 건드렸다 -- 거짓 일치의 원천이다')
    # canned 가 채운 값 자체는 남아 있다 (헤더용).  그건 별개 사안이다.
    assert dict(relay.aux_fields).get('TELID') == 'KMTS'


# -- 판정 결과가 실제 파일명까지 흘러가나 ---------------------------------

def test_resolved_site_reaches_the_filename():
    """판정 → `state.site_code` → 파일명 prefix 로 이어져야 한다."""
    for code in ('KMTC', 'KMTS', 'KMTA', 'KMTT'):
        name = rawpair.physical_name(code, '20260813.000001', 'MK')
        assert name.startswith(f'{code}.')
        assert name.endswith('.MK.fits')

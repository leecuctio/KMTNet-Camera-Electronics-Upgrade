#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사이트 판별 -- `[node] observatory` 한 값이 정본이다 (운영자 지시 2026-08-24).

종전에는 `site`/`telid` 두 줄을 따로 적고 `config.validate()` 가 정합을
검사했으며, 그 위에 **호스트 IP 판정(D-015)이 ini 를 이겼다**.  그 구조를
없앴다 -- 이제 `observatory` 에서 `telid`(사이트 코드)와 `site`(`[site.<이름>]`
절 이름)가 **유도**되므로 어긋날 길 자체가 없다.

`telid` 는 AUXSTATUS 응답값이자 실기(ics_archon) raw pair 물리 파일명의
`<SITE>` prefix 이고(raw_fits_spec 2.3절), `observatory` 는 FITS `OBSERVAT`
카드 그 자체다.  즉 이 한 줄이 **파일명·좌표·ORIGIN·INSTRUME 를 함께** 끌고
간다 -- 그래서 모르는 값은 조용히 떨어뜨리지 않고 **기동을 거부**한다.
"""

import pytest

from ics_sim import config, rawhdr, rawpair
from conftest import make_config


@pytest.mark.parametrize('observatory, telid, site', [
    ('CTIO', 'KMTC', 'ctio'),
    ('SAAO', 'KMTS', 'saao'),
    ('SSO', 'KMTA', 'sso'),
    ('TESTBED', 'KMTT', 'testbed'),
])
def test_observatory_drives_site_and_telid(observatory, telid, site):
    """넷뿐인 어휘가 사이트 코드와 `[site.*]` 절을 함께 정한다."""
    code, norm = rawpair.site_of_observatory(observatory)
    assert (code, norm) == (telid, observatory)
    assert rawpair.SITE_SECTION[code] == site
    # 되돌려도 같은 값이어야 한다 -- OBSERVAT 카드가 그 값이다.
    assert rawpair.OBSERVAT[code] == observatory


def test_observatory_is_case_insensitive():
    """ini 손편집 관용 -- 소문자로 적어도 받는다."""
    assert rawpair.site_of_observatory('sso')[0] == 'KMTA'
    assert rawpair.site_of_observatory('  Testbed  ')[0] == 'KMTT'


def test_unknown_observatory_is_rejected_not_downgraded():
    """⚠️ **모르는 값을 테스트베드로 떨어뜨리지 않는다.**

    종전 `normalize_site()` 는 모르는 코드를 조용히 `KMTT` 로 만들었다.
    그 관대함이 위험한 이유는, 관측소 자료가 벤치 이름으로 아카이브에 들어가도
    아무 오류가 안 나기 때문이다.  이제는 기동이 멈춘다.
    """
    with pytest.raises(ValueError):
        rawpair.site_of_observatory('LASILLA')
    with pytest.raises(ValueError):
        rawpair.site_of_observatory('')


def test_validate_rejects_a_hand_broken_combination():
    """필드를 손으로 덮어써 어긋난 조합을 만들면 `validate()` 가 막는다."""
    cfg = make_config()
    cfg.node.observatory = 'SSO'
    cfg.node.telid = 'KMTC'          # 어긋남
    with pytest.raises(config.ConfigError):
        cfg.validate()

    cfg = make_config()
    cfg.node.observatory = 'LASILLA'
    with pytest.raises(config.ConfigError):
        cfg.validate()


def test_instrume_follows_the_site():
    """`INSTRUME` 기본값이 사이트 코드를 따라간다 -- `'<SITE> 18k CCD'`."""
    for observatory, telid in (('CTIO', 'KMTC'), ('SSO', 'KMTA'),
                               ('SAAO', 'KMTS'), ('TESTBED', 'KMTT')):
        code, _ = rawpair.site_of_observatory(observatory)
        assert code == telid
        head = rawhdr.instrument_header('MK', code)
        assert head['INSTRUME'] == f'{telid} 18k CCD'


def test_the_dataclass_default_is_itself_valid():
    """⚠️ **ini 없이 만든 설정도 그대로 통과해야 한다.**

    기본값이 어휘 밖이면 `SimConfig()` 를 바로 쓰는 코드가 기동에서 죽는다 --
    시험은 전부 ini 를 읽으므로 그 결함이 **초록인 채로 숨는다** (2026-08-25
    실측: 기본값이 `KASI` 로 남아 있었고 어휘를 좁힌 뒤에도 아무도 못 잡았다).
    """
    cfg = config.SimConfig()
    assert cfg.node.observatory in rawpair.SITE_OF_OBSERVATORY
    code, _ = rawpair.site_of_observatory(cfg.node.observatory)
    assert cfg.node.telid == code
    assert cfg.node.site == rawpair.SITE_SECTION[code]
    cfg.validate()          # ConfigError 가 나면 실패


def test_loader_derives_and_ignores_stale_keys(tmp_path):
    """ini 의 `observatory` 만 읽고 `site`/`telid` 는 유도한다."""
    ini = tmp_path / 'x.ini'
    ini.write_text('[node]\nobservatory = SAAO\nsite = ctio\ntelid = KMTC\n',
                   encoding='utf-8')
    cfg = config.load(str(ini))
    assert cfg.node.observatory == 'SAAO'
    assert cfg.node.telid == 'KMTS'      # 낡은 telid=KMTC 는 무시된다
    assert cfg.node.site == 'saao'
    cfg.validate()


def test_loader_rejects_an_unknown_observatory(tmp_path):
    ini = tmp_path / 'x.ini'
    ini.write_text('[node]\nobservatory = NOWHERE\n', encoding='utf-8')
    with pytest.raises(config.ConfigError):
        config.load(str(ini))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""site <-> telid 정합 검증 (D-011).

telid 는 AUXSTATUS 응답값이자 실기(ics_archon) raw pair 물리 파일명의
<SITE> prefix 가 되므로, 설정 오배포(예: CTIO ini 를 SAAO 에 배포)는
config.validate() 에서 막혀야 한다 (raw_fits_spec 2.3절).
"""

import pytest

from ics_sim import config
from conftest import make_config


@pytest.mark.parametrize('site, telid', [
    ('ctio', 'KMTC'),
    ('saao', 'KMTS'),
    ('sso', 'KMTA'),
    ('kasi', 'KMTK'),
])
def test_site_telid_pairs_valid(site, telid):
    cfg = make_config()
    cfg.node.site = site
    cfg.node.telid = telid
    cfg.validate()  # ConfigError 가 나면 실패


def test_site_telid_mismatch_rejected():
    """CTIO ini 를 SAAO 에 배포한 상황 -- 기동을 막아야 한다."""
    cfg = make_config()
    cfg.node.site = 'saao'
    cfg.node.telid = 'KMTC'
    with pytest.raises(config.ConfigError):
        cfg.validate()


def test_unknown_site_rejected():
    cfg = make_config()
    cfg.node.site = 'lasilla'
    with pytest.raises(config.ConfigError):
        cfg.validate()


def test_telid_case_insensitive():
    """telid 는 대소문자 무관하게 비교한다 (ini 손편집 관용)."""
    cfg = make_config()
    cfg.node.site = 'sso'
    cfg.node.telid = 'kmta'
    cfg.validate()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide raw FITS 헤더의 **값 공급** -- raw spec v1.9 9·10장.

science 쪽 `ics_sim.rawhdr` 를 최대한 **그대로 부른다** -- 관측소 상수
(`observatory_header`)·노출 블록(`exposure_header`)·HK 포맷(`thermal_header`
와 `format_*`)·나열 카드 규칙(`_join_readings`)은 guide 도 같은 규범이다
(10.2절 "골격 규칙은 science 그대로").  guide 판이 필요한 것만 여기 있다:

* instrument 블록 -- 기하가 guide 다 (10.3절), `CHMAP` 1장 + `IMGROT`
* controller 블록 -- `CTRL1*` 한 벌 + **`ICGBUILD`** (`ICSBUILD` 개명)
* `C1_*` 나열 -- **온도 8자리 · 레일 8자리(`HEATER` +28 V)**,
  `C1_VOLT` 는 **소수 2자리**(반올림 -- 10.4절 명시, science 는 3자리)
"""

from __future__ import annotations

import logging

from ics_archon import _simpath

_simpath.ensure()

from ics_sim import rawhdr  # noqa: E402

from . import build_id      # noqa: E402
from .config import NAXIS1, NAXIS2  # noqa: E402

log = logging.getLogger('icg_archon.guidehdr')

# ---------------------------------------------------------------------------
# 기하 (raw spec 9.3·9.4절 · 10.3절) -- 견본 v0.0 과 값 일치
# ---------------------------------------------------------------------------

#: amp 타일 해부 -- 채널 528 = prescan 0 + active 512 + 다크 기준열 16,
#: 행 1033 = 0 + active 1024 + 9 (store 구간, 위치·성격은 OI-21).
AMPNAX1, AMPNAX2 = 528, 1033
IMAGEX, IMAGEY = 512, 1024
PRESCNX = PRESCNY = 0
OVRSCNX, OVRSCNY = 16, 9
NAMPDET, NAMPRAW = 2, 8
PIXSIZE = 13.0
#: PROVISIONAL -- 하늘 실측 전 (guide OI-22: 0.49 / 0.51 / 0.52 3파전).
#: 견본 v0.0 의 값을 따른다.
PIXSCALE = 0.49
DETECTOR = 'e2v CCD47-20'

#: `CHMAP` -- 칩당 1토큰, 자리 = raw X 블록 순서 (10.3절).  [TBC] -- 토큰
#: 문법·값·칩 방위는 커미셔닝 실측 전이다 (OI-21, 견본 N·E·S·W vs gmon
#: 잠정 n,s,e,w 어긋남).  science `CHMAP_*` 처럼 코드 상수로 둔다 --
#: 배선 사실은 ini 소관이 아니다 (확정은 규격·견본과 함께 움직인다).
CHMAP = 'NRL,ERL,SRL,WRL'
#: `IMGROT` 신설 -- 칩별 회전 [deg, CW], 자리는 `CHMAP` 과 같은 순서.
#: PROVISIONAL -- 값 검증은 커미셔닝 (OI-21).
IMGROT = '270,180,90,0'


def check_geometry() -> None:
    """합 불변식 -- 어긋나면 import 자체가 멈춘다 (rawhdr 와 같은 방식)."""
    assert PRESCNX + IMAGEX + OVRSCNX == AMPNAX1, 'X 합 불변식 (10.3절)'
    assert PRESCNY + IMAGEY + OVRSCNY == AMPNAX2, 'Y 합 불변식 (10.3절)'
    assert AMPNAX1 * NAMPRAW == NAXIS1, '프레임 폭 = amp 폭 x 8 (9.4절)'
    assert AMPNAX2 == NAXIS2, '프레임 높이 = amp 높이 (9.4절)'
    assert len(CHMAP.split(',')) == 4 and len(IMGROT.split(',')) == 4, \
        'CHMAP/IMGROT 는 칩 4 자리다 (10.3절)'


# ---------------------------------------------------------------------------
# 10.4절 자리 표 -- OI-19 종결분 (guide ACF `[SYSTEM]` · modtm_gui 실증)
# ---------------------------------------------------------------------------

#: `C1_TEMP` 8자리 -- Backplane · Mod3 Drv · Mod4 Drv · Mod5 AD · Mod6 AD ·
#: Mod7 HeaterX · Mod9 HVXBias · Mod10 HeaterX.  첫 guide 구동 때 STATUS
#: 재확인만 남는다 (10.4절).
TEMP_MODS = ('BACKPLANE_TEMP', 'MOD3/TEMP', 'MOD4/TEMP', 'MOD5/TEMP',
             'MOD6/TEMP', 'MOD7/TEMP', 'MOD9/TEMP', 'MOD10/TEMP')

#: 전원 레일 8자리 -- 7레일 + guide 전용 `HEATER`(+28 V) (10.4절).
VOLT_RAILS = ('P2V5', 'P5V', 'P6V', 'N6V', 'P17V', 'N17V', 'P35V', 'HEATER')

#: PROVISIONAL -- `HEATER` 레일의 STATUS 필드 이름은 **실기 미확인**이다
#: (규격에 없고 tvm 실측 로그에도 안 보인다).  첫 구동 때 STATUS 원문에서
#: 확정하고 이 후보 목록을 한 줄로 줄일 것.
HEATER_FIELD_CANDIDATES = ('HEATER_V', 'P28V_V', 'HTR_V')


# ---------------------------------------------------------------------------
# 값 블록 -- guide 판
# ---------------------------------------------------------------------------

def instrument_header(site_code: str,
                      cfg_camera: dict | None) -> dict[str, object]:
    """Instrument·Detector 블록 (10.3절) -- 값 카드 21장 몫.

    `cfg_camera` 는 `[camera]` 절 (`SimConfig.camera.as_dict()` 꼴) --
    `instrume`/`camver`/`fpaid` 를 ini 로 덮을 수 있다 (5.0절 "ICS INI 카드").
    `INSTRUME` 기본은 규격 10.3절 초안 `'<SITE코드> Guide CCD'` 다 --
    견본 v0.0 의 `'KMTA 18k CCD'` 는 science 잔재로 등재된 대사 항목이라
    따르지 않는다 (10.2절 "규격이 이긴다", OI-24).
    """
    cam = dict(cfg_camera or {})
    out: dict[str, object] = {
        'INSTRUME': cam.get('instrume') or f'{site_code.upper()} Guide CCD',
        'CAMVER': cam.get('camver', 'CEU-v2.1'),
        # PROVISIONAL -- guide 조립체의 FPAID 귀속은 OI-24 (견본은 science 값).
        'FPAID': cam.get('fpaid', ''),
        'DETECTOR': DETECTOR,
        'DETID': 'G',
        'PIXSIZE': PIXSIZE,
        'PIXSCALE': cam.get('pixscale', PIXSCALE),
        'CCDXBIN': 1, 'CCDYBIN': 1,          # 1x1 전용 (9.3절)
        'NAMPDET': NAMPDET, 'NAMPRAW': NAMPRAW,
        'AMPNAX1': AMPNAX1, 'AMPNAX2': AMPNAX2,
        'IMAGEX': IMAGEX, 'IMAGEY': IMAGEY,
        'PRESCNX': PRESCNX, 'PRESCNY': PRESCNY,
        'OVRSCNX': OVRSCNX, 'OVRSCNY': OVRSCNY,
        'CHMAP': CHMAP, 'IMGROT': IMGROT,
    }
    return out


#: guide 백엔드 이름 -> `DATASRC` (raw spec 5.5절 어휘).
#: **모르는 이름은 `SIM`** -- science `rawhdr._DATASRC` 와 같은 방침이다
#: (실물이라고 잘못 적는 쪽이 훨씬 나쁘다).
_DATASRC_GUIDE = {
    'archon_guide': rawhdr.DATASRC_GUIDE,
    'sim_guide': rawhdr.DATASRC_SIM,
}


def datasrc_of(backend_name: str) -> str:
    """백엔드 이름 -> `DATASRC`.

    ⚠️ **상수로 박으면 안 된다** -- `DATASRC` 는 규격 5.5절이 "시뮬 프레임
    오인을 막는" 카드로 규정한 자리다.  대역(`SimGuideBackend`)이 쓴
    0-프레임이 `ARCHON_GUIDE` 를 달면 그 방어가 통째로 무의미해진다.
    """
    src = _DATASRC_GUIDE.get((backend_name or '').lower())
    if src is None:
        log.warning('guide 백엔드 %r 를 모르므로 DATASRC=%s 로 적는다 -- '
                    '실물이라고 잘못 적는 것보다 낫다 (raw spec 5.5절)',
                    backend_name, rawhdr.DATASRC_SIM)
        return rawhdr.DATASRC_SIM
    return src


def controller_header(info: dict | None, *, cfg_ctrl: dict | None,
                      rdmode: str, backend_name: str) -> dict[str, object]:
    """Controller·ICS 블록 (10.3절) -- `CTRL1*` 한 벌 + `ICGBUILD`.

    science `rawhdr.controller_header()` 를 그대로 부르고 두 가지만 고친다:
    `ICSBUILD` -> **`ICGBUILD`** (키 개명 -- 값 규약은 같다), `CTRL2*` 는
    guide 템플릿에 없어 `render()` 가 버린다 (10.2절 "미수록").
    """
    # 부모에는 `'sim'` 을 준다 -- science 어휘만 아는 `datasrc_of()` 가 guide
    # 이름에 경고를 내기 때문이고, `DATASRC` 는 바로 아래서 guide 판정으로
    # 덮는다 (`datasrc_of` -- 백엔드에서 유도한다).
    pool = rawhdr.controller_header(info or {}, backend_name='sim',
                                    ics_build=build_id(),
                                    cfg_ctrl=cfg_ctrl, rdmode=rdmode)
    pool['ICGBUILD'] = pool.pop('ICSBUILD')
    pool['DATASRC'] = datasrc_of(backend_name)
    return pool


def ctrl_telemetry_header(unit: dict | None) -> dict[str, object]:
    """`C1_TEMP`/`C1_VOLT`/`C1_CURR` -- guide 8자리 (10.4절).

    science 와 다른 곳: 컨트롤러가 하나라 `C2_*` 가 없고, **`C1_VOLT` 는
    소수 셋째 자리에서 반올림한 2자리**다 (10.4절 명시 -- science 는 3자리).
    `C1_CURR` 는 3자리 그대로.
    """
    u = unit or {}
    return {
        'C1_TEMP': rawhdr._join_readings(u.get('temp'), '.1f',
                                         len(TEMP_MODS)),
        'C1_VOLT': rawhdr._join_readings(u.get('volt'), '.2f',
                                         len(VOLT_RAILS)),
        'C1_CURR': rawhdr._join_readings(u.get('curr'), '.3f',
                                         len(VOLT_RAILS)),
    }


def build_pool(*, site_code: str, ctrl_info: dict | None,
               ctrl_telem: dict | None, sensors: dict | None,
               cfg_site: dict | None, cfg_camera: dict | None,
               cfg_ctrl: dict | None, rdmode: str, backend_name: str,
               telem_cards: dict[str, object],
               date_obs: str | None, exptime: float, ledflash_ms: int,
               imgtype: str, objname: str, projid: str, observer: str,
               filename: str, expid: str) -> dict[str, object]:
    """guide 값 풀 -- 카드 조립은 `guidecards.render()` 가 한다.

    조립 순서는 `rawhdr.build_pool()` 과 같다 (TC 중계를 바닥에 깔고 블록을
    얹는다 -- 템플릿이 낯선 키를 걸러 준다).
    """
    pool: dict[str, object] = dict(telem_cards)
    pool['BUNIT'] = 'ADU'
    pool.update(instrument_header(site_code, cfg_camera))
    pool.update(rawhdr.observatory_header(site_code, cfg_site, observer))
    pool.update(rawhdr.exposure_header(imgtype=imgtype, objname=objname,
                                       projid=projid, exptime=exptime,
                                       ledflash_ms=ledflash_ms,
                                       date_obs=date_obs,
                                       filename=filename, expid=expid))
    pool.update(controller_header(ctrl_info, cfg_ctrl=cfg_ctrl,
                                  rdmode=rdmode,
                                  backend_name=backend_name))
    pool.update(rawhdr.thermal_header(sensors))
    pool.update(ctrl_telemetry_header(ctrl_telem))
    # `TIMESYS`/`EXPID` comment 의 ICS -> ICG 는 **템플릿**(guidecards)이
    # 담당한다 -- 값은 science 와 같다.
    return pool


check_geometry()

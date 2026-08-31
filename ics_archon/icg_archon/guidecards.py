#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guide raw FITS 헤더 카드 템플릿 — guide 견본 헤더 v0.0 의 기계 사본.

정본은 `raw_fits_spec/KMTA.20260821.123456.G.fits.header.v0.0.txt`
(raw spec v1.9 **10장** — 값 카드 **123** + COMMENT 8 + END 1 + 공백 12 =
144 레코드 = 4x2880 = 11,520 B).  science 템플릿(`ics_sim/rawcards.py`)과
다른 자리 (10.2절):

* `CTRL2ID`/`CTRL2SN`/`CTRL2CFG` · `C2_TEMP`/`C2_VOLT`/`C2_CURR` **미수록**
  (컨트롤러가 하나다 — "NC 채움" 안은 기각됐다)
* `CHMAP_*` 4장 -> **`CHMAP` 1장** (`'NRL,ERL,SRL,WRL'` [TBC], OI-21)
* **`IMGROT` 신설** (`'270,180,90,0'` [deg, CW] — 자리는 `CHMAP` 과 같은 칩 순서)
* `ICSBUILD` -> **`ICGBUILD`** (+ `TIMESYS`/`EXPID` comment 의 ICS -> ICG)
* `C1_TEMP` **8자리** · `C1_VOLT`/`C1_CURR` **8자리**(`HEATER` +28 V) — 10.4절
* 기하 카드 값이 guide 다 — `NAXIS` 4224x1033 · `AMPNAX` 528/1033 ·
  `OVRSCNX/Y` 16/9 (10.3절)

⚠️ **공유 키 8장의 문자열 패딩 폭이 science 와 다르다** (컨트롤러 블록
24/29 -> **26**, `C1_*` 51 -> **49**) — 그래서 저장은 `fitswrite` 에
`WIDTHS` 를 꽂아야 견본과 바이트가 같아진다 (`fitswrite.card_image`).
의도 여부는 견본 v1.1 승격 대사 때 확인 대상이다.

**이 파일은 손으로 고치지 않는다** — 견본이 개정되면
`tools/gen_guidecards.py` 를 다시 돌려 `CARDS` 를 통째로 갈고,
`tests/test_icg_cards.py` 의 바이트 대사가 표류를 지킨다.

`render()` 의 규칙은 `ics_sim/rawcards.render()` 와 같다 (그 모듈 docstring
참조) — 템플릿만 guide 판이다.  science 쪽을 파라미터화하지 않고 여기 사본을
둔 것은 `ics_sim` 을 무개정으로 두기 위해서다 (guide 는 `ics_sim` 의
소비자이지 개정 주체가 아니다).
"""

from __future__ import annotations

import logging

log = logging.getLogger('icg_archon.guidecards')

# ---------------------------------------------------------------------------
# 견본 v0.0 의 기계 사본 — tools/gen_guidecards.py 생성물 (2026-08-31)
# ---------------------------------------------------------------------------

CARDS: tuple[tuple[str, str, int, str], ...] = (
    ('SIMPLE', 'L', 0, ''),
    ('BITPIX', 'I', 0, ''),
    ('NAXIS', 'I', 0, ''),
    ('NAXIS1', 'I', 0, ''),
    ('NAXIS2', 'I', 0, ''),
    ('BSCALE', 'I', 0, 'PHYSICAL=INTEGER*BSCALE+BZERO'),
    ('BZERO', 'I', 0, ''),
    ('BUNIT', 'S', 18, 'units of physical values'),
    ('COMMENT', '', 0, '  Instrument and Detector Information ________________________________'),
    ('INSTRUME', 'S', 18, 'Instrument Name'),
    ('CAMVER', 'S', 18, 'Camera electronics version'),
    ('FPAID', 'S', 18, 'FPA ID'),
    ('DETECTOR', 'S', 18, 'Detector device model'),
    ('DETID', 'S', 18, 'Detector ID in this raw FITS file'),
    ('PIXSIZE', 'R', 0, 'Unbinned pixel size [microns]'),
    ('PIXSCALE', 'R', 0, 'Unbinned pixel scale [arcsec per pixel]'),
    ('CCDXBIN', 'I', 0, 'CCD X-axis Binning Factor'),
    ('CCDYBIN', 'I', 0, 'CCD Y-axis Binning Factor'),
    ('NAMPDET', 'I', 0, 'Number of amplifiers in the detector'),
    ('NAMPRAW', 'I', 0, 'Number of amplifiers in the raw FITS file'),
    ('AMPNAX1', 'I', 0, 'Columns per amplifier (prescan+image+overscan)'),
    ('AMPNAX2', 'I', 0, 'Rows per amplifier (prescan+image+overscan)'),
    ('IMAGEX', 'I', 0, 'Image columns per amplifier'),
    ('IMAGEY', 'I', 0, 'Image rows per amplifier'),
    ('PRESCNX', 'I', 0, 'Prescan columns per amplifier (side varies)'),
    ('PRESCNY', 'I', 0, 'Prescan rows per amplifier (frame-edge side)'),
    ('OVRSCNX', 'I', 0, 'Overscan columns per amplifier (side varies)'),
    ('OVRSCNY', 'I', 0, 'Overscan rows per amplifier (frame-center side)'),
    ('COMMENT', '', 0, '  Map of CCD output channels, raw X ascending within each card'),
    ('CHMAP', 'S', 18, 'CCD and output channel layout [TBC]'),
    ('IMGROT', 'S', 18, 'Image rotation [deg, CW] for each CCD (N,E,S,W)'),
    ('COMMENT', '', 0, '  Observatory Information ____________________________________________'),
    ('ORIGIN', 'S', 18, 'Location where the data was generated'),
    ('OBSERVAT', 'S', 18, 'Observatory Site'),
    ('TELESCOP', 'S', 18, 'Telescope Name'),
    ('LATITUDE', 'S', 18, 'Site Latitude [deg N]'),
    ('LONGITUD', 'S', 18, 'Site Longitude [deg W]'),
    ('ELEVATIO', 'I', 0, 'Site Elevation [meters]'),
    ('OBSERVER', 'S', 18, 'Observer(s)'),
    ('COMMENT', '', 0, '  Exposure Information'),
    ('PROJID', 'S', 18, 'Project ID'),
    ('IMAGETYP', 'S', 18, 'Type of observation'),
    ('OBJECT', 'S', 18, 'Name of object'),
    ('OBSTYPE', 'S', 18, 'Type of observation'),
    ('EXPTIME', 'I', 0, 'Exposure time [seconds]'),
    ('LEDFLASH', 'I', 0, 'Time to flash projector LEDs [milliseconds]'),
    ('TIMESYS', 'S', 18, 'ICG Time System'),
    ('DATE-OBS', 'S', 23, 'UTC Date and Time at start of obs'),
    ('FILENAME', 'S', 23, 'FITS file name as written to storage'),
    ('EXPID', 'S', 20, 'Exposure identifier assigned by ICG counter'),
    ('COMMENT', '', 0, '  Controller and ICS Information _____________________________________'),
    ('DATASRC', 'S', 26, 'Pixel data source type'),
    ('CTRL1ID', 'S', 26, 'Controller 1 identifier'),
    ('CTRL1SN', 'S', 26, 'Controller 1 serial number'),
    ('CTRL1CFG', 'S', 26, 'Controller 1 Configuration'),
    ('ICGBUILD', 'S', 26, 'ICG software version and build Info'),
    ('RDMODE', 'S', 26, 'Readout mode setting'),
    ('COMMENT', '', 0, '  Camera System House Keeping Data'),
    ('DEWPRES', 'S', 18, 'Dewar pressure [torr]'),
    ('CCDTEMP', 'S', 18, 'CCD temperature [deg C]'),
    ('DMPTEMP', 'S', 18, 'DMP temperature [deg C]'),
    ('PT30N1', 'S', 18, 'PT-30 #1 cold-end temperature [deg C]'),
    ('PT30N2', 'S', 18, 'PT-30 #2 cold-end temperature [deg C]'),
    ('CHARCOAL', 'S', 18, 'Charcoal canister temperature [deg C]'),
    ('WALLBRD', 'S', 18, 'Wallboard temperature [deg C]'),
    ('HEBOX', 'S', 18, 'HE box internal temperature [deg C]'),
    ('C1_TEMP', 'S', 49, 'Ctrl-1 T[C]'),
    ('C1_VOLT', 'S', 49, 'Ctrl-1 V[V]'),
    ('C1_CURR', 'S', 49, 'Ctrl-1 I[A]'),
    ('COMMENT', '', 0, '  TCS Information and Status _________________________________________'),
    ('TCSLINK', 'S', 18, 'TCS Communications Link Status'),
    ('TCSARC', 'S', 18, 'TCS Link Auto Recovery Mode Status'),
    ('TCSQDATE', 'S', 23, 'UTC Date and Time of last TCS query'),
    ('TCSUDATE', 'S', 23, 'UTC Date and Time of last TCS update'),
    ('TCSTIME', 'S', 18, 'TCS Time System'),
    ('RADECSYS', 'S', 18, 'Telescope Coordinate System'),
    ('RA', 'S', 18, 'Telescope RA'),
    ('DEC', 'S', 18, 'Telescope DEC'),
    ('EQUINOX', 'S', 18, 'Coordinate System Equinox'),
    ('HA', 'S', 18, 'Hour Angle at start of obs'),
    ('ST', 'S', 18, 'Local Sidereal Time at start of obs'),
    ('SECZ', 'S', 18, 'Secant of ZD (Airmass) at start of obs'),
    ('ALT', 'S', 18, 'Telescope Altitude (elevation) in degrees'),
    ('AZ', 'S', 18, 'Telescope Azimuth in degrees'),
    ('TCSDRIVE', 'S', 18, 'Telescope Drive Status'),
    ('TELMOVE', 'S', 18, 'Telescope Motion Status'),
    ('DSSTAT', 'S', 18, 'Dome Shutter Status'),
    ('DSUP', 'S', 18, 'Upper Dome Shutter Position'),
    ('DSLW', 'S', 18, 'Lower Dome Shutter Position'),
    ('DSSAF', 'S', 18, 'Dome Shutter Safety Status'),
    ('DSAUTO', 'S', 18, 'Dome Shutter Autosync Status'),
    ('DSALT', 'S', 18, 'Dome Shutter Altitude in degrees'),
    ('DSAZ', 'S', 18, 'Dome Shutter Azimuth in degrees (S to E)'),
    ('DSTELALT', 'S', 18, 'DS-reported telescope altitude'),
    ('DSTELAZ', 'S', 18, 'DS-reported telescope azimuth'),
    ('DALTERR', 'S', 18, 'Dome altitude synchronization error'),
    ('DAZERR', 'S', 18, 'Dome azimuth synchronization error'),
    ('COMMENT', '', 0, '  AUX Information and Status _________________________________________'),
    ('AUXLINK', 'S', 18, 'AUX Control System Comm Link Status'),
    ('AUXARC', 'S', 18, 'AUX Link Auto Recovery Mode Status'),
    ('AUXQDATE', 'S', 23, 'UTC Date and Time of last AUX query'),
    ('AUXUDATE', 'S', 23, 'UTC Date and Time of last AUX update'),
    ('FSSTAT', 'S', 18, 'Filter-Shutter Subsystem Status'),
    ('FILTOP', 'S', 18, 'Filter Operational Status'),
    ('FILNUM', 'S', 18, 'Filter selector position number'),
    ('FILTER', 'S', 18, 'Filter Name in the beam'),
    ('SHUTOP', 'S', 18, 'Shutter Operational Status'),
    ('SHUTTER', 'S', 18, 'Shutter Position'),
    ('FASTAT', 'S', 18, 'Focus Actuator Subsystem Status'),
    ('FAFOCUS', 'S', 18, 'Focus Position Offset in millimeters'),
    ('FATILTNS', 'S', 18, 'Focus Tilt NS Offset Angle in arcsec'),
    ('FATILTEW', 'S', 18, 'Focus Tilt EW Offset Angle in arcsec'),
    ('FAPOSS', 'S', 18, 'South Focus Actuator Position in millimeters'),
    ('FALIMS', 'S', 18, 'South Focus Actuator Limit Status'),
    ('FAPOSE', 'S', 18, 'East Focus Actuator Position in millimeters'),
    ('FALIME', 'S', 18, 'East Focus Actuator Limit Status'),
    ('FAPOSW', 'S', 18, 'West Focus Actuator Position in millimeters'),
    ('FALIMW', 'S', 18, 'West Focus Actuator Limit Status'),
    ('MCSTAT', 'S', 18, 'Mirror Cover Status'),
    ('MCPOS', 'S', 18, 'Mirror Cover Position in percent'),
    ('ENSTAT', 'S', 18, 'Environmental Control System Status'),
    ('ENFAN', 'S', 18, 'Environment System Fan power status'),
    ('ENS1', 'S', 18, 'Environment Sensor 1 in deg C or percent RH'),
    ('ENS2', 'S', 18, 'Environment Sensor 2 in deg C or percent RH'),
    ('ENS3', 'S', 18, 'Environment Sensor 3 in deg C or percent RH'),
    ('ENS4', 'S', 18, 'Environment Sensor 4 in deg C or percent RH'),
    ('ENS5', 'S', 18, 'Environment Sensor 5 in deg C or percent RH'),
    ('ENS6', 'S', 18, 'Environment Sensor 6 in deg C or percent RH'),
    ('ENS7', 'S', 18, 'Environment Sensor 7 in deg C or percent RH'),
    ('FSATEMP', 'S', 18, 'FSA internal temperature in degree C'),
    ('FSAHUM', 'S', 18, 'FSA internal humidity in percent RH'),
)


# ---------------------------------------------------------------------------
# 파생 표 — science `rawcards` 와 같은 유도 규칙
# ---------------------------------------------------------------------------

#: 구조 카드 — 데이터 기하에서 나온다.  `render()` 는 내지 않고 `fitswrite.
#: structural_cards()` 가 guide 기하 값으로 만든다 (comment 는 science 와 같다).
STRUCTURAL = frozenset(
    ('SIMPLE', 'BITPIX', 'NAXIS', 'NAXIS1', 'NAXIS2', 'BSCALE', 'BZERO'))

#: keyword -> 문자열 패딩 폭 — `fitswrite.card_image(widths=...)` 에 꽂는 표.
#: science `_WIDTH` 를 쓰면 공유 키 8장이 견본과 어긋난다 (모듈 docstring).
WIDTHS = {k: w for k, _t, w, _c in CARDS if k != 'COMMENT'}

#: keyword -> 블록 제목 (COMMENT 카드의 본문에서 유도).
SECTION: dict[str, str] = {}
_sec = 'FITS'
for _key, _kind, _width, _comment in CARDS:
    if _key == 'COMMENT':
        _sec = _comment.strip().rstrip('_').strip()
    else:
        SECTION[_key] = _sec
del _sec, _key, _kind, _width, _comment

#: TC 중계(TCS/AUX 블록) 카드 — `telemetry.fits_header_dict()` 가 채울 몫.
#: 규칙은 science 와 같다 — `FSATEMP`/`FSAHUM` 만 예외 (블록은 AUX 지만
#: 출처가 Radionode 라 백엔드 `sensors()` 쪽이 준다, raw spec 5.8절).
RELAY_CARDS = tuple(
    k for k, s in SECTION.items()
    if s in ('TCS Information and Status', 'AUX Information and Status')
    and k not in ('FSATEMP', 'FSAHUM'))

#: 형별 sentinel (raw spec 5.0절) — science 와 동일.
SENTINEL = {'S': 'NC', 'I': -1, 'R': -999.0, 'L': False}


def render(pool: dict[str, object]) -> list[tuple[str, object, str]]:
    """값 풀에서 guide 카드를 템플릿 순서대로 조립한다.

    규칙·귀결은 `ics_sim.rawcards.render()` 와 같다 (그쪽 docstring 참조):
    문자열은 템플릿 폭까지 패딩, 풀 값 `None` 은 카드 미기록, `I` 형은
    소수점 아래 값이 있을 때만 실수형(`EXPTIME` 조건부 형, 5.4절),
    템플릿에 없는 풀 항목은 버린다.
    """
    out: list[tuple[str, object, str]] = []
    for key, kind, width, comment in CARDS:
        if key == 'COMMENT':
            out.append(('COMMENT', comment, ''))
            continue
        if key in STRUCTURAL:
            continue
        if key not in pool:
            log.error('값 풀에 %s 가 없다 -- 10장 전 카드가 필수이므로 우리 '
                      '결함이다. sentinel 로 싣는다 (raw spec 5.0절)', key)
            value: object = SENTINEL[kind]
        else:
            value = pool[key]
        if value is None:
            log.debug('%s 값이 없어 카드를 내지 않는다 (5.0절 -- 변환 실패 '
                      '경로가 발동해야 하는 카드)', key)
            continue
        if kind == 'S':
            text = str(value)
            if len(text) < width:
                text = text.ljust(width)
            out.append((key, text, comment))
            continue
        try:
            if kind == 'I':
                if isinstance(value, float) and not value.is_integer():
                    out.append((key, float(value), comment))
                else:
                    out.append((key, int(value), comment))
            elif kind == 'R':
                out.append((key, float(value), comment))
            else:
                out.append((key, bool(value), comment))
        except (TypeError, ValueError):
            log.error('%s 값 %r 를 %s 형으로 만들 수 없다 -- sentinel 로 '
                      '싣는다 (raw spec 5.0절)', key, value, kind)
            out.append((key, SENTINEL[kind], comment))
    return out


def value_of(cards: list[tuple[str, object, str]], key: str) -> object:
    """조립된 카드 목록에서 값 하나를 꺼낸다 (COMMENT 제외, 첫 일치)."""
    for k, v, _ in cards:
        if k == key:
            return v
    return None

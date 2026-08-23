#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raw spec 5장 헤더 카드 템플릿 — 초안 헤더 v1.0 pair 의 기계 사본.

**5장의 판 근거는 v1.3 이다** -- 현행 규격 문서는 v1.4 지만 그 개정은
1~4장에 그쳤고 5장 이후는 검토 전이다(raw_fits_spec/SMC_CLAUDE.md).

정본은 [`raw_fits_spec/KMTA.20260821.012345.MK.fits.header.v1.0.txt`] (·NT) --
**카드 순서·comment·문자열 패딩까지 바이트 단위 기준**이다 (raw spec 5장
머리말).  이 모듈의 `CARDS` 는 그 견본에서 기계 추출한 것이고, 추출 규칙은
`tests/test_raw_draft.py` 가 견본 파일을 다시 파싱해 대사한다 -- 견본이
개정되면 그 시험이 어긋난 자리를 가리킨다.

**여기는 틀만 있다.**  값의 의미(출처·sentinel·형 변환)는 `rawhdr.py` 가
공급하는 값 풀(pool)의 몫이고, 이 모듈의 `render()` 는 풀에서 템플릿 순서대로
카드를 꺼내 조립만 한다.  템플릿에 없는 풀 항목은 **버려진다** -- 와이어에서
온 낯선 키가 헤더에 스며드는 경로를 구조적으로 없애는 것이다 (구판에서
`SHUTTER` 겹침 사고가 났던 자리).
"""

from __future__ import annotations

import logging

log = logging.getLogger('ics_sim.rawcards')

#: (keyword, 형, 문자열 패딩 폭, comment).  형: 'L' logical · 'I' 정수 ·
#: 'R' 실수 · 'S' 문자열(폭만큼 우측 공백 패딩).  keyword 'COMMENT' 는 블록
#: 구분 카드이고 comment 칸이 본문(9열부터의 원문 그대로)이다.
CARDS: tuple[tuple[str, str, int, str], ...] = (
    ('SIMPLE', 'L', 0, ''),
    ('BITPIX', 'I', 0, ''),
    ('NAXIS', 'I', 0, ''),
    ('NAXIS1', 'I', 0, ''),
    ('NAXIS2', 'I', 0, ''),
    ('BSCALE', 'I', 0, 'PHYSICAL=INTEGER*BSCALE+BZERO'),
    ('BZERO', 'I', 0, ''),
    ('BUNIT', 'S', 18, 'units of physical values'),
    ('COMMENT', '', 0, '  Instrument and Detector Information '
                       '________________________________'),
    ('INSTRUME', 'S', 18, 'Instrument Name'),
    ('CAMVER', 'S', 18, 'Camera electronics version'),
    ('FPAID', 'S', 18, 'FPA ID'),
    ('DETECTOR', 'S', 18, 'Detector device model'),
    ('DETID', 'S', 18, 'Detector pair in this raw FITS file'),
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
    ('COMMENT', '', 0, '  Map of CCD output channels, raw X ascending within '
                       'each card'),
    ('CHMAP_LT', 'S', 31, 'CCD output ch, left-half TOP'),
    ('CHMAP_LB', 'S', 31, 'CCD output ch, left-half BOT'),
    ('CHMAP_RT', 'S', 31, 'CCD output ch, right-half TOP'),
    ('CHMAP_RB', 'S', 31, 'CCD output ch, right-half BOT'),
    ('COMMENT', '', 0, '  Observatory Information '
                       '____________________________________________'),
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
    ('TIMESYS', 'S', 18, 'ICS Time System'),
    ('DATE-OBS', 'S', 23, 'UTC Date and Time at start of obs'),
    ('FILENAME', 'S', 23, 'Filename assigned by ICS'),
    ('ORIGNAME', 'S', 23, 'Original filename assigned by ICS counter'),
    ('COMMENT', '', 0, '  Controller and ICS Information '
                       '_____________________________________'),
    ('DATASRC', 'S', 24, 'Pixel data source type'),
    ('CTRL1ID', 'S', 24, 'Controller 1 identifier'),
    ('CTRL1SN', 'S', 24, 'Controller 1 serial number'),
    ('CTRL1CFG', 'S', 24, 'Controller 1 Configuration file'),
    ('CTRL2ID', 'S', 24, 'Controller 2 identifier'),
    ('CTRL2SN', 'S', 24, 'Controller 2 serial number'),
    ('CTRL2CFG', 'S', 24, 'Controller 2 Configuration file'),
    ('ICSBUILD', 'S', 24, 'ICS/ICG software version and build Info'),
    ('RDMODE', 'S', 24, 'Readout mode setting'),
    ('COMMENT', '', 0, '  Camera System House Keeping Data'),
    ('DEWPRES', 'S', 18, 'Dewar pressure [torr]'),
    ('CCDTEMP', 'S', 18, 'CCD temperature M [deg C]'),
    ('DMPTEMP', 'S', 18, 'DMP temperature [deg C]'),
    ('PT30N1', 'S', 18, 'PT-30 #1 cold-end temperature [deg C]'),
    ('PT30N2', 'S', 18, 'PT-30 #2 cold-end temperature [deg C]'),
    ('CHARCOAL', 'S', 18, 'Charcoal canister temperature [deg C]'),
    ('WALLBRD', 'S', 18, 'Wallboard temperature [deg C]'),
    ('HEBOX', 'S', 18, 'HE box internal temperature [deg C]'),
    ('AIR_IN', 'S', 18, 'Air temperature at heat exchanger inlet [degC]'),
    ('AIR_OUT', 'S', 18, 'Air temperature at heat exchanger outlet [degC]'),
    ('GLYC_IN', 'S', 18, 'Glycol temperature at HE box inlet [degC]'),
    ('GLYC_OUT', 'S', 18, 'Glycol temperature at HE box outlet [degC]'),
    ('C1_TEMP', 'S', 51, 'Ctr-1 T[C]'),
    ('C1_VOLT', 'S', 51, 'Ctr-1 V[V]'),
    ('C1_CURR', 'S', 51, 'Ctr-1 I[A]'),
    ('C2_TEMP', 'S', 51, 'Ctr-2 T[C]'),
    ('C2_VOLT', 'S', 51, 'Ctr-2 V[V]'),
    ('C2_CURR', 'S', 51, 'Ctr-2 I[A]'),
    ('COMMENT', '', 0, '  TCS Information and Status '
                       '_________________________________________'),
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
    # 'Telesope' 는 견본의 원문이다 -- 고치면 바이트 대사가 어긋난다.
    ('ALT', 'S', 18, 'Telesope Altitude (elevation) in degrees'),
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
    ('COMMENT', '', 0, '  AUX Information and Status '
                       '_________________________________________'),
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
    # 'Acutator' 도 견본 원문이다.
    ('FASTAT', 'S', 18, 'Focus Acutator Subsystem Status'),
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

#: 구조 카드 -- astropy 가 데이터에서 만든다 (`fitsout._as_unsigned16`).
#: `render()` 는 이들을 내지 않고, `fitsout` 이 comment 만 템플릿대로 맞춘다.
STRUCTURAL = frozenset(
    ('SIMPLE', 'BITPIX', 'NAXIS', 'NAXIS1', 'NAXIS2', 'BSCALE', 'BZERO'))

#: pair 에서 **반드시 상이**해야 하는 7장 (raw spec 5.9절).  나머지 값 카드는
#: 반드시 동일이다.
PAIR_DIFF = ('DETID', 'CHMAP_LT', 'CHMAP_LB', 'CHMAP_RT', 'CHMAP_RB',
             'FILENAME', 'ORIGNAME')

#: keyword -> 블록 제목 (COMMENT 카드의 본문에서 유도).
SECTION: dict[str, str] = {}
_sec = 'FITS'
for _key, _kind, _width, _comment in CARDS:
    if _key == 'COMMENT':
        _sec = _comment.strip().rstrip('_').strip()
    else:
        SECTION[_key] = _sec
del _sec, _key, _kind, _width, _comment

#: TC 중계(TCS/AUX 블록) 카드 -- `telemetry.fits_header_dict()` 가 채울 몫.
#: `FSATEMP`/`FSAHUM` 만 예외다 -- 블록은 AUX 지만 출처가 Tapaculo(백엔드)라
#: `rawhdr.thermal_header()` 가 준다 (raw spec 5.8절).
RELAY_CARDS = tuple(
    k for k, s in SECTION.items()
    if s in ('TCS Information and Status', 'AUX Information and Status')
    and k not in ('FSATEMP', 'FSAHUM'))

#: 형별 sentinel (raw spec 5.0절).  값 풀이 카드를 아예 빠뜨렸을 때의
#: 최후 방어이기도 하다 -- 그 경우는 우리 결함이므로 에러 로그가 함께 남는다.
SENTINEL = {'S': 'NC', 'I': -1, 'R': -999.0, 'L': False}


def render(pool: dict[str, object]) -> list[tuple[str, object, str]]:
    """값 풀에서 규격 5장 카드를 템플릿 순서대로 조립한다.

    Returns:
        `(keyword, value, comment)` 목록.  `keyword=='COMMENT'` 는 블록 구분
        카드다.  구조 카드(`STRUCTURAL`)는 내지 않는다 -- astropy 가 데이터에서
        만들고 `fitsout` 이 comment 를 맞춘다.

    규칙:
      * 문자열 카드는 템플릿 폭까지 우측 공백 패딩 -- 견본과 바이트 단위로
        같아진다 (raw spec 5장 머리말).
      * 풀 값이 `None` 이면 **카드를 내지 않는다** -- `DATE-OBS` 결측처럼
        "sentinel 로 가리지 말고 변환 실패 경로를 발동시키는" 자리다
        (raw spec 5.0절).
      * `EXPTIME` 은 정수형 기본, 소수점 아래 값이 있을 때만 실수형이다
        (raw spec 5.4절).
      * 템플릿에 없는 풀 항목은 버린다 -- 와이어의 낯선 키가 헤더로 새는
        경로를 없앤다.
    """
    out: list[tuple[str, object, str]] = []
    for key, kind, width, comment in CARDS:
        if key == 'COMMENT':
            out.append(('COMMENT', comment, ''))
            continue
        if key in STRUCTURAL:
            continue
        if key not in pool:
            log.error('값 풀에 %s 가 없다 -- 5장 전 카드가 필수이므로 우리 '
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
                # EXPTIME 조건부 형: 소수점 아래 값이 있으면 실수형 그대로.
                if isinstance(value, float) and not value.is_integer():
                    out.append((key, float(value), comment))
                else:
                    out.append((key, int(value), comment))
            elif kind == 'R':
                out.append((key, float(value), comment))
            else:
                out.append((key, bool(value), comment))
        except (TypeError, ValueError):
            # 헤더 하나 때문에 노출을 망치지 않는다 -- sentinel 로 남기고
            # "값이 이상했다" 는 사실은 에러 로그로 남긴다.
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

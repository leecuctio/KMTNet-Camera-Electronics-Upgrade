#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""규격 5장 헤더 카드 생성 — geometry · detector · controller · 노출 · 사이트.

근거는 [`raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`] 5.3~5.13절이고
결정 기록은 DECISION_LOG **D-013**(레거시 keyword 판정 + 컨트롤러 색인형)이다.
경위는 DevNote 11.14.

**`rawpair.py` 와 나눈 이유.** 그쪽은 *이름*(물리/논리/정본)만 다룬다 -- 파일이
어디에 어떤 이름으로 앉는지가 관심사다.  이 모듈은 *내용*을 다룬다.  둘을 한
파일에 두면 이름 규약을 고치러 온 사람이 200줄짜리 geometry 상수표를 헤치고
들어가야 한다.

**여기 있는 값의 출처는 셋으로 갈린다** (규격 5장 표의 `출처` 칸):

===========  =========================================================
`ACQ`        취득 SW 가 스스로 아는 것.  이 모듈의 상수 · 노출 상태
`SITE`       설치 상수.  geometry · detector · 사이트 측지값
`ARCHON`     컨트롤러만 아는 것.  백엔드가 준다 (`sensors()`,
             `controller_info()`, `voltages()`)
===========  =========================================================

`ICS`(TC 중계) 출처는 `telemetry.py` 몫이라 여기 없다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from .fitsout import FitsStr

log = logging.getLogger('ics_sim.rawhdr')

S = FitsStr

# ---------------------------------------------------------------------------
# 5.3 Raw geometry -- 4장의 배치를 헤더가 스스로 기술한다
# ---------------------------------------------------------------------------
#
# converter 가 자기 하드코딩 상수와 대조해 불일치를 잡을 수 있도록 싣는다
# (규격 5.3절, 변경점 C-5/C-13).  **불변식이 아래 `check_geometry()` 에 있고
# 모듈을 import 할 때 검사한다** -- 상수를 잘못 고치면 그 자리에서 터진다.

RAWNAX1 = 19200          # raw 폭  = NXTILE * RAWXTILE
RAWNAX2 = 9400           # raw 높이 = BOTROWS + MIDOVSCY + TOPROWS
NXTILE = 16              # X 방향 amp tile 수 (chip 2 x strip 8)
NAMPRAW = 32             # 이 파일에 담긴 amp 수 (chip 2 x amp 16)
RAWXTILE = 1200          # amp tile 폭
AMPDATA = 1152           # tile 당 active column
OVERSCNX = 48            # tile 당 local X overscan
PRESCANX = 0
#: strip 1~8 의 overscan 위치 (R=오른쪽, L=왼쪽).
#:
#: **근거는 converter 의 `is_bias_right()` 다** -- 레거시 실측 헤더에는 이 정보가
#: 없다(레거시는 CCD당 amp 8개, strip당 1개, TOP/BOT 분할이 없어 대응물 자체가
#: 없다).  `mef_converter/kmt_ceu_archon_mknt_to_l0_amp_mef_v2_1.py:253-266`:
#:
#:     strip_id(amp)      = ((amp - 1) % 8) + 1     # amp 1..16 -> strip 1..8
#:     is_bias_right(amp) = 1<=amp<=4 or 9<=amp<=12
#:     amp 1..8 = TOP 단, 9..16 = BOT 단
#:
#: -> strip 1~4 = R, strip 5~8 = L, **두 단이 동일** -> 'RRRRLLLL'
#:
#: ⚠️ **converter 는 이 카드를 읽지 않는다.**  자기 `is_bias_right()` 를 쓴다.
#: 그래서 선언과 하드코딩이 갈라져도 변환 쪽에서는 아무것도 잡지 못한다 --
#: amp 절반의 `DATASEC` 에 overscan 이, `BIASSEC` 에 하늘이 들어가고 **오류는
#: 나지 않는다** (변경점 C-5/C-13 이 그 구멍이다).  우리 쪽 방어는
#: `tests/test_geometry_vs_converter.py` 가 converter 를 import 해 맞대는 것이다.
OSCNPATT = 'RRRRLLLL'
NSTRIP = 8               # chip 당 strip 수
NEND = 2                 # strip 당 독출단 (TOP/BOT)
AMPPCD = 16              # chip 당 amp 수 = NSTRIP * NEND
#: strip 번호가 증가하는 방향.  **raw 좌표계 기준**이다.
#:
#: converter 가 `tile0 = base + (strip_id(amp) - 1) * RAW_XTILE` 로 놓으므로
#: 네 chip 모두 +X 다 (`base` 만 다르다 -- M/N=0, K/T=9600).
#:
#: 레거시 amp 헤더의 `CCDSEC` 는 M·T 와 K·N 이 반대 방향인데, 그건 **CCD 기준**
#: 이고 K·N 이 **180° 회전 장착**이라서다(운영자 확인 2026-08-13).  raw 영상에서는
#: 네 chip 다 좌->우 증가가 맞다.  두 좌표계를 섞어 읽으면 "한 값으로 네 chip 을
#: 기술할 수 없다" 는 잘못된 결론이 나온다 -- 실제로 한 번 그렇게 읽었다.
STRIPDIR = '+X'
TOPROWS = 4616
BOTROWS = 4616
MIDOVSCY = 168           # **중앙** Y overscan 총 row 수 -- 가장자리가 아니다
MIDOSCB = 84
MIDOSCT = 84
ROWORDR = 'CCD'
RDDIRT = '-Y'
RDDIRB = '+Y'
CHIPFLP = 'None'
READMODE = '64AMP'
READARCH = '8STRIPx2END'
CCDXBIN = 1
CCDYBIN = 1

#: 폐지한 `OVERSCNY` 를 되살리지 말라는 표시.  레거시는 이 이름으로 **가장자리**
#: Y overscan 을 뜻했고 신규는 overscan 이 **영상 중앙**에 있다(규격 4.2절).
#: 이름을 물려주면 "위쪽 N행 자르기" 도구가 아무 오류 없이 active 픽셀을 지운다
#: -- 규격 5.13절이 이 사례를 폐지 근거로 적어 뒀다.  `MIDOVSCY` 를 쓸 것.
_RETIRED_GEOMETRY = ('OVERSCNY',)


def check_geometry() -> None:
    """규격 5.3·5.4절 불변식.  import 시 1회 검사한다.

    상수를 손보다 어긋나면 **여기서** 터지는 것이 낫다 -- 헤더에 실린 뒤에
    발견하면 그 프레임들은 이미 아카이브에 들어가 있다.
    """
    checks = (
        ('RAWNAX1 = NXTILE * RAWXTILE', RAWNAX1, NXTILE * RAWXTILE),
        ('RAWXTILE = AMPDATA + OVERSCNX + PRESCANX',
         RAWXTILE, AMPDATA + OVERSCNX + PRESCANX),
        ('RAWNAX2 = BOTROWS + MIDOVSCY + TOPROWS',
         RAWNAX2, BOTROWS + MIDOVSCY + TOPROWS),
        ('MIDOVSCY = MIDOSCB + MIDOSCT', MIDOVSCY, MIDOSCB + MIDOSCT),
        ('AMPPCD = NSTRIP * NEND', AMPPCD, NSTRIP * NEND),
        ('NAMPRAW = NXTILE * NEND', NAMPRAW, NXTILE * NEND),
        ('CCDCOLS = NSTRIP * AMPDATA', CCDCOLS, NSTRIP * AMPDATA),
        ('CCDROWS = TOPROWS + BOTROWS', CCDROWS, TOPROWS + BOTROWS),
    )
    for label, got, want in checks:
        if got != want:
            raise ValueError(f'규격 5.3절 불변식 위반 -- {label} '
                             f'({got} != {want})')


def geometry_header() -> dict[str, object]:
    """5.3절 raw geometry 선언 (27장)."""
    return {
        'RAWNAX1': RAWNAX1, 'RAWNAX2': RAWNAX2,
        'NXTILE': NXTILE, 'NAMPRAW': NAMPRAW, 'RAWXTILE': RAWXTILE,
        'AMPDATA': AMPDATA, 'OVERSCNX': OVERSCNX, 'PRESCANX': PRESCANX,
        'OSCNPATT': S(OSCNPATT), 'NSTRIP': NSTRIP, 'NEND': NEND,
        'AMPPCD': AMPPCD, 'STRIPDIR': S(STRIPDIR),
        'TOPROWS': TOPROWS, 'BOTROWS': BOTROWS,
        'MIDOVSCY': MIDOVSCY, 'MIDOSCB': MIDOSCB, 'MIDOSCT': MIDOSCT,
        'ROWORDR': S(ROWORDR), 'RDDIRT': S(RDDIRT), 'RDDIRB': S(RDDIRB),
        'CHIPFLP': S(CHIPFLP),
        'READMODE': S(READMODE), 'READARCH': S(READARCH),
        'CCDXBIN': CCDXBIN, 'CCDYBIN': CCDYBIN,
        'CCDSUM': S(f'{CCDXBIN} {CCDYBIN}'),
    }


# ---------------------------------------------------------------------------
# 5.4 Detector · Camera 구성
# ---------------------------------------------------------------------------

DETECTOR = 'e2v CCD290-99'   # 레거시 실측 헤더와 같은 모델명
CAMNAME = 'KMT-CEU'
CAMVER = 'CEU-v2.1'
DETTYPE = 'SCIENCE'
NCCD = 4                     # 카메라 전체 science CCD
NAMPS = 64                   # 카메라 전체 amp = NCCD * AMPPCD
PIXSIZE = 10.0               # micron
PIXSCALE = 0.395             # arcsec/pixel -- Gaia DR3 실측 (CR-002)

CCDCOLS = 9216               # chip 1개 active column = NSTRIP * AMPDATA
CCDROWS = 9232               # chip 1개 active row = TOPROWS + BOTROWS
COLGAP = 460                 # chip 간 X 간격
ROWGAP = 933                 # chip 간 Y 간격
DETSIZE = (f'[1:{2 * CCDCOLS + COLGAP},1:{2 * CCDROWS + ROWGAP}]')

#: 레거시 계승 (규격 5.4·5.13절).  Archon 3대 중 1대가 guide 전용이라 이 구분이
#: 살아 있다.  이 규격은 `SCIENCE` 만 다루지만, 카드가 있으면 guide raw 가 섞여
#: 들어왔을 때 한 장만 보고 걸러낼 수 있다.
HEMODE_SCIENCE = 'SCIENCE'
HEMODE_GUIDE = 'GUIDE'


def detector_header(instrume: str) -> dict[str, object]:
    """5.4절 detector · camera · mosaic 배치 (16장).

    Args:
        instrume: `[node] telid` (`KMTC`/`KMTS`/`KMTA`/`KMTT`).  레거시 실측
            헤더가 `INSTRUME='KMTS'` 로 사이트 코드를 넣었다.
    """
    return {
        'DETECTOR': S(DETECTOR), 'CAMNAME': S(CAMNAME), 'CAMVER': S(CAMVER),
        'DETTYPE': S(DETTYPE), 'INSTRUME': S(instrume.upper()),
        'HEMODE': S(HEMODE_SCIENCE),
        'NCCD': NCCD, 'NAMPS': NAMPS,
        'PIXSIZE': PIXSIZE, 'PIXSCALE': PIXSCALE,
        'DETSIZE': S(DETSIZE),
        'CCDCOLS': CCDCOLS, 'CCDROWS': CCDROWS,
        'COLGAP': COLGAP, 'ROWGAP': ROWGAP,
    }


# ---------------------------------------------------------------------------
# 5.5 Controller 정체성
# ---------------------------------------------------------------------------

CONTROLL = 'STA ARCHON'
NCTRL = 2                    # **과학** 컨트롤러 수.  guide 는 별개다
CTRLVER = 'ARCHON-v1.0'
TIMCONF = 'CEU_TIM_v1.0'
TIMVER = 'TIM-v1.0'
BIASVER = 'BIAS-v1.0'
CLKVER = 'CLK-v1.0'
WBTYPE = 'STA Differential Board'
ELECSYS = 'KMT-CEU'
SIGELEC = 'STA_DIFF_VIDEO'

#: `DATASRC` 값 (규격 5.5·5.13절, 레거시 계승).  **시뮬 프레임이 실측으로
#: 오인되는 것을 막는 유일한 카드다.**  레거시도 `SIM` 을 유효값으로 뒀다
#: (`*.IC>OBS ERROR: Invalid selection for DataSource. ADC, CTC, and SIM are
#: valid.` -- DevNote 6.4).
DATASRC_REAL = 'ARCHON'
DATASRC_SIM = 'SIM'

#: 백엔드 이름 -> `DATASRC`.  **모르는 백엔드는 `SIM` 으로 떨어뜨린다** --
#: 실물이라고 잘못 적는 쪽이 훨씬 나쁘기 때문이다.
_DATASRC = {'archon': DATASRC_REAL, 'sim': DATASRC_SIM}


def datasrc_of(backend_name: str) -> str:
    src = _DATASRC.get((backend_name or '').lower())
    if src is None:
        log.warning('백엔드 %r 를 모르므로 DATASRC=SIM 으로 적는다 -- 실물이라고 '
                    '잘못 적는 것보다 낫다 (규격 5.5절)', backend_name)
        return DATASRC_SIM
    return src


def controller_header(ctrltag: str, info: dict, *, backend_name: str,
                      ics_build: str) -> dict[str, object]:
    """5.5·5.5.0절 컨트롤러 정체성 + 런타임 상태.

    **정체는 두 대분을 색인형으로, 런타임 상태는 자기 것만 단수형으로 싣는다**
    (D-013).  converter 는 MK 헤더만 읽으므로(`v2_1.py:758`) 색인형이 없으면
    MEF 의 컨트롤러 정체가 전부 `UNKNOWN` 이 된다 -- **오류 없이** 그렇게 된다.

    런타임 상태를 색인형으로 만들지 않은 이유: 보드 온도·독출 시간·오류 플래그는
    노출마다 두 컨트롤러가 실제로 다르다.  MK 헤더에 두 대분 실으면 NT 자신의
    헤더와 어긋날 수 있는 값이 생긴다 (규격 5.12절).

    Args:
        ctrltag: `MK` 또는 `NT`.
        info: 백엔드 `controller_info()` 결과.  `units` 는 색인 순서대로
            (`1`=MK, `2`=NT) `{'id','sn','fw'}` 를 담고, 나머지 키는 이
            컨트롤러의 런타임 상태다.
        backend_name: `DATASRC` 판정용.
        ics_build: `ICSBUILD` -- 레거시 계승 (규격 5.1·5.13절).
    """
    tag = ctrltag.upper()
    idx = 1 if tag == 'MK' else 2
    out: dict[str, object] = {
        'CONTROLL': S(CONTROLL), 'NCTRL': NCTRL,
        'CTRLID': idx,                    # 색인 정수.  CTRL1ID 와 다른 것이다
        'CTRLVER': S(CTRLVER),
        'CTRLSTAT': S(str(info.get('status', 'NC'))),
        'CTRLERR': int(info.get('errorflag', -1)),
        'BCKTEMP': float(info.get('boardtemp', -999.0)),
        'READTIME': float(info.get('readtime', -1.0)),
        'ACFFILE': S(str(info.get('acffile', 'NC'))),
        'TIMCONF': S(TIMCONF), 'TIMVER': S(TIMVER),
        'BIASVER': S(BIASVER), 'CLKVER': S(CLKVER),
        'WBTYPE': S(WBTYPE), 'ELECSYS': S(ELECSYS), 'SIGELEC': S(SIGELEC),
        'DATASRC': S(datasrc_of(backend_name)),
        'NPHLINES': int(info.get('nphlines', -1)),
        'ICSBUILD': S(ics_build),
    }
    if 'frameno' in info:
        out['FRAMENO'] = int(info['frameno'])
    if 'bufno' in info:
        out['BUFNO'] = int(info['bufno'])

    # 5.5.0 -- 색인형은 **양쪽 파일에서 값이 같다** (규격 5.11절 "반드시 동일").
    for n, unit in enumerate(info.get('units', ()), start=1):
        out[f'CTRL{n}ID'] = S(str(unit.get('id', 'NC')))
        out[f'CTRL{n}SN'] = S(str(unit.get('sn', 'NC')))
        out[f'CTRL{n}FW'] = S(str(unit.get('fw', 'NC')))
    return out


# ---------------------------------------------------------------------------
# 5.5.1 amp <-> 전자계통 매핑
# ---------------------------------------------------------------------------

def ampmap_header(mapping: dict[int, tuple[int, int]] | None) -> dict[str, object]:
    """5.5.1절 `AMPMAP` / `AMOD<nn>` / `ACHN<nn>`.

    배선이 converter 의 추정식과 다르면 **crosstalk 보정이 엉뚱한 amp 묶음에
    적용된다** -- 그래서 실제 매핑을 raw 가 실어야 한다.  아직 배선을 모르면
    `AMPMAP='DEFAULT'` 만 싣고 converter 의 추정식을 쓰겠다고 **선언한다.**
    추정식을 쓰면서 아무 말도 안 하는 것과는 다르다.
    """
    if not mapping:
        return {'AMPMAP': S('DEFAULT')}
    out: dict[str, object] = {'AMPMAP': S('EXPLICIT')}
    for nn in range(1, NAMPRAW + 1):
        mod, chan = mapping.get(nn, (-1, -1))
        out[f'AMOD{nn:02d}'] = int(mod)
        out[f'ACHN{nn:02d}'] = int(chan)
    return out


# ---------------------------------------------------------------------------
# 5.6 전압 Telemetry
# ---------------------------------------------------------------------------

#: 최소 기록 항목.  MEF `VOLTINFO` 의 초기 9종과 같다 (규격 5.6절).
VOLT_NAMES = ('VOD', 'VRD', 'VOG', 'VSS', 'VDD',
              'PCLKH', 'PCLKL', 'SCLKH', 'SCLKL')


def voltage_header(volts: list[dict] | None) -> dict[str, object]:
    """5.6절 전압 telemetry 를 색인 keyword 묶음으로.

    측정값이 없으면 `VMEA<n> = -999.0`, `VSTA<n> = 'NC'`,
    `VOLTSTAT = 'PARTIAL'` 이다 (규격 5.6절 말미).  **`0.0` 을 쓰지 않는 이유는
    0 V 가 실재하는 측정값이기 때문이다** -- clock low 는 실제로 0 근처다.

    ⚠️ 이 카드들은 **아직 MEF 에 도달하지 않는다.** converter 의
    `volt_rows()` 가 헤더 인자를 받지 않고 하드코딩 placeholder 를 돌려준다
    (`v2_1.py:723-727`, 변경점 C-18).  raw 는 아카이브 기록으로서 싣는다.
    """
    rows = volts if volts else [{'name': n} for n in VOLT_NAMES]
    out: dict[str, object] = {'VOLTN': len(rows)}
    measured = 0
    for n, row in enumerate(rows, start=1):
        mea = row.get('measured')
        out[f'VOLT{n}'] = S(str(row.get('name', 'NC')))
        out[f'VSET{n}'] = float(row.get('setpoint', -999.0))
        out[f'VMEA{n}'] = float(mea) if mea is not None else -999.0
        out[f'VUNI{n}'] = S(str(row.get('unit', 'V')))
        out[f'VSTA{n}'] = S(str(row.get('status', 'NC')))
        if mea is not None:
            measured += 1
    if measured == len(rows):
        out['VOLTSTAT'] = S('OK')
    elif measured:
        out['VOLTSTAT'] = S('PARTIAL')
    else:
        out['VOLTSTAT'] = S('UNKNOWN')
    return out


# ---------------------------------------------------------------------------
# 5.7 시각 · 노출
# ---------------------------------------------------------------------------

def _hms(when: datetime | None) -> str:
    """`TSHOPEN`/`TSHSHUT` 형식 (`'14:23:25.467'`)."""
    if when is None:
        return 'NC'
    return when.strftime('%H:%M:%S.') + f'{when.microsecond // 1000:03d}'


def _mjd(when: datetime) -> float:
    """UTC datetime -> MJD.  배정밀도로 기록한다 (규격 5.7절).

    stdlib 만 쓴다 -- Julian day 는 정수 산술로 정확히 얻을 수 있으므로
    astropy 를 끌어올 이유가 없다.
    """
    u = when.astimezone(timezone.utc)
    y, m = u.year, u.month
    if m <= 2:
        y, m = y - 1, m + 12
    a = y // 100
    b = 2 - a + a // 4
    jd0 = (int(365.25 * (y + 4716)) + int(30.6001 * (m + 1))
           + u.day + b - 1524.5)
    frac = (u.hour * 3600 + u.minute * 60 + u.second
            + u.microsecond / 1e6) / 86400.0
    return jd0 + frac - 2400000.5


def exposure_header(*, date_obs: str, exp_start: datetime | None,
                    exp_end: datetime | None, exptime: float,
                    darktime: float, ledflash_ms: int,
                    exp_measured: float | None = None) -> dict[str, object]:
    """5.7절 시각 · 노출.

    **`DATE-OBS` 는 `telemetry.fits_header_dict()` 가 이미 싣는다** -- 여기서는
    같은 순간의 `MJD-OBS`/`UT` 를 파생시키고 셔터 시각을 붙인다.  파생을 한
    자리에 모아 둔 이유는 세 값이 어긋나지 않게 하는 것이다.

    `LEDFLASH` 는 **초** 단위다 (규격 5.7·5.13절).  ICS 내부는 ms 이므로
    나눠서 싣는다 -- 레거시와 같은 이름에 다른 단위를 넣으면 기존 도구가
    조용히 1000배 틀린 값을 읽는다.

    **`SHUTTER` 는 여기서 만들지 않는다** (2026-08-13 확정).  그 이름은 AUX 가
    보고한 **블레이드 위치**이고 `telemetry.py` 몫이다(규격 5.10절).  한때 이
    함수가 "이 노출이 셔터를 썼나" 를 같은 이름으로 실었는데, 그건

      * **이름이 같고 뜻이 다른 것**이라 -- `OVERSCNY` 를 폐지한 근거와 같은
        부류다.  레거시 실측은 `IMAGETYP='OBJECT'`·`EXPTIME=30` 프레임에
        `SHUTTER='CLOSED'`(질의 시점 블레이드)를 남겼다.
      * merge order 때문에 **AUX 값을 조용히 덮었고**,
      * `IMAGETYP` 에서 파생되는 값이라 **애초에 중복**이었다.

    셔터를 쓰는 노출인지는 `IMAGETYP`(`BIAS`/`DARK` 는 열지 않는다)에서 읽는다.
    """
    out: dict[str, object] = {
        'EXPTIME': float(exptime),
        'DARKTIME': float(darktime),
        'LEDFLASH': round(ledflash_ms / 1000.0, 3),
        'TSHOPEN': S(_hms(exp_start)),
        'TSHSHUT': S(_hms(exp_end)),
    }
    if exp_start is not None:
        out['MJD-OBS'] = _mjd(exp_start)
        # **`UT` 카드는 두지 않는다** (운영자 확정 2026-08-13).  `DATE-OBS` 가
        # 날짜와 시각을 밀리초까지 담으므로 완전한 중복이었다.  레거시가 둘 다
        # 실었던 것은 `UT` 에 `TSHOPEN`(백분초)을 붙여 정밀도를 보태려던 것이고,
        # `DATE-OBS` 가 밀리초를 갖는 지금은 이유가 없다.
        #
        # **converter 는 영향받지 않는다** -- MEF 의 `UT` 는 raw 의 `UT` 가 아니라
        # `DATE-OBS` 의 날짜부 + raw 의 `TSHOPEN` 으로 조립된다
        # (`v2_1.py:440,583`).  둘 다 그대로 싣고 있다.
    else:
        # 규격 5.0절 -- 결측이면 카드를 넣지 않는다.  "지금" 으로 채우면
        # 값이 있는 것처럼 보이고 converter 의 실패 경로가 발동하지 않는다.
        log.error('exp_start 가 없어 MJD-OBS/UT 를 만들 근거가 없다 -- 카드를 '
                  '넣지 않는다 (규격 5.0·5.7절, C-6)')
    if exp_measured is not None:
        out['EXPMEAS'] = float(exp_measured)
    return out


# ---------------------------------------------------------------------------
# 5.8 관측 식별
# ---------------------------------------------------------------------------

def observation_header(*, imgtype: str, objname: str, projid: str,
                       observer: str, fieldid: str = '') -> dict[str, object]:
    """5.8절 관측 식별.

    `IMAGETYP` 은 **대문자** 통제 어휘다 -- L1 파이프라인의 master frame
    생성기가 `BIAS`/`FLAT`/`OBJECT` 를 문자열 비교로 검사한다.

    `FILTER`/`FILNUM` 은 AUX 중계값이라 `telemetry.py` 몫이다.
    """
    kind = (imgtype or 'OBJECT').upper()
    return {
        'IMAGETYP': S(kind),
        'OBSTYPE': S(kind),
        'OBJECT': S(objname or 'NC'),
        'FIELDID': S(fieldid or objname or 'NC'),
        'PROJID': S(projid or 'NC'),
        'OBSERVER': S(observer or 'NC'),
    }


# ---------------------------------------------------------------------------
# 5.9 관측소 -- 측지값
# ---------------------------------------------------------------------------
#
# **좌표를 코드에 박지 않는다.**  레거시 실측본으로 확인된 것은 SSO 뿐이고
# (`LATITUDE='-31:16:24'` `LONGITUD='210:56:08'` `ELEVATIO=1150`,
# `TELESCOP='KMTNet 1.6m #3'`), CTIO/SAAO 값은 이 저장소 어디에도 없다.
# 추측한 좌표를 아카이브 헤더에 박으면 규격 6.2절이 경계하는 "조용히 틀린 값"
# 그 자체가 된다 -- 겉보기엔 유효한 좌표라 아무도 의심하지 않는다.
#
# 그래서 `[site]` 설정으로 받고, 설정이 없으면 sentinel 을 싣는다.
# 미확인 상태는 규격 OI-11 로 남겼다.

#: 사이트별 측지값.  **운영자가 세 사이트 실측값을 확인해 줬다 (2026-08-13)** --
#: 그전에는 SSO 하나만 알고 있어서 나머지는 sentinel 이었다.
#:
#: **`LONGITUD` 는 서경(`[deg W]`) 양수다.**  세 사이트 값으로 규약이 확인된다:
#:
#:     CTIO  +70:48:14.39  =  70.804 W   (동경 -70.804)
#:     SAAO   339:11:22    = 339.189 W   (동경 +20.810)
#:     SSO    210:56:08    = 210.936 W   (동경 +149.064)
#:
#: CTIO 만 90 미만이라 `+` 부호가 붙고 나머지는 0~360 이라 형태가 달라 보이지만
#: **규약은 같다.**  다음 사람이 "왜 339도?" 하고 동경으로 고치면 부호가 뒤집힌
#: 좌표가 아카이브에 영구히 박힌다 -- 겉보기엔 유효한 좌표라 아무도 의심하지
#: 않는다 (규격 OI-11).  형식(초의 소수점 자리, `+` 부호 유무)도 사이트마다
#: 다르지만 **운영자가 준 문자열을 그대로 싣는다** -- 정규화하면 레거시
#: 아카이브와 문자열 비교가 깨진다.
#:
#: `TELESCOP` 의 `#1`/`#2`/`#3` 은 사이트에 대응한다 (CTIO/SAAO/SSO).
#:
#: ⚠️ **`[site]` 설정이 있으면 그쪽이 이긴다** -- 현장이 정본이다.  이 표는
#: 설정이 없을 때(단위 시험·최초 배포)의 기본값이다.
VERIFIED_SITES = {
    'KMTC': {'latitude': '-30:10:01.84', 'longitud': '+70:48:14.39',
             'elevatio': 2140, 'telescop': 'KMTNet 1.6m #1'},
    'KMTS': {'latitude': '-32:22:42', 'longitud': '339:11:22',
             'elevatio': 1800, 'telescop': 'KMTNet 1.6m #2'},
    'KMTA': {'latitude': '-31:16:24', 'longitud': '210:56:08',
             'elevatio': 1150, 'telescop': 'KMTNet 1.6m #3'},
    # KMTT(테스트베드)는 실재 좌표가 없다.  일부러 비워 둔다 -- 아무 좌표나
    # 넣으면 시험 산출물이 실제 관측처럼 보인다.
}


def site_header(site_code: str, cfg_site: dict | None = None) -> dict[str, object]:
    """5.9절 관측소 측지값.

    Args:
        site_code: `KMTC`/`KMTS`/`KMTA`/`KMTT`.
        cfg_site: `[site]` 설정.  주어지면 실측 표보다 **우선한다** -- 현장이
            정본이기 때문이다.
    """
    code = site_code.upper()
    vals = dict(VERIFIED_SITES.get(code, {}))
    if cfg_site:
        vals.update({k: v for k, v in cfg_site.items() if v not in ('', None)})
    if not vals:
        log.warning('사이트 %s 의 측지값이 없다 -- LATITUDE/LONGITUD/ELEVATIO 를 '
                    'sentinel 로 싣는다. [site] 설정으로 넣어 줄 것 (규격 5.9절, '
                    'OI-11)', code)
    return {
        'SITEID': S(code),
        'TELESCOP': S(str(vals.get('telescop', 'NC'))),
        'LATITUDE': S(str(vals.get('latitude', 'NC'))),
        'LONGITUD': S(str(vals.get('longitud', 'NC'))),
        'ELEVATIO': int(vals.get('elevatio', -1)),
        'RADECSYS': S('ICRS'),
    }


# ---------------------------------------------------------------------------
# 5.10 열 · 듀어
# ---------------------------------------------------------------------------
#
# 레거시 raw 헤더에서 이 값들은 `ENS7` **뒤에** 있고 AUX 텔레메트리 필드
# 집합에는 없다 -- 즉 각 IC 가 자기 듀어 RTD 를 직접 읽었다.  신규는 Archon 이
# 읽으므로 **백엔드에서 온다** (`sensors()`).  TC 중계가 아니다.

#: 듀어·HK 센서 카드 -- 확정 초안 v0.3.5 의 수록 순서.  일곱은 레거시 이름
#: 계승이고(규격 5.13절), `DMPTEMP`/`WALLBRD`/`HEBOX` 는 HK 재구성 신설이다
#: (운영자 확정 2026-08-21, Header_and_Refs v1.8 3.7절·7장).  `WALLBRD` 는
#: wallboard 의 모음 탈락 축약 -- 8자 절단형 `WALLBOAR`(초안 v0.3.4)를 대체했다.
#: `DEWPRES` 는 형과 표기가 달라 따로 다룬다.
DEWAR_CARDS = ('DMPTEMP', 'PT30N1', 'PT30N2', 'CHARCOAL', 'WALLBRD', 'HEBOX',
               'AIR_IN', 'AIR_OUT', 'GLYC_IN', 'GLYC_OUT')

#: 측정 불가를 뜻하는 `DEWPRES` 값 (운영자 확정 2026-08-21).
DEWPRES_NC = '9.99e-9'

#: 측정으로 인정하는 압력 범위 [torr].
#:
#: **하한은 게이지 실측 하한으로 확인해야 한다.**  이 하한이 sentinel 보다
#: 커야 `9.99e-9` 가 정상값과 겹치지 않는다 -- 지금은 그 성질이 이 두 상수에
#: 걸려 있다.  게이지가 `9.99e-9` 아래를 실제로 읽어낸다면 sentinel 을 바꿔야
#: 한다.
DEWPRES_MIN = 1.0e-8
DEWPRES_MAX = 1.0e+3


def format_dewpres(value: object) -> str:
    """`DEWPRES` 를 `1.23e-4` 꼴 문자열로 만든다 (단위 [torr]).

    **왜 문자열인가.**  FITS 실수 카드의 표기는 우리가 고를 수 없다 -- astropy
    가 크기를 보고 정하므로 `1.23e-4` 를 넣어도 `0.000123` 으로 적힌다.  지수
    표기를 규격으로 못박으려면 문자열 카드여야 한다.  레거시도 듀어·온도 카드를
    전부 문자열로 실었으므로(`DEWPRES = 'N/A'`, `CCDTEMP = '-103.16'`) 형까지
    계승이다.

    **측정 불가는 하나로 모은다** (`9.99e-9`) -- 값이 없거나, `0` 이거나 음수,
    유한하지 않거나, 게이지가 숫자가 아닌 것을 돌려주거나, 인정 범위를 벗어난
    경우다.  범위 밖을 sentinel 로 떨어뜨리는 것은 **게이지 이상값이 정상 측정
    으로 읽히는 것을 막으려는 것**이다.
    """
    if value is None:
        # 게이지를 못 읽은 것은 시뮬에서 정상 경로다 -- 노출마다 경고하지 않는다.
        log.debug('DEWPRES 를 못 읽었다 -- %s 로 싣는다', DEWPRES_NC)
        return DEWPRES_NC
    try:
        p = float(value)
    except (TypeError, ValueError):
        log.warning('DEWPRES 게이지 값이 수치가 아니다(%r) -- %s 로 싣는다',
                    value, DEWPRES_NC)
        return DEWPRES_NC
    if p != p or p in (float('inf'), float('-inf')):
        log.warning('DEWPRES 가 유한하지 않다(%r) -- %s 로 싣는다',
                    p, DEWPRES_NC)
        return DEWPRES_NC
    if p <= 0.0:
        log.warning('DEWPRES 가 %r 이다 -- 게이지 미연결/미독출로 보고 %s 로 '
                    '싣는다', p, DEWPRES_NC)
        return DEWPRES_NC
    if not DEWPRES_MIN <= p <= DEWPRES_MAX:
        log.warning('DEWPRES %r torr 가 인정 범위 [%g, %g] 밖이다 -- 게이지 '
                    '이상으로 보고 %s 로 싣는다',
                    p, DEWPRES_MIN, DEWPRES_MAX, DEWPRES_NC)
        return DEWPRES_NC
    mantissa, _, exponent = f'{p:.2e}'.partition('e')
    # `1.23e-04` 의 지수 앞 0 을 떼어 `1.23e-4` 로 만든다
    return f'{mantissa}e{exponent[0]}{exponent[1:].lstrip("0") or "0"}'


def thermal_header(sensors: dict | None) -> dict[str, object]:
    """5.10절 HK -- 대표 chip 온도 + 듀어·환경 센서.

    **`CCDTEMP` 는 실측 대표 센서 1개의 값이다** (운영자 확정 2026-08-21,
    v1.7_revision -- Header_and_Refs v1.8 3.7절).  종전의 "두 chip 온도의
    평균"(2026-08-13, D-013)은 온도센서 구성이 바뀌면서 폐기됐고
    `CCDTEMP1`/`CCDTEMP2` 카드도 후보에서 제외됐다.  대표 센서는 백엔드
    `ccdtemp1`(파일 첫 chip 쪽 -- 초안 comment "CCD temperature M")이고,
    **죽었을 때 이웃 센서(`ccdtemp2`)로 대체하지 않는다** -- 대표가 아닌 값을
    대표라고 적으면 조용히 틀린 값이 된다.

    `CCDTEMP` 는 **반드시 있어야 한다** -- L1 파이프라인이 이 이름을 지정해
    L1 primary 로 전달한다 (`mef_pipeline/kmt_ceu_preproc/io_l1.py` 의
    `CARRY_KEYS`).  그래서 대표 센서를 못 읽었을 때도 카드를 비우지 않고
    sentinel `-999.0` 으로 싣고 경고를 남긴다.

    MEF/L1 쪽 정의 문구("평균 파생")의 갱신은 LEECU 몫의 C-항목이다
    (`raw_fits_spec/KMT_CEU_Raw_Header_Review_MEF_Impacts_v0.3.md` ②).
    """
    s = sensors or {}
    t1 = s.get('ccdtemp1', s.get('ccdtmp1'))
    if t1 is None:
        log.warning('대표 chip 온도(ccdtemp1)를 못 읽었다 -- CCDTEMP 를 '
                    'sentinel(-999.0)로 싣는다. 이웃 센서로 대체하지 않는다 '
                    '(대표가 아닌 값을 대표라고 적으면 조용히 틀린 값이 된다)')
    out: dict[str, object] = {
        # 압력만 문자열이다 -- 지수 표기를 규격으로 고정하려면 그래야 한다
        # (`format_dewpres` 의 docstring).  온도의 형(초안=문자열, 여기=실수)은
        # 미확정이다 -- v1.8 확인 요망 9.
        'DEWPRES': S(format_dewpres(s.get('dewpres'))),
        'CCDTEMP': float(t1) if t1 is not None else -999.0,
    }
    for card in DEWAR_CARDS:
        v = s.get(card.lower())
        out[card] = float(v) if v is not None else -999.0
    return out


# ---------------------------------------------------------------------------
# 조립
# ---------------------------------------------------------------------------

def spec_header(*, ctrltag: str, site_code: str, backend_name: str,
                ics_build: str, ctrl_info: dict, sensors: dict | None,
                volts: list[dict] | None, ampmap: dict | None,
                cfg_site: dict | None,
                date_obs: str, exp_start: datetime | None,
                exp_end: datetime | None, exptime: float, darktime: float,
                ledflash_ms: int,
                exp_measured: float | None,
                imgtype: str, objname: str, projid: str, observer: str,
                fieldid: str = '') -> dict[str, object]:
    """규격 5.3~5.10절 카드를 한 번에.

    `rawpair.identity_header()`(5.1·5.2)와 `telemetry.fits_header_dict()`
    (5.9 pointing · 5.10 AUX 중계)는 별도로 얹는다 -- 출처가 달라서다.
    """
    out: dict[str, object] = {}
    out.update(geometry_header())
    out.update(detector_header(site_code))
    out.update(controller_header(ctrltag, ctrl_info,
                                 backend_name=backend_name,
                                 ics_build=ics_build))
    out.update(ampmap_header(ampmap))
    out.update(voltage_header(volts))
    out.update(exposure_header(date_obs=date_obs, exp_start=exp_start,
                               exp_end=exp_end, exptime=exptime,
                               darktime=darktime,
                               ledflash_ms=ledflash_ms,
                               exp_measured=exp_measured))
    out.update(observation_header(imgtype=imgtype, objname=objname,
                                 projid=projid, observer=observer,
                                 fieldid=fieldid))
    out.update(site_header(site_code, cfg_site))
    out.update(thermal_header(sensors))
    return out


check_geometry()

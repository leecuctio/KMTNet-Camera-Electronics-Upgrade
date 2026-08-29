#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raw spec 5장 헤더의 **값 공급** — instrument·detector·노출·컨트롤러·HK.

근거는 [`raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.8.md`] 4·5장이고
결정 기록은 D-013(레거시 판정) · D-016(충돌·정체성).  카드의 **순서·comment·
패딩(틀)**은 `rawcards.py` 템플릿이 갖고, 이 모듈은 그 틀에 부을 **값**을
출처별 블록 함수로 만든다.  경위는 DevNote 11.14(구판 구현) · 11.19(v1.3 정렬).

**`rawpair.py` 와 나눈 이유.** 그쪽은 *이름*(파일명·번호·충돌 처리 D-016)만
다룬다.  이 모듈은 *내용*을 다룬다.

**값의 출처** (raw spec 5장 표의 `출처` 칸):

===============  ========================================================
`ICS INI`        설정에서.  `[camera]` `[controllers]` `[site]` --
                 **전부 ini 에서 수정 가능해야 한다** (운영자 지시 2026-08-22)
`ICS code`       취득 SW 가 스스로 아는 것.  이 모듈의 상수 · 노출 상태
`Archon`         컨트롤러만 아는 것.  백엔드가 준다 (`controller_info()`,
                 `controller_telemetry()`)
HK 3계통         `ICG RTD` / `standalone RTD` / `Tapaculo` -- 백엔드
                 `sensors()` 가 모아 준다
=============== ========================================================

`TCS relay`/`AUX relay` 출처는 `telemetry.py` 몫이라 여기 없다
(`rawcards.RELAY_CARDS`).  예외는 `FSATEMP`/`FSAHUM` -- 블록은 AUX 지만
출처가 Tapaculo(백엔드)라 이 모듈이 준다 (raw spec 5.8절).
"""

from __future__ import annotations

import logging

from . import rawcards

log = logging.getLogger('ics_sim.rawhdr')

# ---------------------------------------------------------------------------
# 3·4장 — 파일 구조 · raw geometry (헤더 5.2절 값의 원천)
# ---------------------------------------------------------------------------
#
# 구판의 geometry **선언 카드 27장**(RAWNAX1 OSCNPATT ROWORDR RDDIRT/B …)은
# v1.3 에서 전량 폐지됐다 -- 배치는 **4.3 포장 규범 조항**(문서)과 아래 상수
# (코드)가 정하고, 헤더에는 5.2절의 타일 해부 카드만 싣는다 (raw spec 5.10절,
# 원장 7장).  선언과 하드코딩이 갈라지는 것을 막던 방어는
# `tests/test_geometry_vs_converter.py`(코드-대-코드 대조)가 그대로 맡는다.

RAW_NAXIS1 = 19200       # raw 폭  = NXTILE * AMPNAX1
RAW_NAXIS2 = 9400        # raw 높이 = 2 * AMPNAX2
NXTILE = 16              # X 방향 amp tile 수 (chip 2 x strip 8)

NAMPDET = 16             # detector 당 amp 수
NAMPRAW = 32             # 이 파일의 amp 수 (chip 2 x amp 16)
AMPNAX1 = 1200           # amp tile 폭  = PRESCNX + IMAGEX + OVRSCNX
AMPNAX2 = 4700           # amp tile 높이 = PRESCNY + IMAGEY + OVRSCNY
IMAGEX = 1152
IMAGEY = 4616
PRESCNX = 0              # 레거시 `PRESCANX`(27, 레지스터 pre-scan)의 **키워드
PRESCNY = 0              # 변경 계승** -- 신규는 prescan 을 기록하지 않는다
OVRSCNX = 48             # side varies (4.1절 X overscan 패턴)
OVRSCNY = 84             # ⚠️ **frame-center side** -- 레거시 `OVERSCNY`(가장자리,
                         # 값 0)와 뜻이 달라 이름을 갈랐다 (raw spec 4.2절)
CCDXBIN = 1              # 1x1 전용, 2·3 은 reserved (OI-5)
CCDYBIN = 1

#: X overscan 의 좌우 패턴 (raw spec 4.1절) -- strip 1–4 = 오른쪽 48,
#: strip 5–8 = 왼쪽 48.  **카드가 아니다** (`OSCNPATT` 폐지, 4.3 포장 규범
#: 조항으로 이관).  converter `is_bias_right()` 와의 코드-대-코드 대조
#: (`test_geometry_vs_converter.py`)에 쓴다.
#:
#: ✅ **확정됐다** (raw spec v1.4, 2026-08-22): 실제 획득 자료 육안 확인으로
#: `RRRRLLLL` 이 맞았다 -- **OI-15 종결.**  레거시 MEF `AMPSEC` 의 M/T=5:3 ·
#: K/N=3:5 패턴과 상충한다고 보던 경고는 걷혔다(그쪽은 CCD 기준 표기였다).
XOSC_PATTERN = 'RRRRLLLL'

#: 검출기 상수 (부록 A -- e2v CCD290-99 데이터시트 대응 확인).
PIXSIZE = 10.0           # [micron]
PIXSCALE = 0.395         # [arcsec/px], Gaia DR3 실측 갱신값
DETECTOR = 'e2v CCD290-99'

#: `ICS INI` 카드의 코드 기본값 -- ini 가 비어 있을 때 쓴다 (raw spec 5.2·5.5절).
CAMVER = 'CEU-v2.1'      # **HW·성능상 변경이 있을 때만 올린다** -- 포장 규범
                         # 조항(4.3)의 고정 대상 = CAMVER + CTRLxCFG
#: ⚠️ `FPAID` 는 이제 **사이트가 정한다** -- 정본은 `VERIFIED_SITES` 와
#: `fpaid_of()` 이고 모듈 상수는 두지 않는다 (raw spec 5.3.1절, D-017 항목 6).
RDMODE = 'NORMAL'

#: `CHMAP_*` 4장 (raw spec 4.5절 amp 전수 표의 투영, pair 상이).
#: 기계 가독 정본은 `raw_fits_spec/Detector_Ch_to_AmpID_Map_v1.1.txt`.
#: 값 = CCD 출력 채널, raw X 오름차순.  **TOP/BOT 대역이 chip 마다 반대**인
#: 것이 실배선이다 (M: TOP=16→09 / K: TOP=08→01 등) -- converter 추정식과
#: 다르므로 MEF 쪽 재정의가 C-11 이다.
#:
#: **토큰은 4자 `<chip><A|D><nn>` 이다** (운영자 확정 2026-08-25, raw spec v1.5
#: 4.5·5.2절).  가운데 글자는 **채널 번호가 정한다** -- `01`–`08` = `A` ·
#: `09`–`16` = `D` (e2v image section, 부록 A: 채널 번호 = OS 번호 = 아래/위
#: half).  종전 3자 표기(`M16`)를 대체했고, 기계 정본도 v1.1 에서 같은 판정으로
#: `B-BOT` 을 `D-BOT` 으로 고쳤다 (OI-17 잔여 ①·② 종결).
#:
#: ⚠️ 가운데 글자를 chip 이나 사분면에서 유추하지 말 것 -- **번호만이 정한다.**
#: 같은 chip 안에서 `MD16`(위 half)과 `MA01`(아래 half)이 함께 나온다.
CHMAP = {
    'MK': {
        'CHMAP_LT': 'MD16,MD15,MD14,MD13,MD12,MD11,MD10,MD09',
        'CHMAP_LB': 'MA01,MA02,MA03,MA04,MA05,MA06,MA07,MA08',
        'CHMAP_RT': 'KA08,KA07,KA06,KA05,KA04,KA03,KA02,KA01',
        'CHMAP_RB': 'KD09,KD10,KD11,KD12,KD13,KD14,KD15,KD16',
    },
    'NT': {
        'CHMAP_LT': 'NA08,NA07,NA06,NA05,NA04,NA03,NA02,NA01',
        'CHMAP_LB': 'ND09,ND10,ND11,ND12,ND13,ND14,ND15,ND16',
        'CHMAP_RT': 'TD16,TD15,TD14,TD13,TD12,TD11,TD10,TD09',
        'CHMAP_RB': 'TA01,TA02,TA03,TA04,TA05,TA06,TA07,TA08',
    },
}


def chmap_section(channel: int) -> str:
    """채널 번호가 정하는 `CHMAP_*` 가운데 글자.  01–08 = `A` · 09–16 = `D`.

    raw spec 4.5절 · 부록 A -- 채널 번호 = OS 번호이고 OS1–8 이 아래 half(섹션
    A) · OS9–16 이 위 half(섹션 D) 다.  **chip 이나 사분면은 보지 않는다.**
    """
    return 'A' if 1 <= channel <= 8 else 'D'


def check_geometry() -> None:
    """raw spec 2.4·4장·4.5절 불변식.  import 시 1회 검사한다.

    상수를 손보다 어긋나면 **여기서** 터지는 것이 낫다 -- 헤더에 실린 뒤에
    발견하면 그 프레임들은 이미 아카이브에 들어가 있다.
    """
    checks = (
        ('AMPNAX1 = PRESCNX+IMAGEX+OVRSCNX',
         AMPNAX1, PRESCNX + IMAGEX + OVRSCNX),
        ('AMPNAX2 = PRESCNY+IMAGEY+OVRSCNY',
         AMPNAX2, PRESCNY + IMAGEY + OVRSCNY),
        ('NAXIS1 = NXTILE*AMPNAX1', RAW_NAXIS1, NXTILE * AMPNAX1),
        ('NAXIS2 = 2*AMPNAX2', RAW_NAXIS2, 2 * AMPNAX2),
        ('NAMPRAW = 2*NAMPDET', NAMPRAW, 2 * NAMPDET),
        # 2.4절 크기 등식: 파일 픽셀 − amp 픽셀 = 중앙 Y overscan 블록.
        # 이 등식이 깨지면 4장 해석이 어긋난 것이다.
        ('파일픽셀 − amp픽셀 = 중앙 overscan',
         RAW_NAXIS1 * RAW_NAXIS2 - NAMPRAW * AMPNAX1 * IMAGEY,
         RAW_NAXIS1 * 2 * OVRSCNY),
    )
    for label, got, want in checks:
        if got != want:
            raise ValueError(f'raw spec 4장 불변식 위반 -- {label} '
                             f'({got} != {want})')
    # 4.5절 CHMAP 불변식 (v1.5): 카드당 8토큰 · **토큰 4자** · 첫 글자 = DETID
    # 글자 · **가운데 글자가 번호 규칙(01–08=A · 09–16=D)과 일치** · chip 당
    # 채널 01–16 전량 · pair 합계 64.
    total = 0
    for detid, cards in CHMAP.items():
        chans: dict[str, set[int]] = {detid[0]: set(), detid[1]: set()}
        for side, key in (('L', 'CHMAP_LT'), ('L', 'CHMAP_LB'),
                          ('R', 'CHMAP_RT'), ('R', 'CHMAP_RB')):
            tokens = cards[key].split(',')
            if len(tokens) != 8:
                raise ValueError(f'{detid} {key}: 8토큰이 아니다 -- {tokens}')
            chip = detid[0] if side == 'L' else detid[1]
            for t in tokens:
                if len(t) != 4:
                    raise ValueError(
                        f'{detid} {key}: 토큰 {t!r} 가 4자가 아니다 '
                        f'(<chip><A|D><nn>, raw spec 4.5절)')
                if t[0] != chip:
                    raise ValueError(
                        f'{detid} {key}: 접두 {t[0]} 가 chip {chip} 와 다르다')
                num = int(t[2:])
                want = chmap_section(num)
                if t[1] != want:
                    raise ValueError(
                        f'{detid} {key}: 토큰 {t!r} 의 가운데 글자가 {t[1]} 인데 '
                        f'채널 {num:02d} 는 {want} 여야 한다 (01–08=A · 09–16=D)')
                chans[chip].add(num)
            total += 8
        for chip, seen in chans.items():
            if seen != set(range(1, 17)):
                raise ValueError(f'chip {chip}: 채널 01–16 전량이 아니다 -- '
                                 f'{sorted(seen)}')
    if total != 64:
        raise ValueError(f'pair 합계 64 가 아니다 -- {total}')


# ---------------------------------------------------------------------------
# 5.2 Instrument · Detector (23장)
# ---------------------------------------------------------------------------

def instrument_header(ctrltag: str, site_code: str,
                      cfg_camera: dict | None = None) -> dict[str, object]:
    """5.2절 -- 타일 해부 상수 + `CHMAP_*` + `ICS INI` 카드 4장.

    Args:
        ctrltag: `MK` 또는 `NT`.  `DETID`/`CHMAP_*` 가 여기서 갈린다
            (pair 상이 **6장** 중 5장, raw spec 5.9절 -- v1.6 에서
            `ORIGNAME` 이 빠져 7장에서 줄었다).
        site_code: `INSTRUME` 기본값(`'<SITE> 18k CCD'`, 운영자 확정)과
            **`FPAID`** 를 유도한다 (raw spec 5.3.1절, D-017 항목 6).
        cfg_camera: `[camera]` 설정 (`detector`/`camver`/`instrume`/`fpaid`).
            주어지면 기본값보다 **우선한다** -- Source 가 `ICS INI` 인 카드는
            ini 에서 수정할 수 있어야 한다 (운영자 지시 2026-08-22).
    """
    tag = ctrltag.upper()
    c = cfg_camera or {}
    out: dict[str, object] = {
        'INSTRUME': str(c.get('instrume', f'{site_code.upper()} 18k CCD')),
        'CAMVER': str(c.get('camver', CAMVER)),
        'FPAID': str(c.get('fpaid') or fpaid_of(site_code)),
        'DETECTOR': str(c.get('detector', DETECTOR)),
        'DETID': tag,
        'PIXSIZE': PIXSIZE, 'PIXSCALE': PIXSCALE,
        'CCDXBIN': CCDXBIN, 'CCDYBIN': CCDYBIN,
        'NAMPDET': NAMPDET, 'NAMPRAW': NAMPRAW,
        'AMPNAX1': AMPNAX1, 'AMPNAX2': AMPNAX2,
        'IMAGEX': IMAGEX, 'IMAGEY': IMAGEY,
        'PRESCNX': PRESCNX, 'PRESCNY': PRESCNY,
        'OVRSCNX': OVRSCNX, 'OVRSCNY': OVRSCNY,
    }
    out.update(CHMAP[tag])
    return out


# ---------------------------------------------------------------------------
# 5.3 Observatory (7장)
# ---------------------------------------------------------------------------
#
# **좌표를 코드에 박지 않는다.**  운영자가 세 사이트 실측값을 확인해 줬고
# (2026-08-13), `[site]`/`[site.<코드>]` 설정이 있으면 그쪽이 이긴다 --
# 현장이 정본이다.  KASI(실험실)는 좌표를 **일부러 비워** sentinel 을 싣는다
# (아무 좌표나 넣으면 시험 산출물이 실제 관측처럼 보인다).

#: 사이트별 측지값 (운영자 확인 2026-08-13).
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
#: 않는다 (raw spec OI-11).  형식(초의 소수점 자리, `+` 부호 유무)도 사이트마다
#: 다르지만 **운영자가 준 문자열을 그대로 싣는다** -- 정규화하면 레거시
#: 아카이브와 문자열 비교가 깨진다.
#:
#: **`telescop`·`fpaid` 는 사이트가 정하는 상수다** (raw spec **5.3.1절**,
#: D-017 항목 6, 운영자 확정 2026-08-25).  사이트 하나에서 다섯 값(`<SITE>` ·
#: `OBSERVAT` · `ORIGIN` · `TELESCOP` · `FPAID`)이 함께 유도되고 낱개 설정은
#: 두지 않는다 -- 다만 `[site.*]` / `[camera] fpaid` 에 값이 있으면 그쪽이
#: 이긴다 (현장이 정본).
#:
#: ⚠️ **망원경 번호와 `FPAID` 번호는 관측소 셋 모두 어긋난다** -- CTIO 망원경
#: `#1`·FPA `#2`, SSO `#3`·FPA `#1`, SAAO `#2`·FPA `#3`.  망원경 번호는 설치
#: 순서이고 `FPAID` 는 **조립체 자체의 정체**이며 조립체는 사이트 간 이동이
#: 가능하다.  **어긋난 것을 오타로 보고 맞추면 검출기 귀속이 통째로 틀어진다.**
#: KASI 만 `#0`/`#0` 으로 같은데 그건 우연이다.
#:
#: SSO 값은 **레거시 실측**으로 확인됐다 (`KMTNk.20170209.044131`:
#: `OBSERVAT='SSO'` + `TELESCOP='KMTNet 1.6m #3'`).  나머지 셋은 운영자 제시분.
VERIFIED_SITES = {
    'KMTC': {'latitude': '-30:10:01.84', 'longitud': '+70:48:14.39',
             'elevatio': 2140, 'telescop': 'KMTNet 1.6m #1', 'fpaid': 'FPA#2'},
    'KMTS': {'latitude': '-32:22:42', 'longitud': '339:11:22',
             'elevatio': 1800, 'telescop': 'KMTNet 1.6m #2', 'fpaid': 'FPA#3'},
    'KMTA': {'latitude': '-31:16:24', 'longitud': '210:56:08',
             'elevatio': 1150, 'telescop': 'KMTNet 1.6m #3', 'fpaid': 'FPA#1'},
    # KMTK(KASI 실험실)는 실재 관측 좌표가 없다.  측지값은 **일부러 비워** 둔다
    # -- 아무 좌표나 넣으면 시험 산출물이 실제 관측처럼 보인다.  `telescop`/
    # `fpaid` 만 값이 있는 것은 D-017 항목 6 이 `'KMTNet 1.6m #0'` / `'FPA#0'`
    # 으로 정했기 때문이다 (구 `KMTT` 판의 `TELESCOP='Sim'` 을 대체한다).
    'KMTK': {'telescop': 'KMTNet 1.6m #0', 'fpaid': 'FPA#0'},
}


def fpaid_of(site_code: str) -> str:
    """사이트가 정하는 `FPAID` (raw spec 5.3.1절, D-017 항목 6).

    모르는 코드면 규격 5.0절 문자열 sentinel `'NC'` 다 -- 아무 조립체 번호나
    싣는 것보다 "모른다" 가 낫다.
    """
    return str(VERIFIED_SITES.get(site_code.upper(), {}).get('fpaid', 'NC'))


def observatory_header(site_code: str, cfg_site: dict | None = None,
                       observer: str = '') -> dict[str, object]:
    """5.3절 관측소 (7장).

    `OBSERVAT` 는 파일명 `<SITE>` 와 교차 검증되는 **유일한 변환 하드 실패**
    카드다 (raw spec 2.2절).  `ORIGIN` = "이 파일이 생성된 곳" -- 관측소 raw 는
    관측소명, KASI(실험실) raw 는 `KASI` (운영자 확정 2026-08-21).  **D-017
    이후 네 자리 모두 `OBSERVAT` 와 값이 같아졌지만 뜻은 다르다.**  `[site]` 의
    `origin` 키가 유도값을 이긴다.
    """
    from . import rawpair                      # 순환 import 회피 (이름 규약 쪽)
    code = site_code.upper()
    vals = dict(VERIFIED_SITES.get(code, {}))
    cfg = cfg_site or {}
    vals.update({k: v for k, v in cfg.items() if v not in ('', None)})
    if not vals:
        log.warning('사이트 %s 의 측지값이 없다 -- LATITUDE/LONGITUD/ELEVATIO 를 '
                    'sentinel 로 싣는다. [site] 설정으로 넣어 줄 것', code)
    return {
        'ORIGIN': str(vals.get('origin')
                      or rawpair.ORIGIN_OF.get(code, 'KASI')),
        'OBSERVAT': rawpair.OBSERVAT.get(code, 'NC'),
        'TELESCOP': str(vals.get('telescop', 'NC')),
        'LATITUDE': str(vals.get('latitude', 'NC')),
        'LONGITUD': str(vals.get('longitud', 'NC')),
        'ELEVATIO': int(vals.get('elevatio', -1)),
        'OBSERVER': observer or 'NC',
    }


# ---------------------------------------------------------------------------
# 5.4 Exposure · 파일 정체성 (10장)
# ---------------------------------------------------------------------------

def exposure_header(*, imgtype: str, objname: str, projid: str,
                    exptime: float, ledflash_ms: int, date_obs: str,
                    filename: str, expid: str) -> dict[str, object]:
    """5.4절 -- 노출 식별 + `FILENAME`/`EXPID` 정체성 (D-016 · **D-019**).

    * `IMAGETYP`/`OBSTYPE` 는 **대문자** 통제 어휘 -- L1 파이프라인이 문자열
      비교로 검사한다.  `OBSTYPE` 는 `IMAGETYP` 와 동일 어휘다 (raw spec 5.4절).
    * `EXPTIME` 은 정수형 기본, 소수점 아래 값이 있을 때만 실수형
      (형 판정은 `rawcards.render`).  sentinel 금지 -- 취득 SW 가 구조적으로
      아는 값이다.
    * `LEDFLASH` 는 **[ms] 정수** -- 레거시([s])와 단위가 다르므로 comment 가
      단위를 명시한다 (운영자 확정 2026-08-22).
    * `DATE-OBS` 는 ICS 가 `SHOPEN` 을 지시한 UTC, **밀리초 필수**.  비어
      들어오면 `None` 으로 만들어 **카드를 내지 않는다** -- "지금"으로 채우면
      converter 의 실패 경로가 발동하지 않는다 (raw spec 5.0절, C-6).
    * `FILENAME` = 실제 저장명(확장자 없음, 아카이브 유일 키) ·
      `EXPID` = 카운터 최초 배정 노출 식별자 `<SITE>.<YYYYMMDD>.<NNNNNN>`
      (**`DETID` 필드 없음 -> pair 양쪽 동일**, D-019).  **충돌 신호 =
      `FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값 != `EXPID`** 다 --
      카드 존재가 아니라 (D-016).  구판의 `UNIQNAME`/`NAMECLSH` 는 폐지됐다.

    구판이 여기서 만들던 `MJD-OBS`/`UT`/`TSHOPEN`/`TSHSHUT`/`DARKTIME` 은
    v1.3 미기재 카드다 -- `DATE-OBS`/`EXPTIME` 파생은 하류 몫이다 (5.10절).
    """
    kind = (imgtype or 'OBJECT').upper()
    if not date_obs:
        log.error('DATE-OBS 가 비어 있다 -- ICS 가 노출 개시 시각을 찍지 못한 '
                  '우리 결함이다. 카드를 비워 converter 가 이 노출을 거부하게 '
                  '한다 (raw spec 5.0절, C-6)')
    return {
        'PROJID': projid or 'NC',
        'IMAGETYP': kind,
        'OBJECT': objname or 'NC',
        'OBSTYPE': kind,
        'EXPTIME': float(exptime),
        'LEDFLASH': int(ledflash_ms),
        'TIMESYS': 'UTC',
        'DATE-OBS': date_obs or None,
        'FILENAME': filename,
        'EXPID': expid,
    }


# ---------------------------------------------------------------------------
# 5.5 Controller · ICS (9장)
# ---------------------------------------------------------------------------

#: `DATASRC` 값 체계 (raw spec 5.5절).  **시뮬 프레임이 실측으로 오인되는 것을
#: 막는 유일한 카드**이고, 작성 프로그램 식별도 겸한다.  구판 `ARCHON` 단일값이
#: `HEMODE`(SCIENCE/GUIDE 구분 카드, 폐지)를 흡수해 셋으로 갈라졌다.
DATASRC_SCIENCE = 'ARCHON_SCIENCE'
DATASRC_GUIDE = 'ARCHON_GUIDE'
DATASRC_SIM = 'SIM'

#: 백엔드 이름 -> `DATASRC`.  **모르는 백엔드는 `SIM` 으로 떨어뜨린다** --
#: 실물이라고 잘못 적는 쪽이 훨씬 나쁘기 때문이다.
_DATASRC = {'archon': DATASRC_SCIENCE, 'sim': DATASRC_SIM}


def datasrc_of(backend_name: str) -> str:
    src = _DATASRC.get((backend_name or '').lower())
    if src is None:
        log.warning('백엔드 %r 를 모르므로 DATASRC=SIM 으로 적는다 -- 실물이라고 '
                    '잘못 적는 것보다 낫다 (raw spec 5.5절)', backend_name)
        return DATASRC_SIM
    return src


def controller_header(info: dict, *, backend_name: str, ics_build: str,
                      cfg_ctrl: dict[int, dict] | None = None,
                      rdmode: str = '') -> dict[str, object]:
    """5.5절 컨트롤러 정체 색인형 + ICS 식별 (9장).

    **두 대분을 색인형으로 양쪽 파일에 모두 싣는다** -- converter 가 MK 헤더만
    읽으므로 (raw spec 5.5절, 5.9절 "반드시 동일").  guide FITS 는 `CTRL1xx`
    한 벌만 싣는 확장 규약이다.

    구판의 런타임 상태 카드(`CTRLSTAT`/`CTRLERR`/`BCKTEMP`/`READTIME` …)와
    버전 카드(`CTRLVER`/`TIMVER`/`BIASVER`/`CLKVER` · `CTRLnFW`)는 폐지됐다 --
    타이밍·바이어스·클럭 버전 문자열은 전부 **`CTRLnCFG`(적용 설정 파일명)로
    귀속**된다 (원장 확인 요망 8 종결).  텔레메트리는 `Cn_*` 카드로 갔다
    (`ctrl_telemetry_header`).

    Args:
        info: 백엔드 `controller_info()`.  `units` 는 색인 순서(1=MK, 2=NT)의
            `{'id','sn','cfg'}` 목록이다.
        cfg_ctrl: `[controllers]` 설정 -- 색인별 `{'id','sn','cfg'}` 오버라이드.
            **채워진 키는 백엔드 보고값을 이긴다** (ICS INI 카드, 운영자 지시
            2026-08-22).  실값 원자료는 `raw_fits_spec/__reference/
            Archon_Unit_Info.txt` (`KMTA-SCI-101`=STA-0288 등, ID 숫자 = IP).
        rdmode: `[controllers] rdmode` -- 비면 코드 기본 `NORMAL`.
            MEF `READMODE`(`'64AMP'`, 구조 선언)와 **별개**다 (원장 v1.9).
    """
    units = [dict(u) for u in info.get('units', ())]
    for n, ov in sorted((cfg_ctrl or {}).items()):
        while len(units) < n:
            units.append({})
        units[n - 1].update({k: v for k, v in ov.items() if v})
    while len(units) < 2:
        units.append({})
    out: dict[str, object] = {'DATASRC': datasrc_of(backend_name)}
    # **없는 컨트롤러도 카드는 남긴다** (운영자 지시 2026-08-24).  1대만 운영할
    # 때 빠진 쪽의 `CTRLnID/SN/CFG` 를 빼 버리면 pair 두 파일의 카드 수가
    # 달라지고, converter 와 견본 대사가 그것을 구조 변경으로 읽는다.
    #
    # 값은 규격 5.0절의 문자열 sentinel **`'NC'`** 다 (운영자 확정 2026-08-25).
    # ini 에 `none` 이라고 적은 것도 "없다" 는 뜻이므로 같은 자리로 떨어진다 --
    # 이 셋만 다른 표기를 쓰면 규격과 갈린다.
    for n, unit in enumerate(units[:2], start=1):
        out[f'CTRL{n}ID'] = str(unit.get('id', 'NC'))
        out[f'CTRL{n}SN'] = str(unit.get('sn', 'NC'))
        out[f'CTRL{n}CFG'] = str(unit.get('cfg', 'NC'))
    out['ICSBUILD'] = ics_build
    out['RDMODE'] = rdmode or RDMODE
    return out


# ---------------------------------------------------------------------------
# 5.6 Camera System House Keeping (18장) + 5.8 의 Tapaculo 2장
# ---------------------------------------------------------------------------

#: 듀어·HK 센서 카드 -- 견본 v1.0 의 수록 순서.  출처 3계통은 백엔드
#: `sensors()` docstring 참조 (ICG RTD / standalone RTD / Tapaculo).
#:
#: ⚠️ **`AIR_IN`/`AIR_OUT`/`GLYC_IN`/`GLYC_OUT` 4장은 폐지됐다** (운영자 확정
#: 2026-08-25, raw spec v1.5 -- 5.6절이 18장에서 14장으로 줄었고 5.10절 폐지
#: 목록에 등재됐다).  standalone RTD 계통이 통째로 비었다.  견본 값 카드도
#: 135 -> **131** 이 됐다.  되살리려면 **규격부터** 고칠 것.
DEWAR_CARDS = ('DMPTEMP', 'PT30N1', 'PT30N2', 'CHARCOAL', 'WALLBRD', 'HEBOX')

#: 측정 불가를 뜻하는 `DEWPRES` 값 (운영자 확정 2026-08-21).
DEWPRES_NC = '9.99e-9'

#: 측정 불가를 뜻하는 HK 온도·습도 카드 값 (운영자 확정 2026-08-22, 단일값).
#:
#: 온도로는 어떤 냉각 램프도 닿지 않는 값이고 습도로는 음수라 물리적으로
#: 불가능하다.  `-99.99` 안은 기각됐다 -- **CCDTEMP 냉각/워밍업 램프가 실제로
#: 지나가는 값**(정상 운영값 -101~-103 바로 위)이라 실측과 구별되지 않는다.
#: 습도 `0.00` 안도 기각 -- 0% RH 는 유효 측정값이다.
TEMP_NC = '-999.99'

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


def format_temp(value: object) -> str:
    """HK 온도 카드를 `'-101.23'`/`'+16.78'` 꼴 문자열로 만든다 [deg C].

    **왜 문자열인가** (운영자 확정 2026-08-22) -- 레거시가 온도를 부호 포함
    문자열로 실었고(`CCDTEMP = '-103.16'`), converter 는 pass-through 라 문자열
    계승이 **아카이브 전체의 형을 통일**한다 -- 신규만 실수형이면 같은 이름에
    두 형이 섞인다.  표기를 우리가 못 정하는 astropy 실수 카드 문제는
    `format_dewpres` 와 같다.

    측정 불가는 전부 `TEMP_NC`(`'-999.99'`) 하나로 모은다.
    """
    if value is None:
        return TEMP_NC
    try:
        t = float(value)
    except (TypeError, ValueError):
        log.warning('온도 센서 값이 수치가 아니다(%r) -- %s 로 싣는다',
                    value, TEMP_NC)
        return TEMP_NC
    if t != t or t in (float('inf'), float('-inf')):
        log.warning('온도 센서 값이 유한하지 않다(%r) -- %s 로 싣는다',
                    t, TEMP_NC)
        return TEMP_NC
    return f'{t:+.2f}'


def format_ens(value: object) -> str:
    """`FSATEMP`/`FSAHUM` 의 ENS식 표기 -- 부호 없는 소수 1자리 (`'23.4'`).

    **잠정이다** (raw spec 5.8절, OI-16) -- Tapaculo 원값 포맷을 확인한 뒤
    "원값 그대로 싣기"로 최종 확정한다.  측정 불가 sentinel 은 HK 온도·습도
    공통의 `TEMP_NC`(`'-999.99'`) -- 5.0절이 FSA 2장을 그 규약에 명시했다.
    """
    if value is None:
        return TEMP_NC
    try:
        t = float(value)
    except (TypeError, ValueError):
        log.warning('FSA 센서 값이 수치가 아니다(%r) -- %s 로 싣는다',
                    value, TEMP_NC)
        return TEMP_NC
    if t != t or t in (float('inf'), float('-inf')):
        return TEMP_NC
    return f'{t:.1f}'


def thermal_header(sensors: dict | None) -> dict[str, object]:
    """5.6절 HK 12장 + 5.8절 Tapaculo 2장 (`FSATEMP`/`FSAHUM`).

    **`CCDTEMP` 는 실측 대표 센서 1개의 값이다** (운영자 확정 2026-08-21).
    대표 센서는 백엔드 `ccdtemp` 이고, **죽었을 때 다른 값으로 대체하지
    않는다** -- 대표가 아닌 값을 대표라고 적으면 조용히 틀린 값이 된다.
    L1 `CARRY_KEYS` 가 이 이름을 요구하므로 카드를 비우지 않고 sentinel 로
    싣는다.

    ⚠️ **chip 으로 규정하지 않는다** (운영자 2026-08-27) -- 듀어의 CCD 대표
    온도 하나이고 chip 귀속 정보는 없다.  종전 `ccdtemp1`/`ccdtemp2` 는
    `ccdtemp` 하나로 합쳤다.  **카드 comment 의 `M` 을 없애는 것은 raw spec
    v1.8 작업**이다(견본 pair 바이트가 정본이라 규격과 함께 움직인다) --
    그때까지 comment 는 종전 문안 그대로다.

    ⚠️ **대체 후보가 눈에 보인다는 것이 함정이다** -- `DMPTEMP` 나 `Cn_TEMP`
    의 모듈 온도로 메우고 싶어지는데, 그러면 파일만으로 검산할 수 없는 값이
    대표 자리에 앉는다.

    **온도·습도 카드는 전부 문자열이다** (raw spec 5.0절).
    """
    s = sensors or {}
    t1 = s.get('ccdtemp')
    if t1 is None:
        log.warning('CCD 대표 온도(ccdtemp)를 못 읽었다 -- CCDTEMP 를 '
                    'sentinel(%s)로 싣는다. 다른 센서로 대체하지 않는다 '
                    '(대표가 아닌 값을 대표라고 적으면 조용히 틀린 값이 된다)',
                    TEMP_NC)
    out: dict[str, object] = {
        'DEWPRES': format_dewpres(s.get('dewpres')),
        'CCDTEMP': format_temp(t1),
    }
    for card in DEWAR_CARDS:
        out[card] = format_temp(s.get(card.lower()))
    # 5.8절의 Tapaculo 2장 -- 블록은 AUX 지만 출처가 백엔드라 여기서 준다.
    out['FSATEMP'] = format_ens(s.get('fsatemp'))
    out['FSAHUM'] = format_ens(s.get('fsahum'))
    return out


#: `Cn_VOLT`/`Cn_CURR` 의 자리 순서 (raw spec **5.6.1절**) -- Archon STATUS 의
#: 전원 레일 필드 `P2V5_V/I` … `P35V_V/I` 에 대응한다 (Archon 매뉴얼 p.47).
#: 두 카드가 같은 순서를 쓴다.
VOLT_RAILS = ('P2V5', 'P5V', 'P6V', 'N6V', 'P17V', 'N17V', 'P35V')

#: `Cn_TEMP` 의 자리 순서 -- **science 컨트롤러 10자리** (raw spec **5.6.1절**,
#: 운영자 확정 2026-08-25).  Archon STATUS 의 모듈 온도 필드에 대응한다.
#:
#:     자리  1  Backplane        6  Mod5:ADM
#:           2  Mod1:LVDS        7  Mod8:ADM
#:           3  Mod2:Driver      8  Mod9:HVYBias
#:           4  Mod3:Driver      9  Mod10:Driver
#:           5  Mod4:LVXBias    10  Mod11:Driver
#:
#: **자리 자체가 항목이다** -- 값에 이름표가 없으므로 읽는 쪽은 이 표로만
#: 해석한다.  그래서 결측이면 그 자리에 sentinel 을 넣고 **건너뛰지 않는다**:
#: 건너뛰면 뒤 항목이 앞으로 당겨져 소비자가 구분할 방법이 없다 (labtest v1.1
#: 이 고친 결함).
#:
#: **목록에 없는 모듈(6 · 7 · 12)은 자리를 차지하지 않는다** -- 자리 수가
#: 장착·보고되는 모듈 수를 따르므로 **자리 수 자체가 구성 판별에 쓰인다**.
#: 구성이 바뀌면 `CAMVER`(HW) · `CTRLnCFG`(설정) 범프로 드러나야 한다 (4.3절).
#:
#: ⚠️ **guide 컨트롤러는 8자리로 다르다** (Backplane · Mod3 · Mod4 · Mod5 ·
#: Mod6 · Mod7 · Mod9 · Mod10) -- 원장 7장 기재분이고 **실기 대조 전**이다
#: (**OI-19**).  guide raw 규격을 세울 때 실측으로 확정한다.  전원 레일 7자리는
#: science 와 같다.
#:
#: ⚠️ 종전 구현은 `BACKPLANE_TEMP` + `MOD5~MOD8` **5자리**였다 (AD 모듈이
#: 중앙 4슬롯이라는 매뉴얼 p.20 근거의 잠정안).  v1.5 5.6.1절이 정본을 세우면서
#: 교체했다 -- 견본 pair 의 `C1_TEMP` 도 처음부터 10개였다.
TEMP_MODS = ('BACKPLANE_TEMP', 'MOD1/TEMP', 'MOD2/TEMP', 'MOD3/TEMP',
              'MOD4/TEMP', 'MOD5/TEMP', 'MOD8/TEMP', 'MOD9/TEMP',
              'MOD10/TEMP', 'MOD11/TEMP')

#: `TEMP_MODS` 자리별 항목 이름 -- **규격 5.6.1절 표 그 자체**다 (진단 출력·대사용).
#:
#: ⚠️ **두 상수의 지위가 다르다.**  이 라벨 튜플은 규격이 정한 것이고,
#: 위 `TEMP_MODS`(STATUS 필드명)는 **규격에 없다** -- 각 자리에 어떤 Archon
#: STATUS 필드를 읽어 넣을지는 매뉴얼 p.47-49 근거의 **구현 대응**이다.
#: 규격은 헤더에 무엇이 어느 자리에 실리는지를 정하지, ICS 가 그 값을 어디서
#: 긁어오는지를 정하지 않는다.  자리 순서만 둘이 같아야 한다.
TEMP_MOD_LABELS = ('Backplane', 'Mod1:LVDS', 'Mod2:Driver', 'Mod3:Driver',
                    'Mod4:LVXBias', 'Mod5:ADM', 'Mod8:ADM', 'Mod9:HVYBias',
                    'Mod10:Driver', 'Mod11:Driver')


#: 나열 카드의 결측 자리 sentinel (raw spec **5.6.1절**).
#:
#: `FIELD` = **나열 카드의 토큰 자리**다 -- 백플레인 모듈이 아니다(전압·전류
#: 7레일에도 이 값을 쓴다).  구 이름은 `SLOT_NC` 였는데 **`slot` 이 컨트롤러의
#: 실제 슬롯과 혼동돼** `field` 로 옮겼다 (운영자 2026-08-26).  모듈 자리를
#: 가리키는 상수는 `TEMP_MODS` 로 따로 있다.
#:
#: 단일 HK 카드의
#: `'-999.99'` 와 **다르다** -- 7자짜리가 열 자리를 채우면 79자가 되어 카드
#: 폭을 크게 넘기는데 `NC` 면 29자다.  `archon/parse.FIELD_NC` 와 같은 값이고,
#: 그쪽이 STATUS 를 읽을 때 이미 이 값으로 자리를 채워 보낸다.
FIELD_NC = 'NC'


def _join_readings(values, fmt: str, n_fields: int) -> str:
    """텔레메트리 나열 카드 본문 -- **`|` 구분, 자리 = 항목** (raw spec 5.6.1절).

    수치는 `fmt` 로 표기를 고정하고(견본: 온도 1자리 · 전압/전류 3자리),
    문자열은 그대로 잇는다.  값이 없는 자리는 `'NC'` -- 나열 카드라 온도·습도
    단일값 sentinel(`-999.99`)이 아니라 문자열 공통 sentinel 이다.

    **구분자는 파이프다** (운영자 확정 2026-08-26, v1.6).  공백 하나였는데
    음수가 섞이면(`16.956 -17.067 35.089`) 경계가 눈으로 안 갈렸다.  폭
    비용은 없다 -- 구분자는 어느 쪽이든 1자다.

    ⚠️ **슬래시를 쓰지 말 것** -- FITS 의 comment 구분자와 같은 글자라, 인용
    부호를 먼저 찾지 않는 파서에서 값이 첫 슬래시에서 잘린다 (5.6.1절).

    ⚠️ **한 자리도 못 받았어도 자리 수만큼 `NC` 를 채운다** (`n_fields`).  규격
    5.6.1절 "자리는 비우지 않는다" 이고, 같은 절이 STATUS 무응답·미장착 모듈로
    **전 자리가 결측인 경우를 드물지 않다고 못박으며** 그 모습을
    `'NC|NC|…'` 열 자리로 보인다.  `'NC'` 한 토큰으로 내면 **자리 수가 1이
    되는데, 자리 수 자체가 모듈 구성 판별에 쓰이므로**(같은 절) 읽는 쪽에는
    "모듈 한 장짜리 컨트롤러" 로 보인다 -- `tools/probe_archon.py` 의 자리 표
    대조도 그것을 규격 위반으로 짚는다.

    Args:
        values: 자리 순서대로의 값.  비었으면 전 자리 결측이다.
        fmt: 수치 표기 (`'.1f'` / `'.3f'`).
        n_fields: 이 카드의 자리 수 (`len(TEMP_MODS)` / `len(VOLT_RAILS)`).
    """
    if not values:
        return '|'.join([FIELD_NC] * n_fields)
    parts = []
    for v in values:
        if isinstance(v, bool) or v is None or v == '':
            # `bool` 은 `int` 의 하위형이라 `format(True, '.1f')` 가 `1.0` 이
            # 된다 -- 텔레메트리 자리에 올 값이 아니므로 결측으로 본다.
            parts.append(FIELD_NC)
        elif isinstance(v, (int, float)):
            parts.append(format(v, fmt))
        else:
            parts.append(str(v))
    if len(parts) != n_fields:
        # 자리 수가 규격과 다르면 읽는 쪽은 **다른 모듈 구성**으로 읽는다.
        # 여기서 채우거나 잘라 맞추지 않는다 -- 어느 자리가 밀렸는지 모르는
        # 채로 맞추면 값이 엉뚱한 모듈 것으로 실린다 (5.6.1절 "자리 = 항목").
        log.error('나열 카드 자리 수가 %d 인데 규격은 %d 다 -- 백엔드가 준 '
                  '목록이 규격 5.6.1절 자리 표와 어긋난다', len(parts), n_fields)
    return '|'.join(parts)


def ctrl_telemetry_header(telem: list[dict] | None) -> dict[str, object]:
    """5.6절 `C1_*`/`C2_*` -- 컨트롤러별 온도/전압/전류 나열 6장.

    MEF `VOLTINFO`/`TELEMETRY` 를 실측으로 채울 원천이다 (C-후보, 통합 문서
    §1).  **양쪽 파일에 두 대분을 같은 값으로 싣는다** (5.9절 "반드시 동일") --
    그래서 인자가 컨트롤러별 목록 하나다.  자리 순서 명세는 규격 **5.6.1절**
    이고(v1.5 수록), 여기서는 백엔드가 그 순서로 준 목록을 그대로 쓴다.

    ⚠️ **한 대분이 통째로 없어도 카드는 자리 수만큼 `NC` 를 싣는다** -- 실험실
    처럼 컨트롤러 한 대만 돌 때(미장착)와 STATUS 무응답이 그 경우이고, 규격
    5.6.1절이 둘 다 "전 자리 결측" 으로 다룬다.

    Args:
        telem: 색인 순서(1=MK, 2=NT)의 `{'temp': [...], 'volt': [...],
            'curr': [...]}` 목록 (백엔드 `controller_telemetry()`).
    """
    units = list(telem or ())
    while len(units) < 2:
        units.append({})
    out: dict[str, object] = {}
    for n, unit in enumerate(units[:2], start=1):
        out[f'C{n}_TEMP'] = _join_readings(unit.get('temp'), '.1f',
                                           len(TEMP_MODS))
        out[f'C{n}_VOLT'] = _join_readings(unit.get('volt'), '.3f',
                                           len(VOLT_RAILS))
        out[f'C{n}_CURR'] = _join_readings(unit.get('curr'), '.3f',
                                           len(VOLT_RAILS))
    return out


# ---------------------------------------------------------------------------
# 값 풀 조립
# ---------------------------------------------------------------------------

def build_pool(*, ctrltag: str, site_code: str, backend_name: str,
               ics_build: str, ctrl_info: dict, ctrl_telem: list | None,
               sensors: dict | None,
               cfg_site: dict | None, cfg_camera: dict | None,
               cfg_ctrl: dict[int, dict] | None, rdmode: str,
               telem_cards: dict[str, object],
               date_obs: str, exptime: float, ledflash_ms: int,
               imgtype: str, objname: str, projid: str, observer: str,
               filename: str, expid: str) -> dict[str, object]:
    """규격 5장 값 풀 하나로.  카드 조립은 `rawcards.render()` 가 한다.

    `telem_cards`(TC 중계, `telemetry.fits_header_dict()`)를 바닥에 깔고 이
    모듈의 블록을 위에 얹는다 -- 겹치는 키는 이쪽이 이기지만, 템플릿이 걸러
    주므로 와이어의 낯선 키가 헤더로 새지 않는다 (rawcards docstring).
    """
    pool: dict[str, object] = dict(telem_cards)
    pool['BUNIT'] = 'ADU'
    pool.update(instrument_header(ctrltag, site_code, cfg_camera))
    pool.update(observatory_header(site_code, cfg_site, observer))
    pool.update(exposure_header(imgtype=imgtype, objname=objname,
                                projid=projid, exptime=exptime,
                                ledflash_ms=ledflash_ms, date_obs=date_obs,
                                filename=filename, expid=expid))
    pool.update(controller_header(ctrl_info, backend_name=backend_name,
                                  ics_build=ics_build, cfg_ctrl=cfg_ctrl,
                                  rdmode=rdmode))
    pool.update(thermal_header(sensors))
    pool.update(ctrl_telemetry_header(ctrl_telem))
    return pool


def spec_cards(**kwargs) -> list[tuple[str, object, str]]:
    """`build_pool()` + `rawcards.render()` -- 헤더 카드 한 번에."""
    return rawcards.render(build_pool(**kwargs))


check_geometry()

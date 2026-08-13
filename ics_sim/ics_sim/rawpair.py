#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Raw FITS pair — 저장 단위(컨트롤러)와 통보 단위(CCD)의 분리.

근거는 [`raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md`] 2.3·2.5·5.1·5.2절과
[`mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md`] 2.1·3절이다.
결정 기록은 DECISION_LOG D-010(통보 분리) · D-011(사이트 코드) · D-012(계약 개정).

**한 노출이 만드는 것**

    물리 파일 2개   <SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits   (chip M, K)
                    <SITE>.<YYYYMMDD>.<NNNNNN>.NT.fits   (chip N, T)
    Wrote 통보 4회  KMTN m / k / n / t  .<YYYYMMDD>.<NNNNNN>.fits   (논리 이름)

**논리 이름의 `KMTN` prefix 는 사이트 코드와 무관하게 불변이다.** OBSAgent 가
`"KMTN"` 문자열 위치 +6 부터 15자를 잘라 `FitsNum` 으로 쓰기 때문이다
(DevNote 3.2, `commands.c` 776-784).  물리 파일명에 쓰는 `KMTC`/`KMTS`/`KMTA`/
`KMTT` 는 `KMTN` 을 부분 문자열로 포함하지 않으므로, 물리 경로가 메시지에
섞여 들어가도 그 파서가 오반응하지 않는다 (규격 2.3절).

**`LASTFILE` 은 이제 실재 경로가 아니다.** 논리 이름은 CCD 단위 식별자일 뿐이고
디스크에는 컨트롤러 파일 2개만 있다.  아카이브·DTS 도구는 `LASTFILE` 대신 raw
헤더의 `UNIQNAME`/`FILENAME`/`CTRLTAG` 를 근거로 삼아야 한다 (규격 2.5절 말미).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from . import __version__
from .fitsout import FitsStr

#: 컨트롤러 태그 → 그 파일이 담는 chip.  ICD v4.1 3절의 공식 순서(M,K,N,T)를
#: 그대로 쓴다 -- MK 는 X 낮은 쪽이 M, NT 는 N 이다(규격 5.2 `CHIP1`/`CHIP2`).
#: `[node] ic_ids` 순서(K,M,T,N)와 **다르다** -- 그쪽은 레거시 발신 순서이고
#: 이쪽은 픽셀 배치 순서다.  섞으면 CHIP1/CHIP2 가 뒤집힌다.
CONTROLLERS: tuple[tuple[str, tuple[str, str]], ...] = (
    ('MK', ('M', 'K')),
    ('NT', ('N', 'T')),
)

#: 공식 chip order (규격 5.2 `CHIPLIST`)
CHIPLIST = 'M,K,N,T'

#: 사이트 코드 → `OBSERVAT` 헤더값.  규격 2.3절 표.  파일명 `<SITE>` 와
#: `OBSERVAT` 가 어긋나면 converter v2.2.0 이 오류로 잡는다.
OBSERVAT = {'KMTC': 'CTIO', 'KMTS': 'SAAO', 'KMTA': 'SSO', 'KMTT': 'TESTBED'}

RAWPROD = 'L0_RAW_ARCHON'
RAWVER = 'CEU-RAW-v1.0'
RAWGROUP = 'MKNT'
NUMFILES = 2


def controller_of(ccd: str) -> str:
    """이 chip 이 어느 컨트롤러 파일에 담기나."""
    up = ccd.upper()
    for tag, chips in CONTROLLERS:
        if up in chips:
            return tag
    raise KeyError(f'알 수 없는 chip: {ccd!r}')


def name_stem(site_code: str, suffix: str, ctrltag: str) -> str:
    """`<SITE>.<YYYYMMDD>.<MK|NT>` 형태의 **확장자 없는 이름** (규격 5.1절).

    헤더의 `FILENAME` · `PAIRFILE` 에 싣는 형태다.  **확장자를 붙이지 않는 것이
    레거시 관례**다 -- 실측 헤더가 `FILENAME = 'KMTNk.20170209.044131'` 로
    `.fits` 없이 기록했다(`__reference/Legacy raw fits header samples/`).
    """
    return f'{site_code.upper()}.{suffix}.{ctrltag.upper()}'


def physical_name(site_code: str, suffix: str, ctrltag: str) -> str:
    """`<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits` -- 디스크 파일명 (규격 2.3절).

    `suffix` 는 `state.next_suffix()` 가 만든 `<YYYYMMDD>.<NNNNNN>` 이다 --
    논리 이름과 **같은 일련번호**를 쓰는 것이 규약이다.  헤더에 싣는 것은
    확장자를 뗀 `name_stem()` 이다.
    """
    return f'{name_stem(site_code, suffix, ctrltag)}.fits'


def physical_path(data_dir: str, site_code: str, suffix: str,
                  ctrltag: str) -> str:
    """저장 경로.  메시지에는 항상 '/' 구분자로 나간다 (state.filename 과 동일)."""
    joined = os.path.join(data_dir, physical_name(site_code, suffix, ctrltag))
    return joined.replace(os.sep, '/')


def logical_name(ccd: str, suffix: str) -> str:
    """`Wrote` 에 싣는 CCD 단위 논리 이름.  **`KMTN` prefix 불변** (규격 2.5절)."""
    return f'KMTN{ccd.lower()}.{suffix}.fits'


def logical_path(data_dir: str, ccd: str, suffix: str) -> str:
    joined = os.path.join(data_dir, logical_name(ccd, suffix))
    return joined.replace(os.sep, '/')


#: 파일 **이름이 겹쳤을 때** 격리하는 하위 디렉토리 (규격 2.3.1절).
#:
#: 이름을 `clash` 로 한 이유: 겹친 것은 **이름**이고 자료는 멀쩡한 새
#: 프레임이다.  `dup`(duplicate)은 자료가 중복이라는 오해를 부른다.
#: 디렉토리·파일 접미·헤더 카드(`NAMECLSH`)가 **같은 낱말**을 쓰므로
#: 하나만 봐도 나머지가 짚인다.
#:
#: **개명 대신 이동을 먼저 쓰는 이유**: 개명하는 목적은 "덮어쓰지 않기" 하나인데,
#: 디렉토리를 옮기면 그 목적이 달성되면서 **이름을 훼손하지 않는다.**  정상
#: 산출물 목록이 깨끗하게 유지되고, converter 는 이 디렉토리를 보지 않으므로
#: 이상 데이터가 조용히 변환되는 일도 없다.
CLASH_DIR = 'clash'


def clash_stem(stem: str, when: datetime) -> str:
    """충돌 시 쓰는 이름 -- 정본 이름 + 쓰기 시각 접미 (규격 2.3.1절).

    번호가 아니라 **시각**을 붙인다.  소진될 일이 없고, 같은 프레임이 두 번
    격리되어도 충돌하지 않으며, **언제 생긴 중복인지가 이름에 남는다.**
    """
    return f'{stem}.clash{when.strftime("%Y%m%dT%H%M%SZ")}'


def resolve_write_path(data_dir: str, site_code: str, suffix: str,
                       ctrltag: str, *, check: bool = True,
                       when: datetime | None = None) -> tuple[str, str, bool]:
    """쓸 경로를 정한다.  충돌하면 격리 디렉토리 + 시각 접미 (규격 2.3.1절).

    세 겹이 각각 다른 질문에 답한다 -- **어디에**(격리 디렉토리) · **어느
    것인지**(시각 접미) · **일어났는지**(`NAMECLSH` 카드, identity_header).

    Args:
        check: False 면 존재 확인을 건너뛴다 (`write_fits=false` 인 메시지 전용
            모드 -- 실제로 쓰지 않으므로 충돌 개념이 없다).
        when: 접미에 쓸 시각.  기본은 현재 UTC.

    Returns:
        (경로, 파일 이름 stem, 충돌했는지).  `stem` 은 헤더 `FILENAME` 값이다
        (경로도 확장자도 없는 형태).
    """
    stem = name_stem(site_code, suffix, ctrltag)
    path = os.path.join(data_dir, f'{stem}.fits').replace(os.sep, '/')
    if not check or not os.path.exists(path):
        return path, stem, False
    alt = clash_stem(stem, when or datetime.now(timezone.utc))
    quarantined = os.path.join(data_dir, CLASH_DIR, f'{alt}.fits')
    return quarantined.replace(os.sep, '/'), alt, True


def pair_tag(ctrltag: str) -> str:
    """짝의 컨트롤러 태그."""
    tags = [t for t, _ in CONTROLLERS]
    return tags[1] if ctrltag.upper() == tags[0] else tags[0]


def identity_header(*, site_code: str, suffix: str, ctrltag: str,
                    filename: str, created: str,
                    clashed: bool = False) -> dict[str, object]:
    """규격 5.1·5.2절의 파일 정체성 / pair provenance keyword.

    **텔레메트리와 분리해서 만든다.** 출처가 다르다 -- 이쪽은 규격 표의
    `ACQ`(취득 SW 가 스스로 아는 값)이고, AUX/TCS 값은 `ICS`(TC 중계)다.

    **`UNIQNAME` 과 `FILENAME` 의 역할이 갈린다 (2026-08-12 확정, 규격 2.3.1절):**

    ==============  ================================================
    `UNIQNAME`      **정본 식별자.** 항상 정규 형태이고 **절대 바뀌지 않는다.**
                    파싱은 언제나 이 값으로 한다
    `FILENAME`      **디스크에 실제로 쓴 이름.** 평소엔 `UNIQNAME` 과 같고,
                    충돌 시에만 시각 접미가 붙는다
    `NAMECLSH`      충돌했을 때**만** 넣는다 -- 카드의 존재가 곧 신호다
    ==============  ================================================

    레거시 실측 헤더(`__reference/Legacy raw fits header samples/`)가 이 구조의
    출발점이다 -- `FILENAME = 'KMTNk.20170209.044131'` 과
    `UNIQNAME = '170209.000'` 을 나란히 두고 후자에 *"Unique filename; if
    filename is invalid"* 주석을 달았다.  다만 레거시의 `<yymmdd>.<nnn>` 형식은
    사이트 코드와 컨트롤러 태그를 잃어 3사이트 통합 시 동명 충돌이 되돌아오므로
    쓰지 않는다.  **여기서는 `UNIQNAME` 을 "정규 이름" 쪽으로 승격했다.**

    `EXPID`/`EXPNUM` 은 두지 않는다 -- `UNIQNAME` 이 날짜·연번·컨트롤러를 모두
    담아 상위집합이고, 둘을 함께 두면 서로 어긋날 수 있는 중복이 된다
    (운영자 확정 2026-08-12).

    Args:
        site_code: `KMTC`/`KMTS`/`KMTA`/`KMTT` (`[node] telid`).
        suffix: `<YYYYMMDD>.<NNNNNN>`.
        ctrltag: `MK` 또는 `NT`.
        filename: **실제로 쓰는** 파일의 이름 -- 경로와 **확장자를 뗀** 형태
            (`resolve_write_path()` 의 두 번째 반환값).
        created: 파일 생성 시각, UTC ISO.
        clashed: 파일명이 충돌해 격리 디렉토리로 갔는지.
    """
    tag = ctrltag.upper()
    chips = dict(CONTROLLERS)[tag]
    site = site_code.upper()
    # 문자열 카드는 FitsStr 로 싣는다 -- 숫자로 보이는 식별자가 실수 카드로
    # 저장되면 자릿수가 날아간다 (fitsout.FitsStr 의 docstring).
    S = FitsStr
    out: dict[str, object] = {
        # 5.1 FITS 표준 · 파일 정체성
        'BUNIT': S('ADU'),
        'ORIGIN': S('KASI'),
        'DATE': S(created),
        'CREATOR': S(f'ics_sim_v{__version__}'),
        'FILENAME': S(filename),
        # 5.2 Pair 식별 · Provenance
        'UNIQNAME': S(name_stem(site, suffix, tag)),
        'RAWPROD': S(RAWPROD),
        'RAWVER': S(RAWVER),
        'RAWGROUP': S(RAWGROUP),
        'CHIPLIST': S(CHIPLIST),
        'CTRLTAG': S(tag),
        'CHIPS': S(','.join(chips)),
        'CHIP1': S(chips[0]),
        'CHIP2': S(chips[1]),
        'PAIRFILE': S(name_stem(site, suffix, pair_tag(tag))),
        'NUMFILES': NUMFILES,
        # 5.9 관측소 -- 파일명 <SITE> 와 일치해야 한다 (규격 2.3절)
        'OBSERVAT': S(OBSERVAT.get(site, 'NC')),
    }
    if clashed:
        # 존재 자체가 신호이므로 False 를 넣지 않는다.  넣으면 "충돌 안 했음"
        # 과 "이 규격을 모르는 취득 SW" 가 구분되지 않는다.
        out['NAMECLSH'] = True
    return out

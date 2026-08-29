#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Raw FITS pair — 이름·번호·충돌 처리 (저장 단위와 통보 단위의 분리).

근거는 [`raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.8.md`] 2장과
[`mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md`] 2.1·3절이다.
결정 기록은 D-010(통보 분리) · D-011(사이트 코드) · D-012(계약 개정) ·
**D-016(충돌 번호 증가) · D-019(`FILENAME`/`EXPID` 정체성)**.

**한 노출이 만드는 것**

    물리 파일 2개   <SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits   (chip M, K)
                    <SITE>.<YYYYMMDD>.<NNNNNN>.NT.fits   (chip N, T)
    Wrote 통보 4회  KMTN m / k / n / t  .<YYYYMMDD>.<NNNNNN>.fits   (논리 이름)

**논리 이름의 `KMTN` prefix 는 사이트 코드와 무관하게 불변이다.** OBSAgent 가
`"KMTN"` 문자열 위치 +6 부터 15자를 잘라 `FitsNum` 으로 쓰기 때문이다
(DevNote 3.2, `commands.c` 776-784).  물리 파일명에 쓰는 `KMTC`/`KMTS`/`KMTA`/
`KMTK` 는 `KMTN` 을 부분 문자열로 포함하지 않으므로, 물리 경로가 메시지에
섞여 들어가도 그 파서가 오반응하지 않는다 (규격 2.3절, DevNote 3.2).

**`LASTFILE` 은 실재 경로가 아니다.** 논리 이름은 CCD 단위 식별자일 뿐이고
디스크에는 컨트롤러 파일 2개만 있다.  하류 도구의 근거는 raw 헤더의
**`FILENAME`(+`EXPID`)** 이다 (D-016 · D-019) -- 짝 이름은 `FILENAME` `DETID` 필드의
`.MK`↔`.NT` 치환으로 항상 유도된다 (`PAIRFILE` 카드는 폐지).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

#: 컨트롤러 태그 → 그 파일이 담는 chip.  ICD v4.1 3절의 공식 순서(M,K,N,T)를
#: 그대로 쓴다 -- MK 는 X 낮은 쪽이 M, NT 는 N 이다(raw spec 2.1절).
#: `[node] ic_ids` 순서(K,M,T,N)와 **다르다** -- 그쪽은 레거시 발신 순서이고
#: 이쪽은 픽셀 배치 순서다.
CONTROLLERS: tuple[tuple[str, tuple[str, str]], ...] = (
    ('MK', ('M', 'K')),
    ('NT', ('N', 'T')),
)

#: 사이트 코드 → `OBSERVAT` 헤더값.  raw spec 2.2절 표.  파일명 `<SITE>` 와
#: `OBSERVAT` 가 어긋나면 converter v2.2.0 이 오류로 잡는다.
#:
#: **`[node] observatory` 에 적는 값이 곧 이 카드값이다** (운영자 확정
#: 2026-08-25) -- 네 사이트 모두 어휘가 같다.  그래서 ini 를 보면 헤더에 무엇이
#: 실릴지 그대로 보이고, raw spec 2.2절 표와도 어긋나지 않는다.
#:
#: ⚠️ **D-017 (2026-08-25)로 넷째 자리가 바뀌었다** -- `TESTBED`/`KMTT` 를
#: 폐지하고 `KASI`/`KMTK` 가 그 자리를 잇는다.  `OBSERVAT` 넷이 전부 관측소
#: 이름이 되게 하려는 것이다.  이 개정으로 `ORIGIN_OF` 와 **네 자리 값이 모두
#: 같아졌지만 뜻은 여전히 다르다** -- `ORIGIN` 은 "이 파일이 생성된 곳",
#: `OBSERVAT` 는 "관측소".  값이 같아졌다고 어느 한쪽을 없애지 말 것.
#: converter 쪽 대응(파일명 정규식·L0 prefix `kmtt`->`kmtk`)은 LEECU 소관의
#: C-항목이다.
OBSERVAT = {'KMTC': 'CTIO', 'KMTS': 'SAAO', 'KMTA': 'SSO', 'KMTK': 'KASI'}

#: `OBSERVATORY`(ini) → 사이트 코드.  **사이트 판별의 단일 권위**다
#: (운영자 지시 2026-08-24 -- 종전의 호스트 IP 판정은 폐지됐다).
#:
#: **위 `OBSERVAT` 표의 역방향**이다 -- 값 어휘가 같으므로 ini 에 적은 낱말이
#: 그대로 헤더 카드가 된다.
SITE_OF_OBSERVATORY = {v: k for k, v in OBSERVAT.items()}

#: 사이트 코드 → `[site.<이름>]` 절 이름.
SITE_SECTION = {'KMTC': 'ctio', 'KMTS': 'saao', 'KMTA': 'sso', 'KMTK': 'kasi'}


def site_of_observatory(name: str) -> tuple[str, str]:
    """`OBSERVATORY` 값 → (사이트 코드, 정규화된 `OBSERVATORY`).

    받는 값은 `CTIO`/`SSO`/`SAAO`/`KASI` 넷뿐이다 (D-017) -- FITS `OBSERVAT`
    카드값과 같은 어휘다.  **모르는 값이면
    `ValueError`** -- 종전 `normalize_site()` 처럼 조용히 KASI 로
    떨어뜨리지 않는다.  사이트는 파일명 `<SITE>`·좌표·`ORIGIN` 을 함께 끌고
    가므로, 오타 하나가 자료의 정체를 통째로 바꾼다 (D-015 의 교훈).
    """
    up = (name or '').strip().upper()
    code = SITE_OF_OBSERVATORY.get(up)
    if code is None:
        raise ValueError(
            'OBSERVATORY=%r 를 모르겠다 -- CTIO / SSO / SAAO / KASI 중 '
            '하나여야 한다' % (name,))
    return code, up

#: 사이트 코드 → `ORIGIN` 기본값.  **`ORIGIN` = "이 파일이 생성된 곳"** (운영자
#: 확정 2026-08-21, Header_and_Refs v1.7): 관측소 raw 는 관측소 이름
#: (`OBSERVAT` 와 중복 감수 -- 레거시 계승), KASI(실험실) raw 는 `KASI`.
#: **D-017 이후 `OBSERVAT` 와 네 자리 모두 값이 같다** -- 뜻(생성처 vs 관측소)이
#: 달라 카드는 합치지 않는다.
#: KASI 서버 파이프라인 산출물(MEF·L1)이 `ORIGIN='KASI'` 를 갖는다.
#: `[site]`/`[site.<이름>]` 의 `origin` 키로 덮어쓸 수 있다 (ICS INI 카드).
ORIGIN_OF = {'KMTC': 'CTIO', 'KMTS': 'SAAO', 'KMTA': 'SSO', 'KMTK': 'KASI'}

#: 실재하는 과학 사이트 코드.  이 셋 밖은 모두 KASI 로 떨어진다.
REAL_SITES = ('KMTC', 'KMTS', 'KMTA')

#: 관측소가 아닌 자리(실험실·벤치·데모)의 사이트 코드.  **D-017 (2026-08-25)**
#: 로 구 `TESTBED`/`KMTT` 를 대체한다 -- `OBSERVAT` 넷이 전부 관측소 이름이 되게
#: 하려는 것이고, 그 자리에서 실제로 자료를 만드는 곳이 KASI 이기 때문이다.
KASI_SITE = 'KMTK'


def normalize_site(code: str) -> str:
    """사이트 코드를 정규화한다.  **`KMTC`/`KMTS`/`KMTA` 밖은 모두 `KMTK`.**

    운영자 확정 (2026-08-13, 코드는 D-017 로 개정 2026-08-25).  실재하는 관측소는
    셋뿐이므로, 모르는 값을 그대로 싣기보다 KASI 로 떨어뜨리는 것이 안전하다 --
    파일명 `<SITE>` 는
    converter 정규식(`^(KMTC|KMTS|KMTA|KMTK)[.]…`)이 받는 넷 중 하나여야 하고,
    낯선 코드는 정규식에 걸려 변환 자체가 fallback 경로로 빠진다.

    TC 가 보내는 `TELID` 에 사이트가 아닌 `KMTN`(pctcs 기본값, `pctcs.h:115`)이
    올 수 있어서 이 함수가 특히 필요하다.

    ⚠️ **떨어뜨리는 것이 곧 안전은 아니다.** 실제 관측 자료가 `KMTK` 이름으로
    저장되면 사이트 정체를 잃는다 -- 그래서 호출측은 정규화가 실제로 일어났을 때
    경고를 남겨야 한다 (`sequencer` 참고).
    """
    up = (code or '').strip().upper()
    return up if up in REAL_SITES else KASI_SITE


# ---------------------------------------------------------------------------
# 관측일 (파일명 `<YYYYMMDD>`)
# ---------------------------------------------------------------------------
#
# **운영자 확정 (2026-08-13, LEECU 협의 후).**  종전에는 UT 날짜를 그대로 썼으나
# (구판 OI-10 잠정), 이제 **사이트별 관측일**이 기준이다.  규칙은 UT 시각으로
# 주어졌다:
#
#     CTIO   UT 00:00~16:30 -> 그날 UT 날짜   /  16:30~24:00 -> 다음날
#     SSO    UT 00:00~01:30 -> 전날 UT 날짜   /  01:30~24:00 -> 그날
#     SAAO   UT 00:00~10:30 -> 전날 UT 날짜   /  10:30~24:00 -> 그날
#
# 근거는 "각 사이트 동지 때 관측 종료와 관측 시작 사이의 중간 시각".
#
# **세 경계가 모두 현지 12:30 이다** -- CTIO(UT−4) 16:30−4=12:30,
# SAAO(UT+2) 10:30+2=12:30, SSO(UT+11) 01:30+11=12:30.  숫자가 맞는지 검산할 때
# 이 불변식을 쓰면 된다.  (SSO 는 일광절약 +11 기준이다.)
#
# **이 규약이 종전 OI-12 를 구조적으로 없앤다.**  UT 날짜 기준에서는 날짜 경계가
# UT 자정이고 그게 CTIO(현지 20시)·SAAO(현지 22시)에서 **관측 시간대 안**이라,
# 프레임 하나가 경계를 걸치면 파일명과 `DATE-OBS` 의 날짜가 갈렸다.  관측일 기준의
# 경계는 현지 12:30 이라 **관측 중에는 지나가지 않는다.**
#
# 남는 위험: 현지 12:30 무렵의 주간 교정 프레임(bias/dome flat).  프레임 개시와
# 셔터 개방 사이 ~7.6초가 경계를 걸칠 수 있다.  드물고 교정 프레임에 한정된다.

#: 사이트 코드 -> UT 에 더할 보정.  더한 뒤 **날짜만** 취하면 관측일이 된다.
#: 부호에 주의 -- CTIO 만 양수다(경계가 UT 오후라 다음날로 넘겨야 하기 때문).
OBSDATE_SHIFT_MIN = {
    'KMTC': +7 * 60 + 30,     # 경계 UT 16:30  (현지 12:30, UT-4)
    'KMTS': -(10 * 60 + 30),  # 경계 UT 10:30  (현지 12:30, UT+2)
    'KMTA': -(1 * 60 + 30),   # 경계 UT 01:30  (현지 12:30, UT+11)
    'KMTK': 0,                # KASI(실험실)는 관측 야간이 없다 -- UT 날짜 그대로
}


def boundary_ut(site_code: str) -> str:
    """이 사이트의 관측일 경계 UT 시각, `'HH:MM'`.  기동 배너 표시용.

    보정이 `00:00` 으로 만드는 UT 시각이 곧 경계다 -- 그래서 보정 하나에서
    파생시킬 수 있고, 경계를 따로 적어 두지 않는다.  따로 적으면 보정과
    어긋날 수 있는 두 번째 사실이 생긴다.
    """
    site = normalize_site(site_code)
    shift = OBSDATE_SHIFT_MIN[site]
    if shift == 0:
        return '(없음)'
    m = (-shift) % (24 * 60)
    return f'{m // 60:02d}:{m % 60:02d}'


def observing_date(when: datetime, site_code: str) -> str:
    """`<YYYYMMDD>` -- 그 사이트의 **관측일** (운영자 확정 2026-08-13).

    보정을 더한 뒤 날짜만 취하는 한 줄로 세 사이트를 다 표현한다.  경계 시각을
    if 문으로 나열하지 않는 이유는, 그렇게 쓰면 경계에서 `<`/`<=` 를 잘못 잡는
    off-by-one 이 생기고 그게 **1년에 몇 번만 드러나는** 부류이기 때문이다.
    보정 방식은 경계에서 정확히 00:00 이 되므로 그 실수가 성립하지 않는다.

    Args:
        when: UT 시각 (timezone-aware).
        site_code: `KMTC`/`KMTS`/`KMTA`/`KMTK`.  그 밖은 `KMTK` 로 정규화된다.
    """
    site = normalize_site(site_code)
    shift = OBSDATE_SHIFT_MIN[site]
    ut = when.astimezone(timezone.utc) if when.tzinfo else when.replace(
        tzinfo=timezone.utc)
    return (ut + timedelta(minutes=shift)).strftime('%Y%m%d')


def controller_of(ccd: str) -> str:
    """이 chip 이 어느 컨트롤러 파일에 담기나."""
    up = ccd.upper()
    for tag, chips in CONTROLLERS:
        if up in chips:
            return tag
    raise KeyError(f'알 수 없는 chip: {ccd!r}')


def name_stem(site_code: str, suffix: str, ctrltag: str) -> str:
    """`<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>` -- **확장자 없는 이름** (2.3절).

    헤더의 `FILENAME` 에 싣는 형태다 (구 `ORIGNAME` 은 D-019 로 폐지 --
    `DETID` 필드 없는 `exposure_id()` 가 대신한다).  **확장자를 붙이지 않는 것이
    레거시 관례**다 -- 실측 헤더가 `FILENAME = 'KMTNk.20170209.044131'` 로
    `.fits` 없이 기록했다(`__reference/Legacy raw fits header samples/`).
    """
    return f'{site_code.upper()}.{suffix}.{ctrltag.upper()}'


def exposure_id(site_code: str, suffix: str) -> str:
    """`<SITE>.<YYYYMMDD>.<NNNNNN>` -- `EXPID` 카드 값 (raw spec 2.3절, **D-019**).

    `name_stem()` 과 달리 **컨트롤러 태그를 붙이지 않는다.**  그래서 pair 양쪽
    파일이 같은 값을 싣고, 짝을 잇는 **단일 키**가 된다 (5.9절 "반드시 동일") --
    폐지된 `PAIRFILE` 이 하려던 일을 카드 추가 없이 해낸다.

    ⚠️ 여기 담는 `suffix` 는 **카운터가 처음 배정한 것**이다.  충돌로 번호가
    밀리면 `FILENAME` 만 따라 올라가고 이 값은 그대로 남아, 둘의 불일치가 곧
    충돌 신호가 된다 (D-016 · D-019).
    """
    return f'{site_code.upper()}.{suffix}'


def physical_name(site_code: str, suffix: str, ctrltag: str) -> str:
    """`<SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits` -- 디스크 파일명 (raw spec 2.2절).

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
    """`Wrote` 에 싣는 CCD 단위 논리 이름.  **`KMTN` prefix 불변** (DevNote 3.2).

    ⚠️ 통보 규약의 정본은 **DevNote 3.2** 다 -- raw spec v1.4 에서 2.5절이
    삭제됐다(취득 SW 소관이라 규격에서 뺐다).  규격에 남은 것은 "`LASTFILE`
    은 실재 경로가 아니다" 한 줄이고 2.3절 5항으로 흡수됐다.
    """
    return f'KMTN{ccd.lower()}.{suffix}.fits'


def logical_path(data_dir: str, ccd: str, suffix: str) -> str:
    joined = os.path.join(data_dir, logical_name(ccd, suffix))
    return joined.replace(os.sep, '/')


# ---------------------------------------------------------------------------
# 노출 번호와 이름 충돌 처리 (D-016, raw spec 2.3절)
# ---------------------------------------------------------------------------
#
# **충돌 시 격리·개명 대신 노출 번호를 증가시켜 저장한다.**  구판의
# `clash/` 격리 + 시각 접미 + `NAMECLSH` 카드 세 겹은 폐지됐다 -- 격리는
# "덮어쓰지 않기"는 지켰지만 정상 산출물 흐름에서 프레임을 빼돌렸고, 하류
# 색인이 격리 디렉토리를 몰랐다.  번호 증가는 프레임을 정상 흐름에 남기고,
# 충돌 사실은 `FILENAME` 의 `DETID` 필드를 뗀 값 ≠ `EXPID` 비교 하나로 남는다 (D-019).
#
# 전제: 저장 디렉토리의 쓰기 주체는 **ICS 하나뿐**이다 (raw spec 2.3절 7항).

#: 노출 번호 공간 -- **`000000`–`999999`, 1000000 에서 되감는다** (**D-018**,
#: 2026-08-25).  파일명 `<NNNNNN>` 의 6자리를 전부 쓴다.
#:
#: 구 규칙은 `099999` 상한이었다 (레거시 관례) -- 6자리 형식에 다섯 자리만 쓰는
#: 셈이라 "6자리 고정폭"과 "10만 상한" 을 따로 기억해야 했고, 맨 앞 자리가 늘
#: `0` 이었다.  공간이 10배가 되면 **D-016 이 다루는 되감김 충돌 자체가
#: 드물어진다** -- 되감김이 그 충돌의 주된 원인이기 때문이다.
#:
#: 자릿수·zero-padding 규칙은 D-011 그대로라 **파일명 형식은 바뀌지 않는다.**
#: 기존 `0xxxxx` 자료와도 충돌하지 않는다 (새 공간이 옛 공간을 포함한다).
NUM_SPACE = 1_000_000


class NumberSpaceExhausted(Exception):
    """번호 공간 한 바퀴(**1000000회**, D-018)를 돌아도 빈 이름이 없다.

    상한이 10만에서 100만으로 늘어도 **종료 보장은 그대로**다 -- 여전히 "공간
    한 바퀴" 이고, 루프가 그 횟수에 이르렀다면 저장 자리가 실제로 가득 찬 것이다
    (D-016 2항).

    이 규격의 **유일한 저장 실패 조건**이다 -- 호출측은 ERROR 를 내고
    저장하지 않는다.
    """


def pair_tag(ctrltag: str) -> str:
    """짝의 컨트롤러 태그 (`FILENAME` `DETID` 필드 `.MK`↔`.NT` 치환 규약)."""
    tags = [t for t, _ in CONTROLLERS]
    return tags[1] if ctrltag.upper() == tags[0] else tags[0]


def pair_paths(data_dir: str, site_code: str, date_part: str,
               number: int) -> tuple[str, str]:
    """후보 번호의 MK·NT 두 경로."""
    suffix = f'{date_part}.{number % NUM_SPACE:06d}'
    return tuple(physical_path(data_dir, site_code, suffix, tag)
                 for tag, _ in CONTROLLERS)


def resolve_pair_number(data_dir: str, site_code: str, date_part: str,
                        number: int, *, check: bool = True) -> int:
    """쓸 노출 번호를 정한다 -- D-016 선검사 루프.

    쓰기 전에 후보 N 의 **MK·NT 두 경로를 모두 선검사**하고, 점유 시 N+1 로
    재검사한다 (**999999** 넘으면 000000 으로 되감음, D-018).  +1 이
    **1000000회**(공간 한 바퀴)를 초과하면 `NumberSpaceExhausted` -- 저장하지
    않는다.  실패 조건은 이것 하나뿐이다.

    Args:
        check: False 면 존재 확인을 건너뛰고 그대로 돌려준다
            (`write_fits=false` 메시지 전용 모드 -- 실제로 쓰지 않으므로
            충돌 개념이 없다).

    Returns:
        확정 번호.  호출측은 이 값으로 **카운터를 동기화**한다 (D-016 3항)
        -- 점프가 있으면 WARNING 로그도 남긴다 (`sequencer` 참조).
    """
    start = number % NUM_SPACE
    if not check:
        return start
    n = start
    for _ in range(NUM_SPACE):
        if not any(os.path.exists(p)
                   for p in pair_paths(data_dir, site_code, date_part, n)):
            return n
        n = (n + 1) % NUM_SPACE
    raise NumberSpaceExhausted(
        f'{site_code}.{date_part} 의 번호 공간 {NUM_SPACE}개가 전부 점유됐다 '
        '-- 저장하지 않는다 (D-016)')

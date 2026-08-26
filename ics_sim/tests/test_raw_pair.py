#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Raw FITS pair — 이름·번호·충돌 처리 (D-010/D-011/D-012/**D-016**/**D-019**).

규격: `raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.7.md` 2장,
`mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` 2.1·3절.

**한 노출이 만드는 것**

    물리 파일 2개   <SITE>.<날짜>.<번호>.MK.fits  /  .NT.fits
    Wrote 통보 4회  KMTN{m,k,n,t}.<날짜>.<번호>.fits   (논리 이름, KMTN 불변)

`test_obsagent_contract.py` 가 통보 쪽(4회·FitsNum·타임아웃)을 지키고,
`test_raw_header.py` 가 헤더 내용을 지키고, 이 파일은 **저장 쪽과 그 둘의
대응 + D-016 충돌 처리**를 지킨다.

`write_fits=false` 인 기본 설정에서는 물리 파일을 만들지 않으므로, 여기서는
`paths__write_fits=True` + `tmp_path` 로 실제로 쓰게 한다 (astropy 필요).
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import pytest

from conftest import drive, make_config

from ics_sim import rawpair
from ics_sim.config import SimConfig
from ics_sim.telemetry import TelemetryRelay

fits = pytest.importorskip('astropy.io.fits',
                           reason='물리 저장 검증에는 astropy 가 필요하다')

SCRIPT = ['OBS>ICS DARK pair', 'OBS>ICS EXP 5', 'OBS>ICS GO 1']


def _run(tmp_path, **over):
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path),
                      **over)
    return drive(SCRIPT, cfg), cfg


def _written(tmp_path) -> list[str]:
    return sorted(p for p in os.listdir(tmp_path) if p.endswith('.fits'))


# -- 저장 단위 -------------------------------------------------------------

def test_one_exposure_writes_exactly_two_files(tmp_path):
    """노출 1회 = 물리 파일 2개.  CCD당 1개(4개)가 아니다 (raw spec 2.1절)."""
    _run(tmp_path)
    assert len(_written(tmp_path)) == 2


def test_physical_names_are_site_coded_pair(tmp_path):
    """`<SITE>.<날짜>.<번호>.<MK|NT>.fits` (raw spec 2.2절, D-011)."""
    _, cfg = _run(tmp_path)
    names = _written(tmp_path)
    site = cfg.node.telid
    assert [n.split('.')[0] for n in names] == [site, site]
    assert sorted(n.split('.')[-2] for n in names) == ['MK', 'NT']
    # 6자리 zero-padding 은 선택이 아니다 (converter 정규식이 걸려 있다)
    for n in names:
        num = n.split('.')[2]
        assert len(num) == 6 and num.isdigit(), n
    # pair 양쪽의 날짜·번호가 같아야 한다
    assert len({tuple(n.split('.')[1:3]) for n in names}) == 1


def test_no_kmtn_file_on_disk(tmp_path):
    """논리 이름은 디스크에 없다 -- `LASTFILE` 이 실재 경로가 아니다 (2.3절 5항)."""
    run, _ = _run(tmp_path)
    assert not [n for n in _written(tmp_path) if n.startswith('KMTN')]
    # 그런데 Wrote 는 그 이름을 싣는다
    assert run.count('Wrote LASTFILE=') >= 4


# -- 통보 단위 -------------------------------------------------------------

def test_four_wrote_with_legacy_logical_names(tmp_path):
    """`Wrote` 4회, 논리 이름은 `KMTN<c>` 불변 (DevNote 3.2)."""
    run, cfg = _run(tmp_path)
    relays = [m for m in run.to('OBS') if 'Wrote LASTFILE=' in m]
    assert len(relays) == 4
    for ccd in cfg.node.ccds:
        assert any(f'KMTN{ccd.lower()}.' in m for m in relays), ccd


def test_logical_name_keeps_kmtn_even_when_site_is_not_ctio(tmp_path):
    """사이트 코드가 `KMTA` 여도 논리 이름은 `KMTN` 이다.

    OBSAgent 가 `"KMTN"` 위치 +6 부터 15자를 잘라 `FitsNum` 으로 쓰므로
    (DevNote 3.2) 이걸 사이트 코드로 바꾸면 파싱이 깨진다.
    """
    run, cfg = _run(tmp_path, node__observatory='SSO', node__site='sso', node__telid='KMTA')
    assert cfg.node.telid == 'KMTA'
    assert [n.split('.')[0] for n in _written(tmp_path)] == ['KMTA', 'KMTA']
    relays = [m for m in run.to('OBS') if 'Wrote LASTFILE=' in m]
    assert len(relays) == 4
    assert all('KMTN' in m for m in relays)
    assert not any('KMTA.' in m for m in relays)


def test_two_messages_from_one_file_share_the_rate(tmp_path):
    """한 파일에서 나온 두 통보는 같은 RATE 를 싣는다 (DevNote 3.2)."""
    run, _ = _run(tmp_path)
    rates: dict[str, str] = {}
    for m in run.to('OBS'):
        if 'Wrote LASTFILE=' not in m:
            continue
        name = m.split('LASTFILE=')[1].split()[0]
        ccd = os.path.basename(name)[4]          # KMTN<c>....
        rates[ccd] = m.split('RATE=')[1].split()[0]
    assert rates['m'] == rates['k'], rates       # MK 파일
    assert rates['n'] == rates['t'], rates       # NT 파일


# -- 헤더 정체성 (D-016) -----------------------------------------------------

def _headers(tmp_path) -> dict[str, object]:
    out = {}
    for n in _written(tmp_path):
        with fits.open(os.path.join(tmp_path, n)) as hdul:
            out[n] = dict(hdul[0].header)
    return out


def test_expid_format_and_pair_identity():
    """`EXPID` = `<SITE>.<YYYYMMDD>.<NNNNNN>` — **태그 없음 · pair 동일** (D-019).

    형식이 규약인 이유: 하류가 `FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀 값과 **문자열
    비교**해 충돌을 판별한다(규격 2.3절).  한 자리라도 어긋나면 그 비교가 늘
    참이 되어 **충돌이 조용히 안 잡힌다.**

    ⚠️ 값이 `<SITE>` 접두로 시작하는 것이 **형 사고를 막는 구조**이기도 하다 --
    구 `EXPID`(`'20260811.000001'`)는 숫자로 읽혀 실수 카드가 됐고 6자리
    zero-padding 이 파괴됐다 (DevNote 11.13.2).  접두가 있으면 그 여지가 없다.
    """
    import re

    expid = rawpair.exposure_id('KMTA', '20260821.123450')
    assert expid == 'KMTA.20260821.123450'
    assert re.fullmatch(r'KMT[CSAK]\.\d{8}\.\d{6}', expid), expid
    # 컨트롤러 태그가 붙으면 안 된다 -- 붙는 순간 pair 상이가 되어 5.9절 위반.
    assert not expid.endswith(('.MK', '.NT'))
    # 같은 노출이면 두 컨트롤러가 같은 값을 얻는다 (짝을 잇는 단일 키).
    assert rawpair.exposure_id('KMTA', '20260821.123450') == expid
    # 숫자로 읽히지 않는다 -- 실수 카드 사고(11.13.2)의 구조적 방어.
    try:
        float(expid)
    except ValueError:
        pass
    else:
        raise AssertionError('EXPID 가 숫자로 읽힌다 -- zero-padding 이 위험하다')


def test_identity_cards_present_and_consistent(tmp_path):
    """`FILENAME`(유일 키) + `EXPID`(카운터 배정 식별자) -- 모든 파일에 항상
    (raw spec 2.3절 4항).  구판의 `UNIQNAME`/`CTRLTAG`/`CHIPS`/`PAIRFILE`
    계열은 폐지됐다 -- pair 식별은 `FILENAME` `DETID` 필드 `.MK`/`.NT` 로 충분하다."""
    _run(tmp_path)
    hdrs = _headers(tmp_path)
    assert len(hdrs) == 2
    by_tag = {str(h['DETID']).strip(): h for h in hdrs.values()}
    assert set(by_tag) == {'MK', 'NT'}
    for tag, h in by_tag.items():
        assert str(h['FILENAME']).endswith(f'.{tag}')
        # ⚠️ `EXPID` 에는 컨트롤러 태그가 **없다** (D-019) -- pair 양쪽 동일.
        assert not str(h['EXPID']).strip().endswith(('.MK', '.NT'))
        # 평시 불변식(충돌 없음): `FILENAME` 의 `DETID` 필드(`.MK`/`.NT`)를 뗀
        # 값 == `EXPID`.  이 등식이 깨진 것이 곧 충돌 신호다 (2.3절).
        assert str(h['FILENAME']).strip().rsplit('.', 1)[0] == \
            str(h['EXPID']).strip()
    # 짝 이름은 `DETID` 필드 치환으로 유도된다 (PAIRFILE 카드는 없다)
    mk_stem = str(by_tag['MK']['FILENAME'])
    assert mk_stem[:-2] + 'NT' == str(by_tag['NT']['FILENAME'])


def test_identifier_cards_stay_strings(tmp_path):
    """식별자 카드가 **숫자 카드로 저장되면 안 된다** (raw spec 5.0절).

    숫자 카드는 zero-padding 을 파괴한다 (`'…000010'` -> `…00001`).  검사는
    값이 아니라 **카드의 형**을 본다.
    """
    _run(tmp_path)
    for h in _headers(tmp_path).values():
        for key in ('FILENAME', 'EXPID', 'DETID', 'OBSERVAT', 'ORIGIN',
                    'BUNIT'):
            assert isinstance(h[key], str), f'{key}: {type(h[key])}'
        assert re.fullmatch(r'KMT[CSAK]\.\d{8}\.\d{6}\.(MK|NT)',
                            str(h['FILENAME'])), h['FILENAME']


@pytest.mark.parametrize('suffix', [
    '20260811.000001',   # 끝자리가 0 이 아니라 실수 왕복이 우연히 성립하는 값
    '20260811.000010',   # 000010 -> 00001
    '20260811.000100',   # 000100 -> 0001
    '20260811.010000',   # 010000 -> 01
])
def test_serial_keeps_its_zero_padding(tmp_path, suffix):
    """식별자의 6자리 zero-padding 이 헤더를 왕복해도 살아남아야 한다.

    템플릿이 `FILENAME`/`EXPID` 를 문자열 형으로 못박으므로(rawcards)
    실수 카드가 될 수 없다 -- 그 성질을 왕복으로 확인한다.
    """
    from ics_sim import rawcards
    from ics_sim.fitsout import apply_cards
    stem = rawpair.name_stem('KMTA', suffix, 'MK')
    cards = rawcards.render({'FILENAME': stem, 'EXPID': stem})
    hdr = fits.Header()
    apply_cards(hdr, [c for c in cards
                      if c[0] in ('FILENAME', 'EXPID')])
    for key in ('FILENAME', 'EXPID'):
        assert isinstance(hdr[key], str), f'{key}: {type(hdr[key])}'
        assert f'.{suffix}.' in hdr[key], f'{key}={hdr[key]!r}'


def test_filename_matches_the_actual_file(tmp_path):
    """`FILENAME` 은 자기 파일 이름이며 **확장자를 뗀 형태**다 (2.3절).

    레거시 실측 헤더가 `FILENAME = 'KMTNk.20170209.044131'` 로 `.fits` 없이
    기록했다 (`raw_fits_spec/__reference/Legacy raw fits header samples/`).
    """
    _run(tmp_path)
    for name, h in _headers(tmp_path).items():
        assert str(h['FILENAME']).strip() == os.path.splitext(name)[0]
        assert not str(h['FILENAME']).endswith('.fits')


def test_observat_agrees_with_the_filename_site_code(tmp_path):
    """파일명 `<SITE>` 와 `OBSERVAT` 는 일치해야 한다 (raw spec 2.2절).

    converter v2.2.0 이 이 둘을 교차 검증한다 -- **유일한 변환 하드 실패**다.
    """
    _run(tmp_path, node__observatory='SSO', node__site='sso', node__telid='KMTA')
    for name, h in _headers(tmp_path).items():
        assert (str(h['OBSERVAT']).strip()
                == rawpair.OBSERVAT[name.split('.')[0]] == 'SSO')


# -- D-016 충돌 처리: 번호 증가 · 되감음 · 상한 ------------------------------

def test_collision_bumps_the_number_and_keeps_both_files(tmp_path):
    """이름이 겹치면 **번호를 올려 저장한다** -- 격리·개명이 아니다 (D-016).

    충돌 사실은 `FILENAME` 의 `DETID` 필드를 뗀 값 ≠ `EXPID` 비교 하나로 남는다 (카드 존재가
    아니다).  구판의 `clash/` 디렉토리·`NAMECLSH` 카드·WARNING 메시지는
    전부 폐지됐다.
    """
    _run(tmp_path)
    first = _written(tmp_path)
    assert len(first) == 2

    # expnum 이 다시 1 이므로 같은 이름을 쓰려 한다 -> 선검사가 번호를 올린다
    run = drive(SCRIPT, make_config(paths__write_fits=True,
                                    paths__data_dir=str(tmp_path)))
    names = _written(tmp_path)
    assert len(names) == 4, '충돌 프레임도 정상 흐름에 남아야 한다'
    assert first[0] in names and first[1] in names, '기존 파일을 덮어썼다'
    assert not os.path.isdir(os.path.join(tmp_path, 'clash')), (
        '격리 디렉토리는 폐지됐다 (D-016)')
    # 개명 통보도 폐지 -- WARNING 로그만 남는다
    assert not run.find('already exists')

    new = [n for n in names if n not in first]
    for n in new:
        with fits.open(os.path.join(tmp_path, n)) as hdul:
            h = hdul[0].header
        stem = os.path.splitext(n)[0]
        assert str(h['FILENAME']).strip() == stem       # 실제 저장명
        assert str(h['EXPID']).strip() != \
            str(h['FILENAME']).strip().rsplit('.', 1)[0], (
                '충돌 신호는 FILENAME 의 `DETID` 필드를 뗀 값 != EXPID 다 (D-019)')
        # 번호만 다르고 형식은 같다 (D-011 불변 -- find_pair() 영향 없음)
        assert re.fullmatch(r'KMT[CSAK]\.\d{8}\.\d{6}\.(MK|NT)', stem)
    # pair 양쪽이 같은 번호로 함께 증가한다
    assert len({tuple(n.split('.')[1:3]) for n in new}) == 1


def test_counter_is_synchronized_to_the_final_number(tmp_path):
    """확정 번호로 카운터를 동기화한다 (D-016 3항).

    동기화가 없으면 다음 노출이 또 같은 자리에서 충돌해 **노출마다 선검사
    루프를 다시 돈다** -- 번호 점프는 한 번이어야 한다.
    """
    _run(tmp_path)                    # 000001 점유
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path))
    drive(['OBS>ICS DARK pair', 'OBS>ICS EXP 5', 'OBS>ICS GO 2'], cfg,
          settle=1.0)
    nums = sorted({n.split('.')[2] for n in _written(tmp_path)})
    # 1회차 000001, 2회차 GO 2 -> 충돌로 000002 + 동기화된 000003
    assert nums == ['000001', '000002', '000003'], nums


def test_resolve_pair_number_wraps_and_caps(tmp_path, monkeypatch):
    """되감음(**999999** -> 000000)과 상한(공간 한 바퀴) -- D-016 1·2항 + D-018.

    ⚠️ **경계가 `099999` 에서 `999999` 로 옮겨졌다** (D-018, 2026-08-25).
    구 경계를 그대로 두면 `100000` 부터가 통째로 안 쓰이는 자리가 된다.
    """
    # 되감음: 999999 가 점유되어 있으면 000000 으로 넘어간다
    last = rawpair.NUM_SPACE - 1
    assert last == 999999, 'D-018: 번호 공간은 000000-999999 다'
    taken = {os.path.normpath(p) for p in rawpair.pair_paths(
        str(tmp_path), 'KMTA', '20260822', last)}
    monkeypatch.setattr(os.path, 'exists',
                        lambda p: os.path.normpath(p) in taken)
    got = rawpair.resolve_pair_number(str(tmp_path), 'KMTA', '20260822',
                                      last)
    assert got == 0

    # 상한: 전부 점유면 NumberSpaceExhausted -- 유일한 저장 실패 조건
    monkeypatch.setattr(os.path, 'exists', lambda p: True)
    with pytest.raises(rawpair.NumberSpaceExhausted):
        rawpair.resolve_pair_number(str(tmp_path), 'KMTA', '20260822', 0)


def test_resolve_pair_number_checks_both_members(tmp_path):
    """선검사는 **MK·NT 두 경로 모두**다 -- 한쪽만 있어도 그 번호는 점유다."""
    date_part = '20260822'
    mk, nt = rawpair.pair_paths(str(tmp_path), 'KMTA', date_part, 1)
    os.makedirs(os.path.dirname(nt) or str(tmp_path), exist_ok=True)
    open(nt, 'w').close()             # NT 만 존재
    assert rawpair.resolve_pair_number(str(tmp_path), 'KMTA', date_part,
                                       1) == 2
    assert rawpair.resolve_pair_number(str(tmp_path), 'KMTA', date_part,
                                       1, check=False) == 1


def test_expnum_wraps_at_the_number_space():
    """카운터 자체도 **000000–999999** 순환이다 (D-016 1항 · D-018).

    되감지 않으면 `:06d` 가 7자리를 내놓아 파일명 6자리 고정폭이 깨진다.
    구 경계(`99999`)에서는 넘어가지 않는다는 것도 함께 못박는다 -- 그 자리가
    아직 되감기면 새 공간의 90%가 사라진 것이다.
    """
    from ics_sim.state import IcsState
    st = IcsState()
    st.expnum = 99999
    st.advance()
    assert st.expnum == 100000        # 구 경계에서는 되감지 않는다
    st.expnum = rawpair.NUM_SPACE - 1
    st.advance()
    assert st.expnum == 0
    assert len(f'{rawpair.NUM_SPACE - 1:06d}') == 6


# -- sentinel (raw spec 5.0절) ----------------------------------------------

def test_fits_sentinels_follow_the_spec_not_the_message_layer():
    """FITS 쪽 TC 중계 카드는 전부 문자열이고 결측은 `'NC'` 다.

    메시지 계층은 `'0'` 을 그대로 쓴다 -- 레거시 재현이 필요한 쪽이라
    분리해 두었다 (DevNote 11.2, C-9).
    """
    telem = TelemetryRelay(SimConfig(), None)
    msg = telem.header_dict()
    hdr = telem.fits_header_dict('2026-08-11T12:00:00.000')

    # 메시지 계층: 레거시 관례 그대로
    assert msg['SECZ'] == '0' and msg['ALT'] == '0'
    # FITS 카드: 문자열 sentinel 하나로 통일 (형이 문자열이므로)
    assert hdr['SECZ'] == 'NC'
    assert hdr['MCPOS'] == 'NC'
    assert hdr['DSSTAT'] == 'NC'
    assert hdr['TCSLINK'] == 'Down'       # 질의 성패에서 유도
    from ics_sim.rawcards import RELAY_CARDS
    for key in RELAY_CARDS:
        assert key in hdr, f'{key} 카드 몫이 빠졌다'


def test_date_obs_is_always_written(tmp_path):
    """`DATE-OBS` 는 **무조건 들어간다** (raw spec 5.4절 필수, 출처 ICS)."""
    _run(tmp_path)
    vals = set()
    for name, h in _headers(tmp_path).items():
        assert h['DATE-OBS'], name
        assert re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}',
                            str(h['DATE-OBS'])), h['DATE-OBS']
        assert str(h['TIMESYS']).strip() == 'UTC'
        vals.add(str(h['DATE-OBS']))
    # pair 양쪽이 같아야 한다 (셔터는 하나, 노출도 하나)
    assert len(vals) == 1, vals


def test_date_obs_is_never_silently_substituted():
    """근거가 없으면 **현재 시각으로 채우지 않고** 카드를 비운다 (C-6)."""
    telem = TelemetryRelay(SimConfig(), None)
    assert 'DATE-OBS' not in telem.fits_header_dict('')
    assert telem.fits_header_dict('2026-08-11T12:00:00.000')['DATE-OBS']
    # 기본값이 없어야 호출측이 빠뜨릴 수 없다
    import inspect
    sig = inspect.signature(telem.fits_header_dict)
    assert sig.parameters['date_obs'].default is inspect.Parameter.empty


def test_header_carries_detector_identity(tmp_path):
    """헤더만으로 어느 검출기 pair 인지 알 수 있어야 한다 (`DETID`/`CHMAP_*`)."""
    _run(tmp_path)
    hdrs = list(_headers(tmp_path).values())
    assert len({str(h['DETID']) for h in hdrs}) == 2
    for h in hdrs:
        assert h['CHMAP_LT'] and h['CHMAP_RB']


# -- D-015: 실효 사이트가 파일명·헤더까지 일관되게 흘러가나 --------------------

def test_detected_site_wins_over_the_ini_all_the_way_to_the_header(tmp_path):
    """**실효 사이트 하나가 셋을 함께 정한다** -- 파일명 `<SITE>`·`OBSERVAT`·
    관측일 경계가 **모두 같은 사이트**여야 한다 (raw spec 2.2절).

    구판은 관측일만 판정값(`state.site_code`)을 쓰고 파일명 `<SITE>` 와
    `OBSERVAT` 는 ini 원값(`cfg.node.telid`)을 썼다 -- 판정과 ini 가 다르면
    한 파일 안에서 사이트가 갈렸고, 기동 배너가 찍는 파일명 예시와도
    어긋났다.  **경고만 나고 자료는 조용히 섞이는** 부류다.
    """
    # ini 는 SSO(KMTA) 라고 선언하는데 실효 사이트를 KASI(KMTK) 로 강제한다 --
    # 둘이 갈렸을 때 파일명·헤더·관측일이 **함께** 실효값을 따라가는지 본다.
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path),
                      node__observatory='SSO', node__site='sso', node__telid='KMTA')
    from ics_sim.app import IcsSim
    original = IcsSim._resolve_site
    IcsSim._resolve_site = lambda self: ('KMTK', '(시험 강제)')
    try:
        drive(SCRIPT, cfg)
    finally:
        IcsSim._resolve_site = original

    names = _written(tmp_path)
    assert names, '저장이 안 됐다'
    assert [n.split('.')[0] for n in names] == ['KMTK', 'KMTK'], names
    for name, h in _headers(tmp_path).items():
        assert str(h['OBSERVAT']).strip() == 'KASI', name
        # 관측일도 같은 사이트 규칙(KMTK = UT 날짜 그대로)이어야 한다
        iso = str(h['DATE-OBS'])
        when = datetime.strptime(iso, '%Y-%m-%dT%H:%M:%S.%f').replace(
            tzinfo=timezone.utc)
        assert name.split('.')[1] == rawpair.observing_date(when, 'KMTK')


# -- D-016 1항: 번호 공간을 명령 입구에서 강제한다 ---------------------------

@pytest.mark.parametrize('bad', ['1000000', '1234567', '-5'])
def test_expnum_command_rejects_values_outside_the_number_space(bad):
    r"""`EXPNUM <n>` 은 카운터로 들어오는 유일한 외부 경로다 -- 범위를 안 막으면
    7자리 suffix 나 부호가 자리를 먹는 이름이 와이어로 나간다 (DevNote 3.4 의
    "Filename= 뒤 15자" 파서 · converter 정규식 `\d{6}`)."""
    run = drive([f'OBS>ICS expnum {bad}'])
    replies = run.find('EXPNUM')
    assert any('Invalid exposure number' in m for m in replies), replies


def test_expnum_command_accepts_the_edges_of_the_space():
    for good in ('0', '99999', '100000', '999999'):   # D-018: 6자리 전부
        run = drive([f'OBS>ICS expnum {good}'])
        replies = [m for m in run.find('EXPNUM') if 'Filename=' in m]
        assert replies, good
        assert not any('Invalid' in m for m in run.find('EXPNUM')), good


# -- 5.9절 "반드시 동일" 의 구조적 보장 --------------------------------------

def test_pair_common_facts_are_snapshotted_once_per_exposure(tmp_path):
    """pair 양쪽에 같은 값이 실려야 하는 사실은 **노출당 한 번만** 질의한다
    (raw spec 5.9절).

    컨트롤러별 저장 태스크가 각자 질의하면 두 파일의 스냅샷 시각이
    `write_delay + skew` 만큼 벌어진다 -- 시뮬 백엔드는 고정값을 돌려주므로
    **시험은 통과하는 채로 실기에서만 값이 갈리는** 부류다.  그래서 값이 아니라
    **질의 횟수**를 본다.
    """
    import ics_sim.hardware.sim as simmod
    calls: dict[str, int] = {'sensors': 0, 'telem': 0, 'info': 0}
    orig = (simmod.SimBackend.sensors, simmod.SimBackend.controller_telemetry,
            simmod.SimBackend.controller_info)

    def counted(key, fn):
        def wrapper(self, *a, **kw):
            calls[key] += 1
            return fn(self, *a, **kw)
        return wrapper

    simmod.SimBackend.sensors = counted('sensors', orig[0])
    simmod.SimBackend.controller_telemetry = counted('telem', orig[1])
    simmod.SimBackend.controller_info = counted('info', orig[2])
    try:
        _run(tmp_path)
    finally:
        (simmod.SimBackend.sensors, simmod.SimBackend.controller_telemetry,
         simmod.SimBackend.controller_info) = orig

    assert len(_written(tmp_path)) == 2
    for key, n in calls.items():
        assert n == 1, f'{key} 를 노출 1회에 {n}번 질의했다 (pair 공통 사실은 1번)'


def test_exposure_metadata_is_frozen_at_frame_time(tmp_path):
    """노출 메타데이터는 프레임 시점에 굳는다 -- `_store` 는 `write_delay` 뒤에
    도는데 그 사이 다음 관측의 `object`/`exp` 가 들어오면 프레임 N 의 헤더에
    프레임 N+1 의 값이 실린다 (raw spec 5.4절, `suffix` 와 같은 이유 12.10).

    노출이 끝난 직후(저장 태스크가 아직 자고 있을 때) 새 `object`/`exp` 를
    밀어 넣고, 저장된 헤더가 **원래 값**을 유지하는지 본다.
    """
    from conftest import drive_at
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path))
    # `Wrote` 직전(=IDLE 통보 시점)에 다음 관측 설정을 밀어 넣는다
    drive_at(['OBS>ICS OBJECT firstfield', 'OBS>ICS EXP 5', 'OBS>ICS GO 1'],
             marker='EXPSTATUS=IDLE',
             inject=['OBS>ICS OBJECT nextfield', 'OBS>ICS EXP 60'],
             cfg=cfg, settle=1.2)
    hdrs = _headers(tmp_path)
    assert len(hdrs) == 2, list(hdrs)
    for name, h in hdrs.items():
        assert str(h['OBJECT']).strip() == 'firstfield', (name, h['OBJECT'])
        assert h['EXPTIME'] == 5, (name, h['EXPTIME'])


# -- 외부 INITIALIZE 가 프레임 이름·통보를 훼손하지 못한다 -------------------

@pytest.mark.parametrize('injected', [
    'CHA>K.IC INITIALIZE 0394',          # 레거시 IC 관례: 점 없는 4자리
    'CHA>K.IC INITIALIZE 20260818.abcdef',
    'CHA>K.IC INITIALIZE ../../etc/passwd',
])
def test_external_initialize_cannot_break_the_frame(tmp_path, injected):
    """`INITIALIZE <suffix>` 는 형식 검증이 없는 **외부 입력**이다 (레거시
    관례 -- 실측상 CHA 노드가 쓴다, DevNote 6.3).  그 값이 프레임 중간에
    들어와도 **노출 규약이 깨지면 안 된다** (DevNote 3장).

    구판은 저장 직전에 `st.channel(ccds[0]).suffix` 를 **다시 읽어** 파일명을
    정했고, D-016 선검사가 그 값을 번호로 파싱하면서 노출 태스크가 죽었다 --
    `EXPSTATUS=IDLE` 도 `Wrote` 도 나가지 않아 OBSAgent 가 창 초과로
    `opause` 에 빠지는 경로였다.  이름은 프레임이 정한다.
    """
    from conftest import drive_at
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path))
    run = drive_at(['OBS>ICS DARK pair', 'OBS>ICS EXP 5', 'OBS>ICS GO 1'],
                   marker='EXPSTATUS=READOUT', inject=injected, cfg=cfg,
                   settle=1.2)
    # 규약: IDLE 전이 1회 · Wrote 중계 4회
    assert run.count('EXPSTATUS=IDLE') >= 1, '노출 태스크가 죽었다 (IDLE 유실)'
    relays = [m for m in run.to('OBS') if 'Wrote LASTFILE=' in m]
    assert len(relays) == 4, f'Wrote 4회가 아니다: {len(relays)}'
    # 파일명은 프레임이 정한 규격 형식 그대로여야 한다 (외부 값이 안 섞인다)
    names = _written(tmp_path)
    assert len(names) == 2, names
    for n in names:
        assert re.fullmatch(r'KMT[CSAK]\.\d{8}\.\d{6}\.(MK|NT)\.fits', n), n

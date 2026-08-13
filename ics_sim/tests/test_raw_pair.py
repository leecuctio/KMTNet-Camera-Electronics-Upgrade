#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Raw FITS pair — 저장 단위와 통보 단위의 분리 (D-010/D-011/D-012).

규격: `raw_fits_spec/KMT_CEU_Raw_FITS_Pair_Spec_v1.2.md` 2.3·2.5·5.0·5.1·5.2절,
`mef_fits_spec/KMT_CEU_Science_MEF_ICD_L0AmpRaw_v4.1.md` 2.1·3절.
변경점 C-8 / C-9 / C-16.

**한 노출이 만드는 것**

    물리 파일 2개   <SITE>.<날짜>.<번호>.MK.fits  /  .NT.fits
    Wrote 통보 4회  KMTN{m,k,n,t}.<날짜>.<번호>.fits   (논리 이름, KMTN 불변)

`test_obsagent_contract.py` 가 통보 쪽(4회·FitsNum·타임아웃)을 지키고, 이
파일은 **저장 쪽과 그 둘의 대응**을 지킨다.  둘을 나눠 둔 이유: 통보 규약이
깨지면 관측이 멈추고, 저장 규약이 깨지면 converter 가 못 읽는다 -- 증상이
전혀 다른 곳에서 나타나므로 실패한 테스트 이름이 원인을 가리켜야 한다.

`write_fits=false` 인 기본 설정에서는 물리 파일을 만들지 않으므로, 여기서는
`paths__write_fits=True` + `tmp_path` 로 실제로 쓰게 한다 (astropy 필요).
"""

from __future__ import annotations

import os
import re

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
    """노출 1회 = 물리 파일 2개.  CCD당 1개(4개)가 아니다 (규격 2.1절)."""
    _run(tmp_path)
    assert len(_written(tmp_path)) == 2


def test_physical_names_are_site_coded_pair(tmp_path):
    """`<SITE>.<날짜>.<번호>.<MK|NT>.fits` (규격 2.3절, D-011)."""
    _, cfg = _run(tmp_path)
    names = _written(tmp_path)
    site = cfg.node.telid
    assert [n.split('.')[0] for n in names] == [site, site]
    assert sorted(n.split('.')[-2] for n in names) == ['MK', 'NT']
    # 6자리 zero-padding 은 선택이 아니다 (규격 2.3절 경고 블록)
    for n in names:
        num = n.split('.')[2]
        assert len(num) == 6 and num.isdigit(), n
    # pair 양쪽의 날짜·번호가 같아야 한다
    assert len({tuple(n.split('.')[1:3]) for n in names}) == 1


def test_no_kmtn_file_on_disk(tmp_path):
    """논리 이름은 디스크에 없다 -- `LASTFILE` 이 실재 경로가 아니다 (2.5절 말미)."""
    run, _ = _run(tmp_path)
    assert not [n for n in _written(tmp_path) if n.startswith('KMTN')]
    # 그런데 Wrote 는 그 이름을 싣는다
    assert run.count('Wrote LASTFILE=') >= 4


# -- 통보 단위 -------------------------------------------------------------

def test_four_wrote_with_legacy_logical_names(tmp_path):
    """`Wrote` 4회, 논리 이름은 `KMTN<c>` 불변 (규격 2.5절)."""
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
    run, cfg = _run(tmp_path, node__site='sso', node__telid='KMTA')
    assert cfg.node.telid == 'KMTA'
    assert [n.split('.')[0] for n in _written(tmp_path)] == ['KMTA', 'KMTA']
    relays = [m for m in run.to('OBS') if 'Wrote LASTFILE=' in m]
    assert len(relays) == 4
    assert all('KMTN' in m for m in relays)
    assert not any('KMTA.' in m for m in relays)


def test_two_messages_from_one_file_share_the_rate(tmp_path):
    """한 파일에서 나온 두 통보는 같은 RATE 를 싣는다 (규격 2.5절 말미)."""
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


# -- 헤더 정체성 (5.1 / 5.2) ----------------------------------------------

def _headers(tmp_path) -> dict[str, object]:
    out = {}
    for n in _written(tmp_path):
        with fits.open(os.path.join(tmp_path, n)) as hdul:
            out[n] = dict(hdul[0].header)
    return out


def test_identity_cards_present_and_consistent(tmp_path):
    """규격 5.2절의 pair 식별 카드."""
    _run(tmp_path)
    hdrs = _headers(tmp_path)
    assert len(hdrs) == 2
    by_tag = {h['CTRLTAG']: h for h in hdrs.values()}
    assert set(by_tag) == {'MK', 'NT'}

    for tag, want in (('MK', ('M', 'K')), ('NT', ('N', 'T'))):
        h = by_tag[tag]
        assert h['CHIP1'] == want[0]
        assert h['CHIP2'] == want[1]
        assert h['CHIPS'] == ','.join(want)
        assert h['CHIPLIST'] == 'M,K,N,T'        # 공식 순서
        assert h['RAWPROD'] == 'L0_RAW_ARCHON'
        assert h['RAWVER'] == 'CEU-RAW-v1.0'
        assert h['RAWGROUP'] == 'MKNT'
        assert h['NUMFILES'] == 2

    # UNIQNAME 은 pair 양쪽이 **달라야** 한다 (컨트롤러 태그가 들어가므로)
    assert by_tag['MK']['UNIQNAME'] != by_tag['NT']['UNIQNAME']
    # 그러나 날짜·연번은 같아야 한다 -- 같은 노출이니까
    assert (by_tag['MK']['UNIQNAME'].split('.')[1:3]
            == by_tag['NT']['UNIQNAME'].split('.')[1:3])
    # EXPID/EXPNUM 은 두지 않는다 -- UNIQNAME 이 상위집합이다 (2026-08-12)
    assert 'EXPID' not in by_tag['MK']
    assert 'EXPNUM' not in by_tag['MK']


def test_identifier_cards_stay_strings(tmp_path):
    """식별자 카드가 **숫자 카드로 저장되면 안 된다.**

    회귀 방지 — 처음 구현에서 `EXPID='20260811.000001'` 이 실수 카드가 됐다.
    `_apply_header` 는 텔레메트리를 와이어 문자열로 받아 숫자로 바꾸는데
    (`EQUINOX='2000.000'` 때문에 필요한 동작이다) 숫자로 보이는 식별자가 그
    규칙에 걸린 것이다.  `EXPID` 는 이제 없지만 **같은 함정이 `UNIQNAME` 의
    연번부에도 있으므로** 검사를 유지한다.
    """
    _run(tmp_path)
    for h in _headers(tmp_path).values():
        for key in ('UNIQNAME', 'FILENAME', 'PAIRFILE', 'CTRLTAG', 'CHIPS',
                    'CHIP1', 'CHIP2', 'CHIPLIST', 'RAWPROD', 'RAWVER',
                    'RAWGROUP', 'OBSERVAT', 'ORIGIN', 'BUNIT', 'CREATOR',
                    'DATE'):
            assert isinstance(h[key], str), f'{key}: {type(h[key])}'
        assert re.fullmatch(r'KMT[CSAT]\.\d{8}\.\d{6}\.(MK|NT)',
                            h['UNIQNAME']), h['UNIQNAME']
        # 반대로 개수 카드는 정수여야 한다
        assert isinstance(h['NUMFILES'], int)


@pytest.mark.parametrize('suffix', [
    '20260811.000001',   # 끝자리가 0 이 아니라 실수 왕복이 우연히 성립하는 값
    '20260811.000010',   # 000010 -> 00001
    '20260811.000100',   # 000100 -> 0001
    '20260811.010000',   # 010000 -> 01
])
def test_serial_keeps_its_zero_padding(tmp_path, suffix):
    """식별자의 6자리 zero-padding 이 헤더를 왕복해도 살아남아야 한다.

    실수 카드로 저장되면 **뒤쪽 0 이 날아간다** -- 규격 2.3절이 zero-padding 을
    필수로 정한 이유가 헤더에서 그대로 재현되는 자리다 (5.0절 표).

    위 `test_identifier_cards_stay_strings` 는 형만 보므로 값과 무관하게
    잡지만, 이 테스트는 **결과**를 본다.  처음 구현에서 이 결함이 있었는데
    시험 데이터가 `000001` 이라 왕복이 우연히 성립했다 -- `000010` 이었으면
    그때 바로 드러났을 것이다.
    """
    from ics_sim.fitsout import _apply_header

    hdr = fits.Header()
    _apply_header(hdr, rawpair.identity_header(
        site_code='KMTA', suffix=suffix, ctrltag='MK',
        filename=rawpair.name_stem('KMTA', suffix, 'MK'),
        created='2026-08-11T12:00:00'))

    # UNIQNAME · FILENAME · PAIRFILE 모두 자릿수를 유지해야 한다
    for key in ('UNIQNAME', 'FILENAME', 'PAIRFILE'):
        assert isinstance(hdr[key], str), f'{key}: {type(hdr[key])}'
        assert f'.{suffix}.' in hdr[key], f'{key}={hdr[key]!r}'


def test_filename_matches_the_actual_file(tmp_path):
    """`FILENAME` 은 자기 파일 이름이며 **확장자를 뗀 형태**다 (규격 5.1절).

    레거시 실측 헤더가 `FILENAME = 'KMTNk.20170209.044131'` 로 `.fits` 없이
    기록했다 (`raw_fits_spec/__reference/Legacy raw fits header samples/`).
    """
    _run(tmp_path)
    for name, h in _headers(tmp_path).items():
        assert h['FILENAME'] == os.path.splitext(name)[0]
        assert not h['FILENAME'].endswith('.fits')


def test_pairfile_points_at_the_other_member(tmp_path):
    """`PAIRFILE` 이 짝을 가리킨다."""
    _run(tmp_path)
    hdrs = _headers(tmp_path)
    stems = {os.path.splitext(n)[0] for n in hdrs}
    for name, h in hdrs.items():
        # PAIRFILE 도 FILENAME 과 같은 형태(확장자 없음)로 대칭을 맞춘다
        assert h['PAIRFILE'] in stems - {os.path.splitext(name)[0]}
        assert not h['PAIRFILE'].endswith('.fits')


def test_observat_agrees_with_the_filename_site_code(tmp_path):
    """파일명 `<SITE>` 와 `OBSERVAT` 는 일치해야 한다 (규격 2.3절).

    converter v2.2.0 이 이 둘을 교차 검증해 불일치를 오류로 처리한다.
    """
    _run(tmp_path, node__site='sso', node__telid='KMTA')
    for name, h in _headers(tmp_path).items():
        assert h['OBSERVAT'] == rawpair.OBSERVAT[name.split('.')[0]] == 'SSO'


# -- 파일명 fail-safe 와 정체성 -------------------------------------------

def test_name_clash_quarantines_without_touching_the_identity(tmp_path):
    """이름이 겹치면 **개명하지 않고 `clash/` 로 격리**한다 (규격 2.3.1절).

    세 겹이 각각 다른 질문에 답한다:
      * **어디에**  — `clash/` 하위 디렉토리
      * **어느 것인지** — 파일 이름에 `.clash<UTC>` 접미
      * **일어났는지** — `NAMECLSH` 카드 (존재 자체가 신호)

    그리고 `UNIQNAME` 은 **바뀌지 않는다.** 그래서 격리된 파일도 어느 노출의
    어느 컨트롤러인지 헤더만으로 알 수 있다 -- 개명으로 식별을 잃던 문제가
    아예 성립하지 않는다.
    """
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path))
    drive(SCRIPT, cfg)
    first = _written(tmp_path)
    assert len(first) == 2
    canonical = {os.path.splitext(n)[0] for n in first}

    # expnum 이 다시 1 이므로 같은 이름을 쓰려 한다 -> 충돌
    run = drive(SCRIPT, make_config(paths__write_fits=True,
                                    paths__data_dir=str(tmp_path)))
    assert run.count('already exists') >= 1

    # 정상 디렉토리는 그대로 2개 -- 덮어쓰지도, 늘어나지도 않았다
    assert _written(tmp_path) == first

    clash_dir = os.path.join(tmp_path, rawpair.CLASH_DIR)
    assert os.path.isdir(clash_dir), '격리 디렉토리가 만들어지지 않았다'
    quarantined = sorted(n for n in os.listdir(clash_dir)
                         if n.endswith('.fits'))
    assert len(quarantined) == 2, quarantined

    for name in quarantined:
        stem = os.path.splitext(name)[0]
        assert re.fullmatch(r'KMT[CSAT]\.\d{8}\.\d{6}\.(MK|NT)'
                            r'\.clash\d{8}T\d{6}Z', stem), stem
        with fits.open(os.path.join(clash_dir, name)) as hdul:
            h = hdul[0].header
        assert h['FILENAME'] == stem                 # 실제로 쓴 이름
        assert h['UNIQNAME'] in canonical            # 정본은 그대로
        assert h['NAMECLSH'] is True                 # 충돌했다는 신호
        assert h['CTRLTAG'] in ('MK', 'NT')          # 식별 유지
        assert h['CHIP1'] and h['CHIP2']


def test_no_clash_card_when_nothing_collided(tmp_path):
    """`NAMECLSH` 는 **충돌했을 때만** 넣는다 -- 존재가 곧 신호다.

    `False` 를 넣으면 "충돌 안 함" 과 "이 규격을 모르는 취득 SW" 가 구분되지
    않는다.
    """
    _run(tmp_path)
    for name, h in _headers(tmp_path).items():
        assert 'NAMECLSH' not in h, name
        # 충돌이 없으면 정본과 실제 이름이 같다
        assert h['FILENAME'] == h['UNIQNAME']
    assert not os.path.isdir(os.path.join(tmp_path, rawpair.CLASH_DIR))


def test_failsafe_warning_is_one_per_file_from_ics(tmp_path):
    """fail-safe 경고는 **파일당 1회, `ICS` 이름으로 노출 개시자에게만**.

    파일 단위 사건이므로 파일당 1회다.  발신자를 `*.CB` 로 하지 않는 이유:
    물리 파일 1개에 chip 이 2개라 `M.CB`/`K.CB` 중 무엇으로 보낼지 정할 근거가
    없고, 둘 다 보내면 파일 2개가 겹친 것처럼 보인다.  ICS 가 파일을 쓴
    당사자이므로 ICS 가 보고한다 (2026-08-12 확정).

    OBSAgent 안전성은 소스로 확인했다 — `case WARNING:`(`commands.c:1045`)은
    발신자를 보지 않고 본문을 출력만 하며, 발신 노드 필터(`:757`)는
    `case STATUS:` 안에만 있다.
    """
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path))
    drive(SCRIPT, cfg)
    run = drive(SCRIPT, make_config(paths__write_fits=True,
                                    paths__data_dir=str(tmp_path)))
    warns = [m for m in run.sent if 'already exists' in m]
    assert len(warns) == 2, warns                    # 파일당 1회 = 2회
    for m in warns:
        assert m.startswith('ICS>'), m               # ICS 이름으로
        assert m.split('>')[1].split()[0] == 'OBS'   # 개시자에게만
    # 자기 앞으로는 보내지 않는다 (에코 낭비)
    assert not [m for m in warns if m.split('>')[1].split()[0] == 'ICS']


# -- sentinel (5.0절 / C-9 / OI-6) ----------------------------------------

def test_fits_sentinels_follow_the_spec_not_the_message_layer():
    """FITS 헤더는 정수 `-1` / 실수 `-999.0` / 문자열 `'NC'`.

    메시지 계층은 `'0'` 을 그대로 쓴다 -- 레거시 재현이 필요한 쪽이라
    분리해 두었다 (DevNote 11.2, 변경점 C-9).
    """
    telem = TelemetryRelay(SimConfig(), None)
    msg = telem.header_dict()
    hdr = telem.fits_header_dict('2026-08-11T12:00:00')

    # 메시지 계층: 레거시 관례 그대로
    assert msg['SECZ'] == '0' and msg['ALT'] == '0'
    # FITS 헤더: 0 은 값-없음으로 쓰지 않는다
    assert hdr['SECZ'] == -999.0
    assert hdr['ALT'] == -999.0
    assert hdr['FALIMS'] == -1          # 정수형
    assert hdr['MCPOS'] == -1
    assert hdr['DSSTAT'] == 'NC'        # 문자열
    assert hdr['TIMESYS'] == 'UTC'      # 규격 5.0: 명시한다
    for key, val in hdr.items():
        assert val != '0', f'{key} 가 아직 메시지 계층 sentinel 이다'


def test_date_obs_is_always_written(tmp_path):
    """`DATE-OBS` 는 **무조건 들어간다** (규격 5.7절 필수, 출처 ICS).

    외부에서 받아오는 값이 아니라 ICS 가 셔터를 여는 시점의 OS 시각을 스스로
    찍는 값이므로, 정상 사이클에 "없어서 못 넣는" 상황은 존재하지 않는다.
    """
    _run(tmp_path)
    for name, h in _headers(tmp_path).items():
        assert h['DATE-OBS'], name
        assert re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d', h['DATE-OBS'])
        assert h['TIMESYS'] == 'UTC'
    # pair 양쪽이 같아야 한다 (규격 5.7절 말미: 셔터는 하나, 노출도 하나)
    vals = {h['DATE-OBS'] for h in _headers(tmp_path).values()}
    assert len(vals) == 1, vals


def test_date_obs_is_never_silently_substituted():
    """근거가 없으면 **현재 시각으로 채우지 않고** 카드를 비운다.

    `stamp_iso(None)` 이 조용히 현재 시각을 돌려주므로, 그 값을 그대로 넘기면
    저장 시각이 `DATE-OBS` 가 된다 — 규격 6.1절 변경점 C-6 이 금지한 바로 그
    동작이다.  시퀀서가 `exp_start is None` 을 걸러 빈 문자열을 넘기고, 여기서
    카드가 비는 것을 확인한다.  `date_obs` 에 기본값이 없는 것도 같은 이유다.
    """
    telem = TelemetryRelay(SimConfig(), None)
    assert 'DATE-OBS' not in telem.fits_header_dict('')
    assert telem.fits_header_dict('2026-08-11T12:00:00')['DATE-OBS']
    # 기본값이 없어야 호출측이 빠뜨릴 수 없다
    import inspect
    sig = inspect.signature(telem.fits_header_dict)
    assert sig.parameters['date_obs'].default is inspect.Parameter.empty


def test_header_carries_detector_identity(tmp_path):
    """헤더만으로 어느 검출기인지 알 수 있어야 한다.

    개정 전에는 `header_dict()` 가 텔레메트리만 담아 4개 CCD 가 **똑같은
    헤더**를 받았고, CCD 식별이 파일명에만 있었다.  그래서 fail-safe 가
    이름을 바꾸면 그 파일이 어느 검출기인지 되찾을 방법이 없었다.
    """
    _run(tmp_path)
    hdrs = list(_headers(tmp_path).values())
    assert len({h['CTRLTAG'] for h in hdrs}) == 2   # 두 파일이 서로 다르다
    for h in hdrs:
        assert h['CHIP1'] and h['CHIP2'] and h['CHIPS']

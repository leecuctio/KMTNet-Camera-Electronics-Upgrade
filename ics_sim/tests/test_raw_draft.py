#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""초안 헤더 v1.0 pair 와의 **카드 전량 대사** (raw spec v1.5 5장).

정본 견본은 `raw_fits_spec/KMTA.20260821.012345.{MK,NT}.fits.header.v1.0.txt`
(경로는 박지 않고 glob 으로 찾는다 -- `_find_draft`)
-- **카드 순서·comment·문자열 패딩까지 바이트 단위 기준**이다 (5장 머리말).
이 파일은 세 겹으로 대사한다:

1. **템플릿 대사** -- `rawcards.CARDS` 가 견본의 구조(키 순서·형·폭·comment)와
   일치하는가.  견본이 개정되면 여기가 어긋난 자리를 가리킨다.
2. **바이트 대사** -- 견본의 값을 역산해 풀에 넣고 조립하면, 견본의 카드
   이미지 80바이트가 **그대로** 재현되는가 (구조 카드 7장 제외 -- astropy 가
   데이터에서 만들므로 상수로 따로 확인한다).
3. **pair 규칙** -- 반드시 상이 7장 / 나머지 동일 (5.9절).

raw spec 검증 체크리스트 #3(카드 전량)·#5(pair 규칙)·#6(geometry 선언)의
자동 구현이다 (7장).
"""

from __future__ import annotations

import os
import pathlib

import pytest

from ics_sim import rawcards, rawhdr
from ics_sim.config import SimConfig
from ics_sim.telemetry import TelemetryRelay

fits = pytest.importorskip('astropy.io.fits',
                           reason='카드 이미지 대사에는 astropy 가 필요하다')

SPEC_DIR = pathlib.Path(__file__).resolve().parents[2] / 'raw_fits_spec'


def _find_draft(tag: str) -> pathlib.Path:
    """견본 한 장을 **glob 으로** 찾는다 -- 날짜를 경로에 박지 않는다.

    ⚠️ **하드코딩이 이 시험을 조용히 죽인 적이 있다** (2026-08-22): 견본이
    `KMTA.20260818.…` -> `KMTA.20260821.…` 로 개명되자(파일명 == `FILENAME`
    카드로 맞추는 정본 수정) 경로가 어긋나 **대사 6개가 전부 skip 됐다.**
    skip 은 초록으로 지나가므로 아무도 눈치채지 못한다 -- 바이트 대사가 이
    저장소에서 견본과 구현이 갈라지는 것을 잡는 유일한 수단인데, 그 수단이
    꺼진 것을 시험 결과가 알려 주지 않았다.

    그래서 ① 이름 대신 **패턴**으로 찾고 ② 못 찾으면 **skip 이 아니라
    실패**다.  견본은 정본이므로 없는 것 자체가 결함이다.
    """
    found = sorted(SPEC_DIR.glob(f'KMT?.*.{tag}.fits.header.v1.0.txt'))
    assert found, (
        f'{tag} 견본을 찾을 수 없다 ({SPEC_DIR}) -- 견본은 5장의 바이트 '
        '정본이고, 이 대사가 없으면 구현과 규격이 갈라져도 잡히지 않는다')
    assert len(found) == 1, (
        f'{tag} 견본이 여럿이다 -- 어느 것이 정본인지 알 수 없다: '
        f'{[f.name for f in found]}')
    return found[0]


DRAFTS = {'MK': _find_draft('MK'), 'NT': _find_draft('NT')}


def _cards(path: pathlib.Path) -> list[str]:
    """견본을 80바이트 카드 이미지 목록으로 (`END` **뒤 공백 패딩은 뗀다**).

    ⚠️ **v1.5 에서 견본의 꼬리가 바뀌었다.**  종전에는 `#EOF` 4바이트가 붙어
    11,524 바이트(2880 의 배수가 아니었다)였는데, v1.5 가 그것을 떼고 `END`
    뒤를 **공백 레코드 4장**으로 채워 144 레코드 · 4x2880 = **11,520 바이트**로
    맞췄다 (FITS 표준 패딩, raw spec 3장).  그래서 여기서는 `END` 까지만 카드로
    보고 뒤의 공백 레코드는 버린다 -- 값 카드로 세면 파서가 `= ` 를 못 찾는다.
    """
    raw = path.read_bytes()
    if raw.endswith(b'#EOF'):          # 메모장용 사본(`_REFTEXT`)의 꼬리
        raw = raw[:-4]
    assert len(raw) % 2880 == 0, (
        f'{path}: 2880 바이트 블록 정렬이 아니다 ({len(raw)}) -- FITS 헤더는 '
        '블록 단위로 채워져야 한다 (raw spec 3장)')
    images = [raw[i:i + 80].decode('ascii') for i in range(0, len(raw), 80)]
    for i, c in enumerate(images):
        if c[:8].rstrip() == 'END':
            tail = images[i + 1:]
            assert all(t.strip() == '' for t in tail), (
                f'{path}: END 뒤에 공백이 아닌 레코드가 있다 -- {tail!r}')
            return images[:i + 1]
    raise AssertionError(f'{path}: END 레코드가 없다')


def _parse(card: str) -> tuple[str, str, int, str, str]:
    """카드 이미지 -> (key, 형, 폭, comment, 원문 값)."""
    key = card[:8].rstrip()
    if key == 'COMMENT':
        return ('COMMENT', '', 0, card[8:].rstrip(), '')
    assert card[8:10] == '= ', card
    body = card[10:]
    if body.lstrip().startswith("'"):
        s0 = body.index("'")
        s1 = body.index("'", s0 + 1)
        value = body[s0 + 1:s1]
        rest = body[s1 + 1:]
        comment = rest.split('/', 1)[1].strip() if '/' in rest else ''
        return (key, 'S', len(value), comment, value)
    token, _, comment = body.partition('/')
    value = token.strip()
    kind = ('L' if value in ('T', 'F')
            else 'R' if ('.' in value or 'e' in value.lower()) else 'I')
    return (key, kind, 0, comment.strip(), value)


def _sample(tag: str) -> dict[str, str]:
    """견본의 값 카드 원문 (문자열은 패딩 포함)."""
    out = {}
    for c in _cards(DRAFTS[tag]):
        if c[:8].rstrip() in ('COMMENT', 'END'):
            continue
        key, _, _, _, value = _parse(c)
        out[key] = value
    return out


# -- 1) 템플릿 대사 ----------------------------------------------------------

def test_template_matches_the_draft_structure():
    """`rawcards.CARDS` = 견본의 (키 순서, 형, 폭, comment) 그대로여야 한다.

    견본이 개정되면 이 시험이 어긋난 자리를 가리킨다 -- 템플릿은 견본의
    기계 사본이지 독자적 정의가 아니다.
    """
    parsed = [_parse(c) for c in _cards(DRAFTS['MK'])
              if c[:8].rstrip() != 'END']
    assert len(parsed) == len(rawcards.CARDS), (
        f'카드 수가 다르다 -- 견본 {len(parsed)} vs 템플릿 '
        f'{len(rawcards.CARDS)}')
    for (pk, pkind, pwidth, pcomment, _), (tk, tkind, twidth, tcomment) \
            in zip(parsed, rawcards.CARDS):
        assert pk == tk, f'키 순서가 다르다: 견본 {pk} vs 템플릿 {tk}'
        if pk == 'COMMENT':
            assert pcomment == tcomment, f'COMMENT 본문: {pcomment!r}'
            continue
        # EXPTIME 은 조건부 형(I/R)이라 견본(0=I)과 템플릿(I)이 같지만,
        # 견본이 실수 표본으로 바뀌어도 템플릿은 I 로 남는다 -- 그때 이 줄만
        # 예외 처리한다.
        assert pkind == tkind, f'{pk}: 형이 다르다 ({pkind} vs {tkind})'
        assert pwidth == twidth, f'{pk}: 패딩 폭이 다르다 ({pwidth} vs {twidth})'
        assert pcomment == tcomment, f'{pk}: comment 가 다르다'


def test_draft_counts_match_the_spec():
    """값 **131** + COMMENT 8 + END 1 + 공백 4 = 144 레코드 (raw spec v1.5).

    v1.5 가 HK 4장(`AIR_IN`/`AIR_OUT`/`GLYC_IN`/`GLYC_OUT`)을 폐지해 값 카드가
    135 -> 131 이 됐고, `END` 뒤를 공백 레코드로 채워 11,520 바이트를 유지한다.
    """
    raw = DRAFTS['MK'].read_bytes()
    assert len(raw) == 11520, (
        f'견본이 4x2880 = 11,520 바이트가 아니다 ({len(raw)}) -- v1.5 에서 '
        '`#EOF` 를 떼고 END 뒤 공백 4장으로 맞췄다')
    cards = [_parse(c) for c in _cards(DRAFTS['MK'])
             if c[:8].rstrip() != 'END']
    values = [c for c in cards if c[0] != 'COMMENT']
    assert len(values) == 131
    assert len(cards) - len(values) == 8


def test_pair_diff_is_exactly_the_seven_cards():
    """반드시 상이 7장 (raw spec 5.9절) -- 견본에서 직접 센다."""
    mk, nt = _sample('MK'), _sample('NT')
    assert set(mk) == set(nt)
    diff = sorted(k for k in mk if mk[k] != nt[k])
    assert diff == sorted(rawcards.PAIR_DIFF)


def test_structural_cards_match_our_constants():
    """구조 카드 7장 -- astropy 몫이므로 상수로 대사한다 (raw spec 3장)."""
    mk = _sample('MK')
    assert int(mk['BITPIX']) == 16
    assert int(mk['NAXIS1']) == rawhdr.RAW_NAXIS1 == 19200
    assert int(mk['NAXIS2']) == rawhdr.RAW_NAXIS2 == 9400
    assert int(mk['BZERO']) == 32768
    assert int(mk['BSCALE']) == 1


# -- 2) 바이트 대사 ----------------------------------------------------------

def _rebuild(tag: str) -> list[str]:
    """견본의 값을 역산해 풀에 넣고 조립한 카드 이미지 목록."""
    sample = _sample(tag)
    relay = TelemetryRelay(SimConfig(), lambda *a, **k: None)
    tcs = [k for k in rawcards.RELAY_CARDS
           if rawcards.SECTION[k] == 'TCS Information and Status']
    aux = [k for k in rawcards.RELAY_CARDS
           if rawcards.SECTION[k] == 'AUX Information and Status']
    # `TCSTIME` 은 와이어 `TIMESYS` 의 이관이고 `DALTERR`/`DAZERR` 는 ICS 계산
    # 카드다 -- 와이어에 직접 넣지 않아야 그 경로 자체가 시험된다.
    relay.tcs_fields = [(k, sample[k].strip()) for k in tcs
                        if k not in ('TCSTIME', 'DALTERR', 'DAZERR')]
    relay.tcs_fields.append(('TIMESYS', sample['TCSTIME'].strip()))
    relay.aux_fields = [(k, sample[k].strip()) for k in aux]
    relay.last_tcs_ok = relay.last_aux_ok = True
    telem = relay.fits_header_dict(sample['DATE-OBS'])

    sensors = {'dewpres': float(sample['DEWPRES']),
               'ccdtemp1': float(sample['CCDTEMP']),
               'fsatemp': float(sample['FSATEMP']),
               'fsahum': float(sample['FSAHUM'])}
    for card in rawhdr.DEWAR_CARDS:
        sensors[card.lower()] = float(sample[card])
    ctel = [{'temp': [float(x) for x in sample[f'C{n}_TEMP'].split()],
             'volt': [float(x) for x in sample[f'C{n}_VOLT'].split()],
             'curr': [float(x) for x in sample[f'C{n}_CURR'].split()]}
            for n in (1, 2)]
    cfg_ctrl = {n: {'id': sample[f'CTRL{n}ID'].strip(),
                    'sn': sample[f'CTRL{n}SN'].strip(),
                    'cfg': sample[f'CTRL{n}CFG'].strip()} for n in (1, 2)}

    cards = rawhdr.spec_cards(
        ctrltag=tag, site_code='KMTA', backend_name='archon',
        ics_build=sample['ICSBUILD'].strip(),
        ctrl_info={'units': ()}, ctrl_telem=ctel, sensors=sensors,
        # 견본은 관측소 raw(ORIGIN='SSO') -- KMTA 유도값과 같으므로
        # cfg_site 없이도 성립하지만, 유도 경로를 그대로 태운다.
        cfg_site=None, cfg_camera=None, cfg_ctrl=cfg_ctrl, rdmode='',
        telem_cards=telem,
        date_obs=sample['DATE-OBS'], exptime=int(sample['EXPTIME']),
        ledflash_ms=int(sample['LEDFLASH']),
        imgtype=sample['IMAGETYP'].strip(), objname=sample['OBJECT'].strip(),
        projid=sample['PROJID'].strip(), observer=sample['OBSERVER'].strip(),
        filename=sample['FILENAME'], origname=sample['ORIGNAME'])
    out = []
    for key, val, com in cards:
        if key == 'COMMENT':
            out.append(str(fits.Card('COMMENT', val)))
        else:
            out.append(str(fits.Card(key, val, com)))
    return out


@pytest.mark.parametrize('tag', ('MK', 'NT'))
def test_assembly_reproduces_the_draft_byte_for_byte(tag):
    """견본 값을 넣으면 견본의 카드 이미지가 **80바이트 그대로** 나와야 한다.

    카드 순서·comment·패딩·형(문자열/정수/실수)·sentinel 경로·`TCSTIME` 이관·
    `DALTERR`/`DAZERR` 계산까지 이 한 시험이 전부 덮는다.  값 하나라도 다른
    표기로 실리면(예: 온도 소수 자리, DEWPRES 지수 표기) 여기서 걸린다.
    """
    ours = _rebuild(tag)
    want = [c for c in _cards(DRAFTS[tag])
            if c[:8].rstrip() not in rawcards.STRUCTURAL
            and c[:8].rstrip() != 'END']
    assert len(ours) == len(want)
    for i, (o, w) in enumerate(zip(ours, want)):
        assert o == w, f'#{i}\nours: {o!r}\nwant: {w!r}'


# -- 3) 견본과 무관하게 지켜야 하는 조립 성질 --------------------------------

def test_dalterr_is_computed_when_wire_does_not_send_it():
    """`DALTERR`/`DAZERR` = ICS calculation (raw spec 5.7절)."""
    relay = TelemetryRelay(SimConfig(), lambda *a, **k: None)
    relay.tcs_fields = [('DSALT', '87.7'), ('DSTELALT', '88.1'),
                        ('DSAZ', '12.3'), ('DSTELAZ', '12.1')]
    h = relay.fits_header_dict('2026-08-22T00:00:00.000')
    assert h['DALTERR'] == '-0.4'
    assert h['DAZERR'] == '+0.2'
    # 피연산 카드가 없으면 지어내지 않는다
    empty = TelemetryRelay(SimConfig(), lambda *a, **k: None)
    h2 = empty.fits_header_dict('2026-08-22T00:00:00.000')
    assert h2['DALTERR'] == 'NC' and h2['DAZERR'] == 'NC'


def test_tcstime_comes_from_the_tcs_wire_not_from_ics():
    """`TCSTIME` = TCS 가 보고한 time system -- ICS `TIMESYS` 와 분리 (5.7절)."""
    relay = TelemetryRelay(SimConfig(), lambda *a, **k: None)
    relay.tcs_fields = [('TIMESYS', 'TAI')]           # 일부러 UTC 가 아닌 값
    h = relay.fits_header_dict('2026-08-22T00:00:00.000')
    assert h['TCSTIME'] == 'TAI'
    # 조립하면 ICS 의 TIMESYS 카드는 여전히 UTC 다 (rawhdr 5.4절 몫)
    pool = rawhdr.build_pool(
        ctrltag='MK', site_code='KMTA', backend_name='sim', ics_build='x',
        ctrl_info={'units': ()}, ctrl_telem=None, sensors=None,
        cfg_site=None, cfg_camera=None, cfg_ctrl=None, rdmode='',
        telem_cards=h, date_obs='2026-08-22T00:00:00.000', exptime=0,
        ledflash_ms=0, imgtype='BIAS', objname='x', projid='x', observer='x',
        filename='f', origname='f')
    assert pool['TIMESYS'] == 'UTC'
    assert pool['TCSTIME'] == 'TAI'


def test_unknown_wire_keys_never_leak_into_the_header():
    """템플릿에 없는 와이어 키는 카드로 새지 않는다 (rawcards.render).

    구판에서 `SHUTTER` 겹침 사고를 만들던 경로를 구조적으로 막은 것이다.
    """
    cards = rawcards.render({k: 'x' for k in ('WEIRDKEY', 'TELID', 'EXECODE',
                                              'TCSLIMIT', 'CHSTAT')}
                            | {k: 'v' for k, kd, w, c in rawcards.CARDS
                               if k not in ('COMMENT',)})
    keys = {k for k, _, _ in cards if k != 'COMMENT'}
    for stranger in ('WEIRDKEY', 'TELID', 'EXECODE', 'TCSLIMIT', 'CHSTAT'):
        assert stranger not in keys


def test_written_file_matches_the_template_order(tmp_path):
    """실제 FITS 로 저장해도 카드 순서·comment 가 템플릿 그대로여야 한다."""
    import numpy as np
    from ics_sim.fitsout import write_dummy_fits
    relay = TelemetryRelay(SimConfig(), lambda *a, **k: None)
    telem = relay.fits_header_dict('2026-08-22T00:00:00.000')
    cards = rawhdr.spec_cards(
        ctrltag='MK', site_code='KMTA', backend_name='sim', ics_build='x',
        ctrl_info={'units': ()}, ctrl_telem=None, sensors=None,
        cfg_site=None, cfg_camera=None, cfg_ctrl=None, rdmode='',
        telem_cards=telem, date_obs='2026-08-22T00:00:00.000', exptime=0,
        ledflash_ms=0, imgtype='BIAS', objname='x', projid='x', observer='x',
        filename='f', origname='f')
    path = str(tmp_path / 'x.fits')
    assert write_dummy_fits(path, np.zeros((4, 4)), cards) >= 0
    hdr = fits.getheader(path)
    written = [k for k in hdr.keys() if k]
    tmpl = [k for k, kd, w, c in rawcards.CARDS]
    # 구조 카드 뒤부터 템플릿 순서 그대로 (BUNIT 부터)
    tail = tmpl[tmpl.index('BUNIT'):]
    assert written[-len(tail):] == tail
    # comment 도 템플릿 그대로
    assert hdr.comments['BUNIT'] == 'units of physical values'
    assert hdr.comments['BSCALE'] == 'PHYSICAL=INTEGER*BSCALE+BZERO'
    # CHECKSUM/DATASUM 은 미도입이다 (OI-7)
    assert 'CHECKSUM' not in hdr and 'DATASUM' not in hdr


def test_chmap_matches_the_machine_copy():
    """`CHMAP_*` 상수 = 기계 가독 정본(채널맵 **v1.1**)과 일치 (raw spec 4.5절).

    ⚠️ **v1.1 이 정본이고 자리도 옮겼다** (2026-08-25): 토큰이 4자가 되고
    `IMGSEC` 의 `B-BOT` 이 `D-BOT` 으로 정정되면서, `__` 접두 폴더 읽기 전용
    규칙에 따라 `__reference/` 의 v1.0 은 원본 기록으로 두고 사본을 sub레포
    루트로 올려 고쳤다.  v1.0 을 계속 가리키면 3자 토큰과 대조하게 된다.

    **없으면 skip 이 아니라 실패다** -- `_find_draft` 와 같은 이유다(그쪽
    docstring 참고).  4.5절이 이 파일을 "기계 가독 정본"으로 규정했으므로
    없는 것 자체가 결함이고, skip 으로 두면 정본이 사라져도 스위트가 초록으로
    지나간다.  구 이름 `..._when_present` 의 "있으면" 이 그 헐거움이었다.
    """
    ref = SPEC_DIR / 'Detector_Ch_to_AmpID_Map_v1.1.txt'
    assert ref.exists(), (
        f'기계 사본을 찾을 수 없다 ({ref}) -- raw spec 4.5절의 정본이고, '
        '이 대조가 없으면 CHMAP 상수가 배선표와 갈라져도 잡히지 않는다')
    text = ref.read_text(encoding='utf-8', errors='replace')
    for detid, cards in rawhdr.CHMAP.items():
        for key, value in cards.items():
            for token in value.split(','):
                assert token in text, (
                    f'{detid} {key} 의 {token} 이 기계 사본에 없다')

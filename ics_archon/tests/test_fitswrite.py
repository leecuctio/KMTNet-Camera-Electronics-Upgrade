#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raw FITS 기록 -- **견본 v1.0 pair 와 바이트 단위 대사.**

견본(`raw_fits_spec/KMT?.*.{MK,NT}.fits.header.v1.0.txt`)이 카드 순서·comment·
문자열 패딩까지 바이트 단위 기준이다 (raw spec 5장 머리말).  여기서는 견본의
카드 이미지를 되먹여 **같은 80바이트가 다시 나오는지** 본다 -- 렌더러가
어긋나면 곧바로 걸린다.

⚠️ **없으면 skip 이 아니라 실패다.**  견본은 정본이므로 없는 것 자체가
결함이다.  경로는 이름이 아니라 **패턴**으로 찾는다 -- 견본이 개명되면서 바이트
대사 6개가 조용히 꺼진 적이 있다 (DevNote 11.21: "실행되지 않는데 초록").
"""

from __future__ import annotations

import glob
import os

import pytest

from ics_archon.archon import fitswrite

_SPEC_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir,
    'raw_fits_spec'))


def _find_draft(tag: str) -> str:
    pattern = os.path.join(_SPEC_DIR, 'KMT?.*.%s.fits.header.v1.0.txt' % tag)
    hits = sorted(glob.glob(pattern))
    if not hits:
        raise AssertionError(
            '견본 헤더를 찾을 수 없다 (%s) -- 견본은 정본이므로 없는 것 자체가 '
            '결함이다.  raw_fits_spec/ 를 확인하라' % pattern)
    if len(hits) > 1:
        raise AssertionError(
            '견본 헤더가 여럿이다 (%r) -- 어느 것이 정본인지 알 수 없는 상태를 '
            '통과시키지 않는다' % hits)
    return hits[0]


def _cards_of(path: str) -> list[str]:
    """견본 파일을 80자 카드로 자른다.

    ⚠️ **v1.5 에서 꼬리가 바뀌었다.**  종전에는 `#EOF` 4바이트가 붙어 11,524
    자였는데(2880 의 배수가 아니었다), v1.5 가 그것을 떼고 `END` 뒤를 **공백
    레코드 4장**으로 채워 144 레코드 · 4x2880 = **11,520 자**로 맞췄다 (FITS
    표준 패딩, raw spec 3장).  공백 레코드도 카드로 돌려준다 -- `header_bytes()`
    가 만드는 패딩과 바이트로 대사해야 하기 때문이다.
    """
    text = open(path, encoding='ascii').read()
    if text.endswith('#EOF'):          # 메모장용 사본(`_REFTEXT`)의 꼬리
        text = text[:-4]
    assert len(text) % 2880 == 0, (
        '견본이 2880자 블록의 배수가 아니다 (%d) -- FITS 헤더는 블록 단위로 '
        '채워져야 한다 (raw spec 3장)' % len(text))
    return [text[i:i + 80] for i in range(0, len(text), 80)]


def _parse_card(card: str):  # noqa: ANN202
    """카드 이미지 -> `(key, value, comment)`.  `card_image()` 의 역이다.

    형(型)은 **적힌 모양에서** 되살린다 -- 템플릿을 참조하지 않는다.  그래야
    이 시험이 렌더러만 재고, 값-형 대응(그쪽은 `ics_sim` 의 `test_raw_draft`
    가 본다)과 섞이지 않는다.
    """
    key = card[:8].rstrip()
    if not card.strip():               # `END` 뒤 블록 채움 (v1.5)
        return 'PAD', None, ''
    if key == 'COMMENT':
        return 'COMMENT', card[8:].rstrip(), ''
    if key == 'END':
        return 'END', None, ''
    assert card[8:10] == '= ', repr(card)
    if card[10] == "'":
        close = card.index("'", 11)
        text = card[11:close]
        rest = card[close + 1:]
        comment = rest[3:].rstrip() if rest.startswith(' / ') else ''
        return key, text, comment
    token = card[10:30].strip()
    rest = card[30:]
    comment = rest[3:].rstrip() if rest.startswith(' / ') else ''
    if token == 'T':
        return key, True, comment
    if token == 'F':
        return key, False, comment
    if any(c in token for c in '.eE'):
        return key, float(token), comment
    return key, int(token), comment


@pytest.mark.repo_only
@pytest.mark.parametrize('tag', ['MK', 'NT'])
def test_card_images_reproduce_the_draft_byte_for_byte(tag):  # noqa: ANN001
    """견본 144카드를 되먹이면 같은 바이트가 나와야 한다."""
    cards = _cards_of(_find_draft(tag))
    assert len(cards) == 144, '견본은 144레코드 = 2880B x 4 다'
    # v1.5: 값 131 + COMMENT 8 + END 1 + 공백 4 = 144.
    assert sum(1 for c in cards if _parse_card(c)[0] == 'PAD') == 4
    mismatch = []
    for i, card in enumerate(cards, start=1):
        key, value, comment = _parse_card(card)
        if key == 'END':
            assert card == 'END'.ljust(80)
            continue
        if key == 'PAD':
            assert card == ' ' * 80
            continue
        again = fitswrite.card_image(key, value, comment)
        if again != card:
            mismatch.append((i, key, card, again))
    assert not mismatch, '불일치 %d장:\n%s' % (
        len(mismatch),
        '\n'.join('  카드 %d (%s)\n    견본 %r\n    생성 %r'
                  % (i, k, a, b) for i, k, a, b in mismatch[:5]))


@pytest.mark.repo_only
@pytest.mark.parametrize('tag', ['MK', 'NT'])
def test_header_bytes_of_the_draft_is_exactly_the_draft(tag):  # noqa: ANN001
    """카드를 조립한 결과가 견본 스트림과 같은지 -- 구조 카드 자리 포함.

    `rawcards.render()` 는 구조 카드(`SIMPLE`~`BZERO`)를 내지 않으므로
    `header_bytes()` 가 그것을 템플릿 순서로 채워 넣는다.  그 자리가 어긋나면
    여기서 걸린다.
    """
    cards = _cards_of(_find_draft(tag))
    parsed = [_parse_card(c) for c in cards]
    naxis = {k: v for k, v, _ in parsed if k in ('NAXIS1', 'NAXIS2')}
    # END 와 구조 카드를 뺀 목록 -> `render()` 가 주는 형태와 같다.
    body = [(k, v, c) for k, v, c in parsed
            if k not in ('END', 'PAD')
            and k not in fitswrite.rawcards.STRUCTURAL]
    blob = fitswrite.header_bytes(body, naxis['NAXIS1'], naxis['NAXIS2'])
    assert len(blob) % 2880 == 0
    assert blob.decode('ascii') == ''.join(cards)


def test_non_ascii_is_replaced_not_left_to_break_the_file():
    """비ASCII 한 자가 2880B 정렬을 깨 **파일 전체**를 못 읽게 만든다.

    헤더는 문자 단위로 80자씩 조립하고 파일에는 utf-8 바이트로 쓴다 -- 한글 한
    자가 3바이트라 문자 수는 맞는데 바이트 수가 어긋난다 (DevNote 11.22 (2):
    `OSError: Empty or corrupt FITS file`).  취득 중에는 경고가 한 줄도 안 뜬다.
    """
    card = fitswrite.card_image('OBSERVER', 'HELab 차상목'.ljust(18), 'Observer')
    assert len(card) == 80
    assert card.isascii()
    assert '?' in card


def test_over_long_value_shortens_the_comment_first_not_the_value():
    """**폭이 모자라면 comment 를 먼저 줄인다** (raw spec **5.0절**, v1.6).

    값이 자료이고 comment 는 설명이기 때문이다.  특히 `Cn_*` 나열 카드는
    **자리가 곧 항목**이라(5.6.1절) 값이 잘리면 **뒤 항목이 통째로 사라지는데
    읽는 쪽은 그 사실을 알 방법이 없다.**  comment 가 짧아진 것은 눈에 보이고,
    자리 뜻의 정본은 어차피 규격 5.6.1절 표다.

    ⚠️ **v1.6 에서 규칙이 뒤집혔다** -- 종전에는 값을 자르고 comment 를 살렸다.
    """
    # 음수 열 자리 = 59자.  견본 폭(51)은 넘지만 comment 를 줄이면 들어간다.
    long = '|'.join(['-40.1'] * 10)
    assert len(long) == 59
    card = fitswrite.card_image('C1_TEMP', long, 'Ctrl-1 T[C]')
    assert len(card) == 80
    assert card.count("'") == 2                   # 인용부호가 살아 있다
    assert long in card, '값이 온전해야 한다 -- 잘린 것은 comment 여야 한다'
    assert not card.endswith('Ctrl-1 T[C]'), 'comment 가 줄어야 한다'


def test_value_is_cut_only_when_the_comment_is_already_gone():
    """comment 를 전부 지워도 넘치면 그때 값을 자르고 **경고한다** (5.0절).

    규격 위반 상태이므로 조용히 지나가면 안 된다.  안 자르면 카드가 80자에서
    통째로 절단돼 **닫는 인용부호가 사라지고** astropy 가 파싱조차 못 한다.

    `Cn_*` 는 결측 자리를 `NC` 로 두어(5.6.1절) 이 경우가 실제로 오지 않게
    했다 -- 구 sentinel `-999.99` 로 열 자리를 채우면 79자가 되어 여기 걸린다.
    """
    huge = '|'.join(['-999.99'] * 10)             # 79자 -- 구 sentinel 이 그랬다
    assert len(huge) == 79
    card = fitswrite.card_image('C1_TEMP', huge, 'Ctrl-1 T[C]')
    assert len(card) == 80
    assert card.count("'") == 2, '카드가 깨지면 파일 전체를 못 읽는다'

    # 규격이 정한 `NC` 를 쓰면 잘리지 않는다 -- 그것이 이 sentinel 의 이유다.
    ok = '|'.join(['NC'] * 10)
    card2 = fitswrite.card_image('C1_TEMP', ok, 'Ctrl-1 T[C]')
    # 카드는 80자로 패딩되므로 comment 존재는 rstrip 한 뒤에 본다.
    assert len(card2) == 80 and ok in card2
    assert card2.rstrip().endswith('Ctrl-1 T[C]')


def test_a_quote_inside_a_string_value_is_doubled_not_left_to_break_the_card():
    """FITS 표준 4.2.1 -- 값 안의 `'` 는 겹쳐 써야 한다 (F7).

    안 겹치면 그 자리가 값의 끝으로 읽혀 **카드가 통째로 깨진다.**  값의
    출처가 관측자 입력(`OBJECT`/`OBSERVER`/`PROJID`)이라 `object O'Brien`
    한 번이면 실제로 들어온다 -- 그리고 경고가 한 줄도 안 뜬다.
    """
    from astropy.io import fits

    img = fitswrite.card_image('OBJECT', "O'Brien", 'Object name')
    assert len(img) == 80
    assert "O''Brien" in img, img
    # 정본 판정은 astropy 다 -- 되읽어서 원래 값이 나와야 한다.
    assert fits.Card.fromstring(img).value.strip() == "O'Brien"


def test_truncation_never_leaves_a_dangling_half_of_a_doubled_quote():
    """겹친 따옴표 한가운데서 자르면 홀수 개가 남아 카드가 깨진다.

    길이를 맞추려다 위에서 막은 결함을 그대로 만드는 셈이라 따로 막는다.
    """
    from astropy.io import fits

    value = "A" + "'" * 60
    img = fitswrite.card_image('OBJECT', value, 'Object name')
    assert len(img) == 80
    body = img.split('=', 1)[1]
    quoted = body[body.index("'") + 1:body.rindex("'")]
    assert quoted.count("'") % 2 == 0, img
    assert fits.Card.fromstring(img).value is not None


def test_header_bytes_rejects_a_misaligned_result():
    """정렬은 파일 전체의 생사를 가르므로 두 겹으로 막는다."""
    class Sneaky(str):
        """`card_image` 를 우회해 비ASCII 를 흘려보내는 가짜 값."""

        def isascii(self) -> bool:
            return True

    with pytest.raises(ValueError, match='2880'):
        fitswrite.header_bytes([('OBSERVER', Sneaky('가'), '')], 4, 2)


def test_bzero_conversion_matches_the_verified_two_lines():
    """`BITPIX=16` + `BZERO=32768` 저장형 -- labtest 가 검증한 결과와 같게.

    물리값 0..65535 를 `값 - 32768` 의 부호 있는 16비트로 담고 빅엔디언으로
    쓴다.  **제자리에서** 바꾸므로 344 MiB 사본이 생기지 않는다.
    """
    import numpy as np
    raw = bytearray(np.array([0, 1, 32768, 65535], dtype='<u2').tobytes())
    fitswrite.to_fits_data(raw)
    got = np.frombuffer(bytes(raw), dtype='>i2').astype('int64')
    assert list(got + 32768) == [0, 1, 32768, 65535]


def test_write_frame_round_trips_through_astropy(tmp_path):  # noqa: ANN001
    """실제로 써서 astropy 로 읽는다 -- 값·기하·패딩까지.

    astropy 가 열리는 것이 요점이다.  converter 가 처음 하는 일이 그것이고,
    헤더 정렬이나 데이터부 길이가 어긋나면 `Header missing END card` 같은
    형태로 **파일 전체**가 거부된다.
    """
    import numpy as np
    from astropy.io import fits

    nx, ny = 12, 5
    values = np.arange(nx * ny, dtype='<u2')
    raw = bytearray(values.tobytes())
    cards = [('BUNIT', 'ADU'.ljust(18), 'units of physical values'),
             ('COMMENT', '  Test block ' + '_' * 10, ''),
             ('OBJECT', 'DS0000'.ljust(18), 'Object name'),
             ('EXPTIME', 30, 'Exposure time [s]')]
    path = str(tmp_path / 'KMTK.20260823.000001.MK.fits')
    rate = fitswrite.write_frame(path, cards, raw, naxis1=nx, naxis2=ny)

    assert rate > 0
    size = os.path.getsize(path)
    assert size % 2880 == 0
    assert not os.path.exists(path + '.part')     # 임시 이름이 남지 않는다

    with fits.open(path) as hdul:
        hdu = hdul[0]
        assert hdu.header['NAXIS1'] == nx and hdu.header['NAXIS2'] == ny
        assert hdu.header['BZERO'] == 32768 and hdu.header['BITPIX'] == 16
        assert hdu.header['OBJECT'].strip() == 'DS0000'
        assert hdu.header['EXPTIME'] == 30
        assert np.array_equal(hdu.data.reshape(-1), values)


def test_write_frame_refuses_a_geometry_mismatch(tmp_path):  # noqa: ANN001
    """선언과 실제가 다르면 **파일을 만들지 않는다.**

    패딩을 실제 크기에서 뽑으면 남는 꼬리가 블록 경계에 딱 맞아 astropy 가 그
    뒤를 "다음 HDU" 로 읽는다 -- v1.0 은 꼬리가 미정렬이라 경고만 내고 열렸다.
    """
    raw = bytearray(10 * 2)
    path = str(tmp_path / 'x.fits')
    with pytest.raises(ValueError, match='선언 기하'):
        fitswrite.write_frame(path, [], raw, naxis1=4, naxis2=4)
    assert not os.path.exists(path)


def _dummy_frame(path, nx=8, ny=3):  # noqa: ANN001, ANN201
    """작은 프레임 하나를 쓴다 (되돌려 쓰기 시험용)."""
    import numpy as np
    raw = bytearray(np.arange(nx * ny, dtype='<u2').tobytes())
    return fitswrite.write_frame(path, [('BUNIT', 'ADU'.ljust(18), '')], raw,
                                 naxis1=nx, naxis2=ny)


def test_an_existing_file_is_never_overwritten(tmp_path):  # noqa: ANN001
    """**이미 있는 파일은 덮지 않는다** (운영자 확정 2026-08-23).

    D-016 선검사와 이 쓰기 사이에는 `write_delay` + 저장시간만큼 **틈**이 있다.
    그 틈에 누가 그 경로에 파일을 두면(같은 `data_dir` 에 ICS 두 개 · 백업
    되돌림 · rsync) `os.replace` 가 그것을 말없이 지운다 -- 자료 파괴는 되돌릴
    수 없다.

    둘 중 하나를 잃어야 한다면 **새 프레임을 버리는 쪽**이 맞다: 옛 프레임은
    이미 아카이브에 들어갔을 수 있고, 새 프레임은 다시 찍을 수 있으며 오류가
    크게 뜬다.  이름을 정하는 것은 여전히 시퀀서다 -- 여기서는 "덮어쓰지
    않겠다" 고만 한다.
    """
    path = str(tmp_path / 'KMTK.20260823.000001.MK.fits')
    assert _dummy_frame(path) > 0
    first = open(path, 'rb').read()

    with pytest.raises(OSError, match='덮지 않는다'):
        _dummy_frame(path, nx=8, ny=3)

    # 옛 파일이 그대로다 -- 한 바이트도 안 바뀌었다
    assert open(path, 'rb').read() == first
    # 임시 파일도 남기지 않는다 -- `.part` 가 쌓이면 진단이 흐려진다
    assert not os.path.exists(path + '.part')
    assert sorted(os.listdir(tmp_path)) == [os.path.basename(path)]


def test_a_failed_write_leaves_no_part_file(tmp_path):  # noqa: ANN001
    """기하 불일치로 거부할 때도 `.part` 를 남기지 않는다.

    `.part` 가 최종 이름을 차지하지는 않지만, 쌓이면 디스크를 먹고 다음 시도의
    진단을 흐린다.
    """
    path = str(tmp_path / 'x.fits')
    with pytest.raises(ValueError, match='선언 기하'):
        fitswrite.write_frame(path, [], bytearray(10), naxis1=4, naxis2=4)
    assert os.listdir(tmp_path) == []

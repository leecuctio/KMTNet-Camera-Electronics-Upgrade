#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raw FITS pair 기록 -- **바이트 정본을 그대로 낸다.**

원형은 실험실 취득 스크립트의 `fits_card`/`build_header` + 원시 쓰기다.
`ics_sim` 의 `fitsout.py`(astropy 경로)를 쓰지 않는 이유가 셋이다:

1. **취득 경로에 astropy 를 넣지 않는다.**  `ics_sim` 도 astropy 를 선택
   의존성으로 두고 있고, 실기 취득이 라이브러리 판 차이로 멈추는 것은
   감당할 이유가 없는 위험이다.
2. **메모리.**  프레임 하나가 344 MiB(19200x9400x2B)다.  astropy 는 배열을
   따로 들고 쓰므로 컨트롤러 2대 동시 저장에서 사본이 겹친다.  여기서는
   fetch 버퍼 **하나를 제자리에서** 바꿔 쓴다 (`byteswap(inplace=True)`) --
   labtest 가 사본을 하나 더 만들던 것보다도 적다.
3. **데이터부 2880B 패딩**(raw spec 3장)을 명시적으로 쓴다.  labtest v1.0 은
   마지막 블록이 잘려 있었고, v1.1 이 패딩을 넣으면서 **기하 불일치를
   악화**시켰다 (DevNote 11.22 (3)) -- 그래서 패딩은 **선언 기하**에서 뽑고,
   실제 fetch 바이트 수와의 대조는 부르는 쪽이 fetch **앞에서** 한다.

## 카드 조립

카드 목록·순서·comment·문자열 패딩 폭의 정본은 견본 초안 v1.0 pair 이고,
그 기계 사본이 `ics_sim/rawcards.py` 의 `CARDS` 다.  이 모듈은 **그 템플릿을
직접 읽는다** -- 사본을 또 두지 않는다.

`rawcards.render()` 는 구조 카드(`SIMPLE`~`BZERO`)를 내지 않는다 (astropy 가
데이터에서 만드는 것을 전제로 한 설계다).  원시 쓰기에는 그것을 만들어 주는
쪽이 없으므로 여기서 **템플릿 순서 그대로** 채운다.
"""

from __future__ import annotations

import logging
import os
import time

from .. import _simpath

_simpath.ensure()

from ics_sim import rawcards                  # noqa: E402

log = logging.getLogger('ics_archon.fits')

#: FITS 블록 크기 [B].
BLOCK = 2880
#: 카드 이미지 크기 [B].
CARD = 80

#: keyword -> 견본 문자열 패딩 폭.  값이 이 폭보다 짧으면 우측 공백을 채운다.
_WIDTH = {k: w for k, _t, w, _c in rawcards.CARDS if k != 'COMMENT'}
#: keyword -> 견본 comment.
_COMMENT = {k: c for k, _t, _w, c in rawcards.CARDS if k != 'COMMENT'}

#: 구조 카드는 템플릿 맨 앞 7장이다 -- 그 가정을 여기서 못박는다.  견본이
#: 개정돼 순서가 바뀌면 이 단정이 먼저 걸린다 (조용히 어긋나는 것보다 낫다).
_LEAD = tuple(k for k, _t, _w, _c in rawcards.CARDS[:len(rawcards.STRUCTURAL)])
assert set(_LEAD) == set(rawcards.STRUCTURAL), (
    '구조 카드가 템플릿 맨 앞 %d장이 아니다 -- rawcards.CARDS 가 개정됐다: %r'
    % (len(rawcards.STRUCTURAL), _LEAD))


def structural_cards(naxis1: int, naxis2: int) -> list[tuple[str, object, str]]:
    """`SIMPLE`~`BZERO` 를 템플릿 순서로.  값은 규격 3장 고정이다.

    `BITPIX=16` + `BZERO=32768` 은 converter 의 하드 요구다 -- 다르면 그
    자리에서 `Only BITPIX=16 is supported` 로 멈춘다 (raw spec 3장).
    """
    values: dict[str, object] = {
        'SIMPLE': True, 'BITPIX': 16, 'NAXIS': 2,
        'NAXIS1': naxis1, 'NAXIS2': naxis2,
        'BSCALE': 1, 'BZERO': 32768,
    }
    return [(k, values[k], _COMMENT.get(k, '')) for k in _LEAD]


def card_image(key: str, value: object, comment: str, *,
               widths: dict[str, int] | None = None) -> str:
    """카드 이미지 80자 하나.  견본 v1.0 의 고정 형식을 그대로 재현한다.

    `widths` 를 주면 그 표가 science 견본 폭(`_WIDTH`)을 **통째로 대신한다** --
    guide raw(`icg_archon`)가 자기 견본 폭 표를 꽂는 자리다.  guide 견본은
    science 와 공유하는 키 8장의 폭이 다르다(컨트롤러 블록 24/29 -> 26,
    `C1_*` 51 -> 49) -- science 표로 패딩하면 guide 저장 바이트가 견본과
    어긋난다.

    comment 없는 수치 카드에도 `' /'` 를 붙인다 -- 견본이 그렇다 (astropy 는
    생략하지만 정본은 견본이다).

    **폭이 모자라면 comment 를 먼저 줄인다** (raw spec **5.0절**, 운영자 확정
    2026-08-26).  값이 자료이고 comment 는 설명이기 때문이다 -- 특히 `Cn_*`
    나열 카드는 **자리가 곧 항목**이라(5.6.1절) 값이 잘리면 뒤 항목이 통째로
    사라지는데 읽는 쪽은 그 사실을 알 방법이 없다.  자리 뜻의 정본은 어차피
    규격 5.6.1절 표다.

    comment 를 전부 지워도 넘치면 그때 **값을 자르고 경고한다** -- 규격 위반
    상태이므로 조용히 지나가면 안 된다.  안 자르면 카드가 80자에서 통째로
    절단되어 **닫는 인용부호가 사라지고** astropy·converter 가 파싱조차 못
    한다 (labtest v1.1 이 고친 결함).
    """
    if key == 'COMMENT':
        # 'COMMENT'(7자) + 공백 1 + 본문 (본문은 견본 9열부터의 원문)
        return ('COMMENT ' + str(value)).ljust(CARD)[:CARD]

    if isinstance(value, str):
        text = value
        # 폭 계산과 패딩이 전부 **문자 수** 기준인데 파일에는 바이트로 쓴다.
        # 비ASCII 한 자(한글 3바이트)가 남으면 2880B 정렬이 깨져 **파일 전체가
        # 안 읽힌다** -- 취득 중에는 경고가 한 줄도 안 뜬다 (DevNote 11.22 (2)).
        # 값의 출처가 ini·STATUS·ACF 이름처럼 바깥이므로 여기가 마지막 방어선
        # 이다.
        if not text.isascii():
            log.warning('FITS 카드 %s 의 값에 비ASCII 문자가 있다 (%r) -- '
                        '? 로 바꾼다.  헤더는 ASCII 전용이다 (raw spec 5.0절)',
                        key.strip(), text)
            text = text.encode('ascii', 'replace').decode('ascii')
        # **값 안의 홑따옴표는 겹쳐 쓴다** (FITS 표준 4.2.1).  안 겹치면 그
        # 자리가 값의 끝으로 읽혀 카드가 통째로 깨진다 -- `object O'Brien` 한
        # 번이면 `OBJECT = 'O'Brien   '` 이 되고, 값은 `O` 로 잘리고 나머지가
        # comment 로 새며 **경고가 한 줄도 안 뜬다.**  값의 출처가 관측자 입력
        # (`OBJECT`/`OBSERVER`/`PROJID`)과 ACF 파일명이라 실제로 들어올 수 있다.
        text = text.replace("'", "''")
        table = _WIDTH if widths is None else widths
        width = table.get(key, 0)
        # 값이 들어갈 최대 폭 = 80 - ("KEY     = '" + "'" + " / " + comment)
        room = 80 - (10 + 1 + 1 + (3 + len(comment) if comment else 2))
        room = max(room, width)      # 견본 폭은 항상 들어간다
        if len(text) > room:
            # **comment 를 먼저 줄인다** (5.0절).  값 절단의 문턱은 **값 단독
            # 68자**다 -- `"KEY     = '" (11) + 값 + "'" (1) = 80`.  이때는
            # `' /'` 꼬리도 포기한다(comment 는 선택 사항).  `fitsout.
            # _fit_to_card` 의 `_VALUE_MAX = 68` 과 같은 문턱이어야 두 기록기의
            # 규범 해석이 갈리지 않는다.
            room_bare = max(80 - (11 + 1), width)
            if len(text) <= room_bare:
                keep = 80 - (10 + 1 + 1 + 3) - len(text)
                comment = comment[:max(keep, 0)].rstrip()
                log.warning('FITS 카드 %s 의 값이 길어 comment 를 줄였다 '
                            '(값 %d자) -- 값은 그대로다 (raw spec 5.0절)',
                            key.strip(), len(text))
            else:
                log.warning('FITS 카드 %s 의 값이 너무 길다 (%d > %d) -- '
                            'comment 를 다 지워도 안 들어가 값을 잘라낸다. '
                            '자리 나열 카드면 뒤 항목이 사라진다 (5.6.1절)',
                            key.strip(), len(text), room_bare)
                comment = ''
                text = text[:room_bare]
            # **겹친 따옴표 한가운데서 자르면 안 된다.**  홀수 개가 남으면
            # 그것이 값의 끝으로 읽혀 카드가 깨진다 -- 길이를 맞추려다 위에서
            # 막은 결함을 그대로 만드는 셈이다.
            trail = len(text) - len(text.rstrip("'"))
            if trail % 2:
                text = text[:-1]
        if len(text) < width:
            text = text.ljust(width)
        base = "%-8s= '%s'" % (key, text)
    else:
        if isinstance(value, bool):
            token = 'T' if value else 'F'
        elif isinstance(value, int):
            token = '%d' % value
        else:
            token = repr(float(value))
        base = '%-8s= %20s' % (key, token)

    if comment:
        base += ' / %s' % comment
    elif len(base) + 2 <= CARD:
        base += ' /'
    # comment 를 잃고 값이 카드를 다 채운 경우(68자 값)는 꼬리 없이 그대로 --
    # `' /'` 를 붙이면 [:CARD] 절단이 뒤를 자르므로 결과는 같지만 아래 경고가
    # 오독을 만든다.
    if len(base) > CARD:
        # 값은 위에서 폭에 맞췄으니 넘치는 것은 comment 쪽이다.  자체로는
        # 파싱을 깨지 않지만(인용부호는 살아 있다) **조용한 절단**이라 알린다 --
        # 견본 폭 + comment 가 80자를 넘는 조합은 템플릿 개정에서만 나온다.
        # ⚠️ 폭은 **이 호출이 쓴 표**로 찍는다 -- science 표를 찍으면 guide
        # 저장에서 엉뚱한 숫자가 나온다 (공유 키는 science 폭, guide 전용
        # 키는 0).  2026-08-31 교차검토.
        log.warning('FITS 카드 %s 가 %d자다 -- comment 가 %d자 잘린다.  견본 '
                    '폭(%d)과 comment 길이(%d)의 합이 80자를 넘는다',
                    key.strip(), len(base), len(base) - CARD,
                    (_WIDTH if widths is None else widths).get(key, 0),
                    len(comment))
    return base.ljust(CARD)[:CARD]


def header_bytes(cards, naxis1: int, naxis2: int, *,  # noqa: ANN001
                 widths: dict[str, int] | None = None) -> bytes:
    """카드 목록 -> 2880B 정렬 헤더 바이트열.

    Args:
        cards: `rawcards.render()` 결과 -- `(keyword, value, comment)` 목록.
            구조 카드는 없어도 되고, 있으면 그것을 쓴다 (시험 편의).
        naxis1/naxis2: 구조 카드가 없을 때 선언할 기하.
        widths: 문자열 패딩 폭 표 -- 기본은 science 견본(`_WIDTH`), guide 는
            자기 표(`guidecards.WIDTHS`)를 준다 (`card_image` 참조).

    견본 pair 는 v1.5 에서 값 **131** + COMMENT 8 + END 1 = 140 레코드가 됐고
    (HK 4장 폐지), `END` 뒤를 **공백 레코드 4장**으로 채워 144 레코드 ·
    2880B x 4 = 11,520 바이트를 유지한다 (FITS 표준 패딩, 규격 3장).

    ⚠️ **그 패딩이 여기 있어서 v1.5 반영이 조용히 흡수됐다.**  같은 개정에서
    labtest 스크립트의 `build_header` 는 패딩 없이 정렬 단정만 두고 있었고,
    카드가 4장 줄자 헤더 조립이 통째로 거부됐다 -- 단정만으로는 부족하다.
    """
    have_structural = any(k in rawcards.STRUCTURAL for k, _v, _c in cards)
    out: list[str] = []
    if not have_structural:
        out += [card_image(k, v, c, widths=widths)
                for k, v, c in structural_cards(naxis1, naxis2)]
    for key, value, comment in cards:
        out.append(card_image(key, value, comment, widths=widths))
    out.append('END'.ljust(CARD))

    head = ''.join(out)
    pad = (-len(head)) % BLOCK
    head += ' ' * pad
    blob = head.encode('utf-8')
    # **문자 수가 아니라 바이트 수**로 단정한다 -- 파일에 쓰는 것은 바이트고,
    # 비ASCII 가 섞이면 문자 수는 맞는데 바이트 수가 어긋난다.  `card_image`
    # 가 치환하므로 여기까지 오면 안 되지만, 정렬은 파일 전체의 생사를
    # 가르므로 두 겹으로 막는다.
    if len(blob) % BLOCK:
        raise ValueError('FITS 헤더가 %dB 정렬이 아니다 (%dB) -- 비ASCII 문자?'
                         % (BLOCK, len(blob)))
    return blob


def to_fits_data(raw_le: bytearray) -> memoryview:
    """FETCH 로 받은 리틀엔디언 `uint16` 을 FITS 저장형으로 **제자리에서** 바꾼다.

    규격 3장의 저장형은 `BITPIX=16` + `BZERO=32768` 이다 -- 물리값 0..65535 를
    `값 - 32768` 의 부호 있는 16비트로 담는다.  `uint16` 에 `0x8000` 을 더하면
    (넘침이 감싸므로) 정확히 그 비트 패턴이 되고, 그 다음 빅엔디언으로 뒤집으면
    FITS 바이트 순서가 된다.  labtest 가 검증한 두 줄과 결과가 같다.

    **사본을 만들지 않는다.**  344 MiB 프레임 둘을 동시에 저장하므로 사본 하나가
    곧 수백 MB 다 -- `byteswap(inplace=True)` 로 fetch 버퍼를 직접 고친다.
    그래서 인자는 **쓰기 가능한** `bytearray` 여야 한다.
    """
    import numpy as np
    arr = np.frombuffer(memoryview(raw_le), dtype='<u2')
    arr += np.uint16(0x8000)          # 물리값 -> 부호 있는 16비트 패턴
    arr.byteswap(inplace=True)        # -> 빅엔디언 (FITS)
    return memoryview(raw_le)


def write_frame(path: str, cards, raw_le: bytearray, *,  # noqa: ANN001
                naxis1: int, naxis2: int,
                widths: dict[str, int] | None = None) -> int:
    """raw FITS 파일 하나를 쓰고 **전송률(KB/sec)** 을 돌려준다.

    `raw_le` 는 FETCH 가 준 리틀엔디언 `uint16` 바이트열이고, 길이가 선언 기하와
    맞아야 한다 -- **대조는 fetch 앞에서 이미 끝났어야 한다** (fetch 는 수십
    초가 걸리므로 그 뒤에 거절하는 것은 낭비다).  여기서는 마지막 방어로만
    본다.

    임시 이름(`.part`)으로 쓰고 마지막에 옮긴다.  **중간에 죽은 파일이
    `<SITE>.<날짜>.<번호>.<MK|NT>.fits` 이름을 차지하면 안 된다** -- D-016
    선검사가 그 이름을 점유된 것으로 보고 다음 번호로 밀어 버리고, 반쪽 파일은
    아카이브에 남는다.  실패하면 그 `.part` 도 지운다.

    **이미 있는 파일은 덮지 않는다** (운영자 확정 2026-08-23).  이름을 정하는
    것은 여전히 시퀀서(D-016 선검사)이고 여기서는 "덮어쓰지 않겠다" 고만 한다 --
    선검사와 쓰기 사이에는 `write_delay`+저장시간만큼 **틈**이 있고, 그 틈에
    누가 그 경로에 파일을 두면(같은 `data_dir` 에 ICS 두 개, 백업 되돌림,
    rsync) `os.replace` 가 그것을 말없이 지운다.  둘 중 하나를 잃어야 한다면
    **새 프레임을 버리는 쪽**이 맞다 -- 옛 프레임은 이미 아카이브에 들어갔을 수
    있고 되돌릴 수 없는데, 새 프레임은 다시 찍을 수 있고 오류가 크게 뜬다.
    """
    want = naxis1 * naxis2 * 2
    if len(raw_le) != want:
        raise ValueError(
            'fetch 한 데이터가 %d B 인데 선언 기하는 %dx%d x2 = %d B 다 -- '
            '저장하지 않는다.  ACF 기하와 samplemode 를 확인하라.'
            % (len(raw_le), naxis1, naxis2, want))

    head = header_bytes(cards, naxis1, naxis2, widths=widths)
    data = to_fits_data(raw_le)
    pad = (-want) % BLOCK

    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.part'
    started = time.monotonic()
    try:
        with open(tmp, 'wb') as f:
            f.write(head)
            f.write(data)
            if pad:
                f.write(b'\x00' * pad)
            f.flush()
            os.fsync(f.fileno())
        # **덮어쓰지 않는다.**  `os.replace` 는 그 자리에 뭐가 있어도 말없이
        # 지운다 -- 선검사와 여기 사이의 틈에 생긴 파일이 그렇게 사라진다.
        # 자료 파괴는 되돌릴 수 없으니 새 프레임을 버리고 크게 알린다.
        if os.path.exists(path):
            raise FileExistsError(
                '이미 있는 파일을 덮지 않는다 -- %s.  D-016 선검사 뒤에 누가 '
                '이 경로에 파일을 두었다(같은 data_dir 에 ICS 두 개? 백업 '
                '되돌림?).  이 프레임은 저장하지 않는다' % path)
        os.replace(tmp, path)
    except BaseException:
        # 실패하면 임시 파일을 남기지 않는다 -- `.part` 가 쌓이면 디스크만
        # 먹고 다음 시도의 진단을 흐린다.
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    elapsed = max(time.monotonic() - started, 1e-6)

    total_kb = (len(head) + want + pad) / 1024.0
    return int(total_kb / elapsed)

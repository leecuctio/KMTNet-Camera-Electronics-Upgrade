#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archon 응답 해석 -- `SYSTEM` · `STATUS` · `FRAME` 을 값으로 바꾼다.

세 응답 모두 공백으로 구분된 `KEY=VALUE` 나열이다 (매뉴얼 p.46-50).  여기서는
**해석만** 하고 왕복은 하지 않는다 -- 그래서 실기 없이 시험할 수 있고, 실기
응답 한 줄을 붙여넣어 재현할 수 있다.

필드 이름의 근거는 전부 매뉴얼이다 (2026-08-23 재확인):

| 응답 | 필드 | 쪽 |
|---|---|---|
| `SYSTEM` | `BACKPLANE_ID`(16진 고유 ID = 시리얼 대용) · `BACKPLANE_VERSION` · `MODn_TYPE/REV/VERSION` | p.46 |
| `STATUS` | `POWERGOOD` · `BACKPLANE_TEMP` · `MODm/TEMP` · 전원 레일 `P2V5_V`/`P2V5_I` … | p.47-49 |
| `FRAME` | `RBUF`/`WBUF` · `BUFnCOMPLETE`/`BASE`/`FRAME`/`WIDTH`/`HEIGHT`/`SAMPLE` · **`BUFnLINES`(라인 진행)** · `BUFnPIXELS`(픽셀 진행) | p.49-50 |

⚠️ **`BUFnTIMESTAMP` 는 프레임 기록(readout) 개시 시점**이라 `DATE-OBS`(노출
개시)로 쓸 수 없다.  정밀 시각이 필요하면 `TIMER` ↔ 호스트 UT 상관 + 트리거
에지 타임스탬프(`BUFnREATIMESTAMP` 등)를 봐야 한다.  10 ns tick.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .. import _simpath

_simpath.ensure()

from ics_sim import rawhdr                    # noqa: E402

log = logging.getLogger('ics_archon.parse')

#: `Cn_VOLT`/`Cn_CURR` 자리 순서 -- **`ics_sim` 의 상수를 그대로 쓴다.**
#: 여기 사본을 두면 규격이 개정될 때 한쪽만 고쳐진다.
VOLT_RAILS = rawhdr.VOLT_RAILS

#: `Cn_TEMP` 자리 순서 -- **정본은 `rawhdr.TEMP_MODS`** (raw spec 5.6.1절).
#:
#: ✅ **규격 수록이 끝났다** (v1.5, 2026-08-25).  종전 주석이 "모듈 나열 순서의
#: 정본 명세는 규격 수록 예정" 이라며 잠정 5자리(`BACKPLANE_TEMP` + `MOD5`~
#: `MOD8`)를 두고 있었는데, 5.6.1절이 **science 10자리**를 확정했다.  견본
#: pair 의 `C1_TEMP` 도 처음부터 10개였다 -- 잠정안이 견본과 갈려 있었다.
#:
#: `VOLT_RAILS` 와 같은 이유로 **여기 사본을 두지 않는다** -- 규격이 개정될 때
#: 한쪽만 고쳐지는 것을 막는다.
TEMP_MODS: tuple[str, ...] = rawhdr.TEMP_MODS

#: 나열 카드의 결측 자리에 넣는 값 -- **`'NC'`** (raw spec **5.6.1절**, 운영자
#: 확정 2026-08-26).
#:
#: ⚠️ 단일 HK 온도 카드(`CCDTEMP` 등)의 `'-999.99'` 와 **다르다.**  7자짜리
#: sentinel 이 열 자리를 채우면 79자가 되어 카드 폭(80)을 넘긴다 -- comment 를
#: 다 지워도 안 들어가 값이 잘리고, 나열 카드에서 값이 잘리면 **뒤 항목이
#: 조용히 사라진다.**  `NC` 면 29자로 들어간다.
#:
#: **전 자리가 결측인 경우는 드물지 않다** -- STATUS 무응답 · 미장착 모듈.
#: 그 경우 카드는 `'NC'` 한 토큰이 아니라 **자리 수만큼** `'NC|NC|…'` 로
#: 실린다 (`rawhdr._join_readings`) -- 자리 수 자체가 모듈 구성 판별에 쓰이기
#: 때문이다 (5.6.1절).
#:
#: `VOLT_RAILS`/`TEMP_MODS` 와 같은 이유로 **여기 사본을 두지 않는다.**
FIELD_NC: str = rawhdr.FIELD_NC


def keyvals(payload: bytes | str) -> dict[str, str]:
    """`KEY=VALUE` 나열을 딕셔너리로.  `=` 없는 토큰은 버린다.

    값에는 공백이 없다 (세 응답 모두).  그래서 공백 분리로 충분하다.
    """
    if isinstance(payload, bytes):
        payload = payload.decode('ascii', 'replace')
    out: dict[str, str] = {}
    for token in payload.split():
        key, sep, value = token.partition('=')
        if sep:
            out[key] = value
    return out


# ---------------------------------------------------------------------------
# FRAME
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FrameStatus:
    """`FRAME` 응답에서 뽑은 "가장 최신 프레임" 정보.

    labtest `newest()` 의 반환 6-튜플과 같은 내용에 진행률 필드를 더한 것이다.
    """

    frame: int              #: 프레임 번호.  없으면 -1
    buf: int                #: 0-기준 버퍼 색인 (명령의 `n` 은 buf+1)
    width: int
    height: int
    samplemode: int         #: 0: 16bit, 1: 32bit
    base: int               #: `BUFnBASE` -- FETCH 주소
    lines: int              #: 그 버퍼의 라인 진행
    wbuf: int               #: 쓰기 중 버퍼 (1-기준, 0 = 없음)
    write_lines: int        #: 쓰기 중 버퍼의 라인 진행
    write_height: int       #: 쓰기 중 버퍼의 전체 라인 수

    @property
    def data_bytes(self) -> int:
        """이 프레임의 데이터 바이트 수.

        **`samplemode` 는 기하가 아니라 표본 폭을 바꾼다** -- 32bit 표본이면
        같은 `width x height` 로도 정확히 2배가 된다.  그래서 선언 기하와의
        대조는 픽셀 수가 아니라 **바이트 수**로 해야 한다 (labtest v1.1.1
        회귀 3번: 픽셀 비교는 samplemode 를 못 잡는다).
        """
        return (4 if self.samplemode else 2) * self.width * self.height

    @property
    def progress(self) -> int | None:
        """쓰기 중 프레임의 진행률 [%].  쓰는 중이 아니면 `None`.

        `BUFnLINES`(라인 진행) / `BUFnHEIGHT` 다 (매뉴얼 p.50).  레거시 IC 가
        6/17/28/... 로 듬성듬성 보고한 것은 그쪽 구현 사정이고, 촘촘히 보내도
        OBSAgent 는 문제없다 (DevNote 3.2 -- `PCTREAD=` 는 2회 이상이면
        `READ_3` 에 도달한다).
        """
        if self.wbuf <= 0 or self.write_height <= 0:
            return None
        pct = int(100 * self.write_lines / self.write_height)
        return max(0, min(pct, 99))     # 100 은 완료가 확정된 뒤에만 낸다


def _int(d: dict[str, str], key: str, default: int = 0) -> int:
    raw = d.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        log.warning('FRAME %s=%r 를 정수로 읽을 수 없다 -- %d 로 본다',
                    key, raw, default)
        return default


def newest(fields: dict[str, str]) -> FrameStatus:
    """`FRAME` 응답 -> 가장 최신(완료된) 프레임.

    labtest `newest()` 를 그대로 옮겼다.  판정은 두 단계다 --
    ① `RBUF`(읽기용으로 잠긴 버퍼)를 기본 후보로 삼고 ② 그보다 프레임 번호가
    크고 **완료된** 버퍼가 있으면 그것으로 바꾼다.  버퍼가 셋(bigbuf 는 둘)이라
    가장 최근 것이 반드시 `RBUF` 는 아니다.
    """
    rbuf = _int(fields, 'RBUF', 0) - 1
    frames = [_int(fields, 'BUF%dFRAME' % i) for i in (1, 2, 3)]
    complete = [_int(fields, 'BUF%dCOMPLETE' % i) == 1 for i in (1, 2, 3)]

    if 0 <= rbuf <= 2:
        best_frame, best = frames[rbuf], rbuf
    else:
        best_frame, best = -1, 0
    for i in range(3):
        if frames[i] > best_frame and complete[i]:
            best_frame, best = frames[i], i

    return _status_of(fields, best, best_frame)


def _status_of(fields: dict[str, str], buf: int, frame: int) -> FrameStatus:
    """버퍼 하나(0-기준)의 `FrameStatus`.  진행률 필드는 `WBUF` 에서 온다."""
    n = buf + 1
    wbuf = _int(fields, 'WBUF', 0)
    return FrameStatus(
        frame=frame,
        buf=buf,
        width=_int(fields, 'BUF%dWIDTH' % n),
        height=_int(fields, 'BUF%dHEIGHT' % n),
        samplemode=_int(fields, 'BUF%dSAMPLE' % n),
        base=_int(fields, 'BUF%dBASE' % n),
        lines=_int(fields, 'BUF%dLINES' % n),
        wbuf=wbuf,
        write_lines=_int(fields, 'BUF%dLINES' % wbuf) if wbuf else 0,
        write_height=_int(fields, 'BUF%dHEIGHT' % wbuf) if wbuf else 0,
    )


def buffer_frames(fields: dict[str, str]) -> tuple[int, ...]:
    """세 버퍼의 프레임 번호 (0-기준 순서).  없는 자리는 `-1`.

    **되감김·재시작 판별의 기준선**이다 -- 노출을 걸기 직전에 한 벌 찍어 두고
    (`FrameTicket.prev_frames`), 기다리는 동안 **어느 자리가 새로 바뀌었나**를
    본다.  번호의 크기만으로는 못 가른다: 평소에도 옛 프레임을 담은 버퍼가
    `prev` 보다 작은 번호를 들고 있다 -- **바뀌었다는 사실**이 판별점이다.
    """
    return tuple(_int(fields, 'BUF%dFRAME' % (i + 1), -1) for i in range(3))


def restarted_frame(fields: dict[str, str], prev: int,
                    before: tuple[int, ...]) -> FrameStatus | None:
    """번호가 **새로 바뀐** 완료 버퍼 중 `prev` 보다 크지 않은 것.  없으면 `None`.

    두 가지가 여기 걸린다 -- ① **되감김**(카운터가 한 바퀴 돌아 0 부터 다시)
    ② **컨트롤러 재시작** -- `REBOOT` 또는 백플레인 전원 재투입.  첫 프레임은
    **1** 이다(`0` 은 "없다").  ⚠️ **CCD `POWERON` 과 `WARMBOOT` 는 카운터를 안
    지운다** (2026-09-02 실측, `ics_archon` DevNote 10.7 -- 카운터는 FPGA 쪽에
    산다).  리셋 사건이 적은 것은 이 함수의 오탐이 적다는 뜻이다.  둘 다
    "내 다음 프레임" 을 `frame > prev` 로 찾는 `next_frame()` 에는 **영원히
    안 잡힌다** -- 부르는 쪽이 `frame_timeout` 까지 기다리다 노출을 잃는다.

    ⚠️ **번호 폭을 모르기 때문에 크기 비교로는 못 만든다.**  매뉴얼 p.50 은
    `BUFnFRAME=d ; Buffer n frame number` 라고만 적었다 -- 같은 표에서
    `TIMER=x ; ... 64-bit`, `BUFnTIMESTAMP=x ; ... 64-bit` 처럼 **폭을 아는
    자리에는 폭을 적어 두었으므로** 이 자리는 정말로 미상이다 (2026-08-30
    전수 검색: 매뉴얼에 `wrap`/`rollover`/`overflow` 라는 낱말 자체가 없다).
    그래서 "`prev` 보다 훨씬 작으면 되감김" 같은 휴리스틱을 쓰지 않는다 --
    평소 상태와 구별되지 않아 **정상을 되감김으로 오해**한다.

    대신 **변화**를 본다.  옛 프레임을 담은 버퍼의 번호는 가만히 있고, 엔진이
    새 프레임을 쓸 때만 바뀐다 (매뉴얼 p.71 -- 엔진은 새 프레임을 시작할 때
    "다음 잠기지 않은 버퍼" 를 잡고 그 버퍼의 정보(시각·번호)를 갱신한다).
    그러니 **기다리는 동안 새로 바뀌었는데 `prev` 보다 크지 않다**면 카운터가
    앞으로 안 간 것이고, 그것이 되감김 아니면 재시작이다.

    Args:
        before: 노출을 걸기 직전의 `buffer_frames()` -- 기준선.  비어 있으면
            판별할 수 없으므로 `None` 을 준다 (**추측하지 않는다**).
    """
    if not before or prev < 0:
        return None
    best: tuple[int, int] | None = None
    for i in range(3):
        n = i + 1
        frame = _int(fields, 'BUF%dFRAME' % n, -1)
        if frame < 0 or frame > prev:
            continue                       # 미상이거나 정상 경로(next_frame)
        if i >= len(before) or frame == before[i]:
            continue                       # 안 바뀌었다 -- 옛 프레임 그대로다
        if _int(fields, 'BUF%dCOMPLETE' % n) != 1:
            continue                       # 아직 쓰는 중이다
        if best is None or frame < best[1]:
            best = (i, frame)              # 되감긴 뒤에도 "가장 이른 것"
    return _status_of(fields, best[0], best[1]) if best else None


def next_frame(fields: dict[str, str], prev: int) -> FrameStatus | None:
    """`prev` **이후의 가장 이른** 완료 프레임.  아직 없으면 `None`.

    "최신 프레임" 을 집으면 안 된다 -- 저장은 `write_delay` 뒤 백그라운드라 그
    사이 프레임이 더 나와 있고, 최신 것을 집으면 그 파일이 **남의 노출 픽셀**을
    담는다(헤더는 이 프레임의 것이라 아무 경고도 없다).  "내 다음 프레임" 을
    집고, 그것이 `prev + 1` 이 아니면 부르는 쪽이 "지나쳤다" 로 판정한다.

    ⚠️ **카운터가 뒤로 가면 여기서는 영원히 `None` 이다** -- 되감김이나 컨트롤러
    재시작이 그렇다.  그 경우는 `restarted_frame()` 이 따로 본다: 여기 크기
    비교에 되감김 처리를 섞으면 **정상 상태를 되감김으로 오해**한다(평소에도
    옛 프레임을 담은 버퍼가 `prev` 보다 작다).  매뉴얼 p.71 도 *"이미 받아
    간 것보다 프레임 번호가 **큰** 완료 버퍼"* 라고만 적어 두었다 -- 되감김은
    매뉴얼에도 없는 자리다.  ⚠️ 다만 **매뉴얼이 안 다룬다는 것이 "안 일어난다"
    는 뜻은 아니다** -- 매뉴얼(2021-02-23)은 현행 FW 와 양방향으로 어긋날 수
    있어서 **판정 근거가 아니다**(운영자 2026-08-30, DevNote 8.7).

    **`prev < 0` 인 경우가 첫 실행이다.**  전원을 켜고 아무 프레임도 없으면
    `newest()` 가 `-1` 을 준다.  그때 `prev + 1 = 0` 을 기다리면 컨트롤러가 첫
    프레임에 1 을 붙이는 순간 "0 을 지나쳤다" 가 되어 **첫 노출이 통째로
    버려진다** -- 그래서 번호를 못박지 않고 "이후 가장 이른 것" 으로 찾는다.
    """
    best: tuple[int, int] | None = None
    for i in range(3):
        n = i + 1
        frame = _int(fields, 'BUF%dFRAME' % n, -1)
        if frame > prev and _int(fields, 'BUF%dCOMPLETE' % n) == 1:
            if best is None or frame < best[1]:
                best = (i, frame)
    return _status_of(fields, best[0], best[1]) if best else None


# ---------------------------------------------------------------------------
# STATUS
# ---------------------------------------------------------------------------

def field_value(status: dict[str, str], key: str) -> float | str:
    """STATUS 필드 하나를 수치로.  **결측·비수치는 sentinel 문자열.**

    `float()` 을 방어 없이 쓰면 STATUS 가 비수치 토큰 하나를 주는 것만으로
    저장 경로가 죽는다 -- 그 시점에는 이미 프레임을 fetch 해 둔 뒤라 **읽어낸
    노출이 통째로 버려진다.**  헤더 값 하나 때문에 프레임을 버리는 것은 손해가
    훨씬 크므로 sentinel 로 남기고 저장은 계속한다 (raw spec 5.0절).
    """
    raw = status.get(key)
    if raw is None:
        return FIELD_NC
    try:
        return float(raw)
    except (TypeError, ValueError):
        log.warning('STATUS %s=%r 가 수치가 아니다 -- %s 로 싣는다',
                    key, raw, FIELD_NC)
        return FIELD_NC


def telemetry_of(status: dict[str, str] | None, *,
                 honour_valid: bool = True) -> dict[str, list]:
    """`STATUS` -> 백엔드 `controller_telemetry()` 한 컨트롤러분.

    `{'temp': [...], 'volt': [...], 'curr': [...]}` -- 표기 고정(온도 1자리 ·
    전압/전류 3자리)은 `rawhdr._join_readings` 가 한다.  여기서는 **자리 순서와
    개수**만 지킨다.

    비어 있으면 빈 dict 를 돌려준다 -- `rawhdr.ctrl_telemetry_header()` 가
    그것을 **자리 수만큼의** `'NC|NC|…'` 로 만든다 (규격 5.6.1절 "자리는
    비우지 않는다").  STATUS 무응답과 미장착 모듈을 규격이 똑같이 "전 자리
    결측" 으로 다루므로, 헤더에서 그 둘을 가르지 않는다 -- 가르려고 `'NC'` 한
    토큰을 쓰면 **자리 수가 1이 되어** 읽는 쪽에는 모듈 구성이 달라 보인다.

    Args:
        honour_valid: `VALID=0` 이면 **전 자리를 결측으로 본다** (D4, 운영자
            승인 2026-08-27).  매뉴얼 p.47 이 "n = 1 if remaining status fields
            are valid" 라고 못박으므로, `VALID=0` 인 응답의 온도·전압을 헤더에
            실으면 **무효인 값이 실측값으로 남는다.**  ⚠️ **필드가 없는 경우와
            `VALID=0` 을 가른다** -- 없다고 결측으로 만들면 그 필드를 보고하지
            않는 펌웨어에서 첫 실행이 통째로 `NC` 가 된다 (F2 원칙).

            **감시 기록은 `False` 로 부른다** -- `valid=0` 행도 버리지 않고
            남기는 것이 규칙이고(언제부터 이상했는지가 자료다), 유효 여부는
            기록의 `valid` 열이 따로 말한다.
    """
    if not status:
        return {}
    if honour_valid and status_valid(status) is False:
        return {}
    return {
        'temp': [field_value(status, k) for k in TEMP_MODS],
        'volt': [field_value(status, r + '_V') for r in VOLT_RAILS],
        'curr': [field_value(status, r + '_I') for r in VOLT_RAILS],
    }


def buffer_frame(fields: dict[str, str], buf_n: int) -> int:
    """`FRAME` 에서 버퍼 하나가 **지금** 담고 있는 프레임 번호 (1-기준 번호).

    fetch 직전에 "내 프레임이 아직 그 버퍼에 있나" 를 대조하는 데 쓴다 --
    BIGBUF 는 버퍼가 둘뿐이고 노출 1회가 프레임 2개(flush + 취득)를 만들므로
    다음 노출이 이 버퍼를 덮는다.  덮인 뒤에 fetch 하면 raw 한 장이 **남의
    노출 픽셀**을 담고 헤더는 이 프레임의 것이라 아무 경고도 없다.
    """
    return _int(fields, 'BUF%dFRAME' % buf_n, -1)


def lock_state(fields: dict[str, str]) -> tuple[int, int]:
    """`(RBUF, WBUF)` -- **읽기용으로 잠긴** 버퍼와 **쓰는 중인** 버퍼 (1-기준, 0=없음).

    매뉴얼 p.50: *`RBUF=d ; Current buffer number locked for reading`* ·
    *`WBUF=d ; Current buffer number locked for writing`*.

    ⭐ **`LOCKn` 이 이 FW 에서 실제로 먹는지 확인하는 자리다** (2026-08-30 신설).
    `LOCK1` 을 보낸 뒤 `RBUF` 가 1 이면 **FW 가 잠금을 반영한 것**이고, 그러면
    A-5 판단 ②(`lock_buffer`)의 절반이 실기 관측으로 닫힌다.  이 값은 fetch
    앞의 덮임 대조에서 **이미 읽는 `FRAME` 응답 안에 들어 있다** -- 왕복이 늘지
    않는다.

    ⚠️ **한 방향으로만 결정적이다.**  `RBUF` 가 안 바뀌었다고 *"`LOCK` 이 무효"*
    는 아니다 -- `RBUF` 쪽이 미구현일 수도 있다.  `RBUF` 자체도 매뉴얼의
    주장이고, **매뉴얼은 판정 근거가 아니다**(DevNote 8.7).

    ⭐ `WBUF` 는 **거동**이라 더 강한 증거다 -- fetch 하는 동안 `WBUF` 가 우리가
    잠근 버퍼를 피해 옮겨 갔다면, 그것은 상태 플래그가 아니라 **엔진이 실제로
    다른 버퍼를 쓴 것**이다 (매뉴얼 p.71 의 *"다음 잠기지 않은 버퍼"*).
    """
    return _int(fields, 'RBUF', 0), _int(fields, 'WBUF', 0)


def power_good(status: dict[str, str] | None) -> bool:
    """`POWERGOOD` (매뉴얼 p.47) -- 시스템 전원이 정상인가."""
    return bool(status) and status.get('POWERGOOD', '0').strip() == '1'


#: `POWER=n` -- **CCD 전원의 실제 상태** (매뉴얼 p.47).  `POWERON` 이 성공
#: 응답을 줬다는 것과 전원이 실제로 올라왔다는 것은 다르다.
POWER_STATES = {
    0: 'Unknown (내부 오류)',
    1: 'Not Configured (설정 미적용)',
    2: 'Off',
    3: 'Intermediate (일부 모듈만 전원이 올라왔다)',
    4: 'On',
    5: 'Standby',
}
#: 취득이 성립하는 유일한 상태.
POWER_ON = 4


def power_state(status: dict[str, str] | None) -> int | None:
    """`POWER` (매뉴얼 p.47).  보고가 없으면 `None`."""
    if not status:
        return None
    try:
        return int(str(status.get('POWER', '')).strip())
    except (TypeError, ValueError):
        return None


def overheating(status: dict[str, str] | None) -> bool:
    """`OVERHEAT` (매뉴얼 p.47) -- `1` 이면 과열이다.

    모듈은 과열을 알리면 **스스로 전원을 내린다** (p.20) -- 그 뒤의 프레임은
    자료가 아니라 잔해다.
    """
    return bool(status) and str(status.get('OVERHEAT', '0')).strip() == '1'


def health_problems(status: dict[str, str] | None) -> list[str]:
    """전원·과열 이상을 사람이 읽을 문장으로 (없으면 빈 목록).

    **취득 경로가 이것을 한 번도 안 봤다** (2026-08-24 검토, F2).  전원 레일이
    죽거나 모듈이 과열해도 밖에서는 "취득 실패" 로만 보였고, 원인을 가르려면
    사람이 따로 `STATUS` 를 떠야 했다.  `STATUS` 는 어차피 노출마다 뜨므로
    같은 응답에서 읽어 낸다 -- 왕복이 늘지 않는다.

    ⚠️ **보고가 없는 필드는 이상으로 세지 않는다.**  실기 응답을 아직 못 봤고
    (PROVISIONAL), 없는 필드를 이상으로 세면 첫 실행이 통째로 경보가 된다.
    """
    if not status:
        return []
    bad: list[str] = []
    # ⚠️ **`VALID=0` 이면 나머지 필드를 판정하지 않는다** (2026-08-28).
    # 매뉴얼 p.47 이 "n = 1 if remaining status fields are valid" 라고 못박으므로
    # `POWER`/`POWERGOOD`/`OVERHEAT` 도 그 "나머지" 에 든다 -- 무효인 블록을
    # 읽어 `POWER=0 Unknown` 같은 **가짜 경보**를 내면, 진짜 전원 이상이 왔을
    # 때 사람이 그것을 이미 무시하도록 학습돼 있다.  같은 응답이 헤더에서는
    # `NC` 로 떨어진다(D4) -- 두 경로가 같은 판단을 해야 한다.
    if status_valid(status) is False:
        return ['VALID=0 (이 응답의 나머지 필드는 무효다 -- 판정을 보류한다)']
    if 'POWERGOOD' in status and not power_good(status):
        bad.append('POWERGOOD=0 (시스템 전원 공급 이상)')
    if overheating(status):
        bad.append('OVERHEAT=1 (과열 -- 모듈이 스스로 전원을 내린다)')
    state = power_state(status)
    if state is not None and state != POWER_ON:
        bad.append('POWER=%d %s' % (state, POWER_STATES.get(state, '?')))
    return bad


# ---------------------------------------------------------------------------
# STATUS -- 감시·기록 (층 1·2)
# ---------------------------------------------------------------------------
#
# **판독기가 아니라 기록기다.**  층 1(온도 10 + 레일 7x2 = 24개)은 위
# `telemetry_of()` 가 이미 정확히 그 값을 준다 -- 감시와 FITS 헤더가 **같은
# 함수**를 읽으므로 둘이 어긋날 수 없다(기계 사본을 넷째로 만들지 않는다).
# 여기 있는 것은 그 위에 얹는 것들이다: 응답 자체의 건강 필드(`VALID`/`COUNT`/
# `LOG`), 레일 정상 범위 판정, 그리고 층 2 의 바이어스 16채널이다.


def status_valid(status: dict[str, str] | None) -> bool | None:
    """`VALID` (매뉴얼 p.47) -- 나머지 필드가 유효한가.  **보고가 없으면 `None`.**

    세 값을 갈라야 한다:

    | 반환 | 뜻 | 헤더 |
    |---|---|---|
    | `True` | `VALID=1` -- 나머지 필드가 유효하다 | 실측값 |
    | `False` | `VALID=0` -- **컨트롤러가 무효라고 말했다** | `NC` (D4) |
    | `None` | 필드가 없다 -- 이 펌웨어는 보고하지 않는다 | 실측값 (F2) |

    ⚠️ **`None` 을 `False` 로 접으면 안 된다.**  그러면 `VALID` 를 보고하지
    않는 펌웨어에서 **첫 실행이 통째로 `NC`** 가 된다 -- "보고하지 않는 필드는
    이상으로 세지 않는다" 는 F2 원칙 그대로다.
    """
    if not status:
        return None
    raw = status.get('VALID')
    if raw is None:
        return None
    try:
        return int(str(raw).strip()) != 0
    except (TypeError, ValueError):
        log.warning('STATUS VALID=%r 를 정수로 읽을 수 없다 -- 판정을 '
                    '보류한다(보고 없음과 같게 다룬다)', raw)
        return None


def status_count(status: dict[str, str] | None) -> int | None:
    """`COUNT` (매뉴얼 p.47) -- 내부 상태 레지스터를 갱신한 횟수.

    **두 질의 사이에 안 변하면 새로 잰 것이 아니라 같은 블록이다.**  값 자체는
    뜻이 없고 **직전 행과의 차이**가 신선도다 -- 기록의 `fresh` 열이 그것이다.
    감소하면 래핑 또는 컨트롤러 재기동이다(폭은 매뉴얼 미기재).
    """
    return _opt_int(status, 'COUNT')


def log_count(status: dict[str, str] | None) -> int | None:
    """`LOG` (매뉴얼 p.47) -- 컨트롤러가 들고 있는 로그 항목 수.

    ⚠️ **`FETCHLOG` 로 빼내지 않는다** (운영자 확정 2026-08-27).  이 값 한 열만
    남긴다 -- 이미 파싱하는 응답 안에 있어 **왕복이 0** 이고, 드레인을 안 해도
    신호가 된다: 값이 오르면 컨트롤러가 무언가 기록하고 있다는 뜻이고, 우리
    로그와 나란히 놓으면 "우리가 못 본 사건이 있었나" 를 알 수 있다.  **상한
    근처에 계속 붙어 있으면 놓치고 있다는 신호**다(깊이를 모르는 채로도 읽을
    수 있다).  드레인 승격 기준은 probe 1단계(P-d)가 판단한다.
    """
    return _opt_int(status, 'LOG')


def _opt_int(status: dict[str, str] | None, key: str) -> int | None:
    """정수 필드 하나.  **없거나 안 읽히면 `None`** (0 이 아니다).

    `0` 으로 접으면 "보고하지 않는다" 와 "0 개다" 가 같아진다 -- `LOG` 에서는
    그 둘이 정반대의 뜻이다.
    """
    if not status:
        return None
    raw = status.get(key)
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


#: 전원 레일의 **정상(power good) 범위** -- 매뉴얼 p.41 표 (`(하한, 상한)` [V]).
#:
#: 감시가 수치만 적지 않고 **이탈을 표시**할 근거다.  ⚠️ **비대칭이라 ±% 규칙을
#: 쓰면 틀린다** -- `N6V` 는 하한 −6.6 / 상한 −5.3 인데 `P6V` 는 +5.5 / +6.6 이다.
#:
#: ⚠️ 이 값은 **전원 보드의 저항으로 정해지는 기본값**이므로 (p.42 "The allowed
#: nominal levels are set by resistors on the power board") 유닛마다 다를 수
#: 있다 -- `[archon.rails]` 로 덮을 수 있게 뒀다.
#:
#: 자리 순서는 `VOLT_RAILS`(규격 5.6.1절)와 같고 **`P17V`(+16.4 … +17.5)** 도
#: 표에 있다 -- `SMC_CLAUDE.md` 로 옮겨 적은 표에서 이 한 줄이 빠져 있었다
#: (2026-08-28 매뉴얼 원문으로 확인해 채웠다).
RAIL_LIMITS: dict[str, tuple[float, float]] = {
    'P2V5': (2.1, 2.9),
    'P5V': (4.4, 5.6),
    'P6V': (5.5, 6.6),
    'N6V': (-6.6, -5.3),
    'P17V': (16.4, 17.5),
    'N17V': (-17.7, -16.6),
    'P35V': (34.3, 36.0),
}


def rail_problems(status: dict[str, str] | None,
                  limits: dict[str, tuple[float, float]] | None = None
                  ) -> list[str]:
    """정상 범위를 벗어난 레일 (없으면 빈 목록).  기록의 `rail_flag` 열.

    **보고가 없는 레일은 세지 않는다** (F2 원칙) -- 안 쓰는 레일은 애초에
    배선도 감시도 되지 않으므로(p.42) 결측이 정상이다.  값이 비수치인 경우도
    같다: 그것은 `telemetry_of()` 가 이미 `NC` 로 남긴다.

    ⚠️ **`POWER=4` 가 아니면 바이어스가 ~0 V 다**(p.77).  그건 CCD 바이어스지
    시스템 레일이 아니라 여기에는 영향이 없다 -- 두 층을 섞지 말 것.
    """
    table = RAIL_LIMITS if limits is None else limits
    if not status:
        return []
    bad: list[str] = []
    for rail in VOLT_RAILS:
        span = table.get(rail)
        if span is None:
            continue
        value = field_value(status, rail + '_V')
        if not isinstance(value, float):
            continue                    # 결측·비수치 -- NC 로 이미 남는다
        lo, hi = span
        if value < lo or value > hi:
            bad.append('%s=%.3fV (정상 %.1f..%.1f)' % (rail, value, lo, hi))
    return bad


# -- 층 2 -- 바이어스 채널 ---------------------------------------------------
#
# ⚠️ **ACF 설정 키와 STATUS 키의 문자열이 같다.**  `MODm/HVHC_V1` 은 ACF 에서
# **지령값**("Set the power on voltage", p.60)이고 STATUS 에서 **실측값**
# ("voltage reading", p.48)이다.  `controller.parse_acf()` 가 역슬래시를 `/` 로
# 정규화하므로 `ctrl.config` 와 `ctrl.status` 의 키가 **글자 하나까지 같아진다**
# -- 값도 15 vs 15.02 로 비슷해서 잘못된 dict 를 뒤져도 그럴듯해 보인다.
#
# 그래서 아래 둘은 **인자를 갈라 받는다**: 이름표(어느 채널이 있나)는 ACF 에서,
# 값은 STATUS 에서.  **두 dict 를 절대 합치지 말 것.**

#: 바이어스 계열 이름 -- 모듈 형에 따라 키가 다르다 (매뉴얼 p.48).
#:
#:     LVLC  n=1~24   LV(X)Bias, 10 mA max     LVHC  n=1~6   500 mA max
#:     HVLC  n=1~24   HV(X)Bias, 10 mA max     HVHC  n=1~6   250 mA max
#:
#: ⚠️ **전류 단위가 mA 다** -- 시스템 레일(`P2V5_I` 등)은 A 다.  섞으면 1000배
#: 틀린다.  기록의 열 이름에 단위를 박아 두는 이유가 이것이다.
BIAS_SERIES = ('HVHC', 'HVLC', 'LVHC', 'LVLC')


def bias_channels(config: dict[str, str] | None) -> list[tuple[str, str]]:
    """**ACF** 에서 이름표가 붙은 바이어스 채널을 찾는다.

    돌려주는 것은 `[(필드 앞자리, 이름표), ...]` 이고 앞자리는 `'MOD9/HVHC_1'`
    꼴이다 -- 실제 STATUS 키는 `MOD9/HVHC_V1` · `MOD9/HVHC_I1` 이라
    `bias_readings()` 가 조립한다.

    **왜 ACF 에서 찾나** -- STATUS 는 계열마다 24(또는 6)채널을 전부 보고하지만
    실제로 CCD 에 물린 것은 이름표가 붙은 것뿐이다.  `KMTK_SCI_113` ACF 기준으로
    `MOD4/LVHC` 6 + `MOD9/HVHC` 6 + `MOD9/HVLC` 4 = **16채널**이고 나머지는
    0 V 로 나온다.  전량을 적으면 열이 100개를 넘고 그 대부분이 상수 0 이다.

    **슬롯을 못박지 않는다** -- ACF 를 훑어 찾으므로 채널 구성이 다른 ACF 나
    guide 유닛에도 같은 코드가 그대로 쓰인다.  ⚠️ 그리고 그 구성 변경은
    `CTRLnCFG`(설정) 범프로 드러나야 한다 (규격 4.3절) -- 열 수가 조용히 바뀌면
    과거 기록 파일이 오독된다.  기록이 **날짜별 파일 + 헤더 줄**을 두는 이유가
    그것이다.

    정렬은 `(모듈 번호, 계열, 채널 번호)` 다 -- 실기 science 에서는
    `MOD4/LVHC1..6` -> `MOD9/HVHC1..6` -> `MOD9/HVLC{11,12,23,24}` 순이 된다.
    """
    if not config:
        return []
    found: list[tuple[int, str, int, str]] = []
    for key, value in config.items():
        label = (value or '').strip()
        if not label or not key.startswith('MOD') or '_LABEL' not in key:
            continue
        head, _, chan_txt = key.partition('_LABEL')
        mod_txt, _, series = head.partition('/')
        if series not in BIAS_SERIES:
            continue
        try:
            mod = int(mod_txt[3:])
            chan = int(chan_txt)
        except ValueError:
            continue
        found.append((mod, series, chan, label))
    return [('MOD%d/%s_%d' % (mod, series, chan), label)
            for mod, series, chan, label in sorted(found)]


def bias_readings(status: dict[str, str] | None,
                  channels: list[tuple[str, str]]
                  ) -> list[tuple[str, float | str, float | str]]:
    """**STATUS** 에서 그 채널들의 실측 V [V] · I [mA] 를 읽는다.

    `[(이름표, V, I), ...]` -- 결측·비수치는 `field_value()` 가 `'NC'` 로
    남긴다(자리를 비우지 않는다).

    ⚠️ **`POWER=4` 가 아닐 때의 값은 전 채널 ~0 V 다** (매뉴얼 p.77).  그래서
    기록에 `power` 열이 함께 있어야 하고, 없으면 `BIAS`·전원 꺼진 구간이
    "전 채널 고장" 으로 보인다.
    """
    out = []
    for prefix, label in channels:
        head, _, chan = prefix.rpartition('_')
        out.append((label,
                    field_value(status or {}, '%s_V%s' % (head, chan)),
                    field_value(status or {}, '%s_I%s' % (head, chan))))
    return out


# ---------------------------------------------------------------------------
# SYSTEM
# ---------------------------------------------------------------------------

def unit_identity(system: dict[str, str] | None) -> dict[str, str]:
    """`SYSTEM` -> 백엔드 `controller_info()` 의 한 벌 (`id`/`sn`).

    * `sn` = `BACKPLANE_ID` (16진 16자리 고유 ID).  **컨트롤러가 보고하는
      유일한 개체 식별자**이므로 시리얼 대용이다 (매뉴얼 p.46 -- 모델명
      문자열 필드는 없다).
    * `id` 는 컨트롤러가 모른다 -- 운영이 붙이는 이름(`KMTA-SCI-101`)이라
      `[controllers]` ini 가 정본이다.  여기서는 백플레인 판·펌웨어를 엮어
      **ini 가 비었을 때의 대체값**만 만든다.
    * `cfg`(적용된 ACF 이름)도 컨트롤러가 보고하지 않는다 (p.54) -- 호스트가
      관리한다.  `controller.py` 가 마지막으로 적용한 경로에서 채운다.
    """
    if not system:
        return {}
    sn = system.get('BACKPLANE_ID', '')
    ver = system.get('BACKPLANE_VERSION', '')
    rev = system.get('BACKPLANE_REV', '')
    out: dict[str, str] = {}
    if sn:
        out['sn'] = sn
    if ver or rev:
        # 예: 'ARCHON-X12r2-1.0.408'.  ini 가 채워지면 이 값은 안 쓰인다.
        btype = {'1': 'X12', '2': 'X16'}.get(
            system.get('BACKPLANE_TYPE', ''), 'X??')
        out['id'] = 'ARCHON-%s%s-%s' % (btype,
                                        ('r' + rev) if rev else '', ver)
    return out


def module_types(system: dict[str, str] | None) -> dict[int, int]:
    """슬롯 번호 -> 모듈 형 (`MODn_TYPE`, 매뉴얼 p.46).

    `TEMP_MODS` 의 AD 모듈 가정(5-8)을 **실기에서 확인하는 수단**이다 --
    형 2 가 AD 다.  기동 배너에 찍어 두면 슬롯 가정이 틀린 것이 첫 실행에서
    드러난다.
    """
    out: dict[int, int] = {}
    if not system:
        return out
    for slot in range(1, 17):
        raw = system.get('MOD%d_TYPE' % slot)
        if raw is None:
            continue
        try:
            out[slot] = int(raw)
        except ValueError:
            continue
    return out


#: `MODn_TYPE` 값 -> 이름.  AD = 비디오 모듈.
#:
#: **매뉴얼 p.46 은 15 까지만 정의하고 "16+: Unknown" 이다** -- 그 뒤에 나온
#: 모듈이 있어서다 (운영자 확정 2026-08-27).  실기 ACF 실측으로 둘이 확정됐고,
#: 규격 5.6.1절 라벨표(`TEMP_MOD_LABELS`)가 같은 이름을 쓴다:
#:
#:     17 = ADM       science `MOD5`/`MOD8`.  매뉴얼 p.25 에 모듈 설명은 있다
#:                    (18채널 · 18bit · 12.5 MHz) -- 형 번호만 빠져 있었다
#:     18 = HVYBias   science `MOD9` (KMTC/KMTS).  KMTK 벤치기는 아직 8(HVXBias)
#:
#: ⚠️ **16 은 아직 모른다** -- 매뉴얼 목차에 `DriverX` 장이 따로 있으니(p.28)
#: 그것이거나 다른 신형일 수 있다.  **추측해서 넣지 말 것** -- 이름표가 틀리면
#: 기동 배너가 사람을 잘못 안심시킨다.  모르는 형은 `?16` 처럼 번호가 찍힌다.
MODULE_TYPES = {0: 'None', 1: 'Driver', 2: 'AD', 3: 'LVBias', 4: 'HVBias',
                5: 'Heater', 7: 'HS', 8: 'HVXBias', 9: 'LVXBias',
                10: 'LVDS', 11: 'HeaterX', 12: 'XVBias',
                13: 'ADF', 14: 'ADX', 15: 'ADLN',
                # 매뉴얼 밖 -- 실기 ACF 실측 + 규격 5.6.1 라벨표 (2026-08-27)
                17: 'ADM', 18: 'HVYBias'}

#: **비디오(AD) 계열 전부.**  `2` 하나만 보면 ADF/ADX/ADLN 이 꽂힌 백플레인에서
#: "AD 모듈을 못 찾았다" 가 되어, 슬롯 가정을 확인하라고 만든 1단계 탐침이
#: **모듈이 제자리에 있는데도 경고**를 낸다.  실기 첫 실행에서 가장 먼저 보는
#: 화면이라 그 오경보 하나가 진짜 문제를 덮는다.
#:
#: ⚠️ **`17`(ADM) 이 실기 science 의 비디오 모듈이다** (2026-08-27 추가).  이것이
#: 빠져 있어서 실기 ACF(`MOD5/MOD8_TYPE=17`)에서 `ad` 가 **빈 목록**이 되고,
#: 배너가 "AD 모듈을 못 찾았다" 를 냈다 -- F9 가 막으려던 그 오경보가 형 번호가
#: 달라 그대로 재현됐다.
#:
#: ⚠️ **이것으로 자리 표를 판정하지 않는다** -- 그것은 `field_order_problems()`
#: 의 일이다.  여기는 배너에 "비디오 모듈이 어느 슬롯인가" 를 참고로 찍는 데만
#: 쓴다.
AD_TYPES = frozenset({2, 13, 14, 15, 17})


def temp_mod_slots() -> frozenset:
    """`TEMP_MODS` 가 자리를 준 슬롯 번호 (`BACKPLANE_TEMP` 는 슬롯이 없다)."""
    out = set()
    for field in TEMP_MODS:
        if field.startswith('MOD') and '/' in field:
            try:
                out.add(int(field[3:field.index('/')]))
            except ValueError:
                continue
    return frozenset(out)


def field_order_problems(system: dict[str, str] | None) -> list[str]:
    """`SYSTEM` 의 장착 모듈이 **규격 5.6.1절 자리 표와 맞나** (없으면 빈 목록).

    ⚠️ **종전 판정은 "AD 모듈이 슬롯 5~8 인가" 였고 그것이 틀렸다**
    (2026-08-27).  매뉴얼 p.20 의 "AD 는 중앙 4슬롯" 을 옮긴 잠정안이었는데,
    실기 science 는 AD 계열이 **5·8 둘뿐**이고 6·7 은 빈 슬롯(형 0)이다 --
    `TEMP_MODS` 는 이미 규격 5.6.1절의 10자리로 교체됐는데 이 판정만 남아
    **정상 구성에서 경고가 났다.**

    그래서 AD 슬롯을 짚는 대신 **정말 지켜야 하는 불변식**을 검사한다 --
    "자리 표가 자리를 준 모듈" 과 "실제로 장착·보고된 모듈" 이 같은가.  자리
    수 자체가 모듈 구성 판별에 쓰이므로(5.6.1절) 이것이 어긋나면 소비자는
    **다른 모듈의 온도를 그 모듈 값으로 읽는다.**

    슬롯 번호를 못박지 않으므로 science 10자리와 guide 8자리에 **같은 검사가
    그대로** 쓰인다.
    """
    mods = module_types(system)
    if not mods:
        return []
    present = frozenset(s for s, t in mods.items() if t)
    expected = temp_mod_slots()
    bad: list[str] = []
    extra = sorted(present - expected)
    missing = sorted(expected - present)
    if extra:
        bad.append('장착된 슬롯 %s 가 자리 표에 없다 -- 그 모듈 온도는 '
                   'Cn_TEMP 에 실리지 않는다' % extra)
    if missing:
        bad.append('자리 표의 슬롯 %s 가 미장착·무보고다 -- 그 자리는 NC 로 '
                   '실린다' % missing)
    return bad

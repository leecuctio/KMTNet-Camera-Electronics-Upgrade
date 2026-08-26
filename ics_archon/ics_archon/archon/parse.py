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

#: `Cn_TEMP` 자리 순서 -- **정본은 `rawhdr.TEMP_SLOTS`** (raw spec 5.6.1절).
#:
#: ✅ **규격 수록이 끝났다** (v1.5, 2026-08-25).  종전 주석이 "모듈 나열 순서의
#: 정본 명세는 규격 수록 예정" 이라며 잠정 5자리(`BACKPLANE_TEMP` + `MOD5`~
#: `MOD8`)를 두고 있었는데, 5.6.1절이 **science 10자리**를 확정했다.  견본
#: pair 의 `C1_TEMP` 도 처음부터 10개였다 -- 잠정안이 견본과 갈려 있었다.
#:
#: `VOLT_RAILS` 와 같은 이유로 **여기 사본을 두지 않는다** -- 규격이 개정될 때
#: 한쪽만 고쳐지는 것을 막는다.
TEMP_SLOTS: tuple[str, ...] = rawhdr.TEMP_SLOTS

#: 나열 카드의 결측 자리에 넣는 값 -- **`'NC'`** (raw spec **5.6.1절**, 운영자
#: 확정 2026-08-26).
#:
#: ⚠️ 단일 HK 온도 카드(`CCDTEMP` 등)의 `'-999.99'` 와 **다르다.**  7자짜리
#: sentinel 이 열 자리를 채우면 79자가 되어 카드 폭(80)을 넘긴다 -- comment 를
#: 다 지워도 안 들어가 값이 잘리고, 나열 카드에서 값이 잘리면 **뒤 항목이
#: 조용히 사라진다.**  `NC` 면 29자로 들어간다.
#:
#: **전 자리가 결측인 경우는 드물지 않다** -- STATUS 무응답 · 미장착 모듈.
SLOT_NC = 'NC'


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


def next_frame(fields: dict[str, str], prev: int) -> FrameStatus | None:
    """`prev` **이후의 가장 이른** 완료 프레임.  아직 없으면 `None`.

    "최신 프레임" 을 집으면 안 된다 -- 저장은 `write_delay` 뒤 백그라운드라 그
    사이 프레임이 더 나와 있고, 최신 것을 집으면 그 파일이 **남의 노출 픽셀**을
    담는다(헤더는 이 프레임의 것이라 아무 경고도 없다).  "내 다음 프레임" 을
    집고, 그것이 `prev + 1` 이 아니면 부르는 쪽이 "지나쳤다" 로 판정한다.

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

def slot_value(status: dict[str, str], key: str) -> float | str:
    """STATUS 필드 하나를 수치로.  **결측·비수치는 sentinel 문자열.**

    `float()` 을 방어 없이 쓰면 STATUS 가 비수치 토큰 하나를 주는 것만으로
    저장 경로가 죽는다 -- 그 시점에는 이미 프레임을 fetch 해 둔 뒤라 **읽어낸
    노출이 통째로 버려진다.**  헤더 값 하나 때문에 프레임을 버리는 것은 손해가
    훨씬 크므로 sentinel 로 남기고 저장은 계속한다 (raw spec 5.0절).
    """
    raw = status.get(key)
    if raw is None:
        return SLOT_NC
    try:
        return float(raw)
    except (TypeError, ValueError):
        log.warning('STATUS %s=%r 가 수치가 아니다 -- %s 로 싣는다',
                    key, raw, SLOT_NC)
        return SLOT_NC


def telemetry_of(status: dict[str, str] | None) -> dict[str, list]:
    """`STATUS` -> 백엔드 `controller_telemetry()` 한 컨트롤러분.

    `{'temp': [...], 'volt': [...], 'curr': [...]}` -- 표기 고정(온도 1자리 ·
    전압/전류 3자리)은 `rawhdr._join_readings` 가 한다.  여기서는 **자리 순서와
    개수**만 지킨다.

    비어 있으면 빈 dict 를 돌려준다 -- `rawhdr.ctrl_telemetry_header()` 가
    그것을 `'NC'` 로 만든다.  자리마다 sentinel 을 채워 보내면 "물어봤는데 다
    결측" 과 "안 물어봤다" 가 헤더에서 구별되지 않는다.
    """
    if not status:
        return {}
    return {
        'temp': [slot_value(status, k) for k in TEMP_SLOTS],
        'volt': [slot_value(status, r + '_V') for r in VOLT_RAILS],
        'curr': [slot_value(status, r + '_I') for r in VOLT_RAILS],
    }


def buffer_frame(fields: dict[str, str], buf_n: int) -> int:
    """`FRAME` 에서 버퍼 하나가 **지금** 담고 있는 프레임 번호 (1-기준 번호).

    fetch 직전에 "내 프레임이 아직 그 버퍼에 있나" 를 대조하는 데 쓴다 --
    BIGBUF 는 버퍼가 둘뿐이고 노출 1회가 프레임 2개(flush + 취득)를 만들므로
    다음 노출이 이 버퍼를 덮는다.  덮인 뒤에 fetch 하면 raw 한 장이 **남의
    노출 픽셀**을 담고 헤더는 이 프레임의 것이라 아무 경고도 없다.
    """
    return _int(fields, 'BUF%dFRAME' % buf_n, -1)


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
    if 'POWERGOOD' in status and not power_good(status):
        bad.append('POWERGOOD=0 (시스템 전원 공급 이상)')
    if overheating(status):
        bad.append('OVERHEAT=1 (과열 -- 모듈이 스스로 전원을 내린다)')
    state = power_state(status)
    if state is not None and state != POWER_ON:
        bad.append('POWER=%d %s' % (state, POWER_STATES.get(state, '?')))
    return bad


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

    `TEMP_SLOTS` 의 AD 모듈 가정(5-8)을 **실기에서 확인하는 수단**이다 --
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


#: `MODn_TYPE` 값 -> 이름 (매뉴얼 p.46 전량).  AD = 비디오 모듈.
MODULE_TYPES = {0: 'None', 1: 'Driver', 2: 'AD', 3: 'LVBias', 4: 'HVBias',
                5: 'Heater', 7: 'HS', 8: 'HVXBias', 9: 'LVXBias',
                10: 'LVDS', 11: 'HeaterX', 12: 'XVBias',
                13: 'ADF', 14: 'ADX', 15: 'ADLN'}

#: **비디오(AD) 계열 전부.**  `2` 하나만 보면 ADF/ADX/ADLN 이 꽂힌 백플레인에서
#: "AD 모듈을 못 찾았다" 가 되어, 슬롯 가정(`TEMP_SLOTS`)을 확인하라고 만든
#: 1단계 탐침이 **모듈이 제자리에 있는데도 경고**를 낸다.  실기 첫 실행에서
#: 가장 먼저 보는 화면이라 그 오경보 하나가 진짜 문제를 덮는다.
AD_TYPES = frozenset({2, 13, 14, 15})

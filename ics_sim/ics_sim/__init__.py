#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KMTNet ICS simulator.

레거시 ICS(ICIMACS/IMPv2.5)와 호환되는 메시지를 내는 카메라 통합제어 시뮬레이터.
바깥으로는 레거시와 같은 규약을, 안으로는 신규 통합 구조(ICS + K/M/T/N.IC +
K/M/T/N.CB = 9노드)를 따른다.  설계 근거와 실측 자료는 DevNote.md 참고.
"""

from __future__ import annotations

#: 취득 프로그램 이름.  실기 프로그램(`ics_archon`)은 자기 값을 갖는다.
PROGRAM = 'ics_sim'

__version__ = '0.1.0'

#: **마지막 갱신 일시 (UTC).  손으로 적는다.**
#:
#: 파이썬 스크립트라 컴파일 시각이 없다 -- 그래서 빌드 일시를 자동으로 얻을
#: 방법이 없고, 코드에 적어 두는 것이 유일한 방법이다 (운영자 확정 2026-08-13).
#:
#: ⚠️ **소스를 고치면 이 값을 같이 고쳐야 한다.**  안 고치면 헤더가 옛 일시를
#: 주장하고, 그건 `ICSBUILD` 를 둔 목적(헤더 이상을 소스 상태로 되짚기)을
#: 무력화한다.  자동으로 못 잡는 값이므로 `RELEASE_CHECKLIST` 항목이다.
#:
#: **파일 mtime 을 쓰지 않는 이유**: git checkout·복사·배포가 mtime 을 바꾸므로
#: "언제 만든 코드인가" 와 무관해진다.  손으로 적은 값이 덜 정확해 보여도
#: 실제로는 더 정확하다.
#:
#: ⚠️ **끝의 `Z`(UTC 표시자)는 일부러 붙인 것이다 -- 지우지 말 것**
#: (운영자 확정 2026-08-13).  FITS 시각 카드(`DATE-OBS`·`TSHOPEN`·`TCSQDATE` …)는
#: `Z` 를 붙이지 않고 `TIMESYS='UTC'` 로 한 번 선언한다.  그래서 이 값만 규칙이
#: 다른 것처럼 보이는데, `ICSBUILD` 는 **시각 카드가 아니라 사람이 떼어 읽는
#: 식별자**다 -- 버그 리포트·로그에 붙여넣으면 `TIMESYS` 가 옆에 없으므로 `Z` 가
#: 값을 한다.  일관성만 보고 지우면 시간대 없는 문자열이 남는다.
__build_date__ = '2026-08-13T07:00Z'


def build_id(program: str = PROGRAM, version: str = __version__,
             build_date: str = __build_date__) -> str:
    """FITS `ICSBUILD` · `AUXSTATUS` 꼬리의 `ICSBUILD=` 에 싣는 값.

    형태는 `<프로그램>-v<버전>:<빌드일시>` 다.  레거시 관례
    (`'KX2016-03-23:1381'` = 접두 + 날짜 + `:` + 번호)를 느슨하게 잇되 **프로그램
    이름을 앞에 둔다** -- 신규는 취득 프로그램이 둘(`ics_sim` · `ics_archon`)이라
    어느 쪽이 쓴 파일인지가 값 안에 보여야 한다.

        >>> build_id()
        'ics_sim-v0.1.0:2026-08-13T07:00Z'

    ⚠️ **`build_id('ics_archon')` 처럼 이름만 바꿔 부르지 말 것.**  그러면 이름은
    `ics_archon` 인데 버전·일시는 `ics_sim` 것이 실려 **거짓 provenance** 가 된다.
    실기 프로그램은 자기 패키지에 `PROGRAM`·`__version__`·`__build_date__` 세
    상수를 두고 같은 형태를 만든다 -- 이 함수를 재사용할 거면 세 값을 다 넘긴다.
    """
    return f'{program}-v{version}:{build_date}'

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""icg_archon -- 실기 ICG (STA Archon guide 유닛 제어 + HK 로깅).

`ics_sim`(시퀀서 골격·명령 처리부·메시지 규약·TC 중계)과 `ics_archon` 의
Archon 계층(`archon/protocol·parse·controller·fitswrite`)을 **그대로 가져다
쓰고**, guide 에만 있는 것을 이 패키지가 채운다:

* guide raw FITS (raw spec v1.9 **9·10장**) -- 파일 1개/프레임,
  `<SITE>.<YYYYMMDD>.<NNNNNN>.G.fits`, 4224x1033, 값 카드 123장
* frame-transfer 노출 의미론 (10.1절) -- 셔터 없음, **첫 프레임 폐기**,
  `go n` = n+1 독출 n 저장, `EXPTIME` = 독출 개시 간격,
  `DATE-OBS` = 직전 독출 개시
* HK 취득·로깅 (1분 주기) -- Ctrl(`C1_*`) · DIO(`DEWPRES`) ·
  RTD(`CCDTEMP` 등 6장) · Radionode(`HEBOX`/`FSATEMP`/`FSAHUM`) ·
  AUX(`ENS1~7`).  `ics_archon` 이 이 로그를 읽어 science 헤더를 채운다.

레거시 대응은 `ics_legacy/icg_legacy_report.md` 9장 -- 신규 `icg` 는 레거시
`ICG` + `G.IC` + `G.CB` 3노드의 통합이고, 내부 UDP 경계는 함수 호출로
대체한다.  외부 인터페이스는 `go`/`guideexp` 수신(ABC)·TC 질의·XIS 등록.

버전 규약은 `ics_sim.build_id()` 를 따른다 -- 두 상수를 손으로 올린다
(`ICGBUILD` 카드가 이 값을 싣는다, raw spec 10.3절).
"""

from ics_archon import _simpath

_simpath.ensure()

from ics_sim import build_id as _sim_build_id   # noqa: E402

#: 손으로 올리는 판 -- 소스를 고치면 `__build_date__` 도 같이 올린다.
__version__ = '0.0.0'
__build_date__ = '2026-08-31T10:00Z'


def build_id() -> str:
    """FITS `ICGBUILD` 값 -- `v<버전>:<빌드일시>Z` (raw spec 10.3절).

    `ics_sim.build_id()` 에 **이 패키지의** 두 상수를 넘긴다 -- 기본값을
    쓰면 `ics_sim` 의 판이 실려 거짓 provenance 가 된다 (그쪽 docstring).
    """
    return _sim_build_id(__version__, __build_date__)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`[archon]` 설정 -- 컨트롤러 주소 · ACF · 프로토콜 여유값.

**`ics_sim` 의 `config.py` 를 건드리지 않는다.**  같은 ini 파일의 다른 절을
읽을 뿐이다 -- `ics_sim.config.load()` 는 모르는 절을 조용히 지나가므로
(`site.*` 만 경고한다) 한 파일에 `[archon]` 을 더해도 안전하다.  그래야
`ics_archon.ini` 하나로 두 층을 다 설정할 수 있다.

값의 출처가 셋으로 갈린다는 점을 알아 둘 것:

* **`[archon]`** -- 이 파일.  주소 · ACF 경로 · 시한처럼 **기기 배선**에 관한 것.
* **`[controllers]`** (`ics_sim`) -- FITS `CTRLnID/SN/CFG` · `RDMODE`.  헤더에
  실리는 **선언**이고, 채워져 있으면 백엔드 보고값을 이긴다.
* **`[camera]`·`[site]`** (`ics_sim`) -- 그 밖의 `ICS INI` 출처 카드.

즉 "컨트롤러에 어떻게 접속하나" 는 여기, "헤더에 뭐라고 적나" 는 저쪽이다.
겹쳐 보이지만 갈라 두는 편이 낫다 -- 실험실에서 주소를 바꿔도 헤더의 정체는
그대로여야 하고, 그 반대도 있다.
"""

from __future__ import annotations

import configparser
import logging
import math
import os
import shutil
import time
from dataclasses import dataclass, field

from . import _simpath

_simpath.ensure()

from ics_sim import rawhdr, rawpair          # noqa: E402
from ics_sim.config import ControllersCfg    # noqa: E402

log = logging.getLogger('ics_archon.config')

#: 컨트롤러 태그 (`rawpair.CONTROLLERS` 의 색인 순서 = 1:MK, 2:NT)
CTRLTAGS = tuple(tag for tag, _ in rawpair.CONTROLLERS)

#: ACF 이름에 들어 있는 독출 모드 토큰 -> FITS `RDMODE`.  labtest 의 유도
#: 규칙 그대로다 (`KMTNet_Sci_fast_med_U13.acf` -> `FAST`).
#:
#: ⚠️ **현행 ACF 이름 규칙에는 이 토큰이 없다** (`acf/README.md` — 일곱 전부
#: `<SITE>_<역할>_<유닛>_<시리얼>_<ACF판>[_<조>]`).  그래서 실기에서 이 유도는
#: 늘 빈손이고, `RDMODE` 는 **ini 에 적은 값**이 정본이다 (현행 전부 `NORMAL`,
#: 운영자 확정 2026-08-29).  규칙을 남겨 둔 것은 속도별 ACF 가 다시 올 때를
#: 위한 것이고, `_cross_checks()` 가 **양방향으로** 어긋남을 본다.
_RDMODE_TOKENS = ('fast', 'comp', 'slow')


def rdmode_from_acf(path: str) -> str:
    """ACF 파일명에서 `RDMODE` 를 유도한다.  못 알아보면 빈 문자열.

    빈 문자열을 돌려주는 것이 중요하다 -- 그러면 `rawhdr` 의 코드 기본값
    (`NORMAL`)이 실린다.  여기서 `'NORMAL'` 을 만들어 넣으면 "유도 실패" 와
    "정말 NORMAL" 이 구별되지 않는다.

    ⚠️ 여기는 **토큰을 찾을 뿐**이라 `splitext` 로 충분하다 -- 값 자체가 되는
    `cfg_name_from_acf()` 와 자르기 규칙이 다른 이유다.
    """
    name = os.path.splitext(os.path.basename(path or ''))[0].lower()
    for token in _RDMODE_TOKENS:
        if token in name:
            return token.upper()
    return ''


#: `CTRLnCFG` 값에서 떼는 설정 파일 확장자.  **이 둘만 뗀다** (운영자 확정
#: 2026-08-29).
#:
#: ⚠️ **범용 `os.path.splitext` 를 쓰지 말 것** -- ACF 판 번호에 점이 들어간다
#: (`KMTA_SCI_101_R2609.1.acf`).  확장자 없이 적힌 경로를 받으면 `splitext` 가
#: `.1` 을 먹어 **판 번호가 조용히 깨진다**(`…_R2609`).  모르는 접미는 그대로
#: 두는 것이 규칙이다 -- 임의로 떼면 값이 소리 없이 달라진다.
#:
#: `.cfg` 도 **같은 Archon 설정 파일**이다 (운영자 확인 2026-08-29) -- 다른
#: 종류가 아니라 확장자 표기가 갈릴 수 있어서 둘을 나란히 받는다.
CFG_SUFFIXES = ('.acf', '.cfg')


def cfg_name_from_acf(path: str) -> str:
    """ACF 경로에서 `CTRLnCFG` 값을 만든다 -- **폴더와 확장자를 뗀 이름**.

    규격 5.5절이 못박은 형태다 (raw spec v1.8):

        ~/AIC/Config/acf/KMTC_SCI_101_STA0284_R2608_MK.acf
        ->               KMTC_SCI_101_STA0284_R2608_MK

    경로가 비었거나 이름이 통째로 확장자면 빈 문자열을 돌려준다 -- 그러면
    부르는 쪽이 "유도 실패" 를 알아보고 손편집 값이나 백엔드 보고값에
    맡긴다.  바로 위 `rdmode_from_acf()` 가 빈 문자열을 쓰는 것과 같은
    약속이다.
    """
    name = os.path.basename((path or '').strip())
    lowered = name.lower()
    for suffix in CFG_SUFFIXES:
        if lowered.endswith(suffix):
            # **길이를 접미에서 뽑는다** -- 지금은 둘 다 4자라 리터럴 `-4` 로도
            # 맞지만, 목록이 늘 때 그 우연에 기대면 값이 잘려 나간다.
            return name[:-len(suffix)]
    return name


class ArchonConfigError(Exception):
    """`[archon]` 설정을 읽을 수 없다."""


@dataclass
class ArchonCfg:
    """컨트롤러 계통 설정.  기본값은 실험실 스크립트의 실측값에서 왔다."""

    # -- 대수 ------------------------------------------------------------
    #: **운영할 컨트롤러 수** (`[archon] n_controllers`, 운영자 지시
    #: 2026-08-24).  `1` 또는 `2` 뿐이고 **그 밖의 값은 기동을 거부**한다.
    #:
    #: `1` 이면 어느 쪽 한 대인지를 `[controllers] ctrl1_id`/`ctrl2_id` 의
    #: **선언 여부**가 정한다 -- `ctrl1_id` 가 있으면 `MK`, `ctrl2_id` 가 있으면
    #: `NT`.  결정된 값은 `solo_tag` 에 담긴다.
    #:
    #: ⚠️ 1대 운영은 CCD 가 둘뿐이므로 **OBSAgent 규약을 만족하지 못한다**
    #: (`Acquisition Complete.`/`Wrote` 가 4회가 아니라 2회).  실험실 단독
    #: 취득용이고, 관측 시퀀스 시험은 2대에서 한다 (README "실기 첫 실행 4단계").
    n_controllers: int = 2
    #: 1대 운영일 때의 태그 (`MK` 또는 `NT`).  2대면 빈 문자열.
    solo_tag: str = ''

    # -- 접속 ------------------------------------------------------------
    #: 컨트롤러 태그 -> IP.  비어 있는 태그는 **없는 컨트롤러**다.
    hosts: dict[str, str] = field(default_factory=dict)
    port: int = 4242
    #: 소켓 recv 상한 [s].  labtest `UNIT_TIMEOUT` 과 같은 값이다 -- 짧게
    #: 두는 것이 의도다(끊긴 것을 빨리 알아채야 한다).  FETCH 는 자료가
    #: 계속 흐르므로 이 값에 걸리지 않는다.
    sock_timeout: float = 1.0
    connect_retry: int = 4

    # -- ACF -------------------------------------------------------------
    #: 컨트롤러 태그 -> ACF 경로.  **상대경로면 작업 디렉터리 기준**이다
    #: (labtest 가 여기서 가장 많이 넘어졌다 -- 경로를 못 찾으면 멈춘다).
    acf: dict[str, str] = field(default_factory=dict)
    #: 첫 노출 준비에서 ACF 를 적용할지.  false 면 CLEARCONFIG/WCONFIG/APPLYALL
    #: 을 건너뛰고 줄 번호만 파싱해 RCONFIG 로 대조한다 -- 컨트롤러가 설정 줄을
    #: 들고 있어 **프로그램** 재기동이 빠르다.
    #: ⚠️ "적용" 은 **그 세션의 APPLYALL** 이다 (매뉴얼 p.51).  컨트롤러를
    #: REBOOT 했거나 백플레인 전원을 다시 넣었으면 RCONFIG 가 맞아도 POWERON 이
    #: `?xx` 로 거부된다 (2026-09-01 실기, DevNote 10.2) -- 그때는 true 로.
    apply_acf: bool = True
    acf_retry: int = 4
    #: POWERON 뒤 CCD flush 를 기다리는 시간 [s] (labtest: 24 x 0.5).
    poweron_wait: float = 12.0

    # -- 노출 파라미터 슬롯 (ACF 마다 다르다) -----------------------------
    #
    # labtest 는 `SetConfig('PARAMETER2', 'IntMS=%d')` · `SetConfig(
    # 'PARAMETER1', 'Exposures=1')` 로 썼다.  **슬롯 번호와 파라미터 이름은
    # 둘 다 ACF 소관**이라 다른 ACF 를 쓰면 어긋난다 -- 리터럴로 박아 두면
    # 그 어긋남이 "노출이 안 걸린다" 로만 보인다.
    param_intms_slot: str = 'PARAMETER2'
    param_intms_name: str = 'IntMS'
    param_exposures_slot: str = 'PARAMETER1'
    param_exposures_name: str = 'Exposures'

    # -- 텔레메트리 ------------------------------------------------------
    #: STATUS 를 떠서 `Cn_TEMP/VOLT/CURR` 를 채울지.  **false 로 두면
    #: 컨트롤러와의 왕복이 labtest v1.0 계보와 완전히 같아진다** -- 실기에서
    #: 이상이 보이면 여기부터 끄고 취득을 지킨다 (`Cn_*` 는 `NC` 로 실린다).
    telemetry: bool = True
    status_timeout: float = 3.0

    # -- 텔레메트리 주기 감시·기록 (층 1·2, 2026-08-28) --------------------
    #: 배경 감시를 돌릴지.  **`telemetry = false` 면 이 값과 무관하게 안 돈다**
    #: -- 그 설정의 뜻이 "컨트롤러와의 왕복을 labtest v1.0 계보와 똑같이 둔다"
    #: 이므로 감시도 예외가 아니다.
    #:
    #: 감시는 **헤더용 스냅샷(`ctrl.status`)을 건드리지 않는다** -- 살아 있는
    #: 값은 `ctrl.status_live` 에 따로 든다.  섞으면 `Cn_TEMP` 의 뜻이 "노출
    #: 개시 시점 값" 에서 "마지막 폴링 값" 으로 조용히 바뀌고, 폴링 간격·락
    #: 경합에 따라 **노출마다 달라져 비결정적**이 된다.
    monitor: bool = True
    #: 기록 간격 [s].  운영자 확정 **수십 초 ~ 수 분** (2026-08-27) -- 기본 20초.
    #:
    #: 이 간격이라 FETCH 락(최대 수 분)에 밀려 표본 한두 개를 건너뛰는 것은
    #: **문제로 보지 않는다.**  밀린 시간은 기록의 `lag_ms` 열에 남고, 밀린
    #: 만큼 몰아서 뜨지는 않는다.
    monitor_interval: float = 20.0
    #: 기록 자리.  **`~/AIC/log/`** (운영자 확정 2026-08-27).
    #:
    #: ⚠️ `[paths] data_dir` 밑에 두지 않는다 -- 자료와 함께 굴러가 아카이브
    #: 정책에 걸린다.  `~` 는 읽을 때 펼친다(안 펼치면 **cwd 아래 `~` 폴더**가
    #: 조용히 생기고 오류도 안 난다).
    monitor_log: str = '~/AIC/log'
    #: **듀어·환경 HK 의 원천** -- `icg_archon` 이 남기는 원자적 최신 스냅샷
    #: (`hk_latest.G.json`).  비우면 5.6절 HK 카드가 sentinel 로 실린다.
    #: 물리 원천(guide 유닛 RTD·진공 · Radionode)은 접속자 규칙상 icg 만
    #: 읽을 수 있어, science 는 이 파일을 통해 받는다 (운영자 확정 2026-08-31).
    hk_latest: str = ''
    #: 스냅샷 표본의 신선도 한도 [s] -- 이보다 낡은 키는 버린다 (icg 주기
    #: 60s 의 5배.  낡은 값이 새 값처럼 실리는 것이 결측보다 나쁘다).
    hk_stale_after: float = 300.0
    #: 전원 레일의 정상 범위 [V].  **`None` 이면 매뉴얼 p.41 기본값**
    #: (`archon.parse.RAIL_LIMITS`).
    #:
    #: 그 값은 **전원 보드의 저항으로 정해지는 기본값**이라(p.42) 유닛마다 다를
    #: 수 있어 `[archon.rails]` 절로 덮을 수 있게 뒀다.  ⚠️ **비대칭이라 ±%
    #: 규칙을 쓰면 틀린다** -- `N6V` 는 −6.6 … −5.3 인데 `P6V` 는 +5.5 … +6.6 이다.
    #:
    #: 기본값을 여기 사본으로 두지 않는 이유는 `parse.VOLT_RAILS` 와 같다 --
    #: 한쪽만 고쳐지는 것을 막는다 (그리고 `config` 가 `archon` 을 import 하면
    #: 순환이 된다).
    rail_limits: dict | None = None

    # -- 노출·독출 -------------------------------------------------------
    #: 셔터 트리거(TRIGOUTFORCE)를 내는 컨트롤러.  `both` 면 둘 다.
    #: 실기 배선이 확인되면 한쪽으로 좁힌다 (검토사항).
    shutter_ctrl: str = 'BOTH'
    #: `ERASE` 를 **전체 독출 flush** 로 처리할지 (labtest `bFullFlush`).
    #:
    #: ⛔ **기본값이 `False` 다** (운영자 확정 2026-08-29) -- *"이제는 clock 을
    #: 개선해서 별도 erase 를 하지 않고 바로 노출을 시작한다"*.  종전 기본값
    #: `True` 는 **clock 개선 전의 전제**였다.
    #:
    #: ⚠️ **켜면 노출마다 독출 1회분(실측 12.77초 -- 사강 `NoIntMS` 0.5 가 붙으면
    #: 13.27초, DevNote 10.4)이 더 붙는다** -- 실기 ERASE 는 전체 독출이기 때문이다.  labtest 도 1년 실사용을 `bFullFlush=False` 로
    #: 했고(`GetDataset(..., False, False, ...)`), 그 자료가 근거다.
    full_flush_on_erase: bool = False
    #: fetch 하는 동안 프레임 버퍼를 `LOCKn` 으로 잠글지 (매뉴얼 p.50).
    #:
    #: **BIGBUF 는 버퍼가 둘뿐이고 노출 1회가 프레임 2개**(flush + 취득)를
    #: 만들므로 다음 노출이 이 프레임의 버퍼를 덮는다 -- 저장은 `write_delay`
    #: 뒤에 백그라운드로 도는 일이라 그 경합이 실재한다.
    #: 매뉴얼 p.71 은 `LOCK` 을 **통상 경로**로 적어 두었다.  ⚠️ **그것은 판정이
    #: 아니라 가설의 강도다** -- 매뉴얼(2021-02-23)은 현행 FW 와 **양방향으로
    #: 어긋날 수 있고**(문서에 있는데 FW 에 없거나 그 반대), 이 저장소 안에 이미
    #: 반례가 둘 있다(`MODn_TYPE` 16+ · AD 모듈 슬롯).  **판단 근거는 실측**이다
    #: (운영자 2026-08-30, DevNote 8.7).
    #:
    #: ⭐ **기본이 `true` 인 이유는 값이 있어서**다 -- 주기 13.27초 · fetch 3.4초면
    #: fetch 중 프레임 경계가 걸릴 확률 ≈26% 이고, 그때 잠금이 없으면 엔진이
    #: 우리가 읽는 중인 버퍼를 집어 간다 (2026-09-01 `nolock` 2/2 관측).  켜는
    #: 대가는 0 이다 (`lock` = `idle` = 368 행/초).  (종전 "더 안전한 쪽이라서 ·
    #: 실기에서 지연·정지가 확인되면 즉시 끈다" 는 실기 전의 판단이었다 --
    #: 지연·정지는 두 유닛에서 재현되지 않았다, DevNote 10.6.)
    #:
    #: ⚠️ labtest 는 2026-05-28 에 `LOCK` 을 뺐다("remove to fetch debug") --
    #: 되돌린 것이다.  ✅ **2026-09-01 실기 종결** -- 두 FW(1252·1261) 15/15
    #: 반영, 대가 0(20초 잠금도 감속 0), `nolock` 덮임 2/2 로 **지킬 구간 실재**.
    #: `true` 확정 (DevNote 10.6).  끄면 labtest 와 같아지고, 그래도
    #: fetch 앞의 프레임 번호 대조는 남는다(조용히 틀린 파일은 안 나온다).
    #: ⚠️ **science 는 버퍼가 둘뿐**이라 하나를 잠그면 엔진에 하나만 남는다
    #: (guide 는 셋) -- ✅ 남는 버퍼가 없으면 엔진은 **쓰던 버퍼를 재사용**하며
    #: 만속을 유지한다 (2026-09-01 실측, DevNote 10.4).  ⚠️ 그래서 잠금은
    #: 프레임 주기(13.27초) 안에 풀어야 한다 -- 넘으면 다음 장이 덮인다.
    lock_buffer: bool = True
    #: fetch **뒤에** 버퍼가 덮이지 않았는지 한 번 더 대조할지.
    #:
    #: fetch 앞의 대조는 **직전 한 순간**만 본다.  fetch 자체가 수 초 걸리므로
    #: (실측 3.2~3.5초, 2026-09-01) **그 사이에 덮이는 창**은 앞 대조가 못 본다
    #: -- 주기 13.27초에 경계가 걸릴 확률 ≈26% 다 (DevNote 10.6).
    #: ⭐ **`lock_buffer = false` 인 경우 필요할 수 있다** -- `LOCKn` 을 끄면
    #: 그 창을 막는 것이 아무것도 없어서, 덮여도 조용히 두 노출이 섞인 raw 가
    #: 나온다(헤더는 이 프레임의 것이라 나중에 봐도 못 가른다).  이 재대조가
    #: 그 짝이다.
    #:
    #: 기본을 `true` 로 둔 근거는 **값이 거의 안 든다**는 것이다 -- 3~4초짜리
    #: fetch 뒤에 `FRAME` 왕복 하나(밀리초)를 더 하는 것뿐이고, `lock_buffer`
    #: 가 켜져 있으면 절대 걸리지 않는다(잠긴 버퍼는 안 바뀐다).  그리고
    #: **LOCKn A/B 실험(2026-09-01 종결)을 뜻있게 만들었다**: `lock_buffer=false` 쪽이
    #: 조용히 틀린 파일을 쓰는 대신 **덮였다고 크게 운다** -- 실험이 재기 위한
    #: 바로 그 사실이다.
    #: ⚠️ 반대 논거도 적어 둔다 -- 걸리면 이미 받아 온 자료를 버리므로 fetch
    #: 시간(약 3.4초)이 헛일이 된다.  그래도 대안은 **두 노출이 섞인 한 장을
    #: 경고 없이 쓰는 것**이라 버리는 쪽이 맞다.
    recheck_after_fetch: bool = True
    #: FRAME 폴링 간격 [s].  labtest 는 0.5/0.65 를 썼다.
    frame_poll: float = 0.5
    #: 프레임 대기 중 **진단 덤프**를 몇 초마다 찍을지.  `0` 이면 끈다(기본).
    #:
    #: labtest `FRAME_DUMP_ENABLE` 의 자리다 (v1.3.4, 2026-08-27).  취득이 안
    #: 끝날 때 "노출이 안 걸렸나 / 독출이 안 끝나나" 를 가르는 계측이고,
    #: **정상 취득이 도는 동안은 꺼 둔다** -- 한 번에 왕복이 셋(FRAME·STATUS·
    #: TIMER) 늘어난다.
    #:
    #: ⚠️ **시한 초과 때의 진단 한 장은 이 값과 무관하게 항상 남는다** --
    #: 그 증상은 간헐이라(가동 시간이 길어지면 재발했다) 평소 덤프를 꺼 두면
    #: 정작 재발했을 때 증거가 없다.
    frame_dump: float = 0.0
    #: 노출 지시부터 프레임 완료까지의 상한 [s].  0 이면 무한 대기.
    #:
    #: **없으면 조용히 멈춘다.**  labtest 는 `while True` 로 프레임 번호가
    #: 바뀔 때까지 돌았고 사람이 화면을 보고 있었다.  본편은 OBSAgent 가
    #: 상대이므로, 독출이 시작되지 않으면(ACF 가 틀림 · 클록이 안 감 ·
    #: `LOADPARAMS` 가 먹히지 않음) `EXPSTATUS=READOUT` 에 갇혀 관측자
    #: 화면이 멈추고 `force_idle` 타임아웃으로 `opause` 에 빠진다.
    #: 상한을 넘기면 레거시와 같은 오류 경로를 탄다 -- `DMA WAIT TIMEOUT.
    #: EXPOSURES ABORTED.` (base.py `BackendError` docstring).
    #: 기본 300초는 실측 독출 12.77초 · 프레임 주기 13.27초(2026-09-01, DevNote
    #: 10.4)의 20배가 넘는다 -- 조일 대상이다 (예 60초).  ⚠️ `fetch_timeout` 과는
    #: 별개 상한이다.
    frame_timeout: float = 300.0
    #: `FETCH` 한 프레임의 상한 [s].  ⚠️ **`lock_buffer=true` 에서는 잠금 상한이기도
    #: 하다** -- 이 시간 동안 `LOCKn` 을 쥐고, 잠금 중 엔진은 버퍼 하나로 돌며
    #: 프레임 주기(`MIN_FRAME_PERIOD` 13.27초)를 넘으면 다음 장이 앞 장을 덮는다
    #: (2026-09-01 `--hold 20` 실측, DevNote 10.4·10.6).  그래서 **주기 아래**여야
    #: 하고 `validate()` 가 본다.  실측 FETCH 는 99~107 MiB/s (344 MiB 에 3.2~3.5초,
    #: 두 유닛) -- 기본 10초면 2.9배 여유다.
    #:
    #: **0 이면 크기에서 유도한다** (1 MiB/s 가정 · 최소 60초 -- 344 MiB 면 344초).
    #: 종전 기본값이 0 이었는데, 그 유도값은 주기의 26배라 링크가 느려지면 잠금을
    #: 쥔 채 26장을 잃게 한다 -- 기본을 10 으로 옮겼다 (2026-09-02).
    #:
    #: ⚠️ `frame_timeout` 과 **별개의 상한**이다.  독출(트리거→프레임 완료)을
    #: 조여 놔도 전송은 이 값이 따로 잡는다.
    fetch_timeout: float = 10.0
    #: **호스트 수신·저장 버퍼 수 (컨트롤러당).**  FETCH 가 여기서 하나를 빌려
    #: 채우고, 저장이 끝나면 돌려준다.
    #:
    #: **왜 상한을 두나** -- 종전에는 프레임마다 344 MiB 를 새로 잡았고 저장
    #: 태스크 수에 제한이 없어서, 저장이 밀리면 **메모리가 조용히 늘었다.**
    #: 링으로 두면 상한이 `N x 344 MiB` 로 고정되고, 다 차면 FETCH 가 기다려
    #: **그 사실이 로그에 드러난다**(조용한 증가 대신 신호).
    #:
    #: ⚠️ **`wrote_window` 와 짝이다** -- 창이 넓을수록 더 많은 프레임이
    #: 동시에 살아 있다.  `N >= ceil((창 - write_delay) / 주기)` 여야 하고,
    #: `_cross_checks()` 가 기동에서 본다.  실측(2026-09-01, 주기 13.27초) 기준
    #: 25초 창에는 **2개**면 충분하다 -- 그때 "창이 터진 뒤에도 자료가 남는"
    #: 구간이 약 4.9초다 (N x 13.27 - 25 + 3.4).
    fetch_buffers: int = 2
    #: OBSAgent 의 `force_fitssaved` 창 [s] -- **우리 쪽 선언값**이다
    #: (`IDLE` 진입 -> 4번째 `Wrote`, DevNote 3.2).  넘기면 OBSAgent 가
    #: `FitsSaved` 를 강제하고 `ExpStatus=ERROR` 를 낸다.
    #:
    #: 여기 적는 이유는 **`fetch_buffers` 와 함께 움직이는 값**이기 때문이다 --
    #: 한쪽만 바꾸면 짝이 조용히 끊긴다.
    wrote_window: float = 25.0
    #: 종료할 때 **저장 중인 프레임**을 기다리는 상한 [s].  0 이면 안 기다린다.
    #:
    #: 저장은 `write_delay` 뒤에 백그라운드로 도는 일이라, 그 사이에 종료가
    #: 들어오면 **컨트롤러에서 다 읽어낸 프레임이 파일 없이 사라진다** --
    #: 취득 한 장은 다시 못 찍는다.  전원 차단(`POWEROFF`)보다 먼저 이것을
    #: 기다린다.
    shutdown_drain: float = 30.0
    #: 진행률을 몇 % 이상 올랐을 때 보고할지.  0 이면 폴링마다 보고한다.
    #: 레거시는 6/17/28/... 로 듬성듬성 보냈고 촘촘해도 OBSAgent 는 문제없다
    #: (DevNote 3.2) -- 다만 와이어 소음을 줄이려고 문턱을 둔다.
    progress_step: int = 5

    # -- 기하 ------------------------------------------------------------
    #: 헤더가 **선언하는** 프레임 크기.  fetch 한 바이트 수와 대조하는 기준이
    #: 므로 리터럴로 흩어 두지 않는다 (labtest v1.1.1 회귀 3번).  기본은
    #: raw spec 3장의 science pair 값이고, 시험은 이것을 줄여서 쓴다.
    naxis1: int = rawhdr.RAW_NAXIS1
    naxis2: int = rawhdr.RAW_NAXIS2
    #: FETCH 블록 크기 [B].  Archon 프로토콜 고정값 1024 (매뉴얼 p.51).
    burst_len: int = 1024

    #: 이미 경고한 태그 -- `active_tags()` 를 여러 곳에서 부르므로 같은 경고를
    #: 되풀이하지 않는다.  경고가 반복되면 사람이 그것을 무시하게 된다.
    _warned: set = field(default_factory=set, repr=False, compare=False)

    # -- 유도값 ----------------------------------------------------------

    @property
    def frame_bytes(self) -> int:
        """선언 기하의 데이터부 크기 (`BITPIX=16`)."""
        return self.naxis1 * self.naxis2 * 2

    def active_tags(self, ccds: tuple[str, ...]) -> tuple[str, ...]:
        """설정에 살아 있는 컨트롤러 태그.

        **`[node] ccds` 가 정한다** -- 컨트롤러 목록을 따로 두면 두 설정이
        어긋날 수 있고, 그 어긋남은 "파일이 한 쪽만 나온다" 로만 보인다.
        `[archon]` 에 주소가 없는 태그는 경고와 함께 뺀다.
        """
        out = []
        allowed = (self.solo_tag,) if self.n_controllers == 1 else CTRLTAGS
        for tag, chips in rawpair.CONTROLLERS:
            if tag not in allowed:
                continue                      # [archon] n_controllers 가 뺐다
            if not any(c in ccds for c in chips):
                continue
            if not self.hosts.get(tag):
                if tag not in self._warned:
                    self._warned.add(tag)
                    log.warning('[archon] ctrl_%s_host 가 비어 있는데 [node] '
                                'ccds 에 %s 가 있다 -- 이 컨트롤러는 건너뛴다 '
                                '(그 파일은 생기지 않는다)',
                                tag.lower(), '/'.join(chips))
                continue
            out.append(tag)
        return tuple(out)

    def index_of(self, ctrltag: str) -> int:
        """`Cn_*`/`CTRLn*` 의 색인 (1 = MK, 2 = NT).

        **"내 컨트롤러" 가 아니라 고정 색인이다** -- raw spec 5.9절이 두 파일에
        같은 값을 요구하므로, NT 의 값을 `C1_*` 에 넣으면 pair 두 파일이 같은
        자리에 서로 다른 컨트롤러를 싣는다 (labtest v1.1 이 고친 결함).
        """
        return CTRLTAGS.index(ctrltag) + 1

    def drives_shutter(self, ctrltag: str) -> bool:
        return self.shutter_ctrl == 'BOTH' or self.shutter_ctrl == ctrltag


def _head(sec, key: str, default: str) -> str:
    """값의 첫 토큰.  `10.0.0.113 (KMTK-SCI-113)` 처럼 뒤에 붙은 설명을 떼어낸다.

    `ics_sim` 의 `[auxcontrol]` 과 같은 관례다 -- 현장 ini 를 그대로 복사해
    넣어도 되게 한다.
    """
    raw = sec.get(key)
    if raw is None:
        return default
    tokens = raw.split()
    return tokens[0] if tokens else default


def _text(sec, key: str, default: str) -> str:
    """공백이 값의 일부일 수 있는 항목 (경로 등).  **`~` 를 펼친다.**

    ACF 경로는 관례상 상대경로(`acf/...`)지만 운영자가 `~/AIC/acf/...` 로 적을
    수 있다.  펼치지 않으면 `~` 라는 이름의 폴더를 찾아 "없다" 고 멈춘다 --
    메시지에 절대경로와 cwd 를 함께 찍으므로 진단은 되지만, 애초에 될 일이다.
    """
    raw = sec.get(key)
    if raw is None:
        return default
    raw = raw.strip()
    return os.path.expanduser(raw) if raw else raw


def _num(sec, key: str, default, cast):  # noqa: ANN001, ANN201
    raw = _head(sec, key, '')
    if not raw:
        return default
    try:
        return cast(raw)
    except ValueError:
        raise ArchonConfigError(
            '[archon] %s 를 숫자로 읽을 수 없다: %r' % (key, raw)) from None


def _bool(sec, key: str, default: bool) -> bool:
    raw = _head(sec, key, '').lower()
    if not raw:
        return default
    if raw in ('true', 'yes', 'on', '1'):
        return True
    if raw in ('false', 'no', 'off', '0'):
        return False
    raise ArchonConfigError(
        '[archon] %s 는 true/false 여야 한다: %r' % (key, raw))


def _solo_tag(cp: configparser.ConfigParser, n_controllers: int) -> str:
    """1대 운영일 때 어느 컨트롤러인지 (`MK`/`NT`).  2대면 빈 문자열.

    **`[controllers] ctrl1_id`/`ctrl2_id` 의 선언 여부가 정한다** (운영자 지시
    2026-08-24) -- 색인 1 이 `MK`, 2 가 `NT` 다 (`rawpair.CONTROLLERS` 순서).

    "없음" 은 **비워 두거나 `NC`** 다 (운영자 확정 2026-08-25) -- `NC` 는
    헤더에 실릴 규격 5.0절 sentinel 과 같은 낱말이다.  그래서 1대 운영을 두
    방식으로 적을 수 있다:

        ctrl1_id = KMTA-SCI-103      # 한쪽만 적는다 (키를 지워도 된다)
        ctrl2_id =

        ctrl1_id = KMTA-SCI-103      # 둘 다 적고 한쪽을 NC 로 둔다
        ctrl2_id = NC

    ⚠️ **이름 문자열은 읽지 않는다.**  색인 1 은 언제나 `MK`, 2 는 언제나
    `NT` 다 -- 이름 끝 번호(101/102/103/104…)는 유닛마다 다르고 색인과 아무
    관계가 없다.  정본은 배선(`ctrl_mk_host`/`ctrl_nt_host`)이다.

    Raises:
        ArchonConfigError: 1대인데 둘 다 선언됐을 때.  어느 쪽인지 정할 수
            없는 상태로 진행하면 **엉뚱한 chip 이름으로 자료가 저장된다.**
    """
    if n_controllers != 1:
        return ''
    sec = cp['controllers'] if cp.has_section('controllers') else {}

    def declared(n: int) -> bool:
        # 표기 판정은 `ControllersCfg` 가 정본이다 -- 두 자리가 갈리면 "ini 에
        # 적었는데 헤더와 대수 판정이 서로 다르게 읽는" 상태가 된다.
        raw = str(sec.get('ctrl%d_id' % n, '') or '').split('#')[0]
        return not ControllersCfg.is_absent(raw)

    one, two = declared(1), declared(2)
    if one and two:
        raise ArchonConfigError(
            '[archon] n_controllers=1 인데 [controllers] 에 ctrl1_id 와 '
            'ctrl2_id 가 **둘 다** 선언돼 있다 -- 어느 컨트롤러를 쓸지 정할 수 '
            '없다.  쓰지 않는 쪽을 비우거나 NC 로 둘 것')
    if two:
        return CTRLTAGS[1]
    if not one:
        log.warning('[archon] n_controllers=1 인데 [controllers] 에 ctrl1_id 도 '
                    'ctrl2_id 도 선언돼 있지 않다 -- %s 로 본다.  의도한 쪽의 '
                    'ctrl<n>_id 를 채워 명시할 것', CTRLTAGS[0])
    return CTRLTAGS[0]


def _rail_limits(cp: configparser.ConfigParser) -> dict | None:
    """`[archon.rails]` -> `{레일: (하한, 상한)}`.  절이 없으면 `None`(기본값).

    형식은 `p2v5 = 2.1, 2.9` 다 (레일 이름은 대소문자를 안 가린다).  **기본값은
    매뉴얼 p.41 이고 `archon.parse.RAIL_LIMITS` 가 정본**이다 -- 여기서는 그것을
    통째로 대체하지 않고 **적힌 레일만 덮는다**: 한 레일을 조정하려다 나머지
    여섯의 판정이 통째로 사라지면 그것이 조용한 감시 구멍이 된다.

    ⚠️ 이 값은 전원 보드의 저항으로 정해지므로(p.42) 유닛마다 다를 수 있다.
    그리고 **비대칭이다** -- `-6.6, -5.3` 처럼 작은 쪽을 앞에 적는다(순서가
    뒤집혀 있으면 바로잡고 알린다).
    """
    if not cp.has_section('archon.rails'):
        return None
    # **지연 import** -- 모듈 최상단에서 `archon` 을 끌어오면 `archon/__init__`
    # -> `backend` -> `config` 로 순환한다.
    from .archon import parse as _parse

    out = dict(_parse.RAIL_LIMITS)
    for key, raw in cp.items('archon.rails'):
        rail = key.strip().upper()
        parts = [p.strip() for p in str(raw).split(',')]
        if len(parts) != 2:
            raise ArchonConfigError(
                "[archon.rails] %s 는 '하한, 상한' 두 값이어야 한다: %r"
                % (key, raw))
        try:
            lo, hi = float(parts[0]), float(parts[1])
        except ValueError:
            raise ArchonConfigError(
                '[archon.rails] %s 의 값이 수치가 아니다: %r' % (key, raw)
            ) from None
        if lo > hi:
            log.warning('[archon.rails] %s 의 하한·상한이 뒤집혀 있다 (%g, %g) '
                        '-- 바로잡아 쓴다.  음전압 레일은 -6.6, -5.3 처럼 작은 '
                        '쪽을 앞에 적는다', key, lo, hi)
            lo, hi = hi, lo
        if rail not in out:
            log.warning('[archon.rails] %r 는 규격 5.6.1절 레일 목록에 없다 '
                        '(%s) -- 판정에 쓰이지 않는다',
                        key, ' '.join(_parse.VOLT_RAILS))
        out[rail] = (lo, hi)
    return out


def load(path: str) -> ArchonCfg:
    """ini 에서 `[archon]` 절을 읽는다.  절이 없으면 기본값."""
    cfg = ArchonCfg()
    cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    if not cp.read(path, encoding='utf-8'):
        log.warning('설정 파일을 읽지 못했다 (%s) -- [archon] 기본값을 쓴다',
                    path)
        return cfg
    if not cp.has_section('archon'):
        log.warning('%s 에 [archon] 절이 없다 -- 기본값을 쓴다.  컨트롤러 '
                    '주소가 비어 있으면 첫 노출에서 실패한다', path)
        return cfg
    s = cp['archon']

    for tag in CTRLTAGS:
        host = _head(s, 'ctrl_%s_host' % tag.lower(), '')
        if host:
            cfg.hosts[tag] = host
        acf = _text(s, 'acf_%s' % tag.lower(), '')
        if acf:
            cfg.acf[tag] = acf

    cfg.port = _num(s, 'port', cfg.port, int)
    cfg.sock_timeout = _num(s, 'sock_timeout', cfg.sock_timeout, float)
    cfg.connect_retry = _num(s, 'connect_retry', cfg.connect_retry, int)

    cfg.apply_acf = _bool(s, 'apply_acf', cfg.apply_acf)
    cfg.acf_retry = _num(s, 'acf_retry', cfg.acf_retry, int)
    cfg.poweron_wait = _num(s, 'poweron_wait', cfg.poweron_wait, float)

    cfg.param_intms_slot = _head(s, 'param_intms_slot', cfg.param_intms_slot)
    cfg.param_intms_name = _head(s, 'param_intms_name', cfg.param_intms_name)
    cfg.param_exposures_slot = _head(s, 'param_exposures_slot',
                                     cfg.param_exposures_slot)
    cfg.param_exposures_name = _head(s, 'param_exposures_name',
                                     cfg.param_exposures_name)

    cfg.telemetry = _bool(s, 'telemetry', cfg.telemetry)
    cfg.status_timeout = _num(s, 'status_timeout', cfg.status_timeout, float)

    cfg.monitor = _bool(s, 'monitor', cfg.monitor)
    cfg.monitor_interval = _num(s, 'monitor_interval', cfg.monitor_interval,
                                float)
    # **`~` 를 펼친다.**  안 펼치면 `os.makedirs` 가 작업 디렉터리 아래에 `~`
    # 라는 폴더를 아무 불평 없이 만들고, 오류가 없으므로 기록이 엉뚱한 곳에
    # 쌓이는 것이 드러나지 않는다 (`ics_sim config.py` 의 2026-08-23 실측).
    raw_log = _text(s, 'monitor_log', cfg.monitor_log)
    cfg.monitor_log = os.path.expanduser(raw_log) if raw_log else ''
    raw_hk = _text(s, 'hk_latest', cfg.hk_latest)
    cfg.hk_latest = os.path.expanduser(raw_hk) if raw_hk else ''
    cfg.hk_stale_after = _num(s, 'hk_stale_after', cfg.hk_stale_after, float)
    cfg.rail_limits = _rail_limits(cp)

    cfg.shutter_ctrl = _head(s, 'shutter_ctrl', cfg.shutter_ctrl).upper()
    if cfg.shutter_ctrl not in CTRLTAGS + ('BOTH',):
        raise ArchonConfigError(
            '[archon] shutter_ctrl 은 %s 중 하나여야 한다: %r'
            % (' / '.join(CTRLTAGS + ('both',)), cfg.shutter_ctrl))
    cfg.full_flush_on_erase = _bool(s, 'full_flush_on_erase',
                                    cfg.full_flush_on_erase)
    cfg.lock_buffer = _bool(s, 'lock_buffer', cfg.lock_buffer)
    cfg.recheck_after_fetch = _bool(s, 'recheck_after_fetch',
                                    cfg.recheck_after_fetch)
    cfg.frame_poll = _num(s, 'frame_poll', cfg.frame_poll, float)
    cfg.frame_dump = _num(s, 'frame_dump', cfg.frame_dump, float)
    cfg.frame_timeout = _num(s, 'frame_timeout', cfg.frame_timeout, float)
    cfg.shutdown_drain = _num(s, 'shutdown_drain', cfg.shutdown_drain,
                              float)
    cfg.fetch_timeout = _num(s, 'fetch_timeout', cfg.fetch_timeout, float)
    cfg.fetch_buffers = max(1, _num(s, 'fetch_buffers', cfg.fetch_buffers, int))
    cfg.wrote_window = _num(s, 'wrote_window', cfg.wrote_window, float)
    cfg.progress_step = _num(s, 'progress_step', cfg.progress_step, int)

    # **컨트롤러 대수** -- 1 또는 2 만 받는다 (운영자 지시 2026-08-24).
    cfg.n_controllers = _num(s, 'n_controllers', cfg.n_controllers, int)
    if cfg.n_controllers not in (1, 2):
        raise ArchonConfigError(
            '[archon] n_controllers 는 1 또는 2 여야 한다 (받은 값: %r).  '
            '카메라는 컨트롤러 2대 구성이고, 1 은 실험실 단독 취득용이다'
            % (cfg.n_controllers,))
    cfg.solo_tag = _solo_tag(cp, cfg.n_controllers)

    cfg.naxis1 = _num(s, 'naxis1', cfg.naxis1, int)
    cfg.naxis2 = _num(s, 'naxis2', cfg.naxis2, int)
    cfg.burst_len = _num(s, 'burst_len', cfg.burst_len, int)
    return cfg


def backend_declared(path: str) -> bool:
    """ini 가 `[hardware] backend` 를 **적어 놓았나**.

    `ics_sim.config` 는 기본값 `sim` 을 채워 주므로 "적지 않았다" 와 "sim 이라고
    적었다" 가 구별되지 않는다.  `ics_archon` 은 그 둘을 갈라야 한다 -- 안
    적었으면 실기가 기본이고, `sim` 이라고 적었으면 그 뜻을 존중한다.
    """
    cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    if not cp.read(path, encoding='utf-8'):
        return False
    return cp.has_option('hardware', 'backend')


def validate(cfg: ArchonCfg, ccds: tuple[str, ...],
             sim_cfg=None) -> list[str]:  # noqa: ANN001
    """기동 시 경고 목록.  `ics_sim.config.validate()` 와 같은 자리다."""
    notes: list[str] = []
    tags = cfg.active_tags(ccds)
    if not tags:
        notes.append('살아 있는 컨트롤러가 없다 -- [archon] ctrl_*_host 와 '
                     '[node] ccds 를 확인하라.  이 상태로는 노출이 실패한다')
    for tag in tags:
        if cfg.apply_acf and not cfg.acf.get(tag):
            notes.append('[archon] acf_%s 가 비어 있는데 apply_acf=true 다 -- '
                         'ACF 적용을 건너뛴다' % tag.lower())
    if (cfg.naxis1, cfg.naxis2) != (rawhdr.RAW_NAXIS1, rawhdr.RAW_NAXIS2):
        notes.append(
            '선언 기하가 raw spec 값과 다르다 (%dx%d != %dx%d) -- 시험용 '
            '설정이라면 정상이고, 실기라면 converter 가 거부한다'
            % (cfg.naxis1, cfg.naxis2, rawhdr.RAW_NAXIS1, rawhdr.RAW_NAXIS2))
    if cfg.burst_len != 1024:
        notes.append('[archon] burst_len 이 1024 가 아니다 -- Archon 의 이진 '
                     '응답 블록은 1024B 고정이다 (매뉴얼 p.51)')
    if cfg.frame_timeout <= 0:
        notes.append('[archon] frame_timeout <= 0 -- 프레임이 안 나오면 영구히 '
                     '기다린다.  EXPSTATUS=READOUT 에 갇혀 OBSAgent 가 opause '
                     '로 간다')
    # **대수와 CCD 목록이 어긋나면 통보와 산출물이 갈린다.**  1대인데 `ccds` 가
    # 네 개면 시퀀서는 CCD 4개분 `Acquisition Complete.`/`Wrote` 를 내보내는데
    # 파일은 한 컨트롤러분(2 chip)만 나온다 -- OBSAgent 는 4개를 다 받았으니
    # 정상으로 보고, 없어진 파일은 아무도 알려주지 않는다.
    if cfg.n_controllers == 1:
        missing = [c for tag, chips in rawpair.CONTROLLERS if tag != cfg.solo_tag
                   for c in chips if c in ccds]
        if missing:
            notes.append(
                '[archon] n_controllers=1 (%s) 인데 [node] ic_ids 에 %s 가 '
                '남아 있다 -- 그 chip 의 파일은 생기지 않는데 통보는 나간다.  '
                'ic_ids/cb_ids 를 %s 쪽 2개로 줄일 것'
                % (cfg.solo_tag, '/'.join(missing), cfg.solo_tag))
    if not cfg.telemetry:
        notes.append('[archon] telemetry=false -- Cn_TEMP/VOLT/CURR 가 NC 로 '
                     '실린다 (왕복은 labtest v1.0 계보와 같아진다)')
    # **두 상한이 서로 다른 것을 잰다는 사실을 t=0 에 보여 준다.**  독출을
    # 조여 놓고 전송이 그보다 오래 걸리는 조합은 한쪽만 보면 정상이다 (F5).
    fetch_cap = cfg.fetch_timeout or max(
        60.0, cfg.frame_bytes / (1 << 20) * 1.0)
    if cfg.frame_timeout > 0 and fetch_cap > cfg.frame_timeout:
        notes.append(
            '[archon] FETCH 상한(%.0f초)이 frame_timeout(%.0f초)보다 길다 -- '
            '둘은 다른 국면을 재므로 잘못은 아니지만, 링크가 느려지면 독출 '
            '상한을 조여 놔도 전송에서 그만큼 매달린다.  실측은 99~107 MiB/s '
            '(344 MiB 에 3.2~3.5초, DevNote 10.4) -- fetch_timeout 을 그 기준으로 '
            '적을 것' % (fetch_cap, cfg.frame_timeout))
    # ⭐ **잠금은 주기보다 짧아야 한다** (DevNote 10.6, 2026-09-01 실측).  `LOCKn`
    # 을 쥔 채 프레임 경계를 넘으면 엔진은 남는 버퍼가 없어 **쓰던 버퍼를
    # 재사용**해 다음 장을 덮는다.  FETCH 상한이 곧 잠금 상한이므로 주기
    # (`MIN_FRAME_PERIOD`) 아래여야 한다 -- 실측 FETCH 3.2~3.5초(99~107 MiB/s)
    # 라 10초면 2.9배 여유다.  `fetch_timeout=0`(크기 유도, 344초)이면 걸린다.
    if cfg.lock_buffer and fetch_cap >= MIN_FRAME_PERIOD:
        notes.append(
            '[archon] FETCH 상한(%.0f초)이 프레임 주기(%.2f초) 이상이다 -- '
            'lock_buffer=true 에서 잠금이 주기를 넘으면 엔진이 쓰던 버퍼를 '
            '재사용해 **다음 장이 덮인다** (DevNote 10.6).  fetch_timeout 을 '
            '주기 아래(예 10)로 적을 것' % (fetch_cap, MIN_FRAME_PERIOD))
    notes += _cross_checks(cfg, sim_cfg)
    notes += _storage_checks(cfg, sim_cfg)
    notes += _ascii_checks(sim_cfg)
    return notes


#: 헤더에 그대로 실리는 **손편집 ini 값**들 -- `(절, 필드)`.
#:
#: labtest 는 이 값들을 기동에서 검사한다(`_check_identity_setup()`).  여기서도
#: 같은 자리를 본다 -- 목록을 코드로 못박아 두면 `[site]`/`[camera]` 에 카드가
#: 늘 때 이 검사가 따라가지 않는 것이 드러난다.
#:
#: ⚠️ **`ctrl1_cfg`/`ctrl2_cfg` 만은 손편집이 아닐 수 있다** -- 비어 있으면
#: `IcsArchon.__init__()` 이 `[archon] acf_mk`/`acf_nt` 에서 파생해 채운다.
#: 그래도 **목록에 남겨 둔다**: 파생이 `__init__`, 이 검사가 `start()` 라
#: 여기서 보는 것은 이미 파생된 값이고, 그래야 **ACF 경로에 섞인 비ASCII 도**
#: 걸린다.  뺐다면 파생된 값만 검사를 빠져나간다.
_HEADER_INI_FIELDS = (
    ('controllers', ('ctrl1_id', 'ctrl1_sn', 'ctrl1_cfg',
                     'ctrl2_id', 'ctrl2_sn', 'ctrl2_cfg', 'rdmode')),
    ('camera', ('detector', 'camver', 'instrume', 'fpaid')),
    ('site_override', ('telescop', 'origin', 'latitude', 'longitud')),
)


def _ascii_checks(sim_cfg) -> list[str]:  # noqa: ANN001
    """헤더에 실릴 ini 값에 **비ASCII 가 섞였나** (labtest 3중 방어의 첫째).

    **FITS 헤더는 ASCII 전용이다** (raw spec 5.0절).  한글 한 자가 섞이면
    `fitswrite.card_image()` 가 `?` 로 바꿔 파일은 온전하지만 **값은 잃는다** --
    그리고 그 경고는 카드마다·프레임마다 뜨므로, 밤새 돌리고 나서야 헤더가
    `????` 로 찬 것을 보게 된다.  labtest 는 같은 이유로 **기동에서** 검사한다.

    ⚠️ **기동을 막지는 않는다.**  labtest 는 거부하지만 그쪽은 사람이 붙어 있는
    실험실 스크립트이고, 여기는 OBSAgent 가 상대인 상주 프로그램이다 -- 카드
    한 장 때문에 관측을 통째로 못 하게 만드는 쪽이 더 나쁘다.  대신 기동 배너
    옆에 크게 남는다.

    바이트 정렬은 `fitswrite` 가 따로 지킨다(문자 수가 아니라 **바이트 수**로
    단정한다) -- 그것이 labtest 3중 방어의 둘째·셋째다.
    """
    notes: list[str] = []
    if sim_cfg is None:
        return notes
    bad: list[str] = []

    def _scan(label: str, block, fields) -> None:  # noqa: ANN001
        if block is None:
            return
        for field_name in fields:
            value = getattr(block, field_name, '')
            if isinstance(value, str) and value and not value.isascii():
                bad.append('[%s] %s=%r' % (label, field_name, value))

    for section, fields in _HEADER_INI_FIELDS:
        _scan(section.replace('_override', ''),
              getattr(sim_cfg, section, None), fields)
    # **사이트별 표도 본다** -- 실제로 쓰이는 것은 `[site.<코드>]` 쪽이고,
    # `[site]` 덮어쓰기만 검사하면 현장 값이 통째로 빠진다.
    site_fields = dict(_HEADER_INI_FIELDS)['site_override']
    for code, block in sorted(getattr(sim_cfg, 'site_table', {}).items()):
        _scan('site.%s' % str(code).lower(), block, site_fields)
    if bad:
        notes.append(
            '헤더에 실릴 ini 값에 **비ASCII 문자**가 있다: %s -- FITS 헤더는 '
            'ASCII 전용이라(raw spec 5.0절) 그 자리가 `?` 로 바뀌어 실린다.  '
            '값은 잃고 파일은 온전하다.  ASCII 로 고칠 것' % ', '.join(bad))
    return notes


#: 노출 0초를 연속으로 찍을 때의 **최소 프레임 주기** [s].
#:
#: ⭐ 실측 2026-09-01 (두 유닛 101·113, `tools/ics_archon_buftest.py`):
#: **368 행/초** x 4700 행 = 독출 12.77초 + `NoIntMS` 0.5초 = **13.27초**
#: (`IntMS=0`) -- DevNote 10.4.  종전 12.0 은 운영자 labtest 자료(2026-08-29)의
#: "순수 readout 11.3초" 에서 왔다 (10.4 는 그 차이를 사강으로 본다).
#: `fetch_buffers` 가 `wrote_window` 에 견주어 충분한지 보는 데만 쓴다 --
#: 값이 조금 틀려도 경고 문턱이 움직일 뿐이다.
#:
#: ⚠️ **ACF(독출 속도)가 바뀌면 이 값도 바뀐다.**  guide 유닛은 프레임이
#: 훨씬 작아 주기도 짧다(R2610 기준 1.251초, `icg_archon/acftiming.py` 가 ACF 에서
#: 계산) -- 그때는 이 상수로 판단하지 말 것.
#:
#: ⭐ **잠금 상한의 기준**도 된다 -- `LOCKn` 을 쥔 채 프레임 경계를 넘으면 엔진이
#: 쓰던 버퍼를 재사용해 다음 장을 덮으므로(DevNote 10.6) `fetch_timeout` 이
#: 이보다 길면 기동 검사가 알린다.
MIN_FRAME_PERIOD = 13.27

#: 저장 자리 여유를 볼 때의 기준 -- **pair 몇 장분**인가.
#:
#: 절대값(GB)으로 두면 기하가 바뀔 때 뜻이 달라진다.  10장은 "밤새 돌릴 양" 이
#: 아니라 **"지금 당장 몇 장은 찍을 수 있다"** 의 문턱이다 -- 실기 pair 한 장이
#: 688 MiB(344 x 2)라 10장이면 약 6.7 GiB 다.
STORAGE_MIN_PAIRS = 10


def _storage_checks(cfg: ArchonCfg, sim_cfg) -> list[str]:  # noqa: ANN001
    """저장 자리를 **기동에서** 본다 (labtest v1.1.3 이 세운 규칙).

    **왜 기동인가** -- 저장 경로가 틀렸다는 것이 드러나는 자리가 종전에는
    `write_frame()` 이었고, 그 시점에는 이미 **fetch 를 마친 뒤**다.  즉 다
    읽어낸 노출을 잃는다.  labtest 는 이 검사를 `POWERON` 앞으로 올려서 같은
    문제를 닫았다(`createFolder` 가 `OSError` 를 삼켜 전원을 켠 채로 끝나던
    경로였다 -- README_labtest v1.1.3).

    **막지는 않는다.**  경고만 낸다 -- 관측소에서 마운트가 늦게 붙는 배치가
    실재하고, 여기서 기동을 거부하면 그 배치가 통째로 못 돌아간다.  대신
    기동 배너 옆에 크게 남아 자료 한 장 찍기 전에 사람 눈에 띈다.
    """
    notes: list[str] = []
    if sim_cfg is None:
        return notes
    path = os.path.expanduser(getattr(sim_cfg.paths, 'data_dir', '') or '')
    if not path:
        return notes

    if not os.path.isdir(path):
        # ⚠️ **없다고 만들지 않는다.**  가장 흔한 원인이 "마운트가 안 붙었다"
        # 인데, 그때 만들어 버리면 **마운트 지점을 가려** OS 디스크에 자료가
        # 쌓이기 시작한다 -- 그리고 나중에 마운트가 붙으면 그 자료가 통째로
        # 안 보이게 된다.
        notes.append(
            '[paths] data_dir 이 아직 없다 -- %r.  저장할 때 만들어지지만, '
            '외장을 쓸 작정이었으면 **마운트를 먼저 확인하라** (없는 채로 두면 '
            'OS 디스크에 쌓이고 나중에 마운트가 붙으면 그 자료가 가려진다)'
            % path)
        return notes

    if not os.access(path, os.W_OK):
        notes.append(
            '[paths] data_dir 에 쓸 수 없다 -- %r.  읽기전용으로 붙었거나 '
            '권한이 없다.  **이대로면 독출을 마친 프레임을 저장 단계에서 '
            '잃는다** (mount | grep 으로 확인)' % path)
        return notes

    try:
        free = shutil.disk_usage(path).free
    except OSError as exc:                          # pragma: no cover
        notes.append('[paths] data_dir 의 여유 용량을 못 읽었다 (%s) -- %r'
                     % (exc, path))
        return notes

    pair = cfg.frame_bytes * 2                      # 컨트롤러 2대 = 파일 2개
    if free < pair * STORAGE_MIN_PAIRS:
        notes.append(
            '[paths] data_dir 여유가 %.1f GiB 뿐이다 (%r) -- pair 한 장이 '
            '%.0f MiB 라 %d장도 안 들어간다.  **디스크가 차면 그 프레임은 '
            'fetch 를 마친 뒤에 사라진다**'
            % (free / (1 << 30), path, pair / (1 << 20), STORAGE_MIN_PAIRS))
    return notes


def _cross_checks(cfg: ArchonCfg, sim_cfg) -> list[str]:  # noqa: ANN001
    """`ics_sim` 쪽 설정과 맞물려서만 위험해지는 조합.

    **한쪽만 보면 둘 다 정상인 값들**이라 각자의 `validate()` 로는 안 걸린다.
    """
    notes: list[str] = []
    if sim_cfg is None:
        return notes

    # ⚠️ **듀어·환경 HK 의 원천이 실제로 있나** (2026-08-31 신설).
    #
    # 이 경로가 비었거나 틀리면 5.6절 HK 카드 **전부**가 sentinel 로 실린다.
    # 첫 프레임에 경고 한 줄이 나가긴 하지만 그 뒤로는 조용하므로, 자료를
    # 찍기 전에 기동에서 알린다 -- `icg_archon` 이 안 떠 있는 배치가 흔하다.
    hk_latest = getattr(cfg, 'hk_latest', '')
    if not hk_latest:
        notes.append(
            '[archon] hk_latest 가 비어 있다 -- CCDTEMP·DEWPRES 등 5.6절 HK '
            '카드가 전부 sentinel 로 실린다.  icg_archon 의 [hk] log_dir + '
            'latest_name 이 가리키는 파일 경로를 적을 것')
    else:
        path = os.path.expanduser(hk_latest)
        if not os.path.exists(path):
            notes.append(
                '[archon] hk_latest 파일이 없다 -- %r.  icg_archon 이 아직 안 '
                '떴거나 두 ini 의 경로가 어긋났다(icg [hk] log_dir/'
                'latest_name).  지금 상태로는 5.6절 HK 카드가 전부 sentinel '
                '이다' % path)
        else:
            try:
                import json as _json
                with open(path, encoding='utf-8') as _fh:
                    _age = time.time() - float(
                        _json.load(_fh).get('written', 0.0))
                if _age > max(cfg.hk_stale_after, 1.0):
                    notes.append(
                        '[archon] hk_latest 스냅샷이 %.0f초 묵었다 (한도 '
                        '%.0f초) -- icg_archon 이 돌고 있는지 확인할 것'
                        % (_age, cfg.hk_stale_after))
            except (OSError, ValueError, TypeError):
                notes.append('[archon] hk_latest 를 읽지 못했다 -- %r' % path)
    if cfg.hk_stale_after <= 0:
        raise ArchonConfigError(
            '[archon] hk_stale_after 는 0 보다 커야 한다 -- 0 이하면 모든 '
            'HK 표본이 낡은 것으로 버려진다')

    # ⚠️ **헤더가 주장하는 설정 파일과 실제로 올리는 파일이 갈릴 수 있다.**
    #
    # `CTRLnCFG` 는 비어 있을 때만 ACF 경로에서 파생된다 -- 손으로 적어 둔
    # 값이 있으면 그것이 이긴다(`[controllers]` 는 "채워져 있으면 INI 가
    # 이긴다" 가 원칙이고, 원장 `Source = ICS INI` 카드는 전부 ini 에서
    # 고칠 수 있어야 한다 -- 운영자 지시 2026-08-22).  그 대가로 **둘이
    # 어긋난 채 배포되는 경로**가 남으므로, 여기서 소리 내어 알린다.
    #
    # 이 어긋남은 자료를 봐도 드러나지 않는다 -- 이름이 그럴듯하면 아무도
    # 의심하지 않고, **그 사이트 자료만 영구히 다른 설정을 주장한다.**
    # 사이트 정체 배너와 같은 부류의 방어다.
    for tag in CTRLTAGS:
        n = cfg.index_of(tag)
        typed = str(getattr(sim_cfg.controllers, 'ctrl%d_cfg' % n, '')
                    or '').strip()
        derived = cfg_name_from_acf(cfg.acf.get(tag, ''))
        if (typed and derived and typed != derived
                and not ControllersCfg.is_absent(typed)):
            notes.append(
                '[controllers] ctrl%d_cfg=%r 가 [archon] acf_%s 에서 나오는 '
                '이름(%r)과 다르다 -- 손으로 적은 값이 이기므로 헤더 CTRL%dCFG '
                '는 %r 로 실리는데 컨트롤러에 올라가는 것은 %r 다.  비워 두면 '
                'ACF 경로에서 자동으로 채워진다'
                % (n, typed, tag.lower(), derived, n, typed,
                   os.path.basename(cfg.acf.get(tag, ''))))

    # ⚠️ **호스트 버퍼 수와 `Wrote` 창은 짝이다.**
    #
    # 저장이 밀리면 두 가지가 순서대로 일어난다 -- ① 창을 넘겨 OBSAgent 가
    # `ExpStatus=ERROR` 를 낸다(**경고**) ② 호스트 버퍼가 고갈돼 FETCH 가
    # 밀리고, 그러면 컨트롤러 버퍼가 덮여 **프레임을 잃는다.**
    #
    # ①이 ②보다 **먼저** 와야 한다 -- 그래야 "경고는 떴지만 자료는 남았다" 는
    # 구간이 생긴다.  그 조건이 `N x 주기 >= 창 - write_delay` 다.
    # 한쪽만 바꾸면 이 짝이 조용히 끊기므로 기동에서 본다.
    write_delay = float(getattr(sim_cfg.timing, 'write_delay', 0.0))
    need = int(math.ceil(
        max(0.0, cfg.wrote_window - write_delay) / MIN_FRAME_PERIOD))
    if cfg.fetch_buffers < need:
        notes.append(
            '[archon] fetch_buffers=%d 인데 wrote_window=%.1f초다 -- 창이 %.1f초를 '
            '넘으면 **버퍼가 창보다 먼저 무너져** 프레임을 잃는다(경고만 뜨고 '
            '자료는 남는 구간이 없어진다).  **%d 이상**이 필요하다 '
            '(N x %.1f초 >= 창 - write_delay %.1f초)'
            % (cfg.fetch_buffers, cfg.wrote_window,
               cfg.fetch_buffers * MIN_FRAME_PERIOD + write_delay,
               need, MIN_FRAME_PERIOD, write_delay))

    # ⚠️ **`lock_buffer` 와 `recheck_after_fetch` 는 짝이다.**
    #
    # fetch 하는 동안(실측 3.2~3.5초, 경계가 걸릴 확률 ≈26% -- DevNote 10.6) 버퍼가
    # 덮이는 창을 막는 것은 둘 중 하나다 --
    # `LOCKn`(막는다) 또는 fetch 뒤 재대조(막지는 못하고 **잡아서 버린다**).
    # **둘 다 끄면 그 창을 보는 것이 아무것도 없고**, 덮이면 두 노출이 섞인 raw
    # 한 장이 **아무 경고 없이** 나온다 -- 헤더는 이 프레임의 것이라 나중에
    # 자료를 봐도 못 가른다.  가장 나쁜 실패라 기동에서 알린다.
    if not cfg.lock_buffer and not cfg.recheck_after_fetch:
        notes.append(
            '[archon] lock_buffer=false 인데 recheck_after_fetch 도 false 다 -- '
            'fetch 하는 동안(약 3.4초) 버퍼가 덮여도 **아무도 못 본다**.  두 '
            '노출이 섞인 raw 가 경고 없이 나온다.  둘 중 하나는 켜라 '
            '(LOCKn 을 못 쓰는 상황이면 recheck_after_fetch = true)')

    # ⚠️ **`RDMODE` 유도가 현행 ACF 이름 규칙에서는 걸리지 않는다.**
    #
    # `rdmode_from_acf()` 는 이름에서 `fast`/`comp`/`slow` 토큰을 찾는데,
    # 그 규칙은 labtest 시절 이름(`KMTNet_Sci_fast_med_U13.acf`)에서 왔다.
    # **현행 정본 일곱은 전부 `<SITE>_<역할>_<유닛>_<시리얼>_<ACF판>[_<조>]`
    # 이라 속도 토큰이 없다** (`acf/README.md`) -- 그래서 ini 를 비워 두면
    # 유도가 늘 실패하고 코드 기본값 `NORMAL` 이 조용히 실린다.
    #
    # **조용한 것이 문제다.**  `NORMAL` 은 그럴듯한 값이라 헤더만 봐서는
    # "정말 NORMAL" 과 "못 알아봐서 NORMAL" 이 구별되지 않는다.  ⏳ 현행
    # ACF 의 실제 독출 모드가 무엇인지는 **운영자가 정할 사안**이므로 여기서
    # 값을 만들어 넣지 않고, 사실만 t=0 에 드러낸다.
    rdmode = str(getattr(sim_cfg.controllers, 'rdmode', '') or '').strip()
    tagged = [t for t in CTRLTAGS if cfg.acf.get(t)]
    if not rdmode and tagged:
        notes.append(
            '[controllers] rdmode 가 비었는데 ACF 이름(%s)에 속도 토큰'
            '(fast/comp/slow)이 없다 -- 유도가 실패해 코드 기본값 '
            "'NORMAL' 이 실린다.  현행 ACF 이름 규칙에는 그 토큰이 아예 "
            '없으므로(acf/README.md) 실제 독출 모드를 ini 에 **직접 적을 것** '
            "(2026-08-29 확정분 여섯은 전부 'NORMAL'.  09-03 반입분은 확인 대기)"
            % ' · '.join(os.path.basename(cfg.acf[t]) for t in tagged))

    # ⚠️ **반대 방향** -- ini 에 적어 둔 값이 ACF 이름과 어긋나는 경우.
    #
    # 위 경고가 시킨 대로 `rdmode = NORMAL` 을 적어 두면 그 줄은 **ACF 를
    # 바꿔도 따라오지 않는다.**  속도가 다른 ACF(`…_fast_…`)를 올린 뒤 이
    # 줄을 안 고치면 헤더가 `NORMAL` 이라고 **거짓말**을 하고, 자료만 봐서는
    # 드러나지 않는다 -- `CTRLnCFG` 어긋남과 정확히 같은 형태다.
    for tag in tagged:
        derived = rdmode_from_acf(cfg.acf[tag])
        if rdmode and derived and derived != rdmode.upper():
            notes.append(
                '[controllers] rdmode=%r 인데 [archon] acf_%s 의 이름은 %r 를 '
                '가리킨다(%s) -- ini 값이 이기므로 헤더 RDMODE 는 %r 로 실린다.  '
                'ACF 를 바꾸고 이 줄을 안 고쳤는지 확인할 것'
                % (rdmode, tag.lower(), derived,
                   os.path.basename(cfg.acf[tag]), rdmode))

    # ⚠️ **시간 축척은 하드웨어를 따라오지 않는다.**  적분 길이를 재는 것은
    # 컨트롤러(`IntMS`)이고 시퀀서의 카운트다운은 알림이다.  축척을 낮추면
    # 카운트다운이 먼저 끝나 `close_shutter()` 가 **적분 중에** 불리고, 그것이
    # 셔터를 강제로 닫아 **노출이 잘린다** -- 헤더 `EXPTIME` 은 요청값 그대로라
    # 정상으로 보이는 오염 프레임이 된다.  DevNote 9.2.3 에서 AUX 시뮬을 물릴
    # 때 같은 이유로 `time_scale = 1.0` 을 요구했다.
    scale = float(getattr(sim_cfg.timing, 'time_scale', 1.0))
    if abs(scale - 1.0) > 1e-9:
        notes.append(
            '[timing] time_scale=%g 인데 backend=archon 이다 -- 적분은 '
            '컨트롤러가 재므로 축척을 따라오지 않는다.  카운트다운이 먼저 끝나 '
            '셔터가 강제로 닫히고 노출이 잘린 채 EXPTIME 은 요청값으로 '
            '실린다.  실기는 1.0 이어야 한다' % scale)

    if getattr(getattr(sim_cfg, 'auxcontrol', None), 'enabled', False):
        notes.append('[auxcontrol] enabled=true 인데 backend=archon 이다 -- '
                     '셔터에 구동원이 둘 생긴다 (DevNote 9.2.2).  false 로 둘 것')

    if getattr(sim_cfg.behavior, 'inject', ()):
        notes.append('[behavior] inject 가 켜져 있다 -- 결함 주입은 시뮬 '
                     '백엔드에만 뜻이 있고, 남는 것(wrote_drop·tc_timeout)은 '
                     '실기 자료를 오염시킨다.  비워 둘 것')

    # ⚠️ **상대경로 `data_dir` 은 실행한 디렉터리 기준으로 풀린다.**  ini 위치도
    # 프로그램 위치도 아니다 -- systemd 의 `WorkingDirectory`, cron, 손으로 띄운
    # 셸이 각각 다른 곳을 가리키므로 **같은 설정이 실행마다 다른 곳에 자료를
    # 쌓는다.**  오류가 없으니 드러나지도 않는다(labtest 의 ACF 상대경로가 같은
    # 부류로 가장 많이 넘어졌다).  실기는 절대경로나 `~/...` 로 둘 것.
    import os as _os
    if not _os.path.isabs(_os.path.expanduser(sim_cfg.paths.data_dir)):
        notes.append(
            '[paths] data_dir=%r 가 상대경로다 -- **실행한 디렉터리 기준**으로 '
            '풀려 %r 가 된다.  띄우는 방법(systemd·cron·셸)이 바뀌면 자료가 '
            '조용히 다른 곳에 쌓인다.  실기는 절대경로나 ~/... 로 둘 것'
            % (sim_cfg.paths.data_dir, _os.path.abspath(sim_cfg.paths.data_dir)))

    # 실기에서 뜻이 없는 설정 -- 고쳐도 아무 일이 없다는 사실을 알린다.
    #
    # ⚠️ **기본값과 다를 때만** 센다.  "안 쓰인다" 를 늘 외치면 그것이 배경
    # 소음이 되고, 사람이 **실제로 고쳐 놓은 것**을 알리는 이 경고의 목적이
    # 사라진다.
    dead = []
    if sim_cfg.paths.write_fits:
        dead.append('[paths] write_fits(시뮬 전용)')
    if tuple(sim_cfg.paths.fits_shape) != (256, 256):
        dead.append('[paths] fits_shape(시뮬 전용)')
    # **archon 은 진행률을 컨트롤러의 `FRAME`(BUFnLINES / ACF LINECOUNT)에서 얻는다**
    # -- 시뮬의 계단 파라미터 셋은 아예 안 쓰인다 (`pctread_final` 만 쓴다).
    # 검토사항 A2 (2026-08-28 처리).
    readout = getattr(sim_cfg, 'readout', None)
    for key, default in (('pctread_start', 6), ('pctread_step', 11),
                         ('pctread_tick', 3.37)):
        got = getattr(readout, key, default)
        if got != default:
            dead.append('[readout] %s=%g(시뮬 전용 -- 진행률은 컨트롤러 '
                        'FRAME 에서 온다)' % (key, got))
    if dead:
        notes.append('archon 백엔드가 보지 않는 설정이 바뀌어 있다: %s -- '
                     '실기 산출물에는 영향이 없다' % ', '.join(dead))
    return notes

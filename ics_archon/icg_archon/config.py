#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`icg_archon.ini` 의 icg 전용 절 -- `[icg]` · `[hk]` · `[radionode]`.

`ics_sim` 쪽 절(`[node]`/`[site.*]`/`[timing]` 등)은 `ics_sim.config.load()`
가 같은 파일에서 따로 읽는다 (`ics_archon` 과 같은 2회 읽기 구조).

`IcgCfg` 는 `ics_archon.archon.controller.ArchonController` 가 기대하는
설정 속성(duck-type)을 **전부 실필드로** 갖는다 -- `hosts`/`acf` 는 guide
태그 `'G'` 하나짜리 표다.  science 의 `ArchonCfg`(MK/NT 2대 전제)를 재사용
하지 않는 이유: 태그·색인(1=MK/2=NT)·`solo_tag` 규칙이 전부 pair 전제라,
끼워 맞추면 로그·CSV 이름에 남의 태그가 박힌다.
"""

from __future__ import annotations

import configparser
import logging
import os
from dataclasses import dataclass, field

from . import gauge

log = logging.getLogger('icg_archon.config')

DEFAULT_INI = 'icg_archon.ini'

#: guide 컨트롤러 태그 -- 파일명 `<DETID>` 필드와 같은 글자다 (raw spec 9.2절).
TAG = 'G'

#: guide 프레임 기하 (raw spec 9.3절).  ACF `PIXELCOUNT=528 x 실탭 8` ·
#: `LINECOUNT=1033`.  science 처럼 ini 로 덮을 수 있게 두지 않는다 --
#: 기하가 바뀌면 규격(9장)과 견본부터 움직여야 한다 (4.3절 포장 규범).
NAXIS1 = 4224
NAXIS2 = 1033


class IcgConfigError(Exception):
    """기동을 멈춰야 하는 설정 오류."""


def _head(sec, key: str, default: str) -> str:  # noqa: ANN001
    """첫 토큰만 -- `10.0.0.16 (guide bench)` 같은 꼬리 주석을 허용한다."""
    raw = sec.get(key, default)
    parts = (raw or '').split()
    return parts[0] if parts else default


def _text(sec, key: str, default: str) -> str:  # noqa: ANN001
    return (sec.get(key, default) or '').strip()


#: ini 의 참/거짓 낱말.  ⭐ **`true`/`on`/`1` 과 `false`/`off`/`0` 을 같게**
#: 받는다 (운영자 확정 2026-09-04) -- 대소문자는 안 가린다.  `yes`/`no` 는
#: 종전부터 받던 것이라 남긴다.
_TRUE_WORDS = ('1', 'true', 'yes', 'on')
_FALSE_WORDS = ('0', 'false', 'no', 'off')


def _bool(sec, key: str, default: bool) -> bool:  # noqa: ANN001
    """⛔ **모르는 값을 조용히 거짓으로 떨어뜨리지 않는다.**

    ⚠️ 종전 구현은 어휘 밖을 전부 `False` 로 읽었다 -- `ture` 같은 오타 하나가
    기능을 **조용히 꺼 버린다**.  ICS 쪽 `_bool` 은 처음부터 거부했고, 같은
    저장소에서 규칙이 둘인 것이 더 나빴다 (`EXPENABLE FLASE` 를 거부하는 규칙과
    같은 정신 -- DevNote 11.14-(2)).
    """
    raw = _text(sec, key, '').strip().lower()
    if not raw:
        return default
    if raw in _TRUE_WORDS:
        return True
    if raw in _FALSE_WORDS:
        return False
    raise IcgConfigError(
        '%s=%r 를 참/거짓으로 읽을 수 없다 -- %s 가운데 하나여야 한다 '
        '(대소문자는 안 가린다)'
        % (key, raw, ' | '.join(_TRUE_WORDS + _FALSE_WORDS)))


def _float(sec, key: str, default: float) -> float:  # noqa: ANN001
    raw = _head(sec, key, '')
    try:
        return float(raw) if raw else default
    except ValueError:
        log.warning('[%s] %s=%r 를 수로 읽을 수 없다 -- 기본값 %s',
                    sec.name, key, raw, default)
        return default


def _int(sec, key: str, default: int) -> int:  # noqa: ANN001
    return int(_float(sec, key, float(default)))


def _path(sec, key: str, default: str) -> str:  # noqa: ANN001
    raw = _text(sec, key, default)
    return os.path.expanduser(raw) if raw else raw


@dataclass
class RadionodeDevice:
    """Radionode RN320-BTH 한 대 -- `[radionode.<별칭>]` 절."""

    alias: str = ''
    #: Radionode365 장치 목록에 보이는 MAC/시리얼.  ⭐ `openapi` 경로가 쓴다.
    mac: str = ''
    #: 이 장치가 채우는 HK 키 (센서 계약 `base.py` 의 소문자 키).
    #: HE box 장치는 `('hebox',)` -- 온도만 카드가 있다 (습도는 로그에만).
    keys: tuple[str, ...] = ()
    #: ⭐ **LoRaWAN DevEUI** -- `local_lns` 경로가 uplink 를 이 장치에 붙이는
    #: 열쇠다 (게이트웨이 내장 NS 의 장치 목록에 있다).  ⛔ 안 적으면 그
    #: 장치의 uplink 는 **버려진다**(`STATUS` 가 그 수를 센다).  구분자
    #: (`-`·`:`)는 있어도 되고, base64 로 오는 판도 정규화해 맞춘다.
    deveui: str = ''


@dataclass
class RadionodeCfg:
    """`[radionode]` -- Tapaculo365 Open API 폴링 (RN320-BTH 는 LoRaWAN 이라
    LAN 직접 폴링이 불가하다 -- 조사 기록은 DevNote 9장).

    ⚠️ **정확한 endpoint 는 콘솔 로그인 뒤의 "OPENAPI 매뉴얼" 에만 있다** --
    그래서 URL·경로·인증 헤더 이름까지 전부 ini 로 뺐다.  운영자가 콘솔에서
    KEY/SECRET 을 만들고 그 매뉴얼의 표를 ini 에 옮기면 코드는 안 바뀐다.
    """

    #: `off`(기본 -- 결측 sentinel) · `openapi`(Tapaculo365 클라우드) ·
    #: `sim`(고정값, **헤더 경로로는 안 나간다** -- 배선 확인용) ·
    #: ⏳ `local_lns`(사설 LoRaWAN 서버 -- **자리만 있고 구현은 없다**).
    #:
    #: ⛔ **`openapi` 는 인터넷이 있어야 한다** -- 끊기면 세 카드
    #: (`HEBOX`/`FSATEMP`/`FSAHUM`)가 그동안 sentinel 이다.  운영자 확정
    #: 2026-09-04: **그 결측은 받아들일 수 없다** -- 그래서 `local_lns` 가
    #: 대비책이고, 그것은 게이트웨이를 우리 안쪽 LNS(ChirpStack)로 돌려
    #: **클라우드 없이** 받는 길이다 (DevNote 9.7 경로 2 · 11.22).
    backend: str = 'off'
    poll_period: float = 60.0
    timeout: float = 10.0
    #: API 서버 origin.  실기값 `https://oa.radionode365.com`.
    base_url: str = ''
    #: 공통 경로.  매뉴얼의 모든 endpoint 가 이 아래다 (`…/channel/get_lst`).
    api_path: str = '/tp365/v1'
    #: 인증 -- ⛔ **본문 파라미터다, 헤더가 아니다** (공개 매뉴얼
    #: `oa.radionode365.com/apidoc/kr/`).  종전의 `latest_path`·`key_header`·
    #: `secret_header` 셋은 이 API 에 없는 자리라 **폐기**했다 (DevNote 11.44).
    api_key: str = ''
    api_secret: str = ''
    #: ini 에 남아 있던 **폐기된 칸** 이름들 -- `validate()` 가 알린다.
    retired_keys: tuple = ()
    #: 신선도 경보 문턱 [s] -- 장치 SEND INTERVAL 의 3배쯤.  이보다 낡은
    #: 표본은 헤더에 싣지 않는다 (호출측이 sentinel 을 채운다).
    #: ⭐ **`HKDATA NOW` 가 클라우드를 다시 칠 최소 표본 나이** [s]
    #: (운영자 2026-09-09).  표본이 이보다 젊으면 **안 친다**.
    #:
    #: ⛔ **`poll_period` 를 쓰면 안 된다** -- 운영자가 폴링 주기를 60초보다
    #: 늘릴 수 있는데, 그러면 재조회 기준까지 따라 늘어나 *"방금 값을 원해서
    #: `NOW` 를 쳤는데 안 친다"* 가 된다.  두 눈금은 **뜻이 다르다.**
    #: ⛔ 장치가 응답에서 알려 주는 `device_interval` 로도 안 된다 -- **배우기
    #: 전에는 `stale_after`(초기값 4000초)의 1/3** 이라 첫 `NOW` 들이 통째로
    #: 막힌다 (2026-09-09 검토에서 잡은 결함이다).
    #:
    #: ⭐ **60초인 근거**: 장치가 그 주기로 클라우드에 올리므로 그 안에 다시
    #: 물어도 **같은 값**이다.  그리고 쿼터가 **api_key 당 분당 10회**라
    #: 명령마다 치면 태우는데, 태우면 **주기 폴링까지 실패해** 세 카드가
    #: sentinel 이 된다 -- 하려던 것의 정반대다.
    #: ⚠️ **장치 전송주기보다 작게 두지 말 것** -- 얻는 것 없이 쿼터만 쓴다.
    #: ⚠️ `0` 이면 **늘 친다** -- 쿼터를 태울 수 있으니 시험 때만.
    now_min_age: float = 60.0
    stale_after: float = 600.0
    #: ⭐ `local_lns` -- 게이트웨이 내장 NS 가 uplink 를 **밀어 줄** 우리 주소.
    #: `호스트:포트` (`0.0.0.0:8088`).  ⚠️ 게이트웨이 integration 에 적은 것과
    #: **같아야** 한다.  비우면 임의 포트라 시험용 말고는 쓸 수 없다.
    lns_bind: str = ''
    #: 수신 경로 -- integration 의 URL 뒤쪽.  다르면 404 로 버린다.
    lns_path: str = '/uplink'
    #: 선택 -- integration 에 `X-Auth-Token` 헤더를 붙였으면 그 값.  비우면
    #: 검사하지 않는다 (LAN 전용 전제).  ⚠️ 틀린 값이 헤더로 들어가는 길이라
    #: 여러 계통이 같은 망에 있으면 채울 것.
    lns_token: str = ''
    #: sim 백엔드가 내는 고정값.
    sim_values: dict = field(default_factory=lambda: {
        'hebox': 33.21, 'fsatemp': 23.4, 'fsahum': 12.3})
    devices: tuple[RadionodeDevice, ...] = ()


@dataclass
class HkCfg:
    """`[hk]` -- HK 취득·로깅 (1분 주기, `ics_archon` 이 소비한다)."""

    #: 주기 [s].  운영 확정값은 60 -- 로그가 곧 `ics_archon` 헤더의 원천이라
    #: 이보다 성기면 science 헤더의 HK 나이가 그만큼 낡는다.
    interval: float = 60.0
    #: CSV·스냅샷 자리.  ⚠️ data_dir 밑에 두지 말 것 (아카이브 오염).
    log_dir: str = '~/AIC/Logs'
    #: 원자적 최신 스냅샷 파일 이름 (`log_dir` 안).  `ics_archon` 이 읽는다.
    latest_name: str = 'hk_latest.G.json'
    #: AUX(`ENS1~7`)도 주기마다 TC 에 물어 로그에 싣나.  노출 사이클과 별개의
    #: 질의라 TC 부하가 늘어난다 -- 레거시 ICG 는 노출당 1페어였다 (§5.3).
    query_aux: bool = True


@dataclass
class IcgCfg:
    """`[icg]` -- guide 컨트롤러 배선 (`ArchonController` duck-type)."""

    # -- ArchonController 가 읽는 속성들 (이름을 바꾸면 안 된다) ------------
    hosts: dict = field(default_factory=dict)          # {'G': ip}
    port: int = 4242
    sock_timeout: float = 1.0
    #: ⛔ **4 다 -- science 와 같은 값** (2026-09-09 정정).  종전 `2` 는 근거
    #: 없이 낮았고 `acf_retry` 가 `1` 이었던 것과 **같은 부류**다 (11.54).
    #: ⚠️ 컨트롤러가 어긋난 연결을 놓는 데 **약 10초**가 걸리는데 `2` 는
    #: 시도 사이 대기를 합쳐도 2초라 **거의 늘 포기했다** (벤치 로그의
    #: `접속 실패 1/2 · 2/2` 뒤 기동 실패).
    connect_retry: int = 4
    #: 재수립에서 **끊고** 쉬는 시간 [s].  ⭐ labtest(실기에서 도는 원본)가
    #: `0.8` 이다.  ⛔ 종전에는 **0** 이라 즉시 다시 들이받았고, 컨트롤러가
    #: 앞선 폭주분을 소화하는 동안 **새 SYN 에 응답하지 않아** 재접속이
    #: `timed out` 으로 깨졌다 (2026-09-09 벤치, 약 10초가 걸렸다).
    settle_before: float = 0.8
    #: 재수립에서 **붙고** 쉬는 시간 [s] (labtest `2.0`).  ⚠️ 붙은 직후에도
    #: 컨트롤러가 앞선 것을 소화 중일 수 있다 -- 실제로 새 연결에 **옛 응답**이
    #: 흘러들어왔다 (`기대 <01, 받음 <00`).
    settle_after: float = 2.0
    acf: dict = field(default_factory=dict)            # {'G': path}
    apply_acf: bool = True
    #: ⛔ **4 다 -- science(`ics_archon.ini`)·labtest 와 같은 값** (2026-09-09).
    #: 종전 `1` 은 근거 없이 낮았고, 벤치에서 **첫 실패에 곧바로 `GO` 가 죽었다**
    #: (`WCONFIG` 하나의 응답이 비어 참조번호가 한 칸 밀렸다).  ⭐ 원본 labtest 는
    #: 이 실패를 **정상으로 보고 재접속+재시도**한다 (`SWSET_ACFRETRY = 4`) --
    #: ACF 밀어넣기는 왕복 1000여 개를 몰아 보내는 자리라 링크가 한 번 어긋날
    #: 확률이 실제로 있다.  ⚠️ 재시도 사이에 `resync()` 로 **연결을 새로 연다**
    #: (참조번호만 고치면 늦은 응답이 다음 명령을 먹는다 -- 11.22 (1)).
    acf_retry: int = 4
    poweron_wait: float = 12.0
    param_intms_slot: str = 'PARAMETER2'
    param_intms_name: str = 'IntMS'
    param_exposures_slot: str = 'PARAMETER1'
    param_exposures_name: str = 'Exposures'
    #: flush 플래그의 **Config 슬롯 번호**(`PARAMETERn` 의 n; R2613+, 규격 10.1-2).
    #: ⛔ **`PARAMETER0` 이어야 한다** -- `LOADPARAMS` 는 파라미터를 첫 슬롯부터
    #: 슬롯 번호 순서로 적용하고(매뉴얼 p.52)
    #: 유휴 루프가 1 µs 라, `Exposures`(PARAMETER1) 뒤에 앉으면 코어가 flush
    #: 없이 `Exposure:` 로 먼저 뛴다 (설계 검토 blocker, DevNote 11.31).
    param_flush_slot: str = 'PARAMETER0'
    param_flush_name: str = 'FirstFlush'
    telemetry: bool = True
    status_timeout: float = 2.0
    #: ⭐ **0.2 다** (운영자 2026-09-09).  guide 독출이 1.25 s 라 0.5 면
    #: `PCTREAD` 표본이 **3~4개**뿐이었다.  0.2 면 ~6개다.
    #: ⚠️ 폴링 하나가 `FRAME` 왕복이고 FETCH 와 락을 다투므로 더 낮추지 않았다
    #: -- `progress_step`(5%)이 값이 안 움직이면 안 내보내므로 소음은 걸러진다.
    frame_poll: float = 0.2
    progress_step: int = 5
    burst_len: int = 1024
    fetch_buffers: int = 2
    #: FETCH 상한 [s] = **잠금 상한** -- 하한(1.251 s) 아래여야 한다 (DevNote
    #: 10.6).  8.3 MiB ≈ 0.08 s 라 1 s 면 12배 여유.  `GuideBackend` 가 검사한다.
    #: ⏳ **`HKDATA`/`HK` 지연을 `INFO` 로 남기는 임계 [ms]** (2026-09-09).
    #: 수신부터 응답 본문 완성까지가 이 값을 넘으면 한 줄 남기고, 아래는
    #: `DEBUG` 로 내린다.  ⭐ **`0` 이면 전부 남긴다 -- 벤치 실측용 설정이다**
    #: (평상 운용은 기본 50 ms 로 되돌린다).
    #: ⛔ **`TRIGOUT` 은 이 눈금을 안 탄다** -- 운영자가 칠 때만 나가는 드문
    #: 명령이라 늘 남긴다 (`commands._log_latency(always=True)`).
    #: ⚠️ 임계가 있는 이유는 **바깥 감시 계통이 `HKDATA` 를 초 단위로 물어
    #: 올 수 있어서**다 -- 우리 프로그램에는 주기 발신자가 없다.
    #: ⭐ **150 은 실측으로 정했다** (2026-09-09, DevNote 11.55): 취득 중
    #: `HKDATA` 는 중앙 7.7 ms · 95 % 96.5 ms · 최악 **107.8 ms** 였다.
    #: 종전 임시값 50 으로 두면 **14 %가 매번 `INFO`** 라 소음이 된다 --
    #: 최악값 위로 올려야 *"평시 조용 · 튀면 이상"* 이 된다.
    latency_warn_ms: float = 150.0
    fetch_timeout: float = 1.0
    frame_dump: float = 0.0
    frame_timeout: float = 60.0
    lock_buffer: bool = True
    recheck_after_fetch: bool = True

    # -- icg 고유 ----------------------------------------------------------
    #: 선언 기하 -- 모듈 상수의 사본 (fetch 대조·저장이 이 값을 쓴다).
    naxis1: int = NAXIS1
    naxis2: int = NAXIS2
    #: **설정 가능한 최소 노출시간** [s] -- 이보다 짧은 `EXPTIME` 요청은 이 값으로 접는다
    #: (운영자 확정 2026-09-05: 기본 노출시간 1.2506 s 위에 여유를 두어 1.3; 용어는 운영자
    #: 개명 2026-09-05 -- 구 '운영 하한').  ⚠️ **기본 노출시간**(`GuideBackend.base_exptime()`:
    #: `IntMS=0` 일 때의 주기 = NoIntMS + 트랜스퍼 + 독출, ACF 계산값 -- R2610~R2619 1.251 s;
    #: `NoIntMS` 항은 10.3 실측 1% 적중, 트랜스퍼·독출 항은 ⏳ 첫 guide 구동 실측)과 **다른
    #: 물건**이다 -- `IntMS = EXPTIME - 기본 노출시간` 의 기준은 계산값이어야 헤더가 참이고,
    #: 이 값은 그 위에 얹는 정책이다.  기본 노출시간보다 작게 두면 기본 노출시간이 이긴다.
    #: ACF 계산이 없을 때(스크립트 없는 시험 ACF · 대역)는 이 값이 기본 노출시간 노릇을
    #: 겸한다 (종전 1.0 은 근거 없는 잠정값이었다 -- DevNote 9.10·9.15).
    exptime_min: float = 1.3
    #: 저장 태스크 드레인 상한 [s] (종료 시).
    shutdown_drain: float = 15.0
    #: 노출 잠금(`EXPENABLE`) 기록 파일.  비우면 **ini 옆**
    #: `<ini이름>.expenable` 로 정한다 (`expnum` 과 같은 관례 --
    #: `-c` 로 여러 구성을 나란히 돌려도 섞이지 않는다).
    #: ⚠️ 빈 채로 두고 `source_path` 도 없으면(ini 없이 만든 경우 -- 단위
    #: 시험) **지속시키지 않는다.**
    expenable_file: str = ''

    #: ⭐ **이온게이지를 끄는 갈래** -- `diopower` | `ionen` (`gauge.METHODS`).
    #: `diopower` 는 `MOD10\\DIO_POWER`(8라인 전부의 버퍼 전원)를 내리고,
    #: `ionen` 은 `MOD10\\DIO_SOURCE3`(IONEN 한 라인)만 내린다.
    #:
    #: ✅ **기본은 `diopower` -- 실측으로 확인됐다** (운영자 2026-09-04:
    #: *"MOD10\\DIO_POWER=1/0 으로 On/Off 제어 잘되는 것 확인했어"*).  선임이
    #: 쓰던 길과도 같다 (`…_goff_….acf` 가 정확히 그 한 줄만 다르다).
    #: ⏳ `ionen` 은 **여전히 미검증**이다 -- 읽기를 살린 채 필라멘트만 끄는
    #: 쪽이라 이론상 낫지만 실기로 확인되지 않았다 (DevNote 11.19·11.24).
    gauge_off_method: str = 'diopower'
    #: 기동 때 이온게이지를 **켤지 끌지** (`off`/`on`, 운영자 지시 2026-09-10).
    #:
    #: ⛔ **기본이 `off` 인 이유**: 게이지 필라멘트가 science 영상을 오염시키므로
    #: science 노출 중에는 꺼져 있어야 하는데, 그 사이에 ICG 를 재실행하면
    #: 종전에는 **ACF 가 켜 버렸다**(`MOD10\\DIO_POWER=1`).  ⭐ R2619 에서 ACF 를
    #: `0` 으로 내렸고 이 눈금이 그 위의 정책이다.
    #: ⭐ **켜는 쪽은 ICS 몫이다** -- 노출이 끝나고 `[ics] gauge_reenable_after`
    #: 뒤에 `ICS>ICG VACGAUGE ON` 이 온다 (`ics_archon/gaugectl.py`).
    #: ⚠️ `keep`(건드리지 않는다)은 **두지 않았다** -- 기동이 늘 ACF 를 적용하고
    #: 그 순간 값이 파일 값으로 덮이므로, 앞선 상태를 보존한다는 뜻이 성립하지
    #: 않는다.  *"안 건드린다"* 라고 적어 두면 거짓말이 된다.
    gauge_on_start: str = 'off'

    hk: HkCfg = field(default_factory=HkCfg)
    radionode: RadionodeCfg = field(default_factory=RadionodeCfg)
    source_path: str = ''

    @property
    def frame_bytes(self) -> int:
        return self.naxis1 * self.naxis2 * 2

    def expenable_path(self, sim_cfg=None) -> str:  # noqa: ANN001
        """노출 잠금 기록의 실제 경로.  비어 있으면 **ini 옆**으로 정한다.

        `ics_sim.config.resolve_expnum_file()` 과 같은 관례다 --
        `icg_archon.ini` -> `icg_archon.expenable`.  ⚠️ ini 없이 만든 경우
        (`source_path` 가 빈 단위 시험)는 **빈 값으로 남겨 지속시키지 않는다**
        -- 시험이 실행 순서에 따라 서로의 잠금을 물려받지 않게 한다.
        """
        if self.expenable_file:
            return os.path.expanduser(self.expenable_file)
        if self.source_path:
            return os.path.splitext(self.source_path)[0] + '.expenable'
        return ''

    @property
    def host(self) -> str:
        return self.hosts.get(TAG, '')

    @property
    def acf_path(self) -> str:
        return self.acf.get(TAG, '')


def _make_parser() -> configparser.ConfigParser:
    return configparser.ConfigParser(inline_comment_prefixes=('#',),
                                     comment_prefixes=('#',),
                                     interpolation=None)


def load(path: str) -> IcgCfg:
    """`icg_archon.ini` 에서 icg 전용 절을 읽는다 (없는 절은 기본값)."""
    cfg = IcgCfg()
    cp = _make_parser()
    read = cp.read(path, encoding='utf-8')
    cfg.source_path = os.path.abspath(path) if read else ''

    if cp.has_section('icg'):
        s = cp['icg']
        host = _head(s, 'ctrl_host', '')
        if host:
            cfg.hosts[TAG] = host
        acf = _path(s, 'acf', '')
        if acf:
            cfg.acf[TAG] = acf
        cfg.port = _int(s, 'port', cfg.port)
        cfg.sock_timeout = _float(s, 'sock_timeout', cfg.sock_timeout)
        cfg.connect_retry = _int(s, 'connect_retry', cfg.connect_retry)
        cfg.settle_before = _float(s, 'settle_before', cfg.settle_before)
        cfg.settle_after = _float(s, 'settle_after', cfg.settle_after)
        cfg.apply_acf = _bool(s, 'apply_acf', cfg.apply_acf)
        cfg.acf_retry = _int(s, 'acf_retry', cfg.acf_retry)
        cfg.poweron_wait = _float(s, 'poweron_wait', cfg.poweron_wait)
        cfg.param_flush_slot = _head(s, 'param_flush_slot',
                                     cfg.param_flush_slot)
        cfg.param_flush_name = _head(s, 'param_flush_name',
                                     cfg.param_flush_name)
        cfg.param_intms_slot = _head(s, 'param_intms_slot',
                                     cfg.param_intms_slot)
        cfg.param_intms_name = _head(s, 'param_intms_name',
                                     cfg.param_intms_name)
        cfg.param_exposures_slot = _head(s, 'param_exposures_slot',
                                         cfg.param_exposures_slot)
        cfg.param_exposures_name = _head(s, 'param_exposures_name',
                                         cfg.param_exposures_name)
        cfg.telemetry = _bool(s, 'telemetry', cfg.telemetry)
        cfg.status_timeout = _float(s, 'status_timeout', cfg.status_timeout)
        cfg.frame_poll = _float(s, 'frame_poll', cfg.frame_poll)
        cfg.progress_step = _int(s, 'progress_step', cfg.progress_step)
        cfg.fetch_buffers = _int(s, 'fetch_buffers', cfg.fetch_buffers)
        cfg.latency_warn_ms = _float(s, 'latency_warn_ms',
                                     cfg.latency_warn_ms)
        cfg.fetch_timeout = _float(s, 'fetch_timeout', cfg.fetch_timeout)
        cfg.frame_dump = _float(s, 'frame_dump', cfg.frame_dump)
        cfg.frame_timeout = _float(s, 'frame_timeout', cfg.frame_timeout)
        cfg.lock_buffer = _bool(s, 'lock_buffer', cfg.lock_buffer)
        cfg.recheck_after_fetch = _bool(s, 'recheck_after_fetch',
                                        cfg.recheck_after_fetch)
        cfg.exptime_min = _float(s, 'exptime_min', cfg.exptime_min)
        cfg.shutdown_drain = _float(s, 'shutdown_drain', cfg.shutdown_drain)
        cfg.expenable_file = _path(s, 'expenable_file',
                                   cfg.expenable_file)
        cfg.gauge_off_method = (s.get('gauge_off_method', '').strip().lower()
                                or cfg.gauge_off_method)
        want = (s.get('gauge_on_start', '').strip().lower()
                or cfg.gauge_on_start)
        if want not in ('on', 'off'):
            raise IcgConfigError(
                "[icg] gauge_on_start 는 'on' 또는 'off' 다 -- 받은 값 %r.  "
                "⛔ 'keep' 은 없다: 기동이 늘 ACF 를 적용해 그 순간 값이 파일 "
                '값으로 덮이므로 앞선 상태를 보존할 수 없다' % want)
        cfg.gauge_on_start = want

    if cp.has_section('hk'):
        s = cp['hk']
        cfg.hk.interval = _float(s, 'interval', cfg.hk.interval)
        cfg.hk.log_dir = _path(s, 'log_dir', cfg.hk.log_dir)
        cfg.hk.latest_name = _text(s, 'latest_name', cfg.hk.latest_name)
        cfg.hk.query_aux = _bool(s, 'query_aux', cfg.hk.query_aux)

    if cp.has_section('radionode'):
        s = cp['radionode']
        r = cfg.radionode
        r.backend = _head(s, 'backend', r.backend).lower()
        r.poll_period = _float(s, 'poll_period', r.poll_period)
        r.timeout = _float(s, 'timeout', r.timeout)
        r.base_url = _text(s, 'base_url', r.base_url)
        r.api_path = _text(s, 'api_path', r.api_path)
        r.api_key = _text(s, 'api_key', r.api_key)
        r.api_secret = _text(s, 'api_secret', r.api_secret)
        # ⛔ 폐기한 칸이 **남아 있으면 알린다** -- 현장 ini 에 그대로 있으면
        # 적어 둔 사람은 그것이 쓰인다고 믿는다 (조용히 무시가 제일 나쁘다).
        gone = [k for k in ('latest_path', 'key_header', 'secret_header')
                if s.get(k, fallback='').strip()]
        if gone:
            r.retired_keys = tuple(gone)
        r.now_min_age = _float(s, 'now_min_age', r.now_min_age)
        r.stale_after = _float(s, 'stale_after', r.stale_after)
        r.lns_bind = _text(s, 'lns_bind', r.lns_bind)
        r.lns_path = _text(s, 'lns_path', r.lns_path)
        r.lns_token = _text(s, 'lns_token', r.lns_token)

    devices = []
    for name in cp.sections():
        if not name.startswith('radionode.'):
            continue
        alias = name.split('.', 1)[1]
        s = cp[name]
        keys = tuple(k.strip().lower()
                     for k in _text(s, 'keys', '').split(',') if k.strip())
        devices.append(RadionodeDevice(alias=alias,
                                       mac=_head(s, 'mac', ''), keys=keys,
                                       deveui=_head(s, 'deveui', '')))
    if devices:
        cfg.radionode.devices = tuple(devices)
    return cfg


def validate(cfg: IcgCfg, backend: str) -> list[str]:
    """기동 전 검사 -- 치명적이면 `IcgConfigError`, 나머지는 경고 목록."""
    warn: list[str] = []
    if backend == 'icg_archon':
        if not cfg.host:
            raise IcgConfigError('[icg] ctrl_host 가 없다 -- guide 컨트롤러 '
                                 'IP 를 적을 것 (시뮬 회귀는 --backend sim)')
        # ⚠️ ACF 경로는 apply_acf 와 무관하게 필수다 -- 적용을 건너뛰어도
        # 파라미터 줄 번호(`IntMS`·`Exposures`)를 알려면 파싱은 해야 한다.
        # `prepare()` 는 경로가 비면 ACF 블록을 통째로 건너뛰어 첫 트리거의
        # `set_config` 가 "설정 줄을 모른다" 로 죽는다 (DevNote 9.15-(7)).
        if not cfg.acf_path:
            raise IcgConfigError('[icg] acf 가 없다 -- guide ACF 경로를 적을 것 '
                                 '(apply_acf=false 여도 파라미터 줄 번호를 알기 '
                                 '위해 파싱은 한다)')
        if not os.path.exists(cfg.acf_path):
            raise IcgConfigError('[icg] acf=%s 가 없다' % cfg.acf_path)
        if not cfg.apply_acf:
            # 10.2: POWERON 은 **이 세션의 APPLYALL** 을 전제한다 (p.51).
            warn.append('[icg] apply_acf=false -- 이 프로그램은 APPLYALL 을 하지 '
                        '않는다.  REBOOT/설정 재업로드 뒤에는 GUI(또는 '
                        'probe_archon --expose 0)로 Apply All 을 먼저 할 것 -- '
                        '안 하면 POWERON 이 ?xx 로 거부된다 (DevNote 10.2)')
        if not cfg.lock_buffer and not cfg.recheck_after_fetch:
            # science `_cross_checks` 와 같은 짝 검사 (DevNote 10.6·8.4).
            warn.append('[icg] lock_buffer=false 인데 recheck_after_fetch 도 false 다 '
                        '-- fetch 중 버퍼가 덮이는 창을 보는 것이 없다 (두 노출이 '
                        '섞인 프레임이 경고 없이 저장된다).  lock_buffer=true 가 '
                        '정본이다 (DevNote 10.6·8.4)')
    if cfg.gauge_off_method not in gauge.METHODS:
        # ⛔ 기동을 세운다.  모르는 갈래로 뜨면 `VACGAUGE OFF` 가 **아무것도
        # 끄지 않은 채** 상태를 OFF 로 적고, 그러면 `DEWPRES` 만 sentinel 로
        # 내려가 "껐다고 믿는데 필라멘트는 켜져 있다" 가 된다 -- science 영상
        # 오염을 막으려는 명령이 조용히 무력해지는 자리다.
        raise IcgConfigError('[icg] gauge_off_method=%r 은 모르는 갈래다 -- %s '
                             '가운데 하나여야 한다 (DevNote 11.19)'
                             % (cfg.gauge_off_method,
                                ' | '.join(sorted(gauge.METHODS))))
    if cfg.gauge_off_method == gauge.IONEN:
        # ⏳ **미검증 갈래다.**  실측으로 확인된 것은 diopower 이므로, 이 값을
        # 골랐다는 것은 "아직 안 해 본 길을 쓰겠다" 는 뜻이다 -- 조용히 두면
        # 첫 관측에서 *"껐는데 필라멘트가 안 꺼진"* 상태를 못 알아챈다.
        warn.append('[icg] gauge_off_method=ionen -- ⏳ **실기 미검증**이다.  '
                    '실측으로 확인된 것은 diopower 다 (운영자 2026-09-04).  '
                    'ionen 을 쓰려면 벤치에서 필라멘트가 실제로 꺼지는지 먼저 '
                    '확인할 것 (INSTALL/icg_first_run 게이지 부록)')
    r = cfg.radionode
    if r.backend not in ('sim', 'openapi', 'off', 'local_lns'):
        raise IcgConfigError('[radionode] backend=%r -- sim | openapi | off | '
                             'local_lns 중 하나여야 한다' % r.backend)
    if r.backend == 'local_lns':
        # ⭐ 여기서 막는 것은 **조용히 아무것도 안 받는 상태**다.  주소가 없으면
        # 임의 포트에 뜨고(게이트웨이가 못 찾는다), DevEUI 가 없으면 uplink 가
        # 와도 어느 장치인지 못 붙여 전부 버려진다 -- 둘 다 로그만 보면
        # "잘 떠 있는" 것처럼 보이는 자리다.
        if not r.lns_bind:
            warn.append('[radionode] backend=local_lns 인데 lns_bind 가 비었다 '
                        '-- 임의 포트에 떠서 게이트웨이가 못 찾는다.  '
                        '`0.0.0.0:8088` 처럼 적고 게이트웨이 integration 의 '
                        'URL 과 맞출 것 (INSTALL 7.5)')
        no_eui = [d.alias for d in r.devices if not d.deveui]
        if no_eui:
            warn.append('[radionode] deveui 가 없는 장치: %s -- 그 장치의 '
                        'uplink 는 **전부 버려진다**.  게이트웨이 내장 NS 의 '
                        '장치 목록에서 DevEUI 를 옮겨 적을 것 (INSTALL 7.4)'
                        % ', '.join(no_eui))
    if r.backend == 'openapi':
        missing = [k for k, v in (('base_url', r.base_url),
                                  ('api_key', r.api_key),
                                  ('api_secret', r.api_secret)) if not v]
        if missing:
            raise IcgConfigError(
                '[radionode] openapi 백엔드에 %s 가 없다 -- Tapaculo365 콘솔의 '
                '"OPENAPI 매뉴얼" 에서 옮겨 적을 것' % ', '.join(missing))
        if not r.devices:
            warn.append('[radionode.*] 장치 절이 없다 -- HEBOX/FSATEMP/FSAHUM '
                        '이 전부 sentinel 로 실린다')
        # ⭐ `local_lns` 의 `deveui` 경고와 **짝이다** -- 자격증명 넷이 다 있어도
        # `mac` 이 비면 그 장치는 못 묻는다.  ⛔ 그런데 `CONNECT` 는 통과하므로
        # 4번 걸음(`HK`)에서 sentinel 만 보이고, 원인을 *"인터넷·계정 등급"* 에서
        # 찾게 된다 (`bench_test_plan.md` 1단계 "멈출 조건").  기동은 안 세운다 --
        # 나머지 HK(RTD·진공·AUX)는 돌아야 한다.
        if r.retired_keys:
            warn.append('[radionode] %s 는 **더 이상 쓰지 않는 칸**이다 -- 이 API '
                        '는 인증을 본문 파라미터로 받고(헤더 없음) 채널 목록을 '
                        'channel/get_lst 한 번으로 가져온다.  지워도 된다 '
                        '(DevNote 11.44)' % ', '.join(r.retired_keys))
        no_mac = [d.alias for d in r.devices if not d.mac]
        if no_mac:
            warn.append('[radionode] mac 이 없는 장치: %s -- 그 장치는 폴링에서 '
                        '건너뛰고 카드가 **계속 sentinel** 이다.  Radionode365 '
                        '장치 목록의 MAC/시리얼을 옮겨 적을 것 (자격증명 넷과는 '
                        '별개다)' % ', '.join(no_mac))
    if r.backend == 'sim' and backend == 'icg_archon':
        # 실기 취득인데 환경센서만 시뮬 -- 상수가 헤더에 실물처럼 남으면
        # 아카이브에서 잰 값과 못 가른다.  값 경로는 `values_with_time()`
        # 이 이미 막지만, 조합 자체를 알린다 (science `_warn_if_real_frames…`
        # 와 같은 부류의 방어다).
        warn.append('[radionode] backend=sim 인데 실기 취득이다 -- 고정 '
                    '상수는 헤더로 안 나가고 HEBOX/FSATEMP/FSAHUM 이 '
                    'sentinel 로 실린다.  실값이 필요하면 openapi 로 둘 것')
    if cfg.hk.interval < 1.0:
        warn.append('[hk] interval=%.1fs 는 너무 촘촘하다 -- STATUS 질의가 '
                    '취득 경로와 락을 다툰다' % cfg.hk.interval)
    # rawhdr 기하 불변식과 같은 정신 -- 선언 기하가 모듈 상수와 갈리면 멈춘다.
    if (cfg.naxis1, cfg.naxis2) != (NAXIS1, NAXIS2):
        raise IcgConfigError('guide 기하는 규격 9.3절 고정이다 (4224x1033) -- '
                             '설정으로 바꿀 수 없다')
    return warn

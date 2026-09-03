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


def _bool(sec, key: str, default: bool) -> bool:  # noqa: ANN001
    raw = _text(sec, key, '')
    if not raw:
        return default
    return raw.lower() in ('1', 'true', 'yes', 'on')


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
    #: Radionode365 장치 목록에 보이는 MAC/시리얼.
    mac: str = ''
    #: 이 장치가 채우는 HK 키 (센서 계약 `base.py` 의 소문자 키).
    #: HE box 장치는 `('hebox',)` -- 온도만 카드가 있다 (습도는 로그에만).
    keys: tuple[str, ...] = ()


@dataclass
class RadionodeCfg:
    """`[radionode]` -- Tapaculo365 Open API 폴링 (RN320-BTH 는 LoRaWAN 이라
    LAN 직접 폴링이 불가하다 -- 조사 기록은 DevNote 9장).

    ⚠️ **정확한 endpoint 는 콘솔 로그인 뒤의 "OPENAPI 매뉴얼" 에만 있다** --
    그래서 URL·경로·인증 헤더 이름까지 전부 ini 로 뺐다.  운영자가 콘솔에서
    KEY/SECRET 을 만들고 그 매뉴얼의 표를 ini 에 옮기면 코드는 안 바뀐다.
    """

    #: `off`(기본 -- 결측 sentinel) · `openapi`(Tapaculo365) · `sim`(고정값,
    #: **헤더 경로로는 안 나간다** -- 배선 확인용).
    backend: str = 'off'
    poll_period: float = 60.0
    timeout: float = 10.0
    base_url: str = ''
    #: 최근 측정값 endpoint -- `{mac}` 자리에 장치 MAC 이 들어간다.
    latest_path: str = ''
    #: 인증 -- 헤더 이름까지 ini 소관 (콘솔 매뉴얼이 정본).
    api_key: str = ''
    api_secret: str = ''
    key_header: str = 'X-API-KEY'
    secret_header: str = 'X-API-SECRET'
    #: 신선도 경보 문턱 [s] -- 장치 SEND INTERVAL 의 3배쯤.  이보다 낡은
    #: 표본은 헤더에 싣지 않는다 (호출측이 sentinel 을 채운다).
    stale_after: float = 600.0
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
    log_dir: str = '~/AIC/log'
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
    connect_retry: int = 2
    acf: dict = field(default_factory=dict)            # {'G': path}
    apply_acf: bool = True
    acf_retry: int = 1
    poweron_wait: float = 12.0
    param_intms_slot: str = 'PARAMETER2'
    param_intms_name: str = 'IntMS'
    param_exposures_slot: str = 'PARAMETER1'
    param_exposures_name: str = 'Exposures'
    telemetry: bool = True
    status_timeout: float = 2.0
    frame_poll: float = 0.5
    progress_step: int = 5
    burst_len: int = 1024
    fetch_buffers: int = 2
    #: FETCH 상한 [s] = **잠금 상한** -- 하한(1.251 s) 아래여야 한다 (DevNote
    #: 10.6).  8.3 MiB ≈ 0.08 s 라 1 s 면 12배 여유.  `GuideBackend` 가 검사한다.
    fetch_timeout: float = 1.0
    frame_dump: float = 0.0
    frame_timeout: float = 60.0
    lock_buffer: bool = True
    recheck_after_fetch: bool = True

    # -- icg 고유 ----------------------------------------------------------
    #: 선언 기하 -- 모듈 상수의 사본 (fetch 대조·저장이 이 값을 쓴다).
    naxis1: int = NAXIS1
    naxis2: int = NAXIS2
    #: `EXPTIME` 하한 [s] -- **ACF 를 못 읽을 때의 대체값**이다.  정본은 `acftiming`
    #: 이 타이밍 스크립트에서 계산한 하한(R2610: 1.251 s -- `NoIntMS` 항은 10.3 실측
    #: 1% 적중, 트랜스퍼·독출 항은 ⏳ 첫 guide 구동 실측).  하한 아래 값을 두면
    #: 클램프가 무력해지므로 ini(2.0)와 같이 하한 위로 둔다 (종전 1.0 은 근거 없는
    #: 잠정값이었다 -- DevNote 9.10·9.15).
    exptime_min: float = 2.0
    #: 저장 태스크 드레인 상한 [s] (종료 시).
    shutdown_drain: float = 15.0

    hk: HkCfg = field(default_factory=HkCfg)
    radionode: RadionodeCfg = field(default_factory=RadionodeCfg)
    source_path: str = ''

    @property
    def frame_bytes(self) -> int:
        return self.naxis1 * self.naxis2 * 2

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
        cfg.apply_acf = _bool(s, 'apply_acf', cfg.apply_acf)
        cfg.acf_retry = _int(s, 'acf_retry', cfg.acf_retry)
        cfg.poweron_wait = _float(s, 'poweron_wait', cfg.poweron_wait)
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
        cfg.fetch_timeout = _float(s, 'fetch_timeout', cfg.fetch_timeout)
        cfg.frame_dump = _float(s, 'frame_dump', cfg.frame_dump)
        cfg.frame_timeout = _float(s, 'frame_timeout', cfg.frame_timeout)
        cfg.lock_buffer = _bool(s, 'lock_buffer', cfg.lock_buffer)
        cfg.recheck_after_fetch = _bool(s, 'recheck_after_fetch',
                                        cfg.recheck_after_fetch)
        cfg.exptime_min = _float(s, 'exptime_min', cfg.exptime_min)
        cfg.shutdown_drain = _float(s, 'shutdown_drain', cfg.shutdown_drain)

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
        r.latest_path = _text(s, 'latest_path', r.latest_path)
        r.api_key = _text(s, 'api_key', r.api_key)
        r.api_secret = _text(s, 'api_secret', r.api_secret)
        r.key_header = _text(s, 'key_header', r.key_header)
        r.secret_header = _text(s, 'secret_header', r.secret_header)
        r.stale_after = _float(s, 'stale_after', r.stale_after)

    devices = []
    for name in cp.sections():
        if not name.startswith('radionode.'):
            continue
        alias = name.split('.', 1)[1]
        s = cp[name]
        keys = tuple(k.strip().lower()
                     for k in _text(s, 'keys', '').split(',') if k.strip())
        devices.append(RadionodeDevice(alias=alias,
                                       mac=_head(s, 'mac', ''), keys=keys))
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
    r = cfg.radionode
    if r.backend not in ('sim', 'openapi', 'off'):
        raise IcgConfigError('[radionode] backend=%r -- sim | openapi | off '
                             '중 하나여야 한다' % r.backend)
    if r.backend == 'openapi':
        missing = [k for k, v in (('base_url', r.base_url),
                                  ('latest_path', r.latest_path),
                                  ('api_key', r.api_key),
                                  ('api_secret', r.api_secret)) if not v]
        if missing:
            raise IcgConfigError(
                '[radionode] openapi 백엔드에 %s 가 없다 -- Tapaculo365 콘솔의 '
                '"OPENAPI 매뉴얼" 에서 옮겨 적을 것' % ', '.join(missing))
        if not r.devices:
            warn.append('[radionode.*] 장치 절이 없다 -- HEBOX/FSATEMP/FSAHUM '
                        '이 전부 sentinel 로 실린다')
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

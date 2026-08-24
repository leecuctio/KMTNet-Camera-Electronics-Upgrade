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
import os
from dataclasses import dataclass, field

from . import _simpath

_simpath.ensure()

from ics_sim import rawhdr, rawpair          # noqa: E402

log = logging.getLogger('ics_archon.config')

#: 컨트롤러 태그 (`rawpair.CONTROLLERS` 의 색인 순서 = 1:MK, 2:NT)
CTRLTAGS = tuple(tag for tag, _ in rawpair.CONTROLLERS)


class ArchonConfigError(Exception):
    """`[archon]` 설정을 읽을 수 없다."""


@dataclass
class ArchonCfg:
    """컨트롤러 계통 설정.  기본값은 실험실 스크립트의 실측값에서 왔다."""

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
    #: 첫 노출 준비에서 ACF 를 적용할지.  false 면 이미 적용된 설정을 그대로
    #: 쓴다 -- 컨트롤러가 설정을 들고 있으므로 재기동이 빠르다.
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

    # -- 노출·독출 -------------------------------------------------------
    #: 셔터 트리거(TRIGOUTFORCE)를 내는 컨트롤러.  `both` 면 둘 다.
    #: 실기 배선이 확인되면 한쪽으로 좁힌다 (검토사항).
    shutter_ctrl: str = 'BOTH'
    #: `ERASE` 를 전체 독출 flush 로 처리할지 (labtest `bFullFlush`).
    full_flush_on_erase: bool = True
    #: fetch 하는 동안 프레임 버퍼를 `LOCKn` 으로 잠글지 (매뉴얼 p.50).
    #:
    #: **BIGBUF 는 버퍼가 둘뿐이고 노출 1회가 프레임 2개**(flush + 취득)를
    #: 만들므로 다음 노출이 이 프레임의 버퍼를 덮는다 -- 저장은 `write_delay`
    #: 뒤에 백그라운드로 도는 일이라 그 경합이 실재한다.
    #: ⚠️ labtest 는 2026-05-28 에 `LOCK` 을 뺐다("remove to fetch debug") --
    #: 되돌린 것이므로 실기 확인 항목이다.  끄면 labtest 와 같아지고, 그래도
    #: fetch 앞의 프레임 번호 대조는 남는다(조용히 틀린 파일은 안 나온다).
    lock_buffer: bool = True
    #: FRAME 폴링 간격 [s].  labtest 는 0.5/0.65 를 썼다.
    frame_poll: float = 0.5
    #: 노출 지시부터 프레임 완료까지의 상한 [s].  0 이면 무한 대기.
    #:
    #: **없으면 조용히 멈춘다.**  labtest 는 `while True` 로 프레임 번호가
    #: 바뀔 때까지 돌았고 사람이 화면을 보고 있었다.  본편은 OBSAgent 가
    #: 상대이므로, 독출이 시작되지 않으면(ACF 가 틀림 · 클록이 안 감 ·
    #: `LOADPARAMS` 가 먹히지 않음) `EXPSTATUS=READOUT` 에 갇혀 관측자
    #: 화면이 멈추고 `force_idle` 타임아웃으로 `opause` 에 빠진다.
    #: 상한을 넘기면 레거시와 같은 오류 경로를 탄다 -- `DMA WAIT TIMEOUT.
    #: EXPOSURES ABORTED.` (base.py `BackendError` docstring).
    #: 기본 300초는 실측(독출 ~40초 예상) 대비 넉넉하게 잡은 값이고, 실측이
    #: 나오면 조여야 한다.
    frame_timeout: float = 300.0
    #: `FETCH` 한 프레임의 상한 [s].  **0 이면 크기에서 유도한다** (1 MiB/s
    #: 가정 · 최소 60초) -- 344 MiB 면 344초다.
    #:
    #: ⚠️ `frame_timeout` 과 **별개의 상한**이다.  독출(트리거→프레임 완료)을
    #: 조여 놔도 전송은 이 값이 따로 잡으므로, 링크가 느려졌을 때 아무도
    #: 알려주지 않는다.  실측(`tools/probe_archon.py` 3단계의 MiB/s)이 나오면
    #: 여기에 실측 기반 값을 적는다 -- 그게 미해결 F5 가 기다리는 것이다.
    fetch_timeout: float = 0.0
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
        for tag, chips in rawpair.CONTROLLERS:
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
    """값의 첫 토큰.  `10.0.0.13 (AC13A)` 처럼 뒤에 붙은 설명을 떼어낸다.

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

    ACF 경로는 관례상 상대경로(`acf/...`)지만 운영자가 `~/AICS/acf/...` 로 적을
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

    cfg.shutter_ctrl = _head(s, 'shutter_ctrl', cfg.shutter_ctrl).upper()
    if cfg.shutter_ctrl not in CTRLTAGS + ('BOTH',):
        raise ArchonConfigError(
            '[archon] shutter_ctrl 은 %s 중 하나여야 한다: %r'
            % (' / '.join(CTRLTAGS + ('both',)), cfg.shutter_ctrl))
    cfg.full_flush_on_erase = _bool(s, 'full_flush_on_erase',
                                    cfg.full_flush_on_erase)
    cfg.lock_buffer = _bool(s, 'lock_buffer', cfg.lock_buffer)
    cfg.frame_poll = _num(s, 'frame_poll', cfg.frame_poll, float)
    cfg.frame_timeout = _num(s, 'frame_timeout', cfg.frame_timeout, float)
    cfg.shutdown_drain = _num(s, 'shutdown_drain', cfg.shutdown_drain,
                              float)
    cfg.fetch_timeout = _num(s, 'fetch_timeout', cfg.fetch_timeout, float)
    cfg.progress_step = _num(s, 'progress_step', cfg.progress_step, int)

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
            '상한을 조여 놔도 전송에서 그만큼 매달린다.  실측 MiB/s 가 나오면 '
            'fetch_timeout 에 적을 것 (F5)' % (fetch_cap, cfg.frame_timeout))
    notes += _cross_checks(cfg, sim_cfg)
    return notes


def _cross_checks(cfg: ArchonCfg, sim_cfg) -> list[str]:  # noqa: ANN001
    """`ics_sim` 쪽 설정과 맞물려서만 위험해지는 조합.

    **한쪽만 보면 둘 다 정상인 값들**이라 각자의 `validate()` 로는 안 걸린다.
    """
    notes: list[str] = []
    if sim_cfg is None:
        return notes

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
    dead = []
    if sim_cfg.paths.write_fits:
        dead.append('[paths] write_fits(시뮬 전용)')
    if tuple(sim_cfg.paths.fits_shape) != (256, 256):
        dead.append('[paths] fits_shape(시뮬 전용)')
    if dead:
        notes.append('archon 백엔드가 보지 않는 설정이 바뀌어 있다: %s -- '
                     '실기 산출물에는 영향이 없다' % ', '.join(dead))
    return notes

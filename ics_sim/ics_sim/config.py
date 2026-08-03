#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration loading and validation.

모든 동작 파라미터는 ics_sim.ini 에서 편집한다.  주석 문자는 '#' 하나이고 줄
어디에나 올 수 있으며, '#' 앞의 내용은 유효하다 -- configparser 를
comment_prefixes/inline_comment_prefixes 로 그렇게 설정한다.

기동 시 [timing] 값이 OBSAgent 의 하드 타임아웃 창(DevNote 3.3)을 침범하지
않는지 자가검증한다.  침범하면 실제 OBSAgent 가 스크립트 관측을 멈추거나
경고를 띄우므로, 조용히 넘어가지 않고 경고를 남긴다.
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field

DEFAULT_INI = 'ics_sim.ini'


class ConfigError(Exception):
    """설정 파일이 구조적으로 잘못됐을 때."""


@dataclass
class NodeCfg:
    site: str = 'ctio'
    telid: str = 'KMTC'
    ics_id: str = 'ICS'
    ic_ids: tuple[str, ...] = ('K.IC', 'M.IC', 'T.IC', 'N.IC')
    cb_ids: tuple[str, ...] = ('K.CB', 'M.CB', 'T.CB', 'N.CB')
    master: str = 'K'
    guide_ic_id: str = 'G.IC'
    emit_node_mode: str = 'legacy'

    @property
    def ccds(self) -> tuple[str, ...]:
        """CCD 한 글자 이름들, ic_ids 순서 그대로."""
        return tuple(n.split('.', 1)[0] for n in self.ic_ids)

    def ic_of(self, ccd: str) -> str:
        return f'{ccd}.IC'

    def cb_of(self, ccd: str) -> str:
        return f'{ccd}.CB'

    @property
    def all_node_ids(self) -> tuple[str, ...]:
        """시뮬이 **수신**해야 하는 노드 ID 전부.

        OBSAgent 는 kstatus/dmawait/datasource 를 K.IC 등 개별 노드로 보낸다
        (DevNote 3.1).  ICS 하나만 등록하면 그 명령들이 도달하지 않는다.
        """
        return (self.ics_id,) + tuple(self.ic_ids) + tuple(self.cb_ids)


@dataclass
class TransportCfg:
    bind_host: str = '127.0.0.1'
    bind_port: int = 6600
    xis_host: str = ''
    xis_port: int = 6660
    send_gap_ms: float = 2.0
    peer_ttl_sec: float = 3600.0
    #: 기동 시 9개 노드 ID 전부로 PING 을 보내 XIS 에 등록할지 (DevNote 3.1.1).
    #: false 로 두면 ICS 만 등록되고 kstatus/dmawait/datasource 가 도달하지 않는다.
    #: XIS 가 같은 (IP,port) 의 다중 등록을 거부하는 것으로 밝혀지면 이 값을
    #: 끄는 대신 노드별 소켓(2안)으로 전환해야 한다.
    register_all_nodes: bool = True

    @property
    def xis_addr(self) -> tuple[str, int] | None:
        if not self.xis_host:
            return None
        return (self.xis_host, self.xis_port)


@dataclass
class PathsCfg:
    data_dir: str = './icsdata'
    write_fits: bool = False
    fits_shape: tuple[int, int] = (256, 256)


@dataclass
class TimingCfg:
    time_scale: float = 1.0
    go_to_initializing: float = 0.81
    initialize_ack: float = 0.40
    erase_sec: float = 7.24
    aux_relay_gap: float = 0.058
    tcs_relay_gap: float = 0.029
    shutter_open_delay: float = 0.15
    countdown_tick_dark: float = 5.00
    countdown_tick_shop: float = 5.217
    shutter_to_readout: float = 6.00
    acq_to_idle: float = 0.40
    write_delay: float = 3.40
    ccd_skew: tuple[float, ...] = (0.0, 0.6, 0.7, 1.6)
    ccd_skew_order: tuple[str, ...] = ('N', 'T', 'M', 'K')
    tc_query_timeout: float = 0.50
    tc_timeout_mode: str = 'passthrough'

    def skew_of(self, ccd: str) -> float:
        """CCD 별 디스크 저장 완료 시차."""
        try:
            return self.ccd_skew[self.ccd_skew_order.index(ccd)]
        except (ValueError, IndexError):
            return 0.0


@dataclass
class ReadoutCfg:
    pctread_start: int = 6
    pctread_step: int = 11
    pctread_tick: float = 3.37
    pctread_final: int = 100

    def steps(self) -> list[int]:
        """100 미만의 진행률 시퀀스.  실측: 6,17,28,...,94."""
        out: list[int] = []
        pct = self.pctread_start
        while pct < self.pctread_final:
            out.append(pct)
            pct += self.pctread_step
        return out


@dataclass
class ObsAgentCfg:
    """OBSAgent 쪽 상수.  시뮬이 직접 쓰진 않고 자가검증에만 쓴다."""

    tick_sec: float = 0.045
    force_idle: int = 40
    force_ready: int = 270
    force_fitssaved: int = 560

    @property
    def acq_window_sec(self) -> float:
        """1번째 -> 4번째 Acquisition Complete. 허용 시간."""
        return self.force_idle * self.tick_sec

    @property
    def idle_window_sec(self) -> float:
        """4번째 Acquisition Complete. -> EXPSTATUS=IDLE 허용 시간."""
        return (self.force_idle / 2) * self.tick_sec

    @property
    def fits_window_sec(self) -> float:
        """IDLE_3 -> 4번째 Wrote 허용 시간."""
        return self.force_fitssaved * self.tick_sec

    @property
    def ready_delay_sec(self) -> float:
        """IDLE_3 -> READY 강제 전이까지."""
        return self.force_ready * self.tick_sec


@dataclass
class BehaviorCfg:
    strict_legacy: bool = True
    bug_compat: bool = False
    send_guide_init: bool = True
    console: bool = True
    inject: frozenset[str] = frozenset()

    def injecting(self, fault: str) -> bool:
        return fault in self.inject


@dataclass
class HardwareCfg:
    backend: str = 'sim'


@dataclass
class LoggingCfg:
    level: str = 'info'
    wire: bool = True
    file: str = ''


@dataclass
class SimConfig:
    node: NodeCfg = field(default_factory=NodeCfg)
    transport: TransportCfg = field(default_factory=TransportCfg)
    paths: PathsCfg = field(default_factory=PathsCfg)
    timing: TimingCfg = field(default_factory=TimingCfg)
    readout: ReadoutCfg = field(default_factory=ReadoutCfg)
    obsagent: ObsAgentCfg = field(default_factory=ObsAgentCfg)
    behavior: BehaviorCfg = field(default_factory=BehaviorCfg)
    hardware: HardwareCfg = field(default_factory=HardwareCfg)
    logging: LoggingCfg = field(default_factory=LoggingCfg)

    source_path: str = ''

    # -- 시간 축척 --------------------------------------------------------

    def scaled(self, seconds: float) -> float:
        """time_scale 을 적용한 대기 시간."""
        return seconds * self.timing.time_scale

    # -- 자가검증 ---------------------------------------------------------

    def validate(self) -> list[str]:
        """설정이 스스로 모순되거나 OBSAgent 창을 침범하는지 검사.

        Returns:
            경고 문자열 목록 (비어 있으면 정상).  기동을 막지는 않는다 --
            일부러 창을 좁혀 경보 경로를 시험하는 것도 정당한 사용이기 때문이다.
        """
        warn: list[str] = []
        oa = self.obsagent
        t = self.timing

        if len(self.node.ic_ids) != len(self.node.cb_ids):
            raise ConfigError('ic_ids 와 cb_ids 개수가 다릅니다')
        if self.node.master not in self.node.ccds:
            raise ConfigError(f'master={self.node.master} 가 ic_ids 에 없습니다')
        if self.node.emit_node_mode not in ('legacy', 'merged'):
            raise ConfigError('emit_node_mode 는 legacy 또는 merged')
        if t.tc_timeout_mode not in ('passthrough', 'canned'):
            raise ConfigError('tc_timeout_mode 는 passthrough 또는 canned')
        if self.hardware.backend not in ('sim', 'archon'):
            raise ConfigError('backend 는 sim 또는 archon')

        # DevNote 3.3 (2): 4번째 Acquisition Complete. 이후 EXPSTATUS=IDLE 까지
        if t.acq_to_idle > oa.idle_window_sec:
            warn.append(
                f'acq_to_idle={t.acq_to_idle:.2f}s 가 OBSAgent 창 '
                f'{oa.idle_window_sec:.2f}s 를 넘습니다 -> '
                "WARNING: No 'EXPSTATUS=IDLE' message from ICS 가 뜹니다")

        # DevNote 3.3 (1): 4개 CCD 의 Acquisition Complete. 산포
        spread = max(t.ccd_skew) - min(t.ccd_skew) if t.ccd_skew else 0.0
        if spread > oa.acq_window_sec:
            warn.append(
                f'ccd_skew 산포 {spread:.2f}s 가 OBSAgent 창 '
                f'{oa.acq_window_sec:.2f}s 를 넘습니다 -> '
                'opause + ERROR: Acquisition is not fully completed 가 뜹니다')

        # DevNote 3.3 (3): IDLE_3 -> 4번째 Wrote
        last_write = t.acq_to_idle + t.write_delay + spread
        if last_write > oa.fits_window_sec:
            warn.append(
                f'마지막 Wrote 까지 {last_write:.2f}s 가 OBSAgent 창 '
                f'{oa.fits_window_sec:.2f}s 를 넘습니다 -> '
                'WARNING: Writing FITS data is not fully completed 가 뜹니다')

        if self.node.emit_node_mode == 'merged' and self.behavior.bug_compat:
            warn.append('merged 모드에서는 bug_compat 재현이 레거시 로그와 '
                        '일치하지 않습니다 (골든 대조는 legacy 모드로)')
        return warn


# ---------------------------------------------------------------------------
# ini 로딩
# ---------------------------------------------------------------------------

def _make_parser() -> configparser.ConfigParser:
    """'#' 만 주석으로 쓰고, 인라인 주석도 허용하는 파서."""
    return configparser.ConfigParser(
        comment_prefixes=('#',),
        inline_comment_prefixes=('#',),
        interpolation=None,
    )


def _bool(sec: configparser.SectionProxy, key: str, default: bool) -> bool:
    raw = sec.get(key, '').strip()
    if not raw:
        return default
    return raw.lower() in ('1', 'true', 'yes', 'on', 't')


def _floats(sec: configparser.SectionProxy, key: str,
            default: tuple[float, ...]) -> tuple[float, ...]:
    raw = sec.get(key, '').strip()
    if not raw:
        return default
    return tuple(float(x) for x in raw.split(',') if x.strip())


def _ints(sec: configparser.SectionProxy, key: str,
          default: tuple[int, ...]) -> tuple[int, ...]:
    raw = sec.get(key, '').strip()
    if not raw:
        return default
    return tuple(int(x) for x in raw.split(',') if x.strip())


def _words(sec: configparser.SectionProxy, key: str,
           default: tuple[str, ...]) -> tuple[str, ...]:
    raw = sec.get(key, '').strip()
    if not raw:
        return default
    return tuple(x.strip() for x in raw.split(',') if x.strip())


def load(path: str | None = None) -> SimConfig:
    """ini 파일을 읽어 SimConfig 로.  파일이 없으면 기본값."""
    cfg = SimConfig()
    if path is None:
        path = DEFAULT_INI
    if not os.path.exists(path):
        return cfg

    cp = _make_parser()
    with open(path, 'r', encoding='utf-8') as fh:
        cp.read_file(fh)
    cfg.source_path = os.path.abspath(path)

    if cp.has_section('node'):
        s = cp['node']
        n = cfg.node
        n.site = s.get('site', n.site).strip()
        n.telid = s.get('telid', n.telid).strip()
        n.ics_id = s.get('ics_id', n.ics_id).strip()
        n.ic_ids = _words(s, 'ic_ids', n.ic_ids)
        n.cb_ids = _words(s, 'cb_ids', n.cb_ids)
        n.master = s.get('master', n.master).strip()
        n.guide_ic_id = s.get('guide_ic_id', n.guide_ic_id).strip()
        n.emit_node_mode = s.get('emit_node_mode', n.emit_node_mode).strip().lower()

    if cp.has_section('transport'):
        s = cp['transport']
        t = cfg.transport
        t.bind_host = s.get('bind_host', t.bind_host).strip()
        t.bind_port = int(s.get('bind_port', str(t.bind_port)))
        t.xis_host = s.get('xis_host', t.xis_host).strip()
        t.xis_port = int(s.get('xis_port', str(t.xis_port)))
        t.send_gap_ms = float(s.get('send_gap_ms', str(t.send_gap_ms)))
        t.peer_ttl_sec = float(s.get('peer_ttl_sec', str(t.peer_ttl_sec)))
        t.register_all_nodes = _bool(s, 'register_all_nodes',
                                     t.register_all_nodes)

    if cp.has_section('paths'):
        s = cp['paths']
        p = cfg.paths
        p.data_dir = s.get('data_dir', p.data_dir).strip()
        p.write_fits = _bool(s, 'write_fits', p.write_fits)
        shape = _ints(s, 'fits_shape', p.fits_shape)
        if len(shape) == 2:
            p.fits_shape = (shape[0], shape[1])

    if cp.has_section('timing'):
        s = cp['timing']
        t = cfg.timing
        for name in ('time_scale', 'go_to_initializing', 'initialize_ack',
                     'erase_sec', 'aux_relay_gap', 'tcs_relay_gap',
                     'shutter_open_delay', 'countdown_tick_dark',
                     'countdown_tick_shop', 'shutter_to_readout',
                     'acq_to_idle', 'write_delay', 'tc_query_timeout'):
            setattr(t, name, float(s.get(name, str(getattr(t, name)))))
        t.ccd_skew = _floats(s, 'ccd_skew', t.ccd_skew)
        t.ccd_skew_order = _words(s, 'ccd_skew_order', t.ccd_skew_order)
        t.tc_timeout_mode = s.get('tc_timeout_mode', t.tc_timeout_mode).strip().lower()

    if cp.has_section('readout'):
        s = cp['readout']
        r = cfg.readout
        r.pctread_start = int(s.get('pctread_start', str(r.pctread_start)))
        r.pctread_step = int(s.get('pctread_step', str(r.pctread_step)))
        r.pctread_tick = float(s.get('pctread_tick', str(r.pctread_tick)))
        r.pctread_final = int(s.get('pctread_final', str(r.pctread_final)))

    if cp.has_section('obsagent'):
        s = cp['obsagent']
        o = cfg.obsagent
        o.tick_sec = float(s.get('tick_sec', str(o.tick_sec)))
        o.force_idle = int(s.get('force_idle', str(o.force_idle)))
        o.force_ready = int(s.get('force_ready', str(o.force_ready)))
        o.force_fitssaved = int(s.get('force_fitssaved', str(o.force_fitssaved)))

    if cp.has_section('behavior'):
        s = cp['behavior']
        b = cfg.behavior
        b.strict_legacy = _bool(s, 'strict_legacy', b.strict_legacy)
        b.bug_compat = _bool(s, 'bug_compat', b.bug_compat)
        b.send_guide_init = _bool(s, 'send_guide_init', b.send_guide_init)
        b.console = _bool(s, 'console', b.console)
        b.inject = frozenset(_words(s, 'inject', ()))

    if cp.has_section('hardware'):
        cfg.hardware.backend = cp['hardware'].get(
            'backend', cfg.hardware.backend).strip().lower()

    if cp.has_section('logging'):
        s = cp['logging']
        lg = cfg.logging
        lg.level = s.get('level', lg.level).strip().lower()
        lg.wire = _bool(s, 'wire', lg.wire)
        lg.file = s.get('file', lg.file).strip()

    return cfg

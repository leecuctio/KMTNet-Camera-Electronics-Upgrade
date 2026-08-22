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
import logging
import os
import re
from dataclasses import dataclass, field

DEFAULT_INI = 'ics_sim.ini'

#: IMPv2 노드 이름 규칙 (프로토콜 스펙 2.3절): 2~8자, A-Z 0-9 . _
_NODE_ID_RE = re.compile(r'^[A-Z0-9._]{2,8}$')
#: 노드 ID 로 쓰면 안 되는 이름.  AL/ALL 은 브로드캐스트 예약어, XIS 는 허브의
#: ServerID -- v2.9.1 허브에는 srcID==ServerID 방어가 없어서(xis/xis.md 6.3)
#: 거르는 책임이 전적으로 클라이언트 쪽에 있다.
_RESERVED_IDS = frozenset({'AL', 'ALL', 'XIS'})
#: site <-> TELID 정합 (D-011).  TELID 는 TC 텔레메트리 규약과 같고, 실기의
#: raw pair 물리 파일명 <SITE> prefix 로도 쓰인다 (raw spec 2.2절).
log = logging.getLogger('ics_sim.config')

_SITE_TELID = {'ctio': 'KMTC', 'saao': 'KMTS', 'sso': 'KMTA', 'testbed': 'KMTT'}


class ConfigError(Exception):
    """설정 파일이 구조적으로 잘못됐을 때."""


@dataclass
class NodeCfg:
    #: ini 에 **선언된** 사이트.  `site_from_ip` 가 켜져 있으면 실효 사이트는
    #: 호스트 IP 로 정해지고 이 값은 **대조용**으로만 남는다 (D-015).
    site: str = 'ctio'
    telid: str = 'KMTC'
    #: 호스트 IP 로 사이트를 판정할지 (기본 켬).
    #:
    #: **판정이 ini 를 이긴다.**  벤치에서 `site` 를 `sso` 로 두더라도 파일명은
    #: `KMTT.…` 여야 한다는 것이 요구사항이고(운영자 확정 2026-08-13), 그러려면
    #: 설정 밖에서 오는 신호가 이겨야 한다.  어긋나면 경고를 남긴다.
    #:
    #: **시험은 이걸 끈다** (`tests/conftest.py`) -- 켜 두면 판정이 시험을 돌리는
    #: 머신의 IP 에 좌우돼 기대 파일명이 흔들린다.
    site_from_ip: bool = True
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
    #: 같은 AL 브로드캐스트 원문이 이 시간(초) 안에 다시 오면 XIS 의 슬롯별
    #: 복사본으로 보고 버린다 (DevNote 3.1.2).  0 이하면 중복 억제를 끈다.
    broadcast_dedup_sec: float = 2.0

    @property
    def xis_addr(self) -> tuple[str, int] | None:
        if not self.xis_host:
            return None
        return (self.xis_host, self.xis_port)


@dataclass
class SiteCfg:
    """사이트 측지값 -- FITS `LATITUDE`/`LONGITUD`/`ELEVATIO`/`TELESCOP`.

    **좌표를 코드에 박지 않는 이유**: 레거시 실측본으로 확인된 것은 SSO 뿐이고
    (`LATITUDE='-31:16:24'` `LONGITUD='210:56:08'` `ELEVATIO=1150`), CTIO/SAAO
    값은 이 저장소 어디에도 없다.  추측한 좌표는 raw spec 6장이 경계하는 "조용히
    틀린 값" 그 자체가 된다 -- **겉보기엔 유효한 좌표라 아무도 의심하지 않는다.**
    설정으로 받고, 없으면 sentinel 을 싣는다 (raw spec 5.3절).

    `LONGITUD` 는 레거시 관례대로 **서경**(`[deg W]`)이다 -- SSO 의
    `210:56:08` 이 동경 `149:03:52` 의 보수다.  동경으로 적으면 부호가 뒤집힌
    좌표가 아카이브에 박힌다.
    """

    latitude: str = ''
    longitud: str = ''
    elevatio: int = -1
    telescop: str = ''
    #: FITS `ORIGIN` 덮어쓰기.  비우면 사이트 유도값(`rawpair.ORIGIN_OF` --
    #: 관측소 raw = 관측소명, 테스트베드 = `KASI`, 운영자 확정 2026-08-21).
    origin: str = ''

    def as_dict(self) -> dict:
        """`rawhdr.site_header()` 에 넘길 형태.  **빈 값은 빼고 넘긴다** --
        실측 표(`rawhdr.VERIFIED_SITES`)를 지우지 않게 하기 위해서다."""
        out = {}
        if self.latitude:
            out['latitude'] = self.latitude
        if self.longitud:
            out['longitud'] = self.longitud
        if self.elevatio >= 0:
            out['elevatio'] = self.elevatio
        if self.telescop:
            out['telescop'] = self.telescop
        if self.origin:
            out['origin'] = self.origin
        return out


@dataclass
class CameraCfg:
    """FITS `DETECTOR`·`CAMVER`·`INSTRUME`·`FPAID` -- `ICS INI` 출처 카드.

    **`ICS INI` 출처 카드는 전부 ini 에서 수정할 수 있어야 한다** (운영자 지시
    2026-08-22).  빈 값이면 `rawhdr` 의 기본(상수 또는 사이트 유도값)을 쓴다.
    `CAMVER` 는 **HW·성능상 변경이 있을 때만 올리는** 전자부 세대 참조점이고
    4.3절 포장 규범 조항의 고정 대상(`CAMVER`+`CTRLxCFG`)이다.
    """

    detector: str = ''
    camver: str = ''
    instrume: str = ''
    fpaid: str = ''

    def as_dict(self) -> dict:
        """`rawhdr.instrument_header()` 오버라이드.  빈 값은 빼고 넘긴다."""
        return {k: v for k, v in (('detector', self.detector),
                                  ('camver', self.camver),
                                  ('instrume', self.instrume),
                                  ('fpaid', self.fpaid)) if v}


@dataclass
class ControllersCfg:
    """FITS `CTRL1*`/`CTRL2*` -- 컨트롤러 정체 · 설정 포인터 (`ICS INI` 카드).

    빈 값이면 백엔드 보고값(sim 의 고정 목록, 실기는 Archon SYSTEM 응답)을
    쓰고, **채워져 있으면 INI 가 이긴다** -- 현장이 정본이라는 `[site]` 와
    같은 원칙이다.  실값 원자료는 `raw_fits_spec/__reference/
    Archon_Unit_Info.txt` (예: KMTA SCI-101=STA-0288 · SCI-102=STA-0289,
    ID 숫자 = IP).  `ctrl<n>_cfg` 는 적용된 Archon 설정 파일명
    (`CTRL<n>CFG` 카드) -- 타이밍·바이어스·클럭 버전은 이 파일로 귀속된다
    (Header_and_Refs 3.3절).
    """

    ctrl1_id: str = ''
    ctrl1_sn: str = ''
    ctrl1_cfg: str = ''
    ctrl2_id: str = ''
    ctrl2_sn: str = ''
    ctrl2_cfg: str = ''
    #: FITS `RDMODE`(독출 모드 선언, raw spec 5.5절).  비면 코드 기본
    #: `NORMAL`.  MEF `READMODE`(`'64AMP'`, 구조 선언)와 **별개**다.
    rdmode: str = ''

    def overrides(self) -> dict[int, dict]:
        """`rawhdr.controller_header()` 오버라이드 -- 색인(1=MK, 2=NT)별
        `{'id','sn','cfg'}`.  빈 값은 빼고 넘긴다."""
        out: dict[int, dict] = {}
        for n in (1, 2):
            ov = {k: v for k, v in (
                ('id', getattr(self, f'ctrl{n}_id')),
                ('sn', getattr(self, f'ctrl{n}_sn')),
                ('cfg', getattr(self, f'ctrl{n}_cfg'))) if v}
            if ov:
                out[n] = ov
        return out


@dataclass
class PathsCfg:
    data_dir: str = './icsdata'
    write_fits: bool = False
    fits_shape: tuple[int, int] = (256, 256)
    #: 마지막으로 쓴 EXPNUM 을 적어 두는 파일.  비워 두면 **설정파일 옆**에
    #: 같은 이름 `.expnum` 으로 자동 결정된다(resolve_expnum_file) -- 벤치에서
    #: `-c ~/AICS/Config/ics_sim.ini` 로 띄우면 `~/AICS/Config/ics_sim.expnum`.
    #:
    #: `data_dir` 와 분리해 둔 것이 요구사항이다: 저장 파일을 지우거나 옮겨도
    #: 번호는 되돌아가지 않아야 한다(운영자 확정 2026-08-11, DevNote 11.12).
    expnum_file: str = ''


@dataclass
class TimingCfg:
    time_scale: float = 1.0
    go_to_initializing: float = 0.81
    initialize_ack: float = 0.40
    erase_sec: float = 7.24
    aux_relay_gap: float = 0.058
    tcs_relay_gap: float = 0.029
    shutter_open_delay: float = 0.15
    #: `SHOPEN` 지시 후 이 시간이 지나면 `AUXSTATUS` 를 **다시 질의**해 헤더의
    #: 셔터 상태를 갱신한다 (운영자 확정 2026-08-13).  `0` 이하면 갱신하지 않는다.
    #:
    #: **왜 필요한가**: 프레임 개시의 AUXSTATUS 는 `SHOPEN` 보다 8초 이상 앞서
    #: 질의되므로(`initialize_ack` + `erase_sec`) 헤더의 `SHUTTER` 가 노출과
    #: 무관한 값이 된다 -- 레거시 실측이 `IMAGETYP='OBJECT'`·`EXPTIME=30` 프레임에
    #: `SHUTTER='CLOSED'` 를 남긴 것이 그 증거다.
    #:
    #: ⚠️ **기본값 3초는 블레이드 주행(5초) 중간이다.**  그 시점에는
    #: `SHUTOP='OPENING'` 이고 `SHUTTER` 는 리밋 스위치가 아직 안 트립했을 수
    #: 있다(`CLOSED`/`UNKNOWN`).  운영자는 `SHUTOP='OPENING'` 으로 충분하다고
    #: 확정했다.  Full/Half 2중 블레이드 중 Full 리밋이 더 일찍 트립하는지는
    #: 모르므로 **벤치 실측으로 조정할 수 있게 설정값으로 뺐다** (raw spec OI-13).
    aux_requery_after_shopen: float = 3.0
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
class AuxControlCfg:
    """KMTNet AUX control software 와의 TCP 연동 (auxcontrol.py).

    규격: `TCSAgent/__reference/KMTNet AUX control remote commands(v20140908).pdf`

    키 이름은 TCSAgent 의 `pctcs.kmtn*.ini` 와 맞췄다 -- **같은 AUX 서버를
    가리키므로** 두 설정을 나란히 놓고 비교할 수 있어야 한다:

        # AUX control server info
        AUX_Host   127.0.0.1 (Local)
        AUX_Port   5752
        AUX_TelID  KMTNET
        AUX_SysID  AUX

    실제 사이트 설정은 `192.168.14.60`(KMTNC) · `192.168.13.60`(KMTNS) ·
    `192.168.15.60`(KMTNA) 처럼 사이트망의 `.60` 이다.  규격 문서의
    `192.168.24.10` 은 작성 시점 값이라 현행과 다르다.  기본값은 `127.0.0.1`
    로 둔다 -- 로컬 시험이 기본이고, 현장에서는 명시적으로 채워야 한다.

    **값 뒤의 괄호 주석을 허용한다.** `pctcs` 쪽이 `192.168.14.60 (KMTNC)` 처럼
    적어 두므로, 그 형식을 그대로 붙여넣어도 되도록 첫 토큰만 취한다.

    **보낼 커맨드는 기본값이 비어 있다.** AUX 프로토콜에는 "카메라 셔터를
    열어라"에 해당하는 명령이 없다 -- 카메라 셔터는 HE 박스의 TTL 신호로
    구동되고 AUX 는 `FILTERS LIMIT_SHUT` 으로 상태를 읽기만 한다(문서 4-2).
    그래서 무엇을 보낼지는 운영에서 정할 값이고, 비어 있으면 아무것도 보내지
    않는다.
    """

    enabled: bool = False
    host: str = '127.0.0.1'
    port: int = 5752
    #: 문서 2-4 -- 이 값이 틀리면 서버는 **응답 자체를 하지 않는다**
    telescope_id: str = 'KMTNET'
    system: str = 'AUX'
    #: 패킷 ID 접두어.  뒤에 1씩 올라가는 번호가 붙는다 (`ICS1`, `ICS2`, ...).
    packet_prefix: str = 'ICS'
    #: 비우지 않으면 **이 값을 고정으로** 쓴다 (예: 운영 관례가 `00` 인 경우).
    #: 고정하면 응답 대조가 느슨해지므로 기본은 증가 번호다.
    packet_id: str = ''

    connect_timeout: float = 3.0
    ack_timeout: float = 1.0
    reconnect_sec: float = 2.0
    reconnect_max_sec: float = 30.0
    #: true 면 성공(OK)도 콘솔에 찍는다.  기본은 실패만 눈에 띄게.
    verbose: bool = False

    #: 접속 직후 1회 (예: ALL / ECHO hello).  비우면 생략
    hello_subsystem: str = ''
    hello_command: str = ''

    #: 셔터 개방·폐쇄 시 보낼 <SUBSYSTEM> <COMMAND> (2026-08-05 지정):
    #:     KMTNET AUX 00 FILTERS SET_SH OPEN
    #:     KMTNET AUX 00 FILTERS SET_SH CLOSE
    #:
    #: **이 경로는 하드웨어 트리거의 시뮬레이션용 대체물이다.**  실제 시스템에는
    #: 셔터를 여닫는 SW 명령이 없다 -- HE 박스의 TTL 신호가 그 역할을 하고,
    #: AUX 는 `LIMIT_SHUT` 으로 상태를 읽기만 한다(규격 4-2).  `SET_SH` 는
    #: 하드웨어 없이 시험하려고 AUX 쪽에 새로 넣은 명령이라 v20140908 문서에
    #: 없다.  실기(archon 백엔드)로 넘어가면 TTL 이 이 자리를 대신하므로
    #: `enabled = false` 로 꺼야 한다.
    shopen_subsystem: str = 'FILTERS'
    shopen_command: str = 'SET_SH OPEN'
    shclose_subsystem: str = 'FILTERS'
    shclose_command: str = 'SET_SH CLOSE'


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
    #: `[site.<이름>]` 섹션들을 **사이트 코드로 키잉**해 담는다.  실효 사이트가
    #: 기동 시점에 정해지므로(IP 판정) 설정 읽기 단계에서 하나를 고를 수 없다 --
    #: 전부 읽어 두고 `site_for()` 로 꺼낸다.
    site_table: dict[str, SiteCfg] = field(default_factory=dict)
    #: `[site]` 섹션.  선택된 사이트 값을 **덮어쓴다** -- 현장이 정본이다.
    site_override: SiteCfg = field(default_factory=SiteCfg)
    #: `[camera]` -- `DETECTOR`/`CAMVER`/`INSTRUME` (ICS INI 카드).
    camera: CameraCfg = field(default_factory=CameraCfg)
    #: `[controllers]` -- `CTRL1*`/`CTRL2*` 정체 · 설정 포인터 (ICS INI 카드).
    controllers: ControllersCfg = field(default_factory=ControllersCfg)
    timing: TimingCfg = field(default_factory=TimingCfg)
    readout: ReadoutCfg = field(default_factory=ReadoutCfg)
    obsagent: ObsAgentCfg = field(default_factory=ObsAgentCfg)
    behavior: BehaviorCfg = field(default_factory=BehaviorCfg)
    hardware: HardwareCfg = field(default_factory=HardwareCfg)
    auxcontrol: AuxControlCfg = field(default_factory=AuxControlCfg)
    logging: LoggingCfg = field(default_factory=LoggingCfg)

    source_path: str = ''

    def site_for(self, site_code: str) -> dict:
        """그 사이트의 측지값 (`rawhdr.site_header()` 에 넘길 형태).

        `[site.<이름>]` 을 읽고 `[site]` 로 덮는다.  빈 값은 넘기지 않으므로
        `rawhdr.VERIFIED_SITES` 의 기본값이 살아남는다.
        """
        out = dict(self.site_table.get(site_code.upper(), SiteCfg()).as_dict())
        out.update(self.site_override.as_dict())
        return out

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

        # site <-> telid 정합 (D-011).  telid 는 AUXSTATUS 응답값이자 실기
        # (ics_archon) raw pair 물리 파일명의 <SITE> prefix 가 되므로, 설정
        # 오배포(예: CTIO ini 를 SAAO 에 배포)가 여기서 잡히지 않으면 잘못된
        # 사이트 코드가 아카이브 파일명에 영구히 박힌다 (raw spec 2.2절).
        expected_telid = _SITE_TELID.get(self.node.site.lower())
        if expected_telid is None:
            raise ConfigError(
                f'site={self.node.site!r} 는 ctio/saao/sso/testbed 중 하나여야 '
                '합니다')
        if self.node.telid.upper() != expected_telid:
            raise ConfigError(
                f'site={self.node.site} 와 telid={self.node.telid} 가 어긋납니다 '
                f'(기대값 {expected_telid}, D-011)')

        # 노드 ID 검증.  v2.9.1 허브는 이름을 전혀 검사하지 않으므로(주소
        # 충돌 검사도, ServerID 사칭 방어도 없음 -- xis/xis.md 6.3) 잘못된
        # 이름이 그대로 클라이언트 테이블에 올라가 라우팅을 오염시킨다.
        ids = [i.upper() for i in self.node.all_node_ids]
        for nid in ids:
            if not _NODE_ID_RE.match(nid):
                raise ConfigError(
                    f'노드 ID {nid!r} 가 IMPv2 이름 규칙(2~8자, A-Z 0-9 . _)에 '
                    '어긋납니다')
        if len(set(ids)) != len(ids):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            raise ConfigError(f'노드 ID 가 중복됩니다: {", ".join(dup)}')
        bad = _RESERVED_IDS.intersection(ids)
        if bad:
            raise ConfigError(
                f'노드 ID 로 예약어를 쓸 수 없습니다: {", ".join(sorted(bad))} '
                '(AL/ALL 은 브로드캐스트, XIS 는 허브 ServerID)')
        if self.node.guide_ic_id and self.node.guide_ic_id.upper() in ids:
            raise ConfigError(
                f'guide_ic_id={self.node.guide_ic_id} 가 수신 노드 ID 와 '
                '겹칩니다')
        if self.node.emit_node_mode not in ('legacy', 'merged'):
            raise ConfigError('emit_node_mode 는 legacy 또는 merged')
        if t.tc_timeout_mode not in ('passthrough', 'canned'):
            raise ConfigError('tc_timeout_mode 는 passthrough 또는 canned')
        if self.hardware.backend not in ('sim', 'archon'):
            raise ConfigError('backend 는 sim 또는 archon')

        # AUX 의 SET_SH 는 HW 트리거의 시뮬레이션용 대체물이다.  실기에서는
        # HE 박스의 TTL 이 셔터를 구동하므로, 둘을 함께 켜면 구동원이 둘이 된다.
        if self.hardware.backend == 'archon' and self.auxcontrol.enabled:
            warn.append(
                'backend=archon 인데 [auxcontrol] enabled=true 입니다 -> '
                '실기에서는 HE 박스 TTL 이 셔터를 구동하므로 '
                'AUX SET_SH 와 구동원이 겹칩니다.  끄는 것이 맞는지 확인하세요')

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


def _head(sec: configparser.SectionProxy, key: str, default: str) -> str:
    """공백으로 끊어 **첫 토큰만** 돌려준다.

    TCSAgent 의 `pctcs.kmtn*.ini` 가 값 뒤에 설명을 괄호로 붙여 둔다 --
    `AUX_Host   192.168.14.60 (KMTNC)`.  그 형식을 그대로 복사해 넣어도
    동작하도록 뒤쪽을 버린다.
    """
    raw = sec.get(key, '').strip()
    if not raw:
        return default
    return raw.split()[0]


def _text_or(sec: configparser.SectionProxy, key: str, default: str) -> str:
    """비어 있으면 기본값.  **내부 공백은 보존한다.**

    `sec.get(key, default).strip()` 을 그대로 쓰면 **키가 있고 값이 빈 경우**
    (`telescop =`) 기본값이 아니라 빈 문자열로 덮인다.  `[site.<코드>]` 를
    `[site]` 로 덮는 구조에서 이게 실제로 문제였다 -- 비워 둔 덮어쓰기 섹션이
    사이트 값을 지웠다.

    `_head()` 와 달리 첫 토큰만 취하지 않는다 -- `TELESCOP = 'KMTNet 1.6m #1'`
    처럼 공백이 값의 일부인 항목에 쓴다.
    """
    raw = sec.get(key, '').strip()
    # **값에 '#' 가 들어가면 ini 에 `\#` 로 적어야 한다.**  이 파서는 앞에 공백이
    # 있는 '#' 를 인라인 주석으로 보므로(`_make_parser`)
    # `telescop = KMTNet 1.6m #1` 이 `KMTNet 1.6m` 으로 잘린다 -- 실제로 그렇게
    # 잘렸다.  따옴표로 감싸도 소용없다(파서가 주석을 먼저 떼서
    # `"KMTNet 1.6m` 이 남는다).  '#' 앞이 공백이 아니면 주석으로 보지 않으므로
    # `\#` 가 통과하고, 여기서 백슬래시를 벗긴다.
    raw = raw.replace('\\#', '#')
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
        raw = raw[1:-1].strip()
    return raw if raw else default


def _int_or(sec: configparser.SectionProxy, key: str, default: int) -> int:
    """비어 있거나 숫자가 아니면 기본값.

    `sec.getint(key, default)` 는 **값이 빈 문자열이면 그냥 터진다** --
    `ValueError: invalid literal for int() with base 10: ''`.  주석만 남기고
    비워 둔 설정 항목이 흔하므로(예: `[site] elevatio =`) 그걸로 기동이
    막히면 안 된다.  "값이 없음" 은 오류가 아니라 sentinel 로 가는 경로다.
    """
    raw = sec.get(key, '').strip()
    if not raw:
        return default
    try:
        return int(raw.split()[0])
    except ValueError:
        log.warning('[%s] %s=%r 를 정수로 읽을 수 없다 -- 기본값 %r 을 쓴다',
                    sec.name, key, raw, default)
        return default


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
        n.site_from_ip = _bool(s, 'site_from_ip', n.site_from_ip)
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
        t.broadcast_dedup_sec = float(s.get('broadcast_dedup_sec',
                                            str(t.broadcast_dedup_sec)))

    if cp.has_section('paths'):
        s = cp['paths']
        p = cfg.paths
        p.data_dir = s.get('data_dir', p.data_dir).strip()
        p.write_fits = _bool(s, 'write_fits', p.write_fits)
        p.expnum_file = s.get('expnum_file', p.expnum_file).strip()
        raw_shape = s.get('fits_shape', '').strip().lower()
        if raw_shape in ('spec', 'full'):
            # raw spec 3장의 실물 chip 크기 (rows, cols) -- 파일은 chip 2개를
            # X 로 이어 붙여 19200x9400 이 된다 (hardware/sim.py).
            p.fits_shape = (9400, 9600)
        else:
            shape = _ints(s, 'fits_shape', p.fits_shape)
            if len(shape) == 2:
                p.fits_shape = (shape[0], shape[1])

    # 사이트 측지값.  **`[site.<이름>]` 전부를 표로 읽고 `[site]` 는 따로 둔다.**
    #
    # 하나를 골라 담지 않는 이유: 실효 사이트가 **기동 시점에 호스트 IP 로**
    # 정해지므로(D-015) 설정 읽기 단계에는 아직 모른다.  전부 읽어 두면
    # `site_for()` 가 나중에 꺼낼 수 있고, `[node] site` 한 줄을 고쳐 다른
    # 사이트에 배포해도 좌표가 따라온다.
    def _read_site(sec: configparser.SectionProxy) -> SiteCfg:
        t = SiteCfg()
        # 위도/경도는 공백이 없는 형식(`-30:10:01.84`)이라 첫 토큰만 취해도 안전.
        t.latitude = _head(sec, 'latitude', t.latitude)
        t.longitud = _head(sec, 'longitud', t.longitud)
        t.elevatio = _int_or(sec, 'elevatio', t.elevatio)
        # `telescop` 은 **공백이 값의 일부**다 (`KMTNet 1.6m #1`).
        t.telescop = _text_or(sec, 'telescop', t.telescop)
        t.origin = _head(sec, 'origin', t.origin)
        return t

    for section in cp.sections():
        if not section.lower().startswith('site.'):
            continue
        name = section.split('.', 1)[1].strip().lower()
        code = _SITE_TELID.get(name)
        if code is None:
            log.warning('[%s] 는 알 수 없는 사이트 이름이라 무시한다 -- '
                        'ctio/saao/sso/testbed 중 하나여야 한다', section)
            continue
        cfg.site_table[code] = _read_site(cp[section])
    if cp.has_section('site'):
        cfg.site_override = _read_site(cp['site'])

    if cp.has_section('camera'):
        s = cp['camera']
        c = cfg.camera
        c.detector = _text_or(s, 'detector', c.detector)
        c.camver = _head(s, 'camver', c.camver)
        # `instrume` 은 공백이 값의 일부다 (`KMTA 18k CCD`).
        c.instrume = _text_or(s, 'instrume', c.instrume)
        c.fpaid = _head(s, 'fpaid', c.fpaid)

    if cp.has_section('controllers'):
        s = cp['controllers']
        c = cfg.controllers
        for key in ('ctrl1_id', 'ctrl1_sn', 'ctrl1_cfg',
                    'ctrl2_id', 'ctrl2_sn', 'ctrl2_cfg', 'rdmode'):
            setattr(c, key, _head(s, key, getattr(c, key)))

    if cp.has_section('timing'):
        s = cp['timing']
        t = cfg.timing
        for name in ('time_scale', 'go_to_initializing', 'initialize_ack',
                     'erase_sec', 'aux_relay_gap', 'tcs_relay_gap',
                     'shutter_open_delay', 'aux_requery_after_shopen',
                     'countdown_tick_dark',
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

    if cp.has_section('auxcontrol'):
        s = cp['auxcontrol']
        a = cfg.auxcontrol
        a.enabled = _bool(s, 'enabled', a.enabled)
        # 키 이름은 pctcs.kmtn*.ini 의 AUX_* 와 같게 두었다(같은 서버를 가리킨다).
        # 값 뒤의 "(KMTNC)" 같은 괄호 주석은 _head() 가 떼어낸다.
        a.host = _head(s, 'aux_host', a.host)
        a.telescope_id = _head(s, 'aux_telid', a.telescope_id)
        a.system = _head(s, 'aux_sysid', a.system)
        try:
            a.port = int(_head(s, 'aux_port', str(a.port)))
        except ValueError:
            raise ConfigError(
                f'[auxcontrol] AUX_Port 를 숫자로 읽을 수 없다: '
                f'{s.get("aux_port", "")!r}') from None

        a.packet_prefix = _head(s, 'packet_prefix', a.packet_prefix)
        a.packet_id = _head(s, 'packet_id', a.packet_id)
        a.verbose = _bool(s, 'verbose', a.verbose)
        a.connect_timeout = s.getfloat('connect_timeout', a.connect_timeout)
        a.ack_timeout = s.getfloat('ack_timeout', a.ack_timeout)
        a.reconnect_sec = s.getfloat('reconnect_sec', a.reconnect_sec)
        a.reconnect_max_sec = s.getfloat('reconnect_max_sec',
                                         a.reconnect_max_sec)
        for key in ('hello', 'shopen', 'shclose'):
            raw = s.get(f'{key}_cmd', '').strip()
            if not raw:
                continue
            head, _, rest = raw.partition(' ')
            setattr(a, f'{key}_subsystem', head.strip())
            setattr(a, f'{key}_command', rest.strip())

    if cp.has_section('logging'):
        s = cp['logging']
        lg = cfg.logging
        lg.level = s.get('level', lg.level).strip().lower()
        lg.wire = _bool(s, 'wire', lg.wire)
        lg.file = s.get('file', lg.file).strip()

    resolve_expnum_file(cfg)
    return cfg


def resolve_expnum_file(cfg: SimConfig) -> str:
    """`[paths] expnum_file` 이 비어 있으면 **설정파일 옆**으로 정한다.

    벤치 배치(`~/AICS/{bin,Config,Logs,data}`)에서 지속 카운터를 둘 자리는
    `Config/` 다 -- `Logs/` 는 비워지고 `data/` 는 요구사항상 배제된다(저장
    파일과 무관해야 한다).  설정파일 이름을 따르므로 `-c` 로 여러 구성을
    나란히 돌려도 카운터가 섞이지 않는다:

        ~/AICS/Config/ics_sim.ini  ->  ~/AICS/Config/ics_sim.expnum

    `source_path` 가 비어 있으면(ini 없이 SimConfig() 를 직접 만든 경우 --
    단위 테스트가 그렇다) 빈 값으로 남겨 **지속시키지 않는다.**  테스트가
    실행 순서에 따라 서로의 카운터를 물려받지 않게 하려는 것이다.
    """
    p = cfg.paths
    if p.expnum_file:
        p.expnum_file = os.path.expanduser(p.expnum_file)
    elif cfg.source_path:
        p.expnum_file = os.path.splitext(cfg.source_path)[0] + '.expnum'
    return p.expnum_file

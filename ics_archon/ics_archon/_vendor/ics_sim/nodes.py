#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Node identity and inbound routing.

신규 ics 는 레거시의 9개 노드(ICS + K/M/T/N.IC + K/M/T/N.CB)를 한 프로그램에
통합한다.  안에서는 하나지만 **바깥에서는 9개 이름 전부로 메시지를 받아야
한다** -- OBSAgent 가 kstatus/dmawait/datasource 를 K.IC 등 개별 노드 주소로
보내기 때문이다 (DevNote 3.1).  ICS 하나로만 등록하면 그 명령들은 도달조차
하지 않는다.

반대로 **발신** 쪽은 자유롭다.  OBSAgent 의 CamStatus 필터는 발신자가
ICS / {K,M,T,N}.IC / {K,M,T,N}.CB 중 하나이기만 하면 통과시키므로, 통합 노드가
전부 'ICS' 이름으로 보내도 된다(emit_node_mode=merged).  이 수신/발신 비대칭이
신규 설계에서 놓치기 쉬운 지점이라 여기 명시해 둔다.

발신 노드 화이트리스트는 두지 않는다.  IMPv2 에 노드 인증 개념이 없고, 실제
로그에도 문서화되지 않은 클라이언트(CHA, C1 -- DevNote 6.3)가 명령을 보낸다.
프로토콜에 맞는 메시지면 누가 보냈든 처리하고 요청자에게 응답한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .config import NodeCfg
from .impv2 import BROADCAST, Message


class Role(Enum):
    """수신 노드의 역할."""

    ICS = 'ics'      # 카메라 통합 제어
    IC = 'ic'        # CCD 별 디바이스 제어
    CB = 'cb'        # CCD 별 디스크/전송 컨트롤러
    GUIDE = 'guide'  # G.IC -- 범위 밖, 무응답
    OTHER = 'other'  # 우리 앞으로 온 게 아님


@dataclass(frozen=True)
class Target:
    """수신 메시지가 어느 내부 주체로 가는지."""

    role: Role
    ccd: str = ''       # IC/CB 일 때 CCD 한 글자
    node_id: str = ''   # 응답 시 src 로 쓸 이름

    @property
    def is_ours(self) -> bool:
        return self.role in (Role.ICS, Role.IC, Role.CB)


class NodeRouter:
    """dest 필드를 보고 내부 주체를 찾아준다."""

    def __init__(self, cfg: NodeCfg) -> None:
        self.cfg = cfg
        self._map: dict[str, Target] = {}

        self._map[cfg.ics_id.upper()] = Target(Role.ICS, node_id=cfg.ics_id)
        for ic in cfg.ic_ids:
            ccd = ic.split('.', 1)[0]
            self._map[ic.upper()] = Target(Role.IC, ccd=ccd, node_id=ic)
        for cb in cfg.cb_ids:
            ccd = cb.split('.', 1)[0]
            self._map[cb.upper()] = Target(Role.CB, ccd=ccd, node_id=cb)
        if cfg.guide_ic_id:
            self._map[cfg.guide_ic_id.upper()] = Target(
                Role.GUIDE, node_id=cfg.guide_ic_id)

    # -- 조회 -------------------------------------------------------------

    def resolve(self, msg: Message) -> Target:
        """이 메시지를 처리할 내부 주체.

        브로드캐스트(AL/ALL)는 ICS 가 대표로 받는다 -- PING 처럼 노드 하나가
        답하면 되는 out-of-band 메시지가 대부분이기 때문이다.
        """
        dst = msg.dst.upper()
        if dst in BROADCAST:
            return Target(Role.ICS, node_id=self.cfg.ics_id)
        return self._map.get(dst, Target(Role.OTHER))

    def owns(self, node_id: str) -> bool:
        t = self._map.get(node_id.upper())
        return t is not None and t.is_ours

    @property
    def registered_ids(self) -> tuple[str, ...]:
        """XIS 에 등록할(=수신할) 노드 ID 전부."""
        return self.cfg.all_node_ids

    # -- 발신 이름 --------------------------------------------------------

    def emit_id(self, role: Role, ccd: str = '') -> str:
        """이 역할이 발신할 때 쓸 src 이름.

        emit_node_mode=merged 면 전부 ICS 이름으로 낸다.  OBSAgent 의 CamStatus
        필터는 그래도 통과한다(DevNote 3.2).  merged 는 통합 노드다운 형태이고,
        legacy 는 레거시 로그와 골든 대조가 가능한 형태다.
        """
        if self.cfg.emit_node_mode == 'merged':
            return self.cfg.ics_id
        if role is Role.IC and ccd:
            return self.cfg.ic_of(ccd)
        if role is Role.CB and ccd:
            return self.cfg.cb_of(ccd)
        return self.cfg.ics_id

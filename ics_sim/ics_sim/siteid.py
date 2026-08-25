#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""호스트 IP 로 사이트를 판정한다.

**왜 IP 인가.** `[node] site` 한 줄이 사이트 코드 → 좌표 → 관측일 경계 → 파일명
까지 전부 끌고 가므로(D-011·D-014), 그 한 줄이 틀리면 **아무 오류 없이** 전부
틀린다.  설정 묶음을 통째로 잘못 복사하면 안에 있는 어떤 값으로도 그걸 잡을 수
없다 -- 잡으려면 **설정 밖에서** 오는 신호가 필요하다.

호스트 자기 주소가 그 신호다.  우리가 배포하는 어떤 ini 에도 없고, OS·네트워크
에서 온다.  설정을 복사해도 IP 는 따라오지 않는다.

**TC 의 `TELID` 는 이 자리에 못 쓴다** -- 그 값은 `pctcs.ini` 의 `FITS_TELID`
설정이고(`commands.c:1999` → `aux.FitsTelID`, `loadconfig.c:512-514`) 기본값이
사이트가 아닌 `KMTN`(`pctcs.h:115`)이다.  즉 또 하나의 수동 설정이라, 같은
사람이 같은 실수를 할 수 있다.  다만 **독립된 두 번째 설정이라 교차검증에는
쓸모가 있다** -- `check_telid()` 참고.

**레거시도 IP 로 사이트를 갈랐다** (`ics_legacy_report.md:763`):

    if( strcasecmp(client.isisHost,"192.168.15.109") ) {  // SSO 가 아니면

그리고 우리 보고서가 그걸 이미 비판해 뒀다(`:784`) -- **호스트 IP 를 통째로
박아서**, SSO 의 XIS 주소가 바뀌면 갑자기 매 노출 경고가 떴다.  그래서 여기서는
**/24 대역**으로 본다.  호스트의 마지막 옥텟은 보지 않는다.
"""

from __future__ import annotations

import ipaddress
import logging
import socket

log = logging.getLogger('ics_sim.siteid')

#: 사이트 /24 대역 → 사이트 코드.
#:
#: **대역 매핑 자체는 근거가 여러 갈래로 확인됐다:**
#:
#:   * 각 사이트 자기 `isis.ini` 의 `Instrument` 키워드 --
#:     `ics_legacy/__dts_legacy/dts.icsci.20190326.{ctio,saao,sso}/dts.icsci/
#:     Config/isis.ini` (`KMTC`/`KMTS`/`KMTA`)
#:   * `TCSAgent/TCSAgent.latest/KMTNet/ini/pctcs.kmtn{c,s,a}.ini` --
#:     `ISISHost 192.168.14.109` + `FITS_TelID KMTC` 식으로 세 사이트가 같은 꼴
#:   * `OBSAgent/OBSAgent.latest/KMTObs/ini/test.debug.ini:35-37` -- 세 대역 범례
#:   * `ics_legacy/icg_legacy_report.md:47`
#:
#: ⚠️ **신규 CEU 망이 이 대역을 그대로 쓴다는 것은 운영자 구두 확인(2026-08-13)
#: 뿐이다.**  저장소에 CEU 망을 서술한 문서가 없다 -- `project_management/` 전체를
#: IPv4 로 훑어도 0건이다.  그래서 이 표는 *verified* 가 아니라 *inferred* 다.
#: 망이 바뀌면 여기와 배포 체크리스트를 함께 고쳐야 한다.
#:
#: ⚠️ **인터페이스가 보고하는 netmask 를 쓰지 않는다.**  13/14/15 가 인접해서
#: 누군가 /22 로 잡아 두면 **세 사이트가 한 망으로 합쳐진다.**  literal /24
#: 프리픽스로만 비교한다.  netmask 근거는 저장소에 아예 없다.
#:
#: ⚠️ **호스트 옥텟은 보지 않는다.**  레거시의 역할-옥텟 지도(x.109=XIS/OBS,
#: x.102~.105=IC …)는 **신규에서 무효다** -- 머신 7대가 2대로 통합됐다
#: (`Inst. Ctrl.` = OBSAgent + 신규 `ics`, `Inst. Bakup` = TCSAgent,
#: DevNote 9.1).  옥텟 화이트리스트를 만들면 그 통합 때문에 바로 틀린다.
SITE_SUBNETS: tuple[tuple[str, str], ...] = (
    ('192.168.14.0/24', 'KMTC'),   # CTIO
    ('192.168.13.0/24', 'KMTS'),   # SAAO
    ('192.168.15.0/24', 'KMTA'),   # SSO
)

#: 알려진 대역이 하나도 안 걸리면 벤치/테스트베드다 (운영자 확정 2026-08-13).
#:
#: 테스트베드는 `192.168.x.x` 를 쓰지 않는다는 것을 운영자가 확인해 줬고,
#: 벤치는 사이트 이름 설정을 `kmtnet-sso`/`kmtnet-ctio`/`kmtnet-saao`/
#: `kmtnet-kasi`/`kmtnet-helab` 등 무엇으로 두더라도 **파일명은 항상
#: `KMTK.…`** 여야 한다.  그래서 판정이 ini 를 이긴다.
#:
#: `192.168.x.x` 인데 13/14/15 가 아닌 경우도 벤치로 본다(운영자 확정).
#: 실제 사이트에 우리가 모르는 세그먼트가 있다면 **ini 의 `site` 와 어긋나므로
#: `resolve()` 의 경고가 그걸 드러낸다** -- 조용히 지나가지 않는다.
#: **D-017 (2026-08-25)**: 구 `KMTT`(TESTBED)를 `KMTK`(KASI)가 대체한다.
BENCH_SITE = 'KMTK'

#: 대역별 탐침 목표.  UDP `connect()` 는 **패킷을 보내지 않는다** -- 커널
#: 라우팅 테이블만 조회해 출발 주소를 고른다.  hostname 에 등록되지 않은 NIC
#: (다중 NIC 머신에서 흔하다)를 이 방법으로 잡는다.
_PROBE_TARGETS = tuple(str(ipaddress.ip_network(net).network_address + 1)
                       for net, _ in SITE_SUBNETS)


def local_ipv4s() -> tuple[str, ...]:
    """이 호스트의 IPv4 주소 전부.  **stdlib 만, 패킷 없이, 블로킹 없이.**

    **하나를 고르지 않고 전부 모으는 것이 요점이다.** 신규 호스트는 확실히
    multi-homed 다 -- Archon 망이 `10.0.0.0/24` 로 실재하고
    (`cam_char/archon/campaign_example.ini:15` `host = 10.0.0.13`), 거기에 기기망과
    캠퍼스망이 더해진다.  "primary 주소 하나" 방식은 그래서 못 쓴다 -- 어느 것이
    잡히는지가 OS 의 인터페이스 순서에 좌우된다.

    두 경로를 합친다:

    1. `getaddrinfo(hostname)` -- hostname 에 등록된 주소.
    2. 대역별 UDP `connect()` 후 `getsockname()` -- 라우팅 테이블이 그 대역으로
       나갈 때 쓰는 출발 주소.  그 대역에 붙은 NIC 이 있으면 그 주소가 나오고,
       없으면 기본 경로의 주소가 나와 **대역 검사에서 자연히 탈락한다.**

    루프백은 버린다 -- 판정 근거가 못 된다.  link-local(`169.254.x`)은 남겨
    두지만 어떤 사이트 대역에도 안 걸린다.

    네트워크가 아예 없는 노트북에서는 빈 튜플에 가까운 값이 나오고, 그때
    `resolve()` 는 **"정보 없음"** 으로 처리한다 -- 오탐이 아니다.
    """
    found: set[str] = set()

    try:
        host = socket.gethostname()
    except OSError:                              # pragma: no cover
        host = ''
    if host:
        try:
            for info in socket.getaddrinfo(host, None, socket.AF_INET):
                found.add(info[4][0])
        except OSError:
            # hostname 이 안 풀리는 환경(컨테이너 등)에서 흔하다.  탐침 쪽이
            # 남아 있으므로 치명적이지 않다.
            log.debug('getaddrinfo(%r) 실패 -- 탐침만으로 판정한다', host)

    for target in _PROBE_TARGETS:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(0)               # 어떤 경우에도 기다리지 않는다
                sock.connect((target, 9))        # discard 포트, 전송 없음
                found.add(sock.getsockname()[0])
        except OSError:
            # 경로가 없으면 여기로 온다 -- 정상이다.
            continue

    return tuple(sorted(a for a in found if not a.startswith('127.')))


def site_of(addrs: tuple[str, ...]) -> tuple[str, str]:
    """주소 목록 → `(사이트 코드, 근거 문구)`.

    알려진 대역에 걸리는 주소가 하나라도 있으면 그 사이트다.  없으면 벤치다.

    Returns:
        `('KMTC', '192.168.14.109 in 192.168.14.0/24')` 같은 쌍.  근거 문구는
        배너와 경고에 그대로 싣는다 -- **판정을 사람이 되짚을 수 있어야 한다.**
    """
    for net_str, code in SITE_SUBNETS:
        net = ipaddress.ip_network(net_str)
        for addr in addrs:
            try:
                if ipaddress.ip_address(addr) in net:
                    return code, f'{addr} in {net_str}'
            except ValueError:                   # pragma: no cover
                continue
    if not addrs:
        return BENCH_SITE, '주소를 얻지 못했다 (네트워크 없음)'
    return BENCH_SITE, f'알려진 사이트 대역 없음 ({", ".join(addrs)})'


def detect() -> tuple[str, str]:
    """`(사이트 코드, 근거 문구)`.  `local_ipv4s()` + `site_of()`."""
    return site_of(local_ipv4s())

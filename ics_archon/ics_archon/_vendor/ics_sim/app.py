#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Application wiring.

9개 노드(ICS + K/M/T/N.IC + K/M/T/N.CB)를 한 프로세스에서 대표한다.  수신은
9개 ID 전부로 받고(그래야 OBSAgent 의 kstatus/dmawait/datasource 가 도달한다),
발신 이름은 emit_node_mode 에 따라 노드별 또는 전부 ICS 로 낸다 (DevNote 3.1).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Awaitable

from . import rawhdr, rawpair
from .auxcontrol import AuxControlClient
from .commands import Dispatcher
from .config import SimConfig
from .emitter import Emitter
from .hardware import make_backend
from .impv2 import Message
from .nodes import NodeRouter, Role
from .sequencer import Sequencer
from .state import IcsState
from .telemetry import TelemetryRelay
from .transport import UdpEndpoint

log = logging.getLogger('ics_sim.app')


def _disp_width(text: str) -> int:
    """터미널에서 차지하는 칸 수.  **한글·한자는 두 칸이다.**

    `f'{label:<14}'` 는 문자 수로 세므로 한글 라벨이 든 표가 어긋난다.
    stdlib 만으로 맞추려면 East Asian Width 를 보면 된다.
    """
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1
               for c in text)


class IcsSim:
    """시뮬레이터 본체."""

    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg
        self.router = NodeRouter(cfg.node)
        # `site_code` 는 파일명 `<YYYYMMDD>`(사이트별 관측일)와 헤더 정체성에
        # 함께 쓰인다.  `config.load()` 가 `[node] observatory` 를 검증해 유도한
        # 값이다 -- 넷 밖의 값은 설정 단계에서 기동 거부라 조용한 강등이 없다
        # (D-020 · D-017, raw spec 2.2절).
        site, self.site_why = self._resolve_site()
        self.state = IcsState(expnum_file=cfg.paths.expnum_file,
                              site_code=site)
        # 마지막으로 쓴 EXPNUM 을 이어받는다 -- 재실행에도 번호가 되돌아가지
        # 않는 것이 요구사항이다 (state.load_expnum, DevNote 11.12)
        self.state.load_expnum()
        self.state.init_channels(cfg.node.ccds)
        self.state.guide_build = ''

        #: 응답·보고에 붙은 **조치** -- `(mtype, cmdword) -> 함수`.
        #: ⭐ 등록되지 않은 보고는 **실행하지 않고 알리기만** 한다
        #: (운영자 지시 2026-09-06).  `register_report()` 참고.
        self._reports: dict = {}
        self.transport = UdpEndpoint(cfg, self._on_message)
        self.emit = Emitter(cfg, self.router, self.transport.send)
        self.telem = TelemetryRelay(cfg, self._send_query)
        # TC 의 TELID 를 실효 사이트와 대조하게 한다 (D-020 이 유지한 검사).
        self.telem.site_code = site
        self.backend = make_backend(cfg)
        self.aux = AuxControlClient(cfg.auxcontrol)
        self.seq = Sequencer(cfg, self.state, self.emit, self.router,
                             self.telem, self.backend, self.aux)
        self.dispatch = Dispatcher(self)

        self._tasks: set[asyncio.Task] = set()
        #: 마지막 브로드캐스트 (원문, 수신 시각) -- XIS 가 등록 슬롯마다 한 부씩
        #: 복사해 보내는 중복 사본을 걸러낸다 (DevNote 3.1.2)
        self._last_broadcast: tuple[str, float] = ('', 0.0)

    def _resolve_site(self) -> tuple[str, str]:
        """실효 사이트 코드와 그 근거.

        **`[node] observatory` 한 값이 정한다** (운영자 지시 2026-08-24).
        `config.load()` 가 이미 그 값을 검증하고 `telid`/`site` 를 유도해
        두었으므로 여기서는 읽어 오기만 한다 -- 모르는 값이면 설정 읽기
        단계에서 이미 거부됐다.

        ⚠️ 종전에는 **호스트 IP 판정(D-015)이 ini 를 이겼다.**  그 경로는
        폐지했다: NIC 가 내려가거나 낯선 대역에 붙으면 실제 관측 자료가
        `KMTK.…` 이름으로 저장되는 위험이 있었고, 그것을 막는 대가로 "설정이
        맞는데도 판정이 이긴다" 는 반대 위험을 안고 있었다.  이제는 설정
        한 줄이 정본이고, 대신 그 값이 **틀리면 기동이 멈춘다.**
        """
        n = self.cfg.node
        return n.telid, f'[node] observatory={n.observatory}'


    # -- 생명주기 ---------------------------------------------------------

    async def start(self) -> None:
        for note in self.cfg.validate():
            log.warning('config: %s', note)
        if self.cfg.transport.xis_addr is not None:
            # XIS 는 같은 노드 ID 로 메시지가 오면 (IP,port) 를 확인 없이
            # 덮어쓴다.  운영 허브에 레거시 ICS/IC 가 살아 있는 채로 붙으면
            # 등록하는 순간 그쪽 라우팅을 가로챈다 (xis/xis.md 7절).
            log.warning(
                'XIS 허브 %s:%d 에 연결합니다 -- 운영 허브라면 레거시 ICS/IC '
                '계통(및 isisrelay)을 먼저 정지하세요.  같은 노드 ID 등록이 '
                '레거시의 라우팅을 즉시 가로챕니다 (xis/xis.md 7절)',
                *self.cfg.transport.xis_addr)
        await self.transport.start()
        await self.aux.start()
        self.register()
        self._warn_if_real_frames_would_be_labelled_bench()
        self.log_identity_banner()
        log.info('ICS simulator ready -- nodes: %s, backend=%s',
                 ', '.join(self.router.registered_ids), self.backend.name)

    def _warn_if_real_frames_would_be_labelled_bench(self) -> None:
        """실물 컨트롤러인데 사이트가 `KMTK`(KASI) 인 경우 (D-011 · D-017).

        **이 조합만 조용히 넘어갈 수 있어서 따로 잡는다.**  사이트가 `KMTK` 면
        보통은 정말 실험실이고 시뮬 프레임이라 문제가 없다.  그런데 백엔드가
        `archon` 이면 **실화소가 `KMTK.…` 이름으로 아카이브에 들어간다** --
        사이트 정체를 영구히 잃는 경로다.

        사이트는 이제 `[node] observatory` 한 줄이 정하므로(2026-08-24) 오배포는
        **그 줄 하나가 틀린 것**이다.  실물 백엔드로 KASI 이름을 달고 찍는
        상황이 그 증상이다.

        시뮬 백엔드에서는 아무 말도 하지 않는다 -- 실험실이 조용해야 사람이
        경고를 무시하는 것을 학습하지 않는다.
        """
        if self.state.site_code != rawpair.KASI_SITE:
            return
        # ⚠️ **여기는 `self.backend` 를 그대로 본다** (배너의 훅이 아니다) --
        # ICG 는 이 스텁이 늘 `sim` 이라 이 갈래를 **안 탄다**.  guide 실기에도
        # 같은 경고를 울릴지는 아직 안 정했다: 벤치가 KASI 이고 `KMTK` 가
        # **맞는 사이트**라 매번 뜨면 오경보가 된다 (운영자 판단 대기).
        if rawhdr.datasrc_of(self.backend.name) == rawhdr.DATASRC_SIM:
            return
        log.warning(
            '사이트가 %s(KASI/실험실)인데 백엔드가 실물 %r 이다 -- **실화소가 '
            '%s.… 이름으로 저장된다.**  관측소 장비라면 [node] observatory 가 '
            'KASI 로 남아 있는 것이니 CTIO/SSO/SAAO 중 맞는 값으로 고칠 것.  '
            '자료를 찍기 전에 확인할 것 (D-017)',
            rawpair.KASI_SITE, self.backend.name, rawpair.KASI_SITE)

    def banner_example(self, site: str, suffix: str) -> str:
        """배너의 **파일명 예시**.  ⭐ 앱이 갈아 끼운다.

        ⛔ 기반은 science 다 (`MK`).  guide 는 `.G.fits` 라 그대로 두면 배너가
        **거짓말한다** -- 벤치 첫 구동에서 `KMTK.20260908.000001.MK.fits` 가
        찍혔다(2026-09-08 실측).  배너의 목적이 *"자료 한 장 찍기 전에 사람 눈에
        띄게"* 인데, 정작 그 한 줄이 틀리면 목적을 잃는다.
        """
        return rawpair.physical_name(site, suffix, rawpair.CONTROLLERS[0][0])

    def banner_backend(self) -> str:
        """배너의 **백엔드 이름**.  ⭐ 앱이 갈아 끼운다.

        ⛔ ICG 는 `cfg.hardware.backend` 를 `'sim'` 으로 **일부러 눌러 둔다**
        (부모가 만드는 science 스텁의 경고를 막으려고).  그래서 이 값을 그대로
        찍으면 **실기로 도는데 배너가 `sim` 이라고 말한다** -- 벤치 첫 전원
        인가에서 실제로 그랬다(2026-09-08).  ⚠️ 배너의 목적이 *"배포가 맞는지
        여기서 확인"* 인데 그 줄이 틀리면 목적을 잃는다.
        ⛔ **설정값이 아니라 백엔드 객체의 이름**을 준다 -- 둘은 다른 물건이고,
        한때 이 자리가 설정값이었다 (2026-09-08 반쪽 고침).
        """
        return self.backend.name

    def banner_datasrc(self) -> str:
        """배너의 **`DATASRC`**.  ⭐ 앱이 갈아 끼운다.

        ⛔ **이름과 같은 자리에서 나와야 한다.**  앞 고침이 이름만 갈아 끼우고
        이 값은 눌린 스텁(`self.backend`)에서 뽑아, 벤치 배너가
        `archon_guide   ->  DATASRC=SIM` 이라는 **자기모순**을 찍었다
        (2026-09-08).  ⚠️ 한 줄 안에서 앞뒤가 어긋나면 둘 다 못 믿게 된다.
        ⚠️ guide 는 어휘가 따로다 (`guidehdr.datasrc_of`) -- science 표에는
        `archon_guide` 가 없어 여기서 부르면 *"모르는 백엔드"* 경고까지 난다.
        """
        return rawhdr.datasrc_of(self.banner_backend())

    def banner_instrument(self, site: str) -> dict:
        """배너가 `FPAID` 를 꺼내는 자리.  ⭐ 앱이 갈아 끼운다.

        ⚠️ guide 는 `guidehdr.instrument_header()` 로 **다른 함수**다.  값이
        지금 같은 것은 둘이 같은 사이트 유도를 쓰기 때문이고(OI-24 종결),
        갈리면 배너만 조용히 틀린다.
        """
        return rawhdr.instrument_header(rawpair.CONTROLLERS[0][0], site,
                                        self.cfg.camera.as_dict())

    def log_identity_banner(self) -> None:
        """기동 시 **사이트 정체를 한 덩어리로** 남긴다.

        **오배포를 자료 한 장 찍기 전에 사람 눈에 띄게 하는 것이 목적이다.**
        `[node] observatory` 한 줄이 사이트 코드 -> 좌표 -> 관측일 경계 ->
        파일명 -> `INSTRUME` -> `TELESCOP`/`FPAID` 까지 전부 끌고 가므로
        (D-011·D-014·D-017), 그 한 줄이 틀리면 **아무 오류 없이** 전부 틀린다.  헤더에 `OBSERVAT`/좌표가 남으니 사후 탐지는 가능하지만,
        그때는 이미 아카이브에 들어가 있다 -- 그래서 **t=0 에 보여주는 쪽**이
        런타임 검사보다 값싸고 확실하다.

        파일명 예시를 함께 찍는 이유: 운영자가 실제로 확인해야 하는 것이
        "이 이름으로 아카이브에 들어가도 되나" 이기 때문이다.  설정값 나열보다
        완성된 이름 한 줄이 오배포를 더 빨리 드러낸다.

        `DATASRC` 를 넣은 이유: 시뮬 산출물이 실제 아카이브로 흘러드는 것을
        막는 유일한 카드이므로(규격 5.5절), 기동 때 그 값을 보고 넘어가게 한다.
        """
        cfg, st = self.cfg, self.state
        site = st.site_code
        geo = rawhdr.observatory_header(site, cfg.site_for(site))
        instr = self.banner_instrument(site)
        suffix = f'{st.obs_date()}.{st.expnum:06d}'
        example = self.banner_example(site, suffix)

        def known(card: str) -> bool:
            """sentinel 이 아닌 실제 값인가 (규격 5.0절: 문자열 `NC`, 정수 `-1`)."""
            v = geo[card]
            return str(v) != 'NC' and v != -1

        if known('LATITUDE'):
            where = (f'lat {geo["LATITUDE"]}   lon {geo["LONGITUD"]} (서경)'
                     f'   elev {geo["ELEVATIO"]} m')
        else:
            # 값이 없을 때 `elev -1 m` 처럼 sentinel 을 단위와 함께 보여주면
            # 실제 측정값처럼 읽힌다.  없다고 말하는 편이 낫다.
            where = '(설정 없음 -- 헤더에 sentinel 이 실린다)'

        boundary = rawpair.boundary_ut(site)
        obsday = (f'UT {boundary}   -- 파일명 <YYYYMMDD> 가 이 경계로 갈린다'
                  if boundary != '(없음)' else
                  'UT 날짜 그대로 (KASI 는 관측 야간 개념이 없다)')

        rows = [
            ('사이트', f'{site}   (OBSERVAT='
                       f'{rawpair.OBSERVAT.get(site, "?")})'),
            ('근거', getattr(self, 'site_why', '(없음)')),
            ('TELESCOP', str(geo['TELESCOP'])),
            # `FPAID` 도 사이트가 정한다 (raw spec 5.3.1절, D-017 항목 6) --
            # 사이트를 바꾸면 **조용히 따라오는** 값이라 배너에 세운다.
            # ⚠️ 망원경 번호와 FPA 번호는 관측소 셋 모두 어긋나는 것이 정상이다.
            ('FPAID', str(instr['FPAID']).strip()),
            ('위치', where),
            ('관측일 경계', obsday),
            ('파일명 예시', example),
            # **풀어낸 절대경로를 보여준다.**  상대경로(`../data`)는 **실행한
            # 디렉터리** 기준으로 풀리고 `~` 는 펼쳐지므로, 적어 둔 문자열만
            # 보여 주면 자료가 실제로 어디에 쌓이는지 알 수 없다 -- 배너의
            # 목적은 "자료 한 장 찍기 전에 사람 눈에 띄게" 다.
            ('data_dir', os.path.abspath(cfg.paths.data_dir)
                         + ('' if os.path.isabs(cfg.paths.data_dir)
                            else f'   (설정 {cfg.paths.data_dir!r} · cwd 기준)')),
            ('EXPNUM', f'다음 {st.expnum:06d}'
                       f'   (기록 {st.expnum_file or "지속 없음"})'),
            ('backend', f'{self.banner_backend()}'
                        f'   ->  DATASRC={self.banner_datasrc()}'),
        ]

        width = 74
        lines = ['=' * width,
                 ' 사이트 정체 -- 배포가 맞는지 여기서 확인하세요',
                 '-' * width]
        lines += [f' {label}{" " * max(1, 15 - _disp_width(label))}{value}'
                  for label, value in rows]
        lines.append('=' * width)
        # 여러 줄을 **한 번의 로그 호출**로 낸다 -- 줄마다 부르면 다른 태스크의
        # 로그가 사이에 끼어 덩어리가 깨진다.
        log.info('\n%s', '\n'.join(lines))

    def register(self) -> None:
        """XIS 에 노드를 등록한다 -- 수신하려는 **9개 ID 전부**로 PING 을 보낸다.

        IMPv2 에는 등록 API 가 없다.  노드가 자기 이름으로 아무 메시지나 보내면
        XIS 가 "노드ID -> (IP,port)" 를 기억하는 것이 전부다.  ICS 이름으로만
        보내면 K.IC 앞으로 오는 kstatus/dmawait/datasource 가 도달하지 않는다
        (DevNote 3.1.1).

        **9개 ID 가 같은 (IP,port) 를 가리켜도 안전하다** -- 2026-08-04 에 XIS
        서버 소스로 확인했다.  클라이언트 테이블은 노드 ID 로만 키잉되고
        (`strcmp` 로 ID 만 비교, 주소는 갱신만 한다) 주소 충돌 검사 자체가 없다.
        브로드캐스트 코드도 *"clients that share the same port as the sending
        host"* 를 명시적으로 다룬다.  한때 검토하던 "노드마다 소켓을 따로
        여는 방식(2안)"은 불필요하다 -- 논의 전 과정은 xis/xis.md 부록 A.
        """
        if not self.cfg.transport.register_all_nodes:
            self.emit.register_ping(self.cfg.node.ics_id)
            log.warning('register_all_nodes=false -- %s 만 등록합니다. '
                        'kstatus/dmawait/datasource 는 도달하지 않습니다',
                        self.cfg.node.ics_id)
            return
        for node_id in self.router.registered_ids:
            self.emit.register_ping(node_id)

    async def stop(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
        await self.aux.stop()
        await self.transport.stop()

    def spawn(self, coro: Awaitable) -> asyncio.Task:
        """부수 작업을 백그라운드로 돌린다 (참조를 유지해 GC 를 막는다)."""
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    # -- 수신 -------------------------------------------------------------

    def _send_query(self, dest: str, cmdword: str) -> None:
        """TelemetryRelay 가 TC 에 질의할 때 쓰는 콜백."""
        self.emit.emit_req(dest, cmdword)

    #: 응답·보고 메시지 종류 (IMPv2 7종 중 명령이 아닌 것).  ⭐ 파서가
    #: 대문자로 정규화하므로 대소문자를 여기서 신경 쓰지 않아도 된다.
    REPORT_TYPES = ('DONE', 'STATUS', 'ERROR', 'WARNING', 'FATAL')

    def register_report(self, mtype: str, cmdword: str, fn) -> None:  # noqa: ANN001
        """응답·보고에 **조치**를 붙인다 -- 예: `register_report('DONE', 'HKDATA', …)`.

        ⭐ **등록하지 않은 보고는 실행되지 않고 로그로만 나간다** (운영자 지시
        2026-09-06).  그것이 이 경로를 연 이유다: *내가 보낸 명령의 답은 받되,
        모르는 보고에 답을 되쏘지 않는다.*

        ⚠️ 조치 함수는 `(msg, target)` 를 받고 **답을 보내지 않는다.**  보고에
        답하면 두 노드가 서로 보고를 주고받는 고리가 생긴다.
        """
        self._reports[(mtype.upper().rstrip(':'), cmdword.upper())] = fn

    def _on_message(self, msg: Message, addr) -> None:  # noqa: ANN001
        # 자기 발신 에코부터 버린다.  XIS 경유 모드에서는 시퀀서가 K.IC 등
        # 자기 노드 앞으로 보낸 INITIALIZE/ERASE/SHOPEN/GO 가 허브를 돌아
        # 그대로 되돌아온다 -- 클라이언트 테이블의 K.IC 주소가 우리 자신이기
        # 때문이다.  걸러내지 않으면 명령이 이중 실행된다 (DevNote 3.1.2).
        # 내부 실행은 발신 전에 이미 끝났으므로 에코는 버리는 것이 맞다.
        if self.router.owns(msg.src):
            log.debug('self-echo dropped: %s', msg.raw)
            return

        # AL 브로드캐스트는 XIS 가 등록 슬롯마다 한 부씩 복사한다 -- 9개 ID 로
        # 등록한 우리에게는 같은 데이터그램이 최대 9부 도착한다 (v2.9.1 은
        # 송신 슬롯 하나만 제외한다, xis/xis.md 6.3).  첫 부만 처리한다.
        if msg.is_broadcast:
            now = time.monotonic()
            last_raw, last_seen = self._last_broadcast
            if (msg.raw == last_raw and
                    now - last_seen <= self.cfg.transport.broadcast_dedup_sec):
                log.debug('duplicate broadcast dropped: %s', msg.raw)
                return
            self._last_broadcast = (msg.raw, now)

        # TC 응답부터 걸러낸다 -- 우리가 먼저 질의한 것에 대한 답이다.
        if msg.mtype == 'DONE' and msg.src.upper() == 'TC':
            if self.telem.on_tc_reply(msg):
                return

        target = self.router.resolve(msg)

        if target.role is Role.GUIDE:
            # G.IC 는 범위 밖이다.  ICG 가 별도 프로그램으로 존재하므로 여기서
            # 답하면 오히려 충돌한다.
            return
        if not target.is_ours:
            return

        if msg.mtype in ('REQ', 'EXEC'):
            self.dispatch.handle(msg, target)
            return

        # ⭐ **응답·보고를 다 받는다** (운영자 지시 2026-09-06) -- `DONE`·
        # `STATUS`·`ERROR`·`WARNING`·`FATAL`.  대소문자는 파서가 이미 정규화했다
        # (`impv2.parse_line` 의 `head.upper().rstrip(':')`).
        #
        # ⛔ **조치가 등록된 것만 실행하고, 나머지는 알리기만 한다.**  여기서
        # `dispatch.handle()` 로 흘리면 미등록 커맨드워드에 `Didn't understand …`
        # ERROR 를 **남의 노드로 되쏜다** (DevNote 11.12 F1) -- 레거시의 메시지
        # 오염과 같은 부류라 이 프로그램이 존재하는 이유에 어긋난다.
        #
        # ⚠️ 그래서 이 갈래는 **어떤 경우에도 답을 보내지 않는다.**
        fn = self._reports.get((msg.mtype, (msg.cmdword or '').upper()))
        if fn is not None:
            try:
                fn(msg, target)
            except Exception:  # noqa: BLE001  조치 하나가 수신 루프를 죽이지 않는다
                log.exception('report handler %s %s failed',
                              msg.mtype, msg.cmdword)
            return
        # 조치가 없다 -- **출력만** 한다.  운영자가 자기가 낸 명령의 답과
        # 남의 노드가 흘리는 경고를 눈으로 볼 수 있어야 한다.
        log.info('보고 수신 (조치 없음) -- %s>%s %s: %s %s',
                 msg.src, msg.dst, msg.mtype, msg.cmdword, msg.payload)

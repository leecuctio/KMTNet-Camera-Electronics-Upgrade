#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""icg 조립 -- `ics_sim.IcsSim` 을 상속하고 guide 몫을 갈아 끼운다.

`ics_archon.app.IcsArchon` 과 같은 상속 골격이되 갈아 끼우는 폭이 넓다:

* **시퀀서** -- science 노출 상태기 대신 `GuideSequencer` (frame-transfer).
* **디스패처** -- `IcgDispatcher` (+`GUIEXP`/`HK`/`RADIONODE`).
* **백엔드** -- `GuideBackend`(실기) / `SimGuideBackend`(메시지 층 회귀).
  `ics_sim` 의 `DetectorBackend` 계약을 쓰지 않으므로 `make_backend()` 경로
  밖이다 -- 부모가 만든 science 시퀀서·백엔드는 버려진다 (아래 주석).
* **HK 감시** (1분) + **Radionode 폴러** -- 기동에서 띄운다.

노드 정체는 ini 가 정한다 -- `[node] ics_id=ICG · ic_ids=G.IC · cb_ids=G.CB ·
master=G · guide_ic_id=` (빈 값!  기본 `G.IC` 를 지우지 않으면 라우터가
자기 IC 를 "범위 밖 guide" 로 무시한다 -- `nodes.Role.GUIDE`).
"""

from __future__ import annotations

import logging

from ics_archon import _simpath

_simpath.ensure()

from ics_sim import console  # noqa: E402
from ics_sim.app import IcsSim  # noqa: E402

from ics_sim import rawpair  # noqa: E402

from . import build_id, guidehdr, guidepair  # noqa: E402
from . import commands as icg_commands  # noqa: E402
from .backend import GuideBackend, SimGuideBackend  # noqa: E402
from .config import TAG, IcgCfg, validate  # noqa: E402
from . import gauge as gauge_mod  # noqa: E402
from .expenable import ExpEnable  # noqa: E402
from .gauge import GaugeState  # noqa: E402
from .hk import HkMonitor  # noqa: E402
from .radionode import RadionodeClient  # noqa: E402
from .sequencer import GuideSequencer  # noqa: E402

log = logging.getLogger('icg_archon.app')


class IcgArchon(IcsSim):
    """실기 ICG 본체."""

    def __init__(self, cfg, icfg: IcgCfg, *,  # noqa: ANN001
                 backend: str = 'icg_archon') -> None:
        icg_commands.extend_vocabulary()
        # 부모가 science 백엔드·시퀀서를 만든다 -- guide 는 그 계약 밖이라
        # 아래에서 통째로 갈아 끼우고, 부모 몫은 쓰지 않는다.  `sim` 으로
        # 고정해 두는 이유: `archon` 스텁이 만들어지며 내는 경고를 막는다.
        cfg.hardware.backend = 'sim'
        super().__init__(cfg)
        self.icfg = icfg
        self.backend_name = backend
        self.state.ics_build = build_id()      # 배너·STATUS 응답용
        # ⛔ **백엔드를 만들기 전에 검사한다** (2026-09-08, 벤치 실측).
        # 종전에는 `start()` 에서 했는데, 그때는 `GuideBackend.__init__` 이 이미
        # ACF 를 읽어 본 뒤라 **경고가 치명적 오류보다 먼저** 찍혔다:
        #     Warning: guide ACF 를 못 읽어 … ini 기본값을 쓴다   <- "계속 간다" 는 투
        #     IcgConfigError: [icg] acf=… 가 없다                  <- 그런데 죽는다
        # 읽는 사람이 경고를 보고 "기본값으로라도 도는구나" 했다가 곧 죽는 것을
        # 본다.  없는 파일은 **한 줄로** 죽는 것이 맞다.
        for line in validate(icfg, backend):
            log.warning('%s', line)
        if backend == 'icg_archon':
            self.guide = GuideBackend(cfg, icfg)
        else:
            self.guide = SimGuideBackend(cfg, icfg)
        #: 노출 잠금 -- 지속 플래그.  `IcgDispatcher.cmd_go` 가 이것을
        #: 본다.  ⚠️ 경로가 비면 지속되지 않는다(단위 시험).
        self.expenable = ExpEnable(icfg.expenable_path(cfg))
        #: 이온게이지 켜짐 상태 -- `VACGAUGE` 가 움직이고 `HkMonitor` 가 본다.
        #: ⭐ 꺼진 것을 아는 동안 `DEWPRES` 를 sentinel 로 내리기 위한 것이다
        #: (게이지를 끄면 모듈이 Conductron 값을 계속 내보내는데 그것이
        #: 정상값처럼 보인다 -- `gauge.py` 머리말).
        self.gauge = GaugeState(icfg.gauge_off_method)
        self.radionode = RadionodeClient(icfg.radionode)
        self.hk = HkMonitor(self.guide.ctrl, icfg, telem=self.telem,
                            expstatus=lambda: self.state.expstatus,
                            spawn=self.spawn)
        self.hk.radionode = self.radionode
        self.hk.gauge = self.gauge
        self.seq = GuideSequencer(cfg, icfg, self.state, self.emit,
                                  self.telem, self.guide, self.hk)
        self.dispatch = icg_commands.IcgDispatcher(self)

    # -- 기동 배너 ----------------------------------------------------------

    def banner_example(self, site: str, suffix: str) -> str:
        """guide 는 `.G.fits` 다 -- 기반의 science `.MK.fits` 를 갈아 끼운다."""
        return rawpair.physical_name(site, suffix, guidepair.TAG)

    def banner_backend(self) -> str:
        """⛔ `cfg.hardware.backend` 는 `'sim'` 으로 눌러 둔 값이다 -- guide 의
        진짜 백엔드는 `self.guide` 다.  안 갈아 끼우면 실기인데 `sim` 이라 찍는다."""
        return self.guide.name

    def banner_instrument(self, site: str) -> dict:
        """guide 의 instrument 블록 -- `guidehdr` 가 정본이다 (`rawhdr` 아님)."""
        return guidehdr.instrument_header(site, self.cfg.camera.as_dict())

    # -- 콘솔 도움말 --------------------------------------------------------

    def console_help(self):  # noqa: ANN201
        """기반 명령 + **guide 몫**  (운영자 지시 2026-09-07).

        ⚠️ 기반 절의 IC 레벨 명령은 상속으로 **살아 있다** -- 응답하는 것을
        감추면 그것대로 거짓말이다.  ⛔ 다만 **`shopen`/`shclose` 는 뜻이 다르다**
        (운영자 2026-09-08): guide 에는 셔터가 없어 **Trigger Out 선**을
        세우고/내린다 (`IcgDispatcher.cmd_shopen`).  그 사실이 도움말에 보이도록
        기반 절의 대사를 **guide 판으로 갈아 끼운다** (`console.extend_help` 의
        `swap=`) -- 대사를 그대로 두면 도움말이 "셔터 개방" 이라고 거짓말한다.
        ⛔ 표를 손으로 맞추지 않는다 -- `tests/test_console.py` 가 이 목록과
        `IcgDispatcher` 의 `cmd_*` 를 양방향으로 대조한다.
        """
        return console.extend_help(
            ('guide 취득', (
                ('guiexp <sec>',
                 '가이드 노출시간 = 독출 개시 간격 -- `exp` 와 같은 값'),
                ('expenable [on|off]', '노출 잠금 -- 인자 없으면 조회'),
            )),
            ('CCD 조작 (실기)', (
                ('ccdflush',
                 '유휴 CCD 를 FlushFrame 한 바퀴로 비운다 (프레임 없음)'),
                ('ccdpowon', 'CCD 전원 ON -- poweron_wait 뒤에 DONE'),
                ('ccdpowoff', 'CCD 전원 OFF -- 다음 go 가 다시 켠다'),
                ('trigoutforce [on|off]',
                 'Trigger Out 강제 -- guide 쉬는 상태는 1 (0 = 타이밍 스크립트)'),
                ('trigoutlevel [high|low]',
                 '강제했을 때 나갈 레벨 -- ⛔ FORCE=1 이라야 핀에 나간다'),
                ('archon <원문>',
                 '컨트롤러 바이패스 -- guide 는 한 대라 태그가 없다'),
            )),
            ('듀어 히터 (⛔ 안전 봉투는 bench_test_plan.md)', (
                ('htrset [<0|1> <degC>]', 'Enable + 목표온도 -- 인자 없으면 조회'),
                ('htrforce [<0|1> <V>]',
                 '⛔ 강제 출력 (PID 우회 -- HEATERALIMIT 이 안 걸린다)'),
                ('htrramp [<0|1> <mK/update>]', '목표온도 램프'),
                ('htrpid [<P> <I> <D>]', 'PID 게인 셋'),
            )),
            ('House Keeping', (
                ('hk', 'HK 한 줄 -- HKDATA 와 같은 본문'),
                ('hkdata', 'ICS 가 헤더를 채우려고 묻는 것'),
                ('vacgauge [on|off]', '이온게이지 -- 인자 없으면 조회'),
                ('radionode [<하위명령> [장치]]',
                 'status | connect | disconnect | reconnect | enable | '
                 'disable -- 장치 이름이 없으면 폴링 자체'),
            )),
            swap={
                # ⛔ guide 에는 셔터가 없다 -- 이 둘은 Trigger Out 선을 세운다.
                'shopen':
                    'Trigger Out 을 <sec> 동안 HIGH 로 -- 셔터가 아니다',
                'shclose':
                    '선을 즉시 LOW 로 (LEVEL=0, FORCE=1 유지 -- 타이머도 끊는다)',
            },
        )

    # -- 수명 ---------------------------------------------------------------

    #: ICS 몫 포트 (`ics_archon.ini` · `ics_sim` 기본값).  ⭐ **이 값과 같으면
    #: 한 호스트에서 둘 다 못 뜬다** -- 뒤에 뜨는 쪽이 bind 에서 죽는데, 그
    #: 오류가 "왜 안 뜨나" 로만 보여서 원인을 찾는 데 시간이 든다.  ICG 몫은
    #: **6601** 이고 배정표는 `INSTALL.md` 다 (2026-09-03).
    ICS_BIND_PORT = 6600

    async def start(self) -> None:
        # ⚠️ `validate()` 는 **`__init__` 에서** 돈다 -- 백엔드가 ACF 를 읽어
        # 보기 전에 막아야 경고와 치명이 뒤바뀌지 않는다 (위 주석).
        self.expenable.load()
        if not self.expenable.allowed:
            log.warning('⛔ 노출이 **잠겨** 있다 (EXPENABLE OFF, 출처 %s) -- '
                        'GO 가 거절된다.  풀려면 EXPENABLE ON',
                        self.expenable.origin)
        port = int(getattr(self.cfg.transport, 'bind_port', 0))
        if port == self.ICS_BIND_PORT:
            log.warning('[transport] bind_port=%d 는 **ICS 몫**이다 -- ICG 는 '
                        '6601 이다 (INSTALL.md 배정표).  같은 호스트에서 ICS 와 '
                        '함께 돌리면 뒤에 뜨는 쪽이 bind 에 실패한다.  호스트를 '
                        '갈랐다면 이 경고는 무시해도 된다', port)
        await super().start()
        self._log_icg_banner()
        if self.backend_name == 'icg_archon':
            # 기동 접속 -- 실패해도 기동은 계속한다 (ics_archon 과 같은
            # 규칙: 컨트롤러 전원이 나중에 들어오는 배치가 실재한다).
            self.spawn(self._connect_controller())
        self.hk.start()
        self.radionode.start(self.spawn)

    async def _connect_controller(self) -> None:
        try:
            await self.guide.prepare()
            log.info('guide 컨트롤러 준비 완료 (%s)', self.icfg.host)
            # ⭐ 이온게이지 상태는 **준비된 뒤에야** 되읽을 수 있다 (설정 줄
            # 번호가 ACF 파싱에서 오고, RCONFIG 왕복이 필요하다).  실패하면
            # "모름" 으로 남고 그때는 DEWPRES 를 막지 않는다 -- 추측으로 ON
            # 을 적으면 헤더 판정의 근거가 거짓이 된다 (gauge.load 주석).
            await self.gauge.load(self.guide.ctrl)
        except Exception as exc:  # noqa: BLE001
            # `?xx` 거부(이 세션의 APPLYALL 미실시)는 power_on() 이 진단 문구를
            # 붙여 올린다 (DevNote 10.2) -- 여기서 따로 가르지 않는다.  ⚠️ HK
            # 감시는 재접속하지 않는다 (`refresh_status_live` 는 소켓이 없으면
            # 그냥 실패해 결측으로 남긴다) -- 종전 문구가 그렇게 주장했었다.
            log.error('guide 컨트롤러 기동 접속 실패 -- %s.  첫 GO 의 prepare() 가 '
                      '다시 시도한다 (HK 감시는 재접속하지 않고 STATUS 결측으로 '
                      '기록한다)', exc)

    async def stop(self) -> None:
        # ⭐ **취득 사이클을 먼저 세운다** (2026-08-31 교차검토).  사이클
        # 태스크는 `spawn()` 이 아니라 시퀀서가 직접 띄우므로 부모
        # `IcsSim.stop()` 의 `_tasks` 취소에 안 걸린다 -- 안 세우면 아래
        # `guide.shutdown()`(POWEROFF) 뒤에도 트리거가 나가고, 종료 통보는
        # 이미 멈춘 transport 큐에 쌓여 ABC 가 사이클 끝을 못 듣는다.
        if self.seq.busy:
            log.info('종료 -- 진행 중인 guide 사이클을 세운다')
            self.seq.cancel(save=False, requester='shutdown')
        # busy 가 아니어도 기다린다 -- 방금 끝난 ABORT 의 `Exposures=0` 왕복·꼬리
        # 소화가 아직 날아가는 중일 수 있다 (고아 미래 회수, 9.15-(9)).  비어
        # 있으면 즉시 돌아온다.  ⚠️ 저장은 여기서 기다리지 않는다 -- 아래
        # `drain_writers(shutdown_drain)` 이 **상한을 두고** 기다린다.
        await self.seq.wait(drain=False)
        await self.hk.stop()
        await self.radionode.stop()
        await self.seq.drain_writers(self.icfg.shutdown_drain)
        try:
            await self.guide.shutdown()
        except Exception as exc:  # noqa: BLE001
            log.warning('guide 백엔드 종료 실패 -- %s', exc)
        await super().stop()

    # -- 배너 ---------------------------------------------------------------

    def _log_icg_banner(self) -> None:
        i = self.icfg
        rn = i.radionode
        lines = [
            '-- icg (guide) 배선 ' + '-' * 40,
            'build        : %s' % build_id(),
            'controller   : %s:%d (tag %s)  acf=%s' % (
                i.host or '(미설정)', i.port, TAG, i.acf_path or '(없음)'),
            'geometry     : %dx%d (%.2f MiB/frame)  exptime_min=%.1fs' % (
                i.naxis1, i.naxis2, i.frame_bytes / (1 << 20), i.exptime_min),
            'hk           : every %.0fs -> %s (latest: %s)' % (
                i.hk.interval, i.hk.log_dir, i.hk.latest_name),
            # ⭐ 어느 키로 게이지를 끄는지 배너에 남긴다 -- 둘의 대가가 달라서
            # (diopower 는 압력 읽기까지 죽는다) 나중 로그만 보고 판단할 수
            # 있어야 한다.
            'ion gauge    : off-method=%s (%s)  state=%s' % (
                self.gauge.method,
                gauge_mod.METHODS[self.gauge.method][0],
                self.gauge.word),
            'radionode    : %s (poll %.0fs, devices: %s)' % (
                rn.backend, rn.poll_period,
                ', '.join(d.alias for d in rn.devices) or '없음'),
            # ⚠️ 부모 배너는 `[hardware] backend`(우리가 'sim' 으로 못박은
            # 값)를 찍으므로 여기서 **실제로 쓰는 것**을 다시 적는다 --
            # 안 그러면 배너가 `DATASRC=SIM` 이라고 하는데 파일에는
            # `ARCHON_GUIDE` 가 실린다 (2026-08-31 교차검토).
            'backend      : %s -> DATASRC=%s' % (
                getattr(self.guide, 'name', '?'),
                guidehdr.datasrc_of(getattr(self.guide, 'name', ''))),
            '-' * 60,
        ]
        log.info('\n%s', '\n'.join(lines))

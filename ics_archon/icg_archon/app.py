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
        # ⭐ **헤더 기본값 둘이 계통마다 다르다** (운영자 확정 2026-09-09).
        # 부모(`IcsState`)의 기본은 science 값이라 guide 쪽을 여기서 누른다 --
        # `cfg.hardware.backend` 와 같은 부류의 자리다.
        # ⚠️ **명령이 이걸 덮는다** (`OBSTYPE`/`OBSERVER`) -- 기본값일 뿐이다.
        self.state.obstype = 'GUIDE'
        self.state.observer = 'KMTNetOp'
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
        self.gauge = GaugeState(icfg.gauge_off_method,
                                warmup=icfg.gauge_warmup_wait)
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

    def banner_datasrc(self) -> str:
        """guide 어휘로 옮긴다 -- science 표에는 `archon_guide` 가 없다.

        ⛔ 부모 판을 그대로 쓰면 *"모르는 백엔드라 SIM 으로 적는다"* 경고가
        나면서 배너가 `archon_guide -> DATASRC=SIM` 이 된다 (벤치 2026-09-08).
        """
        return guidehdr.datasrc_of(self.guide.name)

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
                ('ccdpowon', 'CCD 전원 ON -- gauge_warmup_wait 뒤에 DONE'),
                ('ccdpowoff', 'CCD 전원 OFF -- 다음 go 가 다시 켠다'),
                ('trigout <ms>',
                 'Trigger Out 을 <ms> 동안 HIGH 로 -- ⭐ 0 이면 즉시 LOW · '
                 '⚠️ 실현 최소 폭 ≈235 ms'),
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
            # ⛔ **guide 에 없는 기반 명령** (운영자 2026-09-08~09).
            # `dmawait` 는 광케이블 IC 의 지연이고, `flashnow`/`ledflash` 는
            # 점검용 LED 프로젝터이며, `shopen`/`shclose` 는 셔터다 -- guide 엔
            # 셋 다 없다.  ⭐ 감추는 게 아니라 **거절한다**
            # (`IcgDispatcher.UNSUPPORTED` 와 짝).
            drop=('dmawait', 'flashnow', 'ledflash', 'shopen', 'shclose'),
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

    async def _after_config(self) -> None:
        """ACF 적용 직후 · `POWERON` **앞**에 도는 곁다리 (2026-09-10).

        ⭐ **여기 있는 것들은 설정 메모리만 있으면 된다** -- CCD 전원도 `SYSTEM`
        스냅샷도 필요 없다.  ⛔ 종전에는 `prepare()` **전체 뒤**에 줄 서서
        `gauge_warmup_wait`(종전 `poweron_wait`, 벤치 15초)를 통째로
        기다렸고, 그동안 `VACGAUGE` 가
        `UNKNOWN`, `DEWPRES`·온도가 결측이었다 (운영자가 벤치에서 잡았다).
        ⚠️ ArchonGUI 가 빨라 보이는 것은 같은 일을 더 빨리 해서가 아니라
        **ACF 적용도 `POWERON` 도 안 하기** 때문이다 -- 우리가 늦었던 것은
        그 둘 뒤에 이 읽기를 매달아 둔 탓이다.
        """
        # ⭐ 이온게이지 상태는 **ACF 적용 뒤에** 읽는다 (설정 줄 번호가 ACF
        # 파싱에서 오고, `CLEARCONFIG` 가 지운 메모리를 읽으면 뜻이 없다).
        # 실패하면 "모름" 으로 남고 그때는 DEWPRES 를 막지 않는다 -- 추측으로
        # ON 을 적으면 헤더 판정의 근거가 거짓이 된다 (gauge.load 주석).
        # ⭐ **`APPLYALL` 이 방금 게이지 전원을 정했다** (운영자 지적
        # 2026-09-10) -- ACF 의 `MOD10\\DIO_POWER` 가 그대로 적용된다.  그래서
        # 여기서 읽은 `ON` 은 **막 켜진 것**이고 예열 중이다.
        # ⛔ R2619 부터 ACF 는 `0` 이라 보통 `OFF` 로 읽히지만, 옛 ACF(`=1`)를
        # 올리면 켜진 채로 읽힌다 -- 그때 예열을 안 세면 안 미더운 값을 `ON`
        # 이라 적는다.
        await self.gauge.load(self.guide.ctrl, fresh=True)
        await self._settle_gauge()
        # ⭐ **준비되자마자 HK 한 바퀴** (운영자 지시 2026-09-09).
        #
        # ⛔ 종전에는 기동 뒤 **최대 한 주기(60초)** 동안 게이지 상태도
        # `DEWPRES` 도 온도도 결측이었다.  기동 첫 바퀴는 `hk.start()` 가
        # 곧바로 돌리지만 그때는 **ACF 적용이 아직**이라 쓸 값이 안 나오고
        # (로그의 *"ACF 적용 중이라 … 건너뛴다"*), 다음 바퀴는 60초 뒤다.
        # ⭐ **`HKDATA NOW` 와 같은 함수**를 쓴다 (`refresh_now`) -- 따로
        # 만들면 두 경로가 갈린다 (11.56 의 결론).  덤으로 주기 기준이
        # *준비된 시각*으로 다시 놓여 곧바로 또 도는 낭비도 없다.
        # ⚠️ 실패해도 기동은 계속한다 -- 다음 주기 바퀴가 채운다.
        try:
            await self.hk.refresh_now()
        except Exception as exc:  # noqa: BLE001
            log.warning('기동 HK 첫 바퀴 실패 -- %s.  다음 주기(%.0f초)에 '
                        '다시 읽는다', exc, self.icfg.hk.interval)

    async def _connect_controller(self) -> None:
        try:
            await self.guide.prepare(self._after_config)
            log.info('guide 컨트롤러 준비 완료 (%s)', self.icfg.host)
        except Exception as exc:  # noqa: BLE001
            # `?xx` 거부(이 세션의 APPLYALL 미실시)는 power_on() 이 진단 문구를
            # 붙여 올린다 (DevNote 10.2) -- 여기서 따로 가르지 않는다.  ⚠️ HK
            # 감시는 재접속하지 않는다 (`refresh_status_live` 는 소켓이 없으면
            # 그냥 실패해 결측으로 남긴다) -- 종전 문구가 그렇게 주장했었다.
            log.error('guide 컨트롤러 기동 접속 실패 -- %s.  첫 GO 의 prepare() 가 '
                      '다시 시도한다 (HK 감시는 재접속하지 않고 STATUS 결측으로 '
                      '기록한다)', exc)

    async def _settle_gauge(self) -> None:
        """기동 때 이온게이지를 `[icg] gauge_on_start` 에 맞춘다.

        ⛔ **기본은 `off` 다** -- 필라멘트가 science 영상을 오염시키므로 science
        노출 중에는 꺼져 있어야 하는데, 그 사이에 ICG 를 재실행하면 종전에는
        **ACF 가 켜 버렸다**(`MOD10\\DIO_POWER=1`).  R2619 에서 ACF 를 `0` 으로
        내렸고 이것은 그 위의 정책이다.  ⭐ **켜는 쪽은 ICS 몫**이다 -- 노출이
        끝나면 `ICS>ICG VACGAUGE ON` 이 온다.

        ⭐ **되읽은 값과 다를 때만 쓴다.**  `set()` 은 `APPLYDIO09` 라 모듈
        VCPU 를 재시작하고 `DEWPRES` 에 구멍을 내므로, 이미 맞는 값이면
        왕복도 구멍도 만들지 않는다 (ACF 를 갓 적용한 정상 경로가 이쪽이다).
        ⛔ **모르면 쓴다** -- `load()` 가 실패해 상태가 `None` 이면 추측하지
        않고 원하는 값으로 맞춘다.  안 맞추면 *"꺼져 있다고 믿는데 켜져 있는"*
        상태가 남고, 그것이 바로 이 눈금이 막으려는 것이다.
        """
        want = self.icfg.gauge_on_start == 'on'
        # ⭐ **예열할 게이지가 없으면 `POWERON` 뒤 대기를 건너뛴다**
        # (운영자 2026-09-10: *"CCD POWERON에 대한 대기시간은 필요 없는데?"*).
        # 전원 투입 자체는 실측 **약 1초**(`POWER=4 (On) 확인 -- 1.0초 걸렸다`)
        # 이고, 남는 시간은 순전히 이온게이지 예열 몫이다.
        # ⚠️ 판단을 **`want` 가 아니라 실제 상태**로 한다 -- 되읽기가 실패해
        # 모르는 상태면 켜질 수도 있으니 기다리는 쪽이 안전하다.
        ctrl = getattr(self.guide, 'ctrl', None)
        if ctrl is not None:
            ctrl.power_wait = 0.0 if (not want and self.gauge.on is False) \
                else None
        if self.gauge.on is want:
            log.info('이온게이지는 이미 %s -- 기동에서 건드리지 않는다 '
                     '([icg] gauge_on_start=%s)',
                     self.gauge.word, self.icfg.gauge_on_start)
            return
        try:
            await self.gauge.set(self.guide.ctrl, want)
        except Exception as exc:  # noqa: BLE001
            log.warning('기동 이온게이지 %s 실패 -- %s.  ⚠️ 상태를 **모른다** '
                        '-- science 노출 중이면 `vacgauge off` 로 확인할 것',
                        'ON' if want else 'OFF', exc)

    async def stop(self) -> None:
        # ⭐ **취득 사이클을 먼저 세운다** (2026-08-31 교차검토).  사이클
        # 태스크는 `spawn()` 이 아니라 시퀀서가 직접 띄우므로 부모
        # `IcsSim.stop()` 의 `_tasks` 취소에 안 걸린다 -- 안 세우면 아래
        # `guide.shutdown()`(POWEROFF) 뒤에도 트리거가 나가고, 종료 통보는
        # 이미 멈춘 transport 큐에 쌓여 ABC 가 사이클 끝을 못 듣는다.
        # ⛔ **펄스를 먼저 내린다** (운영자 2026-09-09).  `spawn` 한 펄스
        # 태스크는 아래 종료가 취소하므로 내림이 **영영 안 돈다** -- 그러면
        # 사람 없는 채로 **LED 가 켜진 채** 프로세스가 끝난다.
        # ⚠️ `spawn` 이 아니라 **여기서 기다린다** (같은 이유로).
        await self.dispatch.release_pulse('종료')
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
        # ⭐ **이온게이지를 끈다** (운영자 지시 2026-09-09).  ⛔ 우리가 켠 적이
        # 없어도 끈다 -- guide ACF 가 `MOD10\DIO_POWER=1` 을 박아 두어 **ACF
        # 적용마다 저절로 켜지고**, 종전에는 아무도 안 껐다 (벤치에서 운영자가
        # 잡았다: *"ICG 실행 시 켜지고 quit 할 때는 안 꺼지더라"*).
        # ⚠️ **HK 를 세운 뒤에 끈다** -- 먼저 끄면 남은 HK 바퀴가 Conductron
        # 값을 `DEWPRES` 로 보고 인정범위 밖 경고를 낸다.
        # ⚠️ **POWEROFF 앞에 둔다** -- 끄는 것 자체가 `WCONFIG`+`APPLYDIO09`
        # 왕복이라 링크가 살아 있어야 한다.
        # ⚠️ 실패해도 종료는 계속한다 -- 다만 **게이지가 켜진 채 남는다**는
        # 사실을 남긴다 (필라멘트가 켜진 채로 방치되지 않게 사람이 알아야 한다).
        try:
            await self.gauge.set(self.guide.ctrl, False)
        except Exception as exc:  # noqa: BLE001
            log.warning('종료 -- 이온게이지를 못 껐다: %s.  ⚠️ **게이지가 켜진 '
                        '채 남아 있을 수 있다**', exc)
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

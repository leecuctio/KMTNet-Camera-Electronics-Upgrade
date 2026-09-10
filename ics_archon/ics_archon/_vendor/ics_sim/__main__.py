#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point:  python -m ics_sim [options]

설정은 ics_sim.ini 에서 읽고, 아래 인자로 개별 항목을 덮어쓴다.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
import os
import sys

from . import __version__, config
from .app import IcsSim
from .console import Console, PromptSafeStream


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='ics_sim',
        description='KMTNet ICS simulator (IMPv2.5 / UDP)')
    p.add_argument('-c', '--config', default=config.DEFAULT_INI,
                   help='설정 파일 경로 (기본: ics_sim.ini)')
    p.add_argument('--time-scale', type=float,
                   help='전체 시간 축척. 0.1 이면 10배 빠르게')
    p.add_argument('--bind-port', type=int, help='수신 UDP 포트')
    p.add_argument('--xis-host', help='XIS 허브 주소 (비우면 direct-reply)')
    p.add_argument('--xis-port', type=int, help='XIS 허브 포트')
    p.add_argument('--data-dir', help='FITS 저장 경로')
    p.add_argument('--fits', dest='write_fits', action='store_true',
                   help='더미 FITS 를 실제로 생성')
    p.add_argument('--no-fits', dest='write_fits', action='store_false',
                   help='FITS 생성 안 함 (메시지만)')
    p.add_argument('--backend', choices=('sim', 'archon'),
                   help='디텍터 백엔드')
    p.add_argument('--node-mode', choices=('legacy', 'merged'),
                   help='발신 노드 이름 방식')
    p.add_argument('--bug-compat', action='store_true',
                   help='레거시 커맨드워드 오염을 의도적으로 재현')
    p.add_argument('--inject', help='결함 주입 (쉼표 구분)')
    p.add_argument('--no-console', dest='console', action='store_false',
                   help='키보드 인터페이스 없이 실행')
    p.add_argument('--quiet-wire', dest='wire', action='store_false',
                   help='송수신 메시지를 출력하지 않음')
    p.add_argument('--log-level', choices=('debug', 'info', 'warning', 'error'))
    p.add_argument('-V', '--version', action='version',
                   version=f'ics_sim {__version__}')
    p.set_defaults(write_fits=None, console=None, wire=None)
    return p


def apply_args(cfg: config.SimConfig, args: argparse.Namespace) -> None:
    if args.time_scale is not None:
        cfg.timing.time_scale = args.time_scale
    if args.bind_port is not None:
        cfg.transport.bind_port = args.bind_port
    if args.xis_host is not None:
        cfg.transport.xis_host = args.xis_host
    if args.xis_port is not None:
        cfg.transport.xis_port = args.xis_port
    if args.data_dir is not None:
        cfg.paths.data_dir = args.data_dir
    if args.write_fits is not None:
        cfg.paths.write_fits = args.write_fits
    if args.backend is not None:
        cfg.hardware.backend = args.backend
    if args.node_mode is not None:
        cfg.node.emit_node_mode = args.node_mode
    if args.bug_compat:
        cfg.behavior.bug_compat = True
    if args.inject is not None:
        cfg.behavior.inject = frozenset(
            x.strip() for x in args.inject.split(',') if x.strip())
    if args.console is not None:
        cfg.behavior.console = args.console
    if args.wire is not None:
        cfg.logging.wire = args.wire
    if args.log_level is not None:
        cfg.logging.level = args.log_level


#: ⭐ 로그 한 줄의 꼴 -- **시각 태그를 `[...]` 로 감싼다** (운영자 2026-09-08).
#: OBSAgent 와 같은 관례다: `[2026-09-04T10:36:34.942] PONG received from XIS`.
#: 대괄호가 있으면 **시각과 본문의 경계가 눈에 먼저 잡힌다** -- 콘솔에서는
#: 프롬프트 줄과 로그 줄이 섞여 흐르므로 그 경계가 값을 한다.
#: ⛔ **태그 안에 공백을 넣지 말 것** -- `_TailModule` 이 첫 공백에서 갈라 시각
#: 뒤에 `Warning:` 을 끼운다 (`tests/test_console.py` 가 못박는다).
LOG_FORMAT = '[%(asctime)s.%(msecs)03d] %(message)s'
LOG_DATEFMT = '%Y-%m-%dT%H:%M:%S'


class EssentialOnly(logging.Filter):
    """화면에 **함축 메시지(essential message)만** 흘린다 (`verbose = off`).

    ⭐ **판정은 표시 하나다** -- 줄을 내는 자리가 `extra={'essential': False}`
    로 *"이건 잡음"* 이라고 적고, 여기서는 그 표시만 본다.  ⛔ 문구를 여기서
    골라내면 안 된다: 문구가 바뀌면 조용히 안 맞게 되고, 어느 줄이 잡음인지가
    **그 줄에서 멀리 떨어진 곳**에 적히게 된다.

    ⭐ **기본은 "보인다"** 다 -- 표시가 없으면 함축 메시지로 본다.  표시를
    빠뜨렸을 때 **화면이 시끄러워질 뿐 정보가 사라지지 않는** 쪽이 맞다.

    ⚠️ **이 필터는 화면 처리기에만 단다** -- 로그 파일은 언제나 전부 받는다.
    """

    def __init__(self) -> None:
        super().__init__()
        #: ⭐ **끄고 켤 수 있다** -- `VERBOSE` 명령이 이것을 민다 (2026-09-11).
        #: ⛔ 필터를 붙였다 뗐다 하지 않는 이유: 처리기의 필터 목록을 런타임에
        #: 만지면 *"떼는 쪽과 붙이는 쪽"* 이 어긋나는 부류가 하나 는다.
        self.enabled = True

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003, D102
        if not self.enabled:
            return True
        return bool(getattr(record, 'essential', True))


class _TailModule(logging.Formatter):
    """경고 이상이면 **`Warning:`/`Error:` 앞머리**와 **`(module: …)` 꼬리**를 붙인다.

    운영자 지시 2026-09-08: *"실패나 오류의 경우에, 콘솔 메시지여도 `Error:` 나
    `Warning:` 을 붙여줘"* · *"메시지 뒤에 `(module: xxxx)` 이런 식으로"*.

    ⭐ 앞머리와 꼬리가 나뉜 것은 **읽는 차례** 때문이다 -- *무엇인지*(경고냐
    오류냐)는 먼저 보여야 하고, *어디서*(모듈)는 필요할 때만 찾으면 된다.
    ⚠️ 문턱이 `WARNING` 이다(`ERROR` 아님) -- 이 프로그램의 진단은 대부분
    경고로 나간다 (폴링 실패·한계 밖·형태 어긋남).  거기서 모듈이 안 보이면
    단서가 없다.  ⛔ 좁히려면 두 자리를 `ERROR` 로 올릴 것.
    ⚠️ 평시(INFO)에는 **아무것도 안 붙는다** -- 와이어 줄이 가장 잦아서다.
    """

    #: 수준 -> 앞머리.  `CRITICAL` 도 `Error:` 다 (운영자가 든 낱말이 둘이다).
    _WORD = ((logging.ERROR, 'Error: '), (logging.WARNING, 'Warning: '))

    #: 딸린 세부를 본문에서 가르는 표시.
    DETAIL_LEAD = '  --  '

    def __init__(self, *a, with_detail: bool = True, **kw) -> None:  # noqa: ANN002, ANN003
        """`with_detail` 이 거짓이면 **딸린 세부를 뗀다** (`verbose = off` 화면).

        ⭐ **한 사건은 한 기록이다** -- 함축 한 줄과 세부를 따로 남기면 로그
        파일에서 둘이 떨어져 앉고, 사이에 다른 줄이 끼면 짝을 못 찾는다.
        그래서 기록은 하나로 두고 **어디에 어떻게 쓸지는 여기서** 가른다
        (운영자 2026-09-11).

        `detail` 에 들어가는 것 둘:

        * **한글 설명** -- *왜 그런지·어디를 보라* (`⤷` 없이 그대로 잇는다)
        * **영문 세부** -- 버퍼·주소·잠금처럼 평시엔 안 보는 값

        ⛔ 로그 파일 처리기에는 이것을 끄지 않는다 -- 파일은 언제나 전부다.
        """
        super().__init__(*a, **kw)
        self.with_detail = bool(with_detail)

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        out = super().format(record)
        detail = getattr(record, 'detail', '')
        if detail and self.with_detail:
            out = '%s%s%s' % (out, self.DETAIL_LEAD, detail)
        if record.levelno < logging.WARNING:
            return out
        head = next(w for lvl, w in self._WORD if record.levelno >= lvl)
        # 시각 뒤·본문 앞에 끼운다 -- `asctime` 은 형식이 정한 맨 앞이다.
        # ⚠️ **시각 태그 안에 공백이 없어야** 이 가름이 성립한다 --
        # `[%(asctime)s.%(msecs)03d]` 는 대괄호까지 한 덩어리라 괜찮다.
        stamp, sep, body = out.partition(' ')
        return '%s%s%s%s (module: %s)' % (stamp, sep, head, body, record.name)


class DailyFile(logging.Handler):
    r"""`<폴더>/<이름>.<YYYYMMDD>.log` 에 **덧붙이고**, 날이 바뀌면 갈아탄다.

    운영자 지시 2026-09-09: *"icg 로그를 isis 로그처럼 `icg.yyyymmdd.log` 으로
    매일 갱신하여 저장.  재실행해도 전에 파일 지우지 않고 같은 날짜 뒤에
    덧붙이는 식으로."*

    ⭐ **날짜는 UTC 다.**  `HKQDATE`·`DATE-OBS`·FITS 파일명(`KMTK.20260909.…`)이
    다 UTC 이고 사이트 배너도 *"관측일 경계 UT 날짜 그대로"* 라 적는다 --
    로그 파일만 지역시로 끊으면 **같은 관측일의 자취가 두 파일로 갈린다**.
    ⚠️ 그래서 `setup_logging` 이 포매터의 시각도 UTC 로 맞춘다 (아래).

    ⛔ **`logging.Handler.name` 을 가리면 안 된다** -- 그 이름은 처리기 등록부의
    키다.  그래서 파일 이름의 앞머리는 `stem` 으로 든다.

    ⚠️ **회전을 시각이 아니라 기록마다 판정한다** -- `TimedRotatingFileHandler`
    는 자정에 현재 파일을 **개명**하므로 *"오늘 파일은 늘 오늘 이름"* 이 안
    된다.  여기서는 기록의 시각으로 파일을 고르므로 이름이 늘 맞고, 프로그램이
    자정을 넘겨 돌아도 자취가 날짜대로 갈린다.
    ⚠️ 실패해도 **죽지 않는다** -- 로그를 못 남기는 것이 프로그램을 세울 이유는
    아니다 (`handleError` 가 stderr 로 알린다).
    """

    def __init__(self, directory: str, stem: str,
                 encoding: str = 'utf-8') -> None:
        super().__init__()
        self.directory = directory
        self.stem = stem
        self.file_encoding = encoding
        self._day: str | None = None
        self._stream = None

    def path_for(self, day: str) -> str:
        """그 날짜의 파일 경로."""
        return os.path.join(self.directory, '%s.%s.log' % (self.stem, day))

    def _open(self, day: str) -> None:
        os.makedirs(self.directory, exist_ok=True)
        stream = open(self.path_for(day), 'a', encoding=self.file_encoding)
        self.close_stream()
        self._stream, self._day = stream, day

    def close_stream(self) -> None:
        if self._stream is not None:
            try:
                self._stream.close()
            except OSError:
                pass
            self._stream = None

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        try:
            day = time.strftime('%Y%m%d', time.gmtime(record.created))
            if day != self._day or self._stream is None:
                self._open(day)
            self._stream.write(self.format(record) + '\n')
            self._stream.flush()
        except Exception:                       # noqa: BLE001
            self.handleError(record)

    def close(self) -> None:  # noqa: D102
        self.close_stream()
        super().close()


def _log_handler(spec: str, stem: str) -> logging.Handler | None:
    r"""`[logging] file` 한 줄을 처리기로 옮긴다.  비면 `None`.

    ⭐ **`.log` 로 끝나면 그 파일 하나, 아니면 폴더**다 (운영자 2026-09-09:
    *"이제 ini 에는 폴더경로까지만 넣어두면 될까?"* -> 그렇다).
    ⚠️ **판정을 파일계에 묻지 않는다** -- `os.path.isdir` 로 가르면 폴더가 아직
    없을 때 뜻이 뒤집혀, 같은 ini 가 첫 실행과 두 번째 실행에서 다르게 돈다.
    이름만 보고 정하면 그런 일이 없다.
    ⭐ 옛 설정(`~/AIC/Logs/icg_archon.log`)은 **그대로 파일 하나**로 돈다.
    """
    spec = (spec or '').strip()
    if not spec:
        return None
    if spec.lower().endswith('.log'):
        return logging.FileHandler(spec, encoding='utf-8')
    return DailyFile(spec.rstrip('/\\'), stem)


#: 화면 처리기와 그 필터 -- `set_verbose()` 가 민다.  ⚠️ `setup_logging()` 을
#: 안 부른 자리(단위 시험)에서는 `None` 이고, 그때 `set_verbose()` 는 조용히
#: 아무것도 안 한다 (**로그 때문에 명령이 실패하면 안 된다**).
_SCREEN = None
_SCREEN_FILTER = None


def verbose_state() -> bool:
    """지금 화면이 자세한가.  처리기가 없으면 `True`(자세함)로 본다."""
    return _SCREEN_FILTER is None or not _SCREEN_FILTER.enabled


def set_verbose(on: bool) -> bool:
    """화면 자세함을 바꾼다.  **바뀐 뒤의 값**을 돌려준다.

    ⭐ 두 가지를 함께 민다 -- 함축 메시지만 흘리는 **필터**와, 딸린 세부를
    붙일지 정하는 **서식**.  ⛔ 로그 파일 쪽은 안 건드린다: 파일은 언제나
    전부다 (운영자 2026-09-11).
    """
    on = bool(on)
    if _SCREEN_FILTER is not None:
        _SCREEN_FILTER.enabled = not on
    fmt = getattr(_SCREEN, 'formatter', None) if _SCREEN is not None else None
    if fmt is not None and hasattr(fmt, 'with_detail'):
        fmt.with_detail = on
    return on


def setup_logging(cfg: config.SimConfig, name: str = 'ics') -> None:
    level = getattr(logging, cfg.logging.level.upper(), logging.INFO)
    # ⭐ **프롬프트를 알아보는 처리기다** -- 콘솔이 입력을 기다리는 중에 로그가
    # 오면 줄을 지웠다가 프롬프트와 입력 버퍼를 다시 그린다 (운영자 2026-09-08).
    global _SCREEN, _SCREEN_FILTER
    screen = PromptSafeStream(sys.stderr)
    # ⭐ **간결한 화면은 필터 하나로** -- 줄을 안 만드는 것이 아니라 화면에만
    # 안 내보내는 것이다.  파일은 아래에서 그대로 다 받는다.
    # ⭐ **필터는 늘 달아 두고 스위치로 켠다** -- `VERBOSE` 명령이 재기동 없이
    # 바꿀 수 있게 하려는 것이다 (2026-09-11).
    _SCREEN_FILTER = EssentialOnly()
    _SCREEN_FILTER.enabled = not cfg.behavior.verbose
    screen.addFilter(_SCREEN_FILTER)
    _SCREEN = screen
    handlers: list[logging.Handler] = [screen]
    fileh = _log_handler(cfg.logging.file, name)
    if fileh is not None:
        handlers.append(fileh)
    logging.basicConfig(
        level=level,
        datefmt='%Y-%m-%dT%H:%M:%S',
        handlers=handlers,
    )
    # ⭐ **평시엔 모듈 이름을 안 싣고, 경고 이상에서만 꼬리에 붙인다**
    # (운영자 2026-09-08).  콘솔에서 가장 잦은 줄은 와이어 추적인데 거기엔
    # `ics_sim.transport` 18자가 아무것도 더해 주지 않는다.  반대로 문제가
    # 났을 때는 **어느 모듈인지가 첫 단서**라 그때는 남긴다.
    # ⭐ **시각 태그를 `[...]` 로 감싼다** (운영자 2026-09-08) -- OBSAgent 와
    # 같은 관례다: `[2026-09-04T10:36:34.942] PONG received from XIS`.
    # 대괄호가 있으면 **시각과 본문의 경계가 눈에 먼저 잡힌다** -- 콘솔에서는
    # 프롬프트 줄과 로그 줄이 섞여 흐르므로 그 경계가 값을 한다.
    # ⭐ **로그 시각을 UTC 로 맞춘다** (2026-09-09).  ⛔ 종전에는 지역시였다 --
    # 벤치가 UTC 로 돌아서 `HKQDATE` 와 맞아 보였을 뿐, 한국시로 맞춘 기계에
    # 배포하면 로그만 +9 시간이 되어 `HKQDATE`·`DATE-OBS`·FITS 파일명과 어긋난다.
    # ⚠️ 날짜별 로그 파일의 경계도 그때 관측일과 갈린다.
    # ⭐ **서식이 둘이다** -- 화면은 `verbose` 를 타고, 파일은 언제나 전부다
    # (운영자 2026-09-11).  ⚠️ 같은 객체를 두 처리기에 물리면 안 된다:
    # `with_why` 가 서로 다른 값이어야 한다.
    for h in logging.getLogger().handlers:
        fmt = _TailModule(LOG_FORMAT, datefmt=LOG_DATEFMT,
                          with_detail=(h is not screen) or cfg.behavior.verbose)
        fmt.converter = time.gmtime
        h.setFormatter(fmt)


async def amain(cfg: config.SimConfig) -> int:
    app = IcsSim(cfg)
    await app.start()

    console = Console(app) if cfg.behavior.console else None
    try:
        if console is not None:
            await console.run()
        else:
            await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await app.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = config.load(args.config)
    apply_args(cfg, args)
    setup_logging(cfg)
    try:
        return asyncio.run(amain(cfg))
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`LOCK`/`FETCH` 가 readout 을 멈추는가 -- 독립 시험 도구 (2026-08-31).

운영자가 `ArchonGUI` 에서 본 것(DevNote 8.9): **FETCH 하는 동안 다음 프레임의
readout 이 멈춘다.**  노출(적분)은 계속되는데 엔진의 라인 기록만 멈췄다가
FETCH 가 끝나면 **이어서** 재개된다.

⚠️ **그 관측은 원인을 못 가른다** -- GUI 는 `LOCK` 을 fetch 내내 잡고 있어서
**잠금 구간과 정지 구간이 완전히 겹친다.**  이 도구가 그것을 가른다.

    조건      하는 일                       이것이 느려지면
    ------    --------------------------    ----------------------------
    idle      아무것도 안 함                (기준선)
    lock      LOCKn 만 잡고 기다린다        ⭐ LOCK 이 원인이다
    fetch     LOCKn + FETCH                 현행 ics_archon 동작
    nolock    FETCH 만 (잠금 없이)          ⭐ FETCH 가 원인이다

⭐⭐ **결과 (2026-09-01~02, 벤치 두 대)** -- **정지는 없었다.**  KMTC-101(1261/REV 7)·
KMTK-113(1252/REV 5) 둘 다 `idle`=`lock`=`fetch`=`nolock`=**368.0 행/초**.  8.9 의
"정지" 는 GUI 폴이 FETCH 중 버려져 **화면만 얼어붙은 것**이었다 (재개 시 10→1500 점프,
DevNote 10.5).  `LOCK` 은 15/15 반영·대가 0 이고, `nolock` 으로 fetch 하다 프레임 경계를
넘은 2회 모두 엔진이 **읽는 중인 버퍼로** 옮겨왔다 -- `LOCK` 이 지킬 구간이 실재한다.
→ **`lock_buffer = true` 종결.**  이 도구는 **회귀 확인용**으로 남는다 (FW 가 바뀌면 다시
돈다).  경위·계측 결함 여섯은 DevNote 10장, 결과·명령은 `archon_lock_fetch_report.md`.

**`ics_archon` 본편은 한 줄도 안 건드린다.**  검증된 링크 계층(`archon.protocol`)과
파서(`archon.parse`)만 읽기 전용으로 빌려 쓴다 -- 프로토콜을 다시 짜면 프레이밍·
참조번호에서 새 결함이 난다.

⭐ **폴링 없이 전후 두 점으로 잰다.**  Archon 링크는 소켓 하나에 명령 하나라
FETCH 중에는 `FRAME` 을 물어볼 수 없다(GUI 화면이 얼어붙는 이유가 그것이다).
그래서 동작 전후로 한 번씩만 읽고 엔진의 진행량을 수 하나로 접는다:

    pos  = BUF{WBUF}FRAME x BUF{WBUF}HEIGHT + BUF{WBUF}LINES     [라인 누적]
    속도 = (pos1 - pos0) / (t1 - t0)                              [행/초]

프레임 경계를 넘어도 성립한다(프레임 번호가 높은 자리를 맡는다).  ⚠️ 되감김이면
음수가 나오는데 **그 표본은 버린다** -- 표본 하나를 잃는 것이 거짓 0 을 보고하는
것보다 낫다.

사용법
------
    # 1단계 -- 읽기 전용.  전원을 켜지 않는다.
    python tools/ics_archon_buftest.py --host 10.0.0.13 --acf acf/<유닛>.acf

    # 2단계 -- 본시험.  ⚠️ 전원을 켜고 CCD 를 연속으로 읽어낸다.
    python tools/ics_archon_buftest.py --host 10.0.0.13 --acf acf/<유닛>.acf \\
        --stage stall --rounds 4 --csv buftest.csv

    # 3단계 -- 단차 증폭 (계단이 안 보일 때).  정지를 4배로 늘린다.
    python tools/ics_archon_buftest.py --host 10.0.0.13 --acf acf/<유닛>.acf \\
        --stage stall --rounds 2 --fetch-repeat 4 --save-fits ./frames

⚠️ **지킬 것 셋**

1. **한 번에 한 대만.**  두 대를 동시에 돌리면 대역폭을 나눠 써서 fetch 가
   느려지고, *정지 시간 = fetch 시간* 이라 측정값이 그대로 오염된다.
2. **컨트롤러당 접속자는 하나다.**  본편(`python -m ics_archon`)이나 STA GUI 를
   내리고 쓴다.
3. ⛔ **`AUTOFETCH`·`LOCKT` 는 보내지 않는다.**  FW 명령표에는 있으나 뜻을
   모른다(DevNote 8.11).  `AUTOFETCH` 가 자동 송출이면 링크에 프레임이 쏟아진다.

⚠️ 이 도구가 쓰는 FITS 는 **과학 산출물이 아니다** -- raw spec 헤더도 pair 규약도
따르지 않고, 기하는 컨트롤러가 보고한 **프레임 버퍼 그대로(19200 x 9400)** 다
(`FRAMEMODE=2` 가 탭 절반을 위, 절반을 아래에 쓴다).  행·열 프로파일을 보려고 픽셀을
꺼내 놓는 것뿐이다.
"""

from __future__ import annotations

import argparse
import configparser
import csv
import os
import statistics
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ics_archon.archon import parse                            # noqa: E402
from ics_archon.archon.protocol import ArchonError, ArchonLink  # noqa: E402

# ⚠️ 윈도우 콘솔(cp949)에서 기호 때문에 `--help` 조차 안 뜨는 것을 막는다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors='replace')
    except (AttributeError, ValueError):    # 파이프·리다이렉트면 없을 수 있다
        pass

T_FAST = 5.0            # 짧은 명령 상한 [s]
T_SYSTEM = 30.0         # LOADPARAMS·POWERON 상한 [s]
CONDITIONS = ('idle', 'lock', 'fetch', 'nolock')

OK, WARN, BAD = '  OK  ', ' 확인 ', ' 문제 '
_verdicts: list[tuple[str, str]] = []


def say(mark: str, label: str, detail: str = '') -> None:
    _verdicts.append((mark, label))
    print('[%s] %s%s' % (mark, label, ('\n         ' + detail) if detail else ''))


def block(title: str) -> None:
    print('\n' + '=' * 72 + '\n== ' + title + '\n' + '=' * 72)


def dump(fields: dict[str, str], keys: tuple[str, ...] = ()) -> None:
    items = [(k, fields[k]) for k in keys if k in fields] if keys \
        else sorted(fields.items())
    for k, v in items:
        print('     %-22s = %s' % (k, v))


# ---------------------------------------------------------------------------
# ACF -- `controller.parse_acf()` 와 **같은 규칙으로** 읽는다
# ---------------------------------------------------------------------------

def read_acf(path: str) -> tuple[dict[str, str], dict[str, int], dict[str, str]]:
    """`([CONFIG] 값, [CONFIG] 줄번호, [SYSTEM] 값)`.

    ⚠️ **정규화 규칙을 `controller.parse_acf()` 에서 그대로 가져와야 한다** --
    키를 `upper()` 하고 **역슬래시를 `/` 로도 바꾼다**(`MOD1\\DIO_DIR1`).
    안 맞추면 줄 번호가 어긋나 `WCONFIG` 가 **엉뚱한 줄을 덮어쓴다.**
    ⭐ 남의 규칙을 빌릴 때는 규칙 **전부**를 빌려야 한다.
    """
    cp = configparser.RawConfigParser(strict=False)
    cp.read(path, encoding='utf-8')
    config: dict[str, str] = {}
    configline: dict[str, int] = {}
    for i, (key, value) in enumerate(cp.items('CONFIG')):
        k = key.upper().replace('\\', '/')
        config[k] = value.replace('"', '')
        configline[k] = i
    system = {k.upper(): v.replace('"', '') for k, v in cp.items('SYSTEM')} \
        if cp.has_section('SYSTEM') else {}
    return config, configline, system


def param_slots(config: dict[str, str]) -> dict[str, str]:
    """`{파라미터 이름: PARAMETERn 키}` -- `PARAMETER5="Pixels=1201"` 을 뒤집는다."""
    out: dict[str, str] = {}
    for k, v in config.items():
        if k.startswith('PARAMETER') and '=' in v:
            out[v.split('=', 1)[0].strip()] = k
    return out


# ---------------------------------------------------------------------------
# 진행량 -- 엔진이 어디까지 썼나
# ---------------------------------------------------------------------------

def _i(fields: dict[str, str], key: str, default: int = -1) -> int:
    try:
        return int(fields[key])
    except (KeyError, ValueError):
        return default


def write_pos(fields: dict[str, str],
              stride: int) -> tuple[int, int, int] | None:
    """`(누적 라인, 쓰는 중 프레임 번호, 그 버퍼의 라인)`.  쓰는 중이 아니면 `None`.

    누적 라인 = `프레임번호 x stride + 라인` -- 프레임 경계를 넘어도 단조 증가한다.

    ⚠️⚠️ **`stride` 는 `BUFnHEIGHT` 가 아니라 ACF 의 `LINECOUNT` 다**
    (2026-09-01 실기에서 드러났다).  `FRAMEMODE=2`(split, 매뉴얼 p.56·70)면
    앞쪽 절반 탭이 버퍼 위쪽, 뒤쪽 절반이 아래쪽에 쓰여 **라인클록 하나가 두
    행을 채운다** -- `BUFnHEIGHT=9400` 인데 `BUFnLINES` 는 `LINECOUNT=4700`
    에서 멈춘다.  높이를 stride 로 쓰면 프레임 경계를 넘은 표본마다 **유령
    4700 행**이 더해져 속도가 3배로 부풀고, 그 표본이 기준선에 섞이면
    **판정이 뒤집힌다** (첫 실측에서 실제로 그럴 뻔했다).

    ⚠️ 같은 잘못된 전제가 `archon/parse.py` 의 `progress` 에도 있다
    (`PCTREAD` 가 50%% 를 못 넘는다) -- 한쪽만 고치지 말 것.
    """
    wbuf = _i(fields, 'WBUF', 0)
    if wbuf <= 0:
        return None
    frame = _i(fields, 'BUF%dFRAME' % wbuf)
    lines = _i(fields, 'BUF%dLINES' % wbuf)
    if frame < 0 or lines < 0 or stride <= 0:
        return None
    if lines > stride:
        # 전제가 깨졌다 -- 조용히 틀린 속도를 내느니 표본을 버린다.
        print('  ⚠️ BUF%dLINES=%d 가 LINECOUNT=%d 를 넘었다 -- stride 전제가 '
              '깨졌다.  표본을 버린다' % (wbuf, lines, stride))
        return None
    return frame * stride + lines, frame, lines


# ---------------------------------------------------------------------------
# 컨트롤러 한 대와의 대화
# ---------------------------------------------------------------------------

class Unit:
    def __init__(self, host: str, port: int, tag: str) -> None:
        self.link = ArchonLink(host, port)
        self.tag = tag

    def connect(self) -> None:
        self.link.connect(retry=2)

    def close(self) -> None:
        self.link.close()

    def cmd(self, c: str, timeout: float = T_FAST) -> bytes:
        return self.link.command(c, timeout=timeout)

    def query(self, c: str, timeout: float = T_FAST) -> dict[str, str]:
        return parse.keyvals(self.link.command(c, timeout=timeout))

    def frame(self) -> dict[str, str]:
        return self.query('FRAME')

    # -- 파라미터 ----------------------------------------------------------
    def read_config_line(self, line: int) -> str:
        """`RCONFIG<line>` -- 컨트롤러 메모리의 그 줄을 그대로 읽는다."""
        return self.cmd('RCONFIG%04X' % line).decode('ascii', 'replace').strip()

    def set_param(self, configline: dict[str, int], key: str, value: str) -> None:
        """`WCONFIG` 로 `PARAMETERn` 한 줄을 바꾼다.

        ⚠️ **쓰기 전에 그 줄을 읽어 확인한다.**  컨트롤러에 다른 ACF 가 올라가
        있으면 줄 번호가 어긋나 **엉뚱한 설정을 덮어쓴다.**  labtest 는 자기가
        방금 올린 ACF 라 그 위험이 없었지만, 이 도구는 **이미 올라가 있는 것을
        전제**하므로 확인이 필요하다.
        """
        line = configline[key]
        got = self.read_config_line(line)
        if not got.upper().startswith(key + '='):
            raise ArchonError(
                '%s: 설정 줄 %d 이 %s 가 아니라 %r 이다 -- 컨트롤러에 다른 ACF 가 '
                '올라가 있다.  이 ACF 를 먼저 적용하고 다시 돌려라 '
                '(probe_archon 또는 STA GUI).' % (self.tag, line, key, got[:60]),
                cmd='RCONFIG')
        self.cmd('WCONFIG%04X%s=%s' % (line, key, value))

    def load_params(self) -> None:
        self.cmd('LOADPARAMS', timeout=T_SYSTEM)

    # -- 전원 --------------------------------------------------------------
    def power_on(self, wait: float) -> None:
        """`POWERON` 뒤 `POWER=4` 를 확인한다.

        ⚠️⚠️ **`wait` 는 램프 대기가 아니라 CCD flush 대기라 줄이면 안 되고,
        `POWER=4` 를 일찍 봤다고 빠져나가서도 안 된다** (DevNote 4장) --
        확인은 그 대기 *안에서* 하는 것이지 대기를 **대신하는** 것이 아니다.
        ⭐ 그래서 **끝까지 기다린 뒤에** 판정한다.
        """
        self.cmd('POWERON', timeout=T_SYSTEM)
        deadline = time.monotonic() + wait
        state, seen4 = None, False
        while time.monotonic() < deadline:
            time.sleep(1.0)
            state = parse.power_state(self.query('STATUS'))
            seen4 = seen4 or (state == 4)
        if state != 4:
            raise ArchonError('%s: POWERON 뒤 POWER=%s 다 (기대 4%s)'
                              % (self.tag, state,
                                 ', 중간에 4 를 봤다가 떨어졌다' if seen4 else ''),
                              cmd='POWERON')

    def power_off(self) -> None:
        try:
            self.cmd('POWEROFF', timeout=T_SYSTEM)
        except (ArchonError, OSError) as exc:
            print('  ⚠️ POWEROFF 실패: %s' % exc)


# ---------------------------------------------------------------------------
# 1단계 -- 읽기 전용
# ---------------------------------------------------------------------------

def stage_info(u: Unit, acf_system: dict[str, str], acf_path: str) -> dict[str, str]:
    block('1단계  읽기 전용 -- SYSTEM · FRAME · ACF [SYSTEM] 대조')

    system = u.query('SYSTEM', timeout=T_SYSTEM)
    print('\n>> SYSTEM (%d 필드)' % len(system))
    dump(system, ('BACKPLANE_ID', 'BACKPLANE_TYPE', 'BACKPLANE_REV',
                  'BACKPLANE_VERSION'))

    # -- ACF [SYSTEM] 대조 (DevNote 8.15) ---------------------------------
    if acf_system:
        for key, hard in (('BACKPLANE_VERSION', True), ('BACKPLANE_REV', True),
                          ('BACKPLANE_ID', False)):
            live, rec = system.get(key, ''), acf_system.get(key, '')
            if not rec:
                continue
            if live == rec:
                say(OK, '%s 가 ACF 기록과 같다 (%s)' % (key, live))
            elif hard:
                say(BAD, '%s 가 어긋난다 -- 실기 %r / ACF %r' % (key, live, rec),
                    'FW 를 올리고 ACF 를 다시 안 떴거나, 이 ACF 가 형제 '
                    '컨트롤러에서 뜬 것이다')
            else:
                # ⚠️ KMTK 는 한 대에서 MK/NT 두 ACF 를 떴다 -- 설계상 다르다.
                say(WARN, '%s 가 다르다 (실기 %s / ACF %s) -- 형제 컨트롤러에서 '
                          '뜬 ACF 면 정상이다' % (key, live, rec))
    else:
        say(WARN, 'ACF 에 [SYSTEM] 절이 없다 -- 대조를 건너뛴다 (%s)'
            % os.path.basename(acf_path))

    # -- FRAME ------------------------------------------------------------
    fields = u.frame()
    print('\n>> FRAME (%d 필드)' % len(fields))
    dump(fields, ('RBUF', 'WBUF', 'BUF1FRAME', 'BUF1COMPLETE', 'BUF1WIDTH',
                  'BUF1HEIGHT', 'BUF1SAMPLE', 'BUF1LINES', 'BUF1BASE',
                  'BUF2FRAME', 'BUF2COMPLETE', 'BUF2LINES'))

    # ⭐ `RBUF` 존재가 DevNote 8.6-2 의 물음을 닫는다 (FW 1252 에서만 확인됐다).
    if 'RBUF' in fields:
        say(OK, 'FRAME 응답에 RBUF 가 있다 -- 이 FW 는 RBUF 를 구현한다',
            'LOCKn 뒤 RBUF != n 은 이제 "잠금이 반영되지 않았다" 로 읽는다')
    else:
        say(BAD, 'FRAME 응답에 RBUF 가 없다 -- 이 FW 는 RBUF 를 안 낸다',
            'LOCK 반영 여부를 상태로는 못 본다.  WBUF 이동(거동)만 남는다')

    fs = parse.newest(fields)
    if fs.width > 0 and fs.height > 0:
        say(OK, '기하 %dx%d %s -- %.1f MiB'
            % (fs.width, fs.height, '32bit' if fs.samplemode else '16bit',
               fs.data_bytes / (1 << 20)))
    return system


# ---------------------------------------------------------------------------
# 2단계 -- 2x2 시험
# ---------------------------------------------------------------------------

class Sample(dict):
    pass


def _newest_complete(fields: dict[str, str]) -> parse.FrameStatus | None:
    """완료된 최신 버퍼.  없으면 `None`."""
    fs = parse.newest(fields)
    if fs.frame <= 0 or _i(fields, 'BUF%dCOMPLETE' % (fs.buf + 1), 0) != 1:
        return None
    return fs


def run_condition(u: Unit, cond: str, args, ctx: dict) -> Sample | None:  # noqa: ANN001
    """조건 하나를 재고 표본 하나를 돌려준다.  잴 수 없으면 `None`."""
    stall_rows: dict[int, int] = ctx['stall_rows']
    f0 = u.frame()
    p0 = write_pos(f0, ctx['stride'])
    if p0 is None:
        return None                     # 엔진이 쉬는 중 -- 잴 것이 없다
    pos0, wframe0, wlines0 = p0

    fs = _newest_complete(f0)
    if cond in ('lock', 'fetch', 'nolock') and fs is None:
        return None                     # 잠그거나 받을 완료 버퍼가 없다

    # ⭐ 지금 쓰이는 중인 프레임이 **이 조건 때문에 멈출** 프레임이다.
    #    나중에 그 프레임을 fetch 할 때 `STALLROW` 로 실어 준다.
    if cond != 'idle':
        stall_rows[wframe0] = wlines0

    buf_n = (fs.buf + 1) if fs is not None else 0
    data = None
    # ⭐ **`LOCK` 을 보낸 *뒤에* 관측한 `RBUF`** (-1 = 안 잠근 조건).
    # ⚠️ 첫 판은 이것을 `f0`(LOCK 을 보내기 **전**)에서 뽑아, 잠긴 순간을 한
    # 번도 보지 못한 채 늘 0 을 기록했다 (2026-09-01 실기에서 드러났다).
    rbuf_locked = -1
    t0 = time.monotonic()
    try:
        if cond == 'idle':
            time.sleep(args.hold)
        elif cond == 'lock':
            u.cmd('LOCK%d' % buf_n)
            rbuf_locked = parse.lock_state(u.frame())[0]
            time.sleep(args.hold)
        else:
            if cond == 'fetch':
                u.cmd('LOCK%d' % buf_n)
                rbuf_locked = parse.lock_state(u.frame())[0]
            # ⚠️ 크기에서 유도한 상한(344 MiB -> 344초)은 실측의 69배라 링크가
            # 죽으면 그만큼 매달린다 (DevNote 7장 F5).  기본을 조여 둔다.
            for _ in range(max(1, args.fetch_repeat)):
                data = u.link.fetch(fs.base, fs.data_bytes, args.fetch_timeout)
    finally:
        if cond in ('lock', 'fetch'):
            try:
                u.cmd('LOCK0')
            except (ArchonError, OSError) as exc:
                print('  ⚠️ LOCK0 실패: %s' % exc)
    elapsed = time.monotonic() - t0

    f1 = u.frame()
    p1 = write_pos(f1, ctx['stride'])
    if p1 is None:
        return None
    pos1, wframe1, _ = p1

    if pos1 < pos0:
        # ⚠️ 되감김·재시작.  거짓 0 을 보고하느니 표본을 버린다.
        print('  ⚠️ 진행량이 뒤로 갔다 (%d -> %d) -- 표본을 버린다' % (pos0, pos1))
        return None

    _, wbuf0 = parse.lock_state(f0)
    _, wbuf1 = parse.lock_state(f1)
    mib = (fs.data_bytes / (1 << 20) * max(1, args.fetch_repeat)) \
        if data is not None else 0.0
    # ⭐⭐ **사강 보정** (2026-09-01 실측으로 필요해졌다).
    #
    # 프레임과 프레임 사이에는 엔진이 **라인을 안 쓰는 구간**이 있다 -- 타이밍
    # 스크립트의 `NOINT; CALL NoIntUnit(NoIntMS)` 다.  창이 경계를 넘으면 그만큼
    # 희석되어 **조건이 아니라 운(경계를 몇 번 넘었나)이 속도를 가른다**:
    # `--hold 20` 에서 경계 1회는 358.7, 2회는 349.5 로 나왔는데 **둘 다 실제로는
    # 368.0** 이었다.  경계 횟수만큼 빼면 그 흔들림이 사라진다.
    #
    # ⚠️ **사강 = `NoIntMS` 는 모형이다** -- 실측(0.50·1.00초)과 ACF 값(500 ms)이
    # 1% 안에서 맞았지만 `HorizontalSWShift`·`CLAMP` 같은 잔여가 남아 있다.
    # 그래서 원값(`rate_raw`)을 CSV 에 함께 남기고, 요약이 조건마다 **최소~최대**
    # 를 같이 찍는다 -- 보정이 맞으면 그 폭이 좁아진다.
    nframes = max(wframe1 - wframe0, 0)
    active = elapsed - nframes * float(ctx.get('dead_s', 0.0))
    if active <= 0:
        print('  ⚠️ 사강이 창(%.2f초)보다 크다 -- 표본을 버린다' % elapsed)
        return None
    s = Sample(cond=cond, elapsed=elapsed, active=active, dlines=pos1 - pos0,
               rate=(pos1 - pos0) / active,
               rate_raw=(pos1 - pos0) / elapsed if elapsed > 0 else 0.0,
               buf=buf_n, rbuf=rbuf_locked, wbuf0=wbuf0, wbuf1=wbuf1,
               frame=(fs.frame if fs is not None else -1),
               wframe=wframe0, wlines=wlines0, mib=mib,
               # ⭐ 경계를 몇 번 넘었나 -- 보정의 근거이자 stride 의 증인이다.
               nframes=nframes,
               # ⭐ fetch 속도가 곧 **정지 길이**다 -- 같이 재 둔다.
               mibps=(mib / elapsed) if (mib and elapsed > 0) else 0.0)

    # ⚠️ 한 장이 344 MiB 다 -- 상한을 두지 않으면 라운드 몇 번에 수 GB 가 쌓인다.
    if data is not None and args.save_fits:
        if ctx['saved'] < args.save_max:
            s['fits'] = save_fits(args.save_fits, u.tag, cond, fs, data,
                                  stall_rows.get(fs.frame), ctx['saved'] + 1)
            ctx['saved'] += 1
        elif not ctx.get('save_warned'):
            print('  ⚠️ FITS 를 %d장까지만 남긴다 (--save-max)' % args.save_max)
            ctx['save_warned'] = True
    return s


def save_fits(save_dir: str, tag: str, cond: str, fs: parse.FrameStatus,
              data: bytearray, stall_row: int | None, seq: int) -> str:
    """받아 온 프레임을 FITS 로 떨군다.  ⚠️ **과학 산출물이 아니다.**

    기하는 컨트롤러가 보고한 **탭 배열 그대로**(width x height)다 -- raw spec 의
    pair 기하로 접지 않는다.  행·열 프로파일을 보려는 것이 목적이라 그 편이 낫다.
    """
    import numpy as np
    from astropy.io import fits as pyfits

    os.makedirs(save_dir, exist_ok=True)
    dtype = np.dtype('<u4' if fs.samplemode else '<u2')
    # ⚠️ `bytes(data)` 로 감싸면 344 MiB 를 한 벌 더 뜬다 -- bytearray 를 그대로
    # 넘겨 **복사 없이** 본다.
    arr = np.frombuffer(data, dtype=dtype,
                        count=fs.width * fs.height).reshape(fs.height, fs.width)
    hdu = pyfits.PrimaryHDU(arr)
    h = hdu.header
    h['ORIGIN'] = ('ics_archon_buftest', 'LOCK/FETCH stall test -- NOT science')
    h['UNITTAG'] = (tag, 'controller tag')
    h['TESTCOND'] = (cond, 'idle | lock | fetch | nolock')
    h['ARCFRAME'] = (fs.frame, 'Archon buffer frame number')
    h['ARCBUF'] = (fs.buf + 1, 'Archon frame buffer (1-based)')
    if stall_row is not None:
        # ⭐ 열 프로파일을 어느 행에서 봐야 하는지 (DevNote 8.13).
        h['STALLROW'] = (stall_row, 'BUFnLINES when a stall began on this frame')
    else:
        h['STALLROW'] = (-1, 'no stall recorded for this frame')
    h['DATE'] = (datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'), 'UTC')
    # ⚠️ **일련번호를 앞에 둔다.**  첫 판은 이름이 `<tag>.<cond>.f<프레임>`
    # 뿐이라, 라운드가 달라도 프레임 번호가 같으면 `overwrite=True` 로 **조용히
    # 덮였다** (2026-09-01: 4장 세었는데 파일은 셋이었다).
    path = os.path.join(save_dir, '%s.%02d.%s.f%06d.fits'
                        % (tag, seq, cond, fs.frame))
    hdu.writeto(path, overwrite=True)
    return path


def stage_stall(u: Unit, args, config: dict[str, str],
                configline: dict[str, int]) -> list[Sample]:
    block('2단계  2x2 시험  ⚠️ 전원을 켜고 CCD 를 연속으로 읽어낸다')

    slots = param_slots(config)
    for name in ('ContinuousExposures', 'IntMS'):
        if name not in slots:
            raise ArchonError('ACF 에 %s 파라미터가 없다 -- 이 ACF 로는 못 돌린다'
                              % name)
    say(OK, '파라미터 슬롯: %s'
        % ', '.join('%s=%s' % (n, slots[n]) for n in sorted(slots))[:200])

    # ⚠️ **되돌릴 원래 값을 먼저 적어 둔다.**  `IntMS` 를 0 으로 바꿔 놓고 나가면
    # 다음 사람이 노출을 걸었을 때 조용히 BIAS 가 나온다.
    original = {name: config[slots[name]]
                for name in ('IntMS', 'ContinuousExposures')}
    say(OK, 'ACF 원래 값 -- %s'
        % ' · '.join('%s' % v for v in original.values()))

    # ⭐ **진행량의 stride 는 `LINECOUNT` 다** (`BUFnHEIGHT` 가 아니다).
    # 근거와 그렇게 안 했을 때 무슨 일이 나는지는 `write_pos()` 머리말에.
    stride = _i(config, 'LINECOUNT', 0)
    if stride <= 0:
        raise ArchonError('ACF 에 LINECOUNT 가 없다 -- 진행량을 못 잰다')
    height = _i(u.frame(), 'BUF1HEIGHT', 0)
    say(OK, 'stride = LINECOUNT %d  (BUF1HEIGHT %d)' % (stride, height),
        '둘이 다르면 FRAMEMODE=2(split) 다 -- 라인클록 하나가 두 행을 채운다'
        if height and height != stride else '')

    # ⭐ 프레임 사이 사강 -- 타이밍 스크립트의 `NoIntUnit(NoIntMS)` 다.
    dead_ms = 0
    if 'NoIntMS' in slots:
        try:
            dead_ms = int(config[slots['NoIntMS']].split('=')[1])
        except (IndexError, ValueError):
            dead_ms = 0
    say(OK if dead_ms else WARN, '사강 = NoIntMS %d ms x 경계 횟수' % dead_ms,
        '경계를 넘은 창은 그만큼 빼고 잰다 -- 안 빼면 조건이 아니라 운이 '
        '속도를 가른다' if dead_ms
        else 'ACF 에서 NoIntMS 를 못 읽었다 -- 보정 없이 잰다')

    samples: list[Sample] = []
    ctx: dict = {'stall_rows': {}, 'saved': 0, 'stride': stride,
                 'dead_s': dead_ms / 1000.0}
    powered = False
    try:
        u.power_on(args.poweron_wait)
        powered = True
        say(OK, 'POWERON -- POWER=4 확인 (%.0f초 대기 안에서)' % args.poweron_wait)

        # 연속 노출을 건다.  타이밍 스크립트의 Start: 가 곧바로 Continuous: 로
        # 가서 멈추지 않는다 (DevNote 8.13).
        u.set_param(configline, slots['IntMS'], 'IntMS=%d' % args.exp_ms)
        u.set_param(configline, slots['ContinuousExposures'],
                    'ContinuousExposures=1')
        u.load_params()
        say(OK, '연속 노출 시작 -- IntMS=%d' % args.exp_ms)

        # 엔진이 실제로 돌기 시작할 때까지 기다린다.
        # ⚠️ **`WBUF > 0` 만으로는 "도는 중" 이 아니다** -- 프레임이 완료된
        # 뒤에도 `WBUF` 가 그 버퍼를 가리킨 채 남는다(2026-09-01 실측:
        # `WBUF=1` · `BUF1COMPLETE=1` · 엔진 정지).  그 상태로 빠져나가면
        # 첫 라운드 `idle` 이 **0 행/초**로 잡혀 기준선을 오염시킨다.
        # 그래서 **진행량이 실제로 늘어나는 것**을 확인하고 나간다.
        deadline = time.monotonic() + 60.0
        prev = None
        while time.monotonic() < deadline:
            now = write_pos(u.frame(), stride)
            if prev is not None and now is not None and now[0] > prev:
                break
            prev = now[0] if now is not None else None
            time.sleep(1.0)
        else:
            raise ArchonError('60초 안에 엔진이 쓰기 시작하지 않았다 -- '
                              'LOADPARAMS·타이밍·Sync In 을 보라')

        # ⚠️ ABBA -- 라운드마다 순서를 뒤집어 순서 효과를 갈라낸다.
        for r in range(args.rounds):
            order = CONDITIONS if r % 2 == 0 else tuple(reversed(CONDITIONS))
            print('\n-- 라운드 %d/%d  (%s)' % (r + 1, args.rounds, ' '.join(order)))
            for cond in order:
                for _attempt in range(3):
                    s = run_condition(u, cond, args, ctx)
                    if s is not None:
                        break
                    time.sleep(2.0)
                if s is None:
                    print('  %-7s -- 표본 없음 (3회 시도)' % cond)
                    continue
                s['round'] = r + 1
                samples.append(s)
                print('  %-7s %6.2f초  %6d행  %7.1f 행/초%s   '
                      'RBUF=%s WBUF=%d->%d%s%s'
                      % (cond, s['elapsed'], s['dlines'], s['rate'],
                         ('*%d' % s['nframes']) if s['nframes'] else '  ',
                         ('-' if s['rbuf'] < 0 else
                          ('%d' % s['rbuf'] if s['rbuf'] == s['buf']
                           else '%d(기대%d)' % (s['rbuf'], s['buf']))),
                         s['wbuf0'], s['wbuf1'],
                         ('  %.0f MiB/s' % s['mibps']) if s['mibps'] else '',
                         ('  ' + os.path.basename(s['fits'])) if 'fits' in s else ''))
    finally:
        # ⚠️ 무슨 일이 있어도 **ACF 원래 값으로** 되돌린다 -- 연속 노출을 켠 채,
        # 또는 IntMS 를 0 으로 둔 채 나가면 다음 사람이 조용히 당한다.
        for name, value in original.items():
            try:
                u.set_param(configline, slots[name], value)
            except (ArchonError, OSError, KeyError) as exc:
                print('\n  ⚠️ %s 되돌리기 실패: %s' % (name, exc))
        try:
            u.load_params()
            print('\n  ACF 원래 파라미터로 되돌렸다 (%s)'
                  % ' · '.join(original.values()))
        except (ArchonError, OSError) as exc:
            print('\n  ⚠️ LOADPARAMS 실패 -- 파라미터가 시험값으로 남았다: %s' % exc)
        if powered:
            u.power_off()
            print('  POWEROFF')
    return samples


# ---------------------------------------------------------------------------
# 요약
# ---------------------------------------------------------------------------

def summarise(samples: list[Sample]) -> None:
    block('요약')
    if not samples:
        say(BAD, '표본이 없다 -- 판정할 수 없다')
        return

    med: dict[str, float] = {}
    print('  %-8s %5s %10s %17s %10s'
          % ('조건', '표본', '중앙값[행/초]', '최소~최대', '기준선 대비'))
    base = None
    for cond in CONDITIONS:
        rates = [s['rate'] for s in samples if s['cond'] == cond]
        if not rates:
            continue
        med[cond] = statistics.median(rates)
        if cond == 'idle':
            base = med[cond]
    for cond in CONDITIONS:
        if cond not in med:
            continue
        ratio = (med[cond] / base * 100.0) if base else float('nan')
        rs = [x['rate'] for x in samples if x['cond'] == cond]
        print('  %-8s %5d %10.1f %8.1f~%-8.1f %9.0f%%'
              % (cond, len(rs), med[cond], min(rs), max(rs), ratio))

    if base is None or base <= 0:
        say(BAD, '기준선(idle)을 못 잡았다 -- 엔진이 안 돌았을 수 있다')
        return

    def frac(c: str) -> float:
        return med[c] / base if c in med else float('nan')

    # ⭐ 판정 기준은 **실험 전에 못박은 것**이다 (DevNote 8.16).
    stalled = [c for c in ('lock', 'fetch', 'nolock')
               if c in med and frac(c) < 0.20]
    if not stalled:
        say(WARN, '넷 다 기준선 근처다 -- 이 판에서는 정지가 재현되지 않았다',
            '결과에 FW 판·백플레인 REV 를 반드시 붙일 것')
    elif 'lock' in stalled:
        say(BAD, 'LOCK 만으로도 엔진이 멈춘다 (lock=%.0f%%)' % (frac('lock') * 100),
            'lock_buffer=false 가 프레임당 수 초를 번다 -- 설계를 다시 본다')
    elif 'fetch' in stalled and 'nolock' in stalled:
        say(OK, 'FETCH 가 원인이다 (fetch=%.0f%% nolock=%.0f%%, lock 은 정상)'
            % (frac('fetch') * 100, frac('nolock') * 100),
            'LOCK 은 무관하다 -- lock_buffer 는 켜 두고, 다음 노출을 fetch 뒤로 '
            '미루는 처방으로 간다 (DevNote 8.14)')
    else:
        say(WARN, '조건별로 갈렸다 -- ' + ' '.join(
            '%s=%.0f%%' % (c, frac(c) * 100) for c in med),
            '표본을 늘리고(--rounds) 다시 본다')


def write_csv(path: str, samples: list[Sample]) -> None:
    cols = ('round', 'cond', 'elapsed', 'active', 'dlines', 'rate',
            'rate_raw', 'nframes', 'buf', 'rbuf', 'wbuf0', 'wbuf1', 'frame',
            'wframe', 'wlines', 'mib', 'mibps', 'fits')
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for s in samples:
            w.writerow(s)
    print('\n  CSV -> %s (%d행)' % (path, len(samples)))


# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description='LOCK/FETCH 가 readout 을 멈추는가 -- 독립 시험 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--host', required=True, help='컨트롤러 IP')
    p.add_argument('--port', type=int, default=4242)
    p.add_argument('--tag', default='MK', help='기록용 이름표 (기본 MK)')
    p.add_argument('--acf', required=True,
                   help='이 컨트롤러에 올라가 있는 ACF -- [SYSTEM] 대조와 '
                        '파라미터 줄번호에 쓴다 (적용하지는 않는다)')
    p.add_argument('--stage', choices=('info', 'stall'), default='info',
                   help='info: 읽기 전용 (기본) / stall: 전원을 켜고 2x2 시험')
    p.add_argument('--rounds', type=int, default=4, help='ABBA 라운드 수 (기본 4)')
    p.add_argument('--hold', type=float, default=5.0,
                   help='idle/lock 이 기다리는 시간 [s] (기본 5)')
    p.add_argument('--exp-ms', type=int, default=0,
                   help='IntMS -- 0 이면 BIAS 연속 (기본 0, 가장 얇은 조건)')
    p.add_argument('--fetch-repeat', type=int, default=1,
                   help='fetch 조건에서 같은 버퍼를 몇 번 받나 -- 정지를 늘려 '
                        '단차를 증폭한다 (기본 1)')
    p.add_argument('--fetch-timeout', type=float, default=60.0,
                   help='FETCH 한 번의 상한 [s] (기본 60.  실측 ~5초)')
    p.add_argument('--save-max', type=int, default=4,
                   help='FITS 를 최대 몇 장까지 남기나 (기본 4 -- 장당 344 MiB)')
    p.add_argument('--yes', action='store_true',
                   help='--stage stall 의 확인 물음을 건너뛴다')
    p.add_argument('--poweron-wait', type=float, default=12.0,
                   help='POWERON 뒤 대기 [s].  ⚠️ CCD flush 대기라 줄이지 말 것')
    p.add_argument('--csv', help='표본을 CSV 로 남길 경로')
    p.add_argument('--save-fits', metavar='DIR',
                   help='fetch 한 프레임을 FITS 로 떨굴 폴더 (STALLROW 카드 포함)')
    args = p.parse_args()

    config, configline, acf_system = read_acf(args.acf)
    u = Unit(args.host, args.port, args.tag)
    samples: list[Sample] = []
    try:
        u.connect()
        say(OK, '접속 %s:%d' % (args.host, args.port))
        system = stage_info(u, acf_system, args.acf)
        if args.stage == 'stall':
            # ⚠️ 여기서부터 **전원을 켜고 CCD 를 연속으로 읽어낸다.**  잘못된
            # 대상에 흘러들어가는 것을 막으려고 무엇을 만질지 되읽어 준다.
            if not args.yes:
                print('\n  ⚠️ 이제 %s (%s, FW %s) 의 전원을 켜고 CCD 를 '
                      '연속으로 읽어낸다.' % (args.host, args.tag,
                                            system.get('BACKPLANE_VERSION', '?')))
                print('     본편·STA GUI 가 이 컨트롤러에 붙어 있지 않아야 한다.')
                if input('     계속하려면 yes 를 치라: ').strip().lower() != 'yes':
                    print('     중단했다.')
                    return 0
            samples = stage_stall(u, args, config, configline)
            if args.csv:
                write_csv(args.csv, samples)
            summarise(samples)
    except (ArchonError, OSError) as exc:
        print('\n*** 실패: %s' % exc)
        return 2
    finally:
        u.close()

    bad = sum(1 for m, _ in _verdicts if m == BAD)
    print('\n판정 %d건 -- 문제 %d' % (len(_verdicts), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""가짜 Archon 컨트롤러 -- **실기 없이 전 경로를 돌리는 상대역.**

프로토콜(매뉴얼 p.45)과 명령 응답(p.46-52)을 규격대로 흉내낸다.  실물이 없는
동안 이것이 유일한 왕복 검증 수단이므로, 흉내내는 범위를 분명히 적어 둔다.

**흉내내는 것**
  * 프레이밍 -- `>xxCMD\\n` / `<xxRESPONSE\\n` / `<xx:`+1024B / `?xx\\n` /
    **인식 못 한 명령은 무응답**
  * `SYSTEM` · `STATUS` · `FRAME` 의 필드 이름과 형
  * `WCONFIG`/`RCONFIG`/`CLEARCONFIG`/`APPLYALL`/`APPLYSYSTEM`
  * `POWERON`/`POWEROFF` -- ⭐ `POWERON` 은 **이 세션의 `APPLYALL`** 을 전제한다
    (매뉴얼 p.51, 실기 `?02` 거부 2026-09-01 -- DevNote 10.2).  `applied=False`
    로 만들거나 `REBOOT` 를 보내면 그 상태다
  * `REBOOT` -- 프레임 카운터·버퍼·적용 상태를 지운다 (10.7: 카운터를 지우는 것은
    `REBOOT`·백플레인 전원만이고 CCD `POWERON`/`WARMBOOT` 는 아니다)
  * `framemode=2` -- split 모사: `BUFnHEIGHT` 는 그대로인데 `BUFnLINES` 는
    `LINECOUNT`(= height/2)에서 멈춘다 (10.3 -- 이 차이를 모사하지 않아
    `parse.progress` 의 50% 결함이 시험을 다 통과했다)
  * `LOADPARAMS` -> 적분(`IntMS`) -> 독출(라인 진행) -> 프레임 완료 -> `FETCH`
  * 픽셀은 **결정적 패턴**(`y*width + x`)이라 배치·엔디언을 값으로 확인할 수 있다

**흉내내지 않는 것 (그래서 실기에서만 드러나는 것)**
  * 실제 독출 시간·진행률의 거동
  * 모듈 슬롯 구성의 실제 값 (`STATUS` 필드는 기본값을 준다)
  * ACF 문법 해석 -- 설정 줄을 문자열로만 보관한다
"""

from __future__ import annotations

import socket
import threading
import time

#: 기본 `STATUS` 응답 -- 실제 필드 이름 그대로 (매뉴얼 p.47-49).
DEFAULT_STATUS = {
    'POWERGOOD': '1',
    'BACKPLANE_TEMP': '31.5',
    # 규격 5.6.1절의 열 자리 (Mod1·2·3·4·5·8·9·10·11) + 자리를 차지하지 않는
    # Mod6·Mod7.  **일부러 둘을 함께 보고하게 뒀다** -- 컨트롤러가 보고해도
    # 카드에는 안 실린다는 것이 자리 표의 뜻이고, 그 배제를 시험이 밟는다.
    'MOD1/TEMP': '30.1', 'MOD2/TEMP': '30.2',
    'MOD3/TEMP': '30.3', 'MOD4/TEMP': '30.4',
    'MOD5/TEMP': '32.0', 'MOD6/TEMP': '32.5',
    'MOD7/TEMP': '33.0', 'MOD8/TEMP': '33.5',
    'MOD9/TEMP': '34.1', 'MOD10/TEMP': '34.2', 'MOD11/TEMP': '34.3',
    'P2V5_V': '2.512', 'P2V5_I': '4.698',
    'P5V_V': '5.023', 'P5V_I': '4.487',
    'P6V_V': '5.834', 'P6V_I': '2.176',
    'N6V_V': '-5.945', 'N6V_I': '0.465',
    'P17V_V': '16.956', 'P17V_I': '0.454',
    'N17V_V': '-17.067', 'N17V_I': '0.443',
    'P35V_V': '35.089', 'P35V_I': '0.032',
}

#: **매뉴얼 p.47 이 나열한 건강 필드를 다 내는** `STATUS` -- `DEFAULT_STATUS`
#: 와 갈라 둔 것이 의도다.
#:
#: ⚠️ **둘 다 실재하는 경우다.**  `DEFAULT_STATUS` 는 그 필드들을 **보고하지
#: 않는** 응답이고(구 펌웨어 · F2 원칙이 지켜야 하는 쪽), 이것은 다 보고하는
#: 응답이다.  기본을 이쪽으로 바꾸면 "보고 없는 필드를 이상으로 세지 않는다"
#: 를 검사하는 시험들이 통째로 무의미해지고, 반대로 이것이 없으면 감시 기록의
#: `valid`/`count`/`fresh`/`log_n`/`power` 열이 **한 번도 실값으로 안 돌아간다.**
#:
#: 값의 근거: `VALID=1`(p.47) · `COUNT` 는 상태 갱신 횟수 · `LOG=0` ·
#: `POWER=4`(On) · `OVERHEAT=0`.
#:
#: `COUNT` 는 `FakeArchon(count_step=)` 이 `STATUS` 응답마다 올린다 (기본 1,
#: `0` 이면 얼어붙는다 -- 감시 기록의 `fresh=0` 경로를 밟는 설정이다).
#: ⚠️ **실기는 질의가 아니라 자기 주기로 갱신한다** -- 두 번 연달아 물으면 같은
#: 값이 올 수 있다.  그래서 `fresh` 는 "새로 잰 값인가" 의 **신호**이지 보장이
#: 아니다.
FULL_STATUS = dict(DEFAULT_STATUS, VALID='1', COUNT='100', LOG='0',
                   POWER='4', OVERHEAT='0')

#: 기본 `SYSTEM` 응답 -- **실기 science 구성 그대로** (`acf/KMTK_SCI_113_
#: STA0200_R2608_MK.acf` 실측, 2026-08-27).  장착은 1·2·3·4·5·8·9·10·11 이고
#: 6·7·12 는 빈 슬롯(형 0) -- 규격 5.6.1절의 **열 자리와 정확히 같다.**
#:
#: ⚠️ 종전 값은 "AD 모듈이 슬롯 5~8"(매뉴얼 p.20 의 잠정안)이었다.  가짜가
#: 실기와 다르면 **실기에서만 나는 결함을 시험이 못 잡는다** -- 실제로
#: `_log_module_map()`/probe 의 슬롯 판정이 정상 구성에서 경고를 내던 것을
#: 이 시험들이 통과시켰다.
#:
#: 형 17(ADM)·18(HVYBias)은 **매뉴얼 밖**이다 (p.46 은 "16+: Unknown").
#: KMTC/KMTS 는 `MOD9_TYPE=18` 이고 KMTK 벤치기는 8(HVXBias) 이다.
DEFAULT_SYSTEM = {
    'BACKPLANE_TYPE': '1', 'BACKPLANE_REV': '5',
    'BACKPLANE_VERSION': '1.0.408',
    'BACKPLANE_ID': '0024498A715E301C',
    'MOD_PRESENT': '0DBF',
    'MOD1_TYPE': '10', 'MOD2_TYPE': '1', 'MOD3_TYPE': '1', 'MOD4_TYPE': '9',
    'MOD5_TYPE': '17', 'MOD6_TYPE': '0', 'MOD7_TYPE': '0', 'MOD8_TYPE': '17',
    'MOD9_TYPE': '8', 'MOD10_TYPE': '1', 'MOD11_TYPE': '1', 'MOD12_TYPE': '0',
}

BURST = 1024


class FakeArchon(threading.Thread):
    """가짜 컨트롤러 하나.  `port` 로 접속한다."""

    daemon = True

    def __init__(self, *, width: int = 8, height: int = 4,
                 samplemode: int = 0, readout_ticks: int = 4,
                 tick: float = 0.02, status: dict | None = None,
                 system: dict | None = None,
                 status_delay: float = 0.0, nbuf: int = 2,
                 fresh: bool = False,
                 count_step: int = 1,
                 power_ramp: int = 0,
                 unknown: tuple[str, ...] = (),
                 reject: tuple[str, ...] = (),
                 applied: bool = True,
                 framemode: int = 0,
                 linecount: int | None = None) -> None:
        super().__init__()
        self.width = width
        self.height = height
        #: `FRAMEMODE` -- 2 면 split: 앞 절반 탭이 버퍼 위쪽, 뒤 절반이 아래쪽에
        #: 쓰여 라인클록 하나가 두 행을 채운다 (p.56·70).  `BUFnLINES` 의 상한이
        #: `linecount` 다 (기본 = height, split 이면 height // 2).
        self.framemode = int(framemode)
        self.linecount = int(linecount) if linecount else (
            height // 2 if self.framemode == 2 else height)
        #: 이 세션에서 `APPLYALL` 이 있었나 -- `POWERON` 의 전제 (p.51).  기본은
        #: "이미 적용된 컨트롤러" 라 종전 시험이 그대로 돈다.
        self.applied = bool(applied)
        self.samplemode = samplemode
        self.readout_ticks = max(readout_ticks, 1)
        self.tick = tick
        self.status = dict(DEFAULT_STATUS if status is None else status)
        self.system = dict(DEFAULT_SYSTEM if system is None else system)
        #: `STATUS` 를 이만큼 늦게 답한다 -- 시한 초과 경로를 재현한다.
        self.status_delay = status_delay
        self.count_step = count_step
        #: `POWERON` 뒤 `POWER` 가 **`4` 로 오르기까지 걸리는 STATUS 질의 횟수.**
        #:
        #: 실기의 바이어스 램프를 흉내낸다 -- 매뉴얼 p.47 의 `3`(Intermediate,
        #: 일부 모듈만 올라왔다)을 이만큼 낸 뒤에 `4` 로 간다.  ⚠️ **`POWER` 를
        #: 안 내는 `STATUS`(`DEFAULT_STATUS`)에는 영향이 없다** -- 그것도 실재
        #: 하는 경우(구 펌웨어)이고, 없는 필드를 만들어 내면 "보고 없는 필드를
        #: 이상으로 세지 않는다" 를 검사하는 시험이 무의미해진다.
        self.power_ramp = power_ramp
        self._ramp_left = 0
        #: 이 접두로 시작하는 명령은 **무응답** (매뉴얼 p.45 의 "ignored").
        self.unknown = tuple(unknown)
        #: 이 접두로 시작하는 명령은 `?xx` 로 거부한다.
        self.reject = tuple(reject)

        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('127.0.0.1', 0))
        self.srv.listen(8)
        self.port = self.srv.getsockname()[1]

        self.config: dict[int, str] = {}
        self.powered = False
        self.accepts = 0
        #: 받은 명령 이름 순서 -- 시퀀스 검증용.
        self.seen: list[str] = []
        self._lock = threading.Lock()

        # 프레임 버퍼 -- **여러 개다.**  BIGBUF=1 이면 2개, 기본은 3개
        # (매뉴얼 p.49).  하나로 흉내내면 "앞 프레임의 자료가 아직 있나" 를
        # 시험할 수 없고, 그건 raw 한 장이 남의 노출 픽셀을 담는 결함을
        # 조용히 통과시킨다.
        self.nbuf = max(min(int(nbuf), 3), 1)
        # 주소는 유닛마다 다르다 (101: 0x20000000 / 113: 0xA0000000, BIGBUF 간격은
        # 768 MiB -- DevNote 10.8).  본편은 계산하지 않고 `BUFnBASE` 를 읽으므로
        # 여기 값은 시험에 무관하다 -- 실기 배치로 읽지 말 것.
        self.bufs = [{'frame': 0, 'complete': 0, 'lines': 0,
                      'base': 0xA0000000 + i * 0x10000000}
                     for i in range(3)]
        # `fresh=True` 는 **`REBOOT`·백플레인 전원 투입 직후**다 -- 완료된
        # 프레임이 하나도 없어서 `parse.newest()` 가 -1 을 준다 (CCD `POWERON`
        # 은 버퍼를 지우지 않는다 -- DevNote 10.7).  실기 첫 실행의 상태이고,
        # 그 경로를 흉내내지 않으면 첫 노출이 버려지는 결함을 못 잡는다.
        if not fresh:
            self.bufs[0]['complete'] = 1
        self.frame_no = 0
        self.wbuf = 0
        # `RBUF=0` 은 "읽기용으로 잠긴 버퍼가 없다" 다 -- 전원 투입 직후의
        # 상태이고, 그때 `parse.newest()` 가 -1 을 준다.
        self.rbuf = 0 if fresh else 1
        #: `LOCKn` 으로 읽기 고정된 버퍼 번호 (1-기준).  0 = 없음.
        self.locked = 0
        self._next = 0
        self._stop = False

    # -- 서버 -------------------------------------------------------------

    def run(self) -> None:
        while not self._stop:
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            self.accepts += 1
            threading.Thread(target=self._serve, args=(conn,),
                             daemon=True).start()

    def shutdown(self) -> None:
        self._stop = True
        try:
            self.srv.close()
        except OSError:
            pass

    def _serve(self, conn: socket.socket) -> None:
        conn.settimeout(30)
        buf = b''
        while not self._stop:
            try:
                chunk = conn.recv(65536)
            except (OSError, socket.timeout):
                return
            if not chunk:
                return
            buf += chunk
            while b'\n' in buf:
                line, _, buf = buf.partition(b'\n')
                if not line.startswith(b'>'):
                    continue
                ref, cmd = line[1:3], line[3:].decode('ascii', 'replace')
                try:
                    self._handle(conn, ref, cmd)
                except OSError:
                    return

    # -- 명령 -------------------------------------------------------------

    def _reply(self, conn, ref: bytes, body: str = '') -> None:  # noqa: ANN001
        conn.sendall(b'<' + ref + body.encode('ascii') + b'\n')

    def _handle(self, conn, ref: bytes, cmd: str) -> None:  # noqa: ANN001
        name = cmd.split('=')[0][:12]
        with self._lock:
            self.seen.append(cmd.split('=')[0][:20])

        if cmd.startswith(self.unknown) and self.unknown:
            return                              # 무응답 (p.45)
        if cmd.startswith(self.reject) and self.reject:
            conn.sendall(b'?' + ref + b'\n')
            return

        if cmd == 'SYSTEM':
            self._reply(conn, ref, self._kv(self.system))
        elif cmd == 'STATUS':
            if self.status_delay:
                time.sleep(self.status_delay)
            # `COUNT` 는 컨트롤러가 상태 블록을 갱신한 횟수다 (p.47) -- 여기서는
            # 응답마다 올린다.  ⚠️ 실기는 **자기 주기**로 갱신하므로 두 번 연달아
            # 물으면 같은 값이 올 수 있다.  `count_step=0` 이 그 경우다.
            if self._ramp_left and 'POWER' in self.status:
                self._ramp_left -= 1
                self.status['POWER'] = '3' if self._ramp_left else '4'
            if self.count_step and 'COUNT' in self.status:
                try:
                    self.status['COUNT'] = str(int(self.status['COUNT'])
                                               + self.count_step)
                except ValueError:
                    pass
            self._reply(conn, ref, self._kv(self.status))
        elif cmd == 'FRAME':
            self._reply(conn, ref, self._kv(self._frame_fields()))
        elif cmd == 'CLEARCONFIG':
            self.config.clear()
            self._reply(conn, ref)
        elif cmd.startswith('WCONFIG'):
            line = int(cmd[7:11], 16)
            self.config[line] = cmd[11:]
            self._reply(conn, ref)
        elif cmd.startswith('RCONFIG'):
            line = int(cmd[7:11], 16)
            self._reply(conn, ref, self.config.get(line, ''))
        elif cmd.startswith('LOCK'):
            try:
                self.locked = int(cmd[4:])
            except ValueError:
                conn.sendall(b'?' + ref + b'\n')
                return
            self._reply(conn, ref)
        elif cmd in ('APPLYALL', 'APPLYSYSTEM', 'APPLYCDS', 'LOADTIMING'):
            if cmd == 'APPLYALL':
                self.applied = True          # p.51 -- POWERON 의 전제
            self._reply(conn, ref)
        elif cmd == 'REBOOT':
            # FPGA 재적재 -- 카운터·버퍼·적용 상태가 지워진다 (DevNote 10.7·10.2).
            with self._lock:
                self.applied = False
                self.powered = False
                self.frame_no = 0
                for b in self.bufs:
                    b.update(frame=0, complete=0, lines=0)
                self.rbuf = self.wbuf = self.locked = 0
            self._reply(conn, ref)
        elif cmd == 'POWERON' and not self.applied:
            # p.51 "An APPLYALL is required before this operation" -- 실기는
            # `?02` 로 거부한다 (2026-09-01 첫 관문, DevNote 10.2).
            conn.sendall(b'?' + ref + b'\n')
        elif cmd == 'POWERON':
            # **`POWER` 를 같이 움직인다.**  종전에는 `powered` 만 바뀌어서
            # `STATUS` 의 `POWER` 가 `POWERON` 과 무관하게 늘 `4` 였다 -- 그
            # 가짜로는 "응답은 왔는데 전원이 안 올라왔다" 를 한 번도 못 밟는다
            # (`controller._await_power()` 가 보는 바로 그 경우).
            self.powered = True
            if 'POWER' in self.status:
                self._ramp_left = self.power_ramp
                self.status['POWER'] = '3' if self.power_ramp else '4'
            self._reply(conn, ref)
        elif cmd == 'POWEROFF':
            self.powered = False
            self._ramp_left = 0
            if 'POWER' in self.status:
                self.status['POWER'] = '2'      # Off (p.47)
            self._reply(conn, ref)
        elif cmd == 'LOADPARAMS':
            self._reply(conn, ref)
            threading.Thread(target=self._expose, daemon=True).start()
        elif cmd.startswith('FETCH'):
            self._fetch(conn, ref, cmd)
        else:
            # 모르는 명령이지만 시험이 막히지 않게 빈 성공을 준다.
            # (**무응답을 보고 싶으면 `unknown=` 에 넣는다.**)
            self._reply(conn, ref)
        del name

    @staticmethod
    def _kv(fields: dict) -> str:
        return ' '.join('%s=%s' % kv for kv in fields.items())

    def _frame_fields(self) -> dict:
        # ⚠️ **잠금 중에는 `RBUF` 가 잠긴 버퍼를 가리킨다** (매뉴얼 p.50 --
        # "Current buffer number locked for reading").  ✅ **2026-09-01 실기 확인**
        # -- 두 FW(1252·1261)에서 `LOCKn` 뒤 `RBUF` 가 잠근 버퍼를 가리켰다,
        # 15/15 (`ics_archon` DevNote 10.4).  이 모사는 실기와 같다.
        # 잠금이 없을 때는 종전대로 "마지막 완료 버퍼" 를 준다.
        f = {'RBUF': str(self.locked or self.rbuf), 'WBUF': str(self.wbuf)}
        for n in (1, 2, 3):
            b = self.bufs[n - 1]
            live = n <= self.nbuf
            f['BUF%dSAMPLE' % n] = str(self.samplemode if live else 0)
            f['BUF%dCOMPLETE' % n] = str(b['complete'])
            f['BUF%dMODE' % n] = '0'
            f['BUF%dBASE' % n] = str(b['base'] if live else 0)
            f['BUF%dFRAME' % n] = str(b['frame'])
            f['BUF%dWIDTH' % n] = str(self.width if live else 0)
            f['BUF%dHEIGHT' % n] = str(self.height if live else 0)
            f['BUF%dLINES' % n] = str(b['lines'])
            f['BUF%dPIXELS' % n] = str(b['lines'] * self.width)
            f['BUF%dTIMESTAMP' % n] = '0000000000000000'
        return f

    # -- 노출 -------------------------------------------------------------

    def _int_ms(self) -> int:
        for text in self.config.values():
            if 'IntMS=' in text:
                try:
                    return int(text.split('IntMS=')[1].split()[0])
                except (IndexError, ValueError):
                    return 0
        return 0

    def _exposures(self) -> int:
        """`Exposures=n` -- **한 번의 `LOADPARAMS` 가 만드는 프레임 수**.

        ⭐ 타이밍 스크립트가 `GOTO Start` 뒤 `Exposures` 가 남아 있으면 곧바로
        `Exposure:` 로 되돌아가므로, n 을 걸면 **유휴 없이 n 장**이 나온다.
        guide(`icg_archon`)의 시퀀서 pacing 이 이 거동에 기대므로 가짜도
        그대로 모사한다 -- **가짜가 실기와 다르면 실기에서만 나는 결함을
        시험이 못 잡는다** (이 파일 머리말의 원칙).
        """
        for text in self.config.values():
            if 'Exposures=' in text:
                try:
                    return max(int(text.split('Exposures=')[1].split()[0]), 0)
                except (IndexError, ValueError):
                    return 1
        return 1

    def _expose(self) -> None:
        """`LOADPARAMS` -> `Exposures` 장을 **연달아** 찍는다.

        프레임 하나 = 적분(`IntMS`) -> 독출(라인 진행) -> 완료.
        `Exposures=n` 이면 그 사이에 유휴가 없다 (`_exposures()` 참조).

        **버퍼를 순환해 쓰고 `LOCKn` 은 건너뛴다.**  BIGBUF 는 버퍼가 둘뿐이라
        두 프레임 뒤면 앞 프레임의 자료가 덮인다 -- 그것이 `LOCK` 이 있는
        이유다 (매뉴얼 p.50).  ✅ 실기도 그렇다 (2026-09-01): 잠긴 버퍼를
        피하고, 남는 것이 없으면 **쓰던 버퍼를 재사용**한다 (DevNote 10.4).
        """
        for _ in range(max(self._exposures(), 1)):
            if self._stop:
                break
            self._one_frame()

    def _one_frame(self) -> None:
        time.sleep(min(self._int_ms() / 1000.0, 2.0))
        # 잠긴 버퍼는 피한다.  전부 잠겼으면 풀릴 때까지 기다린다.
        for _ in range(2000):
            idx = self._next % self.nbuf
            if idx + 1 != self.locked:
                break
            self._next += 1
            if all((i + 1) == self.locked for i in range(self.nbuf)):
                time.sleep(self.tick)
        self._next += 1
        b = self.bufs[idx]
        b['complete'] = 0
        b['lines'] = 0
        self.wbuf = idx + 1
        for i in range(1, self.readout_ticks + 1):
            # ⚠️ 상한은 `linecount` 다 -- split 에서 HEIGHT 의 절반 (10.3).
            b['lines'] = int(self.linecount * i / self.readout_ticks)
            time.sleep(self.tick)
        self.wbuf = 0
        self.frame_no += 1
        b['frame'] = self.frame_no
        b['complete'] = 1
        self.rbuf = idx + 1

    # -- FETCH ------------------------------------------------------------

    def pixels(self, frame: int | None = None) -> bytes:
        """결정적 픽셀 패턴 (리틀엔디언 `uint16`).

        값 = `(프레임번호 * 1000 + y * width + x) % 65536`.

        * 배치가 뒤집히면 **증분 패턴**이 뒤집혀 드러난다.
        * **프레임 번호를 값에 섞는 것이 요점이다** -- 프레임마다 똑같은 픽셀을
          주면 "앞 프레임의 저장이 뒤 프레임의 자료를 가져갔다" 를 어떤 시험도
          구별할 수 없다 (파이프라인 겹침 결함이 조용히 통과한다).
        * `samplemode=1` 이면 표본이 32bit 라 **정확히 2배** 크기가 된다.
        """
        import numpy as np
        n = self.width * self.height
        f = self.frame_no if frame is None else frame
        arr = ((np.arange(n, dtype='<u4') + f * 1000) % 65536)
        if self.samplemode:
            return arr.astype('<u4').tobytes()
        return arr.astype('<u2').tobytes()

    def _fetch(self, conn, ref: bytes, cmd: str) -> None:  # noqa: ANN001
        addr = int(cmd[5:13], 16)
        blocks = int(cmd[13:21], 16)
        # **주소로 버퍼를 고른다.**  그 버퍼가 지금 담고 있는 프레임의 픽셀을
        # 준다 -- 덮였으면 덮인 것이 나온다(실기와 같다).
        frame = next((b['frame'] for b in self.bufs if b['base'] == addr),
                     self.frame_no)
        data = self.pixels(frame)
        for i in range(blocks):
            chunk = data[i * BURST:(i + 1) * BURST]
            chunk = chunk + b'\x00' * (BURST - len(chunk))
            conn.sendall(b'<' + ref + b':' + chunk)

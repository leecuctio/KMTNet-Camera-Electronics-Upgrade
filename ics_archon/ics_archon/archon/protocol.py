#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archon 텍스트/이진 프로토콜 -- 저수준 왕복 한 자리.

원형은 실험실 취득 스크립트의 전역 함수 4개(`archonsend` · `archonrecv` ·
`archonbinrecv` · `archoncmd`)와 `_resync_archon_link` 다.  **1년 실사용으로
검증된 왕복**이므로 와이어에 나가는 바이트는 그대로 두고, 전역 상태를 객체로
접고 아래 세 가지만 고쳤다.

프로토콜 정본은 Archon 매뉴얼(2021-02-23) p.45 다:

    호스트 -> 컨트롤러   `>xxCOMMAND\\n`          xx = 2자리 16진 참조번호
    성공                 `<xxRESPONSE\\n`
    이진 성공            `<xx:` + **1024바이트** (개행 없음)
    오류                 `?xx\\n`
    **인식 못 한 명령    무응답**  <- 이것이 가장 헷갈리는 실패 형태다

## labtest 에서 고친 것 세 가지

1. **`?xx` 오류 응답을 구분한다.**  labtest 는 `<xx` 만 대조해서 컨트롤러가
   보고한 오류가 `Invalid command packet header` 로 뭉개졌다 -- 원인이 "내
   명령이 거부됐다" 인데 화면에는 "프로토콜이 깨졌다" 로 나온다.
2. **읽기 버퍼가 하나다.**  labtest 의 `archoncmd` 는 `msgbuf` 를 보지 않고
   소켓에서 직접 읽고, `archonrecv`/`archonbinrecv` 는 `msgbuf` 를 쓴다 --
   이진 블록을 읽다 남은 꼬리가 `msgbuf` 에 있으면 다음 `archoncmd` 가 그것을
   못 보고 소켓만 기다린다.  실측된 적은 없지만 구조상 있는 구멍이다.
3. **참조번호를 보내기 **전에** 올린다.**  labtest 는 응답을 검증한 뒤에
   올렸다 -- 시한 초과로 빠져나가면 명령은 나갔는데 번호는 그대로여서, 늦게
   도착한 응답의 `<NN` 이 다음 명령의 번호와 맞아떨어져 **다음 명령이 남의
   응답을 먹는다** (DevNote 11.22 (1) 의 회귀).  먼저 올리면 그 일치가 원리상
   일어나지 않는다.  단 **부분 수신분이 소켓에 남는 문제는 그대로**이므로
   `resync()` 는 여전히 필요하다 -- 번호만 고쳐서는 못 낫는다.

## 그대로 둔 것

* **`command(cmd, timeout=None)` 의 기본값은 무한 대기다.**  `APPLYALL` 처럼
  오래 걸리는 명령이 있어서다 (`ics_archon/SMC_CLAUDE.md` "절대 깨뜨리면 안
  되는 것" 2번).  상한은 부르는 쪽이 준다.
  ⚠️ 인식 못 한 명령은 **무응답**이므로(p.45) 오타 하나로 영구히 멈춘다.
  그래서 이 모듈을 쓰는 `controller.py` 는 명령마다 상한을 준다.
* 참조번호는 **호스트가 정하는 꼬리표**일 뿐이다.  컨트롤러는 받은 값을
  되돌려주므로 값을 건너뛰어도 어긋나지 않는다 (labtest 의 FETCH 루프가 끝에
  하나를 더 올리는 것이 그 증거다).

**이 클래스는 전부 동기(블로킹)다.**  이벤트 루프에서 직접 부르면 안 된다 --
`controller.py` 가 `asyncio.to_thread` 로 감싸고 락으로 한 번에 하나만
보낸다.  OBSAgent 의 시간 창(획득 1.8초 · IDLE 0.9초 · Wrote 25초, DevNote
3.3)이 루프 정지를 허용하지 않기 때문이다.
"""

from __future__ import annotations

import logging
import select
import socket
import time

log = logging.getLogger('ics_archon.proto')

#: 이진 응답 블록 크기 [B] -- 프로토콜 고정값 (매뉴얼 p.45·p.51).
BURST_LEN = 1024


class ArchonError(Exception):
    """컨트롤러와의 왕복이 실패했다.

    `reply_error=True` 면 **컨트롤러가 `?xx` 로 거부한 것**이고(내 명령이
    틀렸다), 아니면 프레이밍·연결 문제다.  둘을 갈라 두는 이유는 대응이
    다르기 때문이다 -- 전자는 명령·ACF 를 보고, 후자는 연결을 다시 세운다.
    """

    def __init__(self, message: str, *, cmd: str = '',
                 reply_error: bool = False) -> None:
        super().__init__(message)
        self.cmd = cmd
        self.reply_error = reply_error


class ArchonLink:
    """컨트롤러 한 대와의 TCP 연결 하나."""

    def __init__(self, host: str, port: int = 4242, *,
                 sock_timeout: float = 1.0, burst_len: int = BURST_LEN,
                 name: str = '') -> None:
        self.host = host
        self.port = port
        self.sock_timeout = sock_timeout
        self.burst_len = burst_len
        #: 로그에 찍을 이름 (컨트롤러 태그).  같은 로그에 두 대가 섞인다.
        self.name = name or host
        self._sock: socket.socket | None = None
        self._buf = bytearray()
        self._ref = 0
        #: **왕복이 깨졌다.**  프레이밍이 어긋나거나 상대가 끊으면 세운다 --
        #: 소켓 객체는 남아 있어도 그 위로 더 보내면 안 된다.  `connected` 가
        #: 이것을 보므로, 표시하지 않으면 `prepare()` 가 "이미 붙어 있다" 고
        #: 판단해 **죽은 소켓으로 남은 밤을 다 보낸다** (2026-08-24 검토).
        self._broken = False
        #: 재동기(resync) 횟수 -- 진단용.  실기에서 이 값이 0 이 아니면
        #: 왕복이 한 번이라도 어긋났다는 뜻이다.
        self.resyncs = 0

    # -- 연결 -------------------------------------------------------------

    @property
    def connected(self) -> bool:
        """쓸 수 있는 연결인가.  **깨진 것으로 표시됐으면 아니다.**"""
        return self._sock is not None and not self._broken

    def mark_broken(self, why: str) -> None:
        """이 링크로는 더 보내면 안 된다고 표시한다.

        소켓을 여기서 닫지는 않는다 -- 닫는 것은 `resync()` 의 일이고, 그 사이에
        진단(누가 무엇을 읽다 깨졌나)을 로그로 남길 여지를 둔다.
        """
        if not self._broken:
            self._broken = True
            log.warning('%s: 링크를 깨진 것으로 표시한다 (%s) -- 다음 왕복 전에 '
                        '재수립해야 한다', self.name, why)

    def connect(self, retry: int = 1, retry_wait: float = 1.0) -> None:
        """연결한다.  이미 열려 있으면 아무것도 하지 않는다."""
        if self._sock is not None and not self._broken:
            return
        if self._sock is not None:
            # 깨진 것으로 표시된 소켓이 남아 있다 -- 버리고 새로 연다.
            self.close()
        last: Exception | None = None
        for attempt in range(max(retry, 1)):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # **settimeout 은 connect 앞에** 둔다 -- 뒤에 두면 죽은 주소로
                # 연결할 때 OS 기본 시한(수십 초)까지 매달린다 (labtest v0.5.0
                # 에서 옮긴 자리).
                s.settimeout(self.sock_timeout)
                s.connect((self.host, self.port))
            except OSError as exc:
                last = exc
                log.warning('%s: 접속 실패 %d/%d (%s)', self.name,
                            attempt + 1, max(retry, 1), exc)
                time.sleep(retry_wait)
                continue
            self._sock = s
            self._buf.clear()
            self._ref = 0
            log.info('%s: %s:%d 접속 -- 참조번호 00 부터', self.name,
                     self.host, self.port)
            return
        raise ArchonError('%s: %s:%d 에 접속할 수 없다 (%s)'
                          % (self.name, self.host, self.port, last))

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        self._buf.clear()
        self._broken = False

    def resync(self, why: str) -> None:
        """어긋난 연결을 **새로 열어** 초기화한다.

        `command()` 가 시한 초과로 빠져나간 뒤에 부른다.  참조번호를 고치는
        것만으로는 부족하다 -- 응답이 **부분만** 도착해 있었으면 소켓에 꼬리
        바이트가 남아 바로 다음 명령을 죽이고, 늦은 응답이 몇 분 뒤 다른
        데이터셋에서 튀어나올 수도 있다 (DevNote 11.22 (1)).

        재접속으로 잃는 상태는 없다 -- 설정(ACF)과 전원은 컨트롤러가 들고
        있다.
        """
        self.resyncs += 1
        log.warning('%s: 연결을 다시 세운다 (%s) -- 누적 %d회',
                    self.name, why, self.resyncs)
        self.close()
        self.connect(retry=3)

    # -- 참조번호 ---------------------------------------------------------

    def _take_ref(self) -> int:
        """다음 참조번호를 꺼내고 카운터를 올린다.

        **보내기 전에 올린다** -- 모듈 docstring 3번.
        """
        ref = self._ref
        self._ref = (self._ref + 1) % 256
        return ref

    # -- 저수준 송수신 ----------------------------------------------------

    def _require_sock(self) -> socket.socket:
        if self._sock is None:
            raise ArchonError('%s: 연결이 없다 -- connect() 를 먼저 부른다'
                              % self.name)
        return self._sock

    def _write(self, ref: int, cmd: str) -> None:
        self._require_sock().sendall(('>%02X%s\n' % (ref, cmd)).encode('ascii'))

    def _fill(self, want: int, deadline: float | None, cmd: str) -> None:
        """버퍼에 최소 `want` 바이트가 모일 때까지 읽는다."""
        sock = self._require_sock()
        while len(self._buf) < want:
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError('%s: %s 응답이 시한 안에 오지 않았다'
                                   % (self.name, cmd or '?'))
            # select 로 먼저 확인한다 -- 소켓 시한(1초)에 걸려 예외가 나는
            # 것과 "아직 안 왔다" 를 갈라야 무한 대기(timeout=None)를
            # 그대로 유지할 수 있다.
            if not select.select([sock], [], [], 0.05)[0]:
                continue
            chunk = sock.recv(65536)
            if not chunk:
                self.mark_broken('상대가 연결을 닫았다')
                raise ArchonError('%s: 연결이 상대에서 끊겼다' % self.name,
                                  cmd=cmd)
            self._buf += chunk

    def _read_line(self, deadline: float | None, cmd: str) -> bytes:
        """개행까지 한 줄 (개행 제외).  버퍼에서 떼어낸다."""
        sock = self._require_sock()
        while True:
            nl = self._buf.find(b'\n')
            if nl >= 0:
                line = bytes(self._buf[:nl])
                del self._buf[:nl + 1]
                return line
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError('%s: %s 응답이 시한 안에 오지 않았다'
                                   % (self.name, cmd or '?'))
            if not select.select([sock], [], [], 0.05)[0]:
                continue
            chunk = sock.recv(65536)
            if not chunk:
                self.mark_broken('상대가 연결을 닫았다')
                raise ArchonError('%s: 연결이 상대에서 끊겼다' % self.name,
                                  cmd=cmd)
            self._buf += chunk

    def _check_head(self, line: bytes, ref: int, cmd: str) -> bytes:
        """`<NN` 을 확인하고 본문을 돌려준다.  `?NN` 이면 오류로 올린다.

        **`?NN`(거부)과 프레이밍 어긋남을 다르게 다룬다.**  거부는 내 명령이
        틀린 것이라 연결은 멀쩡하다.  프레이밍이 어긋난 것은 스트림 위치를 잃은
        것이므로 **그 링크로는 더 보낼 수 없다** -- 표시해 두지 않으면 이후 모든
        명령이 같은 어긋남을 되풀이한다 (2026-08-24 검토).
        """
        head = line[:3].decode('ascii', 'replace')
        if head == '?%02X' % ref:
            raise ArchonError(
                '컨트롤러가 명령을 거부했다 (?%02X): %s' % (ref, cmd),
                cmd=cmd, reply_error=True)
        if head != '<%02X' % ref:
            self.mark_broken('응답 머리 어긋남 (%s)' % cmd)
            raise ArchonError(
                '응답 머리가 어긋났다 -- 기대 <%02X, 받음 %r (명령 %s)'
                % (ref, head, cmd), cmd=cmd)
        return line[3:]

    # -- 명령 -------------------------------------------------------------

    def command(self, cmd: str, timeout: float | None = None) -> bytes:
        """텍스트 명령 하나를 보내고 응답 본문을 돌려준다.

        `timeout=None` 이면 응답이 올 때까지 기다린다 (labtest 와 같다).
        시한을 넘기면 `TimeoutError` 이고, **그때 부르는 쪽이 `resync()` 를
        해야 한다** -- 소켓에 부분 응답이 남아 있을 수 있다.
        """
        ref = self._take_ref()
        deadline = None if timeout is None else time.monotonic() + timeout
        self._write(ref, cmd)
        line = self._read_line(deadline, cmd)
        return self._check_head(line, ref, cmd)

    def command_or_resync(self, cmd: str, timeout: float) -> bytes | None:
        """상한을 준 명령.  시한 초과면 재동기하고 `None` 을 돌려준다.

        텔레메트리처럼 **없어도 취득을 계속해야 하는** 질의를 위한 것이다 --
        헤더 카드 몇 장보다 취득이 우선이므로 실패를 예외로 올리지 않는다
        (raw spec 5.0절 sentinel 경로).
        """
        try:
            return self.command(cmd, timeout=timeout)
        except TimeoutError as exc:
            log.warning('%s: %s', self.name, exc)
            self.resync('%s 응답을 포기했다' % cmd)
            return None
        except ArchonError as exc:
            log.warning('%s: %s', self.name, exc)
            if not exc.reply_error:
                self.resync('%s 왕복이 깨졌다' % cmd)
            return None

    def pipeline(self, cmds: list[str], timeout: float | None = None) -> list[bytes]:
        """여러 명령을 **한꺼번에 보내고** 순서대로 응답을 받는다.

        ACF 적용이 이 형태다 -- 설정 줄 수천 개를 왕복마다 기다리면 몇 분이
        걸린다 (labtest 가 `archonsend` 를 몰아 보내고 `archonrecv` 를 몰아
        받는 이유).  응답은 명령 순서대로 온다.
        """
        refs = [self._take_ref() for _ in cmds]
        for ref, cmd in zip(refs, cmds):
            self._write(ref, cmd)
        deadline = None if timeout is None else time.monotonic() + timeout
        out = []
        for ref, cmd in zip(refs, cmds):
            line = self._read_line(deadline, cmd)
            out.append(self._check_head(line, ref, cmd))
        return out

    # -- 이진 전송 --------------------------------------------------------

    def fetch(self, base_addr: int, nbytes: int,
              timeout: float | None = None,
              on_block=None) -> bytearray:  # noqa: ANN001
        """`FETCH` 로 백플레인 RAM 에서 `nbytes` 를 읽어 온다.

        블록 하나가 `burst_len`(1024) 바이트이고 **응답 하나마다 참조번호가
        같다** (매뉴얼 p.51 -- 요청 블록당 이진 응답 하나).  마지막 블록은
        요청 크기에 맞춰 잘라 쓴다.

        Args:
            base_addr: `BUFnBASE` 값 그대로.  bigbuf 구성에서는 이 값을 쓰는
                것이 유일하게 맞다 -- labtest 의 주석 처리된 주소 계산
                (`(buf+1)|4)<<29` 등)은 버퍼 구성마다 달라서 틀렸다.
            on_block: `(받은_바이트, 전체_바이트)` 로 부르는 진행 콜백.

        Returns:
            정확히 `nbytes` 길이의 바이트열.
        """
        blocks = (nbytes + self.burst_len - 1) // self.burst_len
        ref = self._take_ref()
        deadline = None if timeout is None else time.monotonic() + timeout
        self._write(ref, 'FETCH%08X%08X' % (base_addr, blocks))

        head = ('<%02X:' % ref).encode('ascii')
        err = ('?%02X' % ref).encode('ascii')
        out = bytearray()
        # **중간에 어떤 이유로든 빠져나가면 남은 블록이 소켓으로 흐른다.**
        # 그 상태의 링크로 다음 명령을 보내면 이진 자료를 텍스트로 읽는다.
        try:
            return self._fetch_blocks(ref, base_addr, nbytes, blocks, head,
                                      err, deadline, on_block, out)
        except ArchonError as exc:
            # **거부(`?xx`)는 예외다** -- 컨트롤러가 명령 자체를 안 받았으니
            # 버스트가 흐르지 않는다.  링크는 멀쩡하다.
            if not exc.reply_error:
                self.mark_broken('FETCH 가 중간에 끊겼다 (%d/%d 블록)'
                                 % (len(out) // self.burst_len, blocks))
            raise
        except BaseException:
            self.mark_broken('FETCH 가 중간에 끊겼다 (%d/%d 블록)'
                             % (len(out) // self.burst_len, blocks))
            raise

    def _fetch_blocks(self, ref, base_addr, nbytes, blocks, head,  # noqa: ANN001
                      err, deadline, on_block, out):
        for i in range(blocks):
            # **머리 4바이트를 먼저 본다.**  블록 하나(1028B)가 다 모이기를
            # 기다린 뒤에 판정하면, `?NN\n`(4B)으로 거부된 경우 시한까지
            # 매달린다 -- 거부를 "느린 응답" 으로 오해하는 셈이다.
            self._fill(4, deadline, 'FETCH')
            if bytes(self._buf[:3]) == err:
                # 오류 응답은 텍스트다 (`?NN\n`) -- 줄로 떼어내고 올린다.
                self._read_line(deadline, 'FETCH')
                raise ArchonError(
                    'FETCH 가 거부됐다 (?%02X) -- 주소·블록 수를 확인하라 '
                    '(base=0x%08X, blocks=%d)' % (ref, base_addr, blocks),
                    cmd='FETCH', reply_error=True)
            if self._buf[:4] != head:
                # **남은 블록이 소켓으로 계속 흐른다.**  링크를 깨진 것으로
                # 표시해 다음 왕복 전에 반드시 재수립하게 한다 -- 안 그러면
                # 그 컨트롤러는 재기동까지 못 쓴다.
                self.mark_broken('FETCH 블록 머리 어긋남')
                raise ArchonError(
                    'FETCH 블록 %d/%d 의 머리가 어긋났다 -- 기대 %r, 받음 %r'
                    % (i + 1, blocks, head, bytes(self._buf[:4])), cmd='FETCH')
            del self._buf[:4]
            self._fill(self.burst_len, deadline, 'FETCH')
            take = min(self.burst_len, nbytes - len(out))
            out += self._buf[:take]
            del self._buf[:self.burst_len]
            if on_block is not None:
                on_block(len(out), nbytes)
        return out

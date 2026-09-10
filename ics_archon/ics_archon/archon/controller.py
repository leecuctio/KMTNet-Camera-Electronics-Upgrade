#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""컨트롤러 한 대의 제어 시퀀스 -- ACF 적용 · 전원 · 노출 · 독출 · FETCH.

원형은 실험실 취득 스크립트의 `GetDataset()`/`Exposure()` 다.  **제어 시퀀스
자체(CLEARCONFIG/WCONFIG -> APPLYALL -> POWERON -> LOADPARAMS -> FRAME 폴링 ->
FETCH)는 v1.0 계보로 1년 실사용 검증된 것**이므로 순서와 명령을 바꾸지 않았다
(⚠️ `APPLYALL` 이 `POWERON` 앞이다 -- 매뉴얼 p.51 *"An APPLYALL is required
before this operation"*, 실기 `?02` 거부로 확인 2026-09-01, DevNote 10.2).
바꾼 것은
바깥 껍데기다:

* **전역 상태 -> 객체.**  labtest 는 컨트롤러 한 대를 전제로 전역 변수
  (`archon`/`config`/`configline`/`CURRENT_ACF`/`STATUS_SNAPSHOT`)를 썼다.
  실기는 과학 2대(+가이드 1대)이므로 한 대를 객체 하나로 접는다.
* **블로킹 -> `asyncio.to_thread` + 락.**  시퀀서는 asyncio 이고 OBSAgent 의
  시간 창(획득 1.8초 · IDLE 0.9초 · Wrote 25초, DevNote 3.3)이 이벤트 루프
  정지를 허용하지 않는다.  왕복은 스레드로 내보내고, 한 연결에 한 번에 하나만
  나가도록 락으로 묶는다.
* **명령마다 상한을 준다.**  프로토콜은 **인식 못 한 명령에 무응답**이므로
  (매뉴얼 p.45) 오타 하나로 영구히 멈춘다.  `ArchonLink.command` 의 기본값
  (무한 대기)은 규약이라 그대로 두고, 부르는 쪽인 여기서 상한을 준다.

## 노출을 누가 재나 -- 이 층의 가장 중요한 판단

**컨트롤러가 잰다.**  `IntMS` 를 실어 `LOADPARAMS` 하면 Archon 의 타이밍
스크립트가 적분·셔터 트리거·독출을 스스로 몰고 간다.  시퀀서의 카운트다운
(`Remaining=N sec.`)은 **관측자에게 보내는 알림**이고 하드웨어를 몰지 않는다.

그래서 노출을 시작하는 자리가 두 갈래다 (`backend.py` 가 부른다):

| 노출 | 시작 자리 | 이유 |
|---|---|---|
| 셔터 노출 (OBJECT/FLAT/SKY/DOMEFLAT) | `open_shutter()` | 시퀀서가 여기서 셔터를 열라고 한다.  `IntMS` = 노출시간 |
| DARK / BIAS | `readout()` | 시퀀서가 `_integrate_dark` 에서 백엔드를 아예 부르지 않는다.  적분 시간은 `begin_exposure()` 훅으로 미리 받아 두고 여기서 `IntMS` 에 실어 건다 -- **컨트롤러가 잰다** (훅이 없으면 `IntMS=0` 으로 곧바로 읽어내고 경고를 남긴다) |

⚠️ **STOP(적분 조기 종료)은 컨트롤러의 적분을 자르지 못한다.**  타이밍
스크립트가 이미 `IntMS` 만큼 세고 있으므로, 할 수 있는 것은 `TRIGOUTFORCE=1`
로 **셔터를 강제로 닫아 빛을 끊는 것**뿐이다.  노출은 남은 시간을 다 세고
끝나므로 헤더 `EXPTIME` 은 요청값이고 실제 개방 시간은 그보다 짧다.
`FASTLOADPARAM IntMS 0`(매뉴얼 p.52)이 즉시 반영되는지는 **실기 확인
항목**이다 -- 되면 그쪽이 맞다.
"""

from __future__ import annotations

import asyncio
import configparser
import logging
import os
import time
from dataclasses import dataclass

from . import parse
from .protocol import ArchonError, ArchonLink

log = logging.getLogger('ics_archon.ctrl')


@dataclass
class FrameTicket:
    """노출 1회의 상태 -- **그 프레임이 들고 간다.**

    컨트롤러 필드에 두면 파이프라인이 겹칠 때 뒤 프레임이 앞 프레임의 값을
    덮는다.  저장은 `write_delay` 뒤에 백그라운드로 돌고 그 사이 다음 프레임이
    이미 `LOADPARAMS` 를 냈을 수 있다 -- 그러면 앞 프레임의 저장이 "직전 프레임
    번호" 를 잘못 알고(엉뚱한 프레임을 기다린다), 반대로 앞 프레임의 뒷정리가
    뒤 프레임의 "노출을 걸었다" 표시를 지운다(이중 노출).

    `ics_sim` 이 같은 부류를 두 번 겪었다 -- 파일 일련번호 경합(DevNote 12.10)과
    D-016 선검사의 채널 suffix 재읽기(11.20 critical).  결론은 매번 같았다:
    **프레임의 것은 프레임이 정하고, 나중에 다시 읽지 않는다.**
    """

    #: 이 표가 속한 프레임의 이름 (`<YYYYMMDD>.<NNNNNN>`).
    #:
    #: **이것이 없으면 취소된 프레임의 표가 대기열에 영구히 남는다.**  ABORT 나
    #: 저장 실패로 `write_frame()` 이 안 불리면 아무도 표를 꺼내지 않고, 다음
    #: 프레임의 저장이 **그 낡은 표**를 FIFO 로 집어 온다 -- 그러면 파일마다
    #: 한 노출 뒤진 픽셀이 담기고 헤더는 새 프레임의 것이라 **경고가 한 줄도
    #: 안 뜬다** (2026-08-24 검토에서 확정한 blocker).
    suffix: str
    #: 노출 지시 **직전**의 프레임 번호.  이 값이 바뀌면 내 프레임이다.
    prev_frame: int
    #: 노출 지시 **직전**의 세 버퍼 번호 -- 되감김·재시작 판별의 기준선.
    #:
    #: 번호 하나(`prev_frame`)만으로는 **카운터가 뒤로 간 경우**를 못 가른다:
    #: 평소에도 옛 프레임을 담은 버퍼가 그보다 작은 번호를 들고 있다.  "어느
    #: 자리가 **새로 바뀌었나**" 를 보려면 기준선이 있어야 한다
    #: (`parse.restarted_frame`).  ⭐ 이것도 **표가 들고 간다** -- 컨트롤러
    #: 필드에 두면 파이프라인이 겹칠 때 뒤 프레임이 앞 프레임의 기준선을
    #: 덮는다 (이 클래스가 있는 이유 그대로다).
    prev_frames: tuple[int, ...] = ()
    #: 적분 종료 예상 시각 (monotonic).  `None` 이면 즉시 독출(`IntMS=0`).
    int_until: float | None = None
    #: 완료가 확인된 프레임.  `wait_frame()` 이 채운다.
    ready: parse.FrameStatus | None = None
    #: arm 의 `LOADPARAMS` 왕복 -- 송신 직전과 응답 직후의 **중점**(monotonic /
    #: epoch UTC)과 RTT.  guide 의 flush 는 이 적용 순간 + <=1 us 에 `FrameShift`
    #: 를 시작하므로 첫 저장 프레임의 `DATE-OBS`(10.1-4)가 이 값이다.  링크
    #: 스레드 안에서 찍는다 -- `await` 앞뒤 시각은 `_lock` 대기·루프 지연이
    #: 섞여 수십~수백 ms 틀릴 수 있다 (설계 검토, DevNote 11.31).
    armed_mono: float | None = None
    armed_utc: float | None = None
    arm_rtt: float | None = None

#: 명령별 응답 상한 [s].  근거는 "그 명령이 실제로 무엇을 하나" 다.
#:
#: * 짧은 것(WCONFIG·FRAME·SYSTEM)은 즉답이라 넉넉해도 5초면 충분하다.
#: * `APPLY*`/`LOADTIMING` 은 설정을 모듈에 밀어 넣으므로 초 단위가 걸린다.
#: * `POWERON`/`POWEROFF` 는 바이어스 램프가 있어 더 길다.
#: 상한을 넘기면 연결이 어긋난 것으로 보고 재수립한다 (부분 응답이 소켓에
#: 남을 수 있어서다 -- DevNote 11.22 (1)).
T_FAST = 5.0
#: `APPLYSYSTEM`·`LOADPARAMS` -- 시스템/파라미터만 적용한다.  `APPLYALL` 과 같은
#: 상한을 주면 **노출 안에서 60초를 매달린다**(무응답 명령이면 실제로 그랬다) --
#: 25초 `Wrote` 창을 훌쩍 넘는다.
T_SYSTEM = 15.0
#: `APPLYALL`·`LOADTIMING` -- 설정 전체를 모듈에 밀어 넣는다.  첫 프레임에서만
#: 불리고 시간 창이 없는 구간이라 넉넉히 준다.
T_APPLY = 60.0
#: `APPLYMODxx`·`APPLYDIOxx` -- **모듈 하나**만 적용한다.  벤더 GUI 가
#: `APPLYMOD`·`APPLYDIO` 에 **10초**, `APPLYALL` 에 30초를 준다
#: (ARCHONGUI_ANALYSIS).  ⚠️ 종전에는 이 자리에 맞는 상수가 없어
#: `T_FAST`(5초)나 `T_APPLY`(60초)를 빌려야 했다 -- 앞은 짧고 뒤는
#: 노출 안에서 매달린다 (DevNote 11.18).
T_MODULE = 10.0
T_POWER = 30.0

def _unquote(text: str) -> str:
    """앞뒤 따옴표와 공백을 뗀 비교용 형태.

    ⚠️ ACF 원문은 `"FirstFlush=1"` 처럼 따옴표를 포함하지만 `parse_acf` 가
    그것을 떼고(labtest 관례) 와이어에도 없다.  되읽기 대조에서 그 차이로
    거짓 어긋남을 내지 않도록 양쪽을 같은 형태로 접는다.
    """
    return text.strip().strip('"').strip()

#: `POWERON` 뒤 `POWER` 를 다시 물어보는 간격 [s].
#:
#: **`poweron_wait` 를 줄이지 않는다** -- 그 시간은 전원 램프가 아니라 **CCD
#: flush** 를 기다리는 것이라(labtest 24 x 0.5), `POWER=4` 를 봤다고 일찍
#: 빠져나오면 첫 프레임이 flush 가 덜 된 상태로 나간다.  여기서 하는 것은 그
#: 대기 **안에서** 전원이 실제로 올라왔는지 확인하는 것뿐이다.
T_POWER_POLL = 1.0


class ArchonController:
    """컨트롤러 한 대 (`MK` 또는 `NT`)."""

    def __init__(self, tag: str, cfg) -> None:  # noqa: ANN001 -- ArchonCfg
        self.tag = tag
        self.cfg = cfg
        self.link = ArchonLink(cfg.hosts.get(tag, ''), cfg.port,
                               sock_timeout=cfg.sock_timeout,
                               settle_before=getattr(cfg, 'settle_before', 0.8),
                               settle_after=getattr(cfg, 'settle_after', 2.0),
                               burst_len=cfg.burst_len, name=tag)
        #: 한 연결에 한 번에 하나.  FETCH 가 락을 오래 쥐지만 컨트롤러마다
        #: 연결이 따로라 다른 대의 왕복은 막지 않는다.
        self._lock = asyncio.Lock()

        #: **수신·저장 버퍼 링** (`[archon] fetch_buffers`, 기본 2).
        #:
        #: FETCH 가 하나를 빌려 채우고 **저장이 끝난 뒤** 돌려준다
        #: (`release_buffer`).  종전에는 프레임마다 344 MiB 를 새로 잡았고
        #: 저장 태스크 수에 제한이 없어서, 저장이 밀리면 **메모리가 조용히
        #: 늘었다.**  링으로 두면 상한이 `N x 344 MiB` 로 고정된다.
        #:
        #: 큐에는 처음에 `None` 슬롯만 넣는다 -- **실제 버퍼는 처음 쓸 때
        #: 만든다.**  상한은 슬롯 수가 보장하고, 기동은 가벼운 채로 둔다.
        self._bufpool: asyncio.Queue = asyncio.Queue()
        for _ in range(max(1, int(getattr(cfg, 'fetch_buffers', 2)))):
            self._bufpool.put_nowait(None)
        #: 버퍼가 없어 기다린 횟수·시간.  ⭐ **`fetch_buffers` 가 충분한지를
        #: 추정이 아니라 실기가 답하게 하는 자리다** -- 0 이면 충분한 것이고,
        #: 쌓이면 올려야 한다.
        self.buf_waits = 0
        self.buf_wait_s = 0.0

        #: 마지막 fetch 에서 관측한 **잠금 상태** (진단용, 1-기준.  -1 = 미관측).
        #:
        #: ⭐ `LOCKn` 이 FW 에 반영되는지의 관측값.  ✅ **2026-09-01 두 FW
        #: (1252·1261) 15/15 반영** (DevNote 10.4, A-5 판단 ② 종결) -- 이제는
        #: FW 가 바뀌었을 때의 **회귀 감시**다.  fetch 앞의 덮임 대조에서
        #: **이미 읽는 `FRAME` 응답**에서 뽑으므로 왕복이 늘지 않는다.
        #: - `lock_rbuf` -- `LOCKn` 뒤의 `RBUF`.  `buf_n` 과 같으면 반영된 것
        #: - `lock_wbuf` / `lock_wbuf_after` -- fetch **전후**의 `WBUF`.
        #:   ⭐ 옮겨 갔으면 **엔진이 실제로 다른 버퍼를 썼다**는 거동 증거다
        #:   (매뉴얼 p.71 의 *"다음 잠기지 않은 버퍼"*).
        self.lock_rbuf = -1
        self.lock_wbuf = -1
        self.lock_wbuf_after = -1

        #: ACF 설정 줄 -> 내용, 그리고 키 -> 줄 번호.  `WCONFIG` 는 줄 번호로
        #: 쓰므로 이 대응이 없으면 파라미터를 못 바꾼다.
        self.config: dict[str, str] = {}
        #: ⛔ 캐시를 못 믿는 상태인가.  `ARCHON` 바이패스가 `WCONFIG`/
        #: `CLEARCONFIG` 를 보내면 참이 된다 -- 그 경로는 `set_config` 를
        #: 안 지나 설정 메모리만 바뀐다.  `config_value()` 가 이것을 보고
        #: `RCONFIG` 로 되읽는다.  ⭐ ACF 재파싱이 내리고, 되읽기 성공은
        #: 그 키만 고친다(플래그는 남긴다 -- 다른 키도 낡았을 수 있다).
        self.config_dirty = False
        #: ⭐ **ACF 를 미는 중이다** -- 그동안 설정 메모리는 반쯤 실린 상태라
        #: `RCONFIG` 되읽기가 뜻이 없다 (`CLEARCONFIG` 뒤 아직 안 쓴 줄).
        #: HK 처럼 주기로 도는 것이 이 표시를 보고 비킨다 (DevNote 11.54).
        self.acf_applying = False
        #: ⭐ `APPLY*` 를 **몇 번 보냈나**.  모듈 VCPU 는 `APPLYALL`/`APPLYMOD`/
        #: `APPLYDIO` 에서 재시작되므로(매뉴얼 p.86), 진공 디코더가 이 값을 보고
        #: *"되감김을 우리가 만들었나"* 를 가른다 -- 시각 창으로 어림하지 않는다.
        #: ⚠️ **보낸 횟수**다(성공 여부가 아니다) -- 실패한 적용도 모듈을
        #: 건드렸을 수 있으니 그쪽이 안전하다.
        self.apply_count = 0
        #: 이 컨트롤러의 **온도 자리 표** (`Cn_TEMP` 자리).  `None` 이면
        #: science 기본값(규격 5.6.1절).  ⭐ guide 백엔드가
        #: `guidehdr.TEMP_MODS`(10.4절 8자리)를 꽂는다 -- 안 꽂으면
        #: 정상 구성에서 오경보가 난다.
        self.temp_fields = None
        self.configline: dict[str, int] = {}
        #: ACF `LINECOUNT` -- 진행률(`PCTREAD`)의 분모.  `BUFnHEIGHT` 는 split
        #: 에서 두 배라 못 쓴다 (DevNote 10.3).  0 이면 HEIGHT 로 물러난다.
        self.lines_total: int = 0
        #: 이번 `trigger()` 의 `LOADPARAMS` 가 실제로 나갔나 -- 취소가 그 앞에서
        #: 왔으면 컨트롤러는 유휴라 꼬리가 없다 (guide `_settle`, DevNote 9.15-(9)).
        self.loadparams_sent: bool = False
        #: 마지막으로 적용(또는 파싱)한 ACF 경로 -- FITS `CTRLnCFG`/`RDMODE`
        #: 의 근거다.  컨트롤러는 적용된 ACF 이름을 보고하지 않는다 (p.54).
        self.acf_path: str = ''
        self.acf_applied = False

        #: 마지막 `SYSTEM`/`STATUS` 스냅샷.  **헤더용 접근자는 동기 메서드**
        #: 라(시퀀서가 `_backend_fact` 로 그냥 부른다) 소켓을 만질 수 없다 --
        #: 노출 개시 전에 떠 둔 이 값을 읽는다.  labtest 도 같은 이유로
        #: `STATUS_SNAPSHOT` 을 노출 앞에서 떴다.
        self.system: dict[str, str] = {}
        self.status: dict[str, str] = {}
        #: **살아 있는 스냅샷** -- 배경 감시가 계속 갱신한다 (층 1·2, 2026-08-28).
        #:
        #: ⚠️ **`status` 와 갈라 둔 것이 핵심이다.**  `Cn_TEMP/VOLT/CURR` 의 뜻은
        #: "노출 개시 시점 값" 이고, 그것은 `status` 가 `initialize()` 에서 언
        #: 뒤 아무도 안 건드리기 때문에 성립한다.  감시가 `status` 를 계속
        #: 덮으면 헤더 스냅샷이 굳는 순간에 잡히는 것은 **마지막 폴링 값**이 되고
        #: -- 독출이 모듈을 데우므로 값이 다르다 -- **폴링 간격·락 경합에 따라
        #: 노출마다 달라져 비결정적**이 된다.  카드의 뜻이 조용히 바뀌는 부류다.
        #:
        #: | 자리 | 갱신 | 소비자 |
        #: |---|---|---|
        #: | `status` | 노출 개시에 **언 것** | `controller_telemetry()` -> 헤더 전용 |
        #: | `status_live` | 감시가 계속 | 기록 · ICS `STATUS` 응답 · 건강검사 |
        self.status_live: dict[str, str] = {}
        #: `status_live` 를 뜬 시각 (`time.time()`, UTC epoch).  0 이면 아직 없다.
        #: 기록의 `age_ms` 열이 이것으로 계산된다 -- **"이 값이 몇 초 전 것인가"**
        #: 를 함께 싣지 않으면 신선도가 전달 계층에서 사라진다.
        self.status_live_at: float = 0.0
        #: 감시 폴링이 **연달아** 실패한 횟수.  성공하면 0 으로 돌아간다.
        #:
        #: ⚠️ **`telemetry_enabled` 와 별개다** (반드시 지킬 것 2).  그 래치는
        #: "한 번 실패하면 이 실행 동안 헤더용으로 안 묻는다" 이고(F8), 감시가
        #: 재시도하며 그것을 다시 켜면 **취득 경로의 판단이 감시 쪽 사정으로
        #: 뒤집힌다.**  감시는 자기 카운터로 백오프하고 헤더용 래치는 만지지
        #: 않는다.
        self.status_live_fails: int = 0
        #: STATUS 가 한 번 실패하면 이 실행 동안 다시 묻지 않는다 -- 어긋난
        #: 뒤에도 노출마다 되풀이하는 것은 위험을 반복하는 일이다.  카드
        #: 몇 장보다 취득이 우선이다.
        self.telemetry_enabled = bool(cfg.telemetry)

        self.powered = False
        #: `POWERON` 을 **보낸 적이 있나.**  응답을 잃은 경우까지 포함한다 --
        #: 종료 때 `POWEROFF` 를 낼지는 이 값으로 정한다 (`powered` 는 응답으로
        #: 확인된 상태라 "켜졌는데 모르는" 경우를 놓친다).
        self.power_attempted = False
        #: 이상을 이미 알렸나 -- 프레임마다 같은 줄을 되풀이하지 않는다.
        self._health_bad = False
        #: **진행 중** 프레임의 표 (노출·독출이 끝나면 `release_current()`).
        #: `triggered`/`integrating` 이 이것을 본다.
        self._current: FrameTicket | None = None
        #: 저장을 기다리는 프레임 표 -- FIFO.  `write_frame()` 이 가져간다.
        #: 파이프라인이 겹쳐도 앞 프레임의 저장이 자기 프레임을 기다린다.
        self._queue: list[FrameTicket] = []

    # -- 왕복 -------------------------------------------------------------

    @property
    def link_busy(self) -> bool:
        """지금 **왕복이 도는 중인가** (`_lock` 을 누가 쥐었나).

        ⭐ HK 처럼 **급하지 않은 주기 일**이 취득의 왕복을 비켜 주려고 본다
        (운영자 2026-09-09: *"guide unit 이 바쁠 때에는 60초 폴링 시점이
        되었어도 안 바쁠 때까지 잠시 기다리기"*).
        ⛔ **보장이 아니라 예의다** -- 이걸 보고 비켜도 그 다음 순간에 취득이
        락을 먼저 집을 수 있다.  경합을 막는 것은 락 자신이고, 이 값은 *"지금
        끼어들면 남을 밀겠구나"* 를 알려 줄 뿐이다.
        ⚠️ 그래서 이 값으로 **정확성을 세우면 안 된다** -- 늦추는 판단에만 쓴다.
        """
        return self._lock.locked()

    async def _locked_thread(self, fn, *args):  # noqa: ANN001, ANN201
        """`_lock` 을 쥔 채 블로킹 링크 왕복을 스레드로 돌린다.

        ⭐ **취소돼도 스레드가 끝날 때까지 락을 놓지 않는다** (2026-09-02,
        DevNote 9.15-(9)).  종전 `async with self._lock: await
        asyncio.to_thread(...)` 는 `CancelledError` 에 `async with` 를 빠져
        나오며 락을 풀었는데, 스레드는 취소되지 않아 **소켓 왕복이 아직 진행
        중**이었다 -- 다음 명령(예: ABORT 뒤의 `Exposures=0`)이 같은 소켓에
        끼어들어 응답 번호가 어긋나고 링크가 깨졌다 (가짜에서 10회 중 1회,
        `STATUS` 지연 0.2초로는 20회 중 14회 재현).  `asyncio.to_thread` 는
        어차피 끊을 수 없으니 **끝나기를 기다리는 것**이 유일한 정답이다 --
        링크 시한(`timeout`)이 그 대기를 묶는다.
        """
        async with self._lock:
            fut = asyncio.ensure_future(asyncio.to_thread(fn, *args))
            try:
                return await asyncio.shield(fut)
            except asyncio.CancelledError as first:
                # 스레드가 소켓을 놓을 때까지 락을 쥔다.  ⭐ **두 번째 취소도
                # 흡수한다** -- ABORT 위에 종료가 겹치는 것이 정상 운용이고
                # (2차 반증: 6회 중 3회 재현), 대기는 링크 시한이 묶는다.
                while not fut.done():
                    try:
                        await asyncio.wait({fut})
                    except asyncio.CancelledError:
                        pass
                if not fut.cancelled():
                    fut.exception()          # "never retrieved" 경고 방지
                raise first

    async def cmd(self, command: str, timeout: float = T_FAST) -> bytes:
        """텍스트 명령 하나.  실패하면 `ArchonError`.

        시한 초과는 **연결 재수립**으로 이어진다 -- 참조번호를 미리 올려
        두어(`protocol.py` 3번) 늦은 응답이 다음 명령에 먹히지는 않지만,
        부분 수신분이 소켓에 남는 문제는 그대로다.
        """
        if command.upper().startswith('APPLY'):
            # ⭐ 바이패스(`ARCHON APPLYALL`)도 여기를 지난다 -- 한 곳이면 족하다.
            self.apply_count += 1

        def _run() -> bytes:
            t_s = time.monotonic()
            u_s = time.time()
            try:
                out = self.link.command(command, timeout=timeout)
                t_r = time.monotonic()
                # 마지막 왕복의 (송신 monotonic, 수신 monotonic, 송신 epoch) --
                # `trigger()` 가 LOADPARAMS 직후 읽어 표에 싣는다.
                self.last_cmd_timing = (t_s, t_r, u_s)
                return out
            except TimeoutError as exc:
                self.link.resync('%s 응답 시한 초과' % command)
                raise ArchonError(str(exc), cmd=command) from None
            except ArchonError as exc:
                # **거부(`?xx`)는 연결 문제가 아니다** -- 내 명령이 틀린
                # 것이므로 링크를 버리지 않는다.  그 밖의 실패(프레이밍
                # 어긋남 · 상대가 끊음)는 스트림 위치를 잃은 것이라
                # **반드시 재수립해야 한다** -- 안 하면 이후 모든 명령이
                # 같은 어긋남을 되풀이하고 그 컨트롤러는 재기동까지 죽는다
                # (2026-08-24 검토에서 확정).
                if not exc.reply_error:
                    self.link.resync('%s 왕복이 깨졌다' % command)
                raise
        return await self._locked_thread(_run)

    async def query(self, command: str, timeout: float = T_FAST
                    ) -> dict[str, str]:
        """`KEY=VALUE` 나열을 돌려주는 질의 (`SYSTEM`/`STATUS`/`FRAME`)."""
        return parse.keyvals(await self.cmd(command, timeout))

    # -- 연결 -------------------------------------------------------------

    async def connect(self) -> None:
        if not self.cfg.hosts.get(self.tag):
            raise ArchonError('%s: [archon] ctrl_%s_host 가 비어 있다'
                              % (self.tag, self.tag.lower()))
        await self._locked_thread(self.link.connect, self.cfg.connect_retry)

    async def close(self) -> None:
        await self._locked_thread(self.link.close)

    # -- ACF --------------------------------------------------------------

    def parse_acf(self, path: str) -> None:
        """ACF 를 읽어 `config`/`configline` 을 만든다.  **왕복하지 않는다.**

        `configparser.read()` 는 없는 파일에 조용히 성공하고 그 다음
        `items('CONFIG')` 가 `NoSectionError` 로 터진다 -- "설정 파일이 없다"
        라는 원인이 화면에 안 나온다.  경로가 상대경로라 **작업 디렉터리가
        다른 것**이 가장 흔한 원인이어서 풀어낸 절대경로와 cwd 를 같이 알린다
        (labtest 가 여기서 가장 많이 넘어졌다).
        """
        if not os.path.isfile(path):
            raise ArchonError(
                "%s: ACF 가 없다 -- '%s'\n"
                "        절대경로 '%s'\n"
                "        cwd      '%s'\n"
                '        경로가 상대경로면 작업 디렉터리를 확인하라.'
                % (self.tag, path, os.path.abspath(path), os.getcwd()))
        cp = configparser.RawConfigParser(strict=False)
        # **파싱 예외를 전부 `ArchonError` 로 접는다.**  `configparser` 는
        # `DuplicateOptionError`·`MissingSectionHeaderError`·`ParsingError` 를
        # 낼 수 있고 그것들은 `ArchonError` 가 아니다 -- `initialize()` 의
        # `except (ArchonError, TimeoutError, OSError)` 를 통과하지 못해
        # **노출 태스크가 조용히 죽는다**(`Wrote` 0회 · 오류 0회).  실제 ACF 는
        # 수천 줄이라 중복 키가 있을 수 있다 (2026-08-24 검토에서 확정).
        #
        # `strict=False` 는 labtest 와 같은 관용도를 준다 -- 중복 키는 마지막
        # 값이 이긴다.  그래도 남는 예외는 아래에서 감싼다.
        try:
            cp.read(path)
            items = cp.items('CONFIG')
        except configparser.NoSectionError:
            raise ArchonError("%s: ACF 에 [CONFIG] 절이 없다 -- '%s' 가 Archon "
                              '설정 파일인지 확인하라' % (self.tag, path)) from None
        except (configparser.Error, UnicodeDecodeError, ValueError) as exc:
            raise ArchonError(
                "%s: ACF 를 읽을 수 없다 -- '%s'\n        %s: %s"
                % (self.tag, path, type(exc).__name__, exc)) from None

        # INI 형식의 역슬래시·인용부호를 Archon 형식으로 (labtest 그대로).
        self.config = {}
        self.config_dirty = False       # 파일에서 새로 읽었다
        self.configline = {}
        for i, (key, value) in enumerate(items):
            k = key.upper().replace('\\', '/')
            self.config[k] = value.replace('"', '')
            self.configline[k] = i
        self.acf_path = path
        try:
            self.lines_total = int(self.config.get('LINECOUNT', '0') or 0)
        except ValueError:
            self.lines_total = 0
        log.info('%s: ACF 파싱 %d줄 -- %s', self.tag, len(self.config), path)

    async def apply_acf(self, path: str) -> None:
        """ACF 를 컨트롤러에 밀어 넣고 적용한다 (`CLEARCONFIG`+`WCONFIG`+`APPLYALL`).

        ⭐ **벤더 클라이언트(ArchonGUI)와 같은 절차다** (2026-09-10):

            POLLOFF -> CLEARCONFIG -> WCONFIG x N -> POLLON -> APPLYALL

        ⛔ **`POLLOFF` 가 빠져 있었다.**  ArchonGUI 분석(`ARCHONGUI_ANALYSIS.md`
        5.5절)이 그 이유를 그대로 적어 둔다 -- *"배경 폴링이 `WCONFIG` 수천 줄
        사이에 끼어드는 것을 막으려는 것"*.  ⚠️ 우리 증상이 정확히 그것이었다:
        폭주 중 **응답 하나가 밀린다**(받은 참조번호가 기대 + 1).
        ⚠️ **`POLLON` 은 `finally` 로 되돌린다** -- 적용이 중간에 죽어 폴링이
        꺼진 채 남으면 `STATUS` 값이 통째로 낡는다.  ⭐ 벤더는 `POLLON` 을
        `APPLYALL` **앞**에 두는데 그대로 따랐다.

        ⛔ **`WCONFIG` 는 한 줄씩 왕복한다 -- 눈금이 없다** (운영자 확정
        2026-09-10).  벤더도 그렇게 한다(같은 문서 결함표 C6: *"키 하나당 왕복
        한 번이라 Apply All 이 오래 걸린다"*).  ⚠️ 비용은 실측으로 작다: 왕복
        하나가 약 2 ms 라 1020줄이 **약 2초**다.
        ⛔ **몰아 보내기(`pipeline`)로 되돌리지 말 것** -- 그것이 어긋날 자리를
        만들고, 벤치에서 재현된 결함이 바로 그것이다 (폭주 중 응답 하나가
        밀린다).  ⚠️ 눈금으로 남기지 않은 것도 운영자 판단이다 -- 되돌릴 수
        있게 두면 언젠가 되돌아간다.
        """
        self.parse_acf(path)
        keys = list(self.config)
        cmds = ['WCONFIG%04X%s=%s' % (self.configline[k], k, self.config[k])
                for k in keys]

        # ⭐ **적용 중 표시** -- HK 처럼 주기로 도는 것이 `RCONFIG` 로 설정
        # 메모리를 읽지 않도록 비켜 준다 (`CLEARCONFIG` 직후에는 그 줄이 아직
        # 없다).  ⚠️ 락과 **다른 일**을 한다: 락은 왕복을 줄 세우고, 이 표시는
        # *"지금 읽어 봐야 뜻이 없다"* 를 알린다.
        self.acf_applying = True
        try:
            return await self._apply_acf_loop(path, cmds)
        finally:
            self.acf_applying = False

    async def _apply_acf_loop(self, path: str, cmds: list) -> None:
        """`apply_acf` 의 재시도 고리 -- 적용 중 표시를 확실히 내리려고 뗐다."""
        last: Exception | None = None
        for attempt in range(max(self.cfg.acf_retry, 1)):
            try:
                # ⭐ **`APPLYALL` 까지 한 락에 묶는다** (2026-09-09).
                # ⛔ 종전에는 `_push` 와 `APPLYALL` 이 락을 **따로** 잡아, 그
                # 사이에 남의 왕복이 끼어들 수 있었다.  기동 경로가 바로 그
                # 상황을 만든다 -- `app.start()` 가 `_connect_controller()`
                # (= ACF 적용)를 `spawn` 하고 **곧바로 `hk.start()`** 를 하므로
                # HK 첫 바퀴가 ACF 적용과 **동시에** 돈다.
                # ⚠️ 끼어든 왕복이 실패해 `resync()` 를 하면 **소켓이 통째로
                # 갈린다** -- 그러면 `APPLYALL` 은 밀어 넣은 것과 **다른
                # 연결**로 나간다.  실제로 2026-09-09 벤치에서 `RCONFIG` 가
                # 깨진 3 ms 뒤에 ACF 적용이 실패했다 (DevNote 11.54).
                # ⚠️ 락을 최대 `T_APPLY`(60초) 쥔다 -- 기동·첫 `GO` 뿐이고
                # 그동안 다른 왕복은 어차피 의미가 없다 (설정이 반쯤 실린 상태).
                def _push() -> None:
                    # ⭐ **벤더 절차** -- POLLOFF 로 배경 폴링을 세운다.
                    # ⚠️ 여기서 실패하면 폴링이 꺼진 채 남으므로 `finally`.
                    self.link.command('POLLOFF', timeout=T_APPLY)
                    try:
                        self.link.command('CLEARCONFIG', timeout=T_APPLY)
                        # ⛔ **한 줄씩 왕복한다** -- 몰아 보내면 어긋난다.
                        for one in cmds:
                            self.link.command(one, timeout=T_APPLY)
                    finally:
                        self.link.command('POLLON', timeout=T_APPLY)
                    self.link.command('APPLYALL', timeout=T_APPLY)
                self.apply_count += 1        # `cmd()` 를 안 지나므로 여기서
                await self._locked_thread(_push)
            except (ArchonError, TimeoutError, OSError) as exc:
                if isinstance(exc, ArchonError) and exc.reply_error:
                    # **컨트롤러가 거부한 것이다 -- 연결 문제가 아니다.**  같은
                    # 설정을 다시 밀면 같은 거부가 돌아오고, 그 사이 재접속을
                    # 되풀이하면 원인이 "망이 불안하다" 로 오인된다.
                    raise ArchonError(
                        '%s: 컨트롤러가 ACF 적용을 거부했다 (%s) -- 설정 내용을 '
                        '확인하라.  재시도·재접속하지 않는다' % (self.tag, exc),
                        cmd=exc.cmd, reply_error=True) from None
                last = exc
                log.warning('%s: ACF 적용 실패 %d/%d (%s) -- 연결을 다시 '
                            '세우고 재시도한다', self.tag, attempt + 1,
                            max(self.cfg.acf_retry, 1), exc)
                # ⭐ `resync()` 가 RST 로 끊고 진정 시간까지 쥔다 (2026-09-09)
                # -- 여기서 따로 더 쉬지 않는다.
                await self._locked_thread(self.link.resync, 'ACF 적용 실패')
                continue
            self.acf_applied = True
            log.info('%s: ACF 적용 완료 -- %s', self.tag, path)
            return
        raise ArchonError('%s: ACF 를 적용할 수 없다 (%s)' % (self.tag, last))

    async def set_config(self, key: str, value: str) -> None:
        """설정 줄 하나를 다시 쓴다 (labtest `SetConfig`).

        **Config 줄 번호는 ACF 파싱에서 온다.**  파싱을 안 했으면 어느 줄을
        고칠지 모른다 -- `apply_acf=false` 로 두고 이미 적용된 설정을 쓰는
        경우에도 파일은 읽어 둔다 (`prepare()`).

        ⭐ **번호가 둘이고 한 명령에 같이 실린다** (용어 정리, 운영자 2026-09-06):

            WCONFIG026BPARAMETER0=FirstFlush=1
                   ^^^^          ^
                   |             +-- **Config 슬롯 번호** (`PARAMETERn` 의 n).
                   |                 LOADPARAMS 적용 순서를 정한다.  ACF 키 이름 그대로.
                   +---------------- **Config 줄 번호** (설정 절 안 순번, 0기점 4자리 16진).
                                     `configline` 이 파싱에서 채운다.

        ⚠️ **둘은 따로 논다.**  타이밍 스크립트에 줄이 늘면 **줄 번호만** 밀리고
        (R2617 이 빈 줄 둘로 +2), 슬롯 번호는 그대로다.  반대로 R2613 은 슬롯만
        옮겼다(`ContinuousExposures` 0 -> 16).  ⛔ 그래서 판을 갈면 **반드시 다시
        파싱**해야 한다 -- 옛 줄 번호로 쓰면 다른 줄을 덮는다.
        """
        k = key.upper().replace('\\', '/')
        line = self.configline.get(k)
        if line is None:
            raise ArchonError(
                "%s: 설정 줄 '%s' 을 모른다 -- ACF 를 먼저 파싱해야 한다 "
                '(현재 ACF %r)' % (self.tag, key, self.acf_path or '없음'))
        self.config[k] = value
        await self.cmd('WCONFIG%04X%s=%s' % (line, k, value), timeout=T_FAST)

    async def set_first_flush(self, on: bool) -> bool:
        """노출 전 CCD flush(`FlushFrame` = `Prep`+`Flush`)를 켜고 끈다.  바꿨으면 `True`.

        ⭐ **설정 메모리의 `FirstFlush` 한 줄을 쓰는 일이다** (science R2610+, DevNote
        11.33).  science 는 노출마다 `LOADPARAMS` 를 내므로 메모리가 1 이면 코어가
        `Start:` 첫 줄에서 `FlushFrame` 으로 뛰어 **매 노출 전** Prep+Flush 를 돌고
        `FirstFlush--` 로 소비한 뒤 `Exposure:` 로 온다 -- `ERASE` 한 번이 아니다.
        ⚠️ 그만큼 **프레임 주기가 늘어난다** (`Flush` 가 `SkipLine(FlushLines)`).
        `LOADTIMING` 은 없다 -- 다음 노출의 `LOADPARAMS` 가 그대로 실어 간다.

        (종전 R2609 까지는 `LINE9/LINE10` 의 `#` 를 여닫고 `LOADTIMING` 을 냈다 --
        코어 리셋 · `Exposures=0` 고정 · 두 단계 되읽기가 다 필요했고 유령 독출을
        한 번 낳았다.  같은 결과를 WCONFIG 한 줄로 얻는다.)

        ⚠️ 슬롯이 없는 ACF(R2608 이하)에서는 기동을 세우지 않는다 -- 켜라고 했으면
        크게 경고하고 **flush 없이 간다** (flush 옵션 하나 때문에 관측을 통째로 못
        하는 것이 더 나쁘다).  `apply_acf=false` 경로에서도 컨트롤러 메모리를
        `RCONFIG` 로 되읽어 판정하므로 앞 세션이 켜 둔 값을 되돌린다.
        """
        fslot = getattr(self.cfg, 'param_flush_slot', None)
        fname = getattr(self.cfg, 'param_flush_name', 'FirstFlush')
        # ⛔ **Config 슬롯 번호(`PARAMETERn` 의 n)만 보면 안 된다** -- R2608 의
        # `PARAMETER0` 은 `ContinuousExposures` 였다.
        # 그 자리에 FirstFlush 를 쓰면 다른 파라미터를 덮는다.
        cur = _unquote(await self.config_value(fslot)) if fslot else ''
        if not cur.startswith(fname + '='):
            if on:
                log.warning('⛔ %s: ccdflush 를 켜라고 했는데 ACF 의 %s 슬롯에 %s 가 없다 '
                            '(%r) -- **flush 없이 간다**.  science R2610+ ACF 를 쓸 것',
                            self.tag, fslot or '?', fname, cur[:30])
            return False
        want = '%s=%d' % (fname, 1 if on else 0)
        try:
            got = await self.read_config(fslot)
        except ArchonError as exc:
            log.error('⛔ %s: ccdflush -- %s 를 되읽지 못했다 (%s).  쓰지 않는다',
                      self.tag, fslot, exc)
            return False
        if _unquote(got) == want:
            self.config[fslot] = want            # 캐시를 컨트롤러 값에 맞춘다
            return False
        await self.set_config(fslot, want)
        # ⛔ `set_config()` 는 왕복이 실패해도 로컬 캐시를 먼저 갈아 끼운다 (11.13 F5) --
        # *"보냈다"* 와 *"앉았다"* 가 다르므로 되읽어 확인한다.
        try:
            back = await self.read_config(fslot)
        except ArchonError as exc:
            log.error('⛔ %s: ccdflush -- %s 를 쓴 뒤 되읽지 못했다 (%s)',
                      self.tag, fslot, exc)
            return False
        if _unquote(back) != want:
            log.error('⛔ %s: ccdflush -- %s 가 앉지 않았다 (보낸 것 %r, 되읽은 것 %r)',
                      self.tag, fslot, want, back)
            return False
        log.info('%s: CCD flush(매 노출 전 Prep+Flush) %s -- %s=%s%s', self.tag,
                 '켬' if on else '끔', fslot, want,
                 ' (⚠️ 프레임 주기가 flush 만큼 늘어난다)' if on else '')
        return True

    async def read_config(self, key: str) -> str:
        """설정 줄 하나를 **컨트롤러에서 되읽는다** (`RCONFIG`).

        ⭐ **되읽기는 세 층이고 이것이 가운데다** (DevNote 11.14-(1)):

        * 우리 캐시(`self.config`) -- ⛔ `set_config` 가 **왕복 실패에도 먼저**
          갈아 끼우므로 못 믿는다.
        * **`RCONFIG`(이 함수)** -- `WCONFIG` 가 **실제로 앉은 값**.
        * `STATUS` -- 모듈이 **실제로 내는 값**.  가장 강하지만 히터
          `ENABLE`/`TARGET` 은 거기 없다.

        값만 돌려준다(`KEY=` 접두를 뗀다).  줄 번호를 모르거나 응답이 다른
        키면 `ArchonError` 다 -- **조용히 캐시로 물러나지 않는다**(그러면 이
        함수의 존재 이유가 없어진다).
        """
        k = key.upper().replace('\\', '/')
        line = self.configline.get(k)
        if line is None:
            raise ArchonError(
                "%s: 설정 줄 '%s' 을 모른다 -- ACF 를 먼저 파싱해야 한다"
                % (self.tag, key))
        got = (await self.cmd('RCONFIG%04X' % line, timeout=T_FAST)
               ).decode('ascii', 'replace').strip()
        if not got.upper().startswith(k + '='):
            raise ArchonError(
                '%s: 설정 줄 %04X 가 %s 가 아니다 -- 받은 것 %r'
                % (self.tag, line, k, got[:60]))
        return got[len(k) + 1:]

    async def apply_module(self, slot: int, *, dio: bool = False) -> None:
        """모듈 하나의 설정을 적용한다 -- `APPLYMODxx` / `APPLYDIOxx`.

        ⚠️ **슬롯 인자는 0기점 2자리 16진**이다 (매뉴얼 p.52 *"hex, 00 =
        module 1"*).  즉 **MOD10 -> `09`** 다.  1기점으로 주면 옆 모듈을
        적용한다 -- 조용히 틀리는 자리다.

        | `dio` | 명령 | 적용 범위 (매뉴얼) |
        |---|---|---|
        | `False` | `APPLYMODxx` | *"the configuration for module xx"* -- 모듈 파라미터(RTD·히터 PID/TARGET/LIMIT) |
        | `True` | `APPLYDIOxx` | *"the **DIO and VCPU** configuration"* |

        ⛔⛔ **어느 쪽이든 그 모듈의 VCPU 가 재시작된다** (매뉴얼 p.86:
        *"loaded when an APPLYALL, APPLYMOD, or APPLYDIO command is given.
        The VCPU is held in reset while it's being configured"*).  guide 의
        진공 게이지를 읽는 VCPU 가 **MOD10 에 있으므로 히터 명령 한 번이
        `DEWPRES` 결측 창을 만든다** -- 부르는 쪽이 그 사실을 응답·로그에
        적어야 한다 (DevNote 11.18).
        """
        if not 1 <= slot <= 12:
            raise ArchonError('%s: 모듈 슬롯이 범위 밖이다 -- %r (1..12)'
                              % (self.tag, slot))
        word = 'APPLYDIO' if dio else 'APPLYMOD'
        await self.cmd('%s%02X' % (word, slot - 1), timeout=T_MODULE)
        log.info('%s: %s%02X (모듈 %d) 적용 -- ⚠️ 그 모듈의 VCPU 가 재시작됐다',
                 self.tag, word, slot - 1, slot)

    async def verify_config_lines(self, keys) -> list[str]:  # noqa: ANN001
        """`RCONFIG` 로 줄 번호 대응이 맞는지 확인한다.  어긋난 키 목록을 돌려준다.

        **`apply_acf=false` 의 안전장치 가운데 하나다.**  파일에서 얻은 줄 번호가
        컨트롤러 메모리의 실제 배치와 다르면, `set_config('PARAMETER2',
        'IntMS=…')` 가 **엉뚱한 줄을 고친다** -- 그러면 노출 시간이 안 바뀌는데
        오류도 안 난다.

        ⚠️ **줄이 맞아도 그 세션의 `APPLYALL` 여부는 못 가른다** -- 설정 메모리에
        줄이 남아 있어도 이 세션에서 `APPLYALL` 이 없었으면 `POWERON` 이 `?xx`
        로 거부된다 (매뉴얼 p.51, DevNote 10.2).  그 경우는 `power_on()` 이
        진단 문구를 붙인다.
        기동에서 한 번 대조해 두면 그 침묵을 없앨 수 있다.
        """
        bad = []
        for key in keys:
            k = key.upper().replace('\\', '/')
            line = self.configline.get(k)
            if line is None:
                bad.append(key)
                continue
            try:
                got = (await self.cmd('RCONFIG%04X' % line, timeout=T_FAST)
                       ).decode('ascii', 'replace')
            except ArchonError as exc:
                log.warning('%s: RCONFIG%04X 실패 (%s) -- 대조를 건너뛴다',
                            self.tag, line, exc)
                continue
            if not got.upper().startswith(k + '='):
                log.error('%s: 설정 줄 %04X 가 %s 가 아니다 -- 받은 것 %r.  '
                          'ACF 파일과 컨트롤러 메모리가 다르다 (apply_acf 를 '
                          'true 로 두거나 같은 ACF 를 쓰라)',
                          self.tag, line, k, got[:60])
                bad.append(key)
        return bad

    # -- 전원 -------------------------------------------------------------

    async def power_on(self, wait: float | None = None) -> None:
        """CCD 입력 클록·바이어스 전원 ON + flush 대기.

        **"보냈다" 를 보내기 전에 기록한다.**  응답을 잃어도(시한 초과·망 끊김)
        컨트롤러는 이미 전원을 올렸을 수 있다 -- 그때 `powered=False` 로 남으면
        `shutdown()` 이 `POWEROFF` 를 건너뛰고 **바이어스가 걸린 채로 프로그램이
        끝난다**(검출기 쪽 위험, 규약 11).  확인된 상태(`powered`)와 시도한
        사실(`power_attempted`)을 갈라 두면 종료는 안전한 쪽으로, 재준비는
        확인된 쪽으로 판단할 수 있다.

        flush 대기 **안에서** `POWER=4` 를 확인한다 -- `_await_power()`.
        대기 시간(`poweron_wait`)은 그대로다: 그 시간은 전원 램프가 아니라
        **CCD flush** 를 기다리는 것이라 일찍 빠져나오면 안 된다.
        """
        # **여기서 낡은 저장 표를 버린다** (2026-08-30 배선).  ⚠️ CCD `POWERON`
        # 은 `BUFnFRAME` 을 리셋하지 **않는다** (2026-09-02 실측 -- 리셋은
        # `REBOOT`·백플레인 전원만, DevNote 10.7).  그래도 버리는 것이 맞다:
        # 전원이 내려간 사이의 프레임은 어차피 자료가 아니고, 표를 남겨 두면
        # 다음 프레임의 저장이
        # **그 낡은 표**를 집어 파일마다 한 노출 뒤진 픽셀이 담기고, 헤더는 새
        # 프레임의 것이라 경고가 한 줄도 안 뜬다 (`FrameTicket` 설명의 그
        # blocker 다).  **크게 잃는 것이 조용히 틀린 것보다 낫다.**
        self.drop_tickets('POWERON -- 전원이 내려간 사이의 프레임은 못 받는다')
        self.power_attempted = True
        try:
            await self.cmd('POWERON', timeout=T_POWER)
        except ArchonError as exc:
            if exc.reply_error:
                # ⭐ 첫 관문에서 한 시간을 먹은 한 줄이다 (DevNote 10.2·10.10-6).
                # 매뉴얼 p.51: *"An APPLYALL is required before this operation."*
                # 설정 메모리에 줄이 있어도 **이 세션에서** APPLYALL 이 없었으면
                # 거부한다 -- REBOOT·백플레인 전원 뒤, 또는 apply_acf=false 로
                # 새 세션을 열었을 때가 그 경우다.
                raise ArchonError(
                    '%s: POWERON 을 컨트롤러가 거부했다 (%s) -- 이 세션에서 '
                    'APPLYALL 이 없었을 가능성이 크다 (매뉴얼 p.51).  REBOOT 나 '
                    '전원 재투입 뒤라면 apply_acf=true 로 두거나 GUI Apply All '
                    '을 먼저 할 것 (DevNote 10.2)' % (self.tag, exc),
                    cmd='POWERON', reply_error=True) from exc
            raise
        self.powered = True
        delay = self.cfg.poweron_wait if wait is None else wait
        if delay <= 0:
            return
        log.info('%s: POWERON -- CCD flush %.1f초 대기', self.tag, delay)
        if not self.cfg.telemetry:
            # 규약 4 -- `telemetry=false` 는 **왕복을 labtest v1.0 계보와 똑같이
            # 둔다**는 뜻이다.  확인 질의도 왕복이므로 여기서는 걸지 않는다.
            await asyncio.sleep(delay)
            return
        await self._await_power(delay)

    async def _await_power(self, delay: float) -> None:
        """flush 대기 **안에서** `POWER=4` 를 확인한다 (modtm 계보, 2026-08-28).

        **`POWERON` 이 성공 응답을 준 것과 전원이 실제로 올라온 것은 다르다**
        (`parse.POWER_STATES` 의 주석이 이미 그렇게 적어 두고 있었는데 아무도
        확인하지 않았다).  실험실 계보 둘이 여기서 갈린다 -- labtest v1.0/v1.3
        은 응답만 보고 12초를 세고, `__ref_archon_control/modtm_*.py` 는
        `STATUS` 를 되물어 `POWER==4` 를 확인한 뒤에야 진행한다.  modtm 쪽이
        옳다: 확인이 없으면 전원이 안 올라온 채로 노출이 걸리고, 밖에서는
        **"취득 실패" 로만** 보인다 (F2 가 막으려던 바로 그 모양).

        ⚠️ **막지는 않는다.**  `_check_health()` 와 같은 자리다 -- 이 필드는
        아직 실기 미검증(PROVISIONAL)이라 오독 하나로 관측을 세우는 쪽이 더
        나쁘다.  대신 원인이 보이도록 크게 남긴다.

        ⚠️ **`_check_health()` 를 부르지 않는다.**  램프 도중의 `POWER=3`
        (Intermediate -- 일부 모듈만 올라왔다)은 **정상 경과**인데, 그것을
        건강 판정에 넣으면 켤 때마다 "컨트롤러 상태 이상" 이 뜬다.  같은
        이유로 스냅샷(`status`/`status_live`)도 덮지 않는다 -- 저 둘은 각각
        헤더와 감시의 것이고, 여기 값은 **지나가는 상태**다.
        """
        deadline = time.monotonic() + delay
        started = time.monotonic()
        state = None
        while time.monotonic() < deadline:
            await asyncio.sleep(min(T_POWER_POLL,
                                    max(deadline - time.monotonic(), 0.0)))
            try:
                fields = await self.query('STATUS',
                                          timeout=self.cfg.status_timeout)
            except (ArchonError, TimeoutError, OSError) as exc:
                log.warning('%s: POWERON 확인 질의가 실패했다 (%s) -- 확인 없이 '
                            '남은 flush 시간만 기다린다', self.tag, exc)
                break
            state = parse.power_state(fields)
            if state is None:
                # **보고가 없는 것을 이상으로 세지 않는다** (F2 원칙).  구
                # 펌웨어는 `POWER` 를 아예 안 낸다 -- 그때는 확인 수단이 없는
                # 것이지 전원이 안 올라온 것이 아니다.
                log.info('%s: STATUS 에 POWER 필드가 없다 -- POWERON 확인을 '
                         '건너뛴다 (구 펌웨어일 수 있다)', self.tag)
                break
            if state == parse.POWER_ON:
                log.info('%s: POWER=4 (On) 확인 -- %.1f초 걸렸다.  남은 flush '
                         '시간을 마저 기다린다', self.tag,
                         time.monotonic() - started)
                break
        # ⚠️ **마지막으로 읽은 값을 버리지 않는다.**  `POWER=3` 을 보다가 시한이
        # 끝난 것과 한 번도 못 물어본 것은 다른 사실이고, 아래 판정이 그 둘을
        # 갈라야 한다 (`state is None` 이 "확인 못 했다" 다).
        elapsed = time.monotonic() - started
        remaining = deadline - time.monotonic()
        if remaining > 0:
            await asyncio.sleep(remaining)
        if state is not None and state != parse.POWER_ON:
            log.error('%s: POWERON 뒤 %.1f초가 지나도 POWER=%d %s 다 -- 이 '
                      '상태에서 건 노출은 자료가 아니라 잔해일 수 있다.  유닛 '
                      '전원과 ACF 적용을 확인하라 (매뉴얼 p.47)',
                      self.tag, elapsed, state,
                      parse.POWER_STATES.get(state, '?'))

    async def power_off(self) -> None:
        """전원 OFF.  **실패해도 예외를 올리지 않는다.**

        이것을 부르는 자리는 대개 `finally` 다 -- 여기서 예외를 내면 원래
        원인이 가려진다.  전원을 켠 채로 프로그램이 죽는 것은 검출기 쪽
        위험이므로, 못 껐다는 사실만 크게 알린다.
        """
        try:
            await self.cmd('POWEROFF', timeout=T_POWER)
        except (ArchonError, TimeoutError, OSError) as exc:
            log.error('%s: POWEROFF 를 못 보냈다 (%s) -- 유닛 전원 상태를 '
                      '직접 확인하라', self.tag, exc)
            return
        self.powered = False
        self.power_attempted = False

    async def reset_timing(self) -> None:
        """`RESETTIMING` -- 타이밍 코어를 **스크립트 첫 줄(`Start:`)부터** 다시 돈다
        (매뉴얼 p.52; RELEASETIMING 없이 곧바로 돈다).

        진행 중이던 적분·독출은 그 자리에서 끊긴다 -- 쓰던 버퍼는 미완료로 남고
        프레임 번호는 안 는다.  **자료를 쓸 생각이면 부르지 말 것** -- 이것은
        `flush_now(reset=True)` 가 abort 직후 CCD 를 비우려고 쓰는 길이다
        (운영자 2026-09-05: 노출 중 abort/EXPENABLE=0 이면 비디지타이징 flush 로
        CCD 를 비운다).  끊긴 프레임을 기다리는 표가 있으면 함께 버린다.
        """
        await self.cmd('RESETTIMING', timeout=T_SYSTEM)
        self.drop_tickets('RESETTIMING -- 진행 중이던 프레임은 완료되지 않는다')
        log.info('%s: RESETTIMING -- 코어가 Start 로 돌아갔다', self.tag)

    async def raw_command(self, text: str, timeout: float = T_SYSTEM) -> str:
        """운영자 바이패스 -- 명령 문자열을 **그대로** 보내고 응답을 **그대로** 돌려준다.

        참조 번호·프레이밍은 링크 층이 붙이고 떼므로 여기 들어오는 것은 `STATUS`
        같은 명령 본문이고 나가는 것은 응답 본문이다.  거부(`?xx`)는 `ArchonError`
        (reply_error) 로 온다 -- 부르는 쪽이 문구로 옮긴다.  ⚠️ 위생 검사 없음 --
        운영자 도구다 (2026-09-05 지시).
        """
        text = ' '.join(text.split())
        if not text:
            raise ArchonError('%s: empty command' % self.tag, cmd='')
        word = text.split(' ', 1)[0].upper()
        if word.startswith('WCONFIG') or word == 'CLEARCONFIG':
            # ⛔ **여기가 캐시와 컨트롤러가 갈리는 유일한 경로다.**  바이패스는
            # `set_config` 를 안 지나므로 설정 메모리만 바뀌고 `self.config` 는
            # 옛 값을 든다.  그 뒤 `set_first_flush`/`flush_now` 가 캐시를 믿고
            # *"그 슬롯에 FirstFlush 가 있다"* 로 판단하면 **엉뚱한 슬롯을 덮는다**.
            # ⭐ 그래서 값을 흉내내 고치지 않고 **못 믿는다고 표시만** 한다 --
            # 원문을 우리가 파싱하면 그 파싱이 또 하나의 진실이 된다.
            # 다음 판단은 `config_value()` 가 `RCONFIG` 로 되읽는다.
            self.config_dirty = True
            log.info('%s: 바이패스가 설정 메모리를 건드렸다 (%s) -- 캐시를 '
                     '못 믿는 것으로 표시한다 (다음 판단은 RCONFIG 되읽기)',
                     self.tag, word)
        out = await self.cmd(text, timeout=timeout)
        return out.decode('latin-1', 'replace').strip()

    async def config_value(self, key: str) -> str:
        """설정 줄 하나 -- **믿을 수 있는 값**으로.

        평시에는 캐시(`self.config`)를 준다.  ⭐ 그런데 `ARCHON` 바이패스가
        `WCONFIG`/`CLEARCONFIG` 를 보낸 뒤라면 캐시가 옛 값이므로 **`RCONFIG` 로
        되읽어** 캐시를 고치고 준다 (`config_dirty`).
        ⚠️ 되읽기가 실패하면 **캐시로 물러나되 표시는 남긴다** -- 여기서 죽으면
        운영자 바이패스 한 번이 다음 `ccdflush` 를 통째로 막는다.
        """
        if not self.config_dirty:
            return str(self.config.get(key, ''))
        try:
            got = (await self.read_config(key)).strip()
        except Exception as exc:  # noqa: BLE001 -- 판단을 막지는 않는다
            log.warning('%s: %s 되읽기 실패 (%s) -- 캐시 값으로 간다.  '
                        'ARCHON 바이패스 뒤라 값이 낡았을 수 있다',
                        self.tag, key, exc)
            return str(self.config.get(key, ''))
        self.config[key] = got
        return got

    async def flush_now(self, *, reset: bool = False) -> None:
        """CCD 를 한 바퀴 비운다 -- 타이밍 스크립트의 `FlushFrame` 을 한 번 돌린다.

        `Exposures=0` 을 `LOADPARAMS` 로 걸면 코어가 `Start:` 첫 줄에서 RAM 의
        `FirstFlush` 를 보고 `FlushFrame` 으로 뛴다 (guide R2616: FrameShift +
        SkipLine x FlushLines, science R2610: Prep + Flush).  프레임은 만들지 않는다.
        설정 메모리의 `FirstFlush` 가 1 이 아니면(science `ccdflush=false`) 잠시 1 로
        올렸다가 되돌린다 -- guide 는 ACF 상수가 1 이라 쓸 것이 없다 (DevNote 11.33).

        `reset=True` 면 LOADPARAMS 뒤 **`RESETTIMING`** 으로 진행 중 사이클을 끊고 곧바로
        flush 로 들어간다 -- abort/EXPENABLE=0 경로.  LOADPARAMS 가 파라미터 RAM 과 설정
        메모리를 같은 값으로 맞춘 뒤라, RESETTIMING 이 RAM 을 그대로 쓰든 메모리를 다시
        읽든 결과가 같다(⏳ 어느 쪽인지는 첫 구동 실측).

        ACF 에 슬롯이 없으면(R2612 이하 guide · R2608 이하 science) `ArchonError`.
        """
        fslot = getattr(self.cfg, 'param_flush_slot', None)
        fname = getattr(self.cfg, 'param_flush_name', 'FirstFlush')
        cur = _unquote(await self.config_value(fslot)) if fslot else ''
        if not cur.startswith(fname + '='):        # Config 슬롯 번호만 믿지 않는다 (위 참조)
            raise ArchonError('%s: ACF has no %s parameter (slot %s) -- load an ACF '
                              'with FlushFrame (guide R2613+ / science R2609+)'
                              % (self.tag, fname, fslot or '?'), cmd='WCONFIG')
        armed = cur == '%s=1' % fname
        if not armed:
            await self.set_config(fslot, '%s=1' % fname)
        await self.set_config(self.cfg.param_exposures_slot,
                              '%s=0' % self.cfg.param_exposures_name)
        await self.cmd('LOADPARAMS', timeout=T_SYSTEM)
        if reset:
            await self.reset_timing()
        if not armed:
            await self.set_config(fslot, '%s=0' % fname)
        log.info('%s: CCD flush %s', self.tag,
                 'after RESETTIMING (abort)' if reset else 'from idle')

    # -- 스냅샷 -----------------------------------------------------------

    async def refresh_system(self) -> None:
        """`SYSTEM` 스냅샷 (`CTRLnID`/`CTRLnSN` 의 원천).  실패는 경고만."""
        try:
            self.system = await self.query('SYSTEM', timeout=T_FAST)
        except (ArchonError, TimeoutError, OSError) as exc:
            log.warning('%s: SYSTEM 질의 실패 (%s) -- 컨트롤러 정체는 ini '
                        '값이나 sentinel 로 실린다', self.tag, exc)

    async def refresh_status(self) -> None:
        """`STATUS` 스냅샷 (`Cn_TEMP/VOLT/CURR` 의 원천).

        **노출 개시 전에 부른다.**  fetch 뒤에 두면 컨트롤러가 답하지 않을 때
        다 읽어낸 노출을 잃는다 (labtest 가 v1.1 에서 옮긴 자리).
        """
        if not self.telemetry_enabled:
            return
        try:
            self.status = await self.query('STATUS',
                                          timeout=self.cfg.status_timeout)
            self._check_health()
        except (ArchonError, TimeoutError, OSError) as exc:
            self.telemetry_enabled = False
            # **낡은 스냅샷을 반드시 버린다.**  안 버리면 `controller_telemetry()`
            # 가 앞 프레임의 값을 읽어 **지금 잰 값처럼** 헤더에 싣는다 --
            # 텔레메트리는 이 실행 동안 다시 갱신되지 않으므로 그 뒤의 모든
            # 프레임이 같은 온도·전압을 달고 나가고, 파일만 봐서는 언제 잰
            # 값인지 알 길이 없다.  "물어봤는데 실패" 는 `NC` 여야 한다
            # (`parse.telemetry_of` 가 빈 dict 를 그렇게 만든다).
            self.status = {}
            log.warning('%s: STATUS 질의 실패 (%s) -- 이 실행 동안 텔레메트리를 '
                        '끈다.  Cn_* 는 NC 로 실린다', self.tag, exc)

    async def refresh_status_live(self) -> bool:
        """**감시용** `STATUS` 스냅샷.  성공하면 `True`.

        헤더용 `refresh_status()` 와 갈라 둔 자리다 -- 규칙 넷을 여기서 지킨다
        (`../SMC_CLAUDE.md` "반드시 지킬 것 넷", 운영자 승인 2026-08-27):

        1. **락을 새로 만들지 않는다** -- `query()` 가 `self._lock` 을 타므로
           FETCH·노출 왕복과 자동으로 직렬화된다.  ⚠️ 그래서 **FETCH 가 락을
           344 MiB 동안 쥐면 감시 주기가 그만큼 밀린다.**  그것은 오류가 아니라
           기록할 사실이다 -- 밀린 시간은 기록의 `lag_ms` 열에 남고, **밀린
           만큼 몰아서 뜨지 않는다**(그건 감시가 아니라 부하다).
        2. **`telemetry_enabled` 를 만지지 않는다** -- 그 래치는 취득 경로의
           판단이다(F8).  감시의 성공·실패는 `status_live_fails` 로만 센다.
        3. `self.status`(헤더용 언 스냅샷)를 **덮지 않는다.**
        4. 실패하면 `status_live` 를 **버린다** -- 낡은 값이 새 값처럼 보이는
           것이 가장 나쁘다(`refresh_status()` 가 헤더 쪽에서 같은 판단을 한다).
           `status_live_at` 은 지우지 않는다 -- **"마지막으로 성공한 것이
           언제인가"** 는 버릴 값이 아니라 진단이다.  그 값이 기록에 `age_ms`
           로 나가는 것은 폴링이 성공한 행에서만이다.

        `[archon] telemetry = false` 면 아무것도 하지 않는다 -- 그 설정의 뜻이
        "컨트롤러와의 왕복을 labtest v1.0 계보와 똑같이 둔다" 이므로 감시도
        예외가 아니다.
        """
        if not self.cfg.telemetry:
            return False
        try:
            fields = await self.query('STATUS',
                                      timeout=self.cfg.status_timeout)
        except (ArchonError, TimeoutError, OSError) as exc:
            self.status_live_fails += 1
            self.status_live = {}
            # **같은 줄을 주기마다 되풀이하지 않는다** -- 20초 간격이면 밤새
            # 수천 줄이 되고, 반복되는 경고는 사람이 경고를 무시하도록
            # 학습시킨다.  첫 실패와 그 뒤 10회마다만 알린다 (기록 쪽에는
            # `poll_failed` 행이 빠짐없이 남으므로 사실은 안 잃는다).
            if self.status_live_fails == 1 or self.status_live_fails % 10 == 0:
                log.warning('%s: 감시 STATUS 실패 %d회 연속 (%s) -- 취득용 '
                            '텔레메트리 래치는 건드리지 않는다', self.tag,
                            self.status_live_fails, exc)
            return False
        if self.status_live_fails:
            log.info('%s: 감시 STATUS 복구 (%d회 실패 뒤)',
                     self.tag, self.status_live_fails)
        self.status_live_fails = 0
        self.status_live = fields
        self.status_live_at = time.time()
        self._check_health(fields)
        return True

    async def timer(self) -> str:
        """`TIMER` -- 컨트롤러의 10 ns tick 카운터 (매뉴얼 p.49).  실패하면 `''`.

        **STATUS 필드가 아니라 별도 명령이다** -- labtest 가 2026-08-27 에
        따로 뽑아낸 자리다(`e5d72b5`).  값이 회전마다 변하지 않으면 **타이밍
        코어가 멈춘 것**이고, 그것이 "노출이 안 걸렸나 / 독출이 안 끝나나" 를
        가르는 마지막 계측이다.

        ⚠️ 진단용이라 **예외를 올리지 않는다** -- 이것을 부르는 자리는 이미
        무언가 잘못된 순간이고, 거기서 새 예외를 내면 원인이 가려진다.
        """
        try:
            raw = await self.cmd('TIMER', timeout=T_FAST)
        except (ArchonError, TimeoutError, OSError) as exc:
            return 'ERR(%s)' % exc
        return raw.decode('ascii', 'replace').strip()

    async def diagnostic_snapshot(self, with_status: bool = True) -> str:
        """진단 한 줄 -- `FRAME` (+ `POWER`/`POWERGOOD`/`TIMER`).

        **labtest `_frame_snapshot()` 을 그대로 옮겼다** (v1.3.4, 2026-08-27).
        실기에서 프레임이 한 장도 안 나오던 증상을 가른 것이 이 한 줄이었고,
        원인은 결국 **`Sync In` 이 물려 상대 컨트롤러가 클록을 잡고 있던 것**
        이었다 (`../scr_labtest/README_labtest.md`).  그때 관측된 조합이
        `POWER=4` · `POWERGOOD=1` · `FRAME=0/0/0` 영구였다 --
        **`POWERGOOD` 은 외부 클록 의존을 보지 않는다.**

        읽는 법:

        | 보이는 것 | 뜻 |
        |---|---|
        | `FRAME` 이 안 오름 | 노출 미개시 (`LOADPARAMS`·타이밍·**Sync In**) |
        | `FRAME` 은 오르는데 `COMPLETE=0` | 독출이 버퍼를 못 채운다 (기하·tap) |
        | `TIMER` 가 안 변함 | 타이밍 코어 정지 |

        ⚠️ **예외를 올리지 않는다.**  실패한 순간에 부르는 것이므로 링크가 이미
        깨져 있을 수 있다 -- 그때는 실패 사유를 그 자리에 적는다.
        """
        try:
            fields = await self.query('FRAME', timeout=T_FAST)
        except (ArchonError, TimeoutError, OSError) as exc:
            return 'FRAME 질의 실패: %s' % exc
        line = ('RBUF=%s WBUF=%s  FRAME=%s/%s/%s  COMPLETE=%s/%s/%s  '
                'LINES=%s/%s/%s'
                % (fields.get('RBUF', '?'), fields.get('WBUF', '?'),
                   fields.get('BUF1FRAME', '?'), fields.get('BUF2FRAME', '?'),
                   fields.get('BUF3FRAME', '?'),
                   fields.get('BUF1COMPLETE', '?'),
                   fields.get('BUF2COMPLETE', '?'),
                   fields.get('BUF3COMPLETE', '?'),
                   fields.get('BUF1LINES', '?'), fields.get('BUF2LINES', '?'),
                   fields.get('BUF3LINES', '?')))
        if not with_status:
            return line
        # **감시가 이미 떠 둔 값을 쓰지 않는다** -- 지금 이 순간의 값이라야
        # 진단이 된다.  왕복이 둘 늘지만 부르는 자리는 실패한 순간뿐이다.
        try:
            status = await self.query('STATUS',
                                      timeout=self.cfg.status_timeout)
        except (ArchonError, TimeoutError, OSError) as exc:
            status = {'POWER': 'ERR(%s)' % exc}
        return line + ('  POWER=%s  POWERGOOD=%s  OVERHEAT=%s  TIMER=%s'
                       % (status.get('POWER', '?'),
                          status.get('POWERGOOD', '?'),
                          status.get('OVERHEAT', '?'), await self.timer()))

    def _check_health(self, status: dict[str, str] | None = None) -> None:
        """`STATUS` 응답에서 전원·과열 이상을 읽어 알린다 (F2).

        인자를 안 주면 헤더용 스냅샷(`self.status`)을 본다.  감시는
        `status_live` 를 넘겨 **같은 판정**을 쓴다 -- `_health_bad` 래치를
        공유하므로 취득 경로와 감시가 같은 이상을 두 번 알리지 않는다.
        (⚠️ 이 래치는 **로그 중복 방지**일 뿐 취득 판단이 아니다 -- "감시가
        취득 경로의 판단을 뒤집지 않는다" 규칙에 걸리지 않는다.)

        **막지는 않는다.**  이 필드들은 아직 실기 미검증(PROVISIONAL)이라,
        오독 하나로 관측을 통째로 세우는 쪽이 더 나쁘다 -- 첫 실행에서
        `tools/probe_archon.py` 1단계가 같은 값을 눈으로 확인한다.  대신 원인이
        보이도록 크게 남긴다: 종전에는 전원 이상이 밖에서 "취득 실패" 로만
        보였다.
        """
        # ⚠️ **아직 안 켰으면 `POWER=Off` 는 이상이 아니다** -- `powered` 를
        # 넘겨 그 판정만 접는다 (2026-09-08 벤치 오경보).
        bad = parse.health_problems(self.status if status is None
                                    else status, powered=self.powered)
        if not bad:
            self._health_bad = False
            return
        if not self._health_bad:
            self._health_bad = True
            log.error('%s: 컨트롤러 상태 이상 -- %s.  이 상태의 프레임은 '
                      '자료가 아니라 잔해일 수 있다 (매뉴얼 p.47)',
                      self.tag, ' / '.join(bad))

    async def frame(self) -> parse.FrameStatus:
        return parse.newest(await self.query('FRAME', timeout=T_FAST))

    # -- 셔터 트리거 ------------------------------------------------------

    async def set_trigger(self, *, high: bool | None = None,
                          forced: bool | None = None) -> None:
        """`TRIGOUTLEVEL`/`TRIGOUTFORCE` 를 **한 번의 `APPLYSYSTEM`** 으로 쓴다.

        ⭐ **둘을 같이 주는 것이 뜻이다.**  `WCONFIG` 는 적용을 안 하므로 둘을
        먼저 써 두고 한 번만 적용하면 **두 값이 동시에 선다** -- 따로 적용하면
        그 사이에 *"강제는 걸렸는데 레벨은 옛 값"* 인 찰나가 생긴다.
        ⭐ **`APPLYSYSTEM` 은 모듈 VCPU 를 재시작하지 않는다 -- 실측**
        (2026-09-08 벤치, DevNote 11.48).  `MOD10/VCPU_OUTREG15` 가 60초마다
        `+545`·`+546`·`+545` 로 한 번도 안 끊겼고 그 창에 `APPLYSYSTEM` 이 두 번
        들어 있었다.  ⚠️ 그러니 **적용을 줄이는 이유는 `DEWPRES` 결측이 아니다**
        (그 걱정은 실측으로 지웠다) -- **에지 시점을 한 명령이 정하게** 하는
        것이다 (`IcgDispatcher.cmd_shopen`).
        ⏳ 적용 하나가 몇 ms 인지는 아직 안 쟀다.
        ⛔ 둘 다 `None` 이면 아무것도 안 한다 -- 맨 `APPLYSYSTEM` 은 안 보낸다.
        """
        wrote = False
        if high is not None:
            await self.set_config('TRIGOUTLEVEL', '1' if high else '0')
            wrote = True
        if forced is not None:
            await self.set_config('TRIGOUTFORCE', '1' if forced else '0')
            wrote = True
        if wrote:
            await self.cmd('APPLYSYSTEM', timeout=T_SYSTEM)
        # ⭐ **적용이 끝난 뒤에 적는다** -- 선이 실제로 바뀌는 시점이 여기다.
        # 실패하면 위에서 예외가 올라가므로 **거짓 기록이 안 남는다**.
        if high is not None:
            self.note_trigger_level(bool(high))

    # -- Trigger Out 이 HIGH 였던 구간 (guide 헤더 `TRIGOUT` 카드의 원천) ----
    #
    # ⭐ **한 곳에서만 적는다** -- `set_trigger()` 가 레벨을 쓰는 유일한 자리다
    # (`set_trigger_level` 도 이것을 지난다).  ⛔ 명령마다 따로 적으면 경로가
    # 갈려 *"카드가 0 인데 로그에는 펄스가 있다"* 가 생긴다.
    # ⚠️ **`TRIGOUTFORCE` 는 안 본다** -- 운영자 문면이 *"`TRIGOUTLEVEL=1` 이었던
    # 적이 있으면 1"* 이다.  guide 는 쉬는 상태가 `FORCE=1` 이라 레벨이 곧 핀이다
    # (science 는 이 카드를 안 싣는다).
    # ⚠️ `ARCHON` 바이패스로 `WCONFIG TRIGOUTLEVEL` 을 직접 던지면 여기를 안
    # 지난다 -- 그 경로는 `config_dirty` 와 같은 한계다.

    #: `(시작, 끝)` epoch 구간들.  열려 있으면 끝이 `None`.
    _trig_spans: list | None = None

    #: 붙들 구간 수·나이 상한 -- 밤새 연속 가이딩에서 무한히 쌓이지 않게.
    _TRIG_SPAN_MAX = 32
    _TRIG_SPAN_AGE = 3600.0

    def note_trigger_level(self, high: bool) -> None:
        """Trigger Out 레벨이 바뀌었다고 적는다.

        ⭐ **구간으로 적는 이유**: 카드가 묻는 것이 *"이 프레임의 노출 창에
        HIGH 인 적이 있었나"* 라 **시점 하나로는 못 답한다**.  한 창에 펄스가
        둘 이상 들 수도 있고, 창보다 긴 펄스는 시작도 끝도 창 밖이다.
        """
        import time
        now = time.time()
        spans = self._trig_spans
        if spans is None:
            spans = self._trig_spans = []
        if high:
            if not spans or spans[-1][1] is not None:
                spans.append([now, None])
            return
        if spans and spans[-1][1] is None:
            spans[-1][1] = now
        # 오래된 것부터 버린다 -- 열린 구간은 남긴다.
        cut = now - self._TRIG_SPAN_AGE
        spans[:] = [s for s in spans if s[1] is None or s[1] >= cut]
        if len(spans) > self._TRIG_SPAN_MAX:
            del spans[:-self._TRIG_SPAN_MAX]

    def trigger_was_high_between(self, t0: float, t1: float) -> bool:
        """`[t0, t1]` 에 Trigger Out 이 HIGH 인 적이 있었나.

        ⚠️ **열린 구간은 `t1` 까지 이어진 것으로 본다** -- 지금도 HIGH 면
        그 창에 걸린 것이 맞다.
        """
        for start, end in (self._trig_spans or ()):
            if (t1 if end is None else end) >= t0 and start <= t1:
                return True
        return False

    async def trigger_state(self) -> tuple[str, str]:
        """`(TRIGOUTLEVEL, TRIGOUTFORCE)` -- **`RCONFIG` 되읽기**.

        ⛔ **캐시(`self.config`)로 이 판단을 하면 안 된다.**  `set_config` 는
        왕복이 실패해도 캐시를 **먼저** 갈아 끼우므로(11.13 F5), 캐시가
        *"이미 `FORCE=1` 이다"* 라고 거짓말하면 `SHOPEN` 이 무장을 건너뛰고
        **조용히 아무것도 안 한다** (선은 안 올라가는데 `DONE` 은 나간다).
        ⚠️ 왕복 둘이지만 **적용이 아니라** 빠르고 모듈을 안 건드린다.
        """
        level = (await self.read_config('TRIGOUTLEVEL')).strip()
        forced = (await self.read_config('TRIGOUTFORCE')).strip()
        return level, forced

    async def set_trigger_forced(self, forced: bool) -> None:
        """`TRIGOUTFORCE` -- 셔터/광원 트리거 라인을 강제할지.

        Archon 은 셔터를 **Trigger Out 이 INT 클록을 따르게 해서** 구동한다
        (매뉴얼 p.15).  그래서 `TRIGOUTFORCE=0` 이 "타이밍 스크립트가 몬다"
        (= 셔터 노출), `1` 이 "`TRIGOUTLEVEL` 로 고정" (= 열지 않는다) 이다.
        labtest 의 `shopen` 분기가 정확히 이 두 값이다.
        ⭐ 한 값만 쓰는 얇은 겉이다 -- 둘을 같이 쓸 때는 `set_trigger()`.
        """
        await self.set_trigger(forced=forced)

    async def set_trigger_level(self, high: bool) -> None:
        """`TRIGOUTLEVEL` -- **강제했을 때** Trigger Out 이 나갈 레벨.

        ⛔ `TRIGOUTFORCE` 와 **다른 물건이다**: 이것은 레벨이고 그것은 *강제할지*
        다.  `TRIGOUTFORCE=0` 이면 타이밍 스크립트가 몰므로 이 값은 안 나간다.
        ⚠️ 그래서 핀을 실제로 HIGH 로 세우려면 **둘 다** 필요하다 --
        `TRIGOUTLEVEL=1` + `TRIGOUTFORCE=1`.  guide ACF 의 출고값은 둘 다 0 이다.
        ⭐ 한 값만 쓰는 얇은 겉이다 -- 둘을 같이 쓸 때는 `set_trigger()`.
        """
        await self.set_trigger(high=high)

    # -- 노출 -------------------------------------------------------------
    #
    # **프레임 상태는 프레임이 들고 간다 (`FrameTicket`).**  컨트롤러 필드에
    # 두면 파이프라인이 겹칠 때 뒤 프레임이 앞 프레임의 값을 덮는다 -- 저장은
    # `write_delay` 뒤에 백그라운드로 돌고 그 사이 다음 프레임이 이미
    # `LOADPARAMS` 를 냈을 수 있다.  그러면 앞 프레임의 저장이 "직전 프레임
    # 번호" 를 잘못 알고, 반대로 앞 프레임의 뒷정리가 뒤 프레임의 "노출을
    # 걸었다" 표시를 지운다(-> 이중 노출).
    #
    # `ics_sim` 이 같은 부류를 두 번 겪었다 -- 파일 일련번호 경합(12.10)과
    # D-016 선검사의 채널 suffix 재읽기(11.20 critical).  결론은 매번 같았다:
    # **프레임의 것은 프레임이 정하고, 나중에 다시 읽지 않는다.**

    async def trigger(self, exptime_ms: int, *, queue: bool = True,
                      suffix: str = '', exposures: int = 1) -> FrameTicket:
        """노출을 걸고 곧바로 돌아온다 (적분·독출은 컨트롤러가 몬다).

        순서는 labtest 그대로다 -- **프레임 번호를 먼저 읽고** `IntMS`,
        `Exposures`, `LOADPARAMS`.  번호를 먼저 읽는 이유는 그 값이 "새
        프레임이 나왔나" 의 기준이기 때문이다.

        Args:
            queue: 저장 대기열에 넣을지.  flush 는 **버리는 프레임**이라
                `False` 다 -- 넣으면 저장 쪽이 그것을 자기 프레임으로 집어 온다.
            suffix: 이 프레임의 이름 (`<YYYYMMDD>.<NNNNNN>`).  저장 쪽이 **자기
                프레임의 표를 골라 집는** 근거다.
            exposures: `Exposures` 파라미터.  **science 는 1** (프레임마다
                다시 건다).  guide 는 **n 을 한 번에** 걸어
                시퀀서가 flush 뒤 유휴 없이 연달아 찍게 한다 -- 그때 둘째 프레임부터는 `expect_next()`
                로 표만 잇는다(왕복에 `LOADPARAMS` 가 없다).  타이밍
                스크립트가 `GOTO Start` 뒤 `Exposures` 가 남아 있으면 곧바로
                `Exposure:` 로 되돌아가는 것이 근거다.
        """
        # **한 번의 `FRAME` 으로 둘을 뽑는다** -- 프레임 번호(기준값)와 세
        # 버퍼의 번호(기준선).  왕복은 종전과 같다.
        self.loadparams_sent = False
        _fields = await self.query('FRAME', timeout=T_FAST)
        prev = parse.newest(_fields).frame
        before = parse.buffer_frames(_fields)
        await self.set_config(self.cfg.param_intms_slot,
                              '%s=%d' % (self.cfg.param_intms_name,
                                         max(int(exptime_ms), 0)))
        await self.set_config(self.cfg.param_exposures_slot,
                              '%s=%d' % (self.cfg.param_exposures_name,
                                         max(int(exposures), 1)))
        # flush 는 설정 메모리의 `FirstFlush` 가 정한다 -- guide 는 ACF 상수 1(R2616+),
        # science 는 `ccdflush` 옵션(`set_first_flush`).  이 LOADPARAMS 가 그 값을 RAM 에
        # 실어 코어가 `FlushFrame` 한 번을 돌고 `FirstFlush--` 로 소비한다.  호스트가
        # 프레임마다 쓰고 되쓰는 플래그는 없다 (DevNote 11.33).
        # 취소가 여기서 걸리면 `_locked_thread` 가 스레드를 끝까지 기다리므로
        # 표시가 True 인 순간 ack 는 이미 (또는 곧) 받은 것이다.
        self.loadparams_sent = True
        await self.cmd('LOADPARAMS', timeout=T_SYSTEM)
        timing = getattr(self, 'last_cmd_timing', None)
        ticket = FrameTicket(
            suffix=suffix,
            prev_frame=prev,
            prev_frames=before,
            int_until=(time.monotonic() + exptime_ms / 1000.0
                       if exptime_ms > 0 else None))
        if timing is not None:
            t_s, t_r, u_s = timing
            ticket.armed_mono = (t_s + t_r) / 2.0
            ticket.armed_utc = u_s + (t_r - t_s) / 2.0
            ticket.arm_rtt = t_r - t_s
            if ticket.arm_rtt > 0.020:
                # ⛔ **종전 문면 *"링크가 느리다"* 는 오귀속이었다** (2026-09-09
                # 정정).  링크는 빠르다 -- `RCONFIG` 3회가 **6 ms** 다.  느린
                # 것은 **`LOADPARAMS` 자신의 처리**이고, APPLY 계열이 다 그렇다
                # (`APPLYSYSTEM` ≈229 ms · `RESETTIMING` 246 ms 실측,
                # DevNote 11.55).  ⚠️ 원인을 링크로 적으면 망을 들여다보게 만든다.
                # ⭐ 경고를 남기는 이유는 그대로다: 이 왕복의 **중점**을
                # `DATE-OBS` 로 쓰므로 불확도가 그 절반이다.
                log.warning('%s: LOADPARAMS 왕복 %.1f ms -- 첫 저장 프레임 '
                            'DATE-OBS 의 불확도가 그 절반이다.  ⚠️ 링크가 아니라 '
                            '**이 명령 자체의 처리 시간**이다 (APPLY 계열은 다 '
                            '200 ms 대 -- 실측)', self.tag, ticket.arm_rtt * 1e3)
        self._current = ticket
        if queue:
            self._queue.append(ticket)
        log.info('%s: 노출 지시 -- IntMS=%d Exposures=%d (프레임 %d 다음%s)',
                 self.tag, int(exptime_ms), max(int(exposures), 1), prev,
                 '' if queue else ', 버림')
        return ticket

    async def expect_next(self, after: FrameTicket, *, suffix: str = '',
                          exptime_ms: int = 0,
                          queue: bool = True) -> FrameTicket:
        """**이미 걸려 있는** 연속 노출의 다음 표를 만든다 (`LOADPARAMS` 없음).

        `trigger(exposures=n)` 로 n 장을 한 번에 걸어 두면 시퀀서가 유휴 없이
        연달아 찍는다 -- 호스트는 프레임마다 노출을 다시 걸지 않고 **표만**
        이어 두면 된다.

        ⚠️ 기준선은 **직전 표의 완료 프레임 번호**다.  지금 `FRAME` 의 최신
        번호를 쓰면 안 된다 -- 우리 루프보다 독출이 빠르면 다음 프레임이 이미
        나와 있고, 그것을 기준으로 잡으면 **그 프레임을 통째로 건너뛴다**.

        Args:
            after: 직전 프레임의 표 (`ready` 가 채워져 있어야 한다).
            exptime_ms: 이 프레임의 `IntMS` -- 시한 계산(`int_until`)에만 쓴다.
        """
        if after.ready is None:            # pragma: no cover -- 호출 규약 위반
            raise ArchonError('%s: 직전 프레임이 아직 안 끝났다 -- expect_next '
                              '는 완료된 표 뒤에만 부른다' % self.tag)
        fields = await self.query('FRAME', timeout=T_FAST)
        ticket = FrameTicket(
            suffix=suffix,
            prev_frame=after.ready.frame,
            prev_frames=parse.buffer_frames(fields),
            int_until=(time.monotonic() + exptime_ms / 1000.0
                       if exptime_ms > 0 else None))
        self._current = ticket
        if queue:
            self._queue.append(ticket)
        return ticket

    async def expect_from_now(self, *, suffix: str = '',
                              queue: bool = False) -> FrameTicket:
        """**지금**을 기준선으로 한 표 -- `LOADPARAMS` 없이, 이미 도는 프레임을
        기다리는 데 쓴다 (꼬리 소화, DevNote 9.15-(9)).

        `arm_sequence()` 의 `LOADPARAMS` 도중 ABORT 가 오면 컨트롤러는 돌기
        시작했는데 표가 없다 -- 그때 `FRAME` 한 번으로 기준선을 잡는다.
        """
        fields = await self.query('FRAME', timeout=T_FAST)
        ticket = FrameTicket(
            suffix=suffix,
            prev_frame=parse.newest(fields).frame,
            prev_frames=parse.buffer_frames(fields),
            int_until=None)
        self._current = ticket
        if queue:
            self._queue.append(ticket)
        return ticket

    async def newest_frame(self) -> int:
        """`FRAME` 한 번 -- 지금 완료돼 있는 가장 새 프레임 번호 (-1 = 없음)."""
        return parse.newest(await self.query('FRAME', timeout=T_FAST)).frame

    async def set_exposures(self, n: int) -> None:
        """남은 연속 노출 수를 바꾼다 (`0` 이면 현재 프레임까지만).

        STOP 경로가 쓴다 -- 시퀀서는 `Exposures` 가 0 이 되면 현재 프레임을
        마치고 유휴 루프로 돌아간다 (타이밍 스크립트 `Start:`).  ⚠️ 설정 메모리의
        `FirstFlush` 가 1 이면(guide 상수, R2616+) 이 LOADPARAMS 도 flush 한 번을
        실어 **마지막 프레임 뒤 CCD 를 비우고** 유휴로 간다 (DevNote 11.33).
        """
        await self.set_config(self.cfg.param_exposures_slot,
                              '%s=%d' % (self.cfg.param_exposures_name,
                                         max(int(n), 0)))
        await self.cmd('LOADPARAMS', timeout=T_SYSTEM)
        log.info('%s: Exposures=%d 로 갱신', self.tag, max(int(n), 0))

    async def abort_now(self) -> None:
        r"""**진행 중 적분을 지금 끊는다** (ABORT) -- `Exposures=0` -> `RESETTIMING`.

        ⭐ **순서가 뜻이다.**  `RESETTIMING` 은 코어를 `Start:` 로 돌리는데 그 두
        번째 줄이 `IF Exposures GOTO Exposure` 다 -- `Exposures` 가 남아 있으면
        **곧바로 다음 노출을 시작한다**.  그래서 `Exposures=0` 을 먼저 건다.

        ⭐ **셔터는 이것만으로 닫힌다.**  `Start:` 첫 줄의 상태가 `RESET` 이고
        ACF 의 `STATE0\CONTROL="0,0"` 이라 **6비트를 전부 0** 으로 몬다 -- INT
        비트(bit0)도 0 이므로 `TRIGOUTFORCE=0`(스크립트가 모는 상태)에서 핀이
        LOW 가 된다.  ⛔ 그래서 `TRIGOUTFORCE=1`+`LEVEL=0` 으로 붙들 필요도,
        `NoIntMS` 전용 상태를 새로 만들 필요도 없다 (ACF 실측, 운영자 2026-09-09).

        ⚠️ 진행 중이던 프레임은 미완료로 남고 그 표는 버려진다 -- ABORT 는
        저장하지 않으므로 맞는 거동이다 (`reset_timing`).
        ⚠️ 설정 메모리의 `FirstFlush` 가 1 이면 `Start:` 가 `FlushFrame` 으로
        뛴다 -- 끊긴 전하를 비우므로 해롭지 않다.  science 는 `ccdflush` 가
        정한다 (운영자: *"science 는 abort 뒤 flush 가 필요 없다"* -- 필요 없을
        뿐 해가 되지는 않는다).
        """
        await self.set_exposures(0)
        await self.reset_timing()

    @property
    def triggered(self) -> bool:
        """**이번 프레임**의 노출이 이미 걸렸나 (flush 는 해제한다)."""
        return self._current is not None

    @property
    def current_ticket(self) -> FrameTicket | None:
        """진행 중 프레임의 표.  `readout()` 이 이것을 기다린다."""
        return self._current

    @property
    def integrating(self) -> bool:
        """컨트롤러가 아직 적분 중이라고 볼 수 있나 (호스트 시각 기준)."""
        t = self._current
        return (t is not None and t.int_until is not None
                and time.monotonic() < t.int_until)

    @property
    def integration_left(self) -> float:
        """남은 적분 시간 [s] (호스트 시각 기준).  적분 중이 아니면 0.

        `close_shutter()` 가 "조기 종료인가" 를 이 값으로 판단한다 --
        참/거짓만 보면 정상 경로의 종료 순간과 구별할 수 없다.
        """
        t = self._current
        if t is None or t.int_until is None:
            return 0.0
        return max(t.int_until - time.monotonic(), 0.0)

    def release_current(self) -> None:
        """이번 프레임의 노출·독출이 끝났음을 표시한다.

        저장 대기열은 건드리지 않는다 -- 그쪽은 `take_ticket()` 이 FIFO 로
        가져간다.  이것을 안 해 주면 다음 프레임의 `readout()` 이 "이미
        걸렸다" 고 보고 노출을 안 건다.
        """
        self._current = None

    def take_ticket(self, suffix: str = '') -> FrameTicket | None:
        """저장 대기열에서 **내 프레임의** 표를 가져온다.

        `suffix` 를 주면 그 이름의 표를 찾고, **그보다 앞선 표는 버린다** --
        앞선 표가 아직 남아 있다는 것은 그 프레임이 취소되거나 저장에 실패해
        아무도 꺼내지 않았다는 뜻이다.  FIFO 로 그냥 집으면 이 파일이 **그
        프레임의 픽셀**을 담고 헤더는 내 것이 된다 (경고 0).

        `suffix` 가 비면 종전처럼 FIFO -- 시험용 경로다.
        """
        if not self._queue:
            return None
        if not suffix:
            return self._queue.pop(0)
        for i, t in enumerate(self._queue):
            if t.suffix == suffix:
                dropped = self._queue[:i]
                del self._queue[:i + 1]
                if dropped:
                    log.warning(
                        '%s: 저장되지 않은 프레임 표 %d개를 버린다 (%s) -- '
                        '그 프레임은 취소되거나 저장에 실패했다.  내 프레임(%s)의 '
                        '표를 집는다', self.tag, len(dropped),
                        ', '.join(d.suffix or '?' for d in dropped), suffix)
                return t
        # 내 표가 없다 -- 대기열에 남은 것은 전부 남의 것이므로 집지 않는다.
        log.error('%s: 프레임 %s 의 저장 표가 없다 (대기열: %s) -- 이 프레임은 '
                  '저장하지 않는다', self.tag, suffix,
                  ', '.join(t.suffix or '?' for t in self._queue) or '비어 있음')
        return None

    def drop_tickets(self, why: str) -> int:
        """대기열을 비운다.  버린 개수를 돌려준다 (진단용).

        프레임이 끊겨 저장이 없을 것이 확실할 때 부른다.
        """
        n = len(self._queue)
        if n:
            log.warning('%s: 저장 표 %d개를 버린다 (%s)', self.tag, n, why)
            self._queue.clear()
        return n

    def discard_ticket(self, ticket: FrameTicket | None) -> bool:
        """표 **하나만** 대기열에서 집어 버린다 -- 그 프레임은 저장하지 않는다.

        ⭐ **한 대의 프레임을 잃었을 때 쓴다** (운영자 지시 2026-09-04).  그
        대의 표를 남겨 두면 시퀀서가 띄운 `_store` 가 `write_frame()` 에서
        같은 표를 **다시** 기다려 `frame_timeout`(기본 300초)을 통째로 한 번
        더 쓴다 -- 그 사이 성한 대의 저장은 이미 끝나 있고, 관측자는 이유
        없이 5분을 더 기다린다.  버리면 `take_ticket()` 이 곧바로 `None` 을
        돌려주어 그 컨트롤러만 빠르게 `ERROR` 로 끝난다.

        ⚠️ **`drop_tickets()` 와 다르다** -- 그쪽은 대기열을 통째로 비우므로
        `GO n` 파이프라인에서 아직 저장 중인 **앞 프레임의 표**까지 함께
        날린다.  여기서는 준 객체 하나만 지운다 (동일성 비교 -- 같은 suffix 의
        표가 둘일 수 있는 구성을 배제하지 않는다).
        """
        if ticket is None:
            return False
        for i, t in enumerate(self._queue):
            if t is ticket:
                del self._queue[i]
                log.warning('%s: 프레임 %s 의 저장 표를 버린다 -- 그 프레임은 '
                            '확인되지 않았다', self.tag, t.suffix or '?')
                return True
        return False

    async def flush(self, poll: float | None = None) -> None:
        """전체 독출 flush (labtest `bFullFlush`) -- 프레임 하나를 버린다.

        `IntMS=0` 으로 노출을 걸어 축적된 전하를 읽어내고 그 프레임을 쓰지
        않는다.  레거시 `ERASE` 의 자리이고, 걸리는 시간은 **독출 1회분**이다
        (레거시 실측 7.24초는 IC 구현 값이라 실기와 다르다 -- 실측 대상).
        """
        ticket = await self.trigger(0, queue=False)
        async for _pct in self.wait_frame(ticket, poll=poll):
            pass
        self.release_current()
        log.info('%s: flush 완료 (프레임 %d 버림)', self.tag,
                 ticket.ready.frame if ticket.ready else -1)

    async def wait_frame(self, ticket: FrameTicket,
                         poll: float | None = None):  # noqa: ANN201
        """그 프레임이 완료될 때까지 기다리며 **진행률을 yield** 한다.

        진행률은 `FRAME` 의 `BUFnLINES` / ACF `LINECOUNT` 다 (p.50 · DevNote
        10.3).  ⚠️ `BUFnHEIGHT` 는 분모가 아니다 -- `FRAMEMODE=2` 면 그 2배라
        `PCTREAD` 가 50% 에 묶인다 (`parse.progress_of`).  적분
        중에는 쓰기 버퍼가 없어 `None` 이 나오므로 아무것도 내지 않는다 --
        `PCTREAD=` 는 독출 진행이라야 뜻이 있다.

        마지막에 **100 을 내지 않는다** -- 완료 통보는 부르는 쪽(`readout()`)의
        몫이고, 그 쪽이 시퀀서 규약(`pctread_final`)을 안다.  완료된 프레임은
        `ticket.ready` 에 담긴다.
        """
        if ticket.ready is not None:
            return
        interval = self.cfg.frame_poll if poll is None else poll
        # **최소 1 이다.**  0 이면 폴링마다 같은 값을 되풀이해 보내게 되고
        # (폴링이 라인 진행보다 빠르다), 그건 와이어 소음일 뿐이다.  0 은
        # "값이 바뀔 때마다" 로 읽는다.
        step = max(int(self.cfg.progress_step), 1)
        reported = -1
        #: 첫 폴링의 진행률 -- **직전 프레임의 잔값**일 수 있어 기준선으로만 쓴다.
        base_pct = None
        #: 그 기준선에서 값이 움직였나 (= 이 프레임이 채워지기 시작했다).
        moved = False
        prev = ticket.prev_frame
        limit = float(getattr(self.cfg, 'frame_timeout', 0.0) or 0.0)
        started = time.monotonic()
        # **상한은 적분이 끝난 뒤부터 센다** (2026-08-28 수정).
        #
        # 종전에는 `now + frame_timeout` 이라 **DARK/BIAS 의 긴 노출에서 헛
        # 시한**이 났다: 셔터 노출은 시퀀서가 카운트다운을 다 하고 `readout()`
        # 을 부르므로 여기 들어올 때 적분이 이미 끝나 있지만, DARK/BIAS 는
        # `_readout_stream()` 이 `IntMS=<적분시간>` 으로 걸고 **곧바로** 여기로
        # 들어온다 -- 300초 상한에 600초 dark 를 걸면 프레임이 정상으로 나오는
        # 중에 `DMA WAIT TIMEOUT` 이 났다.  labtest 도 같은 계산이다
        # (`deadline = exptime/1000 + FRAME_WAIT_MAX`, v1.3.4).
        deadline = None
        if limit > 0:
            deadline = max(started, ticket.int_until or 0.0) + limit
        # 프레임 대기 중 주기 덤프 -- 취득이 안 끝날 때 "노출이 안 걸렸나 /
        # 독출이 안 끝나나" 를 가르는 계측이다 (labtest `FRAME_DUMP_ENABLE`).
        # **정상 취득이 도는 동안은 꺼 둔다**(기본 0) -- 왕복이 셋 늘어난다.
        dump_every = float(getattr(self.cfg, 'frame_dump', 0.0) or 0.0)
        next_dump = (started + dump_every) if dump_every > 0 else None
        while True:
            now = time.monotonic()
            if deadline is not None and now > deadline:
                # **영구 대기를 오류로 바꾼다.**  독출이 시작되지 않으면
                # `EXPSTATUS=READOUT` 에 갇혀 관측자 화면이 멈추고 OBSAgent 가
                # `force_idle` 타임아웃으로 `opause` 에 빠진다 -- 조용한 정지가
                # 가장 나쁜 실패다.
                #
                # **실패한 순간의 진단을 항상 남긴다** -- `frame_dump` 설정과
                # 무관하다 (labtest v1.3.4 가 세운 규칙).  이 증상은 간헐이라
                # 평소 덤프를 꺼 두면 정작 재발했을 때 증거가 남지 않는다.
                # ⚠️ 실기에서 이 조합(`POWER=4` · `POWERGOOD=1` · `FRAME` 정지)
                # 의 원인은 **`Sync In` 이 물려 상대 컨트롤러가 클록을 잡고
                # 있던 것**이었다 -- `POWERGOOD` 은 외부 클록을 보지 않는다.
                log.error('%s: 프레임 대기 시한 초과 -- %s', self.tag,
                          await self.diagnostic_snapshot())
                raise ArchonError(
                    '%s: 프레임 %d 이 %.0f초 안에 나오지 않았다 (적분 %.1f초 '
                    '뒤부터 셌다) -- 독출이 시작되지 않았을 수 있다.  ACF·'
                    'LOADPARAMS·클록, 그리고 **Sync In 결선과 상대 유닛**을 '
                    '보라.  [archon] frame_timeout 으로 상한을 조정한다'
                    % (self.tag, prev + 1, limit,
                       max((ticket.int_until or started) - started, 0.0)),
                    cmd='FRAME')
            fields = await self.query('FRAME', timeout=T_FAST)
            # **"내 다음 프레임" 을 찾는다** -- "최신 프레임" 이 아니다.  저장이
            # 늦으면 그 사이 프레임이 더 나와 있고, 최신 것을 집으면 이 파일이
            # **남의 노출 픽셀**을 담는다(헤더는 이 프레임의 것이라 아무 경고도
            # 없다).
            mine = parse.next_frame(fields, prev)
            if mine is None:
                # **카운터가 뒤로 갔나** -- 되감김(한 바퀴) 또는 컨트롤러
                # 재시작.  `next_frame()` 은 `frame > prev` 로 찾으므로 이
                # 경우 **영원히 `None`** 이고, 그대로 두면 `frame_timeout`
                # 까지 기다리다 노출을 잃는다 (2026-08-30 발견).
                #
                # ⚠️ 폭을 모르므로 크기로 판별하지 않는다 -- **기준선 대비
                # 변화**로 판별한다 (`parse.restarted_frame` 의 설명).
                mine = parse.restarted_frame(fields, prev, ticket.prev_frames)
                if mine is not None:
                    log.error(
                        '%s: 프레임 번호가 뒤로 갔다 -- %d 다음을 기다렸는데 '
                        '버퍼 %d 에 %d 이 새로 들어왔다.  카운터 되감김이거나 '
                        '컨트롤러가 재시작했다.  **이 프레임은 받는다** (기준을 '
                        '%d 로 재동기).  자주 보이면 BUFnFRAME 폭을 실측해 '
                        '두라 -- 매뉴얼 p.50 에 폭이 안 적혀 있다',
                        self.tag, prev, mine.buf + 1, mine.frame, mine.frame)
                    prev = mine.frame - 1        # 아래 연속성 검사를 통과시킨다
            if mine is not None:
                # **첫 실행(prev < 0)에는 번호를 못박지 않는다** -- 프레임이
                # 하나도 없으면 `newest()` 가 -1 을 주고, 컨트롤러의 첫 프레임
                # 번호가 1 이면 "0 을 지나쳤다" 가 되어 첫 노출을 버린다.
                if prev >= 0 and mine.frame != prev + 1:
                    raise ArchonError(
                        '%s: 프레임 %d 을 지나쳤다 (찾은 것은 %d) -- 그 버퍼가 '
                        '이미 덮였다.  저장이 다음 노출보다 늦었다는 뜻이니 '
                        'write_delay·독출 시간과 버퍼 수(BIGBUF 는 2개)를 보라'
                        % (self.tag, prev + 1, mine.frame), cmd='FRAME')
                ticket.ready = mine
                return
            # ⛔ **낡은 진행률을 내보내지 않는다** (벤치 2026-09-08).
            #
            # 프레임이 끝나도 컨트롤러는 `WBUF` 를 **그 버퍼에 그대로 두고**
            # `BUFnLINES` 도 꽉 찬 값으로 남긴다.  그래서 무장 직후 첫 폴링이
            # **직전 프레임의 99** 를 진행률로 읽어 `PCTREAD=99` 를 5 ms 만에
            # 내보냈다 -- 그 뒤로는 `step` 을 못 넘어 프레임당 한 번씩만 나갔다.
            # ⚠️ 이 함수의 머리말이 *"적분 중에는 쓰기 버퍼가 없어 None 이
            # 나온다"* 고 적어 둔 것이 **하드웨어에서 성립하지 않았다.**
            #
            # ⭐ 판정: **첫 값은 기준선으로만 쓰고 내보내지 않는다.**  값이
            # 그 기준선에서 움직인 순간부터가 이 프레임의 진행이다.
            # ⛔ 버퍼 식별로 가르려다 실패했다 -- 컨트롤러가 같은 버퍼를
            # 재사용하면 *"낡은 것"* 과 *"새로 채우는 중"* 이 구별되지 않아
            # 진행률이 **하나도 안 나갔다** (시험이 잡았다).  기준선 방식은
            # 버퍼를 어떻게 쓰든 성립한다.
            # ⚠️ 대가는 **이른 표본 하나**를 잃는 것뿐이고, 틀린 값을 내지는
            # 않는다 -- 그 방향이 맞다.
            pct = parse.newest(fields).progress_of(self.lines_total)
            if pct is not None and base_pct is None:
                base_pct = pct           # 기준선 -- 직전 프레임의 잔값일 수 있다
            elif pct is not None and pct != base_pct:
                moved = True
            if moved and pct is not None and pct >= reported + step:
                reported = pct
                yield pct
            if next_dump is not None and time.monotonic() >= next_dump:
                next_dump = time.monotonic() + dump_every
                log.info('%s: 프레임 대기 %.0f초 -- %s', self.tag,
                         time.monotonic() - started,
                         await self.diagnostic_snapshot())
            await asyncio.sleep(interval)

    async def await_frame(self, ticket: FrameTicket) -> parse.FrameStatus:
        """그 프레임의 완료를 기다린다 (진행률은 버린다).

        **저장 쪽이 부른다.**  진행률을 흘려보내는 것은 master 컨트롤러 하나뿐
        이므로(시퀀서가 `readout(master)` 만 부른다) 다른 대의 프레임은 아무도
        기다려 주지 않는다 -- 그 대의 `write_frame()` 이 여기서 기다린다.
        """
        async for _pct in self.wait_frame(ticket):
            pass
        if ticket.ready is None:                     # pragma: no cover
            raise ArchonError('%s: 완료 프레임을 확인하지 못했다' % self.tag)
        return ticket.ready

    # -- FETCH ------------------------------------------------------------

    async def fetch(self, fs: parse.FrameStatus,
                    expect_bytes: int) -> bytearray:
        """프레임 데이터를 받아 온다.  **선언 기하와 다르면 받지 않는다.**

        대조를 fetch **앞**에 둔 것이 요점이다 -- fetch 는 수십 초가 걸리고,
        그 뒤에 거절하면 그 시간을 버린다.  그리고 픽셀 수가 아니라 **바이트
        수**로 대조한다: `samplemode`(32bit 표본)는 기하가 선언과 같은데도
        정확히 2배가 되므로 픽셀 비교로는 안 잡힌다 (DevNote 11.22 (3)).

        패딩까지 넣고 나면 그 어긋남이 astropy 에서 `Header missing END card`
        로 나와 **파일 전체를 못 읽게** 된다 -- 여기서 막는 것이 값싸다.
        """
        if fs.data_bytes != expect_bytes:
            raise ArchonError(
                '%s: 프레임이 %d B (%dx%d, %s) 인데 선언 기하는 %d B 다 -- '
                'fetch 하지 않는다.  ACF 기하와 samplemode 를 확인하라.'
                % (self.tag, fs.data_bytes, fs.width, fs.height,
                   'samplemode/32bit' if fs.samplemode else '16bit',
                   expect_bytes), cmd='FETCH')

        # **버퍼를 잠근다** (`LOCKn`, 매뉴얼 p.50).  BIGBUF 는 버퍼가 둘뿐이고
        # 노출 1회가 프레임 2개(flush + 취득)를 만들므로, **다음 노출이 이
        # 프레임의 버퍼를 덮는다.**  저장은 `write_delay` 뒤에 백그라운드로
        # 도는 일이라 그 경합이 실재한다 -- 덮인 뒤에 fetch 하면 raw 한 장이
        # **남의 노출 픽셀**을 담고, 헤더는 이 프레임의 것이라 아무 경고도 없다.
        #
        # 매뉴얼 p.71 은 `LOCK` 을 **통상 경로**로 적어 두었다("새 프레임이
        # 있으면 호스트는 LOCK 을 내려 그 버퍼가 덮이는 것을 막고 FETCH 한다").
        # ⚠️ **그러나 그것은 판정이 아니라 가설의 강도다** -- 매뉴얼은
        # 2021-02-23 판이고 **현행 FW 와 양방향으로 어긋날 수 있다**(운영자
        # 2026-08-30).  이 저장소 안에 이미 반례가 둘 있다(`MODn_TYPE` 16+ ·
        # AD 모듈 슬롯).  **판단 근거는 실측**이다 -- DevNote 8.7.
        #
        # ⚠️ labtest 는 2026-05-28 에 `LOCK` 을 뺐다("remove to fetch debug").
        # 되돌렸고 ✅ **실기 확인은 종결됐다** (2026-09-01, 두 유닛 -- DevNote
        # 10.4·10.6): `LOCK` 은 매번 반영되고(RBUF 15/15) 대가가 없으며(`lock`
        # = `idle` = 368 행/초), **지킬 구간이 실재한다** -- 잠그지 않은 채
        # fetch 중 프레임 경계가 걸리면 엔진이 우리가 읽는 버퍼로 옮겨온다
        # (2/2 관측).  `[archon] lock_buffer = true` 가 정본이다.  끄더라도
        # 아래 대조는 남고, `recheck_after_fetch` 가 fetch 중의 창까지 본다.
        # ⚠️ **science 는 버퍼가 둘뿐**이라 하나를 잠그면 엔진에 하나만 남는다
        # (guide 는 셋이라 둘이 남는다).  남는 버퍼가 없으면 엔진은 **쓰던
        # 버퍼를 재사용**해 다음 프레임을 덮는다 (H3 닫힘, `--hold 20` 실측)
        # -- 그래서 잠금은 프레임 주기보다 짧아야 하고, 그 상한이
        # `fetch_timeout` 이다 (config 기동 검사가 본다).
        buf_n = fs.buf + 1
        lock = getattr(self.cfg, 'lock_buffer', True)
        # **관측값을 먼저 지운다** -- `LOCK` 이 실패하면 지난 프레임의 값이
        # 남아 실험 로그가 거짓말을 한다.
        self.lock_rbuf = self.lock_wbuf = self.lock_wbuf_after = -1
        try:
            # ⭐ 잠금도 `try` 안이다 (DevNote 10.9) -- `LOCK%d` 의 응답이
            # 타임아웃으로 죽어도 컨트롤러 쪽은 이미 잠겼을 수 있으니
            # `finally` 의 `LOCK0` 을 타야 한다.  잠기지 않은 채 `LOCK0` 을
            # 보내는 것은 무해하다.
            if lock:
                await self.cmd('LOCK%d' % buf_n, timeout=T_FAST)
            # **잠근 뒤에 다시 확인한다.**  잠그기 직전에 이미 덮였을 수 있다.
            live_fields = await self.query('FRAME', timeout=T_FAST)
            live = parse.buffer_frame(live_fields, buf_n)
            # ⭐ **같은 응답에서 잠금 상태도 뽑는다** (왕복 0, 2026-08-30).
            # `LOCKn` 이 FW 에 먹는지 -- A-5 판단 ② 는 2026-09-01 종결 (두 FW
            # 15/15, DevNote 10.4).  이 관측은 이제 FW 회귀 감시다.
            self.lock_rbuf, self.lock_wbuf = parse.lock_state(live_fields)
            if lock and self.lock_rbuf != buf_n:
                # ✅ 두 FW(1252·1261) 가 15/15 반영했고 `RBUF` 는 FW 가 낸다
                # (8.11) -- "미구현" 도피구는 닫혔다.  여기가 뜨면 **FW 회귀
                # 신호**다.  그래도 `recheck_after_fetch` 가 마지막 방어다.
                log.warning(
                    '%s: LOCK%d 을 보냈는데 RBUF=%d 다 (기대 %d) -- 2026-09-01 '
                    '두 FW 15/15 반영과 다르다.  FW 가 바뀌었나 (DevNote 10.4).  '
                    'recheck_after_fetch 를 켜 두라 (매뉴얼 p.50)',
                    self.tag, buf_n, self.lock_rbuf, buf_n)
            if live != fs.frame:
                raise ArchonError(
                    '%s: 버퍼 %d 가 프레임 %d 로 덮였다 (내 프레임은 %d) -- '
                    'fetch 하지 않는다.  저장이 다음 노출보다 늦었다는 뜻이니 '
                    'write_delay·독출 시간을 보라 (lock_buffer=%s)'
                    % (self.tag, buf_n, live, fs.frame, lock), cmd='FETCH')

            # 상한은 크기에서 뽑는다 -- 1 GB/s 를 밑도는 어떤 링크라도 넉넉하고,
            # 그러면서 "영구히 멈춤" 은 막는다.  이 유도값은 `[archon]
            # fetch_timeout` 이 0 일 때만 쓰인다 -- 실측(99~107 MiB/s, DevNote
            # 10.4)으로 ini 는 10초다.  ⚠️ 잠금 상한이기도 하다: 주기(13.27초)
            # 를 넘으면 다음 장이 덮인다(10.6) -- `config` 기동 검사가 알린다.
            # `frame_timeout` 과 **별개의 상한**이라 한쪽만 조여도 다른 쪽은
            # 그대로다.
            timeout = float(getattr(self.cfg, 'fetch_timeout', 0.0) or 0.0)
            if timeout <= 0:
                timeout = max(60.0, expect_bytes / (1 << 20) * 1.0)
            # **버퍼는 `LOCK` 을 잡은 뒤에 기다린다.**  순서가 중요하다 --
            # 잠그지 않은 채 기다리면 그동안 컨트롤러가 이 프레임을 덮어
            # **프레임을 잃는다.**  잠근 채 기다리면 컨트롤러는 다른 버퍼를
            # 쓰므로 **한 프레임만** 더 간다 -- 그 다음 경계부터는 엔진이 쓰던
            # 버퍼를 재사용해 **앞 장을 덮는다** (DevNote 10.4, `--hold 20`).
            # 우리 프레임은 지켜지지만, 이 대기가 프레임 주기(13.27초)를 넘으면
            # 다음 장을 잃는다.  ⏳ 이 대기에는 상한이 없다 -- `fetch_timeout`
            # 은 전송만 잰다.  호스트 버퍼 고갈은 `buf_waits` 경고로 드러나고,
            # 상한을 둘지는 첫 운용 실측 뒤 판단 (DevNote 9.15).
            buf = await self._take_buffer(expect_bytes)
            started = time.monotonic()
            try:
                data = await self._locked_thread(
                    self.link.fetch, fs.base, expect_bytes, timeout, None, buf)
            except BaseException:
                # 실패하면 곧바로 돌려준다 -- 안 그러면 링이 한 칸씩 줄어
                # **몇 번의 실패 뒤에 영구히 막힌다.**
                self.release_buffer(buf)
                raise

            # **fetch 뒤 재대조** (`[archon] recheck_after_fetch`, 2026-08-30).
            #
            # 앞의 대조는 fetch **직전 한 순간**만 본다.  fetch 자체가 수 초
            # 걸리므로(실측 3.2~3.5초, DevNote 10.4) **그 사이에 덮이는 창**은
            # 아무도 안 본다 -- 주기 13.27초에 경계가 걸릴 확률 ≈26% 다 (10.6) --
            # `lock_buffer=true` 면 그 창을 `LOCKn` 이 막지만, **끄면 막는 것이
            # 아무것도 없다.**  그래서 이 재대조가 `lock_buffer=false` 의 짝이다.
            #
            # 덮였으면 **받아 온 자료를 버린다.**  3~4초를 버리는 셈이지만, 그
            # 대안은 남의 노출 픽셀을 담은 raw 한 장을 **아무 경고 없이** 쓰는
            # 것이다 (헤더는 이 프레임의 것이라 나중에 봐도 못 가른다).
            if getattr(self.cfg, 'recheck_after_fetch', True):
                after_fields = await self.query('FRAME', timeout=T_FAST)
                after = parse.buffer_frame(after_fields, buf_n)
                # ⭐ **`WBUF` 의 이동이 `RBUF` 보다 강한 증거다** -- 상태 플래그가
                # 아니라 **엔진이 실제로 다른 버퍼를 썼다**는 거동이다.
                self.lock_wbuf_after = parse.lock_state(after_fields)[1]
                if after != fs.frame:
                    self.release_buffer(buf)
                    raise ArchonError(
                        '%s: fetch 하는 동안 버퍼 %d 가 프레임 %d 로 덮였다 '
                        '(내 프레임은 %d) -- 받아 온 %.1f MiB 를 버린다.  이 '
                        '자료는 두 노출이 섞여 있다.  lock_buffer=%s 이니 '
                        'true 로 두거나, write_delay·독출 시간과 버퍼 수를 '
                        '보라'
                        % (self.tag, buf_n, after, fs.frame,
                           expect_bytes / (1 << 20), lock), cmd='FETCH')
        finally:
            if lock:
                try:
                    await self.cmd('LOCK0', timeout=T_FAST)
                except (ArchonError, TimeoutError, OSError) as exc:
                    # **풀지 못하면 엔진은 버퍼 하나로 돈다** -- 다음 장이 앞 장을
                    # 덮는다 (DevNote 10.6).  크게 알린다.
                    log.error('%s: LOCK0(잠금 해제)에 실패했다 (%s) -- 잠금이 '
                              '남으면 엔진은 남은 버퍼 하나로 돌아 다음 장이 앞 '
                              '장을 덮는다 (DevNote 10.6).  다음 fetch 의 LOCKn 이 '
                              '잠금을 옮길 때까지 프레임을 잃을 수 있다',
                              self.tag, exc)
        # ⭐ 잠금 관측값을 **이미 있는 줄에 얹는다** -- 정상 취득에 새 줄을
        # 늘리지 않으면서 회귀 감시(FW 가 바뀌면 RBUF/WBUF 가 달라진다)에 필요한
        # 것이 매 프레임 남는다.  A/B 실험은 2026-09-01 종결 (DevNote 10.6).
        log.info('%s: FETCH %.1f MiB, %.1f초 (프레임 %d, buf %d, base 0x%08X) '
                 '[lock=%s RBUF=%d WBUF=%d%s]',
                 self.tag, expect_bytes / (1 << 20),
                 time.monotonic() - started, fs.frame, buf_n, fs.base,
                 lock, self.lock_rbuf, self.lock_wbuf,
                 '' if self.lock_wbuf_after < 0
                 else '->%d' % self.lock_wbuf_after)
        return data

    async def _take_buffer(self, nbytes: int) -> bytearray:
        """링에서 버퍼 하나를 빌린다.  비어 있으면 **기다린다**(역압).

        기다렸다는 사실을 세어 두는 것이 요점이다 -- `fetch_buffers` 가
        충분한지를 **실기가 답하게** 한다.  기다림이 길어지면 그동안 컨트롤러
        버퍼가 덮여 프레임을 잃으므로, 조용히 넘어가면 안 되는 신호다.
        """
        try:
            buf = self._bufpool.get_nowait()
        except asyncio.QueueEmpty:
            t0 = time.monotonic()
            buf = await self._bufpool.get()
            waited = time.monotonic() - t0
            self.buf_waits += 1
            self.buf_wait_s += waited
            log.warning('%s: 수신 버퍼가 없어 %.2f초 기다렸다 (누적 %d회 · '
                        '%.1f초) -- 저장이 밀리고 있다.  길어지면 컨트롤러 '
                        '버퍼가 덮여 프레임을 잃는다.  [archon] fetch_buffers '
                        '를 올릴 것', self.tag, waited,
                        self.buf_waits, self.buf_wait_s)
        # 크기가 다르면(기하 변경) 새로 잡는다 -- 재사용이 목적이지 강제가 아니다.
        if buf is None or len(buf) != nbytes:
            buf = bytearray(nbytes)
        return buf

    def release_buffer(self, buf) -> None:  # noqa: ANN001
        """버퍼를 링에 돌려준다.  **저장이 끝난 뒤** 부른다.

        ⚠️ fetch 성공 뒤에 이것을 안 부르면 링이 한 칸 줄고, 몇 프레임 뒤에
        **영구히 막힌다** -- `write_frame` 의 `finally` 가 그 자리다.
        """
        try:
            self._bufpool.put_nowait(buf)
        except asyncio.QueueFull:      # 있을 수 없지만 막지는 않는다
            log.debug('%s: 버퍼 링이 가득 차 하나를 버린다', self.tag)

    # -- 준비 -------------------------------------------------------------

    async def prepare(self) -> None:
        """첫 노출 앞에 한 번 -- 연결 · ACF · 전원 · `SYSTEM` 스냅샷.

        **멱등하다.**  시퀀서는 프레임마다 CCD 별로 `initialize()` 를 부르므로
        (컨트롤러 하나당 2회) 여기서 걸러 준다.  ACF 적용(`APPLYALL`)은 초
        단위가 걸려 프레임마다 되풀이할 수 없다.
        """
        if not self.link.connected:
            await self.connect()
        acf = self.cfg.acf.get(self.tag, '')
        if acf and not self.acf_applied:
            if self.cfg.apply_acf:
                await self.apply_acf(acf)
            else:
                # 적용은 건너뛰지만 **파싱은 한다** -- 줄 번호가 없으면
                # 파라미터를 못 바꾼다.  그리고 그 줄 번호가 컨트롤러 메모리와
                # 맞는지 대조한다(어긋나면 노출 시간이 조용히 안 바뀐다).
                # ⚠️ 이 대조는 **줄 대응**만 본다 -- 그 세션에서 APPLYALL 이
                # 됐는지는 못 가른다 (p.51, DevNote 10.2).  REBOOT 뒤라면 줄이
                # 맞아도 아래 `power_on()` 이 `?xx` 로 거부되고, 그 진단 문구가
                # 이 갈래를 가리킨다.
                self.parse_acf(acf)
                self.acf_applied = True
                slots = [self.cfg.param_intms_slot, self.cfg.param_exposures_slot]
                fslot = getattr(self.cfg, 'param_flush_slot', None)
                if fslot and fslot in self.config:
                    slots.append(fslot)
                bad = await self.verify_config_lines(tuple(slots))
                if bad:
                    raise ArchonError(
                        '%s: apply_acf=false 인데 설정 줄 대응이 어긋났다 (%s) '
                        '-- 같은 ACF 를 쓰거나 apply_acf=true 로 두라'
                        % (self.tag, ', '.join(bad)))
        # ⭐ CCD flush -- ACF 를 민 **뒤에** `FirstFlush` 한 줄만 쓴다 (apply_acf=false
        # 경로에서도 컨트롤러 메모리를 되읽어 판정하므로 앞 세션이 켜 둔 것을
        # 되돌린다).
        # ⛔ **science 전용이다** -- `IcgCfg` 에는 이 설정이 아예 없으므로
        # guide 는 이 자리를 지나지도 않는다 (운영자 확정 2026-09-04).
        # 종전에는 `getattr(..., False)` 로 guide 도 지나며 두 줄을 되읽었는데,
        # 그것은 필요 없는 왕복이고 *"guide 도 대상"* 으로 읽히는 자리였다.
        want_flush = getattr(self.cfg, 'ccdflush', None)
        if want_flush is not None:
            await self.set_first_flush(bool(want_flush))
        if not self.powered:
            await self.power_on()
        if not self.system:
            await self.refresh_system()
            self._log_module_map()

    def _log_module_map(self) -> None:
        """슬롯별 모듈 형을 한 번 찍는다 -- 규격 5.6.1절 자리 표의 실기 확인.

        ⚠️ **종전에는 "AD 모듈이 슬롯 5~8 인가" 로 판정했고 그것이 틀렸다**
        (2026-08-27).  실기 science 는 AD 계열이 5·8 둘뿐이라 **정상 구성에서
        경고가 났다.**  판정은 `parse.field_order_problems()` 로 옮겼다 --
        자리 표가 자리를 준 모듈과 실제 장착 모듈이 같은지를 본다.
        """
        mods = parse.module_types(self.system)
        if not mods:
            return
        shown = ', '.join(
            '%d:%s' % (s, parse.MODULE_TYPES.get(t, '?%d' % t))
            for s, t in sorted(mods.items()) if t)
        log.info('%s: 모듈 %s', self.tag, shown)
        # 비디오 모듈 위치는 **참고로만** 찍는다 -- 판정 근거가 아니다.
        ad = sorted(s for s, t in mods.items() if t in parse.AD_TYPES)
        log.info('%s: 비디오(AD 계열) 모듈 슬롯 %s', self.tag, ad or '없음')
        # ⛔ **대는 표를 골라 줘야 한다** -- `field_order_problems` 의 docstring
        # 이 이 오경보를 그대로 예언해 뒀는데(*"안 골라 주면 guide 실기 정상
        # 구성에서 extra [6,7] + missing [1,2,8,11] 이 거짓으로 뜬다"*) 여기서
        # 안 넘겨서 벤치 첫 전원 인가에 정확히 그것이 났다 (2026-09-08).
        # ⭐ 표는 백엔드가 꽂아 준다(`temp_fields`) -- science 층이 guide 패키지를
        # 수입하면 의존이 거꾸로 선다.
        section = '10.4절' if self.temp_fields else '5.6.1절'
        for note in parse.field_order_problems(self.system, self.temp_fields):
            log.warning('%s: 규격 %s 자리 표와 어긋난다 -- %s.  Cn_TEMP '
                        '자리가 밀릴 수 있으니 자리 표를 확인할 것',
                        self.tag, section, note)
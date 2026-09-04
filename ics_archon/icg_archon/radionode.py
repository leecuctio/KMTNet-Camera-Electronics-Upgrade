#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Radionode RN320-BTH 측정값 -- `HEBOX` · `FSATEMP`/`FSAHUM` 의 원천.

**장치는 LoRaWAN 이라 LAN 폴링이 불가하다** (RN320 은 IP 스택이 없다 --
LoRa 게이트웨이를 거쳐 Tapaculo365 클라우드로만 간다).  그래서 접근은
클라우드 **Open API 폴링**이고, endpoint 상세가 콘솔 로그인 뒤의
"OPENAPI 매뉴얼" 에만 있어 **URL·경로·인증 헤더 이름까지 ini 소관**이다
(`config.RadionodeCfg`).  조사 경위·대안(사설 LoRaWAN 서버)은 DevNote 9장.

백엔드 넷:

* `off`     -- 아무것도 안 한다 (전 키 결측 -> 헤더 sentinel).  **기본값**.
* `openapi` -- Tapaculo365 를 `poll_period` 마다 폴링한다.  ⛔ **인터넷이
  있어야 한다.**
* `sim`     -- **코드 상수** 고정값 (ini 로 못 바꾼다).  ⚠️ 그 값은
  `sim_values()` 로만 나가고 **헤더 경로로는 안 나간다** -- 상수가 실측처럼
  아카이브에 남으면 나중에 파일만 보고 가릴 수 없다 (규격 5.6·5.8 은 이
  3장을 실측 계통으로 규정한다).  배선 확인용이다.
* ⏳ `local_lns` -- 사설 LoRaWAN 서버(ChirpStack)에서 받는다.  **자리만 있고
  구현은 없다.**

⛔⛔ **인터넷이 끊기면 세 카드가 결측이고, 운영자는 그것을 받아들이지 않는다**
(2026-09-04 확정).  ⚠️ 그런데 지금 자료가 들어오는 길이 클라우드 하나뿐이라
**코드로는 못 막는다** -- `stale_after` 를 늘려 옛 값을 계속 싣는 것은 결측을
없애는 것이 아니라 **틀릴 수 있는 값으로 덮는 것**이라 규격 5.0절 sentinel 의
정신에 어긋난다.  ⭐ 실제로 막는 유일한 길이 `local_lns` 이고, 그것은 **운영자
액션 둘**(게이트웨이 관리 접근 · 장치 가입 키)이 선행이다 (DevNote 11.22).

**신선도가 값의 일부다.**  마지막 표본이 `stale_after` 보다 낡으면
`values()` 가 그 키를 **내지 않는다** -- 호출측(`rawhdr.thermal_header`)이
sentinel 을 채우고, "낡은 값이 새 값처럼" 실리는 길을 막는다 (진공 Alive
카운터와 같은 정신 -- `hk.py`).

의존성을 더하지 않는다 -- HTTP 는 표준 라이브러리(`urllib`)로, 호출은
`asyncio.to_thread` 로 이벤트 루프 밖에서.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import RadionodeCfg

log = logging.getLogger('icg_archon.radionode')

#: `openapi` 로 켜려면 **반드시 있어야 하는** ini 값 넷.  ⭐ 운영자가 콘솔의
#: "OPENAPI 매뉴얼" 에서 옮겨 적는 것이 이 넷이다 (README "Radionode 자격증명").
REQUIRED_KEYS = ('base_url', 'latest_path', 'api_key', 'api_secret')


class RadionodeError(Exception):
    """런타임 연결을 **거절하는** 이유.  부르는 쪽이 문구를 그대로 응답에 쓴다."""


# ---------------------------------------------------------------------------
# local_lns -- 게이트웨이 안의 네트워크 서버에서 **밀어 주는** uplink 를 받는다
# ---------------------------------------------------------------------------
#
# ⭐ **폴링이 아니라 수신이다.**  RAK7268CV2(WisGate Edge Lite 2)는 게이트웨이
# 안에 LoRaWAN 네트워크 서버(ChirpStack 계열)가 들어 있어서, 별도 서버를 세울
# 것 없이 그 NS 의 **HTTP integration** 이 장치가 올릴 때마다 우리에게 POST 한다.
#
# ⛔ **의존성을 더하지 않는다** (이 모듈의 원칙).  MQTT 를 쓰면 `paho-mqtt` 가
# 필요한데, HTTP 수신은 표준 라이브러리로 끝난다 -- 그래서 이 갈래를 골랐다.
# ⏳ 게이트웨이가 HTTP integration 을 안 내주고 MQTT 만 있으면 그때 최소 MQTT
# 클라이언트를 쓴다 (DevNote 11.23-(3)).
#
# ⚠️ **push 라서 신선도의 뜻이 달라진다** -- 폴링은 "우리가 안 물어봐서" 늦지만
# 수신은 **장치가 안 올려서** 늦는다.  `stale_after` 는 그대로 쓰되 그 값은
# 이제 장치의 SEND INTERVAL 을 재는 자다.


def _norm_eui(text: str) -> str:
    """DevEUI 를 **소문자 16진 16자**로 맞춘다.

    ⚠️ 같은 값이 세 모양으로 온다 -- ini 는 사람이 적어 `AC-1F-09-…` 처럼
    구분자가 섞이고, ChirpStack 은 판에 따라 **16진**(v4)이나 **base64**(v3
    protobuf-JSON)로 준다.  ⛔ 모양이 다르면 대응이 조용히 빗나가 *"uplink 는
    오는데 아무 장치에도 안 붙는"* 상태가 된다 -- 그래서 한 모양으로 접는다.
    """
    raw = (text or '').strip().replace('-', '').replace(':', '').replace(' ', '')
    if len(raw) == 16:
        try:
            int(raw, 16)
            return raw.lower()
        except ValueError:
            pass
    try:                                    # base64 8바이트
        blob = base64.b64decode(raw + '=' * (-len(raw) % 4), validate=True)
    except Exception:                       # noqa: BLE001
        return raw.lower()
    return blob.hex() if len(blob) == 8 else raw.lower()


def uplink_deveui(msg: dict) -> str:
    """uplink JSON 에서 DevEUI 를 뽑는다 (ChirpStack v3·v4 모양 둘 다)."""
    for path in (('deviceInfo', 'devEui'), ('deviceInfo', 'devEUI'),
                 ('devEUI',), ('devEui',), ('DevEUI',), ('dev_eui',)):
        cur: object = msg
        for key in path:
            cur = cur.get(key) if isinstance(cur, dict) else None
        if isinstance(cur, str) and cur:
            return _norm_eui(cur)
    return ''


def uplink_object(msg: dict):  # noqa: ANN201
    """복호·해석된 측정값 dict.  코덱이 없으면 `None`.

    ⭐ **해석은 게이트웨이의 NS 가 한다** -- 공식 코덱(`rn320bth.js`)을 거기
    올려 두면 uplink JSON 에 `object` 로 들어온다.  ⛔ 코덱이 없으면 `data`
    (base64 원문)만 오는데 그것은 **우리가 못 푼다**(AES 복호는 NS 가 이미
    했지만 바이트 배치는 제조사 코덱이 안다) -- 그때는 결측으로 두고 **이유를
    적는다.**  추측으로 바이트를 자르지 않는다.
    """
    obj = msg.get('object')
    if isinstance(obj, dict):
        return obj
    for key in ('objectJSON', 'object_json'):
        raw = msg.get(key)
        if isinstance(raw, str) and raw.strip():
            try:
                got = json.loads(raw)
            except ValueError:
                continue
            if isinstance(got, dict):
                return got
    return None


#: 받아들일 요청 본문의 상한 [B].  uplink 는 킬로바이트 단위다.
MAX_BODY = 1 << 20


def _make_handler(client):  # noqa: ANN001, ANN202
    """수신 핸들러 -- `client` 를 닫아 넣는다 (클래스 변수 공유를 피한다)."""

    class Handler(BaseHTTPRequestHandler):
        # ⚠️ 조용한 프로토콜이다 -- 게이트웨이가 재시도하지 않을 수 있으므로
        # 실패해도 200 을 주되 **이유를 로그와 last_err 에 남긴다.**  4xx 를
        # 주면 NS 가 큐에 쌓아 두고 되풀이 보내는 판이 있다.
        protocol_version = 'HTTP/1.1'

        def log_message(self, fmt, *args):  # noqa: ANN001, ANN201, A002
            # 기본 구현이 stderr 로 직접 찍는다 -- 우리 로거로 돌린다.
            log.debug('lns http: ' + fmt, *args)

        def _reply(self, code: int, body: str = 'ok') -> None:
            blob = body.encode('ascii', 'replace')
            self.send_response(code)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)

        def _body(self) -> bytes:
            """요청 본문을 **끝까지** 읽는다.

            ⛔⛔ **거절할 때도 먼저 읽어야 한다.**  안 읽고 응답하면 보내는
            쪽이 아직 본문을 밀고 있는 중이라 연결이 리셋되고, 게이트웨이
            쪽에는 *"전송 실패"* 로 남아 되풀이 보내거나 integration 을
            죽은 것으로 표시한다.  ⚠️ 시험에서 `ConnectionAbortedError` 로
            드러난 자리다 (401 을 주는 갈래).
            """
            try:
                length = int(self.headers.get('Content-Length') or 0)
            except ValueError:
                return b''
            if length <= 0:
                return b''
            if length > MAX_BODY:
                # 우리 uplink 는 킬로바이트 단위다 -- 이만한 것은 우리 것이
                # 아니므로 읽지 않고 연결을 닫는다.
                self.close_connection = True
                log.warning('lns 요청 본문이 %d 바이트다 -- 버린다', length)
                return b''
            return self.rfile.read(length)

        def do_POST(self) -> None:  # noqa: N802
            cfg = client.cfg
            raw = self._body()              # ⭐ 판정보다 **먼저** 읽는다
            path = self.path.split('?', 1)[0]
            if cfg.lns_path and path != cfg.lns_path:
                self._reply(404, 'no')
                return
            if cfg.lns_token and self.headers.get('X-Auth-Token') != \
                    cfg.lns_token:
                # ⚠️ LAN 안이라도 **누가 보냈는지**는 가른다 -- 틀린 값이
                # 헤더로 들어가는 길이다.
                log.warning('lns uplink 를 토큰 불일치로 버린다 (%s)',
                            self.client_address[0])
                self._reply(401, 'no')
                return
            try:
                msg = json.loads(raw.decode('utf-8'))
            except Exception as exc:        # noqa: BLE001
                log.warning('lns uplink 를 못 읽었다 -- %s', exc)
                self._reply(200, 'bad')
                return
            client.take_uplink(msg if isinstance(msg, dict) else {})
            self._reply(200)

        def do_GET(self) -> None:  # noqa: N802
            # 게이트웨이 UI 에서 "테스트" 를 누르면 GET 이 오는 판이 있다.
            self._reply(200, 'icg_archon lns listener')

    return Handler


class UplinkListener:
    """게이트웨이 NS 의 HTTP integration 을 받는 최소 수신기.

    ⭐ 스레드에서 돈다 -- 소켓 대기는 블로킹이고, 이 프로세스의 이벤트 루프는
    OBSAgent 시간 창에 묶여 있어 멈출 수 없다 (`SMC_CLAUDE` 규칙 6).
    """

    def __init__(self, client) -> None:  # noqa: ANN001
        self.client = client
        self.server = None
        self.thread: threading.Thread | None = None

    @property
    def alive(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    @property
    def address(self) -> str:
        if self.server is None:
            return ''
        host, port = self.server.server_address[:2]
        return '%s:%d' % (host, port)

    def start(self) -> str:
        host, _, port = (self.client.cfg.lns_bind or '').rpartition(':')
        self.server = ThreadingHTTPServer(
            (host or '0.0.0.0', int(port or 0)), _make_handler(self.client))
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       name='icg-lns', daemon=True)
        self.thread.start()
        return self.address

    def stop(self) -> None:
        """⚠️ **블로킹이다** -- 부르는 쪽이 `to_thread` 로 감싼다."""
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.thread is not None:
            self.thread.join(timeout=5.0)
            self.thread = None


class RadionodeClient:
    """장치 두 대(HE box · FSA)의 최신 표본을 들고 있는 폴러."""

    def __init__(self, cfg: RadionodeCfg) -> None:
        self.cfg = cfg
        #: key(소문자) -> (값, 표본시각 monotonic).  `values()` 가 신선도를
        #: 대조한다.
        self._latest: dict[str, tuple[object, float]] = {}
        #: 장치 별칭 -> 폴링 활성 (RADIONODE DISCONNECT 명령이 끈다).
        self.enabled: dict[str, bool] = {
            d.alias: True for d in cfg.devices}
        #: 장치 별칭 -> 마지막 성공/실패 기록 (RADIONODE STATUS 가 보여 준다).
        self.last_ok: dict[str, float] = {}
        self.last_err: dict[str, str] = {}
        #: 별칭 -> 마지막 **시도**의 결과 (`'ok'`/`'err'`) -- 성공 이력이
        #: 실패를 가리지 않게 하려는 자리다.
        self._last_try: dict[str, str] = {}
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        #: 주기 루프와 `RECONNECT` 가 같은 API 를 이중으로 치지 않게.
        self._poll_lock = asyncio.Lock()
        #: 앱의 태스크 생성자 -- `start()` 가 넘겨준 것을 들고 있다가
        #: 런타임 `CONNECT` 가 루프를 **다시 띄울 때** 쓴다.
        self._spawn = None
        #: ⚠️ `_latest` 를 **두 곳에서** 쓴다 -- `openapi` 는 이벤트 루프에서,
        #: `local_lns` 는 **수신 스레드**에서.  읽는 쪽이 dict 를 훑으므로
        #: 잠금 없이는 "iteration 중 크기 변경" 이 난다.
        self._lock = threading.Lock()
        #: `local_lns` 수신기 (게이트웨이 NS 가 밀어 주는 uplink).
        self._listener = UplinkListener(self)
        #: DevEUI(정규형) -> 장치.  ⭐ ini 가 정한 대응이고 **런타임에 안 바뀐다**.
        self._by_eui = {_norm_eui(d.deveui): d
                        for d in cfg.devices if getattr(d, 'deveui', '')}
        #: 등록 안 된 DevEUI 로 온 uplink -- `STATUS` 가 보여 준다 (센서를 더
        #: 달았는데 ini 에 안 적은 것이 가장 흔하다).
        self._unknown_eui: dict[str, int] = {}

    # -- 소비 --------------------------------------------------------------

    def values_with_time(self) -> dict[str, tuple[object, float]]:
        """`key -> (값, 표본시각 epoch)` -- 신선한 것만.

        ⭐ **표본시각을 값과 함께 낸다.**  호출측이 `now` 로 다시 도장을
        찍으면 "낡은 값이 갓 잰 값" 이 되어 `hk_stale_after` 같은 하류
        판정이 통째로 무력해진다 (DevNote 9.6 이 막겠다고 한 그 경로다).
        `monotonic` 은 프로세스 밖에서 못 읽으므로 epoch 로 환산해 낸다.

        ⚠️ **`sim` 백엔드는 아무것도 내지 않는다.**  고정 상수를 실측처럼
        헤더에 실으면 아카이브에 들어간 뒤 파일만 보고 잰 값인지 가릴 수
        없다 -- 규격 5.6·5.8 은 이 3장의 출처를 실측 계통(`Radionode`)으로
        규정하고, 결측은 5.0절 sentinel 이 이미 규정해 둔 정직한 상태다.
        시뮬 값이 필요하면 `sim_values()` 를 명시적으로 부를 것.
        """
        if not self.publishing:
            return {}
        now_m, now_e = time.monotonic(), time.time()
        out: dict[str, tuple[object, float]] = {}
        with self._lock:                    # 수신 스레드가 쓰는 중일 수 있다
            items = list(self._latest.items())
        for key, (val, when) in items:
            age = now_m - when
            if age <= self.cfg.stale_after:
                out[key] = (val, now_e - age)
        return out

    def values(self) -> dict[str, object]:
        """신선한 키만 (값만) -- 표본시각이 필요하면 `values_with_time()`."""
        return {k: v for k, (v, _t) in self.values_with_time().items()}

    def sim_values(self) -> dict[str, object]:
        """`sim` 백엔드의 고정값 -- **헤더 경로로 내보내지 않는다.**

        시험·벤치에서 배선을 확인할 때만 쓴다 (`HK` 명령 등).
        """
        return dict(self.cfg.sim_values) if self.cfg.backend == 'sim' else {}

    @property
    def publishing(self) -> bool:
        """지금 **헤더로 값을 낼 자격**이 있나 -- 백엔드마다 뜻이 다르다.

        * `openapi` -- 백엔드가 그것이면 낸다 (`DISCONNECT` 가 `off` 로 되돌린다).
        * `local_lns` -- **수신기가 살아 있어야** 낸다.  ⭐ 여기서 백엔드를
          `off` 로 되돌리지 않는 것이 의도다: 되돌리면 다음 `CONNECT` 가
          **클라우드로 간다** -- 인터넷을 안 쓰기로 한 사이트에서 그것은 사고다.
        * 그 밖(`off`/`sim`) -- 안 낸다.
        """
        if self.cfg.backend == 'openapi':
            return True
        if self.cfg.backend == 'local_lns':
            return self._listener.alive
        return False

    @property
    def listening(self) -> bool:
        """`local_lns` 수신기가 떠 있나."""
        return self._listener.alive

    @property
    def polling(self) -> bool:
        """주기 루프가 **실제로 돌고 있나** (백엔드 설정과 별개다).

        ⚠️ 둘을 헷갈리지 말 것 -- `backend=openapi` 인데 루프가 죽어 있을 수
        있고(태스크 예외), 그때 `STATUS` 가 백엔드만 보이면 *"켜져 있다"* 로
        읽힌다.
        """
        return self._task is not None and not self._task.done()

    def missing_credentials(self) -> list[str]:
        """`openapi` 로 켜기에 **모자란 ini 값**들.  없으면 빈 목록."""
        return [k for k in REQUIRED_KEYS if not getattr(self.cfg, k, '')]

    def status_text(self) -> str:
        """`RADIONODE STATUS` 응답 본문 (ASCII 한 줄).

        ⭐ **백엔드·루프·자격증명·장치**를 함께 보인다 -- 운영자가 물어보는
        것은 *"지금 자료가 들어오고 있나, 아니면 왜 안 들어오나"* 하나인데,
        종전에는 `off` 이면 `Backend=off` 한 마디로 끝나 **무엇이 모자라서
        못 켜는지**가 안 보였다.
        """
        parts = ['Backend=%s' % self.cfg.backend]
        if self.cfg.backend == 'local_lns':
            # ⭐ push 라 "폴링" 이 아니라 **수신** 이다 -- 낱말을 갈아 준다.
            parts.append('Listening=%s' % (
                self._listener.address if self.listening else 'no'))
            parts.append('Path=%s' % self.cfg.lns_path)
            no_eui = [d.alias for d in self.cfg.devices if not d.deveui]
            if no_eui:
                parts.append('NoDevEUI=%s' % ','.join(no_eui))
            if self._unknown_eui:
                # ⛔ 등록 안 된 DevEUI -- 센서를 더 달고 ini 에 안 적은 것이
                # 가장 흔하다.  수를 보여 주면 그 자리에서 안다.
                parts.append('UnknownEUI=%s' % ','.join(
                    '%s(%d)' % (eui or '?', n)
                    for eui, n in sorted(self._unknown_eui.items())))
        else:
            parts.append('Polling=%s' % ('yes' if self.polling else 'no'))
            if self.cfg.backend != 'openapi':
                miss = self.missing_credentials()
                parts.append('Credentials=%s' % (
                    ','.join(miss) + ' missing' if miss else 'ok'))
        now = time.monotonic()
        for dev in self.cfg.devices:
            if not self.publishing:
                # ⚠️ 표본은 남아 있어도 **헤더로는 안 나간다** (`values()` 가
                # 백엔드로 먼저 거른다) -- 그 사실을 적는다.  안 적으면
                # `STATUS` 에 값이 보이는데 헤더는 sentinel 인 상태가
                # 설명되지 않는다.
                ok = self.last_ok.get(dev.alias)
                state = ('last ok %.0fs ago, not published' % (now - ok)
                         if ok is not None else 'no sample')
            elif not self.enabled.get(dev.alias, False):
                state = 'disabled'
            else:
                # ⚠️ **마지막 시도 기준으로 보인다** -- 성공 이력만 보이면
                # API 키가 만료돼도 화면에는 계속 'ok …' 만 뜬다
                # (2026-08-31 교차검토).
                ok = self.last_ok.get(dev.alias)
                err = self.last_err.get(dev.alias)
                if ok is None and err is None:
                    state = 'no sample yet'
                elif err and (ok is None or self._last_try.get(dev.alias)
                              == 'err'):
                    state = ('err: %s' % err if ok is None else
                             'ok %.0fs ago / err: %s' % (now - ok, err))
                else:
                    state = 'ok %.0fs ago' % (now - ok)
            parts.append('%s=%s' % (dev.alias, state))
        return ' '.join(parts)

    # -- 제어 (RADIONODE 명령) ----------------------------------------------

    def _start_listener(self) -> str:
        """`local_lns` 수신기를 띄우고 응답 문구를 돌려준다."""
        if not self._by_eui:
            # ⛔ DevEUI 대응이 하나도 없으면 uplink 가 와도 **전부 버려진다** --
            # 떠 있는데 아무것도 안 들어오는 상태를 만들지 않는다.
            raise RadionodeError(
                'No device has a deveui -- every uplink would be dropped; '
                'copy the DevEUIs from the gateway network server '
                '(see INSTALL 7.4)')
        try:
            addr = self._listener.start()
        except OSError as exc:
            raise RadionodeError('Cannot listen on %r -- %s'
                                 % (self.cfg.lns_bind or '(any)', exc)) from exc
        log.info('lns 수신기 %s%s -- 게이트웨이 integration 이 여기로 POST 한다 '
                 '(장치 %d)', addr, self.cfg.lns_path, len(self._by_eui))
        return ('Listening=%s Path=%s Devices=%d (push from the gateway '
                'network server)' % (addr, self.cfg.lns_path, len(self._by_eui)))

    def connect(self) -> str:
        """런타임에 폴링을 켠다 -- `off` → `openapi` + 루프 기동.

        ⭐ **운영자 지시의 "connect 하면 자동으로 주기적으로 받아온다"** 가
        이 함수다.  종전에는 `start()` 가 기동 때 `backend` 를 한 번 보고
        루프를 안 띄우면 끝이라, **`off` 로 뜬 프로세스를 런타임에 켤 길이
        없었다** (DevNote 11.15-(6)).

        ⛔ **자격증명이 모자라면 켜지 않는다.**  켜 놓고 실패를 반복하면
        주기마다 경고만 쌓이고 헤더는 그대로 sentinel 인데, 운영자는
        *"연결했다"* 고 믿는다 -- 무엇이 없는지 이름을 대고 거절한다.

        ⛔ **`sim` 에서는 못 켠다.**  sim 값은 헤더로 안 나가는 배선 확인용
        이고(`values_with_time` 주석), 런타임에 `sim`→`openapi` 로 올리면
        ini 가 말하는 것과 실제가 갈린다 -- ini 를 고치고 다시 띄울 일이다.

        ⚠️ **ini 를 고치지 않는다** -- 재기동하면 ini 값으로 돌아간다.
        상시로 켜 두려면 `[radionode] backend = openapi` 를 적어야 하고,
        응답이 그 사실을 말한다.  (`EXPENABLE` 과 달리 지속시키지 않는 것이
        의도다: 자격증명이 ini 에 있어야 켜지는데, 그 상태면 `backend` 도
        거기 적는 것이 정본이다.)
        """
        if self.cfg.backend == 'sim':
            raise RadionodeError(
                'Backend is sim -- fixed values, nothing to connect (edit '
                '[radionode] backend in the ini to use openapi)')
        if self.cfg.backend == 'local_lns':
            # ⭐ 여기서는 **수신기를 띄운다** -- 클라우드로 올리지 않는다.
            # 올려 버리면 *"인터넷을 안 쓰기로 한 사이트"* 가 조용히 바깥을
            # 치게 된다 (그 회귀를 시험이 못박고 있다).
            if self.listening:
                return 'Already listening on %s' % self._listener.address
            return self._start_listener()
        miss = self.missing_credentials()
        if miss:
            raise RadionodeError(
                'Missing ini values: %s -- copy them from the Tapaculo365 '
                'console ("OPENAPI manual")' % ','.join(miss))
        if self._spawn is None:
            raise RadionodeError('Poller is not started yet')
        was = self.cfg.backend
        self.cfg.backend = 'openapi'
        if not self.polling:
            self._stop.clear()
            self._task = self._spawn(self._run())
            log.info('radionode 폴링을 런타임에 켰다 (%s -> openapi, 주기 '
                     '%.0fs, 장치 %d) -- ⚠️ ini 는 안 고쳤다', was,
                     self.cfg.poll_period, len(self.cfg.devices))
            return ('Polling=on Period=%.0fs Devices=%d (runtime only -- the '
                    'ini still says backend=%s)'
                    % (self.cfg.poll_period, len(self.cfg.devices), was))
        return 'Already polling'

    async def disconnect(self) -> str:
        """런타임에 폴링을 끈다 -- 루프 정지 + `backend` 를 `off` 로.

        ⭐ **표본을 지우지는 않는다** -- 그런데 `values_with_time()` 이
        백엔드로 먼저 거르므로 **헤더에는 곧바로 sentinel** 이 실린다.
        그것이 `off` 의 뜻이고(ini: *"아무것도 안 한다 -- 전 키 결측"*),
        *"끊었는데 10분(`stale_after`)간 옛 값이 나가는"* 상태보다 정직하다.

        ⭐ 캐시를 남기는 것은 **다시 켰을 때를 위해서**다.  되켜면 옛 표본이
        곧바로 다시 보이는데, `values_with_time()` 이 **표본시각을 함께**
        내므로 하류(`HKSTALE`·헤더 나이)가 낡은 것을 낡은 것으로 판정한다 --
        갓 잰 값으로 둔갑하지 않는다.
        """
        if self.cfg.backend == 'local_lns':
            if not self.listening:
                return 'Not listening'
            # ⚠️ `shutdown()` 은 수신 루프가 빠질 때까지 **블로킹**이다.
            await asyncio.to_thread(self._listener.stop)
            # ⭐ **백엔드는 그대로 둔다** -- `off` 로 되돌리면 다음 `CONNECT` 가
            # 클라우드로 간다.  공개 여부는 `publishing` 이 수신기 생사로
            # 판정하므로, 이것만으로 세 카드는 곧바로 sentinel 이다.
            log.info('lns 수신기를 껐다 -- HEBOX/FSATEMP/FSAHUM 는 이제 '
                     'sentinel 이다 (백엔드는 local_lns 그대로)')
            return ('Listening=off (HEBOX/FSATEMP/FSAHUM go to sentinel; '
                    'backend stays local_lns)')
        if self.cfg.backend != 'openapi':
            return 'Not connected (backend=%s)' % self.cfg.backend
        await self.stop()
        self.cfg.backend = 'off'
        log.info('radionode 폴링을 런타임에 껐다 -- 헤더의 HEBOX/FSATEMP/'
                 'FSAHUM 는 이제 sentinel 이다')
        return 'Polling=off (HEBOX/FSATEMP/FSAHUM go to sentinel)'


    def set_enabled(self, alias: str, on: bool) -> bool:
        if alias not in self.enabled:
            return False
        self.enabled[alias] = on
        if not on:
            # 끄면서 그 장치의 키를 물린다 -- 낡은 값이 남는 것보다 결측이
            # 정직하다.
            for dev in self.cfg.devices:
                if dev.alias == alias:
                    for k in dev.keys:
                        self._latest.pop(k, None)
        return True

    async def poll_now(self) -> None:
        """`RADIONODE RECONNECT` -- 주기를 기다리지 않고 즉시 한 바퀴."""
        await self._poll_all()

    # -- 폴링 루프 -----------------------------------------------------------

    def start(self, spawn) -> None:  # noqa: ANN001
        # ⭐ **백엔드와 무관하게 먼저 보관한다** -- `off` 로 떠도 런타임
        # `RADIONODE CONNECT` 가 이 자리를 써서 루프를 띄운다.
        self._spawn = spawn
        if self.cfg.backend == 'local_lns':
            try:
                log.info('%s', self._start_listener())
            except RadionodeError as exc:
                # ⚠️ 기동을 세우지 않는다 -- 나머지 HK(RTD·진공·AUX)는 돌아야
                # 한다.  대신 크게 남기고 `STATUS` 가 계속 보여 준다.
                log.warning('lns 수신기를 못 띄웠다 -- %s.  HEBOX/FSATEMP/'
                            'FSAHUM 는 sentinel 이다', exc)
            return
        if self.cfg.backend != 'openapi':
            log.info('radionode 백엔드 %s -- 폴링 루프를 띄우지 않는다',
                     self.cfg.backend)
            return
        self._stop.clear()
        self._task = spawn(self._run())

    async def stop(self) -> None:
        self._stop.set()
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
        if self._listener.alive:            # ⚠️ 블로킹이라 스레드로
            await asyncio.to_thread(self._listener.stop)

    async def _run(self) -> None:
        # 주기 오차가 누적되지 않게 다음 시각을 절대값으로 잡는다 --
        # 밀린 바퀴를 몰아 돌지는 않는다 (monitor.py 와 같은 규칙).
        next_at = time.monotonic()
        while not self._stop.is_set():
            await self._poll_all()
            next_at = max(next_at + self.cfg.poll_period, time.monotonic())
            try:
                await asyncio.wait_for(self._stop.wait(),
                                       timeout=next_at - time.monotonic())
            except asyncio.TimeoutError:
                pass

    async def _poll_all(self) -> None:
        if self.cfg.backend != 'openapi':
            return                      # 폴러가 없는 백엔드 -- 칠 곳이 없다
        if self._poll_lock.locked():
            # 주기 루프가 도는 중에 `RECONNECT` 가 겹쳤다 -- 같은 API 를
            # 두 번 치지 않는다 (쿼터가 분 단위다).
            log.info('radionode 폴링이 이미 진행 중이라 건너뛴다')
            return
        async with self._poll_lock:
            for dev in self.cfg.devices:
                if not self.enabled.get(dev.alias, False):
                    continue
                try:
                    sample = await asyncio.to_thread(self._fetch_latest,
                                                     dev.mac)
                except Exception as exc:  # noqa: BLE001 -- 폴링 실패가 취득을 못 죽인다
                    self.last_err[dev.alias] = (
                        '%s: %s' % (type(exc).__name__, exc))[:120]
                    self._last_try[dev.alias] = 'err'
                    log.warning('radionode %s 폴링 실패 -- %s (헤더는 sentinel '
                                '로 간다)', dev.alias, exc)
                    continue
                self._store(dev, sample)
                self.last_ok[dev.alias] = time.monotonic()
                self._last_try[dev.alias] = 'ok'

    # -- HTTP --------------------------------------------------------------

    def _fetch_latest(self, mac: str) -> dict:
        """장치 하나의 최신 표본 -- **블로킹**, `to_thread` 로만 부른다.

        응답 JSON 의 모양이 계정 매뉴얼에 달려 있어 **관대하게 판다** --
        온도/습도로 읽을 수 있는 첫 필드 짝을 취한다 (`_pick`).  실기 응답을
        받으면 그 모양을 여기 주석으로 못박을 것 (PROVISIONAL).
        """
        url = self.cfg.base_url.rstrip('/') + \
            self.cfg.latest_path.format(mac=mac)
        req = urllib.request.Request(url, headers={
            self.cfg.key_header: self.cfg.api_key,
            self.cfg.secret_header: self.cfg.api_secret,
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=self.cfg.timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))

    @staticmethod
    def _pick(obj: object, names: tuple[str, ...]) -> object | None:
        """중첩 dict/list 에서 이름 후보의 첫 수치를 찾는다."""
        stack = [obj]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                for name in names:
                    if name in cur:
                        try:
                            return float(cur[name])
                        except (TypeError, ValueError):
                            pass
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
        return None

    def take_uplink(self, msg: dict) -> None:
        """게이트웨이 NS 가 밀어 준 uplink 하나.  ⚠️ **수신 스레드에서** 불린다.

        ⛔ 모르는 DevEUI 는 **버리되 센다** -- 센서를 더 달고 ini 에 안 적은
        것이 가장 흔한 실수인데, 그냥 버리면 *"올리는데 안 들어온다"* 가
        원인 없이 남는다.  `STATUS` 가 그 수를 보여 준다.
        """
        eui = uplink_deveui(msg)
        dev = self._by_eui.get(eui)
        if dev is None:
            self._unknown_eui[eui] = self._unknown_eui.get(eui, 0) + 1
            if self._unknown_eui[eui] == 1:     # 첫 번만 크게
                log.warning('lns uplink 의 DevEUI %s 가 ini 에 없다 -- 버린다.  '
                            '[radionode.<별칭>] deveui 를 적을 것', eui or '(없음)')
            return
        if not self.enabled.get(dev.alias, True):
            return                              # RADIONODE DISABLE 된 장치
        obj = uplink_object(msg)
        if obj is None:
            self.last_err[dev.alias] = 'no decoded object (codec on the NS?)'
            self._last_try[dev.alias] = 'err'
            log.warning('lns uplink %s 에 해석된 값이 없다 -- 게이트웨이 NS 에 '
                        '코덱(rn320bth.js)이 올라가 있는지 볼 것.  ⛔ 원문 '
                        'base64 를 우리가 짐작으로 자르지 않는다', dev.alias)
            return
        self._store(dev, obj)
        self.last_ok[dev.alias] = time.monotonic()
        self._last_try[dev.alias] = 'ok'

    def _store(self, dev, sample: dict) -> None:  # noqa: ANN001
        now = time.monotonic()
        temp = self._pick(sample, ('temperature', 'temp', 'ch1', 'value1'))
        hum = self._pick(sample, ('humidity', 'hum', 'ch2', 'value2'))
        got = []
        with self._lock:                    # ⚠️ 수신 스레드에서도 불린다
            for key in dev.keys:
                val = hum if key.endswith('hum') else temp
                if val is None:
                    continue
                self._latest[key] = (val, now)
                got.append(key)
        if not got:
            self.last_err[dev.alias] = 'no usable fields in response'
            log.warning('radionode %s 응답에서 온도/습도를 못 찾았다 -- '
                        '응답 키: %s', dev.alias,
                        ', '.join(list(sample)[:8]) if isinstance(sample, dict)
                        else type(sample).__name__)

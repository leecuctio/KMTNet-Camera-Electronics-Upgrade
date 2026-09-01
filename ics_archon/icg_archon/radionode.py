#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Radionode RN320-BTH 측정값 -- `HEBOX` · `FSATEMP`/`FSAHUM` 의 원천.

**장치는 LoRaWAN 이라 LAN 폴링이 불가하다** (RN320 은 IP 스택이 없다 --
LoRa 게이트웨이를 거쳐 Tapaculo365 클라우드로만 간다).  그래서 접근은
클라우드 **Open API 폴링**이고, endpoint 상세가 콘솔 로그인 뒤의
"OPENAPI 매뉴얼" 에만 있어 **URL·경로·인증 헤더 이름까지 ini 소관**이다
(`config.RadionodeCfg`).  조사 경위·대안(사설 LoRaWAN 서버)은 DevNote 9장.

백엔드 셋:

* `off`     -- 아무것도 안 한다 (전 키 결측 -> 헤더 sentinel).  **기본값**.
* `openapi` -- Tapaculo365 를 `poll_period` 마다 폴링한다.
* `sim`     -- **코드 상수** 고정값 (ini 로 못 바꾼다).  ⚠️ 그 값은
  `sim_values()` 로만 나가고 **헤더 경로로는 안 나간다** -- 상수가 실측처럼
  아카이브에 남으면 나중에 파일만 보고 가릴 수 없다 (규격 5.6·5.8 은 이
  3장을 실측 계통으로 규정한다).  배선 확인용이다.

**신선도가 값의 일부다.**  마지막 표본이 `stale_after` 보다 낡으면
`values()` 가 그 키를 **내지 않는다** -- 호출측(`rawhdr.thermal_header`)이
sentinel 을 채우고, "낡은 값이 새 값처럼" 실리는 길을 막는다 (진공 Alive
카운터와 같은 정신 -- `hk.py`).

의존성을 더하지 않는다 -- HTTP 는 표준 라이브러리(`urllib`)로, 호출은
`asyncio.to_thread` 로 이벤트 루프 밖에서.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.error
import urllib.request

from .config import RadionodeCfg

log = logging.getLogger('icg_archon.radionode')


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
        if self.cfg.backend != 'openapi':
            return {}
        now_m, now_e = time.monotonic(), time.time()
        out: dict[str, tuple[object, float]] = {}
        for key, (val, when) in self._latest.items():
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

    def status_text(self) -> str:
        """`RADIONODE STATUS` 응답 본문 (ASCII 한 줄)."""
        if self.cfg.backend != 'openapi':
            return 'Backend=%s' % self.cfg.backend
        now = time.monotonic()
        parts = []
        for dev in self.cfg.devices:
            if not self.enabled.get(dev.alias, False):
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
        return 'Backend=openapi ' + ' '.join(parts)

    # -- 제어 (RADIONODE 명령) ----------------------------------------------

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

    def _store(self, dev, sample: dict) -> None:  # noqa: ANN001
        now = time.monotonic()
        temp = self._pick(sample, ('temperature', 'temp', 'ch1', 'value1'))
        hum = self._pick(sample, ('humidity', 'hum', 'ch2', 'value2'))
        got = []
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

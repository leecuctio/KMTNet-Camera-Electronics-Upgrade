#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""진공 이온게이지(MKS 356 Micro-Ion Plus) 켜기/끄기 -- `VACGAUGE` 의 살림집.

**왜 끄나.**  ⭐ *"진공게이지의 필라멘트가 science 영상 자료에 영향을 끼쳐"*
(운영자 2026-09-04).  즉 게이지 Off 는 예외 상황이 아니라 **science 노출 중의
평상 상태**이고, 끄는 명령은 **ICS 가 노출 전에 ICG 로 보낸다**(운영자).
따라서 이 명령은 콘솔 전용이 아니라 **원격에서 들어온다** -- 응답이 필요하다.

끄는 길 셋 (DevNote 11.19 · MKS 매뉴얼 p.31 · Archon 매뉴얼 p.62)
---------------------------------------------------------------
MKS 매뉴얼 p.31 이 정본이다 -- *"You can also install a switch between pins 1
and 5 on the 15-pin … connector … **Pin 1 must be grounded to pin 5 to enable
the Micro-Ion gauge to operate**. A process relay or switch can be used …
To turn OFF the Micro-Ion gauge, the process relay will **open** the switch."*
⭐ **그 스위치가 바로 ACF 의 `MOD10\\DIO_LABEL3=IONEN` 이다.**

| 갈래 | 무엇을 쓰나 | 범위 | 상태 |
|---|---|---|---|
| **`diopower`** (기본) | `MOD10\\DIO_POWER` 1→0 | **8라인 전부**의 버퍼 전원 | ✅ **실측 확인** (운영자 2026-09-04).  선임이 쓰던 길과 같다 (`…_goff_….acf` 가 정확히 이 한 줄만 다르다) |
| `ionen` | `MOD10\\DIO_SOURCE3` 1→0 | IONEN **한 라인**만 HIGH→LOW | ⏳ **미검증**.  Archon p.62 `DIO_SOURCEi` 0=low·1=high·2=timing·3=VCPU |

⭐ **실측이 갈래를 정했다** -- 운영자가 `MOD10\\DIO_POWER=1/0` 으로 On/Off 가
되는 것을 확인했다.  ⚠️ 그 대신 `diopower` 는 시리얼 3선(`ION_DE`/`ION_DI`/
`ION_RO`)의 버퍼 전원도 끊으므로 **압력 읽기까지 죽는다** -- 끈 동안에는 값이
아예 안 온다.  ⭐ 그것이 오히려 아래 Conductron 함정을 **비껴간다**(올 값이
없으니 틀린 값도 없다).  그래도 sentinel 규칙은 그대로 둔다: `ionen` 으로
바꾸면 함정이 되살아나고, *"끈 동안 DEWPRES 는 sentinel"* 은 갈래와 무관한
운영자 확정이다.

⛔⛔ **끈 동안 `DEWPRES` 를 실으면 안 된다** (이 모듈이 존재하는 진짜 이유)
------------------------------------------------------------------------
MKS 356 은 **이온게이지 + Conductron 열손실 센서** 복합이고, 이온게이지를 끄면
모듈이 **Conductron 값을 계속 내보낸다** (매뉴얼 p.31: *"the optional numeric
display … indicates pressure as measured by the Conductron sensor"*).  그런데
Conductron 은 고진공에서 바닥값을 내고, ⛔ **그 바닥값이 `rawhdr` 의 인정 범위
`[1e-8, 1e+3]` 를 그냥 통과한다** -- 즉 실제 압력이 `1e-6` 인데 헤더에는
`1.00e-4` 같은 **정상으로 보이는 틀린 값**이 실린다.

⭐ 그래서 **게이지가 꺼진 것을 아는 동안 `DEWPRES` 는 sentinel `9.99e-9`** 로
내린다 (운영자 확정, DevNote 11.14-(5) *"게이지 Off 중 DEWPRES 는 9.99e-9"* --
이 코드가 그 확정을 실행하는 자리다).  `HkMonitor` 가 이 객체를 본다.

⏳ **켜짐/꺼짐을 게이지에서 되읽지는 못한다.**  MKS 는 `IGS`(ON/OFF 상태) ·
`RF`(필라멘트) · `RE`(방출전류) 질의를 갖고 있지만, 우리 경로인 MOD10 VCPU
프로그램은 `#05RD`(압력) 하나만 보낸다.  ⏳ VCPU 프로그램에 `IGS` 를 더하면
**진짜 확인**이 되지만 그것도 `APPLYDIO` 가 필요한 ACF 작업이다 -- 지금은
`RCONFIG` 로 읽은 **설정값**이 최선의 증거다.
"""

from __future__ import annotations

import asyncio
import logging

log = logging.getLogger('icg_archon.gauge')

IONEN = 'ionen'
DIOPOWER = 'diopower'

#: 갈래 → (설정 키, 켤 때 값, 끌 때 값).  ⭐ 값을 코드 곳곳에 흩지 않는다.
METHODS = {
    DIOPOWER: ('MOD10\\DIO_POWER', '1', '0'),      # ✅ 실측 확인 (기본)
    IONEN: ('MOD10\\DIO_SOURCE3', '1', '0'),       # ⏳ 미검증
}

#: 응답에 붙일 주석 -- 끄고 켜는 것 **둘 다** VCPU 재시작을 부른다
#: (`APPLYDIO` 도 p.86 대상이다).  히터 쪽 `heater.VCPU_NOTE` 와 같은 규약.
VCPU_NOTE = 'VCPU restarted -- DEWPRES has a gap'

#: `ionen` 으로 껐을 때 압력 읽기가 살아 있으면 그 값은 **이온게이지가 아니라
#: Conductron** 이다 -- 응답에 그 사실을 적어 운영자가 헷갈리지 않게 한다.
CONDUCTRON_NOTE = ('gauge OFF -- any pressure now read is the Conductron '
                   'sensor, not the ion gauge; DEWPRES is held at sentinel')


class GaugeState:
    """이온게이지의 **우리가 아는** 켜짐 상태.

    `on` 은 셋 가운데 하나다 -- `True`(켬) · `False`(끔) · `None`(**모름**).
    ⭐ `None` 은 *"믿을 만한 상태를 아직 못 세웠다"* 는 뜻이다 -- 되읽기 전,
    되읽기 실패(`load()`), **적용됐는지 모르는 명령 실패**(`set()` 의
    `APPLYDIO09` 응답 유실, 2026-09-23), 또는 **거부된 `APPLYDIO09` 뒤 되쓰기
    실패**(`_put_back` -- 설정 메모리에 새 값이 남았을 수 있다, 2026-09-24).  그때는 `DEWPRES` 를 **막지 않는다**
    -- 모름을 결측으로 치면 평상 운영에서 진공값이 조용히 사라진다.

    ⭐ **켠 직후에는 `WARMUP` 이다** (운영자 지시 2026-09-10).  이온게이지는
    **전원을 넣고 `warmup` 초가 지나야 측정이 미덥다** -- 그동안은 켜져 있어도
    값을 믿으면 안 된다.  ⛔ **켤 때마다** 그렇다 (기동이든 `VACGAUGE ON` 이든).

    | 상태 | 낱말 |
    |---|---|
    | 켬 · 예열 중 | **`WARMUP`** |
    | 켬 · 예열 끝 | `ON` |
    | 끔 | `OFF` |
    | 모름 | `UNKNOWN` |

    ⚠️ **예열 중에는 `DEWPRES` 를 막는다** -- 켜져 있긴 하지만 값이 아직 안
    미덥고, 안 미더운 값을 싣는 것이 sentinel 보다 나쁘다 (5.0절의 정신).
    ⭐ **막는 자리는 HK 바퀴(`hk._tick`) 하나다** (운영자 2026-09-14) -- 끄거나
    켠 뒤 **다음 바퀴**에서 낱말과 값이 같이 바뀐다.  `HKDATA NOW` 는 새 바퀴라
    즉시.  (2026-09-11 의 *"읽는 자리에서도 판정"* 은 되돌렸다, DevNote 11.89.)
    ⭐ **되읽어서 알게 된 `ON` 은 예열이 끝난 것으로 본다** -- 우리가 켠 것이
    아니라 이미 켜져 있던 것이므로 언제 켜졌는지 알 수 없고, 앞 세션이 켜 둔
    것이라면 진작 예열이 끝났다.  ⛔ 모르는 것을 예열 중이라 적으면 그것대로
    거짓이다.
    """

    def __init__(self, method: str = DIOPOWER,
                 warmup: float = 12.0) -> None:
        if method not in METHODS:
            raise ValueError('gauge_off_method 는 %s 가운데 하나여야 한다 -- %r'
                             % ('|'.join(sorted(METHODS)), method))
        self.method = method
        self.on: bool | None = None
        #: `'unset'`(아직 안 읽음) | `'failed'`(되읽기 실패 · 적용 여부를 모르는
        #: `set()` 실패 · 거부 뒤 되쓰기 실패) | `'rconfig'` | `'command'`
        self.origin = 'unset'
        #: 켠 뒤 측정이 미더워지기까지 [s] (운영자 확정 2026-09-10: 12초).
        self.warmup = float(warmup)
        #: **우리가 켠** 시각 (monotonic).  `None` 이면 예열 중이 아니다 --
        #: 껐거나, 되읽어서 이미 켜져 있음을 알게 된 경우다.
        self.on_at: float | None = None
        #: ⭐ `set()`·`load()` 를 **한 줄로 세우는 락** (2026-09-24, `set()` 머리말).
        self._lock = asyncio.Lock()

    # -- 상태 ---------------------------------------------------------------

    #: 켜졌지만 **측정이 아직 안 미더운** 상태의 낱말.
    WARMUP = 'WARMUP'

    @property
    def warmup_remaining(self) -> float:
        """예열이 끝나기까지 남은 시간 [s].  예열 중이 아니면 **0.0**.

        ⭐ **HK 가 이 값으로 한 바퀴를 예약한다** (2026-09-11) -- 낱말이
        `WARMUP` 에서 `ON` 으로 뒤집히는 그 시각에 값도 같이 오게 하려는
        것이다.  ⛔ 종전에는 낱말만 즉시 뒤집히고 `DEWPRES` 는 **다음 주기
        바퀴(60초)까지** 안 왔다 -- 벤치 로그에 `VACGAUGE=ON` 인데 `DEWPRES`
        가 없는 줄이 셋 찍혔다 (2026-09-10 18:12:46~55, DevNote 11.70).
        """
        if self.on is not True or self.on_at is None:
            return 0.0
        import time
        return max(self.warmup - (time.monotonic() - self.on_at), 0.0)

    @property
    def warming(self) -> bool:
        """켠 지 `warmup` 초가 아직 안 지났나."""
        return self.warmup_remaining > 0.0

    @property
    def word(self) -> str:
        """`VACGAUGE` 조회 응답에 쓰는 정규형.

        ⭐ 켬이 둘로 갈린다 -- `WARMUP`(예열 중) · `ON`(측정 미덥다).
        """
        if self.on is None:
            return 'UNKNOWN'
        if not self.on:
            return 'OFF'
        return self.WARMUP if self.warming else 'ON'

    @property
    def blocks_dewpres(self) -> bool:
        """⛔ 이 바퀴에서 `DEWPRES` 를 sentinel 로 내려야 하나 (`hk._tick` 이 본다).

        **꺼진 것을 아는 동안**과 **예열 중**에 참이다 (운영자 2026-09-10).
        ⚠️ `None`(모름)은 막지 않는다 -- 모름을 결측으로 치면 평상 운영에서
        진공값이 조용히 사라진다.
        ⭐ 예열 중을 막는 이유: 켜져 있긴 하지만 값이 아직 안 미덥고, **안
        미더운 값을 싣는 것이 sentinel 보다 나쁘다** (규격 5.0절의 정신).
        """
        return self.on is False or self.warming

    # -- 왕복 ---------------------------------------------------------------

    async def load(self, ctrl, *, fresh: bool = False) -> None:  # noqa: ANN001
        """기동에서 **컨트롤러 설정을 되읽어** 상태를 세운다.

        ⚠️ 게이지 자체에 물어보는 것이 아니다 (그 경로가 없다 -- 모듈 문서의
        `IGS` 참고).  실패하면 `None`(모름)으로 남긴다 -- 추측으로 `ON` 을
        적으면 `DEWPRES` 판정의 근거가 거짓이 된다.

        ⭐ **`fresh` 는 *"전원 상태가 방금 정해졌다"* 는 뜻이다** (운영자 지적
        2026-09-10).  `APPLYALL` 이 ACF 의 `MOD10\\DIO_POWER` 를 그대로
        적용하므로, ACF 적용 직후에 읽은 `ON` 은 **막 켜진 것**이고 예열 중이다.
        ⛔ `fresh=False`(기본)면 언제 켜졌는지 모르는 것이므로 **예열이 끝난
        것으로 본다** -- 모르는 것을 예열 중이라 적으면 그것대로 거짓이다.

        ⭐ **`set()` 과 같은 락(`_lock`)을 쥔다** (2026-09-24) -- 기동 중에
        `VACGAUGE` 가 들어와 `set()` 이 도는 동안 되읽은 값이 그 선반영을
        덮으면 안 된다 (`set()` 머리말).
        """
        async with self._lock:
            await self._load_locked(ctrl, fresh=fresh)

    async def _load_locked(self, ctrl, *, fresh: bool) -> None:  # noqa: ANN001
        """`load()` 의 몸통 -- ⛔ `_lock` 을 쥔 채로만 부른다."""
        key, on_val, _off = METHODS[self.method]
        try:
            got = (await ctrl.read_config(key)).strip()
        except Exception as exc:            # noqa: BLE001
            log.warning('could not read back the ion gauge state (%s) -- %s',
                        key, exc,
                        extra={'detail': '모름으로 두고 DEWPRES 는 막지 않는다'})
            # ⛔ `'unset'`(아직 안 읽음)이 아니라 `'failed'` 다 -- 시도했고
            # 실패한 것이라 `WARMUP` 이 아니라 `UNKNOWN` 으로 나가야 한다.
            self.on, self.origin = None, 'failed'
            return
        import time
        self.on = got == on_val
        self.origin = 'rconfig'
        # ⭐ `fresh` 면 방금 켜진 것이라 예열 시계를 세운다 (머리말 참조).
        self.on_at = time.monotonic() if (fresh and self.on) else None
        log.info('ion gauge %s', self.word,
                 extra={'detail': '%s=%s, method %s' % (key, got, self.method)})

    async def set(self, ctrl, on: bool) -> str:  # noqa: ANN001
        """게이지를 켜거나 끈다.  응답에 붙일 주석 문구를 돌려준다.

        ⭐ **상태를 먼저 올린다** -- `WCONFIG`/`APPLYDIO` 왕복 동안 HK 주기가
        끼어들 수 있고, 그때 `DEWPRES` 가 이미 Conductron 값일 수 있기
        때문이다 (`EXPENABLE OFF` 가 플래그를 먼저 올리는 것과 같은 이유).
        ⚠️ 그래서 왕복이 실패하면 상태를 고쳐 놓는데, **적용이 안 된 것이
        확실한가**로 갈래가 둘이다 (2026-09-23):

        | 실패한 자리 | 물리 상태 | 남기는 상태 |
        |---|---|---|
        | `WCONFIG` (예외 종류 무관) | 직전 그대로 -- `APPLYDIO09` 를 안 보냈다 | **직전 상태로 되돌린다** (`on`·`origin`·`on_at` 셋 다) |
        | `APPLYDIO09` 를 컨트롤러가 `?xx` 로 거부 (`reply_error=True`) | 직전 그대로 -- 거부는 미적용이다 | 〃 + 설정 메모리에 **직전 값을 되쓴다** (`WCONFIG` 한 번, 아래 *"새 값이 남는다"* 문단).  되쓰기가 실패하면 **모름** |
        | `APPLYDIO09` 의 시한 초과·링크 끊김·취소 (`reply_error` 없는 `ArchonError` · `TimeoutError` · `OSError` …) | **모른다** -- 컨트롤러가 받아 적용한 뒤 응답만 잃었을 수 있다 | **모름** -- `on=None` · `origin='failed'` · `on_at=None` (낱말 `UNKNOWN`) |

        ⭐ 되돌리는 근거: 켜려다 실패했으면 여전히 꺼진 것으로 보고 `DEWPRES`
        를 막는다.  성공한 것처럼 남겨 두면 반대 방향으로 거짓말한다.
        ⛔ 모름으로 두는 근거: 켜려다 응답을 잃었는데 직전 `OFF` 로 되돌리면,
        **실제로는 켜졌을 수 있는** 게이지를 `OFF` 라 적는다 -- ICS 는 `GO` 때
        받은 `HKDATA NOW` 의 `VACGAUGE=OFF` 를 보면 `VACGAUGE OFF` 를
        **건너뛰므로**(`ics_archon/gaugectl.py` `before_exposure`) 필라멘트가
        켜진 채 science 노출이 나간다.  `UNKNOWN` 이면 ICS 가 다음 science 노출
        전에 `OFF` 를 보낸다.
        ⚠️ 모름은 `DEWPRES` 를 막지 않는다(`blocks_dewpres`) -- 끄려다 응답을
        잃었는데 실제로 꺼졌다면 `ionen` 갈래에서는 Conductron 값이 실릴 수
        있다 (`diopower` 는 읽기까지 죽어 실을 값이 없다).  `vacgauge on`/
        `vacgauge off` 로 다시 맞추면 풀린다.
        ⚠️ **`WCONFIG` 는 앉고 `APPLYDIO09` 가 거부되면 설정 메모리(와 우리 캐시
        `ctrl.config`)에 새 값이 남는다** -- 적용이 안 됐으므로 물리 상태는 직전
        그대로인데, 같은 세션에서 뒤에 오는 **히터 쪽 `APPLYMOD09`** 가 그 값을
        적용할 수 있다: 히터 명령 `HTRSET`·`HTRFORCE`·`HTRRAMP`·`HTRPID`
        (`heater._write_and_apply`)와 과열 차단(`heater.OverTempGuard` →
        `heater.shutdown`).  (⏳ `APPLYMOD` 가 DIO 줄까지 싣는지는 매뉴얼이 말하지
        않고 실측도 없다 -- p.86 은 VCPU 를 싣는다고만 적었다.)  ⭐ 그래서 그
        갈래는 **직전 값을 `WCONFIG` 로 한 번 되쓴다** (2026-09-24, `_put_back`).
        직전 상태가 모름(`None`)이면 되쓸 값을 모르므로 쓰지 않는다 -- 상태는
        되돌린 그대로 `UNKNOWN` 이다.  ⛔ 되쓰기도 실패하면 **모름**으로 둔다 --
        메모리에 새 값이 남았을 수 있어 뒤의 `APPLYMOD09` 가 게이지를 바꿀 수
        있다.  ⭐ 어느 쪽이든 올리는 예외는 **원래 것**(`APPLYDIO09` 거부)이다.
        ⚠️ `WCONFIG` 자체가 응답만 잃은 경우는 되쓰지 않는다 (위 표 첫 줄 --
        직전 상태로 되돌린다) -- 그때도 메모리에 새 값이 앉았을 수 있다.  ICG
        재기동은 ACF 를 다시 적용하므로(`CLEARCONFIG` → `WCONFIG` → `APPLYALL`)
        남은 값을 집지 않는다.  ⚠️ 다만 같은 세션에서는 위 히터 쪽 `APPLYMOD09`
        들이나, 운영자가 바이패스로 치는 `archon APPLYALL`·`archon APPLYDIO09`
        가 그 값을 적용할 수 있다 -- 그때는 `vacgauge` 로 다시 맞출 것.

        ⭐ **호출을 한 줄로 세운다** (`_lock`, 2026-09-24).  `VACGAUGE` 는 명령마다
        태스크를 띄우고(`commands._do_vacgauge`) 기동의 `_settle_gauge`·종료도 이
        함수를 부르므로 두 호출이 겹칠 수 있다.  ⛔ 겹치면 뒤 호출이 뜬 직전
        상태가 **앞 호출의 미확정 선반영 값**이 된다 -- 켜진 게이지를 끄려던 앞
        호출이 `APPLYDIO09` 응답을 잃어 `UNKNOWN` 으로 둔 뒤, 켜려던 뒤 호출의
        `WCONFIG` 가 실패하면 그 선반영 값 `OFF` 로 되돌려 **필라멘트가 켜져 있을
        수 있는데 `OFF` 라 적는다** (ICS 가 `VACGAUGE OFF` 를 건너뛴다).  그래서
        직전 상태 뜨기 · 선반영 · 왕복 · 실패 처리를 **통째로** 락 안에서 한다.
        ⚠️ 락을 기다리는 동안은 선반영도 없다 -- HK 바퀴는 앞 호출이 남긴 상태를
        본다.
        ⚠️ **부르는 쪽의 *"이미 맞다"* 판정은 락 밖이다** -- `app._settle_gauge` 의
        `gauge.on is want` 와 `app.stop()` 의 `gauge.on is False` 는 도는 호출의 선반영
        값을 볼 수 있다(⏳ 락 안에서 판정하는 `ensure()` 로 옮길지는 다음 라운드).
        """
        async with self._lock:
            return await self._set_locked(ctrl, on)

    async def _set_locked(self, ctrl, on: bool) -> str:  # noqa: ANN001
        """`set()` 의 몸통 -- ⛔ `_lock` 을 쥔 채로만 부른다."""
        import time
        key, on_val, off_val = METHODS[self.method]
        prev, prev_origin, prev_at = self.on, self.origin, self.on_at
        self.on, self.origin = on, 'command'
        # ⭐ **켤 때마다 예열 시계를 다시 세운다** (운영자 2026-09-10).
        # ⛔ 끌 때는 지운다 -- 꺼진 것에 예열은 뜻이 없다.
        self.on_at = time.monotonic() if on else None
        applying = False                    # `APPLYDIO09` 를 내보냈나
        try:
            await ctrl.set_config(key, on_val if on else off_val)
            applying = True
            await ctrl.apply_module(10, dio=True)      # ⭐ APPLYDIO09
        except BaseException as exc:
            # ⚠️ 취소(`CancelledError`)도 잡는다 -- `APPLYDIO09` 가 나간 뒤
            # 끊기면 역시 적용 여부를 모른다.  어느 갈래든 예외는 그대로 올린다.
            if not applying:
                # `WCONFIG` 에서 멈췄다 -- `APPLYDIO09` 를 안 보냈으니 직전 상태로.
                self.on, self.origin, self.on_at = prev, prev_origin, prev_at
            elif getattr(exc, 'reply_error', False) is True:
                # `APPLYDIO09` 거부 -- 미적용이 확실하다.  ⚠️ 그런데 `WCONFIG` 는
                # 앉았으므로 메모리의 새 값을 직전 값으로 되쓴다 (머리말의
                # *"새 값이 남는다"* 문단).
                self.on, self.origin, self.on_at = prev, prev_origin, prev_at
                await self._put_back(ctrl, key, prev, on_val if on else off_val)
            else:
                self.on, self.origin, self.on_at = None, 'failed', None
                log.warning('ion gauge %s: the APPLYDIO09 round trip broke -- '
                            'state is now UNKNOWN', 'ON' if on else 'OFF',
                            extra={'detail': '컨트롤러가 적용했는지 모른다 '
                                             '(%s).  직전 상태로 되돌리면 켜졌을 '
                                             '수 있는 게이지를 OFF 라 적어 ICS 가 '
                                             'VACGAUGE OFF 를 건너뛴다 -- '
                                             'UNKNOWN 이면 다음 science 노출 '
                                             '전에 OFF 를 보낸다'
                                             % (type(exc).__name__,)})
            raise
        log.info('ion gauge %s', self.word,
                 extra={'detail': '%s, method %s -- ⚠️ %s'
                                  % (key, self.method, VCPU_NOTE)})
        return VCPU_NOTE if on else '%s (%s)' % (CONDUCTRON_NOTE, VCPU_NOTE)

    async def _put_back(self, ctrl, key: str, prev: bool | None,  # noqa: ANN001
                        new: str) -> None:
        """거부된 `APPLYDIO09` 뒤 설정 메모리의 새 값 `new` 를 **직전 값으로 되쓴다**.

        `set()` 머리말의 *"새 값이 남는다"* 문단이 이 갈래다 -- 부르기 전에 상태는
        이미 직전으로 되돌렸다.
        ⭐ **한 번만** 시도한다.  직전 상태가 모름(`prev is None`)이면 되쓸 값을
        모르므로 쓰지 않는다 (상태는 되돌린 그대로 `UNKNOWN`).
        ⛔ **원래 예외를 가리지 않는다** -- 되쓰기의 실패(`Exception`)는 삼키고
        상태를 모름으로 둔 뒤 돌아간다.  원래 예외(`APPLYDIO09` 거부)는 부른
        쪽이 그대로 올린다.  ⚠️ 취소만은 막지 않는다 -- 모름으로 두고 그대로
        올린다 (원래 예외는 그 `__context__` 에 남는다).
        """
        if prev is None:
            return
        _key, on_val, off_val = METHODS[self.method]
        back = on_val if prev else off_val
        try:
            await ctrl.set_config(key, back)
        except BaseException as exc:
            self.on, self.origin, self.on_at = None, 'failed', None
            log.warning('ion gauge: could not put %s back to %s after the '
                        'refused APPLYDIO09 -- state is now UNKNOWN', key, back,
                        extra={'detail': '설정 메모리에 새 값(%s)이 남았을 수 '
                                         '있다 (%s: %s).  뒤의 히터 쪽 '
                                         'APPLYMOD09(HTR* 명령 · 과열 차단)가 '
                                         '그 값을 적용할 수 있어 직전 상태를 '
                                         '단정하지 않는다 -- vacgauge on/off 로 '
                                         '다시 맞출 것'
                                         % (new, type(exc).__name__, exc)})
            if not isinstance(exc, Exception):
                raise

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
    ⭐ `None` 은 *"끄라는 명령을 받은 적이 없다"* 는 뜻이고, 그때는 `DEWPRES`
    를 **막지 않는다** -- 모름을 결측으로 치면 평상 운영에서 진공값이 조용히
    사라진다.

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
        #: `'unset'`(아직 안 읽음) | `'failed'`(읽다 실패) | `'rconfig'` | `'command'`
        self.origin = 'unset'
        #: 켠 뒤 측정이 미더워지기까지 [s] (운영자 확정 2026-09-10: 12초).
        self.warmup = float(warmup)
        #: **우리가 켠** 시각 (monotonic).  `None` 이면 예열 중이 아니다 --
        #: 껐거나, 되읽어서 이미 켜져 있음을 알게 된 경우다.
        self.on_at: float | None = None

    # -- 상태 ---------------------------------------------------------------

    #: 켜졌지만 **측정이 아직 안 미더운** 상태의 낱말.
    WARMUP = 'WARMUP'

    @property
    def warming(self) -> bool:
        """켠 지 `warmup` 초가 아직 안 지났나."""
        if self.on is not True or self.on_at is None:
            return False
        import time
        return (time.monotonic() - self.on_at) < self.warmup

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
        """⛔ 지금 `DEWPRES` 를 sentinel 로 내려야 하나.

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
        """
        key, on_val, _off = METHODS[self.method]
        try:
            got = (await ctrl.read_config(key)).strip()
        except Exception as exc:            # noqa: BLE001
            log.warning('이온게이지 상태를 되읽지 못했다 (%s) -- %s.  모름으로 '
                        '두고 DEWPRES 는 막지 않는다', key, exc)
            # ⛔ `'unset'`(아직 안 읽음)이 아니라 `'failed'` 다 -- 시도했고
            # 실패한 것이라 `WARMUP` 이 아니라 `UNKNOWN` 으로 나가야 한다.
            self.on, self.origin = None, 'failed'
            return
        import time
        self.on = got == on_val
        self.origin = 'rconfig'
        # ⭐ `fresh` 면 방금 켜진 것이라 예열 시계를 세운다 (머리말 참조).
        self.on_at = time.monotonic() if (fresh and self.on) else None
        log.info('이온게이지 %s (%s=%s, 갈래 %s)',
                 self.word, key, got, self.method)

    async def set(self, ctrl, on: bool) -> str:  # noqa: ANN001
        """게이지를 켜거나 끈다.  응답에 붙일 주석 문구를 돌려준다.

        ⭐ **상태를 먼저 올린다** -- `WCONFIG`/`APPLYDIO` 왕복 동안 HK 주기가
        끼어들 수 있고, 그때 `DEWPRES` 가 이미 Conductron 값일 수 있기
        때문이다 (`EXPENABLE OFF` 가 플래그를 먼저 올리는 것과 같은 이유).
        ⚠️ 그래서 왕복이 실패하면 **상태를 모름으로 되돌린다** -- 성공한
        것처럼 남겨 두면 반대 방향으로 거짓말한다.
        """
        import time
        key, on_val, off_val = METHODS[self.method]
        prev, prev_origin, prev_at = self.on, self.origin, self.on_at
        self.on, self.origin = on, 'command'
        # ⭐ **켤 때마다 예열 시계를 다시 세운다** (운영자 2026-09-10).
        # ⛔ 끌 때는 지운다 -- 꺼진 것에 예열은 뜻이 없다.
        self.on_at = time.monotonic() if on else None
        try:
            await ctrl.set_config(key, on_val if on else off_val)
            await ctrl.apply_module(10, dio=True)      # ⭐ APPLYDIO09
        except Exception:
            self.on, self.origin, self.on_at = prev, prev_origin, prev_at
            raise
        log.info('이온게이지 %s (%s, 갈래 %s) -- ⚠️ %s',
                 self.word, key, self.method, VCPU_NOTE)
        return VCPU_NOTE if on else '%s (%s)' % (CONDUCTRON_NOTE, VCPU_NOTE)

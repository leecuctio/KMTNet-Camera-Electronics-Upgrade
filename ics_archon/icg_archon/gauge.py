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

| 갈래 | 무엇을 쓰나 | 범위 | 근거 |
|---|---|---|---|
| **`ionen`** (기본) | `MOD10\\DIO_SOURCE3` 1→0 | IONEN **한 라인**만 HIGH→LOW | Archon p.62 `DIO_SOURCEi` 0=low·1=high·2=timing·3=VCPU |
| `diopower` | `MOD10\\DIO_POWER` 1→0 | **8라인 전부**의 버퍼 전원 | ⭐ 참고 보관함의 `…_goff_….acf` 가 **정확히 이 한 줄만** 다르다 -- 선임이 실제로 쓴 길 |

⚠️ `diopower` 는 시리얼 3선(`ION_DE`/`ION_DI`/`ION_RO`)의 버퍼 전원도 끊으므로
**압력 읽기까지 죽는다**.  `ionen` 은 읽기를 살린 채 필라멘트만 끈다.  ⏳ 둘 다
**첫 구동 실측 대기**라 ini(`[icg] gauge_off_method`)로 고를 수 있게 두었다 --
벤치에서 `ionen` 이 안 통하면 검증된 `diopower` 로 한 줄만 바꾼다.

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
    IONEN: ('MOD10\\DIO_SOURCE3', '1', '0'),
    DIOPOWER: ('MOD10\\DIO_POWER', '1', '0'),
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
    를 **막지 않는다** -- ACF 출하값이 `DIO_SOURCE3=1`(켬)이고, 모름을 결측으로
    치면 평상 운영에서 진공값이 조용히 사라진다.
    """

    def __init__(self, method: str = IONEN) -> None:
        if method not in METHODS:
            raise ValueError('gauge_off_method 는 %s 가운데 하나여야 한다 -- %r'
                             % ('|'.join(sorted(METHODS)), method))
        self.method = method
        self.on: bool | None = None
        self.origin = 'unset'               #: 'unset'|'rconfig'|'command'

    # -- 상태 ---------------------------------------------------------------

    @property
    def word(self) -> str:
        """`VACGAUGE` 조회 응답에 쓰는 정규형."""
        return 'UNKNOWN' if self.on is None else ('ON' if self.on else 'OFF')

    @property
    def blocks_dewpres(self) -> bool:
        """⛔ 지금 `DEWPRES` 를 sentinel 로 내려야 하나.

        **꺼진 것을 아는 동안만** 참이다 -- `None`(모름)은 막지 않는다.
        """
        return self.on is False

    # -- 왕복 ---------------------------------------------------------------

    async def load(self, ctrl) -> None:  # noqa: ANN001
        """기동에서 **컨트롤러 설정을 되읽어** 상태를 세운다.

        ⚠️ 게이지 자체에 물어보는 것이 아니다 (그 경로가 없다 -- 모듈 문서의
        `IGS` 참고).  실패하면 `None`(모름)으로 남긴다 -- 추측으로 `ON` 을
        적으면 `DEWPRES` 판정의 근거가 거짓이 된다.
        """
        key, on_val, _off = METHODS[self.method]
        try:
            got = (await ctrl.read_config(key)).strip()
        except Exception as exc:            # noqa: BLE001
            log.warning('이온게이지 상태를 되읽지 못했다 (%s) -- %s.  모름으로 '
                        '두고 DEWPRES 는 막지 않는다', key, exc)
            self.on, self.origin = None, 'unset'
            return
        self.on = got == on_val
        self.origin = 'rconfig'
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
        key, on_val, off_val = METHODS[self.method]
        prev, prev_origin = self.on, self.origin
        self.on, self.origin = on, 'command'
        try:
            await ctrl.set_config(key, on_val if on else off_val)
            await ctrl.apply_module(10, dio=True)      # ⭐ APPLYDIO09
        except Exception:
            self.on, self.origin = prev, prev_origin
            raise
        log.info('이온게이지 %s (%s, 갈래 %s) -- ⚠️ %s',
                 self.word, key, self.method, VCPU_NOTE)
        return VCPU_NOTE if on else '%s (%s)' % (CONDUCTRON_NOTE, VCPU_NOTE)

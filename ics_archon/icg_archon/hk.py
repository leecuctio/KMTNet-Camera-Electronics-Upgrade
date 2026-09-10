#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HK 취득·로깅 (층 3 + guide 층 1) -- 1분 주기, `ics_archon` 이 소비한다.

한 바퀴에 모으는 것 (운영자 확정 그룹):

* **Ctrl**      `C1_TEMP`/`C1_VOLT`/`C1_CURR` 원값 -- guide STATUS (10.4절 자리 표)
* **DIO**       `DEWPRES` -- MOD10 VCPU 가 MKS 356 을 시리얼로 판 10글자
* **RTD**       `CCDTEMP` `DMPTEMP` `PT30N1` `PT30N2` `CHARCOAL` `WALLBRD`
                -- guide HeaterX 6채널 (`ICG RTD` 계통의 전량)
* **Radionode** `HEBOX` `FSATEMP` `FSAHUM` -- 클라우드 폴러 (`radionode.py`)
* **AUX**       `ENS1~7` -- TC `AUXSTATUS` 질의

산출물 둘 -- **둘 다 지연 없이** 쓴다 (`ics_archon` 이 실시간으로 읽는다):

* `hk.G.<YYYYMMDD>.csv` -- 일자별 CSV, 행마다 flush.  다른 프로세스가 읽는
  중에도 이어 쓴다 (열 구성이 바뀌면 `monitor.py` 처럼 파일을 가른다).
* `hk_latest.G.json` -- **원자적**(tmp + `os.replace`) 최신 스냅샷.
  `ics_archon` 의 `sensors()` 가 이것 하나만 읽으면 된다 -- 값 + 표본시각
  (epoch) 이 실려 있어 **신선도 판정이 읽는 쪽에서 된다.**

해독 규칙의 정본은 `ics_archon/SMC_CLAUDE.md` "층 3" 절들 (실측 확정 --
재조사 금지):

* 단위는 **섭씨다** (매뉴얼 p.48 "in K" 는 오기 -- 273.15 변환 금지).
* RTD 결측 판정은 값이 아니라 **ACF `SENSORx{LOWER,UPPER}LIMIT` 범위**로
  한다 -- 미연결 채널이 그럴듯한 값(-196.9 등)을 낼 수 있다.
* `DEWPRES` 신선도는 **`OUTREG15`(Alive) 증가**로만 안다 -- 응답이 짧으면
  옛 글자가 남고 Alive 도 안 오른다.  두 번 연속 불변이면 결측 처리.
"""

from __future__ import annotations

import asyncio
import csv
import datetime
import json
import logging
import os
import sys
import time

from ics_archon import _simpath

_simpath.ensure()

from ics_sim import console  # noqa: E402
from ics_sim.state import (stamp_compact, stamp_iso,  # noqa: E402
                           stamp_iso_ms, utcnow)

from . import guidehdr, heater  # noqa: E402
from .config import IcgCfg  # noqa: E402

log = logging.getLogger('icg_archon.hk')

#: STATUS 필드 -> 센서 계약 키 (층 3 표 -- ACF 이름표와 일대일).
RTD_FIELDS = (
    ('MOD7/TEMPA', 'charcoal'),
    ('MOD7/TEMPB', 'pt30n1'),
    ('MOD7/TEMPC', 'pt30n2'),
    ('MOD10/TEMPA', 'dmptemp'),
    ('MOD10/TEMPB', 'ccdtemp'),
    ('MOD10/TEMPC', 'wallbrd'),
)

#: 히터 채널 A 의 출력 -- FITS 카드 `HTROUT` 의 원천 (규격 5.6.2절).
#:
#: ⭐ **`MOD10/HEATERAOUTPUT`** -- 백플레인 FW 1.0.1252(guide 실기와 같은 판)
#: 이미지 분석으로 HeaterX(type 11) STATUS 경로가 이 키를 출력함을 확인했다
#: (DevNote 11.30).  매뉴얼 p.48 이 이 줄에 "Heater only" 라 적은 것은 FW 와
#: 어긋난 오기다.  ⏳ 값이 출력단 **측정값**인지 PID/FORCE **명령값**인지는
#: 실기 미확인(규격 OI-28) -- 첫 구동 FORCE 실험이 닫는다.
#:
#: 계약 키 10개 **밖**이다 -- `HKDATA` 완전성 셈(계약키 교집합 + HKSTALE)에
#: 들어가지 않고, 스냅샷 `values` 로만 `ics_archon.sensors()` 에 흘러간다
#: (`rawhdr.thermal_header()` 가 `htrout` 을 `format_htrout()` 로 싣는다).
HEATER_OUTPUT_FIELD = 'MOD%d/HEATER%sOUTPUT' % (heater.SLOT, heater.CH)


def _float_or_none(text: object) -> float | None:
    """STATUS 토큰 -> float, 못 읽으면 None (결측·비수치 둘 다 None)."""
    if text is None:
        return None
    try:
        v = float(str(text).strip())
    except (TypeError, ValueError):
        return None
    return None if v != v else v

def _limit_keys(field: str) -> tuple[str, str]:
    """`MOD<m>/TEMP<c>` -> ACF 한계 키 쌍 (하한, 상한).

    ⚠️ **구분자는 `/` 다.**  ACF 원문은 `MOD7\\SENSORALOWERLIMIT` 처럼
    역슬래시인데 `controller.parse_acf()` 가 읽으면서 `/` 로 정규화한다
    (`controller.py` -- `key.upper().replace('\\', '/')`).  역슬래시로
    조회하면 **한 채널도 안 맞아 한계 판정이 통째로 죽고**, 미연결 채널의
    그럴듯한 값(-196.9 등)이 그대로 헤더에 실린다.  값 판정이 아니라 이
    한계 판정이 결측 판별의 전부라 조용히 틀린 값이 된다 (층 3 규칙).
    """
    mod, tail = field.split('/')          # 'MOD7', 'TEMPA'
    ch = tail[-1]                          # 'A'|'B'|'C'
    return ('%s/SENSOR%sLOWERLIMIT' % (mod, ch),
            '%s/SENSOR%sUPPERLIMIT' % (mod, ch))


def _limit_of(acf_config: dict, key: str):  # noqa: ANN201
    """한계 값 조회 -- 정규화 전 원문(역슬래시)도 받아 준다."""
    got = acf_config.get(key)
    if got is None:
        got = acf_config.get(key.replace('/', '\\'))
    return got


def notify(text: str) -> None:
    """운영자에게 **콘솔로도** 알린다 (운영자 지시 2026-09-06).

    ⚠️ 로그 핸들러는 `sys.stderr` 인데(`ics_sim/__main__.py`) 시험 절차의 실행
    명령이 `python3 -u -m icg_archon | tee …` 라 **stdout 만 tee 된다** -- 로그만
    쓰면 경고가 **기록 파일에 안 남는다**.  그래서 `log` 와 함께 stdout 으로 낸다.

    ⛔ **그런데 stdout·stderr 가 같은 터미널이면 안 낸다.**  그때는 운영자가
    로그 줄을 **이미 봤고**, 또 내면 모든 경고가 **두 줄**로 보이며 프롬프트
    줄에 달라붙는다 (`ICG% ⚠️ HK: …` -- 벤치 2026-09-08).
    ⭐ 이 함수의 존재 이유는 *"파이프로 흘릴 때 기록에 남기기"* 이므로, 그
    조건에서만 내면 이유를 그대로 지킨다.
    ⚠️ 부르는 쪽은 **로그도 함께** 내야 한다 -- 여기서 건너뛴 줄의 유일한
    자취가 로그다 (히터 과열 차단은 `heater.OverTempGuard` 가 `log.error` 둘을
    이미 낸다).
    ⚠️ 실패해도 삼킨다 -- stdout 이 닫힌 배치 실행에서 감시 루프가 죽으면 안 된다.
    """
    if console.is_tty(sys.stdout) and console.is_tty(sys.stderr):
        return
    try:
        print('⚠️  %s' % text, flush=True)
    except Exception:                       # noqa: BLE001
        pass


def decode_rtd(status: dict, acf_config: dict = None) -> dict[str, float]:  # noqa: ANN001
    """RTD 6채널 -- **STATUS 가 준 값을 그대로 낸다.**

    ⛔ **한계로 버리지 않는다** (운영자 지시 2026-09-06: *"센서 상한/하한을
    넘기더라도 버리지 말고 그대로 들어가게 해줘.  센서 결측을 임의로 만들지
    마."*).  종전에는 ACF 의 `SENSOR?LOWER/UPPERLIMIT` 밖이면 키를 안 냈는데,
    그것이 **두 가지 서로 다른 일을 겸하고** 있었다:

    1. 미연결 채널 감추기 (`-273.2` 고정과 그 노이즈 -- 벤치에서 MOD7 의
       `_TBC` 두 채널이 그랬다, 규격 v1.12 767행)
    2. **한계 밖 실측값 감추기**

    2번이 실제 사고를 만들었다 -- 히터 과열(상한 초과)이 헤더에서 `dmptemp`
    **결측**으로만 보였다.  이상 상태가 센서 고장으로 위장된 것이다.

    ⭐ 그래서 **버리는 대신 알린다** -- 한계 밖 판정은 `out_of_limit()` 이
    따로 하고 `_tick` 이 경고 로그를 남긴다.  값은 그대로 나간다.

    결측은 이제 **장치가 값을 안 준 것**뿐이다: STATUS 에 그 필드가 없거나,
    있는데 수치로 못 읽거나.

    ⚠️ `acf_config` 는 이제 안 쓴다 -- 부르는 쪽 표기를 안 깨려고 남겨 뒀다.
    """
    out: dict[str, float] = {}
    for field, key in RTD_FIELDS:
        raw = status.get(field)
        if raw is None:
            continue                    # 장치가 안 줬다 -- 정직한 결측
        try:
            out[key] = float(raw)
        except (TypeError, ValueError):
            continue                    # 수치가 아니다 -- 역시 못 읽은 것
    return out


def out_of_limit(status: dict, acf_config: dict) -> dict[str, tuple]:
    """ACF 한계 **밖**인 RTD 만 `key -> (값, 하한, 상한)` 으로.

    ⭐ **값을 버리려는 것이 아니라 알리려는 것이다** (`decode_rtd` 주석 참고).
    미연결 채널(`-273.2`)도, 진짜 과열도 여기 걸린다 -- 어느 쪽인지는 사람이
    가른다.  한계를 못 읽으면(파싱 전) 아무것도 안 낸다: 판정 근거가 없다.
    """
    out: dict[str, tuple] = {}
    for field, key in RTD_FIELDS:
        raw = status.get(field)
        if raw is None:
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        lo_k, hi_k = _limit_keys(field)
        lo, hi = _limit_of(acf_config or {}, lo_k), _limit_of(acf_config or {}, hi_k)
        if lo is None or hi is None:
            continue
        try:
            lo_f, hi_f = float(lo), float(hi)
        except (TypeError, ValueError):
            continue
        if not (lo_f <= val <= hi_f):
            out[key] = (val, lo_f, hi_f)
    return out


class DewpresDecoder:
    """`MOD10/VCPU_OUTREG0~9` 10글자 + `OUTREG15`(Alive) -> 게이지 원문.

    **정상 판정은 "Alive 가 직전보다 증가" 하나뿐이다.**  0/감소는 진공
    게이지를 읽는 MOD10 VCPU 의 재시작 신호(경고 -- ⭐ **히터 명령·게이지
    명령이 이것을 일으킨다**, DevNote 11.18), 두 번 연속 불변은 게이지
    이상 -- 둘 다 결측.  ⭐ 그래서 재시작 창의 **잔재(OUTREG 에 남은 직전
    응답 10글자)를 실을 위험은 없다** -- Alive 가 먼저 걸러낸다.
    """

    def __init__(self) -> None:
        self._alive: int | None = None
        self._flat = 0
        self._warned_restart = False
        #: 앞 바퀴에 본 `ctrl.apply_count` -- 되감김이 **우리 탓인지** 가른다.
        self._applies: int | None = None

    def decode(self, status: dict, applies: int | None = None) -> str | None:
        """`applies` 는 `ArchonController.apply_count` -- 없으면 종전대로 문다."""
        ours, self._applies = (applies is not None
                               and self._applies is not None
                               and applies != self._applies), applies
        alive_raw = status.get('MOD10/VCPU_OUTREG15')
        if alive_raw is None:
            return None                    # VCPU 보고 자체가 없다
        try:
            alive = int(float(alive_raw))
        except (TypeError, ValueError):
            return None
        prev, self._alive = self._alive, alive
        if prev is None:
            fresh = alive > 0
        elif alive > prev:
            fresh, self._flat = True, 0
        elif alive < prev or alive == 0:
            if ours:
                # ⭐ **우리가 친 `APPLY*` 가 만든 재시작이다** -- 기동의
                # `APPLYALL` 이 대표적이라 이것을 경고로 울면 **띄울 때마다**
                # 뜬다 (벤치 2026-09-08).  그러면 그 줄을 무시하는 버릇이 들어,
                # 정작 *"우리가 안 했는데 재시작됐다"* 는 진짜 신호를 놓친다.
                # ⚠️ 결측 처리는 그대로다 -- 잔재를 실을 수는 없다.
                log.info('vacuum VCPU alive counter rewound (%s -> %s) -- '
                         'expected, we sent an APPLY this round',
                         prev, alive,
                         extra={'detail': 'DEWPRES 는 이번 바퀴만 결측이고 '
                                          '다음 바퀴에 돌아온다'})
                return None
            if not self._warned_restart:
                self._warned_restart = True
                log.warning('vacuum VCPU alive counter rewound (%s -> %s) '
                            '-- we sent no APPLY, so this looks like a restart',
                            prev, alive,
                            extra={'detail':
                                   '⚠️ APPLYALL 뿐 아니라 모듈 하나만 적용하는 '
                                   'APPLYMOD09 · APPLYDIO09 도 그렇다 (매뉴얼 '
                                   'p.86) -- 히터 명령(HTREN/HTRSET)과 게이지 '
                                   '명령(VACGAUGE)이 이것을 일으킨다.  DEWPRES '
                                   '는 결측으로 싣는다.  ⏳ 카운터 wrap 일 수도 '
                                   '있다 -- HK CSV 의 alive 열로 폭을 실측할 것'})
            return None
        else:
            self._flat += 1
            fresh = self._flat < 2         # 한 번 불변까지는 직전 값 인정
        if not fresh:
            return None
        chars = []
        for i in range(10):
            raw = status.get('MOD10/VCPU_OUTREG%d' % i)
            try:
                code = int(float(raw))
            except (TypeError, ValueError):
                return None
            if 32 <= code < 127:
                chars.append(chr(code))
        text = ''.join(chars).strip()
        # 재포맷하지 않는다 -- `rawhdr.format_dewpres` 가 원값을 받아
        # `6.93e-04` -> `6.93e-4` 로 만들고 인정 범위도 검사한다 (층 3 규칙).
        return text or None


def ctrl_unit(status: dict) -> dict:
    """guide STATUS -> `{'temp': [...], 'volt': [...], 'curr': [...]}`.

    자리 표는 `guidehdr.TEMP_MODS`/`VOLT_RAILS` (10.4절, 8자리).  과학 쪽
    `parse.telemetry_of()` 와 같은 D4 규칙 -- `VALID=0` 이면 전 자리 결측
    (기록에는 그 사실이, 헤더에는 `NC` 가 남는다).
    """
    if not status or str(status.get('VALID', '1')).strip() == '0':
        return {}

    def _num(raw):  # noqa: ANN001
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    temps = [_num(status.get(f)) for f in guidehdr.TEMP_MODS]
    volt: list[float | None] = []
    curr: list[float | None] = []
    for rail in guidehdr.VOLT_RAILS:
        if rail == 'HEATER':
            # `HEATER_V`/`HEATER_I` (매뉴얼 p.47 · FW 1.0.1252 -- DevNote 11.30).
            # 후보 튜플은 한 줄이지만 순회 꼴은 그대로 둔다.
            v = i = None
            for cand in guidehdr.HEATER_FIELD_CANDIDATES:
                if cand in status:
                    v = _num(status.get(cand))
                    i = _num(status.get(cand[:-2] + '_I'))
                    break
            volt.append(v)
            curr.append(i)
            continue
        volt.append(_num(status.get(rail + '_V')))
        curr.append(_num(status.get(rail + '_I')))
    if not any(x is not None for x in temps + volt + curr):
        return {}
    return {'temp': temps, 'volt': volt, 'curr': curr}


def _temp_col(field: str) -> str:
    """STATUS 온도 필드 -> CSV 열 이름 (`BACKPLANE_TEMP`->`t_backplane`)."""
    head = field.split('/')[0] if '/' in field else field.split('_')[0]
    return 't_%s' % head.lower()


#: CSV 열 -- 순서 고정.  값 열 이름은 규격 카드/계약 키를 소문자로 따른다.
_COLUMNS = (
    ['utc', 'expstatus', 'valid', 'alive', 'lag_ms']
    + [_temp_col(f) for f in guidehdr.TEMP_MODS]
    + ['v_%s' % r.lower() for r in guidehdr.VOLT_RAILS]
    + ['i_%s' % r.lower() for r in guidehdr.VOLT_RAILS]
    # ⭐ `gauge`/`dewpres_conductron` 는 **진공 결측의 원인을 로그에 남기려고**
    # 있다 (DevNote 11.18-(3)) -- 그냥 빈 `dewpres` 로 두면 나중에 "게이지를
    # 껐던 것" 과 "게이지가 고장난 것" 을 구별할 수 없다.  `dewpres_conductron`
    # 은 게이지 Off 중 모듈이 내던 Conductron 값이고 **헤더로는 안 간다.**
    + ['dewpres', 'gauge', 'dewpres_conductron',
       'ccdtemp', 'dmptemp', 'pt30n1', 'pt30n2', 'charcoal',
       'wallbrd', 'hebox', 'fsatemp', 'fsahum',
       # v1.10 -- `HTROUT` 원천 (`MOD10/HEATERAOUTPUT`, 11.30).  ⚠️ 열이 늘었다:
       # 이전 판 CSV 에 이어 쓰면 헤더와 어긋나니 새 파일에서 시작할 것.
       'htrout']
    + ['ens%d' % n for n in range(1, 8)]
    + ['event'])


class HkMonitor:
    """1분 주기 HK 루프 -- 값의 단일 창구.

    `latest()` 가 백엔드 `sensors()` 의 원천이고(메모리 최신값 -- 운영자
    확정), CSV·스냅샷 파일이 `ics_archon` 쪽 소비 창구다.
    """

    def __init__(self, ctrl, cfg: IcgCfg, *, telem=None,  # noqa: ANN001
                 expstatus=lambda: '', spawn=None) -> None:  # noqa: ANN001
        self.ctrl = ctrl
        #: `HEATER_OUTPUT_FIELD` 결측 경고 래치 -- STATUS 가 왔는데 그 키가 없을 때
        #: 한 번만 (없으면 카드가 조용히 sentinel 로 나가서 아무도 모른다).
        self._warned_htrout = False
        #: 다음 주기 바퀴 시각 (monotonic).  ⭐ `refresh_now()` 가 뒤로
        #: 민다 -- `HKDATA NOW` 뒤에는 60초를 새로 센다 (운영자 2026-09-09).
        self._next_at = 0.0
        #: 히터 **설정** 되읽기 실패를 한 번만 알린다 (`_read_heater_settings`).
        self._warned_htrset = False
        self.cfg = cfg
        self.telem = telem
        self._expstatus = expstatus
        self.radionode = None              # app 이 붙인다
        #: 이온게이지 상태 (`gauge.GaugeState`) -- app 이 붙인다.  ⭐ 꺼진 것을
        #: 아는 동안 `dewpres` 를 **싣지 않기 위해** 본다 (`_tick` 주석).
        self.gauge = None
        self._dew = DewpresDecoder()
        #: ⛔ 되먹임 센서 과열 차단 (운영자 지시 2026-09-06).  한계는
        #: ACF 에서 오고(`HEATER?SENSOR` → `SENSOR?UPPERLIMIT`) 판정은
        #: 이 루프 주기로만 돈다 -- **최후 방어선이지 인터록이 아니다.**
        self.heater_guard = heater.OverTempGuard()
        #: ACF 한계 밖이라고 **이미 알린** RTD 키 -- 경고를 매 바퀴 되풀이하지
        #: 않으려는 래치일 뿐이고, **값은 언제나 그대로 실린다**.
        self._warned_oor: set = set()
        #: 마지막 표본 -- key -> (값, epoch).  `sensors()`/스냅샷의 원천.
        self._sample: dict[str, tuple[object, float]] = {}
        self._ctrl_unit: dict = {}
        self._stop = asyncio.Event()
        self._csv_path = ''
        self._csv = None
        self._writer = None
        self._spawn = spawn
        #: 예열이 끝나는 시각에 한 바퀴를 도는 일회성 작업 (`schedule_warmup_refresh`).
        self._warmup_task = None

    # -- 소비 창구 -----------------------------------------------------------

    def sensors(self) -> dict[str, object]:
        """센서 계약 키 **10개** 중 지금 신선한 것만 (원값) + `hkudate`.

        ⚠️ **개수를 여기 적은 것이 낡았었다** (2026-09-04 정정: 9 -> 10) --
        RTD 6 + `dewpres` + Radionode 3 이다.  `HKDATA` 의 완전성 검사가
        `계약키 교집합 + HKSTALE = 10` 이라 **이 수에 걸려 있다.**  ⭐ 계약 키
        **밖**의 것(`htrout`·`hkudate`)이 함께 나가도 교집합이라 셈은 안 흔들린다.

        guide FITS 헤더가 이걸 그대로 받는다 -- `rawhdr.thermal_header()` 가
        포맷·sentinel 을 맡는다.  **판정 기준은 표본시각 하나**다 --
        Radionode 몫도 `_sample` 에 자기 표본시각으로 들어와 있으므로
        (`_tick`) 여기서 따로 덧붙이지 않는다.  덧붙이면 폴러가 이미
        접은 값이 이 창을 타고 되살아난다.

        ⭐ **`HKUDATE` -- 이 블록 값들의 취득 시각** (규격 5.6절, v1.10).
        **가장 낡은 표본시각**을 준다: 카드는 하나인데 키마다 표본시각이 달라
        어느 하나를 고르면 나머지에 대해 거짓말이 된다.  가장 낡은 것을 실어야
        이 카드가 **실제보다 신선하다고 말하지 않는다**.

        ⛔ **Radionode 몫은 그 셈에서 뺀다** (운영자 확정 2026-09-08):
        *"`HKUDATE` 는 guide unit 에서 측정된 값 중 가장 오래된 값 기준.
        라디오노드 자료는 별도로 시간 기록할 필요 없고 `stale_after` 검사만."*
        ⭐ 근거가 선다 -- Radionode 는 **클라우드를 거치는 남의 계통**이고
        전송주기가 장치마다 다르다(실물 60초·600초).  그것을 섞으면 600초
        장치 하나가 **guide 유닛 전체의 취득 시각을 30분 뒤로** 끌고 간다.
        ⚠️ 대신 그 세 카드(`HEBOX`·`FSATEMP`·`FSAHUM`)의 나이는 `HKUDATE` 로
        읽을 수 없다 -- 신선도는 폴러의 창(`device_interval` x3)이 보증하고,
        원값·표본시각은 HK CSV 에 남는다.
        ⚠️ 살아남은 키가 없으면 **싣지 않는다** -- 호출측이 sentinel `'NC'` 로
        채운다.  빈 블록에 시각만 붙으면 "쟀는데 다 결측" 으로 읽힌다.
        ⛔ 이것이 없어서 **guide 헤더의 `HKUDATE` 가 늘 `NC` 였다** (2026-09-06
        발견).  science 는 `ics_archon/archon/backend.py` 가 같은 셈을 하고
        있었는데 guide 쪽만 빠져 있었다 -- 규격 OI-25 의 *"`HKUDATE` 는 통과
        경로가 섰다"* 는 science 에만 해당했다.  **두 창구가 같은 규칙을 따라야
        한다** (DevNote 11.36).
        """
        now = time.time()
        out: dict[str, object] = {}
        horizon = max(self.cfg.hk.interval * 3, 30.0)
        # ⭐ **Radionode 는 별도 관리다** (운영자 2026-09-08) -- 그 키들은 폴러가
        # **장치의 전송주기 3배**로 이미 걸러서 넘긴다.  여기서 또 자르면 공용
        # 지평선(기본 180초)이 먼저 이겨, 전송주기가 긴 장치(실물 600초)는 늘
        # sentinel 이 된다.  ⛔ 면제가 성립하는 것은 `_tick` 이 **폴러가 접은
        # 키를 `_sample` 에서 빼기** 때문이다 -- 그 짝이 깨지면 안 늙는다.
        own = (self.radionode.all_keys()
               if self.radionode is not None else frozenset())
        # ⛔⛔ **게이지 판정은 읽는 자리에서도 한다** (2026-09-11).  `_tick` 이
        # 표본을 지우는 것만으로는 **주기(60초)만큼 늦는다** -- `VACGAUGE OFF`
        # 를 친 순간 낱말은 즉시 `OFF` 인데 `_sample` 에는 직전 압력이 그대로
        # 남아, 다음 바퀴까지 `VACGAUGE=OFF DEWPRES=<실측값>` 이 나갔다.
        # ⛔ 그것이 바로 `gauge.py` 가 존재하는 이유(*"끈 동안 DEWPRES 를
        # 실으면 안 된다"*)를 깨는 창이다 -- 헤더도 같은 창을 탄다.
        # ⚠️ `_tick` 의 지우기는 **그대로 둔다** -- 그쪽은 CSV 진단(Conductron
        # 값)까지 갈라 적는 자리라 역할이 다르다.
        gate = self.gauge is not None and self.gauge.blocks_dewpres
        oldest: float | None = None
        for key, (val, when) in self._sample.items():
            if key == 'dewpres' and gate:
                continue
            if key in own:
                # ⭐ **Radionode 는 `stale_after` 검사만 받는다** (운영자
                # 2026-09-08) -- 폴러가 자기 창으로 이미 걸렀으므로 여기서 또
                # 자르지 않고, **`HKUDATE` 의 셈에도 넣지 않는다**(아래).
                out[key] = val
                continue
            if now - when <= horizon:
                out[key] = val
                # ⭐ `HKUDATE` 는 **guide 유닛에서 잰 값**만 기준이다.
                oldest = when if oldest is None else min(oldest, when)
        if out and oldest is not None:
            out['hkudate'] = stamp_iso(datetime.datetime.fromtimestamp(
                oldest, datetime.timezone.utc))
        return out

    def ctrl_telemetry(self) -> dict:
        """guide 컨트롤러 나열값 -- `C1_*` 카드의 원천 (10.4절 자리)."""
        return dict(self._ctrl_unit)

    # -- 루프 ----------------------------------------------------------------

    def start(self) -> None:
        self._stop.clear()
        if self._spawn is not None:
            self._task = self._spawn(self.run())

    async def stop(self) -> None:
        self._stop.set()
        # ⚠️ 예약해 둔 예열 바퀴도 접는다 -- 종료 뒤에 왕복이 하나 더 나가면
        # 이미 닫은 연결을 두드린다.
        task = self._warmup_task
        if task is not None and not task.done():
            task.cancel()

    #: ⭐ 예열이 끝난 뒤 이만큼 더 기다렸다가 돈다 [s] -- 경계에서 `warming` 이
    #: 아직 참인 것을 피하는 여유다.
    WARMUP_REFRESH_GRACE = 0.5
    #: 그 바퀴가 빈손이면 다시 보는 간격 [s] 과 횟수.  ⭐ **빈손일 수 있다** --
    #: `VACGAUGE ON` 은 `APPLYDIO09` 라 MOD10 VCPU 가 재시작하고, 그 뒤 첫
    #: 바퀴는 Alive 되감김을 보고 **무조건 결측**이기 때문이다 (`DewpresDecoder`).
    WARMUP_RETRY_WAIT = 3.0
    WARMUP_RETRIES = 2

    def schedule_warmup_refresh(self) -> None:
        """게이지 **예열이 끝나는 시각**에 HK 한 바퀴를 예약한다.

        ⭐ **낱말과 값이 같이 뒤집히게 하는 장치**다 (2026-09-11).  `VACGAUGE`
        는 답을 만드는 순간 `gauge.word` 를 live 로 읽어 예열이 끝나면 곧바로
        `ON` 이 되는데, `DEWPRES` 는 폴링 표본에서 오므로 **다음 주기 바퀴
        (60초)까지** 안 왔다 -- 한 줄 안에서 둘이 어긋났다 (벤치 2026-09-10
        18:12:46~55, DevNote 11.70).

        ⛔ **주기 바퀴를 앞당기지 않는다** -- `_sleep_until` 이 `_next_at` 을
        **뒤로만** 미는 것을 전제로 짜여 있어(깨움 신호를 일부러 안 뒀다),
        앞당기려면 그 전제를 깨야 한다.  대신 `refresh_now()`(= `HKDATA NOW`
        와 같은 함수)를 한 번 부른다 -- 그 함수가 주기 기준도 알아서 민다.
        ⚠️ **켤 때만 부른다** -- 끄는 쪽은 `sensors()` 의 문이 그 자리에서
        막으므로 기다릴 것이 없다.
        """
        if self._spawn is None:
            return                          # 단위 시험 등 -- 띄울 자리가 없다
        task = self._warmup_task
        if task is not None and not task.done():
            task.cancel()                   # 다시 켰다 -- 시계가 새로 섰다
        self._warmup_task = self._spawn(self._warmup_refresh())

    async def _warmup_refresh(self) -> None:
        """예열이 끝나기를 기다렸다가 한 바퀴.  빈손이면 몇 번 더 본다."""
        gauge = self.gauge
        if gauge is None:
            return
        await asyncio.sleep(gauge.warmup_remaining + self.WARMUP_REFRESH_GRACE)
        for attempt in range(self.WARMUP_RETRIES + 1):
            if self._stop.is_set() or gauge.blocks_dewpres:
                return                      # 그새 껐거나 다시 예열 중이다
            try:
                await self.refresh_now()
            except Exception as exc:        # noqa: BLE001 -- 주기 바퀴가 있다
                log.warning('hk round after gauge warmup failed -- %s', exc,
                            extra={'detail': '다음 주기 바퀴가 채운다'})
                return
            if self._sample.get('dewpres') is not None:
                log.info('gauge warmup done: hk round %d brought DEWPRES back',
                         attempt + 1)
                return
            if attempt < self.WARMUP_RETRIES:
                await asyncio.sleep(self.WARMUP_RETRY_WAIT)
        log.warning('gauge warmup done but DEWPRES did not come back after '
                    '%d hk rounds', self.WARMUP_RETRIES + 1,
                    extra={'detail': '다음 주기 바퀴를 기다린다.  ⚠️ VCPU '
                                     '재시작이 길거나 게이지 응답이 없는 것이니 '
                                     '`hkdata now` 로 다시 볼 것'})

    async def run(self) -> None:
        interval = max(self.cfg.hk.interval, 1.0)
        self._next_at = time.monotonic()
        try:
            while not self._stop.is_set():
                await self._await_quiet_link()
                lag_ms = max((time.monotonic() - self._next_at) * 1000.0, 0.0)
                try:
                    await self._tick(lag_ms)
                except Exception:  # noqa: BLE001 -- HK 가 취득을 못 죽인다
                    log.exception('hk round failed -- retrying next round')
                self._next_at = max(self._next_at + interval, time.monotonic())
                if not await self._sleep_until():
                    break
        finally:
            self._write_row({}, event='stop')
            if self._csv is not None:
                self._csv.close()
                self._csv = None

    async def _sleep_until(self) -> bool:
        """다음 바퀴 시각(`_next_at`)까지 잔다.  **정지하면 `False`.**

        ⭐ **깨어날 때마다 `_next_at` 을 다시 본다** -- `refresh_now()` 가 자는
        중에 그것을 뒤로 밀 수 있기 때문이다 (`HKDATA NOW` 뒤 60초).
        ⭐ 미는 쪽은 **늘 뒤로만** 밀므로 이 되풀이는 반드시 끝난다.  ⚠️ 밀린
        만큼 한 번 헛되이 깨어나는데, 60초에 한 번이라 값이 없는 비용이다.
        ⛔ 별도의 깨움 신호(`Event`)를 두지 않은 이유가 이것이다 -- 신호를 두면
        *"세운 쪽과 지운 쪽"* 이 어긋나는 부류가 하나 는다.
        """
        while not self._stop.is_set():
            delay = self._next_at - time.monotonic()
            if delay <= 0:
                return True
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=delay)
            except asyncio.TimeoutError:
                continue                     # 다시 재어 본다
            return False                     # 정지 신호
        return False

    #: ⭐ 주기 바퀴가 **왕복 하나를 비켜 주는 상한** [s] (운영자 2026-09-09).
    #: ⛔ **상한이 있어야 한다** -- guide 는 **연속 취득**이라 *"안 바쁠 때까지"*
    #: 를 곧이곧대로 기다리면 **영영 안 돈다**: HK 가 멈추면 헤더의 온도·진공
    #: 카드가 통째로 sentinel 이 되고, 히터 과열 차단도 같이 멈춘다.
    #: ⭐ 1초면 충분하다 -- guide FETCH 는 8.3 MiB ≈ 0.08 s 고 잠금 상한이
    #: `fetch_timeout` = 1.0 s 다 (DevNote 11.55).
    QUIET_WAIT = 1.0
    #: 위 상한 안에서 다시 보는 간격 [s].
    QUIET_POLL = 0.05

    async def _await_quiet_link(self) -> None:
        """왕복이 도는 중이면 **상한 안에서** 비켜 준다.

        운영자 지시 2026-09-09: *"guide unit 이 바쁠 때에는 60초 폴링 시점이
        되었어도 안 바쁠 때까지 잠시 기다리기."*

        ⭐ **바쁜 것은 취득이 아니라 링크다** -- 연속 취득 중에도 컨트롤러는
        주기(1.251 s)의 대부분이 한가하고 FETCH(≈0.08 s)일 때만 락이 잡힌다.
        그래서 *"취득 중이면 건너뛴다"* 가 아니라 **"왕복 하나가 끝나기를
        기다린다"** 가 맞는 크기다.
        ⛔ **상한을 넘기면 그냥 돈다** (`QUIET_WAIT`) -- 안 그러면 연속 취득이
        HK 를 굶긴다.  ⚠️ 비켜 준 것은 `lag_ms` 에 그대로 남는다(주기 실현
        지연) -- 숨기지 않는다.
        ⚠️ **경합을 막는 장치가 아니다** -- 그것은 락의 몫이고, 이건 예의다.
        """
        ctrl = self.ctrl
        if ctrl is None or not getattr(ctrl, 'link_busy', False):
            return
        deadline = time.monotonic() + self.QUIET_WAIT
        while getattr(ctrl, 'link_busy', False):
            if time.monotonic() >= deadline:
                log.debug('hk: the link stayed busy for %.1fs -- going ahead '
                          'anyway', self.QUIET_WAIT,
                          extra={'detail': '이 바퀴의 왕복은 줄을 선다'})
                return
            await asyncio.sleep(self.QUIET_POLL)

    async def _read_heater_settings(self, now: float) -> None:
        """`HTREN`·`HTRSET`·`HTRFORCE` 를 `RCONFIG` 로 되읽어 `_sample` 에.

        ⭐ **원값을 그대로 담는다** -- `'1'`/`'0'` 은 헤더의
        `rawhdr.format_word()` 가 낱말로 옮긴다.  ⛔ 여기서 `ON`/`OFF` 로
        바꾸면 매핑이 **두 곳**이 된다 (`hkdata._word` 가 유일해야 한다,
        11.14-(1-a)).
        ⚠️ `htrset` 만 수치로 담는다 -- 헤더가 `format_temp()` 로 온도로 싣는다.

        ⚠️ **실패는 조용히 넘긴다** -- ACF 파싱 전이면 *"설정 줄을 모른다"* 가
        나고, 그때는 그 셋이 sentinel 로 가는 것이 맞다.  ⛔ 다만 **한 번은
        알린다**: 계속 조용하면 헤더가 영영 `NC` 인 이유를 아무도 모른다.
        ⚠️ 계약 키 **밖**이라 `HKUDATE`(가장 오래된 측정시각) 셈에 안 낀다 --
        `htrout` 과 같은 자리다 (`sensors()` 머리말).
        """
        if self.ctrl is None:
            return
        # ⛔ **ACF 를 미는 중이면 비킨다** (2026-09-09, DevNote 11.54).
        # `CLEARCONFIG` 직후에는 그 설정 줄이 **아직 없다** -- 읽어 봐야 뜻이
        # 없고, 기동 경로는 이 창을 실제로 만든다 (`app.start()` 가 ACF 적용을
        # `spawn` 하고 곧바로 `hk.start()`).  ⚠️ 다음 바퀴(60초)에 다시 읽으므로
        # 잃는 것은 없다 -- 그 사이 카드는 sentinel 이다.
        if getattr(self.ctrl, 'acf_applying', False):
            log.info('hk: skipping heater readback while the acf is applying',
                     extra={'detail': '다음 바퀴에 다시 읽는다'})
            return
        try:
            got = await heater.read_settings(self.ctrl)
            force = (await self.ctrl.read_config(
                heater.heater_key('FORCE'))).strip()
        except Exception as exc:            # noqa: BLE001 -- HK 를 못 죽인다
            if not self._warned_htrset:
                self._warned_htrset = True
                log.warning('hk: heater settings readback failed -- %s', exc,
                            extra={'detail': 'HTREN·HTRSET·HTRFORCE 카드가 '
                                             'sentinel 로 나간다 (ACF 파싱 '
                                             '전이면 첫 GO 뒤에 풀린다)'})
            return
        self._warned_htrset = False
        if got.get('htren') is not None:
            self._sample['htren'] = (got['htren'], now)
        self._sample['htrforce'] = (force, now)
        try:
            self._sample['htrset'] = (float(got.get('htrset')), now)
        except (TypeError, ValueError):
            pass                            # 못 읽었으면 안 담는다 -> sentinel


    async def refresh_now(self) -> None:
        """`HKDATA NOW` -- **한 바퀴를 지금 돌려** `_sample` 을 갱신한다.

        운영자 지시 2026-09-09: *"`hkdata now` 면 RTD, 진공, Radionode, 히터설정
        모두 되읽기해서 값을 넣어주고, 폴링 값들도 갱신하도록."*

        ⭐ **주기 바퀴와 같은 함수를 쓴다** (`_tick`) -- 따로 만들면 두 경로가
        갈려 *"명령으로 읽은 값과 폴링 값이 다르다"* 가 생긴다.  11.52 가 그
        부류였다.
        ⭐ 그래서 **폴링 값도 함께 갱신된다** -- 다음 FITS 헤더도 이 값을 본다.

        ⚠️ **Radionode 는 충분히 낡았을 때만 다시 친다** (`RADIONODE_NOW_MIN_AGE`)
        -- 쿼터가 분당 10회고, 즉시 조회해도 더 신선해지지 않기 때문이다.
        ⚠️ **CSV 행은 남기되 `hkdata_now` 로 표시한다** -- 실측을 버리지 않으면서
        주기 행과 구별된다 (`lag_ms` 는 주기 실현 지연이라 이 행에서는 뜻이 없다).
        ⏳ ⚠️ **느릴 수 있다** -- `STATUS` + `RCONFIG` 셋은 수 ms 지만 Radionode 를
        실제로 치면 인터넷 왕복(수백 ms~초)이 붙는다.
        """
        # ⭐ **주기 기준을 여기서 민다** (운영자 2026-09-09: *"`HKDATA NOW`
        # 이후 60초 후에 60초 주기 폴링을 하도록"*).  ⛔ 안 밀면 방금 한 바퀴를
        # 돌렸는데 몇 초 뒤 주기 바퀴가 또 돈다 -- 왕복만 쓰고 값은 그대로다.
        # ⚠️ `run()` 의 잠자기가 이 값을 **깨어날 때마다 다시 본다** -- 그래서
        # 자는 중에 밀어도 따라간다 (`_sleep_until`).
        self._next_at = time.monotonic() + max(self.cfg.hk.interval, 1.0)
        if self.radionode is not None and self._radionode_is_old():
            try:
                await self.radionode.poll_now()
            except Exception as exc:      # noqa: BLE001 -- 나머지는 돌아야 한다
                log.warning('hkdata now: radionode poll failed -- %s', exc,
                            extra={'detail': '폴러가 받아 둔 값으로 간다'})
        await self._tick(0.0, note='hkdata_now')

    def _radionode_is_old(self) -> bool:
        r"""Radionode 표본이 `[radionode] now_min_age` 보다 낡았나.

        ⭐ **눈금 하나로 정한다** (운영자 2026-09-09, 기본 60초).  ⛔ 폴링
        주기(`poll_period`)를 쓰면 안 된다 -- 운영자가 그것을 늘릴 수 있는데
        그러면 재조회 기준까지 따라 늘어나 *"방금 값을 원해서 `NOW` 를 쳤는데
        안 친다"* 가 된다.  ⛔ 장치가 알려 주는 `device_interval` 로도 안 된다 --
        **배우기 전에는 `stale_after`(초기값 4000초)의 1/3** 이라 첫 `NOW` 들이
        통째로 막힌다 (2026-09-09 검토에서 잡은 결함이다).

        ⭐ **60초인 근거**: 장치가 그 주기로 올리므로 그 안에 다시 물어도 같은
        값이고, 쿼터가 **분당 10회**라 태우면 **주기 폴링까지 실패해** 세 카드가
        sentinel 이 된다 -- 하려던 것의 정반대다.

        ⚠️ **키 하나라도 낡았으면 친다** -- 주기가 다른 장치가 섞여 있어도
        (실물 60초·600초) 짧은 쪽이 긴 쪽에 묻히지 않는다.  ⭐ 한 번의 호출이
        **장치 전부**를 가져오므로(`get_lst` 한 번, 쿼터 1회) 하나만 낡아도 칠
        값이 있다.
        ⚠️ 표본이 **하나도 없으면 낡은 것으로 본다** -- 첫 `HKDATA NOW` 가
        아무것도 안 하고 끝나면 안 된다.
        """
        rn = self.radionode
        if rn is None:
            return False
        fresh = rn.values_with_time()
        if not fresh:
            return True
        floor = float(getattr(getattr(rn, 'cfg', None), 'now_min_age', 60.0))
        now = time.time()
        return any(now - when >= floor for _v, when in fresh.values())

    async def _tick(self, lag_ms: float, note: str = '') -> None:
        now = time.time()
        row: dict[str, object] = {}
        # 층 1 -- 컨트롤러 STATUS (온도·레일).  접속 실패는 결측일 뿐이다.
        # (`ctrl=None` 은 --backend sim -- 컨트롤러 몫 전부 결측.)
        status: dict = {}
        if self.ctrl is not None:
            try:
                ok = await self.ctrl.refresh_status_live()
                if ok:
                    status = dict(self.ctrl.status_live or {})
            except Exception as exc:  # noqa: BLE001
                log.warning('hk: STATUS query failed -- %s', exc)
        row['valid'] = status.get('VALID', '')
        row['alive'] = status.get('MOD10/VCPU_OUTREG15', '')
        # ⛔ **되먹임 센서 과열 차단** -- 상한을 넘었으면 히터를 끈다.
        # ⚠️ **STATUS 원값으로 판정한다**: 아래 `decode_rtd` 는 한계 밖을
        # 안 내므로(미연결 노이즈를 거르는 규칙) 과열이 `_sample` 에서는
        # 결측으로만 보인다 -- 거기서 보면 영영 안 걸린다.
        # ⚠️ 여기서 끄는 것은 컨트롤러 왕복이라 취득과 락을 다툰다.  그래도
        # 과열 쪽이 먼저다 (운영자 지시 2026-09-06).
        event = ''
        try:
            event = await self.heater_guard.check(self.ctrl, status)
            if event:
                notify(event)          # ⭐ 히터를 껐다 -- 콘솔에 반드시 보인다
        except Exception as exc:  # noqa: BLE001
            log.error('heater over-temperature guard failed -- %s', exc,
                      extra={'detail': '⚠️ 히터가 켜진 채로 남았을 수 있다'})
            notify('heater over-temperature guard failed -- %s '
                   '(the heater may still be on)' % exc)
        unit = ctrl_unit(status)
        self._ctrl_unit = unit
        temps = unit.get('temp') or [None] * len(guidehdr.TEMP_MODS)
        for f, v in zip(guidehdr.TEMP_MODS, temps):
            row[_temp_col(f)] = '' if v is None else v
        for name, prefix in (('volt', 'v'), ('curr', 'i')):
            vals = unit.get(name) or [None] * len(guidehdr.VOLT_RAILS)
            for r, v in zip(guidehdr.VOLT_RAILS, vals):
                row['%s_%s' % (prefix, r.lower())] = '' if v is None else v

        # 층 3 -- RTD (ACF 한계 판정) · DIO (진공).
        acf_cfg = getattr(self.ctrl, 'config', {}) or {}
        rtd = decode_rtd(status)
        for key, val in rtd.items():
            self._sample[key] = (val, now)
            row[key] = val
        # ⛔ **버리지 않는다 -- 알린다.**  한계 밖 값도 위에서 이미 실렸다
        # (운영자 지시 2026-09-06).  여기서는 그 사실만 한 번 알린다: 미연결
        # 채널일 수도 있고 진짜 과열일 수도 있어 **사람이 가를 일**이다.
        oor = out_of_limit(status, acf_cfg)
        for key, (val, lo, hi) in oor.items():
            if key not in self._warned_oor:
                self._warned_oor.add(key)
                text = ('hk: %s = %.2f is outside the acf limits '
                        '[%.2f, %.2f]' % (key, val, lo, hi))
                log.warning('%s', text,
                            extra={'detail': '값은 그대로 싣는다.  미연결 '
                                             '채널인지 실제 이상인지는 배선을 '
                                             '볼 것'})
                notify(text)
        self._warned_oor &= set(oor)   # 돌아온 채널은 다시 알릴 수 있게
        # 히터 출력 -- `HTROUT` (11.30).  ⛔ 결측을 조용히 넘기지 않는다: STATUS 는
        # 왔는데 키가 없으면 FW 판이 다르거나 슬롯이 어긋난 것이라 한 번 알린다.
        htr = _float_or_none(status.get(HEATER_OUTPUT_FIELD))
        if htr is not None:
            self._sample['htrout'] = (htr, now)
            row['htrout'] = htr
            self._warned_htrout = False
        elif status and not self._warned_htrout:
            self._warned_htrout = True
            log.warning('hk: STATUS has no %s -- HTROUT goes out as sentinel',
                        HEATER_OUTPUT_FIELD,
                        extra={'detail': 'FW 1.0.1252 는 HeaterX 슬롯에 이 키를 '
                                         '내야 한다 (DevNote 11.30) -- '
                                         'BACKPLANE_VERSION 과 MOD%d_TYPE 을 볼 것'
                                         % heater.SLOT})
        # ⭐ **히터 설정 셋도 여기서 되읽는다** -- `HTREN`·`HTRSET`·`HTRFORCE`
        # (운영자 2026-09-09).  ⛔ 종전에는 `HKDATA` **응답을 만들 때만** 읽고
        # 버려서, FITS 헤더는 그 셋을 sentinel 로 실었다 -- `HKDATA` 에는 값이
        # 있는데 헤더에는 `NC` 인 어긋남이 벤치에서 드러났다 (2026-09-08).
        # ⚠️ 이 셋은 **`STATUS` 에 없다** -- 설정값이라 `RCONFIG` 되읽기다
        # (`HTROUT` 만 `STATUS` 다).  HK 한 바퀴에 왕복 셋이 는다 -- 주기가
        # 60초라 부담이 아니고, 헤더가 한 원천을 보게 되는 값이 그보다 크다.
        await self._read_heater_settings(now)
        dew = self._dew.decode(status,
                               getattr(self.ctrl, 'apply_count', None))
        gauge = self.gauge
        if gauge is not None and gauge.blocks_dewpres:
            # ⛔⛔ **이온게이지를 끈 것을 아는 동안은 싣지 않는다.**  MKS 356 은
            # 이온게이지를 끄면 **Conductron 열손실 센서 값을 계속 내보내고**
            # (모듈 매뉴얼 p.31), 그 값은 고진공에서 바닥값인데 `rawhdr` 의
            # 인정 범위 [1e-8, 1e+3] 를 **그냥 통과한다** -- 즉 실제 1e-6 인데
            # 헤더에 `1.00e-4` 같은 **정상으로 보이는 틀린 값**이 실린다.
            # ⭐ 운영자 확정: 게이지 Off 중 DEWPRES 는 sentinel `9.99e-9`.
            # ⚠️ 직전 표본도 **즉시 버린다** -- `sensors()` 의 신선도 창이
            # interval*3(기본 180초)이라, 안 버리면 껐는데도 3분간 옛 값이
            # 헤더로 나간다.
            self._sample.pop('dewpres', None)
            row['gauge'] = 'OFF'
            if dew is not None:
                # 진단으로만 남긴다 -- CSV 에는 있고 헤더로는 안 간다.
                row['dewpres_conductron'] = dew
            dew = None
        elif gauge is not None:
            row['gauge'] = gauge.word
        if dew is not None:
            self._sample['dewpres'] = (dew, now)
            row['dewpres'] = dew

        # Radionode -- 폴러의 신선한 값만.  ⚠️ **표본시각은 폴러 것을 그대로
        # 쓴다** (`now` 로 덮으면 낡은 값이 갓 잰 값이 되고, 그 나이를 보고
        # 거르라고 둔 `hk_stale_after` 가 영영 안 걸린다 -- DevNote 9.6).
        if self.radionode is not None:
            fresh = self.radionode.values_with_time()
            for key in self.radionode.all_keys():
                if key in fresh:
                    self._sample[key] = fresh[key]
                    row[key] = fresh[key][0]
                else:
                    # ⛔ **폴러가 접은 키는 여기서도 뺀다.**  안 빼면 옛 표본이
                    # `_sample` 에 남고, `sensors()` 가 Radionode 키를 공용
                    # 지평선에서 면제하므로 **영영 안 늙는다**.
                    self._sample.pop(key, None)

        # AUX ENS1~7 -- **읽기만 한다.  질의는 취득 경로가 한다.**
        #
        # ⚠️ 여기서 `telem.query('AUXSTATUS')` 를 부르면 안 된다 (2026-08-31
        # 교차검토).  `TelemetryRelay` 는 커맨드워드당 대기표가 **하나**라,
        # 취득 사이클의 질의와 겹치면 진 쪽이 시한 처리되고 `_apply_timeout`
        # 이 **TC 가 방금 준 `aux_fields` 를 지운다**(passthrough 기본값).
        # 헤더는 프레임마다 `fits_header_dict()` 를 live 로 읽으므로, 그
        # 뒤의 모든 guide FITS 가 AUX 27장을 sentinel 로 달고 나간다 --
        # TC 는 멀쩡히 답하고 있는데도.  로그 한 줄 얻자고 취득 헤더를
        # 망치는 거래는 성립하지 않는다.
        #
        # 그래서 마지막 응답을 **그냥 읽는다**.  취득이 도는 동안은 사이클
        # 개시 질의가 갱신해 주고, 노출이 없는 동안은 값이 낡는데 그것은
        # `AUXQDATE` 가 헤더에 남기는 사실이라 조용한 오염이 아니다.
        if self.cfg.hk.query_aux and self.telem is not None:
            for k, v in getattr(self.telem, 'aux_fields', ()) or ():
                if k.upper().startswith('ENS'):
                    row[k.lower()] = v

        row['lag_ms'] = '%.0f' % lag_ms
        # ⭐ `note` 는 **왜 이 바퀴가 돌았나** 다 (`hkdata_now`).  ⛔ 과열 차단
        # 사건이 있으면 그것이 먼저다 -- 사건을 표시로 덮으면 안 된다.
        self._write_row(row, event=event or note)
        self._write_latest(now)

    # -- 산출물 ---------------------------------------------------------------

    def _log_dir(self) -> str:
        d = os.path.expanduser(self.cfg.hk.log_dir)
        os.makedirs(d, exist_ok=True)
        return d

    def _write_row(self, row: dict, event: str = '') -> None:
        try:
            path = os.path.join(self._log_dir(),
                                'hk.G.%s.csv' % stamp_compact())
            if path != self._csv_path:
                if self._csv is not None:
                    self._csv.close()
                new = not os.path.exists(path)
                # newline='' -- csv 모듈 규약.  이어 쓰기(a) -- 재기동이 같은
                # 날짜 파일에 이어 붙는다.
                self._csv = open(path, 'a', encoding='utf-8', newline='')
                self._writer = csv.DictWriter(self._csv, fieldnames=_COLUMNS,
                                              extrasaction='ignore')
                if new:
                    self._writer.writeheader()
                self._csv_path = path
            out = {'utc': stamp_iso_ms(utcnow()),
                   'expstatus': self._expstatus(), 'event': event}
            out.update({k: row.get(k, '') for k in _COLUMNS
                        if k not in out})
            self._writer.writerow(out)
            # **행마다 flush** -- `ics_archon` 이 지연 없이 읽는다는 요구.
            self._csv.flush()
        except OSError as exc:
            log.error('hk: CSV write failed -- %s', exc)

    def _write_latest(self, now: float) -> None:
        """원자적 최신 스냅샷 -- `ics_archon.sensors()` 의 소비 창구.

        tmp + `os.replace` 라 읽는 쪽이 반쪽 파일을 볼 수 없다.  값마다
        표본시각(epoch)을 함께 실어 **신선도 판정을 읽는 쪽에 넘긴다.**

        ⚠️ **`sampled` 에 기록 시각을 찍지 않는다.**  `_sample` 이 이미
        키마다 진짜 표본시각을 들고 있고(RTD·진공은 그 바퀴의 측정 시각,
        Radionode 는 폴러의 시각), 여기서 `now` 로 덮으면 읽는 쪽의
        `hk_stale_after` 가 영원히 안 걸린다 (DevNote 9.6 · ics_archon.ini
        의 "이보다 낡은 표본은 버린다" 가 그 셋에만 거짓말이 됐다).
        """
        snap = {'written': now, 'utc': stamp_iso_ms(utcnow()),
                'values': {}, 'sampled': {}}
        for key, (val, when) in sorted(self._sample.items()):
            snap['values'][key] = val
            snap['sampled'][key] = when
        path = os.path.join(self._log_dir(), self.cfg.hk.latest_name)
        tmp = path + '.tmp'
        try:
            with open(tmp, 'w', encoding='utf-8') as fh:
                json.dump(snap, fh)
            os.replace(tmp, path)
        except OSError as exc:
            log.error('hk: snapshot write failed -- %s', exc)
            try:
                os.remove(tmp)
            except OSError:
                pass

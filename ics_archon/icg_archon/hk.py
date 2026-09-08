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
                log.info('진공 VCPU Alive 가 되감겼다 (%s -> %s) -- 이 바퀴에 '
                         '우리가 APPLY 를 보냈으니 예상된 재시작이다.  DEWPRES '
                         '는 이번 바퀴만 결측이고 다음 바퀴에 돌아온다',
                         prev, alive)
                return None
            if not self._warned_restart:
                self._warned_restart = True
                log.warning('진공 VCPU Alive 가 되감겼다 (%s -> %s) -- 진공 '
                            '게이지를 읽는 MOD10 의 VCPU 가 재시작됐다는 '
                            '신호다.  ⚠️ APPLYALL 뿐 아니라 **모듈 하나만 '
                            '적용하는 APPLYMOD09 · APPLYDIO09 도** 그렇다 '
                            '(매뉴얼 p.86) -- 히터 명령(HTREN/HTRSET)과 '
                            '게이지 명령(VACGAUGE)이 이것을 일으킨다.  '
                            'DEWPRES 는 결측으로 싣는다', prev, alive)
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
        oldest: float | None = None
        for key, (val, when) in self._sample.items():
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

    async def run(self) -> None:
        interval = max(self.cfg.hk.interval, 1.0)
        next_at = time.monotonic()
        try:
            while not self._stop.is_set():
                lag_ms = max((time.monotonic() - next_at) * 1000.0, 0.0)
                try:
                    await self._tick(lag_ms)
                except Exception:  # noqa: BLE001 -- HK 가 취득을 못 죽인다
                    log.exception('HK 바퀴 실패 -- 다음 바퀴에 다시 돈다')
                next_at = max(next_at + interval, time.monotonic())
                try:
                    await asyncio.wait_for(
                        self._stop.wait(),
                        timeout=max(next_at - time.monotonic(), 0.0))
                except asyncio.TimeoutError:
                    pass
        finally:
            self._write_row({}, event='stop')
            if self._csv is not None:
                self._csv.close()
                self._csv = None

    async def _tick(self, lag_ms: float) -> None:
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
                log.warning('HK: STATUS 실패 -- %s', exc)
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
            log.error('⛔ 히터 과열 차단이 실패했다 -- %s.  히터가 켜진 채로 '
                      '남았을 수 있다', exc)
            notify('히터 과열 차단이 실패했다 -- %s.  히터가 켜진 채로 남았을 '
                   '수 있다' % exc)
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
                text = ('HK: %s = %.2f 가 ACF 한계 [%.2f, %.2f] 밖이다 -- '
                        '값은 그대로 싣는다.  미연결 채널인지 실제 이상인지는 '
                        '배선을 볼 것' % (key, val, lo, hi))
                log.warning('%s', text)
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
            log.warning('HK: STATUS 에 %s 가 없다 -- HTROUT 카드가 sentinel 로 '
                        '나간다.  FW 1.0.1252 는 HeaterX 슬롯에 이 키를 내야 한다 '
                        '(DevNote 11.30) -- BACKPLANE_VERSION 과 MOD%d_TYPE 을 볼 것',
                        HEATER_OUTPUT_FIELD, heater.SLOT)
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
        self._write_row(row, event=event)
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
            log.error('HK CSV 기록 실패 -- %s', exc)

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
            log.error('HK 스냅샷 기록 실패 -- %s', exc)
            try:
                os.remove(tmp)
            except OSError:
                pass

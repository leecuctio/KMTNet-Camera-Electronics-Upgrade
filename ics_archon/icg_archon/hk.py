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
import json
import logging
import os
import time

from ics_archon import _simpath

_simpath.ensure()

from ics_sim.state import stamp_compact, stamp_iso_ms, utcnow  # noqa: E402

from . import guidehdr  # noqa: E402
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

#: RTD 채널별 ACF 한계 키 -- `MOD<m>/TEMP<c>` -> `MOD<m>\SENSOR<c>...LIMIT`.
def _limit_keys(field: str) -> tuple[str, str]:
    mod, tail = field.split('/')          # 'MOD7', 'TEMPA'
    ch = tail[-1]                          # 'A'|'B'|'C'
    return ('%s\\SENSOR%sLOWERLIMIT' % (mod, ch),
            '%s\\SENSOR%sUPPERLIMIT' % (mod, ch))


def decode_rtd(status: dict, acf_config: dict) -> dict[str, float]:
    """RTD 6채널 -- ACF 한계 밖(미연결·노이즈)은 **내지 않는다**."""
    out: dict[str, float] = {}
    for field, key in RTD_FIELDS:
        raw = status.get(field)
        if raw is None:
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        lo_k, hi_k = _limit_keys(field)
        lo, hi = acf_config.get(lo_k), acf_config.get(hi_k)
        if lo is not None and hi is not None:
            try:
                if not (float(lo) <= val <= float(hi)):
                    # 미연결(-273.2 고정)과 그 노이즈까지 여기서 걸린다.
                    continue
            except ValueError:
                pass
        out[key] = val
    return out


class DewpresDecoder:
    """`MOD10/VCPU_OUTREG0~9` 10글자 + `OUTREG15`(Alive) -> 게이지 원문.

    **정상 판정은 "Alive 가 직전보다 증가" 하나뿐이다.**  0/감소는 VCPU
    재시작 신호(경고), 두 번 연속 불변은 게이지 이상 -- 둘 다 결측.
    """

    def __init__(self) -> None:
        self._alive: int | None = None
        self._flat = 0
        self._warned_restart = False

    def decode(self, status: dict) -> str | None:
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
            if not self._warned_restart:
                self._warned_restart = True
                log.warning('진공 VCPU Alive 가 되감겼다 (%s -> %s) -- VCPU '
                            '재시작(APPLYALL) 신호다.  DEWPRES 는 결측으로 '
                            '싣는다', prev, alive)
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
            # PROVISIONAL -- 필드 이름 미확정 (guidehdr 후보 목록).
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
    + ['dewpres', 'ccdtemp', 'dmptemp', 'pt30n1', 'pt30n2', 'charcoal',
       'wallbrd', 'hebox', 'fsatemp', 'fsahum']
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
        self.cfg = cfg
        self.telem = telem
        self._expstatus = expstatus
        self.radionode = None              # app 이 붙인다
        self._dew = DewpresDecoder()
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
        """센서 계약 키 9개 중 **지금 신선한 것만** (원값).

        guide FITS 헤더가 이걸 그대로 받는다 -- `rawhdr.thermal_header()` 가
        포맷·sentinel 을 맡는다.  Radionode 몫은 폴러의 신선도 규칙을,
        컨트롤러 몫은 "마지막 바퀴에서 읽혔나" 를 따른다.
        """
        now = time.time()
        out: dict[str, object] = {}
        horizon = max(self.cfg.hk.interval * 3, 30.0)
        for key, (val, when) in self._sample.items():
            if now - when <= horizon:
                out[key] = val
        if self.radionode is not None:
            out.update(self.radionode.values())
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
        rtd = decode_rtd(status, getattr(self.ctrl, 'config', {}) or {})
        for key, val in rtd.items():
            self._sample[key] = (val, now)
            row[key] = val
        dew = self._dew.decode(status)
        if dew is not None:
            self._sample['dewpres'] = (dew, now)
            row['dewpres'] = dew

        # Radionode -- 폴러의 신선한 값만.
        if self.radionode is not None:
            for key, val in self.radionode.values().items():
                self._sample[key] = (val, now)
                row[key] = val

        # AUX ENS1~7 -- 로그용 주기 질의 (헤더 몫은 노출 사이클이 따로 질의).
        if self.cfg.hk.query_aux and self.telem is not None:
            try:
                await self.telem.query('AUXSTATUS')
            except Exception as exc:  # noqa: BLE001
                log.debug('HK: AUXSTATUS 질의 실패 -- %s', exc)
            for k, v in getattr(self.telem, 'aux_fields', ()) or ():
                if k.upper().startswith('ENS'):
                    row[k.lower()] = v

        row['lag_ms'] = '%.0f' % lag_ms
        self._write_row(row)
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
        """
        snap = {'written': now, 'utc': stamp_iso_ms(utcnow()),
                'values': {}, 'sampled': {}}
        for key, (val, when) in sorted(self._sample.items()):
            snap['values'][key] = val
            snap['sampled'][key] = when
        if self.radionode is not None:
            for key, val in self.radionode.values().items():
                snap['values'][key] = val
                snap['sampled'][key] = now
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HK 해독·기록 검증 -- 층 3 규칙(`ics_archon/SMC_CLAUDE.md`)의 시험판.

* RTD 결측 판정은 **값이 아니라 ACF 한계**다 (미연결 채널이 그럴듯한 값을
  낸다 -- 실측 -196.9).
* `DEWPRES` 신선도는 **Alive 증가**로만 안다 (짧은 응답은 옛 글자를 남긴다).
* 스냅샷은 원자적이고, 낡은 표본은 `sensors()` 가 내지 않는다.
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import time

import ics_archon  # noqa: F401

from icg_archon import hk as hk_mod  # noqa: E402
from icg_archon.config import IcgCfg  # noqa: E402
from icg_archon.hk import DewpresDecoder, HkMonitor, ctrl_unit, decode_rtd  # noqa: E402


def _status_with_rtd(**vals):  # noqa: ANN003
    base = {
        'MOD7/TEMPA': '-273.2', 'MOD7/TEMPB': '-29.5', 'MOD7/TEMPC': '-196.9',
        'MOD10/TEMPA': '-31.8', 'MOD10/TEMPB': '-27.7', 'MOD10/TEMPC': '7.8',
    }
    base.update(vals)
    return base


#: 실기 ACF 의 한계 (rtd9cal 판 -- SMC_CLAUDE 층 3 표).
ACF_LIMITS = {
    'MOD7\\SENSORALOWERLIMIT': '-230', 'MOD7\\SENSORAUPPERLIMIT': '50',
    'MOD7\\SENSORBLOWERLIMIT': '-180', 'MOD7\\SENSORBUPPERLIMIT': '50',
    'MOD7\\SENSORCLOWERLIMIT': '-180', 'MOD7\\SENSORCUPPERLIMIT': '50',
    'MOD10\\SENSORALOWERLIMIT': '-150', 'MOD10\\SENSORAUPPERLIMIT': '50',
    'MOD10\\SENSORBLOWERLIMIT': '-120', 'MOD10\\SENSORBUPPERLIMIT': '50',
    'MOD10\\SENSORCLOWERLIMIT': '-120', 'MOD10\\SENSORCUPPERLIMIT': '50',
}


def test_rtd_missing_is_judged_by_acf_limits_not_by_value():
    """실측 사례 그대로 -- `-273.2` 고정도, 그럴듯한 `-196.9` 노이즈도
    한계 밖이면 미측정이다."""
    out = decode_rtd(_status_with_rtd(), ACF_LIMITS)
    assert 'charcoal' not in out          # -273.2 -- 한계(-230…50) 밖
    assert 'pt30n2' not in out            # -196.9 -- 그럴듯하지만 한계 밖
    assert out['pt30n1'] == -29.5
    assert out['ccdtemp'] == -27.7
    assert out['dmptemp'] == -31.8
    assert out['wallbrd'] == 7.8


def test_rtd_without_limits_passes_through_with_no_judgement():
    """ACF 한계가 없으면(파싱 전) 값 판정을 지어내지 않는다."""
    out = decode_rtd(_status_with_rtd(), {})
    assert out['charcoal'] == -273.2      # 판정 근거가 없으니 그대로


def _vcpu(text: str, alive: int) -> dict:
    st = {'MOD10/VCPU_OUTREG15': str(alive)}
    for i, ch in enumerate((text + ' ' * 10)[:10]):
        st['MOD10/VCPU_OUTREG%d' % i] = str(ord(ch))
    return st


def test_dewpres_freshness_is_the_alive_counter():
    dec = DewpresDecoder()
    assert dec.decode(_vcpu('6.93e-04  ', 5)) == '6.93e-04'
    # 불변 1회까지는 직전 값 인정, 2회째부터 결측.
    assert dec.decode(_vcpu('6.93e-04  ', 5)) == '6.93e-04'
    assert dec.decode(_vcpu('6.93e-04  ', 5)) is None
    # 증가하면 다시 신선.
    assert dec.decode(_vcpu('7.10e-04  ', 6)) == '7.10e-04'
    # 되감김(재시작 신호)은 결측 + 경고 1회.
    assert dec.decode(_vcpu('7.10e-04  ', 0)) is None


def test_ctrl_unit_follows_the_guide_slot_table():
    """10.4절 -- 온도 8자리 · 레일 8자리, `VALID=0` 은 전 자리 결측 (D4)."""
    status = {'BACKPLANE_TEMP': '33.8'}
    for m in (3, 4, 5, 6, 7, 9, 10):
        status['MOD%d/TEMP' % m] = '30.%d' % m
    for r in ('P2V5', 'P5V', 'P6V', 'N6V', 'P17V', 'N17V', 'P35V'):
        status[r + '_V'] = '1.0'
        status[r + '_I'] = '0.5'
    unit = ctrl_unit(status)
    assert len(unit['temp']) == 8 and unit['temp'][0] == 33.8
    assert len(unit['volt']) == 8
    assert unit['volt'][-1] is None       # HEATER -- 필드 미확정 (PROVISIONAL)
    # HEATER 후보 필드가 있으면 8번째 자리가 찬다.
    status['HEATER_V'] = '28.09'
    status['HEATER_I'] = '0.421'
    unit = ctrl_unit(status)
    assert unit['volt'][-1] == 28.09
    assert unit['curr'][-1] == 0.421
    # VALID=0 -- 전 자리 결측 (기록에는 사실이, 헤더에는 NC 가 남는다).
    status['VALID'] = '0'
    assert ctrl_unit(status) == {}


def test_monitor_writes_csv_and_atomic_latest(tmp_path):
    """한 바퀴 -- CSV 한 행(즉시 flush) + 원자적 스냅샷 + 신선도."""
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    mon = HkMonitor(None, icfg)           # ctrl 없이 -- 컨트롤러 몫 결측

    class _RN:
        def values(self):  # noqa: ANN202
            return {'hebox': 33.2, 'fsatemp': 23.4, 'fsahum': 12.3}
    mon.radionode = _RN()

    asyncio.run(mon._tick(0.0))

    csvs = [p for p in os.listdir(tmp_path) if p.startswith('hk.G.')]
    assert len(csvs) == 1
    with open(tmp_path / csvs[0], encoding='utf-8', newline='') as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]['hebox'] == '33.2'
    assert rows[0]['ccdtemp'] == ''       # 컨트롤러 없음 -> 결측

    snap = json.loads((tmp_path / icfg.hk.latest_name).read_text())
    assert snap['values']['fsahum'] == 12.3
    assert 'ccdtemp' not in snap['values']
    assert abs(snap['written'] - time.time()) < 60

    # sensors() 는 신선한 것만 -- 라디오노드 몫 + (없는) 컨트롤러 몫.
    vals = mon.sensors()
    assert vals['hebox'] == 33.2
    assert 'dewpres' not in vals

    # 낡은 표본은 안 낸다.
    mon._sample['ccdtemp'] = (-100.0, time.time() - 10 * 3600)
    assert 'ccdtemp' not in mon.sensors()


def test_science_backend_reads_the_icg_snapshot(tmp_path):
    """(icg -> ics) 소비 계약 -- `ArchonBackend.sensors()` 가 스냅샷을 읽고
    **신선도는 읽는 쪽이 판정**한다 (표본시각이 값과 함께 실려 있다)."""
    from ics_archon.archon.backend import ArchonBackend

    snap_path = tmp_path / 'hk_latest.G.json'
    now = time.time()
    snap = {'written': now, 'utc': 'x',
            'values': {'ccdtemp': -101.23, 'dewpres': '6.93e-04',
                       'hebox': 33.2, 'wallbrd': 16.8},
            'sampled': {'ccdtemp': now, 'dewpres': now,
                        'hebox': now, 'wallbrd': now - 3600.0}}
    snap_path.write_text(json.dumps(snap), encoding='utf-8')

    import types
    be = object.__new__(ArchonBackend)
    be.acfg = types.SimpleNamespace(hk_latest=str(snap_path),
                                    hk_stale_after=300.0)
    be._warned_sensors = False
    be._warned_stale = False

    got = be.sensors('MK', ('M', 'K'))
    assert got['ccdtemp'] == -101.23
    assert got['dewpres'] == '6.93e-04'
    assert got['hebox'] == 33.2
    assert 'wallbrd' not in got          # 1시간 낡음 -> 버린다

    # 경로가 비면 결측 + (한 번의) 경고 -- 종전 거동.
    be.acfg = types.SimpleNamespace(hk_latest='', hk_stale_after=300.0)
    assert be.sensors('MK', ('M', 'K')) == {}

    # 파일이 없으면 결측 -- icg 가 안 도는 배치도 기동은 된다.
    be.acfg = types.SimpleNamespace(hk_latest=str(tmp_path / 'none.json'),
                                    hk_stale_after=300.0)
    be._warned_sensors = False
    assert be.sensors('MK', ('M', 'K')) == {}


def test_csv_columns_are_stable():
    """열 구성은 소비 계약이다 -- 바꾸려면 ics_archon 쪽 독자와 함께."""
    cols = hk_mod._COLUMNS
    assert cols[:5] == ['utc', 'expstatus', 'valid', 'alive', 'lag_ms']
    for key in ('t_backplane', 't_mod9', 'v_heater', 'i_p2v5', 'dewpres',
                'ccdtemp', 'hebox', 'fsahum', 'ens7', 'event'):
        assert key in cols

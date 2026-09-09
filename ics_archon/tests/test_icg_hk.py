#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HK 해독·기록 검증 -- 층 3 규칙(`ics_archon/SMC_CLAUDE.md`)의 시험판.

* ⛔ **RTD 실측값은 버리지 않는다** (운영자 지시 2026-09-06) -- 한계 밖이어도
  그대로 싣고, 한계 밖이라는 **사실만 따로 알린다**(`out_of_limit`).  종전의
  한계 폐기는 과열을 센서 결측으로 위장시켰다.
* `DEWPRES` 신선도는 **Alive 증가**로만 안다 (짧은 응답은 옛 글자를 남긴다).
* 스냅샷은 원자적이고, 낡은 표본은 `sensors()` 가 내지 않는다.
"""

from __future__ import annotations

import asyncio
import csv
import datetime
import json
import os
import time

import ics_archon  # noqa: F401

from ics_sim import rawhdr  # noqa: E402

from icg_archon import hk as hk_mod  # noqa: E402
from icg_archon.config import IcgCfg  # noqa: E402
from icg_archon.hk import DewpresDecoder, HkMonitor, ctrl_unit, decode_rtd  # noqa: E402


def _status_with_rtd(**vals):  # noqa: ANN003
    base = {
        'MOD7/TEMPA': '-273.2', 'MOD7/TEMPB': '-29.5', 'MOD7/TEMPC': '-196.9',
        'MOD10/TEMPA': '-31.8', 'MOD10/TEMPB': '-27.7', 'MOD10/TEMPC': '7.8',
        # FW 1.0.1252 HeaterX 출력 형식 (%0.3f) -- 픽스처는 증거가 아니라 FW 형식을 따른다 (11.30)
        'MOD10/HEATERAOUTPUT': '0.000', 'MOD10/HEATERBOUTPUT': '0.000',
        'HEATER_V': '28.104', 'HEATER_I': '0.052',
    }
    base.update(vals)
    return base


#: 실기 ACF 의 한계 (rtd9cal 판 -- SMC_CLAUDE 층 3 표).
#: ⚠️ `parse_acf` 가 내는 모양(`/`)으로 적는다 -- 원문의 역슬래시로 적으면
#: 조회가 다 빗나가서 "한계 판정이 죽은" 상태를 시험이 통과시킨다.
ACF_LIMITS = {
    'MOD7/SENSORALOWERLIMIT': '-230', 'MOD7/SENSORAUPPERLIMIT': '50',
    'MOD7/SENSORBLOWERLIMIT': '-180', 'MOD7/SENSORBUPPERLIMIT': '50',
    'MOD7/SENSORCLOWERLIMIT': '-180', 'MOD7/SENSORCUPPERLIMIT': '50',
    'MOD10/SENSORALOWERLIMIT': '-150', 'MOD10/SENSORAUPPERLIMIT': '50',
    'MOD10/SENSORBLOWERLIMIT': '-120', 'MOD10/SENSORBUPPERLIMIT': '50',
    'MOD10/SENSORCLOWERLIMIT': '-120', 'MOD10/SENSORCUPPERLIMIT': '50',
}


def test_rtd_limits_use_the_parsed_acf_key_form():
    """⭐ 한계 키는 **`parse_acf` 가 내는 모양**이어야 한다.

    ACF 원문은 `MOD7\\SENSORALOWERLIMIT`(역슬래시)인데 `parse_acf` 가
    읽으면서 `/` 로 정규화한다.  역슬래시로 조회하면 **한 채널도 안 맞아
    한계 판정이 통째로 죽고** 미연결 채널의 그럴듯한 값이 그대로 실린다
    (2026-08-31 교차검토에서 실제로 그 상태였다).  그래서 손으로 적은
    dict 가 아니라 **실물 ACF 를 파싱한 결과**를 먹인다.
    """
    import os

    from ics_archon.archon.controller import ArchonController
    from icg_archon.config import IcgCfg

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    acf = os.path.join(root, 'acf', 'KMTK_GUI_162_STA0201_R2618.acf')
    icfg = IcgCfg()
    icfg.acf = {'G': acf}
    ctrl = ArchonController('G', icfg)
    ctrl.parse_acf(acf)

    # 파싱된 표에 한계 키가 실제로 잡혀야 한다 (없으면 아래 판정이 무의미).
    lo, hi = hk_mod._limit_keys('MOD7/TEMPA')
    assert hk_mod._limit_of(ctrl.config, lo) is not None, \
        '한계 키를 못 찾는다 -- 구분자 표기를 확인할 것'
    assert hk_mod._limit_of(ctrl.config, hi) is not None

    # ⛔ 값은 **버리지 않는다** -- 한계 밖도 그대로 나온다.
    out = decode_rtd(_status_with_rtd())
    assert out['charcoal'] == -273.2      # 미연결이지만 실측값 그대로
    assert out['pt30n2'] == -196.9
    assert out['pt30n1'] == -29.5
    assert out['ccdtemp'] == -27.7
    # ⭐ 한계 판정은 **알리는 쪽**이 한다 -- 실물 ACF 로 두 채널이 잡혀야 한다.
    oor = hk_mod.out_of_limit(_status_with_rtd(), ctrl.config)
    assert set(oor) == {'charcoal', 'pt30n2'}, oor


def test_a_reading_outside_the_acf_limits_is_still_published():
    """⛔ **한계 밖이라고 버리지 않는다** (운영자 지시 2026-09-06).

    실측 사례 그대로 -- `-273.2` 고정도, 그럴듯한 `-196.9` 노이즈도 **값이
    왔으면 값이다**.  버리면 진짜 이상(예: 히터 과열)이 센서 결측으로 위장된다.
    """
    out = decode_rtd(_status_with_rtd(), ACF_LIMITS)
    assert out['charcoal'] == -273.2      # 한계(-230…50) 밖이지만 실린다
    assert out['pt30n2'] == -196.9
    assert out['pt30n1'] == -29.5
    assert out['ccdtemp'] == -27.7
    assert out['dmptemp'] == -31.8
    assert out['wallbrd'] == 7.8


def test_out_of_limit_reports_without_dropping():
    """⭐ **버리는 것과 알리는 것을 가른다** -- 한계 판정은 여기만 한다."""
    oor = hk_mod.out_of_limit(_status_with_rtd(), ACF_LIMITS)
    assert set(oor) == {'charcoal', 'pt30n2'}
    assert oor['pt30n2'][0] == -196.9     # 값·하한·상한을 함께 낸다
    assert oor['pt30n2'][1:] == (-180.0, 50.0)


def test_out_of_limit_says_nothing_without_limits():
    """한계를 못 읽으면(파싱 전) **판정을 지어내지 않는다.**"""
    assert hk_mod.out_of_limit(_status_with_rtd(), {}) == {}


def test_an_overheating_reading_is_not_disguised_as_a_missing_sensor():
    """⛔⛔ **이것이 폐기를 걷은 이유다.**

    히터 과열로 `dmptemp` 가 상한(50)을 넘으면, 종전에는 키가 사라져 헤더에서
    *"센서가 죽었다"* 로만 보였다.  이제는 값이 그대로 실려 과열이 보인다.
    """
    st = _status_with_rtd(**{'MOD10/TEMPA': '61.5'})
    out = decode_rtd(st, ACF_LIMITS)
    assert out['dmptemp'] == 61.5, '과열이 결측으로 위장됐다'
    assert 'dmptemp' in hk_mod.out_of_limit(st, ACF_LIMITS)


def test_rtd_passes_through_with_no_judgement():
    """⭐ 판정 자체가 없다 -- ACF 를 주든 안 주든 값은 그대로다."""
    out = decode_rtd(_status_with_rtd(), {})
    assert out['charcoal'] == -273.2
    assert decode_rtd(_status_with_rtd()) == out


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
        """폴러 대역 -- **표본시각을 함께** 낸다 (실물과 같은 계약)."""

        def values_with_time(self):  # noqa: ANN202
            t = time.time()
            return {'hebox': (33.2, t), 'fsatemp': (23.4, t),
                    'fsahum': (12.3, t)}

        def values(self):  # noqa: ANN202
            return {k: v for k, (v, _t) in self.values_with_time().items()}

        def all_keys(self):  # noqa: ANN202
            # ⭐ 계약의 일부다 -- `hk` 가 *"이 키는 폴러 소관"* 을 알아야
            # 공용 지평선에서 면제하고, 폴러가 접은 키를 `_sample` 에서 뺀다.
            return frozenset(('hebox', 'fsatemp', 'fsahum'))
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


def test_radionode_sample_time_survives_into_the_snapshot(tmp_path):
    """⭐ 폴러의 **진짜 표본시각**이 스냅샷까지 살아가야 한다.

    HK 틱 시각으로 다시 도장을 찍으면 500초 묵은 값이 "방금 잰 값" 이 되어
    읽는 쪽 `hk_stale_after` 가 영영 안 걸린다 (2026-08-31 교차검토 --
    DevNote 9.6 이 막겠다고 한 바로 그 경로였다).
    """
    from icg_archon.config import RadionodeCfg, RadionodeDevice
    from icg_archon.radionode import RadionodeClient

    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    rn = RadionodeClient(RadionodeCfg(
        backend='openapi', stale_after=600.0,
        devices=(RadionodeDevice(alias='hebox', mac='x', keys=('hebox',)),)))
    # 500초 전에 잰 표본 -- 폴러 한도(600) 안이지만 오래됐다.
    rn._latest['hebox'] = (33.2, time.monotonic() - 500.0)

    mon = HkMonitor(None, icfg)
    mon.radionode = rn
    asyncio.run(mon._tick(0.0))

    snap = json.loads((tmp_path / icfg.hk.latest_name).read_text())
    age = snap['written'] - snap['sampled']['hebox']
    assert 450 < age < 550, '표본 나이가 사라졌다 (age=%.1f)' % age

    # science 쪽 한도(300)를 대면 걸러져야 한다.
    import types

    from ics_archon.archon.backend import ArchonBackend
    be = object.__new__(ArchonBackend)
    be.acfg = types.SimpleNamespace(
        hk_latest=str(tmp_path / icfg.hk.latest_name), hk_stale_after=300.0)
    be._warned_sensors = False
    be._warned_stale = False
    assert 'hebox' not in be.sensors('MK', ('M', 'K'))


def test_sim_radionode_values_never_reach_the_header(tmp_path):
    """`backend=sim` 의 고정 상수는 헤더 경로로 나가면 안 된다.

    아카이브에 들어간 뒤에는 파일만 보고 잰 값인지 못 가른다 -- 규격
    5.6·5.8 이 이 3장을 실측 계통으로 규정하므로, 모르면 sentinel 이
    정직하다 (2026-08-31 교차검토).
    """
    from icg_archon.config import RadionodeCfg
    from icg_archon.radionode import RadionodeClient

    rn = RadionodeClient(RadionodeCfg(backend='sim'))
    assert rn.values() == {}
    assert rn.values_with_time() == {}
    assert rn.sim_values()['hebox'] == 33.21     # 배선 확인용으로만 남는다

    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    mon = HkMonitor(None, icfg)
    mon.radionode = rn
    asyncio.run(mon._tick(0.0))
    snap = json.loads((tmp_path / icfg.hk.latest_name).read_text())
    assert 'hebox' not in snap['values']
    assert 'hebox' not in mon.sensors()


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


def test_sensors_carries_hkudate_as_the_oldest_sample_time(tmp_path):
    """⛔ **guide 헤더의 `HKUDATE` 가 늘 `NC` 였다** (2026-09-06 발견).

    science 는 `ArchonBackend.sensors()` 가 가장 낡은 표본시각을 실었는데 guide
    쪽 `HkMonitor.sensors()` 는 그것을 안 해서, `rawhdr.thermal_header()` 가
    `s.get('hkudate')` 를 못 찾아 sentinel 로 나갔다.  규격 OI-25 의 *"`HKUDATE`
    는 통과 경로가 섰다"* 는 science 에만 해당했던 것이다 (DevNote 11.36).

    지키는 것 셋: ① 실린다 ② **가장 낡은** 표본시각이다(어느 하나를 고르면
    나머지에 대해 거짓말이 된다) ③ 신선한 값이 하나도 없으면 **안 싣는다**.
    """
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    mon = HkMonitor(None, icfg)

    now = time.time()
    # 두 표본의 시각을 일부러 벌린다 -- 60 s 와 5 s 전.
    mon._sample['ccdtemp'] = (-100.0, now - 60.0)      # noqa: SLF001
    # ⚠️ 둘 다 **guide 유닛** 키여야 한다 -- Radionode 키는 이 셈에서 빠진다
    # (운영자 2026-09-08, 아래 시험).
    mon._sample['dmptemp'] = (-31.8, now - 5.0)        # noqa: SLF001

    vals = mon.sensors()
    assert 'hkudate' in vals, vals
    stamp = str(vals['hkudate'])
    assert len(stamp) == 19 and stamp[10] == 'T', stamp      # 초 단위 19자, Z 없음
    # ② 가장 낡은 쪽(60 s 전)이어야 한다.
    want = datetime.datetime.fromtimestamp(
        now - 60.0, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    assert stamp == want, (stamp, want)
    # 헤더까지 실제로 간다 -- 형식은 rawhdr 이 맡는다.
    assert rawhdr.thermal_header(vals)['HKUDATE'] == want

    # ③ 신선한 것이 없으면 안 싣는다 (빈 블록에 시각만 붙으면 안 된다).
    stale = HkMonitor(None, icfg)
    stale._sample['ccdtemp'] = (-100.0, now - 86400.0)  # noqa: SLF001
    assert stale.sensors() == {}
    assert rawhdr.thermal_header(stale.sensors())['HKUDATE'] == rawhdr.WORD_NC


def test_htrout_is_sampled_from_mod10_heateraoutput(tmp_path, caplog):
    """`HTROUT` 의 원천 -- STATUS `MOD10/HEATERAOUTPUT` (DevNote 11.30).

    FW 1.0.1252 가 HeaterX 슬롯에 이 키를 내는 것을 펌웨어 이미지로 확인했다
    (매뉴얼 p.48 'Heater only' 는 오기).  키가 있으면 `_sample['htrout']` 로
    들어가 스냅샷을 타고 `ics_archon.sensors()` 로 흘러가야 하고, STATUS 는
    왔는데 키가 없으면 **한 번** 경고하고 카드는 sentinel 로 나가야 한다 --
    조용히 넘어가면 아무도 모른다.
    """
    import logging

    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False

    class _Ctrl:
        """STATUS 만 내는 컨트롤러 대역."""

        def __init__(self, status):  # noqa: ANN001
            self.status_live = status
            self.config = {}

        async def refresh_status_live(self):  # noqa: ANN202
            return True

    # ① 키가 있다 -- 값이 그대로 표본이 되고 스냅샷에 실린다.
    mon = HkMonitor(_Ctrl(_status_with_rtd(**{'MOD10/HEATERAOUTPUT': '3.512'})), icfg)
    asyncio.run(mon._tick(0.0))
    assert mon._sample['htrout'][0] == 3.512
    assert mon.sensors()['htrout'] == 3.512
    snap = json.loads((tmp_path / icfg.hk.latest_name).read_text())
    assert snap['values']['htrout'] == 3.512
    assert 'htrout' in snap['sampled']
    # 계약 키 셈에는 안 들어간다 -- 10개 밖 (hkwire 의 HKSTALE 규칙과 같다).
    assert 'htrout' not in dict(hk_mod.RTD_FIELDS).values()

    # ② STATUS 는 왔는데 키가 없다 -- 표본 없음 + 경고 한 번(래치).
    status = _status_with_rtd()
    status.pop('MOD10/HEATERAOUTPUT')
    mon2 = HkMonitor(_Ctrl(status), icfg)
    with caplog.at_level(logging.WARNING, logger='icg_archon.hk'):
        asyncio.run(mon2._tick(0.0))
        asyncio.run(mon2._tick(0.0))
    assert 'htrout' not in mon2._sample
    warns = [r for r in caplog.records if 'HEATERAOUTPUT' in r.getMessage()]
    assert len(warns) == 1, '결측 경고는 한 번만 (래치)'

    # ③ 컨트롤러가 없으면(sim) 경고도 없다 -- 결측이 정상이다.
    mon3 = HkMonitor(None, icfg)
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger='icg_archon.hk'):
        asyncio.run(mon3._tick(0.0))
    assert not [r for r in caplog.records if 'HEATERAOUTPUT' in r.getMessage()]


def test_hkudate_ignores_radionode_samples(tmp_path):
    """⛔ **`HKUDATE` 는 guide 유닛 측정값만 기준**이다 (운영자 2026-09-08).

    *"라디오노드 자료는 별도로 시간 기록할 필요 없고 `stale_after` 검사만."*

    ⭐ 근거: Radionode 는 클라우드를 거치는 남의 계통이고 전송주기가 장치마다
    다르다(실물 60초·600초).  섞으면 600초 장치 하나가 **guide 유닛 전체의
    취득 시각을 30분 뒤로** 끌고 간다 -- 카드가 실제보다 낡았다고 말하게 된다.
    ⚠️ 값은 그대로 실린다.  빠지는 것은 **시각 셈**뿐이다.
    """
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    mon = HkMonitor(None, icfg)

    class _RN:
        def all_keys(self):  # noqa: ANN202
            return frozenset(('hebox', 'fsatemp', 'fsahum'))
    mon.radionode = _RN()

    now = time.time()
    mon._sample['ccdtemp'] = (-100.0, now - 30.0)      # noqa: SLF001  guide
    mon._sample['hebox'] = (21.5, now - 1800.0)        # noqa: SLF001  30분 전
    vals = mon.sensors()

    assert vals['hebox'] == 21.5, '값은 실려야 한다'
    want = datetime.datetime.fromtimestamp(
        now - 30.0, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    assert str(vals['hkudate']) == want, (vals['hkudate'], want)


def test_radionode_keys_are_exempt_from_the_shared_horizon(tmp_path):
    """⭐ 공용 지평선(기본 180초)이 Radionode 를 두 번 자르면 안 된다.

    폴러가 **장치 전송주기 x3** 으로 이미 걸러서 넘긴다.  여기서 또 자르면
    주기가 긴 장치(실물 600초)는 늘 sentinel 이다.
    ⛔ 면제가 성립하는 것은 `_tick` 이 **폴러가 접은 키를 `_sample` 에서 빼기**
    때문이다 -- 그 짝이 깨지면 값이 영영 안 늙는다 (아래에서 함께 본다).
    """
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    icfg.hk.interval = 60.0                            # 지평선 180초
    mon = HkMonitor(None, icfg)

    published = {'hebox': (21.5, time.time() - 900.0)}     # 15분 전

    class _RN:
        def all_keys(self):  # noqa: ANN202
            return frozenset(('hebox', 'fsatemp', 'fsahum'))

        def values_with_time(self):  # noqa: ANN202
            return dict(published)

        def values(self):  # noqa: ANN202
            return {k: v for k, (v, _t) in published.items()}
    mon.radionode = _RN()

    asyncio.run(mon._tick(0.0))                        # noqa: SLF001
    assert mon.sensors()['hebox'] == 21.5, '180초 지평선이 잘라 버렸다'

    # ⛔ 폴러가 접으면 `_sample` 에서도 빠져야 한다 -- 안 빼면 안 늙는다.
    published.clear()
    asyncio.run(mon._tick(0.0))                        # noqa: SLF001
    assert 'hebox' not in mon.sensors(), '폴러가 접었는데 헤더에 남았다'


def test_heater_settings_reach_the_header_not_just_hkdata(tmp_path):
    """⛔ `HTREN`·`HTRSET`·`HTRFORCE` 가 **FITS 헤더에도** 실려야 한다.

    ⭐ 벤치가 잡은 어긋남 (2026-09-08): `HKDATA` 응답에는 `HTREN=OFF
    HTRSET=+0.00 HTRFORCE=OFF` 가 있는데 **헤더는 셋 다 sentinel** 이었다.
    원인은 값을 못 읽어서가 아니라 **경로가 둘로 갈려서** -- `hkdata` 가 응답을
    만들 때만 `RCONFIG` 로 읽고 버렸고, 헤더가 보는 `sensors()` 에는 `htrout`
    하나뿐이었다.
    ⚠️ 셋은 **`STATUS` 에 없다** (설정값이라 `RCONFIG`) -- HK 한 바퀴에 왕복
    셋이 느는 것이 이 고침의 값이다.
    ⭐ **원값을 그대로 담는다** -- `'1'`/`'0'` 은 헤더의 `format_word()` 가
    낱말로 옮긴다 (매핑을 두 곳에 두지 않는다, 11.14-(1-a)).
    """
    from ics_sim import rawhdr

    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False

    class _Ctrl:
        """STATUS + 히터 설정 `RCONFIG` 를 내는 컨트롤러 대역."""

        def __init__(self):  # noqa: ANN204
            self.status_live = _status_with_rtd()
            self.config = {}

        async def refresh_status_live(self):  # noqa: ANN202
            return True

        async def read_config(self, key):  # noqa: ANN001, ANN202
            return {'MOD10\\HEATERAENABLE': '1',
                    'MOD10\\HEATERATARGET': '-95.25',
                    'MOD10\\HEATERAFORCE': '0'}[key]

    mon = HkMonitor(_Ctrl(), icfg)
    asyncio.run(mon._tick(0.0))                            # noqa: SLF001

    got = mon.sensors()
    assert got['htren'] == '1' and got['htrforce'] == '0', got
    assert got['htrset'] == -95.25, got

    cards = rawhdr.thermal_header(got)
    assert cards['HTREN'] == 'ON', cards['HTREN']
    assert cards['HTRFORCE'] == 'OFF', cards['HTRFORCE']
    assert cards['HTRSET'] == '-95.25', cards['HTRSET']


def test_a_failed_heater_read_back_leaves_sentinels_and_warns_once(tmp_path):
    """⚠️ 되읽기가 실패하면 **sentinel 이 맞다** -- 다만 한 번은 알린다.

    ACF 파싱 전에는 *"설정 줄을 모른다"* 가 난다.  ⛔ 조용히 넘어가면 헤더가
    영영 `NC` 인 이유를 아무도 모른다.
    """
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False

    class _Blind:
        def __init__(self):  # noqa: ANN204
            self.status_live = _status_with_rtd()
            self.config = {}

        async def refresh_status_live(self):  # noqa: ANN202
            return True

        async def read_config(self, key):  # noqa: ANN001, ANN202
            raise RuntimeError("설정 줄 '%s' 을 모른다" % key)

    mon = HkMonitor(_Blind(), icfg)
    asyncio.run(mon._tick(0.0))                            # noqa: SLF001
    got = mon.sensors()
    assert 'htren' not in got and 'htrset' not in got, got
    assert mon._warned_htrset is True                      # noqa: SLF001


# -- 주기 바퀴가 링크를 비켜 준다 (운영자 2026-09-09) -----------------------


class _Link:
    """`link_busy` 만 흉내내는 컨트롤러 표면."""

    def __init__(self, busy) -> None:  # noqa: ANN001
        self.link_busy = busy


def _quiet(monitor, busy_for):  # noqa: ANN001, ANN202
    """`_await_quiet_link()` 가 실제로 기다린 시간 [s]."""
    import time as _t

    ctrl = _Link(True)
    monitor.ctrl = ctrl

    async def run():  # noqa: ANN202
        if busy_for is not None:
            async def release():  # noqa: ANN202
                await asyncio.sleep(busy_for)
                ctrl.link_busy = False
            asyncio.ensure_future(release())
        t0 = _t.monotonic()
        await monitor._await_quiet_link()          # noqa: SLF001
        return _t.monotonic() - t0

    return asyncio.run(run())


def test_the_cycle_yields_to_a_round_trip_in_flight(tmp_path):
    """⭐ 왕복이 도는 중이면 **끝나기를 기다린다** (운영자 2026-09-09).

    ⭐ **바쁜 것은 취득이 아니라 링크다** -- 연속 취득 중에도 컨트롤러는
    주기(1.251 s)의 대부분이 한가하고 FETCH(≈0.08 s)일 때만 락이 잡힌다.
    그래서 *"취득 중이면 건너뛴다"* 가 아니라 **"왕복 하나가 끝나기를
    기다린다"** 가 맞는 크기다.
    """
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    mon = HkMonitor(None, icfg)
    mon.QUIET_POLL = 0.01
    waited = _quiet(mon, busy_for=0.08)
    assert 0.05 <= waited < mon.QUIET_WAIT, waited


def test_a_busy_link_can_never_starve_the_cycle(tmp_path):
    """⛔ **상한을 넘기면 그냥 돈다** -- 이것이 이 시험의 존재 이유다.

    guide 는 **연속 취득**이라 *"안 바쁠 때까지 기다린다"* 를 곧이곧대로 쓰면
    **HK 가 영영 안 돈다**: 헤더의 온도·진공 카드가 통째로 sentinel 이 되고,
    ⛔ **히터 과열 차단도 같이 멈춘다**(그것이 HK 바퀴에 얹혀 있다).
    ⚠️ 비켜 준 것은 `lag_ms` 에 남으므로 숨겨지지 않는다.
    """
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    mon = HkMonitor(None, icfg)
    mon.QUIET_WAIT, mon.QUIET_POLL = 0.15, 0.01
    waited = _quiet(mon, busy_for=None)            # 영원히 바쁘다
    assert mon.QUIET_WAIT <= waited < mon.QUIET_WAIT + 0.15, waited


def test_an_idle_link_is_not_waited_for(tmp_path):
    """⚠️ 한가하면 **한 틱도 안 쉰다** -- 군더더기 지연을 만들지 않는다."""
    import time as _t

    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    mon = HkMonitor(_Link(False), icfg)
    t0 = _t.monotonic()
    asyncio.run(mon._await_quiet_link())           # noqa: SLF001
    assert _t.monotonic() - t0 < 0.02


def test_a_controller_without_the_flag_is_not_waited_for(tmp_path):
    """⚠️ 시뮬 백엔드처럼 `link_busy` 가 없는 표면에서도 **그냥 돈다**.

    ⛔ `getattr` 기본값이 참이면 시뮬이 매 바퀴 상한만큼 멈춘다.
    """
    import time as _t

    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    mon = HkMonitor(object(), icfg)
    t0 = _t.monotonic()
    asyncio.run(mon._await_quiet_link())           # noqa: SLF001
    assert _t.monotonic() - t0 < 0.02


# -- HKDATA NOW 의 Radionode 제동 · 주기 기준 밀기 (운영자 2026-09-09) -------


class _RnCfg:
    def __init__(self, now_min_age) -> None:  # noqa: ANN001
        self.now_min_age = float(now_min_age)


class _Rn:
    """표본시각과 `cfg.now_min_age` 만 흉내내는 Radionode 대역."""

    def __init__(self, samples, now_min_age=60.0) -> None:  # noqa: ANN001
        self._samples = dict(samples)       # key -> (값, 표본시각 epoch)
        self.cfg = _RnCfg(now_min_age)
        self.polls = 0

    def values_with_time(self) -> dict:  # noqa: ANN201
        return dict(self._samples)

    def all_keys(self):  # noqa: ANN201
        return frozenset(self._samples)

    async def poll_now(self) -> None:  # noqa: ANN202
        self.polls += 1


def _mon(tmp_path, rn=None):  # noqa: ANN001, ANN202
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    m = HkMonitor(None, icfg)
    m.radionode = rn
    return m


def test_radionode_is_not_hit_again_inside_its_own_upload_interval(tmp_path):
    """⭐ **전송주기 안에서는 다시 안 친다** (운영자 2026-09-09).

    ⛔ 근거 둘: ① 쿼터가 **api_key 당 분당 10회**라 태우면 **주기 폴링까지
    실패해** 세 카드가 sentinel 이 된다 -- 하려던 것의 정반대다.  ② ⭐ 장치가
    `device_interval` 마다 올리므로 **그 안에 다시 물어도 같은 값**이다.
    ⚠️ 기준을 상수로 박으면 안 된다 -- 실물 장치가 60초·600초로 갈린다.
    """
    now = time.time()
    m = _mon(tmp_path, _Rn({'hebox': (22.2, now - 10.0)}, now_min_age=60.0))
    assert m._radionode_is_old() is False           # noqa: SLF001


def test_radionode_is_hit_once_the_interval_has_passed(tmp_path):
    """⭐ 전송주기가 지났으면 **친다** -- 그때는 새 값이 있을 수 있다."""
    now = time.time()
    m = _mon(tmp_path, _Rn({'hebox': (22.2, now - 61.0)}, now_min_age=60.0))
    assert m._radionode_is_old() is True            # noqa: SLF001


def test_one_stale_key_is_enough_to_hit_the_cloud(tmp_path):
    """⚠️ **키 하나라도 낡았으면 친다** -- 가장 신선한 것에 맞추지 않는다.

    ⭐ 한 번의 호출이 **장치 전부**를 가져오므로(`get_lst` 한 번, 쿼터 1회)
    하나만 낡아도 칠 값이 있다.  ⛔ 반대로 *"가장 낡은 것이 아직 젊으면 안
    친다"* 로 짜면, 늘 신선한 장치 하나가 **나머지를 영영 막는다**.
    """
    now = time.time()
    rn = _Rn({'hebox': (22.2, now - 90.0),       # 낡았다
              'fsatemp': (21.0, now - 5.0)},     # 갓 받았다
             now_min_age=60.0)
    assert _mon(tmp_path, rn)._radionode_is_old() is True   # noqa: SLF001


def test_the_threshold_comes_from_the_ini_not_the_poll_period(tmp_path):
    """⛔ 기준은 **`[radionode] now_min_age`** 다 -- 폴링 주기가 아니다.

    ⭐ 운영자 지적 2026-09-09: *"폴링 주기를 60초보다 늘릴 수 있으니 Radionode
    갱신 기준은 폴링주기로 하면 안 된다."*  ⚠️ 두 눈금은 **뜻이 다르다** --
    하나는 *"얼마나 자주 받아 두나"*, 다른 하나는 *"다시 물어볼 만큼 낡았나"* 다.
    ⛔ 장치가 알려 주는 `device_interval` 로도 안 된다: **배우기 전에는
    `stale_after`(초기값 4000초)의 1/3** 이라 첫 `NOW` 들이 통째로 막힌다.
    """
    now = time.time()
    icfg = IcgCfg()
    icfg.hk.log_dir = str(tmp_path)
    icfg.hk.query_aux = False
    icfg.hk.interval = 300.0                       # 폴링을 5분으로 늘려 둔다
    m = HkMonitor(None, icfg)
    m.radionode = _Rn({'hebox': (22.2, now - 90.0)}, now_min_age=60.0)
    # ⭐ 90초는 눈금(60)보다 낡았다 -- 폴링 주기(300)를 따라갔다면 거짓이 된다.
    assert m._radionode_is_old() is True            # noqa: SLF001


def test_no_sample_at_all_counts_as_old(tmp_path):
    """⚠️ 표본이 하나도 없으면 **낡은 것으로 본다** -- 첫 `NOW` 가 헛돌면 안 된다."""
    assert _mon(tmp_path, _Rn({}))._radionode_is_old() is True   # noqa: SLF001


def test_hkdata_now_pushes_the_periodic_cycle_out_by_one_interval(tmp_path):
    """⭐ `HKDATA NOW` 뒤에는 **60초를 새로 센다** (운영자 2026-09-09).

    ⛔ 안 밀면 방금 한 바퀴를 돌렸는데 몇 초 뒤 주기 바퀴가 **또 돈다** --
    왕복만 쓰고 값은 그대로다.
    ⚠️ 여기서 재는 것은 `_next_at` 이 **미래로 밀렸는가** 다.  `run()` 의
    잠자기가 깨어날 때마다 그 값을 다시 보므로 자는 중에 밀어도 따라간다.
    """
    m = _mon(tmp_path, _Rn({'hebox': (22.2, time.time())}, now_min_age=60.0))
    m._next_at = time.monotonic()                   # noqa: SLF001 -- 곧 돌 참
    asyncio.run(m.refresh_now())
    left = m._next_at - time.monotonic()            # noqa: SLF001
    assert 55.0 < left <= 60.0, left


def test_the_sleeper_follows_a_deadline_that_moved(tmp_path):
    """⭐ 자는 중에 `_next_at` 이 밀리면 **따라간다**.

    ⚠️ 이것이 별도 깨움 신호 없이 도는 근거다 -- 미는 쪽은 **늘 뒤로만** 밀고,
    자던 쪽은 옛 시각에 한 번 깨어나 다시 재고 또 잔다.
    ⛔ 따라가지 않으면 `HKDATA NOW` 직후에 주기 바퀴가 그대로 돌아 미는 뜻이
    사라진다.
    """
    m = _mon(tmp_path)
    m.QUIET_POLL = 0.01

    async def run():  # noqa: ANN202
        m._next_at = time.monotonic() + 0.05        # noqa: SLF001

        async def push():  # noqa: ANN202
            await asyncio.sleep(0.02)
            m._next_at = time.monotonic() + 0.15    # noqa: SLF001

        asyncio.ensure_future(push())
        t0 = time.monotonic()
        assert await m._sleep_until() is True       # noqa: SLF001
        return time.monotonic() - t0

    waited = asyncio.run(run())
    assert waited >= 0.15, waited                   # 밀린 시각을 따라갔다

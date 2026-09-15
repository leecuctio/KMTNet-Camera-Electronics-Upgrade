# -*- coding: utf-8 -*-
"""HK 를 **파일에서 와이어로** -- `GO` 마다 ICS 가 ICG 에 `HKDATA NOW` 를 묻고 그 답으로
게이지를 끄고 헤더를 채운다 (운영자 지시 2026-09-03 · 구현 2026-09-15, DevNote 11.90).

지키려는 것:

* `GO` 가 받아들여지면 `ICS>ICG HKDATA NOW` 가 나간다.  답이 오면 그 값이 **그 취득의 모든
  프레임**의 5.6절 카드가 된다 -- 키가 없으면 sentinel (`rawhdr` 가 채운다).
* 답의 `VACGAUGE` 가 `ON`/`WARMUP`/`UNKNOWN` 이면 `VACGAUGE OFF` 를 보내고, `OFF` 면 안 보낸다.
  답이 없으면 종전대로 추적 상태로 판단한다.
* 답이 없어도 노출은 간다 -- 카드는 sentinel, 경고 한 줄.
* *"no fresh HK sample yet"* 같은 비응답 본문은 답으로 치지 않는다 (11.12 F9).
* ⛔ 파일 스냅샷 경로는 없다 -- `[archon] hk_latest` 도 `[hk] latest_name` 도 설정에 없다.
"""
from __future__ import annotations

import asyncio
import glob
import logging
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))

from ics_archon import hkwire                                     # noqa: E402
from ics_archon import config as acfg_mod                         # noqa: E402
from icg_archon import config as icfg_mod                         # noqa: E402
from test_ics_ops_commands import Session, until                  # noqa: E402

REPLY = ('HKQDATE=2026-09-15T01:02:03.123 HKUDATE=2026-09-15T01:02:00 HKSTALE=0 '
         'VACGAUGE=%s DEWPRES=6.93e-04 HTREN=OFF HTRSET=-95.00 HTROUT=3.512 '
         'HTRFORCE=OFF CCDTEMP=-101.23 DMPTEMP=-122.34 PT30N1=-153.45 PT30N2=-154.56 '
         'CHARCOAL=-205.67 WALLBRD=16.78 HEBOX=37.89 FSATEMP=16.70 FSAHUM=17.80')


def _headers(tmp_path) -> dict:  # noqa: ANN001
    from astropy.io import fits
    out = {}
    for path in glob.glob(str(tmp_path / 'rawdata' / '*.fits')):
        with fits.open(path) as hdul:
            out[os.path.basename(path)] = dict(hdul[0].header)
    return out


def _sent_after(ses, n: int, needle: str) -> list[str]:  # noqa: ANN001
    return [s for s in ses.sent[n:] if needle in s]


# ---------------------------------------------------------------------------
# 해석기 (11.12 F7·F8·F9·F10)
# ---------------------------------------------------------------------------

def test_parse_lowercases_keys_and_types_values():
    got = hkwire.parse_hkdata(REPLY % 'ON')
    assert got['ccdtemp'] == -101.23 and got['fsahum'] == 17.8
    assert got['dewpres'] == '6.93e-04'                 # 원문 그대로 -- rawhdr 가 판정
    assert got['vacgauge'] == 'ON' and got['htren'] == 'OFF'
    assert got['hkstale'] == 0 and got['hkudate'] == '2026-09-15T01:02:00'


def test_parse_rejects_a_non_reply_body():
    assert hkwire.parse_hkdata('no fresh HK sample yet') is None
    assert hkwire.parse_hkdata('') is None


def test_parse_keeps_expstatus_and_drops_a_bad_number(caplog):  # noqa: ANN001
    caplog.set_level(logging.WARNING, logger='ics_archon.hkwire')
    got = hkwire.parse_hkdata('HKSTALE=1 VACGAUGE=OFF CCDTEMP=cold EXPSTATUS=IDLE')
    assert 'ccdtemp' not in got and got['expstatus'] == 'IDLE'
    assert any('not numeric' in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# 설정 -- 파일 경로가 없다
# ---------------------------------------------------------------------------

def test_the_file_snapshot_is_gone_from_both_configs():
    assert not hasattr(acfg_mod.ArchonCfg(), 'hk_latest')
    assert not hasattr(acfg_mod.ArchonCfg(), 'hk_stale_after')
    assert not hasattr(icfg_mod.IcgCfg().hk, 'latest_name')
    assert acfg_mod.ArchonCfg().hk_query_timeout > 0
    ini = open(os.path.join(ROOT, 'ics_archon.ini'), encoding='utf-8').read()
    assert 'hk_latest' not in [ln.split('=')[0].strip() for ln in ini.splitlines()
                               if '=' in ln and not ln.lstrip().startswith('#')]
    assert 'hk_query_timeout' in ini


def test_zero_query_timeout_is_refused(tmp_path):  # noqa: ANN001
    """0 이하면 매번 곧바로 포기해 카드가 전부 sentinel -- 기동에서 세운다."""
    from ics_sim import config as simcfg
    from test_ini_cards import ACF_TEXT, INI_OVERRIDES, write_ini
    acf = tmp_path / 'KMTC_SCI_101_STA0284_R2613_MK.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')
    over = {k: dict(v) for k, v in INI_OVERRIDES.items()}
    over.setdefault('archon', {})['hk_query_timeout'] = '0'
    ini = write_ini(tmp_path, over, str(acf))
    cfg, acfg = simcfg.load(ini), acfg_mod.load(ini)
    with pytest.raises(acfg_mod.ArchonConfigError):
        acfg_mod.validate(acfg, tuple(cfg.node.ccds), cfg)


# ---------------------------------------------------------------------------
# GO -> HKDATA NOW -> 게이지 판단 -> 헤더
# ---------------------------------------------------------------------------

def test_go_asks_hkdata_now_and_the_reply_fills_the_header(tmp_path, caplog):  # noqa: ANN001
    """⭐ 답의 값이 헤더에 실리고, `VACGAUGE=ON` 이라 `VACGAUGE OFF` 가 나간다 --
    추적 상태가 OFF(예열 GO 가 껐다)여도 ICG 낱말이 정본이다."""
    caplog.set_level(logging.WARNING, logger='ics_archon.gaugectl')

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            n = len(ses.sent)
            ses.app.transport.feed('abc>ICS go 1')
            await until(lambda: _sent_after(ses, n, 'ICG HKDATA NOW'),
                        what='GO 의 HKDATA NOW')
            ses.app.transport.feed('ICG>ICS DONE: HKDATA ' + REPLY % 'ON')
            await until(lambda: _sent_after(ses, n, 'ICG VACGAUGE OFF'),
                        what='ON 이라 VACGAUGE OFF')
            await ses.app.seq.wait()
            await asyncio.sleep(0.3)
            return ses.sent[n:]

    sent = asyncio.run(run())
    assert len([s for s in sent if 'ICG HKDATA NOW' in s]) == 1
    assert any('although we tracked' in r.getMessage() for r in caplog.records)
    heads = _headers(tmp_path)
    newest = max(heads)                       # 이 GO 의 파일 (warmup 의 것보다 뒤 번호)
    h = heads[newest]
    assert h['CCDTEMP'].strip() == '-101.23'
    assert h['DEWPRES'].strip() == '6.93e-4'          # rawhdr.format_dewpres 의 표기
    assert h['HKUDATE'].strip() == '2026-09-15T01:02:00'
    assert h['HEBOX'].strip() == '+37.89' and h['FSAHUM'].strip() == '17.80'
    assert h['HTRSET'].strip() == '-95.00' and h['HTREN'].strip() == 'OFF'


def test_gauge_off_is_not_sent_when_icg_says_off(tmp_path):  # noqa: ANN001
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            n = len(ses.sent)
            ses.app.transport.feed('abc>ICS go 1')
            await until(lambda: _sent_after(ses, n, 'ICG HKDATA NOW'))
            ses.app.transport.feed('ICG>ICS DONE: HKDATA ' + REPLY % 'OFF')
            await ses.app.seq.wait()
            await asyncio.sleep(0.3)
            return ses.sent[n:]

    sent = asyncio.run(run())
    assert not [s for s in sent if 'ICG VACGAUGE OFF' in s], sent


def test_no_reply_keeps_the_exposure_going_with_sentinels(tmp_path, caplog):  # noqa: ANN001
    """⛔ HK 하나 때문에 관측을 막지 않는다 -- 시한을 넘기면 카드는 sentinel, 경고 한 줄."""
    caplog.set_level(logging.WARNING, logger='ics_archon.hw')

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            n = len(ses.sent)
            ses.app.transport.feed('abc>ICS go 1')
            await ses.app.seq.wait()
            await asyncio.sleep(0.3)
            return ses.sent[n:]

    sent = asyncio.run(run())
    assert [s for s in sent if 'ICG HKDATA NOW' in s]
    # 예열 GO 가 이미 껐다(추적 OFF) -- 답이 없으면 추적 상태로 판단하니 또 안 보낸다.
    assert not [s for s in sent if 'ICG VACGAUGE OFF' in s], sent
    heads = _headers(tmp_path)
    h = heads[max(heads)]
    assert h['CCDTEMP'].strip() == '-999.99' and h['DEWPRES'].strip() == '9.99e-9'
    assert h['HKUDATE'].strip() == 'NC'
    assert any('no HKDATA' in r.getMessage() for r in caplog.records)


def test_a_non_reply_body_does_not_count_as_the_answer(tmp_path):  # noqa: ANN001
    """11.12 F9 -- ICG 재기동 직후의 *"no fresh HK sample yet"* 는 답이 아니다.  뒤에 온
    진짜 답이 실린다."""
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            n = len(ses.sent)
            ses.app.transport.feed('abc>ICS go 1')
            await until(lambda: _sent_after(ses, n, 'ICG HKDATA NOW'))
            ses.app.transport.feed('ICG>ICS DONE: HKDATA no fresh HK sample yet')
            await asyncio.sleep(0.01)
            ses.app.transport.feed('ICG>ICS DONE: HKDATA ' + REPLY % 'OFF')
            await ses.app.seq.wait()
            await asyncio.sleep(0.3)

    asyncio.run(run())
    h = _headers(tmp_path)[max(_headers(tmp_path))]
    assert h['CCDTEMP'].strip() == '-101.23'


# ---------------------------------------------------------------------------
# CxHKDATA -- 컨트롤러 텔레메트리의 와이어 판 (운영자 확정 2026-09-04 · 구현 2026-09-15)
# ---------------------------------------------------------------------------

def _kv(body: str) -> dict:
    return dict(p.split('=', 1) for p in body.split() if '=' in p)


def test_c1hkdata_and_c2hkdata_answer_the_controller_telemetry(tmp_path):  # noqa: ANN001
    """ICS -- 자리 표는 헤더의 `Cn_*` 와 같다 (온도 10 · 레일 7×V/I).  `CTRLnID` 는 `BACKPLANE_ID`."""
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()                       # STATUS 스냅샷이 서 있게
            a = await ses.reply('abc>ICS c1hkdata', 'C1HKDATA')
            b = await ses.reply('abc>ICS c2hkdata now', 'C2HKDATA')
            bad = await ses.reply('abc>ICS c1hkdata later', 'C1HKDATA')
            return a, b, bad

    a, b, bad = asyncio.run(run())
    # ① 인자 없음 = 감시 스냅샷.  하네스는 `monitor = false` 라 표본이 없다 -> 전 자리 결측,
    #    `C1UDATE` 없음.  ⭐ 결측을 sentinel 로 채우지 않고 `C1STALE` 로 센다.
    assert ' DONE: C1HKDATA ' in a, a
    kv = _kv(a.split(' DONE: C1HKDATA ', 1)[1])
    assert kv['C1STALE'] == '24' and 'C1UDATE' not in kv and kv['CTRL1ID'] == '0024498A715E301C'
    # ② `NOW` = 지금 STATUS 를 읽는다 -> 전 자리 실값.
    assert ' DONE: C2HKDATA ' in b, b
    kv = _kv(b.split(' DONE: C2HKDATA ', 1)[1])
    assert kv['C2STALE'] == '0', kv
    assert kv['CTRL2ID'] == '0024498A715E301C'
    assert kv['VALID'] == '1' and len(kv['C2QDATE']) == 23 and len(kv['C2UDATE']) == 19
    temps = [k for k in kv if k.endswith('_TEMP')]
    assert len(temps) == 10 and kv['BP_TEMP'].startswith(('+', '-'))
    assert len([k for k in kv if k.endswith('_V')]) == 7 and kv['P2V5_V'].startswith(('+', '-'))
    assert len([k for k in kv if k.endswith('_I')]) == 7
    assert "'" not in b and '"' not in b
    assert ' ERROR: C1HKDATA ' in bad and 'Usage' in bad


def test_c1hkdata_on_the_guide_side_uses_the_guide_slots(tmp_path):  # noqa: ANN001
    """ICG -- 같은 함수, guide 자리 표(온도 8 · 레일 8, `HEATER` 는 `HTR_V`/`HTR_I`).
    하네스의 가짜 컨트롤러엔 STATUS 표본이 없어 **전 자리 결측**(`C1STALE=24`)이고
    `C1UDATE` 가 없다.  컨트롤러 자체가 없으면(sim) 다른 명령처럼 `ERROR`."""
    from test_icg_ops_commands import _drive, _trig, _about
    _calls, sent = _trig(tmp_path, ['abc>ICG C1HKDATA', 'abc>ICG C1HKDATA NOWW'])
    done = [s for s in _about(sent, 'C1HKDATA') if 'DONE:' in s]
    assert len(done) == 1, sent
    kv = _kv(done[0].split(' DONE: C1HKDATA ', 1)[1])
    assert kv['C1STALE'] == '24' and 'C1UDATE' not in kv and len(kv['C1QDATE']) == 23
    assert any('ERROR: C1HKDATA' in s and 'Usage' in s for s in sent)
    _app, sent = _drive(tmp_path, ['abc>ICG C1HKDATA'])
    assert any('ERROR: C1HKDATA' in s for s in sent)      # 컨트롤러 없음 -- 조용히 성공하지 않는다

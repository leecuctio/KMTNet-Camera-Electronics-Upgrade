# -*- coding: utf-8 -*-
"""HK 를 **파일에서 와이어로** -- `GO` 마다 ICS 가 ICG 에 `HKDATA NOW` 를 묻고 그 답으로
게이지를 끄고 헤더를 채운다 (운영자 지시 2026-09-03 · 구현 2026-09-15, DevNote 11.90).

지키려는 것:

* `GO` 가 받아들여지면 `ICS>ICG HKDATA NOW` 가 나간다.  답이 오면 그 값이 **그 취득의 모든
  프레임**의 5.6절 카드가 된다 -- 키가 없으면 sentinel (`rawhdr` 가 채운다).
* 답의 `VACGAUGE` 가 `ON`/`WARMUP`/`UNKNOWN` 이면 `VACGAUGE OFF` 를 보내고, `OFF` 면 안 보낸다.
  답이 없으면 종전대로 추적 상태로 판단한다.
* 답이 없어도 노출은 간다 -- 카드는 sentinel, 경고 한 줄.
* ICG 가 `ERROR`/`FATAL` 로 답하면 **시한을 안 기다리고** 같은 처리를 한다 (DevNote 11.96).
* *"no fresh HK sample yet"* 같은 비응답 본문은 답으로 치지 않는다 (11.12 F9).
* ⛔ 파일 스냅샷 경로는 없다 -- `[archon] hk_latest` 도 `[hk] latest_name` 도 설정에 없다.
* ⛔ ICG 의 답은 **커맨드워드 + 타입**으로 가른다 -- `VACGAUGE`/`EXPENABLE` 의 `ERROR`·
  `FATAL` 은 거절이고, 거절된 `GO` 는 게이지 켜짐대기 타이머를 안 건드린다.
"""
from __future__ import annotations

import asyncio
import glob
import logging
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))

from ics_archon import hkwire                                     # noqa: E402
from ics_archon import config as acfg_mod                         # noqa: E402
from ics_archon import expenablectl as ge                         # noqa: E402
from ics_archon import gaugectl as gc                             # noqa: E402
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


def _new_frame(heads: dict, before: set) -> list[dict]:
    """`before` 뒤에 생긴 파일들의 헤더 -- **프레임이 정확히 하나**여야 한다.

    ⭐ 집합 차로 고른다 -- `max()` 는 이름 순이라 번호 체계가 바뀌면 엉뚱한 파일을 집는다.
    ⚠️ 한 프레임은 **컨트롤러마다 파일 하나**다 (`<SITE>.<YYYYMMDD>.<NNNNNN>.MK.fits` ·
    `….NT.fits`) -- 그래서 파일 수가 아니라 **프레임 번호**(뒤 두 토막을 뗀 이름)를 센다.
    """
    new = sorted(set(heads) - before)
    frames = {name.rsplit('.', 2)[0] for name in new}
    assert len(frames) == 1, '이 GO 의 프레임이 하나가 아니다: %r' % new
    return [heads[name] for name in new]


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


@pytest.mark.parametrize('mtype', ['ERROR', 'FATAL'])
def test_an_hkdata_refusal_ends_the_wait_at_once(tmp_path, caplog, mtype):  # noqa: ANN001
    """⛔ ICG 가 `ERROR`/`FATAL: HKDATA` 로 답하면 **시한을 안 기다린다** (DevNote 11.96).

    종전에는 `DONE` 에만 조치가 걸려 있어 `GO` 마다 `hk_query_timeout` 을 헛기다렸고, 그 뒤
    *"ICG 가 떠 있는지 · XIS …"* 라는 틀린 진단을 냈다 -- ICG 는 떠 있고 답도 했다.
    처리는 무응답과 같다: 카드는 sentinel, 노출은 간다.  원인 본문은 경고에 실린다.
    """
    caplog.set_level(logging.WARNING)
    mark = {}

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()          # ⚠️ 예열 GO 는 ICG 가 없어 시한으로 끝난다 -- 그 뒤부터 센다
            mark['logs'] = len(caplog.records)
            # ⭐ 예열 GO 의 파일을 적어 둔다 -- 이 GO 의 파일은 **집합 차**로 고른다
            # (`_new_frame`).
            mark['files'] = set(_headers(tmp_path))
            # ⚠️ 시한을 길게 -- 하네스의 `time_scale`(0.02)로 접어도 5 s 라, 시한으로
            # 끝났다면 아래 `until`(1 s) 이 못 본다.
            ses.app.acfg.hk_query_timeout = 250.0
            n = len(ses.sent)
            ses.app.transport.feed('abc>ICS go 1')
            await until(lambda: _sent_after(ses, n, 'ICG HKDATA NOW'),
                        what='GO 의 HKDATA NOW')
            task = ses.app.backend.hk_task
            ses.app.transport.feed('ICG>ICS %s: HKDATA Failed: boom' % mtype)
            await until(lambda: task is not None and task.done(), timeout=1.0,
                        what='거절 답에 HK 질의가 곧바로 끝남')
            got = task.result()
            await ses.app.seq.wait()
            await asyncio.sleep(0.3)
            return got

    got = asyncio.run(run())
    assert got is None
    msgs = [r.getMessage() for r in caplog.records[mark['logs']:]]
    assert any('ICG refused HKDATA (%s) -- Failed: boom' % mtype in m for m in msgs), msgs
    assert not any('no HKDATA reply' in m for m in msgs), '시한까지 기다렸다: %r' % msgs
    for h in _new_frame(_headers(tmp_path), mark['files']):
        assert h['CCDTEMP'].strip() == '-999.99' and h['HKUDATE'].strip() == 'NC'


def test_an_hk_refusal_only_warns_and_the_go_keeps_waiting(tmp_path, caplog):  # noqa: ANN001
    """⛔ `ERROR: HK` 는 콘솔 `hk` 의 답이다 -- `GO` 의 `HKDATA NOW` 대기를 **안 끝낸다**
    (DevNote 11.96).  `GO` 의 질의는 `HKDATA` 로만 나가므로 그 거절도 `HKDATA` 로 온다.
    경고는 내고(원인 본문 · 보낸 이), 뒤에 온 `DONE: HKDATA` 가 헤더를 채운다.
    ⚠️ 거절은 `icg_node`(`ICG`)와 **다른 이름**(`ICG2`)에서 보낸다 -- 둘이 같으면 진단이
    실제로 보낸 이(`msg.src`)를 대는지 설정값(`icg_node`)을 대는지 못 가른다."""
    caplog.set_level(logging.WARNING)
    mark = {}

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.warmup()
            mark['logs'] = len(caplog.records)
            mark['files'] = set(_headers(tmp_path))
            ses.app.acfg.hk_query_timeout = 250.0          # 시한으로 끝나지 않게
            n = len(ses.sent)
            ses.app.transport.feed('abc>ICS go 1')
            await until(lambda: _sent_after(ses, n, 'ICG HKDATA NOW'),
                        what='GO 의 HKDATA NOW')
            task = ses.app.backend.hk_task
            assert ses.app.acfg.icg_node == 'ICG'           # 전제: 보낸 이와 다른 이름
            ses.app.transport.feed('ICG2>ICS ERROR: HK HK monitor is not running')
            await asyncio.sleep(0.2)
            waiting = task is not None and not task.done()
            ses.app.transport.feed('ICG>ICS DONE: HKDATA ' + REPLY % 'OFF')
            await until(lambda: task.done(), timeout=1.0, what='DONE 답에 HK 질의가 끝남')
            got = task.result()
            await ses.app.seq.wait()
            await asyncio.sleep(0.3)
            return waiting, got

    waiting, got = asyncio.run(run())
    assert waiting, 'HK 거절이 GO 의 HKDATA 대기를 끝냈다'
    assert got is not None and got['ccdtemp'] == -101.23, got
    recs = [r for r in caplog.records[mark['logs']:]
            if 'refused HK (ERROR)' in r.getMessage()]
    assert len(recs) == 1, [r.getMessage() for r in caplog.records[mark['logs']:]]
    assert 'HK monitor is not running' in recs[0].getMessage()
    assert recs[0].getMessage().startswith('ICG2 refused HK'), recs[0].getMessage()
    assert recs[0].detail.startswith('ICG2 '), recs[0].detail     # 보낸 이(`msg.src`)를 댄다
    for h in _new_frame(_headers(tmp_path), mark['files']):
        assert h['CCDTEMP'].strip() == '-101.23'


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


# ---------------------------------------------------------------------------
# 벤치 첫날 (2026-09-15) 이 짚은 넷 -- DevNote 11.94
# ---------------------------------------------------------------------------

def test_console_hkdata_now_forwards_now_and_rejects_other_words(tmp_path):  # noqa: ANN001
    """⛔ 벤치: 콘솔 `hkdata now` 가 `ICS>ICG HKDATA` 로 나가 ICG 가 폴링값을 답했다
    (`HKUDATE` 가 안 움직였다).  `NOW` 는 넘기고, 모르는 인자는 거절한다.  응답 본문에
    `DONE:` 을 적지 않는다 (`type_in_body` 경고)."""
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            n = len(ses.sent)
            a = await ses.reply('abc>ICS hkdata now', 'HKDATA')
            b = await ses.reply('abc>ICS hkdata', 'HKDATA')
            c = await ses.reply('abc>ICS hk NOW', 'HK')
            bad = await ses.reply('abc>ICS hkdata later', 'HKDATA')
            return ses.sent[n:], a, b, c, bad

    sent, a, b, c, bad = asyncio.run(run())
    assert [s for s in sent if s.endswith('ICS>ICG HKDATA NOW')], sent
    assert [s for s in sent if s.endswith('ICS>ICG HKDATA')], sent
    assert [s for s in sent if s.endswith('ICS>ICG HK NOW')], sent
    assert ' DONE: HKDATA' in a and 'DONE:' not in a.split(' DONE: HKDATA', 1)[1]
    assert ' DONE: HKDATA' in b and ' DONE: HK ' in c
    assert ' ERROR: HKDATA' in bad and 'later' in bad
    assert not [s for s in sent if 'ICG HKDATA LATER' in s.upper()]


def test_an_hkdata_reply_is_not_mistaken_for_a_vacgauge_reply(tmp_path, caplog):  # noqa: ANN001
    """⛔ 벤치: `ICG>ICS DONE: HKDATA … VACGAUGE=ON …` 이 `vacuum gauge reply` 로 찍혔다 --
    원문 부분 문자열로 엿들어서.  답은 **커맨드워드**로 가른다: HKDATA 답은 데드맨을
    안 풀고, `DONE: VACGAUGE` 는 푼다."""
    caplog.set_level(logging.INFO, logger='ics_archon.gaugectl')

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            g = ses.app.gauge
            g._replied = False                                   # noqa: SLF001
            ses.app.transport.feed('ICG>ICS DONE: HKDATA ' + REPLY % 'ON')
            await asyncio.sleep(0.05)
            hk_replied = g._replied                              # noqa: SLF001
            ses.app.transport.feed('ICG>ICS EXEC: VACGAUGE')
            await asyncio.sleep(0.05)
            exec_replied = g._replied                            # noqa: SLF001
            ses.app.transport.feed('ICG>ICS DONE: VACGAUGE Gauge=OFF')
            await asyncio.sleep(0.05)
            return hk_replied, exec_replied, g._replied          # noqa: SLF001

    hk_replied, exec_replied, done_replied = asyncio.run(run())
    assert hk_replied is False and exec_replied is False and done_replied is True
    msgs = [r.getMessage() for r in caplog.records if 'vacuum gauge reply' in r.getMessage()]
    assert len(msgs) == 1 and 'DONE: VACGAUGE' in msgs[0], msgs


@pytest.mark.parametrize('mtype', ['ERROR', 'FATAL'])
def test_a_refusal_on_the_wire_makes_gauge_and_lock_unknown(tmp_path, caplog, mtype):  # noqa: ANN001
    """⛔ 수신 경로 전체(`_on_message` -> `_is_reply_to` -> `note_reply`)에서 `ERROR`·`FATAL`
    이 거절로 읽히는가 (DevNote 11.96).  종전에는 `note_reply` 가 원문에 `ERROR` 낱말이
    있나로 봐서 `FATAL` 이 정상 답으로 지나가 **껐다고 믿는** 상태가 남았다.
    ⚠️ 상대 노드(`ICG`)의 답만 센다 -- 허브(`XIS`)가 보낸 같은 꼴은 무시한다.
    ⚠️ 상태는 `feed` 직후(동기)에 읽는다 -- 감시 루프의 국면 틱이 잠금 상태를 다시
    쓰기 전이다."""
    caplog.set_level(logging.WARNING)

    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            g, e = ses.app.gauge, ses.app.expenable
            g.state, e.state = gc.OFF, ge.BLOCKED
            ses.app.transport.feed('XIS>ICS %s: VACGAUGE x' % mtype)
            ses.app.transport.feed('XIS>ICS %s: EXPENABLE x' % mtype)
            from_hub = (g.state, e.state)
            ses.app.transport.feed('ICG>ICS %s: VACGAUGE Gauge control not '
                                   'available' % mtype)
            ses.app.transport.feed('ICG>ICS %s: EXPENABLE Exposure lock is not '
                                   'available' % mtype)
            return from_hub, (g.state, e.state)

    from_hub, from_icg = asyncio.run(run())
    assert from_hub == (gc.OFF, ge.BLOCKED), '허브의 줄을 ICG 의 답으로 셌다: %r' % (from_hub,)
    assert from_icg == (gc.UNKNOWN, ge.UNKNOWN), from_icg
    refused = [r.getMessage() for r in caplog.records if 'was refused' in r.getMessage()]
    assert len(refused) == 2 and all(mtype in m for m in refused), refused


def test_a_rejected_go_keeps_the_reenable_timer(tmp_path):  # noqa: ANN001
    """⛔ **거절된 `GO` 는 켜짐대기 타이머를 안 푼다** (DevNote 11.96).

    종전 `IcsDispatcher.cmd_go` 는 수락 여부를 보기 **전에** 타이머를 풀었다.  거절된 `GO`
    는 취득을 안 세우므로 독출 완료(`after_acquisition`)도 안 오고, 그러면 타이머를 다시
    걸 사람이 없어 다음 `GO` 가 성공해 끝날 때까지 게이지가 꺼진 채 남는다 (그동안
    `DEWPRES` 도 못 잰다).
    """
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            g = ses.app.gauge
            g.before_exposure()                  # 추적 OFF (답은 없다 -- 데드맨 10 s)
            g.after_acquisition()                # 켜짐대기 + 600 s 타이머
            assert g.state == gc.PENDING_ON and g.pending_reenable
            bad = await ses.reply('abc>ICS go x', 'GO')
            return bad, g.state, g.pending_reenable

    bad, state, pending = asyncio.run(run())
    assert ' ERROR: GO ' in bad and 'Invalid frame count' in bad, bad
    assert state == gc.PENDING_ON and pending, '거절된 GO 가 켜짐대기 타이머를 지웠다'


def test_c1hk_and_c2hk_are_aliases_with_the_same_body(tmp_path):  # noqa: ANN001
    """⭐ 별칭 (운영자 지시 2026-09-15): `C1HK` = `C1HKDATA`, `C2HK` = `C2HKDATA` --
    `HK`/`HKDATA` 짝처럼 **같은 본문, 커맨드워드만 다르다**.  ICG 도 `C1HK`."""
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            a = await ses.reply('abc>ICS c1hk', 'C1HK')
            b = await ses.reply('abc>ICS c1hkdata', 'C1HKDATA')
            c = await ses.reply('abc>ICS c2hk now', 'C2HK')
            bad = await ses.reply('abc>ICS c2hk later', 'C2HK')
            return a, b, c, bad, ses.app.emit.violations

    a, b, c, bad, violations = asyncio.run(run())
    ka = _kv(a.split(' DONE: C1HK ', 1)[1])
    kb = _kv(b.split(' DONE: C1HKDATA ', 1)[1])
    assert set(ka) == set(kb) and ka['C1STALE'] == kb['C1STALE']
    assert ' DONE: C2HK ' in c and _kv(c.split(' DONE: C2HK ', 1)[1])['C2STALE'] is not None
    assert ' ERROR: C2HK ' in bad and 'Usage: C2HK' in bad
    assert violations == [], violations              # 어휘에 등록됐다

    from test_icg_ops_commands import _trig, _about
    _calls, sent = _trig(tmp_path, ['abc>ICG c1hk', 'abc>ICG C1HK NOWW'])
    done = [s for s in _about(sent, 'C1HK') if 'DONE:' in s]
    assert len(done) == 1 and 'C1STALE=' in done[0], sent
    assert any('ERROR: C1HK' in s and 'Usage: C1HK' in s for s in sent)


def test_imagetype_is_a_query_with_three_spellings(tmp_path):  # noqa: ANN001
    """⭐ `IMAGETYPE`/`IMAGETYP`/`IMGTYP` -- **조회만** (운영자 지시 2026-09-15 벤치: 종전엔
    *"Didn't understand"*).  설정은 종전대로 `OBJECT`/`BIAS`/… 이고 인자가 오면 거절한다.
    ICS 와 ICG 둘 다."""
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            await ses.reply('abc>ICS dark M31', 'DARK')
            a = await ses.reply('abc>ICS imagetype', 'IMAGETYPE')
            b = await ses.reply('abc>ICS imagetyp', 'IMAGETYP')
            c = await ses.reply('abc>ICS imgtyp', 'IMGTYP')
            bad = await ses.reply('abc>ICS imagetype bias', 'IMAGETYPE')
            return a, b, c, bad, ses.app.emit.violations

    a, b, c, bad, violations = asyncio.run(run())
    for line, word in ((a, 'IMAGETYPE'), (b, 'IMAGETYP'), (c, 'IMGTYP')):
        assert (" DONE: %s ImageType=DARK ObjectName='M31' EXP=" % word) in line, line
    assert ' ERROR: IMAGETYPE ' in bad and 'Query only' in bad
    assert violations == [], violations

    from test_icg_ops_commands import _drive, _about
    _app, sent = _drive(tmp_path, ['abc>ICG object NGC1', 'abc>ICG imgtyp'])
    done = [s for s in _about(sent, 'IMGTYP') if 'DONE:' in s]
    assert len(done) == 1 and 'ImageType=OBJECT' in done[0], sent


def test_hknow_and_cxhknow_are_now_aliases(tmp_path):  # noqa: ANN001
    """⭐ 운영자 지시 2026-09-15: `hknow` = `hk now`, `c1hknow` = `c1hk now` = `c1hkdata now`
    (ICS 는 `c2hknow` 도).  ICS 의 `hknow` 는 와이어로 `HK NOW` 가 나간다 -- 답이 `DONE: HK`
    로 와야 받아 적으니까.  인자는 거절."""
    async def run():  # noqa: ANN202
        async with Session(tmp_path) as ses:
            n = len(ses.sent)
            a = await ses.reply('abc>ICS hknow', 'HKNOW')
            bad = await ses.reply('abc>ICS hknow x', 'HKNOW')
            c1 = await ses.reply('abc>ICS c1hknow', 'C1HKNOW')
            c2 = await ses.reply('abc>ICS c2hknow', 'C2HKNOW')
            return ses.sent[n:], a, bad, c1, c2, ses.app.emit.violations

    sent, a, bad, c1, c2, violations = asyncio.run(run())
    assert [s for s in sent if s.endswith('ICS>ICG HK NOW')], sent
    assert ' DONE: HKNOW Queried ICG now' in a
    assert ' ERROR: HKNOW ' in bad and 'no argument' in bad
    assert ' DONE: C1HKNOW ' in c1 and 'C1STALE=' in c1
    assert ' DONE: C2HKNOW ' in c2 and 'C2STALE=' in c2
    assert violations == [], violations

    from test_icg_ops_commands import _Rec, _trig, _about

    class _RecNow(_Rec):
        """`NOW` 갈래가 부르는 `refresh_status_live` 를 가진 가짜 -- 표본은 없다."""
        status_live: dict = {}
        status_live_at = 0.0

        async def refresh_status_live(self) -> bool:
            return True

    import test_icg_ops_commands as ops
    orig = ops._Rec
    ops._Rec = _RecNow
    try:
        _calls, sent = _trig(tmp_path, ['abc>ICG hknow', 'abc>ICG c1hknow',
                                        'abc>ICG c1hknow x'])
    finally:
        ops._Rec = orig
    assert [s for s in _about(sent, 'HKNOW') if 'DONE: HKNOW HKQDATE=' in s], sent
    assert [s for s in _about(sent, 'C1HKNOW') if 'DONE: C1HKNOW C1QDATE=' in s], sent
    assert any('ERROR: C1HKNOW' in s and 'no argument' in s for s in sent)


def test_openapi_is_the_default_and_missing_credentials_only_warn():
    """⭐ `[radionode] backend = openapi` 가 기본 (운영자 2026-09-15).  자격증명이 없으면
    **기동을 세우지 않고** 경고 + off 로 내린다 -- 저장소 ini 그대로도 떠야 한다."""
    from icg_archon import config as icfg_mod
    cfg = icfg_mod.IcgCfg()
    cfg.radionode.backend = 'openapi'         # 배포 ini 의 값 -- 자격증명은 없다
    warn = icfg_mod.validate(cfg, 'sim')
    assert any('backend=openapi' in w and 'off' in w for w in warn), warn
    assert cfg.radionode.backend == 'off'
    # ⭐ 저장소 ini 는 **실제 로더**로 읽는다 (DevNote 11.96) -- 파일 전체에서 첫
    # `backend` 줄을 잡던 판은 다른 절에 `backend` 키가 생기면 엉뚱한 줄을 봤다.
    # `load()` 는 `[radionode]` 절만 보고 인라인 `#` 주석도 뗀다 (`_make_parser`).
    assert icfg_mod.load(os.path.join(ROOT, 'icg_archon.ini')).radionode.backend == 'openapi'


#: `[radionode]` 내림 시험의 장치·자격증명 -- `test_icg_radionode.py` 의 것과 같은 꼴.
_RN_DEVICES = (icfg_mod.RadionodeDevice(alias='hebox', mac='AA', keys=('hebox',)),
               icfg_mod.RadionodeDevice(alias='fsa', mac='BB', keys=('fsatemp', 'fsahum')))
_RN_CREDS = dict(base_url='https://example.invalid', api_key='k', api_secret='s')

#: 내림 경고의 *"빠진 칸"* 자리.  ⚠️ 경고 뒤쪽 안내문에 `api_key`·`api_secret` 낱말이
#: 늘 들어 있어서 줄 전체로 보면 가를 수 없다 -- 그 자리만 떼어 본다.
_DOWNGRADE = re.compile(r'backend=openapi 인데 (.+?) 가 없다')


def _downgrade_missing(warn: list[str]) -> list[str]:
    return [m.group(1) for m in map(_DOWNGRADE.search, warn) if m]


def _openapi_cfg(**creds):  # noqa: ANN003, ANN202
    cfg = icfg_mod.IcgCfg()
    cfg.radionode = icfg_mod.RadionodeCfg(backend='openapi', devices=_RN_DEVICES, **creds)
    return cfg


def test_openapi_with_every_credential_stays_openapi():
    """⭐ **반대 방향** -- 자격증명이 다 있으면 `openapi` 그대로다 (DevNote 11.96).

    내리는 조건이 망가져 **늘** `off` 로 가는 회귀가 나면 실기 폴링이 조용히 꺼지고
    HEBOX/FSATEMP/FSAHUM 이 sentinel 이 된다 -- 그것을 잡는 시험이 없었다.
    """
    cfg = _openapi_cfg(**_RN_CREDS)
    warn = icfg_mod.validate(cfg, 'sim')
    assert cfg.radionode.backend == 'openapi', warn
    assert _downgrade_missing(warn) == [], warn


def test_one_missing_credential_is_named_alone():
    """하나만 빠졌으면(`api_secret`) **그것만** 적고 `off` 로 내린다 -- 운영자가 채울 칸을
    바로 알게 (DevNote 11.96)."""
    creds = dict(_RN_CREDS)
    del creds['api_secret']
    cfg = _openapi_cfg(**creds)
    warn = icfg_mod.validate(cfg, 'sim')
    assert cfg.radionode.backend == 'off', warn
    assert _downgrade_missing(warn) == ['api_secret'], warn

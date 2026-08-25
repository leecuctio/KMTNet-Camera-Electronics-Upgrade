#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전 경로 -- 가짜 Archon 2대로 노출 사이클을 끝까지 돌린다.

**v0.0 이 실기 없이 확인할 수 있는 최대치다.**  시퀀서·명령 처리부·메시지
규약은 `ics_sim` 의 것을 그대로 쓰므로, 여기서 보는 것은 둘이다:

1. **OBSAgent 규약이 실기 백엔드로도 그대로 지켜지나** -- `Acquisition
   Complete.` 4회 · `Wrote` 4회 · `EXPSTATUS=IDLE`.  백엔드를 갈아끼웠는데
   메시지가 달라지면 그것이 곧 회귀다.
2. **산출물이 규격대로 나오나** -- pair 2파일 · 기하 · 픽셀 배치 · 헤더의
   실기 유래 카드(`CTRLnSN`/`Cn_TEMP`/`DATASRC`)와 sentinel(`CCDTEMP`).

⚠️ 확인되지 **않는** 것: 실제 독출 시간, STATUS 필드의 실제 값, 픽셀 좌우
배치의 실물 정합.  가짜 상대역이 우리가 읽은 규격대로 답하기 때문이다
(`fake_archon.py` 머리말).
"""

from __future__ import annotations

import asyncio
import glob
import os

import pytest
from fake_archon import FakeArchon

from ics_archon import config as acfg_mod
from ics_archon.app import IcsArchon, rdmode_from_acf

from ics_sim import config as simcfg

#: 시험용 기하 -- 실물(19200x9400, 344 MiB)을 쓸 수 없으니 줄인다.  chip 을
#: X 로 반 나누므로 폭은 짝수여야 한다.
NX, NY = 12, 4

ACF_TEXT = """[CONFIG]
TRIGOUTFORCE=0
TRIGOUTLEVEL=1
PARAMETER1="Exposures=1"
PARAMETER2="IntMS=0"
MOD5\\PREAMPGAIN=0
"""

INI = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    os.pardir, 'ics_archon.ini'))


def make_cfgs(tmp_path, mk: FakeArchon, nt: FakeArchon):  # noqa: ANN001
    """`ics_archon.ini` 를 읽고 시험용으로 바꾼다 -- ini 도 함께 검증된다."""
    acf = tmp_path / 'test.acf'
    acf.write_text(ACF_TEXT, encoding='ascii')

    cfg = simcfg.load(INI)
    cfg.timing.time_scale = 0.02
    cfg.transport.bind_host = '127.0.0.1'
    cfg.transport.bind_port = 0
    cfg.transport.send_gap_ms = 0.0
    cfg.behavior.console = False
    cfg.logging.wire = False
    cfg.paths.data_dir = str(tmp_path / 'rawdata')
    cfg.paths.expnum_file = str(tmp_path / 'expnum')
    cfg.hardware.backend = 'archon'

    acfg = acfg_mod.load(INI)
    acfg.hosts = {'MK': '127.0.0.1', 'NT': '127.0.0.1'}
    acfg.acf = {'MK': str(acf), 'NT': str(acf)}
    acfg.naxis1, acfg.naxis2 = NX, NY
    acfg.poweron_wait = 0.0
    acfg.frame_poll = 0.01
    acfg.progress_step = 0                 # 폴링마다 보고 -- 진행률을 보려고
    # 포트가 컨트롤러마다 다르다 -- 한 주소에 두 가짜를 띄웠으므로.
    acfg.port = mk.port
    return cfg, acfg, nt.port


class TwoFakes:
    """가짜 컨트롤러 2대.  `MK`/`NT` 가 서로 다른 포트에 있다."""

    def __init__(self, **kw) -> None:
        self.mk = FakeArchon(width=NX, height=NY, **kw)
        self.nt = FakeArchon(width=NX, height=NY, **kw)
        self.mk.start()
        self.nt.start()

    def close(self) -> None:
        self.mk.shutdown()
        self.nt.shutdown()


@pytest.fixture()
def fakes():  # noqa: ANN201
    two = TwoFakes()
    yield two
    two.close()


async def _drive(cfg, acfg, nt_port, script, settle=0.8):  # noqa: ANN001
    app = IcsArchon(cfg, acfg)
    # 두 가짜가 포트만 다르므로 NT 링크의 포트를 여기서 맞춘다.
    app.backend.ctrls['NT'].link.port = nt_port
    await app.start()
    try:
        for line in script:
            app.transport.feed(line)
            await asyncio.sleep(0.02)
        await app.seq.wait()
        await asyncio.sleep(settle)
        return list(app.transport.sent_log), app
    finally:
        await app.stop()


def drive(tmp_path, fakes, script):  # noqa: ANN001
    cfg, acfg, nt_port = make_cfgs(tmp_path, fakes.mk, fakes.nt)
    return asyncio.run(_drive(cfg, acfg, nt_port, script))


# ---------------------------------------------------------------------------
# OBSAgent 규약 -- 백엔드를 갈아끼워도 메시지는 같아야 한다
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('kind', ['dark', 'object'])
def test_obsagent_contract_holds_with_the_real_backend(tmp_path, fakes, kind):  # noqa: ANN001
    """`Acquisition Complete.` 4회 · `Wrote` 4회 · `EXPSTATUS=IDLE`.

    **개수가 곧 규약이다** (DevNote 3장 2항).  DARK 는 노출을 `readout()` 에서
    걸고 OBJECT 는 `open_shutter()` 에서 거는데(두 갈래), 밖으로 나가는
    메시지는 어느 쪽이든 같아야 한다.
    """
    script = ['OBS>ICS projid ENG',
              'OBS>ICS %s begin' % kind,
              'OBS>ICS exp 1',
              'OBS>ICS go']
    sent, _ = drive(tmp_path, fakes, script)
    assert sum('Acquisition Complete.' in m for m in sent) == 4
    assert sum('Wrote' in m for m in sent) == 8      # CB 4 + ICS 중계 4
    assert sum('EXPSTATUS=IDLE' in m for m in sent) == 1


def test_progress_comes_from_the_controller_not_the_ini(tmp_path, fakes):  # noqa: ANN001
    """`PCTREAD=` 는 `FRAME` 의 `BUFnLINES`/`BUFnHEIGHT` 에서 온다.

    시뮬은 `[readout] pctread_start/step` 대로 6/17/28/... 을 만들지만 실기는
    컨트롤러가 보고하는 값을 그대로 흘려보낸다 -- 그래서 6 이 아니라 25 의
    배수(height=4, 틱 4회)가 나와야 한다.  **이 코드는 시퀀서를 고치지 않고
    바뀐다** 는 것이 `readout()` 을 제너레이터로 만든 이유다.
    """
    sent, _ = drive(tmp_path, fakes,
                    ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go'])
    # 획득 완료 메시지도 `PCTREAD=100` 을 싣는다 (레거시 형태) -- 진행률
    # 보고와는 다른 것이므로 뺀다.
    pct = [m.split('PCTREAD=')[1].split()[0] for m in sent
           if 'PCTREAD=' in m and 'Acquisition Complete.' not in m]
    assert pct, '진행률이 하나도 안 나왔다'
    assert '6' not in pct[:1], 'ini 의 시뮬 모델(6부터)이 새어 나왔다'
    # height=4 · 4틱이므로 라인 진행이 25/50/75/(99) 다.  99 는 완료 전
    # 상한이고, 100 은 프레임이 확정된 뒤에만 나간다.
    assert all(int(x) in (25, 50, 75, 99) for x in pct), pct
    assert [int(x) for x in pct] == sorted(int(x) for x in pct), pct
    assert len(set(pct)) == len(pct), '같은 값을 되풀이해 보냈다: %r' % pct
    assert int(pct[-1]) <= 99, '완료 전에 100 을 내면 획득 완료가 앞당겨진다'


# ---------------------------------------------------------------------------
# 두 컨트롤러 병렬 독출 (목 지시 2026-08-24)
# ---------------------------------------------------------------------------

def test_frame_events_name_each_controller_in_completion_order(tmp_path):  # noqa: ANN001
    """`readout_events()` 가 컨트롤러별 완료를 **끝난 순서대로** 낸다 (1-C).

    `readout()` 은 진행률 정수만 흘려보내므로 "어느 컨트롤러가 끝났나" 를
    표현할 자리가 없었다.  NT 를 느리게 만들면 MK 가 먼저 나와야 한다 --
    그 순서가 곧 실기의 시차이고, `acq_per_frame` 기본값을 정할 근거다.
    """
    mk = FakeArchon(width=NX, height=NY, readout_ticks=2, tick=0.02)
    nt = FakeArchon(width=NX, height=NY, readout_ticks=8, tick=0.05)
    mk.start(); nt.start()
    try:
        cfg, acfg, nt_port = make_cfgs(tmp_path, mk, nt)
        acfg.full_flush_on_erase = False

        async def run():  # noqa: ANN202
            app = IcsArchon(cfg, acfg)
            app.backend.ctrls['NT'].link.port = nt_port
            await app.start()
            try:
                for tag in ('MK', 'NT'):
                    await app.backend.initialize(
                        'K' if tag == 'MK' else 'N', '20260824.000001')
                got = []
                async for kind, value in app.backend.readout_events('K'):
                    got.append((kind, value))
                return got
            finally:
                await app.stop()

        events = asyncio.run(run())
    finally:
        mk.shutdown(); nt.shutdown()
    frames = [v for k, v in events if k == 'frame']
    assert frames == ['MK', 'NT'], (
        '완료 순서가 아니다 (NT 를 4배 느리게 뒀다): %r' % frames)
    assert any(k == 'progress' for k, _v in events), '진행률이 하나도 안 나왔다'
    # 진행률은 master 것만 -- 100 은 시퀀서 몫이라 여기서 내지 않는다.
    assert all(v < 100 for k, v in events if k == 'progress'), events


@pytest.mark.parametrize('per_frame', [False, True])
def test_acq_per_frame_switch_keeps_the_four_messages(tmp_path, fakes, per_frame):  # noqa: ANN001
    """스위치를 켜든 끄든 **`Acquisition Complete.` 는 4회**다.

    바뀌는 것은 개수가 아니라 **언제 나가나** 뿐이다 -- 개수가 곧 규약이다
    (DevNote 3장 2항).  꺼짐이 기본이고 그때가 종전 거동(같은 틱 4개)이다.
    """
    cfg, acfg, nt_port = make_cfgs(tmp_path, fakes.mk, fakes.nt)
    cfg.readout.acq_per_frame = per_frame
    sent, _ = asyncio.run(_drive(cfg, acfg, nt_port,
                                 ['OBS>ICS dark begin', 'OBS>ICS exp 0',
                                  'OBS>ICS go']))
    acq = [m for m in sent if 'Acquisition Complete.' in m]
    assert len(acq) == 4, acq
    assert sum('Wrote' in m for m in sent) == 8
    assert sum('EXPSTATUS=IDLE' in m for m in sent) == 1
    if per_frame:
        # 컨트롤러 묶음으로 나간다 -- MK(M/K) 가 먼저, 그 다음 NT(N/T).
        who = [m.split('.IC>')[0] for m in acq]
        assert set(who[:2]) == {'M', 'K'}, who
        assert set(who[2:]) == {'N', 'T'}, who


# ---------------------------------------------------------------------------
# 산출물
# ---------------------------------------------------------------------------

def test_pair_of_files_with_spec_geometry_and_pixels(tmp_path, fakes):  # noqa: ANN001
    """pair 2파일 · 선언 기하 · 픽셀 값 · 2880B 정렬."""
    import numpy as np
    from astropy.io import fits

    drive(tmp_path, fakes,
          ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go'])
    got = sorted(os.path.basename(p) for p in
                 glob.glob(str(tmp_path / 'rawdata' / '*.fits')))
    assert len(got) == 2, got
    assert got[0].endswith('.MK.fits') and got[1].endswith('.NT.fits')
    assert got[0].startswith('KMTK.'), 'KASI(실험실) <SITE> 가 아니다'
    assert got[0][:-8] == got[1][:-8], 'pair 의 이름 줄기가 다르다'

    for name in got:
        path = str(tmp_path / 'rawdata' / name)
        assert os.path.getsize(path) % 2880 == 0
        with fits.open(path) as hdul:
            hdu = hdul[0]
            assert hdu.header['NAXIS1'] == NX
            assert hdu.header['NAXIS2'] == NY
            # 가짜가 낸 결정적 패턴이 그대로 -- 배치·엔디언·BZERO 가 다 맞다
            # (기준값은 프레임 번호에 따라 달라지므로 증분으로 본다)
            flat = hdu.data.reshape(-1).astype('int64')
            assert np.array_equal(flat - flat[0],
                                  np.arange(NX * NY, dtype='int64'))


def test_header_carries_the_facts_only_the_controller_knows(tmp_path, fakes):  # noqa: ANN001
    """`CTRLnSN`(BACKPLANE_ID) · `Cn_TEMP`(STATUS) · `DATASRC` · `ICSBUILD`.

    **이 셋이 MEF 의 placeholder 를 없애는 자리다** (base.py `controller_info`
    머리말).  그리고 `Cn_*` 는 **양쪽 파일에 같은 값**이어야 한다 (5.9절).
    """
    from astropy.io import fits
    import ics_archon

    drive(tmp_path, fakes,
          ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go'])
    heads = {}
    for path in glob.glob(str(tmp_path / 'rawdata' / '*.fits')):
        with fits.open(path) as hdul:
            heads[os.path.basename(path).split('.')[-2]] = dict(
                hdul[0].header)

    assert set(heads) == {'MK', 'NT'}
    mk, nt = heads['MK'], heads['NT']

    assert mk['DATASRC'].strip() == 'ARCHON_SCIENCE'
    assert mk['ICSBUILD'].strip() == ics_archon.build_id()
    # 두 대분을 색인 자리로 -- C1/CTRL1 은 "내 컨트롤러" 가 아니라 MK 고정이다
    for n in (1, 2):
        assert mk['CTRL%dSN' % n].strip() == '0024498A715E301C'
        assert mk['CTRL%dCFG' % n].strip() == 'test'      # ACF 파일명
        # 규격 5.6.1절 -- science 10자리 (Backplane + Mod1·2·3·4·5·8·9·10·11).
        # v1.5 전에는 잠정 5자리(BACKPLANE + MOD5~8)였고 견본과 갈려 있었다.
        assert len(mk['C%d_TEMP' % n].split()) == 10
        assert len(mk['C%d_VOLT' % n].split()) == 7       # 전원 레일 7개
        assert len(mk['C%d_CURR' % n].split()) == 7
    # 5.9절 "반드시 동일" -- pair 상이 7장만 다르다
    for card in ('C1_TEMP', 'C1_VOLT', 'C2_CURR', 'CTRL1SN', 'DATE-OBS'):
        assert mk[card] == nt[card], card
    assert mk['DETID'].strip() == 'MK' and nt['DETID'].strip() == 'NT'

    # 원천이 아직 없는 것은 sentinel 로 남아야 한다 -- 값을 지어내지 않는다
    assert mk['CCDTEMP'].strip() == '-999.99'
    assert mk['DEWPRES'].strip() == '9.99e-9'
    assert mk['RDMODE'].strip() == 'NORMAL'    # ACF 이름에 fast/comp/slow 없음


def test_imagetyp_and_dateobs_are_real_values_not_sentinels(tmp_path, fakes):  # noqa: ANN001
    """5.4절 카드는 sentinel 조차 금지다 -- 값이 실려야 한다."""
    from astropy.io import fits

    drive(tmp_path, fakes,
          ['OBS>ICS projid ENG', 'OBS>ICS object M31',
           'OBS>ICS exp 2', 'OBS>ICS go'])
    path = glob.glob(str(tmp_path / 'rawdata' / '*.MK.fits'))[0]
    with fits.open(path) as hdul:
        h = hdul[0].header
    assert h['IMAGETYP'].strip() == 'OBJECT'
    assert h['OBJECT'].strip() == 'M31'
    assert h['EXPTIME'] == 2
    assert h['DATE-OBS'].strip().startswith('20')
    assert h['FILENAME'].strip() == os.path.basename(path)[:-5]


# ---------------------------------------------------------------------------
# 제어 시퀀스
# ---------------------------------------------------------------------------

def test_control_sequence_order_matches_the_verified_script(tmp_path, fakes):  # noqa: ANN001
    """POWERON -> WCONFIG/APPLYALL -> LOADPARAMS -> FRAME 폴링 -> FETCH.

    **v1.0 계보의 순서를 바꾸지 않았다** 는 확인이다.  ACF 적용이 전원보다
    앞이고(설정 없이 전원을 올리지 않는다), FETCH 는 프레임 완료 뒤다.
    """
    _, app = drive(tmp_path, fakes,
                   ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go'])
    seen = fakes.mk.seen
    order = [c for c in seen if c in ('CLEARCONFIG', 'APPLYALL', 'POWERON',
                                      'LOADPARAMS', 'POWEROFF')
             or c.startswith('FETCH')]
    assert order[0] == 'CLEARCONFIG'
    assert order[1] == 'APPLYALL'
    assert order[2] == 'POWERON'
    assert order.index('LOADPARAMS') > order.index('POWERON')
    fetch = [i for i, c in enumerate(order) if c.startswith('FETCH')]
    assert fetch, 'FETCH 가 나가지 않았다'
    assert fetch[0] > order.index('LOADPARAMS')
    # 종료에서 전원을 끈다 -- 켠 채로 끝나는 것은 검출기 쪽 위험이다
    assert order[-1] == 'POWEROFF'
    assert not app.backend.ctrls['MK'].link.connected


def test_acf_is_applied_once_not_per_frame(tmp_path, fakes):  # noqa: ANN001
    """`initialize()` 는 프레임마다 CCD 4회 오지만 `APPLYALL` 은 한 번이다.

    컨트롤러당 두 chip 이므로 걸러 주지 않으면 2회, 프레임마다 되풀이하면
    노출 사이가 초 단위로 벌어진다.
    """
    drive(tmp_path, fakes,
          ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go 2'])
    assert fakes.mk.seen.count('APPLYALL') == 1
    assert fakes.mk.seen.count('POWERON') == 1
    # LOADPARAMS 는 프레임마다: flush 1 + 노출 1 = 프레임당 2, 2프레임 = 4
    assert fakes.mk.seen.count('LOADPARAMS') == 4


def test_erase_flushes_both_controllers_not_just_the_master(tmp_path, fakes):  # noqa: ANN001
    """시퀀서는 master(K) 한 번만 부르지만 **두 대 다 비워야 한다.**

    NT 를 안 비우면 그쪽 chip 에 앞 프레임의 잔상이 남는다 -- master 만
    flushing 한 것은 레거시 IC 구조의 관례이고 실기의 사실이 아니다.
    """
    drive(tmp_path, fakes,
          ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go'])
    assert fakes.nt.seen.count('LOADPARAMS') == 2     # flush + 노출
    assert fakes.nt.seen.count('POWERON') == 1


def test_geometry_mismatch_refuses_before_fetch(tmp_path):  # noqa: ANN001
    """`samplemode`(32bit 표본)면 **fetch 앞에서** 거부한다.

    바이트 수가 정확히 2배가 되는데 기하는 선언과 같으므로 픽셀 비교로는 안
    잡힌다 (DevNote 11.22 (3)).  fetch 는 수십 초가 걸리므로 그 뒤에 거절하면
    그 시간을 버린다 -- FETCH 가 아예 나가지 않아야 한다.
    """
    two = TwoFakes(samplemode=1)
    try:
        sent, _ = drive(tmp_path, two,
                        ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go'])
    finally:
        two.close()
    assert not any(c.startswith('FETCH') for c in two.mk.seen)
    assert not glob.glob(str(tmp_path / 'rawdata' / '*.fits'))
    # 규약은 지킨다 -- 저장이 실패해도 획득 완료는 이미 나갔다
    assert sum('Acquisition Complete.' in m for m in sent) == 4
    assert any('ERROR' in m for m in sent), '저장 실패가 통보되지 않았다'


def test_status_timeout_does_not_lose_the_frame(tmp_path):  # noqa: ANN001
    """STATUS 가 늦으면 텔레메트리를 끄고 **취득은 계속한다.**

    labtest v1.1 의 회귀 1번이 여기서 났다 -- 시한 초과가 프로토콜을 어긋내
    두 명령 뒤에 취득이 죽었다.  카드 몇 장보다 취득이 우선이므로 `Cn_*` 는
    `NC` 로 실리고 프레임은 나와야 한다.
    """
    from astropy.io import fits

    two = TwoFakes(status_delay=1.0)
    try:
        cfg, acfg, nt_port = make_cfgs(tmp_path, two.mk, two.nt)
        acfg.status_timeout = 0.1
        sent, _ = asyncio.run(_drive(
            cfg, acfg, nt_port,
            ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go']))
    finally:
        two.close()
    assert sum('Acquisition Complete.' in m for m in sent) == 4
    path = glob.glob(str(tmp_path / 'rawdata' / '*.MK.fits'))
    assert path, '프레임을 잃었다 -- STATUS 실패가 취득을 죽였다'
    with fits.open(path[0]) as hdul:
        assert hdul[0].header['C1_TEMP'].strip() == 'NC'
        # 컨트롤러 정체는 SYSTEM 에서 오므로 살아 있어야 한다
        assert hdul[0].header['CTRL1SN'].strip() == '0024498A715E301C'


# ---------------------------------------------------------------------------
# 자잘한 것
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('name, want', [
    ('acf/KMTNet_Sci_fast_med_U13.acf', 'FAST'),
    ('KMTNet_Sci_comp_med_U13.acf', 'COMP'),
    ('/x/KMTNet_Sci_slow_sens_U23.acf', 'SLOW'),
    ('KMTA_SCI_101_R2609.1.acf', ''),          # 못 알아보면 빈 문자열
    ('', ''),
])
def test_rdmode_is_derived_from_the_acf_name(name, want):  # noqa: ANN001
    """컨트롤러는 적용된 ACF 이름을 보고하지 않는다 (매뉴얼 p.54).

    호스트가 아는 유일한 근거가 파일명이다.  **못 알아보면 빈 문자열**이라야
    한다 -- `'NORMAL'` 을 만들어 넣으면 "유도 실패" 와 "정말 NORMAL" 이
    구별되지 않는다.
    """
    assert rdmode_from_acf(name) == want


def test_ini_validate_warns_when_a_controller_is_missing():
    """`[node] ccds` 에 있는데 주소가 없으면 그 파일은 생기지 않는다."""
    cfg = acfg_mod.ArchonCfg()
    notes = acfg_mod.validate(cfg, ('K', 'M', 'T', 'N'))
    assert any('살아 있는 컨트롤러가 없다' in n for n in notes)
    cfg.hosts = {'MK': '10.0.0.13'}
    cfg.acf = {'MK': 'x.acf'}
    assert cfg.active_tags(('K', 'M', 'T', 'N')) == ('MK',)
    assert cfg.index_of('MK') == 1 and cfg.index_of('NT') == 2


def test_pipelined_frames_do_not_steal_each_others_state(tmp_path):  # noqa: ANN001
    """**앞 프레임의 저장이 뒤 프레임과 겹쳐도 서로를 망치지 않는다.**

    저장은 `write_delay` 뒤에 백그라운드로 돈다 -- 그 사이 다음 프레임이 이미
    `LOADPARAMS` 를 냈을 수 있다.  프레임 상태를 컨트롤러 필드에 두면 두 가지가
    깨진다: ① 앞 프레임의 저장이 "직전 프레임 번호" 를 뒤 프레임의 것으로 읽어
    **엉뚱한 프레임을 기다린다** ② 앞 프레임의 뒷정리가 뒤 프레임의 "노출을
    걸었다" 표시를 지워 **이중 노출**이 된다.

    `write_delay` 를 프레임 간격보다 크게 잡아 그 겹침을 강제한다.
    `ics_sim` 이 같은 부류를 두 번 겪었다 (DevNote 12.10 · 11.20 critical).
    """
    # 버퍼 3개(Archon 기본) -- 늦은 저장이 버퍼 재활용에 걸리지 않게 한다.
    # BIGBUF(2개)에서 늦으면 어떻게 되는지는 아래 시험이 따로 본다.
    two = TwoFakes(nbuf=3)
    try:
        cfg, acfg, nt_port = make_cfgs(tmp_path, two.mk, two.nt)
        cfg.timing.write_delay = 50.0        # 축척 0.02 -> 1초
        sent, _ = asyncio.run(_drive(
            cfg, acfg, nt_port,
            ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go 2'],
            settle=3.0))
    finally:
        two.close()

    files = sorted(os.path.basename(p) for p in
                   glob.glob(str(tmp_path / 'rawdata' / '*.fits')))
    assert len(files) == 4, files
    numbers = {name.split('.')[2] for name in files}
    assert len(numbers) == 2, files          # 프레임마다 다른 번호
    # LOADPARAMS = 프레임당 (flush 1 + 노출 1).  하나라도 더 나가면 이중 노출이다.
    assert two.mk.seen.count('LOADPARAMS') == 4, two.mk.seen
    assert two.nt.seen.count('LOADPARAMS') == 4
    assert sum('Wrote' in m for m in sent) == 16      # 프레임 2 x (CB 4 + 중계 4)

    # **각 프레임이 자기 자료를 담았나.**  가짜는 픽셀에 프레임 번호를 섞으므로
    # (`fake_archon.pixels`) 앞 프레임의 저장이 뒤 프레임의 자료를 가져갔으면
    # 두 노출의 기준값이 같아진다 -- 그것이 이 시험의 판별점이다.
    from astropy.io import fits
    base = {}
    for name in files:
        with fits.open(str(tmp_path / 'rawdata' / name)) as hdul:
            base.setdefault(name.split('.')[2], set()).add(
                int(hdul[0].data.reshape(-1)[0]))
    assert len(base) == 2, base
    for num, values in base.items():
        assert len(values) == 1, ('pair 두 파일의 프레임이 다르다', num, values)
    assert len({v for s_ in base.values() for v in s_}) == 2, (
        '두 노출이 같은 프레임 자료를 담았다 -- 저장이 남의 프레임을 가져갔다: %r'
        % base)


def test_a_recycled_buffer_is_refused_instead_of_writing_wrong_pixels(tmp_path):  # noqa: ANN001
    """**BIGBUF 는 버퍼가 둘뿐이다** -- 저장이 늦으면 앞 프레임이 덮인다.

    노출 1회가 프레임 **2개**(flush + 취득)를 만들므로, 버퍼 2개 구성에서는
    다음 노출이 이 프레임의 버퍼를 정확히 덮는다.  덮인 뒤에 fetch 하면 raw 한
    장이 **남의 노출 픽셀**을 담고 헤더는 이 프레임의 것이라 아무 경고도 없다 --
    아카이브에 들어가면 되돌릴 수 없는 오염이다.

    그래서 fetch 앞에서 버퍼의 프레임 번호를 대조하고, 어긋나면 **저장하지
    않는다.**  파일 한 장을 잃는 것이 틀린 파일을 남기는 것보다 낫다.

    ⚠️ 실기에서는 프레임이 ~40초, `write_delay` 가 3.4초라 이 경합이 나지
    않는다 -- 여기서는 `write_delay` 를 프레임 간격보다 크게 잡아 강제한다.
    독출 시간 실측 뒤에 여유를 다시 재는 것이 검토사항이다.
    """
    from astropy.io import fits

    two = TwoFakes(nbuf=2)                 # BIGBUF=1 구성
    try:
        cfg, acfg, nt_port = make_cfgs(tmp_path, two.mk, two.nt)
        # **저장을 프레임 3개 뒤로 밀어** 버퍼가 반드시 재활용되게 한다.
        # (DARK 의 적분 시간이 컨트롤러로 가게 된 뒤로는 exp 1 이 프레임 하나를
        #  1초 늦추므로, 종전 값(50)으로는 경합이 재현되지 않았다.)
        cfg.timing.write_delay = 400.0     # 축척 0.02 -> 8초
        sent, _ = asyncio.run(_drive(
            cfg, acfg, nt_port,
            ['OBS>ICS bias begin', 'OBS>ICS exp 0', 'OBS>ICS go 3'],
            settle=12.0))
    finally:
        two.close()

    files = sorted(os.path.basename(p) for p in
                   glob.glob(str(tmp_path / 'rawdata' / '*.fits')))
    assert len(files) < 6, '버퍼 재활용을 못 잡았다: %r' % files
    assert any('ERROR' in m for m in sent), '저장 실패가 통보되지 않았다'
    # 남은 파일은 **자기 프레임 자료**여야 한다 -- 틀린 픽셀을 쓴 파일이 없다.
    for name in files:
        num = int(name.split('.')[2])          # 노출 순서 (EXPNUM 은 1 부터)
        with fits.open(str(tmp_path / 'rawdata' / name)) as hdul:
            base = int(hdul[0].data.reshape(-1)[0])
        # 가짜의 프레임 번호 = 노출 순서 x 2 (flush 가 노출마다 하나 앞선다).
        # **남은 파일은 반드시 자기 프레임 자료여야 한다** -- 남의 픽셀을 담은
        # 파일이 하나라도 있으면 거부 대신 오염이 일어난 것이다.
        assert base == num * 2 * 1000, (name, base)


def test_a_cancelled_frame_does_not_poison_the_next_one(tmp_path, fakes):  # noqa: ANN001
    """⚠️ **취소된 프레임의 저장 표가 다음 프레임을 오염시키지 않는다.**

    ABORT 나 저장 실패로 `write_frame()` 이 안 불리면 그 프레임의 표를 아무도
    꺼내지 않는다.  종전에는 대기열이 FIFO 라 **다음 프레임의 저장이 그 낡은
    표를 집어 왔다** -- 파일마다 한 노출 뒤진 픽셀이 담기고 헤더는 새 프레임의
    것이라 경고가 한 줄도 안 뜬다 (2026-08-24 검토 blocker).

    이제 표에 프레임 이름이 붙고 저장 쪽이 **자기 것만** 집는다.
    """
    from ics_archon.archon.controller import ArchonController, FrameTicket
    cfg, acfg, _ = make_cfgs(tmp_path, fakes.mk, fakes.nt)
    ctrl = ArchonController('MK', acfg)

    old = FrameTicket(suffix='20260824.000001', prev_frame=0)
    mine = FrameTicket(suffix='20260824.000002', prev_frame=1)
    ctrl._queue.extend([old, mine])          # noqa: SLF001

    got = ctrl.take_ticket('20260824.000002')
    assert got is mine, '내 표가 아니라 앞 프레임의 표를 집었다'
    assert ctrl._queue == [], '버려야 할 표가 남았다'   # noqa: SLF001

    # 내 표가 아예 없으면 **집지 않는다** -- 남의 것을 쓰는 것보다 안 쓰는 편이 낫다
    ctrl._queue.append(old)                  # noqa: SLF001
    assert ctrl.take_ticket('20260824.000009') is None
    assert len(ctrl._queue) == 1             # noqa: SLF001


def test_dark_exposure_time_reaches_the_controller(tmp_path, fakes):  # noqa: ANN001
    """⚠️ **DARK 의 적분 시간이 컨트롤러에 전달된다** (labtest 방식).

    labtest 는 DARK 에도 `IntMS=<적분시간>` 을 넣어 **컨트롤러가** 적분을 잰다.
    v0.0 은 `IntMS=0` 으로 곧바로 읽어내 적분을 **호스트 카운트다운**이 재게
    했고, 그러면 `time_scale`·이벤트 루프 지연·`erase` 소요가 섞여 들어가는데
    헤더 `EXPTIME` 은 요청값이라 **조용히 어긋났다** (2026-08-24 blocker).

    계약에 `begin_exposure()` 훅을 넣어 시퀀서가 알려 준다.
    """
    drive(tmp_path, fakes,
          ['OBS>ICS dark begin', 'OBS>ICS exp 3', 'OBS>ICS go'])
    # 가짜 컨트롤러가 마지막으로 받은 IntMS -- flush(0) 뒤에 노출(3000) 이 온다
    wrote = [t for t in fakes.mk.config.values() if 'IntMS=' in t]
    assert wrote, fakes.mk.config
    assert wrote[-1].endswith('IntMS=3000'), (
        'DARK 의 적분 시간이 컨트롤러에 안 갔다 -- %r' % wrote)


def test_shutter_exposure_still_carries_its_time(tmp_path, fakes):  # noqa: ANN001
    """셔터 노출은 종전대로 `open_shutter(seconds)` 가 적분을 건다."""
    drive(tmp_path, fakes,
          ['OBS>ICS object M31', 'OBS>ICS exp 2', 'OBS>ICS go'])
    wrote = [t for t in fakes.mk.config.values() if 'IntMS=' in t]
    assert wrote[-1].endswith('IntMS=2000'), wrote

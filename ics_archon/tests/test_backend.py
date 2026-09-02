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

#: `LINECOUNT` 를 넣어 `ArchonController.lines_total` 경로(진행률 분모, DevNote 10.3)를
#: 실제로 밟게 한다.  가짜는 FRAMEMODE=0 모사라 HEIGHT(NY)와 같은 값이다.
ACF_TEXT = """[CONFIG]
TRIGOUTFORCE=0
TRIGOUTLEVEL=1
LINECOUNT=4
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
    # **감시는 끈다.**  ini 기본값이 켬이라 그대로 두면 이 시험이 사용자 홈의
    # `~/AIC/log/` 에 진짜 CSV 를 쌓고, 기동 시점에 링크를 잡아 시험이 세운
    # 가짜 컨트롤러와 왕복을 다툰다.  감시 자체는 `test_monitor.py` 가 자기
    # 임시 폴더에서 본다.
    acfg.monitor = False
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


def drive(tmp_path, fakes, script, full_flush=False):  # noqa: ANN001
    #: `full_flush` -- ERASE 를 전체 독출 flush 로 할지.  ⭐ **기본값이
    #: 2026-08-29 에 `false` 로 바뀌었다**(clock 개선으로 실기는 별도 erase 를
    #: 하지 않는다).  그 경로를 보는 시험만 켠다.
    cfg, acfg, nt_port = make_cfgs(tmp_path, fakes.mk, fakes.nt)
    acfg.full_flush_on_erase = bool(full_flush)
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
    """`PCTREAD=` 는 `FRAME` 의 `BUFnLINES` / ACF `LINECOUNT` 에서 온다.

    (이 가짜는 `FRAMEMODE=0` 이고 시험 ACF 에 `LINECOUNT` 가 없어 분모가 HEIGHT
    로 물러난다 -- 그래서 25 의 배수가 나온다.  split 판은 `test_ch10_reflection`.)

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
    # 가짜는 FRAMEMODE=0(LINES 상한 = HEIGHT = 4)이고 4틱이므로 25/50/75/(99).  99 는 완료 전
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
        # 구분자는 파이프다 (규격 5.6.1절, v1.6)
        assert len(mk['C%d_TEMP' % n].strip().split('|')) == 10
        assert len(mk['C%d_VOLT' % n].strip().split('|')) == 7   # 전원 레일 7개
        assert len(mk['C%d_CURR' % n].strip().split('|')) == 7
    # 5.9절 "반드시 동일" -- pair 상이 6장만 다르다 (v1.6: 7 -> 6)
    for card in ('C1_TEMP', 'C1_VOLT', 'C2_CURR', 'CTRL1SN', 'DATE-OBS'):
        assert mk[card] == nt[card], card
    assert mk['DETID'].strip() == 'MK' and nt['DETID'].strip() == 'NT'

    # 원천이 아직 없는 것은 sentinel 로 남아야 한다 -- 값을 지어내지 않는다
    assert mk['CCDTEMP'].strip() == '-999.99'
    assert mk['DEWPRES'].strip() == '9.99e-9'
    # ⭐ `RDMODE` 는 **더 이상 이 무리가 아니다** (2026-08-29) -- 저장소 ini 가
    # `NORMAL` 을 적어 두므로 원천이 있다(현행 ACF 여섯의 실제 모드, 운영자
    # 확정).  ACF 이름에 속도 토큰이 없어 유도는 빈손이고, 그때의 코드 기본값이
    # **`UNKNOWN`** 인 것은 `test_ini_cards.py` 와 `ics_sim` 쪽 시험이 지킨다 --
    # 여기서 보는 것은 **ini 값이 실제로 카드까지 닿는가** 다.
    assert mk['RDMODE'].strip() == 'NORMAL'


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
    """CLEARCONFIG/WCONFIG -> APPLYALL -> POWERON -> LOADPARAMS -> FRAME 폴링 -> FETCH.

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
    # LOADPARAMS 는 프레임마다 노출 1회.  ⭐ **flush 는 안 센다** --
    # `full_flush_on_erase` 기본값이 2026-08-29 에 `false` 로 바뀌었다
    # (clock 개선으로 실기는 별도 erase 를 하지 않는다).  켜면 프레임당 2다.
    assert fakes.mk.seen.count('LOADPARAMS') == 2


def test_erase_flushes_both_controllers_not_just_the_master(tmp_path, fakes):  # noqa: ANN001
    """시퀀서는 master(K) 한 번만 부르지만 **두 대 다 비워야 한다.**

    NT 를 안 비우면 그쪽 chip 에 앞 프레임의 잔상이 남는다 -- master 만
    flushing 한 것은 레거시 IC 구조의 관례이고 실기의 사실이 아니다.

    ⚠️ **flush 를 명시적으로 켠다** -- 기본값이 2026-08-29 에 `false` 로 바뀌었다
    (clock 개선으로 실기는 별도 erase 를 하지 않는다).  그래도 **켠 배치에서는
    두 대 다 비워야 한다**는 규칙이 유효하므로 시험은 남긴다.
    """
    drive(tmp_path, fakes,
          ['OBS>ICS dark begin', 'OBS>ICS exp 1', 'OBS>ICS go'],
          full_flush=True)
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
        # **전 자리 결측도 자리 수만큼 `NC` 다** (규격 5.6.1절 "자리는 비우지
        # 않는다") -- 한 토큰짜리 `'NC'` 는 자리 수가 1이 되어 읽는 쪽에
        # 모듈 구성이 달라 보인다.
        from ics_sim import rawhdr
        assert hdul[0].header['C1_TEMP'].strip() ==             '|'.join(['NC'] * len(rawhdr.TEMP_MODS))
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
    한다 -- 여기서 값을 만들어 넣으면 "유도 실패" 와 "정말 그 값" 이
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
        # ⚠️ **flush 를 켜서 노출당 프레임을 2개로** 만든다 -- 겹침을 재현하는
        # 조건이다.  기본값은 2026-08-29 부터 `false` 다.
        acfg.full_flush_on_erase = True
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


def test_fetch_buffer_ring_is_bounded_reused_and_returned():
    """**호스트 수신 버퍼는 링이다** (`[archon] fetch_buffers`, 2026-08-29).

    종전에는 프레임마다 344 MiB 를 새로 잡았고 저장 태스크 수에 제한이 없어서,
    저장이 밀리면 **메모리가 조용히 늘었다.**  링으로 두면 셋이 생긴다:

    1. **상한** -- `N x 344 MiB` 를 넘지 않는다
    2. **재사용** -- 할당 비용(344 MiB 에 0.81초)이 사라진다
    3. ⭐ **역압** -- 다 차면 기다리고, **기다린 사실이 세어진다.**  그 수가
       `fetch_buffers` 가 충분한지를 **추정이 아니라 실기로** 답하게 한다.
    """
    from ics_archon.archon.controller import ArchonController
    acfg = acfg_mod.ArchonCfg()
    acfg.fetch_buffers = 2
    ctrl = ArchonController('MK', acfg)
    assert ctrl._bufpool.qsize() == 2                      # noqa: SLF001

    async def go():
        a = await ctrl._take_buffer(100)                   # noqa: SLF001
        b = await ctrl._take_buffer(100)                   # noqa: SLF001
        assert a is not b and len(a) == len(b) == 100
        assert ctrl._bufpool.qsize() == 0                  # noqa: SLF001

        # ⭐ 링이 비면 **기다린다** -- 그냥 새로 만들면 상한이 없어진다
        pending = asyncio.ensure_future(ctrl._take_buffer(100))  # noqa: SLF001
        await asyncio.sleep(0.05)
        assert not pending.done(), '버퍼가 없는데 그냥 내줬다 -- 상한이 없다'

        ctrl.release_buffer(a)
        got = await pending
        assert got is a, '반납한 버퍼를 재사용하지 않았다'
        assert ctrl.buf_waits == 1 and ctrl.buf_wait_s > 0, (
            '기다린 사실이 안 세어졌다 -- fetch_buffers 가 충분한지 실기가 '
            '답할 수 없게 된다')

        # 다 돌려주면 처음 크기로 돌아온다 (새지 않는다)
        ctrl.release_buffer(b)
        ctrl.release_buffer(got)
        assert ctrl._bufpool.qsize() == 2                  # noqa: SLF001

        # 기하가 바뀌면 새로 잡는다 -- 재사용이 목적이지 강제가 아니다
        big = await ctrl._take_buffer(200)                 # noqa: SLF001
        assert len(big) == 200

    asyncio.run(go())


def _fs(frame, buf=0, base=0x1000, nx=4, ny=4):
    """시험용 `FrameStatus` 하나."""
    from ics_archon.archon import parse
    return parse.FrameStatus(frame=frame, buf=buf, width=nx, height=ny,
                             samplemode=0, base=base, lines=ny,
                             wbuf=0, write_lines=0, write_height=0)


def _stub_fetch(ctrl, before_frame, after_frame, nbytes, rbuf=1, wbuf=(0, 0)):
    """`fetch()` 의 왕복을 가짜로 채운다 -- fetch **전후**의 `FRAME` 을 정한다.

    `rbuf`/`wbuf` 로 잠금 상태도 정한다 (`RBUF`/`WBUF`, 매뉴얼 p.50).
    """
    seen = {'queries': 0, 'cmds': []}

    async def query(cmd, timeout=None):        # noqa: ANN001, ARG001
        seen['queries'] += 1
        first = seen['queries'] == 1
        frame = before_frame if first else after_frame
        return {'BUF1FRAME': str(frame), 'BUF1COMPLETE': '1',
                'RBUF': str(rbuf), 'WBUF': str(wbuf[0] if first else wbuf[1])}

    async def cmd(name, timeout=None):         # noqa: ANN001, ARG001
        seen['cmds'].append(name)
        return b''

    def link_fetch(base, n, timeout, on_block, out):   # noqa: ANN001, ARG001
        out[:] = bytes(n)
        return out

    ctrl.query = query
    ctrl.cmd = cmd
    ctrl.link.fetch = link_fetch
    return seen


def test_a_frame_overwritten_during_fetch_is_caught_after_the_fetch():
    """**fetch 뒤 재대조** (`[archon] recheck_after_fetch`, 2026-08-30).

    fetch 앞의 대조는 **직전 한 순간**만 본다.  fetch 자체가 수 초 걸리므로
    (실측 3.2~3.5초) 그 사이에 덮이는 창은 앞 대조가 못 본다 -- `lock_buffer`
    가 켜져 있으면 `LOCKn` 이 그 창을 막지만, **끄면 막는 것이 없다.**

    ⭐ 여기서 보는 것은 "**받아 온 뒤에라도 버린다**" 는 성질이다.  3~4초를
    버리는 셈이지만 대안은 두 노출이 섞인 raw 한 장을 **경고 없이** 쓰는
    것이다(헤더는 이 프레임의 것이라 나중에 봐도 못 가른다).
    """
    from ics_archon.archon.controller import ArchonController
    from ics_archon.archon.protocol import ArchonError

    acfg = acfg_mod.ArchonCfg()
    acfg.lock_buffer = False               # LOCK 을 끈 쪽이 이 방어의 대상이다
    acfg.recheck_after_fetch = True
    ctrl = ArchonController('MK', acfg)
    seen = _stub_fetch(ctrl, before_frame=7, after_frame=9, nbytes=32)

    with pytest.raises(ArchonError) as err:
        asyncio.run(ctrl.fetch(_fs(7), 32))
    assert '덮였다' in str(err.value)
    assert seen['queries'] == 2, 'fetch 뒤에 다시 안 물어봤다'
    assert not seen['cmds'], 'lock_buffer=false 인데 LOCK 을 보냈다'
    # ⚠️ 버려도 **버퍼는 링에 돌려준다** -- 안 그러면 몇 번의 실패 뒤에
    # 링이 비어 영구히 막힌다.
    assert ctrl._bufpool.qsize() == acfg.fetch_buffers      # noqa: SLF001


def test_the_recheck_can_be_turned_off_and_then_nothing_watches_the_gap():
    """끄면 왕복이 안 는다 -- 그리고 **그 창을 보는 것이 없어진다.**

    성질을 못박아 두는 시험이다: 껐을 때 조용해지는 것이 의도된 동작이고,
    그래서 `lock_buffer` 와 **둘 다 끄면** 기동 교차검사가 알린다.
    """
    from ics_archon.archon.controller import ArchonController

    acfg = acfg_mod.ArchonCfg()
    acfg.lock_buffer = False
    acfg.recheck_after_fetch = False
    ctrl = ArchonController('MK', acfg)
    seen = _stub_fetch(ctrl, before_frame=7, after_frame=9, nbytes=32)

    data = asyncio.run(ctrl.fetch(_fs(7), 32))
    assert len(data) == 32
    assert seen['queries'] == 1, '껐는데도 fetch 뒤에 물어봤다'


def test_the_recheck_never_fires_while_the_buffer_is_locked():
    """`lock_buffer=true` 면 재대조는 **절대 안 걸린다** -- 값이 안 든다는 근거다.

    잠긴 버퍼는 안 바뀌므로 기본을 `true` 로 둬도 정상 취득에는 영향이 없다.
    """
    from ics_archon.archon.controller import ArchonController

    acfg = acfg_mod.ArchonCfg()
    acfg.lock_buffer = True
    acfg.recheck_after_fetch = True
    ctrl = ArchonController('MK', acfg)
    seen = _stub_fetch(ctrl, before_frame=7, after_frame=7, nbytes=32)

    data = asyncio.run(ctrl.fetch(_fs(7), 32))
    assert len(data) == 32
    assert seen['cmds'] == ['LOCK1', 'LOCK0'], seen['cmds']


def test_wait_frame_recovers_when_the_frame_counter_wraps():
    """**되감김에서 노출을 잃지 않는다** (2026-08-30 수정).

    종전에는 `next_frame()` 이 `frame > prev` 로만 찾아, 카운터가 한 바퀴 돌면
    **어떤 버퍼도 조건을 못 만족해** `frame_timeout`(300초)까지 기다리다
    노출을 잃었다.  ⭐ fail-closed 이긴 하지만(틀린 자료가 아니라 실패),
    **guide 유닛은 16비트면 하룻밤 안에 도달**한다(1초 주기 18시간).

    ⚠️ 폭을 모르므로 크기로 판별하지 않는다 -- 노출 직전의 기준선
    (`FrameTicket.prev_frames`) 대비 **변화**로 판별한다.
    """
    from ics_archon.archon.controller import ArchonController, FrameTicket

    acfg = acfg_mod.ArchonCfg()
    acfg.frame_poll = 0.0
    ctrl = ArchonController('MK', acfg)
    calls = {'n': 0}

    async def query(cmd, timeout=None):        # noqa: ANN001, ARG001
        calls['n'] += 1
        # 첫 폴에서는 아직 옛 프레임뿐이고, 그 다음에 되감긴 0 이 들어온다.
        new = '0' if calls['n'] > 1 else '65534'
        return {'RBUF': '1', 'WBUF': '0',
                'BUF1FRAME': '65535', 'BUF1COMPLETE': '1',
                'BUF2FRAME': new, 'BUF2COMPLETE': '1',
                'BUF2WIDTH': '4', 'BUF2HEIGHT': '4', 'BUF2SAMPLE': '0',
                'BUF2BASE': '4096', 'BUF2LINES': '4'}
    ctrl.query = query

    ticket = FrameTicket(suffix='20260830.000001', prev_frame=65535,
                         prev_frames=(65535, 65534, -1))

    async def go():
        async for _pct in ctrl.wait_frame(ticket):
            pass
    asyncio.run(go())

    assert ticket.ready is not None, '되감김에서 프레임을 못 찾았다'
    assert ticket.ready.frame == 0, ticket.ready


def test_lock_is_verified_against_rbuf_without_extra_round_trips():
    """⭐ **`LOCKn` 이 이 FW 에서 실제로 먹는지를 실기가 답하게 한다** (A-5 판단 ②).

    매뉴얼 p.50 의 `RBUF`(*"Current buffer number locked for reading"*)를 fetch
    앞의 덮임 대조가 **이미 읽는 `FRAME` 응답**에서 뽑는다 -- **왕복이 안 는다.**
    `WBUF` 는 fetch 전후를 재는데, 옮겨 갔으면 상태 플래그가 아니라 **엔진이
    실제로 다른 버퍼를 썼다**는 거동 증거다.

    ✅ 2026-09-01 실기: 두 FW 15/15 반영 (DevNote 10.4) -- A-5 판단 ② 종결.  이
    시험은 관측값을 담아 오는 경로의 **회귀 감시**로 남는다.  ⚠️ 이 시험이 재는
    것은 **우리 코드가 관측값을 제대로 담아 오는가**이지, 실기가 그렇게 답하는가가
    아니다 (DevNote 8.7 -- 매뉴얼도 가짜 컨트롤러도 판정 근거가 아니다).
    """
    from ics_archon.archon.controller import ArchonController

    acfg = acfg_mod.ArchonCfg()
    acfg.lock_buffer = True
    ctrl = ArchonController('MK', acfg)
    seen = _stub_fetch(ctrl, 7, 7, 32, rbuf=1, wbuf=(1, 2))

    asyncio.run(ctrl.fetch(_fs(7), 32))
    assert seen['cmds'] == ['LOCK1', 'LOCK0'], seen['cmds']
    assert seen['queries'] == 2, '왕복이 늘었다 -- 이미 읽는 응답에서 뽑아야 한다'
    assert ctrl.lock_rbuf == 1, 'RBUF 를 안 담아 왔다'
    assert (ctrl.lock_wbuf, ctrl.lock_wbuf_after) == (1, 2), (
        'WBUF 이동을 안 담아 왔다 -- 엔진이 버퍼를 옮겼다는 거동 증거다')


def test_a_lock_that_does_not_take_is_reported_not_swallowed(caplog):  # noqa: ANN001
    """⚠️ **`LOCK` 을 보냈는데 `RBUF` 가 안 따라오면 크게 알린다.**

    그 조합이면 **`LOCK` 에 기대면 안 된다** -- `recheck_after_fetch` 가 유일한
    방어가 된다.  조용히 넘기면 *"두 겹으로 막고 있다"* 고 믿으면서 실제로는 한
    겹도 없는 상태가 된다.
    """
    import logging
    from ics_archon.archon.controller import ArchonController

    acfg = acfg_mod.ArchonCfg()
    acfg.lock_buffer = True
    ctrl = ArchonController('MK', acfg)
    _stub_fetch(ctrl, 7, 7, 32, rbuf=0)        # 잠갔는데 RBUF 가 0 이다

    with caplog.at_level(logging.WARNING):
        asyncio.run(ctrl.fetch(_fs(7), 32))
    assert any('RBUF' in r.getMessage() for r in caplog.records), caplog.text
    assert ctrl.lock_rbuf == 0


def test_power_on_drops_save_tickets_left_over_from_the_previous_session():
    """**`POWERON` 에서 낡은 저장 표를 버린다** (2026-08-30 배선).

    ⚠️ CCD `POWERON` 은 카운터를 리셋하지 않는다 (2026-09-02 실측, DevNote 10.7) --
    버리는 이유는 번호가 아니라 "전원이 내려간 사이의 프레임은 자료가 아니다" 다.
    그 프레임은 버퍼에 없고 다시 못 받는다.  그런데 표를
    남겨 두면 다음 프레임의 저장이 **그 낡은 표**를 FIFO 로 집어, 파일마다 한
    노출 뒤진 픽셀이 담기고 헤더는 새 프레임의 것이라 **경고가 한 줄도 안
    뜬다** (`FrameTicket` 설명의 그 blocker).

    ⭐ **크게 잃는 것이 조용히 틀린 것보다 낫다** -- 표를 버리면 그 프레임은
    저장되지 않고, 그 사실이 경고로 남는다.
    """
    from ics_archon.archon.controller import ArchonController, FrameTicket

    acfg = acfg_mod.ArchonCfg()
    acfg.poweron_wait = 0.0
    ctrl = ArchonController('MK', acfg)
    ctrl._queue.extend([FrameTicket(suffix='20260830.000001', prev_frame=1),  # noqa: SLF001
                        FrameTicket(suffix='20260830.000002', prev_frame=2)])

    async def cmd(name, timeout=None):     # noqa: ANN001, ARG001
        return b''
    ctrl.cmd = cmd

    asyncio.run(ctrl.power_on())
    assert ctrl._queue == [], '전원을 다시 켰는데 낡은 표가 남았다'   # noqa: SLF001


def test_a_recycled_buffer_is_refused_instead_of_writing_wrong_pixels(tmp_path):  # noqa: ANN001
    """**BIGBUF 는 버퍼가 둘뿐이다** -- 저장이 늦으면 앞 프레임이 덮인다.

    노출 1회가 프레임 **2개**(flush + 취득)를 만들므로, 버퍼 2개 구성에서는
    다음 노출이 이 프레임의 버퍼를 정확히 덮는다.  덮인 뒤에 fetch 하면 raw 한
    장이 **남의 노출 픽셀**을 담고 헤더는 이 프레임의 것이라 아무 경고도 없다 --
    아카이브에 들어가면 되돌릴 수 없는 오염이다.

    그래서 fetch 앞에서 버퍼의 프레임 번호를 대조하고, 어긋나면 **저장하지
    않는다.**  파일 한 장을 잃는 것이 틀린 파일을 남기는 것보다 낫다.

    ⭐ **실측(2026-09-01, DevNote 10.4)으로 여유가 확인됐다** -- FETCH 는
    `IDLE`+3.4+3.2~3.5 ≈ 6.9초에 끝나는데 그 버퍼가 다시 쓰이는 것은 프레임 주기
    13.27초 뒤다 (**여유 ~6초**).  종전 주석의 "프레임 ~40초" 는 가정이었고 실제
    주기는 훨씬 짧다(독출 12.77 + 사강 0.5).
    여기서는 `write_delay` 를 프레임 간격보다 크게 잡아 경합을 강제한다.

    ⚠️ **flush 를 명시적으로 켠다** -- "노출 1회 = 프레임 2개" 가 이 시험의
    전제인데 기본값이 2026-08-29 에 `false`(프레임 1개)로 바뀌었다.
    """
    from astropy.io import fits

    two = TwoFakes(nbuf=2)                 # BIGBUF=1 구성
    try:
        cfg, acfg, nt_port = make_cfgs(tmp_path, two.mk, two.nt)
        acfg.full_flush_on_erase = True    # 노출당 프레임 2개 (이 시험의 전제)
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


def test_bias_is_zero_seconds_not_a_missing_hook(tmp_path, fakes, caplog):  # noqa: ANN001
    """⚠️ **`BIAS` 는 적분이 0초인 것이 정상이다** -- 결측이 아니다.

    종전에는 `_dark_seconds` 의 `0.0` 이 **"훅을 못 받았다"** 와 **"BIAS 라서
    0초다"** 를 겸해서, **정상 `BIAS` 마다 "적분 시간을 못 받았다" 경고**가
    떴다.  게다가 그 문구가 *"시퀀서에 begin_exposure 훅이 없다"* 였는데 훅은
    2026-08-24(`ecf3487`)부터 있다 -- **두 번 틀린 경고**다.

    실제로 쓰이는 값을 결측 표시로 쓰면 정상 동작이 경보가 되고, 그 소음이
    **진짜 결측을 덮는다.**  `RDMODE` 의 구 기본값 `'NORMAL'` 과 같은 부류다
    (2026-08-29 정정).
    """
    import logging
    with caplog.at_level(logging.WARNING, logger='ics_archon.hw'):
        drive(tmp_path, fakes,
              ['OBS>ICS bias begin', 'OBS>ICS exp 0', 'OBS>ICS go'])

    # ① BIAS 는 IntMS=0 이 맞는 값이다 -- 컨트롤러가 곧바로 읽어낸다
    wrote = [t for t in fakes.mk.config.values() if 'IntMS=' in t]
    assert wrote and wrote[-1].endswith('IntMS=0'), wrote

    # ② 그런데 그것을 결측으로 경고하면 안 된다
    noise = [r.getMessage() for r in caplog.records
             if '적분 시간을 못 받았다' in r.getMessage()]
    assert not noise, '정상 BIAS 인데 결측 경고가 떴다: %r' % noise

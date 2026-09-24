#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`[archon] ccdflush_first`/`ccdflush_every` -- 노출 전 CCD flush
(운영자 2026-09-04 · 기제 단순화 2026-09-05 · 둘로 가름 2026-09-14, DevNote 11.33 · 11.86-(12)).

science R2610+ 부터 flush 는 타이밍 스크립트의 `FlushFrame`(Prep+Flush)이고, 켜고 끄는 일은
**설정 메모리의 `FirstFlush` 한 줄**(`PARAMETER0`)이다.  science 는 노출마다 `LOADPARAMS` 를
내므로 메모리가 1 이면 코어가 `Start:` 첫 줄에서 `FlushFrame` 으로 뛰어 **매 노출 전**
Prep+Flush 가 돈다.  `LOADTIMING` 은 없다 -- 코어 리셋도, `Exposures=0` 고정도, 두 단계
검증도 필요 없다.  (종전 R2609 까지는 `LINE9/LINE10` 의 `#` 를 여닫고 LOADTIMING 을 냈고,
그 기제의 시험은 이 판에서 지웠다.)

지키려는 것:

* **되읽어 판정한다** -- 캐시가 아니라 `RCONFIG`.  앞 세션이 켜 둔 1 을
  되돌린다 (⚠️ 캐시는 왕복 실패에도 먼저 갈아 끼워져 못 믿는다).
* **바뀔 때만 쓴다** -- 이미 원하는 값이면 WCONFIG 없이 `False`.
* **앉았는지 확인한다** -- 안 앉았으면 `False` 와 오류 로그 (조용히 캐시로 물러나지 않는다).
* **슬롯 번호만 믿지 않는다** -- R2608 의 `PARAMETER0` 은 `ContinuousExposures` 다.  그
  자리에 이름이 다르면 쓰지 않고, 켜라고 했으면 경고하고 flush 없이 간다.
* **`LOADTIMING` 을 내지 않는다.**
"""

from __future__ import annotations

import asyncio
import io
import os

import pytest

import ics_archon  # noqa: F401

from icg_archon.config import IcgCfg  # noqa: E402
from ics_archon.archon.controller import ArchonController  # noqa: E402
from ics_archon.archon.protocol import ArchonError  # noqa: E402
from ics_archon.config import ArchonCfg  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCI_ACF = os.path.join(ROOT, 'acf', 'KMTC_SCI_101_STA0284_R2613_MK.acf')
GUIDE_ACF = os.path.join(ROOT, 'acf', 'KMTK_GUI_162_STA0201_R2622.acf')


class Ctrl(ArchonController):
    """실물 ACF 를 파싱한 진짜 컨트롤러 + 소켓만 가짜.

    `cmd()` 하나만 갈아 끼우므로 줄 번호 조회·키 정규화·`RCONFIG` 응답 검사가
    **전부 실제 코드**를 지난다.  ⭐ 컨트롤러 메모리(`_memory`)를 캐시(`config`)와
    **따로** 둔다 -- `WCONFIG` 가 앉은 것과 캐시가 바뀐 것을 가르기 위해서다
    (`stuck=True` 면 `WCONFIG` 가 앉지 않는 컨트롤러).

    ⭐ **실패를 넣을 수 있다** (DevNote 11.96) -- `fail_on` 글자(하나 또는 여럿)가
    든 명령을 모두 합쳐 `fail_times` 번 실패시킨다(`fail_exc`, 기본 `ArchonError`).
    `land=True` 면
    `WCONFIG` 를 **메모리에 앉힌 뒤** 던진다 -- 시한 초과(앉았는데 답만 잃었다)와,
    `_locked_thread` 가 스레드를 끝까지 기다린 뒤 올리는 취소가 그 꼴이다.
    ⚠️ `'=IntMS='` 처럼 `=` 로 감싸 맞출 것 -- `'IntMS'` 는 `NoIntMS` 에도 걸린다.
    """

    def __init__(self, acf: str = SCI_ACF, *, stuck: bool = False,
                 fail_on=(), fail_times: int = 1, fail_exc=None,  # noqa: ANN001
                 land: bool = False) -> None:
        cfg = ArchonCfg()
        cfg.acf = {'MK': acf}
        super().__init__('MK', cfg)
        self.parse_acf(acf)
        self.sent: list[str] = []
        self.stuck = stuck
        self.fail_on = (fail_on,) if isinstance(fail_on, str) else tuple(fail_on)
        self.fail_times = fail_times
        self.fail_exc = fail_exc or ArchonError
        self.land = land
        self._memory: dict[str, str] = dict(self.config)

    async def cmd(self, command: str, timeout: float = 0.0) -> bytes:  # noqa: ANN001
        self.sent.append(command)
        failing = (self.fail_times > 0
                   and any(s and s in command for s in self.fail_on))
        if failing:
            self.fail_times -= 1
            if not self.land:
                raise self.fail_exc('시험이 일부러 실패시킨 명령 -- %s' % command)
        if command.startswith('WCONFIG') and not self.stuck:
            key, _, val = command[11:].partition('=')
            self._memory[key] = val
        if failing:
            raise self.fail_exc('시험이 일부러 실패시킨 명령(앉은 뒤) -- %s' % command)
        if command.startswith('RCONFIG'):
            line = int(command[7:11], 16)
            for key, val in self._memory.items():
                if self.configline.get(key) == line:
                    return ('%s=%s' % (key, val)).encode('ascii')
            return b''
        return b''

    def writes(self) -> list[str]:
        return [c for c in self.sent if c.startswith('WCONFIG')]

    def loads(self) -> list[str]:
        return [c for c in self.sent if c in ('LOADTIMING', 'LOADPARAMS')]

    def flag(self) -> str | None:
        """컨트롤러 메모리의 `PARAMETER0` 값."""
        return self._memory.get('PARAMETER0')


def _slot_write(ctrl: Ctrl, value: str) -> str:
    return 'WCONFIG%04XPARAMETER0=%s' % (ctrl.configline['PARAMETER0'], value)


# -- 켜기 · 끄기 --------------------------------------------------------------


def test_turning_it_on_writes_one_line_and_no_loadtiming():
    """⭐ WCONFIG **한 줄** -- `PARAMETER0=FirstFlush=1`.  `LOADTIMING`/`LOADPARAMS` 는 없다."""
    ctrl = Ctrl()
    assert ctrl.flag() == 'FirstFlush=0', 'science ACF 원문은 0 이어야 한다'
    assert asyncio.run(ctrl.set_flush_param('FirstFlush', 1)) is True
    assert ctrl.writes() == [_slot_write(ctrl, 'FirstFlush=1')], ctrl.sent
    assert ctrl.loads() == [], ctrl.sent
    assert ctrl.flag() == 'FirstFlush=1'
    assert ctrl.config['PARAMETER0'] == 'FirstFlush=1'


def test_it_reads_back_before_and_after_writing():
    """되읽기 둘 -- 쓰기 전(판정)과 뒤(앉았나).  `set_config` 는 캐시를 먼저 바꾸므로
    뒤의 되읽기가 없으면 *"보냈다"* 를 *"앉았다"* 로 착각한다 (11.13 F5)."""
    ctrl = Ctrl()
    asyncio.run(ctrl.set_flush_param('FirstFlush', 1))
    reads = [i for i, c in enumerate(ctrl.sent) if c.startswith('RCONFIG')]
    write = ctrl.sent.index(ctrl.writes()[0])
    assert len(reads) == 2 and reads[0] < write < reads[1], ctrl.sent


def test_already_on_writes_nothing():
    ctrl = Ctrl()
    asyncio.run(ctrl.set_flush_param('FirstFlush', 1))
    assert asyncio.run(ctrl.set_flush_param('FirstFlush', 1)) is False
    assert len(ctrl.writes()) == 1, ctrl.writes()


def test_the_default_science_acf_is_off_so_off_writes_nothing():
    ctrl = Ctrl()
    assert asyncio.run(ctrl.set_flush_param('FirstFlush', 0)) is False
    assert ctrl.writes() == []
    assert ctrl.loads() == []


def test_turning_it_off_again_writes_zero():
    ctrl = Ctrl()
    asyncio.run(ctrl.set_flush_param('FirstFlush', 1))
    assert asyncio.run(ctrl.set_flush_param('FirstFlush', 0)) is True
    assert ctrl.writes()[-1] == _slot_write(ctrl, 'FirstFlush=0')
    assert ctrl.flag() == 'FirstFlush=0'


# -- 컨트롤러 메모리가 캐시와 다를 때 ---------------------------------------


def test_a_previous_session_left_it_on_and_the_option_off_restores_zero():
    """캐시(ACF 파일)는 0 인데 컨트롤러 메모리는 앞 세션의 1 -- 되읽어 알고 0 을 쓴다."""
    ctrl = Ctrl()
    ctrl._memory['PARAMETER0'] = 'FirstFlush=1'    # noqa: SLF001
    assert asyncio.run(ctrl.set_flush_param('FirstFlush', 0)) is True
    assert ctrl.writes() == [_slot_write(ctrl, 'FirstFlush=0')]
    assert ctrl.flag() == 'FirstFlush=0'


def test_controller_already_on_syncs_the_cache_without_writing():
    ctrl = Ctrl()
    ctrl._memory['PARAMETER0'] = 'FirstFlush=1'    # noqa: SLF001
    assert asyncio.run(ctrl.set_flush_param('FirstFlush', 1)) is False
    assert ctrl.writes() == []
    assert ctrl.config['PARAMETER0'] == 'FirstFlush=1', '캐시를 컨트롤러 값에 맞춘다'


# -- 실패 · 구판 ACF ----------------------------------------------------------


def test_a_write_that_did_not_land_is_reported(caplog):  # noqa: ANN001
    """⛔ 되읽은 값이 다르면 `False` + 오류 로그.  캐시로 물러나 *됐다* 고 하지 않는다."""
    ctrl = Ctrl(stuck=True)
    with caplog.at_level('ERROR'):
        assert asyncio.run(ctrl.set_flush_param('FirstFlush', 1)) is False
    assert ctrl.flag() == 'FirstFlush=0'
    assert any('did not land' in r.getMessage()
               for r in caplog.records), caplog.text


def test_an_acf_whose_slot_zero_is_another_parameter_is_left_alone(tmp_path, caplog):  # noqa: ANN001
    """R2608 꼴 -- `PARAMETER0="ContinuousExposures=0"`.  ⛔ 슬롯 번호만 보고 쓰면 그
    파라미터를 덮는다.  켜라고 했으면 **경고하고 flush 없이** 간다 (기동은 세우지 않는다);
    끄라는 것은 조용히 `False`."""
    text = open(SCI_ACF, encoding='ascii').read()
    assert text.count('PARAMETER0="FirstFlush=0"\n') == 1
    old = tmp_path / 'sci_r2608.acf'
    old.write_text(text.replace('PARAMETER0="FirstFlush=0"\n',
                                'PARAMETER0="ContinuousExposures=0"\n'), encoding='ascii')
    ctrl = Ctrl(str(old))
    with caplog.at_level('WARNING'):
        assert asyncio.run(ctrl.set_flush_param('FirstFlush', 1)) is False
    assert ctrl.writes() == [] and ctrl.loads() == [], ctrl.sent
    assert any('continuing without flush' in r.getMessage()
               for r in caplog.records), caplog.text
    caplog.clear()
    with caplog.at_level('WARNING'):
        assert asyncio.run(ctrl.set_flush_param('FirstFlush', 0)) is False
    assert not [r for r in caplog.records if r.levelname == 'WARNING'], caplog.text


def test_guide_has_no_option_so_its_constant_is_never_touched():
    """guide 의 `FirstFlush` 는 **ACF 상수**다.  `IcgCfg` 에 이 설정이 없어
    `apply_flush_overrides()` 가 `getattr` 에서 `None` 을 받아 그냥 지나간다."""
    for attr in ('ccdflush_first', 'ccdflush_every'):
        assert getattr(IcgCfg(), attr, None) is None, attr
    ctrl = Ctrl(GUIDE_ACF)
    assert ctrl.flag() == 'FirstFlush=1'


# -- ini ---------------------------------------------------------------------


def test_the_ini_default_is_follow_the_acf():
    """⭐ **기본은 `None`** -- *"ACF 값을 그대로 따른다"* 는 뜻이다 (운영자 2026-09-14).

    ⛔ 종전 `ccdflush: bool = False` 를 대신한다.  `False` 는 *"0 을 써 넣는다"* 로
    읽힐 여지가 있었는데, `None` 은 **아무것도 안 쓴다**가 분명하다.
    ⭐ 그래서 10장 실측(독출 12.77 s)과 `MIN_FRAME_PERIOD` 는 **기본 구성의 값이
    맞다** -- 켤 때만 `SkipLine(FlushLines)` 만큼 길어진다.
    """
    assert ArchonCfg().ccdflush_first is None
    assert ArchonCfg().ccdflush_every is None


def _ini_with(tmp_path, **kv):  # noqa: ANN001, ANN003
    import configparser

    cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    cp.read(os.path.join(ROOT, 'ics_archon.ini'), encoding='utf-8')
    for k, v in kv.items():
        cp['archon'][k] = v
    path = tmp_path / 'ics.ini'
    with open(path, 'w', encoding='utf-8') as fh:
        cp.write(fh)
    return str(path)


@pytest.mark.parametrize('key', ['ccdflush_first', 'ccdflush_every'])
def test_an_empty_value_means_follow_the_acf(tmp_path, key):  # noqa: ANN001
    """⭐ **비워 두면 ACF 를 따른다** -- 배포 ini 가 그 꼴이다."""
    from ics_archon import config as acfg_mod

    assert getattr(acfg_mod.load(_ini_with(tmp_path, **{key: ''})), key) is None


@pytest.mark.parametrize('key', ['ccdflush_first', 'ccdflush_every'])
@pytest.mark.parametrize('word, want', [('0', 0), ('1', 1), ('3', 3)])
def test_a_number_overrides_the_acf(tmp_path, key, word, want):  # noqa: ANN001
    """⭐ 값이 있으면 그 수를 ACF 슬롯에 써 넣는다.

    ⛔ `0` 과 *"비어 있음"* 은 **다르다** -- `0` 은 *"ACF 가 뭐라 하든 끈다"* 이고
    비어 있음은 *"ACF 를 따른다"* 다.
    """
    from ics_archon import config as acfg_mod

    assert getattr(acfg_mod.load(_ini_with(tmp_path, **{key: word})),
                   key) == want


@pytest.mark.parametrize('key', ['ccdflush_first', 'ccdflush_every'])
def test_a_non_number_is_refused(tmp_path, key):  # noqa: ANN001
    """⛔ **모르는 값은 모른다고 말한다** -- 조용히 꺼지지 않는다.

    종전에는 `true`/`false` 낱말을 받았다.  ⚠️ **옛 ini 의 `ccdflush = true` 를
    새 키에 그대로 옮겨 적으면 여기서 걸린다** -- 새 설계에서 그것은
    `ccdflush_every = 1` 이다.
    """
    from ics_archon import config as acfg_mod

    with pytest.raises(acfg_mod.ArchonConfigError) as exc:
        acfg_mod.load(_ini_with(tmp_path, **{key: 'true'}))
    assert key in str(exc.value)


def test_the_shipped_ini_leaves_both_empty():
    """⭐ 배포 ini 는 둘 다 비워 둔다 -- ACF(둘 다 0)를 따른다."""
    from ics_archon import config as acfg_mod

    acfg = acfg_mod.load(os.path.join(ROOT, 'ics_archon.ini'))
    assert acfg.ccdflush_first is None
    assert acfg.ccdflush_every is None


def test_the_old_boolean_key_is_gone():
    """⛔ `ccdflush` 는 **없앴다** (2026-09-14).  남아 있으면 두 기제가 공존한다."""
    assert not hasattr(ArchonCfg(), 'ccdflush')
    ini = io.open(os.path.join(ROOT, 'ics_archon.ini'),
                  encoding='utf-8').read()
    for line in ini.splitlines():
        head = line.split('=')[0].strip()
        assert head != 'ccdflush', '배포 ini 에 옛 키가 남아 있다: %r' % line


# -- ARCHON 바이패스가 캐시를 갈라놓는다 (2026-09-08, 운영자) ----------------
#
# ⛔ **캐시와 컨트롤러가 갈릴 수 있는 유일한 경로**다.  바이패스는 `set_config` 를
# 안 지나므로 설정 메모리만 바뀌고 `ctrl.config` 는 옛 값을 든다.  그 뒤
# `set_first_flush`/`flush_now` 가 캐시를 믿고 *"그 슬롯에 FirstFlush 가 있다"* 로
# 판단하면 **엉뚱한 슬롯을 덮는다**.


class _Ctrl:
    """`ArchonController` 의 설정 층만 흉내낸다 -- 왕복은 세기만."""

    def __init__(self, cached, on_wire):  # noqa: ANN001
        from ics_archon.archon.controller import ArchonController
        self.config = dict(cached)
        #: 줄 번호 -- 캐시 순서대로 (바이패스 `WCONFIGnnnn` 이 어느 줄인지 가를 때 쓴다).
        self.configline = {k: i for i, k in enumerate(self.config)}
        self.config_dirty = False
        #: 못 되돌린 임시 줄 -- 바이패스가 설정 메모리를 쓰면 비운다 (`raw_command`).
        self._pending_restore = {}
        self._wire = dict(on_wire)
        self.reads = []
        self.tag = 'G'
        self.raw_command = ArchonController.raw_command.__get__(self)
        self.config_value = ArchonController.config_value.__get__(self)

    async def cmd(self, text, timeout=None):  # noqa: ANN001, ANN202
        return b'OK'

    async def read_config(self, key):  # noqa: ANN001, ANN202
        self.reads.append(key)
        return self._wire[key]


def test_a_bypass_wconfig_marks_the_cache_untrustworthy():
    """⭐ 값을 흉내내 고치지 않고 **못 믿는다고 표시만** 한다.

    원문을 우리가 파싱하면 그 파싱이 또 하나의 진실이 된다 -- 다음 판단이
    `RCONFIG` 로 되읽게 두는 편이 낫다.
    """
    c = _Ctrl({'PARAMETER0': '"FirstFlush=1"'}, {'PARAMETER0': '"Other=9"'})
    assert not c.config_dirty
    asyncio.run(c.raw_command('WCONFIG0000PARAMETER0="Other=9"'))
    assert c.config_dirty, '설정을 건드렸는데 표시가 안 섰다'

    # 되읽기로 실제 값이 온다 -- 캐시가 아니라.
    got = asyncio.run(c.config_value('PARAMETER0'))
    assert got == '"Other=9"', got
    assert c.reads == ['PARAMETER0'], c.reads


def test_a_harmless_bypass_does_not_mark_the_cache():
    """⛔ `STATUS` 같은 조회까지 표시하면 **매번 되읽어** 쿼터·시간을 버린다."""
    c = _Ctrl({'PARAMETER0': '"FirstFlush=1"'}, {})
    asyncio.run(c.raw_command('STATUS'))
    asyncio.run(c.raw_command('APPLYALL'))
    assert not c.config_dirty, '설정을 안 건드렸는데 표시가 섰다'
    assert asyncio.run(c.config_value('PARAMETER0')) == '"FirstFlush=1"'
    assert c.reads == [], '평시에 되읽으면 안 된다'


def test_a_failed_read_back_falls_back_to_the_cache():
    """⚠️ 되읽기 실패로 **죽지는 않는다** -- 여기서 죽으면 바이패스 한 번이
    다음 `ccdflush` 를 통째로 막는다.  캐시로 물러나되 표시는 남긴다."""
    c = _Ctrl({'PARAMETER0': '"FirstFlush=1"'}, {})   # _wire 가 비어 KeyError
    asyncio.run(c.raw_command('CLEARCONFIG'))
    assert asyncio.run(c.config_value('PARAMETER0')) == '"FirstFlush=1"'
    assert c.config_dirty, '실패했다고 표시를 내리면 안 된다'


def test_a_bypass_config_write_hands_the_pending_put_back_to_the_operator(caplog):  # noqa: ANN001
    """⭐ 바이패스가 설정 메모리를 쓰면 **못 되돌린 임시 줄을 비운다** (DevNote 11.96) --
    그 뒤로 메모리는 운영자 몫이라, 다음 LOADPARAMS 앞의 되쓰기(`_retry_pending_restore`)가
    운영자가 쓴 값을 덮으면 안 된다.  조회(`STATUS`)는 표시를 건드리지 않는다."""
    c = _Ctrl({'PARAMETER0': 'FirstFlush=0'}, {})
    c._pending_restore['PARAMETER0'] = 'FirstFlush=0'          # noqa: SLF001
    asyncio.run(c.raw_command('STATUS'))
    assert c._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001
    with caplog.at_level('WARNING'):
        asyncio.run(c.raw_command('WCONFIG0000PARAMETER0=FirstFlush=2'))
    assert c._pending_restore == {}                             # noqa: SLF001
    assert any('dropping the pending put-back' in r.getMessage()
               for r in caplog.records), caplog.text


@pytest.mark.parametrize('bypass, left', [
    ('WCONFIG0001PARAMETER1=IntMS=5', {'PARAMETER0': 'FirstFlush=0'}),   # 그 줄만
    ('CLEARCONFIG', {}),                                                 # 전부
    ('WCONFIGZZZZPARAMETER1=IntMS=5', {}),         # 줄 번호를 못 읽었다 -- 전부로 본다
])
def test_a_bypass_hands_over_only_the_lines_it_touched(bypass, left):  # noqa: ANN001
    """⭐ `WCONFIG` 는 **그 줄의** 표시만 비우고, `CLEARCONFIG` 는 전부 비운다 -- 다른 줄의 못
    되돌린 값(`FirstFlush=1`)까지 비우면 science 가 세션 내내 매 장 flush 를 돈다."""
    c = _Ctrl({'PARAMETER0': 'FirstFlush=0', 'PARAMETER1': 'IntMS=0'}, {})
    c._pending_restore.update({'PARAMETER0': 'FirstFlush=0',     # noqa: SLF001
                               'PARAMETER1': 'IntMS=0'})
    asyncio.run(c.raw_command(bypass))
    assert c._pending_restore == left                           # noqa: SLF001


def test_a_refused_bypass_write_keeps_the_pending_put_back():
    """⚠️ 거부(`?NN`)된 바이패스는 메모리를 안 바꿨다 -- 표시를 남긴다."""
    class _Refusing(_Ctrl):
        async def cmd(self, text, timeout=None):  # noqa: ANN001, ANN202
            raise ArchonError('시험이 일부러 거부한 명령 -- %s' % text, cmd=text,
                              reply_error=True)

    c = _Refusing({'PARAMETER0': 'FirstFlush=0'}, {})
    c._pending_restore['PARAMETER0'] = 'FirstFlush=0'          # noqa: SLF001
    with pytest.raises(ArchonError):
        asyncio.run(c.raw_command('WCONFIG0000PARAMETER0=FirstFlush=2'))
    assert c._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001


# -- `flush_now()` 는 오류·취소에도 `FirstFlush` 를 되돌린다 (DevNote 11.96) ------
#
# ⛔ 종전에는 되돌림이 `finally` 밖이라 `Exposures=0`·`LOADPARAMS`·`RESETTIMING` 가운데
# 하나만 깨져도 설정 메모리에 `FirstFlush=1` 이 남았다.  캐시도 `set_config` 가 먼저 1 로
# 바꿔 둬서 다음 `flush_now` 는 *"이미 켜져 있다"* 로 보고 되돌리지 않았고, science 는 그
# 세션 내내 **매 장** flush 를 돌았다(+5.5 s).


def _flag_writes(ctrl: Ctrl) -> list[str]:
    return [c for c in ctrl.writes() if 'PARAMETER0=' in c]


@pytest.mark.parametrize('fail_on, reset, land', [
    ('=Exposures=', False, False),
    ('=Exposures=', False, True),
    ('LOADPARAMS', False, False),
    ('RESETTIMING', True, False),
    ('FirstFlush=1', False, False),          # 올림 쓰기 자체가 깨졌다 (앉지 않았다)
    ('FirstFlush=1', False, True),           # 앉았는데 답을 잃었다 (시한 초과 꼴)
])
def test_flush_now_puts_the_flag_back_when_a_step_fails(fail_on, reset, land):  # noqa: ANN001
    """⭐ 어느 걸음이 깨져도 **메모리와 캐시가 둘 다** 원래 값(0)으로 끝나고, 원래 예외가
    그대로 올라온다."""
    ctrl = Ctrl(fail_on=fail_on, land=land)
    with pytest.raises(ArchonError) as exc:
        asyncio.run(ctrl.flush_now(reset=reset))
    assert fail_on.strip('=') in str(exc.value), '원래 예외가 가려졌다: %s' % exc.value
    assert ctrl.flag() == 'FirstFlush=0', ctrl.sent
    assert ctrl.config['PARAMETER0'] == 'FirstFlush=0'
    assert _flag_writes(ctrl)[-1] == _slot_write(ctrl, 'FirstFlush=0'), ctrl.sent
    assert ctrl._pending_restore == {}           # noqa: SLF001  되돌림은 성공했다


def test_flush_now_restores_a_count_above_one_on_failure():
    """⛔ 되돌리는 값은 0 고정이 아니라 **읽어 둔 값**이다 -- `ccdflush_first=2` 면 2."""
    ctrl = Ctrl()
    asyncio.run(ctrl.set_flush_param('FirstFlush', 2))
    ctrl.fail_on, ctrl.fail_times = ('LOADPARAMS',), 1
    with pytest.raises(ArchonError):
        asyncio.run(ctrl.flush_now())
    assert ctrl.flag() == 'FirstFlush=2', ctrl.sent
    assert ctrl.config['PARAMETER0'] == 'FirstFlush=2'


def test_a_failed_put_back_after_the_flush_is_retried_next_time(caplog):  # noqa: ANN001
    """되돌림 **만** 실패 -- flush 는 돌았으니 명령은 성공으로 끝나고, 오류 한 줄 +
    `config_dirty` + `_pending_restore` 가 남는다.  다음 `flush_now` 가 **판정 전에**
    먼저 되쓴다 -- 안 그러면 되읽은 1 을 *"이미 켜져 있다"* 로 보고 영구히 남긴다."""
    ctrl = Ctrl(fail_on='FirstFlush=0')
    with caplog.at_level('ERROR'):
        asyncio.run(ctrl.flush_now())
    errs = [r for r in caplog.records if 'could not be put back' in r.getMessage()]
    assert errs, caplog.text
    # ⭐ 오류 줄의 사정은 **부르는 쪽이 준다** -- 노출 이야기가 아니라 flush 가 걸렸다는 것.
    assert '일회성 flush 는 걸렸다' in errs[0].detail, errs[0].detail
    assert '노출' not in errs[0].detail, errs[0].detail
    assert ctrl.flag() == 'FirstFlush=1', '가짜가 되돌림을 거절했으니 메모리는 1 이다'
    assert ctrl.config_dirty is True
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001

    ctrl.sent.clear()
    asyncio.run(ctrl.flush_now())
    assert ctrl.sent[0] == _slot_write(ctrl, 'FirstFlush=0'), '판정보다 먼저 되써야 한다'
    assert ctrl.loads() == ['LOADPARAMS'], ctrl.sent
    assert ctrl.flag() == 'FirstFlush=0', ctrl.sent
    assert ctrl._pending_restore == {}           # noqa: SLF001


@pytest.mark.parametrize('step, context', [
    ('LOADPARAMS', '일회성 flush 가 걸렸는지 모른다'),    # 나갔는데 깨졌다
    ('=Exposures=', '일회성 flush 는 걸지 않았다'),       # LOADPARAMS 전에 깨졌다
])
def test_the_put_back_error_line_says_how_far_the_flush_got(caplog, step, context):  # noqa: ANN001
    """그 걸음도 깨지고 되돌림도 깨진다 -- 올라오는 것은 그 걸음의 예외이고, 오류 줄의 사정은
    **flush 가 어디까지 갔나**다 (DevNote 11.96)."""
    ctrl = Ctrl(fail_on=(step, 'FirstFlush=0'), fail_times=2)
    with caplog.at_level('ERROR'):
        with pytest.raises(ArchonError) as got:
            asyncio.run(ctrl.flush_now())
    assert step.strip('=') in str(got.value), got.value
    errs = [r for r in caplog.records if 'could not be put back' in r.getMessage()]
    assert errs and context in errs[0].detail, [r.__dict__.get('detail') for r in errs]
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001


@pytest.mark.parametrize('retry_fails', [True, False])
def test_the_abort_flush_resets_timing_before_the_retry(caplog, retry_fails):  # noqa: ANN001
    """⭐ `flush_now(reset=True)`(guide ABORT/EXPENABLE=0)는 **멈춤이 먼저다** -- 앞서 못
    되돌린 줄은 `RESETTIMING` **뒤에** `strict=False` 로 되쓴다(`abort_now` 와 같다).
    ⛔ 종전에는 판정 전에 엄격히 되써서, 그 되쓰기가 깨지면 `RESETTIMING` 이 아예 안 나갔다.
    깨지면 경고만 하고 표시는 남는다(다음 GO·CCDFLUSH 가 엄격히 쓴다)."""
    ctrl = Ctrl(fail_on='FirstFlush=0', fail_times=5 if retry_fails else 0)
    ctrl._memory['PARAMETER0'] = 'FirstFlush=1'                   # noqa: SLF001  남은 1
    ctrl._pending_restore['PARAMETER0'] = 'FirstFlush=0'          # noqa: SLF001
    ctrl.config_dirty = True
    with caplog.at_level('WARNING'):
        asyncio.run(ctrl.flush_now(reset=True))                   # 올라오지 않는다
    assert 'RESETTIMING' in ctrl.sent, ctrl.sent
    retry = ctrl.sent.index(_slot_write(ctrl, 'FirstFlush=0'))
    assert ctrl.sent.index('RESETTIMING') < retry, ctrl.sent
    if retry_fails:
        assert ctrl.flag() == 'FirstFlush=1'
        assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001
        assert any('the stop went out anyway' in r.getMessage()
                   for r in caplog.records), caplog.text
    else:
        assert ctrl.flag() == 'FirstFlush=0', ctrl.sent
        assert ctrl._pending_restore == {}                          # noqa: SLF001


@pytest.mark.parametrize('reread_fails, says', [
    (False, 'RCONFIG 로 되읽어도 원래 값이 아니다'),
    (True, '원래 값임을 확인하지 못했다'),
])
def test_a_strict_retry_failure_says_what_the_read_back_found(caplog, reread_fails,  # noqa: ANN001
                                                              says):
    """⭐ 되읽기의 답은 셋이다 (`_memory_holds`) -- **되읽기마저 깨졌으면** 오류 줄의 사정이
    *"원래 값이 아니다"* 라고 하면 안 된다.  어느 쪽이든 LOADPARAMS 는 안 나간다."""
    ctrl = Ctrl(fail_on=('FirstFlush=0', 'RCONFIG') if reread_fails else 'FirstFlush=0',
                fail_times=2 if reread_fails else 1)
    ctrl._memory['PARAMETER0'] = 'FirstFlush=1'                   # noqa: SLF001
    ctrl._pending_restore['PARAMETER0'] = 'FirstFlush=0'          # noqa: SLF001
    with caplog.at_level('ERROR'):
        with pytest.raises(ArchonError):
            asyncio.run(ctrl.flush_now())
    errs = [r for r in caplog.records if 'still cannot be put back' in r.getMessage()]
    assert errs and says in errs[0].detail, [r.__dict__.get('detail') for r in errs]
    assert ctrl.loads() == [], ctrl.sent
    assert ctrl._pending_restore == {'PARAMETER0': 'FirstFlush=0'}   # noqa: SLF001


def test_the_flush_now_put_back_is_in_a_finally():
    """소스 수준 확인 -- 되돌림이 `finally` 안에 있다 (ACF 적용의 `POLLON` 과 같은 규범)."""
    import inspect
    src = inspect.getsource(ArchonController.flush_now)
    assert src.index('finally:') < src.index('self._put_back(fslot, cur'), src


# -- 노출 파라미터 슬롯을 **이름으로** 찾는다 (운영자 2026-09-12) -----------
#
# ⛔⛔ **이름 고정은 KMTNet 의 ACF 규약이다** -- Archon 의 제약이 아니다.
# 컨트롤러는 파라미터 이름에 아무 규칙도 걸지 않는다(아무 이름이나 쓸 수 있다).
# **우리가** ACF 를 개정해도 `IntMS`·`Exposures`·`FirstFlush` 세 이름은 바꾸지
# 않기로 정했고, 그 대가로 **슬롯 번호를 설정에서 뺐다**.

def _ctrl_with_acf(tmp_path, text):  # noqa: ANN001, ANN202
    """ACF 만 읽은 컨트롤러 (왕복 없음)."""
    from ics_archon.archon.controller import ArchonController
    acf = tmp_path / 'p.acf'
    acf.write_text(text, encoding='ascii')
    c = ArchonController.__new__(ArchonController)
    c.tag, c.ltag = 'MK', ''
    c.parse_acf(str(acf))
    return c


def test_slots_are_found_by_name_not_by_number(tmp_path):
    """⭐ 번호가 밀려도 **이름으로** 찾는다 -- ACF 개정을 따라간다."""
    c = _ctrl_with_acf(tmp_path, '[CONFIG]\n'
                       'PARAMETER0="FirstFlush=0"\n'
                       'PARAMETER1="IntMS=0"\n'
                       'PARAMETER2="Exposures=0"\n')
    # ⭐ 고정물이 놓은 그대로 찾는다 -- **정본 번호란 것이 없다.**
    assert c.param_slots['IntMS'] == 'PARAMETER1'
    assert c.param_slots['Exposures'] == 'PARAMETER2'

    # 판이 밀려 번호가 통째로 달라져도 따라간다.
    d = _ctrl_with_acf(tmp_path, '[CONFIG]\n'
                       'PARAMETER0="FirstFlush=0"\n'
                       'PARAMETER3="IntMS=0"\n'
                       'PARAMETER7="Exposures=0"\n')
    assert d.param_slots['IntMS'] == 'PARAMETER3'
    assert d.param_slots['Exposures'] == 'PARAMETER7'


def test_a_missing_exposure_parameter_stops_the_start(tmp_path):
    """⛔ `IntMS`/`Exposures` 가 없으면 **노출 준비가 멈춘다**.

    그 ACF 로는 노출을 걸 수가 없다 -- 그대로 두면 첫 `GO` 의 `WCONFIG` 가
    엉뚱한 슬롯을 덮는다.
    ⚠️ **멈추는 자리는 `parse_acf()` 가 아니다** -- 감시(바이어스 채널 찾기)와
    `probe_archon`(진단)도 같은 길로 ACF 를 읽으므로, 파싱은 통과시키고
    `_require_param_slots()`(= `prepare()` 가 부른다)에서 판정한다.
    """
    from ics_archon.archon.protocol import ArchonError
    c = _ctrl_with_acf(tmp_path, '[CONFIG]\nPARAMETER1="Exposures=0"\n')
    assert 'Exposures' in c.param_slots, '파싱 자체는 통과한다'
    with pytest.raises(ArchonError) as e:
        c._require_param_slots()      # noqa: SLF001
    assert 'IntMS' in str(e.value)
    # ⭐ 규약이 어디 것인지 문면이 말해야 한다 -- 벤더 제약으로 오해하면
    #    엉뚱한 자리(Archon 매뉴얼)를 뒤진다.
    assert 'KMTNet' in str(e.value)


def test_firstflush_may_be_absent(tmp_path):
    """⭐ `FirstFlush` 는 **없어도 간다** -- R2608 이하 ACF 가 그렇다.

    *"flush 옵션 하나 때문에 관측을 통째로 못 하는 것이 더 나쁘다"* 는
    `set_first_flush()` 의 판단을 그대로 따른다.
    """
    c = _ctrl_with_acf(tmp_path, '[CONFIG]\n'
                       'PARAMETER1="IntMS=0"\nPARAMETER2="Exposures=0"\n')
    assert 'FirstFlush' not in c.param_slots


def test_exposures_must_be_the_last_slot(tmp_path):
    """⛔ `Exposures` 가 **맨 마지막 슬롯**이 아니면 멈춘다 (매뉴얼 p.52).

    `LOADPARAMS` 는 파라미터를 **하나씩 제자리에 덮어쓰고**(*"one at a time,
    starting with the first in the parameter list"*) 그동안 **코어를 세우지
    않는다**(*"does not reset the timing cores"*).  그래서 `Exposures` 가 먼저
    앉으면 코어가 `Start:` 에서 `FirstFlush` 를 묵은 0 으로 읽고 **flush 없이**
    `Exposure:` 로 뛴다 (DevNote 11.31).
    ⭐ 벤더가 이 성질을 안다는 증거가 바로 옆에 있다 -- `PREPPARAM`/`EXTLOAD` 가
    *"미리 채워 두었다가 신호에 한꺼번에 갈아끼우는"* 장치이고, 평범한
    `LOADPARAMS` 에는 그것이 없다.

    ⭐ **`FirstFlush` 만의 이야기가 아니다** -- `Exposures` 가 0 이 아니게 되는
    순간 코어는 `Exposure:` 로 뛰고 거기서 **거의 모든 파라미터를 읽는다**
    (`IntMS`·`NoIntMS`·`Lines`·`Pixels`·`AT`·`ST` …).  그래서 규칙은 *"셋만 앞에"*
    가 아니라 **방아쇠가 맨 뒤** 하나다 (운영자 2026-09-13).

    ⚠️ **2026-09-13: 이 시험을 한 번 뒤집었다가 되돌렸다.**  뒤집은 근거는
    *"`Exposures`(줄 2번째)와 `IntMS`(13번째) 사이가 ~100 ms 인데 노출시간이 안
    밀리니 원자적이다"* 였는데, 그 ~100 ms 가 **검증 안 한 가정**(*"list 순서 =
    파일 줄 순서"*) 위에 서 있었다.  `PARAMETERn` 의 n 이 곧 첨자면 한 칸
    차이다.  ⛔ **없는 증상은 반증이 아니다** -- 창이 작으면 안 보일 뿐이다.
    """
    from ics_archon.archon.protocol import ArchonError
    c = _ctrl_with_acf(tmp_path, '[CONFIG]\n'
                       'PARAMETER1="IntMS=0"\n'
                       'PARAMETER2="Exposures=0"\n'
                       'PARAMETER5="FirstFlush=0"\n')
    with pytest.raises(ArchonError) as e:
        c._require_param_slots()      # noqa: SLF001
    assert 'FirstFlush' in str(e.value)


def test_the_order_check_reads_slot_numbers_not_file_order(tmp_path):
    """⭐ 순서는 **슬롯 번호**로 본다 -- ACF 파일의 줄 순서가 아니다.

    ACF 는 `PARAMETER0,1,10,…,19,2,…` **사전순**으로 적히므로 파일 줄 순서와 슬롯
    번호 순서가 다르다.  ⛔ 우리는 매뉴얼의 *"the **first** in the parameter
    list"* 를 **번호 순**으로 읽는다 (`PARAMETERn` + `PARAMETERS=n` 은 첨자 붙은
    배열의 모양이다).
    ⚠️ 종전에 **두 순서를 다** 보게 짰다가 걷었다 -- 파라미터가 열 개를 넘으면
    두 순서에서 동시에 "맨 마지막" 인 슬롯이 **존재하지 않아** 올바른 배치가
    불가능해진다 (운영자 확정 2026-09-13).
    """
    # 줄 차례로는 `Exposures` 가 맨 뒤인데 **번호로는 앞**이다 -> 멈춰야 한다.
    from ics_archon.archon.protocol import ArchonError
    c = _ctrl_with_acf(tmp_path, '[CONFIG]\n'
                       'PARAMETER0="FirstFlush=0"\n'
                       'PARAMETER2="IntMS=0"\n'
                       'PARAMETER9="Exposures=0"\n'
                       'PARAMETER10="NoIntMS=0"\n')
    with pytest.raises(ArchonError) as e:
        c._require_param_slots()      # noqa: SLF001
    assert 'NoIntMS' in str(e.value), str(e.value)


def test_every_parameter_must_precede_exposures(tmp_path):
    """⭐ **아무 파라미터나** `Exposures` 뒤에 있으면 멈춘다.

    `Exposure:` 분기가 읽는 것이 거의 전부라, 이름을 하나하나 세는 대신 *"방아쇠가
    맨 뒤"* 하나로 규정했다.
    """
    from ics_archon.archon.protocol import ArchonError
    ok = _ctrl_with_acf(tmp_path, '[CONFIG]\n'
                        'PARAMETER0="FirstFlush=0"\n'
                        'PARAMETER1="ContinuousExposures=0"\n'
                        'PARAMETER2="IntMS=0"\n'
                        'PARAMETER3="NoIntMS=0"\n'
                        'PARAMETER4="Exposures=0"\n')
    ok._require_param_slots()        # 멈추지 않는다  # noqa: SLF001

    bad = _ctrl_with_acf(tmp_path, '[CONFIG]\n'
                         'PARAMETER0="FirstFlush=0"\n'
                         'PARAMETER1="IntMS=0"\n'
                         'PARAMETER2="Exposures=0"\n'
                         'PARAMETER3="Lines=4700"\n')
    with pytest.raises(ArchonError) as e:
        bad._require_param_slots()   # noqa: SLF001
    assert 'Lines' in str(e.value), str(e.value)


@pytest.mark.repo_only
def test_every_shipped_acf_keeps_the_kmtnet_names(tmp_path):
    """⭐⭐ **저장소의 ACF 열둘이 규약을 지키나** -- 규범의 실물 검산이다.

    ⛔ **슬롯 번호는 보지 않는다** -- 규약이 고정하는 것은 *이름*이다.  번호를
    여기서 요구하면 ACF 를 개정해 번호가 밀렸을 때 **멀쩡한 ACF 가 시험을
    깨뜨리고**, 읽는 이는 *"번호를 도로 맞춰야 한다"* 로 읽는다 -- 우리가
    없애려던 바로 그 습관이다 (운영자 지적 2026-09-13).
⭐ 슬롯 **순서**는 본다 -- 다만 *"몇 번이냐"* 가 아니라 *"`Exposures` 가
    맨 마지막이냐"* 만 본다 (매뉴얼 p.52, 위 시험 참조).
    ⚠️ science 와 guide 의 번호가 지금 같은 것은 **우연이고 규약이 아니다** --
    두 계통은 타이밍 스크립트도 파라미터 구성도 다르다 (guide 17 · science 22,
    `VerticalBinning`·`AT`·`ST`·`FlushLines`·`ContinuousExposures` 는 이름이
    같은데 슬롯이 다르다).
    """
    import glob
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    acfs = sorted(glob.glob(os.path.join(root, 'acf', '*.acf')))
    assert len(acfs) >= 7, acfs
    from ics_archon.archon.controller import ArchonController
    for path in acfs:
        c = ArchonController.__new__(ArchonController)
        c.tag, c.ltag = 'MK', ''
        c.parse_acf(path)
        c._require_param_slots()     # 규약을 어기면 여기서 ArchonError  # noqa: SLF001
        # 이름이 있다 -- 번호가 몇이든.
        assert c.param_slots['IntMS'].startswith('PARAMETER'), path
        assert c.param_slots['Exposures'].startswith('PARAMETER'), path
        assert 'FirstFlush' in c.param_slots, path
        # ⛔ 유일한 순서 제약 -- `Exposures` 가 **맨 마지막 슬롯**이다.
        assert (c.param_order['Exposures']
                == max(c.param_order.values())), path


# -- 셔터 닫힘 대기 (`NoIntMS` 의 하한) ---------------------------------------
#
# 운영자 규정 2026-09-13: 셔터를 여는 IMAGETYPE 에서 `EXPTIME` 은 *"셔터가 열리기
# 시작 ~ 셔터가 닫히기 시작"* 이고, **그 뒤 셔터가 다 닫힐 때까지** 기다렸다가
# 독출을 시작해야 한다.  그 대기를 만드는 것이 `NOINT; CALL NoIntUnit(NoIntMS)` 다.
# ⛔ 짧으면 셔터가 닫히는 중에 독출이 시작돼 **프레임에 빛이 샌다** -- 조용하게.


def _noint(ctrl) -> int:  # noqa: ANN001
    slot = ctrl.param_slots['NoIntMS']
    return int(ctrl.config[slot].split('=', 1)[1])


def test_a_short_noint_is_raised_to_the_shutter_close_time():
    """⛔ ACF 의 `NoIntMS` 가 짧으면 **올려서 적용한다** (경고와 함께)."""
    ctrl = Ctrl()
    slot = ctrl.param_slots['NoIntMS']
    ctrl.config[slot] = 'NoIntMS=120'
    ctrl._memory[slot] = 'NoIntMS=120'       # noqa: SLF001
    ctrl.cfg.shutter_close_ms = 500

    asyncio.run(ctrl._enforce_shutter_close_dwell())   # noqa: SLF001

    assert _noint(ctrl) == 500, '하한으로 올라와야 한다'
    # ⭐ **`WCONFIG` 한 줄**이다 -- `LOADTIMING` 도 `LOADPARAMS` 도 없다.
    #    코어 RAM 에는 다음 노출의 LOADPARAMS 가 실어 간다.
    assert len(ctrl.writes()) == 1, ctrl.sent
    assert 'NoIntMS=500' in ctrl.writes()[0], ctrl.writes()
    assert ctrl.loads() == [], ctrl.sent


def test_a_long_enough_noint_is_left_alone():
    """⭐ ACF 가 이미 충분하면 **아무것도 안 쓴다** -- 정본은 ACF 다."""
    ctrl = Ctrl()
    ctrl.cfg.shutter_close_ms = 500
    assert _noint(ctrl) == 500, '현행 science ACF 는 500 이다'
    asyncio.run(ctrl._enforce_shutter_close_dwell())   # noqa: SLF001
    assert ctrl.writes() == [], ctrl.sent


def test_zero_turns_the_check_off():
    """⭐ `0` 이면 검사하지 않는다 -- 셔터가 없는 구성용."""
    ctrl = Ctrl()
    slot = ctrl.param_slots['NoIntMS']
    ctrl.config[slot] = 'NoIntMS=0'
    ctrl.cfg.shutter_close_ms = 0
    asyncio.run(ctrl._enforce_shutter_close_dwell())   # noqa: SLF001
    assert ctrl.writes() == [], ctrl.sent


def test_the_guide_unit_never_reaches_this_check():
    """⭐ **guide 에는 이 눈금이 없다** -- `IcgCfg` 에 `shutter_close_ms` 가 없다 (셔터가 없다).

    `ccdflush` 와 같은 방식이다: `getattr(..., 0)` 이 0 을 돌려 검사도 바닥값도 없이
    지나간다(ACF 값을 `shutter_dwell_ms` 에 적어 둘 뿐 -- guide 백엔드는 안 읽는다).
    ⚠️ guide ACF 는 `NoIntMS=0` 이라, 강제가 걸리면 **없는 대기를 만들어** guide
    프레임 주기를 망가뜨린다.
    """
    ctrl = Ctrl(GUIDE_ACF)
    ctrl.cfg = IcgCfg()                      # guide 설정으로 갈아 끼운다
    ctrl.cfg.acf = {'MK': GUIDE_ACF}
    assert not hasattr(ctrl.cfg, 'shutter_close_ms')
    asyncio.run(ctrl._enforce_shutter_close_dwell())   # noqa: SLF001
    assert ctrl.writes() == [], ctrl.sent
    assert _noint(ctrl) == 0, 'guide 는 NoIntMS=0 그대로여야 한다'


# -- 셔터 노출이 노출마다 싣는 값 (`shutter_dwell_ms`, DevNote 11.96) --------------
#
# ⛔ 종전에는 셔터 노출이 `shutter_close_ms` 를 그대로 싣고 `0` 이면 **안 실었다**.
# 그러면 *"0 이면 ACF 값이 정본"* 이 아니라 앞 DARK/BIAS 가 쓴 값이 갔고(BIAS 뒤면 0),
# ACF 가 `shutter_close_ms` 보다 길면 하한이어야 할 눈금이 ACF 값을 **깎았다**.


@pytest.mark.parametrize('acf, close_ms, want, writes', [
    (None, 0, 500, 0),        # 검사를 꺼 뒀다 -- ACF 값 그대로
    (None, 200, 500, 0),      # ACF 가 더 길다 -- 깎지 않는다 (하한이다)
    (None, 500, 500, 0),
    (None, 5200, 5200, 1),    # ACF 가 짧다 -- 올리고 한 줄 쓴다
    # ⭐ ACF 값을 못 읽는다(`이름=값` 꼴이 아니다) -- 슬롯은 안 건드리되 **바닥값은
    #    노출마다 나간다** (DevNote 11.96).  종전에는 `None` 으로 끝나 바닥값이 빠졌다.
    ('NoIntMS=?', 5200, 5200, 0),
    ('NoIntMS=?', 0, None, 0),    # 바닥값도 꺼 뒀다 -- 셀 기준이 없다
])
def test_the_shutter_dwell_is_the_longer_of_the_acf_and_the_floor(acf, close_ms,  # noqa: ANN001
                                                                   want, writes):
    ctrl = Ctrl()
    assert _noint(ctrl) == 500, '현행 science ACF 는 500 이다'
    if acf is not None:
        ctrl.config[ctrl.param_slots['NoIntMS']] = acf
    ctrl.cfg.shutter_close_ms = close_ms
    asyncio.run(ctrl._enforce_shutter_close_dwell())   # noqa: SLF001
    assert ctrl.shutter_dwell_ms == want
    assert len(ctrl.writes()) == writes, ctrl.sent


def test_an_acf_without_noint_leaves_the_shutter_dwell_unset(tmp_path):  # noqa: ANN001
    """슬롯이 없으면 `None` -- 셔터 노출은 `NoIntMS` 를 안 싣는다 (기동 검사가 이미 경고)."""
    acf = tmp_path / 'old.acf'
    acf.write_text('[CONFIG]\nPARAMETER1="IntMS=0"\nPARAMETER2="Exposures=0"\n',
                   encoding='ascii')
    ctrl = Ctrl(str(acf))
    ctrl.cfg.shutter_close_ms = 5200
    asyncio.run(ctrl._enforce_shutter_close_dwell())   # noqa: SLF001
    assert ctrl.shutter_dwell_ms is None
    assert ctrl.writes() == [], ctrl.sent


def test_prepare_decides_the_dwell_only_right_after_the_acf_apply():
    """⛔ `prepare()` 는 프레임마다 불린다 -- 그 사이 DARK/BIAS 가 `NoIntMS` 슬롯을 덮으므로
    ACF 를 민 직후에만 판정해야 한다 (소스 수준 확인)."""
    import inspect
    src = inspect.getsource(ArchonController.prepare)
    assert 'fresh = not self.acf_applied' in src
    body = src[src.index('self._require_param_slots()'):]
    assert body.index('if fresh:') < body.index('self._enforce_shutter_close_dwell()'), body

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`[archon] ccdflush` -- 노출 전 CCD flush (운영자 지시 2026-09-04 · 기제 단순화 2026-09-05, DevNote 11.33).

science R2610+ 부터 flush 는 타이밍 스크립트의 `FlushFrame`(Prep+Flush)이고, 켜고 끄는 일은
**설정 메모리의 `FirstFlush` 한 줄**(`PARAMETER0`)이다.  science 는 노출마다 `LOADPARAMS` 를
내므로 메모리가 1 이면 코어가 `Start:` 첫 줄에서 `FlushFrame` 으로 뛰어 **매 노출 전**
Prep+Flush 가 돈다.  `LOADTIMING` 은 없다 -- 코어 리셋도, `Exposures=0` 고정도, 두 단계
검증도 필요 없다.  (종전 R2609 까지는 `LINE9/LINE10` 의 `#` 를 여닫고 LOADTIMING 을 냈고,
그 기제의 시험은 이 판에서 지웠다.)

지키려는 것:

* **되읽어 판정한다** -- 캐시가 아니라 `RCONFIG`.  `apply_acf=false` 경로에서 앞 세션이
  켜 둔 1 을 되돌린다.
* **바뀔 때만 쓴다** -- 이미 원하는 값이면 WCONFIG 없이 `False`.
* **앉았는지 확인한다** -- 안 앉았으면 `False` 와 오류 로그 (조용히 캐시로 물러나지 않는다).
* **슬롯 번호만 믿지 않는다** -- R2608 의 `PARAMETER0` 은 `ContinuousExposures` 다.  그
  자리에 이름이 다르면 쓰지 않고, 켜라고 했으면 경고하고 flush 없이 간다.
* **`LOADTIMING` 을 내지 않는다.**
"""

from __future__ import annotations

import asyncio
import os

import pytest

import ics_archon  # noqa: F401

from icg_archon.config import IcgCfg  # noqa: E402
from ics_archon.archon.controller import ArchonController  # noqa: E402
from ics_archon.config import ArchonCfg  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCI_ACF = os.path.join(ROOT, 'acf', 'KMTC_SCI_101_STA0284_R2611_MK.acf')
GUIDE_ACF = os.path.join(ROOT, 'acf', 'KMTK_GUI_162_STA0201_R2618.acf')


class Ctrl(ArchonController):
    """실물 ACF 를 파싱한 진짜 컨트롤러 + 소켓만 가짜.

    `cmd()` 하나만 갈아 끼우므로 줄 번호 조회·키 정규화·`RCONFIG` 응답 검사가
    **전부 실제 코드**를 지난다.  ⭐ 컨트롤러 메모리(`_memory`)를 캐시(`config`)와
    **따로** 둔다 -- `WCONFIG` 가 앉은 것과 캐시가 바뀐 것을 가르기 위해서다
    (`stuck=True` 면 `WCONFIG` 가 앉지 않는 컨트롤러).
    """

    def __init__(self, acf: str = SCI_ACF, *, stuck: bool = False) -> None:
        cfg = ArchonCfg()
        cfg.acf = {'MK': acf}
        super().__init__('MK', cfg)
        self.parse_acf(acf)
        self.sent: list[str] = []
        self.stuck = stuck
        self._memory: dict[str, str] = dict(self.config)

    async def cmd(self, command: str, timeout: float = 0.0) -> bytes:  # noqa: ANN001
        self.sent.append(command)
        if command.startswith('WCONFIG') and not self.stuck:
            key, _, val = command[11:].partition('=')
            self._memory[key] = val
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
    assert asyncio.run(ctrl.set_first_flush(True)) is True
    assert ctrl.writes() == [_slot_write(ctrl, 'FirstFlush=1')], ctrl.sent
    assert ctrl.loads() == [], ctrl.sent
    assert ctrl.flag() == 'FirstFlush=1'
    assert ctrl.config['PARAMETER0'] == 'FirstFlush=1'


def test_it_reads_back_before_and_after_writing():
    """되읽기 둘 -- 쓰기 전(판정)과 뒤(앉았나).  `set_config` 는 캐시를 먼저 바꾸므로
    뒤의 되읽기가 없으면 *"보냈다"* 를 *"앉았다"* 로 착각한다 (11.13 F5)."""
    ctrl = Ctrl()
    asyncio.run(ctrl.set_first_flush(True))
    reads = [i for i, c in enumerate(ctrl.sent) if c.startswith('RCONFIG')]
    write = ctrl.sent.index(ctrl.writes()[0])
    assert len(reads) == 2 and reads[0] < write < reads[1], ctrl.sent


def test_already_on_writes_nothing():
    ctrl = Ctrl()
    asyncio.run(ctrl.set_first_flush(True))
    assert asyncio.run(ctrl.set_first_flush(True)) is False
    assert len(ctrl.writes()) == 1, ctrl.writes()


def test_the_default_science_acf_is_off_so_off_writes_nothing():
    ctrl = Ctrl()
    assert asyncio.run(ctrl.set_first_flush(False)) is False
    assert ctrl.writes() == []
    assert ctrl.loads() == []


def test_turning_it_off_again_writes_zero():
    ctrl = Ctrl()
    asyncio.run(ctrl.set_first_flush(True))
    assert asyncio.run(ctrl.set_first_flush(False)) is True
    assert ctrl.writes()[-1] == _slot_write(ctrl, 'FirstFlush=0')
    assert ctrl.flag() == 'FirstFlush=0'


# -- 컨트롤러 메모리가 캐시와 다를 때 (apply_acf=false 경로) ---------------------


def test_a_previous_session_left_it_on_and_the_option_off_restores_zero():
    """캐시(ACF 파일)는 0 인데 컨트롤러 메모리는 앞 세션의 1 -- 되읽어 알고 0 을 쓴다."""
    ctrl = Ctrl()
    ctrl._memory['PARAMETER0'] = 'FirstFlush=1'    # noqa: SLF001
    assert asyncio.run(ctrl.set_first_flush(False)) is True
    assert ctrl.writes() == [_slot_write(ctrl, 'FirstFlush=0')]
    assert ctrl.flag() == 'FirstFlush=0'


def test_controller_already_on_syncs_the_cache_without_writing():
    ctrl = Ctrl()
    ctrl._memory['PARAMETER0'] = 'FirstFlush=1'    # noqa: SLF001
    assert asyncio.run(ctrl.set_first_flush(True)) is False
    assert ctrl.writes() == []
    assert ctrl.config['PARAMETER0'] == 'FirstFlush=1', '캐시를 컨트롤러 값에 맞춘다'


# -- 실패 · 구판 ACF ----------------------------------------------------------


def test_a_write_that_did_not_land_is_reported(caplog):  # noqa: ANN001
    """⛔ 되읽은 값이 다르면 `False` + 오류 로그.  캐시로 물러나 *됐다* 고 하지 않는다."""
    ctrl = Ctrl(stuck=True)
    with caplog.at_level('ERROR'):
        assert asyncio.run(ctrl.set_first_flush(True)) is False
    assert ctrl.flag() == 'FirstFlush=0'
    assert any('앉지 않았다' in r.getMessage() for r in caplog.records), caplog.text


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
        assert asyncio.run(ctrl.set_first_flush(True)) is False
    assert ctrl.writes() == [] and ctrl.loads() == [], ctrl.sent
    assert any('flush 없이' in r.getMessage() for r in caplog.records), caplog.text
    caplog.clear()
    with caplog.at_level('WARNING'):
        assert asyncio.run(ctrl.set_first_flush(False)) is False
    assert not [r for r in caplog.records if r.levelname == 'WARNING'], caplog.text


def test_guide_has_no_option_so_its_constant_is_never_touched():
    """guide 의 `FirstFlush=1` 은 **ACF 상수**다 (R2616).  `IcgCfg` 에 `ccdflush` 가 없어
    `prepare()` 가 `set_first_flush` 를 부르지 않는다 -- 그 판정은 `getattr(cfg, 'ccdflush',
    None) is not None` 이다."""
    assert getattr(IcgCfg(), 'ccdflush', None) is None
    assert ArchonCfg().ccdflush is False
    ctrl = Ctrl(GUIDE_ACF)
    assert ctrl.flag() == 'FirstFlush=1'


# -- ini ---------------------------------------------------------------------


def test_the_ini_default_is_off():
    """⭐ **기본은 꺼짐**이다 (운영자 정정 2026-09-04: *"보통은 false, 가끔 true"*).

    ⭐ 그래서 10장 실측(독출 12.77 s · 주기 13.27 s)과 `MIN_FRAME_PERIOD` 는
    **기본 구성의 값이 맞다** -- 켤 때만 `SkipLine(FlushLines)` 만큼 길어진다.
    ⚠️ 켠 채로 운영할 거면 주기를 다시 재야 한다.  ⭐ 다만 `MIN_FRAME_PERIOD`
    는 두 안전검사에서 **하한**으로만 쓰이므로(잠금이 주기를 넘는지 · 버퍼 수가
    충분한지) 실제 주기가 더 길면 검사는 **보수적인 쪽으로** 틀린다 -- 위험한
    방향이 아니다.
    """
    assert ArchonCfg().ccdflush is False


@pytest.mark.parametrize('word, want', [
    ('true', True), ('TRUE', True), ('on', True), ('ON', True), ('1', True),
    ('false', False), ('FALSE', False), ('off', False), ('Off', False),
    ('0', False),
])
def test_the_ini_takes_all_six_words_in_any_case(tmp_path, word, want):  # noqa: ANN001
    """⭐ `true`/`on`/`1` 과 `false`/`off`/`0` 을 **같게** 받는다 (운영자 2026-09-04).

    ini 키·값 모두 **대소문자를 안 가린다**.
    """
    import configparser

    from ics_archon import config as acfg_mod

    cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    cp.read(os.path.join(ROOT, 'ics_archon.ini'), encoding='utf-8')
    cp['archon']['ccdflush'] = word
    path = tmp_path / 'ics.ini'
    with open(path, 'w', encoding='utf-8') as fh:
        cp.write(fh)
    assert acfg_mod.load(str(path)).ccdflush is want


def test_an_unrecognized_word_is_refused(tmp_path):  # noqa: ANN001
    """⛔ **모르는 값은 모른다고 말한다** -- 조용히 거짓으로 떨어뜨리지 않는다.

    `ture` 같은 오타 하나가 기능을 소리 없이 끄면 안 된다.
    """
    import configparser

    from ics_archon import config as acfg_mod

    cp = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    cp.read(os.path.join(ROOT, 'ics_archon.ini'), encoding='utf-8')
    cp['archon']['ccdflush'] = 'ture'
    path = tmp_path / 'ics.ini'
    with open(path, 'w', encoding='utf-8') as fh:
        cp.write(fh)
    with pytest.raises(acfg_mod.ArchonConfigError) as exc:
        acfg_mod.load(str(path))
    assert 'ccdflush' in str(exc.value)


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
        self.config_dirty = False
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

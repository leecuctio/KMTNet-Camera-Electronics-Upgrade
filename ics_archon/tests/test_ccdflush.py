#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`[archon] ccdflush` -- 노출 전 CCD flush (운영자 지시 2026-09-04).

타이밍 스크립트의 두 줄 앞에 붙은 `#` 를 여닫는 일이다:

    LINE9 ="#X; CALL Prep"
    LINE10="#X; CALL Flush"

⭐ 그 둘은 `Continuous:` 바로 아래 **적분(`IntUnit`) 직전**에 있으므로, 켜면
`ERASE` 한 번이 아니라 **매 프레임** Prep+Flush 가 돈다.

지키려는 것 셋:

* ⛔⛔ **줄 번호로만 고치지 않는다** -- guide ACF 의 같은 번호는
  `X; CALL IntUnit(IntMS)` 다.  덮으면 **적분이 통째로 사라진다**.
* ⭐ **따옴표를 보존한다** -- ACF 값은 따옴표를 포함한 원문이고, 잃으면 그 줄이
  다른 뜻이 된다.
* **바꿨을 때만 `LOADTIMING`** -- 안 바뀌었는데 태우면 기동이 그만큼 느려지고,
  바뀌었는데 안 태우면 **설정만 바뀌고 거동은 그대로**다(조용히 틀린다).
"""

from __future__ import annotations

import asyncio
import os

import pytest

import ics_archon  # noqa: F401

from ics_archon.archon.controller import (ArchonController,  # noqa: E402
                                          ArchonError, flush_line)
from ics_archon.config import ArchonCfg  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCI_ACF = os.path.join(ROOT, 'acf', 'KMTC_SCI_101_STA0284_R2608_MK.acf')
GUIDE_ACF = os.path.join(ROOT, 'acf', 'KMTK_GUI_162_STA0201_R2614.acf')


class Ctrl(ArchonController):
    """실물 ACF 를 파싱한 진짜 컨트롤러 + 소켓만 가짜.

    `cmd()` 하나만 갈아 끼우므로 줄 번호 조회·키 정규화·`RCONFIG` 응답 검사가
    **전부 실제 코드**를 지난다.
    """

    def __init__(self, acf: str = SCI_ACF) -> None:
        cfg = ArchonCfg()
        cfg.acf = {'MK': acf}
        super().__init__('MK', cfg)
        self.parse_acf(acf)
        self.sent: list[str] = []

    async def cmd(self, command: str, timeout: float = 0.0) -> bytes:  # noqa: ANN001
        self.sent.append(command)
        if command.startswith('RCONFIG'):
            line = int(command[7:11], 16)
            for key, val in self.config.items():
                if self.configline.get(key) == line:
                    return ('%s=%s' % (key, val)).encode('ascii')
            return b''
        return b''

    def writes(self) -> list[str]:
        return [c for c in self.sent if c.startswith('WCONFIG')]

    def loads(self) -> list[str]:
        return [c for c in self.sent if c == 'LOADTIMING']


# -- 문자열 다루기 ----------------------------------------------------------


@pytest.mark.parametrize('raw, on, want', [
    ('"#X; CALL Prep"', True, '"X; CALL Prep"'),
    ('"X; CALL Prep"', False, '"#X; CALL Prep"'),
    ('"X; CALL Prep"', True, '"X; CALL Prep"'),        # 이미 켜짐 -- 그대로
    ('"#X; CALL Flush"', False, '"#X; CALL Flush"'),   # 이미 꺼짐 -- 그대로
    ('#X; CALL Flush', True, 'X; CALL Flush'),         # 따옴표 없는 판
])
def test_the_comment_marker_toggles_and_the_quotes_survive(raw, on, want):  # noqa: ANN001
    """⭐ 따옴표를 잃으면 그 줄이 다른 뜻이 된다."""
    assert flush_line(raw, on) == want


def test_a_double_marker_is_cleaned_up():
    """`##X; …` 처럼 두 번 붙은 것도 한 번에 푼다 (손으로 고친 ACF 대비)."""
    assert flush_line('"##X; CALL Prep"', True) == '"X; CALL Prep"'


# -- 실제 ACF 에 대고 -------------------------------------------------------


def test_turning_it_on_edits_both_lines_and_loads_the_timing_once():
    """⭐ 두 줄을 고치고 **LOADTIMING 은 한 번**이다."""
    ctrl = Ctrl()
    changed = asyncio.run(ctrl.set_ccdflush(True, required=True))
    assert changed is True
    writes = ctrl.writes()
    # ⚠️ **따옴표는 와이어에 없다** -- `parse_acf` 가 `value.replace('"','')`
    # 로 떼고(labtest 관례) 컨트롤러에는 그 형태로 나간다.  `flush_line` 이
    # 따옴표를 보존하는 것은 그 규약이 바뀌어도 안 깨지게 하려는 것이다.
    assert any('LINE9=X; CALL Prep' in c for c in writes), writes
    assert any('LINE10=X; CALL Flush' in c for c in writes), writes
    assert ctrl.loads() == ['LOADTIMING'], ctrl.sent


def test_exposures_is_pinned_to_zero_before_the_timing_is_reloaded():
    """⛔⛔ **`LOADTIMING` 앞에 `Exposures=0` 을 눌러 둔다** (매뉴얼 p.51).

    매뉴얼 문면: *"LOADTIMING -- Parses and compiles the timing script **and
    parameters** contained in the configuration memory, and applies them to the
    system.  **This resets the timing cores.**"*  즉 ①파라미터를 **적용하고**
    ②코어를 리셋해 스크립트를 **첫 줄부터** 돌린다.

    ⚠️ 그래서 앞 프레임의 `Exposures=1` 이 설정 메모리에 남아 있으면 **여기서
    유령 독출이 시작된다** -- 운영자가 ArchonGUI 로 실측한 거동이 그것이다
    (`Exposures=1` + "Load Timing" -> 독출 진행).

    ⭐ 눌러 둔 값은 남지 않는다 -- 프레임마다 `trigger()` 가 다시 쓰고
    `LOADPARAMS`(코어 리셋 없음, p.52)를 낸다.
    """
    ctrl = Ctrl()
    asyncio.run(ctrl.set_ccdflush(True, required=True))
    writes = ctrl.writes()
    assert any('Exposures=0' in c for c in writes), (
        'LOADTIMING 앞에 Exposures 를 안 눌렀다: %r' % writes)
    # ⭐ **순서가 요점이다** -- 누른 뒤에 태워야 한다.
    zero_at = max(i for i, c in enumerate(ctrl.sent) if 'Exposures=0' in c)
    load_at = ctrl.sent.index('LOADTIMING')
    assert zero_at < load_at, ctrl.sent


def test_the_disarm_is_written_before_the_flush_lines():
    """⭐ **순서: `Exposures=0` -> flush 두 줄 -> 되읽기 -> `LOADTIMING`**
    (운영자 확정 2026-09-04).

    세 `WCONFIG` 는 다 "설정 메모리에 글자만 적는" 일이라(매뉴얼 p.51) 서로의
    순서가 거동을 바꾸지는 않는다.  ⭐ 그래도 **먼저 무장을 해제하는** 순서로
    두면 나중에 누가 사이에 이른 `return` 이나 중간 적용을 끼워도 **안전한
    쪽으로** 깨진다.
    """
    ctrl = Ctrl()
    asyncio.run(ctrl.set_ccdflush(True, required=True))
    writes = [c for c in ctrl.sent if c.startswith('WCONFIG')]
    exp = next(i for i, c in enumerate(writes) if 'Exposures=0' in c)
    line9 = next(i for i, c in enumerate(writes) if 'LINE9=' in c)
    assert exp < line9, writes


def test_a_write_that_did_not_land_stops_before_loadtiming(caplog):  # noqa: ANN001
    """⛔ **되읽기가 어긋나면 `LOADTIMING` 을 안 낸다** (2026-09-04).

    `set_config()` 는 왕복이 실패해도 **로컬 캐시를 먼저** 갈아 끼운다
    (11.13 F5) -- *"보냈다"* 와 *"앉았다"* 가 다르다.  ⭐ 확인을 **태우기
    전에** 두는 것이 요점이다: 어긋나면 `LOADTIMING` 을 아예 안 내므로
    **아무것도 적용되지 않고 코어도 안 리셋된다**.  뒤에 두면 이미 태운 뒤라
    늦다.
    """
    import logging

    class Stubborn(Ctrl):
        """`PARAMETER*` 쓰기가 **컨트롤러에 안 앉는** 상황을 흉내 낸다."""

        async def set_config(self, key, value):  # noqa: ANN001, ANN201
            if key.upper().startswith('PARAMETER'):
                self.sent.append('WCONFIG-LOST %s=%s' % (key, value))
                return
            return await super().set_config(key, value)

    caplog.set_level(logging.ERROR)
    ctrl = Stubborn()
    # ⚠️ **배포 ACF 는 이미 `Exposures=0`** 이라(실물 확인) 그대로 두면 쓰기가
    # 유실돼도 되읽기가 맞아떨어진다.  이 시험이 무엇을 보는지 살리려면 앞
    # 프레임이 남긴 `Exposures=1` 상태를 만들어야 한다 -- 그것이 유령 독출의
    # 전제이기도 하다.
    ctrl.config['PARAMETER1'] = 'Exposures=1'
    assert asyncio.run(ctrl.set_ccdflush(True, required=True)) is False
    assert ctrl.loads() == [], 'Exposures 가 안 앉았는데 LOADTIMING 을 냈다'
    assert any('LOADTIMING' in r.message for r in caplog.records),         [r.message for r in caplog.records]


def test_nothing_is_pinned_when_the_timing_is_not_reloaded():
    """⚠️ 안 바뀌었으면 `Exposures` 도 **안 건드린다** -- 태우지 않으니까."""
    ctrl = Ctrl()
    asyncio.run(ctrl.set_ccdflush(False))
    assert ctrl.writes() == [] and ctrl.loads() == []


def test_the_default_acf_is_already_off_so_nothing_is_written():
    """⚠️ 안 바뀌었는데 태우면 기동만 느려진다 -- 그때는 아무것도 안 한다."""
    ctrl = Ctrl()
    changed = asyncio.run(ctrl.set_ccdflush(False))
    assert changed is False
    assert ctrl.writes() == [] and ctrl.loads() == []


def test_turning_it_off_again_restores_the_comment():
    """앞 세션이 켜 뒀으면 되돌린다 (`apply_acf=false` 경로의 몫)."""
    ctrl = Ctrl()
    asyncio.run(ctrl.set_ccdflush(True, required=True))
    ctrl.sent.clear()
    changed = asyncio.run(ctrl.set_ccdflush(False))
    assert changed is True
    assert any('LINE9=#X; CALL Prep' in c for c in ctrl.writes()), ctrl.sent
    assert ctrl.loads() == ['LOADTIMING']


# -- ⛔ guide ACF 를 지킨다 --------------------------------------------------


def test_a_guide_acf_is_left_alone_when_the_option_is_off():
    """⛔ guide 의 `LINE9` 은 **적분 호출**이다 -- 건드리면 노출이 사라진다.

    ⭐ 꺼져 있을 때는 조용히 건너뛴다: 같은 컨트롤러 코드를 icg 도 쓰므로
    여기서 오류를 내면 **guide 기동이 통째로 막힌다**.
    """
    ctrl = Ctrl(GUIDE_ACF)
    assert asyncio.run(ctrl.set_ccdflush(False)) is False
    assert ctrl.writes() == [] and ctrl.loads() == []
    # 실물 확인 -- 그 줄이 정말 적분 호출이다.
    assert 'IntUnit' in ctrl.config['LINE9']


def test_an_acf_without_the_flush_lines_warns_but_does_not_stop_the_run(caplog):  # noqa: ANN001
    """⭐ 켜라고 했는데 못 켜면 **크게 경고하되 기동은 세우지 않는다**.

    ⚠️ 처음에는 오류로 올렸는데, 그러면 그 줄이 없는 ACF 로는 프레임이 **한
    장도** 안 나온다 -- flush 옵션 하나 때문에 관측을 통째로 잃는 것이 더 나쁘다.
    ⛔ 안전 성질(엉뚱한 줄에 안 쓴다)은 그대로다.
    """
    import logging

    caplog.set_level(logging.WARNING)
    ctrl = Ctrl(GUIDE_ACF)
    assert asyncio.run(ctrl.set_ccdflush(True, required=True)) is False
    assert ctrl.writes() == [], 'guide 타이밍 줄에 썼다'
    assert ctrl.loads() == []
    assert any('ccdflush' in r.message for r in caplog.records), \
        [r.message for r in caplog.records]


def test_a_half_matching_acf_writes_nothing_at_all(caplog):  # noqa: ANN001
    """⛔ **`LINE10` 이 flush 줄이 아니면 `LINE9` 도 안 쓴다** (2026-09-04).

    종전에는 읽기와 쓰기가 한 루프였다 -- `LINE9` 을 **이미 `WCONFIG` 로 쓴
    뒤** `LINE10` 에서 걸려 루프 안의 `return False` 로 빠져나갔다.  그러면
    `LOADTIMING` 도 안 나가고 되돌리지도 않은 채 호출자에게는 `False`
    (= *"안 바꿨다"*) 로 보고되어, 컨트롤러 설정에는 **`Flush` 없는 `Prep`**
    이 남는다.  ⛔ 다음 프레임에도 안 낫는다 -- `LINE9` 은 이미 want 라 다시
    안 쓰이고 `LINE10` 은 또 걸려서 **영원히 반쪽**이다.  그 상태에서 누가
    벤더 GUI 나 `APPLYALL` 로 스크립트를 태우면 그때 반쪽이 실제로 켜진다.

    ⭐ 이 시험이 못박는 성질: **확인이 끝나기 전에는 한 줄도 안 쓴다.**
    """
    import logging

    caplog.set_level(logging.WARNING)
    ctrl = Ctrl()
    # guide ACF 의 같은 번호가 실제로 이것이다 -- 덮으면 적분이 사라진다.
    ctrl.config['LINE10'] = 'X; CALL IntUnit(IntMS)'
    assert asyncio.run(ctrl.set_ccdflush(True, required=True)) is False
    assert ctrl.writes() == [], '반쪽만 썼다: %r' % ctrl.writes()
    assert ctrl.loads() == []


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

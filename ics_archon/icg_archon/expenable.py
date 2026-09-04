#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""노출 잠금 플래그 -- `EXPENABLE` (운영자 확정 2026-09-03).

초점면 작업 중에 노출이 시작되는 것을 막는 **지속 플래그**다.  `STOP`/`ABORT`
와 다르다: 그것들은 *진행 중인 것*을 세우는 일회성이고, 이것은 **다음 `GO` 를
계속 거절하는 상태**다.

* 받는 값은 `ON`/`TRUE`(허용) · `OFF`/`FALSE`(금지) 넷이고, 응답은 **정규형**
  (`ON`/`OFF`)으로 되돌린다 -- 운영자가 `true` 를 쳐도 로그가 한 형태로만
  남아 나중에 grep 이 된다.
* ⛔ **모르는 값은 기본값으로 떨어뜨리지 않는다** -- `EXPENABLE FLASE` 는
  거부하고 **상태를 그대로 둔다.**  ⭐ 이 규칙이 **잘림 손상까지 막는다**:
  시리얼 구간에서 `OFF` 가 `O` 로 잘려 와도 거부된다 (그 구간의 실측 고장이
  바이트 손상·메시지 접합이다).
* **지속된다** -- 재기동해도 유지돼야 한다.  `expnum` 과 같은 수법으로
  쓴다(내용 `fsync` -> `os.replace` -> 디렉터리 `fsync`).

⚠️ **science(ICS)는 막지 않는다** (운영자 확정) -- 초점면 작업 중 ICS 쪽은
사람이 지킨다.  나중에 필요해지면 `cmd_go` 검사를 `ics_sim` 으로 올리는 것은
한 줄이지만, 지금은 **`ics_sim` 을 0줄도 안 고친다.**
"""

from __future__ import annotations

import logging
import os

from ics_archon import _simpath

_simpath.ensure()

from ics_sim.state import _fsync_dir  # noqa: E402  -- 같은 영속 규약을 쓴다

log = logging.getLogger('icg_archon.expenable')

#: 와이어·응답의 정규형.
ON, OFF = 'ON', 'OFF'

#: 받는 어휘 -> 정규형.  ⚠️ 여기 없는 값은 **거부**한다 (기본값으로 떨어뜨리지
#: 않는다 -- 위 docstring).
VOCAB = {'ON': True, 'TRUE': True, 'OFF': False, 'FALSE': False}


class ExpEnable:
    """지속되는 노출 허용 플래그.

    ⚠️ **폴라리티가 `expnum` 과 반대다** -- 값을 못 믿을 때 `expnum` 은 이어서
    세면 되지만 이것은 **안전 장치**라 모르면 잠그는 쪽이 맞다.
    """

    def __init__(self, path: str = '') -> None:
        self.path = path
        #: 지금 노출을 허용하나.
        self.allowed = True
        #: 기동에서 파일을 어떻게 읽었나 -- 진단·시험용.
        self.origin = 'default'

    # -- 읽기 -------------------------------------------------------------

    def load(self) -> None:
        """기동에서 한 번.  ⚠️ **"없음" 과 "못 읽음" 을 가른다.**

        * 경로가 없거나 **파일이 아직 없으면** -> 허용 (초기 상태).  ⭐ 아무도
          잠근 적이 없다는 뜻이고, 첫 구동마다 잠겨 있으면 체크리스트가
          `EXPENABLE ON` 없이는 한 걸음도 못 간다.
        * 파일이 **있는데 못 읽거나 값이 어휘 밖이면** -> **금지 + WARNING.**
          잠금 상태를 알 수 없을 때 허용으로 기동하면 **잠금이 조용히 풀린다.**

        ⚠️ 이 갈래는 판단이다 -- 운영자 문면은 *"파일을 못 읽으면 금지로
        기동"* 이었고 "없음" 은 따로 적히지 않았다.  같은 부류의 갈래를 이
        저장소가 이미 쓴다 (F2: *"보고 없음"* 과 *"0"* 은 다른 뜻이다).
        """
        if not self.path:
            self.allowed, self.origin = True, 'no-path'
            return
        if not os.path.exists(self.path):
            self.allowed, self.origin = True, 'absent'
            log.info('노출 잠금 기록이 없다 -- 허용으로 시작한다 (%s)', self.path)
            return
        try:
            with open(self.path, encoding='utf-8') as fh:
                raw = fh.read().strip().upper()
        except OSError as exc:
            self.allowed, self.origin = False, 'unreadable'
            log.warning('노출 잠금 기록을 읽지 못했다 (%s: %s) -- **금지**로 '
                        '기동한다.  풀려면 EXPENABLE ON', self.path, exc)
            return
        if raw not in VOCAB:
            self.allowed, self.origin = False, 'garbled'
            log.warning('노출 잠금 기록이 어휘 밖이다 (%s: %r) -- **금지**로 '
                        '기동한다.  풀려면 EXPENABLE ON', self.path, raw)
            return
        self.allowed, self.origin = VOCAB[raw], 'file'
        log.info('노출 잠금 기록을 이어받는다 -- %s (%s)', self.word, self.path)

    # -- 쓰기 -------------------------------------------------------------

    def set(self, allowed: bool) -> None:
        """값을 바꾸고 **곧바로** 기록한다.

        ⚠️ 기록 실패는 막지 않는다 -- 메모리 상태는 바뀌고 경고만 남긴다.
        (막으면 초점면 작업을 못 잠근다.  잠그는 쪽이 안전하다.)
        """
        self.allowed = allowed
        self.origin = 'set'
        self._record()

    def _record(self) -> None:
        path = self.path
        if not path:
            return
        tmp = '%s.tmp' % path
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(tmp, 'w', encoding='utf-8') as fh:
                fh.write('%s\n' % self.word)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            _fsync_dir(parent or '.')
        except OSError as exc:
            log.warning('노출 잠금(%s)을 기록할 수 없다 (%s: %s) -- 재기동하면 '
                        '이 값이 사라진다', self.word, path, exc)

    # -- 표현 -------------------------------------------------------------

    @property
    def word(self) -> str:
        """정규형 한 낱말 -- 응답·기록·`HKDATA` 가 같은 글자를 쓴다."""
        return ON if self.allowed else OFF


def parse(arg: str):  # noqa: ANN201
    """인자 -> `True`/`False`, 어휘 밖이면 `None`.

    ⚠️ `None` 을 **기본값으로 접지 말 것** -- 부르는 쪽이 거부해야 한다.
    """
    return VOCAB.get((arg or '').strip().upper())

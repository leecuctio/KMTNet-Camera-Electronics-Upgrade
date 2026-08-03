#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUXSTATUS / TCSSTATUS relay.

ICS 는 TC(TCS Agent)에 텔레메트리를 질의해서 과학 CCD 들에게 중계한다.  각 IC 는
그 값을 저장해뒀다가 FITS 헤더에 기록한다.  CCD 구동 자체에는 영향이 없다.

실측에서 확인된 두 가지 특징 (DevNote 4.3):

1. **필드 순서가 정확히 역순이다.**  TC 응답이
       AUXQDATE=.. TIMESYS=.. TELID=.. ... ENS7=..
   이면 ICS 는
       ENS7=.. ... TELID=.. TIMESYS=.. AUXQDATE=..
   순서로 중계한다.  스택에 쌓았다 빼는 구현으로 보인다.

2. **필드 집합이 사이트마다 다르다.**  SSO 는 DSSTAT 앞에 돔 필드
   (DSTEL DSALT DSAUTO DSSAF DSLW DSUP)가 더 있고 GBUILD 가 채워져 있는 반면,
   CTIO 는 그 필드들이 없고 GBUILD= 가 빈 값이다.

그래서 사이트별 필드 테이블을 두지 않고 **받은 key=value 를 순서 그대로 보존해
역순으로 되돌려 보낸다**(pass-through).  ICS 가 알아야 할 것은 "어디까지가 TC
필드이고 어디부터 내가 붙이는 꼬리인지"뿐이다.  FITS 헤더 생성에 특정 필드가
필요한데 없으면 sentinel(수치 0, 문자열 NC)로 채운다 -- 레거시의 GBUILD=(빈 값),
DSSTAT=NC 관례와 같은 방식이다.

타이밍 (ics_legacy_report 5.3절):
  * AUXSTATUS 는 ERASE 를 내리는 시점에 질의하고 **곧바로** 중계한다.
  * TCSSTATUS 는 같이 질의해두지만 **셔터가 실제로 열린 시각을 DATE-OBS 로
    확정한 뒤에야** 중계한다.  FITS 헤더의 DATE-OBS/좌표가 노출 시작 순간을
    정확히 반영하도록 하기 위한 설계다.
"""

from __future__ import annotations

import asyncio
import logging

from . import impv2
from .config import SimConfig
from .impv2 import Message

log = logging.getLogger('ics_sim.telemetry')

#: ICS 가 AUXSTATUS 중계 끝에 덧붙이는 꼬리 필드 순서.
AUX_TAIL = ('KBUILD', 'MBUILD', 'TBUILD', 'NBUILD', 'GBUILD', 'ICSBUILD')

#: 없을 때 sentinel 을 넣어줄 필드 (FITS 헤더가 기대하는 것들).
_SENTINEL_NUM = frozenset({
    'ENS1', 'ENS2', 'ENS3', 'ENS4', 'ENS5', 'ENS6', 'ENS7',
    'FAPOSS', 'FAPOSE', 'FAPOSW', 'FAFOCUS', 'FATILTNS', 'FATILTEW',
    'FALIMS', 'FALIME', 'FALIMW', 'MCPOS', 'CHSET', 'CHPROC',
    'AZ', 'ALT', 'SECZ', 'EQUINOX',
})
_SENTINEL_STR = frozenset({
    'ENFAN', 'ENSTAT', 'CHOP', 'CHSTAT', 'MCSTAT', 'DSSTAT', 'FASTAT',
    'SHUTTER', 'SHUTOP', 'FILTER', 'FILNUM', 'FILTOP', 'FSSTAT',
    'AUXARC', 'AUXLINK', 'TELID', 'TIMESYS',
    'TCSDRIVE', 'TCSLIMIT', 'TELMOVE', 'TCSARC', 'TCSLINK', 'EXECODE',
    'RA', 'DEC', 'HA', 'ST',
})

#: TC 가 응답하지 않을 때 쓸 내장 텔레메트리 (tc_timeout_mode=canned).
#: 값은 CTIO 실측 로그에서 가져왔다.  TC 응답과 같은 순서로 적는다.
CANNED_AUX = (
    'AUXQDATE', 'TIMESYS', 'TELID', 'AUXLINK', 'AUXARC', 'AUXUDATE',
    'FSSTAT', 'FILTOP', 'FILNUM', 'FILTER', 'SHUTOP', 'SHUTTER',
    'FASTAT', 'FAFOCUS', 'FATILTNS', 'FATILTEW', 'FALIMS', 'FALIME', 'FALIMW',
    'FAPOSS', 'FAPOSE', 'FAPOSW', 'DSSTAT', 'MCSTAT', 'MCPOS',
    'CHSTAT', 'CHOP', 'CHSET', 'CHPROC', 'ENSTAT', 'ENFAN',
    'ENS1', 'ENS2', 'ENS3', 'ENS4', 'ENS5', 'ENS6', 'ENS7',
)
CANNED_AUX_VALUES = {
    'TIMESYS': 'UTC', 'AUXLINK': 'Up', 'AUXARC': 'Enabled',
    'FSSTAT': 'STANDBY', 'FILTOP': 'STANDBY', 'FILNUM': '3', 'FILTER': 'V',
    'SHUTOP': 'STANDBY', 'SHUTTER': 'CLOSED',
    'FASTAT': 'STANDBY', 'FAFOCUS': '-0.912', 'FATILTNS': '-262.5',
    'FATILTEW': '+51.0', 'FALIMS': '0', 'FALIME': '0', 'FALIMW': '0',
    'FAPOSS': '+0.372', 'FAPOSE': '-1.338', 'FAPOSW': '-1.770',
    'DSSTAT': 'NC', 'MCSTAT': 'STANDBY', 'MCPOS': '0',
    'CHSTAT': 'ERROR', 'CHOP': 'OFF', 'CHSET': '0.0', 'CHPROC': '0.0',
    'ENSTAT': 'STANDBY', 'ENFAN': 'ON',
    'ENS1': '16.5', 'ENS2': '17.5', 'ENS3': '18.2', 'ENS4': '37.2',
    'ENS5': '17.8', 'ENS6': '17.5', 'ENS7': '0.0',
}

CANNED_TCS = (
    'TCSQDATE', 'TIMESYS', 'TCSLINK', 'TCSARC', 'TCSUDATE',
    'RA', 'DEC', 'EQUINOX', 'HA', 'ST', 'SECZ', 'ALT', 'AZ',
    'TELMOVE', 'TCSLIMIT', 'TCSDRIVE', 'EXECODE',
)
CANNED_TCS_VALUES = {
    'TIMESYS': 'UTC', 'TCSLINK': 'Up', 'TCSARC': 'Enabled',
    'RA': '04:30:45.61', 'DEC': '-30:00:01.7', 'EQUINOX': '2000.000',
    'HA': '-00:00:00', 'ST': '04:30:45', 'SECZ': '1.00',
    'ALT': '90.0', 'AZ': '0.0',
    'TELMOVE': 'Idle', 'TCSLIMIT': 'No', 'TCSDRIVE': 'Disabled',
    'EXECODE': 'E',
}


class TelemetryRelay:
    """TC 질의 결과를 보관하고 IC 중계 본문을 만든다."""

    def __init__(self, cfg: SimConfig, send_req) -> None:  # noqa: ANN001
        """
        Args:
            send_req: ``send_req(dest, cmdword)`` -- ICS>TC AUXSTATUS 같은
                요청을 내보내는 콜백.  transport 의존을 여기 두지 않으려고
                주입받는다.
        """
        self.cfg = cfg
        self._send_req = send_req
        #: 마지막 TC 응답의 (key, value) 목록 -- **원문 순서 보존**
        self.aux_fields: list[tuple[str, str]] = []
        self.tcs_fields: list[tuple[str, str]] = []
        self._waiters: dict[str, asyncio.Future] = {}
        self.last_aux_ok = False
        self.last_tcs_ok = False

    # -- TC 질의 ----------------------------------------------------------

    async def query(self, what: str) -> bool:
        """TC 에 AUXSTATUS 또는 TCSSTATUS 를 질의한다.

        타임아웃이면 False.  노출은 중단하지 않는다 -- 레거시도 TC 가 답하지
        않으면 빈 필드로 그냥 중계하고 진행했다(DevNote 6.5).
        """
        key = what.upper()
        if self.cfg.behavior.injecting('tc_timeout'):
            self._apply_timeout(key)
            return False

        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._waiters[key] = fut
        self._send_req('TC', key)
        try:
            await asyncio.wait_for(
                fut, timeout=self.cfg.scaled(self.cfg.timing.tc_query_timeout))
        except asyncio.TimeoutError:
            log.warning('TC %s query timed out (mode=%s)',
                        key, self.cfg.timing.tc_timeout_mode)
            self._apply_timeout(key)
            return False
        finally:
            self._waiters.pop(key, None)
        return True

    def _apply_timeout(self, key: str) -> None:
        """TC 무응답 처리.

        passthrough  -- TC 필드를 통째로 비운다.  레거시 실측 형태로,
                        ICS 가 덧붙이는 꼬리만 남은 채 중계된다.
        canned       -- 내장 텔레메트리로 채운다.  TC 스텁 없이도 FITS 헤더가
                        그럴듯하게 나오길 원할 때.
        """
        from .state import stamp_iso_ms  # 순환 import 회피

        if self.cfg.timing.tc_timeout_mode == 'canned':
            now = stamp_iso_ms()
            if key == 'AUXSTATUS':
                vals = dict(CANNED_AUX_VALUES)
                vals['TELID'] = self.cfg.node.telid
                vals.setdefault('AUXQDATE', now)
                vals.setdefault('AUXUDATE', now)
                self.aux_fields = [(k, vals.get(k, '')) for k in CANNED_AUX]
                self.last_aux_ok = True
            else:
                vals = dict(CANNED_TCS_VALUES)
                vals.setdefault('TCSQDATE', now)
                vals.setdefault('TCSUDATE', now)
                self.tcs_fields = [(k, vals.get(k, '')) for k in CANNED_TCS]
                self.last_tcs_ok = True
            return

        if key == 'AUXSTATUS':
            self.aux_fields = []
            self.last_aux_ok = False
        else:
            self.tcs_fields = []
            self.last_tcs_ok = False

    def on_tc_reply(self, msg: Message) -> bool:
        """TC>ICS DONE: AUXSTATUS ... 수신 처리.  우리가 기다리던 것이면 True."""
        key = msg.cmdword.upper()
        if key not in ('AUXSTATUS', 'TCSSTATUS'):
            return False
        fields = list(impv2.iter_kv(msg.body))
        if key == 'AUXSTATUS':
            self.aux_fields = fields
            self.last_aux_ok = bool(fields)
        else:
            self.tcs_fields = fields
            self.last_tcs_ok = bool(fields)
        fut = self._waiters.get(key)
        if fut is not None and not fut.done():
            fut.set_result(True)
        return True

    # -- 중계 본문 --------------------------------------------------------

    def aux_body(self, expstatus: str, builds: dict[str, str]) -> str:
        """ICS>*.IC STATUS: AUXSTATUS 의 본문.

        TC 필드를 역순으로, 그 뒤에 BUILD 꼬리와 EXPSTATUS 를 붙인다.
        """
        parts = [f'{k}={v}' for k, v in reversed(self.aux_fields)]
        parts += [f'{k}={builds.get(k, "")}' for k in AUX_TAIL]
        parts.append(f'EXPSTATUS={expstatus}')
        return ' '.join(parts)

    def tcs_body(self, date_obs: str, expstatus: str) -> str:
        """ICS>*.IC STATUS: TCSSTATUS 의 본문.

        DATE-OBS 는 ICS 가 맨 앞에 덧붙인다.  값은 TC 질의 시각이 아니라
        **셔터가 실제로 열린 시각**이다.
        """
        parts = [f'DATE-OBS={date_obs}']
        parts += [f'{k}={v}' for k, v in reversed(self.tcs_fields)]
        parts.append(f'EXPSTATUS={expstatus}')
        return ' '.join(parts)

    # -- FITS 헤더 --------------------------------------------------------

    def header_dict(self, date_obs: str = '') -> dict[str, str]:
        """FITS 헤더용 딕셔너리.  없는 필드는 sentinel 로 채운다."""
        out: dict[str, str] = {}
        for k, v in self.aux_fields:
            out[k] = v
        for k, v in self.tcs_fields:
            out[k] = v
        for k in _SENTINEL_NUM:
            out.setdefault(k, '0')
        for k in _SENTINEL_STR:
            out.setdefault(k, 'NC')
        out.setdefault('TELID', self.cfg.node.telid)
        if date_obs:
            out['DATE-OBS'] = date_obs
        return out

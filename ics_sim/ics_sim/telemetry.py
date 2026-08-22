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

from . import impv2, rawcards
from .config import SimConfig
from .impv2 import Message

log = logging.getLogger('ics_sim.telemetry')

#: ICS 가 AUXSTATUS 중계 끝에 덧붙이는 꼬리 필드 순서.
AUX_TAIL = ('KBUILD', 'MBUILD', 'TBUILD', 'NBUILD', 'GBUILD', 'ICSBUILD')

#: 없을 때 sentinel 을 넣어줄 필드 (FITS 헤더가 기대하는 것들).
#:
#: **sentinel 은 계층에 따라 다르다** (C-9):
#:   - 레거시 **메시지 계층**(`ICS>*.IC STATUS: AUXSTATUS …`)은 `'0'` -- 레거시
#:     관례를 그대로 재현한다 (DevNote 4.3, 11.2).  아래 두 집합은 그쪽
#:     (`header_dict()`) 전용이다.
#:   - **FITS 카드**는 raw spec 5.7절이 전부 문자열 형으로 정했으므로 문자열
#:     공통 `'NC'` 하나다 (`fits_header_dict()` -- 카드 목록은
#:     `rawcards.RELAY_CARDS`).  `0` 을 값-없음으로 쓰면 `SECZ=0` 같은 값이
#:     유효값처럼 남아 조용한 오염이 된다.
_SENTINEL_INT = frozenset({
    'FALIMS', 'FALIME', 'FALIMW',   # 액추에이터 리밋 코드
    'MCPOS',                        # 주경 커버 개방률 %
})
_SENTINEL_FLOAT = frozenset({
    'ENS1', 'ENS2', 'ENS3', 'ENS4', 'ENS5', 'ENS6', 'ENS7',
    'FAPOSS', 'FAPOSE', 'FAPOSW', 'FAFOCUS', 'FATILTNS', 'FATILTEW',
    'CHSET', 'CHPROC',
    'AZ', 'ALT', 'SECZ', 'EQUINOX',
})
_SENTINEL_NUM = _SENTINEL_INT | _SENTINEL_FLOAT
#: AUX 실선의 이름 -> FITS 헤더 이름.  **converter 가 fallback 없이 읽는
#: 이름으로 옮겨 실어야 한다** (raw spec 5.7절 -- `DSTELALT` 는 레거시
#: `DSTEL` 의 개칭, D-013).
#:
#: `DSTEL` 이 그 사례다.  AUX 가 보내는 이름은 `DSTEL`(`pctcs/commands.c:2023`)
#: 인데, Archon converter 는 `v("DSTELALT","")` 로 **`DSTELALT` 만** 읽는다
#: (`v2_1.py:485`).  레거시32 converter 에는 `sv(ph,"DSTELALT", sv(ph,"DSTEL"))`
#: 로 fallback 이 있지만 Archon 쪽에는 없다 -- 그래서 옮겨 싣지 않으면 MEF 의
#: 돔-망원경 고도가 **오류 없이** 빈 값이 된다.
#:
#: 원래 이름도 함께 남긴다 -- 레거시 도구와의 연속성이고, 옮겨 실은 것이
#: 대조 가능해야 한다.
_FITS_RENAME = {'DSTEL': 'DSTELALT'}

_SENTINEL_STR = frozenset({
    'ENFAN', 'ENSTAT', 'CHOP', 'CHSTAT', 'MCSTAT', 'DSSTAT', 'FASTAT',
    'SHUTTER', 'SHUTOP', 'FILTER', 'FILNUM', 'FILTOP', 'FSSTAT',
    'AUXARC', 'AUXLINK', 'TELID', 'TIMESYS',
    'TCSDRIVE', 'TCSLIMIT', 'TELMOVE', 'TCSARC', 'TCSLINK', 'EXECODE',
    'RA', 'DEC', 'HA', 'ST',
    # 질의/갱신 시각.  **TC 가 답하지 않아도 카드를 남긴다** -- raw spec
    # 5장 전 카드가 원칙적으로 필수다.  카드가 아예 없으면 이 규격을
    # 모르는 취득 SW 가 쓴 파일과 구분되지 않는다.
    'AUXQDATE', 'AUXUDATE', 'TCSQDATE', 'TCSUDATE',
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
    # 돔 셔터·지향 -- newTCS 편입으로 출처가 TCS 계통이다 (raw spec 5.7절).
    # 실기 중계 필드명은 미확정이라 카드명과 같게 두었다 (canned 전용).
    'DSSTAT', 'DSUP', 'DSLW', 'DSSAF', 'DSAUTO', 'DSALT', 'DSAZ',
    'DSTELALT', 'DSTELAZ',
)
CANNED_TCS_VALUES = {
    'TIMESYS': 'UTC', 'TCSLINK': 'Up', 'TCSARC': 'Enabled',
    'RA': '04:30:45.61', 'DEC': '-30:00:01.7', 'EQUINOX': '2000.000',
    'HA': '-00:00:00', 'ST': '04:30:45', 'SECZ': '1.00',
    'ALT': '90.0', 'AZ': '0.0',
    'TELMOVE': 'Idle', 'TCSLIMIT': 'No', 'TCSDRIVE': 'Disabled',
    'EXECODE': 'E',
    'DSSTAT': 'STANDBY', 'DSUP': 'MID', 'DSLW': 'OPEN', 'DSSAF': 'INACTIVE',
    'DSAUTO': 'ENABLED', 'DSALT': '87.7', 'DSAZ': '12.3',
    'DSTELALT': '88.1', 'DSTELAZ': '12.1',
}


def _sync_error(dome: object, tel: object) -> str:
    """`DALTERR`/`DAZERR` -- 돔·망원경 지향차, 부호 포함 소수 1자리 문자열.

    견본 v1.0: `DSALT='87.7'` − `DSTELALT='88.1'` -> `DALTERR='-0.4'`.
    피연산 값이 없거나 수치가 아니면 `'NC'` -- 계산값을 지어내지 않는다.
    """
    try:
        diff = float(str(dome)) - float(str(tel))
    except (TypeError, ValueError):
        return 'NC'
    return f'{diff:+.1f}'


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
        #: 실효 사이트 코드.  TC 가 보낸 `TELID` 와 대조하는 기준이다.
        #: `app` 이 사이트를 판정한 뒤 넣어 준다 (D-015).  비어 있으면 대조를
        #: 건너뛴다 -- 단위 시험이 relay 를 홀로 만들 때가 그렇다.
        self.site_code = ''
        #: 이미 경고한 `TELID` 값.  **서로 다른 값마다 한 번씩** 경고한다 --
        #: "바뀔 때마다" 가 아니다.  값이 `KMTS` -> `KMTC`(일치) -> `KMTS` 로
        #: 오가도 두 번째 `KMTS` 는 조용하다.  이미 말한 사실을 다시 말할 이유가
        #: 없고, TC 를 재기동하는 동안 값이 오가는 것은 흔하다.
        #:
        #: AUXSTATUS 는 노출마다 오므로 매번 경고하면 하룻밤에 1000줄이 되고,
        #: 그러면 사람이 경고를 무시하는 것을 학습한다.  그건 검사가 없는 것보다
        #: 나쁘다.
        self._telid_warned: set[str] = set()

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

    def check_telid(self, fields: list[tuple[str, str]]) -> None:
        """TC 가 보낸 `TELID` 를 실효 사이트와 대조한다 (D-015).

        **경고만 한다.**  `TELID` 는 `pctcs.ini` 의 `FITS_TELID` 설정이고
        (`commands.c:1999` -> `aux.FitsTelID`, `loadconfig.c:512-514`) 기본값이
        사이트가 아닌 `KMTN` 이다(`pctcs.h:115`).  즉 정본이 못 되지만, 우리
        설정과 **독립된 두 번째 설정**이라 어긋남이 실제 정보를 준다.

        **없는 것은 불일치가 아니다.**  TC 가 안 뜨거나 `TELID` 를 안 보내면
        조용히 넘어간다 -- 정보가 없는 것과 틀린 것은 다르다.

        pctcs 기본값 `KMTN` 은 "설정이 안 됐다" 는 뜻이라 문구를 따로 준다.
        그걸 사이트 불일치로 말하면 엉뚱한 곳을 보게 된다.
        """
        if not self.site_code:
            return
        raw = next((v for k, v in fields if k.upper() == 'TELID'), '')
        telid = raw.strip().upper()
        if not telid or telid in self._telid_warned:
            return
        if telid == self.site_code:
            return
        self._telid_warned.add(telid)
        if telid == 'KMTN':
            log.warning(
                'TC 가 TELID=KMTN 을 보냈다 -- pctcs 의 FITS_TELID 가 설정되지 '
                '않은 기본값이다(pctcs.h:115). 우리 판정은 %s 이고 파일명은 '
                '%s.… 로 나간다. pctcs.ini 의 FITS_TELID 를 채울 것 (D-015)',
                self.site_code, self.site_code)
            return
        log.warning(
            'TC 의 TELID 가 우리 사이트 판정과 다르다.\n'
            '  TC (pctcs.ini FITS_TELID) : %s\n'
            '  우리 판정 (호스트 IP)      : %s\n'
            '파일명은 %s.… 로 저장된다. 둘 중 하나가 잘못 배포된 것이니 자료를 '
            '찍기 전에 확인할 것 (D-015)',
            telid, self.site_code, self.site_code)

    def on_tc_reply(self, msg: Message) -> bool:
        """TC>ICS DONE: AUXSTATUS ... 수신 처리.  우리가 기다리던 것이면 True."""
        key = msg.cmdword.upper()
        if key not in ('AUXSTATUS', 'TCSSTATUS'):
            return False
        fields = list(impv2.iter_kv(msg.body))
        if key == 'AUXSTATUS':
            self.aux_fields = fields
            self.last_aux_ok = bool(fields)
            # 사이트 정체 대조 (D-015).  서로 다른 값마다 한 번씩 경고한다.
            self.check_telid(fields)
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
        """**메시지 계층** 값 딕셔너리.  없는 필드는 레거시 관례대로 `'0'`/`'NC'`.

        ⚠️ **FITS 헤더에는 이걸 쓰지 않는다** -- `fits_header_dict()` 를 쓴다.
        수치 sentinel 이 `'0'` 이라 `SECZ=0`/`ALT=0` 이 유효값처럼 남는다
        (C-9 / raw_fits_spec OI-6).  레거시 재현이 필요한 중계 본문 전용이다.
        """
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

    def fits_header_dict(self, date_obs: str) -> dict[str, object]:
        """**FITS 헤더용** 값 딕셔너리 -- raw spec 5.7·5.8절 몫.

        카드 목록의 정본은 `rawcards.RELAY_CARDS`(TCS 27 + AUX 33 에서
        Tapaculo 2장 제외)다.  와이어에서 받은 값은 그대로 두고, 없는 카드만
        sentinel `'NC'` 로 채운다 -- **TC 중계 카드는 전부 문자열**이다
        (raw spec 5.7절 "TCS 중계값은 문자열로 싣는다", 레거시 계승).  구판의
        수치 sentinel(`-1`/`-999.0`)은 카드가 문자열 형으로 통일되면서 문자열
        공통 sentinel 로 접혔다.  메시지 계층(`header_dict()`, sentinel `'0'`)
        과는 계속 분리다 (C-9).

        와이어에 없는 파생·이관 카드는 여기서 만든다:

        * `TCSTIME` -- TCS 응답의 `TIMESYS` 를 **이관**한다.  ICS 자신의
          `TIMESYS` 카드(5.4절, `rawhdr`)와 시각계를 분리하는 신설 카드다.
        * `DSTELALT` -- 실선 `DSTEL` 의 개칭 (converter 가 fallback 없이 이
          이름만 읽는다, `_FITS_RENAME`).
        * `DALTERR`/`DAZERR` -- **ICS calculation** (raw spec 5.7절): 돔과
          망원경의 지향차.  피연산 카드가 없으면 `'NC'`.
        * `RADECSYS` -- TC 가 안 보내면 좌표계 기본 `'ICRS'`.
        * `TCSLINK`/`AUXLINK` -- 와이어 값이 없으면 마지막 질의 성패로.

        **`date_obs` 는 기본값이 없는 필수 인자다.** raw spec 5.4절이
        `DATE-OBS` 를 필수로, 출처를 ICS 로 정한다 -- ICS 가 노출을 개시하는
        그 시점의 OS 시각(UTC)을 스스로 찍는 값이다.  빈 값이 들어오면 **우리
        결함**이므로 에러를 남기고 카드를 비운다 -- `'NC'` 나 "현재 시각"으로
        채우면 converter 의 실패 경로(C-6)가 발동하지 않아 조용히 틀린 값이
        된다.
        """
        out: dict[str, object] = {}
        for k, v in self.aux_fields:
            out[k] = v
        for k, v in self.tcs_fields:
            out[k] = v
        # TCS 시각계 이관: 와이어 `TIMESYS`(TCS 응답) -> `TCSTIME` 카드.
        # ICS 의 `TIMESYS` 카드는 rawhdr(5.4절)가 'UTC' 로 싣는다.
        tcs_timesys = next(
            (v for k, v in self.tcs_fields if k.upper() == 'TIMESYS'), '')
        out.setdefault('TCSTIME', tcs_timesys or 'NC')
        # 실선 이름 -> converter 가 읽는 이름.  **원래 이름을 지우지 않는다**
        # (템플릿이 걸러 주므로 카드로 새지는 않는다 -- 대조용으로만 남는다).
        for wire, fits in _FITS_RENAME.items():
            if wire in out:
                out.setdefault(fits, out[wire])
        out.setdefault('RADECSYS', 'ICRS')
        out.setdefault('TCSLINK', 'Up' if self.last_tcs_ok else 'Down')
        out.setdefault('AUXLINK', 'Up' if self.last_aux_ok else 'Down')
        # 돔-망원경 지향차 (ICS calculation).  와이어가 직접 주면 그 값을 쓴다.
        out.setdefault('DALTERR',
                       _sync_error(out.get('DSALT'), out.get('DSTELALT')))
        out.setdefault('DAZERR',
                       _sync_error(out.get('DSAZ'), out.get('DSTELAZ')))
        for k in rawcards.RELAY_CARDS:
            out.setdefault(k, 'NC')
        if date_obs:
            out['DATE-OBS'] = date_obs
        else:
            log.error('DATE-OBS 가 비어 있다 -- ICS 가 노출 개시 시각을 찍지 '
                      '못했다는 뜻이고 우리 결함이다 (raw spec 5.4절). 카드를 '
                      '비워 두어 converter 가 이 노출을 거부하게 한다')
        return out

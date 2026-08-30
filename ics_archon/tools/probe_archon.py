#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""실기 첫 실행 도구 -- **미검증 3자리를 컨트롤러에게 직접 물어본다.**

`ics_archon` v0.0 은 가짜 컨트롤러로만 검증됐고, 잠정인 자리가 셋이다
(`../SMC_CLAUDE.md` 검토사항 B):

    1. STATUS 필드 이름 · 모듈 나열 순서   -> `Cn_TEMP` 의 자리
    2. 독출 진행률 · 독출 시간             -> `PCTREAD` · `Wrote` 25초 창
    3. 산출물 실물                          -> 기하 · 픽셀 배치 · 헤더

**이 도구가 그 셋을 순서대로 확인한다.**  본편(`python -m ics_archon`)을 그냥
돌리면 세 가지가 한꺼번에 걸려 원인을 가릴 수 없으므로, 위험이 낮은 것부터
하나씩 본다.  쓰는 코드는 본편과 **같은 모듈**이라 여기서 통과한 것은 본편에서도
통과한다.

    1단계  읽기 전용 (전원을 켜지 않는다)
        python tools/probe_archon.py --host 10.0.0.13
        -> SYSTEM · STATUS · FRAME 원문 + 해석 + 가정 대조

    2단계  ACF 대조 (여전히 읽기 전용)
        python tools/probe_archon.py --host 10.0.0.13 --acf acf/KMTC_SCI_101_STA0284_R2608_MK.acf
        -> 파라미터 슬롯이 컨트롤러 메모리와 맞는지 (RCONFIG 로 확인만)

    3단계  프레임 1장  ⚠️ **전원을 켜고 CCD 를 읽어낸다**
        python tools/probe_archon.py --host 10.0.0.13 --acf ... --expose 0 --write
        -> 독출 시간 실측 · FETCH 속도 · FITS 1장 (기하·헤더 확인용)

3단계는 `--expose` 를 준 경우에만 돈다.  끝나면 **무슨 일이 있어도 POWEROFF** 를
보낸다 (전원을 켠 채로 끝나는 것은 검출기 쪽 위험이다).

⚠️ 이 도구는 파일 이름을 `probe.<...>.fits` 로 쓴다 -- 관측 번호 공간(D-016)을
건드리지 않으려는 것이다.  아카이브에 넣을 자료를 만드는 도구가 아니다.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ics_archon import config as acfg_mod                 # noqa: E402
from ics_archon.archon import fitswrite, parse            # noqa: E402
from ics_archon.archon.controller import ArchonController  # noqa: E402
from ics_archon.archon.protocol import ArchonError        # noqa: E402
from ics_sim import rawcards, rawhdr                      # noqa: E402

OK, WARN, BAD = '  OK  ', ' 확인 ', ' 문제 '
_verdicts: list[tuple[str, str]] = []


def say(mark: str, label: str, detail: str = '') -> None:
    _verdicts.append((mark, label))
    print('[%s] %s%s' % (mark, label, ('\n         ' + detail) if detail else ''))


def block(title: str) -> None:
    print('\n' + '=' * 74 + '\n ' + title + '\n' + '-' * 74)


def _num(value, digits: int) -> str:
    """수치는 자리수 고정, sentinel 문자열(`'NC'`)은 그대로."""
    return ('%.*f' % (digits, value)) if isinstance(value, float) else str(value)


def dump(fields: dict, per_line: int = 3) -> None:
    """`KEY=VALUE` 를 보기 좋게.  **원문을 다 보여 준다** -- 우리가 모르는
    필드가 있는지가 이 도구의 요점이므로 추려서 보여 주면 안 된다."""
    items = ['%s=%s' % kv for kv in fields.items()]
    width = max((len(x) for x in items), default=0) + 2
    for i in range(0, len(items), per_line):
        print('   ' + ''.join(x.ljust(width) for x in items[i:i + per_line]))


# ---------------------------------------------------------------------------
# 1단계 -- 읽기 전용
# ---------------------------------------------------------------------------

async def stage_read_only(ctrl: ArchonController, acfg) -> dict:  # noqa: ANN001
    block('1단계  읽기 전용 -- SYSTEM · STATUS · FRAME')

    started = time.monotonic()
    await ctrl.connect()
    say(OK, '접속 %s:%d (%.3f초)'
        % (ctrl.link.host, ctrl.link.port, time.monotonic() - started))

    # -- SYSTEM ------------------------------------------------------------
    # **본편과 같은 스냅샷 자리에 넣는다** (`ctrl.system`/`ctrl.status`) --
    # 3단계의 헤더가 그 값을 읽으므로, 따로 들고 있으면 여기서는 보이는데
    # 파일에는 `NC` 가 실리는 어긋남이 생긴다.
    await ctrl.refresh_system()
    system = ctrl.system
    print('\n>> SYSTEM (%d 필드)' % len(system))
    dump(system)
    ident = parse.unit_identity(system)
    if ident.get('sn'):
        say(OK, 'BACKPLANE_ID = %s  (FITS CTRLnSN 의 원천)' % ident['sn'])
    else:
        say(BAD, 'BACKPLANE_ID 가 없다 -- CTRLnSN 이 sentinel 로 실린다')

    mods = parse.module_types(system)
    shown = ', '.join('%d:%s' % (s, parse.MODULE_TYPES.get(t, '?%d' % t))
                      for s, t in sorted(mods.items()) if t)
    ad = sorted(s for s, t in mods.items() if t in parse.AD_TYPES)
    print('\n   모듈: %s' % (shown or '(보고 없음)'))
    print('   비디오(AD 계열) 슬롯: %s' % (ad or '없음'))

    # ⚠️ 종전에는 'AD 가 슬롯 5~8 인가' 로 판정했고 그것이 틀렸다 (2026-08-27).
    #    실기 science 는 AD 계열이 5·8 둘뿐이라 **정상 구성에서 BAD 가 났다.**
    #    판정은 자리 표(규격 5.6.1절) 대 실제 장착 모듈 비교로 바꿨다.
    problems = parse.field_order_problems(system)
    slots = sorted(parse.temp_mod_slots())
    if not problems:
        say(OK, '장착 모듈이 규격 5.6.1절 자리 표와 정합한다 (%d자리: %s)'
                % (len(parse.TEMP_MODS), slots))
    else:
        for note in problems:
            say(BAD, note, '지금 자리 표(%d자리): %s'
                           % (len(parse.TEMP_MODS), ' '.join(parse.TEMP_MODS)))
    if not ad:
        say(WARN, '비디오(AD 계열) 모듈을 못 찾았다 (형 %s) -- 형 번호가 '
                  '매뉴얼·표에 없는 신형일 수 있다'
                  % ', '.join(str(t) for t in sorted(parse.AD_TYPES)))

    # -- STATUS ------------------------------------------------------------
    await ctrl.refresh_status()
    status = ctrl.status
    print('\n>> STATUS (%d 필드)' % len(status))
    dump(status)

    missing = [k for k in parse.TEMP_MODS if k not in status]
    if missing:
        say(BAD, '온도 슬롯 %d/%d 결측: %s'
            % (len(missing), len(parse.TEMP_MODS), ' '.join(missing)),
            '그 자리는 %s 로 실린다 (자리=항목이라 건너뛰지 않는다)'
            % parse.FIELD_NC)
    else:
        say(OK, '온도 슬롯 %d개 전부 있다' % len(parse.TEMP_MODS))

    rails = [r for r in parse.VOLT_RAILS
             if r + '_V' not in status or r + '_I' not in status]
    if rails:
        say(BAD, '전원 레일 결측: %s' % ' '.join(rails))
    else:
        say(OK, '전원 레일 %d개의 _V/_I 쌍이 전부 있다' % len(parse.VOLT_RAILS))

    say(OK if parse.power_good(status) else BAD,
        'POWERGOOD = %s' % status.get('POWERGOOD', '(없음)'))
    # `POWERON` 이 성공 응답을 준 것과 전원이 실제로 올라온 것은 다르다 --
    # `POWER=3`(일부 모듈만 올라옴)이 그 사이의 상태다 (매뉴얼 p.47).
    pstate = parse.power_state(status)
    if pstate is None:
        say(WARN, 'POWER 를 보고하지 않는다 -- 전원 상태를 못 가른다')
    else:
        say(OK if pstate == parse.POWER_ON else BAD,
            'POWER = %d %s' % (pstate, parse.POWER_STATES.get(pstate, '?')))
    if 'OVERHEAT' not in status:
        say(WARN, 'OVERHEAT 를 보고하지 않는다')
    else:
        say(BAD if parse.overheating(status) else OK,
            'OVERHEAT = %s' % status['OVERHEAT'])

    # 이 컨트롤러가 색인 1(MK) 자리라고 보고 카드를 만들어 본다.
    cards = rawhdr.ctrl_telemetry_header([parse.telemetry_of(status), {}])
    print('\n   헤더에 이렇게 실린다:')
    comments = {k: c for k, _t, _w, c in rawcards.CARDS}
    for key in ('C1_TEMP', 'C1_VOLT', 'C1_CURR'):
        value = str(cards[key])
        print('     %-8s= %r' % (key, value))
        # **폭 판정은 실제 카드 조립기에 물어본다.**  규격 5.0절(v1.6)의 규범은
        # "comment 를 먼저 자르고 값은 마지막" 인데, 어느 단계에 걸리는지는
        # comment 길이에 달려 있다 -- 여기서 문턱을 다시 계산하면 조립기와
        # 갈라진다.  카드를 실제로 만들어 보고 무엇이 남았나를 본다.
        comment = comments[key]
        card = fitswrite.card_image(key, value, comment)
        if value not in card:
            say(BAD, '%s 의 **값이 잘려서** 실린다 -- 자리 나열 카드라 뒤 '
                     '항목이 통째로 사라진다 (규격 5.0절 · 5.6.1절)' % key,
                '값 %d자 -- comment 를 다 지워도 안 들어간다' % len(value))
        elif not card.rstrip().endswith(comment):
            say(WARN, '%s 가 견본 폭(51자)을 넘어 **comment 가 줄어** 실린다 '
                      '(규격 5.0절 -- 값은 온전하다)' % key,
                '값 %d자' % len(value))

    # **자리마다 무엇인지 눈으로 대조할 수 있게 이름표를 붙여 준다.**  카드에는
    # 이름표가 없고(자리 = 항목, 규격 5.6.1절) 값만 나열되므로, 실기 첫 실행에서
    # "이 자리가 정말 그 모듈인가" 를 확인할 수 있는 자리는 여기뿐이다.
    # 순서가 하나만 밀려도 값은 그럴듯하고 아무 경고도 안 뜬다.
    print('\n   자리 표 (규격 5.6.1절) -- 값이 그 모듈의 것인지 대조할 것:')
    # 구분자는 파이프다 (규격 5.6.1절, v1.6) -- 공백으로 쪼개면 열 자리가
    # 통째로 1번 자리에 들어간다.
    temps = str(cards['C1_TEMP']).strip().split('|')
    for i, label in enumerate(rawhdr.TEMP_MOD_LABELS):
        got = temps[i] if i < len(temps) else '(없음)'
        print('     %2d  %-14s %s' % (i + 1, label, got))
    if len(temps) != len(rawhdr.TEMP_MOD_LABELS):
        say(BAD, 'C1_TEMP 가 %d자리다 -- 규격 5.6.1절은 %d자리다'
            % (len(temps), len(rawhdr.TEMP_MOD_LABELS)),
            '자리 수 자체가 모듈 구성을 뜻한다 -- 규격부터 확인할 것')
    print('     레일  %s' % ' · '.join(parse.VOLT_RAILS))

    # -- 응답 자체의 건강 필드 (P-g) --------------------------------------
    # `VALID`/`COUNT`/`LOG` 는 **실기 보고 여부가 미확인**이었다 (PROVISIONAL).
    # D4(`VALID=0` -> 헤더 NC)와 F2(보고 없는 필드는 이상으로 세지 않는다)가
    # 둘 다 이 세 값의 실물에 달려 있으므로 여기서 눈으로 확인한다.
    valid = parse.status_valid(status)
    if valid is None:
        say(WARN, 'VALID 를 보고하지 않는다 -- D4(무효 응답을 헤더 NC 로)가 '
                  '작동하지 않는다.  값은 그대로 실린다(F2)')
    else:
        say(OK if valid else BAD, 'VALID = %s' % status.get('VALID'),
            '' if valid else 'D4 -- 이 응답의 Cn_* 는 NC 로 실린다')
    count = parse.status_count(status)
    if count is None:
        say(WARN, 'COUNT 를 보고하지 않는다 -- 기록의 fresh 열이 NC 가 된다 '
                  '(같은 블록을 다시 읽었는지 못 가른다)')
    else:
        say(OK, 'COUNT = %d  (두 질의 사이에 안 변하면 같은 블록이다)' % count)
    log_n = parse.log_count(status)
    if log_n is None:
        say(WARN, 'LOG 를 보고하지 않는다 -- 감시 기록의 log_n 열이 NC 가 된다')
    else:
        say(OK, 'LOG = %d  (FETCHLOG 는 쓰지 않는다 -- 이 값만 기록한다)'
            % log_n,
            'P-a/P-b/P-c/P-d: 드레인 승격은 사람이 한 번 보고 판단한다')

    # -- 전원 레일 정상 범위 (매뉴얼 p.41) --------------------------------
    rail_bad = parse.rail_problems(status, acfg.rail_limits)
    if rail_bad:
        say(BAD, '전원 레일이 정상 범위 밖이다 -- %s' % ' / '.join(rail_bad),
            '기본값은 매뉴얼 p.41 이고 전원 보드 저항으로 정해진다(p.42) -- '
            '유닛이 다르면 [archon.rails] 로 덮을 것')
    else:
        say(OK, '전원 레일 %d개가 정상 범위 안이다 (매뉴얼 p.41)'
            % len(parse.VOLT_RAILS))

    # -- 층 2 -- 바이어스 채널 (ACF 이름표 x STATUS 실측) ------------------
    # ⚠️ 이름표는 **ACF**, 값은 **STATUS** 다.  두 dict 의 키 문자열이 같아서
    #    (지령값 vs 실측값) 섞으면 그럴듯한 거짓말이 나온다.
    if not ctrl.config:
        acf_path = acfg.acf.get(ctrl.tag, '')
        if acf_path:
            try:
                ctrl.parse_acf(acf_path)        # 파일만 읽는다 -- 왕복 없음
            except ArchonError as exc:
                say(WARN, '바이어스 이름표를 못 읽었다 (%s)' % exc)
    channels = parse.bias_channels(ctrl.config)
    if not channels:
        say(WARN, 'ACF 에서 이름표 붙은 바이어스 채널을 못 찾았다 -- '
                  '--acf 나 [archon] acf_%s 를 주면 층 2 를 대조한다'
                  % ctrl.tag.lower())
    else:
        print('\n   바이어스 %d채널 (이름표는 ACF, 값은 STATUS -- 단위 V / mA):'
              % len(channels))
        for label, volt, curr in parse.bias_readings(status, channels):
            print('     %-12s %10s V   %10s mA'
                  % (label, _num(volt, 3), _num(curr, 3)))
        missing = [label for label, v, _i in
                   parse.bias_readings(status, channels)
                   if not isinstance(v, float)]
        if missing:
            say(BAD, '바이어스 %d채널을 STATUS 가 보고하지 않는다: %s'
                % (len(missing), ' '.join(missing)),
                'ACF 이름표와 모듈 형이 맞는지 볼 것 (LV(X)Bias 는 LVLC/LVHC, '
                'HV(X)Bias 는 HVLC/HVHC 만 낸다 -- 매뉴얼 p.48)')
        else:
            say(OK, '바이어스 %d채널의 V/I 를 전부 읽었다' % len(channels))
        pstate = parse.power_state(status)
        if pstate is not None and pstate != parse.POWER_ON:
            say(WARN, 'POWER=%d 라 바이어스가 ~0 V 로 나온다 (매뉴얼 p.77) -- '
                      '위 값을 고장으로 읽지 말 것' % pstate)

    # -- FRAME -------------------------------------------------------------
    fields = await ctrl.query('FRAME', timeout=5.0)
    print('\n>> FRAME (%d 필드)' % len(fields))
    dump(fields, per_line=4)
    fs = parse.newest(fields)
    print('\n   최신 프레임: %d (buf %d, base 0x%08X)'
          % (fs.frame, fs.buf + 1, fs.base))
    print('   기하 %d x %d, samplemode=%d -> 데이터 %d B (%.1f MiB)'
          % (fs.width, fs.height, fs.samplemode, fs.data_bytes,
             fs.data_bytes / (1 << 20)))

    if fs.frame < 0:
        say(WARN, '완료된 프레임이 아직 없다 (첫 전원 투입 뒤 정상)',
            'prev < 0 경로를 타므로 첫 프레임 번호가 1 이어도 받는다')
    if fs.width == 0:
        say(WARN, '기하를 보고하지 않았다 -- ACF 적용 전이면 정상이다')
    elif fs.data_bytes == acfg.frame_bytes:
        say(OK, '기하가 선언과 일치 (%d x %d)' % (acfg.naxis1, acfg.naxis2))
    else:
        say(BAD, '기하 불일치 -- 실제 %d B vs 선언 %d B'
            % (fs.data_bytes, acfg.frame_bytes),
            'ACF 기하와 [archon] naxis1/naxis2 를 맞출 것.  이대로면 본편이 '
            'fetch 앞에서 거부한다')
    if fs.samplemode:
        say(BAD, 'samplemode=1 (32bit 표본) -- 바이트 수가 정확히 2배가 된다')

    if any(k.endswith('LINES') for k in fields):
        say(OK, 'BUFnLINES(라인 진행)가 있다 -- PCTREAD 를 보고값으로 낸다')
    else:
        say(BAD, 'BUFnLINES 가 없다 -- 진행률 산출 방법을 다시 정해야 한다')
    return status


# ---------------------------------------------------------------------------
# 2단계 -- ACF 대조 (읽기 전용)
# ---------------------------------------------------------------------------

async def stage_acf(ctrl: ArchonController, acf: str, acfg) -> None:  # noqa: ANN001
    block('2단계  ACF 대조 -- 파라미터 슬롯이 컨트롤러 메모리와 맞나')

    ctrl.parse_acf(acf)
    say(OK, "ACF %d줄 파싱 -- '%s'" % (len(ctrl.config), acf))

    slots = (acfg.param_intms_slot, acfg.param_exposures_slot)
    names = (acfg.param_intms_name, acfg.param_exposures_name)
    for slot, name in zip(slots, names):
        key = slot.upper().replace(chr(92), '/')
        line = ctrl.configline.get(key)
        if line is None:
            say(BAD, "ACF 에 설정 줄 '%s' 이 없다" % slot,
                '[archon] param_*_slot 을 이 ACF 에 맞춰야 한다')
            continue
        text = ctrl.config[key]
        mark = OK if name in text else BAD
        say(mark, "%s (줄 %04X) = %r" % (slot, line, text),
            '' if name in text else "'%s' 가 이 줄에 없다 -- "
            '[archon] param_*_name 을 확인할 것' % name)

    # **`RCONFIG` 로 컨트롤러 메모리와 대조한다.**  세 결과를 갈라야 한다 --
    # ① 비어 있음(설정을 아직 안 올렸다) ② 다름(줄 번호가 어긋났다) ③ 같음.
    # ①을 "실패" 로 뭉개면 첫 실행에서 헛경보가 뜬다(전원을 켜기 전에는 설정이
    # 없는 것이 정상이다).  ②는 진짜 문제다 -- 그대로 두면 `set_config` 가
    # **엉뚱한 줄을 고쳐** 노출 시간이 조용히 안 바뀐다.
    for slot in slots:
        key = slot.upper().replace(chr(92), '/')
        line = ctrl.configline.get(key)
        if line is None:
            continue
        got = (await ctrl.cmd('RCONFIG%04X' % line, timeout=5.0)
               ).decode('ascii', 'replace').strip()
        if not got:
            say(WARN, '컨트롤러의 설정 줄 %04X 가 비어 있다 -- 아직 ACF 를 '
                      '올리지 않은 상태다' % line,
                '3단계(APPLYALL)를 거치면 맞는다.  --no-apply-acf 로 돌릴 '
                '생각이면 먼저 같은 ACF 를 올려 둘 것')
        elif got.upper().startswith(key + '='):
            say(OK, '설정 줄 %04X 대조 통과 -- %r' % (line, got[:40]))
        else:
            say(BAD, '설정 줄 %04X 가 %s 가 아니다 -- 받은 것 %r'
                % (line, key, got[:40]),
                '파일의 줄 번호가 컨트롤러 메모리와 다르다.  이대로 '
                'set_config 를 부르면 엉뚱한 줄을 고쳐 노출 시간이 조용히 '
                '안 바뀐다 -- apply_acf=true 로 두거나 같은 ACF 를 쓸 것')


# ---------------------------------------------------------------------------
# 3단계 -- 프레임 1장 (전원 ON)
# ---------------------------------------------------------------------------

async def stage_frame(ctrl: ArchonController, acfg, args) -> None:  # noqa: ANN001
    block('3단계  프레임 1장  ⚠️ 전원을 켜고 CCD 를 읽어낸다')

    if args.acf and args.apply_acf:
        t0 = time.monotonic()
        await ctrl.apply_acf(args.acf)
        say(OK, 'ACF 적용 (APPLYALL) %.1f초' % (time.monotonic() - t0))
    elif args.acf:
        ctrl.parse_acf(args.acf)
        ctrl.acf_applied = True
        say(WARN, 'ACF 적용을 건너뛴다 (--no-apply-acf) -- 이미 적용된 설정을 쓴다')

    try:
        t0 = time.monotonic()
        await ctrl.power_on(wait=args.poweron_wait)
        say(OK, 'POWERON + flush 대기 %.1f초' % (time.monotonic() - t0))

        # 셔터를 열지 않는다 -- 첫 확인은 암전 프레임이 안전하다.
        await ctrl.set_trigger_forced(True)
        say(OK, 'TRIGOUTFORCE=1 (셔터/광원 트리거 고정 -- 열지 않는다)')

        t0 = time.monotonic()
        ticket = await ctrl.trigger(args.expose)
        samples: list[tuple[float, int]] = []
        async for pct in ctrl.wait_frame(ticket, poll=args.poll):
            samples.append((time.monotonic() - t0, pct))
            print('   진행 %3d%%  (%.1f초)' % (pct, samples[-1][0]))
        elapsed = time.monotonic() - t0
        fs = ticket.ready
        say(OK, '프레임 %d 완료 -- 노출 지시부터 %.2f초 (IntMS=%d)'
            % (fs.frame, elapsed, args.expose),
            '진행률 보고 %d회.  [timing] 과 25초 Wrote 창의 근거가 이 값이다'
            % len(samples))
        if not samples:
            say(WARN, '진행률이 한 번도 안 나왔다',
                '독출이 폴링 간격(%.2f초)보다 빨랐거나 BUFnLINES 가 안 움직인다'
                % args.poll)

        if fs.data_bytes != acfg.frame_bytes:
            say(BAD, '기하 불일치로 fetch 하지 않는다 -- 실제 %d B vs 선언 %d B'
                % (fs.data_bytes, acfg.frame_bytes))
            return

        # **어느 쪽으로 돌았는지 먼저 찍는다** -- 두 실행의 로그를 나중에
        # 비교할 때 이 줄이 없으면 어느 것이 어느 쪽인지 알 수 없다.
        say(OK, 'lock_buffer = %s%s'
            % (acfg.lock_buffer,
               '  (--lock/--no-lock 로 지정)' if args.lock_buffer is not None
               else '  (ini 값)'))
        t0 = time.monotonic()
        raw = await ctrl.fetch(fs, acfg.frame_bytes)
        dt = max(time.monotonic() - t0, 1e-6)
        say(OK, 'FETCH %.1f MiB, %.2f초 (%.1f MiB/s)  [lock=%s]'
            % (len(raw) / (1 << 20), dt, len(raw) / (1 << 20) / dt,
               acfg.lock_buffer))

        if not args.write:
            say(WARN, 'FITS 는 쓰지 않았다 (--write 를 주면 쓴다)')
            return
        _write_probe_fits(raw, fs, ctrl, acfg, args)
    finally:
        await ctrl.power_off()
        say(OK, 'POWEROFF')


def _write_probe_fits(raw, fs, ctrl, acfg, args) -> None:  # noqa: ANN001
    """규격 5장 헤더를 **본편과 같은 경로로** 만들어 파일 1장을 쓴다.

    TC 중계 카드는 전부 `'NC'` 다 (이 도구는 TCS·AUX 에 붙지 않는다).  즉
    확인할 수 있는 것은 **기하 · 구조 카드 · 컨트롤러 유래 카드 · 정렬**이고,
    관측 카드의 실값은 본편에서 본다.
    """
    from ics_sim import rawcards

    telem = {k: 'NC' for k in rawcards.RELAY_CARDS}
    stem = 'probe.%s.%s' % (time.strftime('%Y%m%dT%H%M%S', time.gmtime()),
                            ctrl.tag)
    cards = rawhdr.spec_cards(
        ctrltag=ctrl.tag, site_code='KMTK',
        backend_name='archon', ics_build=_build_id(),
        ctrl_info={'units': (
            {**parse.unit_identity(ctrl.system),
             **({'cfg': os.path.splitext(os.path.basename(ctrl.acf_path))[0]}
                if ctrl.acf_path else {})}, {})},
        ctrl_telem=[parse.telemetry_of(ctrl.status), {}],
        sensors={},                      # 원천이 없다 -- sentinel 경로 확인용
        cfg_site=None, cfg_camera=None, cfg_ctrl=None, rdmode='',
        telem_cards=telem,
        date_obs=time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()) + '.000',
        exptime=args.expose / 1000.0, ledflash_ms=0,
        imgtype='DARK' if args.expose else 'BIAS', objname='PROBE',
        projid='ENG', observer='probe',
        # probe 는 카운터를 쓰지 않으므로 `EXPID` 도 같은 stem 이다
        # (충돌 판별이 성립하지 않는 진단 산출물이다).
        filename=stem, expid=stem)

    path = os.path.join(args.out, stem + '.fits')
    t0 = time.monotonic()
    rate = fitswrite.write_frame(path, cards, raw,
                                 naxis1=acfg.naxis1, naxis2=acfg.naxis2)
    say(OK, 'FITS 저장 %s (%.2f초, %d KB/sec)'
        % (path, time.monotonic() - t0, rate))

    size = os.path.getsize(path)
    if size % 2880:
        say(BAD, '파일이 2880B 배수가 아니다 (%d B)' % size)
    else:
        say(OK, '파일 %d B = 2880 x %d' % (size, size // 2880))
    try:
        from astropy.io import fits
    except ImportError:
        say(WARN, 'astropy 가 없어 읽기 확인을 건너뛴다')
        return
    with fits.open(path) as hdul:
        h = hdul[0].header
        say(OK, 'astropy 로 열린다 -- NAXIS %dx%d, BITPIX %d, BZERO %s'
            % (h['NAXIS1'], h['NAXIS2'], h['BITPIX'], h.get('BZERO')),
            'converter 가 처음 하는 일이 이것이다')
        data = hdul[0].data
        say(OK, '픽셀 통계: min %d  max %d  평균 %.1f'
            % (data.min(), data.max(), float(data.mean())),
            '4장 배치(좌우 chip · overscan)를 눈으로 확인할 자료다')


def _build_id() -> str:
    import ics_archon
    return ics_archon.build_id()


# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='probe_archon',
        description='실기 첫 실행 확인 -- 미검증 3자리를 컨트롤러에 직접 물어본다',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='1단계는 전원을 켜지 않는다.  --expose 를 주면 3단계(전원 ON)가 돈다.')
    p.add_argument('--host', required=True, help='컨트롤러 IP (예 10.0.0.13)')
    p.add_argument('--port', type=int, default=4242)
    p.add_argument('--tag', default='MK', choices=('MK', 'NT'),
                   help='이 컨트롤러가 담당하는 pair (헤더 색인 자리)')
    p.add_argument('-c', '--config', default='ics_archon.ini',
                   help='[archon] 기본값을 읽을 ini (기본: ics_archon.ini)')
    p.add_argument('--acf', help='2단계 -- 대조할 ACF 경로')
    p.add_argument('--no-apply-acf', dest='apply_acf', action='store_false',
                   help='3단계에서 APPLYALL 을 건너뛴다')
    p.add_argument('--expose', type=int, metavar='MS',
                   help='3단계 -- ⚠️ 전원을 켜고 이 노출시간[ms]으로 1프레임')
    p.add_argument('--write', action='store_true',
                   help='3단계에서 FITS 를 실제로 쓴다')
    p.add_argument('--out', default='./probe', help='FITS 저장 폴더')
    p.add_argument('--poll', type=float, default=0.2,
                   help='FRAME 폴링 간격 [s] (기본 0.2 -- 진행률을 촘촘히 본다)')
    # ⭐ **A/B 실험용 스위치** (2026-08-30).  labtest 는 2026-05-28 에 `LOCK` 을
    # 뺐는데 근거가 "remove to fetch debug" 한 줄뿐이라, **켜서 되는지**를
    # 실기에서 갈라야 한다.  ini 를 고쳐 가며 두 번 돌리는 대신 이 플래그로
    # 바꾼다 -- 두 실행의 차이가 이 한 곳뿐이어야 비교가 성립한다.
    p.add_argument('--lock', dest='lock_buffer', action='store_true',
                   default=None,
                   help='3단계 -- fetch 중 LOCKn 으로 버퍼를 잠근다 '
                        '(기본: ini 의 [archon] lock_buffer)')
    p.add_argument('--no-lock', dest='lock_buffer', action='store_false',
                   help='3단계 -- 잠그지 않는다 (labtest 와 같은 거동)')
    p.add_argument('--poweron-wait', type=float, default=12.0,
                   help='POWERON 뒤 flush 대기 [s]')
    p.set_defaults(apply_acf=True)
    return p


async def amain(args) -> int:  # noqa: ANN001
    acfg = acfg_mod.load(args.config)
    acfg.hosts[args.tag] = args.host
    acfg.port = args.port
    acfg.frame_poll = args.poll
    acfg.progress_step = 1               # 촘촘히 본다 (거동 확인이 목적)
    if args.lock_buffer is not None:     # --lock / --no-lock 이 ini 를 이긴다
        acfg.lock_buffer = args.lock_buffer
    if args.acf:
        # **`--acf` 가 ini 를 이긴다.**  이렇게 해 두면 1단계의 바이어스 채널
        # 표(층 2)도 그 ACF 의 이름표를 쓴다 -- 안 넘기면 `--acf` 를 주고도
        # 1단계가 "이름표를 못 찾았다" 를 낸다.
        acfg.acf[args.tag] = args.acf
    ctrl = ArchonController(args.tag, acfg)

    print('probe_archon -- %s (%s:%d), 선언 기하 %d x %d (%.1f MiB)'
          % (args.tag, args.host, args.port, acfg.naxis1, acfg.naxis2,
             acfg.frame_bytes / (1 << 20)))
    try:
        await stage_read_only(ctrl, acfg)
        if args.acf:
            await stage_acf(ctrl, args.acf, acfg)
        if args.expose is not None:
            os.makedirs(args.out, exist_ok=True)
            await stage_frame(ctrl, acfg, args)
        else:
            print('\n(--expose 를 주지 않았으므로 전원을 켜지 않았다)')
    except (ArchonError, TimeoutError, OSError) as exc:
        say(BAD, '중단 -- %s' % exc)
    finally:
        await ctrl.close()

    block('요약')
    bad = [l for m, l in _verdicts if m == BAD]
    warn = [l for m, l in _verdicts if m == WARN]
    print(' 확인 %d건 · 확인필요 %d건 · 문제 %d건'
          % (len(_verdicts), len(warn), len(bad)))
    for label in warn:
        print('   확인: %s' % label)
    for label in bad:
        print('   문제: %s' % label)
    print('=' * 74)
    return 1 if bad else 0


def main(argv=None) -> int:  # noqa: ANN001
    args = build_parser().parse_args(argv)
    try:
        return asyncio.run(amain(args))
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main())

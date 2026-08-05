#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STOP / ABORT -- 레거시 분기를 그대로 옮겼는지 확인한다.

근거는 `IC2.img` 의 ICS 소스 `KMTX\\PAP7KX.CMD:279-302` 다:

    CASE "STOP"                                  CASE "ABORT"
       IF ExpLoopFlag = 1 THEN                      IF GoFlag = 1 THEN
          PauseFlag=0 : ExpLoopFlag=0                  PauseFlag=0 : ExpLoopFlag=0
          SoftStop=1 : AbortHost=발신자                GoFlag=0 : AbortHost=발신자
       ELSE                                         ELSE
          ERROR: No integration in progress.           ERROR: No acquisition in progress.
                 Nothing to stop.                             Nothing to abort.

두 명령은 48GB 로그 전량에서 송수신 0건이라 **응답 형식의 실측 근거가 없다.**
그래서 여기서 검증하는 것은 (a) 거부 문자열이 레거시 그대로인가, (b) 수락
조건이 레거시 플래그와 같은 의미인가, (c) 중지 후에도 OBSAgent 가 IDLE 로
돌아올 수 있는가 세 가지다.  (c)가 특히 중요하다 -- 알리지 않고 끊으면
CamStatus 가 READOUT 에 갇혀 force_idle 타임아웃 → opause 로 간다(DevNote 3.3).
"""

from __future__ import annotations

from conftest import DARK_SCRIPT, drive, drive_at, make_config


# -- 노출 중이 아닐 때: 레거시와 같은 거부 -------------------------------

def test_stop_when_idle_is_refused():
    run = drive(['OBS>ICS stop'])
    msgs = run.find('STOP')
    assert msgs, 'STOP 에 응답이 없다'
    assert any('ERROR:' in m for m in msgs)
    assert any('No integration in progress. Nothing to stop.' in m
               for m in msgs), msgs


def test_abort_when_idle_is_refused():
    run = drive(['OBS>ICS abort'])
    msgs = run.find('ABORT')
    assert msgs, 'ABORT 에 응답이 없다'
    assert any('ERROR:' in m for m in msgs)
    assert any('No acquisition in progress. Nothing to abort.' in m
               for m in msgs), msgs


def test_refusals_go_back_to_the_sender():
    run = drive(['OBS>ICS abort'])
    assert run.to('OBS'), 'ABORT 거부가 요청자에게 가지 않았다'


# -- STOP: 적분만 끊고 나머지는 정상 -------------------------------------

def _stop_run():
    # 카운트다운이 한 번이라도 나온 뒤 = 확실히 적분 중인 시점에 STOP.
    return drive_at(DARK_SCRIPT, marker='Remaining=', inject='OBS>ICS stop')


def test_stop_is_accepted_while_integrating():
    run = _stop_run()
    assert any('DONE:' in m and 'STOP' in m for m in run.find('STOP')), \
        run.find('STOP')


def test_stop_still_completes_readout_and_save():
    """STOP 은 적분만 끊는다 -- readout 과 저장은 끝까지 간다."""
    run = _stop_run()
    assert run.count('EXPSTATUS=READOUT') >= 1, 'readout 으로 넘어가지 않았다'
    assert run.count('Acquisition Complete.', node='OBS') == 4
    assert run.count('Wrote LASTFILE=', node='OBS') == 4
    assert run.count('EXPSTATUS=IDLE') >= 1


def test_stop_shortens_the_countdown():
    """중지했으니 끝까지 센 노출보다 카운트다운이 적어야 한다."""
    stopped = _stop_run().count('Remaining=')
    full = drive(DARK_SCRIPT).count('Remaining=')
    assert stopped < full, f'stopped={stopped} full={full}'


def test_stop_keeps_the_wire_clean():
    assert _stop_run().violations == []


# -- ABORT: 전부 중지 -----------------------------------------------------

def _abort_run():
    return drive_at(DARK_SCRIPT, marker='Remaining=', inject='OBS>ICS abort')


def test_abort_is_accepted_while_exposing():
    run = _abort_run()
    assert any('DONE:' in m and 'ABORT' in m for m in run.find('ABORT')), \
        run.find('ABORT')


def test_abort_skips_readout_and_save():
    run = _abort_run()
    assert run.count('PCTREAD=') == 0, '중지했는데 readout 이 돌았다'
    assert run.count('Wrote LASTFILE=') == 0, '중지했는데 저장됐다'


def test_abort_still_reports_idle():
    """OBSAgent 가 READOUT 에 갇히지 않도록 종료를 알려야 한다."""
    run = _abort_run()
    assert run.count('EXPSTATUS=IDLE', node='OBS') >= 1, run.to('OBS')


def test_abort_keeps_the_wire_clean():
    assert _abort_run().violations == []


# -- 상태가 제자리로 돌아오는가 -------------------------------------------

def test_go_is_accepted_again_after_abort():
    """중지 뒤 노출을 다시 걸 수 있어야 한다.

    `GoFlag` 가 제대로 내려갔는지를 보는 것이다 -- 레거시도 ABORT 가 하는 일이
    사실상 `GoFlag = 0` 이었다.  안 내려가면 다음 GO 가
    `ERROR: Data acquisition already in progress!` 로 거부된다(5.4절).
    """
    run = drive_at(DARK_SCRIPT, marker='Remaining=',
                   inject=['OBS>ICS abort', 'OBS>ICS go'], settle=1.2)
    assert run.count('Data acquisition already in progress') == 0, \
        run.find('already in progress')
    # 두 번째 노출이 실제로 처음부터 다시 돌았어야 한다.
    assert run.count('EXPSTATUS=INITIALIZING') >= 2, run.find('EXPSTATUS=')

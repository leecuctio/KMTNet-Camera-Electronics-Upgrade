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
    """STOP 을 받아도 **그 프레임은 저장까지 끝까지 간다** (운영자 확정)."""
    run = _stop_run()
    assert run.count('EXPSTATUS=READOUT') >= 1, 'readout 으로 넘어가지 않았다'
    assert run.count('Acquisition Complete.', node='OBS') == 4
    assert run.count('Wrote LASTFILE=', node='OBS') == 4
    assert run.count('EXPSTATUS=IDLE') >= 1


def test_stop_does_not_shorten_the_integration():
    """⛔ **STOP 은 적분을 끊지 않는다** (운영자 확정 2026-09-04).

    ⚠️ **앞 결정을 뒤집은 자리다.**  종전에는 레거시 `SoftStop=1`
    (PAP7KX.CMD:279-290)을 그대로 옮겨 **카운트다운을 끊었다.**
    ⛔ 그런데 짧아진 적분이 헤더 `EXPTIME` 에는 **요청값 그대로** 실려
    (raw spec 5.4절) *"정상으로 보이는 오염 프레임"* 을 만든다.

    ⭐ 이제 갈림은 이렇다: **ABORT** 는 적분을 끊고 **버린다** · **STOP** 은
    적분을 그대로 두고 **저장까지 하고 다음을 안 건다**.  그래서 저장되는
    프레임은 언제나 온전한 노출이다.
    """
    stopped = _stop_run().count('Remaining=')
    full = drive(DARK_SCRIPT).count('Remaining=')
    assert stopped == full, (
        'STOP 이 카운트다운을 끊었다 -- stopped=%d full=%d' % (stopped, full))


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


# -- STOP 은 "다음 프레임을 안 건다" 다 -------------------------------------

def test_stop_ends_the_sequence_after_the_current_frame():
    """⭐ `GO n` 도중 STOP -> **그 프레임까지만 저장하고 멈춘다**.

    ⚠️ 종전 시험(`…does_not_shorten_the_following_frames`)은 *"뒤 프레임들이
    정상 카운트다운을 낸다"* 를 봤다 -- STOP 이 적분을 끊던 시절, 표시가 다음
    프레임으로 **새는** 것을 막는 시험이었다.  이제 뒤 프레임은 **아예 안
    돈다**(그것이 STOP 의 뜻이다).

    ⚠️ **`GO`(1장)에는 영향이 없다** -- 막을 "다음" 이 없다.
    """
    from conftest import drive_at, make_config
    cfg = make_config()
    # 마커는 **적분 중임이 확실한** 첫 카운트다운으로 잡는다 (구판 주석 유지).
    run = drive_at(['OBS>ICS projid eng', 'OBS>ICS dark stopped',
                    'OBS>ICS exp 30', 'OBS>ICS go 3'],
                   marker='Remaining=', inject='OBS>ICS stop',
                   cfg=cfg, settle=2.0, timeout=20.0)
    assert not run.find('Nothing to stop'), 'STOP 이 거부됐다 -- 마커가 이르다'
    # ⭐ 3장을 걸었지만 STOP 을 맞은 첫 프레임에서 멈춘다 -- 획득 완료 4회.
    acq = run.count('Acquisition Complete.')
    assert acq == 4, '3장이 다 돌았거나(%d) 프레임이 잘렸다' % acq
    assert run.count('Wrote LASTFILE=', node='OBS') == 4
    assert run.count('EXPSTATUS=IDLE') >= 1
    assert run.violations == []


def test_abort_does_not_destroy_a_previous_frames_pending_save(tmp_path):
    """ABORT 는 **진행 중 노출만** 버린다 -- 앞 프레임의 미완료 저장은 지키다.

    구판은 `_writers` 전체를 취소해서, `GO n` 파이프라인에서 프레임 k 초반에
    ABORT 가 오면 이미 `Acquisition Complete.` 까지 발신한 프레임 k-1 의
    파일이 **기록 전에 사라졌다** (저장 태스크는 `write_delay+skew` 동안
    잠들어 있다).  그 프레임의 `Wrote` 는 영영 안 나가고(OBSAgent 25초 창)
    번호는 이미 소비돼 디스크에 구멍만 남았다.
    """
    import os
    from conftest import drive_at, make_config
    cfg = make_config(paths__write_fits=True, paths__data_dir=str(tmp_path))
    # 프레임 1 의 저장이 아직 잠든 사이(프레임 2 의 개시 직후)에 ABORT --
    # 프레임 1 완료 통보가 'Image 1 of 2 complete.' 다 (emitter.image_complete)
    run = drive_at(['OBS>ICS projid eng', 'OBS>ICS bias two', 'OBS>ICS go 2'],
                   marker='Image 1 of 2 complete.', inject='OBS>ICS abort',
                   cfg=cfg, settle=2.5, timeout=20.0)
    written = sorted(p for p in os.listdir(tmp_path) if p.endswith('.fits'))
    assert len(written) == 2, (
        f'프레임 1 의 pair 가 남아야 한다 -- 실제 {written}')
    relays = [m for m in run.to('OBS') if 'Wrote LASTFILE=' in m]
    assert len(relays) == 4, f'프레임 1 의 Wrote 4회가 유실됐다: {len(relays)}'

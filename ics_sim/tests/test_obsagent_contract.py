#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OBSAgent 호환 규약 검증 -- 이 저장소에서 가장 중요한 테스트.

`ics_legacy_report.md` 8.0.1절의 규약은 OBSAgent 소스를 정독해 도출한 것일 뿐
**실행으로 검증된 적이 없었다.**  여기서 그 규약을 실제로 돌려 확인한다.

방법: `ics_sim/obsagent_model.py` 가 OBSAgent 의 CamStatus 상태머신
(commands.c 757~864 + main.c 650~708)을 그대로 재현한다.  시뮬의 발신 스트림을
그 모델에 먹여 상태가 규약대로 흐르는지 본다.  같은 모델을
`tools/scan_legacy_logs.py camstatus` 가 실측 로그 재생에도 쓰므로, 실측과
시뮬을 같은 자로 잰다.
"""

from __future__ import annotations

import pytest

from conftest import (DARK_SCRIPT, GON5_SCRIPT, OBJECT_SCRIPT, drive,
                      drive_at, make_config)
from ics_sim.obsagent_model import CamStatusReplay


def replay(run) -> CamStatusReplay:  # noqa: ANN001
    r = CamStatusReplay()
    for when, msg in run.timed:
        r.feed(msg, when)
    return r


# -- 상태 전이 -----------------------------------------------------------

def test_object_reaches_all_states(object_run):
    """셔터 노출은 PREP_I -> ... -> IDLE_3 을 빠짐없이 밟는다."""
    r = replay(object_run)
    seen = r.visited()
    for state in ('PREP_I', 'PREP_E', 'INT_1', 'INT_2', 'INT_3',
                  'CLOSING', 'READ_1', 'READ_2', 'READ_3',
                  'IDLE_1', 'IDLE_2', 'IDLE_3'):
        assert state in seen, f'{state} 를 거치지 않았다: {seen}'
    assert r.state == 'IDLE_3'


def test_dark_skips_int_2(dark_run):
    """DARK/BIAS 는 셔터를 열지 않아 INT_2 를 건너뛴다.

    실측에서도 그렇다 -- Shutter=Open 메시지 자체가 없기 때문이다
    (DevNote 3.2.1).  건너뛰어도 CLOSING 은 정상적으로 밟는다.
    """
    r = replay(dark_run)
    seen = r.visited()
    assert 'INT_2' not in seen
    assert 'INT_1' in seen and 'INT_3' in seen and 'CLOSING' in seen
    assert r.state == 'IDLE_3'


def test_no_backward_transitions(object_run, dark_run):
    """INT_3 -> INT_1 같은 역행이 없어야 한다.

    실측 전이 집계에서도 역행은 0건이다.  EXPSTATUS= 를 담은 메시지를 OBS 로
    과다 발신하면 여기서 깨진다 (DevNote 3.2.1 의 신규 설계 제약).
    """
    backward = {('INT_2', 'INT_1'), ('INT_3', 'INT_1'), ('INT_3', 'INT_2'),
                ('CLOSING', 'INT_1'), ('CLOSING', 'INT_2'), ('CLOSING', 'INT_3'),
                ('READ_1', 'INT_1'), ('IDLE_3', 'INT_1')}
    for run in (object_run, dark_run):
        r = replay(run)
        bad = backward & set(r.transitions)
        assert not bad, f'역행 전이 발생: {bad}'


# -- 개수 규약 -----------------------------------------------------------

def test_acquisition_complete_exactly_four(dark_run):
    """`Acquisition Complete.` (마침표 포함) 4회 -> IDLE_2."""
    assert dark_run.count('Acquisition Complete.', node='OBS') == 4
    r = replay(dark_run)
    assert r.count_acqcomp >= 4 or r.state == 'IDLE_3'
    assert 'IDLE_2' in r.visited()


def test_wrote_four_times_sets_fitssaved(dark_run):
    """`Wrote` 4회 -> FitsSaved=1.

    OBSAgent 가 세는 것은 CB 직송이 아니라 **ICS 가 OBS 로 중계한 것**이다.
    """
    assert dark_run.count('Wrote LASTFILE=', node='OBS') == 4
    assert replay(dark_run).fits_saved == 1


def test_fitsnum_parsing(dark_run):
    """`Wrote` 본문에서 "KMTN"+6 부터 15자를 잘라 FitsNum 으로 쓴다.

    파일명 KMTN<x>.<8자리>.<6자리>.fits 형식이 깨지면 표시가 망가진다.
    """
    import re
    r = replay(dark_run)
    assert re.fullmatch(r'\d{8}\.\d{6}', r.fits_num), \
        f'FitsNum 파싱 실패: {r.fits_num!r}'


def test_pctread_at_least_twice(dark_run):
    """PCTREAD= 가 2회 이상이어야 READ_3 에 도달한다."""
    assert dark_run.count('PCTREAD=', node='OBS') >= 2
    assert 'READ_3' in replay(dark_run).visited()


# -- 하드 타임아웃 창 (DevNote 3.3) --------------------------------------

@pytest.mark.parametrize('fixture_name', ['dark_run', 'object_run'])
def test_timeout_windows_not_violated(request, fixture_name):
    """OBSAgent 의 세 창을 침범하지 않는지.

    침범하면 실제 OBSAgent 가 스크립트 관측을 멈추거나(opause) 경고를 띄운다.
    """
    run = request.getfixturevalue(fixture_name)
    bad = replay(run).check_windows()
    assert bad == [], f'{fixture_name}: {bad}'


def test_config_self_check_flags_bad_timing():
    """설정이 창을 침범하면 기동 시 경고가 나와야 한다 (음성 테스트)."""
    cfg = make_config()
    cfg.timing.acq_to_idle = 5.0        # 허용 0.9초
    cfg.timing.ccd_skew = (0.0, 0.0, 0.0, 40.0)  # 허용 산포 1.8초
    warnings = cfg.validate()
    assert any('acq_to_idle' in w for w in warnings)
    assert any('ccd_skew' in w for w in warnings)


def test_short_acquisition_trips_opause_path():
    """`Acquisition Complete.` 가 4회에 못 미치면 모델이 위반을 잡아낸다.

    실제 OBSAgent 는 이 경우 1.8초 뒤 opause + ERROR 를 낸다.
    """
    cfg = make_config(behavior__inject=frozenset({'acq_short'}))
    run = drive(DARK_SCRIPT, cfg)
    # acq_short 주입은 아래 test 에서 별도로 다룬다 -- 여기서는 모델이 부족한
    # 개수를 실제로 위반으로 잡는지만 확인한다.
    r = CamStatusReplay()
    for when, msg in run.timed:
        if 'Acquisition Complete.' in msg and r.count_acqcomp >= 3:
            continue  # 4번째를 일부러 빠뜨린다
        r.feed(msg, when)
    assert any('4회' in b or 'Acquisition' in b for b in r.check_windows())


def test_missing_wrote_is_detected():
    """Wrote 가 4회에 못 미치면 FitsSaved 가 서지 않는다."""
    cfg = make_config(behavior__inject=frozenset({'wrote_drop'}))
    run = drive(DARK_SCRIPT, cfg, settle=1.0)
    assert run.count('Wrote LASTFILE=', node='OBS') == 3
    r = replay(run)
    assert r.fits_saved == 0
    assert any('Wrote' in b for b in r.check_windows())


# -- ExpNum 자동 질의 (DevNote 3.4) --------------------------------------

def test_expnum_query_answered():
    """OBSAgent 는 첫 PCTREAD= 를 받으면 스스로 `OBS>ICS ExpNum` 을 보낸다.

    응답의 Filename= 뒤 **정확히 15자**가 expinfo.strNextNum 이 되고, 그 값이
    관측자 화면과 /data/Logs/ObsStatus.txt 의 ExpNum 필드를 채운다.
    응답하지 않으면 카메라는 정상 동작하지만 표시가 갱신되지 않는다.
    """
    import re
    run = drive(['OBS>ICS ExpNum'], settle=0.1)
    replies = run.find('DONE: EXPNUM')
    assert replies, 'ExpNum 질의에 응답하지 않았다'
    m = re.search(r'Filename=(\S+)', replies[0])
    assert m and len(m.group(1)) == 15, \
        f'Filename= 값이 15자가 아니다: {m.group(1) if m else None!r}'
    assert re.fullmatch(r'\d{8}\.\d{6}', m.group(1))


def test_expnum_answers_next_frame_number():
    """readout 중 EXPNUM 질의에는 **다음** 노출 번호를 답해야 한다.

    OBSAgent 는 그 값을 `strNextNum` 에 담았다가 **다음 노출이 시작될 때**
    `strCurNum` 으로 승격해 관측자 화면의 `ExpNum` 으로 쓴다(DevNote 3.4).
    노출 N 의 readout 중에 N 을 답하면 화면이 노출마다 한 칸씩 밀린다.

    **실물 연동에서 드러난 결함이다 (2026-08-11).**  실제 OBSAgent 를 붙이자
    노출 2 가 도는 내내 `ExpNum=...000001` 이 표시됐고 그 노출이 저장한 파일은
    `...000002` 였다.  레거시 실측(CTIO isis.20250401.log)은 readout 중 응답이
    `Filename=...010459` / 그 노출의 Wrote 가 `...010458` 로 **N+1** 이다.
    질의에 답하기만 하면 되는 줄 알았던 3.4 규약에 값의 규약이 빠져 있었다.

    `test_expnum_query_answered` 는 형식(15자)만, 아래
    `test_expnum_advances_between_exposures` 는 파일명 연속성만 보므로
    둘 다 이 결함을 놓쳤다.
    """
    import re
    run = drive_at(DARK_SCRIPT, marker='PCTREAD=6', inject='OBS>ICS ExpNum')

    replies = run.find('DONE: EXPNUM')
    assert replies, 'readout 중 ExpNum 질의에 응답하지 않았다'
    answered = re.search(r'Filename=(\d{8})\.(\d{6})', replies[-1])
    assert answered, f'Filename= 형식이 아니다: {replies[-1]!r}'

    wrote = [m for m in (re.search(r'KMTN\w\.(\d{8})\.(\d{6})\.fits', line)
                         for line in run.find('Wrote LASTFILE=')) if m]
    assert wrote, '이 노출의 Wrote 를 찾지 못했다'

    this_frame = int(wrote[0].group(2))
    assert all(int(m.group(2)) == this_frame for m in wrote), \
        '한 노출의 Wrote 4개가 같은 번호가 아니다'
    assert int(answered.group(2)) == this_frame + 1, (
        f'EXPNUM 응답이 {answered.group(2)} 인데 이 노출의 파일은 '
        f'{this_frame:06d} 다 -- 다음 번호({this_frame + 1:06d})를 답해야 한다')


def test_expnum_outside_exposure_does_not_skip():
    """노출 중이 아닐 때는 카운터를 그대로 답한다 -- 두 칸 밀면 안 된다.

    `advance()` 가 이미 돌아 `expnum` 이 다음 노출 번호를 가리키는 상태이므로,
    거기에 또 더하면 관측자가 보는 번호가 실제보다 하나 앞선다.
    """
    import re
    # 노출 전에 한 번, 노출이 끝난 뒤(EXPSTATUS=IDLE)에 한 번 묻는다.
    # drive() 로는 스크립트가 20ms 간격으로 한꺼번에 들어가 뒤쪽 질의가 노출
    # **도중**에 도착해 버린다 -- 끝난 뒤를 보려면 발신을 마커로 삼아야 한다.
    run = drive_at(['OBS>ICS ExpNum'] + DARK_SCRIPT,
                   marker='DONE: EXPSTATUS=IDLE', inject='OBS>ICS ExpNum')
    replies = run.find('DONE: EXPNUM')
    assert len(replies) >= 2, f'EXPNUM 응답이 2개 미만이다: {replies}'

    before = int(re.search(r'Filename=\d{8}\.(\d{6})', replies[0]).group(1))
    after = int(re.search(r'Filename=\d{8}\.(\d{6})', replies[-1]).group(1))
    wrote = re.search(r'KMTN\w\.\d{8}\.(\d{6})\.fits',
                      run.find('Wrote LASTFILE=')[0])
    frame = int(wrote.group(1))

    assert before == frame, \
        f'노출 전 응답 {before:06d} 가 그 노출이 쓴 번호 {frame:06d} 와 다르다'
    assert after == frame + 1, \
        f'노출 후 응답이 {after:06d} 다 -- 다음 번호 {frame + 1:06d} 여야 한다'


def test_expnum_advances_between_exposures(gon5_run):
    """프레임마다 일련번호가 1씩 올라간다.

    OBSAgent 는 readout 중 ExpNum 으로 받은 값을 **다음** 노출의 ExpNum 으로
    쓰므로, 프레임 사이에 번호가 반드시 전진해야 한다.
    """
    import re
    nums = sorted({m.group(1) for m in
                   (re.search(r'KMTN\w\.(\d{8}\.\d{6})\.fits', line)
                    for line in gon5_run.find('Wrote LASTFILE=')) if m})
    assert len(nums) == 5, f'프레임 5개의 일련번호가 아니다: {nums}'
    seq = [int(n.split('.')[1]) for n in nums]
    assert seq == list(range(seq[0], seq[0] + 5)), f'번호가 연속이 아니다: {seq}'


# -- 스크립트 관측 응답 체크 (DevNote 3.5) -------------------------------

def test_go_reaches_prep_state_promptly(dark_run):
    """GO 의 응답 확인은 CamStatus 가 PREP_I~INT_3 에 드는지로 판정된다."""
    r = CamStatusReplay()
    reached = False
    for when, msg in dark_run.timed:
        r.feed(msg, when)
        if r.state in ('PREP_I', 'PREP_E', 'INT_1', 'INT_2', 'INT_3'):
            reached = True
            break
    assert reached


@pytest.mark.parametrize('command, needle', [
    ('OBS>ICS projid obs', 'PROJID'),
    ('OBS>ICS object BLG11', 'OBJECT'),
    ('OBS>ICS dark begin', 'DARK'),
    ('OBS>ICS bias bias', 'BIAS'),
    ('OBS>ICS flat flat', 'FLAT'),
    ('OBS>ICS sky sky', 'SKY'),
    ('OBS>ICS domeflat df', 'DOMEFLAT'),
    ('OBS>ICS exp 30', 'EXP'),
    ('OBS>ICS observer smc', 'OBSERVER'),
    ('OBS>ICS ledflash 1', 'LEDFLASH'),
    ('OBS>ICS acqstatus', 'ACQSTATUS'),
    ('OBS>ICS filename', 'FILENAME'),
    ('OBS>ICS status', ' STATUS'),
    ('OBS>K.IC dmawait 500', 'DMAWAIT'),
    ('OBS>K.IC datasource ctc', 'DATASOURCE'),
])
def test_script_response_check_strings(command, needle):
    """`.osc` 스크립트 실행 중 응답 확인에 쓰이는 문자열이 본문에 있어야 한다.

    `" STATUS"` 는 **앞 공백이 필요하다** (commands.c 987).
    """
    run = drive([command], settle=0.1)
    replies = run.to(command.split('>')[0])
    assert any(needle in m for m in replies), \
        f'{command} 응답에 {needle!r} 이 없다: {replies}'


# -- 수신 노드 (DevNote 3.1) ---------------------------------------------

@pytest.mark.parametrize('command, expect', [
    ('OBS>K.IC STATUS', 'Inst=KMTNk'),
    ('OBS>M.IC STATUS', 'Inst=KMTNm'),
    ('OBS>T.IC STATUS', 'Inst=KMTNt'),
    ('OBS>N.IC STATUS', 'Inst=KMTNn'),
    ('OBS>K.IC DMAWAIT 500', 'DMAWaitTime=500'),
])
def test_per_node_commands_are_received(command, expect):
    """kstatus/dmawait/datasource 는 K.IC 등 **개별 노드 주소**로 온다.

    ICS 하나로만 등록하면 이 명령들은 도달조차 하지 않는다.  기존 8.0.1절이
    발신 쪽 비대칭만 다루고 수신 쪽을 빠뜨린 지점이다.
    """
    run = drive([command], settle=0.1)
    assert any(expect in m for m in run.to('OBS')), \
        f'{command} 에 응답하지 않았다'


def test_startup_registers_all_nine_nodes():
    """기동 시 9개 노드 ID **전부**로 PING 을 보내야 한다.

    IMPv2 에는 등록 API 가 없고, 노드가 자기 이름으로 메시지를 보내면 XIS 가
    "노드ID -> (IP,port)" 를 기억하는 것이 전부다.  ICS 이름으로만 보내면
    K.IC 앞으로 오는 kstatus/dmawait/datasource 가 도달하지 않는다
    (DevNote 3.1.1).
    """
    run = drive([], settle=0.1)
    pings = [m for m in run.sent if m.endswith(' PING')]
    srcs = [m.split('>', 1)[0] for m in pings]
    assert srcs == ['ICS', 'K.IC', 'M.IC', 'T.IC', 'N.IC',
                    'K.CB', 'M.CB', 'T.CB', 'N.CB'], srcs
    assert all(m.split('>', 1)[1].startswith('AL ') for m in pings)


@pytest.mark.parametrize('mode', ['legacy', 'merged'])
def test_registration_ignores_emit_node_mode(mode):
    """등록 PING 은 emit_node_mode 를 따르지 않는다.

    merged 는 **발신 이름**만 ICS 로 통일하는 옵션이고, 수신은 언제나 9개 ID
    전부여야 한다.  등록까지 merged 로 하면 개별 IC 앞 명령이 영영 안 온다.
    """
    cfg = make_config(node__emit_node_mode=mode)
    run = drive([], cfg, settle=0.1)
    srcs = [m.split('>', 1)[0] for m in run.sent if m.endswith(' PING')]
    assert len(srcs) == 9, f'{mode} 모드에서 등록 PING 이 {len(srcs)}개'
    assert 'K.IC' in srcs and 'N.CB' in srcs


def test_broadcast_ping_answered_by_all_nine_nodes():
    """`XIS>AL PING` 에 9개 노드 전부로 PONG 을 보내야 한다.

    XIS 는 재시작할 때 `handShake()` 로 `XIS>AL PING` 을 뿌리고 돌아오는 PONG
    으로 클라이언트 테이블을 다시 채운다(XIS 소스 `interfaces.c`).
    **이것이 XIS 재시작 후 재등록되는 유일한 경로다.**  레거시는 노드마다
    프로세스가 따로라 각자 답했지만, 통합 프로그램인 우리가 하나만 답하면
    `ICS` 만 살아나고 나머지 8개는 죽는다 (DevNote 3.1.1).
    """
    run = drive(['XIS>AL PING'], settle=0.2)
    startup = 9  # 기동 시 보내는 등록 PING
    pongs = [m for m in run.sent[startup:] if m.endswith(' PONG')]
    srcs = [m.split('>', 1)[0] for m in pongs]
    assert srcs == ['ICS', 'K.IC', 'M.IC', 'T.IC', 'N.IC',
                    'K.CB', 'M.CB', 'T.CB', 'N.CB'], srcs
    assert all(m.split('>', 1)[1].startswith('XIS ') for m in pongs)


def test_directed_ping_answered_by_that_node_only():
    """지목된 PING 에는 그 노드로만 답한다."""
    run = drive(['OBS>K.IC PING'], settle=0.2)
    pongs = [m for m in run.sent[9:] if m.endswith(' PONG')]
    assert pongs == ['K.IC>OBS PONG'], pongs


def test_register_all_nodes_false_only_registers_ics():
    """스위치를 끄면 ICS 만 등록된다 (음성 테스트).

    XIS 가 같은 (IP,port) 의 다중 등록을 거부하는 것으로 밝혀졌을 때를 대비한
    탈출구이지만, 그 상태로는 개별 IC 명령을 받을 수 없다는 점을 확인해 둔다.
    """
    cfg = make_config(transport__register_all_nodes=False)
    run = drive([], cfg, settle=0.1)
    srcs = [m.split('>', 1)[0] for m in run.sent if m.endswith(' PING')]
    assert srcs == ['ICS']


def test_datasource_broadcast_to_all_ics():
    """OBSAgent 는 datasource 를 4개 IC 에 각각 보낸다."""
    script = [f'OBS>{n} DATASOURCE ctc' for n in
              ('K.IC', 'M.IC', 'T.IC', 'N.IC')]
    run = drive(script, settle=0.2)
    assert run.count('DataSource=CT_CORRECTION', node='OBS') == 4


@pytest.mark.parametrize('mode', ['legacy', 'merged'])
def test_contract_holds_in_both_node_modes(mode):
    """발신 이름을 전부 ICS 로 바꿔도 CamStatus 필터를 통과한다."""
    cfg = make_config(node__emit_node_mode=mode)
    run = drive(DARK_SCRIPT, cfg, settle=1.0)
    r = replay(run)
    assert r.state == 'IDLE_3'
    assert r.fits_saved == 1
    assert run.count('Acquisition Complete.', node='OBS') == 4


# -- GO n 다중 노출 (DevNote 6.1) ----------------------------------------

def test_go_n_emits_image_progress(gon5_run):
    """중간 프레임은 `STATUS: Image n of N complete.`, 마지막만 `DONE:`.

    실측에서 `Image 5 of 5` 가 0건인 것이 근거다.
    """
    for i in range(1, 5):
        hits = gon5_run.find(f'Image {i} of 5 complete.')
        assert len(hits) == 1, f'Image {i} of 5 가 {len(hits)}회'
        assert hits[0].startswith('ICS>OBS STATUS:')
    assert not gon5_run.find('Image 5 of 5')
    assert gon5_run.count('DONE: EXPSTATUS=IDLE', node='OBS') == 1


def test_go_n_wrote_counts_survive_pipelining(gon5_run):
    """프레임 N 의 Wrote 4개가 프레임 N+1 의 PCTREAD= 전에 들어와야 한다.

    PCTREAD= 가 count_wrote 를 0 으로 리셋하므로, 늦으면 FitsSaved 가 영영
    서지 않는다.  레거시도 이 순서로 파이프라인했다.
    """
    r = replay(gon5_run)
    assert r.fits_saved == 1, 'GO 5 종료 시 FitsSaved 가 서지 않았다'
    assert gon5_run.count('Wrote LASTFILE=', node='OBS') == 5 * 4


def test_go_rejected_while_busy():
    """노출 중 GO 는 거부한다 (레거시 실측 에러 메시지)."""
    run = drive(['OBS>ICS exp 30', 'OBS>ICS dark d', 'OBS>ICS go',
                 'OBS>ICS go'], settle=1.0)
    assert run.find('Data acquisition already in progress!')

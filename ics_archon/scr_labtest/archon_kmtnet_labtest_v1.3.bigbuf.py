# archon_kmtnet_labtest_v1.3.bigbuf.py
# revised on 2026-08-26 by SMC
#
# Prev.version: __ref_archon_control/archon_kmtnet_labtest_v1.0.bigbuf.py (2025-04-18/SMC)
# Ref.version: archon_kmtnet_stascience_modtm_imgacq_v0.3_kasi.STA0287.102.py (2026-05-29/SMC)
#
# v1.3 (2026-08-26): CEU 샘플영상 획득용 코드 추가
#   Target 데이터셋 신설 (DS_TARGET = 4 — 비어 있던 자리를 써서 기존 번호 안 건드림)
#   TEST_DARK_NUMBER 도입 — dark 를 여러 장 찍을 수 있게. 다섯 데이터셋 전부 + _expected_dataset_bytes() 까지 일관 반영
#   실기 유닛 정보 — STA-0284(CTIO 행 유닛), IP .101, ACF KMTC_SCI_101_STA0284_R2608_MK.acf, 관측자 SMC
#   저장 자리 DS 폴더 분리 해제
#   헤더는 규격 v1.7 그대로 (SITE_CODE=KMTK = 실험실에서 딴 자료)
#
# v1.2 (2026-08-26): raw spec v1.5/v1.6 반영으로 **헤더 내용이 바뀌었다** --
#   값 카드 135 -> 131 (HK 4장 폐지) · CHMAP_* 4자 토큰 · ORIGNAME -> EXPID ·
#   Cn_* 구분자 공백 -> '|' · 결측 자리 sentinel 'NC' · 카드 폭 초과 규범.
#   ⚠️ **판을 올린 이유**: 이 상수 둘이 그대로 FITS ICSBUILD 카드에 실린다.
#   1.1.3 에 머물러 있으면 135카드/공백구분 프레임과 131카드/파이프 프레임이
#   **같은 ICSBUILD 로 찍혀** 나중에 헤더만 보고 구분할 수 없다.
#   파일명도 함께 옮겼다 (구 archon_kmtnet_labtest_v1.1.bigbuf.py).
#
# v1.1 (2026-08-22): raw spec 적용 (raw_fits_spec/KMT_CEU_Raw_FITS_Specification_v1.7.md)
#   ※ 최초 작성은 v1.3 기준. v1.4 는 1~4장 표현만 바뀌어 구현 영향이 없었고
#     (2.5절 삭제 = 취득 SW 소관 이관 · 4.1 RRRRLLLL 확정 · 4.2/4.4 표기),
#     **v1.5 (2026-08-26 반영)는 값이 바뀌어 아래 다섯 자리를 고쳤다.**
#   - 파일명: <SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits (D-011).  SITE 는 실험실이라
#     KMTK(KASI), 날짜는 UT (KMTK 보정 0), 번호는 기존 DS 체계(6자리) 유지.
#     ⚠️ v1.5/D-017: 구 KMTT(TESTBED) 폐지 -- KMTK(KASI) 가 그 자리를 잇는다.
#   - 이름 충돌: 격리·개명 대신 번호 증가 (D-016) — 쓰기 전에 MK·NT 두 경로를
#     선검사하고, 카운터 최초 배정분은 EXPID 카드로 남긴다 (v1.6/D-019 --
#     구 ORIGNAME).  EXPID 는 DETID 필드가 없어 pair 양쪽이 같다.  번호 공간은
#     D-018 로 000000-999999 가 되어 이 스크립트의 6자리 되감음과 같아졌다.
#   - FITS 헤더: 견본 초안 v1.0 pair 의 값 카드 **131장** + COMMENT 8장 + END 1
#     + 공백 4 = 144 레코드 (정확히 2880B x 4블록).  카드 순서·comment·패딩은
#     견본과 바이트 단위 동일 (기계 사본 = ics_sim/rawcards.py 와 같은 원천).
#     실험실에서 모르는 값은 규격 5.0절 sentinel ('NC' / -1 / '-999.99' /
#     '9.99e-9').
#   - v1.6 개정분 (2026-08-26 반영): ① ORIGNAME 폐지 · EXPID 신설 (위) ②
#     FILENAME comment -> 'FITS file name as written to storage' ③ Cn_*
#     구분자 공백 -> 파이프(|) · comment Ctr-n -> Ctrl-n · 결측 자리
#     sentinel 을 NC 로 (FIELD_NC -- 단일 HK 카드의 '-999.99' 와 다르다) ④
#     규격 5.0절에 카드 폭 초과 규범 신설: 80자를 넘으면 **comment 를 뒤에서
#     자르고 값은 자르지 않는다**.  comment 를 다 잘라도 넘칠 때만 값을
#     자르고 경고한다 (fits_card).  ⚠️ 나열 카드는 자리가 곧 항목이라 값이
#     잘리면 뒤 항목이 조용히 사라진다.
#     ⚠️ 전 자리 결측은 'NC' 한 토큰이 아니라 **자리 수만큼** 'NC|NC|...'
#     다 (5.6.1절 "자리는 비우지 않는다" -- 자리 수 자체가 모듈 구성
#     판별에 쓰인다).  all_fields_nc() 가 그것을 만든다.
#   - v1.5 개정분: ① HK 4장 폐지 (AIR_IN/AIR_OUT/GLYC_IN/GLYC_OUT) ② CHMAP_*
#     토큰 3자 -> 4자 <chip><A|D><nn> (01-08=A · 09-16=D) ③ 견본 comment 오타
#     2건 정정 (Telesope->Telescope · Acutator->Actuator) ④ 사이트 코드 D-017
#     ⑤ TELESCOP/FPAID 를 SITE_CODE 에서 유도 (5.3.1절).
#   - Archon STATUS 텔레메트리: C1_TEMP(BACKPLANE_TEMP+MODn/TEMP) ·
#     C1_VOLT/C1_CURR(P2V5 P5V P6V N6V P17V N17V P35V 레일) — Archon 매뉴얼 p.47-49.
#   - 데이터부 2880B 패딩 (규격 3장 — v1.0 은 마지막 블록이 잘려 있었다).
#   - DATE-OBS: 노출 지시(LOADPARAMS) 시점의 UTC, 밀리초까지 (규격 5.4절).
#     TIME-OBS(Local) 카드는 폐지 — DATE-OBS 하나가 날짜·시각을 다 담는다.
#   - science 유닛 = 이 bigbuf 판.  guide 유닛은 smallbuf 판(v1.0 원본 참조) —
#     guide raw 규격은 미정이라 아직 적용하지 않는다.
#

#-------------------------------------------------------------------------------
# HW / SW / Dataset Configurations
#

#--------------------------------
# Unit/Storage setup

DATA_PREFIX = 'KMTK'   #  <---- Set this (로그·SMS 표시용 유닛 라벨)

UNIT_ID = 'KMTK-SCI-101'   #  <---- Set this
UNIT_IP = '101'            #  <---- Set this

UNIT_IPADDR = '10.0.0.'+UNIT_IP
UNIT_TIMEOUT = 1

## 저장소 -- **자료는 무조건 이 한 곳으로 간다** (운영자 확정 2026-08-24).
##
## v1.1.2 까지는 세 갈래였다 (DATA_STORAGE_C/A/B = 내장 · USB SSD 둘) -- 데이터셋
## 마다 골라 넘겼다.  벤치 설치가 `~/AIC` 한 벌로 통일되면서(INSTALL.md) 저장
## 자리도 한 곳이다.  다른 디스크로 보내려면 이 값을 바꾸는 대신 `~/AIC/data`
## 를 심볼릭 링크로 둔다 -- 그래야 ics_sim/ics_archon 본편과 자리가 같아진다.
##
## **`~` 는 GetDataset 이 펼친다.**  여기서 os.path.expanduser 로 감싸지 않는
## 이유는 `import os` 가 아래(모듈 본문 앞머리)에 있어서다 -- 이 자리에서
## 부르면 NameError 다.  펼치지 않은 값이 os.makedirs 로 넘어가면 **작업
## 디렉터리 아래에 '~' 라는 이름의 폴더**가 생기고 오류도 안 난다
## (ics_sim config.py `_path_or` 의 2026-08-23 실측과 같은 함정).
DATA_STORAGE = '~/AIC/data'    #  <---- Set this: 취득 자료 저장 자리

#--------------------------------
# raw spec identity setup  (v1.1 신설 -- 현행 판 v1.6)
#
# 파일명 <SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits (D-011) 과 헤더 5장의
# ICS INI 출처 카드를 채우는 값들.  실험실은 KASI 라 SITE_CODE='KMTK',
# OBSERVAT='KASI', ORIGIN='KASI' 로 유도된다 (규격 2.2·5.3절, D-017).

SITE_CODE = 'KMTK'          # KASI(실험실).  관측소 반입 시 KMTC/KMTS/KMTA
                            # ⚠️ D-017(2026-08-25): 구 KMTT(TESTBED) 폐지
UNIT_CTRLTAG = 'MK'         #  <---- Set this: 이 유닛이 담당하는 detector pair
                            #        (MK = science ctrl 1 / NT = science ctrl 2)
UNIT_CTRL_ID = 'KMTC-SCI-101'   #  <---- Set this: FITS CTRL1ID (예 KMTA-SCI-101)
UNIT_CTRL_SN = 'STA-0284'       #  <---- Set this: FITS CTRL1SN (seril number on real pannel lable)
OBSERVER_NAME = 'SMC'           # FITS OBSERVER

## Archon STATUS 텔레메트리(Cn_TEMP/VOLT/CURR)를 헤더에 실을지.
##
## **False 로 두면 컨트롤러와의 왕복이 v1.0 과 완전히 같아진다** -- v1.1 이
## 추가한 프로토콜 명령은 STATUS 하나뿐이라, 그것을 끄면 검증된 v1.0 과
## 동일한 명령 열이 된다(헤더·파일명 변경은 호스트 쪽 일이라 무관).  실기에서
## 조금이라도 이상하면 여기부터 끄고 취득을 지킨다 -- Cn_* 는 'NC' 로 실린다.
TELEMETRY_ENABLE = True     #  <---- 문제가 보이면 False
TELEMETRY_TIMEOUT = 3.0     # STATUS 응답 대기 상한 [s]

SCRIPT_VERSION = '1.3.0'            # FITS ICSBUILD = v<버전>:<빌드일시>Z
SCRIPT_BUILD = '2026-08-26T18:05Z'  # 소스를 고치면 같이 올린다

## 위 손편집 항목(`<---- Set this`)을 **기동 시점에 한 번** 검증한다.
##
## 안 하면 오타가 매 노출의 헤더 생성 자리에서 터진다 -- 그 시점에는 이미
## 프레임을 fetch 해 둔 뒤라 **읽어낸 노출이 통째로 버려지고**, 파일명은
## 이미 잘못된 태그로 만들어진 상태다.  값이 틀린 것은 시작할 때 알아야 한다.
def _check_identity_setup():
    if UNIT_CTRLTAG not in ('MK', 'NT'):
        raise SystemExit("> ERROR: UNIT_CTRLTAG must be 'MK' or 'NT' "
                         "(got %r) -- detector pair of this unit" % UNIT_CTRLTAG)
    if SITE_CODE not in SITE_INFO:
        raise SystemExit('> ERROR: SITE_CODE must be one of %s (got %r)'
                         % ('/'.join(sorted(SITE_INFO)), SITE_CODE))
    ## **비ASCII 한 자도 못 들어간다.**  헤더는 문자 단위로 80자씩 조립하지만
    ## 파일에는 `bytes(head,'utf-8')` 로 쓴다 -- 한글 한 자가 3바이트라 그 카드
    ## 하나가 82바이트가 되고 헤더 전체가 2880B 배수를 벗어난다.  그러면
    ## astropy 는 END 카드를 못 찾고 **파일 전체**를 'Empty or corrupt FITS
    ## file' 로 거부한다.  취득 중에는 경고가 한 줄도 안 뜨므로, 손편집 문자열은
    ## 여기서 막는다 (FITS 헤더는 규격상 ASCII 전용이다).
    for name, text in (('SITE_CODE', SITE_CODE),
                       ('UNIT_CTRLTAG', UNIT_CTRLTAG),
                       ('UNIT_CTRL_ID', UNIT_CTRL_ID),
                       ('UNIT_CTRL_SN', UNIT_CTRL_SN),
                       ('OBSERVER_NAME', OBSERVER_NAME),
                       ('SCRIPT_VERSION', SCRIPT_VERSION),
                       ('SCRIPT_BUILD', SCRIPT_BUILD),
                       ('DATA_PREFIX', DATA_PREFIX)):
        if not text.isascii():
            raise SystemExit(
                '> ERROR: %s = %r 에 비ASCII 문자가 있다 -- FITS 헤더는 ASCII '
                '전용이다.\n'
                '>        한글/기호가 한 자라도 들어가면 헤더가 2880B 정렬을 '
                '벗어나 파일 전체를 못 읽는다.' % (name, text))

#--------------------------------
# ACF lists

UNIT_ACF_SCI_NORMAL = '../Config/acf/KMTC_SCI_101_STA0284_R2608_MK.acf'


#--------------------------------
# Notes

##
## File number for HELab.2025.03
##
##  File Number
##     1+2+1+2 digit: [UnitID(1)][TestSetup(2)][DatasetType(1)][FrameSN(2/3)]
##
##  Unit ID (1-digit)
##                1-22A / 2-22B / 3-23A / 4-23B / 
##                5-12A / 6-12B / 7-13A / 8-13B
##
##  Test Setup (2-digit) 
##    (1st place) 1x-fast.sens / 2x-fast.med / 3x-fast.lown / 
##                4x-comp.sens / 5x-comp.med / 6x-comp.lown /
##                7x-slow.sens / 8x-slow.med / 9x-slow.lown /
##                0x-other ACF for testing
##    (2nd place) x1-OD29V_R1  / x2-OD30V_R1  / x3-OD31V_R1  /
##                x4-OD29V_R2  / x5-OD30V_R2  / x6-OD31V_R2  /
##                x7-OD29V_STA / x8-OD30V_STA / x9-OD31V_STA /
##                x0-image check or other test setup w/suffix
##
##  Dataset Type(1-digit)
##                0xx: Check images
##                1xx: xTalk dataset
##                2xx: Dark dataset
##                3xx-4xx: iFlat dataset
##                5xx: Guide xTalk
##                6xx-9xx: reserved
##  
##  Frame SN(2-digit/3-digit)
##                000-099: xTalk/Dark
##                000-199: iFlat
##
##  Dataset ID (4-digit)
##    1+2+1 digit: [UnitID(1)][TestSetup(2)][DatasetType(1)]
##

#--------------------------------
# Configuration for Datasets

TEST_DATASET = 0;
TEST_SHOPEN = False
TEST_REF_ENABLE = False
TEST_REF_EXPTIME = 0  # ms
TEST_DARK_ENABLE = False
TEST_DARK_NUMBER = 0
TEST_DARK_EXPTIME = 0
TEST_FRAMENUM = 0
TEST_EXPTIMES = (0,)


## xTalk dataset
## with Max.LED
## Num of frame: 3 x 7 = 21 frames
## Running time: 0.3 hours (20 min)
TEST_SHOPEN_xTalk = True
TEST_REF_ENABLE_xTalk = False
TEST_REF_EXPTIME_xTalk = 0  # ms
TEST_DARK_ENABLE_xTalk = False
TEST_DARK_NUMBER_xTalk = 0
TEST_DARK_EXPTIME_xTalk = 0
TEST_FRAMENUM_xTalk = 3  # frame number in each subset
TEST_EXPTIMES_xTalk = (0, 1000, 4000, 0, 16000, 32000, 0)

## Dark dataset
## LED trigger disabled
## Num of frame:  3 x (16+5) = 63 frames
## Running time: 3.3 hours
TEST_SHOPEN_Dark = False
TEST_REF_ENABLE_Dark = False
TEST_REF_EXPTIME_Dark = 0  # ms
TEST_DARK_ENABLE_Dark = False
TEST_DARK_EXPTIME_Dark = 0
TEST_FRAMENUM_Dark = 3  # frame number in each subset
TEST_EXPTIMES_Dark = (0,) \
                   + (2395, 12123,  61371,  310689, 0,) \
                   + (3592, 18184,  92056,  466033, 0,) \
                   + (5388, 27276, 138084,  699049, 0,) \
                   + (8082, 40914, 207126, 1048574, 0,)

## iFlat dataset
## with new LED setup
## Num of frame: Flat25x3 + Ref24 + Bias3x3 + Dark1x3 = 111 frames
## Running time: 2.0 hours
TEST_SHOPEN_iFlat = True
TEST_REF_ENABLE_iFlat = True
TEST_REF_EXPTIME_iFlat = 12000  # ms
TEST_DARK_ENABLE_iFlat = True
TEST_DARK_NUMBER_iFlat = 1
TEST_DARK_EXPTIME_iFlat = 25000
TEST_FRAMENUM_iFlat = 3  # frame number in each subset
#TEST_EXPTIMES_iFlat = tuple(range(   0,  900, 100)) + (0,) \
#                    + tuple(range( 900, 1700, 100)) + (0,)  # old LED
TEST_EXPTIMES_iFlat = (0,) \
                    + tuple(range(  1000, 13001, 1000)) + (0,) \
                    + tuple(range( 14000, 25001, 1000)) + (0,) # new LED

## Notes for light source and dataset setup
##   Old LED: saturation started on center from 1500ms, fully saturated at 2000ms
##   New LED: saturation started on center from 24s, fully saturated at 30s
##   Max.ExpTime: 1048574ms(1048.574s) = (0x00100000 - 2) = 0x000FFFFE

## Target dataset
## with LED set to marked position
## Num of frame: 4 + 4 + 4 = 12 frames
## Running time: 0.2 hours (10 min)
TEST_SHOPEN_Target = True
TEST_REF_ENABLE_Target = False
TEST_REF_EXPTIME_Target = 0  # ms
TEST_DARK_ENABLE_Target = True
TEST_DARK_NUMBER_Target = 4
TEST_DARK_EXPTIME_Target = 3000
TEST_FRAMENUM_Target = 4  # frame number in each subset
TEST_EXPTIMES_Target = (3000, 0,)

## Gui-xtalk test dataset
TEST_SHOPEN_GxT = False
TEST_REF_ENABLE_GxT = False
TEST_REF_EXPTIME_GxT = 0  # ms
TEST_DARK_ENABLE_GxT = False
TEST_DARK_NUMBER_GxT = 0
TEST_DARK_EXPTIME_GxT = 0
TEST_FRAMENUM_GxT = 15  # frame number in each subset
TEST_EXPTIMES_GxT = (0,)

#--------------------------------
# SW setting for Controller optimization

##SWSET_EXPWAIT = 0.60  # optimized for ExpTime=1s with PREP+TM1
##SWSET_EXPWAIT = 0.75  # optimized for ExpTime=25s with PREP+TOx
##SWSET_EXPWAIT = 1.40  # optimized for ExpTime=25s with PREP+TM1
##SWSET_EXPWAIT = 0.90  # defaultTEST_POWERONDELAY = False
#SWSET_EXPWAIT = 0.90  # interval for waiting for exposure() proc
#--> SWSET_EXPWAIT set using local variable in Exposure()

#-------------------------------------------------------------------------------
# Python setup
#

## Importing modules

import sys, os, shutil
import socket, configparser, select, time  # for Archon control
import numpy as np

## Mecros

arrow = chr(int('02192',16))
bar_solid = chr(int('02588',16))
bar_shadow = chr(int('02593',16))

progbar = bar_shadow
progend = bar_solid

LOW = 0
HIGH = 1
UNDEF = 2
DEFAULT = LOW

DS_CHECK  = 0
DS_XTALK  = 1
DS_DARK   = 2
DS_IFLAT  = 3
DS_TARGET = 4
DS_GXT    = 5

AMPCFG = ('Low','High', 'Undef')

## Global variables

headbuf = ''
TestRunNum = 0
TestRunDone = 0
DatasetIdLast = 0
CURRENT_ACF = ''    # 마지막으로 적용한 ACF 경로 -- FITS CTRL1CFG/RDMODE 의 근거
STATUS_SNAPSHOT = {}  # 노출 개시 전에 뜬 Archon STATUS -- Cn_* 카드의 원천


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Archon control code
#

## Software setting for Archon control
SWSET_ACFRETRY = 4
SWSET_CONNECTRETRY = 4

## Default settings for Archon control
BURST_LEN = 1024

## Message reference
msgref = 0
msgbuf = b''
databuf = b''

## Send a textual command to Archon
def archonsend(cmd):
    global msgref
    archon.sendall(str.encode('>%02X%s\n' % (msgref, cmd)))
    msgref = (msgref + 1) % 256
    return

## Retrieve a textual response from Archon
def archonrecv():
    global msgref, msgbuf
    while not (b'\n' in msgbuf):
        msgbuf = msgbuf + archon.recv(4096)
    (reply, msgbuf) = msgbuf.split(b'\n', 1)
    if reply[0:3].decode() != '<%02X' % msgref:
        raise Exception('Invalid packet header in cmd recv')
    msgref = (msgref + 1) % 256
    return reply[3:]

## Retrieve a binary response from Archon
def archonbinrecv():
    global msgref, msgbuf
    binlen = BURST_LEN + 4
    while len(msgbuf) < binlen:
        msgbuf = msgbuf + archon.recv(4096)
    reply = msgbuf[0:binlen]
    msgbuf = msgbuf[binlen:]
    if reply[0:4].decode() != '<%02X:' % msgref:
        raise Exception('Invalid packet header in bin recv')
    msgref = (msgref + 1) % 256
    return reply[4:]

## Send a textual command and receive a textual response from Archon
def archoncmd(cmd, timeout=None):
    ## timeout=None 이면 v1.0 과 동일하게 응답이 올 때까지 기다린다 --
    ## APPLYALL 처럼 오래 걸리는 명령이 있어 기본 동작을 바꾸지 않는다.
    ## 값을 주면 그만큼만 기다리고 TimeoutError 를 낸다 -- v1.1 이 새로
    ## 넣은 STATUS 전용이고, 무한 회전으로 취득이 멈추는 것을 막는다.
    global msgref
    archon.sendall(str.encode('>%02X%s\n' % (msgref, cmd)))
    reply = b'';
    deadline = None if timeout is None else time.time() + timeout
    while not (b'\n' in reply):
        if select.select([archon], [], [], 0.01)[0]:
            reply = reply + archon.recv(1)
        elif deadline is not None and time.time() > deadline:
            raise TimeoutError('no reply to %s in %.1fs' % (cmd, timeout))
    reply = reply.splitlines()[0]
    if reply[0:3].decode() != '<%02X' % msgref:
        raise Exception('Invalid command packet header')
    msgref = (msgref + 1) % 256
    return reply[3:]

## Retrieve information about the most recent available frame
def newest():
    framestatus = {}
    for pair in archoncmd('FRAME').split():
        d = pair.decode().split('=')
        framestatus[d[0]] = d[1]
    rbuf = int(framestatus['RBUF']) - 1
    frames = []
    framecomplete = []
    for i in range(1,4):
        frames.append(int(framestatus['BUF%dFRAME' % i]))
        framecomplete.append(int(framestatus['BUF%dCOMPLETE' % i]) == 1)
    if rbuf >= 0 and rbuf <= 2:
        newestframe = frames[rbuf]
        newestbuf = rbuf
    else:
        newestframe = -1
        newestbuf = 0
    for i in range(0, 3):
        if frames[i] > newestframe and framecomplete[i]:
            newestframe = frames[i]
            newestbuf = i
    framew = int(framestatus['BUF%dWIDTH' % (newestbuf + 1)])
    frameh = int(framestatus['BUF%dHEIGHT' % (newestbuf + 1)])
    rbufbase = int(framestatus['BUF%dBASE' % (newestbuf + 1)])   ## for using bigbuffer
    samplemode = int(framestatus['BUF%dSAMPLE' % (newestbuf + 1)])
    #return (newestframe, newestbuf, framew, frameh, samplemode)
    return (newestframe, newestbuf, framew, frameh, samplemode, rbufbase)   ## for using bigbuffer


## Set PostAmpGain
def SetConfig(key, cfg):
    global config, configline
    config[key] = cfg
    #config[key.upper().replace('\\', '/')] = cfg.replace('"', '')    
    archoncmd('WCONFIG%04X%s=%s' % (configline[key], key, config[key]))
    #print('WCONFIG%04X%s=%s' % (configline[key], key, config[key]))  ######## ForDBG
    return


#-------------------------------------------------------------------------------
# raw spec FITS header  (v1.1 이 구 SetHeader 12카드를 전면 교체했다)
#
# 카드 목록·순서·comment·문자열 패딩 폭의 정본은 초안 헤더 v1.0 pair
# (raw_fits_spec/KMTA.20260821.123456.{MK,NT}.fits.header.v1.0.txt) 이고,
# 아래 RAWCARDS 는 그 기계 사본이다 (ics_sim/rawcards.py 와 같은 원천).
# 값 131 + COMMENT 8 + END 1 = 140 레코드 -- 2880 의 배수가 아니므로
# build_header() 가 END 뒤를 공백 레코드 4장으로 채워 144 레코드 ·
# 2880B x 4블록을 맞춘다 (v1.5 에서 HK 4장이 폐지되며 135 -> 131).
# 판 근거는 v1.7 -- 단 v1.7 은 파일명 넷째 필드를 <DETID> 로 명명했을
# 뿐이고 카드 내용은 v1.6 그대로다.  v1.6 이 정체성 카드를 ORIGNAME 에서
# EXPID 로 바꿨고(D-019),
# Cn_* 나열 카드가 파이프 구분 · 결측 자리 NC 가 됐다.
#
# 형: 'L' logical / 'I' 정수 (EXPTIME 은 소수점 있으면 실수) / 'R' 실수 /
#     'S' 문자열 (폭만큼 우측 공백 패딩).  'COMMENT' 는 블록 구분 카드.

RAWCARDS = (
    ('SIMPLE', 'L', 0, ''),
    ('BITPIX', 'I', 0, ''),
    ('NAXIS', 'I', 0, ''),
    ('NAXIS1', 'I', 0, ''),
    ('NAXIS2', 'I', 0, ''),
    ('BSCALE', 'I', 0, 'PHYSICAL=INTEGER*BSCALE+BZERO'),
    ('BZERO', 'I', 0, ''),
    ('BUNIT', 'S', 18, 'units of physical values'),
    ('COMMENT', '', 0, '  Instrument and Detector Information '
                       '________________________________'),
    ('INSTRUME', 'S', 18, 'Instrument Name'),
    ('CAMVER', 'S', 18, 'Camera electronics version'),
    ('FPAID', 'S', 18, 'FPA ID'),
    ('DETECTOR', 'S', 18, 'Detector device model'),
    ('DETID', 'S', 18, 'Detector pair in this raw FITS file'),
    ('PIXSIZE', 'R', 0, 'Unbinned pixel size [microns]'),
    ('PIXSCALE', 'R', 0, 'Unbinned pixel scale [arcsec per pixel]'),
    ('CCDXBIN', 'I', 0, 'CCD X-axis Binning Factor'),
    ('CCDYBIN', 'I', 0, 'CCD Y-axis Binning Factor'),
    ('NAMPDET', 'I', 0, 'Number of amplifiers in the detector'),
    ('NAMPRAW', 'I', 0, 'Number of amplifiers in the raw FITS file'),
    ('AMPNAX1', 'I', 0, 'Columns per amplifier (prescan+image+overscan)'),
    ('AMPNAX2', 'I', 0, 'Rows per amplifier (prescan+image+overscan)'),
    ('IMAGEX', 'I', 0, 'Image columns per amplifier'),
    ('IMAGEY', 'I', 0, 'Image rows per amplifier'),
    ('PRESCNX', 'I', 0, 'Prescan columns per amplifier (side varies)'),
    ('PRESCNY', 'I', 0, 'Prescan rows per amplifier (frame-edge side)'),
    ('OVRSCNX', 'I', 0, 'Overscan columns per amplifier (side varies)'),
    ('OVRSCNY', 'I', 0, 'Overscan rows per amplifier (frame-center side)'),
    ('COMMENT', '', 0, '  Map of CCD output channels, raw X ascending within '
                       'each card'),
    ('CHMAP_LT', 'S', 39, 'CCD out ch, left-half TOP'),
    ('CHMAP_LB', 'S', 39, 'CCD out ch, left-half BOT'),
    ('CHMAP_RT', 'S', 39, 'CCD out ch, right-half TOP'),
    ('CHMAP_RB', 'S', 39, 'CCD out ch, right-half BOT'),
    ('COMMENT', '', 0, '  Observatory Information '
                       '____________________________________________'),
    ('ORIGIN', 'S', 18, 'Location where the data was generated'),
    ('OBSERVAT', 'S', 18, 'Observatory Site'),
    ('TELESCOP', 'S', 18, 'Telescope Name'),
    ('LATITUDE', 'S', 18, 'Site Latitude [deg N]'),
    ('LONGITUD', 'S', 18, 'Site Longitude [deg W]'),
    ('ELEVATIO', 'I', 0, 'Site Elevation [meters]'),
    ('OBSERVER', 'S', 18, 'Observer(s)'),
    ('COMMENT', '', 0, '  Exposure Information'),
    ('PROJID', 'S', 18, 'Project ID'),
    ('IMAGETYP', 'S', 18, 'Type of observation'),
    ('OBJECT', 'S', 18, 'Name of object'),
    ('OBSTYPE', 'S', 18, 'Type of observation'),
    ('EXPTIME', 'I', 0, 'Exposure time [seconds]'),
    ('LEDFLASH', 'I', 0, 'Time to flash projector LEDs [milliseconds]'),
    ('TIMESYS', 'S', 18, 'ICS Time System'),
    ('DATE-OBS', 'S', 23, 'UTC Date and Time at start of obs'),
    ('FILENAME', 'S', 23, 'FITS file name as written to storage'),
    ('EXPID', 'S', 20, 'Exposure identifier assigned by ICS counter'),
    ('COMMENT', '', 0, '  Controller and ICS Information '
                       '_____________________________________'),
    ('DATASRC', 'S', 24, 'Pixel data source type'),
    ('CTRL1ID', 'S', 24, 'Controller 1 identifier'),
    ('CTRL1SN', 'S', 24, 'Controller 1 serial number'),
    ('CTRL1CFG', 'S', 24, 'Controller 1 Configuration file'),
    ('CTRL2ID', 'S', 24, 'Controller 2 identifier'),
    ('CTRL2SN', 'S', 24, 'Controller 2 serial number'),
    ('CTRL2CFG', 'S', 24, 'Controller 2 Configuration file'),
    ('ICSBUILD', 'S', 24, 'ICS/ICG software version and build Info'),
    ('RDMODE', 'S', 24, 'Readout mode setting'),
    ('COMMENT', '', 0, '  Camera System House Keeping Data'),
    ('DEWPRES', 'S', 18, 'Dewar pressure [torr]'),
    ('CCDTEMP', 'S', 18, 'CCD temperature M [deg C]'),
    ('DMPTEMP', 'S', 18, 'DMP temperature [deg C]'),
    ('PT30N1', 'S', 18, 'PT-30 #1 cold-end temperature [deg C]'),
    ('PT30N2', 'S', 18, 'PT-30 #2 cold-end temperature [deg C]'),
    ('CHARCOAL', 'S', 18, 'Charcoal canister temperature [deg C]'),
    ('WALLBRD', 'S', 18, 'Wallboard temperature [deg C]'),
    ('HEBOX', 'S', 18, 'HE box internal temperature [deg C]'),
    ('C1_TEMP', 'S', 51, 'Ctrl-1 T[C]'),
    ('C1_VOLT', 'S', 51, 'Ctrl-1 V[V]'),
    ('C1_CURR', 'S', 51, 'Ctrl-1 I[A]'),
    ('C2_TEMP', 'S', 51, 'Ctrl-2 T[C]'),
    ('C2_VOLT', 'S', 51, 'Ctrl-2 V[V]'),
    ('C2_CURR', 'S', 51, 'Ctrl-2 I[A]'),
    ('COMMENT', '', 0, '  TCS Information and Status '
                       '_________________________________________'),
    ('TCSLINK', 'S', 18, 'TCS Communications Link Status'),
    ('TCSARC', 'S', 18, 'TCS Link Auto Recovery Mode Status'),
    ('TCSQDATE', 'S', 23, 'UTC Date and Time of last TCS query'),
    ('TCSUDATE', 'S', 23, 'UTC Date and Time of last TCS update'),
    ('TCSTIME', 'S', 18, 'TCS Time System'),
    ('RADECSYS', 'S', 18, 'Telescope Coordinate System'),
    ('RA', 'S', 18, 'Telescope RA'),
    ('DEC', 'S', 18, 'Telescope DEC'),
    ('EQUINOX', 'S', 18, 'Coordinate System Equinox'),
    ('HA', 'S', 18, 'Hour Angle at start of obs'),
    ('ST', 'S', 18, 'Local Sidereal Time at start of obs'),
    ('SECZ', 'S', 18, 'Secant of ZD (Airmass) at start of obs'),
    ('ALT', 'S', 18, 'Telescope Altitude (elevation) in degrees'),  # v1.5 정정
    ('AZ', 'S', 18, 'Telescope Azimuth in degrees'),
    ('TCSDRIVE', 'S', 18, 'Telescope Drive Status'),
    ('TELMOVE', 'S', 18, 'Telescope Motion Status'),
    ('DSSTAT', 'S', 18, 'Dome Shutter Status'),
    ('DSUP', 'S', 18, 'Upper Dome Shutter Position'),
    ('DSLW', 'S', 18, 'Lower Dome Shutter Position'),
    ('DSSAF', 'S', 18, 'Dome Shutter Safety Status'),
    ('DSAUTO', 'S', 18, 'Dome Shutter Autosync Status'),
    ('DSALT', 'S', 18, 'Dome Shutter Altitude in degrees'),
    ('DSAZ', 'S', 18, 'Dome Shutter Azimuth in degrees (S to E)'),
    ('DSTELALT', 'S', 18, 'DS-reported telescope altitude'),
    ('DSTELAZ', 'S', 18, 'DS-reported telescope azimuth'),
    ('DALTERR', 'S', 18, 'Dome altitude synchronization error'),
    ('DAZERR', 'S', 18, 'Dome azimuth synchronization error'),
    ('COMMENT', '', 0, '  AUX Information and Status '
                       '_________________________________________'),
    ('AUXLINK', 'S', 18, 'AUX Control System Comm Link Status'),
    ('AUXARC', 'S', 18, 'AUX Link Auto Recovery Mode Status'),
    ('AUXQDATE', 'S', 23, 'UTC Date and Time of last AUX query'),
    ('AUXUDATE', 'S', 23, 'UTC Date and Time of last AUX update'),
    ('FSSTAT', 'S', 18, 'Filter-Shutter Subsystem Status'),
    ('FILTOP', 'S', 18, 'Filter Operational Status'),
    ('FILNUM', 'S', 18, 'Filter selector position number'),
    ('FILTER', 'S', 18, 'Filter Name in the beam'),
    ('SHUTOP', 'S', 18, 'Shutter Operational Status'),
    ('SHUTTER', 'S', 18, 'Shutter Position'),
    ('FASTAT', 'S', 18, 'Focus Actuator Subsystem Status'),         # v1.5 정정
    ('FAFOCUS', 'S', 18, 'Focus Position Offset in millimeters'),
    ('FATILTNS', 'S', 18, 'Focus Tilt NS Offset Angle in arcsec'),
    ('FATILTEW', 'S', 18, 'Focus Tilt EW Offset Angle in arcsec'),
    ('FAPOSS', 'S', 18, 'South Focus Actuator Position in millimeters'),
    ('FALIMS', 'S', 18, 'South Focus Actuator Limit Status'),
    ('FAPOSE', 'S', 18, 'East Focus Actuator Position in millimeters'),
    ('FALIME', 'S', 18, 'East Focus Actuator Limit Status'),
    ('FAPOSW', 'S', 18, 'West Focus Actuator Position in millimeters'),
    ('FALIMW', 'S', 18, 'West Focus Actuator Limit Status'),
    ('MCSTAT', 'S', 18, 'Mirror Cover Status'),
    ('MCPOS', 'S', 18, 'Mirror Cover Position in percent'),
    ('ENSTAT', 'S', 18, 'Environmental Control System Status'),
    ('ENFAN', 'S', 18, 'Environment System Fan power status'),
    ('ENS1', 'S', 18, 'Environment Sensor 1 in deg C or percent RH'),
    ('ENS2', 'S', 18, 'Environment Sensor 2 in deg C or percent RH'),
    ('ENS3', 'S', 18, 'Environment Sensor 3 in deg C or percent RH'),
    ('ENS4', 'S', 18, 'Environment Sensor 4 in deg C or percent RH'),
    ('ENS5', 'S', 18, 'Environment Sensor 5 in deg C or percent RH'),
    ('ENS6', 'S', 18, 'Environment Sensor 6 in deg C or percent RH'),
    ('ENS7', 'S', 18, 'Environment Sensor 7 in deg C or percent RH'),
    ('FSATEMP', 'S', 18, 'FSA internal temperature in degree C'),
    ('FSAHUM', 'S', 18, 'FSA internal humidity in percent RH'),
)

## 헤더가 **선언하는** 프레임 크기 (science 2-chip, raw spec 3장).
## 리터럴로 흩어 두면 실제 fetch 기하와 대조할 수가 없다 -- 쓰기 직전 단정에서
## 이 상수를 쓴다 (Exposure() 의 geometry check).
HDR_NAXIS1 = 19200
HDR_NAXIS2 = 9400

## CHMAP_* 4장 -- raw spec 4.5절 amp 전수 표의 투영 (pair 상이).
##
## **토큰은 4자 <chip><A|D><nn> 이다** (v1.5, 운영자 확정 2026-08-25).
## 가운데 글자는 채널 번호가 정한다 -- 01-08 = A · 09-16 = D (e2v image
## section, 부록 A).  종전 3자 표기(M16)를 대체했다.  chip 이나 사분면에서
## 유추하면 안 된다 -- 같은 chip 안에 MD16 과 MA01 이 함께 나온다.
## 기계 가독 정본(현행): raw_fits_spec/Detector_Ch_to_AmpID_Map_v1.1.txt
##   -- 대조는 이것으로 한다.  `__reference/..._v1.0.txt` 는 개정 전 원본
##      기록이다 (`__` 접두 폴더가 읽기 전용이라 사본을 루트로 올려 고쳤다).
CHMAP = {
    'MK': {
        'CHMAP_LT': 'MD16,MD15,MD14,MD13,MD12,MD11,MD10,MD09',
        'CHMAP_LB': 'MA01,MA02,MA03,MA04,MA05,MA06,MA07,MA08',
        'CHMAP_RT': 'KA08,KA07,KA06,KA05,KA04,KA03,KA02,KA01',
        'CHMAP_RB': 'KD09,KD10,KD11,KD12,KD13,KD14,KD15,KD16',
    },
    'NT': {
        'CHMAP_LT': 'NA08,NA07,NA06,NA05,NA04,NA03,NA02,NA01',
        'CHMAP_LB': 'ND09,ND10,ND11,ND12,ND13,ND14,ND15,ND16',
        'CHMAP_RT': 'TD16,TD15,TD14,TD13,TD12,TD11,TD10,TD09',
        'CHMAP_RB': 'TA01,TA02,TA03,TA04,TA05,TA06,TA07,TA08',
    },
}

## sentinel (raw spec 5.0절)
TEMP_NC = '-999.99'     # HK 온도·습도 문자열 카드의 측정불가 단일값
## Cn_* **나열 카드 안**의 결측 자리 (규격 5.6.1절, 운영자 확정 2026-08-26).
## ⚠️ 위 TEMP_NC 와 다르다 -- 7자짜리가 열 자리를 채우면 79자가 되어 카드
## 폭(80)을 넘긴다.  그러면 comment 를 다 지워도 값이 잘리고, 나열 카드에서
## 값이 잘리면 **뒤 항목이 조용히 사라진다**.  'NC' 면 29자로 들어간다.
## 전 자리 결측은 드물지 않다 -- STATUS 무응답 · 미장착 모듈.
FIELD_NC = 'NC'
DEWPRES_NC = '9.99e-9'  # DEWPRES 전용

## Cn_VOLT/Cn_CURR 의 자리 순서 -- Archon STATUS 의 전원 레일 (매뉴얼 p.47)
VOLT_RAILS = ('P2V5', 'P5V', 'P6V', 'N6V', 'P17V', 'N17V', 'P35V')

## Cn_TEMP 의 자리 순서 -- STATUS 의 온도 필드 (매뉴얼 p.47-48).
##
## **자리 = 항목이므로 목록이 고정이어야 한다** (raw spec 5.6절).  결측이면
## 그 자리에 sentinel 을 넣고 건너뛰지 않는다 -- 건너뛰면 뒤 항목이 앞으로
## 당겨져 소비자가 구분할 수 없다.
##
## ✅ **규격 수록이 끝났다 -- v1.5 5.6.1절이 science 10자리를 확정했다**
## (운영자 확정 2026-08-25).  자리 표:
##
##     1 Backplane      2 Mod1:LVDS     3 Mod2:Driver    4 Mod3:Driver
##     5 Mod4:LVXBias   6 Mod5:ADM      7 Mod8:ADM       8 Mod9:HVYBias
##     9 Mod10:Driver  10 Mod11:Driver
##
## 목록에 없는 모듈(6·7·12)은 자리를 차지하지 않는다 -- 자리 수 자체가 구성
## 판별에 쓰인다.  종전 잠정안은 `BACKPLANE_TEMP`+`MOD5`~`MOD8` 5자리였는데
## (매뉴얼 p.20 의 "AD 모듈은 중앙 4슬롯" 근거), 견본 pair 의 `C1_TEMP` 는
## 처음부터 10개였다 -- 잠정안이 견본과 갈려 있었다.
## 카드 폭은 51자다 -- 10자리 x '%.1f'(4자) + 파이프 9 = 49자로 들어간다
## (v1.6 에서 구분자가 공백에서 파이프로 바뀌었다 -- 폭 비용은 0이다).
## ⚠️ `ics_sim.rawhdr.TEMP_MODS` 가 정본이고 이것은 그 사본이다.
## `tests/test_labtest_spec_copy.py` 가 둘이 갈라지면 잡는다.
TEMP_MODS = ('BACKPLANE_TEMP', 'MOD1/TEMP', 'MOD2/TEMP', 'MOD3/TEMP',
              'MOD4/TEMP', 'MOD5/TEMP', 'MOD8/TEMP', 'MOD9/TEMP',
              'MOD10/TEMP', 'MOD11/TEMP')

## 사이트 코드 -> (OBSERVAT, ORIGIN, TELESCOP)  -- raw spec 2.2절 표 · 5.3절.
##
## **파일명 `<SITE>` 와 헤더 `OBSERVAT` 불일치는 이 규격에서 유일한 하드
## 실패다** (converter 가 교차 검증해 거부한다).  그래서 `SITE_CODE` 하나만
## 고치면 나머지가 따라오게 유도한다 -- 리터럴로 박아 두면 관측소 반입 때
## 파일명만 바뀌고 헤더는 옛 사이트로 남아 그 실행분 전량이 거부된다.
## `ORIGIN` = "이 파일이 생성된 곳" (관측소 raw = 관측소명, 실험실 = KASI).
##
## ⚠️ **`TELESCOP` 과 `FPAID` 도 사이트가 정한다** (raw spec **5.3.1절**,
## D-017 항목 6, 운영자 확정 2026-08-25).  망원경 번호와 FPA 번호는 **관측소
## 셋 모두 어긋난다** -- CTIO 망원경 #1·FPA #2 / SSO #3·FPA #1 / SAAO #2·FPA #3.
## 어긋난 것을 오타로 보고 맞추면 검출기 귀속이 통째로 틀어진다.
## (KASI 만 #0/#0 으로 같은데 그건 우연이다.)
SITE_INFO = {
    'KMTC': ('CTIO', 'CTIO', 'KMTNet 1.6m #1', 'FPA#2'),
    'KMTS': ('SAAO', 'SAAO', 'KMTNet 1.6m #2', 'FPA#3'),
    'KMTA': ('SSO',  'SSO',  'KMTNet 1.6m #3', 'FPA#1'),
    'KMTK': ('KASI', 'KASI', 'KMTNet 1.6m #0', 'FPA#0'),
}


def fits_card(key, kind, width, comment, value):
    """카드 이미지 80바이트 하나.  견본 v1.0 의 고정 형식을 그대로 재현한다.

    comment 없는 수치 카드도 ' /' 를 붙인다 -- 견본이 그렇다 (astropy 는
    생략하지만 정본은 견본이다).

    **폭이 모자라면 comment 를 먼저 줄인다** (규격 **5.0절**, 운영자 확정
    2026-08-26).  값이 자료이고 comment 는 설명이기 때문이다 -- 특히 `Cn_*`
    나열 카드는 **자리가 곧 항목**이라(5.6.1절) 값이 잘리면 뒤 항목이 통째로
    사라지는데 읽는 쪽은 그 사실을 알 방법이 없다.  자리 뜻의 정본은 어차피
    규격 5.6.1절 표다.

    comment 를 전부 지워도 넘치면 그때 **값을 자르고 경고한다.**  안 자르면
    카드가 80바이트에서 통째로 절단되어 **닫는 인용부호와 comment 가 사라지고**
    astropy·converter 가 파싱조차 못 한다 -- 규격 5장 머리말이 "카드 순서·
    comment·패딩까지 바이트 단위 기준"이라고 못박은 것을 정면으로 깨는 쪽이다.

    ⚠️ 본편 `ics_archon/archon/fitswrite.card_image()` 와 **같은 규칙**이다 --
    한쪽만 고치면 실험실 자료만 다른 절단 규범을 따르게 된다.
    """
    if key == 'COMMENT':
        # 'COMMENT'(7자) + 공백 1 + 본문 (본문은 견본 col 9 부터의 원문)
        return ('COMMENT ' + comment).ljust(80)[:80]
    if kind == 'S':
        text = str(value)
        ## 폭 계산과 패딩이 전부 **문자 수** 기준이므로 비ASCII 가 남으면
        ## 카드가 80바이트를 넘는다 -- 기동 검사(_check_identity_setup)가
        ## 손편집 값을 막지만, 여기 오는 값에는 STATUS·ACF 이름처럼 바깥에서
        ## 온 것도 있다.  마지막 방어선으로 '?' 로 바꾼다.
        if not text.isascii():
            print('> WARNING: FITS card %s value has non-ASCII characters '
                  '(%r) -- replaced with ?' % (key.strip(), text))
            text = text.encode('ascii', 'replace').decode('ascii')
        ## **값 안의 홑따옴표는 겹쳐 쓴다** (FITS 표준 4.2.1).  안 겹치면 그
        ## 자리가 값의 끝으로 읽혀 카드가 통째로 깨지는데 경고가 한 줄도 안
        ## 뜬다.  본편 card_image() 와 같은 방어다.
        text = text.replace("'", "''")
        # 값이 들어갈 수 있는 최대 폭 = 80 - ("KEY     = '" + "'" + " / " + comment)
        room = 80 - (10 + 1 + 1 + (3 + len(comment) if comment else 2))
        room = max(room, width)      # 견본 폭은 항상 들어간다
        if len(text) > room:
            ## **comment 를 먼저 줄인다** (5.0절).  comment 를 다 지웠을 때의
            ## 최대 폭은 ' /' 만 남기고 계산한다.
            room_bare = max(80 - (10 + 1 + 1 + 2), width)
            if len(text) <= room_bare:
                keep = 80 - (10 + 1 + 1 + 3) - len(text)
                comment = comment[:max(keep, 0)].rstrip()
                print("> WARNING: FITS card %s value is long (%d chars) -- "
                      "comment shortened, value kept (spec 5.0)"
                      % (key.strip(), len(text)))
            else:
                print("> WARNING: FITS card %s value too long (%d > %d) -- "
                      "comment dropped and value truncated.  If this is a "
                      "slot list, trailing items are gone (spec 5.6.1)"
                      % (key.strip(), len(text), room_bare))
                comment = ''
                text = text[:room_bare]
            ## **겹친 따옴표 한가운데서 자르면 안 된다** -- 홀수 개가 남으면
            ## 그것이 값의 끝으로 읽혀, 길이를 맞추려다 위에서 막은 결함을
            ## 그대로 만든다.
            trail = len(text) - len(text.rstrip("'"))
            if trail % 2:
                text = text[:-1]
        if len(text) < width:
            text = text.ljust(width)
        base = "%-8s= '%s'" % (key, text)
    else:
        if kind == 'L':
            token = 'T' if value else 'F'
        elif kind == 'I' and not (isinstance(value, float)
                                  and value != int(value)):
            token = '%d' % int(value)
        else:
            token = repr(float(value))
        base = '%-8s= %20s' % (key, token)
    base += ' / %s' % comment if comment else ' /'
    if len(base) > 80:
        ## 값은 위에서 폭에 맞췄으니 넘치는 것은 comment 쪽이다.  자체로는
        ## 파싱을 깨지 않지만(인용부호는 살아 있다) **조용한 절단**이라 알린다
        ## -- 견본 폭 + comment 가 80자를 넘는 조합은 템플릿 개정에서만 나온다.
        print('> WARNING: FITS card %s is %d chars -- comment cut by %d '
              '(template width %d + comment %d exceeds 80)'
              % (key.strip(), len(base), len(base) - 80, width, len(comment)))
    return base.ljust(80)[:80]


def build_header(values):
    """값 딕셔너리 -> 2880B 정렬 헤더 (144 레코드 = 4블록).

    RAWCARDS 템플릿 순서 그대로 조립한다 -- 템플릿에 없는 키는 버려지고,
    빠진 카드는 형별 sentinel 로 남는다 (규격 5.0절).

    **END 뒤는 공백 레코드로 블록을 채운다** (FITS 표준 패딩, 규격 3장).
    v1.5 에서 HK 4장이 폐지돼 값 131 + COMMENT 8 + END 1 = 140 레코드
    (11,200B)가 됐는데, 그건 2880 의 배수가 아니다 -- 공백 4장을 채워야
    144 레코드 · 11,520B 가 되고 견본 pair 와 바이트로 같아진다.
    ⚠️ 패딩 없이 단정만 두면 **카드 수가 바뀌는 개정마다 헤더 조립이 통째로
    거부된다** (v1.5 반영 때 실제로 그랬다).
    """
    cards = []
    for key, kind, width, comment in RAWCARDS:
        if key == 'COMMENT':
            cards.append(fits_card(key, kind, width, comment, ''))
            continue
        if key in values:
            value = values[key]
        else:
            value = {'S': 'NC', 'I': -1, 'R': -999.0, 'L': False}[kind]
        cards.append(fits_card(key, kind, width, comment, value))
    cards.append('END'.ljust(80))
    head = ''.join(cards)
    ## END 뒤를 공백 레코드로 채워 블록을 맞춘다 (규격 3장).
    head += ' ' * ((-len(head)) % 2880)
    ## **문자 수가 아니라 바이트 수**로 단정한다 -- 파일에 쓰는 것은
    ## bytes(head,'utf-8') 이고, 비ASCII 가 섞이면 문자 수는 맞는데 바이트
    ## 수가 어긋나 파일 전체가 안 읽힌다 (len(head) 로는 못 잡는다).
    ## 패딩을 문자 수로 계산했으므로 이 단정이 그 경우를 그대로 잡아낸다.
    nbytes = len(head.encode('utf-8'))
    assert nbytes % 2880 == 0, (
        'FITS 헤더가 2880B 정렬이 아니다 (%dB) -- 비ASCII 문자?' % nbytes)
    return head


def archon_status():
    """Archon STATUS 를 딕셔너리로 (매뉴얼 p.47-49).  실패하면 {}.

    **한 번 실패하면 이후 질의를 아예 끊는다.**  상한을 넘긴 뒤 늦게 도착한
    응답은 다음 archoncmd 가 자기 것으로 읽어 'Invalid command packet header'
    를 내고, 그러면 취득 자체가 죽는다 -- 어긋난 뒤에도 노출마다 계속 물어보는
    것은 그 위험을 되풀이하는 일이다.  카드 몇 장보다 취득이 우선이다.
    """
    global TELEMETRY_ENABLE
    if not TELEMETRY_ENABLE:
        return {}
    try:
        status = {}
        for pair in archoncmd('STATUS', timeout=TELEMETRY_TIMEOUT).split():
            d = pair.decode().split('=')
            status[d[0]] = d[1]
        return status
    except Exception as e:
        TELEMETRY_ENABLE = False
        print('> WARNING: STATUS query failed (%s)' % e)
        print('>          -- telemetry cards go NC for the rest of this run')
        ## 끄는 것만으로는 **이미 어긋난 것**이 안 풀린다 -- 늦게 도착한 응답이
        ## 소켓에 남아 다음 명령을 먹는다.  연결을 새로 열어 끊어낸다.
        _resync_archon_link('STATUS reply abandoned')
        return {}


def _resync_archon_link(why):
    """어긋난 연결을 **새로 열어** 초기화한다 (STATUS 시한 초과 전용).

    `archoncmd` 는 명령을 보낸 뒤 응답을 검증하고 나서야 `msgref` 를 올린다.
    시한 초과로 빠져나가면 **명령은 이미 나갔는데 msgref 는 그대로**여서,
    다음 명령이 같은 msgref 를 재사용한다 -- 늦게 도착한 STATUS 응답의 헤더
    `<NN` 가 그 msgref 와 맞아떨어지므로 다음 명령이 남의 응답을 자기 것으로
    먹고, 그 다음 명령이 'Invalid command packet header' 로 죽는다.  실측
    확인: 시한 초과 직후 `WCONFIG` 가 STATUS 본문을 받고, 이어지는
    `APPLYSYSTEM` 이 예외로 떨어졌다.

    **msgref 만 올려서는 안 된다.**  응답이 부분만 도착해 있었으면 소켓에 꼬리
    바이트가 남아 바로 다음 명령을 죽인다.  게다가 늦은 응답이 몇 분 뒤 다음
    데이터셋에서 튀어나올 수도 있다.  그래서 소켓을 버리고 새로 연다 --
    설정·전원은 컨트롤러가 들고 있으므로 재접속으로 잃는 상태는 없다.
    """
    global archon, msgbuf, msgref
    print('> WARNING: resyncing the Archon link (%s)' % why)
    try:
        archon.close()
    except Exception:
        pass
    msgbuf = b''
    last = None
    for attempt in range(3):
        try:
            archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            archon.settimeout(UNIT_TIMEOUT)
            archon.connect((UNIT_IPADDR, 4242))
            msgref = 0
            print('>          reconnected to %s:4242 -- msgref reset to 00'
                  % UNIT_IPADDR)
            return
        except Exception as e:
            last = e
            print('>          reconnect attempt %d failed (%s)' % (attempt + 1, e))
            time.sleep(1.0)
    raise RuntimeError('cannot reconnect to Archon at %s:4242 (%s)'
                       % (UNIT_IPADDR, last))


def status_number(status, key, fmt):
    """STATUS 필드 하나를 표기 고정 문자열로.  **결측·비수치는 sentinel.**

    `float()` 을 방어 없이 쓰면 STATUS 가 비수치 토큰을 하나 주는 것만으로
    `Exposure()` 가 죽는다 -- 그 시점에는 이미 프레임을 fetch 해 둔 뒤라
    **읽어낸 노출이 통째로 버려진다.**  헤더 값 하나 때문에 프레임을 버리는
    것은 손해가 훨씬 크므로 sentinel 로 남기고 저장은 계속한다 (규격 5.0절).
    """
    raw = status.get(key)
    if raw is None:
        return FIELD_NC
    try:
        return fmt % float(raw)
    except (TypeError, ValueError):
        print("> WARNING: STATUS %s=%r is not numeric -- writing %s"
              % (key, raw, FIELD_NC))
        return FIELD_NC


def all_fields_nc(n):
    """전 자리 결측 -- `'NC|NC|…'` n자리 (규격 5.6.1절 "자리는 비우지 않는다").

    ⚠️ `'NC'` **한 토큰으로 내면 안 된다.**  같은 절이 자리 수 자체를 모듈
    구성 판별에 쓰라고 규정하므로, 한 토큰짜리는 읽는 쪽에 "모듈 한 장짜리
    컨트롤러" 로 보인다.  규격이 전 자리 결측(STATUS 무응답 · 미장착 모듈)을
    "드물지 않다" 고 못박고 그 모습을 열 자리 `NC` 로 보인 것이 이 때문이다.
    """
    return '|'.join([FIELD_NC] * n)


def ctrl_telemetry_cards(status, ctrl_index):
    """STATUS -> Cn_TEMP/Cn_VOLT/Cn_CURR (규격 5.6절 -- 파이프 구분, 자리=항목).

    temp = `TEMP_MODS` 순, volt/curr = `VOLT_RAILS` 의 `_V`/`_I` 쌍.
    **결측 자리에도 sentinel 을 넣는다** -- 건너뛰면 뒤 항목이 앞으로 당겨져
    "자리 = 항목" 규약이 조용히 깨진다(소비자가 구분할 방법이 없다).

    Args:
        ctrl_index: 이 유닛이 **컨트롤러 몇 번인가** (1 = MK 쪽 / 2 = NT 쪽).
            규격 5.9절이 `Cn_*` 를 "양쪽 파일에 같은 값" 으로 규정하므로
            `C1_*` 는 "내 컨트롤러" 가 아니라 **컨트롤러 1 고정**이다 --
            NT 유닛의 값을 `C1_*` 에 넣으면 pair 두 파일이 같은 자리에 서로
            다른 컨트롤러를 싣게 된다.  실험실은 한 대만 돌리므로 나머지 한
            벌은 sentinel 이고, 두 대분을 합치는 것은 ics_archon 본편 몫이다.
    """
    out = {}
    ## 실험실은 컨트롤러 한 대만 돌린다 -- 나머지 한 벌은 **미장착**이고,
    ## 규격 5.6.1절이 그것을 "전 자리 결측" 으로 다룬다.
    other = 2 if ctrl_index == 1 else 1
    out['C%d_TEMP' % other] = all_fields_nc(len(TEMP_MODS))
    out['C%d_VOLT' % other] = all_fields_nc(len(VOLT_RAILS))
    out['C%d_CURR' % other] = all_fields_nc(len(VOLT_RAILS))
    if not status:
        out['C%d_TEMP' % ctrl_index] = all_fields_nc(len(TEMP_MODS))
        out['C%d_VOLT' % ctrl_index] = all_fields_nc(len(VOLT_RAILS))
        out['C%d_CURR' % ctrl_index] = all_fields_nc(len(VOLT_RAILS))
        return out
    ## 구분자는 **파이프**다 (규격 5.6.1절, 운영자 확정 2026-08-26).  공백
    ## 하나였는데 음수가 섞이면 경계가 눈으로 안 갈렸다.  ⚠️ 슬래시를 쓰지
    ## 말 것 -- FITS comment 구분자와 같은 글자라 순진한 파서가 값을 자른다.
    out['C%d_TEMP' % ctrl_index] = '|'.join(
        status_number(status, key, '%.1f') for key in TEMP_MODS)
    out['C%d_VOLT' % ctrl_index] = '|'.join(
        status_number(status, rail + '_V', '%.3f') for rail in VOLT_RAILS)
    out['C%d_CURR' % ctrl_index] = '|'.join(
        status_number(status, rail + '_I', '%.3f') for rail in VOLT_RAILS)
    return out


def resolve_pair_number(datadir, date_part, number):
    r"""이름 충돌 처리 (D-016, raw spec 2.3절) -- 쓰기 전에 후보 번호의
    MK·NT 두 경로를 선검사하고, 점유 시 +1 재검사 (999999 넘으면 000000).
    한 바퀴(1000000회)를 초과하면 예외 -- 유일한 저장 실패 조건이다.

    **D-018 (2026-08-25)로 관측 운용의 번호 공간도 000000-999999 가 됐다** --
    실험실 DS 번호 체계([Unit][Setup][Type][SN])가 6자리 전체를 쓰던 것과
    이제 같다.  구 규칙(099999 상한)과 갈려 있던 자리가 하나 없어졌다.
    파일명 형식(\d{6})은 처음부터 동일해 converter 정규식에 그대로 걸린다."""
    n = number % 1000000
    for _ in range(1000000):
        clash = False
        for tag in ('MK', 'NT'):
            path = '%s/%s.%s.%06d.%s.fits' % (datadir, SITE_CODE, date_part,
                                              n, tag)
            if os.path.exists(path):
                clash = True
                break
        if not clash:
            return n
        n = (n + 1) % 1000000
    raise RuntimeError('number space exhausted -- not saving (D-016)')


def build_spec_header(ShutOpen, ExpTimeMs, DateObs, AcfPath, FileStem,
                      OrigStem, DatasetId):
    """raw spec 5장 값 채우기 -- 실험실에서 아는 값 + sentinel (현행 v1.6).

    * IMAGETYP: 노출 조건에서 유도 -- 0초는 BIAS, 트리거 없으면 DARK,
      트리거(LED) 노출은 FLAT (대문자 통제 어휘, 규격 5.4절).
    * LEDFLASH: 실험실 광원(LED)이 셔터 트리거 라인으로 노출 내내 켜지므로
      트리거 노출이면 노출시간[ms], 아니면 0.
    * EXPTIME: ms/1000 -- 정수면 정수형, 아니면 실수형 (규격 5.4절).
    * TCS/AUX 카드: 실험실에는 계통이 없으므로 전부 'NC' (build_header 의
      sentinel 경로).  듀어 HK 도 이 스크립트는 읽는 경로가 없어 sentinel.
    * 관측소 정체(`OBSERVAT`/`ORIGIN`/`TELESCOP`)는 `SITE_CODE` 에서 유도한다.
    * 컨트롤러 카드는 `UNIT_CTRLTAG` 가 정하는 **색인 자리**로 들어간다.
    """
    observat, origin, telescop, fpaid = SITE_INFO[SITE_CODE]
    ctrl_index = 1 if UNIT_CTRLTAG == 'MK' else 2
    if ExpTimeMs <= 0:
        imgtype = 'BIAS'
    elif ShutOpen:
        imgtype = 'FLAT'
    else:
        imgtype = 'DARK'
    exptime = ExpTimeMs / 1000.0
    if exptime == int(exptime):
        exptime = int(exptime)
    acfname = os.path.splitext(os.path.basename(AcfPath))[0]
    rdmode = 'NORMAL'
    for token in ('fast', 'comp', 'slow'):
        if token in acfname.lower():
            rdmode = token.upper()
            break
    values = {
        'SIMPLE': True, 'BITPIX': 16, 'NAXIS': 2,
        'NAXIS1': HDR_NAXIS1, 'NAXIS2': HDR_NAXIS2,   # 2-chip frame (3장)
        'BSCALE': 1, 'BZERO': 32768, 'BUNIT': 'ADU',
        'INSTRUME': '%s 18k CCD' % SITE_CODE,
        'CAMVER': 'CEU-v2.1', 'FPAID': fpaid,      # 5.3.1절 -- 사이트 유도
        'DETECTOR': 'e2v CCD290-99',
        'DETID': UNIT_CTRLTAG,
        'PIXSIZE': 10.0, 'PIXSCALE': 0.395,
        'CCDXBIN': 1, 'CCDYBIN': 1,
        'NAMPDET': 16, 'NAMPRAW': 32,
        'AMPNAX1': 1200, 'AMPNAX2': 4700,
        'IMAGEX': 1152, 'IMAGEY': 4616,
        'PRESCNX': 0, 'PRESCNY': 0,
        'OVRSCNX': 48, 'OVRSCNY': 84,
        # 5.3 -- **SITE_CODE 에서 유도한다** (SITE_INFO).  파일명 <SITE> 와
        # OBSERVAT 불일치가 이 규격의 유일한 하드 실패이므로 리터럴로 박아
        # 두면 안 된다.  좌표(LATITUDE/LONGITUD/ELEVATIO)는 값 딕셔너리에
        # 넣지 않아 sentinel 로 남는다 -- KASI(실험실)는 일부러 비우는 것이
        # 규격이고(5.3절), 관측소 반입 시에는 측지값을 여기 채워야 한다.
        'OBSERVAT': observat, 'ORIGIN': origin, 'TELESCOP': telescop,
        'OBSERVER': OBSERVER_NAME,
        # 5.4
        'PROJID': 'ENG', 'IMAGETYP': imgtype, 'OBSTYPE': imgtype,
        'OBJECT': 'DS%04d' % DatasetId,
        'EXPTIME': exptime,
        'LEDFLASH': ExpTimeMs if ShutOpen else 0,
        'TIMESYS': 'UTC', 'DATE-OBS': DateObs,
        # EXPID 는 **`DETID` 필드를 붙이지 않는다** -- pair 양쪽이 같은
        # 값을 싣고 그것이 짝을 잇는 키가 된다 (D-019, 규격 5.9절).
        'FILENAME': FileStem,
        'EXPID': OrigStem.rsplit('.', 1)[0],
        # 5.5 -- 컨트롤러 정체는 **색인 자리**로 들어간다.  `CTRL1*` 는 "내
        # 컨트롤러" 가 아니라 컨트롤러 1(MK 쪽) 고정이다 (5.9절 "양쪽 파일에
        # 같은 값") -- NT 유닛 값을 CTRL1* 에 넣으면 pair 두 파일이 같은
        # 자리에 서로 다른 컨트롤러를 싣는다.  실험실은 한 대만 돌리므로
        # 나머지 한 벌은 sentinel 이고, 두 대분 합치기는 ics_archon 본편 몫.
        'DATASRC': 'ARCHON_SCIENCE',
        'CTRL%dID' % ctrl_index: UNIT_CTRL_ID,
        'CTRL%dSN' % ctrl_index: UNIT_CTRL_SN,
        'CTRL%dCFG' % ctrl_index: acfname,
        'ICSBUILD': 'v%s:%s' % (SCRIPT_VERSION, SCRIPT_BUILD),
        'RDMODE': rdmode,
        # 5.6 -- 듀어 HK 는 이 스크립트가 읽는 경로가 없다 (sentinel)
        'DEWPRES': DEWPRES_NC,
        'CCDTEMP': TEMP_NC, 'DMPTEMP': TEMP_NC, 'PT30N1': TEMP_NC,
        'PT30N2': TEMP_NC, 'CHARCOAL': TEMP_NC, 'WALLBRD': TEMP_NC,
        'HEBOX': TEMP_NC,
        # AIR_IN/AIR_OUT/GLYC_IN/GLYC_OUT 4장은 v1.5 에서 폐지됐다
        # (standalone RTD 계통, 5.6절 18장 -> 14장 · 5.10절 폐지 목록).
        'FSATEMP': TEMP_NC, 'FSAHUM': TEMP_NC,
    }
    values.update(CHMAP[UNIT_CTRLTAG])
    ## 텔레메트리는 **노출 개시 전에** 떠 둔 스냅샷을 쓴다 (Exposure 참고).
    ## 여기서 질의하면 이미 fetch 한 프레임을 손에 들고 왕복하는 셈이라,
    ## 컨트롤러가 답하지 않으면 다 읽어낸 그 노출을 잃는다.
    values.update(ctrl_telemetry_cards(STATUS_SNAPSHOT, ctrl_index))
    return build_header(values)


## Single exposure and writing a FITS
def Exposure(shopen, exptime, bWaitFlush, bFullFlush, filenum, datasetid,
             datadir):

    global config, configline
    global msgref
    global STATUS_SNAPSHOT

    print('> Start for Exposure #%06d / %dms ' % (filenum, exptime))

    ## FITS Cn_* 텔레메트리를 **노출 개시 전에** 떠 둔다.  v1.1 이 추가한
    ## 프로토콜 명령은 이 STATUS 하나뿐이고, 실패해도 이 시점에는 잃을
    ## 프레임이 없다 -- fetch 뒤에 두면 다 읽어낸 노출을 버리게 된다.
    STATUS_SNAPSHOT = archon_status()

    # Set shutter trigger output control mode
    if shopen: 
        print('> ShutOpen Enabled')
        SetConfig('TRIGOUTFORCE', 0)
    else:
        print('> ShutOpen Disabled')
        SetConfig('TRIGOUTFORCE', 1)
    archoncmd('APPLYSYSTEM')

    # Flush using a full readout
    if bFullFlush:
        #lastframe, lastbuf, _, _, _ = newest()
        lastframe, lastbuf, _, _, _, _ = newest()   ## for using bigbuffer
        SetConfig('PARAMETER2', 'IntMS=0')
        SetConfig('PARAMETER1', 'Exposures=1')
        archoncmd('LOADPARAMS')
        print('>> Flushing with a full readout..\n   ', end='')
        while True:
            #frame, buf, framew, frameh, samplemode = newest()
            frame, buf, framew, frameh, samplemode, baseaddr = newest()   ## for using bigbuffer
            if frame != lastframe:
                break
            time.sleep(0.4);  print(end=progbar);
        print(progend)

    # Get current frame number & date
    #lastframe, lastbuf, _, _, _ = newest()
    lastframe, lastbuf, _, _, _, _ = newest()   ## for using bigbuffer
    
    # Set exposure time
    SetConfig('PARAMETER2', 'IntMS=%d' % exptime)

    # Trigger an exposure
    SetConfig('PARAMETER1', 'Exposures=1')
    archoncmd('LOADPARAMS')

    # DATE-OBS = 노출 지시(LOADPARAMS) 시점의 UTC, 밀리초까지 (raw spec 5.4절).
    # 파일명 날짜부는 관측일인데 KMTK(KASI 실험실)는 보정 0 = UT 날짜 그대로
    # (D-014).  구판의 Local 시각·TIME-OBS 카드는 폐지 -- 시각은 전부 UTC 로
    # TIMESYS 가 선언한다.
    # TODO: 컨트롤러 정밀 시각은 TIMER + BUFnTIMESTAMP(10ns tick, 매뉴얼
    # p.49-50)로 얻을 수 있다 -- 단 BUFnTIMESTAMP 는 프레임 기록(readout) 개시
    # 시점이라 노출 개시와 다르므로 그대로 DATE-OBS 로 쓰면 안 된다.
    now = time.time()
    date = time.strftime('%Y%m%d', time.gmtime(now))
    dateobs = (time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(now))
               + '.%03d' % int((now % 1) * 1000))

    # Wait for frame to complete
    if bFullFlush:
        print('>> Exposure & Readout progress: \n   ', end='')  ## when using non-prep version
        sleepint = 0.5
    else:
        print('>> CCD Flush / Exposure / Readout progress: \n   ', end='')
        sleepint = 0.65
    while True:
        #frame, buf, framew, frameh, samplemode = newest()
        frame, buf, framew, frameh, samplemode, baseaddr = newest()   ## for using bigbuffer
        if frame != lastframe:
            break
        time.sleep(sleepint);  print(end=progbar);
    print(progend)
    
    # Fetch frame
    print('>> Image downloading..', end='')
    #archoncmd('LOCK%d' % (buf + 1))   ## remove to fetch debug on 2026-05-28
    if samplemode:
        framesize = 4 * framew * frameh
    else:
        framesize = 2 * framew * frameh
    ## **선언 NAXIS 와 실제 fetch 기하가 다르면 아예 읽지 않는다.**
    ## 데이터부를 2880B 로 패딩하기 때문에(v1.1 신설), 실제가 선언보다 길면
    ## 남는 꼬리가 블록 경계에 딱 맞아 astropy 가 그 뒤를 '다음 HDU' 로 읽고
    ## 'Header missing END card' 로 **파일 전체**를 거부한다 -- v1.0 은 꼬리가
    ## 미정렬이라 경고만 내고 열렸으니, 패딩이 이 경우를 악화시킨 셈이다.
    ## 걸리는 두 경로: samplemode(32bit 샘플 = 정확히 2배), ACF 기하 변경.
    ## fetch(25초) 앞에 두어 첫 프레임에서 바로 드러나게 한다.
    ## 대조는 **픽셀 수가 아니라 바이트 수**로 한다 -- samplemode 는 기하가
    ## 선언과 같은데도 표본이 32bit 라 framesize 가 정확히 2배가 되고, 그건
    ## 픽셀 수 비교로는 안 잡힌다 (pixnum = framesize/2 로 u2 재해석하므로
    ## 데이터부가 선언의 2배로 나간다).
    if framesize != HDR_NAXIS1 * HDR_NAXIS2 * 2:
        raise RuntimeError(
            'frame data %d B (%dx%d, %s) != header NAXIS %dx%d x2 = %d B '
            '-- not saving.  ACF 기하와 samplemode 를 확인하라.'
            % (framesize, framew, frameh,
               'samplemode/32bit' if samplemode else '16bit',
               HDR_NAXIS1, HDR_NAXIS2, HDR_NAXIS1 * HDR_NAXIS2 * 2))
    linesize = BURST_LEN
    lines = (framesize + linesize - 1) // linesize
    ref = msgref
    #archonsend('FETCH%08X%08X' % (((buf + 1) | 4) << 29, lines))  # small buffer (Addr: A/C/E)
    #archonsend('FETCH%08X%08X' % ((buf*3 + 10) << 28, lines))  # large buffer (Addr: A/D)
    #archonsend('FETCH%08X%08X' % (((buf^1)*3 + 10) << 28, lines))  # large buffer (Addr: D/A)
    archonsend('FETCH%08X%08X' % (baseaddr, lines))  # small/large buffer (Addr from BUFnBASE in the frame status)
    ## codes are added for using bigbuffer

    fitsbuf = bytearray();
    bytesremaining = framesize        
    for i in range(lines):
        msgref = ref
        datanum = min(linesize, bytesremaining)
        databuf = archonbinrecv()[0:datanum]
        fitsbuf += databuf
        bytesremaining -= linesize
    msgref = (msgref + 1) % 256
    print(' complete')

    # Rebuild image data & write a FITS  (raw spec 현행 v1.6)
    #
    # 파일명: <SITE>.<YYYYMMDD>.<NNNNNN>.<MK|NT>.fits (D-011).  이름이 겹치면
    # 번호를 올려 저장하고(D-016 선검사), 카운터(여기서는 DS 체계) 최초
    # 배정분은 EXPID 카드로 남는다 (D-019) -- 충돌 신호 = FILENAME 의 `DETID` 필드를
    # 뗀 값 != EXPID.
    # 구판의 '%s.%s.%06d.fits'%(prefix,...) 이름은 폐지 -- 죽은 prefix 인자를
    # datasetid 로 교체했다.  OBJECT 카드가 쓰던 filenum//100 역산은 iFlat
    # (116 프레임)의 nframe>=100 구간에서 DatasetId+1 이 되어, DS7213 실행이
    # DS7213/ 폴더에 들어가면서 카드는 OBJECT='DS7214' 가 됐다.  호출측이
    # DatasetId 를 이미 들고 있으므로 그대로 넘긴다.
    print('>> FITS writing..', end='')
    orig_stem = '%s.%s.%06d.%s' % (SITE_CODE, date, filenum, UNIT_CTRLTAG)
    final_num = resolve_pair_number(datadir, date, filenum)
    file_stem = '%s.%s.%06d.%s' % (SITE_CODE, date, final_num, UNIT_CTRLTAG)
    if final_num != filenum:
        print('\n>> WARNING: filename clash -- number bumped %06d -> %06d '
              '(D-016)' % (filenum, final_num))
    headbuf = build_spec_header(shopen, exptime, dateobs, CURRENT_ACF,
                                file_stem, orig_stem, datasetid)
    pixnum = int(framesize/2)
    fitsbuf = np.ndarray(shape=(pixnum,),dtype='<u2', buffer=fitsbuf)
    fitsbuf += 0x8000
    fitsbuf = fitsbuf.byteswap()
    # 데이터부도 2880B 블록으로 패딩한다 (규격 3장 -- v1.0 은 잘려 있었다)
    pad = (-fitsbuf.nbytes) % 2880
    with open('%s/%s.fits' % (datadir, file_stem), 'wb') as f:
        f.write(bytes(headbuf,'utf-8'))
        f.write(fitsbuf)
        if pad:
            f.write(b'\x00' * pad)
    print(' complete')

    if bWaitFlush: 
        print(">> Waiting for flushing more: ", end='')
        for ii in range(14):
            time.sleep(0.5); print(end=progbar);
        print(progend)
          
    print()
    
    return


## Report current dataset configuration
def RepDatasetConfig():

    if TEST_DATASET == DS_XTALK:
        print('-'*28);
        print("xTalk dataset configuration")
    elif TEST_DATASET == DS_DARK:
        print('-'*28);
        print("Dark dataset configuration")
    elif TEST_DATASET == DS_IFLAT:
        print('-'*28);
        print("iFlat dataset configuration")
    elif TEST_DATASET == DS_TARGET:
        print('-'*28);
        print("Target dataset configuration")
    elif TEST_DATASET == DS_GXT:
        print('-'*28);
        print("GxT dataset configuration")
    else:
        print("ReportDatasetConfig(): Check dataset type!")
        return
    print('-'*28);

    nframe = TEST_DATASET*100

    if TEST_REF_ENABLE:
        print ("  %03d: %5.1fs reference" % (nframe,TEST_REF_EXPTIME/1000))
        nframe+=1

    for exptime in TEST_EXPTIMES:

        for i in range(0, TEST_FRAMENUM):
            if TEST_SHOPEN:
                print ("  %03d: %5.1fs shopen" % (nframe,exptime/1000))
            else:
                print ("  %03d: %5.1fs shclose" % (nframe,exptime/1000))
            nframe+=1

        if TEST_DARK_ENABLE and exptime==0:
            for i in range(0, TEST_DARK_NUMBER):
                print ("  %03d: %5.1fs dark" % (nframe,TEST_DARK_EXPTIME/1000))
                nframe+=1
        if TEST_REF_ENABLE:
            print ("  %03d: %5.1fs reference" % (nframe,TEST_REF_EXPTIME/1000))
            nframe+=1

    print('-'*28)

    return


## Set dataset
def SetDatasetConfig(DatasetType):

    global TEST_DATASET
    global TEST_SHOPEN
    global TEST_REF_ENABLE
    global TEST_REF_EXPTIME
    global TEST_DARK_ENABLE
    global TEST_DARK_NUMBER
    global TEST_DARK_EXPTIME
    global TEST_FRAMENUM
    global TEST_EXPTIMES
    
    TEST_DATASET = DatasetType  # 0: Check 1: xTalk / 2: Dark / 3: iFlat / 4: Target / 5: Gui-xTalk

    if DatasetType == DS_XTALK:
        TEST_SHOPEN = TEST_SHOPEN_xTalk
        TEST_REF_ENABLE = TEST_REF_ENABLE_xTalk
        TEST_REF_EXPTIME = TEST_REF_EXPTIME_xTalk
        TEST_DARK_ENABLE = TEST_DARK_ENABLE_xTalk
        TEST_DARK_NUMBER = TEST_DARK_NUMBER_xTalk
        TEST_DARK_EXPTIME = TEST_DARK_EXPTIME_xTalk
        TEST_FRAMENUM = TEST_FRAMENUM_xTalk
        TEST_EXPTIMES = TEST_EXPTIMES_xTalk
        print("Set dataset type = xTalk")
    elif DatasetType == DS_DARK:
        TEST_SHOPEN = TEST_SHOPEN_Dark
        TEST_REF_ENABLE = TEST_REF_ENABLE_Dark
        TEST_REF_EXPTIME = TEST_REF_EXPTIME_Dark
        TEST_DARK_ENABLE = TEST_DARK_ENABLE_Dark
        TEST_DARK_EXPTIME = TEST_DARK_EXPTIME_Dark
        TEST_FRAMENUM = TEST_FRAMENUM_Dark
        TEST_EXPTIMES = TEST_EXPTIMES_Dark
        print("Set dataset type = Dark")
    elif DatasetType == DS_IFLAT:
        TEST_SHOPEN = TEST_SHOPEN_iFlat
        TEST_REF_ENABLE = TEST_REF_ENABLE_iFlat
        TEST_REF_EXPTIME = TEST_REF_EXPTIME_iFlat
        TEST_DARK_ENABLE = TEST_DARK_ENABLE_iFlat
        TEST_DARK_NUMBER = TEST_DARK_NUMBER_iFlat
        TEST_DARK_EXPTIME = TEST_DARK_EXPTIME_iFlat
        TEST_FRAMENUM = TEST_FRAMENUM_iFlat
        TEST_EXPTIMES = TEST_EXPTIMES_iFlat
        print("Set dataset type = iFlat")
    elif DatasetType == DS_TARGET:
        TEST_SHOPEN = TEST_SHOPEN_Target
        TEST_REF_ENABLE = TEST_REF_ENABLE_Target
        TEST_REF_EXPTIME = TEST_REF_EXPTIME_Target
        TEST_DARK_ENABLE = TEST_DARK_ENABLE_Target
        TEST_DARK_NUMBER = TEST_DARK_NUMBER_Target
        TEST_DARK_EXPTIME = TEST_DARK_EXPTIME_Target
        TEST_FRAMENUM = TEST_FRAMENUM_Target
        TEST_EXPTIMES = TEST_EXPTIMES_Target
        print("Set dataset type = Target")
    elif DatasetType == DS_GXT:
        TEST_SHOPEN = TEST_SHOPEN_GxT
        TEST_REF_ENABLE = TEST_REF_ENABLE_GxT
        TEST_REF_EXPTIME = TEST_REF_EXPTIME_GxT
        TEST_DARK_ENABLE = TEST_DARK_ENABLE_GxT
        TEST_DARK_NUMBER = TEST_DARK_NUMBER_GxT
        TEST_DARK_EXPTIME = TEST_DARK_EXPTIME_GxT
        TEST_FRAMENUM = TEST_FRAMENUM_GxT
        TEST_EXPTIMES = TEST_EXPTIMES_GxT
        print("Set dataset type = GxT")
    else:
        TEST_DATASET = DS_CHECK
        print("SetDataset(): Check dataset type!")
        
    return


## Process multiple integration & FITS output for an iFlat dataset
## Note: bWaitFlush and bFullFlush are used when using non-prep version    
## 프레임 하나가 파일에서 차지하는 바이트 -- 헤더 4블록 + 데이터 + 2880 패딩.
FRAME_FILE_BYTES = (2880 * 4
                    + HDR_NAXIS1 * HDR_NAXIS2 * 2
                    + (-(HDR_NAXIS1 * HDR_NAXIS2 * 2)) % 2880)
GIB = 1073741824.0


def _expected_dataset_bytes():
    """이 데이터셋이 쓸 바이트.  SetDatasetConfig 가 정한 값을 그대로 센다.

    아래 노출 루프와 **같은 셈이어야 한다** -- REF 는 맨 앞에 한 장 더 붙고
    노출마다 한 장씩 붙으며, DARK 는 0 초 노출마다 한 장씩 붙는다.
    """
    nframe = len(TEST_EXPTIMES) * TEST_FRAMENUM
    if TEST_REF_ENABLE:
        nframe += 1 + len(TEST_EXPTIMES)
    if TEST_DARK_ENABLE:
        nframe += sum(1 for ms in TEST_EXPTIMES if ms == 0) * TEST_DARK_NUMBER
    return nframe * FRAME_FILE_BYTES


def _check_data_storage(datastorage):
    """저장 자리를 **POWERON 전에** 확인한다 (v1.1.3 신설).

    `createFolder` 는 OSError 를 삼키고 메시지만 찍는다.  그래서 경로가 틀리면
    폴더가 안 생긴 채로 진행하고, 그 다음 `os.listdir(datadir)` 이
    FileNotFoundError 로 터진다 -- 그 자리가 노출 루프 `try/finally` 의
    **바깥**이라 POWEROFF 를 못 보내고 **전원을 켠 채로** 끝난다.  ACF 선검사와
    같은 자리에서 같은 방식으로 막는다.
    """
    ## **없으면 만들지 않고 거부한다.**  만들어 주면 오타가 조용히 새 트리를
    ## 만든다 -- '~' 를 안 펼친 경우(cwd 아래 '~' 폴더)와 마운트가 안 붙은
    ## 경우(외장 대신 OS 디스크에 수십 GiB)가 둘 다 이리로 온다.  저장 자리를
    ## 만드는 것은 운영자 몫이다 (INSTALL.md "2. 자리 만들기").
    if not os.path.isdir(datastorage):
        raise SystemExit(
            "> ERROR: data storage not found -- '%s'\n"
            ">        cwd '%s'\n"
            '>        **만들어 주지 않는다.**  마운트가 안 붙었거나 경로가 틀린\n'
            '>        것을 폴더 생성으로 덮으면 자료가 엉뚱한 곳에 쌓인다.\n'
            '>        자리를 먼저 만들어라 -- mkdir -p, 또는 마운트 확인\n'
            '>        (lsblk -o NAME,LABEL,MOUNTPOINT).'
            % (datastorage, os.getcwd()))

    ## 읽기전용 마운트는 isdir 로 안 잡힌다 -- 실제로 써 봐야 안다.
    ## 외장 디스크가 I/O 오류를 내면 커널이 조용히 ro 로 다시 붙인다.
    probe = os.path.join(datastorage, '.labtest_write_test')
    try:
        with open(probe, 'wb'):
            pass
        os.remove(probe)
    except OSError as e:
        raise SystemExit(
            "> ERROR: data storage not writable -- '%s'\n"
            '>        %s\n'
            '>        읽기전용으로 붙었거나 권한이 없다 (`mount | grep` 로 확인).'
            % (datastorage, e))

    ## 여유 용량.  모자라면 노출 중간에 ENOSPC 로 끊긴다 -- 전원을 켠 뒤라
    ## 여기서 막는 것이 낫다.  데이터셋마다 보므로 첫 데이터셋이 통과하고
    ## 셋째에서 걸릴 수 있다 -- 그때도 그 데이터셋의 POWERON 앞이다.
    need = _expected_dataset_bytes()
    free = shutil.disk_usage(datastorage).free
    if free < need:
        raise SystemExit(
            "> ERROR: data storage too small -- '%s'\n"
            '>        need %.2f GiB (%d frames) / free %.2f GiB\n'
            '>        비우거나 다른 디스크로 옮겨라.'
            % (datastorage, need / GIB, need // FRAME_FILE_BYTES, free / GIB))

    ## 마운트 지점이 아니면 **경고만** 한다 -- `~/AIC/data` 를 OS 디스크의
    ## 평범한 디렉터리로 두는 것도 정상 배치다 (INSTALL.md).  다만 외장
    ## 디스크를 쓸 작정이었는데 안 붙은 경우가 이리로 오므로 알리기는 한다.
    ## 심볼릭 링크로 걸었으면 링크가 가리키는 자리를 본다.
    if not os.path.ismount(os.path.realpath(datastorage)):
        print("> WARNING: '%s' 는 마운트 지점이 아니다 -- OS 디스크에 쌓인다"
              % datastorage)
        print('>          외장 디스크를 쓸 작정이었으면 마운트를 확인하라.')
    print("> Data storage '%s' -- free %.2f GiB / need %.2f GiB"
          % (datastorage, free / GIB, need / GIB))
    print()


def GetDataset(AcfPath, bWaitFlush, bFullFlush, DatasetId, StartNum, DataStorage):

    global archon
    global config, configline
    global msgref
    global TestRunNum, TestRunDone
    global DatasetIdLast
    global CURRENT_ACF

    ## ACF 가 없으면 **여기서 멈춘다.**  configparser 의 read() 는 없는 파일에
    ## 조용히 성공하고 그 다음 items('CONFIG') 가 NoSectionError 로 터지므로,
    ## "설정 파일이 없다" 라는 원인이 화면에 안 나온다.  경로가 상대경로
    ## ('acf/...') 라 **작업 디렉터리가 다른 것**이 가장 흔한 원인이어서 풀어낸
    ## 절대경로와 cwd 를 같이 찍는다.  POWERON 앞이라 여기서 멈추는 것은
    ## 안전하다 -- 이 데이터셋은 아직 전원을 올리지 않았다.
    if not os.path.isfile(AcfPath):
        raise SystemExit(
            "> ERROR: ACF not found -- '%s'\n"
            ">        resolved to '%s'\n"
            ">        cwd        '%s'\n"
            '>        경로가 상대경로다 -- 스크립트를 그 상위 폴더에서 '
            '실행했는지 확인하라.'
            % (AcfPath, os.path.abspath(AcfPath), os.getcwd()))

    ## **`~` 를 여기서 펼친다.**  DataStorage 는 이 아래 datadir 조립에만
    ## 쓰이므로(한 곳), 인자를 다시 묶는 것으로 아래 전부가 따라온다.
    DataStorage = os.path.expanduser(DataStorage)

    ## 저장소 선검사 -- ACF 와 같은 자리(POWERON 앞)에서 본다.
    ## SetDatasetConfig 를 여기로 올린 이유는 예상 용량을 알기 위해서다.  이
    ## 함수는 전역 대입과 print 뿐이라 컨트롤러와 무관하다 (v1.1.2 까지는
    ## 노출 루프 바로 앞, 즉 POWERON 뒤에서 불렀다).
    SetDatasetConfig(DatasetId%10)
    _check_data_storage(DataStorage)

    CURRENT_ACF = AcfPath    # FITS CTRL1CFG/RDMODE 의 근거 (raw spec 5.5절)

    print('DS%04d dataset acquisition start..\n' % DatasetId )

    #if TestRunDone == 0:
    #    SMS_TIO_HELabAlerts('HELab: %s test start.. FirstDID=%04d / RunNum=%d' 
    #                       % (DATA_PREFIX, DatasetId, TestRunNum) ); print();

    if TestRunDone == (TestRunNum-1):
        SMS_TIO_HELabAlerts('HELab: %s test - last run DS%04d start..' 
                           % (DATA_PREFIX, DatasetId) ); print();
    #else:
    #    SMS_TIO_HELabAlerts( 'HELab: %s test run DS%04d (%d/%d) start..'
    #        % (DATA_PREFIX, DatasetId, TestRunDone+1, TestRunNum) ); print();

    # Read configuration file    
    print(f"> ACF loading from '{AcfPath}'")    
    config = configparser.RawConfigParser()
    config.read(AcfPath)
    lines = config.items('CONFIG')
    config = {}    
    
    # Convert INI-style slashes and quotes to Archon format
    for i in range(len(lines)):
        config[lines[i][0].upper().replace('\\', '/')] = lines[i][1].replace('"', '')
    '''   
    # Check for configuration    
    print('-'*60);  print(f'  ACF: {AcfPath}');  print('-'*60);
    i = 0
    configline = {}
    for k in config.keys():
        configline[k] = i
        print('  CFG LINE %04d: %s=%s' % (i, k, config[k]))
        i = i + 1
    '''
    
    # Apply configuration    

    for acfretry in range(30):

        print("> Appling all the ACF to Archon unit..", end='')    
    
        archoncmd('CLEARCONFIG')
    
        ref = msgref
        i = 0
        configline = {}
        for k in config.keys():
            configline[k] = i
            archonsend('WCONFIG%04X%s=%s' % (i, k, config[k]))
            i = i + 1
        msgref = ref
    
        try:
            for k in config.keys():
                archonrecv()
                
        except Exception as e:
            print(" failed\n  Error: ", e)
            archon.close()
            if acfretry == SWSET_ACFRETRY: 
                print("\n>> Error: Failed to write ACF into Archon!\n")
                SMS_TIO_HELabAlerts('HELab: Achon test stopped with packet recv error.')
                print()
                sys.exit()
            time.sleep(0.8)
            print('> Retry to connect to AC unit #%02d ....' \
                  % int(UNIT_IPADDR.split('.')[-1]), end='')
            archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            archon.settimeout(UNIT_TIMEOUT)
            archon.connect((UNIT_IPADDR, 4242))
            print(' success.')        
            time.sleep(2.0)
            continue
        
        break
    
    #archoncmd('APPLYALL')
    
    for acfretry in range(30):
        try:
            archoncmd('APPLYALL')
        except Exception as e:
            print(" failed\n  Error: ", e)
            archon.close()
            if acfretry == SWSET_ACFRETRY: 
                print("\n>> Error: Failed to command 'APPLYALL' !\n")
                SMS_TIO_HELabAlerts('HELab: Achon test stopped with APPLYALL cmd error.')
                print()
                sys.exit()
            time.sleep(0.8)
            print('> Retry to connect to AC unit #%02d ....' \
                  % int(UNIT_IPADDR.split('.')[-1]), end='')
            archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            archon.settimeout(UNIT_TIMEOUT)
            archon.connect((UNIT_IPADDR, 4242))
            print(' success.')
            time.sleep(2.0)
            print('> Retry to apply all the ACF .. ', end='') 
            continue
            
        break

    print(' complete')

    SMS_TIO_HELabAlerts( 'HELab: DS%04d (%d/%d) started, ACF loading complete'
                           % (DatasetId, TestRunDone+1, TestRunNum) ); print();


    ####print('\n'); return;  ######## ForDBG for v0.5
    
    
    # CCD input clock/bias power ON
    
    print("> CCD input clock/bias power ON", end='')
    archoncmd('POWERON')
    if bWaitFlush or bFullFlush:
        print(" and Waiting for CCD flush..\n  ", end='')
        for i in range(24):
            time.sleep(0.5); print(end=progbar);
        print(end=progend)
    print('\n')


    '''
    # Data acquisition start message
    
    #print('> [ DS%04d %sGain C%+.1fV ] dataset acquisition start..\n' \
    #       % (DatasetId, AMPCFG[AmpGain], ClampLevel) )

    # Set PostAmp gain
    
    print('> Set PostAmp(AD) to %s gain' % AMPCFG[AmpGain])    
    SetConfig('MOD5/PREAMPGAIN', '%d'%AmpGain)
    SetConfig('MOD6/PREAMPGAIN', '%d'%AmpGain)
    SetConfig('MOD7/PREAMPGAIN', '%d'%AmpGain)
    SetConfig('MOD8/PREAMPGAIN', '%d'%AmpGain)

    # Set ClampLevel
    
    print('> Set ClampLevel to %+.2fV' % ClampLevel)
    SetConfig('CONSTANT10', 'CLAMP_LEVEL=%+.2f' % ClampLevel)

    print()

    --> oldver, APPLYALL necessary
    '''

    # Setup for data directory
    
    #datadir = "%s/DS%04d" % (DataStorage, DatasetId)
    datadir = DataStorage
    createFolder(datadir)

    ## **같은 UT 날짜에** 파일이 남아 있는 DS 폴더를 StartNum=0 으로 다시
    ## 돌리면 덮어쓰지 않는다.  v1.0 은 같은 이름을 'wb' 로 열어 덮어써서
    ## 재실행이 멱등했지만, v1.1 은 D-016 선검사가 점유된 번호를 피해 올라간다.
    ## 그래서 재실행분은 다음 DS 의 번호 영역으로 넘어가고, `filenum -
    ## DatasetId*100 == nframe` 이라는 v1.0 의 불변식이 깨진다 -- '07번 프레임'
    ## 식으로 번호를 믿는 분석이 어긋난다.  폴더를 비우거나 옮기거나,
    ## StartNum 으로 이어받아라.
    ##
    ## **날짜까지 봐야 한다.**  선검사 경로에 날짜가 들어 있으므로(D-011)
    ## 다음 날 같은 DS 를 다시 찍는 것은 충돌이 아니다 -- 그게 실험실의 평상
    ## 재실행이고, 날짜를 안 보면 그때마다 헛경고가 뜬다.
    today = time.strftime('%Y%m%d', time.gmtime())
    stale_pfx = '%s.%s.' % (SITE_CODE, today)
    stale = [name for name in os.listdir(datadir)
             if name.startswith(stale_pfx) and name.endswith('.fits')]
    if stale and StartNum == 0:
        print('> WARNING: %s 에 오늘(UT %s) 자 파일이 이미 %d 개 있다 -- '
              '덮어쓰지 않고 번호를 밀어 저장한다 (D-016)'
              % (datadir, today, len(stale)))
        print('>          폴더를 비우거나 옮기거나, StartNum 으로 이어받아라.')
        print()

    # Multiple Exposure loop
    
    nframe = StartNum
    ## 노출 루프를 try/finally 로 감싼다 -- **예외로 중간에 빠져나가도 CCD
    ## 바이어스/클록은 끈다.**  v1.0 은 감싸지 않았고, Exposure()/GetDataset()
    ## 호출부에도 try 가 없어서 예외 하나로 POWEROFF 를 건너뛴 채 traceback 으로
    ## 끝났다.  v1.1 은 예외 원인을 새로 늘렸으니(기하 대조, 재접속 실패) 여기서
    ## 막는다.  전원을 켠 채로 스크립트가 죽는 것은 검출기 쪽 위험이다.
    try:
        if TEST_REF_ENABLE:
            filenum = DatasetId*100 + nframe; nframe+=1;
            Exposure(TEST_SHOPEN, TEST_REF_EXPTIME, bWaitFlush, bFullFlush, filenum, DatasetId, datadir)
        for exptime in TEST_EXPTIMES:
            for i in range(0, TEST_FRAMENUM):
                filenum = DatasetId*100 + nframe; nframe+=1;
                Exposure(TEST_SHOPEN, exptime, bWaitFlush, bFullFlush, filenum, DatasetId, datadir)
            if TEST_DARK_ENABLE and exptime==0:
                for i in range(0, TEST_DARK_NUMBER):
                    filenum = DatasetId*100 + nframe; nframe+=1;
                    Exposure(False, TEST_DARK_EXPTIME, bWaitFlush, bFullFlush, filenum, DatasetId, datadir)
            if TEST_REF_ENABLE:
                filenum = DatasetId*100 + nframe; nframe+=1;
                Exposure(TEST_SHOPEN, TEST_REF_EXPTIME, bWaitFlush, bFullFlush, filenum, DatasetId, datadir)

    finally:
        # CCD input bias/clock power OFF
        print("> CCD input bias/clock power OFF")
        try:
            archoncmd('POWEROFF')
            time.sleep(2.0)
        except Exception as e:
            ## 여기서 또 예외를 내면 원래 원인이 가려진다 -- 알리고 넘긴다.
            print('> WARNING: POWEROFF 를 못 보냈다 (%s)' % e)
            print('>          유닛 전원 상태를 직접 확인하라.')
        print()
    
    # Finish

    #print('> [ DS%04d %sGain C%+.2fV ] dataset complete.\n\n' % (DatasetId, Gain[AmpGain], Clamp) )
    print('DS%04d dataset complete.\n' % DatasetId )
    time.sleep(1.0)

    TestRunDone += 1
    SMS_TIO_HELabAlerts( 'HELab: %s test run DS%04d (%d/%d) done'
         % (DATA_PREFIX, DatasetId, TestRunDone, TestRunNum) ); print();
    
    DatasetIdLast = DatasetId
    
    return


## Creat a directory
def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        #print ('Error: Creating directory. ' +  directory)
        print ("> ERROR: Failed to creat the directory, '%s'", directory)
    return
# 출처: https://data-make.tistory.com/170 [Data Makes Our Future]
# Usage: createFolder('/Users/aaron/Desktop/test')


## SMS sending with the Twilio messaging service
##   using a active phone number
##   since 'HELab Alerts' messaging service is not working

## ⚠️ **쓰지 않는 import 였고 리눅스에서 기동을 막았다** (2026-08-23).
## 아래 함수 본문은 통째로 주석(docstring) 처리돼 있어 `Client` 를 쓰는 코드가
## 없는데, import 는 실행되므로 twilio 가 없는 기계에서는 **스크립트가 아예
## 시작하지 못했다**(`ModuleNotFoundError`).  SMS 를 되살릴 때 그대로 쓰도록
## 형태는 남기고 없어도 넘어가게만 한다.
try:
    from twilio.rest import Client
except ImportError:
    Client = None       # SMS 를 되살릴 때 twilio 를 설치한다

def SMS_TIO_HELabAlerts(msg):
    '''
    try:
        account_sid = ''
        auth_token = '' 
        client = Client(account_sid, auth_token) 
 
        message = client.messages.create(body=msg,
                        from_='', to='')
 
        #print(message.sid)
        print("> SMS message '" + msg + "' sent via Twilio")
        print("  MessageSID: " + message.sid)

    except Exception as e:
        print("> SMS message '" + msg + "' sent via Twilio")
        print("  --> Failed (Error: %s)" % e)
    '''
    return

# Usage: SMS_TIO_HELabAlerts('메시지 전송시험 - chasm')
# ** MMS if more than 52 characters, and SMS if 52 or less


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
# Main script
#

## Check/Debugging initialization
'''
#### Check dataset configuration
SetDatasetConfig(DS_XTALK);RepDatasetConfig();print();
SetDatasetConfig(DS_DARK );RepDatasetConfig();print();
SetDatasetConfig(DS_IFLAT);RepDatasetConfig();print();
SetDatasetConfig(DS_GXT  );RepDatasetConfig();print();
sys.exit() ######## ForDBG
'''
'''
#### Check for FITS Header format (raw spec -- 144 레코드 = 4블록)
CURRENT_ACF = UNIT_ACF_SCI_FAST_MEDIUM
hb = build_spec_header(True, 12345, '2026-08-22T12:34:56.789',
                       CURRENT_ACF, 'KMTK.20260822.321101.MK',
                       'KMTK.20260822.321101.MK', 3211)
print('FITS header check (%d cards)\n' % (len(hb)//80) + '-'*80)
for i in range(len(hb)//80):
    print("%03d: %s|" % ( (i+1), hb[80*i:80+80*i] ) )
print()
sys.exit() ######## ForDBG
'''
'''
SMS_TIO_HELabAlerts('HELab: SMS messaging test for Achon UNIT %s test' % DATA_PREFIX)
sys.exit() ######## ForDBG
'''


## Check the hand-edited identity setup before touching the controller

_check_identity_setup()
print('Identity: SITE=%s  DETID=%s  CTRL%d=%s (%s)'
      % (SITE_CODE, UNIT_CTRLTAG, 1 if UNIT_CTRLTAG == 'MK' else 2,
         UNIT_CTRL_ID, UNIT_CTRL_SN))
print('          OBSERVAT=%s  ORIGIN=%s  TELESCOP=%s'
      % SITE_INFO[SITE_CODE])
print()


## Connect to Archon

print('Connecting to Archon unit #%02d ..' \
              % int(UNIT_IPADDR.split('.')[-1]), end='')

archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
archon.settimeout(UNIT_TIMEOUT)
#archon.connect(('10.0.0.2', 4242))
archon.connect((UNIT_IPADDR, 4242))
#archon.settimeout(10)
#archon.settimeout(UNIT_TIMEOUT) --> moved above connect() at v0.5.0

print(' success.')
time.sleep(0.4)
print()

SMS_TIO_HELabAlerts('HELab: %s unit test started' % DATA_PREFIX)
print()


## Data acquisition for multiple configurations
'''
#20250401 U13-xTalk/Dark-Med
TestRunNum = 3
GetDataset(UNIT_ACF_SCI_FAST_MEDIUM, False, False, 7211, 0, DATA_STORAGE)
GetDataset(UNIT_ACF_SCI_COMP_MEDIUM, False, False, 7511, 0, DATA_STORAGE)
GetDataset(UNIT_ACF_SCI_SLOW_MEDIUM, False, False, 7811, 0, DATA_STORAGE)

#20250406 U13-iFlat
TestRunNum = 3
GetDataset(UNIT_ACF_SCI_FAST_MEDIUM, False, False, 7213, 0, DATA_STORAGE)
GetDataset(UNIT_ACF_SCI_COMP_MEDIUM, False, False, 7513, 0, DATA_STORAGE)
GetDataset(UNIT_ACF_SCI_SLOW_MEDIUM, False, False, 7813, 0, DATA_STORAGE)

#20250413 U23-xTalk/Dark
TestRunNum = 3
GetDataset(UNIT_ACF_SCI_FAST_MEDIUM, False, False, 3211, 0, DATA_STORAGE)
GetDataset(UNIT_ACF_SCI_COMP_MEDIUM, False, False, 3511, 0, DATA_STORAGE)
GetDataset(UNIT_ACF_SCI_SLOW_MEDIUM, False, False, 3811, 0, DATA_STORAGE)
'''

GetDataset(UNIT_ACF_SCI_NORMAL, False, False, 2844, 0, DATA_STORAGE)


## Disconnect from Archon

print('Disconnect from Archon #%02d ..' % int(UNIT_IPADDR.split('.')[-1]))
archon.close()
print()

SMS_TIO_HELabAlerts('HELab: %s test complete. LastDID=%d / RunNum=%d' 
              % ( DATA_PREFIX, DatasetIdLast, TestRunNum ) ); print();

print('All done.\n')


#-------------------------------------------------------------------------------
# NOTES
#
'''
<ACF Lists>

  Fast/Sensitive: KMTNet_Sci_fast_sen_Uxx.acf = UNIT_ACF_SCI_FAST_SENSTV
  Fast/Medium   : KMTNet_Sci_fast_med_Uxx.acf = UNIT_ACF_SCI_FAST_MEDIUM
  Fast/LowNoise : KMTNet_Sci_fast_lon_Uxx.acf = UNIT_ACF_SCI_FAST_LONOIS

  Comp/Sensitive: KMTNet_Sci_comp_sen_Uxx.acf = UNIT_ACF_SCI_COMP_SENSTV
  Comp/Medium   : KMTNet_Sci_comp_med_Uxx.acf = UNIT_ACF_SCI_COMP_MEDIUM
  Comp/LowNoise : KMTNet_Sci_comp_lon_Uxx.acf = UNIT_ACF_SCI_COMP_LONOIS

  Slow/Sensitive: KMTNet_Sci_slow_sen_Uxx.acf = UNIT_ACF_SCI_SLOW_SENSTV
  Slow/Medium   : KMTNet_Sci_slow_med_Uxx.acf = UNIT_ACF_SCI_SLOW_MEDIUM
  Slow/LowNoise : KMTNet_Sci_slow_lon_Uxx.acf = UNIT_ACF_SCI_SLOW_LONOIS


< Dataset lists of HELab.2025.04 test >

  DS7111: AC13A / fast.sen / OD29V_R1  / xTalk / 1st
  DS7112: AC13A / fast.sen / OD29V_R1  / Dark  / 1st
  DS7121: AC13A / fast.sen / OD30V_R1  / xTalk / 1st
  DS7122: AC13A / fast.sen / OD30V_R1  / Dark  / 1st
  DS7131: AC13A / fast.sen / OD31V_R1  / xTalk / 1st
  DS7132: AC13A / fast.sen / OD31V_R1  / Dark  / 1st

  DS7211: AC13A / fast.med / OD29V_R1  / xTalk / 1st
  DS7212: AC13A / fast.med / OD29V_R1  / Dark  / 1st
  DS7221: AC13A / fast.med / OD30V_R1  / xTalk / 1st
  DS7222: AC13A / fast.med / OD30V_R1  / Dark  / 1st
  DS7231: AC13A / fast.med / OD31V_R1  / xTalk / 1st
  DS7232: AC13A / fast.med / OD31V_R1  / Dark  / 1st

  DS7311: AC13A / fast.lon / OD29V_R1  / xTalk / 1st
  DS7312: AC13A / fast.lon / OD29V_R1  / Dark  / 1st
  DS7321: AC13A / fast.lon / OD30V_R1  / xTalk / 1st
  DS7322: AC13A / fast.lon / OD30V_R1  / Dark  / 1st
  DS7331: AC13A / fast.lon / OD31V_R1  / xTalk / 1st
  DS7332: AC13A / fast.lon / OD31V_R1  / Dark  / 1st

  DS7411: AC13A / comp.sen / OD29V_R1  / xTalk / 1st
  DS7412: AC13A / comp.sen / OD29V_R1  / Dark  / 1st
  DS7421: AC13A / comp.sen / OD30V_R1  / xTalk / 1st
  DS7422: AC13A / comp.sen / OD30V_R1  / Dark  / 1st
  DS7431: AC13A / comp.sen / OD31V_R1  / xTalk / 1st
  DS7432: AC13A / comp.sen / OD31V_R1  / Dark  / 1st

  DS7511: AC13A / comp.med / OD29V_R1  / xTalk / 1st
  DS7512: AC13A / comp.med / OD29V_R1  / Dark  / 1st
  DS7521: AC13A / comp.med / OD30V_R1  / xTalk / 1st
  DS7522: AC13A / comp.med / OD30V_R1  / Dark  / 1st
  DS7531: AC13A / comp.med / OD31V_R1  / xTalk / 1st
  DS7532: AC13A / comp.med / OD31V_R1  / Dark  / 1st

  DS7611: AC13A / comp.lon / OD29V_R1  / xTalk / 1st
  DS7612: AC13A / comp.lon / OD29V_R1  / Dark  / 1st
  DS7621: AC13A / comp.lon / OD30V_R1  / xTalk / 1st
  DS7622: AC13A / comp.lon / OD30V_R1  / Dark  / 1st
  DS7631: AC13A / comp.lon / OD31V_R1  / xTalk / 1st
  DS7632: AC13A / comp.lon / OD31V_R1  / Dark  / 1st

  DS7711: AC13A / slow.sen / OD29V_R1  / xTalk / 1st
  DS7712: AC13A / slow.sen / OD29V_R1  / Dark  / 1st
  DS7721: AC13A / slow.sen / OD30V_R1  / xTalk / 1st
  DS7722: AC13A / slow.sen / OD30V_R1  / Dark  / 1st
  DS7731: AC13A / slow.sen / OD31V_R1  / xTalk / 1st
  DS7732: AC13A / slow.sen / OD31V_R1  / Dark  / 1st

  DS7811: AC13A / slow.med / OD29V_R1  / xTalk / 1st
  DS7812: AC13A / slow.med / OD29V_R1  / Dark  / 1st
  DS7821: AC13A / slow.med / OD30V_R1  / xTalk / 1st
  DS7822: AC13A / slow.med / OD30V_R1  / Dark  / 1st
  DS7831: AC13A / slow.med / OD31V_R1  / xTalk / 1st
  DS7832: AC13A / slow.med / OD31V_R1  / Dark  / 1st

  DS7911: AC13A / slow.lon / OD29V_R1  / xTalk / 1st
  DS7912: AC13A / slow.lon / OD29V_R1  / Dark  / 1st
  DS7921: AC13A / slow.lon / OD30V_R1  / xTalk / 1st
  DS7922: AC13A / slow.lon / OD30V_R1  / Dark  / 1st
  DS7931: AC13A / slow.lon / OD31V_R1  / xTalk / 1st
  DS7932: AC13A / slow.lon / OD31V_R1  / Dark  / 1st

  DS7113: AC13A / fast.sen / OD29V_R1  / iFlat / 1st
  DS7123: AC13A / fast.sen / OD30V_R1  / iFlat / 1st
  DS7133: AC13A / fast.sen / OD31V_R1  / iFlat / 1st
  DS7213: AC13A / fast.med / OD29V_R1  / iFlat / 1st
  DS7223: AC13A / fast.med / OD30V_R1  / iFlat / 1st
  DS7233: AC13A / fast.med / OD31V_R1  / iFlat / 1st
  DS7313: AC13A / fast.lon / OD29V_R1  / iFlat / 1st
  DS7323: AC13A / fast.lon / OD30V_R1  / iFlat / 1st
  DS7333: AC13A / fast.lon / OD31V_R1  / iFlat / 1st

  DS7413: AC13A / comp.sen / OD29V_R1  / iFlat / 1st
  DS7423: AC13A / comp.sen / OD30V_R1  / iFlat / 1st
  DS7433: AC13A / comp.sen / OD31V_R1  / iFlat / 1st
  DS7513: AC13A / comp.med / OD29V_R1  / iFlat / 1st
  DS7523: AC13A / comp.med / OD30V_R1  / iFlat / 1st
  DS7533: AC13A / comp.med / OD31V_R1  / iFlat / 1st
  DS7613: AC13A / comp.lon / OD29V_R1  / iFlat / 1st
  DS7623: AC13A / comp.lon / OD30V_R1  / iFlat / 1st
  DS7633: AC13A / comp.lon / OD31V_R1  / iFlat / 1st

  DS7713: AC13A / slow.sen / OD29V_R1  / iFlat / 1st
  DS7723: AC13A / slow.sen / OD30V_R1  / iFlat / 1st
  DS7733: AC13A / slow.sen / OD31V_R1  / iFlat / 1st
  DS7813: AC13A / slow.med / OD29V_R1  / iFlat / 1st
  DS7823: AC13A / slow.med / OD30V_R1  / iFlat / 1st
  DS7833: AC13A / slow.med / OD31V_R1  / iFlat / 1st
  DS7913: AC13A / slow.lon / OD29V_R1  / iFlat / 1st
  DS7923: AC13A / slow.lon / OD30V_R1  / iFlat / 1st
  DS7933: AC13A / slow.lon / OD31V_R1  / iFlat / 1st

  DS3113: AC23A / fast.sen / OD29V_R1  / iFlat / 1st
  DS3213: AC23A / fast.med / OD29V_R1  / iFlat / 1st
  DS3313: AC23A / fast.lon / OD29V_R1  / iFlat / 1st
  DS3413: AC23A / comp.sen / OD29V_R1  / iFlat / 1st
  DS3513: AC23A / comp.med / OD29V_R1  / iFlat / 1st
  DS3613: AC23A / comp.lon / OD29V_R1  / iFlat / 1st
  DS3713: AC23A / slow.sen / OD29V_R1  / iFlat / 1st
  DS3813: AC23A / slow.med / OD29V_R1  / iFlat / 1st
  DS3913: AC23A / slow.lon / OD29V_R1  / iFlat / 1st

  DS3123: AC23A / fast.sen / OD30V_R1  / iFlat / 1st
  DS3223: AC23A / fast.med / OD30V_R1  / iFlat / 1st
  DS3323: AC23A / fast.lon / OD30V_R1  / iFlat / 1st
  DS3423: AC23A / comp.sen / OD30V_R1  / iFlat / 1st
  DS3523: AC23A / comp.med / OD30V_R1  / iFlat / 1st
  DS3623: AC23A / comp.lon / OD30V_R1  / iFlat / 1st
  DS3723: AC23A / slow.sen / OD30V_R1  / iFlat / 1st
  DS3823: AC23A / slow.med / OD30V_R1  / iFlat / 1st
  DS3923: AC23A / slow.lon / OD30V_R1  / iFlat / 1st

  DS3133: AC23A / fast.sen / OD31V_R1  / iFlat / 1st
  DS3233: AC23A / fast.med / OD31V_R1  / iFlat / 1st
  DS3333: AC23A / fast.lon / OD31V_R1  / iFlat / 1st
  DS3433: AC23A / comp.sen / OD31V_R1  / iFlat / 1st
  DS3533: AC23A / comp.med / OD31V_R1  / iFlat / 1st
  DS3633: AC23A / comp.lon / OD31V_R1  / iFlat / 1st
  DS3733: AC23A / slow.sen / OD31V_R1  / iFlat / 1st
  DS3833: AC23A / slow.med / OD31V_R1  / iFlat / 1st
  DS3933: AC23A / slow.lon / OD31V_R1  / iFlat / 1st

  DS3111: AC23A / fast.sen / OD29V_R1  / xTalk / 1st
  DS3112: AC23A / fast.sen / OD29V_R1  / Dark  / 1st
  DS3211: AC23A / fast.med / OD29V_R1  / xTalk / 1st
  DS3212: AC23A / fast.med / OD29V_R1  / Dark  / 1st
  DS3311: AC23A / fast.lon / OD29V_R1  / xTalk / 1st
  DS3312: AC23A / fast.lon / OD29V_R1  / Dark  / 1st

  DS3411: AC23A / comp.sen / OD29V_R1  / xTalk / 1st
  DS3412: AC23A / comp.sen / OD29V_R1  / Dark  / 1st
  DS3511: AC23A / comp.med / OD29V_R1  / xTalk / 1st
  DS3512: AC23A / comp.med / OD29V_R1  / Dark  / 1st
  DS3611: AC23A / comp.lon / OD29V_R1  / xTalk / 1st
  DS3612: AC23A / comp.lon / OD29V_R1  / Dark  / 1st

  DS3711: AC23A / slow.sen / OD29V_R1  / xTalk / 1st
  DS3712: AC23A / slow.sen / OD29V_R1  / Dark  / 1st
  DS3811: AC23A / slow.med / OD29V_R1  / xTalk / 1st
  DS3812: AC23A / slow.med / OD29V_R1  / Dark  / 1st
  DS3911: AC23A / slow.lon / OD29V_R1  / xTalk / 1st
  DS3912: AC23A / slow.lon / OD29V_R1  / Dark  / 1st

  DS3121: AC23A / fast.sen / OD30V_R1  / xTalk / 1st
  DS3122: AC23A / fast.sen / OD30V_R1  / Dark  / 1st
  DS3221: AC23A / fast.med / OD30V_R1  / xTalk / 1st
  DS3222: AC23A / fast.med / OD30V_R1  / Dark  / 1st
  DS3321: AC23A / fast.lon / OD30V_R1  / xTalk / 1st
  DS3322: AC23A / fast.lon / OD30V_R1  / Dark  / 1st

  DS3421: AC23A / comp.sen / OD30V_R1  / xTalk / 1st
  DS3422: AC23A / comp.sen / OD30V_R1  / Dark  / 1st
  DS3521: AC23A / comp.med / OD30V_R1  / xTalk / 1st
  DS3522: AC23A / comp.med / OD30V_R1  / Dark  / 1st
  DS3621: AC23A / comp.lon / OD30V_R1  / xTalk / 1st
  DS3622: AC23A / comp.lon / OD30V_R1  / Dark  / 1st

  DS3721: AC23A / slow.sen / OD30V_R1  / xTalk / 1st
  DS3722: AC23A / slow.sen / OD30V_R1  / Dark  / 1st
  DS3821: AC23A / slow.med / OD30V_R1  / xTalk / 1st
  DS3822: AC23A / slow.med / OD30V_R1  / Dark  / 1st
  DS3921: AC23A / slow.lon / OD30V_R1  / xTalk / 1st
  DS3922: AC23A / slow.lon / OD30V_R1  / Dark  / 1st

  DS3131: AC23A / fast.sen / OD31V_R1  / xTalk / 1st
  DS3132: AC23A / fast.sen / OD31V_R1  / Dark  / 1st
  DS3231: AC23A / fast.med / OD31V_R1  / xTalk / 1st
  DS3232: AC23A / fast.med / OD31V_R1  / Dark  / 1st
  DS3331: AC23A / fast.lon / OD31V_R1  / xTalk / 1st
  DS3332: AC23A / fast.lon / OD31V_R1  / Dark  / 1st

  DS3431: AC23A / comp.sen / OD31V_R1  / xTalk / 1st
  DS3432: AC23A / comp.sen / OD31V_R1  / Dark  / 1st
  DS3531: AC23A / comp.med / OD31V_R1  / xTalk / 1st
  DS3532: AC23A / comp.med / OD31V_R1  / Dark  / 1st
  DS3631: AC23A / comp.lon / OD31V_R1  / xTalk / 1st
  DS3632: AC23A / comp.lon / OD31V_R1  / Dark  / 1st

  DS3731: AC23A / slow.sen / OD31V_R1  / xTalk / 1st
  DS3732: AC23A / slow.sen / OD31V_R1  / Dark  / 1st
  DS3831: AC23A / slow.med / OD31V_R1  / xTalk / 1st
  DS3832: AC23A / slow.med / OD31V_R1  / Dark  / 1st
  DS3931: AC23A / slow.lon / OD31V_R1  / xTalk / 1st
  DS3932: AC23A / slow.lon / OD31V_R1  / Dark  / 1st

  DS3115: AC13A / fast.sen / OD29V_R1  / GxT   / 1st
  DS3215: AC13A / fast.med / OD29V_R1  / GxT   / 1st
  DS3315: AC13A / fast.lon / OD29V_R1  / GxT   / 1st
  DS3415: AC13A / comp.sen / OD29V_R1  / GxT   / 1st
  DS3515: AC13A / comp.med / OD29V_R1  / GxT   / 1st
  DS3615: AC13A / comp.lon / OD29V_R1  / GxT   / 1st
  DS3715: AC13A / slow.sen / OD29V_R1  / GxT   / 1st
  DS3815: AC13A / slow.med / OD29V_R1  / GxT   / 1st
  DS3915: AC13A / slow.lon / OD29V_R1  / GxT   / 1st

  DS3125: AC13A / fast.sen / OD30V_R1  / GxT   / 1st
  DS3225: AC13A / fast.med / OD30V_R1  / GxT   / 1st
  DS3325: AC13A / fast.lon / OD30V_R1  / GxT   / 1st
  DS3425: AC13A / comp.sen / OD30V_R1  / GxT   / 1st
  DS3525: AC13A / comp.med / OD30V_R1  / GxT   / 1st
  DS3625: AC13A / comp.lon / OD30V_R1  / GxT   / 1st
  DS3725: AC13A / slow.sen / OD30V_R1  / GxT   / 1st
  DS3825: AC13A / slow.med / OD30V_R1  / GxT   / 1st
  DS3925: AC13A / slow.lon / OD30V_R1  / GxT   / 1st

  DS3135: AC13A / fast.sen / OD31V_R1  / GxT   / 1st
  DS3235: AC13A / fast.med / OD31V_R1  / GxT   / 1st
  DS3335: AC13A / fast.lon / OD31V_R1  / GxT   / 1st
  DS3435: AC13A / comp.sen / OD31V_R1  / GxT   / 1st
  DS3535: AC13A / comp.med / OD31V_R1  / GxT   / 1st
  DS3635: AC13A / comp.lon / OD31V_R1  / GxT   / 1st
  DS3735: AC13A / slow.sen / OD31V_R1  / GxT   / 1st
  DS3835: AC13A / slow.med / OD31V_R1  / GxT   / 1st
  DS3935: AC13A / slow.lon / OD31V_R1  / GxT   / 1st

  ------


< Dataset volume >

  Frame data size = 344MB/Frame (360,962,880 Bytes/Frame)
  xTalk dataset volume =  7.06GB/set ( 21 FITSs /  7,580,220,480 Bytes)
  Dark  dataset volume = 21.18GB/set ( 63 FITSs / 22,740,661,440 Bytes)
  iFlat dataset volume = 39.00GB/set (116 FITSs / 41,871,694,080 Bytes)

  SSD A/B volumn = 232.44 GB = 249,923,862,528 Bytes --> Free 249,587,695,616 Bytes
  > SSD/(xTalk+Dark) = 232.44/(7.06+21.18) = 8.23 --> 8 sets *
  > SSD/(Dark+iFlat) = 232.44/(21.18+39.00) = 3.86 --> 3 sets
  > SSD/xTalk = 232.44/ 7.06 = 32.92 --> 32 sets
  > SSD/Dark  = 232.44/21.18 = 10.97 --> 10 sets
  > SSD/iFlat = 232.44/39.00 =  5.96 -->  5 sets *

  C storage free = 151.1 GB on 20250406
  > C/(xTalk+Dark) = 151/(7.06+21.18) = 5.34 --> 5 sets
  > C/iFlat = 151/39.00 =  3.87 --> 3 sets

  27 setup: fast/comp/slow x sen/med/lon x 29V/30V/31V
  3 datasets: xTalk + Dark + iFlat = 67.24GB
  27 setup x 3 datasets: 27 x 67.24 = 1,815GB = 1.77TB for each Unit


< Dataset ID definition >

##
## File number for HELab.2025.03
##
##  File Number
##     1+2+1+2 digit: [UnitID(1)][TestSetup(2)][DatasetType(1)][FrameSN(2/3)]
##
##  Unit ID (1-digit)
##                1-22A / 2-22B / 3-23A / 4-23B / 
##                5-12A / 6-12B / 7-13A / 8-13B
##
##  Test Setup (2-digit) 
##    (1st place) 1x-fast.sens / 2x-fast.med / 3x-fast.lown / 
##                4x-comp.sens / 5x-comp.med / 6x-comp.lown /
##                7x-slow.sens / 8x-slow.med / 9x-slow.lown /
##                0x-other ACF for testing
##    (2nd place) x1-OD29V_R1  / x2-OD30V_R1  / x3-OD31V_R1  /
##                x4-OD29V_R2  / x5-OD30V_R2  / x6-OD31V_R2  /
##                x7-OD29V_STA / x8-OD30V_STA / x9-OD31V_STA /
##                x0-image check or other test setup w/suffix
##
##  Dataset Type(1-digit)
##                0xx: Check images
##                1xx: xTalk dataset
##                2xx: Dark dataset
##                3xx-4xx: iFlat dataset
##                5xx-9xx: reserved
##  
##  Frame SN(2-digit/3-digit)
##                000-099: xTalk/Dark
##                000-199: iFlat
##
##  Dataset ID (4-digit)
##    1+2+1 digit: [UnitID(1)][TestSetup(2)][DatasetType(1)]
##

## xTalk dataset
## with Max.LED
## Num of frame: 3 x 7 = 21 frames
## Running time: 0.3/0.4/0.4 hours (20/23/26 min; Fast/Comp/Slow)

## Dark dataset
## LED trigger disabled
## Num of frame:  3 x (16+5) = 63 frames
## Running time: 3.3/3.4/3.5 hours (Fast/Comp/Slow)

## iFlat dataset
## with new LED setup
## Num of frame: Ref(1+3+25) + Bias3x3 + Dark1x3 + Flat25x3 = 116 frames
## Running time: 1.9/2.2/2.5 hours (Fast/Comp/Slow)


<Overhead time>

>> Flushing: 11s
>> Image readout: 25.78s
>> Total readout: 37s
>> Acq overhead: 12s
>> Total overhead: 49.0s (Fast)
>> Total overhead: 58.3s (Comp)
>> Total overhead: 67.5s (Slow)


< Dataset configurations >

#### Check dataset configuration
SetDatasetConfig(DS_XTALK);RepDatasetConfig();print();
SetDatasetConfig(DS_DARK );RepDatasetConfig();print();
SetDatasetConfig(DS_IFLAT);RepDatasetConfig();print();
SetDatasetConfig(DS_GXT  );RepDatasetConfig();print();
sys.exit() ######## ForDBG

Set dataset type = xTalk
----------------------------
xTalk dataset configuration
----------------------------
  100:   0.0s shopen
  101:   0.0s shopen
  102:   0.0s shopen
  103:   1.0s shopen
  104:   1.0s shopen
  105:   1.0s shopen
  106:   4.0s shopen
  107:   4.0s shopen
  108:   4.0s shopen
  109:   0.0s shopen
  110:   0.0s shopen
  111:   0.0s shopen
  112:  16.0s shopen
  113:  16.0s shopen
  114:  16.0s shopen
  115:  32.0s shopen
  116:  32.0s shopen
  117:  32.0s shopen
  118:   0.0s shopen
  119:   0.0s shopen
  120:   0.0s shopen
----------------------------

Set dataset type = Dark
----------------------------
Dark dataset configuration
----------------------------
  200:   0.0s shclose
  201:   0.0s shclose
  202:   0.0s shclose
  203:   2.4s shclose
  204:   2.4s shclose
  205:   2.4s shclose
  206:  12.1s shclose
  207:  12.1s shclose
  208:  12.1s shclose
  209:  61.4s shclose
  210:  61.4s shclose
  211:  61.4s shclose
  212: 310.7s shclose
  213: 310.7s shclose
  214: 310.7s shclose
  215:   0.0s shclose
  216:   0.0s shclose
  217:   0.0s shclose
  218:   3.6s shclose
  219:   3.6s shclose
  220:   3.6s shclose
  221:  18.2s shclose
  222:  18.2s shclose
  223:  18.2s shclose
  224:  92.1s shclose
  225:  92.1s shclose
  226:  92.1s shclose
  227: 466.0s shclose
  228: 466.0s shclose
  229: 466.0s shclose
  230:   0.0s shclose
  231:   0.0s shclose
  232:   0.0s shclose
  233:   5.4s shclose
  234:   5.4s shclose
  235:   5.4s shclose
  236:  27.3s shclose
  237:  27.3s shclose
  238:  27.3s shclose
  239: 138.1s shclose
  240: 138.1s shclose
  241: 138.1s shclose
  242: 699.0s shclose
  243: 699.0s shclose
  244: 699.0s shclose
  245:   0.0s shclose
  246:   0.0s shclose
  247:   0.0s shclose
  248:   8.1s shclose
  249:   8.1s shclose
  250:   8.1s shclose
  251:  40.9s shclose
  252:  40.9s shclose
  253:  40.9s shclose
  254: 207.1s shclose
  255: 207.1s shclose
  256: 207.1s shclose
  257: 1048.6s shclose
  258: 1048.6s shclose
  259: 1048.6s shclose
  260:   0.0s shclose
  261:   0.0s shclose
  262:   0.0s shclose
----------------------------

Set dataset type = iFlat
----------------------------
iFlat dataset configuration
----------------------------
  300:  12.0s reference
  301:   0.0s shopen
  302:   0.0s shopen
  303:   0.0s shopen
  304:  25.0s dark
  305:  12.0s reference
  306:   1.0s shopen
  307:   1.0s shopen
  308:   1.0s shopen
  309:  12.0s reference
  310:   2.0s shopen
  311:   2.0s shopen
  312:   2.0s shopen
  313:  12.0s reference
  314:   3.0s shopen
  315:   3.0s shopen
  316:   3.0s shopen
  317:  12.0s reference
  318:   4.0s shopen
  319:   4.0s shopen
  320:   4.0s shopen
  321:  12.0s reference
  322:   5.0s shopen
  323:   5.0s shopen
  324:   5.0s shopen
  325:  12.0s reference
  326:   6.0s shopen
  327:   6.0s shopen
  328:   6.0s shopen
  329:  12.0s reference
  330:   7.0s shopen
  331:   7.0s shopen
  332:   7.0s shopen
  333:  12.0s reference
  334:   8.0s shopen
  335:   8.0s shopen
  336:   8.0s shopen
  337:  12.0s reference
  338:   9.0s shopen
  339:   9.0s shopen
  340:   9.0s shopen
  341:  12.0s reference
  342:  10.0s shopen
  343:  10.0s shopen
  344:  10.0s shopen
  345:  12.0s reference
  346:  11.0s shopen
  347:  11.0s shopen
  348:  11.0s shopen
  349:  12.0s reference
  350:  12.0s shopen
  351:  12.0s shopen
  352:  12.0s shopen
  353:  12.0s reference
  354:  13.0s shopen
  355:  13.0s shopen
  356:  13.0s shopen
  357:  12.0s reference
  358:   0.0s shopen
  359:   0.0s shopen
  360:   0.0s shopen
  361:  25.0s dark
  362:  12.0s reference
  363:  14.0s shopen
  364:  14.0s shopen
  365:  14.0s shopen
  366:  12.0s reference
  367:  15.0s shopen
  368:  15.0s shopen
  369:  15.0s shopen
  370:  12.0s reference
  371:  16.0s shopen
  372:  16.0s shopen
  373:  16.0s shopen
  374:  12.0s reference
  375:  17.0s shopen
  376:  17.0s shopen
  377:  17.0s shopen
  378:  12.0s reference
  379:  18.0s shopen
  380:  18.0s shopen
  381:  18.0s shopen
  382:  12.0s reference
  383:  19.0s shopen
  384:  19.0s shopen
  385:  19.0s shopen
  386:  12.0s reference
  387:  20.0s shopen
  388:  20.0s shopen
  389:  20.0s shopen
  390:  12.0s reference
  391:  21.0s shopen
  392:  21.0s shopen
  393:  21.0s shopen
  394:  12.0s reference
  395:  22.0s shopen
  396:  22.0s shopen
  397:  22.0s shopen
  398:  12.0s reference
  399:  23.0s shopen
  400:  23.0s shopen
  401:  23.0s shopen
  402:  12.0s reference
  403:  24.0s shopen
  404:  24.0s shopen
  405:  24.0s shopen
  406:  12.0s reference
  407:  25.0s shopen
  408:  25.0s shopen
  409:  25.0s shopen
  410:  12.0s reference
  411:   0.0s shopen
  412:   0.0s shopen
  413:   0.0s shopen
  414:  25.0s dark
  415:  12.0s reference
----------------------------

Set dataset type = GxT
----------------------------
GxT dataset configuration
----------------------------
  500:   0.0s shclose
  501:   0.0s shclose
  502:   0.0s shclose
  503:   0.0s shclose
  504:   0.0s shclose
  505:   0.0s shclose
  506:   0.0s shclose
  507:   0.0s shclose
  508:   0.0s shclose
  509:   0.0s shclose
----------------------------


<Clock timing and Sampling configuration>

FAST Timing script:

LINE71=Pixel:
LINE72=RGHIGH
LINE73=PixelFirst:
LINE74="RGHIGH; X(19)"
LINE75=RGLOW
LINE76="X; CALL HorizontalShift(HorizontalBinning)"
LINE77=PCLK
LINE78=NOPCLK
LINE79="S1LOW; X(10)"
LINE80="S3HIGH; X(10)"
LINE81="S2LOW; X(10)"
LINE82="S1HIGH; X(63)"
LINE83=SWLOW
LINE84="S3LOW; X(10)"
LINE85=SWHIGH
LINE86="S2HIGH; X(63)"
LINE87="RGHIGH; RETURN Pixel"

Fast Pixel Period:  200

Fast Sampling (sens/med/lown)
SHP1   94 /  84 /  74
SHP2  104 / 104 / 104
SHD1  170 / 160 / 150
SHD2  180 / 180 / 180


COMP Timing script:
LINE71=Pixel:
LINE72=RGHIGH
LINE73=PixelFirst:
LINE74="RGHIGH; X(19)"
LINE75=RGLOW
LINE76="X; CALL HorizontalShift(HorizontalBinning)"
LINE77=PCLK
LINE78=NOPCLK
LINE79="S1LOW; X(10)"
LINE80="S3HIGH; X(10)"
LINE81="S2LOW; X(10)"
LINE82="S1HIGH; X(88)"
LINE83=SWLOW
LINE84="S3LOW; X(10)"
LINE85=SWHIGH
LINE86="S2HIGH; X(88)"
LINE87="RGHIGH; RETURN Pixel"

Fast Pixel Period:  250

Comp Sampling (sens/med/lown)
SHP1  117 / 107 /  97
SHP2  127 / 127 / 127
SHD1  220 / 210 / 200
SHD2  230 / 230 / 230


SLOW Timing script:
LINE71=Pixel:
LINE72=RGHIGH
LINE73=PixelFirst:
LINE74="RGHIGH; X(19)"
LINE75=RGLOW
LINE76="X; CALL HorizontalShift(HorizontalBinning)"
LINE77=PCLK
LINE78=NOPCLK
LINE79="S1LOW; X(10)"
LINE80="S3HIGH; X(10)"
LINE81="S2LOW; X(10)"
LINE82="S1HIGH; X(113)"
LINE83=SWLOW
LINE84="S3LOW; X(10)"
LINE85=SWHIGH
LINE86="S2HIGH; X(113)"
LINE87="RGHIGH; RETURN Pixel"

Fast Pixel Period:  300

Slow Sampling (sens/med/lown)
SHP1  140 / 130 / 120 
SHP2  150 / 150 / 150
SHD1  270 / 260 / 250
SHD2  280 / 280 / 280




'''








#-------------------------------------------------------------------------------
#EOF

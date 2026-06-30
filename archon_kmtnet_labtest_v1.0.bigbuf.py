# archon_kmtnet_labtest_v1.0.bigbuf.py
# revised on 2025-04-18 by SMC
#
# Prev.version: archon_kmtnet_labtest_v0.9.1.gxtalk.py (2025-04-18/SMC)
# Ref.version: archon_kmtnet_stascience_modtm_imgacq_v0.3_kasi.STA0287.102.py (2026-05-29/SMC)
#

#-------------------------------------------------------------------------------
# HW / SW / Dataset Configurations
#

#--------------------------------
# Unit/Storage setup 

DATA_PREFIX = 'AC13A'   #  <---- Set this

UNIT_ID = 7  # AC13A    #  <---- Set this
UNIT_IP = '13' # AC13   #  <---- Set this

UNIT_IPADDR = '10.0.0.'+UNIT_IP
UNIT_TIMEOUT = 1

DATA_STORAGE_C = 'C:/DATA'  # C drive (OS)
DATA_STORAGE_A = 'H:/DATA'  # SSDA (USB)
DATA_STORAGE_B = 'L:/DATA'  # SSDB (USB)

#--------------------------------
# ACF lists

UNIT_ACF_SCI_FAST_MEDIUM = 'acf/KMTNet_Sci_fast_med_U'+UNIT_IP+'.acf'
UNIT_ACF_SCI_COMP_MEDIUM = 'acf/KMTNet_Sci_comp_med_U'+UNIT_IP+'.acf'
UNIT_ACF_SCI_SLOW_MEDIUM = 'acf/KMTNet_Sci_slow_med_U'+UNIT_IP+'.acf'


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

TEST_SHOPEN_GxT = False
TEST_REF_ENABLE_GxT = False
TEST_REF_EXPTIME_GxT = 0  # ms
TEST_DARK_ENABLE_GxT = False
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

import sys, os
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

DS_CHECK = 0
DS_XTALK = 1
DS_DARK  = 2
DS_IFLAT = 3
DS_GXT   = 5

AMPCFG = ('Low','High', 'Undef')

## Global variables

headbuf = ''
TestRunNum = 0
TestRunDone = 0
DatasetIdLast = 0


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
def archoncmd(cmd):
    global msgref
    archon.sendall(str.encode('>%02X%s\n' % (msgref, cmd)))
    reply = b'';
    while not (b'\n' in reply):
        if select.select([archon], [], [], 0.01)[0]:
            reply = reply + archon.recv(1)
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


## FITS Header setup for Science data
def SetHeader(ShutOpen, ExpTime, DateObs, TimeObs):
    global headbuf
    headbuf = ''; n=0;
    headbuf += '%-8s= %20s / %-47s' % ( 'SIMPLE  ',   'T', "Conform to FITS standard" ); n+=1;
    headbuf += '%-8s= %20d / %-47s' % ( 'BITPIX  ',    16, "Unsigned short data"      ); n+=1;
    headbuf += '%-8s= %20d / %-47s' % ( 'NAXIS   ',     2, "Number of axes"           ); n+=1;
    headbuf += '%-8s= %20d / %-47s' % ( 'NAXIS1  ', 19200, "Image width"              ); n+=1;   ## science image format
    headbuf += '%-8s= %20d / %-47s' % ( 'NAXIS2  ',  9400, "Image height"             ); n+=1;   ## science image format
   #headbuf += '%-8s= %20d / %-47s' % ( 'NAXIS1  ',  4224, "Image width"              ); n+=1;   ## guide image format
   #headbuf += '%-8s= %20d / %-47s' % ( 'NAXIS2  ',  1033, "Image height"             ); n+=1;   ## guide image format
    headbuf += '%-8s= %20d / %-47s' % ( 'BZERO   ', 32768, "Offset for unsigned short"); n+=1;
    headbuf += '%-8s= %20d / %-47s' % ( 'BSCALE  ',     1, "Default scaling factor"   ); n+=1;
    headbuf += '%-8s= %20.2f / %-47s' % ( 'EXPTIME ',  ExpTime/1000, "Exposure time in seconds"); n+=1;
    headbuf += '%-8s= %20d / %-47s' % ( 'SHUTOPEN', ShutOpen    , "Shutter trigger output"); n+=1;
    headbuf += '%-8s= %-20s / %-47s' % ( 'DATE-OBS',  DateObs, "Observation date(Local)"); n+=1;
    headbuf += '%-8s= %-20s / %-47s' % ( 'TIME-OBS',  TimeObs, "Observation time(Local)"); n+=1;
    headbuf += '%-80s' % 'END'; n+=1;
    headbuf += ' '*(80*(36-n))
    return


## Single exposure and writing a FITS
def Exposure(shopen, exptime, bWaitFlush, bFullFlush, filenum, prefix, datadir):

    global config, configline
    global msgref

    print('> Start for Exposure #%06d / %dms ' % (filenum, exptime))

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

    # Get date
    date = time.strftime('%Y%m%d', time.localtime(time.time()))
    dateobs = time.strftime("'%Y-%m-%d'", time.localtime(time.time()))
    timeobs = time.strftime("'%H:%M:%S'", time.localtime(time.time()))

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

    # Rebuild image data & write a FITS
    print('>> FITS writing..', end='')
    SetHeader(shopen, exptime, dateobs, timeobs)
    pixnum = int(framesize/2)
    fitsbuf = np.ndarray(shape=(pixnum,),dtype='<u2', buffer=fitsbuf)
    fitsbuf += 0x8000
    fitsbuf = fitsbuf.byteswap()
    with open('%s/%s.%s.%06d.fits' % (datadir,prefix,date,filenum), 'wb') as f:
        f.write(bytes(headbuf,'utf-8'))
        f.write(fitsbuf)
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
    global TEST_DARK_EXPTIME
    global TEST_FRAMENUM
    global TEST_EXPTIMES
    
    TEST_DATASET = DatasetType  # 0: Check 1: xTalk / 2: Dark / 3: iFlat

    if DatasetType == DS_XTALK:
        TEST_SHOPEN = TEST_SHOPEN_xTalk
        TEST_REF_ENABLE = TEST_REF_ENABLE_xTalk
        TEST_REF_EXPTIME = TEST_REF_EXPTIME_xTalk
        TEST_DARK_ENABLE = TEST_DARK_ENABLE_xTalk
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
        TEST_DARK_EXPTIME = TEST_DARK_EXPTIME_iFlat
        TEST_FRAMENUM = TEST_FRAMENUM_iFlat
        TEST_EXPTIMES = TEST_EXPTIMES_iFlat
        print("Set dataset type = iFlat")
    elif DatasetType == DS_GXT:
        TEST_SHOPEN = TEST_SHOPEN_GxT
        TEST_REF_ENABLE = TEST_REF_ENABLE_GxT
        TEST_REF_EXPTIME = TEST_REF_EXPTIME_GxT
        TEST_DARK_ENABLE = TEST_DARK_ENABLE_GxT
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
def GetDataset(AcfPath, bWaitFlush, bFullFlush, DatasetId, StartNum, DataStorage):

    global archon
    global config, configline
    global msgref
    global TestRunNum, TestRunDone
    global DatasetIdLast

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
    
    datadir = "%s/DS%04d" % (DataStorage, DatasetId)
    createFolder(datadir)

    # Multiple Exposure loop
    
    SetDatasetConfig(DatasetId%10)
    nframe = StartNum
    if TEST_REF_ENABLE:
        filenum = DatasetId*100 + nframe; nframe+=1;
        Exposure(TEST_SHOPEN, TEST_REF_EXPTIME, bWaitFlush, bFullFlush, filenum, DATA_PREFIX, datadir)
    for exptime in TEST_EXPTIMES:
        for i in range(0, TEST_FRAMENUM):
            filenum = DatasetId*100 + nframe; nframe+=1;
            Exposure(TEST_SHOPEN, exptime, bWaitFlush, bFullFlush, filenum, DATA_PREFIX, datadir)
        if TEST_DARK_ENABLE and exptime==0:
            filenum = DatasetId*100 + nframe; nframe+=1;
            Exposure(False, TEST_DARK_EXPTIME, bWaitFlush, bFullFlush, filenum, DATA_PREFIX, datadir)
        if TEST_REF_ENABLE:
            filenum = DatasetId*100 + nframe; nframe+=1;
            Exposure(TEST_SHOPEN, TEST_REF_EXPTIME, bWaitFlush, bFullFlush, filenum, DATA_PREFIX, datadir)

    # CCD input bias/clock power OFF
    
    print("> CCD input bias/clock power OFF")
    archoncmd('POWEROFF')
    time.sleep(2.0)
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

from twilio.rest import Client 

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
#### Check for FITS Header format
SetHeader(True, 12.345, "'2021-09-29'", "'12:34:56'")
print('FITS header check\n'+'-'*80)
for i in range(36):
    print("%02d: %s|" % ( (i+1), headbuf[80*i:80+80*i] ) )
print()
#sys.exit() ######## ForDBG
'''
'''
SMS_TIO_HELabAlerts('HELab: SMS messaging test for Achon UNIT %s test' % DATA_PREFIX)
sys.exit() ######## ForDBG
'''


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
GetDataset(UNIT_ACF_SCI_FAST_MEDIUM, False, False, 7211, 0, DATA_STORAGE_A)
GetDataset(UNIT_ACF_SCI_COMP_MEDIUM, False, False, 7511, 0, DATA_STORAGE_B)
GetDataset(UNIT_ACF_SCI_SLOW_MEDIUM, False, False, 7811, 0, DATA_STORAGE_A)

#20250406 U13-iFlat
TestRunNum = 3
GetDataset(UNIT_ACF_SCI_FAST_MEDIUM, False, False, 7213, 0, DATA_STORAGE_A)
GetDataset(UNIT_ACF_SCI_COMP_MEDIUM, False, False, 7513, 0, DATA_STORAGE_A)
GetDataset(UNIT_ACF_SCI_SLOW_MEDIUM, False, False, 7813, 0, DATA_STORAGE_B)
'''

#20250413 U23-xTalk/Dark
TestRunNum = 3
GetDataset(UNIT_ACF_SCI_FAST_MEDIUM, False, False, 3211, 0, DATA_STORAGE_B)
GetDataset(UNIT_ACF_SCI_COMP_MEDIUM, False, False, 3511, 0, DATA_STORAGE_B)
GetDataset(UNIT_ACF_SCI_SLOW_MEDIUM, False, False, 3811, 0, DATA_STORAGE_A)


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

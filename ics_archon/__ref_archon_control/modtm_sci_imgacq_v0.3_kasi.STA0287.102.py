#### archon_kmtnet_stascience_modtm_v0.3.kasi.STA0286.102.py / 2026-05-29
#### - original version: archon_kmtnet_stascience_modtm_v0.2.kasi.STA0286.102.py / 2026-05-28
####   & archon_kmtnet_stascience_modtm_imgacq_v0.1.kasi.STA0286.102.py / 2026-05-27
####   & archon_kmtnet_stascience_modtm_v0.2.kasi.STA0286.102.py / 2026-05-28

#### for monitoring module's temperatures
#### no notice via SMS, long interval, modified at KASI for labtest


#### v0.0
####   + CCD clock/bias power ON in initialization
####   + image acquisition in the main loop
####   + retrieve buffer base address for using bigbuffer
#### v0.1
####   - disable fits save
####   + power on routine in the main loop
#### v0.2
####   + Connecting Archon only once during initialization
####   + Mecro option to enable/disable fits save
####   + replace the unconditional power on routine with routine to check 
####     the power status and to execute unit initialization in the main loop
#### v0.3
####   + Exposure interval setting independently


#--------------------------------
# Unit/ACF/Storage configuration 

UNIT_IPADDR = '10.0.0.102'
UNIT_ACF = 'acf/kmtnet_stascience_STA0287_102_R2601.acf'

#UNIT_TIMEOUT = 1
#UNIT_TIMEOUT = 5            ####DBG@kasi/20260512
#UNIT_TIMEOUT = 1            ####DBG@kasi/20260512 with time.sleep(0.001)
UNIT_TIMEOUT = 5             ####DBG@kasi/20260512 with time.sleep(0.001)

ENABLE_FITS_SAVE = False

DIR_LOG = 'data_tvm'

INTERVAL_ACQ =  2  # sec  ####v0.2##
INTERVAL_EXP = 60  # sec  ####v0.3##
INTERVAL_LOG = 20  # sec
INTERVAL_SMS = 20  # min

## short interval
#INTERVAL_ACQ =  1  # sec
#INTERVAL_LOG =  2  # sec

TH_TM = 0.5  # threshold of change to send SMS

#--------------------------------
# Mecros

arrow = chr(int('02192',16))
bar_solid = chr(int('02588',16))
bar_shadow = chr(int('02593',16))

progbar = bar_shadow
progend = bar_solid

#-------------------------------------------------------------------------------
# Python setup

## Importing modules
import sys, os
import socket, configparser, select, time, msvcrt
import numpy as np

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


## Set one of Archon configuration
def SetConfig(key, cfg):
    global config, configline
    config[key] = cfg
    #config[key.upper().replace('\\', '/')] = cfg.replace('"', '')    
    archoncmd('WCONFIG%04X%s=%s' % (configline[key], key, config[key]))
    #print('WCONFIG%04X%s=%s' % (configline[key], key, config[key]))  ######## ForDBG
    return


## Initialize Archon Unit
def ArchonInit(IpAddr, AcfPath):

    global archon
    global config, configline
    global msgref

    UnitSN = int(IpAddr.split('.')[-1])%1000

    print('> Archon unit #%03d initialization start..' % UnitSN)

    ## Connect to Archon

    print('> Connecting to Archon unit #%03d..' % UnitSN, end='')
    try:
        archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        archon.settimeout(UNIT_TIMEOUT)
        archon.connect((IpAddr, 4242))
    except Exception as e:
        print(f'\n>> Error: Failed to connect to AC#{UnitSN:03d}')
        print(f'>> {e}\n')
        try:
            archon.close()
        except:
            pass
        archon = None
        return -1
    print(' success.')

    time.sleep(0.2)

    ## Read configuration file    

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
    
    ## Uploading configuration to memory in the unit

    #print("> Loading all the ACF to Archon unit..", end='')
    print("> Loading all the ACF to Archon unit..")    ## for progbar

    for acfretry in range(30):

        try:

            archoncmd('CLEARCONFIG')

            ref = msgref
            i = 0
            configline = {}
            for k in config.keys():
                configline[k] = i
                archonsend('WCONFIG%04X%s=%s' % (i, k, config[k]))
                i = i + 1
            msgref = ref

            i = 0
            for k in config.keys():
                archonrecv()
                if not i%20: print(end=progbar)
                time.sleep(0.005)
                i = i + 1
            # for k in config.keys():
            #     archonrecv()
            #     time.sleep(0.005)                              ####DBG@kasi/20260512
            ##  i = 0                                           ####DBG@kasi/20260512
            ##  for k in config.keys():                         ####DBG@kasi/20260512
            ##      i = i + 1                                   ####DBG@kasi/20260512
            ##      print(">> DBG: %d --> " % i, k)             ####DBG@kasi/20260512
            ##      archonrecv()                                ####DBG@kasi/20260512
            ##      #time.sleep(0.005)                          ####DBG@kasi/20260512
                
        except Exception as e:
            
            #print(" failed\n  Error:", e, '\n')
            print("\n>> Loading ACF failed\n  Error:", e, '\n')    ## for progbar
            try:
                archon.close()
            except:
                pass
            archon = None
            
            if acfretry == SWSET_ACFRETRY: 
                print("\n>> Error: Failed to write ACF into Archon!\n")                
                time.sleep(1.0)
                return -2

            for connectretry in range(30):
                time.sleep(1.0)
                if connectretry == SWSET_CONNECTRETRY: 
                    return -4
                print('> Retry to connect to AC unit #%03d..' % UnitSN, end='')
                try:
                    archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    archon.settimeout(UNIT_TIMEOUT)
                    archon.connect((IpAddr, 4242))
                except Exception as e:
                    print(f'\n>> Error: Failed to connect to AC#{UnitSN:03d}')
                    print(f'>> {e}\n')
                    try:
                        archon.close()
                    except:
                        pass
                    archon = None
                    continue
                print(' success.')
                time.sleep(1.0)
                break
                
            #print("> Retry to upload all the ACF to Archon unit..", end='')
            print("> Retry to upload all the ACF to Archon unit..")    ## for progbar
            time.sleep(0.4)
            continue  

        print(progend)
        #print(' success.')
        print(">> Loading ACF complete.")    ## for progbar
        time.sleep(1.0)
        break
    
    ## Apply configuration    
   
    print('> Appling all to the unit..', end='')

    for acfretry in range(30):
        
        try:
            
            archoncmd('APPLYALL')
            
        except Exception as e:
            
            print(" failed\n  Error: ", e, '\n')
            
            try:
                archon.close()
            except:
                pass
            archon = None
            
            if acfretry == SWSET_ACFRETRY: 
                print("\n>> Error: Failed to command 'APPLYALL' !\n")
                time.sleep(1.0)
                return -3
                
            for connectretry in range(30):
                time.sleep(1.0)
                if connectretry == SWSET_CONNECTRETRY: 
                    return -4
                print('> Retry to connect to AC unit #%03d..' % UnitSN, end='')
                try:
                    archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    archon.settimeout(UNIT_TIMEOUT)
                    archon.connect((IpAddr, 4242))
                except Exception as e:
                    print(f'\n>> Error: Failed to connect to AC#{UnitSN:03d}')
                    print(f'>> {e}\n')
                    try:
                        archon.close()
                    except:
                        pass
                    archon = None
                    continue
                print(' success.')
                time.sleep(1.0)
                break

            print('> Retry to apply all the ACF .. ', end='') 
            time.sleep(0.4)
            continue
            
        break

    time.sleep(0.4)
    print(' complete')
    time.sleep(0.8)

    # CCD clock/bias power ON

    try:
        print("> CCD clock/bias power ON..", end='')
        archoncmd('POWERON')
        for i in range(40):
            time.sleep(0.2)
            recvbuf = archoncmd('STATUS')
            STATUS_POWER = -1
            strbuf = recvbuf.decode('utf-8')
            list_status = strbuf.split()
            for status in list_status:
                splited = status.replace('/','=').split('=')
                if splited[0] == 'POWER':
                    STATUS_POWER = int(splited[1])
            if STATUS_POWER < 0:
                print('>> Error: No status of CCD Power !')
                break;
            elif STATUS_POWER == 4:
                break;
        if STATUS_POWER != 4:
            print('\n>> Error: Failed to turn CCD power on !')
            print()
            try:
                archon.close()
            except:
                pass
            archon = None
            return -6

    except Exception as e:
        print('\n>> Error: Failed to power on !')
        print('>> %s\n' % e)
        try:
            archon.close()
        except:
            pass
        archon = None
        return -5

    print(' complete')
    time.sleep(0.8)

    '''
    ## Disconnect from Archon

    archon.close()
    print('> Disconnected from Archon unit #%03d\n' % UnitSN)
    '''####v0.2##

    print()
    
    return 0


## Getting status about module temperature
def GetModTemps(IpAddr):

    global archon
    
    UnitSN = int(IpAddr.split('.')[-1])%1000
    
    ## Connect to Archon
    '''
    print('> Connecting to Archon unit #%03d..' % UnitSN, end='')
    try:
        archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        archon.settimeout(UNIT_TIMEOUT)
        archon.connect((IpAddr, 4242))
    except Exception as e:
        archon.close()
        print('\n>> Error: Failed to connect to AC#%03d\n' % UnitSN)
        return None
    print(' success.')
    time.sleep(0.2)
    '''####v0.1##
    
    if archon is None or archon.fileno() < 0:
        print('> Connecting to Archon unit #%03d..' % UnitSN, end='')
        try:
            archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            archon.settimeout(UNIT_TIMEOUT)
            archon.connect((IpAddr, 4242))
        except Exception as e:
            print(f'\n>> Error: Failed to connect to AC#{UnitSN:03d}')
            print(f'>> {e}\n')
            try:
                archon.close()
            except:
                pass
            archon = None
            return None
        print(' success.')
        time.sleep(0.2)
    ####v0.2##

    ## Get All status

    print('> Getting all status..', end='')

    try:
        recvbuf = archoncmd('STATUS')
        #print(recvbuf)  #### forDBG
    except Exception as e:
        print('\n>> Error: Failed to get TV data, disconnected from AC#%03d' % UnitSN)
        print('>> %s\n' % e)
        try:
            archon.close()
        except:
            pass
        archon = None
        return None

    #timeacq = time.strftime('%y%m%d / %H%M%S', time.localtime(time.time()))
    timeacq = time.strftime('%y%m%d / %H%M%S', time.localtime())
    print(' success.')

    ## Extract TV status

    print('> Extracting Temperature status..')

    T_BPT = T_M01 = T_M02 = T_M03 = T_M04 = 0.0
    T_M05 = T_M08 = T_M09 = T_M10 = T_M11 = 0.0
    STATUS_POWER = -1

    strbuf = recvbuf.decode('utf-8')
    list_status = strbuf.split()

    for status in list_status:
        #print( '  status: %s' % status )
        splited = status.replace('/','=').split('=')
        n = len(splited)
        if n < 3:
            if splited[0] == 'BACKPLANE_TEMP':
                print( '  BPT:  %s' % splited[1] )
                T_BP = float(splited[1])
            elif splited[0] == 'POWER':
                STATUS_POWER = int(splited[1])
            else: 
                continue
        elif splited[0] == 'MOD1':
            if splited[1] == 'TEMP':
                print( '  M01:  %s' % splited[2] )
                T_M01 = float(splited[2])
        elif splited[0] == 'MOD2':
            if splited[1] == 'TEMP':
                print( '  M02:  %s' % splited[2] )
                T_M02 = float(splited[2])
        elif splited[0] == 'MOD3':
            if splited[1] == 'TEMP':
                print( '  M03:  %s' % splited[2] )
                T_M03 = float(splited[2])
        elif splited[0] == 'MOD4':
            if splited[1] == 'TEMP':
                print( '  M04:  %s' % splited[2] )
                T_M04 = float(splited[2])
        elif splited[0] == 'MOD5':
            if splited[1] == 'TEMP':
                print( '  M05:  %s' % splited[2] )
                T_M05 = float(splited[2])
        elif splited[0] == 'MOD8':
            if splited[1] == 'TEMP':
                print( '  M08:  %s' % splited[2] )
                T_M08 = float(splited[2])
        elif splited[0] == 'MOD9':
            if splited[1] == 'TEMP':
                print( '  M09:  %s' % splited[2] )
                T_M09 = float(splited[2])
        elif splited[0] == 'MOD10':
            if splited[1] == 'TEMP':
                print( '  M10:  %s' % splited[2] )
                T_M10 = float(splited[2])
        elif splited[0] == 'MOD11':
            if splited[1] == 'TEMP':
                print( '  M11:  %s' % splited[2] )
                T_M11 = float(splited[2])

    #tStatus = (timeacq, T_BP, T_M01, T_M02, T_M03, T_M04, T_M05, T_M08, T_M09, T_M10, T_M11, STATUS_POWER)

    '''
    ## Disconnect from Archon
    
    archon.close()
    print('> Disconnected from Archon unit #%03d\n' % UnitSN)
    '''####v0.2##

    return (timeacq, T_BP, T_M01, T_M02, T_M03, T_M04, T_M05, T_M08, T_M09, T_M10, T_M11, STATUS_POWER)


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
def Exposure(shopen, exptime, bWaitFlush, bFullFlush, filenum, prefix, datadir=None):

    global msgref
    global archon

    ## Expose frame
    
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
    
    #### for DBG ##################################################
    if samplemode: framesize = 4 * framew * frameh
    else: framesize = 2 * framew * frameh
    linesize = BURST_LEN ; lines = (framesize + linesize - 1)
    #print( "\nDBG> buf = %d (0x%08X)/ frame = %d / lines = %d / linesize = %d\n" % (buf, ((buf+1) | 4) << 29, frame, lines, linesize) )
    #print( "\nDBG> buf = %d (0x%08X)/ frame = %d / lines = %d / linesize = %d\n" % (buf, (buf*3 + 10) << 28, frame, lines, linesize) )
    #print( "\nDBG> buf = %d (0x%08X)/ frame = %d / lines = %d / linesize = %d\n" % (buf, ((buf^1)*3 + 10) << 28, frame, lines, linesize) )
    print( "\nDBG> buf = %d (0x%08X)/ frame = %d / lines = %d / linesize = %d\n" % (buf, baseaddr, frame, lines, linesize) )
    #archon.close(); return  ## for debug about digbuffer
    ################################################################

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
    if ENABLE_FITS_SAVE:
        print('>> FITS writing..', end='')
        SetHeader(shopen, exptime, dateobs, timeobs)
        pixnum = int(framesize/2)
        fitsbuf = np.ndarray(shape=(pixnum,),dtype='<u2', buffer=fitsbuf)
        fitsbuf += 0x8000
        fitsbuf = fitsbuf.byteswap()
        if datadir is None: datadir = '.'
        with open('%s/%s.%s.%06d.fits' % (datadir,prefix,date,filenum), 'wb') as f:
            f.write(bytes(headbuf,'utf-8'))
            f.write(fitsbuf)
        print(' complete')

    # Wait for extra flush
    if bWaitFlush: 
        print(">> Waiting for flushing more: ", end='')
        for ii in range(14):
            time.sleep(0.5); print(end=progbar);
        print(progend)
          
    print()

    return


#-------------------------------------------------------------------------------
# Utilities
#

## Creat a directory
def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        #print ('Error: Creating directory. ' +  directory)
        print ("> ERROR: Failed to creat the directory, '%s'\n", directory)
    return
# 출처: https://data-make.tistory.com/170 [Data Makes Our Future]
# Usage: createFolder('/Users/aaron/Desktop/test')

'''
## SMS sending with the Twilio messaging service
##   using a active phone number
##   since 'HELab Alerts' messaging service is not working

from twilio.rest import Client 

def SMS_TIO_HELabAlerts(msg):
    try:
        account_sid = ''
        auth_token = '' 
        client = Client(account_sid, auth_token) 
        # NOTE: credentials and phone numbers were redacted (2026-08-28)
        #       -- GitHub secret scanning rejected the push.  The real
        #       values live only in the operator's working copy.  This
        #       whole block is inside a disabled triple-quoted section.
 
        message = client.messages.create(body=msg,
                        from_='', to='')
 
        #print(message.sid)
        print("> SMS message '" + msg + "' sent via Twilio")
        print("  MessageSID: " + message.sid)

    except Exception as e:
        print("> SMS message '" + msg + "' sent via Twilio")
        print("  --> Failed (Error: %s)" % e)

    return

# Usage: SMS_TIO_HELabAlerts('메시지 전송시험 - chasm')
# ** SMS if 52 or less, and MMS if more than 52 characters on trial account
# ** SMS if 90 or less, and MMS if more than 90 characters on primumdtrial account
'''

#-------------------------------------------------------------------------------
# Main script
#

FlagNotice = True
TimePreSms = 0
TimePreLog = 0
TimePreExp = 0
running = True

UnitSN = int(UNIT_IPADDR.split('.')[-1])%1000
tStatusPrev = ('', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)  # 12 elements (index: 0-11)


nRtn = ArchonInit(UNIT_IPADDR, UNIT_ACF)
if nRtn < 0:
    print('\nQuit script.\n')
    sys.exit()




createFolder(DIR_LOG)
PathLog = "%s/modtm.sci.102.log" % DIR_LOG
DirFits = "%s/fits.sci.102" % DIR_LOG
DATA_PREFIX = "sci.102"
createFolder(DirFits)

while running:
    
    TimeCur = time.time()
    
    tStatus = GetModTemps(UNIT_IPADDR)
    
    if tStatus == None:
        if FlagNotice:
            FlagNotice = False
            ###SMS_TIO_HELabAlerts('HELab: Failed to get ModTemp status!')
            print('> Error: Failed to get ModTemp status!\n')
    else:        
        FlagNotice = True

        strLog = '%s / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %d' % tStatus
        print('> Log: ' + strLog + '\n' )

        ElapsedLog = (TimeCur-TimePreLog)  # sec
        if ElapsedLog > INTERVAL_LOG:
            TimePreLog = TimeCur
            with open(PathLog, 'a') as f:
                f.write(strLog+'\n')

        ElapsedSms = (TimeCur-TimePreSms)/60.0  # min
        if ElapsedSms > INTERVAL_SMS:
            TimePreSms = TimeCur
            if abs( tStatus[1] -tStatusPrev[1] )>TH_TM or \
               abs( tStatus[2] -tStatusPrev[2] )>TH_TM or \
               abs( tStatus[3] -tStatusPrev[3] )>TH_TM or \
               abs( tStatus[4] -tStatusPrev[4] )>TH_TM or \
               abs( tStatus[5] -tStatusPrev[5] )>TH_TM or \
               abs( tStatus[6] -tStatusPrev[6] )>TH_TM or \
               abs( tStatus[7] -tStatusPrev[7] )>TH_TM or \
               abs( tStatus[8] -tStatusPrev[8] )>TH_TM or \
               abs( tStatus[9] -tStatusPrev[9] )>TH_TM or \
               abs( tStatus[10]-tStatusPrev[10])>TH_TM :
                tStatusPrev = tStatus
             ###SMS_TIO_HELabAlerts(strLog);print()

        # check CCD power status
        if tStatus[11] < 0:
            print('> Error: No status of CCD Power !')
        elif tStatus[11] == 0:
            print('> Warning: Unknown status of CCD Power')
        elif tStatus[11] != 4:
            print('> Archon Config and CCD Power are not ready..\n')
            nRtn = ArchonInit(UNIT_IPADDR, UNIT_ACF)
            if nRtn < 0:
                print('Warning: Failed to initialize Archon unit #%03d\n' % UnitSN)
                time.sleep(1)
                continue

        # exposure process intervally
        ElapsedExp = (TimeCur-TimePreExp)  # sec
        if ElapsedExp > INTERVAL_EXP:
            #TimePreExp = TimeCur
            time.sleep(1)
            try:
                Exposure(False, 1000, False, False, int(tStatus[0][9:15]), DATA_PREFIX, DirFits)
                ## def Exposure(shopen, exptime, bWaitFlush, bFullFlush, filenum, prefix, datadir=None)
            except Exception as e:
                print('\n>> Exposure process was interrupted due to an unexpected problem !')
                print('>> %s\n' % e)
            TimePreExp = time.time()

    time.sleep(INTERVAL_ACQ)
    '''
    start = time.time()
    while time.time() - start < INTERVAL_ACQ:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            # 특수키 처리 (방향키/F키 등)
            if key in (b'\x00', b'\xe0'):
                msvcrt.getch()
                continue
            # ESC
            if key == b'\x1b':
                print('> ESC pressed.')
                running = False
                break
            else:
                try:
                    print(f'> Key pressed: {key.decode()}')
                except:
                    print(f'> Key pressed: {key}')
        time.sleep(0.02)
    ''' ## in CMD console or PowerShell, this should work, but doesn't work in IDLE Shell

## Disconnect from Archon

try:
    archon.close()
except:
    pass
archon = None

print('> Disconnected from Archon Science #%03d\n' % UnitSN)

## Finish script

print('Quit script.\n')


#-------------------------------------------------------------------------------
#EOF

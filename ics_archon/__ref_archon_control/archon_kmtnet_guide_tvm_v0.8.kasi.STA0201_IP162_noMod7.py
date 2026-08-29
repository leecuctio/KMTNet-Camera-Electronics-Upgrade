#### archon_kmtnet_guide_tvm_v0.9.kasi.STA0201_IP162_noMod7.py / 2026-08-14
#### - original version: archon_kmtnet_guide_modtm_v0.2.kasi.STA0291.py / 2026-05-28
####                   & archon_kmtnet_guide_tvm_v0.7.nn.kasi.STA0291.py / 2026-05-13

#### for monitoring Vacuum, RTDs, and Module's temperatures
#### no notice via SMS, long interval, modified at KASI for labtest

#### v0.8: GetModTemps()--> GetTVnModTemps() modified for RTDs and Vacuum reading with only one HeaterX
#### 



#--------------------------------
# Unit/ACF/Storage configuration 

UNIT_IPADDR = '10.0.0.162'
#UNIT_ACF = 'acf/kmtnet_guide_STA0201_162_R2601_for1110.acf'
UNIT_ACF = 'acf/kmtnet_guide_STA0201_162_R2601_for1259.acf'


#UNIT_TIMEOUT = 1
#UNIT_TIMEOUT = 5            ####DBG@kasi/20260512
#UNIT_TIMEOUT = 1            ####DBG@kasi/20260512 with time.sleep(0.001)
UNIT_TIMEOUT = 5             ####DBG@kasi/20260512 with time.sleep(0.001)

DIR_LOG = 'data_tvm'

#INTERVAL_ACQ =  5  # sec
INTERVAL_ACQ =  2  # sec  ####v0.2##
INTERVAL_LOG = 20  # sec
INTERVAL_SMS = 20  # min

## short interval
#INTERVAL_ACQ =  1  # sec
#INTERVAL_LOG =  2  # sec

## threshold of change to send SMS
TH_VC = 0.002
TH_TR = 0.2
TH_TM = 0.5

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
    #print('DBG> %02X %s' % (msgref, cmd))
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
    samplemode = int(framestatus['BUF%dSAMPLE' % (newestbuf + 1)])
    return (newestframe, newestbuf, framew, frameh, samplemode)


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
    global TestRunNum, TestRunDone
    global DatasetIdLast

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

    '''
    ## Disconnect from Archon

    archon.close()
    print('> Disconnected from Archon unit #%03d\n' % UnitSN)
    '''####v0.2##

    return 0


## Getting status about module temperature
def GetTVnModTemps(IpAddr):

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

    T_BPT = T_M03 = T_M04 = T_M05 = T_M06 = T_M09 = T_M10 = 0.0     #### T_BPT = T_M03 = T_M04 = T_M05 = T_M06 = T_M07 = T_M09 = T_M10 = 0.0
    T_M10_A = T_M10_B = T_M10_C = 0.0 ; vacuum = 1.0 ; str_vacuum = ''

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
            else: 
                continue
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
        elif splited[0] == 'MOD6':
            if splited[1] == 'TEMP':
                print( '  M06:  %s' % splited[2] )
                T_M06 = float(splited[2])
        elif splited[0] == 'MOD9':
            if splited[1] == 'TEMP':
                print( '  M09:  %s' % splited[2] )
                T_M09 = float(splited[2])
        elif splited[0] == 'MOD10':
            #print( '  MOD10 status: %s -- %s -- %s' % (splited[0],splited[1],splited[2]) )
            if splited[1] == 'TEMP':
                print( '  M10:  %s' % splited[2] )
                T_M10 = float(splited[2])
            elif splited[1] == 'TEMPA':
                print( '  TA_RTD9_DMP      :  %s' % splited[2] )
                T_M10_A = float(splited[2])
            elif splited[1] == 'TEMPB':
                print( '  TB_RTD5_WB(TBC)  :  %s' % splited[2] )
                T_M10_B = float(splited[2])
            elif splited[1] == 'TEMPC':
                print( '  TC_RTD8_CCD1(TBC):  %s' % splited[2] )
                T_M10_C = float(splited[2])
            elif len(splited[1])==12 and splited[1][:11]=='VCPU_OUTREG':
                #print( ' VCPU %s' % splited[2] )
                if splited[1][11:12]=='9':
                    print( '  Mod10 VACUUM %s' % str_vacuum )
                    #vacuum = float(str_vacuum)
                    try: vacuum = float(str_vacuum)
                    except Exception as e: vacuum = 9.99e+99;
                    if vacuum==0.0: vacuum = 8.88e+88
                else:
                    str_vacuum += chr(int(splited[2]))

    #tStatus = (timeacq, vacuum, T_M10_A, T_M10_B, T_M10_C, T_BP, T_M03, T_M04, T_M05, T_M06, T_M09, T_M10)


    '''
    ## Disconnect from Archon
    
    archon.close()
    print('> Disconnected from Archon unit #%03d\n' % UnitSN)
    '''####v0.2##

    return (timeacq, vacuum, T_M10_A, T_M10_B, T_M10_C, T_BP, T_M03, T_M04, T_M05, T_M06, T_M09, T_M10)


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
        # NOTE: credentials and phone numbers were redacted (2026-08-27)
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
running = True

tStatusPrev = ('', 1.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

nRtn = ArchonInit(UNIT_IPADDR, UNIT_ACF)
if nRtn < 0:
    print('\nQuit script.\n')
    sys.exit()

####print('> Waiting for vacuum gauge power on..\n' )
####time.sleep(12)   ## disabled at _goff_ version

createFolder(DIR_LOG)
PathLog = "%s/tvm.gui.log" % DIR_LOG

while running:
    
    TimeCur = time.time()
    
    tStatus = GetTVnModTemps(UNIT_IPADDR)
    # tStatus: (timeacq, vacuum, T_M10_A, T_M10_B, T_M10_C, T_BP, T_M03, T_M04, T_M05, T_M06, T_M09, T_M10)
    
    if tStatus == None:
        if FlagNotice:
            FlagNotice = False
            ###SMS_TIO_HELabAlerts('HELab: Failed to get ModTemp status!')
            print('> Error: Failed to get ModTemp status!\n')
    else:        
        FlagNotice = True

        strLog = '%s / %.2e / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f' % tStatus
        print('> Log: ' + strLog + '\n' )

        ElapsedLog = (TimeCur-TimePreLog)  # sec
        if ElapsedLog > INTERVAL_LOG:
            TimePreLog = TimeCur
            with open(PathLog, 'a') as f:
                f.write(strLog+'\n')

        ElapsedSms = (TimeCur-TimePreSms)/60.0  # min
        if ElapsedSms > INTERVAL_SMS:
            TimePreSms = TimeCur
            if abs( tStatus[1] / tStatusPrev[1] - 1)>TH_VC or \
               abs( tStatus[2] - tStatusPrev[2] )>TH_TR or \
               abs( tStatus[3] - tStatusPrev[3] )>TH_TR or \
               abs( tStatus[4] - tStatusPrev[4] )>TH_TR or \
               abs( tStatus[5] - tStatusPrev[5] )>TH_TM or \
               abs( tStatus[6] - tStatusPrev[6] )>TH_TM or \
               abs( tStatus[7] - tStatusPrev[7] )>TH_TM or \
               abs( tStatus[8] - tStatusPrev[8] )>TH_TM or \
               abs( tStatus[9] - tStatusPrev[9] )>TH_TM or \
               abs( tStatus[10]- tStatusPrev[10])>TH_TM :
                tStatusPrev = tStatus
             ###SMS_TIO_HELabAlerts(strLog);print()


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

print('> Disconnected from Archon Guide #%03d\n' % UnitSN)

## Finish script

print('Quit script.\n')


#-------------------------------------------------------------------------------
#EOF

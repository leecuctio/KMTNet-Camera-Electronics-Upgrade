#### archon_kmtnet_guide_tvm_goff_v0.7.nn.kasi.STA0291.py / 2026-05-13
#### - original version: archon_kmtnet_guide_tvm_v0.6.nn.sso.py / 2026-02-08
####     & archon_kmtnet_guide_tvm_v0.7.nn.kasi.STA0291.py / 2026-05-13

#### gauge off in initialization with _goff_ ACF
#### no notice via SMS, long interval, modified at KASI for labtest



#--------------------------------
# Unit/ACF/Storage configuration 

UNIT_IPADDR = '10.0.0.103'
UNIT_ACF = 'acf/kmtnet_guide_STA0291_103_goff_R2601_for1259.acf'

#UNIT_TIMEOUT = 1
#UNIT_TIMEOUT = 5            ####DBG@kasi/20260512
#UNIT_TIMEOUT = 1            ####DBG@kasi/20260512 with time.sleep(0.001)
UNIT_TIMEOUT = 5             ####DBG@kasi/20260512 with time.sleep(0.001)

DIR_LOG = 'data_tvm'

INTERVAL_ACQ =  5  # sec
INTERVAL_LOG = 20  # sec
INTERVAL_SMS = 20  # min

## short interval
#INTERVAL_ACQ =  1  # sec
#INTERVAL_LOG =  2  # sec

#-------------------------------------------------------------------------------
# Python setup

## Importing modules
import sys, os
import socket, configparser, select, time

IDX_TT = 0
IDX_VACUM = 1
IDX_M10TA = 2
IDX_M10TB = 3
IDX_M10TC = 4
IDX_M10TM = 5
IDX_M07TA = 6
IDX_M07TB = 7
IDX_M07TC = 8
IDX_M07TM = 9

TH_VC = 0.002
TH_TA = 0.2
TH_TB = 0.2
TH_TC = 0.2
TH_TM = 0.5


#-------------------------------------------------------------------------------
# Archon control code
#

## Software setting for Archon control
SWSET_ACFRETRY = 5

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

    print('> Archon #%03d initialization Start..' % UnitSN)

    ## Connect to Archon

    print('> Connecting to Archon Guide #%03d..' % UnitSN, end='')
    try:
        archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        archon.settimeout(UNIT_TIMEOUT)
        archon.connect((IpAddr, 4242))
    except Exception as e:
        archon.close()
        print('\n>> Error: Failed to connect to AC#%03d\n' % UnitSN)
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
    
    ## Set configuration to memory

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
                time.sleep(0.005)                              ####DBG@kasi/20260512
            #  i = 0                                           ####DBG@kasi/20260512
            #  for k in config.keys():                         ####DBG@kasi/20260512
            #      i = i + 1                                   ####DBG@kasi/20260512
            #      print(">> DBG: %d --> " % i, k)             ####DBG@kasi/20260512
            #      archonrecv()                                ####DBG@kasi/20260512
            #      #time.sleep(0.005)                          ####DBG@kasi/20260512
                
        except Exception as e:
            print(" failed\n  Error:", e, '\n')
            archon.close()
            if acfretry == SWSET_ACFRETRY: 
                print("\n>> Error: Failed to write ACF into Archon!\n")
                archon.close()
                return -2
            time.sleep(0.8)
            print('> Retry to connect to AC unit #%03d..' % UnitSN, end='')
            archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            archon.settimeout(UNIT_TIMEOUT)
            archon.connect((IpAddr, 4242))
            print(' success.')        
            time.sleep(2.0)
            continue
        
        break
    
    ## Apply configuration    
   
    for acfretry in range(30):
        try:
            archoncmd('APPLYALL')
        except Exception as e:
            print(" failed\n  Error: ", e, '\n')
            archon.close()
            if acfretry == SWSET_ACFRETRY: 
                print("\n>> Error: Failed to command 'APPLYALL' !\n")
                archon.close()
                return -3
            time.sleep(0.8)
            print('> Retry to connect to AC unit #%03d..' % UnitSN, end='')
            archon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            archon.settimeout(UNIT_TIMEOUT)
            archon.connect((IpAddr, 4242))
            print(' success.')
            time.sleep(2.0)
            print('> Retry to apply all the ACF .. ', end='') 
            continue
            
        break

    print(' complete')

    ## Disconnect from Archon

    archon.close()
    print('> Disconnected from Archon Guide #%03d\n' % UnitSN)

    return 0


## Getting thermal/vacuum status
def GetTVstatus(IpAddr):

    global archon
    
    UnitSN = int(IpAddr.split('.')[-1])%1000
    
    ## Connect to Archon

    print('> Connecting to Archon Guide #%03d..' % UnitSN, end='')
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

    ## Get All status

    print('> Getting all status..', end='')

    try:
        recvbuf = archoncmd('STATUS')
        #print(recvbuf)  #### forDBG
    except Exception as e:
        archon.close()
        print('\n>> Error: Failed to get TV data, disconnected from AC#%03d\n' % UnitSN)
        return None


    timeacq = time.strftime('%y%m%d / %H%M%S', time.localtime(time.time()))
    print(' success.')

    ## Extract TV status

    print('> Extracting TV status..')

    m10_temp_m = m10_temp_a = m10_temp_b = m10_temp_c = 0.0
    m07_temp_m = m07_temp_a = m07_temp_b = m07_temp_c = 0.0
    vacuum = 1.0
    str_vacuum = ''

    #keyword = b'MOD10/TEMPA'
    #idx = recvbuf.find(keyword)
    #keyword = 'MOD10/TEMPA'
    strbuf = recvbuf.decode('utf-8')
    list_status = strbuf.split()

    for status in list_status:
        #print( '  status: %s' % status )
        splited = status.replace('/','=').split('=')
        n = len(splited)
        if n < 3:
            continue
        elif splited[0] == 'MOD7':
            #print( '  MOD10 status: %s -- %s -- %s' % (splited[0],splited[1],splited[2]) )
            if splited[1] == 'TEMP':
                print( '  Mod07 TEMP_M  MODULE_TEMP    %s' % splited[2] )
                m07_temp_m = float(splited[2])
            elif splited[1] == 'TEMPA':
                print( '  Mod07 TEMP_A  RTD1_PT30-1    %s' % splited[2] )
                m07_temp_a = float(splited[2])
            elif splited[1] == 'TEMPB':
                print( '  Mod07 TEMP_B  RTD4_REALDEAL  %s' % splited[2] )
                m07_temp_b = float(splited[2])
            elif splited[1] == 'TEMPC':
                print( '  Mod07 TEMP_C  RTD3_PT30-2    %s' % splited[2] )
                m07_temp_c = float(splited[2])
        elif splited[0] == 'MOD10':
            #print( '  MOD10 status: %s -- %s -- %s' % (splited[0],splited[1],splited[2]) )
            if splited[1] == 'TEMP':
                print( '  Mod10 TEMP_M  MODULE_TEMP    %s' % splited[2] )
                m10_temp_m = float(splited[2])
            elif splited[1] == 'TEMPA':
                print( '  Mod10 TEMP_A  RTD9_DMP       %s' % splited[2] )
                m10_temp_a = float(splited[2])
            elif splited[1] == 'TEMPB':
                print( '  Mod10 TEMP_B  RTD8_NC        %s' % splited[2] )
                m10_temp_b = float(splited[2])
            elif splited[1] == 'TEMPC':
                print( '  Mod10 TEMP_C  RTD5_CHARCOAL  %s' % splited[2] )
                m10_temp_c = float(splited[2])
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

    #tStatus = (timeacq, vacuum, m10_temp_a, m10_temp_b, m10_temp_c, m10_temp_m, m07_temp_a, m07_temp_b, m07_temp_c, m07_temp_m)

    ## Disconnect from Archon
    
    archon.close()
    print('> Disconnected from Archon Guide #%03d\n' % UnitSN)

    return (timeacq, vacuum, m10_temp_a, m10_temp_b, m10_temp_c, m10_temp_m, m07_temp_a, m07_temp_b, m07_temp_c, m07_temp_m)


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
        account_sid = '<redacted>'
        auth_token = '<redacted>' 
        client = Client(account_sid, auth_token) 
        # NOTE: credentials and phone numbers were redacted (2026-08-28)
        #       -- GitHub secret scanning rejected the push.  The real
        #       values live only in the operator's working copy.  This
        #       whole block is inside a disabled triple-quoted section.
 
        message = client.messages.create(body=msg,
                        from_='<redacted>', to='<redacted>')
 
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

tStatusPrev = ('', 1, 0, 0, 0, 0, 0, 0, 0, 0)

nRtn = ArchonInit(UNIT_IPADDR, UNIT_ACF)
if nRtn < 0:
    print('\nQuit script.\n')
    sys.exit()


#print('> Waiting for vacuum gauge power on..\n' )
#time.sleep(12)   ## disabled at _goff_ version


createFolder(DIR_LOG)
PathLog = "%s/tvm.gui.log" % DIR_LOG

while True:
    
    TimeCur = time.time()
    
    tStatus = GetTVstatus(UNIT_IPADDR)
    
    if tStatus == None:
        if FlagNotice:
            FlagNotice = False
            ###SMS_TIO_HELabAlerts('HELab: Failed to get TVM status!')
            print('> Error: Failed to get TVM status!')
    else:        
        FlagNotice = True

        strLog = '%s / %.2e / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f / %+6.1f' % tStatus
        print('> Report: ' + strLog + '\n' )

        ElapsedLog = (TimeCur-TimePreLog)  # sec
        if ElapsedLog > INTERVAL_LOG:
            TimePreLog = TimeCur
            with open(PathLog, 'a') as f:
                f.write(strLog+'\n')

        ElapsedSms = (TimeCur-TimePreSms)/60.0  # min
        if ElapsedSms > INTERVAL_SMS:
            TimePreSms = TimeCur
            if abs(tStatus[IDX_VACUM]/tStatusPrev[IDX_VACUM]-1)>TH_VC or \
               abs(tStatus[IDX_M10TA]-tStatusPrev[IDX_M10TA]  )>TH_TA or \
               abs(tStatus[IDX_M10TB]-tStatusPrev[IDX_M10TB]  )>TH_TB or \
               abs(tStatus[IDX_M10TC]-tStatusPrev[IDX_M10TC]  )>TH_TC or \
               abs(tStatus[IDX_M10TM]-tStatusPrev[IDX_M10TM]  )>TH_TM or \
               abs(tStatus[IDX_M07TA]-tStatusPrev[IDX_M07TA]  )>TH_TA or \
               abs(tStatus[IDX_M07TB]-tStatusPrev[IDX_M07TB]  )>TH_TB or \
               abs(tStatus[IDX_M07TC]-tStatusPrev[IDX_M07TC]  )>TH_TC or \
               abs(tStatus[IDX_M07TM]-tStatusPrev[IDX_M07TM]  )>TH_TM :
                tStatusPrev = tStatus
             ###SMS_TIO_HELabAlerts(strLog);print()

    time.sleep(INTERVAL_ACQ)



print('\nAll done.\n')


#-------------------------------------------------------------------------------
#EOF

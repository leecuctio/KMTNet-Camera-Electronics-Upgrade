#ifndef OBSTOOL_H
#define OBSTOOL_H

//------------------------------------------------------------------------------
//
// Main OBS Agent header file
//
// Defaults and definitions below are defined for the KMTNet system
// 
// Author: 
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2003 Feb 1 (TCSAgent original version - agent pctcs for Yale1m v3.3.1)
//
//   S. Cha, KASI KMTNet team
//   chasm@kasi.re.kr
//   2014 Apr  1 (TCSAgent KMTNet version)
//   2016 Sep 20 (OBSAgent for KMTNet system)
//
// Modification History:
//   2016 Sep 20: OBSAgent v0.0 re-creation re-using TCSAgent flatform and code [sc/kasi]
//   2017 Aug 07: Replaced old code with new improved code of TCSAtgent v1.6.6 (v0.0.4)
//                Added a defalut value for time tag display option (v0.0.5)
//   2017 Aug 20: Removed codes and comments regarding TCS/AUX from TCSAgent (v0.0.6)
//   2017 Dec 22: Observation script structure modification (v0.0.7)
//   2017 Dec 26: Observation system status and data structure (v0.0.8)
//   2018 Jan 03: Obs system / Obs script / Agent structure modification (v0.0.9-v0.2.2)
//   2018 Jan 12: TCS limit information included in Observation system structure (v0.2.6)
//   2019 May 03: flat_fsaerror added in Observation system structure (v0.3.4) 
//   2020 Jul 27: flag_warning, count_warning, interval_warning added in OBSAgent structure,
//                and WARNING_BLINK_.. Warning blinking interval settings configured (v0.3.5)
//   2020 Sep 18: tcs_latitude/longitude/elevation included in Observation system structure (v0.4.0)
//   2020 Sep 19: tcs_tolerance included in Observation system structure (v0.4.1)
//   2020 Sep 23: tcs_tolerance replaced with tcs_tolerance_pointing & tcs_tolerance_tracking, 
//                and threshold_tracking included in Observation system structure (v0.4.2)
//   2020 Oct 08: CAMSTATUS_READY added for camstatus of Observation system structure(system_config), 
//                count_ready & force_ready added in Observation system structure (v0.4.5)
//   2020 Oct 12: flag_tcswarning_nearlimit added in Observation system structure, 
//                OSC_ADJ_TOL_POINTING added for (v0.4.5)
//   2020 Nov 26: flag_override_tcsconnection added in Observation system structure (v0.4.9)
//   2020 Nov 27: max_object_length added in obsscript structure (v0.5.0)
//   2020 Dec 01: flag_override_isisconnection added in OBSAgent configuration structure (v0.5.0)
//   2021 Mar 05: ECMD_DLAMP mecros & ecmd_dlamp strings in OBSAgent configuration structure 
//                for domeflat lamp relay control with external command line execution,
//                ECMD_MCFAN mecros & ecmd_mcfan strings in OBSAgent configuration structure 
//                for mirror cell fan relay control with external command line execution (v0.5.1)
//   2021 Mar 09: ECMD_DTCHK added for 'dtchk' command, TELID & IPADDR mecros added,
//                flag_delay/count_delay added in OSC structure (v0.5.2)
//   2021 Apr 08: ProjID included in Observation system structure, CMDBIT/CHKBIT definition and 
//                flag_projidcommanded added for ProjID process (v0.6.4)
//   2021 Apr 08: OSC_CHKCNT_CMDRETRY & count_cmdretry added (v0.6.5)
//   2021 Jun 21: ics_datasource setting added in Observation system structure (v0.6.6)
//   2022 Jul 12: relay configurations & commands added in Observation system structure, 
//                mecro for external commands modification for Web relay commandes, 
//                mecros for default relay configuration (v0.6.8)
//   2022 Jul 13: secse(sec since epoch) in obsscript_line, copt type: char --> string (v0.7.0)
//   2022 Jul 15: cmd_velra/cmd_veldec/timestamp_tmr added in the system structure (v0.7.5)
//   2022 Jul 18: member values for dome status & curl redirecture in the system structure (v0.7.8)
//   2022 Aug 12: flat_additionalshot added in the OSC structure (v0.8.0)
//   2022 Aug 26: OSC_DEFAULT_PREPSEC/READSEC adjusted, found that optimized UT_TOL should be UT_OBS_INT/2 (v0.8.3)
//   2022 Aug 27: OSC_MINIMUM_UTTOL/OSC_DEFAULT_UTTOL adjusted (v0.8.4)
//   2022 Aug 29: default Web relay XML port numbers definitions (v0.8.5)
//                default TCS paddle mode at SSO changed to GUIDE (v0.8.6)
//                default spec definition and update, and member variables added in Obs.system structure 
//                for slewing speed, settling down time, dome rotating speed, and dome shut speed (v0.8.7)
//   2022 Oct 06: declaration of functions in commands.c checked/modified, calculation function included (v0.8.8)
//   2022 Oct 07: declaration of functions for astronomical/numerical calculation in calculation.c (v0.8.9)
//   2023 Feb 21: Add new members, unstable_ra/dec/axis, tpfailed_axis and flag_tcswarning_oscinexp, into system_config (v0.9.0)
//   2023 Mar 03: Append new default config DEFAULT_TCS_ALLOWANCE_UNSTABLE for system_config(obssystem_t) structure (v0.9.1)
//   2024 Jun 18: Define mecros for Dome Status, Add domeshutstatus & relay_dctrl_failnum into system_config,
//                Append default on mecro definition and add members in system_config for redis server configuration (v0.9.3)
//   2024 Jun 20: Append new default config for Redis values and error handling for Dome status monitoring
//                (REDIS_DOMEROT_POSITIONED/ROTATING/UNKNOWN & REDIS_DOMESHUT_POSITIONED/MOVING/UNKNOWN, DEFAULT_REDIS_ERRTH_DOMEROT/DOMESHUT), 
//                Add new members for monitoring and importing dome status for Redis, Relay, Aux DS into system_config (v0.9.4)
//   2024 Jun 24: Refactory definitions for relay commands (v0.9.6)
//   2024 Jun 26: Append new default config for Maximum operation time for dome rotation/shutter (DEFAULT_DOME_ERRTH_WAITROT/WAITSHUT) (v0.9.8)
//   2024 Jun 27: Modify Redis dome shutter status definition - REDIS_DOMESHUT_POSITIONED(green)/NEARPOS(yellow)/FARPOS(red)/UNKNOWN, 
//                Append new default config DEFAULT_DOME_ROTCHK_MAXALT (v0.9.9)
//   2024 Jun 28: Add definition of exposure status and expinfo structure(CEXP) to share information for current exposure (v1.0.0)
//   2024 Jul 05: Add new default config DEFAULT_OBSSTAT "/data/Logs/ObsStatus.txt" (v1.0.4)
//   2024 Jul 11: Add new members into expinfo structure(CEXP) for debugging (v1.0.7)
//   2026 Jun 02: Add flag_preparenextexp and flag_wait_for_shutreload into the Agent structure to configure with .ini RC, 
//                Add OSC_CHKCNT_SHUTRELOAD setting, and DEFAULT_PREPARE_NEXT_EXP/DEFAULT_WAIT_SHUTRELOAD for new configuration, 
//                Add flag/count_wait_for_shutreload into the OSC structure (v1.2.0)
//   
//
//------------------------------------------------------------------------------

// system header files 

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <sys/time.h>
#include <sys/times.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/file.h>
#include <netdb.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <termios.h>
#include <fcntl.h>

// GNU utility

#include <readline/readline.h>
#include <readline/history.h>
#include "hiredis.h"

// ISIS Client API header

#include "isisclient.h"

// In case the version and compilation data are not defined
// at compilation, put in some placeholders to prevent code barfing

#define APP_VER "v1.2.0"

#ifndef APP_VERSION
#define APP_VERSION APP_VER
#endif

#ifndef APP_COMPDATE
#define APP_COMPDATE "2016-09-20"
#endif

#ifndef APP_COMPTIME
#define APP_COMPTIME "00:00:00"
#endif

// System configurations

#define SYSCFG_TELID_CTIO  "KMTC"
#define SYSCFG_TELID_SSO   "KMTA"
#define SYSCFG_TELID_SAAO  "KMTS"

#define SYSCFG_IPADDR_CTIO  14
#define SYSCFG_IPADDR_SAAO  13
#define SYSCFG_IPADDR_SSO   15

#define SYSCFG_DTDATE_CHANGE_CTIO   0
#define SYSCFG_DTDATE_CHANGE_SSO    9
#define SYSCFG_DTDATE_CHANGE_SAAO  18 

// Site-Dependent but System-Independent default values 

  #define DEFAULT_MYID        "OBS"
  #define DEFAULT_MYPORT      6650
  #define DEFAULT_RCFILE      "/home/dts/Config/obstool.ini"
  #define DEFAULT_OSCDIR      "/home/dts/osc/"
//#define DEFAULT_INITOSC     "/home/dts/osc/default.osc"
//#define DEFAULT_INITOSC     "/data/osc/default.osc"
  #define DEFAULT_INITOSC     "no"
  #define DEFAULT_OBSSTAT     "/data/Logs/ObsStatus.txt"
  #define DEFAULT_LOGFILE     "/data/Logs/OBS/obs"               
  #define TEMP_EVENTLOGFILE   "/data/Logs/OBS/obs.temp.event.log"
  #define TEMP_DEBUGLOGFILE   "/data/Logs/OBS/obs.temp.debug.log"
  #define TEMP_SCROBSLOGFILE  "/data/Logs/OBS/obs.temp.scrobs.log"
    // NOTE: ".type.date.time.log" will be appended at the end of DEFAULT_LOGFILE
    // Default file name of Event Log: "/data/Logs/OBS/obs.event.yyyymmdd.hhmmss.log"


#define CORTABLE_BLGOFF        "/home/dts/cortable/offset_blg.table"

// typical ISIS server defaults (not used if in STANDALONE mode)

#define DEFAULT_ISISHOST  "localhost"
#define DEFAULT_ISISPORT  6600
#define DEFAULT_ISISID    "IS"

// default OBS Agent client application runtime flags (On:1, Off:0)

#define DEFAULT_VERBOSE     0     // default: not verbose (concise)
#define DEFAULT_DEBUG       0     // default: no debugging mode
#define DEFAULT_EVENTLOG    1     // default: enable runtime event enabled (DOLOG)
#define DEFAULT_LOGVERBOSE  1     // default: set verbose log mode
#define DEFAULT_DEBUGLOG    1     // default: enable runtime debugging log
#define DEFAULT_SCROBSLOG   1     // default: enable runtime script observation log
#define DEFAULT_TIMETAG     1     // default: do time tag display on console

#define DEFAULT_PREPARE_NEXT_EXP  1   // default: prepare next exposure during exposing / v1.2.0
#define DEFAULT_WAIT_SHUTRELOAD   1   // default: wait for shutter reloading to complete / v1.2.0

// default TCS specification and configuration

#define DEFAULT_TELID                 "KMTN"
#define DEFAULT_TCS_LIMIT_HA           4.60  // hour (04:38:24)
#define DEFAULT_TCS_LIMIT_DEC_N      +21.00  // deg  (Alt 36.4 on Merdian)
#define DEFAULT_TCS_LIMIT_DEC_S      -79.00  // deg  (Alt 41.2 on Merdian)
#define DEFAULT_TCS_LIMIT_SECZ         2.37  // secZ (Alt=25)
#define DEFAULT_TCS_LIMIT_ALT         30.00  // deg
#define DEFAULT_TCS_LIMIT_WARNING      1.25  // deg (5 min)

#define DEFAULT_TCS_SLEWSPEED_RA       1.0   // RA  slewing speed in deg/sec
#define DEFAULT_TCS_SLEWSPEED_DEC      1.0   // DEC slewing speed in deg/sec
#define DEFAULT_TCS_SETTLEDOWN_RA     18.0   // RA  settling down time in sec
#define DEFAULT_TCS_SETTLEDOWN_DEC    12.0   // DEC settling down time in sec
#define DEFAULT_TCS_DOMESPEED_ROT      1.0   // Dome rotating speed in deg/sec
#define DEFAULT_TCS_DOMESPEED_SHUT     0.3   // Dome shutter speed in deg/sec

#define DEFAULT_TCS_TOLERANCE_POINTING    2.0    // arc-sec, default tolerance for pointing error
#define DEFAULT_TCS_TOLERANCE_TRACKING    0.30   // arc-sec, default tolerance for tracking error
#define DEFAULT_TCS_ALLOWANCE_UNSTABLE    2      // unstable hysteresis for checking RA/DEC axes oscillation (Typ. 2 or 3)

// default TCS redis server configuration  (v0.9.3)

#define DEFAULT_REDIS_IP        121  // IP address of redis server on newTCS
#define DEFAULT_REDIS_PORT     6379  // Port number of redis server on newTCS
#define DEFAULT_REDIS_TIMEOUT   100  // Timeout in msec for connecting to redis

#define DEFAULT_REDIS_ERRTH_DOMEROT    3  // Maximun try number
#define DEFAULT_REDIS_ERRTH_DOMESHUT   3  // Maximun try number

// default Web relay error threshold (v0.9.3)

#define DEFAULT_RELAY_ERRTH_DCTRL   3   // Maximun try number

// default Web relay IPs (v0.6.8)

#define DEFAULT_RELAY_IP_MCFAN     65   // default Mirror cell fan relay ip address
#define DEFAULT_RELAY_IP_MDRV_    151   // default RA/DEC motor drive relay ip address
#define DEFAULT_RELAY_IP_WINDOW_  152   // default Power louver windows relay ip address (open/close/status/Temperature/Humidity)
#define DEFAULT_RELAY_IP_TCSPAD   153   // default PC-TCS Paddle relay ip address (N/S/E/W)
#define DEFAULT_RELAY_IP_HVAC_    154   // default HVAC relay ip address (Power/Cooling/Heating/Circulator)
#define DEFAULT_RELAY_IP_DLAMP    161   // default Domeflat lamp power relay ip address
#define DEFAULT_RELAY_IP_DCTRL    163   // default Dome controller power & rotation status relay ip address
#define DEFAULT_RELAY_IP_DLIGHT   164   // default Dome LED Light power relay ip address
#define DEFAULT_RELAY_IP_FSA_     165   // default FSA power & status relay ip address
#define DEFAULT_RELAY_IP_DHUM_    168   // default dehumidifier power & status relay ip address

// default Web relay XML port numbers (for port forwarding at the router) (v0.8.5)

#define DEFAULT_RELAY_PORT_MCFAN      80   // default Mirror cell fan relay XML port number (device default: http 80)
#define DEFAULT_RELAY_PORT_MDRV_    8051   // default RA/DEC motor drive relay XML port number
#define DEFAULT_RELAY_PORT_WINDOW_  8052   // default Power louver windows relay XML port number (open/close/status/Temperature/Humidity)
#define DEFAULT_RELAY_PORT_TCSPAD   8053   // default PC-TCS Paddle relay XML port number (N/S/E/W)
#define DEFAULT_RELAY_PORT_HVAC_    8054   // default HVAC relay XML port number (Power/Cooling/Heating/Circulator)
#define DEFAULT_RELAY_PORT_DLAMP    8061   // default Domeflat lamp power relay XML port number
#define DEFAULT_RELAY_PORT_DCTRL    8063   // default Dome controller power & rotation status relay XML port number
#define DEFAULT_RELAY_PORT_DLIGHT   8064   // default Dome LED Light power relay XML port number
#define DEFAULT_RELAY_PORT_FSA_     8065   // default FSA power & status relay XML port number
#define DEFAULT_RELAY_PORT_DHUM_    8068   // default dehumidifier power & status relay XML port number

// default Web relay Rly numbers or Digital input port (v0.6.8)

#define DEFAULT_RELAY_NUM_MCFAN      1   // default Mirror fan power relay number
#define DEFAULT_RELAY_NUM_MDRV_RDC_  1   // default RA motor drive 24VDC power relay number
#define DEFAULT_RELAY_NUM_MDRV_RMP_  2   // default RA motor drive main power on/off switch relay number
#define DEFAULT_RELAY_NUM_MDRV_DDC_  3   // default DEC motor drive 24VDC power
#define DEFAULT_RELAY_NUM_MDRV_DMP_  4   // default DEC motor drive main power on/off switch relay number
#define DEFAULT_RELAY_NUM_TPAD_N     1   // default PC-TCS paddle North button relay number
#define DEFAULT_RELAY_NUM_TPAD_S     2   // default PC-TCS paddle South button relay number
#define DEFAULT_RELAY_NUM_TPAD_E     3   // default PC-TCS paddle East button relay number
#define DEFAULT_RELAY_NUM_TPAD_W     4   // default PC-TCS paddle West button relay number
#define DEFAULT_RELAY_NUM_DLAMP      1   // default Domeflat lamp power relay number
//#define DEFAULT_RELAY_NUM_DROTIN     1   // default Dome rotation status digital input port number
#define DEFAULT_RELAY_NUM_DLIGHT     1   // default Dome litht power relay number

#define DEFAULT_TCSPAD_MODE       RELAY_TCSPAD_MODE_UNDEF  // default PC-TCS paddle mode = undefined
#define DEFAULT_TCSPAD_MODE_CTIO  RELAY_TCSPAD_MODE_GUIDE  // CTIO: #1 common pin & #6 mode pin connected at PC-TCS paddle input port
#define DEFAULT_TCSPAD_MODE_SAAO  RELAY_TCSPAD_MODE_DRIFT  // SAAO: #6 mode pin open at PC-TCS paddle input port
#define DEFAULT_TCSPAD_MODE_SSO   RELAY_TCSPAD_MODE_GUIDE  // SSO : #6 mode pin open at PC-TCS paddle input port

#define DEFAULT_DOME_ERRTH_WAITROT    (180.0/DEFAULT_TCS_DOMESPEED_ROT)  // Maximum operation time for dome rotation in sec (v0.9.8)
#define DEFAULT_DOME_ERRTH_WAITSHUT   ( 75.0/DEFAULT_TCS_DOMESPEED_ROT)  // Maximum operation time for dome shutter  in sec (v0.9.8)
#define DEFAULT_DOME_ROTCHK_MAXALT      82.0     // to disable the Dome rotation status check when the telescope is near the zenith

// default ExpInfo Redis server

//#define DEFAULT_EXPINFO_REDIS_IP        241   // Redis server IP address in DTS
//#define DEFAULT_EXPINFO_REDIS_PORT    55030   // Port number of redis server on newTCS
//#define DEFAULT_EXPINFO_REDIS_TIMEOUT   100   // Timeout in msec for connecting to redis

// END of Site-Dependent default setup


//------------------------------------------------------------
//
// Touch the stuff below this at your own risk..
//

// Message handling select() Time intervals and monitoring setting

#define SELECT_TIMEOUT         50    // select() timeout for input-waiting in msec
#define SELECT_ERR_IGNORE_NUM   0    // select() error number for no msg print

// String lengths

#define MAXCFGLINE         128    // maximum mumber of characters/line of the file

#define STRLEN_CMD         256    // Keyboard/ISIS command string length
#define STRLEN_ARG         256    // Keyboard/ISIS command's argument field length
#define STRLEN_ARGS         32    // short argument field length
#define STRLEN_ARGSS        16    // pretty short argument field length
#define STRLEN_REP        1024    // reply string size, must be larger that info or auxstatus
#define STRLEN_MAXKEYIN    256    // Maximum length of Keyboard input message string
#define STRLEN_MAXSOCIN   1024    // Maximum length of ISIS input message string
#define STRLEN_MAXFILNAME   16    // Maximum length of filter name, defined in TCSAgent
#define STRLEN_FILE        512
#define STRLEN_CMSG       1024

#define STRLEN_ISISSTAT    128          // size of STATUS string to report to ISIS nodes
#define STRLEN_ISISADDR     32          // maximum size of ICIMACS(ISIS) command type string
#define STRLEN_ISISTYPE     64          // maximum size of ICIMACS(ISIS) command type string
#define STRLEN_ISISNODE  ISIS_NODESIZE  // maximum size of ICIMACS(ISIS) node ID, 8+1
#define STRLEN_ISISMSG   ISIS_MSGSIZE   // ISIS mesage size using ISIS Lib. function, 2048

#define STRLEN_TSTAT_MAX   200          // Max. TSTAT string length, normal length = 137 when Link = UP, defined in TCS Agent

// Maximum line/data number and array length for loading the obs script and config file

#define OSC_MAXLINENUM    12000      // max num of command and exposure config lines
#define OSC_MAXLINELEN      256      // max string length of input line in obs script

#define OSC_MAXCMDLEN        16      // max length of command string of each command line
#define OSC_MAXARGLEN        64      // max length of argument string of each command line
#define OSC_MAXEXPLEN       256      // max string length of exposure configuration line
#define OSC_MAXMSGLEN       256      // max string length for message output
#define OSC_MAX_ARGIN       101
#define OSC_MAX_DPLAB        16
#define OSC_MAX_DPOBJ        16
#define OSC_MAX_PROJID       16
#define OSC_MAX_LABEL        64
#define OSC_MAX_OBJECT       32


//------------------------------------------------------------
//
// Script observation status/flags/configuration mecros
//

// script observation command type definition

#define OSC_TYPE_INDEF        0
#define OSC_TYPE_CMD          1
#define OSC_TYPE_EXP          2

// return codes script observation running function

#define OSC_RTN_NOERR         0
#define OSC_RTN_NOTICE        2
#define OSC_RTN_WARNING       1
#define OSC_RTN_ERROR        -1

// script observation running flags bit definition

//#define OSC_CMDBIT_STANDBY         0x00000000  // not necessary, we can use other flags such as isISISconnected, tcsconnected and auxconnected
#define OSC_CMDBIT_POINTING        0x00000001
#define OSC_CMDBIT_SETFILTER       0x00000002
#define OSC_CMDBIT_SETPROJID       0x00000004   // v0.6.4
#define OSC_CMDBIT_SETOBJECT       0x00000008
#define OSC_CMDBIT_SETEXPTIME      0x00000010
#define OSC_CMDBIT_STARTEXP        0x00000020 
#define OSC_CMDBIT_ONTRACKING      0x00000040 
#define OSC_CMDBIT_ENABLESERVO     0x00000080 
//#define OSC_CMDBIT_CHKFILTER     0x00000000   // to do unconditionally
//#define OSC_CMDBIT_CHKTELRADEC   0x00000000   // to do unconditionally
#define OSC_CMDBIT_SET_NSTVEL      0x00010000 
#define OSC_CMDBIT_ON_NSTRACK      0x00010000 

// script observation check to receive response flags bit 

#define OSC_CHKBIT_POINTING        0x00000100
#define OSC_CHKBIT_SETFILTER       0x00000200
#define OSC_CHKBIT_SETPROJID       0x00000400   // v0.6.4
#define OSC_CHKBIT_SETOBJECT       0x00000800
#define OSC_CHKBIT_SETEXPTIME      0x00001000
#define OSC_CHKBIT_STARTEXP        0x00002000   
#define OSC_CHKBIT_ONTRACKING      0x00004000 
#define OSC_CHKBIT_ENABLESERVO     0x00008000
#define OSC_CHKBIT_SET_NSTVEL      0x01000000 
#define OSC_CHKBIT_ON_NSTRACK      0x01000000 

// checking duration(count) definition

//#define OSC_INTERVAL_PROCESS   10    // Observation script process interval in loop number (10 ~ 0.5s)
//#define OSC_INTERVAL_PROCESS   TCS_DATAUP_INTERVAL  // = TCS data update interval in func call number = 20 ~ 1.0s
//        --> not used, just TCS_DATAUP_INTERVAL used in codes
//#define OSC_CHKCNT_RESPCHK      6    //  ~5s = (OSC_CHKCNT_RESPCHK -1) x OSC_INTERVAL_PROCESS
#define OSC_CHKCNT_RESPCHK      4    //  ~3s = (OSC_CHKCNT_RESPCHK -1) x OSC_INTERVAL_PROCESS, modified at v0.6.5
#define OSC_CHKCNT_EXPSTART    21    // ~20s = (OSC_CHKCNT_EXPSTART-1) x OSC_INTERVAL_PROCESS
// 13 sec ~ 15 sec usually, for EXPSTATUS=IDLE  -->  EXPSTATUS=INITIALIZING

#define OSC_CHKCNT_CMDRETRY     3    // v0.6.5

#define OSC_CHKCNT_SHUTRELOAD   6    // 6+a sec waiting / v1.2.0

//#define OSC_CHKCNT_POINTING     4    // total tmr trying number = 5 = initial try + OSC_CHKCNT_POINTING
//#define OSC_CHKCNT_POINTING     7    // total tmr trying number = 8 = initial try + OSC_CHKCNT_POINTING, increased at v0.2.5
  #define OSC_CHKCNT_POINTING     8    // total tmr trying number = 9 = initial try + OSC_CHKCNT_POINTING, increased at v0.4.7
  #define OSC_CHKCNT_FILTER       5

#define OSC_ADJ_TOL_POINTING    0.2  // in arc-sec, adopted at v0.4.5
                                     // 1) tcs_tolerance_pointing_corr = tcs_tolerance_pointing + OSC_ADJ_TOL_POINTING * (posc->count_pointing/2),   (v0.4.7)
                                     // 2) if posc->count_pointing > OSC_CHKCNT_POINTING*3/4,   (v0.4.6)
                                     //    if posc->count_pointing > OSC_CHKCNT_POINTING*2,     (v0.4.7)
                                     //        tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING * 1 when |Dec| > 50
                                     //        tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING * 2 when |Dec| > 60
                                     //        tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING * 3 when |Dec| > 70

// default script observation configuration

#define OSC_DEFAULT_PREPSEC  14  // telescope re-pointing & CCD clearing time
#define OSC_DEFAULT_READSEC  42  // readout and finalizing time by CAMSTATUS_IDLE
#define OSC_DEFAULT_ADVANCE   0  // seconds to advance exp.start, used while waiting for UT_OBS (v0.8.3)
#define OSC_DEFAULT_UTTOL    60  // default tolerence for UT_OBS in seconds, optimized UT_TOL is UT_OBS_INT/2
#define OSC_MINIMUM_UTTOL    30  // minimum tolerence for UT_OBS in seconds
//#define OSC_MAXIMUM_UTTOL 10800  // maximum tolerence for UT_OBS in seconds, 10800s = 3h (removed at v0.9.0)

// NOTE: 
// - Optimized UT_TOL = UT_OBS_INT/2
// - If UT_TOL <= 0, the exp line is observed regardless of the current time.


//------------------------------------------------------------
//
// System configuration mecros
//

// Mecros for system status (mainly refered for script running)

#define CAMSTATUS_NC        -1    // not connected to ICS
#define CAMSTATUS_PREP_I     1    // "EXPSTATUS=INITIALIZING"
#define CAMSTATUS_PREP_E     2    // "EXPSTATUS=ERASE"
#define CAMSTATUS_INT_1      3    // "EXPSTATUS=INTEGRATING"
#define CAMSTATUS_INT_2      4    // "Shutter=Open"
#define CAMSTATUS_INT_3      5    // "Remaining="
#define CAMSTATUS_CLOSING    6    // "Shutter=Closed", Shutter is closing.
#define CAMSTATUS_READ_1     7    // "EXPSTATUS=READOUT"
#define CAMSTATUS_READ_2     8    // 1st "PCTREAD="
#define CAMSTATUS_READ_3     9    // 2nd "PCTREAD="
#define CAMSTATUS_IDLE_1    10    // 1st "Acquisition Complete"
#define CAMSTATUS_IDLE_2    11    // 4th "Acquisition Complete"
#define CAMSTATUS_IDLE_3    12    // "EXPSTATUS=IDLE", 'GO' command available
#define CAMSTATUS_READY     13    // "Disk Write Complete" on all ICs, 
#define CAMSTATUS_CHECK      0    // status unknown
#define CAMSTATUS_CRASHED   -2    // "Failed to Start acquisition on one or more ICs", 
                                  // or "Failed to initialize one or more ICs",
                                  // or when the status become not IDLE2 or IDLE3.
#define CAMSTATUS_DEAD      -3    // not used just now

//// Note
////  - 'EXP'/'OBJECT'/'DARK'/'BIAS'/'FLAT'/'PROJID'/'OBSERVER' commands are available only in READY status.
////  - CamStatus is forcibly set to 'READY' status 12 seconds after setting to 'IDLE_3' by "EXPSTATUS=IDLE" message. 


#define ICS_UNDEF           0
#define ICS_ADC             1
#define ICS_CTC             2

#define TELSTATUS_NC        -1
#define TELSTATUS_CHECKING   0
#define TELSTATUS_STOW       1
#define TELSTATUS_HOLDING    2
#define TELSTATUS_TRACKING   3
#define TELSTATUS_TRACKINGS  4    // tracking stably
#define TELSTATUS_OSCILLATE  5
#define TELSTATUS_SLEW       6
#define TELSTATUS_SETTLING   7
#define TELSTATUS_DISABLED  -2

#define TCSSTATUS_MOVE_NO         0    // defined in PC-TCS telemetry data
#define TCSSTATUS_MOVE_RA         1    // defined in PC-TCS telemetry data
#define TCSSTATUS_MOVE_DEC        2    // defined in PC-TCS telemetry data
#define TCSSTATUS_MOVE_BOTH       3    // defined in PC-TCS telemetry data
#define TCSSTATUS_MOVE_UNKNOWN   -1
#define TCSSTATUS_LIMIT_NO        0    // defined in PC-TCS telemetry data
#define TCSSTATUS_LIMIT_R         1    // defined in PC-TCS telemetry data
#define TCSSTATUS_LIMIT_D         2    // defined in PC-TCS telemetry data
#define TCSSTATUS_LIMIT_RD        3    // defined in PC-TCS telemetry data
#define TCSSTATUS_LIMIT_H         4    // defined in PC-TCS telemetry data
#define TCSSTATUS_LIMIT_RH        5    // defined in PC-TCS telemetry data
#define TCSSTATUS_LIMIT_DH        6    // defined in PC-TCS telemetry data
#define TCSSTATUS_LIMIT_RDH       7    // defined in PC-TCS telemetry data
#define TCSSTATUS_LIMIT_BIT_RA    0x01
#define TCSSTATUS_LIMIT_BIT_DEC   0x02
#define TCSSTATUS_LIMIT_BIT_HOR   0x04
#define TCSSTATUS_LIMIT_UNKNOWN  -1
#define TCSSTATUS_DRIVE_ENABLED   0    // defined in PC-TCS telemetry data
#define TCSSTATUS_DRIVE_DISABLED  1    // defined in PC-TCS telemetry data
#define TCSSTATUS_DRIVE_UNKNOWN  -1

#define TEL_AXIS_NO         0    // Telescope axis Undefined or No axis under condition
#define TEL_AXIS_RA         1    // Telescope axis RA
#define TEL_AXIS_DEC        2    // Telescope axis DEC
#define TEL_AXIS_BOTH       3    // Telescope axis Both RA/DEC
#define TEL_AXIS_UNKNOWN   -1    // Telescope axis Unkonwn or Invalid definition

#define DOME_IDLE       0   // v0.9.3
#define DOME_MOVING     1   // using for domerot & domeshut in system_config
#define DOME_ROTATING   1   // same value & mean as <state value> of relays
#define DOME_UNKNOWN   -1

// generic mecro for AUX statues

#define AUX_UNKNOWN  -1

// Status for connection and operation

#define AUX_STATUS_NC         10  // not connected
#define AUX_STATUS_STANDBY    11  // connected & standby
#define AUX_STATUS_RUNNING    12  // connected & running
#define AUX_STATUS_ERROR      13  // a error was occured
#define AUX_STATUS_UNKNOWN    AUX_UNKNOWN

// Mecros for filter slide configuration

#define FNUM_N    0    // no filter
#define FNUM_1    1    // filter #1
#define FNUM_2    2    // filter #2
#define FNUM_3    3    // filter #3
#define FNUM_4    4    // filter #4
#define FNUM_M    5    // more than 2 filters
#define FNUM_U    6    // unknown(in operation)
#define FNUM_X    9    // not availalbe

#define FNAME_N   "NO"
#define FNAME_M   "MANY"
#define FNAME_U   "UNKNOWN"
#define FNAME_X   "N/A"

#define FNAME_1_DEFAULT  "1"
#define FNAME_2_DEFAULT  "2"
#define FNAME_3_DEFAULT  "3"
#define FNAME_4_DEFAULT  "4"

// Mecros for system connection and update monitoring configuration

#define TCS_CONCHK_INTERVAL   50    // TCS connection check interval in loop number (50 loops ~ 2.6s)
#define AUX_CONCHK_INTERVAL   50    // AUX connection check interval in loop number (50 loops ~ 2.6s)
#define XIS_CONCHK_INTERVAL   50    // XIS connection check interval in loop number (50 loops ~ 2.6s)

//#define TCS_DATAUP_INTERVAL   20    // TCS data update interval in loop number (20 loops ~ 1.0s) 
  #define TCS_DATAUP_INTERVAL   21    // TCS data update interval in loop number (21 loops ~ 1.0s)   <-- modified at v0.4.0
  #define AUX_DATAUP_INTERVAL   TCS_DATAUP_INTERVAL

// Mecros for Web relay 

#define RELAY_TCSPAD_MODE_UNDEF  -1 
#define RELAY_TCSPAD_MODE_DRIFT   0   // #6 mode pin open at PC-TCS paddle input port
#define RELAY_TCSPAD_MODE_GUIDE   1   // #1 common pin & #6 mode pin connected at PC-TCS paddle input port

#define RELAY_DROT_IDLE       0   // v0.9.7
#define RELAY_DROT_LEFT       1   // DigitalInput1, fixed(?)
#define RELAY_DROT_RIGHT      2   // DigitalInput2, fixed(?)
#define RELAY_DROT_BOTH       3
#define RELAY_DROT_UNKNOWN   -1

// Mecros for Redis values (v0.9.4)

#define REDIS_DOMEROT_POSITIONED   0   // <newTCS Redis definition>
#define REDIS_DOMEROT_ROTATING     2   //   'dome_error' = 0: positioned(green) / 2: rotating(orange) / 3: stowing or halted(red)
#define REDIS_DOMEROT_HALTED       3   //   'SHUTTER' = 1: positioned(green) / 0: moving(orange) / -1: stowing or error>tolerance(red)
#define REDIS_DOMEROT_UNKNOWN     -1
#define REDIS_DOMESHUT_POSITIONED  1
#define REDIS_DOMESHUT_NEARPOS     0   // shutter is positioned within 10 sec, and we can Go since CCD flushing time < 10 sec
#define REDIS_DOMESHUT_FARPOS     -1
#define REDIS_DOMESHUT_UNKNOWN    -2

// Mecros for ExpInfo (v1.0.0)

#define EXPSTATUS_CHECK       0   // Init. or sys.camstatus == CAMSTATUS_CHECK, when script observation is not in progress
#define EXPSTATUS_STANDBY     1   // sys.camstatus== CAMSTATUS_READY, when script observation is not in progress
#define EXPSTATUS_WAITING     2   // sys.camstatus== CAMSTATUS_READY, in preparing Tel during script observation
#define EXPSTATUS_CMDED       3   // sys.camstatus== CAMSTATUS_CHECK, at Go commanded by script observation process
#define EXPSTATUS_FLUSH       4   // sys.camstatus>= CAMSTATUS_PREP_I -- "EXPSTATUS=INITIALIZING"
#define EXPSTATUS_EXPOSURE    5   // sys.camstatus>= CAMSTATUS_INT_1  -- "EXPSTATUS=INTEGRATING"
#define EXPSTATUS_READOUT     6   // sys.camstatus>= CAMSTATUS_READ_1 -- "EXPSTATUS=READOUT"
#define EXPSTATUS_FINISH      7   // sys.camstatus>= CAMSTATUS_IDLE_1 -- 1st "Acquisition Complete"
#define EXPSTATUS_ERROR      -1   // sys.camstatus < 0 (CAMSTATUS_CRASHED/DEAD/...)


//------------------------------------------------------------------------------
//
// Mecros for utilities & software config
//

//// External commands
#define ECMD_DTCHK  "/home/kmt/KMTNetPL_SHEL/CHK_ICS_to_DTS.csh"  // cmd to execute c shell for data trasfer check

//// External commands for Web relays for Mirror cell fan / Domeflat lamp / Dome LED light / Dome rotation / TCS Keypaddle (v0.6.8)
//#define RCMD_SET_HEAD     " curl -m1 -X GET 'http://192.168"
#define RCMD_SET_CMDHEAD    " curl -m1 -X GET '"   // v0.9.6
#define RCMD_SET_URLHEAD    "http://192.168"       // v0.9.6
#define RCMD_SET_MIDDLE     "state.xml?relay"
#define RCMD_SET_ON_TAIL    "State=1'"    
#define RCMD_SET_OFF_TAIL   "State=0'"    
#define RCMD_SET_REDIRECT   "/dev/null 2>&1 "
//#define RCMD_GET_HEAD     " curl -m1 -X GET 'http://192.168"
#define RCMD_GET_CMDHEAD    " curl -m1 -X GET '"   // v0.9.6
#define RCMD_GET_URLHEAD    "http://192.168"       // v0.9.6
#define RCMD_GET_MIDDLE     "state.xml"            // for CURLOPT_POSTFIELDS
#define RCMD_GET_STAT_TAIL  "'"
#define RCMD_GET_REDIRECT   "curl.temp 2>&1 "
#define RCMD_GET_OUTPUT     "curl.temp"
    // set on   : curl -m1 -X GET 'http://192.168.xx.xxx:8063/state.xml?relay[RN]State=1' > /dev/null 2>&1
    // set off  : curl -m1 -X GET 'http://192.168.xx.xxx:8063/state.xml?relay[RN]State=0' > /dev/null 2>&1
    // get state: curl -m1 -X GET 'http://192.168.xx.xxx:8063/state.xml > curl.temp 2>&1'
    // CURLOPT_URL: http://192.168.xx.xxx:nnnn/state.xml

//// Warning blinking interval settings

/// Slow speed blinking
//#define WARNING_BLINK_INTERVAL  160    // Warning blinking interval in loop number, 1 loop ~ 50ms, 160 loops ~ 8 sec
//#define WARNING_BLINK_SHORTINT   20    // 20 loops Low and High respectively, 1 cycle = 40 loops & beeps ~ 2.0 sec
//#define WARNING_BLINK_NUMBER      3    // the number of blinking cycle, 40 loops x 3 cycles ~ 6.0 sec

/// Middle speed blinking
//  #define WARNING_BLINK_INTERVAL   80    // Warning blinking interval in loop number, 1 loop ~ 50ms, 80 loops ~ 4 sec
//  #define WARNING_BLINK_SHORTINT   10    // 10 loops Low and High respectively, 1 cycle = 20 loops & beeps ~ 1.0 sec
//  #define WARNING_BLINK_NUMBER      3    // the number of blinking cycle, 20 loops x 3 cycles ~ 3.0 sec

/// Fast speed blinking
#define WARNING_BLINK_INTERVAL   50    // Warning blinking interval in loop number, 1 loop ~ 50ms, 50 loops ~ 2.5 sec
#define WARNING_BLINK_SHORTINT    6    // 6 loops Low and High respectively, 1 cycle = 12 loops & beeps ~ 0.6 sec
#define WARNING_BLINK_NUMBER      3    // the number of blinking cycle, 12 loops x 3 cycles ~ 1.8 sec


//------------------------------------------------------------------------------
//
// Application global system table structure 
//

//
// Type definitions
//

typedef unsigned int UINT;

typedef struct smctime {
  int year;
  int month;
  int day;
  int hour;
  int min;
  double sec;
  UINT secse;  // the time as the number of seconds since the Epoch, 1970-01-01 00:00:00 +0000 (UTC)  //  v0.7.0
} smctime_t;

//
// OBS Agent structure for application diagnostic data
//

typedef struct obsagent_config {

  char   StartTime[24];            // UTC time server started
  char   UserID[64];               // user ID that launched TCSAgent 
  char   exeFile[STRLEN_FILE];     // rootname(path/name) of executable file   
  char   InitOsc[STRLEN_FILE];     // initial observation script path
  char   AppVersion[64];           // Application version

  FILE*  pLogEvent;                 // All event/erbose message log file pointer
  FILE*  pLogDebug;                 // All event/verbose/debugging message log file pointer
  FILE*  pLogScrObs;                // Script observation Log file pointer

  int    isLogVerbose;             // Flag to enable verbose log
  int    isDebugLog;               // Flag to enable bebugging message log (make another log file)
  int    isScrObsLog;              // Flag to enable script obs results log (make another log file)
  int    isTimeTag;                // Flag to enable the time tag display on console
  int    isBlockTimeTag;           // Flag to temporarily block time tag display, 
                                   //      used for Initializing/Script loading
  int    isISISconnected;          // Flag to set ISIS connection status
  int    ISISchecknum;             // ISIS connection check num in loop num in main()
  int    ISIScheckint;             // ISIS connection check interval

  int    flag_warning;             // Flag to set the warning blinking
  int    count_warning;            // Loop counter to use for waiting for interval
  int    interval_warning;         // Warning blinking interval in loop number (1 loop ~ 50 ms)

  int  flag_preparenextexp;        // Flag to enable preparing next exposure during exposing / v1.2.0
  int  flag_wait_for_shutreload;   // Flag to enable waiting for shutter reloading to complete before slew for thd next exposure / v1.2.0

  int flag_override_isisconnection;

} obsagent_t;

//
// System configuration and status data
//

typedef struct system_config {

  //// Camera status/flags/counters for monitoring

     int camstatus;

     int count_acqcomp;
     int count_wrote;
     int count_idle;           // counting started at IDLE_1/IDLE_2 status, count in main() loop (~0.045sec/count)
     int force_idle;           // set camstatus to IDLE_3 when count_idle == force_idle
     int count_ready;          // counting started at IDLE_3 status, count in main() loop (~0.045sec/count)
     int force_ready;          // set camstatus to READY when count_ready == force_ready

     int status_fitssaved;
     int flag_icscheck;

     int count_fitssaving;
     int allowance_fitssaving;
     int force_fitssaved;

  double exp_set;              // exposure time set in seconds, updated from "ICS>OBS DONE: .. ExpTime=## .." message
  double exp_remaining;        // exposure time remaining in seconds
  double exp_starttime;        // time stamp that exposure is started, in seconds
     int flag_expcount;        // v0.3.3
    char exp_fitsnum[32];      // FITS number for current exposure, get with "ICS>OBS DONE: EXPNUM  Filename=" message from ICS

  //// Telescope status/counters for monitoring

     int telstatus;
     int nston;                // non-sidereal tracking on:1, off:0, unknown;-1 (v0.6.9)

     int duration_slew;        // update number during slew
     int duration_settling;    // update number during settling
     int duration_unstable;    // update number keeping continous unstable state (for checking tracking or holding status)
     int duration_stable;      // update number keeping continous steady state (for checking tracking stability)
     int unstable_ra;          // update number keeping continous unstable state on RA axis (v0.9.0)
     int unstable_dec;         // update number keeping continous unstable state on DEC axis (v0.9.0)
     int unstable_axis;        // remark axis oscillating: TEL_AXIS_NO(0)/_RA(1)/_DEC(2)/_BOTH(3)/_UNKNOWN(4) (v0.9.0)
     int tpfailed_axis;        // remark axis pointing failed: TEL_AXIS_NO(0)/_RA(1)/_DEC(2)/_BOTH(3)/_UNKNOWN(4) (v0.9.0)

     int allowance_slew;       // Max. update number to wait for slew finish (Max. 120 deg in DEC axis)
     int allowance_settling;   // Max. update number to wait for completely settling down (Typ. settling down time ~ 20 sec in DEC axis)
   //int allowance_unstable;   // update number for tolerencing the oscillation condition, bumper(or buffer) for oscillation determination --> moved TCS config, and changed to tcs_allowance_unstable
     int threshold_tracking;   // update number that can confirm the status is tracking
     int threshold_stable;     // update number that can confirm the status is stable

  //// TCS flags/counters for monitoring connection and data update

     int flag_tcsconnected;
     int checknum_tcsconnection;
     int interval_tcsconnection;
     int checknum_tcsdisconnected;
     int allowance_tcsdisconnected;   // bumper for disconnection determination 

     int flag_tcsdata_updated;
     int flag_tcsdata_requested;      // set to 1 when tcsdata requested periodically in main() loop
     int checknum_tcsdata;
     int interval_tcsdata;
     
     int flag_tcswarning_nearlimit;
     int flag_tcswarning_oscinexp;

  //// Instrument control system / CCD camera settings

     int ics_datasource;  // ICS_UNDEF / ICS_ADC / ICS_CTC

  //// TCS specification & configuration

  double tcs_latitude;    // deg N, used for calculating the destination ALT
  double tcs_longitude;   // deg W, used for calculating the LST/HA
  double tcs_elevation;   // meter, not used yet

  double tcs_limit_ha;
  double tcs_limit_dec_n;
  double tcs_limit_dec_s;
  double tcs_limit_secz;
  double tcs_limit_alt;
  double tcs_limit_warning;
  
  double tcs_slewspeed_ra;     // RA  slewspeed in deg/sec
  double tcs_slewspeed_dec;    // DEC slewspeed in deg/sec
  double tcs_settledown_ra;    // RA  settling down time in sec
  double tcs_settledown_dec;   // DEC settling down time in sec
  double tcs_domerotspeed;     // Dome rotation speed in deg/sec
  double tcs_domeshutspeed;    // Dome shutter speed in deg/sec

     int tcs_allowance_unstable;   // unstable hysteresis for checking RA/DEC axes oscillation (Typ. 2 or 3)
  double tcs_tolerance_pointing;   // arc-sec, tolerance for pointing error  
  double tcs_tolerance_tracking;   // arc-sec, tolerance for tracking error
  double tcs_tolerance_pointing_corr;   // arc-sec, if posc->count_pointing > OSC_CHKCNT_POINTING*3/4, 
                                        // tcs_tolerance_pointing_corr = tcs_tolerance_pointing + OSC_ADJ_TOL_POINTING (v0.4.5)

  //// TCS data

    char ra [16];
    char dec[16];
    char ha [16];
    char lst[16];

  double ra_h;
  double dec_d;
  double epoch_y;
  double ha_h;
  double lst_h;
  double secz;
  double alt_d;
  double az_d;

  double cmd_velra;   // latest commanded RA velocity for non-sidereal tracking
  double cmd_veldec;  // latest commanded Dec velocity for non-sidereal tracking

  double timestamp_tmr;

     int movestatus;
     int limitstatus;
     int drivedisable;

  //// AUX flags/counters for monitoring connection and data update

     int flag_auxconnected;
     int checknum_auxconnection;
     int interval_auxconnection;
     int checknum_auxdisconnected;
     int allowance_auxdisconnected;   // bumper for disconnection determination 

     int flag_auxdata_updated;
     int flag_auxdata_requested;
     int checknum_auxdata;
     int interval_auxdata;

     int flag_filterlabel_requested;
     int flag_fsaerror;               // v0.3.4

  //// AUX configuration

    char telid[32];
    char filterlabel[7][16];

  //// AUX data

    char fsastatus[16];
    char shutstatus[16];
    char shutopstat[16];
    char filteropstat[16];
    char filtername[16];
     int filternum;
  double focus;
  double tns;
  double tew;
  double ens[7];
    char fan[16];
    char dsstatus[16];  // v0.9.3
     int aux_domeshut;  // aux dome shutter subsys status (AUX_STATUS_NC/_STANDBY/_RUNNING/_ERROR)  // v0.9.4


  //// Camera housekeeping data
  //double dewartv[8];       // dewar temperature/vacuum update func reserved..

  //// flags to override subsys error

     int flag_override_tcsconnection;
     int flag_override_auxconnection;

  //// Web relay configuration (v0.6.8)

     int relay_dlamp_ipaddr;   // domeflat lamp relay ip address
     int relay_dlamp_portnum;  // domeflat lamp relay XML port num
     int relay_dlamp_rlynum;   // domeflat lamp rly port number
     int relay_dlight_ipaddr;  // dome LED light relay ip address
     int relay_dlight_portnum; // dome LED light relay XML port num
     int relay_dlight_rlynum;  // dome LED light rly port number
     int relay_mcfan_ipaddr;   // mirror cell fan relay ip address
     int relay_mcfan_portnum;  // mirror cell fan relay XML port num
     int relay_mcfan_rlynum;   // mirror cell fan rly port number
     int relay_tcspad_ipaddr;  // pc-tcs paddle relay ip address
     int relay_tcspad_portnum; // pc-tcs paddle relay XML port num
     int relay_tcspad_rn[4];   // pc-tcs paddle n/s/e/w rly port number
     int relay_tcspad_mode;    // pc-tcs paddle mode switch config(site-dependent)
     int relay_dctrl_ipaddr;   // dome controller relay ip address
     int relay_dctrl_portnum;  // dome controller relay XML port num
     int relay_dctrl_din_drot; // dome rotation digital input port number

  //// Web relay status & variables for state input (v0.9.4)

     int relay_dctrl_failnum;  // dome controller access failure number (v0.9.3)
     int relay_dctrl_state_drot;  // state about dome rotation of dome controller (v0.9.4)

  //// Web relay commands; external sh commands to set relays, and to get status of relays (v0.6.8)

    char rcmd_dlamp_set_on      [STRLEN_CMD];   // domeflat lamp power on
    char rcmd_dlamp_set_off     [STRLEN_CMD];   // domeflat lamp power off
    char rcmd_dlamp_get_stat    [STRLEN_CMD];   // domeflat lamp power status
    char rcmd_dlight_set_on     [STRLEN_CMD];   // dome LED light power on
    char rcmd_dlight_set_off    [STRLEN_CMD];   // dome LED light power off
    char rcmd_dlight_get_stat   [STRLEN_CMD];   // dome LED light power status
    char rcmd_mcfan_set_on      [STRLEN_CMD];   // mirror cell fan power on
    char rcmd_mcfan_set_off     [STRLEN_CMD];   // mirror cell fan power off
    char rcmd_mcfan_get_stat    [STRLEN_CMD];   // mirror cell fan power status
    char rcmd_tcspad_set_on  [4][STRLEN_CMD];   // pc-tcs paddle button n/s/e/w on
    char rcmd_tcspad_set_off [4][STRLEN_CMD];   // pc-tcs paddle button n/s/e/w off
    char rcmd_tcspad_get_stat   [STRLEN_CMD];   // pc-tcs paddle buttons status
    char rcmd_drotin_get_stat   [STRLEN_CMD];   // dome rotation status(digital input)
    char rcmd_drotin_curlopt_url[STRLEN_CMD];   // dome controller CURLOPT_URL for curl lib (v0.9.6)

  //// commands for PC-TCS paddle setup & control

    char tcspad_tcmd_vel_ra  [STRLEN_ARGS];
    char tcspad_tcmd_vel_dec [STRLEN_ARGS];

  //// redis server configruation & status values (v0.9.3/v0.9.4)

    char redis_host[64];
     int redis_port;
    struct timeval redis_timeout;

     int redis_domerot;    // key: 'dome_error' = 0: positioned(green) / 2: rotating(orange) / 3: stowing or halted(red)
     int redis_domeshut;   // key: 'SHUTTER' = 1: positioned(green) / 0: moving(orange) / -1: stowing or error>tolerance(red)

     int redis_failnum_domerot;   // number of failure to get dome_error
     int redis_failnum_domeshut;  // number of failure to get SHUTTER

  //// Dome status (v0.7.8)

     int domerot;     // dome rotation status (0: IDLE / 1: Rotating / -1: Unknown)
     int domeshut;    // dome shutter status (0: IDLE / 1: Moving / -1: Unknown)

} obssystem_t;

//
// OBS Script structure definition
//

typedef struct obsscript_line {

     int  type;      // OSC_TYPE_CMD or OSC_TYPE_EXP
     int  idx;       // CMD or EXP line index (serial number)

    char  projid[17];    // ProjID for an exposure, OSC_MAX_PROJID = 16
    char  label [65];    // description of the line or field/exposure config
    char  ra    [16];    // J2000 RA  coordinate string,  hh:mm:ss.ss
    char  dec   [16];    // J2000 DEC coordinate string, +dd:mm:ss.s
    char  copt  [16];    // a character for correction option on RA/Dec pointing (0:No/1:BLG offset)
    char  imgtyp[16];    // image type definition for Exp.Config. of ICS (object/bias/dark/flat/domeflat/sky)
    char  object[33];    // object name to record in FITS header
    char  filter[16];    // filter name (or number), STRLEN_MAXFILNAME==16 (N/I/R/V/B//z/i/r/z//0/1/2/3/4)
  double  exptime   ;    // Exposure time in seconds
    UINT  secobs    ;    // the number of seconds since the Epoch, 1970-01-01 00:00:00 +0000 (UTC)  //  v0.7.0
    char  utobs [32];    // ISO UT string to start exposure, yyyy-mm-ssThh:mm:ss.s
     int  uttol     ;    // tolerance for UT_OBS in seconds, The exposure starts at UT_OBS +/-UT_TOL.
                         // NOTE: 
                         // - Optimized UT_TOL = UT_OBS_INT/2
                         // - If UT_TOL <= 0, the exp line is observed regardless of the current time.

  double  velra     ;    // RA velocity for non-sidereal tracking
  double  veldec    ;    // DEC velocity for non-sidereal tracking

  double  ra_h      ;    // RA in hours
  double  dec_d     ;    // Dec in degrees
     int  filter_n  ;    // filter slide number
  double  jdobs     ;

     int flag_movedisable;    // 1 if ra == "-" && dec == "-"

    char  cmd [OSC_MAXCMDLEN];
    char  arg [OSC_MAXARGLEN];

} CLINE;

typedef struct obsscript {

     int  flag_running;
     int  flag_paused;
     int  flag_exposing;
     int  flag_expcomplete;
     int  flag_preparenextexp;
     int  flag_additionalshot;

     int  flag_wait_for_shutreload;  // v1.2.0
     int  count_wait_for_shutreload;  // v1.2.0

     int  flag_filterchanged;
     int  count_filtercommanded;
     int  flag_projidcommanded;   // v0.6.4
     int  flag_objectcommanded;
     int  flag_exptimecommanded;
     int  flag_pointed;
     int  flag_nstchecked;
     int  count_pointing;
     int  count_tmrwaiting;  // v0.7.7

     int  flag_responseok;
     int  flag_responsecheck;
     int  count_responsecheck;
     int  count_cmdretry;

    UINT  procflags;    // bit flags for reference to process to do

     int  flag_process;
     int  count_process;
     int  interval_process;

     int  flag_delay;
     int  count_delay;   // in sec, remains

     int waiting_dome_rotation;  // v0.9.6
     int waiting_dome_shutter;  // v0.9.6

    char  filepath [STRLEN_FILE];
    char  filename [STRLEN_FILE];

   CLINE  line [OSC_MAXLINENUM+1];  //  1 line = 1 command or 1 exposure

     int  linenum;      // the number of all command and exposure lines
     int  cmdnum;       // the number of all command lines in the script
     int  expnum;       // the number of all exposure lines in the script
     int  expnum_skip;  // the number of exposure lines to skip

     int  lineidx;      // line index executing crruently or executed
     int  cmdidx;       // cmd index executing crruently or executed
     int  expidx;       // exp index executing crruently or executed
     int  restartidx;   // upcomming restart number to be commanded

     int  lastidx_expcompleted;
     int  lastidx_fitssaved;

     int  max_projid_length;
     int  max_label_length;
     int  max_object_length;
    char  reschkcmd[OSC_MAXCMDLEN];

  //char  expstart[32];  // string about time at exposure start with "Shutter=Open" message from K.IC, added for scrobs logging at v0.7.9
  //// --> moved into expinfo at v1.0.0

} COSC;

/*
# 
# NOTES:
#
# Structure of KMTNet observation script
#   - The observation script is imported with a text file including command lines and exposure lines.
#   - Exposure lines that are grouped by +LOOPSTART and +LOOPEND are repeated as many as the loop number that is previously defined with a +LOOPNUM command line.
#   - Command lines are defined with '+' identifier. (ex. "+cmd arg1 arg2 ..")
#   - Command lines systex
#     Format  ) "+<command_word> <arguments_string>"
#     Examples) "+projid eng"
#                "+tguide +50 -50"
#   - Exposure lines systex
#     Columns ) LABEL  RA  DEC  COPT  IMGTYP  OBJECT  FILTER  EXPTIME  UTOBS  UTTOL
#     Examples) BLG-NORMAL-1015  17:54:24 -31:08:00  1  object  BLG01  I 60  - -  # comments..
#               2011WO41  00:53:20.0  -27:00:00.0  0   object  S29000  R  42   2017-08-08T05:52:42  20    
#
# Descriptions of the exposure configuration line
#   - 1 line = 1 exposure, line length: not to exceed 240 characters
#   - Not case sensitive, colnum spliter = 0x20(space)
#   - Columns: LABEL RA DEC COPT IMGTYP OBJECT FILTER EXPTIME UTOBS UTTOL
#
# Descriptions of columns of exposure configuration lines
#   - LABLE  : description of the line or exposure, not FITS header keyword, 
#              ex. index#, serial#, target ID, any infomation of frame, etc.
#   - RA/DEC : J2000 RA/Dec coordinate, hh:mm:ss.ss / +dd:mm:ss.s
#   - COPT   : pointing correction option, 0 = No / 1 = BLG offset
#   - IMGTYP : image type, object / bias / dark / flat / domeflat / sky
#   - OBJECT : object name to record in FITS header
#   - FILTER : I / R / V / B / N // z / i / r / z / n // 1 / 2 / 3 / 4 / 0
#   - EXPTIME: Exposure time in seconds, Min. 0.1 seconds
#   - UTOBS  : ISO UT string yyyy-mm-ssThh:mm:ss.s or simple format yyyy-mm-ssThh:mm, to start exposure
#   - UTTOL  : tolerance for UTOBS in seconds, optimized UT_TOL = UT_OBS_INT/2, and
               if UT_TOL <= 0, the exp line is observed regardless of the current time.
#   * If UTOBS is defined with ISO UT string, the exposure starts at UTOBS +/-UTTOL.
# 
*/

//
// Exposure information structure definition (v1.0.0)
//

typedef struct expinfo { 

     int  nStatus;           // EXP_STATUS_STANDBY/TELPREP/FLUSH/EXPOSURE/READOUT/FINISH/ERROR
  double  dSetting;          // exposure time set in seconds, updated from "ICS>OBS DONE: .. ExpTime=## .." message
  double  dElapsed;          // elapsed time in seconds
  double  dStartTime;        // time stamp that exposure is started, in seconds
     int  flagStart;         // flag for setting dStartTime/strCurNum/strExpStart
     int  flagOscPre;        // indicates whether oscillating during exposure, regarding PreNum
     int  flagOscInExp;      // indicates whether oscillating during exposure, regarding CurNum
     int  cntOscInExp;       // Number of oscillation detections during exposure, regarding CurNum

    char  strStatus   [16];  // Min.  9 required, "STANDBY" / "TELPREP" / "FLUSH" / "EXPOSURE" / "READOUT" / "FINISH" / "ERROR" / "UNKNOWN"
    char  strFitsOsc  [ 8];  // Min.  6 required, "YES" / "NO" / "CHECK" - flag about oscillating during exposure, regarding FitsNum
    char  strFitsNum  [32];  // Min. 16 required, last saved FITS number, get with "ICS>OBS STATUS:    Wrote LASTFILE=/mnt/ICSData/KMTNt." message from ICS
    char  strNextNum  [32];  // Min. 16 required, FITS number for next exposure, get with "ICS>OBS DONE: EXPNUM  Filename=" message from ICS during READOUT status
    char  strCurNum   [32];  // Min. 16 required, FITS number for current exposure, copied from strNextNum at "Shutter=Open" message from K.IC
    char  strPreNum   [32];  // Min. 16 required, FITS number for previous exposure, copied from strCurNum at "ICS>OBS DONE: EXPNUM  Filename=" message
    char  strExpStart [32];  // Min. 24 required, UTC time string at exposure start, get with "Shutter=Open" message from K.IC
    char  strExpProg  [16];  // Min. 10 required, "Elapsed/Setting" in seconds integer, updated when calling cmd_expinfo()


    //// Note: updated with messages from camera system, regardless of script observation run. 

} CEXP;


//------------------------------------------------------------------------------
//
// Mecros for programming
//

// a useful alias 

#define NUL             '\0'
#define DEG2RAD         (3.141592654/180.0)
#define SEC2RAD         (DEG2RAD/3600.0)
#define RAD2DEG         (180.0/3.141592654)
#define RAD2SEC         (RAD2DEG*3600.0)
#define SQRT3           1.732050808   // square root of 3.0
#define CONST_STR_SPACE "                                                                "

// XTerm Color Printing Macros - always pair a color with TXTRESET

#define REDTEXT  printf("%c[0;31m",27)   //!< Red normal for most errors
#define GRNTEXT  printf("%c[0;32m",27)   //!< Green normal, sometimes for diagnostics
#define YELTEXT  printf("%c[0;33m",27)   //!< Yellow normal, unused (unreadable)
#define BLUTEXT  printf("%c[0;34m",27)   //!< Blue normal, process/telmove status
#define MAGTEXT  printf("%c[1;35m",27)   //!< Magenta bold for fatal errors
#define CYATEXT  printf("%c[0;36m",27)   //!< Cyan normal for warnings
#define TXTRESET printf("%c[0m",27)      //!< reset default text color

#define WHITEBG  printf("\x1b[?5l"),fflush(stdout)
#define BLACKBG  printf("\x1b[?5h"),fflush(stdout)
#define BEEP     printf("\a"),fflush(stdout)
//#define BEEP     printf("\a")
//// debugged at v0.3.6

/*
//
// TCS link state values 
//
// TCS_UP   : Telcom tcp link and PC-TCS serial telemetry input ok
// TCS_DOWN : Telcom tcp link disconnected, automatically trying to recover 
//            tcp connection with a auto-recovery interval (ArcInt)
// TCS_IDLE : PC-TCS serial link idle status (no telemetry input), 
//            running a routine for input check with select()

#define TCS_UP     1
#define TCS_DOWN   0
#define TCS_IDLE   2

// AUX link state values 

#define AUX_UP     1
#define AUX_DOWN   0
*/

// generic mecro/flags

#define UNKNOWN      -1

#define START         1
#define STOP          0

#define ON            1
#define OFF           0

#define TRUE          1
#define FALSE         0

#define ENABLED       ON
#define DISABLED      OFF

#define CMSGTYP_CONCISE       0
#define CMSGTYP_VERBOSE       1

#define NORTH  0
#define SOUTH  1
#define EAST   2
#define WEST   3

#define N  NORTH
#define S  SOUTH
#define E  EAST
#define W  WEST

// mecro func

#define UC(c)         ( ( 0x60<c && c<0x7B ) ? c-0x20 : c )
#define MAX(a,b)			(a>b?a:b)
#define MIN(a,b)			(a<b?a:b) 
#define SIGN(a)       (a<0?-1:+1)
#define ABS(f)        (f<0.0?f*-1.0:f)
#define cosd(deg)     cos(deg*DEG2RAD)


//------------------------------------------------------------------------------
//
// Application Function Prototypes 
//

// common utilities in loadconfig.c

   int  LoadConfig(const char *cfgfile);              // Load/parse the agent runtime config file
  void  InitObsScript(COSC *);                        // Initialization (zero set) the observation script data
   int  LoadObsScript(COSC *, const char *, char *);  // Load/parse the observation script file

// common utilities in commands.c

  void  KeyboardCommand(char *);                      // process keyboard commands
  void  SocketCommand(char *);                        // process message from an ISIS server/client
  char *GetOscStatus(void);                           // get string for script observation status
   int  OscCommand(const char*);                      // process a command line for script observation process
   int  ProcOsc(COSC *, obssystem_t *, obsagent_t *, char *);
  void  GetAgentInfo(char *info);                     // get information string for OBSAgent config and info
  char *GetExpInfo(void);                             // Get information string for current exposure
  void  InitExpInfo(CEXP *);                          // reset the exposure information data
  char *GetSysStatus(void);                           // get string for observation system status
  void  InitSysConfig(obssystem_t *);                 // reset the observation system configuration data
  void  ResetTcsData(obssystem_t *);                  // reset the TCS data
  void  ResetAuxData(obssystem_t *);                  // reset the AUX data
   int  QueryTcsData(obssystem_t *, char *);          // send a request msg 'tstat' to TC node for the TCS data update
   int  QueryAuxData(obssystem_t *, char *);          // send a request msg 'tstat' to TC node for the TCS data update
   int  QueryFilterLabels(obssystem_t *, char *);     // send a request msg 'filname' to TC node for the filter names update
   int  WriteObsStatus(const char *);                 // write observation status file (SYS.STATUS/EXP.INFO/OBS.Script)

// common generic utilities in commands.c

  double StopWatch(int, const char *);
  char *GetUTCTime(void);
  char *GetUTCDateTime(smctime_t *);
  char *strupr(const char *);
  void _msgout(char *);
  void _vmsgout(char *);
  void _dbgmsgout(char *);
  void _eventlog(const char *);
  void _debuglog(const char *);
  void _scrobslog(const char *);

// functions for astronomical/numerical calculation in calculation.c

double GetGst(double dJD);
double GetJd(smctime_t ut);
double GetAltitude(double HA, double Dec, double Latitude);
double GetAzimuth (double HA, double Dec, double Latitude);
double GetAirmass(double HA, double Dec, double Latitude);
void GetAltAzmAir(double HA, double Dec, double Latitude, double *Alt, double *Azm, double *Airmass);
void SetSmctime(struct tm tmtime, smctime_t *psmctime);
char trans1060(double dHour, int *pnHour, int *pnMin, double *pdSec, int nDP);


//------------------------------------------------------------------------------
//
// Global Variable Prototypes 
//

extern char cmsg[STRLEN_CMSG];

#endif

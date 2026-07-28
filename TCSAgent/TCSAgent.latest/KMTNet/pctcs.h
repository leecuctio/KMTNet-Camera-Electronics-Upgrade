#ifndef PCTCS_H
#define PCTCS_H

//
//
// Main TCS Agent header file
//
// Defaults and definitions below are defined for the KMTNet system
// 
// Author: 
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2003 February 1 (original version - Yale1m v3.3.1)
//
//   S. Cha, KASI KMTNet team
//   chasm@kasi.re.kr
//   2014 April 1 (KMTNet version)
//
// Modification History:
//   2004 Feb 17 - modified for updated ISIS system [rwp/osu]
//   2004 Jun 30 - added hooks for status flags [rwp/osu]
//   2005 May 27 - overhauled for the current system [rwp/osu]
//   2014 May 03 - modified for the KMTNet TCS [sc/kasi]
//   2014 Aug 08 - update version info from v1.1 to v1.2
//                 revised code: pctcs.h/comsoft.c/commands.c/main.c
//   2014 Aug 24 - TCS recv() timeout setting parameter definition (v1.2.2)
//                 and default TCS Input Epoch definition(hardcoded in this ver)
//                 pctcs_config.dDec (Dec in Degrees) variable added (v1.2.3)
//   2014 Aug 31 - AUX TCP response timeout changed 
//                 for the 'ACMD ALL CONNECT' command (v1.2.5)
//   2014 Sep 02 - Filter names added- in auxctrl_config for labeling on UI (v1.3.0)
//   2014 Sep 28 - Filter/Shutter operation timeout(OP_TIMEOUT) adjustment (v1.3.2)
//   2015 Jan 12 - TCS Limit status in pctcs_config to modify TCSSTATUS string,
//                 AUX Filter name in auxctrl_config to modify AUXSTATUS string (v1.4.1)
//   2015 Jan 17 - SiteID in auxctrl_config to add site info to AUXSTATUS (v1.4.2)
//   2015 Feb 12 - SiteID changed to FitsTelID (v1.4.5)
//   2015 Jul 08 - dHA, dRA added for BLG offset correction (v1.5.0)
//   2015 Jul 16 - RA/Dec object catalog data added in tcsagent_config (v1.5.1)
//   2015 Jul 22 - Elevation limit added for cmd_tmelaz() (v1.5.2)
//   2015 Oct 15 - Log file pointers added in tcsagent_config (v1.6.0)
//   2015 OCt 17 - Default TSTAT/ASTAT logging interval and verbose log option added, 
//                 FS_CmdFilNum(commanded filter#) added in auxctrl_config (v1.6.1)
//   2017 Jun 08 - DataChkMsg added in pctcs_config for logging result of check for 
//                 telemetry data field, and version update (v1.6.3)
//   2017 Jun 14 - trans1060() declaration changed (v1.6.4)
//   2017 Jun 20 - DecodingNum added in pctcs_config for modification of telemetry 
//                 data decoding code, related on recalling parse_comsoft() (v1.6.5)
//                 EncodingNum added in pctcs_config for modification of TSTAT/TCSSTATUS 
//                 string encoding code, related on recalling sprintf() to build the string
//                 in cmd_tstat and cmd_tcsstatus (v1.6.5)
//   2017 Jul 31 - String lengths, mecro names and constant values were redefined (v1.6.6)
//
//
// Notes for KMTNet TCS:
//   - Two interfaces, PCTCS Telcom and AUX control software
//   - PCTCS interface is modified with PCTCS-NG Network protocol
//   - AUX interface is added with AUX control remote commands definition
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

// Gnu readline & history utility

#include <readline/readline.h>
#include <readline/history.h>

// ISIS Client API header

#include "isisclient.h"

// In case the version and compilation data are not defined
// at compilation, put in some placeholders to prevent code barfing

#define APP_VER "v1.7.2"  // v1.7.2.0

#ifndef APP_VERSION
#define APP_VERSION APP_VER
#endif

#ifndef APP_COMPDATE
#define APP_COMPDATE "2014-09-02"
#endif

#ifndef APP_COMPTIME
#define APP_COMPTIME "00:00:00"
#endif

// various site-dependent but system-independent default values 

#define DEFAULT_MYID      "TC"
#define DEFAULT_MYPORT    6606
#define DEFAULT_RCFILE    "/home/dts/Config/pctcs.ini"
#define DEFAULT_CATFILE   "/home/dts/catalog/pctcs.cat"
#define DEFAULT_LOGFILE   "/data/Logs/TC/tc"               
#define TEMP_LOGFILE      "/data/Logs/TC/tc.temp.log"
    // NOTE: ".type.date.time.log" will be appended at the end of DEFAULT_LOGFILE
    // Default file name of Event Log: "/data/Logs/TC/tc.event.yyyymmdd.hhmmss.log"
    // Default file name of TSTAT Log: "/data/Logs/TC/tc.tstat.yyyymmdd.hhmmss.log"
    // Default file name of ASTAT Log: "/data/Logs/TC/tc.astat.yyyymmdd.hhmmss.log"

#define DEFAULT_CORTABLE_BLGOFF  "/home/dts/cortable/offset_blg.table"  //v1.5.1

// typical ISIS server defaults (not used if in STANDALONE mode)

#define DEFAULT_ISISHOST  "localhost"
#define DEFAULT_ISISPORT  6600
#define DEFAULT_ISISID    "IS"

// default PCTCS Telcom server and AUX control server info

#define DEFAULT_TCS_HOST   "KMTNet.TCS.AUX"
#define DEFAULT_TCS_PORT    5750
#define DEFAULT_AUX_HOST   "KMTNet.TCS.AUX"
#define DEFAULT_AUX_PORT    5752

#define DEFAULT_TCS_TELID  "KMTNET"
#define DEFAULT_TCS_SYSID  "TCS"
#define DEFAULT_AUX_TELID  "KMTNET"
#define DEFAULT_AUX_SYSID  "AUX"

#define DEFAULT_FITS_TELID "KMTN"

// default TCS & AUX telemetry update & status logging interval (in seconds)

#define DEFAULT_UPINT_TCS     1.0
#define DEFAULT_UPINT_AUX     0.2
#define DEFAULT_LOGINT_TCS  300.0
#define DEFAULT_LOGINT_AUX  300.0

//
// Default TCS Timeout Interval (in seconds)
//
// TCS Agent will declare the PCTCS serial link "idle" and link status "IDLE"
//  if there has been no telemetry in the interval Timeout_PCTCS.
// TCS Agent will declare the Telcom TCP link "down" and link status "DOWN" 
//  if there has been no resopnse from Telcom in the interval Timeout_Telcom.
// TCS Agent will declare the AUX TCP link "down" and link status "DOWN" 
//  if there is no resopnse from AUX or TCP connection is disconnected.
// The actual timeout will be overriden by any set in the runtime config file.
//

#define DEFAULT_TIMEOUT_PCTCS    5
#define DEFAULT_TIMEOUT_TELCOM   8

// default TCS & AUX tcp links auto recovery mode setting (On:1, Off:0)

#define DEFAULT_AUTORECOVERY_TCS  1
#define DEFAULT_AUTORECOVERY_AUX  1

// default TCS & AUX links auto recovery try interval (in second)

#define DEFAULT_ARCINT     2.0

// default HW configuration

#define DEFAULT_TCS_GUIDE_STEP_RA      0.00503608
#define DEFAULT_TCS_GUIDE_STEP_DEC     0.01321939
#define DEFAULT_TCS_GUIDE_MINOFF_RA    0.01        // +/-0.01 arcsec
#define DEFAULT_TCS_GUIDE_MINOFF_DEC   0.02        // +/-0.02 arcsec
#define DEFAULT_AUX_FILTER_OPTIME     20.0
#define DEFAULT_AUX_CSHUTT_OPTIME     12.0
#define DEFAULT_AUX_ACTNUM_SOUTH       2
#define DEFAULT_AUX_ACTNUM_EAST        1
#define DEFAULT_AUX_ACTNUM_WEST        3

// default TCS Agent client application runtime flags (On:1, Off:0)

#define DEFAULT_VERBOSE     0     // default: not verbose (concise)
#define DEFAULT_DEBUG       0     // default: no debugging mode
#define DEFAULT_DOLOG       0     // default: runtime logging disabled
#define DEFAULT_LOGVERBOSE  1     // default: enable verbose log

// END of Site-Dependent Setup

//------------------------------------------------------------
//
// Touch the stuff below this at your own risk..
//

// Definitions for PC-TCS & Telcom communication control

#define MIN_UPDATEINT_TCS  0.5  // tcs minimum update interval in seconds
#define MIN_UPDATEINT_AUX  0.1  // aux minimum update interval in seconds
#define MIN_ARCINT         0.5  // minimum auto-recovery try interval in sec
#define MIN_LOGINT_TCS     1.0  // minimum TSTAT logging interval in sec
#define MIN_LOGINT_AUX     0.2  // minimum ASTAT logging interval in sec

#define MIN_TCSBUF  104  // minimum size a TCS telemetry packet must have to be parsable
#define PID_OPTCMD  100  // Telcom packet ID for operating command
#define PID_REQCMD  900  // Telcom packet ID for telemetry request

#define MAX_GUIDEOFFSET_RA   (3.0*3600.0)  // +/-3 degree
#define MAX_GUIDEOFFSET_DEC  (3.0*3600.0)  // +/-3 degree
#define MAX_OFFSETMOVE_RA     6.0          // +/-6 hour
#define MAX_OFFSETMOVE_DEC  120.0          // +/-120 degree
#define MIN_ELEVATION        25.0          // Elevation lower limit (1.5.2)

#define TCS_INPUT_EPOCH      2000.0
#define TCS_DECODINGNUM         3    // Max attempts num for parse_comsoft() recall (v1.6.5)
#define TCS_ENCODINGNUM         3    // Max attempts num for encodding TSTAT/TCSSTATUS str
#define TCS_TSTATLENGTH       137    // normal length of TSTAT string when Link = UP
#define TCS_TCSSTATUSLEN      217    // normal length of TCSSTATUS string when Link = UP

// Definitions for AUX communication control & HW spec

#define MAX_DELTAFOCUS     30.0    // +/-30 mm
#define MAX_FOCUSRANGE     15.0    // +/-15 mm
#define MAX_DELTATILT    5000.0    // +/-5000 arcsec ~ 1.4 deg (Max. @ h.diff. = 60 mm)
#define MAX_TILTRANGE    2500.0    // +/-2500 arcsec ~ 0.7 deg (Max. @ h.diff. = 30 mm)
#define MIN_ACTRESOL        0.001  // +/-0.001 mm

#define RAC  1008.8    // radius of the actuator circle in mm
#define FOP_TIMEOUT      2.0  // (filter operating timeout - OpTimeConfig) in seconds
#define SOP_TIMEOUT      1.0  // (shutter operating timeout - OpTimeConfig) in seconds

// Message handling select() Time intervals and monitoring setting

#define SELECT_TIMEOUT        50    // select() timeout for input-waiting in msec
#define SELECT_ERR_IGNORE_NUM  0    // select() error number for no msg print

// Display settings

#define DISPLAY_DELAY          1    // in telemetry update cycle

// TCP/IP recv() timeout setting

#define TCP_TIMEOUT_TCSCMD_SEC   3  // in sec
#define TCP_TIMEOUT_TCSCMD_MS  500  // in mille seconds
#define TCP_TIMEOUT_AUX_SEC      3  // in sec
#define TCP_TIMEOUT_AUX_MS     500  // in mille seconds

// String lengths, mecro names and constant values were redefined at v1.6.6.3 

#define STRLEN_CMD         256    // Keyboard/ISIS command string length
#define STRLEN_ARG         256    // Keyboard/ISIS command's argument field length
#define STRLEN_REP        1024    // reply string size, must be larger that info or auxstatus
#define STRLEN_TSTAT       256    // TSTAT string size
#define STRLEN_MAXKEYIN    256    // Maximum length of Keyboard input message string
#define STRLEN_MAXSOCIN   1004    // Maximum length of ISIS input message string
#define STRLEN_FILE        512
#define STRLEN_CMSG       1024
#define STRLEN_DATACHK     128

#define STRLEN_ISISSTAT    128          // size of STATUS string to report to ISIS nodes
#define STRLEN_ISISADDR     32          // maximum size of ICIMACS(ISIS) command type string
#define STRLEN_ISISTYPE     64          // maximum size of ICIMACS(ISIS) command type string
#define STRLEN_ISISNODE  ISIS_NODESIZE  // maximum size of ICIMACS(ISIS) node ID, 8+1
#define STRLEN_ISISMSG   ISIS_MSGSIZE   // ISIS mesage size using ISIS Lib. function, 
                                        // must be larger that ISIS_MSGSIZE (2048)

#define CMDBUFLEN   512    // TCS/AUX command/recv buffer length, used in TCS/AUX cmd proc func
#define ARGBUFLEN    64    // TCS/AUX command's argument field buffer length


// Maximum Line/Data number

#define MAXCFGLINE     128      // maximum mumber of characters/line of the file
#define MAXCATNUM    20000      // maximum catalog line number

// For pointing model measurement (v1.5.5)

#define PM_PSCALE      0.4      // pixel scale in arc-sec/pixel
#define PM_OFF_X0      230      // y offset from image center
#define PM_OFF_Y0      475      // y offset from image center
#define PM_OFF_X1      576      // x offset from (0,0) corner
#define PM_OFF_Y1      576      // x offset from (0,0) corner
#define PM_COO_X0     9432      // x of (0,0) corner
#define PM_COO_Y0     9232      // y of (0,0) corner
#define PM_ERRCHK      999      // allowed range from est.star coord in pixel

//
// Memo about K strip #8
//  - X start = 8281 / end = 9432
//  - Y start =    0 / end = 9232
//  - X width = 9432-8280 = 1152
//  - Center  = 1152/2 = 576
//  - Quarter = 1152/4 = 288
//  - X center  = 9432-576 = 8856
//  - Y center  = 9232-576 = 8656
//  - X quarter = 9432-288 = 9144
//  - Y quarter = 9232-288 = 8944
//

//------------------------------------------------------------------------------
//
// Application global system table structure 
//
// parameters are loaded from the pctcs.ini file
//

//
// TCS Agent structure for application diagnostic data
//

typedef struct tcsagent_config {

  char   StartTime[24];          // UTC time server started
  char   UserID[64];             // user ID that launched TCSAgent 
  char   exeFile[STRLEN_FILE];   // rootname(path/name) of executable file   
  char   AppVersion[64];         // Application version
  char   CatFile[STRLEN_FILE];   // RA/Dec obj cat rootname for initially importing
  char   CatObj[MAXCATNUM][64];  // Object name field of RA/Dec object Catalog
  char   CatRA[MAXCATNUM][32];   // RA  coordinate string of RA/Dec object Catalog
  char   CatDec[MAXCATNUM][32];  // DEC coordinate string of RA/Dec object Catalog
  char   CatCopt[MAXCATNUM];     // Correction option character of RA/Dec object Catalog
  int    CatDataNum;             // Imported data number of RA/Dec object Catalog
//  CATLOG*   Catlog; <-- reserved at v1.6.6.4

  double ArcTick;                // time of last links auto recovery try
  double ArcIdle;                // seconds since last links auto recovery try
  double ArcInt;                 // Auto Recovery try interval

  FILE*  LogMsg;                 // All message and event Log file pointer
  int    LogVerbose;             // Flag to disable verbose log

  FILE*  LogTcs;                 // TCS Status Log file pointer
  double LogTcsInt;              // TCS status logging interval
  double LogTcsIdle;             // seconds since last TCS status logging
  double LogTcsTick;             // time of last TCS status logging

  FILE*  LogAux;                 // AUX Status Log file pointer
  double LogAuxInt;              // AUX status logging interval
  double LogAuxIdle;             // seconds since last AUX status logging
  double LogAuxTick;             // time of last AUX status logging

} tcsagent_t;

//
// TCS (PC-TCS & Telcom) configuration and control structure
//

typedef struct pctcs_config {

  // PC-TCS Telcom server info

  int    FDtel;                 // Telcom tcp socket's file descriptor for telemetry
  int    FDcmd;                 // Telcom tcp socket's file descriptor for commanding
  char   Host[64];              // Telcom server's host name or IP address
  int    PortNum;               // Telcom server's port number
  sockaddr_in Addr;             // Telcom server's tcp socket address database

  // Telcom TCP and PC-TCS serial interface info

  char   TelID[64];             // telescope ID for PCTCS-NG protocol with Telcom
  char   SysID[64];             // system ID for PCTCS-NG protocol with Telcom
  int    Link;                  // PC-TCS & Telcom interface status (UP/IDLE/DOWN)
  double PctcsTick;             // time of last successful TCS telemetry data update
  double PctcsIdle;             // seconds since last successful TCS telemetry data update
  int    PctcsTimeout;          // PC-TCS link idle timeout in seconds
  double TelcomTick;            // time of last successful tcp communication with Telcom
  double TelcomIdle;            // seconds since last successful tcp communication
  int    TelcomTimeout;         // Telcom tcp link idle timeout in seconds
  double UpdateTick;            // time of last command for TCS telemetry request
  double UpdateIdle;            // seconds since last command for TCS telemetry request
  double UpdateInt;             // interval of command for TCS telemetry request
  int    UpdateFlag;            // flag for checking execution code update after op command
  int    ArcMode;               // Telcom tcp link auto recovery mode(On:1, Off:0)

  // Telemetry request command and data packet info

  char   RequestMsg[CMDBUFLEN];    // telemetry request command packet message
  int    RequestLen;               // telemetry request command packet length
  int    MinTelemetryLen;          // minimum telemetry data packet length
  int    ReqHedLen;                // request cmd header(TelID+SysID+PID) length

  // PC-TCS Telemetry Data

  char RA[32];                     // Right Ascension in hh:mm:ss.s format
  char Dec[32];                    // Declination in +dd:mm:ss.s format
  char HA[32];                     // Hour Angle in hh:mm:ss.s format
  char LST[32];                    // Local Siderial Time in hh:mm:ss.s format
  char SecZ[32];                   // SecZ [dimensionless]
  char Equinox[32];                // Epoch (really equinox) in years
  char Date[32];                   // UTC Date in ccyy-mm-dd format, received packet
  char UTC[32];                    // UTC time in hh:mm:ss.sss, received packet
  char Alt[32];                    // Altitude in degrees
  char Az[32];                     // Azimuth in degrees
  char RawPacket[CMDBUFLEN];       // Raw telemetry packet
  char DataChkMsg[STRLEN_DATACHK]; // Result of Alt,Az,SecZ,RA,DEC data/string check
  int  DecodingNum;                // Iteration number of telemetry data decoding
  int  EncodingNum;                // Iteration number of TSTAT/TCSSTATUS encoding
  int  MoveStatus;                 // Move status (No:0, RA:1, DEC:2, Both:3)
  int  LimitStatus;                // Limit status (No:0, RA:1, DEC:2, Horizon:3)
  int  RALimit;                    // 0 if OK, 1 if at RA limit
  int  DecLimit;                   // 0 if OK, 1 if at Dec limit
  int  HorizonLimit;               // 0 if OK, 1 if at Horizon limit
  int  DriveDisable;               // 0 if OK, 1 if disabled
  int  Moving;                     // 1 if telescope is in motion, 0 otherwise
  int  ComNum;                     // current com channel number of PC-TCS (0~8)
  char ExeCode;                    // 'e'/'E' if prev cmd was executed succefully,
                                   // '3' if the last command was unrecognized
  double dHA;
  double dRA;
  double dDec;

  // PC-TCS HW configuration

  double GuideStepRA;            // RA  guide step unit in arcsec/step
  double GuideStepDec;           // Dec guide step unit in arcsec/step
  double GuideMinOffRA;          // minimum guiding offset, if commanded offset is
  double GuideMinOffDec;         //  smaller, TCS Agent will ignore the tguide cmd

} pctcs_t;

//
// AUX configuration and control structure
//

typedef struct auxctrl_config {

  // AUX control remote commmand server info

  int    FD;                     // AUX tcp socket's file descriptor
  char   Host[64];               // AUX server IP address
  int    PortNum;                // AUX server port number
  sockaddr_in Addr;              // AUX server's socket address database

  // AUX control server TCP interface info

  char   TelID[64];              // telescope ID for AUX remote commands
  char   SysID[64];              // system ID for AUX remote commands
  int    Link;                   // AUX tcp interface staus (UP/DOWN)
  double UpdateTick;             // time of last AUX telemetry data update
  double UpdateIdle;             // seconds since last AUX telemetry data update
  double UpdateInt;              // AUX telemetry update interval
  int    ArcMode;                // AUX tcp link auto recovery mode (On:1, Off:0)
  char   FitsTelID[64];          // Telescope ID, got from pctcs.ini temporary (v1.4.2)
                                 // and got from AUX SW at InitAUX() finally (v1.5.x ?)

  char   Date[32];               // UTC Date in ccyy-mm-dd format, update completed
  char   UTC[32];                // UTC time in hh:mm:ss.sss, update completed
  int    Statuses[6];            // connection and operation statuses for each subsystem
  int    FS_Limits[6];           // filter & shutter limit status
  int    FS_CmdFilNum;           // commanded filter number
  int    FS_FilterNum;           // current filter number
  char   FS_FilterName[16];      // current filter name
  int    FS_FilterOpStat;        // filter slide operation status
  double FS_FilterOpTime;        // filter slide operation time
  int    FS_ShutStatus;          // camera shutter status(open/closed)
  int    FS_ShutOpStat;          // camera shutter operation status
  double FS_ShutOpTime;          // canera shutter operation time with HW spec
  char   FS_FilNames[6][16];     // Filter names for slide 1~4 for labeling on UI
  int    FA_Limits[3];           // focuser actuator limit status (0:no,1:out,2:in,3:both)
  double FA_Positions[3];        // focuser actuator position in millimeters
  int    FA_ActNums[3];          // actuator number for the orientation (1/2/3)
  double FA_ActPoss[3];          // actuator positions for the each orientation
  int    FA_ActLims[3];          // actuator limit statuses for the each orientation
  double FA_Focus;               // focus position at the center of detector (on axis)
  double FA_TiltNS;              // North-South tilt in arcsec, if +, N is higher than S
  double FA_TiltEW;              // East-West tilt in arcsec, if +, E is higher than W
  int    DS_LimitUpper;          // upper dome shutter limit status
  int    DS_LimitLower;          // lower dome shutter limit status
  int    DS_LimitSafety;         // safety interlock switch status
  int    DS_AutoSync;            // dome shutter Auto-sync mode (Enabled:1, Disabled:0)
  double DS_ShutAlt;             // upper shutter altitude in degrees
  double DS_TeleAlt;             // telescope altitude that AUX read form Telcom in deg
  int    MC_Position;            // mirror cover position in percentages
  int    CH_Cooling;             // chiller cooling switch status (On:1, Off:0)
  double CH_Setpoint;            // chiller setpoint temperature in deg C
  double CH_ProcTemp;            // chiller processed temperature in deg C
  int    EN_FanRelay;            // mirror cooling fan relay status (On:1, Off:0)
  double EN_Sensors[7];          // environment sersors value in deg C or RH %

  // (abbreviations)
  // FS: Filter/Shutter box
  // FA: Focus Actuator
  // DS: Dome Shutter
  // MC: Mirror Cover
  // CH: Chiller for mirror cooling
  // EN: Environment monitor

} auxctrl_t;

//
// date time data structure
//

typedef struct systime {
  int year;
  int month;
  int day;
  int hour;
  int min;
  double sec;
} systime_t;

//------------------------------------------------------------------------------
//
// Definitions for programming
//

// a useful alias 

#define NUL             '\0'
#define DEG2RAD         (3.141592654/180.0)
#define SEC2RAD         (DEG2RAD/3600.0)
#define RAD2DEG         (180.0/3.141592654)
#define RAD2SEC         (RAD2DEG*3600.0)
#define SQRT3           1.732050808   // square root of 3.0

// XTerm Color Printing Macros - always pair a color with TXTRESET

#define REDTEXT  printf("%c[0;31m",27)   //!< Red normal for most errors
#define GRNTEXT  printf("%c[0;32m",27)   //!< Green normal, sometimes for diagnostics
#define YELTEXT  printf("%c[0;33m",27)   //!< Yellow normal, unused (unreadable)
#define BLUTEXT  printf("%c[0;34m",27)   //!< Blue normal, process/telmove status
#define MAGTEXT  printf("%c[1;35m",27)   //!< Magenta bold for fatal errors
#define CYATEXT  printf("%c[0;36m",27)   //!< Cyan normal for warnings
#define TXTRESET printf("%c[0m",27)      //!< reset default text color

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

//
// Definitions for AUX control
//

// generic mecro for AUX statues

#define AUX_UNKNOWN  -1

// Status for connection and operation

#define AUX_STATUS_NC         10  // not connected
#define AUX_STATUS_STANDBY    11  // connected & standby
#define AUX_STATUS_RUNNING    12  // connected & running
#define AUX_STATUS_ERROR      13  // a error was occured

// Index for statuses of subsys

#define AUX_IDX_FS             0  // FS: Filter/Shutter box
#define AUX_IDX_FA             1  // FA: Focus Actuator
#define AUX_IDX_DS             2  // DS: Dome Shutter
#define AUX_IDX_MC             3  // MC: Mirror Cover
#define AUX_IDX_CH             4  // CH: Chiller for mirror cooling
#define AUX_IDX_EN             5  // EN: Environment monitor
#define AUX_IDX_AL             6  // AL: ALL subsystems

// Index for filter/shutter & focuse actuator
// NOTE: These definitions must not be changed for cmd-process routines in commands.c

#define AUX_IDX_FS_F1          0  // F1: Filter slide #1
#define AUX_IDX_FS_F2          1  // F2: Filter slide #2
#define AUX_IDX_FS_F3          2  // F3: Filter slide #3
#define AUX_IDX_FS_F4          3  // F4: Filter slide #4
#define AUX_IDX_FS_SH          4  // SH: Half shutter <SL2>
#define AUX_IDX_FS_SF          5  // SF: Full shutter <SL1>
#define AUX_IDX_FA_A1          0  // A1: Actuator #1
#define AUX_IDX_FA_A2          1  // A2: Actuator #2
#define AUX_IDX_FA_A3          2  // A3: Actuator #3

// Value for Limit status of focus filter slide, camera shutter and focus acutator

#define AUX_BILIMIT_NO         0  // inner=off  outer=off
#define AUX_BILIMIT_IN         2  // inner=on   outer=off
#define AUX_BILIMIT_OUT        1  // inner=off  outer=on
#define AUX_BILIMIT_BOTH       3  // inner=on   outer=on

// Value for filter slide number (FS_FiltrNum)

#define AUX_FS_FNUM_NO         0    // no filter
#define AUX_FS_FNUM_F1         1    // filter #1
#define AUX_FS_FNUM_F2         2    // filter #2
#define AUX_FS_FNUM_F3         3    // filter #3
#define AUX_FS_FNUM_F4         4    // filter #4
#define AUX_FS_FNUM_MANY       5    // more than 2 filters
#define AUX_FS_FNAME_NO        "NO"
#define AUX_FS_FNAME_MANY      "MANY"
#define AUX_FS_FNAME_UNKNOWN   "UNKNOWN"

// Status for filter operation (FS_FiltrOp)

#define AUX_FS_FOP_NC         20    // not connected to the device
#define AUX_FS_FOP_STANDBY    21    // standby
#define AUX_FS_FOP_RUNNING    22    // running
#define AUX_FS_FOP_ERROR      23    // error - OpTime timeout

// Status for camera shutter open/closed (FS_ShutStatus)

#define AUX_FS_SHUT_OPEN      30    // open
#define AUX_FS_SHUT_CLOSED    31    // closed

// Status for camera shutter operation (FS_ShutOp)

#define AUX_FS_SOP_NC         40    // not connected to the device
#define AUX_FS_SOP_STANDBY    41    // standby
#define AUX_FS_SOP_OPENING    42    // opening
#define AUX_FS_SOP_OPENED     43    // waiting (for close cmd)
#define AUX_FS_SOP_CLOSING    44    // closing
#define AUX_FS_SOP_RELOADING  45    // reloading
#define AUX_FS_SOP_ERROR      46    // error - timeout for OpTime
#define AUX_FS_SOP_STANDBY_FORCED  49    // for temporary optimization at v1.3.2.temp

// Status for dome shutter limits

#define AUX_DS_LIMIT_OPENED   50
#define AUX_DS_LIMIT_CLOSED   51
#define AUX_DS_LIMIT_MIDDLE   52
#define AUX_DS_LIMIT_ACTIVE   53
#define AUX_DS_LIMIT_INACTI   54

// generic flags

#define START         1
#define STOP          0

#define ON            1
#define OFF           0

#define ENABLED       ON
#define DISABLED      OFF

#define SOUTH         0
#define EAST          1
#define WEST          2

#define CMSGTYP_CONCISE       0
#define CMSGTYP_VERBOSE       1

// mecro func

#define UC(c)         ( ( 0x60<c && c<0x7B ) ? c-0x20 : c )
#define MAX(a,b)			(a>b?a:b)
#define MIN(a,b)			(a<b?a:b) 
#define SIGN(a)       (a<0?-1:+1)


//------------------------------------------------------------------------------
//
// Application Function Prototypes 
//

// common client utilities

   int  LoadConfig(const char *cfgfile);   // Load/parse the agent runtime config file
   int  LoadCatalog(const char *, char *); // Load/parse the RA/DEC object catalog file
  void  KeyboardCommand(char *);           // process keyboard commands
  void  SocketCommand(char *);             // process message from an ISIS server/client
  void  SendStatus(char *);                // send a STATUS/ERROR message to configured node

// common utilities in commands.c

double  StopWatch(int, const char *);
  char *GetUTCTime(void);
  char *GetUTCDateTime(systime_t *);
  char *strupr(const char *);
//char  trans1060(double , int *, int *, double *);
  char  trans1060(double , int *, int *, double *, int );  // v1.6.4
  void  GetTstatStr(char *buf);
  void  GetAstatStr(char *buf);
  void _msgout(char *);
  void _vmsgout(char *);
  void _msglog(const char *);
  void _tcslog(const char *);
  void _auxlog(const char *);

// TCS command processes (subroutines) in commands.c

int TcsSetEpoch(pctcs_t *tcs, char *reply);   // used in main()

// AUX update and command processes in commands.c

   int  AuxTelemetry(auxctrl_t *, char *);
   int  AuxFilterNameUpdate(auxctrl_t *aux, char *reply);  // v1.3.0
   int  AuxStatusVal(char *);
  char *AuxStatusArg(int);

// I/O routines for PC-TCS, Telcom, & AUX ctrl interaction in comsoft.c

   int  parse_comsoft(pctcs_t *, char *);
  void  UpdateTcsMoving(pctcs_t *);
   int  InitPCTCS(pctcs_t *, char *);
  void  ClearPCTCS(pctcs_t *);
   int  InitAUX(auxctrl_t *, char *);
  void  ClearAUX(auxctrl_t *);
  void  ClearAuxData(auxctrl_t *, int);
  char *GetAuxSubsysName(int);

//------------------------------------------------------------------------------
//
// Global Variable Prototypes 
//

extern char cmsg[STRLEN_CMSG];

#endif

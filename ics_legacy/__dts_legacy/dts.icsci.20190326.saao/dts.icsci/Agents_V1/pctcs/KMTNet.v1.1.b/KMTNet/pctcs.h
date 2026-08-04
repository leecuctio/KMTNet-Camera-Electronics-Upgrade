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
//
// Notes for KMTNet TCS:
//   - Two interfaces, PCTCS Telcom and AUX control software
//   - PCTCS interface is modified with PCTCS-NG Network protocol
//   - AUX interface is added with AUX control remote commands definition
// 
//
//---------------------------------------------------------------------------

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

#define APP_VER "v1.1"

#ifndef APP_VERSION
#define APP_VERSION APP_VER
#endif

#ifndef APP_COMPDATE
#define APP_COMPDATE "2014-04-01"
#endif

#ifndef APP_COMPTIME
#define APP_COMPTIME "00:00:00"
#endif

// various site-dependent but system-independent default values 

#define DEFAULT_MYID      "TC"
#define DEFAULT_MYPORT    6606
#define DEFAULT_RCFILE    "/home/dts/Config/pctcs.ini"
#define DEFAULT_LOGFILE   "/data/Logs/pctcs.log"

// typical ISIS server defaults (not used if in STANDALONE mode)

#define DEFAULT_ISISHOST  "localhost"
#define DEFAULT_ISISPORT  6600
#define DEFAULT_ISISID    "IS"

// default PCTCS Telcom server and AUX control server info

#define DEFAULT_TCS_HOST  "KMTNet.TCS.AUX"
#define DEFAULT_TCS_PORT   5750
#define DEFAULT_AUX_HOST  "KMTNet.TCS.AUX"
#define DEFAULT_AUX_PORT   5752

#define DEFAULT_TCS_TELID "KMTNET"
#define DEFAULT_TCS_SYSID "TCS"
#define DEFAULT_AUX_TELID "KMTNET"
#define DEFAULT_AUX_SYSID "AUX"

// default TCS & AUX info update interval (in seconds)

#define DEFAULT_UPINT_TCS  1.0
#define DEFAULT_UPINT_AUX  0.2

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
#define DEFAULT_TIMEOUT_TELCOM   7

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

#define DEFAULT_VERBOSE  0   // default: not verbose (concise)
#define DEFAULT_DEBUG    0   // default: no debugging mode
#define DEFAULT_DOLOG    0   // default: runtime logging disabled

// END of Site-Dependent Setup

//----------------------------------------------------------------
//
// Touch the stuff below this at your own risk..
//

// Definitions for PC-TCS & Telcom communication control

#define MIN_UPDATEINT_TCS  0.5  // tcs minimum update interval in seconds
#define MIN_UPDATEINT_AUX  0.1  // aux minimum update interval in seconds
#define MIN_ARCINT         0.5  // minimum auto-recovery try interval in sec

#define MIN_TCSBUF  104  // minimum size a TCS telemetry packet must have to be parsable
#define PID_OPTCMD  100  // Telcom packet ID for operating command
#define PID_REQCMD  900  // Telcom packet ID for telemetry request

#define MAX_GUIDEOFFSET_RA   (3600.0*30)  // +/-30 degree
#define MAX_GUIDEOFFSET_DEC  (3600.0*30)  // +/-30 degree
#define MAX_OFFSETMOVE_RA    2  // +/-2 hour
#define MAX_OFFSETMOVE_DEC  30  // +/-30 degree

// Definitions for AUX communication control & HW spec

#define MAX_DELTAFOCUS     30.0    // +/-30 mm
#define MAX_FOCUSRANGE     15.0    // +/-15 mm
#define MAX_DELTATILT    5000.0    // +/-5000 arcsec ~ 1.4 deg (Max. @ h.diff. = 60 mm)
#define MAX_TILTRANGE    2500.0    // +/-2500 arcsec ~ 0.7 deg (Max. @ h.diff. = 30 mm)
#define MIN_ACTRESOL        0.001  // +/-0.001 mm

#define RAC  1008.8    // radius of the actuator circle in mm
#define FOP_TIMEOUT      6.0  // filter operating timeout in seconds
#define SOP_TIMEOUT      3.0  // shutter operating timeout in seconds

// Time intervals for application setting

#define SELECT_TIMEOUT  50    // select() timeout for input-waiting in msec
#define DISPLAY_DELAY    2    // in seconds

// String sizes 

#define POSIX
#define BUF_SIZE          2048
#define LONG_STR_SIZE     4096  // a long string
#define MED_STR_SIZE      256   // a medium-sized string
#define BIG_STR_SIZE      512   // bigger than medium, smaller than long
#define SHORT_STR_SIZE    32    // a short string
#define ICIMACS_HOST_SIZE 9     // maximum size of ICIMACS host names 8+1
#define MAX_MSG_SIZE      256   // maximum message buffer size

#define CMDBUFLEN  512
#define ARGBUFLEN  256

//---------------------------------------------------------------------------
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
  char   UserID[SHORT_STR_SIZE]; // user ID that launched TCSAgent 
  char   exeFile[MED_STR_SIZE];  // path/name of executable file   
  char   AppVersion[64];         // Application version
  double ArcTick;                // time of last links auto recovery try
  double ArcIdle;                // seconds since last links auto recovery try
  double ArcInt;                 // Auto Recovery try interval

} tcsagent_t;

//
// TCS (PC-TCS & Telcom) configuration and control structure
//

typedef struct pctcs_config {

  // PC-TCS Telcom server info

  int    FDtel;                 // Telcom tcp socket's file descriptor for telemetry
  int    FDcmd;                 // Telcom tcp socket's file descriptor for commanding
  char   Host[SHORT_STR_SIZE];  // Telcom server's host name or IP address
  int    PortNum;               // Telcom server's port number
  sockaddr_in Addr;             // Telcom server's tcp socket address database

  // Telcom TCP and PC-TCS serial interface info

  char   TelID[SHORT_STR_SIZE]; // telescope ID for PCTCS-NG protocol with Telcom
  char   SysID[SHORT_STR_SIZE]; // system ID for PCTCS-NG protocol with Telcom
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

  char   RequestMsg[MAX_MSG_SIZE]; // telemetry request command packet message
  int    RequestLen;               // telemetry request command packet length
  int    MinTelemetryLen;          // minimum telemetry data packet length
  int    ReqHedLen;                // request cmd header(TelID+SysID+PID) length

  // PC-TCS Telemetry Data

  char RA[SHORT_STR_SIZE];       // Right Ascension in hh:mm:ss.s format
  char Dec[SHORT_STR_SIZE];      // Declination in +dd:mm:ss.s format
  char HA[SHORT_STR_SIZE];       // Hour Angle in hh:mm:ss.s format
  char LST[SHORT_STR_SIZE];      // Local Siderial Time in hh:mm:ss.s format
  char SecZ[SHORT_STR_SIZE];     // SecZ [dimensionless]
  char Equinox[SHORT_STR_SIZE];  // Epoch (really equinox) in years
  char Date[SHORT_STR_SIZE];     // UTC Date in ccyy-mm-dd format, received packet
  char UTC[SHORT_STR_SIZE];      // UTC time in hh:mm:ss.sss, received packet
  char Alt[SHORT_STR_SIZE];      // Altitude in degrees
  char Az[SHORT_STR_SIZE];       // Azimuth in degrees
  char RawPack[BUF_SIZE];        // Raw telemetry packet
  int  MoveStatus;               // Move status (No:0, RA:1, DEC:2, Both:3)
  int  RALimit;                  // 0 if OK, 1 if at RA limit
  int  DecLimit;                 // 0 if OK, 1 if at Dec limit
  int  HorizonLimit;             // 0 if OK, 1 if at Horizon limit
  int  DriveDisable;             // 0 if OK, 1 if disabled
  int  Moving;                   // 1 if telescope is in motion, 0 otherwise
  int  ComNum;                   // current com channel number of PC-TCS (0~8)
  char ExeCode;                  // 'e'/'E' if prev cmd was executed succefully,
                                 // '3' if the last command was unrecognized
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
  char   Host[SHORT_STR_SIZE];   // AUX server IP address
  int    PortNum;                // AUX server port number
  sockaddr_in Addr;              // AUX server's socket address database

  // AUX control server TCP interface info

  char   TelID[SHORT_STR_SIZE];  // telescope ID for AUX remote commands
  char   SysID[SHORT_STR_SIZE];  // system ID for AUX remote commands
  int    Link;                   // AUX tcp interface staus (UP/DOWN)
  double UpdateTick;             // time of last AUX telemetry data update
  double UpdateIdle;             // seconds since last AUX telemetry data update
  double UpdateInt;              // AUX telemetry update interval
  int    ArcMode;                // AUX tcp link auto recovery mode (On:1, Off:0)

  // AUX telemetry data of each subsystem

  char   Date[SHORT_STR_SIZE];  // UTC Date in ccyy-mm-dd format, update completed
  char   UTC[SHORT_STR_SIZE];   // UTC time in hh:mm:ss.sss, update completed
  int    Statuses[6];           // connection and operation statuses for each subsystem
  int    FS_Limits[6];          // filter & shutter limit status
  int    FS_FilterNumber;       // current filter number
  int    FS_FilterOpStat;       // filter slide operation status
  double FS_FilterOpTime;       // filter slide operation time
  int    FS_ShutStatus;         // camera shutter status(open/closed)
  int    FS_ShutOpStat;         // camera shutter operation status
  double FS_ShutOpTime;         // canera shutter operation time with HW spec
  int    FA_Limits[3];          // focuser actuator limit status (0:no,1:out,2:in,3:both)
  double FA_Positions[3];       // focuser actuator position in millimeters
  int    FA_ActNums[3];         // actuator number for the orientation (1/2/3)
  double FA_ActPoss[3];         // actuator positions for the each orientation
  int    FA_ActLims[3];         // actuator limit statuses for the each orientation
  double FA_Focus;              // focus position at the center of detector (on axis)
  double FA_TiltNS;             // North-South tilt in arcsec, if +, N is higher than S
  double FA_TiltEW;             // East-West tilt in arcsec, if +, E is higher than W
  int    DS_LimitUpper;         // upper dome shutter limit status
  int    DS_LimitLower;         // lower dome shutter limit status
  int    DS_LimitSafety;        // safety interlock switch status
  double DS_Elevation;          // upper shutter elevation in degrees
  int    MC_Position;           // mirror cover position in percentages
  double CH_Setpoint;           // chiller setpoint temperature in deg C
  double CH_ProcTemp;           // chiller processed temperature in deg C
  double EN_Sensors[7];         // environment sersors value in deg C or RH %

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

//---------------------------------------------------------------------------
//
// Definitions for programming
//

// a useful alias 

#define NUL             '\0'
#define DEG2RAD         (3.141592654/180.0)
#define SEC2RAD         (DEG2RAD/3600.0)
#define RAD2DEG         (180.0/3.141592654)
#define RAD2SEC         (RAD2DEG*3600.0)
#define SQRT3           1.732050808   // square root or 3.0

// XTerm Color Printing Macros - always pair a color with TXTRESET

#define REDTEXT  printf("%c[0;31m",27)   //!< Red normal for most errors
#define GRNTEXT  printf("%c[0;32m",27)   //!< Green normal, sometimes for diagnostics
#define YELTEXT  printf("%c[0;33m",27)   //!< Yellow normal, unused (unreadable)
#define BLUTEXT  printf("%c[0;34m",27)   //!< Blue normal, move status
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

// Value for filter number (FS_FiltrNum)

#define AUX_FS_FNUM_NO         0    // no filter
#define AUX_FS_FNUM_F1         1    // filter #1
#define AUX_FS_FNUM_F2         2    // filter #2
#define AUX_FS_FNUM_F3         3    // filter #3
#define AUX_FS_FNUM_F4         4    // filter #4
#define AUX_FS_FNUM_MANY       5    // more than 2 filters

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

// Status for dome shutter limits

#define AUX_DS_LIMIT_OPENED   50
#define AUX_DS_LIMIT_CLOSED   51
#define AUX_DS_LIMIT_MIDDLE   52
#define AUX_DS_LIMIT_ACTIVE   53
#define AUX_DS_LIMIT_INACTI   54

// generic flags

#define START         1
#define STOP          0

#define SOUTH         0
#define EAST          1
#define WEST          2

//---------------------------------------------------------------------------
//
// Application Function Prototypes 
//

// common client utilities

   int  LoadConfig(const char *cfgfile);  // Load/parse the agent runtime config file
  void  KeyboardCommand(char *);          // process keyboard commands
  void  SocketCommand(char *);            // process message from an ISIS server/client

// common utilities in commands.c

double  StopWatch(int, const char *);
  char *GetUTCTime(void);
  void  GetUTCDateTime(systime_t *);
  char *strupr(const char *);

// AUX update and command processes in commands.c

   int  AuxTelemetry(auxctrl_t *, char *);
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
#endif

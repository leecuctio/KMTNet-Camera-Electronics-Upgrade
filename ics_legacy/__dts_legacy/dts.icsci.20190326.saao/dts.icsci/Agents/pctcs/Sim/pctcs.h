#ifndef PCTCS_H
#define PCTCS_H

//
//
// Main PCTCSAgent header file
//
// Defaults below are defined for the ANDICAM installation
// 
// Author: 
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2003 February 1
//
// Modification History:
//   2004 Feb 17 - modified for updated ISIS system [rwp/osu]
//   2004 Jun 30 - added hooks for status flags [rwp/osu]
//   2005 May 27 - overhauled for the current system [rwp/osu]
//   2013 Mar 29 - start of new-generation PC-TCS development [rwp/osu]
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

// ISIS Client API header

#include "isisclient.h"

extern isisclient_t client;  // global client runtime config table

// In case the version and compilation data are not defined
// at compilation, put in some placeholders to prevent code barfing

#ifndef APP_VERSION
#define APP_VERSION "2.0 Beta"
#endif

#ifndef APP_COMPDATE
#define APP_COMPDATE "2003-01-01"
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

#define DEFAULT_ISISHOST "localhost"
#define DEFAULT_ISISPORT 6600
#define DEFAULT_ISISID   "IS"

// default PC-TCS serial port assignment on the local computer

#define TCS_TTYPORT "/dev/ttyS0"

//
// Observatory locale information - change to suit, or
// note that these are all defined in the INI file.
// 

#define DEFAULT_OBSERVAT  "CTIO"
#define DEFAULT_TELESCOP  "KMTN1"
#define DEFAULT_OBSLAT  -30.16500
#define DEFAULT_OBSLONG 70.81500
#define DEFAULT_OBSALT 2215

//
// END of Site-Dependent Setup
//
// Touch the stuff below this at your own risk..
//
//----------------------------------------------------------------

// String sizes 

#define POSIX
#define BUF_SIZE          2048
#define LONG_STR_SIZE     4096  // a long string                          
#define MED_STR_SIZE      256   // a medium-sized string                  
#define BIG_STR_SIZE      512   // bigger than medium, smaller than long  
#define SHORT_STR_SIZE    32    // a short string                         
#define ICIMACS_HOST_SIZE 9     // maximum size of ICIMACS host names 8+1 
#define MAX_MSG_SIZE      256   // maximum message buffer size            

// A useful alias for some things

#define NUL             '\0'

// XTerm Color Printing Macros - always pair a color with TXTRESET

#define REDTEXT  printf("%c[0;31m",27)   //!< Red normal for most errors
#define GRNTEXT  printf("%c[0;32m",27)   //!< Green normal, sometimes for diagnostics
#define YELTEXT  printf("%c[0;33m",27)   //!< Yellow normal, unused (unreadable)
#define BLUTEXT  printf("%c[0;34m",27)   //!< Blue normal, unused
#define MAGTEXT  printf("%c[1;35m",27)   //!< Magenta bold for fatal errors
#define CYATEXT  printf("%c[0;36m",27)   //!< Cyan normal for warnings

#define TXTRESET printf("%c[0m",27)      //!< reset default text color

//---------------------------------------------------------------------------
//
// Application global system table structure 
//
// parameters are loaded from the pctcs.ini file
//

typedef struct pctcs_config {

  // Runtime parameters

  int    simMode;              // Agent is in simulation mode [default: 0]

  // PC-TCS telemetry serial port interface info

  int    fd;                   // PC-TCS serial file descriptor     
  char   port[SHORT_STR_SIZE]; // PC-TCS serial port device name    
  int    link;                 // PC-TCS interface state flag       
  double tick;                 // time of last PC-TCS telemetry     
  double idle;                 // seconds since last PC-TCS telemetry   
  int    timeout;              // timeout in seconds for PC-TCS link  
  int    idleTime;             // time in seconds for idle testing
  int    doSip;                // sip the telemetry stream

  // Time/Date information (for use when PC-TCS is idle/disabled)

  char   utcDate[SHORT_STR_SIZE]; // UTC Date CCYY-MM-DD format     
  char   utcTime[SHORT_STR_SIZE]; // UTC Time hh:mm:ss format       
  char   dateTag[SHORT_STR_SIZE]; // UTC date tag CCYYMMDD format   

  // PC-TCS Telemetry Data

  char RA[SHORT_STR_SIZE];      // Right Ascension in hh:mm:ss.s format     
  char Dec[SHORT_STR_SIZE];     // Declination in +dd:mm:ss.s format        
  char HA[SHORT_STR_SIZE];      // Hour Angle in hh:mm:ss.s format          
  char LST[SHORT_STR_SIZE];     // Local Siderial Time in hh:mm:ss.s format 
  char secZD[SHORT_STR_SIZE];   // Secant of Zenith Distance [dimensionless]                     
  char Equinox[SHORT_STR_SIZE]; // Epoch (really equinox) in years          
  char JD[SHORT_STR_SIZE];      // Julian Day Number                        
  char Date[SHORT_STR_SIZE];    // UTC Date in ccyy-mm-dd format            
  char UTC[SHORT_STR_SIZE];     // UTC time in hh:mm:ss                     
  char Temp[SHORT_STR_SIZE];    // Temperature in degrees C                 
  char Focus[SHORT_STR_SIZE];   // Secondary mirror focus in encoder steps  
  char Alt[SHORT_STR_SIZE];     // Altitude in degrees                      
  char Az[SHORT_STR_SIZE];      // Azimuth in degrees                
  char Raw[BUF_SIZE];           // Raw TCS telemetry string
  int  moveStatus;              // Move status (0,1,2,3)
  int  RALimit;                 // 0 if OK, 1 if at RA limit
  int  DecLimit;                // 0 if OK, 1 if at Dec limit
  int  HorizonLimit;            // 0 if OK, 1 if at Horizon limit
  int  DriveDisable;            // 0 if OK, 1 if disabled
  int  Moving;                  // 1 if telescope is in motion, 0 otherwise

  // Various diagnostic data

  char   startTime[24];          // UTC time server started        
  char   userID[SHORT_STR_SIZE]; // user ID that launched TCSAgent 
  char   exeFile[MED_STR_SIZE];  // path/name of executable file   

} pctcs_t;

extern pctcs_t tcs;

// date time data structure

typedef struct systime {
  int year;
  int month;
  int day;
  int hour;
  int min;
  double sec;
} systime_t;

extern systime_t tctime;

// TCS state values 

#define TCS_DOWN 0
#define TCS_UP   1
#define TCS_IDLE 2
#define TCS_SIM  3  

// Which PC-TCS installation are we using?
//  ... there can be only one ...

#undef  __Lab
#define __Yale      
#undef  __CTIO13m
#undef  __NextGen

// PC-TCS implementation-dependent parameters

#define MAX_SIP 20        // maximum number of telemetry "sips" at a time

#if defined(__Lab)
#define MIN_TCSBUF 100

#elif defined(__CTIO13m)
#define MIN_TCSBUF 180    // minimum size a TCS telemetry stream must have to be parsable

#elif defined(__Yale)
#define MIN_TCSBUF 149    // minimum size a TCS telemetry stream must have to be parsable

#endif

//
// Default TCS Timeout Interval [seconds]
//
// The PCTCS Agent will declare that the TCS link is "idle" if there
// has been no telemetry received down the serial port for this
// interval in seconds.  The actual timeout will be overriden by any
// value set in the runtime config file.
//

#define TCS_TIMEOUT 10

//---------------------------------------------------------------------------
//
// Application Function Prototypes 
//

// common client utilities

int  loadConfig(char *);    // Load/parse the agent runtime config file
void keyboardCmd(char *);   // process keyboard commands
void socketCmd(char *);     // process message from an ISIS server/client

// I/O routines for Comsoft PC-TCS interaction

void comsoftChkSum(char *cmd);
void parseComsoft(pctcs_t *, char *);
char *getUTCTime(void);
void getUTCDateTime(systime_t *);

// Utility routines

int initPCTCS(pctcs_t *, char *);

#endif

#ifndef RELAY_H
#define RELAY_H

//
// relay.h - Custom port relay application header
//

/*!
  \file relay.h
  \brief ISIS Port Relay Application Header

  ISIS relay application header

  \date 2014 Oct8
*/

// Various site-dependent but system-independent default values 

// Default relay application values (override/set in loadconfig.c)

#define DEFAULT_MYPORT    10801 //!< default relay socket port   
#define DEFAULT_RCFILE    "/home/dts/Config/isisrelay.ini" //!< default relay runtime config file
#define DEFAULT_LOGFILE   "/home/dts/Logs/isisrelay.log" //!< default relay runtime log file (unimplemented)

// Default ISIS server information (see loadconfig.c)

#define DEFAULT_ISISID   "IS"        //!< default ISIS server node name
#define DEFAULT_ISISHOST "localhost" //!< default ISIS server host
#define DEFAULT_ISISPORT 6600        //!< default ISIS server port number

//
// END of Site-Dependent Setup
// 
//----------------------------------------------------------------

// System header files 

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/file.h>
#include <unistd.h>
#include <errno.h>
#include <sys/time.h>
#include <sys/times.h>
#include <sys/socket.h>
#include <netdb.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <termios.h>
#include <fcntl.h>
#include <signal.h>

// In case the version and compilation data are not defined
// at compilation, put in some placeholders to prevent code barfing

#ifndef APP_VERSION
#define APP_VERSION "0.0.0" //!< placeholder version number, set in Makefile
#endif

#ifndef APP_COMPDATE
#define APP_COMPDATE "2014-10-01" //!< placeholder compilation date, set by build script
#endif

#ifndef APP_COMPTIME
#define APP_COMPTIME "00:00:00" //!< placeholder compilation time, set by build script
#endif

// Useful working parameters

#ifndef MAXCFGLINE
#define MAXCFGLINE 128 //!< Maximum characters/line in runtime config files
#endif

/*!
  \brief Port Relay parameters

  Some of these parameters are designed to overload elements of the
  client struct, which we use only for access to the existing 
  ISIS client socket and serial I/O functions.
*/

typedef struct relay_params {
  char ttyPort[128];  //!< Name of the TTY port
  int  ttyFD;         //!< TTY port file descriptor
  int  ttySpeed;      //!< TTY port speed (e.g., 9600)
  int  ttyDataBits;   //!< TTY port number of data bits (usually 8)
  int  ttyStopBits;   //!< TTY port number of stop bits (1 or 2)
  int  ttyParity;     //!< TTY port parit (0 or 1)
  int  udpPort;       //!< Name of the UDP socket port
  int  udpFD;         //!< UDP socket file descriptor
  int  verboseMode;   //!< Enable (1) or disable (0) verbose output
} relay_t;

extern relay_t relay;

// ISIS common client utilties library header
// We use these for common socket and tty port functions so we don't have to
// re-invent any essential wheels.  An ISIS relay is a silent "pseudo-client"
// application.

#include "isisclient.h"     // should be in -I path in Makefile, no paths here!

extern isisclient_t client; // global relay runtime config table

//----------------------------------------------------------------
//
// Custom relay application function prototypes 
//
 
int  loadConfig(char *);    // Load/parse the runtime config file

// Signal Handlers

void HandleInt(int);  // SIGINT handler

#endif  // RELAY_H

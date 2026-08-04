#ifndef CLIENT_H
#define CLIENT_H

//
// client.h - Custom client application header
//

/*!
  \file client.h
  \brief TVDisplay Client Application Header

  ISIS client application header for the tvdisp application.

  \date 2005 May 31
*/

// Various site-dependent but system-independent default values 

// Default client application values (override/set in loadconfig.c)

#define DEFAULT_MYID      "TV"  //!< default client ISIS node name
#define DEFAULT_MYPORT    10801 //!< default client socket port   
#define DEFAULT_RCFILE    "/home/dts/Config/tvdisp.ini" //!< default client runtime config file
#define DEFAULT_LOGFILE   "/home/dts/Logs/tvdisp.log" //!< default client runtime log file (unimplemented)

// Default ISIS server information (see loadconfig.c if used)

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
#define APP_VERSION "1.0 Beta" //!< placeholder version number, set in Makefile
#endif

#ifndef APP_COMPDATE
#define APP_COMPDATE "2004-01-01" //!< placeholder compilation date, set by build script
#endif

#ifndef APP_COMPTIME
#define APP_COMPTIME "00:00:00" //!< placeholder compilation time, set by build script
#endif

// Useful working parameters

#ifndef MAXCFGLINE
#define MAXCFGLINE 128 //!< Maximum characters/line in runtime config files
#endif

// ISIS common client utilties library header

#include "isisclient.h"    // should be in -I path in Makefile, no paths here!

extern isisclient_t client;  // global client runtime config table

// XTVUtils API header

#include "xtv.h"   

// HEASARC CFITSIO library header 

#include "fitsio.h"

//---------------------------------------------------------------------------

/*!
  \brief FITS image parameters data structure

  Encapsulates the parameters describing a FITS format image
  and its data.

*/

typedef struct img_params {
  float *data;        //!< pointer to a floating array with the data
  int nx;             //!< size of the image in X (NAXIS1)
  int ny;             //!< size of the image in Y (NAXIS2)
  char file[32];      //!< name of the file (from header FILENAME card or command line)
  char fullname[128]; //!< full filename including path
  char object[32];    //!< image header OBJECT card, if present
  int haveImage;      //!< Flag: 1=have an image to display, 0=no images to display

  // Image statistics

  float min;          //!< minimum data value in the image
  float max;          //!< maximum data value in the image
  float mean;         //!< mean of data values
  float median;       //!< median of data values
  float sigma;        //!< standard deviation (sigma) of data values

} img_t;

extern img_t img;  // displayed FITS image (declare in main)

/*!
  \brief XTV Display Parameters data structure

  Encapsulates all of the parameters that describe the current image
  display.

*/

typedef struct disp_params {

  // Display Properties

  char AppName[32]; //!< Application name for the X resource database
  char WinName[32];   //!< Title for the display
  int NX;           //!< display size in X
  int NY;           //!< display size in Y
  int NColors;      //!< number of colors
  int Zoom;         //!< Zoom factor for the magnifying-glass window, 0=no zoom window
  int Flip;         //!< Flag: 1=flip Y-axis, 0=native order

  // Data display mapping

  float z1;         //!< minimum display data value
  float z2;         //!< maximum display data value
  int cmap;         //!< color map, one of #BW, #IBW
  short r[256];     //!< Red color map vector
  short g[256];     //!< Green color map vector
  short b[256];     //!< Blue color map vector

  int FD;           //!< XWindows event handler file descriptor

} disp_t;

extern disp_t tv;  // global for routines

#define BW  0  //!< Black-and-White color map
#define IBW 1  //!< Inverse Black-and-White (photonegative) color map

//----------------------------------------------------------------
//
// Custom client application function prototypes 
//
 
int LoadConfig(char *);       // Load/parse the agent runtime config file (see loadconfig.c)
void KeyboardCommand(char *); // process keyboard (cli) commands (see commands.c)
void SocketCommand(char *);   // process messages from the client socket (see commands.c)

// Client utility routines

void InitImgPars(img_t *);
void InitDispPars(disp_t *);
void DispInfo(disp_t *);
void ImageInfo(img_t *);

int ReadFITSFile(img_t *, char *, char *);
int ImageMean(img_t *, int);
int FakeImage(img_t *, int, int, float);

// Signal Handlers

void HandleInt(int);  // SIGINT handler
void abortall(void);  // abort all moves

#endif  // CLIENT_H

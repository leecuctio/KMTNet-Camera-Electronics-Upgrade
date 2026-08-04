#include <stdio.h>   /* Used for standard input/output commands (printf, etc.)                   */
#include <string.h>  /* Used for string manipulation commands (strcpy, etc.)                     */
#include <curses.h>  /* Used for screen i/o                                                      */
#include <sys/types.h>
#include <sys/stat.h>/* Used for file statistics                                                 */
#include <sys/file.h>/* Used for file routines (open, etc.)                                      */
#include "/usr/include/unistd.h"/* Used for file routines (chmod, etc.)                          */
#include <fcntl.h>   /* Used for file constants                                                  */
#include <errno.h>
#include <sys/time.h>

/* Conditional directives */
#ifdef SUNOS
#define AUTOLOG_CMD "/home/rowland/dts/bin/autologger %s"
#define USE_ERRLIST
#define cb_FILEMODE O_RDONLY
#define INI_FILE_NAME "/home/rowland/dts/Caliban/Caliban.ini"
#endif

#ifdef SOLARIS
/* prototype autolog command script */
#define AUTOLOG_CMD "/opt/local/pkg/dts/bin/autologger %s" 
/* defining the inifile with a full path lets caliban be run anywhere */
#define INI_FILE_NAME "/opt/local/pkg/dts/Caliban/Caliban.ini"
#undef USE_ERRLIST
#define cb_FILEMODE O_RDONLY
#endif

#ifdef LINUX
/* prototype autolog command script */
#define AUTOLOG_CMD "/home/pleiades/dts/bin/autologger %s"
/* defining the inifile with a full path lets caliban be run anywhere */
#define INI_FILE_NAME   "/home/pleiades/dts/Caliban/Caliban.ini"
#undef USE_ERRLIST
#define cb_FILEMODE O_RDWR
#endif

/* Save-The-Bits generic archive command */
#define ARCHIVE_CMD "lpr -Pbits -s %s"    

#define POSIX
#define FITS_BLOCK_SIZE 2880
#define FITS_DATA_BLOCK_SIZE 8192
#define BLOCK_SIZE      512
#define BUF_SIZE        2048
#define LONG_STR_SIZE   4096
#define MED_STR_SIZE    256
#define SHORT_STR_SIZE  32
#define MAXDISKS        24
#define cb_TRUE         1
#define cb_FALSE        0
#define cb_ERROR        -1
#define cb_OK           32767
#define cb_FATAL        -666
#define SYSERR          -32768
#define NUL             '\0'

/* Interface port constants */
#define KEYBOARD  0
#define SERIAL    1
#define SOCKET    2
#define TELNET    3
#define HTTP      4

struct st {                         /* Global system table structure                                           */
  int  done;                        /* Flag indicating whether to continue operation or quit                   */
  int  verbose;                     /* Verbose output mode enabled                                             */
  int  maxcards;                    /* Maximum number of FITS cards in one file                                */
  int  headlng;                     /* Maximum length of FITS header unit                                      */
  int  datalng;                     /* Maximum length of FITS data unit                                        */
  int  blocksize;                   /* Blocking factor for disk operations                                     */
  int  max_xfer_files;              /* Max number of files transferrable at once                               */
  int  fd_serial;                   /*                                                                         */
  int  fd_http;                     /*                                                                         */
  int  fd_telnet;                   /* File descriptors for each interface                                     */
  int  fd_server_socket;            /*                                                                         */
  int  fd_client_socket;            /*                                                                         */
  int  fd_keyboard;                 /*                                                                         */
  int  logfd;                       /* Log file descriptor                                                     */
  int  cols;                        /* Number of curses columns in current window                              */
  int  noswap;                      /* Flag indicating whether disk transfers are currently allowed            */
  int  debug;                       /* Flag indicating whether Caliban is running in debug mode (verbose)      */

  int  doarchive;                   /* Flag indicating whether to archive each file transferred                */
  int  dodisplay;                   /* Flag indicating whether to display each file transferred                */
  int  doautolog;                   /* Flag indicating whether to autolog each file transferred                */
  int  addfits;                     /* Flag indicating whether to append the .fits extension to filenames      */

  int  olddoarchive;                /* Variables to save initial state as read in from .ini file in case       */
  int  olddodisplay;                /* user issues the reset command to restore these default values           */
  int  olddoautolog;                /*                                                                         */
  int  oldaddfits;                  /*                                                                         */

  long headwritten;                 /* Stores number of chars written to FITS head seg for debugging purposes  */
  long datawritten;                 /* Stores number of chars written to FITS data seg for debugging purposes  */

  long sgloc;                       /* Virtual position counter for SCSI generic seek and read routines        */

  char serialdev[MED_STR_SIZE];     /* Physical serial device name                                             */
  char serialhost[SHORT_STR_SIZE];  /* Name of downstream host on serial interface                             */
  char localhost[SHORT_STR_SIZE];   /* Local hostname                                                          */
  char logfilename[MED_STR_SIZE];   /* Log file name                                                           */
  char oldcmdline[BUF_SIZE];        /* Command line history buffer                                             */
  char oldinbuf[BUF_SIZE];          /* Serial input history buffer                                             */
  char lastfile[MED_STR_SIZE];      /* Last file written to disk                                               */
  WINDOW *input;                    /* Curses input window pointer                                             */
  WINDOW *output;                   /* Curses output window pointer                                            */
};

extern struct st *systab;           /* Global system table pointer                                             */

struct dt {                         /* Global disk table structure                                             */
  int  synched;                     /* Flag indicating whether disk synchronization has occurred               */
  char disk[MAXDISKS][MED_STR_SIZE];/* Array containing disk name in the form DISK#.BUS#.DateCreated           */
  char alias[MAXDISKS][MED_STR_SIZE];/* Array containing disk alias for use in comm with serial host e.g. DISK#*/
  char device[MAXDISKS][MED_STR_SIZE];/* Array containing physical device name e.g. /dev/sd6a                    */
  int  valid[MAXDISKS];             /* Flag indicating whether device is valid                                 */
  int  use[MAXDISKS];               /* Flag indicating whether device is being used for transfer               */
  int  numdisks;                    /* Number of disk devices capable of being synched                         */
  int  numvalid;                    /* Number of valid disks in the disktable                                  */
  int  ackdisk;                     /* Flag indicating whether ACKDISK acknowledgment has been received        */
};

extern struct dt *disktab;          /* Global disk table pointer                                               */

struct mt                           /* Mount table structure definition                                        */
{
  char mount[SHORT_STR_SIZE][MED_STR_SIZE]; /* Array containing mount point names                              */
  int nummounts;                    /* Number of currently defined mount points                                */
  int current;                      /* Index to currently active mount point                                   */
};

extern struct mt *mounttab;         /* Global mount table pointer                                              */

/* Function prototypes                                                                                         */

int  InitDisk(int, char *, char *);
int  InitDiskTable();
int  InitSerial();
int  IsValidMount(char *);
int  BCmp(char *, char *, int);
int  GetFITS(int, char *, char *, char *, int);
int  ChkDiskSpace(char *, long);
long SGread(int, char *, long);
long CBread(int, char *, long);
char *CatStr(char *, char *, char *);
void GetArg(char *, int, char *);
void ltos(char *, long);
void ReqMount();
void UpperCase(char *);
void BZero(char *, int);
void LeftStr(char *, char *, int);
void RightStr(char *, char *, int);
void MidStr(char *, char *, int, int);
void XmitMsg();
void AckDisk(int, char *);
void LogMsg(char *);
void ConsoleMsg(char *, char *);
void Ping(int, char *);
void Pong(char *);
void Prompt();
void Status(char *, char *);
void TransferDisk(int, char *);
void UseDisk(int, char *, char *);
void UseMount(int, char *, char *);
void UserCancel();
void ParseIniFile();
void PrintSystab();
void CBStatus(int, char *);
void SGseek(long);
void CBseek(int, long, int);
void InitCB();
void DoCommand(char *);

/* Global error message vector and index - kind of messy */

#ifdef USE_ERRLIST
int sys_nerr;
char *sys_errlist[];
#define ERRORSTR sys_errlist[errno]
#else
#define ERRORSTR strerror(errno)
#endif
int errno;

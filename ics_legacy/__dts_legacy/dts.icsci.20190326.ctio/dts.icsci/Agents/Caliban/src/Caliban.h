//
//
// Caliban.h - Caliban header file
//
// Default set for the OSIRIS setup on host "osiris"
// R. Pogge, OSU Astronomy Dept.
// pogge@astronomy.ohio-state.edu
// 2003 January 20
//

// System header files 

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
#include <sys/stat.h>
#include <netdb.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <termios.h>
#include <fcntl.h>
#include <curses.h>

// GNU readline & history header files 

#include <readline/readline.h>
#include <readline/history.h>

// Version and Compilation Info (usually set by the build script) 

#ifndef VERSION
#define VERSION "Caliban v3.6"
#endif
#ifndef COMPDATE
#define COMPDATE "unknown"
#endif
#ifndef COMPTIME
#define COMPTIME "unknown"
#endif

// Conditional directives
//
// *** Make sure all paths are physical rather than logical or
// *** automount paths to ensure integrity
//

#ifdef LINUX
#define AUTOLOG_CMD "/lhome/dts/bin/autologger %s"
#define DEFAULT_INI_FILE "/lhome/dts/Config/caliban.ini"
#undef USE_ERRLIST
#define cb_FILEMODE O_RDONLY
#undef UseSG
//#define cb_FILEMODE O_RDWR
#endif

// Save-The-Bits generic archive command 

#define ARCHIVE_CMD "lpr -Pbits -s %s"    

#define POSIX

// data block and string sizes 

#define FITS_DATA_BLOCK_SIZE 16384

#define FITS_BLOCK_SIZE 2880
#define BLOCK_SIZE      512
#define BUF_SIZE        2048
#define LONG_STR_SIZE   4096
#define MED_STR_SIZE    1024
#define SHORT_STR_SIZE  32
#define MAXDISKS        24
#define MAXREQSWAP      3

// useful values 

#define cb_TRUE         1
#define cb_FALSE        0
#define cb_ERROR        -1
#define cb_OK           32767
#define cb_FATAL        -666
#define SYSERR          -32768
#define NUL             '\0'

// XTerm Color Printing Macros - always pair colors with TXTRESET

#define REDTEXT  printf("%c[0;31m",27)   //!< Red normal for most errors
#define GRNTEXT  printf("%c[0;32m",27)   //!< Green normal, sometimes for diagnostics
#define YELTEXT  printf("%c[0;33m",27)   //!< Yellow normal, unused (unreadable)
#define BLUTEXT  printf("%c[0;34m",27)   //!< Blue normal, unused
#define MAGTEXT  printf("%c[1;35m",27)   //!< Magenta bold for fatal errors
#define CYATEXT  printf("%c[0;36m",27)   //!< Cyan normal for warnings

#define TXTRESET printf("%c[0m",27)      //!< Reset to default text color

// Interface port constants 

#define KEYBOARD     0
#define SERIAL       1
#define SOCKET       2
#define TELNET       3
#define HTTP         4
#define NOINTERFACE -1

//***************************************************************
//
// Global System Table Structure
//

struct st {
  int  done;           // Flag indicating whether to continue operation or quit           
  int  verbose;        // Verbose output mode enabled                                             
  int  maxcards;       // Maximum number of FITS cards in one file                                
  int  headlng;        // Maximum length of FITS header unit                                      
  int  datalng;        // Maximum length of FITS data unit                                        
  int  blocksize;      // Blocking factor for disk operations                                     
  int  max_xfer_files; // Max number of files transferrable at once                      

  int  fd_serial;      //                                                                         
  int  fd_http;        //                                                                         
  int  fd_telnet;      // File descriptors for each interface                                     
  int  fd_socket;      //                                                                         
  int  fd_keyboard;    //                                                                         
  int  fd_disk;        // File descriptor of the downstream disk host                             
  int  logfd;          // Log file descriptor                                                     

  int  noswap;         // Flag indicating whether disk transfers are currently allowed            
  int  debug;          // Flag indicating whether Caliban is running in debug mode (verbose)      

  int  doarchive;      // Flag indicating whether to archive each file transferred                
  int  dodisplay;      // Flag indicating whether to display each file transferred                
  int  doautolog;      // Flag indicating whether to autolog each file transferred                
  int  addfits;        // Flag indicating whether to append the .fits extension to filenames      

  int  olddoarchive;   // Variables to save initial state as read in from .ini file in case       
  int  olddodisplay;   // user issues the reset command to restore these default values           
  int  olddoautolog;   //                                                                         
  int  oldaddfits;     //                                                                         

  int  serverport;     // port number of the network server                                       
  int  clientport;     // port number of Caliban, if using sockets                                
  int  diskinterface;  // interface used by the disk data-transfer agent: SERIAL or SOCKET        
  int  usesocket;
  int  useserial;

  int  doAckSwap;      // Toggles whether or not we require ACK SWAP and REQ SWAP retries.
  int  reqswap;        // Disk swap request status 0=no active request, 1=acknowledge pending
  int  nreqswap;       // Number of repeated swap requests (max = MAXREQSWAP)
  long timeout;        // pending REQ timeout interval in integer seconds

  long headwritten;    // Stores number of chars written to FITS head seg for debugging purposes  
  long datawritten;    // Stores number of chars written to FITS data seg for debugging purposes  
  long serveraddr;     // 32-bit IP address of network server                                     

  long sgloc;          // Virtual position counter for SCSI generic seek and read routines        

  char serialdev[MED_STR_SIZE];     // Physical serial device name 
  char serialhost[SHORT_STR_SIZE];  // Name of downstream host on serial interface
  char sockethost[SHORT_STR_SIZE];  // Name of downstream socket host           
  char serverIPaddr[SHORT_STR_SIZE];// server IP Address (text format)          
  char diskhost[SHORT_STR_SIZE];    // Name of the downstream data-transfer host
  char localhost[SHORT_STR_SIZE];   // Local hostname                           

  char archivecmd[MED_STR_SIZE];    // data archiving command if enabled
  char autologcmd[MED_STR_SIZE];    // autolog command if enabled       
  char displaycmd[MED_STR_SIZE];    // display command if enabled       
  char inifilename[MED_STR_SIZE];   // Initialization File name         
  char logfilename[MED_STR_SIZE];   // Log file name                    
  char oldcmdline[BUF_SIZE];        // Command line history buffer      
  char oldinbuf[BUF_SIZE];          // Serial input history buffer      
  char lastfile[MED_STR_SIZE];      // Last file written to disk        
  char exefile[MED_STR_SIZE];       // Executable file (how it was launched at the command line) 
  char userid[MED_STR_SIZE];        // username of who launched caliban 
  char starttime[MED_STR_SIZE];     // date/time caliban was launched 
  char date[SHORT_STR_SIZE];        // date in ISO8601 CCYY-MM-DD format 
  char time[SHORT_STR_SIZE];        // UTC time in hh:mm:ss format 
};

extern struct st *systab;           // Global system table pointer

//***************************************************************
//
// Global Disk Table Structure
//

struct dt {
  int  synched;                     // Flag indicating whether disk synchronization has occurred               
  char disk[MAXDISKS][MED_STR_SIZE];// Array containing disk name in the form DISK#.BUS#.DateCreated           
  char alias[MAXDISKS][MED_STR_SIZE];// Array containing disk alias for use in comm with serial host e.g. DISK#
  char device[MAXDISKS][MED_STR_SIZE];// Array containing physical device name e.g. /dev/sd6a                    
  int  valid[MAXDISKS];             // Flag indicating whether device is valid                                 
  int  use[MAXDISKS];               // Flag indicating whether device is being used for transfer               
  int  numdisks;                    // Number of disk devices capable of being synched                         
  int  numvalid;                    // Number of valid disks in the disktable                                  
  int  ackdisk;                     // Flag indicating whether ACKDISK acknowledgment has been received        
};

extern struct dt *disktab;          // Global disk table pointer                                               

//***************************************************************
//
// Global Mount Table Structure
//

struct mt {
  char mount[SHORT_STR_SIZE][MED_STR_SIZE]; // Array containing mount point names 
  int nummounts;                    // Number of currently defined mount points   
  int current;                      // Index to currently active mount point      
};

extern struct mt *mounttab;         // Global mount table pointer                 

// Function Prototypes 

int  InitDisk(int, char *, char *);
int  InitDiskTable(void);
int  InitSerial(void);
int  InitSocket(void);
int  IsValidMount(char *);
int  BCmp(char *, char *, int);
int  GetFITS(int, char *, char *, char *, int);
int  ChkDiskSpace(char *, long);
long SGread(int, char *, long);
long CBread(int, char *, long);
char *CatStr(char *, char *, char *);
void GetArg(char *, int, char *);
void ltos(char *, long);
void ReqMount(int , char *);
void UpperCase(char *);
void BZero(char *, int);
void LeftStr(char *, char *, int);
void RightStr(char *, char *, int);
void MidStr(char *, char *, int, int);
void XmitMsg(int port, ...);
void AckDisk(int, char *);
void LogMsg(char *);
void ConsoleMsg(char *, char *);
void Ping(int, char *);
void Pong(int, char *);
void Status(char *, char *);
void TransferDisk(int, char *);
void UseDisk(int, char *, char *);
void UseMount(int, char *, char *);
void UserCancel(void);
void ParseIniFile(void);
void PrintSystab(void);
void CBStatus(int, char *);
void SGseek(long);
void CBseek(int, long, int);
void InitCB(void);
void DoCommand(int, char *);
void GetUTCTime(void);

// Global error message vector and index - kind of messy 

#ifdef USE_ERRLIST
int sys_nerr;
char *sys_errlist[];
#define ERRORSTR sys_errlist[errno]
#else
#define ERRORSTR strerror(errno)
#endif
int errno;

#include "Caliban.h"
#include <signal.h>

void 
InitCB(void) 
{
  int lcv; // Loop control variable 

  signal(SIGINT, (sighandler_t)UserCancel);  // Trap user interrupt signal                  

  //*************************************************
  // Initialize system table entries -- clean livin' 
  //*************************************************

  systab->done = cb_FALSE;
  systab->fd_keyboard = 0;  // Set standard in 
  systab->debug = cb_FALSE; // By default we do not operate in debug mode 

  systab->fd_serial = 0;
  systab->fd_socket = 0;
  systab->fd_disk   = 0;

  systab->doarchive = systab->dodisplay = systab->doautolog = systab->addfits = cb_FALSE;
  systab->olddoarchive = systab->olddodisplay = systab->olddoautolog = systab->oldaddfits = cb_FALSE;

  strcpy(systab->autologcmd,AUTOLOG_CMD);
  strcpy(systab->archivecmd,ARCHIVE_CMD);
  memset(systab->displaycmd,0,sizeof(systab->displaycmd));

  memset(systab->serialdev,0,sizeof(systab->serialdev));
  memset(systab->serialhost,0,sizeof(systab->serialhost));
  memset(systab->localhost,0,sizeof(systab->localhost));
  memset(systab->sockethost,0,sizeof(systab->sockethost));
  memset(systab->serverIPaddr,0,sizeof(systab->serverIPaddr));
  memset(systab->diskhost,0,sizeof(systab->diskhost));

  memset(systab->logfilename,0,sizeof(systab->logfilename));
  memset(systab->oldcmdline,0,sizeof(systab->oldcmdline));
  memset(systab->oldinbuf,0,sizeof(systab->oldinbuf));
  memset(systab->lastfile,0,sizeof(systab->lastfile));

  sprintf(systab->lastfile, "none");

  // set the communications interface flags 

  systab->diskinterface = NOINTERFACE;
  systab->useserial = cb_FALSE;
  systab->usesocket = cb_FALSE;
  systab->clientport = 0;
  systab->serverport = 0;
  systab->serveraddr = 0;

  // REQ SWAP/ACK SWAP variables

  systab->doAckSwap = 0;  // by default, do not require AckSwap
  systab->timeout = 5;    // Polling timeout default is 5 sec
  systab->reqswap = 0;    // Reset REQ SWAP acknowledge pending flag 
  systab->nreqswap = 0;   // Reset REQ SWAP retry counter

  // initialize the disk table 

  for(lcv=0; lcv<MAXDISKS; lcv++) {
    memset(disktab->disk[lcv],0,sizeof(disktab->disk[lcv]));
    memset(disktab->alias[lcv],0,sizeof(disktab->alias[lcv]));
    memset(disktab->device[lcv],0,sizeof(disktab->device[lcv]));
  }

  // initialize the disk table 

  for(lcv=0; lcv<SHORT_STR_SIZE; lcv++)
    memset(mounttab->mount[lcv],0,sizeof(mounttab->mount[lcv]));

  systab->headwritten = 0;
  systab->datawritten = 0;

  //*******************************
  // Parse the initialization file 
  //*******************************


  ParseIniFile(); // Load global tables with values from initialization file  

  //**********************************
  // Logging mechanism initialization 
  //**********************************

  // Attempt to open the log file, or create one if it does not already exist 

  if((systab->logfd=open(systab->logfilename, O_WRONLY))==cb_ERROR) {
      if((systab->logfd=creat(systab->logfilename, 0666))==cb_ERROR)
	ConsoleMsg("ERROR: Unable to create log file--%s", ERRORSTR);
  }

  lseek(systab->logfd, 0L, SEEK_END); // Position the log file pointer to EOF 

  LogMsg("#### Caliban started normally ####");

  //****************************
  // Serial port initialization 
  //****************************

  // Attempt to get a handle to the serial port, if requested 

  if (systab->useserial == cb_TRUE) {
    if((systab->fd_serial=InitSerial())==SYSERR) {
      ConsoleMsg("ERROR: Connect to serial port failed - %s", ERRORSTR);
    } else {
      ConsoleMsg("Connected to serial port %s", systab->serialdev);
    }
  }

  //****************************
  // Socket Port Initialization  
  //****************************

  if (systab->usesocket == cb_TRUE) {
    if((systab->fd_socket=InitSocket())==SYSERR) {
      ConsoleMsg("ERROR: Network socket port initialization failed - %s", 
		 ERRORSTR);
    } 
  }

  // set the disk host file descriptor 
   

  if (systab->diskinterface == SERIAL) {
    if (systab->fd_serial > 0) {
      systab->fd_disk = systab->fd_serial;
    }
    else {
      printf("ERROR: DISK_HOST serial port not enabled.\n");
      printf("Caliban must abort...\n");
      exit(1);
    }
  }
  else if (systab->diskinterface == SOCKET) {
    if (systab->fd_socket > 0) {
      systab->fd_disk = systab->fd_socket;
    }
    else {
      printf("ERROR: DISK_HOST socket interface not enabled.\n");
      printf("Caliban must abort...\n");
      exit(1);
    }
  }
  else {
    printf("ERROR: no DISK_HOST interface was specified in the\n");
    printf("       initialization file.  Caliban must abort...\n");
    exit(1);
  }

  //****************************
  // Mount table initialization 
  //****************************

  // In the event no valid mount points are discovered in the ini
  // file, set the current mount point to reflect not available
   

  if(mounttab->nummounts==0) {
    sprintf(mounttab->mount[0], "n/a");
    ConsoleMsg("%s", "ERROR: No valid mount points specified");
  }

  mounttab->current = 0;     // By default, the first entry in the mount table becomes current 

  //***************************
  // Disk table initialization 
  //***************************

  if(InitDiskTable()==0)
    ConsoleMsg("%s", "ERROR: No valid spool device(s) detected");
  
  if (disktab->numvalid < disktab->numdisks)
    ConsoleMsg("%s", "WARNING: Caliban.ini contains invalid spool device(s)");
}

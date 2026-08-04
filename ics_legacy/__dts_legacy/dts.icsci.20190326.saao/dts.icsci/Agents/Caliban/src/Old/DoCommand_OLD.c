#include "Caliban.h"

// added port, indicating who sent the command, so who gets the reply 

void 
DoCommand(int port, char *cmdStr)
{
  int lcv=0;
  int numLines=0;              // Used for displaying n log lines on the screen 
  int diskNum=0;               // Disk table index                              
  int numImages=0;             // Number of images to read
  long timeout=0;              // default test timeout interval

  char logStr[MED_STR_SIZE];   // Command string sent to the runtime log
  char xferCmd[MED_STR_SIZE];  // Data Transfer command string (see RECOVER)
  char diskID[MED_STR_SIZE];   // ID of a transfer disk (e.g., DISK1 - see RECOVER)
  char cmdWord[BUF_SIZE];      // Command "word" portion of the message
  char argStr[BUF_SIZE];       // String with the command-line arguments
  char argBuf[MED_STR_SIZE];   // Current argument buffer
  char outStr[BUF_SIZE];       // General purpose output buffer                 
  char fromID[SHORT_STR_SIZE]; // Host name command was received from           
  char destID[SHORT_STR_SIZE]; // Host name command is destined for             
  FILE *logPipe;               // Handle to pipe for log display command        

  // stuff for history handling 

  register HIST_ENTRY **the_list;
  register int ihist;

  // Yow! 

  UpperCase(cmdStr); // Makes comparisons much easier 

  // Parse the message string into components
  
  sscanf(cmdStr,"%[^>]>%s %s %[^\n]",fromID,destID,cmdWord,argStr);

  if (strcasecmp(fromID,systab->localhost)==0)
    port=0;

  // We have a verbose switch which determines whether serial input is echoed       

  if ((systab->verbose==cb_TRUE) && 
     (strcmp(fromID, systab->localhost)!=0))   {
    ConsoleMsg("IN: %s", systab->oldinbuf);
  }

  // QUIT or Q will result in setting the done flag which exits this   
  // whole loop (first confirm that the user didn't fat-finger a key   
  
  if (strcmp(cmdWord, "QUIT")==0 || strcmp(cmdWord, "Q")==0) {
    systab->done = 1;

  }

  // History command 

  else if (strcasecmp(cmdWord,"history")==0) {
    if (port == 0) {
      printf("\n");
      the_list = history_list();
      if (the_list)
	for (ihist=0; the_list[ihist]; ihist++)
	  printf("%5d   %s\n",ihist+history_base,the_list[ihist]->line);
      rl_refresh_line(0,0);
    } 
    else {
      XmitMsg(port, fromID, "ERROR: history command only available on the console");
    }
  }

  // HELP or ? displays a list of the available commands which can be
  // entered at the keyboard--note that this does not represent the
  // full list of supported commands
  
  else if (strcmp(cmdWord, "?")==0 || strcmp(cmdWord, "HELP")==0) {
    if (port==0) {
      printf("\nCaliban Interactive Commands:\n");
      printf("  HELP or ?     - This list\n");
      printf("  QUIT or Q     - End the Caliban session and Exit\n");
      printf("  INFO          - Detailed info on this Caliban session\n");
      printf("  STATUS        - Return the Caliban status\n");
      printf("  LOG n         - Print out the last n lines of the log file\n");
      printf("  +/-ARCHIVE    - Enable/Disable/Query archiving\n");
      printf("  +/-AUTOLOG    - Enable/Disable/Query autologging\n");
      printf("  +/-DISPLAY    - Enable/Disable/Query autodisplay\n");
      printf("  +/-ADDFITS    - Enable/Disable/Query .fits extension append\n");
      printf("  +/-SWAP       - Enable/Disable/Query transfer disk swapping\n");
      printf("  RESTORE       - Restore system flags to default values\n");
      printf("  RESYNCH       - Attempt to resynchronize disks with the CCD host\n");
      printf("  HISTORY       - Show command history\n");
      printf("  Ctrl+L        - Clear screen\n");
      printf("  >{host} {msg} - Sends message {msg} to hostname {host}\n");
      printf("  +/-VERBOSE    - Enable/Disable verbose echo of all messages\n");
      printf("  +/-DEBUG      - Enable/Disable super-verbose engineering output\n");
      printf("  +/-ACKSWAP    - Enable/Disable REQ SWAP acknowledge check/retry\n");
      printf(" RECOVER n disk - Attempt to recover n images from disk (e.g. DISK1)\n");
      printf("                    after a system hang during transfers.\n");
      printf("                    Example: RECOVER 50 DISK1 - get up to 50 images from DISK1.\n");
      printf("  DBGREAD n     - Reads an image from disk n (n>=0) without\n");
      printf("                    having synched disks (ENGINEERING)\n");
      printf("  XMIT cmdStr   - send a command to the detector host (ENGINEERING)\n");
    }
    else {
      XmitMsg(port, fromID, "ERROR: Caliban HELP command only available on the console");
    }
      
  }
  else if (strcmp(cmdWord, "+ARCHIVE")==0) {
    systab->doarchive = cb_TRUE;
    XmitMsg(port, fromID, "STATUS: ARCHIVE=T");
  }

  else if (strcmp(cmdWord, "-ARCHIVE")==0) {
    systab->doarchive = cb_FALSE;
    XmitMsg(port, fromID, "STATUS: ARCHIVE=F");
  }

  else if (strcmp(cmdWord, "ARCHIVE")==0) {
    if (systab->doarchive == cb_TRUE)
      XmitMsg(port, fromID, "STATUS: ARCHIVE=T");
    else
      XmitMsg(port, fromID, "STATUS: ARCHIVE=F");
  }

  else if (strcmp(cmdWord, "+AUTOLOG")==0) {
    systab->doautolog = cb_TRUE;
    XmitMsg(port, fromID, "STATUS: AUTOLOG=T");
  }

  else if (strcmp(cmdWord, "-AUTOLOG")==0) {
    systab->doautolog = cb_FALSE;
    XmitMsg(port, fromID, "STATUS: AUTOLOG=F");
  }

  else if (strcmp(cmdWord, "AUTOLOG")==0) {
    if (systab->doautolog == cb_TRUE)
      XmitMsg(port, fromID, "STATUS: AUTOLOG=T");
    else
      XmitMsg(port, fromID, "STATUS: AUTOLOG=F");
  }

  else if (strcmp(cmdWord, "+DISPLAY")==0) {
    systab->dodisplay = cb_TRUE;
    XmitMsg(port, fromID, "STATUS: DISPLAY=T");
  }

  else if (strcmp(cmdWord, "-DISPLAY")==0) {
    systab->dodisplay = cb_FALSE;
    XmitMsg(port, fromID, "STATUS: DISPLAY=F");
  }

  else if (strcmp(cmdWord, "DISPLAY")==0) {
    if (systab->dodisplay == cb_TRUE)
      XmitMsg(port, fromID, "STATUS: DISPLAY=T");
    else
      XmitMsg(port, fromID, "STATUS: DISPLAY=F");
  }

  else if (strcmp(cmdWord, "+ADDFITS")==0) {
    systab->addfits = cb_TRUE;
    XmitMsg(port, fromID, "STATUS: ADDFITS=T");
  }

  else if (strcmp(cmdWord, "-ADDFITS")==0) {
    systab->addfits = cb_FALSE;
    XmitMsg(port, fromID, "STATUS: ADDFITS=F");
  }

  else if (strcmp(cmdWord, "ADDFITS")==0) {
    if (systab->addfits == cb_TRUE)
      XmitMsg(port, fromID, "STATUS: ADDFITS=T");
    else
      XmitMsg(port, fromID, "STATUS: ADDFITS=F");
  }

  else if (strcmp(cmdWord, "+SWAP")==0) {
    systab->noswap=cb_FALSE;
    XmitMsg(port, fromID, "STATUS: SWAP=T");

    // Tell the downstream disk host that it can use the disk again

    XmitMsg(systab->fd_disk, systab->diskhost, "%s", "REQ SWAP"); 
    systab->reqswap = 1;
    systab->nreqswap++;
  }

  else if (strcmp(cmdWord, "-SWAP")==0) {
    systab->noswap=cb_TRUE;
    XmitMsg(port, fromID, "STATUS: SWAP=F");
  }

  else if (strcmp(cmdWord, "SWAP")==0) {
    if (systab->noswap == cb_TRUE)
      XmitMsg(port, fromID, "STATUS: SWAP=T");
    else
      XmitMsg(port, fromID, "STATUS: SWAP=F");
  }

  else if (strcmp(cmdWord, "RESTORE")==0) {
    systab->doarchive = systab->olddoarchive;
    systab->dodisplay = systab->olddodisplay;
    systab->doautolog = systab->olddoautolog;
    systab->addfits = systab->oldaddfits;
    XmitMsg(port, fromID, "STATUS: Caliban system variables restored to default values");
  }

  // resynch with the diskhost (ping it)

  else if (strcmp(cmdWord,"RESYNCH")==0) {
    // XmitMsg(systab->fd_disk, systab->diskhost, "%s", "PING"); 
    XmitMsg(systab->fd_disk, systab->diskhost, "%s", "REQ INITDISK"); 
    sprintf(outStr,"DONE: Caliban/%s transfer disk resynch initiated",systab->diskhost);
    XmitMsg(port, fromID, outStr);
  }

  // Attempt to recover data from a transfer disk en masse (bad fault recovery)

  else if (strcmp(cmdWord,"RECOVER")==0) {
    GetArg(argStr,1,argBuf);
    numImages = atoi(argBuf);
    if (numImages < 1) {
      XmitMsg(port,fromID,"Must specify the number of images to recover");
    }
    else {
      GetArg(argStr,2,argBuf);
      strcpy(diskID,argBuf);
      // Try to recover N images from the designated disk
      sprintf(outStr,"STATUS: Attempting to recover up to %d images from transfer disk %s",
	      numImages,diskID);
      XmitMsg(port, fromID, outStr);
      sprintf(xferCmd,"TRANSFER DISK %s %d %s",diskID,numImages,fromID);
      TransferDisk(systab->fd_disk, xferCmd);
    }
  }

  // We have the ability to display the last n lines of the log file on screen 
  // n defaults to 10                                                          
  
  else if (strcmp(cmdWord, "LOG")==0) {
    GetArg(argStr,1,argBuf);
    numLines=atoi(cmdWord);
    if (numLines<1)
      numLines = 10;
      
    // We open a pipe which submits a command to the shell 
    
    printf("\n");
    sprintf(logStr, "tail -%d %s", numLines, systab->logfilename);
    logPipe = popen(logStr, "r");
      
    // Then we read the resulting output from the pipe 
      
    while(fgets(outStr, sizeof(outStr), logPipe) != NULL)
      XmitMsg(port, fromID, "STATUS: LOG: %s", outStr);
      
    if (logPipe!=0)
      pclose(logPipe);
  }
  
  // This causes a status table to be displayed on screen 

  else if (strcmp(cmdWord, "INFO")==0) {
    if (port == 0) { // screen dump 
      printf("\nCurrent Caliban Status:\n");
      printf("  VERSION: %s [%s %s]\n", VERSION,COMPDATE,COMPTIME);
      printf("  HostName: %s\n", systab->localhost);
      printf("  Executable: %s\n",systab->exefile);
      printf("  Config File: %s\n",systab->inifilename);
      printf("  Started by user '%s' at %s\n",systab->userid,systab->starttime);
      if (systab->useserial) {
	printf("  SerialPort: %s\n", systab->serialdev);
      }
      if (systab->usesocket) {
	printf("Instrument Server:\n");
	printf("  ServerHost: %s\n",systab->sockethost);
	sprintf(cmdWord,"%d",systab->serverport);
	printf("  ServerAddr: %s:%s\n",systab->serverIPaddr,cmdWord);
	printf("Caliban Client:\n");
	sprintf(cmdWord,"%d",systab->clientport);
	printf("  ClientPort: %s\n",cmdWord);
      }
      printf("Data-Transfer Disk Server:\n");
      printf("  DiskHost: %s\n", systab->diskhost);
      if (systab->diskinterface == SERIAL) 
	printf("  Interface: Serial\n");
      else if (systab->diskinterface==SOCKET)
	printf("  Interface: Socket\n");
      else
	printf("  Interface: None\n");

      printf("Runtime Config:\n");
      printf("  LogFile: %s\n", systab->logfilename);
      sprintf(cmdWord, "%d", BLOCK_SIZE);
      printf("  BlockSize: %s\n", cmdWord);
      printf("  LastFile: %s\n", systab->lastfile);
      sprintf(cmdWord, "%d", systab->headwritten);
      printf("  HeadBytes: %s\n", cmdWord);
      sprintf(cmdWord, "%d", systab->datawritten);
      printf("  DataBytes: %s\n", cmdWord);
      if (systab->doAckSwap) {
	printf("  REQ SWAP acknowledge check/retry enabled\n");
	printf("  ACK SWAP Timeout: %ld sec\n",systab->timeout);
      }
      else
	printf("  REQ SWAP acknowledge check/retry disabled\n");

      printf("  Flags:");
      if (systab->verbose == cb_TRUE)
	printf(" VERBOSE");
      else
	printf(" CONCISE");
      if (systab->debug == cb_TRUE)
	printf(" +DEBUG");
      else
	printf(" -DEBUG");

      if (systab->dodisplay == cb_TRUE)
	printf(" DISPLAY=T");
      else
	printf(" DISPLAY=F");
      if (systab->doarchive == cb_TRUE)
	printf(" ARCHIVE=T");
      else
	printf(" ARCHIVE=F");
      if (systab->doautolog == cb_TRUE)
	printf(" AUTOLOG=T");
      else
	printf(" AUTOLOG=F");
      if (systab->addfits == cb_TRUE)
	printf(" ADDFITS=T");
      else
	printf(" ADDFITS=F");
      
      if (systab->noswap == cb_TRUE)
	printf(" NOSWAP=T\n");
      else
	printf(" NOSWAP=F\n");

      printf("Transfer Disks:\n");

      if (systab->reqswap)
	printf(" ** %d Pending SWAP(s) Requested **\n",systab->nreqswap);

      for(lcv=0;lcv<disktab->numdisks;lcv++) {
	sprintf(cmdWord, "%d", lcv);
	printf("  DiskName[%s]=%s Alias=%s Synched=%s Valid=%s DevName=%s\n", 
	       cmdWord, disktab->disk[lcv], disktab->alias[lcv], 
	       (disktab->use[lcv]==1) ? "Y" : "N", 
	       (disktab->valid[lcv]==1) ? "Y" : "N", 
	       disktab->device[lcv]);
      }
      printf("Mount Points:\n");
      for(lcv=0;lcv<mounttab->nummounts;lcv++) {
	sprintf(cmdWord, "%d", lcv);
	printf("  MountPoint[%s]=%s\n", cmdWord, mounttab->mount[lcv]);
      }
      printf("  Current Mount Point: %s\n\n", 
	     mounttab->mount[mounttab->current]);
    }    
    else { // for remote requests, info -> status 
      CBStatus(port, fromID); 

    }
  }

  else if (strcmp(cmdWord,"STATUS")==0) { // generic status dump 
    CBStatus(port, fromID);

  }
  else if (strcmp(cmdWord, "CBSTATUS")==0) {
      CBStatus(port, fromID); // Someone is requesting a status 
  }

  // Send (transmit) a raw command to the disk host

  else if (strcmp(cmdWord,"XMIT")==0) { 
    if (strlen(argStr) > 0) {
      if (systab->usesocket)
	XmitMsg(systab->fd_socket, systab->diskhost, "%s", argStr);
      else
	XmitMsg(systab->fd_serial, systab->diskhost, "%s", argStr);
    }
  }

  // This allows us to send a message manually to any other host on
  // the system.  Currently, it relies on the downstream serial host
  // to forward the message.
  
  else if (cmdWord[0]=='>') {
    memset(outStr,0,sizeof(outStr));
    memset(fromID,0,sizeof(fromID));
    sscanf(cmdWord,">%s",fromID);
    if (systab->usesocket)
      XmitMsg(systab->fd_socket, fromID, "%s", argStr);
    else
      XmitMsg(systab->fd_serial, fromID, "%s", argStr);

    /*
    if (systab->verbose == cb_TRUE) {
      sprintf(outStr, "%s%s %s", systab->localhost, cmdWord, argStr);
      if (outStr[strlen(outStr)]=='\n')
	ConsoleMsg("*OUT: %s", outStr);
      else
	ConsoleMsg("*OUT: %s", outStr);
    }
    */

  }
  
  // This is a special command used to allow us to read an image from
  // a disk when no disk synchronization has occurred.  This is
  // especially useful if the downstream host is not operational, as
  // we can still get data
  
  else if (strcmp(cmdWord, "DBGREAD")==0) {

    // This takes a single argument which is the disk number to read
    // from.  The number starts at zero and counts up.  Normally
    // during transfers we refer to disks by the special alias
    // assigned during disk synch, but since that would not have
    // occurred in this situation, we need a way to refer to the
    // device.  Disk zero is the first valid swap device specified in
    // the initialization file, and so on
      
    GetArg(argStr,1,argBuf);
    diskNum=atoi(argBuf);

    if ((diskNum > disktab->numdisks) || 
       (diskNum < 0) || (disktab->valid[diskNum]!=1)) {
      XmitMsg(port, fromID, "Invalid device number");
    }
    else {
      // Maxcards--the maximum number of FITS header cards would
      // normally have been determined at disk synch time, so we have
      // to simulate it
	  
      systab->maxcards = systab->headlng*BLOCK_SIZE/80;
	  
      if (GetFITS(systab->fd_disk, systab->diskhost, 
                  disktab->device[diskNum], "DEBUG", 1)<1)
	{
	  sprintf(outStr, "ERROR: Unable to transfer file");
	  XmitMsg(port, fromID, outStr);
	}
    }
  }

  else if (strcmp(cmdWord, "PING")==0) {
    Ping(port, fromID);
  
  }
  else if (strcmp(cmdWord, "PONG")==0) {
    Pong(port, fromID);

  }
  else if (strcmp(cmdWord, "INIT")==0) {
    GetArg(argStr,1,argBuf);
    if (strcmp(argBuf, "DISK")==0)
      if (strcmp(fromID, systab->diskhost)==0)
	InitDisk(systab->fd_disk, fromID, cmdStr); // Begin disk synchronization 

  }
  else if (strcmp(cmdWord, "USE")==0) {
    GetArg(argStr,1,argBuf);
    if (strstr(argBuf, "DISK")) {
      UseDisk(systab->fd_disk, fromID, cmdStr);
    }
    else if (strcmp(argBuf, "MOUNT")==0) { // Agreement on valid mount points 
      UseMount(systab->fd_disk, fromID, cmdStr);
    }

  }
  else if (strcmp(cmdWord, "ACK")==0) { // Various command acknowlegement
    GetArg(argStr,1,argBuf);

    // ACK DISK - acknowledge disk synch

    if (strcmp(argBuf, "DISK")==0) {
      AckDisk(systab->fd_disk, fromID);
    }

    // ACK SWAP - acknowledge disk swap
    else if (strcmp(argBuf, "SWAP")==0) {
      systab->reqswap = 0;
      systab->nreqswap = 0;
    }
  }
  else if (strcmp(cmdWord, "TIMEOUT")==0) { // set the REQ ACK timeout interval in seconds
    GetArg(argStr,1,argBuf);
    timeout = (long)(atoi(argBuf));
    if (timeout <= 0) {
      XmitMsg(port,fromID,"ERROR: Invalid REQ ACK Timeout interval given, must be >0");
    }
    else {
      systab->timeout = timeout;
      sprintf(outStr,"DONE: REQ ACK Timeout=%d sec",timeout);
      XmitMsg(port,fromID,outStr);
    }
  }
  else if (strcmp(cmdWord, "+ACKSWAP")==0) { // enable ACK SWAP 
    systab->doAckSwap = 1;
    sprintf(outStr,"DONE: +AckSwap - REQ SWAP acknowledge check/retry enabled with Timeout=%d sec",systab->timeout);
    XmitMsg(port,fromID,outStr);
  }
  else if (strcmp(cmdWord, "-ACKSWAP")==0) { // disable ACK SWAP 
    systab->doAckSwap = 0;
    sprintf(outStr,"DONE: -AckSwap - REQ SWAP acknowledge check/retry disabled");
    XmitMsg(port,fromID,outStr);
  }
  else if (strcmp(cmdWord, "TRANSFER")==0) { // There's at least one file out there for us 
    GetArg(argStr,1,argBuf);
    if (strstr(argBuf, "DISK")) {
      if (disktab->ackdisk) { // Make sure we've already synched disks 
	if (systab->noswap==cb_FALSE)
	  TransferDisk(systab->fd_disk, cmdStr);
	else {
	  XmitMsg(port, fromID, "%s", 
	  "ERROR: NOSWAP=T Cannot transfer files until a +SWAP command is issued at the Caliban console.");
	}
      }
      else {
	XmitMsg(port, fromID, "%s", "ERROR: Disks not synched");
      }
    }

  }
  else if (strcmp(cmdWord, "REQ")==0) { // An information request
    GetArg(argStr,1,argBuf);
    // valid mount points 
    if (strcmp(argBuf, "MOUNT")==0)   
      ReqMount(systab->fd_disk, fromID);

  }

  else if (strcmp(cmdWord, "LASTFILE")==0)  { // what was the last file written?
      XmitMsg(port, fromID, "STATUS: LASTFILE=%s", systab->lastfile);
  
  }

  else if (strcmp(cmdWord, "PATH")==0)  { // what is the current path (mount point)?
      XmitMsg(port, fromID, "STATUS: PATH=%s", mounttab->mount[mounttab->current]);

  }
 
  // report our version and compilation info 

  else if (strcmp(cmdWord, "VERSION")==0)  {
    XmitMsg(port, fromID, "STATUS: Version=(%s) ExeName=%s UserID=%s CompilationDate=%s CompilationTime=%s", 
	    VERSION,systab->exefile,systab->userid,COMPDATE,COMPTIME);
  }

  // these commands allow interactive setting of runtime configuration parameters
   

  // enable verbose mode 

  else if ((strcmp(cmdWord,"VERBOSE")==0) ||
	   (strcmp(cmdWord,"+VERBOSE")==0)) {
    systab->verbose = cb_TRUE;
    printf("VERBOSE mode enabled\n");

  }

  // disable verbose mode 

  else if ((strcmp(cmdWord,"CONCISE")==0) ||
	   (strcmp(cmdWord,"-VERBOSE")==0)) {
    systab->verbose = cb_FALSE;
    printf("VERBOSE mode disabled\n");
    
  }

  // enable debug printout (super-verbose) 

  else if ((strcmp(cmdWord,"DEBUG")==0) ||
	   (strcmp(cmdWord,"+DEBUG")==0) ) {
    systab->debug = cb_TRUE;
    printf("DEBUG mode enabled\n");
    
  }

  // disable debug printout (super-verbose) 
  
  else if (strcmp(cmdWord,"-DEBUG")==0) {
    systab->debug = cb_FALSE;
    printf("DEBUG mode disabled\n");
  }
  
  // if someone goes off line, this out-of-protocol message is often sent 

  else if (strcmp(cmdWord, "OFFLINE")==0)  {

  }

  // these last set of commands service ICIMACS protocol message-type codes 

  else if (strcmp(cmdWord, "ERROR:")==0) // Someone is reporting an error 
    {
    }
  else if (strcmp(cmdWord, "FATAL:")==0) // Someone is reporting a fatal error 
    {
    }
  else if (strcmp(cmdWord, "WARNING:")==0) // Someone is reporting a warning 
    {
    }
  else if (strcmp(cmdWord, "STATUS:")==0) { // Someone is reporting status 
    Status(fromID, cmdStr);
  }

  else if (strcmp(cmdWord, "DONE:") == 0) { // someone is reporting request completion 
    
  }

  // finally, handle blank or unknwon commands 

  else if (strcmp(cmdWord, "")==0) {

  }
  else {
    XmitMsg(port, fromID, "ERROR: Unknown Command '%s'", systab->oldinbuf);

  }

  // bottom of the command tree, clear and return 

  cmdStr[0] = NUL;

}

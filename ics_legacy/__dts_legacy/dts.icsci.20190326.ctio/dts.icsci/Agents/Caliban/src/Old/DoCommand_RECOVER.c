#include "Caliban.h"

// added port, indicating who sent the command, so who gets the reply 

void 
DoCommand(int port, char *cmdline)
{
  int lcv=0;
  int numlines=0;              // Used for displaying n log lines on the screen 
  int disknum=0;               // Disk table index                              
  int nimages=0;               // Number of images to read
  long timeout=0;              // default test timeout interval

  char logcmd[MED_STR_SIZE];   //
  char xfercmd[MED_STR_SIZE];  // Data Transfer command string (see RECOVER)
  char argbuf[BUF_SIZE];       // Used during parsing of command lines          
  char outbuf[BUF_SIZE];       // General purpose output buffer                 

  char host[SHORT_STR_SIZE];   // Host name command was received from           
  char dest[SHORT_STR_SIZE];   // Host name command is destined for             
  FILE *logpipe;               // Handle to pipe for log display command        

  // stuff for history handling 

  register HIST_ENTRY **the_list;
  register int ihist;

  // Yow! 

  UpperCase(cmdline); // Makes comparisons much easier 

  // The first argument is assumed to contain the host name 

  GetArg(cmdline, 1, host);

  strncpy(dest, host+3, 2); // Characters 4 and 5 are assumed to be the destination host 

  host[2] = NUL; // Chop off the destination portion of the address string 

  if (strncmp(host, systab->localhost, 2)==0)
    port=0;

  // We have a verbose switch which determines whether serial input is echoed       

  if ((systab->verbose==cb_TRUE) && 
     (strcmp(host, systab->localhost)!=0))   {
    ConsoleMsg("IN: %s", systab->oldinbuf);
  }

  GetArg(cmdline, 2, argbuf); // The second argument is assumed to be the first word of a valid command 

  // QUIT or Q will result in setting the done flag which exits this   
  // whole loop (first confirm that the user didn't fat-finger a key   
  
  if (strcmp(argbuf, "QUIT")==0 || strcmp(argbuf, "Q")==0) {
    systab->done = 1;

  }

  // history command 

  else if (strcasecmp(argbuf,"history")==0) {
    if (port == 0) {
      printf("\n");
      the_list = history_list();
      if (the_list)
	for (ihist=0; the_list[ihist]; ihist++)
	  printf("%5d   %s\n",ihist+history_base,the_list[ihist]->line);
      rl_refresh_line(0,0);
    } 
    else {
      XmitMsg(port, host, "ERROR: history command only available on the console");
    }
  }

  // HELP or ? displays a list of the available commands which can be  
  // entered at the keyboard--note that this does not represent the    
  // full list of supported commands                                   
  
  else if (strcmp(argbuf, "?")==0 || strcmp(argbuf, "HELP")==0) {
    if (port==0) {
      printf("\nCaliban Interactive Commands:\n");
      printf("  HELP or ?     - This list\n");
      printf("  QUIT or Q     - End the Caliban session and Exit\n");
      printf("  INFO          - Detailed info on this Caliban session\n");
      printf("  STATUS        - Return the Caliban status\n");
      printf("  LOG n         - Print out the last n lines of the log file\n");
      printf("  +/-ARCHIVE    - Enable/Disable/Show archiving\n");
      printf("  +/-AUTOLOG    - Enable/Disable/Show autologging status\n");
      printf("  +/-DISPLAY    - Enable/Disable/Show autodisplay status\n");
      printf("  +/-ADDFITS    - Enable/Disable/Show fits extension status\n");
      printf("  +SWAP         - Enable transfer disk swapping\n");
      printf("  RESTORE       - Restore system flags to default values\n");
      printf("  HISTORY       - Show command history\n");
      printf("  Ctrl+L        - Clear screen\n");
      printf("  >{host} {msg} - Sends message {msg} to hostname {host}\n");
      printf("  +/-VERBOSE    - Enable/Disable verbose echo of all messages\n");
      printf("  +/-DEBUG      - Enable/Disable super-verbose engineering output\n");
      printf("  DBGREAD n     - Reads an image from disk n (n>=0) without\n");
      printf("                    having synched disks\n");
      printf("  RECOVER d n   - Attempt to recover n images from disk d (d=0|1)\n");
      printf("                    after a system hang during transfers.\n");
    }
    else {
      XmitMsg(port, host, "ERROR: Caliban HELP command only available on the console");
    }
      
  }
  else if (strcmp(argbuf, "+ARCHIVE")==0) {
    systab->doarchive = cb_TRUE;
    XmitMsg(port, host, "STATUS: ARCHIVE=T");
  }

  else if (strcmp(argbuf, "-ARCHIVE")==0) {
    systab->doarchive = cb_FALSE;
    XmitMsg(port, host, "STATUS: ARCHIVE=F");
  }

  else if (strcmp(argbuf, "ARCHIVE")==0) {
    if (systab->doarchive == cb_TRUE)
      XmitMsg(port, host, "STATUS: ARCHIVE=T");
    else
      XmitMsg(port, host, "STATUS: ARCHIVE=F");
  }

  else if (strcmp(argbuf, "+AUTOLOG")==0) {
    systab->doautolog = cb_TRUE;
    XmitMsg(port, host, "STATUS: AUTOLOG=T");
  }

  else if (strcmp(argbuf, "-AUTOLOG")==0) {
    systab->doautolog = cb_FALSE;
    XmitMsg(port, host, "STATUS: AUTOLOG=F");
  }

  else if (strcmp(argbuf, "AUTOLOG")==0) {
    if (systab->doautolog == cb_TRUE)
      XmitMsg(port, host, "STATUS: AUTOLOG=T");
    else
      XmitMsg(port, host, "STATUS: AUTOLOG=F");
  }

  else if (strcmp(argbuf, "+DISPLAY")==0) {
    systab->dodisplay = cb_TRUE;
    XmitMsg(port, host, "STATUS: DISPLAY=T");
  }

  else if (strcmp(argbuf, "-DISPLAY")==0) {
    systab->dodisplay = cb_FALSE;
    XmitMsg(port, host, "STATUS: DISPLAY=F");
  }

  else if (strcmp(argbuf, "DISPLAY")==0) {
    if (systab->dodisplay == cb_TRUE)
      XmitMsg(port, host, "STATUS: DISPLAY=T");
    else
      XmitMsg(port, host, "STATUS: DISPLAY=F");
  }

  else if (strcmp(argbuf, "+ADDFITS")==0) {
    systab->addfits = cb_TRUE;
    XmitMsg(port, host, "STATUS: ADDFITS=T");
  }

  else if (strcmp(argbuf, "-ADDFITS")==0) {
    systab->addfits = cb_FALSE;
    XmitMsg(port, host, "STATUS: ADDFITS=F");
  }

  else if (strcmp(argbuf, "ADDFITS")==0) {
    if (systab->addfits == cb_TRUE)
      XmitMsg(port, host, "STATUS: ADDFITS=T");
    else
      XmitMsg(port, host, "STATUS: ADDFITS=F");
  }

  else if (strcmp(argbuf, "+SWAP")==0) {
    systab->noswap=cb_FALSE;
    XmitMsg(port, host, "STATUS: SWAP=T");

    // Tell the downstream disk host that it can use the disk again

    XmitMsg(systab->fd_disk, systab->diskhost, "%s", "REQ SWAP"); 
    systab->reqswap = 1;
    systab->nreqswap++;
  }

  else if (strcmp(argbuf, "-SWAP")==0) {
    systab->noswap=cb_TRUE;
    XmitMsg(port, host, "STATUS: SWAP=F");
  }

  else if (strcmp(argbuf, "SWAP")==0) {
    if (systab->noswap == cb_TRUE)
      XmitMsg(port, host, "STATUS: SWAP=T");
    else
      XmitMsg(port, host, "STATUS: SWAP=F");
  }

  else if (strcmp(argbuf, "RESTORE")==0) {
    systab->doarchive = systab->olddoarchive;
    systab->dodisplay = systab->olddodisplay;
    systab->doautolog = systab->olddoautolog;
    systab->addfits = systab->oldaddfits;
    XmitMsg(port, host, "STATUS: Caliban system variables restored to default values");
  }

  // resynch with the diskhost (ping it)

  else if (strcmp(argbuf,"RESYNCH")==0) {
    XmitMsg(systab->fd_disk, systab->diskhost, "%s", "PING"); 
    sprintf(outbuf,"DONE: Caliban/%s transfer disk resynch initiated",systab->diskhost);
    XmitMsg(port, host, outbuf);
  }

  // Attempt to recover data from a transfer disk en masse (bad fault recovery)

  else if (strcmp(argbuf,"RECOVER")==0) {
    GetArg(cmdline, 3, outbuf);
    disknum = atoi(outbuf);
    if ((disknum > disktab->numdisks) || 
       (disknum < 0) || (disktab->valid[disknum]!=1)) {
      XmitMsg(port, host, "Invalid Disk Device Number (usually 0 or 1)");
    }
    else {
      GetArg(cmdline, 4, outbuf);
      nimages = atoi(outbuf);
      if (nimages < 1) {
	XmitMsg(port,host,"Must specify the number of images to recover");
      }
      else {
	// Try to recover N images from the designated disk
	XmitMsg(port,host,"Attempting to recover up to %d images from transfer disk %s",
		nimages,disktab->device[disknum]);
	sprintf(xfercmd,"TRANSFER DISK %s %d %s",disktab->device[disknum],nimages,host);
	TransferDisk(systab->fd_disk, xfercmd);
      }
    }
  }

  // We have the ability to display the last n lines of the log file on screen 
  // n defaults to 10                                                          
  
  else if (strcmp(argbuf, "LOG")==0) {
    GetArg(cmdline, 2, argbuf);
    numlines=atoi(argbuf);
    if (numlines<1)
      numlines = 10;
      
    // We open a pipe which submits a command to the shell 
    
    printf("\n");
    sprintf(logcmd, "tail -%d %s", numlines, systab->logfilename);
    logpipe = popen(logcmd, "r");
      
    // Then we read the resulting output from the pipe 
      
    while(fgets(outbuf, sizeof(outbuf), logpipe) != NULL)
      XmitMsg(port, host, "STATUS: LOG: %s", outbuf);
      
    if (logpipe!=0)
      pclose(logpipe);
  }
  
  // This causes a status table to be displayed on screen 

  else if (strcmp(argbuf, "INFO")==0) {
    if (port == 0) { // screen dump 
      printf("\nCurrent Caliban Status:\n");
      printf("  VERSION: %s [%s %s]\n", VERSION,COMPDATE,COMPTIME);
      printf("  HostName: %s\n", systab->localhost);
      printf("  Executable: %s\n",systab->exefile);
      printf("  Started by user '%s' at %s\n",systab->userid,systab->starttime);
      if (systab->useserial) {
	printf("  SerialPort: %s\n", systab->serialdev);
      }
      if (systab->usesocket) {
	printf("Instrument Server:\n");
	printf("  ServerHost: %s\n",systab->sockethost);
	sprintf(argbuf,"%d",systab->serverport);
	printf("  ServerAddr: %s:%s\n",systab->serverIPaddr,argbuf);
	printf("Caliban Client:\n");
	sprintf(argbuf,"%d",systab->clientport);
	printf("  ClientPort: %s\n",argbuf);
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
      sprintf(argbuf, "%d", BLOCK_SIZE);
      printf("  BlockSize: %s\n", argbuf);
      printf("  LastFile: %s\n", systab->lastfile);
      sprintf(argbuf, "%d", systab->headwritten);
      printf("  HeadBytes: %s\n", argbuf);
      sprintf(argbuf, "%d", systab->datawritten);
      printf("  DataBytes: %s\n", argbuf);
      printf("  Pending REQ Timeout: %ld sec\n",systab->timeout);

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
	sprintf(argbuf, "%d", lcv);
	printf("  DiskName[%s]=%s Alias=%s Synched=%s Valid=%s DevName=%s\n", 
	       argbuf, disktab->disk[lcv], disktab->alias[lcv], 
	       (disktab->use[lcv]==1) ? "Y" : "N", 
	       (disktab->valid[lcv]==1) ? "Y" : "N", 
	       disktab->device[lcv]);
      }
      printf("Mount Points:\n");
      for(lcv=0;lcv<mounttab->nummounts;lcv++) {
	sprintf(argbuf, "%d", lcv);
	printf("  MountPoint[%s]=%s\n", argbuf, mounttab->mount[lcv]);
      }
      printf("  Current Mount Point: %s\n\n", 
	     mounttab->mount[mounttab->current]);
    }    
    else { // for remote requests, info -> status 
      CBStatus(port, host); 

    }
  }

  else if (strcmp(argbuf,"STATUS")==0) { // generic status dump 
    CBStatus(port, host);

  }
  else if (strcmp(argbuf, "CBSTATUS")==0) {
      CBStatus(port, host); // Someone is requesting a status 
  }

  // This allows us to send a message manually to any other host on the system.  Currently, it relies 
  // on the downstream serial host to forward the message.  This allows us even to forward a message  
  // back to ourselves, which is how we get around certain commands not being available from the      
  // command line                                                                                         
  
  else if (argbuf[0]=='>') {
    memset(outbuf,0,sizeof(outbuf));
    memset(host,0,sizeof(host));
    sscanf(cmdline+6,">%s %[^\n]",host,outbuf);
    if (systab->usesocket) {
      XmitMsg(systab->fd_socket, host, "%s", outbuf);
    }
    else {
      XmitMsg(systab->fd_serial, host, "%s", outbuf);
    }
    if (systab->verbose == cb_TRUE) {
      sprintf(outbuf, "%s%s", systab->localhost, cmdline+6);
      if (outbuf[strlen(outbuf)]=='\n')
	ConsoleMsg("OUT: %s", outbuf);
      else
	ConsoleMsg("OUT: %s", outbuf);
    }

  }
  
  // This is a special command used to allow us to read an image from a disk when 
  // no disk synchronization has occurred.  This is especially useful if the      
  // downstream host is not operational, as we can still get data                 
  
  else if (strcmp(argbuf, "DBGREAD")==0) {

    // This takes a single argument which is the disk number to read from.  The 
    // number starts at zero and counts up.  Normally during transfers we refer 
    // to disks by the special alias assigned during disk synch, but since that 
    // would not have occurred in this situation, we need a way to refer to     
    // the device.  Disk zero is the first valid swap device specified in the   
    // initialization file, and so on                                           
      
    GetArg(cmdline, 3, outbuf);
      
    disknum=atoi(outbuf);

    if ((disknum > disktab->numdisks) || 
       (disknum < 0) || (disktab->valid[disknum]!=1)) {
      XmitMsg(port, host, "Invalid device number");
    }
    else {
      // Maxcards--the maximum number of FITS header cards would normally have been 
      // determined at disk synch time, so we have to simulate it                   
	  
      systab->maxcards = systab->headlng*BLOCK_SIZE/80;
	  
      if (GetFITS(systab->fd_disk, systab->diskhost, disktab->device[disknum], "DEBUG", 1)<1)
	{
	  sprintf(outbuf, "ERROR: Unable to transfer file");
	  XmitMsg(port, host, outbuf);
	}
    }
  }

  else if (strcmp(argbuf, "PING")==0) {
    Ping(port, host);
  
  }
  else if (strcmp(argbuf, "PONG")==0) {
    Pong(port, host);

  }
  else if (strcmp(argbuf, "INIT")==0) {
    GetArg(cmdline, 3, argbuf);
    if (strcmp(argbuf, "DISK")==0)
      if (strcmp(host, systab->diskhost)==0)
	InitDisk(systab->fd_disk, host, cmdline); // Begin disk synchronization 

  }
  else if (strcmp(argbuf, "USE")==0) {
    GetArg(cmdline, 3, argbuf);
    if (strstr(argbuf, "DISK")) {
      UseDisk(systab->fd_disk, host, cmdline);
    }
    else if (strcmp(argbuf, "MOUNT")==0) { // Agreement on valid mount points 
      UseMount(systab->fd_disk, host, cmdline);
    }

  }
  else if (strcmp(argbuf, "ACK")==0) { // Various command acknowlegement
    GetArg(cmdline, 3, argbuf);

    // ACK DISK - acknowledge disk synch

    if (strcmp(argbuf, "DISK")==0) {
      AckDisk(systab->fd_disk, host);
    }

    // ACK SWAP - acknowledge disk swap
    else if (strcmp(argbuf, "SWAP")==0) {
      systab->reqswap = 0;
      systab->nreqswap = 0;
    }
  }
  else if (strcmp(argbuf, "TIMEOUT")==0) { // set the REQ ACK timeout interval in seconds
    GetArg(cmdline, 3, argbuf);
    timeout = (long)(atoi(argbuf));
    if (timeout <= 0) {
      XmitMsg(port,host,"ERROR: Invalid REQ ACK Timeout interval given, must be >0");
    }
    else {
      systab->timeout = timeout;
      sprintf(outbuf,"DONE: REQ ACK Timeout=%d sec",timeout);
      XmitMsg(port,host,outbuf);
    }
  }
  else if (strcmp(argbuf, "TRANSFER")==0) { // There's at least one file out there for us 
    GetArg(cmdline, 3, argbuf);
    if (strstr(argbuf, "DISK")) {
      if (disktab->ackdisk) { // Make sure we've already synched disks 
	if (systab->noswap==cb_FALSE)
	  TransferDisk(systab->fd_disk, cmdline);
	else {
	  XmitMsg(port, host, "%s", 
	  "ERROR: NOSWAP=T Cannot transfer files until a +SWAP command is issued at the Caliban console.");
	}
      }
      else {
	XmitMsg(port, host, "%s", "ERROR: Disks not synched");
      }
    }

  }
  else if (strcmp(argbuf, "REQ")==0) { // An information request
    GetArg(cmdline, 3, argbuf);
    // valid mount points 
    if (strcmp(argbuf, "MOUNT")==0)   
      ReqMount(systab->fd_disk, host);

  }

  else if (strcmp(argbuf, "LASTFILE")==0)  { // what was th elast file written?
      XmitMsg(port, host, "STATUS: LASTFILE=%s", systab->lastfile);
  
  }

  else if (strcmp(argbuf, "PATH")==0)  { // what is the current path (mount point)?
      XmitMsg(port, host, "STATUS: PATH=%s", mounttab->mount[mounttab->current]);

  }
 
  // report our version and compilation info 

  else if (strcmp(argbuf, "VERSION")==0)  {
    XmitMsg(port, host, "STATUS: Version=(%s) ExeName=%s UserID=%s CompilationDate=%s CompilationTime=%s", 
	    VERSION,systab->exefile,systab->userid,COMPDATE,COMPTIME);
  }

  // these commands allow interactive setting of runtime configuration parameters
   

  // enable verbose mode 

  else if ((strcmp(argbuf,"VERBOSE")==0) ||
	   (strcmp(argbuf,"+VERBOSE")==0)) {
    systab->verbose = cb_TRUE;
    printf("VERBOSE mode enabled\n");

  }

  // disable verbose mode 

  else if ((strcmp(argbuf,"CONCISE")==0) ||
	   (strcmp(argbuf,"-VERBOSE")==0)) {
    systab->verbose = cb_FALSE;
    printf("VERBOSE mode disabled\n");
    
  }

  // enable debug printout (super-verbose) 

  else if ((strcmp(argbuf,"DEBUG")==0) ||
	   (strcmp(argbuf,"+DEBUG")==0) ) {
    systab->debug = cb_TRUE;
    printf("DEBUG mode enabled\n");
    
  }

  // disable debug printout (super-verbose) 
  
  else if (strcmp(argbuf,"-DEBUG")==0) {
    systab->debug = cb_FALSE;
    printf("DEBUG mode disabled\n");
  }
  
  // if someone goes off line, this out-of-protocol message is often sent 

  else if (strcmp(argbuf, "OFFLINE")==0)  {

  }

  // these last set of commands service ICIMACS protocol message-type codes 

  else if (strcmp(argbuf, "ERROR:")==0) // Someone is reporting an error 
    {
    }
  else if (strcmp(argbuf, "FATAL:")==0) // Someone is reporting a fatal error 
    {
    }
  else if (strcmp(argbuf, "WARNING:")==0) // Someone is reporting a warning 
    {
    }
  else if (strcmp(argbuf, "STATUS:")==0) { // Someone is reporting status 
    Status(host, cmdline);
  }

  else if (strcmp(argbuf, "DONE:") == 0) { // someone is reporting request completion 
    
  }

  // finally, handle blank or unknwon commands 

  else if (strcmp(argbuf, "")==0) {

  }
  else {
    XmitMsg(port, host, "ERROR: Unknown Command '%s'", systab->oldinbuf);

  }

  // bottom of the command tree, clear and return 

  cmdline[0] = NUL;

}

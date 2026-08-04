#include "Caliban.h"

void DoCommand(char *cmdline)
{
  int port=0;
  int lcv=0;
  int numlines=0;              /* Used for displaying n log lines on the screen */
  int disknum=0;               /* Disk table index                              */

  char logcmd[MED_STR_SIZE];   /* "                                             */
  char argbuf[BUF_SIZE];       /* Used during parsing of command lines          */
  char outbuf[BUF_SIZE];       /* General purpose output buffer                 */

  char host[SHORT_STR_SIZE];   /* Host name command was received from           */
  char dest[SHORT_STR_SIZE];   /* Host name command is destined for             */
  FILE *logpipe;               /* Handle to pipe for log display command        */

  UpperCase(cmdline); /* Makes comparisons much easier */

  /* The first argument is assumed to contain the host name */

  GetArg(cmdline, 1, host);

  strncpy(dest, host+3, 2); /* Characters 4 and 5 are assumed to be the destination host */

  host[2] = NUL; /* Chop off the destination portion of the address string */

  if (strncmp(host, systab->localhost, 2)==0)
    port=0;
  else
    port=systab->fd_serial;

  /* We have a verbose switch which determines whether serial input is echoed       */

  if((systab->verbose==cb_TRUE) && (strcmp(host, systab->localhost)!=0))
    {
      ConsoleMsg("IN:  %s", cmdline);
    }

  GetArg(cmdline, 2, argbuf); /* The second argument is assumed to be the first word of a valid command */

  /* QUIT or Q will result in setting the done flag which exits this   */
  /* whole loop (first confirm that the user didn't fat-finger a key   */
  
  if(strcmp(argbuf, "QUIT")==0 || strcmp(argbuf, "Q")==0)
    {
      systab->done=1;
    }
  
  /* HELP or ? displays a list of the available commands which can be  */
  /* entered at the keyboard--note that this does not represent the    */
  /* full list of supported commands                                   */
  
  else if(strcmp(argbuf, "?")==0 || strcmp(argbuf, "HELP")==0)
    {
      XmitMsg(port, host, "STATUS: Command List:");
      XmitMsg(port, host, "STATUS: HELP or ?       -This list");
      XmitMsg(port, host, "STATUS: QUIT or Q       -End program");
      XmitMsg(port, host, "STATUS: CLEAR or C      -Clear the screen");
      XmitMsg(port, host, "STATUS: CHKSTATUS or CS -Status report");
      XmitMsg(port, host, "STATUS: LOG n           -Prints out last n lines of the log file");
      XmitMsg(port, host, "STATUS: +/-ARCHIVE      -Enable/Disable/Show archiving");
      XmitMsg(port, host, "STATUS: +/-AUTOLOG      -Enable/Disable/Show autologging status");
      XmitMsg(port, host, "STATUS: +/-DISPLAY      -Enable/Disable/Show autodisplay status");
      XmitMsg(port, host, "STATUS: +/-ADDFITS      -Enable/Disable/Show fits extension status");
      XmitMsg(port, host, "STATUS: +SWAP           -Enable swapping");
      XmitMsg(port, host, "STATUS: RESTORE         -Restore system flags to default values");
      XmitMsg(port, host, "STATUS: {Ctrl-P}        -Recall last command");
      XmitMsg(port, host, "STATUS: >{host} {msg}   -Sends message {msg} to hostname {host}");
      XmitMsg(port, host, "STATUS: {ESC}           -Clears the current input line");
      XmitMsg(port, host, "STATUS: DBGREAD n       -Reads an image from disk n (n>=0) without");
      XmitMsg(port, host, "STATUS:                  having synched disks");
    }
  else if(strcmp(argbuf, "+ARCHIVE")==0)
    {
      systab->doarchive = cb_TRUE;
      XmitMsg(port, host, "STATUS: ARCHIVE=T");
    }
  else if(strcmp(argbuf, "-ARCHIVE")==0)
    {
      systab->doarchive = cb_FALSE;
      XmitMsg(port, host, "STATUS: ARCHIVE=F");
    }
  else if(strcmp(argbuf, "ARCHIVE")==0)
    {
      if(systab->doarchive == cb_TRUE)
	XmitMsg(port, host, "STATUS: ARCHIVE=T");
      else
	XmitMsg(port, host, "STATUS: ARCHIVE=F");
    }
  else if(strcmp(argbuf, "+AUTOLOG")==0)
    {
      systab->doautolog = cb_TRUE;
      XmitMsg(port, host, "STATUS: AUTOLOG=T");
    }
  else if(strcmp(argbuf, "-AUTOLOG")==0)
    {
      systab->doautolog = cb_FALSE;
      XmitMsg(port, host, "STATUS: AUTOLOG=F");
    }
  else if(strcmp(argbuf, "AUTOLOG")==0)
    {
      if(systab->doautolog == cb_TRUE)
	XmitMsg(port, host, "STATUS: AUTOLOG=T");
      else
	XmitMsg(port, host, "STATUS: AUTOLOG=F");
    }
  else if(strcmp(argbuf, "+DISPLAY")==0)
    {
      systab->dodisplay = cb_TRUE;
      XmitMsg(port, host, "STATUS: DISPLAY=T");
    }
  else if(strcmp(argbuf, "-DISPLAY")==0)
    {
      systab->dodisplay = cb_FALSE;
      XmitMsg(port, host, "STATUS: DISPLAY=F");
    }
  else if(strcmp(argbuf, "DISPLAY")==0)
    {
      if(systab->dodisplay == cb_TRUE)
	XmitMsg(port, host, "STATUS: DISPLAY=T");
      else
	XmitMsg(port, host, "STATUS: DISPLAY=F");
    }
  else if(strcmp(argbuf, "+ADDFITS")==0)
    {
      systab->addfits = cb_TRUE;
      XmitMsg(port, host, "STATUS: ADDFITS=T");
    }
  else if(strcmp(argbuf, "-ADDFITS")==0)
    {
      systab->addfits = cb_FALSE;
      XmitMsg(port, host, "STATUS: ADDFITS=F");
    }
  else if(strcmp(argbuf, "ADDFITS")==0)
    {
      if(systab->addfits == cb_TRUE)
	XmitMsg(port, host, "STATUS: ADDFITS=T");
      else
	XmitMsg(port, host, "STATUS: ADDFITS=F");
    }
  else if(strcmp(argbuf, "+SWAP")==0)
    {
      systab->noswap=cb_FALSE;
      XmitMsg(port, host, "STATUS: SWAP=T");
      XmitMsg(systab->fd_serial, systab->serialhost, "%s", "REQ SWAP"); /* Tell downstream host it's ok to use the disk again */
    }
  else if(strcmp(argbuf, "-SWAP")==0)
    {
      systab->noswap=cb_TRUE;
      XmitMsg(port, host, "STATUS: SWAP=F");
    }
  else if(strcmp(argbuf, "SWAP")==0)
    {
      if(systab->noswap == cb_TRUE)
	XmitMsg(port, host, "STATUS: SWAP=T");
      else
	XmitMsg(port, host, "STATUS: SWAP=F");
    }
  else if(strcmp(argbuf, "CLEAR")==0 || strcmp(argbuf, "C")==0) /* Clear the screen */
    {
      wclear(systab->output);
      wrefresh(systab->output);
      Prompt();
    }
  else if(strcmp(argbuf, "RESTORE")==0)
    {
      systab->doarchive = systab->olddoarchive;
      systab->dodisplay = systab->olddodisplay;
      systab->doautolog = systab->olddoautolog;
      systab->addfits = systab->oldaddfits;
      XmitMsg(port, host, "STATUS: System variables restored to default values");
    }
  
  /* We have the ability to display the last n lines of the log file on screen */
  /* n defaults to 10                                                          */
  
  else if(strcmp(argbuf, "LOG")==0)
    {
      GetArg(cmdline, 2, argbuf);
      numlines=atoi(argbuf);
      if(numlines<1)
	numlines = 10;
      
      /* We open a pipe which submits a command to the shell */
      
      sprintf(logcmd, "tail -%d %s", numlines, systab->logfilename);
      logpipe = popen(logcmd, "r");
      
      /* Then we read the resulting output from the pipe */
      
      while(fgets(outbuf, sizeof(outbuf), logpipe) != NULL)
	XmitMsg(port, host, "STATUS: LOG: %s", outbuf);
      
      if(logpipe!=0)
	pclose(logpipe);
    }
  
  /* This causes a status table to be displayed on screen */

  else if(strcmp(argbuf, "CHKSTATUS")==0 || strcmp(argbuf, "CS")==0)
    {
      XmitMsg(port, host, "STATUS: HOST='%s'", systab->localhost);
      XmitMsg(port, host, "STATUS: VERSION='%s'", VERSION);
      XmitMsg(port, host, "STATUS: SERIALHOST='%s'", systab->serialhost);
      XmitMsg(port, host, "STATUS: SERIALPORT='%s'", systab->serialdev);
      XmitMsg(port, host, "STATUS: LOGFILE='%s'", systab->logfilename);
      sprintf(argbuf, "%d", BLOCK_SIZE);
      XmitMsg(port, host, "STATUS: BLOCKSIZE=%s", argbuf);
      XmitMsg(port, host, "STATUS: LASTFILE='%s'", systab->lastfile);
      sprintf(argbuf, "%d", systab->headwritten);
      XmitMsg(port, host, "STATUS: HEADBYTES=%s", argbuf);
      sprintf(argbuf, "%d", systab->datawritten);
      XmitMsg(port, host, "STATUS: DATABYTES=%s", argbuf);
      
      if(systab->dodisplay == cb_TRUE)
	XmitMsg(port, host, "STATUS: DISPLAY=T");
      else
	XmitMsg(port, host, "STATUS: DISPLAY=F");
      if(systab->doarchive == cb_TRUE)
	XmitMsg(port, host, "STATUS: ARCHIVE=T");
      else
	XmitMsg(port, host, "STATUS: ARCHIVE=F");
      if(systab->doautolog == cb_TRUE)
	XmitMsg(port, host, "STATUS: AUTOLOG=T");
      else
	XmitMsg(port, host, "STATUS: AUTOLOG=F");
      if(systab->addfits == cb_TRUE)
	XmitMsg(port, host, "STATUS: ADDFITS=T");
      else
	XmitMsg(port, host, "STATUS: ADDFITS=F");
      
      if(systab->noswap == cb_TRUE)
	XmitMsg(port, host, "STATUS: NOSWAP=T");
      else
	XmitMsg(port, host, "STATUS: NOSWAP=F");
      
      XmitMsg(port, host, "STATUS: CURMOUNT='%s'", mounttab->mount[mounttab->current]);
      for(lcv=0;lcv<disktab->numdisks;lcv++)
	{
	  sprintf(argbuf, "%d", lcv);
	  XmitMsg(port, host, "STATUS: DISKNAME(%s)='%s' ALIAS='%s' SYNCD=%s VALID=%s DEVNAME='%s'", argbuf, disktab->disk[lcv], disktab->alias[lcv], (disktab->use[lcv]==1) ? "Y" : "N", (disktab->valid[lcv]==1) ? "Y" : "N", disktab->device[lcv]);
	}
      for(lcv=0;lcv<mounttab->nummounts;lcv++)
	{
	  sprintf(argbuf, "%d", lcv);
	  XmitMsg(port, host, "STATUS: MOUNTNAME(%s)='%s'", argbuf, mounttab->mount[lcv]);
	}
    }      

  /* This allows us to send a message manually to any other host on the system.  Currently, it relies */
  /* on the downstream serial host to forward the message.  This allows us even to forward a message  */
  /* back to ourselves, which is how we get around certain commands not being available from the      */
  /* command line                                                                                     */    
  
  else if(argbuf[0]=='>')
    {
      sprintf(outbuf, "%s%s\r", systab->localhost, cmdline+6);
      write(systab->fd_serial, outbuf, strlen(outbuf));
      if(systab->verbose == cb_TRUE)
	{
	  sprintf(outbuf, "%s%s", systab->localhost, cmdline+6);
	  if(outbuf[strlen(outbuf)]=='\n')
	    ConsoleMsg("%s", outbuf);
	  else
	    ConsoleMsg("OUT: %s", outbuf);
	}
    }
  
  /* This is a special command used to allow us to read an image from a disk when */
  /* no disk synchronization has occurred.  This is especially useful if the      */
  /* downstream host is not operational, as we can still get data                 */
  
  else if(strcmp(argbuf, "DBGREAD")==0)
    {
      /* This takes a single argument which is the disk number to read from.  The */
      /* number starts at zero and counts up.  Normally during transfers we refer */
      /* to disks by the special alias assigned during disk synch, but since that */
      /* would not have occurred in this situation, we need a way to refer to     */
      /* the device.  Disk zero is the first valid swap device specified in the   */
      /* initialization file, and so on                                           */
      
      GetArg(cmdline, 3, outbuf);
      
      disknum=atoi(outbuf);

      if((disknum > disktab->numdisks) || (disknum < 0) || (disktab->valid[disknum]!=1))
	{
	  XmitMsg(port, host, "Invalid device number");
	}
      else
	{
	  /* Maxcards--the maximum number of FITS header cards would normally have been */
	  /* determined at disk synch time, so we have to simulate it                   */
	  
	  systab->maxcards = systab->headlng*BLOCK_SIZE/80;
	  
	  if(GetFITS(systab->fd_serial, systab->serialhost, disktab->device[disknum], "DEBUG", 1)<1)
	    {
	      sprintf(outbuf, "ERROR: Unable to transfer file");
	      XmitMsg(port, host, outbuf);
	    }
	}
    }

  else if (strcmp(argbuf, "PING")==0) /* Call the Ping handler routine */
    {
      Ping(systab->fd_serial, host);
    }
  else if (strcmp(argbuf, "PONG")==0) /* Call the Pong handler routine */
    {
      Pong(host);
    }
  else if (strcmp(argbuf, "INIT")==0) /* Disk synchronization command */
    {
      GetArg(cmdline, 3, argbuf);
      if(strcmp(argbuf, "DISK")==0)
	if(strcmp(host, systab->serialhost)==0)
	  InitDisk(systab->fd_serial, host, cmdline); /* Begin disk synchronization */
    }
  else if (strcmp(argbuf, "USE")==0) /* Agreement on valid disk devices and names */
    {
      GetArg(cmdline, 3, argbuf);
      if(strstr(argbuf, "DISK")) {
	UseDisk(systab->fd_serial, host, cmdline);
      }
      else if(strcmp(argbuf, "MOUNT")==0) { /* Agreement on valid mount points */
	UseMount(systab->fd_serial, host, cmdline);
      }
    }
  else if (strcmp(argbuf, "ACK")==0) /* Valid disk synch completion confirmation */
    {
      GetArg(cmdline, 3, argbuf);
      if(strcmp(argbuf, "DISK")==0)
	AckDisk(systab->fd_serial, host);
    }
  else if (strcmp(argbuf, "TRANSFER")==0) /* There's at least one file out there for us */
    {
      GetArg(cmdline, 3, argbuf);
      if(strstr(argbuf, "DISK"))
	{
	  if(disktab->ackdisk) /* Make sure we've already synched disks */
	    {
	      if(systab->noswap==cb_FALSE)
		TransferDisk(systab->fd_serial, cmdline);
	      else
		{
		  XmitMsg(port, host, "%s", "ERROR: NOSWAP=T Cannot transfer files until a +SWAP command is issued at the Caliban console.");
		}
	    }
	  else
	    {
	      XmitMsg(port, host, "%s", "ERROR: Disks not synched");
	    }
	}
    }
  else if (strcmp(argbuf, "REQ")==0) /* A request for valid mount points we have */
    {
      GetArg(cmdline, 3, argbuf);
      if(strcmp(argbuf, "MOUNT")==0)
	ReqMount(systab->fd_serial, host);
    }
  else if (strcmp(argbuf, "LASTFILE")==0)
    {
      XmitMsg(port, host, "STATUS: LASTFILE=%s", systab->lastfile);
    }
  else if (strcmp(argbuf, "PATH")==0)
    {
      XmitMsg(port, host, "STATUS: PATH=%s", mounttab->mount[mounttab->current]);
    }
  else if (strcmp(argbuf, "OFFLINE")==0)
    {
    }
  else if (strcmp(argbuf, "ERROR:")==0) /* Someone is reporting an error */
    {
    }
  else if (strcmp(argbuf, "FATAL:")==0) /* Someone is reporting a fatal error */
    {
    }
  else if ((strcmp(argbuf, "CBSTATUS")==0) || (strcmp(argbuf, "STATUS")==0) )
    {
      CBStatus(systab->fd_serial, host); /* Someone is requesting a status */
    }
  else if (strcmp(argbuf, "STATUS:")==0) /* Someone is reporting a status */
    {
      Status(host, cmdline);
    }
  else if (strcmp(argbuf, "VERSION")==0)
    {
      XmitMsg(port, host, "STATUS: VERSION=%s", VERSION);
    }
  else if (strcmp(argbuf, "")==0)
    {
    }
  else
    {
      /* If port=0, the command came from the keyboard, so we grab the old command from systab->oldcmdline */
      /* but if the command came from elsewhere, the old one is stored in systab->oldinbuf                 */
      if(port==0) 
	XmitMsg(port, host, "ERROR: Unknown command '%s'", systab->oldcmdline); /* Stupid local user       */
      else
	XmitMsg(port, host, "ERROR: Unknown command '%s'", systab->oldinbuf);   /* Stupid remote user      */
    }
  cmdline[0] = NUL;
}



/* Main Routine                                                            */
/* Purpose: Main Caliban routine - handles i/o mulitplexing and dispatch   */
/* Requires: nothing                                                       */

#include "Caliban.h"     /* Caliban header file                            */
#include <signal.h>      /* Used for trapping ctrl-c                       */

struct st st;            /* System table structure */
struct mt mt;            /* Mount table structure  */
struct dt dt;            /* Disk table structure   */

struct st *systab=&st;   /*                                                */
struct mt *mounttab=&mt; /* Set up pointers to tables to be used globally  */
struct dt *disktab=&dt;  /*                                                */

int main()
{
  int lcv;               /* Loop control variable                          */
  int done=0;            /* Completion flag                                */
  int charsin=0;         /* Number of characters read in                   */
  int cmdcnt=0;          /* Keyboard command array index                   */
  int xpos=0, ypos=0;    /* Screen coordinates (curses.h)                  */
  int disknum=0;         /* Disk table index                               */
  int numlines=0;        /* Used for displaying n log entries on screen    */
  int numvalid=0;        /* Number of valid disks in the Disk Table        */
  char numlinesstr[SHORT_STR_SIZE]; /*                                     */
  char logcmd[MED_STR_SIZE];   /*                                          */
  char confirm;                /* Exit confirmation                        */
  char host[SHORT_STR_SIZE];   /* Name of destination host                 */
  char argbuf[MED_STR_SIZE];   /* Used during parsing of command lines     */
  char inbuf[BUF_SIZE];        /* Buffer for incoming commands             */
  char outbuf[BUF_SIZE];       /* Buffer for outgoing messages             */
  char cmdline[BUF_SIZE];      /* Buffer for keyboard commands             */
  fd_set readfds;              /* File descriptor set for multiplexing i/o */      
  FILE *logpipe;               /* Handle to pipe for log display command   */

  signal(SIGINT, UserCancel);  /* Trap user interrupt signal               */

  initscr(); /* Initialize curses library */
  cbreak();  /* Put tty into cbreak mode (no buffering) */
  noecho();  /* Put tty into no echo mode so characters aren't displayed twice */

  /* Initialize system table entries */

  systab->fd_keyboard = 0; /* Set standard in */
  systab->cols = COLS; /* Record number of window columns reported by curses initscr routine */
  systab->output = newwin(LINES-1, COLS, 0, 0); /* Create output window */
  systab->input = newwin(1, COLS, LINES-1, 0);  /* Create one line input window */
  systab->doarchive = systab->dodisplay = systab->doautolog = systab->addfits = cb_FALSE;
  systab->olddoarchive = systab->olddodisplay = systab->olddoautolog = systab->oldaddfits = cb_FALSE;
  sprintf(systab->lastfile, "none");
  systab->headwritten = 0;
  systab->datawritten = 0;

  scrollok(systab->output, TRUE); /* Enable window scrolling */
  scrollok(systab->input, TRUE);
  wrefresh(systab->output);

  ParseIniFile(); /* Load global tables with values from initialization file */

  Prompt(); /* Clear the command line */

  /* Attempt to open the log file, or create one if it does not already exist */

  if((systab->logfd=open(systab->logfilename, O_WRONLY))==cb_ERROR)
    {
      if((systab->logfd=creat(systab->logfilename, 0664))==cb_ERROR)
	ConsoleMsg("ERROR: Unable to create log file--%s\n", sys_errlist[errno]);
    }

  lseek(systab->logfd, 0L, SEEK_END); /* Position the log file pointer to the EOF */

  LogMsg("#### Caliban started normally ####");

  /* Attempt to get a handle to the serial port */

  if((systab->fd_serial=InitSerial())==SYSERR) {
    ConsoleMsg("ERROR: Connect to serial port failed--%s\n", sys_errlist[errno]);
  } else {
    ConsoleMsg("Connected to serial port %s\n", systab->serialdev);
  }

  if(mounttab->nummounts==0) /* In the event no valid mount points are discovered in the       */
    {                        /* ini file, set the current mount point to reflect not available */
      sprintf(mounttab->mount[0], "n/a");
      ConsoleMsg("%s\n", "ERROR: No valid mount points specified");
    }

  mounttab->current = 0;     /* By default, the first entry in the mount table becomes current */

  /* Initialize the global disk table */

  if((numvalid=InitDiskTable())==0)
    ConsoleMsg("%s\n", "ERROR: No valid spool device(s) detected");

  if (numvalid < disktab->numdisks)
    ConsoleMsg("%s\n", "WARNING: Caliban.ini contains invalid spool device(s)");

  /* Request disk synchronization */

  XmitMsg(systab->fd_serial, systab->serialhost, "%s", "REQ INITDISK");

  /* Main i/o multiplexing loop--multiplexes between serial and keyboard input */
  /* Uses select wait mechanism to avoid busy waiting and wasting CPU cycles.  */

  do
    {
      /* Set up file descriptor set which is used to determine which port */
      /* became active while sleeping on the select semaphore             */
      FD_ZERO(&readfds);

      if(systab->fd_serial!=0) /* Don't include serial if we couldn't get a handle */
	FD_SET(systab->fd_serial, &readfds);
      FD_SET(systab->fd_keyboard, &readfds);

      /* Go to sleep, waking up when there is something waiting on a port */

      select(systab->fd_serial+1, &readfds, NULL, NULL, NULL);

      /* Now determine which port had some input by checking the fd set */

      if (FD_ISSET(systab->fd_keyboard, &readfds)) /* Keyboard input */
	{
	  switch (cmdline[cmdcnt]=fgetc(stdin)) /* Grab the first character */
	    {
	    case 27: /* Escape character causes the command line to be cleared */
	      Prompt();
	      cmdcnt = 0; /* Resets the index to zero */
	      cmdline[0] = NUL; /* Clear the buffer */
	      break;
	    case '\b': /* A backspace or a delete */
	    case 127:
	      getyx(systab->input, ypos, xpos);
	      if(xpos>strlen(systab->localhost)+2) /* No need to backspace if at beginning */
		{
		  cmdline[cmdcnt] = NUL; /* Clear out current character */
		  cmdcnt--; /* Decrement the index */
		  getyx(systab->input, ypos, xpos); /* Figure out where we are on screen */
		  wmove(systab->input, 0, xpos-1);  /* Move us back one */
		  wprintw(systab->input, " ");      /* Blank out the character on screen */
		  wmove(systab->input, 0, xpos-1);  /* Move us back one */
		  wrefresh(systab->input);          /* Redraw the screen */
		}
	      break;
	    case 16:  /* Ctrl-P -- Recall old command */

	      /* We store the most recent command in a buffer in the system table, */
	      /* so this amounts to blanking out the command line, recalling the   */
	      /* old command, positioning ourselves at the end both in terms of    */
	      /* the index and the screen position, and redrawing the screen       */

	      Prompt();
	      strcpy(cmdline, systab->oldcmdline);
	      cmdcnt = strlen(cmdline);
	      wprintw(systab->input, cmdline);
	      wrefresh(systab->input);
	      break;
	    case '\n': /* Hit enter */
	      /* Now come the fun part.  Once a carriage return has been received, */
	      /* we need to check the validity of the entire command and then call */
	      /* the appropriate function or indicate an error                     */

	      /* First some general housekeeping...take the command from the input */
	      /* line and move it up to the output area of the screen and clear    */
	      /* the command input line                                            */

	      cmdline[cmdcnt] = NUL;
	      strcpy(systab->oldcmdline, cmdline);
	      wprintw(systab->output, "%% %s\n", cmdline);
	      wrefresh(systab->output);
	      Prompt();
	      cmdcnt = 0;

	      UpperCase(cmdline); /* Makes comparisons much easier */

	      /* Now we grab the first argument, which is everything up until the  */
	      /* first space.  We assume this is the first word of a given command */

	      GetArg(cmdline, 1, argbuf);

	      /* QUIT or Q will result in setting the done flag which exits this   */
	      /* whole loop (first confirm that the user didn't fat-finger a key   */

	      if(strcmp(argbuf, "QUIT")==0 || strcmp(argbuf, "Q")==0)
		{
		  wprintw(systab->input, "Are you sure? (Y/N)");
		  wrefresh(systab->input);
		  confirm=getchar();
		  if(confirm=='Y' || confirm=='y')
		    done=1;
		  else
		    Prompt();
		}
	      
	      /* HELP or ? displays a list of the available commands which can be  */
	      /* entered at the keyboard--note that this does not represent the    */
	      /* full list of supported commands                                   */
	      
	      else if(strcmp(argbuf, "?")==0 || strcmp(argbuf, "HELP")==0)
		{
		  wprintw(systab->output, "Command List:   HELP or ?       -This list\n");
		  wprintw(systab->output, "                QUIT or Q       -End program\n");
		  wprintw(systab->output, "                CLEAR or C      -Clear the screen\n");
		  wprintw(systab->output, "                CHKSTATUS or CS -Status report\n");
		  wprintw(systab->output, "                LOG n           -Prints out last n lines of the log file\n");
		  wprintw(systab->output, "                +ARCHIVE        -Enables archiving\n");
		  wprintw(systab->output, "                -ARCHIVE        -Disables archiving\n");
		  wprintw(systab->output, "                ARCHIVE         -Tells if archiving is currently enabled\n");
		  wprintw(systab->output, "                +/-AUTOLOG      -Enable/Disable/Show autologging status\n");
		  wprintw(systab->output, "                +/-DISPLAY      -Enable/Disable/Show autodisplay status\n");
		  wprintw(systab->output, "                +/-ADDFITS      -Enable/Disable/Show fits extension status\n");
		  wprintw(systab->output, "                RESTORE         -Restore system flags to default values\n");
		  wprintw(systab->output, "                {Ctrl-P}        -Recall last command\n");
		  wprintw(systab->output, "                >{host} {msg}   -Sends message {msg} to hostname {host}\n");
		  wprintw(systab->output, "                {ESC}           -Clears the current input line\n");
		  wprintw(systab->output, "                DBGREAD n       -Reads an image from disk n (n>=0) without\n");
		  wprintw(systab->output, "                                 having synched disks\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "+ARCHIVE")==0)
		{
		  systab->doarchive = cb_TRUE;
		  wprintw(systab->output, "Archiving is now enabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "-ARCHIVE")==0)
		{
		  systab->doarchive = cb_FALSE;
		  wprintw(systab->output, "Archiving is now disabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "ARCHIVE")==0)
		{
		  if(systab->doarchive == cb_TRUE)
		    wprintw(systab->output, "Archiving is currently enabled\n");
		  else
		    wprintw(systab->output, "Archiving is currently disabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "+AUTOLOG")==0)
		{
		  systab->doautolog = cb_TRUE;
		  wprintw(systab->output, "Auto logging is now enabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "-AUTOLOG")==0)
		{
		  systab->doautolog = cb_FALSE;
		  wprintw(systab->output, "Auto logging is now disabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "AUTOLOG")==0)
		{
		  if(systab->doautolog == cb_TRUE)
		    wprintw(systab->output, "Autologging is currently enabled\n");
		  else
		    wprintw(systab->output, "Autologging is currently disabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "+DISPLAY")==0)
		{
		  systab->dodisplay = cb_TRUE;
		  wprintw(systab->output, "Auto display is now enabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "-DISPLAY")==0)
		{
		  systab->dodisplay = cb_FALSE;
		  wprintw(systab->output, "Auto display is now disabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "DISPLAY")==0)
		{
		  if(systab->dodisplay == cb_TRUE)
		    wprintw(systab->output, "Auto display is currently enabled\n");
		  else
		    wprintw(systab->output, "Auto display is currently disabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "+ADDFITS")==0)
		{
		  systab->addfits = cb_TRUE;
		  wprintw(systab->output, "Adding .fits extension is now enabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "-ADDFITS")==0)
		{
		  systab->addfits = cb_FALSE;
		  wprintw(systab->output, "Adding .fits extension is now disabled\n");
		  wrefresh(systab->output);
		  Prompt();
		}
	      else if(strcmp(argbuf, "ADDFITS")==0)
		{
		  if(systab->addfits == cb_TRUE)
		    wprintw(systab->output, "Adding .fits extension is currently enabled\n");
		  else
		    wprintw(systab->output, "Adding .fits extension is currently disabled\n");
		  wrefresh(systab->output);
		  Prompt();
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
		  wprintw(systab->output, "System variables restored to default values\n");
		  wrefresh(systab->output);
		  Prompt();
		}

	      /* We have the ability to display the last n lines of the log file on screen */
	      /* n defaults to 10                                                          */

	      else if(strcmp(argbuf, "LOG")==0)
		{
		  GetArg(cmdline, 2, numlinesstr);
		  numlines=atoi(numlinesstr);
		  if(numlines<1)
		    numlines = 10;
		  
		  /* We open a pipe which submits a command to the shell */

		  sprintf(logcmd, "tail -%d %s", numlines, systab->logfilename);
		  logpipe = popen(logcmd, "r");
		  
		  /* Then we read the resulting output from the pipe */

		  while(fgets(outbuf, sizeof(outbuf), logpipe) != NULL)
		      wprintw(systab->output, outbuf);
		  wrefresh(systab->output);

		  Prompt();

		  if(logpipe!=0)
		    pclose(logpipe);
		}
	      
	      /* This causes a status table to be displayed on screen */

	      else if(strcmp(argbuf, "CHKSTATUS")==0 || strcmp(argbuf, "CS")==0)
		{
		  wprintw(systab->output, "Status Report for %s:\n", systab->localhost);
		  wprintw(systab->output, "                Version = %s\n", VERSION);
		  wprintw(systab->output, "                Serial Host = %s\n", systab->serialhost);
		  wprintw(systab->output, "                Serial Port = %s\n", systab->serialdev);
		  wprintw(systab->output, "                Logfile = %s\n", systab->logfilename);
		  wprintw(systab->output, "                Block Size = %d\n", BLOCK_SIZE);
		  wprintw(systab->output, "                Last File Written = %s\n", systab->lastfile);
		  wprintw(systab->output, "                                    Header bytes = %d\n", systab->headwritten);
		  wprintw(systab->output, "                                    Data bytes   = %d\n", systab->datawritten);

		  if(systab->dodisplay == cb_TRUE)
		    wprintw(systab->output, "                Auto display enabled\n");
		  else
		    wprintw(systab->output, "                Auto display disabled\n");
		  if(systab->doarchive == cb_TRUE)
		    wprintw(systab->output, "                Archiving enabled\n");
		  else
		    wprintw(systab->output, "                Archiving disabled\n");
		  if(systab->doautolog == cb_TRUE)
		    wprintw(systab->output, "                Auto logging enabled\n");
		  else
		    wprintw(systab->output, "                Auto logging disabled\n");
		  if(systab->addfits == cb_TRUE)
		    wprintw(systab->output, "                Adding .fits extension enabled\n");
		  else
		    wprintw(systab->output, "                Adding .fits extension disabled\n");

		  wprintw(systab->output, "                Current Mount Point = %s\n\n", mounttab->mount[mounttab->current]);
		  wprintw(systab->output, "                Disk Table:\n\n");
		  wprintw(systab->output, "                     Disk Name         Alias   Syncd  Valid  Device Name\n");
		  wprintw(systab->output, "                --------------------  -------  -----  -----  -----------\n");
		  for(lcv=0;lcv<disktab->numdisks;lcv++)
		    wprintw(systab->output, "                %20s  %6s     %c      %c    %s\n", disktab->disk[lcv], disktab->alias[lcv], (disktab->use[lcv]==1) ? 'Y' : 'N', (disktab->valid[lcv]==1) ? 'Y' : 'N', disktab->device[lcv]);
		  wprintw(systab->output, "\n");
		  wprintw(systab->output, "                Mount Table:\n\n");
		  wprintw(systab->output, "                  Mount Point Name\n");
		  wprintw(systab->output, "                --------------------\n");
		  for(lcv=0;lcv<mounttab->nummounts;lcv++)
		    wprintw(systab->output, "                %s\n", mounttab->mount[lcv]);
		  wrefresh(systab->output);
		  Prompt();
		}
	      
	      /* This allows us to send a message manually to any other host on the system.  Currently, it relies */
	      /* on the downstream serial host to forward the message.  This allows us even to forward a message  */
	      /* back to ourselves, which is how we get around certain commands not being available from the      */
	      /* command line                                                                                     */    

	      else if(cmdline[0]=='>')
		{
		  sprintf(outbuf, "%s%s\r", systab->localhost, cmdline);
		  write(systab->fd_serial, outbuf, strlen(outbuf));
		  if(systab->verbose == cb_TRUE)
		    {
		      sprintf(outbuf, "%s%s", systab->localhost, cmdline);
		      if(outbuf[strlen(outbuf)]=='\n')
			ConsoleMsg("%s", outbuf);
		      else
			ConsoleMsg("OUT: %s\n", outbuf);
		    }
		}
	      else if(cmdline[0]==NUL) /* Null command--do nothing */
		{
		  continue;
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
		  
		  GetArg(cmdline, 2, outbuf);

		  disknum=atoi(outbuf);
		    
		  if((disknum > disktab->numdisks) || (disknum < 0) || (disktab->valid[disknum]!=1))
		    {
		      wprintw(systab->output, "Invalid device number\n");
		      wrefresh(systab->output);
		      Prompt();
		    }
		  else
		    {
		      /* Maxcards--the maximum number of FITS header cards would normally have been */
		      /* determined at disk synch time, so we have to simulate it                   */

		      systab->maxcards = systab->headlng*BLOCK_SIZE/80;

		      if(GetFITS(systab->fd_serial, systab->serialhost, disktab->device[disknum], "DEBUG", 1)<1)
			{
			  sprintf(outbuf, "ERROR: Unable to transfer file\n");
			  ConsoleMsg("%s\n", outbuf);
			}
		    }
		}
	      else
		{
		  wprintw(systab->output, "Unknown command\n"); /* Stupid user */
		  wrefresh(systab->output);
		  Prompt();
		}
	      cmdline[0] = NUL;
	      break;
	    default: /* The default behavior is just to copy the incoming character into the buffer and proceed */
	      if(cmdcnt < systab->cols-6)
		{
		  if(cmdline[cmdcnt]=='\t') /* Convert tabs to spaces */
		    cmdline[cmdcnt]=' ';

		  wprintw(systab->input, "%c", cmdline[cmdcnt]);
		  wrefresh(systab->input);
		  cmdcnt++;
		}
	      else
		wprintw(systab->input, "\a"); /* End of the line has been reached, so beep */
	    }
	}
      
      /* Second branch of the multiplexing.  Input is waiting on the serial port */

      else if (FD_ISSET(systab->fd_serial, &readfds))
	{
	  BZero(inbuf, sizeof(inbuf));
	  charsin = read(systab->fd_serial, inbuf, sizeof(inbuf));
	  inbuf[charsin] = NUL;

	  /* We store a copy of the most recent input in the system table.  This is because */
	  /* we then uppercase the characters, and in some cases we will need the original  */
	  /* case back for things like file names which are case-sensitive in UNIX          */
	  
	  strcpy(systab->oldinbuf, inbuf);
	  
	  UpperCase(inbuf);

	  /* We have a verbose switch which determines whether serial input is echoed       */

	  if(systab->verbose == cb_TRUE)
	    {
	      ConsoleMsg("IN:  %s", inbuf);
	    }

	  /* The first argument is assumed to contain the host name */

	  GetArg(inbuf, 1, host);


	  /* If the message not is addressed to us or all, ignore it */
	  
	  if(strstr(host, CatStr(outbuf, systab->localhost, "")) || strstr(host, ">AL"))
	    {
	      host[2] = NUL; /* Chop off the destination portion of the address string */

	      GetArg(inbuf, 2, argbuf);

	      /* The second argument is assumed to be the first word of a valid command */

	      if (strcmp(argbuf, "PING")==0) /* Call the Ping handler routine */
		{
		  Ping(systab->fd_serial, host);
		}
	      else if (strcmp(argbuf, "PONG")==0) /* Call the Pong handler routine */
	      {
		Pong(host);
	      }
	      else if (strcmp(argbuf, "INIT")==0) /* Disk synchronization command */
		{
		  GetArg(inbuf, 3, argbuf);
		  if(strcmp(argbuf, "DISK")==0)
		    if(strcmp(host, systab->serialhost)==0)
		      InitDisk(systab->fd_serial, host, inbuf); /* Begin disk synchronization */
		}
	      else if (strcmp(argbuf, "USE")==0) /* Agreement on valid disk devices and names */
		{
		  GetArg(inbuf, 3, argbuf);
		  if(strstr(argbuf, "DISK")) {
		    UseDisk(systab->fd_serial, host, inbuf);
		  }
		  else if(strcmp(argbuf, "MOUNT")==0) { /* Agreement on valid mount points */
		    UseMount(systab->fd_serial, host, inbuf);
		  }
		}
	      else if (strcmp(argbuf, "+ARCHIVE")==0)
		{
		  systab->doarchive = cb_TRUE;
		  XmitMsg(systab->fd_serial, host, "%s", "STATUS: ARCHIVE=T");
		}
	      else if (strcmp(argbuf, "-ARCHIVE")==0)
		{
		  systab->doarchive = cb_FALSE;
		  XmitMsg(systab->fd_serial, host, "%s", "STATUS: ARCHIVE=F");
		}
	      else if (strcmp(argbuf, "ARCHIVE")==0)
		{
		  if(systab->doarchive == cb_TRUE)
		    XmitMsg(systab->fd_serial, host, "%s", "STATUS: ARCHIVE=T");
		  else
		    XmitMsg(systab->fd_serial, host, "%s", "STATUS: ARCHIVE=F");
		}
	      else if (strcmp(argbuf, "+DISPLAY")==0)
		{
		  systab->dodisplay = cb_TRUE;
		  XmitMsg(systab->fd_serial, host, "%s", "STATUS: DISPLAY=T");
		}
	      else if (strcmp(argbuf, "-DISPLAY")==0)
		{
		  systab->dodisplay = cb_FALSE;
		  XmitMsg(systab->fd_serial, host, "%s", "STATUS: DISPLAY=F");
		}
	      else if (strcmp(argbuf, "DISPLAY")==0)
		{
		  if(systab->dodisplay == cb_TRUE)
		    XmitMsg(systab->fd_serial, host, "%s", "STATUS: DISPLAY=T");
		  else
		    XmitMsg(systab->fd_serial, host, "%s", "STATUS: DISPLAY=F");
		}
	      else if (strcmp(argbuf, "+AUTOLOG")==0)
		{
		  systab->doautolog = cb_TRUE;
		  XmitMsg(systab->fd_serial, host, "%s", "STATUS: AUTOLOG=T");
		}
	      else if (strcmp(argbuf, "-AUTOLOG")==0)
		{
		  systab->doautolog = cb_FALSE;
		  XmitMsg(systab->fd_serial, host, "%s", "STATUS: AUTOLOG=F");
		}
	      else if (strcmp(argbuf, "AUTOLOG")==0)
		{
		  if(systab->doautolog == cb_TRUE)
		    XmitMsg(systab->fd_serial, host, "%s", "STATUS: AUTOLOG=T");
		  else
		    XmitMsg(systab->fd_serial, host, "%s", "STATUS: AUTOLOG=F");
		}
	      else if (strcmp(argbuf, "+ADDFITS")==0)
		{
		  systab->addfits = cb_TRUE;
		  XmitMsg(systab->fd_serial, host, "%s", "STATUS: ADDFITS=T");
		}
	      else if (strcmp(argbuf, "-ADDFITS")==0)
		{
		  systab->addfits = cb_FALSE;
		  XmitMsg(systab->fd_serial, host, "%s", "STATUS: ADDFITS=F");
		}
	      else if (strcmp(argbuf, "ADDFITS")==0)
		{
		  if(systab->addfits == cb_TRUE)
		    XmitMsg(systab->fd_serial, host, "%s", "STATUS: ADDFITS=T");
		  else
		    XmitMsg(systab->fd_serial, host, "%s", "STATUS: ADDFITS=F");
		}
	      else if (strcmp(argbuf, "RESTORE")==0)
		{
		  systab->doarchive = systab->olddoarchive;
		  systab->dodisplay = systab->olddodisplay;
		  systab->doautolog = systab->olddoautolog;
		  systab->addfits = systab->oldaddfits;
		  XmitMsg(systab->fd_serial, "%s", "STATUS: System variables restored to default values");
		}
	      else if (strcmp(argbuf, "ACK")==0) /* Valid disk synch completion confirmation */
		{
		  GetArg(inbuf, 3, argbuf);
		  if(strcmp(argbuf, "DISK")==0)
		    AckDisk(systab->fd_serial, host);
		}
	      else if (strcmp(argbuf, "TRANSFER")==0) /* There's at least one file out there for us */
		{
		  GetArg(inbuf, 3, argbuf);
		  if(strstr(argbuf, "DISK"))
		    {
		      if(disktab->ackdisk) /* Make sure we've already synched disks */
			{
			  TransferDisk(systab->fd_serial, inbuf);
			}
		      else
			{
			  XmitMsg(systab->fd_serial, host, "%s", "ERROR: Disks not synched");
			}
		    }
		}
	      else if (strcmp(argbuf, "REQ")==0) /* A request for valid mount points we have */
		{
		  GetArg(inbuf, 3, argbuf);
		  if(strcmp(argbuf, "MOUNT")==0)
		    ReqMount(systab->fd_serial, host);
		}
	      else if (strcmp(argbuf, "LASTFILE")==0)
		{
		  XmitMsg(systab->fd_serial, host, "STATUS: LASTFILE=%s", systab->lastfile);
		}
	      else if (strcmp(argbuf, "PATH")==0)
		{
		  XmitMsg(systab->fd_serial, host, "STATUS: PATH=%s", mounttab->mount[mounttab->current]);
		}
	      else if (strcmp(argbuf, "QUIT")==0 || strcmp(argbuf, "Q")==0) /* Notice there's no confirmation */
		{
		  done=1;
 		}
	      else if (strcmp(argbuf, "OFFLINE")==0)
		{
		  continue;
		}
	      else if (strcmp(argbuf, "ERROR:")==0) /* Someone is reporting an error */
		{
		  continue;
		}
	      else if (strcmp(argbuf, "CBSTATUS")==0)
		{
		  CBStatus(systab->fd_serial, host); /* Someone is requesting a status */
		}
	      else if (strcmp(argbuf, "STATUS:")==0) /* Someone is reporting a status */
		{
		  Status(host, inbuf);
		}
	      else if (strcmp(argbuf, "VERSION")==0)
		{
		  XmitMsg(systab->fd_serial, host, "STATUS: VERSION=%s", VERSION);
		}
	      else
		{
		  XmitMsg(systab->fd_serial, host, "%s", "ERROR: Unknown command"); /* Out of possibilities */
		}
	    }
	}
    } while (!(done)); /* Exit once the done flag is set */

  /* We're about to exit, so we need to let the downstream host know that the mount points */
  /* we'd agreed on are no longer available, so we send UNMOUNT commands for each          */

  for(lcv=0;lcv<mounttab->nummounts;lcv++)
      XmitMsg(systab->fd_serial, systab->serialhost, "UNMOUNT %s", mounttab->mount[lcv]);

  /* Now we report that we're going off line */

  XmitMsg(systab->fd_serial, systab->serialhost, "%s", "OFFLINE");

  LogMsg("#### Caliban exited normally ####");

  if(systab->fd_serial!=0)
    close(systab->fd_serial);

  if(systab->logfd!=0)
    close(systab->logfd);

  endwin(); /* Kill curses */

  exit(OK);
}

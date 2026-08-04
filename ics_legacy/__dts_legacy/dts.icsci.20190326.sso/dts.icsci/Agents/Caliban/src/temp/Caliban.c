/* Main Routine                                                            */
/* Purpose: Main Caliban routine - handles i/o mulitplexing and dispatch   */
/* Requires: nothing                                                       */

#include "Caliban.h"     /* Caliban header file                            */

struct st st;            /* System table structure */
struct mt mt;            /* Mount table structure  */
struct dt dt;            /* Disk table structure   */

struct st *systab=&st;   /*                                                */
struct mt *mounttab=&mt; /* Set up pointers to tables to be used globally  */
struct dt *disktab=&dt;  /*                                                */

int main()
{
  int lcv;                  /* Loop control variable                          */
  int done=0;               /* Completion flag                                */
  int charsin=0;            /* Number of characters read in                   */
  int cmdcnt=0;             /* Keyboard command array index                   */
  int xpos=0, ypos=0;       /* Screen coordinates (curses.h)                  */

  char confirm;                /* Exit confirmation                           */
  char host[SHORT_STR_SIZE];   /* Name of destination host                    */
  char cmdline[BUF_SIZE];      /* Buffer for keyboard commands                */
  char argbuf[BUF_SIZE];       /* Buffer for processing arguments             */
  fd_set readfds;              /* File descriptor set for multiplexing i/o    */      

  InitCB();

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
	  /* Grab the first character */
	  switch (cmdline[cmdcnt]=fgetc(stdin))
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
	    case '\n': /* Hit enter  */
	    case '\r': /* Hit return */
	      /* Now comes the fun part.  Once a carriage return has been received, */
	      /* we need to check the validity of the entire command and then call  */
	      /* the appropriate function or indicate an error                      */

	      cmdline[cmdcnt] = NUL;
	      strcpy(systab->oldcmdline, cmdline); /* Save it for later recalling with Ctrl-P */

	      cmdcnt = 0; /* Reset the keyboard input character counter */

	      ConsoleMsg("%% %s", cmdline);

	      sprintf(argbuf, "CB>CB %s", cmdline);

	      DoCommand(argbuf); /* Process the damn command */
	      
	      Prompt();

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
	  BZero(cmdline, sizeof(cmdline));
	  charsin = read(systab->fd_serial, cmdline, sizeof(cmdline));
	  cmdline[charsin] = NUL;

	  /* We store a copy of the most recent input in the system table.  This is because */
	  /* we then uppercase the characters, and in some cases we will need the original  */
	  /* case back for things like file names which are case-sensitive in UNIX          */
	  
	  strcpy(systab->oldinbuf, cmdline);
	  
	  DoCommand(cmdline); /* Process the damn command */
	}
    } while (!(systab->done)); /* Exit once the done flag is set */
  
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



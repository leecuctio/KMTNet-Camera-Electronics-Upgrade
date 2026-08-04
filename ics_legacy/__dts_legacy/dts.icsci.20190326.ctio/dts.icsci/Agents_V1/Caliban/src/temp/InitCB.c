#include "Caliban.h"
#include <signal.h>

void InitCB() {
  int lcv; /* Loop control variable */

  signal(SIGINT, UserCancel);  /* Trap user interrupt signal                  */

  /*************************************************/
  /* Initialize the console (curses library stuff) */
  /*************************************************/

  initscr(); /* Initialize curses library */
  cbreak();  /* Put tty into cbreak mode (no buffering) */
  noecho();  /* Put tty into no echo mode so characters aren't displayed twice */

  /***************************************************/
  /* Initialize system table entries -- clean livin' */
  /***************************************************/

  systab->done = cb_FALSE;
  systab->fd_keyboard = 0;  /* Set standard in */
  systab->cols = COLS;      /* Record number of window columns reported by curses initscr routine */
  systab->debug = cb_FALSE; /* By default we do not operate in debug mode */

  systab->output = newwin(LINES-1, COLS, 0, 0); /* Create output window */

  systab->input = newwin(1, COLS, LINES-1, 0);  /* Create one line input window */
  systab->doarchive = systab->dodisplay = systab->doautolog = systab->addfits = cb_FALSE;
  systab->olddoarchive = systab->olddodisplay = systab->olddoautolog = systab->oldaddfits = cb_FALSE;

  bzero(systab->serialdev, sizeof(systab->serialdev));
  bzero(systab->serialhost, sizeof(systab->serialhost));
  bzero(systab->localhost, sizeof(systab->localhost));
  bzero(systab->logfilename, sizeof(systab->logfilename));
  bzero(systab->oldcmdline, sizeof(systab->oldcmdline));
  bzero(systab->oldinbuf, sizeof(systab->oldinbuf));
  bzero(systab->lastfile, sizeof(systab->lastfile));

  sprintf(systab->lastfile, "none");

  for(lcv=0; lcv<MAXDISKS; lcv++)
    {
      bzero(disktab->disk[lcv], sizeof(disktab->disk[lcv]));
      bzero(disktab->alias[lcv], sizeof(disktab->alias[lcv]));
      bzero(disktab->device[lcv], sizeof(disktab->device[lcv]));
    }

  for(lcv=0; lcv<SHORT_STR_SIZE; lcv++)
    bzero(mounttab->mount[lcv], sizeof(mounttab->mount[lcv]));

  systab->headwritten = 0;
  systab->datawritten = 0;

  scrollok(systab->output, TRUE); /* Enable window scrolling */
  scrollok(systab->input, TRUE);
  wrefresh(systab->output);

  /*********************************/
  /* Parse the initialization file */
  /*********************************/

  ParseIniFile(); /* Load global tables with values from initialization file  */

  /************************************/
  /* Logging mechanism initialization */
  /************************************/

  /* Attempt to open the log file, or create one if it does not already exist */

  if((systab->logfd=open(systab->logfilename, O_WRONLY))==cb_ERROR)
    {
      if((systab->logfd=creat(systab->logfilename, 0666))==cb_ERROR)
	ConsoleMsg("ERROR: Unable to create log file--%s", ERRORSTR);
    }

  lseek(systab->logfd, 0L, SEEK_END); /* Position the log file pointer to EOF */

  LogMsg("#### Caliban started normally ####");

  /******************************/
  /* Serial port initialization */
  /******************************/

  /* Attempt to get a handle to the serial port */

  if((systab->fd_serial=InitSerial())==SYSERR) {
    ConsoleMsg("ERROR: Connect to serial port failed--%s", ERRORSTR);
  } else {
    ConsoleMsg("Connected to serial port %s", systab->serialdev);
  }

  /******************************/
  /* Mount table initialization */
  /******************************/

  if(mounttab->nummounts==0) /* In the event no valid mount points are discovered in the       */
    {                        /* ini file, set the current mount point to reflect not available */
      sprintf(mounttab->mount[0], "n/a");
      ConsoleMsg("%s", "ERROR: No valid mount points specified");
    }

  mounttab->current = 0;     /* By default, the first entry in the mount table becomes current */

  /*****************************/
  /* Disk table initialization */
  /*****************************/

  if(InitDiskTable()==0)
    ConsoleMsg("%s", "ERROR: No valid spool device(s) detected");

  if (disktab->numvalid < disktab->numdisks)
    ConsoleMsg("%s", "WARNING: Caliban.ini contains invalid spool device(s)");
}

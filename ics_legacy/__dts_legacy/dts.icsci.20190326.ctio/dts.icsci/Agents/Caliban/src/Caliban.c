/*
 * caliban - Interactive SCSI-disk data transfer agent
 *
 * Usage: caliban [-fINIfile]
 *
 * where:
 *    -fINIfile = use "INIfile" as the server initialization file 
 *                 instead of the default (hardwired in Caliban.h)
 *
 * Description: 
 *
 *   Caliban is an autonomous "agent" that handles image data-transfer
 *   between the data-taking system and a Unix workstation.  The data
 *   transport system is a pair of shared SCSI disks used in "target
 *   mode".  Images are placed on one of the disks (the "inbox"), by the
 *   "disk host" process in the data-tking system, and Caliban is
 *   signaled that an image is ready for pickup.  The inbox disk then
 *   becomes an "outbox", allowing the data-taking system to
 *   concurrently write images to the other disk while Caliban is
 *   reading.  Once Caliban is done, it signals completion to the disk
 *   host, which then swaps the in- and outbox disks and begins again.
 *
 * Notes:
 *   Uses select() for multiplexing.  No multithreading at the present
 *   time.
 *
 *   With version 3.1 we are using the GNU readline and history utilties
 *   for the cli.  Very nice.
 *
 * History:
 *   Caliban was originally written by Brian Hartung, an OSU CIS student
 *   who worked with us in the Instrument Lab from late 1996 until 1998.
 *   Jerry Mason developed the shared SCSI disk transport system, writing
 *   the DOS-side code and working out the procedures.  Brian wrote
 *   the Unix-side "caliban" code, adding low-level SCSI (sg) drivers
 *   in 1997.
 *
 *   On Brian's departure, Rick Pogge tookover maintenance of Caliban,
 *   and in January 2003 revived the Linux version for use with our
 *   prototype next-generation Linux workstation system.  He added the
 *   new cli interface, and the socket interface to the ISIS server.
 *
 *   See the 00CHANGES file for the Modification history prior to
 *   (and including) January 2003.
 *
 * Modification History:
 *   2003 Jan 17: resurrected Caliban, modified for the ISIS system. [rwp]
 *
 ***************************************************************************/

#include "Caliban.h"     

/* prototypes only used by main() */

void KbdHandler(char *); /* readline callback for keyboard input handling  */
void PrintUsage(void);   /* print usage message on command-line errors     */

/* global tables */

struct st st;            /* System table structure */
struct mt mt;            /* Mount table structure  */
struct dt dt;            /* Disk table structure   */

struct st *systab=&st;   /*                                                */
struct mt *mounttab=&mt; /* Set up pointers to tables to be used globally  */
struct dt *disktab=&dt;  /*                                                */

/* The Main Event... */

static int sel_wid;

static char msgbuf[BUF_SIZE];  /* Buffer for commands */

int 
main(int argc, char *argv[]) 
{
  int lcv;                  /* Loop control variable                          */
  int done=0;               /* Completion flag                                */
  int charsin=0;            /* Number of characters read in                   */
  int c;

  char host[SHORT_STR_SIZE];   /* Name of destination host                    */
  char argbuf[BUF_SIZE];       /* Buffer for processing arguments             */
  fd_set readfds;              /* File descriptor set for multiplexing i/o    */      
  struct timeval timeout;  // select() timeout interval
  int nready;
  char cmdPrompt[SHORT_STR_SIZE];  // command prompt (hostID%)

  /* internet address handling */

  struct sockaddr_in server;   /* ISIS server's network socket address */
  int server_len;

  /* Yow! */

  sel_wid = getdtablesize();

  /* 
   * Set the default ini filename, may be overridded by -f 
   */

  strcpy(systab->exefile,argv[0]);
  strcpy(systab->inifilename,DEFAULT_INI_FILE);
  strcpy(systab->userid,getenv("USER"));
  GetUTCTime();
  sprintf(systab->starttime,"UTC %s %s",systab->date,systab->time);

  /* Process the command line arguments, if any */

  while (--argc > 0 && (*++argv)[0] == '-') {
    c = *++argv[0];
    switch(c) {
    case 'f':  /* use a different initialization file */
      memset(systab->inifilename,0,sizeof(systab->inifilename));
      sscanf(*argv,"f%s",systab->inifilename);
      if (strlen(systab->inifilename) == 0) {
	MAGTEXT;
	printf("ERROR: -f syntax incorrect\n");
	TXTRESET;
	PrintUsage();
	exit(1);
      }
      break;
      
    default:
      MAGTEXT;
      printf("Error: Illegal option %c\n",c);
      TXTRESET;
      PrintUsage();
      exit(1);
      break;
    }
  }

  /* So far so good, give the welcome banner */
  
  printf("\n");
  printf("  ----------------------------------------------\n");
  printf("                     Caliban\n");
  printf("     Data-Taking System Image-Transfer Agent\n\n");
  printf("  Version: %s (%s %s)\n",VERSION,COMPDATE,COMPTIME);
  printf("  ----------------------------------------------\n");
  printf("\n");

  /* Initialize the Caliban session */

  InitCB();

  /* startup the history functions and the readline handler */

  using_history();

  /* Request disk synchronization from the disk host */

  if (systab->fd_disk != 0) 
    XmitMsg(systab->fd_disk, systab->diskhost, "%s", "REQ INITDISK");

  /* 
   * If using sockets, and the socket port is not the transfer disk
   * interface, ping the server to handshake.  If the transfer disk
   * interface is SOCKET, the disk-sync request above implicitly
   * handshakes with the ISIS server.
   */

  if (systab->usesocket == cb_TRUE) {
    if (systab->fd_disk != systab->fd_socket) {
      XmitMsg(systab->fd_socket,systab->sockethost,"%s","PING");
    }
  }

  /* Display the cli prompt and install the keyboard callback handler */

  sprintf(cmdPrompt,"%s%% ",systab->localhost);

  //rl_callback_handler_install("CB% ",KbdHandler);
  rl_callback_handler_install(cmdPrompt,KbdHandler);

  /*********************************************************************
   * 
   * *** Main Communications Multiplexing Loop ***
   *
   * multiplexes between keyboard and port inputs (serial, socket, or
   * both).  We use the select() wait mechanism to avoid busy waiting
   * and wasting CPU cycles.
   */

  do {

    /* 
     * Set up file descriptor set for the select() semaphore
     */

    FD_ZERO(&readfds);

    /* Always use the keyboard */

    FD_SET(systab->fd_keyboard, &readfds);

    /* If we are using serial or socket or both, set their file
     * descriptors here, but only if we actually got an active handle in
     * from the initialization.
     */

    if (systab->fd_serial!=0) 
      FD_SET(systab->fd_serial, &readfds);

    if (systab->fd_socket!=0)
      FD_SET(systab->fd_socket, &readfds);

    // select() waits for something to happen on one of the ports...
    // subject to a timeout interval.  If systab->timeout=0, wait forever
    // for something to happen

    if (systab->timeout > 0) {
      timeout.tv_sec = systab->timeout;
      timeout.tv_usec = 0;
      nready = select(sel_wid, &readfds, NULL, NULL, &timeout);
    }
    else {
      nready = select(sel_wid, &readfds, NULL, NULL, NULL);
    }      

    // figure out what happened

    if (nready == 0) { // timeout, see if we should do anything 
      // Do we have any pending REQ SWAP acknolwedges?
      if (systab->doAckSwap && systab->reqswap) {
	if (systab->nreqswap >= MAXREQSWAP) { // max retries failed, bad
	  MAGTEXT;
	  printf("*** BADNESS: %d REQ SWAP attempts failed\n",systab->nreqswap);
	  printf("             Cancelling REQ SWAP attempts - check %s host status\n",
		 systab->diskhost);
	  TXTRESET;
	  systab->reqswap = 0;
	  systab->nreqswap = 0;
	}
	else {
	  REDTEXT;
	  printf("*** Pending REQ SWAP ACK timeout, retry %d ***\n",systab->nreqswap);
	  TXTRESET;
	  XmitMsg(systab->fd_disk, systab->diskhost, "%s", "REQ SWAP"); 
	  systab->reqswap = 1;
	  systab->nreqswap++;
	}
      }	  
    }
    else if (nready < 0) { // select() returned an error, handle it
      if (errno == EINTR) 
	printf("select() interrupted by Ctrl+C...continuing\n");
      else 
        printf("Warning: select() failed - %s - pressing on anyway...\n",
               strerror(errno));

      rl_refresh_line(0,0);
      continue;
    }
    else {  // select() has input to process

      // if the keyboard, use the readline handler

      if (FD_ISSET(systab->fd_keyboard, &readfds)) {
	rl_callback_read_char();

	if (strlen(msgbuf) > 0) {
	  msgbuf[strlen(msgbuf)] = NUL;
	  strcpy(systab->oldinbuf, msgbuf);

	  // a keyboard command is basically a message to myself

	  sprintf(argbuf, "%s>%s %s", systab->localhost,
		  systab->localhost,msgbuf);
    
	  // Process the command
	
	  DoCommand(0,argbuf); 

	  rl_refresh_line(0,0);
	
	}

	memset(msgbuf,0,sizeof(msgbuf));
      }
      
      // Second branch of the multiplexing.  Input is waiting on the
      // serial port, read and pass to the command handler.

      else if (FD_ISSET(systab->fd_serial, &readfds)) {
	memset(msgbuf, 0, sizeof(msgbuf));
	charsin = read(systab->fd_serial, msgbuf, sizeof(msgbuf));
	if (charsin < 0) {
	  REDTEXT;
	  printf("\n<< ERROR: could not read serial port - %s >>\n",strerror(errno));
	  TXTRESET;
	}
	else {
	  msgbuf[charsin] = NUL;
	  if (msgbuf[strlen(msgbuf)-1]=='\r') msgbuf[strlen(msgbuf)-1]='\0';
	  strcpy(systab->oldinbuf, msgbuf);
	  DoCommand(systab->fd_serial,msgbuf); /* Process the command */
	}
	rl_refresh_line(0,0);
	
      }

      // Third branch of the multiplexing.  Input is waiting on the
      // socket port, read and pass to the command handler.

      else if (FD_ISSET(systab->fd_socket, &readfds)) {
	memset(msgbuf, 0, sizeof(msgbuf));

	server_len = sizeof(server);
	charsin = recvfrom(systab->fd_socket, msgbuf, sizeof(msgbuf), 0,
			   (struct sockaddr *) &server, (socklen_t *)&server_len);
	if (charsin < 0) {
	  REDTEXT;
	  printf("\n<< ERROR: could not read network socket - %s >>\b",strerror(errno));
	  TXTRESET;
	}
	else {
	  msgbuf[charsin] = NUL;
	  if (msgbuf[strlen(msgbuf)-1]=='\r') msgbuf[strlen(msgbuf)-1]='\0';
	  strcpy(systab->oldinbuf, msgbuf);
	  DoCommand(systab->fd_socket,msgbuf); /* Process the command */
	}
	rl_refresh_line(0,0);
	
      }
    } // select() return test done

  } while (!(systab->done)); /* Exit once the done flag is set */

  /*
   * *** End of the Communications Multiplexing Loop ***
   *
   ****************************************************************/

  /*
   * We're about to exit, so we need to let the diskhost know that the
   * mount points we'd setup earlier are no longer available.  Do this
   * by sending a sequence of UNMOUNT requests for each mountpoint.
   */

  for(lcv=0;lcv<mounttab->nummounts;lcv++)
    XmitMsg(systab->fd_disk, systab->diskhost, "UNMOUNT %s", mounttab->mount[lcv]);

  /* Broadcast that we're going offline (new-style syntax) */
  
    if (systab->fd_disk != 0) 
      XmitMsg(systab->fd_disk, "AL", "STATUS: MODE=OFFLINE %s=DISABLED", 
	      systab->localhost);
      
  /* Mop up */

  LogMsg("#### Caliban exited normally ####");

  if(systab->fd_serial!=0)
    close(systab->fd_serial);

  if(systab->fd_socket!=0)
    close(systab->fd_socket);

  if(systab->logfd!=0)
    close(systab->logfd);
      
  exit(0);
}
  

/***************************************************************************/

/* 
 * KbdHandler() - readline callback function that handles all keyboard input
 *                
 */

void
KbdHandler(char *line)
{
  char argbuf[BUF_SIZE];   /* Buffer for protocol messages    */

  /* if we got null, return */

  if (line==NULL) 
    return;

  memset(msgbuf,0,sizeof(msgbuf));

  if (strlen(line)==0) 
    return;

  /*  history expansion */

  strcpy(msgbuf,line);

  if (line[0]) {
    char *expansion;
    int result;

    result = history_expand(line,&expansion);
    if (result) 
      printf("%s\n", expansion);
    
    if (result < 0 || result == 2) {
      free(expansion);
      return;
    }
    
    add_history(expansion);
    strncpy(msgbuf,expansion,sizeof(msgbuf)-1);

    free(expansion);
  }

  free(line);

}

/***************************************************************************/

void 
PrintUsage()
{
  printf("\nUsage: caliban [-fINIfile]\n");
  printf("where:\n");
  printf("   -fINIfile = use INIfile instead of the system default\n");
  printf("\n");
}

/***************************************************************************/

void
GetUTCTime(void)
{
  struct tm *gmt;
  time_t t;
  int monthnum;
  int ccyy;

  t = time(NULL);
  gmt = gmtime(&t);
  monthnum = (gmt->tm_mon)+1;

  /* ISO 8601 Date & time format: ccyy-mm-dd, hh:mm:ss */

  ccyy = gmt->tm_year + 1900;
  sprintf(systab->date,"%.4i-%.2i-%.2i",ccyy,monthnum,gmt->tm_mday);
  sprintf(systab->time,"%.2i:%.2i:%.2i",gmt->tm_hour,gmt->tm_min,
	  gmt->tm_sec);

}

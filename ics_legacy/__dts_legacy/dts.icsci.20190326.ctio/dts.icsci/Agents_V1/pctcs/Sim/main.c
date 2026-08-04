//
// pctcs - Simple interactive client to interface with a ComSoft PC-TCS
//         telescope controller.
//
// usage: pctcs [rcfile]
// 
// where:
//   rcfile   = optional runtime config file to load.  By default it
//              uses the runtime config file defined in the pctcs.h
//              header file, DEFAULT_RCFILE
//
// Description:
//   The ComSoft PC-TCS system provides a serial interface for remote
//   interation.  This serial interface primarily transmits a continous
//   stream of TCS telemetry at a cadence of about 1 message string
//   every 200msec.  This agent provides a basic IMPv2-compliant
//   interface to the PC-TCS system.
//
//   In its current implementation, its only role is to record and
//   translate the PC-TCS telemetry data into an IMPv2-compliant status
//   message.  (as well as providing some low-level diagnostics).
//   Future expansion will include are remote command interface, e.g.,
//   for commanding focus changes, offsets, etc.
//
//   The basic program uses select() to monitor the serial port
//   telemetry stream, watch the command-line interface for keyboard
//   commands (stdin via the GNU readline/history mechanism), and to
//   watch for IMPv2 communications on its UDP socket interface.  The
//   agent may be configured either as an ISIS client, or as a
//   standalone program operating independently of an ISIS system.
//
//   Runtime configuration is accomplished using an external config file
//   to specify ports and relevant runtime parameters.  Basic commands
//   allow some dynamic re-configuration, but generally the config file is
//   given primacy for critical parameters (e.g., port assignments).
//
// Author:
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2004 February 29
//
// Modification History:
//   2004 Feb 29 - based on fwagent
//
//---------------------------------------------------------------------------

#include "pctcs.h"       // PC-TCS agent header file

// The client cli uses the GNU readline and history utilities

#include <readline/readline.h>
#include <readline/history.h>

// define this to turn on ultra-verbose debugging

#undef __DEBUG

// maximum number of telemetry sips

// maximum select() width (overkill, but works for now)

static int sel_wid;

// Client data structures

isisclient_t client;  // ISIS Client runtime parameters
pctcs_t tcs;         // PC-TCS data
systime_t tctime;    // generic date/time data structure

// The main event...

int
main(int argc, char *argv[]) 
{
  int n;
  int i=0;

  char buf[ISIS_MSGSIZE];   // command/message buffer
  int n_tcs;                // # of chars read on the PC-TCS port
  int sipcount=0;           // telemetry stream sip counter
  char reply[BIG_STR_SIZE]; // reply buffer

  // readline & history handling stuff

  char cliPrompt[ISIS_NODESIZE+2]; // the console prompt is our ISIS node name

  // PC-TCS comm buffer

  char tcsbuf[BUF_SIZE];

  // select() event handler parameters

  fd_set read_fd;
  int kbdFD;
  int n_ready;
  struct timeval timeout;

  // Basic initializations

  sel_wid = getdtablesize();
  kbdFD = fileno(stdin);  // file descriptor of stdin, safe definition

  // Parse the command line 

  if (argc>2) {
    printf("usage: %s [rcfile]\n", argv[0]);
    printf("where: rcfile = optional runtime config file (default %s)\n",
           DEFAULT_RCFILE);
    exit(1);
  }

  // Load the specified runtime config file, or use the default if none given

  if (argc==2)
    n = loadConfig(argv[1]);
  else
    n = loadConfig(DEFAULT_RCFILE);

  if (n!=0) {
    printf("Unable to load the runtime config file...pctcs aborting\n");
    exit(1);
  }

  // Some useful startup info (who, what, when...)

  strcpy(tcs.userID,getenv("USER"));  // Who started this thing, anyway?
  strcpy(tcs.exeFile,argv[0]);        // command executed
  strcpy(tcs.startTime,ISODate());    // when the agent was started

  // So far so good, give the welcome information
  
  printf("\n");
  printf("  --------------------------------------------\n");
  printf("                   PC-TCSAgent\n");
  printf("    Interactive PC-TCS Remote Interface Client\n\n");

  printf("  Version: %s (%s %s)\n",APP_VERSION,APP_COMPDATE,
	 APP_COMPTIME);
  printf("  --------------------------------------------\n");
  if (tcs.simMode) {
    REDTEXT;
    printf("       *** Running in Simulation Mode ***\n");
    TXTRESET;
  }
  printf("\n");

  // If required, initialize the socket connection to the ISIS server.
  // We can disable ISIS interaction by specifying "Mode Standalone" or
  // "ServerID None" in the runtime config file

  if (client.useISIS) {
    if (InitISISServer(&client)<0) {
      printf("ISIS server connection initialization failed - aborting\n");
      exit(2);
    }
  }

  // Open the client network socket port for ISIS communications.  We
  // open this anyway since it costs us nothing, and a subsequent "open
  // isis" command will need it.  Also provides the the comm port used
  // for socket comm in Standalone mode.
  
  if (OpenClientSocket(&client)<0) {
    printf("Client socket initialization failed - aborting\n");
    exit(3);
  }

  if (client.useISIS)
    printf("Started pctcs as ISIS client node %s on %s port %d\n",
	   client.ID, client.Host, client.Port);
  else
    printf("Started pctcs as standalone ISIS node %s on %s port %d\n",
	   client.ID, client.Host, client.Port);

  // Initialize the PC-TCS link
  
  if (!tcs.simMode) {
    if (initPCTCS(&tcs,reply)<0) {
      REDTEXT;
      printf("PC-TCS serial port comm init failed - %s\n",reply);
      printf("Try again later using the \"tcinit\" command\n");
      TXTRESET;
    }
    else
      printf("PC-TCS comm link initialized.\n");
  }

  // All set to rock-n-roll...

  printf("\n-------------------------------------------------\n");
  printf("Type 'quit' to terminate the pctcs session\n");
  printf("Type 'help' to see a list of interactive commands\n");
  printf("-------------------------------------------------\n");

  // Startup the command-line history mechanism

  using_history();

  // Setup the command prompt and install the readline() callback
  // handler for this application (keyboardCmd() in commands.c)

  sprintf(cliPrompt,"%s%% ",client.ID);
  rl_callback_handler_install(cliPrompt,keyboardCmd);

  // If configured as an ISIS client, broadcast a PING to the ISIS
  // server.  If it fails, we'll have to do the ping by hand after the
  // comm loop starts.

  if (client.useISIS) {
    memset(buf,0,ISIS_MSGSIZE);
    sprintf(buf,"%s>AL ping\r",client.ID);
    n = SendToISISServer(&client,buf);
    if (n<0) {
      REDTEXT;
      printf("failed to ping the ISIS server...\n",strerror(errno));
      TXTRESET;
    }
    if (client.isVerbose)
      printf("OUT: %s\n",buf);
  }

  // If a SIGINT trap is used, set it here...

  // Set the initial states of the TCS telemetry flags

  tcs.idle = 0.0;             // zero the idle-time clock
  tcs.doSip = 0;                 // turn off the telemetry stream "sip" flag
  tcs.tick = SysTimestamp();  // Set the starting timestamp

  // Start the I/O event handling loop 

  client.KeepGoing = 1;

  while (client.KeepGoing) {

    FD_ZERO(&read_fd); // clear the table of active file descriptors

    // we always listen for console keyboard input

    FD_SET(kbdFD, &read_fd);

    // if enabled, listen to this app's ISIS client socket

    if (client.FD > 0) FD_SET(client.FD, &read_fd);

    // if initialized, listen to the PC-TCS serial port

    if (tcs.fd > 0)
      FD_SET(tcs.fd, &read_fd);    

    // For the PC-TCS, on each pass through the comm loop, check the
    // time since the last PC-TCS telemetry string was received.  This
    // lets us detect when the PC-TCS has gone idle and set our comm
    // state accordingly.  We check to see if the idle time is greater
    // than the idle timeout interval.

    if (client.Debug)
      printf("Last PC-TCS telemetry was %.6f seconds ago\n",tcs.idle);

    // Only check idle status if a live PC-TCS system

    if (!tcs.simMode) {
      if (tcs.idle > (double)(tcs.idleTime)) {
	switch (tcs.link) {
	case TCS_UP:
	  tcs.link = TCS_IDLE;
	  printf("STATUS: PC-TCS Link has been idle for %.6f sec (>%d sec)\n",
		 tcs.idle,tcs.idleTime);
	  printf("         Setting PC-TCS state flag to IDLE\n");
	  break;
	  
	default:
	  break;
	}
      }
      else {
	switch (tcs.link) {
	case TCS_IDLE:
	  tcs.link = TCS_UP;
	  printf("STATUS: PC-TCS Link has become active again\n");
	  break;
	
	default:
	  break;
	}
      }
    }
    else 
      tcs.link = TCS_SIM;

    // Do the select() call and wait for activity on any of our comm
    // ports or the console keyboard
     
    n_ready = 0;
    n_ready = select(sel_wid, &read_fd, NULL, NULL, NULL);
    
    if (n_ready == 0) { // would be a timeout if enabled, do nothing...
      continue;

    }
    else if (n_ready < 0) {
      CYATEXT;
      printf("Warning: select() failed - %s - pressing on anyway...\n",
             strerror(errno));
      TXTRESET;
      rl_refresh_line(0,0);
      continue;

    }
    else { // somebody wants something, figure out who...

      // Update the idle timer

      tcs.idle = SysTimestamp() - tcs.tick;

      // Console keyboard input

      if (FD_ISSET(kbdFD, &read_fd))
	rl_callback_read_char(); // readline() handler

      // ISIS client socket input

      if (FD_ISSET(client.FD, &read_fd)) {
	memset(buf,0,ISIS_MSGSIZE);
	if (ReadClientSocket(&client,buf)>0) {
	  if (client.isVerbose) printf("IN: %s\n",buf);
	  socketCmd(buf);
	  rl_refresh_line(0,0);
	}
      }

      // Input on the PC-TCS serial port

      if (tcs.fd > 0) {

	if (FD_ISSET(tcs.fd, &read_fd)) {

	  memset(tcsbuf,0,BUF_SIZE);

	  if ((n_tcs=read(tcs.fd,tcsbuf,BUF_SIZE)) < 0) {
	    REDTEXT;
	    printf("ERROR: read() error on serial port %s - %s\n",
		   tcs.port,strerror(errno));
	    printf("       Assuming that the PC-TCS link is DOWN.\n");
	    TXTRESET;
	    tcs.link = TCS_DOWN;
	  }
	
	  // We got something, set the tcsTick timestamp

	  if (n_tcs > 1) 
	    tcs.tick = SysTimestamp();
	  
	  // If sipping the telemetry stream, print the raw stream and
	  // advance the sip counter

	  if (tcs.doSip) {
	    if (n_tcs > 1) {
	      if (sipcount==0) 
		printf("starting telemetry stream sipping\n");
	      printf("TCS [%d]: %s",n_tcs,tcsbuf);
	      sipcount++;
	    }
	    if (sipcount > MAX_SIP) {
	      tcs.doSip = 0;
	      sipcount = 0;
	      printf("DONE: sipped telemetry stream %d times\n",MAX_SIP);
	    }
	  }
	  
	  // if we got something big enough, try to parse it

	  if (n_tcs >= MIN_TCSBUF) parseComsoft(&tcs,tcsbuf);

	  memset(tcsbuf,0,BUF_SIZE);  // reset comm buffer

	} // end of PC-TCS read 

      } // end of PC-TCS serial port handling

      // add any new FD handlers here...

    } // end of select() I/O handling checking

  } // bottom of the while(client.KeepGoing) loop

  //----------------------------------------------------------------
  //
  // If we got here, the client was instructed to shut down
  //

  printf("\npctcs client shutting down...\n");

  // Tear down the client socket connection

  if (client.FD > 0)
    close(client.FD);

  // Tear down the PC-TCS serial port connection

  if (tcs.fd>0)
    close(tcs.fd);

  // Remove the readline() callback handler

  rl_callback_handler_remove();

  // all done, say goodbye...

  printf("bye\n");

  exit(0);

}

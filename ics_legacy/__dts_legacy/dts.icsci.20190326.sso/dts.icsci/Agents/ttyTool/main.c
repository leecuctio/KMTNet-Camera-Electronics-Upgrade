/*!
  \mainpage TTYTool - Interactive Serial (TTY) Port Client

  \author R. Pogge, OSU Astronomy Dept. (pogge@astronomy.ohio-state.edu)
  \date 2005 February 17

  \section Usage

  Usage: ttytool [rcfile]

  Where: \c rcfile is an optional runtime config file to load.  

  By default, ttytool uses the runtime config file defined by
  #DEFAULT_RCFILE in the client.h header.

  \section Introduction

  ...

  ttytool can be run as either a standalone interactive program with a
  command-line interface and backdoor socket interface, or as a client
  in an ISIS system.  Using the agent in standalone mode with the
  backdoor socket interface (the same UDP socket used for ISIS server
  communications), we have successfully run the agent from a Perl script
  and other external processes that know how to communicate in the IMPv2
  messaging syntax.

  \section Commands

  These are the interactive commands for ttytool:
<pre>
Client Commands:
  info           - report client information
  version        - report ttytool version & compile info
  reset          - reset runtime & controller parameters
  verbose        - toggle verbose output mode
  debug          - toggle debugging output
  quit           - quit ttytool
  history        - show command history
  !!             - repeat last command
  !cmd           - repeat last command matching 'cmd'
  help or ?      - view this list
</pre>
  Note that all commands are <em>case-insensitive</em>.

  \section Config Runtime Configuration File

  This is a typical runtime config file for the ttytool agent:

  \verbinclude ttytool.ini

  Note that all parameter names are \e case-insensitive.

  \section Notes

  This application uses the ISISclient library (link).

  \section Mods Modification History

<pre>
2005 February 16 - new application [rwp/osu]
</pre>

\todo 
<ul>
<li>Add commands for opening/closing/changing comm ports
<li>Add commands for loading/saving config files by name
<li>Add a command for executing an input sensor scan w/output
<li>Add a command for operating a brake
<li>Add a command apropos facility
</ul>
*/

/*!
  \file main.c
  \brief ttytool main program and I/O event handler.
*/

#include "isisclient.h"  // ISIS common client library header
#include "client.h"      // Custom client application header

// The client cli uses the GNU readline and history utilities

#include <readline/readline.h>
#include <readline/history.h>

// ISIS Client data structure

isisclient_t client;

// Mechanism structs, as required

ttyport_t commport;    // comm port parameters struct

//----------------------------------------------------------------
//
// The main event...

int
main(int argc, char *argv[]) 
{
  int n;
  int i=0;
  int nread;
  
  int nopen=0;          // number of open, addressable RTS server ports
  
  char buf[ISIS_MSGSIZE]; // command/message buffer
  
  char ttyData[256];   // raw scl serial port data string (oversized)
  int lastchar;
  
  // readline & history handling stuff
  
  char cliPrompt[ISIS_NODESIZE+2]; // the console prompt is our ISIS node name
  
  // select() event handler parameters
  
  fd_set read_fd;
  int kbdFD;
  int n_ready;
  struct timeval timeout;
  static int sel_wid;
  
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
  
  // So far so good, give the welcome information
  
  printf("\n");
  printf("  -------------------------------------------\n");
  printf("                  TTYTool\n");
  printf("  Interactive Serial (TTY) Port Command Agent\n\n");

  printf("  Version: %s (%s %s)\n",APP_VERSION,APP_COMPDATE,APP_COMPTIME);
  printf("  -------------------------------------------\n");
  printf("\n");

  // Load the specified runtime config file, or use the default if none given

  if (argc==2)
    n = LoadConfig(argv[1]);
  else
    n = LoadConfig(DEFAULT_RCFILE);

  if (n!=0) {
    printf("Unable to load the runtime config file...ttytool aborting\n");
    exit(1);
  }

  // If required, initialize the socket connection to the ISIS server
  // We can disable ISIS interaction by specifying "ServerID None" in
  // the runtime config file

  if (client.useISIS) {
    if (InitISISServer(&client)<0) {
      printf("ISIS server connection initialization failed - aborting\n");
      exit(2);
    }
  }

  // Open the client network socket port for interprocess communications
  
  if (OpenClientSocket(&client)<0) {
    printf("Client socket initialization failed - aborting\n");
    exit(3);
  }

  if (client.useISIS)
    printf("Started ttytool as ISIS client node %s on %s port %d\n",
	   client.ID, client.Host, client.Port);
  else
    printf("Started ttytool as standalone agent %s on %s port %d\n",
	   client.ID, client.Host, client.Port);

  // Now, open connections to all of the specified RTS server serial ports.

  printf("Initializing comm port connection(s)...\n");

  OpenTTYPort(&commport);
  if (commport.FD>0) {
    printf("Opened comm port %s\n",commport.Port);
  }
  else {
    printf("ERROR: Could not Open comm port %s\n",commport.Port);
    printf("       Make sure the system is on and properly configured,\n");
    printf("       then try again.\n");
    printf("ttytool aborting\n");
    exit(3);
  }

  // All set to rock-n-roll...

  printf("\n----------------------------------------------\n");
  printf("Type 'quit' to terminate the ttytool session\n");
  printf("Type 'help' to see a list of commands\n");
  printf("Type 'reset' to reset the comm port\n");
  printf("----------------------------------------------\n");

  // Startup the command-line history mechanism

  using_history();

  // Setup the command prompt and install the readline() callback
  // handler for this application (KeyboardCommand() in commands.c)

  sprintf(cliPrompt,"%s%% ",client.ID);
  rl_callback_handler_install(cliPrompt,KeyboardCommand);
  
  // Broadcast a PING to the ISIS server, if enabled.  If it fails,
  // we'll have to do the ping by hand after the comm loop starts.

  if (client.useISIS) {
    memset(buf,0,ISIS_MSGSIZE);
    sprintf(buf,"%s>AL ping\r",client.ID);
    if (SendToISISServer(&client,buf)<0) 
      printf("Failed to PING the ISIS server...\n",strerror(errno));
    if (client.isVerbose)
      printf("OUT: %s\n",buf);
  }

  // Set the SIGINT signal trap 

  signal(SIGINT,HandleInt); // Ctrl+C sends a move abort to controller
  signal(SIGPIPE,SIG_IGN);  // ignore broken pipes

  // Start the I/O event handling loop 

  client.KeepGoing = 1;

  while (client.KeepGoing) {

    FD_ZERO(&read_fd); // clear the table of active file descriptors

    // we always listen for console keyboard input

    FD_SET(kbdFD, &read_fd);

    // if enabled, listen to this application's UDP socket

    if (client.FD > 0) FD_SET(client.FD, &read_fd);

    // Also listen to the TTY comm port, if active

    if (commport.FD > 0) FD_SET(commport.FD, &read_fd);    

    // Do the select() call and wait for activity on any of our comm
    // ports or the console keyboard
     
    n_ready = 0;
    n_ready = select(sel_wid, &read_fd, NULL, NULL, NULL);
    
    if (n_ready == 0) { // would be a timeout if enabled, do nothing...
      continue;

    }
    else if (n_ready < 0) {
      if (errno == EINTR) { // caught Ctrl+C, hopefully sigint handler caught it
	if (client.Debug)
	  printf("select() interrupted by Ctrl+C...continuing\n");
      }
      else { // something else bad happened, let us know
	printf("Warning: select() failed - %s - pressing on anyway...\n",
	       strerror(errno));
      }
      rl_refresh_line(0,0);
      continue;
      
    }
    else { // somebody wants something, figure out who...
      
      // Console keyboard input
      
      if (FD_ISSET(kbdFD, &read_fd)) {
	rl_callback_read_char();  // readline() command handler
	signal(SIGINT,HandleInt);  // reset the SIGINT handler
      }
      
      // Client socket input
      
      if (FD_ISSET(client.FD, &read_fd)) {
	memset(buf,0,ISIS_MSGSIZE);
	if (ReadClientSocket(&client,buf)>0) {
	  if (client.isVerbose) printf("IN: %s\n",buf);
	  SocketCommand(buf);
	  rl_refresh_line(0,0);
	}
      }
      
      // Unexpected input the filter-wheel microstep drive port.
      // just echo it to the console for now.
      
      if (commport.FD > 0) {
	if (FD_ISSET(commport.FD, &read_fd)) {
	  
	  // read the comm port
	  
	  nread = ReadTTYPort(&commport,ttyData,0L);  // direct read, no timeout
	  if (nread > 0) {
	    printf(">> %s\n",ttyData);
	    memset(ttyData,0,sizeof(ttyData));
	    rl_refresh_line(0,0);
	  }
	}
	
      } // end of TTY Port handling
      
      // add any new FD handlers here...
      
    } // end of select() I/O handling checking
    
  } // bottom of the while(client.KeepGoing) loop

  //----------------------------------------------------------------
  //
  // If we got here, the client was instructed to shut down
  //

  printf("\nttytool client shutting down...\n");

  // Tear down the client socket

  CloseClientSocket(&client);

  // Tear down any remaining microstep drive comm port connection(s)
  
  if (commport.FD>0) 
    CloseTTYPort(&commport);

  // Remove the readline() callback handler

  rl_callback_handler_remove();

  // all done, say goodbye...

  printf("bye\n");
  
  exit(0);

}

//---------------------------------------------------------------------------

/*!
  \brief Service Ctrl+C Interrupts (SIGINT signals)

  SIGINT signal trap for trapping Ctrl+C interrupts.  Calls
  abortall() to immediately abort all moves in progress.

  \sa abortall()
*/

void
HandleInt(int signalValue)
{
  if (client.Debug)
    printf("Caught Ctrl+C (Signal %d)...\n", signalValue);
  
  printf("Ctrl+C Abort requested - aborting moves now - check state after abort!\n");

}

//---------------------------------------------------------------------------
//
// abortall() - Abort all pending moves
//

/*!
  \brief Abort all pending moves

  Uses the low-level SCLAbort() function to send the motion abort (SK =
  Stop/Kill) command to all microstep drives.  Sending SK to an idle
  microstep drive has no consequences, so this shotgun approach is the
  simplest and safest.

  Invoked by the Ctrl+C interrupt handler (HandleInt()), and called
  at the end of the main program when the application is quitting to
  make sure we don't accidentally quit and leave things running.

  \sa HandleInt() and SCLAbort()
*/

//void
// abortall(void) 
// { 
//   if (commport.FD > 0) 
//     SCLAbort(commport.FD); 
//   scl.Abort = 1; 
// } 


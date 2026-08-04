/*!
  \mainpage tvdisp - Interactive Image Display Client

  \author R. Pogge, OSU Astronomy Dept. (pogge@astronomy.ohio-state.edu)
  \date 2005 May 31

  \section Usage

  Usage: tvdisp [rcfile]

  Where: \c rcfile is an optional runtime config file to load.  

  By default, tvdisp uses the runtime config file defined by
  #DEFAULT_RCFILE in the client.h header.

  \section Introduction

  ...

  \section Commands

  These are the interactive commands for tvdisp:
  <pre>
  info           - report client information
  version        - report tvdisp version & compile info
  reset          - reset runtime & controller parameters
  verbose        - toggle verbose output mode
  debug          - toggle debugging output
  quit           - quit tvdisp
  history        - show command history
  !!             - repeat last command
  !cmd           - repeat last command matching 'cmd'
  help or ?      - view this list
  </pre>
  Note that all commands are <em>case-insensitive</em>.

  \section Config Runtime Configuration File

  This is a typical runtime config file for the tvdisp agent:
  \verbinclude tvdisp.ini

  Note that all parameter names are \e case-insensitive.

  \section Notes

  This application uses the ISISclient library (link).

  \section Mods Modification History

<pre>
2005 May 31 - new application [rwp/osu]
</pre>

*/

/*!
  \file main.c
  \brief tvdisp main program and I/O event handler.
*/

#include "isisclient.h"  // ISIS common client library header

#include "client.h"      // Custom client application header

// The client cli uses the GNU readline and history utilities

#include <readline/readline.h>
#include <readline/history.h>

// Global data structures

isisclient_t client;  // Client ISIS common data structure
disp_t tv;   // Display parameters data structure
img_t img; // FITS image data structure

//----------------------------------------------------------------
//
// The main event...

int
main(int argc, char *argv[]) 
{
  int n;
  int i=0;
  int nread;
  int readout = 0;
  int countdown = 0;
  double dt;

  char buf[ISIS_MSGSIZE]; // command/message buffer
  char reply[256];   // generic reply string

  char camData[256];   // raw AzCam socket port string
  int lastchar;
  
  // readline & history handling stuff
  
  char cliPrompt[ISIS_NODESIZE+2]; // the console prompt is our ISIS node name
  
  // select() event handler parameters
  
  fd_set read_fd;
  int kbdFD;
  int n_ready;
  struct timeval timeout;
  static int sel_wid;

  // Parameters for the display in main

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
  printf("  --------------------------------------\n");
  printf("                tvdisp\n");
  printf("  Interactive Image Display Agent\n\n");

  printf("  Version: %s (%s %s)\n",APP_VERSION,APP_COMPDATE,APP_COMPTIME);
  printf("  --------------------------------------\n");
  printf("\n");

  // Load the specified runtime config file, or use the default if none given

  if (argc==2)
    n = LoadConfig(argv[1]);
  else
    n = LoadConfig(DEFAULT_RCFILE);

  if (n!=0) {
    printf("Unable to load the runtime config file...tvdisp aborting\n");
    exit(1);
  }

  // Now we do various initializations

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
    printf("Started tvdisp as ISIS client node %s on %s port %d\n",
	   client.ID, client.Host, client.Port);
  else
    printf("Started tvdisp as standalone agent %s on %s port %d\n",
	   client.ID, client.Host, client.Port);
  
  // Initialize the image display

  tv.FD = xtvopen(tv.NX,tv.NY,tv.NColors,tv.Zoom,tv.Flip,tv.AppName,tv.WinName);

  if (tv.FD < 0) {
    printf("Could not initialize the image display\n");
    printf("tvdisp aborting\n");
    exit(2);
  }
  else {
    printf("Image Display Window initialized.\n");
    // now, some random bogosity, make a fake image full of zeros
    // and display it.  Default is the size of the image display
    if (FakeImage(&img,tv.NX,tv.NY,0.0)<0) {
      printf("Not good, tvdisp aborting...\n");
      exit(2);
    }
    tv.z1 = 0.0;
    tv.z2 = 4.0;
    xtvload(img.data,img.nx,img.ny,img.nx,0,0,1,1,tv.z1,tv.z2,tv.Flip,1,0);
    xtvcolorld(tv.r,tv.g,tv.b,256);
  }

  // All set to rock-n-roll...

  printf("\n----------------------------------------------\n");
  printf("Type 'quit' to terminate the interactive session\n");
  printf("Type 'help' to see a list of commands\n");
  printf("Type 'reset' to reset the session\n");
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

  //----------------------------------------------------------------------
  //
  // Start the I/O event handling loop.
  //
  // The event handler has to have some awareness of the AzCam server
  // state, which it tracks using the ccd.State data member.
  //
  // If ccd.State = IDLE, the handler just waits for input (select()
  // call with no timeout).  If, however, there is an AzCam server
  // connected, then every 30 seconds it queries the AzCam server to
  // read the CCD and Dewar temperature.
  //
  // If ccd.State = EXPOSING, then it sets up select() with a 1
  // second timeout to watch for Abort directives from the console or
  // remote clients, and then polls the AzCam for the current
  // integration status, maintaining a parallel countdown.  On
  // integration completion, it switches the state to ccd.State=READOUT
  // as appropriate.
  // 
  // If ccd.State = READOUT, it similarly sets up select()  with a 1
  // second timeout and polls the AzCam server for the readout
  // status by watching the pixel counter.  When the pixel counter
  // reaches the expected number (ccd.Npixels), it fires off the
  // Write command and when write is done, sets the AzCam server state
  // flag back to IDLE.
  // 
  // If ccd.State = PAUSE, we have a paused exposure, so we go into
  // a minimal polling state like being idle.
  //

  client.KeepGoing = 1;

  while (client.KeepGoing) {
    
    FD_ZERO(&read_fd); // clear the table of active file descriptors
    
    // we always listen for console keyboard input
    
    FD_SET(kbdFD, &read_fd);
    
    // if enabled, listen to this application's UDP socket
    
    if (client.FD > 0) FD_SET(client.FD, &read_fd);
    
    // Also listen for X events
    
    if (tv.FD > 0) FD_SET(tv.FD, &read_fd);    

    // Do the select() call and wait for activity on any of our comm
    // ports or the console keyboard
     
    n_ready = 0;

    // Setup for 1 second timeout, refresh the display 

    timeout.tv_sec = 1;
    timeout.tv_usec = 0;
    n_ready = select(sel_wid, &read_fd, NULL, NULL, &timeout);
      
    //----------------------------------------------------------------
    //
    // select() done, take action depending on the value of n_ready
    // returned
    //

    // select() timed out, refresh the display or other timeout activities

    if (n_ready == 0) {
      if (tv.FD > 0) xtv_refresh(0);
    }
    
    // select() returned an error, handle it
    
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
    
    // select() has input to process on one of the input channels
    
    else {
      
      // Console keyboard input
      
      if (FD_ISSET(kbdFD, &read_fd)) {
	rl_callback_read_char();  // readline() command handler
	signal(SIGINT,HandleInt);  // reset the SIGINT handler
      }
      
      // Client socket input
      
      if (client.FD > 0 && FD_ISSET(client.FD, &read_fd)) {
	memset(buf,0,ISIS_MSGSIZE);
	if (ReadClientSocket(&client,buf)>0) {
	  if (client.isVerbose) printf("IN: %s\n",buf);
	  SocketCommand(buf);
	  rl_refresh_line(0,0);
	}
      }
      
      // XTV event, means refresh the display

      if (tv.FD > 0 && FD_ISSET(tv.FD, &read_fd)) {
	xtv_refresh(0);
      }

      // add any new FD handlers here...
      
    } // end of select() I/O handling checking
    
  } // bottom of the while(client.KeepGoing) loop
  
  //----------------------------------------------------------------
  //
  // If we got here, the client was instructed to shut down
  //

  printf("\nImage Display Client Shutting Down...\n");

  // Tear down the image display
  
  if (tv.FD>0) 
    xtvclose();

  // Tear down the application's client socket

  CloseClientSocket(&client);

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
  char reply[256];
  if (client.Debug)
    printf("Caught Ctrl+C Abort...\n");
  
  printf("Ctrl+C Abort requested - Aborts Sent\n");

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
//   if (ccd.FD > 0) 
//     SCLAbort(ccd.FD); 
//   scl.Abort = 1; 
// } 


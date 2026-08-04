/*!
  \mainpage isisrelay - ISIS UDP/TTY Port Relay

  \author R. Pogge, OSU Astronomy Dept. (pogge@astronomy.ohio-state.edu)
  \date 2014 Oct 8

  \section Usage

  Usage: isisrelay [rcfile]

  Where: \c rcfile is an optional runtime config file to load.  

  By default, isisrelay uses the runtime config file defined by
  #DEFAULT_RCFILE in the client.h header.

  \section Introduction

  ...

  \section Config Runtime Configuration File

  This is a typical runtime config file for the isisrelay agent:
  \verbinclude isisrelay.ini

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
  \brief isisrelay main program and I/O event handler.
*/

#include "isisclient.h"  // ISIS common client library header

#include "relay.h"       // ISIS port relay application header

// Global data structures

isisclient_t client; // ISIS client common data structure
relay_t relay;       // Port relay configuration data structure

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
  char bufStr[ISIS_MSGSIZE];
  int lenBuf;
  int numBytes;

  // select() event handler parameters
  
  fd_set fdList;
  int numReady;
  int numSent;
  struct timeval timeout;
  static int sel_wid;

  // Basic initializations
  
  sel_wid = getdtablesize();
 
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
    n = loadConfig((char *)DEFAULT_RCFILE);

  if (n!=0) {
    printf("Unable to load the runtime config file...isisrelay aborting\n");
    exit(1);
  }

  // Now we do various initializations

  // If required, initialize the socket connection to the ISIS server
  // We can disable ISIS interaction by specifying "ServerID None" in
  // the runtime config file

  if (InitISISServer(&client)<0) {
    printf("ISIS server address database initialization failed - aborting\n");
    exit(2);
  }

  // Open the UDP network socket port for the internet-facing side
  // of the relay.  We use the same basic tools as an ISIS client
  // application, even though we are not an ISIS client proper.
  
  if (OpenClientSocket(&client)<0) {
    printf("ISIS Relay UDP socket initialization failed - aborting\n");
    exit(3);
  }
  printf("Started isisrelay UDP Socket %s:%d\n",client.Host,client.Port);

  // Open the TTY socket port

  relay.ttyFD = OpenSerialPort(relay.ttyPort);
  if (relay.ttyFD < 0) {
    printf("ISIS Relay TTY port %s open failed - aborting\n",relay.ttyPort);
    exit(3);
  }

  // Set the TTY attributes.  Speed, Data Bits, Stop Bits, and Parity
  // are defined in the .ini file (default: 9600, 8, 1, 0)

  if (SetSerialPort(relay.ttyFD,relay.ttySpeed,relay.ttyDataBits,
		    relay.ttyStopBits,relay.ttyParity)<0) {
    printf("Could not set ISIS relay TTY port attributes - aborting\n");
    exit(3);
  }

  printf("Connected isisrelay TTY port %s\n",relay.ttyPort);
  printf("  Speed=%d DataBits=%d StopBits=%d Parity=%d\n",
	 relay.ttySpeed,relay.ttyDataBits,relay.ttyStopBits,relay.ttyParity);
  relay.udpFD = client.FD;

  // Set the SIGINT signal trap 
  
  signal(SIGINT,HandleInt); // Ctrl+C sends a move abort to controller
  signal(SIGPIPE,SIG_IGN);  // ignore broken pipes

  //----------------------------------------------------------------------
  //
  // Start the I/O event handling loop.
  //

  client.KeepGoing = 1;

  while (client.KeepGoing) {
    
    FD_ZERO(&fdList); // clear the table of active file descriptors
    
    // listen to the relay UDP and TTY ports
    
    FD_SET(relay.udpFD, &fdList);
    FD_SET(relay.ttyFD, &fdList);
    
    // Do the select() call and wait for activity on any of our comm
    // ports or the console keyboard
     
    numReady = 0;
    numSent = 0;

    // Setup for 120 second idle timeout.  This gives us a possibility
    // of doing light housekeeping (like refreshing the UDP port) as
    // needed when idle for a while.

    timeout.tv_sec = 120;
    timeout.tv_usec = 0;
    numReady = select(sel_wid, &fdList, NULL, NULL, &timeout);
      
    //----------------------------------------------------------------
    //
    // select() done, take action depending on the value of numReady
    // returned
    //

    // select() timed out, do some housekeeping...

    if (numReady == 0) {
      // do housekeeping here...
      continue;
    }
    
    // select() returned an error, handle it
    
    else if (numReady < 0) {
      if (errno == EINTR) { // caught Ctrl+C, hopefully sigint handler caught it
	if (client.Debug)
	  printf("select() interrupted by Ctrl+C...aborting\n");
	exit(1);
      }
      else { // something else bad happened, let us know
	printf("Warning: select() failed - %s - pressing on anyway...\n",
	       strerror(errno));
      }
      continue;
    }
    
    // select() has input to process on one of the input channels
    
    else {
      
      // Input on the UDP socket side of the relay.  Pass it as-is
      // to the TTY Port
      
      if (FD_ISSET(relay.udpFD, &fdList)) {
	memset(buf,0,ISIS_MSGSIZE);
	memset(bufStr,0,ISIS_MSGSIZE);
	if (ReadClientSocket(&client,buf)>0) {
	  lenBuf = strlen(buf);
	  if (relay.verboseMode) {
	    if (lenBuf > 1) {
	      strcpy(bufStr,buf);
	      bufStr[lenBuf-1]='\0';
	      printf("[%d] UDP>> %s >>TTY\n",lenBuf,bufStr);
	    }
	  }
	  // Pass it to the tty port
	  if (lenBuf > 1)
	    numSent = WriteSerialPort(relay.ttyFD,buf);
	}
      }
      
      // Input on the TTY port side of the relay.  Pass it as-is
      // to the UDP Port

      if (FD_ISSET(relay.ttyFD, &fdList)) {
	memset(buf,0,ISIS_MSGSIZE);
	memset(bufStr,0,ISIS_MSGSIZE);
	numBytes = read(relay.ttyFD,buf,ISIS_MSGSIZE);
	if (numBytes < 0) {
	  printf ("Cannot read from %s - %s\n",
		  relay.ttyPort,strerror(errno));
	}
	else {
	  lenBuf = strlen(buf);
	  if (relay.verboseMode) {
	    if (lenBuf > 1) {
	      strcpy(bufStr,buf);
	      bufStr[lenBuf-1]='\0';
	      printf("[%d] UDP<< %s <<TTY\n",lenBuf,bufStr);
	    }
	  }
	  if (lenBuf > 1)
	    numSent = SendToISISServer(&client,buf);
	}

 /*
	if (ReadSerialPort(relay.ttyFD,buf)>0) {
	  lenBuf = strlen(buf);
	  if (relay.verboseMode) {
	    if (lenBuf > 1) {
	      strcpy(bufStr,buf);
	      bufStr[lenBuf-1]='\0';
	      printf("[%d] UDP<< %s <<TTY\n",lenBuf,bufStr);
	    }
	  }
	  if (lenBuf > 1)
	    numSent = SendToISISServer(&client,buf);
	}
 */
      }
      
    } // end of select() I/O handling checking
    
  } // bottom of the while(client.KeepGoing) loop
  
  //----------------------------------------------------------------
  //
  // If we got here, the client was instructed to shut down
  //

  printf("\nISIS Port Relay Shutting Down...\n");

  // Tear down the application's client socket

  CloseClientSocket(&client);
  
  // all done, say goodbye...

  printf("bye\n");
  
  exit(0);

}

//---------------------------------------------------------------------------

/*!
  \brief Service Ctrl+C Interrupts (SIGINT signals)

  SIGINT signal trap for trapping Ctrl+C interrupts.

*/

void
HandleInt(int signalValue)
{
  char reply[256];
  if (client.Debug)
    printf("Caught Ctrl+C Abort...\n");
  
  printf("Ctrl+C Abort requested - Aborts Sent\n");

}

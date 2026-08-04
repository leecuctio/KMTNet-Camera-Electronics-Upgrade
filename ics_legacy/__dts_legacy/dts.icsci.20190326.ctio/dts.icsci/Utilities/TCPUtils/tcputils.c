/*!
  \file tcputils.c
  \brief Generic TCP Socket Client I/O handling utilties.

  This is a set of simple functions for TCP socket client I/O.  The
  library encapsulates a number of useful basic functions for opening,
  closing, setting attributes, reading, writing, and flushing junk from
  TCP client sockets, relieving writers of ISIS client applications from
  the pain of getting all the arcane bits right.  In particular, it
  handles some of the odder buffering issues transparently.

  \author R. Pogge, OSU Astronomy Dept (pogge@astronomy.ohio-state.edu)
  \date 2005 May 2

*/

#include "tcputils.h" // All the header we should need

/*!
  \brief Open a client TCP socket connection
  \param port pointer to a tcpport_t struct with the port configuration
  \return File descriptor of the open comm port connection, or -1 if an error.

  Performs the necessary initialization functions to open a serial port.
  The device name syntax is as follows:
  <pre>
     host:port    = network serial port server address (IP and port #).
  </pre>
  To use, you must fill in the relevant data members of the tcpport_t
  struct.  The port->Host and port->Port members are used to define the
  server TCP address.

  For socket communications we use INET streams (SOCK_STREAM) with a
  persistent client connection.  

  \sa CloseTCPPort(), SetTCPPort()
*/

int
OpenTCPPort(tcpport_t *port)
{ 
  int portFD = -1;

  // sockaddr and hostent structs for the TCP Server

  char hostID[64];
  int portID;
  struct sockaddr_in PortServer;
  int PortServer_len;
  struct hostent *PortHost;

  // The server hostname better be plausible

  if (strlen(port->Host)<=0) {
    printf("ERROR(OpenTCPPort): TCP server hostname NULL!\n");
    return -1;
  }

  strcpy(hostID,port->Host);
  portID = port->Port;

  // Try to resolve the network port server's host ID.  If not resolvable
  // we're screwed - abort with informative error messages.

  if (!(PortHost=gethostbyname(hostID))) {
    printf("ERROR(OpenTCPPort): Cannot resolve network serial port server hostname %s - %s\n",
	   hostID,hstrerror(h_errno));
    return -1;
  }

  // Initialize the network serial port attributes

  if (port->FD > 0) {
    close(port->FD);
    port->FD = -1;  // the no-port value
  }

  // Build the sockaddr database: protocol family is AF_INET

  PortServer.sin_family = AF_INET;
  memcpy(&PortServer.sin_addr,PortHost->h_addr, PortHost->h_length); 
  PortServer.sin_port = htons(portID);

  // Get a socket: all network serial port servers we've encountered thus
  // far use INET streams.  Not sure UDP datagrams would work...

  portFD = socket(AF_INET,SOCK_STREAM,0);
  if (portFD < 0) {
    printf("ERROR(OpenTCPPort): Cannot open socket for network port server %s:%d - %s\n",
	   hostID,portID,strerror(errno));
    return -1;
  }

  // Connect to the network serial port server

  if (connect(portFD,(struct sockaddr *) &PortServer, sizeof(PortServer))<0) {
    printf("ERROR(OpenTCPPort): Cannot connect to network port server %s:%d - %s\n",
	   hostID,portID,strerror(errno));
    close(portFD);
    return -1;
  }
  
  // Make sure this port is non-blocking

  fcntl(portFD,F_SETFL,O_NONBLOCK);

  // Success: return the file descriptor of the open comm port
  
  port->FD = portFD;

  return 0;

}

/*!
  \brief Close an open client socket.

  \param port pointer to a tcpport_t struct with the port parameters
  (see OpenTCPPort())
  
  Closes an open serial port.  Used as a simple wrapper for the close()
  function to provide a logical functional opposite to OpenTCPPort().
  Also sets the FD and Interface data members of the port struct to
  indicate that the port is closed and its interface is unknown.  Other
  attributes (Speed, etc. as relevant) are left alone to permit the user
  to preserve memory of these if they wish.

*/

void
CloseTCPPort(tcpport_t *port) 
{
  if (port->FD > 0)
    close(port->FD);
  port->FD = -1;
}
  
/*!
  \brief Write a character string to the TCP server

  \param port pointer to a tcpport_t struct with the port parameters
  \param msgstr message string to write
  \return Number of bytes written if successful, 0 or -1 if unsuccessful.

  Writes the message string provided to the serial port described by the
  port struct.  This serial port must have been previously opened and
  setup using the OpenTCPPort() function.

  \sa ReadTCPPort()
*/

int  
WriteTCPPort(tcpport_t *port, char *msgstr)
{
  int nsent = 0;

  nsent = write(port->FD,msgstr,strlen(msgstr));
  if (nsent < 0) 
    printf("ERROR(WriteTCPPort()) - Cannot write to TCP server %s:%d - %s\n",
	   port->Host,port->Port,strerror(errno));
  return nsent;

}

/*!
  \brief Read data from a TCP server socket 

  \param port Pointer to a tcpport_t struct with the port parameters
  \param msgstr Message string to carry the input string
  \param timeout Wait timeout seconds for input

  \return The number of characters read, or <0 if an error.  -1 on error
  or timeout, with \e msgstr containing the error message text.

  Uses select() to read data from the specified comm port with the
  timeout interval specified.  Note that because TCP sockets are streams
  rather than line-buffered, the data can arive in bursts depending on
  the system state and the degree of stream synchronization.  As such we
  read in chunks of data w/o blocking until we have read everything from
  the port, which means looking for the \\r (ASCII 13 = Ctrl+M) or \\n
  terminator.  This makes the logic tricky, but robust against most comm
  glitches.  Use of a timeout allows us to break out of cases where the
  message is unterminated because of a comm fault, not because of the
  usual stream buffering/sync issues.

  \note 
  If select() is interrupted by Ctrl+C, it returns an error message in the
  \e reply string.

*/

int  
ReadTCPPort(tcpport_t *port, char *msgstr, long timeout)
{
  int keepReading;
  char inbuf[256];  // working buffer
  int lastchar;

  // for select()

  fd_set readfds;     
  int nready;
  struct timeval tv;

  // timeout interval is given in seconds.  if <0 or 0, set to 0, which
  // means we are polling the port

  if (timeout <= 0L) {
    tv.tv_sec = 0;
    tv.tv_usec = 0;
  }
  else {
    tv.tv_sec = timeout;
    tv.tv_usec = 0;
  }

  memset(inbuf,0,sizeof(inbuf));

  keepReading = 1;

  while (keepReading) {

    // we use a select() call to enable read with timeout

    FD_ZERO(&readfds);  // clear file descriptors
    FD_SET(port->FD,&readfds);

    // select() returns <0 if interrupted by a signal before the timeout
    // interval has expired, or if an error occurs, otherwise it returns
    // 0 when a timeout occurs, or >0 if it got something

    nready = select(port->FD+1,&readfds,(fd_set *)NULL, (fd_set *)NULL, &tv);

    if (nready < 0) {
      if (errno == EINTR) { // got a Ctrl+C interrupt
	sprintf(msgstr,"(ReadTCPPort) Socket %s:%d read aborted Ctrl+C",
		port->Host,port->Port);
	return -1;
      }
      sprintf(msgstr,"(ReadTCPPort) Socket %s:%d read select() error - %s",
	      port->Host,port->Port,strerror(errno));
      return -1;
    }
    else if (nready == 0 && timeout > 0L) {
      sprintf(msgstr,"(ReadTCPPort) Socket %s:%d read timed out after %d sec",
	      port->Host,port->Port,timeout);
      return -1;
    }
    else { 
      if (FD_ISSET(port->FD,&readfds)) {
	memset(inbuf,0,sizeof(inbuf));
	if (read(port->FD,inbuf,sizeof(inbuf))<0) {
	  sprintf(msgstr,"(ReadTCPPort) Cannot read socket %s:%d - %s",
		  port->Host,port->Port,strerror(errno));
	  return -1;
	}
	
	// Now the fun bit, this is a stream terminated by either
	// \r or \n, and since we're not line-buffered, we have to buffer
	// ourselves on account of lack of stream synch etc.

	if (strlen(inbuf) > 0) {
	  strcat(msgstr,inbuf);  
	  lastchar = strlen(msgstr)-1;
	  // if the last char is \r or \n the string is complete then
	  // null terminate & return
	  if (msgstr[lastchar]=='\r' || msgstr[lastchar]=='\n') {
	    msgstr[lastchar]='\0'; 
	    return strlen(msgstr);
	  }
	}
      }
    }

  } // select() event loop

  return 0;

}


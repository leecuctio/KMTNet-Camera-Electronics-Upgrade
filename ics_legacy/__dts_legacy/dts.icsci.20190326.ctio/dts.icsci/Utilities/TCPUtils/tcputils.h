#ifndef TCPUTILS_H
#define TCPUTILS_H

//
// tcputils.h - TCP Socket Client Parameter Table Header
//

/*!
  \file tcputils.h
  \brief TCP Socket Client I/O Utilties header

  \author R. Pogge, OSU Astronomy Dept. (pogge@astronomy.ohio-state.edu)
  \date 2005 May 2

  \par Modification History:
<pre>
</pre>
*/

// System header files 

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <sys/time.h>
#include <sys/times.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/file.h>
#include <netdb.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <termios.h>
#include <fcntl.h>
#include <signal.h>
#include <math.h>

//----------------------------------------------------------------
//
// tcpport: serial port configuration struct
//


/*!
  \brief TCP Socket Port Configuration Table

  Contains the configuration of a tcp socket client

*/

typedef struct tcpport {
  char   Host[64]; //!< Host name of the TCP server
  int    Port;     //!< Port number of the TCP server socket
  int    FD;       //!< File descriptor of the open client port, -1 = closed
} tcpport_t;

// tcputils Function Prototypes

int OpenTCPPort(tcpport_t *);
void CloseTCPPort(tcpport_t *);
int WriteTCPPort(tcpport_t *, char *);
int ReadTCPPort(tcpport_t *, char *, long);

#endif  // TCPUTILS_H

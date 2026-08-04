#ifndef TTYUTILS_H
#define TTYUTILS_H

//
// ttyutils.h - Serial Port (tty) Parameter Table Header
//

/*!
  \file ttyutils.h
  \brief Serial (TTY) Port I/O Utilties header

  \author R. Pogge, OSU Astronomy Dept. (pogge@astronomy.ohio-state.edu)
  \date 2004 Mar 13

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
// ttyport: serial port configuration struct
//


/*!
  \brief Serial (TTY) Port Configuration Table

  Contains the configuration of a serial port.

*/

typedef struct ttyport {
  char   Port[64];    //!< Port name (e.g., /dev/tty1 or host:port)
  int    Interface;   //!< Interface Type: one of TTY_SERIAL/TTY_NETWORK/TTY_UNKNOWN
  int    FD;          //!< File descriptor of the open port, 0 = closed
  int    Speed;       //!< Port Speed if Interface=TTY_SERIAL, one of (1200,2400,4800,9600,19200,38400)
  int    DataBits;    //!< Port data bits if Interface=TTY_SERIAL, range: 5..8
  int    StopBits;    //!< Port stop bits if Interface=TTY_SERIAL, values: 1 or 2
  int    Parity;      //!< Enable parity generation/checking if Interface=TTY_SERIAL, values: 0 or 1
} ttyport_t;

// Serial Port Parameters

#define TTY_UNKNOWN 0 //!< Port interface unknown (should be starting default)
#define TTY_SERIAL  1 //!< Port is a direct serial device on the host computer
#define TTY_NETWORK 2 //!< Port is a serial port connected through a TCP network port server

// TTYUtils Function Prototypes

int OpenTTYPort(ttyport_t *);
int SetTTYPort(ttyport_t *);
void CloseTTYPort(ttyport_t *);
int WriteTTYPort(ttyport_t *, char *);
int ReadTTYPort(ttyport_t *, char *, long);
void FlushTTYPort(ttyport_t *, int);
int TTYMSleep(long);

#endif  // TTYUTILS_H

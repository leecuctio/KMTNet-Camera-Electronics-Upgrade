/* Ping Routine                                                                  */
/* Purpose: Handles PING command received from serial port by replying with PONG */
/* Requires: Port number and host to receive pong                                */
/* Returns: Nothing                                                              */

#include "Caliban.h"

void Ping(int port, char *host)
{
  XmitMsg(port, host, "%s", "PONG");  /* Pong originator                         */
}

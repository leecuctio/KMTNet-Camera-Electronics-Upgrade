/* Pong Routine                                                                  */
/* Purpose: Handles incoming PONG messages by displaying them on screen          */
/* Requires: Port number and host to receive pong                                */
/* Returns: Nothing                                                              */

#include "Caliban.h"

void Pong(char *host)
{
  ConsoleMsg("Received Pong from %s\n", host);
  XmitMsg(systab->fd_serial, host, "%s", "STATUS: MACHINETYPE=DOWNSTREAM");
}

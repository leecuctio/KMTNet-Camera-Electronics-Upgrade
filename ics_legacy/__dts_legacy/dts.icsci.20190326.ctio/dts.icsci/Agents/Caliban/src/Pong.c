/* Pong Routine                                                                  */
/* Purpose: Handles incoming PONG messages by displaying them on screen          */
/* Requires: Port number and host to receive pong                                */
/* Returns: Nothing                                                              */

#include "Caliban.h"

void Pong(int port, char *host)
{
  ConsoleMsg("Received Pong from %s", host);
  XmitMsg(port, host, "%s", "STATUS: MACHINETYPE=DOWNSTREAM");
}

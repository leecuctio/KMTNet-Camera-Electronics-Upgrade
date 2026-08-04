// CBStatus Routine
// Purpose: Handles CBStatus command received from serial port by
//          replying with status
// Requires: Port number and host to receive status
// Returns: Nothing
//

#include "Caliban.h"

void 
CBStatus(int port, char *host)
{
  char msg[MED_STR_SIZE];

  sprintf(msg, "DONE: AUTOLOG=%c DISPLAY=%c ADDFITS=%c ARCHIVE=%c NOSWAP=%c INTERFACE=%s %s", 
	  (systab->doautolog == cb_TRUE ? 'T' : 'F'), 
	  (systab->dodisplay == cb_TRUE ? 'T' : 'F'), 
	  (systab->addfits == cb_TRUE ? 'T' : 'F'), 
	  (systab->doarchive == cb_TRUE ? 'T' : 'F'), 
	  (systab->noswap == cb_TRUE ? 'T' : 'F'),
	  (systab->diskinterface == SERIAL ? "Serial" : "Network"),
	  (systab->doAckSwap ? "+AckSwap" : "-AckSwap"));
  XmitMsg(port, host, "%s", msg);
}

/* Status Routine                                            */
/* Purpose: Displays incoming status messages on the console */
/* Requires: Status message buffer                           */
/* Returns: Nothing                                          */

#include "Caliban.h"

void Status(char *host, char *status)
{
  char buf[MED_STR_SIZE];
  char buf2[MED_STR_SIZE];
  char *pbuf;

  ConsoleMsg("%s", status);
 
  GetArg(status, 3, buf);
  UpperCase(buf);
  pbuf = (char *)buf;

  if (strlen(pbuf) >= 20) {
    if (strncmp(pbuf, "MACHINETYPE=", 12)==0) {
      pbuf += 12;

      GetArg(status, 4, buf2);

      if(strncmp(buf2, "PONG", 4)!=0) {
	if (strncmp(pbuf, "UPSTREAM", 8)==0) {
	  pbuf += 8;
	  if (disktab->ackdisk)
	    XmitMsg(systab->fd_serial, host, "%s", "STATUS: MachineType=Downstream PONG");
	  else
	    XmitMsg(systab->fd_serial, systab->serialhost, "%s", "REQ INITDISK");
	  
	}
	else if (strncmp(pbuf, "SWITCHED", 8)==0) {
	  pbuf += 8;
	  if (disktab->ackdisk)
	    XmitMsg(systab->fd_serial, host, "%s", "STATUS: MachineType=Downstream PONG");
	  else
	    XmitMsg(systab->fd_serial, systab->serialhost, "%s", "REQ INITDISK");
	}
	else if (strncmp(pbuf, "DOWNSTREAM", 10)==0) {
	  XmitMsg(systab->fd_serial, host, "%s", "STATUS: MachineType=Downstream PONG");      
	}
      }
    }
  }
}





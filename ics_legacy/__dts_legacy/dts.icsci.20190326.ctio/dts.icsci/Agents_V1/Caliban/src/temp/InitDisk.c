/* InitDisk Routine                                                     */
/* Purpose:  Disk synchronization startup routine                       */
/* Requires: Port and host for notification and incoming message buffer */
/* Returns:  Success flag                                               */

#include "Caliban.h"

int InitDisk(int port, char *host, char *inbuf)
{
  int lcv;                    /* Loop control variable */
  char argbuf[MED_STR_SIZE];  /* Argument buffer       */

  /* Embedded in the input buffer are the maximum FITS header and data  */
  /* segment sizes to use                                               */

  GetArg(inbuf, 4, argbuf);
  systab->headlng = atoi(argbuf);
  GetArg(inbuf, 5, argbuf);
  systab->datalng = atoi(argbuf);

  if(systab->headlng<=0 || systab->datalng<=0)
    {
      XmitMsg(port, host, "%s", "ERROR: Invalid FITS block parameters.  Unable to synchronize disks");
      return(SYSERR);
    }

  systab->maxcards = systab->headlng * BLOCK_SIZE / 80; /* Maximum number of FITS cards possible in one file */

  disktab->ackdisk = cb_FALSE; /* Indicate that successful disk synchronization has not yet occurred */

  /* Loop through the available disks we can see and report them to the downstream host */

  for(lcv=0;lcv<disktab->numdisks;lcv++)
    {
      if(disktab->valid[lcv] == cb_TRUE)
	{
	  XmitMsg(port, host, "FOUND %s", disktab->disk[lcv]);
	}
    }

  XmitMsg(port, host, "%s", "FOUND ALL"); /* Done listing disk devices */

  return(cb_OK);
}

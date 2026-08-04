/* UseDisk Routine                                                           */
/* Purpose: Establishes which disk(s) can be shared                          */
/* Requires: Port number, host to be notified, and original input buffer     */
/* Returns: Nothing                                                          */

#include "Caliban.h"

void UseDisk(int port, char *host, char *inbuf)
{
  int lcv;                    /* Loop control variable                        */
  char argbuf[MED_STR_SIZE];  /* Generic argument buffer                      */

  /* Loop through the available disks and check to see if the device reported */
  /* for use by the downstream host is valid, and if so, note the alias in    */
  /* the disk table for future use                                            */

  for(lcv=0; lcv<disktab->numdisks; lcv++)
    {
      GetArg(inbuf, 4, argbuf);

      if((strncmp(argbuf, disktab->disk[lcv], strlen(disktab->disk[lcv]))==0) && disktab->valid[lcv]==cb_TRUE)
	{
	  disktab->use[lcv] = cb_TRUE;  /* Mark the device as synchronized    */

	  GetArg(inbuf, 3, argbuf);

	  sprintf(disktab->alias[lcv], argbuf);    /* Record alias            */
	  XmitMsg(port, host, "USING %s", argbuf); /* Final confirmation      */
	}
    }
}

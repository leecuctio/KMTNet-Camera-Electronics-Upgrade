/* TransferDisk Routine                                               */
/* Purpose: Initiates transfer of one or more files from spool device */
/* Requires: Port number and original command buffer                  */
/* Returns: Nothing                                                   */

#include "Caliban.h"

void TransferDisk(int port, char *inbuf)
{
  int lcv;                           /* Loop control variable                      */ 
  int valid=0;                       /* Valid disk device indicator                */
  int numfiles;                      /* Number of files to transfer                */
  int numxferd;                      /* Number of files successfully transferred   */
  char alias[SHORT_STR_SIZE];        /* Alias by which we refer to the disk device */
  char numfilesstr[SHORT_STR_SIZE];  /* Number of files to transfer                */
  char host[SHORT_STR_SIZE];         /* Host to receive status report              */
  char outstr[MED_STR_SIZE];         /* Buffer for outgoing messages               */
  char argbuf[MED_STR_SIZE];         /* Generic argument buffer for parsing        */

  GetArg(inbuf, 3, argbuf);          /* Parse off disk to transfer from            */
  strcpy(alias, argbuf);
  
  GetArg(inbuf, 4, argbuf);          /* Parse number of files to transfer          */
  strcpy(numfilesstr, argbuf);

#ifdef SHUTUP
  sprintf(host,"%s","WC");
#else
  GetArg(inbuf, 5, argbuf);          /* Parse host name to notify                  */
  strcpy(host,argbuf);
#endif

  numfiles = atoi(numfilesstr);

  /* Check to make sure number of files to transfer is in bounds                   */

  if((numfiles>systab->max_xfer_files) || (numfiles<1))
    {
      XmitMsg(port, host, "ERROR: Number of files to transfer must be between 1 and %d", systab->max_xfer_files);
    }
  else
    {
      /* Search the disk table for the device known as 'alias' */

      for(lcv=0; lcv<MAXDISKS; lcv++)
	{
	  if(strcmp(disktab->alias[lcv], alias)==0)
	    {
	      numxferd = GetFITS(port, host, disktab->device[lcv], alias, numfiles); /* Transfer file(s) */

	      if(numxferd == 0)
		{
		  XmitMsg(port, host, "%s", "ERROR: No files transferred");
		}

	      valid = TRUE;
	      break;
	    }
	}
      if(!(valid))
	{
	  XmitMsg(port, host, "ERROR: Specified disk not synched - %s", alias);
	}
    }
  XmitMsg(port, systab->serialhost, "%s", "REQ SWAP"); /* Tell downstream host it's ok to use the disk again */
}




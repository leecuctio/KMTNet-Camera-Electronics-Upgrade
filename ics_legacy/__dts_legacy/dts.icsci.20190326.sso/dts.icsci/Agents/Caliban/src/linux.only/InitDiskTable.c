/* InitDiskTable Routine                                      */
/* Purpose: Assemble working disk table structure             */
/* Requires: Nothing                                          */
/* Returns: Number of valid spool devices                     */

/* More sophisticated error trapping introduced [rwp/97Apr14]  */

#include "Caliban.h"

int InitDiskTable()
{
  int ifd;                     /* Input file descriptor        */
  int lcv;                     /* Loop control variable        */
  int validdisks=0;            /* Number of valid disk devices */
  char device[MED_STR_SIZE];   /* Physical device name         */
  char diskname[MED_STR_SIZE]; /* Logical device name          */

  disktab->ackdisk = cb_FALSE;  /* Reset acknowledgement flag to prevent transfers before synchronization */

  for(lcv=0; lcv<disktab->numdisks; lcv++) /* Cycle through available devices to test validity */
    {
      bzero(diskname, sizeof(diskname));
      ifd=open(disktab->device[lcv],O_RDWR);
      if (ifd == -1) 
	{
	  disktab->valid[lcv] = cb_FALSE; /* error on open, invalid spool device */
	  ConsoleMsg("ERROR: Invalid spool device %s\n", disktab->device[lcv]);
	  ConsoleMsg("Reason: %s\n", ERRORSTR);
	} 
      else 
	{
	  SGseek(0);
	  SGread(ifd, diskname, 20);

	  if(ifd && (bcmp(diskname, "DISK", 4)==0)) /* A valid spool device is defined by first 4 bytes = "DISK" */
	    {
	      sprintf(disktab->disk[lcv], diskname);
	      disktab->valid[lcv] = cb_TRUE; /* Valid entry */
	      validdisks++;
	      if(ifd!=0)
		close(ifd);
	    }
	  else
	    {
	      disktab->valid[lcv] = cb_FALSE; /* Invalid disk info */
	      ConsoleMsg("ERROR: Invalid disk info on %s\n", disktab->device[lcv]);
	      ConsoleMsg("diskname=%s\n", diskname);
	    }
	}
    }
  return(validdisks); /* Return number of valid spool devices */
}

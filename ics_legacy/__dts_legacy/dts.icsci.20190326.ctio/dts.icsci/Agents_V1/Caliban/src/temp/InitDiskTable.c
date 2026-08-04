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
  char device[MED_STR_SIZE];   /* Physical device name         */
  char diskname[MED_STR_SIZE]; /* Logical device name          */

  disktab->ackdisk = cb_FALSE; /* Reset acknowledgement flag to prevent transfers before synchronization */
  disktab->numvalid = 0;       /* Initially there are no valid disks */  

  for(lcv=0; lcv<disktab->numdisks; lcv++) /* Cycle through available devices to test validity */
    {
      bzero(diskname, sizeof(diskname));
      ifd=open(disktab->device[lcv], cb_FILEMODE);

      if (ifd == -1) 
	{
	  disktab->valid[lcv] = cb_FALSE; /* error on open, invalid spool device */
	  ConsoleMsg("ERROR: Invalid spool device %s", disktab->device[lcv]);
	} 
      else 
	{
	  CBseek(ifd, 0, 0);
	  CBread(ifd, diskname, 20);
	  
	  if(ifd && (bcmp(diskname, "DISK", 4)==0)) /* A valid spool device is defined by first 4 bytes = "DISK" */
	    {
	      sprintf(disktab->disk[lcv], diskname);
	      disktab->valid[lcv] = cb_TRUE; /* Valid entry */
	      (disktab->numvalid)++;
	      if(ifd!=0)
		close(ifd);
	    }
	  else
	    {
	      disktab->valid[lcv] = cb_FALSE; /* Invalid disk info */
	      ConsoleMsg("ERROR: Invalid disk info on %s", disktab->device[lcv]);
	      ConsoleMsg("Diskname=%s", diskname);
	    }
	}
    }
  return(disktab->numvalid); /* Return number of valid spool devices */
}

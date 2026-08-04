/* UseMount Routine                                                             */
/* Purpose: Establishes which mount points are valid                            */
/* Requires: Port number, host to be notified, and original input buffer        */
/* Returns: Nothing                                                             */

#include "Caliban.h"

void UseMount(int port, char *host, char *inbuf)
{
  int lcv;                       /* Loop control variable                       */
  int valid=0;                   /* Validity flag                               */
  char mountname[MED_STR_SIZE];  /* Mount point name buffer                     */

  if (disktab->ackdisk != cb_TRUE)
    {
      XmitMsg(port, host, "%s", "ERROR: Disks not synched");
    }
  else
    {
  
      /* Here we recall the mount point name from the original buffer as it was     */
      /* prior to being UpperCase'd.  This preserves UNIX filename case sensitivity */
      
      GetArg(systab->oldinbuf, 4, mountname);

      /* Loop through the available mount points and find the one being requested   */
      /* If it's valid, report that it will be used                                 */
      
      for(lcv=0;lcv<mounttab->nummounts;lcv++)
	{
	  if((strcmp(mounttab->mount[lcv], mountname)==0) && (IsValidMount(mountname)==1))
	    {
	      valid=cb_TRUE;
	      mounttab->current = lcv;
	      XmitMsg(port, host, "STATUS: Path=%s", mountname);
	      XmitMsg(port, systab->serialhost, "%s", "REQ SWAP");
	    }
	}
      
      if(valid==cb_FALSE)
	{
	  XmitMsg(port, host, "ERROR: Invalid mount point (%s)--%s", mountname, ERRORSTR);
	}
    }
}

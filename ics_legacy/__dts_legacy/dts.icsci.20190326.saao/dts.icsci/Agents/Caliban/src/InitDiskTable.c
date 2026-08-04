// InitDiskTable Routine                                     
// Purpose: Assemble working disk table structure            
// Requires: Nothing                                         
// Returns: Number of valid spool devices                    
//
// More sophisticated error trapping introduced [rwp/97Apr14] 
//

#include "Caliban.h"

int 
InitDiskTable()
{
  int ifd;                     // Input file descriptor       
  int lcv;                     // Loop control variable       
  char device[MED_STR_SIZE];   // Physical device name        
  char diskname[MED_STR_SIZE]; // Logical device name         
  long nch;

  // Reset acknowledgement flag to prevent transfers before
  // synchronization.  Initially there are no valid disks

  disktab->ackdisk = cb_FALSE; 
  disktab->numvalid = 0;

  // Cycle through available devices to test validity

  for(lcv=0; lcv<disktab->numdisks; lcv++) {
#ifdef __DEBUG
    ConsoleMsg("Opening device %s",disktab->device[lcv]);
#endif
    memset(diskname,0,sizeof(diskname));
    ifd=open(disktab->device[lcv], cb_FILEMODE);

    if (ifd == -1) {
      disktab->valid[lcv] = cb_FALSE; // error on open, invalid spool device
      ConsoleMsg("ERROR: Invalid spool device %s", disktab->device[lcv]);
      ConsoleMsg("       Reason: %s",strerror(errno));
    } 
    else {
      CBseek(ifd, 0, 0);
      nch = CBread(ifd, diskname, 20);
      if (ifd && (bcmp(diskname, "DISK", 4)==0)) {
	sprintf(disktab->disk[lcv], diskname);
	disktab->valid[lcv] = cb_TRUE; // Valid entry
	(disktab->numvalid)++;
	if(ifd!=0)
	  close(ifd);
#ifdef __DEBUG
	ConsoleMsg("Valid disk header found on %s",disktab->device[lcv]);
#endif
      }
      else {
	disktab->valid[lcv] = cb_FALSE; // Invalid disk info
	ConsoleMsg("ERROR: Invalid disk info on %s", disktab->device[lcv]);
	ConsoleMsg("Diskname=%s", diskname);
      }
    }
  }
  return(disktab->numvalid); // Return number of valid spool devices
}

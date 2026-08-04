// TransferDisk Routine                                               
// Purpose: Initiates transfer of one or more files from spool device 
// Requires: Port number and original command buffer                  
// Returns: Nothing                                                   

#include "Caliban.h"

void TransferDisk(int port, char *inbuf)
{
  int lcv;                           // Loop control variable                       
  int valid=0;                       // Valid disk device indicator                
  int numfiles;                      // Number of files to transfer                
  int numxferd;                      // Number of files successfully transferred   
  char alias[SHORT_STR_SIZE];        // Alias by which we refer to the disk device 
  char numfilesstr[SHORT_STR_SIZE];  // Number of files to transfer                
  char host[SHORT_STR_SIZE];         // Host to receive status report              
  char outstr[MED_STR_SIZE];         // Buffer for outgoing messages               
  char argbuf[MED_STR_SIZE];         // Generic argument buffer for parsing        

  // Parse the arguments in inbuf

  GetArg(inbuf, 3, argbuf);          // Parse the ID of the source disk
  strcpy(alias, argbuf);
  
  GetArg(inbuf, 4, argbuf);          // Parse number of files to transfer          
  strcpy(numfilesstr, argbuf);

#ifdef SHUTUP
  sprintf(host,"%s","WC");
#else
  GetArg(inbuf, 5, argbuf);          // Parse host name to notify                  
  strcpy(host,argbuf);
#endif

  numfiles = atoi(numfilesstr);

  if (systab->debug == cb_TRUE) {
    sprintf(outstr, "TRANSFER requests we move %d file(s)", numfiles);
    ConsoleMsg("%s", outstr);
  }

  // Check to make sure number of files to transfer is in bounds                   

  if ((numfiles>systab->max_xfer_files) || (numfiles<1)) {
    if (systab->debug == cb_TRUE) {
      sprintf(outstr, "Bogus number of files to transfer: %d", numfiles);
      ConsoleMsg("%s", outstr);
    }
    XmitMsg(port, host, "ERROR: Number of files to transfer (%s) outside bounds", numfilesstr);
  }
  else {  // Search the disk table for the device known as 'alias'
    for (lcv=0; lcv<MAXDISKS; lcv++) {
      if (strcmp(disktab->alias[lcv], alias)==0) { // Transfer Files
	numxferd = GetFITS(port, host, disktab->device[lcv], alias, numfiles);
	if (numxferd == cb_FATAL) {
	  XmitMsg(port, host, "%s", "ERROR: A fatal error has occurred while writing to disk.  Recover the disk and issue the +SWAP command at the Caliban console to continue.");
	  // Don't allow further transfers until the RESTORE command resets this flag 
	  systab->noswap = cb_TRUE; 
	}
	valid = cb_TRUE;
	break;
      }
    }
    if (!(valid))
      XmitMsg(port, host, "ERROR: Specified disk not synched - %s", alias);

  }

  // Tell the downstream host that it is OK to use the disk again

  if (systab->noswap==cb_FALSE) {
    XmitMsg(systab->fd_disk, systab->diskhost, "%s", "REQ SWAP");
    systab->reqswap = 1;
    systab->nreqswap = 1;
  }

}




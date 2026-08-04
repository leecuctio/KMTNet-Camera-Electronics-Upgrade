// ParseIniFile Routine                                                                
// Purpose: Parses initialization file to set up initial state configuration structures
// Requires: Nothing                                                                   
// Returns: Nothing                                                                    

#include "Caliban.h"

void 
ParseIniFile()
{
  int lcv;                             // Loop control variable                        
  char keyword[MED_STR_SIZE];          // File is organized into KEYWORD VALUE pairs   
  char argbuf[MED_STR_SIZE];           // Generic argument buffer                      
  char inbuf[BUF_SIZE];                // Generic input buffer                         
  char longarg[MED_STR_SIZE];          // real long argument buffer
  FILE *rfp;                           // Initialization file pointer                  

  // Open initialization file

  if(!(rfp=fopen(systab->inifilename, "r"))) {
    MAGTEXT;
    printf("Unable to open initialization file %s - %s\n", systab->inifilename, ERRORSTR);
    printf("Caliban aborting...\n");
    TXTRESET;
    exit(SYSERR);
  }
  else {

    // Loop through file reading 80 byte blocks at a time

    while(fgets(inbuf, 80, rfp)) {   

      if((inbuf[0]!='#') && (inbuf[0]!='\n') && inbuf[0]!=NUL) { // Skip comments and blank lines               
	inbuf[80] = NUL;
	GetArg(inbuf, 1, argbuf);
	strcpy(keyword, argbuf);
	UpperCase(keyword);

	if(strcmp(keyword, "LOCAL_HOST")==0) {  // Local host name                                       
	  GetArg(inbuf, 2, argbuf);
	  sprintf(systab->localhost, argbuf);
	}

	else if (strcmp(keyword, "LOCAL_PORT")==0) { // port # of Caliban
	  GetArg(inbuf, 2, argbuf);
	  systab->clientport = atoi(argbuf);
	}

	else if (strcmp(keyword, "LOG_FILE_NAME")==0) { // Log file name                                         
	  GetArg(inbuf, 2, argbuf);
	  sprintf(systab->logfilename, argbuf);
	}

	// data-transfer disk host information

	else if(strcmp(keyword, "DISK_HOST")==0) { // name of disk transfer host
	  GetArg(inbuf, 2, argbuf);
	  sprintf(systab->diskhost, argbuf);
	}

	else if(strcmp(keyword, "SERIAL_HOST")==0) { // name of disk transfer host
	  GetArg(inbuf, 2, argbuf);
	  sprintf(systab->diskhost, argbuf);
	}

	else if(strcmp(keyword, "DISK_INTERFACE")==0) { // name of disk transfer host comm method
	  GetArg(inbuf, 2, argbuf);
	  if (strcasecmp(argbuf,"serial")==0) {
	    systab->diskinterface = SERIAL;
	  }
	  else if (strcasecmp(argbuf,"socket")==0) {
	    systab->diskinterface = SOCKET;
	  } 
	  else {
	    MAGTEXT;
	    printf("ERROR: DISK_INTERFACE must be one of SERIAL or SOCKET\n");
	    printf("       Error in initialization file - Caliban aborting.\n");
	    TXTRESET;
	    exit(1);
	  }
	}

	// Serial port interface

	else if(strcmp(keyword, "SERIAL_PORT")==0) { // Serial port device name                               
	  GetArg(inbuf, 2, argbuf);		      
	  sprintf(systab->serialdev, argbuf);
	  systab->useserial = cb_TRUE;
	}

	// ISIS server socket interface stuff

	else if(strcmp(keyword, "SERVER_HOST")==0) { // name of ISIS server
	  GetArg(inbuf, 2, argbuf);
	  sprintf(systab->sockethost, argbuf);
	  systab->usesocket = cb_TRUE;
	}

	else if (strcmp(keyword, "SERVER_IP")==0) { // network hostname of ISIS server
	  GetArg(inbuf, 2, argbuf);
	  sprintf(systab->serverIPaddr, argbuf);
	  systab->usesocket = cb_TRUE;
	}

	else if (strcmp(keyword, "SERVER_PORT")==0) { // port # of ISIS server
	  GetArg(inbuf, 2, argbuf);
	  systab->serverport = atoi(argbuf);
	  systab->usesocket = cb_TRUE;
	}

	// data-transfer disk information

	else if(strcmp(keyword, "SPOOL_DEVICE")==0) { 
	  GetArg(inbuf, 2, argbuf);		      
	  sprintf(disktab->device[disktab->numdisks], argbuf);
	  disktab->numdisks++; 
	}

	// mount-point table entry

	else if(strcmp(keyword, "MOUNT")==0) {
	  GetArg(inbuf, 2, argbuf);
	  sprintf(mounttab->mount[mounttab->nummounts], argbuf);
	  if(IsValidMount(mounttab->mount[mounttab->nummounts])==cb_TRUE) // Validate mount point         
	    mounttab->nummounts++; // Increment count of valid mount points
	  else
	    BZero(mounttab->mount[mounttab->nummounts], sizeof(mounttab->mount[mounttab->nummounts])); 
	}

	// runtime configuration flags

	else if(strcmp(keyword, "VERBOSE")==0) {     // Enable verbose mode                                   
	  systab->verbose = cb_TRUE;
	}

	else if(strcmp(keyword, "DEBUG")==0) {       // Enable debug mode                                     
	  systab->debug = cb_TRUE;
	}

	else if(strcmp(keyword, "DOARCHIVE")==0) {   // Enable archiving                                      
	  systab->doarchive = systab->olddoarchive = cb_TRUE;
	}

	else if(strcmp(keyword, "ARCHIVE_CMD")==0) { // archive command
	  sscanf(inbuf,"%s %[^\n]",argbuf,systab->archivecmd);
	  systab->doarchive = systab->olddoarchive = cb_TRUE;
	}

	else if(strcmp(keyword, "DOAUTOLOG")==0) {   // Enable autologging                                    
	  systab->doautolog = systab->olddoautolog = cb_TRUE;
	}

	else if(strcmp(keyword, "AUTOLOG_CMD")==0) { // autolog command
	  sscanf(inbuf,"%s %[^\n]",argbuf,systab->autologcmd);
	  systab->doautolog = systab->olddoautolog = cb_TRUE;
	}

	else if(strcmp(keyword, "DODISPLAY")==0) {   // Enable auto display of images                         
	  systab->dodisplay = systab->olddodisplay = cb_TRUE;
	}

	else if(strcmp(keyword, "DISPLAY_CMD")==0) { // display command
	  sscanf(inbuf,"%s %[^\n]",argbuf,systab->displaycmd);
	  systab->dodisplay = systab->olddodisplay = cb_TRUE;
	}

	else if(strcmp(keyword, "ADDFITS")==0) {     // Add .fits filename extension                          
	  systab->addfits = systab->oldaddfits = cb_TRUE;
	}

	else if(strcmp(keyword, "BLOCK_SIZE")==0) {  // FITS file block size
	  GetArg(inbuf, 2, argbuf);
	  systab->blocksize = atoi(argbuf);
	}	

	else if(strcmp(keyword, "DBG_HEADLNG")==0) { // Default FITS Header Unit length before synchronization
	  GetArg(inbuf, 2, argbuf);
	  systab->headlng = atoi(argbuf);
	}

	else if(strcmp(keyword, "DBG_DATALNG")==0) { // Default FITS Data Unit length before synchronization  
	  GetArg(inbuf, 2, argbuf);
	  systab->datalng = atoi(argbuf);
	}

	else if(strcmp(keyword, "MAX_XFER_FILES")==0) { // Max number of files transferrable at one time     
	  GetArg(inbuf, 2, argbuf);		      
	  systab->max_xfer_files = atoi(argbuf);
	}

	else if(strcmp(keyword, "ACKSWAP")==0) { // Enable ACK SWAP handling
	  systab->doAckSwap = 1;
	}
	
	else if(strcmp(keyword, "TIMEOUT")==0) { // REQ ACK Timeout interval
	  GetArg(inbuf, 2, argbuf);
	  systab->timeout = (long)(atoi(argbuf));
	  if (systab->timeout <=0) {
	    systab->timeout = 5;
	    CYATEXT;
	    printf("***WARNING: Invalid TIMEOUT in config file, set TIMEOUT=%d sec",
		   systab->timeout);
	    TXTRESET;
	  }	
	}

	else {// Unrecognized entry handler
	  ConsoleMsg("Ignoring unrecognized entry in initialization file - %s", inbuf);
	}
      }
      memset(inbuf, 0, sizeof(inbuf));
    }
  }
  
  if(rfp!=0)
    fclose(rfp); 
  
}

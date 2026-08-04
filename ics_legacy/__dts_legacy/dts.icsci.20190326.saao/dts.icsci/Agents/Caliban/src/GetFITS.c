// GetFITS Routine 
//
// Purpose: Actual FITS file acquisition and structuring routine
//
// Requires: Port number, host to notify, spool device name and alias
// name, and number of files to xfer
//
// Returns: Nothing

#include "Caliban.h"
#include <sys/times.h>
#include <time.h>

double FineSysTime(void);

int 
GetFITS(int port, char *host, char *devicename, char *alias, int numfiles)
{
  int ifd, ofd;                   // Input and output file descriptors                     
  int headsize;                   // FITS header unit size in bytes                        
  int numcards=0;                 // FITS header card counter                              
  int bitpix;                     // FITS bits per pixel                                   
  int lcv;                        // Local loop control variable                           
  int gfcv;                       // Loop control varible for multiple file gets           
  int invalid=0;                  // Invalid flag                                          
  int numxferd=0;                 // Number of files successfully transferred              
  int chksum=0;                   // Checksum flag                                         
  int charsin, charsout;          // Number of characters read/wrote during r/w operations 
  int done=0;                     // Done flag                                             
  long datasize;                  // FITS data unit size in bytes                          
  long naxis1, naxis2;            // FITS axis values                                      
  char inbuf[513];                // Generic buffer                                        
  char *headbuf;                  // Variable length buffer used to transfer header        
  char databuf[FITS_DATA_BLOCK_SIZE+1]; // Buffer used to transfer data in 8K chunks       
  char argbuf[MED_STR_SIZE];      // Argument buffer for GetArg calls                      
  char logstr[MED_STR_SIZE];      // Log message buffer                                    
  char outbuf[MED_STR_SIZE];      // General purpose buffer used in ConsoleMsg calls       
  char pad[FITS_BLOCK_SIZE];      // Padding to accomodate FITS file structure requirements
  char filename[MED_STR_SIZE];    // target file name
  char uniquename[MED_STR_SIZE];  // fallback unique name
  double bytes, rate;             // Used in calculating throughput rate                   
  double before;                  // Time structures for use in timing throughtput         
  double after;                   //                                                       
  struct stat sbuf;               // File statistics buffer                                
  struct timeval tp;
  char lprcmd[MED_STR_SIZE];      // Archive command                                       
  FILE *lprpipe;                  // Shell pipe handle for archive command                 
  FILE *alogpipe;                 // Shell pipe handle for autolog command                 

  long header_addr;  // disk address of the first byte of a header section, in bytes
  long image_addr;   // disk address of the first byte of an image section, in bytes

  double ts0, ts1, dt;

  if ((ifd=open(devicename, cb_FILEMODE))==cb_ERROR) { // Attempt to open the spool device  
    XmitMsg(port, host, "ERROR: Unable to open spool device %s--%s", 
	    devicename, ERRORSTR);
    return(SYSERR);
  }

  for (gfcv=0;gfcv<numfiles;gfcv++) { // Loop numfiles times 
    systab->headwritten = 0;
    systab->datawritten = 0;

    if (systab->verbose == cb_TRUE) {
      sprintf(outbuf, "Initiating file transfer iteration #%d...", gfcv+1);
      ConsoleMsg("%s", outbuf);
    }

    // query the time clock for this transfer 

    before = FineSysTime();

    //
    // The first sector on the spool device contains a header with the
    // physical drive parameters and an identification string assigned
    // to the data-transfer disk.  Each sector is BLOCK_SIZE bytes long.
    //
    // Valid data begins in the second disk sector and is divided into
    // contiguous header and image sectionss.  The entire data section
    // (header+image) has a size of systab->datalng blocks (sectors),
    // and the header section is systab->headlng blocks (sectors) long.
    // These parameters are communicated to Caliban via the "INIT DISK
    // headlng datalng" command when Caliban handshakes with the data
    // host.
    //
    // For each image we are reading, compute the address of the header
    // and image sections.  The variable "gfcv" is the file counter
    // variable, and runs 0..N(images), in effect the number of previous
    // images read thus far in the loop.  Both are long integers.

    header_addr = (long) (BLOCK_SIZE * (1 + gfcv*systab->datalng));
    image_addr  = (long) (BLOCK_SIZE * (1 + gfcv*systab->datalng + systab->headlng));

    if (systab->debug == cb_TRUE) {
      sprintf(outbuf, "Seeking to first header byte %d", header_addr);
      ConsoleMsg("%s", outbuf);
      ts0 = FineSysTime();
    }

    CBseek(ifd, header_addr, 0);

    if (systab->debug == cb_TRUE) {
      ts1 = FineSysTime();
      dt = ts1 - ts0;
      sprintf(outbuf, "time to seek = %.6f sec", dt);
      ConsoleMsg("%s", outbuf);

      sprintf(outbuf, "Reading fits header");
      ConsoleMsg("%s", outbuf);
      ts0 = FineSysTime();
    }

    if ((charsin = CBread(ifd, inbuf, 80))==cb_ERROR) { // Attempt to read header data 
      ltos(argbuf, (long) gfcv);
      XmitMsg(port, host, "ERROR: Unable to read FITS header in file #%s, skipping...", argbuf);
      continue;
    }

    if (systab->debug == cb_TRUE) {
      ts1 = FineSysTime();
      dt = ts1 - ts0;
      sprintf(outbuf, "time to read header = %.6f sec", dt);
      ConsoleMsg("%s", outbuf);
    }

    inbuf[80] = NUL; // So string routines won't blow up 

    // The first card of a valid FITS head should contain the word SIMPLE 

    if (strncmp(inbuf, "SIMPLE", 6)!=0) {
      ltos(argbuf, (long) gfcv+1);
      XmitMsg(port, host, "ERROR: No SIMPLE card in FITS file #%s, skipping...", argbuf);
      continue;
    }
      
    numcards = 1;

    bitpix = naxis1 = naxis2 = chksum = done = invalid = 0;
    BZero(filename, sizeof(filename));
    BZero(uniquename, sizeof(uniquename));
    
    // The following loop searches through the FITS header looking for the required 
    // cards.  Each time it finds a required card, it increments a checksum so that 
    // at the end we will know if all required cards were found                     

    while(!done && !invalid) {

      charsin = CBread(ifd, inbuf, 80);
      inbuf[80] = NUL;
      numcards++;

      if (strncmp(inbuf, "BITPIX  =", 9)==0) {       // Read bits-per-pixel value 
	chksum++;
	GetArg(inbuf, 3, argbuf);
	bitpix = atoi(argbuf);
      }
      else if (strncmp(inbuf, "FILENAME=", 9)==0) { // File name card            
	chksum += 2;
	GetArg(inbuf, 2, argbuf);

	if (argbuf[0] == '\'')                           // Make sure first character is a quote 
	  RightStr(filename, argbuf, strlen(argbuf)-1);  // Remove quotes from file name         
	else
	  sprintf(filename, "%s", argbuf);
	if (filename[strlen(filename)-1] == '\'')        // Make sure last character is a quote  
	  LeftStr(argbuf, filename, strlen(filename)-1);
	else
	  sprintf(argbuf, "%s", filename);
	    
	// Add path and .fits extension if enabled 
	if (systab->addfits == cb_TRUE)
	  sprintf(filename, "%s/%s.fits", strstr(mounttab->mount[mounttab->current], "/"), argbuf);
	else
	  sprintf(filename, "%s/%s", strstr(mounttab->mount[mounttab->current], "/"), argbuf);
      }
      else if (strncmp(inbuf, "UNIQNAME=", 9)==0) {         // Unique file name card        
	chksum += 3;
	GetArg(inbuf, 2, argbuf);
	    
	if (argbuf[0] == '\'')                            // Make sure first character is a quote 
	  RightStr(uniquename, argbuf, strlen(argbuf)-1); // Remove quotes from file name         
	else
	  sprintf(uniquename, "%s", argbuf);
	if (uniquename[strlen(uniquename)-1] == '\'')     // Make sure last character is a quote  
	  LeftStr(argbuf, uniquename, strlen(uniquename)-1);
	else
	  sprintf(argbuf, "%s", uniquename);
	    
	// Add path 
	    
	if (systab->addfits == cb_TRUE)
	  sprintf(uniquename, "%s/%s.fits", strstr(mounttab->mount[mounttab->current], "/"), argbuf);
	else
	  sprintf(uniquename, "%s/%s", strstr(mounttab->mount[mounttab->current], "/"), argbuf);
      }
      else if (strncmp(inbuf, "NAXIS1  =", 9)==0) { // Read and convert axis values  
	chksum += 4;
	GetArg(inbuf, 3, argbuf);
	naxis1 = atoi(argbuf);
      }
      else if (strncmp(inbuf, "NAXIS2  =", 9)==0) {
	chksum += 5;
	GetArg(inbuf, 3, argbuf);
	naxis2 = atoi(argbuf);
      }

      else if (strncmp(inbuf, "END ", 4)==0) {
        // new style, avoids sector boundaries - we hope...
	//if (systab->verbose == cb_TRUE)
	//  printf("Found END card, numcards=%d\n",numcards);
        done = cb_TRUE;
      }

      /* 
       * Old Style - badness if we cross a disk sector boundary
      else if (strncmp(inbuf, "END                                                                             ", 80)==0) {
         done = cb_TRUE;
      }
      */

      if (numcards >= systab->maxcards) { // Have we read more header cards than are allowed? 
	REDTEXT;
	printf("ERROR: numcards=%d maxcards=%d\n",numcards,systab->maxcards);
	TXTRESET;
	invalid=cb_TRUE;
      }

    }
      
    if (chksum<15) { // Have we found all required cards? 
      ltos(argbuf, (long) gfcv+1);
      XmitMsg(port, host, 
	      "ERROR: FITS header missing one or more required entries in file #%s, skipping...", argbuf);
      continue;
    }
      
    if (invalid == cb_TRUE) { // A valid FITS header must end with END followed by 77 spaces 
      ltos(argbuf, (long) gfcv+1);
      XmitMsg(port, host, "ERROR: Missing END card in FITS file #%s, skipping...", argbuf);
      continue;
    }
      
    headsize = numcards * 80;                            // Calculate header unit size 
    datasize = (abs(bitpix)/8) * naxis1 * naxis2;        // Calculate data unit size 
      
    if (systab->debug == cb_TRUE) {
      sprintf(pad, "Headsize = %d, Datasize = %d, naxis1 = %d, naxis2 = %d, bitpix = %d\n", 
	      headsize, datasize, naxis1, naxis2, bitpix);
      ConsoleMsg("%s", pad);
    }
      
    //***************************************************************
    // Attempt to open the output file
    //
    // All kinds of things can go wrong here:
    //   a) file already exists - if so, switch to the unique name
    //   b) we are out of disk space on the target disk file system
    //   c) ...
    //
    //**************************************************************

    if ((ofd=open(filename, 2))==cb_ERROR) {
      if ((ofd=creat(filename, 0664))==cb_ERROR)  {
	if ((ofd=creat(uniquename, 0664))==cb_ERROR) {
	  ltos(argbuf, (long) gfcv+1);
	  XmitMsg(port, host, 
		  "ERROR: Cannot create unique FITS file #%s (%s)--%s, skipping...", 
		  argbuf, uniquename, ERRORSTR);
	  continue;
	}
	sprintf(filename, uniquename);
      }
    }
    else {            // Primary name already exists, use unique name 
      if (ofd!=0)
	close(ofd);
      if ((ofd=creat(uniquename, 0664))==cb_ERROR) {
	ltos(argbuf, (long) gfcv+1);
	XmitMsg(port, host, 
		"ERROR: Cannot create unique FITS file #%s (%s)--%s, skipping...", 
		argbuf, uniquename, ERRORSTR);
	continue;
      }
      XmitMsg(port, host, 
	      "WARNING: FITS file '%s' already exists, writing as '%s' instead", 
	      filename,uniquename);
      sprintf(filename, uniquename);
    }

    if (systab->debug == cb_TRUE)
      ConsoleMsg("Created file %s", filename);

    // Check disk space on target mount point - currently disabled [98Sept27/rwp] 

    if (ChkDiskSpace((char *)(mounttab->mount[mounttab->current]), 
		     (long) ((bitpix / 8) * naxis1 * naxis2)) != cb_TRUE) {
      close(ofd);
      XmitMsg(port, host, "FATAL: %s Disk is FULL, write failed", mounttab->mount[mounttab->current]);
      return(cb_FATAL);
    }

    // Go back to the start of the header (BOF), and read in the
    // header and copy it into the output FITS file

    if (systab->debug == cb_TRUE) {
      sprintf(outbuf, "Seeking to BOF at byte %d", header_addr);
      ConsoleMsg("%s", outbuf);
      ts0 = FineSysTime();
    }
      
    CBseek(ifd, header_addr, 0); // Seek to BOF 

    if (systab->debug == cb_TRUE) {
      ts1 = FineSysTime();
      dt = ts1 - ts0;
      sprintf(outbuf, "time to seek = %.6f sec", dt);
      ConsoleMsg("%s", outbuf);
    }

    // Allocate a buffer big enough to transfer the header segment in
    // one chunk

    headbuf = (char *)malloc(headsize+1); 
      
    charsin = CBread(ifd, headbuf, headsize);
    charsout = write(ofd, headbuf, headsize);

    // Check value of charsout.  if -1, a fatal write error occured,
    // check errno code & abort

    if (charsout == -1) {     // error on write() to disk 
      free(headbuf); // Free the allocated header memory 
      close(ofd);
      if (errno == ENOSPC) { // file system full! 
	XmitMsg(port,host,"FATAL: Cannot write %s -- DISK FULL",filename);
      }
      else { // some other fool thing - print error message 
	XmitMsg(port,host,"FATAL: Cannot write %s -- %s",filename,ERRORSTR);
      }
      return(cb_FATAL);
    }	

    systab->headwritten += charsout;

    free(headbuf); // Free the allocated memory 

    if (systab->debug == cb_TRUE) {
      sprintf(outbuf, "Wrote %d header bytes", systab->headwritten);
      ConsoleMsg("%s", outbuf);
    }

    // If headsize is a multiple of FITS_BLOCK_SIZE (2880), don't pad
    // Otherwise, pad header unit out to a multiple of FITS_BLOCK_SIZE
    // with spaces  
    
    if ((headsize%FITS_BLOCK_SIZE)>0) {
      for(lcv=0; lcv < FITS_BLOCK_SIZE-(headsize%FITS_BLOCK_SIZE); lcv++) { 
	pad[lcv] = ' ';                                                 
      }
      
      charsout = write(ofd, pad, lcv);

      if (charsout == -1) {    // error on write() to disk 
	close(ofd);
	if (errno == ENOSPC) { // file system full! 
	  XmitMsg(port,host,"FATAL: Cannot write %s -- DISK FULL",filename);
	}
	else { // some other fool thing - print error message 
	  XmitMsg(port,host,"FATAL: Cannot write %s -- %s",filename,ERRORSTR);
	}
	return(cb_FATAL);
      }	
      
      systab->headwritten += charsout;
      
      if (systab->debug == cb_TRUE) {
	sprintf(outbuf, "Padded header with %d bytes", charsout);
	ConsoleMsg("%s", outbuf);
      }
    }
    
    // Seek to end of header/beginning of data 

    if (systab->debug == cb_TRUE) {
      sprintf(outbuf, "Seeking to byte %d (end of header/start of data)", image_addr);
      ConsoleMsg("%s", outbuf);
      ts0 = FineSysTime();
    }
    
    CBseek(ifd, image_addr, 0);

    if (systab->debug == cb_TRUE) {
      ts1 = FineSysTime();
      dt = ts1 - ts0;
      sprintf(outbuf, "time to seek = %.6f sec", dt);
      ConsoleMsg("%s", outbuf);

      sprintf(outbuf, "Reading the data...");
      ConsoleMsg("%s", outbuf);
      ts0 = FineSysTime();
    }
    
    // Since size of data unit was calculable from bits per pixel and
    // image size, we know how many blocks to read

    for(lcv=0; lcv<(datasize/FITS_DATA_BLOCK_SIZE); lcv++)  {
      charsin = CBread(ifd, databuf, FITS_DATA_BLOCK_SIZE); 
      charsout = write(ofd, databuf, FITS_DATA_BLOCK_SIZE);
      
      if (charsout == -1) {  // error on write() to disk 
	close(ofd);
	if (errno == ENOSPC) {// file system full! 
	  XmitMsg(port,host,"FATAL: Cannot write %s -- DISK FULL",filename);
	}
	else {  // some other fool thing - print error message 
	  XmitMsg(port,host,"FATAL: Cannot write %s -- %s",filename,ERRORSTR);
	}
	return(cb_FATAL);
      }	
      
      systab->datawritten += charsout;
      
    } // end of read loop 
    
    if (systab->debug == cb_TRUE) {
      ts1 = FineSysTime();
      dt = ts1 - ts0;
      sprintf(outbuf, "...done.  Time to read data = %.6f sec", dt);
      ConsoleMsg("%s", outbuf);

      sprintf(outbuf, "Looped %d times", lcv);
      ConsoleMsg("%s", outbuf);
      
      sprintf(outbuf, "%d data bytes written in 8192-byte chunks", systab->datawritten);
      ConsoleMsg("%s", outbuf);
      
    }
    
    // And again we write out the last line of the data unit and prepare
    // to pad out to a multiple of FITS_BLOCK_SIZE
    
    charsin = CBread(ifd, databuf, FITS_DATA_BLOCK_SIZE);
    charsout = write(ofd, databuf, datasize%FITS_DATA_BLOCK_SIZE);
    
    if (charsout == -1) {    // error on write() to disk 
      close(ofd);
      if (errno == ENOSPC) { // file system full! 
	XmitMsg(port,host,"FATAL: Cannot write %s -- DISK FULL",filename);
      }
      else {  // some other fool thing - print error message 
	XmitMsg(port,host,"FATAL: Cannot write %s -- %s",filename,ERRORSTR);
      }
      return(cb_FATAL);
    }	
    
    systab->datawritten += charsout;
    
    if (systab->debug == cb_TRUE) {
      sprintf(outbuf, "Added an extra %d bytes", charsout);
      ConsoleMsg("%s", outbuf);
      
      sprintf(outbuf, "Wrote %d total data bytes", systab->datawritten);
      ConsoleMsg("%s", outbuf);
    }
    
    // If datasize is a multiple of FITS_BLOCK_SIZE (2880), don't pad
    // Otherwise, pad data unit out to a multiple of FITS_BLOCK_SIZE
    // with zeros.
     
    
    if ((datasize%FITS_BLOCK_SIZE)>0) {
      for(lcv=0; lcv < FITS_BLOCK_SIZE - (datasize%FITS_BLOCK_SIZE); lcv++) 
	pad[lcv] = 0;                                                       
      
      if (lcv<FITS_BLOCK_SIZE) {
	charsout = write(ofd, pad, lcv);
	
	if (charsout == -1) {     // error on write() to disk 
	  close(ofd);
	  if (errno == ENOSPC) {// file system full! 
	    XmitMsg(port,host,"FATAL: Cannot write %s -- DISK FULL",filename);
	  }
	  else {  // some other fool thing - print error message 
	    XmitMsg(port,host,"FATAL: Cannot write %s -- %s",filename,ERRORSTR);
	  }
	  return(cb_FATAL);
	}	
	
	systab->datawritten += charsout;
	
	if (systab->debug == cb_TRUE) {
	  sprintf(outbuf, "Padded data with %d bytes", charsout);
	  ConsoleMsg("%s", outbuf);
	}
      }
    }
    
    // all done, update the files-transferred counter 

    numxferd++;                   
    sprintf(systab->lastfile, filename);
    
    // query the time clock at completion 

    after = FineSysTime();

    // Determine how much data we just output 

    stat(filename, &sbuf);
    bytes = sbuf.st_size;
    if (systab->debug == cb_TRUE) {
      sprintf(pad, "%d total bytes written (%d header + %d data)", 
	      (long) bytes, systab->headwritten, systab->datawritten);
      ConsoleMsg("%s", pad);
    }

    rate = (bytes/1024.0)/(after-before);

    sprintf(logstr, "Transferred file #%d (%s) at %.0f KB in %.2f sec (%.0f KB/sec)", 
	    gfcv+1, filename, bytes/1024.0, after-before, rate);
    
    ConsoleMsg("%s", logstr);
      
    // changed to ICIMACS/Prospero-style keyword=value message format [97Apr29, rwp] 
    
    // Check to see if we need to notify anyone of the transfer--QT
    // means don't

    if (strcmp(host, "QT")!=0)  {
      ltos(argbuf, rate);
      XmitMsg(port, host, "DONE: Wrote LASTFILE=%s RATE=%s KB/sec", filename, argbuf);
    }

    // give everybody read/write privs & then close the FITS file 

    fchmod(ofd, 0666);
    close(ofd);

    // if archiving, issue the archive command 

    if (systab->doarchive == cb_TRUE) {
      sprintf(lprcmd, systab->archivecmd, filename);
      lprpipe = popen(lprcmd, "r");
      if (lprpipe!=0)
	pclose(lprpipe);
    }
    
    // if autologging, issue the autolog command 
    
    if (systab->doautolog == cb_TRUE) {
      sprintf(lprcmd, systab->autologcmd, filename);
      alogpipe = popen(lprcmd, "r");
      if (alogpipe!=0)
	pclose(alogpipe);
    }
    
  }
  
  close(ifd);                        // Close files 
  
  ltos(argbuf, (long) numfiles);     // Report completion to disk server host 
  XmitMsg(systab->fd_disk, systab->diskhost, "DONE %s %s", alias, argbuf);
  
  return(numxferd);                  // Return number of files transferred 
}

//**************************************************************************
// 
// FineSysTime() - get the system time in seconds+microseconds since 
//                 UTC 1970 January 1
//
 
double 
FineSysTime(void)
{
  struct timeval tv;
  static char str[30];
  char *ptr;

  if (gettimeofday(&tv,NULL)<0)
    printf("gettimeofday error\n");
  ptr = ctime(&tv.tv_sec);

  sprintf(str,"%ld.%06ld",tv.tv_sec,tv.tv_usec);
  
  return((double)(atof(str)));

}

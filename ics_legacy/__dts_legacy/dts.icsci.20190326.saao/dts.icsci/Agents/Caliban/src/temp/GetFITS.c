/* GetFITS Routine                                                                                              */
/* Purpose: Actual FITS file acquisition and structuring routine                                                */
/* Requires: Port number, host to notify, spool device name and alias name, and number of files to xfer         */
/* Returns: Nothing                                                                                             */

#include "Caliban.h"

int GetFITS(int port, char *host, char devicename[SHORT_STR_SIZE], char alias[SHORT_STR_SIZE], int numfiles)
{
  int ifd, ofd;                   /* Input and output file descriptors                                          */
  int headsize;                   /* FITS header unit size in bytes                                             */
  int numcards=0;                 /* FITS header card counter                                                   */
  int bitpix;                     /* FITS bits per pixel                                                        */
  int lcv;                        /* Local loop control variable                                                */
  int gfcv;                       /* Loop control varible for multiple file gets                                */
  int invalid=0;                  /* Invalid flag                                                               */
  int numxferd=0;                 /* Number of files successfully transferred                                   */
  int chksum=0;                   /* Checksum flag                                                              */
  int charsin, charsout;          /* Number of characters returned/written during various read/write operations */
  int done=0;                     /* Done flag                                                                  */
  long datasize;                  /* FITS data unit size in bytes                                               */
  long naxis1, naxis2;            /* FITS axis values                                                           */
  char inbuf[513];                /* Generic buffer                                                             */
  char *headbuf;                  /* Variable length buffer used to transfer header in one chunk                */
  char databuf[FITS_DATA_BLOCK_SIZE+1]; /* Buffer used to transfer data in 8K chunks                            */
  char argbuf[MED_STR_SIZE];      /* Argument buffer for GetArg calls                                           */
  char logstr[MED_STR_SIZE];      /* Log message buffer                                                         */
  char outbuf[MED_STR_SIZE];      /* General purpose buffer used in ConsoleMsg calls                            */
  char pad[FITS_BLOCK_SIZE];      /* Padding to accomodate FITS file structure requirements                     */
  char filename[MED_STR_SIZE], uniquename[MED_STR_SIZE]; /* File names                                          */
  double bytes, rate;             /* Used in calculating throughput rate                                        */
  double before;                  /* Time structures for use in timing throughtput                              */
  double after;                   /*                                                                            */
  struct stat sbuf;               /* File statistics buffer                                                     */
  struct timeval tp;
  char lprcmd[MED_STR_SIZE];      /* Archive command                                                            */
  FILE *lprpipe;                  /* Shell pipe handle for archive command                                      */
  FILE *alogpipe;                 /* Shell pipe handle for autolog command                                      */


  if((ifd=open(devicename, cb_FILEMODE))==cb_ERROR) /* Attempt to open the spool device                               */
    {
      XmitMsg(port, host, "ERROR: Unable to open spool device %s--%s", devicename, ERRORSTR);
      return(SYSERR);
    }

  for(gfcv=0;gfcv<numfiles;gfcv++) /* Loop numfiles times */
    {
      systab->headwritten = 0;
      systab->datawritten = 0;

      if(systab->verbose == cb_TRUE)
	{
	  sprintf(outbuf, "Initiating file transfer iteration #%d...", gfcv+1);
	  ConsoleMsg("%s", outbuf);
	}

      gettimeofday(&tp, '\0');
      
      before = tp.tv_sec + (tp.tv_usec/1000000.0);

      /* The first sector on the spool device contains physical drive parameters   */
      /* Therefore, valid data begins on the second sector, so we begin by seeking */
      /* to it.  From there, we find numfiles occurrences of header unit followed  */
      /* by data unit, the lengths of which are contained in headlng and datalng   */

      CBseek(ifd, (long) (BLOCK_SIZE + (BLOCK_SIZE * gfcv * systab->datalng)), 0);

      if(systab->debug == cb_TRUE)
	{
	  sprintf(outbuf, "Seeking to byte %d", (BLOCK_SIZE + (BLOCK_SIZE * gfcv * systab->datalng)));
	  ConsoleMsg("%s", outbuf);
	}

      if((charsin = CBread(ifd, inbuf, 80))==cb_ERROR) /* Attempt to read header data */
	{
	  ltos(argbuf, (long) gfcv);
	  XmitMsg(port, host, "ERROR: Unable to read FITS header in file #%s, skipping...", argbuf);
	  continue;
	}

      inbuf[80] = NUL; /* So string routines won't blow up */

      /* The first card of a valid FITS head should contain the word SIMPLE */

      if(strncmp(inbuf, "SIMPLE", 6)!=0) 
	{
	  ltos(argbuf, (long) gfcv+1);
	  XmitMsg(port, host, "ERROR: No SIMPLE card in FITS file #%s, skipping...", argbuf);
	  continue;
	}
      
      numcards = 1;

      bitpix = naxis1 = naxis2 = chksum = done = invalid = 0;
      BZero(filename, sizeof(filename));
      BZero(uniquename, sizeof(uniquename));

      /* The following loop searches through the FITS header looking for the required */
      /* cards.  Each time it finds a required card, it increments a checksum so that */
      /* at the end we will know if all required cards were found                     */

      while(!done && !invalid)
	{
	  charsin = CBread(ifd, inbuf, 80);
	  inbuf[80] = NUL;
	  numcards++;

	  if(strncmp(inbuf, "BITPIX  =", 9)==0)          /* Read bits-per-pixel value */
	    {
	      chksum++;
	      GetArg(inbuf, 3, argbuf);
	      bitpix = atoi(argbuf);
	    }
	  else if(strncmp(inbuf, "FILENAME=", 9)==0)     /* File name card            */
	    {
	      chksum += 2;
	      GetArg(inbuf, 2, argbuf);

	      if (argbuf[0] == '\'')                           /* Make sure first character is a quote */
		RightStr(filename, argbuf, strlen(argbuf)-1);  /* Remove quotes from file name         */
	      else
		sprintf(filename, "%s", argbuf);
	      if (filename[strlen(filename)-1] == '\'')        /* Make sure last character is a quote  */
		LeftStr(argbuf, filename, strlen(filename)-1);
	      else
		sprintf(argbuf, "%s", filename);

	      /* Add path and .fits extension if enabled */
	      if (systab->addfits == cb_TRUE)
		sprintf(filename, "%s/%s.fits", strstr(mounttab->mount[mounttab->current], "/"), argbuf);
	      else
		sprintf(filename, "%s/%s", strstr(mounttab->mount[mounttab->current], "/"), argbuf);
	    }
	  else if(strncmp(inbuf, "UNIQNAME=", 9)==0)          /* Unique file name card        */
	    {
	      chksum += 3;
	      GetArg(inbuf, 2, argbuf);

	      if (argbuf[0] == '\'')                            /* Make sure first character is a quote */
		RightStr(uniquename, argbuf, strlen(argbuf)-1); /* Remove quotes from file name         */
	      else
		sprintf(uniquename, "%s", argbuf);
	      if (uniquename[strlen(uniquename)-1] == '\'')     /* Make sure last character is a quote  */
		LeftStr(argbuf, uniquename, strlen(uniquename)-1);
	      else
		sprintf(argbuf, "%s", uniquename);

	      /* Add path */

	      if (systab->addfits == cb_TRUE)
		sprintf(uniquename, "%s/%s.fits", strstr(mounttab->mount[mounttab->current], "/"), argbuf);
	      else
		sprintf(uniquename, "%s/%s", strstr(mounttab->mount[mounttab->current], "/"), argbuf);
	    }
	  else if(strncmp(inbuf, "NAXIS1  =", 9)==0)          /* Read and convert axis values */ 
	    {
	      chksum += 4;
	      GetArg(inbuf, 3, argbuf);
	      naxis1 = atoi(argbuf);
	    }
	  else if(strncmp(inbuf, "NAXIS2  =", 9)==0)
	    {
	      chksum += 5;
	      GetArg(inbuf, 3, argbuf);
	      naxis2 = atoi(argbuf);
	    }
	  else if(strncmp(inbuf, "END                                                                             ", 80)==0)
	    {
	      done = cb_TRUE;
	    }
	  
	  if(numcards >= systab->maxcards) /* Have we read more header cards than are allowed? */
	    invalid=cb_TRUE;
	}

      if(chksum<15) /* Have we found all required cards? */
	{
	  ltos(argbuf, (long) gfcv+1);
	  XmitMsg(port, host, "ERROR: FITS header missing one or more required entries in file #%s, skipping...", argbuf);
	  continue;
	}
      
      if(invalid == cb_TRUE) /* A valid FITS header must end with END followed by 77 spaces */
	{
	  ltos(argbuf, (long) gfcv+1);
	  XmitMsg(port, host, "ERROR: Missing END card in FITS file #%s, skipping...", argbuf);
	  continue;
	}
      
      headsize = numcards * 80;                            /* Calculate header unit size */
      datasize = (abs(bitpix)/8) * naxis1 * naxis2;        /* Calculate data unit size */

      if(systab->debug == cb_TRUE)
	{
	  sprintf(pad, "Headsize = %d, Datasize = %d, naxis1 = %d, naxis2 = %d, bitpix = %d\n", headsize, datasize, naxis1, naxis2, bitpix);
	  ConsoleMsg("%s", pad);
	}

      /****************************************************************
       * Attempt to open the output file
       *
       * All kinds of things can go wrong here:
       *   a) file already exists - if so, switch to the unique name
       *   b) we are out of disk space on the target disk file system
       *   c) ...
       *
       ****************************************************************/

      if((ofd=open(filename, 2))==cb_ERROR) 
	{
	  if((ofd=creat(filename, 0664))==cb_ERROR)
	    {
	      if((ofd=creat(uniquename, 0664))==cb_ERROR)
		{
		  ltos(argbuf, (long) gfcv+1);
		  XmitMsg(port, host, "ERROR: Cannot create unique FITS file #%s (%s)--%s, skipping...", argbuf, uniquename, ERRORSTR);
		  continue;
		}
	      sprintf(filename, uniquename);
	    }
	}
      else                                                 /* Primary name already exists, so use unique name */
	{
	  if(ofd!=0)
	    close(ofd);
	  if((ofd=creat(uniquename, 0664))==cb_ERROR)
	    {
	      ltos(argbuf, (long) gfcv+1);
	      XmitMsg(port, host, "ERROR: Cannot create unique FITS file #%s (%s)--%s, skipping...", argbuf, uniquename, ERRORSTR);
	      continue;
	    }
	  sprintf(filename, uniquename);
	}

      if(systab->debug == cb_TRUE)
	ConsoleMsg("Created file %s", filename);

      /* check disk space on target mount point - currently disabled [98Sept27/rwp] */

      if (ChkDiskSpace((char *)(mounttab->mount[mounttab->current]), (long) ((bitpix / 8) * naxis1 * naxis2)) != cb_TRUE)
	{
	  close(ofd);
	  XmitMsg(port, host, "FATAL: %s Disk is FULL, write failed", mounttab->mount[mounttab->current]);
	  return(cb_FATAL);
	}
      
      CBseek(ifd, (long) (BLOCK_SIZE + (BLOCK_SIZE * gfcv * systab->datalng)), 0); /* Seek to BOF */

      if(systab->debug == cb_TRUE)
	{
	  sprintf(outbuf, "Seeking to byte %d", (BLOCK_SIZE + (BLOCK_SIZE * gfcv * systab->datalng)));
	  ConsoleMsg("%s", outbuf);
	}

      headbuf = malloc(headsize+1); /* Allocate a buffer big enough to transfer the header segment in one chunk */
      
      charsin = CBread(ifd, headbuf, headsize);
      charsout = write(ofd, headbuf, headsize);

      /* Check value of charsout.  if -1, a fatal write error occured, check errno code & abort */

      if (charsout == -1)      /* error on write() to disk */
	{ 
	  free(headbuf); /* Free the allocated header memory */
	  close(ofd);
	  if (errno == ENOSPC) /* file system full! */
	    {  
	      XmitMsg(port,host,"FATAL: Cannot write %s -- DISK FULL",filename);
	    }
	  else   /* some other fool thing - print error message */
	    {
	      XmitMsg(port,host,"FATAL: Cannot write %s -- %s",filename,ERRORSTR);
	    }
	  return(cb_FATAL);
	}	

      systab->headwritten += charsout;

      free(headbuf); /* Free the allocated memory */

      if(systab->debug == cb_TRUE)
	{
	  sprintf(outbuf, "Wrote %d header bytes", systab->headwritten);
	  ConsoleMsg("%s", outbuf);
	}

      /* If headsize is a multiple of FITS_BLOCK_SIZE (2880), don't pad */

      if ((headsize%FITS_BLOCK_SIZE)>0) {
	for(lcv=0; lcv < FITS_BLOCK_SIZE-(headsize%FITS_BLOCK_SIZE); lcv++) /* Pad header unit out to a    */
	  {                                                                 /* multiple of FITS_BLOCK_SIZE */
	    pad[lcv] = ' ';                                                 /* with spaces                 */
	  }

	charsout = write(ofd, pad, lcv);

	if (charsout == -1)      /* error on write() to disk */
	  { 
	    close(ofd);
	    if (errno == ENOSPC) /* file system full! */
	      {  
		XmitMsg(port,host,"FATAL: Cannot write %s -- DISK FULL",filename);
	      }
	    else   /* some other fool thing - print error message */
	      {
		XmitMsg(port,host,"FATAL: Cannot write %s -- %s",filename,ERRORSTR);
	      }
	    return(cb_FATAL);
	  }	

	systab->headwritten += charsout;

	if(systab->debug == cb_TRUE)
	  {
	    sprintf(outbuf, "Padded header with %d bytes", charsout);
	    ConsoleMsg("%s", outbuf);
	  }
      }
      
      /* Seek to end of header/beginning of data */

      CBseek(ifd, (long) ((systab->headlng+1) * (BLOCK_SIZE + (BLOCK_SIZE * gfcv * systab->datalng))), 0);

      if(systab->debug == cb_TRUE)
	{
	  sprintf(outbuf, "Seeking to byte %d", ((systab->headlng+1) * (BLOCK_SIZE + (BLOCK_SIZE * gfcv * systab->datalng))));
	  ConsoleMsg("%s", outbuf);
	}

      for(lcv=0; lcv<(datasize/FITS_DATA_BLOCK_SIZE); lcv++)  /* Since size of data unit was calculable from */
	{                                                     /* bits per pixel and image size, we know how  */
	  charsin = CBread(ifd, databuf, FITS_DATA_BLOCK_SIZE); /* many blocks to read                         */
	  charsout = write(ofd, databuf, FITS_DATA_BLOCK_SIZE);

	  if (charsout == -1)      /* error on write() to disk */
	    { 
	      close(ofd);
	      if (errno == ENOSPC) /* file system full! */
		{  
		  XmitMsg(port,host,"FATAL: Cannot write %s -- DISK FULL",filename);
		}
	      else   /* some other fool thing - print error message */
		{
		  XmitMsg(port,host,"FATAL: Cannot write %s -- %s",filename,ERRORSTR);
		}
	      return(cb_FATAL);
	    }	

	  systab->datawritten += charsout;
	}

      if(systab->debug == cb_TRUE)
	{
	  sprintf(outbuf, "Looped %d times", lcv);
	  ConsoleMsg("%s", outbuf);
	  
	  sprintf(outbuf, "%d data bytes written in 8192-byte chunks", systab->datawritten);
	  ConsoleMsg("%s", outbuf);
	}

      charsin = CBread(ifd, databuf, FITS_DATA_BLOCK_SIZE);          /* And again we write out the last line of the */
                                                                     /* data unit and prepare to pad out to a       */
                                                                     /* multiple of FITS_BLOCK_SIZE                 */

      charsout = write(ofd, databuf, datasize%FITS_DATA_BLOCK_SIZE);

      if (charsout == -1)      /* error on write() to disk */
	{ 
	  close(ofd);
	  if (errno == ENOSPC) /* file system full! */
	    {  
	      XmitMsg(port,host,"FATAL: Cannot write %s -- DISK FULL",filename);
	    }
	  else   /* some other fool thing - print error message */
	    {
	      XmitMsg(port,host,"FATAL: Cannot write %s -- %s",filename,ERRORSTR);
	    }
	  return(cb_FATAL);
	}	

      systab->datawritten += charsout;

      if(systab->debug == cb_TRUE)
	{
	  sprintf(outbuf, "Added an extra %d bytes", charsout);
	  ConsoleMsg("%s", outbuf);

	  sprintf(outbuf, "Wrote %d total data bytes", systab->datawritten);
	  ConsoleMsg("%s", outbuf);
	}

      /* If datasize is a multiple of FITS_BLOCK_SIZE (2880), don't pad */

      if ((datasize%FITS_BLOCK_SIZE)>0) {
	for(lcv=0; lcv < FITS_BLOCK_SIZE - (datasize%FITS_BLOCK_SIZE); lcv++) /* Pad data unit out to a      */
	  pad[lcv] = 0;                                                       /* multiple of FITS_BLOCK_SIZE */

	if(systab->debug == cb_TRUE)
	  {
	    sprintf(outbuf, "FITS_BLOCK_SIZE - (datasize%FITS_BLOCK_SIZE) = %d", FITS_BLOCK_SIZE - (datasize%FITS_BLOCK_SIZE));
	    ConsoleMsg("%s", outbuf);
	    
	    sprintf(outbuf, "lcv = %d", lcv);
	    ConsoleMsg("%s", outbuf);
	  }
                                                                /* with zeroes                 */
	if (lcv<FITS_BLOCK_SIZE) {
	  charsout = write(ofd, pad, lcv);

	  if (charsout == -1)      /* error on write() to disk */
	    { 
	      close(ofd);
	      if (errno == ENOSPC) /* file system full! */
		{  
		  XmitMsg(port,host,"FATAL: Cannot write %s -- DISK FULL",filename);
		}
	      else   /* some other fool thing - print error message */
		{
		  XmitMsg(port,host,"FATAL: Cannot write %s -- %s",filename,ERRORSTR);
		}
	      return(cb_FATAL);
	    }	

	  systab->datawritten += charsout;

	  if(systab->debug == cb_TRUE)
	    {
	      sprintf(outbuf, "Padded data with %d bytes", charsout);
	      ConsoleMsg("%s", outbuf);
	    }
	}
      }

      numxferd++;                                          /* Update the counter of files transferred */
      sprintf(systab->lastfile, filename);

      gettimeofday(&tp, '\0');
      after = tp.tv_sec + (tp.tv_usec/1000000.0); /* Stop the clock */

      stat(filename, &sbuf);                               /* Determine how much data we just output */

      bytes = sbuf.st_size;

      if(systab->debug == cb_TRUE)
	{
	  sprintf(pad, "%d total bytes written (%d header + %d data)", (long) bytes, systab->headwritten, systab->datawritten);
	  
	  ConsoleMsg("%s", pad);
	}

      rate = (bytes/1024.0)/(after-before);

      sprintf(logstr, "Transferred file #%d (%s) at %.0f KB in %.2f sec (%.0f KB/sec)", gfcv+1, filename, bytes/1024.0, after-before, rate);

      ConsoleMsg("%s", logstr);

/* changed to ICIMACS/Prospero-style keyword=value message format [97Apr29, rwp] */

      if(strcmp(host, "QT")!=0)  /* Check to see if we need to notify anyone */
	{                        /* of the transfer--QT means don't */
	  ltos(argbuf, rate);
	  XmitMsg(port, host, "STATUS: Wrote LASTFILE=%s RATE=%s KB/sec", filename, argbuf);
	}

      /* give everybody read/write privs & then close the FITS file */

      fchmod(ofd, 0666);
      close(ofd);

      /* if archiving, issue the archive command */

      if(systab->doarchive == cb_TRUE) {
	sprintf(lprcmd, ARCHIVE_CMD, filename);
	lprpipe = popen(lprcmd, "r");
	if (lprpipe!=0)
	  pclose(lprpipe);
      }

      /* if autologging, issue the autolog command */

      if(systab->doautolog == cb_TRUE) {
	sprintf(lprcmd, AUTOLOG_CMD, filename);
	alogpipe = popen(lprcmd, "r");
	if (alogpipe!=0)
	  pclose(alogpipe);
      }

  }

  ltos(argbuf, (long) numfiles);     /* Report completion to serial host */
  XmitMsg(port, systab->serialhost, "DONE %s %s", alias, argbuf);
    
  close(ifd);                        /* Close files */
  
  return(numxferd);                  /* Return number of files transferred */
}


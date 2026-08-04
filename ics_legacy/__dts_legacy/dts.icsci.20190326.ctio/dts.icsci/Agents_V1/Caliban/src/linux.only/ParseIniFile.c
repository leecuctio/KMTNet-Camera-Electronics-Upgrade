/* ParseIniFile Routine                                                                 */
/* Purpose: Parses initialization file to set up initial state configuration structures */
/* Requires: Nothing                                                                    */
/* Returns: Nothing                                                                     */

#include "Caliban.h"

void ParseIniFile()
{
  int lcv;                             /* Loop control variable                         */
  char keyword[MED_STR_SIZE];          /* File is organized into KEYWORD VALUE pairs    */
  char argbuf[MED_STR_SIZE];           /* Generic argument buffer                       */
  char inbuf[BUF_SIZE];                /* Generic input buffer                          */
  FILE *rfp;                           /* Initialization file pointer                   */

  if(!(rfp=fopen(INI_FILE_NAME, "r"))) /* Open initialization file                      */
    {
      /* If the ini file cannot be found, exit abnormally                               */

      endwin();  /* Restore the tty to its previous state                               */
      printf("Unable to open initialization file--%s--exiting abnormally\n", ERRORSTR);
      exit(SYSERR);
    }
  else
    {
      while(fgets(inbuf, 80, rfp))   /* Loop through file reading 80 byte blocks at a time                             */
	    {
	      if((inbuf[0]!='#') && (inbuf[0]!='\n') && inbuf[0]!=NUL) /* Skip comments and blank lines                */
		{
		  inbuf[80] = NUL;
		  GetArg(inbuf, 1, argbuf);
		  strcpy(keyword, argbuf);
		  UpperCase(keyword);

		  if(strcmp(keyword, "LOG_FILE_NAME")==0)    /* Log file name                                          */
		    {
		      GetArg(inbuf, 2, argbuf);
		      sprintf(systab->logfilename, argbuf);
		    }
		  else if(strcmp(keyword, "SERIAL_PORT")==0) /* Serial port device name                                */
		    {
		      GetArg(inbuf, 2, argbuf);		      
		      sprintf(systab->serialdev, argbuf);
		    }
		  else if(strcmp(keyword, "BLOCK_SIZE")==0)  /* FITS file block size                                   */
		      {
			GetArg(inbuf, 2, argbuf);
			systab->blocksize = atoi(argbuf);
		      }
		  else if(strcmp(keyword, "SERIAL_HOST")==0) /* Name of host on other end of serial interface          */
		    {
		      GetArg(inbuf, 2, argbuf);
		      sprintf(systab->serialhost, argbuf);
		    }
		  else if(strcmp(keyword, "SPOOL_DEVICE")==0) /* Disk table device entry                               */
		    {
		      GetArg(inbuf, 2, argbuf);		      
		      sprintf(disktab->device[disktab->numdisks], argbuf);
		      disktab->numdisks++; /* Increment potential disk devices counter                                 */
		    }
		  else if(strcmp(keyword, "LOCAL_HOST")==0)  /* Local host name                                        */
		    {
		      GetArg(inbuf, 2, argbuf);
		      sprintf(systab->localhost, argbuf);
		    }
		  else if(strcmp(keyword, "VERBOSE")==0)     /* Enable verbose mode                                    */
		    {
		      systab->verbose = cb_TRUE;
		    }
		  else if(strcmp(keyword, "DOARCHIVE")==0)   /* Enable archiving                                       */
		    {
		      systab->doarchive = systab->olddoarchive = cb_TRUE;
		    }
		  else if(strcmp(keyword, "DOAUTOLOG")==0)   /* Enable autologging                                     */
		    {
		      systab->doautolog = systab->olddoautolog = cb_TRUE;
		    }
		  else if(strcmp(keyword, "DODISPLAY")==0)   /* Enable auto display of images                          */
		    {
		      systab->dodisplay = systab->olddodisplay = cb_TRUE;
		    }
		  else if(strcmp(keyword, "ADDFITS")==0)     /* Add .fits filename extension                           */
		    {
		      systab->addfits = systab->oldaddfits = cb_TRUE;
		    }
		  else if(strcmp(keyword, "DBG_HEADLNG")==0) /* Default FITS Header Unit length before synchronization */
		    {
		      GetArg(inbuf, 2, argbuf);
		      systab->headlng = atoi(argbuf);
		    }
		  else if(strcmp(keyword, "DBG_DATALNG")==0) /* Default FITS Data Unit length before synchronization   */
		    {
		      GetArg(inbuf, 2, argbuf);
		      systab->datalng = atoi(argbuf);
		    }
		  else if(strcmp(keyword, "MOUNT")==0) /* Mount table entry */
		    {
		      GetArg(inbuf, 2, argbuf);
		      sprintf(mounttab->mount[mounttab->nummounts], argbuf);
		      if(IsValidMount(mounttab->mount[mounttab->nummounts])==cb_TRUE) /* Validate mount point          */
			{
			  mounttab->nummounts++; /* Increment count of valid mount points */
			}
		      else
			{
			  BZero(mounttab->mount[mounttab->nummounts], sizeof(mounttab->mount[mounttab->nummounts])); /* If not valid, leave blank */
			}
		    }
		  else if(strcmp(keyword, "MAX_XFER_FILES")==0) /* Max number of files transferrable at one time      */
		    {
		      GetArg(inbuf, 2, argbuf);		      
		      systab->max_xfer_files = atoi(argbuf);
		    }
		  else /* Unrecognized entry handler */
		    {
		      ConsoleMsg("Ignoring unrecognized entry in initialization file - %s\n", inbuf);
		    }
		}
	      BZero(inbuf, sizeof(inbuf)); /* Reset input buffer to the empty string                                  */
	    }
    }

if(rfp!=0)
  fclose(rfp);                             /* Close initialization file                                               */
}

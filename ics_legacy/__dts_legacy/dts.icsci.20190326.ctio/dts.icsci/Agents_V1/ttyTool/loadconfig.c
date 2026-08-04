//**************************************************************************
//
// Loadconfig() - load an ISIS client's runtime configuration file
//

/*!
  \file loadconfig.c
  \brief Load/Parse ISIS client's runtime configuration file.

  ISIS-style runtime configuration files (e.g., named myclient.ini,
  .myclientrc, whatever) contain simple Keyword-Value pairs that are
  parsed into global-scope variables for the client and its various
  subroutines to use.
 
  The # is used as a comment character, making a comment line when it
  appears as the first character in a line by itself.  Inline comments
  are not supported by this simple parser, but are generally ignored
  since it assumes (again for simplicity) that value arguments are
  numbers or strings without spaces.  Fancier parsers can be implemented
  as needed.  Blank lines are ignored by the parser.  We adopt the
  convention that keywords and values are case insensitive, to remove
  any ambiguity.
  
  This template provides a good example of common client initialiation
  file parameters and syntax.  The idea is to make the runtime config
  files for all ISIS clients look pretty much the same in terms of
  having a common syntax as appearance.  The utility function GetArg()
  used here is from isisutils.c, with the prototype defined in the
  isisclient.h header.
 
  A typical runtime config file has the following structure:
  \code 
       #
       # myclient runtime configuration file
       #
       # Modified 2003 June 21 by R. Pogge, OSU Astronomy Dept.
       # for the fauxMODS spectrograph system echoclient.
       #
       ID   echo
       Port 7890
       LogFile    /data/Logs/myclient
       Verbose
       #
       ServerID   isis1
       ServerHost mods1.lbto.org
       ServerPort 6789
  \endcode
 
  Here we are telling myclient that it is a client of an ISIS server
  named "isis1" running on host mods1.lbto.org and listening to network
  socket port 6789.  We are to be an ISIS client node named "echo"
  listing to network socket port 7890 on the localhost.  All runtime
  logging will be recorded to a file named /data/Logs/myclient.log, and
  both logging and screen output will be Verbose for debugging purposes.
 
  As this example shows, the goal is that runtime configuration files
  are easily read and created by humans.  A common syntax makes
  maintenance of many clients easier.
 
  This version is custom for the ttytool application. 
 
  \author R. Pogge, OSU Astronomy Dept. (pogge@astronomy.ohio-state.edu)
  \date 2003 September 14 (original version based on the ISIS server ParseIniFile())

  \par Mods Modification History:
<pre>  
2005 Feb 17 - modified for the ttytool app [rwp/osu]
</pre>
 
*/

#include "client.h"   // Custom client application header file

// maximum mumber of characters/line of the file

#define MAXCFGLINE 80 //!< Maximum mumber of characters/line in the runtime config file

/*!
  \brief Load/Parse ISIS client's runtime configuration file.
  \param cfgfile Path/name of the client runtime configuration file
  \return 0 if success, <0 if failure.  All error message are printed 
  to the client's console.

  The precise actions of LoadConfig() are tailored to the client application.
*/

int 
LoadConfig(char *cfgfile)
{
  char keyword[MAXCFGLINE];  // File is organized into KEYWORD VALUE pairs
  char argbuf[MAXCFGLINE];   // Generic argument buffer
  char inbuf[MAXCFGLINE];    // Generic input buffer

  FILE *cfgFP;               // Configuration file pointer
  int i;
  char c;                    

  // If we need to initialize any default parameter values, do it here.
  // Note that as-written these variables have been defined in global scope
  // for the entire client application, e.g., in main.c for the
  // application.

  // Record the runtime config file in use.

  strcpy(client.rcFile,cfgfile);

  // ISIS server information (Defaults defined in the client.h header):

  client.useISIS = 0;                       // default: STANDALONE mode rather
                                         //          than an ISIS client
  strcpy(client.isisHost,DEFAULT_ISISHOST); 
  client.isisPort = DEFAULT_ISISPORT;       
  strcpy(client.isisID,DEFAULT_ISISID);     

  // Client information (defaults in client.h):

  strcpy(client.ID,DEFAULT_MYID);     // client default ISIS node name
  client.Port = DEFAULT_MYPORT;       // client default port number

  gethostname(client.Host,sizeof(client.Host));   // client hostname

  // Client runtime parameters

  client.doLogging = 0;                   // default: runtime logging enabled 
  strcpy(client.logFile,DEFAULT_LOGFILE); // default client runtime log filename

  client.isVerbose = 0;                   // default: not verbose (concise)
  client.Debug = 0;                       // default: no debugging

  // Defaults for the serial port if a direct host connection

  commport.Speed = 9600;  // 9600 Baud
  commport.DataBits = 8;  // 8 Data Bits
  commport.StopBits = 1;  // 1 Stop Bit
  commport.Parity = 0;    // No Parity

  // Now open the config file, if not, gripe and return -1.  Opening the
  // file here ensures that sensible defaults are set even if the config
  // file stuff was in error.

  if (!(cfgFP=fopen(cfgfile, "r"))) {
    printf("ERROR: Cannot open runtime configuration file %s\n",cfgfile);
    printf("       %s\n",strerror(errno));
    return(-1);
  }

  //----------------------------------------------------------------
  //
  // Config file parser loop
  //
  // Read in each line of the config file and process it 
  //

  while(fgets(inbuf, MAXCFGLINE, cfgFP)) {

    // Skip comments (#) and blank lines

    if ((inbuf[0]!='#') && (inbuf[0]!='\n') && inbuf[0]!='\0') {
      inbuf[MAXCFGLINE] ='\0';
      GetArg(inbuf, 1, argbuf);
      strcpy(keyword, argbuf);
      
      //------------------------------
      // Keywords:
      //

      // Mode: the application's operating mode.  2 options:
      //       STANDALONE: no ISIS server present
      //       ISISClient: we're an ISIS client
      //

      if (strcasecmp(keyword,"MODE")==0) {
	GetArg(inbuf,2,argbuf);
	if (strcasecmp(argbuf,"STANDALONE")==0) {
	  client.useISIS = 0;
	}
	else if (strcasecmp(argbuf,"ISISCLIENT")==0) {
	  client.useISIS = 1;
	}
	else {
	  printf("ERROR: Mode option '%s' unrecognized\n",argbuf);
	  printf("       Must be STANDALONE or ISISCLIENT\n");
	  printf("Aborting - fix the config file (%s) and try again\n",
		 client.rcFile);
	  return -1;
	}
      }

      // ID: node name of this client 

      else if (strcasecmp(keyword,"ID")==0) {
	GetArg(inbuf,2,argbuf);
	strcpy(client.ID,argbuf);
      }

      // PORT: network socket port number of this client.  Host is
      //       assumed to be localhost (since it can't be anything else)

      else if (strcasecmp(keyword, "PORT")==0) {
	GetArg(inbuf, 2, argbuf);
	client.Port = atoi(argbuf);
      }

      // ISISID: Node name of the ISIS server.
      // 
      // Only meaningful if MODE ISISCLIENT has been set.
      //

      else if (strcasecmp(keyword, "ISISID")==0) {
	GetArg(inbuf, 2, argbuf);
	strcpy(client.isisID, argbuf);
      }

      // ISISHost: Hostname of the machine running the ISIS server.
      //             May be a resolvable name or an IP address.

      else if (strcasecmp(keyword,"ISISHOST")==0) {
	GetArg(inbuf,2,argbuf);
	strcpy(client.isisHost,argbuf);
      }
	
      // ISISPort: network socket port number used by the ISIS server 
      //             running on ServerHost
							  
      else if (strcasecmp(keyword, "ISISPORT")==0) {
	GetArg(inbuf, 2, argbuf);
	client.isisPort = atoi(argbuf);
      }

      // LogFile: Runtime log file rootname (including path) 
      //
      // The .log extension will be appended to this rootname. 

      else if (strcasecmp(keyword, "LOGFILE")==0) { 
	GetArg(inbuf, 2, argbuf);
	strcpy(client.logFile, argbuf);
	client.doLogging = 1;
      }

      // NOLOG: Explicitly disable the runtime logging

      else if (strcasecmp(keyword, "NOLOG")==0) {
	client.doLogging = 0;
	
      }
      
      // Verbose: Enable verbose output mode (e.g., for debugging)

      else if (strcasecmp(keyword, "VERBOSE")==0) {
	client.isVerbose = 1;
	
      }

      // Debug: Enable runtime debugging out (superverbose mode)

      else if (strcasecmp(keyword, "DEBUG")==0) {
	client.Debug = 1;
	
      }

      //---------------------------------------------------------------
      //
      // Microstep drive Parameters
      //

      // TTYPort = device port for microstep drive serial communications

      else if (strcasecmp(keyword, "TTYPORT")==0) {
	GetArg(inbuf,2,argbuf);
	strcpy(commport.Port,argbuf);
      }

      // SPEED - port speed in baud (1200,2400,4800,9600,19200,38400)

      else if (strcasecmp(keyword, "SPEED")==0) {
	GetArg(inbuf,2,argbuf);
	commport.Speed = atof(argbuf);
      }

      // DATABITS - port databits

      else if (strcasecmp(keyword, "DATABITS")==0) {
	GetArg(inbuf,2,argbuf);
	commport.DataBits = atoi(argbuf);
      }

      // DATABITS - port databits

      else if (strcasecmp(keyword, "DATABITS")==0) {
	GetArg(inbuf,2,argbuf);
	commport.DataBits = atoi(argbuf);
      }

      // STOPBITS - port stopbits

      else if (strcasecmp(keyword, "STOPBITS")==0) {
	GetArg(inbuf,2,argbuf);
	commport.StopBits = atoi(argbuf);
      }

      // Parity - port Parity (0 or 1)

      else if (strcasecmp(keyword, "PARITY")==0) {
	GetArg(inbuf,2,argbuf);
	commport.Parity = atoi(argbuf);
      }

      // Gripe if junk is in the config file

      else { 
	printf("Ignoring unrecognized config file entry - %s", inbuf);

      }
    }

    memset(inbuf,0,sizeof(inbuf)); 

  }

  /* all done, close the config file and return */

  if (cfgFP!=0)
    fclose(cfgFP);

  return(0);

}

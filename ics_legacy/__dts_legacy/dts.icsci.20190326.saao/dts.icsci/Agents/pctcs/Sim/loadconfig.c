//---------------------------------------------------------------------------
//
// loadConfig() - load an ISIS client's runtime configuration file
//
// Arguments
//     cfgfile (char*): full path/name of the client runtime config file
//
// Returns:
//   0 if success, <0 if failure.  All error message are printed internally
//
// Description:
//   Typical ISIS-style runtime configuration files (e.g., usually named
//   myclient.ini, .myclientrc, whatever) contain simple Keyword-Value pairs
//   that are parsed into global-scope variables for the client and its
//   various subroutines to use.
//
//   The # is used as a comment character, making a commend line when it
//   appears as the first character in a line by itself.  Inline comments
//   are not supported by this simple parser, but are generally ignored
//   since it assumes (again for simplicity) that value arguments are
//   numbers or strings without spaces.  Fancier parsers can be implemented
//   as needed.  of the comment is to the end of the line.  Blank lines are
//   ignored by the parser.  We also follow the covention that keywords and
//   values are case insensitive, to remove any ambiguity.
//  
//   This template provides a good example of common client initialiation
//   file parameters and syntax.  The idea is to make the runtime config
//   files for all ISIS clients look pretty much the same in terms of
//   having a common syntax as appearance.  The utility function GetArg()
//   used here is from isisutils.c, with the prototype defined in the
//   isisclient.h header.
//
// Example:
//   In the code shown in this file, the runtime config file would look
//   something like this:
//
//      #
//      # myclient runtime configuration file
//      #
//      # Modified 2003 June 21 by R. Pogge, OSU Astronomy Dept.
//      # for the fauxMODS spectrograph system echoclient.
//      #
//      ServerID   isis1
//      ServerHost mods1.lbto.org
//      ServerPort 6789
//      
//      ClientID   echo
//      ClientPort 7890
//      LogFile    /data/Logs/myclient
//      TCSPort    /dev/ttyS0
//      Verbose
//
//   Here we are telling myclient that it is a client of an ISIS server
//   named "isis1" running on host mods1.lbto.org and listening to network
//   socket port 6789.  We are to be an ISIS client node named "echo"
//   listing to network socket port 7890 on the localhost.  All runtime
//   logging will be recorded to a file named /data/Logs/myclient.log, and
//   both logging and screen output will be Verbose for debugging purposes.
//
//   As this example shows, the goal is that runtime configuration files
//   are easily read and created by humans.  A common syntax makes
//   maintenance of many clients easier.
//
// Author:
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2003 September 14
//
// Modification History:
//   2003 Sep 14: based on the ISIS server ParseIniFile.c program, but
//                stripped of server-specific code
//   2004 Feb 19: modified for pctcs
//
//---------------------------------------------------------------------------

#include "pctcs.h"       // PC-TCS interface agent header

#define MAXCFGLINE 80 // maximum mumber of characters/line of the file

int 
loadConfig(char *cfgfile)
{
  char keyword[MAXCFGLINE];  // File is organized into KEYWORD VALUE pairs
  char argbuf[MAXCFGLINE];   // Generic argument buffer
  char inbuf[MAXCFGLINE];    // Generic input buffer

  FILE *cfgFP;               // Configuration file pointer

  // If we need to initialize any default parameter values, do it here.
  // Note that as-written these variables have been defined in global scope
  // for the entire client application, e.g., in main.c for the
  // application.

  // These values are all members of the system table struct named tcs
  // defined in global scope in the pctcs.h header

  // record the runtime config file in use.

  strcpy(client.rcFile,cfgfile);

  // ISIS server information (Defaults defined in the pctcs.h header):

  client.useISIS = 0;                       // default: STANDALONE mode rather
                                         //          than an ISIS client
  strcpy(client.isisHost,DEFAULT_ISISHOST); 
  client.isisPort = DEFAULT_ISISPORT;       
  strcpy(client.isisID,DEFAULT_ISISID);     

  // Client information (defaults in pctcs.h):

  strcpy(client.ID,DEFAULT_MYID);     // client default ISIS node name
  client.Port = DEFAULT_MYPORT;       // client default port number

  gethostname(client.Host,sizeof(client.Host));   // client hostname

  // Client runtime parameters

  client.doLogging = 0;                   // default: runtime logging enabled 
  strcpy(client.logFile,DEFAULT_LOGFILE); // default client runtime log filename

  client.isVerbose = 0;                   // default: not verbose (concise)
  client.Debug = 0;                       // default: no debugging

  // PC-TCS serial port info ...
  
  strcpy(tcs.port,TCS_TTYPORT);     // default serial port device
  if (tcs.fd > 0)                   // PC-TCS connection closed at startup
    close(tcs.fd);
  tcs.fd = -1;    
  tcs.link = TCS_DOWN;

  // PC-TCS parameters of interest ...

  tcs.simMode = 0;                     // default is not simulation mode (0)
  tcs.timeout = TCS_TIMEOUT;           // default timeout for comm to PC-TCS
  tcs.idleTime = TCS_TIMEOUT;          // default "idle" time for telemetry health monitoring
  // Now to open the config file, if not, gripe and return -1.  Opening
  // the file here ensures that sensible defaults are set even if the
  // config file stuff was in error.

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

    if ((inbuf[0]!='#') && (inbuf[0]!='\n') && inbuf[0]!=NUL) {
      inbuf[MAXCFGLINE] = NUL;
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

      // ID: node name of this client 

      else if (strcasecmp(keyword,"ID")==0) {
	GetArg(inbuf,2,argbuf);
	strcpy(client.ID,argbuf);
      }

      // Port: network socket port number of this client.  Host is
      //             assumed to be localhost (since it can't be anything else)

      else if (strcasecmp(keyword, "PORT")==0) {
	GetArg(inbuf, 2, argbuf);
	client.Port = atoi(argbuf);
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

      // SIMMODE - put agent in simulation mode (not a live PC-TCS,
      //           but an amazing simulation...)

      else if (strcasecmp(keyword,"SIMMODE")==0) {
	tcs.simMode = 1;
      }

      // Parameters of the PC-TCS serial port link

      // TCSPort = device name (e.g., /dev/ttyA) of the serial port
      // connected to the PC-TCS computer

      else if (strcasecmp(keyword, "TCSPORT")==0) {
	GetArg(inbuf,2,argbuf);
	strcpy(tcs.port,argbuf);
      }

      // TCS comm parameters

      // TIMEOUT - timeout for direct communications, in seconds

      else if (strcasecmp(keyword, "TIMEOUT")==0) {
	GetArg(inbuf,2,argbuf);
	tcs.timeout = (long)(atoi(argbuf));
	if (tcs.timeout <= 0L)
	  tcs.timeout = 0L;

      }

      // IDLETIME - interval of time after which the PC-TCS telemetry link
      //            is judged to be idle, in seconds.  Since PC-TCS telemetry
      //            typically hits the port 5 times/sec, failure to receive
      //            50 telemetry packets is equivalent to IDLETIME 10 [seconds]

      else if (strcasecmp(keyword, "IDLETIME")==0) {
	GetArg(inbuf,2,argbuf);
	tcs.idleTime = atoi(argbuf);
      }

      // gripe if scruff is in the config file

      else { 
	printf("Ignoring unrecognized config file entry - %s", inbuf);

      }
    }

    memset(inbuf,0,sizeof(inbuf)); 

  }

  // all done, close the config file and return 

  if (cfgFP!=0)
    fclose(cfgFP);

  return(0);

}

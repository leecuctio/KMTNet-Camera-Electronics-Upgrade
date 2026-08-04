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
   # ISIS port relay config file
   #
   # R. Pogge, OSU Astronomy Dept.
   # pogge@astronomy.ohio-state.edu
   # 2014 Oct 8
   #
   ################################################################

   # UCP Socket info (localhost is implicit)

   UDPPort 10801

   # TTY Port info

   TTYPort /dev/ttyS0
   SPEED 115200
   DATABITS 8
   STOPBITS 1
   PARITY 0

   # ISIS Server Info

   ISISHost localhost
   ISISPort 6600

   # Relay Runtime flags 

   VERBOSE
   #nolog
   #debug
  \endcode
 
  As this example shows, the goal is that runtime configuration files
  are easily read and created by humans.  A common syntax makes
  maintenance of many clients easier.
 
  \author R. Pogge, OSU Astronomy Dept. (pogge@astronomy.ohio-state.edu)
  \date 2014 October 8

  \par Mods Modification History:
<pre>  
  2014 Oct 8 - based on a typical isis client loadconfig, but much
               reduced for the relay function [rwp/osu]
</pre>
 
*/

#include "relay.h"   // ISIS relay application header file

/*!
  \brief Load/Parse ISIS relay's runtime configuration file.
  \param cfgfile Path/name of the relay runtime configuration file
  \return 0 if success, <0 if failure.  All error message are printed 
  to the client's console.

*/

int 
loadConfig(char *cfgfile)
{
  char keyword[MAXCFGLINE];  // File is organized into KEYWORD VALUE pairs
  char args[MAXCFGLINE];     // Generic argument buffer
  char argbuf[MAXCFGLINE];   // Generic sub-arg buffer
  char inbuf[MAXCFGLINE];    // Generic input buffer
  char reply[256];           // reply buffer

  FILE *cfgFP;               // Configuration file pointer
  int i;
  char c;                    

  int errcount;
  int nproc;

  // If we need to initialize any default parameter values, do it here.
  // Note that as-written these variables have been defined in global scope
  // for the entire relay application, e.g., in main.c

  // Record the runtime config file in use.

  strcpy(client.rcFile,cfgfile);

  // We use a subset of the ISIS client data structure, turning off
  // features we don't need for the relay application

  // ISIS server information (Defaults defined in the client.h header):

  client.useISIS = 0;  // We are not actually an ISIS client per-se
  strcpy(client.isisHost,DEFAULT_ISISHOST); 
  client.isisPort = DEFAULT_ISISPORT;       
  strcpy(client.isisID,DEFAULT_ISISID);     

  // Client information (defaults in client.h):

  client.Port = DEFAULT_MYPORT;       // client default port number

  gethostname(client.Host,sizeof(client.Host));   // client hostname

  // Client runtime parameters

  client.doLogging = 0;                   // default: runtime logging enabled 
  strcpy(client.logFile,DEFAULT_LOGFILE); // default client runtime log filename

  client.isVerbose = 0;                   // default: not verbose (concise)
  relay.verboseMode = 0;
  client.Debug = 0;                       // default: no debugging

  // Default Port settings

  relay.ttySpeed = 9600;
  relay.ttyDataBits = 8;
  relay.ttyStopBits = 1;
  relay.ttyParity = 0;

  // Now open the config file, if not, gripe and return -1.  Opening the
  // file here ensures that sensible defaults are set even if the config
  // file stuff was in error.

  if (!(cfgFP=fopen(cfgfile,"r"))) {
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

  errcount = 0;
  nproc = 0;

  while(fgets(inbuf, MAXCFGLINE, cfgFP)) {

    // Skip comments (#) and blank lines

    if ((inbuf[0]!='#') && (inbuf[0]!='\n') && inbuf[0]!='\0') {
      inbuf[MAXCFGLINE] ='\0';

      sscanf(inbuf,"%s %[^\n]",keyword,args);

      //------------------------------
      // Keywords:
      //

      // UDPPORT: UDP socket port number of the internet-facing
      //    side of the relay.
      //    Host is assumed to be localhost (can't be anything else)

      if (strcasecmp(keyword,"UDPPORT")==0) {
	GetArg(inbuf, 2, argbuf);
	client.Port = atoi(argbuf);
	relay.udpPort = atoi(argbuf);
      }

      // TTYPORT: TTY port for the local side of the relay

      else if (strcasecmp(keyword,"TTYPORT")==0) {
	GetArg(inbuf, 2, argbuf);
	strcpy(relay.ttyPort,argbuf);
      }

      // SPEED: TTY port speed in baud 

      else if (strcasecmp(keyword,"SPEED")==0) {
	GetArg(inbuf, 2, argbuf);
	relay.ttySpeed = atoi(argbuf);
      }

      // DATABITS: TTY port number of data bits (usually 8)

      else if (strcasecmp(keyword,"DATABITS")==0) {
	GetArg(inbuf, 2, argbuf);
	relay.ttyDataBits = atoi(argbuf);
      }

      // STOPBITS: TTY port number of stop bits (1 or 2)

      else if (strcasecmp(keyword,"STOPBITS")==0) {
	GetArg(inbuf, 2, argbuf);
	relay.ttyStopBits = atoi(argbuf);
      }

      // PARITY: TTY port parity (0 or 1)

      else if (strcasecmp(keyword,"PARITY")==0) {
	GetArg(inbuf, 2, argbuf);
	relay.ttyParity = atoi(argbuf);
      }

      // ISISHost: Hostname of the machine running the ISIS server.
      //           Must be a resolvable name or an IP address.

      else if (strcasecmp(keyword,"ISISHOST")==0) {
	GetArg(inbuf,2,argbuf);
	strcpy(client.isisHost,argbuf);
      }
	
      // ISISPort: network socket port number used by the ISIS server 
      //           running on isisHost
							  
      else if (strcasecmp(keyword,"ISISPORT")==0) {
	GetArg(inbuf, 2, argbuf);
	client.isisPort = atoi(argbuf);
      }

      // LogFile: Runtime log file rootname (including path) 
      //
      // The .log extension will be appended to this rootname. 

      else if (strcasecmp(keyword,"LOGFILE")==0) { 
	GetArg(inbuf, 2, argbuf);
	strcpy(client.logFile, argbuf);
	client.doLogging = 1;
      }

      // NOLOG: Explicitly disable the runtime logging

      else if (strcasecmp(keyword,"NOLOG")==0) {
	client.doLogging = 0;
	
      }
      
      // Verbose: Enable verbose output mode (e.g., for debugging)
      //          We only switch on the relay-specific verbose
      //          output, leaving client verbose output "concise"

      else if (strcasecmp(keyword,"VERBOSE")==0) {
	relay.verboseMode = 1;
	
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

  if (errcount>0) {
    printf("Errors occurred in processing the runtime config file\n");
    return -1;
  }

  return(0);

}

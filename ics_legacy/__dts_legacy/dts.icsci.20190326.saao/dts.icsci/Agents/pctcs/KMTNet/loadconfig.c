//---------------------------------------------------------------------------
//
// Loadconfig() - load an ISIS client's runtime configuration file, 
//                modified for KMTNet TCS Agent initialization
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
//   2003 September 14 (original version - Yale1m v3.3.1)
//
//   S. Cha, KASI KMTNet team
//   chasm@kasi.re.kr
//   2014 April 1 (KMTNet version)
//
// Modification History:
//   2003 Sep 14: based on the ISIS server ParseIniFile.c program, but
//                stripped of server-specific code [rwp/osu]
//   2004 Feb 19: modified for pctcs [rwp/osu]
//   2014 Apr 30: modified for KMTNet TCS Agent [sc/kasi]
//   2015 Jan 17: Site name 'AUX_SITEID' added in RC file (v1.4.2) [sc/kasi]
//   2015 Feb 12: Keyword AUX_SITEID changed to FITS_TELID (v1.4.5) [sc/kasi]
//
//
//---------------------------------------------------------------------------

#include "pctcs.h"      // PC-TCS interface agent header

#define MAXCFGLINE 80   // maximum mumber of characters/line of the file

extern isisclient_t client;  // global client runtime config table
extern pctcs_t tcs;
extern auxctrl_t aux;
extern tcsagent_t agent;

int SetHostAddr(char *HostName, int Port, sockaddr_in *Addr);

//---------------------------------------------------------------------------

int 
LoadConfig(const char *cfgfile)
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

  //
  // Start of default configuration setting
  //

  // ISIS server information (Defaults defined in the pctcs.h header):

  client.useISIS = 0;                    // default: STANDALONE mode rather
                                         //          than an ISIS client
  strcpy(client.isisID  ,DEFAULT_ISISID  );
  strcpy(client.isisHost,DEFAULT_ISISHOST);
  client.isisPort = DEFAULT_ISISPORT;       

  // Client information (defaults in pctcs.h):

  strcpy(client.ID,DEFAULT_MYID);     // client default ISIS node name
  client.Port = DEFAULT_MYPORT;       // client default port number
  gethostname(client.Host,sizeof(client.Host));   // client hostname

  // Client runtime parameters

  client.doLogging = DEFAULT_DOLOG;       // default runtime logging flag
  strcpy(client.logFile,DEFAULT_LOGFILE); // default client runtime log filename

  client.isVerbose = DEFAULT_VERBOSE;     // default verbose mode
  client.Debug = DEFAULT_DEBUG;           // default debugging mode

  // PC-TCS Telcom server info ...
  
  strcpy(tcs.Host,DEFAULT_TCS_HOST);     // default Telcom server host name
  tcs.PortNum = DEFAULT_TCS_PORT;        // default Telcom server port number
  strcpy(tcs.TelID, DEFAULT_TCS_TELID);  // telescope ID for PCTCS-NG protocol
  strcpy(tcs.SysID, DEFAULT_TCS_SYSID);  // system ID for PCTCS-NG protocol
  
  if (tcs.FDtel > 0) close(tcs.FDtel);   // PC-TCS connection closed at startup
  tcs.FDtel = -1;
  tcs.Link = TCS_DOWN;
  if (tcs.FDcmd > 0) close(tcs.FDcmd);   // PC-TCS connection closed at startup
  tcs.FDcmd = -1;
  tcs.Link = TCS_DOWN;

  // PC-TCS parameters of interest ...

  tcs.UpdateInt     = DEFAULT_UPINT_TCS;           // default TCS update interval
  tcs.PctcsTimeout  = DEFAULT_TIMEOUT_PCTCS;       // default timeout for PCTCS serial link
  tcs.TelcomTimeout = DEFAULT_TIMEOUT_TELCOM;      // default timeout for Telcom tcp link
  tcs.ArcMode       = DEFAULT_AUTORECOVERY_TCS;    // default TCS link auto recovery mode
  tcs.GuideStepRA   = DEFAULT_TCS_GUIDE_STEP_RA;   // default RA guide step
  tcs.GuideStepDec  = DEFAULT_TCS_GUIDE_STEP_DEC;  // default Dec guide step
  tcs.GuideMinOffRA = DEFAULT_TCS_GUIDE_MINOFF_RA; // default RA minimun guide offset
  tcs.GuideMinOffDec= DEFAULT_TCS_GUIDE_MINOFF_DEC;// default Dec minimun guide offset

  // AUX control server info ...
  
  strcpy(aux.Host,DEFAULT_AUX_HOST);      // default AUX server host name
  aux.PortNum = DEFAULT_AUX_PORT;         // default AUX server port number
  strcpy(aux.TelID, DEFAULT_AUX_TELID);   // telescope ID for AUX remote command
  strcpy(aux.SysID, DEFAULT_AUX_SYSID);   // system ID for AUX remote command

  strcpy(aux.FitsTelID, DEFAULT_FITS_TELID); // Temporary, telescope name for AUXSTATUS/ASTAT string --> this info will be get from AUX

  // AUX parameters of interest ...

  aux.UpdateInt         = DEFAULT_UPINT_AUX;         // default AUX update interval
  aux.ArcMode           = DEFAULT_AUTORECOVERY_AUX;  // default AUX link auto recovery mode
  aux.FS_FilterOpTime   = DEFAULT_AUX_FILTER_OPTIME; // filter slide operation time
  aux.FS_ShutOpTime     = DEFAULT_AUX_CSHUTT_OPTIME; // shutter operation time
  aux.FA_ActNums[SOUTH] = DEFAULT_AUX_ACTNUM_SOUTH;  // south actuator number
  aux.FA_ActNums[EAST]  = DEFAULT_AUX_ACTNUM_EAST;   // east actuator number
  aux.FA_ActNums[WEST]  = DEFAULT_AUX_ACTNUM_WEST;   // west actuator number

  // TCS Agent application runtime parameters

  agent.ArcInt = DEFAULT_ARCINT;  // tcs & aux links auto recovery trying interval

  //
  // End of default configuration setting
  //

  // Now to open the config file, if not, gripe and return -1.  Opening
  // the file here ensures that sensible defaults are set even if the
  // config file stuff was in error.

  if (!(cfgFP=fopen(cfgfile, "r"))) {
    printf("  Error: Cannot open runtime configuration file %s\n",cfgfile);
    printf("         %s\n",strerror(errno));
    printf("         default rcfile path is '%s'\n", DEFAULT_RCFILE);
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
      
      //
      // Client configuration parameters
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
          printf("  Error: Mode option '%s' unrecognized\n",argbuf);
          printf("         Must be STANDALONE or ISISCLIENT\n");
          printf("  >> fix the config file (%s) and try again\n",client.rcFile);
          return(-1);
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
      //       assumed to be localhost (since it can't be anything else)

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
      }

      // NOLOG: Explicitly disable the runtime logging

      else if (strcasecmp(keyword, "DOLOG")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          client.doLogging = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          client.doLogging = 0;
        else {
          printf("  Warning: DOLOG flag is '%s' unrecognized\n",argbuf);
          client.doLogging = DEFAULT_DOLOG;
          printf("  >> changed to defalut setting: %s\n", client.doLogging?"on":"off");
        }
      }
      
      // Verbose: Enable verbose output mode (e.g., for debugging)

      else if (strcasecmp(keyword, "VERBOSE")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          client.isVerbose = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          client.isVerbose = 0;
        else {
          printf("  Warning: VERBOSE flag is '%s' unrecognized\n",argbuf);
          client.isVerbose = DEFAULT_VERBOSE;
          printf("  >> changed to defalut setting: %s\n", client.isVerbose?"on":"off");
        }
      }

      // Debug: Enable runtime debugging out (superverbose mode)

      else if (strcasecmp(keyword, "DEBUG")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          client.Debug = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          client.Debug = 0;
        else {
          printf("  Warning: DEBUG flag is '%s' unrecognized\n",argbuf);
          client.Debug = DEFAULT_DEBUG;
          printf("  >> changed to defalut setting: %s\n", client.Debug?"on":"off");
        }
      }

      // ARCINT - TCS & AUX links auto recovery trying interval

      else if (strcasecmp(keyword, "ARCINT")==0) {
        GetArg(inbuf,2,argbuf);
        agent.ArcInt = atof(argbuf);
        if (agent.ArcInt < MIN_ARCINT) {
          printf("  Warning: ARCINT is %.2f unrecognized\n",agent.ArcInt);
          agent.ArcInt = DEFAULT_ARCINT;
          printf("  >> changed to defalut value: %.2f sec\n",agent.ArcInt);
        }
      }

      //
      // TCS server (PC-TCS Telcom) parameters
      //

      else if (strcasecmp(keyword, "TCS_HOST")==0) {
        GetArg(inbuf,2,argbuf);
        strcpy(tcs.Host, argbuf);
      }

      else if (strcasecmp(keyword, "TCS_PORT")==0) {
        GetArg(inbuf,2,argbuf);
        tcs.PortNum = atoi(argbuf);
      }

      else if (strcasecmp(keyword, "TCS_TELID")==0) {
        GetArg(inbuf,2,argbuf);
        strcpy(tcs.TelID, argbuf);
      }

      else if (strcasecmp(keyword, "TCS_SYSID")==0) {
        GetArg(inbuf,2,argbuf);
        strcpy(tcs.SysID, argbuf);
      }

      //
      // TCS communication control parameters
      //

      // UPDATEINT - tcs telemetry update interval

      else if (strcasecmp(keyword, "UPDATEINT_TCS")==0) {
        GetArg(inbuf,2,argbuf);
        tcs.UpdateInt = atof(argbuf);
        if (tcs.UpdateInt < MIN_UPDATEINT_TCS) {
          printf("  Warning: UPDATEINT_TCS is %.2f unrecognized\n",tcs.UpdateInt);
          tcs.UpdateInt = DEFAULT_UPINT_TCS;
          printf("  >> changed to defalut value: %.2f sec\n",tcs.UpdateInt);
        }
      }

      // TCS Link timeout
      //
      // TIMEOUT_PCTCS  - interval of time after which the PC-TCS serial link
      //                  between Telcom and PC_TCS is judged to be idle
      // TIMEOUT_TELCOM - interval of time after which the Telcom tcp link
      //                  between TCS Agent and Telcom is judged to be down
      // * PC-TCS telemetry typically hits the port 5 times/sec
      // * Telcom-TCSAgent communication is able to be performed 1 times/sec

      else if (strcasecmp(keyword, "TIMEOUT_PCTCS")==0) {
        GetArg(inbuf,2,argbuf);
        tcs.PctcsTimeout = atoi(argbuf);
        if (tcs.PctcsTimeout <= 0) {
          printf("  Warning: TIMEOUT_PCTCS is %d unrecognized\n",tcs.PctcsTimeout);
          tcs.PctcsTimeout = DEFAULT_TIMEOUT_PCTCS;
          printf("  >> changed to defalut value: %d sec\n",tcs.PctcsTimeout);
        }
      }

      else if (strcasecmp(keyword, "TIMEOUT_TELCOM")==0) {
        GetArg(inbuf,2,argbuf);
        tcs.TelcomTimeout = atoi(argbuf);
        if (tcs.TelcomTimeout <= 0) {
          printf("  Warning: TIMEOUT_Telcom is %d unrecognized\n",tcs.TelcomTimeout);
          tcs.TelcomTimeout = DEFAULT_TIMEOUT_TELCOM;
          printf("  >> changed to defalut value: %d sec\n",tcs.TelcomTimeout);
        }
      }

      // AUTORECOVERY_TCS - TCS tcp link auto recovery mode (on:1, off:0)

      else if (strcasecmp(keyword, "AUTORECOVERY_TCS")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          tcs.ArcMode = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          tcs.ArcMode = 0;
        else {
          printf("  Warning: AUTORECOVERY_TCS flag is '%s' unrecognized\n",argbuf);
          tcs.ArcMode = DEFAULT_AUTORECOVERY_TCS;
          printf("  >> changed to defalut setting: %s\n", tcs.ArcMode?"on":"off");
        }
      }

      //
      // TCS HW configuration
      //

      // RA/Dec guide step (arcsec/encoder count)

      else if (strcasecmp(keyword, "TCS_GUIDE_STEP_RA")==0) {
        GetArg(inbuf,2,argbuf);
        tcs.GuideStepRA = atof(argbuf);
        if ( tcs.GuideStepRA < 0.000001 || tcs.GuideStepRA > 0.1 ) {
          printf("  Error: GUIDE_STEP_RA is %.6f unrecognized\n",tcs.GuideStepRA);
          printf("  >> fix the config file (%s) and try again\n",client.rcFile);
          return(-1);
        }
      }

      else if (strcasecmp(keyword, "TCS_GUIDE_STEP_DEC")==0) {
        GetArg(inbuf,2,argbuf);
        tcs.GuideStepDec = atof(argbuf);
        if ( tcs.GuideStepDec < 0.000001 || tcs.GuideStepDec > 0.1 ) {
          printf("  Error: GUIDE_STEP_DEC is %.6f unrecognized\n",tcs.GuideStepDec);
          printf("  >> fix the config file (%s) and try again\n",client.rcFile);
          return(-1);
        }
      }

      // RA/Dec minimun guiding offset (arcsec)

      else if (strcasecmp(keyword, "TCS_GUIDE_MINOFF_RA")==0) {
        GetArg(inbuf,2,argbuf);
        tcs.GuideMinOffRA = atof(argbuf);
        if ( tcs.GuideMinOffRA < 0.0 || tcs.GuideMinOffRA > 60.0 ) {
          printf("  Warning: GUIDE_MINOFF_RA is %.4f unrecognized\n",tcs.GuideMinOffRA);
          tcs.GuideMinOffRA = DEFAULT_TCS_GUIDE_MINOFF_RA;
          printf("  >> changed to defalut setting: %.4f\n", tcs.GuideMinOffRA);
        }
      }

      else if (strcasecmp(keyword, "TCS_GUIDE_MINOFF_DEC")==0) {
        GetArg(inbuf,2,argbuf);
        tcs.GuideMinOffDec = atof(argbuf);
        if ( tcs.GuideMinOffDec < 0.0 || tcs.GuideMinOffDec > 60.0 ) {
          printf("  Warning: GUIDE_MINOFF_DEC is %.4f unrecognized\n",tcs.GuideMinOffDec);
          tcs.GuideMinOffDec = DEFAULT_TCS_GUIDE_MINOFF_DEC;
          printf("  >> changed to defalut setting: %.4f\n", tcs.GuideMinOffDec);
        }
      }

      //
      // AUX server parameters
      //

      else if (strcasecmp(keyword, "AUX_HOST")==0) {
        GetArg(inbuf,2,argbuf);
        strcpy(aux.Host, argbuf);
      }

      else if (strcasecmp(keyword, "AUX_PORT")==0) {
        GetArg(inbuf,2,argbuf);
        aux.PortNum = atoi(argbuf);
      }

      else if (strcasecmp(keyword, "AUX_TELID")==0) {
        GetArg(inbuf,2,argbuf);
        strcpy(aux.TelID, argbuf);
      }

      else if (strcasecmp(keyword, "AUX_SYSID")==0) {
        GetArg(inbuf,2,argbuf);
        strcpy(aux.SysID, argbuf);
      }

      else if (strcasecmp(keyword, "FITS_TELID")==0) {
        GetArg(inbuf,2,argbuf);
        strcpy(aux.FitsTelID, argbuf);
      }

      //
      // AUX communication control parameters
      //

      // UPDATEINT_AUX - aux telemetry update interval for each subsystem

      else if (strcasecmp(keyword, "UPDATEINT_AUX")==0) {
        GetArg(inbuf,2,argbuf);
        aux.UpdateInt = atof(argbuf);
        if (aux.UpdateInt < MIN_UPDATEINT_AUX) {
          printf("  Warning: UPDATEINT_AUX is %.2f unrecognized\n",aux.UpdateInt);
          aux.UpdateInt = DEFAULT_UPINT_AUX;
          printf("  >> changed to defalut value: %.2f sec\n",aux.UpdateInt);
        }
      }

      // AUTORECOVERY_AUX - AUX tcp link auto recovery mode (on:1, off:0)

      else if (strcasecmp(keyword, "AUTORECOVERY_AUX")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          aux.ArcMode = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          aux.ArcMode = 0;
        else {
          printf("  Warning: AUTORECOVERY_AUX flag is '%s' unrecognized\n",argbuf);
          aux.ArcMode = DEFAULT_AUTORECOVERY_AUX;
          printf("  >> changed to defalut setting: %s\n", aux.ArcMode?"on":"off");
        }
      }

      //
      // AUX HW configuration
      //

      // AUX Filter/Shutter operation time

      else if (strcasecmp(keyword, "AUX_FS_FILTER_OPTIME")==0) {
        GetArg(inbuf,2,argbuf);
        aux.FS_FilterOpTime = atof(argbuf);
        if (aux.FS_FilterOpTime <= 0.0) {
          printf("  Warning: AUX_FS_FILTER_OPTIME is %.2f unrecognized\n",
                  aux.FS_FilterOpTime);
          aux.FS_FilterOpTime = DEFAULT_AUX_FILTER_OPTIME;
          printf("  >> changed to defalut value: %.2f sec\n",aux.FS_FilterOpTime);
        }
      }

      else if (strcasecmp(keyword, "AUX_FS_SHUTTER_OPTIME")==0) {
        GetArg(inbuf,2,argbuf);
        aux.FS_ShutOpTime = atof(argbuf);
        if (aux.FS_ShutOpTime <= 0.0) {
          printf("  Warning: AUX_FS_SHUTTER_OPTIME is %.2f unrecognized\n",
                  aux.FS_ShutOpTime);
          aux.FS_ShutOpTime = DEFAULT_AUX_CSHUTT_OPTIME;
          printf("  >> changed to defalut value: %.2f sec\n",aux.FS_ShutOpTime);
        }
      }

      // AUX Focuser actuator number for the orientation

      else if (strcasecmp(keyword, "AUX_FA_ACTNUM_SOUTH")==0) {
        GetArg(inbuf,2,argbuf);
        aux.FA_ActNums[SOUTH] = atoi(argbuf);
        if ( aux.FA_ActNums[SOUTH] < 1 || aux.FA_ActNums[SOUTH] > 3 ) {
          printf("  Error: AUX_FA_ACTNUM_SOUTH is %d unrecognized\n",
                  aux.FA_ActNums[SOUTH]);
          printf("         Must be 1, 2 or 3\n");
          printf("  >> fix the config file (%s) and try again\n",client.rcFile);
          return(-1);
        }
      }

      else if (strcasecmp(keyword, "AUX_FA_ACTNUM_EAST")==0) {
        GetArg(inbuf,2,argbuf);
        aux.FA_ActNums[EAST] = atoi(argbuf);
        if ( aux.FA_ActNums[EAST] < 1 || aux.FA_ActNums[EAST] > 3 ) {
          printf("  Error: AUX_FA_ACTNUM_SOUTH is %d unrecognized\n",
                  aux.FA_ActNums[EAST]);
          printf("         Must be 1, 2 or 3\n");
          printf("  >> fix the config file (%s) and try again\n",client.rcFile);
          return(-1);
        }
      }

      else if (strcasecmp(keyword, "AUX_FA_ACTNUM_WEST")==0) {
        GetArg(inbuf,2,argbuf);
        aux.FA_ActNums[WEST] = atoi(argbuf);
        if ( aux.FA_ActNums[WEST] < 1 || aux.FA_ActNums[WEST] > 3 ) {
          printf("  Error: AUX_FA_ACTNUM_SOUTH is %d unrecognized\n",
                  aux.FA_ActNums[WEST]);
          printf("         Must be 1, 2 or 3\n");
          printf("  >> fix the config file (%s) and try again\n",client.rcFile);
          return(-1);
        }
      }

      // gripe if scruff is in the config file

      else { 
        GetArg(inbuf,1,argbuf);
        printf("  Ignoring unrecognized config file entry - '%s..'\n", argbuf);        
      }

    } // if(!#)

    memset(inbuf,0,sizeof(inbuf)); 

  } // while()

  // checking for Telcom and AUX server info

  if(SetHostAddr(tcs.Host, tcs.PortNum, &tcs.Addr) < 0) {
    printf("  Error: cannot resolve Telcom server hostname '%s'\n",tcs.Host);
    printf("         %s\n", hstrerror(h_errno));
    printf("  >> check the hostname and TCP_HOST in config file\n");
    return(-1);
  }

  if(SetHostAddr(aux.Host, aux.PortNum, &aux.Addr) < 0) {
    printf("  Error: cannot resolve AUX server hostname '%s'\n",aux.Host);
    printf("         %s\n", hstrerror(h_errno));
    printf("  >> check the hostname and AUX_HOST in config file\n");
    return(-1);
  }

  // checking for AUX Focuser actuator number for the orientation

  if ( aux.FA_ActNums[SOUTH]==aux.FA_ActNums[EAST] || 
       aux.FA_ActNums[EAST] ==aux.FA_ActNums[WEST] || 
       aux.FA_ActNums[WEST] ==aux.FA_ActNums[SOUTH] ) {
    printf("  Error: Focuser Actuator numbers are overlapped\n");
    printf("  >> fix the config file (%s) and try again\n",client.rcFile);
    return(-1);
  }

  // all done, close the config file and return 

  if (cfgFP!=0)
    fclose(cfgFP);

  // Display all configuration for Debug

  if(client.Debug) {
    printf("\n");
    printf("--------------------------------------------------\n");
    printf("DEBUG: Runtion configuration loaded..\n"             );
    printf("  Application mode & flag settings\n"                );
    printf("    App. mode   : %s\n", client.useISIS?"ISISclient":"standalone");
    printf("    Verbose     : %s\n", client.isVerbose?"on":"off" );
    printf("    DebugMsg    : %s\n", client.Debug?"on":"off"     );
    printf("    Logging     : %s\n", client.doLogging?"on":"off" );
    printf("    Log file    : %s\n", client.logFile              );
    printf("  ISIS\n"                                            );
    printf("    ID          : %s\n", client.isisID               );
    printf("    Host        : %s\n", client.isisHost             );
    printf("    Port        : %d\n", client.isisPort             );
    printf("  TCS Agent\n"                                       );
    printf("    ID          : %s\n", client.ID                   );
    printf("    Host        : %s\n", client.Host                 );
    printf("    Port        : %d\n", client.Port                 );
    printf("  PCTCS Telcom\n"                                    );
    printf("    Host        : %s\n", tcs.Host                    );
    printf("    Addr        : %s\n", inet_ntoa(tcs.Addr.sin_addr));
    printf("    Port        : %d\n", tcs.PortNum                 );
    printf("    TelID       : %s\n", tcs.TelID                   );
    printf("    SysID       : %s\n", tcs.SysID                   );
    printf("    PctTimeout  : %d\n", tcs.PctcsTimeout            );
    printf("    TelTimeout  : %d\n", tcs.TelcomTimeout           );
    printf("  AUX ctrl server\n"                                 );
    printf("    Host        : %s\n", aux.Host                    );
    printf("    Addr        : %s\n", inet_ntoa(aux.Addr.sin_addr));
    printf("    Port        : %d\n", aux.PortNum                 );
    printf("    TelID       : %s\n", aux.TelID                   );
    printf("    SysID       : %s\n", aux.SysID                   );
    printf("  Telemetry update intervals\n"                      );
    printf("    TCS interval: %.2f\n", tcs.UpdateInt             );
    printf("    AUX interval: %.2f\n", aux.UpdateInt             );
    printf("  Links auto recovery setting\n"                     );
    printf("    TCS ARC mode: %s\n", tcs.ArcMode?"on":"off"      );
    printf("    AUX ARC mode: %s\n", aux.ArcMode?"on":"off"      );
    printf("    ARC interval: %.2f\n", agent.ArcInt              );
    printf("  Hardware configurations\n"                         );
    printf("    GuideStepRA : %.8f\n", tcs.GuideStepRA           );
    printf("    GuideStepDec: %.8f\n", tcs.GuideStepDec          );
    printf("    GuideMinRA  : %.2f\n", tcs.GuideMinOffRA         );
    printf("    GuideMinDec : %.2f\n", tcs.GuideMinOffDec        );
    printf("    FilterOpTime: %.2f\n", aux.FS_FilterOpTime       );
    printf("    CShuttOpTime: %.2f\n", aux.FS_ShutOpTime         );
    printf("    ActNumSouth : %d\n", aux.FA_ActNums[SOUTH]       );
    printf("    ActNumEast  : %d\n", aux.FA_ActNums[EAST]        );
    printf("    ActNumWest  : %d\n", aux.FA_ActNums[WEST]        );
    printf("--------------------------------------------------\n");
    printf("\n"                                                  );
  }

  return(0);

}


//---------------------------------------------------------------------------
//
// Utility functions for network communication
//
//---------------------------------------------------------------------------


// SetHostAddr: setting sockaddr_in structure from hostname, port number
//              based on InitISISServer(isisclient_t *client)

int
SetHostAddr(char *HostName, int Port, sockaddr_in *Addr)
{
  struct hostent *host;

  // translate the server hostname into an IP address 

  if (!(host=gethostbyname(HostName))) {
    return -1;
  }

  // Setup the server's socket address database 

  Addr->sin_port = htons(Port);
  Addr->sin_family = AF_INET;
  memcpy(&Addr->sin_addr, host->h_addr, host->h_length);

  return 0;
}

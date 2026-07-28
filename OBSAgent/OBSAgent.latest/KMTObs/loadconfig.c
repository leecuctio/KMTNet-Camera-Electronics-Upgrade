//------------------------------------------------------------------------------
//
// LoadConfig() - load an ISIS client's runtime configuration file, 
//                modified for KMTNet OBS Agent initialization
//
// LoadCatalog() - load an RA/Dec object catalog file,
//                 created for BLG offset correction at v1.5.1
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
//   2003 Sep 14 (TCSAgent original version - agent pctcs for Yale1m v3.3.1)
//
//   S. Cha, KASI KMTNet team
//   chasm@kasi.re.kr
//   2014 Apr  1 (TCSAgent KMTNet version)
//   2016 Sep 20 (OBSAgent for KMTNet system)
//
// Modification History:
//   2016 Sep 20: OBSAgent v0.0 re-creation re-using TCSAgent flatform and code [sc/kasi]
//   2017 Aug 07: Replaced old code with new improved code of TCSAtgent v1.6.6 (v0.0.4)
//                Added new RC value for time tag display option (v0.0.5)
//   2017 Aug 20: Removed codes and comments regarding TCS/AUX from TCSAgent (v0.0.6)
//   2017 Dec 24: Observation script loading function (v0.0.7)
//   2017 Dec 31: new config keywords: 
//                DBGLOG: on/off to log debugging messages on the 'debug' log (making another log file for debugging message log) (v0.0.8)
//                OBSLOG: on/off to log script obs results on the 'scrobs' log, (making another log file for script obs results log) (v0.0.8)
//   2018 Jan 12: TCS limit information update with runtime configuration for each site (v0.2.6)
//   2020 Sep 18: Telescope tcs_latitude/longitude/elevation update with runtime configuration, 
//                debugging for the case of CRLF line in osc (v0.4.0)
//   2020 Sep 19: Telescope tcs_tolerance update with runtime configuration (v0.4.1)
//   2020 Sep 20: Telescope tcs_tolerance_pointing and tcs_tolerance_tracking update with runtime configuration (v0.4.2)
//   2020 Oct 14: TCS_TOLERANCE_POINTING/_TRACKING input limit adjested (v0.4.8)
//   2020 Nov 27: max_object_label got during osc importing, line display improved on verbose mode (v0.5.0)
//   2020 Dec 01: TimeTag disabling during loading a ObsScript with the agent.isBlockTimeTag flag (v0.5.0)
//   2021 Mar 03: ecmd_dlamp & ecmd_mcfan string setup when isisHost loading, 
//                test for ecmd_dlamp_get_state & ecmd_mcfan_get_state at the end of RC loading (v0.5.1)
//   2021 Mar 25: modification for printing command lines & for the script having command lines only with 
//                removal of codes to check the exp line number in LoadObsScript() (v0.6.2)
//   2021 Apr 08: ProjID importing during loading a script in LoadObsScript(), Error message output with neg return of 
//                LoadObsScript() even if there is only one line invalid (v0.6.4)
//   2021 Jun 21: ICS_DATASOURCE for sys.ics_datasource loading in LoadConifg() (v0.6.6)
//   2022 Jul 12: web relay default configs, set/get commands setup, and debugging codes (v0.6.8)
//                VELRA/VELDEC importing from osc (v0.6.9)
//   2022 Jul 14: UT_OBS/UT_TOL importing and checking codes (v0.7.0-v0.7.3)
//   2022 Aug 24: UT_TOL importing modified (v0.8.0), minimum UT_TOL applied (v0.8.2)
//   2022 Aug 27: debugging UT_TOL importing error in case UT_TOL=0 (v0.8.4)
//   2022 Aug 29: web relay set/get commands including XML port numbers for port forwarding (v0.8.5)
//                TCS spec setup with default spec mecros for slewing speed, settling down time, dome rotating/shutter speed (v0.8.7)
//   2023 Mar 04: Append importing tcs_allowance_unstable from TCS_UNSTABLE_HYSTERESIS value in RC (v0.9.1)
//   2023 Nov 06: Replace _msgout() with _dbgmsgout() when loading UTOBS, 
//                Add an option to omit UTObs & UTTol columns in the observation script (v0.9.2)
//   2024 Jun 18: Add setting TCS redis server configuration (v0.9.3)
//   2024 Jun 24: Refactory setting relay commands and URL string for Curl option (v0.9.6)
//   2026 Jun 02: Move osc.flag_preparenextexp setting from main() to LoadConfig()/InitOscConfig() to configure with .ini RC (v1.2.0)
//                Add flag_wait_for_shutreload configuration setup (v1.2.0)
//
//
//
//------------------------------------------------------------------------------

#include "obstool.h"      // OBS Agent header

//#define MAXCFGLINE 80   // maximum mumber of characters/line of the file
// --> moved to pctcs.h & extended to 128 at v1.5.2

extern isisclient_t client;  // global client runtime config table
extern obsagent_t agent;     // OBSAgent(this process) configuration & data
extern obssystem_t sys;      // System configuration data

//------------------------------------------------------------------------------

struct Commands {
  char *cmd;        // command name
  int(* action)(char *args, MsgType msgtype, char *reply); // action taken for this command
};

extern struct Commands cmdtab[];  // For checking command line in obsscript
extern int NumCommands;

//------------------------------------------------------------------------------

 int LoadConfig(const char *cfgfile);
void InitObsScript(COSC *posc);
 int LoadObsScript(COSC *posc, const char *oscpath, char *reply);
 int SetHostAddr(char *HostName, int Port, sockaddr_in *Addr);

//------------------------------------------------------------------------------

int 
LoadConfig(const char *cfgfile)
{
  char keyword[MAXCFGLINE+1];  // File is organized into KEYWORD VALUE pairs
  char argbuf[MAXCFGLINE+1];   // Generic argument buffer
  char inbuf[MAXCFGLINE+1];    // Generic input buffer

  int nVal, n, i;
  double dVal;

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

  client.isVerbose  = DEFAULT_VERBOSE;     // default verbose mode
  client.Debug      = DEFAULT_DEBUG;       // default debugging mode
  client.doLogging  = DEFAULT_EVENTLOG;    // default runtime logging flag
  agent.isDebugLog  = DEFAULT_DEBUGLOG;    // default runtime logging flag
  agent.isScrObsLog = DEFAULT_SCROBSLOG;   // default runtime logging flag

  agent.isLogVerbose = DEFAULT_LOGVERBOSE;  // default verbose logging mode
  agent.isTimeTag    = DEFAULT_TIMETAG;     // default time tag display option

  strcpy(client.logFile,DEFAULT_LOGFILE);   // default client runtime log rootname(path/filename)
  strcpy(agent.InitOsc, DEFAULT_INITOSC);   // default observation script file path

  agent.flag_preparenextexp = DEFAULT_PREPARE_NEXT_EXP;      // default about preparing next exposure during exposing / v1.2.0
  agent.flag_wait_for_shutreload = DEFAULT_WAIT_SHUTRELOAD;  // default about waiting for shutter reloading to complete / v1.2.0

  sys.tcs_slewspeed_ra   = DEFAULT_TCS_SLEWSPEED_RA;    // RA  slewspeed in deg/sec
  sys.tcs_slewspeed_dec  = DEFAULT_TCS_SLEWSPEED_DEC;   // DEC slewspeed in deg/sec
  sys.tcs_settledown_ra  = DEFAULT_TCS_SETTLEDOWN_RA;   // RA  settling down time in sec
  sys.tcs_settledown_dec = DEFAULT_TCS_SETTLEDOWN_DEC;  // DEC settling down time in sec
  sys.tcs_domerotspeed   = DEFAULT_TCS_DOMESPEED_ROT;   // Dome rotation speed in deg/sec
  sys.tcs_domeshutspeed  = DEFAULT_TCS_DOMESPEED_SHUT;  // Dome shutter speed in deg/sec
  //// --> RC loading for TCS spec is not yet implemented.


  sys.relay_dlamp_ipaddr     = DEFAULT_RELAY_IP_DLAMP;     // default domeflat lamp relay ip address
  sys.relay_dlamp_portnum    = DEFAULT_RELAY_PORT_DLAMP;   // default domeflat lamp relay XML port number
  sys.relay_dlamp_rlynum     = DEFAULT_RELAY_NUM_DLAMP;    // default domeflat lamp rly port number
  sys.relay_dlight_ipaddr    = DEFAULT_RELAY_IP_DLIGHT;    // default dome LED light relay ip address
  sys.relay_dlight_portnum   = DEFAULT_RELAY_PORT_DLIGHT;  // default dome LED light relay XML port number
  sys.relay_dlight_rlynum    = DEFAULT_RELAY_NUM_DLIGHT;   // default dome LED light rly port number
  sys.relay_mcfan_ipaddr     = DEFAULT_RELAY_IP_MCFAN;     // default mirror cell fan relay ip address
  sys.relay_mcfan_portnum    = DEFAULT_RELAY_PORT_MCFAN;   // default mirror cell fan relay XML port number
  sys.relay_mcfan_rlynum     = DEFAULT_RELAY_NUM_MCFAN;    // default mirror cell fan rly port number
  sys.relay_tcspad_ipaddr    = DEFAULT_RELAY_IP_TCSPAD;    // default pc-tcs paddle relay ip address
  sys.relay_tcspad_portnum   = DEFAULT_RELAY_PORT_TCSPAD;  // default pc-tcs paddle relay XML port number
  sys.relay_tcspad_rn[NORTH] = DEFAULT_RELAY_NUM_TPAD_N;   // default pc-tcs paddle north rly port number
  sys.relay_tcspad_rn[SOUTH] = DEFAULT_RELAY_NUM_TPAD_S;   // default pc-tcs paddle south rly port number
  sys.relay_tcspad_rn[EAST]  = DEFAULT_RELAY_NUM_TPAD_E;   // default pc-tcs paddle east rly port number
  sys.relay_tcspad_rn[WEST]  = DEFAULT_RELAY_NUM_TPAD_W;   // default pc-tcs paddle west rly port number
  sys.relay_tcspad_mode      = DEFAULT_TCSPAD_MODE;        // default pc-tcs paddle mode
  sys.relay_dctrl_ipaddr     = DEFAULT_RELAY_IP_DCTRL;     // default dome controller relay ip address
  sys.relay_dctrl_portnum    = DEFAULT_RELAY_PORT_DCTRL;   // default dome controller relay XML port number
//sys.relay_dctrl_din_drot   = DEFAULT_RELAY_NUM_DROTIN;   // default dome rotation digital input port number
  //// --> RC loading for WebRelay is not yet implemented.

  //
  // End of default configuration setting
  //

  // Now to open the config file, if not, gripe and return -1.  Opening
  // the file here ensures that sensible defaults are set even if the
  // config file stuff was in error.

  if(!(cfgFP=fopen(cfgfile, "r"))) {
    REDTEXT;sprintf(cmsg, "  Error: Cannot open rcfile %s\n",cfgfile);_msgout(cmsg);
    REDTEXT;sprintf(cmsg, "         %s\n",strerror(errno));_msgout(cmsg);
    REDTEXT;sprintf(cmsg, "         default rcfile rootname is '%s'\n", DEFAULT_RCFILE);_msgout(cmsg);
    return(-1);
  }

  //--------------------------------------------------------
  //
  // Config file parser loop
  //
  // Read in each line of the config file and process it 
  //

  while( fgets(inbuf, MAXCFGLINE, cfgFP) ) {

    // Skip comments (#) and blank lines

    //  if((inbuf[0]!='#') && (inbuf[0]!='\n') && inbuf[0]!=NUL) {
    //  
    //  inbuf[MAXCFGLINE] = NUL;
    //  GetArg(inbuf, 1, argbuf);
    //  strcpy(keyword, argbuf);
    //    :
    //
    //////// old code, improved as follows at v0.6.4

    for(n=0;n<MAXCFGLINE;n++) {
      if( inbuf[n]=='#' || inbuf[n]=='\n' || inbuf[n]==NUL ) { n=MAXCFGLINE; break; }
      if( inbuf[n]!=' ' && inbuf[n]!=0x0D ) break;
    }

    if( n != MAXCFGLINE ) {

      strcpy(inbuf, inbuf+n);

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

      if(strcasecmp(keyword,"MODE")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf,"STANDALONE")==0) {
          client.useISIS = 0;
        }
        else if(strcasecmp(argbuf,"ISISCLIENT")==0) {
          client.useISIS = 1;
        }
        else {
          REDTEXT;
          sprintf(cmsg, "  Error: Mode option '%s' unrecognized\n",argbuf            );_msgout(cmsg);
          REDTEXT;
          sprintf(cmsg, "         Must be STANDALONE or ISISCLIENT\n"                );_msgout(cmsg);
          REDTEXT;
          sprintf(cmsg, "   >> fix the config file (%s) and try again\n",client.rcFile);_msgout(cmsg);
          return(-1);
        }
      }

      // ISISID: Node name of the ISIS server.
      // 
      // Only meaningful if MODE ISISCLIENT has been set.
      //

      else if(strcasecmp(keyword, "ISISID")==0) {
        GetArg(inbuf, 2, argbuf);
        strcpy(client.isisID, argbuf);
      }

      // ISISHost: Hostname of the machine running the ISIS server.
      //             May be a resolvable name or an IP address.

      else if(strcasecmp(keyword,"ISISHOST")==0) {
        
        GetArg(inbuf,2,argbuf);
        strcpy(client.isisHost,argbuf);

        sscanf(argbuf, "%*d.%*d.%d.%*d", &nVal);   // setup commands for web relays (v0.6.8)  // port fowarding added (v0.8.4)
        sprintf(sys.rcmd_dlamp_set_on     , "%s%s.%d.%d:%d/%s%d%s > %s", RCMD_SET_CMDHEAD, RCMD_SET_URLHEAD, nVal, sys.relay_dlamp_ipaddr , sys.relay_dlamp_portnum , RCMD_SET_MIDDLE, sys.relay_dlamp_rlynum , RCMD_SET_ON_TAIL  , RCMD_SET_REDIRECT);
        sprintf(sys.rcmd_dlamp_set_off    , "%s%s.%d.%d:%d/%s%d%s > %s", RCMD_SET_CMDHEAD, RCMD_SET_URLHEAD, nVal, sys.relay_dlamp_ipaddr , sys.relay_dlamp_portnum , RCMD_SET_MIDDLE, sys.relay_dlamp_rlynum , RCMD_SET_OFF_TAIL , RCMD_SET_REDIRECT);
        sprintf(sys.rcmd_dlamp_get_stat   , "%s%s.%d.%d:%d/%s%s > %s"  , RCMD_GET_CMDHEAD, RCMD_GET_URLHEAD, nVal, sys.relay_dlamp_ipaddr , sys.relay_dlamp_portnum , RCMD_GET_MIDDLE,                          RCMD_GET_STAT_TAIL, RCMD_GET_REDIRECT);
        sprintf(sys.rcmd_dlight_set_on    , "%s%s.%d.%d:%d/%s%d%s > %s", RCMD_SET_CMDHEAD, RCMD_SET_URLHEAD, nVal, sys.relay_dlight_ipaddr, sys.relay_dlight_portnum, RCMD_SET_MIDDLE, sys.relay_dlight_rlynum, RCMD_SET_ON_TAIL  , RCMD_SET_REDIRECT);
        sprintf(sys.rcmd_dlight_set_off   , "%s%s.%d.%d:%d/%s%d%s > %s", RCMD_SET_CMDHEAD, RCMD_SET_URLHEAD, nVal, sys.relay_dlight_ipaddr, sys.relay_dlight_portnum, RCMD_SET_MIDDLE, sys.relay_dlight_rlynum, RCMD_SET_OFF_TAIL , RCMD_SET_REDIRECT);
        sprintf(sys.rcmd_dlight_get_stat  , "%s%s.%d.%d:%d/%s%s > %s"  , RCMD_GET_CMDHEAD, RCMD_GET_URLHEAD, nVal, sys.relay_dlight_ipaddr, sys.relay_dlight_portnum, RCMD_GET_MIDDLE,                          RCMD_GET_STAT_TAIL, RCMD_GET_REDIRECT);
        sprintf(sys.rcmd_mcfan_set_on     , "%s%s.%d.%d:%d/%s%d%s > %s", RCMD_SET_CMDHEAD, RCMD_SET_URLHEAD, nVal, sys.relay_mcfan_ipaddr , sys.relay_mcfan_portnum , RCMD_SET_MIDDLE, sys.relay_mcfan_rlynum , RCMD_SET_ON_TAIL  , RCMD_SET_REDIRECT);
        sprintf(sys.rcmd_mcfan_set_off    , "%s%s.%d.%d:%d/%s%d%s > %s", RCMD_SET_CMDHEAD, RCMD_SET_URLHEAD, nVal, sys.relay_mcfan_ipaddr , sys.relay_mcfan_portnum , RCMD_SET_MIDDLE, sys.relay_mcfan_rlynum , RCMD_SET_OFF_TAIL , RCMD_SET_REDIRECT);
        sprintf(sys.rcmd_mcfan_get_stat   , "%s%s.%d.%d:%d/%s%s > %s"  , RCMD_GET_CMDHEAD, RCMD_GET_URLHEAD, nVal, sys.relay_mcfan_ipaddr , sys.relay_mcfan_portnum , RCMD_GET_MIDDLE,                          RCMD_GET_STAT_TAIL, RCMD_GET_REDIRECT);
       for(i=0;i<4;i++) {
        sprintf(sys.rcmd_tcspad_set_on [i], "%s%s.%d.%d:%d/%s%d%s > %s", RCMD_SET_CMDHEAD, RCMD_SET_URLHEAD, nVal, sys.relay_tcspad_ipaddr, sys.relay_tcspad_portnum, RCMD_SET_MIDDLE, sys.relay_tcspad_rn[i] , RCMD_SET_ON_TAIL  , RCMD_SET_REDIRECT);
        sprintf(sys.rcmd_tcspad_set_off[i], "%s%s.%d.%d:%d/%s%d%s > %s", RCMD_SET_CMDHEAD, RCMD_SET_URLHEAD, nVal, sys.relay_tcspad_ipaddr, sys.relay_tcspad_portnum, RCMD_SET_MIDDLE, sys.relay_tcspad_rn[i] , RCMD_SET_OFF_TAIL , RCMD_SET_REDIRECT);
        //printf("  %d:  (%s)  (%s)\n", i+1, sys.rcmd_tcspad_set_on[i], sys.rcmd_tcspad_set_off[i]);
       }
        sprintf(sys.rcmd_tcspad_get_stat , "%s%s.%d.%d:%d/%s%s > %s"  , RCMD_GET_CMDHEAD, RCMD_GET_URLHEAD, nVal, sys.relay_tcspad_ipaddr, sys.relay_tcspad_portnum, RCMD_GET_MIDDLE,                          RCMD_GET_STAT_TAIL, RCMD_GET_REDIRECT);
        sprintf(sys.rcmd_drotin_get_stat , "%s%s.%d.%d:%d/%s%s > %s"  , RCMD_GET_CMDHEAD, RCMD_GET_URLHEAD, nVal, sys.relay_dctrl_ipaddr , sys.relay_dctrl_portnum , RCMD_GET_MIDDLE,                          RCMD_GET_STAT_TAIL, RCMD_GET_REDIRECT);
        if(client.Debug) {  //// for checking return from curl for DBG
          sprintf(sys.rcmd_dlamp_get_stat , "%s%s.%d.%d:%d/%s%s", RCMD_GET_CMDHEAD, RCMD_GET_URLHEAD, nVal, sys.relay_dlamp_ipaddr , sys.relay_dlamp_portnum , RCMD_GET_MIDDLE, RCMD_GET_STAT_TAIL);
          sprintf(sys.rcmd_dlight_get_stat, "%s%s.%d.%d:%d/%s%s", RCMD_GET_CMDHEAD, RCMD_GET_URLHEAD, nVal, sys.relay_dlight_ipaddr, sys.relay_dlight_portnum, RCMD_GET_MIDDLE, RCMD_GET_STAT_TAIL);
          sprintf(sys.rcmd_mcfan_get_stat , "%s%s.%d.%d:%d/%s%s", RCMD_GET_CMDHEAD, RCMD_GET_URLHEAD, nVal, sys.relay_mcfan_ipaddr , sys.relay_mcfan_portnum , RCMD_GET_MIDDLE, RCMD_GET_STAT_TAIL);
          sprintf(sys.rcmd_tcspad_get_stat, "%s%s.%d.%d:%d/%s%s", RCMD_GET_CMDHEAD, RCMD_GET_URLHEAD, nVal, sys.relay_tcspad_ipaddr, sys.relay_tcspad_portnum, RCMD_GET_MIDDLE, RCMD_GET_STAT_TAIL);
          sprintf(sys.rcmd_drotin_get_stat, "%s%s.%d.%d:%d/%s%s", RCMD_GET_CMDHEAD, RCMD_GET_URLHEAD, nVal, sys.relay_dctrl_ipaddr , sys.relay_dctrl_portnum , RCMD_GET_MIDDLE, RCMD_GET_STAT_TAIL);
        } 
        switch(nVal) {
          case SYSCFG_IPADDR_CTIO: sys.relay_tcspad_mode = DEFAULT_TCSPAD_MODE_CTIO; break;
          case SYSCFG_IPADDR_SAAO: sys.relay_tcspad_mode = DEFAULT_TCSPAD_MODE_SAAO; break;
          case SYSCFG_IPADDR_SSO : sys.relay_tcspad_mode = DEFAULT_TCSPAD_MODE_SSO ; break;
          default                : sys.relay_tcspad_mode = DEFAULT_TCSPAD_MODE     ; break;  // initially DEFAULT_TCSPAD_MODE = RELAY_TCSPAD_MODE_UNDEF
        }
        if( sys.relay_tcspad_mode == RELAY_TCSPAD_MODE_GUIDE ) { strcpy(sys.tcspad_tcmd_vel_ra, "GUIDERA"); strcpy(sys.tcspad_tcmd_vel_dec, "GUIDEDEC"); }
        else                                                   { strcpy(sys.tcspad_tcmd_vel_ra, "DRIFTRA"); strcpy(sys.tcspad_tcmd_vel_dec, "DRIFTDEC"); }
        
        sprintf(sys.rcmd_drotin_curlopt_url, "%s.%d.%d:%d/%s", RCMD_GET_URLHEAD, nVal, sys.relay_dctrl_ipaddr, sys.relay_dctrl_portnum, RCMD_GET_MIDDLE);  // modified at v0.9.6

        sprintf(sys.redis_host, "192.168.%d.%d", nVal, DEFAULT_REDIS_IP);
        sys.redis_port = DEFAULT_REDIS_PORT;
        sys.redis_timeout.tv_sec = (long)0;
        sys.redis_timeout.tv_usec = (long)(DEFAULT_REDIS_TIMEOUT*1000);  // 100 ms

      }
	
      // ISISPort: network socket port number used by the ISIS server 
      //             running on ServerHost
							  
      else if(strcasecmp(keyword, "ISISPORT")==0) {
        GetArg(inbuf, 2, argbuf);
        client.isisPort = atoi(argbuf);
      }

      // ID: node name of this client 

      else if(strcasecmp(keyword,"ID")==0) {
        GetArg(inbuf,2,argbuf);
        strcpy(client.ID,argbuf);
      }

      // Port: network socket port number of this client.  Host is
      //       assumed to be localhost (since it can't be anything else)

      else if(strcasecmp(keyword, "PORT")==0) {
        GetArg(inbuf, 2, argbuf);
        client.Port = atoi(argbuf);
      }

      // OSC_PREPARE_NEXT_EXP: preparing next exposure during exposing

      else if(strcasecmp(keyword, "OSC_PREPARE_NEXT_EXP")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          agent.flag_preparenextexp = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          agent.flag_preparenextexp = 0;
        else {
          CYATEXT;
          sprintf(cmsg, "  Warning: OSC_PREPARE_NEXT_EXP flag is '%s' unrecognized\n",argbuf);_msgout(cmsg);
          agent.flag_preparenextexp = DEFAULT_PREPARE_NEXT_EXP;
          CYATEXT;
          sprintf(cmsg, "   >> changed to defalut setting: %s\n", agent.flag_preparenextexp?"on":"off");_msgout(cmsg);
        }
      }

      // OSC_WAIT_FOR_SHUTCOMP: preparing next exposure during exposing

      else if(strcasecmp(keyword, "OSC_WAIT_FOR_SHUTCOMP")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          agent.flag_wait_for_shutreload = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          agent.flag_wait_for_shutreload = 0;
        else {
          CYATEXT;
          sprintf(cmsg, "  Warning: OSC_WAIT_FOR_SHUTCOMP flag is '%s' unrecognized\n",argbuf);_msgout(cmsg);
          agent.flag_wait_for_shutreload = DEFAULT_WAIT_SHUTRELOAD;
          CYATEXT;
          sprintf(cmsg, "   >> changed to defalut setting: %s\n", agent.flag_wait_for_shutreload?"on":"off");_msgout(cmsg);
        }
      }

      // ICS_DATASOURCE: Instrument Control System configuration for datasource for x-talk correction

      else if(strcasecmp(keyword, "ICS_DATASOURCE")==0) {
        GetArg(inbuf, 2, argbuf);
        if(strcasecmp(argbuf, "ADC")==0) sys.ics_datasource = ICS_ADC;
        else if(strcasecmp(argbuf, "CTC")==0) sys.ics_datasource = ICS_CTC;
        else {
          CYATEXT;sprintf(cmsg, "  Warning: ICS_DATASOURCE '%s' is unrecognized\n",argbuf);_msgout(cmsg);
          sys.ics_datasource = ICS_UNDEF;
        }
      }

      // TCS_LATITUDE: TCS configuration for telescope position
							  
      else if(strcasecmp(keyword, "TCS_LATITUDE")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal < -90.0 || dVal > +90.0 ) {
          CYATEXT;sprintf(cmsg, "  Warning: TCS_LATITUDE %.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = 0.0;
        }
        sys.tcs_latitude = dVal;
      }

      // TCS_LONGITUDE: TCS configuration for telescope position
							  
      else if(strcasecmp(keyword, "TCS_LONGITUDE")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal <= -360.0 || dVal >= +360.0 ) {
          CYATEXT;sprintf(cmsg, "  Warning: TCS_LONGITUDE %.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = 0.0;
        }
        sys.tcs_longitude = dVal;
      }

      // TCS_ELEVATION: TCS configuration for telescope position
							  
      else if(strcasecmp(keyword, "TCS_ELEVATION")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal < 0.0 || dVal > 10000.0 ) {
          CYATEXT;sprintf(cmsg, "  Warning: TCS_ELEVATION %.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = 0.0;
        }
        sys.tcs_elevation = dVal;
      }

      // TCS_TOLERANCE_POINTING: Tolerance for telescope pointing error
							  
      else if(strcasecmp(keyword, "TCS_TOLERANCE_POINTING")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal < 0.01 || dVal > 60.0 ) {
          CYATEXT;sprintf(cmsg, "  Warning: TCS_TOLERANCE_POINTING %.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = DEFAULT_TCS_TOLERANCE_POINTING;
          CYATEXT;sprintf(cmsg, "   >> changed to defalut setting: %.2f\n", dVal);_msgout(cmsg);
        }
        sys.tcs_tolerance_pointing = dVal;
      }

      // TCS_TOLERANCE_TRACKING: Tolerance for telescope tracking error
      
      else if(strcasecmp(keyword, "TCS_TOLERANCE_TRACKING")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal < 0.01 || dVal > 30.0 ) {
          CYATEXT;sprintf(cmsg, "  Warning: TCS_TOLERANCE_TRACKING %.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = DEFAULT_TCS_TOLERANCE_TRACKING;
          CYATEXT;sprintf(cmsg, "   >> changed to defalut setting: %.2f\n", dVal);_msgout(cmsg);
        }
        sys.tcs_tolerance_tracking = dVal;
      }

      // TCS_UNSTABLE_HYSTERESIS: sys.tcs_allowance_unstable, unstable hysteresis for checking RA/DEC axes oscillation (Typ. 2 or 3)

      else if(strcasecmp(keyword, "TCS_UNSTABLE_HYSTERESIS")==0) {
        GetArg(inbuf, 2, argbuf);
        nVal = atoi(argbuf);
        if( dVal < 0 || nVal > 100 ) {
          CYATEXT;sprintf(cmsg, "  Warning: TCS_UNSTABLE_HYSTERESIS %d is out of range\n",nVal);_msgout(cmsg);
          nVal = DEFAULT_TCS_ALLOWANCE_UNSTABLE;
          CYATEXT;sprintf(cmsg, "   >> changed to defalut setting: %d\n", nVal);_msgout(cmsg);
        }
        sys.tcs_allowance_unstable = nVal;
      }

      // TCS_LIMIT_HA: TCS configiguration for HA limit
							  
      else if(strcasecmp(keyword, "TCS_LIMIT_HA")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal <= 0.0 || dVal > 4.8 ) {  // HW limit = Max. 4.73h
          CYATEXT;sprintf(cmsg, "  Warning: TCS_LIMIT_HA %.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = DEFAULT_TCS_LIMIT_HA;
          CYATEXT;sprintf(cmsg, "   >> changed to defalut setting: %.2f\n", dVal);_msgout(cmsg);
        }
        sys.tcs_limit_ha = dVal;
      }

      // TCS_LIMIT_DEC_N: TCS configiguration for DEC Northern limit
							  
      else if(strcasecmp(keyword, "TCS_LIMIT_DEC_N")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal <= 0.0 || dVal > +45.0 ) {  // Dec +45 deg = Min. Alt 14.8/12.6/13.7 deg on Northern Merdian
          CYATEXT;sprintf(cmsg, "  Warning: TCS_LIMIT_DEC_N %+.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = DEFAULT_TCS_LIMIT_DEC_N;
          CYATEXT;sprintf(cmsg, "   >> changed to defalut setting: %+.2f\n", dVal);_msgout(cmsg);
        }
        sys.tcs_limit_dec_n = dVal;
      }

      // TCS_LIMIT_DEC_S: TCS configiguration for DEC Southern limit
							  
      else if(strcasecmp(keyword, "TCS_LIMIT_DEC_S")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal < -90.0 || dVal > -45.0 ) {  // Dec -45 deg = Min. Alt 75.2/77.4/76.3 deg on Southern Merdian
          CYATEXT;sprintf(cmsg, "  Warning: TCS_LIMIT_DEC_S %+.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = DEFAULT_TCS_LIMIT_DEC_S;
          CYATEXT;sprintf(cmsg, "   >> changed to defalut setting: %+.2f\n", dVal);_msgout(cmsg);
        }
        sys.tcs_limit_dec_s = dVal;
      }

      // TCS_LIMIT_SECZ: TCS configiguration for SecZ limit

      else if(strcasecmp(keyword, "TCS_LIMIT_SECZ")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal < 1.0 || dVal > 4.0 ) {  // SecZ 4.0 = Alt 14.5 deg
          CYATEXT;sprintf(cmsg, "  Warning: TCS_LIMIT_SECZ %.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = DEFAULT_TCS_LIMIT_SECZ;
          CYATEXT;sprintf(cmsg, "   >> changed to defalut setting: %.2f\n", dVal);_msgout(cmsg);
        }
        sys.tcs_limit_secz = dVal;
      }

      // TCS_LIMIT_ALT: TCS configiguration for Alt limit
							  
      else if(strcasecmp(keyword, "TCS_LIMIT_ALT")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal <= 0.0 || dVal > 75.0 ) {
          CYATEXT;sprintf(cmsg, "  Warning: TCS_LIMIT_ALT %.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = DEFAULT_TCS_LIMIT_ALT;
          CYATEXT;sprintf(cmsg, "   >> changed to defalut setting: %.2f\n", dVal);_msgout(cmsg);
        }
        sys.tcs_limit_alt = dVal;
      }


      // TCS_LIMIT_WARNING: TCS configiguration for Warning range from limit
							  
      else if(strcasecmp(keyword, "TCS_LIMIT_WARNING")==0) {
        GetArg(inbuf, 2, argbuf);
        dVal = atof(argbuf);
        if( dVal < 0.0 || dVal > 70.0 ) {  // sometimes need to put a big number for test..
          CYATEXT;sprintf(cmsg, "  Warning: TCS_LIMIT_WARNING %.2f is out of range\n",dVal);_msgout(cmsg);
          dVal = DEFAULT_TCS_LIMIT_WARNING;
          CYATEXT;sprintf(cmsg, "   >> changed to defalut setting: %.2f\n", dVal);_msgout(cmsg);
        }
        sys.tcs_limit_warning = dVal;
      }

      // Verbose: Enable verbose output mode (e.g., for debugging)

      else if(strcasecmp(keyword, "VERBOSE")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          client.isVerbose = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          client.isVerbose = 0;
        else {
          CYATEXT;
          sprintf(cmsg, "  Warning: VERBOSE flag is '%s' unrecognized\n",argbuf);_msgout(cmsg);
          client.isVerbose = DEFAULT_VERBOSE;
          CYATEXT;
          sprintf(cmsg, "   >> changed to defalut setting: %s\n", client.isVerbose?"on":"off");_msgout(cmsg);
        }
      }

      // Debug: Enable runtime debugging out (superverbose mode)

      else if(strcasecmp(keyword, "DEBUG")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          client.Debug = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          client.Debug = 0;
        else {
          CYATEXT;
          sprintf(cmsg, "  Warning: DEBUG flag is '%s' unrecognized\n",argbuf);_msgout(cmsg);
          client.Debug = DEFAULT_DEBUG;
          CYATEXT;
          sprintf(cmsg, "   >> changed to defalut setting: %s\n", client.Debug?"on":"off");_msgout(cmsg);
        }
      }

      // DOLOG: Explicitly disable the runtime logging

      else if(strcasecmp(keyword, "DOLOG")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          client.doLogging = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          client.doLogging = 0;
        else {
          CYATEXT;  // v1.5.1
          sprintf(cmsg, "  Warning: DOLOG flag is '%s' unrecognized\n",argbuf);_msgout(cmsg);
          client.doLogging = DEFAULT_EVENTLOG;
          CYATEXT;
          sprintf(cmsg, "   >> changed to defalut setting: %s\n", client.doLogging?"on":"off");_msgout(cmsg);
        }
      }
      
      // LogFile: Runtime log file rootname (filename including path) 
      //
      // The .log extension will be appended to this rootname. 

      else if(strcasecmp(keyword, "LOGFILE")==0) { 
        GetArg(inbuf, 2, argbuf);
        strcpy(client.logFile, argbuf);
      }

      // ObsScript: Runtime observation script file path 

      else if(strcasecmp(keyword, "SCRIPT")==0) { 
        GetArg(inbuf, 2, argbuf);
        strcpy(agent.InitOsc, argbuf);
      }

      // VERLOG: Verbose logging mode for the runtime event log

      else if(strcasecmp(keyword, "LOGVER")==0) {  // v1.6.1
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          agent.isLogVerbose = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          agent.isLogVerbose = 0;
        else {
          CYATEXT;  // v1.5.1
          sprintf(cmsg, "  Warning: LOGVER flag is '%s' unrecognized\n",argbuf);_msgout(cmsg);
          agent.isLogVerbose = DEFAULT_LOGVERBOSE;
          CYATEXT;
          sprintf(cmsg, "   >> changed to defalut setting: %s\n", agent.isLogVerbose?"on":"off");_msgout(cmsg);
        }
      }

      // DBGLOG: debugging messages logging on the runtime debug log, making another log for debugging

      else if(strcasecmp(keyword, "DBGLOG")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          agent.isDebugLog = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          agent.isDebugLog = 0;
        else {
          CYATEXT;
          sprintf(cmsg, "  Warning: DBGLOG flag is '%s' unrecognized\n",argbuf);_msgout(cmsg);
          agent.isDebugLog = DEFAULT_DEBUGLOG;
          CYATEXT;
          sprintf(cmsg, "   >> changed to defalut setting: %s\n", agent.isDebugLog?"on":"off");_msgout(cmsg);
        }
      }

      // OBSLOG: script obs results logging on the runtime scrobs log, making another log for script obs log

      else if(strcasecmp(keyword, "OBSLOG")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          agent.isScrObsLog = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          agent.isScrObsLog = 0;
        else {
          CYATEXT;
          sprintf(cmsg, "  Warning: OBSLOG flag is '%s' unrecognized\n",argbuf);_msgout(cmsg);
          agent.isScrObsLog = DEFAULT_SCROBSLOG;
          CYATEXT;
          sprintf(cmsg, "   >> changed to defalut setting: %s\n", agent.isScrObsLog?"on":"off");_msgout(cmsg);
        }
      }

      // TIMETAG: Time tag display option    (v0.0.5)

      else if(strcasecmp(keyword, "TIMETAG")==0) {
        GetArg(inbuf,2,argbuf);
        if(strcasecmp(argbuf, "ON")==0) 
          agent.isTimeTag = 1;
        else if(strcasecmp(argbuf, "OFF")==0)
          agent.isTimeTag = 0;
        else {
          CYATEXT;
          sprintf(cmsg, "  Warning: TIMETAG flag is '%s' unrecognized\n",argbuf);_msgout(cmsg);
          agent.isTimeTag = DEFAULT_TIMETAG;
          CYATEXT;
          sprintf(cmsg, "   >> changed to defalut setting: %s\n", agent.isTimeTag?"on":"off");_msgout(cmsg);
        }
      }
      
      // gripe if scruff is in the config file

      else { 
        GetArg(inbuf,1,argbuf);
        CYATEXT;
        sprintf(cmsg, "  Warning: Ignoring unrecognized config file entry - '%s..'\n", argbuf);
        _msgout(cmsg);
      }

    } // if(!#)

    memset(inbuf,0,sizeof(inbuf)); 

  } // while()

  // additional value check..

  nVal = system(sys.rcmd_dlamp_get_stat);
  if( nVal!=0 ) {
    CYATEXT; 
    switch( WEXITSTATUS(nVal) ) {
      case   1: sprintf(cmsg, "  Warning: Invalid argument format for domeflat lamp control" ); break;
      case 127: sprintf(cmsg, "  Warning: Invalid command line for domeflat lamp control"    ); break;
      case  28: sprintf(cmsg, "  Warning: Failed to connect with the domeflat lamp relay"    ); break;
      case   7: sprintf(cmsg, "  Warning: Connection refused by the domeflat lamp relay"     ); break;
      case   6: sprintf(cmsg, "  Warning: Invalid IP address for the domeflat lamp relay"    ); break;
      default : sprintf(cmsg, "  Warning: Failed to get status of the domeflat lamp relay"   ); break;
    }
    strcat(cmsg, ",\n           ECMD string: \""); strcat(cmsg, sys.rcmd_dlamp_get_stat); strcat(cmsg, "\"");
    strcat(cmsg, "\n");
    _msgout(cmsg);
  } // v0.5.1/v0.6.8

  nVal = system(sys.rcmd_dlight_get_stat);
  if( nVal!=0 ) {
    CYATEXT; 
    switch( WEXITSTATUS(nVal) ) {
      case   1: sprintf(cmsg, "  Warning: Invalid argument format for dome LED light control" ); break;
      case 127: sprintf(cmsg, "  Warning: Invalid command line for dome LED light control"    ); break;
      case  28: sprintf(cmsg, "  Warning: Failed to connect with the dome LED light relay"    ); break;
      case   7: sprintf(cmsg, "  Warning: Connection refused by the dome LED light relay"     ); break;
      case   6: sprintf(cmsg, "  Warning: Invalid IP address for the dome LED light relay"    ); break;
      default : sprintf(cmsg, "  Warning: Failed to get status of the dome LED light relay"   ); break;
    }
    strcat(cmsg, ",\n           ECMD string: \""); strcat(cmsg, sys.rcmd_dlight_get_stat); strcat(cmsg, "\"");
    strcat(cmsg, "\n");
    _msgout(cmsg);
  } // v0.6.8

  nVal = system(sys.rcmd_mcfan_get_stat);
  if( nVal!=0 ) {
    CYATEXT; 
    switch( WEXITSTATUS(nVal) ) {
      case   1: sprintf(cmsg, "  Warning: Invalid argument format for mirror cell fan control" ); break;
      case 127: sprintf(cmsg, "  Warning: Invalid command line for mirror cell fan control"    ); break;
      case  28: sprintf(cmsg, "  Warning: Failed to connect with the mirror cell fan relay"    ); break;
      case   7: sprintf(cmsg, "  Warning: Connection refused by the mirror cell fan relay"     ); break;
      case   6: sprintf(cmsg, "  Warning: Invalid IP address for the mirror cell fan relay"    ); break;
      default : sprintf(cmsg, "  Warning: Failed to get status of the mirror cell fan relay"   ); break;
    }
    strcat(cmsg, ",\n           ECMD string: \""); strcat(cmsg, sys.rcmd_mcfan_get_stat); strcat(cmsg, "\"");
    strcat(cmsg, "\n");
    _msgout(cmsg);
  } // v0.5.1/v0.6.8

  nVal = system(sys.rcmd_tcspad_get_stat);
  if( nVal!=0 ) {
    CYATEXT; 
    switch( WEXITSTATUS(nVal) ) {
      case   1: sprintf(cmsg, "  Warning: Invalid argument format for PC-TCS paddle control" ); break;
      case 127: sprintf(cmsg, "  Warning: Invalid command line for PC-TCS paddle control"    ); break;
      case  28: sprintf(cmsg, "  Warning: Failed to connect with the PC-TCS paddle relay"    ); break;
      case   7: sprintf(cmsg, "  Warning: Connection refused by the PC-TCS paddle relay"     ); break;
      case   6: sprintf(cmsg, "  Warning: Invalid IP address for the PC-TCS paddle relay"    ); break;
      default : sprintf(cmsg, "  Warning: Failed to get status of the PC-TCS paddle relay"   ); break;
    }
    strcat(cmsg, ",\n           ECMD string: \""); strcat(cmsg, sys.rcmd_tcspad_get_stat); strcat(cmsg, "\"");
    strcat(cmsg, "\n");
    _msgout(cmsg);
  } // v0.6.8

  nVal = system(sys.rcmd_drotin_get_stat);
  if( nVal!=0 ) {
    CYATEXT; 
    switch( WEXITSTATUS(nVal) ) {
      case   1: sprintf(cmsg, "  Warning: Invalid argument format for Getting the dome rotation status" ); break;
      case 127: sprintf(cmsg, "  Warning: Invalid command line for Getting the dome rotation status"    ); break;
      case  28: sprintf(cmsg, "  Warning: Failed to connect with the dome controller relay"             ); break;
      case   7: sprintf(cmsg, "  Warning: Connection refused by the dome controller relay"              ); break;
      case   6: sprintf(cmsg, "  Warning: Invalid IP address for the dome controller relay"             ); break;
      default : sprintf(cmsg, "  Warning: Failed to get status of the dome controller relay"            ); break;
    }
    strcat(cmsg, ",\n           ECMD string: \""); strcat(cmsg, sys.rcmd_drotin_get_stat); strcat(cmsg, "\"");
    strcat(cmsg, "\n");
    _msgout(cmsg);
  } // v0.6.8

  if( sys.relay_tcspad_mode == RELAY_TCSPAD_MODE_UNDEF ) { // v0.6.8
    CYATEXT; 
    sprintf(cmsg, "  Warning: PC-TCS paddle mode undefined, it is over written with DRIFT mode\n" );_msgout(cmsg);
  }

  ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
  //
  //  nVal = system(agent.ecmd_dlamp_get_state);
  //  if( nVal!=0 ) {
  //    CYATEXT; 
  //    switch( WEXITSTATUS(nVal) ) {
  //      case   1: sprintf(cmsg, "  Warning: Invalid argument format for domeflat lamp control" ); break;
  //      case 127: sprintf(cmsg, "  Warning: Invalid command line for domeflat lamp control"    ); break;
  //      case  28: sprintf(cmsg, "  Warning: Failed to connect with the domeflat lamp relay"    ); break;
  //      case   7: sprintf(cmsg, "  Warning: Connection refused by the domeflat lamp relay"     ); break;
  //      case   6: sprintf(cmsg, "  Warning: Invalid IP address for the domeflat lamp relay"    ); break;
  //      default : sprintf(cmsg, "  Warning: Failed to get status of the domeflat lamp relay"   ); break;
  //    }
  //    strcat(cmsg, ",\n           ECMD string: \""); strcat(cmsg, agent.ecmd_dlamp_get_state); strcat(cmsg, "\"");
  //    strcat(cmsg, "\n");
  //    _msgout(cmsg);
  //  } // v0.5.1
  //
  //  nVal = system(agent.ecmd_mcfan_get_state);
  //  if( nVal!=0 ) {
  //    CYATEXT; 
  //    switch( WEXITSTATUS(nVal) ) {
  //      case   1: sprintf(cmsg, "  Warning: Invalid argument format for mirror cell fan control" ); break;
  //      case 127: sprintf(cmsg, "  Warning: Invalid command line for mirror cell fan control"    ); break;
  //      case  28: sprintf(cmsg, "  Warning: Failed to connect with the mirror cell fan relay"    ); break;
  //      case   7: sprintf(cmsg, "  Warning: Connection refused by the mirror cell fan relay"     ); break;
  //      case   6: sprintf(cmsg, "  Warning: Invalid IP address for the mirror cell fan relay"    ); break;
  //      default : sprintf(cmsg, "  Warning: Failed to get status of the mirror cell fan relay"   ); break;
  //    }
  //    strcat(cmsg, ",\n           ECMD string: \""); strcat(cmsg, agent.ecmd_mcfan_get_state); strcat(cmsg, "\"");
  //    strcat(cmsg, "\n");
  //    _msgout(cmsg);
  //  } // v0.5.1
  //////////////////////////////////////////////////////////////////////////////////////////////// old codes to remove


  //////////////// for debugging
  //
  //    printf("\n");    
  //    GRNTEXT; sprintf(cmsg, "  DBGMSG: \"%s\"\n", agent.ecmd_dlamp_get_status);_msgout(cmsg);
  //    nVal = system(agent.ecmd_dlamp_get_status);
  //    GRNTEXT; sprintf(cmsg, "  DBGMSG: Rtn = %d\n", nVal); _msgout(cmsg);
  //    GRNTEXT; sprintf(cmsg, "  DBGMSG: WIFEXITED(Rtn) = %d\n", WIFEXITED(nVal)); _msgout(cmsg);
  //    GRNTEXT; sprintf(cmsg, "  DBGMSG: WEXITSTATUS(Rtn) = %d\n", WEXITSTATUS(nVal)); _msgout(cmsg);
  //    printf("\n");
  //    GRNTEXT; sprintf(cmsg, "  DBGMSG: \"%s\"\n", agent.ecmd_dlamp_set_off);_msgout(cmsg);
  //    nVal = system(agent.ecmd_dlamp_set_off);
  //    GRNTEXT; sprintf(cmsg, "  DBGMSG: Rtn = %d\n", nVal); _msgout(cmsg);
  //    GRNTEXT; sprintf(cmsg, "  DBGMSG: WEXITSTATUS(Rtn) = %d\n", WEXITSTATUS(nVal)); _msgout(cmsg);
  //    printf("\n");
  //    usleep(2000000);
  //    GRNTEXT; sprintf(cmsg, "  DBGMSG: \"%s\"\n", agent.ecmd_dlamp_set_on);_msgout(cmsg);
  //    nVal = system(agent.ecmd_dlamp_set_on);
  //    GRNTEXT; sprintf(cmsg, "  DBGMSG: Rtn = %d\n", nVal); _msgout(cmsg);
  //    GRNTEXT; sprintf(cmsg, "  DBGMSG: WEXITSTATUS(Rtn) = %d\n", WEXITSTATUS(nVal)); _msgout(cmsg);
  //    printf("\n");
  //
  ////////////////////////////////


  // all done, close the config file and return 

  if(cfgFP!=0)
    fclose(cfgFP);

  // Display all configuration for Debug

  if(client.Debug) {
    printf("----------------------------------------------------------------\n"   );
    printf("DEBUG: Runtion configuration loaded..\n"                              );
    printf("  App.configs\n"                                                      );
    printf("    ICIMACS mode   : %s\n", client.useISIS?"ISISclient":"standalone"  );
    printf("    Verbose Msg    : %s\n", client.isVerbose?"on":"off"               );
    printf("    Debug Msg      : %s\n", client.Debug?"on":"off"                   );
    printf("    Event Log      : %s\n", client.doLogging?"on":"off"               );
    printf("    Debug Log      : %s\n", agent.isDebugLog?"on":"off"               );
    printf("    ScrObs Log     : %s\n", agent.isScrObsLog?"on":"off"              );
    printf("    Log Verbose    : %s\n", agent.isLogVerbose?"on":"off"             );
    printf("    Log path       : %s\n", client.logFile                            );
    printf("    Osc path       : %s\n", agent.InitOsc                             );
    printf("    Time Tag       : %s\n", agent.isTimeTag?"on":"off"                );
    printf("  ISIS\n"                                                             );
    printf("    ID             : %s\n", client.isisID                             );
    printf("    Host           : %s\n", client.isisHost                           );
    printf("    Port           : %d\n", client.isisPort                           );
    printf("  OBS Agent\n"                                                        );
    printf("    ID             : %s\n", client.ID                                 );
    printf("    Host           : %s\n", client.Host                               );
    printf("    Port           : %d\n", client.Port                               );
    printf("  Sys.configs\n"                                                      );
    printf("    IcsDatasource  : %s\n", sys.ics_datasource==ICS_ADC?"ADC":sys.ics_datasource==ICS_CTC?"CTC":"UNDEF");
    printf("    TcsLatitude    : %f\n", sys.tcs_latitude                          );
    printf("    TcsLongitude   : %f\n", sys.tcs_longitude                         );
    printf("    TcsElevation   : %f\n", sys.tcs_elevation                         );
    printf("    TcsTolPointing : %f\n", sys.tcs_tolerance_pointing                );
    printf("    TcsTolTracking : %f\n", sys.tcs_tolerance_tracking                );
    printf("    TcsHysUnstable : %d\n", sys.tcs_allowance_unstable                );
    printf("    TcsLimitHa     : %f\n", sys.tcs_limit_ha                          );
    printf("    TcsLimitDecN   : %f\n", sys.tcs_limit_dec_n                       );
    printf("    TcsLimitDecS   : %f\n", sys.tcs_limit_dec_s                       );
    printf("    TcsLimitSecZ   : %f\n", sys.tcs_limit_secz                        );
    printf("    TcsLimitAlt    : %f\n", sys.tcs_limit_alt                         );
    printf("    TcsLimitWarning: %f\n", sys.tcs_limit_warning                     );
    printf("----------------------------------------------------------------\n"   );
  }

  return(0);

}


//------------------------------------------------------------------------------
// Observation script initializing and loading functions

void
InitObsScript(COSC *posc)
{
  //int flag_temp;  
  //flag_temp = posc->flag_preparenextexp;  <-- removed at v1.2.0

  memset(posc, 0x00, sizeof(COSC));

  //flag_temp = posc->flag_preparenextexp;  <-- removed at v1.2.0

  posc->flag_preparenextexp = agent.flag_preparenextexp;  // v1.2.0
  posc->flag_wait_for_shutreload = agent.flag_wait_for_shutreload;  // v1.2.0

  //posc->count_process = 0;
  //posc->interval_process = OSC_INTERVAL_PROCESS;
  posc->count_process = sys.checknum_tcsdata-TCS_DATAUP_INTERVAL*2/3;    // zero point setting *2/4 --> *2/3 modified at v0.4.0
  posc->interval_process = TCS_DATAUP_INTERVAL;

  // the other initialization are in main()

}


int 
LoadObsScript(COSC *posc, const char *oscpath, char *reply)
{
  int i, n, rtn, maxlen, nVal, len;
  int nTypeLine, nTypeCmd, nTypeExp;
  int nLine, nCmd, nExp;
  int nHour, nDeg, nMin;
  double dRA, dDEC, dSec;
  char cCOpt, cSign, c1, c2, *cp;
  char strLine  [OSC_MAXLINELEN];
  char strProjID [OSC_MAX_ARGIN];
  char strLabel  [OSC_MAX_ARGIN];
  char strRA     [OSC_MAX_ARGIN];
  char strDEC    [OSC_MAX_ARGIN];
  char strCOpt   [OSC_MAX_ARGIN];
  char strImgTyp [OSC_MAX_ARGIN];
  char strObject [OSC_MAX_ARGIN];
  char strFilter [OSC_MAX_ARGIN];
  char strExpTime[OSC_MAX_ARGIN];
  char strUTObs  [OSC_MAX_ARGIN];
  char strUTTol  [OSC_MAX_ARGIN];
  char strVelRA  [OSC_MAX_ARGIN];  // v0.6.9
  char strVelDEC [OSC_MAX_ARGIN];
  FILE *fpOsc;

  if( strcasecmp(oscpath,"no")==0 || strcasecmp(oscpath,"none")==0 ) {
    sprintf(reply, "No script file to load data at the moment");
    return(1);
  }

  // Open the script file, if not, gripe and return -1.

  if(!(fpOsc=fopen(oscpath, "r"))) {
    sprintf(reply, "Cannot open the observation script file '%s'", oscpath);
    return(-1);
  }

  // Initialize the obsscript structure and local variables

  InitObsScript(posc);
  nTypeLine = 0;
  nTypeCmd = nTypeExp = 0;
  nLine = nCmd = nExp = 0;
  
  //posc->max_projid_length = 0;
  //posc->max_label_length = 0;
  //posc->max_object_length = 0;
  // --> not necessary because this is done in InitObsScript(posc), removed at v0.5.0

  // Get script file name

  for(i=strlen(oscpath);i>0;i--) if( oscpath[i-1] == '/' ) break;
  strcpy(posc->filename, oscpath+i);
  strcpy(posc->filepath, oscpath);

  // Get maximum projid/lable length

  while( fgets(strLine, OSC_MAXLINELEN, fpOsc) ) {

    for(n=0;n<OSC_MAXLINELEN;n++) {
      if( strLine[n]=='#' || strLine[n]=='\n' || strLine[n]==NUL || strLine[n]=='+' ) { n=OSC_MAXLINELEN; break; }
      //if( strLine[n]!=' ' ) break;
      if( strLine[n]!=' ' && strLine[n]!=0x0D ) break;   // modified fir CRLF line case at v0.6.4
    }

    //if( n != OSC_MAXLINELEN ) {
    //  if( ( cp = strchr(strLine+n, ' ' ) ) != NULL ) *cp = NUL;
    //  posc->max_label_length = MAX(posc->max_label_length,strlen(strLine+n));
    //}
    
    //rtn = sscanf(strLine+n, "%s %s", strProjID, strLabel);   // modified with inserting ProjID column at v0.6.4
    //if( rtn==2 ) {
    //rtn = sscanf(strLine+n, "%s %s %s %s %s %s %s %s %s %s %s", strProjID, strLabel, strRA, strDEC, strCOpt,
    //                         strImgTyp, strObject, strFilter, strExpTime, strUTObs, strUTTol);
    rtn = sscanf(strLine+n, "%s %s %s %s %s %s %s %s %s %s %s %s %s", strProjID, strLabel, strRA, strDEC, strCOpt,
                             strImgTyp, strObject, strFilter, strExpTime, strUTObs, strUTTol, strVelRA, strVelDEC);
    if( rtn>=11 ) {
      posc->max_projid_length = MAX(posc->max_projid_length,strlen(strProjID));
      posc->max_projid_length = MIN(posc->max_projid_length,OSC_MAX_PROJID);
      posc->max_label_length = MAX(posc->max_label_length,strlen(strLabel));
      posc->max_label_length = MIN(posc->max_label_length,OSC_MAX_LABEL);
    }    

  }

  rewind(fpOsc);

  //------------------------------------------------------
  //
  // Observation Script file parser loop
  //
  // Read in each line of the script and import it to the obsscript(posc) structure
  //
  
  sprintf(cmsg, "Script decoding and importing start..\n");_msgout(cmsg);

  agent.isBlockTimeTag = 1;   // TimeTag disabling added at v0.5.0

  for(i=0;fgets(strLine, OSC_MAXLINELEN, fpOsc);i++) {  // read n-1 characters, or up to '\n', or up to EOF

    // skip comments (#) and blank lines

    for(n=0;n<OSC_MAXLINELEN;n++) {
      if( strLine[n]=='#' || strLine[n]=='\n' || strLine[n]==NUL ) { n=OSC_MAXLINELEN; break; }
      if( strLine[n]=='+' ) { posc->line[nLine].type=OSC_TYPE_CMD; break; }
      //if( strLine[n]!=' ' ) { posc->line[nLine].type=OSC_TYPE_EXP; break; }
      if( strLine[n]!=' ' && strLine[n]!=0x0D ) { posc->line[nLine].type=OSC_TYPE_EXP; break; }   // modified for CRLF line case
    }

    if( n == OSC_MAXLINELEN ) continue;
    else nTypeLine++;

    posc->line[nLine].flag_movedisable = 0;

    //strLine[OSC_MAXLINELEN-1] = NUL;  // NUL is already stored at the end of buffer by fgets().

    //
    // a command line decoding/checking/importing
    //

    if( posc->line[nLine].type == OSC_TYPE_CMD ) {

      nTypeCmd++;

      //// set index

      posc->line[nLine].idx=(nCmd+1);

      //// command word and arguments import

      //strArgs[0] = NUL;
      //sscanf(strLine+n+1, "%s %[^\n]", posc->line[nLine].cmd, strArgs);
      //sscanf(strArgs, "%[^#]", posc->line[nLine].arg);
      //--> improved as follows
      sscanf(strLine+n+1, "%s %[^\n]", posc->line[nLine].cmd, posc->line[nLine].arg);
      if( ( cp = strchr(posc->line[nLine].arg, '#' ) ) != NULL ) *cp = NUL;

      for(n=0;n<NumCommands;n++) {
        if( strcasecmp(cmdtab[n].cmd, posc->line[nLine].cmd) == 0 ) break;
      }

      if( n == NumCommands ) {
          CYATEXT;sprintf(cmsg, "Warning: Command word '%s' is unrecognized in input line #%d.\n", posc->line[nLine].cmd, (i+1));_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         This command line is skipped in the script data import.\n");_msgout(cmsg);
          continue;
      }

      // all done, display confirmed and imported command line & increase command line count

      {//verbose
        sprintf(cmsg, "  LINE#%04d  CMD#%04d: +%s  %s\n", (nLine+1), (nCmd+1), posc->line[nLine].cmd, posc->line[nLine].arg);
        _vmsgout(cmsg);
      }

      nCmd++;

    }

    //
    // an exposure line decoding/checking/importing
    //

    if( posc->line[nLine].type == OSC_TYPE_EXP ) {

      nTypeExp++;

      ////strLine[strlen(strLine)-1] = NUL;
      ////sscanf(strLine, "%[^#]", strArgs);
      ////rtn = sscanf(strArgs, "%s %s %s %s %s %s %s %s %s %s", strLabel, strRA, strDEC, strCOpt, 
      ////                         strImgTyp, strObject, strFilter, strExpTime, strUTObs, strUTTol);
      ////--> improved as follows
      if     ( ( cp = strchr(strLine, '#' ) ) != NULL ) *cp = NUL;
      else if( ( cp = strchr(strLine, '\n') ) != NULL ) *cp = NUL;
      //rtn = sscanf(strLine, "%s %s %s %s %s %s %s %s %s %s", strLabel, strRA, strDEC, strCOpt, 
      //                         strImgTyp, strObject, strFilter, strExpTime, strUTObs, strUTTol);
      //rtn = sscanf(strLine, "%s %s %s %s %s %s %s %s %s %s %s", strProjID, strLabel, strRA, strDEC, strCOpt, // strProjID added at v0.6.4
      //                         strImgTyp, strObject, strFilter, strExpTime, strUTObs, strUTTol);
      rtn = sscanf(strLine, "%s %s %s %s %s %s %s %s %s %s %s %s %s", strProjID, strLabel, strRA, strDEC, strCOpt, 
                               strImgTyp, strObject, strFilter, strExpTime, strUTObs, strUTTol, strVelRA, strVelDEC);  // VelRA/DEC added at v0.6.9

      //// arguments number check
      
      //if(rtn<10) {
      //if(rtn<11) {   // +1 since ProjID included at v0.6.4
      if(rtn<9) {   // -2 since added an option to omit UTObs & UTTol ProjID columns at v0.9.2
        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has not enough arguments.\n", (i+1), strLabel);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
        continue;
      }
      //else if( rtn==13 && ( strVelRA[0]=='+' || strVelRA[0]=='-' ) && ( strVelDEC[0]=='+' || strVelDEC[0]=='-' ) ) {  // v0.6.9
      //  posc->line[nLine].velra  = atof(strVelRA );
      //  posc->line[nLine].veldec = atof(strVelDEC);
      //}
      else if( rtn==13 ) {  // v0.8.7
        posc->line[nLine].velra  = atof(strVelRA );
        posc->line[nLine].veldec = atof(strVelDEC);
      }
      else {
        posc->line[nLine].velra  = 0.0;
        posc->line[nLine].veldec = 0.0;
      }

      if(rtn==11) { // v0.9.2
        //// do nothing here since do somthing at "UT_OBS check and import" routine below
      }
      else if( rtn==10 ) {
        //// about UTOBS, do nothing here since do somthing at "UT_OBS check and import" routine below..
        strcpy(strUTTol, "-");        
      }
      else {  // rtn must be 9.
        strcpy(strUTObs, "-");
        strcpy(strUTTol, "-");
      }

      //// set index

      posc->line[nLine].idx=(nExp+1);

      //// projid string import, added at v0.6.4

      strncpy(posc->line[nLine].projid, strProjID, OSC_MAX_PROJID);

      if( strlen(strProjID) > OSC_MAX_PROJID ) {
        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has a too long ProjID '%s'.\n", (i+1), strLabel, strProjID);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Only the first %d characters are imported to the script data.\n", OSC_MAX_PROJID);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
      }   // v0.6.4

      //// label string import

      strncpy(posc->line[nLine].label, strLabel, OSC_MAX_LABEL);

      if( strlen(strLabel) > OSC_MAX_LABEL ) {
        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has a too long label '%s'.\n", (i+1), strLabel, strLabel);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Only the first %d characters are imported to the script data.\n", OSC_MAX_LABEL);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
      }

      //// check RA input string and values & convert to regular format

      if( strcmp(strRA, "-") == 0 ) {

        strcpy( posc->line[nLine].ra, strRA);
        posc->line[nLine].flag_movedisable = 1;
        goto SKIP_RA;

      }

      rtn = sscanf(strRA, "%d%c%d%c%lf", &nHour, &c1, &nMin, &c2, &dSec);

      if(rtn<5) {        
        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has unrecognized RA '%s'.\n", (i+1), strLabel, strRA);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
        continue;
      }

      if( c1!=':' || c2!=':' ) {
        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has an unexpected character '%c' in RA.\n", (i+1), strLabel, (c1!=':'?c1:c2));_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
        continue;
      }

      dRA = fabs((double)nHour) + (double)nMin/60.0 + dSec/3600.0;
      if( strRA[0]=='-' ) dRA *= -1.0;

      if( strRA[0]=='-' || nHour<0 || nHour>=24 || nMin<0 || nMin>=60 || dSec<0.0 || dSec>=60.0 || dRA<0.0 || dRA>24.0 ) {
        CYATEXT;sprintf(cmsg, "Warning: In the input line #%d(%s), RA '%s' is out of range.\n", (i+1), strLabel, strRA);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
        continue;
      }

      cSign = trans1060(dRA, &nHour, &nMin, &dSec, 3);
      sprintf(posc->line[nLine].ra, "%02d:%02d:%06.3f", nHour, nMin, dSec);

      posc->line[nLine].ra_h = dRA;

      SKIP_RA:

      //// check DEC input string and values & convert to regular format

      if( strcmp(strDEC, "-") == 0 ) {

        if( posc->line[nLine].flag_movedisable == 0 ) {
          CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has only RA coordinate.\n", (i+1), strLabel);_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
          continue;
        }

        strcpy( posc->line[nLine].dec, strDEC);
        posc->line[nLine].flag_movedisable = 1;
        goto SKIP_DEC;

      }

      if( posc->line[nLine].flag_movedisable == 1 ) {
          CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has only DEC coordinate.\n", (i+1), strLabel);_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
        continue;
      }

      rtn = sscanf(strDEC, "%d%c%d%c%lf", &nDeg, &c1, &nMin, &c2, &dSec);

      if(rtn<5) {
        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has unrecognized DEC '%s'.\n", (i+1), strLabel, strDEC);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
        continue;
      }

      if( c1!=':' || c2!=':' ) {
        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has an unexpected character '%c' in DEC string.\n", (i+1), strLabel, (c1!=':'?c1:c2));_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
        continue;
      }

      dDEC = fabs((double)nDeg) + (double)nMin/60.0 + dSec/3600.0;
      if( strDEC[0]=='-' ) dDEC *= -1.0;

      if( nDeg<-90 || nDeg>90 || nMin<0 || nMin>=60 || dSec<0.0 || dSec>=60.0 || dDEC<-90.0 || dDEC>90.0 ) {
        CYATEXT;sprintf(cmsg, "Warning: In the input line #%d(%s), DEC '%s' is out of range.\n", (i+1), strLabel, strDEC);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
        continue;
      }

      cSign = trans1060(dDEC, &nDeg, &nMin, &dSec, 2);
      sprintf(posc->line[nLine].dec, "%c%02d:%02d:%05.2f", cSign, nDeg, nMin, dSec);

      posc->line[nLine].dec_d = dDEC;

      SKIP_DEC: 

      //// correction option check and import

      cCOpt = strCOpt[0];
      switch(cCOpt) {
        case '-':             break;  // No correction
        case '0':             break;  // No correction
        case '1':             break;  // BLG correction
        case 'k': case 'K':   break;  // Offset to K from center
        case 'm': case 'M':   break;  // Offset to M from center
        case 't': case 'T':   break;  // Offset to T from center
        case 'n': case 'N':   break;  // Offset to N from center
        case 'c': case 'C':   break;  // center (No correctioin)
        default : cCOpt='?';  break;  // default setting
      }

      if(cCOpt=='?') {
        cCOpt = '0';        
        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has unrecognized correction option '%c'.\n", (i+1), strLabel, strCOpt[0]);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         This option is replaced with option '0'(no correction).\n");_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
      }

      strcpy(posc->line[nLine].copt, strCOpt);

      //// image type check and import

           if( strcasecmp(strImgTyp, "OBJECT"  ) == 0 ) strcpy(posc->line[nLine].imgtyp, "OBJECT"  );
      else if( strcasecmp(strImgTyp, "BIAS"    ) == 0 ) strcpy(posc->line[nLine].imgtyp, "BIAS"    );
      else if( strcasecmp(strImgTyp, "DARK"    ) == 0 ) strcpy(posc->line[nLine].imgtyp, "DARK"    );
      else if( strcasecmp(strImgTyp, "FLAT"    ) == 0 ) strcpy(posc->line[nLine].imgtyp, "FLAT"    );
      else if( strcasecmp(strImgTyp, "SKY"     ) == 0 ) strcpy(posc->line[nLine].imgtyp, "SKY"     );
      else if( strcasecmp(strImgTyp, "DOMEFLAT") == 0 ) strcpy(posc->line[nLine].imgtyp, "DOMEFLAT");
      else if( strcasecmp(strImgTyp, "STANDARD") == 0 ) strcpy(posc->line[nLine].imgtyp, "STANDARD");
      else {
        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has unrecognized IMAGETYPE '%s'.\n", (i+1), strLabel, strImgTyp);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
        continue;
      }
 
      //// object name import

      strncpy(posc->line[nLine].object, strObject, OSC_MAX_OBJECT);

      if( strlen(strObject) > OSC_MAX_OBJECT ) {
        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has too long object name '%s'.\n", (i+1), strLabel, strObject);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Only the first %d characters are imported to the script data.\n", OSC_MAX_OBJECT);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
      }
      
      posc->max_object_length = MAX(posc->max_object_length,strlen(strObject));   // to get maximum object length, added at v0.5.0
      posc->max_object_length = MIN(posc->max_object_length,OSC_MAX_OBJECT);

      //// filter name check and import

      n = strlen(strFilter); 

           if( strFilter[0]=='0' ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_N]); posc->line[nLine].filter_n = FNUM_N; }
      else if( strFilter[0]=='1' ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_1]); posc->line[nLine].filter_n = FNUM_1; }
      else if( strFilter[0]=='2' ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_2]); posc->line[nLine].filter_n = FNUM_2; }
      else if( strFilter[0]=='3' ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_3]); posc->line[nLine].filter_n = FNUM_3; }
      else if( strFilter[0]=='4' ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_4]); posc->line[nLine].filter_n = FNUM_4; }
      else if( strcasecmp(strFilter,sys.filterlabel[FNUM_N])==0 ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_N]); posc->line[nLine].filter_n = FNUM_N; }
      else if( strcasecmp(strFilter,sys.filterlabel[FNUM_1])==0 ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_1]); posc->line[nLine].filter_n = FNUM_1; }
      else if( strcasecmp(strFilter,sys.filterlabel[FNUM_2])==0 ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_2]); posc->line[nLine].filter_n = FNUM_2; }
      else if( strcasecmp(strFilter,sys.filterlabel[FNUM_3])==0 ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_3]); posc->line[nLine].filter_n = FNUM_3; }
      else if( strcasecmp(strFilter,sys.filterlabel[FNUM_4])==0 ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_4]); posc->line[nLine].filter_n = FNUM_4; }
      else if( n==1 && UC(strFilter[0])==UC(sys.filterlabel[FNUM_N][0]) ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_N]); posc->line[nLine].filter_n = FNUM_N; }
      else if( n==1 && UC(strFilter[0])==UC(sys.filterlabel[FNUM_1][0]) ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_1]); posc->line[nLine].filter_n = FNUM_1; }
      else if( n==1 && UC(strFilter[0])==UC(sys.filterlabel[FNUM_2][0]) ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_2]); posc->line[nLine].filter_n = FNUM_2; }
      else if( n==1 && UC(strFilter[0])==UC(sys.filterlabel[FNUM_3][0]) ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_3]); posc->line[nLine].filter_n = FNUM_3; }
      else if( n==1 && UC(strFilter[0])==UC(sys.filterlabel[FNUM_4][0]) ) { strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_4]); posc->line[nLine].filter_n = FNUM_4; }
      else {

        strcpy(posc->line[nLine].filter,sys.filterlabel[FNUM_U]);
        posc->line[nLine].filter_n = FNUM_U;

        CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has unrecognized filter name '%s'.\n", (i+1), strLabel, strFilter);_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
        CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);

        continue;

      }

      //// exposure time check and import

      if( strcasecmp(strImgTyp, "BIAS") == 0 ) posc->line[nLine].exptime = 0.0;
      else {
        posc->line[nLine].exptime = atof(strExpTime);
        if( posc->line[nLine].exptime < 0.05 || posc->line[nLine].exptime > 18000.0 ) {
          CYATEXT;sprintf(cmsg, "Warning: In the input line #%d(%s), ExpTime '%s' is out of range.\n", (i+1), strLabel, strExpTime);_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         This exposure line is skipped in the script data import.\n");_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
          continue;
        }
        else if( posc->line[nLine].exptime > 3600.0 ) {
          CYATEXT;sprintf(cmsg, "Warning: In the input line #%d(%s), ExpTime %.1f is too long in the system.\n", (i+1), strLabel, posc->line[nLine].exptime);_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         Anyway this exposure line will be imported into the script data.\n");_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         But please check this exposure time setting.\n");_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);
        }
      }

      //// UT_OBS check and import (v0.7.0/v0.7.9)

      time_t sec_obs;
      struct tm ut_obs;
      smctime_t ut_smc;

      //if( strUTObs[0]!='2' ) {
      //if( strUTObs[0]=='-' || strUTObs[0]=='0' ) {
      if( strUTObs[0]=='-' ) {

        strcpy(posc->line[nLine].utobs, "-");
        posc->line[nLine].secobs = 0;    // If secobs is 0, the exp line is observed regardless of the current time.

      }
      else {

        len = strlen(strUTObs);
        for( n=0 ; n<len ; n++ ) if( strUTObs[n]<0x30 || strUTObs[n]>0x39 ) strUTObs[n] = 0x20;   // to replace simbolic characters with a space      
        rtn = sscanf(strUTObs, "%d %d %d %d %d %d", &ut_obs.tm_year, &ut_obs.tm_mon, &ut_obs.tm_mday, &ut_obs.tm_hour, &ut_obs.tm_min, &ut_obs.tm_sec);

        if( rtn == 5 ) ut_obs.tm_sec = 0;

        if( rtn <  5 || 
            ut_obs.tm_year<0 || ut_obs.tm_year>9999 || 
            ut_obs.tm_mon <1 || ut_obs.tm_mon >  12 || 
            ut_obs.tm_mday<1 || ut_obs.tm_mday>  31 || 
            ut_obs.tm_hour<0 || ut_obs.tm_hour>  23 || 
            ut_obs.tm_min <0 || ut_obs.tm_min >  59 || 
            ut_obs.tm_sec <0 || ut_obs.tm_sec >  59 ) {

          strcpy(posc->line[nLine].utobs, "-");
          posc->line[nLine].secobs = 0;

          CYATEXT;sprintf(cmsg, "Warning: Input line #%d(%s) has unrecognized UT_OBS '%s'.\n", (i+1), strLabel, strUTObs);_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         UT_OBS option is disabled for this line.\n");_msgout(cmsg);
          CYATEXT;sprintf(cmsg, "         Exp. line input #%d: \"%s\"\n", nTypeExp, strLine);_vmsgout(cmsg);

        }
        else {

          sprintf(posc->line[nLine].utobs, "%04d-%02d-%02dT%02d:%02d:%02d", ut_obs.tm_year, ut_obs.tm_mon, ut_obs.tm_mday, ut_obs.tm_hour, ut_obs.tm_min, ut_obs.tm_sec);  // v0.7.3

          ut_obs.tm_mon-=1;
          ut_obs.tm_year-=1900;
          sec_obs = mktime(&ut_obs);
          posc->line[nLine].secobs = (UINT)sec_obs;
          SetSmctime(ut_obs, &ut_smc);
          //posc->line[nLine].secobs = ut_smc.secse;
          posc->line[nLine].jdobs = GetJd(ut_smc);

          BLUTEXT;sprintf(cmsg, "DBG:  utobs=%s        secobs=%u\n      utsmc=%04d-%02d-%02dT%02d:%02d:%02d\n         secse=%u\n      jdobs=%f\n", 
                                 posc->line[nLine].utobs, ut_smc.year, ut_smc.month, ut_smc.day, ut_smc.hour, ut_smc.min, (int)ut_smc.sec, 
                                 posc->line[nLine].secobs, ut_smc.secse, posc->line[nLine].jdobs);_dbgmsgout(cmsg);  // _msgout() replaced with _dbgmsgout() at v0.9.2
        }

      }

      //// UT_TOL check and import (v0.7.0/v0.7.9)

      nVal = atoi(strUTTol);   

    //if( nVal< 0 ) posc->line[nLine].uttol = 0;   // v0.8.3
    //if( nVal<=0 ) posc->line[nLine].uttol = 0;   // v0.8.4
    //else if( nVal>OSC_MAXIMUM_UTTOL ) posc->line[nLine].uttol = OSC_DEFAULT_UTTOL;  // v0.8.0
    //else posc->line[nLine].uttol = MAX(nVal,OSC_MINIMUM_UTTOL);  // minimum UTTOL applied at v0.8.2
    //--> for the sake of simplicity, modified at v0.9.0

      if( nVal<=0 ) posc->line[nLine].uttol = 0;
      else if( nVal<OSC_MINIMUM_UTTOL ) posc->line[nLine].uttol = OSC_MINIMUM_UTTOL;
    //else if( nVal>OSC_MAXIMUM_UTTOL ) posc->line[nLine].uttol = OSC_MAXIMUM_UTTOL;  // v0.9.0, no limit for large uttol anymore
      else posc->line[nLine].uttol = nVal;

      // NOTE: 
      // - Optimized UT_TOL = UT_OBS_INT/2
      // - If UT_TOL <= 0, the exp line is observed regardless of the current time.

      //// get other jobs

      // TBD..

      //// init indices

      posc->lineidx = 1;
      posc->cmdidx  = 1;
      posc->expidx  = 1;

      //// All done, Display confirmed and imported exposure data & Increase exposure line count

      {//verbose
      	
      	//maxlen = MIN(posc->max_projid_length,OSC_MAX_PROJID);
      	//if( strlen(strProjID) > OSC_MAX_PROJID ) strProjID[OSC_MAX_PROJID] = NUL;
      	//else strncat( strProjID, CONST_STR_SPACE, MAX(maxlen-strlen(strProjID),0) );   // added at v0.6.4
      	if( strlen(strProjID) > OSC_MAX_PROJID ) strProjID[OSC_MAX_PROJID] = NUL;
      	else strncat( strProjID, CONST_STR_SPACE, MAX(posc->max_projid_length-strlen(strProjID),0) );   // added at v0.6.4

        //posc->max_label_length = MIN(posc->max_label_length,OSC_MAX_DPLAB);
        maxlen = MIN(posc->max_label_length,OSC_MAX_DPLAB);   // modified at v0.5.0
        if( strlen(strLabel) > OSC_MAX_DPLAB ) {
          //strLabel[OSC_MAX_DPLAB-2] = '.';
          //strLabel[OSC_MAX_DPLAB-1] = '.';
          strLabel[OSC_MAX_DPLAB-1] = '~';
          strLabel[OSC_MAX_DPLAB-0] = NUL;
        }
        else {
         //strcat( strLabel, CONST_STR_SPACE);  strLabel[max+1] = NUL;
         // --> overflow possible according to length of CONST_STR_SPACE
         //strncat( strLabel, CONST_STR_SPACE, MAX(posc->max_label_length-strlen(strLabel),0) );
         strncat( strLabel, CONST_STR_SPACE, MAX(maxlen-strlen(strLabel),0) );   // modified at v0.5.0
        }

        if( strlen(strObject) > OSC_MAX_DPOBJ ) {
         //strObject[OSC_MAX_DPOBJ-2] = '.';
         //strObject[OSC_MAX_DPOBJ-1] = '.';
           strObject[OSC_MAX_DPOBJ-1] = '~';
           strObject[OSC_MAX_DPOBJ-0] = NUL;
        }

        //sprintf(cmsg, "LINE#%04d  EXP#%04d: %s %-12s %-12s %c  %-8s %-16s %-2s %6.1f  %-19s %4d   # %s\n", // OSC_MAX_DPOBJ = 16
        //sprintf(cmsg, "  LINE#%04d  EXP#%04d: %s %-12s %-12s %c  %-8s %-16s %-2s %6.1f  %7s %4d   # %s\n", // OSC_MAX_DPOBJ = 16, Ut-OBS filed shorten at v0.5.0
        sprintf(cmsg, "  LINE#%04d  EXP#%04d: %s  %s  %-12s %-12s %s  %-8s %-16s %-2s %6.1f  %7s %4d   # %s\n", // OSC_MAX_DPOBJ = 16, ProjID column added at v0.6.4
                          (nLine+1), (nExp+1), strProjID, strLabel, 
                          posc->line[nLine].ra, posc->line[nLine].dec, posc->line[nLine].copt, 
                          posc->line[nLine].imgtyp, strObject, 
                          posc->line[nLine].filter, posc->line[nLine].exptime, 
                          posc->line[nLine].utobs, posc->line[nLine].uttol, posc->line[nLine].flag_movedisable?"Move Disabled":"Move Enabled");
        _vmsgout(cmsg);

      }

      nExp++;

    }

    // No error, Increase confirmed and imported script line count

    nLine++;

  } //// End of for(i=1;fgets(strLine, OSC_MAXLINELEN, fpOsc);i++) 
  
  agent.isBlockTimeTag = 0;   // TimeTag disabling added at v0.5.0

  // check confirmed/available script data number

  if(nLine==0) {
    sprintf(reply, "No available data in the input script '%s'", posc->filename);
    return (-2);
  }

  //if(nExp==0) {
  //  sprintf(reply, "No available exposure data in the input script '%s'", posc->filename);
  //  return (-3);
  //}
  // removed at v0.6.2 for script with only command lines

  // Put loaded line/cmd/exp number into osc scructure

  posc->linenum = nLine;
  posc->cmdnum = nCmd;
  posc->expnum = nExp;

  // Put result & complete message into reply

  sprintf(reply, "%d of %d lines, %d of %d commands and %d of %d exposures"
                 " imported in the observation script data from '%s'"
                  , nLine, nTypeLine, nCmd, nTypeCmd, nExp, nTypeExp, posc->filename);

  if( nLine < nTypeLine ) {
    sprintf(reply, "%s  ---- Failed to import %d lines !!", reply, (nTypeLine-nLine) );
    return(-101);
  }  // added at v0.6.4
  
  return(0);

}


//------------------------------------------------------------------------------
//
// Utility functions for network communication
//
//------------------------------------------------------------------------------


// SetHostAddr: setting sockaddr_in structure from hostname, port number
//              based on InitISISServer(isisclient_t *client)

int
SetHostAddr(char *HostName, int Port, sockaddr_in *Addr)
{
  struct hostent *host;

  // translate the server hostname into an IP address 

  if(!(host=gethostbyname(HostName))) {
    return -1;
  }

  // Setup the server's socket address database 

  Addr->sin_port = htons(Port);
  Addr->sin_family = AF_INET;
  memcpy(&Addr->sin_addr, host->h_addr, host->h_length);

  return 0;
}

//------------------------------------------------------------------------------
//
// obstool - Simple interactive client for scripting observation.
//
// usage: obstool [rcfile]
// 
// where:
//   rcfile   = optional runtime config file to load.  By default it
//              uses the runtime config file defined in the obstool.h
//              header file, DEFAULT_RCFILE
//
// Description:
//
//
//
//
// Author:
//   S. Cha, KASI KMTNet team
//   chasm@kasi.re.kr
//   2014 Apr  1 (TCSAgent KMTNet version)
//   2016 Sep 20 (OBSAgent for KMTNet system)
//
// Author of framework for ICIMACS message handling:
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2004 Feb 29 (TCSAgent original version - agent pctcs for Yale1m v3.3.1)
//
// Modification History:
//   2016 Sep 20: OBSAgent v0.0 re-creation re-using TCSAgent flatform and code [sc/kasi]
//   2017 Aug 07: Replaced old code with new improved code of TCSAtgent v1.6.6 (v0.0.4)
//   2017 Aug 20: Removed codes and comments regarding TCS/AUX from TCSAgent (v0.0.6)
//   2017 Dec 21: ISIS connection checking code and monitoring/warning routine improved (v0.0.7)
//                Observation configuration data update/status monitoring/warning (v0.0.7)
//   2017 Dec 26: TC/PC-TCS/AUX connection monitoring and data update routine (v0.0.8)
//                Cam IC crash error handling routine - warning message to observer (v0.0.8)
//   2017 Dec 31: TC with AUX connection and AUX link in TC monitorint routine (v0.0.9)
//   2018 Jan 02: script running routine/function implementation (v0.1.9)
//   2018 Jan 10: Temp log files removal before exit main (v0.2.4)
//                several ERROR/WARNING message output modification (v0.2.4)
//   2018 Jan 11: improvement for handling the Acquisition completion error due to IC crash (v0.2.5)
//                (In case of the acquisition completion error due to IC crash, 
//                 now the script observation is paused and a ERROR message is displayed)
//                debugging for the routine monitoring the FITS Writing error (v0.2.5)
//   2018 Jan 12: debugging for event logging before the client.doLogging flag is ON (v0.2.6)
//                improvement of message in case of no initial observation script file (v0.2.6)
//   2018 Jan 25: debugging log changed (v0.2.8)
//   2018 Jan 31: optimization for SSO ICS version which is no 'Wrote' message (v0.2.9)
//                (removal of routine to set status_fitssaving = -1 and display warning message 
//                and replacement with routine forcing status_fitssaving = 1)
//   2018 Mar 20: "WARNING: FITS data is not fully completed.." display in case of no 4 Wrote msg if not at SSO
//   2020 Jul 27: warning blinking routine added, flag_warning=1 setting when critical error/warning (v0.3.5)
//   2020 Sep 17: debugging warning blinking (v0.3.6)
//   2020 Sep 18: SYS.STATUS logging although no script observation (v0.4.0)
//   2020 Sep 23: Log the information of client/process/configurations after process initialization (v0.4.2)
//   2020 Oct 08: camstatus = CAMSTATUS_READY forced 12 seconds later after CAMSTATUS_IDLE_3 (force_ready=270),
//                recovery using 5 sec timer for the black screen bug of warning blinking (v0.4.5)
//   2020 Nov 26: addition of override tcs connection error with flag_override_tcsconnection (v0.4.9)
//   2020 Dec 01: addition of override isis connection error with flag_override_isisconnection (v0.5.0)
//   2021 Mar 09: 1s timmer added in main loop, osc delay counter settings in 1s timmer (v0.5.2)
//   2022 Aug 12: osc.count_process reset position moved for no delay in case skip exp line due to UT_OBS passed (v0.8.1)
//   2024 Jun 28: Add declaration and initialization for exposure information structure, (CEXP)expinfo (v1.0.0)
//   2024 Jul 01: Add EXP.INFO string logging whether script observing or not (v1.0.2)
//   2024 Jul 02: Add func call to overwrite obs status file in 5sec-intervals routine(v1.0.3)
//   2024 Jul 12: Debugging for setting FitsNum at SSO (v1.0.7), Add setting strFitsOsc at SSO (v1.0.9)
//   2024 Jul 16: Add set expinfo.nStatus = EXPSTATUS_ERROR;  when writing FITS has not been completed, 
//                Add set expinfo.nStatus = EXPSTATUS_STANDBY when no script obs mode for SSO (v1.1.2)
//   2026 Jun 02: Move osc.flag_preparenextexp setting from main() to LoadConfig() to configured by .ini RC (v1.2.0)
//
//
// Reserved items:
//
//
//
//------------------------------------------------------------------------------

#include "obstool.h"       // PC-TCS agent header file

// The client cli uses the GNU readline and history utilities

// define this to turn on ultra-verbose debugging

#define __DEBUG
#undef  __DEBUG

// Client data structures

isisclient_t client;  // ISIS Client runtime parameters
obsagent_t agent;     // OBS Agent data (this process)
obssystem_t sys;      // System configuration data
COSC osc;             // Observation script data
CEXP expinfo;         // Exposure information data (v1.0.0)

char cmsg[STRLEN_CMSG];  // printing on console and logfile

// Test function declare
int testcode(void);

// The main event...

int
main(int argc, char *argv[]) 
{

  int i, rtn;
  int verbose_temp, auxstat_prev[6];
  int fopt_prev, sopt_prev;
  char reply[STRLEN_REP];
  char buf[STRLEN_ISISMSG];   // buffer for received message from ISIS/Remote host, 
                              // and somtimes used for short temporary string
  int  ibuf[32];
  char cbuf[32];

  // readline & history handling stuff

  char cliPrompt[ISIS_NODESIZE+2]; // the console prompt is our ISIS node name

  // maximum select() width (overkill, but works for now)

  int sel_wid;

  // select() event handler parameters

  fd_set read_fd;
  int kbdFD;
  int n_ready;
  int select_failnum, select_failnum_sig;
  struct timeval timeout, timeout_temp;

  // long interval timer configuration

    int timer_5s_counter = 0;
    int timer_5s_interval = 100;   // 1 loop = 55ms, 5/0.055=91, modified at v0.5.3

    int timer_1s_counter = 0;
    int timer_1s_interval = 20;   // 1 loop = 55ms, 1/0.055=18, modified at v0.5.3

  // warning blinking configuration

  agent.flag_warning = 0;  //v0.3.5
  agent.count_warning = 0;
  agent.interval_warning = WARNING_BLINK_INTERVAL;

  // Basic initializations

  select_failnum = 0;
  select_failnum_sig = SELECT_ERR_IGNORE_NUM;
  timeout.tv_sec  = 0;
  timeout.tv_usec = SELECT_TIMEOUT*1000;  // SELECT_TIMEOUT = msec

  sel_wid = getdtablesize();
  kbdFD = fileno(stdin);  // file descriptor of stdin, safe definition

  agent.isBlockTimeTag = 1;  // makes the Time Tag display flag be uneffective
  agent.ISIScheckint = XIS_CONCHK_INTERVAL;  // move this initializing routine into LoadConfig() later
  agent.flag_override_isisconnection = 0;
  agent.pLogEvent  = NULL;  // v0.2.6
  agent.pLogDebug  = NULL;
  agent.pLogScrObs = NULL;

  InitSysConfig(&sys);
  InitObsScript(&osc);
  InitExpInfo(&expinfo);   // v1.0.0

  // osc.flag_preparenextexp = 1;  // Enable to prepare the next exposure
  // --> this setting moved into loadconfig to configured by .ini RC (v1.2.0)

  // Parse the command line 

  if(argc>2) {
    printf("usage: %s [rcfile]\n", argv[0]);
    printf("where: rcfile = optional runtime config file (default %s)\n",
           DEFAULT_RCFILE);
    exit(0);
  }

  // Application version input

  rtn = strlen(APP_VERSION);
  if(rtn) strcpy(agent.AppVersion, APP_VERSION);
  else    strcpy(agent.AppVersion, APP_VER);

  // Some useful startup info (who, what, when...)

  strcpy(agent.UserID,getenv("USER"));  // Who started this thing, anyway?
  strcpy(agent.exeFile,argv[0]);        // command executed
  strcpy(agent.StartTime,ISODate());    // when the agent was started

  // Open temporary log files (TC.v1.6.0)

  agent.pLogEvent  = fopen(TEMP_EVENTLOGFILE , "w");
  agent.pLogDebug  = fopen(TEMP_DEBUGLOGFILE , "w");
  agent.pLogScrObs = fopen(TEMP_SCROBSLOGFILE, "w");
  _eventlog ("LOG_START\n");
  _debuglog ("LOG_START\n");
  _scrobslog("LOG_START\n");
  agent.isDebugLog = 1;  // tempoaray enable DebugLog before LoadConfig()

  // So far so good, give the welcome information

  sprintf(cmsg, "\n"                                                      );_msgout(cmsg);
  sprintf(cmsg, "  ----------------------------------------------------\n");_msgout(cmsg);
  sprintf(cmsg, "                   KMTNet OBS Agent\n"                   );_msgout(cmsg);
  sprintf(cmsg, "\n"                                                      );_msgout(cmsg);
  sprintf(cmsg, "    Version: %s (%s %s)\n",
                                agent.AppVersion,APP_COMPDATE,APP_COMPTIME);_msgout(cmsg);
  sprintf(cmsg, "  ----------------------------------------------------\n");_msgout(cmsg);
  sprintf(cmsg, "\n"                                                      );_msgout(cmsg);

  // Load the specified runtime config file, or use the default if none given

  sprintf(cmsg, "- Runtime configuration loading..\n");_msgout(cmsg);  // TC.v1.5.1

  if(argc==2)
    rtn = LoadConfig(argv[1]);
  else
    rtn = LoadConfig(DEFAULT_RCFILE);

  if(rtn!=0) {
    REDTEXT;sprintf(cmsg, "  > RC loading failed !\n");_msgout(cmsg);
    REDTEXT;sprintf(cmsg, "  >> OBS Agent aborting\n");_msgout(cmsg);
    if(agent.pLogEvent !=NULL) fclose(agent.pLogEvent );
    if(agent.pLogDebug !=NULL) fclose(agent.pLogDebug );
    if(agent.pLogScrObs!=NULL) fclose(agent.pLogScrObs);
    sprintf(buf, "rm %s", TEMP_EVENTLOGFILE ); system(buf);  // v0.2.4
    sprintf(buf, "rm %s", TEMP_DEBUGLOGFILE ); system(buf);
    sprintf(buf, "rm %s", TEMP_SCROBSLOGFILE); system(buf);
    exit(1);
  }
  else {
    sprintf(cmsg, "  > RC loading complete\n");_msgout(cmsg);
  }

  //
  // Check for logging option & Configure event/debugging/scrobs logs (TC.v1.6.1)
  //

  sprintf(cmsg, "- Log option check & Logging configuring..\n");_msgout(cmsg);

  sscanf(agent.StartTime, "%d%*c%d%*c%d%*c%d%*c%d%*c%d", ibuf+0, ibuf+1, ibuf+2, ibuf+3, ibuf+4, ibuf+5);
  sprintf(cbuf, "%04d%02d%02d.%02d%02d%02d", ibuf[0], ibuf[1], ibuf[2], ibuf[3], ibuf[4], ibuf[5]);

  // Check for event message logging option & Configure the event log

  if(client.doLogging) {
    if(agent.pLogEvent==NULL) {
      REDTEXT;
      printf("  > Event Log file open failed !\n");
      TXTRESET;
    }
    else {
      fclose(agent.pLogEvent);
      sprintf(buf, "mv %s %s.event.%s.log", TEMP_EVENTLOGFILE, client.logFile, cbuf);
      system(buf);
      sprintf(buf, "%s.event.%s.log", client.logFile, cbuf);
      agent.pLogEvent = fopen(buf, "a");
      if(agent.pLogEvent==NULL) {
        REDTEXT;
        printf("  > Event Logging start failed !\n");
        TXTRESET;
      }
      else {
        sprintf(cmsg, "  > Event Logging started successfully\n");_msgout(cmsg);
      }
    }
  }
  else {
    if(agent.pLogEvent!=NULL) {
      fclose(agent.pLogEvent);
      agent.pLogEvent = NULL;
      sprintf(buf, "rm %s", TEMP_EVENTLOGFILE);
      system(buf);
    }
  }

  // Check for debugging message logging option & Configure the debug log

  if(agent.isDebugLog) {
    if(agent.pLogDebug==NULL) {
      REDTEXT;
      printf("  > Debug Log file open failed !\n");
      TXTRESET;
    }
    else {
      fclose(agent.pLogDebug);
      sprintf(buf, "mv %s %s.debug.%s.log", TEMP_DEBUGLOGFILE, client.logFile, cbuf);
      system(buf);
      sprintf(buf, "%s.debug.%s.log", client.logFile, cbuf);
      agent.pLogDebug = fopen(buf, "a");
      if(agent.pLogDebug==NULL) {
        REDTEXT;
        printf("  > Debug Logging start failed !\n");
        TXTRESET;
      }
      else {
        sprintf(cmsg, "  > Debug Logging started successfully\n");_msgout(cmsg);
      }
    }
  }
  else {
    if(agent.pLogDebug!=NULL) {
      fclose(agent.pLogDebug);
      agent.pLogDebug = NULL;
      sprintf(buf, "rm %s", TEMP_DEBUGLOGFILE);
      system(buf);
    }
  }

  // Check for script observation results logging option & Configure the ScrObs log

  if(agent.isScrObsLog) {
    if(agent.pLogScrObs==NULL) {
      REDTEXT;
      printf("  > ScrObs Log file open failed !\n");
      TXTRESET;
    }
    else {
      fclose(agent.pLogScrObs);
      sprintf(buf, "mv %s %s.scrobs.%s.log", TEMP_SCROBSLOGFILE, client.logFile, cbuf);
      system(buf);
      sprintf(buf, "%s.scrobs.%s.log", client.logFile, cbuf);
      agent.pLogScrObs = fopen(buf, "a");
      if(agent.pLogScrObs==NULL) {
        REDTEXT;
        printf("  > ScrObs Logging start failed !\n");
        TXTRESET;
      }
      else {
        sprintf(cmsg, "  > ScrObs Logging started successfully\n");_msgout(cmsg);
      }
    }
  }
  else {
    if(agent.pLogScrObs!=NULL) {
      fclose(agent.pLogScrObs);
      agent.pLogScrObs = NULL;
      sprintf(buf, "rm %s", TEMP_SCROBSLOGFILE);
      system(buf);
    }
  }

  //
  // Loading the observation script from DEFAULT_INITOSC or SCRIPT of RC
  //

  sprintf(cmsg, "- Observation Script loading..\n");_msgout(cmsg);

  rtn = LoadObsScript(&osc, agent.InitOsc, reply);

  if(rtn<0) {
    REDTEXT;sprintf(cmsg, "  > Observation script loading failed !\n");_msgout(cmsg);
    REDTEXT;sprintf(cmsg, "  >> %s\n", reply);_msgout(cmsg);
    REDTEXT;sprintf(cmsg, "  >> Try to import script data using the 'oscript' command.\n");_msgout(cmsg);
  }
  else if(rtn==1) {  // v0.2.6
    sprintf(cmsg, "  > %s\n", reply);_msgout(cmsg);
    sprintf(cmsg, "  >> Import script data using the 'oscript' command.\n");_msgout(cmsg);
    sprintf(cmsg, "     if the script file is ready.\n");_msgout(cmsg);
  }
  else {
    sprintf(cmsg, "  > %s\n", reply);_msgout(cmsg);
  }

//WriteObsStatus();   // v1.0.4
  WriteObsStatus(DEFAULT_OBSSTAT);   // v1.0.5

  // If required, initialize the socket connection to the ISIS server.
  // We can disable ISIS interaction by specifying "Mode Standalone" or
  // "ServerID None" in the runtime config file

  if(client.useISIS) {
    if(InitISISServer(&client)<0) {
      REDTEXT;sprintf(cmsg, "- ISIS server connection initialization failed !\n");_msgout(cmsg);
      REDTEXT;sprintf(cmsg, "  >> OBS Agent aborting\n");_msgout(cmsg);
      if(agent.pLogEvent !=NULL) fclose(agent.pLogEvent );
      if(agent.pLogDebug !=NULL) fclose(agent.pLogDebug );
      if(agent.pLogScrObs!=NULL) fclose(agent.pLogScrObs);
      exit(2);
    }
    //else {printf("ISIS connection success\n");}
    else {  // v0.0.7
      printf("- ISIS configuration initialization..\n");
      printf("  > ISIS server hostname resolved\n");
    }
  }

  // Open the client network socket port for ISIS communications.  We
  // open this anyway since it costs us nothing, and a subsequent "open
  // isis" command will need it.  Also provides the the comm port used
  // for socket comm in Standalone mode.
  
  if(OpenClientSocket(&client)<0) {
    REDTEXT;sprintf(cmsg, "- Client socket initialization failed !\n");_msgout(cmsg);
    REDTEXT;sprintf(cmsg, "  >> OBS Agent aborting\n");_msgout(cmsg);
    if(agent.pLogEvent !=NULL) fclose(agent.pLogEvent );
    if(agent.pLogDebug !=NULL) fclose(agent.pLogDebug );
    if(agent.pLogScrObs!=NULL) fclose(agent.pLogScrObs);
    exit(3);
  }

  if(client.useISIS)
  {
    sprintf(cmsg, "- Started OBS Agent as ISIS client node %s\n", client.ID);_msgout(cmsg);
    sprintf(cmsg, "  on %s port %d\n", client.Host, client.Port);_msgout(cmsg);
  }
  else
  {
    sprintf(cmsg, "- Started OBS Agent as standalone ISIS node %s\n", client.ID);_msgout(cmsg);
    sprintf(cmsg, "  on %s port %d\n", client.Host, client.Port);_msgout(cmsg);
  }

  sprintf(cmsg, "\n");_msgout(cmsg);

  // All set to rock-n-roll...

  sprintf(cmsg, "- OBS Agent start..\n\n");_msgout(cmsg);

  sprintf(cmsg, "-------------------------------------------------------\n");_msgout(cmsg);
  sprintf(cmsg, " Type 'quit' to terminate OBS Agent process\n");_msgout(cmsg);
  sprintf(cmsg, " Type 'help' to see a list of commands\n");_msgout(cmsg);
  sprintf(cmsg, "-------------------------------------------------------\n\n");_msgout(cmsg);

  agent.isBlockTimeTag = 0;  // Setting to use the Time Tag display flag

  // Startup the command-line history mechanism

  using_history();

  // Setup the command prompt and install the readline() callback
  // handler for this application (KeyboardCommand() in commands.c)

  sprintf(cliPrompt,"%s%% ",client.ID);
  rl_callback_handler_install(cliPrompt,KeyboardCommand);

  // If configured as an ISIS client, broadcast a PING to the ISIS
  // server.  If it fails, we'll have to do the ping by hand after the
  // comm loop starts.

  if(client.useISIS) {
    //if( SendISISMsg("ping", REQ, "XIS", reply) < 0 ) {  --> error since ISIS not connected yet..
    memset(buf,0,ISIS_MSGSIZE);
    //sprintf(buf,"%s>AL ping\r",client.ID);
    sprintf(buf,"%s>XIS ping\r",client.ID);  //v0.0.7
    rtn = SendToISISServer(&client,buf);
    sprintf(cmsg, "ISIS OUT: %s\n",buf);_dbgmsgout(cmsg);
    if(rtn<0) {
      REDTEXT;
      sprintf(cmsg, "ERROR: Failed to ping the ISIS server - %s\n", strerror(errno)); _msgout(cmsg);
    }
  }

  // If configured as an ISIS client, send a command to request TCS data to TC
  // (TCS connection check == initial TCS data update check)

  if(client.useISIS) {
    rtn = QueryTcsData(&sys, reply);
    if(rtn<0) {
      REDTEXT;
      sprintf(cmsg, "ERROR: %s\n", reply);_msgout(cmsg);
    }    
  }

  // If configured as an ISIS client, send a command to request filter names to TC
  // (AUX connection check == filter names update check)

  if(client.useISIS) {
    rtn = QueryFilterLabels(&sys, reply);
    if(rtn<0) {
      REDTEXT;
      sprintf(cmsg, "ERROR: %s\n", reply);_msgout(cmsg);
    }    
  }
  
  // Log the information of client/process/configurations
  
  GetAgentInfo(reply);
  sprintf(cmsg, "AGENT INFO: %s\n", reply);_vmsgout(cmsg);   // v0.4.2
  
  // Test function

  if(testcode()) exit(0);

  
  /////////////////////////////////////////////////////////////////////////////////////////////
  //// temporary settings for debugging the aux connection and data update monitoring routine
  //// maybe we can use this settings in the aux error override routine later..
  //sys.flag_auxconnected = 1;
  //sys.flag_auxdata_requested = 0;
  //sys.flag_auxdata_updated = 1;
  //sys.checknum_auxdisconnected = 0;
  //sys.flag_filterlabel_requested = 0;
  /////////////////////////////////////////////

  // If a SIGINT trap is used, set it here...

  rl_refresh_line(0,0);

  //////////////////////////////////////////////////////////////////////////////////////////////////////
  // Start the I/O event handling loop

  client.KeepGoing = 1;

  while (client.KeepGoing) { //

    //
    // Monitoring ISIS connection (initializing process)
    //

    if( client.useISIS && agent.isISISconnected==0 && !agent.flag_override_isisconnection ) {

      agent.ISISchecknum++;

      if( agent.ISISchecknum > agent.ISIScheckint ) {

        REDTEXT;sprintf(cmsg, "WARNING: ISIS server is disconnected.\n");_msgout(cmsg);
        REDTEXT;sprintf(cmsg, "         Please check ICS status.\n");_vmsgout(cmsg);

        memset(buf,0,ISIS_MSGSIZE);
        sprintf(buf,"%s>XIS ping\r",client.ID);
        rtn = SendToISISServer(&client,buf);
        sprintf(cmsg, "ISIS OUT: %s\n",buf);_dbgmsgout(cmsg);
        if(rtn<0) {
          REDTEXT;
          sprintf(cmsg, "ERROR: Failed to ping the ISIS server - %s\n", strerror(errno)); _msgout(cmsg);
        }
        else {
          sprintf(cmsg, ">> PING sended to XIS to register in ICIMACS\n");_vmsgout(cmsg);
        }

        agent.ISISchecknum = 0;

      }

    }

    //
    // Monitoring TC/PC-TCS/AUX connection and the observation configuration update (initializing process)
    //

    // TCS connection and initial TCS data update check 

    if( client.useISIS && !sys.flag_tcsconnected && !sys.flag_override_tcsconnection ) {

      if( ++sys.checknum_tcsconnection > sys.interval_tcsconnection ) {

        sys.checknum_tcsconnection = 0;

        REDTEXT;sprintf(cmsg, "WARNING: TCS Agent or PC-TCS is disconnected.\n");_msgout(cmsg);
        REDTEXT;sprintf(cmsg, "         Please restart and initialize TCS Agent with PC-TCS.\n");_vmsgout(cmsg);

        rtn = QueryTcsData(&sys, reply);
        if(rtn<0) {
          REDTEXT;sprintf(cmsg, "ERROR: %s\n", reply);_msgout(cmsg);
        }
        else {
          sprintf(cmsg, ">> %s\n", reply);_vmsgout(cmsg);
        }

      }

    }

    // AUX connection and initial filter names update check

    if( client.useISIS && !sys.flag_auxconnected && !sys.flag_override_auxconnection ) {

      if( ++sys.checknum_auxconnection > sys.interval_auxconnection ) {

        sys.checknum_auxconnection = 0;

        REDTEXT;sprintf(cmsg, "WARNING: TCS Agent or AUX Ctrl. is disconnected.\n");_msgout(cmsg);
        REDTEXT;sprintf(cmsg, "         Filter information is not updated.\n");_vmsgout(cmsg);
        REDTEXT;sprintf(cmsg, "         Please restart and initialize TCS Agent with AUX Ctrl.\n");_vmsgout(cmsg);

        rtn = QueryFilterLabels(&sys, reply);
        if(rtn<0) {
          REDTEXT;sprintf(cmsg, "ERROR: %s\n", reply);_msgout(cmsg);
        }
        else {
          sprintf(cmsg, ">> %s\n", reply);_vmsgout(cmsg);
        }

      }

    }

    //
    // Monitoring TCS/AUX data update and connections
    //

    // TCS data update request and check

    if( client.useISIS && sys.flag_tcsconnected ) {

      if( ++sys.checknum_tcsdata > sys.interval_tcsdata ) {

          sys.checknum_tcsdata = 0;

          if( sys.flag_tcsdata_requested==1 && sys.flag_tcsdata_updated==0 ) {
            sys.checknum_tcsdisconnected++;
            if( sys.allowance_tcsdisconnected < sys.checknum_tcsdisconnected ) {          
              sys.flag_tcsconnected = 0;
              sys.telstatus = TELSTATUS_NC;
              ResetTcsData(&sys);  // also call in display()
            }
          }

          else {
            rtn = QueryTcsData(&sys, reply);
            if(rtn<0) {
              REDTEXT;sprintf(cmsg, "ERROR: %s\n", reply);_msgout(cmsg);
            }
          }

      }

    }

    // AUX data update request and check

    if( client.useISIS && sys.flag_auxconnected ) {

      if( ++sys.checknum_auxdata > sys.interval_auxdata ) {

          sys.checknum_auxdata = 0;

          if( sys.flag_auxdata_requested==1 && sys.flag_auxdata_updated==0 ) {
            sys.checknum_auxdisconnected++;
            if( sys.allowance_auxdisconnected < sys.checknum_auxdisconnected ) {          
              sys.flag_auxconnected = 0;
              //sys.telstatus = TELSTATUS_NC;  --> in case of AUX system failed, keep going the observation
              ResetAuxData(&sys);  // also call in display()
            }
          }

          else {
            rtn = QueryAuxData(&sys, reply);
            if(rtn<0) {
              REDTEXT;sprintf(cmsg, "ERROR: %s\n", reply);_msgout(cmsg);
            }
          }

      }

    }

    //
    // Camera status checking and detecting any miss/error
    //

    if( sys.camstatus == CAMSTATUS_IDLE_1 ) {
      sys.count_idle++;
      if( sys.force_idle < sys.count_idle ) {
        sys.camstatus = CAMSTATUS_IDLE_3;
        sys.count_fitssaving = 0;
        //MAGTEXT;sprintf(cmsg, "WARNING: Acquisition is not fully completed. Check ICs status and FITS writing progress.\n");_msgout(cmsg);
        OscCommand("opause");   // v0.2.5
        REDTEXT;sprintf(cmsg, "ERROR: Acquisition is not fully completed !! The process is paused now. Please check ICs status and FITS writing progress.\n");_msgout(cmsg);  // v0.2.5
        agent.flag_warning = 1;
      }
    }

    if( sys.camstatus == CAMSTATUS_IDLE_2 ) {
      sys.count_idle++;
      if( sys.force_idle < sys.count_idle ) {
        sys.camstatus = CAMSTATUS_IDLE_3;
        sys.count_fitssaving = 0;
        MAGTEXT;sprintf(cmsg, "WARNING: No 'EXPSTATUS=IDLE' message from ICS, Check ICs status.\n");_msgout(cmsg);
      }
    }

    if( sys.camstatus == CAMSTATUS_IDLE_3 ) {   // v0.4.5
      if( sys.force_ready < sys.count_ready++ ) sys.camstatus = CAMSTATUS_READY;
    }

  //if( sys.status_fitssaved==0 &&   sys.camstatus==CAMSTATUS_IDLE_3  ) {
  //if( sys.status_fitssaved==0 && ( sys.camstatus==CAMSTATUS_IDLE_3 || ( sys.camstatus>=CAMSTATUS_PREP_I && sys.camstatus<=CAMSTATUS_CLOSING ) ) ) {
    if( sys.status_fitssaved==0 && ( sys.camstatus>=CAMSTATUS_IDLE_3 || ( sys.camstatus>=CAMSTATUS_PREP_I && sys.camstatus<=CAMSTATUS_CLOSING ) ) ) {   // v0.4.5

      sys.count_fitssaving++;

      //// if( sys.allowance_fitssaving < sys.count_fitssaving ) {
      ////   sys.status_fitssaved = -1;
      ////   MAGTEXT;sprintf(cmsg, "WARNING: Writing FITS data is not fully completed !! Please check ICs status and FITS files existing.\n");_msgout(cmsg);
      //// }
      //// --> removed this routine to set status and display warning message since no 'Wrote' message anymore due to IC upgrade at v0.2.9 at SSO 
      ////     and replace with following code for forcing fits saved (not monitoring and assume FITS saved 18s later after EXPSTATUS=IDLE)

      ////if( sys.force_fitssaved < sys.count_fitssaving ) {  // v0.2.9
      ////  sys.status_fitssaved = 1;
      ////}

      if( sys.force_fitssaved < sys.count_fitssaving ) {  // v0.3.2
        sys.status_fitssaved = 1;
        if( strcasecmp(client.isisHost,"192.168.15.109") ) {  // if ISISHOST IP is not SSO thing, this phrase should be removed after SSO IC version is upgraded
          //OscCommand("opause");
          //REDTEXT;sprintf(cmsg, "ERROR: Writing FITS data is not fully completed !! The process is paused now. Please check ICs status and FITS files existing.\n");_msgout(cmsg);
          MAGTEXT;sprintf(cmsg, "WARNING: Writing FITS data is not fully completed !! Please check ICs status and FITS files existing.\n");_msgout(cmsg);
          agent.flag_warning = 1;
          expinfo.nStatus = EXPSTATUS_ERROR;  // v1.1.2, set ERROR when writing FITS has not been completed, determined since no 4th "wrote" message
        }
        else {
          osc.lastidx_fitssaved = osc.lastidx_expcompleted;
          if(expinfo.nStatus>=EXPSTATUS_FINISH) expinfo.nStatus = EXPSTATUS_STANDBY;  // v1.1.2, set STANDBY when no script obs. mode
        //strcpy(expinfo.strFitsNum, expinfo.strCurNum);
          strcpy(expinfo.strFitsNum, expinfo.strPreNum);   // debugging at v1.0.7
          strcpy(expinfo.strFitsOsc, expinfo.flagOscPre?"YES":"NO");   // added at v1.0.9
        }  // added in v1.0.6 for SSO
      }

    }

    //
    // Observation script process
    //

    if( osc.flag_process ) {

      if( ++osc.count_process > osc.interval_process ) {

        osc.count_process = 0;  // moved here at v0.8.1

        //sprintf(cmsg, "SYS.STATUS: %s\n", GetSysStatus());_dbgmsgout(cmsg);   // v0.2.8
        //sprintf(cmsg, "EXP.INFO: %s\n", GetExpInfo());_dbgmsgout(cmsg);   // v1.0.2 
        sprintf(cmsg, "SYS.STATUS: %s\n", GetSysStatus());_debuglog(cmsg);   // v1.0.3
        sprintf(cmsg, "EXP.INFO: %s\n", GetExpInfo());_debuglog(cmsg);   // v1.0.3
        //// Note: In order to record the state immediately before the call to ProcOsc(), better to place these in this routine.

        rtn = ProcOsc(&osc, &sys, &agent, reply);

        switch( rtn ) {
          case OSC_RTN_NOERR  : break;
          case OSC_RTN_NOTICE : sprintf(cmsg, "STATUS: %s\n" , reply);_msgout(cmsg);
                                break;
          case OSC_RTN_WARNING: CYATEXT;
                                sprintf(cmsg, "Warning: %s\n", reply);_msgout(cmsg);
                                agent.flag_warning = 1;
                                break;
          case OSC_RTN_ERROR  : REDTEXT;
                                sprintf(cmsg, "ERROR: %s\n"  , reply);_msgout(cmsg);
                                agent.flag_warning = 1;
                                break;
        }

        //sprintf(buf, "OSC.STATUS: %s\n", GetOscStatus());_dbgmsgout(buf);
        sprintf(buf, "OSC.STATUS: %s\n", GetOscStatus());_debuglog(buf);   // v1.0.4

        //osc.count_process = 0;  // moved above for no delay skip when UT-OBS passed, v0.8.1

      }

    }
    
    else {   // added for SYS.STATUS log when no script observation as well at v0.4.0

    //if( ++osc.count_process > osc.interval_process*2 ) {  // interval x 2
      if( ++osc.count_process > osc.interval_process   ) {
        
        osc.count_process = 0;

        //sprintf(cmsg, "SYS.STATUS: %s\n", GetSysStatus());_dbgmsgout(cmsg);   // v0.2.8
        //sprintf(cmsg, "EXP.INFO: %s\n", GetExpInfo());_dbgmsgout(cmsg);   // v1.0.2
        sprintf(cmsg, "SYS.STATUS: %s\n", GetSysStatus());_debuglog(cmsg);   // v1.0.3
        sprintf(cmsg, "EXP.INFO: %s\n", GetExpInfo());_debuglog(cmsg);   // v1.0.3

      }
    }

    //
    // The other processes
    //

    if( agent.flag_warning ) {  // v0.3.5

      if( ++agent.count_warning < 2*WARNING_BLINK_SHORTINT*WARNING_BLINK_NUMBER+1 ) {  // e.g. 2 x 2 x 5 cycle = 20
        //     if( agent.count_warning % (WARNING_BLINK_SHORTINT*2) == 0 ) {WHITEBG;BEEP;printf("\n\n  DBGMSG: blinking off\n\n");}
        //else if( agent.count_warning % (WARNING_BLINK_SHORTINT*1) == 0 ) {BLACKBG;BEEP;printf("\n\n  DBGMSG: blinking on \n\n");}  // active
               if( agent.count_warning % (WARNING_BLINK_SHORTINT*2) == 0 ) {WHITEBG;BEEP;}
          else if( agent.count_warning % (WARNING_BLINK_SHORTINT*1) == 0 ) {BLACKBG;BEEP;}
      } //// debugged at v0.3.6

      if( agent.count_warning > agent.interval_warning ) agent.count_warning = 0;   // 1 loop ~ 50 ms

    }
    
    if( ++timer_5s_counter > timer_5s_interval ) {   // v0.4.5
      
      timer_5s_counter = 0;

    //rtn = WriteObsStatus();   // v1.0.3
      rtn = WriteObsStatus(DEFAULT_OBSSTAT);   // v1.0.5
      if( rtn<0 ) { strcpy(cmsg, "Warning: Failed to write the observation status file\n");CYATEXT;_msgout(cmsg); }
      
      //if( agent.flag_warning==0 ) WHITEBG;  --> removed at v0.5.1 since WHITEBG is put unconditionally in KeyboardCommand()
      
    }
    
    if( ++timer_1s_counter > timer_1s_interval ) {   // v0.5.2
      
      timer_1s_counter = 0;
      
      if( osc.flag_delay ) {   // v0.5.2        
          if( osc.count_delay < 1 ) {
            sprintf(cmsg, "STATUS: OSC delay remains - %3d sec\n", 0);BLUTEXT;_msgout(cmsg);
            //printf("\r                                                                              ");
            strcpy(cmsg, "STATUS: OSC delay complete.\n"); _msgout(cmsg);
            OscCommand("oresume");   // osc.flag_delay is set to 0 in cmd_oscresume()
          }
          else {
            //printf("\r");
            //sprintf(cmsg, "STATUS: OSC delay remains - %d sec  ", osc.count_delay--);BLUTEXT;_msgout(cmsg); fflush(stdout);
            sprintf(cmsg, "STATUS: OSC delay remains - %3d sec\n", osc.count_delay--);BLUTEXT;_msgout(cmsg);
          }
      }
      
    }

    //
    // Reset file descriptor list for calling select()
    //

    FD_ZERO(&read_fd); // clear the table of active file descriptors

    // we always listen for console keyboard input

    FD_SET(kbdFD, &read_fd);

    // if enabled, listen to this app's ISIS client socket

    if(client.FD > 0) FD_SET(client.FD, &read_fd);

    //
    // Do the select() call and wait for activity on any of our communication
    // link or the console keyboard
    //

    memcpy(&timeout_temp, &timeout, sizeof(timeout));
    n_ready = select(sel_wid, &read_fd, NULL, NULL, &timeout_temp);
      // set timeout of select() to process update routine without anyinput in KMTNet TCS
    
    if(n_ready == 0) {
      #ifdef __DEBUG
      //printf("\rDEBUG: select() return 0, would be a timeout\n");  // removed at TC.v1.2.2
      #endif
      // would be a timeout if enabled, do nothing...
      continue;
    }
    else if(n_ready < 0) {
      select_failnum++;
      {//verbose
        if(select_failnum>select_failnum_sig) {    // TC.v1.2.2
          CYATEXT;sprintf(cmsg, "Warning: select() failed - %s\n", strerror(errno));_vmsgout(cmsg);
        }
      }
      continue;
    }
    else { // somebody wants something, figure out who...

      // Console keyboard input

      if(FD_ISSET(kbdFD, &read_fd)) {
        rl_callback_read_char(); // readline() handler
      }

      // ISIS client socket input (from either the ISIS or a remete client)

      if(FD_ISSET(client.FD, &read_fd)) {
        memset(buf,0,ISIS_MSGSIZE);
        if(ReadClientSocket(&client,buf)>0)
          SocketCommand(buf);
        rl_refresh_line(0,0);
      }

      // add any new FD handlers here...

      // ..
      
      // select() noerr reset

      select_failnum = 0;

    } // end of select() I/O handling checking - if(n_ready==0) {..} else {

  } // bottom of the while(client.KeepGoing) loop

  //------------------------------------------------------------
  //
  // If we got here, the client was instructed to shut down
  //

  sprintf(cmsg, "                                \n");_msgout(cmsg);
  sprintf(cmsg, "OBS Agent client shutting down...\n\n");_msgout(cmsg);  // TC.v1.6.0

  // Tear down the client socket connection

  if(client.FD > 0) close(client.FD);

  // Remove the readline() callback handler

  rl_callback_handler_remove();

  // Close message/event log (v1.6.0)

  _eventlog ("LOG_END\n\n");
  _debuglog ("LOG_END\n\n");
  _scrobslog("LOG_END\n\n");
  if(agent.pLogEvent !=NULL) fclose(agent.pLogEvent );
  if(agent.pLogDebug !=NULL) fclose(agent.pLogDebug );
  if(agent.pLogScrObs!=NULL) fclose(agent.pLogScrObs);

  // all done, say goodbye...

  printf("\rBye.             \n\n");

  WHITEBG; BEEP;

  exit(0);

}




//------------------------------------------------------------------------------
// Test codes
//

int testcode(void)
{
  
  return 0;  // keep going main()
  
  printf("\n\n  TEST START..\n\n");
  
  for(int i;1;i++) {    
    
    sys.tcs_tolerance_pointing_corr = sys.tcs_tolerance_pointing + OSC_ADJ_TOL_POINTING * (double)(osc.count_pointing/2);   // v0.4.7
    printf("    %d:  %.2f  =  %.2f  +  %.2f  *  %.2f\n", osc.count_pointing, sys.tcs_tolerance_pointing_corr,  sys.tcs_tolerance_pointing, OSC_ADJ_TOL_POINTING, (double)(osc.count_pointing/2));
    if( osc.count_pointing++ > OSC_CHKCNT_POINTING ) break;
      
  }
  
  printf("\n\n  TEST FINISHED.\n\n\n");

//return 0;  // keep going main()
  return 1;  // exit main()

}



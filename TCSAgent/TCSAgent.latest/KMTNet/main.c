//
// pctcs - Simple interactive client to interface with a ComSoft PC-TCS
//         and AUX control software, modified for KMTNet TCS.
//
// usage: pctcs [rcfile]
// 
// where:
//   rcfile   = optional runtime config file to load.  By default it
//              uses the runtime config file defined in the pctcs.h
//              header file, DEFAULT_RCFILE
//
// Description:
//   This agent provides a basic IMPv2-compliant interface to the 
//   telescope control system (TCS).  The IMPv2-compliant interface is 
//   a remote-command interface for both the End-User (GUI) software 
//   and the camera software such as ISIS.  TCS Agent also provides a 
//   command-line interface for the local user.
//
//   KMTNet TCS has both TCP/IP network interfaces for remote 
//   interaction with the ComSoft PC-TCS and the AUX control software.  
//   The PC-TCS controls the telescope mount.  The AUX control software 
//   controls several subsystems of the telescope such as 
//   filter/shutter, focuser, dome shutter, and mirror cooling system.
//
//   The network interface for PC-TCS is implemented with a program 
//   named Telcom.  Telcom includes a TCP/IP server to process the 
//   remote commands according to the 'PCTCS-NG Network Protocol'.  The 
//   network interface for AUX control is also implemented with a 
//   TCP/IP server in the AUX control software.  AUX server is made 
//   based on the definitions in 'AUX control remote commands 
//   definition'.
//
//   Three main functions of TCS Agent are to manage the telemetry 
//   data, to process high-level commands for telescope operations, and 
//   to monitor/diagnose the telescope status, subsystems statues, and 
//   the TCS/AUX links.
//
//   TCS Agent records and translates the PC-TCS and AUX telemetry data 
//   into an IMPv2-compliant status message, as well as providing some 
//   low-level diagnostics.  The Update routine for PC-TCS telemetry 
//   data is tried at an interval of tcs.UpdateInt, set in Runtime 
//   configuration (default 1 sec).  TCS Agent only sends a telemetry 
//   request command to Telcom for trying the telemetry update because 
//   Telcom's response is not prompt.  Telcom sends a telemetry data 
//   packet 0~1 second later since a telemetry request.  The Telcom's 
//   message is monitored in another routine with select().  If the 
//   PC-TCS telemetry data packet is received successfully, the data is 
//   converted and saved into the tcs structure.  The AUX telemetry 
//   data is updated at an interval of aux.UpdateInt, set in Runtime 
//   configuration (default 200 msec).  The AUX telemetry data update 
//   is completeed at once in same routine because AUX server responds 
//   promptly for a data request command.  When the user or ISIS 
//   queries the telemetry data with a command of tcs/aux status, TCS 
//   Agent return the data with an IMPv2-compliant status message.
//
//   TCS Agent provides high-level commands for telescope operation 
//   such as guiding offset, goto RA/Dec, change filters and adjust 
//   focus/tip-tilt.  The high-level commands are processed using low-
//   level data and remote commands of PC-TCS and AUX, defined in each 
//   protocol.  All commands and cmd-process functions are defined in 
//   commands.h and commands.c.
//
//   TCS Agent monitors and diagnoses statuses of TCS link, AUX link, 
//   the telescope and subsystems.  If judged to be an error or 
//   abnormal status, TCS Agent prints an error message or a warning 
//   message on the console for the local user, and also provides all 
//   statuses and diagnostic data to the remote user with the IMPv2-
//   compliant status message. 'ERROR' message is printed if a critical 
//   error was occurred or an unavailable command is received.  
//   'Warning' message is printed, if unhealthy situation or an error 
//   was occurred but it is not critical.  In TCS link monitoring, both 
//   the TCP/IP connection with Telcom and the serial stream of PC-TCS 
//   were monitored.  TCS link is set to IDLE in case that the PC-TCS 
//   serial stream is invalid.  TCS link is set to DOWN in case the 
//   TCP/IP connection with Telcom is disconnected or unavailable.  In 
//   AUX link monitoring, AUX link is set to DOWN if an error is 
//   occurred in command send/receive process or the TCP/IP connection 
//   with AUX server is disconnected or unavailable.  If Auto Recovery 
//   mode (ArcMode) is enabled, TCS Agent tries to connect to 
//   Telcom/AUX server, and to recover the TCS/AUX links in intervals 
//   of ArcInt.
//
//   The basic program uses select() to monitor the telemetry data 
//   packet from Telcom and AUX server, to watch the command-line 
//   interface for keyboard commands (stdin via the GNU 
//   readline/history mechanism), and to watch for IMPv2 communications 
//   on its UDP socket interface.  In the original version, there was 
//   no timeout for select() because the PC-TCS transmits a continuous 
//   stream of TCS telemetry at a cadence of about 1 message string 
//   every 200msec via a serial interface so select() didn't block the 
//   main loop.  In the KMTNet version, the timeout for select() is set 
//   to 50 msec (default defined in pctcs.h) to run other routines for 
//   checking the update time and sending the telemetry request 
//   commands at the update interval.
//
//   Runtime configuration is accomplished using an external config 
//   file (e.g., pctcs.ini) to specify ports and relevant runtime 
//   parameters.  Basic commands allow some dynamic re-configuration, 
//   but generally the config file is given primacy for critical 
//   parameters (e.g., port). In the KMTNet version, the runtime 
//   configuration was extended for optimization to KMTNet TCS.  New 
//   keywords were added to the config file to specify Telcom/AUX 
//   server information, communication control settings, and HW 
//   configurations.
//
//   The agent is configured either as an ISIS client, or as a 
//   standalone program operating independently of an ISIS system. 
//   Either in the Standalone mode or the ISIS client mode, TCS Agent 
//   interacts any client that according to IMPv2 through a UDP socket.
//   In the ISIS client mode, TCS Agent acts a client of ISIS server 
//   that has the ISIS ID and the ISIS port defined in Runtime 
//   configuration, and also an ISIS client terminal is enabled so the 
//   local user can interacts other nodes through ISIS server on the 
//   console. (e.g., TC% >ICS ping)
//
// Author:
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2004 February 29 (original version - Yale1m v3.3.1)
//
//   S. Cha, KASI KMTNet team
//   chasm@kasi.re.kr
//   2014 April 1 (KMTNet version)
//
// Modification History:
//   2004 Feb 29 - based on fwagent [rwp/osu]
//   2014 May 03 - modified for KMTNet TCS [sc/kasi]
//   2014 Aug 08 - ARC loop modified
//   2014 Aug 24 - TCP Link control modified
//                 Epoch setting at TCS init/recovery
//                 overall improvement & debugging (v1.2)
//   2015 Jan 12 - Messages output modification (v1.4.0)
//   2015 Jul 20 - Initially importing RA/Dec object catalog from catfile (v1.5.1)
//   2015 Oct 15 - cmsg string buffer added and _(v)msgout() applied 
//                 for colsole message output and logging function (v1.6.0)
//                 readline callback addec to reset consol prompt after _(v)msgout() 
//   2015 Oct 17 - TSTAT/ASTAT logging routine added (v1.6.1)
//   2017 Jun 08 - changed error handling for new Rtn of parse_comsoft() (v1.6.3)
//   2017 Jun 19 - code for debugging trans1060() in testcode() (v1.6.4)
//                 removed old debugging/testing code (v1.6.5)
//   2017 Jun 20 - modified for telemetry data decoding routine with recalling parse_comsoft()
//                 in case of the telemetry data/string error, and the history logging (v1.6.5)
//   2017 Jul 26 - Long string array buffers' length/declaration reviewed and modified (v1.6.6)
//
//
//
//------------------------------------------------------------------------------

#include "pctcs.h"       // PC-TCS agent header file

// The client cli uses the GNU readline and history utilities

// define this to turn on ultra-verbose debugging

#define __DEBUG
#undef  __DEBUG

// Client data structures

isisclient_t client;  // ISIS Client runtime parameters
tcsagent_t agent;     // TCS Agent data (this process)
pctcs_t tcs;          // PC-TCS data
auxctrl_t aux;

char cmsg[STRLEN_CMSG];  // printing on console and logfile

// Test function declare
int testcode(void);

// The main event...

int
main(int argc, char *argv[]) 
{
  int i, arctry, rtn;
  int verbose_temp, auxstat_prev[6];
  int fopt_prev, sopt_prev;
  double arcloopint;

  char reply[STRLEN_REP];     // buffer for reply from TCS/AUX init/telemetry func
  char recvbuf[STRLEN_REP];   // buffer for received message from TCS/AUX host,
                              // including the pc-tcs telemetry string
  char buf[STRLEN_ISISMSG];   // buffer for received message from ISIS/Remote host, 
                              // and somtimes used for short temporary string
  int  ibuf[32];
  char cbuf[32];

  // readline & history handling stuff

  int flag_keyinput;
  char cliPrompt[STRLEN_ISISNODE+2]; // the console prompt is our ISIS node name

  // maximum select() width (overkill, but works for now)

  int sel_wid;

  // select() event handler parameters

  fd_set read_fd;
  int kbdFD;
  int n_ready;
  int select_failnum, select_failnum_sig;
  struct timeval timeout, timeout_temp;

  // Test function
  if(testcode()) exit(0);

  // Basic initializations

  tcs.FDtel = -1;
  tcs.FDcmd = -1;
  aux.FD = -1;
  memset(recvbuf,0,STRLEN_REP*sizeof(char));

  select_failnum = 0;
  select_failnum_sig = SELECT_ERR_IGNORE_NUM;
  timeout.tv_sec  = 0;
  timeout.tv_usec = SELECT_TIMEOUT*1000;  // SELECT_TIMEOUT = msec

  sel_wid = getdtablesize();
  kbdFD = fileno(stdin);  // file descriptor of stdin, safe definition

  for(i=0;i<6;i++) 
    auxstat_prev[i] = AUX_STATUS_STANDBY;

  fopt_prev = AUX_FS_FOP_STANDBY;
  sopt_prev = AUX_FS_SOP_STANDBY;

  strcpy(aux.FS_FilNames[AUX_FS_FNUM_NO  ], AUX_FS_FNAME_NO     );
  strcpy(aux.FS_FilNames[AUX_FS_FNUM_F1  ], AUX_FS_FNAME_UNKNOWN);
  strcpy(aux.FS_FilNames[AUX_FS_FNUM_F2  ], AUX_FS_FNAME_UNKNOWN);
  strcpy(aux.FS_FilNames[AUX_FS_FNUM_F3  ], AUX_FS_FNAME_UNKNOWN);
  strcpy(aux.FS_FilNames[AUX_FS_FNUM_F4  ], AUX_FS_FNAME_UNKNOWN);
  strcpy(aux.FS_FilNames[AUX_FS_FNUM_MANY], AUX_FS_FNAME_MANY   );

  arctry = 0;

  flag_keyinput = 0;

  // Parse the command line 

  if (argc>2) {
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

  // Open temporary log file (v1.6.0)

  agent.LogMsg = fopen(TEMP_LOGFILE, "w");
  _msglog("LOG_START\n\n");

  // So far so good, give the welcome information

  sprintf(cmsg, "\n"                                                      );_msgout(cmsg);
  sprintf(cmsg, "  ----------------------------------------------------\n");_msgout(cmsg);
  sprintf(cmsg, "                   KMTNet TCS Agent\n"                   );_msgout(cmsg);
  sprintf(cmsg, "    Interactive PC-TCS & AUX Remote Interface Client\n"  );_msgout(cmsg);
  sprintf(cmsg, "\n"                                                      );_msgout(cmsg);
  sprintf(cmsg, "    Version: %s (%s %s)\n",agent.AppVersion,APP_COMPDATE,APP_COMPTIME);_msgout(cmsg);
  sprintf(cmsg, "  ----------------------------------------------------\n");_msgout(cmsg);
  sprintf(cmsg, "\n"                                                      );_msgout(cmsg);

  // Load the specified runtime config file, or use the default if none given

  sprintf(cmsg, "- Runtime configuration loading..\n");_msgout(cmsg);  // v1.5.1

  if (argc==2)
    rtn = LoadConfig(argv[1]);
  else
    rtn = LoadConfig(DEFAULT_RCFILE);

  if (rtn!=0) {
    REDTEXT;sprintf(cmsg, "  > RC loading failed !\n");_msgout(cmsg);
    REDTEXT;sprintf(cmsg, "  >> TCS Agent aborting\n");_msgout(cmsg);
    if(agent.LogMsg!=NULL) fclose(agent.LogMsg);  // v1.6.0
    if(agent.LogTcs!=NULL) fclose(agent.LogTcs);  // v1.6.1
    if(agent.LogAux!=NULL) fclose(agent.LogAux);  // v1.6.1
    exit(1);
  }
  else {
    sprintf(cmsg, "  > RC loading complete\n");_msgout(cmsg);
  }

  //
  // Check for logging option & Configure event/tstat/astat logs (v1.6.1)
  //

  sprintf(cmsg, "- Log option check & Logging configuring..\n");_msgout(cmsg);

  sscanf(agent.StartTime, "%d%*c%d%*c%d%*c%d%*c%d%*c%d", ibuf+0, ibuf+1, ibuf+2, ibuf+3, ibuf+4, ibuf+5);
  sprintf(cbuf, "%04d%02d%02d.%02d%02d%02d", ibuf[0], ibuf[1], ibuf[2], ibuf[3], ibuf[4], ibuf[5]);

  // Check for logging option & Configure event log (v1.6.0)

  if(client.doLogging) {

    if(agent.LogMsg==NULL) {
      REDTEXT;
      printf("  > Event Log file open failed !\n");
      TXTRESET;
    }

    else {

      fclose(agent.LogMsg);

      sprintf(buf, "mv %s %s.event.%s.log", TEMP_LOGFILE, client.logFile, cbuf);
                       
      system(buf);

      sprintf(buf, "%s.event.%s.log", client.logFile, cbuf);
      agent.LogMsg = fopen(buf, "a");

      if(agent.LogMsg==NULL) {
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

    if(agent.LogMsg!=NULL) {
      fclose(agent.LogMsg);
      agent.LogMsg = NULL;
      sprintf(buf, "rm %s", TEMP_LOGFILE);
      system(buf);
    }

  }

  // Configure TCS status and AUX status logging (v1.6.1)

  sprintf(buf, "%s.tstat.%s.log", client.logFile, cbuf);
  agent.LogTcs = fopen(buf, "w");
  if(agent.LogTcs==NULL) {
    REDTEXT;
    sprintf(cmsg, "  > TSTAT Logging start failed !\n");_msgout(cmsg);
  }
  else {
    sprintf(cmsg, "  > TSTAT Logging started successfully\n");_msgout(cmsg);
    _tcslog("LOG_START\n\n");
  }

  sprintf(buf, "%s.astat.%s.log", client.logFile, cbuf);
  agent.LogAux = fopen(buf, "w");
  if(agent.LogAux==NULL) {
    REDTEXT;
    sprintf(cmsg, "  > ASTAT Logging start failed !\n");_msgout(cmsg);
  }
  else {
    sprintf(cmsg, "  > ASTAT Logging started successfully\n");_msgout(cmsg);
    _auxlog("LOG_START\n\n");
  }

  agent.LogTcsTick = 0.0;  // set 0 for no delay at the first try, 
  agent.LogAuxTick = 0.0;  // status logging routine shuld be after status update routine

  //
  // Import the RA/Dec object catalog data from DEFAULT_CATFILE file
  //

  sprintf(cmsg, "- RA/Dec Object Catalog importing..\n");_msgout(cmsg);

  rtn = LoadCatalog(agent.CatFile, reply);

  if (rtn<0) {
    switch(rtn) {
      // In case of no catfile (Cannot open RA/Dec object catalog file "filename")
      case -1: REDTEXT;sprintf(cmsg, "  Error: %s\n", reply);_msgout(cmsg);
               REDTEXT;sprintf(cmsg, "         %s\n",strerror(errno));_msgout(cmsg);
               REDTEXT;sprintf(cmsg, "         default catfile rootname is \"%s\"\n", DEFAULT_CATFILE);
               _msgout(cmsg);
               break;
      // In case of no data in catfile (No available data in catalog file "filename")
      case -2: REDTEXT;sprintf(cmsg, "  Error: %s\n", reply);_msgout(cmsg);
               REDTEXT;sprintf(cmsg, "  > cat data importing failed !\n");_msgout(cmsg);
               REDTEXT;sprintf(cmsg, "  >> Try to import the catalog data using 'catalog' command\n");
               _msgout(cmsg);
               break;
    }
  }
  else {
    sprintf(cmsg, "  > %s\n", reply);_msgout(cmsg);
  }

  // If required, initialize the socket connection to the ISIS server.
  // We can disable ISIS interaction by specifying "Mode Standalone" or
  // "ServerID None" in the runtime config file

  if (client.useISIS) {
    if (InitISISServer(&client)<0) {
      REDTEXT;sprintf(cmsg, "- ISIS server connection initialization failed !\n");_msgout(cmsg);
      REDTEXT;sprintf(cmsg, "  >> TCS Agent aborting\n");_msgout(cmsg);
      if(agent.LogMsg!=NULL) fclose(agent.LogMsg);  // v1.6.0
      if(agent.LogTcs!=NULL) fclose(agent.LogTcs);  // v1.6.1
      if(agent.LogAux!=NULL) fclose(agent.LogAux);  // v1.6.1
      exit(2);
    }
  }

  // Open the client network socket port for ISIS communications.  We
  // open this anyway since it costs us nothing, and a subsequent "open
  // isis" command will need it.  Also provides the the comm port used
  // for socket comm in Standalone mode.
  
  if (OpenClientSocket(&client)<0) {
    REDTEXT;sprintf(cmsg, "- Client socket initialization failed !\n");_msgout(cmsg);
    REDTEXT;sprintf(cmsg, "  >> TCS Agent aborting\n");_msgout(cmsg);
    if(agent.LogMsg!=NULL) fclose(agent.LogMsg);  // v1.6.0
    if(agent.LogTcs!=NULL) fclose(agent.LogTcs);  // v1.6.1
    if(agent.LogAux!=NULL) fclose(agent.LogAux);  // v1.6.1
    exit(3);
  }

  if (client.useISIS)
  {
    sprintf(cmsg, "- Started TCS Agent as ISIS client node %s\n", client.ID);_msgout(cmsg);
    sprintf(cmsg, "  on %s port %d\n", client.Host, client.Port);_msgout(cmsg);
  }
  else
  {
    sprintf(cmsg, "- Started TCS Agent as standalone ISIS node %s\n", client.ID);_msgout(cmsg);
    sprintf(cmsg, "  on %s port %d\n", client.Host, client.Port);_msgout(cmsg);
  }

  sprintf(cmsg, "\n");_msgout(cmsg);

  // Initialize the PC-TCS Telcom tcp link

  if (InitPCTCS(&tcs,reply)<0) {
    REDTEXT;
    sprintf(cmsg, "- PCTCS Telcom tcp link init failed !\n");_msgout(cmsg);
    sprintf(cmsg, "  > %s\n",reply);_msgout(cmsg);
  }
  else {
    sprintf(cmsg, "- PCTCS Telcom tcp link initialized\n");_msgout(cmsg);
    if (TcsSetEpoch(&tcs,reply)<0) {  // v1.2.2
      REDTEXT;
      sprintf(cmsg, "- %s\n", reply);_msgout(cmsg);
    }
  }

  if (InitAUX(&aux,reply)<0) {
    REDTEXT;
    sprintf(cmsg, "- AUX ctrl link init failed !\n");_msgout(cmsg);
    sprintf(cmsg, "  > %s\n",reply);_msgout(cmsg);
  }
  else {
    sprintf(cmsg, "- AUX ctrl link initialized\n");_msgout(cmsg);
  }

  sprintf(cmsg, "\n");_msgout(cmsg);

  // All set to rock-n-roll...

  sprintf(cmsg, "- TCS Agent start..\n\n");_msgout(cmsg);

  sprintf(cmsg, "-------------------------------------------------------\n");_msgout(cmsg);
  sprintf(cmsg, " Type 'quit' to terminate TCS Agent process\n");_msgout(cmsg);
  sprintf(cmsg, " Type 'help' to see a list of commands\n");_msgout(cmsg);
  sprintf(cmsg, "-------------------------------------------------------\n\n");_msgout(cmsg);

  // Startup the command-line history mechanism

  using_history();

  // Setup the command prompt and install the readline() callback
  // handler for this application (KeyboardCommand() in commands.c)

  //sprintf(cliPrompt,"%s%% ",client.ID);
  //rl_callback_handler_install(cliPrompt,KeyboardCommand);
      // to delete readline consol prompt, put CR as printf("\r");
      // to reset consol prompt, use rl_refresh_line(0,0); after printf()
      // --> now rl_refresh_line(0,0) isn't used,   <-- real?? check this !!!
      //     modified at v1.6.0 as belows

  sprintf(cliPrompt,"%s%% ",client.ID);
  //rl_callback_handler_install(cliPrompt,_msgout);
  //rl_callback_handler_install(cliPrompt,_vmsgout); //// <-- effective?? check it !!!
  //rl_callback_handler_install(cliPrompt,KeyboardCommand);
      // rollbacked to original code as belows at v1.6.6.3,
      // because two lines for _msgout/_vmsgout seem not to be effective
      // and rl_refresh_line(0,0); is reactivated in _msgout() and _vmsgout()
      // --> no effective at test of v1.6.6.5

  sprintf(cliPrompt,"%s%% ",client.ID);
  rl_callback_handler_install(cliPrompt,KeyboardCommand);

  // If configured as an ISIS client, broadcast a PING to the ISIS
  // server.  If it fails, we'll have to do the ping by hand after the
  // comm loop starts.

  if (client.useISIS) {
    memset(buf,0,STRLEN_ISISMSG*sizeof(char));
    sprintf(buf,"%s>AL ping\r",client.ID);
    rtn = SendToISISServer(&client,buf);
    {//verbose
      sprintf(cmsg, "ISIS OUT: %s\n",buf);_vmsgout(cmsg);
    }
    if (rtn<0) {
      REDTEXT;
      sprintf(cmsg, "ERROR: Failed to ping the ISIS server...\n");_msgout(cmsg);
      REDTEXT;
      sprintf(cmsg, "       - %s\n",strerror(errno));_msgout(cmsg);
    }
  }

  // If a SIGINT trap is used, set it here...

  // Set the initial states and value for TCS/AUX telemetry link

  tcs.PctcsTick = tcs.TelcomTick = SysTimestamp();
  tcs.UpdateTick = 0.0;  // set 0 for no delay at the first try
  aux.UpdateTick = 0.0;  // set 0 for no delay at the first try, added at v1.6.1

  if(tcs.Link==TCS_DOWN) {
    REDTEXT;
    sprintf(cmsg, "STATUS: Telcom tcp link is DOWN.. please check Telcom\n");_msgout(cmsg);
    {//verbose
      REDTEXT;
      sprintf(cmsg, "        Telcom tcp link initialization failed\n");_vmsgout(cmsg);
    }
    if(!tcs.ArcMode) {
      sprintf(cmsg, ">> Try to connect again using the 'tcsinit' command\n");_msgout(cmsg);
    }
  }

  if(aux.Link==AUX_DOWN) {
    REDTEXT;
    sprintf(cmsg, "STATUS: AUX tcp link is DOWN.. please check AUX ctrl server\n");_msgout(cmsg);
    {//verbose
      REDTEXT;
      sprintf(cmsg, "        AUX tcp link initialization failed\n");_vmsgout(cmsg);
    }
    if(!aux.ArcMode) {
      sprintf(cmsg, ">> Try to connect again using the 'auxinit' command\n");_msgout(cmsg);
    }
  }

  rl_refresh_line(0,0);

  // Set the initial states and value for links auto recovery

  agent.ArcTick = 0.0;  // set 0 for no delay at the first try
  arcloopint = agent.ArcInt / 2.0;

  //////////////////////////////////////////////////////////////////////////////////////////////////////
  // Start the I/O event handling loop

  client.KeepGoing = 1;

  while (client.KeepGoing) { //

    //
    // TCS Link (PC-TCS link & Telcom link) monitoring
    //

    // For the PC-TCS, on each pass through the comm loop, check the time
    // since the last PC-TCS telemetry string was received.  This lets us
    // detect when the PC-TCS has gone idle and set our comm state accordingly.
    // We check to see if the idle time is greater than the idle timeout interval.

    // update & monitoring idle time for Telcom tcp link

    tcs.TelcomIdle = SysTimestamp() - tcs.TelcomTick;

    if(tcs.TelcomIdle > (double)tcs.TelcomTimeout) { //

      switch (tcs.Link) {
      case TCS_UP:
      case TCS_IDLE:
        ClearPCTCS(&tcs);
        REDTEXT;
        sprintf(cmsg, "STATUS: Telcom tcp link is DOWN.. please check Telcom\n");_msgout(cmsg);
        {//verbose
          REDTEXT;
          sprintf(cmsg, "        Telcom tcp link has been down for %.3f(>%d) sec\n",
                        tcs.TelcomIdle,tcs.TelcomTimeout);_vmsgout(cmsg);
        }
        break;
      }

    } // end of if(tcs.TelcomIdle > (double)tcs.TelcomTimeout) 

    // update & monitoring idle time for PC-TCS serial link

    tcs.PctcsIdle  = SysTimestamp() - tcs.PctcsTick;

    if(tcs.PctcsIdle > (double)tcs.PctcsTimeout) { //

      switch (tcs.Link) {
      case TCS_UP:
        tcs.Link = TCS_IDLE;
        REDTEXT;
        sprintf(cmsg, "STATUS: PC-TCS serial link is IDLE.. please check PC-TCS\n");_msgout(cmsg);
        {//verbose
          REDTEXT;
          sprintf(cmsg, "        PC-TCS serial link has been idle for %.3f(>%d) sec\n",
                        tcs.PctcsIdle, tcs.PctcsTimeout);_vmsgout(cmsg);
        }
        break;
      }

    }

    else {

      switch (tcs.Link) {
        case TCS_IDLE:
          tcs.Link = TCS_UP;
          tcs.UpdateFlag = 0;
          GRNTEXT;
          sprintf(cmsg, "STATUS: PC-TCS serial link has become active again\n");_msgout(cmsg);
          if (TcsSetEpoch(&tcs,reply)<0) {    // v1.2.2
            REDTEXT;
            sprintf(cmsg, "ERROR: %s\n", reply);_msgout(cmsg);
          }
          //else {
          //  sprintf(cmsg, "DONE: %s\n", reply);_msgout(cmsg);
          //}    --> removed at v1.4.0
          break;
      }

    } // end of if(tcs.PctcsIdle > (double)tcs.PctcsTimeout) {..} else {

    #ifdef __DEBUG
    printf("\rDEBUG:");r
    switch (tcs.Link) {
      case TCS_UP  : printf(" UP"  );break;
      case TCS_IDLE: printf(" IDLE");break;
      case TCS_DOWN: printf(" DOWN");break;
    }
    //printf("  request idle = %.3f", tcs.UpdateIdle);
    printf("  pctcs idle = %.3f", tcs.PctcsIdle);
    printf("  Telcom idle = %.3f", tcs.TelcomIdle);
    printf("\n");
    fflush(stdout);
    #endif

    //
    // update & monitoring idle time for TCS data update command
    //

    tcs.UpdateIdle  = SysTimestamp() - tcs.UpdateTick;

    if(tcs.UpdateIdle > tcs.UpdateInt) { //

      switch (tcs.Link) {
      case TCS_UP:
      case TCS_IDLE:
        rtn = send(tcs.FDtel, tcs.RequestMsg, tcs.RequestLen, 0);
        if( rtn < tcs.RequestLen ) {
          {//verbose
            CYATEXT;sprintf(cmsg, "Warning: Telemetry request CMD send error..\n");_vmsgout(cmsg);
          }
        }
        break;
      }

      tcs.UpdateTick = SysTimestamp();

    } // end of if(tcs.UpdateIdle > tcs.UpdateInt)

    //
    // update AUX telemetry data
    //

    aux.UpdateIdle  = SysTimestamp() - aux.UpdateTick;

    if(aux.UpdateIdle > aux.UpdateInt) { //

      switch (aux.Link) {
      case AUX_UP:

        // AUX telemetry update and result check

        if(client.Debug) {
          StopWatch(START, NULL);
        }

        rtn = AuxTelemetry(&aux, reply);

        if(client.Debug) {
          printf("> fnum %2d  fopt %-7s  %2d %2d  shut %-7s  sopt %-9s  ",
                  aux.FS_FilterNum, AuxStatusArg(aux.FS_FilterOpStat), 
                  aux.FS_Limits[AUX_IDX_FS_SF], aux.FS_Limits[AUX_IDX_FS_SH], 
                  AuxStatusArg(aux.FS_ShutStatus), AuxStatusArg(aux.FS_ShutOpStat) );
          StopWatch(STOP, "> ");
        }

        if(rtn<0) {
            REDTEXT;
            sprintf(cmsg, "STATUS: AUX link is DOWN.. please check AUX ctrl server\n");_msgout(cmsg);
            {//verbose
              REDTEXT;
              sprintf(cmsg, "        AUX telemetry failed - %s\n", reply);_vmsgout(cmsg);
            }
            if(!aux.ArcMode) {
              sprintf(cmsg, ">> Try to connect again using the 'auxinit' command\n");_msgout(cmsg);
            }
            ClearAUX(&aux);
            continue;  // for reset FD listen
        }

        // Subsystem's status monitoring and print warning message

        for(i=0;i<6;i++) {
          //if(client.isVerbose) 
          if( aux.Statuses[i]==AUX_STATUS_ERROR && auxstat_prev[i]!=AUX_STATUS_ERROR ) {
            CYATEXT;
            sprintf(cmsg, "Warning: AUX subsystem %s's status became ERROR\n", 
                    GetAuxSubsysName(i));_msgout(cmsg);
          }

          auxstat_prev[i] = aux.Statuses[i];
        }

        // Filter/Shutter operation status monitoring and print error message

        if( aux.FS_FilterOpStat==AUX_FS_FOP_ERROR && fopt_prev!=AUX_FS_FOP_ERROR ) {
          REDTEXT;
          sprintf(cmsg, "ERROR: AUX Filter operational error..\n");_msgout(cmsg);
          sprintf(cmsg, " >> check operational status of the filter slide\n");_msgout(cmsg);
        }
        fopt_prev = aux.FS_FilterOpStat;

        if( aux.FS_ShutOpStat==AUX_FS_SOP_ERROR && sopt_prev!=AUX_FS_SOP_ERROR ) {
          REDTEXT;
          sprintf(cmsg, "ERROR: AUX Camera Shutter operational error..\n");_msgout(cmsg);
          sprintf(cmsg, " >> check operational status of the camera shutter\n");_msgout(cmsg);
        }
        sopt_prev = aux.FS_ShutOpStat;

        break;

      } // end of switch (aux.Link)

      aux.UpdateTick = SysTimestamp();

    } // end of if(aux.UpdateIdle > aux.UpdateInt)

    //
    // update & monitoring idle time for TSTAT/ASTAT logging (v1.6.1)
    //

    agent.LogTcsIdle  = SysTimestamp() - agent.LogTcsTick;
    if(agent.LogTcsIdle > agent.LogTcsInt) {
      GetTstatStr(buf);_tcslog(buf);
      agent.LogTcsTick = SysTimestamp();
    }

    agent.LogAuxIdle  = SysTimestamp() - agent.LogAuxTick;
    if(agent.LogAuxIdle > agent.LogAuxInt) {
      GetAstatStr(buf);_auxlog(buf);
      agent.LogAuxTick = SysTimestamp();
    }

    //
    // auto recover try for TCS & AUX tcp links
    //

    if( tcs.ArcMode || aux.ArcMode ) { //

      agent.ArcIdle  = SysTimestamp() - agent.ArcTick;

      if( agent.ArcIdle > arcloopint ) { //

        if(tcs.ArcMode && (arctry%2)==0) { //

          switch (tcs.Link) {
          case TCS_DOWN:
            if(client.Debug) {
              printf("\rDEBUG: Trying to TCS Link recovery ... "); 
              fflush(stdout);
            }
            rtn = InitPCTCS(&tcs,reply);
            if(client.Debug) {
              if(rtn<0) printf("Failure.\n");
              else      printf("Success.\n");
            }
            if(rtn==0) {
              GRNTEXT;
              sprintf(cmsg, "STATUS: Telcom tcp link has been recovered\n");_msgout(cmsg);
              if (TcsSetEpoch(&tcs,reply)<0) {    // v1.2.2
                tcs.PctcsTick = SysTimestamp() - (double)tcs.PctcsTimeout;
                tcs.Link = TCS_IDLE;                
                REDTEXT;
                sprintf(cmsg, "ERROR: %s\n", reply);
                _msgout(cmsg);
                REDTEXT;
                sprintf(cmsg, "       > PC-TCS serial link is set to IDLE.. check the PC-TCS\n");
                _msgout(cmsg);
              }
              //else {
              //  sprintf(cmsg, "DONE: %s\n", reply);_msgout(cmsg);
              //} --> removed at v1.4.0
              //// continue;  // for reset FD listen  //// v1.4.1
            }
            break;
          }

        } // end of if(tcs.ArcMode)

        if(aux.ArcMode && (arctry%2)==1) { //

          switch (aux.Link) {
          case AUX_DOWN:
            if(client.Debug) {
              printf("\rDEBUG: Trying to AUX Link recovery ... "); 
              fflush(stdout);
            }
            rtn = InitAUX(&aux,reply);
            if(client.Debug) {
              if(rtn<0) printf("Failure.\n");
              else      printf("Success.\n");
            }
            if(rtn==0) {
              GRNTEXT;sprintf(cmsg, "STATUS: AUX link has been recovered\n");_msgout(cmsg);
              //// continue;  // for reset FD listen  //// v1.4.1
            }
            break;
          }
        } // end of if(aux.ArcMode)

        agent.ArcTick = SysTimestamp();

        arctry++;

      }  // end of if( agent.ArcIdle > agent.ArcInt)
      
    } // end of if( tcs.ArcMode || aux.ArcMode )

    //
    // Check key input for display control in tel moving status (v1.2.3)
    //

    if(rl_end==0) flag_keyinput = 0;  // if keyinput flushed, flag off

    if(rl_end>0 && !flag_keyinput) {    // if keyinput started, flag on
      rl_refresh_line(0,0);
      flag_keyinput = 1;
    }

    //
    // Reset file descriptor list for calling select()
    //

    FD_ZERO(&read_fd); // clear the table of active file descriptors

    // we always listen for console keyboard input

    FD_SET(kbdFD, &read_fd);

    // if enabled, listen to this app's ISIS client socket

    if (client.FD > 0) FD_SET(client.FD, &read_fd);

    // if TCS was initialized, listen to the PC-TCS Telcom tcp socket

    if (tcs.FDtel > 0) FD_SET(tcs.FDtel, &read_fd);

    // if AUX was initialized, listen to the AUX ctrl server tcp socket

    if (aux.FD > 0) FD_SET(aux.FD, &read_fd);  // for disconnection request from server

    //
    // Do the select() call and wait for activity on any of our communication
    // link or the console keyboard
    //

    memcpy(&timeout_temp, &timeout, sizeof(timeout));
    n_ready = select(sel_wid, &read_fd, NULL, NULL, &timeout_temp);
      // set timeout of select() to process update routine without anyinput in KMTNet TCS

    if (n_ready == 0) {
      #ifdef __DEBUG
      //printf("\rDEBUG: select() return 0, would be a timeout\n");  // removed at v1.2.2
      #endif
      // would be a timeout if enabled, do nothing...
      continue;
    }
    else if (n_ready < 0) {
      select_failnum++;
      {//verbose
        if(select_failnum>select_failnum_sig) {    // v1.2.2
          CYATEXT;sprintf(cmsg, "Warning: select() failed - %s\n", strerror(errno));_vmsgout(cmsg);
        }
      }
      continue;
    }
    else { // somebody wants something, figure out who...

      // Console keyboard input

      if (FD_ISSET(kbdFD, &read_fd)) {
        rl_callback_read_char(); // readline() handler
      }

      // ISIS client socket input (from either the ISIS or a remete client)

      if (FD_ISSET(client.FD, &read_fd)) {
        memset(buf,0,STRLEN_ISISMSG*sizeof(char));
        if (ReadClientSocket(&client,buf)>0) 
          SocketCommand(buf);
      }

      // Input on the TCS link (PC-TCS Telcom tcp socket)

      if (tcs.FDtel > 0) { //

        if (FD_ISSET(tcs.FDtel, &read_fd)) { //

          rtn = recv(tcs.FDtel, recvbuf, STRLEN_REP-1, 0);

          if(rtn<=0) { //
            REDTEXT;
            sprintf(cmsg, "STATUS: Telcom tcp link is DOWN.. please check Telcom\n");_msgout(cmsg);
            {//verbose
              REDTEXT;
              sprintf(cmsg, "        Telcom tcp link was disconnected "
                                                "by a request of the Telcom\n");_vmsgout(cmsg);
            }
            if(!tcs.ArcMode) {
              sprintf(cmsg, ">> Try to connect again using the 'tcsinit' command\n");_msgout(cmsg);
            }

            ClearPCTCS(&tcs);
          }
          else if(rtn<tcs.MinTelemetryLen) {
            tcs.TelcomTick = SysTimestamp();

            if(client.Debug) {
              recvbuf[tcs.ReqHedLen] = NULL;
              printf("\rDEBUG: %s %s --> no telemetry data\n", UTCTime(), recvbuf);
              rl_refresh_line(0,0);
            }
          }
          else { // if we got something big enough, try to parse it
            tcs.TelcomTick = SysTimestamp();

            //// Ref: old-version code until v1.6.3
            //rtn = parse_comsoft(&tcs,(recvbuf+tcs.ReqHedLen));

            //// modified at at v1.6.5
            for(i=1;i<=TCS_DECODINGNUM;i++) {
              rtn = parse_comsoft(&tcs,(recvbuf+tcs.ReqHedLen));
              if(rtn<=0) { tcs.DecodingNum=i; break; }
            }

            //if(rtn==0) tcs.PctcsTick = SysTimestamp();    // telemetry data ok, until v1.6.2
            if(rtn>=0) tcs.PctcsTick = SysTimestamp();    // telemetry data acceptable (v1.6.3)

            if(!flag_keyinput)       // display at no keyinput only, v1.2.3
              UpdateTcsMoving(&tcs); // If we're moving, show update status

            if(client.Debug && 0) {  //disabled at v1.2
              if(rtn<0) printf("\rDEBUG: %s %s  --> no Az/Alt/secz data\n", UTCTime(), recvbuf);
              else      printf("\rDEBUG: %s %s  --> telemetry data ok\n"  , UTCTime(), recvbuf);
              rl_refresh_line(0,0);
            }
          } // end of TCS recv msg handling - if(recvlen<=0) {..} else {..

          memset(recvbuf,0,STRLEN_REP*sizeof(char));  // reset tcp recv buffer

        } // end of TCS telemetry socket read - if (FD_ISSET(tcs.FDtel, &read_fd))

      } // end of TCS telemetry tcp socket(FDtel) handling - if (tcs.FDtel > 0)


      // Input on the AUX link (AUX control server tcp socket)
      //  - only for disconnection request from server

      if (aux.FD > 0) { //

        if (FD_ISSET(aux.FD, &read_fd)) { //

          rtn = recv(aux.FD, recvbuf, STRLEN_REP-1, 0);

          if(rtn<=0) { //
            REDTEXT;
            sprintf(cmsg, "STATUS: AUX link is DOWN.. please check AUX ctrl server\n");_msgout(cmsg);
            {//verbose
              REDTEXT;
              sprintf(cmsg, "        AUX link was disconnected "
                                                     "by a request of AUX server\n");_vmsgout(cmsg);
            }
            if(!aux.ArcMode) {
              sprintf(cmsg, ">> Try to connect again using the 'auxinit' command\n");_msgout(cmsg);
            }
            ClearAUX(&aux);
          }
          else {
            recvbuf[rtn] = NULL;
            {//verbose
              sprintf(cmsg, " AUX IN : '%s' - recv msg from AUX without request\n", recvbuf);
              _vmsgout(cmsg);              
            }
          } // end of AUX recv msg handling - if(recvlen<=0) {..} else {

          memset(recvbuf,0,STRLEN_REP*sizeof(char));  // reset AUX tcp recv buffer

        } // end of AUX tcp socket read - if (FD_ISSET(aux.FD, &read_fd))

      } // end of AUX tcp socket(aux.FD) handling - if (aux.FD > 0)

      // add any new FD handlers here...

      // ..
      
      // select() noerr reset

      select_failnum = 0;

    } // end of select() I/O handling checking - if (n_ready==0) {..} else {

  } // bottom of the while(client.KeepGoing) loop

  //------------------------------------------------------------
  //
  // If we got here, the client was instructed to shut down
  //

  sprintf(cmsg, "                                \n");_msgout(cmsg);
  sprintf(cmsg, "TCSAgent client shutting down...\n\n");_msgout(cmsg);  // v1.6.0

  // Tear down the client socket connection

  if (client.FD > 0) close(client.FD);

  // Tear down the TCS and AUX links

  ClearPCTCS(&tcs);
  ClearAUX(&aux);

  // Remove the readline() callback handler

  rl_callback_handler_remove();

  // Close message/event log (v1.6.0)

  _msglog("LOG_END\n\n");
  if(agent.LogMsg!=NULL) fclose(agent.LogMsg);

  // Close TSTAT/ASTAT log (v1.6.1)

  _tcslog("LOG_END\n\n");
  _auxlog("LOG_END\n\n");
  if(agent.LogTcs!=NULL) fclose(agent.LogTcs);
  if(agent.LogAux!=NULL) fclose(agent.LogAux);


  // all done, say goodbye...

  printf("\rBye.            \n\n");

  exit(0);

}




//------------------------------------------------------------------------------
// Test codes
//

int cmd_tcsstatus(char*, MsgType, char*);

int testcode(void)
{

  /*
  // For debugging at v1.6.5.1
  {{

   int nTest, rtn, prevtcslink, i;
  char tstatstr[STRLEN_REP];
  char rawpctcs[STRLEN_REP];

  memset(tstatstr, 0, STRLEN_REP*sizeof(char));
  memset(rawpctcs, 0, STRLEN_REP*sizeof(char));
  prevtcslink = tcs.Link;
  tcs.Link = TCS_UP;

  for(nTest=0;nTest<10000;nTest++) {

    //switch (nTest%5) {
    //  case  0: strcpy(rawpctcs, "0  174600.80 -244009.9  -01:13:18 16:33:37 72.9  +103.7  1.05  E           2000.000           2   170421");break;
    //  case  1: strcpy(rawpctcs, "0  175424.84 -331506.2  +01:29:39 19:25:05 70.7   -74.6  1.06  E           2000.000           2   170421");break;
    //  case  2: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52 82.6   -78.1  1.01  E           2000.000           2   170421");break;
    //  case  3: strcpy(rawpctcs, "0  040900.63 -300241.1  +00:00:00 04:09:31 90.0    +0.0  1.00  E          12000.000           2   170421");break;
    //  case  4: strcpy(rawpctcs, "0  075011.88 -295718.2  +00:00:00 07:50:43 90.0    +0.0  1.00  e          12000.000           2   170422");break;
    //  default: printf("TEST: Finished.\n");return -1;
    //}

    switch (nTest%20) {
      case  0: strcpy(rawpctcs, "0  174600.80 -244009.9  -01:13:18 16:33:37 72.9  +103.7  1.05  E           2000.000           2   170421");break;
      case  1: strcpy(rawpctcs, "0  174600.80 -244009.9  -01:13:18 16:33:37  8.4  +103.7  1.05  E           2000.000           2   170421");break;
      case  2: strcpy(rawpctcs, "0  174600.80 -244009.9  -01:13:18 16:33:37 72.9  -103.7  1.05  E           2000.000           2   170421");break;
      case  3: strcpy(rawpctcs, "0  174600.80 -244009.9  -01:13:18 16:33:37  8.4  -103.7  1.05  E           2000.000           2   170421");break;
      case  4: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52 82.6   +78.1  1.01  E           2000.000           2   170421");break;
      case  5: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52  5.1   +78.1  1.01  E           2000.000           2   170421");break;
      case  6: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52 82.6   -78.1  1.01  E           2000.000           2   170421");break;
      case  7: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52  5.1   -78.1  1.01  E           2000.000           2   170421");break;
      case  8: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52 82.6    +3.4  1.01  E           2000.000           2   170421");break;
      case  9: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52  5.1    +3.4  1.01  E           2000.000           2   170421");break;
      case 10: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52 82.6    -3.4  1.01  E           2000.000           2   170421");break;
      case 11: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52  5.1    -3.4  1.01  E           2000.000           2   170421");break;
      case 12: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52  0.0    +0.0  1.01  E           2000.000           2   170421");break;
      case 13: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52  0.0    -0.0  1.01  E           2000.000           2   170421");break;
      case 14: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52 90.0    +0.0  1.01  E           2000.000           2   170421");break;
      case 15: strcpy(rawpctcs, "0  175408.22 -311535.0  +00:33:45 18:28:52 90.0    -0.0  1.01  E           2000.000           2   170421");break;
      case 16: strcpy(rawpctcs, "0  040900.63 -300241.1  +00:00:00 04:09:31 90.0    +0.0 10.00  E          12000.000           2   170421");break;
      case 17: strcpy(rawpctcs, "0  075011.88 -295718.2  +00:00:00 07:50:43 90.0    +0.0 10.00  e          12000.000           2   170422");break;
      case 18: strcpy(rawpctcs, "0  040900.63 -300241.1  +00:00:00 04:09:31 90.0    +0.0  0.00  E          12000.000           2   170421");break;
      case 19: strcpy(rawpctcs, "0  075011.88 -295718.2  +00:00:00 07:50:43 90.0    +0.0  0.00  e          12000.000           2   170422");break;
      default: printf("TEST: Finished.\n");return -1;
    }

    //rtn = parse_comsoft(&tcs,rawpctcs);
    for(i=1;i<=TCS_DECODINGNUM;i++) {
      rtn = parse_comsoft(&tcs,rawpctcs);
      if(rtn<=0) { tcs.DecodingNum=i; break; }
    }

    if(rtn<0) {
      printf("TEST: Failure - %s\n", tcs.DataChkMsg);
      return -1;    
    }
  
    //GetTstatStr(tstatstr);
    //printf("TEST: %04d %s", nTest, tstatstr);

    cmd_tcsstatus(NULL, EXEC, tstatstr);
    //printf("TEST: %04d %s  \"%s\"    %d  %d  %s\n", 
    //  nTest, tstatstr, tcs.RawPacket, tcs.DecodingNum, tcs.EncodingNum, tcs.DataChkMsg);
    printf("TEST: %04d %s  %d  %d  %s\n", 
      nTest, tstatstr, tcs.DecodingNum, tcs.EncodingNum, tcs.DataChkMsg);

  }

  printf("TEST: Done.\n");

  tcs.Link = prevtcslink;

  return 1;

  }}
  */
  
  //printf("\rTEST: %d  %d\n", 0x00000003, 0xFFFFFFFD);  // 3 -3
  //return 1;

  rl_refresh_line(0,0);
  return 0;  // keep going main()
}

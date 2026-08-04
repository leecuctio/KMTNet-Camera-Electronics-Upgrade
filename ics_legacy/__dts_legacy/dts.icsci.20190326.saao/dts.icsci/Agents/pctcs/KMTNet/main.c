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
//
//   2015 Jan xx - Send STATUS/ERROR message to configured node (v1.4.9?)
//   2015 Jan xx - ARC & Link monitoring routine modification (v1.5?)
//   
//
//---------------------------------------------------------------------------

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

// The main event...

int
main(int argc, char *argv[]) 
{
  int i, arctry, rtn;
  int verbose_temp, auxstat_prev[6];
  int fopt_prev, sopt_prev;
  double arcloopint;

  char buf[ISIS_MSGSIZE];    // command/message buffer
  char reply[BIG_STR_SIZE];  // reply buffer
  char recvbuf[BUF_SIZE];    // TCS & AUX receved tcp message buffer

  // readline & history handling stuff

  int flag_keyinput;
  char cliPrompt[ISIS_NODESIZE+2]; // the console prompt is our ISIS node name

  // maximum select() width (overkill, but works for now)

  int sel_wid;

  // select() event handler parameters

  fd_set read_fd;
  int kbdFD;
  int n_ready;
  int select_failnum, select_failnum_sig;
  struct timeval timeout, timeout_temp;

  // Basic initializations

  tcs.FDtel = -1;
  tcs.FDcmd = -1;
  aux.FD = -1;
  memset(recvbuf,0,BUF_SIZE);

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
    exit(1);
  }

  // Application version input

  rtn = strlen(APP_VERSION);
  if(rtn) strcpy(agent.AppVersion, APP_VERSION);
  else    strcpy(agent.AppVersion, APP_VER);

  // So far so good, give the welcome information

  printf("\n");
  printf("  ----------------------------------------------------\n");
  printf("                   KMTNet TCS Agent\n");
  printf("    Interactive PC-TCS & AUX Remote Interface Client\n\n");
  printf("    Version: %s (%s %s)\n",agent.AppVersion,APP_COMPDATE,APP_COMPTIME);
  printf("  ----------------------------------------------------\n");
  printf("\n");

  // Load the specified runtime config file, or use the default if none given

  if (argc==2)
    rtn = LoadConfig(argv[1]);
  else
    rtn = LoadConfig(DEFAULT_RCFILE);

  if (rtn!=0) {
    REDTEXT;
    printf("  Runtime configuration loading failed\n");
    printf("  >> TCS Agent aborting\n");
    TXTRESET;
    exit(1);
  }
  else {
    printf("- Runtime configuration loading completed\n");
  }

  // Some useful startup info (who, what, when...)

  strcpy(agent.UserID,getenv("USER"));  // Who started this thing, anyway?
  strcpy(agent.exeFile,argv[0]);        // command executed
  strcpy(agent.StartTime,ISODate());    // when the agent was started

  // If required, initialize the socket connection to the ISIS server.
  // We can disable ISIS interaction by specifying "Mode Standalone" or
  // "ServerID None" in the runtime config file

  if (client.useISIS) {
    if (InitISISServer(&client)<0) {
      REDTEXT;
      printf("  ISIS server connection initialization failed\n");
      printf("  >> TCS Agent aborting\n");
      TXTRESET;
      exit(2);
    }
  }

  // Open the client network socket port for ISIS communications.  We
  // open this anyway since it costs us nothing, and a subsequent "open
  // isis" command will need it.  Also provides the the comm port used
  // for socket comm in Standalone mode.
  
  if (OpenClientSocket(&client)<0) {
    REDTEXT;
    printf("  Client socket initialization failed\n");
    printf("  >> TCS Agent aborting\n");
    TXTRESET;
    exit(3);
  }

  if (client.useISIS)
    printf("- Started TCS Agent as ISIS client node %s\n  on %s port %d\n",
	   client.ID, client.Host, client.Port);
  else
    printf("- Started TCS Agent as standalone ISIS node %s\n  on %s port %d\n",
	   client.ID, client.Host, client.Port);

  printf("\n");

  // Initialize the PC-TCS Telcom tcp link

  if (InitPCTCS(&tcs,reply)<0) {
    REDTEXT;
    printf("- PCTCS Telcom tcp link init failed\n  > %s\n",reply);
    TXTRESET;
  }
  else {
    printf("- PCTCS Telcom tcp link initialized\n");
    if (TcsSetEpoch(&tcs,reply)<0) {  // v1.2.2
      REDTEXT;  
      printf("- %s\n", reply);
      TXTRESET;
    }
  }

  if (InitAUX(&aux,reply)<0) {
    REDTEXT;
    printf("- AUX ctrl link init failed..\n  > %s\n",reply);
    TXTRESET;
  }
  else {
    printf("- AUX ctrl link initialized\n");
  }

  printf("\n");

  // All set to rock-n-roll...

  printf("- TCS Agent start..\n\n");

  printf("-------------------------------------------------------\n");
  printf(" Type 'quit' to terminate TCS Agent process\n");
  printf(" Type 'help' to see a list of commands\n");
  printf("-------------------------------------------------------\n\n");

  // Startup the command-line history mechanism

  using_history();

  // Setup the command prompt and install the readline() callback
  // handler for this application (KeyboardCommand() in commands.c)

  sprintf(cliPrompt,"%s%% ",client.ID);
  rl_callback_handler_install(cliPrompt,KeyboardCommand);
      // to delete readline consol prompt, put CR as printf("\r");
      // to reset consol prompt, use rl_refresh_line(0,0); after printf()

  // If configured as an ISIS client, broadcast a PING to the ISIS
  // server.  If it fails, we'll have to do the ping by hand after the
  // comm loop starts.

  if (client.useISIS) {
    memset(buf,0,ISIS_MSGSIZE);
    sprintf(buf,"%s>AL ping\r",client.ID);
    rtn = SendToISISServer(&client,buf);
    if (client.isVerbose) {
      printf("\rOUT: %s\n",buf);
      rl_refresh_line(0,0);
    }
    if (rtn<0) {
      REDTEXT;
      printf("\rERROR: Failed to ping the ISIS server...\n");
      printf("       - %s\n",strerror(errno));
      TXTRESET;
      rl_refresh_line(0,0);
    }
  }

  // If a SIGINT trap is used, set it here...

  // Set the initial states and value for TCS telemetry link

  tcs.PctcsTick = tcs.TelcomTick = SysTimestamp();
  tcs.UpdateTick = 0.0;  // set 0 for no delay at the first try

  if(tcs.Link==TCS_DOWN) {
    REDTEXT;
    printf("\rSTATUS: Telcom tcp link is DOWN.. please check Telcom\n");
    if(client.isVerbose)
      printf("        Telcom tcp link initialization failed\n");
    TXTRESET;
    if(!tcs.ArcMode)
      printf(">> Try to connect again using the \"tcsinit\" command\n");
    rl_refresh_line(0,0);
  }

  if(aux.Link==AUX_DOWN) {
    REDTEXT;
    printf("\rSTATUS: AUX tcp link is DOWN.. please check AUX ctrl server\n");
    if(client.isVerbose)
      printf("        AUX tcp link initialization failed\n");
    TXTRESET;
    if(!aux.ArcMode)
      printf(">> Try to connect again using the 'auxinit' command\n");
    rl_refresh_line(0,0);
  }

  // Set the initial states and value for links auto recovery

  agent.ArcTick = 0.0;  // set 0 for no delay at the first try
  arcloopint = agent.ArcInt / 2.0;

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
        printf("\rSTATUS: Telcom tcp link is DOWN.. please check Telcom\n");
        if(client.isVerbose)
          printf("        Telcom tcp link has been down for %.3f(>%d) sec\n",
                  tcs.TelcomIdle,tcs.TelcomTimeout);
        TXTRESET;
        rl_refresh_line(0,0);
        break;
      }

    } // end of if(tcs.TelcomIdle > (double)tcs.TelcomTimeout) 

    // update & monitoring idle time for PC-TCS serial link

    tcs.PctcsIdle  = SysTimestamp() - tcs.PctcsTick;

    if(tcs.PctcsIdle > (double)tcs.PctcsTimeout) { //

      switch (tcs.Link) {
      case TCS_UP:
        tcs.Link = TCS_IDLE;
        rl_refresh_line(0,0);
        REDTEXT;
        printf("\rSTATUS: PC-TCS serial link is IDLE.. please check PC-TCS\n");
        if(client.isVerbose)
          printf("        PC-TCS serial link has been idle for %.3f(>%d) sec\n",
                  tcs.PctcsIdle, tcs.PctcsTimeout);
        TXTRESET;
        rl_refresh_line(0,0);
        break;
      }

    }

    else {

      switch (tcs.Link) {
      case TCS_IDLE:
        tcs.Link = TCS_UP;
        tcs.UpdateFlag = 0;

        rl_refresh_line(0,0);

        GRNTEXT;
        printf("\rSTATUS: PC-TCS serial link has become active again\n");
        TXTRESET;

        if (TcsSetEpoch(&tcs,reply)<0) {    // v1.2.2
          REDTEXT;
          printf("ERROR: %s\n", reply);
          TXTRESET;
        }
        //else {
        //  printf("DONE: %s\n", reply);
        //}    --> removed at v1.4.0
        rl_refresh_line(0,0);
        break;
      }

    } // end of if(tcs.PctcsIdle > (double)tcs.PctcsTimeout) {..} else {

    #ifdef __DEBUG
    printf("\rDEBUG:");
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
          if(client.isVerbose) {
            CYATEXT;
            printf("\rWarning: Telemetry request CMD send error..\n");
            TXTRESET;
            rl_refresh_line(0,0);
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
        else {
          verbose_temp=client.isVerbose;
          client.isVerbose=0;
        }

        rtn = AuxTelemetry(&aux, reply);

        if(client.Debug) {
          printf("> fnum %2d  fopt %-7s  %2d %2d  shut %-7s  sopt %-9s  ",
                  aux.FS_FilterNum, AuxStatusArg(aux.FS_FilterOpStat), 
                  aux.FS_Limits[AUX_IDX_FS_SF], aux.FS_Limits[AUX_IDX_FS_SH], 
                  AuxStatusArg(aux.FS_ShutStatus), AuxStatusArg(aux.FS_ShutOpStat) );
          StopWatch(STOP, "> ");
        }
        else {
          client.isVerbose=verbose_temp;
        }

        if(rtn<0) {
            REDTEXT;
            printf("\rSTATUS: AUX link is DOWN.. please check AUX ctrl server\n");
            if(client.isVerbose)
              printf("        AUX telemetry failed - %s\n", reply);
            TXTRESET;
            if(!aux.ArcMode)
              printf(">> Try to connect again using the 'auxinit' command\n");
            rl_refresh_line(0,0);

            ClearAUX(&aux);
            continue;  // for reset FD listen
        }

        // Subsystem's status monitoring and print warning message

        for(i=0;i<6;i++) {
          //if(client.isVerbose) 
          if( aux.Statuses[i]==AUX_STATUS_ERROR && auxstat_prev[i]!=AUX_STATUS_ERROR ) {
            CYATEXT;
            printf("\rWarning: AUX subsystem %s's status became ERROR\n", 
                    GetAuxSubsysName(i));
            TXTRESET;
            rl_refresh_line(0,0);
          }

          auxstat_prev[i] = aux.Statuses[i];
        }

        // Filter/Shutter operation status monitoring and print error message

        if( aux.FS_FilterOpStat==AUX_FS_FOP_ERROR && fopt_prev!=AUX_FS_FOP_ERROR ) {
          REDTEXT;
          printf("\rERROR: AUX Filter operational error occurred..\n");
          TXTRESET;
          printf(" >> check operational status of the filter slide\n");
          rl_refresh_line(0,0);
        }
        fopt_prev = aux.FS_FilterOpStat;

        if( aux.FS_ShutOpStat==AUX_FS_SOP_ERROR && sopt_prev!=AUX_FS_SOP_ERROR ) {
          REDTEXT;
          printf("\rERROR: AUX Camera Shutter operational error occurred..\n");
          TXTRESET;
          printf(" >> check operational status of the camera shutter\n");
          rl_refresh_line(0,0);
        }
        sopt_prev = aux.FS_ShutOpStat;

        break;

      } // end of switch (aux.Link)

      aux.UpdateTick = SysTimestamp();

    } // end of if(aux.UpdateIdle > aux.UpdateInt)

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
              printf("\rSTATUS: Telcom tcp link has been recovered\n");
              TXTRESET;
              if (TcsSetEpoch(&tcs,reply)<0) {    // v1.2.2
                REDTEXT;
                tcs.PctcsTick = SysTimestamp() - (double)tcs.PctcsTimeout;
                tcs.Link = TCS_IDLE;                
                printf("ERROR: %s\n", reply);
                printf("       > PC-TCS serial link is set to IDLE.. check the PC-TCS\n");
                TXTRESET;
              }
              //else {
              //  printf("DONE: %s\n", reply);
              //} --> removed at v1.4.0
              rl_refresh_line(0,0);
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
              GRNTEXT;
              printf("\rSTATUS: AUX link has been recovered\n");
              TXTRESET;
              rl_refresh_line(0,0);
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
      if(client.isVerbose) {
        if(select_failnum>select_failnum_sig) {    // v1.2.2
          CYATEXT;
          printf("\rWarning: select() failed - %s\n", strerror(errno));
          TXTRESET;
          rl_refresh_line(0,0);
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
        memset(buf,0,ISIS_MSGSIZE);
        if (ReadClientSocket(&client,buf)>0)
          SocketCommand(buf);
      }

      // Input on the TCS link (PC-TCS Telcom tcp socket)

      if (tcs.FDtel > 0) { //

        if (FD_ISSET(tcs.FDtel, &read_fd)) { //

          rtn = recv(tcs.FDtel, recvbuf, BUF_SIZE-1, 0);

          if(rtn<=0) { //
            REDTEXT;
            printf("\rSTATUS: Telcom tcp link is DOWN.. please check Telcom\n");
            if(client.isVerbose)
              printf("        Telcom tcp link was disconnected "
                                                "by a request of the Telcom\n");
            TXTRESET;
            if(!tcs.ArcMode)
              printf(">> Try to connect again using the 'tcsinit' command\n");
            rl_refresh_line(0,0);

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

            rtn = parse_comsoft(&tcs,(recvbuf+tcs.ReqHedLen));
            if(rtn==0) tcs.PctcsTick = SysTimestamp();    // telemetry data ok

            if(!flag_keyinput)       // display at no keyinput only, v1.2.3
              UpdateTcsMoving(&tcs); // If we're moving, show update status

            if(client.Debug && 0) {  //disabled at v1.2
              if(rtn<0) printf("\rDEBUG: %s %s  --> no Az/Alt/secz data\n", 
                         UTCTime(), recvbuf);
              else      printf("\rDEBUG: %s %s  --> telemetry data ok\n", 
                         UTCTime(), recvbuf);
              rl_refresh_line(0,0);
            }
          } // end of TCS recv msg handling - if(recvlen<=0) {..} else {..

          memset(recvbuf,0,BUF_SIZE);  // reset tcp recv buffer

        } // end of TCS telemetry socket read - if (FD_ISSET(tcs.FDtel, &read_fd))

      } // end of TCS telemetry tcp socket(FDtel) handling - if (tcs.FDtel > 0)


      // Input on the AUX link (AUX control server tcp socket)
      //  - only for disconnection request from server

      if (aux.FD > 0) { //

        if (FD_ISSET(aux.FD, &read_fd)) { //

          rtn = recv(aux.FD, recvbuf, BUF_SIZE-1, 0);

          if(rtn<=0) { //
            REDTEXT;
            printf("\rSTATUS: AUX link is DOWN.. please check AUX ctrl server\n");
            if(client.isVerbose)
              printf("        AUX link was disconnected by a request of AUX server\n");
            TXTRESET;
            if(!aux.ArcMode)
              printf(">> Try to connect again using the 'auxinit' command\n");
            rl_refresh_line(0,0);

            ClearAUX(&aux);
          }
          else {
            recvbuf[rtn] = NULL;
            if(client.isVerbose) {
              printf("\r AUX IN : '%s' - recv msg from AUX without request\n", recvbuf);
              rl_refresh_line(0,0);
            }
          } // end of AUX recv msg handling - if(recvlen<=0) {..} else {

          memset(recvbuf,0,BUF_SIZE);  // reset AUX tcp recv buffer

        } // end of AUX tcp socket read - if (FD_ISSET(aux.FD, &read_fd))

      } // end of AUX tcp socket(aux.FD) handling - if (aux.FD > 0)

      // add any new FD handlers here...

      // ..
      
      // select() noerr reset

      select_failnum = 0;

    } // end of select() I/O handling checking - if (n_ready==0) {..} else {

  } // bottom of the while(client.KeepGoing) loop

  //----------------------------------------------------------------
  //
  // If we got here, the client was instructed to shut down
  //

  printf("\r    \npctcs client shutting down...\n");

  // Tear down the client socket connection

  if (client.FD > 0) close(client.FD);

  // Tear down the TCS and AUX links

  ClearPCTCS(&tcs);
  ClearAUX(&aux);

  // Remove the readline() callback handler

  rl_callback_handler_remove();

  // all done, say goodbye...

  printf("bye\n\n");

  exit(0);

}

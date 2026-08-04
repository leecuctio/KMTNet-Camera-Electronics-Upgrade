//
// commands.c - command action functions for the TCS Agent application
//
// Includes the high-level handlers, plus the common action subroutines
// called by each:
//
//    void KeyboardCommand() - handle keyboard commands
//    void SocketCommand()   - handle commands from other ISIS nodes
//
//    int cmd_xxxxx()        - individual command "action" handlers
//
// Author:
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2004 February 17 (original version - Yale1m v3.3.1)
//
//   S. Cha, KASI KMTNet team
//   chasm@kasi.re.kr
//   2014 April 1 (KMTNet version)
//
// Modification History:
//   2014 May 12: modified for KMTNet TCS [sc/kasi]
//   2014 Aug 08: update according to the commands definition revision to 
//                KMTNet TCS Agent Rev.2/AUX remote commands definition v20140802,
//                and TCSAgent version update from v1.1 to v1.2
//   2014 Aug 26: EPOCH setting automatically in tcsinit() (v1.2.1)
//                TCS command socket & AUX socket recv() timeout setting (v1.2.2)
//                STEP RA offset changed from RA difference to angular distance (v1.2.3)
//                Some other debugging and improvement (v1.2.4)
//   2014 Sep 02: Skip's user interface portocol added (v1.3.0)
//                tcmd/treq message modified, TREQ - cmd_treq() added, 
//                ':' added in RA/DEC string, dtilt/tffgoto cmd set to REQ:,
//                FILNAME - cmd_afilname() & AuxFilterNameUpdate() added,
//                TCSSTATUS/AUXSTATUS keyword added in the reply
//   2014 Sep 05: Minor debuggings (v1.3.1)
//   2014 Sep 28: FILTER cmd modified for error handling on the AUX ctrl sw 
//                to set AUX.Filters.InputType to Remote (v1.3.2), 
//                Forcing to ignore shutter switch error for temporary optimization,
//                Debugging for tguide (v1.3.2.temp)
//   2015 Jan 12: Disable the temporary forcing rotine to ignore shutter error (v1.4.0),
//                AUX Filter name update in FSA update, check FS status in cmd_afilter(),
//                TCSSTATUS/AUXSTATUS/TSTAT/ASTAT/FSASTAT strings modification,
//                Filter change with filter name/initial arg (v1.4.1)
//   2015 Jan 17: SITEID keyword added to INFO/AUXSTATUS/ASTAT strings to identify 
//                the site regardless of the camera software (v1.4.2)
//   2015 Jan 21: Modified to accept any ID in ISIS client mode, added MsgFromISIS
//                for message output handling  (v1.4.3), Tick utility (v1.4.4)
//   2015 Feb 12: AUXSTATUS modification FILTNUM/FILTNAME/SITEID --> FILNUM/FILTER/TELID,
//                filnum command added (v1.4.5)
//                
//
//
//   2015 Jan xx: SendStatus() added (v1.4.9?)
//   2015 Jan xx: fttgotop()/dtiltp() added for Tip/Tilt adjustment with polar coordsys,
//                .... (v1.5?)
//
//   Update plan: 
//
//
//---------------------------------------------------------------------------

#include "pctcs.h"     // PC-TCS Agent application header file
#include "commands.h"  // Command tree header file

extern isisclient_t client;  // global client runtime config table
extern tcsagent_t agent;     // TCS Agent data (this process)
extern pctcs_t tcs;
extern auxctrl_t aux;

int SocketCmdFlag = 0;  // for important message display
char SourceID[ISIS_NODESIZE];

//---------------------------------------------------------------------------
//---------------------------------------------------------------------------
//
// Command event callback and handling functions
//

//---------------------------------------------------------------------------
//
// KeyboardCommand() - process a command from the keyboard
//
// Calls the low-level cmd_xxx() routines for most commands, as
// well as handling commands particular to the console keyboard
//
// This version of the KeyboardCommand() function is setup as
// a callback for readline(), like TTYHandler in the main ISIS
// server application
//

void
KeyboardCommand(char *line)
{
  char cmd[BIG_STR_SIZE];       // command string (oversized)
  char args[BIG_STR_SIZE];      // command-line argument buffer (oversized)
  char reply[BIG_STR_SIZE];     // command reply buffer

  // ISIS message handling stuff

  char msg[ISIS_MSGSIZE];       // ISIS message buffer
  char destID[ISIS_NODESIZE];   // ISIS message destination node ID
  char msgbody[ISIS_MSGSIZE];   // ISIS message body

  // Variables used to traverse the command tree

  int i;
  int nfound=0;
  int icmd=-1;

  // Pointer for the keyboard message buffer

  char *message;

  // Stuff for the history facility

  char *expansion;
  int result;

  // If line is NULL, we have nothing to do, return

  if (line==NULL) return;

  // Similarly, if line is blank, return

  if (strlen(line)==0) {
    free(line);
    return;
  }

  // Allocate memory for the message buffer and clear it

  message = (char *)malloc((ISIS_MSGSIZE)*sizeof(char));
  memset(message,0,ISIS_MSGSIZE);

  // Copy the keyboard input line into the message buffer 

  strcpy(message,line);

  // do any history expansion (!, !!, etc.) if required

  if (line[0]) {
    result = history_expand(line,&expansion);
    if (result)
      printf("%s\n",expansion);
    
    if (result < 0 || result==2) {
      free(expansion);
      return;
    }

    add_history(expansion);
    memset(message,0,ISIS_MSGSIZE);
    sprintf(message,"%s",expansion);
    free(expansion);
  }

  // We're all done with the original string from readline(), free it

  free(line);

  // Remove any \n terminator on the message string

  if (message[strlen(message)-1]=='\n') message[strlen(message)-1]='\0';

  // Clear the command handling strings

  memset(reply,0,sizeof(reply));
  memset(args,0,sizeof(args));
  memset(cmd,0,sizeof(cmd));

  // Split message into command and argument strings

  sscanf(message,"%s %[^\n]",cmd,args);

  // We're all done with the message string, free its memory

  free(message);

  // Message Handling:

  // >XX commands
  //
  // Look for > in cmd, this means a redirect to another ISIS node.
  // This is handled outside the usual command tree, for the obvious
  // reason that the syntax is unique to this operation.

  if (strncasecmp(cmd,">",1)==0) {
    if (client.useISIS) {
      memset(msg,0,sizeof(msg));
      memset(destID,0,sizeof(destID));
      memset(msgbody,0,sizeof(msgbody));

      sscanf(cmd,">%s",destID); // extract the destination node ID
      strcpy(msgbody,args);     // and the message body

      // The trick here is that REQ doesn't put anything in the
      // msgtype field, so that whatever msgtype designator is
      // in the message string gets retained.

      strcpy(msg,ISISMessage(client.ID,destID,REQ,msgbody));

      // and send it off

      SendToISISServer(&client,msg);
      if (client.isVerbose) {
        msg[strlen(msg)-1]='\0';
        printf("ISIS OUT: %s\n",msg);
      }
    }
    else {
      REDTEXT;
      printf("No ISIS server active >> command unavailable\n");
      TXTRESET;
    }
    
  }

  // All other commands use the cmd_xxx() action calls

  else { 

    // Traverse the command table, matches are case-insensitive, but
    // must be exact word matches (no abbreviations or aliases)
    
    nfound = 0;
    for (i=0; i<NumCommands; i++) {
      if (strcasecmp(cmdtab[i].cmd,cmd)==0) { 
        nfound++;
        icmd=i;
        break;
      }
    }
    if (nfound == 0) {
      if (strlen(cmd)>0) {
        REDTEXT;
        printf("ERROR: Unknown command - '%s'\n",cmd);
        TXTRESET;
      }
    }
    else {
	
      // all console keyboard are treated as EXEC: type messages
	
      switch (cmdtab[icmd].action(args,EXEC,reply)) {
	
      case CMD_ERR:
        REDTEXT;
        printf("ERROR: %s\n",reply);
        TXTRESET;
        break;
	
      case CMD_OK:
        printf("DONE: %s\n",reply);
        TXTRESET;
        break;
	
      case CMD_NOOP:
      default:
        break;
	
      } // end of switch()
    }
  }
}

//---------------------------------------------------------------------------
//
// SocketCommand() - process a message or command from an ISIS server/client
//
// All EXEC: and implicit REQ: type messages are passed to cmd_xxx()
// action routines for processing, while the remaining informational
// messages are simply echoed to the console screen.  More sophisticated
// handlers might pass such messages on to parser/handlers of their own
// if the inputs were actually used for something other than information
// for the user.
//
// All messages received from an ISIS node are assumed to be in the
// proper "ICIMACS" protocol messaging syntax.
//
// Note that EXEC: is new to the ISIS implementation of ICIMACS, and
// allows remote nodes to transmit protected "executive" commands to
// clients, giving them access to commands that would otherwise only be
// available on the console keyboard (e.g., the "quit" command).
//

void
SocketCommand(char *buf)
{

  // ISIS message components 

  char msg[ISIS_MSGSIZE];       // Full ISIS message buffer
  char srcID[ISIS_NODESIZE];    // ISIS message sending node ID
  char destID[ISIS_NODESIZE];   // ISIS message destination node ID
  MsgType msgtype = REQ;        // ISIS message type, defined in isisclient.h
  char msgbody[ISIS_MSGSIZE];   // ISIS message/command body

  // command components (command args)

  char cmd[BIG_STR_SIZE];       // command string (oversized)
  char args[BIG_STR_SIZE];      // command-line argument buffer (oversized)
  char reply[BIG_STR_SIZE];     // command reply string

  // other working variables

  int i;
  int nfound=0;
  int icmd=-1;
  int rtn;
  int MsgFromISIS;

  // Some simple initializations

  memset(reply,0,sizeof(reply));
  memset(args,0,sizeof(args));
  memset(cmd,0,sizeof(cmd));
  memset(msg,0,ISIS_MSGSIZE);

  // Split the ISIS format message into components

  rtn = SplitMessage(buf,srcID,destID,&msgtype,msgbody);

  // check destination ID

  if ( strcasecmp(destID,client.ID) && strcasecmp(destID,"AL") ) 
    return;  // if not mine, ignore it.

  strcpy(SourceID, srcID);

  // check source ID & message format in case of ISISclint mode

  //if (client.useISIS) { 
  //  if( strcasecmp(client.isisID,srcID) || client.remPort!=client.isisPort ) 
  //    return;  // if not message from IS, ignore it.
  // changed to below at v1.4.3

  if (client.useISIS && client.remPort==client.isisPort ) {

    MsgFromISIS = 1;  // v1.4.3

    if (rtn<0) {
      if(client.isVerbose) {
        printf("\rISIS IN : Malformed message\n");
        rl_refresh_line(0,0);
      }
      return;
    }

    if(client.isVerbose) {
      printf("\rISIS IN : %s\n",buf);
      rl_refresh_line(0,0);
    }
  }

  // check only message format in case of Standalone mode

  else { 

    MsgFromISIS = 0;  // v1.4.3

    if (rtn<0) {
      if(client.isVerbose) {
        printf("\rREMC IN : Malformed message from %s\n", srcID);
        rl_refresh_line(0,0);
      }
      return;
    }

    if(client.isVerbose) {
      printf("\rREMC IN : %s\n",buf);
      rl_refresh_line(0,0);
    }
  }    

  // Immediate action depends on the type of message received as
  // recorded by the msgtype code.

  switch(msgtype) {

  case STATUS:  // we've been sent a status message, echo to console
    printf("\r%s\n",buf);
    rl_refresh_line(0,0);
    break;
	  
  case DONE:    // command completion message (?), echo to console.
    printf("\r%s\n",buf);
    rl_refresh_line(0,0);
    break;
	  
  case ERROR:   // error messages, echo to console, get fancy later
    REDTEXT;
    printf("\r%s\n",buf);
    TXTRESET;
    rl_refresh_line(0,0);
    break;

  case WARNING:
    CYATEXT;
    printf("\r%s\n",buf);
    TXTRESET;
    rl_refresh_line(0,0);
    break;

  case FATAL:
    MAGTEXT;
    printf("\r%s\n",buf);
    TXTRESET;
    rl_refresh_line(0,0);
    break;
	  
  case REQ:    // implicit command requests
  case EXEC:   // and executive override commands

    sscanf(msgbody,"%s %[^\n]",cmd,args);  // split into command + args

    // traverse the command table, exact case-insensitive match required

    nfound = 0;
    for (i=0; i<NumCommands; i++) {
      if (strcasecmp(cmdtab[i].cmd,cmd)==0) { 
        nfound++;
        icmd=i;
        break;
      }
    }

    if (nfound == 0) {
      sprintf(msg,"%s>%s ERROR: Unknown command - '%s'\n\r",
	          client.ID,srcID,msgbody);
    }
    else {
      SocketCmdFlag = 1;
      switch(cmdtab[icmd].action(args,msgtype,reply)) {

      case CMD_ERR: // command generated an error
        sprintf(msg,"%s>%s ERROR: %s\n\r",client.ID,srcID,reply);
        break;

      case CMD_NOOP: // command is a no-op, debug/verbose output only
        //if (client.isVerbose)
        //  printf("ISIS IN: %s from ISIS node %s\n",msgbody,srcID);
        // ==> there was printf("ISIS IN : %s\n",buf); aleady above
        break;

      case CMD_OK:  // command executed OK, return reply
      default:
        sprintf(msg,"%s>%s DONE: %s\n\r",client.ID,srcID,reply);
        break;
	
      } // end of switch on cmdtab.action()
      SocketCmdFlag = 0;
    }

    // An incoming PING requires special handling - it is an exception
    // to the usual messaging syntax since PONG is sent in reply 

    if (strcasecmp(cmd,"PING") == 0)
      sprintf(msg,"%s>%s %s\r",client.ID,srcID,reply);
      
    break;

  default:  // we don't know what we got, print for debugging purposes

    sprintf(msg,"%s>%s ERROR: Unknown message type\n\r",client.ID,srcID);

    if(client.isVerbose) {
      CYATEXT;    
      if (MsgFromISIS) printf("\rISIS IN : Malformed message type\n");
      else             printf("\rREMC IN : Malformed message type\n");
      TXTRESET;
      rl_refresh_line(0,0);
    }

    break;

  } // end of switch(msgtype) -- default falls through with no-op

  // Do we have something to send back? 
  //
  // If we are configured as an ISIS client (client.useISIS=true), send the
  // reply back to the ISIS server for handling with SendToISISServer().
  //
  // If we are configured as standalone (client.useISIS=false), send the
  // reply back to the remote host with ReplyToRemHost().

  if (strlen(msg)>0) { // we have something to send

    //if (client.useISIS) {
    if (MsgFromISIS) {  // client.useISIS and Msg from ISIS (v1.4.3)
      SendToISISServer(&client,msg);
      if (client.isVerbose) {
        msg[strlen(msg)-1]='\0';
        printf("\rISIS OUT: %s\n",msg);
        rl_refresh_line(0,0);
      }
    }

    else {
      ReplyToRemHost(&client,msg);
      if (client.isVerbose) {
        msg[strlen(msg)-1]='\0';
        printf("\rREMC OUT: %s\n",msg);
        rl_refresh_line(0,0);
      }
    }
  } // end of reply handling

}

//---------------------------------------------------------------------------
//
// SendStatus() - send a STATUS/ERROR message to all nodes in ISIS client mode (v1.4.9?)
//

void
SendStatus(char *statusmsg)
{
  char destID[ISIS_NODESIZE];
  char msg[ISIS_MSGSIZE];
  int rtn;

  if (client.useISIS==0) return;

  strcpy(destID, "AL");

  memset(msg,0,ISIS_MSGSIZE);

  sprintf(msg,"%s>%s %s\r",client.ID, destID, statusmsg);

  rtn = SendToISISServer(&client,msg);
  if (client.isVerbose) {
    msg[strlen(msg)-1]='\0';
    printf("\rISIS OUT: %s\n",msg);
    rl_refresh_line(0,0);
  }

  if (rtn<0) {
    REDTEXT;
    printf("\rERROR: Failed to send a STATUS/ERROR message to ISIS server..\n");
    if (client.isVerbose) printf("       - %s\n",strerror(errno));
    TXTRESET;
    rl_refresh_line(0,0);
  }

}

//---------------------------------------------------------------------------
//---------------------------------------------------------------------------
//
// cmd_xxx() action functions
//
// Add new functions at the end.  To be available, they must be entered
// as "action" members in the Commands struct for this application (see
// commands.h)
//

//
// *** Client COMMANDS BEGIN HERE ***
//

//---------------------------------------------------------------------------
//
// client.quit - allowed only if EXEC from remote hosts (keyboard
//               commands are always EXEC.

int
cmd_quit(char *args, MsgType msgtype, char *reply)
{
  if (msgtype == EXEC) {
    client.KeepGoing=0;
    sprintf(reply,"%s=DISABLED MODE=OFFLINE",client.ID);
  }
  else {
    strcpy(reply,"cannot exec 'quit' command - operation not allowed");
    return CMD_ERR;
  }
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// client.init - (re)initialize the TCS and AUX links
//

int
cmd_init(char *args, MsgType msgtype, char *reply)
{
  if(cmd_tcsinit(args,msgtype,reply)==CMD_ERR) 
    return CMD_ERR;

  strcat(reply, " & ");

  if(cmd_auxinit(args,msgtype,reply+strlen(reply))==CMD_ERR) 
    return CMD_ERR;

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// client.close - close the TCS and AUX links & clear all telemetry data
//

int
cmd_close(char *args, MsgType msgtype, char *reply)
{
  cmd_tcsclose(args, msgtype, reply);
  strcat(reply, " & ");
  cmd_auxclose(args, msgtype, reply+strlen(reply));

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// client.arc - toggle the auto recovery mode for both TCS and AUX links
//
  
int
cmd_arc(char *args, MsgType msgtype, char *reply)
{
  if (tcs.ArcMode) {
    tcs.ArcMode = 0;
    aux.ArcMode = 0;
    sprintf(reply,"TCS & AUX Links Auto Recovery Mode Disabled");
  }
  else {
    tcs.ArcMode = 1;
    aux.ArcMode = 1;
    sprintf(reply,"TCS & AUX Links Auto Recovery Mode Enabled");
  }
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// client.info - return application runtime information
//

int
cmd_info(char *args, MsgType msgtype, char *reply)
{
  int i;

  // start with the application version #, ID, and host info

  sprintf(reply, "KMTNET TCS Agent %s ID=%s Host=%s:%d",
	             agent.AppVersion, client.ID, client.Host, client.Port);

  // if configured as an ISIS client, report this and the ISIS host:port info,
  // otherwise if standalone, report that, and the host:port of the last
  // remote host to send us something, if known.

  if (client.useISIS) {
    sprintf(reply, "%s Mode=ISISClient ISIS=%s ISISHost=%s:%d", reply,
	               client.isisID, client.isisHost, client.isisPort);
  }
  else {
    if (strlen(client.remHost)>0)
      sprintf(reply, "%s Mode=STANDALONE RemHost=%s:%d",reply,
	                 client.remHost, client.remPort);
    else
      strcat(reply," Mode=STANDALONE");
  }

  // Info about the PC-TCS Telcom server

  sprintf(reply, "%s TCSSHost=%s:%d", reply, tcs.Host, tcs.PortNum);
  sprintf(reply, "%s TCSTelID=%s TCSSysID=%s", reply, tcs.TelID, tcs.SysID);

  // Info about the PC-TCS serial link and Telcom tcp link

  switch (tcs.Link) {
  case TCS_UP  : strcat(reply," TCSLink=Up"  );break;
  case TCS_IDLE: strcat(reply," TCSLink=Idle");break;
  default      : strcat(reply," TCSLink=DOWN");break;
  }

  sprintf(reply, "%s TcsArcMode=%s", reply, tcs.ArcMode?"Enabled":"Disabled");

  ///sprintf(reply, "%s PctcsIdleTime=%.1f sec" , reply, tcs.PctcsIdle    );
  sprintf(reply, "%s PctcsTimeout=%d sec"    , reply, tcs.PctcsTimeout );
  ///sprintf(reply, "%s TelcomIdleTime=%.1f sec", reply, tcs.TelcomIdle   );
  sprintf(reply, "%s TelcomTimeout=%d sec"   , reply, tcs.TelcomTimeout);
  sprintf(reply, "%s TcsUpdateInt=%.1f sec"  , reply, tcs.UpdateInt    );

  // Report TCS HW setting

  sprintf(reply, "%s TcsGuideStepRA=%.8f arcsec/encount", reply, tcs.GuideStepRA);
  sprintf(reply, "%s TcsGuideStepDec=%.8f arcsec/encount", reply, tcs.GuideStepDec);
  sprintf(reply, "%s TcsGuideMinOffsetRA=%.2f arcsec", reply, tcs.GuideMinOffRA);
  sprintf(reply, "%s TcsGuideMinOffsetDec=%.2f arcsec", reply, tcs.GuideMinOffDec);

  // Info about the AUX control server

  sprintf(reply, "%s AUXHost=%s:%d"          , reply, aux.Host, aux.PortNum);
  sprintf(reply, "%s AUXTelID=%s AUXSysID=%s", reply, aux.TelID, aux.SysID );
  sprintf(reply, "%s FitsTelID=%s"           , reply, aux.FitsTelID        );

  // Info about the AUX server tcp link

  switch (aux.Link) {
  case AUX_UP  : strcat(reply, " AUXLink=Up"  );break;
  //case AUX_IDLE: strcat(reply, " AUXLink=Idle");break;
  default      : strcat(reply, " AUXLink=DOWN");break;
  }

  sprintf(reply, "%s AuxArcMode=%s", reply, aux.ArcMode?"Enabled":"Disabled");

  sprintf(reply, "%s AuxUpdateInt=%.1f sec"  , reply, aux.UpdateInt);

  // Report AUX HW setting

  sprintf(reply, "%s AuxFilterOpTime=%.1f sec"  , reply, aux.FS_FilterOpTime);
  sprintf(reply, "%s AuxShutOpTime=%.1f sec"  , reply, aux.FS_ShutOpTime);

  sprintf(reply, "%s AuxFAnSouth=%d AuxFAnEast=%d AuxFAnWest=%d", reply,
                      aux.FA_ActNums[SOUTH], aux.FA_ActNums[EAST], aux.FA_ActNums[WEST]);

  // Report links auto reocvery mode setting

  sprintf(reply, "%s ArcInt=%.1f", reply, agent.ArcInt);

  // Report application runtime flags

  sprintf(reply, "%s %s %s %s", reply,
                 (client.isVerbose ? "Verbose" : "Concise"),
                 (client.Debug     ? "+DEBUG"  : "-DEBUG" ),
                 (client.doLogging ? "+DOLOG"  : "-DOLOG" )  );
	 
  // Finally, report the application's runtime config file

  sprintf(reply, "%s rcfile=%s exe=%s UserID=%s Start=%s", reply, 
                 client.rcFile, agent.exeFile, agent.UserID, agent.StartTime);

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// client.version - report application version and compilation info
//

int
cmd_version(char *args, MsgType msgtype, char *reply)
{
  
  sprintf(reply, "KMTNet TCS Agent Version=(%s) CompileDate=%s CompileTime=%s",
                 agent.AppVersion, APP_COMPDATE, APP_COMPTIME);
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// client.verbose - toggle enable verbose console output
//
  
int
cmd_verbose(char *args, MsgType msgtype, char *reply)
{
  if (client.isVerbose) {
    client.isVerbose = 0;
    sprintf(reply,"verbose mode disabled");
  }
  else {
    client.isVerbose = 1;
    sprintf(reply,"verbose mode enabled");
  }
  return CMD_OK;
}

//---------------------------------------------------------------------------
// 
// client.debug - toggle debugging output
//

int
cmd_debug(char *args, MsgType msgtype, char *reply)
{
  if (client.Debug) {
    client.Debug = 0;
    sprintf(reply,"debugging output disabled");
  }
  else {
    client.Debug = 1;
    sprintf(reply,"debugging output enabled");
  }
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// client.history - show the history list
//
// Uses the Gnu history() and readline() mechanism, shows a unix-like
// command history.  For obvious reasons, we only run this if we
// are an EXEC: (i.e., keyboard) command.
//

int
cmd_history(char *args, MsgType msgtype, char *reply)
{
  register HIST_ENTRY **the_list;
  register int ihist;

  if (msgtype == EXEC) {
    the_list = history_list();
    if (the_list) {
      for (ihist=0; the_list[ihist]; ihist++) 
      printf("%5d   %s\n",ihist+history_base,the_list[ihist]->line);
    }
    return CMD_NOOP;
  }

  // can't do history unless you're on the console...

  strcpy(reply, "cannot exec 'history' command - remote operation not allowed");
  return CMD_ERR;

}

//---------------------------------------------------------------------------
//
// client.help - quick list of available commands
//

int
cmd_help(char *args, MsgType msgtype, char *reply)
{
  if (msgtype==EXEC) {
    printf("\n              <<KMTNet TCS Agent interactive commands>>\n");
    printf("______________________________________________________________________\n");
    printf("Client commands:\n");
    printf("   quit         - quit TCS Agent application\n");
    printf("   init         - initialize both TCS & AUX links\n");
    printf("   reset        - reset/restart both TCS & AUX links\n");
    printf("   close        - close both TCS & AUX links\n");
    printf("   arc          - toggle AutoRecovery mode for both TCS & AUX links\n");
    printf("   info         - report client information\n");
    printf("   version      - report client version & compile info\n");
    printf("   verbose      - toggle verbose output mode\n");
    printf("   debug        - toggle debugging output\n");
    printf("   history      - show command history\n");
    printf("   !!           - repeat last command\n");
    printf("   !cmd         - repeat last command matching 'cmd'\n");
    printf("   help or ?    - view this TCS Agent commands list\n");
    printf("______________________________________________________________________\n");
    printf("TCS (PC-TCS Telcom) commands:\n");
    printf("   tcsinit      - initialize PC-TCS Telcom link\n");
    printf("   tcsreset     - reset/restart PC-TCS Telcom link\n");
    printf("   tcsclose     - close PC-TCS Telcom link\n");
    printf("   tcsarc       - toggle AutoRecovery mode for TCS link\n");
    printf("   tcsstatus    - query & return TCS status with the telemetry data\n");
    printf("   tstat        - query & return raw TCS status without keywords\n");
    printf("   traw         - return lastest raw PC-TCS telemetry packet string\n");
    printf("   tsync        - synch PC-TCS clock with the system UTC clock\n");
    printf("   tcmd         - send a raw PC-TCS command, arg: <tcmd>\n");
    printf("   treq         - send a raw PC-TCS request, arg: <treq>\n");
    printf("   tguide       - guiding offset move, args: <ra_offset> <dec_offset>\n");
    printf("   tgoto        - goto J2000 RA/Dec, args: <ra> <dec>\n");
    printf("   toffset      - offset move RA/Dec, args: <ra_offset> <dec_offset>\n");
    printf("   tstop        - cancel command and stop telescope for commanded motions\n");
    printf("   tdi          - synch the current posidtion with the commanded position\n");
    printf("______________________________________________________________________\n");
    printf("AUX control commands:\n");
    printf("   auxinit      - initialize AUX control link\n");
    printf("   auxreset     - reset/restart AUX control link\n");
    printf("   auxclose     - close AUX control link\n");
    printf("   auxarc       - toggle the auto recovery mode for AUX link\n");
    printf("   auxstatus    - query & return AUX status with the telemetry data\n");
    printf("   astat        - query & return raw AUX status without keywords\n");
    printf("   acmd         - send a raw AUX control remote command, arg: <acmd>\n");
    printf("   filter       - change filters to arg # or name, arg: <fnum/fname>\n");
    printf("   filname      - query & return the filter names for 4 slides\n");
    printf("   fsastat      - query & return AUX Filter/Shutter status\n");
    printf("   dfocus       - adjust the focus position of PFI, arg: <dfoc>\n");
    printf("   dtilt        - adjust the tip-tilt angle of PFI, arg: <dtns> <dtew>\n");
    printf("   dtiltp       - adjust the tip-tilt angle of PFI, arg: <theta> <dtilt>\n");
    printf("   fttgoto      - goto abs focus & tip-tilt, arg: <foc> (<tns> <tew>)\n");
    printf("   fttgotop     - goto abs focus & tip-tilt, arg: <foc> (<theta> <tilt>)\n");
    printf("   fttstat      - query & return AUX Focuser/Tip-Tilt/Limit/Position(S/E/W)\n");
    printf("\n");

    return CMD_NOOP;
  }

  // Can't use HELP unless you're on the console...

  strcpy(reply, "cannot exec help command - remote operation not allowed");
  return CMD_ERR;

}

//---------------------------------------------------------------------------
//
// client.ping - communication handshaking request
//
// If we are PINGed, we have to PONG back to the sender.  This is a
// little bit silly in keyboard command mode, but at least we can
// debug our ping handler.  
//
// PINGs are actually handled separately in the SocketCommand() handler
// (nothing is done by the KeyboardCommand() handler) because the
// PONG sent back acknowledging the comm handshaking request is, in
// effect, a pseudo-command (implicit REQ:), not a "DONE:" response
// to a command request.  This exception to the general messaging
// syntax has to be handled carefully to prevent problems, especially
// with older ICIMACS apps.
//

int
cmd_ping(char *args, MsgType msgtype, char *reply)
{
  strcpy(reply,"PONG");
  return CMD_OK;
}


//---------------------------------------------------------------------------
//
// client.pong - communication handshaking acknowledge
//
// For historical reasons, a "PONG" sent in acknowledgment of a software
// handshaking "PING" looks like an implicit REQ:, and hence like a
// "command request" for the recipient.  It isn't.  It is, however, an
// exception to the strict messaging protocol, which is why it needs a
// handler.
//
// We don't do anything here but return a CMD_NOOP (since this "command"
// must not result in a reply back to the sender).  In more
// sophisticated apps, we might actually use receipt of a pong to do
// something useful (e.g., help build up a node table).
//

int
cmd_pong(char *args, MsgType msgtype, char *reply)
{
  //if (client.isVerbose) {  // v1.4.3
    printf("\rPONG received from %s\n", SourceID);
    rl_refresh_line(0,0);
  //}
  return CMD_NOOP;
}

//
// *** PC-TCS COMMANDS BEGIN HERE ***
//

//---------------------------------------------------------------------------
//
// tcs.tcsinit - (re)initialize the PC-TCS serial communications link
//
// Initializes the PCTCS link.  Calls InitPCTCS() to do the dirty work.
//

int
cmd_tcsinit(char *args, MsgType msgtype, char *reply)
{
  char errmsg[MED_STR_SIZE];

  // TCS connection and initionalization
  if (InitPCTCS(&tcs,reply)<0)     
    return CMD_ERR;

  // Set the input epoch of PC-TCS to 2000
  //     Revised at v1.2, to set the input epoch to 2000 automatically
  //     and also to remove the procedure of manual setting on PC-TCS.
  if (TcsSetEpoch(&tcs, errmsg)<0) {
    sprintf(reply, "%s, but %s", reply, errmsg);
    return CMD_ERR;
  }

  if(SocketCmdFlag) {
    GRNTEXT;
    printf("\rSTATUS: PC-TCS Telcom Link Initialized at a request from ISIS\n");
    TXTRESET;
    rl_refresh_line(0,0);
  }
  else {
    GRNTEXT;  // TXTRESET in KeyboardCommand()
  }

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// tcs.tcsclose - close the TCS (PC-TCS & Telcom) link
//
// Simply closes the tcp socket for Telcom server & clear TCS telemetry data
// and sets the TCS link to TCS_DOWN
//

int
cmd_tcsclose(char *args, MsgType msgtype, char *reply)
{
  ClearPCTCS(&tcs);
  strcpy(reply, "PC-TCS Telcom Link closed");

  if(SocketCmdFlag) {
    REDTEXT;
    printf("\rSTATUS: PC-TCS Telcom Link closed at a request from ISIS\n");
    TXTRESET;
    rl_refresh_line(0,0);
  }
  else {
    REDTEXT;  // TXTRESET in KeyboardCommand()
  }

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// tcs.tcsarc - toggle the auto recovery mode for PC-TCS link
//
// If Enabled, TCS Agent will try to connect to Telcom server and to recover
// TCS link and PC-TCS link in an interval of ArcInt (auto recovery interval)
//
  
int
cmd_tcsarc(char *args, MsgType msgtype, char *reply)
{
  if (tcs.ArcMode) {
    tcs.ArcMode = 0;
    sprintf(reply,"TCSLink Auto Recovery Mode Disabled");
  }
  else {
    tcs.ArcMode = 1;
    sprintf(reply,"TCSLink Auto Recovery Mode Enabled");
  }
  return CMD_OK;
}

//--------------------------------------------------------------------------
//
// tcs.tcstatus - return TCS status info as a valid IMPv2 message string
//
// relies on the last telemetry received, or just the time/date info and
// ARC mode, if the TCS link is down or idle too long.  Note that this is 
// usually within 20msec of the query, so the lag is small.
//

int
cmd_tcsstatus(char *args, MsgType msgtype, char *reply)
{
  float secz, alt, az;
  char curdate[16], curtime[16];
  systime_t curutc;

  // set obs date & time with current system clock

  GetUTCDateTime(&curutc);
  sprintf(curdate, "%04d-%02d-%02d", curutc.year, curutc.month, curutc.day);
  sprintf(curtime, "%02d:%02d:%06.3f", curutc.hour, curutc.min, curutc.sec);

  switch (tcs.Link) {

  case TCS_UP:
    secz = atof(tcs.SecZ);
    alt = atof(tcs.Alt);
    az = atof(tcs.Az);

    sprintf(reply, "TCSSTATUS TCSQDATE=%sT%s TIMESYS=UTC TCSLINK=Up TCSARC=%s"
                   " TCSUDATE=%sT%s RA=%s DEC=%s EQUINOX=%s HA=%s"
                   " ST=%s SECZ=%.2f ALT=%.1f AZ=%.1f",
                   curdate, curtime, tcs.ArcMode?"Enabled":"Disabled",
                   tcs.Date, tcs.UTC, tcs.RA, tcs.Dec, tcs.Equinox, tcs.HA,
                   tcs.LST, secz, alt, az);

    switch (tcs.MoveStatus) {
    case 0:
      strcat(reply," TELMOVE=Idle");
      break;
    case 1: 
      strcat(reply," TELMOVE=RA");
      break;
    case 2:
      strcat(reply," TELMOVE=Dec");
      break;
    case 3:
      strcat(reply," TELMOVE=RA+Dec");
      break;
    default:
      strcat(reply," TELMOVE=Unknown");
      break;
    }

    //if (tcs.RALimit)
    //  strcat(reply," TCSLIMIT=RA");
    //else if (tcs.DecLimit)
    //  strcat(reply," TCSLIMIT=Dec");
    //else if (tcs.HorizonLimit)
    //  strcat(reply," TCSLIMIT=Horizon");
    //else 
    //  strcat(reply," TCSLIMIT=No");

    // v1.4.1
    switch (tcs.LimitStatus) {
    case 0: 
      strcat(reply," TCSLIMIT=No");
      break;
    case 1: 
      strcat(reply," TCSLIMIT=RA");
      break;
    case 2:
      strcat(reply," TCSLIMIT=Dec");
      break;
    case 3:
      strcat(reply," TCSLIMIT=Horizon");
      break;
    default:
      strcat(reply," TCSLIMIT=Unknown");
      break;
    }

    sprintf(reply, "%s TCSDRIVE=%s EXECODE=%c", reply, 
                   tcs.DriveDisable?"Disabled":"Enabled", tcs.ExeCode);

    break;

  case TCS_IDLE:
    sprintf(reply, "TCSSTATUS TCSQDATE=%sT%s TIMESYS=UTC TCSLINK=Idle TCSARC=%s", 
                   curdate, curtime, tcs.ArcMode?"Enabled":"Disabled");
    break;

  default:
    sprintf(reply, "TCSSTATUS TCSQDATE=%sT%s TIMESYS=UTC TCSLINK=Down TCSARC=%s",
                   curdate, curtime, tcs.ArcMode?"Enabled":"Disabled");
    break;

  }

  return CMD_OK;

}

//--------------------------------------------------------------------------
//
// tcs.tstat - return TCS status info in lightweight (non-IMPv2 format)
//
// Like cmd_tcstatus, it relies on the last telemetry received, or just
// the time/date info if the TCS link is down or idle too long.  The lag
// is usually no more than 20msec from the receipt of the request.
//
// Returns a lightweight status string in simple, non-IMPv2 compilant format
// for simple reading/parsing by machines not humans.  The format is
// as follows, depending on the TCS link state:
//
// TCS_UP: PC-TCS link active
//    UP TCSARC TCSQDATE TIMESYS TCSUDATE RA DEC EQUINOX HA 
//     ST SECZ ALT AZ TELMOVE TCSLIMIT TCSDRIVE EXECODE
//
// TCS_IDLE: PC-TCS link has been idle for longer than the allowed time
//    IDLE TCSARC TCSQDATE TIMESYS
//
// TCS_DOWN: PC-TCS link is disabled ("down")
//    DOWN TCSARC TCSQDATE TIMESYS
//
// Time system for Time/Date in all cases is UTC.  In the Idle/Down cases,
// the time/date returned are from the system time clock, which hopefully is
// reasonable synchronized with a real time server.
//
//   TCSARC   : TCS Link Auto recovery mode - 0:Disabled / 1:Enabled
//   TCSQDATE : query time, recorded when this function is called
//   TCSUDATE : updated time, recorded when the telemetry data packet was received
//   TELMOVE  : RA/DEC move status - 0:no / 1:RA / 2:Dec / 3: Both moving / -1:Unknown
//   TCSLIMIT : TCS Limit status - 0:no(normal) / 1:RA / 2:Dec / 3:Horizon / -1:Unknown
//   TCSDRIVE : TCS Drive status - 0:Enabled(normal) / 1:Disabled / -1:Unknown
//   EXECODE  : '0' / 'e' / 'E' / '3', if cmd was executed successfully, changed e/E
//

int
cmd_tstat(char *args, MsgType msgtype, char *reply)
{
  char curdate[16], curtime[16];
  systime_t curutc;
 
  GetUTCDateTime(&curutc);
  sprintf(curdate, "%04d-%02d-%02d", curutc.year, curutc.month, curutc.day);
  sprintf(curtime, "%02d:%02d:%06.3f", curutc.hour, curutc.min, curutc.sec);

  switch (tcs.Link) {

  case TCS_UP:
    sprintf(reply, "UP %d %sT%s UTC %sT%s %s %s %s %s %s %s %s %s %2d %2d %2d %c",
                   tcs.ArcMode, curdate, curtime, tcs.Date, tcs.UTC, tcs.RA, tcs.Dec,
                   tcs.Equinox, tcs.HA, tcs.LST, tcs.SecZ, tcs.Alt, tcs.Az, 
                   tcs.MoveStatus, tcs.LimitStatus, tcs.DriveDisable, tcs.ExeCode);
    break;

  case TCS_IDLE:
    sprintf(reply, "IDLE %d %sT%s UTC", tcs.ArcMode, curdate, curtime);
    break;

  default:
    sprintf(reply, "DOWN %d %sT%s UTC", tcs.ArcMode, curdate, curtime);
    break;

  }

  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tcs.traw - return raw string of the telemetry data packet
//

int
cmd_traw(char *args, MsgType msgtype, char *reply)
{
  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, telemetry unavailable");
    return CMD_ERR;
  }

  // copy raw packet string to reply buffer

  strcpy(reply, tcs.RawPack);

  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tcs.tcmd - send a PC-TCS remote command defined in COMSOFT Native Portocol
//

int
cmd_tcmd(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[CMDBUFLEN];  // command buffer
  char argbuf[ARGBUFLEN];
  int rtn, nsent, cmdlen, argnum;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check update flag

  if (!tcs.UpdateFlag) {
    //strcpy(reply, "too frequent command to Telcom, execution code is not updated yet");
    rtn = TcsTelemetry(&tcs, reply);  // v1.2.2
    if(rtn!=CMD_OK) return CMD_ERR;
  }

  // also need something to send

  if (strlen(args)<=0) {
    strcpy(reply, "usage: tcmd <tcmd>");
    strcat(reply, "  /  <tcmd>: PC-TCS command keywords");
    strcat(reply, ", defined in COMSOFT Native Protocol");
    return CMD_ERR;
  }

  //if(strncasecmp(args,"REQUEST",7)==0 && strlen(args)<10) {
  //  strcpy(reply, "usage: tcmd request <keyword>");
  //  strcat(reply, "  /  <keyword>: PC-TCS Request Keyword");
  //  strcat(reply, " defined in COMSOFT Native Protocol");
  //  return CMD_ERR;
  //}
  // --> removed for Skip's UI protocol (v1.3.0)

  // Assume the command is the argument buffer, we won't try to
  // validate command syntax.

  memset(tcscmd, 0, CMDBUFLEN);
  //cmdlen = sprintf(tcscmd, "%s %s %03d %s\n",
  cmdlen = sprintf(tcscmd, "%s %s %03d COMMAND %s\n",  // v1.3.0
                            tcs.TelID, tcs.SysID, PID_REQCMD, strupr(args));

  // send the command to Telcom via tcp link

  nsent = send(tcs.FDcmd, tcscmd, cmdlen, 0);
  if (nsent < cmdlen) {
    sprintf(reply, "command send failed - tcmd='%s' cmdlen=%d, sentbyte=%d", 
                   args, cmdlen, nsent);
    return CMD_ERR;
  }

  if(client.isVerbose) {
    printf("\r TCS OUT: %s", tcscmd);
    //rl_refresh_line(0,0);
  }

  // receive the response of command

  memset(tcscmd, 0, CMDBUFLEN);
  cmdlen = recv(tcs.FDcmd, tcscmd, CMDBUFLEN-1, 0);
  if(cmdlen<=0) {
    sprintf(reply, "response recv failed - recvbyte = %d", cmdlen);
    return CMD_ERR;
  }
  tcscmd[cmdlen] = NULL;
  if(client.isVerbose) {
    printf("\r TCS IN : %s", tcscmd);
    //rl_refresh_line(0,0);
  }

  tcs.UpdateFlag = 0;

  memset(argbuf, 0, ARGBUFLEN);
  argnum = sscanf(tcscmd, "%*s %*s %*s %[^\n]", argbuf);
  if(argnum!=1) {
    sprintf(reply, "unrecognized response - scaned argnum = %d", argnum);
    return CMD_ERR;
  }

  if(strcasecmp(argbuf,"BAD")==0) {
    sprintf(reply, "command execution failed with 'BAD' response");
    return CMD_ERR;
  }

  //if(strncasecmp(args,"REQUEST",7)==0) {
  //  //sprintf(reply, "TCS %s = %s", args+8, argbuf);
  //  sprintf(reply, "TREQ %s %s", args, argbuf);  //v1.3.0
  //  return CMD_OK;
  //}
  // --> removed, REQUEST only used with TREQ/cmd_treq() (v1.3.1)

  if(strcasecmp(argbuf,"OK")) {
    strcpy(reply, "unrecognized response - neither 'OK' nor 'BAD'");
    return CMD_ERR;
  }

  // all done

  sprintf(reply, "TCMD %s OK", args);
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tcs.treq - send a PC-TCS remote request defined in COMSOFT Native Portocol,
//            added for Skip's UI
//

int
cmd_treq(char *args, MsgType msgtype, char *reply)    // v1.3.0
{
  char tcscmd[CMDBUFLEN];  // command buffer
  char argbuf[ARGBUFLEN];
  int rtn, nsent, cmdlen, argnum;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // also need something to send

  if (strlen(args)<=0) {
    strcpy(reply, "usage: treq <treq>");
    strcat(reply, "  /  <treq>: PC-TCS request keywords");
    strcat(reply, ", defined in COMSOFT Native Protocol");
    return CMD_ERR;
  }

  // Assume the command is the argument buffer, we won't try to
  // validate command syntax.

  memset(tcscmd, 0, CMDBUFLEN);
  cmdlen = sprintf(tcscmd, "%s %s %03d REQUEST %s\n", 
                            tcs.TelID, tcs.SysID, PID_REQCMD, strupr(args));

  // send the command to Telcom via tcp link

  nsent = send(tcs.FDcmd, tcscmd, cmdlen, 0);
  if (nsent < cmdlen) {
    sprintf(reply, "request send failed - treq='%s' reqlen=%d, sentbyte=%d", 
                   args, cmdlen, nsent);
    return CMD_ERR;
  }

  if(client.isVerbose) {
    printf("\r TCS OUT: %s", tcscmd);
    //rl_refresh_line(0,0);
  }

  // receive the response of command

  memset(tcscmd, 0, CMDBUFLEN);
  cmdlen = recv(tcs.FDcmd, tcscmd, CMDBUFLEN-1, 0);
  if(cmdlen<=0) {
    sprintf(reply, "response recv failed - recvbyte = %d", cmdlen);
    return CMD_ERR;
  }
  tcscmd[cmdlen] = NULL;
  if(client.isVerbose) {
    printf("\r TCS IN : %s", tcscmd);
    //rl_refresh_line(0,0);
  }

  memset(argbuf, 0, ARGBUFLEN);
  argnum = sscanf(tcscmd, "%*s %*s %*s %[^\n]", argbuf);
  if(argnum!=1) {
    sprintf(reply, "unrecognized response - scaned argnum = %d", argnum);
    return CMD_ERR;
  }

  if(strcasecmp(argbuf,"BAD")==0) {
    sprintf(reply, "command execution failed with 'BAD' response");
    return CMD_ERR;
  }

  // all done

  if( strncasecmp(args,"RA",2)==0 || strncasecmp(args,"NEXTRA" ,6)==0 )  // v1.3.0, v1.3.1
    sprintf(reply, "TREQ %s %c%c:%c%c:%s", 
                   args, argbuf[0], argbuf[1], argbuf[2], argbuf[3], argbuf+4);
  else if( strncasecmp(args,"DEC",3)==0 || strncasecmp(args,"NEXTDEC" ,7)==0 )
    sprintf(reply, "TREQ %s %c%c%c:%c%c:%s", 
                   args, argbuf[0], argbuf[1], argbuf[2], argbuf[3], argbuf[4], argbuf+5);
  else 
    sprintf(reply, "TREQ %s %s", args, argbuf);

  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tcs.tsync - synch the PC-TCS clock with the local system clock,
//             allowed only if EXEC
//
// NOTE: User must check the UT date will not change soon before using this cmd
// If the time is pass on 24:00 in progress, the date will be not correct since 
// time-sync command and date-sync command are sperated and there is some delay 
// in the process.
//

int
cmd_tsync(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[128];  // command buffer
  int rtn;
  systime_t tctime;

  // check command type (EXEC only allowed)

  if (msgtype != EXEC) {
    strcpy(reply, "cannot exec 'tsync' command - remote operation not allowed");
    return CMD_ERR;
  }

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // Get the system date now (user have to check the date will not change soon)

  GetUTCDateTime(&tctime);

  // Build the SETDATE command string

  memset(tcscmd,0,sizeof(tcscmd));
  sprintf(tcscmd, "SETDATE %.2d/%.2d/%.4d", tctime.month, tctime.day, tctime.year);

  // Execute the command for setting the date on PC-TCS

  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // Execution code update between SETDATE and SETTIME commands

  rtn = TcsTelemetry(&tcs, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // Get the system time now (user have to check the time is not pass on 24:00)

  GetUTCDateTime(&tctime);

  // Build the SETTIME command string

  memset(tcscmd,0,sizeof(tcscmd));
  sprintf(tcscmd, "SETTIME %.2d%.2d%05.2f", tctime.hour, tctime.min, tctime.sec);

  // Execute the command for setting the time on PC-TCS

  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  strcpy(reply, "synched PC-TCS with the local host UTC clock");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tcs.tguide - move the telescope as guiding offset RA/Dec in arcsec
//

int
cmd_tguide(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[128];  // command buffer
  int rtn, step;
  int raop, decop;
  double ra_offset, dec_offset;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // Check argument number

  rtn = sscanf(args, "%lf %lf", &ra_offset, &dec_offset);

  if(rtn<2) {
    strcpy(reply, "usage: tguide <RA_offset> <Dec_offset>");
    strcat(reply, "  /  <RA_offset>: +x.xx  <Dec_offset>: +x.xx (in arcsec)");
    return CMD_ERR;
  }

  // Check RA offset value and set operation flag

  if( fabs(ra_offset) > MAX_GUIDEOFFSET_RA ) {
    sprintf(reply, "<RA offset> value is out of range (Max. %.3f asec)",
                    MAX_GUIDEOFFSET_RA);
    return CMD_ERR;
  }
  else if( fabs(ra_offset) < tcs.GuideMinOffRA ) 
    raop = 0;  // don't move RA
  else 
    raop = 1;  // move RA

  // Check Dec offset value and set operation flag

  if( fabs(dec_offset) > MAX_GUIDEOFFSET_DEC ) {
    sprintf(reply, "<Dec offset> value is out of range (Max. %.3f asec)", 
                    MAX_GUIDEOFFSET_DEC);
    return CMD_ERR;
  }
  else if( fabs(dec_offset) < tcs.GuideMinOffDec ) 
    decop = 0;  // don't move Dec
  else
    decop = 1;  // move Dec

  // Execute RA guide-offset move

  if(raop) {

    // convert RA offset(arcsec) to PC-TCS guide step(encoder count)

    step = (int)(ra_offset/tcs.GuideStepRA/cos(tcs.dDec*DEG2RAD)+0.5);
    // step is not in angular distance, so apply cos(DEC) at v1.2.3

    // build the STEPRA command string

    memset(tcscmd, 0, sizeof(tcscmd));
    sprintf(tcscmd, "STEPRA %+d", step);

    // send the command

    rtn = cmd_tcmd(tcscmd, EXEC, reply);
    if(rtn!=CMD_OK) return CMD_ERR;

  }

  // Execution code update between RA and Dec commands

  if( raop && decop ) {  // if both RA and Dec is operated

    rtn = TcsTelemetry(&tcs, reply);
    if(rtn!=CMD_OK) return CMD_ERR;

  }

  // Execute Dec guide-offset move

  if(decop) {

    // convert Dec offset(arcsec) to PC-TCS guide step(encoder count)

    step = (int)(dec_offset/tcs.GuideStepDec+0.5);

    // build the STEPDEC command string

    memset(tcscmd, 0, sizeof(tcscmd));
    sprintf(tcscmd, "STEPDEC %+d", step);

    // send the command

    rtn = cmd_tcmd(tcscmd, EXEC, reply);
    if(rtn!=CMD_OK) return CMD_ERR;

  }

  // all done

  strcpy(reply, "guiding offset move commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tcs.tgoto - goto to J2000 RA/Dec, arg format: hh:mm:ss.s dd:mm:ss.s
//
// NOTE: Input Epoch must be set to J2000 manually on PC-TCS before this command (v1.1)
//       --> Revised, Automatically set to 2000 in cmd_tcsinit(), 
//           So manual setting is not necessary now (v1.2.0)
//

int
cmd_tgoto(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[128];  // command buffer
  char ra[16], dec[16];
  int rtn;
  int hour, deg, min;
  double sec;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%s %s", &ra, &dec);

  if(rtn<2) {
    strcpy(reply, "usage: tgoto <RA> <Dec>");
    strcat(reply, "  /  <RA>: hh:mm:ss.sss  <Dec>: +dd:mm:ss.ss (J2000)");
    return CMD_ERR;
  }

  // check RA string and values & convert to PC-TCS format

  rtn = sscanf(ra, "%d%*c%d%*c%lf", &hour, &min, &sec);

  if(rtn<3) {
    sprintf(reply, "<RA> is '%s' unrecognized", ra);
    return CMD_ERR;
  }

  if( hour<0 || hour>=24 || min<0 || min>=60 || sec<0.0 || sec>=60.0 ) {
    sprintf(reply, "<RA> value is out of range - '%s'", ra);
    return CMD_ERR;
  }

  sprintf(ra, "%+03d%02d%06.3f", hour, min, sec);

  // check Dec string and values & convert to PC-TCS format

  rtn = sscanf(dec, "%d%*c%d%*c%lf", &deg, &min, &sec);

  if(rtn<3) {
    sprintf(reply, "<Dec> is '%s' unrecognized", dec);
    return CMD_ERR;
  }

  if( deg<-90 || deg>90 || min<0 || min>=60 || sec<0.0 || sec>=60.0 ) {
    sprintf(reply, "<Dec> value is out of range - '%s'", dec);
    return CMD_ERR;
  }

  sprintf(dec, "%+03d%02d%05.2f", deg, min, sec);

  /*
  // set the input coordinate epoch in PC-TCS

  sprintf(tcscmd, "EPOCH 2000.000");
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // execution code update between commands

  rtn = TcsTelemetry(&tcs, reply);
  if(rtn!=CMD_OK) return CMD_ERR;
  */
  // --> Input Epoch must be set to 2000 manually on PC-TCS before this command (v1.1)
  // --> Revised, Automatically set to 2000 in cmd_tcsinit(), 
  //     So manual setting is not necessary now (v1.2.0)

  // set the RA Next position in PC-TCS

  sprintf(tcscmd, "NEXTRA %s", ra);
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // execution code update between commands

  rtn = TcsTelemetry(&tcs, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // set the Dec Next position in PC-TCS

  sprintf(tcscmd, "NEXTDEC %s", dec);
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // execution code update between commands

  rtn = TcsTelemetry(&tcs, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // send a command to move to Next position

  sprintf(tcscmd, "MOVNEXT");
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  strcpy(reply, "goto RA/Dec commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tcs.toffset - move as offset RA/Dec, arg format: +hh:mm:ss.s +dd:mm:ss.s
//

int
cmd_toffset(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[128];  // command buffer
  char ra[16], dec[16];
  int rtn;
  int hour, deg, min;
  double sec;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%s %s", &ra, &dec);

  if(rtn<2) {
    strcpy(reply, "usage: toffset <RA_offset> <Dec_offset>");
    strcat(reply, "  /  <RA_offset>: +hh:mm:ss.ss  <Dec_offset>: +dd:mm:ss.s");
    return CMD_ERR;
  }

  // check RA offset string and values & convert to PC-TCS format

  rtn = sscanf(ra, "%d%*c%d%*c%lf", &hour, &min, &sec);

  if(rtn<3) {
    sprintf(reply, "<RA offset> is '%s' unrecognized, <RA_offset>: +hh:mm:ss.ss", ra);
    return CMD_ERR;
  }

  if( abs(hour)>=MAX_OFFSETMOVE_RA || min<0 || min>=60 || sec<0.0 || sec>=60.0 ) {
    sprintf(reply, "<RA offset> value is out of range - '%s'", ra);
    return CMD_ERR;
  }

  sprintf(ra, "%+03d%02d%05.2f", hour, min, sec);

  // check Dec offset string and values & convert to PC-TCS format

  rtn = sscanf(dec, "%d%*c%d%*c%lf", &deg, &min, &sec);

  if(rtn<3) {
    sprintf(reply, "<Dec offset> is '%s' unrecognized, <Dec_offset>: +dd:mm:ss.s", dec);
    return CMD_ERR;
  }

  if( abs(deg)>=MAX_OFFSETMOVE_DEC || min<0 || min>=60 || sec<0.0 || sec>=60.0 ) {
    sprintf(reply, "<Dec offset> value is out of range - '%s'", dec);
    return CMD_ERR;
  }

  sprintf(dec, "%+03d%02d%04.1f", deg, min, sec);

  // set the RA Offset component in PC-TCS

  sprintf(tcscmd, "OFFRA %s", ra);
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // execution code update between commands

  rtn = TcsTelemetry(&tcs, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // set the Dec Offset component in PC-TCS

  sprintf(tcscmd, "OFFDEC %s", dec);
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // execution code update between commands

  rtn = TcsTelemetry(&tcs, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // command move as Offset RA/Dec

  sprintf(tcscmd, "MOVOFF");
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  strcpy(reply, "offset move commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tcs.tstop - command cancel - stop all commanded motions
//

int
cmd_tstop(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[128];  // command buffer
  int rtn;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // command Cancel slew with full ramp down

  sprintf(tcscmd, "CANCEL");
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  strcpy(reply, "stop commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tcs.tdi - command DECLAREINIT: Synchronizes the telescope by forcing 
//           the current position to become the same as the commanded position.
//

int
cmd_tdi(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[128];  // command buffer
  int rtn;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // command Cancel slew with full ramp down

  sprintf(tcscmd, "DECLAREINIT");
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  strcpy(reply, "DECLAREINIT commanded");
  return CMD_OK;

}

//
// *** AUX CTRL COMMANDS BEGIN HERE ***
//

//---------------------------------------------------------------------------
//
// aux.auxinit - (re)initialize the AUX control link
//
// Initializes the AUX link.  Calls InitAUX() to do the dirty work.
//

int
cmd_auxinit(char *args, MsgType msgtype, char *reply)
{
  if (InitAUX(&aux,reply)<0)     
    return CMD_ERR;

  if(SocketCmdFlag) {
    GRNTEXT;
    printf("\rSTATUS: AUX Link Initialized at a request from ISIS\n");
    TXTRESET;
    rl_refresh_line(0,0);
  }
  else {
    GRNTEXT;  // TXTRESET in KeyboardCommand()
  }

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// aux.auxclose - close the AUX link
//
// Simply closes the serial port and sets tcsLink flag to AUX_DOWN
//

int
cmd_auxclose(char *args, MsgType msgtype, char *reply)
{
  ClearAUX(&aux);
  strcpy(reply, "AUX Link closed");

  if(SocketCmdFlag) {
    REDTEXT;
    printf("\rSTATUS: AUX Link closed at a request from ISIS\n");
    TXTRESET;
    rl_refresh_line(0,0);
  }
  else {
    REDTEXT;  // TXTRESET in KeyboardCommand()
  }

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// aux.auxarc - toggle the auto recovery mode for AUX link
//
// If Enabled, TCS Agent will try to connect to AUX control remote server 
// and to recover AUX link at an interval of ArcInt (auto recovery interval)
//
  
int
cmd_auxarc(char *args, MsgType msgtype, char *reply)
{
  if (aux.ArcMode) {
    aux.ArcMode = 0;
    sprintf(reply,"AUX Link Auto Recovery Mode Disabled");
  }
  else {
    aux.ArcMode = 1;
    sprintf(reply,"AUX Link Auto Recovery Mode Enabled");
  }
  return CMD_OK;
}

//--------------------------------------------------------------------------
//
// aux.auxstatus - return AUX status info as a valid IMPv2 message string
//
// relies on the last telemetry received, or just the AUX Link and 
// ARC mode info if the AUX link is down.  Note that this is usually
// within 20msec of the query, so the lag is small.
// AUX telemetry data update interval is default 0.2 sec.
//

int
cmd_auxstatus(char *args, MsgType msgtype, char *reply)
{
  int i;
  char curdate[16], curtime[16];
  systime_t curutc;

  // set obs date & time with current system clock

  GetUTCDateTime(&curutc);
  sprintf(curdate, "%04d-%02d-%02d", curutc.year, curutc.month, curutc.day);
  sprintf(curtime, "%02d:%02d:%06.3f", curutc.hour, curutc.min, curutc.sec);

  switch (aux.Link) {

  case AUX_UP:
    sprintf(reply, "AUXSTATUS AUXQDATE=%sT%s TIMESYS=UTC TELID=%s AUXLINK=Up AUXARC=%s"
                   " AUXUDATE=%sT%s",
                    curdate, curtime, aux.FitsTelID, aux.ArcMode?"Enabled":"Disabled", 
                    aux.Date, aux.UTC);

    sprintf(reply, "%s FSSTAT=%s", reply, AuxStatusArg(aux.Statuses[AUX_IDX_FS]));
    if(aux.Statuses[AUX_IDX_FS]!=AUX_STATUS_NC) {
      sprintf(reply, "%s FILTOP=%s FILNUM=%d FILTER=%s SHUTOP=%s SHUTTER=%s", reply,
                     AuxStatusArg(aux.FS_FilterOpStat), aux.FS_FilterNum, aux.FS_FilterName, 
                     AuxStatusArg(aux.FS_ShutOpStat), AuxStatusArg(aux.FS_ShutStatus));
    }

    sprintf(reply, "%s FASTAT=%s", reply, AuxStatusArg(aux.Statuses[AUX_IDX_FA]));
    if(aux.Statuses[AUX_IDX_FA]!=AUX_STATUS_NC) {
      sprintf(reply, "%s FAFOCUS=%+.3f FATILTNS=%+.1f FATILTEW=%+.1f"
                     " FALIMS=%d FALIME=%d FALIMW=%d"
                     " FAPOSS=%+.3f FAPOSE=%+.3f FAPOSW=%+.3f", reply,
                     aux.FA_Focus, aux.FA_TiltNS, aux.FA_TiltEW,
                     aux.FA_ActLims[SOUTH], aux.FA_ActLims[EAST], aux.FA_ActLims[WEST],
                     aux.FA_ActPoss[SOUTH], aux.FA_ActPoss[EAST], aux.FA_ActPoss[WEST]);
    }

    sprintf(reply, "%s DSSTAT=%s", reply, AuxStatusArg(aux.Statuses[AUX_IDX_DS]));
    if(aux.Statuses[AUX_IDX_DS]!=AUX_STATUS_NC) {
      sprintf(reply, "%s DSUP=%s DSLW=%s DSSAF=%s DSAUTO=%s DSALT=%.1f DSTEL=%.1f", reply,
                     AuxStatusArg(aux.DS_LimitUpper), AuxStatusArg(aux.DS_LimitLower), 
                     AuxStatusArg(aux.DS_LimitSafety), aux.DS_AutoSync?"ENABLED":"DISABLED",
                     aux.DS_ShutAlt, aux.DS_TeleAlt);
    }

    sprintf(reply, "%s MCSTAT=%s", reply, AuxStatusArg(aux.Statuses[AUX_IDX_MC]));
    if(aux.Statuses[AUX_IDX_MC]!=AUX_STATUS_NC) {
      sprintf(reply, "%s MCPOS=%d", reply, aux.MC_Position);
    }

    sprintf(reply, "%s CHSTAT=%s", reply, AuxStatusArg(aux.Statuses[AUX_IDX_CH]));
    if(aux.Statuses[AUX_IDX_CH]!=AUX_STATUS_NC) {
      sprintf(reply, "%s CHOP=%s CHSET=%.1f CHPROC=%.1f", reply,
                      aux.CH_Cooling?"ON":"OFF", aux.CH_Setpoint, aux.CH_ProcTemp);
    }

    sprintf(reply, "%s ENSTAT=%s", reply, AuxStatusArg(aux.Statuses[AUX_IDX_EN]));
    if(aux.Statuses[AUX_IDX_EN]!=AUX_STATUS_NC) {
      sprintf(reply, "%s ENFAN=%s", reply, aux.EN_FanRelay?"ON":"OFF");
      for(i=0;i<7;i++) 
        sprintf(reply, "%s ENS%d=%.1f", reply, i+1, aux.EN_Sensors[i]);
    }

    break;

  default:
    sprintf(reply, "AUXSTATUS AUXQDATE=%sT%s TIMESYS=UTC TELID=%s AUXLINK=Down AUXARC=%s",
                    curdate, curtime, aux.FitsTelID, aux.ArcMode?"Enabled":"Disabled");
    break;

  }

  return CMD_OK;

}

//--------------------------------------------------------------------------
//
// aux.astat - return AUX status info in lightweight (non-IMPv2 format)
//
// Like cmd_auxstatus, it relies on the last telemetry received, or just
// the AUX Link and ARC mode info if the TCS link is down. The lag
// is usually no more than 20msec from the receipt of the request.
// AUX telemetry data update interval is default 200msec.
//
// Returns a lightweight status string in simple, non-IMPv2 compilant format
// for simple reading/parsing by machines not humans.  The format is
// as follows, depending on the AUX link state:
//
// AUX_UP: AUX link active
//     UP AUXARC AUXQDATE TIMESYS TELID AUXUDATE
//      FS: FSSTAT FILTOP FILNUM FILTER SHUTOP SHUTTER 
//      FA: FASTAT FAFOCUS FATILTNS FATILTEW FALIMS FALIME FALIMW FAPOSS FAPOSE FAPOSW 
//      DS: DSSTAT DSUP DSLW DSSAF DSAUTO DSALT DSTEL 
//      MC: MCSTAT MCPOS 
//      CH: CHSTAT CHOP CHSET CHPROC 
//      EN: ENSTAT ENFAN ENS1 ENS2 ENS3 ENS4 ENS5 ENS6 ENS7
//
// AUX_DOWN: AUX link is disabled ("down")
//     DOWN AUXARC AUXQDATE TIMESYS TELID
//
// Time system for Time/Date in all cases is UTC.  In the Idle/Down cases,
// the time/date returned are from the system time clock, which hopefully is
// reasonable synchronized with a real time server.
//
// Keywords
//   AUXARC   : AUX Link Auto recovery mode - 0:Disabled / 1:Enabled
//   AUXQDATE : query time, recorded when this function is called
//   TELID    : Telescope Identifier - KMTN/KMTC/KMTS/KMTA
//   AUXUDATE : updated time, recorded when the telemetry data packet was received
//   FS:      : Filter/Shutter data identifier
//   FSSTAT   : FS subsystem operation status (NC/STANDBY/RUNNING/ERROR)
//   FILTOP   : filter operation status (NC/STANDBY/RUNNING/ERROR)
//   FILNUM   : current filter number (no:0 / filter 1~4:1~4 / 2 more:5 / unknown:-1)
//   FILTER   : current filter name (NO: no filter / MANY: 2 more filters / UNKNOWN)
//   SHUTOP   : shutter operation status(NC/STANDBY/OPENING/OPENED/CLOSING/RELOADING/ERROR)
//   SHUTTER  : shutter status (OPEN/CLOSED/UNKNOWN)
//   FA:      : Focuser Acutaor data identifier
//   FASTAT   : FA subsystem operation status (NC/STANDBY/RUNNING/ERROR)
//   FAFOCUS  : focus position at the center of PFI(on axis), averaged of 3 actuator pos
//   FATILTNS : North-South PFI tilt angle in arcsec, positive when N is higher than S
//   FATILTEW : East-West PFI tilt angle in arcsec, positive when E is higher than W
//   FALIMS   : limit status of south actuator (no:0/outer:1/inner:2/both:3)
//   FALIME   : limit status of east actuator
//   FALIMW   : limit status of west actuator
//   FAPOSS   : position of south actuator in mm
//   FAPOSE   : position of east actuator in mm
//   FAPOSW   : position of west actuator in mm
//   DS:      : Dome Shutter data identifier
//   DSSTAT   : DS subsystem operation status
//   DSUP     : upper dome shutter status (OPEN/MID/CLOSED)
//   DSLW     : lower dome shutter status (OPEN/MID/CLOSED)
//   DSSAF    : safety interlock switch status (ACTIVE/INACTIVE)
//   DSAUTO   : dome shutter Auto-sync mode (ENABLED/DISABLED)
//   DSALT    : upper dome shutter altitude in deg
//   DSTLE    : telescope altitude that AUX read from Telcom in deg
//   MC:      : Mirror Cover data identifier
//   MCSTAT   : MC subsystem operation status
//   MCPOS    : mirror cover position (0~100)
//   CH:      : Chiller for mirror cooling data identifier
//   CHSTAT   : CH subsystem operation status
//   CHOP     : chiller cooling switch status (ON/OFF)
//   CHSET    : chiller set point temperature, in deg C
//   CHPROC   : chiller process temperature, in deg C
//   EN:      : Environmental system data identifier
//   ENSTAT   : EN subsystem operation status
//   ENFAN    : mirror cooling fan relay status (ON/OFF)
//   ENS1~ENS7: Environmental sensor #1 ~ #7 data, in deg C or RH %

int
cmd_astat(char *args, MsgType msgtype, char *reply)
{
  int i;
  char curdate[16], curtime[16];
  systime_t curutc;
 
  GetUTCDateTime(&curutc);
  sprintf(curdate, "%04d-%02d-%02d", curutc.year, curutc.month, curutc.day);
  sprintf(curtime, "%02d:%02d:%06.3f", curutc.hour, curutc.min, curutc.sec);

  switch (aux.Link) {

  case AUX_UP:
    sprintf(reply, "UP %d %sT%s UTC %s %sT%s", 
                   aux.ArcMode, curdate, curtime, aux.FitsTelID, aux.Date, aux.UTC);
    sprintf(reply, "%s  FS: %s %s %d %s %s %s", reply, 
                   AuxStatusArg(aux.Statuses[AUX_IDX_FS]), 
                   AuxStatusArg(aux.FS_FilterOpStat), aux.FS_FilterNum, aux.FS_FilterName,
                   AuxStatusArg(aux.FS_ShutOpStat), AuxStatusArg(aux.FS_ShutStatus));
    sprintf(reply, "%s  FA: %s %+.3f %+.1f %+.1f  %d %d %d  %+.3f %+.3f %+.3f", reply,
                   AuxStatusArg(aux.Statuses[AUX_IDX_FA]),
                   aux.FA_Focus, aux.FA_TiltNS, aux.FA_TiltEW,
                   aux.FA_ActLims[SOUTH], aux.FA_ActLims[EAST], aux.FA_ActLims[WEST],
                   aux.FA_ActPoss[SOUTH], aux.FA_ActPoss[EAST], aux.FA_ActPoss[WEST]);
    sprintf(reply, "%s  DS: %s %s %s %s %s %.1f %.1f", reply, 
                   AuxStatusArg(aux.Statuses[AUX_IDX_DS]), 
                   AuxStatusArg(aux.DS_LimitUpper), AuxStatusArg(aux.DS_LimitLower), 
                   AuxStatusArg(aux.DS_LimitSafety), aux.DS_AutoSync?"ENABLED":"DISABLED",
                   aux.DS_ShutAlt, aux.DS_TeleAlt);
    sprintf(reply, "%s  MC: %s %d", reply, 
                   AuxStatusArg(aux.Statuses[AUX_IDX_MC]), aux.MC_Position);
    sprintf(reply, "%s  CH: %s %s %.1f %.1f", reply, 
                   AuxStatusArg(aux.Statuses[AUX_IDX_CH]), 
                   aux.CH_Cooling?"ON":"OFF", aux.CH_Setpoint, aux.CH_ProcTemp);
    sprintf(reply, "%s  EN: %s %s", reply, 
                   AuxStatusArg(aux.Statuses[AUX_IDX_EN]), aux.EN_FanRelay?"ON":"OFF");
    for(i=0;i<7;i++) sprintf(reply, "%s %.1f", reply, aux.EN_Sensors[i]);

    break;

  default:
    sprintf(reply, "DOWN %d %sT%s UTC %s", aux.ArcMode, curdate, curtime, aux.FitsTelID);
    break;

  }

  return CMD_OK;

}

//--------------------------------------------------------------------------
//
// aux.fsastat - return status of Filter/Shut assembly in lightweight (non-IMPv2 format)
//
// Returns a lightweight string in simple for only Filter/Shutter status,
// non-IMPv2 compilant format for simple reading/parsing by machines not humans.
// The format is as follows, depending on the AUX link state:
//
// AUX_UP: AUX link active
//     UP FILTOP FILNUM FILTER SHUTOP SHUTTER 
//
// AUX_DOWN: AUX link is disabled ("down")
//     DOWN 
//
// Keywords
//   FILTOP   : filter operation status (NC/STANDBY/RUNNING/ERROR)
//   FILNUM  : current filter number (no:0 / filter 1~4:1~4 / 2 more:5 / unknown:-1)
//   FILTER   : current filter name (NO: no filter / MANY: 2 more filters / UNKNOWN)
//   SHUTOP   : shutter operation status(NC/STANDBY/OPENING/OPENED/CLOSING/RELOADING/ERROR)
//   SHUTTER  : shutter status (OPEN/CLOSED/UNKNOWN)
//

int
cmd_afsastat(char *args, MsgType msgtype, char *reply)
{
  switch (aux.Link) {

  case AUX_UP:
    sprintf(reply, "UP %s %d %s %s %s", 
                    AuxStatusArg(aux.FS_FilterOpStat), aux.FS_FilterNum, aux.FS_FilterName, 
                    AuxStatusArg(aux.FS_ShutOpStat), AuxStatusArg(aux.FS_ShutStatus));
    break;

  default:
    sprintf(reply, "DOWN");
    break;

  }

  return CMD_OK;
}

//--------------------------------------------------------------------------
//
// aux.fttstat - return status of Focus/Tip-Tilt in lightweight (non-IMPv2 format)
//
// Returns a lightweight string in simple for only Focus/Tip-Tilt status,
// non-IMPv2 compilant format for simple reading/parsing by machines not humans.
// The format is as follows, depending on the AUX link state:
//
// AUX_UP: AUX link active
//     UP FASTAT FAFOCUS FATILTNS FATILTEW FALIMS FALIME FALIMW FAPOSS FAPOSE FAPOSW
//
// AUX_DOWN: AUX link is disabled ("down")
//     DOWN 
//
// Ketwords
//   FASTAT   : FA subsystem operation status (NC/STANDBY/RUNNING/ERROR)
//   FAFOCUS  : focus position at the center of PFI(on axis), averaged of 3 actuator pos
//   FATILTNS : North-South PFI tilt angle in arcsec, positive when N is higher than S
//   FATILTEW : East-West PFI tilt angle in arcsec, positive when E is higher than W
//   FALIMS   : limit status of south actuator (no:0/outer:1/inner:2/both:3)
//   FALIME   : limit status of east actuator
//   FALIMW   : limit status of west actuator
//   FAPOSS   : position of south actuator in mm
//   FAPOSE   : position of east actuator in mm
//   FAPOSW   : position of west actuator in mm
//

int
cmd_afttstat(char *args, MsgType msgtype, char *reply)
{
  switch (aux.Link) {

  case AUX_UP:
    sprintf(reply, "UP %s %+.3f %+.1f %+.1f  %d %d %d  %+.3f %+.3f %+.3f", 
                      AuxStatusArg(aux.Statuses[AUX_IDX_FA]), 
                      aux.FA_Focus, aux.FA_TiltNS, aux.FA_TiltEW,
                      aux.FA_ActLims[SOUTH], aux.FA_ActLims[EAST], aux.FA_ActLims[WEST],
                      aux.FA_ActPoss[SOUTH], aux.FA_ActPoss[EAST], aux.FA_ActPoss[WEST]);
    break;

  default:
    sprintf(reply, "DOWN");
    break;

  }

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// aux.acmd - send a AUX ctrl remote command
//
// if success, AUX server's response is copied to reply buffer to send to user
// if error, a error message will be copied to reply buffer
//

int
cmd_acmd(char *args, MsgType msgtype, char *reply)
{
  char cmd[CMDBUFLEN];
  char rsp[CMDBUFLEN];
  char subsys[ARGBUFLEN];
  char subcmd[ARGBUFLEN];
  int rtn, cmdlen;

  // gotta be up to send commands

  if (aux.Link != AUX_UP) {
    strcpy(reply, "AUX Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // also need something to send

  rtn = sscanf(args, "%s %[^\n]", subsys, subcmd);
  if ( rtn < 2 ) {
    strcpy(reply, "usage: acmd <acmd>  /  <acmd>: consist of <subsys> <auxcmd>");
    strcat(reply, ", defined in KMTNet AUX control remote commands definition");
    return CMD_ERR;
  }

  // Assume the command is the argument buffer, we won't try to
  // validate command syntax.

  memset(cmd, 0, CMDBUFLEN);
  cmdlen = sprintf(cmd, "%s %s %03d %s\n", aux.TelID, aux.SysID, PID_REQCMD, strupr(args));

  // send the command to Telcom via aux link

  rtn = send(aux.FD, cmd, cmdlen, 0);
  if( rtn < cmdlen ) {
    sprintf(reply, "command send failed - cmd='%s' cmdlen=%d, sentbyte=%d", 
                   args, cmdlen, rtn);
    return CMD_ERR;
  }
  if(client.isVerbose) {
    printf("\r AUX OUT: %s", cmd);
    //rl_refresh_line(0,0);
  }

  // receive the response of command

  memset(cmd, 0, CMDBUFLEN);
  cmdlen = recv(aux.FD, cmd, CMDBUFLEN-1, 0);
  if(cmdlen<=0) {
    sprintf(reply, "response recv failed - recvbyte = %d", cmdlen);
    return CMD_ERR;
  }
  cmd[cmdlen] = NULL;
  if(client.isVerbose) {
    printf("\r AUX IN : %s", cmd);
    //rl_refresh_line(0,0);
  }

  // check the response from aux ctrl server

  rtn = sscanf(cmd, "%*s %*s %*s %[^\n]", rsp);
  if( rtn != 1 ) {
    sprintf(reply, "unrecognized response - not scannable(argnum=%d)", rtn);
    return CMD_ERR;
  }

  // common response for general operationg cmd

  if(strcasecmp(rsp,"OK")==0) {
    sprintf(reply, "AUX CMD '%s' OK", args);
    return CMD_OK;
  }

  if(strcasecmp(rsp,"WAIT")==0) {
    sprintf(reply, "command failed with 'WAIT' response");
    return CMD_ERR;
  }

  if(strcasecmp(rsp,"BAD")==0) {
    sprintf(reply, "command failed with 'BAD' response");
    return CMD_ERR;
  }

  if(strcasecmp(rsp,"ERROR")==0) {
    if(strcasecmp(subcmd, "STATUS")!=0) {
      sprintf(reply, "command failed with 'ERROR' response");
      return CMD_ERR;
    }
  }

  // all done

  strcpy(reply, rsp);
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// aux.filter - change filters to the filter number commanded by a argument 
//

int
cmd_afilter(char *args, MsgType msgtype, char *reply)
{
  char cmd[CMDBUFLEN];
  char arg[ARGBUFLEN];
  int rtn, cmdlen, i;
  int fnum;

  // gotta be up to send commands

  if (aux.Link != AUX_UP) {
    strcpy(reply, "AUX Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  if (aux.Statuses[AUX_IDX_FS] == AUX_STATUS_NC ) {
    strcpy(reply, "Filter/Shutter subsystem not connected");
    return CMD_ERR;
  }

  // check argument number

  if(strlen(args)<1) {
    sprintf(reply, "usage: filter <fnum/fname>"
                   "  /  <fnum/fname>: filter number 0 ~ 4 (0:no filter)"
                   ", or filter name %s/%s/%s/%s/%s or initial", 
                   aux.FS_FilNames[AUX_FS_FNUM_NO], aux.FS_FilNames[AUX_FS_FNUM_F1],
                   aux.FS_FilNames[AUX_FS_FNUM_F2], aux.FS_FilNames[AUX_FS_FNUM_F3],
                   aux.FS_FilNames[AUX_FS_FNUM_F4] );
    return CMD_ERR;
  }

  rtn = sscanf(args, "%d", &fnum);

  if(rtn<1) {
         if(strcasecmp(args,aux.FS_FilNames[AUX_FS_FNUM_NO])==0) fnum = AUX_FS_FNUM_NO;
    else if(strcasecmp(args,aux.FS_FilNames[AUX_FS_FNUM_F1])==0) fnum = AUX_FS_FNUM_F1;
    else if(strcasecmp(args,aux.FS_FilNames[AUX_FS_FNUM_F2])==0) fnum = AUX_FS_FNUM_F2;
    else if(strcasecmp(args,aux.FS_FilNames[AUX_FS_FNUM_F3])==0) fnum = AUX_FS_FNUM_F3;
    else if(strcasecmp(args,aux.FS_FilNames[AUX_FS_FNUM_F4])==0) fnum = AUX_FS_FNUM_F4;
    else fnum = AUX_UNKNOWN;
    if(strlen(args)==1) {
           if(UC(args[0])==UC(aux.FS_FilNames[AUX_FS_FNUM_NO][0])) fnum = AUX_FS_FNUM_NO;
      else if(UC(args[0])==UC(aux.FS_FilNames[AUX_FS_FNUM_F1][0])) fnum = AUX_FS_FNUM_F1;
      else if(UC(args[0])==UC(aux.FS_FilNames[AUX_FS_FNUM_F2][0])) fnum = AUX_FS_FNUM_F2;
      else if(UC(args[0])==UC(aux.FS_FilNames[AUX_FS_FNUM_F3][0])) fnum = AUX_FS_FNUM_F3;
      else if(UC(args[0])==UC(aux.FS_FilNames[AUX_FS_FNUM_F4][0])) fnum = AUX_FS_FNUM_F4;
      else fnum = AUX_UNKNOWN;
    }
    rtn=2;
  }

  // check filter number

  if( fnum<0 || fnum>4 ) {
    switch(rtn) {
      case  1: sprintf(reply, "incorrect filter number"      ); break;
      case  2: sprintf(reply, "incorrect filter name/initial"); break;
      default: sprintf(reply, "incorrect argument"           ); break;
    }
    return CMD_ERR;
  }

  // control 4 filter slides (move the set filter to IN, move other filters to OUT)
  // in pctcs.h, AUX_IDX_FS_F1 must be 0, and AUX_IDX_FS_F4 must be 3 for this routine

  rtn = CMD_OK;  // rtn is not refered if fnum = 0 and all filter limit = OUT

  for(i=0;i<4;i++) {
    //if( (i+1)==fnum && aux.FS_Limits[i]!=AUX_BILIMIT_IN ) {
    if( (i+1)==fnum ) {
      sprintf(cmd, "FILTERS SET_F%d IN", (i+1));  // v1.3.2
      rtn = cmd_acmd(cmd, EXEC, reply);
    }
    else if( (i+1)!=fnum && aux.FS_Limits[i]!=AUX_BILIMIT_OUT ) {
      sprintf(cmd, "FILTERS SET_F%d OUT", (i+1));
      rtn = cmd_acmd(cmd, EXEC, reply);
    }

    if(rtn!=CMD_OK) {
      sprintf(reply, "%s for filter change to #%d (%s)", reply, fnum, aux.FS_FilNames[fnum]);
      return CMD_ERR;
    }
  }

  // all done

  sprintf(reply, "change to filter #%d (%s) commanded", fnum, aux.FS_FilNames[fnum]);
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// aux.filname - return AUX filter slide names as a valid IMPv2 message string
//               for labeling on UI
//
// String format: F1_NAME=__ F2_NAME=__ F3_NAME=__ F4_NAME=__
//

int
cmd_afilname(char *args, MsgType msgtype, char *reply)    // v1.3.0
{
  // gotta be up to send commands

  if (aux.Link != AUX_UP) {
    strcpy(reply, "AUX Link is IDLE/DOWN, filter names query unavailable");
    return CMD_ERR;
  }

  sprintf(reply, "FILNAME F1_NAME=%s F2_NAME=%s F3_NAME=%s F4_NAME=%s", 
                 aux.FS_FilNames[AUX_FS_FNUM_F1], aux.FS_FilNames[AUX_FS_FNUM_F2], 
                 aux.FS_FilNames[AUX_FS_FNUM_F3], aux.FS_FilNames[AUX_FS_FNUM_F4]);

  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// aux.dfocus - adjust the focus position of PFI center as delta focus (offset)
//

int
cmd_adfocus(char *args, MsgType msgtype, char *reply)
{
  char cmd[CMDBUFLEN];
  int rtn, cmdlen;
  double dfoc;  // delta focus

  // gotta be up to send commands

  if (aux.Link != AUX_UP) {
    strcpy(reply, "AUX Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%lf", &dfoc);

  if(rtn<1) {
    strcpy(reply, "usage: dfocus <dfoc>");
    strcat(reply, "  /  <dfoc>: delta focus = dest.focus - curr.focus, +x.xxx (in mm)");
    return CMD_ERR;
  }

  // check delta focus value

  if( fabs(dfoc) > MAX_DELTAFOCUS ) {
    sprintf(reply, "<dfoc> value is out of range (Max. +/-%.3f mm)", MAX_DELTAFOCUS);
    return CMD_ERR;
  }
 
  // send a command for focus offset move

  sprintf(cmd, "FOCUSER OFFSET %+.3f", dfoc);
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  sprintf(reply, "adjust focus commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// aux.dtilt - adjust the PFI tip-tilt angle as delta tilt (+/- arcsec)
//             on cartesian coordinate system, using n-s and e-w tilting angle
//

int
cmd_adtilt(char *args, MsgType msgtype, char *reply)
{
  char cmd[CMDBUFLEN];
  int rtn, cmdlen;
  double dtns, dtew;  // delta tip-tilt angle for N-S & E-W
  double das, dae, daw;  // delta positions of As, Ae & Aw
  double a[3];  // destination, abs positions of A1, A2 & A3

  // check command type (EXEC only allowed)

  //if (msgtype != EXEC) {
  //  strcpy(reply, "cannot exec 'dtilt' command - remote operation not allowed");
  //  return CMD_ERR;
  //}
  // --> removed for Skip's UI (v1.3.0)

  // gotta be up to send commands

  if (aux.Link != AUX_UP) {
    strcpy(reply, "AUX Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%lf %lf", &dtns, &dtew);

  if(rtn<2) {
    strcpy(reply, "usage: dtilt <dtns> <dtew>");
    strcat(reply, "  /  <dtns>: delta tilt for N-S, +x.x");
    strcat(reply, "  <dtew>: delta tilt for E-W, +x.x (in arcsec)");
    strcat(reply, "  /  positive when N/E goes up and S/W goes down");
    return CMD_ERR;
  }

  // check delta focus value

  if( fabs(dtns) > MAX_DELTATILT ) {
    sprintf(reply, "<dns> value is out of range (Max. +/-%.1f arcsec)", MAX_DELTATILT);
    return CMD_ERR;
  }

  if( fabs(dtew) > MAX_DELTATILT ) {
    sprintf(reply, "<dew> value is out of range (Max. +/-%.1f arcsec)", MAX_DELTATILT);
    return CMD_ERR;
  }

  // check limit status with tip-tilt direction

  // dtns>0, N goes up   & S goes down, should not be limit at north-out & south-in
  // dtns<0, N goes down & S goes up  , should not be limit at north-in  & south-out
  // dtew>0, E goes up   & W goes down, should not be limit at east-out  & west-in
  // dtew<0, E goes down & W goes up  , should not be limit at east-in   & west-out

  if( ( ( aux.FA_ActLims[SOUTH]==AUX_BILIMIT_IN  ||
          aux.FA_ActLims[EAST ]==AUX_BILIMIT_OUT || 
          aux.FA_ActLims[WEST ]==AUX_BILIMIT_OUT  ) && dtns>0.0 ) ||
      ( ( aux.FA_ActLims[SOUTH]==AUX_BILIMIT_OUT ||
          aux.FA_ActLims[EAST ]==AUX_BILIMIT_IN  || 
          aux.FA_ActLims[WEST ]==AUX_BILIMIT_IN   ) && dtns<0.0 ) ||
      ( ( aux.FA_ActLims[EAST ]==AUX_BILIMIT_OUT || 
          aux.FA_ActLims[WEST ]==AUX_BILIMIT_IN   ) && dtew>0.0 ) ||
      ( ( aux.FA_ActLims[EAST ]==AUX_BILIMIT_IN  || 
          aux.FA_ActLims[WEST ]==AUX_BILIMIT_OUT  ) && dtew<0.0 )  ) {
    sprintf(reply, "cannot tilt angle anymore due to the HW limit");
    return CMD_ERR;
  }

  // calculate each actuator's offset for commanded tip-tilting angle

  das = -1.0 * RAC * dtns * SEC2RAD;
  dae = +0.5 * RAC * dtns * SEC2RAD;
  daw = +0.5 * RAC * dtns * SEC2RAD;

  dae += +SQRT3 * 0.5 * RAC * dtew * SEC2RAD;
  daw += -SQRT3 * 0.5 * RAC * dtew * SEC2RAD;

  a[aux.FA_ActNums[SOUTH]-1] = aux.FA_ActPoss[SOUTH] + das;
  a[aux.FA_ActNums[EAST] -1] = aux.FA_ActPoss[EAST]  + dae;
  a[aux.FA_ActNums[WEST] -1] = aux.FA_ActPoss[WEST]  + daw;

  // send a command for focus offset move

  sprintf(cmd, "FOCUSER GOTO_ALL %+.3f %+.3f %+.3f", a[0], a[1], a[2]);
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  sprintf(reply, "adjust PFI tip-tilt commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// aux.dtiltp - adjust the PFI tip-tilt angle as delta tilt (+/- arcsec)
//              with orientation & tilting angle on the polar coordinate system
//              orientation: 0 deg on South / 90 deg on East, 
//              tilting angle: + up / - down
//

int
cmd_adtiltp(char *args, MsgType msgtype, char *reply)    // v1.5?
{
  char cmd[CMDBUFLEN];
  int rtn, cmdlen;
  double theta, dtilt; // theta: 0 deg on South / 90 deg on East
  double dtns, dtew;  // delta tip-tilt angle for N-S & E-W
  double das, dae, daw;  // delta positions of As, Ae & Aw
  double a[3];  // destination, abs positions of A1, A2 & A3

  // check command type (EXEC only allowed)

  //if (msgtype != EXEC) {
  //  strcpy(reply, "cannot exec 'dtilt' command - remote operation not allowed");
  //  return CMD_ERR;
  //}
  // --> removed for Skip's UI (v1.3.0)

  // gotta be up to send commands

  if (aux.Link != AUX_UP) {
    strcpy(reply, "AUX Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%lf %lf", &dtns, &dtew);

  if(rtn<2) {
    strcpy(reply, "usage: dtilt <dtns> <dtew>");
    strcat(reply, "  /  <dtns>: delta tilt for N-S, +x.x");
    strcat(reply, "  <dtew>: delta tilt for E-W, +x.x (in arcsec)");
    strcat(reply, "  /  positive when N/E goes up and S/W goes down");
    return CMD_ERR;
  }

  // check delta focus value

  if( fabs(dtns) > MAX_DELTATILT ) {
    sprintf(reply, "<dns> value is out of range (Max. +/-%.1f arcsec)", MAX_DELTATILT);
    return CMD_ERR;
  }

  if( fabs(dtew) > MAX_DELTATILT ) {
    sprintf(reply, "<dew> value is out of range (Max. +/-%.1f arcsec)", MAX_DELTATILT);
    return CMD_ERR;
  }

  // check limit status with tip-tilt direction

  // dtns>0, N goes up   & S goes down, should not be limit at north-out & south-in
  // dtns<0, N goes down & S goes up  , should not be limit at north-in  & south-out
  // dtew>0, E goes up   & W goes down, should not be limit at east-out  & west-in
  // dtew<0, E goes down & W goes up  , should not be limit at east-in   & west-out

  if( ( ( aux.FA_ActLims[SOUTH]==AUX_BILIMIT_IN  ||
          aux.FA_ActLims[EAST ]==AUX_BILIMIT_OUT || 
          aux.FA_ActLims[WEST ]==AUX_BILIMIT_OUT  ) && dtns>0.0 ) ||
      ( ( aux.FA_ActLims[SOUTH]==AUX_BILIMIT_OUT ||
          aux.FA_ActLims[EAST ]==AUX_BILIMIT_IN  || 
          aux.FA_ActLims[WEST ]==AUX_BILIMIT_IN   ) && dtns<0.0 ) ||
      ( ( aux.FA_ActLims[EAST ]==AUX_BILIMIT_OUT || 
          aux.FA_ActLims[WEST ]==AUX_BILIMIT_IN   ) && dtew>0.0 ) ||
      ( ( aux.FA_ActLims[EAST ]==AUX_BILIMIT_IN  || 
          aux.FA_ActLims[WEST ]==AUX_BILIMIT_OUT  ) && dtew<0.0 )  ) {
    sprintf(reply, "cannot tilt angle anymore due to the HW limit");
    return CMD_ERR;
  }

  // calculate each actuator's offset for commanded tip-tilting angle

  das = -1.0 * RAC * dtns * SEC2RAD;
  dae = +0.5 * RAC * dtns * SEC2RAD;
  daw = +0.5 * RAC * dtns * SEC2RAD;

  dae += +SQRT3 * 0.5 * RAC * dtew * SEC2RAD;
  daw += -SQRT3 * 0.5 * RAC * dtew * SEC2RAD;

  a[aux.FA_ActNums[SOUTH]-1] = aux.FA_ActPoss[SOUTH] + das;
  a[aux.FA_ActNums[EAST] -1] = aux.FA_ActPoss[EAST]  + dae;
  a[aux.FA_ActNums[WEST] -1] = aux.FA_ActPoss[WEST]  + daw;

  // send a command for focus offset move

  sprintf(cmd, "FOCUSER GOTO_ALL %+.3f %+.3f %+.3f", a[0], a[1], a[2]);
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  sprintf(reply, "adjust PFI tip-tilt commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// aux.fttgoto - goto the focus position and the tip-tilt angle (Abs.position) 
//               on cartesian coordinate system, using n-s and e-w tilting angle
//               (EXEC only in case tip-tilt args used)

int
cmd_afttgoto(char *args, MsgType msgtype, char *reply)
{
  char cmd[CMDBUFLEN];
  int rtn, cmdlen;
  double foc, tns, tew;  // destination, abs focus position and abs tip-tilt angle
  double dfoc, dtns, dtew;  // delta focus position and delta tip-tilt angle
  double das, dae, daw;  // delta positions of As, Ae & Aw
  double a[3];  // destination, abs positions of A1, A2 & A3

  // gotta be up to send commands

  if (aux.Link != AUX_UP) {
    strcpy(reply, "AUX Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%lf %lf %lf", &foc, &tns, &tew);

  if(rtn==3) {  // EXEC only allowed, if there are tip-tilt args
  //if (msgtype != EXEC) {
  //  strcpy(reply, "cannot exec 'fttgoto' command");
  //  strcat(reply, " - including <tns> & <tew> arguments, remote operation not allowed");
  //  return CMD_ERR;
  //}
  // --> removed for Skip's UI (v1.3.0)
  }
  else if(rtn==1) {
    tns = aux.FA_TiltNS;
    tew = aux.FA_TiltEW;
  }
  else {
    strcpy(reply, "usage: fttgoto <foc> (<tns> <tew>)");
    strcat(reply, "  /  <foc>: abs focus position, +x.xxx (in mm)");
    //strcat(reply, "  <tns>: abs tilt angle for N-S, +x.x");
    //strcat(reply, "  <tew>: abs tilt angle for E-W, +x.x (in arcsec)");
    //strcat(reply, "  /  <tns> & <tew> arguments are optional and allowed only EXEC cmd");
    strcat(reply, "  <tns>: abs tilt angle for N-S, +x.x, optional");  // v1.3.0
    strcat(reply, "  <tew>: abs tilt angle for E-W, +x.x, optional (in arcsec)");
    return CMD_ERR;
  }

  // check the value of focus argument

  if( fabs(foc) > MAX_FOCUSRANGE ) {
    sprintf(reply, "<foc> value is out of range (Max. +/-%.3f mm)", MAX_FOCUSRANGE);
    return CMD_ERR;
  }

  // check the value of tilt angle arguments

  if( rtn==3 && fabs(tns) > MAX_TILTRANGE ) {
    sprintf(reply, "<tns> value is out of range (Max. +/-%.1f arcsec)", MAX_TILTRANGE);
    return CMD_ERR;
  }

  if( rtn==3 && fabs(tew) > MAX_TILTRANGE ) {
    sprintf(reply, "<tew> value is out of range (Max. +/-%.1f arcsec)", MAX_TILTRANGE);
    return CMD_ERR;
  }

  // calculate each actuator's abs position for the commanded focus & tip-tilt

  dfoc = foc - aux.FA_Focus;
  dtns = tns - aux.FA_TiltNS;
  dtew = tew - aux.FA_TiltEW;

  das = -1.0 * RAC * dtns * SEC2RAD;
  dae = +0.5 * RAC * dtns * SEC2RAD;
  daw = +0.5 * RAC * dtns * SEC2RAD;

  dae += +SQRT3 * 0.5 * RAC * dtew * SEC2RAD;
  daw += -SQRT3 * 0.5 * RAC * dtew * SEC2RAD;

  a[aux.FA_ActNums[SOUTH]-1] = aux.FA_ActPoss[SOUTH] + das + dfoc;
  a[aux.FA_ActNums[EAST] -1] = aux.FA_ActPoss[EAST]  + dae + dfoc;
  a[aux.FA_ActNums[WEST] -1] = aux.FA_ActPoss[WEST]  + daw + dfoc;

  // send a command for focus offset move

  sprintf(cmd, "FOCUSER GOTO_ALL %+.3f %+.3f %+.3f", a[0], a[1], a[2]);
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  sprintf(reply, "goto focus and tip-tilt commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// aux.fttgotop - goto the focus position and the tip-tilt angle (Abs.position) 
//                with orientation & tilting angle on the polar coordinate system
//                orientation: 0 deg on South / 90 deg on East, 
//                tilting angle: + up / - down
//                (EXEC only in case tip-tilt args used)

int
cmd_afttgotop(char *args, MsgType msgtype, char *reply)    // v1.5?
{
  char cmd[CMDBUFLEN];
  int rtn, cmdlen;
  double foc, tns, tew;  // destination, abs focus position and abs tip-tilt angle
  double dfoc, dtns, dtew;  // delta focus position and delta tip-tilt angle
  double das, dae, daw;  // delta positions of As, Ae & Aw
  double a[3];  // destination, abs positions of A1, A2 & A3

  // gotta be up to send commands

  if (aux.Link != AUX_UP) {
    strcpy(reply, "AUX Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%lf %lf %lf", &foc, &tns, &tew);

  if(rtn==3) {  // EXEC only allowed, if there are tip-tilt args
  //if (msgtype != EXEC) {
  //  strcpy(reply, "cannot exec 'fttgoto' command");
  //  strcat(reply, " - including <tns> & <tew> arguments, remote operation not allowed");
  //  return CMD_ERR;
  //}
  // --> removed for Skip's UI (v1.3.0)
  }
  else if(rtn==1) {
    tns = aux.FA_TiltNS;
    tew = aux.FA_TiltEW;
  }
  else {
    strcpy(reply, "usage: fttgoto <foc> (<tns> <tew>)");
    strcat(reply, "  /  <foc>: abs focus position, +x.xxx (in mm)");
    //strcat(reply, "  <tns>: abs tilt angle for N-S, +x.x");
    //strcat(reply, "  <tew>: abs tilt angle for E-W, +x.x (in arcsec)");
    //strcat(reply, "  /  <tns> & <tew> arguments are optional and allowed only EXEC cmd");
    strcat(reply, "  <tns>: abs tilt angle for N-S, +x.x, optional");  // v1.3.0
    strcat(reply, "  <tew>: abs tilt angle for E-W, +x.x, optional (in arcsec)");
    return CMD_ERR;
  }

  // check the value of focus argument

  if( fabs(foc) > MAX_FOCUSRANGE ) {
    sprintf(reply, "<foc> value is out of range (Max. +/-%.3f mm)", MAX_FOCUSRANGE);
    return CMD_ERR;
  }

  // check the value of tilt angle arguments

  if( rtn==3 && fabs(tns) > MAX_TILTRANGE ) {
    sprintf(reply, "<tns> value is out of range (Max. +/-%.1f arcsec)", MAX_TILTRANGE);
    return CMD_ERR;
  }

  if( rtn==3 && fabs(tew) > MAX_TILTRANGE ) {
    sprintf(reply, "<tew> value is out of range (Max. +/-%.1f arcsec)", MAX_TILTRANGE);
    return CMD_ERR;
  }

  // calculate each actuator's abs position for the commanded focus & tip-tilt

  dfoc = foc - aux.FA_Focus;
  dtns = tns - aux.FA_TiltNS;
  dtew = tew - aux.FA_TiltEW;

  das = -1.0 * RAC * dtns * SEC2RAD;
  dae = +0.5 * RAC * dtns * SEC2RAD;
  daw = +0.5 * RAC * dtns * SEC2RAD;

  dae += +SQRT3 * 0.5 * RAC * dtew * SEC2RAD;
  daw += -SQRT3 * 0.5 * RAC * dtew * SEC2RAD;

  a[aux.FA_ActNums[SOUTH]-1] = aux.FA_ActPoss[SOUTH] + das + dfoc;
  a[aux.FA_ActNums[EAST] -1] = aux.FA_ActPoss[EAST]  + dae + dfoc;
  a[aux.FA_ActNums[WEST] -1] = aux.FA_ActPoss[WEST]  + daw + dfoc;

  // send a command for focus offset move

  sprintf(cmd, "FOCUSER GOTO_ALL %+.3f %+.3f %+.3f", a[0], a[1], a[2]);
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  sprintf(reply, "goto focus and tip-tilt commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tick
//

int
cmd_tick(char *args, MsgType msgtype, char *reply)    // v1.4.4
{
  int rtn;
  int arg;
  static int idx=-1;
  static systime_t ut;
  double tick_curr;
  static double tick_prev;
  static double tick_zero;
  

  rtn = sscanf(args,"%d",&arg);
  //sprintf(reply,"%d\n",rtn);return CMD_ERR;  //for test

  if(rtn==0) goto USAGE;  // not integer

  if(rtn<0)  // no arg
  {
    if(idx==-1) goto USAGE;
    else idx++;
  }

  if(rtn==1) // arg ok
  {
    if(arg==0) 
    {
      idx = 0;
      strcpy(reply, "tick ready..");
      return CMD_OK;
    }

    if(arg<0) goto USAGE;
    if(idx==-1) goto USAGE;

    idx = arg;
  }


  tick_curr = SysTimestamp();
  GetUTCDateTime(&ut);

  if(idx==1) tick_zero = tick_prev = tick_curr;
    
  printf("                %04d-%02d-%02dT%02d:%02d:%06.3f    %04d %6.1f %6.1f\n", 
                          ut.year, ut.month, ut.day, ut.hour, ut.min, ut.sec,
                          idx, tick_curr-tick_zero, tick_curr-tick_prev);

  tick_prev = tick_curr;

  return CMD_NOOP;

  USAGE:
    strcpy(reply, "usage: 'tick 0' = reset"
                  "  / 'tick' = +1 step  / 'tick 1' = set index");
    return CMD_ERR;
}

//---------------------------------------------------------------------------
//---------------------------------------------------------------------------
//
// Utility functions
//

//
// *** PC-TCS CMD SUBROUTINES BEGIN HERE ***
//

//---------------------------------------------------------------------------
//
// TcsTelemetry - update TCS telemetry data, 
//                independent from telemetry update in main()
//

int
TcsTelemetry(pctcs_t *tcs, char *reply) 
{
  int rtn;
  char tcsbuf[BUF_SIZE];
  memset(tcsbuf,0,BUF_SIZE);

  // Send the telemetry request CMD for execution code update

  rtn = send(tcs->FDcmd, tcs->RequestMsg, tcs->RequestLen, 0);
  if( rtn < tcs->RequestLen ) {
    sprintf(reply, "telemetry rquest CMD send failed - cmdlen = %d, sentbyte = %d", 
                   tcs->RequestLen, rtn);
    return -1;
  }

  // Waitting and Receive the telemetry data

  rtn = recv(tcs->FDcmd, tcsbuf, BUF_SIZE-1, 0);

  if( rtn > 0 ) tcs->TelcomTick = SysTimestamp();
  if( rtn < tcs->MinTelemetryLen ) {  // not enough telemetry data length
    sprintf(reply, "telemetry data update failed - recvbyte = %d", rtn);
    return -1;
  }

  // Inspection and Update the telemetry data

  rtn = parse_comsoft(tcs,(tcsbuf+tcs->ReqHedLen));
  if(rtn==0) tcs->PctcsTick = SysTimestamp();    // telemetry data ok
  if(rtn<-4) {                                   // no data
    sprintf(reply, "telemetry data update failed - no data", rtn);
    return -1;
  }

  // all done

  strcpy(reply, "TCS Telemetry data updated");
  return 0;

}

//---------------------------------------------------------------------------
//
// TcsSetEpoch - set PC-TCS Input Epoch to 2000
//

int
TcsSetEpoch(pctcs_t *tcs, char *reply)    // v1.2.2
{
  char cmd[SHORT_STR_SIZE];
  char errmsg[MED_STR_SIZE];
  int rtn, verbose;

  verbose=client.isVerbose;
  client.isVerbose=0;

  sprintf(cmd, "EPOCH %.3f", TCS_INPUT_EPOCH);
  rtn = cmd_tcmd(cmd, EXEC, errmsg);

////  tcs->TelcomTick = SysTimestamp();  // reset idle time for Telcom link, v1.5?

  client.isVerbose=verbose;

  if(rtn!=CMD_OK)
  {
    //sprintf(reply, "TCS Input Epoch setting failed (%s)", errmsg);  // too long..
    errmsg[4] = NULL;
    sprintf(reply, "TCS Input Epoch setting failed (%s)", errmsg);
    return -1;
  }

  sprintf(reply, "TCS Input Epoch set to %.3f success", TCS_INPUT_EPOCH);
  return 0;
}



//
// *** AUX CTRL SUBROUTINES BEGIN HERE ***
//

//-------------------------------------------------------------------------
//
// AuxTelemetry - Update the AUX control data
//
// return 0 on success, -1 on errors
// if error, the AUXLink will be set to DOWN in main()
//
// Processing time for all telemetry data update is usually less than 10 ms.
//

int
AuxTelemetry(auxctrl_t *aux, char *reply)
{
  static char cmd[CMDBUFLEN];
  static char arg[16][ARGBUFLEN];
  int rtn, cmdlen;
  int argnum, arglen;
  double As, Ae, Aw, foc;
  static double As_prev, Ae_prev, Aw_prev;
  systime_t systime;

  // get All statuses for all the AUX subsystems ///////////////////////////////////
  
  // Request All statuses
  sprintf(cmd, "ALL STATUS");
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return -1;

  // Receive All statuses response
  rtn = sscanf(reply, 
               "%*s %s %d %d %d %lf %lf %lf "
               "%*s %s %lf %lf %s %s %s %s "
               "%*s %s %d %d %d %d %d %d "
               "%*s %s %d "
               "%*s %s %lf %lf %s "
               "%*s %s %lf %lf %lf %lf %lf %lf %lf %s ",
               arg[AUX_IDX_FA], 
               &aux->FA_Limits[AUX_IDX_FA_A1], &aux->FA_Limits[AUX_IDX_FA_A2],
               &aux->FA_Limits[AUX_IDX_FA_A3], &aux->FA_Positions[AUX_IDX_FA_A1],
               &aux->FA_Positions[AUX_IDX_FA_A2], &aux->FA_Positions[AUX_IDX_FA_A3],
               arg[AUX_IDX_DS], 
               &aux->DS_ShutAlt, &aux->DS_TeleAlt, arg[10], arg[11], arg[12], arg[13], 
               arg[AUX_IDX_FS], 
               &aux->FS_Limits[AUX_IDX_FS_F1], &aux->FS_Limits[AUX_IDX_FS_F2],
               &aux->FS_Limits[AUX_IDX_FS_F3], &aux->FS_Limits[AUX_IDX_FS_F4],
               &aux->FS_Limits[AUX_IDX_FS_SF], &aux->FS_Limits[AUX_IDX_FS_SH],
               arg[AUX_IDX_MC], 
               &aux->MC_Position,
               arg[AUX_IDX_CH], 
               &aux->CH_ProcTemp, &aux->CH_Setpoint, arg[14],
               arg[AUX_IDX_EN],
               aux->EN_Sensors+0, aux->EN_Sensors+1, aux->EN_Sensors+2, aux->EN_Sensors+3, 
               aux->EN_Sensors+4, aux->EN_Sensors+5, aux->EN_Sensors+6, arg[15]
               );

  // Check All statuses string
  if(rtn!=36)
  {
      sprintf(reply, "Invalid string for All statuses - argnum = %d\n", rtn);
      return -1;
  }


  // update Focuser Actuator status ///////////////////////////////////////////////

  aux->Statuses[AUX_IDX_FA] = AuxStatusVal(arg[AUX_IDX_FA]);
  if( aux->Statuses[AUX_IDX_FA] == AUX_STATUS_NC )
  {
    ClearAuxData(aux, AUX_IDX_FA);
  }
  else
  {
    // update Focus position & Tip-Tilt angle for high-level control by the user
    // NOTE: aux->FA_ActNums[x] were set to 1, 2, or 3, not overlapped,
    //       AUX_IDX_FA_A1 must be defined to 0, and AUX_IDX_FA_A3 must be 2 
    //       for this routine in pctcs.h

    As = aux->FA_ActPoss[SOUTH] = aux->FA_Positions[aux->FA_ActNums[SOUTH]-1];
    Ae = aux->FA_ActPoss[EAST]  = aux->FA_Positions[aux->FA_ActNums[EAST] -1];
    Aw = aux->FA_ActPoss[WEST]  = aux->FA_Positions[aux->FA_ActNums[WEST] -1];

    aux->FA_ActLims[SOUTH] = aux->FA_Limits[aux->FA_ActNums[SOUTH]-1];
    aux->FA_ActLims[EAST]  = aux->FA_Limits[aux->FA_ActNums[EAST] -1];
    aux->FA_ActLims[WEST]  = aux->FA_Limits[aux->FA_ActNums[WEST] -1];

    foc = (As+Ae+Aw)/3.0;

    aux->FA_TiltNS = (foc-As)/RAC * RAD2SEC;         // if N is higher than S, positive
    aux->FA_TiltEW = (Ae-Aw)/(SQRT3*RAC) * RAD2SEC;  // if E is higher than W, positive
    aux->FA_Focus  = foc;              // focus position at the center of PFI (on axis)

    // check status with position variation

    if( ( aux->Statuses[AUX_IDX_FA] == AUX_STATUS_STANDBY ) && 
        ( fabs(As-As_prev)>MIN_ACTRESOL || fabs(Ae-Ae_prev)>MIN_ACTRESOL || 
          fabs(Aw-Aw_prev)>MIN_ACTRESOL ) )  
      aux->Statuses[AUX_IDX_FA] == AUX_STATUS_RUNNING;  // seems to be running..

    As_prev = As;
    Ae_prev = Ae;
    Aw_prev = Aw;
  }

  // update Dome Shutter status /////////////////////////////////////////////////////

  aux->Statuses[AUX_IDX_DS] = AuxStatusVal(arg[AUX_IDX_DS]);
  if( aux->Statuses[AUX_IDX_DS] == AUX_STATUS_NC ) 
  {
    ClearAuxData(aux, AUX_IDX_DS);
  }
  else
  {
    aux->DS_LimitUpper  = AuxStatusVal(arg[10]);
    aux->DS_LimitLower  = AuxStatusVal(arg[11]);
    aux->DS_LimitSafety = AuxStatusVal(arg[12]);
    aux->DS_AutoSync    = AuxStatusVal(arg[13]);
  }

  // update Filter/Shutter status //////////////////////////////////////////////////

  aux->Statuses[AUX_IDX_FS] = AuxStatusVal(arg[AUX_IDX_FS]);
  if( aux->Statuses[AUX_IDX_FS] == AUX_STATUS_NC ) 
  {
    ClearAuxData(aux, AUX_IDX_FS);
  }
  else
  {
    AuxFSUpdate(aux);
  }
  
  // update Mirror Cover status ///////////////////////////////////////////////////

  aux->Statuses[AUX_IDX_MC] = AuxStatusVal(arg[AUX_IDX_MC]);
  if( aux->Statuses[AUX_IDX_MC] == AUX_STATUS_NC ) 
  {
    ClearAuxData(aux, AUX_IDX_MC);
  }
  else
  {
  }
  
  // update Chiller status ////////////////////////////////////////////////////////

  aux->Statuses[AUX_IDX_CH] = AuxStatusVal(arg[AUX_IDX_CH]);
  if( aux->Statuses[AUX_IDX_CH] == AUX_STATUS_NC ) 
  {
    ClearAuxData(aux, AUX_IDX_CH);
  }
  else
  {
    aux->CH_Cooling = AuxStatusVal(arg[14]);
  }
  
  // update Environment monitor status /////////////////////////////////////////////

  aux->Statuses[AUX_IDX_EN] = AuxStatusVal(arg[AUX_IDX_EN]);
  if( aux->Statuses[AUX_IDX_EN] == AUX_STATUS_NC ) 
  {
    ClearAuxData(aux, AUX_IDX_EN);
  }
  else
  {
    aux->EN_FanRelay = AuxStatusVal(arg[15]);
  }


  // Get the UTC time from the local clock now, for recording updated time ///////

  GetUTCDateTime(&systime);
  sprintf(aux->Date,"%04d-%02d-%02d",systime.year,systime.month,systime.day);
  sprintf(aux->UTC,"%02d:%02d:%06.3f",systime.hour,systime.min,systime.sec);


  // all done

  strcpy(reply, "AUX Telemetry data updated");
  return 0;
}

//-------------------------------------------------------------------------
//
// AuxFilterNameUpdate - Update the names for filter slides
//
// return 0 on success, -1 on errors
// if error, the AUXLink will be set to DOWN in main()
//

int
AuxFilterNameUpdate(auxctrl_t *aux, char *reply)    // v1.3.0
{
  char cmd[SHORT_STR_SIZE];
  char recv[MED_STR_SIZE];
  char fname[4][SHORT_STR_SIZE];
  int rtn, verbose;

  verbose=client.isVerbose;
  client.isVerbose=0;

  // Request filter names
  sprintf(cmd, "FILTERS FNAMES");
  rtn = cmd_acmd(cmd, EXEC, recv);
  if(rtn!=CMD_OK) {
    sprintf(reply, "AUX Filter names update failed (%s)\n", recv);
    client.isVerbose=verbose;
    return -1;
  }

  // Receive filter name string
  rtn = sscanf(recv, "%s %s %s %s", fname[0], fname[1], fname[2], fname[3]);

  // Check argument number
  if(rtn!=4)
  {
      sprintf(reply, "AUX Filter names update failed (argnum=%d)\n", rtn);
      client.isVerbose=verbose;
      return -1;
  }

  strcpy(aux->FS_FilNames[AUX_FS_FNUM_NO  ], AUX_FS_FNAME_NO  );
  strcpy(aux->FS_FilNames[AUX_FS_FNUM_F1  ], fname[0]         );
  strcpy(aux->FS_FilNames[AUX_FS_FNUM_F2  ], fname[1]         );
  strcpy(aux->FS_FilNames[AUX_FS_FNUM_F3  ], fname[2]         );
  strcpy(aux->FS_FilNames[AUX_FS_FNUM_F4  ], fname[3]         );
  strcpy(aux->FS_FilNames[AUX_FS_FNUM_MANY], AUX_FS_FNAME_MANY);

  // all done

  sprintf(reply, "AUX Filter names updated - F1=%s F2=%s F3=%s F4=%s", 
                  fname[0], fname[1], fname[2], fname[3]);
  client.isVerbose=verbose;
  return 0;
}

//-------------------------------------------------------------------------
//
// AuxFSUpdate - Update the AUX Filter/Shutter status from limit switch statuses
//
// - Filter number is updated from status of 8 limit switches for 4 filter slides
// - Filter OpStatus is set to RUNNING if all Limit statuses are AUX_BILIMIT_NO(0)
// - Filter OpStatus is set to ERROR if any filter slide is running longer than 
//   6s + FilterOpTime(filter operation time) defined in runtime HW config
//
// - Status(open/closed status) and OpStatus(operation status) are updated 
//   through monitoring the Limit statuses of both SF(full shutte SH(half shutter)
// - Shutter OpStatus is set to ERROR if the shutter is running longer than
//   3 sec + ShutOpTime(shutter operation time)+3s defined in runtime HW config
//
// << camera shutter operation and status info >>
//
// - Shutter control input: Pin11 - TTL 5V input, pulled up / Pin10 - common
// - OPEN CMD : LOW-->HIGH: The shutter starts opening when the input goes HIGH
// - CLOSE CMD: HIGH-->LOW: The shutter starts closing when the input goes LOW
//
// - NOTE: in the HE box utility operation for shutter open/close, 
//         OPEN  CMD should be commanded when the operation status is STANDBY
//         CLOSE CMD should be commanded when the operation status is OPENING or OPENED
//
// - Limit status SF and SH
//    - SF: limit status of Full shutter / SH: limit status of Half shutter
//    - Limit status value: 0:no, 1:out, 2:in, 3:both (in-->block, out-->open)
//
// - Table 1: Status and OpStatus configuration with Limit status SF/SH
//
//  ----------------------------------------------------------------------------
//   CASE A: exposure time > shutter opening time
//  ----------------------------------------------------------------------------
//   Input --  Limit --  Status  --  OpStatus   (duration time)       Remark
//  ----------------------------------------------------------------------------
//   LOW   --  2  1  --  closed  --  standby    
//   HIGH  --  0  1  --  open    --  opening    (5 sec)
//   HIGH  --  1  1  --  open    --  opened     (ExpTime - 5 sec)
//   LOW   --  1  0  --  open    --  closing    (5 sec)
//   LOW   --  1  2  --  closed  --  reloading  (0.5 sec)
//   LOW   --  0  2  --  closed  --  reloading  (0.1 sec)  possibly
//   LOW   --  1  0  --  closed  --  reloading  (0.1 sec)  possibly
//   LOW   --  0  0  --  closed  --  reloading  (5 sec)
//   LOW   --  2  0  --  closed  --  reloading  (0.1 sec)  possibly
//   LOW   --  0  1  --  closed  --  reloading  (0.1 sec)  possibly
//   LOW   --  2  1  --  closed  --  standby    
//  ----------------------------------------------------------------------------
//
//  ----------------------------------------------------------------------------
//   CASE B: exposure time < shutter opening time
//  ----------------------------------------------------------------------------
//   Input --  Limit --  Status  --  OpStatus   (duration time)       Remark
//  ----------------------------------------------------------------------------
//   LOW   --  2  1  --  closed  --  standby    
//   HIGH  --  0  1  --  open    --  opening    (ExpTime)
//   LOW   --  0  0  --  open    --  opening    (5 sec - ExpTime)    & closing
//   LOW   --  1  0  --  open    --  closing    (ExpTime)
//   LOW   --  1  2  --  closed  --  reloading  (0.5 sec)
//   LOW   --  0  2  --  closed  --  reloading  (0.1 sec)  possibly
//   LOW   --  1  0  --  closed  --  reloading  (0.1 sec)  possibly
//   LOW   --  0  0  --  closed  --  reloading  (5 sec)
//   LOW   --  2  0  --  closed  --  reloading  (0.1 sec)  possibly
//   LOW   --  0  1  --  closed  --  reloading  (0.1 sec)  possibly
//   LOW   --  2  1  --  closed  --  standby
// ---------------------------------------------------------------------------- 
//
// - Table 2: Lookup table for Status/OpStatus with SF/SH
//
// ----------------------------------------------------------------------------
//    SF SH      Status / OpStatus    previous OpStatus or SF SH
// ---------------------------------------------------------------------------- 
//    2  1  -->  closed / standby
//    1  1  -->  open   / opened
//    0  1  -->  open   / opening     standby* or (opening)
//          -->  closed / reloading   reloading* or (reloading)
//    1  0  -->  open   / closing     opened* or opening* or (closing)
//          -->  closed / reloading   reloading* or closing or (reloading)
//    0  0  -->  closed / reloading   1 2* or 1 0* or 1 0 or 0 2 or (0 0)
//          -->  open   / opening     0 1* or 2 1* or (0 0)
//    1  2  -->  closed / reloading
//    0  2  -->  closed / reloading
//    2  0  -->  closed / reloading
// ---------------------------------------------------------------------------- 
//      //original

void
AuxFSUpdate(auxctrl_t *aux)
{
  int flimits;
  int fnum, fopt;
  static int fopt_prev=AUX_FS_FOP_STANDBY;
  static double tick_filter;

  int sf, sh;
  int shut, sopt;
  //static int sf_prev=2, sh_prev=1;          // v1.3.1
  //static int sopt_prev=AUX_FS_SOP_OPENING;  // v1.3.1
  static int sf_prev=0, sh_prev=0;            // v1.3.2
  static int sopt_prev=AUX_FS_SOP_NC;         // v1.3.2
  static double tick_shut;

  // update filter number and status

  if( aux->FS_Limits[AUX_IDX_FS_F1]!=1 && aux->FS_Limits[AUX_IDX_FS_F1]!=2 || 
      aux->FS_Limits[AUX_IDX_FS_F2]!=1 && aux->FS_Limits[AUX_IDX_FS_F2]!=2 || 
      aux->FS_Limits[AUX_IDX_FS_F3]!=1 && aux->FS_Limits[AUX_IDX_FS_F3]!=2 || 
      aux->FS_Limits[AUX_IDX_FS_F4]!=1 && aux->FS_Limits[AUX_IDX_FS_F4]!=2 ) {
    fnum = AUX_UNKNOWN;
    strcpy(aux->FS_FilterName, AUX_FS_FNAME_UNKNOWN);
    fopt = AUX_FS_FOP_RUNNING;
  }
  else {
    flimits =   aux->FS_Limits[AUX_IDX_FS_F1]<< 0 & 0x0000000F
              | aux->FS_Limits[AUX_IDX_FS_F2]<< 4 & 0x000000F0
              | aux->FS_Limits[AUX_IDX_FS_F3]<< 8 & 0x00000F00
              | aux->FS_Limits[AUX_IDX_FS_F4]<<12 & 0x0000F000 ;

    switch(flimits) {
    case 0x00001111: fnum = AUX_FS_FNUM_NO;  break;
    case 0x00001112: fnum = AUX_FS_FNUM_F1;  break;
    case 0x00001121: fnum = AUX_FS_FNUM_F2;  break;
    case 0x00001211: fnum = AUX_FS_FNUM_F3;  break;
    case 0x00002111: fnum = AUX_FS_FNUM_F4;  break;
    default        : fnum = AUX_FS_FNUM_MANY;break;
    }
    strcpy(aux->FS_FilterName, aux->FS_FilNames[fnum]);
    fopt = AUX_FS_FOP_STANDBY;
  }

  // check filter operating timeout

  if(fopt==AUX_FS_FOP_RUNNING) {
    if( fopt_prev!=AUX_FS_FOP_RUNNING && fopt_prev!=AUX_FS_FOP_ERROR ) 
      tick_filter = SysTimestamp();
    else if( (SysTimestamp()-tick_filter) > (aux->FS_FilterOpTime+FOP_TIMEOUT) ) 
      fopt = AUX_FS_FOP_ERROR;
  }

   aux->FS_FilterNum = fnum;
   aux->FS_FilterOpStat = fopt;
   fopt_prev = fopt;

  // update shutter status

  sf = aux->FS_Limits[AUX_IDX_FS_SF];
  sh = aux->FS_Limits[AUX_IDX_FS_SH];

  if( sf==2 && sh==1 ) {
    shut = AUX_FS_SHUT_CLOSED;
    sopt = AUX_FS_SOP_STANDBY;
  }
  else if( sf==1 && sh==1 ) {
    shut = AUX_FS_SHUT_OPEN;
    sopt = AUX_FS_SOP_OPENED;
  }
  else if( sf==0 && sh==1 ) {
    if( sopt_prev==AUX_FS_SOP_STANDBY || sopt_prev==AUX_FS_SOP_OPENING ) {
      shut = AUX_FS_SHUT_OPEN;
      sopt = AUX_FS_SOP_OPENING;
    }
    else if( sopt_prev==AUX_FS_SOP_RELOADING || sopt_prev==AUX_FS_SOP_NC ) {
      shut = AUX_FS_SHUT_CLOSED;
      sopt = AUX_FS_SOP_RELOADING;
    }
    //ignore switch error for temporary optimization at v1.3.2.temp ////////////////
    //else if( sopt_prev == AUX_FS_SOP_STANDBY_FORCED ) {
    //  sopt = AUX_FS_SOP_STANDBY_FORCED;
    //}
    ////////////////////////////////////////////////////////////////////////////////
    // --> disabled at v1.4.0
    else {
      shut = AUX_UNKNOWN;
      sopt = AUX_FS_SOP_ERROR;
    }
  }
  else if( sf==1 && sh==0 ) {
    if( sopt_prev==AUX_FS_SOP_OPENED || sopt_prev==AUX_FS_SOP_OPENING ) {
      shut = AUX_FS_SHUT_OPEN;
      sopt = AUX_FS_SOP_CLOSING;
    }
    else if( sopt_prev==AUX_FS_SOP_RELOADING || sopt_prev==AUX_FS_SOP_NC ) {
      shut = AUX_FS_SHUT_CLOSED;
      sopt = AUX_FS_SOP_RELOADING;
    }
    else if( sopt_prev==AUX_FS_SOP_CLOSING ) {
      shut = AUX_FS_SHUT_OPEN;
      sopt = AUX_FS_SOP_CLOSING;  // more possible..
    }
    else {
      shut = AUX_UNKNOWN;
      sopt = AUX_FS_SOP_ERROR;
    }
  }
  else if( sf==0 && sh==0 ) {
    if( sf_prev==1 && sh_prev==2 || sf_prev==1 && sh_prev==0 || 
        sf_prev==0 && sh_prev==2 ) {
      shut = AUX_FS_SHUT_CLOSED;
      sopt = AUX_FS_SOP_RELOADING;
    }
    else if( sf_prev==0 && sh_prev==1 || sf_prev==2 && sh_prev==1 ) {
      shut = AUX_FS_SHUT_OPEN;
      sopt = AUX_FS_SOP_OPENING;
    }
    else if( sf_prev==0 && sh_prev==0 ) {  //v1.2
      if( sopt_prev==AUX_FS_SOP_RELOADING || sopt_prev==AUX_FS_SOP_NC ) {
        shut = AUX_FS_SHUT_CLOSED;
        sopt = AUX_FS_SOP_RELOADING;
      }
      else if( sopt_prev==AUX_FS_SOP_OPENING ) {
        shut = AUX_FS_SHUT_OPEN;
        sopt = AUX_FS_SOP_OPENING;
      }
      else {
        shut = AUX_UNKNOWN;
        sopt = AUX_FS_SOP_ERROR;
      }
    }
    else if( sopt_prev==AUX_FS_SOP_NC ) {  //v1.2
      shut = AUX_FS_SHUT_CLOSED;
      sopt = AUX_FS_SOP_RELOADING;
    }
    else {
      shut = AUX_UNKNOWN;
      sopt = AUX_FS_SOP_ERROR;
    }
  }
  else if( sf==1 && sh==2 ) {
    shut = AUX_FS_SHUT_CLOSED;
    sopt = AUX_FS_SOP_RELOADING;
  }
  else if( sf==0 && sh==2 ) {
    shut = AUX_FS_SHUT_CLOSED;
    sopt = AUX_FS_SOP_RELOADING;
  }
  else if( sf==2 && sh==0 ) {
    shut = AUX_FS_SHUT_CLOSED;
    sopt = AUX_FS_SOP_RELOADING;
  }
  else {
    shut = AUX_UNKNOWN;
    sopt = AUX_FS_SOP_ERROR;
  }

  // check shutter operating timeout

  if(sopt==AUX_FS_SOP_OPENING) {
    if( sopt_prev!=AUX_FS_SOP_OPENING && sopt_prev!=AUX_FS_SOP_ERROR ) {
      tick_shut = SysTimestamp();
    }
    else if( (SysTimestamp()-tick_shut) > (aux->FS_ShutOpTime+SOP_TIMEOUT) ) {
      //original
      shut = AUX_UNKNOWN;
      sopt = AUX_FS_SOP_ERROR;

      //ignore switch error for temporary optimization at v1.3.2.temp
      //shut = AUX_FS_SHUT_CLOSED;
      //sopt = AUX_FS_SOP_STANDBY_FORCED;
      // --> disabled at v1.4.0
    }
  }

  if(sopt==AUX_FS_SOP_CLOSING) {
    if( sopt_prev!=AUX_FS_SOP_CLOSING && sopt_prev!=AUX_FS_SOP_ERROR ) {
      tick_shut = SysTimestamp();
    }
    else if( (SysTimestamp()-tick_shut) > (aux->FS_ShutOpTime+SOP_TIMEOUT) ) {
      //original
      shut = AUX_UNKNOWN;
      sopt = AUX_FS_SOP_ERROR;

      //ignore switch error for temporary optimization at v1.3.2.temp
      //shut = AUX_FS_SHUT_CLOSED;
      //sopt = AUX_FS_SOP_RELOADING;
      // --> disabled at v1.4.0
    }
  }

  if(sopt==AUX_FS_SOP_RELOADING) {
    if( sopt_prev!=AUX_FS_SOP_RELOADING && sopt_prev!=AUX_FS_SOP_ERROR ) {
      tick_shut = SysTimestamp();
    }
    else if( (SysTimestamp()-tick_shut) > (aux->FS_ShutOpTime+SOP_TIMEOUT) ) {
      //original
      shut = AUX_UNKNOWN;
      sopt = AUX_FS_SOP_ERROR;

      //ignore switch error for temporary optimization at v1.3.2.temp
      //sopt = AUX_FS_SOP_STANDBY_FORCED;
      // --> disabled at v1.4.0
    }
  }

  sf_prev = sf;
  sh_prev = sh;

  aux->FS_ShutStatus = shut;
  aux->FS_ShutOpStat = sopt;
  sopt_prev = sopt;

  // all done
}

//-------------------------------------------------------------------------
//
// AuxStatusVal() - AUX argument decoding (message --> int status definition)
//

int
AuxStatusVal(char *arg)
{
  int status;

       if(strcasecmp(arg,"NC"      )==0) status = AUX_STATUS_NC;
  else if(strcasecmp(arg,"STANDBY" )==0) status = AUX_STATUS_STANDBY;
  else if(strcasecmp(arg,"RUNNING" )==0) status = AUX_STATUS_RUNNING;
  else if(strcasecmp(arg,"ERROR"   )==0) status = AUX_STATUS_ERROR;
  else if(strcasecmp(arg,"OPEN"    )==0) status = AUX_DS_LIMIT_OPENED;
  else if(strcasecmp(arg,"CLOSED"  )==0) status = AUX_DS_LIMIT_CLOSED;
  else if(strcasecmp(arg,"MID"     )==0) status = AUX_DS_LIMIT_MIDDLE;
  else if(strcasecmp(arg,"ACTIVE"  )==0) status = AUX_DS_LIMIT_ACTIVE;
  else if(strcasecmp(arg,"INACTIVE")==0) status = AUX_DS_LIMIT_INACTI;
  else if(strcasecmp(arg,"SUCCESS" )==0) status = AUX_STATUS_STANDBY;
  else if(strcasecmp(arg,"FAILURE" )==0) status = AUX_STATUS_NC;
  else if(strcasecmp(arg,"ON"      )==0) status = ON;  // 1, ENABLED
  else if(strcasecmp(arg,"OFF"     )==0) status = OFF; // 0, DISABLED
  else                                   status = AUX_UNKNOWN;

  return status;
}

//-------------------------------------------------------------------------
//
// AuxStatusArg() - AUX argument encoding (int status definition --> message)
//

char
*AuxStatusArg(int status)
{
  static char arg[16][ARGBUFLEN];
  static int i=0;

  if(i==16) i=0;
  memset(arg[i], 0, ARGBUFLEN);

  switch(status) {
  // Status for connection and operation
  case AUX_STATUS_NC       : strcpy(arg[i], "NC"       ); break;
  case AUX_STATUS_STANDBY  : strcpy(arg[i], "STANDBY"  ); break;
  case AUX_STATUS_RUNNING  : strcpy(arg[i], "RUNNING"  ); break;
  case AUX_STATUS_ERROR    : strcpy(arg[i], "ERROR"    ); break;
  // Status for filter operation (FS_FiltrOp)
  case AUX_FS_FOP_NC       : strcpy(arg[i], "NC"       ); break;
  case AUX_FS_FOP_STANDBY  : strcpy(arg[i], "STANDBY"  ); break;
  case AUX_FS_FOP_RUNNING  : strcpy(arg[i], "RUNNING"  ); break;
  case AUX_FS_FOP_ERROR    : strcpy(arg[i], "ERROR"    ); break;
  // Status for camera shutter open/closed (FS_ShutStatus)
  case AUX_FS_SHUT_OPEN    : strcpy(arg[i], "OPEN"     ); break;
  case AUX_FS_SHUT_CLOSED  : strcpy(arg[i], "CLOSED"   ); break;
  // Status for camera shutter operation (FS_ShutOp)
  case AUX_FS_SOP_NC       : strcpy(arg[i], "NC"       ); break;
  case AUX_FS_SOP_STANDBY_FORCED: // for temporary optimization at v1.3.2.temp
  case AUX_FS_SOP_STANDBY  : strcpy(arg[i], "STANDBY"  ); break;
  case AUX_FS_SOP_OPENING  : strcpy(arg[i], "OPENING"  ); break;
  case AUX_FS_SOP_OPENED   : strcpy(arg[i], "OPENED"   ); break;
  case AUX_FS_SOP_CLOSING  : strcpy(arg[i], "CLOSING"  ); break;
  case AUX_FS_SOP_RELOADING: strcpy(arg[i], "RELOADING"); break;
  case AUX_FS_SOP_ERROR    : strcpy(arg[i], "ERROR"    ); break;
  // Status for dome shutter limits
  case AUX_DS_LIMIT_OPENED : strcpy(arg[i], "OPEN"     ); break;
  case AUX_DS_LIMIT_CLOSED : strcpy(arg[i], "CLOSED"   ); break;
  case AUX_DS_LIMIT_MIDDLE : strcpy(arg[i], "MID"      ); break;
  case AUX_DS_LIMIT_ACTIVE : strcpy(arg[i], "ACTIVE"   ); break;
  case AUX_DS_LIMIT_INACTI : strcpy(arg[i], "INACTIVE" ); break;
  // common
  case AUX_UNKNOWN         : strcpy(arg[i], "UNKNOWN"  ); break;
  default                  : return NULL;
  }

  return arg[i++];
}

//
// *** GENERIC UTILITY FUNCTIONS BEGIN HERE ***
//

//-------------------------------------------------------------------------
//
// StopWatch - measure the time from START to STOP
//
double
StopWatch(int flag, const char *title)  //flag: START/STOP
{
  static double tick;
  double record;

  switch(flag) {
  case START:
    tick = SysTimestamp();
    record = 0.0;
    break;
  case STOP:
    record = SysTimestamp() - tick;
    if(title!=NULL) {
      BLUTEXT;
      printf("%s %6.3f ms\n", title, record*1000.0);
      TXTRESET;
    }
    break;
  }
  return record;
}



//-------------------------------------------------------------------------
//
// GetUTCTime() - read the system's UTC time clock and return the
//                fine-grained time to msec precision
//
// Arguments: none
//
// Description:
//   Reads the system's UTC time clock and returns a pointer to a
//   string with the fine-grained UTC time in the format
//
//      hh:mm:ss.sss
//
//   Based on gf_time() from Stevens, W.R., 1998, Unix Network Programming,
//   Vol 2, Prentice Hall, Figure 15.6, but I make a string, and restrict
//   the output of seconds to ~10 msec rather than usec.
//
// Author:
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2007 June 14
//
// Modification History:
//
//-------------------------------------------------------------------------

char *
GetUTCTime(void)
{
  struct timeval tv;
  static char str[30];
  struct tm *gmt;
  int tmsec;

  gettimeofday(&tv,NULL);
  gmt = gmtime(&tv.tv_sec);
  tmsec = (int)(tv.tv_usec/1000);
  sprintf(str,"%.2i:%.2i:%.2i.%03ld",gmt->tm_hour,gmt->tm_min,
          gmt->tm_sec,tmsec);

  return(str);

}

//-------------------------------------------------------------------------
//
// GetUTCDateTime() - read the system's UTC time clock and return the
//                    fine-grained time to msec precision
//
//

void
GetUTCDateTime(systime_t *datime)
{
  struct timeval tv;
  static char str[30];
  struct tm *gmt;
  int tmsec;

  gettimeofday(&tv,NULL);
  gmt = gmtime(&tv.tv_sec);
  tmsec = (int)(tv.tv_usec/1000);

  datime->year  = gmt->tm_year + 1900;
  datime->month = (gmt->tm_mon)+1;
  datime->day   = gmt->tm_mday;

  datime->hour  = gmt->tm_hour;
  datime->min   = gmt->tm_min;
  datime->sec   = (double)(gmt->tm_sec) + ((double)(tmsec)/1000.0);
}

//-------------------------------------------------------------------------
//
// strupr() - return string replaced with uppercase
//

char *strupr(const char *s) 
{
  static char buf[CMDBUFLEN];
  char *p = buf;

  do *p++ = ( 0x60<*s && *s<0x7B ) ? *s-0x20 : *s;
  while(*s++);

  return buf;
}


// Command Template

/*
int
cmd_xxx(char *args, MsgType msgtype, char *reply)
{

  if (badness)
    return CMD_ERR;
  
  return CMD_OK;
}
*/

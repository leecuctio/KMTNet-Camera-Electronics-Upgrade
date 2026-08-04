//
// commands.c - command action functions for the PC-TCS agent application
//
// Includes the high-level handlers, plus the common action subroutines
// called by each:
//
//    void KeyboardCommand() - handle keyboard commands
//    void SocketCommand()   - handle commands from other ISIS nodes
//
//    int cmd_xxxxx()        - individual command "action" handlers
//
// Does not include the serial port handler used for the incoming PCTCS
// telemetry stream.  That is found in...
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
//   2014 Apr 16: modified for KMTNet TCS
//
//---------------------------------------------------------------------------

#include "pctcs.h"     // PC-TCS Agent application header file
#include "commands.h"  // Command tree header file

extern isisclient_t client;  // global client runtime config table
extern tcsagent_t agent;     // TCS Agent data (this process)
extern pctcs_t tcs;
extern auxctrl_t aux;

int SocketCmdFlag = 0;  // for important message display

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
  char srcID[ISIS_NODESIZE];    // ISIS message sending node ID
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
        printf("OUT: %s\n",msg);
      }
    }
    else {
      REDTEXT;
      printf("No ISIS server active, > command unavailable\n");
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
        printf("ERROR: unknown command '%s'\n",cmd);
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

  // Some simple initializations

  memset(reply,0,sizeof(reply));
  memset(args,0,sizeof(args));
  memset(cmd,0,sizeof(cmd));
  memset(msg,0,ISIS_MSGSIZE);

  // Split the ISIS format message into components

  if (SplitMessage(buf,srcID,destID,&msgtype,msgbody)<0) {
    if (client.isVerbose) {
        //printf("ISIS IN : Malformed message\n");
        printf("ISIS IN : \n");
        rl_refresh_line(0,0);
    }
    return;
  }

  if (client.isVerbose) printf("ISIS IN : %s\n",buf);

  // Immediate action depends on the type of message received as
  // recorded by the msgtype code.

  switch(msgtype) {

  case STATUS:  // we've been sent a status message, echo to console
    printf("%s\n",buf);
    break;
	  
  case DONE:    // command completion message (?), echo to console.
    printf("%s\n",buf);
    break;
	  
  case ERROR:   // error messages, echo to console, get fancy later
    REDTEXT;
    printf("%s\n",buf);
    TXTRESET;
    break;

  case WARNING:
    CYATEXT;
    printf("%s\n",buf);
    TXTRESET;
    break;

  case FATAL:
    MAGTEXT;
    printf("%s\n",buf);
    TXTRESET;
    break;
	  
  case REQ:    // implicit command requests
  case EXEC:   // and executive override commands

    memset(msg,0,ISIS_MSGSIZE);

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
      sprintf(msg,"%s>%s ERROR: Unknown command - '%s'\n",
	          client.ID,srcID,msgbody);
    }
    else {
      SocketCmdFlag = 1;
      switch(cmdtab[icmd].action(args,msgtype,reply)) {

      case CMD_ERR: // command generated an error
        sprintf(msg,"%s>%s ERROR: %s\n",client.ID,srcID,reply);
        break;

      case CMD_NOOP: // command is a no-op, debug/verbose output only
        if (client.isVerbose)
          printf("ISIS IN: %s from ISIS node %s\n",msgbody,srcID);
        break;

      case CMD_OK:  // command executed OK, return reply
      default:
        sprintf(msg,"%s>%s DONE: %s\n",client.ID,srcID,reply);
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
    //BLUTEXT;
    CYATEXT;
    printf("Malformed message received on client port: %s\n",buf);
    TXTRESET;
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
    if (client.useISIS)
      SendToISISServer(&client,msg);
    else 
      ReplyToRemHost(&client,msg);
    if (client.isVerbose) {
      msg[strlen(msg)-1]='\0';
      printf("ISIS OUT: %s\n",msg);
    }
  } // end of reply handling

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
// quit command - allowed only if EXEC from remote hosts (keyboard
//                commands are always EXEC.

int
cmd_quit(char *args, MsgType msgtype, char *reply)
{
  if (msgtype == EXEC) {
    client.KeepGoing=0;
    sprintf(reply,"%s=DISABLED MODE=OFFLINE",client.ID);
  }
  else {
    strcpy(reply,"cannot exec quit command - operation not allowed");
    return CMD_ERR;
  }
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// init - (re)initialize the TCS and AUX links
//

int
cmd_init(char *args, MsgType msgtype, char *reply)
{
  if(cmd_tcsinit(args,msgtype,reply)==CMD_ERR) 
    return CMD_ERR;

  if(cmd_auxinit(args,msgtype,reply)==CMD_ERR) 
    return CMD_ERR;

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// close - close the TCS and AUX links & clear all telemetry data
//

int
cmd_close(char *args, MsgType msgtype, char *reply)
{
  cmd_tcsclose(args, msgtype, reply);
  cmd_auxclose(args, msgtype, reply);

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// arc - toggle the auto recovery mode for TCS and AUX links
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
// info = return application runtime information
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

  // Report TCS link auto reocvery mode setting

  sprintf(reply, "%s TcsArcMode=%s", reply, tcs.ArcMode?"Enabled":"Disabled");

  // Info about the AUX control server

  sprintf(reply, "%s AUXHost=%s:%d"          , reply, aux.Host, aux.PortNum);
  sprintf(reply, "%s AUXTelID=%s AUXSysID=%s", reply, aux.TelID, aux.SysID );

  // Info about the AUX server tcp link

  switch (aux.Link) {
  case AUX_UP  : strcat(reply, " AUXLink=Up"  );break;
  //case AUX_IDLE: strcat(reply, " AUXLink=Idle");break;
  default      : strcat(reply, " AUXLink=DOWN");break;
  }

  sprintf(reply, "%s AuxUpdateInt=%.1f sec"  , reply, aux.UpdateInt);

  // Report AUX HW setting

  sprintf(reply, "%s AuxFilterOpTime=%.1f sec"  , reply, aux.FS_FilterOpTime);
  sprintf(reply, "%s AuxShutOpTime=%.1f sec"  , reply, aux.FS_ShutOpTime);

  // Report AUX link auto reocvery mode setting

  sprintf(reply, "%s AuxArcMode=%s", reply, aux.ArcMode?"Enabled":"Disabled");

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
// version - report application version and compilation info
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
// verbose - toggle enable verbose console output
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
// debug - toggle debugging output
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
// history - show the history list
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

  strcpy(reply, "cannot exec history command - remote operation not allowed");
  return CMD_ERR;

}

//---------------------------------------------------------------------------
//
// help - quick list of available commands
//

int
cmd_help(char *args, MsgType msgtype, char *reply)
{
  if (msgtype==EXEC) {
    printf("\n\n<<KMTNet TCS Agent interactive commands>>\n");
    printf("Client Commands:\n");
    printf("   quit         - quit TCS Agent application (EXEC only)\n");
    printf("   init         - initialize both TCS & AUX links\n");
    printf("   reset        - reset/restart both TCS & AUX links\n");
    printf("   close        - close both TCS & AUX links\n");
    printf("   arc          - toggle the auto recovery mode for TCS & AUX links\n");
    printf("   info         - report client information\n");
    printf("   version      - report client version & compile info\n");
    printf("   verbose      - toggle verbose output mode\n");
    printf("   debug        - toggle debugging output\n");
    printf("   history      - show command history (EXEC only)\n");
    printf("   !!           - repeat last command\n");
    printf("   !cmd         - repeat last command matching 'cmd'\n");
    printf("   help or ?    - view this list (EXEC only)\n\n");
    printf("TCS (PC-TCS Telcom) Commands:\n");
    printf("   tcsinit      - initialize PC-TCS Telcom link\n");
    printf("   tcsreset     - reset/restart PC-TCS Telcom link\n");
    printf("   tcsclose     - close PC-TCS Telcom link\n");
    printf("   tcsarc       - toggle the auto recovery mode for TCS link\n");
    printf("   tcsstatus    - query & return TCS status with the telemetry data\n");
    printf("   tstat        - query & return raw TCS status without keywords\n");
    printf("   traw         - return lastest raw PC-TCS telemetry packet string\n");
    printf("   tsynch       - synch PC-TCS clock with the system UTC clock (EXEC only)\n");
    printf("   tcmd <cmd>   - send a raw PC-TCS command (COMSOFT Native Protocol)\n");
    printf("   tguide       - guiding offset move, args: <ra_offset> <dec_offset>\n");
    printf("   tgoto        - goto to J2000 RA/Dec, args: <ra> <dec>\n");
    printf("   toffset      - offset move RA/Dec, args: <ra_offset> <dec_offset>\n");
    printf("   tstop        - cancel command and stop telescope for commanded motions\n");
    printf("   tdi          - synch the current posidtion with the commanded position\n");
    printf("AUX Control Commands:\n");
    printf("   auxinit      - initialize AUX control link\n");
    printf("   auxreset     - reset/restart AUX control link\n");
    printf("   auxclose     - close AUX control link\n");
    printf("   auxarc       - toggle the auto recovery mode for AUX link\n");
    printf("   auxstatus    - query & return AUX status with the telemetry data\n");
    printf("   astat        - query & return raw AUX status without keywords\n");
    printf("   afstat       - query & return raw AUX Filter/Shutter status\n");
    printf("   acmd <cmd>   - send a raw AUX control remote command\n");
    printf("   afilter      - change filters to arg filter#, arg: <fnum>\n");

    return CMD_NOOP;
  }

  // Can't use HELP unless you're on the console...

  strcpy(reply, "cannot exec help command - remote operation not allowed");
  return CMD_ERR;

}

//---------------------------------------------------------------------------
//
// ping - communication handshaking request
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
// pong - communication handshaking acknowledge
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
  if (client.isVerbose)
    printf("PONG received\n");
  return CMD_NOOP;
}

//
// *** PC-TCS COMMANDS BEGIN HERE ***
//

//---------------------------------------------------------------------------
//
// tcsinit - (re)initialize the PC-TCS serial communications link
//
// Initializes the PCTCS link.  Calls InitPCTCS() to do the dirty
// work.  Later versions may try to do more.
//

int
cmd_tcsinit(char *args, MsgType msgtype, char *reply)
{
  if (InitPCTCS(&tcs,reply)<0)     
    return CMD_ERR;

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
// tcsclose - close the TCS (PC-TCS & Telcom) link
//
// Simply closes the tcp socket for Telcom server & clear TCS data
// and sets tcsLink flag to TCS_DOWN
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
// tcsarc - toggle the auto recovery mode for PC-TCS link
//
// If Enabled, TCS Agent will try to connect to Telcom cover and to recover
// Telcom link and PC-TCS link with the ArcInt (auto recovery try interval)
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
// tcstatus - return TCS status info as a valid IMPv2 message string
//
// relies on the last telemetry received, or just the time/date info
// if the TCS link is down or idle too long.  Note that this is usually
// within 20msec of the query, so the lag is small.
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

    sprintf(reply, "DATE-OBS=%s TIME-OBS=%s TIMESYS=UTC TELEMDATE=%s TELEMTIME=%s"
                   " RA=%s DEC=%s EQUINOX=%s HA=%s ST=%s SECZ=%.2f ALT=%.1f AZ=%.1f"
                   " TCSLINK=Up ARCMODE=%s",
                   curdate, curtime, tcs.Date, tcs.UTC, 
                   tcs.RA, tcs.Dec, tcs.Equinox, tcs.HA, tcs.LST, secz, alt, az,
                   tcs.ArcMode?"Enabled":"Disabled");

    switch (tcs.MoveStatus) {
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
      strcat(reply," TELMOVE=Idle");
      break;
    }

    if (tcs.RALimit)
      strcat(reply," TCSLIMIT=RA");
    else if (tcs.DecLimit)
      strcat(reply," TCSLIMIT=Dec");
    else if (tcs.HorizonLimit)
      strcat(reply," TCSLIMIT=Horizon");

    sprintf(reply, "%s TCSDRIVE=%s COMNUM=%d EXECODE=%c", reply, 
                    tcs.DriveDisable?"Disabled":"Enabled", tcs.ComNum, tcs.ExeCode);

    break;

  case TCS_IDLE:
    sprintf(reply, "DATE-OBS=%s TIME-OBS=%s TIMESYS=UTC TCSLINK=Idle ARCMODE=%s", 
                   curdate, curtime, tcs.ArcMode?"Enabled":"Disabled");
    break;

  default:
    sprintf(reply, "DATE-OBS=%s TIME-OBS=%s TIMESYS=UTC TCSLINK=Down ARCMODE=%s",
                   curdate, curtime, tcs.ArcMode?"Enabled":"Disabled");
    break;

  }

  return CMD_OK;

}

//--------------------------------------------------------------------------
//
// tstat - return TCS status info in lightweight (non-IMPv2 format)
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
//    UP DATE-OBS TIME-OBS JD RA DEC EQUINOX HA ST SECZ TELFOCUS TEMTEMP
//
// TCS_IDLE: PC-TCS link has been idle for longer than the allowed time
//    IDLE DATE-OBS TIME-OBS
//
// TCS_DOWN: PC-TCS link is disabled ("down")
//    DOWN DATE-OBS TIME-OBS
//
// Time system for Time/Date in all cases is UTC.  In the Idle/Down cases,
// the time/date returned are from the system time clock, which hopefully is
// reasonable synchronized with a real time server.
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
    sprintf(reply, "UP %s %s UTC %s %s %s %s %s %s %s %s %s %s %d %c",
                   curdate, curtime, tcs.Date, tcs.UTC, 
                   tcs.RA, tcs.Dec, tcs.Equinox, tcs.HA, 
                   tcs.LST, tcs.SecZ, tcs.Alt, tcs.Az, 
                   tcs.MoveStatus, tcs.ExeCode);
    break;

  case TCS_IDLE:
    sprintf(reply, "IDLE %s %s UTC", curdate, curtime);
    break;

  default:
    sprintf(reply, "DOWN %s %s UTC", curdate, curtime);
    break;

  }

  sprintf(reply, "%s %s", reply, tcs.ArcMode?"ARC.ENABLED":"ARC.DISABLED");

  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// traw - return raw telemetry packet string
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
// tcmd - send a remote PC-TCS command
//

int
cmd_tcmd(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[CMDBUFLEN];  // command buffer
  char argbuf[ARGBUFLEN];
  int nsent, cmdlen, argnum;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check update flag

  if (!tcs.UpdateFlag) {
    strcpy(reply, "too frequent command to Telcom, execution code is not updated yet");
    return CMD_ERR;
  }

  // also need something to send

  if (strlen(args)<=0) {
    strcpy(reply, "usage: tcmd <pctcs_native_command>");
    return CMD_ERR;
  }

  // Assume the command is the argument buffer, we won't try to
  // validate command syntax.

  memset(tcscmd, 0, CMDBUFLEN);
  cmdlen = sprintf(tcscmd, "%s %s %03d %s\n", tcs.TelID, tcs.SysID, PID_REQCMD, args);

  // send the command to Telcom via tcp link

  nsent = send(tcs.FDcmd, tcscmd, cmdlen, 0);
  if (nsent < cmdlen) {
    sprintf(reply, "command send failed - cmd='%s' cmdlen=%d, sentbyte=%d", 
                   args, cmdlen, nsent);
    return CMD_ERR;
  }

  if(client.isVerbose) printf(" TCS OUT: %s", tcscmd);

  // receive the response of command

  memset(tcscmd, 0, CMDBUFLEN);
  cmdlen = recv(tcs.FDcmd, tcscmd, CMDBUFLEN-1, 0);
  if(cmdlen<=0) {
    sprintf(reply, "response recv failed - recvbyte = %d", cmdlen);
    return CMD_ERR;
  }
  tcscmd[cmdlen] = NULL;
  if(client.isVerbose) printf(" TCS IN : %s", tcscmd);

  memset(argbuf, 0, ARGBUFLEN);
  argnum = sscanf(tcscmd, "%*s %*s %*s %s", argbuf);
  if(argnum!=1) {
    sprintf(reply, "unrecognized response - scaned argnum = %d", argnum);
    return CMD_ERR;
  }

  if(strcasecmp(argbuf,"BAD")==0) {
    sprintf(reply, "command execution failed with 'BAD' response");
    return CMD_ERR;
  }

  if(strcasecmp(argbuf,"OK")) {
    strcpy(reply, "unrecognized response - neither 'OK' nor 'BAD'");
    return CMD_ERR;
  }

  tcs.UpdateFlag = 0;

  // all done

  sprintf(reply, "PC-TCS CMD '%s' OK", args);
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tsync - synch the PC-TCS clock with the local system clock,
//         allowed only if EXEC
//
// NOTE: User must check the UT date will not change soon before using this cmd
// since if the time is pass on 24:00 in progress, the date will be not correct.
//

int
cmd_tsync(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[128];  // command buffer
  int rtn;
  systime_t tctime;

  // check command type (EXEC only allowed)

  if (msgtype != EXEC) {
    strcpy(reply, "cannot exec tcssynch command - remote operation not allowed");
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
// tguide - guiding offset move RA/Dec in arcsec
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

  // check argument number

  rtn = sscanf(args, "%lf %lf", &ra_offset, &dec_offset);

  if(rtn<2) {
    strcpy(reply, "usage: tguide <RA_offset> <Dec_offset>");
    strcat(reply, "  /  <RA_offset>: +x.xx  <Dec_offset>: +x.xx (in arcsec)");
    return CMD_ERR;
  }

  // check RA offset value and set operation flag

  if( fabs(ra_offset) > MAX_GUIDEOFFSET_RA ) {
    sprintf(reply, "<RA offset> value is out of range (Max. RA offset = %.3f asec)",
                   MAX_GUIDEOFFSET_RA);
    return CMD_ERR;
  }
  else if( fabs(ra_offset) < tcs.GuideMinOffRA ) 
    raop = 0;  // don't operate RA
  else 
    raop = 1;  // operation

  // check Dec offset value and set operation flag

  if( fabs(dec_offset) > MAX_GUIDEOFFSET_DEC ) {
    sprintf(reply, "<Dec offset> value is out of range (Max. Dec offset = %.3f asec)",
                   MAX_GUIDEOFFSET_DEC);
    return CMD_ERR;
  }
  else if( fabs(dec_offset) < tcs.GuideMinOffDec ) 
    decop = 0;  // don't operate Dec
  else
    decop = 1;  // operate Dec

  // execute RA offset move

  if(raop) {

    // Convert RA offset(arcsec) to PC-TCS guide step(encoder count)

    step = (int)(ra_offset/tcs.GuideStepRA+0.5);

    // Build the STEPRA command string

    memset(tcscmd, 0, sizeof(tcscmd));
    sprintf(tcscmd, "STEPRA %+d", step);

    // Execute the command

    rtn = cmd_tcmd(tcscmd, EXEC, reply);
    if(rtn!=CMD_OK) return CMD_ERR;

  }

  // Execution code update between RA and Dec commands

  if( raop && decop ) {  // if both RA and Dec is operated

    rtn = TcsTelemetry(&tcs, reply);
    if(rtn!=CMD_OK) return CMD_ERR;

  }

  // check Dec offset value and execute

  if(decop) {

    // Convert Dec offset(arcsec) to PC-TCS guide step(encoder count)

    step = (int)(dec_offset/tcs.GuideStepDec+0.5);

    // Build the STEPDEC command string

    memset(tcscmd, 0, sizeof(tcscmd));
    sprintf(tcscmd, "STEPDEC %+d", step);

    // Execute the command

    rtn = cmd_tcmd(tcscmd, EXEC, reply);
    if(rtn!=CMD_OK) return CMD_ERR;

  }

  // all done

  strcpy(reply, "guiding offset move commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tgoto - goto to J2000 RA/Dec, arg: hh/dd:mm:ss.s
//
// NOTE: Input Epoch must be set to J2000 manually on PC-TCS before this command
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
  // ==> Input Epoch must be set to 2000 manually on PC-TCS before this command

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

  // command move to Next position

  sprintf(tcscmd, "MOVNEXT");
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  strcpy(reply, "goto RA/Dec commanded");
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// toffset - offset move RA/Dec, arg: hh/+dd:mm:ss.s
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
// tstop - cancel command and stop commanded motions
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
// tdi - Synchronizes the telescope by forcing the current position to
//       become the same as the commanded position with DECLAREINIT cmd,
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
// auxinit - (re)initialize the AUX control link
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
// auxclose - close the AUX link
//
// Simply closes the serial port and sets tcsLink flag to TCS_DOWN
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
// auxarc - toggle the auto recovery mode for AUX link
//
// If Enabled, TCS Agent will try to connect to AUX control remote server 
// and to recover AUX link with the ArcInt (auto recovery try interval)
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
// auxstatus - return AUX status info as a valid IMPv2 message string
//
// relies on the last telemetry received, or just the AUX Link and 
// ARC mode info if the AUX link is down.  Note that this is usually
// within 20msec of the query, so the lag is small. On the one hand, 
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

    sprintf(reply, "SYSDATE=%s SYSTIME=%s TIMESYS=UTC TELEMDATE=%s TELEMTIME=%s",
                    curdate, curtime, aux.Date, aux.UTC);
    sprintf(reply, "%s AUXLINK=Up ARCMODE=%s", reply, aux.ArcMode?"Enabled":"Disabled");

    sprintf(reply, "%s FILTER/SHUTTER_STATUS=%s", reply, 
                    AuxStatusArg(aux.Statuses[AUX_IDX_FS]));

    if(aux.Statuses[AUX_IDX_FS]!=AUX_STATUS_NC) {
      sprintf(reply, "%s FILTERNUM=%d FILTER_OPSTAT=%s", reply, 
                      aux.FS_FilterNumber, AuxStatusArg(aux.FS_FilterOpStat));
      sprintf(reply, "%s SHUTTER=%s SHUTTER_OPSTAT=%s", reply, 
                      AuxStatusArg(aux.FS_ShutStatus), AuxStatusArg(aux.FS_ShutOpStat));
    }

    sprintf(reply, "%s FOCUSER_STATUS=%s", reply,
                    AuxStatusArg(aux.Statuses[AUX_IDX_FA]));

    if(aux.Statuses[AUX_IDX_FA]!=AUX_STATUS_NC) {
      sprintf(reply, "%s FA1_LIMIT=%d FA2_LIMIT=%d FA3_LIMIT=%d", reply,
                      aux.FA_Limits[AUX_IDX_FA_A1], aux.FA_Limits[AUX_IDX_FA_A2], 
                      aux.FA_Limits[AUX_IDX_FA_A3]);
      sprintf(reply, "%s FA1_POS=%+.3f FA2_POS=%+.3fd FA3_POS=%+.3f", reply,
                      aux.FA_Positions[AUX_IDX_FA_A1], aux.FA_Positions[AUX_IDX_FA_A2], 
                      aux.FA_Positions[AUX_IDX_FA_A3]);
    }

    sprintf(reply, "%s DOMESHUT_STATUS=%s", reply,
                    AuxStatusArg(aux.Statuses[AUX_IDX_DS]));

    if(aux.Statuses[AUX_IDX_DS]!=AUX_STATUS_NC) {
      sprintf(reply, "%s DS_UPPERSHUT=%s DS_LOWERSHUT=%s DS_SAFETYSW=%s DS_ELEVAION=%.1f", 
              reply, AuxStatusArg(aux.DS_LimitUpper), AuxStatusArg(aux.DS_LimitLower), 
                     AuxStatusArg(aux.DS_LimitSafety), aux.DS_Elevation);
    }

    sprintf(reply, "%s MIRRORCOVER_STATUS=%s", reply,
                    AuxStatusArg(aux.Statuses[AUX_IDX_MC]));

    if(aux.Statuses[AUX_IDX_MC]!=AUX_STATUS_NC) {
      sprintf(reply, "%s MC_POS=%d", reply, aux.MC_Position);
    }

    sprintf(reply, "%s CHILLER_STATUS=%s", reply,
                    AuxStatusArg(aux.Statuses[AUX_IDX_CH]));

    if(aux.Statuses[AUX_IDX_CH]!=AUX_STATUS_NC) {
      sprintf(reply, "%s CH_SETPOINT=%.1f CH_PROCTEMP=%.1f", reply,
                      aux.CH_Setpoint, aux.CH_ProcTemp );
    }

    sprintf(reply, "%s ENVIRONMENT_STATUS=%s", reply,
                    AuxStatusArg(aux.Statuses[AUX_IDX_EN]));

    if(aux.Statuses[AUX_IDX_EN]!=AUX_STATUS_NC) {
      for(i=0;i<7;i++) 
        sprintf(reply, "%s EN_S%d=%.1f", reply, i+1, aux.EN_Sensors[i]);
    }

    break;

  default:
    sprintf(reply, "DATE-OBS=%s TIME-OBS=%s TIMESYS=UTC AUXLINK=Down ARCMODE=%s",
                    curdate, curtime, aux.ArcMode?"Enabled":"Disabled");
    break;

  }

  return CMD_OK;

}

//--------------------------------------------------------------------------
//
// astat - return AUX status info in lightweight (non-IMPv2 format)
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
//    UP DATE-OBS TIME-OBS JD RA DEC EQUINOX HA ST SECZ TELFOCUS TEMTEMP
//
// TCS_IDLE: PC-TCS link has been idle for longer than the allowed time
//    IDLE DATE-OBS TIME-OBS
//
// TCS_DOWN: PC-TCS link is disabled ("down")
//    DOWN DATE-OBS TIME-OBS
//
// Time system for Time/Date in all cases is UTC.  In the Idle/Down cases,
// the time/date returned are from the system time clock, which hopefully is
// reasonable synchronized with a real time server.
//

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
    sprintf(reply, "UP %s %s UTC %s %s FS.%s FA.%s DS.%s MC.%s CH.%s EN.%s",
                   curdate, curtime, aux.Date, aux.UTC, 
                   AuxStatusArg(aux.Statuses[AUX_IDX_FS]),
                   AuxStatusArg(aux.Statuses[AUX_IDX_FA]), 
                   AuxStatusArg(aux.Statuses[AUX_IDX_DS]), 
                   AuxStatusArg(aux.Statuses[AUX_IDX_MC]), 
                   AuxStatusArg(aux.Statuses[AUX_IDX_CH]), 
                   AuxStatusArg(aux.Statuses[AUX_IDX_EN]));
    sprintf(reply, "%s FS: %d %s %s %s", reply, 
                    aux.FS_FilterNumber, AuxStatusArg(aux.FS_FilterOpStat), 
                    AuxStatusArg(aux.FS_ShutStatus), AuxStatusArg(aux.FS_ShutOpStat));
    sprintf(reply, "%s FA: %d %d %d %+.3f %+.3f %+.3f", reply,
                      aux.FA_Limits[AUX_IDX_FA_A1], aux.FA_Limits[AUX_IDX_FA_A2], 
                      aux.FA_Limits[AUX_IDX_FA_A3], aux.FA_Positions[AUX_IDX_FA_A1], 
                      aux.FA_Positions[AUX_IDX_FA_A2], aux.FA_Positions[AUX_IDX_FA_A3]);
    sprintf(reply, "%s DS: %s %s %s %.1f", reply, 
                    AuxStatusArg(aux.DS_LimitUpper), AuxStatusArg(aux.DS_LimitLower), 
                    AuxStatusArg(aux.DS_LimitSafety), aux.DS_Elevation);
    sprintf(reply, "%s MC: %d", reply, aux.MC_Position);
    sprintf(reply, "%s %.1f %.1f", reply, aux.CH_Setpoint, aux.CH_ProcTemp);
    sprintf(reply, "%s EN:", reply);
    for(i=0;i<7;i++) sprintf(reply, "%s %.1f", reply, aux.EN_Sensors[i]);

    break;

  default:
    sprintf(reply, "DOWN %s %s UTC", curdate, curtime);
    break;

  }

  sprintf(reply, "%s %s", reply, aux.ArcMode?"ARC.ENABLED":"ARC.DISABLED");

  return CMD_OK;

}

//--------------------------------------------------------------------------
//
// afstat - return Filter/Shutter status info in lightweight (non-IMPv2 format)
//
// Returns a lightweight string in simple for only Filter/Shutter status,
// non-IMPv2 compilant format for simple reading/parsing by machines not humans.
// The format is as follows, depending on the AUX link state:
//
// AUX_UP: AUX link active
//    UP FNUMBER FOPSTAT SSTATUS SOPSTAT
//
// AUX_DOWN: AUX link is disabled ("down")
//    DOWN 
//
// -FNUMBER: current filter number (no:0 / filter 1~4:1~4 / 2 more:5 / unknown:-1)
// -FOPSTAT: filter operation status (NC/STANDBY/RUNNING/ERROR)
// -SSTATUS: shutter status (OPEN/CLOSED/UNKNOWN)
// -SOPSTAT: shutter operation status (NC/STANDBY/OPENING/OPENED/CLOSING/RELOADING/ERROR)
//

int
cmd_afstat(char *args, MsgType msgtype, char *reply)
{
  switch (aux.Link) {

  case AUX_UP:
    sprintf(reply, "UP %d %s %s %s", 
                    aux.FS_FilterNumber, AuxStatusArg(aux.FS_FilterOpStat), 
                    AuxStatusArg(aux.FS_ShutStatus), AuxStatusArg(aux.FS_ShutOpStat));
    break;

  default:
    sprintf(reply, "DOWN");
    break;

  }

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// cmd_acmd - send a AUX ctrl remote command
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
    strcpy(reply, "usage: acmd <subsys> <auxcmd>");
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
  if(client.isVerbose) printf(" AUX OUT: %s", cmd);

  // receive the response of command

  memset(cmd, 0, CMDBUFLEN);
  cmdlen = recv(aux.FD, cmd, CMDBUFLEN-1, 0);
  if(cmdlen<=0) {
    sprintf(reply, "response recv failed - recvbyte = %d", cmdlen);
    return CMD_ERR;
  }
  cmd[cmdlen] = NULL;
  if(client.isVerbose) printf(" AUX IN : %s", cmd);

  // check the response from aux ctrl server

  rtn = sscanf(cmd, "%*s %*s %*s %[^\n]", rsp);
  if( rtn != 1 ) {
    sprintf(reply, "unrecognized response - scaned argnum = %d", rtn);
    return CMD_ERR;
  }

  // common response for general operationg cmd

  if(strcasecmp(rsp,"OK")==0) {
    sprintf(reply, "AUX CMD '%s' OK", args);
    return CMD_OK;
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
// afilter - change filters to commanded filter number with a argument 
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

  // check argument number

  rtn = sscanf(args, "%d", &fnum);

  if(rtn<1) {
    strcpy(reply, "usage: afilter <filter_number>");
    strcat(reply, "  /  <filter_number>: 0 ~ 4 (0:no filter)");
    return CMD_ERR;
  }

  // check filter number

  if( fnum<0 || fnum>4 ) {
    sprintf(reply, "<filter_number> value is must be 0 ~ 4", fnum);
    return CMD_ERR;
  }

  // control 4 filter slides (move the set filter to IN, move other filters to OUT)
  // in pctcs.h, AUX_IDX_FS_F1 must be 0, and AUX_IDX_FS_F4 must be 3 for this

  rtn = CMD_OK;  // rtn is not refered if fnum = 0 and all filter limit = OUT

  for(i=0;i<4;i++) {
    if( (i+1)==fnum && aux.FS_Limits[i]!=AUX_BILIMIT_IN ) {
      sprintf(cmd, "FILTER SET_F%d IN", (i+1));
      rtn = cmd_acmd(cmd, EXEC, reply);
    }
    else if( (i+1)!=fnum && aux.FS_Limits[i]!=AUX_BILIMIT_OUT ) {
      sprintf(cmd, "FILTER SET_F%d OUT", (i+1));
      rtn = cmd_acmd(cmd, EXEC, reply);
    }

    if(rtn!=CMD_OK) {
      sprintf(reply, "%s in filter %d control", reply, (i+1));
      return CMD_ERR;
    }
  }
  
  // all done

  sprintf(reply, "change to filter %d commanded", fnum);
  return CMD_OK;

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

  if( rtn < tcs->MinTelemetryLen ) {  // not enough telemetry data length
    if(rtn>0) tcs->TelcomTick = SysTimestamp();
    sprintf(reply, "telemetry data update failed - recvbyte = %d", rtn);
    return -1;
  }

  // Inspection and Update the telemetry data

  tcs->TelcomTick = SysTimestamp();
  rtn = parse_comsoft(tcs,(tcsbuf+tcs->ReqHedLen));
  if(rtn==0) tcs->PctcsTick = SysTimestamp();    // telemetry data ok
  if(rtn<-4) {                                  // no data
    sprintf(reply, "telemetry data update failed - no data", rtn);
    return -1;
  }

  // all done

  strcpy(reply, "TCS Telemetry data updated");
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
  char cmd[CMDBUFLEN];
  char arg[16][ARGBUFLEN];
  int rtn, cmdlen;
  int argnum, arglen;
  systime_t systime;

  // update status of all subsystems

  sprintf(cmd, "filter status");
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return -1;
  aux->Statuses[AUX_IDX_FS] = AuxStatusVal(reply);

  sprintf(cmd, "focuser status");
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return -1;
  aux->Statuses[AUX_IDX_FA] = AuxStatusVal(reply);

  sprintf(cmd, "shutter status");
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return -1;
  aux->Statuses[AUX_IDX_DS] = AuxStatusVal(reply);

  sprintf(cmd, "mirror_cover status");
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return -1;
  aux->Statuses[AUX_IDX_MC] = AuxStatusVal(reply);

  sprintf(cmd, "chiller status");
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return -1;
  aux->Statuses[AUX_IDX_CH] = AuxStatusVal(reply);

  sprintf(cmd, "environ status");
  rtn = cmd_acmd(cmd, EXEC, reply);
  if(rtn!=CMD_OK) return -1;
  aux->Statuses[AUX_IDX_EN] = AuxStatusVal(reply);

  // update Filter/Shutter data

  if( aux->Statuses[AUX_IDX_FS] == AUX_STATUS_NC ) {
    ClearAuxData(aux, AUX_IDX_FS);
  }
  else {
    sprintf(cmd, "filter limit_filter");
    rtn = cmd_acmd(cmd, EXEC, reply);
    if(rtn!=CMD_OK) return -1;

    rtn = sscanf(reply, "%d %d %d %d", 
                 &aux->FS_Limits[AUX_IDX_FS_F1], &aux->FS_Limits[AUX_IDX_FS_F2],
                 &aux->FS_Limits[AUX_IDX_FS_F3], &aux->FS_Limits[AUX_IDX_FS_F4] );
    if(rtn<4) {
      sprintf(reply, "FS LIMIT_FILTER cmd response error - argnum = %d (<4)\n", rtn);
      return -1;
    }

    sprintf(cmd, "filter limit_shutter");
    rtn = cmd_acmd(cmd, EXEC, reply);
    if(rtn!=CMD_OK) return -1;

    rtn = sscanf(reply, "%d %d", 
                 &aux->FS_Limits[AUX_IDX_FS_SF], &aux->FS_Limits[AUX_IDX_FS_SH] );
    if(rtn<2) {
      sprintf(reply, "FS LIMIT_SHUT cmd response error - argnum = %d (<2)\n", rtn);
      return -1;
    }

    AuxFSUpdate(aux);  
  }


  // update Focuser Actuator data
  if( aux->Statuses[AUX_IDX_FA] == AUX_STATUS_NC) {
    ClearAuxData(aux, AUX_IDX_FA);
  }
  else {
    sprintf(cmd, "focuser limit");
    rtn = cmd_acmd(cmd, EXEC, reply);
    if(rtn!=CMD_OK) return -1;

    rtn = sscanf(reply, "%d %d %d", 
                 &aux->FA_Limits[AUX_IDX_FA_A1], &aux->FA_Limits[AUX_IDX_FA_A2],
                 &aux->FA_Limits[AUX_IDX_FA_A3] );
    if(rtn<3) {
      sprintf(reply, "FA LIMIT cmd response error - argnum = %d (<3)\n", rtn);
      return -1;
    }

    sprintf(cmd, "focuser position");
    rtn = cmd_acmd(cmd, EXEC, reply);
    if(rtn!=CMD_OK) return -1;

    rtn = sscanf(reply, "%lf %lf %lf", 
                 &aux->FA_Positions[AUX_IDX_FA_A1], &aux->FA_Positions[AUX_IDX_FA_A2],
                 &aux->FA_Positions[AUX_IDX_FA_A3] );
    if(rtn<3) {
      sprintf(reply, "FA POSITION cmd response error - argnum = %d (<3)\n", rtn);
      return -1;
    }
  }

  // update Dome Shutter data

  if( aux->Statuses[AUX_IDX_DS] == AUX_STATUS_NC) {
    ClearAuxData(aux, AUX_IDX_DS);
  }
  else {
    sprintf(cmd, "shutter elevation");
    rtn = cmd_acmd(cmd, EXEC, reply);
    if(rtn!=CMD_OK) return -1;

    rtn = sscanf(reply, "%lf", &aux->DS_Elevation);
    if(rtn<1) {
      sprintf(reply, "DS ELEVATION cmd response error - argnum = %d (<1)\n", rtn);
      return -1;
    }

    sprintf(cmd, "shutter limit");
    rtn = cmd_acmd(cmd, EXEC, reply);
    if(rtn!=CMD_OK) return -1;

    rtn = sscanf(reply, "%s %s %s", arg[0], arg[1], arg[2]);
    if(rtn<3) {
      sprintf(reply, "DS LIMITS cmd response error - argnum = %d (<3)\n", rtn);
      return -1;
    }

    aux->DS_LimitUpper  = AuxStatusVal(arg[0]);
    aux->DS_LimitLower  = AuxStatusVal(arg[1]);
    aux->DS_LimitSafety = AuxStatusVal(arg[2]);
  }

  // Mirror Cover

  if( aux->Statuses[AUX_IDX_MC] == AUX_STATUS_NC) {
    ClearAuxData(aux, AUX_IDX_MC);
  }
  else {
    sprintf(cmd, "mirror_cover position");
    rtn = cmd_acmd(cmd, EXEC, reply);
    if(rtn!=CMD_OK) return -1;

    rtn = sscanf(reply, "%d", &aux->MC_Position);
    if(rtn<1) {
      sprintf(reply, "MC POSITION cmd response error - argnum = %d (<1)\n", rtn);
      return -1;
    }
  }

  // Chiller cooling mirror

  if( aux->Statuses[AUX_IDX_CH] == AUX_STATUS_NC) {
    ClearAuxData(aux, AUX_IDX_CH);
  }
  else {
    sprintf(cmd, "chiller get_temp");
    rtn = cmd_acmd(cmd, EXEC, reply);
    if(rtn!=CMD_OK) return -1;

    rtn = sscanf(reply, "%lf", &aux->CH_ProcTemp);
    if(rtn<1) {
      sprintf(reply, "CH GET_TEMP cmd response error - argnum = %d (<1)\n", rtn);
      return -1;
    }

    sprintf(cmd, "chiller get_setpoint");
    rtn = cmd_acmd(cmd, EXEC, reply);
    if(rtn!=CMD_OK) return -1;

    rtn = sscanf(reply, "%lf", &aux->CH_Setpoint);
    if(rtn<1) {
      sprintf(reply, "CH GET_TEMP cmd response error - argnum = %d (<1)\n", rtn);
      return -1;
    }
  }

  // Environment monitor

  if( aux->Statuses[AUX_IDX_EN] == AUX_STATUS_NC) {
    ClearAuxData(aux, AUX_IDX_EN);
  }
  else {
    sprintf(cmd, "environ sensors");
    rtn = cmd_acmd(cmd, EXEC, reply);
    if(rtn!=CMD_OK) return -1;

    rtn = sscanf(reply, "%lf %lf %lf %lf %lf %lf %lf", aux->EN_Sensors+0,
                 aux->EN_Sensors+1, aux->EN_Sensors+2, aux->EN_Sensors+3, 
                 aux->EN_Sensors+4, aux->EN_Sensors+5, aux->EN_Sensors+6 );
    if(rtn<7) {
      sprintf(reply, "EN GET_TEMP cmd response error - argnum = %d (<7)\n", rtn);
      return -1;
    }
  }

  // Get the UTC time from the local clock now, for recording updated time

  GetUTCDateTime(&systime);
  sprintf(aux->Date,"%04d-%02d-%02d",systime.year,systime.month,systime.day);
  sprintf(aux->UTC,"%02d:%02d:%06.3f",systime.hour,systime.min,systime.sec);

  // all done

  strcpy(reply, "AUX Telemetry data updated");
  return 0;
}

//-------------------------------------------------------------------------
//
// AuxFSUpdate - Update the AUX Filter/Shutter status from limit switch statuses
//
// - Filter number is updated with Limit statuses of 4 filter slides
// - Filter OpStatus is set to RUNNING if all Limit statuses are AUX_BILIMIT_NO(0)
// - Filter OpStatus is set to ERROR if any filter slide is running longer
//   than OpTime(operation time)+5s defined in runtime HW config
//
// - Status(open/closed status) and OpStatus(operation status) are updated 
//   through monitoring Limit statuses of both SF(full shutter) & SH(half shutter)
// - Shutter OpStatus is set to ERROR if the shutter is running longer
//   than OpTime(operation time)+5s defined in runtime HW config
//
// << camera shutter operation and status info >>
//
// - Shutter control input Pin11: TTL 5V input, pulled up / Pin10: common
//
// - OPEN CMD : LOW-->HIGH: The shutter starts opening when the input goes HIGH
// - CLOSE CMD: HIGH-->LOW: The shutter starts closing when the input goes LOW
//
// - NOTE:
//   OPEN CMD should be commanded when the operation status is STANDBY
//   CLOSE CMD should be commanded when the operation status is OPENING or OPENED
//
// - Status and OpStatus configuration table
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
// - Limit status:  SF  SH
//     SF: Full shutter limit status, SH: Half shutter limit status
//     Limit status value: 0:no, 1:out, 2:in, 3:both (in-->block, out-->open)
//
// - Lookup table for Status/OpStatus with SF/SH
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
//

void
AuxFSUpdate(auxctrl_t *aux)
{
  int flimits;
  int fnum, fopt;
  static int fopt_prev=AUX_FS_FOP_STANDBY;
  static double tick_filter;

  int sf, sh;
  int shut, sopt;
  static int sf_prev=2, sh_prev=1;
  static int sopt_prev=AUX_FS_SOP_OPENING;
  static double tick_shut;

  // update filter number and status

  if( aux->FS_Limits[AUX_IDX_FS_F1]!=1 && aux->FS_Limits[AUX_IDX_FS_F1]!=2 || 
      aux->FS_Limits[AUX_IDX_FS_F2]!=1 && aux->FS_Limits[AUX_IDX_FS_F2]!=2 || 
      aux->FS_Limits[AUX_IDX_FS_F3]!=1 && aux->FS_Limits[AUX_IDX_FS_F3]!=2 || 
      aux->FS_Limits[AUX_IDX_FS_F4]!=1 && aux->FS_Limits[AUX_IDX_FS_F4]!=2 ) {
    fnum = AUX_UNKNOWN;
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
    fopt = AUX_FS_FOP_STANDBY;
  }

  // check filter operating timeout

  if(fopt==AUX_FS_FOP_RUNNING) {
    if( fopt_prev!=AUX_FS_FOP_RUNNING && fopt_prev!=AUX_FS_FOP_ERROR ) 
      tick_filter = SysTimestamp();
    else if( (SysTimestamp()-tick_filter) > (aux->FS_FilterOpTime+FOP_TIMEOUT) ) 
      fopt = AUX_FS_FOP_ERROR;
  }

   aux->FS_FilterNumber = fnum;
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
    else if( sopt_prev==AUX_FS_SOP_RELOADING ) {
      shut = AUX_FS_SHUT_CLOSED;
      sopt = AUX_FS_SOP_RELOADING;
    }
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
    else if( sopt_prev==AUX_FS_SOP_RELOADING ) {
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
    else if( sf==0 && sh==0 ) {
      if(sopt_prev==AUX_FS_SOP_RELOADING) {
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
    if( sopt_prev!=AUX_FS_SOP_OPENING && sopt_prev!=AUX_FS_SOP_ERROR ) 
      tick_shut = SysTimestamp();
    else if( (SysTimestamp()-tick_shut) > (aux->FS_ShutOpTime+SOP_TIMEOUT) ) 
      sopt = AUX_FS_SOP_ERROR;
  }

  if(sopt==AUX_FS_SOP_CLOSING) {
    if( sopt_prev!=AUX_FS_SOP_CLOSING && sopt_prev!=AUX_FS_SOP_ERROR ) 
      tick_shut = SysTimestamp();
    else if( (SysTimestamp()-tick_shut) > (aux->FS_ShutOpTime+SOP_TIMEOUT) ) 
      sopt = AUX_FS_SOP_ERROR;
  }

  if(sopt==AUX_FS_SOP_RELOADING) {
    if( sopt_prev!=AUX_FS_SOP_RELOADING && sopt_prev!=AUX_FS_SOP_ERROR ) 
      tick_shut = SysTimestamp();
    else if( (SysTimestamp()-tick_shut) > (aux->FS_ShutOpTime+SOP_TIMEOUT) ) 
      sopt = AUX_FS_SOP_ERROR;
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
// AuxStatusVal() - AUX argument decoding
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
  else                                   status = AUX_UNKNOWN;

  return status;
}

//-------------------------------------------------------------------------
//
// AuxStatusArg() - AUX argument encoding
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
  case AUX_STATUS_ERROR    : strcpy(arg[i], "STANDBY"  ); break;
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
  case AUX_FS_SOP_STANDBY  : strcpy(arg[i], "STANDBY"  ); break;
  case AUX_FS_SOP_OPENING  : strcpy(arg[i], "OPENING"  ); break;
  case AUX_FS_SOP_OPENED   : strcpy(arg[i], "OPENED"   ); break;
  case AUX_FS_SOP_CLOSING  : strcpy(arg[i], "CLOSING"  ); break;
  case AUX_FS_SOP_RELOADING: strcpy(arg[i], "RELOADING"); break;
  case AUX_FS_SOP_ERROR    : strcpy(arg[i], "ERROR    "); break;
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
StopWatch(int flag, const char *title)  //flag: START/STOP (no LAP..^^;)
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
//                fine-grained time to msec precision
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
// using toupper in ctype.h
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

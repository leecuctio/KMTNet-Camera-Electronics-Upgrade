//
// commands.c - command action functions for the PC-TCS agent application
//
// Includes the high-level handlers, plus the common action subroutines
// called by each:
//
//    void keyboardCmd() - handle keyboard commands
//    void socketCmd()   - handle commands from other ISIS nodes
//
//    int cmd_xxxxx()        - individual command "action" handlers
//
// Does not include the serial port handler used for the incoming PCTCS
// telemetry stream.  That is found in...
//
// Author:
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2004 February 17
//
// Modification History:
//   2013 Mar 29: Added simulation mode hooks.  Still primitive [rwp/osu]
//
//---------------------------------------------------------------------------

#include "pctcs.h"     // PC-TCS Agent application header file
#include "commands.h"  // Command tree header file

#include <readline/readline.h>  // Gnu readline utility
#include <readline/history.h>   // Gnu history utility

//---------------------------------------------------------------------------
//
// keyboardCmd() - process a command from the keyboard
//
// Calls the low-level cmd_xxx() routines for most commands, as
// well as handling commands particular to the console keyboard
//
// This version of the KeyboardCommand() function is setup as
// a callback for readline(), like TTYHandler in the main ISIS
// server application
//

void
keyboardCmd(char *line)
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
// socketCmd() - process a message or command from an ISIS server/client
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
socketCmd(char *buf)
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
    if (client.isVerbose)
      printf("\nISIS IN: %s\n",buf);
    return;
  }
        
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
      sprintf(msg,"%s>%s ERROR: Unknown command - %s\n",
	      client.ID,srcID,msgbody);
    }
    else {
      switch(cmdtab[icmd].action(args,msgtype,reply)) {

      case CMD_ERR: // command generated an error
	sprintf(msg,"%s>%s ERROR: %s\n",client.ID,srcID,reply);
	break;

      case CMD_NOOP: // command is a no-op, debug/verbose output only
	if (client.isVerbose)
	  printf("IN: %s from ISIS node %s\n",msgbody,srcID);
	break;

      case CMD_OK:  // command executed OK, return reply
      default:
	sprintf(msg,"%s>%s DONE: %s\n",client.ID,srcID,reply);
	break;
	
      } // end of switch on cmdtab.action()
    }

    // An incoming PING requires special handling - it is an exception
    // to the usual messaging syntax since PONG is sent in reply 

    if (strcasecmp(cmd,"PING") == 0)
      sprintf(msg,"%s>%s %s\r",client.ID,srcID,reply);
      
    break;

  default:  // we don't know what we got, print for debugging purposes
    BLUTEXT;
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
//
// cmd_xxx() action functions
//
// Add new functions at the end.  To be available, they must be entered
// as "action" members in the Commands struct for this application (see
// commands.h)
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
    sprintf(reply,"quit %s=DISABLED MODE=OFFLINE",client.ID);
  }
  else {
    strcpy(reply,"quit Cannot exec quit command - operation not allowed");
    return CMD_ERR;
  }
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// ports - print port table
//

int
cmd_ports(char *args, MsgType msgtype, char *reply)
{
  int i;

  if (tcs.fd < 0)
    strcpy(reply,"ports No PC-TCS serial port is connected.");
  else
    sprintf(reply,"ports TCSPort=%s",tcs.port);

  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// version - report application version and compilation info
//

int
cmd_version(char *args, MsgType msgtype, char *reply)
{
  
  sprintf(reply,"version PCTCSAgent Version=(%s) CompileDate=%s CompileTime=%s",
	  APP_VERSION,APP_COMPDATE,APP_COMPTIME);
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
    sprintf(reply,"debug super-verbose debugging output disabled");
  }
  else {
    client.Debug = 1;
    sprintf(reply,"debug super-verbose debugging output enabled");
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

  sprintf(reply,"info %s ID=%s Host=%s:%d",
	  APP_VERSION, client.ID, client.Host, client.Port);

  // if configured as an ISIS client, report this and the ISIS host:port info,
  // otherwise if standalone, report that, and the host:port of the last
  // remote host to send us something, if known.

  if (client.useISIS) {
    sprintf(reply,"%s Mode=ISISClient ISIS=%s ISISHost=%s:%d",reply,
	    client.isisID,client.isisHost,client.isisPort);
  }
  else {
    if (strlen(client.remHost)>0)
      sprintf(reply,"%s Mode=STANDALONE RemHost=%s:%d",reply,
	      client.remHost,client.remPort);
    else
      strcat(reply," Mode=STANDALONE");

  }

  // Info about the PC-TCS port

  sprintf(reply,"%s TCSPort=%s", reply, tcs.port);

  switch (tcs.link) {
  case TCS_UP:
    sprintf(reply,"%s TCSLink=Up LastTelem=%.6f sec",reply,tcs.idle);
    sprintf(reply,"%s IdleTimeout=%d sec",reply,tcs.idleTime);
    break;

  case TCS_IDLE:
    sprintf(reply,"%s TCSLink=Idle IdleTime=%.2f sec",reply,tcs.idle);
    sprintf(reply,"%s IdleTimeout=%d sec",reply,tcs.idleTime);
    break;

  default:
    if (tcs.simMode)
      strcat(reply," TCSLink=SIM");
    else
      strcat(reply," TCSLink=DOWN");
    break;
  }

  // Report application runtime flags

  sprintf(reply,"%s %s %s",reply,
	  ((client.isVerbose) ? "Verbose" : "Concise"),
	  ((client.Debug) ? "+DEBUG" : "-DEBUG"));
	 
  // Finally, report the application's runtime config file

  sprintf(reply,"%s rcfile=%s exe=%s UserID=%s",
	  reply,client.rcFile,tcs.exeFile,tcs.userID);

  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// help - quick list of available commands
//

int
cmd_help(char *args, MsgType msgtype, char *reply)
{
  if (msgtype==EXEC) {
    printf("\nPCTCSAgent interactive commands:\n");
    printf("PC-TCS Commands:\n");
    printf("   tcinit         - initialize PC-TCS comm link\n");
    printf("   tcclose        - close PC-TCS comm link\n");
    printf("   tcstatus       - query & return TCS status info\n");
    printf("   tcsynch        - synch the PC-TCS clock with the system UTC clock\n");
    printf("   tcscmd <cmd>   - send a raw PC-TCS command\n");
    printf("   tstat          - raw TCS status query\n");
    printf("   reset          - reset/restart PC-TCS comm link\n");
    printf("   idletime <sec> - set/query TCS telemetry idle timeout interval\n");
    printf("   sip            - sip raw telemetry stream (EXEC only)\n");
    printf("Client Commands:\n");
    printf("   quit           - quit application\n");
    printf("   info           - report client information\n");
    printf("   version        - report client version & compile info\n");
    printf("   verbose        - toggle verbose output mode\n");
    printf("   debug          - toggle debugging output\n");
    printf("   history        - show command history\n");
    printf("   !!             - repeat last command\n");
    printf("   !cmd           - repeat last command matching 'cmd'\n");
    printf("   help or ?      - view this list\n\n");
    return CMD_NOOP;
  }

  // Can't use HELP unless you're on the console...

  strcpy(reply,"Cannot exec help command - remote operation not allowed");
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
// PINGs are actually handled separately in the socketCmd() handler
// (nothing is done by the keyboardCmd() handler) because the
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

  strcpy(reply,"Cannot exec history command - remote operation not allowed");
  return CMD_ERR;

}

//
// *** PC-TCS COMMANDS BEGIN HERE ***
//
//---------------------------------------------------------------------------
//
// cmd_tcinit - (re)initialize the PC-TCS serial communications link
//
// Initializes the PCTCS link.  Calls initPCTCS() to do the dirty
// work.  Later versions may try to do more.
//

int
cmd_tcinit(char *args, MsgType msgtype, char *reply)
{
  if (tcs.link == TCS_SIM) {
    strcpy(reply,"tcinit PC-TCS Link Initialized [SIM]");
    return CMD_OK;
  }

  if (initPCTCS(&tcs,reply)<0)
    return CMD_ERR;
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// tcclose - close the PC-TCS serial communications link
//
// Simply closes the serial port and sets tcsLink flag to TCS_DOWN
//

int
cmd_tcclose(char *args, MsgType msgtype, char *reply)
{
  int istat;

  if (tcs.simMode) {
    sprintf(reply,"tcclose PC-TCS Link Closed [SIM]");
    return CMD_OK;
  }

  if (tcs.fd > 0) {
    istat = close(tcs.fd);
    tcs.fd = -1;
  }
  tcs.link = TCS_DOWN;
  sprintf(reply,"tcclose PC-TCS Link Closed");
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// cmd_setidle - set the communication idle timeout interval in seconds
//
// If the timeout command was given w/o arguments, it returns the
// current timeout interval, otherwise it sets the timeout to the interval
// specified by the first command-line argument.
//
// The idle timeout is the time interval over which if we receive no
// PC-TCS telemetry (which normally comes in at a rate of 5 telemetry
// "packets" per second), we judge that the PC-TCS telemetry has 
// become "idle", and set the tcsLink flag accordingly.  This allows
// us to distinguish between "TCS no initialized" ("down") and "TCS
// has nothing to say, and hasn't said anything in >idletime seconds"
// ("idle").
//

int
cmd_setidle(char *args, MsgType msgtype, char *reply)
{
  char argbuf[32];

  if (strlen(args)<=0) {
    sprintf(reply,"idletime IdleTime=%d seconds",tcs.idleTime);
  }
  else {
    GetArg(args,1,argbuf);
    tcs.idleTime = atoi(argbuf);
    if (tcs.idleTime >= 1) {
      sprintf(reply,"idletime IdleTimeout=%d seconds",tcs.idleTime);
    }
    else {
      sprintf(reply,"idletime Invalid comm idle timeout '%s'",argbuf);
      return CMD_ERR;
    }
  }
  return CMD_OK;

}

//--------------------------------------------------------------------------
//
// cmd_tcstatus - return TCS status info as a valid IMPv2 message string
//
// relies on the last telemetry received, or just the time/date info
// if the TCS link is down or idle too long.  Note that this is usually
// within 20msec of the query, so the lag is small.
//

int
cmd_tcstatus(char *args, MsgType msgtype, char *reply)
{
  float secz;
  int telfoc;
  int teltemp;

  strcpy(tcs.utcDate,UTCDate());
  strcpy(tcs.utcTime,getUTCTime());
  strcpy(tcs.UTC,getUTCTime());
 
  switch (tcs.link) {

  case TCS_UP:
    secz = atof(tcs.secZD);
    telfoc = atoi(tcs.Focus);
#if defined(__Lab)
    sprintf(reply,"tcstatus DATE-OBS=%s TIME-OBS=%s TIMESYS=UTC JD=%s RA=%s DEC=%s EQUINOX=%s HA=%s ST=%s SECZ=%.2f TELFOCUS=%d TCSLINK=Enabled",
            tcs.utcDate, tcs.utcTime, tcs.JD, tcs.RA, tcs.Dec, tcs.Equinox, tcs.HA, 
            tcs.LST, secz, telfoc);

#elif defined(__Yale)
    sprintf(reply,"tcstatus DATE-OBS=%s TIME-OBS=%s TIMESYS=UTC JD=%s RA=%s DEC=%s EQUINOX=%s HA=%s ST=%s SECZ=%.2f TELFOCUS=%d TCSLINK=Enabled",
            tcs.utcDate, tcs.utcTime, tcs.JD, tcs.RA, tcs.Dec, tcs.Equinox, tcs.HA, 
            tcs.LST, secz, telfoc);

#elif defined(__CTIO13m)    
    teltemp = atoi(tcs.Temp);
    sprintf(reply,"tcstatus DATE-OBS=%s TIME-OBS=%s TIMESYS=UTC JD=%s RA=%s DEC=%s EQUINOX=%s HA=%s ST=%s SECZ=%.2f TELFOCUS=%d TELTEMP=%d TCSLINK=Enabled",
            tcs.utcDate, tcs.utcTime, tcs.JD, tcs.RA, tcs.Dec, tcs.Equinox, tcs.HA, 
            tcs.LST, secz, telfoc, teltemp);
#endif

    switch (tcs.moveStatus) {
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
    else
      strcat(reply," TCSLIMIT=None");

    break;

  case TCS_IDLE:
    sprintf(reply,"tcstatus DATE-OBS=%s TIME-OBS=%s TIMESYS=UTC TCSLINK=Idle",
            tcs.utcDate, tcs.utcTime);
    break;

  case TCS_SIM:
    sprintf(reply,"tcstatus DATE-OBS=%s TIME-OBS=%s TIMESYS=UTC",
            tcs.utcDate, tcs.utcTime);
    sprintf(reply,"%s JD=1234567.89000 RA=01:02:03.4 DEC=-22:33:44.5 EQUINOX=2000.0 HA=-01:01:01.1 ST=02:03:04.5 SECZ=1.00 TELFOCUS=12345 TELTEMP=34.5 TCSLINK=SIM TELMOVE=Idle TCSLIMIT=None",reply);

    break;

  default:
    sprintf(reply,"tcstatus DATE-OBS=%s TIME-OBS=%s TIMESYS=UTC TCSLINK=Disabled",
            tcs.utcDate, tcs.utcTime);
    break;

  }

  return CMD_OK;

}

//--------------------------------------------------------------------------
//
// cmd_tstat - return TCS status info in lightweight (non-IMPv2 format)
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
 
  strcpy(tcs.utcDate,UTCDate());
  strcpy(tcs.utcTime,getUTCTime());
  strcpy(tcs.UTC,getUTCTime());

  switch (tcs.link) {

  case TCS_UP:
    sprintf(reply,"UP %s %s %s %s %s %s %s %s %s %s %s",
            tcs.utcDate, tcs.utcTime, tcs.JD, tcs.RA, tcs.Dec, tcs.Equinox, tcs.HA, 
            tcs.LST, tcs.secZD, tcs.Focus, tcs.Temp);
    break;

  case TCS_IDLE:
    sprintf(reply,"IDLE %s %s",tcs.utcDate, tcs.utcTime);
    break;

  default:
    sprintf(reply,"DOWN %s %s",tcs.utcDate, tcs.utcTime);
    break;

  }

  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// cmd_sip - "sip" the raw TCS telemetry stream
//
// They asked for it...
//

int
cmd_sip(char *args, MsgType msgtype, char *reply)
{
  
  switch (tcs.link) {

  case TCS_UP:
    strcat(reply,tcs.Raw);
    tcs.doSip = 1;
    break;

  case TCS_DOWN:
    sprintf(reply,"sip TCSLink is DOWN, telemetry stream unavailable");
    tcs.doSip = 0;
    break;

  case TCS_IDLE:
    sprintf(reply,"sip TCSLink is IDLE, telemetry stream unavailable");
    tcs.doSip = 0;
    break;

  case TCS_SIM:
    sprintf(reply,"sip PC-TCS Agent running in SIM mode, sip command unavailable");
    tcs.doSip = 0;
    break;

  }
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// cmd_tcscmd - send a remote PC-TCS command
//

int
cmd_tcscmd(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[128];  // command buffer
  char argbuf[32];
  int nsent;

  // Must be up (or in simulation mode) to send commands...

  if (tcs.link != TCS_UP && tcs.link != TCS_SIM) {
    sprintf(reply,"tcscmd TCSLink is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // ... and you also need something to send ...

  if (strlen(args)<=0) {
    strcpy(reply,"Usage: tcscmd pc-tcs_command");
    return CMD_ERR;
  }

  // Simulation mode is easy...

  if (tcs.link == TCS_SIM) {
    sprintf(reply,"tcscmd Sent PC-TCS Command '%s'",args);
    return CMD_OK;
  }

  // Assume the command is the argument buffer, we won't try to
  // validate command syntax.

  memset(tcscmd,0,sizeof(tcscmd));
  strcpy(tcscmd,args);
  comsoftChkSum(tcscmd);  // append checksum

  // send the command (write to port) 

  nsent = write(tcs.fd,tcscmd,strlen(tcscmd));
  if (nsent < 0) {
    REDTEXT;
    sprintf(reply,"tcscmd Cannot send command '%s' to PC-TCS port - %s",
	    args,strerror(errno));
    TXTRESET;
    return CMD_ERR;
  }

  // all done (?)

  sprintf(reply,"tcscmd Sent PC-TCS Command '%s'",args);
  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// cmd_tcsynch - synch the PC-TCS clock with the local system clock
//

int
cmd_tcsynch(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[128];  // command buffer
  char argbuf[32];
  int nsent;

  // gotta be up to send commands

  if (tcs.link != TCS_UP && tcs.link != TCS_SIM) {
    sprintf(reply,"tcsynch TCSLink is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // Get the system date/time now

  getUTCDateTime(&tctime);

  // If simulation mode, return now

  if (tcs.simMode) {
    sprintf(tcscmd,"SETDATE %.2d/%.2d/%.2d",tctime.year,tctime.month,tctime.day);
    sprintf(reply,"tcsynch sent pc-tcs the commands '%s'",tcscmd);
    sprintf(tcscmd,"SETTIME %.2d%.2d%05.2f",tctime.hour,tctime.min,tctime.sec);
    sprintf(reply,"%s and '%s' [SIM]",reply,tcscmd);
    return CMD_OK;
  }

  // Build the SETDATE command string

  memset(tcscmd,0,sizeof(tcscmd));
  sprintf(tcscmd,"SETDATE %.2d/%.2d/%.2d",tctime.year,tctime.month,tctime.day);
  comsoftChkSum(tcscmd);  // append checksum

  // Send the command (write to port) 

  nsent = write(tcs.fd,tcscmd,strlen(tcscmd));
  if (nsent < 0) {
    REDTEXT;
    sprintf(reply,"tcsynch Cannot send command '%s' to PC-TCS port - %s",
	    args,strerror(errno));
    TXTRESET;
    return CMD_ERR;
  }

  // Build the SETTIME command string

  getUTCDateTime(&tctime);
  memset(tcscmd,0,sizeof(tcscmd));
  sprintf(tcscmd,"SETTIME %.2d%.2d%05.2f",tctime.hour,tctime.min,tctime.sec);
  comsoftChkSum(tcscmd);  // append checksum

  // Send the command (write to port) 

  nsent = write(tcs.fd,tcscmd,strlen(tcscmd));
  if (nsent < 0) {
    REDTEXT;
    sprintf(reply,"tcsynch Cannot send command '%s' to PC-TCS port - %s",
	    args,strerror(errno));
    TXTRESET;
    return CMD_ERR;
  }

  // all done (?)

  strcpy(reply,"tcsynch Synched PC-TCS with the local host UTC clock");
  return CMD_OK;

}

//-------------------------------------------------------------------------
//
// getUTCTime() - read the system's UTC time clock and return the
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
getUTCTime(void)
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
// getUTCDateTime() - read the system's UTC time clock and return the
//                fine-grained time to msec precision
//
//

void
getUTCDateTime(systime_t *datime)
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


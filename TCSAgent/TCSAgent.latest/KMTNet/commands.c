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
//   2015 Feb 13: FILTNUM/FILTNAME added at the end of FS Info in AUXSTATUS, 
//                temporary for smooth camera software update and testing (v1.4.6)
//   2015 Jul 08: Debugging for tgoto, BLG offset correction routine added (v1.5.0)
//   2015 Jul 21: RA/Dec object catalog import & quiry function added, tmoffset debugging
//                tmobject function added for using catalog data (v1.5.1)
//   2015 Jul 22: debugging tmradec(), tmelaz() created, tguide() debugging completed (v1.5.2)
//   2015 Jul 23: degugging tmradec() about ha string (v1.5.3)
//                modified for appling dHA of destination (v1.5.4)
//   2015 Aug 27: pointing modeling utilities pmo(oo)/pmc(cc) added (v1.5.5)
//   2015 Oct 15: _(v)msgout() added & applied for message output on console and logfile 
//                Put the terminator and set the length to BIG_STR_SIZE on Socket cmd buf (v1.6.0)
//   2015 Oct 17: _tcslog()/_auxlog() added for logging TSTAT/ASTAT, 
//                FS_CmdFilNum setting routine in cmd_afilter() and FS_FilterName(FILTER keyword)
//                setting routine with FS_CmdFilNum in AuxFSUpdate() to prevent UNKNOWN problem, 
//                old keywords FILTNUM and FILTNAME removed in AUXSTATUS message string (v1.6.1.0)
//   2016 Jan 15: logging the raw TCS telemetry string in tstat log and event log (v1.6.1.1)
//   2016 Sep 22: debugging for Cat coord input error with modifying trans1060() (v1.6.2)
//   2017 Jun 08: changed "TRAW STRING:" to "TRAW STR:" in _msgout() for event log's legibility
//                made low acceptancy of telemetry data with return of parse_comsoft() 
//                added logging DataChkMsg in GetTstatStr(), _msgout() and _vmsgout()
//                changed error checking/handling for new Rtn of parse_comsoft() (v1.6.3)
//   2017 Jun 09: trans1060() modified for debugging 59.999 error of dSec value (v1.6.3)
//   2017 Jun 14: a new argument nDP in trans1060() for rounding dSec down to the designated 
//                decimal places for debugging the round off errors in sprintf() (v1.6.4)
//   2017 Jun 15: trans1060() modified using tricks with a tunning term 
//                and upgraded with new conversion code (v1.6.4)
//   2017 Jun 19: trans1060() modified and tunned with robust and simplified code (v1.6.4)
//   2017 Jun 20: modified for telemetry data decoding routine with recalling parse_comsoft() 
//                in case of the telemetry data/string error, and logging the history (v1.6.5)
//                modified for TSTAT/TCSSTATUS string encoding routine with string length inspection
//                and recalling sprintf() to build the string, and logging the histories (v1.6.5)
//   2017 Jun 22: cmd_catalog() and _vmsgout() modified for some minor debugging and improvement 
//                for message output (v1.6.6.0)
//   2017 Jul 26: Lables of LimitStatus in TCSSTATUS added for simultaneous events (v1.6.6.1)
//                line history addition roution improved to skip repetitions (v1.6.6.2)
//   2017 Jul 28: Long string array buffers' length reviewed and corrected (v1.6.6.4)
//                Checking for size in memset() functions, Debugging for using ISIS Lib. funcs, 
//                Line history upgrade with last entry number, "history #/-c" available (v1.6.6.5)
//                Readline prompt reset routine improved both in key cmd proc and socket cmd proc
//                with selectively disabling rl_refresh_line(0,0) in _msgout()/_vmsgout() (v1.6.6.5)
//   2017 Jul 31: Checking for length of string buffer in TCS/AUX cmd proc functions (v1.6.6.6)
//                cmd_tsync() code modified, debugging/checking prompt reset with NC error (v1.6.6.6)
//   2017 Dec 10: Offset correction to move to K/M/T from N (v1.6.7)
//                Offset correction to move to M/T/N from K (v1.6.8)
//
//
//   Update plan: 
//     - SendStatus() added (v1.7.0)
//     - fttgotop()/dtiltp() added for Tip/Tilt adjustment with polar coordsys 
//       -- held on
//
//
//------------------------------------------------------------------------------

#include "pctcs.h"     // PC-TCS Agent application header file
#include "commands.h"  // Command tree header file

extern isisclient_t client;  // global client runtime config table
extern tcsagent_t agent;     // TCS Agent data (this process)
extern pctcs_t tcs;
extern auxctrl_t aux;

int KeyCmdFlag = 0;     // to disable readline prompt reset in _msgout()/_vmsgout()
int SocketCmdFlag = 0;  // for important message display
int TcsStatusFlag = 0;  // for logging the traw string in event log, v1.6.2
char SourceID[STRLEN_ISISNODE];

//// **NOTE: Big array occur memory problems on global area


//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
//
// Command event callback and handling functions
//

//------------------------------------------------------------------------------
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
  ////  // ISIS message handling stuff
  ////
  ////  char msg[ISIS_MSGSIZE];       // ISIS message buffer
  ////  char destID[ISIS_NODESIZE];   // ISIS message destination node ID
  ////  char msgbody[ISIS_MSGSIZE];   // ISIS message body
  ////
  ////  // command components (command arguments and reply string)
  ////  
  ////  char cmd[BIG_STR_SIZE];      // command string (oversized)
  ////  char args[BIG_STR_SIZE];     // command-line argument buffer (oversized)
  ////  char reply[BIG_STR_SIZE];    // command reply buffer

  //// The length of reply has been shorter than AUXSTATUS string !!
  //// The reply was corrected to longer size (1024) for AUXSTATUS/INFO
  //// (AUXSTATUS length ~ 600, INFO length ~ 800)
  //// and the other strings were changed to shorter size or same size 
  //// using memory allocation to prevent the memory problems.(v1.6.6.3)

  // ISIS message handling stuff

  char msg[STRLEN_CMD];           // ISIS message packet to send to ISIS node when '>ID' commanded (including "TC>ID REQ ..")
  char destID[STRLEN_ISISNODE];   // ISIS message destination node ID
  char msgbody[STRLEN_ARG];       // ISIS message body to send to ISIS node when '>ID' commanded

  // command components (command arguments and reply string)

  char cmd[STRLEN_CMD];       // command word extracted from keyboard input command-line
  char args[STRLEN_ARG];      // argument field extracted from keyboard input command-line
  char reply[STRLEN_REP];     // reply string buffer from cmd_xxx() functions, including INFO/AUXSTATUS strings

  static char PrevMessage[STRLEN_MAXKEYIN];

  // Variables used to traverse the command tree

  int i;
  int nfound=0;
  int icmd=-1;

  // Pointer for the keyboard message buffer

  char *message;
  int strlen_message = STRLEN_MAXKEYIN;

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

  KeyCmdFlag = 1;

  if (strlen(line)>STRLEN_MAXKEYIN) {  // v1.6.6.3
    REDTEXT;
    sprintf(cmsg, "ERROR: Too long input message\n");_msgout(cmsg);
    free(line);
    KeyCmdFlag = 0;
    return;
  }

  // Allocate memory for the message buffer and clear it

  message = (char *)malloc(strlen_message*sizeof(char));
  memset(message,0,strlen_message*sizeof(char));

  /*
  //////// OldVer - START

  // Copy the keyboard input line into the message buffer 

  strcpy(message,line);

  // do any history expansion (!, !!, etc.) if required

  if (line[0]) {
    result = history_expand(line,&expansion);
    if (result)
      printf("%s\n",expansion);
    
    if (result < 0 || result==2) {
      free(expansion);
      KeyCmdFlag = 0;
      return;
    }

    add_history(expansion);
    memset(message,0,ISIS_MSGSIZE);
    sprintf(message,"%s",expansion);
    free(expansion);
  }
  //////// OldVer - END
  */

  /*
  //////// NewVer A - START

  // Copy the keyboard input line into the message buffer 
  // and do any history expansion (!, !!, etc.) if required

  if (line[0]=='!') {  // v1.6.6.4
    result = history_expand(line,&expansion);
    if (result) {
     sprintf(cmsg, "%s\n",expansion);_msgout(cmsg);  // v1.6.0
    }
    if (result < 0 || result==2) {
      free(expansion);
      free(line);  // v1.6.6.3
      KeyCmdFlag = 0;
      return;
    }
    sprintf(message,"%s",expansion);
    free(expansion);
  }
  else {
    strcpy(message,line);
  }

  // Add history if input message is not repetition..

  if ( strcasecmp (PrevMessage, message) ) {  // v1.6.6.2 & v1.6.6.4
    add_history(message);
    strcpy(PrevMessage, message);
  }

  //////// NewVer A - END
  */

  ///*
  //////// NewVer B - START

  // Copy the keyboard input line into the message buffer 
  // and do any history expansion (!, !!, etc.) if required

  result = history_expand(line,&expansion);  // if(line[0]..) removed at v1.6.6.4
  if (result) {
   sprintf(cmsg, "%s\n",expansion);_msgout(cmsg);  // v1.6.0
  }
  if (result < 0 || result==2) {
    free(expansion);
    free(line);  // v1.6.6.3
    KeyCmdFlag = 0;
    return;
  }

  sprintf(message,"%s",expansion);
  free(expansion);

  // Add history if input message is not repetition..

  if ( strcasecmp (PrevMessage, message) ) {  // v1.6.6.2 & v1.6.6.4
    add_history(message);
    strcpy(PrevMessage, message);
  }

  //////// NewVer B - END
  //*/

  //////// NOTE: Both A and B are ok. B is simpler, which is better


  // We're all done with the original string from readline(), free it

  free(line);

  // Remove any \n terminator on the message string

  if (message[strlen(message)-1]=='\n') message[strlen(message)-1]='\0';

  // Keyboard input string output on Console and Logfile

  {//verbose
    sprintf(cmsg, " KEY IN : %s\n",message);_vmsgout(cmsg);
  }

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

  if (strncasecmp(cmd,">",1)==0) { //

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

      {//verbose
        msg[strlen(msg)-1]='\0';
        sprintf(cmsg, "ISIS OUT: %s\n",msg);_vmsgout(cmsg);
      }

    } 

    else {
      REDTEXT;
      //sprintf(cmsg, "No ISIS server active >> command unavailable\n");_msgout(cmsg);
      sprintf(cmsg, "No ISIS client mode >> ICIMACS command unavailable\n");_msgout(cmsg);  // v1.6.6.3
    }
    
  } // end if (strncasecmp(cmd,">",1)==0)

  // All other commands use the cmd_xxx() action calls

  else { //

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
        sprintf(cmsg, "ERROR: Unknown command - '%s'\n",cmd);_msgout(cmsg);
      }
    }
    else { // all console keyboard are treated as EXEC: type messages
	    switch (cmdtab[icmd].action(args,EXEC,reply)) { //////
	      case CMD_ERR:
          REDTEXT;
          sprintf(cmsg, "ERROR: %s\n",reply);_msgout(cmsg);
          break;
	      case CMD_OK:
          sprintf(cmsg, "DONE: %s\n",reply);_msgout(cmsg);
          break;
	      case CMD_NOOP:
        default:
          break;
	    } 

    } 

  } // end of else {

  KeyCmdFlag = 0;

}

//------------------------------------------------------------------------------
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
  ////  // ISIS message components 
  ////
  ////  char msg[ISIS_MSGSIZE];       // Full ISIS message buffer
  ////  char srcID[ISIS_NODESIZE];    // ISIS message sending node ID
  ////  char destID[ISIS_NODESIZE];   // ISIS message destination node ID
  ////  char msgbody[ISIS_MSGSIZE];   // ISIS message/command body
  ////  MsgType msgtype = REQ;        // ISIS message type, defined in isisclient.h
  ////
  ////  // command components (command arguments and reply string)
  ////
  ////  char cmd[BIG_STR_SIZE];       // command string (oversized)
  ////  char args[BIG_STR_SIZE];      // command-line argument buffer (oversized)
  ////  char reply[REPLY_STR_SIZE];    // command reply buffer

  //// The length of reply has been shorter than AUXSTATUS string !!
  //// The reply was corrected to longer size (1024) for AUXSTATUS/INFO
  //// (AUXSTATUS length ~ 600, INFO length ~ 800)
  //// and the other strings were changed to shorter size or same size 
  //// using memory allocation to prevent the memory problems.(v1.6.6.3)

  // ISIS message handling stuff

  char msg[STRLEN_REP];           // ISIS message to send to ISIS node or remote host
  char srcID[STRLEN_ISISNODE];    // ISIS message source node ID
  char destID[STRLEN_ISISNODE];   // ISIS message destination node ID
  char msgbody[STRLEN_ISISMSG];   // ISIS message received from ISIS node or remote host
  MsgType msgtype = REQ;          // ISIS message type of recevied message, defined in isisclient.h

  // command components (command arguments and reply string)

  char cmd[STRLEN_CMD];       // command word extracted from socket command-line received from ISIS node or other remote host
  char args[STRLEN_REP];      // argument field extracted from socket command-line received from ISIS node or other remote host
  char reply[STRLEN_REP];     // reply string buffer from cmd_xxx() functions, including INFO/AUXSTATUS strings

  // other working variables

  int i;
  int nfound=0;
  int icmd=-1;
  int rtn;
  int MsgFromISIS;

  // Some simple initializations

  memset(msg,0,sizeof(msg));
  memset(cmd,0,sizeof(cmd));
  memset(args,0,sizeof(args));
  memset(reply,0,sizeof(reply));

  // Inspect ID & Type string length for using SplitMessage(), v1.6.6.4

  memset(msgbody,0,sizeof(msgbody));
  sscanf(buf, "%s", msgbody);
  if( strlen(msgbody) >= STRLEN_ISISADDR ) return;

  memset(msgbody,0,sizeof(msgbody));
  sscanf(buf, "%*s %s", msgbody);
  if( strlen(msgbody) >= STRLEN_ISISTYPE ) return;

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

      //if(client.isVerbose) {
      //  printf("\rISIS IN : Malformed message\n");
      //  rl_refresh_line(0,0);
      //}
      //// replaced with below code at v1.6.0

      {//verbose
        sprintf(cmsg, "ISIS IN : Malformed message\n");_vmsgout(cmsg);
      }

      return;
    }

    {//verbose
      sprintf(cmsg, "ISIS IN : %s\n",buf);_vmsgout(cmsg);
    }

  }

  // check only message format in case of Standalone mode

  else { 

    MsgFromISIS = 0;  // v1.4.3

    if (rtn<0) {
      {//verbose
        sprintf(cmsg, "REMC IN : Malformed message from %s\n", srcID);_vmsgout(cmsg);
      }
      return;
    }

    {//verbose
      sprintf(cmsg, "REMC IN : %s\n",buf);_vmsgout(cmsg);
    }
  }    

  // Immediate action depends on the type of message received as
  // recorded by the msgtype code.

  switch(msgtype) {

  case STATUS:  // we've been sent a status message, echo to console
    sprintf(cmsg, "%s\n",buf);_msgout(cmsg);
    break;
	  
  case DONE:    // command completion message (?), echo to console.
    sprintf(cmsg, "%s\n",buf);_msgout(cmsg);
    break;
	  
  case ERROR:   // error messages, echo to console, get fancy later
    REDTEXT;
    sprintf(cmsg, "%s\n",buf);_msgout(cmsg);
    break;

  case WARNING:
    CYATEXT;
    sprintf(cmsg, "%s\n",buf);_msgout(cmsg);
    break;

  case FATAL:
    MAGTEXT;
    sprintf(cmsg, "%s\n",buf);_msgout(cmsg);
    break;
	  
  case REQ:    // implicit command requests
  case EXEC:   // and executive override commands

    msgbody[STRLEN_ISISMSG-1] = '\0';  // v1.6.0
    msgbody[STRLEN_ISISMSG-2] = '\n';  // v1.6.0

    if (strlen(msgbody)>STRLEN_MAXSOCIN) {  // v1.6.6.4
      sprintf(msg,"%s>%s ERROR: Message is too long! (length=%d)\n\r",
                  client.ID, srcID, strlen(msgbody) );
      break;
    }

    //printf("\nDEBUG: input message length = %d\n\n", strlen(msgbody));
    //sprintf(msg, "DEBUG: input message length = %d\n\r", strlen(msgbody));
    //goto SENDMSG;

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
	          client.ID,srcID,cmd);
    }
    else {
      SocketCmdFlag = 1;
      switch(cmdtab[icmd].action(args,msgtype,reply)) {

      case CMD_ERR: // command generated an error
        sprintf(msg,"%s>%s ERROR: %s\n\r",client.ID,srcID,reply);
        break;

      case CMD_NOOP: // command is a no-op, debug/verbose output only
        //if (client.isVerbose)
        //  /printf("ISIS IN: %s from ISIS node %s\n",msgbody,srcID);
        // ==> there was /printf("ISIS IN : %s\n",buf); aleady above
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
      //sprintf(msg,"%s>%s %s\r",client.ID,srcID,reply);
      sprintf(msg,"%s>%s %s\n\r",client.ID,srcID,reply);  // v1.6.2

    break;

  default:  // we don't know what we got, print for debugging purposes

    sprintf(msg,"%s>%s ERROR: Unknown message type\n\r",client.ID,srcID);

    {//verbose
      CYATEXT;    
      if (MsgFromISIS) {sprintf(cmsg, "ISIS IN : Malformed message type\n");_vmsgout(cmsg);}
      else             {sprintf(cmsg, "REMC IN : Malformed message type\n");_vmsgout(cmsg);}
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

  //SENDMSG:  // for debugging about input string length

  if (strlen(msg)>0) { // we have something to send

    //if (client.useISIS) {
    if (MsgFromISIS) {  // client.useISIS and Msg from ISIS (v1.4.3)
      SendToISISServer(&client,msg);
      {//verbose
        msg[strlen(msg)-1]='\0';
        //sprintf(cmsg, "ISIS OUT: %s\n",msg);_vmsgout(cmsg);
        sprintf(cmsg, "ISIS OUT: %s",msg);_vmsgout(cmsg);  // v1.6.2
      }
    }

    else {
      ReplyToRemHost(&client,msg);
      {//verbose
        msg[strlen(msg)-1]='\0';
        //sprintf(cmsg, "REMC OUT: %s\n",msg);_vmsgout(cmsg);
        sprintf(cmsg, "REMC OUT: %s",msg);_vmsgout(cmsg);  // v1.6.2
      }
    }
  } // end of reply handling

}

//------------------------------------------------------------------------------
//
// SendStatus() - send a STATUS/ERROR message to all nodes in ISIS client mode (v1.4.9?)
// 
// Event list to send status
//    - Filter changed
//    - Telescope slew completed
//    - Shutter closed ?
//    - ... ?
//

void
SendStatus(char *statusmsg, char *destID)
{
  //char destID[STRLEN_ISISNODE];
  char msg[STRLEN_ISISSTAT];
  int rtn;

  if (client.useISIS==0) return;

  ////strcpy(destID, "AL");
  ////strcpy(destID, LastDestID);  ---> AL or specific node ??

  memset(msg,0,sizeof(msg));

  sprintf(msg,"%s>%s STATUS: %s\r",client.ID, destID, statusmsg);

  rtn = SendToISISServer(&client,msg);
  {//verbose
    msg[strlen(msg)-1]='\0';
    sprintf(cmsg, "ISIS OUT: %s\n",msg);_vmsgout(cmsg);
  }

  if (rtn<0) {
    REDTEXT;
    sprintf(cmsg, "ERROR: Failed to send a STATUS/ERROR message to ISIS server..\n");_msgout(cmsg);
    {//verbose
      REDTEXT;
      sprintf(cmsg, "       - %s\n",strerror(errno));_vmsgout(cmsg);
    }
  }

}

//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
//
// cmd_xxxxx() action functions
//
// Add new functions at the end.  To be available, they must be entered
// as "action" members in the Commands struct for this application (see
// commands.h)
//

//
// *** Client COMMANDS BEGIN HERE ***
//

//------------------------------------------------------------------------------
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
    strcpy(reply,"cannot exec 'quit/exit' command - remote operation not allowed");
    return CMD_ERR;
  }
  return CMD_OK;
}

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
//
// client.catalog - import/quiry & display the RA/Dec catalog
//

int
cmd_catalog(char *args, MsgType msgtype, char *reply)
{
  int rtn, i;
  char catalog[STRLEN_FILE];

  // input & check args

  rtn = sscanf(args, "%s", catalog);

  if(rtn<1) {  // Quiry the RA/Dec object catalog data loaded on memory

    if(msgtype==EXEC) {  // display all the data on console

      sprintf(cmsg, "\n");_msgout(cmsg);
      sprintf(cmsg, "--------------------------------------------------------------------\n");_msgout(cmsg);
      sprintf(cmsg, "  RA/Dec Object Catalog Data - '%s'\n", agent.CatFile                  );_msgout(cmsg);
      sprintf(cmsg, "--------------------------------------------------------------------\n");_msgout(cmsg);

      if(agent.CatDataNum<=0) {
        //sprintf(cmsg, "    no catalog data\n");_msgout(cmsg);
        sprintf(cmsg, "No RA/Dec object catalog data imported from catfile '%s'\n", agent.CatFile);_msgout(cmsg);  // v1.6.6.6
      }
      else {
        for(i=0;i<agent.CatDataNum;i++) {
          sprintf(cmsg, "    %05d  %12s  %s  %s  %c\n", 
                 (i+1), agent.CatObj[i], agent.CatRA[i], agent.CatDec[i], agent.CatCopt[i]);
          _msgout(cmsg);
        }
      }

      //sprintf(catalog, "  imported from '%s'", agent.CatFile);
      sprintf(catalog, "  %d data imported from '%s'", agent.CatDataNum, agent.CatFile);  // v1.6.6.0

      sprintf(cmsg, "--------------------------------------------------------------------\n");_msgout(cmsg);
      sprintf(cmsg, "%68s\n\n", catalog);_msgout(cmsg);

      return CMD_NOOP;
    }

    else {  // response the data number and catalog file name to ISIS node
      if(agent.CatDataNum<=0) {
        //sprintf(cmsg, "No RA/Dec object catalog data - catfile '%s'\n", agent.CatFile);_msgout(cmsg);
        sprintf(reply, "No RA/Dec object catalog data imported from catfile '%s'\n", agent.CatFile);  // v1.6.6.6
      }
      else {
        sprintf(reply, "RA/Dec object catalog - %d data loaded,"
                       " imported from catfile '%s'"
                       , agent.CatDataNum, agent.CatFile );
      }
    }

  }

  else {  // Import the RA/Dec object catalog data from input rootname

    rtn = LoadCatalog(catalog, reply);

    if(rtn<0) {
      // Return -1: In case of no catfile (Cannot open RA/Dec object catalog file "filename")
      // Return -2: In case of no data in catfile (No available data in catalog file "filename")
      return CMD_ERR;
    }

    strcpy(agent.CatFile, catalog);

  }

  return CMD_OK;
}

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
//
// client.concise - disable verbose console output
//
  
int
cmd_concise(char *args, MsgType msgtype, char *reply)
{
  client.isVerbose = 0;
  sprintf(reply,"verbose mode disabled");

  return CMD_OK;
}

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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
  int rtn, n, hlen, start=0;

  if (msgtype == EXEC) {  // v1.6.6.4

    the_list = history_list();

    if (strstr(args,"-c")>0) {
      clear_history();
      sprintf(reply,"All the histroy entries cleared");
      return CMD_OK;
    }

    if (the_list) {

      rtn = sscanf(args, "%d", &n);
      if(rtn>0) {
        if( n>0 && n<=history_length ) start = history_length - n;
      }

      for (ihist=start; the_list[ihist]; ihist++) {
        printf("%5d   %s\n",ihist+history_base,the_list[ihist]->line);
      }

    }

    return CMD_NOOP;

  }

  /*
  if (msgtype == EXEC) {  // OldVer
    the_list = history_list();
    if (the_list) {
      for (ihist=0; the_list[ihist]; ihist++) {
        printf("%5d   %s\n",ihist+history_base,the_list[ihist]->line);
      }
    }
    return CMD_NOOP;
  }
  */

  // can't do history unless you're on the console...

  strcpy(reply, "cannot exec 'history' command - remote operation not allowed");
  return CMD_ERR;

}

//------------------------------------------------------------------------------
//
// client.help - quick list of available commands
//


int
cmd_help(char *args, MsgType msgtype, char *reply)
{
  if (msgtype==EXEC) {
    printf("\n");
    printf("                  <<KMTNet TCS Agent interactive commands>>                   \n");
    printf("______________________________________________________________________________\n");
    printf("Client commands:\n");
    printf("   quit           - quit TCS Agent application\n");
    printf("   init           - initialize both TCS & AUX links\n");
    printf("   reset          - reset/restart both TCS & AUX links\n");
    printf("   close          - close both TCS & AUX links\n");
    printf("   arc            - toggle AutoRecovery mode for both TCS & AUX links\n");
    printf("   info           - report client information\n");
    printf("   version        - report client version & compile info\n");
    printf("   catalog / cat  - quiry & import RA/Dec object catalog, args: (<catfile>)\n");
    printf("   verbose / ver  - toggle verbose output mode\n");
    printf("   concise / con  - disable verbose output mode\n");
    printf("   debug          - toggle debugging output\n");
    printf("   history (n/-c) - show command history (n: last n entries / -c: clear all)\n");
    printf("   !!             - repeat last command\n");
    printf("   !cmd           - repeat last command matching 'cmd'\n");
    printf("   help    / ?    - view this TCS Agent commands list\n");
    printf("______________________________________________________________________________\n");
    printf("TCS (PC-TCS Telcom) commands:\n");
    printf("   tcsinit        - initialize PC-TCS Telcom link\n");
    printf("   tcsreset       - reset/restart PC-TCS Telcom link\n");
    printf("   tcsclose       - close PC-TCS Telcom link\n");
    printf("   tcsarc         - toggle AutoRecovery mode for TCS link\n");
    printf("   tcsstatus      - query & return TCS status with the telemetry data\n");
    printf("   tstat          - query & return raw TCS status without keywords\n");
    printf("   traw           - return lastest raw PC-TCS telemetry packet string\n");
    printf("   tsync          - synch PC-TCS clock with the system UTC clock\n");
    printf("   tcmd           - send a raw PC-TCS command, arg: <tcmd>\n");
    printf("   treq           - send a raw PC-TCS request, arg: <treq>\n");
    printf("   tmradec / tmr  - move to J2000 RA/Dec, args: <ra> <dec> (<copt>)\n"); 
    printf("   tmobject/ tmo  - move to object, defined in catalog, args: <obj>\n");
    printf("   tmelaz  / tme  - move to elevation/azimuth, args: <el> <az>\n");
    printf("   tmoffset/ toff - move to offset RA/Dec, args: <RA_offset> <DEC_offset>\n");
    printf("   tguide  / tgui - guiding offset move, args: <ra_offset> <dec_offset>\n");
    printf("   tstop          - cancel command and stop telescope for commanded motions\n");
    printf("   tstow          - stow telescope\n");
    printf("   tdi            - synch the current position with the commanded position\n");
    printf("______________________________________________________________________________\n");
    printf("AUX control commands:\n");
    printf("   auxinit        - initialize AUX control link\n");
    printf("   auxreset       - reset/restart AUX control link\n");
    printf("   auxclose       - close AUX control link\n");
    printf("   auxarc         - toggle the auto recovery mode for AUX link\n");
    printf("   auxstatus      - query & return AUX status with the telemetry data\n");
    printf("   astat          - query & return raw AUX status without keywords\n");
    printf("   acmd           - send a raw AUX control remote command, arg: <acmd>\n");
    printf("   fsastat  /fs   - query & return AUX Filter/Shutter status\n");
    printf("   filter         - change filters to arg # or name, arg: <fnum/fname>\n");
    printf("   filname        - query & return the filter names for 4 slides\n");
    printf("   fttstat  /ft   - query & return AUX Focuser/Tip-Tilt/Limit/Position(S/E/W)\n");
    printf("   dfocus         - adjust the focus position of PFI, arg: <dfoc>\n");
    printf("   dtilt          - adjust the tip-tilt angle ofg PFI, arg: <dtns> <dtew>\n");
    printf("   fttgoto        - goto abs focus & tip-tilt, arg: <foc> (<tns> <tew>)\n");
//  printf("   dtiltp         - adjust the tip-tilt angle of PFI, arg: <theta> <dtilt>\n");
//  printf("   fttgotop       - goto abs focus & tip-tilt, arg: <foc> (<theta> <tilt>)\n");
//  printf("______________________________________________________________________________\n");
//  printf("Alias: quit=exit / init=reset / catalog=cat / verbose=ver / help=? / \n");
//  printf("       tcsinit=tcsreset / tcsstatus=tcsstat=tstatus / tmradec=tmr=tgoto / \n");
//  printf("       tmobject=tmobj=tmo / tmelaz=tme / toffset=toff / tguide=tgui / \n");
//  printf("       auxinit=auxreset / auxstatus=auxstat=astatus / fsastat=fs / fttstat=ft\n");
    printf("______________________________________________________________________________\n");
    printf("Utilities: tick / cc / oo\n");
    printf("\n");

    _msglog("                  <<KMTNet TCS Agent interactive commands>>                   \n");
    _msglog("______________________________________________________________________________\n");
    _msglog("...omission\n");

    return CMD_NOOP;
  }

  // Can't use HELP unless you're on the console...

  strcpy(reply, "cannot exec 'help' command - remote operation not allowed");
  return CMD_ERR;

}

//------------------------------------------------------------------------------
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


//------------------------------------------------------------------------------
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
  sprintf(cmsg, "PONG received from %s\n", SourceID);_vmsgout(cmsg);
  return CMD_NOOP;
}

//
// *** PC-TCS COMMANDS BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// tcs.tcsinit - (re)initialize the PC-TCS serial communications link
//
// Initializes the PCTCS link.  Calls InitPCTCS() to do the dirty work.
//

int
cmd_tcsinit(char *args, MsgType msgtype, char *reply)
{
  //char errmsg[MSGBUFLEN];
  char errmsg[128];

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
    sprintf(cmsg, "STATUS: PC-TCS Telcom Link Initialized at a request from ISIS\n");
    _msgout(cmsg);
  }
  else {
    GRNTEXT;  // TXTRESET in KeyboardCommand()
  }

  return CMD_OK;
}

//------------------------------------------------------------------------------
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
    sprintf(cmsg, "STATUS: PC-TCS Telcom Link closed at a request from ISIS\n");
    _msgout(cmsg);
  }
  else {
    REDTEXT;  // TXTRESET in KeyboardCommand()
  }

  return CMD_OK;
}

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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
  int i, maxlen;
  float secz, alt, az;
  char curdate[16], curtime[16];
  systime_t curutc;

  // set obs date & time with current system clock

  GetUTCDateTime(&curutc);
  sprintf(curdate, "%04d-%02d-%02d", curutc.year, curutc.month, curutc.day);
  //sprintf(curtime, "%02d:%02d:%06.3f", curutc.hour, curutc.min, curutc.sec);
  sprintf(curtime, "%02d:%02d:%02d.%03d", curutc.hour, curutc.min, 
                    (int)curutc.sec, (int)(curutc.sec*1000.)%1000 );  // v1.6.4

  switch (tcs.Link) {

  case TCS_UP:

    for(i=1;i<=TCS_ENCODINGNUM;i++) {  // v1.6.5

      tcs.EncodingNum = i;

      secz = atof(tcs.SecZ);
      alt = atof(tcs.Alt);
      az = atof(tcs.Az);

      sprintf(reply, "TCSSTATUS TCSQDATE=%sT%s TIMESYS=UTC TCSLINK=Up TCSARC=%s"
                     " TCSUDATE=%sT%s RA=%s DEC=%s EQUINOX=%s HA=%s"
                     " ST=%s SECZ=%.2f ALT=%.1f AZ=%.1f",
                     curdate, curtime, tcs.ArcMode?"Enabled":"Disabled",
                     tcs.Date, tcs.UTC, tcs.RA, tcs.Dec, tcs.Equinox, tcs.HA,
                     tcs.LST, secz, alt, az);

      maxlen = TCS_TCSSTATUSLEN -(tcs.ArcMode?1:0) -(tcs.SecZ[0]==' '?1:0)
                -(tcs.Alt[0]==' '?1:0) -(tcs.Az[0]==' '?1:0) -(tcs.Az[1]==' '?1:0)
                 -(tcs.Az[0]=='+'?1:0) -(tcs.Az[1]=='+'?1:0) -(tcs.Az[2]=='+'?1:0);

      if( strlen(reply) == maxlen ) break;

    }

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

    ////// v1.4.1
    ////switch (tcs.LimitStatus) {
    ////case 0: 
    ////  strcat(reply," TCSLIMIT=No");
    ////  break;
    ////case 1: 
    ////  strcat(reply," TCSLIMIT=RA");
    ////  break;
    ////case 2:
    ////  strcat(reply," TCSLIMIT=Dec");
    ////  break;
    ////case 3:
    ////  strcat(reply," TCSLIMIT=Horizon");
    ////  break;
    ////default:
    ////  strcat(reply," TCSLIMIT=Unknown");
    ////  break;
    ////}

    // v1.6.6
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
      strcat(reply," TCSLIMIT=RA+Dec");
      break;
    case 4:
      strcat(reply," TCSLIMIT=Horizon");
      break;
    case 5:
      strcat(reply," TCSLIMIT=RA+Horizon");
      break;
    case 6:
      strcat(reply," TCSLIMIT=Dec+Horizon");
      break;
    case 7:
      strcat(reply," TCSLIMIT=RA+Dec+Horizon");
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

  TcsStatusFlag = 1;  // for logging the traw string in event log, v1.6.2

  return CMD_OK;

}

//------------------------------------------------------------------------------
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
  int i;
  char curdate[16], curtime[16];
  systime_t curutc;
 
  GetUTCDateTime(&curutc);
  sprintf(curdate, "%04d-%02d-%02d", curutc.year, curutc.month, curutc.day);
  //sprintf(curtime, "%02d:%02d:%06.3f", curutc.hour, curutc.min, curutc.sec);
  sprintf(curtime, "%02d:%02d:%02d.%03d", curutc.hour, curutc.min, 
                    (int)curutc.sec, (int)(curutc.sec*1000.)%1000 );  // v1.6.4

  switch (tcs.Link) {

  case TCS_UP:
    for(i=1;i<=TCS_ENCODINGNUM;i++) {  // v1.6.5
      tcs.EncodingNum = i;
      sprintf(reply, "UP %d %sT%s UTC %sT%s %s %s %s %s %s %s %s %s %2d %2d %2d %c",
                     tcs.ArcMode, curdate, curtime, tcs.Date, tcs.UTC, tcs.RA, tcs.Dec,
                     tcs.Equinox, tcs.HA, tcs.LST, tcs.SecZ, tcs.Alt, tcs.Az, 
                     tcs.MoveStatus, tcs.LimitStatus, tcs.DriveDisable, tcs.ExeCode);
      if( strlen(reply) == TCS_TSTATLENGTH ) break;      
    }
    break;

  case TCS_IDLE:
    sprintf(reply, "IDLE %d %sT%s UTC", tcs.ArcMode, curdate, curtime);
    break;

  default:
    sprintf(reply, "DOWN %d %sT%s UTC", tcs.ArcMode, curdate, curtime);
    break;

  }

  TcsStatusFlag = 1;

  return CMD_OK;

}

//------------------------------------------------------------------------------
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

  strcpy(reply, tcs.RawPacket);

  return CMD_OK;

}

//------------------------------------------------------------------------------
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

  memset(tcscmd, 0, sizeof(tcscmd));
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

  {//verbose
    sprintf(cmsg, " TCS OUT: %s", tcscmd);_vmsgout(cmsg);
  }

  // receive the response of command

  memset(tcscmd, 0, sizeof(tcscmd));
  cmdlen = recv(tcs.FDcmd, tcscmd, CMDBUFLEN-1, 0);
  if(cmdlen<=0) {
    sprintf(reply, "response recv failed - recvbyte = %d", cmdlen);
    return CMD_ERR;
  }
  tcscmd[cmdlen] = NULL;
  {//verbose
    sprintf(cmsg, " TCS IN : %s", tcscmd);_vmsgout(cmsg);
  }

  tcs.UpdateFlag = 0;

  memset(argbuf, 0, sizeof(argbuf));
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

//------------------------------------------------------------------------------
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

  memset(tcscmd, 0, sizeof(tcscmd));
  cmdlen = sprintf(tcscmd, "%s %s %03d REQUEST %s\n", 
                            tcs.TelID, tcs.SysID, PID_REQCMD, strupr(args));

  // send the command to Telcom via tcp link

  nsent = send(tcs.FDcmd, tcscmd, cmdlen, 0);
  if (nsent < cmdlen) {
    sprintf(reply, "request send failed - treq='%s' reqlen=%d, sentbyte=%d", 
                   args, cmdlen, nsent);
    return CMD_ERR;
  }

  {//verbose
    sprintf(cmsg, " TCS OUT: %s", tcscmd);_vmsgout(cmsg);
  }

  // receive the response of command

  memset(tcscmd, 0, sizeof(tcscmd));
  cmdlen = recv(tcs.FDcmd, tcscmd, CMDBUFLEN-1, 0);
  if(cmdlen<=0) {
    sprintf(reply, "response recv failed - recvbyte = %d", cmdlen);
    return CMD_ERR;
  }
  tcscmd[cmdlen] = NULL;
  {//verbose
    sprintf(cmsg, " TCS IN : %s", tcscmd);_vmsgout(cmsg);
  }

  memset(argbuf, 0, sizeof(argbuf));
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

//------------------------------------------------------------------------------
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
  char tcscmd[CMDBUFLEN];  // command buffer
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

  // Get the system time/date (user have to check the time is not passing on 24:00)

  GetUTCDateTime(&tctime);

  // Build the SETTIME command string

  memset(tcscmd,0,sizeof(tcscmd));
  //sprintf(tcscmd, "SETTIME %.2d%.2d%05.2f", tctime.hour, tctime.min, tctime.sec);
  sprintf(tcscmd, "SETTIME %.2d%.2d%.2d.%.2d", 
                  tctime.hour, tctime.min, (int)tctime.sec, (int)(tctime.sec*100.)%100);  // v1.6.4

  // Execute the command for setting the time on PC-TCS

  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // Execution code update between SETDATE and SETTIME commands

  rtn = TcsTelemetry(&tcs, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // Build the SETDATE command string

  memset(tcscmd,0,sizeof(tcscmd));
  sprintf(tcscmd, "SETDATE %.2d/%.2d/%.4d", tctime.month, tctime.day, tctime.year);

  // Execute the command for setting the date on PC-TCS

  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  strcpy(reply, "synched PC-TCS with the local host UTC clock");
  return CMD_OK;

}

//------------------------------------------------------------------------------
//
// tcs.tmradec - move to J2000 RA/Dec, arg format: hh:mm:ss.s dd:mm:ss.s
//
// NOTE: Input Epoch must be set to J2000 manually on PC-TCS before this command (v1.1)
//        --> Revised, Automatically set to 2000 in cmd_tcsinit(), 
//            So manual setting is not necessary now (v1.2.0).
//       Func was overall modified and the name was changed 
//        for BLG offset correction (v1.5.0), and related to catalog importing (v1.5.1).
//

int
cmd_tmradec(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[CMDBUFLEN];  // command buffer
  char rai[32], deci[32];  // input string (hh:mm:ss.ss/+dd:mm:ss.s)
  char rac[16], decc[16];  // corrected string (hh:mm:ss.ss/+dd:mm:ss.s)
  char rat[16], dect[16];  // PC-TCS/Telcom string (+hhmmss.sss/+ddmmss.ss)
  char sign, ha[16], copt;
  int hour, deg, min, rtn;
  double sec;
  double dRA, dDEC, dHA;  // destinations
  double ad_ra, ad_dec;   // angular distance


  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%s %s %c", &rai, &deci, &copt);

  if(rtn<2) {
    strcpy(reply, "usage: tmradec <RA> <DEC> (<copt>)");
    strcat(reply, "  /  <RA>: hh:mm:ss.sss  <DEC>: +dd:mm:ss.ss (J2000)");
    strcat(reply, "  <copt>: option for pointing error correction, optional");
    strcat(reply, " - 0(default): no correction, 1: BLG offset correction");
    return CMD_ERR;
  }

  if(rtn<3) copt = '0';  // defalt setting: 0 = no correction

  // check coordinate correction option

  switch(copt) {
    case '0':           break;  // No correction
    case '1':           break;  // BLG correction
    case 'k': case 'K': break;  // Offset to K from center
    case 'm': case 'M': break;  // Offset to M
    case 't': case 'T': break;  // Offset to T
    case 'n': case 'N': break;  // Offset to N
    default : copt='0'; break;  // default setting
  }

  // check RA input string and values & convert to PC-TCS/Telcom format

  rtn = sscanf(rai, "%d%*c%d%*c%lf", &hour, &min, &sec);

  if(rtn<3) {
    sprintf(reply, "<ra> '%s' is unrecognized", rai);
    return CMD_ERR;
  }

  dRA = fabs((double)hour) + (double)min/60.0 + sec/3600.0;
  if( rai[0]=='-' ) dRA *= -1.0;

  if( rai[0]=='-' || hour<0 || hour>=24 || min<0 || min>=60 || sec<0.0 || sec>=60.0 ||
      dRA<0.0 || dRA>24.0 ) {
    sprintf(reply, "<ra> value is out of range - '%s'", rai);
    return CMD_ERR;
  }

  sign = trans1060(dRA, &hour, &min, &sec, 3);
  sprintf(rai, "%02d:%02d:%06.3f",        hour, min, sec);
  sprintf(rat, "%c%02d%02d%06.3f",  sign, hour, min, sec);

  // check Dec input string and values & convert to PC-TCS/Telcom format

  rtn = sscanf(deci, "%d%*c%d%*c%lf", &deg, &min, &sec);

  if(rtn<3) {
    sprintf(reply, "<dec> '%s' is unrecognized", deci);
    return CMD_ERR;
  }

  dDEC = fabs((double)deg) + (double)min/60.0 + sec/3600.0;
  if( dDEC<0.000001) dDEC = 0.0;
  else if( deci[0]=='-' ) dDEC *= -1.0;

  if( deg<-90 || deg>90 || min<0 || min>=60 || sec<0.0 || sec>=60 || 
      dDEC<-90.0 || dDEC>90.0 ) {
    sprintf(reply, "<dec> value is out of range - '%s'", deci);
    return CMD_ERR;
  }

  sign = trans1060(dDEC, &deg, &min, &sec, 2);
  sprintf(deci, "%c%02d:%02d:%05.2f", sign, deg, min, sec);
  sprintf(dect, "%c%02d%02d%05.2f"  , sign, deg, min, sec);

  ad_ra  = (63.0/60.0/15.0);  // angular distance inter chips
  ad_dec = (66.0/60.0     );

  // correction RA/DEC coordinates & convert to PC-TCS/Telcom format

  if(copt=='1') {  // BLG correction

    dHA = tcs.dHA + (tcs.dRA-dRA) + 20.0/3600.0;  // dHA: HA of destination, updated at v1.5.4

    rtn = offset_blg(&dRA, &dDEC, dHA, DEFAULT_CORTABLE_BLGOFF);
    if(rtn<0) {
      sprintf(reply, "RA/Dec coordinates BLG offset correction failure! (ErrCode=%d)", rtn);
      return CMD_ERR;
    }

    if(dRA>=24.0) dRA-=24.0;  // v1.5.2

    sign = trans1060(dHA, &hour, &min, &sec, 0);
    sprintf(ha, "%c%02d:%02d:%02.0f", sign, hour, min, sec);  // debugged at v1.5.3 - sign var was put, since there was no sign while there was %c for sign field
    sign = trans1060(dRA, &hour, &min, &sec, 3);
    sprintf(rac, "%02d:%02d:%06.3f",       hour, min, sec);
    sprintf(rat, "%c%02d%02d%06.3f", sign, hour, min, sec);
    sign = trans1060(dDEC, &deg, &min, &sec, 2);
    sprintf(decc, "%c%02d:%02d:%05.2f", sign, deg, min, sec);
    sprintf(dect, "%c%02d%02d%05.2f"  , sign, deg, min, sec);

   {//verbose --> msg activation during debugging
      BLUTEXT;
      sprintf(cmsg, "BLG offset corrected: \n");
      _msgout(cmsg);//_vmsgout(cmsg);
      BLUTEXT;
      sprintf(cmsg,   " INPUT      RA %s  DEC %s  HA %s\n", rai, deci, ha);
      _msgout(cmsg);//_vmsgout(cmsg);
      BLUTEXT;
      sprintf(cmsg,   " CORRECTED  RA %s  DEC %s\n"       , rac, decc    );
      _msgout(cmsg);//_vmsgout(cmsg);
    }
  }

    else if(copt=='k'||copt=='K') {

    //// Offset to K from N (v1.6.7)
    //dRA  += ad_ra/cos(dDEC*DEG2RAD);
    //dDEC -= ad_dec;

    //// Offset to K from K (v1.6.8)
    //Do nothing

    //// Offset to K from C (v1.6.9)
    dRA  += ad_ra /2.0/cos(dDEC*DEG2RAD);
    dDEC -= ad_dec/2.0;

    sign = trans1060(dRA, &hour, &min, &sec, 3);
    sprintf(rac, "%02d:%02d:%06.3f",       hour, min, sec);
    sprintf(rat, "%c%02d%02d%06.3f", sign, hour, min, sec);
    sign = trans1060(dDEC, &deg, &min, &sec, 2);
    sprintf(decc, "%c%02d:%02d:%05.2f", sign, deg, min, sec);
    sprintf(dect, "%c%02d%02d%05.2f"  , sign, deg, min, sec);


   {//verbose --> msg activation during debugging
      BLUTEXT;
      sprintf(cmsg, "Correction for offset to K: \n");
      _msgout(cmsg);//_vmsgout(cmsg);
      BLUTEXT;
      sprintf(cmsg,   " INPUT      RA %s  DEC %s\n", rai, deci);
      _msgout(cmsg);//_vmsgout(cmsg);
      BLUTEXT;
      sprintf(cmsg,   " CORRECTED  RA %s  DEC %s\n", rac, decc);
      _msgout(cmsg);//_vmsgout(cmsg);
    }

  }

  else if(copt=='m'||copt=='M') {

    //// Offset to M from N (v1.6.7)
    //dDEC -= ad_dec;

    //// Offset to M from K (v1.6.8)
    //dRA  -= ad_ra/cos(dDEC*DEG2RAD);

    //// Offset to M from C (v1.6.9)
    dRA  -= ad_ra /2.0/cos(dDEC*DEG2RAD);
    dDEC -= ad_dec/2.0;

    sign = trans1060(dRA, &hour, &min, &sec, 3);
    sprintf(rac, "%02d:%02d:%06.3f",       hour, min, sec);
    sprintf(rat, "%c%02d%02d%06.3f", sign, hour, min, sec);
    sign = trans1060(dDEC, &deg, &min, &sec, 2);
    sprintf(decc, "%c%02d:%02d:%05.2f", sign, deg, min, sec);
    sprintf(dect, "%c%02d%02d%05.2f"  , sign, deg, min, sec);


   {//verbose --> msg activation during debugging
      BLUTEXT;
      sprintf(cmsg, "Correction for offset to M: \n");
      _msgout(cmsg);//_vmsgout(cmsg);
      BLUTEXT;
      sprintf(cmsg,   " INPUT      RA %s  DEC %s\n", rai, deci);
      _msgout(cmsg);//_vmsgout(cmsg);
      BLUTEXT;
      sprintf(cmsg,   " CORRECTED  RA %s  DEC %s\n", rac, decc);
      _msgout(cmsg);//_vmsgout(cmsg);
    }

  }

  else if(copt=='t'||copt=='T') {

    //// Offset to T from N (v1.6.7)
    //dRA  += ad_ra/cos(dDEC*DEG2RAD);

    //// Offset to T from K (v1.6.8)
    //dDEC += ad_dec;

    //// Offset to T from C (v1.6.9)
    dRA  += ad_ra /2.0/cos(dDEC*DEG2RAD);
    dDEC += ad_dec/2.0;

    sign = trans1060(dRA, &hour, &min, &sec, 3);
    sprintf(rac, "%02d:%02d:%06.3f",       hour, min, sec);
    sprintf(rat, "%c%02d%02d%06.3f", sign, hour, min, sec);
    sign = trans1060(dDEC, &deg, &min, &sec, 2);
    sprintf(decc, "%c%02d:%02d:%05.2f", sign, deg, min, sec);
    sprintf(dect, "%c%02d%02d%05.2f"  , sign, deg, min, sec);


   {//verbose --> msg activation during debugging
      BLUTEXT;
      sprintf(cmsg, "Correction for offset to T: \n");
      _msgout(cmsg);//_vmsgout(cmsg);
      BLUTEXT;
      sprintf(cmsg,   " INPUT      RA %s  DEC %s\n", rai, deci);
      _msgout(cmsg);//_vmsgout(cmsg);
      BLUTEXT;
      sprintf(cmsg,   " CORRECTED  RA %s  DEC %s\n", rac, decc);
      _msgout(cmsg);//_vmsgout(cmsg);
    }

  }

  else if(copt=='n'||copt=='N') {

    //// Offset to N from N (v1.6.7)
    //Do nothing

    //// Offset to N from K (v1.6.8)
    //dRA  -= ad_ra/cos(dDEC*DEG2RAD);
    //dDEC += ad_dec;

    //// Offset to N from C (v1.6.9)
    dRA  -= ad_ra /2.0/cos(dDEC*DEG2RAD);
    dDEC += ad_dec/2.0;

    sign = trans1060(dRA, &hour, &min, &sec, 3);
    sprintf(rac, "%02d:%02d:%06.3f",       hour, min, sec);
    sprintf(rat, "%c%02d%02d%06.3f", sign, hour, min, sec);
    sign = trans1060(dDEC, &deg, &min, &sec, 2);
    sprintf(decc, "%c%02d:%02d:%05.2f", sign, deg, min, sec);
    sprintf(dect, "%c%02d%02d%05.2f"  , sign, deg, min, sec);


   {//verbose --> msg activation during debugging
      BLUTEXT;
      sprintf(cmsg, "Correction for offset to N: \n");
      _msgout(cmsg);//_vmsgout(cmsg);
      BLUTEXT;
      sprintf(cmsg,   " INPUT      RA %s  DEC %s\n", rai, deci);
      _msgout(cmsg);//_vmsgout(cmsg);
      BLUTEXT;
      sprintf(cmsg,   " CORRECTED  RA %s  DEC %s\n", rac, decc);
      _msgout(cmsg);//_vmsgout(cmsg);
    }

  }

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

  sprintf(tcscmd, "NEXTRA %s", rat);
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // execution code update between commands

  rtn = TcsTelemetry(&tcs, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // set the Dec Next position in PC-TCS

  sprintf(tcscmd, "NEXTDEC %s", dect);
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

  strcpy(reply, "move to RA/Dec commanded");
  if(copt==1) strcat(reply, ", coordinates corrected with BLG offset function");
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// tcs.tradec - move to object on catalog file, arg: ObjName
//
// NOTE: Created for Catalog input at v1.5.1
//

int
cmd_tmobject(char *args, MsgType msgtype, char *reply)
{
  char obj[64], copt;
  char radecstr[64];
  int rtn, i;

  // check catalog data number

  if(agent.CatDataNum<=0) {
    strcpy(reply, "No available data, import/quiry the catalog data using 'catalog' command");
    return CMD_ERR;
  }

  // gotta be up to send commands
  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%s %c", obj, &copt);

  if(rtn<1) {  
    strcpy(reply, "usage: tmobject <object> (<copt>)");
    strcat(reply, "  /  <object>: object name in the catalog data loaded on memory");
    strcat(reply, "  <copt>: option for pointing error correction, optional");
    strcat(reply, " - 0: no correction(default), 1: BLG offset correction");
    if(client.isVerbose) {
      strcat(reply, ",  Note: if default <copt> was aleady filled in catalog data"
                    ", then this command follows it as default <copt>"
                    ", else the default <copt> is 0(No correction)");
    }
    return CMD_ERR;
  }

  // search object name on catalog data

  for(i=0;i<agent.CatDataNum;i++) 
    if( !strcasecmp(agent.CatObj[i], obj) ) break;

  if(i==agent.CatDataNum) {
    strcpy(reply, "no maching object name, quiry/check the catalog data using 'catalog' command");
    return CMD_ERR;
  }

  // check default correction option on the catalog data

  if(rtn==1) copt = agent.CatCopt[i];
  // if rtn==1, there was not <copt> input, use default copt of catalog data
  // if rtn==2, there was <copt> input, use <copt> of command input

  // put RA/Dec/Copt into ra/dec string(args for cmd_tmradec()) & move to object

  sprintf(radecstr, "%s  %s  %c  #%s\n", 
                    agent.CatRA[i], agent.CatDec[i], copt, agent.CatObj[i] );

  rtn = cmd_tmradec(radecstr, msgtype, reply);

  if(rtn==CMD_OK) {
    sprintf(reply, "move to object %s commanded", agent.CatObj[i]);
    if(copt=='1') strcat(reply, ", coordinates corrected with BLG offset function");
    return CMD_OK;
  }

  return rtn;
}

//------------------------------------------------------------------------------
//
// tcs.tmelaz - move to elevation/azimuth, arg: ee.ee +aaa.aa
//
// NOTE: Created for Catalog input at v1.5.2
//

int
cmd_tmelaz(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[CMDBUFLEN];  // command buffer
  int rtn;
  double el, az;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%lf %lf", &el, &az);

  if(rtn<2) {
    strcpy(reply, "usage: tmelaz <el> <az>");
    strcat(reply, "  /  <el>: xx.xx  <az>: +xxx.xx (elevation and azimuth in deg)");
    return CMD_ERR;
  }

  // check El/Az value

  if( el<MIN_ELEVATION || el>90.0 ) {
    sprintf(reply, "<el> value (%.2f) is out of range", el);
    return CMD_ERR;
  }

  if( az<-360.0 || az>+360.0 ) {
    sprintf(reply, "<az> value (%+.2f) is out of range", az);
    return CMD_ERR;
  }

  // convert to PC-TCS/Telcom format & command move to El/Az

  sprintf(tcscmd, "ELAZ %.2f %+.2f", el, az);
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  strcpy(reply, "move to el/az commanded");
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// tcs.tmoffset - move as offset RA/Dec, arg format: +hh:mm:ss.s +dd:mm:ss.s
//

int
cmd_tmoffset(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[CMDBUFLEN];  // command buffer
  char rai[32], deci[32];  // input string (hh:mm:ss.ss/+dd:mm:ss.s)
  char rat[16], dect[16];  // PC-TCS/Telcom string (+hhmmss.sss/+ddmmss.ss)
  char sign;
  int rtn;
  int hour, deg, min;
  double sec, dRA, dDEC;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%s %s", &rai, &deci);

  if(rtn<2) {
    strcpy(reply, "usage: tmoffset <ra_offset> <dec_offset>");
    strcat(reply, "  /  <ra_offset>: +hh:mm:ss.ss  <dec_offset>: +dd:mm:ss.s");
    return CMD_ERR;
  }

  // check RA offset input string and values & convert to PC-TCS/Telcom format

  rtn = sscanf(rai, "%d%*c%d%*c%lf", &hour, &min, &sec);

  if(rtn<3) {
    sprintf(reply, "<ra_offset> '%s' is unrecognized, <ra_offset> format: +hh:mm:ss.ss", rai);
    return CMD_ERR;
  }

  dRA = fabs((double)hour) + (double)min/60.0 + sec/3600.0;
  if( rai[0]=='-' ) dRA *= -1.0;

  if( fabs(dRA)>MAX_OFFSETMOVE_RA || min<0 || min>=60 || sec<0.0 || sec>=60.0 ) {
    sprintf(reply, "<ra_offset> value '%s' is out of range - (Max. %.1f deg)", rai, MAX_OFFSETMOVE_RA);
    return CMD_ERR;
  }

  sign = trans1060(dRA, &hour, &min, &sec, 3);
  sprintf(rai, "%c%02d:%02d:%06.3f", sign, hour, min, sec);
  sprintf(rat, "%c%02d%02d%06.3f"  , sign, hour, min, sec);

  // check Dec offset input string and values & convert to PC-TCS/Telcom format

  rtn = sscanf(deci, "%d%*c%d%*c%lf", &deg, &min, &sec);

  if(rtn<3) {
    sprintf(reply, "<dec_offset> '%s' is unrecognized, <dec_offset> format: +dd:mm:ss.s", deci);
    return CMD_ERR;
  }

  dDEC = fabs((double)deg) + (double)min/60.0 + sec/3600.0;
  if( deci[0]=='-' ) dDEC *= -1.0;

  if( fabs(dDEC)>MAX_OFFSETMOVE_DEC || min<0 || min>=60 || sec<0.0 || sec>=60 ) {
    sprintf(reply, "<dec_offset> value '%s' is out of range - (Max. %.1f deg)", deci, MAX_OFFSETMOVE_DEC);
    return CMD_ERR;
  }

  sign = trans1060(dDEC, &deg, &min, &sec, 2);
  sprintf(deci, "%c%02d:%02d:%05.2f", sign, deg, min, sec);
  sprintf(dect, "%c%02d%02d%05.2f"  , sign, deg, min, sec);

  // set the RA Offset component in PC-TCS

  sprintf(tcscmd, "OFFRA %s", rat);
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // execution code update between commands

  rtn = TcsTelemetry(&tcs, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // set the Dec Offset component in PC-TCS

  sprintf(tcscmd, "OFFDEC %s", dect);
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

//------------------------------------------------------------------------------
//
// tcs.tguide - move the telescope as guiding offset RA/Dec in arcsec
//
// NOTE: Func was overall modified for debugging & adding large angle distance (v1.5.2)


int
cmd_tguide(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[CMDBUFLEN];  // command buffer
  int rtn, i, raop, decop;
  int nStepRa, nStepDec, nStep, nSign;
  double ra_offset, dec_offset;

  //
  // Checking & Set everything for guiding command
  //

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%lf %lf", &ra_offset, &dec_offset);

  if(rtn<2) {
    strcpy(reply, "usage: tguide <ra_offset> <dec_offset>");
    strcat(reply, "  /  <ra_offset>: +x.xx  <dec_offset>: +x.xx");
    strcat(reply, "  (angular distance in arcsec)");
    return CMD_ERR;
  }

  // check RA guiding offset value

  if( fabs(ra_offset) > MAX_GUIDEOFFSET_RA ) {
    sprintf(reply, "<ra_offset> value is out of range (Max. %.1f asec)", MAX_GUIDEOFFSET_RA);
    return CMD_ERR;
  }

  // set RA guiding operation flag

  if( fabs(ra_offset) < tcs.GuideMinOffRA )  raop = 0;  // don't move RA
  else                                       raop = 1;  // move RA

  // check Dec guiding offset value

  if( fabs(dec_offset) > MAX_GUIDEOFFSET_DEC ) {
    sprintf(reply, "<dec_offset> value is out of range (Max. %.1f asec)", MAX_GUIDEOFFSET_DEC);
    return CMD_ERR;
  }

  // set Dec guiding operation flag

  if( fabs(dec_offset) < tcs.GuideMinOffDec )  decop = 0;  // don't move Dec
  else                                         decop = 1;  // move Dec

  //
  // Start RA guide-offset move
  //

  if(raop) {

    // convert RA offset(arcsec) to PC-TCS guiding step(encoder count)

    nStepRa = (int)(ra_offset/tcs.GuideStepRA/cos(tcs.dDec*DEG2RAD)+0.5);
              //// step is not in angular distance, so must apply cos(DEC) at v1.2.3

    nSign = SIGN(nStepRa);  // if nStepRa < 0 then nSign = -1 else nSign = +1
    nStepRa *= nSign;       // making nStepRa be positive integer

    for( i=0 ; nStepRa ; i++ ) {

      // build STEPRA command string

      nStep = MIN(nStepRa, 30000);

      sprintf(tcscmd, "STEPRA %+d", nSign*nStep);

      // command STEPRA to TCS

      rtn = cmd_tcmd(tcscmd, EXEC, reply);
      if(rtn!=CMD_OK) return CMD_ERR;

      nStepRa -= nStep;

    }

	}

  //
  // Execution code update between RA and Dec commands
  //

  if( raop && decop ) {  // if both RA and Dec is operated

    rtn = TcsTelemetry(&tcs, reply);
    if(rtn!=CMD_OK) return CMD_ERR;

  }

  //
  // Start Dec guide-offset move
  //

  if(decop) {

    // convert Dec offset(arcsec) to PC-TCS guiding step(encoder count)

    nStepDec = (int)(dec_offset/tcs.GuideStepDec+0.5);
              //// step is not in angular distance, so must apply cos(DEC) at v1.2.3

    nSign = SIGN(nStepDec);  // if nStepDec < 0 then nSign = -1 else nSign = +1
    nStepDec *= nSign;       // making nStepDec be positive integer

    for( i=0 ; nStepDec ; i++ ) {

      // build STEPDEC command string

      nStep = MIN(nStepDec, 30000);

      sprintf(tcscmd, "STEPDEC %+d", nSign*nStep);

      // command STEPDEC to TCS

      rtn = cmd_tcmd(tcscmd, EXEC, reply);
      if(rtn!=CMD_OK) return CMD_ERR;

      nStepDec -= nStep;

    }

	}

  // all done

  strcpy(reply, "guiding offset move complete");
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// tcs.tstop - command cancel - stop all commanded motions
//

int
cmd_tstop(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[CMDBUFLEN];  // command buffer
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

//------------------------------------------------------------------------------
//
// tcs.tstop - command cancel - stop all commanded motions
//

int
cmd_tstow(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[CMDBUFLEN];  // command buffer
  int rtn;

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // command Cancel slew with full ramp down

  sprintf(tcscmd, "MOVSTOW");
  rtn = cmd_tcmd(tcscmd, EXEC, reply);
  if(rtn!=CMD_OK) return CMD_ERR;

  // all done

  strcpy(reply, "stow commanded");
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// tcs.tdi - command DECLAREINIT: Synchronizes the telescope by forcing 
//           the current position to become the same as the commanded position.
//

int
cmd_tdi(char *args, MsgType msgtype, char *reply)
{
  char tcscmd[CMDBUFLEN];  // command buffer
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

//------------------------------------------------------------------------------
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
    sprintf(cmsg, "STATUS: AUX Link Initialized at a request from ISIS\n");
    _msgout(cmsg);
  }
  else {
    GRNTEXT;  // TXTRESET in KeyboardCommand()
  }

  return CMD_OK;
}

//------------------------------------------------------------------------------
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
    sprintf(cmsg, "STATUS: AUX Link closed at a request from ISIS\n");
    _msgout(cmsg);
  }
  else {
    REDTEXT;  // TXTRESET in KeyboardCommand()
  }

  return CMD_OK;
}

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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
  //sprintf(curtime, "%02d:%02d:%06.3f", curutc.hour, curutc.min, curutc.sec);
  sprintf(curtime, "%02d:%02d:%02d.%03d", curutc.hour, curutc.min,
                    (int)curutc.sec, (int)(curutc.sec*1000.)%1000 );  // v1.6.4

  switch (aux.Link) {

  case AUX_UP:
    sprintf(reply, "AUXSTATUS AUXQDATE=%sT%s TIMESYS=UTC TELID=%s AUXLINK=Up AUXARC=%s"
                   " AUXUDATE=%sT%s",
                    curdate, curtime, aux.FitsTelID, aux.ArcMode?"Enabled":"Disabled", 
                    aux.Date, aux.UTC);

    sprintf(reply, "%s FSSTAT=%s", reply, AuxStatusArg(aux.Statuses[AUX_IDX_FS]));
    if(aux.Statuses[AUX_IDX_FS]!=AUX_STATUS_NC) {
      sprintf(reply, "%s FILTOP=%s FILNUM=%d FILTER=%s SHUTOP=%s SHUTTER=%s", reply,
                     AuxStatusArg(aux.FS_FilterOpStat), 
                     aux.FS_FilterNum, aux.FS_FilterName,  
                     AuxStatusArg(aux.FS_ShutOpStat), AuxStatusArg(aux.FS_ShutStatus));
      //sprintf(reply, "%s FILTNUM=%d FILTNAME=%s", reply, aux.FS_FilterNum, aux.FS_FilterName );
      // --> temporary addtion at v1.4.6
      // --> removed at v1.6.1
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

//------------------------------------------------------------------------------
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
  //sprintf(curtime, "%02d:%02d:%06.3f", curutc.hour, curutc.min, curutc.sec);
  sprintf(curtime, "%02d:%02d:%02d.%03d", curutc.hour, curutc.min, 
                    (int)curutc.sec, (int)(curutc.sec*1000.)%1000 );  // v1.6.4

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

//------------------------------------------------------------------------------
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
//   FILNUM   : current filter number (no:0 / filter 1~4:1~4 / 2 more:5 / unknown:-1)
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

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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

  memset(cmd, 0, sizeof(cmd));
  cmdlen = sprintf(cmd, "%s %s %03d %s\n", aux.TelID, aux.SysID, PID_REQCMD, strupr(args));

  // send the command to Telcom via aux link

  rtn = send(aux.FD, cmd, cmdlen, 0);
  if( rtn < cmdlen ) {
    sprintf(reply, "command send failed - cmd='%s' cmdlen=%d, sentbyte=%d", 
                   args, cmdlen, rtn);
    return CMD_ERR;
  }
  {//verbose
    sprintf(cmsg, " AUX OUT: %s", cmd);_vmsgout(cmsg);
  }

  // receive the response of command

  memset(cmd, 0, sizeof(cmd));
  cmdlen = recv(aux.FD, cmd, CMDBUFLEN-1, 0);
  if(cmdlen<=0) {
    sprintf(reply, "response recv failed - recvbyte = %d", cmdlen);
    return CMD_ERR;
  }
  cmd[cmdlen] = NULL;
  {//verbose
    sprintf(cmsg, " AUX IN : %s", cmd);_vmsgout(cmsg);
  }

  // check the response from aux ctrl server

  rtn = sscanf(cmd, "%*s %*s %*s %[^\n]", rsp);
  if( rtn != 1 ) {
    sprintf(reply, "unrecognized response - not scannable(argnum=%d)", rtn);
    return CMD_ERR;
  }

  // common response for general operationg cmd

  if(strcasecmp(rsp,"OK")==0) {
    sprintf(reply, "ACMD %s OK", args);
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

//------------------------------------------------------------------------------
//
// aux.filter - change filters to the filter number commanded by a argument 
//

int
cmd_afilter(char *args, MsgType msgtype, char *reply)
{
  char cmd[CMDBUFLEN];
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

  aux.FS_CmdFilNum = fnum;  // v1.6.1

  // all done

  sprintf(reply, "change to filter #%d (%s) commanded", fnum, aux.FS_FilNames[fnum]);
  return CMD_OK;

}

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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

/*
//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
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
  }FilNames
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
*/

//------------------------------------------------------------------------------
//
// util.tick
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
    
  //printf("                %04d-%02d-%02dT%02d:%02d:%06.3f    %04d %6.1f %6.1f\n", 
  //                        ut.year, ut.month, ut.day, ut.hour, ut.min, ut.sec,
  //                        idx, tick_curr-tick_zero, tick_curr-tick_prev);
  printf("                %04d-%02d-%02dT%02d:%02d:%02d.%03d    %04d %6.1f %6.1f\n", 
                          ut.year, ut.month, ut.day, 
                          ut.hour, ut.min, (int)ut.sec, (int)(ut.sec*1000.)%1000,  // v1.6.4
                          idx, tick_curr-tick_zero, tick_curr-tick_prev);

  tick_prev = tick_curr;

  return CMD_NOOP;

  USAGE:
    strcpy(reply, "usage: 'tick 0' = reset"
                  "  / 'tick' = +1 step  / 'tick 1' = set index");
    return CMD_ERR;
}

//------------------------------------------------------------------------------
//
// util.pmo: offseting for pointing model measurement
//

int
cmd_pmo(char *args, MsgType msgtype, char *reply)    // v1.5.5
{
  int rtn;
  char guistr[64];      // guiding string (args for cmd_tguide())
  double off_x, off_y;  // in arcsec, offset from image center

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // set offset parameters

  off_x = (double)( PM_OFF_X0 + PM_OFF_X1 ) * PM_PSCALE;
  off_y = (double)( PM_OFF_Y0 + PM_OFF_Y1 ) * PM_PSCALE;

  off_x *= +1.0;  // in case of using K chip, Tel moves to East  to move star to West
  off_y *= -1.0;  // in case of using K chip, Tel moves to South to move star to North

  // put x/y offset in arcsec into guistr & command offset

  sprintf(guistr, "%+.2f %+.2f", off_x, off_y);

  rtn = cmd_tguide(guistr, msgtype, reply);

  if(rtn==CMD_OK) sprintf(reply, "pm offset %s commanded", guistr);

  return rtn;
}

//------------------------------------------------------------------------------
//
// util.pmc: centering for pointing model measurement
//

int
cmd_pmc(char *args, MsgType msgtype, char *reply)    // v1.5.5
{
  int rtn;
  char guistr[64];      // guiding string (args for cmd_tguide())
  double coo_x, coo_y;  // in pixels, (x,y) coordination of star
  double off_x, off_y;  // in arcsec, offset for moving star to center

  // gotta be up to send commands

  if (tcs.Link != TCS_UP) {
    strcpy(reply, "TCS Link is IDLE/DOWN, remote commands unavailable");
    return CMD_ERR;
  }

  // check argument number

  rtn = sscanf(args, "%lf %lf", &coo_x, &coo_y);

  if(rtn<2) {
    strcpy(reply, "usage: cc <off_x> <off_y>  (in pixels)");
    return CMD_ERR;
  }

  // check x/y value, in case of K chip, used for star posi measurement

  if( coo_x>PM_COO_X0 || coo_x<(PM_COO_X0-PM_OFF_X1-PM_ERRCHK) ) {
    sprintf(reply, "<off_x> value (%.2f) is out of range", coo_x);
    return CMD_ERR;
  }

  if( coo_y>PM_COO_Y0 || coo_y<(PM_COO_Y0-PM_OFF_Y1-PM_ERRCHK) ) {
    sprintf(reply, "<off_y> value (%.2f) is out of range", coo_y);
    return CMD_ERR;
  }

  // set offset parameters

  off_x = (double)( PM_OFF_X0 + ( PM_COO_X0 - coo_x ) ) * PM_PSCALE;
  off_y = (double)( PM_OFF_Y0 + ( PM_COO_Y0 - coo_y ) ) * PM_PSCALE;

  off_x *= -1.0;  // in case of using K chip, Tel moves to West  to move star to East
  off_y *= +1.0;  // in case of using K chip, Tel moves to North to move star to South

  // put x/y offset in arcsec into guistr & command offset

  sprintf(guistr, "%+.2f %+.2f", off_x, off_y);

  rtn = cmd_tguide(guistr, msgtype, reply);

  if(rtn==CMD_OK) sprintf(reply, "pm offset %s commanded for centering", guistr);

  return rtn;
}

//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
//
// Utility functions
//

//
// *** PC-TCS CMD SUBROUTINES BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// TcsTelemetry - update TCS telemetry data, 
//                independent from telemetry update in main()
//

int
TcsTelemetry(pctcs_t *tcs, char *reply) 
{
  int rtn, i;
  char tcsbuf[CMDBUFLEN];  // v1.6.6.6 (old=2048)

  memset(tcsbuf,0,sizeof(tcsbuf));

  // Send the telemetry request CMD for execution code update

  rtn = send(tcs->FDcmd, tcs->RequestMsg, tcs->RequestLen, 0);
  if( rtn < tcs->RequestLen ) {
    sprintf(reply, "telemetry rquest CMD send failed - cmdlen = %d, sentbyte = %d", 
                   tcs->RequestLen, rtn);
    return -1;
  }

  // Waitting and Receive the telemetry data

  rtn = recv(tcs->FDcmd, tcsbuf, CMDBUFLEN-1, 0);

  if( rtn > 0 ) tcs->TelcomTick = SysTimestamp();
  if( rtn < tcs->MinTelemetryLen ) {  // not enough telemetry data length
    sprintf(reply, "telemetry data update failed - recvbyte = %d", rtn);
    return -1;
  }

  // Inspection and Update the telemetry data

  //// Ref: old-version code until v1.6.3
  //rtn = parse_comsoft(tcs,(tcsbuf+tcs->ReqHedLen));

  //// modified at at v1.6.5
  for(i=1;i<=TCS_DECODINGNUM;i++) {
    rtn = parse_comsoft(tcs,(tcsbuf+tcs->ReqHedLen));
    if(rtn<=0) { tcs->DecodingNum=i; break; }
  }

  //// modified at v1.6.3
  if(rtn<0) {
    sprintf(reply, "telemetry data update failed - %s", tcs->DataChkMsg);
    return -1;
  }
  else tcs->PctcsTick = SysTimestamp();  // if(rtn>=0), telemetry data acceptable

  //// Ref: old-version code until v1.6.2
  //if(rtn==0) tcs->PctcsTick = SysTimestamp();    // telemetry data ok
  //if(rtn<-4) {                                   // no data
  //  sprintf(reply, "telemetry data update failed - no data", rtn);
  //  return -1;
  //}

  // all done

  strcpy(reply, "TCS Telemetry data updated");
  return 0;

}

//------------------------------------------------------------------------------
//
// TcsSetEpoch - set PC-TCS Input Epoch to 2000
//

int
TcsSetEpoch(pctcs_t *tcs, char *reply)    // v1.2.2
{
  char cmd[CMDBUFLEN];
  //char errmsg[MSGBUFLEN];
  int rtn, verbose;

  verbose=client.isVerbose;
  client.isVerbose=0;

  sprintf(cmd, "EPOCH %.3f", TCS_INPUT_EPOCH);
  //rtn = cmd_tcmd(cmd, EXEC, errmsg);
  rtn = cmd_tcmd(cmd, EXEC, reply);

////  tcs->TelcomTick = SysTimestamp();  // reset idle time for Telcom link, v1.5?

  client.isVerbose=verbose;

  if(rtn!=CMD_OK)
  {
    //sprintf(reply, "TCS Input Epoch setting failed (%s)", errmsg);  // too long..

    //errmsg[4] = NULL;
    //sprintf(reply, "TCS Input Epoch setting failed (%s)", errmsg);

    reply[4] = NULL;
    sprintf(reply, "TCS Input Epoch setting failed (%s..)", reply);

    return -1;
  }

  sprintf(reply, "TCS Input Epoch set to %.3f success", TCS_INPUT_EPOCH);
  return 0;
}



//
// *** AUX CTRL SUBROUTINES BEGIN HERE ***
//

//------------------------------------------------------------------------------
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
  //static char arg[16][ARGBUFLEN];
  static char arg[16][32];  // v1.6.6.6
  int rtn, cmdlen;
  int verbose, LogVerbose;
  int argnum, arglen;
  double As, Ae, Aw, foc;
  static double As_prev, Ae_prev, Aw_prev;
  systime_t systime;

  // get All statuses for all the AUX subsystems ///////////////////////////////////

  // Request All statuses

  if(!client.Debug) {
    verbose=client.isVerbose;
    client.isVerbose=0;
  }

  LogVerbose = agent.LogVerbose;
  agent.LogVerbose = 0;

  sprintf(cmd, "ALL STATUS");
  rtn = cmd_acmd(cmd, EXEC, reply);

  if(!client.Debug) client.isVerbose=verbose;
  agent.LogVerbose = LogVerbose;

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
               //// Raw status string example:
               //// KMTNET AUX 123 
               //// FOCUSER STANDBY 0 0 0 +1.111 +1.222 +1.333 
               //// SHUTTER STANDBY 60.0 60.0 MID OPEN INACTIVE ON 
               //// FILTERS STANDBY 2 1 1 1 2 1 
               //// M1COVER STANDBY 100 
               //// CHILLER STANDBY +10.2 +5.0 OFF 
               //// ENVIRON STANDBY 13.2 13.6 13.7 20.4 15.5 15.6 0.0 OFF
               //// ==> 237 characters

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
  sprintf(aux->Date, "%04d-%02d-%02d", systime.year, systime.month, systime.day );
  //sprintf(aux->UTC, "%02d:%02d:%06.3f", systime.hour, systime.min, systime.sec);
  sprintf(aux->UTC, "%02d:%02d:%02d.%03d", systime.hour, systime.min,
                   (int)systime.sec, (int)(systime.sec*1000.)%1000 );  // v1.6.4


  // all done

  strcpy(reply, "AUX Telemetry data updated");
  return 0;
}

//------------------------------------------------------------------------------
//
// AuxFilterNameUpdate - Update the names for filter slides
//
// return 0 on success, -1 on errors
// if error, the AUXLink will be set to DOWN in main()
//

int
AuxFilterNameUpdate(auxctrl_t *aux, char *reply)    // v1.3.0
{
  char cmd[CMDBUFLEN];
  //char recv[CMDBUFLEN];  // changed to reply at v1.6.6.6
  char fname[4][16];
  int rtn, verbose;

  // Request filter names

  verbose=client.isVerbose;
  client.isVerbose=0;

  sprintf(cmd, "FILTERS FNAMES");
  //rtn = cmd_acmd(cmd, EXEC, recv);
  rtn = cmd_acmd(cmd, EXEC, reply);  // v1.6.6.6

  client.isVerbose=verbose;

  if(rtn!=CMD_OK) {
    //sprintf(reply, "AUX Filter names update failed (%s)\n", recv);
    sprintf(reply, "AUX Filter names update failed (%s)\n", reply);  // v1.6.6.6
    return -1;
  }

  // Receive filter name string
  //rtn = sscanf(recv, "%s %s %s %s", fname[0], fname[1], fname[2], fname[3]);
  rtn = sscanf(reply, "%s %s %s %s", fname[0], fname[1], fname[2], fname[3]);  // v1.6.6.6

  // Check argument number
  if(rtn!=4)
  {
      sprintf(reply, "AUX Filter names update failed (argnum=%d)\n", rtn);
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

  return 0;
}

//------------------------------------------------------------------------------
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
    //strcpy(aux->FS_FilterName, AUX_FS_FNAME_UNKNOWN);
    strcpy(aux->FS_FilterName, aux->FS_FilNames[aux->FS_CmdFilNum]);  // replaced at v1.6.1
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

   if(aux->FS_CmdFilNum==AUX_UNKNOWN) aux->FS_CmdFilNum = fnum;  // v1.6.1

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

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
//
// AuxStatusArg() - AUX argument encoding (int status definition --> message)
//

char
*AuxStatusArg(int status)
{
  static char arg[16][32];  // v1.6.6.6
  static int i=0;

  if(i==16) i=0;
  memset( arg[i], 0, sizeof(arg[i]) );

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

//------------------------------------------------------------------------------
//
// GetTstatStr/GetAstatStr - return TSTAT/ASTAT strings with '\n' terminator
//
// - GetTstatStr() is used only in rountine for tcslog so far. (noted at v1.6.3)
//

//void
//GetTstatStr(char *buf)  // v1.6.1
//{ 
//  cmd_tstat(NULL, EXEC, buf);
//  strcat(buf, "\n");
//}

//void
//GetTstatStr(char *buf)  // v1.6.2
//{ 
//  char traw[MIN_TCSBUF+1];  // +1 for NULL
//  cmd_tstat(NULL, EXEC, buf );
//  TcsStatusFlag = 0;
//  cmd_traw (NULL, EXEC, traw);
//  strcat(buf, "    \"");
//  strcat(buf, traw);
//  strcat(buf, "\"\n");
//}

//void
//GetTstatStr(char *buf)  // v1.6.3.0
//{ 
//  char traw[MIN_TCSBUF+1];  // +1 for NULL
//  cmd_tstat(NULL, EXEC, buf );
//  TcsStatusFlag = 0;
//  if (tcs.Link == TCS_UP) {
//    cmd_traw (NULL, EXEC, traw);
//    strcat(buf, "    \"");
//    strcat(buf, traw);
//    strcat(buf, "\"");
//  }
//  strcat(buf, "\n");
//}

void
GetTstatStr(char *buf)  // v1.6.3
{
  char tstat[STRLEN_TSTAT];
  cmd_tstat(NULL, EXEC, tstat);
  TcsStatusFlag = 0;
  if (tcs.Link == TCS_UP) sprintf(buf, "%s    \"%s\"    %d  %d  %s\n", tstat, tcs.RawPacket, tcs.DecodingNum, tcs.EncodingNum, tcs.DataChkMsg);
  else                    sprintf(buf, "%s\n", tstat);
}

void
GetAstatStr(char *buf)  // v1.6.1
{  
  cmd_astat(NULL, EXEC, buf);
  strcat(buf, "\n");
}


//------------------------------------------------------------------------------
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


//------------------------------------------------------------------------------
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
//------------------------------------------------------------------------------

char *
GetUTCTime(void)
{
  struct timeval tv;
  static char str[16];  // changed to [16] from [30] at v1.6.6.6
  struct tm *gmt;
  int tmsec;

  gettimeofday(&tv,NULL);
  gmt = gmtime(&tv.tv_sec);
  tmsec = (int)(tv.tv_usec/1000);
  sprintf(str,"%.2i:%.2i:%.2i.%03ld",gmt->tm_hour,gmt->tm_min,
          gmt->tm_sec,tmsec);

  return(str);

}

//------------------------------------------------------------------------------
//
// GetUTCDateTime() - read the system's UTC time clock and return the
//                    fine-grained time to msec precision
//
// Return: 
//   - systime_t 
//   - string yyyy-mm-ddThh:mm:ss.sss
//

char *
GetUTCDateTime(systime_t *datime)
{
  struct timeval tv;
  static char str[32];
  struct tm *gmt;
  int tmsec;
  systime_t systime;

  gettimeofday(&tv,NULL);
  gmt = gmtime(&tv.tv_sec);
  tmsec = (int)(tv.tv_usec/1000);

  systime.year  = gmt->tm_year + 1900;
  systime.month = (gmt->tm_mon)+1;
  systime.day   = gmt->tm_mday;

  systime.hour  = gmt->tm_hour;
  systime.min   = gmt->tm_min;
  systime.sec   = (double)(gmt->tm_sec) + ((double)(tmsec)/1000.0);

  //sprintf(str, "%04d-%02d-%02dT%02d:%02d:%06.3f",
  //              systime.year, systime.month, systime.day,
  //              systime.hour, systime.min, systime.sec    );
  sprintf(str, "%04d-%02d-%02dT%02d:%02d:%02d.%03d",
                systime.year, systime.month, systime.day,
                systime.hour, systime.min, 
                (int)systime.sec, (int)(systime.sec*1000.)%1000 );  // v1.6.4

  if(datime!=NULL) memcpy(datime, &systime, sizeof(systime_t));

  return(str);
}

//------------------------------------------------------------------------------
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

//------------------------------------------------------------------------------
//
// trans1060() - convert decimal to sexagesimal system and return the sign
//  - modified for debugging cat input error at v1.6.2, and 
//    for debugging the rounding off (to 60.0/59.9) error at v1.6.3/4
//  - added a new argument nDP for rounding dSec down 
//    to the designated decimal places at v1.6.4.0
//  - modified with robust and simplified code at v1.6.4.3
//    only tiny diff error despite no the trick (T)
//    For details, see the old code and comments of v1.6.4.3
//  * NOTE: nDP should be matched to rounding-off format in printf().
//    For examples, "%02.0f" --> nDP=0 / "%04.1f" --> nDP=1 / "%06.3f" --> nDP=3
//    Don't use only rounding-off format in printf() such as %02.0f, %05.2f, ..
//    to round dSec off to some decimal places to avoid 60.0 error of sec field.
//    nDP should be less than 10. (0 <= nDP <= 10)

char trans1060(double dHour, int *pnHour, int *pnMin, double *pdSec, int nDP)
{
  char cSign;
  double dMin, dRDT;

  if(nDP<0) nDP=0;
  dRDT = pow10(nDP);  // Rounding-down term, added at v1.6.4

  if(dHour<0.0) {cSign = '-';dHour*=-1.0;}
  else          {cSign = '+';           ;}

  dHour += 0.0000000006/3600;  // tunned in modification for v1.6.4.3
  //// a trick for debugging and a tunning term for precise conversion
  //// This value should be between ~0.00000000003/3600(1E-14) and 0.001/3600.

  *pnHour = (int)dHour;    dMin = ( dHour - (double)*pnHour ) * 60.0;
  *pnMin  = (int)dMin ;  *pdSec = ( dMin  - (double)*pnMin  ) * 60.0;

  *pdSec = fabs ( *pdSec );
  *pdSec = floor( *pdSec * dRDT ) / dRDT;

  return cSign;
}

//------------------------------------------------------------------------------
//
// _msgout()/_vmsgout()/_msglog() - console message output on console/logfile
//

void _msgout(char *msg)  // v1.6.0
{
  printf("\r%s", msg);
  TXTRESET;
  //rl_refresh_line(0,0);  // <--- Don't we need this?? check it !!
  //rl_refresh_line(0,0);  // re-activated at v1.6.6.3 --> make error TC%~~TC%
  if(!KeyCmdFlag) rl_refresh_line(0,0);  // v1.6.6.5

  _msglog(msg);

  if(agent.LogVerbose) {  // added for traw log at v1.6.2

    if(TcsStatusFlag) {  // logging the traw string when cmd_tcsstatus/cmd_tstat, v1.6.2
      //char traw[MIN_TCSBUF+1];  // +1 for NULL
      //cmd_traw (NULL, EXEC, traw);
      //sprintf(msg, "TRAW STR: \"%s\"\n", traw);_msglog(msg);  //// until v1.6.2
      if (tcs.Link != TCS_UP) strcpy(tcs.RawPacket, "TCS Link is IDLE/DOWN, No telemetry data");
      //sprintf(msg, "TRAW STR: \"%s\"    %s\n", tcs.RawPacket, tcs.DataChkMsg);_msglog(msg);  //// until v1.6.3
      sprintf(msg, "TRAW STR: \"%s\"    %d  %d  %s\n", tcs.RawPacket, tcs.DecodingNum, tcs.EncodingNum, tcs.DataChkMsg);_msglog(msg);  //// v1.6.5
      TcsStatusFlag = 0;      
    }

  }

}

void _vmsgout(char *msg)  // v1.6.0
{

  if(client.isVerbose) {
    printf("\r%s", msg);
    TXTRESET;
    //rl_refresh_line(0,0);  // <--- Don't we need this?? check it !!
    //rl_refresh_line(0,0);  // re-activated at v1.6.6.3 --> make error TC%~~TC%
    if(!KeyCmdFlag) rl_refresh_line(0,0);  // v1.6.6.5
  }
  else {
    TXTRESET;
  }

  if(agent.LogVerbose) {

    _msglog(msg);

    if(TcsStatusFlag) {  // logging the traw string when cmd_tcsstatus/cmd_tstat, v1.6.2
      //char traw[MIN_TCSBUF+1];  // +1 for NULL
      //cmd_traw (NULL, EXEC, traw);
      //sprintf(msg, "TRAW STR: \"%s\"\n", traw);_msglog(msg);  //// until v1.6.2
      if (tcs.Link != TCS_UP) strcpy(tcs.RawPacket, "TCS Link is IDLE/DOWN, No telemetry data");
      //sprintf(msg, "TRAW STR: \"%s\"    %s\n", tcs.RawPacket, tcs.DataChkMsg);_msglog(msg);  //// until v1.6.3
      sprintf(msg, "TRAW STR: \"%s\"    %d  %d  %s\n", tcs.RawPacket, tcs.DecodingNum, tcs.EncodingNum, tcs.DataChkMsg);_msglog(msg);  //// v1.6.5
      TcsStatusFlag = 0;      
    }

  }

}

void _msglog(const char *msg)  // v1.6.0
{
  if(agent.LogMsg!=NULL) {
    fprintf(agent.LogMsg, "[%s]  %s", GetUTCDateTime(NULL), msg);
  }
}

void _tcslog(const char *tstat)  // v1.6.1
{
  if(agent.LogTcs!=NULL) {
    fprintf(agent.LogTcs, "[%s]  %s", GetUTCDateTime(NULL), tstat);
  }
}

void _auxlog(const char *astat)  // v1.6.1
{
  if(agent.LogAux!=NULL) {
    fprintf(agent.LogAux, "[%s]  %s", GetUTCDateTime(NULL), astat);
  }
}

//------------------------------------------------------------------------------
//
// offset_blg() - KMTNet BLG offset correction v20150702
//
// Author:
//   S. Kim, KASI KMTNet team
//   slkim@kasi.re.kr
//   2015 July 2
//

#define NDATA  500

//#define M_PI 3.14159265358979323846

int offset_blg(double *ra, double *dec, double ha, const char *table)
{
    int i, nn;
    double  ora,odec, HA[NDATA],oRA[NDATA],oDEC[NDATA];
    char field[300];
    FILE *in;

    if( (in=fopen(table,"r")) == NULL) { 
        puts("File Read Error: No Offset Table");  
        return -1;  
    }
    fgets(field, 300, in);
    for(i=0; i<NDATA && !feof(in); i++) {
        sscanf(field,"%lf %lf %lf", &HA[i], &oRA[i], &oDEC[i]);  /* The table should be an increasing order of HA */
        fgets(field, 300, in);
    }
    fclose(in);  
    nn = i;

    if(ha<HA[0] || ha>HA[nn-1]) {
        printf("Input Data Error: Beyond the Range of Offset Table [%.1lf,%.1f]\n", HA[0], HA[nn-1]);
        return -2;
    }
    for(i=1; i<nn; i++) 
        if(ha <= HA[i]) {
            ora =  oRA[i-1]  + (oRA[i] -oRA[i-1]) *(ha-HA[i-1])/(HA[i]-HA[i-1]);  /* unit in arcsec */
            odec = oDEC[i-1] + (oDEC[i]-oDEC[i-1])*(ha-HA[i-1])/(HA[i]-HA[i-1]);  /* unit in arcsec */
            break;
        }
    (*ra)  +=  ora/15.0/3600.0/cos((*dec)*M_PI/180.0);  /* unit in hour */
    (*dec) += odec/3600.0;                              /* unit in degree */
    return 1;
}





//------------------------------------------------------------------------------
//
// Command Template
//

/*
int
cmd_xxx(char *args, MsgType msgtype, char *reply)
{

  if (badness)
    return CMD_ERR;
  
  return CMD_OK;
}
*/

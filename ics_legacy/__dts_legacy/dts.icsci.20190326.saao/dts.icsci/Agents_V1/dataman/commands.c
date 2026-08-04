//
// commands.c - application command interpreter
//

/*!
  \file commands.c 
  \brief Client application command interpreter functions.

  This module contains the command "action" functions called to
  service client commands.  These consist of a suite of \arg "common"
  client action functions common to most ISIS clients \arg
  client-specific functions that perform the client's particular tasks
  \arg common interface routines for keyboard and ISIS socket
  interfaces.

  The common client commands include the following:

  These 3 commands are \b REQUIRED of all ISIS client apps:
  \arg \c cmd_quit() terminate a client session (QUIT)
  \arg \c cmd_ping() communications handshaking request (PING) from a remote ISIS node
  \arg \c cmd_pong() communications handshaking acknowledgment (PONG) from
  a remote ISIS node

  These client commands are recommended for most apps:
  \arg \c cmd_version() Report application version information (VERSION)
  \arg \c cmd_info() Report client runtime configuration (INFO, sometimes
  CONFIG in legacy apps).

  These are common commands relevant for the CLI, but generally not available
  to remote ISIS nodes (e.g., they test that the message type is EXEC:):
  \arg \c cmd_verbose() Toggle verbose output to the client console on/off (VERBOSE)
  \arg \c cmd_debug()   Toggle debugging (super-verbose) output to console on/off (DEBUG)
  \arg \c cmd_help()    List interactive client commands (HELP or ?)
  \arg \c cmd_history() Print the recent interactive command history (HISTORY)

  These are then followed by cmd_xxx() action functions that implement the
  various client tasks.

  At the end of this file are the template I/O handlers used by the
  command interpreter:
  \arg KeyboardCommand() Keyboard command handler (command-line interface)
  \arg SocketCommand() Socket command/message handler (client socket interface)

  \author R. Pogge, OSU Astronomy Dept. (pogge@astronomy.ohio-state.edu)
  \date 2003 October 13
*/

#include "isisclient.h" // ISIS common client library header
#include "client.h"     // Custom client application header file
#include "commands.h"   // Command action functions header file

//***************************************************************************
//
// Common client commands
//
// Commands common to most ISIS client applications are defined here.
//

//---------------------------------------------------------------------------
//
// quit command - allowed only if EXEC from remote hosts (keyboard
//                commands are always EXEC.

/*!
  \brief QUIT command - terminate the client session
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK if command executed without errors, #CMD_ERR if an error
  occurred.  On errors \e reply contains the error message.

  \par Usage:
  quit

  Executes the application QUIT command.  Only works if msgtype=EXEC,
  indicating that it is an IMPv2 executive command.  This prevents
  remote applications from prematurely terminating this application
  by sending a QUIT command unqualified by the EXEC: directive.

*/

int
cmd_quit(char *args, MsgType msgtype, char *reply)
{
  if (msgtype == EXEC) {
    client.KeepGoing=0;
    sprintf(reply,"%s=DISABLED MODE=OFFLINE",client.ID);
  }
  else {
    strcpy(reply,"Cannot execute quit command - operation not allowed except as EXEC:");
    return CMD_ERR;
  }
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// ping - communication handshaking request
//

/*!
  \brief PING command - communication handshaking request
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK if command executed without errors, #CMD_ERR if an error
  occurred.  On errors reply contains the error message.

  This function is invoked when the client application receives a PING
  from a remote host requesting a communications handshaking reply.

  PINGs are actually handled separately in the SocketCommand() handler
  (nothing is done by the KeyboardCommand() handler) because the PONG
  sent back acknowledging the comm handshaking request is, in effect, a
  pseudo-command (implicit REQ:), not a "DONE:" response to a command
  request.  This exception to the general messaging syntax has to be
  handled carefully to prevent problems, especially to ensure backwards
  compatibility with older IMPv applications.

  \sa cmd_pong
*/

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

/*!
  \brief PONG command - communication handshaking acknowledgment
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_NOOP since PONG is a no-op pseudo command.

  For historical reasons, a "PONG" sent in acknowledgment of a software
  handshaking "PING" looks like an implicit REQ:, and hence like a
  "command request" sent to the recipient, even though it isn't.  It is,
  however, an exception to the strict messaging protocol, which is why
  it needs a separate handler.

  cmd_pong doesn't do anything except return a #CMD_NOOP (since this
  "command" must NOT result in a reply back to the sender).  In more
  sophisticated apps, we might actually use receipt of a pong to do
  something useful (e.g., help build up a node table), so at the very
  least this module works as a placeholder for future expansion.

  \sa cmd_ping
*/

int
cmd_pong(char *args, MsgType msgtype, char *reply)
{
  if (client.isVerbose)
    printf("PONG received\n");
  return CMD_NOOP;
}

//---------------------------------------------------------------------------
//
// version - report application version and compilation info
//

/*!
  \brief VERSION command - report application version and compilation info
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK

  \par Usage:
  version

  Creates an IMPv2 message (in the \e reply string) with the version
  number and any relevant compilation information (e.g., date and time
  of compilation).  VERSION allows a way for users or remote apps to
  verify the runtime version of the current application.

  Example output:
  <pre>
  Version=v1.0 CompileDate=2004-Jun-11 CompileTime=17:08:15
  </pre>
*/

int
cmd_version(char *args, MsgType msgtype, char *reply)
{
  
  sprintf(reply,"dataman Version=%s CompileDate=%s CompileTime=%s",
	  APP_VERSION,APP_COMPDATE,APP_COMPTIME);
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// verbose - toggle verbose console output
//
  
/*!
  \brief VERBOSE command - toggle verbose console output on/off
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK

  \par Usage:
  verbose

  Sets the client isVerbose flag to 1 (enabled) if currently 0
  (disabled) and vis-versa.  Verbose output mode is used for basic
  client debugging information by printing extra information on the
  application console screen.  Disabling throttles verbose console
  output.  VERBOSE mode is normally disabled during normal operations.

  In general "Verbose" output refers only to client application level
  output (i.e., echoing socket message traffic, printing status update
  info, etc.).  An more chatty DEBUG mode is provided that prints more
  engineering-level info for detailed low-level system debugging.

  \sa cmd_debug
*/

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
// debug - toggle debugging output (super-verbose mode)
//

/*!
  \brief DEBUG command - toggle debugging (super-verbose) console output on/off
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK

  \par Usage:
  debug

  Sets the client Debug flag to 1 (enabled) if currently 0 (disabled)
  and vis-versa.  

  DEBUG mode is a super-verbose mode that spews lots of I/O chatter onto
  the application console, useful during client debugging or for
  troubleshooting.  For example, in client applications that control
  stepper motors, the full motor control chatter is echoed to the console
  during DEBUG mode to enable the user to follow the steps the system is
  (or is not) taking, watch encoder and limit switches assert (or not), 
  etc.  DEBUG is normally disabled during normal user operations.

  \sa cmd_verbose
*/

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
// info - report application runtime configuration information
//

/*!
  \brief INFO command - report client application runtime information
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on successful creation of the info report, #CMD_ERR
  if errors encountered.

  \par Usage:
  info

  Creates a summary report of the current client application's runtime
  configuration as an IMPv2-compliant message string in which the
  runtime parameters are reported as keyword=value pairs.

  The format of cmd_info should be tailored specifically for the
  particular client application.  If a client controls specific
  instrument or interface functions, the state of those functions should
  be reported in the info string, making it an omnibus "what is your
  status" command.

  Example Output:
  <pre>
ID=AC Host=darkstar:10702 Mode=STANDALONE Verbose -DEBUG rcfile=port2.ini
  </pre>
*/

int
cmd_info(char *args, MsgType msgtype, char *reply)
{
  int i;

  // Start with the node ID, and host info

  sprintf(reply,"HostID=%s HostAddr=%s:%d",
	  client.ID, client.Host, client.Port);

  // If configured as an ISIS client, report this and the ISIS host:port info,
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

  // Add more stuff about the app here...

  // Report application runtime flags

  sprintf(reply,"%s %s %s",reply,
	  ((client.isVerbose) ? "Verbose" : "Concise"),
	  ((client.Debug) ? "+DEBUG" : "-DEBUG"));
	 
  // Finally, report the application's runtime config info as required

  sprintf(reply,"%s rcfile=%s",reply,client.rcFile);

  return CMD_OK;

}

//---------------------------------------------------------------------------
//
// help - print a list of available commands on the client console
//

/*!
  \brief HELP command - print a list of commands on the client console
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_NOOP on success, #CMD_ERR if help executed as a non-EXEC: command

  \par Usage:
  help [cmd]

  cmd_help is usually invoked by the HELP or ? commands.  It prints a
  list of all interactive commands on the client application's console
  screen.  It is only meant to be executed as an EXEC: message type.  If
  the command is not qualifed as EXEC:, it returns an error.

  If an argument is given, it tries to find that string in the command
  list, and if successful, prints a brief description and usage message.

  Help is meant to be simple.  It can give help on particular commands
  (really a reminder of the command's function and syntax), or a list
  of all commands.
  
*/

int
cmd_help(char *args, MsgType msgtype, char *reply)
{
  int i, icmd, found;
  int ls;
  char argbuf[32];

  if (msgtype!=EXEC) {
    strcpy(reply,"Cannot exec help command - remote operation not allowed");
    return CMD_ERR;
  }

  if (strlen(args)>0) {  // we are being asked for help on a specific command
    GetArg(args,1,argbuf);

    found = 0;
    for (i=0; i<NumCommands; i++) {
      if (strcasecmp(cmdtab[i].cmd,argbuf)==0) {
	found++;
	icmd = i;
	break;
      }
    }
    if (found > 0) {
      printf("  %s - %s\n",cmdtab[i].cmd,cmdtab[i].description);
      printf("  usage: %s\n",cmdtab[i].usage);
    } 
    else {
      printf("Unknown Command '%s' (type 'help' to list all commands)\n");
    }
  }
  else { // no arguments, print the whole command list

    printf("Interactive Command Summary:\n");
    for (i=0; i<NumCommands; i++) {
      ls = strlen(cmdtab[i].usage);
      if (ls > 0) {
	if (ls < 6)
	  printf("  %s\t\t - %s\n",cmdtab[i].usage,cmdtab[i].description);

	else if (ls > 13)
	  printf("  %s - %s\n",cmdtab[i].usage,cmdtab[i].description);

	else
	  printf("  %s\t - %s\n",cmdtab[i].usage,cmdtab[i].description);
      }
    }
    printf("Command History:\n");
    printf("  !!  \t\t - repeat last command\n");
    printf("  !cmd\t\t - repeat last command matching 'cmd'\n");
    printf("  arrow keys for command-line & history editing\n");
  }

  return CMD_NOOP;
    
}

//---------------------------------------------------------------------------
//
// history - show the history list
//

#include <readline/readline.h>  // Gnu readline utility
#include <readline/history.h>   // Gnu history utility

/*!
  \brief HISTORY command - show the application's interactive command history
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_NOOP on success, #CMD_ERR if history executed as a non-EXEC: 
  command

  \par Usage:
  history

  List the application's interactive command history on the console.
  The KeyboardCommand() function uses the GNU readline and history
  system to record all commands entered.  This prints a list of the most
  recent commands.

  \sa KeyboardCommand()
*/

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

//***************************************************************************
//
// *** CLIENT-SPECIFIC COMMANDS BEGIN HERE ***
//

/*!  
  \brief STATUS command - report the client status
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  status

  Returns the current client status info as an IMPv2-compliant
  status message.  

*/

int
cmd_status(char *args, MsgType msgtype, char *reply)
{

  // Are we doing data transfer?

  sprintf(reply,"%s SrcPath=%s %s ImgPath=%s %s BufSize=%d",
	  ((xfer.doTransfer) ? "+Transfer" : "-Transfer"),
	    xfer.srcPath,
	  ((xfer.marksrc) ? "+Mark" : "-Mark"),
	  xfer.imgPath,
	  ((xfer.backimg) ? "+BackUp" : "-BackUp"),
	  xfer.bufsize);

  // Doing image display?

  sprintf(reply,"%s %s Min=%.3f Max=%.3f",reply,
	  ((tv.doDisplay) ? "+AutoDisp" : "-AutoDisp"),
	  tv.z1,tv.z2);

  // Post-Processing info goes here

  return CMD_OK;
}

/*!
  \brief PROCESS command - process a file
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_STATUS on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  process fname

  Processes the named file through the processing pipeline.  If enabled,
  the steps followed, in order, are:
  <ol>
  <li>Transfer Images (if enabled, otherwise image in imgPath)
  <li>Display Images
  <li>1st External PostProcessing Script
  <li>2nd External PostProcessing Script<br>
  ...
  <li>6th External PostProcessing Script
  </ol>
  If process is given with no arguments, it will report the
  processing status (steps and order to be followed).

  Since all post-processing is "offline", only STATUS: messages are
  generated, to avoid sending a DONE: that might interrupt some other
  process the exposure-initiating client is doing.

*/

int
cmd_process(char *args, MsgType msgtype, char *reply)
{
  char argbuf[32];
  char infile[128];  // name of the file to process
  char prfile[128];  // full name (path/name) of image file
  char msgstr[128];  // generic message string
  int i, iproc;

  // Process arguments, if no arguments, send a processing report
  // listing the steps we would have taken if we were actually given a
  // file to process

  if (strlen(args)>0) { // process arguments
    GetArg(args,1,argbuf);
    strcpy(infile,argbuf);

    memset(prfile,0,sizeof(prfile));
    sprintf(prfile,"%s/%s",xfer.imgPath,infile);

    // Transfer the image if enabled

    if (xfer.doTransfer) {
      if (client.isVerbose)
	printf("Transferring image %s...\n",infile);
      if (TransferImage(&xfer,infile,msgstr)<0) {
	sprintf(reply,"Image Transfer failed - %s",msgstr);
	return CMD_ERR;
      }
    }

    // Display the image, if enabled

    memset(msgstr,0,sizeof(msgstr));
    if (tv.doDisplay) {
      if (client.isVerbose)
	printf("Displaying image %s...\n",infile);
      if (DisplayImage(&img,&tv,prfile,msgstr)<0) {
	sprintf(reply,"Image Display failed - %s",msgstr);
	return CMD_ERR;
      }
    }

    // Do any required post-processing steps

    if (post.Nproc>0) {
      for (i=0;i<MAX_PROCS;i++) {
	if (post.doProc[i]) {
	  iproc = i+1;
	  if (client.isVerbose)
	    printf("Executing external post-processing step %d on %s...\n",
		   iproc,infile);
	  if (PostProcImg(&post,iproc,prfile,msgstr)<0) {
	    sprintf(reply,"Post-Processing Step %d failed - %s",
		    iproc,msgstr);
	    return CMD_ERR;
	  }
	}
      }
      if (client.isVerbose)
	printf("%d external post-processing steps completed\n",post.Nproc);
    }

    // All done

    sprintf(reply,"Post-Processing of %s complete",infile);

  }
  else {
    sprintf(reply,"Nothing to process... infile='%s'",infile);
    return CMD_ERR;
  }

  return CMD_STATUS;  // only return STATUS: messages
}

//---------------------------------------------------------------------------
//
// Data Transfer Commands
//

/*!
  \brief DOTRANS command - Enable/Disable image transfer
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  dotrans
  
  Toggles image transfer on/off.  

*/

int
cmd_dotrans(char *args, MsgType msgtype, char *reply)
{
  if (xfer.doTransfer) {
    xfer.doTransfer = 0;
    strcpy(reply,"-Transfer - Image Transfer Disabled");
  }
  else {
    xfer.doTransfer = 1;
    sprintf(reply,"+Transfer - Image Transfer Enabled from SrcPath=%s to ImgPath=%s",
	    xfer.srcPath,xfer.imgPath);
  }
  return CMD_OK;
}

/*!
  \brief TRANSFER command - transfer an image from the source to destination paths

  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  transfer [fname] 

  Transfers the filename (byte-for-byte copy) from the source
  directory path (#xfer_params::srcPath) to the destination directory
  path (#xfer_params::imgPath).  On successful transfers, the
  #xfer_params::file string is set to the name of the transferred
  image file.

  Images are not allowed to be clobbered if the #xfer_params::clobber
  flag is set to 0.

  If given without arguments, this command reports the current
  transfer paths and the overwrite and transfer status.

  All the dirty work is done by TransferImage().

  \sa TransferImage()
*/

int
cmd_transfer(char *args, MsgType msgtype, char *reply)
{
  char msgstr[128];

  // can't do this unless file transfer is enabled

  if (!xfer.doTransfer) {
    strcpy(reply,"File Transfer not enabled (see DoTrans)");
    return CMD_ERR;
  }

  // Do the file transfer, or report path if no arguments given

  if (strlen(args)>0) { // do it
    memset(msgstr,0,sizeof(msgstr));
    if (TransferImage(&xfer,args,msgstr)<0) {
      sprintf(reply,"Transfer failed - %s",msgstr);
      return CMD_ERR;
    }
    sprintf(reply,"Transfer Complete - %s",msgstr);
  }
  else {
    sprintf(reply,"Transfer Path: from SrcPath=%s to ImgPath=%s BufSize=%d bytes",
	    xfer.srcPath,xfer.imgPath,xfer.bufsize);
  }
  return CMD_OK;
}

/*!
  \brief SRCPATH command - Set/Query the image source path for image transfers

  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  srcpath [path]

  Sets the file path to be used as the source of raw images for image
  transfers.  If given with no arguments, it reports the current
  source path.

  \sa cmd_imgpath()
*/

int
cmd_srcpath(char *args, MsgType msgtype, char *reply)
{
  char argbuf[32];

  if (strlen(args)>0) { // have arguments to process
    GetArg(args,1,argbuf);

    // Test the path to see if valid

    if (isDir(argbuf)<1) {
      sprintf(reply,"Image source path '%s' is not a valid directory",argbuf);
      return CMD_ERR;
    }
    if (argbuf[strlen(argbuf)-1] == '/') // strip off any extraneous \'s
      argbuf[strlen(argbuf)-1] = '\0';
    strcpy(xfer.srcPath,argbuf);
  }
  sprintf(reply,"SrcPath=%s",xfer.srcPath);
  return CMD_OK;
}

/*!
  \brief IMGPATH command - Set/Query the image destination path for image transfers

  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  imgpath [path]

  Sets the file path to be used as the destinatoin of raw images for
  image transfers.  If given with no arguments, it reports the current
  source path.  This path is also used for all subsequent
  post-processing steps, so it must be defined even if file transfer
  is not being done.

  \sa cmd_srcpath()
*/

int
cmd_imgpath(char *args, MsgType msgtype, char *reply)
{
  char argbuf[32];

  if (strlen(args)>0) { // have arguments to process
    GetArg(args,1,argbuf);

    // Test the path to see if valid

    if (isDir(argbuf)<1) {
      sprintf(reply,"Image destination path '%s' is not a valid directory",argbuf);
      return CMD_ERR;
    }
    if (argbuf[strlen(argbuf)-1] == '/') // strip off any extraneous \'s
      argbuf[strlen(argbuf)-1] = '\0';
    strcpy(xfer.imgPath,argbuf);
  }
  sprintf(reply,"ImgPath=%s",xfer.imgPath);
  return CMD_OK;
}

/*!
  \brief CLOBBER command - Enable/Disable image file clobber/noclobber on transfers
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  clobber
  
  Toggles image clobber/noclobber mode.  Clobber allows files on the
  destination disk to be overwritten by new images with the same
  filename by the transfer process.  NoClobber mode will refuse to
  overwrite any files it finds on the destination disk

*/

int
cmd_clobber(char *args, MsgType msgtype, char *reply)
{
  if (xfer.clobber) {
    xfer.clobber = 0;
    strcpy(reply,"-Clobber - Image Transfers will not overwrite existing files (noclobber)");
  }
  else {
    xfer.clobber = 1;
    strcpy(reply,"+Clobber - Image Transfers may overwrite existing files (clobber)");
  }
  return CMD_OK;
}

/*!
  \brief MARKSRC command - Enable/Disable source file-was-processed mark/nomark on transfers
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  marksrc
  
  Toggles whether or not the source file is "marked" as having been successfully
  transferred from the srcdisk by appending ".proc" to the filename.  "mark" means
  mark source images as processed, "nomark" means don't.   Used to make it obvious
  that a file on the source disk has already been handled by DataMan.

*/

int
cmd_marksrc(char *args, MsgType msgtype, char *reply)
{
  if (xfer.marksrc) {
    xfer.marksrc = 0;
    strcpy(reply,"-Mark - Source images not marked after transfer (nomark)");
  }
  else {
    xfer.marksrc = 1;
    strcpy(reply,"+Mark - Source images marked by the .proc extension after transfer (mark)");
  }
  return CMD_OK;
}

/*!
  \brief BACKUP command - Enable/Disable source file-was-processed mark/nomark on transfers
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  backup
  
  Toggles whether or not the source file is "marked" as having been successfully
  transferred from the srcdisk by appending ".proc" to the filename.  "mark" means
  mark source images as processed, "nomark" means don't.   Used to make it obvious
  that a file on the source disk has already been handled by DataMan.

*/

int
cmd_backimg(char *args, MsgType msgtype, char *reply)
{
  if (xfer.backimg) {
    xfer.backimg = 0;
    strcpy(reply,"-BackUp - Destination images not backed up if transfer clobbers (noback)");
  }
  else {
    xfer.backimg = 1;
    strcpy(reply,"+BackUp - Destination image is backed up (.bak) if transfer would clobber");
  }
  return CMD_OK;
}

/*!  
  \brief XFERINFO command - print the image transfer configuration on stdout
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  xferinfo

  Prints the image transfer configuration info on stdout.  This is an
  engineering command not accessible to remote hosts.

*/

int
cmd_xferinfo(char *args, MsgType msgtype, char *reply)
{
  if (msgtype == EXEC) {
    XferInfo(&xfer);
  }
  else {
    strcpy(reply,"Cannot execute XFERINFO command except as EXEC:");
    return CMD_ERR;
  }
  strcpy(reply,"XFERINFO dump complete.");
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// TV Display Commands
//

/*!
  \brief DODISP command - Enable/Disable automatic image display
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  dodisp
  
  Toggles the autodisplay on/off.  AutoDisplay allows automatic
  display of images during processing (after transfer, before
  execution of post-processing scripts) with the PROCESS command.

*/

int
cmd_dodisp(char *args, MsgType msgtype, char *reply)
{
  if (tv.doDisplay) {
    tv.doDisplay = 0;
    strcpy(reply,"-AutoDisp - AutoDisplay Disabled");
  }
  else {
    tv.doDisplay = 1;
    sprintf(reply,"+AutoDisp - AutoDisplay Enabled with Min=%.3f Max=%.3f",
	    tv.z1,tv.z2);
  }
  return CMD_OK;
}

/*!  
  \brief TV command - display an image 
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  tv file [z1 z2]

  Reads FITS image file into memory. If optional keywords "z1 z2" are
  it sets the display scale, otherwise it uses the default display
  scale.

  If given without arguments, it reports the name and scale parameters
  of the image currently on the display.

*/

int
cmd_tv(char *args, MsgType msgtype, char *reply)
{
  char argbuf[32];
  int nargs;
  float z1, z2;
  char infile[64];

  if (strlen(args)>0) { // have arguments to process
    nargs = sscanf(args,"%s %f %f",infile,&z1,&z2);
    if (nargs == 0) {
      sprintf(reply,"Unrecognized command arguments '%s'",args);
      return CMD_ERR;
    }
    if (nargs == 3) {
      tv.z1 = z1;
      tv.z2 = z2;
    }
    strcpy(img.fullname,infile);

    // Read in the image (handles all memory allocation issues)

    if (ReadFITSFile(&img,infile,reply)<0) {
      strcat(reply," - Could not display image");
      return CMD_ERR;
    }

    // Display it

    if (client.Debug) printf("displaying image...\n");

    xtvload(img.data,img.nx,img.ny,img.nx,0,0,1,1,tv.z1,tv.z2,tv.Flip,1,0);

    if (client.Debug) printf("updating color map...\n");

    xtvcolorld(tv.r,tv.g,tv.b,256);

    if (strcasecmp(img.file,"NONE")==0)
      updatename(img.fullname,1);
    else
      updatename(img.file,1);

    updatename(img.object,2);

    sprintf(reply,"Displayed image %s with limits z1=%.3f z2=%.3f",
	    infile,tv.z1,tv.z2);

    return CMD_OK;
  }  

  sprintf(reply,"Current image=%s with limits z1=%.3f z2=%.3f",
	  img.fullname,tv.z1,tv.z2);

  return CMD_OK;

}

/*!  
  \brief DISPLAY command - (re)display the image 
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  display [z1 z2]

  Redisplays the image in memory. If optional keywords "z1 z2" are
  given, it remaps the image before display.

  If given without arguments, it redisplays the image in memory and
  reports the display scaling z1 and z2.

  \par Note:
  To provide simple back-compatibility with Prospero, we've made
  "displ" an alias for "display", and ignore the third argument
  (sat) that usually accompanies displ.

*/

int
cmd_display(char *args, MsgType msgtype, char *reply)
{
  char argbuf[32];

  // Note: if invoked using displ, could have an optional 3rd
  // argument, "sat", which we ignore here since as yet there is no
  // analogous setting for the xtv display.

  if (strlen(args)>0) { 
    GetArg(args,1,argbuf);
    tv.z1 = atoi(argbuf);
    GetArg(args,2,argbuf);
    tv.z2 = atoi(argbuf);
  }

  if (img.haveImage) {  // image in memory, display it
    xtvload(img.data,img.nx,img.ny,img.nx,0,0,1,1,
	    tv.z1,tv.z2,tv.Flip,1,0);

    // and reset the color bar
    xtvcolorld(tv.r,tv.g,tv.b,256);

    if (strcasecmp(img.file,"NONE")==0)
      updatename(img.fullname,1);
    else
      updatename(img.file,1);

    updatename(img.object,2);

  } 

  sprintf(reply,"z1=%.3f z2=%.3f",tv.z1,tv.z2);
  return CMD_OK;
}

/*!  
  \brief ERASE command - erase the image display
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  erase [vec]
  
  Erases the image display.  If the optional "vec" keyword is included,
  it only erases the graphics overlay plane (aka "vector plane").

*/

int
cmd_erase(char *args, MsgType msgtype, char *reply)
{
  if (strlen(args)>0) {
    if (strcasecmp(args,"VEC")==0) {
      vecclear();
      strcpy(reply,"Image display vector overlay cleared");
      return CMD_OK;
    }
    else {
      sprintf(reply,"Unknown option '%s', usage: ERASE [vec]",args);
      return CMD_ERR;
    }
  }

  imageerase();
  strcpy(reply,"Image display erased");
  return CMD_OK;
}

/*!  
  \brief DISPINFO command - print the image display configuration on stdout
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  dispinfo

  Prints the display configuration info on stdout.  This is an
  engineering command not accessible to remote hosts.

*/

int
cmd_dispinfo(char *args, MsgType msgtype, char *reply)
{
  if (msgtype == EXEC) {
    DispInfo(&tv);
  }
  else {
    strcpy(reply,"Cannot execute DISPINFO command except as EXEC:");
    return CMD_ERR;
  }
  strcpy(reply,"DISPINFO dump complete.");
  return CMD_OK;
}

/*!  
  \brief IMGINFO command - print the image display configuration on stdout
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  imginfo

  Prints the parameters of the currently attached image on stdout.
  If the command came in as an REQ, instead generate an IMPv2-format
  status message string.

*/

int
cmd_imginfo(char *args, MsgType msgtype, char *reply)
{
  if (img.haveImage) {
    sprintf(reply,"Image=%s Image.NX=%d Image.NY=%d Image.Filename=%s",
	    img.fullname,img.nx,img.ny,img.file);
    if (strlen(img.object)>0)
      sprintf(reply,"%s Title=(%s)",reply,img.object);
  }
  else {
    strcpy(reply,"No images loaded into the display");
  }
  return CMD_OK;
}

//---------------------------------------------------------------------------
//
// Post-Processing Commands
//

/*!
  \brief DOPROC command - Enable/Disable image post-processing
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  doproc [proc]
  
  Toggles execution of additional external post-processing scripts
  on/off for the numbered processes [proc=1..#MAX_PROCS].  External
  post-processing scripts are executed in the order that they
  appear in the runtime configuration file.

  If given without arguments, it reports the status of the various
  post-processing commands available.

*/

int
cmd_doproc(char *args, MsgType msgtype, char *reply)
{
  char argbuf[32];
  int iproc;

  if (post.Nproc == 0) {
    strcpy(reply,"No post-processing commands defined");
    return CMD_ERR;
  }

  if (strlen(args)>0) {
    GetArg(args,1,argbuf);
    iproc = atoi(argbuf);
    if (iproc < 0 || iproc > MAX_PROCS) { // a valid process ID?
      sprintf(reply,"Invalid post-processing command number '%s', must be 1..%d",
	      argbuf,MAX_PROCS);
      return CMD_ERR;
    }
    if (post.Cmd[iproc-1] == NULL) { // is a command bound to this ID?
      sprintf(reply,"No post-processing command number %d",iproc);
      return CMD_ERR;
    }
    if (post.doProc[iproc-1]) {
      post.doProc[iproc-1] = 0;
      sprintf(reply,"Proc%d=Disabled",iproc);
    }
    else {
      post.doProc[iproc-1] = 1;
      sprintf(reply,"Proc%d=Enabled",iproc);
    }
  }
  else { // no arguments, report enabled/disabled status
    sprintf(reply,"NProc=%d ",post.Nproc);
    for (iproc=0;iproc<MAX_PROCS;iproc++) {
      if (post.Cmd[iproc] == NULL)
	sprintf(reply,"%s Proc%d=Undefined",reply,iproc+1);
      else
	sprintf(reply,"%s Proc%d=%s",reply,iproc+1,
		((post.doProc[iproc]) ? "Enabled" : "Disabled"));
    }
  }
  return CMD_OK;
}

/*!
  \brief POSTPROC command - Execute external image post-processing scripts
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  postproc [procID fname]
  
  Execute external post-processing script procID on file fname.
  procID runs from 1..#MAX_PROCS.

  If given with no arguments, it reports the enabled post-processing
  steps.

  PostProcImg() does all the dirty work.

*/

int
cmd_postproc(char *args, MsgType msgtype, char *reply)
{
  char arbuf[32];
  int  nargs;
  char fname[64];
  int  iproc;
  char msgstr[128];

  // Make sure we have post-processing commands to execute:

  if (post.Nproc == 0) {
    strcpy(reply,"No post-processing commands defined.");
    return CMD_ERR;
  }

  // Process the arguments

  if (strlen(args)>0) { // we have arguments to process
    nargs = sscanf(args,"%d %s",&iproc,fname);
    if (nargs == 0) {
      sprintf(reply,"Unrecognized POSTPROC command arguments '%s' - Usage: postproc ID fname",args);
      return CMD_ERR;
    }
    if (nargs != 2) {
      strcpy(reply,"Syntax Error - Usage: postproc ID fname");
      return CMD_ERR;
    }
    memset(msgstr,0,sizeof(msgstr));
    if (PostProcImg(&post,iproc,fname,msgstr)<0) {
      sprintf(reply,"PostProcessing Failed - %s",msgstr);
      return CMD_ERR;
    }
    else {
      strcpy(reply,msgstr);
      return CMD_OK;
    }
  }
  
  // No arguments, report processing steps

  strcpy(reply,"External Post-Processing Commands:");
  for (iproc=0;iproc<MAX_PROCS;iproc++) {
    if (post.doProc[iproc] && post.Cmd[iproc] != NULL) 
      sprintf(reply,"%s Cmd%d=(%s)",
	      iproc+1,post.Cmd[iproc]);
  }
  return CMD_OK;

}

/*!  
  \brief POSTINFO command - print the post-processing configuration to stdout
  \param args string with the command-line arguments
  \param msgtype message type if the command was sent as an IMPv2 message
  \param reply string to contain the command return reply
  \return #CMD_OK on success, #CMD_ERR if errors occurred, reply contains
  an error message.

  \par Usage:
  postinfo

  Prints the post-processing command configuration info on stdout.
  This is an engineering command not accessible to remote hosts.

*/

int
cmd_postinfo(char *args, MsgType msgtype, char *reply)
{
  if (msgtype == EXEC) {
    PostProcInfo(&post);
  }
  else {
    strcpy(reply,"Cannot execute POSTINFO command except as EXEC:");
    return CMD_ERR;
  }
  strcpy(reply,"POSTINFO dump complete.");
  return CMD_OK;
}

//***************************************************************************
//
// Command Interpreter I/O Handlers
//

//---------------------------------------------------------------------------
//
// KeyboardCommand() - process a command from the keyboard
//

#include <readline/readline.h>  // Gnu readline utility
#include <readline/history.h>   // Gnu history utility

/*!  
  \brief Process a command from the client's console keyboard
  \param line string with the keyboard command

  This function is setup as a callback for readline(), the GNU
  command-line library that provides Emacs-like key bindings for
  command-line editing, rapid "arrow keys" command history browsing, and
  convenient command history commands (!, !!, etc.).  This gives the
  client application's command-line interface a look-and-feel familiar
  to most users of Unix system command shells (e.g., the tcsh shell).

  This function parses the interactive command line and calls the
  appropriate low-level cmd_xxx() command action functions for excuting
  most commands, as well as servicing ">XX msgtype: command" format raw
  IMPv2 message sending requests.

  Once the parser gets past the main command tree, instead of griping
  about an unknown command, it assumes that it might be a raw host
  command and ships it to the port as-is.  Syntax errors or unknown
  commands will result in gripes from the controller, which is the
  idea at this point.

  All keyboard commands are treated as EXEC: type IMPv2 messages.  This
  makes the downstream cmd_xxx() action functions insensitive to whether
  or not the command came from the keyboard or from a remote ISIS server
  or client application.

  \sa SocketCommand()
*/

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

  // Make sure Ctrl+C is set for motion aborts

  signal(SIGINT,HandleInt);  // reset the SIGINT handler

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
    else
      printf("No ISIS server active, > command unavailable\n");
    
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

    // If unknown command, gripe, otherwise do it

    if (nfound == 0) {
      if (strlen(cmd)>0) 
        printf("ERROR: unknown command - %s\n",cmd);
    }
    else {
	
      // All console keyboard are treated as EXEC: type messages
	
      switch (cmdtab[icmd].action(args,EXEC,reply)) {
	
      case CMD_ERR:
	printf("ERROR: %s\n",reply);
	break;
	
      case CMD_OK:
	printf("DONE: %s\n",reply);
	break;

      case CMD_STATUS:
	printf("STATUS: %s\n",reply);
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
// SocketCommand() - process a message/command from a remote ISIS server/client
//

/*!  
  \brief Process a message/command from a remote ISIS server/client application
  \param buf string with the IMPv2 message received from the remote application

  This function parses a message received from a remote ISIS server or
  client application, and interprets the message.  All EXEC: and
  implicit REQ: type messages are passed to the corresponding cmd_xxx()
  action functions for handling, while the remaining informational
  messages are simply echoed to the console screen.

  More sophisticated handlers might pass such messages on to
  parsers/handlers of their own if the inputs were actually used for
  something other than "visual" information for the user of this
  application.
 
  All messages received from an ISIS node are assumed to be in the
  proper IMPv2 messaging syntax.
 
  Note that EXEC: is new to IMPv2.  It allows remote nodes to transmit
  protected "executive" commands to clients, giving them access to
  commands that would otherwise only be available on the console
  keyboard (e.g., the "quit" command).  Thus a remote EXEC: command
  means "act as if this was typed at the keyboard".  It is the
  responsibility of the remote application to make sure that EXEC: is
  used with care, as you could do something stupid (though your client
  application should not allow actions that would be physically unsafe
  to personnel or equipment).

  \sa KeyboardCommand()
*/

void
SocketCommand(char *buf)
{

  // ISIS message components 

  char msg[ISIS_MSGSIZE];       // Full ISIS message buffer
  char srcID[ISIS_NODESIZE];    // ISIS message sending node ID
  char destID[ISIS_NODESIZE];   // ISIS message destination node ID
  MsgType msgtype = REQ;        // ISIS message type, defined in isisclient.h
  char msgbody[ISIS_MSGSIZE];   // ISIS message/command body

  // Command components (command args)

  char cmd[BIG_STR_SIZE];       // command string (oversized)
  char args[BIG_STR_SIZE];      // command-line argument buffer (oversized)
  char reply[BIG_STR_SIZE];     // command reply string

  // Other working variables

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
  case WARNING:
  case FATAL:
    printf("%s\n",buf);
    break;
	  
  case REQ:    // implicit command requests
  case EXEC:   // and executive override commands

    memset(msg,0,ISIS_MSGSIZE);

    sscanf(msgbody,"%s %[^\n]",cmd,args);  // split into command + args

    // Traverse the command table, exact case-insensitive match required

    nfound = 0;
    for (i=0; i<NumCommands; i++) {
      if (strcasecmp(cmdtab[i].cmd,cmd)==0) { 
	nfound++;
	icmd=i;
	break;
      }
    }

    // Unknown command, gripe back to the sender, otherwise try to do it

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

      case CMD_STATUS:  // command is returning STATUS info
	sprintf(msg,"%s>%s STATUS: %s\n",client.ID,srcID,reply);
	break;
	
      case CMD_OK:  // command executed OK and is DONE, return reply
      default:
	sprintf(msg,"%s>%s DONE: %s\n",client.ID,srcID,reply);
	break;
	
      } // end of switch on cmdtab.action()
    }

    // An incoming PING requires special handling - it is an exception
    // to the usual messaging syntax since PONG is sent in reply 

    if (strcasecmp(cmd,"PING") == 0)
      sprintf(msg,"%s>%s %s\n",client.ID,srcID,reply);
      
    break;

  default:  // we don't know what we got, print for debugging purposes
    printf("Malformed message received on client port: %s\n",buf);
    break;

  } // end of switch(msgtype) -- default falls through with no-op

  // Do we have something to send back? 
  //
  // If we are configured as an ISIS client (client.useISIS=true), send
  // the reply back to the ISIS server for handling with
  // SendToISISServer().
  //
  // If we are configured as standalone (client.useISIS=false), send the
  // reply back to the remote host with SendToHost().

  if (strlen(msg)>0) { // we have something to send
    if (client.useISIS)
      SendToISISServer(&client,msg);
    else 
      ReplyToRemHost(&client,msg);

    if (client.isVerbose) {
      msg[strlen(msg)-1]='\0';
      printf("OUT: %s\n",msg);
    }
  } // end of reply handling

}


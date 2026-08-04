#ifndef COMMANDS_H
#define COMMANDS_H

/*!
  \file commands.h
  \brief Client application command tree header file

  To add a command, you need to 
  <ol>
  <li>Add a command action function prototype to the code below
  <li>Add the command verb and its function call to the #cmdtab struct
  </ol>
 
  See commands.c for the full implementation details.
*/

// Common interactive client commands 

int cmd_quit   (char *, MsgType, char *); // quit the application
int cmd_ping   (char *, MsgType, char *); // ping (comm handshake request)
int cmd_pong   (char *, MsgType, char *); // pong (comm handshake acknowledge)
int cmd_info   (char *, MsgType, char *); // return client application info
int cmd_version(char *, MsgType, char *); // return version info
int cmd_verbose(char *, MsgType, char *); // toggle verbose mode
int cmd_debug  (char *, MsgType, char *); // toggle debug (superverbose) mode
int cmd_help   (char *, MsgType, char *); // show command help
int cmd_history(char *, MsgType, char *); // cli history utility

// High-Level Commands

int cmd_process (char *, MsgType, char *); // Process an image
int cmd_status  (char *, MsgType, char *); // Status command (placeholder)

// Image Transfer Commands

int cmd_dotrans (char *, MsgType, char *); // Enable/Disable image transfer
int cmd_transfer(char *, MsgType, char *); // Transfer an image
int cmd_srcpath (char *, MsgType, char *); // Set/Query the image source path
int cmd_imgpath (char *, MsgType, char *); // Set/Query the image destination path
int cmd_clobber (char *, MsgType, char *); // Enable/Disable file clobber/noclobber
int cmd_marksrc (char *, MsgType, char *); // Enable/Disable source file process marking
int cmd_backimg (char *, MsgType, char *); // Enable/Disable destination file backup once if transfer would clobber
int cmd_xferinfo(char *, MsgType, char *); // Print info about image transfer

// TV Display Commands

int cmd_dodisp  (char *, MsgType, char *); // Enable/Disable image display
int cmd_tv      (char *, MsgType, char *); // load an image from FITS and display
int cmd_display (char *, MsgType, char *); // re-display an image
int cmd_erase   (char *, MsgType, char *); // Erase the display
int cmd_imginfo (char *, MsgType, char *); // Print image info
int cmd_dispinfo(char *, MsgType, char *); // Print TV display info (engineering)

// Post Processing Commands

int cmd_doproc  (char *, MsgType, char *); // Enable/Disable image post-processing
int cmd_postproc(char *, MsgType, char *); // Execute post-processing scripts
int cmd_postinfo(char *, MsgType, char *); // Print info about post-processing scripts

// Application command/action structure

/*!
  \brief Client command action function data structure
*/

struct Commands {
  char *cmd;        //!< command verb (e.g., read, quit, etc.)

  /*!
    \brief Action function for this command
    \param args command-line arguments (less the command verb)
    \param msgtype ISIS message-type code (see isismessage.h)
    \param reply string with the command return reply (info or error message)

    Command action functions take the form

    int cmd_xxx(char *args, MsgType msgtype, char *reply){}

    They return one of three integer return status values (defined in
    commands.h):

    \arg \c #CMD_OK command execution completed OK, \p reply contains the
    command output string to return to the caller.

    \arg \c #CMD_NOOP command execution OK, but nothing to return to the
    caller (\p reply is empty, command requires no reply service).

    \arg \c #CMD_ERR command execution resulted in an error, \p reply contains
    the error message to return to the caller.

    See the individual command action functions implemented in commands.c
    for details.
  */

  int(* action)(char *args, MsgType msgtype, char *reply);  

  char *usage;        //!< command usage syntax, for the help facility and error messages
  char *description;  //!< brief, 1-line command description for the help facility
}
cmdtab[] = {   //!< global scope command table for this application
  {"quit"    ,cmd_quit    ,"quit","Terminate the client session"},
  {"verbose" ,cmd_verbose ,"verbose","Toggle verbose output mode on/off"},
  {"debug"   ,cmd_debug   ,"debug","Toggle super-verbose debugging output mode on/off"},
  {"history" ,cmd_history ,"history","Show the command history (console only)"},
  {"info"    ,cmd_info    ,"info","Report client session runtime info"},
  {"version" ,cmd_version ,"version","Report the client version and compilation time"},
  {"process" ,cmd_process ,"process [file]","Process the named file through the data manager"},
  {"dotrans" ,cmd_dotrans ,"dotrans","Enable/Disable image transfer"},
  {"dodisp"  ,cmd_dodisp  ,"dodisp","Enable/Disable autodisplay"},
  {"doproc"  ,cmd_doproc  ,"doproc","Enable/Disable additional external post-processing"},
  {"transfer",cmd_transfer,"transfer [file]","Transfer file from source to destination paths"},
  {"srcpath" ,cmd_srcpath ,"srcpath [path]","Set/Query the image source path"},
  {"imgpath" ,cmd_imgpath ,"imgpath [path]","Set/Query the image destination path"},
  {"clobber" ,cmd_clobber ,"clobber","Enable/Disable file overwrite on transfers"},
  {"marksrc" ,cmd_marksrc ,"marksrc","Enable/Disable source file process marking (.proc append)"},
  {"backup"  ,cmd_backimg ,"backup","Enable/Disable image file backup (.bak) if transfer would clobber"},
  {"tv"      ,cmd_tv      ,"tv file [z1 z2]","Display file between optional limits z1 z2"},
  {"display" ,cmd_display ,"display [z1 z2]","Redisplay the image between optional limits z1..z2"},
  {"erase"   ,cmd_erase   ,"erase [vec]","Erase the image display. vec = only erase the overlay"},
  {"postproc",cmd_postproc,"postproc [#proc file]","Execute post-processing command #proc on file"},
  {"xferinfo",cmd_xferinfo,"xferinfo","Report the image transfer configuration"},
  {"dispinfo",cmd_dispinfo,"dispinfo","Report the display configuration parameters"},
  {"imginfo" ,cmd_imginfo ,"imginfo","Report the parameters of the current image"},
  {"postinfo",cmd_postinfo,"postinfo","Report the image post-processing configuration"},
  {"status"  ,cmd_status  ,"status","Report the current image display client status"},
  {"help"    ,cmd_help    ,"help <cmd>","Help command (alias: ? <cmd>)"},
  {"?"       ,cmd_help    ,"",""},  // "" excludes from help
  {"displ"   ,cmd_display ,"",""},  // alias for display, old-style syntax
  {"ping"    ,cmd_ping    ,"",""},
  {"pong"    ,cmd_pong    ,"",""}   
};

// Number of commands defined (so we don't have to count correctly)
  
int NumCommands = sizeof(cmdtab)/sizeof(struct Commands);  //!< number of commands defined

// command function return codes

#define CMD_OK   0   //!< Command executed OK, return completion status
#define CMD_ERR -1   //!< Command execution resulted in an error
#define CMD_NOOP 1   //!< Command execution requires no further action (no-op)
#define CMD_STATUS 2 //!< Command execution results in a STATUS: message

#endif // COMMANDS_H

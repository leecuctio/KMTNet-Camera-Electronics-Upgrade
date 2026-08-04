#ifndef COMMANDS_H
#define COMMANDS_H

//
// command tree header for the PCTCS Agent
//
// To add a command, you ned to 
//   a) add a command action function prototype
//   b) add it to the cmdtab struct
// 

// Command action function prototypes, see commands.c for the implementation

// Generic interactive client commands 

int cmd_quit   (char *, MsgType, char *); // quit the application
int cmd_info   (char *, MsgType, char *); // return client application info
int cmd_version(char *, MsgType, char *); // return version info
int cmd_verbose(char *, MsgType, char *); // toggle verbose mode
int cmd_debug  (char *, MsgType, char *); // toggle debug (superverbose) mode
int cmd_help   (char *, MsgType, char *); // show command help
int cmd_ping   (char *, MsgType, char *); // ping (comm handshake request)
int cmd_pong   (char *, MsgType, char *); // pong (comm handshake acknowledge)
int cmd_history(char *, MsgType, char *); // cli history utility

// TCS commands

int cmd_tcinit  (char *, MsgType, char *); // (re)initialize PC-TCS link
int cmd_tcclose (char *, MsgType, char *); // close PC-TCS link
int cmd_tcstatus(char *, MsgType, char *); // query & return TCS status
int cmd_tstat   (char *, MsgType, char *); // lightweight TCSTATUS (no key=value pairs)
int cmd_sip     (char *, MsgType, char *); // sip from the raw TCS telemetry stream
int cmd_setidle (char *, MsgType, char *); // set/query the PC-TCS telemetry idle timeout interval
int cmd_tcscmd  (char *, MsgType, char *); // send a remote command to the PC-TCS
int cmd_tcsynch (char *, MsgType, char *); // synch the PC-TCS to the host system clock
int cmd_ports   (char *, MsgType, char *); // query the PC-TCS serial port assignment

// Application command/action structure

struct Commands {
  char *cmd;        // command name
  int(* action)(char *args, MsgType msgtype, char *reply);  // action taken for this command
}
cmdtab[] = {   // global scope command table for this app
  // generic client commands
  {"quit"    ,cmd_quit    },
  {"info"    ,cmd_info    },
  {"version" ,cmd_version },
  {"verbose" ,cmd_verbose },
  {"debug"   ,cmd_debug   },
  {"help"    ,cmd_help    },
  {"?"       ,cmd_help    },  // ? is an alias for help
  {"ping"    ,cmd_ping    },
  {"pong"    ,cmd_pong    },
  {"history" ,cmd_history },
  // TCS commands
  {"tcinit"  ,cmd_tcinit  },
  {"reset"   ,cmd_tcinit  }, // alias for tcinit
  {"tcclose" ,cmd_tcclose },
  {"tcstatus",cmd_tcstatus},
  {"tcsynch" ,cmd_tcsynch },
  {"idletime",cmd_setidle },
  {"sip"     ,cmd_sip     },
  {"tstat"   ,cmd_tstat   },  // lightweight tcstatus
  {"ports"   ,cmd_ports   },
  {"tcscmd"  ,cmd_tcscmd  }
};

// Number of commands defined (so we don't have to count correctly)
  
int NumCommands = sizeof(cmdtab)/sizeof(struct Commands); 

// command function return codes

#define CMD_OK   0   // command OK, returns normally
#define CMD_ERR -1   // command error
#define CMD_NOOP 1   // no-op (no action required)

#endif // COMMANDS_H

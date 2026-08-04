#ifndef COMMANDS_H
#define COMMANDS_H

//
// command tree header for the KMTNet TCS Agent
//
// To add a command, you need to 
//   a) add a command action function prototype
//   b) add it to the cmdtab struct
// 

// Subroutine & Utility functions
 int  TcsTelemetry(pctcs_t *, char *);
 int  AuxTelemetry(auxctrl_t *, char *);
void  AuxFSUpdate(auxctrl_t *);

// Command action function prototypes, see commands.c for the implementation

// Generic interactive client commands 
int cmd_quit     (char *, MsgType, char *); // quit the application
int cmd_init     (char *, MsgType, char *); // (re)initialize TCS & AUX link
int cmd_close    (char *, MsgType, char *); // close TCS & AUX link and clear all data
int cmd_arc      (char *, MsgType, char *); // toggle auto recovery mode for TCS/AUX link
int cmd_info     (char *, MsgType, char *); // return client application info
int cmd_version  (char *, MsgType, char *); // return version info
int cmd_verbose  (char *, MsgType, char *); // toggle verbose mode
int cmd_debug    (char *, MsgType, char *); // toggle debug (superverbose) mode
int cmd_history  (char *, MsgType, char *); // cli history utility
int cmd_help     (char *, MsgType, char *); // show command help
int cmd_ping     (char *, MsgType, char *); // ping (comm handshake request)
int cmd_pong     (char *, MsgType, char *); // pong (comm handshake acknowledge)
// TCS commands
int cmd_tcsinit  (char *, MsgType, char *); // (re)initialize TCS (PC-TCS & Telcom) link
int cmd_tcsclose (char *, MsgType, char *); // close TCS link & clear TCS data
int cmd_tcsarc   (char *, MsgType, char *); // toggle auto recovery mode for TCS link
int cmd_tcsstatus(char *, MsgType, char *); // query & return TCS status w/ telemetry data
int cmd_tstat    (char *, MsgType, char *); // lightweight TCSSTATUS (no key=value pairs)
int cmd_traw     (char *, MsgType, char *); // return raw telemetry packet string
int cmd_tcmd     (char *, MsgType, char *); // send a remote command to the PC-TCS
int cmd_tsync    (char *, MsgType, char *); // synch the PC-TCS to the host system clock
int cmd_tguide   (char *, MsgType, char *); // guiding offset move RA/Dec in arcsec
int cmd_tgoto    (char *, MsgType, char *); // goto J2000 RA/Dec, arg: hh/+dd:mm:ss.s
int cmd_toffset  (char *, MsgType, char *); // offset move RA/Dec, arg: hh/+dd:mm:ss.s
int cmd_tstop    (char *, MsgType, char *); // cancel command and stop commanded motions
int cmd_tdi      (char *, MsgType, char *); // Synch the cur position to the cmd position
// AUX commands
int cmd_auxinit  (char *, MsgType, char *); // (re)initialize AUX link
int cmd_auxclose (char *, MsgType, char *); // close AUX link & clear AUX data
int cmd_auxarc   (char *, MsgType, char *); // toggle auto recovery mode for AUX link
int cmd_auxstatus(char *, MsgType, char *); // query & return AUX status w/ telemetry data
int cmd_astat    (char *, MsgType, char *); // lightweight AUXSTATUS (no key=value pairs)
int cmd_afsastat (char *, MsgType, char *); // lightweight Filter/Shutter Assembly status
int cmd_afttstat (char *, MsgType, char *); // lightweight Focuse/TipTilt status
int cmd_acmd     (char *, MsgType, char *); // send a remote command to the AUX control
int cmd_afilter  (char *, MsgType, char *); // change filters to filter #
int cmd_adfocus  (char *, MsgType, char *); // adjust focus position of PFI center(on axis)
int cmd_adtilt   (char *, MsgType, char *); // adjust tip-tilt angle of the head ring(PFI)
int cmd_afttgoto (char *, MsgType, char *); // goto the commanded focus & tip-tilt

// Application command/action structure

struct Commands {
  char *cmd;        // command name
  int(* action)(char *args, MsgType msgtype, char *reply); // action taken for this command
}

cmdtab[] = {   // global scope command table for this app
// generic client commands
  {"quit"     ,cmd_quit     },  // (EXEC only)
  {"init"     ,cmd_init     },
  {"reset"    ,cmd_init     },  // alias for init
  {"close"    ,cmd_close    },  // alias for init
  {"arc"      ,cmd_arc      },
  {"info"     ,cmd_info     },
  {"version"  ,cmd_version  },
  {"verbose"  ,cmd_verbose  },
  {"debug"    ,cmd_debug    },
  {"history"  ,cmd_history  },  // (EXEC only)
  {"help"     ,cmd_help     },  // (EXEC only)
  {"?"        ,cmd_help     },  // ? is an alias for help (EXEC only)
  {"ping"     ,cmd_ping     },
  {"pong"     ,cmd_pong     },
  // TCS commands
  {"tcsinit"  ,cmd_tcsinit  },
  {"tcsreset" ,cmd_tcsinit  },  // alias for tcsinit
  {"tcsclose" ,cmd_tcsclose },
  {"tcsarc"   ,cmd_tcsarc   },
  {"tcsstatus",cmd_tcsstatus},
  {"tstat"    ,cmd_tstat    },  // lightweight tcstatus
  {"traw"     ,cmd_traw     },  
  {"tsync"    ,cmd_tsync    },  // (EXEC only)
  {"tcmd"     ,cmd_tcmd     },
  {"tguide"   ,cmd_tguide   },
  {"tgoto"    ,cmd_tgoto    },
  {"toffset"  ,cmd_toffset  },
  {"tstop"    ,cmd_tstop    },
  {"tdi"      ,cmd_tdi      },
  // AUX commands
  {"auxinit"  ,cmd_auxinit  },
  {"auxreset" ,cmd_auxinit  },  // alias for auxinit
  {"auxclose" ,cmd_auxclose },
  {"auxarc"   ,cmd_auxarc   },
  {"auxstatus",cmd_auxstatus},
  {"astat"    ,cmd_astat    },
  {"acmd"     ,cmd_acmd     },
  {"filter"   ,cmd_afilter  },
  {"fsastat"  ,cmd_afsastat },
  {"dfocus"   ,cmd_adfocus  },
  {"dtilt"    ,cmd_adtilt   },  // (EXEC only)
  {"fttgoto"  ,cmd_afttgoto },  // (including tip-tilt args, EXEC only)
  {"fttstat"  ,cmd_afttstat },
};

// Number of commands defined (so we don't have to count correctly)
  
int NumCommands = sizeof(cmdtab)/sizeof(struct Commands); 

// command function return codes

#define CMD_OK   0   // command OK, returns normally
#define CMD_ERR -1   // command error
#define CMD_NOOP 1   // no-op (no action required)

#endif // COMMANDS_H

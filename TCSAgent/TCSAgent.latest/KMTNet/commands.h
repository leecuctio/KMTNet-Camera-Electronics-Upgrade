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
 int offset_blg(double *, double *, double, const char *);

// Command action function prototypes, see commands.c for the implementation

// Generic interactive client commands 
int cmd_quit     (char *, MsgType, char *); // quit the application
int cmd_init     (char *, MsgType, char *); // (re)initialize TCS & AUX link
int cmd_close    (char *, MsgType, char *); // close TCS & AUX link and clear all data
int cmd_arc      (char *, MsgType, char *); // toggle auto recovery mode for TCS/AUX link
int cmd_info     (char *, MsgType, char *); // return client application info
int cmd_version  (char *, MsgType, char *); // return version info
int cmd_catalog  (char *, MsgType, char *); // quiry & import RA/Dec object of catalog
int cmd_verbose  (char *, MsgType, char *); // toggle verbose mode
int cmd_concise  (char *, MsgType, char *); // disable verbose mode
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
int cmd_treq     (char *, MsgType, char *); // send a remote request to the PC-TCS
int cmd_tsync    (char *, MsgType, char *); // synch the PC-TCS to the host system clock
int cmd_tmradec  (char *, MsgType, char *); // goto J2000 RA/Dec, arg: hh/+dd:mm:ss.s     //v1.5.0
int cmd_tmobject (char *, MsgType, char *); // goto object on catalog file, arg: ObjName  //v1.5.1
int cmd_tmelaz   (char *, MsgType, char *); // goto elevation/azimuth, arg: ee.ee +aaa.aa //v1.5.1
int cmd_tmoffset (char *, MsgType, char *); // offset move RA/Dec, arg: +hh/+dd:mm:ss.s
int cmd_tguide   (char *, MsgType, char *); // guiding offset move RA/Dec in arcsec
int cmd_tstop    (char *, MsgType, char *); // cancel command and stop commanded motions
int cmd_tstow    (char *, MsgType, char *); // stow command
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
int cmd_afilname (char *, MsgType, char *); // query & return filter names for labeling
int cmd_adfocus  (char *, MsgType, char *); // adjust focus position of PFI center(on axis)
int cmd_adtilt   (char *, MsgType, char *); // adjust tip-tilt angle of PFI (cartesian coord)
int cmd_afttgoto (char *, MsgType, char *); // goto the commanded focus & tip-tilt (cartesian)
//int cmd_adtiltp  (char *, MsgType, char *); // adjust tip-tilt angle of PFI (polar coord)
//int cmd_afttgotop(char *, MsgType, char *); // goto the commanded focus & tip-tilt (polar)

int cmd_tick     (char *, MsgType, char *);
int cmd_pmo      (char *, MsgType, char *);
int cmd_pmc      (char *, MsgType, char *);

// Application command/action structure

struct Commands {
  char *cmd;        // command name
  int(* action)(char *args, MsgType msgtype, char *reply); // action taken for this command
}

cmdtab[] = {   // global scope command table for this app
// generic client commands
  {"quit"     ,cmd_quit     },  // (EXEC only)
  {"init"     ,cmd_init     },
  {"reset"    ,cmd_init     },  // alias for 'init'
  {"close"    ,cmd_close    },
  {"arc"      ,cmd_arc      },
  {"info"     ,cmd_info     },
  {"version"  ,cmd_version  },
  {"catalog"  ,cmd_catalog  },  // (EXEC only) (v1.5.1)
  {"cat"      ,cmd_catalog  },  // alias for 'catalog'
  {"verbose"  ,cmd_verbose  },
  {"ver"      ,cmd_verbose  },  // alias for 'verbose'
  {"concise"  ,cmd_concise  },
  {"con"      ,cmd_concise  },  // alias for 'concise'
  {"debug"    ,cmd_debug    },
  {"history"  ,cmd_history  },  // (EXEC only)
  {"help"     ,cmd_help     },  // (EXEC only)
  {"?"        ,cmd_help     },  // ? is an alias for 'help' (EXEC only)
  {"ping"     ,cmd_ping     },
  {"pong"     ,cmd_pong     },
  // TCS commands
  {"tcsinit"  ,cmd_tcsinit  },
  {"tcsreset" ,cmd_tcsinit  },  // alias for 'tcsinit'
  {"tcsclose" ,cmd_tcsclose },
  {"tcsarc"   ,cmd_tcsarc   },
  {"tcsstatus",cmd_tcsstatus},
  {"tcsstat"  ,cmd_tcsstatus},  // alias for 'tcsstatus'
  {"tstatus"  ,cmd_tcsstatus},  // alias for 'tcsstatus'
  {"tstat"    ,cmd_tstat    },  // lightweight 'tcstatus'
  {"traw"     ,cmd_traw     },  
  {"tsync"    ,cmd_tsync    },  // (EXEC only)
  {"tcmd"     ,cmd_tcmd     },
  {"treq"     ,cmd_treq     },  // for Skip's UI (v1.2.6)
  {"tmradec"  ,cmd_tmradec  },  // (v1.5.0)
  {"tmr"      ,cmd_tmradec  },  // alias for 'tmradec'
  {"tmobject" ,cmd_tmobject },  // (v1.5.1)
  {"tmobj"    ,cmd_tmobject },  // alias for 'tmobject'
  {"tmo"      ,cmd_tmobject },  // alias for 'tmobject'
  {"tmelaz"   ,cmd_tmelaz   },  // (v1.5.1)
  {"tme"      ,cmd_tmelaz   },  // alias for 'tmelaz'
  {"tgoto"    ,cmd_tmradec  },  // alias for 'tmradec' (v1.5.0)
  {"toffset"  ,cmd_tmoffset },
  {"toff"     ,cmd_tmoffset },  // alias for 'tmoffset'
  {"tguide"   ,cmd_tguide   },
  {"tgui"     ,cmd_tguide   },  // alias for 'tguide'
  {"tstop"    ,cmd_tstop    },
  {"tstow"    ,cmd_tstow    },
  {"stow"     ,cmd_tstow    },
  {"tdi"      ,cmd_tdi      },
  // AUX commands
  {"auxinit"  ,cmd_auxinit  },
  {"auxreset" ,cmd_auxinit  },  // alias for auxinit
  {"auxclose" ,cmd_auxclose },
  {"auxarc"   ,cmd_auxarc   },
  {"auxstatus",cmd_auxstatus},
  {"auxstat"  ,cmd_auxstatus},  // alias for 'auxstatus'
  {"astatus"  ,cmd_auxstatus},  // alias for 'auxstatus'
  {"astat"    ,cmd_astat    },
  {"acmd"     ,cmd_acmd     },
  {"filter"   ,cmd_afilter  },
  {"filnum"   ,cmd_afilname },  // alias for filname
  {"filname"  ,cmd_afilname },
  {"fsastat"  ,cmd_afsastat },
  {"fs"       ,cmd_afsastat },
  {"dfocus"   ,cmd_adfocus  },
  {"dtilt"    ,cmd_adtilt   },
  {"fttgoto"  ,cmd_afttgoto },
//{"dtiltp"   ,cmd_adtiltp  },
//{"fttgotop" ,cmd_afttgotop},
  {"fttstat"  ,cmd_afttstat },
  {"ft"       ,cmd_afttstat },
  // Utilities
  {"tick"     ,cmd_tick     },
  {"oo"       ,cmd_pmo      },  // for pointing model measurement (v1.5.5)
  {"cc"       ,cmd_pmc      },  // for pointing model measurement (v1.5.5)
};

// Number of commands defined (so we don't have to count correctly)
  
int NumCommands = sizeof(cmdtab)/sizeof(struct Commands); 

// command function return codes

#define CMD_OK   0   // command OK, returns normally
#define CMD_ERR -1   // command error
#define CMD_NOOP 1   // no-op (no action required)

#endif // COMMANDS_H

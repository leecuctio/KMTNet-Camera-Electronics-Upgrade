#ifndef COMMANDS_H
#define COMMANDS_H

//------------------------------------------------------------------------------
//
// command tree header for the KMTNet OBS Agent
//
// To add a command, you need to 
//   a) add a command action function prototype
//   b) add it to the cmdtab struct
// 
//------------------------------------------------------------------------------

// Subroutine & Utility functions

// ..

// Command action function prototypes, see commands.c for the implementation

// ..

// Generic interactive client commands 

int cmd_quit         (char *, MsgType, char *); // quit the application
int cmd_init         (char *, MsgType, char *); // (re)initialize --> quit
int cmd_info         (char *, MsgType, char *); // return client application info
int cmd_version      (char *, MsgType, char *); // return version info
int cmd_timetag      (char *, MsgType, char *); // toggle time tag display option
int cmd_verbose      (char *, MsgType, char *); // toggle verbose mode
int cmd_concise      (char *, MsgType, char *); // disable verbose mode
int cmd_debug        (char *, MsgType, char *); // toggle debug (superverbose) mode
int cmd_history      (char *, MsgType, char *); // cli history utility
int cmd_help         (char *, MsgType, char *); // show command help
int cmd_ping         (char *, MsgType, char *); // ping (comm handshake request)
int cmd_pong         (char *, MsgType, char *); // pong (comm handshake acknowledge)
int cmd_tc           (char *, MsgType, char *); // send a command to TC
int cmd_nstset       (char *, MsgType, char *); // setup non-sidereal tracking RA/Dec velocity
int cmd_nston        (char *, MsgType, char *); // enable non-sidereal tracking
int cmd_nstoff       (char *, MsgType, char *); // disable non-sidereal tracking
int cmd_ics          (char *, MsgType, char *); // send a command to ICS
int cmd_ics_go       (char *, MsgType, char *); // send the 'go' command to ICS
int cmd_ics_exp      (char *, MsgType, char *); // send the 'exp' command to ICS
int cmd_dmawait      (char *, MsgType, char *); // send dmawait commands to K.IC
int cmd_datasource   (char *, MsgType, char *); // send datasource commands to K.IC/M.IC/T.IC/N.IC
int cmd_kstatus      (char *, MsgType, char *); // send status commands to K.IC
int cmd_mstatus      (char *, MsgType, char *); // send status commands to M.IC
int cmd_tstatus      (char *, MsgType, char *); // send status commands to T.IC
int cmd_nstatus      (char *, MsgType, char *); // send status commands to N.IC
int cmd_gstatus      (char *, MsgType, char *); // send status commands to G.IC
int cmd_expinfo      (char *, MsgType, char *); // query information for current exposure
int cmd_sysstatus    (char *, MsgType, char *); // return observation system status
int cmd_domestatus   (char *, MsgType, char *); // return dome status on Redis/Relay/AuxStatus
int cmd_override     (char *, MsgType, char *); // toggle to enable/disable override some system disconnection/error to keep going to observation
int cmd_dlamp        (char *, MsgType, char *); // domeflat lamp relay control with system()
int cmd_dlight       (char *, MsgType, char *); // dome LED light relay control with system()
int cmd_mcfan        (char *, MsgType, char *); // mirror cell fan relay control with system()
int cmd_tpad         (char *, MsgType, char *); // PC-TCS paddle N/S/E/W button control
int cmd_drot         (char *, MsgType, char *); // getting and update dome rotation status
int cmd_warning      (char *, MsgType, char *); // activate the warning blinking
int cmd_msgout       (char *, MsgType, char *); // input message string output for operational availability or some logs required
int cmd_sleep        (char *, MsgType, char *); // sleep all the process as specified seconds
int cmd_dtchk        (char *, MsgType, char *); // move FITS data from /data to /data/YYYYDDMM and check for data transfer from ICS to DTS
int cmd_ecmd         (char *, MsgType, char *); // external command execution on the shell with system()
int cmd_redisget     (char *, MsgType, char *); // get a value from redis server on newTCS
int cmd_redisset     (char *, MsgType, char *); // set key=value pair to redis server on newTCS
int cmd_redislocal   (char *, MsgType, char *); // set redis host name to loopback ip addr "127.0.0.1"
int cmd_test         (char *, MsgType, char *); // test function, call by command
int cmd_noop         (char *, MsgType, char *); // no operation and response, for dummy command line in osc
int cmd_tick         (char *, MsgType, char *); // tick utility configuration and output
int cmd_getut        (char *, MsgType, char *); // get UT date & time
int cmd_getjd        (char *, MsgType, char *); // get Julian date from UT string
int cmd_getlst       (char *, MsgType, char *); // get local sidereal time
int cmd_getalt       (char *, MsgType, char *); // get alt/az/ha/airmass from ra, dec, and (ut)
int cmd_oscscript    (char *, MsgType, char *); // query or load an observation script
int cmd_oscline      (char *, MsgType, char *); // query a line of the osc data imported
int cmd_osclabel     (char *, MsgType, char *); // query the line that has input lable string
int cmd_oscobject    (char *, MsgType, char *); // query the line that has input object name
int cmd_oscstatus    (char *, MsgType, char *); // query script observation status
int cmd_osclast      (char *, MsgType, char *); // query ast completed script line number
int cmd_oscstart     (char *, MsgType, char *); // start script observation
int cmd_oscstop      (char *, MsgType, char *); // stop script observation after finishing current line
int cmd_oscabort     (char *, MsgType, char *); // abort script observation, immediately stop all the process
int cmd_oscpause     (char *, MsgType, char *); // pause script observation
int cmd_oscresume    (char *, MsgType, char *); // resume script observation
int cmd_oscprepare   (char *, MsgType, char *); // toggle next exposure preparation mode
int cmd_oscdelay     (char *, MsgType, char *); // delay osc process, but the other process is not blocked

// Application command/action structure

struct Commands {
  char *cmd;        // command name
  int(* action)(char *args, MsgType msgtype, char *reply); // action taken for this command
}

cmdtab[] = {   // global scope command table for this app

  // Generic agent/client commands
  {"quit"        ,cmd_quit     },  // (EXEC only)
  {"init"        ,cmd_init     },
  {"reset"       ,cmd_init     },  // alias for 'init'
  {"info"        ,cmd_info     },
  {"version"     ,cmd_version  },
  {"ver"         ,cmd_version  },  // alias for 'version'
  {"timetag"     ,cmd_timetag  },
  {"verbose"     ,cmd_verbose  },
  {"concise"     ,cmd_concise  },
  {"debug"       ,cmd_debug    },
  {"history"     ,cmd_history  },  // (EXEC only)
  {"help"        ,cmd_help     },  // (EXEC only)
  {"?"           ,cmd_help     },  // ? is an alias for 'help' (EXEC only)
  {"ping"        ,cmd_ping     },
  {"pong"        ,cmd_pong     },

  // TC.TCS commands
  {"tcsinit"   ,cmd_tc       },
  {"tcsreset"  ,cmd_tc       },  // alias for 'tcsinit'
  {"tcsclose"  ,cmd_tc       },
  {"tcsarc"    ,cmd_tc       },
  {"tcsstatus" ,cmd_tc       },
  {"tcsstat"   ,cmd_tc       },  // alias for 'tcsstatus'
  {"tstat"     ,cmd_tc       },  // lightweight 'tcstatus'
  {"traw"      ,cmd_tc       },  
  {"tsync"     ,cmd_tc       },  // (EXEC only)
  {"tcmd"      ,cmd_tc       },
  {"treq"      ,cmd_tc       },  // for Skip's UI
  {"tmradec"   ,cmd_tc       },
  {"tmr"       ,cmd_tc       },  // alias for 'tmradec'
  {"tmobject"  ,cmd_tc       },
  {"tmobj"     ,cmd_tc       },  // alias for 'tmobject'
  {"tmo"       ,cmd_tc       },  // alias for 'tmobject'
  {"tmelaz"    ,cmd_tc       },
  {"tme"       ,cmd_tc       },  // alias for 'tmelaz'
//{"tgoto"     ,cmd_tc       },  // alias for 'tmradec'
  {"toffset"   ,cmd_tc       },
  {"toff"      ,cmd_tc       },  // alias for 'tmoffset'
  {"tguide"    ,cmd_tc       },
  {"tgui"      ,cmd_tc       },  // alias for 'tguide'
  {"tstop"     ,cmd_tc       },
  {"tstow"     ,cmd_tc       },
  {"stow"      ,cmd_tc       },
  {"tdi"       ,cmd_tc       },
  {"oo"        ,cmd_tc       },  // for pointing model measurement
  {"cc"        ,cmd_tc       },  // for pointing model measurement
  {"nstset"    ,cmd_nstset   },  
  {"nston"     ,cmd_nston    },  
  {"nstoff"    ,cmd_nstoff   },  

  // TC.AUX commands
  {"auxinit"   ,cmd_tc       },
  {"auxreset"  ,cmd_tc       },  // alias for auxinit
  {"auxclose"  ,cmd_tc       },
  {"auxarc"    ,cmd_tc       },
  {"auxstatus" ,cmd_tc       },
  {"auxstat"   ,cmd_tc       },  // alias for 'auxstatus'
  {"astat"     ,cmd_tc       },  // lightweight 'auxstatus'
  {"acmd"      ,cmd_tc       },
  {"fsastat"   ,cmd_tc       },
  {"fs"        ,cmd_tc       },
  {"filter"    ,cmd_tc       },
  {"filname"   ,cmd_tc       },
  {"filnum"    ,cmd_tc       },  // alias for 'filname'
  {"fttstat"   ,cmd_tc       },
  {"ft"        ,cmd_tc       },
  {"dfocus"    ,cmd_tc       },
  {"dtilt"     ,cmd_tc       },
  {"fttgoto"   ,cmd_tc       },

  // ISIS/ICS commands
  {"status"    ,cmd_ics      },
  {"acqstatus" ,cmd_ics      },
  {"filename"  ,cmd_ics      },
  {"expnum"    ,cmd_ics      },
  {"bin"       ,cmd_ics      },
//{"roi"       ,cmd_ics      },  // reserved
//{"displ"     ,cmd_ics      },  // reserved
  {"ledflash"  ,cmd_ics      },
  {"observer"  ,cmd_ics      },
  {"projid"    ,cmd_ics      },
  {"exp"       ,cmd_ics_exp  },
  {"bias"      ,cmd_ics      },
  {"dark"      ,cmd_ics      },
  {"object"    ,cmd_ics      },
  {"flat"      ,cmd_ics      },
  {"sky"       ,cmd_ics      },
  {"domeflat"  ,cmd_ics      },
  {"standard"  ,cmd_ics      },
  {"go"        ,cmd_ics_go   },
//{"stop"      ,cmd_ics      },  // error, need debugging --> proc in script func
//{"abort"     ,cmd_ics      },  // error, need debugging
//{"movie"     ,cmd_ics      },  // reserved

  // ISIS/ICs(K/M/T/N/G) commands
  {"dmawait"   ,cmd_dmawait   },
  {"datasource",cmd_datasource},
  {"kstatus"   ,cmd_kstatus   },
  {"mstatus"   ,cmd_mstatus   },
  {"tstatus"   ,cmd_tstatus   },
  {"nstatus"   ,cmd_nstatus   },
  {"gstatus"   ,cmd_gstatus   },

  // Status and sub-system commands
  {"expinfo"   ,cmd_expinfo   },
  {"ee"        ,cmd_expinfo   },  // alias for 'expinfo'
  {"sysstatus" ,cmd_sysstatus },  // alias for 'sysstat'
  {"sysstat"   ,cmd_sysstatus },  
  {"sstat"     ,cmd_sysstatus },  // alias for 'sysstat'
  {"ss"        ,cmd_sysstatus },  // alias for 'sysstat'
  {"domestatus",cmd_domestatus},  // alias for 'domestat'
  {"domestat"  ,cmd_domestatus},
  {"dstat"     ,cmd_domestatus},  // alias for 'domestat'
  {"override"  ,cmd_override  },
  {"ovr"       ,cmd_override  },  // alias for 'override'
//{"ovron"     ,cmd_ovron     },  // replace with 'override'
//{"ovroff"    ,cmd_ovroff    },  // replace with 'override'
  {"dlamp"     ,cmd_dlamp     },
  {"dlight"    ,cmd_dlight    },
  {"mcfan"     ,cmd_mcfan     },
  {"tpad"      ,cmd_tpad      }, 
  {"drot"      ,cmd_drot      },
  {"dr"        ,cmd_drot      },  // alias for 'drot'

  // Utility commands
  {"warning"   ,cmd_warning   },
  {"msgout"    ,cmd_msgout    },
  {"sleep"     ,cmd_sleep     },
  {"dtchk"     ,cmd_dtchk     },
  {"ecmd"      ,cmd_ecmd      },
  {"ec"        ,cmd_ecmd      },  // alias for 'ecmd'
  {"redisget"  ,cmd_redisget  },
  {"rget"      ,cmd_redisget  },  // alias for 'redisget'
  {"redisset"  ,cmd_redisset  },
  {"redislocal",cmd_redislocal},
  {"test"      ,cmd_test      },
  {"tt"        ,cmd_test      },  // alias for 'test'
  {"noop"      ,cmd_noop      },
  {"tick"      ,cmd_tick      },
  {"getut"     ,cmd_getut     },
  {"ut"        ,cmd_getut     },  // alias for 'getut'
  {"getjd"     ,cmd_getjd     },
  {"jd"        ,cmd_getjd     },  // alias for 'getjd'
  {"getlst"    ,cmd_getlst    },
  {"lst"       ,cmd_getlst    },  // alias for 'getlst'
  {"getalt"    ,cmd_getalt    },
  {"alt"       ,cmd_getalt    },  // alias for 'getalt'

  // Script observation commands
  {"oscript"   ,cmd_oscscript   },
  {"oscr"      ,cmd_oscscript   },  // alias for 'oscript'
  {"osc"       ,cmd_oscscript   },  // alias for 'oscript'
  {"oline"     ,cmd_oscline     },
  {"olabel"    ,cmd_osclabel    },
  {"oobject"   ,cmd_oscobject   },
  {"oobj"      ,cmd_oscobject   },  // alias for 'oobject'
  {"ostatus"   ,cmd_oscstatus   },
  {"ostat"     ,cmd_oscstatus   },  // alias for 'ostatus'
  {"os"        ,cmd_oscstatus   },  // alias for 'ostatus'
  {"olast"     ,cmd_osclast     },
  {"ostart"    ,cmd_oscstart    },
  {"ostop"     ,cmd_oscstop     },
  {"oabort"    ,cmd_oscabort    },
  {"opause"    ,cmd_oscpause    },
  {"op"        ,cmd_oscpause    },  // alias for 'opause'
  {"pause"     ,cmd_oscpause    },  // alias for 'opause'
  {"oresume"   ,cmd_oscresume   },
  {"or"        ,cmd_oscresume   },  // alias for 'oresume'
  {"resume"    ,cmd_oscresume   },  // alias for 'oresume'
  {"oprepare"  ,cmd_oscprepare  },
  {"odelay"    ,cmd_oscdelay    },
  {"delay"     ,cmd_oscdelay    },  // alias for 'odelay'

//  {"loopnum"   ,cmd_oscloopnum  },  // set loop repeat number
//  {"loopstart" ,cmd_oscloopstart},  // set loop start point(ID)
//  {"loopend"   ,cmd_oscloopend  },  // set loop end point(ID)
//  {"exitloop"  ,cmd_oscexitloop },  // exit loop immediately
//  {"fitsview"  ,cmd_oscfitsview },  // enable/disable fits viewer launching option
//  {"movetodfp" ,cmd_movetodfp   },  // one of frequent command line set

};

// Number of commands defined (so we don't have to count correctly)

int NumCommands = sizeof(cmdtab)/sizeof(struct Commands); 

// return code for command functions

#define CMD_OK   0   // command OK, returns normally
#define CMD_ERR -1   // command error
#define CMD_NOOP 1   // no-op (no action required)

#define NOOP  (MsgType)90   // no-op for socket commands
#define OSC   (MsgType)91   // Obs script commands, added at v0.6.0

// Utilites functions only used in commands.c
int SendISISMsg(const char *, MsgType, const char *, char *);  // send a ISIS message to ICIMACS node
int GetOscLine(int, int, char*, char*);
int OscSetDatasource(const int nDatasource);
int UpdateTcsData(obssystem_t*, char*, char*);
int UpdateAuxData(obssystem_t*, char*, char*);
int UpdateFilterLabels(obssystem_t*, char*, char*);
int UpdateDomeStatus(obssystem_t*, char*);
int offset_blg(double*, double*, double, const char*);

// Define and Declare for Curl Lib. using XML in/out (v0.9.6)
#include <curl/curl.h>
#define XML_BUFFER_SIZE 1024
size_t curl_write_data(void *ptr, size_t size, size_t nmemb, void *userdata);

#endif // COMMANDS_H

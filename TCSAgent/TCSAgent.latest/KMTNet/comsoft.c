//
// comsoft - ComSoft PCTCS and AUX control utility routines
//
// Routines:
//   void parse_comsoft(char *cmd) - parse a comsoft telemetry string 
//                                   and load into the tcs struct
//   void  UpdateTcsMoving() - monitor and display the telescope moving status
//    int  InitPCTCS(pctcs_t *tcs, char *reply) - initialize the TCS link 
//   void  ClearPCTCS(pctcs_t *tcs) - clear the TCS link and telemetry data
//    int  InitAUX(auxctrl_t *aux, char *reply) - initialize the AUX link
//   void  ClearAUX(auxctrl_t *aux) - clear the AUX control data
//   void  ClearAuxData(auxctrl_t *aux, int subsys) - clear the AUX data
//   char *GetAuxSubsysName(int SubsysIndex) - ceturn the AUX subsystem's name
//
// Description:
//   (the original version interacting directly with PC-TCS)
//   A set of utility routines for communicating with the ComSoft PC-TCS
//   via a serial port.  Used by the TCSAgent client program to
//   interface between an OSU IMPv2-compliant system and a ComSoft
//   PC-TCS.
//
//   We have used some documentation from Dave Harvey (creator of
//   PC-TCS), but generally there is a fair amount of customization
//   among various PC-TCS implementations, so we have to use a lot of
//   #defs to get the details correct.  The flags that set which
//   implementation we are using need to be set in the pctcs.h header
//   file *before* compilation - at present there is no simple way to
//   tell dynamically which particular PC-TCS system we are connected
//   to.  Also, in each implementation the exact format of the telemetry
//   stream can vary greatly, so the mappings must be determined
//   empirically.
//
//   (the KMTNet version interacting with PC-TCS Telcom and AUX ctrl sever)
//   A set of utility routines for communicating with the ComSoft PC-TCS
//   Telcom server and AUX control remote server via TCP/IP socket.
//   Modified for KMTNet TCS that consist of a ComSoft PC-TCS including 
//   Telcom interface and AUX control software including the AUX remote 
//   commands interface. Used by the TCSAgent client program to interface 
//   between an OSU IMPv2-compliant system and KMTNet TCS. 
//
// Author: 
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2003 February 1 (original version - Yale1m v3.3.1)
//
//   S. Cha, KASI KMTNet team
//   chasm@kasi.re.kr
//   2014 April 1 (KMTNet version)
//
// Modification History:
//   2004 Feb 29 - new-style routines for parsing that know which particular
//                 PC-TCS implementation we're using (see pctcs.h) [rwp/osu]
//   2014 Apr 30 - modified for KMTNet TCS [sc/kasi]
//   2014 Aug 04 - update according to the commands definition revision to 
//                 KMTNet TCS Agent Rev.2/AUX remote commands definition v20140802,
//                 and TCSAgent version update from v1.1 to v1.2
//   2014 Aug 24 - TCP recv() timeout setting (v1.2.2)
//                 tcs.dDec added to apply cos(Dec) to RA guide in cmd_tguide()
//   2014 Sep 02 - Filter names update added in InitAUX() (v1.3.0)
//   2015 Jan 12 - TCS LimitStatus update, AUX Filter name update (v1.4.1)
//   2015 Jul 08 - dHA, dRA update for BLG offset correction (v1.5.0)
//   2015 Oct 15 - _(v)msgout() applied for tel-moving msg output on logfile (v1.6.0)
//   2015 Oct 17 - aux->FS_CmdFilNum = AUX_UNKNOWN; in AuxInit() for init update (v1.6.1)
//   2017 Jun 07 - inspection of RA/DEC values & string length and Alt/Az data, 
//                 addition of return value and DataChkMsg in parse_comsoft() (v1.6.3)
//   2017 Jun 20 - modified/added for inspection/correction of string/data/value 
//                 of RA/DEC/HA/Alt/Az pctcs telemetry data in parse_comsoft() (v1.6.5)
//   2017 Jul 26 - LimitStatus modified with bit masking for simultaneous events (v1.6.6)
//
//
//------------------------------------------------------------------------------
// Updating plans
//
//   2015 Jan xx - FitsTelID update added in InitAUX (reserved)
//
//------------------------------------------------------------------------------

#include "pctcs.h"    // PC-TCS interface agent header

   int  parse_comsoft(pctcs_t *tcs, char *tcsstr);
  void  UpdateTcsMoving(pctcs_t *tcs);
double  HACoordConv(const char *strCoord);
double  RACoordConv(const char *strCoord);
double  DecCoordConv(const char *strCoord);
   int  InitPCTCS(pctcs_t *tcs, char *reply);
  void  ClearPCTCS(pctcs_t *tcs);
   int  InitAUX(auxctrl_t *aux, char *reply);
  void  ClearAUX(auxctrl_t *aux);
  void  ClearAuxData(auxctrl_t *aux, int subsys);
  char *GetAuxSubsysName(int SubsysIndex);

//------------------------------------------------------------------------------
// Mecro definition for flagging rtn, only used in comsoft.c (v1.6.3)

#define  COMSOFT_MASK_ERR_NOALT     0x00000001
#define  COMSOFT_MASK_ERR_NOAZ      0x00000002
#define  COMSOFT_MASK_ERR_NOSECZ    0x00000004
#define  COMSOFT_MASK_ERR_RAHOUR    0x00000008
#define  COMSOFT_MASK_ERR_RAMIN     0x00000010
#define  COMSOFT_MASK_ERR_RASEC     0x00000020
#define  COMSOFT_MASK_ERR_RALEN     0x00000040
#define  COMSOFT_MASK_ERR_DECSGN    0x00000080
#define  COMSOFT_MASK_ERR_DECDEG    0x00000100
#define  COMSOFT_MASK_ERR_DECMIN    0x00000200
#define  COMSOFT_MASK_ERR_DECSEC    0x00000400
#define  COMSOFT_MASK_ERR_DECLEN    0x00000800
#define  COMSOFT_MASK_COR_RAH_AC    0x00001000
#define  COMSOFT_MASK_COR_RAM_AC    0x00002000
#define  COMSOFT_MASK_COR_RAS_AC    0x00004000
#define  COMSOFT_MASK_COR_RAS_RO    0x00008000
#define  COMSOFT_MASK_COR_DSGN_AC   0x00100000
#define  COMSOFT_MASK_COR_DECD_AC   0x00200000
#define  COMSOFT_MASK_COR_DECM_AC   0x00400000
#define  COMSOFT_MASK_COR_DECS_AC   0x00800000
#define  COMSOFT_MASK_COR_DECS_RO   0x01000000
#define  COMSOFT_MASK_COR_HASTR     0x10000000
#define  COMSOFT_MASK_ERR_HAVAL     0x20000000
#define  COMSOFT_MASK_NOTUSED       0x80000000  // don't use for negative return value

#define  COMSOFT_RTN_ERR_NODATA   -1
#define  COMSOFT_RTN_NOERROR       0

#define  COMSOFT_SPEC_HA_NEG  -5.0
#define  COMSOFT_SPEC_HA_POS  +5.0


//------------------------------------------------------------------------------
//
// parse_comsoft() - parse the ComSoft TCS telemetry string into components
//
// Arguments:
//   tcs: pointer to a pctcs_config data structure
//   tcsstr (char *): TCS telemetry string
//
// Description:
//   Parses the telemetry string returned by the ComSoft port, and
//   loads the relevant variables into the members of the pctcs_config
//   data structure.
//   
//   Any eventual processing (e.g., computing HJD and such like) will
//   be done here.  Not yet...
//
//   What this does is very implementation-dependent, see the notes and
//   #defs below for the gory details.
//
// Author:
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2003 February 1
//
// Modification History:
//   2004 Feb 29: updated for the new-style substring parsing [rwp/osu]
//   2004 Jun 30: added status and limit flag checking [rwp/osu]
//   2005 May 27: overhauled for the new system [rwp/osu]
//   2014 Apr 16: modified for KMTNet PC-TCS & Telcom [sc/kasi]
//   2017 Jun 01: Checking for RA/DEC values & string length [sc/kasi]
//
//------------------------------------------------------------------------------

int
parse_comsoft(pctcs_t *tcs, char *tcsstr)
{
  char ra[16];     // RA in hhmmss.ss format
  char dec[16];    // Dec in +ddmmss.s format
  char temp[16];
 
  int   rah;
  int   ram;
  float ras;
  char  dsgn[2];
  int   decd;
  int   decm;
  float decs;

  systime_t systime;

  int rtn;  // using to flag with comsoft masks, v1.6.3
  rtn = COMSOFT_RTN_NOERROR;

  //static int aftermove=0;

  // Check telemetry data
  //if( tcsstr[0]==' ' ) return -5;  // no data
  //if( tcsstr[53]!='.' || tcsstr[58]!='.' ) return -1; // no Alt Az data

  // Check telemetry data from v1.6.3
  if( tcsstr[0]==' ' ) { strcpy(tcs->DataChkMsg, "ERR_NODATA"); return -1; }

  // Trim dummy string

  tcsstr[MIN_TCSBUF] = NULL;

  // Get the UTC time from the local clock now - Telemetry data update time

  GetUTCDateTime(&systime);
  sprintf(tcs->Date,"%04d-%02d-%02d",systime.year,systime.month,systime.day);
  sprintf(tcs->UTC,"%02d:%02d:%06.3f",systime.hour,systime.min,systime.sec);

  // Pick apart the telemetry packet data based on the telemetry tables
  // provided either by Dave Harvey or (more useful) empirically
  // determined for a particular PC-TCS emulation by looking at the
  // actual telemetry data in the packet from Telcom of KMTNet PC-TCS.

  SubStr(ra,tcsstr,3,11);
  SubStr(dec,tcsstr,13,21);
  SubStr(tcs->HA,tcsstr,24,32);
  SubStr(tcs->LST,tcsstr,34,41);
  SubStr(tcs->Alt,tcsstr,43,46);
  SubStr(tcs->Az,tcsstr,49,54);
  SubStr(tcs->SecZ,tcsstr,56,60);
  SubStr(tcs->Equinox,tcsstr,75,82);

  // now derive or convert bits that need converting, as required by the implementation

  // Conversions required of all PC-TCS implementations

  // scan ra into parts, convert to hh:mm:ss.ss string 

  ////  //// oldver
  ////  //sscanf(ra,"%02d%02d%f",&rah,&ram,&ras);
  ////  //sprintf(tcs->RA,"%.2i:%.2i:%05.2f",rah,ram,ras);

  ////  //// v1.6.3
  ////  sscanf(ra,"%02d%02d%f",&rah,&ram,&ras);
  ////  if( rah>=24   || rah<0   ) { rah = 0  ; rtn |= COMSOFT_MASK_ERR_RAHOUR; }
  ////  if( ram>=60   || ram<0   ) { ram = 0  ; rtn |= COMSOFT_MASK_ERR_RAMIN ; }
  ////  if( ras>=60.0 || ras<0.0 ) { ras = 0.0; rtn |= COMSOFT_MASK_ERR_RASEC ; }
  ////  sprintf(tcs->RA,"%02d:%02d:%05.2f",rah,ram,ras);
  ////  if( strlen(tcs->RA)>11 ) { strcpy(tcs->RA, "00:00:00.00"); rtn |= COMSOFT_MASK_ERR_RALEN; }
  ////  //// another idea..
  ////  //if( strlen(tcs->RA)>11 ) { strcpy(tcs->RA, tcs->prevRA); rtn |= COMSOFT_MASK_ERR_RALEN; } 
  ////  //strcpy(tcs->prevRA, tcs->RA);

  //// v1.6.5
  sscanf(ra,"%02d%02d%f",&rah,&ram,&ras);

  if( ras>59.990 && ras<60.005 ) {
    ras = 59.990;
    rtn |= COMSOFT_MASK_COR_RAS_RO;
  }

  if( rah>=24 || rah<0 ) {
    temp[0]=tcsstr[3];
    temp[1]=tcsstr[4];
    temp[2]='\0';
    rah = atoi(temp);
    rtn |= COMSOFT_MASK_COR_RAH_AC;
  }
  if( ram>=60 || ram<0 ) {
    temp[0]=tcsstr[5];
    temp[1]=tcsstr[6];
    temp[2]='\0';
    ram = atoi(temp);
    rtn |= COMSOFT_MASK_COR_RAM_AC;
  }
  if( ras>=60.0 || ras<0.0 ) { 
    temp[0]=tcsstr[7];
    temp[1]=tcsstr[8];
    temp[2]='.' ;
    temp[3]=tcsstr[10];
    temp[4]=tcsstr[11];
    temp[5]='\0';
    ras = atof(temp);
    rtn |= COMSOFT_MASK_COR_RAS_AC;
  }

  if( rah>=24   || rah<0   ) { rah = 0  ; rtn |= COMSOFT_MASK_ERR_RAHOUR; }
  if( ram>=60   || ram<0   ) { ram = 0  ; rtn |= COMSOFT_MASK_ERR_RAMIN ; }
  if( ras>=60.0 || ras<0.0 ) { ras = 0.0; rtn |= COMSOFT_MASK_ERR_RASEC ; }

  sprintf(tcs->RA,"%02d:%02d:%05.2f",rah,ram,ras);

  if( strlen(tcs->RA)>11 ) { strcpy(tcs->RA, "00:00:00.00"); rtn |= COMSOFT_MASK_ERR_RALEN; }


  // scan dec into parts, convert to +dd:mm:ss.s 

  ////  //// oldver
  ////  //sscanf(dec,"%1s%02d%02d%f",dsgn,&decd,&decm,&decs);
  ////  //sprintf(tcs->Dec,"%1s%.2i:%.2i:%04.1f",dsgn,decd,decm,decs);

  ////  //// v1.6.3
  ////  sscanf(dec,"%1s%02d%02d%f",dsgn,&decd,&decm,&decs);
  ////  if( dsgn[0]!='+' && dsgn[0]!='-' ) { dsgn[0]='+'; dsgn[1]='\0'; rtn |= COMSOFT_MASK_ERR_DECSGN; }
  ////  if( decd> 90   || decd< -90   ) { decd = 0  ;  rtn |= COMSOFT_MASK_ERR_DECDEG; }
  ////  if( decm>=60   || decm<   0   ) { decm = 0  ;  rtn |= COMSOFT_MASK_ERR_DECMIN; }
  ////  if( decs>=60.0 || decs<   0.0 ) { decs = 0.0;  rtn |= COMSOFT_MASK_ERR_DECSEC; }
  ////  sprintf(tcs->Dec,"%1s%02d:%02d:%04.1f",dsgn,decd,decm,decs);
  ////  if( strlen(tcs->Dec)>11 ) { strcpy(tcs->Dec, "+00:00:00.0"); rtn |= COMSOFT_MASK_ERR_DECLEN; }

  //// v1.6.5
  sscanf(dec,"%1s%02d%02d%f",dsgn,&decd,&decm,&decs);
  //printf(" (decd=%d) ", decd);

  if( decs>59.90 && decs<60.05 ) {
    decs = 59.90;
    rtn |= COMSOFT_MASK_COR_DECS_RO;
  }

  if( dsgn[0]!='+' && dsgn[0]!='-' ) {
    dsgn[0]=tcsstr[13];
    dsgn[1]='\0';
    rtn |= COMSOFT_MASK_COR_DSGN_AC;
  }
  if( decd>90 || decd<0 ) {
    temp[0]=tcsstr[14];
    temp[1]=tcsstr[15];
    temp[2]='\0';
    decd = atoi(temp);
    rtn |= COMSOFT_MASK_COR_DECD_AC;
  }
  if( decm>=60 || decm<0 ) {
    temp[0]=tcsstr[16];
    temp[1]=tcsstr[17];
    temp[2]='\0';
    decm = atoi(temp);
    rtn |= COMSOFT_MASK_COR_DECM_AC;
  }
  if( decs>=60.0 || decs<0.0 ) { 
    temp[0]=tcsstr[18];
    temp[1]=tcsstr[19];
    temp[2]='.'       ;
    temp[3]=tcsstr[21];
    temp[4]='\0'      ;
    decs = atof(temp);
    rtn |= COMSOFT_MASK_COR_DECS_AC;
  }

  if( dsgn[0]!='+' && dsgn[0]!='-' ) { dsgn[0]='+'; dsgn[1]='\0'; rtn |= COMSOFT_MASK_ERR_DECSGN; }
  if( decd> 90   || decd< -90   ) { decd = 0  ;  rtn |= COMSOFT_MASK_ERR_DECDEG; }
  if( decm>=60   || decm<   0   ) { decm = 0  ;  rtn |= COMSOFT_MASK_ERR_DECMIN; }
  if( decs>=60.0 || decs<   0.0 ) { decs = 0.0;  rtn |= COMSOFT_MASK_ERR_DECSEC; }

  sprintf(tcs->Dec,"%1s%02d:%02d:%04.1f",dsgn,decd,decm,decs);

  if( strlen(tcs->Dec)>11 ) { strcpy(tcs->Dec, "+00:00:00.0"); rtn |= COMSOFT_MASK_ERR_DECLEN; }

  // Convertions for RA/Dec to Hour/Deg values from strings

  tcs->dRA  =  RACoordConv(ra     );  // v1.5.0
  tcs->dDec = DecCoordConv(dec    );  // v1.2.3

  // Convertions for HA to Hour/Deg values from strings

  tcs->dHA  =  HACoordConv(tcs->HA);  // v1.5.0

  if( tcs->dHA < COMSOFT_SPEC_HA_NEG || tcs->dHA > COMSOFT_SPEC_HA_POS || strlen(tcs->HA)>9 ) {  // v1.6.5
    tcs->HA[0]=tcsstr[24]; tcs->HA[1]=tcsstr[25]; tcs->HA[2]=tcsstr[26];
    tcs->HA[3]=tcsstr[27]; tcs->HA[4]=tcsstr[28]; tcs->HA[5]=tcsstr[29];
    tcs->HA[6]=tcsstr[30]; tcs->HA[7]=tcsstr[31]; tcs->HA[8]=tcsstr[32];
    tcs->HA[9]=NULL;
    tcs->dHA  =  HACoordConv(tcs->HA);
    rtn |= COMSOFT_MASK_COR_HASTR;
  }

  if( tcs->dHA < COMSOFT_SPEC_HA_NEG || tcs->dHA > COMSOFT_SPEC_HA_POS ) {  // v1.6.5
    tcs->dHA = 0.0;
    strcpy(tcs->HA, "+00:00:00");
    rtn |= COMSOFT_MASK_ERR_HAVAL;
  }

  // check for Alt/Az/SecZ data (added at v1.6.3)

  if( tcsstr[45]!='.' ) { strcpy(tcs->Alt ,   "90.0"  ); rtn |= COMSOFT_MASK_ERR_NOALT ; }
  if( tcsstr[53]!='.' ) { strcpy(tcs->Az  , "  +0.0"  ); rtn |= COMSOFT_MASK_ERR_NOAZ  ; }
  if( tcsstr[58]!='.' ) { strcpy(tcs->SecZ,   " 1.00" ); rtn |= COMSOFT_MASK_ERR_NOSECZ; }

  // Motion status and limit status flags

  tcs->MoveStatus = (int)(tcsstr[0]-0x30);  //0x30='0'
  if( tcs->MoveStatus < 0 || tcs->MoveStatus > 3 ) tcs->MoveStatus = -1;

       if(tcsstr[71]=='1') tcs->RALimit =  1;
  else if(tcsstr[71]==' ') tcs->RALimit =  0;
  else                     tcs->RALimit = -1;

       if(tcsstr[72]=='1') tcs->DecLimit =  1;
  else if(tcsstr[72]==' ') tcs->DecLimit =  0;
  else                     tcs->DecLimit = -1;

       if(tcsstr[73]=='1') tcs->HorizonLimit =  1;
  else if(tcsstr[73]==' ') tcs->HorizonLimit =  0;
  else                     tcs->HorizonLimit = -1;

       if(tcsstr[74]=='1') tcs->DriveDisable =  1;
  else if(tcsstr[74]==' ') tcs->DriveDisable =  0;
  else                     tcs->DriveDisable = -1;

  if ( tcs->RALimit<0 || tcs->DecLimit<0 || tcs->HorizonLimit<0 ) {
    tcs->LimitStatus = -1;
  }
  ////else { 
  ////       if (tcs->RALimit     ) tcs->LimitStatus = 1;
  ////  else if (tcs->DecLimit    ) tcs->LimitStatus = 2;
  ////  else if (tcs->HorizonLimit) tcs->LimitStatus = 3;
  ////  else                        tcs->LimitStatus = 0;
  ////}  // v1.4.1
  else { 
    tcs->LimitStatus = 0x00;
    if (tcs->RALimit     ) tcs->LimitStatus |= 0x01;
    if (tcs->DecLimit    ) tcs->LimitStatus |= 0x02;
    if (tcs->HorizonLimit) tcs->LimitStatus |= 0x04;
  }  // v1.6.6


  tcs->ComNum = (int)(tcsstr[94]-0x30);  //0x30='0'
  if( tcs->ComNum < 0 || tcs->ComNum > 8 ) tcs->ComNum = -1;

  tcs->ExeCode = tcsstr[61+tcs->ComNum];  // blank/'e'/'E'/'3'/..
  tcs->UpdateFlag = 1;
      // Description of UpdateFlag:
      // This flag is used for checking execution code is updated.
      // This flag is set to 0 after operating command is sended and  
      // checked before sending another operating command in commands.c.
      // After sending operating command, update request command is also
      // sended in commands.c for prompt update of telemetry data including
      // the execution code, and then set to 1 if telemetry data is received.

  // keep the telemetry raw packet string

  strcpy(tcs->RawPacket, tcsstr);

  // summarize result of check for data field/value/string length (v1.6.3)

  strcpy(tcs->DataChkMsg, "ERR");
  if( rtn & COMSOFT_MASK_ERR_NOALT   ) strcat(tcs->DataChkMsg, "_NOAL");
  if( rtn & COMSOFT_MASK_ERR_NOAZ    ) strcat(tcs->DataChkMsg, "_NOAZ");
  if( rtn & COMSOFT_MASK_ERR_NOSECZ  ) strcat(tcs->DataChkMsg, "_NOSZ");
  if( rtn & COMSOFT_MASK_ERR_RAHOUR  ) strcat(tcs->DataChkMsg, "_RH"  );
  if( rtn & COMSOFT_MASK_ERR_RAMIN   ) strcat(tcs->DataChkMsg, "_RM"  );
  if( rtn & COMSOFT_MASK_ERR_RASEC   ) strcat(tcs->DataChkMsg, "_RS"  );
  if( rtn & COMSOFT_MASK_ERR_RALEN   ) strcat(tcs->DataChkMsg, "_RL"  );
  if( rtn & COMSOFT_MASK_ERR_DECSGN  ) strcat(tcs->DataChkMsg, "_DG"  );
  if( rtn & COMSOFT_MASK_ERR_DECDEG  ) strcat(tcs->DataChkMsg, "_DD"  );
  if( rtn & COMSOFT_MASK_ERR_DECMIN  ) strcat(tcs->DataChkMsg, "_DM"  );
  if( rtn & COMSOFT_MASK_ERR_DECSEC  ) strcat(tcs->DataChkMsg, "_DS"  );
  if( rtn & COMSOFT_MASK_ERR_DECLEN  ) strcat(tcs->DataChkMsg, "_DL"  );
  if( rtn & COMSOFT_MASK_ERR_HAVAL   ) strcat(tcs->DataChkMsg, "_HV"  );
  if( rtn & COMSOFT_MASK_COR_HASTR   ) strcat(tcs->DataChkMsg, "_CHAS");
  if( rtn & COMSOFT_MASK_COR_RAH_AC  ) strcat(tcs->DataChkMsg, "_CRHA");
  if( rtn & COMSOFT_MASK_COR_RAM_AC  ) strcat(tcs->DataChkMsg, "_CRMA");
  if( rtn & COMSOFT_MASK_COR_RAS_AC  ) strcat(tcs->DataChkMsg, "_CRSA");
  if( rtn & COMSOFT_MASK_COR_RAS_RO  ) strcat(tcs->DataChkMsg, "_CRSR");
  if( rtn & COMSOFT_MASK_COR_DSGN_AC ) strcat(tcs->DataChkMsg, "_CDGA");
  if( rtn & COMSOFT_MASK_COR_DECD_AC ) strcat(tcs->DataChkMsg, "_CDDA");
  if( rtn & COMSOFT_MASK_COR_DECM_AC ) strcat(tcs->DataChkMsg, "_CDMA");
  if( rtn & COMSOFT_MASK_COR_DECS_AC ) strcat(tcs->DataChkMsg, "_CDSA");
  if( rtn & COMSOFT_MASK_COR_DECS_RO ) strcat(tcs->DataChkMsg, "_CDSR");
  //// strlen("ERR_NOAL_NOAZ_NOSZ_RH_RM_RS_RL_DG_DD_DM_DS_DL_HV"
  ////        "CHAS_CRHA_CRMA_CRSA_CRSR_CDGA_CDDA_CDMA_CDSA_CDSR") = 95

  if( rtn == COMSOFT_RTN_NOERROR     ) strcpy(tcs->DataChkMsg, "NORMAL");

  // Some things will need to be computed, do it here eventually

  // ..

  // all done 

  return rtn;  // v1.6.3 (return 0; until v1.6.2)
}

//------------------------------------------------------------------------------
//
// UpdateTcsMoving() - Monitoring and Display the telescope moving status
//
// Arguments:
//   tcs: pointer to a pctcs_config data structure
//
// Description:
//   If the telescope is moving, display the telescope position on the consol.
//   The routine of this function was saparated from original parse_comsoft() 
//   to handle message display and modified for KMTNet TCS Agent
//
//   This function is called right after parse_comsoft() in main() for 
//   monitoring the telescope moving status code in TCS telemetry data,
//   and update moving status. In the case that parse-comsoft() is called 
//   only for updating the telemetry data with execution code in commands.c, 
//   This function is not used because user don't need to know moving status
//   during operation command process.
//
// Author:
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2003 February 1 (original code)
//
// Modification History:
//   2014 Apr 16: saparate the routine from parse_comsoft() 
//                and modified for KMTNet [sc/kasi]
//
//------------------------------------------------------------------------------

void
UpdateTcsMoving(pctcs_t *tcs) 
{
  static int aftermove=0;  // the number of telemetry after moving completed

  // If we're moving, show update status on the console...

  if (tcs->Moving) {

    // telescope was moving

    if (tcs->MoveStatus > 0) { // still moving...
      sprintf(cmsg, "%d RA=%s Dec=%s HA=%s ST=%s UTC=%s",
                    tcs->MoveStatus, tcs->RA, tcs->Dec, tcs->HA, tcs->LST, tcs->UTC);
      BLUTEXT;  printf("\r%s\r",cmsg);  TXTRESET;  fflush(stdout);
      strcat(cmsg,"\n");_msglog(cmsg);
    } 
    else if(tcs->MoveStatus == 0){ // but not any more...
      tcs->Moving = 0;
      aftermove = 1;
      sprintf(cmsg, "%d RA=%s Dec=%s HA=%s ST=%s UTC=%s",
              tcs->MoveStatus, tcs->RA, tcs->Dec, tcs->HA, tcs->LST, tcs->UTC);
      BLUTEXT;  printf("\r%s\r",cmsg);  TXTRESET;  fflush(stdout);
      strcat(cmsg,"\n");_msglog(cmsg);
    }
  }

  // telescope was not moving as of last telemetry packet

  else {

    if (tcs->MoveStatus > 0) { 
      // but it is moving now
      tcs->Moving = 1;
      sprintf(cmsg, "%d RA=%s Dec=%s HA=%s ST=%s UTC=%s",
              tcs->MoveStatus, tcs->RA, tcs->Dec, tcs->HA, tcs->LST, tcs->UTC);
      BLUTEXT;  printf("\r%s\r",cmsg);  TXTRESET;  fflush(stdout);
      strcat(cmsg,"\n");_msglog(cmsg);
    }
    if(aftermove) {
      aftermove++;
      if(aftermove>DISPLAY_DELAY) {
        aftermove = 0;
        rl_refresh_line(0,0);
      }
    } // end of if(aftermove) {}

  } // end of if(tcs->Moving) {} else {}

}

/*!
  \brief - Get HA value in hours from HA string in PC-TCS telemetry data (v1.5.0)

  \param strCoord  : pointer to a HA string in PC-TCS telemetry data
  
  \return : double HA in hours
*/

double HACoordConv(const char *strCoord)
{
	//format: +hh:mm:ss
	double dHour, dSec;
	int nHour, nMin;
	char strBuf[16];
	
	strcpy(strBuf, strCoord);

	strBuf[9] = NULL;
	dSec = atof(strBuf+7);

	strBuf[6] = NULL;
	nMin = atoi(strBuf+4);
		
	strBuf[3] = NULL;
	nHour = atoi(strBuf+1);

	dHour = (double)nHour + (double)nMin/60.0 + dSec/3600.0;

	     if(strBuf[0]=='-') dHour *= -1.0;
	else if(strBuf[0]=='+') dHour *= +1.0;
	else                    dHour *=  0.0;
	
	return dHour;
}

/*!
  \brief - Get RA value in hours from RA string in PC-TCS telemetry data (v1.5.0)

  \param strCoord  : pointer to a RA string in PC-TCS telemetry data
  
  \return : double RA in hours
*/

double RACoordConv(const char *strCoord)
{
	//format: hhmmss.ss
	double dHour, dSec;
	int nHour, nMin;
	char strBuf[16];

	strcpy(strBuf, strCoord);

	strBuf[9] = NULL;
	dSec = atof(strBuf+4);

	strBuf[4] = NULL;
	nMin = atoi(strBuf+2);
		
	strBuf[2] = NULL;
	nHour = atoi(strBuf+0);

	dHour = (double)nHour + (double)nMin/60.0 + dSec/3600.0;
	
	return dHour;
}

/*!
  \brief - Get Dec value in degrees from Dec string in PC-TCS telemetry data (v1.2.3)

  \param strCoord  : pointer to a Dec string in PC-TCS telemetry data
  
  \return Dec in degrees
*/

double DecCoordConv(const char *strCoord)
{
	//format: +ddmmss.s
	double dDeg, dSec;
	int nDeg, nMin;
	char strBuf[16];

	strcpy(strBuf, strCoord);

	strBuf[9] = NULL;
	dSec = atof(strBuf+5);

	strBuf[5] = NULL;
	nMin = atoi(strBuf+3);
		
	strBuf[3] = NULL;
	nDeg = atoi(strBuf+1);

	dDeg = (double)nDeg + (double)nMin/60.0 + dSec/3600.0;

	     if(strBuf[0]=='-') dDeg *= -1.0;
	else if(strBuf[0]=='+') dDeg *= +1.0;
	else                    dDeg *=  0.0;
	
	return dDeg;
}

/*!
  \brief - Initialize the PC-TCS Telcom tcp link

  \param tcs  : pointer to a pctcs data structure
  \param reply: string to contain the reply status
  
  \return 0 on success, -1 on errors

  (Re)initializes the Telcom tcp socket and connect to Telcom

*/

int
InitPCTCS(pctcs_t *tcs, char *reply)
{
  struct termios tty;  /* Port configuration structure */
  int i, rtn;
  int NFlush=3;
  char junk[256];
  struct timeval timeout_tcscmd;

  // If the any tcp connection is active, close it before proceeding.

  ClearPCTCS(tcs);

  // Create tcp socket and connection to Telcom server for the telemetry
  
  tcs->FDtel = socket(AF_INET, SOCK_STREAM, 0);
  if(tcs->FDtel<0) {
    strcpy(reply, "cannot create tcp socket for the telemetry");
    tcs->Link = TCS_DOWN;
    tcs->FDtel = -1;
    return -1;
  }

	rtn = connect(tcs->FDtel, (struct sockaddr *)&tcs->Addr, sizeof(tcs->Addr));
	if(rtn<0) {
    strcpy(reply, "cannot connect to Telcom server for the telemetry");
    tcs->Link = TCS_DOWN;
    close(tcs->FDtel);
    tcs->FDtel = -1;
    return -1;
  }
  
  // Create tcp socket and connection to Telcom server for command proc
  
  tcs->FDcmd = socket(AF_INET, SOCK_STREAM, 0);
  if(tcs->FDcmd<0) {
    sprintf(reply,"cannot create tcp socket for command process");
    tcs->Link = TCS_DOWN;
    tcs->FDcmd = -1;    
    return -1;
  }

  timeout_tcscmd.tv_sec  = TCP_TIMEOUT_TCSCMD_SEC;
  timeout_tcscmd.tv_usec = TCP_TIMEOUT_TCSCMD_MS*1000;
  setsockopt(tcs->FDcmd, SOL_SOCKET, SO_RCVTIMEO, &timeout_tcscmd, sizeof(struct timeval));
    // set timeoout of recv() for TCS command TCP socket, 
    // to avoid blocking by recv() when TCP link is failed, v1.2.2

	rtn = connect(tcs->FDcmd, (struct sockaddr *)&tcs->Addr, sizeof(tcs->Addr));
	if(rtn<0) {
    sprintf(reply,"cannot connect to Telcom server for command process");
    tcs->Link = TCS_DOWN;
    close(tcs->FDcmd);
    tcs->FDcmd = -1;
    return -1;
  }

  sprintf(reply,"PC-TCS Telcom TCP Link Initialized");
  tcs->Link = TCS_UP;

  // Set Tick for checking TCS link status and telemetry data

  tcs->TelcomTick = SysTimestamp();  // set to UP or IDLE
  tcs->PctcsTick  = SysTimestamp();  // set to UP

  // Some other initializations

  tcs->Moving = 0;     // set these as "not", next telemetry will update
  tcs->MoveStatus = 0;
  tcs->LimitStatus = 0;

  memset(tcs->RequestMsg, 0, sizeof(tcs->RequestMsg));
  tcs->RequestLen = sprintf(tcs->RequestMsg, "%s %s %03d REQUEST ALL\n",
                                              tcs->TelID, tcs->SysID, PID_REQCMD);
  tcs->ReqHedLen = tcs->RequestLen - 12;
  tcs->MinTelemetryLen = tcs->ReqHedLen + MIN_TCSBUF;

  return 0;
}

/*!
  \brief - Clear the PC-TCS Telcom (TCS) telemetry data

  \param tcs: pointer to a pctcs data structure
  
  \no return

  close the Telcom tcp socket and reset the TCS telemetry data

*/

void
ClearPCTCS(pctcs_t *tcs)
{
  // Tear down the TCS server socket connection

  if (tcs->FDtel>0) close(tcs->FDtel);
  if (tcs->FDcmd>0) close(tcs->FDcmd);
  tcs->FDtel = tcs->FDcmd = -1;
  tcs->Link = TCS_DOWN;

  // Clear PC-TCS telemetry data

  memset(tcs->RA        , 0, sizeof(tcs->RA        ));
  memset(tcs->Dec       , 0, sizeof(tcs->Dec       ));
  memset(tcs->HA        , 0, sizeof(tcs->HA        ));
  memset(tcs->LST       , 0, sizeof(tcs->LST       ));
  memset(tcs->SecZ      , 0, sizeof(tcs->SecZ      ));
  memset(tcs->Equinox   , 0, sizeof(tcs->Equinox   ));
  memset(tcs->Date      , 0, sizeof(tcs->Date      ));
  memset(tcs->UTC       , 0, sizeof(tcs->UTC       ));
  memset(tcs->Alt       , 0, sizeof(tcs->Alt       ));
  memset(tcs->Az        , 0, sizeof(tcs->Az        ));
  memset(tcs->RawPacket , 0, sizeof(tcs->RawPacket ));
  memset(tcs->DataChkMsg, 0, sizeof(tcs->DataChkMsg));

  tcs->MoveStatus   =  -1;
  tcs->LimitStatus  =  -1;
  tcs->RALimit      =  -1;
  tcs->DecLimit     =  -1;
  tcs->HorizonLimit =  -1;
  tcs->DriveDisable =  -1;
  tcs->Moving       =  -1;
  tcs->ComNum       =  -1;
  tcs->ExeCode      = ' ';

  tcs->dDec = 0.0;

  // all done
}

/*!
  \brief - Initialize the AUX control tcp link

  \param aux  : pointer to a aux ctrl data structure
  \param reply: string to contain the reply status
  
  \return 0 on success, -1 on errors

  (Re)initializes the AUX control tcp socket and connect to AUX control server

*/

int
InitAUX(auxctrl_t *aux, char *reply)
{
  struct termios tty;  /* Port configuration structure */
  int i, rtn;
  int NFlush=3;
  char junk[256];
  struct timeval timeout_aux;

  // If the any tcp connection is active, close it before proceeding.

  ClearAUX(aux);

  // Create tcp socket and connection to AUX control server
  
  aux->FD = socket(AF_INET, SOCK_STREAM, 0);
  if(aux->FD<0) {
    strcpy(reply, "cannot create tcp socket for AUX control");
    aux->Link = AUX_DOWN;
    aux->FD = -1;
    return -1;
  }

  timeout_aux.tv_sec  = TCP_TIMEOUT_AUX_SEC;
  timeout_aux.tv_usec = TCP_TIMEOUT_AUX_MS*1000;
  setsockopt(aux->FD, SOL_SOCKET, SO_RCVTIMEO, &timeout_aux, sizeof(struct timeval));
    // set timeoout of recv() for AUX TCP socket, 
    // to avoid blocking by recv() when TCP link is failed, v1.2.2

	rtn = connect(aux->FD, (struct sockaddr *)&aux->Addr, sizeof(aux->Addr));
	if(rtn<0) {
    strcpy(reply, "cannot connect to AUX server");
    aux->Link = AUX_DOWN;
    close(aux->FD);
    aux->FD = -1;
    return -1;
  }

  aux->Link = AUX_UP;

  rtn = AuxFilterNameUpdate(aux, reply);
  if(rtn<0) {
    aux->Link = AUX_DOWN;
    close(aux->FD);
    aux->FD = -1;
    return -1;
  }

  aux->FS_CmdFilNum = AUX_UNKNOWN;  // v1.6.1

  sprintf(reply,"AUX control Link Initialized");

  // Some other initializations

  return 0;
}

/*!
  \brief - Clear the AUX control data

  \param aux: pointer to a aux ctrl data structure
  
  \no return

  close the aux tcp socket and reset the aux ctrl data

*/

void
ClearAUX(auxctrl_t *aux)
{
  // Tear down the AUX server socket connection

  if (aux->FD>0) close(aux->FD);
  aux->FD = -1;
  aux->Link = AUX_DOWN;

  // Clear all AUX subsystem's telemetry data

  ClearAuxData(aux, AUX_IDX_AL);

  // all done
}

/*!
  \brief - Clear the AUX control data for designated subsystem

  \param aux   : pointer to a aux ctrl data structure
  \param subsys: index of subsystem
  
  \no return

*/

void
ClearAuxData(auxctrl_t *aux, int subsys)
{
  if( subsys==AUX_IDX_FS || subsys==AUX_IDX_AL ) {
    aux->Statuses[AUX_IDX_FS]          = AUX_STATUS_NC;
    aux->FS_Limits[AUX_IDX_FS_F1]      = AUX_UNKNOWN;
    aux->FS_Limits[AUX_IDX_FS_F2]      = AUX_UNKNOWN;
    aux->FS_Limits[AUX_IDX_FS_F3]      = AUX_UNKNOWN;
    aux->FS_Limits[AUX_IDX_FS_F4]      = AUX_UNKNOWN;
    aux->FS_Limits[AUX_IDX_FS_SH]      = AUX_UNKNOWN;
    aux->FS_Limits[AUX_IDX_FS_SF]      = AUX_UNKNOWN;
    aux->FS_FilterNum                  = AUX_UNKNOWN;
    aux->FS_FilterOpStat               = AUX_FS_FOP_NC;
    aux->FS_ShutStatus                 = AUX_UNKNOWN;
    aux->FS_ShutOpStat                 = AUX_FS_SOP_NC;
    strcpy(aux->FS_FilterName, AUX_FS_FNAME_UNKNOWN);
  }

  if( subsys==AUX_IDX_FA || subsys==AUX_IDX_AL ) {
    aux->Statuses[AUX_IDX_FA]          = AUX_STATUS_NC;
    aux->FA_Limits[AUX_IDX_FA_A1]      = AUX_UNKNOWN;
    aux->FA_Limits[AUX_IDX_FA_A2]      = AUX_UNKNOWN;
    aux->FA_Limits[AUX_IDX_FA_A3]      = AUX_UNKNOWN;
    aux->FA_Positions[AUX_IDX_FA_A1]   = 0.0;
    aux->FA_Positions[AUX_IDX_FA_A2]   = 0.0;
    aux->FA_Positions[AUX_IDX_FA_A3]   = 0.0;
    aux->FA_Focus                      = 0.0;
    aux->FA_TiltNS                     = 0.0;
    aux->FA_TiltEW                     = 0.0;
    aux->FA_ActPoss[SOUTH]             = 0.0;
    aux->FA_ActPoss[EAST]              = 0.0;
    aux->FA_ActPoss[WEST]              = 0.0;
    aux->FA_ActLims[SOUTH]             = AUX_UNKNOWN;
    aux->FA_ActLims[EAST]              = AUX_UNKNOWN;
    aux->FA_ActLims[WEST]              = AUX_UNKNOWN;
  }

  if( subsys==AUX_IDX_DS || subsys==AUX_IDX_AL ) {
    aux->Statuses[AUX_IDX_DS]          = AUX_STATUS_NC;
    aux->DS_LimitUpper                 = AUX_UNKNOWN;
    aux->DS_LimitLower                 = AUX_UNKNOWN;
    aux->DS_LimitSafety                = AUX_UNKNOWN;
    aux->DS_AutoSync                   = DISABLED;
    aux->DS_ShutAlt                    = 0.0;
    aux->DS_TeleAlt                    = 0.0;
  }

  if( subsys==AUX_IDX_MC || subsys==AUX_IDX_AL ) {
    aux->Statuses[AUX_IDX_MC]          = AUX_STATUS_NC;
    aux->MC_Position                   = 0;
  }

  if( subsys==AUX_IDX_CH || subsys==AUX_IDX_AL ) {
    aux->Statuses[AUX_IDX_CH]          = AUX_STATUS_NC;
    aux->CH_Cooling                    = OFF;
    aux->CH_Setpoint                   = 0.0;
    aux->CH_ProcTemp                   = 0.0;
  }

  if( subsys==AUX_IDX_EN || subsys==AUX_IDX_AL ) {
    aux->Statuses[AUX_IDX_EN]          = AUX_STATUS_NC;
    aux->EN_FanRelay                   = OFF;
    aux->EN_Sensors[0]                 = 0.0;
    aux->EN_Sensors[1]                 = 0.0;
    aux->EN_Sensors[2]                 = 0.0;
    aux->EN_Sensors[3]                 = 0.0;
    aux->EN_Sensors[4]                 = 0.0;
    aux->EN_Sensors[5]                 = 0.0;
    aux->EN_Sensors[6]                 = 0.0;
  }

  if( subsys==AUX_IDX_AL ) {
    memset(aux->Date, 0, sizeof(aux->Date));
    memset(aux->UTC , 0, sizeof(aux->UTC ));
  }

  // all done
}

/*!
  \brief - Return the AUX subsystem's name for designated index

  \param subsys: index of subsystem
  
  \no return

  close the aux tcp socket and reset the aux ctrl data

*/

char
*GetAuxSubsysName(int SubsysIndex)
{
  static char SubsysName[16];

  switch(SubsysIndex) {
  case AUX_IDX_FS: strcpy(SubsysName, "Filter/Shutter"); break;
  case AUX_IDX_FA: strcpy(SubsysName, "Focuser"       ); break;
  case AUX_IDX_DS: strcpy(SubsysName, "Dome shutter"  ); break;
  case AUX_IDX_MC: strcpy(SubsysName, "Mirror cover"  ); break;
  case AUX_IDX_CH: strcpy(SubsysName, "Chiller"       ); break;
  case AUX_IDX_EN: strcpy(SubsysName, "Environment"   ); break;
  default        : strcpy(SubsysName, "unknown"       ); break;
  }

  return SubsysName;
}

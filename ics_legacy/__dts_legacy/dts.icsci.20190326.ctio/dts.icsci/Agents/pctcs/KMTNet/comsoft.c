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
//
//
//   2015 Jan xx - SiteID update added in InitAUX()
//
//---------------------------------------------------------------------------

#include "pctcs.h"    // PC-TCS interface agent header

   int  parse_comsoft(pctcs_t *tcs, char *tcsstr);
  void  UpdateTcsMoving(pctcs_t *tcs);
double  DecCoordConv(const char *strCoord);
   int  InitPCTCS(pctcs_t *tcs, char *reply);
  void  ClearPCTCS(pctcs_t *tcs);
   int  InitAUX(auxctrl_t *aux, char *reply);
  void  ClearAUX(auxctrl_t *aux);
  void  ClearAuxData(auxctrl_t *aux, int subsys);
  char *GetAuxSubsysName(int SubsysIndex);

//---------------------------------------------------------------------------
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
//   2014 Sep 02: AuxFilterNameUpdate() added in InitAUX()
//
//---------------------------------------------------------------------------

int
parse_comsoft(pctcs_t *tcs, char *tcsstr)
{
  char ra[16];     // RA in hhmmss.ss format
  char dec[16];    // Dec in +ddmmss.s format
 
  int   rah;
  int   ram;
  float ras;
  char  dsgn[2];
  int   decd;
  int   decm;
  float decs;

  systime_t systime;

  //static int aftermove=0;

  // Check telemetry data

  if( tcsstr[0]==' ' ) return -5;  // no data
  if( tcsstr[53]!='.' || tcsstr[58]!='.' ) return -1; // no Alt Az data

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

  sscanf(ra,"%02d%02d%f",&rah,&ram,&ras);
  sprintf(tcs->RA,"%.2i:%.2i:%05.2f",rah,ram,ras);

  // scan dec into parts, convert to +dd:mm:ss.s 

  sscanf(dec,"%1s%02d%02d%f",dsgn,&decd,&decm,&decs);
  sprintf(tcs->Dec,"%1s%.2i:%.2i:%04.1f",dsgn,decd,decm,decs);
  tcs->dDec = DecCoordConv(dec);   // v1.2.3

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
  else { 
         if (tcs->RALimit     ) tcs->LimitStatus = 1;
    else if (tcs->DecLimit    ) tcs->LimitStatus = 2;
    else if (tcs->HorizonLimit) tcs->LimitStatus = 3;
    else                        tcs->LimitStatus = 0;
  }  // v1.4.1

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

  strcpy(tcs->RawPack, tcsstr);

  // Some things will need to be computed, do it here eventually

  // ..

  // all done 

  return 0;
}

//---------------------------------------------------------------------------
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
//---------------------------------------------------------------------------

void
UpdateTcsMoving(pctcs_t *tcs) 
{
  static int aftermove=0;  // the number of telemetry after moving completed

  // If we're moving, show update status on the console...

  if (tcs->Moving) {

    // telescope was moving

    if (tcs->MoveStatus > 0) { // still moving...
      BLUTEXT;
      printf("\r%d RA=%s Dec=%s HA=%s ST=%s UTC=%s\r",
              tcs->MoveStatus, tcs->RA, tcs->Dec, tcs->HA, tcs->LST, tcs->UTC);
      TXTRESET;
      fflush(stdout);
    } 
    else if(tcs->MoveStatus == 0){ // but not any more...
      tcs->Moving = 0;
      aftermove = 1;
      BLUTEXT;
      printf("\r%d RA=%s Dec=%s HA=%s ST=%s UTC=%s\r",
              tcs->MoveStatus, tcs->RA, tcs->Dec, tcs->HA, tcs->LST, tcs->UTC);
      TXTRESET;
      fflush(stdout);
    }
  }

  // telescope was not moving as of last telemetry packet

  else {

    if (tcs->MoveStatus > 0) { 
      // but it is moving now
      tcs->Moving = 1;
      BLUTEXT;
      printf("\r%d RA=%s Dec=%s HA=%s ST=%s UTC=%s\r",
              tcs->MoveStatus, tcs->RA, tcs->Dec, tcs->HA, tcs->LST, tcs->UTC);
      TXTRESET;
      fflush(stdout);
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
  \brief - Get Dec value in degrees from Dec string in PC-TCS telemetry data

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

  memset(tcs->RA     , 0, sizeof(tcs->RA     ));
  memset(tcs->Dec    , 0, sizeof(tcs->Dec    ));
  memset(tcs->HA     , 0, sizeof(tcs->HA     ));
  memset(tcs->LST    , 0, sizeof(tcs->LST    ));
  memset(tcs->SecZ   , 0, sizeof(tcs->SecZ   ));
  memset(tcs->Equinox, 0, sizeof(tcs->Equinox));
  memset(tcs->Date   , 0, sizeof(tcs->Date   ));
  memset(tcs->UTC    , 0, sizeof(tcs->UTC    ));
  memset(tcs->Alt    , 0, sizeof(tcs->Alt    ));
  memset(tcs->Az     , 0, sizeof(tcs->Az     ));

  memset(tcs->RawPack, 0, sizeof(tcs->RawPack));

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

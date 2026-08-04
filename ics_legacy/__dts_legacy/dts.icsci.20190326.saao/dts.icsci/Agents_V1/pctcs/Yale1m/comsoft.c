//
// comsoft - ComSoft PCTCS utility routines
//
// Routines:
//   void chksum_comsoft(char *cmd) - append a checksum to a PC-TCS command
//   void parse_comsoft(char *cmd) - parse a comsoft telemetry string
//                                   and load into the tcs struct
//
// Description:
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
// Author: 
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2003 February 1
//
// Modification History:
//   2004 Feb 29 - new-style routines for parsing that know which particular
//                 PC-TCS implementation we're using (see pctcs.h)
//
//---------------------------------------------------------------------------

#include "pctcs.h"  // PC-TCS interface agent header

//---------------------------------------------------------------------------
//
// chksum_comsoft() - append a checksum to a PCTCS command
//
// Arguments:
//   cmd (char *): command string
//
// Description:
//   A checksum consisting of the sum of all the ascii character
//   codes in the command string needs to be added to a remote PCTCS
//   command before uploading it to the PCTCS serial port.  All
//   characters are used except \n, and a \n is added at the end as
//   required by the PCTCS.
//
//   This code is taken directly from siocln_chksum_comsoft() from
//   the NOAO pcguider code written by R. Cantarutti at CTIO. 
//   
// Adapter: 
//   R. Pogge, OSU Astronomy Dept.
//   pogge@astronomy.ohio-state.edu
//   2003 February 1
//
// Modification History:
//   
//---------------------------------------------------------------------------

void 
chksum_comsoft(char *cmd)
{
  int sum=0;
  int len=0;
  int i, subchar;

  for (i=0; i <= strlen(cmd); i++) {
    len = i;
    subchar = cmd[i];
    if (subchar != 13)
      sum += subchar;
    else
      break;
  }
  cmd[len] = (sum % 64) + 0x20;
  cmd[len+1] = 13;
  return;
}

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
//
//---------------------------------------------------------------------------

void
parse_comsoft(pctcs_t *tcs, char *tcsstr)
{

  char wrkstr[32];

  // holding strings for stuff that must be converted 

  char ra[16];     // RA in hhmmss.ss format  
  char dec[16];    // Dec in +ddmmss.s format 
  char yymmdd[8];  // year in yymmdd format   
 
  int   rah;
  int   ram;
  float ras;
  char  dsgn[2];
  int   decd;
  int   decm;
  float decs;

  int yy, mm, dd, ccyy;

  int nchar = 0;
  int i;

  // Yow! 

  //  printf("tcsstr=%s\n",tcsstr);

  // Pick apart the telemetry string based on the telemetry tables
  // provided either by Dave Harvey or (more useful) empirically
  // determined for a particular PC-TCS emulation by looking at the
  // actual telemetry stream.  Some things are the same from
  // system-to-system, other things change significantly depending on
  // what customizations were requested.  Set the #def flags in pctcs.h
  // accordingly if adding an implementation below.

#if defined(__Lab)   // Lab PC-TCS emulator running at OSU
  SubStr(ra,tcsstr,3,11);       // raw RA is in 4-12, but string indexing is 0 relative
  SubStr(dec,tcsstr,13,21);     // raw Dec is in 14-22
  SubStr(tcs->HA,tcsstr,24,32);  // sexigesimal HA 
  SubStr(tcs->LST,tcsstr,34,41); // sexigesimla LST
  SubStr(tcs->Alt,tcsstr,43,46); // you get the drill...
  SubStr(tcs->Az,tcsstr,49,54);  
  SubStr(tcs->SecZ,tcsstr,56,60);
  SubStr(tcs->Equinox,tcsstr,75,82);
  SubStr(tcs->JD,tcsstr,84,92);
  SubStr(tcs->Focus,tcsstr,96,101);
  SubStr(tcs->UTC,tcsstr,110,119);

#elif defined(__Yale)   // CTIO Yale 1-meter Telescope PC-TCS system
  SubStr(ra,tcsstr,3,11);       
  SubStr(dec,tcsstr,13,21);     
  SubStr(tcs->HA,tcsstr,24,32);  
  SubStr(tcs->LST,tcsstr,34,41); 
  SubStr(tcs->Alt,tcsstr,43,46); 
  SubStr(tcs->Az,tcsstr,49,54);  
  SubStr(tcs->SecZ,tcsstr,56,60);
  SubStr(tcs->Equinox,tcsstr,75,82);
  SubStr(tcs->JD,tcsstr,84,95);
  SubStr(tcs->Focus,tcsstr,100,104);
  SubStr(tcs->UTC,tcsstr,113,122);
  SubStr(tcs->Date,tcsstr,124,133);

#elif defined(__CTIO13m)  // CTIO 1.3-meter (ex-2MASS) Telescope PC-TCS system
  SubStr(ra,tcsstr,3,11);       
  SubStr(dec,tcsstr,13,21);     
  SubStr(tcs->HA,tcsstr,24,32);  
  SubStr(tcs->LST,tcsstr,34,41); 
  SubStr(tcs->Alt,tcsstr,43,46); 
  SubStr(tcs->Az,tcsstr,49,54);  
  SubStr(tcs->SecZ,tcsstr,56,60);
  SubStr(tcs->Equinox,tcsstr,75,82);
  SubStr(tcs->JD,tcsstr,84,96);
  SubStr(yymmdd,tcsstr,98,103);    // date in yymmdd format, convert below
  SubStr(tcs->Temp,tcsstr,105,109);
  SubStr(tcs->Focus,tcsstr,111,116);
  SubStr(tcs->UTC,tcsstr,158,165);

#endif

  // now derive or convert bits that need converting, as required by the implementation

#if defined(__Lab)
  strcpy(tcs->Date,UTCDate());  // no UTC date returned by TCS, get it off the system clock
#elif defined(__CTIO13m)
  sscanf(yymmdd,"%02d%02d%02d",&yy,&mm,&dd);
  ccyy = yy + 2000;  // thanks...
  sprintf(tcs->Date,"%.4i-%.2i-%.2i",ccyy,mm,dd);  // proper ISO8601 format
#endif

  // Conversions required of all PC-TCS implementations

  // scan ra into parts, convert to hh:mm:ss.ss string 

  sscanf(ra,"%02d%02d%f",&rah,&ram,&ras);
  sprintf(tcs->RA,"%.2i:%.2i:%05.2f",rah,ram,ras);

  // scan dec into parts, convert to +dd:mm:ss.s 

  sscanf(dec,"%1s%02d%02d%f",dsgn,&decd,&decm,&decs);
  sprintf(tcs->Dec,"%1s%.2i:%.2i:%04.1f",dsgn,decd,decm,decs);

  // Motion status and limit status flags (same for all so far)

  SubStr(wrkstr,tcsstr,0,0);
  tcs->MoveStatus = atoi(wrkstr);

  SubStr(wrkstr,tcsstr,71,71);
  if (strstr(wrkstr,"R")>0) 
    tcs->RALimit = 1;
  else
    tcs->RALimit = 0;

  SubStr(wrkstr,tcsstr,72,72);
  if (strstr(wrkstr,"D")>0) 
    tcs->DecLimit = 1;
  else
    tcs->DecLimit = 0;

  SubStr(wrkstr,tcsstr,73,73);
  if (strstr(wrkstr,"H")>0) 
    tcs->HorizonLimit = 1;
  else
    tcs->HorizonLimit = 0;

  SubStr(wrkstr,tcsstr,74,74);
  if (strstr(wrkstr,"D")>0) 
    tcs->DriveDisable = 1;
  else
    tcs->DriveDisable = 0;

  // Some things will need to be computed, do it here eventually

  // Get the UTC time from the local clock now - don't believe the PC-TCS!

  strcpy(tcs->UTC,GetUTCTime());

  // If we're moving, show update status on the console...

  if (tcs->Moving) {

    // telescope was moving

    if (tcs->MoveStatus > 0) { // still moving...
      GRNTEXT;
      printf("RA=%s Dec=%s HA=%s ST=%s UTC=%s              \r",
	     tcs->RA, tcs->Dec, tcs->HA, tcs->LST, tcs->UTC);
      TXTRESET;
      fflush(stdout);
    } 
    else { // but not any more...
      tcs->Moving = 0;
      GRNTEXT;
      printf("RA=%s Dec=%s HA=%s ST=%s UTC=%s              \r",
	     tcs->RA, tcs->Dec, tcs->HA, tcs->LST, tcs->UTC);
      TXTRESET;
    }
  }
  else { // telescope was not moving as of last telemetry packet
    if (tcs->MoveStatus > 0) { 
      // but it is now...
      tcs->Moving = 1;
      GRNTEXT;
      printf("RA=%s Dec=%s HA=%s ST=%s UTC=%s           \r",
	     tcs->RA, tcs->Dec, tcs->HA, tcs->LST, tcs->UTC);
      TXTRESET;
      fflush(stdout);
    }
  }

  // all done 

  return;
}

/*!
  \brief - Initialize the TCS link

  \param tcs pointer to a pctcs data structure
  \param reply string to contain the reply status
  
  \return 0 on success, -1 on errors

  (Re)initializes the PC-TCS serial communications, clears the telemetry
  buffers, and gets the ball rolling.

*/

int
InitPCTCS(pctcs_t *tcs, char *reply)
{
  struct termios tty;  /* Port configuration structure */
  int istat;
  int i;
  int NFlush=3;
  char junk[256];

  // If the serial port is active, close it before proceeding.

  if (tcs->FD > 0) {
    istat = close(tcs->FD);
    tcs->FD = -1;
  }

  // Attempt to open the port and set its attributes
  
  tcs->FD = open(tcs->Port, O_RDWR|O_NDELAY);

  if (tcs->FD > 0) {

    // Port opened up OK, set attributes:
    //
    //  9600 baud, No parity, 8 data bits, 1 stop bit 
    //

    tcgetattr(tcs->FD, &tty);
    tty.c_iflag &= ~ISTRIP;     
    tty.c_lflag |= ICANON;
    tty.c_lflag &= ~ECHO;
    tty.c_cflag |= CS8;       // 8 data bits
    tty.c_cflag |= CREAD;
    tty.c_cflag &= ~CSTOPB;   // 1 stop bit 
    tty.c_cflag &= ~PARENB;   // no parity  
    tty.c_cc[VMIN] = 1;
    tty.c_cc[VTIME] = 0;
    cfsetispeed(&tty, (speed_t) B9600);  // input 9600 baud
    cfsetospeed(&tty, (speed_t) B9600);  // output 9600 baud
    tcflush(tcs->FD, TCIFLUSH);
    tcsetattr(tcs->FD, TCSAFLUSH, &tty);
 
    // Flush the serial port again to remove any crap, pausing 500msec
    // between flushes.

    BLUTEXT;
    printf("Initializing PC-TCS comm port...\n");
    printf("  Flushing PC-TCS comm port of junk...\n");
    for (i=0; i<NFlush; i++) {
      read(tcs->FD,junk,sizeof(junk));
      if (client.isVerbose) {
	printf("    Flush %d   \r",i);
	fflush(stdout);
      }
      MilliSleep(500);  
    }
    printf("done.          \n");
    TXTRESET;

  }
  else {
    sprintf(reply,"TCINIT Failed - Cannot open serial port %s - %s\n", 
	   tcs->Port,strerror(errno));
    tcs->Link = TCS_DOWN;
    tcs->FD = -1;
    return -1;
  }
    
  sprintf(reply,"PC-TCS Comm Link Initialized");
  tcs->Link = TCS_UP;

  // Some other initializations

  tcs->Moving = 0;     // set these as "not", next telemetry will update
  tcs->MoveStatus = 0;

  return 0;

}

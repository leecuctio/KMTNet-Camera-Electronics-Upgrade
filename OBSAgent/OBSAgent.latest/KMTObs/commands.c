//------------------------------------------------------------------------------
//
// commands.c - command action functions for the OBS Agent application
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
//   2004 Feb 17 (TCSAgent original version - agent pctcs for Yale1m v3.3.1)
//
//   S. Cha, KASI KMTNet team
//   chasm@kasi.re.kr
//   2014 Apr  1 (TCSAgent KMTNet version)
//   2016 Sep 20 (OBSAgent for KMTNet system)
//
// Modification History:
//   2016 Sep 20: OBSAgent v0.0 re-creation re-using TCSAgent flatform and code [sc/kasi]
//   2017 Aug 07: Replaced old code with new improved code of TCSAtgent v1.6.6 (v0.0.4)
//                Added 'timetag' command/func and modified _msgout/_vmsgout() (v0.0.5)
//                Command history fucntion improved with repetitions skip in history addition (v0.0.5)
//   2017 Aug 20: Removed codes and comments regarding TCS/AUX from TCSAgent (v0.0.6)
//   2017 Dec 19: cmd_init() modified with including PING sending for ISIS node registration (v0.0.7)
//                Filter names query and update functions, script commands (v0.0.7)
//   2017 Dec 26: KEY IN, ISIS IN, REMC IN, ISIS OUT, REMC OUT messages changed to debug msg from verbose msg (v0.0.8)
//                TC/PC-TCS/AUX connection monitoring and data update routine
//                TelStatus update: NC/CHECKING/STOW/HOLDING/TRACKING/TRACKINGS/SLEW/SETTLING/OSCILLATE/DISABLED
//                CamStatus update: NC/PREP_I/PREP_E/INT_1-3/CLOSING/READ_1-3/IDLE_1-3/CHECK/CRASHED/DEAD
//                Cam IC crash error handling routine - warning message to observer (v0.0.8)
//                Cam data acqustion completion check after readout (v0.0.8)
//                Cam fits data writing completion check after idle (v0.0.8)
//                TelStatus update: TRACKINGS (stable tracking state) and bumper for oscillation and disconnection determination (v0.0.8)
//                'systemstatus' command, Limit monitoring and warning routine (v0.0.8)
//   2017 Dec 31: script load/display command and func modification (v0.0.9)
//                _msgout()/_vmsgout() review and modification (v0.0.9)
//                debugging message logging, ISIS message sending function (v0.0.9)
//                ICs commands modified such as datasource using >k.ic/>m.ic/>t.ic/>n.ic (v0.0.9)
//                AUX data update function, script observation logging, Debugging message logging routine, Script obs results logging routine (v0.0.9)
//                ICs commands DATASOURCE/DMAWAIT added, input without '>k.ic/>m.ic/>t.ic/>n.ic'
//                New commands and functions: oline/sstat/sstart/sstop/spause(sp)/sresume(sr)
//                override(set flags to override subsys error, just now only to override aux connection error)
//   2018 Jan 02: script running routine/function implementation (v0.1.9)
//                current filter checking routine in ProcOsc()
//                toggle next exposure preparation routine
//                disagle to prepare next exp in the case cur type == CMD
//                disable to set exptime in the case of BIAS image type
//                RA/DEC pointing check with count and pause in the case of failure
//                Go response check (exposure start check) with count and pause in case no response(failure to exp start)
//                output messages check and check and modification, OscStatus string modification
//                New commands and functions: 'oprepare'(toggle next exposure preparation), 'oabort'(abort obs script running (immediately stop all the process)
//   2018 Jan 03: Slew/Filter commands when status >= READ_1 (No error at IDLE_3 if TC commands) (v0.2.2)
//                debugging for pointing before every exposure 
//                ostop command modification --> stop after complete the current exposure
//                New commands and functions: 'olabel'(query the line that has a label string including input string),
//                'oobject'(query the line that has a object string including input string)
//   2018 Jan 09: Script observation logging function implementation (v0.2.3)
//   2018 Jan 10: debugging unexpected TCS/AUX data updating error due to not enough arguments number
//                logging KEY IN and OSC IN message into the event log
//                several ERROR/WARNING message output modification
//                correction of FILTCMD --> ACTFILT in SysStatus (v0.2.4)
//   2018 Jan 11: improvement for handling the Acquisition completion error due to IC crash (v0.2.5)
//                (In case of the acquisition completion error due to IC crash, 
//                 now the script observation is paused and a ERROR message is displayed)
//                debugging for the routine monitoring the FITS Writing error (v0.2.5)
//                debugging for handling the msgtyp ERROR: messages from ICS (v0.2.5)
//                some modification for OSC.STATUS: verbose messages (v0.2.5)
//                telescope pointing trying number threshold(OSC_CHKCNT_POINTING) increased (v0.2.5)
//   2018 Jan 12: debugging QueryAuxData() remove the error of "Failed to send a command.." (v0.2.6)
//                adjusting allowance_tcsdisconnected & allowance_auxdisconnected number (v0.2.6)
//                modification to use TCS limit information from runtime configuration for each site (v0.2.6)
//                debugging "Wrote" counting error due to appended message "EXPSTATUS=.." (v0.2.7)
//   2018 Jan 18: realtime logging for the script observation result (v0.2.8)
//   2018 Jan 25: debugging for image type & object name setting during integration (v0.2.8)
//                debugging frequent tmr command sending in OSCILLATION status (v0.2.8)
//                debugging log modified, *GetSysStatus() added, *GetOscStatus() modified (v0.2.8)
//   2018 Feb 01: OSC IN message display on console (v0.3.0)
//                detecting 'EXPSTATUS=IDLE' message in STATUS: socket message process for 'go n' command (v0.3.0)
//   2018 Mar 20: For EXPSTATUS update in SocketCommand(), scrID check added to ignore msg from ICG/G.IC (v0.3.1/2)
//                ICS commands ACQSTATUS/EXPNUM added, input without '>ICS'  (v0.3.2)
//                ICs commands K/M/T/N/GSTATUS added, input without '>k.ic/>m.ic/>t.ic/>n.ic' (v0.3.2)
//                BLG-offset corrected RA/DEC applied in the current RA/DEC check routine 
//                 both for current and next exposure in ProcOsc() (v0.3.2)
//                response check keyword modification for ICS/TC.TCS/TC.AUX commands (v0.3.2)
//   2019 Mar 19: EXPREM (exposure time remaining) is added in SYSSTATUS string (v0.3.3)
//   2019 May 03: FSA error warning message output only once at the error occurred using flag_fsaerror (v0.3.4)
//   2020 Jul 27: warning blinking reset when anykey input, flag_warning=1 setting when critical error/warning, 
//                New commands and functions: 'warning' - set the warning blinking enable, 
//                'delay' - sleep the process as specified with arg in seconds (v0.3.5)
//   2020 Sep 17: debugging warning bliking, Telescope RA/Dec error checking for setting OSC_CMDBIT_STARTEXP (v0.3.6)
//   2020 Sep 18: the near-limit warning enhanced for HA & Alt when HA>0, cmd_getalt() added for Get_Altitude function test, 
//                checking clearance between the destination and the PC-TCS limit defined in INI and output warning message 
//                if near or out of the limit during the script observation in ProcOsc(), GetUTCDateTime() improved, 
//                zero setting for osc.count_process & sys.checknum_auxdata modified and reset when state changes (v0.4.0)
//   2020 Sep 18: TRACKING_ACCURACY replaced with tcs_tolerance, cmd_info() update for new configurations (v0.4.1)
//   2020 Sep 23: angular distance applied for checking RA pointing error, TELSTATUS_TRACKING/TRACKINGS condition modified, 
//                Ra/Dec pointing error output into the event log & display in verbose mode, GetAgentInfo() added,
//                tcs_tolerance is separated to tcs_tolerance_pointing and tcs_tolerance_tracking,
//                TelStatus TRACKING & STABLE conditions enhanced for waiting for telescope pointing start (v0.4.2)
//   2020 Sep 23: debugging for "WARNING: AUX data request commanded.." message/log instead of 
//                "Destination .... the limit, LINE#0000 exposure skipped !!" , Ra/Dec position error output into 
//                the debugging log & display in debugging mode instead of verbose mode (v0.4.3)
//   2020 Sep 29: DIFF_RA calculation modified and DEST_DEC(deg) included in the CHK_POSERR log, 
//                debugging for destination HA used for BLG offset correction function 
//                regarding to the "Input Data Error: Beyond the Range of Offset Table [-5.0,5.0]" error,
//                fsastatus included as a criterion for the filter change commanding to debug the 'WAIT' 
//                response error since filteropstatus is updated too slowly, 
//                force_idle(criterion for ERROR: Acquisition is not fully completed) changed 40(2s) --> 60(3s),
//                cancellation of commanding flags for the skipped next exposure, and re-configuration of flags 
//                for another next exposure line when an exposure skipped during the script observation, 
//                osc.expnum_skip member included and initialized when starting osc and next exp skipped (v0.4.4)
//   2020 Oct 08: 'EXP'/'OBJECT'/'DARK'/'BIAS'/'FLAT'/'PROJID'/'OBSERVER' commands are ignored when CamStatus is NOT CAMSTATUS_INT/_READ/_READY, and 
//                'GO' command is ignored when CamStatus is NOT CAMSTATUS_IDLE_3/_READY with a warning message, for this, cmd_ics_go() added (v0.4.5)
//   2020 Oct 12: DEST_RA & CMD_NUM included in the CHK_POSERR log, force_idle(criterion for ERROR: Acquisition is not fully completed) 
//                rollback 60(3s) --> 40(2s) since "EXPSTATUS=IDLE" received Typ. 0.4~0.5s later after 4th "Acquisition Complete." received,
//                force_fitssaved(criterion for WARNING: Writing FITS data is not fully completed) modified 400(18s) --> 560(25s), 
//                tcs_tolerance_pointing_corr = tcs_tolerance_pointing + OSC_ADJ_TOL_POINTING if posc->count_pointing > OSC_CHKCNT_POINTING*3/4, 
//                debugging for "WARNING: Writing FITS data is not fully completed !! .." message error during the "go n" process 
//                (sys.count_fitssaving = 0 for "STATUS: ... EXPSTATUS=IDLE" message), debugging for the unit of "WARNING: Near HA limit, clearance = 0.0 min"
//                modification for the near limit warning with flag_tcswarning_nearlimit: output when the TCS data update(1 sec interval) 
//                --> output once when the telstatus changed from CHECKING to TRACKING/HOLDING/OSCILLATE, but always flag on during telescope moving 
//                osc.expnum_skip applied to osc.lineidx and reset for updating the line index in the case of the some next lines are skipped (v0.4.5)
//   2020 Oct 14: debugging for condition to add up OSC_ADJ_TOL_POINTING ( dec>70 --> fabs(dec>70) ) (v0.4.6)
//                modification of tcs_tolerance_pointing_corr setting with increasing it according to count_pointing) increasing (v0.4.7)
//                'EXP' commands are ignored when CamStatus is NOT CAMSTATUS_READ/_READY with a warning message, for this, cmd_ics_exp() added,
//                debugging for tcs_tolerance_pointing_corr setting for the current exposure (v0.4.8)
//   2020 Nov 26: 'oline'/'oobject'/'olabel' commands improved to calculate HA & Alt and display, 
//                modified to include TCS connection error override (v0.4.9)
//   2020 Nov 27: 'oscript'/'oobject'/'olabel' commands functionally improved to adjust object & label field length for display/logging (v0.5.0)
//   2020 Dec 01: 'oline'/'oobject'/'olabel' commands functionally improved to input UT string and to calculate Alt/HA at input UT,
//                modified to include ISIS connection error override (v0.5.0)
//   2021 Mar 06: 'ecmd' command added for external command line excution, 'dlamp' command added for domeflat lamp on/off control,
//                'mcfan' command added for mirror cell fan on/off control, help message updated & modified, 
//                'delay' command is changed to 'sleep', modification of the warning blinking off code (v0.5.1)
//   2021 Mar 09: 'dtchk' command added to move FITS data from /data to /data/YYYYDDMM and check for data transfer from ICS to DTS, 
//                'odelay'(='delay') command implementation for script observation, which doesn't block the other process, 'noop' added (v0.5.2)
//   2021 Mar 10: cmd_oscscript() modified for debugging the "incorrect command data number in the osc data" error (v0.5.3)
//   2021 Mar 11: debugging one-more-exposure error when ostop commanded (v0.5.4-v0.5.5)
//   2021 Mar 15: rollback to v0.5.3 for flag_paused/flag_running/flag_expcomplete settings to debug tel-mov-during-exp error (v0.5.6)
//                flag_running check before commanding 'Go' to debug one-more-exposure error after ostop (v0.5.7)
//   2021 Mar 16: in ProcOSC(), "posc->flag_exposing is  = 1" setting is moved from 'Go' command's response check routine 
//                with OSC_CHKBIT_STARTEXP flag check, to 'Go' commanding routine with OSC_CMDBIT_STARTEXP flag check, 
//                to debug filter-change-for-next error, which occurs right after 'Go' commanding (v0.5.8)
//                "psys->camstatus = CAMSTATUS_CHECK" flag setting at the 'Go' commanding routine with OSC_CMDBIT_STARTEXP flag check 
//                rollback for posc->flag_exposing settings since using "psys->camstatus = CAMSTATUS_CHECK" flag setting (v0.5.9)
//   2021 Mar 17: flag_responseok = 1 removed at case: CMD_NOOP in OscCommand() to debug the serial command before responseok, 
//                and flag_responseok = 1 added in cmd_noop() for commanding in the script (v0.6.0)
//   2021 Mar 19: OSC message type definition, 'OSC' message type is added for commanding in script, 
//                execution of some command process func some cmd_xxx() for OSC as well as EXEC (v0.6.0)
//   2021 Mar 26: another option added for oline to print first few lines, and cmd_oscline() are modified overall 
//                with using new GetOscLine() sub-routine function (v0.6.2)
//   2021 Apr 01: agent quit after dtchk (v0.6.3)
//   2021 Apr 08: ProjID added for oscscript/oscline/osclabel/oscobject output, ProjID set in ProcOsc() during exp line config,
//                ProjID response check at 'if( osc.flag_responsecheck ) ..' in SocketCommands(), acceptance of space at the beginning of 
//                configuration lines in runtime configuration file(.ini) (v0.6.4)
//   2021 Apr 08: cmd retry routine added, removal of spaces at the end of args in cmd_tc() for 'ERROR: incorrect filter name/initial' dubugging, 
//                response check added for TSTAT/TCSSTAT/TCSSTATUS/ASTAT/AUXSTAT/AUXSTATUS commands (v0.6.5)
//   2021 Jun 21: ics_datasource, tcs_latitude, tcs_longitude, and tcs_elevation initialization in InitSysConfig(),
//                datasource setting at the beginning of script observation(oscstart/oscresume) with OscSetDatasource() (v0.6.6)
//   2021 Jul 22: TCS_TOLERANCE_POINTING increasing routine is improved for near-pole target. (v0.6.7)
//   2022 Jul 12: web relay control codes, and implementation of dlamp/dlight/mcfan/tpad/drot commands (v0.6.8)
//                setup VELRA/VELDEC and control tpad relay functions, implementation NST during script obs (v0.6.9)
//   2022 Jul 14: getut command with sec since epoch, improovment of UT string input, Cx COPT applied temporary, 
//                debugging for reply message buffer, debugging NST setup codes in ProcOsc() (v0.7.0-v0.7.3)
//                override arg 'on'/'off' added, FILNAME input message handling modified, cmd_help() updated (v0.7.4)
//   2022 Jul 15: TCS paddle off(disable NST) right before OscCommand("opause"); or OSC_FINISH, 
//                last commanded VELRA/VELDEC applied to the telposition & tolerence using timestamps in case of NST both in the script obs 
//                and in checking the tracking stability in UpdateTcsData(), for calculating the time interval, timestamp is used  (v0.7.5)
//                debugging for cmd_velra/cmd_verdec reset problem, telstatus/tracking check modified, nston/nstoff commands added (v0.7.6)
//                count_tmrwaiting applied in tmr commanding proc in ProcOsc() to prevent frequently commanding in case normal and nst (v0.7.7)
//   2022 Jul 18: drot command func implemented using redirection to a file as output channel of external curl GET command (v0.7.8)
//                function getting actual status of all the drot commands(v0.7.8), ovron & ovroff added (v0.7.9)
//   2022 Aug 10: UTOBS/UTTOL func of trial version implemented, UTOBS/UTTOL applied to current exposure in ProcOsc(), 
//                Exposure starting time logging on the script observation log (v0.7.9)
//   2022 Aug 12: UTOBS func debugged/modified for current exposure (UTOBS func is not yet applied to the preparation routine for next exp),
//                OscCommand "tpad on/off off on/off off" replaced with "nston/nstoff", and debugging for index of printing msg in ProcOsc(), 
//                the default obs script dir with DEFAULT_OSCDIR "/home/dts/osc/" when no input abs. path which is not starting 
//                with '/', '.', or '~' in cmd_oscscript() (v0.8.0)
//   2022 Aug 24: debugging for " KEY IN : .." message logging to the event log, debugging for setting default obs script dir, 
//                debugging for logging scrobs in case script running stopped,  (v0.8.2)
//   2022 Aug 26: modification to avoid possibility not to set for following exposure after line skips at CURRENT_LINE_SKIP: in ProcOsc()
//                found cause to make 20s delay on averaged (DATE-OBS - UT_OBS), UT_OBS interval make it even though no error on UT_OBS code..
//                added a note that optimized UT_TOL = UT_OBS_INT/2, debugging additional shot msg repeat error (v0.8.2)
//   2022 Aug 29: OscCommand("opause") removed in case NST-off control failed for non-stop observation even if the relay failed (v0.8.6)
//                UTOBS/UTTOL func upgrade: check for UT_OBS including Telescope slew and settling down time (v0.8.7)
//   2022 Oct 13: getjd/getlst/getalt implementation with calculation.c using NOVAS C codes (v0.8.8/v0.8.9)
//                ha & altitude calculated with calculation.c in the GetOscLine() (v0.8.8/v0.8.9)
//   2023 Feb 22: Modify CHK_POSERR string - moved after NST calculation, NST correction values applied, and tolerance value appended,
//                Increase allowance for RA/Dec axes unstability from 2 to 3 (TelStatus=OSCILLATE after three 'TelStatus=CHECKING'),
//                Modify the message "Telescope failed to point .." to report which axis fails to point or is oscillating,
//                Append REPORT_TPFAILED string into debugging log, Add Warning and Logging in case oscillation during exposure (v0.9.0)
//   2023 Mar 04: Change allowance_unstable to tcs_allowance_unstable in sysconfig, initialized with DEFAULT_TCS_ALLOWANCE_UNSTABLE and imported from RC (v0.9.1)
//   2023 Nov 06: Replace _msgout() with _dbgmsgout() when loading an OSC (v0.9.2)
//   2024 Jun 18: Complement dome status update(sys.domerot/sys.domeshut update), 
//                Append DomeRot/DomeShut to SYS.STATUS string in cmd_sysstatus(),
//                Add hiredis lib, Add command/func 'redisget'/'redisset' (v0.9.3)
//   2024 Jun 20: Complement dome status update for system status (sys.domerot/sys.domeshut) with UpdateDomeStatus(), 
//                Waiting for dome rotation and shutter moving completed before starting exposure during script observation 
//                with checking for psys->domerot and psys->domeshut before start exposure in ProcOsc()
//                *NOTE: if dome status update is not available, the status is set to IDLE and the exposure starts regardless of dome status.
//                Modify cmd_drot() for updating dome rotation status from Relay, Modify cmd_redisget() for updating dome rotation status from Redis, 
//                Code refactoring for Dome status update (Redis/Relay/Aux/Sys), Code refactoring in command.c and command.h,
//                Add 'olast' command and cmd_osclast() to query last completed script line number (v0.9.4)
//   2024 Jun 21: Add command 'domestat' and cmd_domestatus() to update and return, or only return dome status on Redis/Relay/AuxStatus, 
//                Disable old codes in cmd_drot() due to Error 24, it uses external Curl command to access Relay and frequent file In/Out to get state stream (v0.9.5)
//   2024 Jun 25: Modify cmd_drot() to get dome rotation status from Web relay with applying easy Curl library, 
//                Modify message output about waiting for dome moving to complete during script observation (v0.9.6)
//   2024 Jun 26: Add anomaly handling for waiting time during waiting for dome moving to complete in ProcOsc() (v0.9.8)
//   2024 Jun 27: Change conditions for determining dome shutter status in UpdateDomeStatus() 
//                so that we can Go when the dome shutter position is near telescope position, 
//                Add function to disable the Dome rotation status check when the telescope is near the zenith (Alt>ConfigRotChkMaxAlt),
//                Change conditions for determining dome rotation status from Relay (in case Unknown, set IDLE) (v0.9.9)
//   2024 Jun 29: Add setting expinfo.nStatus/strExpStart with CamStatus setting, Add 'expinfo' command/function to return ExpInfo string,
//                Remove labels(ALT/HA/EXPSTART) in obs.scrobs log, Add functions for expinfo initialization and string edition (v1.0.0)
//   2024 Jul 01: Add ExpNum query to ICS and ExpNum(strNextNum/strCurNum) update (v1.0.1)
//   2024 Jul 05: Add a func to edit and overwrite obs.status(SYS.STATUS/OSC.STATUS/EXP.INFO/OBS.Script) on /data/Logs/ObsStatus.txt (v1.0.3-v1.0.4)
//                *NOTE: For details on the observation status file format, refer to Ref.ObsStatus.txt in OBSAgent directory.
//   2024 Jul 11: Debug missing set expinfo.dStartTime for ExpProg status (v1.0.6), Debug ExpNum error at SSO (v1.0.7-v1.0.8)
//   2024 Jul 12: Add a flag about oscillating during exposure into exposure information, set to "YES" if oscillating more than 5% of exposure time (v1.0.9)
//   2024 Jul 15: Add flag labels '+DROTCOMP' or '+DROTSHUT' to RemainingProc status in OscStatus string line, during waiting dome rotation or dome shutter complete,
//                Append secz, az, expnum, and oscillation info columms into scrobs log, Modify secz, alt, az, ha to status at the starting of exposure (v1.1.0)
//   2024 Jul 16: Add set expinfo.nStatus = EXPSTATUS_WAITING in Line finishing routine in ProcOsc() during script observation (v1.1.1)
//                Sdd set expinfo.nStatus = EXPSTATUS_STANDBY in Wrote message handing routine when no script obs. mode (v1.1.2)
//   2024 Jul 18: Debug momentary unmatch of ExpNum and ExpStatus, Debug missing ExpNum/ExpStart update in dark/bias mode (v1.1.3)
//   2026 Jun 02: Add to wait for shutter reloading to complete in preparing next Exp before slewing telescope (v1.2.0)
//
//
//   Reserved items: 
//    - redis timeout setting --> add to runtime config 
//    - ConfigRotChkMaxAlt --> add to runtime config 
//    - improve UT and strUT handling
//    - UTOBS/UTTOL func upgrade
//      -- DeltaSec -= MAX(TelMovingSec,DomMovingSec)
//      -- Applying to preparation for next exposure
//         * we should check posc->expnum_skip setting (e.g. posc->expnum_skip++; at the end of NEXT_LINE_SKIP: )
//    - Status messages upgrade: including status of relays, status of NST, VEL_RA/VEL_DEC, and etc.
//    - Getting actual status of all the web relays dlamp/dlight/mcfan/tpad commands with ezCurl Lib.
//    - Guide CCD acquisition function & GUIDECCD ON/OFF command implementation
//
//------------------------------------------------------------------------------

#include "obstool.h"         // OBS Agent application header file
#include "commands.h"        // Command tree header file

extern isisclient_t client;  // global client runtime config table
extern obsagent_t agent;     // TCS Agent data (this process)
extern obssystem_t sys;      // System configuration data
extern COSC osc;
extern CEXP expinfo;

int KeyCmdFlag = 0;          // to disable readline prompt reset in _msgout()/_vmsgout()
int SocketCmdFlag = 0;       // for important message display
char InputCMD[STRLEN_CMD];  // command to send to ISIS node TC/ICS
char SourceID[STRLEN_ISISNODE];
char SysStatus[STRLEN_REP];

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

  // warning flag off with any key input

  if( agent.flag_warning ) {  // v0.3.5
    agent.flag_warning = 0;
    agent.count_warning = 0;
    strcpy(cmsg,"STATUS: warning blinking off\n");
    _msgout(cmsg);
    WHITEBG; BEEP; usleep(300000); BEEP; 
    printf("\r");
  } //// debugged at v0.3.6

  {
    WHITEBG;
    agent.flag_warning = 0;
    agent.count_warning = 0;
  }
  //// added at v0.5.1

  // If line is NULL, we have nothing to do, return

  if(line==NULL) return;

  // Similarly, if line is blank, return

  if(strlen(line)==0) {
    free(line);
    return;
  }

  KeyCmdFlag = 1;

  memset(SourceID, 0, sizeof(SourceID));
  strcpy(SourceID, "KEYIN");

  if(strlen(line)>STRLEN_MAXKEYIN) {  // TCSAgent v1.6.6.3
    REDTEXT;
    sprintf(cmsg, "ERROR: Too long input message\n");_msgout(cmsg);
    free(line);
    KeyCmdFlag = 0;
    return;
  }

  // Allocate memory for the message buffer and clear it

  message = (char *)malloc(strlen_message*sizeof(char));
  memset(message,0,strlen_message*sizeof(char));

  // Copy the keyboard input line into the message buffer 
  // and do any history expansion (!, !!, etc.) if required

  result = history_expand(line,&expansion);  // if(line[0]..) removed at TCSAgent v1.6.6.4
  if(result) {
   sprintf(cmsg, "%s\n",expansion);_msgout(cmsg);  // TCSAgent v1.6.0
  }
  if(result < 0 || result==2) {
    free(expansion);
    free(line);  // TCSAgent v1.6.6.3
    KeyCmdFlag = 0;
    return;
  }

  sprintf(message,"%s",expansion);
  free(expansion);

  // Add history if input message is not repetition..

  if( strcasecmp (PrevMessage, message) ) {  // TCSAgent v1.6.6.2 & v1.6.6.4
    add_history(message);
    strcpy(PrevMessage, message);
  }

  // We're all done with the original string from readline(), free it

  free(line);

  // Remove any \n terminator on the message string

  if(message[strlen(message)-1]=='\n') message[strlen(message)-1]='\0';

  // Keyboard input string output on Console and Logfile

  //  sprintf(cmsg, " KEY IN : %s\n",message);_dbgmsgout(cmsg);
  //  //if(client.doLogging) _eventlog(cmsg);  // v0.2.4
  //  _eventlog(cmsg);  // doLogging flag check removed at v0.8.0
  //  ////if( client.doLogging && agent.isLogVerbose ) _eventlog(cmsg);  
  //  //// --> use this if wanted to log only in verbose logging mode instead of above code.

  sprintf(cmsg, " KEY IN : %s\n",message);_eventlog(cmsg);_dbgmsgout(cmsg);   // v0.8.2


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

  if(strncasecmp(cmd,">",1)==0) { // 

    if( client.useISIS && agent.isISISconnected ) {
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

      msg[strlen(msg)-1]='\0';
      sprintf(cmsg, "ISIS OUT: %s\n",msg);_dbgmsgout(cmsg);

    }
    else {
      REDTEXT;
      sprintf(cmsg, "ERROR: No ISIS client mode >> ICIMACS command unavailable\n");_msgout(cmsg);
    }
    
  }// end of if(strncasecmp(cmd,">",1)==0)

  // All other commands use the cmd_xxx() action calls

  else { //

    // Traverse the command table, matches are case-insensitive, but
    // must be exact word matches (no abbreviations or aliases)
    
    nfound = 0;
    for (i=0; i<NumCommands; i++) {
      if(strcasecmp(cmdtab[i].cmd,cmd)==0) { 
        nfound++;
        icmd=i;
        break;
      }
    }
    if(nfound == 0) {
      if(strlen(cmd)>0) {
        REDTEXT;
        sprintf(cmsg, "ERROR: Unknown command - '%s'\n",cmd);_msgout(cmsg);
      }
    }
    else {

      // all console keyboard are treated as EXEC: type messages

      memset(InputCMD, 0, sizeof(InputCMD));
      strcpy(InputCMD, cmd);

      switch (cmdtab[icmd].action(args,EXEC,reply)) {
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

  }// end of else {

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

  char *pstr;

  // Some simple initializations

  memset(msg,0,sizeof(msg));
  memset(cmd,0,sizeof(cmd));
  memset(args,0,sizeof(args));
  memset(reply,0,sizeof(reply));

  // Inspect ID & Type string length for using SplitMessage(), TCSAgent v1.6.6.4

  memset(msgbody,0,sizeof(msgbody));
  sscanf(buf, "%s", msgbody);
  if( strlen(msgbody) >= STRLEN_ISISADDR ) return;

  memset(msgbody,0,sizeof(msgbody));
  sscanf(buf, "%*s %s", msgbody);
  if( strlen(msgbody) >= STRLEN_ISISTYPE ) return;

  // Split the ISIS format message into components

  rtn = SplitMessage(buf,srcID,destID,&msgtype,msgbody);

  // check destination ID

  if( strcasecmp(destID,client.ID) && strcasecmp(destID,"AL") ) 
    return;  // if not mine, ignore it.

  // check source ID & message format in case of ISISclint mode

  //if(client.useISIS) { 
  //  if( strcasecmp(client.isisID,srcID) || client.remPort!=client.isisPort ) 
  //    return;  // if not message from IS, ignore it.
  // changed to below at TCSAgent v1.4.3

  if(client.useISIS && client.remPort==client.isisPort ) {

    MsgFromISIS = 1;  // TCSAgent v1.4.3

    if(rtn<0) {

      //if(client.isVerbose) {
      //  printf("\rISIS IN : Malformed message\n");
      //  rl_refresh_line(0,0);
      //}
      //// replaced with below code at TCSAgent v1.6.0

      sprintf(cmsg, "ISIS IN : Malformed message\n");_dbgmsgout(cmsg);

      return;
    }

    sprintf(cmsg, "ISIS IN : %s\n",buf);_dbgmsgout(cmsg);

  }

  // check only message format in case of Standalone mode

  else { 

    MsgFromISIS = 0;  // TCSAgent v1.4.3

    if(rtn<0) {
      sprintf(cmsg, "REMC IN : Malformed message from %s\n", srcID);_dbgmsgout(cmsg);
      return;
    }

    sprintf(cmsg, "REMC IN : %s\n",buf);_dbgmsgout(cmsg);

  }

  //
  // parser the socket message string
  //

  msgbody[STRLEN_ISISMSG-1] = '\0';  // TCSAgent v1.6.0
  msgbody[STRLEN_ISISMSG-2] = '\n';  // TCSAgent v1.6.0

  if(strlen(msgbody)>STRLEN_MAXSOCIN) {  // TCSAgent v1.6.6.4
    sprintf(msg,"%s>%s ERROR: Message is too long! (length=%d)\n\r",
                client.ID, srcID, strlen(msgbody) );
    msgtype = NOOP;
  }

  //printf("\nDEBUG: input message length = %d\n\n", strlen(msgbody));
  //sprintf(msg, "DEBUG: input message length = %d\n\r", strlen(msgbody));
  //goto SENDMSG;

  sscanf(msgbody,"%s %[^\n]",cmd,args);  // split into command + args

  //
  // if the message is TSTAT/ASTAT and it has been requested, process it here
  // we need to handle this message exceptively to avoid unnecessary DONE message display.
  //

  /*
  if( sys.flag_tcsdata_requested && strcasecmp(cmd,"UP")==0 && strlen(args)<STRLEN_TSTAT_MAX ) {

    rtn = UpdateTcsData(&sys, args, reply);

    if(rtn<0) {
      REDTEXT;
      sprintf(cmsg, "ERROR: %s",reply);_vmsgout(cmsg);
    }

    msgtype = NOOP;

  }

  else if( sys.flag_auxdata_requested && strcasecmp(cmd,"UP")==0 ) {

    rtn = UpdateAuxData(&sys, args, reply);

    if(rtn<0) {
      REDTEXT;
      sprintf(cmsg, "ERROR: %s",reply);_vmsgout(cmsg);
    }

     msgtype = NOOP;

  }
  */
  // --> modified as follows.. at v0.2.4 
  //     for debugging unexpected TCS/AUX data updating error due to not enough arguments number

  if( strncmp(msgbody,"UP 1 ", 5)==0 || strncmp(msgbody,"UP 0 ", 5)==0 ) {  // v0.2.4 

    if( sys.flag_tcsdata_requested && strlen(args)<STRLEN_TSTAT_MAX ) {
        rtn = UpdateTcsData(&sys, args, reply);
        if(rtn<0) { REDTEXT;sprintf(cmsg, "ERROR: %s\n",reply);_vmsgout(cmsg); }
        else      { msgtype = NOOP;                                            }
    }

    else if ( sys.flag_auxdata_requested ) {
        rtn = UpdateAuxData(&sys, args, reply);
        if(rtn<0) { REDTEXT;sprintf(cmsg, "ERROR: %s\n",reply);_vmsgout(cmsg); }
        else      { msgtype = NOOP;                                            }
    }

  }

  //// For reference, 
  ////TSTAT STRING1:  DONE: UP 1 2017-12-25T19:48:31.913 UTC 2017-12-25T19:48:31.861 21:22:28.03 -30:04:51.5 2000.000 +00:00:00 21:23:20  1.00 90.0   +0.0  0  0  0 E
  ////ASTAT STRING1:  DONE: UP 1 2017-12-25T19:48:31.506 UTC KMTC 2017-12-25T19:48:31.475  FS: STANDBY STANDBY 3 V STANDBY CLOSED  FA: STANDBY -1.260 -110.0 +174.9  0 0 0  -0.722 -0.788 -2.270  DS: STANDBY CLOSED CLOSED ACTIVE DISABLED 16.8 90.0  MC: STANDBY 0  CH: ERROR OFF 8.0 0.1  EN: STANDBY ON 24.4 23.9 19.1 26.6 16.8 17.9 0.0
  ////ASTAT STRING2:  DONE: UP 1 2017-12-25T19:58:08.173 UTC KMTC 2017-12-25T19:58:08.023  FS: NC NC -1 UNKNOWN NC UNKNOWN  FA: NC +0.000 +0.0 +0.0  -1 -1 -1  +0.000 +0.000 +0.000  DS: NC UNKNOWN UNKNOWN UNKNOWN DISABLED 0.0 0.0  MC: NC 0  CH: NC OFF 0.0 0.0  EN: NC OFF 0.0 0.0 0.0 0.0 0.0 0.0 0.0

  //
  // if the message is FILNAME and it has been requested, process it here
  // we need to handle this message exceptively to avoid unnecessary DONE message display.
  //

  ///////////////////////////////////////////////////////////////////////////////////////  
  //  if( strcasecmp(cmd,"FILNAME")==0 && sys.flag_filterlabel_requested ) {
  //
  //    rtn = UpdateFilterLabels(&sys, args, reply);
  //
  //    if(rtn<0) { 
  //      REDTEXT;
  //      sprintf(cmsg, "ERROR: %s\n",reply);_vmsgout(cmsg);
  //    }
  //
  //    msgtype = NOOP;
  //
  //  }
  //////////////////////////////////////////////////////////////// old codes until v0.7.3


  if( strcasecmp(cmd,"FILNAME")==0 ) {

    if( sys.flag_filterlabel_requested ) {

      rtn = UpdateFilterLabels(&sys, args, reply);

      if(rtn<0) { 
        REDTEXT;
        sprintf(cmsg, "ERROR: %s\n",reply);_vmsgout(cmsg);
      }

      msgtype = NOOP;

    }

    else if ( sys.flag_override_auxconnection ) {  // v0.7.4

      msgtype = NOOP;

    }

  }

  //
  // Immediate action depends on the type of message received as
  // recorded by the msgtype code.
  //

  switch(msgtype) {

  case STATUS:  // we've been sent a status message, echo to console
    sprintf(cmsg, "%s\n",buf);_msgout(cmsg);

    //
    // update camera status
    //

    if( !strcasecmp(srcID,"ICS") 
        || !( strcasecmp(srcID,"K.IC")&&strcasecmp(srcID,"M.IC")&&strcasecmp(srcID,"T.IC")&&strcasecmp(srcID,"N.IC") )
        || !( strcasecmp(srcID,"K.CB")&&strcasecmp(srcID,"M.CB")&&strcasecmp(srcID,"T.CB")&&strcasecmp(srcID,"N.CB") ) ) {
        // scrID check is added to ignore msg from ICG/G.IC/G.CB at v0.3.2
        // scrID check was added for ID that sends the status message in each if phrase at v0.3.1 
        // but scrID check is moved here to make this scrID check insensitive to the change of IC at v0.3.2

      if( strstr(buf,"EXPSTATUS=IDLE")!=NULL ) {  // this msg is from ICG as well
        sys.camstatus = CAMSTATUS_IDLE_3;         // msg type of 'EXPSTATUS=IDLE' is STATUS in the case of 'go n' command, added here at v0.3.0
        expinfo.nStatus = EXPSTATUS_FINISH;   // v1.0.0
        sys.count_fitssaving = 0;   // v0.4.5
        sys.count_ready = 0;   // v0.4.5
        //if( SendISISMsg("ExpNum",REQ,"ICS",reply)<0 ) { strcpy(cmsg,"Warning: ExpNum commanding failure ! \n");CYATEXT;_msgout(cmsg); }   // v1.0.1 --> moved to {sys.camstatus = CAMSTATUS_READ_2; } that is less busy..
      } 
      if( strstr(buf,"Wrote")!=NULL ) {  // this msg is from G.CB as well // FITS save status monitoring, moved here at v0.2.7
        if( ++sys.count_wrote >= 4 ) {
          sys.status_fitssaved = 1;
          osc.lastidx_fitssaved = osc.lastidx_expcompleted;   // for 'olast' command, v0.9.4
          if(expinfo.nStatus>=EXPSTATUS_FINISH) expinfo.nStatus = EXPSTATUS_STANDBY;  // v1.1.2, set STANDBY when no script obs. mode
          pstr = strstr(buf,"KMTN");
          if(pstr==NULL) {
            strcpy(expinfo.strFitsNum, "00000000.000000");
            strcpy(expinfo.strFitsOsc, "CHECK");   // v1.0.9
          }
          else {
            strncpy(expinfo.strFitsNum, pstr+6, 15);
            strcpy(expinfo.strFitsOsc, expinfo.flagOscPre?"YES":"NO");   // v1.0.9
          }   // add FitsNum import in v1.0.1
        }
      }
      else if( strstr(buf,"Acquisition Complete.")!=NULL ) {  // this msg is from G.IC as well
        sys.camstatus = CAMSTATUS_IDLE_1;
        expinfo.nStatus = EXPSTATUS_FINISH;   // v1.0.0
        sys.count_acqcomp++;
        sys.count_idle = 0;  // force_idle = 40 --> 1.8s later after 1st "Acquisition Complete."
        if( sys.count_acqcomp >= 4 ) {
          sys.camstatus = CAMSTATUS_IDLE_2;
          sys.count_idle = sys.force_idle/2;  // force_idle/2 = 40/2 = 20 --> 0.9s later after 4th "Acquisition Complete."
        }
      }
      else if( strstr(buf,"PCTREAD=")!=NULL ) {  // this msg is only from K.IC, or from M.IC/T.IC/N.IC in case the master is not K CBB (no from ICG/G.IC)
        if( sys.camstatus==CAMSTATUS_READ_1 ) { 
          if( SendISISMsg("ExpNum",REQ,"ICS",reply)<0 ) { 
            strcpy(cmsg,"Warning: ExpNum commanding failure ! \n");
            CYATEXT;_msgout(cmsg); 
          }
        } //// v1.0.1
             if( sys.camstatus==CAMSTATUS_READ_1 ) { sys.camstatus = CAMSTATUS_READ_2; }
        else if( sys.camstatus==CAMSTATUS_READ_2 ) { sys.camstatus = CAMSTATUS_READ_3; }
        else if( sys.camstatus!=CAMSTATUS_READ_3 ) { sys.camstatus = CAMSTATUS_READ_1; }
        expinfo.nStatus = EXPSTATUS_READOUT;   // v1.0.0
        sys.count_acqcomp = 0;
        sys.count_wrote = 0;
        sys.status_fitssaved = 0;   // v0.2.5
      }
      else if( strstr(buf,"EXPSTATUS=READOUT")!=NULL ) {  // this msg is from G.IC as well
        sys.camstatus = CAMSTATUS_READ_1;
        expinfo.nStatus = EXPSTATUS_READOUT;   // v1.0.0
        sys.count_wrote = 0;
        sys.status_fitssaved = 0;
      }
      else if( strstr(buf,"Shutter=Closed")!=NULL ) {  // this msg is only from K.IC, or from M.IC/T.IC/N.IC in case the master is not K CBB (no from ICG/G.IC)
        sys.camstatus = CAMSTATUS_CLOSING;
        expinfo.nStatus = EXPSTATUS_EXPOSURE;   // v1.0.0
        sys.flag_expcount = 0;    // v0.3.3
        sys.exp_remaining = 0.0;
      }
      else if( strstr(buf,"Remaining=")!=NULL ) {  // Maybe this msg is only from K.IC, or from M.IC/T.IC/N.IC in case the master is not K CBB (no from ICG/G.IC)
        sys.camstatus = CAMSTATUS_INT_3;
        expinfo.nStatus = EXPSTATUS_EXPOSURE;   // v1.0.0
      }
      else if( strstr(buf,"Shutter=Open")!=NULL ) {  // this msg is only from K.IC, or from M.IC/T.IC/N.IC in case the master is not K CBB (no from ICG/G.IC)
        sys.camstatus = CAMSTATUS_INT_2;
        sys.flag_expcount = 1;    // v0.3.3
        if(!expinfo.flagStart) { // skip if it has not been set by missing message EXPSTATUS=INTEGRATING", set here, v1.1.3
          expinfo.nStatus = EXPSTATUS_EXPOSURE;   // v1.0.0
          //strcpy(osc.expstart, GetUTCDateTime(NULL));   // added for logging at v0.7.9
          strcpy(expinfo.strExpStart, GetUTCDateTime(NULL));   // modified at v1.0.0
          strcpy(expinfo.strCurNum  , expinfo.strNextNum  );   // v1.0.1
          //strcpy(expinfo.strNextNum , "00000000.000000"   );  <-- functionally unnecessary, removed in v1.1.3
          //sys.exp_starttime = SysTimestamp();  // v0.3.3
          sys.exp_starttime = expinfo.dStartTime = SysTimestamp();    // v1.0.6
        } 
        sys.flag_tcswarning_oscinexp = 1;   // v1.0.9, added just in case (Probably not really necessary)
        expinfo.flagOscInExp = FALSE;   // v1.0.9, added just in case (Probably not really necessary)
        expinfo.cntOscInExp = 0;   // v1.0.9, added just in case (Probably not really necessary)
      }
      else if( strstr(buf,"EXPSTATUS=INTEGRATING")!=NULL ) {  // this msg is from G.IC as well
        sys.camstatus = CAMSTATUS_INT_1;
        expinfo.nStatus = EXPSTATUS_EXPOSURE;   // v1.0.0
        strcpy(expinfo.strExpStart, GetUTCDateTime(NULL));        //// added for debugging to 
        strcpy(expinfo.strCurNum  , expinfo.strNextNum  );        //// match ExpStatus and ExpNum, 
        sys.exp_starttime = expinfo.dStartTime = SysTimestamp();  //// and for dark/bias as well, 
        expinfo.flagStart = TRUE;                                 //// in v1.1.3
        sys.flag_tcswarning_oscinexp = 1;   // v0.9.0
        expinfo.flagOscInExp = FALSE;   // v1.0.9
        expinfo.cntOscInExp = 0;   // v1.0.9
      }
      else if( strstr(buf,"EXPSTATUS=ERASE")!=NULL ) {  // this msg is from G.IC as well
        sys.camstatus = CAMSTATUS_PREP_E;
        expinfo.nStatus = EXPSTATUS_FLUSH;   // v1.0.0
      }
      else if( strstr(buf,"EXPSTATUS=INITIALIZING")!=NULL ) {  // this msg is from ICG as well
        sys.camstatus = CAMSTATUS_PREP_I;
        expinfo.nStatus = EXPSTATUS_FLUSH;   // v1.0.0
        //strcpy(expinfo.strCurNum, expinfo.strNextNum);   // v1.0.1  --> moved to "Shutter=Open"
        //strcpy(expinfo.strNextNum, "00000000.000000");
      }
      // FITS save status monitoring
      //else if( strstr(buf,"Wrote")!=NULL ) {
      //  if( ++sys.count_wrote >= 4 ) sys.status_fitssaved = 1;
      //}
      // --> moved to first if phrase filter at v0.2.7 to debug "Wrote" counting error due to appended message "EXPSTATUS=.."

      // IC crash error handling..
      //  else if( strstr(buf,"Failed to initialize one or more ICs")!=NULL || 
      //           strstr(buf,"Failed to Start acquisition on one or more ICs")!=NULL ) {
      //    sys.flag_icscheck = 1;  // set to 0 after checking by observer
      //    MAGTEXT;sprintf(cmsg, "WARNING: some IC might be crashed, need to check it !!\n");_msgout(cmsg);
      //    // .. osc proc pause needed ?
      //  }
      // --> moved to ERROR: message type handling routine at v0.2.5

      //if( sys.camstatus!=CAMSTATUS_IDLE_3 ) sys.status_fitssaved = 0;
      // --> moved into READ_1 ~ REAE_3 status above at v0.2.5

    }// end of if( !strcasecmp(srcID,"ICS")..

    if( osc.flag_responsecheck && strcasecmp(osc.reschkcmd,"GO")==0 && 
        sys.camstatus>=CAMSTATUS_PREP_I && sys.camstatus<=CAMSTATUS_INT_3 ) {
      osc.flag_responseok = 1;
      //memset(buf, NULL, OSC_MAXCMDLEN);  // buf is not used anymore in this func(), but not necessary..
    }

    break;
	  
  case DONE:    // command completion message (?), echo to console.
    sprintf(cmsg, "%s\n",buf);_msgout(cmsg);

    //
    // Message check for script observation running
    //

    //
    // DONE: messages from ICS/AUX/TC for ///////////////////////////////////////
    //
    // DONE: OBJECT  ImageType=OBJECT ObjectName='BLG41' EXP=60
    // DONE: FLAT  ImageType=FLAT ObjectName='flat' EXP=60
    // DONE: DARK  ImageType=DARK ObjectName='dark' EXP=20
    // DONE: BIAS  ImageType=BIAS ObjectName='bias' EXP=0
    // DONE: EXP  ExpTime=90 seconds.
    // DONE: PROJID  ProjID=ALL
    // DONE: OBSERVER  Observer=(choi)
    // DONE: DATASOURCE   DataSource=CT_CORRECTION (>k.ic/>m.ic/>t.ic/>n.ic)
    // DONE: LEDFLASH  LEDFlashTime=1 EXPSTATUS=READOUT
    // DONE: DMAWAIT  DMAWaitTime=500 (>k.ic)
    // DONE: FILENAME  Filename=ICS.20171228T013347.058164
    // DONE: FILENAME  Filename=KMTNk.20171228.058164 (>k.ic)
    // DONE: STATUS  Inst=ICS ExpTime=60 GuideExp=0 ImageType=OBJECT ObjectName='N7793-1' Mode=Acquiring ComTest=F EXPSTATUS=INTEGRATING
    // DONE:   EXPSTATUS=IDLE
    // DONE: ? EXPSTATUS=IDLE
    //
    // DONE: change to filter #4 (B) commanded
    // DONE: ACMD m1cover close OK
    // DONE: ACMD shutter both open OK
    // DONE: ACMD shutter both close OK
    // DONE: ACMD shutter set_async on OK
    // DONE: ACMD <args> OK
    //
    // DONE: TCMD unkill OK
    // DONE: TCMD track on OK
    // DONE: TCMD <args> OK
    // DONE: move to RA/Dec commanded
    // DONE: stow commanded
    //

    //// update cam/tel status

    if( !strcasecmp(srcID,"ICS") 
        || !( strcasecmp(srcID,"K.IC")&&strcasecmp(srcID,"M.IC")&&strcasecmp(srcID,"T.IC")&&strcasecmp(srcID,"N.IC") )
        || !( strcasecmp(srcID,"K.CB")&&strcasecmp(srcID,"M.CB")&&strcasecmp(srcID,"T.CB")&&strcasecmp(srcID,"N.CB") ) ) {
        // scrID check is added to ignore msg from ICG/G.IC/G.CB at v0.3.2

      if( strstr(buf,"EXPSTATUS=IDLE")!=NULL ) {
        sys.camstatus = CAMSTATUS_IDLE_3;
        expinfo.nStatus = EXPSTATUS_FINISH;   // v1.0.0
        sys.count_fitssaving = 0;
        sys.count_ready = 0;   // v0.4.5
        //if( SendISISMsg("ExpNum",REQ,"ICS",reply)<0 ) { strcpy(cmsg,"Warning: ExpNum commanding failure ! \n");CYATEXT;_msgout(cmsg); }   // v1.0.1 --> moved to {sys.camstatus = CAMSTATUS_READ_2; } that is less busy..
      }
      else if( ( pstr = strstr(buf,"ExpTime=") )!=NULL ) {    // DONE: EXP .. / v0.3.3.0
        //if( sscanf(pstr, "%*s%lf", &sys.exp_set) != 1 ) {  --> not working
        //  sys.exp_set = 0.0;
        //} 
        expinfo.dSetting = sys.exp_set = atof(pstr+8);
      }
      else if( ( pstr = strstr(buf,"EXP=") )!=NULL ) {    // DONE: OBJECT .. / v0.3.3.1
        expinfo.dSetting = sys.exp_set = atof(pstr+4);
      }
      else if( ( pstr = strstr(buf,"Filename=") )!=NULL ) {   // v1.0.1
        strncpy(expinfo.strNextNum, pstr+9, 15);
        strcpy(expinfo.strPreNum, expinfo.strCurNum);   // added for SSO in v1.0.8
        expinfo.flagOscPre = expinfo.flagOscInExp;   // added for SSO in v1.0.9
      }
      ////  else if( ( pstr = strstr(buf,"EXPNUM") )!=NULL ) {   
      ////  else if( ( pstr = strstr(buf,"EXPNUM  Filename=") )!=NULL ) {
      ////    strncpy(expinfo.strNextNum, pstr+17, 15);
      //////// --> These will work fine too.. anyway, I put it like above finally. (v1.0.1)

    }

    //// check response for command by script observation process

    if( osc.flag_responsecheck ) {
      if( ( strcasecmp(osc.reschkcmd,"PROJID"    )==0 && strstr(buf,"PROJID"          )!=NULL ) ||  // v0.6.4
          ( strcasecmp(osc.reschkcmd,"STANDARD"  )==0 && strstr(buf,"STANDARD"        )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"DOMEFLAT"  )==0 && strstr(buf,"DOMEFLAT"        )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"SKY"       )==0 && strstr(buf,"SKY"             )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"FLAT"      )==0 && strstr(buf,"FLAT"            )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"OBJECT"    )==0 && strstr(buf,"OBJECT"          )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"DARK"      )==0 && strstr(buf,"DARK"            )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"BIAS"      )==0 && strstr(buf,"BIAS"            )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"EXP"       )==0 && strstr(buf,"EXP"             )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"PROJID"    )==0 && strstr(buf,"PROJID"          )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"OBSERVER"  )==0 && strstr(buf,"OBSERVER"        )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"LEDFLASH"  )==0 && strstr(buf,"LEDFLASH"        )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"DATASOURCE")==0 && strstr(buf,"DATASOURCE"      )!=NULL ) ||  // >k.ic/>m.ic/>t.ic/>n.ic
          ( strcasecmp(osc.reschkcmd,"DMAWAIT"   )==0 && strstr(buf,"DMAWAIT"         )!=NULL ) ||  // >k.ic
          ( strcasecmp(osc.reschkcmd,"FILENAME"  )==0 && strstr(buf,"FILENAME"        )!=NULL ) ||  // >k.ic/>ics
          ( strcasecmp(osc.reschkcmd,"ACQSTATUS" )==0 && strstr(buf,"ACQSTATUS"       )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"STATUS"    )==0 && strstr(buf," STATUS"         )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"FTTGOTO"   )==0 && strstr(buf,"goto focus and"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"DTILT"     )==0 && strstr(buf,"adjust PFI tip"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"DFOCUS"    )==0 && strstr(buf,"adjust focus"    )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"FILTER"    )==0 && strstr(buf,"change to filter")!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"ACMD"      )==0 && strstr(buf,"ACMD "           )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"ASTAT"     )==0 && strstr(buf," UTC "           )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"AUXSTAT"   )==0 && strstr(buf,"AUXSTATUS "      )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"AUXSTATUS" )==0 && strstr(buf,"AUXSTATUS "      )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TDI"       )==0 && strstr(buf,"DECLAREINIT "    )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"STOW"      )==0 && strstr(buf,"stow commanded"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TSTOW"     )==0 && strstr(buf,"stow commanded"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TSTOP"     )==0 && strstr(buf,"stop commanded"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TGUI"      )==0 && strstr(buf,"guiding offset"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TGUIDE"    )==0 && strstr(buf,"guiding offset"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TOFF"      )==0 && strstr(buf,"offset move "    )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TOFFSET"   )==0 && strstr(buf,"offset move "    )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TME"       )==0 && strstr(buf,"move to el/az"   )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TMELAZ"    )==0 && strstr(buf,"move to el/az"   )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TMO"       )==0 && strstr(buf,"move to object"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TMOBJ"     )==0 && strstr(buf,"move to object"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TMOBJECT"  )==0 && strstr(buf,"move to object"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TMR"       )==0 && strstr(buf,"move to RA/Dec"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TMRADEC"   )==0 && strstr(buf,"move to RA/Dec"  )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TREQ"      )==0 && strstr(buf,"TREQ "           )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TCMD"      )==0 && strstr(buf,"TCMD "           )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TSTAT"     )==0 && strstr(buf," UTC "           )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TCSSTAT"   )==0 && strstr(buf,"TCSSTATUS "      )!=NULL ) ||
          ( strcasecmp(osc.reschkcmd,"TCSSTATUS" )==0 && strstr(buf,"TCSSTATUS "      )!=NULL )  ) {

        osc.flag_responseok = 1;
        //memset(buf, NULL, OSC_MAXCMDLEN);  // buf is not used anymore in this func(), but not necessary

      }
    }

    break;
	  
  case ERROR:   // error messages, echo to console, get fancy later
    REDTEXT;
    sprintf(cmsg, "%s\n",buf);_msgout(cmsg);

    // IC crash error handling..
    if( strstr(buf,"Failed to initialize one or more ICs")!=NULL || 
        strstr(buf,"Failed to Start acquisition on one or more ICs")!=NULL ) {
        sys.flag_icscheck = 1;  // set to 0 after checking by observer
        MAGTEXT;sprintf(cmsg, "WARNING: some IC might be crashed!! Please check it.\n");_msgout(cmsg);
        // .. osc proc pause needed ?  --> paused at Acquisition completion error handling routine
    }

    if( osc.flag_responsecheck ) {
      //if( osc.count_errorresponse > .. ) {
      //  ERROR and osc.flag_responsecheck = 0;
      //}
    }

    break;

  case WARNING:
    CYATEXT;
    sprintf(cmsg, "%s\n",buf);_msgout(cmsg);
    break;

  case FATAL:
    MAGTEXT;
    sprintf(cmsg, "%s\n",buf);_msgout(cmsg);
    break;
	  
  case NOOP:
    break;

  case REQ:    // implicit command requests
  case EXEC:   // and executive override commands

    /*
    msgbody[STRLEN_ISISMSG-1] = '\0';  // TCSAgent v1.6.0
    msgbody[STRLEN_ISISMSG-2] = '\n';  // TCSAgent v1.6.0

    if(strlen(msgbody)>STRLEN_MAXSOCIN) {  // TCSAgent v1.6.6.4
      sprintf(msg,"%s>%s ERROR: Message is too long! (length=%d)\n\r",
                  client.ID, srcID, strlen(msgbody) );
      break;
    }

    //printf("\nDEBUG: input message length = %d\n\n", strlen(msgbody));
    //sprintf(msg, "DEBUG: input message length = %d\n\r", strlen(msgbody));
    //goto SENDMSG;

    sscanf(msgbody,"%s %[^\n]",cmd,args);  // split into command + args
    */
    // --> moved above for FILNAME message handling

    // traverse the command table, exact case-insensitive match required

    nfound = 0;
    for (i=0; i<NumCommands; i++) {
      if(strcasecmp(cmdtab[i].cmd,cmd)==0) { 
        nfound++;
        icmd=i;
        break;
      }
    }

    if(nfound == 0) {
      sprintf(msg,"%s>%s ERROR: Unknown command - '%s'\n\r",
	          client.ID,srcID,cmd);
    }
    else {

      SocketCmdFlag = 1;

      memset(InputCMD, 0, sizeof(InputCMD));  // v0.0.5
      memset(SourceID, 0, sizeof(SourceID));
      strcpy(InputCMD, cmd  );
      strcpy(SourceID, srcID);

      switch(cmdtab[icmd].action(args,msgtype,reply)) {

      case CMD_ERR: // command generated an error
        sprintf(msg,"%s>%s ERROR: %s\n\r",client.ID,srcID,reply);
        break;

      case CMD_NOOP: // command is a no-op, debug/verbose output only
        //if(client.isVerbose)
        //  /printf("ISIS IN: %s from ISIS node %s\n",msgbody,srcID);
        // ==> there was /printf("ISIS IN : %s\n",buf); aleady above
        break;

      case CMD_OK:  // command executed OK, return reply
      default:
        sprintf(msg,"%s>%s DONE: %s\n\r",client.ID,srcID,reply);
        break;
	
      }// end of switch on cmdtab.action()
      SocketCmdFlag = 0;
    }

    // An incoming PING requires special handling - it is an exception
    // to the usual messaging syntax since PONG is sent in reply 

    if(strcasecmp(cmd,"PING") == 0) 
      //sprintf(msg,"%s>%s %s\r",client.ID,srcID,reply);
      sprintf(msg,"%s>%s %s\n\r",client.ID,srcID,reply);  // TCSAgent v1.6.2

    break;

  default:  // we don't know what we got, print for debugging purposes

    sprintf(msg,"%s>%s ERROR: Unknown message type\n\r",client.ID,srcID);

    CYATEXT;    
    if(MsgFromISIS) {sprintf(cmsg, "ISIS IN : Malformed message type\n");_dbgmsgout(cmsg);}
    else            {sprintf(cmsg, "REMC IN : Malformed message type\n");_dbgmsgout(cmsg);}

    break;

  }// end of switch(msgtype) -- default falls through with no-op

  // Do we have something to send back? 
  //
  // If we are configured as an ISIS client (client.useISIS=true), send the
  // reply back to the ISIS server for handling with SendToISISServer().
  //
  // If we are configured as standalone (client.useISIS=false), send the
  // reply back to the remote host with ReplyToRemHost().

  //SENDMSG:  // for debugging about input string length

  if(strlen(msg)>0) { // we have something to send

    //if(client.useISIS) {
    if(MsgFromISIS) {  // client.useISIS and Msg from ISIS (TCSAgent v1.4.3)
      SendToISISServer(&client,msg);
      msg[strlen(msg)-1]='\0';
      sprintf(cmsg, "ISIS OUT: %s",msg);_dbgmsgout(cmsg);
    }

    else {
      ReplyToRemHost(&client,msg);
      msg[strlen(msg)-1]='\0';
      sprintf(cmsg, "REMC OUT: %s",msg);_dbgmsgout(cmsg);
    }
  }// end of reply handling

}

//------------------------------------------------------------------------------
//
// SendISISMsg() - send a STATUS/ERROR message to remote nodes in ISIS client mode
//
//

int 
SendISISMsg(const char *msg, MsgType type, const char *dest, char *reply)
{

  char ISISmsg[BIG_STR_SIZE];

  if( client.useISIS && agent.isISISconnected ) {

    strcpy(ISISmsg, ISISMessage(client.ID,(char*)dest,type,(char*)msg));

    if( SendToISISServer(&client,ISISmsg) < 0 ) {
      sprintf(reply, "Failed to send a message to ISIS node %s.. %s", dest, strerror(errno));
      return -1;
    }
    else {
      ISISmsg[strlen(ISISmsg)-1]='\0';
      sprintf(cmsg, "ISIS OUT: %s\n",ISISmsg);_dbgmsgout(cmsg);
    }

  }

  else {

    strcpy(reply, "No ISIS server active, remote cmds unavailable");
    return -1;

  }
    
  return 0;
}


//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
//
// cmd_xxx() action functions
//
// Add new functions at the end.  To be available, they must be entered
// as "action" members in the Commands struct for this application (see
// commands.h)
//

//
// *** CLIENT COMMANDS BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// section.cmdname - command functions Template
//

/*
int
cmd_xxx(char *args, MsgType msgtype, char *reply)
{

  if(badness)
    return CMD_ERR;
  
  return CMD_OK;
}
*/

//------------------------------------------------------------------------------
//
// client.quit - allowed only if EXEC from remote hosts (keyboard
//               commands are always EXEC.

int
cmd_quit(char *args, MsgType msgtype, char *reply)
{
//if( msgtype == EXEC ) {
  if( msgtype == EXEC || msgtype == OSC ) {   // 'OSC' message type is added for commanding in script at v0.6.0
    client.KeepGoing=0;
    sprintf(reply,"%s=DISABLED MODE=OFFLINE", client.ID);
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

  sprintf(cmsg, "\n\n"
                "  OBS Agent now quit to re-start.\n"
                "  Press ENTER to continue..");
  _msgout(cmsg);
  getchar();
  putchar('\n');

  cmd_quit(args, msgtype, reply);

  return CMD_OK;


  ////////////////////////////////////////////////////////////////////////////
  // v0.0.7 --> modified at v0.0.9
  /*
  if( SendISISMsg("ping", REQ, "XIS", cbuf) < 0 ) {
    sprintf(reply, "Failed to ping the ISIS server (%s), %s", strerror(errno), cbuf);
    return CMD_ERR;
  }
  strcpy(reply, "PING sended for ISIS node registration"); 
  return CMD_OK;
  */
  ////////////////////////////////////////////////////////////////////////////

}

//------------------------------------------------------------------------------
//
// client.info - return application runtime information
//

int
cmd_info(char *args, MsgType msgtype, char *reply)
{

  // start with the application version #, ID, and host info

  sprintf(reply, "KMTNet OBSAgent %s ID=%s Host=%s:%d",
	                agent.AppVersion, client.ID, client.Host, client.Port);

  // if configured as an ISIS client, report this and the ISIS host:port info,
  // otherwise if standalone, report that, and the host:port of the last
  // remote host to send us something, if known.

  if(client.useISIS) {
    sprintf(reply, "%s Mode=ISISClient ISISID=%s ISISHost=%s:%d ISISConnection=%d", reply,
	                  client.isisID, client.isisHost, client.isisPort, agent.isISISconnected);
  }
  else {
    if(strlen(client.remHost)>0)
      sprintf(reply, "%s Mode=STANDALONE RemHost=%s:%d",reply,
	                    client.remHost, client.remPort);
    else
      strcat(reply," Mode=STANDALONE");
  }

  // Report system status and configuration

  sprintf(reply, "%s ISISconnection=%d TCSconnection=%d AUXconnection=%d", reply, 
                  agent.isISISconnected, sys.flag_tcsconnected, sys.flag_auxconnected  );

  sprintf(reply, "%s TelLatitude=%.6f TelLongitude=%+.6f TelElevation=%.1f", reply, 
                  sys.tcs_latitude, sys.tcs_longitude, sys.tcs_elevation  );

  sprintf(reply, "%s TcsTolerancePointing=%.2f TcsToleranceTracking=%.2f", reply, 
                  sys.tcs_tolerance_pointing, sys.tcs_tolerance_tracking  );

  sprintf(reply, "%s TcsHysteresisUnstable=%d", reply, sys.tcs_allowance_unstable );  // v0.9.1

  sprintf(reply, "%s TcsLimitHA=%.2f TcsLimitDecN=%+.2f TcsLimitDecS=%+.2f"
                 " TcsLimitSecZ=%.2f TcsLimitAlt=%.2f TcsLimitWarning=%.2f", reply, 
                  sys.tcs_limit_ha, sys.tcs_limit_dec_n, sys.tcs_limit_dec_s, 
                  sys.tcs_limit_secz, sys.tcs_limit_alt, sys.tcs_limit_warning  );

  sprintf(reply, "%s Filter0=%s Filter1=%s Filter2=%s Filter3=%s Filter4=%s", reply, 
                  sys.filterlabel[0], sys.filterlabel[1], sys.filterlabel[2], 
                  sys.filterlabel[3], sys.filterlabel[4]  );

  sprintf(reply, "%s OverrideIsisConErr=%s OverrideTcsConErr=%s OverrideAuxConErr=%s", reply, 
                  agent.flag_override_isisconnection?"ENABLED":"DISABLED", 
                  sys.flag_override_tcsconnection?"ENABLED":"DISABLED", 
                  sys.flag_override_auxconnection?"ENABLED":"DISABLED"  );   // modified to include TCS connection error overide (v0.4.9)

  // Report application runtime flags

  sprintf(reply, "%s %s %s %s %s %s %s %s", reply,
                  (client.isVerbose    ? "VERBOSE"  : "CONCISE" ),
                  (client.Debug        ? "DEBUG+"   : "DEBUG-"  ),
                  (client.doLogging    ? "DOLOG+"   : "DOLOG-"  ),
                  ( agent.isDebugLog   ? "DBGLOG+"  : "DBGLOG-" ),
                  ( agent.isScrObsLog  ? "OBSLOG+"  : "OBSLOG-" ),
                  ( agent.isLogVerbose ? "LOGVER+"  : "LOGVER-" ),
                  ( agent.isTimeTag    ? "TIMETAG+" : "TIMETAG-")  );

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
  sprintf(reply, "KMTNet OBS Agent Version=(%s) CompileDate=%s CompileTime=%s",
                 agent.AppVersion, APP_COMPDATE, APP_COMPTIME);
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// client.timetag - toggle to enable time tag display on console
//
  
int
cmd_timetag(char *args, MsgType msgtype, char *reply)
{
  if(agent.isTimeTag) {
    agent.isTimeTag = 0;
    strcpy(reply,"time tag display disabled");
  }
  else {
    agent.isTimeTag = 1;
    strcpy(reply,"time tag display enabled");
  }
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// client.verbose - toggle to enable verbose console output
//
  
int
cmd_verbose(char *args, MsgType msgtype, char *reply)
{
  if(client.isVerbose) {
    client.isVerbose = 0;
    strcpy(reply,"verbose mode disabled");
  }
  else {
    client.isVerbose = 1;
    strcpy(reply,"verbose mode enabled");
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
  strcpy(reply,"verbose mode disabled");

  return CMD_OK;
}

//------------------------------------------------------------------------------
// 
// client.debug - toggle debugging output
//

int
cmd_debug(char *args, MsgType msgtype, char *reply)
{
  if(client.Debug) {
    client.Debug = 0;
    strcpy(reply,"debugging output disabled");
  }
  else {
    client.Debug = 1;
    strcpy(reply,"debugging output enabled");
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

  if( msgtype == EXEC ) {

    the_list = history_list();

    if(strstr(args,"-c")>0) {
      clear_history();
      strcpy(reply,"All the histroy entries cleared");
      return CMD_OK;
    }

    if(the_list) {

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
  if( msgtype == EXEC ) {
    printf("\n");
    printf("              <<  KMTNet OBS Agent interactive commands  >>                    \n");
    printf("_______________________________________________________________________________\n");
    printf("Client commands:\n");
    printf("  quit            - quit OBS Agent application\n");
    printf("  init    / reset - quit OBS Agent application to restart\n");
    printf("  info            - report client information\n");
    printf("  version / ver   - report client version & compile info\n");
    printf("  timetag         - toggle time tag display on console\n");
    printf("  verbose         - toggle verbose output mode\n");
    printf("  concise         - disable verbose output mode\n");
    printf("  debug           - toggle debugging output\n");
    printf("  history         - show command history\n");
    printf("  !!              - repeat last command\n");
    printf("  !cmd            - repeat last command matching 'cmd'\n");
    printf("  help      / ?   - view this TCS Agent commands list\n");
    printf("_______________________________________________________________________________\n");
    printf("TCS commands:\n");
    printf("  tcsinit         - initialize PC-TCS Telcom link\n");
    printf("  tcsreset        - reset/restart PC-TCS Telcom link\n");
    printf("  tcsclose        - close PC-TCS Telcom link\n");
    printf("  tcsarc          - toggle AutoRecovery mode for TCS link\n");
    printf("  tcsstatus       - query TCS status with the telemetry data\n");
    printf("  tstat           - query lightweight TCS status without keywords\n");
    printf("  traw            - return lastest raw PC-TCS telemetry packet string\n");
    printf("  tsync           - synch PC-TCS clock with the system UTC clock\n");
    printf("  tcmd            - send a raw PC-TCS command, arg: <tcmd>\n");
    printf("  treq            - send a raw PC-TCS request, arg: <treq>\n");
    printf("  tmradec  / tmr  - move to J2000 RA/Dec, args: <ra> <dec> (<copt>)\n"); 
    printf("  tmobject / tmo  - move to object, defined in catalog, arg: <obj>\n");
    printf("  tmelaz   / tme  - move to elevation/azimuth, args: <el> <az>\n");
    printf("  tmoffset / toff - move to offset RA/Dec, args: <RA_offset> <DEC_offset>\n");
    printf("  tguide   / tgui - guiding offset move, args: <ra_offset> <dec_offset>\n");
    printf("  tstop    / stop - cancel command and stop telescope for commanded motions\n");
    printf("  tstow    / stow - tracking off & move telescope to stow position(zenith)\n");
    printf("  tdi             - synch the current position with the commanded position\n");
    printf("  cc / oo         - utility for the pointing model measurement observation\n");
    printf("  nstset          - set RA/Dec velocity for non-sidereal tracking\n");
    printf("  nston           - enable the non-sidereal tracking\n");
    printf("  nstoff          - disable the non-sidereal tracking\n");
    printf("_______________________________________________________________________________\n");
    printf("AUX control commands:\n");
    printf("  auxinit         - initialize AUX control link\n");
    printf("  auxreset        - reset/restart AUX control link\n");
    printf("  auxclose        - close AUX control link\n");
    printf("  auxarc          - toggle the auto recovery mode for AUX link\n");
    printf("  auxstatus       - query AUX status with the telemetry data\n");
    printf("  astat           - query lightweight AUX status without keywords\n");
    printf("  acmd            - send a raw AUX control remote command, arg: <acmd>\n");
    printf("  fsastat  /fs    - query & return AUX Filter/Shutter status\n");
    printf("  filter          - change filters to arg # or name, arg: <fnum/fname>\n");
    printf("  filname         - query & return the filter names for 4 slides\n");
    printf("  fttstat  /ft    - query & return AUX Focuse/TipTilt/Limit/Position(S/E/W)\n");
    printf("  dfocus          - adjust the focus position of PFI, arg: <dfoc>\n");
    printf("  dtilt           - adjust the tip-tilt angle ofg PFI, args: <dtns> <dtew>\n");
    printf("  fttgoto         - goto abs focus & tip-tilt, args: <foc> (<tns> <tew>)\n");
    printf("_______________________________________________________________________________\n");
    printf("ICS commands:\n");
    printf("  status          - query ICS  status and check connection to ICS\n");
    printf("  kstatus         - query K.IC status and check connection to K.IC\n");
    printf("  mstatus         - query M.IC status and check connection to M.IC\n");
    printf("  tstatus         - query T.IC status and check connection to T.IC\n");
    printf("  nstatus         - query N.IC status and check connection to N.IC\n");
    printf("  gstatus         - query G.IC status and check connection to G.IC\n");
    printf("  acqstatus       - query acqusition ready status for Sci.CCDs(K/M/T/N.IC)\n");
    printf("  filename        - query & set filename of FITS data\n");
    printf("  expnum          - query & set file serial number, arg: <filenum>\n");
  //printf("  bin             - query & set CCD binning configuration, arg: <bin>\n");
  //printf("  roi             - query & set CCD region of interest(subsection), arg: <x1> <x2> <y1> <y2>\n");
  //printf("  displ           - what is this for ?\n");
    printf("  dmawait         - query & set DMAWAIT of Master IC, arg: <dmawait>\n");
    printf("  datasource      - query & set DATASOUECE of each CCD, arg: 'adc'/'ctc'\n");
    printf("  ledflash        - query and set projector LED flashing time, arg: <cnt>\n");
    printf("  observer        - query and set observer's name, arg: <observer's name>\n");
    printf("  projid          - query and set project ID, arg: <projid>\n");
    printf("  exp             - query and set exposure time, arg: <exptime> in sec\n");
    printf("  object / bias / dark / flat / sky / domeflat / standard\n");
    printf("                  - query & set image type and object name, arg: <objname>\n");
    printf("  go              - start exposure and readout sequence, arg: <framenum>\n");
  //printf("  stop            - stop exposure and start readout\n");  // reserved, error, debugging needed
  //printf("  abort           - stop exposure and abort readout\n");  // reserved, error, debugging needed
  //printf("  movie           - what is this for ?\n");
    printf("_______________________________________________________________________________\n");
    printf("Status and sub-system commands:\n");
    printf("  expinfo  / ee   - query information about current exposure\n");
    printf("  sysstat  / ss   - query observation system status\n");
    printf("  domestat / dstat- query dome status on Redis/Relay/AuxStatus\n");
    printf("  override / ovr  - toggle override for link failed, arg: 'i'/'t'/'a'/'*'/'?'\n");
  //printf("  ovron/ovroff    - enable/disable to override for link failed to all systems\n"); --> replaced with 'override'
    printf("  dlamp           - set domeflat lamp power, args: 'on'/'off'\n");
    printf("  dlight          - set dome LED light power, args: 'on'/'off'\n");
    printf("  mcfan           - set mirror cell fan power, args: 'on'/'off'\n");
    printf("  tpad            - set TCS paddle N/S/E/W buttons, args: 'on'/'off' x 4\n");
    printf("  drot     / dr   - get and update the dome rotation status\n");
    printf("_______________________________________________________________________________\n");
    printf("Utility commands:\n");
    printf("  ecmd     / ec   - execute a external command line on shell, arg: <ecmd>\n");
    printf("  dtchk           - check data transfer & quit OBSAgent, arg: 'last'/<yyyymmdd>\n");
    printf("  redisget / rget - get a value from redis server on newTCS, arg: <key>\n");
  //printf("  redisset        - set key=value pair to redis server on newTCS, arg: <key> <val>\n");
    printf("  warning         - activate/deactivate warning blinking\n");    
    printf("  msgout          - output message on console & into log file, arg: <msg>\n");    
    printf("  sleep           - sleep all the process as specified, arg: <sleep_sec>\n");
    printf("  tick            - time tag output and measure elapse times, arg: '0'/<n>\n");
    printf("  noop            - no operation and response, for dummy command line in osc\n");
    printf("  getut     / ut  - get UT string & seconds since epoch(1970Jan01)\n");
    printf("  getjd     / jd  - get Julian date at input UT, arg: (<ut>)\n");
    printf("  getlst    / lst - get Local sidereal time at input UT, arg: (<ut>)\n");
    printf("  getalt    / alt - get Alt/Az/HA/Airmass at input UT, args: <ra> <dec> (<ut>)\n");
    printf("_______________________________________________________________________________\n");
    printf("Script observation commands:\n");
    printf("  oscript  / osc  - query & import an observation script, arg: (<file>)\n");
  //printf("  oline           - query a script line, args: (cmd/exp) <#>(-<#>) (<ut>)\n");  // one of plans considered..
    printf("  oline           - query script lines, args: (cmd/exp) <line#>/-<lines> (<ut>)\n");
    printf("  olabel          - search for labels containing keyword, args: <word> (<ut>)\n");
    printf("  oobject         - search for objects containing keyword, args: <word> (<ut>)\n");
    printf("  ostat    / os   - query script observation status\n");
    printf("  olast           - query last completed script line number\n");
    printf("  ostart          - start obs script running, arg: (<start line#>)\n");
    printf("  ostop           - stop obs script running after current exposure complete\n");
    printf("  oabort          - abort obs script running (immediately stop all process)\n");
    printf("  opause   / op   - pause obs script running\n");
    printf("  oresume  / or   - resume obs script running\n");
    printf("  oprepare        - toggle next exposure preparation\n");
    printf("  odelay  / delay - delay script observation process, arg: <delay_sec>\n");
    printf("_______________________________________________________________________________\n");
    printf("\n");

    return CMD_NOOP;
  }

  // Can't use HELP unless you're on the console...

  strcpy(reply, "cannot execute 'help' - remote operation not allowed");
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
  
  if( msgtype == REQ ) {
    
    sprintf(cmsg, "PONG received from %s\n", SourceID);_vmsgout(cmsg);

    if(strcasecmp(SourceID, client.isisID)==0) {
      if( !agent.isISISconnected ) {  // v0.1.2
        agent.isISISconnected = 1;  // v0.0.7
        GRNTEXT;sprintf(cmsg, "STATUS: ISIS server is connected.\n");_msgout(cmsg);
      }
      if(sys.camstatus==CAMSTATUS_NC) {
        //sys.camstatus = CAMSTATUS_IDLE_3;  // v0.0.8 
        sys.camstatus = CAMSTATUS_READY;  // v0.4.5
        if(osc.flag_process) expinfo.nStatus = EXPSTATUS_WAITING;
        else expinfo.nStatus = EXPSTATUS_STANDBY;   // v1.0.0
        sys.status_fitssaved = 1;
      }
    }
    
    return CMD_NOOP;
    
  }

  strcpy(reply, "'pong' command is not allowed on console or script operation");   // added to prevent the confusion (v0.6.0)  
  return CMD_ERR;
}

//
// *** TC.TCS & TC.AUX COMMANDS BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// tc.cmd - send a command to TC
//

int
cmd_tc(char *args, MsgType msgtype, char *reply)
{

  char msg[BIG_STR_SIZE];       // ISIS message buffer

  sprintf(msg, "%s %s", InputCMD, args);

  for( int n = strlen(msg) ; n>0 ; n-- ) 
    if( msg[n-1]==0x20 || msg[n-1]==0x0D ) msg[n-1] = NUL;  // Space or CR
    else break;

  if( sys.nston && strncasecmp(args,"TMR" ,3)==0 ) sys.timestamp_tmr = SysTimestamp();   // for checking tel position if NST on, v0.7.5

  if( SendISISMsg(msg, REQ, "TC", reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;

}

//------------------------------------------------------------------------------
//
// tc.nstset - set non-sidereal tracking RA/DEC velocity
//

int
cmd_nstset(char *args, MsgType msgtype, char *reply)
{

  int nRtn;
  char msg[BIG_STR_SIZE];       // ISIS message buffer
  double vel_ra, vel_dec;

  nRtn = sscanf(args, "%lf %lf", &vel_ra, &vel_dec);

  if( nRtn < 2 ) {
    strcpy(reply, "Usage: nstset  <vel_ra>  <vel_dec>  (in arcsec/sec)"); 
    return CMD_ERR;
  }

  if(vel_ra>300.0) {
    sprintf(reply, "Too fast RA velocity %.2f arcsec/sec!", vel_ra); 
    return CMD_ERR;
  }

  if(vel_dec>300.0) {
    sprintf(reply, "Too fast DEC velocity %.2f arcsec/sec!", vel_dec); 
    return CMD_ERR;
  }

  sprintf(msg, "tcmd %s %.5f", sys.tcspad_tcmd_vel_ra, vel_ra);
  if( SendISISMsg(msg, REQ, "TC", reply) < 0 ) return CMD_ERR;
  sys.cmd_velra = vel_ra;  // latest commanded RA velocity for non-sidereal tracking

  sprintf(msg, "tcmd %s %.5f", sys.tcspad_tcmd_vel_dec, vel_dec);
  if( SendISISMsg(msg, REQ, "TC", reply) < 0 ) return CMD_ERR;
  sys.cmd_veldec = vel_dec;  // latest commanded Dec velocity for non-sidereal tracking

  //return CMD_NOOP;

  sprintf(reply, "Non-sidereal tracking velocity setting complete, VEL_RA=%.5f, VEL_DEC=%.5f (aresec/sec)", vel_ra, vel_dec);
  return CMD_OK;

}

//------------------------------------------------------------------------------
//
// tc.nston - enable the non-sidereal tracking (v0.7.6)
//

int
cmd_nston(char *args, MsgType msgtype, char *reply)
{
  int nRtn, i;
  char strCmd[STRLEN_CMD];

  for(i=0;i<4;i++) {

    if( i==NORTH || i==EAST ) strcpy(strCmd, sys.rcmd_tcspad_set_on [i]);
    else                      strcpy(strCmd, sys.rcmd_tcspad_set_off[i]);

    nRtn = system(strCmd);

    if( nRtn!=0 ) {
      switch( WEXITSTATUS(nRtn) ) {
        case   1: strcpy(reply, "Invalid argument format for PC-TCS paddle control" ); break;
        case 127: strcpy(reply, "Invalid command line for PC-TCS paddle control"    ); break;
        case  28: strcpy(reply, "Failed to connect with the PC-TCS paddle relay"    ); break;
        case   7: strcpy(reply, "Connection refused by the PC-TCS paddle relay"     ); break;
        case   6: strcpy(reply, "Invalid IP address for the PC-TCS paddle relay"    ); break;
        default : strcpy(reply, "Failed to get status of the PC-TCS paddle relay"   ); break;
      }
      //sprintf(reply, "%s (ECMD string: \"%s\")", reply, strCmd);  // replaced as below at v0.9.4
      sprintf(cmsg, "STATUS: NST on failure! (ECMD string: \"%s\")", strCmd);_dbgmsgout(cmsg);
      return CMD_ERR;
    }

    if( i==NORTH || i==EAST ) sys.nston = ON;

  }

  strcpy(reply,"Non-sidereal tracking ON by TCS paddle control");  // using replay for remote client

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// tc.nstoff - disable the non-sidereal tracking (v0.7.6)
//

int
cmd_nstoff(char *args, MsgType msgtype, char *reply)
{
  int nRtn, i;
  char strCmd[STRLEN_CMD];

  for(i=0;i<4;i++) {

    strcpy(strCmd, sys.rcmd_tcspad_set_off[i]);

    nRtn = system(strCmd);

    if( nRtn!=0 ) {
      switch( WEXITSTATUS(nRtn) ) {
        case   1: strcpy(reply, "Invalid argument format for PC-TCS paddle control" ); break;
        case 127: strcpy(reply, "Invalid command line for PC-TCS paddle control"    ); break;
        case  28: strcpy(reply, "Failed to connect with the PC-TCS paddle relay"    ); break;
        case   7: strcpy(reply, "Connection refused by the PC-TCS paddle relay"     ); break;
        case   6: strcpy(reply, "Invalid IP address for the PC-TCS paddle relay"    ); break;
        default : strcpy(reply, "Failed to get status of the PC-TCS paddle relay"   ); break;
      }
      //sprintf(reply, "%s (ECMD string: \"%s\")", reply, strCmd);  // replaced as below at v0.9.4
      sprintf(cmsg, "STATUS: NST off failure! (ECMD string: \"%s\")", strCmd);_dbgmsgout(cmsg);
      return CMD_ERR;
    }

  }

  sys.nston = OFF;

  strcpy(reply,"Non-sidereal tracking OFF by TCS paddle control");  // using replay for remote client

  return CMD_OK;
}

//
// *** ISIS/ICS COMMANDS BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// ics.cmd - send a command to ICS
//

int
cmd_ics(char *args, MsgType msgtype, char *reply)
{

  if(  ( CAMSTATUS_CHECK  < sys.camstatus && sys.camstatus < CAMSTATUS_INT_1  ) || 
       ( CAMSTATUS_INT_3  < sys.camstatus && sys.camstatus < CAMSTATUS_READ_1 ) || 
       ( CAMSTATUS_READ_3 < sys.camstatus && sys.camstatus < CAMSTATUS_READY  )   ) {   // added for checking camstatus at v0.4.5
    strcpy(reply, "ICS commands are unavailable during PREP / IDLE, input again after the CamStatus is changed to INT / READ / READY");
    return CMD_ERR;
  }

  char msg[BIG_STR_SIZE];       // ISIS message buffer

  sprintf(msg, "%s %s", InputCMD, args);

  if( SendISISMsg(msg, REQ, "ICS", reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;

}

//------------------------------------------------------------------------------
//
// ics.cmd.go - send the 'GO' command to ICS
//

int
cmd_ics_go(char *args, MsgType msgtype, char *reply)
{

  if( CAMSTATUS_CHECK < sys.camstatus && sys.camstatus < CAMSTATUS_IDLE_3 ) {   // added for checking camstatus at v0.4.5
    strcpy(reply, "'GO' command is unavailable until IDLE_2 , input again after the CamStatus is changed to IDLE_3 / READY");
    return CMD_ERR;
  }

  char msg[BIG_STR_SIZE];       // ISIS message buffer

  sprintf(msg, "%s %s", InputCMD, args);

  if( SendISISMsg(msg, REQ, "ICS", reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;

}

//------------------------------------------------------------------------------
//
// ics.cmd.exp - send the 'EXP' command to ICS
//

int
cmd_ics_exp(char *args, MsgType msgtype, char *reply)
{

  if( ( CAMSTATUS_CHECK < sys.camstatus && sys.camstatus < CAMSTATUS_READ_1 ) || 
      ( CAMSTATUS_READ_3 < sys.camstatus && sys.camstatus < CAMSTATUS_READY )   ) {   // added for checking camstatus at v0.4.8
    strcpy(reply, "'EXP' command is unavailable during PREP / INT / IDLE, input again after the CamStatus is changed to READ / READY");
    return CMD_ERR;
  }

  char msg[BIG_STR_SIZE];       // ISIS message buffer

  sprintf(msg, "%s %s", InputCMD, args);

  if( SendISISMsg(msg, REQ, "ICS", reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;

}

//
// *** ISIS/ICs(K/M/T/N/G) COMMANDS BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// ics.dmawait - send DMAWAIT commands to K.IC
//

int
cmd_dmawait(char *args, MsgType msgtype, char *reply)
{
  char msg[BIG_STR_SIZE];       // ISIS message buffer
  char dest[16];

  sprintf(msg, "DMAWAIT %s", args);

  strcpy(dest, "K.IC");
  if( SendISISMsg(msg, REQ, dest, reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;
}

//------------------------------------------------------------------------------
//
// ics.datasource - send DATASOURCE commands to K.IC/M.IC/T.IC/N.IC
//

int
cmd_datasource(char *args, MsgType msgtype, char *reply)
{
  char msg[BIG_STR_SIZE];       // ISIS message buffer
  char dest[16];

  sprintf(msg, "DATASOURCE %s", args);

  strcpy(dest, "K.IC");
  if( SendISISMsg(msg, REQ, dest, reply) < 0 ) return CMD_ERR;

  strcpy(dest, "M.IC");
  if( SendISISMsg(msg, REQ, dest, reply) < 0 ) return CMD_ERR;

  strcpy(dest, "T.IC");
  if( SendISISMsg(msg, REQ, dest, reply) < 0 ) return CMD_ERR;

  strcpy(dest, "N.IC");
  if( SendISISMsg(msg, REQ, dest, reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;
}

//------------------------------------------------------------------------------
//
// ics.kstatus - send STATUS commands to K.IC
//

int
cmd_kstatus(char *args, MsgType msgtype, char *reply)
{
  char msg[BIG_STR_SIZE];       // ISIS message buffer
  char dest[16];

  strcpy(msg, "STATUS");
  strcpy(dest, "K.IC");
  if( SendISISMsg(msg, REQ, dest, reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;
}

//------------------------------------------------------------------------------
//
// ics.mstatus - send STATUS commands to M.IC
//

int
cmd_mstatus(char *args, MsgType msgtype, char *reply)
{
  char msg[BIG_STR_SIZE];       // ISIS message buffer
  char dest[16];

  strcpy(msg, "STATUS");
  strcpy(dest, "M.IC");
  if( SendISISMsg(msg, REQ, dest, reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;
}

//------------------------------------------------------------------------------
//
// ics.tstatus - send STATUS commands to T.IC
//

int
cmd_tstatus(char *args, MsgType msgtype, char *reply)
{
  char msg[BIG_STR_SIZE];       // ISIS message buffer
  char dest[16];

  strcpy(msg, "STATUS");
  strcpy(dest, "T.IC");
  if( SendISISMsg(msg, REQ, dest, reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;
}

//------------------------------------------------------------------------------
//
// ics.nstatus - send STATUS commands to N.IC
//

int
cmd_nstatus(char *args, MsgType msgtype, char *reply)
{
  char msg[BIG_STR_SIZE];       // ISIS message buffer
  char dest[16];

  strcpy(msg, "STATUS");
  strcpy(dest, "N.IC");
  if( SendISISMsg(msg, REQ, dest, reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;
}

//------------------------------------------------------------------------------
//
// ics.gstatus - send STATUS commands to G.IC
//

int
cmd_gstatus(char *args, MsgType msgtype, char *reply)
{
  char msg[BIG_STR_SIZE];       // ISIS message buffer
  char dest[16];

  strcpy(msg, "STATUS");
  strcpy(dest, "G.IC");
  if( SendISISMsg(msg, REQ, dest, reply) < 0 ) return CMD_ERR;
 
  return CMD_NOOP;
}

//
// *** STATUS and SUB-SYSTEM COMMANDS BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// expc.info - query information about current exposure and FITS file (v1.0.0)
//

int
cmd_expinfo(char *args, MsgType msgtype, char *reply)
{

  //// Update and return the informatoin string for current exposure
  
  //  if( sys.camstatus<0 ) expinfo.nStatus = EXPSTATUS_ERROR;
  //  else if( sys.camstatus==CAMSTATUS_CHECK ) {
  //    if(osc.flag_process) expinfo.nStatus = EXPSTATUS_CMDED;
  //    else expinfo.nStatus = EXPSTATUS_CHECK;
  //  }
  //  else if( sys.camstatus==CAMSTATUS_READY ) {
  //    if(osc.flag_process) expinfo.nStatus = EXPSTATUS_WAITING;
  //    else expinfo.nStatus = EXPSTATUS_STANDBY;
  //  }
  //  else if( CAMSTATUS_PREP_I<=sys.camstatus && sys.camstatus<CAMSTATUS_INT_1  ) expinfo.nStatus = EXPSTATUS_FLUSH;
  //  else if( CAMSTATUS_INT_1 <=sys.camstatus && sys.camstatus<CAMSTATUS_READ_1 ) expinfo.nStatus = EXPSTATUS_EXPOSURE;
  //  else if( CAMSTATUS_READ_1<=sys.camstatus && sys.camstatus<CAMSTATUS_IDLE_1 ) expinfo.nStatus = EXPSTATUS_READOUT;
  //  else if( CAMSTATUS_IDLE_1<=sys.camstatus && sys.camstatus<CAMSTATUS_READY  ) expinfo.nStatus = EXPSTATUS_FINISH;
  //  else expinfo.nStatus = 99;
  //// not necessary, since expinfo.nStatus is set at the same time as setting camstatus to synchronize information in memory

  switch(expinfo.nStatus) {
    case EXPSTATUS_CHECK   : strcpy(expinfo.strStatus, "CHECK   "); break;
    case EXPSTATUS_STANDBY : strcpy(expinfo.strStatus, "STANDBY "); break;
    case EXPSTATUS_WAITING : strcpy(expinfo.strStatus, "WAITING "); break;
    case EXPSTATUS_CMDED   : strcpy(expinfo.strStatus, "CMDED   "); break;
    case EXPSTATUS_FLUSH   : strcpy(expinfo.strStatus, "FLUSH   "); break;
    case EXPSTATUS_EXPOSURE: strcpy(expinfo.strStatus, "EXPOSURE"); break;
    case EXPSTATUS_READOUT : strcpy(expinfo.strStatus, "READOUT "); break;
    case EXPSTATUS_FINISH  : strcpy(expinfo.strStatus, "FINISH  "); break;
    case EXPSTATUS_ERROR   : strcpy(expinfo.strStatus, "ERROR   "); break;
    default                : strcpy(expinfo.strStatus, "UNKNOWN "); break;
  }

       if(expinfo.nStatus<EXPSTATUS_EXPOSURE) expinfo.dElapsed = 0.0;
  else if(expinfo.nStatus>EXPSTATUS_EXPOSURE) expinfo.dElapsed = expinfo.dSetting;
  else expinfo.dElapsed = MIN( (SysTimestamp()-expinfo.dStartTime), expinfo.dSetting );
  sprintf(expinfo.strExpProg, "%d/%d", (int)expinfo.dElapsed, (int)expinfo.dSetting);

  //sprintf(reply, "ExpStatus=%s ExpNum=%s  ExpStart=%s  ExpProg=%-9s  FitsNum=%s", 
  //        expinfo.strStatus,  expinfo.strCurNum, expinfo.strExpStart, expinfo.strExpProg, expinfo.strFitsNum);
  sprintf(reply, "ExpStatus=%s ExpNum=%s  ExpStart=%s  ExpProg=%-9s  FitsNum=%s  FitsOsc=%-5s", 
          expinfo.strStatus,  expinfo.strCurNum, expinfo.strExpStart, expinfo.strExpProg, expinfo.strFitsNum, expinfo.strFitsOsc);   // v1.0.9

  return CMD_OK;

}

//------------------------------------------------------------------------------
//
// sys.sysstatus - observation system status/data report
//

int
cmd_sysstatus(char *args, MsgType msgtype, char *reply)
{
  char strCamStatus[16];
  char strTelStatus[16];
  char strTcsMove  [16];
  char strTcsLimit [16];
  char strTcsDrive [16];
  char strDomeRota [16];  // v0.9.4
  char strDomeShut [16];  // v0.9.4

  //// update camera status label

  switch (sys.camstatus) {
    case CAMSTATUS_NC      : strcpy(strCamStatus, "NC"      ); break;
    case CAMSTATUS_PREP_I  : strcpy(strCamStatus, "PREP_I"  ); break;
    case CAMSTATUS_PREP_E  : strcpy(strCamStatus, "PREP_E"  ); break;
    case CAMSTATUS_INT_1   : strcpy(strCamStatus, "INT_1"   ); break;
    case CAMSTATUS_INT_2   : strcpy(strCamStatus, "INT_2"   ); break;
    case CAMSTATUS_INT_3   : strcpy(strCamStatus, "INT_3"   ); break;
    case CAMSTATUS_CLOSING : strcpy(strCamStatus, "CLOSING" ); break;
    case CAMSTATUS_READ_1  : strcpy(strCamStatus, "READ_1"  ); break;
    case CAMSTATUS_READ_2  : strcpy(strCamStatus, "READ_2"  ); break;
    case CAMSTATUS_READ_3  : strcpy(strCamStatus, "READ_3"  ); break;
    case CAMSTATUS_IDLE_1  : strcpy(strCamStatus, "IDLE_1"  ); break;
    case CAMSTATUS_IDLE_2  : strcpy(strCamStatus, "IDLE_2"  ); break;
    case CAMSTATUS_IDLE_3  : strcpy(strCamStatus, "IDLE_3"  ); break;
    case CAMSTATUS_READY   : strcpy(strCamStatus, "READY"   ); break;
    case CAMSTATUS_CHECK   : strcpy(strCamStatus, "CHECK"   ); break;
    case CAMSTATUS_CRASHED : strcpy(strCamStatus, "CRASHED" ); break;
    case CAMSTATUS_DEAD    : strcpy(strCamStatus, "DEAD"    ); break;
    default                : strcpy(strCamStatus, "UNKNOWN" ); break;
  }

  //// update telescope status label

  switch (sys.telstatus) {
    case TELSTATUS_NC       : strcpy(strTelStatus, "NC"       ); break;
    case TELSTATUS_CHECKING : strcpy(strTelStatus, "CHECKING" ); break;
    case TELSTATUS_STOW     : strcpy(strTelStatus, "STOW"     ); break;
    case TELSTATUS_HOLDING  : strcpy(strTelStatus, "HOLDING"  ); break;
    case TELSTATUS_TRACKING : strcpy(strTelStatus, "TRACKING" ); break;
    case TELSTATUS_TRACKINGS: strcpy(strTelStatus, "TRACKINGS"); break;
    case TELSTATUS_SLEW     : strcpy(strTelStatus, "SLEW"     ); break;
    case TELSTATUS_SETTLING : strcpy(strTelStatus, "SETTLING" ); break;
    case TELSTATUS_OSCILLATE: strcpy(strTelStatus, "OSCILLATE"); break;
    case TELSTATUS_DISABLED : strcpy(strTelStatus, "DISABLED" ); break;
    default                 : strcpy(strTelStatus, "UNKNOWN"  ); break;
  }

  //// update TCS moving status labels

  switch (sys.movestatus) {
    case 0: strcpy(strTcsMove,"IDLE   ");break;
    case 1: strcpy(strTcsMove,"RA     ");break;
    case 2: strcpy(strTcsMove,"DEC    ");break;
    case 3: strcpy(strTcsMove,"RA+DEC ");break;
   default: strcpy(strTcsMove,"UNKNOWN");break;
  }

  //// update TCS limits status labels

  switch (sys.limitstatus) {
    case 0: strcpy(strTcsLimit,"NO       ");break;
    case 1: strcpy(strTcsLimit,"RA       ");break;
    case 2: strcpy(strTcsLimit,"DEC      ");break;
    case 3: strcpy(strTcsLimit,"RA+DEC   ");break;
    case 4: strcpy(strTcsLimit,"ELEVATION");break;
    case 5: strcpy(strTcsLimit,"RA+EL    ");break;
    case 6: strcpy(strTcsLimit,"DEC+EL   ");break;
    case 7: strcpy(strTcsLimit,"RA+DEC+EL");break;
   default: strcpy(strTcsLimit,"UNKNOWN  ");break;
  }

  //// update TCS drive enable/disable status labels

  switch (sys.drivedisable) {
    case 0: strcpy(strTcsDrive,"ENABLED ");break;
    case 1: strcpy(strTcsDrive,"DISABLED");break;
   default: strcpy(strTcsDrive,"UNKNOWN ");break;
  }

  //// update exposure time remaining (v0.3.3)

  if( sys.flag_expcount ) {
    sys.exp_remaining = sys.exp_set - ( SysTimestamp() - sys.exp_starttime );
    sys.exp_remaining = MAX( sys.exp_remaining, 0.0 );
  }

  //// update dome status labels (v0.9.4)

  switch (sys.domerot) {
    case DOME_IDLE    : strcpy(strDomeRota,"IDLE    ");break;
    case DOME_ROTATING: strcpy(strDomeRota,"ROTATING");break;
    case DOME_UNKNOWN : strcpy(strDomeRota,"UNKNOWN ");break;
    default           : strcpy(strDomeRota,"UNKNOWN ");break;
  }

  switch (sys.domeshut) {
    case DOME_IDLE   : strcpy(strDomeShut,"IDLE   ");break;
    case DOME_MOVING : strcpy(strDomeShut,"MOVING ");break;
    case DOME_UNKNOWN: strcpy(strDomeShut,"UNKNOWN");break;
    default          : strcpy(strDomeShut,"UNKNOWN");break;
  }

  //// build system status reply

  sprintf(reply, "CamStatus=%-7s FitsSaved=%-2d ExpSet=%-4.0f ExpRem=%-4.0f "
                 "TelStatus=%-11s  RA=%s DEC=%-11s Epoch=%-8.3f "
                 "HA=%-9s LST=%-8s SecZ=%-4.2f Alt=%-4.1f Az=%-+6.1f "
                 "Move=%s Limit=%s Drive=%s "
                 "TELID=%-8s "
                 "FILTSTAT=%-7s FILTER=%-7s ACTFILT=%-7s SHUTSTAT=%-9s SHUTTER=%-7s "
                 "FOCUS=%-+7.3f TNS=%-+5.0f TEW=%-+5.0f "
                 "S1=%+05.1f S2=%+05.1f S3=%+05.1f S4=%05.1f S5=%+05.1f S6=%+05.1f S7=%+05.1f FAN=%-3s "
                 "DomeRot=%s DomeShut=%s ",  // v0.9.3
                  strCamStatus, sys.status_fitssaved,
                  sys.exp_set, sys.exp_remaining,  // v0.3.3 
                  strTelStatus, sys.ra, sys.dec, sys.epoch_y, 
                  sys.ha, sys.lst, sys.secz, sys.alt_d, sys.az_d,
                  strTcsMove, strTcsLimit, strTcsDrive,
                  sys.telid, 
                  sys.filteropstat, sys.filtername, sys.filterlabel[sys.filternum], 
                  sys.shutopstat, sys.shutstatus, 
                  sys.focus, sys.tns, sys.tew, 
                  sys.ens[0], sys.ens[1], sys.ens[2], sys.ens[3], 
                  sys.ens[4], sys.ens[5], sys.ens[6], sys.fan,
                  strDomeRota, strDomeShut );

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// sys.domestatus - update dome status from Redis/Relay/AuxStatus (v0.9.5)
//

int
cmd_domestatus(char *args, MsgType msgtype, char *reply)
{
  UpdateDomeStatus(&sys, reply);
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// sys.override - toggle to enable/disable override system disconnection/error
//

int
cmd_override(char *args, MsgType msgtype, char *reply)
{
  // modified to include TCS connection error overide (v0.4.9)
  
  // args input & check

  if( strlen(args)==0 ) {
    strcpy(reply, "Usage: override 'isis'/'i'/'tcs'/'t'/'aux'/'a'/'*'/'on'/'off'/'?'>"); 
    return CMD_ERR;
  }

  else if( args[0] == '?' ) {
    sprintf(reply, "overrideISIS=%s overrideTCS=%s overrideAUX=%s", 
                               agent.flag_override_isisconnection?"ON":"OFF", 
                               sys.flag_override_tcsconnection?"ON":"OFF", 
                               sys.flag_override_auxconnection?"ON":"OFF" );
  }
  
  else if( args[0] == '*' ) {
    
    // toggle to override all the isis/tcs/aux disconnection/error

    if( agent.flag_override_isisconnection && sys.flag_override_tcsconnection && sys.flag_override_auxconnection ) {
      agent.flag_override_isisconnection = sys.flag_override_tcsconnection = sys.flag_override_auxconnection = 0;
      strcpy(reply,"Override disabled for all the ISIS/TCS/AUX disconnection");
    }
    else {
      agent.flag_override_isisconnection = sys.flag_override_tcsconnection = sys.flag_override_auxconnection = 1;
      strcpy(reply,"Override enabled for all the ISIS/TCS/AUX disconnection");
    }
    
  }

  else if( strncasecmp(args,"ON",2)==0 ) { 
    
    // enable to override all the isis/tcs/aux disconnection/error

    agent.flag_override_isisconnection = sys.flag_override_tcsconnection = sys.flag_override_auxconnection = 1;
    strcpy(reply,"Override enabled for all the ISIS/TCS/AUX disconnection");

  }

  else if( strncasecmp(args,"OFF",3)==0 ) { 

    // disable to override all the isis/tcs/aux disconnection/error

    agent.flag_override_isisconnection = sys.flag_override_tcsconnection = sys.flag_override_auxconnection = 0;
    strcpy(reply,"Override disabled for all the ISIS/TCS/AUX disconnection");

  }

  else if( strncasecmp(args,"ISIS",4)==0 || strncasecmp(args,"XIS",3)==0 || strncasecmp(args,"IS",2)==0 || strncasecmp(args,"I",1)==0 ) { 
    
  // toggle to override isis disconnection/error

    if(agent.flag_override_isisconnection) {
      agent.flag_override_isisconnection = 0;
      strcpy(reply,"Override disabled for the ISIS disconnection");
    }
    else {
      agent.flag_override_isisconnection = 1;
      strcpy(reply,"Override enabled for the ISIS disconnection");
    }
    
  }

  else if( strncasecmp(args,"TCS",3)==0 || strncasecmp(args,"TC",2)==0 || strncasecmp(args,"T",1)==0 ) { 
    
  // toggle to override tcs disconnection/error

    if(sys.flag_override_tcsconnection) {
      sys.flag_override_tcsconnection = 0;
      strcpy(reply,"Override disabled for the TCS disconnection");
    }
    else {
      sys.flag_override_tcsconnection = 1;
      strcpy(reply,"Override enabled for the TCS disconnection");
    }
    
  }
  
  else if( strncasecmp(args,"AUX",3)==0 || strncasecmp(args,"AU",2)==0 || strncasecmp(args,"A",1)==0 ) { 

  // toggle to override aux disconnection/error

    if(sys.flag_override_auxconnection) {
      sys.flag_override_auxconnection = 0;
      strcpy(reply,"Override enabled for the AUX disconnection");
    }
    else {
      sys.flag_override_auxconnection = 1;
      strcpy(reply,"Override disabled for the AUX disconnection");
    }

  }
  
  else {
    
    strcpy(reply, "The argument should be 'isis' / 'tcs' / 'aux' / '*' / 'on' / 'off' / '?'"); 
    return CMD_ERR;

  }

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// sys.ovron/ovroff - enable/disable to override for all the isis/tcs/aux disconnection or errors (v0.7.9)
//

//int
//cmd_ovron(char *args, MsgType msgtype, char *reply)
//{
//  agent.flag_override_isisconnection = sys.flag_override_tcsconnection = sys.flag_override_auxconnection = 1;
//  strcpy(reply,"Override enabled for all the ISIS/TCS/AUX disconnection");
//  return CMD_OK;
//}
//
//int
//cmd_ovroff(char *args, MsgType msgtype, char *reply)
//{
//  agent.flag_override_isisconnection = sys.flag_override_tcsconnection = sys.flag_override_auxconnection = 0;
//  strcpy(reply,"Override disabled for all the ISIS/TCS/AUX disconnection");
//  return CMD_OK;
//}
// -->  deleted at v0.9.4 as replaced with cmd_override()

//
// *** WEB RELAY COMMANDS BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// relay.dlamp - domeflat lamp relay control
//

int
cmd_dlamp(char *args, MsgType msgtype, char *reply)   // v0.5.1
{
  int nRtn;
  char strCmd[STRLEN_CMD];

       if( strncasecmp(args,"ON" ,2)==0 ) strcpy(strCmd, sys.rcmd_dlamp_set_on );
  else if( strncasecmp(args,"OFF",3)==0 ) strcpy(strCmd, sys.rcmd_dlamp_set_off);
  else {
    strcpy(reply, "Usage: dlamp 'on'/'off'"); 
    return CMD_ERR;
  }

  nRtn = system(strCmd);

  if( nRtn!=0 ) {
    switch( WEXITSTATUS(nRtn) ) {
      case   1: strcpy(reply, "Invalid argument format for domeflat lamp control" ); break;
      case 127: strcpy(reply, "Invalid command line for domeflat lamp control"    ); break;
      case  28: strcpy(reply, "Failed to connect with the domeflat lamp relay"    ); break;
      case   7: strcpy(reply, "Connection refused by the domeflat lamp relay"     ); break;
      case   6: strcpy(reply, "Invalid IP address for the domeflat lamp relay"    ); break;
      default : strcpy(reply, "Failed to get status of the domeflat lamp relay"   ); break;
    }
    //sprintf(reply, "%s (ECMD string: \"%s\")", reply, strCmd);  // replaced as below at v0.9.4
    sprintf(cmsg, "STATUS: Domeflat lamp control failure! (ECMD string: \"%s\")", strCmd);_dbgmsgout(cmsg);
    return CMD_ERR;
  }

  sprintf(reply,"Domeflat lamp turned %s", args);  // using replay for remote client

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// relay.dlight - dome LED light relay control
//

int
cmd_dlight(char *args, MsgType msgtype, char *reply)   // v0.6.8
{
  int nRtn;
  char strCmd[STRLEN_CMD];

       if( strncasecmp(args,"ON" ,2)==0 ) strcpy(strCmd, sys.rcmd_dlight_set_on );
  else if( strncasecmp(args,"OFF",3)==0 ) strcpy(strCmd, sys.rcmd_dlight_set_off);
  else {
    strcpy(reply, "Usage: dlight 'on'/'off'"); 
    return CMD_ERR;
  }

  nRtn = system(strCmd);

  if( nRtn!=0 ) {
    switch( WEXITSTATUS(nRtn) ) {
      case   1: strcpy(reply, "Invalid argument format for dome LED light control" ); break;
      case 127: strcpy(reply, "Invalid command line for dome LED light control"    ); break;
      case  28: strcpy(reply, "Failed to connect with the dome LED light relay"    ); break;
      case   7: strcpy(reply, "Connection refused by the dome LED light relay"     ); break;
      case   6: strcpy(reply, "Invalid IP address for the dome LED light relay"    ); break;
      default : strcpy(reply, "Failed to get status of the dome LED light relay"   ); break;
    }
    //sprintf(reply, "%s (ECMD string: \"%s\")", reply, strCmd);  // replaced as below at v0.9.4
    sprintf(cmsg, "STATUS: Dome light control failure! (ECMD string: \"%s\")", strCmd);_dbgmsgout(cmsg);
    return CMD_ERR;
  }

  sprintf(reply,"Dome LED light turned %s", args);  // using replay for remote client

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// relay.mcfan - mirror cell fan relay control
//

int
cmd_mcfan(char *args, MsgType msgtype, char *reply)   // v0.5.1
{
  int nRtn;
  char strCmd[STRLEN_CMD];

       if( strncasecmp(args,"ON" ,2)==0 ) strcpy(strCmd, sys.rcmd_mcfan_set_on );
  else if( strncasecmp(args,"OFF",3)==0 ) strcpy(strCmd, sys.rcmd_mcfan_set_off);
  else {
    strcpy(reply, "Usage: mcfan 'on'/'off'"); 
    return CMD_ERR;
  }

  nRtn = system(strCmd);

  if( nRtn!=0 ) {
    switch( WEXITSTATUS(nRtn) ) {
      case   1: strcpy(reply, "Invalid argument format for mirror cell fan control" ); break;
      case 127: strcpy(reply, "Invalid command line for mirror cell fan control"    ); break;
      case  28: strcpy(reply, "Failed to connect with the mirror cell fan relay"    ); break;
      case   7: strcpy(reply, "Connection refused by the mirror cell fan relay"     ); break;
      case   6: strcpy(reply, "Invalid IP address for the mirror cell fan relay"    ); break;
      default : strcpy(reply, "Failed to get status of the mirror cell fan relay"   ); break;
    }
    //sprintf(reply, "%s (ECMD string: \"%s\")", reply, strCmd);  // replaced as below at v0.9.4
    sprintf(cmsg, "STATUS: Mirrorcell Fan control failure! (ECMD string: \"%s\")", strCmd);_dbgmsgout(cmsg);

    return CMD_ERR;
  }

  sprintf(reply,"Mirror cell fan turned %s", args);  // using replay for remote client

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// relay.tpad - PC-TCS paddle control
//

int
cmd_tpad(char *args, MsgType msgtype, char *reply)   // v0.6.8
{
  int nRtn, i;
  char strCmd[STRLEN_CMD];
  char arg[4][STRLEN_ARGSS];

  nRtn = sscanf(args, "%s %s %s %s", arg[0], arg[1], arg[2], arg[3]);

  if( nRtn < 4 ) {
    strcpy(reply, "Usage: tpad  <north_relay>  <soutn_relay>  <east_relay>  <west_relay>, eg. \"tpad  on/off  on/off  on/off  on/off\""); 
    return CMD_ERR;
  }

  if( strncasecmp(arg[0],"ON",2) && strncasecmp(arg[0],"OFF",3) || 
      strncasecmp(arg[1],"ON",2) && strncasecmp(arg[1],"OFF",3) ||
      strncasecmp(arg[2],"ON",2) && strncasecmp(arg[2],"OFF",3) ||
      strncasecmp(arg[3],"ON",2) && strncasecmp(arg[3],"OFF",3) ) {
    strcpy(reply, "Usage: the arguments must be only 'on' / 'off'."); 
    return CMD_ERR;
  }

  for(i=0;i<4;i++) {

         if( !strncasecmp(arg[i],"ON" ,2) ) strcpy(strCmd, sys.rcmd_tcspad_set_on [i]);
    else if( !strncasecmp(arg[i],"OFF",3) ) strcpy(strCmd, sys.rcmd_tcspad_set_off[i]);

    nRtn = system(strCmd);

    if( nRtn!=0 ) {
      switch( WEXITSTATUS(nRtn) ) {
        case   1: strcpy(reply, "Invalid argument format for PC-TCS paddle control" ); break;
        case 127: strcpy(reply, "Invalid command line for PC-TCS paddle control"    ); break;
        case  28: strcpy(reply, "Failed to connect with the PC-TCS paddle relay"    ); break;
        case   7: strcpy(reply, "Connection refused by the PC-TCS paddle relay"     ); break;
        case   6: strcpy(reply, "Invalid IP address for the PC-TCS paddle relay"    ); break;
        default : strcpy(reply, "Failed to get status of the PC-TCS paddle relay"   ); break;
      }
      //sprintf(reply, "%s (ECMD string: \"%s\")", reply, strCmd);  // replaced as below at v0.9.4
      sprintf(cmsg, "STATUS: TCS Paddle control failure! (ECMD string: \"%s\")", strCmd);_dbgmsgout(cmsg);
      return CMD_ERR;
    }

    if( !strncasecmp(arg[i],"ON",2) ) sys.nston = ON;   // v0.7.6

  }

  if( !strncasecmp(arg[0],"OFF",3) && !strncasecmp(arg[1],"OFF",3) && 
      !strncasecmp(arg[2],"OFF",3) && !strncasecmp(arg[3],"OFF",3) ) {
    sys.nston = OFF;
  }
  //else {
  //  sys.nston = ON;  // v0.6.9
  //} // v0.7.2

  sprintf(reply,"TCS paddle set to %s", args);  // using replay for remote client

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// relay.drot - getting the dome rotation status, and update to system status
//

int
cmd_drot(char *args, MsgType msgtype, char *reply)   // v0.6.8
{
  //  sys.relay_dctrl_failnum = 0;
  //  sys.relay_dctrl_state_drot = RELAY_DROT_IDLE;
  //  return CMD_OK;
  //// cmd_drot() temporary disabled at v0.9.5, until applying new modified code at v0.9.6

  //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
  //
  //  int nRtn;
  //  char *pstr;
  //  char strCmd[STRLEN_CMD];
  //  char curl_buf[1024];
  //  FILE *curl_input;
  //
  //  sys.relay_dctrl_state_drot = RELAY_DROT_UNKNOWN;
  //
  //  strcpy(strCmd, sys.rcmd_drotin_get_stat);
  //  nRtn = system(strCmd);   //// using redirection to a file as output channel
  //
  //  if( nRtn!=0 ) {
  //    switch( WEXITSTATUS(nRtn) ) {
  //      case   1: strcpy(reply, "Invalid argument format for Getting the dome rotation status" ); break;
  //      case 127: strcpy(reply, "Invalid command line for Getting the dome rotation status"    ); break;
  //      case  28: strcpy(reply, "Failed to connect with the dome controller relay"             ); break;
  //      case   7: strcpy(reply, "Connection refused by the dome controller relay"              ); break;
  //      case   6: strcpy(reply, "Invalid IP address for the dome controller relay"             ); break;
  //      default : strcpy(reply, "Failed to get status of the dome controller relay"            ); break;
  //    }
  //    //sprintf(reply, "%s (ECMD string: \"%s\")", reply, strCmd);  // replaced as below at v0.9.4
  //    sprintf(cmsg, "STATUS: Failed to get dome rotation status from Dome control relay ! (ECMD string: \"%s\")", strCmd);_dbgmsgout(cmsg);
  //    return CMD_ERR;
  //  }
  //
  //  if( (curl_input=fopen(RCMD_GET_OUTPUT, "r")) == NULL ) {  // 0.7.8
  //    sprintf(reply, "Cannot open the output '%s' by curl to get status of dome rotation", RCMD_GET_REDIRECT);
  //    return CMD_ERR;
  //  }
  //  nRtn = fread(curl_buf, 1, 1024, curl_input);
  //  fclose(curl_input);   // for debugging about "Error 24" (v0.9.6)
  //
  //  if( nRtn < 0 ) {
  //    sprintf(reply, "Failed to read the output '%s' by curl to get status of dome rotation", RCMD_GET_REDIRECT);
  //    return CMD_ERR;
  //  }
  //  else if( nRtn < 60 ) {
  //    sprintf(reply, "Not enough data in output '%s' by curl to get status of dome rotation", RCMD_GET_REDIRECT);
  //    return CMD_ERR;
  //  }
  //
  //  if( (pstr=strstr(curl_buf,"<digitalInput1>")) == NULL ) {
  //    sprintf(reply, "No <digitalInput1> data in output '%s' by curl to get status of dome rotation", RCMD_GET_REDIRECT);
  //    return CMD_ERR;
  //  }
  //  nRtn = atoi(pstr+15);
  //  if( nRtn!=0 && nRtn!=1 ) {
  //    sprintf(reply, "Invaild value <digitalInput1> in output '%s' by curl to get status of dome rotation", RCMD_GET_REDIRECT);
  //    return CMD_ERR;
  //  }
  //
  //  sys.relay_dctrl_state_drot = nRtn;   // v0.9.4
  //  sprintf(reply,"DomeRotStatus=%s", nRtn==DOME_ROTATING?"ROTATING":nRtn==DOME_IDLE?"IDLE":"UNKNOWN" );  // v0.9.3
  //
  //// test code used before applying the Curl library, using system command and input via temporary file (until v0.9.4)
  //// this way making "sh: error while loading shared libraries: libtinfo.so.5: cannot open shared object file: Error 24"
  //// --> Update: The error was caused by missing fclose(). It was debugged v0.9.6. Anyway the code replaced with below codes.
  //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
  //
      int nDIn1, nDIn2;
      CURL *curl;
      CURLcode res;
      char curl_buf[XML_BUFFER_SIZE];
      char *pstr;

      sys.relay_dctrl_state_drot = RELAY_DROT_UNKNOWN;
      memset(curl_buf, 0x00, sizeof(curl_buf));

      curl = curl_easy_init();
      if (curl == NULL) {
        strcpy(reply, "Failed to initialize Curl ");
        return CMD_ERR;
      }

      curl_easy_setopt(curl, CURLOPT_URL, sys.rcmd_drotin_curlopt_url);  // "http://192.168.xx.163:8063/state.xml"
      curl_easy_setopt(curl, CURLOPT_TIMEOUT, 1);
      curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_data);
      curl_easy_setopt(curl, CURLOPT_WRITEDATA, curl_buf);

      res = curl_easy_perform(curl);
      //curl_easy_cleanup(curl); --> not sure if calling right here..

      if (res != CURLE_OK) {
        printf(reply, "Failed to get dome rotation status - Curl perform error (%s)\n", curl_easy_strerror(res));
        curl_easy_cleanup(curl);
        return CMD_ERR;
      }

      if( (pstr=strstr(curl_buf,"<digitalInput1>")) == NULL ) {
        strcpy(reply, "Failed to get dome rotation status - No <digitalInput1> in state.xml got via Curl");
        curl_easy_cleanup(curl);
        return CMD_ERR;
      }
      nDIn1 = atoi(pstr+15);
      if( nDIn1!=0 && nDIn1!=1 ) {
        strcpy(reply, "Failed to get dome rotation status - Invaild value of <digitalInput1> got via Curl");
        curl_easy_cleanup(curl);
        return CMD_ERR;
      }

      if( (pstr=strstr(curl_buf,"<digitalInput2>")) == NULL ) {
        strcpy(reply, "Failed to get dome rotation status - No <digitalInput2> in state.xml got via Curl");
        curl_easy_cleanup(curl);
        return CMD_ERR;
      }
      nDIn2 = atoi(pstr+15);
      if( nDIn2!=0 && nDIn2!=1 ) {
        strcpy(reply, "Failed to get dome rotation status - Invaild value of <digitalInput1> got via Curl");
        curl_easy_cleanup(curl);
        return CMD_ERR;
      }

      curl_easy_cleanup(curl);

      sys.relay_dctrl_state_drot = 1*nDIn1 + 2*nDIn2;   // v0.9.7
      switch(sys.relay_dctrl_state_drot) {
        case RELAY_DROT_IDLE   : strcpy(curl_buf,"IDLE   "); break;
        case RELAY_DROT_LEFT   : strcpy(curl_buf,"LEFT   "); break;
        case RELAY_DROT_RIGHT  : strcpy(curl_buf,"RIGHT  "); break;
        case RELAY_DROT_BOTH   : strcpy(curl_buf,"BOTH   "); break;
        case RELAY_DROT_UNKNOWN: strcpy(curl_buf,"UNKNOWN"); break;
        default                : strcpy(curl_buf,"IDLE   "); break;
      }
      sprintf(reply,"DomeRotStatus=%s", curl_buf);   // v0.9.7

  //
  //// modified code using easy Curl library (v0.9.6)
  //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

  sys.relay_dctrl_failnum = 0;   // v0.9.4

  return CMD_OK;
}

//// Curl 응답 데이터 처리 함수
size_t curl_write_data(void *ptr, size_t size, size_t nmemb, void *userdata) {
  char *buffer = (char *)userdata;
  size_t written = size * nmemb;
  memcpy(buffer, ptr, written);
  buffer[written] = '\0';
  return written;
}

//
// *** UTILITY COMMANDS BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// util.warning - activate the warning blinking process (flag on)
//                the warning blinking is off with any key input
//

int
cmd_warning(char *args, MsgType msgtype, char *reply)
{
  agent.flag_warning = 1;
  //agent.count_warning = 0;  -->  moved to init & reset routine
  strcpy(reply,"warning blinking activated");

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// util.msgout - a message string output & log
//               for operational availability or some logs required
//

int
cmd_msgout(char *args, MsgType msgtype, char *reply)
{
  int i, len = strlen(args);
  
  if( args[0]==0x22 ) {
    //strcpy(args, args+1);  // maybe error some compiler or some system
    for(i=0;i<len;i++) args[i] = args[i+1];
    for(i=len-2;i>=0;i--) if(args[i]==0x22) break;
    if(i>=0) {args[i] = 0x00;}
  }  
  //sprintf(reply, "(%s)", args);  return CMD_OK; //// for debugging

  GRNTEXT;strcat(args,"\n");_msgout(args);
  
  strcpy(reply,"message output completed");

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// util.sleep - sleep the process for the seconds specified in arg, 
//              whole process is blocked for input <sleep seconds>
//

int
cmd_sleep(char *args, MsgType msgtype, char *reply)
{
  //double dSec = atof(args);
  //int nMicroSec = (int)(dSec*1000000.0);

  //sprintf(cmsg,"STATUS: delay %.1f sec started\n", dSec);_msgout(cmsg);
  //fflush(stdout);

  //usleep(nMicroSec);

  ////sprintf(cmsg,"DONE: delay %.1f sec completed\n", dSec);_msgout(cmsg);
  ////return CMD_NOOP;
  
  //sprintf(reply,"delay %.1f sec completed", dSec);  // using replay for remote client
  //return CMD_OK;

  const int interval = 500000;  // =0.5s

  double dSec = atof(args);
  int total = (int)(dSec*1000000.0);
  int loopnum = total / interval;
  int remainder = total % interval;
  int i;

  if( remainder ) {
    printf("\r"); BLUTEXT;
    sprintf(cmsg,"STATUS: Sleep %.1f sec in progress - %.1f sec remain ", dSec, dSec);  // some space should be put at the end of string
    _msgout(cmsg); fflush(stdout);
    usleep(remainder);
  }
  
  for( i=0 ; i<loopnum ; i++ ) {
    printf("\r"); BLUTEXT; 
    sprintf(cmsg,"STATUS: Sleep %.1f sec in progress - %.1f sec remain ", dSec, (double)(total-remainder-interval*i)/1000000.0); 
    _msgout(cmsg); fflush(stdout);
  	usleep(interval);
  }  
  
  //  if( loopnum || remainder ) {
  //  	printf("\r"); BLUTEXT; 
  //    sprintf(cmsg,"STATUS: Sleep %.1f sec in progress - %.1f sec remain ", dSec, 0.0); 
  //    _msgout(cmsg); fflush(stdout);
  //  }
  //  --> meaningless since using carrage return and reply will be printed
  
  printf("\r                                                                              ");

  sprintf(reply,"Sleep %.1f sec completed", dSec);  // using replay for remote client
  
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// util.dtchk - move FITS data from /data to /data/YYYYDDMM and check for data transfer from ICS to DTS
//

int
cmd_dtchk(char *args, MsgType msgtype, char *reply)   // v0.5.1
{
  int nRtn, nDtDateChange;
  char strDir[STRLEN_ARG];
  char strCmd[STRLEN_CMD];
  smctime_t systime;
  struct timeval tv;  
  struct tm *gmt;

  if( strncasecmp(args,"LAST" ,4)==0 ) {
    
    gettimeofday(&tv,NULL);
    gmt = gmtime(&tv.tv_sec);
    
         if( strcasecmp(sys.telid, SYSCFG_TELID_CTIO)==0 ) nDtDateChange = SYSCFG_DTDATE_CHANGE_CTIO;
    else if( strcasecmp(sys.telid, SYSCFG_TELID_SAAO)==0 ) nDtDateChange = SYSCFG_DTDATE_CHANGE_SAAO;
    else if( strcasecmp(sys.telid, SYSCFG_TELID_SSO )==0 ) nDtDateChange = SYSCFG_DTDATE_CHANGE_SSO ;    
    if( gmt->tm_hour < nDtDateChange ) tv.tv_sec -= (3600*24);      
    //if( 1 ) tv.tv_sec -= (3600*24);  //// for debugging
    
    gmt = gmtime(&tv.tv_sec);
    sprintf(strDir, "%04d%02d%02d", gmt->tm_year+1900, (gmt->tm_mon)+1, gmt->tm_mday);
    
  }
  else if( strlen(args) ) {
    
    strcpy(strDir, args);
    
  }
  else {
    
    strcpy(reply, "Usage: dtchk 'last'/<yyyymmdd>"); 
    return CMD_ERR;
    
  }

  sprintf(strCmd, "/data/%s", strDir);
  //sprintf(strCmd, "./data/%s", strDir);  //// for debugging
  nRtn = access(strCmd, 0);
  if(nRtn) {
    nRtn = mkdir(strCmd, 0777);
    if(nRtn) {
      sprintf(reply,"Failed to make directory '%s'", args);
      return CMD_ERR;
    }  
  }
   
  sprintf(strCmd, " mv  /data/*.fits  /data/%s ", strDir);
  //sprintf(strCmd, " mv  ./data/*.fits  ./data/%s ", strDir);  //// for debugging

  //nRtn = cmd_ecmd(strCmd, EXEC, reply);
  //if( nRtn != CMD_OK ) return nRtn;
  
  nRtn = system(strCmd);
  if( nRtn!=0 ) {
    switch( WEXITSTATUS(nRtn) ) {
      case   1: break;  // syntex error or no such file or directory ..
      case 127: sprintf(reply, "Invalid command input (ECMD string: \"%s\")", strCmd); return CMD_ERR;
      default : sprintf(reply, "Failed to move file (ECMD string: \"%s\")"  , strCmd); return CMD_ERR;
    }
  }  

  sprintf(strCmd, " %s  %s ", ECMD_DTCHK, strDir);
  nRtn = cmd_ecmd(strCmd, EXEC, reply);
  if( nRtn != CMD_OK ) return nRtn;

  sprintf(reply,"Data transfer check complete for '%s' directory", strDir);  // using replay for remote client

  client.KeepGoing=0;  // quit after dtchk, added at v0.6.3

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// util.ecmd - external command execution on the shell
//

int
cmd_ecmd(char *args, MsgType msgtype, char *reply)   // v0.5.1
{
  if( strlen(args)==0 ) {
    strcpy(reply, "Usage: ecmd <command line to execute on the shell>"); 
    return CMD_ERR;
  }
  
  int nRtn, i;
  
  if( args[0]==0x22 ) {
    args[0] = 0x20;
    for( i=strlen(args)-1 ; i ; i-- ) if( args[i]==0x22 ) break;      
    if( i ) { args[i] = 0x20; args[i+1] = 0x00; }
    //else { strcpy(reply, "no '\"' symbol at the end of string"); return CMD_ERR; }   // removed for more flexible
  }

  nRtn = system(args);

  //////////////// for debugging
  //
  //  GRNTEXT;sprintf(cmsg, "DBGMSG: ECMD string: \"%s\"\n", args);_msgout(cmsg);
  //  GRNTEXT;sprintf(cmsg, "DBGMSG: Rtn = %d\n", nRtn);_msgout(cmsg);
  //  GRNTEXT;sprintf(cmsg, "DBGMSG: WIFEXITED(Rtn) = %d\n", WIFEXITED(nRtn));_msgout(cmsg);
  //  GRNTEXT;sprintf(cmsg, "DBGMSG: WEXITSTATUS(Rtn) = %d\n", WEXITSTATUS(nRtn));_msgout(cmsg);
  //
  ////////////////////////////////

  if( nRtn!=0 ) {
    switch( WEXITSTATUS(nRtn) ) {
      case   1: strcpy(reply, "Invalid argument format"     ); break;
      case 127: strcpy(reply, "Invalid command input"       ); break;
      default : strcpy(reply, "Failed to complete cmd proc" ); break;      
    }
    sprintf(reply, "%s (ECMD string: \"%s\")", reply, args);
    return CMD_ERR;
  }  

  strcpy(reply, "Extenal command excuted");
  
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// util.redisget - get a value from the redis server on newTCS (v0.9.3)
//

int
cmd_redisget(char *args, MsgType msgtype, char *reply)
{
  //// Argument input & Variable declaration

  if( strlen(args)==0 ) {
    strcpy(reply, "Usage: rget <key>"); 
    return CMD_ERR;
  }
  
  char key[64];
  char val[64];

  sscanf(args, "%s", key);

  //// Connect to server

  unsigned int j;
  redisContext *c;
  redisReply *rep;

  //c = redisConnectWithTimeout("127.0.0.1", 6379, sys.redis_timeout); // for local test
  c = redisConnectWithTimeout(sys.redis_host, sys.redis_port, sys.redis_timeout);
  if (c==NULL || c->err) {
    if (c) {
        sprintf(reply, "Redis connection error, %s", c->errstr);
        redisFree(c);
    } else {
        sprintf(reply, "Connection error, can't allocate redis context");
    }
    return CMD_ERR;
  }

  //// PING server

  //rep = (redisReply*)redisCommand(c,"PING");
  //strcpy(reply, rep->str);
  //freeReplyObject(rep);

  //// GET value from server

  rep = (redisReply*)redisCommand(c,"GET %s", key);
  if(rep->str==NULL) strcpy(val, "(nil)");
  else strncpy(val, rep->str, 64);
  freeReplyObject(rep);

  //// Free context structure

  redisFree(c);

  //// check value and reset parameters about redis dome status (v0.9.4)

  if( !strcmp(key,"dome_error") ) {                                                  // checking whether val is a number or not, 
    if(  ( val[0]!='-' && ( val[0]<0x30 || val[0]>0x39 ) ) ||                        // actually this is not necessary for ProcOsc()
         ( val[0]=='-' && ( val[1]<0x30 || val[1]>0x39 ) )  ) strcpy(val,"(nan)");   // as REDIS_DOMEROT_IDLE=0 on redis_domerot
    else sys.redis_failnum_domerot = 0;    // to reset and resume check with UpdateDomeStatus()
  }
  if( !strcmp(key,"SHUTTER") ) {                                                     // to check whether val is a number or not, 
    if(  ( val[0]!='-' && ( val[0]<0x30 || val[0]>0x39 ) ) ||                        // because not a number is converted 0, 
         ( val[0]=='-' && ( val[1]<0x30 || val[1]>0x39 ) )  ) strcpy(val,"(nan)");   // and it is considered shutter-moving status
    else sys.redis_failnum_domeshut = 0;   // to reset and resume check with UpdateDomeStatus()      // (REDIS_DOMESHUT_NEARPOS=0)
  }

  //// All done.

  sprintf(reply, "%s=%s", key, val);

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// util.redisset - set a value into the redis server on newTCS (v0.9.3)
//

int
cmd_redisset(char *args, MsgType msgtype, char *reply)
{
  //// Variable declaration & Argument input
  
  int rtn;
  char key[64];
  char val[64];

  rtn = sscanf(args, "%s %s", key, val);

  if( rtn < 2 ) {
    strcpy(reply, "Usage: rset <key> <value>"); 
    return CMD_ERR;
  }

  //// Connect to server

  unsigned int j;
  redisContext *c;
  redisReply *rep;

  c = redisConnectWithTimeout(sys.redis_host, sys.redis_port, sys.redis_timeout);
  if (c==NULL || c->err) {
    if (c) {
        sprintf(reply, "Redis Connection error, %s", c->errstr);
        redisFree(c);
    } else {
        sprintf(reply, "Connection error, can't allocate redis context");
    }
    return CMD_ERR;
  }

  //// SET value from server

  rep = (redisReply*)redisCommand(c,"SET %s %s", key, val);
  if( rep->str==NULL ) {
    sprintf(reply, "Failed to SET %s %s (Rep=null)", key, val);
    freeReplyObject(rep);
    redisFree(c);
    return CMD_ERR;
  }
  if( strcmp(rep->str,"OK") ) {
    sprintf(reply, "Failed to SET %s %s (Rep=%s)", key, val, rep->str);
    freeReplyObject(rep);
    redisFree(c);
    return CMD_ERR;
  }
  freeReplyObject(rep);

  //// GET value from server

  rep = (redisReply*)redisCommand(c,"GET %s", key);
  if(rep->str==NULL) strcpy(val, "(nil)");
  else strncpy(val, rep->str, 64);
  freeReplyObject(rep);

  //// Free context structure

  redisFree(c);

  //// All done.

  sprintf(reply, "OK, %s=%s", key, val);
  
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// util.redislocal - set redis host name to loopback ip addr (v0.9.3)
//

int
cmd_redislocal(char *args, MsgType msgtype, char *reply)
{
  static char redis_host[64];

  if(strcmp(sys.redis_host,"127.0.0.1")) {
    strcpy(redis_host, sys.redis_host);
    strcpy(sys.redis_host, "127.0.0.1");
  }
  else {
    strcpy(sys.redis_host, redis_host);
  }
  
  sprintf(reply, "Redis hostname = %s", sys.redis_host);
  
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// util.test - test function (v0.9.4)
//

int
cmd_test(char *args, MsgType msgtype, char *reply)
{

  ////// test for WriteObsStatus()
  int rtn;
  rtn = WriteObsStatus("../Test.ObsStatus.txt");
  if(rtn<0) {
    strcpy(reply, "Failed to write Test.ObsStatus.txt");
    return CMD_ERR;
  }
  strcpy(reply, "Wrote Test.ObsStatus.txt");
  return CMD_OK;

  ////// test for Exposure Information
  //
  //  InitExpInfo(&expinfo);
  //
  //  char *pstr;
  //  char *buf = "Wrote LASTFILE=/mnt/ICSData/KMTNk.20231002.002183.fits RATE=1111199 KB/sec EXPSTATUS=ERASE";
  //  sys.count_wrote = 3;  //// for test
  //  {
  //      if( strstr(buf,"Wrote")!=NULL ) {  // this msg is from G.CB as well // FITS save status monitoring, moved here at v0.2.7
  //        if( ++sys.count_wrote >= 4 ) {
  //          sys.status_fitssaved = 1;
  //          osc.lastidx_fitssaved = osc.lastidx_expcompleted;   // for 'olast' command, v0.9.4
  //
  //          pstr = strstr(buf,"KMTN");
  //          if(pstr==NULL) {
  //            strcpy(expinfo.strFitsNum, "00000000.000000");
  //          }
  //          else {
  //            strncpy(expinfo.strFitsNum, pstr+6, 15);
  //          }
  //        }
  //      }
  //  }
  //  buf = "EXPNUM  Filename=20240628.028004 EXPSTATUS=ERASE";
  //  {   if(0) {}   // remove this line
  //
  //      else if( ( pstr = strstr(buf,"EXPNUM  Filename=") )!=NULL ) {   // v1.0.1
  //        strncpy(expinfo.strNextNum, pstr+17, 15);
  //      }
  //
  //      strcpy(expinfo.strCurNum, expinfo.strNextNum);  // put this next to Shutter=Open or EXPSTATUS=INITIALIZING
  //      //strcpy(expinfo.strNextNum, "00000000.000000");  <-- not necessary for function
  //  }
  //
  //  strcpy(reply, GetExpInfo());
  //  return CMD_OK;
  //

  ////// test for UpdateDomeStatus()
  //  if(sys.camstatus==CAMSTATUS_PREP_I) sys.camstatus = CAMSTATUS_CHECK ;
  //  else sys.camstatus = CAMSTATUS_PREP_I;
  //  osc.flag_process = 1; 
  //  UpdateDomeStatus(&sys, NULL);
  //  osc.flag_process = 0;
  //

  ////// test for atoi()
  //  sprintf(reply, "'%s' --> %d\n", args, atoi(args));
  //  return CMD_OK;  
  //

  strcpy(reply, "Test finished");
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// util.noop - no operation and response, for dummy command line in osc (v0.5.2)
//

int
cmd_noop(char *args, MsgType msgtype, char *reply) {

  osc.flag_responseok = 1;   // added at v0.6.0 for commanding in the script, 
                             // since this removed in OscCommand() to debug the serial command before responseok

  return CMD_NOOP;
}

//------------------------------------------------------------------------------
//
// util.tick
//

int
cmd_tick(char *args, MsgType msgtype, char *reply)    // TCSAgent v1.4.4
{
  int rtn;
  int arg;
  static int idx=-1;
  static smctime_t ut;
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
  //
  //tick_prev = tick_curr;
  //
  //return CMD_NOOP;

  sprintf(reply, " %04d-%02d-%02dT%02d:%02d:%06.3f    %04d %6.1f %6.1f", 
                   ut.year, ut.month, ut.day, ut.hour, ut.min, ut.sec,
                   idx, tick_curr-tick_zero, tick_curr-tick_prev);

  tick_prev = tick_curr;
  
  return CMD_OK;

  USAGE:
    strcpy(reply, "Usage: 'tick 0' = reset / 'tick' = +1 step / 'tick <n>' = set index");
    return CMD_ERR;
}

//------------------------------------------------------------------------------
//
// util.getut - get UT date & time
//

int
cmd_getut(char *args, MsgType msgtype, char *reply)
{
  static smctime_t ut;
  GetUTCDateTime(&ut);
  sprintf(reply, "%4d-%02d-%02dT%02d:%02d:%06.3f (%d seconds since the epoch)", 
                  ut.year, ut.month, ut.day, ut.hour, ut.min, ut.sec, ut.secse);
  //sprintf(reply, "%s\n  DEBUG: %d\n  DEBUG: %u\n  DEBUG: %f", reply, ut.secse, (UINT)time(NULL), SysTimestamp());
  return CMD_OK;  
}

//------------------------------------------------------------------------------
//
// util.getjd - get JD from UT string
//

int
cmd_getjd(char *args, MsgType msgtype, char *reply)
{
  int n, len;
  double dJD;
  smctime_t ut;
  char strUT[OSC_MAX_ARGIN];

  len = strlen(args);

  if( len==0 ) {
    GetUTCDateTime(&ut);
  }
  else {
    strcpy(strUT, args);
    if( strUT[0]<0x30 || strUT[0]>0x39 ) {
      strcpy(reply, "Usage: getjd (<ut string>)"
                    " // note: symbolic characters can be alternated with a space"
                    " // e.g. \"getjd\""
                    ", \"getjd 2020-01-23T01:23\""
                    ", \"getjd 2020 01 23 01 23\""
                    ", \"getjd 2020-01-23T01:23:45\""
                    ", \"getjd 2020 01 23 01 23 45\"");
      return CMD_ERR;

    }
    else {      
      for( n=0 ; n<len ; n++ ) if( strUT[n]<0x30 || strUT[n]>0x39 ) strUT[n] = 0x20;   // to replace simbolic characters with a space      
      n = sscanf(strUT, "%d %d %d %d %d %lf", &ut.year, &ut.month, &ut.day, &ut.hour, &ut.min, &ut.sec);

      if(n==5) ut.sec = 0.0;
      if( n<5 || ut.year<0 || ut.year>9999 || ut.month<1 || ut.month>12 || ut.day<1   || ut.day> 31 
              || ut.hour<0 || ut.hour>23   || ut.min  <0 || ut.min  >59 || ut.sec<0.0 || ut.sec>=60.0 ) {
        strcpy(reply, "Invalid UT string (format: \"2020-01-23T01:23\" or \"2020-01-23T01:23:45\", "
                      "symbolic characters can be alternated with a space, e.g. \"2020 01 23 01 23 45\")");
        return CMD_ERR;
      }
    }
  }

  sprintf(strUT, "%04d-%02d-%02dT%02d:%02d:%02d", ut.year, ut.month, ut.day, ut.hour, ut.min, (int)ut.sec);

  dJD = GetJd(ut);

  sprintf(reply, "UT=%s  JD=%.5f", strUT, dJD);

  return CMD_OK;  
}

//------------------------------------------------------------------------------
//
// util.getlst - get local sidereal time
//

int
cmd_getlst(char *args, MsgType msgtype, char *reply)
{
  int n, len;
  double dJD;
  smctime_t ut;
  char strUT[OSC_MAX_ARGIN];

  int nLST_h, nLST_m;
  double dLST_s, dLST;

  len = strlen(args);

  if( len==0 ) {
    GetUTCDateTime(&ut);
  }
  else {
    strcpy(strUT, args);
    if( strUT[0]<0x30 || strUT[0]>0x39 ) {
      strcpy(reply, "Usage: getlst (<ut string>)"
                    " // note: symbolic characters can be alternated with a space"
                    " // e.g. \"getlst\""
                    ", \"getlst 2020-01-23T01:23\""
                    ", \"getlst 2020 01 23 01 23\""
                    ", \"getlst 2020-01-23T01:23:45\""
                    ", \"getlst 2020 01 23 01 23 45\"");
      return CMD_ERR;

    }
    else {      
      for( n=0 ; n<len ; n++ ) if( strUT[n]<0x30 || strUT[n]>0x39 ) strUT[n] = 0x20;   // to replace simbolic characters with a space      
      n = sscanf(strUT, "%d %d %d %d %d %lf", &ut.year, &ut.month, &ut.day, &ut.hour, &ut.min, &ut.sec);

      if(n==5) ut.sec = 0.0;
      if( n<5 || ut.year<0 || ut.year>9999 || ut.month<1 || ut.month>12 || ut.day<1   || ut.day> 31 
              || ut.hour<0 || ut.hour>23   || ut.min  <0 || ut.min  >59 || ut.sec<0.0 || ut.sec>=60.0 ) {
        strcpy(reply, "Invalid UT string (format: \"2020-01-23T01:23\" or \"2020-01-23T01:23:45\", "
                      "symbolic characters can be alternated with a space, e.g. \"2020 01 23 01 23 45\")");
        return CMD_ERR;
      }
    }
  }

  sprintf(strUT, "%04d-%02d-%02dT%02d:%02d:%02d", ut.year, ut.month, ut.day, ut.hour, ut.min, (int)ut.sec);

  dJD = GetJd(ut);
  dLST = GetGst(dJD) - sys.tcs_longitude/15.0;  // west longitude
  if(dLST<0.0) dLST += 24.0;
  trans1060(dLST, &nLST_h, &nLST_m, &dLST_s, 2);

  //sprintf(reply, "UT=%s  LST=%02d:%02d:%05.2f  LST_H=%.4f", strUT, nLST_h, nLST_m, dLST_s, dLST);
  sprintf(reply, "UT=%s  LST=%02d:%02d:%02d  LST_H=%.4f", strUT, nLST_h, nLST_m, (int)dLST_s, dLST);

  return CMD_OK;  
}

//------------------------------------------------------------------------------
//
// util.getalt - getting altitude, azimuth, hour angle, airmass from ra, dec, (ut) (v0.8.9)
//

int
cmd_getalt(char *args, MsgType msgtype, char *reply)
{
  int n, len;
  double dJD, dLST;
  smctime_t ut;
  char strBuf[OSC_MAX_ARGIN];
  char strUT[32];

  int nHA_h, nHA_m;
  double dHA_s, dHA;
  char cHA_dir;
  char strHA[16];
  int nRA_h, nRA_m;
  double dRA_s, dRA;
  char strRA[16];
  int nDEC_d, nDEC_m;
  double dDEC_s, dDEC;
  char cDEC_dir;
  char strDEC[16];
  double dAlt, dAz, dAir;
  char strAlt[16], strAz[16];
  int nDeg, nMin;
  double dSec;
  char cDir;

  int flag_printall=0;
  int flag_noconvaz=0;
  memset(&ut,0,sizeof(smctime_t));

  if( strcasestr(args,"ALL") ) flag_printall = 1;
  if( strcasestr(args,"NC") ) flag_noconvaz = 1;

  strcpy(strBuf, args);
  len = strlen(strBuf);
  //if( len==0 || ( ( strBuf[0]<0x30 || strBuf[0]>0x39 ) && strBuf[0]!='+' && strBuf[0]!='-' ) ) goto USAGE;
  if( len==0 ) goto USAGE;
  for( n=0 ; n<len ; n++ ) if( ( strBuf[n]<0x30 || strBuf[n]>0x39 ) && strBuf[n]!='+' && strBuf[n]!='-' && strBuf[n]!='.' ) strBuf[n] = 0x20;   // to replace simbolic characters with a space, except dot '.'
  n = sscanf(strBuf, "%d %d %lf %d %d %lf %d %d %d %d %d %lf", &nRA_h, &nRA_m, &dRA_s, &nDEC_d, &nDEC_m, &dDEC_s, &ut.year, &ut.month, &ut.day, &ut.hour, &ut.min, &ut.sec);
  if( n<6 ) goto USAGE;

  ut.year=abs(ut.year); ut.month=abs(ut.month); ut.day=abs(ut.day);
  ut.hour=abs(ut.hour); ut.min=abs(ut.min); ut.sec=fabs(ut.sec);

  dRA = (double)abs(nRA_h) + (double)nRA_m/60.0 + dRA_s/3600.0;
  if( nRA_h<0 ) dRA *= -1.0;
  while( dRA<0.0 ) dRA += 24.0;
  while( dRA>=24.0 ) dRA -= 24.0;
  trans1060(dRA, &nRA_h, &nRA_m, &dRA_s, 3);
  sprintf(strRA, "%02d:%02d:%06.3f", nRA_h, nRA_m, dRA_s);

  dDEC = (double)abs(nDEC_d) + (double)nDEC_m/60.0 + dDEC_s/3600.0;
  if( nDEC_d<0 ) dDEC *= -1.0;
  if( dDEC<-90.0 || dDEC>+90.0 ) {
    strcpy(reply, "Out of range, Declination input should be (-90<Dec<+90)");
    return CMD_ERR;
  }
  cDEC_dir = trans1060(dDEC, &nDEC_d, &nDEC_m, &dDEC_s, 2);
  sprintf(strDEC, "%c%02d:%02d:%06.2f", cDEC_dir, nDEC_d, nDEC_m, dDEC_s);

  if( n==6 ) {
    GetUTCDateTime(&ut);
  }
  else {
    if( ut.year<0 || ut.year>9999 || ut.month<1 || ut.month>12 || ut.day<1   || ut.day> 31 || 
        ut.hour<0 || ut.hour>23   || ut.min  <0 || ut.min  >59 || ut.sec<0.0 || ut.sec>=60.0 ) {
        strcpy(reply, "Invalid UT string (format: \"2020-01-23T01:23\" or \"2020-01-23T01:23:45\", "
                      "symbolic characters can be alternated with a space, e.g. \"2020 01 23 01 23 45\")");
        return CMD_ERR;
    }
  }

  sprintf(strUT, "%04d-%02d-%02dT%02d:%02d:%02d", ut.year, ut.month, ut.day, ut.hour, ut.min, (int)ut.sec);

  dJD = GetJd(ut);
  dLST = GetGst(dJD) - sys.tcs_longitude/15.0;  // west longitude
  if(dLST<0.0) dLST += 24.0;

  dHA = dLST - dRA;
  if( dHA<-12.0 ) dHA += 24.0;
  if( dHA>=12.0 ) dHA -= 24.0;
  cHA_dir = trans1060(dHA, &nHA_h, &nHA_m, &dHA_s, 0);
  sprintf(strHA, "%c%02d:%02d:%02.0f", cHA_dir, nHA_h, nHA_m, dHA_s);

  GetAltAzmAir(dHA, dDEC, sys.tcs_latitude, &dAlt, &dAz, &dAir);
  if(!flag_noconvaz) dAz = 180.0 - dAz;  // converting Az to PC-TCS on the southern hemisphere

  cDir = trans1060(dAlt, &nDeg, &nMin, &dSec, 0);
  sprintf(strAlt, "%c%02d:%02d:%02d", cDir, nDeg, nMin, (int)dSec);
  cDir = trans1060(dAz, &nDeg, &nMin, &dSec, 0);
  sprintf(strAz, "%c%02d:%02d:%02d", cDir, nDeg, nMin, (int)dSec);

  if(flag_printall) sprintf(reply, "UT=%s  RA=%s (%.7f)  Dec=%s (%.6f)  Alt=%.2f (%s)  Az=%.2f (%s)  HA=%s (%.4f)  Airmass=%.5f  JD=%.5f  LST_H=%.4f", 
                                    strUT, strRA, dRA, strDEC, dDEC, dAlt, strAlt, dAz, strAz, strHA, dHA, dAir, dJD, dLST);
  else              sprintf(reply, "UT=%s  RA=%s  Dec=%s  Alt=%.2f  Az=%.2f  HA=%s  Airmass=%.5f", 
                                    strUT, strRA, strDEC, dAlt, dAz, strHA, dAir);

  return CMD_OK;

  USAGE:

  strcpy(reply, "Usage: getalt <ra> <dec> (<ut string>)"
                " // note: symbolic characters can be alternated with a space"
                " // e.g. \"getalt  12:34:56.78  -12:34:56.7\""
                ", \"getalt  12:34:56.78  -12:34:56.7  2020-01-23T01:23\""
                ", \"getalt  12:34:56.78  -12:34:56.7  2020-01-23T01:23:45\""
                ", \"getalt  12 34 56.78  -12 34 56.7  2020 01 23 01 23 45\"");
  return CMD_ERR;

}

//
// *** SCRIPT OBSERVATION COMMANDS BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// osc.script - loading or query & display the observation script
//

int
cmd_oscscript(char *args, MsgType msgtype, char *reply)
{
  int rtn, i, nCmd, nExp;
  char path[STRLEN_FILE];
  char strProjID[OSC_MAX_PROJID+1];  // added at v0.6.4
  //char strLabel[OSC_MAX_ARGIN];
  //char strLabel[OSC_MAX_LABEL];  // modified at v0.5.0
  char strLabel[OSC_MAX_LABEL+1];  // modified at v0.6.4
  //char strObject[OSC_MAX_ARGIN];
  //char strObject[OSC_MAX_OBJECT];  // modified at v0.5.0
  char strObject[OSC_MAX_OBJECT+1];  // modified at v0.6.4
  double ha, alt;

  // input & check args

  rtn = sscanf(args, "%s", path);

  if(rtn<1) {  // query the observaion script loaded on memory

    if(osc.linenum<=0) {
      strcpy(reply, "No observation script data loaded");
      return CMD_OK;
    }

    agent.isBlockTimeTag = 1; // TimeTag disabling added at v0.5.0

    if( msgtype == EXEC ) {  // display all the data on console

      //sprintf(cmsg, "\n");_msgout(cmsg);
      sprintf(cmsg, "----------------------------------------------------------------------------------------------------------------------------------------------------------------------\n");_msgout(cmsg);
      sprintf(cmsg, "  Observation Script - '%s'\n", osc.filename);_msgout(cmsg);
      sprintf(cmsg, "----------------------------------------------------------------------------------------------------------------------------------------------------------------------\n");_msgout(cmsg);

      nCmd = nExp = 0;

      for( i=0 ; i<osc.linenum ; i++ ) {

        if( osc.line[i].type == OSC_TYPE_CMD ) {

            sprintf(cmsg, "  LINE#%04d  CMD#%04d  +%s  %s\n", 
                           (i+1), ++nCmd, osc.line[i].cmd, osc.line[i].arg);
            _msgout(cmsg);

        }

        else if( osc.line[i].type == OSC_TYPE_EXP ) {
          
            //  
            //  strcpy(strLabel, osc.line[i].label);
            //  osc.max_label_length = MIN(osc.max_label_length,OSC_MAX_DPLAB);
            //  if( strlen(strLabel) > OSC_MAX_DPLAB ) {
            //      //strLabel[OSC_MAX_DPLAB-2] = '.';
            //      //strLabel[OSC_MAX_DPLAB-1] = '.';
            //      strLabel[OSC_MAX_DPLAB-1] = '~';
            //      strLabel[OSC_MAX_DPLAB-0] = NUL;
            //  }
            //  else {
            //     strncat(strLabel, CONST_STR_SPACE, MAX(osc.max_label_length-strlen(strLabel),0));
            //  }
            //  
            //  strcpy(strObject, osc.line[i].object);
            //  if( strlen(strObject) > OSC_MAX_DPOBJ ) {
            //      //strObject[OSC_MAX_DPOBJ-2] = '.';
            //      //strObject[OSC_MAX_DPOBJ-1] = '.';
            //      strObject[OSC_MAX_DPOBJ-1] = '~';
            //      strObject[OSC_MAX_DPOBJ-0] = NUL;
            //  }
            //   
            //  sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s %-12s %-12s %c  %-8s %-16s %-2s %6.1f  %-19s %4d   # %s\n",  // OSC_MAX_DPOBJ = 16
            //                 (i+1), ++nExp, strLabel, 
            //                 osc.line[i].ra, osc.line[i].dec, osc.line[i].copt, 
            //                 osc.line[i].imgtyp, strObject, 
            //                 osc.line[i].filter, osc.line[i].exptime, 
            //                 osc.line[i].utobs, osc.line[i].uttol, 
            //                 osc.line[i].flag_movedisable?"Move Disabled":"Move Enabled");
            //  _msgout(cmsg);
            //
            //// modified as below at v0.5.0


            ha = sys.ha_h + ( sys.ra_h - osc.line[i].ra_h );
            if(ha<-12.0) ha+=24.0;  if(ha>=+12.0) ha-=24.0;
            alt = GetAltitude(ha, osc.line[i].dec_d, sys.tcs_latitude);
            
            strcpy( strProjID, osc.line[i].projid );   // v0.6.4
            strcpy( strLabel , osc.line[i].label  );
            strcpy( strObject, osc.line[i].object );
            strncat( strProjID, CONST_STR_SPACE, MAX(osc.max_projid_length-strlen(strProjID),0) );   // v0.6.4
            strncat( strLabel , CONST_STR_SPACE, MAX(osc.max_label_length -strlen(strLabel ),0) );
            strncat( strObject, CONST_STR_SPACE, MAX(osc.max_object_length-strlen(strObject),0) );

          //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %-12s %-12s %c  %-8s %s %-2s %6.1f  %7s %4d   ALT %5.2f  HA %+.2f\n",
          //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %c  %-8s %s  %-2s %6.1f  %7s %4d   ALT %5.2f  HA %+.2f\n",  // projid added at v0.6.4
          //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %s  %-2s %6.1f  %7s %4d  %+10.5f %+10.5f  %u %d %d  ALT %5.2f  HA %+.2f\n",  //// for DBG
          //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %s  %-2s %6.1f  %7s %4d  %+10.5f %+10.5f  %u   ALT %5.2f  HA %+.2f\n",  //// for DBG
            sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %s  %-2s %6.1f  %7s %4d  %+10.5f %+10.5f   ALT %5.2f  HA %+.2f\n",  // velra/dec added at v0.6.9
                             (i+1), ++nExp, strProjID, strLabel,  
                              osc.line[i].ra, osc.line[i].dec, osc.line[i].copt, 
                              osc.line[i].imgtyp, strObject, 
                              osc.line[i].filter, osc.line[i].exptime, 
                              osc.line[i].utobs, osc.line[i].uttol, 
                              osc.line[i].velra, osc.line[i].veldec, // v0.6.9
                            //osc.line[i].secobs,   //// for DBG
                            //fabs(osc.line[i].velra)<0.000001?0:1, fabs(osc.line[i].velra)<0.000001?0:1,   //// for DBG
                              alt, ha);  // Move disabled flag removed, Alt & HA added, modified for Label & Object field adjusted at v0.5.0                              
            _msgout(cmsg);

        }// end of if( osc.line[nLine].type == OSC_TYPE_CMD ) {..} else if( osc.line[nLine].type == OSC_TYPE_EXP ) {..}

      }// end of for( i=0 ; i<osc.linenum ; i++ ) {..}

      //  sprintf(cmsg, "--------------------------------------------------------------------------------------------------------------------------------------\n");_msgout(cmsg);       
      //  sprintf(strLabel, "observation script data %d lines including %d commands and %d exposures loaded from '%s'", osc.linenum, osc.cmdnum, osc.expnum, osc.filename);
      //  //sprintf(cmsg, "%134s\n\n", strLabel);_msgout(cmsg);
      //  sprintf(cmsg, "  %s\n\n", strLabel);_msgout(cmsg);
      //////// modified for debugging the "incorrect command data number in the osc data" error at v0.5.3

      //  sprintf(cmsg, "--------------------------------------------------------------------------------------------------------------------------------------\n");_msgout(cmsg);       
      //  sprintf(cmsg, "observation script data %d lines including %d commands and %d exposures loaded from '%s'", osc.linenum, osc.cmdnum, osc.expnum, osc.filename);
      //  //sprintf(cmsg, "%134s\n\n", cmsg);_msgout(cmsg);
      //  sprintf(cmsg, "  %s\n\n", cmsg);_msgout(cmsg);
      //////// this is also not working properly.. replaced with belows
      
      sprintf(cmsg, "----------------------------------------------------------------------------------------------------------------------------------------------------------------------\n");_msgout(cmsg);
      sprintf(cmsg, "  observation script data %d lines including %d commands and %d exposures loaded from '%s'\n\n", osc.linenum, osc.cmdnum, osc.expnum, osc.filename);_msgout(cmsg);
      
      agent.isBlockTimeTag = 0;   // TimeTag disabling added at v0.5.0

      if( nCmd != osc.cmdnum ) {
        strcpy(reply, "incorrect command line number in the osc data");
        return CMD_ERR;
      } 
      else if( nExp != osc.expnum ) {
        strcpy(reply, "incorrect exposure line number in the osc data");
        return CMD_ERR;
      }
      else {
        return CMD_NOOP;
      }

    }// end of if( msgtype == EXEC ) {..}

    else {  // response the data number and the file name to ISIS node

      sprintf(reply, "observation script data %d lines including %d commands and %d exposures loaded from '%s'", 
                      osc.linenum, osc.cmdnum, osc.expnum, osc.filename);

    }

  }// end of if(rtn<1) {..}

  else {  // Loading an observation script from input filepath

    ////sprintf(cmsg, "DBG: path='%s' before correction\n", path);_msgout(cmsg);//_dbgmsgout(cmsg);

    if( path[0]!='/' && path[0]!='.' && path[0]!='~' )  { // v0.8.0
      ////sprintf(path, "%s/%s", DEFAULT_OSCDIR, path);  // v0.8.0  <-- bug..
      strcpy(cmsg, DEFAULT_OSCDIR);
      strcat(cmsg, path);
      strcpy(path, cmsg);  // v0.8.2
    }

    sprintf(cmsg, "DBG: path='%s' after correction\n", path);_dbgmsgout(cmsg);  // _msgout() replaced with _dbgmsgout() at v0.9.2

    rtn = LoadObsScript(&osc, path, reply);

    if(rtn<0) return CMD_ERR;  // v0.6.4

  }

  return CMD_OK;

}

//------------------------------------------------------------------------------
//
// osc.line - qury a script/cmd/exp line
//
//     - codes are modified overall with using GetOscLine() sub-routine function 
//       for option to print first few lines at v0.6.2
//

int
cmd_oscline(char *args, MsgType msgtype, char *reply)
{

  if(osc.linenum<=0) {
    strcpy(reply, "No observation script data loaded");
    return CMD_OK;
  }

  int i, option, nLineNum, nLines, utin=0;
  char strUT[OSC_MAX_ARGIN];

  //
  // Arguments input & check
  //

  if( strlen(args)==0 ) {
    strcpy(reply, "Usage: oline (cmd/exp) <line #>/-<lines> (<ut string>)"
                  " // e.g. \"oline 10\""
                  ", \"oline -10\""
                  ", \"oline cmd 10\""
                  ", \"oline exp 10\""
                  ", \"oline 10 2020-01-23T01:23:45\""
                  ", \"oline 10 2020 01 23 01 23 45\""
                  ", \"oline exp -10 2020-01-23T01:23:45\""
                  " // 'cmd'/'exp' can be alternated with a abbreviation 'c'/'e'");
    return CMD_ERR;
  }

       if( strncasecmp(args,"-CMD",4)==0 || strncasecmp(args,"-EXP",4)==0 ) nLineNum = atoi(args+4);
  else if( strncasecmp(args,"CMD" ,3)==0 || strncasecmp(args,"EXP" ,3)==0 ) nLineNum = atoi(args+3);
  else if( strncasecmp(args,"-C"  ,2)==0 || strncasecmp(args,"-E"  ,2)==0 ) nLineNum = atoi(args+2);
  else if( strncasecmp(args,"C"   ,1)==0 || strncasecmp(args,"E"   ,1)==0 ) nLineNum = atoi(args+1);
  else                                                                      nLineNum = atoi(args+0);

  if( nLineNum==0 ) {
    strcpy(reply, "Invalid format or line number");
    return CMD_ERR;
  }

  if( nLineNum<0 ) option = 1;  // multiple lines print with fixed field
  else option = 0;  // a single line print with fitted(minimized) field

  //
  // Command line printing
  //

  if( strncasecmp(args,"CMD",3)==0 || strncasecmp(args,"-CMD",4)==0 || 
      strncasecmp(args,"C"  ,1)==0 || strncasecmp(args,"-C"  ,2)==0 ) {

    if( osc.cmdnum<=0 ) {
      strcpy(reply, "No command line in the script data loaded");
      return CMD_OK;
    }

    if( nLineNum>osc.cmdnum ) { 
      sprintf(reply, "Invalid line number, command lines are %d ", osc.cmdnum);
      return CMD_ERR;
    }

    if( nLineNum<0 ) nLines = MIN( (nLineNum*-1), osc.cmdnum );
    else nLines = nLineNum;

    for(i=0;i<osc.linenum;i++) {
      
      if(osc.line[i].type==OSC_TYPE_CMD) {

        if(osc.line[i].idx<nLineNum) continue;
        if(osc.line[i].idx>nLines) break;

        if( GetOscLine( (i+1), option, NULL, reply ) < 0 ) return CMD_ERR;

        if( nLineNum<0 ) {
          strcpy(cmsg, reply); strcat(cmsg, "\n");
          agent.isBlockTimeTag=1; _msgout(cmsg); agent.isBlockTimeTag=0;
        }

      }
      
    }

    if( nLineNum<0 ) 
      sprintf(reply, "First %d of %d command lines are printed.", nLines, osc.cmdnum);

  }

  //
  // Exposure line printing
  //

  else if( strncasecmp(args,"EXP",3)==0 || strncasecmp(args,"-EXP",4)==0 || 
           strncasecmp(args,"E"  ,1)==0 || strncasecmp(args,"-E"  ,2)==0  ) {

    if( osc.expnum<=0 ) {
      strcpy(reply, "No exposure line in the script data loaded");
      return CMD_OK;
    }

    if( nLineNum>osc.expnum ) { 
      sprintf(reply, "Invalid line number, exposure lines are %d", osc.expnum);
      return CMD_ERR;
    }    

    if( nLineNum<0 ) nLines = MIN( (nLineNum*-1), osc.expnum );
    else nLines = nLineNum;

    //i = sscanf(args, "%*s %*s %[^\n]", strUT);
    //if(i<0) strUT[0] = NULL;
    strUT[0]=NULL; sscanf(args, "%*s %*s %[^\n]", strUT);
    //sprintf(reply, "    Rtn = %2d    strUT=\"%s\"", i, strUT); return CMD_OK;
    
    for(i=0;i<osc.linenum;i++) {
      
      if(osc.line[i].type==OSC_TYPE_EXP) {

        if(osc.line[i].idx<nLineNum) continue;
        if(osc.line[i].idx>nLines) break;

        if( GetOscLine( (i+1), option, strUT, reply ) < 0 ) return CMD_ERR;

        if( nLineNum<0 ) {
          strcpy(cmsg, reply); strcat(cmsg, "\n");
          agent.isBlockTimeTag=1; _msgout(cmsg); agent.isBlockTimeTag=0;
        }

      }
      
    }

    if( nLineNum<0 ) {
        if( strUT[0]==NULL )
          sprintf(reply, "First %d of %d exposure lines are printed with current Alt & HA.", nLines, osc.expnum);
        else
          sprintf(reply, "First %d of %d exposure lines are printed with Alt & HA at UTC %s.", nLines, osc.expnum, strUT);
    }

  }

  //
  // Script line printing
  //

  else {

    if( nLineNum>osc.linenum ) { 
      sprintf(reply, "Invalid line number, script lines are %d", osc.linenum);
      return CMD_ERR;
    }    

    if( nLineNum<0 ) nLines = MIN( (nLineNum*-1), osc.linenum );
    else nLines = nLineNum;

    //i = sscanf(args, "%*s %[^\n]", strUT);
    //if(i<0) strUT[0] = NULL;
    strUT[0]=NULL; sscanf(args, "%*s %[^\n]", strUT);
    //sprintf(reply, "    Rtn = %2d    strUT=\"%s\"", i, strUT); return CMD_OK;
    
    for(i=0;i<osc.linenum;i++) {

      if((i+1)<nLineNum) continue;
      if((i+1)>nLines) break;

      if( osc.line[i].type==OSC_TYPE_CMD ) {
        if( GetOscLine( (i+1), option, NULL, reply ) < 0 ) return CMD_ERR;
      }
      else if( osc.line[i].type==OSC_TYPE_EXP ) {
        if( GetOscLine( (i+1), option, strUT, reply ) < 0 ) return CMD_ERR;
      }
      else {
        sprintf(reply, "Invalid script line index, #%d line type is indefinite.", (i+1));
        return CMD_ERR;
      }
      
      if( nLineNum<0 ) {
        strcpy(cmsg, reply); strcat(cmsg, "\n");
        agent.isBlockTimeTag=1; _msgout(cmsg); agent.isBlockTimeTag=0;
      }

    }

    if( nLineNum<0 ) {
        if( strUT[0]==NULL )
          sprintf(reply, "First %d of %d script lines are printed with current Alt & HA.", nLines, osc.linenum);
        else 
          sprintf(reply, "First %d of %d script lines are printed with Alt & HA at UTC %s.", nLines, osc.linenum, strUT);
    }

  }

  // All done.
  
  return CMD_OK;

}

  //////////////////////////////////////////////////////////////////////////////////////////
  //
  //  //
  //  // args input & check
  //  //
  //
  //  if( strlen(args)==0 ) {
  //    strcpy(reply, "Usage: oline (cmd/exp) <start line #>(-<end line #>) (<ut string>)"
  //                  " // e.g. \"oline 10\""
  //                  ", \"oline cmd 10\""
  //                  ", \"oline exp 10\""
  //                  ", \"oline 10-20\""
  //                  ", \"oline 10 2020-01-23T01:23:45\""
  //                  ", \"oline 10 2020 01 23 01 23 45\""
  //                  ", \"oline 10-20 2020-01-23T01:23:45\""
  //                  ", \"oline -exp 10-20 2020-01-23T01:23:45\""
  //                  " // 'cmd'/'exp' can be alternated with a abbreviation 'c'/'e'"
  //                  );   // v0.6.2
  //    return CMD_ERR;
  //  }
  //  
  //       if( strncasecmp(args,"-CMD",4)==0 || strncasecmp(args,"-EXP",4)==0 ) n = 4;
  //  else if( strncasecmp(args,"CMD" ,3)==0 || strncasecmp(args,"EXP" ,3)==0 ) n = 3;
  //  else if( strncasecmp(args,"-C"  ,2)==0 || strncasecmp(args,"-E"  ,2)==0 ) n = 2;
  //  else if( strncasecmp(args,"C"   ,1)==0 || strncasecmp(args,"E"   ,1)==0 ) n = 1;
  //  else                                                                      n = 0;
  //  
  //  n = sscanf(args+n, "%d-%d", &nIndexStart, &nIndexEnd);
  //  
  //  if( strncasecmp(args,"CMD",3)==0 || strncasecmp(args,"-CMD",4)==0 || 
  //      strncasecmp(args,"C"  ,1)==0 || strncasecmp(args,"-C"  ,2)==0 ) {
  //    utin = 0;
  //  }
  //  else if( strncasecmp(args,"EXP",3)==0 || strncasecmp(args,"-EXP",4)==0 || 
  //           strncasecmp(args,"E"  ,1)==0 || strncasecmp(args,"-E"  ,2)==0  ) {
  //    utin = sscanf(args, "%*s %*s %[^\n]", strUT);
  //  }
  //  else {
  //    utin = sscanf(args, "%*s %[^\n]", strUT);
  //  }
  //  
  //  sprintf(reply, "n %d    start %d    end %d    utin %d", n, nIndexStart, nIndexEnd, utin);
  //  return CMD_OK;
  //
  //////////////// codes for one of designs considered..

//------------------------------------------------------------------------------
//
// osc.label - query the line that has a label string including input string
//

int
cmd_osclabel(char *args, MsgType msgtype, char *reply)
{

  if(osc.linenum<=0) {
    strcpy(reply, "No observation script data loaded");
    return CMD_OK;
  }

  if( osc.expnum<=0 ) {
    strcpy(reply, "No exposure line in the script data loaded");
    return CMD_OK;
  }

  // args input & check

  if( strlen(args)==0 ) {
    strcpy(reply, "Usage: olabel <label> (<ut string>)"); 
    return CMD_ERR;
  }

  int i, n, len, utin, cnt;
  double ha, alt, delta_ha;
  time_t sec_obs;
  struct tm ut_obs;
  
  char strUT[OSC_MAX_ARGIN];
  char strKeyword[OSC_MAX_ARGIN];
  char strProjID[OSC_MAX_PROJID+1];
  char strLabel[OSC_MAX_LABEL+1];
  char strObject[OSC_MAX_OBJECT+1];

  n = sscanf(args, "%s %[^\n]", strKeyword, strUT);  
  if(n>1) utin = 1;  else utin = 0;
    
  //sprintf(cmsg, "Searching for lines that has labels including input string '%s' ..\n", args);_msgout(cmsg);
  //sprintf(cmsg, "Searching for labels containing input string '%s' ..\n", args);_msgout(cmsg);
  sprintf(cmsg, "Searching for labels containing input string '%s' ..\n", strKeyword);_msgout(cmsg);   // modified for UT input at v0.5.0

  for( cnt=i=0 ; i<osc.linenum ; i++ ) {

    //if( strstr(osc.line[i].label, args) ) {
    if( osc.line[i].type==OSC_TYPE_EXP && ( strstr(osc.line[i].label, strKeyword) || strKeyword[0] == '*' ) ) {   // modified for UT input at v0.5.0

      //
      //ha = sys.ha_h + ( sys.ra_h - osc.line[i].ra_h );
      //if(ha<-12.0) ha+=24.0;  if(ha>=+12.0) ha-=24.0;
      //alt = GetAltitude(ha, osc.line[i].dec_d, sys.tcs_latitude);   // HA & Alt calculation added at v0.4.9
      //
      //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %-16s %-12s %-12s %c  %-8s %-12s %-2s %6.1f  %-19s %4d   ALT %5.2f  HA %+.2f\n",
      //                 (i+1), osc.line[i].idx, osc.line[i].label, 
      //                  osc.line[i].ra, osc.line[i].dec, osc.line[i].copt, 
      //                  osc.line[i].imgtyp, osc.line[i].object, 
      //                  osc.line[i].filter, osc.line[i].exptime, 
      //                  osc.line[i].utobs, osc.line[i].uttol, 
      //                  alt, ha);   // Alt & HA display added at v0.4.9
      //_msgout(cmsg);
      //
      //// modified as below at v0.5.0

      if(utin) {

        len = strlen(strUT);      
        for( n=0 ; n<len ; n++ ) if( strUT[n]<0x30 || strUT[n]>0x39 ) strUT[n] = 0x20;   // to replace simbolic characters with a space      
        n = sscanf(strUT, "%d %d %d %d %d %d", &ut_obs.tm_year, &ut_obs.tm_mon, &ut_obs.tm_mday, &ut_obs.tm_hour, &ut_obs.tm_min, &ut_obs.tm_sec);

        if(n==5) ut_obs.tm_sec = 0;
        if( n<5 || ut_obs.tm_year<0 || ut_obs.tm_year>9999 || ut_obs.tm_mon<1 || ut_obs.tm_mon>12 || ut_obs.tm_mday<1 || ut_obs.tm_mday>31 
                || ut_obs.tm_hour<0 || ut_obs.tm_hour>23   || ut_obs.tm_min<0 || ut_obs.tm_min>59 || ut_obs.tm_sec<0  || ut_obs.tm_sec>59 ) goto UT_INPUT_ERROR;

        sprintf(strUT, "%04d-%02d-%02dT%02d:%02d:%02d", ut_obs.tm_year, ut_obs.tm_mon, ut_obs.tm_mday, ut_obs.tm_hour, ut_obs.tm_min, ut_obs.tm_sec);
            
        ut_obs.tm_mon -= 1;
        ut_obs.tm_year -= 1900;  
        sec_obs = mktime(&ut_obs);
        
        delta_ha = (double)(sec_obs-time(NULL)) / 3600.0 * 1.00273791;   // 1.00273791 = solar time / sidereal time = 24.0 solar hours / 23.935 solar hours (23h 56m 04s) for 1 Earth rotation = 366.2422 sidereal days / 365.2422 solar days for 1 solar year

      }
      else {

      	  delta_ha = 0.0;

      }

      ha = sys.ha_h + ( sys.ra_h - osc.line[i].ra_h ) + delta_ha;   // modified to calculate Alt & HA at UTC input at v0.5.0
      while(ha< -12.0) ha+=24.0;  while(ha>=+12.0) ha-=24.0;   // modified for large delta_hour at v0.5.0
      alt = GetAltitude(ha, osc.line[i].dec_d, sys.tcs_latitude);

      strcpy( strProjID, osc.line[i].projid );   // v0.6.4
      strcpy( strLabel , osc.line[i].label  );
      strcpy( strObject, osc.line[i].object );
      strncat( strProjID, CONST_STR_SPACE, MAX(osc.max_projid_length-strlen(strProjID),0) );   // v0.6.4
      strncat( strLabel , CONST_STR_SPACE, MAX(osc.max_label_length -strlen(strLabel ),0) );
      strncat( strObject, CONST_STR_SPACE, MAX(osc.max_object_length-strlen(strObject),0) );
      //// added for adjusting Label & Object field length at v0.5.0

    //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %s  %-2s %6.1f  %7s %4d  %+10.5f %+10.5f  %u   ALT %5.2f  HA %+.2f\n",   //// for DBG
      sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %s  %-2s %6.1f  %7s %4d  %+10.5f %+10.5f   ALT %5.2f  HA %+.2f\n",
                       (i+1), osc.line[i].idx, strProjID, strLabel, 
                        osc.line[i].ra, osc.line[i].dec, osc.line[i].copt, 
                        osc.line[i].imgtyp, strObject, 
                        osc.line[i].filter, osc.line[i].exptime, 
                        osc.line[i].utobs, osc.line[i].uttol, 
                        osc.line[i].velra, osc.line[i].veldec, // v0.6.9
                      //(UINT)sec_obs,   //// for DBG
                        alt, ha);   // modified for Label & Object field adjusted at v0.5.0
      agent.isBlockTimeTag=1; _msgout(cmsg); agent.isBlockTimeTag=0;   // TimeTag disabling added at v0.5.0
                        
      cnt++;
      
    }

  }

  //sprintf(reply, "%d/%d Exp lines found for '%s' label string", cnt, osc.expnum, args);
  if(utin) sprintf(reply, "%d/%d lines found for '%s' lable keyword, and displayed with Alt & HA at UTC %s", cnt, osc.expnum, strKeyword, strUT);
  else sprintf(reply, "%d/%d lines found for '%s' lable keyword", cnt, osc.expnum, strKeyword);   // modified for UT input at v0.5.0

  return CMD_OK;

  
  UT_INPUT_ERROR:
  
  strcpy(reply, "Invalid UT string (format: \"2020-01-23T01:23:45\", "
                "symbolic characters can be alternated with a space, e.g. \"2020 01 23 01 23 45\")");
  
  return CMD_ERR;

}

//------------------------------------------------------------------------------
//
// osc.object - query the line that has a object string including input string
//

int
cmd_oscobject(char *args, MsgType msgtype, char *reply)
{

  if(osc.linenum<=0) {
    strcpy(reply, "No observation script data loaded");
    return CMD_OK;
  }

  if( osc.expnum<=0 ) {
    strcpy(reply, "No exposure line in the script data loaded");
    return CMD_OK;
  }

  // args input & check

  if( strlen(args)==0 ) {
    strcpy(reply, "Usage: oobject <object> (<ut string>)"); 
    return CMD_ERR;
  }

  int i, n, len, utin, cnt;
  double ha, alt, delta_ha;
  time_t sec_obs;
  struct tm ut_obs;
  
  char strUT[OSC_MAX_ARGIN];
  char strKeyword[OSC_MAX_ARGIN];
  char strProjID[OSC_MAX_PROJID+1];
  char strLabel[OSC_MAX_LABEL+1];
  char strObject[OSC_MAX_OBJECT+1];

  n = sscanf(args, "%s %[^\n]", strKeyword, strUT);  
  if(n>1) utin = 1;  else utin = 0;

  //sprintf(cmsg, "Searching for lines that has object names including input string '%s' ..\n", args);_msgout(cmsg);
  //sprintf(cmsg, "Searching for objects containing input string '%s' ..\n", args);_msgout(cmsg);
  sprintf(cmsg, "Searching for objects containing input string '%s' ..\n", strKeyword);_msgout(cmsg);   // modified for UT input at v0.5.0
  
  for( cnt=i=0 ; i<osc.linenum ; i++ ) {

    //if( strstr(osc.line[i].object, args) ) {
    if( osc.line[i].type==OSC_TYPE_EXP && ( strstr(osc.line[i].object, strKeyword) || strKeyword[0] == '*' ) ) {   // modified for UT input at v0.5.0

      //
      //ha = sys.ha_h + ( sys.ra_h - osc.line[i].ra_h );
      //if(ha<-12.0) ha+=24.0;  if(ha>=+12.0) ha-=24.0;
      //alt = GetAltitude(ha, osc.line[i].dec_d, sys.tcs_latitude);   // HA & Alt calculation added at v0.4.9
      //
      //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %-16s %-12s %-12s %c  %-8s %-12s %-2s %6.1f  %-19s %4d   ALT %5.2f  HA %+.2f\n",
      //                 (i+1), osc.line[i].idx, osc.line[i].label, 
      //                  osc.line[i].ra, osc.line[i].dec, osc.line[i].copt, 
      //                  osc.line[i].imgtyp, osc.line[i].object, 
      //                  osc.line[i].filter, osc.line[i].exptime, 
      //                  osc.line[i].utobs, osc.line[i].uttol, 
      //                  alt, ha);   // Alt & HA display added at v0.4.9
      //_msgout(cmsg);
      //
      //// modified as below at v0.5.0

      if(utin) {

        len = strlen(strUT);      
        for( n=0 ; n<len ; n++ ) if( strUT[n]<0x30 || strUT[n]>0x39 ) strUT[n] = 0x20;   // to replace simbolic characters with a space      
        n = sscanf(strUT, "%d %d %d %d %d %d", &ut_obs.tm_year, &ut_obs.tm_mon, &ut_obs.tm_mday, &ut_obs.tm_hour, &ut_obs.tm_min, &ut_obs.tm_sec);

        if(n==5) ut_obs.tm_sec = 0;
        if( n<5 || ut_obs.tm_year<0 || ut_obs.tm_year>9999 || ut_obs.tm_mon<1 || ut_obs.tm_mon>12 || ut_obs.tm_mday<1 || ut_obs.tm_mday>31 
                || ut_obs.tm_hour<0 || ut_obs.tm_hour>23   || ut_obs.tm_min<0 || ut_obs.tm_min>59 || ut_obs.tm_sec<0  || ut_obs.tm_sec>59 ) goto UT_INPUT_ERROR;

        sprintf(strUT, "%04d-%02d-%02dT%02d:%02d:%02d", ut_obs.tm_year, ut_obs.tm_mon, ut_obs.tm_mday, ut_obs.tm_hour, ut_obs.tm_min, ut_obs.tm_sec);
            
        ut_obs.tm_mon -= 1;
        ut_obs.tm_year -= 1900;  
        sec_obs = mktime(&ut_obs);
        
        delta_ha = (double)(sec_obs-time(NULL)) / 3600.0 * 1.00273791;   // 1.00273791 = solar time / sidereal time = 24.0 solar hours / 23.935 solar hours (23h 56m 04s) for 1 Earth rotation = 366.2422 sidereal days / 365.2422 solar days for 1 solar year

      }
      else {

      	  delta_ha = 0.0;

      }

      ha = sys.ha_h + ( sys.ra_h - osc.line[i].ra_h ) + delta_ha;   // modified to calculate Alt & HA at UTC input at v0.5.0
      while(ha< -12.0) ha+=24.0;  while(ha>=+12.0) ha-=24.0;   // modified for large delta_hour at v0.5.0
      alt = GetAltitude(ha, osc.line[i].dec_d, sys.tcs_latitude);
      
      strcpy( strProjID, osc.line[i].projid );   // v0.6.4
      strcpy( strLabel , osc.line[i].label  );
      strcpy( strObject, osc.line[i].object );
      strncat( strProjID, CONST_STR_SPACE, MAX(osc.max_projid_length-strlen(strProjID),0) );   // v0.6.4
      strncat( strLabel , CONST_STR_SPACE, MAX(osc.max_label_length -strlen(strLabel ),0) );
      strncat( strObject, CONST_STR_SPACE, MAX(osc.max_object_length-strlen(strObject),0) );
      //// added for adjusting Label & Object field length at v0.5.0

    //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %s  %-2s %6.1f  %7s %4d  %+10.5f %+10.5f  %u   ALT %5.2f  HA %+.2f\n",   //// for DBG
      sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %s  %-2s %6.1f  %7s %4d  %+10.5f %+10.5f   ALT %5.2f  HA %+.2f\n",
                       (i+1), osc.line[i].idx, strProjID, strLabel, 
                        osc.line[i].ra, osc.line[i].dec, osc.line[i].copt, 
                        osc.line[i].imgtyp, strObject, 
                        osc.line[i].filter, osc.line[i].exptime, 
                        osc.line[i].utobs, osc.line[i].uttol, 
                        osc.line[i].velra, osc.line[i].veldec, // v0.6.9
                      //(UINT)sec_obs,   //// for DBG
                        alt, ha);   // modified for Label & Object field adjusted at v0.5.0
      agent.isBlockTimeTag=1; _msgout(cmsg); agent.isBlockTimeTag=0;   // TimeTag disabling added at v0.5.0
                        
      cnt++;
      
    }

  }

  //sprintf(reply, "%d/%d Exp lines found for '%s' object string", cnt, osc.expnum, args);
  if(utin) sprintf(reply, "%d/%d lines found for '%s' object keyword, and displayed with Alt & HA at UTC %s", cnt, osc.expnum, strKeyword, strUT);
  else sprintf(reply, "%d/%d lines found for '%s' object keyword", cnt, osc.expnum, strKeyword);   // modified for UT input at v0.5.0

  return CMD_OK;


  UT_INPUT_ERROR:
  
  strcpy(reply, "Invalid UT string (format: \"2020-01-23T01:23:45\", "
                "symbolic characters can be alternated with a space, e.g. \"2020 01 23 01 23 45\")");
  
  return CMD_ERR;

}

//------------------------------------------------------------------------------
//
// osc.status - query script observation status
//

int
cmd_oscstatus(char *args, MsgType msgtype, char *reply)
{
  //strcpy(reply, GetOscStatus());  --> changed as follows at v0.2.8

  char buf[256];
  char curline[65], nextline[65];

  if( osc.flag_running && osc.line[osc.lineidx-1].type==OSC_TYPE_CMD ) {
    strcpy(buf, "-COMMAND");
  }
  else if( osc.flag_running && osc.line[osc.lineidx-1].type==OSC_TYPE_EXP ) {

    buf[0] = NULL;

    if( !osc.flag_exposing ) {
      if( !osc.flag_pointed && !osc.line[osc.lineidx-1].flag_movedisable ) strcat(buf, "+POINTING");
      if( !osc.flag_filterchanged    ) strcat(buf, "+FILTER"  );
      if( !osc.flag_projidcommanded  ) strcat(buf, "+PROJID"  );   // added at v0.6.4
      if( !osc.flag_objectcommanded  ) strcat(buf, "+OBJECT"  );
      if( !osc.flag_exptimecommanded ) strcat(buf, "+EXPTIME" );
      if(  osc.waiting_dome_rotation ) strcat(buf, "+DROTCOMP" );   // added at v1.1.0
      if(  osc.waiting_dome_shutter  ) strcat(buf, "+DSHUTCOMP");   // added at v1.1.0
      strcat(buf, "+EXPSTART"     );
      strcat(buf, "+EXPCOMPLETE"  );
      if( osc.flag_preparenextexp && osc.line[osc.lineidx].type==OSC_TYPE_EXP ) {
        strcat(buf, "+NEXTPOINTING");
        strcat(buf, "+NEXTFILTER"  );
        strcat(buf, "+NEXTOBJECT"  );
        strcat(buf, "+NEXTEXPTIME" );
      }
    }

    else {
      strcat(buf, "+EXPCOMPLETE"  );
      if( osc.flag_preparenextexp && osc.line[osc.lineidx].type==OSC_TYPE_EXP ) {
        if( !osc.flag_pointed && !osc.line[osc.lineidx].flag_movedisable ) strcat(buf, "+NEXTPOINTING");
        if( !osc.flag_filterchanged    ) strcat(buf, "+NEXTFILTER"  );
        if( !osc.flag_projidcommanded  ) strcat(buf, "+NEXTPROJID"  );   // added at v0.6.4
        if( !osc.flag_objectcommanded  ) strcat(buf, "+NEXTOBJECT"  );
        if( !osc.flag_exptimecommanded ) strcat(buf, "+NEXTEXPTIME" );
      }
    }

  }
  else if( osc.flag_running ) {
    strcpy(buf, "-INDEF");
  }
  else {
    strcpy(buf, "-No");
  }

  switch( osc.line[osc.lineidx-1].type ) {
    case OSC_TYPE_CMD: sprintf(curline, "'+%s'", osc.line[osc.lineidx-1].cmd  ); break;
    case OSC_TYPE_EXP: sprintf(curline, "'%s'" , osc.line[osc.lineidx-1].label); break;
    default          : strcpy (curline, "INDEF");                                break;
  }

  if( osc.lineidx == osc.linenum ) strcpy(nextline, "END");
  else {
    switch( osc.line[osc.lineidx].type ) {
      case OSC_TYPE_CMD: sprintf(nextline, "'+%s'", osc.line[osc.lineidx].cmd                  ); break;
    //case OSC_TYPE_EXP: sprintf(nextline, "'%s'" , osc.line[osc.lineidx].label                ); break;
      case OSC_TYPE_EXP: sprintf(nextline, "'%s'" , osc.line[osc.lineidx+osc.expnum_skip].label); break;   // v0.4.4
      default          : strcpy (nextline, "INDEF");                                              break;
    }
  }

  sprintf(reply, "LINE#=%04d/%04d  CMD#=%04d/%04d  EXP#=%04d/%04d    "
                 "OpStatus=%-8s  CurrentLine=%-16s NextLine=%-16s "
                 "PrepNextExp=%-3s  OpFlags=0x%04X   RemainingProc=%s",
                  osc.lineidx, osc.linenum, osc.cmdidx, osc.cmdnum, osc.expidx, osc.expnum, 
                  (osc.flag_paused?"PAUSED":(osc.flag_running?"RUNNING":"IDLE")), curline, nextline, 
                  (osc.flag_preparenextexp?"ON":"OFF"), osc.procflags, (buf+1));

  return CMD_OK;

}

//------------------------------------------------------------------------------
//
// osc.last - query last completed script line number (v0.9.4)
//

int
cmd_osclast(char *args, MsgType msgtype, char *reply)
{
    sprintf(reply, "LastExpCompleted=%d  LastFitsSaved=%d", 
                    osc.lastidx_expcompleted, osc.lastidx_fitssaved);
    return CMD_OK;
}

//------------------------------------------------------------------------------
//
// osc.start - start script observation
//

int
cmd_oscstart(char *args, MsgType msgtype, char *reply)
{
  int i, nIndex = 0;

  if( osc.linenum <= 0 ) {
    strcpy(reply, "No observation script data");
    return CMD_ERR;
  }

  ////if(osc.flag_running) {
  ////  strcpy(reply, "Script observation is already running. Please stop the script observation first.");
  ////  return CMD_ERR;
  ////}
  //// --> disabled to use ostart command in the script

  // args input & check

  if( sscanf(args,"%d",&nIndex)<1 ) {
    strcpy(reply, "Usage: sstart <lineidx>  /  <lineidx>: script line index to start");
    return CMD_ERR;
  }

  if( nIndex<1 || nIndex>osc.linenum ) {
    sprintf(reply, "Invalid line index #%d (FirstLineIndex=1 LastLineIndex=%d)", nIndex, osc.linenum);
    return CMD_ERR;
  }

  // Datasource commanding at the beginning of script observation

  if( OscSetDatasource(sys.ics_datasource) < 0 ) {
    strcpy(reply, "Datasource commanding failure");
    return CMD_ERR;
  }

  osc.lineidx = nIndex;
  osc.cmdidx  = 0;
  osc.expidx  = 0;
  for(i=(osc.lineidx-1);i<osc.linenum;i++) if(osc.line[i].type==OSC_TYPE_CMD) { osc.cmdidx=osc.line[i].idx; break; }
  for(i=(osc.lineidx-1);i<osc.linenum;i++) if(osc.line[i].type==OSC_TYPE_EXP) { osc.expidx=osc.line[i].idx; break; }
  osc.lastidx_fitssaved = osc.lastidx_expcompleted = 0;   // for 'olast' command, v0.9.4

  osc.expnum_skip = 0;   // v0.4.4
  
  osc.flag_delay = 0;
  osc.flag_paused = 0;
  osc.flag_running = 1;
  osc.flag_exposing = 0;
  osc.flag_expcomplete = 0;
  osc.flag_additionalshot = 0;   // v0.8.0
  osc.count_filtercommanded = 0;
  osc.flag_filterchanged = 0;
  osc.flag_projidcommanded = 0;   // added at v0.6.4
  osc.flag_objectcommanded = 0;
  osc.flag_exptimecommanded = 0;

  osc.flag_pointed = 0;
  osc.count_pointing = 0;
  //osc.procflags |= OSC_CMDBIT_POINTING;  // do pointing before first exposure start
  osc.procflags = OSC_CMDBIT_POINTING;  // off all the flags for CMD/CHK and on the pointing flag to do pointing before first exposure start, modified at v0.4.5
  osc.flag_nstchecked = 0;  // v0.6.9
  osc.waiting_dome_rotation = 0;  // v0.9.6
  osc.waiting_dome_shutter = 0;  // v0.9.6

  osc.flag_responseok = 0;
  osc.flag_responsecheck = 0;
  osc.count_responsecheck = 0;
  osc.count_cmdretry = 0;

  osc.flag_process = 1;
  //osc.count_process = 0;
  osc.count_process = sys.checknum_tcsdata-TCS_DATAUP_INTERVAL*2/3;    // zero point setting *2/4 --> *2/3 modified at v0.4.0

  //strcpy(reply, "Script observation start..  ");
  strcpy(reply, "Script observation start..  OSC.STATUS: ");   // modified at v0.5.3
  //strcat(reply, GetOscStatus());
  cmd_oscstatus(NULL, EXEC, reply+strlen(reply));  // v0.2.8

  for(i=(osc.lineidx-1);i<osc.linenum;i++) {
    if(osc.line[i].type==OSC_TYPE_CMD) {
      if( !strcasecmp(osc.line[i].cmd,"ostart") ) {

        break; 
      }
    }
  } //// v0.9.3
  
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// osc.stop - stop script observation after finishing current line
//

int
cmd_oscstop(char *args, MsgType msgtype, char *reply)
{
  if( !osc.flag_running ) {
    strcpy(reply, "Script observation is not running now.");
    return CMD_ERR;
  }

  osc.flag_running = osc.flag_paused = 0;  
  osc.flag_delay = 0;

  //  if( osc.flag_exposing )
  //    strcpy(reply, "Script observation will stop after completion of the exposure in progress..  ");
  //  else 
  //    strcpy(reply, "Script observation will stop..  ");
  //  --> we will do complete the current exposure.

  //strcpy(reply, "Script observation will stop after completion of the exposure in progress..  ");
  strcpy(reply, "Script observation will stop after completion of the exposure in progress..  OSC.STATUS: ");  // modified at v0.5.3
  //strcat(reply, GetOscStatus());
  cmd_oscstatus(NULL, EXEC, reply+strlen(reply));  // v0.2.8

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// osc.abort - abort script observation, immediately stop all the processes
//

int
cmd_oscabort(char *args, MsgType msgtype, char *reply)
{

  osc.procflags = 0x0000;

  osc.flag_delay = 0;
  osc.flag_paused = 0;
  osc.flag_running = 0;
  osc.flag_exposing = 0;
  osc.flag_expcomplete = 0;
  osc.flag_additionalshot = 0;   // v0.8.0

  osc.count_filtercommanded = 0;
  osc.flag_filterchanged = 1;
  osc.flag_projidcommanded = 1;   // added at v0.6.4
  osc.flag_objectcommanded = 1;
  osc.flag_exptimecommanded = 1;
  osc.flag_pointed = 1;
  osc.count_pointing = 0;
  osc.flag_nstchecked = 1;  // v0.6.9
  osc.waiting_dome_rotation = 0;  // v0.9.6
  osc.waiting_dome_shutter = 0;  // v0.9.6

  osc.flag_responseok = 1;
  osc.flag_responsecheck = 0;
  osc.count_responsecheck = 0;
  osc.count_cmdretry = 0;

  osc.flag_process = 0;
  //osc.count_process = 0;
  osc.count_process = sys.checknum_tcsdata-TCS_DATAUP_INTERVAL*2/3;    // zero point setting *2/4 --> *2/3 modified at v0.4.0

  //strcpy(reply, "Script observation is aborted.  ");
  strcpy(reply, "Script observation is aborted.  OSC.STATUS: ");  // modified at v0.5.3
  //strcat(reply, GetOscStatus());
  cmd_oscstatus(NULL, EXEC, reply+strlen(reply));  // v0.2.8

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// osc.pause - pause script observation
//

int
cmd_oscpause(char *args, MsgType msgtype, char *reply)
{
  if( !osc.flag_running ) {
    strcpy(reply, "Script observation is not running now.");
    return CMD_ERR;
  }

  if( osc.lineidx == osc.linenum ) {
    sprintf(reply, "Currently running line(#%d) is the last one. The script running just will be stopped..", osc.lineidx);
    return CMD_OK;
  }

  osc.flag_paused = 1;

  if( osc.flag_exposing ) {
    //strcpy(reply, "Script observation will be paused after completion of the exposure in progress..  ");
    strcpy(reply, "Script observation will be paused after completion of the exposure in progress..  OSC.STATUS: ");   // modified at v0.5.3
  }
  else {
    //strcpy(reply, "Script observation is paused.  OSC.STATUS: ");
    strcpy(reply, "Script observation is paused.  OSC.STATUS: ");   // modified at v0.5.3
    
  }

  //strcat(reply, GetOscStatus());
  cmd_oscstatus(NULL, EXEC, reply+strlen(reply));  // v0.2.8

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// osc.resume - resume script observation
//

int
cmd_oscresume(char *args, MsgType msgtype, char *reply)
{
  
  osc.flag_delay = 0;

  if(!osc.flag_running) {
    strcpy(reply, "Script observation is not running now.");
    return CMD_ERR;
  }

  if(!osc.flag_paused) {
    strcpy(reply, "Script observation is not paused now.");
    return CMD_ERR;
  }

  // Datasource commanding at the resuming of script observation

  if( OscSetDatasource(sys.ics_datasource) < 0 ) {
    strcpy(reply, "Datasource commanding failure");
    return CMD_ERR;
  }

  osc.flag_paused = 0;
  osc.flag_pointed = 0;
  osc.count_pointing = 0;
  osc.flag_nstchecked = 0;  // v0.6.9
  osc.waiting_dome_rotation = 0;  // v0.9.6
  osc.waiting_dome_shutter = 0;  // v0.9.6
  osc.flag_filterchanged = 0;  // v0.4.4
  osc.count_filtercommanded = 0;  // v0.4.4
  osc.procflags |= OSC_CMDBIT_POINTING;
  //osc.procflags = OSC_CMDBIT_POINTING;  // off all the flags for CMD/CHK and on the pointing flag to do pointing before first exposure start, modified at v0.4.5
  // --> responsecheck was left..

  osc.count_process = sys.checknum_tcsdata-TCS_DATAUP_INTERVAL*2/3;    // zero point setting *2/4 --> *2/3 modified at v0.4.0

  //osc.flag_responseok = 0;
  //osc.flag_responsecheck = 0;
  //osc.count_responsecheck = 0;
  //osc.count_cmdretry = 0;
  //  -->  this can make duplicately commanding 'go'

  //strcpy(reply, "Script observation resumed..  ");
  strcpy(reply, "Script observation resumed..  OSC.STATUS: ");   // modified at v0.5.3
  //strcat(reply, GetOscStatus());
  cmd_oscstatus(NULL, EXEC, reply+strlen(reply));  // v0.2.8

  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// osc.prepare - toggle to enable/disable preparation for next exposure
//

int
cmd_oscprepare(char *args, MsgType msgtype, char *reply)
{
  if(osc.flag_preparenextexp) {
    osc.flag_preparenextexp = 0;
    strcpy(reply,"Next exposure preparation mode Disabled");
  }
  else {
    osc.flag_preparenextexp = 1;
    strcpy(reply,"Next exposure preparation mode Enabled");
  }
  return CMD_OK;
}

//------------------------------------------------------------------------------
//
// osc.delay - delay osc process before Go command or preparation process start for the next exposure
//
  
int
cmd_oscdelay(char *args, MsgType msgtype, char *reply)  // reserved at v0.3.7, implementation at v0.5.2
{
  if(strlen(args)==0) {
    strcpy(reply, "Usage: delay <sec>");
    return CMD_ERR;
  }    
  
  //// for debugging
  //  osc.flag_running = 1;
  //  osc.lineidx = -1;
  
  if( !osc.flag_running ) {
    strcpy(reply, "Script observation is not running now.");
    return CMD_ERR;
  }

  if( osc.lineidx == osc.linenum ) {
    sprintf(reply, "Currently running line(#%d) is the last one. The script running just will be stopped..", osc.lineidx);
    return CMD_OK;
  }
  
//osc.flag_paused = 1;  <-- moved to ProcOsc() at v0.5.3, osc.flag_delay is set to 0 in cmd_oscresume(), cmd_oscresume() is called in the main loop
  osc.flag_delay = 1;
  osc.count_delay = (int)(atof(args));
  
  if( osc.flag_exposing ) {
    sprintf(reply, "Script observation delay for %d sec will start after completion of current exposure..  OSC.STATUS: ", osc.count_delay);
  }
  else {
    sprintf(reply, "Start the script observation delay for %d seconds.  OSC.STATUS: ", osc.count_delay);
  }

  cmd_oscstatus(NULL, EXEC, reply+strlen(reply));
  
  return CMD_OK;
}


//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
//
// Script observation subroutine/utility functions
//

//------------------------------------------------------------------------------
//
// osc.util.GetOscLine - print a line of the observation script line (v0.6.2)
//

int 
GetOscLine(int nLineNum, int nOption, char *strUT, char *strRtn)
// Option 0: fitted field width / Option 1: fixed field width / ..
{
  int i = nLineNum - 1;
  int n, len;
  double jd, lst;
  double ha, alt;
  //double delta_ha;
  //time_t sec_obs;
  //struct tm ut_obs;    // replaced with smctime_t at v0.8.9
  smctime_t ut;
  
  if( nLineNum<=0 ) {
    strcpy(strRtn, "Invalid line number");
    return CMD_ERR;
  }

  if(osc.line[i].type==OSC_TYPE_CMD) {

    if( nOption==0 ) {   // Option 0: fitted field width

      sprintf(strRtn, "LINE#%04d  CMD#%04d  +%s  %s", 
                      (i+1), osc.line[i].idx, osc.line[i].cmd, osc.line[i].arg);

    }
    else if( nOption==1 ) {   // Option 1: fixed field width for exp lines for printing multi lines in case option to print first few lines

      sprintf(strRtn, "  LINE#%04d  CMD#%04d  +%-11s %s", 
                      (i+1), osc.line[i].idx, osc.line[i].cmd, osc.line[i].arg);

    }

  }
  else if(osc.line[i].type==OSC_TYPE_EXP) {

    if(strUT==NULL) len = 0;
    else len = strlen(strUT);

    ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    ////
    ////    delta_ha = 0.0;
    ////
    ////    if( len ) {
    ////
    ////      //sprintf(cmsg, "\n utin = %d / \"%s\"\n\n", utin, strUT);_msgout(cmsg);     //// FOR DBG
    ////
    ////      for( n=0 ; n<len ; n++ ) if( strUT[n]<0x30 || strUT[n]>0x39 ) strUT[n] = 0x20;   // to replace simbolic characters with a space      
    ////      n = sscanf(strUT, "%d %d %d %d %d %d", &ut_obs.tm_year, &ut_obs.tm_mon, &ut_obs.tm_mday, &ut_obs.tm_hour, &ut_obs.tm_min, &ut_obs.tm_sec);
    ////
    ////      if(n==5) ut_obs.tm_sec = 0;
    ////      if( n<5 || ut_obs.tm_year<0 || ut_obs.tm_year>9999 || ut_obs.tm_mon<1 || ut_obs.tm_mon>12 || ut_obs.tm_mday<1 || ut_obs.tm_mday>31 
    ////              || ut_obs.tm_hour<0 || ut_obs.tm_hour>23   || ut_obs.tm_min<0 || ut_obs.tm_min>59 || ut_obs.tm_sec<0  || ut_obs.tm_sec>59 ) {
    ////        strcpy(strRtn, "Invalid UT string (format: \"2020-01-23T01:23:45\", "
    ////                       "symbolic characters can be alternated with a space, e.g. \"2020 01 23 01 23 45\")");  
    ////        return -1;
    ////      }
    ////
    ////      sprintf(strUT, "%04d-%02d-%02dT%02d:%02d:%02d", ut_obs.tm_year, ut_obs.tm_mon, ut_obs.tm_mday, ut_obs.tm_hour, ut_obs.tm_min, ut_obs.tm_sec);
    ////
    ////      ut_obs.tm_mon -= 1;
    ////      ut_obs.tm_year -= 1900;  
    ////      sec_obs = mktime(&ut_obs);
    ////
    ////      delta_ha = (double)(sec_obs-time(NULL)) / 3600.0 * 1.00273791;   // 1.00273791 = solar time / sidereal time = 24.0 solar hours / 23.935 solar hours (23h 56m 04s) for 1 Earth rotation = 366.2422 sidereal days / 365.2422 solar days for 1 solar year
    ////
    ////  
    ////      //sprintf(cmsg, "\n delta_hour = %.1f\n\n", delta_hour);_msgout(cmsg);   //// FOR DBG
    ////
    ////    }
    ////
    ////    //ha = sys.ha_h + ( sys.ra_h - osc.line[i].ra_h );
    ////    //if(ha<-12.0) ha+=24.0;  if(ha>=+12.0) ha-=24.0;
    ////    //alt = GetAltitude(ha, osc.line[i].dec_d, sys.tcs_latitude);   // HA & Alt calculation added at v0.4.9
    ////
    ////    ha = sys.ha_h + ( sys.ra_h - osc.line[i].ra_h ) + delta_ha;   // modified to calculate Alt & HA at UTC input at v0.5.0
    ////    while(ha< -12.0) ha+=24.0;  while(ha>=+12.0) ha-=24.0;   // modified for large delta_hour at v0.5.0
    ////    alt = GetAltitude(ha, osc.line[i].dec_d, sys.tcs_latitude);
    ////
    //////////////////////////////////////////////////////////////////////////////////////////////// replaced with follows at v0.8.9
    ////
            if( len ) {
              for( n=0 ; n<len ; n++ ) if( strUT[n]<0x30 || strUT[n]>0x39 ) strUT[n] = 0x20;   // to replace simbolic characters with a space      
              n = sscanf(strUT, "%d %d %d %d %d %lf", &ut.year, &ut.month, &ut.day, &ut.hour, &ut.min, &ut.sec);
              if(n==5) ut.sec = 0.0;
              if( n<5 || ut.year<0 || ut.year>9999 || ut.month<1 || ut.month>12 || ut.day<1   || ut.day> 31 
                      || ut.hour<0 || ut.hour>23   || ut.min  <0 || ut.min  >59 || ut.sec<0.0 || ut.sec>=60.0 ) {
                strcpy(strRtn, "Invalid UT string (format: \"2020-01-23T01:23\" or \"2020-01-23T01:23:45\", "
                               "symbolic characters can be alternated with a space, e.g. \"2020 01 23 01 23 45\")");
                return -1;
              }
            }
            else {
              GetUTCDateTime(&ut);
            }

            //sprintf(strUT, "%04d-%02d-%02dT%02d:%02d:%02d", ut.year, ut.month, ut.day, ut.hour, ut.min, (int)ut.sec);
            //// not used, removed in v1.0.4 because making Segmentation fault (core dumped) when strUT==NULL though EXP type
            //// --> Reserved: improve UT and strUT handling

            jd = GetJd(ut);
            lst = GetGst(jd) - sys.tcs_longitude/15.0;  // west longitude
            if(lst<0.0) lst += 24.0;
            ha = lst - osc.line[i].ra_h;
            if(ha>12.0) ha-=24.0;  if(ha<-12.0) ha+=24.0;  // actually not necessary;
            alt = GetAltitude(ha, osc.line[i].dec_d, sys.tcs_latitude);
    ////
    ///////////////////////////////////////////////// codes getting ha/alt modified with calculation.c functions using NOVAS C, v0.8.9

    if( nOption==0 ) {   // Option 0: fitted field width

      //sprintf(strRtn, "LINE#%04d  EXP#%04d  %s  %s %s %c  %s %s %s %.1f  %s %d   ALT %.2f  HA %+.2f",
      //sprintf(strRtn, "LINE#%04d  EXP#%04d  %s  %s  %s %s %c  %s %s  %s %.1f  %s %d   ALT %.2f  HA %+.2f",   // ProjID added at v0.6.4
        sprintf(strRtn, "LINE#%04d  EXP#%04d  %s  %s  %s %s %2s %s %s  %s %.1f  %s %d  %+10.5f %+10.5f   ALT %.2f  HA %+.2f",   // verra/dec added at v0.6.9
                      (i+1), osc.line[i].idx, osc.line[i].projid, osc.line[i].label, 
                      osc.line[i].ra, osc.line[i].dec, osc.line[i].copt, 
                      osc.line[i].imgtyp, osc.line[i].object, 
                      osc.line[i].filter, osc.line[i].exptime, 
                      osc.line[i].utobs, osc.line[i].uttol, 
                      osc.line[i].velra, osc.line[i].veldec, // v0.6.9
                      alt, ha);   // Alt & HA display added at v0.4.9

    }
    else if( nOption==1 ) {   // Option 1: fixed field width for exp lines for printing multi lines in case option to print first few lines

      char strProjID[OSC_MAX_PROJID+1];
      char strLabel[OSC_MAX_LABEL+1];
      char strObject[OSC_MAX_OBJECT+1];

      strcpy( strProjID, osc.line[i].projid );   // v0.6.4
      strcpy( strLabel , osc.line[i].label  );
      strcpy( strObject, osc.line[i].object );
      strncat( strProjID, CONST_STR_SPACE, MAX(osc.max_projid_length-strlen(strProjID),0) );   // v0.6.4
      strncat( strLabel , CONST_STR_SPACE, MAX(osc.max_label_length -strlen(strLabel ),0) );
      strncat( strObject, CONST_STR_SPACE, MAX(osc.max_object_length-strlen(strObject),0) );

    //sprintf(strRtn, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %s  %-2s %6.1f  %7s %4d  %+10.5f %+10.5f  %u   ALT %5.2f  HA %+.2f",   //// for DBG
      sprintf(strRtn, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %s  %-2s %6.1f  %7s %4d  %+10.5f %+10.5f   ALT %5.2f  HA %+.2f",
                      (i+1), osc.line[i].idx, strProjID, strLabel, 
                      osc.line[i].ra, osc.line[i].dec, osc.line[i].copt, 
                      osc.line[i].imgtyp, strObject, 
                      osc.line[i].filter, osc.line[i].exptime, 
                      osc.line[i].utobs, osc.line[i].uttol, 
                      osc.line[i].velra, osc.line[i].veldec, // v0.6.9
                    //osc.line[i].secobs,   //// for DBG
                    //(UINT)sec_obs,   //// for DBG
                      alt, ha);   // modified for Label & Object field adjusted at v0.5.0

    }
    else {

      strcpy(strRtn, "Invalid line formating option");
      return -1;

    }

  }
  else {

    strcpy(strRtn, "Indefinite script line type"); 
    return -1;

  }

  return 0;
}
 
//------------------------------------------------------------------------------
//
// osc.util.GetOscStatus - return observation script running/process status
//

char 
*GetOscStatus(void)
{
  static char oscstatus[512];
  memset(oscstatus, NULL, sizeof(oscstatus));
  cmd_oscstatus(NULL, EXEC, oscstatus);
  return oscstatus;
}

//------------------------------------------------------------------------------
//
// osc.util.OscCommand - execute a command for observation script process
//
//   - Calls the low-level cmd_xxx() routines for most commands
//   - command-sending routine was extracted from KeyboardCommand()
//

int
OscCommand(const char *cmdline)
{

  // command components (command arguments and reply string)

  char cmd[STRLEN_CMD];       // command word extracted from keyboard input command-line
  char args[STRLEN_ARG];      // argument field extracted from keyboard input command-line
  char reply[STRLEN_REP];     // reply string buffer from cmd_xxx() functions, including INFO/AUXSTATUS strings

  // Variables used to traverse the command tree

  int i, rtn;

  // Initialize buffers

  memset(args , NULL, STRLEN_ARG);
  memset(reply, NULL, STRLEN_REP);

  // message output and logging

  GRNTEXT;  // v0.5.4
  sprintf(cmsg, " OSC IN : %s\n", cmdline);_msgout(cmsg);   // v0.3.0
  //// --> use this if wanted to log in eventlog with message display on console.

  ////sprintf(cmsg, " OSC IN : %s\n", cmdline);_dbgmsgout(cmsg);
  ////if(client.doLogging) _eventlog(cmsg);  // v0.2.4
  //// --> use this if wanted to log in eventlog without message display on console.

  ////sprintf(cmsg, " OSC IN : %s\n", cmdline);_dbgmsgout(cmsg);
  ////if( client.doLogging && agent.isLogVerbose ) _eventlog(cmsg);  
  //// --> use this if wanted to log only in verbose logging mode without message display on console.

  // Split message into command and argument strings

  rtn = sscanf(cmdline,"%s %[^\n]",cmd,args);

  if( rtn<1 ) {
      REDTEXT;
      sprintf(cmsg, "ERROR: Invalid command from script observation process\n");_msgout(cmsg);
      return CMD_ERR;
  }

  // Traverse the command table, matches are case-insensitive, but
  // must be exact word matches (no abbreviations or aliases)

  for( i=0 ; i<NumCommands ; i++ ) {
      if( strcasecmp(cmdtab[i].cmd,cmd)==0 ) break;
  }

  if( i == NumCommands ) {
      REDTEXT;
      sprintf(cmsg, "ERROR: Unknown command - '%s'\n",cmd);_msgout(cmsg);
  }
  else {

      // all osc input are treated as EXEC: type messages as Keyboard input

      memset(InputCMD, 0, sizeof(InputCMD));
      strcpy(InputCMD, cmd);

    //rtn = cmdtab[i].action(args,EXEC,reply);
      rtn = cmdtab[i].action(args,OSC,reply);  // v0.6.9
      switch (rtn) {   // 'OSC' message type is added for commanding in script at v0.6.0
        case CMD_ERR:
          REDTEXT;
          sprintf(cmsg, "ERROR: %s\n",reply);_msgout(cmsg);
          osc.flag_responseok = 1;
          break;
        case CMD_OK:
          sprintf(cmsg, "DONE: %s\n",reply);_msgout(cmsg);
          osc.flag_responseok = 1;
          break;
        case CMD_NOOP:
          //osc.flag_responseok = 1;   // v0.5.3
          //// --> removed at v0.6.0 to debug the serial command before responseok
          break;
        default:
          break;
      }

  }

  return rtn;
}

//------------------------------------------------------------------------------
//
// osc.util.OscSetDatasource (v0.6.6)
//   - Send a datasource command to each IC (no response check) at the beginning of script observation with cmd_datasource()
//

int 
OscSetDatasource(const int nDatasource)
{

  char args[STRLEN_ARG];      // argument field extracted from keyboard input command-line
  char reply[STRLEN_REP];     // reply string buffer from cmd_xxx() functions, including INFO/AUXSTATUS strings
  int rtn;

  switch(nDatasource) {
    case ICS_ADC:  strcpy(args,"ADC"); break;
    case ICS_CTC:  strcpy(args,"CTC"); break;
    default:  strcpy(args,""); break;
  }

  memset(reply, NULL, STRLEN_REP);

  GRNTEXT;
  sprintf(cmsg, " OSC IN : datasource %s\n", args);

  _msgout(cmsg);
  //// --> use this if wanted to log in eventlog with message display on console.

  // _dbgmsgout(cmsg);
  // if(client.doLogging) _eventlog(cmsg);
  //// --> use this if wanted to log in eventlog without message display on console.

  // dbgmsgout(cmsg);
  // if( client.doLogging && agent.isLogVerbose ) _eventlog(cmsg);  
  //// --> use this if wanted to log only in verbose logging mode without message display on console.

  rtn = cmd_datasource(args,OSC,reply);
  if(rtn==CMD_ERR) {
    REDTEXT;sprintf(cmsg, "ERROR: %s\n",reply);_msgout(cmsg);
    return -1;
  }

  return 0;
}

//------------------------------------------------------------------------------
//
// osc.util.ProcOsc - process observation script running, called in main()
//

int
ProcOsc(COSC *posc, obssystem_t *psys, obsagent_t *pagent, char *reply)
{

  if( posc->flag_paused && !posc->flag_exposing ) return 0;

  if( !pagent->isISISconnected ) {
    posc->flag_running = posc->flag_paused = osc.flag_delay = 0;
    posc->flag_process = 0;
    posc->count_process = psys->checknum_tcsdata-TCS_DATAUP_INTERVAL*2/3;   // zero point setting when flag_process = 0 as well, added at v0.4.0
    strcpy(reply, "Cannnot operate the script observation since ISIS is disconnected. The script observation stopped.");
    return OSC_RTN_ERROR;
  }

  if( !psys->flag_tcsconnected ) {
    posc->flag_running = posc->flag_paused = osc.flag_delay = 0;
    posc->flag_process = 0;
    posc->count_process = psys->checknum_tcsdata-TCS_DATAUP_INTERVAL*2/3;   // zero point setting when flag_process = 0 as well, added at v0.4.0
    strcpy(reply, "Cannnot operate the script observation since TCS is disconnected. The script observation stopped.");
    return OSC_RTN_ERROR;
  }

  if( !psys->flag_auxconnected ) {
    posc->flag_running = posc->flag_paused = osc.flag_delay = 0;
    posc->flag_process = 0;
    posc->count_process = psys->checknum_tcsdata-TCS_DATAUP_INTERVAL*2/3;   // zero point setting when flag_process = 0 as well, added at v0.4.0
    strcpy(reply, "Cannnot operate the script observation since AUX is disconnected. The script observation stopped.");
    return OSC_RTN_ERROR;
  }

  //if( strcmp(psys->filteropstat,"NC")==0 ) {
  if( strcmp(psys->filteropstat,"NC")==0 || strcmp(psys->fsastatus,"NC")==0 ) {  // v0.4.4
    posc->flag_running = posc->flag_paused = osc.flag_delay = 0;
    posc->flag_process = 0;
    posc->count_process = psys->checknum_tcsdata-TCS_DATAUP_INTERVAL*2/3;   // zero point setting when flag_process = 0 as well, added at v0.4.0
    strcpy(reply, "Cannnot operate the script observation since the Filter/Shutter system is not connected. The script observation stopped.");
    return OSC_RTN_ERROR;
  }

  // OK, start process!

  const int i = (posc->lineidx-1)+0;  // current index
//const int n = (posc->lineidx-1)+1;  // next index <-- modified as below at v0.4.4
  const int n = (posc->lineidx-1)+1 + posc->expnum_skip;  // next index
  
  const int expidx_curr = posc->expidx+0;
  const int expidx_next = posc->expidx+1 + posc->expnum_skip;  

  static char lineinput[OSC_MAXLINELEN];
  static char strProjID[OSC_MAX_PROJID+1];
  static char strLabel [OSC_MAX_LABEL+1];
  static char strObject[OSC_MAX_OBJECT+1];  

  int rtn, retry;
  int utpassed=0;
  double ha, alt;
  double dClearance;
  double dTelMovingSec;
  double dDomMovingSec;
  double radeg, decdeg;
  double rasec, decsec;
  double nsttimestamp;
  double nstposadd_ra, nstposadd_dec;
  double nsttoladd_ra, nsttoladd_dec;

  double expstart_dSecZ;
  double expstart_dAlt;
  double expstart_dAz;
  double expstart_dHA;

  // for UT_OBS proc  
  static int cnt_waiting_utobs=0;
  int nDeltaSec, nNextDeltaSec;


  ////////////////////////////////////////////////////////////////
  //  if( !posc->flag_running && !posc->flag_responsecheck && posc->flag_expcomplete ) {
  //    posc->lineidx--;
  //    goto OSC_FINISH;
  //  }
  //////// removed at v0.5.5 --> but still makes the one-more-exp error and newly makes tel-moving-during-exp error
  //
  //if( posc->flag_expcomplete ) posc->flag_expcomplete = 0;
  //////// removed for debugging one-more-exposure error after ostop at v0.5.4, 
  //////// posc->flag_expcomplete is set to 0 at the end of LINE_FINISH
  //////// but this is not relate to the error.. ==> rollback at v0.5.6
  ////////////////////////////////////////////////////////////////
                                                                
  if( !posc->flag_running && !posc->flag_responsecheck && posc->flag_expcomplete ) {
    posc->lineidx--;
    goto OSC_FINISH;
  }

  if( posc->flag_expcomplete ) posc->flag_expcomplete = 0;

  //
  // CURRENT CMD LINE PROCESS
  //

  if( posc->line[i].type==OSC_TYPE_CMD ) {
    
    if( psys->camstatus!=CAMSTATUS_READY ) {   //// previous line finished (LINE_FINISH) when IDLE_3, but should wait for READY status for any commanding except 'go' (v0.4.5)
      return OSC_RTN_NOERR;   //// on going process a script line..
    }

    if( !posc->flag_responsecheck ) {  //// CMD is not sended yet..
      posc->flag_responseok = 0;
      posc->flag_responsecheck = 1;
      posc->count_responsecheck = 0;
      strcpy(posc->reschkcmd, posc->line[i].cmd);
      sprintf(lineinput, "%s %s", posc->line[i].cmd, posc->line[i].arg);
      //KeyboardCommand(lineinput); --> fatal memory error
      //sprintf(cmsg, "DBG> '%s' SEND..\n", lineinput);_dbgmsgout(cmsg);
      OscCommand(lineinput);
    }

    else {   //// CMD has been already sended..
      if( posc->flag_responseok ) {
        posc->flag_responseok = 0;
        posc->flag_responsecheck = 0;
        posc->count_responsecheck = 0;
        posc->count_cmdretry = 0;
        //sprintf(cmsg, "DBG> '%s' CMD RESPONSE OK.\n", posc->reschkcmd);_dbgmsgout(cmsg);
        memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);    // not necessary ??
        if(osc.flag_delay) osc.flag_paused = 1;   // v0.5.3
        goto LINE_FINISH;
      }
      else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
        sprintf(reply, "Script observation process failed to receive OK response. "
                       " The process will retry to command line '%s'.", lineinput);
        posc->flag_responsecheck = 0;
        if( posc->count_cmdretry++ > OSC_CHKCNT_CMDRETRY ) {  // v0.6.5
          sprintf(reply, "Script observation process failed to receive OK response. "
                         " The script observation is paused now. "
                         " Please check for command line '%s'.", lineinput);
          posc->count_cmdretry = 0;
          if(psys->nston) {   // v0.7.5
            sprintf(cmsg, "DBG: TCS paddle off before osc pause\n");_dbgmsgout(cmsg);
            for(retry=0;retry<3;retry++) {
              //strcpy(lineinput, "tpad  off off off off");
              strcpy(lineinput, "nstoff");   // v0.8.0
              rtn = OscCommand(lineinput);
              if(rtn==CMD_OK) break;
              usleep(100);
            }
            if(retry>=3) strcat(reply, "AS WELL AS Failed to control TCS paddle for NST off !! Please check PC-TCS Guide/Drift status..");
          }
          OscCommand("opause");
          return OSC_RTN_ERROR;
        }
        return OSC_RTN_WARNING;
      }
    }

  }// end of if( posc->line[i].type==OSC_TYPE_CMD ) {..}



  //
  // CURRENT EXP LINE PROCESS
  //

  else if( posc->line[i].type==OSC_TYPE_EXP ) {

    //////// check UT_OBS/UT_TOL (v0.7.9-v0.8.0)

  //if( !posc->flag_exposing && posc->line[i].secobs && posc->line[i].uttol ) {   
    if( !posc->flag_exposing && !posc->flag_additionalshot && posc->line[i].secobs && posc->line[i].uttol ) {   // v0.8.3
      // If secobs or uttol is 0, don't check UT_OBS/UT_TOL, and this exp line is observed regardless of the current time.

/*
.. check for move disable flag 
.. with if( !posc->line[i].flag_movedisable )
*/

      if( !posc->flag_pointed ) {   // telescope position will be checked, and pointing will be commanded if necessary..

        //// Telescope slew time setup (v0.8.7)

        psys->tcs_tolerance_pointing_corr = psys->tcs_tolerance_pointing + OSC_ADJ_TOL_POINTING * (double)(posc->count_pointing/2);   // v0.4.7
        if( posc->count_pointing > OSC_CHKCNT_POINTING/2 ) {   // v0.6.7
          if( fabs(posc->line[i].dec_d) > 50.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.3 ~ 1.1
          if( fabs(posc->line[i].dec_d) > 60.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.5 ~ 1.3
          if( fabs(posc->line[i].dec_d) > 65.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.7 ~ 1.5
          if( fabs(posc->line[i].dec_d) > 70.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.9 ~ 1.7
          if( fabs(posc->line[i].dec_d) > 75.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 1.1 ~ 1.9
          if( fabs(posc->line[i].dec_d) > 80.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 1.3 ~ 2.1
          if( fabs(posc->line[i].dec_d) > 85.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 1.5 ~ 2.3
        }

        rasec = 0.0;
        radeg = fabs( posc->line[i].ra_h - psys->ra_h ) * 15.0;
        if( radeg*3600.0 > psys->tcs_tolerance_pointing_corr ) //////////////////////////////// <--- coord correction option is not yet applied..
          rasec = radeg / psys->tcs_slewspeed_ra + psys->tcs_settledown_ra;
        if( fabs(posc->line[i].velra)>=0.000001 )  // ra nst will be activated, and it affects pointing check or settling down
          rasec += psys->tcs_settledown_ra/2;

        decsec = 0.0;
        decdeg = fabs( posc->line[i].dec_d - psys->dec_d );
        if( decdeg*3600.0 > psys->tcs_tolerance_pointing_corr ) //////////////////////////////// <--- coord correction option is not yet applied..
          decsec = decdeg / psys->tcs_slewspeed_dec + psys->tcs_settledown_dec;
        if( fabs(posc->line[i].veldec)>=0.000001 )  // dec nst will be activated, and it affects pointing check or settling down
          decsec += psys->tcs_settledown_dec/2;

        dTelMovingSec = MAX(rasec,decsec);

      }
      else if( posc->procflags&OSC_CMDBIT_POINTING ) {   // pointing must be commanded at least one time..
        dTelMovingSec = MAX(psys->tcs_settledown_ra,psys->tcs_settledown_dec);
      }
      else {
        dTelMovingSec = 0.0;
      }

      //// Dome rotating time setup (v0.x.x)

      //if( fabs( Azm_dest - Azm_curr ) > Tol ) {
      if(0) {  //////////////////////////////////////////// <--- just set zero temporary.. dome moving time is not yet applied..

        // ..
        // ...

      }
      else {
        dDomMovingSec = 0.0;
      }

      // if(AutoDome) {
      //   ..
      // }

      //// UT_OBS check and proceed to do

      nDeltaSec = (int)(posc->line[i].secobs-1660000000U) - (int)((UINT)time(NULL)-1660000000U) - OSC_DEFAULT_PREPSEC - MAX(dTelMovingSec,dDomMovingSec);

      if( posc->line[i].uttol < abs(nDeltaSec) ) {   ///// currently out of tolerance

          if( nDeltaSec < 0 ) {  ////// UT_OBS passed

              nNextDeltaSec = (int)(posc->line[n].secobs-1660000000U) - (int)((UINT)time(NULL)-1660000000U) - OSC_DEFAULT_PREPSEC - MAX(dTelMovingSec,dDomMovingSec);

              if( nNextDeltaSec > -nDeltaSec && posc->line[n].type==OSC_TYPE_EXP && 
                //nNextDeltaSec > OSC_DEFAULT_PREPSEC + (int)posc->line[i].exptime + OSC_DEFAULT_READSEC ) {   // v0.8.0
                  nNextDeltaSec > OSC_DEFAULT_PREPSEC + (int)posc->line[i].exptime + OSC_DEFAULT_READSEC + OSC_DEFAULT_ADVANCE ) {   // v0.8.3
                //// if current shot is better than next shot, and no problem to take next shot at UT-OBS, just proceeds current shot
                posc->flag_additionalshot = 1;   // making this shot be one additional shot while waiting for UT_OBS
                cnt_waiting_utobs = 0;
                GRNTEXT;sprintf(cmsg, "OSC.STATUS: LINE#%04d EXP#%d (%s) proceeds as additional shot since better than next exposure though UT_OBS passed (%d sec past UT_OBS %s)\n", 
                                       (i+1), expidx_curr, posc->line[i].label, -nDeltaSec, posc->line[i].utobs);_msgout(cmsg);
              }
              else {  
                //// next shot is better, or no time to take additional shot with keeping the UT_OBS of next shot
                posc->count_process = posc->interval_process;  // making no delay in the main loop
                utpassed = 1;  // no notice for skip anymore (v0.8.0)
                cnt_waiting_utobs = 0;
                GRNTEXT;sprintf(cmsg, "OSC.STATUS: LINE#%04d EXP#%d (%s) skipped since UT_OBS passed\n", (i+1), expidx_curr, posc->line[i].label);_msgout(cmsg);
                goto CURRENT_LINE_SKIP;
              }

          }
          else {  ////// UT_OBS comming

            //if( nDeltaSec > OSC_DEFAULT_PREPSEC + (int)posc->line[i].exptime + OSC_DEFAULT_READSEC ) {   // v0.8.0
              if( nDeltaSec > OSC_DEFAULT_PREPSEC + (int)posc->line[i].exptime + OSC_DEFAULT_READSEC + OSC_DEFAULT_ADVANCE ) {   // v0.8.3
                //// we have time to take a shot while waiting for UT_OBS
                posc->flag_additionalshot = 1;   // making this shot be one additional shot while waiting for UT_OBS
                cnt_waiting_utobs = 0;
                GRNTEXT;sprintf(cmsg, "OSC.STATUS: LINE#%04d EXP#%d (%s) proceeds as additional shot while waiting for UT_OBS (%d sec left until UT_OBS %s)\n", 
                                       (i+1), expidx_curr, posc->line[i].label, nDeltaSec, posc->line[i].utobs);_msgout(cmsg);
              }
              else {  
                //// we should wait for UT_OBS since no time to take additional shot
                if( (cnt_waiting_utobs++)%10 == 0 ) {
                  GRNTEXT;sprintf(cmsg, "OSC.STATUS: LINE#%04d EXP#%d (%s) delayed to wait for UT_OBS (%d sec left until UT_OBS %s)\n", 
                                       (i+1), expidx_curr, posc->line[i].label, nDeltaSec, posc->line[i].utobs);_msgout(cmsg);
                }
                return OSC_RTN_NOERR;   // delay exposure on going process for this exp line
              }

          }

      }

    }

    //////// check TCS status and telescope positon, and command to pointing for the current exposure..

    if( !posc->line[i].flag_movedisable && !posc->flag_exposing ) {

      //// check TCS status for the current exposure ////////////////////////////////

      if( psys->telstatus==TELSTATUS_DISABLED ) { 
        if( !(posc->procflags&OSC_CHKBIT_ENABLESERVO) ) posc->procflags |= OSC_CMDBIT_ENABLESERVO;
      }

      if(   psys->telstatus==TELSTATUS_HOLDING ) {
        if( !(posc->procflags&OSC_CHKBIT_ONTRACKING) ) posc->procflags |= OSC_CMDBIT_ONTRACKING;
      }

      if(   psys->telstatus==TELSTATUS_STOW ) {
        if( !(posc->procflags&OSC_CHKBIT_ONTRACKING) ) posc->procflags |= OSC_CMDBIT_ONTRACKING;

      }

      //// setup non-sidereal tracking for the current exposure ////////////////////////////////

      if( !posc->flag_nstchecked && psys->camstatus>=CAMSTATUS_READ_1 ) {

        BLUTEXT;sprintf(cmsg, "OSC.STATUS: SETUP NST FOR CURRENT EXPOSURE\n");_vmsgout(cmsg);

        if( fabs(posc->line[i].velra)<0.000001 && fabs(posc->line[i].veldec)<0.000001 ) {

          sprintf(cmsg, "DBG: Disable NST since velra & veldec are all zero\n");_dbgmsgout(cmsg);

          /* 
          for(retry=0;retry<3;retry++) { 
            //strcpy(posc->reschkcmd, "nstset");
            strcpy(lineinput, "nstset  0.0  0.0");
            rtn = OscCommand(lineinput);
            if(rtn==CMD_OK) break;
            usleep(100);
          }
          if(retry>=3) {
            strcpy(reply, "Failed to set PC-TCS RA/DEC velocity to 0.0 for NST disable fully");
            OscCommand("opause");
            return OSC_RTN_ERROR;
          } //////// for DBG
          */

          posc->flag_nstchecked = 1;  

          if(psys->nston) {

            sprintf(cmsg, "DBG: TCS paddle has been on, now off it\n");_dbgmsgout(cmsg);

            for(retry=0;retry<3;retry++) {
              //strcpy(posc->reschkcmd, "tpad");
              //strcpy(lineinput, "tpad  off off off off");
              strcpy(lineinput, "nstoff");   // v0.8.0
              rtn = OscCommand(lineinput);
              if(rtn==CMD_OK) break;
              usleep(100);
            }
            if(retry>=3) {
              strcpy(reply, "Failed to control TCS paddle for NST off !!");
              //OscCommand("opause");
              //return OSC_RTN_ERROR;
              return OSC_RTN_WARNING;  // don't the observation only due to NST-control failure (v0.8.5)
            }

          }

        }
        else {

          sprintf(cmsg, "DBG: Setup & Enable NST since velra or veldec is not zero\n");_dbgmsgout(cmsg);

          for(retry=0;retry<3;retry++) {
            //strcpy(posc->reschkcmd, "nstset");
            sprintf(lineinput, "nstset  %+.5f  %+.5f", posc->line[i].velra, posc->line[i].veldec);
            rtn = OscCommand(lineinput);
            if(rtn==CMD_OK) break;
            usleep(100);
          }
          if(retry>=3) {
            strcpy(reply, "Failed to setup PC-TCS RA/DEC velocity for NST");
            OscCommand("opause");
            return OSC_RTN_ERROR;
          }

          for(retry=0;retry<3;retry++) {
            //strcpy(posc->reschkcmd, "tpad");
            //strcpy(lineinput, "tpad  on off  on off");
            strcpy(lineinput, "nston");   // v0.8.0
            rtn = OscCommand(lineinput);
            if(rtn==CMD_OK) break;
            usleep(100);
          }
          if(retry>=3) {
            strcpy(reply, "Failed to control TCS paddle for NST on");
            OscCommand("opause");
            return OSC_RTN_ERROR;
          }

          posc->flag_nstchecked = 1;

        }

        sprintf(cmsg, "DBG: NST setup complete\n");_dbgmsgout(cmsg);

      }

      //// check telescope position for the current exposure ////////////////////////////////

      if( !posc->flag_pointed && !(posc->procflags&OSC_CMDBIT_POINTING) && !(posc->procflags&OSC_CHKBIT_POINTING) ) {

        double   ra_corr = posc->line[i].ra_h ;
        double  dec_corr = posc->line[i].dec_d;
        double   ha_dest;
        double    ad_ra  = (63.0/60.0/2.0/15.0);  // angular distance between field center and CCD center
        double    ad_dec = (66.0/60.0/2.0     );
        double  diff_ra ;   // = (  ra_current -  ra_destination ) / cos(dec) in arcsec
        double  diff_dec;   // = ( dec_current - dec_destination ) in arcsec

        ha_dest = psys->ha_h + ( psys->ra_h - posc->line[i].ra_h ) + 20.0/3600.0;  // destination HA after init+erase
        if(ha_dest<-12.0) ha_dest+=24.0;  if(ha_dest>=+12.0) ha_dest-=24.0; // added for 24h range matching at v0.4.4

        //ad_ra  -= (60.0/16.0*1.0/60.0/15.0);  // offset to field center and for position the object on center of strip
        //ad_dec -= (60.0/16.0*1.0/60.0     );  // same offset as RA
        // sould be changed at TCSAgent

        switch(posc->line[i].copt[0]) {  // for offset correction enabled, v0.3.2
          case '-':                                                               break;  // No correction
          case '0':                                                               break;  // No correction
          case '1':  offset_blg( &ra_corr, &dec_corr, ha_dest, CORTABLE_BLGOFF);  break;  // BLG correction
          case 'k': 
          case 'K':  ra_corr += ad_ra / cosd(dec_corr);  dec_corr -= ad_dec;      break;  // Offset to K from center
          case 'm': 
          case 'M':  ra_corr -= ad_ra / cosd(dec_corr);  dec_corr -= ad_dec;      break;  // Offset to M from center
          case 't': 
          case 'T':  ra_corr += ad_ra / cosd(dec_corr);  dec_corr += ad_dec;      break;  // Offset to T from center
          case 'n': 
          case 'N':  ra_corr -= ad_ra / cosd(dec_corr);  dec_corr += ad_dec;      break;  // Offset to N from center
          case 'c': 
          case 'C':                                                               break;  // Center: No correction (v0.9.0)
          default :                                                               break;  // default setting: No correction
        }

        //if(ra_corr>=24.0) ra_corr-=24.0;   // until v0.4.3
        //if(ra_corr<0.0) ra_corr+=24.0;  if(ra_corr>=24.0) ra_corr-=24.0;   // modified for more correct 24h range matching at v0.4.4
        // --> these cannot prevent the diff_ra from overing the 24h range (0.0000~23.9999) when 0h is between current RA and destination RA, removed v0.4.4
        
        //diff_ra  = ( ra_corr - psys-> ra_h)*3600.0*15.0 * cosd(dec_corr);   // v0.4.2
        //diff_dec = (dec_corr - psys->dec_d)*3600.0;                         // v0.4.2
        // modified to prevent the diff_ra from overing the -12h ~ +12h range as follows at v0.4.4
        
        //diff_ra  = ( ra_corr - psys-> ra_h);
        //diff_dec = (dec_corr - psys->dec_d);
        diff_ra  = (psys-> ra_h -  ra_corr);  // v0.4.4
        diff_dec = (psys->dec_d - dec_corr);  // v0.4.4
        if(diff_ra<-12.0) diff_ra+=24.0;  if(diff_ra>=+12.0) diff_ra-=24.0;  // added for the -12h ~ +12h range matching at v0.4.4
        diff_ra  *= 3600.0*15.0*cosd(dec_corr);
        diff_dec *= 3600.0;
        
        psys->tcs_tolerance_pointing_corr = psys->tcs_tolerance_pointing + OSC_ADJ_TOL_POINTING * (double)(posc->count_pointing/2);   // v0.4.7
        // OSC_ADJ_TOL_POINTING = 0.2 & OSC_CHKCNT_POINTING = 8 (defined at v0.4.7), tcs_tolerance_pointing = 0.1 (INI runtime config updated on 2020-10-14)
        // 0: 0.1 = 0.1 + 0.2 * (0/2)
        // 1: 0.1 = 0.1 + 0.2 * (1/2)
        // 2: 0.3 = 0.1 + 0.2 * (2/2)
        // 3: 0.3 = 0.1 + 0.2 * (3/2)
        // 4: 0.5 = 0.1 + 0.2 * (4/2)
        // 5: 0.5 = 0.1 + 0.2 * (5/2)
        // 6: 0.7 = 0.1 + 0.2 * (6/2)
        // 7: 0.7 = 0.1 + 0.2 * (7/2)
        // 8: 0.9 = 0.1 + 0.2 * (8/2)
        // 9: 0.9 = 0.1 + 0.2 * (9/2)
        // --> tcs_tolerance_pointing_corr = 0.1 ~ 0.9
        
        if( posc->count_pointing > OSC_CHKCNT_POINTING/2 ) {   // added at v0.4.5, debugged at v0.4.6, modified at v0.4.7, modified at v0.6.7, modified at v0.7.4
          if( fabs(dec_corr) > 50.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.3 ~ 1.1
          if( fabs(dec_corr) > 60.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.5 ~ 1.3
          if( fabs(dec_corr) > 65.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.7 ~ 1.5
          if( fabs(dec_corr) > 70.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.9 ~ 1.7
          if( fabs(dec_corr) > 75.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 1.1 ~ 1.9
          if( fabs(dec_corr) > 80.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 1.3 ~ 2.1
          if( fabs(dec_corr) > 85.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 1.5 ~ 2.3
        }

        if( psys->nston ) {   // v0.7.5
          nsttimestamp = SysTimestamp();
          nstposadd_ra  = psys->cmd_velra  * ( nsttimestamp - psys->timestamp_tmr ) * cosd(dec_corr);
          nstposadd_dec = psys->cmd_veldec * ( nsttimestamp - psys->timestamp_tmr )             ;
          nsttoladd_ra  = fabs( psys->cmd_velra  * ( nsttimestamp - psys->timestamp_tmr ) * 2.0 * cosd(dec_corr) );
          nsttoladd_dec = fabs( psys->cmd_veldec * ( nsttimestamp - psys->timestamp_tmr ) * 2.0                  );
        }
        else {
          nstposadd_ra = nstposadd_dec = 0.0;
          nsttoladd_ra = nsttoladd_dec = 0.0;
        }

      //sprintf(cmsg, "CHK_POSERR:  DIFF_RA %+.2f  DIFF_DEC %+.2f  DEST_HA %+08.4f  DEST_RA %07.4f  DEST_DEC %+07.3f  CMD_NUM %d  FOR CURRENT EXPOSURE\n", 
      //                            diff_ra, diff_dec, ha_dest, ra_corr, dec_corr, posc->count_pointing);_dbgmsgout(cmsg);   
      //                            // CHK_POSERR logging added at v0.4.3, keywords modified & destination Dec logging added at v0.4.4, destination RA & commanded number logging added at v0.4.5
        sprintf(cmsg, "CHK_POSERR:  DIFF_RA %+.2f  DIFF_DEC %+.2f  DEST_HA %+08.4f  DEST_RA %07.4f  DEST_DEC %+07.3f  CMD_NUM %d  DSEC %.2f  VEL_RA %+.2f  VEL_DEC %+.2f  TOL_RA %.2f  TOL_DEC %.2f  FOR CURRENT EXPOSURE\n", 
                                    (diff_ra + nstposadd_ra), (diff_dec + nstposadd_dec), ha_dest, ra_corr, dec_corr, posc->count_pointing, (nsttimestamp - psys->timestamp_tmr), psys->cmd_velra, psys->cmd_veldec, 
                                    (psys->tcs_tolerance_pointing_corr + nsttoladd_ra), (psys->tcs_tolerance_pointing_corr + nsttoladd_dec) );_dbgmsgout(cmsg);
                                    // moved here from right after "diff_dec *= 3600.0;" line, NST correction applied, and tolerance value appended at v0.9.0

      //if( fabs(posc->line[i].ra_h -psys->ra_h )*3600.0*15.0 < psys->tcs_tolerance  &&
      //    fabs(posc->line[i].dec_d-psys->dec_d)*3600.0      < psys->tcs_tolerance  &&
      //      psys->telstatus<=TELSTATUS_TRACKINGS && psys->telstatus>=TELSTATUS_TRACKING ) {  // until v0.3.0
      //    //psys->telstatus==TELSTATUS_TRACKINGS ) {  // oldver
      //if( fabs( ra_corr-psys-> ra_h)*3600.0*15.0 < psys->tcs_tolerance  &&
      //    fabs(dec_corr-psys->dec_d)*3600.0      < psys->tcs_tolerance  &&
      //    TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_TRACKINGS ) {  // v0.3.2
      //if( fabs(diff_ra) < psys->tcs_tolerance_pointing  && fabs(diff_dec) < psys->tcs_tolerance_pointing  &&
      //    TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_TRACKINGS ) {  // v0.4.2
      //if( fabs(diff_ra) < psys->tcs_tolerance_pointing_corr  && fabs(diff_dec) < psys->tcs_tolerance_pointing_corr  &&
      //    TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_TRACKINGS ) {  // v0.4.5
        if( fabs( diff_ra  + nstposadd_ra  ) < ( psys->tcs_tolerance_pointing_corr + nsttoladd_ra  ) && 
            fabs( diff_dec + nstposadd_dec ) < ( psys->tcs_tolerance_pointing_corr + nsttoladd_dec ) &&
            TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_TRACKINGS ) {  // v0.7.5

            posc->flag_pointed = 1;
            posc->count_pointing = 0;
            //posc->procflags &= ~OSC_CMDBIT_POINTING;  // actually this is not necessary because this routine is excuted only when !(posc->procflags&OSC_CMDBIT_POINTING)==1. so, removed to prevent some confution at v0.3.2

            BLUTEXT;sprintf(cmsg, "OSC.STATUS: TELESCOPE POINTED FOR CURRENT EXPOSURE\n");_vmsgout(cmsg);  // v0.2.5
            psys->tpfailed_axis = TEL_AXIS_NO;  // v0.9.0

        }

        else if( TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_OSCILLATE ) {

          if( posc->count_pointing++ > OSC_CHKCNT_POINTING ) {

              // strcpy(reply, "Telescope failed to point at the RA/DEC for current exposure !!"
              //               " The script observation is paused now. "
              //               " Please check RA/Dec & PC-TCS status, and do pointing manually.");  // v0.3.6

              if( psys->telstatus==TELSTATUS_OSCILLATE ) {
                  rtn = psys->unstable_axis;
                  sprintf(reply, "Telescope failed to point due to OSCILLATION on %s", (rtn==TEL_AXIS_BOTH)?"Both RA/Dec axes":(rtn==TEL_AXIS_RA)?"RA axis":(rtn==TEL_AXIS_DEC)?"DEC axis":"unknown axis");
              }
              else {
                       if( fabs( diff_ra  + nstposadd_ra  ) >= ( psys->tcs_tolerance_pointing_corr + nsttoladd_ra  ) &&
                           fabs( diff_dec + nstposadd_dec ) >= ( psys->tcs_tolerance_pointing_corr + nsttoladd_dec ) ) psys->tpfailed_axis = TEL_AXIS_BOTH;
                  else if( fabs( diff_ra  + nstposadd_ra  ) >= ( psys->tcs_tolerance_pointing_corr + nsttoladd_ra  ) ) psys->tpfailed_axis = TEL_AXIS_RA;
                  else if( fabs( diff_dec + nstposadd_dec ) >= ( psys->tcs_tolerance_pointing_corr + nsttoladd_dec ) ) psys->tpfailed_axis = TEL_AXIS_DEC;
                  else                                                                                                 psys->tpfailed_axis = TEL_AXIS_UNKNOWN;
                  rtn = psys->tpfailed_axis;
                  sprintf(reply, "Telescope failed to point at %s", (rtn==TEL_AXIS_BOTH)?"Both RA/Dec dest":(rtn==TEL_AXIS_RA)?"RA dest":(rtn==TEL_AXIS_DEC)?"DEC dest":"the coordinates");
              }
              strcat(reply, " !!  The script observation is paused now.  Please check RA/Dec axes & TCS status, and do pointing manually.");   /////// v0.9.0

              sprintf(cmsg, "REPORT_TPFAILED: Type=%-12s Axis=%-5s CmdRA=%-12s CmdDEC=%-12s CorOpt=%c  TelRA=%-11s TelDEC=%-11s TelHA=%-9s  Epoch=%-8.3f LST=%-8s SecZ=%-4.2f Alt=%-4.1f Az=%-+6.1f  "
                            "DiffRA=%+.2f DiffDEC=%+.2f DestRA=%07.4f DestDec=%+07.3f DestHA=%+08.4f CmdNum=%d  DelSec=%.2f VelRA=%+.2f VelDEC=%+.2f TolRA=%.2f TolDec=%.2f PointFor=%-9s\n", 
                            (psys->telstatus==TELSTATUS_OSCILLATE)?"OSCILLATION":"POINTINGFAIL", (rtn==TEL_AXIS_BOTH)?"BOTH":(rtn==TEL_AXIS_RA)?"RA":(rtn==TEL_AXIS_DEC)?"DEC":"UNDEF", 
                            posc->line[i].ra, posc->line[i].dec, posc->line[i].copt[0], psys->ra, psys->dec, psys->ha, psys->epoch_y, psys->lst, psys->secz, psys->alt_d, psys->az_d, 
                            (diff_ra + nstposadd_ra), (diff_dec + nstposadd_dec), ra_corr, dec_corr, ha_dest, posc->count_pointing, (nsttimestamp - psys->timestamp_tmr), psys->cmd_velra, psys->cmd_veldec, 
                            (psys->tcs_tolerance_pointing_corr + nsttoladd_ra), (psys->tcs_tolerance_pointing_corr + nsttoladd_dec), "CURRENT" );_dbgmsgout(cmsg);   /////// v0.9.0

              posc->flag_pointed = 1;
              posc->count_pointing = 0;

              if(psys->nston) {   // v0.7.5
                sprintf(cmsg, "DBG: TCS paddle off before osc pause\n");_dbgmsgout(cmsg);
                for(retry=0;retry<3;retry++) {
                  //strcpy(lineinput, "tpad  off off off off");
                  strcpy(lineinput, "nstoff");   // v0.8.0
                  rtn = OscCommand(lineinput);
                  if(rtn==CMD_OK) break;
                  usleep(100);
                }
                if(retry>=3) strcat(reply, " As well as Failed to control TCS paddle for NST off !! Please check PC-TCS Guide/Drift status..");
              }

              OscCommand("opause");

              return OSC_RTN_ERROR;

          }
          else {    // RA/Dec error is large or Tracking error is unstable
            
              //// Checking clearance between the PC-TCS limit and destination, added at v0.4.0, and modified at v0.4.4 /////////////////////////////////////////////////////////////////////////////////////////              
              //

              dClearance = ( psys->tcs_limit_ha - ha_dest ) * 15.0;   // Clearance between west HA limit and destination
              if( dClearance <= 0.0 ) {
                  REDTEXT;sprintf(cmsg, "WARNING: Destination HA is out of the limit, LINE#%04d EXP#%d (%s) skipped !!\n", (i+1), expidx_curr, posc->line[i].label);_msgout(cmsg);
                  goto CURRENT_LINE_SKIP;
              }
              else if( dClearance < psys->tcs_limit_warning ) { 
                  CYATEXT;sprintf(cmsg, "Warning: Destination HA is near the limit !\n");_msgout(cmsg);
              }

              dClearance = psys->tcs_limit_dec_n - posc->line[i].dec_d;   // Clearance between north Dec limit and destination
              if( dClearance <= 0.0 ) {
                  REDTEXT;sprintf(cmsg, "WARNING: Destination DEC is out of the north limit, LINE#%04d EXP#%d (%s) skipped !!\n", (i+1), expidx_curr, posc->line[i].label);_msgout(cmsg);
                  goto CURRENT_LINE_SKIP;
              }
              else if( dClearance < psys->tcs_limit_warning ) { 
                  CYATEXT;sprintf(cmsg, "Warning: Destination DEC is near the limit in North !\n");_msgout(cmsg);
              }

              dClearance = posc->line[i].dec_d - psys->tcs_limit_dec_s;   // Clearance between south Dec limit and destination
              if( dClearance <= 0.0 ) {
                  REDTEXT;sprintf(cmsg, "WARNING: Destination DEC is out of the south limit, LINE#%04d EXP#%d (%s) skipped !!\n", (i+1), expidx_curr, posc->line[i].label);_msgout(cmsg);
                  goto CURRENT_LINE_SKIP;
              }
              else if( dClearance < psys->tcs_limit_warning ) { 
                  CYATEXT;sprintf(cmsg, "Warning: Destination DEC is near the limit in South!\n");_msgout(cmsg);
              }
              
              dClearance = GetAltitude(ha_dest, posc->line[i].dec_d, psys->tcs_latitude) - psys->tcs_limit_alt;   // Clearance between Altitude limit and destination
              if( dClearance <= 0.0 ) {
                  REDTEXT;sprintf(cmsg, "WARNING: Destination ALT is lower than the limit, LINE#%04d EXP#%d (%s) skipped !!\n", (i+1), expidx_curr, posc->line[i].label);_msgout(cmsg);
                  goto CURRENT_LINE_SKIP;
              }
              else if( dClearance < psys->tcs_limit_warning && ha_dest > 0.0 ) { 
                  CYATEXT;sprintf(cmsg, "Warning: Destination ALT is near the limit !\n");_msgout(cmsg);
              }

              //
              //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
              
              posc->procflags |= OSC_CMDBIT_POINTING;    // command to move telescope
              
          }

        }

      }

      //// command to enable servo & check response for the current exposure ////////////////////////////////

      //if( posc->procflags&OSC_CMDBIT_ENABLESERVO && posc->procflags<0x0100 &&  // if the other checking flags are all down
      //  ( psys->camstatus==CAMSTATUS_READ_2 || psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) ) {
      if( posc->procflags&OSC_CMDBIT_ENABLESERVO && posc->procflags<0x0100 && psys->camstatus>=CAMSTATUS_READ_1  ) {  // if the other checking flags are all down

        posc->flag_responseok = 0;
        posc->flag_responsecheck = 1;
        posc->count_responsecheck = 0;
        strcpy(posc->reschkcmd, "tcmd");
        sprintf(lineinput, "tcmd unkill");
        OscCommand(lineinput);

        posc->procflags &= ~OSC_CMDBIT_ENABLESERVO;
        posc->procflags |=  OSC_CHKBIT_ENABLESERVO;

      }

      if( posc->procflags&OSC_CHKBIT_ENABLESERVO ) {

        if( posc->flag_responseok ) {
          posc->flag_responseok = 0;
          posc->flag_responsecheck = 0;
          posc->count_responsecheck = 0;
          memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
          posc->procflags &= ~OSC_CHKBIT_ENABLESERVO;
        }
        else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
          posc->procflags |=  OSC_CMDBIT_ENABLESERVO;
          posc->procflags &= ~OSC_CHKBIT_ENABLESERVO;
          sprintf(reply, "Script observation process failed to receive OK response."
                         " The process will retry to command line '%s'.", lineinput);
          posc->flag_responsecheck = 0;
          return OSC_RTN_WARNING;
        }

      }

      //// command to enable tracking & check response for the current exposure ////////////////////////////////

      //if( posc->procflags&OSC_CMDBIT_ONTRACKING && posc->procflags<0x0100 && 
      //    ( psys->camstatus==CAMSTATUS_READ_2 || psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) ) {
      if( posc->procflags&OSC_CMDBIT_ONTRACKING && posc->procflags<0x0100 && psys->camstatus>=CAMSTATUS_READ_1  ) {  // if TC cmd, No error in IDLE_3

        posc->flag_responseok = 0;
        posc->flag_responsecheck = 1;
        posc->count_responsecheck = 0;
        strcpy(posc->reschkcmd, "tcmd");
        sprintf(lineinput, "tcmd track on");
        OscCommand(lineinput);

        posc->procflags &= ~OSC_CMDBIT_ONTRACKING;
        posc->procflags |=  OSC_CHKBIT_ONTRACKING;

      }

      if( posc->procflags&OSC_CHKBIT_ONTRACKING ) {

        if( posc->flag_responseok ) {
          posc->flag_responseok = 0;
          posc->flag_responsecheck = 0;
          posc->count_responsecheck = 0;
          memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
          posc->procflags &= ~OSC_CHKBIT_ONTRACKING;
        }
        else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
          posc->procflags |=  OSC_CMDBIT_ONTRACKING;
          posc->procflags &= ~OSC_CHKBIT_ONTRACKING;
          sprintf(reply, "Script observation process failed to receive OK response."
                         " The process will retry to command line '%s'.", lineinput);
          posc->flag_responsecheck = 0;
          return OSC_RTN_WARNING;
        }

      }

      //// command to slew telescope & check response for the current exposure ////////////////////////////////

      //if( posc->procflags&OSC_CMDBIT_POINTING && posc->procflags<0x0100 && 
      //    psys->telstatus>=TELSTATUS_TRACKING && psys->telstatus<=TELSTATUS_OSCILLATE && 
      //    ( psys->camstatus==CAMSTATUS_READ_2 || psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) ) {
      //if( posc->procflags&OSC_CMDBIT_POINTING && posc->procflags<0x0100 && psys->camstatus>=CAMSTATUS_READ_1 && 
      //    psys->telstatus>=TELSTATUS_TRACKING && psys->telstatus<=TELSTATUS_OSCILLATE ) {
      if( posc->procflags&OSC_CMDBIT_POINTING && posc->procflags<0x0100 && psys->camstatus>=CAMSTATUS_READ_1 && 
          psys->telstatus>=TELSTATUS_TRACKING && psys->telstatus<=TELSTATUS_OSCILLATE && --posc->count_tmrwaiting < 0  ) {  // v0.7.7

        posc->flag_responseok = 0;
        posc->flag_responsecheck = 1;
        posc->count_responsecheck = 0;
        strcpy(posc->reschkcmd, "tmr");
        //sprintf(lineinput, "tmr  %s  %s  %c", posc->line[i].ra, posc->line[i].dec, posc->line[i].copt);
        if( posc->line[i].copt[0] == 'c' || posc->line[i].copt[0] == 'C' )  // v0.7.0 temporary
          //sprintf(lineinput, "tmr  %s  %s  %c", posc->line[i].ra, posc->line[i].dec, 'm');
            sprintf(lineinput, "tmr  %s  %s  %c", posc->line[i].ra, posc->line[i].dec, '0');  // v0.9.0
        else
            sprintf(lineinput, "tmr  %s  %s  %c", posc->line[i].ra, posc->line[i].dec, posc->line[i].copt[0]);
        OscCommand(lineinput);

        posc->count_tmrwaiting = 1;   // v0.7.7
        if(psys->nston) posc->count_tmrwaiting += 2;

        psys->telstatus = TELSTATUS_CHECKING;   // added for debugging frequent tmr command sending in OSCILLATION status at v0.2.8
        psys->duration_stable = 0;  // v0.4.2

        posc->procflags &= ~OSC_CMDBIT_POINTING;
        posc->procflags |=  OSC_CHKBIT_POINTING;

      }

      if( posc->procflags&OSC_CHKBIT_POINTING ) {

        if( posc->flag_responseok ) {
          posc->flag_responseok = 0;
          posc->flag_responsecheck = 0;
          posc->count_responsecheck = 0;
          memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
          posc->procflags &= ~OSC_CHKBIT_POINTING;
        }
        else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
          posc->procflags |=  OSC_CMDBIT_POINTING;
          posc->procflags &= ~OSC_CHKBIT_POINTING;
          sprintf(reply, "Script observation process failed to receive OK response."
                         " The process will retry to command line '%s'.", lineinput);
          posc->flag_responsecheck = 0;
          return OSC_RTN_WARNING;
        }

      }

    }// end of if( !posc->line[i].flag_movedisable && !posc->flag_exposing ) {..}

    else if( posc->line[i].flag_movedisable && !posc->flag_exposing ) {
      posc->flag_pointed = 1;
      posc->count_pointing = 0;
      posc->procflags &= ~OSC_CMDBIT_POINTING;
    }


    //////// check Filter and ICS status and command to configure exposure for the current exposure..

    //// check filter for the current exposure ////////////////////////////////

    //if( !posc->flag_exposing && !posc->flag_filtercommanded  ) posc->procflags |= OSC_CMDBIT_SETFILTER;    // --> do unconditionally temporary, current filter number check rourine reserved..
    if( !posc->flag_exposing && !posc->flag_filterchanged ) {  // v0.1.3
      if( posc->line[i].filter_n == psys->filternum ) {
          posc->flag_filterchanged = 1;
          posc->count_filtercommanded = 0;
          posc->procflags &= ~OSC_CMDBIT_SETFILTER;
      }
      else if( posc->count_filtercommanded<OSC_CHKCNT_FILTER || strcasecmp(posc->line[i].filter,psys->filtername) ) {  // shouldn't this include "posc->line[i].filter_n != psys->filternum" ??
          //if( !(posc->procflags&OSC_CHKBIT_SETFILTER) && strcmp(psys->filteropstat,"RUNNING") ) posc->procflags |= OSC_CMDBIT_SETFILTER;
          if( !(posc->procflags&OSC_CHKBIT_SETFILTER) && strcmp(psys->filteropstat,"RUNNING") && strcmp(psys->fsastatus,"RUNNING") ) posc->procflags |= OSC_CMDBIT_SETFILTER;
          //// modified for debugging 'WAIT' response problem due to delayed filteropstat update at v0.4.4
      }
      else if( posc->count_filtercommanded>=OSC_CHKCNT_FILTER ) {
          strcpy(reply, "Script obs process failed to confirm the filter for current exposure !!"
                        " Please check the filter status and control it manually.");
          posc->flag_filterchanged = 1;
          posc->count_filtercommanded = 0;
          posc->procflags &= ~OSC_CMDBIT_SETFILTER;
          //return OSC_RTN_WARNING;  // modified to pause & error display at v0.4.4
          if(psys->nston) {   // v0.7.5
            sprintf(cmsg, "DBG: TCS paddle off before osc pause\n");_dbgmsgout(cmsg);
            for(retry=0;retry<3;retry++) {
              //strcpy(lineinput, "tpad  off off off off");
              strcpy(lineinput, "nstoff");   // v0.8.0
              rtn = OscCommand(lineinput);
              if(rtn==CMD_OK) break;
              usleep(100);
            }
            if(retry>=3) strcat(reply, "As well as failed to control TCS paddle for NST off !! Please check PC-TCS Guide/Drift status...");
          }
          OscCommand("opause");
          return OSC_RTN_ERROR;          
      }
    }
    // MEMO: don't need to use filtername to refer to commanded filter info (supposed filter) ?

    //// check exposure configuration for the current exposure ////////////////////////////////

    if( !posc->flag_exposing && !posc->flag_projidcommanded  ) {    // added at v0.6.4, current object setting check routine reserved using >k.ic exp
      if( !(posc->procflags&OSC_CHKBIT_SETPROJID ) ) posc->procflags |= OSC_CMDBIT_SETPROJID;
    }   

    if( !posc->flag_exposing && !posc->flag_objectcommanded  ) {    // --> current object  setting check routine reserved, using >k.ic exp
      if( !(posc->procflags&OSC_CHKBIT_SETOBJECT ) ) posc->procflags |= OSC_CMDBIT_SETOBJECT;
    }   

    if( !posc->flag_exposing && !posc->flag_exptimecommanded ) {    // --> current exp time  setting check routine reserved, using >k.ic exp
      if( !strcmp(posc->line[i].imgtyp,"BIAS") ) posc->flag_exptimecommanded = 1;
      else if( !(posc->procflags&OSC_CHKBIT_SETEXPTIME ) ) posc->procflags |= OSC_CMDBIT_SETEXPTIME;
    }   

    //// command to set filter & check response for the current exposure ////////////////////////////////

    //if( !posc->flag_exposing && posc->procflags&OSC_CMDBIT_SETFILTER && posc->procflags<0x0100 && 
    //    //( psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) && 
    //    //( !strcmp(psys->filteropstat,"STANDBY") || !strcmp(psys->filteropstat,"ERROR") )  ) {
    //        psys->camstatus>=CAMSTATUS_READ_1 && strcmp(psys->filteropstat,"RUNNING") ) {    // no error if TC command although IDLE_3

    if( !posc->flag_exposing && posc->procflags&OSC_CMDBIT_SETFILTER && posc->procflags<0x0100 && 
            psys->camstatus>=CAMSTATUS_READ_1 && strcmp(psys->filteropstat,"RUNNING") && strcmp(psys->fsastatus,"RUNNING") ) {
            //// modified for debugging 'WAIT' response problem due to delayed filteropstat update at v0.4.4

      posc->flag_responseok = 0;
      posc->flag_responsecheck = 1;
      posc->count_responsecheck = 0;
      strcpy(posc->reschkcmd, "filter");
      sprintf(lineinput, "filter  %s", posc->line[i].filter);
      OscCommand(lineinput);

      posc->procflags &= ~OSC_CMDBIT_SETFILTER;
      posc->procflags |=  OSC_CHKBIT_SETFILTER;

      posc->count_filtercommanded++;   // moved here at v0.4.5 (according to modification for debugging 'WAIT' response problem with strcmp(psys->fsastatus,"RUNNING" check for commanding to change filter at v0.4.4)

    }

    if( !posc->flag_exposing && posc->procflags&OSC_CHKBIT_SETFILTER ) {

      if( posc->flag_responseok ) {
        posc->flag_responseok = 0;
        posc->flag_responsecheck = 0;
        posc->count_responsecheck = 0;
        //posc->count_filtercommanded++;
        memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
        posc->procflags &= ~OSC_CHKBIT_SETFILTER;
      }
      else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
        posc->procflags |=  OSC_CMDBIT_SETFILTER;
        posc->procflags &= ~OSC_CHKBIT_SETFILTER;
        sprintf(reply, "Script observation process failed to receive OK response."
                       " The process will retry to command line '%s'.", lineinput);
        posc->flag_responsecheck = 0;
        return OSC_RTN_WARNING;
      }

    }

    //// command to configure projid & check response for the current exposure //////////////////////////////// added at v0.6.4

    if( !posc->flag_exposing && posc->procflags&OSC_CMDBIT_SETPROJID && posc->procflags<0x0100 && 
          ( psys->camstatus==CAMSTATUS_READ_3 || ( psys->camstatus>=CAMSTATUS_READY  && psys->status_fitssaved==1 ) ) ) {

      posc->flag_responseok = 0;
      posc->flag_responsecheck = 1;
      posc->count_responsecheck = 0;
      strcpy(posc->reschkcmd, "projid");
      sprintf(lineinput, "ProjID  %s", posc->line[i].projid);
      OscCommand(lineinput);

      posc->procflags &= ~OSC_CMDBIT_SETPROJID;
      posc->procflags |=  OSC_CHKBIT_SETPROJID;

    }

    if( !posc->flag_exposing && posc->procflags&OSC_CHKBIT_SETPROJID ) {

      if( posc->flag_responseok ) {
        posc->flag_responseok = 0;
        posc->flag_responsecheck = 0;
        posc->count_responsecheck = 0;
        posc->flag_projidcommanded = 1;
        memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
        posc->procflags &= ~OSC_CHKBIT_SETPROJID;
      }
      else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
        posc->procflags |=  OSC_CMDBIT_SETPROJID;
        posc->procflags &= ~OSC_CHKBIT_SETPROJID;
        sprintf(reply, "Script observation process failed to receive OK response."
                       " The process will retry to command line '%s'.", lineinput);
        posc->flag_responsecheck = 0;
        return OSC_RTN_WARNING;
      }

    }

    //// command to configure imagetype and object name & check response for the current exposure ////////////////////////////////

    if( !posc->flag_exposing && posc->procflags&OSC_CMDBIT_SETOBJECT && posc->procflags<0x0100 && 
        //( psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) ) {  // Error if ICS commands at IDLE_3 --> error to set image type & object name during integration for next exposure
        //( psys->camstatus==CAMSTATUS_READ_3 || ( psys->camstatus==CAMSTATUS_IDLE_3 && psys->status_fitssaved==1 ) ) ) {  // Error if ICS commands at IDLE_3, debugged at v0.2.8
          ( psys->camstatus==CAMSTATUS_READ_3 || ( psys->camstatus>=CAMSTATUS_READY  && psys->status_fitssaved==1 ) ) ) {  // v0.4.5

      posc->flag_responseok = 0;
      posc->flag_responsecheck = 1;
      posc->count_responsecheck = 0;
      strcpy(posc->reschkcmd, posc->line[i].imgtyp);
      sprintf(lineinput, "%s  %s", posc->line[i].imgtyp, posc->line[i].object);
      OscCommand(lineinput);

      posc->procflags &= ~OSC_CMDBIT_SETOBJECT;
      posc->procflags |=  OSC_CHKBIT_SETOBJECT;

    }

    if( !posc->flag_exposing && posc->procflags&OSC_CHKBIT_SETOBJECT ) {

      if( posc->flag_responseok ) {
        posc->flag_responseok = 0;
        posc->flag_responsecheck = 0;
        posc->count_responsecheck = 0;
        posc->flag_objectcommanded = 1;
        memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
        posc->procflags &= ~OSC_CHKBIT_SETOBJECT;
      }
      else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
        posc->procflags |=  OSC_CMDBIT_SETOBJECT;
        posc->procflags &= ~OSC_CHKBIT_SETOBJECT;
        sprintf(reply, "Script observation process failed to receive OK response."
                       " The process will retry to command line '%s'.", lineinput);
        posc->flag_responsecheck = 0;
        return OSC_RTN_WARNING;
      }

    }

    //// command to configure exposure time & check response for the current exposure ////////////////////////////////

    if( !posc->flag_exposing && posc->procflags&OSC_CMDBIT_SETEXPTIME && posc->procflags<0x0100 && 
        //( psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) ) {  // Error if ICS commands at IDLE_3 --> error to set image type & object name during integration for next exposure
        //( psys->camstatus==CAMSTATUS_READ_3 || ( psys->camstatus==CAMSTATUS_IDLE_3 && psys->status_fitssaved==1 ) ) ) {  // Error if ICS commands at IDLE_3, debugged at v0.2.8
          ( psys->camstatus==CAMSTATUS_READ_3 || ( psys->camstatus>=CAMSTATUS_READY  && psys->status_fitssaved==1 ) ) ) {  // v0.4.5

      posc->flag_responseok = 0;
      posc->flag_responsecheck = 1;
      posc->count_responsecheck = 0;
      strcpy(posc->reschkcmd, "exp");
      sprintf(lineinput, "exp  %.1f", posc->line[i].exptime);
      OscCommand(lineinput);

      posc->procflags &= ~OSC_CMDBIT_SETEXPTIME;
      posc->procflags |=  OSC_CHKBIT_SETEXPTIME;

    }

    if( !posc->flag_exposing && posc->procflags&OSC_CHKBIT_SETEXPTIME ) {

      if( posc->flag_responseok ) {
        posc->flag_responseok = 0;
        posc->flag_responsecheck = 0;
        posc->count_responsecheck = 0;
        posc->flag_exptimecommanded = 1;
        memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
        posc->procflags &= ~OSC_CHKBIT_SETEXPTIME;
      }
      else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
        posc->procflags |=  OSC_CMDBIT_SETEXPTIME;
        posc->procflags &= ~OSC_CHKBIT_SETEXPTIME;
        sprintf(reply, "Script observation process failed to receive OK response."
                       " The process will retry to command line '%s'.", lineinput);
        posc->flag_responsecheck = 0;
        return OSC_RTN_WARNING;
      }

    }
    
    //// check whether ready to go or yet.. ////////////////////////////////

    //if( !posc->flag_exposing && !posc->procflags ) {    // if procflags == 0, then all ready.
    //if( !posc->flag_exposing && !posc->procflags && posc->flag_pointed ) {    // if procflags == 0x0000 && flag_pointed == 1, then all ready. modified at v0.3.6
    if( !posc->flag_exposing && !posc->procflags && posc->flag_pointed && posc->flag_filterchanged ) {    // if procflags == 0x0000 && telescope pointed && finter changed, then all ready. modified at v0.4.4     

      //if( !posc->flag_running ) goto LINE_FINISH;   // stop before starting exposure  --> no no, we have the 'oabort' command.
      //if( !(posc->procflags&OSC_CHKBIT_STARTEXP ) && strcmp(psys->filteropstat,"RUNNING") &&
      //      TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_TRACKINGS ) posc->procflags |= OSC_CMDBIT_STARTEXP;  --> replaced with below because now flag_pointed is checked at v0.3.6  
      //                                                                                                                                 flag_pointed is set to 1 only when telstatus is TRACKING or TRACKINGS.
      
      //if( !(posc->procflags&OSC_CHKBIT_STARTEXP ) && strcmp(psys->filteropstat,"RUNNING") ) posc->procflags |= OSC_CMDBIT_STARTEXP;
      //if( !(posc->procflags&OSC_CHKBIT_STARTEXP ) && strcmp(psys->filteropstat,"RUNNING") && strcmp(psys->fsastatus,"RUNNING") ) posc->procflags |= OSC_CMDBIT_STARTEXP;
      //// modified for debugging 'WAIT' response problem due to delayed filteropstat update at v0.4.4
      
      //if( !(posc->procflags&OSC_CHKBIT_STARTEXP) ) posc->procflags |= OSC_CMDBIT_STARTEXP;    //// filter running status check is also removed because place the flag_filterchanged check above at v0.4.4
      //// replaced as below at v0.9.4

    //if( psys->domerot!=DOME_ROTATING && psys->domeshut!=DOME_MOVING ) {   // domerot/shut is set to IDLE unless ROTATING/MOVING status in UpdateDomeStatus(). 
    //if( psys->domerot==DOME_IDLE && psys->domeshut==DOME_IDLE ) {         // Thus this statement is also ok.. anyway decision making is set as below finally.. (v0.9.4)

    //if( psys->domerot==DOME_ROTATING ) {   // check dome rotation status (until v0.9.8)
      if( psys->domerot==DOME_ROTATING && psys->alt_d<DEFAULT_DOME_ROTCHK_MAXALT ) {   // check dome rotation status only when telescope altitude < ConfigRotChkMaxAlt to dome rotation check (v0.9.9)
        if(posc->waiting_dome_rotation<1) {   // notice only once (v0.9.4)
          BLUTEXT;sprintf(cmsg, "OSC.STATUS: WAITING FOR DOME ROTATION TO COMPLETE..\n");_msgout(cmsg);
        }
        else {
          BLUTEXT;sprintf(cmsg, "OSC.STATUS: WAITING FOR DOME ROTATION TO COMPLETE..\n");_vmsgout(cmsg);
        }
        posc->waiting_dome_rotation++;
        if(posc->waiting_dome_rotation>DEFAULT_DOME_ERRTH_WAITROT) {   // append anomaly handling for waiting time at v0.9.8
          psys->redis_failnum_domerot =-1;
          psys->redis_domerot = REDIS_DOMEROT_UNKNOWN;
          strcpy(cmsg, "OSC.WARNING: Too long operation time for dome rotation, Redis dome rotation check DISABLED !!\n");MAGTEXT;_msgout(cmsg);
          strcpy(cmsg, ">> Please check dome rotation controller and software.\n");BLUTEXT;_msgout(cmsg);//_vmsgout(cmsg);   // output in normal mode for observer guidance..
        }
      }
      else if( psys->domeshut==DOME_MOVING ) {   // check dome shutter status
        if(posc->waiting_dome_shutter<1) {   // notice only once (v0.9.4)
          BLUTEXT;sprintf(cmsg, "OSC.STATUS: WAITING FOR DOME SHUTTER TO COMPLETE..\n");_msgout(cmsg);
        }
        else {
          BLUTEXT;sprintf(cmsg, "OSC.STATUS: WAITING FOR DOME SHUTTER TO COMPLETE..\n");_vmsgout(cmsg);
        }
        posc->waiting_dome_shutter++;
        if(posc->waiting_dome_shutter>DEFAULT_DOME_ERRTH_WAITSHUT) {   // append anomaly handling for waiting time at v0.9.8
          psys->redis_failnum_domeshut =-1;
          psys->redis_domeshut = REDIS_DOMESHUT_UNKNOWN;
          strcpy(cmsg, "OSC.WARNING: Too long operation time for dome shutter positioning, Redis dome shutter check DISABLED !!\n");
          strcpy(cmsg, ">> Please check dome shutter controller and software.\n");BLUTEXT;_msgout(cmsg);//_vmsgout(cmsg);   // output in normal mode for observer guidance..
          MAGTEXT;_msgout(cmsg);          
        }
      }
      else {
        if( !(posc->procflags&OSC_CHKBIT_STARTEXP) ) posc->procflags |= OSC_CMDBIT_STARTEXP;  // Go!
      }
    }

    //// command to start exposure & check response ////////////////////////////////

    if( !posc->flag_exposing && posc->procflags&OSC_CMDBIT_STARTEXP && posc->procflags<0x0100 && 
        //psys->camstatus==CAMSTATUS_IDLE_3 ) {
        //psys->camstatus>=CAMSTATUS_IDLE_3 ) {   // 'GO' available when IDLE_3, and READY as well, modified at v0.4.5
          psys->camstatus>=CAMSTATUS_IDLE_3 && posc->flag_running ) {   // flag_running check for debugging one-more-exposure error after ostop, modified at v0.5.7

      posc->flag_responseok = 0;
      posc->flag_responsecheck = 1;
      posc->count_responsecheck = 0;
      strcpy(posc->reschkcmd, "Go");
      sprintf(lineinput, "Go");
      OscCommand(lineinput);
      //memset(lineinput, NULL, OSC_MAXLINELEN);

      psys->camstatus = CAMSTATUS_CHECK;   // added to debug filter-change-for-next error, which occurs right after 'Go' commanding, modification at v0.5.9
      expinfo.nStatus = EXPSTATUS_CMDED;   // v1.0.0

      //posc->flag_exposing = 1;    // moved from 'Go' command's response check routine with OSC_CHKBIT_STARTEXP flag check, to debug filter-change-for-next error, which occurs right after 'Go' commanding, modification at v0.5.8
      //// --> not necessary since putting "psys->camstatus = CAMSTATUS_CHECK" setting, removed for rollback at v0.5.9

      posc->procflags &= ~OSC_CMDBIT_STARTEXP;
      posc->procflags |=  OSC_CHKBIT_STARTEXP;

    }

    //if( !posc->flag_exposing && posc->procflags&OSC_CHKBIT_STARTEXP ) {
    //if( posc->procflags&OSC_CHKBIT_STARTEXP ) {   // '!posc->flag_exposing' is removed since "posc->flag_exposing = 1" is moved to 'Go' commanding routine with OSC_CMDBIT_STARTEXP flag check, to debug filter-change-for-next error, modification at v0.5.8
    if( !posc->flag_exposing && posc->procflags&OSC_CHKBIT_STARTEXP ) {   // rollback since using "psys->camstatus = CAMSTATUS_CHECK" flag setting at v0.5.9

      if( posc->flag_responseok ) {
        //posc->flag_exposing = 1;   // moved to 'Go' commanding routine with OSC_CMDBIT_STARTEXP flag check, to debug filter-change-for-next error, which occurs right after 'Go' commanding, modification at v0.5.8
        posc->flag_exposing = 1;     // enabled for rollback since using "psys->camstatus = CAMSTATUS_CHECK" flag setting at v0.5.9
        posc->flag_responseok = 0;
        posc->flag_responsecheck = 0;
        posc->count_responsecheck = 0;
        posc->flag_filterchanged = 0;
        posc->count_filtercommanded = 0;
        posc->flag_projidcommanded = 0;   // added at v0.6.4
        posc->flag_objectcommanded = 0;
        posc->flag_exptimecommanded = 0;
        posc->flag_pointed = 0;
        posc->count_pointing = 0;
        posc->flag_nstchecked = 0;  // v0.6.9
        posc->waiting_dome_rotation = 0;  // v0.9.6
        posc->waiting_dome_shutter = 0;  // v0.9.6
        posc->count_wait_for_shutreload = 0;  // v1.2.0
        posc->procflags |= OSC_CMDBIT_POINTING;   // if exposure started and will proceed readout for long time, 
                                                  // must do pointing at least one time before next exposure, and it is best to do during readout
        memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
        posc->procflags &= ~OSC_CHKBIT_STARTEXP;
        BLUTEXT;sprintf(cmsg, "OSC.STATUS: EXPOSURE & READOUT START\n");_vmsgout(cmsg);  // v0.2.5
        //psys->camstatus = CAMSTATUS_PREP_I;   // added to completely escape CHECK status that was set in above 'Go' commanding routine with OSC_CMDBIT_STARTEXP flag check

        expstart_dSecZ = psys->secz;   // v1.1.0
        expstart_dAlt = psys->alt_d;
        expstart_dAz = psys->az_d;
        expstart_dHA = psys->ha_h;
                                                // not necessary since flag_responseok is set when camstatus >= PREP_x (at v0.5.9)
      }
      else if( posc->count_responsecheck++ > OSC_CHKCNT_EXPSTART ) {
        posc->procflags |=  OSC_CMDBIT_STARTEXP;
        posc->procflags &= ~OSC_CHKBIT_STARTEXP;
        strcpy(reply, "Script observation process failed to start exposure !!"
                      " The process is paused now. Please check ICs status and command 'go' manually.");
        posc->flag_responsecheck = 0;
        //posc->flag_exposing = 0;   // added since "posc->flag_exposing = 1" is moved from 'Go' command's response check routine with OSC_CHKBIT_STARTEXP flag check to 'Go' commanding routine with OSC_CMDBIT_STARTEXP flag check, to debug filter-change-for-next error, modification at v0.5.8
                                     // removed for rollback since using "psys->camstatus = CAMSTATUS_CHECK" flag setting at v0.5.9
        if(psys->nston) {   // v0.7.5
          sprintf(cmsg, "DBG: TCS paddle off before osc pause\n");_dbgmsgout(cmsg);
          for(retry=0;retry<3;retry++) {
            //strcpy(lineinput, "tpad  off off off off");
            strcpy(lineinput, "nstoff");   // v0.8.0
            rtn = OscCommand(lineinput);
            if(rtn==CMD_OK) break;
            usleep(100);
          }
          if(retry>=3) strcat(reply, "AS WELL AS Failed to control TCS paddle for NST off !! Please check PC-TCS Guide/Drift status..");
        }
        OscCommand("opause");
        return OSC_RTN_ERROR;
      }

    }

    //// check exposure and readout finished ////////////////////////////////

    if( posc->flag_exposing && psys->camstatus>=CAMSTATUS_IDLE_3 ) {

      posc->flag_exposing = 0;
      posc->flag_expcomplete = 1;

      //posc->count_filtercommanded = 0;
      //posc->flag_filterchanged = 0;
      //posc->flag_projidcommanded = 0;
      //posc->flag_objectcommanded = 0;
      //posc->flag_exptimecommanded = 0;
      //posc->flag_pointed = 0;
      //posc->count_pointing = 0;
      //posc->flag_nstchecked = 0;  // v0.6.9
      //posc->waiting_dome_rotation = 0;  // v0.9.6
      //posc->waiting_dome_shutter = 0;  // v0.9.6
      //posc->procflags |= OSC_CMDBIT_POINTING;
      // --> do not initialize these flags to keep work by next exposure configuration

      BLUTEXT;sprintf(cmsg, "OSC.STATUS: EXPOSURE & READOUT COMPLETE\n");_vmsgout(cmsg);  // v0.2.5

      goto LINE_FINISH;

    }

  }// end of else if( posc->line[i].type==OSC_TYPE_EXP ) {..}

  else {

    posc->flag_running = posc->flag_paused = osc.flag_delay = 0;
    posc->flag_process = 0;
    posc->count_process = psys->checknum_tcsdata-TCS_DATAUP_INTERVAL*2/3;   // zero point setting when flag_process = 0 as well, added at v0.4.0

    sprintf(reply, "LINE#%d script data type definition error, Script observation stopped.", posc->lineidx);

    return OSC_RTN_ERROR;

  }



  //
  // NEXT EXP LINE PROCESS
  //
  
  //if( posc->line[i].type==OSC_TYPE_EXP && posc->line[n].type==OSC_TYPE_EXP    // Note: if n >= posc->linenum, type == OSC_TYPE_INDEF
  //    && posc->flag_running && posc->flag_preparenextexp ) {  
  //    //&& !posc->flag_paused && posc->flag_running && posc->flag_preparenextexp ) {  // flag_paused added at v0.5.5
  //    // --> flag_paused check removed and rollback at v0.5.6 because flag_paused check is not necessary 
  //    //     since it is checked at the beginning of ProcOsc(), and 
  //    //     the process never arrive this line if flag_paused == 0.
  //// original code until v0.7.9, flag_additionalshot check added at v0.8.0 as follows

  if( posc->line[i].type==OSC_TYPE_EXP && posc->line[n].type==OSC_TYPE_EXP    // Note: if n >= posc->linenum, type == OSC_TYPE_INDEF
      && posc->flag_running && posc->flag_preparenextexp && !posc->flag_additionalshot ) {   // v0.8.0

    //////// check TCS status and telescope positon, and command to pointing for the next exposure..

    if( !posc->line[n].flag_movedisable && posc->flag_exposing ) {  // do during exposing

      //// check TCS status for the next exposure ////////////////////////////////

      if( psys->telstatus==TELSTATUS_DISABLED ) { 
        if( !(posc->procflags&OSC_CHKBIT_ENABLESERVO) ) posc->procflags |= OSC_CMDBIT_ENABLESERVO;
      }

      if(   psys->telstatus==TELSTATUS_HOLDING ) {
        if( !(posc->procflags&OSC_CHKBIT_ONTRACKING) ) posc->procflags |= OSC_CMDBIT_ONTRACKING;
      }

      if(   psys->telstatus==TELSTATUS_STOW ) {
        if( !(posc->procflags&OSC_CHKBIT_ONTRACKING) ) posc->procflags |= OSC_CMDBIT_ONTRACKING;

      }

      //// setup non-sidereal tracking for the next exposure ////////////////////////////////

      if( !posc->flag_nstchecked && psys->camstatus>=CAMSTATUS_READ_1 ) {

        BLUTEXT;sprintf(cmsg, "OSC.STATUS: SETUP NST FOR NEXT EXPOSURE\n");_vmsgout(cmsg);

        if( fabs(posc->line[n].velra)<0.000001 && fabs(posc->line[n].veldec)<0.000001 ) {

          sprintf(cmsg, "DBG: Disable NST since velra & veldec are all zero\n");_dbgmsgout(cmsg);

          /* 
          for(retry=0;retry<3;retry++) { 
            //strcpy(posc->reschkcmd, "nstset");
            strcpy(lineinput, "nstset  0.0  0.0");
            rtn = OscCommand(lineinput);
            if(rtn==CMD_OK) break;
            usleep(100);
          }
          if(retry>=3) {
            strcpy(reply, "Failed to set PC-TCS RA/DEC velocity to 0.0 for NST disable fully");
            OscCommand("opause");
            return OSC_RTN_ERROR;
          } //////// for DBG
          */

          posc->flag_nstchecked = 1;  

          if(psys->nston) {

            sprintf(cmsg, "DBG: TCS paddle has been on, now off it\n");_dbgmsgout(cmsg);

            for(retry=0;retry<3;retry++) {
              //strcpy(posc->reschkcmd, "tpad");
              //strcpy(lineinput, "tpad  off off off off");
              strcpy(lineinput, "nstoff");   // v0.8.0
              rtn = OscCommand(lineinput);
              if(rtn==CMD_OK) break;
              usleep(100);
            }
            if(retry>=3) {
              strcpy(reply, "Failed to control TCS paddle for NST off !");
              //OscCommand("opause");
              //return OSC_RTN_ERROR;
              return OSC_RTN_WARNING;  // don't stop the observation only due to NST-control failure (v0.8.5)
            }

          }

        }
        else {

          sprintf(cmsg, "DBG: Setup & Enable NST since velra or veldec is not zero\n");_dbgmsgout(cmsg);

          for(retry=0;retry<3;retry++) {
            //strcpy(posc->reschkcmd, "nstset");
            sprintf(lineinput, "nstset  %+.5f  %+.5f", posc->line[n].velra, posc->line[n].veldec);
            rtn = OscCommand(lineinput);
            if(rtn==CMD_OK) break;
            usleep(100);
          }
          if(retry>=3) {
            strcpy(reply, "Failed to setup PC-TCS RA/DEC velocity for NST");
            OscCommand("opause");
            return OSC_RTN_ERROR;
          }

          for(retry=0;retry<3;retry++) {
            //strcpy(posc->reschkcmd, "tpad");
            //strcpy(lineinput, "tpad  on off  on off");
            strcpy(lineinput, "nston");   // v0.8.0
            rtn = OscCommand(lineinput);
            if(rtn==CMD_OK) break;
            usleep(100);
          }
          if(retry>=3) {
            strcpy(reply, "Failed to control TCS paddle for NST on");
            OscCommand("opause");
            return OSC_RTN_ERROR;
          }

          posc->flag_nstchecked = 1;

        }

        sprintf(cmsg, "DBG: NST setup complete\n");_dbgmsgout(cmsg);

      }

      //// check telescope position for the next exposure ////////////////////////////////

      if( !posc->flag_pointed && !(posc->procflags&OSC_CMDBIT_POINTING) && !(posc->procflags&OSC_CHKBIT_POINTING) ) {

        double   ra_corr = posc->line[n].ra_h ;
        double  dec_corr = posc->line[n].dec_d;
        double   ha_dest;
        double    ad_ra  = (63.0/60.0/2.0/15.0);  // angular distance between field center and CCD center
        double    ad_dec = (66.0/60.0/2.0     );
        double  diff_ra ;   // = (  ra_current -  ra_destination ) / cos(dec) in arcsec
        double  diff_dec;   // = ( dec_current - dec_destination ) in arcsec

        ha_dest = psys->ha_h + ( psys->ra_h - posc->line[n].ra_h ) + (43.0+20.0)/3600.0;  // destination HA after readout+writing+init+erase (Min. 41 / Max. 48 / Typ. 43 sec between EXPSTATUS=READOUT and EXPSTATUS=INITIALIZING)
        if(ha_dest<-12.0) ha_dest+=24.0;  if(ha_dest>=+12.0) ha_dest-=24.0; // added for 24h range matching at v0.4.4

        //ad_ra  -= (60.0/16.0*1.0/60.0/15.0);  // offset to field center and for position the object on center of strip
        //ad_dec -= (60.0/16.0*1.0/60.0     );  // same offset as RA
        // sould be changed at TCSAgent

        switch(posc->line[n].copt[0]) {  // for offset correction enabled, v0.3.2
          case '-':                                                               break;  // No correction
          case '0':                                                               break;  // No correction
          case '1':  offset_blg( &ra_corr, &dec_corr, ha_dest, CORTABLE_BLGOFF);  break;  // BLG correction
          case 'k': 
          case 'K':  ra_corr += ad_ra / cosd(dec_corr);  dec_corr -= ad_dec;      break;  // Offset to K from center
          case 'm': 
          case 'M':  ra_corr -= ad_ra / cosd(dec_corr);  dec_corr -= ad_dec;      break;  // Offset to M from center
          case 't': 
          case 'T':  ra_corr += ad_ra / cosd(dec_corr);  dec_corr += ad_dec;      break;  // Offset to T from center
          case 'n': 
          case 'N':  ra_corr -= ad_ra / cosd(dec_corr);  dec_corr += ad_dec;      break;  // Offset to N from center
          case 'c': 
          case 'C':                                                               break;  // Center: No correction (v0.9.0)
          default :                                                               break;  // default setting: No correction
        }

        //if(ra_corr>=24.0) ra_corr-=24.0;   // until v0.4.3
        //if(ra_corr<0.0) ra_corr+=24.0;  if(ra_corr>=24.0) ra_corr-=24.0;   // modified for more correct 24h range matching at v0.4.4
        // --> these cannot prevent the diff_ra from overing the 24h range (0.0000~23.9999) when 0h is between current RA and destination RA, removed v0.4.4
        
        //diff_ra  = ( ra_corr - psys-> ra_h)*3600.0*15.0 * cosd(dec_corr);   // v0.4.2
        //diff_dec = (dec_corr - psys->dec_d)*3600.0;                         // v0.4.2
        // modified to prevent the diff_ra from overing the -12h ~ +12h range as follows at v0.4.4
        
        //diff_ra  = ( ra_corr - psys-> ra_h);
        //diff_dec = (dec_corr - psys->dec_d);
        diff_ra  = (psys-> ra_h -  ra_corr);  // v0.4.4
        diff_dec = (psys->dec_d - dec_corr);  // v0.4.4
        if(diff_ra<-12.0) diff_ra+=24.0;  if(diff_ra>=+12.0) diff_ra-=24.0;  // added for the -12h ~ +12h range matching at v0.4.4
        diff_ra  *= 3600.0*15.0*cosd(dec_corr);
        diff_dec *= 3600.0;

        psys->tcs_tolerance_pointing_corr = psys->tcs_tolerance_pointing + OSC_ADJ_TOL_POINTING * (double)(posc->count_pointing/2);   // v0.4.7
        // OSC_ADJ_TOL_POINTING = 0.2 & OSC_CHKCNT_POINTING = 8 (defined at v0.4.7), tcs_tolerance_pointing = 0.1 (INI runtime config updated on 2020-10-14)
        // 0: 0.1 = 0.1 + 0.2 * (0/2)
        // 1: 0.1 = 0.1 + 0.2 * (1/2)
        // 2: 0.3 = 0.1 + 0.2 * (2/2)
        // 3: 0.3 = 0.1 + 0.2 * (3/2)
        // 4: 0.5 = 0.1 + 0.2 * (4/2)
        // 5: 0.5 = 0.1 + 0.2 * (5/2)
        // 6: 0.7 = 0.1 + 0.2 * (6/2)
        // 7: 0.7 = 0.1 + 0.2 * (7/2)
        // 8: 0.9 = 0.1 + 0.2 * (8/2)
        // 9: 0.9 = 0.1 + 0.2 * (9/2)
        // --> tcs_tolerance_pointing_corr = 0.1 ~ 0.9
        
        if( posc->count_pointing > OSC_CHKCNT_POINTING/2 ) {   // added at v0.4.5, debugged at v0.4.6, modified at v0.4.7, modified at v0.6.7, modified at v0.7.4
          if( fabs(dec_corr) > 50.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.3 ~ 1.1
          if( fabs(dec_corr) > 60.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.5 ~ 1.3
          if( fabs(dec_corr) > 65.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.7 ~ 1.5
          if( fabs(dec_corr) > 70.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 0.9 ~ 1.7
          if( fabs(dec_corr) > 75.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 1.1 ~ 1.9
          if( fabs(dec_corr) > 80.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 1.3 ~ 2.1
          if( fabs(dec_corr) > 85.0 ) psys->tcs_tolerance_pointing_corr += OSC_ADJ_TOL_POINTING;   // --> tcs_tolerance_pointing_corr = 1.5 ~ 2.3
        }

        if( psys->nston ) {   // v0.7.5
          nsttimestamp = SysTimestamp();
          nstposadd_ra  = psys->cmd_velra  * ( nsttimestamp - psys->timestamp_tmr ) * cosd(dec_corr);
          nstposadd_dec = psys->cmd_veldec * ( nsttimestamp - psys->timestamp_tmr )             ;
          nsttoladd_ra  = fabs( psys->cmd_velra  * ( nsttimestamp - psys->timestamp_tmr ) * 2.0 * cosd(dec_corr) );
          nsttoladd_dec = fabs( psys->cmd_veldec * ( nsttimestamp - psys->timestamp_tmr ) * 2.0                  );
        }
        else {
          nstposadd_ra = nstposadd_dec = 0.0;
          nsttoladd_ra = nsttoladd_dec = 0.0;
        }

      //sprintf(cmsg, "CHK_POSERR:  DIFF_RA %+.2f  DIFF_DEC %+.2f  DEST_HA %+08.4f  DEST_RA %07.4f  DEST_DEC %+07.3f  CMD_NUM %d  FOR NEXT EXPOSURE\n", 
      //                            diff_ra, diff_dec, ha_dest, ra_corr, dec_corr, posc->count_pointing);_dbgmsgout(cmsg);   
      //                            // CHK_POSERR logging added at v0.4.3, keywords modified & destination Dec logging added at v0.4.4, destination RA & commanded number logging added at v0.4.5
        sprintf(cmsg, "CHK_POSERR:  DIFF_RA %+.2f  DIFF_DEC %+.2f  DEST_HA %+08.4f  DEST_RA %07.4f  DEST_DEC %+07.3f  CMD_NUM %d  DSEC %.2f  VEL_RA %+.2f  VEL_DEC %+.2f  TOL_RA %.2f  TOL_DEC %.2f  FOR NEXT EXPOSURE\n", 
                                    (diff_ra + nstposadd_ra), (diff_dec + nstposadd_dec), ha_dest, ra_corr, dec_corr, posc->count_pointing, (nsttimestamp - psys->timestamp_tmr), psys->cmd_velra, psys->cmd_veldec, 
                                    (psys->tcs_tolerance_pointing_corr + nsttoladd_ra), (psys->tcs_tolerance_pointing_corr + nsttoladd_dec) );_dbgmsgout(cmsg);
                                    // moved here from right after "diff_dec *= 3600.0;" line, NST correction applied, and tolerance value appended at v0.9.0

      //if( fabs(posc->line[i].ra_h -psys->ra_h )*3600.0*15.0 < psys->tcs_tolerance  &&
      //    fabs(posc->line[i].dec_d-psys->dec_d)*3600.0      < psys->tcs_tolerance  &&
      //      psys->telstatus<=TELSTATUS_TRACKINGS && psys->telstatus>=TELSTATUS_TRACKING ) {  // until v0.3.0
      //    //psys->telstatus==TELSTATUS_TRACKINGS ) {  // oldver
      //if( fabs( ra_corr-psys-> ra_h)*3600.0*15.0 < psys->tcs_tolerance  &&
      //    fabs(dec_corr-psys->dec_d)*3600.0      < psys->tcs_tolerance  &&
      //    TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_TRACKINGS ) {  // v0.3.2
      //if( fabs(diff_ra) < psys->tcs_tolerance_pointing  && fabs(diff_dec) < psys->tcs_tolerance_pointing  &&
      //    TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_TRACKINGS ) {  // v0.4.2
      //if( fabs(diff_ra) < psys->tcs_tolerance_pointing_corr  && fabs(diff_dec) < psys->tcs_tolerance_pointing_corr  &&
      //    TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_TRACKINGS ) {  // v0.4.5
        if( fabs( diff_ra  + nstposadd_ra  ) < ( psys->tcs_tolerance_pointing_corr + nsttoladd_ra  ) && 
            fabs( diff_dec + nstposadd_dec ) < ( psys->tcs_tolerance_pointing_corr + nsttoladd_dec ) &&
            TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_TRACKINGS ) {  // v0.7.5

            posc->flag_pointed = 1;
            posc->count_pointing = 0;
            //posc->procflags &= ~OSC_CMDBIT_POINTING;  // actually this is not necessary because this routine is excuted only when !(posc->procflags&OSC_CMDBIT_POINTING)==1. so, removed to prevent some confution at v0.3.2

            BLUTEXT;sprintf(cmsg, "OSC.STATUS: TELESCOPE POINTED FOR NEXT EXPOSURE\n");_vmsgout(cmsg);  // v0.2.5
            psys->tpfailed_axis = TEL_AXIS_NO;  // v0.9.0

        }

        else if( TELSTATUS_TRACKING<=psys->telstatus && psys->telstatus<=TELSTATUS_OSCILLATE ) {

          if( posc->count_pointing++ > OSC_CHKCNT_POINTING ) {

              // strcpy(reply, "Telescope failed to point at the RA/DEC for next exposure !!"
              //               " The script observation is paused now. "
              //               " Please check RA/Dec & PC-TCS status, and do pointing manually.");  // v0.3.6

              if( psys->telstatus==TELSTATUS_OSCILLATE ) {
                  rtn = psys->unstable_axis;
                  sprintf(reply, "Telescope failed to point due to OSCILLATION on %s", (rtn==TEL_AXIS_BOTH)?"Both RA/Dec axes":(rtn==TEL_AXIS_RA)?"RA axis":(rtn==TEL_AXIS_DEC)?"DEC axis":"unknown axis");
              }
              else {
                       if( fabs( diff_ra  + nstposadd_ra  ) >= ( psys->tcs_tolerance_pointing_corr + nsttoladd_ra  ) &&
                           fabs( diff_dec + nstposadd_dec ) >= ( psys->tcs_tolerance_pointing_corr + nsttoladd_dec ) ) psys->tpfailed_axis = TEL_AXIS_BOTH;
                  else if( fabs( diff_ra  + nstposadd_ra  ) >= ( psys->tcs_tolerance_pointing_corr + nsttoladd_ra  ) ) psys->tpfailed_axis = TEL_AXIS_RA;
                  else if( fabs( diff_dec + nstposadd_dec ) >= ( psys->tcs_tolerance_pointing_corr + nsttoladd_dec ) ) psys->tpfailed_axis = TEL_AXIS_DEC;
                  else                                                                                                 psys->tpfailed_axis = TEL_AXIS_UNKNOWN;
                  rtn = psys->tpfailed_axis;
                  sprintf(reply, "Telescope failed to point at %s", (rtn==TEL_AXIS_BOTH)?"Both RA/Dec":(rtn==TEL_AXIS_RA)?"the RA":(rtn==TEL_AXIS_DEC)?"the DEC":"the destination");
              }
              strcat(reply, " !!  The script observation is paused now.  Please check RA/Dec axes & TCS status, and do pointing manually for NEXT exposure.");   /////// v0.9.0

              sprintf(cmsg, "REPORT_TPFAILED: Type=%-12s Axis=%-5s CmdRA=%-12s CmdDEC=%-12s CorOpt=%c  TelRA=%-11s TelDEC=%-11s TelHA=%-9s  Epoch=%-8.3f LST=%-8s SecZ=%-4.2f Alt=%-4.1f Az=%-+6.1f  "
                            "DiffRA=%+.2f DiffDEC=%+.2f DestRA=%07.4f DestDec=%+07.3f DestHA=%+08.4f CmdNum=%d  DelSec=%.2f VelRA=%+.2f VelDEC=%+.2f TolRA=%.2f TolDec=%.2f PointFor=%-9s\n", 
                            (psys->telstatus==TELSTATUS_OSCILLATE)?"OSCILLATION":"POINTINGFAIL", (rtn==TEL_AXIS_BOTH)?"BOTH":(rtn==TEL_AXIS_RA)?"RA":(rtn==TEL_AXIS_DEC)?"DEC":"UNDEF", 
                            posc->line[n].ra, posc->line[n].dec, posc->line[n].copt[0], psys->ra, psys->dec, psys->ha, psys->epoch_y, psys->lst, psys->secz, psys->alt_d, psys->az_d, 
                            (diff_ra + nstposadd_ra), (diff_dec + nstposadd_dec), ra_corr, dec_corr, ha_dest, posc->count_pointing, (nsttimestamp - psys->timestamp_tmr), psys->cmd_velra, psys->cmd_veldec, 
                            (psys->tcs_tolerance_pointing_corr + nsttoladd_ra), (psys->tcs_tolerance_pointing_corr + nsttoladd_dec), "NEXT" );_dbgmsgout(cmsg);   /////// v0.9.0

              posc->flag_pointed = 1;
              posc->count_pointing = 0;

              if(psys->nston) {   // v0.7.5
                sprintf(cmsg, "DBG: TCS paddle off before osc pause\n");_dbgmsgout(cmsg);
                for(retry=0;retry<3;retry++) {
                  //strcpy(lineinput, "tpad  off off off off");
                  strcpy(lineinput, "nstoff");   // v0.8.0
                  rtn = OscCommand(lineinput);
                  if(rtn==CMD_OK) break;
                  usleep(100);
                }
                if(retry>=3) strcat(reply, " As well as Failed to control TCS paddle for NST off !! Please check PC-TCS Guide/Drift status..");
              }

              OscCommand("opause");

              return OSC_RTN_ERROR;

          }
          else {    // RA/Dec error is large or Tracking error is unstable
            
              //// Checking clearance between the PC-TCS limit and destination, added at v0.4.0, and modified at v0.4.4 /////////////////////////////////////////////////////////////////////////////////////////              
              //

              dClearance = ( psys->tcs_limit_ha - ha_dest ) * 15.0;   // Clearance between west HA limit and destination
              if( dClearance <= 0.0 ) {
                  REDTEXT;sprintf(cmsg, "WARNING: Destination HA is out of the limit, LINE#%04d EXP#%d (%s) skipped !!\n", (n+1), expidx_next, posc->line[n].label);_msgout(cmsg);
                  goto NEXT_LINE_SKIP;
              }
              else if( dClearance < psys->tcs_limit_warning ) { 
                  CYATEXT;sprintf(cmsg, "Warning: Destination HA is near the limit !\n");_msgout(cmsg);
              }

              dClearance = psys->tcs_limit_dec_n - posc->line[n].dec_d;   // Clearance between north Dec limit and destination
              if( dClearance <= 0.0 ) {
                  REDTEXT;sprintf(cmsg, "WARNING: Destination DEC is out of the north limit, LINE#%04d EXP#%d (%s) skipped !!\n", (n+1), expidx_next, posc->line[n].label);_msgout(cmsg);
                  goto NEXT_LINE_SKIP;
              }
              else if( dClearance < psys->tcs_limit_warning ) { 
                  CYATEXT;sprintf(cmsg, "Warning: Destination DEC is near the limit in North !\n");_msgout(cmsg);
              }

              dClearance = posc->line[n].dec_d - psys->tcs_limit_dec_s;   // Clearance between south Dec limit and destination
              if( dClearance <= 0.0 ) {
                  REDTEXT;sprintf(cmsg, "WARNING: Destination DEC is out of the south limit, LINE#%04d EXP#%d (%s) skipped !!\n", (n+1), expidx_next, posc->line[n].label);_msgout(cmsg);
                  goto NEXT_LINE_SKIP;
              }
              else if( dClearance < psys->tcs_limit_warning ) { 
                  CYATEXT;sprintf(cmsg, "Warning: Destination DEC is near the limit in South!\n");_msgout(cmsg);
              }
              
              dClearance = GetAltitude(ha_dest, posc->line[n].dec_d, psys->tcs_latitude) - psys->tcs_limit_alt;   // Clearance between Altitude limit and destination
              if( dClearance <= 0.0 ) {
                  REDTEXT;sprintf(cmsg, "WARNING: Destination ALT is lower than the limit, LINE#%04d EXP#%d (%s) skipped !!\n", (n+1), expidx_next, posc->line[n].label);_msgout(cmsg);
                  goto NEXT_LINE_SKIP;
              }
              else if( dClearance < psys->tcs_limit_warning && ha_dest > 0.0 ) { 
                  CYATEXT;sprintf(cmsg, "Warning: Destination ALT is near the limit !\n");_msgout(cmsg);
              }
              
              //
              //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
            
              posc->procflags |= OSC_CMDBIT_POINTING;    // command to move telescope
              
          }

        }

      }

      //// command to enable servo & check response for the next exposure ////////////////////////////////

      //if( posc->procflags&OSC_CMDBIT_ENABLESERVO && posc->procflags<0x0100 &&  // if the other checking flags are all down
      //  ( psys->camstatus==CAMSTATUS_READ_2 || psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) ) {
      if( posc->procflags&OSC_CMDBIT_ENABLESERVO && posc->procflags<0x0100 && psys->camstatus>=CAMSTATUS_READ_1  ) {  // if the other checking flags are all down

        posc->flag_responseok = 0;
        posc->flag_responsecheck = 1;
        posc->count_responsecheck = 0;
        strcpy(posc->reschkcmd, "tcmd");
        sprintf(lineinput, "tcmd unkill");
        OscCommand(lineinput);

        posc->procflags &= ~OSC_CMDBIT_ENABLESERVO;
        posc->procflags |=  OSC_CHKBIT_ENABLESERVO;

      }

      if( posc->procflags&OSC_CHKBIT_ENABLESERVO ) {

        if( posc->flag_responseok ) {
          posc->flag_responseok = 0;
          posc->flag_responsecheck = 0;
          posc->count_responsecheck = 0;
          memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
          posc->procflags &= ~OSC_CHKBIT_ENABLESERVO;
        }
        else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
          posc->procflags |=  OSC_CMDBIT_ENABLESERVO;
          posc->procflags &= ~OSC_CHKBIT_ENABLESERVO;
          sprintf(reply, "Script observation process failed to receive OK response."
                         " The process will retry to command line '%s'.", lineinput);
          posc->flag_responsecheck = 0;
          return OSC_RTN_WARNING;
        }

      }

      //// command to enable tracking & check response for the next exposure ////////////////////////////////

      //if( posc->procflags&OSC_CMDBIT_ONTRACKING && posc->procflags<0x0100 && 
      //    ( psys->camstatus==CAMSTATUS_READ_2 || psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) ) {
      if( posc->procflags&OSC_CMDBIT_ONTRACKING && posc->procflags<0x0100 && psys->camstatus>=CAMSTATUS_READ_1  ) {  // if TC cmd, No error in IDLE_3

        posc->flag_responseok = 0;
        posc->flag_responsecheck = 1;
        posc->count_responsecheck = 0;
        strcpy(posc->reschkcmd, "tcmd");
        sprintf(lineinput, "tcmd track on");
        OscCommand(lineinput);

        posc->procflags &= ~OSC_CMDBIT_ONTRACKING;
        posc->procflags |=  OSC_CHKBIT_ONTRACKING;

      }

      if( posc->procflags&OSC_CHKBIT_ONTRACKING ) {

        if( posc->flag_responseok ) {
          posc->flag_responseok = 0;
          posc->flag_responsecheck = 0;
          posc->count_responsecheck = 0;
          memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
          posc->procflags &= ~OSC_CHKBIT_ONTRACKING;
        }
        else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
          posc->procflags |=  OSC_CMDBIT_ONTRACKING;
          posc->procflags &= ~OSC_CHKBIT_ONTRACKING;
          sprintf(reply, "Script observation process failed to receive OK response."
                         " The process will retry to command line '%s'.", lineinput);
          posc->flag_responsecheck = 0;
          return OSC_RTN_WARNING;
        }

      }

      //// command to slew telescope & check response for the next exposure ////////////////////////////////

      //if( posc->procflags&OSC_CMDBIT_POINTING && posc->procflags<0x0100 && 
      //    psys->telstatus>=TELSTATUS_TRACKING && psys->telstatus<=TELSTATUS_OSCILLATE && 
      //    ( psys->camstatus==CAMSTATUS_READ_2 || psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) ) {
      if( posc->procflags&OSC_CMDBIT_POINTING && posc->procflags<0x0100 && psys->camstatus>=CAMSTATUS_READ_1 && 
          psys->telstatus>=TELSTATUS_TRACKING && psys->telstatus<=TELSTATUS_OSCILLATE && --posc->count_tmrwaiting < 0 ) {   // v 0.7.7

        if( !posc->flag_wait_for_shutreload || !strcasecmp(psys->shutopstat,"STANDBY") ||   // if "STANDBY" or have waited long enough, slew the telescope 
            OSC_CHKCNT_SHUTRELOAD <= posc->count_wait_for_shutreload++ ) {                  // if not, skip to wait for shutter reloading to complete (v1.2.0)

          posc->flag_responseok = 0;
          posc->flag_responsecheck = 1;
          posc->count_responsecheck = 0;
          strcpy(posc->reschkcmd, "tmr");
          if( posc->line[n].copt[0] == 'c' || posc->line[n].copt[0] == 'C' )  // v0.7.0 temporary
            //sprintf(lineinput, "tmr  %s  %s  %c", posc->line[n].ra, posc->line[n].dec, 'm');
              sprintf(lineinput, "tmr  %s  %s  %c", posc->line[n].ra, posc->line[n].dec, '0');   // v0.9.0
          else
              sprintf(lineinput, "tmr  %s  %s  %c", posc->line[n].ra, posc->line[n].dec, posc->line[n].copt[0]);
          OscCommand(lineinput);

          posc->count_tmrwaiting = 1;   // v0.7.7
          if(psys->nston) posc->count_tmrwaiting += 2;

          psys->telstatus = TELSTATUS_CHECKING;   // added for debugging frequent tmr command sending in OSCILLATION status at v0.2.8
          psys->duration_stable = 0;  // v0.4.2

          posc->procflags &= ~OSC_CMDBIT_POINTING;
          posc->procflags |=  OSC_CHKBIT_POINTING;          

        }

      }

      if( posc->procflags&OSC_CHKBIT_POINTING ) {

        if( posc->flag_responseok ) {
          posc->flag_responseok = 0;
          posc->flag_responsecheck = 0;
          posc->count_responsecheck = 0;
          memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
          posc->procflags &= ~OSC_CHKBIT_POINTING;
        }
        else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
          posc->procflags |=  OSC_CMDBIT_POINTING;
          posc->procflags &= ~OSC_CHKBIT_POINTING;
          sprintf(reply, "Script observation process failed to receive OK response."
                         " The process will retry to command line '%s'.", lineinput);
          posc->flag_responsecheck = 0;
          return OSC_RTN_WARNING;
        }

      }

    }// end of if( !posc->line[n].flag_movedisable  && posc->flag_exposing ) {..}

    else if( posc->line[n].flag_movedisable && posc->flag_exposing ) {
      posc->flag_pointed = 1;
      posc->count_pointing = 0;
      posc->procflags &= ~OSC_CMDBIT_POINTING;
    }


    //////// check Filter and ICS status and command to configure exposure for the next exposure..

    //// check filter for the next exposure ////////////////////////////////


    if( posc->flag_exposing && !posc->flag_filterchanged ) {  // v0.1.3
      if( posc->line[n].filter_n == psys->filternum ) {
          posc->flag_filterchanged = 1;
          posc->count_filtercommanded = 0;
          posc->procflags &= ~OSC_CMDBIT_SETFILTER;
      }
      else if( posc->count_filtercommanded<OSC_CHKCNT_FILTER || strcasecmp(posc->line[n].filter,psys->filtername) ) {
          //if( !(posc->procflags&OSC_CHKBIT_SETFILTER) && strcmp(psys->filteropstat,"RUNNING") ) posc->procflags |= OSC_CMDBIT_SETFILTER;
          if( !(posc->procflags&OSC_CHKBIT_SETFILTER) && strcmp(psys->filteropstat,"RUNNING") && strcmp(psys->fsastatus,"RUNNING") ) posc->procflags |= OSC_CMDBIT_SETFILTER;
          //// modified for debugging 'WAIT' response problem due to delayed filteropstat update at v0.4.4
      }
      else if( posc->count_filtercommanded>=OSC_CHKCNT_FILTER ) {
          strcpy(reply, "Script obs process failed to confirm the filter for next exposure !!"
                        " Please check the filter status and control it manually.");
          posc->flag_filterchanged = 1;
          posc->count_filtercommanded = 0;
          posc->procflags &= ~OSC_CMDBIT_SETFILTER;
          //return OSC_RTN_WARNING;  // modified to pause & error display at v0.4.4          
          if(psys->nston) {   // v0.7.5
            sprintf(cmsg, "DBG: TCS paddle off before osc pause\n");_dbgmsgout(cmsg);
            for(retry=0;retry<3;retry++) {
              //strcpy(lineinput, "tpad  off off off off");
              strcpy(lineinput, "nstoff");   // v0.8.0
              rtn = OscCommand(lineinput);
              if(rtn==CMD_OK) break;
              usleep(100);
            }
            if(retry>=3) strcat(reply, "As well as failed to control TCS paddle for NST off !! Please check PC-TCS Guide/Drift status...");
          }
          OscCommand("opause");
          return OSC_RTN_ERROR;          
      }
    } 
    

    //// check exposure configuration for the next exposure ////////////////////////////////

    if( posc->flag_exposing && !posc->flag_projidcommanded  ) {  // added at v0.6.4, do during exposing
      if( !(posc->procflags&OSC_CHKBIT_SETPROJID ) ) posc->procflags |= OSC_CMDBIT_SETPROJID;
    }   

    if( posc->flag_exposing && !posc->flag_objectcommanded  ) {  // do during exposing
      if( !(posc->procflags&OSC_CHKBIT_SETOBJECT ) ) posc->procflags |= OSC_CMDBIT_SETOBJECT;
    }   

    if( posc->flag_exposing && !posc->flag_exptimecommanded  ) {  // do during exposing
      if( !strcmp(posc->line[n].imgtyp,"BIAS") ) posc->flag_exptimecommanded = 1;
      else if( !(posc->procflags&OSC_CHKBIT_SETEXPTIME ) ) posc->procflags |= OSC_CMDBIT_SETEXPTIME;
    }   

    //// command to set filter & check response for the next exposure ////////////////////////////////

    //if( posc->flag_exposing && posc->procflags&OSC_CMDBIT_SETFILTER && posc->procflags<0x0100 && 
    //    //( psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) &&
    //    //( !strcmp(psys->filteropstat,"STANDBY") || !strcmp(psys->filteropstat,"ERROR") )  ) {
    //        psys->camstatus>=CAMSTATUS_READ_1 && strcmp(psys->filteropstat,"RUNNING") ) {    // no error if TC command although IDLE_3

    if( posc->flag_exposing && posc->procflags&OSC_CMDBIT_SETFILTER && posc->procflags<0x0100 && 
            psys->camstatus>=CAMSTATUS_READ_1 && strcmp(psys->filteropstat,"RUNNING") && strcmp(psys->fsastatus,"RUNNING") ) {    
            //// modified for debugging 'WAIT' response problem due to delayed filteropstat update at v0.4.4

      posc->flag_responseok = 0;
      posc->flag_responsecheck = 1;
      posc->count_responsecheck = 0;
      strcpy(posc->reschkcmd, "filter");
      sprintf(lineinput, "filter  %s", posc->line[n].filter);
      OscCommand(lineinput);

      posc->procflags &= ~OSC_CMDBIT_SETFILTER;
      posc->procflags |=  OSC_CHKBIT_SETFILTER;
      
      posc->count_filtercommanded++;   // moved here at v0.4.5 (according to modification for debugging 'WAIT' response problem with strcmp(psys->fsastatus,"RUNNING" check for commanding to change filter at v0.4.4)

    }

    if( posc->flag_exposing && posc->procflags&OSC_CHKBIT_SETFILTER ) {

      if( posc->flag_responseok ) {
        posc->flag_responseok = 0;
        posc->flag_responsecheck = 0;
        posc->count_responsecheck = 0;
        //posc->count_filtercommanded++;
        memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
        posc->procflags &= ~OSC_CHKBIT_SETFILTER;
      }
      else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
        posc->procflags |=  OSC_CMDBIT_SETFILTER;
        posc->procflags &= ~OSC_CHKBIT_SETFILTER;
        sprintf(reply, "Script observation process failed to receive OK response."
                       " The process will retry to command line '%s'.", lineinput);
        posc->flag_responsecheck = 0;
        return OSC_RTN_WARNING;
      }

    }

    //// command to configure projid & check response for the next exposure //////////////////////////////// v0.6.4

    if( posc->flag_exposing && posc->procflags&OSC_CMDBIT_SETPROJID && posc->procflags<0x0100 && 
        ( psys->camstatus==CAMSTATUS_READ_3 ) ) {

      posc->flag_responseok = 0;
      posc->flag_responsecheck = 1;
      posc->count_responsecheck = 0;
      strcpy(posc->reschkcmd, "projid");
      sprintf(lineinput, "ProjID  %s", posc->line[n].projid);
      OscCommand(lineinput);

      posc->procflags &= ~OSC_CMDBIT_SETPROJID;
      posc->procflags |=  OSC_CHKBIT_SETPROJID;

    }

    if( posc->flag_exposing && posc->procflags&OSC_CHKBIT_SETPROJID ) {

      if( posc->flag_responseok ) {
        posc->flag_responseok = 0;
        posc->flag_responsecheck = 0;
        posc->count_responsecheck = 0;
        posc->flag_projidcommanded = 1;
        memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
        posc->procflags &= ~OSC_CHKBIT_SETPROJID;
      }
      else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
        posc->procflags |=  OSC_CMDBIT_SETPROJID;
        posc->procflags &= ~OSC_CHKBIT_SETPROJID;
        sprintf(reply, "Script observation process failed to receive OK response."
                       " The process will retry to command line '%s'.", lineinput);
        posc->flag_responsecheck = 0;
        return OSC_RTN_WARNING;
      }

    }

    //// command to configure imagetype and object name & check response for the next exposure ////////////////////////////////

    if( posc->flag_exposing && posc->procflags&OSC_CMDBIT_SETOBJECT && posc->procflags<0x0100 && 
      //( psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) ) {  // Error if ICS commands at IDLE_3 --> error to set image type & object name during integration for next exposure
      //( psys->camstatus==CAMSTATUS_READ_3 || ( psys->camstatus==CAMSTATUS_IDLE_3 && psys->status_fitssaved==1 ) ) ) {   // Error if ICS commands at IDLE_3, debugged at v0.2.8
      //( psys->camstatus==CAMSTATUS_READ_3 || ( psys->camstatus>=CAMSTATUS_READY  && psys->status_fitssaved==1 ) ) ) {   // (v0.4.5.0)
        ( psys->camstatus==CAMSTATUS_READ_3 ) ) {   // checking status>=READY removed for  because flag_exposing == 0 and line finished always if status >= IDLE_3 (v0.4.5.1)

      posc->flag_responseok = 0;
      posc->flag_responsecheck = 1;
      posc->count_responsecheck = 0;
      strcpy(posc->reschkcmd, posc->line[n].imgtyp);
      sprintf(lineinput, "%s  %s", posc->line[n].imgtyp, posc->line[n].object);
      OscCommand(lineinput);

      posc->procflags &= ~OSC_CMDBIT_SETOBJECT;
      posc->procflags |=  OSC_CHKBIT_SETOBJECT;

    }

    if( posc->flag_exposing && posc->procflags&OSC_CHKBIT_SETOBJECT ) {

      if( posc->flag_responseok ) {
        posc->flag_responseok = 0;
        posc->flag_responsecheck = 0;
        posc->count_responsecheck = 0;
        posc->flag_objectcommanded = 1;
        memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
        posc->procflags &= ~OSC_CHKBIT_SETOBJECT;
      }
      else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
        posc->procflags |=  OSC_CMDBIT_SETOBJECT;
        posc->procflags &= ~OSC_CHKBIT_SETOBJECT;
        sprintf(reply, "Script observation process failed to receive OK response."
                       " The process will retry to command line '%s'.", lineinput);
        posc->flag_responsecheck = 0;
        return OSC_RTN_WARNING;
      }

    }

    //// command to configure exposure time & check response for the next exposure ////////////////////////////////

    if( posc->flag_exposing && posc->procflags&OSC_CMDBIT_SETEXPTIME && posc->procflags<0x0100 && 
      //( psys->camstatus==CAMSTATUS_READ_3 || psys->status_fitssaved==1 ) ) {  // Error if ICS commands at IDLE_3 --> error to set image type & object name during integration for next exposure
      //( psys->camstatus==CAMSTATUS_READ_3 || ( psys->camstatus==CAMSTATUS_IDLE_3 && psys->status_fitssaved==1 ) ) ) {  // Error if ICS commands at IDLE_3, debugged at v0.2.8
      //( psys->camstatus==CAMSTATUS_READ_3 || ( psys->camstatus>=CAMSTATUS_READY  && psys->status_fitssaved==1 ) ) ) {   // (v0.4.5.0)
        ( psys->camstatus==CAMSTATUS_READ_3 ) ) {   // checking status>=READY removed for  because flag_exposing == 0 and line finished always if status >= IDLE_3 (v0.4.5.1)

      posc->flag_responseok = 0;
      posc->flag_responsecheck = 1;
      posc->count_responsecheck = 0;
      strcpy(posc->reschkcmd, "exp");
      sprintf(lineinput, "exp  %.1f", posc->line[n].exptime);
      OscCommand(lineinput);

      posc->procflags &= ~OSC_CMDBIT_SETEXPTIME;
      posc->procflags |=  OSC_CHKBIT_SETEXPTIME;

    }

    if( posc->flag_exposing && posc->procflags&OSC_CHKBIT_SETEXPTIME ) {

      if( posc->flag_responseok ) {
        posc->flag_responseok = 0;
        posc->flag_responsecheck = 0;
        posc->count_responsecheck = 0;
        posc->flag_exptimecommanded = 1;
        memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);
        posc->procflags &= ~OSC_CHKBIT_SETEXPTIME;
      }
      else if( posc->count_responsecheck++ > OSC_CHKCNT_RESPCHK ) {
        posc->procflags |=  OSC_CMDBIT_SETEXPTIME;
        posc->procflags &= ~OSC_CHKBIT_SETEXPTIME;
        sprintf(reply, "Script observation process failed to receive OK response."
                       " The process will retry to command line '%s'.", lineinput);
        posc->flag_responsecheck = 0;
        return OSC_RTN_WARNING;
      }

    }

  }// end of if( posc->line[i].type==OSC_TYPE_EXP && posc->line[n].type==OSC_TYPE_EXP && posc->flag_running && posc->flag_preparenextexp ) {..}  to prepare the next exposure


  return OSC_RTN_NOERR;   //// on going process a script line without "STATUS: <reply>" notice..



  //
  // Process for skipping a Exposure Line
  //

  //// if the next expousre line should be skipped, setup to jump smoothly to another next exposure line and then return

  NEXT_LINE_SKIP:   // v0.4.4

  //posc->procflags &= 0xFF00;   // down all the command flags
  posc->procflags = 0x0000;   // down all the command/respcheck flags, modified at v0.4.5
  
  posc->flag_responseok = 0;
  posc->flag_responsecheck = 0;
  posc->count_responsecheck = 0;
  posc->flag_filterchanged = 0;
  posc->count_filtercommanded = 0;
  posc->flag_projidcommanded = 0;   // v0.6.4
  posc->flag_objectcommanded = 0;
  posc->flag_exptimecommanded = 0;
  posc->flag_pointed = 0;
  posc->count_pointing = 0;
  posc->flag_nstchecked = 0;  // v0.6.9
  posc->waiting_dome_rotation = 0;  // v0.9.6
  posc->waiting_dome_shutter = 0;  // v0.9.6
  ////posc->procflags |= OSC_CMDBIT_POINTING;  // must do pointing at least one time before next exposure
  ////--> removed to reduce overhead at v0.8.7
  memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);

  posc->expnum_skip++;
  
  return OSC_RTN_NOERR;
  
  //// if the current expousre line should be skipped, just jump to the routine LINE_SKIPPED: that is setting up for the next script line, after a notice
  
  CURRENT_LINE_SKIP:   // v0.4.4

  /// posc->flag_filterchanged = 0;    // added at v0.4.5
  /// posc->count_filtercommanded = 0;    // adeded at v0.4.5
  /// posc->flag_nstchecked = 0;  // v0.6.9
  ///
  /// sprintf(reply, "Script LINE#%d EXP#%d (%s) skipped..  ", posc->lineidx, posc->expidx, posc->line[i].label);
  ///
  /// --> modified as below to avoid possibility, on code, not to set for following exposure after line skips at v0.8.3

  //posc->procflags &= 0xFF00;   // down all the command flags
  posc->procflags = 0x0000;   // down all the command/respcheck flags, modified at v0.4.5
  
  posc->flag_responseok = 0;
  posc->flag_responsecheck = 0;
  posc->count_responsecheck = 0;
  posc->flag_filterchanged = 0;
  posc->count_filtercommanded = 0;
  posc->flag_projidcommanded = 0;
  posc->flag_objectcommanded = 0;
  posc->flag_exptimecommanded = 0;
  posc->flag_pointed = 0;
  posc->count_pointing = 0;
  posc->flag_nstchecked = 0;  // v0.6.9
  posc->waiting_dome_rotation = 0;  // v0.9.6
  posc->waiting_dome_shutter = 0;  // v0.9.6
  ////posc->procflags |= OSC_CMDBIT_POINTING;  // must do pointing at least one time before next exposure
  ////--> removed to reduce overhead at v0.8.7
  memset(posc->reschkcmd, NULL, OSC_MAXCMDLEN);

  if( !strcmp( posc->line[i].projid, posc->line[n].projid ) ) posc->flag_projidcommanded = 1;
  if( !strcmp( posc->line[i].object, posc->line[n].object ) ) posc->flag_objectcommanded = 1;
  if( fabs( posc->line[i].exptime - posc->line[n].exptime ) < 0.001 ) posc->flag_exptimecommanded = 1;
  /// end of code modified at v0.8.3

  sprintf(reply, "Script LINE#%d EXP#%d (%s) skipped..  ", posc->lineidx, posc->expidx, posc->line[i].label);
  
  goto LINE_SKIPPED;



  //
  // Line finishing: (1) CMD line finished / (2) EXP line finished / (3) Script running stopped / (4) Current EXP line skipped / (5) Script complete
  //

  //// if a script line is finished

  LINE_FINISH:

  if( posc->line[i].type == OSC_TYPE_CMD ) {    // (1) CMD line finished

    sprintf(reply, "Script LINE#%d CMD#%d (%s) complete..  ", posc->lineidx, posc->cmdidx, posc->line[i].cmd);

    if(pagent->isScrObsLog) {
      sprintf(cmsg, "  LINE#%04d  CMD#%04d  +%s  %s\n", posc->lineidx, posc->line[i].idx, posc->line[i].cmd, posc->line[i].arg);
      _scrobslog(cmsg);
    }

  }
  else {  // EXP line finished, or Script running stopped,   // 'else' and 'if(..)' separated for logging scrobs in case stopped (v0.8.2)

    posc->lastidx_expcompleted = posc->lineidx;   // for 'olast' command, v0.9.4

    if(posc->flag_expcomplete) {    // (2) EXP line finished

      sprintf(reply, "Script LINE#%d EXP#%d (%s) complete..  ", posc->lineidx, posc->expidx, posc->line[i].label);

      if(pagent->isScrObsLog) {
      
        //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %-32s %-12s %-12s %c  %-8s %-20s %-2s %6.1f  %-19s %4d\n", 
        //                 posc->lineidx, posc->line[i].idx, posc->line[i].label,  // OSC_MAX_OBJECT = 32 --> display 20
        //                 posc->line[i].ra, posc->line[i].dec, posc->line[i].copt, 
        //                 posc->line[i].imgtyp, posc->line[i].object,  // OSC_MAX_LABEL = 64 --> display 32
        //                 posc->line[i].filter, posc->line[i].exptime, 
        //                 posc->line[i].utobs, posc->line[i].uttol  );  
        //// modified as below at v0.5.0
      
        //ha = psys->ha_h + ( psys->ra_h - posc->line[i].ra_h );    
        //if(ha<-12.0) ha+=24.0;  if(ha>=+12.0) ha-=24.0;
        //alt = GetAltitude(ha, posc->line[i].dec_d, psys->tcs_latitude);   // HA & Alt cal added at v0.4.9
        // --> moved to exposure start in v1.0.0
      
        strcpy( strProjID, osc.line[i].projid );   // v0.6.4
        strcpy( strLabel , osc.line[i].label  );
        strcpy( strObject, osc.line[i].object );
        strncat( strProjID, CONST_STR_SPACE, MAX(osc.max_projid_length-strlen(strProjID),0) );   // v0.6.4
        strncat( strLabel , CONST_STR_SPACE, MAX(osc.max_label_length -strlen(strLabel ),0) );
        strncat( strObject, CONST_STR_SPACE, MAX(osc.max_object_length-strlen(strObject),0) );
        //// added for adjusting Label & Object field length at v0.5.0

      }

    }
    else {    // (3) Script running stopped, 
              //     this case is effective only when the current exp line process is stopped before starting exposure using flag_exposing in cmd_oscstop() of old version before v0.2.3
    
      sprintf(reply, "Script LINE#%d EXP#%d (%s) stopped, the exposure was not executed..  ", 
                     posc->lineidx, posc->expidx, posc->line[i].label);

    }

  //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %-16s %-2s %6.1f  %7s %4d  %+10.5f %+10.5f   ALT %5.2f  HA %+.2f  EXPSTART %s\n",
  //sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %-16s %-2s %6.1f  %7s %4d  %+10.5f %+10.5f   %5.2f  %+.2f   %s\n",  // modified at v1.0.0
    sprintf(cmsg, "  LINE#%04d  EXP#%04d  %s  %s  %-12s %-12s %2s %-8s %-16s %-2s %6.1f  %7s %4d  %+10.5f %+10.5f  %5.2f  %5.2f %+7.2f  %+6.2  %s  %s  %s\n",  // add secz, az, expnum, and oscillation info in v1.1.0
                     posc->lineidx, posc->line[i].idx, strProjID, strLabel, 
                     posc->line[i].ra, posc->line[i].dec, posc->line[i].copt, 
                     posc->line[i].imgtyp, strObject, 
                     posc->line[i].filter, posc->line[i].exptime, 
                     posc->line[i].utobs, posc->line[i].uttol, 
                     posc->line[i].velra, posc->line[i].veldec, // v0.6.9
                   //alt, ha, expinfo.strExpStart );   // modified for Label & Object field adjusted, and for Alt/HA log at v0.5.0, and for EXPSTART log at v0.7.9
                     expstart_dSecZ, expstart_dAlt, expstart_dAz, expstart_dHA,   // add secz and az, and modify secz, alt, az, ha to status at the starting of exposure in v1.1.0
                     expinfo.strExpStart, expinfo.strCurNum, expinfo.flagOscInExp?"Oscillated":"Stabled" );   // add expnum and oscillation info in v1.1.0
    _scrobslog(cmsg);   // moved here at v0.8.2

  }

  //// if a script line is skipped, start from here
  
  LINE_SKIPPED:    // (4) Current EXP line skipped
  
  if( posc->lineidx == posc->linenum ) goto OSC_FINISH;    // (5) script complete..
  if( !posc->flag_running ) goto OSC_FINISH;    // (3) script running stopped

  posc->lineidx++;
  posc->lineidx += posc->expnum_skip;    // added at v0.4.5
  posc->expnum_skip = 0;                 // added at v0.4.5
  //posc->flag_expcomplete = 0; // ? --> moved to initial checking of this func() ==> enabled at v0.5.4 with debugging one-more exp error ==> removed to rollback at v0.5.6

  //switch( posc->line[n].type ) {   <-- moved into else{} below
  //  case OSC_TYPE_CMD: posc->cmdidx = posc->line[n].idx;break;
  //  case OSC_TYPE_EXP: posc->expidx = posc->line[n].idx;break;
  //} 

  if( posc->flag_additionalshot ) {  // v0.8.0
    posc->flag_additionalshot = 0;
    posc->lineidx--;
  }
  else {
    switch( posc->line[n].type ) {   // <-- moved here, if additional shot, next == current
      case OSC_TYPE_CMD: posc->cmdidx = posc->line[n].idx;break;
      case OSC_TYPE_EXP: posc->expidx = posc->line[n].idx;break;
    }
  }

  strcat(reply, "Next stage: ");
  strcat(reply, GetOscStatus());

  expinfo.nStatus = EXPSTATUS_WAITING;   // v1.1.1

  if(utpassed) {   // v0.8.0
    utpassed = 0;
    return OSC_RTN_NOERR;   //// on going process a script line without "STATUS: <reply>" notice..
  }

  return OSC_RTN_NOTICE;

  //// If the observation script is all done or stopped.

  OSC_FINISH:    // (3) Script running stopped, or (5) Script complete

  if( posc->flag_running ) {
    posc->flag_running = posc->flag_paused = osc.flag_delay = 0;
    strcpy(reply, "Script observation complete. ");
  }
  else {
    strcpy(reply, "Script observation is stopped. ");
  }

  strcat(reply, GetOscStatus());

  posc->flag_process = 0;
  posc->count_process = psys->checknum_tcsdata-TCS_DATAUP_INTERVAL*2/3;   // zero point setting when flag_process = 0 as well, added at v0.4.0

  if(psys->nston) {   // v0.7.5
    sprintf(cmsg, "DBG: TCS paddle off before osc pause\n");_dbgmsgout(cmsg);
    for(retry=0;retry<3;retry++) {
      //strcpy(lineinput, "tpad  off off off off");
      strcpy(lineinput, "nstoff");   // v0.8.0
      rtn = OscCommand(lineinput);
      if(rtn==CMD_OK) break;
      usleep(100);
    }
    if(retry>=3) strcat(reply, "BUT Failed to control TCS paddle for NST off !! Please check PC-TCS Guide/Drift status");
  }

  return OSC_RTN_NOTICE;

}//// End of ProcOsc()


//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
//
// Client Info and Obs.system Config/Status handling utility functions
//

//------------------------------------------------------------------------------
//
// client.GetClientInfo - return the information for the information of client/process/configurations
//

void 
GetAgentInfo(char *info)
{
  cmd_info(NULL, EXEC, info);
}

//------------------------------------------------------------------------------
//
// expinfo.GetExpInfo - return information string for current exposure (v1.0.0)
//

char
*GetExpInfo(void)
{
  static char strExpInfo[256];
  memset(strExpInfo, NULL, sizeof(strExpInfo));
  cmd_expinfo(NULL, EXEC, strExpInfo);
  return strExpInfo;
}

//------------------------------------------------------------------------------
//
// expinfo.InitExpInfo - reset the exposure information data (v1.0.0)
//

void  
InitExpInfo(CEXP *pexpinfo)
{
  memset(pexpinfo, 0x00, sizeof(CEXP));
  pexpinfo->nStatus = EXPSTATUS_CHECK;
  strcpy(pexpinfo->strFitsOsc, "CHECK");
  strcpy(pexpinfo->strFitsNum, "00000000.000000");
  strcpy(pexpinfo->strNextNum, "00000000.000000");
  strcpy(pexpinfo->strCurNum , "00000000.000000");
  strcpy(pexpinfo->strPreNum , "00000000.000000");
  strcpy(pexpinfo->strExpStart, "0000-00-00T00:00:00.000");
  pexpinfo->flagStart = FALSE;
  pexpinfo->flagOscPre = FALSE;
  pexpinfo->flagOscInExp = FALSE;
  pexpinfo->cntOscInExp = 0;
}

//------------------------------------------------------------------------------
//
// obssys.GetSysStatus - return observation script running/process status
//  - called
//

char 
*GetSysStatus(void)
{
  static char sysstatus[512];
  UpdateDomeStatus(&sys, NULL);   // v0.9.4
  cmd_sysstatus(NULL, EXEC, sysstatus);
  return sysstatus;
}

//------------------------------------------------------------------------------
//
// obssys.InitSysConfig - Initialize the observation system configuration data
//

void
InitSysConfig(obssystem_t *psys)
{

  // reset Camera status/flags/counters

  psys->camstatus = CAMSTATUS_NC;

  psys->count_acqcomp = 0;
  psys->count_wrote = 0;
  psys->count_idle = 0;
  psys->count_ready = 0;
  psys->force_idle = 40;             // >1.8 sec (>0.045sec/count), rollback at v0.4.5
//psys->force_idle = 60;             // >2.7 sec (>0.045sec/count), modified at v0.4.4
  psys->force_ready = 270;           // >12.2 sec (0.045~0.050sec/count), added at v0.4.5

  psys->status_fitssaved = 0;
  psys->flag_icscheck = 0;

  psys->count_fitssaving = 0;
  psys->allowance_fitssaving = 670;  //  ~30.0 sec (~0.045sec/count)    <-- not used now
  //psys->allowance_fitssaving = 600;  //  ~27.0 sec (~0.045sec/count)
  //// duration from 'EXPSTATUS=IDLE' to last 'Wrote ..' message: 
  //// typically 16s, Min. 15s, rarely ~23s, Max. ??

  //psys->force_fitssaved = 400.0;  // ~18 sec (~0.045sec/count)
  psys->force_fitssaved = 560.0;  // ~25 sec (~0.045sec/count)
  //// duration from 'EXPSTATUS=IDLE' to 'REQ SWAP'(1st 'Wrote' message):
  //// typically 12s, Min 10.4s

  psys->exp_set = 0.0;
  psys->exp_remaining = 0.0;
  psys->exp_starttime = 0.0;
  psys->flag_expcount = 0;      // v0.3.3

  // reset Telescope status/counters

  psys->telstatus = TELSTATUS_NC;
  psys->nston = UNKNOWN;

  psys->duration_slew = 0;
  psys->duration_settling = 0;
  psys->duration_unstable = 0;
  psys->unstable_ra = 0;   // v0.9.0
  psys->unstable_dec = 0;   // v0.9.0
  psys->duration_stable = 0;
  psys->unstable_axis = TEL_AXIS_UNKNOWN;  // v0.9.0
  psys->tpfailed_axis = TEL_AXIS_NO;  // v0.9.0

  psys->allowance_slew = 120;
//psys->allowance_settling = 30;
  psys->allowance_settling = 40;   // v0.2.8
//psys->allowance_unstable = 2;    // tracking or stable status until 2 times (threshold for unstable hysteresis)
//psys->allowance_unstable = 3;    // tracking or stable status until 3 times, increased at v0.9.0 --> moved RC at v0.9.1
  psys->threshold_tracking = 4;    // telstatus = tracking if duration >= threshold_tracking
  psys->threshold_stable = 2;      // telstatus = stable if duration >= threshold_tracking + threshold_stable

  // reset TCS flags/counters

  psys->flag_tcsconnected = 0;
  psys->checknum_tcsconnection = 0;
  psys->interval_tcsconnection = TCS_CONCHK_INTERVAL;
  psys->checknum_tcsdisconnected = 0;
  psys->allowance_tcsdisconnected = 20;  // although update failed, assume still connected until 20 times failure
                                               // ~ 20.0 sec if interval_tcsdata is 1.0 sec (allowance_auxdisconnected*interval_tcsdata)
  psys->flag_tcsdata_updated = 0;
  psys->flag_tcsdata_requested = 0;
  psys->checknum_tcsdata = 0;
  psys->interval_tcsdata = TCS_DATAUP_INTERVAL;  // if 21 loops ~ 1.0 sec

  psys->flag_tcswarning_nearlimit = 0;
  psys->flag_tcswarning_oscinexp = 0;

  // reset ICS configuration

  psys->ics_datasource = ICS_UNDEF;   // v0.6.6

  // reset TCS configuration

  psys->tcs_latitude = 0.0;    // deg N, used for calculating the destination ALT
  psys->tcs_longitude = 0.0;   // deg W, not used yet
  psys->tcs_elevation = 0.0;   // meter, not used yet

  psys->tcs_tolerance_pointing = DEFAULT_TCS_TOLERANCE_POINTING;
  psys->tcs_tolerance_tracking = DEFAULT_TCS_TOLERANCE_TRACKING;
  psys->tcs_allowance_unstable = DEFAULT_TCS_ALLOWANCE_UNSTABLE;  // unstable hysteresis for checking RA/DEC axes oscillation (Typ. 2 or 3)
  
  psys->tcs_limit_ha       = DEFAULT_TCS_LIMIT_HA      ;
  psys->tcs_limit_dec_n    = DEFAULT_TCS_LIMIT_DEC_N   ;
  psys->tcs_limit_dec_s    = DEFAULT_TCS_LIMIT_DEC_S   ;
  psys->tcs_limit_secz     = DEFAULT_TCS_LIMIT_SECZ    ;
  psys->tcs_limit_alt      = DEFAULT_TCS_LIMIT_ALT     ;
  psys->tcs_limit_warning  = DEFAULT_TCS_LIMIT_WARNING ;

  // reset TCS data

  ResetTcsData(psys);

  psys->cmd_velra  = 0.0;  // latest commanded RA velocity for non-sidereal tracking
  psys->cmd_veldec = 0.0;  // latest commanded DEC velocity for non-sidereal tracking
    //// moved here at v0.7.6

  // reset AUX flags/counters

  psys->flag_auxconnected = 0;
  psys->checknum_auxconnection = 0;
  psys->interval_auxconnection = AUX_CONCHK_INTERVAL;
  psys->checknum_auxdisconnected = 0;
  psys->allowance_auxdisconnected = 10;  // although update failed, assume still connected until 10 times failure
                                               // ~ 10.0 sec if interval_auxdata is 1.0 sec (allowance_auxdisconnected*interval_tcsdata)
  psys->flag_auxdata_updated = 0;              
  psys->flag_auxdata_requested = 0;
  //psys->checknum_auxdata = TCS_DATAUP_INTERVAL-4;  // 4 loops(0.2 sec) later than tcsdata update                  
  psys->checknum_auxdata = psys->checknum_tcsdata-TCS_DATAUP_INTERVAL*1/3;    // zero point setting *1/4 --> *1/3 modified at v0.4.0
  psys->interval_auxdata = AUX_DATAUP_INTERVAL;  // if 20 loops ~ 1.0 sec

  psys->flag_filterlabel_requested = 0;
  psys->flag_fsaerror = 0;

  // reset AUX configuration 

  strcpy(psys->filterlabel[FNUM_N], FNAME_N         );
  strcpy(psys->filterlabel[FNUM_1], FNAME_1_DEFAULT );
  strcpy(psys->filterlabel[FNUM_2], FNAME_2_DEFAULT );
  strcpy(psys->filterlabel[FNUM_3], FNAME_3_DEFAULT );
  strcpy(psys->filterlabel[FNUM_4], FNAME_4_DEFAULT );
  strcpy(psys->filterlabel[FNUM_M], FNAME_M         );
  strcpy(psys->filterlabel[FNUM_U], FNAME_U         );

  //reset AUX data

  ResetAuxData(psys);

  //reset Dome status  (v0.9.3/v0.9.4)

  psys->domerot = DOME_UNKNOWN;
  psys->domeshut = DOME_UNKNOWN;

  psys->relay_dctrl_state_drot = RELAY_DROT_UNKNOWN;
  psys->relay_dctrl_failnum = 0;

  psys->redis_domerot = REDIS_DOMEROT_UNKNOWN;
  psys->redis_failnum_domerot = 0;

  psys->redis_domeshut = REDIS_DOMESHUT_UNKNOWN;
  psys->redis_failnum_domeshut = 0;

  // reset flags to override subsys error

  psys->flag_override_auxconnection = 0;
  psys->flag_override_tcsconnection = 0;

  // set timming for connection check and message display

  agent.isISISconnected = 0;
  agent.ISISchecknum = 40;
  psys->checknum_tcsconnection = 30;
  psys->checknum_auxconnection = 20;

  // all done

}

//------------------------------------------------------------------------------
//
// obssys.ResetTcsData - Initialize the TCS data
//

void
ResetTcsData(obssystem_t *psys)
{

  strcpy(psys->ra , "N/A");
  strcpy(psys->dec, "N/A");
  strcpy(psys->ha , "N/A");
  strcpy(psys->lst, "N/A");

  psys->ra_h    = 0.0;
  psys->dec_d   = 0.0;
  psys->epoch_y = 0.0;
  psys->ha_h    = 0.0;
  psys->lst_h   = 0.0;
  psys->secz    = 0.0;
  psys->alt_d   = 0.0;
  psys->az_d    = 0.0;

  psys->movestatus   = TCSSTATUS_MOVE_UNKNOWN;
  psys->limitstatus  = TCSSTATUS_LIMIT_UNKNOWN;
  psys->drivedisable = TCSSTATUS_DRIVE_UNKNOWN;

  //psys->cmd_velra  = 0.0;  // latest commanded RA velocity for non-sidereal tracking
  //psys->cmd_veldec = 0.0;  // latest commanded DEC velocity for non-sidereal tracking
  // disabled not to reset these every call in UpdateTcsData(), alternatively moved to InitSysConfig() at v0.7.6

}

//------------------------------------------------------------------------------
//
// obssys.ResetAuxData - Initialize the AUX data
//

void
ResetAuxData(obssystem_t *psys)
{

  strcpy(psys->fsastatus, "N/A");
  strcpy(psys->shutstatus, "N/A");
  strcpy(psys->shutopstat, "N/A");
  strcpy(psys->filteropstat, "N/A");
  strcpy(psys->filtername, FNAME_X);
  psys->filternum  = FNUM_X;

  psys->focus = 0.0;
  psys->tns   = 0.0;
  psys->tew   = 0.0;

  memset(psys->ens, 0, sizeof(psys->ens));
  strcpy(psys->fan, "OFF");
  strcpy(psys->telid, DEFAULT_TELID);

  strcpy(psys->dsstatus, "N/A");   // v0.9.3
  psys->aux_domeshut = AUX_STATUS_UNKNOWN;   // v0.9.4

}

//------------------------------------------------------------------------------
//
// obssys.QueryTcsData - Send a query message 'TSTAT' to request the TCS data to TC node
//
// return 0 on success, -1 on errors
// if error or no response, TCS link in TC or TC node in ICIMACIS is not available
//

int
QueryTcsData(obssystem_t *psys, char *reply)
{
  int rtn;
  char msg[STRLEN_CMD];

  // Request TCS data

  strcpy(InputCMD, "TSTAT");
  //rtn = cmd_tc("", EXEC, reply); 
  //if(rtn!=CMD_NOOP) {
  // ..
  // --> always error in cmd_tc() when ISIS is not connected yet.

  sprintf(msg,"%s>TC %s\r",client.ID, InputCMD);
  rtn = SendToISISServer(&client,msg);
  sprintf(cmsg, "ISIS OUT: %s\n",msg);_dbgmsgout(cmsg);
  if(rtn<0) {
    strcpy(reply, "Failed to send a command to request TCS data to TC node");    
    return -1;
  }

  // all done

  strcpy(reply, "TCS data request commanded..");

  psys->flag_tcsdata_requested = 1;
  psys->flag_tcsdata_updated = 0;

  return 0;
}
// --> Acually this func is not necessory for handling error because cmd_tc() never return error.
//     we can just use cmd_tc() directory. but use this object-oriented commands.c.

//------------------------------------------------------------------------------
//
// obssys.UpdateTcsData - Update the TCS data with TSTAT response
//
// return 0 on success, -1 on errors
//

int
UpdateTcsData(obssystem_t *psys, char *args, char *reply)
{
  double dTimestamp = SysTimestamp();

  int rtn;
  char strRA [STRLEN_ARG];
  char strDEC[STRLEN_ARG];
  char strHA [STRLEN_ARG];
  char strLST[STRLEN_ARG];
  double dRA, dDEC, dHA, dLST;
  double dEpoch, dSecZ, dAlt, dAz;
  double dSec, dClearance;
  double dVelRA, dVelDEC;
  double dTrackTolRa;   // tolerance of RA tracking
  double dTrackTolDec;   // tolerance of DEC tracking
  int nMove, nLimit, nDrive;
  int nHour, nDeg, nMin;
  char cSign;

  static double dRA_prev, dHA_prev, dDEC_prev;
  static double dTimestamp_prev;

  //// Reset TCS data

  ResetTcsData(psys);

  //// Parser TSTAT string

  rtn = sscanf(args, "%*s %*s %*s %*s %s %s %lf %s %s %lf %lf %lf %d %d %d %*s", 
                      strRA, strDEC, &dEpoch, strHA, strLST, &dSecZ, &dAlt, &dAz, &nMove, &nLimit, &nDrive);

  //// arguments number check

  if(rtn<11) {        
    sprintf(reply, "Failed to update the TCS data, not enough arguments number(=%d) in TSTAT string", rtn);
    return -01;
  }

  //// check RA input string and values

  rtn = sscanf(strRA, "%d%*c%d%*c%lf", &nHour, &nMin, &dSec);

  if(rtn<3) {        
    sprintf(reply, "Failed to update the TCS data, unrecognized RA '%s'", strRA);
    return -11;
  }

  dRA = fabs((double)nHour) + (double)nMin/60.0 + dSec/3600.0;
  if( strRA[0]=='-' ) dRA *= -1.0;

  if( strRA[0]=='-' || nHour<0 || nHour>=24 || nMin<0 || nMin>=60 || dSec<0.0 || dSec>=60.0 || dRA<0.0 || dRA>24.0 ) {
    sprintf(reply, "Failed to update the TCS data, RA '%s' is out of range.", strRA);
    return -12;
  }

  cSign = trans1060(dRA, &nHour, &nMin, &dSec, 2);
  sprintf(psys->ra, "%02d:%02d:%05.2f", nHour, nMin, dSec);

  //// check DEC input string and values

  rtn = sscanf(strDEC, "%d%*c%d%*c%lf", &nDeg, &nMin, &dSec);

  if(rtn<3) {
    sprintf(reply, "Failed to update the TCS data, unrecognized DEC '%s'", strDEC);
    return -21;
  }

  dDEC = fabs((double)nDeg) + (double)nMin/60.0 + dSec/3600.0;
  if( strDEC[0]=='-' ) dDEC *= -1.0;

  if( nDeg<-90 || nDeg>90 || nMin<0 || nMin>=60 || dSec<0.0 || dSec>=60.0 || dDEC<-90.0 || dDEC>90.0 ) {
    sprintf(reply, "Failed to update the TCS data, DEC '%s' is out of range.", strDEC);
    return -22;
  }

  cSign = trans1060(dDEC, &nDeg, &nMin, &dSec, 1);
  sprintf(psys->dec, "%c%02d:%02d:%04.1f", cSign, nDeg, nMin, dSec);

  //// check Epoch value

  if( dEpoch<1900.0 || dEpoch>3000.0 ) {
    sprintf(reply, "Failed to update the TCS data, Epoch input(=%f) is out of range.", dEpoch);
    return -51;
  }

  //// check HA input string and values

  rtn = sscanf(strHA, "%d%*c%d%*c%lf", &nHour, &nMin, &dSec);

  if(rtn<3) {        
    sprintf(reply, "Failed to update the TCS data, unrecognized HA '%s'", strHA);
    return -31;
  }

  dHA = fabs((double)nHour) + (double)nMin/60.0 + dSec/3600.0;
  if( strHA[0]=='-' ) dHA *= -1.0;

  if( nHour<-12 || nHour>+12 || nMin<0 || nMin>=60 || dSec<0.0 || dSec>=60.0 || dHA<-12.0 || dHA>+12.0 ) {
    sprintf(reply, "Failed to update the TCS data, HA '%s' is out of range.", strHA);
    return -32;
  }

  cSign = trans1060(dHA, &nHour, &nMin, &dSec, 0);
  sprintf(psys->ha, "%c%02d:%02d:%02.0f", cSign, nHour, nMin, dSec);

  //// check LST input string and values

  rtn = sscanf(strLST, "%d%*c%d%*c%lf", &nHour, &nMin, &dSec);

  if(rtn<3) {        
    sprintf(reply, "Failed to update the TCS data, unrecognized LST '%s'", strLST);
    return -41;
  }

  dLST = fabs((double)nHour) + (double)nMin/60.0 + dSec/3600.0;
  if( strLST[0]=='-' ) dLST *= -1.0;

  if( strLST[0]=='-' || nHour<0 || nHour>=24 || nMin<0 || nMin>=60 || dSec<0.0 || dSec>=60.0 || dLST<0.0 || dLST>24.0 ) {
    sprintf(reply, "Failed to update the TCS data, LST '%s' is out of range.", strLST);
    return -42;
  }

  cSign = trans1060(dLST, &nHour, &nMin, &dSec, 0);
  sprintf(psys->lst, "%02d:%02d:%02.0f", nHour, nMin, dSec);

  //// check SecZ value

  if( dSecZ<1.0 || dSecZ>3.9 ) {  // (Alt < 15 deg)
    sprintf(reply, "Failed to update the TCS data, SecZ input(=%f) is out of range.", dSecZ);
    return -52;
  }

  //// check Alt/Az value

  if( dAlt<15.0 || dAlt>90.001 ) {
    sprintf(reply, "Failed to update the TCS data, Alt input(TC_DATAUP_INTERVAL=%f) is out of range.", dAlt);
    return -53;
  }

  if( dAz<-180.001 || dAz>+180.001 ) {
    sprintf(reply, "Failed to update the TCS data, Az input(=%f) is out of range.", dAz);
    return -54;
  }

  //// check move status value

  if( nMove<0 || nMove>3 ) {
    sprintf(reply, "Failed to update the TCS data, unrecognized Move status input(=%d)", nMove);
    return -61;
  }

  //// check limit status value

  if( nLimit<0 || nLimit>7 ) {
    sprintf(reply, "Failed to update the TCS data, unrecognized Limit status input(=%d)", nLimit);
    return -62;
  }

  //// check drive status value

  if( nDrive<0 || nDrive>1 ) { 
    sprintf(reply, "Failed to update the TCS data, unrecognized Drive status input(=%d)", nDrive);
    return -63;
  }

  psys->ra_h     = dRA;
  psys->dec_d    = dDEC;
  psys->epoch_y  = dEpoch;
  psys->ha_h     = dHA;
  psys->lst_h    = dLST;
  psys->secz     = dSecZ;
  psys->alt_d    = dAlt;
  psys->az_d     = dAz;

  psys->movestatus   = nMove;
  psys->limitstatus  = nLimit;
  psys->drivedisable = nDrive;

  ////Limit monitoring and warning

  agent.flag_warning = 1;

  switch (nLimit) {
     case 1: REDTEXT;sprintf(cmsg, "WARNING: Limit RA !!\n"       );_msgout(cmsg);break;
     case 2: REDTEXT;sprintf(cmsg, "WARNING: Limit DEC !!\n"      );_msgout(cmsg);break;
     case 3: REDTEXT;sprintf(cmsg, "WARNING: Limit RA+DEC !!\n"   );_msgout(cmsg);break;
     case 4: REDTEXT;sprintf(cmsg, "WARNING: Limit ELEVATION !!\n");_msgout(cmsg);break;
     case 5: REDTEXT;sprintf(cmsg, "WARNING: Limit RA+EL !!\n"    );_msgout(cmsg);break;
     case 6: REDTEXT;sprintf(cmsg, "WARNING: Limit DEC+EL !!\n"   );_msgout(cmsg);break;
     case 7: REDTEXT;sprintf(cmsg, "WARNING: Limit RA+DEC+EL !!\n");_msgout(cmsg);break;
     default: agent.flag_warning = 0; break;
  }

  dClearance = ( psys->tcs_limit_ha - fabs(dHA) ) * 15.0;   // in deg
  //if( dClearance < psys->tcs_limit_warning ) {
  if( dClearance < psys->tcs_limit_warning && psys->flag_tcswarning_nearlimit ) {   // v0.4.5
    psys->flag_tcswarning_nearlimit = 0;   // v0.4.5
    //if( dHA>0.0 ) REDTEXT; else CYATEXT;   // v0.4.0
    //sprintf(cmsg, "WARNING: Near HA limit, clearance = %.1f min\n", dClearance*4.0);_msgout(cmsg);
    if( dHA>0.0 ) {
      REDTEXT;sprintf(cmsg, "WARNING: Near HA limit in the west, clearance = %.1f min\n", dClearance*4.0);_msgout(cmsg);
    }
    else {
      CYATEXT;sprintf(cmsg, "Warning: Near eastern HA limit in the east, clearance = %.1f min\n", dClearance*4.0);_msgout(cmsg);
    } //// v0.9.4
    if( dHA>0.0 && dClearance<psys->tcs_limit_warning*0.4 ) agent.flag_warning = 1;   // blinking on if 40% remains at west side, v0.4.0
  }

  dClearance = psys->tcs_limit_dec_n - dDEC;
  //if( dClearance < psys->tcs_limit_warning ) {
  if( dClearance < psys->tcs_limit_warning && psys->flag_tcswarning_nearlimit ) {   // v0.4.5
    psys->flag_tcswarning_nearlimit = 0;   // v0.4.5
    CYATEXT;sprintf(cmsg, "Warning: Near DEC limit, clearance = %.1f deg in the north\n", dClearance);_msgout(cmsg);
  }

  dClearance = dDEC - psys->tcs_limit_dec_s;
  //if( dClearance < psys->tcs_limit_warning ) {
  if( dClearance < psys->tcs_limit_warning && psys->flag_tcswarning_nearlimit ) {   // v0.4.5
    psys->flag_tcswarning_nearlimit = 0;   // v0.4.5
    REDTEXT;sprintf(cmsg, "WARNING: Near DEC limit, clearance = %.1f deg in the south\n", dClearance);_msgout(cmsg);
  }

  dClearance = dAlt - psys->tcs_limit_alt;
  //if( dClearance < psys->tcs_limit_warning ) {
  if( dClearance < psys->tcs_limit_warning && psys->flag_tcswarning_nearlimit ) {  // v0.4.5
    psys->flag_tcswarning_nearlimit = 0;   // v0.4.5
    //if( dHA>0.0 ) REDTEXT; else CYATEXT;   // v0.4.0
    //sprintf(cmsg, "WARNING: Near ELEVATION limit, clearance = %.1f deg\n", dClearance);_msgout(cmsg);
    if( dHA>0.0 ) {
      REDTEXT;sprintf(cmsg, "WARNING: Near ELEVATION limit in the west, clearance = %.1f deg\n", dClearance);_msgout(cmsg);
    } 
    else {
      CYATEXT;sprintf(cmsg, "Warning: Near ELEVATION limit in the east, clearance = %.1f deg\n", dClearance);_msgout(cmsg);
    } //// v0.9.4
    if( dHA>0.0 && dClearance<psys->tcs_limit_warning*0.4 ) agent.flag_warning = 1;   // blinking on if 40% remains at west side, v0.4.0
  }

  //// update flags and monitoring count

  if( !psys->flag_tcsconnected ) {
    psys->flag_tcsconnected = 1;
    GRNTEXT;sprintf(cmsg, "STATUS: TCS Agent is connected with PC-TCS.\n");_msgout(cmsg);
  }

  psys->flag_tcsdata_requested = 0;
  psys->flag_tcsdata_updated = 1;
  
  psys->checknum_tcsdisconnected = 0;

  //// update telescope status

  if( psys->telstatus == TELSTATUS_NC ) {

    psys->telstatus = TELSTATUS_CHECKING;
    psys->duration_stable = 0;  // v0.4.2

  }

  else {

    if( nDrive==1 ) {
        psys->telstatus = TELSTATUS_DISABLED;
        psys->duration_slew = 0;
        psys->duration_settling = 0;
        psys->unstable_axis = TEL_AXIS_NO;   // v0.9.0
        psys->unstable_ra = psys->unstable_dec = 0;   // v0.9.0
        psys->duration_unstable = 0;
        psys->duration_stable = 0;
    }
    else if( nMove==TCSSTATUS_MOVE_NO ) {

        if(psys->nston) {  // prototype code at v0.6.9, modified with (dTimestamp-dTeimstamp_prev) at v0.7.5
          dVelRA  = psys->cmd_velra ;
          dVelDEC = psys->cmd_veldec;
        }
        else {
          dVelRA  = 0;
          dVelDEC = 0;
        }

        dTrackTolRa  = psys->tcs_tolerance_tracking + fabs( dVelRA  * (dTimestamp-dTimestamp_prev) * 0.4 * cosd(dDEC) );
        dTrackTolDec = psys->tcs_tolerance_tracking + fabs( dVelDEC * (dTimestamp-dTimestamp_prev) * 0.4              );

      //if( fabs(dRA-dRA_prev)*3600.0*15.0 < psys->tcs_tolerance && fabs(dDEC-dDEC_prev)*3600.0 < psys->tcs_tolerance ) {
      //if( fabs(dRA -dRA_prev )*3600.0*15.0*cosd(dDEC) < psys->tcs_tolerance_tracking && 
      //    fabs(dDEC-dDEC_prev)*3600.0                 < psys->tcs_tolerance_tracking   ) {  // v0.4.2
      //if( fabs(dRA -dRA_prev )*3600.0*15.0*cosd(dDEC) < dTrackTolRa && 
      //    fabs(dDEC-dDEC_prev)*3600.0                 < dTrackTolDec  ) {  // v0.6.9
        if( fabs( (dRA -dRA_prev  )*3600.0*15.0 - dVelRA *(dTimestamp-dTimestamp_prev) ) * cosd(dDEC) < dTrackTolRa && 
            fabs( (dDEC-dDEC_prev )*3600.0      - dVelDEC*(dTimestamp-dTimestamp_prev) )              < dTrackTolDec  ) {  // v0.7.5

            psys->duration_stable++;

            //if( psys->telstatus == TELSTATUS_TRACKING || psys->telstatus == TELSTATUS_TRACKINGS ) {
            //    if( psys->threshold_stable <= psys->duration_stable ) {
            //        psys->telstatus = TELSTATUS_TRACKINGS;
            //    }
            //}
            //else {
            //    psys->telstatus = TELSTATUS_TRACKING;
            //} 

            if( psys->threshold_tracking + psys->threshold_stable <= psys->duration_stable ) {
              psys->telstatus = TELSTATUS_TRACKINGS;
            }
            else if( psys->threshold_tracking <= psys->duration_stable ) {
              if( psys->telstatus == TELSTATUS_CHECKING ) psys->flag_tcswarning_nearlimit = 1;   // v0.4.5
              psys->telstatus = TELSTATUS_TRACKING;
            } //// modified at v0.4.2

            psys->unstable_axis = TEL_AXIS_NO;   // v0.9.0
            psys->unstable_ra = psys->unstable_dec = 0;   // v0.9.0
            psys->duration_unstable = 0;

        }
        //else if( fabs(dHA-dHA_prev)*3600.0*15.0 < psys->tcs_tolerance_tracking && fabs(dDEC-dDEC_prev)*3600.0 < psys->tcs_tolerance_tracking ) {
        else if( fabs(dHA-dHA_prev)*3600.0*15.0 < 0.1 && fabs(dDEC-dDEC_prev)*3600.0 < 0.1 ) {

            if( dAlt >= 89.9 && fabs(dAz) <= 0.1 ) psys->telstatus = TELSTATUS_STOW;
            else {
              if( psys->telstatus == TELSTATUS_CHECKING ) psys->flag_tcswarning_nearlimit = 1;   // v0.4.5
              psys->telstatus = TELSTATUS_HOLDING;
            }

            psys->unstable_axis = TEL_AXIS_NO;   // v0.9.0
            psys->unstable_ra = psys->unstable_dec = 0;   // v0.9.0
            psys->duration_unstable = 0;
            psys->duration_stable = 0;

        }
        else if( psys->tcs_allowance_unstable <= psys->duration_unstable++ ) {

            if( abs( psys->unstable_ra - psys->unstable_dec ) <= (psys->tcs_allowance_unstable/3) ) psys->unstable_axis = TEL_AXIS_BOTH;
            else if( psys->unstable_ra > psys->unstable_dec ) psys->unstable_axis = TEL_AXIS_RA;
            else if( psys->unstable_ra < psys->unstable_dec ) psys->unstable_axis = TEL_AXIS_DEC;    //// v0.9.0

            if( psys->telstatus == TELSTATUS_CHECKING ) psys->flag_tcswarning_nearlimit = 1;   // v0.4.5
            psys->telstatus = TELSTATUS_OSCILLATE;
            psys->duration_stable = 0;

            //  if( CAMSTATUS_INT_2<=psys->camstatus && psys->camstatus<=CAMSTATUS_CLOSING && psys->flag_tcswarning_oscinexp ) {  // Oscillation during exposure
            //    CYATEXT;sprintf(cmsg, "WARNING: Oscillation on %s during the exposure !\n", (psys->unstable_axis==TEL_AXIS_BOTH)?"Both RA/Dec axes":
            //                           (psys->unstable_axis==TEL_AXIS_RA)?"RA axis":(psys->unstable_axis==TEL_AXIS_DEC)?"DEC axis":"unknown axis");_msgout(cmsg);
            //    psys->flag_tcswarning_oscinexp = 0;   // on again at when camstatus==CAMSTATUS_INT_1
            //  } ///// v0.9.0

            if( CAMSTATUS_INT_2<=psys->camstatus && psys->camstatus<=CAMSTATUS_CLOSING ) {  // Oscillation during exposure
              if( psys->flag_tcswarning_oscinexp ) {
                sprintf(cmsg, "WARNING: Oscillation on %s during the exposure !\n", (psys->unstable_axis==TEL_AXIS_BOTH)?"Both RA/Dec axes":
                               (psys->unstable_axis==TEL_AXIS_RA)?"RA axis":(psys->unstable_axis==TEL_AXIS_DEC)?"DEC axis":"unknown axis");
                CYATEXT;_msgout(cmsg);
                psys->flag_tcswarning_oscinexp = 0;   // on again at when camstatus==CAMSTATUS_INT_1
              }
              if( expinfo.flagOscInExp==FALSE ) {
                if( ++expinfo.cntOscInExp > (int)(expinfo.dSetting*0.05) ) expinfo.flagOscInExp = TRUE;  // if oscillating more than 5% of exposure time
              }
            } ///// v1.0.9

        }
        else {

          psys->unstable_ra++;  psys->unstable_dec++;
          if( fabs( (dHA - dHA_prev )*3600.0*15.0                                        )              < 0.1          ) psys->unstable_ra-- ;
          if( fabs( (dRA - dRA_prev )*3600.0*15.0 - dVelRA *(dTimestamp-dTimestamp_prev) ) * cosd(dDEC) < dTrackTolRa  ) psys->unstable_ra-- ;
          if( fabs( (dDEC-dDEC_prev )*3600.0      - dVelDEC*(dTimestamp-dTimestamp_prev) )              < dTrackTolDec ) psys->unstable_dec--;   ///// v0.9.0

          psys->unstable_axis = TEL_AXIS_UNKNOWN;   // v0.9.0
          //psys->telstatus = TELSTATUS_TRACKING;
          psys->telstatus = TELSTATUS_CHECKING;   // modified at v0.4.2
          psys->flag_tcswarning_nearlimit = 0;   // v0.4.5
          psys->duration_stable = 0;

        }

        psys->duration_slew = 0;
        psys->duration_settling = 0;

    ///////////////////////////////////////////////////////////////////////////////////////
        char strTStat[16];
        switch (psys->telstatus) {
          case TELSTATUS_NC       : strcpy(strTStat, "NC"       ); break;
          case TELSTATUS_CHECKING : strcpy(strTStat, "CHECKING" ); break;
          case TELSTATUS_STOW     : strcpy(strTStat, "STOW"     ); break;
          case TELSTATUS_HOLDING  : strcpy(strTStat, "HOLDING"  ); break;
          case TELSTATUS_TRACKING : strcpy(strTStat, "TRACKING" ); break;
          case TELSTATUS_TRACKINGS: strcpy(strTStat, "TRACKINGS"); break;
          case TELSTATUS_SLEW     : strcpy(strTStat, "SLEW"     ); break;
          case TELSTATUS_SETTLING : strcpy(strTStat, "SETTLING" ); break;
          case TELSTATUS_OSCILLATE: strcpy(strTStat, "OSCILLATE"); break;
          case TELSTATUS_DISABLED : strcpy(strTStat, "DISABLED" ); break;
          default                 : strcpy(strTStat, "UNKNOWN"  ); break;
        }
        BLUTEXT;
        sprintf(cmsg, "DBG: dSec %.2f   RA %+6.2f   DEC %+6.2f   TSTAT: %s\n", 
                      (dTimestamp-dTimestamp_prev), 
                      (dTimestamp-dTimestamp_prev)*dVelRA, 
                      (dTimestamp-dTimestamp_prev)*dVelDEC, 
                      strTStat  );_dbgmsgout(cmsg);
    /////////////////////////////////////////////////////////////////////////////// for DBG

    }
    else {
        //if( fabs(dHA-dHA_prev)*15.0 < psys->tcs_slewspeed_ra/2.0 && fabs(dDEC-dDEC_prev) < psys->tcs_slewspeed_ra/2.0 ) {  // The update interval must be ~1 sec.
        if( fabs(dHA-dHA_prev)*15.0 < psys->tcs_slewspeed_ra/3.0 && fabs(dDEC-dDEC_prev) < psys->tcs_slewspeed_dec/3.0 ) {  // The update interval must be ~1 sec. , /2.0 changed to / 3.0 at v0.2.8
            psys->telstatus = TELSTATUS_SETTLING;
            if( psys->allowance_settling < psys->duration_settling++ ) {
                psys->telstatus = TELSTATUS_OSCILLATE;
            }
        }
        else {
            psys->telstatus = TELSTATUS_SLEW;
            if( psys->allowance_slew < psys->duration_slew++ ) {
                psys->telstatus = TELSTATUS_OSCILLATE;
            }
        }
        psys->flag_tcswarning_nearlimit = 1;   // v0.4.5
        psys->unstable_axis = TEL_AXIS_NO;   // v0.9.0
        psys->unstable_ra = psys->unstable_dec = 0; // v0.9.0
        psys->duration_unstable = 0;
        psys->duration_stable = 0;
    }
    
  }

  dRA_prev  = dRA;
  dHA_prev  = dHA;
  dDEC_prev = dDEC;
  dTimestamp_prev = dTimestamp;

  //// all done

  strcpy(reply, "TCS data updated successfully");

  { // observation system status update & debugging msg display

      //cmd_sysstatus("", EXEC, SysStatus);
      //sprintf(cmsg, "STATUS: TcsDataUpdated  SYS.STATUS: %s\n", SysStatus);_dbgmsgout(cmsg);   // --> too much logging data

      sprintf(cmsg, "STATUS: TCS DATA UPDATED\n");_dbgmsgout(cmsg);   // v0.2.8

  }

  return 0;
}

//// For reference,
//
// TSTAT response,
// DONE: UP 1 2017-12-25T20:01:01.004 UTC 2017-12-25T20:01:00.075 21:34:58.82 -30:05:02.7 2000.000 +00:00:00 21:35:51  1.00 90.0   +0.0  0  0  0 E
// DONE: UP 1 2017-12-29T18:41:22.462 UTC 2017-12-29T18:41:22.245 20:30:51.55 -30:03:57.5 2000.000 +00:00:00 20:31:46  1.00 90.0   +0.0  0  0  1 E
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

//------------------------------------------------------------------------------
//
// obssys.QueryAuxData - Send a query message 'ASTAT' to request the AUX data to TC node
//
// return 0 on success, -1 on errors
// if error or no response, AUX link in TC or TC node in ICIMACIS is not available
//

int
QueryAuxData(obssystem_t *psys, char *reply)
{
  int rtn;
  char msg[STRLEN_CMD];

  // Request AUX data

  strcpy(InputCMD, "ASTAT");
  //rtn = cmd_tc("", EXEC, reply); 
  //if(rtn!=CMD_NOOP) {
  // ..
  // --> always error in cmd_tc() when ISIS is not connected yet.

  sprintf(msg,"%s>TC %s\r",client.ID, InputCMD);
  rtn = SendToISISServer(&client,msg);
  sprintf(cmsg, "ISIS OUT: %s\n",msg);_dbgmsgout(cmsg);
  if(rtn<0) {
    strcpy(reply, "Failed to send a command to request AUX data to TC node");    
    return -1;
  }

  // all done

  strcpy(reply, "AUX data request commanded..");

  psys->flag_auxdata_requested = 1;
  psys->flag_auxdata_updated = 0;

  return 0;
}
// --> Acually this func is not necessory for handling error because cmd_tc() never return error.
//     we can just use cmd_tc() directory. but use this object-oriented commands.c.

//------------------------------------------------------------------------------
//
// obssys.UpdateAuxData - Update the AUX data with ASTAT response
//
// return 0 on success, -1 on errors
//

int
UpdateAuxData(obssystem_t *psys, char *args, char *reply)
{
  int rtn;

  //// Reset AUX data

  ResetAuxData(psys);

  //// Parser ASTAT string

  rtn = sscanf(args, "%*s %*s %*s %s %*s "
                     "%*s %s %s %d %s "
                     "%s %s "
                     "%*s %*s %lf %lf %lf %*s %*s %*s %*s %*s %*s "
                     "%*s %s %*s %*s %*s %*s %*s %*s "
                     "%*s %*s %*s %*s %*s %*s %*s %*s "
                     "%*s %*s %s %lf %lf %lf "
                     "%lf %lf %lf %lf",
                      psys->telid, 
                      psys->fsastatus, psys->filteropstat, &psys->filternum, psys->filtername, 
                      psys->shutopstat, psys->shutstatus, 
                      &psys->focus, &psys->tns, &psys->tew, 
                      psys->dsstatus,  // v0.9.3
                      psys->fan, &psys->ens[0], &psys->ens[1], &psys->ens[2], 
                      &psys->ens[3], &psys->ens[4], &psys->ens[5], &psys->ens[6]);

  //// arguments number check

  if(rtn<18) {        
    ResetAuxData(psys);
    sprintf(reply, "Failed to update the AUX data, not enough arguments number(=%d) in ASTAT string", rtn);
    return -01;
  }

  if(psys->filternum==AUX_UNKNOWN) psys->filternum = FNUM_U;

  //// Subsys connection monitoring and warning

  if( strcasecmp(psys->fsastatus,"NC")==0 ) {
    REDTEXT;sprintf(cmsg, "WARNING: AUX Filter/Shutter subsystem is not connected. Check it in AUX system..\n");_msgout(cmsg);
    agent.flag_warning = 1;
  }

  //if( strcasecmp(psys->fsastatus,"ERROR")==0 ) {
  //  REDTEXT;sprintf(cmsg, "WARNING: Error occurred in the AUX Filter/Shutter subsystem. Check it on AUX system..\n");_msgout(cmsg);
  //}
  if( strcasecmp(psys->fsastatus,"ERROR")==0 ) {
    if( psys->flag_fsaerror==0 ) {
      psys->flag_fsaerror = 1;   // v0.3.4
      REDTEXT;sprintf(cmsg, "WARNING: Error occurred in the AUX Filter/Shutter subsystem. Check it on AUX system..\n");_msgout(cmsg);
      agent.flag_warning = 1;  // v0.3.5
    }
  }
  else {
    psys->flag_fsaerror = 0;   // v0.3.4
  }

  /////// checking shutter operation status & setting expcount flag (v0.3.3)
  /////// this rountine is for double checking to update exposure time remaining
  ///
  ///if( strcasecmp(psys->shutopstat,"OPENING")==0 || strcasecmp(psys->shutopstat,"OPENED")==0 ) {
  ///  if( psys->flag_expcount != 1 ) {
  ///    psys->flag_expcount = 1;
  ///    psys->exp_starttime = SysTimestamp();
  ///  }
  ///}
  ///else {
  ///  if( psys->flag_expcount != 0 ) {
  ///    psys->flag_expcount = 0;
  ///    psys->exp_remaining = 0.0;
  ///  }    
  ///}
  /// ==> removed because of interference with update using CamStatus

  //// Dome shutter status update (v0.9.4)

       if( strcasecmp(psys->dsstatus,"NC"     )==0 ) psys->aux_domeshut = AUX_STATUS_NC     ;
  else if( strcasecmp(psys->dsstatus,"STANDBY")==0 ) psys->aux_domeshut = AUX_STATUS_STANDBY;
  else if( strcasecmp(psys->dsstatus,"RUNNING")==0 ) psys->aux_domeshut = AUX_STATUS_RUNNING;
  else if( strcasecmp(psys->dsstatus,"ERROR"  )==0 ) psys->aux_domeshut = AUX_STATUS_ERROR  ;
  else                                               psys->aux_domeshut = AUX_STATUS_UNKNOWN;

  //// update flags and monitoring count

  if( !psys->flag_auxconnected ) {
    psys->flag_auxconnected = 1;
    psys->checknum_auxdata = psys->checknum_tcsdata-TCS_DATAUP_INTERVAL*1/3;    // zero point setting at AUX connection as well, added at v0.4.0    
    GRNTEXT;sprintf(cmsg, "STATUS: TCS Agent is connected with AUX Ctrl.\n");_msgout(cmsg);
  }

  psys->flag_auxdata_requested = 0;
  psys->flag_auxdata_updated = 1;
  psys->checknum_auxdisconnected = 0;

  //// all done

  strcpy(reply, "AUX data updated successfully");

  { // observation system status update & debugging msg display

      //cmd_sysstatus("", EXEC, SysStatus);
      //sprintf(cmsg, "STATUS: AuxDataUpdated  SYS.STATUS: %s\n", SysStatus);_dbgmsgout(cmsg);   // --> too much logging data

      sprintf(cmsg, "STATUS: AUX DATA UPDATED\n");_dbgmsgout(cmsg);   // v0.2.8

  }

  return 0;
}

//// For reference,
//
// ASTAT response,
// DONE: UP 1 2017-12-29T18:41:24.682 UTC KMTC 2017-12-29T18:41:24.643  FS: STANDBY STANDBY 0 NO STANDBY CLOSED  FA: STANDBY -1.200 -110.0 +174.9  0 0 0  -0.662 -0.728 -2.210  DS: NC UNKNOWN UNKNOWN UNKNOWN DISABLED 0.0 0.0  MC: STANDBY 0  CH: STANDBY ON 8.0 -1.2  EN: STANDBY ON 26.3 25.6 18.5 29.5 11.9 11.5 0.0
// DONE: UP 1 2017-06-20T22:36:02.149 UTC KMTC 2017-06-20T22:36:02.149  FS: STANDBY STANDBY 2 R STANDBY CLOSED  FA: STANDBY -0.940 -105.0 +155.0  0 0 0  -0.426 -0.540 -1.853  DS: STANDBY CLOSED CLOSED ACTIVE DISABLED 16.8 83.7  MC: STANDBY 0  CH: STANDBY OFF 7.0 6.8  EN: STANDBY OFF 11.7 11.4 9.7 12.4 0.0 10.6 0.0
// DONE: UP 1 2017-06-20T23:19:20.097 UTC KMTC 2017-06-20T23:19:19.997  FS: STANDBY STANDBY 3 V OPENED OPEN  FA: STANDBY -0.900 -105.0 +155.0  0 0 0  -0.386 -0.500 -1.813  DS: RUNNING MID OPEN INACTIVE DISABLED 83.4 55.1  MC: STANDBY 100  CH: STANDBY OFF 7.0 6.8  EN: STANDBY OFF 10.1 10.8 9.7 9.1 0.0 10.6 0.0
// DONE: UP 1 2017-06-20T23:19:25.146 UTC KMTC 2017-06-20T23:19:24.951  FS: STANDBY STANDBY 3 V CLOSING OPEN  FA: STANDBY -0.900 -105.0 +155.0  0 0 0  -0.386 -0.500 -1.813  DS: RUNNING MID OPEN INACTIVE DISABLED 85.3 55.1  MC: STANDBY 100  CH: STANDBY OFF 7.0 6.8  EN: STANDBY OFF 10.1 10.8 9.7 9.1 0.0 10.6 0.0
// DONE: UP 1 2017-06-20T23:19:30.150 UTC KMTC 2017-06-20T23:19:30.150  FS: STANDBY STANDBY 3 V RELOADING CLOSED  FA: STANDBY -0.900 -105.0 +155.0  0 0 0  -0.386 -0.500 -1.813  DS: RUNNING MID OPEN INACTIVE DISABLED 87.4 55.1  MC: STANDBY 100  CH: STANDBY OFF 7.0 6.8  EN: STANDBY OFF 10.1 10.8 9.7 9.1 0.0 10.6 0.0
// DONE: UP 1 2017-06-20T23:19:35.163 UTC KMTC 2017-06-20T23:19:35.163  FS: STANDBY STANDBY 3 V STANDBY CLOSED  FA: STANDBY -0.900 -105.0 +155.0  0 0 0  -0.386 -0.500 -1.813  DS: RUNNING MID OPEN INACTIVE DISABLED 89.3 55.0  MC: STANDBY 100  CH: STANDBY OFF 7.0 6.8  EN: STANDBY OFF 10.2 10.8 9.7 9.1 0.0 10.6 0.0
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
//   FILNUM   : actual current filter number, currently updated with limits feedback (no:0 / filter 1~4:1~4 / 2 more:5 / unknown:-1)
//   FILTER   : supposed current filter name, lately commanded (NO: no filter / MANY: 2 more filters / UNKNOWN)
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
//

//------------------------------------------------------------------------------
//
// QueryFilterLabels - Send a query message to request the filter labels of current set to TC node
//
// return 0 on success, -1 on errors
// if error, AUX link in TC or TC node in ICIMACIS is not available
//

int
QueryFilterLabels(obssystem_t *psys, char *reply)
{
  int rtn;
  char msg[STRLEN_CMD];

  // Request filter names

  strcpy(InputCMD, "FILNAME");
  //rtn = cmd_tc("", EXEC, reply); 
  //if(rtn!=CMD_NOOP) {
  // ..
  // --> always error in cmd_tc() when ISIS is not connected yet.

  sprintf(msg,"%s>TC %s\r",client.ID, InputCMD);
  rtn = SendToISISServer(&client,msg);
  sprintf(cmsg, "ISIS OUT: %s\n",msg);_dbgmsgout(cmsg);
  if(rtn<0) {
    strcpy(reply, "Failed to send a command to request filter names to TC node");    
    return -1;
  }

  // all done

  strcpy(reply, "Filter name request commanded..");

  psys->flag_filterlabel_requested = 1;

  return 0;
}
// --> Acually this func is not necessory for handling error because cmd_tc() never return error.
//     we can just use cmd_tc() directory. but use this object-oriented commands.c.

//------------------------------------------------------------------------------
//
// UpdateFilterLabels - Update the filter labels of current set with FILNAME response
//
// return 0 on success, -1 on errors
//

int
UpdateFilterLabels(obssystem_t *psys, char *args, char *reply)
{
  int rtn;
  char fname[4][16];

  // Parser FILNAME string
  rtn = sscanf(args, "%*[^=]%s %*[^=]%s %*[^=]%s %*[^=]%s", fname[0], fname[1], fname[2], fname[3]);

  // Check argument number
  if(rtn!=4)
  {
      sprintf(reply, "Filter name update failed due to not enough argument number(=%d)\n", rtn);
      return -1;
  }

  strcpy(psys->filterlabel[FNUM_N], FNAME_N   );
  strcpy(psys->filterlabel[FNUM_1], fname[0]+1);
  strcpy(psys->filterlabel[FNUM_2], fname[1]+1);
  strcpy(psys->filterlabel[FNUM_3], fname[2]+1);
  strcpy(psys->filterlabel[FNUM_4], fname[3]+1);
  strcpy(psys->filterlabel[FNUM_M], FNAME_M   );
  strcpy(psys->filterlabel[FNUM_U], FNAME_U   );

  // all done

  //sprintf(reply, "Filter names updated - F1=%s F2=%s F3=%s F4=%s", 
  //                fname[0], fname[1], fname[2], fname[3]);

  sprintf(reply, "Filter names updated - F1=%s F2=%s F3=%s F4=%s", 
                  psys->filterlabel[FNUM_1], psys->filterlabel[FNUM_2], 
                  psys->filterlabel[FNUM_3], psys->filterlabel[FNUM_4]);  // v0.9.4

  //// update flags and monitoring count

  if( !psys->flag_auxconnected ) {
    psys->flag_auxconnected = 1;
    psys->checknum_auxdata = psys->checknum_tcsdata-TCS_DATAUP_INTERVAL*1/3;    // zero point setting at AUX connection as well, added at v0.4.0
    GRNTEXT;sprintf(cmsg, "STATUS: TCS Agent is connected with AUX Ctrl.\n");_msgout(cmsg);
  }

  psys->flag_auxdata_requested = 0;
  psys->flag_auxdata_updated = 1;
  psys->checknum_auxdisconnected = 0;

  psys->flag_filterlabel_requested = 0;

  return 0;
}

//------------------------------------------------------------------------------
//
// obssys.UpdateDomeStatus - Update Dome status from Web relay & Redis server (v0.9.4)
//
// return 0 on success, -1 on errors
//
// Func: update dome status in TCS/AUX data and dome data for SYS.STATUS
// Parameters: 
//   (TCS.Redis) redis_domerot('dome_error' in newTCS Redis) = 0: positioned(green) / 2: rotating(orange) / 3: stowing or halted(red) / -1: Unknown
//   (TCS.Redis) redis domeshut('SHUTTER' in newTCS Redis) = 1: positioned(green) / 0: near position(yellow) / -1: far position or open/closing(red) / -2: Unknown
//   (TCS.Relay) relay_dctrl_state_drot(dome rotation activity in WebRelay) =  0: Idle / 1: Left / 2: Right / 3: Both / -1: Unknown (modified at v0.9.7)
//   (AUX.STATUS) aux_domeshut(DS:STATUS) = AUX_STATUS_NC/AUX_STATUS_STANDBY/AUX_STATUS_RUNNING/AUX_STATUS_ERROR/AUX_STATUS_UNKNOWN
//   (SYS.STATUS) domerot(dome rotation status for ProcOsc() & RemHost) = 0: Idle / 1: Rotating / -1: Unknown
//   (SYS.STATUS) domeshut(dome shutter status for ProcOsc() & RemHost) = 0: Idle / 1: Moving / -1: Unknown
// Notes: 
//   This function is called in GetSysStatus(), which is called periodically(1s), 
//   whether OSC is running or not. If running, called just before ProcOsc().
//   GetSysStatus() is called in main() after UpdateTcsData()/UpdateAuxData().
//

int
UpdateDomeStatus(obssystem_t *psys, char *reply)
{
  int rtn;
  char strBuf[256];
  char strVal[16];

  static int all_not_available = 0;
  static int prev_cam_status = CAMSTATUS_CHECK;

  //// get dome rotation status from redis('dome_error' key)

  if( psys->redis_failnum_domerot>=0 ) {

    rtn = cmd_redisget("dome_error", EXEC, strBuf);

    if( rtn!=CMD_OK ) {
      psys->redis_failnum_domerot++;
      psys->redis_domerot = REDIS_DOMEROT_UNKNOWN;
      sprintf(cmsg, "Warning: Failed to get dome rotation status from redis - %s !\n", strBuf);
      CYATEXT;_msgout(cmsg);
    }
    else if( !strcmp(strBuf,"dome_error=(nil)") ) {
      psys->redis_failnum_domerot++;
      psys->redis_domerot = REDIS_DOMEROT_UNKNOWN;
      strcpy(cmsg, "Warning: Failed to get dome rotation status from redis - no 'dome_error' key in the redis !\n");
      CYATEXT;_msgout(cmsg);
    }
    else if( !strcmp(strBuf,"dome_error=(nan)") ) {   // statement to check nan is inserted for more exact status importing although 
      psys->redis_failnum_domerot++;                  // actually not necessary for ProcOsc() as REDIS_DOMEROT_IDLE=0 in redis_domerot setting
      psys->redis_domerot = REDIS_DOMEROT_UNKNOWN;
      strcpy(cmsg, "Warning: Failed to get dome rotation status from redis - 'dome_error' value is not a number !\n");
      CYATEXT;_msgout(cmsg);
    }
    else {
      psys->redis_failnum_domerot = 0;
      sscanf(strBuf, "%*[^=]%*[=]%s", strVal);
      psys->redis_domerot = atoi(strVal);    // if "(nil)", return 0      
    }

    if( psys->redis_failnum_domerot>=DEFAULT_REDIS_ERRTH_DOMEROT ) {
      psys->redis_failnum_domerot = -1;   // to restore this, need to command 'rget SHUTTER' and succes it
      strcpy(cmsg, "Warning: Redis dome rotation check DISABLED !!\n");
      MAGTEXT;_msgout(cmsg);
    }

  }

  //// get dome shutter status from redis('SHUTTER' key)

  if( psys->redis_failnum_domeshut>=0 ) {

    rtn = cmd_redisget("SHUTTER", EXEC, strBuf);

    if( rtn!=CMD_OK ) {
      psys->redis_failnum_domeshut++;
      psys->redis_domeshut = REDIS_DOMESHUT_UNKNOWN;
      sprintf(cmsg, "Warning: Failed to get dome shutter status from redis - %s !\n", strBuf);
      CYATEXT;_msgout(cmsg);
    }
    else if( !strcmp(strBuf,"SHUTTER=(nil)") ) {
      psys->redis_failnum_domeshut++;
      psys->redis_domeshut = REDIS_DOMESHUT_UNKNOWN;
      strcpy(cmsg, "Warning: Failed to get dome shutter status from redis - no 'SHUTTER' key in redis !\n");
      CYATEXT;_msgout(cmsg);
    }
    else if( !strcmp(strBuf,"SHUTTER=(nan)") ) {
      psys->redis_failnum_domeshut++;
      psys->redis_domeshut = REDIS_DOMESHUT_UNKNOWN;
      strcpy(cmsg, "Warning: Failed to get dome shutter status from redis - 'SHUTTER' value is not a number !\n");
      CYATEXT;_msgout(cmsg);
    }
    else {
      psys->redis_failnum_domeshut = 0;
      sscanf(strBuf, "%*[^=]%*[=]%s", strVal);
      psys->redis_domeshut = atoi(strVal);    // if "(nil)", return 0
    }

    if( psys->redis_failnum_domeshut>=DEFAULT_REDIS_ERRTH_DOMESHUT ) {
        psys->redis_failnum_domeshut = -1;  // to restore this, need to command 'rget SHUTTER' and succes it
        strcpy(cmsg, "Warning: Redis dome shutter check DISABLED !!\n");
        MAGTEXT;_msgout(cmsg);
    }

  }

  //// get dome rotation status from web relay dctrl

  //
  // Note: psys->relay_dctrl_state_drot is set in cmd_drot(), and 
  //       psys->relay_dctrl_failnum can be reset by command 'drot' 
  //       since it set to 0 when no error in cmd_drot()
  //

  if( psys->relay_dctrl_failnum>=0 ) {

    rtn = cmd_drot(NULL, EXEC, strBuf);

    if( rtn!=CMD_OK ) {
      psys->relay_dctrl_failnum++;
      //psys->relay_dctrl_state_drot = RELAY_DROT_UNKNOWN;   <-- already done in cmd_drot()
      sprintf(cmsg, "Warning: Failed to get dome rotation status from dctrl relay - %s !\n", strBuf);
      CYATEXT;_msgout(cmsg);
    }
    else {
      //psys->relay_dctrl_failnum = 0;
      //sscanf(strBuf, "%*[^=]%*[=]%s", strVal);
      //if( !strcmp(strVal,"IDLE") ) psys->relay_dctrl_state_drot = RELAY_DROT_IDLE;
      //else if( !strcmp(strVal,"LEFT") ) psys->relay_dctrl_state_drot = RELAY_DROT_LEFT;
      //else if( !strcmp(strVal,"RIGHT") ) psys->relay_dctrl_state_drot = RELAY_DROT_RIGHT;
      //else if( !strcmp(strVal,"BOTH") ) psys->relay_dctrl_state_drot = RELAY_DROT_BOTH;
      //else psys->relay_dctrl_state_drot = RELAY_DROT_UNKNOWN;
      ////// already done all in cmd_drot()      
    }

    if( psys->relay_dctrl_failnum>=DEFAULT_RELAY_ERRTH_DCTRL ) {
      psys->relay_dctrl_failnum = -1;  // to reset this, need to command 'drot' and success it
      strcpy(cmsg, "Warning: Relay dome rotation check DISABLED !!\n");
      MAGTEXT;_msgout(cmsg);
    }

  }

  //// update dome status for SYS.STATUS and ProcOsc()

  //if( psys->redis_domerot==REDIS_DOMEROT_ROTATING || psys->relay_dctrl_state_drot!=RELAY_DROT_IDLE ) {
  if( psys->redis_domerot==REDIS_DOMEROT_ROTATING || psys->relay_dctrl_state_drot>RELAY_DROT_IDLE ) {  // v0.9.9
    psys->domerot = DOME_ROTATING;
  }
  else {
    psys->domerot = DOME_IDLE;
  }

  //if( psys->redis_domeshut==REDIS_DOMESHUT_MOVING || psys->aux_domeshut==AUX_STATUS_RUNNING ) {
  if( psys->redis_domeshut==REDIS_DOMESHUT_FARPOS || psys->aux_domeshut==AUX_STATUS_RUNNING ) {  // v0.9.9
    psys->domeshut = DOME_MOVING;
  }
  else {
    psys->domeshut= DOME_IDLE;
  }

  //// Warning in case all the parameters not available

  if( psys->redis_failnum_domerot<0 && psys->redis_failnum_domeshut<0 && psys->relay_dctrl_failnum<0 && 
      psys->aux_domeshut!=AUX_STATUS_STANDBY && psys->aux_domeshut!=AUX_STATUS_RUNNING ) {
      all_not_available++;
      strcpy(cmsg, "WARNING: Dome status monitoring is not available at all !!\n");
      if( all_not_available<10 && all_not_available%3==0 ) { REDTEXT;_msgout(cmsg); }
      if( osc.flag_process && psys->camstatus==CAMSTATUS_PREP_I && psys->camstatus!=prev_cam_status ) { REDTEXT;_msgout(cmsg); }
  }
  else {
      all_not_available = 0;
      sprintf(cmsg, "DOME.STATUS: RedisDomeRot=%-2d RelayDomeRot=%-2d RedisDomeShut=%-2d AuxDomeShut=%-2d\n", 
          psys->redis_domerot, psys->relay_dctrl_state_drot, psys->redis_domeshut, psys->aux_domeshut);
      _dbgmsgout(cmsg);
  }

  prev_cam_status = psys->camstatus;

  //// All done

  if(reply!=NULL) {
    sprintf(reply, "RedisDomeRot=%d RelayDomeRot=%d RedisDomeShut=%d AuxDomeShut=%d DomeStatusUpdate=%s", 
        psys->redis_domerot, psys->relay_dctrl_state_drot, psys->redis_domeshut, psys->aux_domeshut, all_not_available?"NO":"YES");
  }

  return 0;
}

//------------------------------------------------------------------------------
//
// obsstatus.WriteObsStatus - write observation status file (SYS.STATUS/EXP.INFO/OBS.Script) (v1.0.3-v1.0.4)
//

int
WriteObsStatus(const char *strObsStat)
{
  int i, nLineIdx, nTemp;
  FILE *pfObsStat;
  pfObsStat = fopen(strObsStat, "wt");
  if(pfObsStat==NULL) return -1;

  //// 
  //// set system status value/strings
  //// 

  char strCamStatus[16];
  char strTelStatus[16];
  char strTcsMove  [16];
  char strTcsLimit [16];
  char strTcsDrive [16];
  char strDomeRota [16];
  char strDomeShut [16];
  char strTilt     [16];

  //// update camera status label

  switch (sys.camstatus) {
    case CAMSTATUS_NC      : strcpy(strCamStatus, "NC"      ); break;
    case CAMSTATUS_PREP_I  : strcpy(strCamStatus, "PREP_I"  ); break;
    case CAMSTATUS_PREP_E  : strcpy(strCamStatus, "PREP_E"  ); break;
    case CAMSTATUS_INT_1   : strcpy(strCamStatus, "INT_1"   ); break;
    case CAMSTATUS_INT_2   : strcpy(strCamStatus, "INT_2"   ); break;
    case CAMSTATUS_INT_3   : strcpy(strCamStatus, "INT_3"   ); break;
    case CAMSTATUS_CLOSING : strcpy(strCamStatus, "CLOSING" ); break;
    case CAMSTATUS_READ_1  : strcpy(strCamStatus, "READ_1"  ); break;
    case CAMSTATUS_READ_2  : strcpy(strCamStatus, "READ_2"  ); break;
    case CAMSTATUS_READ_3  : strcpy(strCamStatus, "READ_3"  ); break;
    case CAMSTATUS_IDLE_1  : strcpy(strCamStatus, "IDLE_1"  ); break;
    case CAMSTATUS_IDLE_2  : strcpy(strCamStatus, "IDLE_2"  ); break;
    case CAMSTATUS_IDLE_3  : strcpy(strCamStatus, "IDLE_3"  ); break;
    case CAMSTATUS_READY   : strcpy(strCamStatus, "READY"   ); break;
    case CAMSTATUS_CHECK   : strcpy(strCamStatus, "CHECK"   ); break;
    case CAMSTATUS_CRASHED : strcpy(strCamStatus, "CRASHED" ); break;
    case CAMSTATUS_DEAD    : strcpy(strCamStatus, "DEAD"    ); break;
    default                : strcpy(strCamStatus, "UNKNOWN" ); break;
  }

  //// update telescope status label

  switch (sys.telstatus) {
    case TELSTATUS_NC       : strcpy(strTelStatus, "NC"       ); break;
    case TELSTATUS_CHECKING : strcpy(strTelStatus, "CHECKING" ); break;
    case TELSTATUS_STOW     : strcpy(strTelStatus, "STOW"     ); break;
    case TELSTATUS_HOLDING  : strcpy(strTelStatus, "HOLDING"  ); break;
    case TELSTATUS_TRACKING : strcpy(strTelStatus, "TRACKING" ); break;
    case TELSTATUS_TRACKINGS: strcpy(strTelStatus, "TRACKINGS"); break;
    case TELSTATUS_SLEW     : strcpy(strTelStatus, "SLEW"     ); break;
    case TELSTATUS_SETTLING : strcpy(strTelStatus, "SETTLING" ); break;
    case TELSTATUS_OSCILLATE: strcpy(strTelStatus, "OSCILLATE"); break;
    case TELSTATUS_DISABLED : strcpy(strTelStatus, "DISABLED" ); break;
    default                 : strcpy(strTelStatus, "UNKNOWN"  ); break;
  }

  //// update TCS moving status labels

  switch (sys.movestatus) {
    case 0: strcpy(strTcsMove,"IDLE   ");break;
    case 1: strcpy(strTcsMove,"RA     ");break;
    case 2: strcpy(strTcsMove,"DEC    ");break;
    case 3: strcpy(strTcsMove,"RA+DEC ");break;
   default: strcpy(strTcsMove,"UNKNOWN");break;
  }

  //// update TCS limits status labels

  switch (sys.limitstatus) {
    case 0: strcpy(strTcsLimit,"NO       ");break;
    case 1: strcpy(strTcsLimit,"RA       ");break;
    case 2: strcpy(strTcsLimit,"DEC      ");break;
    case 3: strcpy(strTcsLimit,"RA+DEC   ");break;
    case 4: strcpy(strTcsLimit,"ELEVATION");break;
    case 5: strcpy(strTcsLimit,"RA+EL    ");break;
    case 6: strcpy(strTcsLimit,"DEC+EL   ");break;
    case 7: strcpy(strTcsLimit,"RA+DEC+EL");break;
   default: strcpy(strTcsLimit,"UNKNOWN  ");break;
  }

  //// update TCS drive enable/disable status labels

  switch (sys.drivedisable) {
    case 0: strcpy(strTcsDrive,"ENABLED ");break;
    case 1: strcpy(strTcsDrive,"DISABLED");break;
   default: strcpy(strTcsDrive,"UNKNOWN ");break;
  }

  //// update exposure time remaining

  if( sys.flag_expcount ) {
    sys.exp_remaining = sys.exp_set - ( SysTimestamp() - sys.exp_starttime );
    sys.exp_remaining = MAX( sys.exp_remaining, 0.0 );
  }

  //// update dome status labels

  switch (sys.domerot) {
    case DOME_IDLE    : strcpy(strDomeRota,"IDLE    ");break;
    case DOME_ROTATING: strcpy(strDomeRota,"ROTATING");break;
    case DOME_UNKNOWN : strcpy(strDomeRota,"UNKNOWN ");break;
    default           : strcpy(strDomeRota,"UNKNOWN ");break;
  }

  switch (sys.domeshut) {
    case DOME_IDLE   : strcpy(strDomeShut,"IDLE   ");break;
    case DOME_MOVING : strcpy(strDomeShut,"MOVING ");break;
    case DOME_UNKNOWN: strcpy(strDomeShut,"UNKNOWN");break;
    default          : strcpy(strDomeShut,"UNKNOWN");break;
  }

  //// set Tilt string

  sprintf(strTilt, "%+.0f,%+.0f", sys.tns, sys.tew);

  //// 
  //// set exposure status value/strings
  //// 

  switch(expinfo.nStatus) {
    case EXPSTATUS_CHECK   : strcpy(expinfo.strStatus, "CHECK   "); break;
    case EXPSTATUS_STANDBY : strcpy(expinfo.strStatus, "STANDBY "); break;
    case EXPSTATUS_CMDED   : strcpy(expinfo.strStatus, "CMDED   "); break;
    case EXPSTATUS_WAITING : strcpy(expinfo.strStatus, "WAITING "); break;
    case EXPSTATUS_FLUSH   : strcpy(expinfo.strStatus, "FLUSH   "); break;
    case EXPSTATUS_EXPOSURE: strcpy(expinfo.strStatus, "EXPOSURE"); break;
    case EXPSTATUS_READOUT : strcpy(expinfo.strStatus, "READOUT "); break;
    case EXPSTATUS_FINISH  : strcpy(expinfo.strStatus, "FINISH  "); break;
    case EXPSTATUS_ERROR   : strcpy(expinfo.strStatus, "ERROR   "); break;
    default                : strcpy(expinfo.strStatus, "UNKNOWN "); break;
  }

       if(expinfo.nStatus<EXPSTATUS_EXPOSURE) expinfo.dElapsed = 0.0;
  else if(expinfo.nStatus>EXPSTATUS_EXPOSURE) expinfo.dElapsed = expinfo.dSetting;
  else expinfo.dElapsed = MIN( (SysTimestamp()-expinfo.dStartTime), expinfo.dSetting );
  sprintf(expinfo.strExpProg, "%d/%d", (int)expinfo.dElapsed, (int)expinfo.dSetting);

  //// 
  //// output ObsStatus.txt
  //// 

  fprintf(pfObsStat, "OBSERVATION STATUS\n");
  fprintf(pfObsStat, "\n");
  fprintf(pfObsStat, "Updated=%s\n", GetUTCDateTime(NULL));
  fprintf(pfObsStat, "\n");
  fprintf(pfObsStat, "CamStatus=%-7s\n", strCamStatus);
  fprintf(pfObsStat, "FitsSaved=%-2d\n", sys.status_fitssaved);
  fprintf(pfObsStat, "ExpSet=%-4.0f\n", sys.exp_set);
  fprintf(pfObsStat, "ExpRem=%-4.0f\n", sys.exp_remaining);
  fprintf(pfObsStat, "\n");
  fprintf(pfObsStat, "TelStatus=%-11s\n", strTelStatus);
  fprintf(pfObsStat, "RA=%s\n", sys.ra);
  fprintf(pfObsStat, "DEC=%-11s\n", sys.dec);
  fprintf(pfObsStat, "HA=%-9s\n", sys.ha);
  fprintf(pfObsStat, "SecZ=%-4.2f\n", sys.secz);
  fprintf(pfObsStat, "Alt=%-4.1f\n", sys.alt_d);
  fprintf(pfObsStat, "Az=%-+6.1f\n", sys.az_d);
  fprintf(pfObsStat, "Move=%s\n", strTcsMove);
  fprintf(pfObsStat, "Limit=%s\n", strTcsLimit);
  fprintf(pfObsStat, "Drive=%s\n", strTcsDrive);
  fprintf(pfObsStat, "\n");
  fprintf(pfObsStat, "TELID=%-8s\n", sys.telid);
  fprintf(pfObsStat, "FILTSTAT=%-7s\n", sys.filteropstat);
  fprintf(pfObsStat, "FILTER=%-7s\n", sys.filtername);
  fprintf(pfObsStat, "ACTFILT=%-7s\n", sys.filterlabel[sys.filternum]);
  fprintf(pfObsStat, "SHUTSTAT=%-9s\n", sys.shutopstat);
  fprintf(pfObsStat, "SHUTTER=%-7s\n", sys.shutstatus);
  fprintf(pfObsStat, "FOCUS=%-+7.3f\n", sys.focus);
  fprintf(pfObsStat, "TILT=%-12s\n", strTilt);
  fprintf(pfObsStat, "SENS=%+05.1f,%+05.1f,%+05.1f,%05.1f,%+05.1f,%+05.1f,%+05.1f\n", 
          sys.ens[0], sys.ens[1], sys.ens[2], sys.ens[3], sys.ens[4], sys.ens[5], sys.ens[6]);
  fprintf(pfObsStat, "FAN=%-3s\n", sys.fan);
  fprintf(pfObsStat, "DomeRot=%s\n", strDomeRota);
  fprintf(pfObsStat, "DomeShut=%s\n", strDomeShut);
  fprintf(pfObsStat, "\n");
  fprintf(pfObsStat, "OscStatus=%-8s\n", osc.flag_paused?"PAUSED":(osc.flag_running?"RUNNING":"IDLE"));
  fprintf(pfObsStat, "LINE#=%04d/%04d\n", osc.lineidx, osc.linenum);
  fprintf(pfObsStat, "CMD#=%04d/%04d\n", osc.cmdidx, osc.cmdnum);
  fprintf(pfObsStat, "EXP#=%04d/%04d\n", osc.expidx, osc.expnum);
  fprintf(pfObsStat, "\n");
  fprintf(pfObsStat, "ExpStatus=%s\n", expinfo.strStatus);
  fprintf(pfObsStat, "ExpNum=%s\n", expinfo.strCurNum);
  fprintf(pfObsStat, "ExpStart=%s\n", expinfo.strExpStart);
  fprintf(pfObsStat, "ExpProg=%-9s\n", expinfo.strExpProg);
  fprintf(pfObsStat, "FitsNum=%s\n", expinfo.strFitsNum);
  fprintf(pfObsStat, "FitsOsc=%-5s\n", expinfo.strFitsOsc);   // v1.0.9
  fprintf(pfObsStat, "\n");

  nLineIdx = osc.lineidx;
  for(i=0;i<6;i++) {
    if( osc.lineidx==0 ) strcpy(cmsg, "--RESERVED"); 
    else if( nLineIdx<0 ) strcpy(cmsg, "--WRONGIDX");
    else if( nLineIdx>osc.linenum ) strcpy(cmsg, "--COMPLETE");
    else {
      if( osc.line[nLineIdx-1].type==OSC_TYPE_CMD && !strcmp(osc.line[nLineIdx-1].cmd, "ostart") ) {
          nLineIdx = atoi(osc.line[nLineIdx-1].arg);
      }
      if( GetOscLine(nLineIdx, 1, NULL, cmsg)<0 ) strcpy(cmsg, "--INVALID");
    }
    fprintf(pfObsStat, "[%d]%-255s\n", i, cmsg);   // OSC_MAXLINELEN==OSC_MAXEXPLEN==OSC_MAXMSGLEN==256==(ProjId 16 + Label 64 + Object 32 + .. + NUL), modified in v1.0.5
    nLineIdx++;
  }

  fprintf(pfObsStat, "%-5s\n", " ");
  fprintf(pfObsStat, "EOF");

  fclose(pfObsStat);
  return 0;
}


//------------------------------------------------------------------------------
//------------------------------------------------------------------------------
//
// Utility functions
//

//
// *** GENERIC UTILITY FUNCTIONS BEGIN HERE ***
//

//------------------------------------------------------------------------------
//
// utility.StopWatch - measure the time from START to STOP
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
// utility.GetUTCTime() - read the system's UTC time clock and return the
//                        fine-grained time to msec precision
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
//

char *
GetUTCTime(void)
{
  struct timeval tv;
  static char str[16];
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
// utility.GetUTCDateTime() - read the system's UTC time clock and return the
//                            fine-grained time to msec precision
//
// Return: 
//   - smctime_t (centime
//   - string yyyy-mm-ddThh:mm:ss.sss
//

char *
GetUTCDateTime(smctime_t *datime)
{
  struct timeval tv;
  static char str[32];
  struct tm *gmt;
  int ms;
  smctime_t systime;

  gettimeofday(&tv,NULL);
  gmt = gmtime(&tv.tv_sec);
  ms = (int)(tv.tv_usec/1000);

  systime.secse = (UINT)tv.tv_sec;

  systime.year  = gmt->tm_year + 1900;
  systime.month = (gmt->tm_mon)+1;
  systime.day   = gmt->tm_mday;

  systime.hour  = gmt->tm_hour;
  systime.min   = gmt->tm_min;
  systime.sec   = (double)(gmt->tm_sec) + ((double)(ms)/1000.0);

  sprintf(str, "%04d-%02d-%02dT%02d:%02d:%02d.%03d",
                systime.year, systime.month, systime.day,
                systime.hour, systime.min, 
                //(int)systime.sec, (int)(systime.sec*1000.)%1000 );
                  (int)systime.sec, ms );  // v0.4.0

  if(datime!=NULL) memcpy(datime, &systime, sizeof(smctime_t));

  return(str);
}

//------------------------------------------------------------------------------
//
// utility.strupr() - return string replaced with uppercase
//

char *
strupr(const char *s) 
{
  static char buf[STRLEN_CMD];
  char *p = buf;

  do *p++ = ( 0x60<*s && *s<0x7B ) ? *s-0x20 : *s;
  while(*s++);

  return buf;
}

//------------------------------------------------------------------------------
//
// utility._msgout()/_vmsgout()/_dbgmsgout()/_eventlog()/_debuglog()
//    - console message output on console and event/debugg log file 
//      and script observation result output on scrobs log file
//

void _msgout(char *msg)
{

  if( agent.isTimeTag && !agent.isBlockTimeTag ) {    // v0.0.5
    printf("\r[%s] %s", GetUTCDateTime(NULL), msg);
  }
  else {
    printf("\r%s", msg);
  }

  TXTRESET;
  if( !KeyCmdFlag ) rl_refresh_line(0,0);

  //if( client.doLogging ) {  // v0.2.5
  // --> do unconditionally 
  //     because we have another filter "if(agent.pLogEvent!=NULL)" in _eventlog()
  //     and we need to log before the client.doLogging flag is ON.
  {  // v0.2.6 and before v0.2.5
    _eventlog(msg);
  }

  if( agent.isDebugLog ) {
    _debuglog(msg);
  }

  memset(msg,0,sizeof(msg));  // if didn't this, previous message is in the buffer, and it is outputted in case no writing msg into reply buffer v0.7.3

}

void _vmsgout(char *msg)
{

  if( client.isVerbose ) {
    if( agent.isTimeTag && !agent.isBlockTimeTag ) {    // v0.0.5
      printf("\r[%s] %s", GetUTCDateTime(NULL), msg);
    }
    else {
      printf("\r%s", msg);
    }
    TXTRESET;
    if( !KeyCmdFlag ) rl_refresh_line(0,0);
  }
  else {
    TXTRESET;
  }

  //if( client.doLogging && agent.isLogVerbose ) {
  // --> do only if the agent.isLogVerbose flag is ON 
  //     because we have another filter "if(agent.pLogEvent!=NULL)" in _eventlog()
  //     and we need to log before the client.doLogging flag is ON.
  if( agent.isLogVerbose ) {  // v0.2.6 and before v0.2.5
    _eventlog(msg);
  }

  if( agent.isDebugLog ) {
    _debuglog(msg);
  }

  memset(msg,0,sizeof(msg));  // if didn't this, previous message is in the buffer, and it is outputted in case no writing msg into reply buffer v0.7.3
}

void _dbgmsgout(char *msg)  // v0.0.8
{

  if( client.Debug ) {
    if( agent.isTimeTag && !agent.isBlockTimeTag ) {
      printf("\r[%s] %s", GetUTCDateTime(NULL), msg);
    }
    else {
      printf("\r%s", msg);
    }
    TXTRESET;
    if( !KeyCmdFlag ) rl_refresh_line(0,0);
  }
  else {
    TXTRESET;
  }

  if( agent.isDebugLog ) {
    _debuglog(msg);
  }

  memset(msg,0,sizeof(msg));  // if didn't this, previous message is in the buffer, and it is outputted in case no writing msg into reply buffer v0.7.3

}

void _eventlog(const char *msg)  // should be called before _msgout()/_vmsgout()/_dbgmsgout()
{
  if(agent.pLogEvent!=NULL) fprintf(agent.pLogEvent, "[%s]  %s", GetUTCDateTime(NULL), msg);
}

void _debuglog(const char *msg)  // should be called before _msgout()/_vmsgout()/_dbgmsgout()
{
  if(agent.pLogDebug!=NULL) fprintf(agent.pLogDebug, "[%s]  %s", GetUTCDateTime(NULL), msg);
}

void _scrobslog(const char *msg)  // should be called before _msgout()/_vmsgout()/_dbgmsgout()
{
  if(agent.pLogScrObs!=NULL) {
    fprintf(agent.pLogScrObs, "[%s]  %s", GetUTCDateTime(NULL), msg);
    fflush(agent.pLogScrObs);   // v0.2.8
  }
}

//
// *** CORRECTION FUNCTIONS BEGIN HERE ***
//

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

#define M_PI 3.14159265358979323846

int offset_blg(double *ra, double *dec, double ha, const char *table)
{
    int i, nn;
    double  ora,odec, HA[NDATA],oRA[NDATA],oDEC[NDATA];
    char field[300];
    FILE *in;

    if( (in=fopen(table,"r")) == NULL) { 
        //puts("File Read Error: No Offset Table");  
        REDTEXT;
        sprintf(cmsg, "WARNING: BLG offset correction -- "
                      "File Read Error: No Offset Table");
        _msgout(cmsg);  // OBSAgent v0.3.2
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
        //printf("Input Data Error: Beyond the Range of Offset Table [%.1lf,%.1f]\n", HA[0], HA[nn-1]);
        REDTEXT;
        sprintf(cmsg, "WARNING: BLG offset correction -- "
                      "Input Data Error: Beyond the Range of Offset Table [%.1lf,%.1f]\n", HA[0], HA[nn-1]);
        _msgout(cmsg);  // OBSAgent v0.3.2
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
//------------------------------------------------------------------------------
//EOF
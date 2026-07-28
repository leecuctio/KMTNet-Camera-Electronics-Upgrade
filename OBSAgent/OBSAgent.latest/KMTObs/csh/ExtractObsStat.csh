#!/bin/csh

# Extract Observation Statatus from DebugLogs

if ( $# < 1 ) then
  echo "Usage: $0  <directory>  <yyyymmdd.hhmmss='*'>"
  echo "Examples:"
  echo "  $0  Logs.CTIO/OBS.ICSci.CTIO.20240713  20240711.220649  > ObsStatExtracted.20240711.2206.log"
# echo "  $0  Logs.CTIO/OBS.ICSci.CTIO.20240713  20240711.*  > ObsStatExtracted.20240711.all.log"
  echo "  $0  Logs.CTIO/OBS.ICSci.CTIO.20240713  > ObsStatExtracted.2024.all.log"
  exit
else if ( $# < 2 ) then
  set LOGDIR = $1
  set LOGNUM = "*"
else
  set LOGDIR = $1
  set LOGNUM = $2
endif

#echo
#echo "Start to extract ObsStatus in OscRunning from DebugLogs.."
#echo "  - Directory: $LOGDIR"
#echo "  - Debuglogs: obs.debug.$LOGNUM.log"
#echo

#  awk ' { idx = index($0,"DOME.STATUS:"); if(idx>0){ domstat = substr($0,idx); }; \
#          idx = index($0,"SYS.STATUS:" ); if(idx>0){ sysstat = substr($0,idx); }; \
#          idx = index($0,"EXP.INFO:"   ); if(idx>0){ expinfo = substr($0,idx); }; \
#          idx = index($0,"OSC.STATUS:" ); if(idx>0){ oscstat = substr($0,idx); }; \
#          if(idx>0){ \
#            if($6=="OpStatus=RUNNING"){  \
#              printf( "%s %s | %s | %s | %s | \n", \
#                       $1, domestat, sysstat, expinfo, oscstat ); \
#            } \
#          } \
#        } ' $LOGDIR/obs.debug.$LOGNUM.log

awk ' { idx = index($0,"DOME.STATUS:"); if(idx>0){ domstat = $0 }; \
        idx = index($0,"SYS.STATUS:" ); if(idx>0){ sysstat = $0 }; \
        idx = index($0,"EXP.INFO:"   ); if(idx>0){ expinfo = $0 }; \
        idx = index($0,"OSC.STATUS:" ); if(idx>0){ oscstat = $0 }; \
        if(idx>0){ \
          if($6=="OpStatus=RUNNING"){  \
            printf( "%s  %s  %s  %s  \n", \
                     domestat, sysstat, expinfo, oscstat ); \
          } \
        } \
      } ' $LOGDIR/obs.debug.$LOGNUM.log

#echo "Done."
#echo

exit


#EOF
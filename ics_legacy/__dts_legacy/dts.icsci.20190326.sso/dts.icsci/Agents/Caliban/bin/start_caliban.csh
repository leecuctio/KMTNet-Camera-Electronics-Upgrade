#!/bin/csh -f
#
# start_cb - wrapper used to invoke the Caliban data-transfer
#            agent in a safe and minimally painful fashion.
#
# usage: start_cb [-finifile]
#
# where: -finifile = use inifile as the runtime config file instead of
#                    the default (used only for engineering)
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.mps.ohio-state.edu
# 2003 January 30 
#
# 2004 Jun 15 - restored /data settings (CBLogs) [rwp/osu]
# 2013 Apr 12 - version for the KMTN testbed [rwp/osu]
#
############################################################################

if ($#argv > 0) then
   setenv CBargs $1
else
   setenv CBargs " "
endif

# Make sure these are explicit (not automount) paths on the 
# local host

setenv CBBin  /home/dts/Agents/Caliban/bin
setenv CBLogs /home/data/Logs/Caliban

# Rotate the logs.  We retain them 9-deep (crudely implemented)

\mv $CBLogs/Caliban.log.8 $CBLogs/Caliban.log.9 >& /dev/null
\mv $CBLogs/Caliban.log.7 $CBLogs/Caliban.log.8 >& /dev/null
\mv $CBLogs/Caliban.log.6 $CBLogs/Caliban.log.7 >& /dev/null
\mv $CBLogs/Caliban.log.5 $CBLogs/Caliban.log.6 >& /dev/null
\mv $CBLogs/Caliban.log.4 $CBLogs/Caliban.log.5 >& /dev/null
\mv $CBLogs/Caliban.log.3 $CBLogs/Caliban.log.4 >& /dev/null
\mv $CBLogs/Caliban.log.2 $CBLogs/Caliban.log.3 >& /dev/null
\mv $CBLogs/Caliban.log.1 $CBLogs/Caliban.log.2 >& /dev/null
\mv $CBLogs/Caliban.log   $CBLogs/Caliban.log.1 >& /dev/null

# Launch caliban *in this window*

echo "]2;Caliban Command Window"

${CBBin}/caliban ${CBargs} 


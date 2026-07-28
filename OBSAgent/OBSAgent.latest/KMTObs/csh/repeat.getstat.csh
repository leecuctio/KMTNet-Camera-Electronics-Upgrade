#!/bin/csh

## repeat.initobs.csh v0.0

if ( $# != 1 ) then
    echo 'Usage $0 <interval(sec)>'
    exit 1
endif

set CMD_NC =  'nc -w1 -u 127.0.0.1 6650'
set CMD_01 =  'echo CHA>OBS ss'
set CMD_02 =  'echo CHA>OBS os'


set n = 0

while(1)

    set now = `date +%Y-%m-%dT%H:%M:%S`


    if ( $n % 4 == 0 ) then
       set fan = '/'
    else if ( $n % 4 == 1 ) then
       set fan = '-'
    else if ( $n % 4 == 2 ) then
       set fan = \\
    else if ( $n % 4 == 3 ) then
       set fan = '|'
    endif

    echo
    echo ________________________________________________________________________________
    echo "$CMD_01 | $CMD_NC"
    echo

    $CMD_01 | $CMD_NC

    echo    
    echo ________________________________________________________________________________
    echo "$CMD_02 | $CMD_NC"
    echo

    $CMD_02 | $CMD_NC

    echo
    echo "                                       -- Current time:" ${now} ${fan}
    echo "                                       -- Press Ctrl+C to stop process.."

    sleep $1

    @ n = $n + 1
end



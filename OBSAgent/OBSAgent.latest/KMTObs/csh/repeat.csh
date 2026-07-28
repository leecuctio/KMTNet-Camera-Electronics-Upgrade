#!/bin/csh -f

## repeat.csh v0.0

if ( $# != 2 ) then
    echo 'Usage $0 "<command line>" <interval(sec)>'
    exit 1
endif

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

    echo ________________________________________________________________________________
    echo "$1"
    echo

    $1
    
    echo
    echo "                                       -- Current time:" ${now} ${fan}
    echo "                                       -- Press Ctrl+C to stop process.."

    sleep $2

    @ n = $n + 1
end



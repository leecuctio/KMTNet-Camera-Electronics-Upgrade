#!/bin/csh

# Stack Observation Status file - v1.0 - 20240710

if ( $# < 1 ) then
    set INTERVAL = 5
else if ( $1 < 1 ) then
    echo "Usage: $0 <interval_sec=5>"
    exit
endif

echo
echo "Start to stack ObsStatus.."
echo

set DIR_STACK = .
set PORT = 22
set ID = kasi

if( -e ~/camera/CTIO ) then
    set SITE = CTIO
    set PATH = 192.168.14.109:/data/Logs/ObsStatus.txt
    set WORD = "kasimain"
else if( -e ~/camera/SAAO ) then
    set SITE = SAAO
    set PATH = 192.168.13.109:/data/Logs/ObsStatus.txt
    set WORD = "kasimain"
else if( -e ~/camera/SSO ) then
    set SITE = SSO
    set PATH = 192.168.15.109:/data/Logs/ObsStatus.txt
    set WORD = '#wndfurfpswm@SS0\!$'
else if( -e ~/camera/KASI ) then
    set SITE = KASI
    set PATH = 210.98.54.10:~/camera/Logs/ObsStatus.txt
    set WORD = 'kmtnet'
    set PORT = 7774
    set ID = kmtnet
else
    echo "    Error: No site ID in the directory.\n\n"
    exit
endif 

echo "Interval = $INTERVAL"
echo "Site = $SITE"
echo

set n = 0

while(1)

    sshpass -p $WORD scp -P$PORT $ID@$PATH $DIR_STACK/

    set timetag = ` awk ' NR==3 { printf( "%s%s%s.%s%s%s", \
                    substr($1, 9,4), substr($1,14,2), substr($1,17,2), \
                    substr($1,20,2), substr($1,23,2), substr($1,26,2) ) \
                    } ' $DIR_STACK/ObsStatus.txt `

    set filename = ObsStatus.$SITE.$timetag.txt

    \mv -f $DIR_STACK/ObsStatus.txt $DIR_STACK/$filename

    sshpass -p kmtnet scp $filename kmtnet@210.98.54.10:/KMTNet_Raw/IC_LOGS/StackObsStat/StackObsStat.$SITE

    echo "$filename copied"

    sleep $INTERVAL

end


exit


#EOF
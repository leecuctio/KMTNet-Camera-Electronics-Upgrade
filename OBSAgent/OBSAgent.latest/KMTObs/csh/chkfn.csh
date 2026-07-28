#!/bin/csh

cd ~/Logs/StackObsStat

# Print the number of files in StackObsStat.CTIO/SAAO/SSO - R20240712

if ( $# < 1 ) then
    set INTERVAL = 5
else if ( $1 < 1 ) then
    echo "Usage: $0 <interval_sec=5>"
    exit
endif

echo "Start to print file numbers.."
echo "Interval = $INTERVAL"

while(1)

    set FNCL = `ls StackObsStat.CTIO | wc -l`
    set FNSA = `ls StackObsStat.SAAO | wc -l`
    set FNAU = `ls StackObsStat.SSO  | wc -l`
    printf "    CTIO %5d      SAAO %5d       SSO %5d\n" $FNCL $FNSA $FNAU

    sleep $INTERVAL

end


exit


#EOF

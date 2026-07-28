#!/bin/bash

if [ $# -lt 3 ]; then
    echo "command : retarget.sh [Original TargetName] [Replace TargetName] [Filename] ([Filter])"
    exit 1
fi

if [ ! -f $3 ]; then
    echo "No such file : $3"
    exit 1
fi

if [ $# -eq 4 ]; then
    sear="$1.$4"
else 
    sear=$1
fi

r=$(awk -v target=$2 '$0 ~ target && !seen[$7]++  {print $3}' $3)
d=$(awk -v target=$2 '$0 ~ target && !seen[$7]++  {print $4}' $3)
awk -v ra=$r -v dec=$d -v ta=$1 -v se=$sear -v re=$2 '{if($0 ~ se) { gsub(ta, re); $3 = ra; $4 = dec; printf("%-11s %-13s %10s %11s %4s %8s %12s %6s %7s %19s %5s %-9s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12); i++} else {print}}' $3 > ret.tmp
mv ret.tmp $3
#!/bin/bash

if [ $# -ne 3 ]; then
    echo "command : retarget.sh [Original TargetName] [Reaplce TargetName] [filename]"
    exit 1
fi

if [ ! -f $3 ]; then
    echo "No such file : $3"
    exit 1
fi

r=$(awk -v target=$2 '$0 ~ target && !seen[$7]++  {print $3}' $3)
d=$(awk -v target=$2 '$0 ~ target && !seen[$7]++  {print $4}' $3)
awk -i inplace -v ra=$r -v dec=$d -v re=$1 -v ta=$2 'BEGIN{i=9001;} {if($0 ~ re) { gsub(/,-?[0-9]+/,","i,$2); gsub(re, ta); $3 = ra; $4 = dec; printf("%-11s %-13s %11s %11s %4s %8s %12s %6s %7s %19s %5s %-9s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12); i++} else {print}}' $3 

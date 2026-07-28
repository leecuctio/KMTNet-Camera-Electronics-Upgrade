#!/bin/csh -f

## update filter name of OBSAgent on local machine

echo "CHA>OBS ping"
echo "CHA>OBS ping" | nc -w1 -u 127.0.0.1 6650

echo "CHA>OBS filname"
echo "CHA>OBS filname F1=I F2=R F3=V F4=B" | nc -w1 -u 127.0.0.1 6650

echo "done."

exit

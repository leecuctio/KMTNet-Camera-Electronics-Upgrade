#!/bin/bash

## Reference
##
## #-- Start the Flat utilities
## xterm -T "FLAT EXPTIME CAL"  -geometry 74x18-0+0 -e "/home/kasi/flatcal/flat-cl" &
## gnome-terminal -e "/home/kasi/flatcal/cal_flat.py" -t "FLAT POSITION CAL" --geometry=34x9-0+293 &
##
## #gnome-terminal -t "FLAT EXPTIME CAL" --geometry=74x18-0+0 -e "/home/kasi/flatcal/flat-cl" &
## #gnome-terminal -e "/home/kasi/flatcal/cal_flat.py" -t "FLAT POSITION CAL" --geometry=34x9-0+388 &
## 


DIR="/home/chasm/camera/OBSAgent"

#xterm -T "OBSAgent"  -fn fixed  -geometry 108x56-0+0  -e "cd $DIR/dflat"  -p  &
#exit

 cd $DIR                ; xterm -T "OBSAgent"         -fn fixed  -geometry 108x56+0000+0001  &
 cd $DIR                ; xterm -T "OBSAgnet"         -fn fixed  -geometry 108x25+0000+0764  &
 cd $DIR/KMTObs         ; xterm -T "OBSAgent/KMTObs"  -fn fixed  -geometry 108x56+0668+0001  &
 cd $DIR/KMTObs         ; xterm -T "OBSAgent/KMTObs"  -fn fixed  -geometry 108x25+0668+0764  &
 cd $DIR/KMTObs         ; xterm -T "OBSAgent run"     -fn fixed  -geometry 240x40+1336+0001  &

 cd $DIR/KMTObs         ; xterm -T "Init. OBSAgent.." -fn fixed  -geometry 080x13+1336+0556  \
                                -e "csh/repeat.initobs.csh 3" &


#EOF

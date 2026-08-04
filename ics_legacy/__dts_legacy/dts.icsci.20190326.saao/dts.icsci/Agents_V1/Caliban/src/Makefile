#
# Caliban v3.1 Makefile
#
# use "build" to do a full package build
# use "make install" to install the public binaries
#
# This is a distribution version for the OSIRIS system
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# 2003 January 20
#
# Last Mod: 
#  2007 Jul 21 - added REQ SWAP ACK handling and retries [rwp/osu]
#
CC          = /usr/bin/g++
AR          = /usr/bin/ar

# Version number: <major>.<minor>.<build>

CFLAGS	    = -w -c -DLINUX -DVERSION='"Caliban v3.6.1"' \
              -DCOMPDATE='"$(COMPDATE)"' -DCOMPTIME='"$(COMPTIME)"'
LFLAGS      = -o caliban
CBLIBS      = -lreadline -lhistory -lncurses
CBHOME	    = /lhome/dts/Agents/Caliban

OFILES      = XmitMsg.o AckDisk.o InitDisk.o InitDiskTable.o InitSerial.o \
              IsValidMount.o LogMsg.o ConsoleMsg.o Pong.o Status.o \
              TransferDisk.o UseDisk.o UseMount.o Utils.o ParseIniFile.o \
              GetFITS.o ReqMount.o Ping.o CBStatus.o ChkDiskSpace.o CBread.o \
              CBseek.o GenericSCSI.o InitCB.o DoCommand.o InitSocket.o

all:        libcaliban.a caliban

.c.o:       Caliban.h
	    $(CC) $(CFLAGS) $*.c

Caliban.o:  Caliban.h Caliban.c
	    $(CC) $(CFLAGS) Caliban.c

libcaliban.a:    $(OFILES)
	    /bin/rm -f  libcaliban.a
	    $(AR) cr libcaliban.a $(OFILES)
	    ranlib libcaliban.a

caliban:    Caliban.o libcaliban.a
	    $(CC) $(LFLAGS) -DLINUX Caliban.o libcaliban.a $(CBLIBS)

clean:
	    /bin/rm -f caliban libcaliban.a *.o *~

#
# install the public binary file and library
#
install:
	    \cp caliban $(CBHOME)/bin/caliban
	    \cp libcaliban.a $(CBHOME)/lib/libcaliban.a

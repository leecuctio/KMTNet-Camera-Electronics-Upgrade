#VERSION:sh  = date '+%y%h%d'
CC          = /usr/bin/gcc
AR          = /usr/bin/ar
CFLAGS	    = -w -c
LFLAGS      = -o Caliban
CBHOME	    = /home/pleiades/dts/Caliban

OFILES      = XmitMsg.o AckDisk.o InitDisk.o InitDiskTable.o InitSerial.o IsValidMount.o \
	      LogMsg.o ConsoleMsg.o Pong.o Prompt.o Status.o TransferDisk.o UseDisk.o    \
	      UseMount.o Utils.o ParseIniFile.o GetFITS.o ReqMount.o Ping.o CBStatus.o   \
	      ChkDiskSpace.o GenericSCSI.o

.c.o:       Caliban.h
	    $(CC) $(CFLAGS) $*.c

all:        libx.a Caliban

Caliban.o:  Caliban.h
	    $(CC) $(CFLAGS) -DVERSION='"Caliban v2.1[linux] OSU"' Caliban.c

libx.a:	    $(OFILES)
	    /bin/rm -f  libx.a
	    $(AR) cr libx.a $(OFILES)
	    ranlib libx.a

Caliban:    Caliban.o libx.a
	    $(CC) $(LFLAGS) Caliban.o libx.a /usr/lib/libncurses.a

clean:
	    /bin/rm -f Caliban libx.a *.o *~ #*

install:
	    \cp Caliban $(CBHOME)/Caliban

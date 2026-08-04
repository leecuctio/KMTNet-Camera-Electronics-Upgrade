#
# Makefile for KMTNet TCS Agent
#
# main.c is the main program for the PC-TCS interface agent
#
# Use "build", not "make" to build the pctcs executable.
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# Last Modified: 2007 Aug 14 [rwp/osu]
# --> original file for Yale1m system
#
# Modified for KMTNet by S. Cha, KASI
# Last Modified: 2014 Apr 01
#
# NOTE: If VERSION is not defined in this file, 
#       the version info in pctcs.h will be used.
#

VERSION     = v1.0 Beta
CC          = /usr/bin/g++
AR          = /usr/bin/ar
ISISLIB     = /home/dts/ISIS/client

CFLAGS      = -w -c -I$(ISISLIB) -L$(ISISLIB)
VFLAGS      = -DAPP_VERSION='"$(VERSION)"' -DAPP_COMPDATE='"$(COMPDATE)"' \
              -DAPP_COMPTIME='"$(COMPTIME)"'
LIBS        = -I$(ISISLIB) -L$(ISISLIB) -lisis -lreadline -lhistory \
	      -lncurses -lm
LFLAGS      = -o pctcs

OBJS        = loadconfig.o commands.o comsoft.o

.c.o:       pctcs.h commands.h sclutils.h
	    $(CC) $(CFLAGS) $(VFLAGS) $*.c

all:        pctcs

pctcs:    $(OBJS) main.c
	    $(CC) $(LFLAGS) $(VFLAGS) main.c $(OBJS) $(LIBS)

clean:
	    /bin/rm -f pctcs *.o

install:
	    \cp pctcs ../bin/
	    /bin/rm -f *.o

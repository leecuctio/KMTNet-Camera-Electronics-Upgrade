#
# Makefile for pctcs
#
# main.c is the main program for the PC-TCS interface agent
#
# Use "build", not "make" to build the pctcs executable.
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# Last Modified: 2013 Mar 29 [rwp/osu]
#
VERSION     = PCTCS v4.0.1
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

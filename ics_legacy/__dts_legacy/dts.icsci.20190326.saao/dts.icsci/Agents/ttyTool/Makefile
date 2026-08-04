#
# Makefile for ttytool
#
# Use "build", not "make" to build the ttytool executable.
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# Last Modified: 2005 Feb 17
#
VERSION     = v0.2.1
CC          = /usr/bin/g++
AR          = /usr/bin/ar
ISISLIB     = /home/dts/ISIS/client
TTYUTILS     = /home/dts/Utilities/TTYUtils

INCLUDES    = -I$(ISISLIB) -I$(TTYUTILS)
CFLAGS      = -w -c $(INCLUDES) 
VFLAGS      = -DAPP_VERSION='"$(VERSION)"' -DAPP_COMPDATE='"$(COMPDATE)"' \
              -DAPP_COMPTIME='"$(COMPTIME)"'
LIBS        = $(INCLUDES) -L$(ISISLIB) -L$(TTYUTILS) -lisis -lttyutils \
	      -lreadline -lhistory -lncurses
LFLAGS      = -o ttytool

OBJS        = loadconfig.o commands.o

.c.o:       client.h commands.h
	    $(CC) $(CFLAGS) $(VFLAGS) $*.c

all:        ttytool

ttytool:    $(OBJS) main.c
	    $(CC) $(LFLAGS) $(VFLAGS) main.c $(OBJS) $(LIBS)

clean:
	    /bin/rm -f ttytool *.o

install:
	    \cp ttytool ../bin/
	    /bin/rm -f *.o

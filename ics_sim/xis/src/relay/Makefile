#
# Makefile for isisrelay - an simple UDP/TTY port relay
#
# Use "build", not "make" to build the isisrelay executable.
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# Last Modified: 2014 Oct 21
#
VERSION     = v0.5.0
CC          = /usr/bin/g++
AR          = /usr/bin/ar
#ISISLIB     = /home/dts/ISIS/client
ISISLIB     = ../client

INCLUDES    = -I$(ISISLIB) 
LIBRARIES   = -L$(ISISLIB) 
CFLAGS      = -w -c $(INCLUDES) 
VFLAGS      = -DAPP_VERSION='"$(VERSION)"' -DAPP_COMPDATE='"$(COMPDATE)"' \
              -DAPP_COMPTIME='"$(COMPTIME)"'
LIBS        = $(INCLUDES) $(LIBRARIES) -lisis 
LFLAGS      = -o isisrelay

OBJS        = loadconfig.o

.c.o:       relay.h
	    $(CC) $(CFLAGS) $(VFLAGS) $*.c

all:        isisrelay

isisrelay:  $(OBJS) main.c
	    $(CC) $(LFLAGS) $(VFLAGS) main.c $(OBJS) $(LIBS)

clean:
	    /bin/rm -f isisrelay *.o

install:
	    \cp isisrelay ../bin/
	    /bin/rm -f *.o

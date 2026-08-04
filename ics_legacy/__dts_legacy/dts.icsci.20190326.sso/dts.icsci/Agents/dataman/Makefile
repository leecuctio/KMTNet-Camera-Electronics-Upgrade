#
# Makefile for dataman - an XVista-style image display agent.
#
# Use "build", not "make" to build the dataman executable.
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# Last Modified: 2005 July 9
#
VERSION     = v0.2.2
CC          = /usr/bin/g++
AR          = /usr/bin/ar
ISISLIB     = /home/dts/ISIS/client
XTVUTILS    = /home/dts/Utilities/XTV
CFITSIO     = /home/dts/Tools/cfitsio

INCLUDES    = -I$(ISISLIB) -I$(XTVUTILS) -I$(CFITSIO)
LIBRARIES   = -L$(ISISLIB) -L$(XTVUTILS) -L$(CFITSIO)
CFLAGS      = -w -c $(INCLUDES) 
VFLAGS      = -DAPP_VERSION='"$(VERSION)"' -DAPP_COMPDATE='"$(COMPDATE)"' \
              -DAPP_COMPTIME='"$(COMPTIME)"'
LIBS        = $(INCLUDES) $(LIBRARIES) -lX11 \
              -lisis -lxtv -lcfitsio -lreadline -lhistory -lncurses
LFLAGS      = -o dataman

OBJS        = clientutils.o loadconfig.o commands.o 

.c.o:       client.h commands.h
	    $(CC) $(CFLAGS) $(VFLAGS) $*.c

all:        dataman

dataman:     $(OBJS) main.c
	    $(CC) $(LFLAGS) $(VFLAGS) main.c $(OBJS) $(LIBS)

clean:
	    /bin/rm -f dataman *.o

install:
	    \cp dataman ../bin/
	    /bin/rm -f *.o

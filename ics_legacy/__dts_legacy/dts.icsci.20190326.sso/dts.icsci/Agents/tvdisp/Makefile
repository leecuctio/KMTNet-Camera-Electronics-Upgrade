#
# Makefile for tvdisp - an XVista-style image display agent.
#
# Use "build", not "make" to build the tvdisp executable.
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# Last Modified: 2005 May 31
#
VERSION     = v0.1.0
HOMEDIR     = /home/dts

CC          = /usr/bin/g++
AR          = /usr/bin/ar
ISISLIB     = $(HOMEDIR)/ISIS/client
XTVUTILS    = $(HOMEDIR)/Utilities/XTV
CFITSIO     = /home/dts/Tools/cfitsio

INCLUDES    = -I$(ISISLIB) -I$(XTVUTILS) -I$(CFITSIO)
LIBRARIES   = -L$(ISISLIB) -L$(XTVUTILS) -L$(CFITSIO)
CFLAGS      = -w -c $(INCLUDES) 
VFLAGS      = -DAPP_VERSION='"$(VERSION)"' -DAPP_COMPDATE='"$(COMPDATE)"' \
              -DAPP_COMPTIME='"$(COMPTIME)"'
#LIBS        = $(INCLUDES) $(LIBRARIES) -L/usr/lib64/X11 -lX11 
LIBS        = $(INCLUDES) $(LIBRARIES) -lX11 \
              -lisis -lxtv -lcfitsio -lreadline -lhistory -lncurses
LFLAGS      = -o tvdisp

OBJS        = clientutils.o loadconfig.o commands.o 

.c.o:       client.h commands.h
	    $(CC) $(CFLAGS) $(VFLAGS) $*.c

all:        tvdisp

tvdisp:     $(OBJS) main.c
	    $(CC) $(LFLAGS) $(VFLAGS) main.c $(OBJS) $(LIBS)

clean:
	    /bin/rm -f tvdisp *.o

install:
	    \cp tvdisp ../bin/
	    /bin/rm -f *.o

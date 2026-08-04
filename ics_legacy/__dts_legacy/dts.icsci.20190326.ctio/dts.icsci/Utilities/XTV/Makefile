#
# Makefile for libxtv, the XTV API library
#
# Build the package using the "build" script not with make.
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# Last Modified 2005 May 30
#

VERSION     = XTVUtils v0.3.0
CC          = /usr/bin/g++
AR          = /usr/bin/ar

CFLAGS      = -w -c
VFLAGS      = -DAPP_VERSION='"$(VERSION)"' -DAPP_COMPDATE='"$(COMPDATE)"' \
              -DAPP_COMPTIME='"$(COMPTIME)"'

OBJS        = xtvutils.o xtv.o

.c.o:       xtv.h
	    $(CC) $(CFLAGS) $(VFLAGS) $*.c

all:        libxtv.a 

libxtv.a:  $(OBJS) 
	    /bin/rm -f  libxtv.a
	    $(AR) cr libxtv.a $(OBJS)
	    ranlib libxtv.a

clean:
	    /bin/rm -f libxtv.a *.o


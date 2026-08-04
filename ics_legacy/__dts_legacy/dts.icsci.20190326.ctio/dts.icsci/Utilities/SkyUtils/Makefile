#
# Makefile for libsky - celestial utilities library
#
# Build the package using the "build" script not with make.
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# Last Modified 2007 July 25 
#
# Versions:
#   v1.0 - 2007 Jul 25 - first version as a library [rwp/osu]
#

VERSION     = SkyUtils v1.1.0
CC          = /usr/bin/g++
AR          = /usr/bin/ar

CFLAGS      = -w -c
VFLAGS      = -DSKY_VERSION='"$(VERSION)"' -DSKY_COMPDATE='"$(COMPDATE)"' \
              -DSKY_COMPTIME='"$(COMPTIME)"'

OBJS        = skyutils.o sexstr.o

.c.o:       skyutils.h 
	    $(CC) $(CFLAGS) $(VFLAGS) $*.c

all:        libsky.a 

libsky.a:  $(OBJS) 
	    /bin/rm -f  libsky.a
	    $(AR) cr libsky.a $(OBJS)
	    ranlib libsky.a

clean:
	    /bin/rm -f libsky.a *.o


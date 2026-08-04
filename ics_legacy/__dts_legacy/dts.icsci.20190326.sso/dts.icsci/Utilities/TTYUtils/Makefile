#
# Makefile for libttyutils Serial (TTY) Port I/O API library
#
# Build the package using the "build" script not with make.
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# Last Modified 2004 March 18
#
# Versions:
#   v1.0 - 2004 Mar 18 - first version of the general library [rwp/osu]
#

VERSION     = TTYUtils v1.0.1
CC          = /usr/bin/g++
AR          = /usr/bin/ar

CFLAGS      = -w -c
VFLAGS      = -DTTY_VERSION='"$(VERSION)"' -DTTY_COMPDATE='"$(COMPDATE)"' \
              -DTTY_COMPTIME='"$(COMPTIME)"'

OBJS        = ttyutils.o

.c.o:       ttyutils.h
	    $(CC) $(CFLAGS) $(VFLAGS) $*.c

all:        libttyutils.a 

libttyutils.a:  $(OBJS) 
	    /bin/rm -f  libttyutils.a
	    $(AR) cr libttyutils.a $(OBJS)
	    ranlib libttyutils.a

clean:
	    /bin/rm -f libttyutils.a *.o


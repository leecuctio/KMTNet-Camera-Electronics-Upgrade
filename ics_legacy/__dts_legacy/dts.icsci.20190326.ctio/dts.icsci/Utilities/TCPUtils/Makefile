#
# Makefile for libtcputils TCP Socket I/O API library
#
# Build the package using the "build" script not with make.
#
# R. Pogge, OSU Astronomy Dept.
# pogge@astronomy.ohio-state.edu
# Last Modified 2005 May 2
#
# Versions:
#   v1.0 - 2005 May 2 - first version of the general library [rwp/osu]
#

VERSION     = TCPUtils v1.0.1
CC          = /usr/bin/g++
AR          = /usr/bin/ar

CFLAGS      = -w -c
VFLAGS      = -DTCP_VERSION='"$(VERSION)"' -DTCP_COMPDATE='"$(COMPDATE)"' \
              -DTCP_COMPTIME='"$(COMPTIME)"'

OBJS        = tcputils.o

.c.o:       tcputils.h
	    $(CC) $(CFLAGS) $(VFLAGS) $*.c

all:        libtcputils.a 

libtcputils.a:  $(OBJS) 
	    /bin/rm -f  libtcputils.a
	    $(AR) cr libtcputils.a $(OBJS)
	    ranlib libtcputils.a

clean:
	    /bin/rm -f libtcputils.a *.o


#
# Makefile for KMTNet OBS Agent
#
# main.c is the main program for the scripting observation agent
#
# Use "build", not "make" to build the obstool executable.
#
# Original codes and plotform was from KMTNet TCS Agent v1.6.1.1
# Developed by R. Pogge in OSU Astronomy Dept and S. Cha in KASI
#
# Modified for scripting observation tool by S. Cha, KASI
# Last Modified: 2024 Jun 25
#
# NOTE: If VERSION is not defined in this file, 
#       the version info in obstool.h will be used.
#

#VERSION    = v0.1  --> use the ver info in obstool.h

 CC          = /usr/bin/g++
 AR          = /usr/bin/ar

#ISISLIB    = /home/dts/ISIS/client
 ISISLIB    = ../ISISclient
 HIREDIS    = ../hiredis

#CFLAGS      = -w -c -I$(ISISLIB) -L$(ISISLIB)
 CFLAGS      = -w -c -I$(ISISLIB) -L$(ISISLIB) -I$(HIREDIS) -L$(HIREDIS)

 VFLAGS      = -DAPP_VERSION='"$(VERSION)"' -DAPP_COMPDATE='"$(COMPDATE)"' \
               -DAPP_COMPTIME='"$(COMPTIME)"'

#LIBS        = -I$(ISISLIB) -L$(ISISLIB) -lisis -lreadline -lhistory \
               -lncurses -lm
#LIBS        = -I$(ISISLIB) -L$(ISISLIB) -lisis -lreadline -lhistory \
               -lncurses -lcurl -lm   ## including curl lib on 20220718                                      
#LIBS        = -I$(ISISLIB) -L$(ISISLIB) -lisis -lreadline -lhistory \
               -lncurses -lm  ## rollback since not using curl lib
#LIBS        = -I$(ISISLIB) -L$(ISISLIB) -lisis \
               -I$(HIREDIS) -L$(HIREDIS) -lhiredis \
               -lreadline -lhistory -lncurses -lm 
                                       ## including hiredis on 20240618
 LIBS        = -I$(ISISLIB) -L$(ISISLIB) -lisis \
               -I$(HIREDIS) -L$(HIREDIS) -lhiredis \
               -lreadline -lhistory -lncurses -lm -lcurl 
                                       ## including Curl Lib on 20240625

 LFLAGS      = -o obstool

#OBJS        = loadconfig.o commands.o
 OBJS        = loadconfig.o commands.o calculation.o

.c.o:       obstool.h commands.h sclutils.h

	    $(CC) $(CFLAGS) $(VFLAGS) $*.c

all:        obstool

obstool:    $(OBJS) main.c

	    $(CC) $(LFLAGS) $(VFLAGS) main.c $(OBJS) $(LIBS)

clean:
	    /bin/rm -f obstool *.o

install:    
	    \cp obstool ../bin/
	    /bin/rm -f *.o


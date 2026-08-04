TCS Agent for KMTNet system
  - Official KMTNet Version
  - Last Verified: 2014 Aug 26 [sc/kasi]

# Original version information

pctcs Agent
  - Official Yale 1.0m Version
  - Last Verified: 2013 March 29 [rwp/osu]

# File list

  - 00README.txt : directions for 1st building and running the TCS Agent
  - pctcs.h      : main TCS Agent header file
  - main.c       : main func for interface monitoring and processing
  - loadconfig.c : load an TCS Agent's runtime configuration file
  - comsoft.c    : ComSoft PCTCS and AUX control utility routines
  - commands.h   : command tree header for the TCS Agent
  - commands.c   : command handler, command action, and utility functions
  - pctcs.ini    : runtime configuration file (default)
  - Makefile     : compile and build configuration
  - build (exec) : script to build a executable file of TCS Agent
  - pctcs (exec) : executable file of TCS Agent, built by the script 'build'
  (10 items)

# Notes for building exec file

Use "build", not "make" to build the TCS Agent executable.

Both the ISIS client library of OSU and GNU Readline library are required to build a TCS Agent.

The ISIS client library must be installed in the below directory before building TCS Agent. "isisclient.h" and "libisis.a" files are used in the complile.

    /home/dts/ISIS/client

The GNU Readline library must be installed in your system before building TCS Agent. You can download the installation file with open source and detailed manuals in the Readline homepage.

# Notes for running

If TCS Agent is executed without the argument for runtime configuration file, the default name and location will be used, same as below. 

    /home/dts/Config/pctcs.ini

If you are going to use the default, you should copy a pctcs.ini to the default location. If you don't want to use the default name and location, you can put a arguments for the file path as below.

    $ ./pctcs ./pctcs.ctio.ini

The agent is configured either as an ISIS client, or as a standalone program operating independently of an ISIS system. Either the Standalone mode or the ISIS client mode, TCS Agent interacts any client that according to IMPv2 through a UDP socket.
In the ISIS client mode, TCS Agent acts a client of ISIS server that has the ISIS ID and the ISIS port defined in Runtime configuration, and also an ISIS client terminal is enabled so the local user can interacts other nodes through ISIS server on the console. (e.g., TC% >ICS ping)


The agent is configured either as an ISIS client, or as a standalone program operating independently of an ISIS system. In the Standalone mode, TCS Agent accepts and processes commands of any client that according to IMPv2 through a UDP socket. In the ISIS client mode, TCS Agent interacts only ISIS that has the ISIS ID and the ISIS port defined in Runtime configuration, and also an ISIS client terminal is enabled so the local user can send commands to ISIS on the console, IMPv2-compliant. (e.g., TC% >IS ping)

# Usage

The 'help' command shows the TCS Agent commands list with simple descriptions.

For using low-level commands of PCTCS and AUX ctrl, refer the documents 'COMSOFT Legacy PC-TCSTM Communications' and 'KMTNet Auxiliary GUI control SW – Remote commands definition'

# Reporting Bugs

Bugs for this version of the KMTNet TCS agent should be sent to:

    chasm@kasi.re.kr
    Sang-Mok Cha, KASI KMTNet team

# END

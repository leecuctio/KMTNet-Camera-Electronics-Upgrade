EXEC_ISIS - A modified ISIS for the KMTN system, which requires many
ICIMACS-protocol machines communicating across hardware boundaries.

-Jerry Mason
Imaging Sciences Laboratory
Ohio State University Astronomy Department
14 February 2014

All code based on Dr. Richard Pogge's ISIS code - his ISIS README file starts
below.

------------------------------------------------------------------------------


ISIS - Integrated Science Instrument Server


Overview:
--------

ISIS is a lightweight, simple message-passing server used by the
data-taking system of new-generation OSU instruments for interprocess
communication and coordination.  The messaging syntax is the ICIMACS
protocol in used in the older DOS-based instrument systems.  Instrument
data-taking processes are ISIS client nodes, and communicate with each
other through ISIS (a few legacy clients can communicate directly with
each other, but ideally clients are non-routing nodes).

The ISIS server application is written in ANSI C, and can communicate
via TCP/IP sockets (standard INET protocol connection-less UDP datagram
sockets) and serial ports.  It provides a simple command-line interface
(based on the GNU readline/history packages), and provides runtime
communication logging.  The application is designed at present to be
single-threaded, though with some modification it can be made
multi-threaded as many of the low-level routines were designed to make
at least an attempt at being thread-safe.


Package Organization:
--------------------

The organization of the package is as follows:

     server/ -- ISIS server source code.  Server app is self-contained.

     client/ -- ISIS client library (libisis.a) source code and library.
                 the clients/examples/ directory contains examples and
                 template utility subroutines for building ISIS clients.

     config/ -- Runtime configuration files for the server app.

        bin/ -- Binary executable(s) for the server, and sample wrapper
                 scripts (e.g., how to run an isis server with log rotation)

        doc/ -- ISIS server app and client library documentation.  Includes
                 a formal definition of the ICIMACS protocol.

   workshop/ -- Working space with test code, defunct code.

     RELEASE -- Package release notes

      README -- This file


About ISIS:
----------

In a new-generation system, ISIS takes on and extends the function of
the old "WC" DOS machines.  DOS clients connect via serial ports,
eliminating the need for the tcwrappers code that contributed to the
instability of the WC system.  A "WC" host may still be used, it is
treated as yet another ISIS client, though the fact that it and the IC
are "routing" clients does occasionally emerge as a problem: both the WC
and IC "block" when performing critical realtime tasks, making it
possible for communications to hang up.  ISIS is designed to be
specifically non-blocking.

Prospero version 5.x is designed to run as an ISIS client, eliminating
the need for the old ariel program.  More specifically, Prospero is a
prototype of a type of ISIS client known as a "director" - an
interactive meta-client that is aware of other clients and coordinates
their functions.

Caliban has been recast as an ISIS client, but can still be configured
to communicate directly with a WC DOS pc for backwards compatibility).
This required only modification of the low-level transport interface,
and replacing the old curses-based command-line interface with a GNU
readline/history type interface.  Caliban cannot yet connect directly to
an IC, bypassing a WC, because of some file handling functions still
assumed by the WC.

A new type of application introduced with the prototype ISIS system is
the family of programs called "agents".  Agents are autonomous clients
that perform specific real-time and/or "blocking" functions, often
acting as interfaces between the data-taking system and external
applications (e.g., a telescope control system) that do not use our
messaging protocol. Most agents will have little or no command-line
interface (in this, they somewhat resemble Unix daemons).  Agents are
explicitly non-routing, and in the server/client topology sit at the
termini of communications lines.  The first agent introduced was
TCSAgent, a small C program that provides a serial interface to the
PC-TCS system at the CTIO 1.3m telescope, translating the continous
serial telemetry stream into TCS status strings that can be returned
upon request by various ISIS nodes (e.g., in response to "tcstatus"
commands by the IC to build the CCD image header).

A general client library (libisis.a) has been provided to make the
creation of new ISIS client applications easier.


Future Developments:
-------------------

Two main developments are in various stages of progress.  One has been to
create a set of C++ classes to support building ISIS clients in C++
(there is no plan as yet to rewrite the ISIS server application itself
in C++ anytime soon, but we compile with g++).  We have done this with the
isisclient class written in the Qt framework for the MODS user interface
and related tools.  MODS is the first OSU instrument that uses a GUI.

The second is a plan - executed in 2004 - was to remove the WC from
all systems where we can.  This was first done for OSIRIS at SOAR, and
then repeated at MDM for CCDS, TIFKAM, and the new MDM4K.  With MODS,
we developed a 2-channel linux-based caliban system, so we could in
principle remove the WC from the ANDICAM system, but there is no immediate
plans for doing so.

An example of a hybrid project using the ISIS architecture is the 
CTIO/Yale 4K camera project in which the CCD controller is a Steward
Observatory AzCam system provided by ITL (the hardware uses an ARC
GenII controller and Windows XP computer with a socket interface).

MODS is being built entirely using the ISIS architecture.  The first iteration
used an old-style DOS IC system, but we hope to develop a Linux-based
IC once the new generationg PCI sequence card is working, so we can move
away from the Caliban data transfer system with its dependence on legacy
hardware that is no longer manufactured or supported generally (can you say
eBay kids?).

------------------------------
R. Pogge, OSU Astronomy Dept.
pogge@astronomy.ohio-state.edu
2010 March 30

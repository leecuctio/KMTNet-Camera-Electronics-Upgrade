// CBread Routine
// Purpose: Generic abstraction for read command.  Works for both regular disk
//          access as well as Linux SCSI Pass Through driver access 
// Requires: File descriptor, buffer, and length
// Returns: Nothing
//

#include "Caliban.h"

long 
CBread(int ifd, char *inbuf, long buflen) 
{
  long numchars;

#ifdef UseSG
  numchars = SGread(ifd, inbuf, buflen);
#else
  numchars = read(ifd, inbuf, buflen);
#endif

  return (numchars);
}

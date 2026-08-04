// CBseek Routine
// Purpose: Generic abstraction for seek command.  Works for both regular disk
//          access as well as Linux SCSI Pass Through driver access
// Requires: File descriptor, offset, and base (from beg or end indicator)
// Returns: Nothing
//

#include "Caliban.h"

void 
CBseek(int ifd, long CBoffset, int CBbase) 
{
#ifdef UseSG
  SGseek(CBoffset);
#else
  lseek(ifd, CBoffset, CBbase);
#endif
}

/* IsValidMount Function                                                              */
/* Purpose: Determines validity of a given file system mount point                    */
/* Requires: Mount buffer                                                             */
/* Returns: cb_FALSE for invalid mount point; cb_TRUE for valid mount point condition */

#include "Caliban.h"

int IsValidMount(char *mountname)
{
  char filename[MED_STR_SIZE];                       /* Filename buffer               */
  int tfd;                                           /* Temporary file descriptor     */

  sprintf(filename, "%s/.", strstr(mountname, "/")); /* Assemble complete mount point */

  if(access(filename, W_OK)==cb_ERROR)               /* Test accessibility            */ 
    {
      return(cb_FALSE);                              /* Failure                       */
    }
  else
    {
      return(cb_TRUE);                               /* Success                       */
    }
}

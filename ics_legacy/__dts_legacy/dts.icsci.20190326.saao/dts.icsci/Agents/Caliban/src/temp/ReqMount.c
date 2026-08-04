/* ReqMount Routine                                      */
/* Purpose: Reports known valid mount points             */
/* Requires: Port number and host to receive mount list  */
/* Returns: Nothing                                      */

#include "Caliban.h"

void ReqMount(int port, char *host)
{
  int lcv;                   /* Loop control variable    */
  char outstr[MED_STR_SIZE]; /* Output string buffer     */

  /* Loop through available mount points and report them */

  for(lcv=0;lcv<mounttab->nummounts;lcv++)
    {
      XmitMsg(port, host, "FOUND MOUNT %s", mounttab->mount[lcv]);
    }

  XmitMsg(port, host, "%s", "FOUND MOUNT ALL"); /* Done  */
}

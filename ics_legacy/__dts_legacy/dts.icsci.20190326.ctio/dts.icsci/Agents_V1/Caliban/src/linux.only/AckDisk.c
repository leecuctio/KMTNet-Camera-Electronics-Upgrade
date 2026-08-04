/* AckDisk Routine                         */
/* Purpose: ACK DISK command handler       */
/* Requires: Port number, destination host */

#include "Caliban.h"

/* Sets the flag in the system table to indicate that disk synchronization */
/* has been acknowledged and transmits the request swap command to enable  */
/* disk transfers                                                          */

void AckDisk(int port, char *dest)
{
  disktab->ackdisk = cb_TRUE;
}

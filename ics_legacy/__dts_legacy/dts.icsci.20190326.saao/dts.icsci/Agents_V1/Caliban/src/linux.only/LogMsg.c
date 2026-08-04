/* LogMsg Routine                               */
/* Purpose: Central logfile generation facility */
/* Requires: Log file entry buffer              */
/* Returns: Nothing                             */

#include "Caliban.h"

void LogMsg(char logstr[MED_STR_SIZE])
{
  char outstr[MED_STR_SIZE];    /* Output string buffer   */

  char *timestr;                /*                        */
  struct tm *lst;               /* Time structures        */
  time_t t;                     /*                        */

  t = time(NULL);               /* Initialize time string */
  lst = localtime(&t);          /* Get current time       */
  timestr = asctime(lst);       /* Format time string     */
  timestr[strlen(timestr) - 1] = '\0';
  sprintf(outstr, "%s - %s\n", timestr, logstr); /* Enter current time into log */
  write(systab->logfd, outstr, strlen(outstr));  /* Enter message into log      */
}



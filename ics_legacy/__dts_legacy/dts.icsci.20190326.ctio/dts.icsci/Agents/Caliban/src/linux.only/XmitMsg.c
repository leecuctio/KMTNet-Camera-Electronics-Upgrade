/* XmitMsg Routine                                                             */
/* Purpose : Central message multiplexer                                       */
/* Requires: Port handle, Destination name, Message format string and buffer   */
/* Returns : Nothing                                                           */

#include "Caliban.h"
#include <varargs.h> /* Used for variable length argument list    */

void XmitMsg(va_alist)
va_dcl
{
  /* Note that this routine accepts a variable number of parameters to allow   */
  /* for a variable length format string                                       */

  int port;                       /* Destination port number                   */
  int cnt=0;                      /* Format string index                       */
  int argcnt=0;                   /* Argument index                            */
  char *host;                     /* Destination host name                     */
  char *format;                   /* Message format string                     */
  char expformat[MED_STR_SIZE];   /* Expanded format string                    */
  char arglst[MED_STR_SIZE];      /* Argument list                             */
  char xmitstr[MED_STR_SIZE];     /* Message to be transmitted                 */
  char outstr[MED_STR_SIZE];      /* Generic output buffer                     */
  va_list paramlist;              /* Variable parameter list structure         */

  bzero(expformat, sizeof(expformat));  /* Initialize arrays                   */
  bzero(arglst, sizeof(arglst));

  va_start(paramlist);            /* Initialize variable length parameter list */

  port = va_arg(paramlist, int);      /* Port is first argument                */
  host = va_arg(paramlist, char *);   /* Host is next argument                 */
  format = va_arg(paramlist, char *); /* Then the format string                */

  /* Loop through the format string and replace %s's with the corresponding    */
  /* remaining arguments in the list                                           */

  while(cnt<strlen(format))
    {
      if(format[cnt]=='%')
	{
	  cnt += 2;
	  strcat(arglst, va_arg(paramlist, char *));
	  argcnt = strlen(arglst);
	}
      arglst[argcnt++]=format[cnt++];
    }

  sprintf(expformat, "%s %s\r", "%s>%s", arglst);

  sprintf(outstr, expformat, systab->localhost, host);      /* Format output string including address info    */

  write(port, outstr, strlen(outstr));                      /* Output message                                 */

  if(systab->verbose == cb_TRUE)                            /* Check to see if verbose mode is enabled and if */
    {                                                       /*   so, output the message to the screen         */
      outstr[strlen(outstr)-1] = NUL;                       /* Remove the trailing carriage return (\r)       */
      ConsoleMsg("OUT: %s\n", outstr);
    }
}

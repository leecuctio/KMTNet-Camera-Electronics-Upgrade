/* ConsoleMsg Routine                                     */
/* Purpose:  Central screen output facility               */
/* Requires: Printf-like format string and message buffer */
/* Returns:  Nothing                                      */

#include "Caliban.h"

void ConsoleMsg(char *usr_format, char *usr_outstr)
{
  int out_xpos, out_ypos;                    /* Output window screen coordinates                            */
  int in_xpos, in_ypos;                      /* Input window screen coordinates                             */
  char logstr[MED_STR_SIZE];                 /* Generic log string buffer                                   */
  char format[LONG_STR_SIZE];
  char outstr[LONG_STR_SIZE];

  bzero(logstr, sizeof(logstr));             /*                                                             */
  bzero(format, sizeof(format));             /* Clean livin'                                                */
  bzero(outstr, sizeof(outstr));             /*                                                             */

  /* Let's put what the user gave us into a buffer in case they passed us a constant string expression,     */
  /* which would cause a segmentation fault if we try to modify it below                                    */

  strcpy(format, usr_format);
  strcpy(outstr, usr_outstr);

  getyx(systab->input, in_ypos, in_xpos);    /* Record the current command line cursor position             */

  getyx(systab->output, out_ypos, out_xpos); /* Determine if output has reached bottom of screen and if so, */
  if(out_ypos>=LINES-2)                      /* clear screen and reposition at top.  Improves performance.  */
    wclear(systab->output);                  /*                                                             */

  /* Replace any carriage return characters (\r) with newlines (\n) before displaying, or the \r would      */
  /* cause the line to be immediately overwritten on screen                                                 */

  if(outstr[strlen(outstr)-1]=='\r')
    outstr[strlen(outstr)-1]='\n';

  if(outstr[strlen(outstr)-1]!='\n')
      sprintf(outstr, "%s\n", outstr);
  
  /* If this message is an error or status from me, don't bother displaying the addressing/header           */
  /* Magic number city, someday I'll clean this up and make it more generalized                             */

  if(strncmp(outstr, "CB>CB STATUS: ", 14)==0)
    sprintf(outstr, "%s", outstr+14);

  if(strncmp(outstr, "CB>CB ERROR: ", 13)==0)
    sprintf(outstr, "%s", outstr+13);

  wprintw(systab->output, format, outstr);   /* Display message to output region of virtual screen          */
  wrefresh(systab->output);                  /* Repaint screen                                              */

  wmove(systab->input, in_ypos, in_xpos);    /* Return the cursor to its original position                  */
  wrefresh(systab->input);                   /* Repaint screen                                              */

  if(systab->verbose == cb_TRUE)             /* Check to see if verbose mode is enabled and if              */
    {                                        /* so, log the message                                         */
      sprintf(logstr, format, outstr);

      /* If this is the result of displaying the log or just echoing a command entered, don't log it        */

      if(!strstr(logstr, "LOG:") && (logstr[0] != '%'))
	{

	  /* Get rid of those pesky carriage returns to beautify the log */

	  while(logstr[strlen(logstr)-1]=='\n')
	    logstr[strlen(logstr)-1]=NUL;
	  LogMsg(logstr); /* Log the damn thing */
	}
    }
  
}





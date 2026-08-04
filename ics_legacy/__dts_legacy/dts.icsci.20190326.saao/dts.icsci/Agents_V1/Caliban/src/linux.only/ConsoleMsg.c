/* ConsoleMsg Routine                                     */
/* Purpose:  Central screen output facility               */
/* Requires: Printf-like format string and message buffer */
/* Returns:  Nothing                                      */

#include "Caliban.h"

void ConsoleMsg(char format[MED_STR_SIZE], char outstr[MED_STR_SIZE])
{
  int out_xpos, out_ypos;                    /* Output window screen coordinates                            */
  int in_xpos, in_ypos;                      /* Input window screen coordinates                             */
  char logstr[MED_STR_SIZE];                 /* Generic log string buffer                                   */

  getyx(systab->input, in_ypos, in_xpos);    /* Record the current command line cursor position             */

  getyx(systab->output, out_ypos, out_xpos); /* Determine if output has reached bottom of screen and if so, */
  if(out_ypos>=LINES-2)                      /* clear screen and reposition at top.  Improves performance.  */
    wclear(systab->output);                  /*                                                             */

  wprintw(systab->output, format, outstr);   /* Display message to output region of virtual screen          */
  wrefresh(systab->output);                  /* Repaint screen                                              */

  wmove(systab->input, in_ypos, in_xpos);    /* Return the cursor to its original position                  */
  wrefresh(systab->input);                   /* Repaint screen                                              */

  if(systab->verbose == cb_TRUE)             /* Check to see if verbose mode is enabled and if              */
    {                                        /* so, log the message                                         */
      sprintf(logstr, format, outstr);
      while(logstr[strlen(logstr)-1]=='\n')
	logstr[strlen(logstr)-1]=NUL;
      LogMsg(logstr);
    }

}





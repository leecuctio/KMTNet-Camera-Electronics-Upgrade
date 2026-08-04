/* Prompt Routine                                         */
/* Purpose: Clears and re-displays the command input line */
/* Requires: Nothing                                      */
/* Returns: Nothing                                       */

#include "Caliban.h"

void Prompt()
{
  int lcv;

  wstandout(systab->input); /* Invert color */
  wclear(systab->input);    /* Clear the input line */
  wprintw(systab->input, "%s%% ", systab->localhost); /* Display the prompt */

  /* Blacken out the rest of the line */

  for(lcv=0;lcv<systab->cols-(strlen(systab->localhost)+3);lcv++)
    wprintw(systab->input, " ");
  
  /* Return the cursor to the beginning and paint the screen */

  wmove(systab->input, 0, strlen(systab->localhost)+2);
  wrefresh(systab->input);
}

// ConsoleMsg Routine                                     
// Purpose:  Central screen output facility               
// Requires: Printf-like format string and message buffer 
// Returns:  Nothing                                      
// 
// Stripped out all curses stuff because we don't do that
// no more (what were we thinking?).
// 

#include "Caliban.h"

void 
ConsoleMsg(char *usr_format, char *usr_outstr)
{
  char logstr[MED_STR_SIZE]; 
  char format[LONG_STR_SIZE];
  char outstr[LONG_STR_SIZE];

  // zero the working buffers 

  memset(logstr, 0, sizeof(logstr));  
  memset(format, 0, sizeof(format));  
  memset(outstr, 0, sizeof(outstr));  

  // Put what the user gave us into a buffer in case they passed us a
  // constant string expression, which would cause a segmentation fault
  // if we try to modify it below

  strcpy(format, usr_format);
  strcpy(outstr, usr_outstr);

  // Replace any carriage return characters (\r) with newlines (\n)
  // before displaying, or the \r would cause the line to be immediately
  // overwritten on screen
   
  if(outstr[strlen(outstr)-1]=='\r')
    outstr[strlen(outstr)-1]='\n';

  if(outstr[strlen(outstr)-1]!='\n')
    sprintf(outstr, "%s\n", outstr);

  // Check for special message types & set colors appropriately

  if (strstr(outstr,"ERROR:"))
    REDTEXT;
  else if (strstr(outstr,"WARNING:"))
    BLUTEXT;
  else if (strstr(outstr,"FATAL:"))
    MAGTEXT;

  // If this message is an error or status from me, don't bother
  // displaying the addressing/header.  Magic number city, someday I'll
  // clean this up and make it more generalized

  /*
  if(strncmp(outstr, "CB>CB STATUS: ", 14)==0)
    sprintf(outstr, "%s", outstr+14);

  if(strncmp(outstr, "CB>CB ERROR: ", 13)==0)
    sprintf(outstr, "ERROR: %s", outstr+13);

  if(strncmp(outstr, "CB>CB WARNING: ", 15)==0)
    sprintf(outstr, "WARNING: %s", outstr+15);
  */

  // Now print the silly thing

  sprintf(logstr,format,outstr);
  printf("%s",logstr);
  TXTRESET;

  // verbose mode handling & logging  

  if(systab->verbose == cb_TRUE)  {
    sprintf(logstr, format, outstr);
    if(!strstr(logstr, "LOG:") && (logstr[0] != '%')) {
      while(logstr[strlen(logstr)-1]=='\n')
	logstr[strlen(logstr)-1]=NUL;
      LogMsg(logstr);
    }
  }
  
}


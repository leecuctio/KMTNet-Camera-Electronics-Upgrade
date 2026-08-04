// LogMsg Routine                               
// Purpose: Central logfile generation facility 
// Requires: Log file entry buffer              
// Returns: Nothing                             

#include "Caliban.h"
char *GetFineTime(void);

void 
LogMsg(char *logstr)
{
  char outstr[MED_STR_SIZE];    // Output string buffer     
  char *timestr;         
  struct tm *lst;               // Time structures          
  time_t t;              

  memset(outstr, 0, sizeof(outstr));

  /*
  t = time(NULL);               // Initialize time string   
  lst = localtime(&t);          // Get current time         
  timestr = asctime(lst);       // Format time string       
  timestr[strlen(timestr) - 1] = '\0';
  sprintf(outstr, "%s - %s\n", timestr, logstr); // timetag log entry  
  */

  // Newstyle - fine-grained timestamp

  sprintf(outstr, "%s - %s\n", GetFineTime(), logstr); // timetag log entry  

  write(systab->logfd, outstr, strlen(outstr));  // log outstr         
}

/***************************************************************************
 *
 * GetFineTime() - read the system's UTC time clock and return the
 *                 fine-grained time, with seconds to usec precision
 *
 * Arguments: none
 *
 * Description: 
 *   Reads the system's UTC time clock and returns a pointer to a
 *   string with the fine-grained UTC time in the format
 *
 *      hh:mm:ss.ssssss
 * 
 *   Based on gf_time() from Stevens, W.R., 1998, Unix Network Programming,
 *   Vol 2, Prentice Hall, Figure 15.6, but I make a string, and restrict
 *   the output of seconds to msec rather than usec.
 *
 * Author:
 *   R. Pogge, OSU Astronomy Dept.
 *   pogge@astronomy.ohio-state.edu
 *   2003 January 7
 *
 * Modification History:
 *
 ***************************************************************************/

char *
GetFineTime(void)
{
  struct timeval tv;
  static char str[30];
  char *ptr;
  struct tm *gmt;
  time_t t;

  /* first get the UTC time */

  t = time(NULL);
  gmt = gmtime(&t);

  /* then get the usec part, If we're off a couple of usec no big deal */

  if (gettimeofday(&tv,NULL)<0)
    printf("gettimeofday error\n");
  ptr = ctime(&tv.tv_sec);

  sprintf(str,"%.2i:%.2i:%.2i.%06ld",gmt->tm_hour,gmt->tm_min,
	  gmt->tm_sec,tv.tv_usec);

  return(str);

}


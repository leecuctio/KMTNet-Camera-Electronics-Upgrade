/***************************************************************************
 *
 * Time Utilities: 
 * --------------
 *   GetUTCTime()  - read the system's UTC time clock
 *   GetFineTime() - get fine-grained system UTC time with usec precision
 *   SysTimestamp() - return the fine-grained system time in with usec
 *                    precision as seconds elapsed since UTC 1970 January 1.
 *
 ***************************************************************************/

#include "ISISsock.h"
#include "ISIS.h"

/***************************************************************************
 *
 * GetUTCTime() - read the system's UTC time clock
 *
 * Arguments: none
 *
 * Description: 
 *   Reads the system's UTC time clock and puts date/time information
 *   into the system table.
 *
 *   Dates are encoded in CCYY-MM-DD (ISO-8601) format
 *   Times are encoded in hh:mm:ss format
 *   DateTags are encoded in ccyymmdd format
 *
 * Author:
 *   R. Pogge, OSU Astronomy Dept.
 *   pogge@astronomy.ohio-state.edu
 *   2003 January 4
 *
 * Modification History:
 *
 ***************************************************************************/

void
GetUTCTime(void)
{
  struct tm *gmt;
  time_t t;
  int monthnum;
  int ccyy;

  t = time(NULL);
  gmt = gmtime(&t);
  monthnum = (gmt->tm_mon)+1;

  /* ISO 8601 Date & time format: ccyy-mm-dd, hh:mm:ss */

  ccyy = gmt->tm_year + 1900;
  sprintf(isis.DateTag,"%.4i%.2i%.2i",ccyy,monthnum,gmt->tm_mday);
  sprintf(isis.UTCDate,"%.4i-%.2i-%.2i",ccyy,monthnum,gmt->tm_mday);
  sprintf(isis.UTCTime,"%.2i:%.2i:%.2i",gmt->tm_hour,gmt->tm_min,
	  gmt->tm_sec);

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

/***************************************************************************
 *
 * SysTimestamp() - read the system's time clock and return the
 *                  elapsed time in sec since UTC 1970 Jan 1 with
 *                  usec precision.
 *
 * Arguments: none
 *
 * Description: 
 *   Reads the system's time clock and returns a double-precision
 *   value with the time in seconds and microseconds since UTC
 *   1970 January 1.  This provides us with a fine-grained numerical
 *   timestamp for the syste.
 *
 * Author:
 *   R. Pogge, OSU Astronomy Dept.
 *   pogge@astronomy.ohio-state.edu
 *   2003 January 7
 *
 * Modification History:
 *
 ***************************************************************************/

double 
SysTimestamp(void)
{
  struct timeval tv;
  static char str[30];
  char *ptr;

  if (gettimeofday(&tv,NULL)<0)
    printf("gettimeofday error\n");
  ptr = ctime(&tv.tv_sec);

  sprintf(str,"%ld.%06ld",tv.tv_sec,tv.tv_usec);
  
  return((double)(atof(str)));

}

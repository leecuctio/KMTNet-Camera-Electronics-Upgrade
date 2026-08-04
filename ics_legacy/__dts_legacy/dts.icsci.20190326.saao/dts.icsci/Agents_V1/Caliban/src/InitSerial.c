/* InitSerial Routine                                          */
/* Purpose: Serial device initialization                       */
/* Requires: Nothing                                           */
/* Returns: File descriptor upon success, zero upon failure    */

#include <termio.h>  /* Serial device constants and structures */
#include "Caliban.h"

int InitSerial()
{
  int serialport;                               /* Serial device file descriptor */
  struct termios tty;                           /* Port configuration structure */

  if ((serialport = open(systab->serialdev, O_RDWR | O_NDELAY)) != cb_ERROR) /* Attempt to open the port */
    {
      tcgetattr(serialport, &tty);              /* Set port parameters to match serial */
      tty.c_iflag &= ~ISTRIP;                   /* host's configuration                */
      tty.c_lflag |= ICANON;
      tty.c_lflag &= ~ECHO;
      tty.c_cflag |= CS8;
      tty.c_cflag |= CREAD;
      tty.c_cflag &= ~CSTOPB;
      tty.c_cflag &= ~PARENB;
      tty.c_cc[VMIN] = 1;
      tty.c_cc[VTIME] = 0;
      cfsetispeed(&tty, (speed_t) B9600);
      cfsetospeed(&tty, (speed_t) B9600);
      tcflush(serialport, TCIFLUSH);
      tcsetattr(serialport, TCSAFLUSH, &tty);
    }
  else
    return(SYSERR);                             /* Failure */

return(serialport);                             /* Success */

}

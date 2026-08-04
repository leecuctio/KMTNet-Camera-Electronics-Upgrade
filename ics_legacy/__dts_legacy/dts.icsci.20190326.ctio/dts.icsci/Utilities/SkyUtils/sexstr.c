//---------------------------------------------------------------------------
//
// SexStr(x,str) - convert a decimal angular coordinate into sexigesimal
//
// output is coded into sexstr as -dd:mm:ss.s
//
// R. Pogge, OSU Astronomy Dept.
// 1998 July 10
//

#include "skyutils.h"

void 
SexStr(double x, char *tstr)
{
  int dd;
  int dm;
  double sec;
  double tmp;
  int isigned;

  if (x == 0.0) {
    strcpy(tstr,"00:00:00.0");
    return;
  }

  if (x < 0.0) {
    isigned = 1;
    x = fabs(x);
  } else {
    isigned = 0;
  }

  dd = (int)(x);
  tmp = (x - (double)(dd)) * 60.0;
  dm = (int)(tmp);
  tmp = (double)(dd) + (double)(dm)/60.0;
  sec = 3600.0*(x-tmp);

  if (isigned == 1) {
    sprintf(tstr,"-%.2i:%.2i:%04.1f",dd,dm,sec);
  } else {
    sprintf(tstr,"%.2i:%.2i:%04.1f",dd,dm,sec);
  }

}

